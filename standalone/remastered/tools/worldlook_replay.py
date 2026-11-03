#!/usr/bin/env python3
"""World look probe: the 3D view's real page code fed a real scene, no client and no input.

  python3 tools/worldlook_replay.py bench           # dump, and time Remaster3DTerrain (ms/call + output md5)
  python3 tools/worldlook_replay.py dump            # build the scenes (tests/worldlook_dump_test.dm) into tests/worldlook-replay/
  python3 tools/worldlook_replay.py shots OUT [--tag before] [--shots NAME,...]
                                                    # stills at fixed cameras (headless Chrome, the Mac's GPU) into OUT/
  python3 tools/worldlook_replay.py perf [--units 40,200] [--secs 6]
  python3 tools/worldlook_replay.py check           # terrain chunks == one whole build, on every dumped scene
                                                    # frame times: CPU ms spent in v3frame and the frame interval

The page is a copy of game/Interface/remastered.html with a small replay script in its head: send() goes nowhere,
the 3D view is switched on and given the scene, and the camera is set from the address (cx, cy, dist, yaw, pitch;
night=1, dayp=0..1; units=N clones the crowd to N units; fx=N lands N blows a second through the page's own v3hits)."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT.parent/'replica/runtime/macos-x64'   # shared engine, used read-only
OUT = ROOT/'tests/worldlook-replay'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

REPLAY = r"""
addEventListener('DOMContentLoaded',()=>setTimeout(async()=>{try{send=function(){};const q=new URLSearchParams(location.search),n=q.get('scene')||'1';
 v3set(true);const d=await (await fetch('worldlook-3d-'+n+'.json')).json();
 if(q.get('night'))d.night=+q.get('night');if(q.get('season')){V3.seasonOverride=q.get('season');V3.seas=null}if(q.get('clouds')!=='1')V3.noClouds=true;/* cloud shadows drift with time: off unless asked, so stills compare */if(q.get('dayp'))d.dayp=+q.get('dayp');
 const want=+q.get('units')||0;if(want){const base=d.things.filter(t=>t.kind==='mine'||t.kind==='unit'||t.unit||t.icon&&t.hp!=null);const src=base.length?base:d.things.slice(0,20);let k=0;
  const out=d.things.filter(t=>!src.includes(t));for(let i=0;i<want;i++){const s=src[i%src.length],c=JSON.parse(JSON.stringify(s));const ring=Math.floor(i/src.length);c.ref=(c.ref||c.id)+'_c'+i;c.id=c.ref;c.x=s.x+((ring*3)%9)-4;c.y=s.y+(Math.floor(ring/3)%5)*2-4;out.push(c)}d.things=out}
 if(q.get('cx'))d.cx=+q.get('cx');if(q.get('cy'))d.cy=+q.get('cy');update3D(d);window.replayData=d;
 const cam=()=>{if(q.get('dist'))V3.dist=+q.get('dist');if(q.get('yaw'))V3.yaw=+q.get('yaw');if(q.get('pitch'))V3.pitch=+q.get('pitch');if(q.get('iso')==='0')V3.iso=false;if(q.get('cx')){V3.cx=V3.tcx=+q.get('cx');V3.cy=V3.tcy=+q.get('cy')}};cam();const ci=setInterval(cam,200);setTimeout(()=>clearInterval(ci),1500);
 if(q.get('clean')){const c=$('world3d');c.style.cssText+=';position:fixed;left:0;top:0;width:100vw;height:100vh;z-index:99999';for(const e of document.querySelectorAll('body *'))if(e!==c&&!e.contains(c))e.style.visibility='hidden';c.style.visibility='visible'}
 // frame cost: wrap v3frame and keep the last 600 frames
 const F=window.replayFrames=[];const orig=v3frame;const M=performance.memory;v3frame=function(ts){const h0=M?M.usedJSHeapSize:0,t0=performance.now();orig(ts);const t1=performance.now(),h1=M?M.usedJSHeapSize:0;F.push([t0,t1-t0,h1-h0,h0]);if(F.length>600)F.shift()};
 // fx=N: N blows a second between the units near the middle (sword, axe, mace, arrows; some parried, some kills)
 const fxn=+q.get('fx')||0;if(fxn){let hid=500000;const W=['sword','axe','mace','bow','spear','dagger'],K=['hit','hit','big','parry','hit','block'];setInterval(()=>{const T=V3.things.filter(t=>t.kind==='mine');if(!T.length)return;const t=T[Math.floor(Math.random()*Math.min(T.length,60))],w=W[hid%W.length],far=w==='bow';
  v3hits([{id:hid++,k:K[hid%K.length],x:t.x,y:t.y,ax:t.x-(far?5:1),ay:t.y+(far?2:0),n:5+hid%40,w,p:far?'arrow':undefined,mine:0,mineby:1}])},1000/fxn)}
 window.replayReady=true}catch(e){(window.__errs=window.__errs||[]).push(String(e&&e.stack||e))}},600));
"""

# Fixed cameras for before/after stills: name -> address
SHOTS = {
    'village-day': 'scene=1&cx=41&cy=31&dist=13&pitch=0.62&yaw=0.35&dayp=0.45',
    'village-close': 'scene=1&cx=40&cy=30&dist=7&pitch=0.55&yaw=0.2&dayp=0.45',
    'pond-shore': 'scene=1&cx=29&cy=37&dist=11&pitch=0.7&yaw=-0.4&dayp=0.45',
    'mountain': 'scene=3&cx=64&cy=38&dist=13&pitch=0.62&yaw=0.75&dayp=0.3',
    'transitions': 'scene=4&cx=56&cy=20&dist=16&pitch=0.75&yaw=0.1&dayp=0.45',
    'forest': 'scene=5&cx=14&cy=47&dist=12&pitch=0.6&yaw=-0.3&dayp=0.45',
    'morning': 'scene=1&cx=40&cy=30&dist=7&pitch=0.55&yaw=0.2&dayp=0.18',
    'forest-fall': 'scene=5&cx=14&cy=47&dist=12&pitch=0.6&yaw=-0.3&dayp=0.45&season=fall',
    'village-winter': 'scene=1&cx=41&cy=31&dist=13&pitch=0.62&yaw=0.35&dayp=0.45&season=winter',
    'clouds': 'scene=1&cx=41&cy=31&dist=20&pitch=0.7&yaw=0.35&dayp=0.45&clouds=1',
    'forest-night': 'scene=5&cx=16&cy=46&dist=11&pitch=0.6&yaw=-0.3&night=1&season=summer',
    'moria': 'scene=L7&cx=74&cy=11&dist=10&pitch=0.8&yaw=0.35&dayp=0.45',
    'moria-carved': 'scene=L7&cx=87&cy=11&dist=9&pitch=0.75&yaw=0.3&dayp=0.45',
    'dragon-lair': 'scene=L4&cx=15&cy=16&dist=8&pitch=0.8&yaw=0.4',
    'forge-hall': 'scene=L2&cx=36&cy=12&dist=11&pitch=0.75&yaw=0.45&dayp=0.45',
    'buildings-night': 'scene=L5&cx=20&cy=50&dist=16&pitch=0.7&yaw=0.45&night=1',
    'village-fall': 'scene=1&cx=41&cy=31&dist=18&pitch=0.65&yaw=0.35&dayp=0.45&season=fall',
    'beasts-day': 'scene=6&cx=43&cy=31&dist=15&pitch=0.62&yaw=0.35&dayp=0.25',
    'top': 'scene=1&cx=41&cy=31&dist=13&pitch=1.22&yaw=0&iso=0&dayp=0.3',
    'chase': 'scene=1&cx=40&cy=30&dist=9&pitch=0.28&yaw=0.9&iso=0&dayp=0.45',
    'pocket': 'scene=8&cx=86&cy=46&dist=12&pitch=0.65&yaw=0.785&dayp=0.4',
    'canopy-shop': 'scene=5&cx=16&cy=46&dist=8&pitch=0.62&yaw=0.35&dayp=0.4',
    'evening': 'scene=1&cx=41&cy=31&dist=13&pitch=0.62&yaw=0.35&dayp=0.92',
    'night': 'scene=1&cx=41&cy=31&dist=13&pitch=0.62&yaw=0.35&night=1',
    'underground': 'scene=2&cx=28&cy=19&dist=11&pitch=0.7&yaw=0.3',
}


def dump(bench=False):
    arena = ROOT/'tests/worldlook-dump-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
    (arena/'worldlook_dump.dme').write_text(dme + '\n#include "worldlook_dump_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) WorldLookDumpRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/worldlook_dump_test.dm', arena/'worldlook_dump_test.dm')
    if os.environ.get('WORLDLOOK_V3DM'):   # another View3D.dm (say the one before a change) for an A/B of the server side
        shutil.copy2(os.environ['WORLDLOOK_V3DM'], arena/'Code/Remastered/View3D.dm')
    # the terrain bench (tests/worldlook_terrain_bench.dm) is always compiled in; `bench` switches it on
    shutil.copy2(ROOT/'tests/worldlook_terrain_bench.dm', arena/'worldlook_terrain_bench.dm')
    (arena/'worldlook_dump.dme').write_text((arena/'worldlook_dump.dme').read_text(encoding='latin-1') + '#include "worldlook_terrain_bench.dm"\n', encoding='latin-1')
    if bench:   # also time Remaster3DTerrain and keep its exact output
        (arena/'worldlook-bench.on').write_text('1')
    (arena/'rsc').mkdir()
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    with (ROOT/'tests/worldlook-dump-compile.log').open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'worldlook_dump.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    log = ROOT/'tests/worldlook-dump-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-worldlook-dump-') as data, log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"worldlook_dump.json"}', '--cvar', 'opendream.topic_port=25897',
            '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12397', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline and server.poll() is None:
            t = log.read_text(errors='replace')
            if 'WORLDLOOK_DUMP|complete' in t or '[ERRO]' in t: break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = log.read_text(errors='replace')
    print('\n'.join(re.findall(r'WORLDLOOK_DUMP\|[^\r\n]*', text)))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    if errors: print('\n'.join(errors[:5]))
    OUT.mkdir(parents=True, exist_ok=True)
    for f in arena.glob('worldlook-3d-*.json'): shutil.copy2(f, OUT/f.name)
    if (arena/'worldlook-bench.json').exists(): shutil.copy2(arena/'worldlook-bench.json', OUT/'worldlook-bench.json'); print((arena/'worldlook-bench.json').read_text())
    for f in (arena/'rsc').glob('*.png'): shutil.copy2(f, OUT/f.name)
    shutil.rmtree(arena)
    if errors or 'WORLDLOOK_DUMP|complete' not in text: raise SystemExit(1)


def page():
    """The replay page beside the scene data: the current HUD page (re-copied each run, so edits show)."""
    for f in (ROOT/'game/Interface/models').glob('*.json'): shutil.copy2(f, OUT/f'model-{f.stem}.json')
    for f in (ROOT/'game/Interface/textures').glob('*.png'): shutil.copy2(f, OUT/f'r3t-{f.stem}.png')
    beasts = ROOT/'game/Icons/Remastered/Beasts'
    if beasts.exists():
        for f in beasts.glob('*/*/*.png'):
            dst = OUT/f'rb-{f.parent.parent.name}-{f.parent.name}-{f.stem}.png'
            if not dst.exists(): shutil.copy2(f, dst)
    # WORLDLOOK_HTML: replay another copy of the page (say the restore point's) for before/after stills
    html = Path(os.environ.get('WORLDLOOK_HTML') or ROOT/'game/Interface/remastered.html').read_text()
    html = html.replace("function send(action,value){window.location.href=", "function send(action,value){return;window.location.href=", 1)
    i = html.index('<head>') + len('<head>')
    (OUT/'replay.html').write_text(html[:i] + '<script>window.__errs=[];addEventListener("error",e=>__errs.push(e.message+" @"+e.lineno));' + REPLAY + '</script>' + html[i:])


class Server:
    """A plain file server for the replay folder (the page fetches its scene and textures)."""
    def __enter__(self):
        import http.server, threading, functools
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a): pass
        handler = functools.partial(Quiet, directory=str(OUT))
        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}/replay.html?clean=1&'
        return self

    def __exit__(self, *a):
        self.httpd.shutdown()


ENGINE = os.environ.get('WORLDLOOK_ENGINE', 'chromium')   # webkit: Playwright's WebKit (JavaScriptCore, like the app)


def browser(pw, w=1440, h=900):
    if ENGINE == 'webkit':
        b = pw.webkit.launch(headless=os.environ.get('WORLDLOOK_HEADED') != '1')
        p = b.new_page(viewport=dict(width=w, height=h))
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)[:300]))
        p.on('console', lambda c: errs.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
        return b, p, errs
    b = pw.chromium.launch(executable_path=CHROME, headless=True, args=['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-precise-memory-info', '--js-flags=--expose-gc'])
    p = b.new_page(viewport=dict(width=w, height=h), device_scale_factor=float(os.environ.get('WORLDLOOK_DPR', '1')))
    errs = []
    p.on('pageerror', lambda e: errs.append(str(e)[:300]))
    p.on('console', lambda c: errs.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    return b, p, errs


def load(p, url, settle=3500):
    p.goto(url, wait_until='domcontentloaded')
    p.wait_for_function('window.replayReady===true||(window.__errs&&window.__errs.length>0)', timeout=20000)
    p.wait_for_timeout(settle)


def shots(out, tag, names, w, h):
    from playwright.sync_api import sync_playwright
    page()
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    with Server() as s, sync_playwright() as pw:
        b, p, errs = browser(pw, w, h)
        for name in names:
            load(p, s.base + SHOTS[name])
            f = out/f'{name}-{tag}.jpg' if tag else out/f'{name}.jpg'
            p.screenshot(path=str(f), type='jpeg', quality=88)
            report[name] = str(f)
        report['errors'] = errs + p.evaluate('window.__errs||[]')
        b.close()
    print(json.dumps(report, indent=1))
    return report


def perf(units, secs, scene_url, w, h):
    from playwright.sync_api import sync_playwright
    page()
    rows = {}
    with Server() as s, sync_playwright() as pw:
        b, p, errs = browser(pw, w, h)
        for n in units:
            load(p, s.base + scene_url + (f'&units={n}' if n else ''), settle=2500)
            p.evaluate('window.replayFrames.length=0')
            p.wait_for_timeout(int(secs * 1000))
            F = p.evaluate('window.replayFrames.slice()')
            cpu = sorted(f[1] for f in F)
            gaps = sorted(F[i + 1][0] - F[i][0] for i in range(len(F) - 1))
            pct = lambda L, q: round(L[min(len(L) - 1, int(len(L) * q))], 2) if L else None
            hs = [f[3] for f in F if len(f) > 3]
            grow = [hs[i + 1] - hs[i] for i in range(len(hs) - 1)]
            alloc = sorted(g for g in grow if g >= 0)
            gcs = sum(1 for g in grow if g < -200000)
            things = p.evaluate('(V3.things||[]).length')
            heap = p.evaluate('performance.memory?Math.round(performance.memory.usedJSHeapSize/1048576):null')
            rows[n] = dict(things=things, frames=len(F), cpu_ms_median=pct(cpu, .5), cpu_ms_p95=pct(cpu, .95), cpu_ms_max=pct(cpu, .999),
                           interval_ms_median=pct(gaps, .5), interval_ms_p95=pct(gaps, .95), interval_ms_max=pct(gaps, .999),
                           fps=round(1000 / (sum(gaps) / len(gaps)), 1) if gaps else None, heap_mb=heap,
                           alloc_kb_per_frame_median=round(alloc[len(alloc) // 2] / 1024, 1) if alloc else None, alloc_kb_per_frame_p95=round(alloc[int(len(alloc) * .95)] / 1024, 1) if alloc else None,
                           alloc_kb_per_frame_mean=round(sum(alloc) / max(1, len(grow)) / 1024, 1), gcs=gcs)
        rows['errors'] = errs + p.evaluate('window.__errs||[]')
        b.close()
    print(json.dumps(rows, indent=1))
    return rows


CHUNK_CHECK = r"""()=>{const T=V3.terrain;
 const tris=(F)=>{const L=[];for(let o=0;o+36<=F.length;o+=36){let s='';for(let q=0;q<36;q++)s+=(Math.round(F[o+q]*1000)/1000)+',';L.push(s)}return L.sort()};
 V3.torchList=[];V3.hoardList=[];V3.rampH=new Map();V3.rockGeo=new Map();V3.waterList=[];V3.waterSet=new Set();V3.foamSegs=[];
 const G=v3meshes(T,0,null,false,{i0:0,i1:T.w,j0:0,j1:T.h});const mono={};for(const [k,a] of G)if(a.length)mono[k]=tris(new Float32Array(a));
 const side=o=>JSON.stringify([o.torch.map(String).sort(),o.hoard.map(String).sort(),o.water.map(String).sort(),o.ramp.map(String).sort(),o.wset.slice().sort(),o.rock.map(e=>e[0]).sort(),o.foam]);
 const ms=side({torch:V3.torchList,hoard:V3.hoardList,water:V3.waterList,ramp:[...V3.rampH],wset:[...V3.waterSet],rock:[...V3.rockGeo],foam:V3.foamSegs.length});
 V3.tchunks=null;V3.tmesh=v3meshesChunked(T,V3.tmesh);const ch={};for(const E of V3.tchunks.values())for(const [k,f] of E.geo)(ch[k]=ch[k]||[]).push(...tris(f));for(const k in ch)ch[k].sort();
 const cs=side({torch:V3.torchList,hoard:V3.hoardList,water:V3.waterList,ramp:[...V3.rampH],wset:[...V3.waterSet],rock:[...V3.rockGeo],foam:V3.foamSegs.length});
 let diff=0;for(const k of new Set([...Object.keys(mono),...Object.keys(ch)])){const a=mono[k]||[],b=ch[k]||[];if(a.length!==b.length){diff+=Math.abs(a.length-b.length);continue}for(let i=0;i<a.length;i++)if(a[i]!==b[i])diff++}
 V3.tmesh=v3meshesChunked(T,V3.tmesh);return {diff,sideSame:ms===cs,reusedAll:V3.chunkBuilt===0}}"""


def check(scenes):
    """The terrain built in chunks (v3meshesChunked) against one whole build: the same triangles per texture and the
    same side lists, on each scene; and a second build reuses every chunk. Exit status 1 on any difference."""
    from playwright.sync_api import sync_playwright
    page()
    out, ok = {}, True
    with Server() as s, sync_playwright() as pw:
        b, p, errs = browser(pw)
        for sc in scenes:
            if not (OUT / f'worldlook-3d-{sc}.json').exists():
                continue
            load(p, s.base + f'scene={sc}&dist=13', settle=1500)
            r = p.evaluate(CHUNK_CHECK)
            out[sc] = r
            ok = ok and r['diff'] == 0 and r['sideSame'] and r['reusedAll']
        out['errors'] = errs + p.evaluate('window.__errs||[]')
        b.close()
    ok = ok and not out['errors']
    print(json.dumps(out, indent=1))
    print('PASS' if ok else 'FAIL')
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('what', choices=['dump', 'bench', 'shots', 'perf', 'page', 'check'])
    ap.add_argument('out', nargs='?', type=Path, default=ROOT/'reports/polish-2026-10-22/world-look')
    ap.add_argument('--tag', default='')
    ap.add_argument('--shots', default=','.join(SHOTS))
    ap.add_argument('--units', default='0,200')
    ap.add_argument('--secs', type=float, default=6)
    ap.add_argument('--scene', default=SHOTS['village-day'])
    ap.add_argument('--size', default='1440x900')
    ap.add_argument('--json', type=Path)
    a = ap.parse_args()
    w, h = map(int, a.size.split('x'))
    if a.what == 'dump': dump()
    elif a.what == 'bench': dump(bench=True)
    elif a.what == 'page': page()
    elif a.what == 'check': raise SystemExit(0 if check(['1', '3', '4', '5', '6', '2', 'L2', 'L3', 'L5', 'L7', 'L9', 'L12', 'L13']) else 1)
    elif a.what == 'shots': r = shots(a.out, a.tag, a.shots.split(','), w, h)
    else: r = perf([int(u) for u in a.units.split(',')], a.secs, a.scene, w, h)
    if a.json and a.what in ('shots', 'perf'): a.json.write_text(json.dumps(r, indent=1) + '\n')


if __name__ == '__main__':
    main()
