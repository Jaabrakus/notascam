#!/usr/bin/env python3
"""Split a tick_profile.py --pan run into its legs (tests/tick_profile_probe.dm: the first leg into land the view hasn't
shown yet, the next back over land it has) and compare them: worst ticks, ticks over 100 ms, real time against ticks,
and each system's ms a game second, slowest call.

    python3 tools/pan_legs.py real-pan"""
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'reports/server-cost'


def main():
    label = sys.argv[1]
    lines = (OUT / f'{label}-tick-profile.log').read_text(errors='replace').splitlines()
    marks = [(int(re.search(r't=(\d+)', l).group(1)), l.split('|')[2]) for l in lines if l.startswith('TP|') and '|pan|' in l]
    rows = []
    for l in lines:
        if not l.startswith('RMPROF|'): continue
        head, _, body = l.rpartition('|')
        f = dict(kv.split('=', 1) for kv in head.split('|')[1:] if '=' in kv)
        systems = {}
        for part in body.split(';'):
            n, _, v = part.rpartition('=')
            systems[n] = [float(x) for x in v.split('/')]
        cpu = [float(x) for x in f['cpu'].split('/')]
        rows.append(dict(t=int(f['t']), ticks=int(f['ticks']), real=int(f['real']), cpu=cpu[0], worst=cpu[1], over=int(cpu[2]), sys=systems))
    if not marks:
        print('no pan marks'); return
    edges = [m[0] for m in marks] + [10 ** 9]
    names = ['into new land', 'back over seen land', 'into seen land again', 'back again']
    for i in range(len(edges) - 1):
        leg = [r for r in rows if edges[i] < r['t'] <= edges[i + 1]]
        if not leg: continue
        secs = len(leg)
        print(f"\n== leg {i + 1} ({names[i] if i < len(names) else ''}): {secs} game seconds; real {sum(r['real'] for r in leg) / 10:.1f} s for "
              f"{sum(r['ticks'] for r in leg) / 10:.0f} s of ticks; DM avg {sum(r['cpu'] for r in leg) / secs:.1f} ms a tick; "
              f"worst tick {max(r['worst'] for r in leg):.0f} ms; ticks over 100 ms: {sum(r['over'] for r in leg)}")
        keys = sorted({k for r in leg for k in r['sys']})
        tot = []
        for k in keys:
            ms = sum(r['sys'].get(k, [0, 0, 0])[0] for r in leg) / secs
            mx = max(r['sys'].get(k, [0, 0, 0])[2] for r in leg)
            n = sum(r['sys'].get(k, [0, 0, 0])[1] for r in leg) / secs
            tot.append((ms, k, n, mx))
        for ms, k, n, mx in sorted(tot, reverse=True)[:16]:
            print(f'   {k:32s} {ms:8.1f} ms/s  {n:7.1f} calls/s  slowest {mx:.0f} ms')


if __name__ == '__main__':
    main()
