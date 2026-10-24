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
mkdir -p flamegraphs
awk -f "$fg/stackcollapse-sample.awk" "$input" > "flamegraphs/$name.folded"
[[ -s "flamegraphs/$name.folded" ]] || { echo 'No stacks found'; exit 1; }
perl "$fg/flamegraph.pl" --title "macOS sample — $name (fixed-duration observation)" \
    "flamegraphs/$name.folded" > "flamegraphs/$name.svg"
git -C "$fg" rev-parse HEAD > flamegraphs/tool-commit.txt
printf '%s\n' "$input" > "flamegraphs/$name-source.txt"
echo "Графік: flamegraphs/$name.svg"
