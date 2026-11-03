#!/usr/bin/env python3
"""Real native right-click on an isolated original Human, then SetTarget.

Only a private mapless test world/profile is launched. It never opens or closes
the normal packaged game. A paused queue is fixture setup, not an input result.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from check_mouse import ROOT, RUNTIME, stop, write_hints


def main():
    out = ROOT / 'tests'
    result = dict(checks={}, scope='Isolated real Human/native context-menu check; original SetTarget verb; paused queue fixture.')
    slp, clp = out / 'right-click-server.log', out / 'right-click-client.log'
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-right-click-') as temp:
        base = Path(temp)
        world, probe = base / 'world', base / 'probe'
        probe.mkdir()
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'units', 'saves', 'ErrorLog.txt'))
        text = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = text.index('\tNew()'), text.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(text[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + text[end:], encoding='latin-1')
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        fixture = world / 'context.dme'
        shutil.copy2(out / 'right_click_menu_probe.dm', world / 'right_click_menu_probe.dm')
        fixture.write_text(dme + '\n#include "right_click_menu_probe.dm"\n', encoding='latin-1')
        result['skin_sha256'] = hashlib.sha256((world / 'skin.dmf').read_bytes()).hexdigest()
        result['checks']['map_keeps_original_context_menu_enabled'] = re.search(r'elem "map"\s+type = MAP.*?right-click = false', (world / 'skin.dmf').read_text(), re.S) is not None
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (out / 'right-click-compile.log').open('w') as log:
            subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60, check=True)
        cd = base / 'client'
        shutil.copytree(RUNTIME / 'client/Space Station 14.app/Contents/Resources', cd, ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
        hints = base / 'layout.json'
        write_hints(world / 'skin.dmf', hints)
        env.update(DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe),
                   DM_NATIVE_UI_TEST_TITLE='Remastered - Right-click Menu Check',
                   ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(ROOT / 'engine/webview-webkit'))

        def world_log():
            path = world / 'ErrorLog.txt'
            return path.read_text(errors='replace') if path.exists() else ''

        def state():
            try:
                return json.loads((probe / 'state.json').read_text())
            except (FileNotFoundError, ValueError):
                return {}

        def observed():
            rows = re.findall(r'CONTEXT\|state\|([^\r\n]+)', world_log())
            return json.loads(rows[-1]) if rows else {}

        def until(predicate, timeout=10):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if predicate():
                    return
                time.sleep(.1)
            raise TimeoutError('Native context check timed out: ' + str(observed()))

        def window():
            return next((w for w in state()['windows'] if w.get('viewports')), None) or max(state()['windows'], key=lambda w: w['width'] * w['height'])

        def action(**values):
            payload = dict(window=window()['id'], kind=5, x=0, y=0, code=0, modifiers=0, text='')
            payload.update(values)
            result.setdefault('inputs', []).append(payload.copy())
            (probe / 'action.pending').write_text(json.dumps(payload))
            (probe / 'action.pending').replace(probe / 'action.json')
            until(lambda: not (probe / 'action.json').exists(), 5)
            time.sleep(.35)

        def screenshot(filename):
            (probe / 'capture.txt').write_text(filename)
            # Screenshot encoding is asynchronous; creation alone can expose an
            # empty/partial PNG. Wait for its terminal IEND chunk before copying.
            def complete():
                path = probe / filename
                return path.exists() and path.read_bytes().endswith(b'IEND\xaeB`\x82')
            until(complete, 5)
            shutil.copy2(probe / filename, out / filename)

        try:
            with slp.open('w') as sl, clp.open('w') as cl:
                server = subprocess.Popen([str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', str(base / 'server-data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12169', '--cvar', 'opendream.topic_port=25669', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in slp.read_text(errors='replace'), 30)
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(RUNTIME / 'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12169', '--username', 'ContextCheck', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: 'CONTEXT|ready' in world_log() and state().get('windows'), 30)
                time.sleep(1)
                result['checks']['popup_menu_runtime_flag_enabled'] = 'CONTEXT|ready|popup=1' in world_log()
                border = re.findall(r'CONTEXT\|border\|([^\r\n]+)', world_log())
                result['border_diagnostics'] = json.loads(border[-1]) if border else {}
                result['checks']['retained_native_border_state_updates'] = bool(border) and all(result['border_diagnostics'].values())
                result['before'] = observed()
                result['interface_state'] = state().get('interfaceState')
                w = window()
                v = max(w['viewports'] or [{'rect': {'x': 0, 'y': 0, 'width': w['width'], 'height': w['height']}}], key=lambda v: v['rect']['width'] * v['rect']['height'])['rect']
                tile = min(v['width']/25, v['height']/19)
                px, py = v['x']+v['width']/2-2*tile, v['y']+v['height']/2
                action(kind=6, x=px/w['width'], y=py/w['height'])
                until(lambda: any(i['text'] == 'Context Human' for i in window()['contextItems']))
                result['checks']['native_right_click_opens_original_menu'] = True
                screenshot('right-click-dropdown.png')
                result['after_open'] = observed()
                result['checks']['opening_menu_preserves_selection_and_queue'] = observed() == result['before']
                result['menu_items'] = window()['contextItems']
                # Read the actual menu row bounds. This opens its verb
                # submenu; selecting a verb remains a separate native click.
                row = next(i for i in window()['contextItems'] if i['text'] == 'Context Human')['rect']
                action(x=(row['x']+row['width']/2)/w['width'], y=(row['y']+row['height']/2)/w['height'])
                until(lambda: any('SetTarget' in b['text'].replace(' ', '') for b in window()['buttons']))
                result['checks']['original_target_verb_is_available'] = True
                screenshot('right-click-verbs.png')
                b = next(b for b in window()['buttons'] if 'SetTarget' in b['text'].replace(' ', ''))['rect']
                action(x=(b['x']+b['width']/2)/w['width'], y=(b['y']+b['height']/2)/w['height'])
                until(lambda: observed().get('targetSelf'))
                result['after_action'] = observed()
                result['checks']['native_menu_runs_original_settarget'] = True
                result['checks']['settarget_preserves_existing_task_queue'] = bool(observed().get('activeSame') and observed().get('pendingSame') and observed().get('paused') and observed().get('selected') == 1)
        except Exception as error:
            result['error'] = repr(error)
            result['last_state'] = state()
            result['last_observed'] = observed()
        finally:
            stop(client)
            stop(server)
        (out / 'right-click-world.log').write_text(world_log())
        log = slp.read_text(errors='replace') + '\n' + clp.read_text(errors='replace') + '\n' + world_log()
        result['errors'] = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', log, re.M | re.I)
    result['passed'] = len(result['checks']) == 8 and all(result['checks'].values()) and not result.get('error') and not result['errors']
    (out / 'right-click-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
