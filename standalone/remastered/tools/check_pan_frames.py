#!/usr/bin/env python3
"""Panning into new land (world-look, 2026-10-24): what the 3D view's page spends a frame when the camera pans at
10 tiles/s over 300 tiles of land never drawn, then back over it (seen). The page's real code in headless Chrome on the
Mac's GPU and in a real WKWebView (the app's engine), fed the server's messages as Remaster3DTick sends them (the 45x35
terrain every 0.5 s, far cells, fog, a unit), no client and no input. Frames are paced at real 60 Hz.

  python3 tools/check_pan_frames.py [--engine chrome,webkit] [--runs 1] [--json OUT]

Per pass: CPU ms per frame (update3D + v3frame: median, 95th percentile, worst, frames over 16.7 ms) and the frames
over 12 ms with the page functions they spent time in. Chrome also checks that the far view and the horizon built a
few ms a frame (v3bgWork) are float for float what one build at once makes. WebKit's clock ticks in whole ms.
PASS: no pass has more than 2 frames over 16.7 ms, and the jobs equal the builds at once.
WORLDLOOK_HTML=<page> measures another copy of the page (as worldlook_replay.py). Exit status 1 on any failure.
Paced on purpose: frames pumped back to back let the GPU fall behind, and uploads then wait on it (100+ ms frames that
the real, display-paced loop does not see)."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import worldlook_replay as W   # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SWIFT = ROOT/'tools/worldlook_wkpan.swift'

# per-function time (calls, total, max) for the attribution of slow frames
TIMERS = r"""window.panTM={};['v3applyTerrain','v3buildFar','v3chunksWarm','v3meshesChunked','v3buildTerrain','v3heights','v3fogData','v3fogStamp','v3fogFrame','v3chunkBuild','v3horizon','v3terrainFx','v3meshes','v3depthField','v3roofs','v3chunkCtx','v3chunkSig','v3waterSurfaces','v3buildLiquids','v3bgWork'].forEach(n=>{const o=window[n];if(typeof o!=='function')return;window[n]=function(){const a=performance.now();const r=o.apply(this,arguments);const d=performance.now()-a;const T=panTM[n]||(panTM[n]={n:0,sum:0,max:0});T.n++;T.sum+=d;if(d>T.max)T.max=d;return r}});
window.panTMout=()=>Object.fromEntries(Object.entries(panTM).map(([k,v])=>[k,{n:v.n,total:+v.sum.toFixed(1),max:+v.max.toFixed(1)}]));
{const o=window.v3meshesChunked;window.panJoin=[];window.v3meshesChunked=function(){const a=performance.now();const b0=(panTM.v3chunkBuild||{sum:0}).sum;const r=o.apply(this,arguments);const d=performance.now()-a;panJoin.push([+d.toFixed(1),V3.chunkBuilt,+((panTM.v3chunkBuild||{sum:0}).sum-b0).toFixed(1),(V3.tgroups||new Map()).size]);return r}}"""

PAN = r"""// Pan probe (world-look): the camera pans at 10 tiles/s over 300 tiles of land never drawn, then back over it (seen),
// with the server's messages as Remaster3DTick sends them every 0.5 s: the 45x35 terrain round the camera, the far
// cells when it enters another 32-tile chunk, fog (explored bits and a sight circle), and one of your units walking
// with the camera. Frames are pumped by hand (16.7 ms apart) so Chrome and WKWebView run the same steps.
// Frames are paced at real 60 Hz (opts.paced=false pumps them back to back, which lets the GPU fall behind and makes
// uploads wait on it). Returns per-frame CPU (update3D + v3frame) for the two passes.
window.panProbe = async function (opts) {
  opts = opts || {};
  const K0 = window.replayData.terrain.kinds, base = window.replayData.things.find(t => t.kind === 'mine');
  const rock = {kind: 'wall', tex: 'r3d-0dfa3d7f092919d8b08643a2ab8bfd02.png', color: '#704c2a', state: 'cavewall', wood: 0, biome: null, vein: null, blocks: 3, roof: 0, under: null, road: null, ceil: 0, carve: null, dug: 0, hoard: 0};
  const kinds = K0.concat([rock]), KR = kinds.length;
  const idx = s => 1 + K0.findIndex(k => k.state === s && !k.biome);
  const GR = idx('grass'), DE = idx('desert'), SN = idx('snow'), TR = 1 + K0.findIndex(k => k.kind === 'tree' && k.state === 'tree 2x1'), WA = 1 + K0.findIndex(k => k.kind === 'water');
  const hh = (x, y, s) => { let n = (x * 374761393 + y * 668265263 + s * 2246822519) | 0; n = (n ^ (n >>> 13)) * 1274126177 | 0; return ((n ^ (n >>> 16)) >>> 0) / 4294967296; };
  const vn = (x, y, sc, s) => { const fx = x / sc, fy = y / sc, ix = Math.floor(fx), iy = Math.floor(fy), u = fx - ix, v = fy - iy, a = hh(ix, iy, s), b = hh(ix + 1, iy, s), c = hh(ix, iy + 1, s), d = hh(ix + 1, iy + 1, s), su = u * u * (3 - 2 * u), sv = v * v * (3 - 2 * v); return a + (b - a) * su + (c - a) * sv + (a - b - c + d) * su * sv; };
  const kindAt = (x, y) => { const m = vn(x, y, 23, 7), w = vn(x, y, 17, 3), tr = vn(x, y, 9, 5), bi = vn(x, y, 41, 11);
    if (m > 0.72) return KR; if (w < 0.2) return WA; if (tr > 0.66 && hh(x, y, 9) < 0.55) return TR; return bi < 0.3 ? DE : bi > 0.78 ? SN : GR; };
  const HW = 22, HH = 17, Y = 200, X0 = 200;
  const terr = (cx, cy) => { const x0 = cx - HW, y0 = cy - HH, w = 2 * HW + 1, h = 2 * HH + 1, tiles = new Array(w * h); for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) tiles[j * w + i] = kindAt(x0 + i, y0 + j); return {x0, y0, w, h, z: 1, tiles, kinds}; };
  const COL = {[GR]: '#3f6a34', [DE]: '#a08c5a', [SN]: '#c8d2d6', [TR]: '#2c4a28', [WA]: '#33607a', [KR]: '#6b665c'};
  const far = (cx, cy) => { const out = [], c0x = Math.floor((cx - 1) / 16), c0y = Math.floor((cy - 1) / 16); for (let b = c0y - 8; b <= c0y + 8; b++) for (let a = c0x - 10; a <= c0x + 10; a++) { const cells = []; for (let j = 0; j < 4; j++) for (let i = 0; i < 4; i++) cells.push(COL[kindAt(a * 16 + i * 4 + 2, b * 16 + j * 4 + 2)] || '#3f6a34'); out.push([a, b, cells, '1111111111111111']); } return out; };
  const explored = new Set();
  const fog = (T, ux, uy) => { let s = ''; for (let j = 0; j < T.h; j++) for (let i = 0; i < T.w; i++) { const x = T.x0 + i, y = T.y0 + j; if ((x - ux) * (x - ux) + (y - uy) * (y - uy) <= 144) explored.add(x * 4096 + y); s += explored.has(x * 4096 + y) ? '2' : '0'; } return {x0: T.x0, y0: T.y0, w: T.w, h: T.h, z: 1, s, c: [[ux, uy, 12, 'pan-unit']]}; };
  const unit = (x, y) => { const u = JSON.parse(JSON.stringify(base)); u.ref = u.id = 'pan-unit'; u.x = Math.round(x); u.y = Math.round(y); u.selected = 1; return u; };
  const msg = (cx, cy, withFar) => { const T = terr(cx, cy), m = {cx, cy, z: 1, things: [unit(cx, cy)], night: 0, dayp: 0.4, xray: 0, stack: 0, magic: 0, blueprints: [], build: null, terrain: T, fog: opts.fog === false ? 0 : fog(T, cx, cy)}; if (withFar) m.far = far(cx, cy); return m; };
  V3.iso = false; V3.dist = opts.dist || 13; V3.pitch = 0.62; V3.yaw = 0.35; V3.turnTo = null; V3.userTurn = performance.now() + 1e9;
  V3.tcx = V3.cx = X0; V3.tcy = V3.cy = Y; update3D(msg(X0, Y, true));
  let t = performance.now(); for (let k = 0; k < 60; k++) { t += 16.7; v3frame(t); }
  const pass = async (from, to) => { const F = [], U = [], dir = Math.sign(to - from), steps = Math.round(Math.abs(to - from) / 10 * 60); let lastChunk = null, sx = from;
    const T0 = performance.now();
    for (let k = 0; k <= steps; k++) { const x = from + dir * k * 10 / 60; V3.tcx = x; V3.panAt = performance.now();
      let u = 0; if (k % 30 === 0) { const cx = Math.round(x), ch = Math.floor((cx - 1) / 32); const a = performance.now(); update3D(msg(cx, Y, ch !== lastChunk)); u = performance.now() - a; lastChunk = ch; U.push(u); }
      const snap = window.panTM ? Object.fromEntries(Object.entries(panTM).map(([n, v]) => [n, v.sum])) : null;
      t += 16.7; const a = performance.now(); v3frame(t); const f = performance.now() - a; F.push(u + f);
      if (snap && u + f > 12) { const d = {}; for (const [n, v] of Object.entries(panTM)) { const x = v.sum - (snap[n] || 0); if (x > 0.5) d[n] = +x.toFixed(1); } (window.panSlow || (window.panSlow = [])).push([+(u + f).toFixed(1), +u.toFixed(1), d]); }
      if (opts.paced === false) { if (k % 6 === 0) await new Promise(r => setTimeout(r, 0)); } else { const due = T0 + (k + 1) * 16.7; await new Promise(r => setTimeout(r, Math.max(0, due - performance.now()))); } }
    const st = L => { const s = L.slice().sort((p, q) => p - q), q = f => +s[Math.min(s.length - 1, Math.floor(s.length * f))].toFixed(2); return {n: s.length, median: q(0.5), p95: q(0.95), worst: +s[s.length - 1].toFixed(2), over16: s.filter(v => v > 16.7).length}; };
    return {frame: st(F), update3D: st(U)}; };
  const fresh = await pass(X0, X0 + 300), seen = await pass(X0 + 300, X0);
  return {fresh, seen, chunksKept: V3.tchunks ? V3.tchunks.size : null};
};
"""

EQ = r"""// The far view and the horizon built a few ms a frame (jobs) against the same built at once: every float equal.
window.panEq = async function () {
  let t = performance.now(); const pump = async n => { for (let k = 0; k < n; k++) { t += 16.7; v3frame(t); if (k % 10 === 0) await new Promise(r => setTimeout(r, 0)); } };
  const until = async f => { for (let k = 0; k < 600 && !f(); k++) await pump(1); return f(); };
  const copy = va => Float32Array.from(va.f.subarray(0, va.length));
  const same = (A, B) => { if (A.length !== B.length) return {same: false, lenA: A.length, lenB: B.length}; let n = 0; for (let i = 0; i < A.length; i++) if (A[i] !== B[i] && !(A[i] !== A[i] && B[i] !== B[i])) n++; return {same: n === 0, floats: A.length, differ: n}; };
  await pump(30); await until(() => !V3.farJob && !V3.horJob && !V3.pendTerr);
  const out = {farData: (V3.farData || []).length};
  v3buildFar(); const deferred = !!V3.farJob; let frames = 0; while (V3.farJob && frames < 600) { await pump(1); frames++; }
  const A = copy(V3.farV), cA = V3.far[0] && V3.far[0].count, hA = V3.farH && Float32Array.from(V3.farH.H);
  v3buildFar(true); const B = copy(V3.farV), cB = V3.far[0] && V3.far[0].count, hB = V3.farH && Float32Array.from(V3.farH.H);
  out.far = Object.assign({deferred, frames, count: [cA, cB], heights: hA && hB ? same(hA, hB).same : null}, same(A, B));
  V3.hor.stale = true; await pump(1); const hdef = !!V3.horJob; frames = 0; while (V3.horJob && frames < 600) { await pump(1); frames++; }
  const C = copy(V3.horV), at = [V3.hor.x, V3.hor.z], cC = V3.hor.count;
  V3.gl.deleteBuffer(V3.hor.buf); V3.hor = null; v3horizon(at[0], at[1]); const D = copy(V3.horV);
  out.horizon = Object.assign({deferred: hdef, frames, count: [cC, V3.hor.count]}, same(C, D));
  return out;
};
"""

RESULT = "return JSON.stringify({r,timers:panTMout(),slow:(window.panSlow||[]).filter(s=>s[0]>16).slice(0,20),errs:window.__errs||[]})"


def chrome(runs):
    from playwright.sync_api import sync_playwright
    out = []
    with W.Server() as s, sync_playwright() as pw:
        for _ in range(runs):
            b, p, errs = W.browser(pw, 1440, 900)
            W.load(p, s.base + 'scene=1&dayp=0.4', settle=2500)
            p.evaluate('()=>{window.requestAnimationFrame=()=>0;return 0}')   # frames pumped by the probe only
            p.wait_for_timeout(300)
            p.evaluate(TIMERS + ';0'); p.evaluate(PAN + ';0'); p.evaluate(EQ + ';0')
            r = json.loads(p.evaluate('async()=>{const r=await panProbe({});r.eq=await panEq();' + RESULT + '}'))
            r['errs'] = r['errs'] + errs
            out.append(r)
            b.close()
    return out


def webkit(runs):
    exe = W.OUT/'wkpan'
    if not exe.exists() or exe.stat().st_mtime < SWIFT.stat().st_mtime:
        subprocess.run(['swiftc', '-O', str(SWIFT), '-o', str(exe)], check=True)
    body = ("for(let i=0;i<200&&!window.replayReady;i++)await new Promise(r=>setTimeout(r,100));await new Promise(r=>setTimeout(r,2500));"
            "window.requestAnimationFrame=()=>0;await new Promise(r=>setTimeout(r,300));\n" + TIMERS + '\n' + PAN + '\nconst r=await panProbe({});' + RESULT)
    (W.OUT/'wkpan-body.js').write_text(body)
    out = []
    with W.Server() as s:
        for _ in range(runs):
            res = subprocess.run([str(exe), s.base + 'scene=1&dayp=0.4', '1440', '900', str(W.OUT/'wkpan-body.js'), str(W.OUT/'wkpan.png'), '400'], capture_output=True, text=True, timeout=450)
            line = next((l for l in res.stdout.splitlines() if l.startswith('PROBE ')), None)
            if not line or not line[6:].startswith('{'):
                out.append({'errs': [res.stdout[-800:] + res.stderr[-400:]]}); continue
            r = json.loads(line[6:]); r['errs'] = r['errs'] + [l for l in res.stdout.splitlines() if l.startswith(('ERROR', 'console.error'))]
            out.append(r)
    return out


def ok(r):
    if r.get('errs') or 'r' not in r: return False
    if any(r['r'][k]['frame']['over16'] > 2 for k in ('fresh', 'seen')): return False
    e = r['r'].get('eq')
    return not e or (e['far']['same'] and e['far']['heights'] and e['horizon']['same'])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--engine', default='chrome,webkit')
    ap.add_argument('--runs', type=int, default=1)
    ap.add_argument('--json', type=Path)
    a = ap.parse_args()
    W.page()
    res = {}
    if 'chrome' in a.engine: res['chrome'] = chrome(a.runs)
    if 'webkit' in a.engine: res['webkit'] = webkit(a.runs)
    good = all(ok(r) for L in res.values() for r in L)
    for eng, L in res.items():
        for r in L:
            if 'r' in L[0] and 'r' in r:
                print(eng, json.dumps({k: r['r'][k]['frame'] for k in ('fresh', 'seen')}), 'eq' if r['r'].get('eq') else '', json.dumps(r['r'].get('eq')) if r['r'].get('eq') else '')
            else:
                print(eng, 'failed', r.get('errs'))
    if a.json: a.json.write_text(json.dumps(res, indent=1) + '\n')
    print('PASS' if good else 'FAIL')
    raise SystemExit(0 if good else 1)


if __name__ == '__main__':
    main()
