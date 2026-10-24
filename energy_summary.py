"""Recompute summaries from saved measurements; no synthetic measurements."""
import argparse
import csv
import json
import re
import statistics
from pathlib import Path
from battery_energy import integral


def create(process_folder, battery_folders, output):
    process_rows, battery_rows = [], []
    for level in (0, 3):
        for run in range(1, 6):
            text = (process_folder / f'O{level}-{run}-energy.txt').read_text()
            program = (process_folder / f'O{level}-{run}-program.txt').read_text()
            meta = dict(re.findall(r'(\w+)=([^\s]+)', program))
            if (meta.get('check'), meta.get('elements'), meta.get('repetitions'), meta.get('checksum')) != ('OK','1000000','2000','1000000000'):
                raise ValueError('Inconsistent process workload')
            values = dict(re.findall(r'(\w+)=([^\s]+)', text))
            energy = int(values['energy_nj']) / 1e9
            seconds = float(values['seconds'])
            if energy <= 0 or seconds <= 0:
                raise ValueError('Invalid process energy/time')
            process_rows.append(dict(level=f'O{level}', run=run, seconds=seconds,
                                     energy_j=energy, average_accounted_w=energy/seconds))
    for folder in battery_folders:
        data = json.loads((folder / 'battery-capture.json').read_text())
        if (data['elements'], data['repetitions']) != (1000000, 200000):
            raise ValueError('Inconsistent battery workload')
        for trial in data['trials']:
            ew, tw = integral(trial['work'])
            eb, tb = integral(trial['before'])
            ea, ta = integral(trial['after'])
            baseline = (eb+ea)/(tb+ta)
            battery_rows.append(dict(level=trial['level'], run=trial['run'], source=folder.name,
                                     seconds=tw, energy_j=ew, average_w=ew/tw,
                                     baseline_before_w=eb/tb, baseline_after_w=ea/ta,
                                     incremental_j=ew-baseline*tw))
    if [sum(r['level'] == l for r in battery_rows) for l in ('O0','O3')] != [3,3]:
        raise ValueError('Expected three valid runs per version, including retry')
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in [('process',process_rows), ('battery',battery_rows)]:
        with (output / f'{name}.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
    text = '# Енерговимірювання: фактичні результати\n\n'
    text += '## 3.1. Уся система на виході батареї\n\n'
    text += 'Однакова задача O0/O3: 1 млн чисел × 200 000 повторень. P = −U(mV) × I(mA) / 10⁶ W; E = ∫P dt.\n\n'
    text += '| Версія | Серія | Час вибірок, с | Енергія батареї, J | Середня W | Фон до, W | Фон після, W | Приріст, J |\n'
    text += '|---|---|---:|---:|---:|---:|---:|---:|\n'
    for r in battery_rows:
        text += f"| {r['level']} | {r['source']}/{r['run']} | {r['seconds']:.3f} | {r['energy_j']:.3f} | {r['average_w']:.3f} | {r['baseline_before_w']:.3f} | {r['baseline_after_w']:.3f} | {r['incremental_j']:.3f} |\n"
    text += '\nУ першій серії O3/3 перервано через непридатне значення струму. Частковий запуск не включено; повтор збережено окремо. Інші результати, зокрема від’ємний приріст, НЕ відкинуті.\n'
    text += '\n## 3.2. CPU-енергія саме процесу за обліком macOS\n\n'
    text += f'Джерело: `{process_folder}`. Однакова задача: 1 млн чисел × 2000 повторень.\n\n'
    text += '`proc_pid_rusage(RUSAGE_INFO_V6)` → `ri_energy_nj / 10⁹`. Це облік CPU-енергії процесу в ОС, не вся енергія його непрямих наслідків, пам’яті, дисплея чи GPU.\n\n'
    text += '| Версія | Запуск | Час, с | CPU енергія, J | Середня облікована W |\n|---|---:|---:|---:|---:|\n'
    for r in process_rows:
        text += f"| {r['level']} | {r['run']} | {r['seconds']:.6f} | {r['energy_j']:.6f} | {r['average_accounted_w']:.3f} |\n"
    text += '\n## 4.4. Порівняння медіан\n\n'
    text += '| Межа вимірювання | O0, J | O3, J | O0/O3 | Зменшення |\n|---|---:|---:|---:|---:|\n'
    for label, rows in [('Батарея, 200 000 повторень', battery_rows), ('CPU процесу, 2000 повторень', process_rows)]:
        med = {l: statistics.median(r['energy_j'] for r in rows if r['level']==l) for l in ('O0','O3')}
        text += f"| {label} | {med['O0']:.6f} | {med['O3']:.6f} | {med['O0']/med['O3']:.2f}× | {(1-med['O3']/med['O0'])*100:.1f}% |\n"
    text += '\nЦі рядки НЕ віднімаємо й НЕ ділимо між собою: обсяг роботи та межі різні. Порівнюємо O0/O3 тільки всередині рядка.\n'
    text += '\n## Пояснення та межі\n\n'
    text += ('- O3 виконує менше інструкцій і швидше завершує ту саму задачу; у ньому підтверджено NEON. Це узгоджується зі зменшенням енергії.\n'
             '- Вища чи нижча миттєва потужність сама по собі не визначає енергію: важливий також час.\n'
             '- Батарейний датчик грубий, може усереднювати струм; межі запуску наближені до 0,5 с плюс затримка читання. Фон суттєво змінювався. Точність відсотків системної енергії обмежена.\n'
             '- Від’ємний приріст після віднімання фону показує непридатність цього способу для надійної ізоляції короткої O3 у цій серії. Він не є фізично від’ємною енергією. Для п.3.2 використовуємо окремий лічильник процесу.\n'
             '- ri_energy_nj — системний облік/оцінка CPU-енергії задачі, а не незалежний фізичний ватметр процесу. Фонові витрати всього комп’ютера до нього не додаються.\n'
             '- Нуль чи недоступний енерголічильник спричиняє помилку, а не фіктивні 0 J.\n')
    text += '\nДжерела Apple: [battery units](https://github.com/apple-oss-distributions/xnu/blob/main/iokit/IOKit/pwr_mgt/IOPMPowerSource.h), [rusage v6](https://developer.apple.com/documentation/kernel/rusage_info_current), [task accounting](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/kern/bsd_kern.c), [recount](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/kern/recount.c).\n'
    (output / 'summary.md').write_text(text)
    print(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--process', type=Path, required=True)
    parser.add_argument('--battery', nargs='+', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('results/energy-final'))
    args = parser.parse_args()
    create(args.process,args.battery,args.output)
