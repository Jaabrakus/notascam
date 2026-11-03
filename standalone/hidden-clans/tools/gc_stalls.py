#!/usr/bin/env python3
"""Line up a tick_profile.py run's stalls with the engine's GC metrics (run it with --metrics PORT).

    python3 tools/gc_stalls.py LABEL

Reads reports/server-cost/LABEL-tick-profile.log (each game second's real time, rt, and its gaps of 0.3 s or more
between ticks) and LABEL-metrics.json (a scrape a second: collections by generation, GC pause time). For every second
with a gap, says which collections and how much pause time fell in the scrapes round it; then the totals."""
import json
from pathlib import Path
import re
import sys
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parents[1] / 'reports/server-cost'


def counts(m):
    gens, pause, pcount = {}, 0.0, 0.0
    for k, v in m.items():
        g = re.search(r'gen(?:eration)?="?(\d)', k)
        if ('collection_count' in k or 'collections_total' in k) and g and 'bucket' not in k:
            gens[g.group(1)] = gens.get(g.group(1), 0) + v
        if 'gc_pause_seconds_sum' in k: pause += v
        if 'gc_pause_seconds_count' in k: pcount += v
    return gens, pause, pcount


def main():
    label = sys.argv[1]
    rows = []
    for l in (OUT / f'{label}-tick-profile.log').read_text(errors='replace').splitlines():
        if not l.startswith('RMPROF|'): continue
        f = dict(kv.split('=', 1) for kv in l.split('|')[1:] if '=' in kv and ';' not in kv)
        st = f.get('stalls', '0/0/0').split('/')
        rows.append((int(f.get('rt', -1)), int(st[0]), float(st[1]), float(st[2])))
    scr = json.loads((OUT / f'{label}-metrics.json').read_text())
    series = []
    for t, m in scr:
        d = datetime.fromtimestamp(t, timezone.utc)
        ds = (d.hour * 3600 + d.minute * 60 + d.second + d.microsecond / 1e6) * 10   # world.timeofday's clock
        series.append((ds,) + counts(m))
    keys = sorted({g for s in series for g in s[1]})
    print('metrics seen:', sorted({k.split('{')[0] for _, m in scr for k in m})[:40])
    stalls = [r for r in rows if r[1]]
    hit = {'gen2': 0, 'gen1': 0, 'gen0 only': 0, 'none': 0}
    for rt, n, longest, cpu in stalls:
        # the scrapes in the 2.5 s before this game second's line (it covers the second that just ended)
        win = [s for s in series if rt - 25 <= s[0] <= rt + 5]
        if len(win) < 2:
            print(f'rt={rt}: no metrics round it'); continue
        a, b = win[0], win[-1]
        dg = {g: b[1].get(g, 0) - a[1].get(g, 0) for g in keys}
        dp = b[2] - a[2]
        kind = 'gen2' if dg.get('2') else 'gen1' if dg.get('1') else 'gen0 only' if dg.get('0') else 'none'
        hit[kind] += 1
        print(f'stall rt={rt} gaps={n} longest={longest / 10:.1f}s cpu_after={cpu:.0f}% | collections {dg} pause {dp * 1000:.0f} ms')
    first, last = series[0], series[-1]
    total = {g: last[1].get(g, 0) - first[1].get(g, 0) for g in keys}
    print(f'\n{len(stalls)} seconds with a gap; their GC: {hit}')
    print(f'whole run: collections {total}, GC pause total {(last[2] - first[2]) * 1000:.0f} ms in {last[3] - first[3]:.0f} pauses over {(last[0] - first[0]) / 10:.0f} s')


if __name__ == '__main__':
    main()
