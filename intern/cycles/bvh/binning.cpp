/* SPDX-FileCopyrightText: 2009-2011 Intel Corporation
 * SPDX-FileCopyrightText: 2012-2022 Blender Foundation
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Adapted code from Intel Corporation. */

// #define __KERNEL_SSE__

#include "bvh/binning.h"

#include <cstdlib>

#include "util/algorithm.h"
#include "util/boundbox.h"
#include "util/types.h"

CCL_NAMESPACE_BEGIN

/* SSE replacements */

__forceinline void prefetch_L1(const void * /*ptr*/) {}
__forceinline void prefetch_L2(const void * /*ptr*/) {}
__forceinline void prefetch_L3(const void * /*ptr*/) {}
__forceinline void prefetch_NTA(const void * /*ptr*/) {}

template<size_t src> __forceinline float extract(const int4 &b)
{
  return b[src];
}
template<size_t dst> __forceinline const float4 insert(const float4 &a, const float b)
{
  float4 r = a;
  r[dst] = b;
  return r;
}

__forceinline int get_best_dimension(const float4 &bestSAH)
{
  // return (int)__bsf(movemask(reduce_min(bestSAH) == bestSAH));

  const float minSAH = min(bestSAH.x, min(bestSAH.y, bestSAH.z));

  if (bestSAH.x == minSAH) {
    return 0;
  }
  if (bestSAH.y == minSAH) {
    return 1;
  }
  return 2;
}

/* BVH Object Binning */

BVHObjectBinning::BVHObjectBinning(const BVHRange &job,
                                   BVHReference *prims,
                                   const BVHUnaligned *unaligned_heuristic,
                                   const Transform *aligned_space)
    : BVHRange(job),
      splitSAH(FLT_MAX),
      dim(0),
      pos(0),
      unaligned_heuristic_(unaligned_heuristic),
      aligned_space_(aligned_space)
{
  if (aligned_space_ == nullptr) {
    bounds_ = bounds();
    cent_bounds_ = cent_bounds();
  }
  else {
    /* TODO(sergey): With some additional storage we can avoid
     * need in re-calculating this.
     */
    bounds_ = unaligned_heuristic->compute_aligned_boundbox(
        *this, prims, *aligned_space, &cent_bounds_);
  }

  /* Clamp bin count to MAX_BINS; the 4 + 0.05*n heuristic balances
   * SAH accuracy against the O(n) binning cost. */
  num_bins = min(size_t(MAX_BINS), size_t(4.0f + 0.05f * size()));
  /* Precompute per-axis scale so that a centroid maps to [0, num_bins)
   * via: bin_idx = (centroid - min) * scale */
  scale = safe_divide(make_float3((float)num_bins), cent_bounds_.size());

  /* Initialize per-bin accumulators.  The second dimension of bin_bounds is
   * sized 4 (not 3) so that each row is 4-element aligned, which avoids
   * false sharing and keeps the per-dimension stride a power-of-two. */
  BoundBox bin_bounds[MAX_BINS][4]; /* bounds accumulated per bin, per axis (axes 0-2 used; [3] is alignment pad) */
  int4 bin_count[MAX_BINS];         /* primitive count per bin across all three axes (stored as int4) */

  for (size_t i = 0; i < num_bins; i++) {
    bin_count[i] = make_int4(0);
    bin_bounds[i][0] = bin_bounds[i][1] = bin_bounds[i][2] = BoundBox::empty;
  }

  /* Map each primitive to its bin for all three axes.  The loop is manually
   * unrolled by 2 so that the prefetch of the next cache line (8 prims
   * ahead) can overlap with the current iteration's binning work. */
  {
    int64_t prim_idx;

    for (prim_idx = 0; prim_idx < int64_t(size()) - 1; prim_idx += 2) {
      prefetch_L2(&prims[start() + prim_idx + 8]);

      /* Bin the even-indexed and odd-indexed primitives together to amortise
       * the loop overhead and hide memory latency via the prefetch above. */
      const BVHReference &prim0 = prims[start() + prim_idx + 0];
      const BVHReference &prim1 = prims[start() + prim_idx + 1];

      const BoundBox bounds0 = get_prim_bounds(prim0);
      const BoundBox bounds1 = get_prim_bounds(prim1);

      const int4 bin0 = get_bin(bounds0);
      const int4 bin1 = get_bin(bounds1);

      /* Accumulate the even primitive's bounds into its bins for each axis. */
      const int bin0_x = (int)extract<0>(bin0);
      bin_count[bin0_x][0]++;
      bin_bounds[bin0_x][0].grow(bounds0);
      const int bin0_y = (int)extract<1>(bin0);
      bin_count[bin0_y][1]++;
      bin_bounds[bin0_y][1].grow(bounds0);
      const int bin0_z = (int)extract<2>(bin0);
      bin_count[bin0_z][2]++;
      bin_bounds[bin0_z][2].grow(bounds0);

      /* Accumulate the odd primitive's bounds into its bins for each axis. */
      const int bin1_x = (int)extract<0>(bin1);
      bin_count[bin1_x][0]++;
      bin_bounds[bin1_x][0].grow(bounds1);
      const int bin1_y = (int)extract<1>(bin1);
      bin_count[bin1_y][1]++;
      bin_bounds[bin1_y][1].grow(bounds1);
      const int bin1_z = (int)extract<2>(bin1);
      bin_count[bin1_z][2]++;
      bin_bounds[bin1_z][2].grow(bounds1);
    }

    /* Handle the last primitive when the total count is odd. */
    if (prim_idx < int64_t(size())) {
      /* Map the remaining primitive to its bin for all three axes. */
      const BVHReference &prim0 = prims[start() + prim_idx];
      const BoundBox bounds0 = get_prim_bounds(prim0);
      const int4 bin0 = get_bin(bounds0);

      /* increase bounds of bins */
      const int bin0_x = (int)extract<0>(bin0);
      bin_count[bin0_x][0]++;
      bin_bounds[bin0_x][0].grow(bounds0);
      const int bin0_y = (int)extract<1>(bin0);
      bin_count[bin0_y][1]++;
      bin_bounds[bin0_y][1].grow(bounds0);
      const int bin0_z = (int)extract<2>(bin0);
      bin_count[bin0_z][2]++;
      bin_bounds[bin0_z][2].grow(bounds0);
    }
  }

  /* Right-to-left prefix sweep: for each candidate split plane i, accumulate
   * the merged bounding box and primitive count of all bins to the *right*
   * of the plane.  This gives the right-child SAH terms in O(n) rather than
   * recomputing them for every candidate during the left-to-right pass. */
  float4 right_half_area[MAX_BINS];  /* half-area of right-child merged bounds per axis */
  float4 right_prim_count[MAX_BINS]; /* block-rounded primitive count on the right per axis */
  int4 count = make_int4(0);

  /* Per-axis running bounding boxes for the right-side prefix. */
  BoundBox merged_bounds_x = BoundBox::empty;
  BoundBox merged_bounds_y = BoundBox::empty;
  BoundBox merged_bounds_z = BoundBox::empty;

  for (size_t bin_idx = num_bins - 1; bin_idx > 0; bin_idx--) {
    count = count + bin_count[bin_idx];
    right_prim_count[bin_idx] = blocks(count);

    merged_bounds_x = merge(merged_bounds_x, bin_bounds[bin_idx][0]);
    right_half_area[bin_idx][0] = merged_bounds_x.half_area();
    merged_bounds_y = merge(merged_bounds_y, bin_bounds[bin_idx][1]);
    right_half_area[bin_idx][1] = merged_bounds_y.half_area();
    merged_bounds_z = merge(merged_bounds_z, bin_bounds[bin_idx][2]);
    right_half_area[bin_idx][2] = merged_bounds_z.half_area();
    /* Duplicate Z into slot [3] so the float4 SAH multiply is fully populated. */
    right_half_area[bin_idx][3] = right_half_area[bin_idx][2];
  }

  /* Left-to-right SAH sweep: combine the left-side prefix (accumulated here)
   * with the pre-computed right-side prefix to evaluate SAH cost at every
   * candidate split plane simultaneously for all three axes via float4 ops. */
  int4 split_plane_idx = make_int4(1);  /* current candidate split plane index, per axis */
  float4 best_sah   = make_float4(FLT_MAX);
  int4   best_split = make_int4(-1);    /* bin index of the lowest-SAH split, per axis */

  count = make_int4(0);

  /* Reset left-side running bounding boxes for the forward sweep. */
  merged_bounds_x = BoundBox::empty;
  merged_bounds_y = BoundBox::empty;
  merged_bounds_z = BoundBox::empty;

  for (size_t bin_idx = 1; bin_idx < num_bins; bin_idx++, split_plane_idx += make_int4(1)) {
    /* Grow the left child's bounding box by all primitives in bin (bin_idx-1). */
    count = count + bin_count[bin_idx - 1];

    merged_bounds_x = merge(merged_bounds_x, bin_bounds[bin_idx - 1][0]);
    const float half_area_x = merged_bounds_x.half_area();
    merged_bounds_y = merge(merged_bounds_y, bin_bounds[bin_idx - 1][1]);
    const float half_area_y = merged_bounds_y.half_area();
    merged_bounds_z = merge(merged_bounds_z, bin_bounds[bin_idx - 1][2]);
    const float half_area_z = merged_bounds_z.half_area();

    /* SAH cost = left_area * left_count + right_area * right_count (all axes). */
    const float4 left_prim_count = blocks(count);
    const float4 left_half_area  = make_float4(half_area_x, half_area_y, half_area_z, half_area_z);
    const float4 sah = left_half_area * left_prim_count +
                       right_half_area[bin_idx] * right_prim_count[bin_idx];

    best_split = select(sah < best_sah, split_plane_idx, best_split);
    best_sah   = min(sah, best_sah);
  }

  /* Mask out axes whose centroid extent is zero — splitting along a flat
   * axis is meaningless and would produce degenerate children. */
  const int4 degenerate_axis_mask = make_float4(cent_bounds_.size()) <= zero_float4();
  best_sah = insert<3>(select(degenerate_axis_mask, make_float4(FLT_MAX), best_sah), FLT_MAX);

  /* Select the axis with the globally lowest SAH cost as the split dimension. */
  dim = get_best_dimension(best_sah);
  splitSAH = best_sah[dim];
  pos = best_split[dim];
  leafSAH = bounds_.half_area() * blocks(size());
}

void BVHObjectBinning::split(BVHReference *prims,
                             BVHObjectBinning &left_o,
                             BVHObjectBinning &right_o) const
{
  const size_t N = size();

  BoundBox lgeom_bounds = BoundBox::empty;
  BoundBox rgeom_bounds = BoundBox::empty;
  BoundBox lcent_bounds = BoundBox::empty;
  BoundBox rcent_bounds = BoundBox::empty;

  /* Two-pointer partition: move primitives whose bin index along `dim` is
   * below `pos` to the left partition, and the rest to the right partition,
   * swapping in-place to avoid extra allocation. */
  int64_t left_idx  = 0;
  int64_t right_idx = N - 1;

  while (left_idx <= right_idx) {
    prefetch_L2(&prims[start() + left_idx  + 8]);
    prefetch_L2(&prims[start() + right_idx - 8]);

    const BVHReference prim = prims[start() + left_idx];
    /* Use the aligned/unaligned bounds for the bin lookup (consistent with
     * how bins were built), but grow geometry bounds using the original
     * primitive AABB so the child node bounds remain tight. */
    const BoundBox aligned_prim_bounds = get_prim_bounds(prim);
    const float3   aligned_center      = aligned_prim_bounds.center2();
    const BoundBox geom_bounds         = prim.bounds();
    const float3   geom_center         = geom_bounds.center2();

    if (get_bin(aligned_center)[dim] < pos) {
      lgeom_bounds.grow(geom_bounds);
      lcent_bounds.grow(geom_center);
      left_idx++;
    }
    else {
      rgeom_bounds.grow(geom_bounds);
      rcent_bounds.grow(geom_center);
      swap(prims[start() + left_idx], prims[start() + right_idx]);
      right_idx--;
    }
  }
  /* If both partitions are non-empty the binning split succeeded; construct
   * child ranges from the accumulated bounds and return early. */
  if (left_idx != 0 && N - 1 - right_idx != 0) {
    right_o = BVHObjectBinning(
        BVHRange(rgeom_bounds, rcent_bounds, start() + left_idx, N - 1 - right_idx),
        prims,
        unaligned_heuristic_,
        aligned_space_);
    left_o = BVHObjectBinning(
        BVHRange(lgeom_bounds, lcent_bounds, start(), left_idx),
        prims,
        unaligned_heuristic_,
        aligned_space_);
    return;
  }

  /* Fallback: median object split.  This is reached only when all primitives
   * share the same centroid, making every SAH split degenerate.  We simply
   * cut the sorted array in half so recursion always terminates. */
  lgeom_bounds = BoundBox::empty;
  rgeom_bounds = BoundBox::empty;
  lcent_bounds = BoundBox::empty;
  rcent_bounds = BoundBox::empty;

  for (size_t prim_idx = 0; prim_idx < N / 2; prim_idx++) {
    /* Cache bounds to avoid calling bounds() twice per primitive. */
    const BoundBox prim_bounds = prims[start() + prim_idx].bounds();
    lgeom_bounds.grow(prim_bounds);
    lcent_bounds.grow(prim_bounds.center2());
  }

  for (size_t prim_idx = N / 2; prim_idx < N; prim_idx++) {
    /* Cache bounds to avoid calling bounds() twice per primitive. */
    const BoundBox prim_bounds = prims[start() + prim_idx].bounds();
    rgeom_bounds.grow(prim_bounds);
    rcent_bounds.grow(prim_bounds.center2());
  }

  /* Forward aligned_space_ and unaligned_heuristic_ so the child binning
   * passes use the same coordinate frame as this pass. */
  right_o = BVHObjectBinning(
      BVHRange(rgeom_bounds, rcent_bounds, start() + N / 2, N / 2 + N % 2),
      prims,
      unaligned_heuristic_,
      aligned_space_);
  left_o = BVHObjectBinning(
      BVHRange(lgeom_bounds, lcent_bounds, start(), N / 2),
      prims,
      unaligned_heuristic_,
      aligned_space_);
}

CCL_NAMESPACE_END