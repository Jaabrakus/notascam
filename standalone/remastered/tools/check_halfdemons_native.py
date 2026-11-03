#!/usr/bin/env python3
"""The half-demon kinds in the real client's 3D view: a native client window on a mapless arena
(tests/halfdemons_native_probe.dm) with eight races as they are, Marked, Ashen and Hellblooded, and a Good
Altar, a darkened one and an Evil Altar. Checks each unit is drawn from its kind's 64 px sheet, that all of
them reach the 3D view with their pictures loaded, and keeps snapshots of the view. No input is sent except,
if WebKit holds the first frame, one recorded click on empty ground."""
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

INSTRUMENT = """function probeReport(){
 const things=(V3.things||[]);
 const units=things.filter(u=>u.kind==='mine');
 const loaded=units.filter(u=>{const k=(u.texd&&u.texd[v3face(u)])||u.tex;const e=k&&V3.tex.get(k);return e&&e.ok}).length;
 const altars=things.filter(u=>u.m3==='station:altar').map(u=>u.mat).sort();
 const bounds={v3:{on:!!V3.on,inv:!!V3.inv,pitch:V3.pitch},units:units.length,loaded,altars};
 const text=JSON.stringify(bounds);if(text!==window.probeLast){window.probeLast=text;send('proberects',text)}}
setInterval(()=>{try{probeReport()}catch(e){}},500);
send('ready','');"""


def main():
    result = {'checks': {}, 'scope': __doc__.strip().splitlines()[0]}
    tests = ROOT / 'tests'
    slp, clp = tests / 'halfdemons-native-server.log', tests / 'halfdemons-native-client.log'
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-halfdemons-native-') as temp:
        base = Path(temp)
        world = base / 'world'
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        shutil.copy2(tests / 'halfdemons_native_probe.dm', world / 'halfdemons_native_probe.dm')
        fixture = world / 'halfdemons_native.dme'
        fixture.write_text(dme + '\n#include "halfdemons_native_probe.dm"\n', encoding='latin-1')
        if os.environ.get('HD_NATIVE_USE32'):   # comparison run: the old 32 px unit pictures
            v3 = world / 'Code/Remastered/View3D.dm'
            v3.write_text(v3.read_text(encoding='latin-1').replace('var/remaster_3d_use64 = 1', 'var/remaster_3d_use64 = 0'), encoding='latin-1')
        html = world / 'Interface/remastered.html'
        html.write_text(html.read_text().replace("send('ready','');", INSTRUMENT))
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests / 'halfdemons-native-compile.log').open('w') as log_file:
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
            rows = re.findall(r'HD_NATIVE\|rects\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

        def hud_ready():
            rows = re.findall(r'HD_NATIVE\|state\|([^\r\n]+)', log())
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
            prefix = 'halfdemons-native-' + name
            (probe / 'capture-web.txt').write_text(prefix)
            until(lambda: (probe / f'{prefix}-panels.json').exists(), 10, 'HUD snapshot')
            time.sleep(1.5)
            for row in json.loads((probe / f'{prefix}-panels.json').read_text()):
                src = probe / row['file']
                if src.exists():
                    shutil.copy2(src, tests / row['file'])
                    result.setdefault('screenshots', []).append(str(tests / row['file']))

        checks = result['checks']
        try:
            with slp.open('w') as sl, clp.open('w') as cl:
                server = subprocess.Popen([str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'opendream.topic_port=25903', '--cvar', 'net.port=12403', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in slp.read_text(errors='replace'), 30, 'server')
                cd = client_copy()
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(RUNTIME / 'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12403', '--username', 'HalfDemonsNative', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: 'HD_NATIVE|ready' in log() and hud_ready() and state().get('windows') and rects().get('v3', {}).get('on'), 90, 'client and HUD')
                units = dict(re.findall(r'HD_NATIVE\|unit\|([^|]*)\|sheet=([^\r\n]*)', log()))
                result['units'] = units
                def sheet_ok(name, sheet):
                    kind = name.split(' ')[-1]
                    if kind == 'flying':
                        return 'Fly' in sheet
                    if kind == 'walking':
                        return '/Gargoyle-' in sheet
                    if kind.startswith('possessed'):
                        return sheet.endswith('-Possessed' + kind[-1] + '.dmi')
                    return sheet.endswith('-' + kind + '.dmi') if kind != 'plain' else not any(k in sheet for k in ('-Marked', '-Ashen', '-Hellblooded'))
                checks['every_unit'] = len(units) == 38
                checks['kinds_have_sheets'] = all(sheet_ok(n, s) for n, s in units.items())
                try:
                    until(lambda: rects()['v3']['inv'], 20, '3D view to draw')
                except TimeoutError:
                    result['wake_click'] = True
                    action(kind=5, x=.3, y=.3)
                    until(lambda: rects()['v3']['inv'], 30, '3D view to draw after the wake click')
                until(lambda: rects().get('units', 0) >= 38, 30, 'the units in 3D')
                checks['units_in_3d'] = rects().get('units', 0) >= 38
                until(lambda: rects().get('loaded', 0) >= 38, 90, 'the unit pictures to load')
                checks['pictures_load'] = rects().get('loaded', 0) >= 38
                checks['altars'] = rects().get('altars') == ['evil', 'holy', 'holy2']
                result['rects'] = rects()
                for k in range(3):
                    capture(f'units-{k + 1}')
                    time.sleep(.3)
                (world / 'halfdemons-native-done.txt').write_text('done')
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
        (tests / 'halfdemons-native-world.log').write_text(log())
        result['errors'] = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + clp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
        result['known_unrelated'] = [e for e in result['errors'] if 'Cache was ensured for a file (/r3t-ground-' in e]
        result['errors'] = [e for e in result['errors'] if e not in result['known_unrelated']]
        result['passed'] = not result.get('error') and not result['errors'] and len(checks) == 5 and all(checks.values())
        (tests / 'halfdemons-native-checks.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
        return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
