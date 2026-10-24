#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
[[ -x build/process_energy ]] || bash build.sh
out="results/process-energy-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$out"
for level in 0 3; do ./build/program_O"$level" 1000000 10 > /dev/null; done
for run in 1 2 3 4 5; do
    if (( run % 2 )); then order="0 3"; else order="3 0"; fi
    for level in $order; do
        ./build/process_energy ./build/program_O"$level" 1000000 2000 \
            > "$out/O$level-$run-program.txt" 2> "$out/O$level-$run-energy.txt"
    done
done
echo "$out"
