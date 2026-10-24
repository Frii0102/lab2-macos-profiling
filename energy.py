"""Оцінка CPU+GPU+ANE енергії. Не вимірює весь ноутбук чи точні джоулі процесу.

Python працює як звичайний користувач. Лише powermetrics запускається через sudo.
Режим analyze повторно аналізує JSON без адміністративних прав.
"""
import argparse
import datetime
import json
import re
import statistics
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEADER = re.compile(r'\(([\d.]+)ms elapsed\)')
POWER = re.compile(r'^(CPU|GPU|ANE) Power:\s*([\d.]+)\s*(mW|W)\s*$', re.M)


def parse_block(text, received):
    match = HEADER.search(text)
    if not match:
        return None
    seconds = float(match[1]) / 1000
    powers = {kind: float(value) / (1000 if unit == 'mW' else 1)
              for kind, value, unit in POWER.findall(text)}
    if seconds <= 0 or set(powers) != {'CPU', 'GPU', 'ANE'}:
        return None  # Не вважаємо відсутній сенсор нульовою потужністю.
    return dict(start=received-seconds, end=received, duration=seconds,
                watts=sum(powers.values()), components_w= powers)


def integrate(samples, start, end):
    if end <= start:
        raise ValueError('Invalid measurement interval')
    energy = covered = 0.0
    cursor = start
    for sample in sorted(samples, key=lambda s: s['end']):
        lo = max(start, sample['start'], cursor)
        hi = min(end, sample['end'])
        if hi > lo:
            duration = hi-lo
            energy += sample['watts'] * duration
            covered += duration
            cursor = hi
    coverage = covered / (end-start)
    if coverage < 0.95:
        raise ValueError(f'Insufficient power coverage: {coverage:.1%}; do not report joules')
    return energy, coverage, covered


def analyze(folder):
    record = json.loads((folder / 'capture.json').read_text())
    samples = record['samples']
    rows = []
    for trial in record['trials']:
        baseline_e = baseline_t = 0
        for lo, hi in trial['baseline_windows']:
            energy, coverage, covered = integrate(samples, lo, hi)
            baseline_e += energy
            baseline_t += covered
        idle_w = baseline_e / baseline_t
        lo, hi = trial['work_window']
        energy, coverage, covered = integrate(samples, lo, hi)
        # Інтегруємо лише покриті інтервали; не вигадуємо даних у прогалинах.
        incremental = energy - idle_w * covered
        rows.append(dict(level=trial['level'], run=trial['run'], seconds=hi-lo,
                         coverage=coverage, covered_seconds=covered,
                         mean_w=energy/covered, subsystem_j=energy,
                         baseline_w=idle_w, incremental_j=incremental))
    text = '# Енергія: оцінка CPU + GPU + ANE\n\n'
    text += '**Не весь ноутбук. Не пряме вимірювання енергії окремого процесу.**\n\n'
    text += '| Версія | Запуск | Час, с | Покриття | Середня W | E підсистем, J | Фон, W | Приріст E, J |\n'
    text += '|---|---:|---:|---:|---:|---:|---:|---:|\n'
    for r in rows:
        text += (f"| {r['level']} | {r['run']} | {r['seconds']:.3f} | {r['coverage']:.1%} | "
                 f"{r['mean_w']:.3f} | {r['subsystem_j']:.3f} | {r['baseline_w']:.3f} | {r['incremental_j']:.3f} |\n")
    text += '\nМедіани приросту енергії:\n\n'
    medians = {}
    for level in ('O0', 'O3'):
        values = [r['incremental_j'] for r in rows if r['level'] == level]
        if values:
            medians[level] = statistics.median(values)
            text += f'- {level}: {medians[level]:.3f} J; діапазон {min(values):.3f}–{max(values):.3f} J.\n'
    if len(medians) == 2 and all(v > 0 for v in medians.values()):
        text += f"\nСпіввідношення O0/O3: {medians['O0']/medians['O3']:.2f}.\n"
    text += '\nE = Σ(P × Δt); приріст = E − P_фон × покритий час. Фон до та після кожного запуску.\n'
    text += ('Межі вибірок наближені за часом отримання заголовка логу і його elapsed_ms. '
             'Потужність усередині вибірки вважається сталою. Буферизація, планувальник, '
             'частоти, температура та фонові програми додають похибку. '
             'Оцінки powermetrics не відкалібровані ватметром.\n')
    text += ('Пропуски не заповнюються. Для звіту вказується покриття; нижче 95% аналіз відмовляється. '
             'Негативний приріст не приховується: потрібен повтор експерименту. '
             'Не порівнювати ці джоулі зі звичайною серією 2000 повторень: '
             'тут однакова між O0/O3, але довша задача, параметри у capture.json.\n')
    (folder / 'energy-summary.md').write_text(text)
    (folder / 'energy-results.json').write_text(json.dumps(rows, indent=2))
    print(text)


def capture(repetitions, runs):
    subprocess.run(['sudo', '-n', 'true'], check=True)
    for level in (0, 3):
        if not (ROOT / f'build/program_O{level}').is_file():
            raise RuntimeError('Спочатку bash build.sh')
    folder = ROOT / 'results' / ('energy-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    folder.mkdir(parents=True, exist_ok=False)
    record = dict(elements=1000000, repetitions=repetitions, samples=[], trials=[],
                  method='CPU+GPU+ANE, receive-time aligned intervals; incremental estimate')
    errorfile = (folder / 'powermetrics-errors.txt').open('w')
    command = ['sudo', '-n', '/usr/bin/powermetrics', '--samplers',
               'cpu_power,gpu_power,ane_power', '-i', '100', '-b', '1', '-n', '9000']
    power = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errorfile,
                             text=True, bufsize=1)
    reader_errors = []

    def reader():
        try:
            block, timestamp = [], None
            with (folder / 'powermetrics.txt').open('w') as log:
                for line in power.stdout:
                    now = time.monotonic()
                    log.write(line)
                    if HEADER.search(line):
                        if block and timestamp is not None:
                            value = parse_block(''.join(block), timestamp)
                            if value:
                                record['samples'].append(value)
                        block, timestamp = [line], now
                    elif timestamp is not None:
                        block.append(line)
                if block and timestamp is not None:
                    value = parse_block(''.join(block), timestamp)
                    if value:
                        record['samples'].append(value)
        except Exception as exc:
            reader_errors.append(str(exc))

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    def idle():
        begin = time.monotonic()
        time.sleep(5)
        return [begin, time.monotonic()]

    def healthy():
        if power.poll() is not None or reader_errors:
            raise RuntimeError('powermetrics stopped: inspect powermetrics-errors.txt')

    try:
        time.sleep(2)
        healthy()
        if not record['samples']:
            raise RuntimeError('CPU/GPU/ANE power format not recognized; raw log preserved')
        for run in range(1, runs+1):
            for level in ((0, 3) if run % 2 else (3, 0)):
                print(f'Енергія O{level}, серія {run}/{runs}. Не користуйся важкими програмами.', flush=True)
                # Однаковий короткий прогрів; не входить у вікно навантаження.
                subprocess.run([str(ROOT / f'build/program_O{level}'), '1000000', '10'],
                               stdout=subprocess.DEVNULL, check=True)
                time.sleep(3)
                before = idle()
                start = time.monotonic()
                proc = subprocess.run([str(ROOT / f'build/program_O{level}'), '1000000', str(repetitions)],
                                      capture_output=True, text=True, check=True, timeout=180)
                end = time.monotonic()
                (folder / f'O{level}-{run}-program.txt').write_text(proc.stdout + proc.stderr)
                if 'check=OK' not in proc.stdout:
                    raise RuntimeError('Program correctness check missing')
                after = idle()
                healthy()
                record['trials'].append(dict(level=f'O{level}', run=run,
                                            baseline_windows=[before, after], work_window=[start, end]))
        time.sleep(0.3)
    finally:
        if power.poll() is None:
            subprocess.run(['sudo', '-n', '/bin/kill', '-TERM', str(power.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            power.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print('Collector did not stop; inspect the powermetrics process locally.')
        thread.join(timeout=3)
        errorfile.close()
        # Навіть невдалий запуск зберігає фактичні дані, без намальованих чисел.
        (folder / 'capture.json').write_text(json.dumps(record, indent=2))
    analyze(folder)
    print(f'Готово: {folder / "energy-summary.md"}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analyze', type=Path)
    parser.add_argument('--repetitions', type=int, default=60000)
    parser.add_argument('--runs', type=int, default=3)
    args = parser.parse_args()
    if args.analyze:
        analyze(args.analyze)
    elif 20000 <= args.repetitions <= 100000 and 1 <= args.runs <= 5:
        capture(args.repetitions, args.runs)
    else:
        parser.error('repetitions: 20000..100000; runs: 1..5')
