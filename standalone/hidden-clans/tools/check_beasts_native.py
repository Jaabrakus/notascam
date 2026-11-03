#!/usr/bin/env python3
"""Huge beasts in the real client's 3D view: a native client window on a mapless arena
(tests/beasts_native_probe.dm) with four dragons - standing, walking, flying, a fire dragon
fighting - and a spider of each caste and age. Checks every one is sent to the 3D view as a
beast with its variant, size and action, that their pictures load in the page, that the
walker steps, the flyer flies and the fighter fights, and keeps snapshots of the HUD panels a
moment apart. No input is sent except, if WebKit holds the first frame, one recorded click on
empty ground."""
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from check_mouse import ROOT, RUNTIME, client_copy, stop, write_hints

INSTRUMENT = """function probeJaws(name,foe){const things=V3.things||[],t=things.find(u=>u.name===name),kd=t&&V3.disp.get(t.key),f=things.find(u=>u.name===foe);if(!kd||!kd.mouthPt||!f)return null;
 const c=document.getElementById('world3d').getBoundingClientRect(),s=v3project(kd.mouthPt),g=v3project([f.dx,v3groundAt(f.dx,f.dy)+0.45,-f.dy]);
 return {mouth:s&&[Math.round(c.x+s[0]),Math.round(c.y+s[1])],foe:g&&[Math.round(c.x+g[0]),Math.round(c.y+g[1])],anim:t.beast.anim,fresh:performance.now()/1000-kd.mouthAt<0.3,dist:Math.round(Math.hypot(t.x-f.x,t.y-f.y)*10)/10}}
function probeReport(){
 const things=(V3.things||[]);
 const beasts=things.filter(u=>u.beast);
 const loaded=[...V3.tex.keys()].filter(k=>k.startsWith('rb-')&&V3.tex.get(k).ok).length;
 const steps=Math.max(0,...beasts.map(u=>(V3.disp.get(u.key)||{}).n||0));
 const bounds={v3:{on:!!V3.on,inv:!!V3.inv,pitch:V3.pitch},beasts:beasts.length,loaded,steps,flying:beasts.filter(u=>u.beast.fly).length,dead:beasts.filter(u=>u.beast.dead).length,back:Math.round(10*Math.max(0,...beasts.map(u=>(V3.disp.get(u.key)||{}).boff||0)))/10,breaths:(V3.breaths||[]).length,parts:Math.max(0,...beasts.map(u=>(u.beast.parts||[]).length)),fired:Object.keys(V3.siegeAnim||{}).length,cone:(V3.fx||[]).filter(f=>f.sp==='breath').length,fxlit:[...V3.tex.keys()].includes('rb-breath-dragon.png')&&V3.tex.get('rb-breath-dragon.png').ok,
  webbed:things.filter(u=>u.webbed).length,beastegg:things.filter(u=>u.m3==='beastegg').length,eggsac:things.filter(u=>u.m3==='egg'&&u.mat==='spider').length,nests:things.filter(u=>u.m3==='beastnest').length,webs:things.filter(u=>u.m3==='web').length,webfx:Math.max(window.probeWebFx||0,(V3.fx||[]).filter(f=>f.sp==='web').length),bonds:things.filter(u=>u.beast&&u.beast.bound).length,vap:things.filter(u=>u.vap!=null).length,flames:things.filter(u=>u.flame).length,smoke:!!(V3.tex.get('#smoke')||{}).ok,carried:things.filter(u=>u.egg).length,fireMouth:probeJaws('Fire dragon','Dummy'),biteMouth:probeJaws('Bite dragon','Bite dummy'),chainAt:(()=>{const t=things.find(u=>u.name==='Chained dragon');if(!t)return null;const c=document.getElementById('world3d').getBoundingClientRect(),s=v3project([t.dx,v3groundAt(t.dx,t.dy)+0.6,-t.dy]);return s?[Math.round(c.x+s[0]),Math.round(c.y+s[1])]:null})(),
  anims:beasts.map(u=>u.beast.kind+':'+u.beast.variant+':'+u.beast.anim+':'+u.beast.size)};
 window.probeWebFx=bounds.webfx;const text=JSON.stringify(bounds);if(text!==window.probeLast){window.probeLast=text;send('proberects',text)}}
setInterval(()=>{try{probeReport()}catch(e){}},500);
send('ready','');"""


def main():
    result = {'checks': {}, 'scope': __doc__.strip().splitlines()[0]}
    tests = ROOT / 'tests'
    slp, clp = tests / 'beasts-native-server.log', tests / 'beasts-native-client.log'
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-beasts-native-') as temp:
        base = Path(temp)
        world = base / 'world'
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        shutil.copy2(tests / 'beasts_native_probe.dm', world / 'beasts_native_probe.dm')
        fixture = world / 'beasts_native.dme'
        fixture.write_text(dme + '\n#include "beasts_native_probe.dm"\n', encoding='latin-1')
        if os.environ.get('BEASTS_NATIVE_USE32'):   # comparison run: the old 32 px unit pictures
            v3 = world / 'Code/Remastered/View3D.dm'
            v3.write_text(v3.read_text(encoding='latin-1').replace('var/remaster_3d_use64 = 1', 'var/remaster_3d_use64 = 0'), encoding='latin-1')
        html = world / 'Interface/remastered.html'
        html.write_text(html.read_text().replace("send('ready','');", INSTRUMENT))
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests / 'beasts-native-compile.log').open('w') as log_file:
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
            rows = re.findall(r'BEASTS_NATIVE\|rects\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

        def hud_ready():
            rows = re.findall(r'BEASTS_NATIVE\|state\|([^\r\n]+)', log())
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
            prefix = 'beasts-native-' + name
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
                server = subprocess.Popen([str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'opendream.topic_port=25883', '--cvar', 'net.port=12383', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in slp.read_text(errors='replace'), 30, 'server')
                cd = client_copy()
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(RUNTIME / 'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12383', '--username', 'BeastsNative', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: 'BEASTS_NATIVE|ready' in log() and hud_ready() and state().get('windows') and rects().get('v3', {}).get('on'), 90, 'client and HUD')
                units = {u[0]: dict(kind=u[1], variant=u[2], anim=u[3], size=u[4], fly=u[5])
                         for u in re.findall(r'BEASTS_NATIVE\|unit\|([^|]*)\|kind=([^|]*)\|variant=([^|]*)\|anim=([^|]*)\|size=([^|]*)\|fly=([^|\r\n]*)', log())}
                result['units'] = units
                checks['every_beast_known'] = len(units) >= 12 and all(u['kind'] in ('dragon', 'spider', 'corpse') for k, u in units.items() if k != 'Person for scale') and units['Person for scale']['kind'] == 'none'
                checks['hatchling_small'] = float(units['Hatchling']['size']) < 1 and float(units['Red dragon']['size']) == 2.4
                checks['corpses_known'] = units['Dead dragon']['anim'] == 'death' and units['Dead spider']['anim'] == 'death'
                checks['variants'] = ([units[k]['variant'] for k in ('Red dragon', 'Ice dragon', 'Black dragon', 'Fire dragon')] == ['red', 'ice', 'black', 'green']
                    and [units[k]['variant'] for k in ('Young warrior', 'Older worker', 'Older hunter', 'Mature queen')] == ['warrior', 'worker', 'hunter', 'queen'])
                sizes = [float(units[k]['size']) for k in ('Young warrior', 'Older worker', 'Older hunter', 'Mature queen')]
                checks['spiders_grow'] = sizes[0] < sizes[1] <= sizes[2] < sizes[3]
                checks['dragon_flies'] = units['Black dragon']['anim'] == 'fly' and units['Black dragon']['fly'] == '1'
                try:
                    until(lambda: rects()['v3']['inv'], 20, '3D view to draw')
                except TimeoutError:
                    result['wake_click'] = True
                    action(kind=5, x=.3, y=.3)
                    until(lambda: rects()['v3']['inv'], 30, '3D view to draw after the wake click')
                until(lambda: rects().get('beasts', 0) >= 11, 30, 'the beasts in 3D')
                checks['beasts_in_3d'] = rects().get('beasts', 0) >= 11
                checks['corpses_in_3d'] = rects().get('dead', 0) >= 2
                until(lambda: rects().get('loaded', 0) >= 8, 60, 'the beast pictures to load')
                checks['pictures_load'] = rects().get('loaded', 0) >= 8
                until(lambda: rects().get('steps', 0) >= 3, 20, 'the walker to step')
                checks['walking'] = rects().get('steps', 0) >= 3
                checks['flying_in_3d'] = rects().get('flying', 0) >= 1
                until(lambda: any(':breathe:' in a or ':attack:' in a for a in rects().get('anims', [])), 30, 'the fire dragon to fight')
                checks['fighting'] = any(':breathe:' in a or ':attack:' in a for a in rects().get('anims', []))
                checks['no_sliding'] = rects().get('back', 0) == 0   # drawn on its own tile: it bites from its jaws' reach (Beasts.dm RmJawStrike)
                until(lambda: rects().get('breaths', 0) >= 1, 20, 'the fire dragon to breathe on its foe')
                checks['breath'] = rects().get('breaths', 0) >= 1
                until(lambda: rects().get('cone', 0) >= 1 and rects().get('fxlit'), 30, 'the fire breath special and its particles')
                checks['special_breath'] = rects().get('cone', 0) >= 1 and bool(rects().get('fxlit'))
                checks['parts_known'] = rects().get('parts', 0) >= 7
                until(lambda: rects().get('fired', 0) >= 1, 30, 'the ballista to shoot')
                checks['ballista_fires'] = rects().get('fired', 0) >= 1
                until(lambda: rects().get('beastegg', 0) >= 2 and rects().get('eggsac', 0) >= 2, 20, 'the eggs as 3D models')
                checks['eggs_3d'] = True
                checks['nests_3d'] = rects().get('nests', 0) >= 2
                until(lambda: rects().get('webs', 0) >= 1 and rects().get('webbed', 0) >= 1, 20, 'someone held fast in the sticky web')
                checks['sticky_web_3d'] = True
                until(lambda: rects().get('webfx', 0) >= 1, 30, "the spider's web shot")
                checks['web_shot_fx'] = True
                until(lambda: rects().get('bonds', 0) >= 1, 20, 'the chained dragon')
                checks['chained_3d'] = True
                def gear_keys():   # the fixture's last state line in the world log
                    lines = re.findall(r'BEASTS_NATIVE\|state\|(.*)$', log(), flags=re.M)
                    try:
                        return json.loads(lines[-1]).get('gearKeys') or {} if lines else {}
                    except ValueError:
                        return {}
                until(lambda: all(gear_keys().get(n) for n in ('Red knight', 'Dragon knight', 'Dragon mage')), 30, 'the knights drawn in 3D')
                g = gear_keys()
                result['gear_keys'] = g
                checks['dragon_coloured_gear_3d'] = '#ice:chest.plate.dragon' in g['Dragon knight'] and '#ice:helmet' in g['Dragon knight'] \
                    and '#blue:chest.robe.dragonrobe' in g['Dragon mage'] and '#' not in g['Red knight']
                result['rects'] = rects()
                for k in range(3):
                    capture(f'units-{k + 1}')
                    time.sleep(.3)
                # close looks: the camera on one unit at a time (the fixture moves the player there)
                for name, label in (('Chained dragon', 'chained'), ('Dragon knight', 'dragon-gear'), ('Fire dragon', 'breath')):
                    (world / 'beasts-native-focus.txt').write_text(name)
                    time.sleep(4)
                    if label == 'dragon-gear':   # the camera is by the smoke clouds and the fire now
                        until(lambda: rects().get('vap', 0) >= 8 and rects().get('flames', 0) >= 1 and rects().get('smoke'), 20, 'the smoke clouds and the fire')
                        checks['smoke_3d'] = True
                        checks['egg_carried_3d'] = rects().get('carried', 0) >= 1
                    capture(label)
                def jaws_on(key):   # the jaws drawn on the foe: mouth and foe close on screen while it fights
                    j = rects().get(key) or {}
                    return bool(j.get('mouth') and j.get('foe') and j.get('anim') in ('attack', 'breathe') and math.dist(j['mouth'], j['foe']) <= 80)
                for k in range(2, 5):   # the fight goes on: a few more looks at the jaws and the breath
                    time.sleep(1.1)
                    result.setdefault('fire_mouth', []).append(rects().get('fireMouth'))
                    capture(f'breath-{k}')
                until(lambda: jaws_on('fireMouth'), 20, "the fire dragon's jaws at its foe")
                (world / 'beasts-native-focus.txt').write_text('Bite dragon')
                time.sleep(4)
                until(lambda: jaws_on('biteMouth'), 30, "the biting dragon's jaws on its foe")
                checks['jaws_on_foe'] = True
                for k in range(1, 4):
                    result.setdefault('bite_mouth', []).append(rects().get('biteMouth'))
                    capture(f'bite-{k}')
                    time.sleep(0.6)
                (world / 'beasts-native-done.txt').write_text('done')
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
        (tests / 'beasts-native-world.log').write_text(log())
        result['errors'] = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + clp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
        result['known_unrelated'] = [e for e in result['errors'] if 'Cache was ensured for a file (/r3t-ground-' in e]
        result['errors'] = [e for e in result['errors'] if e not in result['known_unrelated']]
        result['passed'] = not result.get('error') and not result['errors'] and len(checks) == 26 and all(checks.values())
        (tests / 'beasts-native-checks.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
        return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
