#!/usr/bin/env python3
"""GPU unit drawing (world-look, 2026-10-24, the user: "3D world look: GPU unit drawing"): what the 3D view's page spends a
frame with a crowd, and that the units look as they did.

  python3 tools/check_unit_frames.py frames [--engine chrome,webkit] [--units 200,2000,10000] [--walk 0.2] [--secs 8]
  python3 tools/check_unit_frames.py geometry [--old restore-points/page-before-gpu-units-20261024/remastered.html]

frames    N units cloned from the scene's own (their sprite sheets) spread over the 3D window, a share of them (--walk)
          stepping every 0.5 s through move3D, the whole update3D (a JSON string, as the client gets it) every 0.5 s.
          Frames pumped by hand at a real 60 Hz (headless Chrome on the Mac's GPU; WKWebView through
          tools/worldlook_wkpan.swift, on screen behind every window). CPU ms per frame (v3frame): median, 95th
          percentile, worst, frames over 16.7 ms; and per update3D / move3D. In Chrome the replay page's own frame wrapper
          (performance.memory) adds about 1.5 ms at 10,000 units; WebKit has no such counter, and ticks in whole ms.
geometry  (--new PAGE: check that page; --old-records: the old page draws records too, both read as records)
          Six scenes (some units hurt, selected, foes), three frames each (the last from the record cache): the old
          page's triangles for the units' pictures, silhouettes, cast and contact shadows and rings, against the new
          page's records spread into triangles by v3instTris (the corners the vertex shader builds). PASS when every
          triangle matches (to 1e-4; cast shadows round differently in the 4th decimal, so they get 2e-4). The huge
          beasts' sheets (rb-*) are left out: they are drawn as before, and fly on the clock.
WORLDLOOK_HTML=<page> measures another copy of the page (frames). Exit status 1 on any failure."""
import argparse
import collections
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import worldlook_replay as W   # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SWIFT = ROOT/'tools/worldlook_wkpan.swift'
OLD = ROOT/'restore-points/page-before-gpu-units-20261024/remastered.html'

CROWD = r"""// Crowd probe (world-look, GPU unit drawing): N units spread over the 3D window round the camera, cloned from the
// scene's own units (their sprite sheets), a fifth of them taking a step every 0.5 s through move3D (the server's
// moves push), the whole update3D (as a JSON string, as the client gets it) every 0.5 s. Frames pumped by hand at a
// real 60 Hz. Returns CPU ms per frame (v3frame alone) and per update3D / move3D.
window.crowdProbe = async function (N, secs, opts) {
  opts = opts || {};
  const d = JSON.parse(JSON.stringify(window.replayData));
  const src = d.things.filter(t => t.kind === 'mine' && (t.tex || t.texd));
  const others = d.things.filter(t => t.kind !== 'mine' && t.kind !== 'npc' && t.kind !== 'player' && t.kind !== 'animal');
  const cx = d.cx, cy = d.cy, HW = opts.hw || 22, HH = opts.hh || 17;
  let seed = 7; const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  const units = [];
  for (let i = 0; i < N; i++) { const s = src[i % src.length], c = JSON.parse(JSON.stringify(s)); c.ref = c.id = 'crowd' + i; c.x = Math.round(cx - HW + rnd() * 2 * HW); c.y = Math.round(cy - HH + rnd() * 2 * HH); c.selected = i < 12 ? 1 : 0; c.hp = i % 7 === 0 ? 60 : 100; if (i % 5 === 4) { c.kind = 'npc'; c.peace = 0 } units.push(c) }
  d.things = others.concat(units);
  V3.dist = opts.dist || 30; V3.pitch = 0.62; V3.yaw = 0.35; V3.turnTo = null; V3.userTurn = performance.now() + 1e9; V3.tcx = V3.cx = cx; V3.tcy = V3.cy = cy; V3.panAt = performance.now() + 1e9;
  const send = () => { const a = performance.now(); update3D(JSON.stringify(d)); return performance.now() - a };
  send();
  let t = performance.now(); for (let k = 0; k < 90; k++) { t += 16.7; v3frame(t); if (k % 10 === 0) await new Promise(r => setTimeout(r, 0)) }
  const F = [], U = [], M = [], steps = Math.round(secs * 60), T0 = performance.now();
  for (let k = 0; k < steps; k++) {
    if (k % 30 === 15) { const mv = []; for (const u of units) if (rnd() < (opts.walk == null ? 0.2 : opts.walk)) { u.x += rnd() < 0.5 ? 1 : -1; mv.push([u.ref, u.x, u.y, 2]) } const a = performance.now(); move3D(JSON.stringify(mv)); M.push(performance.now() - a) }
    if (k % 30 === 0) U.push(send());
    t += 16.7; const a = performance.now(); v3frame(t); F.push(performance.now() - a);
    const due = T0 + (k + 1) * 16.7; await new Promise(r => setTimeout(r, Math.max(0, due - performance.now())));
  }
  const st = L => { const s = L.slice().sort((p, q) => p - q), q = f => +s[Math.min(s.length - 1, Math.floor(s.length * f))].toFixed(2); return {n: s.length, median: q(0.5), p95: q(0.95), worst: +s[s.length - 1].toFixed(2), over16: s.filter(v => v > 16.7).length} };
  return {N, things: V3.things.length, frame: st(F), update3D: st(U), move3D: st(M), json_kb: Math.round(JSON.stringify(d).length / 1024)};
};
"""

SCENES = {'village': 'scene=1&cx=41&cy=31&dist=9&pitch=0.62&yaw=0.35&dayp=0.4', 'village-far': 'scene=1&cx=41&cy=31&dist=20&pitch=0.7&yaw=0.9&dayp=0.3',
          'night': 'scene=1&cx=40&cy=30&dist=8&pitch=0.55&yaw=0.2&night=1', 'beasts': 'scene=6&cx=43&cy=31&dist=15&pitch=0.62&yaw=0.35&dayp=0.25',
          'forest': 'scene=5&cx=14&cy=47&dist=12&pitch=0.6&yaw=-0.3&dayp=0.45', 'top': 'scene=1&cx=41&cy=31&dist=14&pitch=1.15&yaw=0.35&dayp=0.45'}
SETUP = r"""(()=>{window.requestAnimationFrame=()=>0;const q=new URLSearchParams(location.search);V3.turnTo=null;V3.userTurn=1e12;V3.panAt=1e12;V3.dist=+q.get('dist');V3.yaw=+q.get('yaw');V3.pitch=+q.get('pitch');V3.tcx=V3.cx=+q.get('cx');V3.tcy=V3.cy=+q.get('cy');V3.iso=false;const d=window.replayData;let i=0;const hp=[100,82,55,30,12,100,64,40,75];
 for(const t of d.things){if(t.kind!=='mine'&&t.kind!=='npc')continue;t.hp=hp[i%hp.length];if(i%4===3&&t.kind==='mine'){t.kind='npc';t.peace=0}t.selected=t.kind==='mine'&&i%3===0?1:0;i++}
 update3D(d);let t=2e6;for(let k=0;k<150;k++){t+=16.7;v3frame(t)}return i})()"""
DUMP = r"""((isNew)=>{const r4=v=>Math.round(v*1e4)/1e4,tris=(f,n)=>{const out=[];for(let o=0;o+36<=n;o+=36){const vs=[];for(let k=0;k<3;k++){const b=o+k*12;vs.push([f[b],f[b+1],f[b+2],f[b+6],f[b+7],f[b+8],f[b+9],f[b+10],f[b+11]].map(r4).join(','))}vs.sort();out.push(vs.join('|'))}return out};
 const VA2=a=>tris(a.f,a.length),S=V3.vaS,out={pic:{},cast:{},sil:{},contact:[],rings:[]};
 const spread=(a,mode)=>{if(mode!==4)return VA2(v3instTris(a,mode));const res=[];for(let i=0;i<a.length;i+=12){const f=a.f;if(f[i+4]===0&&f[i+5]===1){const X=f[i],y=f[i+1],Z=f[i+2],r=f[i+3],q=new VA();quad(q,[X-r,y,Z+r],[X+r,y,Z+r],[X+r,y,Z-r],[X-r,y,Z-r],[0,0,0],[f[i+8],f[i+9],f[i+10],f[i+11]],[0,1,1,1,1,0,0,0]);res.push(...VA2(q))}else{const one=new VA();one.v(...Array.from(f.subarray(i,i+12)));res.push(...VA2(v3instTris(one,4)))}}return res};
 if(isNew){for(const [k,a] of V3.vaI)if(a.length)out.pic[k]=spread(a,1);for(const [k,a] of S.castG)if(a.length)out.cast[k]=spread(a,2);for(const [k,a] of S.castB)if(a.length)out.cast[k]=(out.cast[k]||[]).concat(VA2(a));for(const [k,a] of S.sil)if(a.length)out.sil[k]=spread(a,1);out.contact=spread(S.contact,3);out.rings=spread(S.rings,4)}
 else{for(const [k,a] of V3.vaG)if(a.length&&k)out.pic[k]=VA2(a);for(const [k,a] of S.castG)if(a.length)out.cast[k]=VA2(a);for(const [k,a] of S.sil)if(a.length)out.sil[k]=VA2(a);out.contact=VA2(S.contact);out.rings=VA2(S.rings)}
 return JSON.stringify(out)})"""


def frames_chrome(Ns, secs, walk):
    from playwright.sync_api import sync_playwright
    out = []
    with W.Server() as s, sync_playwright() as pw:
        for n in Ns:
            b, p, errs = W.browser(pw, 1440, 900)
            W.load(p, s.base + 'scene=1&dayp=0.4', settle=2500)
            p.evaluate('()=>{window.requestAnimationFrame=()=>0;return 0}')
            p.wait_for_timeout(300)
            p.evaluate(CROWD + ';0')
            r = json.loads(p.evaluate(f'async()=>JSON.stringify(await crowdProbe({n},{secs},{{walk:{walk}}}))'))
            r['errors'] = errs + p.evaluate('window.__errs||[]')
            out.append(r)
            b.close()
    return out


def frames_webkit(Ns, secs, walk):
    exe = W.OUT/'wkpan'
    if not exe.exists() or exe.stat().st_mtime < SWIFT.stat().st_mtime:
        subprocess.run(['swiftc', '-O', str(SWIFT), '-o', str(exe)], check=True)
    body = ("for(let i=0;i<200&&!window.replayReady;i++)await new Promise(r=>setTimeout(r,100));await new Promise(r=>setTimeout(r,2500));"
            "window.requestAnimationFrame=()=>0;await new Promise(r=>setTimeout(r,300));\n" + CROWD +
            "\nconst out=[];for(const n of [" + ','.join(map(str, Ns)) + "])out.push(await crowdProbe(n," + str(secs) + ",{walk:" + str(walk) + "}));return JSON.stringify({out,errs:window.__errs||[]})")
    (W.OUT/'units-body.js').write_text(body)
    with W.Server() as s:
        res = subprocess.run([str(exe), s.base + 'scene=1&dayp=0.4', '1440', '900', str(W.OUT/'units-body.js'), str(W.OUT/'units.png'), '900'], capture_output=True, text=True, timeout=960)
    line = next((l for l in res.stdout.splitlines() if l.startswith('PROBE ')), '')
    if not line[6:].startswith('{'): return [{'errors': [res.stdout[-600:] + res.stderr[-300:]]}]
    d = json.loads(line[6:])
    for r in d['out']: r['errors'] = d['errs']
    return d['out']


WALK = r"""(()=>{const mv=[];let i=0;for(const t of V3.things){if(!(t.kind==='mine'||t.kind==='npc')||!t.ref)continue;if(i++%2)continue;mv.push([t.ref,t.x+(i%4?1:-1),t.y,i%4?4:8])}move3D(JSON.stringify(mv));return mv.length})()"""


SHEETS = r"""(()=>{let n=0,ok=0;for(const t of V3.things)if(Array.isArray(t.texd))for(const k of t.texd)if(k){n++;const e=v3tex(k);if(e&&e.ok)ok++}if(typeof v3bgWork==='function')v3bgWork(50);return [n,ok]})()"""


def geometry(old_html, new_html=None, old_records=False, walk=False):
    from playwright.sync_api import sync_playwright
    def run(html, isnew):
        os.environ['WORLDLOOK_HTML'] = str(html)
        W.page(); res = {}
        with W.Server() as s, sync_playwright() as pw:
            b, p, errs = W.browser(pw, 1440, 900)
            for name, q in SCENES.items():
                W.load(p, s.base + q, settle=2500); p.evaluate(SETUP); p.evaluate('()=>{v3frame(3e6);v3frame(3e6+16.7);v3frame(3e6+33.4);return 0}')
                res[name] = json.loads(p.evaluate(DUMP, isnew))
                if walk:   # half the units step a tile; the frames along the step, at the same times on both pages
                    for _ in range(80):   # every facing's sheet loaded first, or a turn draws the old sheet for a load's while
                        n, ok = p.evaluate(SHEETS)
                        if ok >= n: break
                        p.wait_for_timeout(100)
                    p.evaluate(WALK)
                    for k in range(1, 13):
                        p.evaluate(f'()=>{{v3frame(3e6+33.4+{k}*16.7);return 0}}')
                        if k % 3 == 0: res[f'{name}@walk{k}'] = json.loads(p.evaluate(DUMP, isnew))
            res['errors'] = errs + p.evaluate('window.__errs||[]')
            b.close()
        return res
    old, new = run(old_html, old_records), run(new_html or ROOT/'game/Interface/remastered.html', True)
    os.environ.pop('WORLDLOOK_HTML', None)
    def near(a, b, tol):
        A, B = [list(map(float, v.split(','))) for v in a.split('|')], [list(map(float, v.split(','))) for v in b.split('|')]
        return all(abs(x - y) <= tol for va, vb in zip(A, B) for x, y in zip(va, vb))
    out, ok = {}, not old['errors'] and not new['errors']
    for name in [k for k in new if k != 'errors']:
        O, N, row = old[name], new[name], {}
        for part in ('pic', 'cast', 'sil', 'contact', 'rings'):
            if part in ('contact', 'rings'): ot, nt = collections.Counter(O[part]), collections.Counter(N[part])
            else:
                keys = {k for k in N[part] if not os.path.basename(k).startswith('rb-')}   # not the beasts' own (drawn as before, flying on the clock)
                ot = collections.Counter(t for k in keys for t in O[part].get(k, [])); nt = collections.Counter(t for k in keys for t in N[part][k])
            a, b = sorted((ot - nt).elements()), sorted((nt - ot).elements())
            left = sum(1 for x, y in zip(a, b) if not near(x, y, 2e-4)) + abs(len(a) - len(b))   # rounding in the 4th decimal only
            row[part] = dict(triangles=sum(nt.values()), differ=left)
            ok = ok and not left and sum(nt.values()) > 0 if part != 'sil' else ok and not left
        out[name] = row
    out['errors'] = old['errors'] + new['errors']
    return out, ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('what', choices=['frames', 'geometry'])
    ap.add_argument('--engine', default='chrome,webkit')
    ap.add_argument('--units', default='200,2000,10000')
    ap.add_argument('--walk', type=float, default=0.2)
    ap.add_argument('--secs', type=float, default=8)
    ap.add_argument('--old', type=Path, default=OLD)
    ap.add_argument('--new', type=Path, help='the page to check (default game/Interface/remastered.html)')
    ap.add_argument('--stepping', action='store_true', help='geometry: also half the units stepping a tile, compared at four frames along the step')
    ap.add_argument('--old-records', action='store_true', help='the old page draws units as records too (a check between two GPU-drawing pages)')
    ap.add_argument('--json', type=Path)
    a = ap.parse_args()
    if a.what == 'geometry':
        res, ok = geometry(a.old, a.new, a.old_records, a.stepping)
        print(json.dumps(res, indent=1))
    else:
        W.page()
        Ns = [int(x) for x in a.units.split(',')]
        res = {}
        if 'chrome' in a.engine: res['chrome'] = frames_chrome(Ns, a.secs, a.walk)
        if 'webkit' in a.engine: res['webkit'] = frames_webkit(Ns, a.secs, a.walk)
        ok = all('frame' in r and not r.get('errors') for L in res.values() for r in L)
        for eng, L in res.items():
            for r in L: print(eng, r.get('N'), json.dumps(r.get('frame')), 'update3D', json.dumps(r.get('update3D')), r.get('errors') or '')
    if a.json: a.json.write_text(json.dumps(res, indent=1) + '\n')
    print('PASS' if ok else 'FAIL')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
