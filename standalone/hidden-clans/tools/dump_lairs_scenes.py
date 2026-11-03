#!/usr/bin/env python3
"""Replay the lairs scenes in a browser: builds the scenes of tests/lairs_native_probe.dm in an
arena (tests/lairs_dump_test.dm, no client), writes what the 3D view is sent for each and the
textures it names, and puts them beside a copy of the HUD page (replay.html) that feeds them to
the real 3D code. For looking at the models when no native client can draw (a locked screen).
Open replay.html?scene=N&dist=7&yaw=0.8&pitch=0.6 in a browser served from the output folder."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT.parent/'replica/runtime/macos-x64'   # shared engine, used read-only

REPLAY = """
// Replay (tools/dump_lairs_scenes.py): no server here, so commands go nowhere; the 3D view is
// switched on and fed the scene's data; the camera is set from the address.
addEventListener('DOMContentLoaded',()=>setTimeout(async()=>{try{send=function(){};const q=new URLSearchParams(location.search),n=q.get('scene')||'1';
 v3set(true);const d=await (await fetch('lairs-3d-'+n+'.json')).json();
 // noroof=1: a tunnel's rock roof is not drawn (its data stays); cut=1 also cuts the rock round it
 // down to the ceiling: a mock of a cutaway, to look into a mountain's halls (the game has none yet)
 if(q.get('noroof')){const cr=v3cutRock;v3cutRock=function(g,T,kindAt,i,j,X,Y,Z,K,cut,recess){return recess?cr(g,T,kindAt,i,j,X,Y,Z,K,cut,recess):{c:null}}}
 if(q.get('cut'))for(const k of d.terrain.kinds){if(k.kind==='wall'&&k.blocks)k.blocks=Math.min(k.blocks,2);else if(k.roof)k.roof=0.001}
 if(q.get('cx'))d.cx=+q.get('cx');if(q.get('cy'))d.cy=+q.get('cy');update3D(d);
 const cam=()=>{if(q.get('dist'))V3.dist=+q.get('dist');if(q.get('yaw'))V3.yaw=+q.get('yaw');if(q.get('pitch'))V3.pitch=+q.get('pitch');if(q.get('cx')){V3.cx=V3.tcx=+q.get('cx');V3.cy=V3.tcy=+q.get('cy')}};cam();const ci=setInterval(cam,300);setTimeout(()=>clearInterval(ci),1500);   // then the camera is yours (wheel, right-drag, Q/E)
 // clean=1: only the 3D view, full window (the HUD panels hidden)
 if(q.get('clean')){const c=$('world3d');c.style.cssText+=';position:fixed;left:0;top:0;width:100vw;height:100vh;z-index:99999';for(const e of document.querySelectorAll('body *'))if(e!==c&&!e.contains(c))e.style.visibility='hidden';c.style.visibility='visible'}
 window.replayReady=true}catch(e){(window.__errs=window.__errs||[]).push(String(e&&e.stack||e))}},800));
"""


VIEWER = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lairs viewer</title><style>
:root{--bg:#14181a;--panel:#1d2326;--ink:#e8e2d0;--muted:#a59d88;--gold:#e0bb73}
body{margin:0;display:grid;grid-template-columns:250px 1fr;height:100vh;background:var(--bg);color:var(--ink);font:13px system-ui,sans-serif}
nav{background:var(--panel);overflow:auto;padding:12px;border-right:1px solid #2e3538}h1{font:600 15px Georgia,serif;color:var(--gold);margin:0 0 4px}
p{color:var(--muted);margin:0 0 12px;line-height:1.4}button{display:block;width:100%;text-align:left;margin:0 0 6px;padding:8px 10px;border-radius:6px;border:1px solid #3a3f3a;background:#232a2d;color:var(--ink);cursor:pointer;font:inherit}
button:hover,button.on{border-color:var(--gold)}button small{display:block;color:var(--muted);margin-top:2px}iframe{width:100%;height:100%;border:0;background:#000}
@media (max-width:700px){body{grid-template-columns:1fr;grid-template-rows:auto 1fr}nav{max-height:38vh}}
</style></head><body><nav><h1>Buildings &amp; lairs</h1><p>The game's real 3D data and page code, replayed. Wheel zooms, right-drag pans, Q / E turn.</p><div id="list"></div></nav>
<iframe id="v" title="3D view"></iframe><script>
const S=[['Two-storey keep','The upper storey cut away round the view so the ground floor shows',15,73,53,14,0.75,0.6],
const S=[['Wide gate: down','Three-wide portcullis up, a drawbridge three wide across a three-wide moat, down',13,15,56,9,0.6,0.35],
['Wide gate: up','The same gate shut: portcullis down, drawbridge raised',14,15,56,9,0.6,0.35],
['Gates','Portcullis up (left) and down (right), drawbridge down and up over a moat, a lever',12,39,38,9,0.7,0.35],
['Lifts: cliff and shaft head','A lift up a cliff (tower to the rock top) and the head frame of a shaft down, each turned by a windmill',10,56,33,8,0.65,0.7],
['Lifts: shaft foot','The foot of the shaft in a tunnel underground',11,53,33,6,0.6,0.7],
['Power','Water wheel, axles, bellows by a forge, rune dynamo, windmill; a still line on the right',9,37,56,9,0.7,0.6],
['Mine carts','Track with a bend and a junction, cart stops, an empty and a loaded cart',8,16,31,10,0.75,0.5],
['Moria: hall in the rock','Dwarven hall dug into a mountain, seen through the cut-away',7,74,11,10,0.8,0.35],
['Moria: carved hall','Hall dug wider and lined with carved stone walls, torches',7,87,11,9,0.75,0.3],
['Dwarven forge-hall','Fixed layout, built with the game\u2019s own code',2,36,12,11,0.75,0.45],
['Spider brood lair','Silk walls and floor, cocoons, cobwebs, sticky web',3,36,28,9,0.75,0.4],
['Dragon\u2019s lair','Cavern under the rock, the hoard, an egg',4,15,16,8,0.8,0.4],
['Lair pieces up close','Sticky webs, cocoon, eggs, the hoard at four sizes',1,16,13,8,0.6,0.35],
['Timber house, Elven lodge, Orc lodge','Race buildings on the surface',5,20,50,16,0.7,0.45],
['Goblin, Kobold, Rat, Tribal, Devourer, Svartalfar','More race buildings and lairs',6,66,46,18,0.75,0.45]];
const L=document.getElementById('list'),V=document.getElementById('v');
S.forEach((s,i)=>{const b=document.createElement('button');b.innerHTML=s[0]+'<small>'+s[1]+'</small>';b.onclick=()=>{document.querySelectorAll('button').forEach(x=>x.classList.remove('on'));b.classList.add('on');V.src='replay.html?clean=1&scene='+s[2]+'&cx='+s[3]+'&cy='+s[4]+'&dist='+s[5]+'&pitch='+s[6]+'&yaw='+s[7]+'&t='+Date.now()};L.appendChild(b);if(!i)b.click()});
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=ROOT/'tests/lairs-replay')
    a = ap.parse_args()
    arena = ROOT/'tests/lairs-dump-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
    (arena/'lairs_dump.dme').write_text(dme + '\n#include "lairs_dump_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) LairsDumpRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/lairs_dump_test.dm', arena/'lairs_dump_test.dm')
    (arena/'rsc').mkdir()
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    with (ROOT/'tests/lairs-dump-compile.log').open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'lairs_dump.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    log = ROOT/'tests/lairs-dump-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-lairs-dump-') as data, log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"lairs_dump.json"}', '--cvar', 'opendream.topic_port=25893',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12393', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline and server.poll() is None:
            t = log.read_text(errors='replace')
            if 'LAIR_DUMP|complete' in t or '[ERRO]' in t: break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = log.read_text(errors='replace')
    print('\n'.join(re.findall(r'LAIR_DUMP\|[^\r\n]*|LAIR_NATIVE\|unbuilt[^\r\n]*', text)))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    if errors: print('\n'.join(errors[:5]))
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    for f in arena.glob('lairs-3d-*.json'): shutil.copy2(f, out/f.name)
    if (arena/'lairs-build.json').exists(): shutil.copy2(arena/'lairs-build.json', out/'lairs-build.json')
    for f in (arena/'rsc').glob('*.png'): shutil.copy2(f, out/f.name)
    for f in (ROOT/'game/Interface/models').glob('*.json'): shutil.copy2(f, out/f'model-{f.stem}.json')
    for f in (ROOT/'game/Interface/textures').glob('*.png'): shutil.copy2(f, out/f'r3t-{f.stem}.png')
    for f in (ROOT/'game/Icons/Remastered/Beasts').glob('*/*/*.png'):
        shutil.copy2(f, out/f'rb-{f.parent.parent.name}-{f.parent.name}-{f.stem}.png')
    page = (ROOT/'game/Interface/remastered.html').read_text()
    # No server: commands go nowhere (a byond:// address would start a navigation that stops the page).
    page = page.replace("function send(action,value){window.location.href=", "function send(action,value){return;window.location.href=", 1)
    # In the head, before the page's own script: it waits for the page to load.
    i = page.index('<head>') + len('<head>')
    (out/'replay.html').write_text(page[:i] + '<script>window.__errs=[];addEventListener("error",e=>__errs.push(e.message+" @"+e.lineno));' + REPLAY + '</script>' + page[i:])
    (out/'viewer.html').write_text(VIEWER)
    print('replay at', out/'replay.html', 'scenes:', sorted(f.name for f in out.glob('lairs-3d-*.json')))
    if errors or 'LAIR_DUMP|complete' not in text: raise SystemExit(1)


if __name__ == '__main__':
    main()
