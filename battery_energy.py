"""Battery-side system energy estimate, not isolated process energy.

Uses documented Voltage (mV), Amperage (mA) from IOPMPowerSource.
Requires battery-only operation. Refuses low battery and stops on power changes.
No sudo required in an ordinary local Terminal.
"""
import argparse
import datetime
import json
import plistlib
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def reading():
    result = subprocess.run(['/usr/sbin/ioreg', '-r', '-c', 'AppleSmartBattery', '-a'],
                            capture_output=True, check=True, timeout=5)
    rows = plistlib.loads(result.stdout)
    if len(rows) != 1:
        raise ValueError('Expected one battery')
    d = rows[0]
    current = int(d['Amperage'])
    if current >= 2**63:
        current -= 2**64
    voltage = int(d['Voltage'])
    if d['ExternalConnected'] or d['IsCharging']:
        raise ValueError('Unplug charger only after charging to >=30%; battery-only measurement required')
    if current >= 0 or voltage <= 0:
        raise ValueError('No valid discharge reading')
    if d.get('AtCriticalLevel') or d.get('AtWarnLevel'):
        raise ValueError('Battery warning: charge first')
    percent = 100 * float(d['CurrentCapacity']) / float(d['MaxCapacity'])
    if percent < 20:
        raise ValueError('Battery below 20%: measurement refused. Charge to >=30% first.')
    return dict(t=time.monotonic(), millivolts=voltage, milliamps=current,
                watts=-voltage*current/1e6, battery_percent=percent)


def integral(samples):
    if len(samples) < 3:
        raise ValueError('Too few samples')
    energy = 0
    for a, b in zip(samples, samples[1:]):
        dt = b['t']-a['t']
        if not 0 < dt <= 3:
            raise ValueError('Sampling gap: reject energy estimate')
        energy += (a['watts']+b['watts'])/2*dt
    return energy, samples[-1]['t']-samples[0]['t']


def collect(seconds=None, process=None):
    samples = [reading()]
    start = samples[0]['t']
    while process.poll() is None if process else time.monotonic()-start < seconds:
        time.sleep(.5)
        samples.append(reading())
    return samples


def run(runs, only_level=None):
    first = reading()
    print(f"Battery {first['battery_percent']:.0f}%, discharge estimate {first['watts']:.2f} W", flush=True)
    folder = ROOT / 'results' / ('battery-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    folder.mkdir(parents=True, exist_ok=False)
    record = dict(method='Battery voltage × discharge current; trapezoidal integration',
                  repetitions=200000, elements=1000000, trials=[])
    process = None
    try:
        for run_id in range(1, runs+1):
            levels = (only_level,) if only_level is not None else ((0, 3) if run_id % 2 else (3, 0))
            for level in levels:
                print(f'O{level}, run {run_id}/{runs}: background → program → background', flush=True)
                before = collect(seconds=15)
                with (folder / f'O{level}-{run_id}-program.txt').open('w') as output:
                    begin = time.monotonic()
                    process = subprocess.Popen([str(ROOT / f'build/program_O{level}'), '1000000', '200000'],
                                               stdout=output, stderr=subprocess.STDOUT)
                    work = collect(process=process)
                    code = process.wait()
                    end = time.monotonic()
                if code:
                    raise ValueError(f'Program failed with {code}')
                if 'check=OK' not in (folder / f'O{level}-{run_id}-program.txt').read_text():
                    raise ValueError('Correctness check missing')
                after = collect(seconds=15)
                ew, tw = integral(work)
                eb, tb = integral(before)
                ea, ta = integral(after)
                if tw < 10:
                    raise ValueError('Work window too short for coarse battery telemetry')
                baseline = (eb+ea)/(tb+ta)
                record['trials'].append(dict(level=f'O{level}', run=run_id,
                    process_bounds=[begin,end], before=before, work=work, after=after,
                    sampled_seconds=tw, battery_side_j=ew, baseline_w=baseline,
                    incremental_estimate_j=ew-baseline*tw))
    finally:
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        (folder / 'battery-capture.json').write_text(json.dumps(record, indent=2))
    lines = ['# Battery-side energy estimate', '',
             'Coarse system-level estimate at the battery terminals; not wall power or exact process energy.', '',
             '| Version | Run | Sample window s | Battery energy J | Background W | Incremental estimate J |',
             '|---|---:|---:|---:|---:|---:|']
    for r in record['trials']:
        lines.append(f"| {r['level']} | {r['run']} | {r['sampled_seconds']:.3f} | {r['battery_side_j']:.3f} | {r['baseline_w']:.3f} | {r['incremental_estimate_j']:.3f} |")
    lines.extend(['', 'Amperage can be averaged/stale; polling faster does not increase sensor resolution.',
                  'Sampling window approximates process lifetime, with up to about one poll interval at boundaries.',
                  'Other apps, display, temperature, sensor lag and measurement overhead affect the result.',
                  'Negative incremental energy is retained, not hidden; repeat and inspect background drift.',
                  'No claim of exact attribution to the program. Do not mix with 2000-repeat time measurements.',
                  'Source: https://github.com/apple-oss-distributions/xnu/blob/main/iokit/IOKit/pwr_mgt/IOPMPowerSource.h'])
    (folder / 'battery-summary.md').write_text('\n'.join(lines)+'\n')
    print(folder / 'battery-summary.md')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--runs', type=int, choices=(1,2,3), default=3)
    parser.add_argument('--only-level', type=int, choices=(0,3), help='Retry one interrupted version; preserve original logs')
    args = parser.parse_args()
    if args.check:
        print(reading())
    else:
        run(args.runs, args.only_level)
