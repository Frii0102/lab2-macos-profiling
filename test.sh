#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
bash build.sh
for n in 1 3 15 16 17 1001; do
    for level in 0 3; do
        "./build/program_O$level" "$n" 3
    done
done
for level in 0 3; do
    for bad in 0 -1 abc 20000001; do
        if "./build/program_O$level" "$bad" 1 > /dev/null 2>&1; then
            echo "FAIL: invalid argument accepted: $bad"
            exit 1
        fi
    done
done
echo 'PASS: обидві версії перевіряють кожен результат; неправильні аргументи відхилено.'
