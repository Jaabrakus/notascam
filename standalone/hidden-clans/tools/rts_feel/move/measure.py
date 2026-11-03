#!/usr/bin/env python3
"""Unit movement smoothness (rts-feel 2026-10-23). 1) the server: tools/rts_feel/move/move_probe.dm in check_breaking's
arena logs each unit's steps and what the 3D pushes would carry; 2) the page: those pushes replayed in headless Chrome in
real time (1 tick = 100 ms) into move3D, each unit's drawn position recorded every frame; 3) metrics per scene.
  python3 tools/rts_feel/move/measure.py [--html PAGE] [--server-log FILE] [--tag NAME]"""
import argparse, json, re, statistics as st, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
ap = argparse.ArgumentParser()
ap.add_argument('--html', type=Path, default=ROOT/'game/Interface/remastered.html')
ap.add_argument('--server-log', type=Path, default=None, help='reuse a server log instead of running the arena')
ap.add_argument('--tag', default='now')
ap.add_argument('--overlay', default=None)
a = ap.parse_args()
OUT = ROOT/'reports/polish-2026-10-22/rts-feel/movement'; OUT.mkdir(parents=True, exist_ok=True)
log = a.server_log
if not log:
    cmd = ['python3', str(ROOT/'tools/check_breaking.py'), '--entry', 'RfMoveRun', '--extra', str(ROOT/'tools/rts_feel/move/move_probe.dm'), '--report', f'rts-move-{a.tag}-checks.json']
    if a.overlay: cmd += ['--overlay', a.overlay]
    subprocess.run(cmd, cwd=ROOT, capture_output=True)
    log = OUT/f'server-{a.tag}.log'
    log.write_text((ROOT/'tests/breaking-server.log').read_text(errors='replace'))
    for f in ROOT.glob(f'tests/rts-move-{a.tag}-checks.json'): f.rename(OUT/f.name)
runs = [json.loads(m) for m in re.findall(r'BK\|move [^|]*\|1\|(\{.*\})', log.read_text(errors='replace'))]
print(len(runs), 'unit walks from', log)

# ---- 2) the page: the pushes replayed in real time, each unit's drawn position every frame
from playwright.sync_api import sync_playwright
scene = json.loads((ROOT/'tests/lairs-dump-arena/lairs-3d-12.json').read_text())
model = json.loads((ROOT/'tests/idle-model-available.json').read_text())
model['view3d'] = 1; model['targets'] = []; model['hover'] = None; model['maxx'], model['maxy'] = 200, 200
def replay(group):
    """group: unit runs of one scene, played together. Returns {ref: [[ms, dx, dy], ...]} and the page-time of tick 0."""
    things = [t for t in scene['things'] if t['kind'] not in ('mine', 'npc', 'animal')]
    refs = []
    for r in group:
        ref = f"mv-{r['scene']}-{r['unit']}"; refs.append(ref)
        s0 = r['steps'][0] if r['steps'] else [0, r['end'][0], r['end'][1]]
        first = next((o for o in r['obs'] if o[0] >= r['t0']), None)
        x, y = (first[1], first[2]) if first else (s0[1], s0[2])
        things.append({'kind': 'mine', 'x': x, 'y': y, 'name': ref, 'dir': 2, 'act': 'idle', 'model': 'dwarf', 'ref': ref, 'tex': '', 'selected': 0, 'hp': 100})
    sc = dict(scene, things=things)
    T = scene['terrain']; cw = 14   # a small patch of ground only, so headless Chrome draws enough frames to measure
    cx0 = max(T['x0'], scene['cx'] - cw//2); cy0 = max(T['y0'], scene['cy'] - cw//2)
    sc['terrain'] = dict(T, x0=cx0, y0=cy0, w=cw, h=cw, tiles=[T['tiles'][(cy0 - T['y0'] + j)*T['w'] + (cx0 - T['x0'] + i)] for j in range(cw) for i in range(cw)])
    for k in ('far', 'farunits', 'fog'): sc.pop(k, None)
    t0 = min(r['t0'] for r in group); t1 = max((r['steps'][-1][0] if r['steps'] else r['t0']) for r in group) + 12
    ev = {}   # tick -> {ref: (x, y)}
    for r, ref in zip(group, refs):
        for o in r['obs']:
            if t0 <= o[0] <= t1: ev.setdefault(o[0], {})[ref] = [o[1], o[2], o[4] if len(o) > 4 else None]
    timeline = sorted(ev.items())
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        page_file = Path(tmp)/'p.html'; page_file.write_text(a.html.read_text(encoding='utf-8').replace('window.location.href=', 'window.testLastURL='), encoding='utf-8')
        b = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = b.new_page(viewport=dict(width=480, height=270)); pg.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
        pg.evaluate("()=>{window.send=function(){}}"); pg.evaluate('m=>updateHUD(m)', model); pg.evaluate('()=>v3set(true)'); pg.evaluate('s=>update3D(s)', sc)
        pg.wait_for_timeout(1500)
        res = pg.evaluate("""([timeline,refs,t0])=>new Promise(done=>{const rec={};for(const r of refs)rec[r]=[];const start=performance.now()+300;
          for(const [tick,pos] of timeline)setTimeout(()=>{const rows=Object.entries(pos).map(([ref,p])=>p[2]!=null?[ref,p[0],p[1],2,p[2]]:[ref,p[0],p[1],2]);move3D(JSON.stringify(rows))},start-performance.now()+(tick-t0)*100);
          const end=start+(timeline.length?timeline[timeline.length-1][0]-t0:0)*100+1500;
          (function f(){const now=performance.now();for(const t of V3.things)if(rec[t.ref])rec[t.ref].push([Math.round((now-start)*10)/10,+(t.dx??t.x).toFixed(4),+(t.dy??t.y).toFixed(4)]);if(now<end)requestAnimationFrame(f);else done(rec)})()})""", [timeline, refs, t0])
        b.close()
    return res, refs, t0

def metrics(r, frames, t0):
    """pauses over 150 ms while the unit is walking, snaps over 0.3 tile in a frame, backtracks, speed spread"""
    S = r['steps']
    if len(S) < 3 or len(frames) < 10: return None
    w0 = (S[0][0] - t0)*100; w1 = (S[-1][0] - t0)*100   # walking, in replay ms: first step to last step
    F = [f for f in frames if w0 + 150 <= f[0] <= w1]
    pauses = []; run = None; snaps = 0; back = 0; sp = []
    gx, gy = S[-1][1] - S[0][1], S[-1][2] - S[0][2]; gl = (gx*gx + gy*gy) ** 0.5 or 1
    for i in range(1, len(F)):
        dt = (F[i][0] - F[i-1][0])/1000; dx = F[i][1] - F[i-1][1]; dy = F[i][2] - F[i-1][2]; d = (dx*dx + dy*dy) ** 0.5
        if d > 0.3: snaps += 1
        if (dx*gx + dy*gy)/gl < -0.01: back += 1
        if d < 1e-4:
            run = run or F[i-1][0]
        else:
            if run is not None and F[i-1][0] - run > 150: pauses.append(F[i-1][0] - run)
            run = None
            if dt > 0: sp.append(d/dt)
    if run is not None and F[-1][0] - run > 150: pauses.append(F[-1][0] - run)
    mean = st.mean(sp) if sp else 0
    return {'pauses': len(pauses), 'pause_max_ms': round(max(pauses), 0) if pauses else 0, 'snaps': snaps, 'backtracks': back,
            'speed_mean': round(mean, 2), 'speed_cv': round(st.pstdev(sp)/mean, 2) if mean else None, 'slow_frames': round(sum(1 for s in sp if s < 0.5*mean)/len(sp), 2) if sp else None,
            'frames': len(F), 'fps': round(len(F)/((w1 - w0 - 150)/1000), 1) if w1 > w0 + 150 else None}

by = {}
for r in runs: by.setdefault(r['scene'], []).append(r)
report = {}
for sc, group in by.items():
    rec, refs, t0 = replay(group)
    M = [m for m in (metrics(r, rec[ref], t0) for r, ref in zip(group, refs)) if m]
    if not M: continue
    agg = {'units': len(M), 'pauses_per_unit': round(sum(m['pauses'] for m in M)/len(M), 1), 'pause_max_ms': max(m['pause_max_ms'] for m in M),
           'snaps': sum(m['snaps'] for m in M), 'backtracks': sum(m['backtracks'] for m in M), 'speed_cv': round(st.mean(m['speed_cv'] for m in M if m['speed_cv'] is not None), 2),
           'slow_frames': round(st.mean(m['slow_frames'] for m in M if m['slow_frames'] is not None), 2), 'fps': round(st.mean(m['fps'] for m in M if m['fps']), 1)}
    report[sc] = agg; print(sc, json.dumps(agg))
(OUT/f'metrics-{a.tag}.json').write_text(json.dumps(report, indent=1) + '\n')
