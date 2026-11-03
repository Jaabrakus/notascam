#!/usr/bin/env python3
"""Build tab with real input: a native client window, real AppKit clicks and drags.

A private, mapless arena (tests/build_menu_native_probe.dm) only creates two
workers and a stockpile of 8 stone. The test then plays it like a player: opens
the Build tab, picks Fortress wall, paints a 10-tile wall on the 3D view with a
mouse drag, stops placing, box-selects the workers on the 3D view and presses
the task's "Assign selected" button. The workers haul the stone and build 8
pieces, then the task waits for stone (4 more arrive: the fixture's only world
event) and finishes; the leftover piece goes back to the stockpile. HTML
instrumentation only reports element and tile positions; it sends no commands.
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

WALL = [(12, 15), (21, 15)]          # the wall line painted with the drag (open canvas in the iso view, clear of the workers)
TOWER = (16, 11)                     # the tile clicked for a tower (open ground in front of the wall, not hidden by it)
INSTRUMENT = """const originalUpdateHUD=window.updateHUD;
function probeReport(){
 const ids={nav:'nav [data-value=build]',stone:'[data-buildpick=fortress_wall]',assign:'[data-do=siteassign]',cancel:'#cancelmode',main:'main',catalogview:'[data-buildview=catalog]',tower:'[data-buildpick=tower]',sitecancel:'#buildSites [data-do=sitecancel]'};
 const bounds={width:innerWidth,height:innerHeight,buttons:{},tiles:{},v3:{on:!!V3.on,build:!!V3.build,inv:!!V3.inv,blueprints:(V3.blueprints||[]).length}};
 for(const [k,s] of Object.entries(ids)){const el=document.querySelector(s);if(!el||!el.getClientRects().length)continue;const r=el.getBoundingClientRect();const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);bounds.buttons[k]={x:r.x+r.width/2,y:r.y+r.height/2,w:r.width,h:r.height,disabled:!!el.disabled,visible:!!hit&&el.contains(hit)}}
 {const c=document.getElementById('world3d').getBoundingClientRect(),on=(x,y)=>{const e=document.elementFromPoint(x,y);return !!e&&e.id==='world3d'};const pts=(V3.things||[]).filter(u=>u.kind==='mine').map(u=>{const x=u.dx??u.x,y=u.dy??u.y;return v3project([x,0.55+v3groundAt(x,y),-y])}).filter(Boolean);
  if(pts.length){const xs=pts.map(p=>c.x+p[0]),ys=pts.map(p=>c.y+p[1]);const b={x0:Math.min(...xs)-45,y0:Math.min(...ys)-45,x1:Math.max(...xs)+45,y1:Math.max(...ys)+45};b.canvas=on(b.x0,b.y0)&&on(b.x1,b.y1);bounds.box=b}}
 for(const [x,y] of %s){if(!V3.vp)break;const p=v3project([x,typeof v3groundAt==='function'?v3groundAt(x,y):0,-y]);if(!p)continue;const c=document.getElementById('world3d').getBoundingClientRect();const e=document.elementFromPoint(c.x+p[0],c.y+p[1]);bounds.tiles[x+','+y]={x:c.x+p[0],y:c.y+p[1],canvas:!!e&&e.id==='world3d'}}
 const text=JSON.stringify(bounds);if(text!==window.probeLast){window.probeLast=text;send('proberects',text)}}
window.updateHUD=function(raw){originalUpdateHUD(raw);setTimeout(probeReport,60)};
setInterval(()=>{try{probeReport()}catch(e){}},500);
send('ready','');""" % json.dumps(WALL + [TOWER])


def main():
    result = {'checks': {}, 'scope': __doc__.strip().splitlines()[0], 'inputs': []}
    tests = ROOT / 'tests'
    slp, clp = tests / 'build-native-server.log', tests / 'build-native-client.log'
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-build-native-') as temp:
        base = Path(temp)
        world = base / 'world'
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        shutil.copy2(tests / 'build_menu_native_probe.dm', world / 'build_menu_native_probe.dm')
        fixture = world / 'build_native.dme'
        fixture.write_text(dme + '\n#include "build_menu_native_probe.dm"\n', encoding='latin-1')
        html = world / 'Interface/remastered.html'
        html.write_text(html.read_text().replace("send('ready','');", INSTRUMENT))
        result['source_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'game/Code/Remastered').glob('*.dm')}
        result['hud_sha256'] = hashlib.sha256((ROOT / 'game/Interface/remastered.html').read_bytes()).hexdigest()
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests / 'build-native-compile.log').open('w') as log:
            subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
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
            rows = re.findall(r'BUILD_NATIVE\|state\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

        def rects():
            rows = re.findall(r'BUILD_NATIVE\|rects\|([^\r\n]+)', log())
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
            raise TimeoutError('Timed out waiting for ' + what + ': ' + json.dumps(observed())[:1500])

        def window():
            return next((w for w in state()['windows'] if w.get('viewports')), None) or max(state()['windows'], key=lambda w: w['width'] * w['height'])

        def action(**values):
            w = window()
            payload = dict(window=w['id'], kind=5, x=0, y=0, code=0, modifiers=0, text='')
            payload.update(values)
            result['inputs'].append(dict(payload, time=time.time()))
            (probe / 'action.pending').write_text(json.dumps(payload))
            (probe / 'action.pending').replace(probe / 'action.json')
            until(lambda: not (probe / 'action.json').exists(), 5, 'input delivery')
            time.sleep(.3)

        def to_window(px, py):
            # Page coordinates -> this window's normalised coordinates, through
            # the WebKit panel's frame (as check_easy_orders_mouse.py does).
            w = window()
            b = rects()
            panels = re.findall(r'panel\d+ hidden=false top-left=\((\d+),(\d+)\)\)? size=(\d+)x(\d+)', w['responder'])
            panel = min(panels, key=lambda p: abs(int(p[2]) - b['width']))
            x0, y0, pw, ph = map(int, panel)
            return dict(x=(x0 + px * pw / b['width']) / w['width'], y=(y0 + py * ph / b['height']) / w['height'])

        def click(name):
            b = rects()['buttons'][name]
            action(kind=5, **to_window(b['x'], b['y']))

        def tile(x, y):
            t = rects()['tiles'][f'{x},{y}']
            if not t['canvas']:
                raise RuntimeError(f'tile {x},{y} is covered by HUD at {t}')
            return to_window(t['x'], t['y'])

        def drag(a, b):
            p, q = tile(*a), tile(*b)
            action(kind=7, x=p['x'], y=p['y'], x2=q['x'], y2=q['y'], modifiers=0)

        def drag_box():
            until(lambda: rects()['box'], 10, 'unit positions')
            b = rects()['box']
            if not b['canvas']:
                raise RuntimeError(f'selection box is covered by HUD at {b}')
            p, q = to_window(b['x0'], b['y0']), to_window(b['x1'], b['y1'])
            action(kind=7, x=p['x'], y=p['y'], x2=q['x'], y2=q['y'], modifiers=0)

        def wall():
            return next((s for s in observed().get('sites', []) if s['total'] == 10), None)

        def capture(name):
            prefix = 'build-native-' + name
            (probe / 'capture-web.txt').write_text(prefix)
            until(lambda: (probe / f'{prefix}-panels.json').exists(), 10, 'HUD snapshot')
            time.sleep(1.5)
            for row in json.loads((probe / f'{prefix}-panels.json').read_text()):
                source = probe / row['file']
                if source.exists():
                    shutil.copy2(source, tests / row['file'])
                    result.setdefault('screenshots', []).append(str(tests / row['file']))

        checks = result['checks']
        try:
            with slp.open('w') as sl, clp.open('w') as cl:
                server = subprocess.Popen([str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'opendream.topic_port=25845', '--cvar', 'net.port=12345', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in slp.read_text(errors='replace'), 30, 'server')
                cd = client_copy()
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(RUNTIME / 'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12345', '--username', 'BuildMenuNative', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: 'BUILD_NATIVE|ready' in log() and observed().get('hudReady') and state().get('windows') and rects().get('v3', {}).get('on'), 90, 'client and HUD')
                try:
                    until(lambda: rects()['v3']['inv'], 20, '3D view to draw')
                except TimeoutError:
                    # WebKit sometimes holds animation frames until the window is
                    # activated: one click on empty ground (nothing is selected, so
                    # it gives no order) wakes it. Recorded, and checked below.
                    result['wake_click'] = True
                    action(kind=5, x=.3, y=.3)
                    until(lambda: rects()['v3']['inv'], 30, '3D view to draw after the wake click')
                time.sleep(2)
                result['initial_window'] = {k: v for k, v in window().items() if k != 'responder'}
                checks['tiles_on_3d_canvas'] = all(t['canvas'] for t in rects()['tiles'].values())

                # 1. Open the Build tab and pick Stone wall.
                click('nav')
                until(lambda: observed()['tab'] == 'build' and 'stone' in rects()['buttons'], 15, 'Build tab with its catalog')
                checks['build_tab_opens_with_catalog'] = True
                capture('catalog')
                click('stone')
                until(lambda: observed()['mode'] == 'FortressWall' and rects()['v3']['build'], 15, 'fortress wall build mode in 3D')
                checks['catalog_pick_sets_build_mode'] = True

                # 2. Paint a 10-tile wall with a mouse drag on the 3D view (nobody selected).
                result['sites_before_drag'] = observed()['sites']   # anything here was not sent by this test
                checks['no_plan_before_the_drag'] = not observed()['sites'] and not observed()['selection']
                drag(*WALL)
                until(lambda: wall(), 15, 'the painted plan')
                site = wall()
                result['planned'] = site
                checks['drag_plans_one_task_of_ten_tiles'] = site['label'] == 'Fortress wall' and site['crew'] == 0
                checks['task_shows_needs'] = site['need'] == '10 stone: 8 in stockpiles, 2 missing'
                until(lambda: rects()['v3']['blueprints'] == 10, 10, '3D ghosts')
                checks['ghosts_in_3d'] = True

                # 3. Stop placing, box-select the two workers on the 3D view.
                click('cancel')
                until(lambda: not observed()['mode'] and not rects()['v3']['build'], 10, 'placement to stop')
                drag_box()
                until(lambda: sorted(observed()['selection']) == ['Mason A', 'Mason B'], 10, 'box selection')
                checks['box_select_on_3d_view'] = True

                # 4. Build tab, "Assign selected (2)" on the task.
                click('nav')
                until(lambda: observed()['tab'] == 'build' and 'assign' in rects()['buttons'] and not rects()['buttons']['assign']['disabled'], 15, 'Assign button')
                # The task card sits below the catalog: scroll the panel with the mouse wheel until the button shows.
                for attempt in range(12):
                    if rects()['buttons']['assign']['visible']:
                        break
                    m = rects()['buttons']['main']
                    before = rects()['buttons']['assign']['y']
                    action(kind=11, dy=-3 if attempt < 6 else 3, **to_window(m['x'], m['y']))
                    time.sleep(.8)
                    result.setdefault('scrolls', []).append([before, rects()['buttons']['assign']['y']])
                checks['assign_button_visible'] = rects()['buttons']['assign']['visible']
                click('assign')
                until(lambda: wall()['crew'] == 2, 10, 'workers on the task')
                checks['assign_button_puts_selected_on_task'] = True
                time.sleep(2)
                capture('assigned')

                # 5. They haul the 8 stone and build; the task waits; stone arrives; it finishes.
                until(lambda: observed()['walls'] == 8 and observed()['waiting'], 180, '8 walls then waiting for stone')
                o = observed()
                result['waiting_state'] = o
                checks['eight_built_from_stockpile_then_waits'] = o['stock'] == 0 and wall()['built'] == 8 and o['board'] == 1 and 'stone' in (wall()['note'] or '')
                click('nav') if observed()['tab'] != 'build' else None
                time.sleep(2)
                capture('waiting')
                until(lambda: wall()['done'] and observed()['carried'] == 0, 180, 'the wall to finish and leftovers to go back')
                time.sleep(2)
                o = observed()
                result['final_state'] = o
                checks['resumes_when_stock_arrives_and_finishes'] = o['refilled'] == 1 and o['walls'] >= 10 and wall()['built'] == 10
                checks['leftovers_back_on_stockpile'] = o['stock'] == 2 and o['carried'] == 0
                capture('finished')

                # 6. A one-click piece: What to build -> Tower, then a click on the 3D view.
                if 'catalogview' not in rects()['buttons']:
                    click('nav')
                    until(lambda: 'catalogview' in rects()['buttons'], 10, 'Build panel')
                click('catalogview')
                until(lambda: rects()['buttons'].get('tower', {}).get('visible'), 10, 'Tower card')
                click('tower')
                until(lambda: observed()['mode'] == 'Tower', 10, 'tower placement mode')
                time.sleep(1)
                action(kind=5, **tile(*TOWER))
                until(lambda: any(s['label'] == 'Tower' for s in observed()['sites']), 10, 'the tower task')
                tw = next(s for s in observed()['sites'] if s['label'] == 'Tower')
                result['tower'] = tw
                checks['tower_click_plans_3x3'] = tw['total'] == 9 and tw['need'] == '9 stone: 2 in stockpiles, 7 missing' and not observed()['mode']

                # 7. The task's own Cancel button.
                click('nav') if 'sitecancel' not in rects()['buttons'] else None
                until(lambda: rects()['buttons'].get('sitecancel', {}).get('visible'), 10, 'the task Cancel button')
                click('sitecancel')
                until(lambda: next(s for s in observed()['sites'] if s['label'] == 'Tower')['done'], 10, 'the tower task to be cancelled')
                checks['cancel_button_cancels_task'] = next(s for s in observed()['sites'] if s['label'] == 'Tower')['note'] == 'Cancelled'
                (world / 'build-native-done.txt').write_text('done')
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
        (tests / 'build-native-world.log').write_text(log())
        result['observations'] = re.findall(r'BUILD_NATIVE\|(?:hud|refill|FAIL)[^\r\n]*', log())
        result['errors'] = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + clp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
        # Known and unrelated: the 3D view asks for ground textures the server never sent (View3D.dm).
        result['known_unrelated'] = [e for e in result['errors'] if 'Cache was ensured for a file (/r3t-ground-' in e]
        result['errors'] = [e for e in result['errors'] if e not in result['known_unrelated']]
        result['passed'] = not result.get('error') and not result['errors'] and len(checks) == 15 and all(checks.values())
        (tests / 'build-native-checks.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k not in ('initial_window', 'inputs', 'source_sha256')}, indent=2), flush=True)
        return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
