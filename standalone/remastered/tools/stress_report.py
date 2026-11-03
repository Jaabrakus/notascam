"""Sums up a stress run (tests/stress_check.dm via tools/check_arena.py --profile): for each army size and phase
(standing, moving, war), DM ms per tick (world.cpu), ticks over 100 ms, real seconds behind, the costliest parts, and the
memory report after it. python3 tools/stress_report.py tests/stress_check-checks-tick-profile.log"""
import re
import sys


def main(path):
    lines = open(path, errors='replace').read().splitlines()
    phases, current, mem = [], None, {}
    for line in lines:
        if line.startswith('STRESS|start|'):
            _, _, n, phase, t = line.split('|')[:5]
            current = dict(n=int(n), phase=phase, seconds=[])
            phases.append(current)
        elif line.startswith('STRESS|end|'):
            current = None
        elif line.startswith('STRESS|'):
            print(line)
        elif line.startswith('CK|memory'):
            m = re.match(r'CK\|memory, (\d+) units, after (\w+)\|\d\|(.*)', line)
            if m:
                d = dict(kv.split('=', 1) for kv in m.group(3).split('|') if '=' in kv)
                mem[(int(m.group(1)), m.group(2))] = d
        elif line.startswith('RMPROF|') and current is not None:
            head = line.split('|')
            f = dict(x.split('=', 1) for x in head[1:11] if '=' in x)
            parts = {}
            for p in head[-1].split(';'):
                if '=' not in p: continue
                k, v = p.rsplit('=', 1)
                a = v.split('/')
                if len(a) == 3: parts[k] = (float(a[0]), float(a[1]), float(a[2]))
            cpu = f.get('cpu', '0/0/0').split('/')
            current['seconds'].append(dict(cpu=float(cpu[0]), max=float(cpu[1]), over=int(cpu[2]), ticks=int(f.get('ticks', 10)),
                                           real=int(f.get('real', 10)), parts=parts))
    print(f"{'units':>6} {'phase':<9} {'DM ms/tick':>10} {'worst ms':>8} {'ticks>100':>9} {'behind s':>8} {'heap MB':>7} {'proc MB':>7}  costliest (ms a second)")
    for ph in phases:
        S = ph['seconds']
        if not S: continue
        avg = sum(s['cpu'] for s in S) / len(S)
        worst = max(s['max'] for s in S)
        over = sum(s['over'] for s in S)
        behind = sum(max(0, s['real'] - s['ticks']) for s in S) / 10
        tot = {}
        for s in S:
            for k, v in s['parts'].items():
                if '/' in k and not k.startswith('track'): pass
                tot[k] = tot.get(k, 0) + v[0]
        top = sorted(((v / len(S), k) for k, v in tot.items() if '/' not in k or k.count('/') == 0), reverse=True)[:5]
        m = mem.get((ph['n'], ph['phase']), {})
        print(f"{ph['n']:>6} {ph['phase']:<9} {avg:>10.1f} {worst:>8.0f} {over:>9} {behind:>8.1f} {m.get('heap MB', '?'):>7} {m.get('working set MB', '?'):>7}  "
              + ', '.join(f'{k} {v:.0f}' for v, k in top))


if __name__ == '__main__':
    main(sys.argv[1])
