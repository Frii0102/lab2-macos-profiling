"""Зведення реальних логів, лише стандартна бібліотека Python."""
import csv
import re
import statistics
import sys
from pathlib import Path

def parse(timing, output):
    values = dict(re.findall(r'(\w+)=([^\s]+)', output))
    if values.get('check') != 'OK' or values.get('mode') != 'fixed-work':
        raise ValueError('Need correct fixed-work results')
    row = {k: int(values[k]) for k in ('elements', 'repetitions', 'checksum')}
    for name in ('real', 'user', 'sys'):
        row[name] = float(re.search(r'([\d.]+) ' + name, timing)[1])
    row['kernel_seconds'] = float(values['kernel_seconds'])
    for key, label in (
        ('rss_bytes', 'maximum resident set size'),
        ('minor_faults', 'page reclaims'), ('major_faults', 'page faults'),
        ('voluntary_switches', 'voluntary context switches'),
        ('involuntary_switches', 'involuntary context switches'),
        ('instructions', 'instructions retired'), ('cycles', 'cycles elapsed'),
    ):
        match = re.search(r'^\s*(\d+)\s+' + label + r'\s*$', timing, re.M)
        row[key] = int(match[1]) if match else None
    row['ipc'] = row['instructions'] / row['cycles'] if row['instructions'] and row['cycles'] else None
    return row


def summarize(folder):
    data = []
    for level in (0, 3):
        for run in range(1, 6):
            row = parse((folder / f'O{level}-{run}-time.txt').read_text(),
                        (folder / f'O{level}-{run}-output.txt').read_text())
            data.append(dict(level=f'O{level}', run=run, **row))
    if len({(r['elements'], r['repetitions'], r['checksum']) for r in data}) != 1:
        raise ValueError('Workload or checksum differs: comparison rejected')
    with (folder / 'measurements.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    metrics = list(data[0])[5:]
    metrics = ['real', 'user', 'sys', 'kernel_seconds', 'rss_bytes', 'instructions',
               'cycles', 'ipc', 'minor_faults', 'major_faults', 'voluntary_switches',
               'involuntary_switches']
    medians = {}
    for level in ('O0', 'O3'):
        group = [r for r in data if r['level'] == level]
        medians[level] = {m: statistics.median([r[m] for r in group])
                          if all(r[m] is not None for r in group) else None for m in metrics}
    text = '# Зведення замірів\n\nДжерело: `' + folder.name + '`; медіани 5 запусків.\n\n'
    text += f"Однакова робота: {data[0]['elements']} чисел × {data[0]['repetitions']} повторень.\n\n"
    text += '| Показник | O0 | O3 |\n|---|---:|---:|\n'
    for m in metrics:
        vals = [medians[level][m] for level in ('O0', 'O3')]
        fmt = lambda v: 'недоступно' if v is None else (f'{v:.6f}' if isinstance(v, float) else str(v))
        text += f'| {m} | {fmt(vals[0])} | {fmt(vals[1])} |\n'
    text += f"\nПрискорення за real: {medians['O0']['real']/medians['O3']['real']:.2f}×. "
    text += f"За внутрішнім таймером: {medians['O0']['kernel_seconds']/medians['O3']['kernel_seconds']:.2f}×.\n"
    text += '\nIPC = instructions / cycles, спочатку для кожного запуску, потім медіана.\n'
    text += 'real/user/sys — секунди, rss_bytes — байти, решта лічильників — кількості.\n'
    text += 'real округлений time до 0,01 с; 0,00 sys не означає відсутність системної роботи.\n'
    text += 'Серія не вимірює cache misses чи branch misses і не замінює всі події perf stat -d.\n'
    (folder / 'summary.md').write_text(text)
    print(text)


if __name__ == '__main__':
    summarize(Path(sys.argv[1]))
