#!/usr/bin/env python3
"""New gear in the real client's 3D view: a native client window on a mapless arena
(tests/gear_native_probe.dm) where one unit of every playable race stands in its kit, a few
in mage kits, one in the game's own iron set, a row of women, two units walking to and fro and
two fighting a dummy through a real attack order. Checks every unit got its 64 px body, gear,
hair, beard and woman's top, that the pictures are strips of walk (and attack) frames, that the
3D view sees the walkers step and the fighters fight, and keeps snapshots of the HUD panels
(the 3D view among them) a moment apart. No input is sent except, if WebKit holds the first
frame, one recorded click on empty ground."""
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
 const mine=things.filter(u=>u.kind==='mine');
 const sample=mine.slice(0,4).map(u=>{const tk=(u.texd&&u.texd[v3face(u)])||u.tex||'';const e=V3.tex.get(tk);return {x:u.x,y:u.y,ly:u.ly||0,ground:v3groundAt(u.x,u.y),tex:tk,ok:!!(e&&e.ok),model:u.model||null,el:u.el||0}});
 const steps=Math.max(0,...mine.map(u=>(V3.disp.get(u.key)||{}).n||0));const wf={};for(const u of mine)wf[u.wf||1]=(wf[u.wf||1]||0)+1;
 const bounds={v3:{on:!!V3.on,inv:!!V3.inv,models:!!V3.models,unitModels:!!V3.unitModels,pitch:V3.pitch},units:mine.length,textured:mine.filter(u=>u.texd&&u.texd.length).length,wf,steps,attacking:mine.filter(u=>u.act==='attack').length,fxsent:mine.filter(u=>u.fxd&&u.fxd.length===4).length,fx:mine.filter(u=>{if(!u.fxd)return false;const e=V3.tex.get(u.fxd[v3face(u)]);return !!(e&&e.ok)}).length,sample};
 const text=JSON.stringify(bounds);if(text!==window.probeLast){window.probeLast=text;send('proberects',text)}}
setInterval(()=>{try{probeReport()}catch(e){}},500);
send('ready','');"""


def main():
    result = {'checks': {}, 'scope': __doc__.strip().splitlines()[0]}
    tests = ROOT / 'tests'
    slp, clp = tests / 'gear-native-server.log', tests / 'gear-native-client.log'
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-gear-native-') as temp:
        base = Path(temp)
        world = base / 'world'
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        shutil.copy2(tests / 'gear_native_probe.dm', world / 'gear_native_probe.dm')
        fixture = world / 'gear_native.dme'
        fixture.write_text(dme + '\n#include "gear_native_probe.dm"\n', encoding='latin-1')
        if os.environ.get('GEAR_NATIVE_USE32'):   # comparison run: the old 32 px unit pictures
            v3 = world / 'Code/Remastered/View3D.dm'
            v3.write_text(v3.read_text(encoding='latin-1').replace('var/remaster_3d_use64 = 1', 'var/remaster_3d_use64 = 0'), encoding='latin-1')
        html = world / 'Interface/remastered.html'
        html.write_text(html.read_text().replace("send('ready','');", INSTRUMENT))
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests / 'gear-native-compile.log').open('w') as log_file:
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
            rows = re.findall(r'GEAR_NATIVE\|rects\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

        def hud_ready():
            rows = re.findall(r'GEAR_NATIVE\|state\|([^\r\n]+)', log())
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
            prefix = 'gear-native-' + name
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
                server = subprocess.Popen([str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'opendream.topic_port=25881', '--cvar', 'net.port=12381', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in slp.read_text(errors='replace'), 30, 'server')
                cd = client_copy()
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(RUNTIME / 'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12381', '--username', 'GearNative', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: 'GEAR_NATIVE|ready' in log() and hud_ready() and state().get('windows') and rects().get('v3', {}).get('on'), 90, 'client and HUD')
                units = {u[0]: dict(icon=u[1], body64=u[2], worn=int(u[3]), kit=int(u[4]), gender=u[5], looks=[x for x in u[6].split(',') if x], frames=int(u[7]), fx=int(u[8]))
                         for u in re.findall(r'GEAR_NATIVE\|unit\|([^|]*)\|icon=([^|]*)\|body64=([^|]*)\|worn=(\d+)\|kit=(\d+)\|gender=([^|]*)\|looks=([^|]*)\|frames=(\d+)\|fx=(\d+)', log())}
                result['units'] = units
                checks['every_unit_has_64px_body'] = len(units) == 25 and all(u['body64'].startswith('Icons/Remastered/Races64/') for u in units.values())
                checks['kits_worn'] = all(u['worn'] == u['kit'] for u in units.values())
                women = {k: u['looks'] for k, u in units.items() if u['gender'] == 'Female'}
                checks['women_hair_and_tops'] = (len(women) == 5 and women['Human woman'][0] == 'Unders' and women['Human woman'][1] in ('HumanBrown', 'HumanBlack')
                    and women['Elf woman'] == ['Unders', 'ElfFemale'] and women['Dwarf woman'] == ['Unders', 'HumanBrown']
                    and women['Orc woman'] == ['Shirt'] and women['Goblin woman'] == ['Shirt'])
                checks['dwarf_beards'] = (units['Dwarf']['looks'] == ['Brown'] and units['Old iron set']['looks'] == ['Black']
                    and units['Grey-beard dwarf']['looks'] == ['Grey'] and units['Naked dwarf']['looks'] == [])
                checks['frame_strips'] = (all(u['frames'] == 5 for k, u in units.items() if u['kit'] and k not in ('Dwarf woman', 'Elf woman'))
                    and all(u['frames'] == 3 for k, u in units.items() if not u['kit']))
                try:
                    until(lambda: rects()['v3']['inv'], 20, '3D view to draw')
                except TimeoutError:
                    result['wake_click'] = True
                    action(kind=5, x=.3, y=.3)
                    until(lambda: rects()['v3']['inv'], 30, '3D view to draw after the wake click')
                until(lambda: rects().get('textured', 0) >= 25, 30, 'unit textures')
                checks['units_textured_in_3d'] = rects().get('textured', 0) >= 25
                until(lambda: rects().get('steps', 0) >= 4, 20, 'the walkers to step in 3D')
                checks['walking_in_3d'] = rects().get('steps', 0) >= 4 and rects().get('wf', {}).get('5', 0) >= 15
                until(lambda: rects().get('attacking', 0) >= 1, 30, 'the fighters to fight in 3D')
                checks['fighting_in_3d'] = rects().get('attacking', 0) >= 1
                magic = ('Elf', 'Lizardman', 'Vampire', 'Demon', 'Human mage', 'Elf mage', 'Orc shaman', 'Orc woman')
                checks['magic_effects'] = all(units[k]['fx'] == 4 for k in magic) and all(u['fx'] == 0 for k, u in units.items() if k not in magic)
                until(lambda: rects().get('fx', 0) >= len(magic), 20, 'the magic effects to load in 3D')
                checks['magic_effects_in_3d'] = rects().get('fx', 0) >= len(magic)
                until(lambda: 'GEAR_NATIVE|textures' in log(), 15, 'texture copies')
                result['rects'] = rects()
                for k in range(3):
                    capture(f'units-{k + 1}')
                    time.sleep(.3)
                (world / 'gear-native-done.txt').write_text('done')
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
        for f in list(tests.glob('gear-native-tex-*.png')) + list(tests.glob('gear-native-fx-*.png')):
            f.unlink()
        fx_sizes = []
        for f in world.glob('gear-native-fx-*.png'):
            shutil.copy2(f, tests / f.name)
            from PIL import Image
            fx_sizes.append(Image.open(f).size)
        result['fx_sizes'] = sorted(set(fx_sizes))
        checks['fx_atlases'] = bool(fx_sizes) and all(s == (320, 256) for s in fx_sizes)
        widths = []
        for f in world.glob('gear-native-tex-*.png'):
            shutil.copy2(f, tests / f.name)
            from PIL import Image
            widths.append(Image.open(f).size)
        result['texture_sizes'] = sorted(set(widths))
        checks['strip_pictures'] = bool(widths) and all(h == 64 and w in (192, 320) for w, h in widths)
        (tests / 'gear-native-world.log').write_text(log())
        result['errors'] = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + clp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
        result['known_unrelated'] = [e for e in result['errors'] if 'Cache was ensured for a file (/r3t-ground-' in e]
        result['errors'] = [e for e in result['errors'] if e not in result['known_unrelated']]
        result['passed'] = not result.get('error') and not result['errors'] and len(checks) == 12 and all(checks.values())
        (tests / 'gear-native-checks.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
        return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
