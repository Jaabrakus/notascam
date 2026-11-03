#!/usr/bin/env python3
"""The blocks being worked, highlighted yellow (ramps-gather 2026-10-25; the user: "we should see a yellow highlight of
what blocks are being worked on"). Each own unit's 3D record carries the block it is mining (wk, Plans.dm
RmWorkedBlock3D); the page draws one yellow mark per block on the rock's faces (pm_module.js pmWorked), kept until the
things, the ground or the camera's turn change. On world-look's mountain replay scene (tools/worldlook_replay.py), N of
your units mining a rock face each, none selected (so no order lines: only the worked blocks):
  - a still with 60 workers (worked-60.png);
  - the shadow check: V3.workCheck=1 builds the marks afresh each frame and compares, through still frames, units
    walking, the camera turning, a block mined out (new ground) and the targets changing; PASS when compared in every
    part and none differed;
  - CPU ms per frame (v3frame, 60 Hz pacing) with N = 0, 50, 200, the highlight on and off.
  python3 tools/plan_mode/worked_probe.py OUTDIR [--wk]     (--wk: the frame times in a real WKWebView too)"""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import worldlook_replay as W
from playwright.sync_api import sync_playwright

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
URL = 'scene=3&cx=64&cy=38&dist=13&pitch=0.62&yaw=0.75&dayp=0.3'
PROBE = r"""async (args) => {const [N, still, off] = args;
 window.requestAnimationFrame = () => 0;
 const d = JSON.parse(JSON.stringify(window.replayData)), cx = d.cx, cy = d.cy;
 const src = (window.__src = window.__src || d.things.filter(t => t.kind === 'mine' && (t.tex || t.texd)));
 const keep = d.things.filter(t => t.kind !== 'mine'), units = [], rock = [];
 for (let y = cy - 18; y <= cy + 18; y++) for (let x = cx - 24; x <= cx + 24; x++) { const g = V3.rockGeo && V3.rockGeo.get(x + ',' + y), K = v3kindAt(x, y); if (g && Array.isArray(g.s) && g.s.length && K && K.kind === 'wall') { const open = [[1,0],[-1,0],[0,1],[0,-1]].map(([a,b]) => [x + a, y + b]).find(([a,b]) => { const N2 = v3kindAt(a, b); return N2 && N2.kind !== 'wall' && N2.kind !== 'block' }); if (open) rock.push([x, y, open]) } }
 for (let i = 0; i < N && src.length && rock.length; i++) { const s = src[i % src.length], c = JSON.parse(JSON.stringify(s)), r = rock[i % rock.length]; c.ref = c.id = 'dig' + i; c.x = r[2][0]; c.y = r[2][1]; c.selected = 0; c.act = 'work'; if (!off) c.wk = [r[0], r[1], i % 3 === 2 ? 1 : 0]; units.push(c) }
 d.things = keep.concat(units);
 model = Object.assign(model || {}, {targets: [], z: d.z});
 if (rock.length) { const mx = rock.reduce((a, r) => a + r[0], 0) / rock.length, my = rock.reduce((a, r) => a + r[1], 0) / rock.length; V3.turnTo = null; V3.userTurn = 1e12; V3.panAt = 1e12; V3.tcx = V3.cx = mx; V3.tcy = V3.cy = my; V3.dist = 16 }
 update3D(JSON.stringify(d));
 let t = performance.now(); for (let k = 0; k < 60; k++) { t += 16.7; v3frame(t) }
 if (still) { const r = {rock: rock.length, units: units.length, worked: new Set(units.filter(u => u.wk).map(u => u.wk.join(','))).size, marks: window.PM && PM.wk ? PM.wk.keys.length : -1, verts: window.PM && PM.wk && PM.wk.v ? PM.wk.v.length : 0};
   // a selected unit's dig already outlines its rock in the orders' gold: no yellow on it too
   if (units.length) { const u = units[0]; model = Object.assign({}, model, {targets: [{x: u.wk[0], y: u.wk[1], z: d.z, kind: 'Mine', unit: u.ref, index: 0, blk: u.wk[2]}]}); v3frame(t += 16.7);
     r.outlined = PM.wk.keys.length; r.skipped = !PM.wk.keys.includes(u.wk.join(',')); model = Object.assign({}, model, {targets: []}); v3frame(t += 16.7); r.back = PM.wk.keys.length }
   return JSON.stringify(r) }
 const F = [], T0 = performance.now();
 for (let k = 0; k < 240; k++) { t += 16.7; const a = performance.now(); v3frame(t); F.push(performance.now() - a); const due = T0 + (k + 1) * 16.7; await new Promise(r => setTimeout(r, Math.max(0, due - performance.now()))) }
 const s = F.slice().sort((p, q) => p - q), q = f => +s[Math.min(s.length - 1, Math.floor(s.length * f))].toFixed(2);
 return JSON.stringify({N, rock: rock.length, median: q(0.5), p95: q(0.95), worst: +s[s.length - 1].toFixed(2)});
}"""
CHECK = r"""async () => {
 const P = """ + PROBE + r""";
 V3.workCheck = 1; await P([60, true, false]);
 const ck = () => { const C = V3.workCk || {checked: 0, differ: 0}; const r = [C.checked, C.differ]; V3.workCk = {checked: 0, differ: 0}; return r };
 let t = performance.now(); const fr = n => { for (let k = 0; k < n; k++) { t += 16.7; v3frame(t) } };
 const out = {}; ck();
 fr(30); out.still = ck();
 for (let s = 0; s < 6; s++) { const mv = []; for (const th of V3.things) if (th.ref && th.ref.startsWith('dig') && (s + th.x) % 3 === 0) mv.push([th.ref, th.x + (s % 2 ? 1 : -1), th.y, 2]); move3D(JSON.stringify(mv)); fr(10) } out.walking = ck();
 for (let s = 0; s < 40; s++) { V3.yaw += 0.03; V3.turnTo = null; fr(1) } fr(10); out.turning = ck();
 { const d = JSON.parse(JSON.stringify(window.replayData)), T = d.terrain, fk = T.kinds.findIndex(k => k.kind === 'floor') + 1, digs = V3.things.filter(x => x.ref && x.ref.startsWith('dig')); let n = 0;
   for (const u of digs) { if (n >= 3) break; const i = (u.wk[1] - T.y0) * T.w + (u.wk[0] - T.x0); if (i >= 0 && i < T.tiles.length) { T.tiles[i] = fk; n++ } }
   d.things = d.things.filter(x => x.kind !== 'mine').concat(digs.map(x => Object.assign({}, x))); update3D(JSON.stringify(d)); fr(30) } out.mined = ck();
 { const d = JSON.parse(JSON.stringify(window.replayData)); const digs = V3.things.filter(x => x.ref && x.ref.startsWith('dig')).map((x, i) => Object.assign({}, x, i % 2 ? {wk: null} : {wk: [x.wk[0], x.wk[1], x.wk[2] === 0 ? 1 : 0]}));
   d.terrain = undefined; d.things = d.things.filter(x => x.kind !== 'mine').concat(digs); update3D(JSON.stringify(d)); fr(30) } out.targets = ck();
 return JSON.stringify(out);
}"""
W.page()
ok = True
with W.Server() as s, sync_playwright() as pw:
    b, p, errs = W.browser(pw, 1440, 900)
    W.load(p, s.base + URL, settle=3000)
    st = json.loads(p.evaluate(PROBE, [60, True, False])); print('still', st)
    p.evaluate("v3frame(performance.now())")
    p.screenshot(path=str(out / 'worked-60.png'))
    if not (st['units'] == 60 and st['marks'] == st['worked'] and st['marks'] > 0 and st['verts'] > 0): ok = False; print('FAIL the still: every worked block marked once')
    if not (st.get('skipped') and st.get('back') == st['marks'] and st.get('outlined', 0) < st['marks']): ok = False; print('FAIL a selected unit\'s outlined dig should not get the yellow too')
    W.load(p, s.base + URL, settle=3000)
    r = json.loads(p.evaluate(CHECK))
    for k, v in r.items(): print(f'shadow {k:8s} compared {v[0]:5d}  differ {v[1]}')
    if not all(v[0] > 0 and v[1] == 0 for v in r.values()): ok = False; print('FAIL the shadow check')
    rows = []
    for off in (False, True):
        for n in (0, 50, 200):
            q = json.loads(p.evaluate(PROBE, [n, False, off])); q['highlight'] = 'off' if off else 'on'; rows.append(q); print('chrome', q)
    e = errs + p.evaluate('window.__errs||[]')
    if e: print('page errors', e[:3]); ok = False
    b.close()
(out / 'worked-frames.json').write_text(json.dumps(rows, indent=1))
if '--wk' in sys.argv:
    SWIFT = W.ROOT / 'tools/worldlook_wkpan.swift'
    exe = W.OUT / 'wkpan'
    if not exe.exists() or exe.stat().st_mtime < SWIFT.stat().st_mtime:
        subprocess.run(['swiftc', '-O', str(SWIFT), '-o', str(exe)], check=True)
    body = ("for(let i=0;i<200&&!window.replayReady;i++)await new Promise(r=>setTimeout(r,100));await new Promise(r=>setTimeout(r,2500));\n"
            "const P=" + PROBE + ";\nconst out=[];for(let rep=0;rep<2;rep++)for(const off of [false,true])for(const n of [0,200]){const r=JSON.parse(await P([n,false,off]));r.highlight=off?'off':'on';r.rep=rep;out.push(r)}"
            "\nreturn JSON.stringify({out,errs:window.__errs||[]})")
    (W.OUT / 'worked-body.js').write_text(body)
    W.page()
    with W.Server() as s:
        res = subprocess.run([str(exe), s.base + URL, '1440', '900', str(W.OUT / 'worked-body.js'), str(out / 'worked-wk.png'), '600'], capture_output=True, text=True, timeout=700)
    line = next((l for l in res.stdout.splitlines() if l.startswith('PROBE ')), '')
    if not line[6:].startswith('{'):
        print(res.stdout[-800:], res.stderr[-400:]); ok = False
    else:
        d = json.loads(line[6:])
        for q in d['out']: print('webkit', q)
        if d['errs']: print('webkit errors', d['errs'][:3]); ok = False
        (out / 'worked-frames-wk.json').write_text(json.dumps(d, indent=1))
print('PASS' if ok else 'FAIL')
