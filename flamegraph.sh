#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
[[ $# == 2 ]] || { echo 'Use: bash flamegraph.sh results/.../sample.txt O0'; exit 1; }
input=$1
name=$2
[[ "$name" == O0 || "$name" == O3 ]] || { echo 'Name must be O0 or O3'; exit 1; }
fg=tools/FlameGraph
[[ -f "$fg/stackcollapse-sample.awk" && -f "$fg/flamegraph.pl" ]] || {
    echo 'Спочатку: git clone https://github.com/brendangregg/FlameGraph.git tools/FlameGraph'
    exit 1
}
output=${FLAMEGRAPH_OUTPUT_DIR:-flamegraphs}
mkdir -p "$output"
awk -f "$fg/stackcollapse-sample.awk" "$input" > "$output/$name.folded"
[[ -s "$output/$name.folded" ]] || { echo 'No stacks found'; exit 1; }
perl "$fg/flamegraph.pl" --title "macOS sample — $name (fixed-duration observation)" \
    "$output/$name.folded" > "$output/$name.svg"
git -C "$fg" rev-parse HEAD > "$output/tool-commit.txt"
printf '%s\n' "$input" > "$output/$name-source.txt"
echo "Графік: $output/$name.svg"
