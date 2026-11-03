#!/usr/bin/env python3
"""The page's unit glide (remastered.html v3frame, V3.disp), simulated at 60 frames a second on the positions the 3D view
is told (a server log from move_probe.dm), to measure what the player sees per variant of the pushes and the glide:
  now    pushes every 2 ticks + the scene every 5; glide = time since the last change seen (0.12..0.7 s)
  tick   pushes every tick
  gap    pushes every tick, the glide lasts the unit's real step gap (sent with the push)
  timed  pushes every tick with each unit's step time; drawn 120 ms behind, between the steps at their real times
  python3 tools/rts_feel/move/sim.py LOG [variants...]"""
import json, re, statistics as st, sys
from pathlib import Path
LOG = Path(sys.argv[1]); VARIANTS = sys.argv[2:] or ['now', 'tick', 'gap', 'timed']
runs = [json.loads(m) for m in re.findall(r'BK\|move [^|]*\|1\|(\{.*\})', LOG.read_text(errors='replace'))]
NET = 15        # ms from the server's tick to the page
FRAME = 1000/60

def arrivals(r, variant):
    """(page ms, x, y, step gap ticks, step tick) the page is told, in order"""
    S = r['steps']; out = []
    def pos(t):   # where the unit is after the steps of tick t
        p = None
        for s in S:
            if s[0] <= t: p = s
            else: break
        return p
    t0 = r['t0']; t1 = (S[-1][0] if S else t0) + 15
    for t in range(t0, t1 + 1):
        if variant == 'now':
            if t % 2 and t % 5: continue
        if variant == 'server':   # what the server really sent: its push samples, with the gap it logged (ms)
            o = next((o for o in r['obs'] if o[0] == t and o[3] == 'p'), None)
            if o and len(o) > 4: out.append(((t - t0)*100 + NET, o[1], o[2], o[4]/100 if o[4] else None, None))
            continue
        p = pos(t)
        if not p: continue
        i = S.index(p); gap = (p[0] - S[i-1][0]) if i else None
        if variant == 'gap' and (gap is None or gap > 3*r['delay']): gap = r['delay'] + 1   # a first step after standing: its own step time (server rule)
        out.append(((t - t0)*100 + NET, p[1], p[2], gap, p[0]))
    return out

def simulate(r, variant):
    A = arrivals(r, variant); S = r['steps']
    if not S: return []
    t0 = r['t0']; pre = [o for o in r['obs'] if o[0] < t0]; x0, y0 = (pre[-1][1], pre[-1][2]) if pre else (A[0][1], A[0][2])   # where it stood before the order
    k = dict(dx=x0, dy=y0, fx=x0, fy=y0, tx=x0, ty=y0, t0=0, dur=0.3, last=0)
    frames = []; ai = 0; tx, ty = x0, y0; gap = None
    hist = [((s[0] - t0)*100, s[1], s[2]) for s in S]   # for 'timed': steps at their server times
    known = []
    end = (S[-1][0] - t0)*100 + 1500; now = 0.0
    while now < end:
        while ai < len(A) and A[ai][0] <= now:
            _, tx, ty, gap, st_ = A[ai]
            if variant == 'timed' and (not known or known[-1][0] != (st_ - t0)*100): known.append(((st_ - t0)*100, tx, ty))
            ai += 1
        if variant == 'timed':
            rt = now - 120   # drawn a little behind, between known steps at their real times
            if not known: dx, dy = x0, y0
            else:
                j = max([i for i, h in enumerate(known) if h[0] <= rt], default=-1)
                if j < 0: dx, dy = (x0, y0) if rt < known[0][0] else known[0][1:]
                else:
                    h = known[j]; prev = known[j-1] if j else (h[0] - 500, x0, y0)
                    seg = max(100, h[0] - prev[0]) if j else 500
                    q = min(1, (rt - h[0])/seg) if False else None
                    # glide from the previous tile to this one over the step's own gap, starting at the step
                    gapms = (h[0] - prev[0]) if j else 500
                    q = min(1, max(0, (rt - h[0])/max(100, gapms)))
                    dx = prev[1] + (h[1] - prev[1])*q; dy = prev[2] + (h[2] - prev[2])*q
            frames.append((now, dx, dy)); now += FRAME; continue
        if k['tx'] != tx or k['ty'] != ty:
            if abs(k['dx'] - tx) > 3 or abs(k['dy'] - ty) > 3: k.update(dx=tx, fx=tx, tx=tx, dy=ty, fy=ty, ty=ty, dur=0.001)
            else:
                k.update(fx=k['dx'], fy=k['dy'], tx=tx, ty=ty)
                k['dur'] = max(0.12, min(1.5, gap/10)) if (variant in ('gap', 'server') and gap) else max(0.12, min(0.7, (now - k['last'])/1000))
            k['t0'] = now; k['last'] = now
        p = min(1, (now - k['t0'])/1000/k['dur']); k['dx'] = k['fx'] + (k['tx'] - k['fx'])*p; k['dy'] = k['fy'] + (k['ty'] - k['fy'])*p
        frames.append((now, k['dx'], k['dy'])); now += FRAME
    return frames

def metrics(r, F):
    S = r['steps']; t0 = r['t0']
    if len(S) < 3: return None
    w0 = (S[0][0] - t0)*100 + 150; w1 = (S[-1][0] - t0)*100
    F = [f for f in F if w0 <= f[0] <= w1 + 400]
    pauses = []; run = None; snaps = 0; back = 0; sp = []
    gx, gy = S[-1][1] - S[0][1], S[-1][2] - S[0][2]; gl = (gx*gx + gy*gy) ** 0.5 or 1
    for i in range(1, len(F)):
        dt = (F[i][0] - F[i-1][0])/1000; dx = F[i][1] - F[i-1][1]; dy = F[i][2] - F[i-1][2]; d = (dx*dx + dy*dy) ** 0.5
        if d > 0.3: snaps += 1
        if (dx*gx + dy*gy)/gl < -0.005: back += 1
        if d < 1e-5:
            run = F[i-1][0] if run is None else run
        else:
            if run is not None and F[i][0] - run > 150 and F[i][0] < w1: pauses.append(F[i][0] - run)
            run = None
            if F[i][0] < w1: sp.append(d/dt)
    mean = st.mean(sp) if sp else 0
    return dict(pauses=len(pauses), pause_max=max(pauses) if pauses else 0, snaps=snaps, back=back, cv=st.pstdev(sp)/mean if mean else 0,
                slow=sum(1 for s in sp if s < 0.5*mean)/len(sp) if sp else 0, mean=mean)

by = {}
for r in runs: by.setdefault(r['scene'], []).append(r)
out = {}
for v in VARIANTS:
    out[v] = {}
    for sc, group in by.items():
        M = [m for m in (metrics(r, simulate(r, v)) for r in group) if m]
        if not M: continue
        agg = dict(units=len(M), pauses_per_unit=round(sum(m['pauses'] for m in M)/len(M), 1), pause_max_ms=round(max(m['pause_max'] for m in M)),
                   snaps=sum(m['snaps'] for m in M), backtracks=sum(m['back'] for m in M), speed_cv=round(st.mean(m['cv'] for m in M), 2),
                   slow_frames=round(st.mean(m['slow'] for m in M), 2), tiles_per_s=round(st.mean(m['mean'] for m in M), 2))
        out[v][sc] = agg
        print(f'{v:6} {sc:17} ' + ' '.join(f'{k}={x}' for k, x in agg.items()))
print(json.dumps(out), file=open(LOG.with_name(LOG.stem.replace('server', 'sim') + '.json'), 'w'))
