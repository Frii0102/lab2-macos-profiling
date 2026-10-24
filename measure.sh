#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
[[ -x build/program_O0 && -x build/program_O3 ]] || bash build.sh
n=${1:-1000000}
reps=${2:-2000}
out="results/time-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$out"
{
    sw_vers
    uname -m
    xcrun clang++ --version
    printf 'elements=%s repetitions=%s\n' "$n" "$reps"
} > "$out/environment.txt"
# Прогрів не включений у результати. Порядок версій чергується.
for level in 0 3; do "./build/program_O$level" "$n" 10 > /dev/null; done
for run in 1 2 3 4 5; do
    if (( run % 2 )); then order="0 3"; else order="3 0"; fi
    for level in $order; do
        /usr/bin/time -l "./build/program_O$level" "$n" "$reps" \
            > "$out/O$level-$run-output.txt" 2> "$out/O$level-$run-time.txt"
    done
done
echo "Результати: $out"
echo "Порівнюємо медіану п’яти real; kernel_seconds — лише обчислювальний цикл."
