#!/usr/bin/env python3
"""tests/stress_wild_ab.dm's profile, per phase: DM ms a second (world.cpu) and the costliest parts with their calls.
    python3 tools/rts_feel/wild/ab_parts.py tests/swabp-g6-tick-profile.log"""
import re
import sys
from collections import defaultdict


def main(path):
    cur, agg = None, {}
    for line in open(path, errors='replace'):
        if line.startswith('STRESS|start|'):
            f = line.split('|')
            cur = f[2] + ' ' + f[3]
            agg[cur] = (defaultdict(float), defaultdict(float), [0, 0.0])
        elif line.startswith('STRESS|end|'):
            cur = None
        elif line.startswith('RMPROF|') and cur:
            ms, n, c = agg[cur]
            c[0] += 1
            c[1] += float(re.search(r'\|cpu=([0-9.]+)/', line).group(1))
            for part in line.strip().split('|')[-1].split(';'):
                if '=' not in part: continue
                k, v = part.rsplit('=', 1)
                a = v.split('/')
                if len(a) == 3:
                    ms[k] += float(a[0])
                    n[k] += float(a[1])
    for ph, (ms, n, c) in agg.items():
        top = sorted(ms, key=lambda k: -ms[k])[:5]
        print(f"{ph:<12} DM {c[1] / c[0] * 10:5.0f} ms/s | " + '  '.join(f"{k} {ms[k] / c[0]:.0f} ms {n[k] / c[0]:.0f}/s" for k in top))


if __name__ == '__main__':
    main(sys.argv[1])
