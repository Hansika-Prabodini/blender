# Changes

## Bug Fix: `ngon_tessellate` — incorrect consecutive-duplicate-vertex check

### File changed
`scripts/modules/bpy_extras/mesh_utils.py`

### What was wrong

`ngon_tessellate()` contains a pre-tessellation cleanup loop (active when
`fix_loops=False`) that is supposed to remove **consecutive duplicate vertices**
from the polygon before passing it to `tessellate_polygon`.

The original condition was:

```python
if verts[i][1] == verts[i - 1][0]:
```

`verts` is a list of `mathutils.Vector` objects, so `[0]` and `[1]` are the
**X** and **Y** components respectively.  
The condition therefore compared the **Y component of vertex `i`** against the
**X component of vertex `i-1`** — two completely unrelated values from
neighbouring vertices. This means:

| Situation | Outcome with bug |
|---|---|
| Two genuinely identical consecutive vertices (e.g. `(2, 7, 0)` twice) | **Not detected** (duplicate silently kept) |
| Two distinct consecutive vertices whose Y and X happen to be equal | **False positive** (valid vertex wrongly removed) |

Both failure modes corrupt the vertex list before tessellation, causing
`tessellate_polygon` to receive the wrong number of vertices and produce an
incorrect triangle count.

### The fix

```python
# Before (buggy)
if verts[i][1] == verts[i - 1][0]:

# After (correct)
if verts[i] == verts[i - 1]:
```

Comparing the full `Vector` objects with `==` correctly detects when two
consecutive vertices share the same position on all three axes.

---

## New test file
`tests/python/bl_pyapi_bpy_extras_mesh_utils.py`

A new `unittest`-based test module was added to cover the fixed behaviour.
Run it with:

```
./blender.bin --background --python tests/python/bl_pyapi_bpy_extras_mesh_utils.py -- --verbose
```

### Tests added

| Test | Description |
|---|---|
| `test_simple_quad_no_duplicates` | Baseline: a clean 4-vertex diamond polygon tessellates into exactly 2 triangles. |
| `test_quad_with_consecutive_duplicate_vertex` | Regression: the same polygon with one vertex duplicated consecutively (5 inputs) must still yield 2 triangles after dedup — **this test fails before the fix and passes after**. |

### Why the regression test works as a canary

The test uses coordinates where `y ≠ x` for every vertex
(e.g. `(2.0, 7.0, 0.0)`), so the buggy cross-component comparison
`y_i == x_{i-1}` cannot accidentally produce a true positive on
non-duplicate pairs. With the bug present, the real duplicate at index 1
is missed, the polygon retains 5 vertices, `tessellate_polygon` returns
3 triangles, and `assertEqual(len(result), 2)` fails. After the fix the
duplicate is removed, 4 vertices remain, and the assertion passes.
