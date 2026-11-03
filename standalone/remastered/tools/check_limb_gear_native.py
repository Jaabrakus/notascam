#!/usr/bin/env python3
"""Armour over a lost limb in the real client's 3D view (fixture tests/limb_gear_native_probe.dm, LimbGear.dm): a
kobold, a human and an orc in greaves, mail, vambraces and a sword, each whole and missing the right leg and arm.
Checks the server drew no right vambrace and no sword in the lost hand and cut the shared gear for the limbless three, the client's 3D view
loaded every unit's picture, and keeps the strips the client got and snapshots of the 3D view. Run it through the
lock: it opens a game window. No input is sent except, if WebKit holds the first frame, one click on empty ground."""
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

OUT = ROOT/'reports/polish-2026-10-22/qa-stability/limbs/native'
INSTRUMENT = """function probeReport(){
 const mine=(V3.things||[]).filter(u=>u.kind==='mine');
 const loaded=mine.filter(u=>{const tk=(u.texd&&u.texd[v3face(u)])||u.tex||'';const e=V3.tex.get(tk);return !!(e&&e.ok)}).length;
 const text=JSON.stringify({v3:{on:!!V3.on,inv:!!V3.inv,unitModels:!!V3.unitModels},units:mine.length,loaded,models:mine.filter(u=>u.model).length,dist:V3.dist});
 if(text!==window.probeLast){window.probeLast=text;send('proberects',text)}}
setInterval(()=>{try{probeReport()}catch(e){}},500);
setTimeout(()=>{try{V3.dist=7}catch(e){}},4000);
send('ready','');"""
NAMES = [f'{r} {k}' for r in ('Kobold', 'Human', 'Orc') for k in ('whole', 'no right leg or arm')]


def main():
    result = {'checks': {}, 'scope': __doc__.strip().splitlines()[0]}
    tests = ROOT/'tests'
    slp, clp = tests/'limb-gear-native-server.log', tests/'limb-gear-native-client.log'
    server = client = None
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dm-limb-gear-native-') as temp:
        base = Path(temp)
        world = base/'world'
        shutil.copytree(ROOT/'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world/'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world/'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        shutil.copy2(tests/'limb_gear_native_probe.dm', world/'limb_gear_native_probe.dm')
        fixture = world/'limb_gear_native.dme'
        fixture.write_text(dme + '\n#include "limb_gear_native_probe.dm"\n', encoding='latin-1')
        html = world/'Interface/remastered.html'
        html.write_text(html.read_text().replace("send('ready','');", INSTRUMENT))
        dotnet = RUNTIME/'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests/'limb-gear-native-compile.log').open('w') as log_file:
            subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=log_file, stderr=subprocess.STDOUT, check=True, timeout=180)
        probe = base/'probe'
        probe.mkdir()
        hints = base/'layout.json'
        write_hints(world/'skin.dmf', hints)
        env.update(DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(ROOT/'engine/webview-webkit'))

        def log():
            path = world/'ErrorLog.txt'
            return path.read_text(errors='replace') if path.exists() else ''

        def state():
            try:
                return json.loads((probe/'state.json').read_text())
            except (ValueError, FileNotFoundError):
                return {}

        def rects():
            rows = re.findall(r'LGN\|rects\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

        def hud_ready():
            rows = re.findall(r'LGN\|state\|([^\r\n]+)', log())
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
            (probe/'action.pending').write_text(json.dumps(payload))
            (probe/'action.pending').replace(probe/'action.json')
            until(lambda: not (probe/'action.json').exists(), 5, 'input delivery')

        def capture(name):
            prefix = 'limb-gear-native-' + name
            (probe/'capture-web.txt').write_text(prefix)
            until(lambda: (probe/f'{prefix}-panels.json').exists(), 10, 'HUD snapshot')
            time.sleep(1.5)
            for row in json.loads((probe/f'{prefix}-panels.json').read_text()):
                src = probe/row['file']
                if src.exists():
                    shutil.copy2(src, OUT/row['file'])
                    result.setdefault('screenshots', []).append(str((OUT/row['file']).relative_to(ROOT)))

        checks = result['checks']
        try:
            with slp.open('w') as sl, clp.open('w') as cl:
                server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', str(base/'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'opendream.topic_port=25891', '--cvar', 'net.port=12391', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in slp.read_text(errors='replace'), 30, 'server')
                cd = client_copy()
                client = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(RUNTIME/'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12391', '--username', 'LimbGear', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: 'LGN|ready' in log() and hud_ready() and state().get('windows') and rects().get('v3', {}).get('on'), 120, 'client and HUD')
                units = {u[0]: dict(state=u[1], worn=int(u[2]), right_vambrace_drawn=int(u[3]), cut_layers=int(u[4]), sword_drawn=int(u[5]), model=u[6])
                         for u in re.findall(r'LGN\|unit\|([^|]*)\|state=([^|]*)\|worn=(\d+)\|right_vambrace_drawn=(\d+)\|cut_layers=(\d+)\|sword_drawn=(\d+)\|model=([^\r\n|]*)', log())}
                result['units'] = units
                whole = [units.get(n) for n in NAMES if n.endswith('whole')]
                lost = [units.get(n) for n in NAMES if not n.endswith('whole')]
                checks['six_units_in_kit'] = len(units) == 6 and all(u and u['worn'] == 5 for u in units.values())
                checks['whole_units_whole'] = all(u and u['state'] == 'Normal' and u['right_vambrace_drawn'] and not u['cut_layers'] for u in whole)
                checks['lost_limbs_posed'] = all(u and u['state'] == 'NoRightArmNoRightLeg' for u in lost)
                checks['lost_arm_vambrace_not_drawn'] = all(u and not u['right_vambrace_drawn'] for u in lost)
                checks['lost_hand_sword_not_drawn'] = all(u and not u['sword_drawn'] for u in lost) and all(u and u['sword_drawn'] for u in whole)
                checks['shared_gear_cut'] = all(u and u['cut_layers'] >= 2 and u['model'] == '-' for u in lost)
                try:
                    until(lambda: rects()['v3']['inv'], 20, '3D view to draw')
                except TimeoutError:
                    result['wake_click'] = True
                    action(kind=5, x=.3, y=.3)
                    until(lambda: rects()['v3']['inv'], 30, '3D view to draw after the wake click')
                until(lambda: rects().get('loaded', 0) >= 6, 40, 'unit pictures in 3D')
                checks['pictures_loaded_in_3d'] = rects().get('loaded', 0) >= 6
                until(lambda: rects().get('dist', 99) <= 7.5, 15, 'the camera to come close')
                until(lambda: 'LGN|textures' in log(), 20, 'strip copies')
                time.sleep(2)
                result['rects'] = rects()
                for k in range(2):
                    capture(f'view-{k + 1}')
                    time.sleep(.5)
                (world/'lgn-done.txt').write_text('done')
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
        strips = sorted(world.glob('lgn-tex-*.png'))
        for f in strips:
            shutil.copy2(f, OUT/f.name)
        result['strips'] = [str((OUT/f.name).relative_to(ROOT)) for f in strips]
        checks['strips_kept'] = len(strips) == 6
        if len(strips) == 6:
            from PIL import Image, ImageDraw
            order = [OUT/f"lgn-tex-{n.lower().replace(' ', '-')}.png" for n in NAMES]
            ims = [Image.open(f).convert('RGBA') for f in order if f.exists()]
            if len(ims) == 6:
                w = max(i.width for i in ims) * 4
                h = ims[0].height * 4
                sheet = Image.new('RGB', (2 * w + 24, 3 * (h + 24) + 8), (96, 120, 72))
                d = ImageDraw.Draw(sheet)
                for i, im in enumerate(ims):
                    x, y = 8 + (i % 2) * (w + 8), 8 + (i // 2) * (h + 24)
                    d.text((x, y), NAMES[i], fill=(255, 255, 255))
                    sheet.paste(im.resize((im.width * 4, im.height * 4), Image.NEAREST), (x, y + 14), im.resize((im.width * 4, im.height * 4), Image.NEAREST))
                sheet.save(OUT/'limb-gear-native-strips-4x.png')
                result['sheet'] = str((OUT/'limb-gear-native-strips-4x.png').relative_to(ROOT))
        (tests/'limb-gear-native-world.log').write_text(log())
        result['errors'] = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + clp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
        result['known_unrelated'] = [e for e in result['errors'] if 'Cache was ensured for a file (/r3t-ground-' in e]
        result['errors'] = [e for e in result['errors'] if e not in result['known_unrelated']]
        result['passed'] = not result.get('error') and not result['errors'] and len(checks) == 8 and all(checks.values())
        (tests/'limb-gear-native-checks.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
        return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
