#!/usr/bin/env python3
"""World look in the real client: a native client window on a mapless arena (tests/worldlook_native_probe.dm) with a
village - grass, desert, marsh and snow patches, a pond with a swampy edge, a forest, cactus, a rock mountain - and
about 200 villagers. No input is sent: the fixture sets the time of day and passes commands to the page's probe, which
times every v3frame (CPU ms) and the frame interval, and lands blows through the page's own v3hits. Keeps HUD
snapshots (the 3D view under the HUD) at day, mid-fight, dusk and night, and the frame numbers for each.

    python3 tools/runlock.py --who world-look -- python3 tools/check_worldlook_native.py"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from check_mouse import ROOT, RUNTIME, client_copy, stop, write_hints

OUT = Path(os.environ.get('WORLDLOOK_OUT') or ROOT / 'reports/polish-2026-10-22/world-look/native').resolve()   # WORLDLOOK_OUT: another folder (before/after runs)

INSTRUMENT = r"""(function(){let F=[];window.__wlErr=[];addEventListener('error',e=>__wlErr.push(String(e.message).slice(0,200)));
 // time some of what v3frame calls, by name (they are global functions, so the frame picks up the wrappers)
 const TM={};const timeFn=n=>{const o=window[n];if(typeof o!=='function'||o.__wl)return;const w=function(){const t0=performance.now();const r=o.apply(this,arguments);(TM[n]||(TM[n]=[])).push(performance.now()-t0);if(TM[n].length>600)TM[n].shift();return r};w.__wl=1;window[n]=w};
 const timed=['v3floatsTick','v3drawFx','v3combatFx','v3breathFx','v3drawWork','v3drawLiquids','v3hover','v3marks','v3bars','v3vignette','v3fireLights','v3mountainCut','v3foodTags','v3sayTags'];
 const U3=[],UH=[],GAPS=[];const wrapU=()=>{if(!window.__wlH&&typeof updateHUD==='function'){window.__wlH=1;const oh=updateHUD;window.updateHUD=function(r){const t0=performance.now();const x=oh(r);UH.push(performance.now()-t0);if(UH.length>400)UH.shift();return x}}if(window.__wlU||typeof update3D!=='function')return;window.__wlU=1;const o=update3D;window.update3D=function(r){const t0=performance.now();const x=o(r);U3.push(performance.now()-t0);if(U3.length>400)U3.shift();return x}};let pan=null;
 const wrap=()=>{wrapU();if(window.__wlWrapped||typeof v3frame!=='function')return;window.__wlWrapped=1;timed.forEach(timeFn);const o=v3frame;v3frame=function(ts){const t0=performance.now();o(ts);F.push([t0,performance.now()-t0]);if(F.length>1200)F.shift();if(window.__wlRK&&V3.eye&&performance.now()>(window.__wlRKfrom||0)){const e=V3.eye;__wlRK.push([e[1],V3.camH,Math.hypot(e[0]-V3.cx,e[1]-V3.camH,e[2]+V3.cy),performance.now()]);if(__wlRK.length>1200)__wlRK.shift()}}};
 const pct=(L,q)=>L.length?Math.round(L[Math.min(L.length-1,Math.floor(L.length*q))]*100)/100:null;let fight=null;
 window.wlProbe=function(c){c=String(c);if(c==='reset'||c==='hits'||c==='hitsnofloat'||c==='lite'||c==='nohud'||c==='pan'||c==='ridge'||c==='ridgeorbit'){F.length=0;U3.length=0;UH.length=0;for(const k in TM)TM[k].length=0}clearInterval(pan);
  // the camera at the mountain's foot (70,38: rock from x=71 east), looking at it from over the mountain; ridgeorbit turns it
  // round that spot (the page's own E turn) and logs the eye per frame (the rock fade: the camera must not move for rock)
  // The camera is held there (for ridgeorbit 3 s, then it turns): after the jump the game puts its own camera back.
  V3.keys&&V3.keys.delete('e');window.__wlRK=null;clearInterval(window.__wlCam);if((c==='ridge'||c==='ridgeorbit')&&!window.__wlHome)window.__wlHome=[V3.tcx,V3.tcy,V3.dist,V3.pitch,V3.yaw,V3.iso];   /* 'home' puts the camera back */
  if(c==='home'&&window.__wlHome){const H=window.__wlHome;v3iso(H[5]);V3.tcx=V3.cx=H[0];V3.tcy=V3.cy=H[1];V3.dist=H[2];V3.pitch=H[3];V3.yaw=H[4];V3.userTurn=0;V3.panAt=performance.now();if(typeof v3panSend==='function')v3panSend(performance.now())}
  if(c==='ridge'||c==='ridgeorbit'){const cam=()=>{v3iso(false);V3.turnTo=null;V3.tcx=V3.cx=70;V3.tcy=V3.cy=38;V3.dist=9;V3.pitch=0.32;V3.yaw=Math.PI/2;V3.userTurn=performance.now()+1e9};cam();V3.panAt=performance.now();if(typeof v3panSend==='function')v3panSend(performance.now());
   const t0=performance.now();window.__wlCam=setInterval(()=>{if(c==='ridgeorbit'&&performance.now()-t0>3000){clearInterval(window.__wlCam);{window.__wlRKfrom=performance.now()+400;window.__wlRK=[];V3.keys.add('e')}return}cam()},200)}
  if(c==='pan'){let k=0;pan=setInterval(()=>{const d=Math.floor(k/12)%2?-1:1;k++;V3.tcx+=d;V3.panAt=performance.now();if(typeof v3panSend==='function')v3panSend(performance.now())},250)}
  V3.lite=c==='lite';const hide=c==='nohud',cv=document.getElementById('world3d');for(const e of document.body.children)if(e!==cv&&!e.contains(cv)&&e.tagName!=='SCRIPT')e.style.visibility=hide?'hidden':'';const fb=document.getElementById('dmgfloats');if(fb)fb.style.display=c==='hitsnofloat'?'none':'';if(c==='hitsnofloat')c='hits';if(c==='hits'){let id=700000,n=0;const W=['sword','axe','mace','bow','spear','dagger'],K=['hit','hit','big','parry','hit','kill'];clearInterval(fight);
  fight=setInterval(()=>{const T=(V3.things||[]).filter(t=>t.kind==='mine'&&Math.abs(t.x-V3.cx)<7&&Math.abs(t.y-V3.cy)<5);if(!T.length||n++>300){clearInterval(fight);return}const t=T[Math.floor(Math.random()*T.length)],w=W[id%W.length],far=w==='bow';
   v3hits([{id:id++,k:K[id%K.length],x:t.x,y:t.y,ax:t.x-(far?5:1),ay:t.y+(far?2:0),n:5+id%40,w,p:far?'arrow':undefined,mine:0,mineby:1}])},33)}};
 setInterval(()=>{try{wrap();const c=document.getElementById('world3d');const cpu=F.map(f=>f[1]).sort((a,b)=>a-b),gaps=[];for(let i=1;i<F.length;i++)gaps.push(F[i][0]-F[i-1][0]);gaps.sort((a,b)=>a-b);
  const r={v3:{on:!!V3.on,inv:!!V3.inv},things:(V3.things||[]).length,W:c.width,H:c.height,cw:c.clientWidth,ch:c.clientHeight,dpr:devicePixelRatio,frames:F.length,cpu50:pct(cpu,.5),cpu95:pct(cpu,.95),cpuMax:pct(cpu,.999),gap50:pct(gaps,.5),gap95:pct(gaps,.95),gapMax:pct(gaps,.999),
   over20:gaps.filter(g=>g>20).length,over34:gaps.filter(g=>g>34).length,fx:(V3.fx||[]).length,ghosts:(V3.ghosts||[]).length,errs:__wlErr.slice(-3),u3:(()=>{const S=U3.slice().sort((a,b)=>a-b);return [pct(S,.5),pct(S,.95),pct(S,.999),S.length]})(),uh:(()=>{const S=UH.slice().sort((a,b)=>a-b);return [pct(S,.5),pct(S,.95),pct(S,.999),S.length]})(),fn:Object.fromEntries(Object.entries(TM).map(([k,L])=>{const S=L.slice().sort((a,b)=>a-b);return [k,[pct(S,.5),pct(S,.95)]]})),floats:(V3.floats||[]).length,night:!!V3.night,dayp:V3.dayp,shore:(V3.waterList||[]).filter(w=>w[7]).length,glErr:V3.gl?V3.gl.getError():-1,rock:(()=>{const K=window.__wlRK||[],st=i=>{let m=0;for(let k=1;k<K.length;k++){const dt=Math.max(0.008,(K[k][3]-K[k-1][3])/1000);m=Math.max(m,Math.abs(K[k][i]-K[k-1][i])/dt)}return Math.round(m*100)/100};let lo=1e9,hi=-1e9;for(const q of K){lo=Math.min(lo,q[1]);hi=Math.max(hi,q[1])}
   return {fade:V3.fprF?Array.from(V3.fprF).filter(v=>v>0.5).length:null,camH:V3.camH,eyeY:V3.eye&&V3.eye[1],n:K.length,eyeSpeed:st(0),distSpeed:st(2),aimRange:K.length?Math.round((hi-lo)*1000)/1000:null}})()};
  send('proberects',JSON.stringify(r))}catch(e){}},1000)})();
send('ready','');"""


def main():
    if (OUT / 'SKIP').exists():   # a queued run called off (a file named SKIP in its output folder): nothing to do
        print('skipped: ' + str(OUT / 'SKIP'))
        return
    result = {'checks': {}, 'phases': {}, 'scope': __doc__.strip().splitlines()[0]}
    OUT.mkdir(parents=True, exist_ok=True)
    tests = ROOT / 'tests'
    slp, clp = tests / 'worldlook-native-server.log', tests / 'worldlook-native-client.log'
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-worldlook-native-') as temp:
        base = Path(temp)
        world = base / 'world'
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        shutil.copy2(tests / 'worldlook_native_probe.dm', world / 'worldlook_native_probe.dm')
        fixture = world / 'worldlook_native.dme'
        fixture.write_text(dme + '\n#include "worldlook_native_probe.dm"\n', encoding='latin-1')
        html = world / 'Interface/remastered.html'
        page = html.read_text()
        assert "send('ready','');" in page
        # WORLDLOOK_NOINST=1: the units drawn without instancing (V3.ix off: v3drawInst spreads their records into triangles
        # in JS, the old geometry), for a before/after of GPU unit drawing in the real client
        noinst = "(function(){const i=setInterval(()=>{if(window.V3&&V3.gl&&V3.ix!==undefined){V3.ix=null;clearInterval(i)}},20)})();" if os.environ.get('WORLDLOOK_NOINST') == '1' else ''
        html.write_text(page.replace("send('ready','');", noinst + INSTRUMENT, 1))
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests / 'worldlook-native-compile.log').open('w') as log_file:
            subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=log_file, stderr=subprocess.STDOUT, check=True, timeout=180)
        probe = base / 'probe'
        probe.mkdir()
        hints = base / 'layout.json'
        write_hints(world / 'skin.dmf', hints)
        env.update(DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(ROOT / 'engine/webview-webkit'))

        def log():
            path = world / 'ErrorLog.txt'
            return path.read_text(errors='replace') if path.exists() else ''

        def state():
            try:
                return json.loads((probe / 'state.json').read_text())
            except (ValueError, FileNotFoundError):
                return {}

        def rects():
            rows = re.findall(r'WORLDLOOK_NATIVE\|rects\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

        def hud_ready():
            rows = re.findall(r'WORLDLOOK_NATIVE\|state\|([^\r\n]+)', log())
            return rows and json.loads(rows[-1]).get('hudReady')

        def until(predicate, timeout=15, what=''):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                try:
                    if predicate():
                        return True
                except (KeyError, IndexError, TypeError):
                    pass
                time.sleep(.1)
            raise TimeoutError('Timed out waiting for ' + what + ': ' + json.dumps(rects())[:500])

        def window():
            return next((w for w in state()['windows'] if w.get('viewports')), None) or max(state()['windows'], key=lambda w: w['width'] * w['height'])

        def action(**values):
            w = window()
            payload = dict(window=w['id'], kind=5, x=0, y=0, code=0, modifiers=0, text='')
            payload.update(values)
            (probe / 'action.pending').write_text(json.dumps(payload))
            (probe / 'action.pending').replace(probe / 'action.json')
            until(lambda: not (probe / 'action.json').exists(), 5, 'input delivery')

        def capture(name):
            prefix = 'worldlook-native-' + name
            (probe / 'capture-web.txt').write_text(prefix)
            until(lambda: (probe / f'{prefix}-panels.json').exists(), 10, 'HUD snapshot')
            time.sleep(1.0)
            for row in json.loads((probe / f'{prefix}-panels.json').read_text()):
                src = probe / row['file']
                if src.exists():
                    dst = OUT / (Path(row['file']).stem + '.jpg')
                    subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '82', str(src), '--out', str(dst)], capture_output=True)
                    result.setdefault('screenshots', []).append(str(dst.relative_to(ROOT)))

        n = [0]

        def phase(name, when, page_cmd, wait, shot_after=None):
            n[0] += 1
            (world / 'worldlook-native-cmd.txt').write_text(f'{when}|{page_cmd}|{n[0]}')
            until(lambda: f'WORLDLOOK_NATIVE|cmd|{when}|{page_cmd}|{n[0]}' in log(), 15, 'the command ' + name)
            t0 = time.monotonic()
            if shot_after is not None:
                time.sleep(shot_after)
                capture(name)
            time.sleep(max(0, wait - (time.monotonic() - t0)))
            r = rects()
            result['phases'][name] = {k: r.get(k) for k in ('things', 'W', 'H', 'cw', 'ch', 'dpr', 'frames', 'cpu50', 'cpu95', 'cpuMax', 'gap50', 'gap95', 'gapMax', 'over20', 'over34', 'fx', 'ghosts', 'errs', 'night', 'dayp', 'shore', 'glErr', 'fn', 'floats', 'u3', 'uh', 'rock')}
            result['phases'][name]['load'] = os.getloadavg()[0]
            return r

        checks = result['checks']
        try:
            with slp.open('w') as sl, clp.open('w') as cl:
                server = subprocess.Popen([str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'opendream.topic_port=25887', '--cvar', 'net.port=12387', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in slp.read_text(errors='replace'), 40, 'server')
                cd = client_copy()
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(RUNTIME / 'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12387', '--username', 'WorldLook', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: 'WORLDLOOK_NATIVE|ready' in log() and hud_ready() and state().get('windows') and rects().get('v3', {}).get('on'), 120, 'client and HUD')
                try:
                    until(lambda: rects()['v3']['inv'], 20, '3D view to draw')
                except TimeoutError:
                    result['wake_click'] = True
                    action(kind=5, x=.3, y=.3)
                    until(lambda: rects()['v3']['inv'], 30, '3D view to draw after the wake click')
                until(lambda: rects().get('things', 0) >= 150, 60, 'the crowd in 3D')
                time.sleep(4)
                # WORLDLOOK_RIDGE_FIRST=1: the rock-fade phases first, while the window is fresh and in front (late in a long run the
                # display can start to sleep and the window stops drawing)
                early = os.environ.get('WORLDLOOK_RIDGE_FIRST') == '1'
                if early:
                    ridge = phase('ridge', 'day', 'ridge', 10, shot_after=7)
                    orbit = phase('ridge-orbit', 'day', 'ridgeorbit', 12)
                    phase('home', 'day', 'home', 6)   # back to the village for the rest
                day = phase('day', 'day', 'reset', 9, shot_after=5)
                phase('day-lite', 'day', 'lite', 8)     # without the sun-shadow pass, clouds, foam, glows, ambience, vignette
                phase('day-nohud', 'day', 'nohud', 8)   # the full 3D view with the HUD panels hidden
                phase('day-again', 'day', 'reset', 8)
                phase('pan', 'day', 'pan', 9)   # the camera stepping a tile every 0.25 s, 12 east then 12 west (the server follows)
                phase('after-pan', 'day', 'reset', 5)
                fight = phase('fight', 'day', 'hits', 9, shot_after=2.5)
                time.sleep(2)
                phase('fight-nofloats', 'day', 'hitsnofloat', 9)   # the same blows with the damage numbers' box hidden
                time.sleep(2)
                dusk = phase('dusk', 'dusk', 'reset', 7, shot_after=4)
                night = phase('night', 'night', 'reset', 7, shot_after=4)
                if not early:
                    ridge = phase('ridge', 'day', 'ridge', 10, shot_after=7)   # the camera over the mountain at its foot: the rock there fades
                    orbit = phase('ridge-orbit', 'day', 'ridgeorbit', 12)     # turning round that spot: no snaps, the aim flat
                (world / 'worldlook-native-done.txt').write_text('done')
                P = result['phases']
                checks['crowd_drawn'] = (day.get('things') or 0) >= 150
                checks['no_page_errors'] = not any(p.get('errs') for p in P.values())
                checks['no_gl_errors'] = all(p.get('glErr') == 0 for p in P.values())
                checks['shore_built'] = (day.get('shore') or 0) > 0
                checks['fight_effects'] = (fight.get('fx') or 0) > 0 or (fight.get('ghosts') or 0) > 0
                checks['night_flag'] = bool(night.get('night')) and not dusk.get('night')
                rk, ro = ridge.get('rock') or {}, orbit.get('rock') or {}
                checks['rock_fades'] = (rk.get('fade') or 0) > 0
                checks['camera_steady_by_rock'] = (ro.get('n') or 0) > 60 and ro.get('eyeSpeed', 99) < 25 and ro.get('distSpeed', 99) < 20 and (ro.get('aimRange') or 0) < 0.05
                checks['steady_60fps'] = all((p.get('gap50') or 99) < 17.5 and (p.get('over34') or 0) <= 3 for k, p in P.items() if k != 'home')   # 'home' is the jump back, not a view
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
        (tests / 'worldlook-native-world.log').write_text(log())
        result['errors'] = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + clp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
        result['known_unrelated'] = [e for e in result['errors'] if 'Cache was ensured for a file (/r3t-ground-' in e]
        result['errors'] = [e for e in result['errors'] if e not in result['known_unrelated']]
        result['passed'] = not result.get('error') and not result['errors'] and len(checks) == 9 and all(checks.values())
        (OUT / 'worldlook-native-checks.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
        return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
