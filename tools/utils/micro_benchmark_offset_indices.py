#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Micro-benchmark offset count accumulation variants.

Builds and runs a tiny C++ benchmark for the serial prefix accumulation used by
`blender::offset_indices::accumulate_counts_to_offsets`. The benchmark prints
basic host information so results can be interpreted for the target runner.
"""

import argparse
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path


CPP_SOURCE = r'''
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <numeric>
#include <vector>

static void accumulate_index(std::vector<int> &counts_to_offsets)
{
  int offset = 0;
  const int64_t size = int64_t(counts_to_offsets.size());
  for (int64_t i = 0; i < size - 1; i++) {
    const int count = counts_to_offsets[i];
    counts_to_offsets[i] = offset;
    offset += count;
  }
  counts_to_offsets[size - 1] = offset;
}

static void accumulate_pointer(std::vector<int> &counts_to_offsets)
{
  int offset = 0;
  int *offsets = counts_to_offsets.data();
  int *const offsets_end = offsets + counts_to_offsets.size() - 1;
  for (; offsets != offsets_end; offsets++) {
    const int count = *offsets;
    *offsets = offset;
    offset += count;
  }
  *offsets = offset;
}

template<typename Fn>
static double bench(const char *name, Fn &&fn, const std::vector<int> &input, const int repeats)
{
  std::vector<int> data(input.size());
  int64_t checksum = 0;
  double best = 1.0e100;
  for (int repeat = 0; repeat < repeats; repeat++) {
    std::copy(input.begin(), input.end(), data.begin());
    const auto start = std::chrono::steady_clock::now();
    fn(data);
    const auto end = std::chrono::steady_clock::now();
    checksum += data[data.size() / 2] + data.back();
    const std::chrono::duration<double> duration = end - start;
    best = std::min(best, duration.count());
  }
  std::printf("%-16s %.6f s  %.2f GiB/s  checksum=%lld\n",
              name,
              best,
              double(input.size() * sizeof(int)) / best / (1024.0 * 1024.0 * 1024.0),
              static_cast<long long>(checksum));
  return best;
}

int main(int argc, char **argv)
{
  const int64_t size = argc > 1 ? std::atoll(argv[1]) : 20000000;
  const int repeats = argc > 2 ? std::atoi(argv[2]) : 9;
  std::vector<int> input(size + 1);
  for (int64_t i = 0; i < size; i++) {
    input[i] = int((i * 1103515245u + 12345u) % 4u) + 1;
  }
  input[size] = -1;

  std::printf("elements=%lld repeats=%d bytes=%.2f MiB\n",
              static_cast<long long>(input.size()),
              repeats,
              double(input.size() * sizeof(int)) / (1024.0 * 1024.0));
  const double index_time = bench("index", accumulate_index, input, repeats);
  const double pointer_time = bench("pointer", accumulate_pointer, input, repeats);
  std::printf("speedup %.3fx\n", index_time / pointer_time);
}
'''


def command_output(command):
    if not shutil.which(command[0]):
        return None
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.SubprocessError:
        return None


def print_host_info():
    print(f"system: {platform.system()} {platform.release()} {platform.machine()}")
    print(f"python: {platform.python_version()}")
    print(f"cpu_count: {os.cpu_count()}")
    lscpu = command_output(["lscpu"])
    if lscpu:
        for line in lscpu.splitlines():
            if line.startswith(("Architecture:", "Model name:", "CPU(s):", "Thread(s) per core:", "Core(s) per socket:")):
                print(line)
    free = command_output(["free", "-h"])
    if free:
        print(free)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cxx", default=os.environ.get("CXX", "c++"))
    parser.add_argument("--elements", type=int, default=20_000_000)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--keep-build-dir", action="store_true")
    args = parser.parse_args()

    print_host_info()

    with tempfile.TemporaryDirectory(prefix="offset_indices_bench_") as temp_dir:
        temp_path = Path(temp_dir)
        source = temp_path / "offset_indices_bench.cc"
        binary = temp_path / "offset_indices_bench"
        source.write_text(CPP_SOURCE)

        compile_cmd = [
            args.cxx,
            "-std=c++17",
            "-O3",
            "-DNDEBUG",
            "-march=native",
            str(source),
            "-o",
            str(binary),
        ]
        print("compile:", " ".join(compile_cmd))
        subprocess.check_call(compile_cmd)
        subprocess.check_call([str(binary), str(args.elements), str(args.repeats)])

        if args.keep_build_dir:
            kept_path = Path.cwd() / temp_path.name
            shutil.copytree(temp_path, kept_path)
            print(f"kept build directory: {kept_path}")


if __name__ == "__main__":
    main()
