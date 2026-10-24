#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build assembly
for level in 0 3; do
    xcrun clang++ -std=c++17 -O"$level" -g -fno-omit-frame-pointer \
        main.cpp kernel.cpp -o "build/program_O$level"
    xcrun clang++ -std=c++17 -O"$level" -S kernel.cpp -o "assembly/kernel_O$level.s"
done
{
    sw_vers
    uname -m
    xcrun clang++ --version
} > assembly/build-environment.txt
echo "Готово: дві програми та два асемблерні файли."
