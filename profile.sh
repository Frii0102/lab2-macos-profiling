#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
level=${1:-0}
[[ "$level" == 0 || "$level" == 3 ]] || { echo "Use: bash profile.sh 0 or 3"; exit 1; }
[[ -x "build/program_O$level" ]] || bash build.sh
out="results/profile-O$level-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$out"
# Однакові 12 секунд спостереження, але НЕ однакова кількість роботи!
"./build/program_O$level" 1000000 --seconds 12 > "$out/program.txt" &
pid=$!
trap 'kill "$pid" 2>/dev/null || true' EXIT
/usr/bin/sample "$pid" 10 2 -mayDie -file "$out/sample.txt" > "$out/sample-log.txt" 2>&1
wait "$pid"
trap - EXIT
echo "Профіль: $out/sample.txt"
