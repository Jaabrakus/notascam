#!/usr/bin/env python3
"""Bounded native mouse + embedded WebKit test in a private, mapless arena.

The fixture only creates units and targets. Commands come from real AppKit
clicks and keys, including the HUD's Add tasks button. HTML instrumentation
reports element bounds without dispatching actions or changing game state.
"""
import hashlib
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


def main():
    result = {'checks': {}, 'scope': 'Native AppKit pointer/key input and embedded WebKit HUD; desktop only.'}
    tests = ROOT / 'tests'
    slp, clp = tests / 'easy-orders-mouse-server.log', tests / 'easy-orders-mouse-client.log'
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-easy-mouse-') as temp:
        base = Path(temp)
        world = base / 'world'
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        shutil.copy2(tests / 'easy_orders_mouse_probe.dm', world / 'easy_orders_mouse_probe.dm')
        fixture = world / 'easy_mouse.dme'
        fixture.write_text(dme + '\n#include "easy_orders_mouse_probe.dm"\n', encoding='latin-1')
        html = world / 'Interface/remastered.html'
        html.write_text(html.read_text().replace("send('ready','');", """const originalUpdateHUD=window.updateHUD;
window.updateHUD=function(raw){originalUpdateHUD(raw);setTimeout(()=>{
 const ids=['#queue','#doNow','nav [data-value=orders]','[data-do=action][data-value=clear]'];
 const bounds={width:innerWidth,height:innerHeight,buttons:{}};
 ids.forEach(id=>{const el=document.querySelector(id),r=el.getBoundingClientRect();bounds.buttons[id]={x:r.x+r.width/2,y:r.y+r.height/2,w:r.width,h:r.height}});
 send('proberects',JSON.stringify(bounds));
},50)};
send('ready','');"""))
        result['source_sha256'] = {str(p.relative_to(ROOT / 'game')): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'game/Code/Remastered').glob('*.dm')}
        result['hud_sha256'] = hashlib.sha256((ROOT / 'game/Interface/remastered.html').read_bytes()).hexdigest()
        result['fixture_sha256'] = hashlib.sha256((world / 'easy_orders_mouse_probe.dm').read_bytes()).hexdigest()
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests / 'easy-orders-mouse-compile.log').open('w') as log:
            subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
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

        def observed():
            rows = re.findall(r'EASY_MOUSE\|state\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

        def until(predicate, timeout=15):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                if predicate():
                    return True
                time.sleep(.1)
            raise TimeoutError('Timed out waiting for native input outcome: ' + str(observed()))

        def action(window, **values):
            payload = dict(window=window['id'], kind=5, x=0, y=0, code=0, modifiers=0, text='')
            payload.update(values)
            result.setdefault('input_actions', []).append(dict(payload, time=time.time()))
            (probe / 'action.pending').write_text(json.dumps(payload))
            (probe / 'action.pending').replace(probe / 'action.json')
            until(lambda: not (probe / 'action.json').exists(), 5)
            time.sleep(.25)

        def window():
            return next((w for w in state()['windows'] if w.get('viewports')), None) or max(state()['windows'], key=lambda w: w['width'] * w['height'])

        def at(dx, dy):
            w = window()
            v = max(w['viewports'] or [{'rect': {'x': 0, 'y': 0, 'width': w['width'], 'height': w['height']}}], key=lambda v: v['rect']['width'] * v['rect']['height'])['rect']
            tile = min(v['width'] / 25, v['height'] / 19)
            return dict(x=(v['x'] + v['width']/2 + dx*tile)/w['width'], y=(v['y'] + v['height']/2 - dy*tile)/w['height'])

        def hud(selector):
            w = window()
            rectangles = re.findall(r'EASY_MOUSE\|hud\|proberects\|([^\r\n]+)', log())
            bounds = json.loads(rectangles[-1])
            panels = re.findall(r'panel\d+ hidden=false top-left=\((\d+),(\d+)\)\) size=(\d+)x(\d+)', w['responder'])
            if not panels:
                panels = re.findall(r'panel\d+ hidden=false top-left=\((\d+),(\d+)\) size=(\d+)x(\d+)', w['responder'])
            panel = min(panels, key=lambda p: abs(int(p[2])-bounds['width']))
            px, py, pw, ph = map(int, panel)
            b = bounds['buttons'][selector]
            action(w, x=(px + b['x']*pw/bounds['width'])/w['width'], y=(py + b['y']*ph/bounds['height'])/w['height'])

        try:
            with slp.open('w') as sl, clp.open('w') as cl:
                server = subprocess.Popen([str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'opendream.topic_port=25665', '--cvar', 'net.port=12165', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in slp.read_text(errors='replace'), 30)
                cd = client_copy()
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(RUNTIME / 'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12165', '--username', 'EasyOrdersMouse', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: 'EASY_MOUSE|ready' in log() and observed().get('hudReady') and state().get('windows'), 60)
                time.sleep(2)
                result['initial_window'] = window()
                result['initial_click'] = at(-4, 0)
                wins = subprocess.run([os.environ.get('TMPDIR', '/tmp') + '/winlist'], capture_output=True, text=True).stdout.splitlines()
                wid = next((line.split()[0] for line in wins if 'Dream Seeker' in line or 'Remastered' in line), None)
                if wid: subprocess.run(['screencapture', '-x', '-o', '-l' + wid, str(tests / 'easy-orders-mouse-native.png')])
                action(window(), **at(-4, 0))
                until(lambda: observed().get('selection') == ['Worker A'])
                result['checks']['native_click_selects_worker'] = True
                action(window(), **at(1, 0))
                until(lambda: observed().get('aActive') == 'Chop')
                result['checks']['native_tree_click_starts_chop'] = True
                hud('#queue')
                until(lambda: observed().get('queueMode') == 1)
                result['checks']['native_webkit_add_tasks_button'] = True
                action(window(), **at(4, 0))
                until(lambda: observed().get('aPending') == 1)
                result['checks']['second_tree_click_appends'] = True
                action(window(), **at(-4, 3))
                until(lambda: observed().get('selection') == ['Worker B'])
                result['checks']['switch_unit_keeps_first_queue_and_resets_mode'] = observed().get('aActive') == 'Chop' and observed().get('aPending') == 1 and observed().get('queueMode') == 0
                action(window(), kind=4, code=49, text=' ')
                until(lambda: observed().get('selection') == [])
                result['checks']['space_deselect_keeps_work'] = observed().get('aActive') == 'Chop'
                until(lambda: not observed().get('tree1') and not observed().get('tree2') and observed().get('aWood') == 4, 60)
                result['checks']['two_harvests_finish_and_collect_while_deselected'] = observed().get('selection') == [] and observed().get('aPending') == 0
                result['final_state'] = observed()
                result['native_window'] = window()
                (world / 'easy-mouse-done.txt').write_text('done')
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
        (tests / 'easy-orders-mouse-world.log').write_text(log())
        result['observations'] = re.findall(r'EASY_MOUSE\|(?:click|finish|hud\|(?:queue|action))[^\r\n]*', log())
        result['errors'] = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + clp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
        result['passed'] = not result.get('error') and not result['errors'] and len(result['checks']) == 7 and all(result['checks'].values())
        (tests / 'easy-orders-mouse-checks.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k:v for k,v in result.items() if k != 'native_window'}, indent=2), flush=True)
        return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
