#!/usr/bin/env python3
"""Buildings and lairs in the real client's 3D view, close up: a native client window on a
mapless arena (tests/lairs_native_probe.dm) that shows, scene by scene, the new 3D models
(sticky webs, a cobweb, a cocoon, the eggs, the hoard at its four sizes), a Dwarven forge-hall
and a spider's brood lair built with the game's own build code, and a dragon's lair dug into
rock underground. Checks each scene's models reach the 3D view and keeps a snapshot of the
HUD panels (the 3D view among them) for each. No input is sent except, if WebKit holds the
first frame, one recorded click on empty ground."""
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

# Close up: the camera at its nearest (the page's wheel zoom stops at 6), looking on.
INSTRUMENT = """function probeReport(){
 if(V3.dist!==window.probeDist&&window.probeDist)V3.dist=window.probeDist;
 const things=(V3.things||[]),m3={};for(const t of things)if(t.m3)m3[t.m3]=(m3[t.m3]||0)+1;
 const bounds={v3:{on:!!V3.on,inv:!!V3.inv,models:!!V3.models,dist:V3.dist},z:(V3.terrain||{}).z,m3,raf:window.probeRaf>0,err:window.probeErr||null,canvas:[$('world3d').clientWidth,$('world3d').clientHeight],win:[innerWidth,innerHeight],hidden:document.hidden,eye:(V3.eye||[]).map(v=>Math.round(v)),cx:[V3.cx,V3.cy],pitch:V3.pitch,mc:Math.round(V3.mcR||0)};
 const text=JSON.stringify(bounds);if(text!==window.probeLast){window.probeLast=text;send('proberects',text)}}
window.probeDist=7;window.probeRaf=0;(function f(){window.probeRaf++;requestAnimationFrame(f)})();
window.addEventListener('error',e=>{window.probeErr=String(e.message)+' @'+e.lineno+':'+e.colno});
setInterval(()=>{try{probeReport()}catch(e){}},500);
send('ready','');"""

# What each scene must show in 3D (model name -> at least this many).
SCENES = {
    1: {'web': 2, 'cobweb': 1, 'cocoon': 1, 'egg': 4, 'hoard0': 1, 'hoard1': 1, 'hoard2': 1, 'hoard3': 1},
    2: {'door': 1, 'bed': 2, 'table': 1, 'chair': 1, 'station:forge': 1},
    3: {'web': 1, 'cobweb': 2, 'cocoon': 2, 'egg': 1},
    4: {'hoard3': 1, 'egg': 1},
    5: {'dwarfpillar': 2, 'bed': 2, 'station:forge': 1},
}


def main():
    result = {'checks': {}, 'scope': __doc__.strip().splitlines()[0]}
    tests = ROOT / 'tests'
    slp, clp = tests / 'lairs-native-server.log', tests / 'lairs-native-client.log'
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-lairs-native-') as temp:
        base = Path(temp)
        world = base / 'world'
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        shutil.copy2(tests / 'lairs_native_probe.dm', world / 'lairs_native_probe.dm')
        fixture = world / 'lairs_native.dme'
        fixture.write_text(dme + '\n#include "lairs_native_probe.dm"\n', encoding='latin-1')
        html = world / 'Interface/remastered.html'
        html.write_text(html.read_text().replace("send('ready','');", INSTRUMENT))
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests / 'lairs-native-compile.log').open('w') as log_file:
            subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=log_file, stderr=subprocess.STDOUT, check=True, timeout=120)
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
            rows = re.findall(r'LAIRS_NATIVE\|rects\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

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
            prefix = 'lairs-native-' + name
            (probe / 'capture-web.txt').write_text(prefix)
            until(lambda: (probe / f'{prefix}-panels.json').exists(), 10, 'HUD snapshot')
            time.sleep(1.5)
            for row in json.loads((probe / f'{prefix}-panels.json').read_text()):
                src = probe / row['file']
                if src.exists():
                    shutil.copy2(src, tests / row['file'])
                    result.setdefault('screenshots', []).append(str(tests / row['file']))

        def shows(scene):
            r = rects()
            seen = r.get('m3', {})
            # scene 4 is underground: wait for that layer's data, not the surface's left over
            return (scene != 4 or r.get('z') == 2) and (scene != 5 or (r.get('z') == 1 and r.get('mc', 0) >= 7)) and all(seen.get(k, 0) >= n for k, n in SCENES[scene].items())

        checks = result['checks']
        try:
            with slp.open('w') as sl, clp.open('w') as cl:
                server = subprocess.Popen([str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'opendream.topic_port=25891', '--cvar', 'net.port=12391', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in slp.read_text(errors='replace'), 30, 'server')
                cd = client_copy()
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(RUNTIME / 'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12391', '--username', 'LairsNative', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: 'LAIR_NATIVE|scene|1' in log() and state().get('windows') and rects().get('v3', {}).get('on'), 90, 'client and HUD')
                try:
                    until(lambda: rects()['v3']['inv'], 20, '3D view to draw')
                except TimeoutError:
                    result['wake_click'] = True
                    action(kind=5, x=.3, y=.3)
                    try:
                        until(lambda: rects()['v3']['inv'], 20, '3D view to draw after the wake click')
                    except TimeoutError:
                        # WebKit draws nothing while its window is hidden behind another app:
                        # bring the test client's window to the front (no game input).
                        result['activated'] = True
                        subprocess.run(['osascript', '-e', f'tell application "System Events" to set frontmost of (first process whose unix id is {client.pid}) to true'], capture_output=True, timeout=10)
                        until(lambda: rects()['v3']['inv'], 30, '3D view to draw with the window in front')
                def front():
                    # WebKit stops drawing while its window is hidden behind another app: bring
                    # the test client's window to the front (no game input).
                    if rects().get('hidden'):
                        subprocess.run(['osascript', '-e', f'tell application "System Events" to set frontmost of (first process whose unix id is {client.pid}) to true'], capture_output=True, timeout=10)
                        time.sleep(1)
                for scene in sorted(SCENES):
                    front()
                    if scene > 1:
                        (world / f'lairs-native-next-{scene}.txt').write_text('next')
                        until(lambda: f'LAIR_NATIVE|scene|{scene}|' in log(), 60, f'scene {scene}')
                    try:
                        until(lambda: shows(scene), 30, f'scene {scene} models in 3D')
                    except TimeoutError:
                        pass
                    checks[f'scene_{scene}_models'] = shows(scene)
                    result[f'scene_{scene}_m3'] = rects().get('m3', {})
                    time.sleep(3)   # textures and the camera glide
                    front()
                    capture(f'scene-{scene}')
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
        (tests / 'lairs-native-world.log').write_text(log())
        result['unbuilt'] = re.findall(r'LAIR_NATIVE\|unbuilt\|([^\r\n]+)', log())
        result['errors'] = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + clp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
        result['known_unrelated'] = [e for e in result['errors'] if 'Cache was ensured for a file (/r3t-ground-' in e]
        result['errors'] = [e for e in result['errors'] if e not in result['known_unrelated']]
        result['passed'] = not result.get('error') and not result['errors'] and not result['unbuilt'] and len(checks) == len(SCENES) and all(checks.values())
        (tests / 'lairs-native-checks.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
        return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
