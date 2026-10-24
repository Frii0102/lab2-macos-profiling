#!/bin/bash
# Live demonstration; original report measurements are preserved.
set -euo pipefail
cd "$(dirname "$0")"
pause() { printf '\n%s\n' "$1"; read -r -p 'Натисни Enter, щоб продовжити… ' reply; }
pause '1. Покажи програму й поясни формулу.'
cat kernel.cpp
pause '2. Збираємо O0 та O3, перевіряємо однакові результати.'
bash build.sh
./build/program_O0 10 1
./build/program_O3 10 1
pause '3. Новий приклад time -l. Цифри можуть відрізнятися від збереженої серії.'
/usr/bin/time -l ./build/program_O0 1000000 2000
/usr/bin/time -l ./build/program_O3 1000000 2000
pause '4. Записуємо новий профіль O0, будуємо folded та SVG. Приблизно 12 секунд.'
message=$(bash profile.sh 0)
printf '%s\n' "$message"
source_path=${message#Профіль: }
[[ -f "$source_path" ]] || { echo 'Не знайдено профіль; перевір повідомлення вище.'; exit 1; }
demo_out="$(dirname "$source_path")/demo-graphs"
FLAMEGRAPH_OUTPUT_DIR="$demo_out" bash flamegraph.sh "$source_path" O0
printf '\nПочаток профілю:\n'
head -n 22 "$source_path"
printf '\nЗгорнуті стеки:\n'
head -n 8 "$demo_out/O0.folded"
open "$demo_out/O0.svg"
pause '5. Поясни новий SVG. Далі відкриються два збережені графіки для порівняння.'
open flamegraphs/O0.svg flamegraphs/O3.svg
pause '6. Асемблер O0, потім O3. Прокрути термінал до потрібних інструкцій.'
cat assembly/kernel_O0.s
cat assembly/kernel_O3.s
pause '7. Показуємо ЗБЕРЕЖЕНІ енергетичні результати. Новий батарейний тест не запускається.'
cat results/energy-final/summary.md
pause '8. Демонстрація завершена. Поясни висновки, покажи GitHub і зупини запис.'
