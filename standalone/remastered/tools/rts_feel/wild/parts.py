#!/usr/bin/env python3
"""Every profiled part, ms a second, per stress phase, side by side for several tick-profile logs.
    python3 tools/rts_feel/wild/parts.py tests/A-tick-profile.log tests/B-tick-profile.log"""
import re
import sys
from collections import defaultdict


def phases(path):
    out, cur = {}, None
    for line in open(path, errors='replace'):
        line = line.rstrip('\n')
        if line.startswith('STRESS|start|'):
            _, _, n, ph = line.split('|')[:4]
            cur = f'{n} {ph}'
            out[cur] = defaultdict(float), [0]
        elif line.startswith('STRESS|end|'):
            cur = None
        elif line.startswith('RMPROF|') and cur:
            parts, cnt = out[cur]
            cnt[0] += 1
            head = line.split('|')
            f = dict(x.split('=', 1) for x in head[1:11] if '=' in x)
            parts['(DM cpu ms/s)'] += float(f.get('cpu', '0/0/0').split('/')[0]) * float(f.get('ticks', 10))
            for p in head[-1].split(';'):
                if '=' not in p: continue
                k, v = p.rsplit('=', 1)
                a = v.split('/')
                if len(a) == 3: parts[k] += float(a[0])
    return {k: ({p: v / max(1, c[0]) for p, v in d.items()}) for k, (d, c) in out.items()}


def main():
    logs = [phases(p) for p in sys.argv[1:]]
    for ph in logs[0]:
        print(f'== {ph}')
        keys = set()
        for L in logs: keys |= set(L.get(ph, {}))
        rows = sorted(keys, key=lambda k: -max(L.get(ph, {}).get(k, 0) for L in logs))
        for k in rows:
            vals = [L.get(ph, {}).get(k, 0) for L in logs]
            if max(vals) < 0.5: continue
            print(f'  {k:<42}' + ''.join(f'{v:9.1f}' for v in vals))


if __name__ == '__main__':
    main()
