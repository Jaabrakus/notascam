#!/usr/bin/env python3
"""Deaths and bodies with real input (Gear3D.dm, the 3D page's dolls): a native client window, real AppKit mouse.

A private, mapless arena (tests/death_native_probe.dm): a soldier kills a foe with a blow, a unit with a stump bleeds
out, a unit is hit and walks off. For each body the test right-clicks it where the page's own picking finds it (the
menu must open) and picks the menu's first action (the server must get it), and checks no dead unit is left standing.
python3 tools/check_death_native.py [1|0]: the dolls on (DM_TEST_DOLLS=1, this private world only) or off. Your saves are
never touched. HTML instrumentation only reports positions and what is drawn; it sends no commands.
"""
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

INSTRUMENT = """function probeOn(x,y){const e=document.elementFromPoint(x,y);return !!e&&e.id==='world3d'}
function probeSpot(t){const c=document.getElementById('world3d').getBoundingClientRect(),g=v3groundAt(t.dx??t.x,t.dy??t.y);
 for(const h of [0.12,0.3,0.55])for(let r=0;r<=36;r+=3)for(let k=0;k<(r?16:1);k++){const s=v3project([t.dx??t.x,g+h,-(t.dy??t.y)]);if(!s)continue;const mx=s[0]+r*Math.cos(k/16*6.283),my=s[1]+r*Math.sin(k/16*6.283),p=v3pickThing(mx,my);
  if(!p||p!==t&&(p.id!==t.id||!t.id))continue;if(!probeOn(c.x+mx,c.y+my))continue;return {x:Math.round(c.x+mx),y:Math.round(c.y+my)}}
 return null}
function probeReport(){const things=V3.things||[],c=document.getElementById('world3d').getBoundingClientRect();
 let park=null;{const s=v3project([20,v3groundAt(20,19)+0.05,-19]);if(s&&probeOn(c.x+s[0],c.y+s[1])&&!v3pickThing(s[0],s[1]))park={x:Math.round(c.x+s[0]),y:Math.round(c.y+s[1])}}
 const bodies=things.filter(t=>t.body||/Body/.test(t.name||'')).map(t=>({name:t.name,x:t.x,y:t.y,doll:!!t.g3doll,spot:probeSpot(t)}));
 const dolls=(typeof RD!=='undefined'?RD.dolls:[]).filter(d=>!d.done).map(d=>({name:d.t&&d.t.name,alive:!!d.alive,kind:d.kind,landed:!!d.landed}));
 const m=document.getElementById('menu3d'),menu=m&&!m.hidden?[...m.querySelectorAll('button')].map(b=>{const r=b.getBoundingClientRect();return {t:(b.title||b.textContent||'').trim(),x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}}):[];
 const units=things.filter(t=>t.kind==='mine'||t.kind==='npc'||t.kind==='player').map(t=>({name:t.name,hidden:!!t.g3doll,spot:t.name==='Walker'?probeSpot(t):null}));
 const bounds={width:innerWidth,height:innerHeight,v3:{on:!!V3.on,inv:!!V3.inv,dist:Math.round(V3.dist*10)/10},spots:{park},bodies,dolls,units,menu,nodolls:!!window.G3NODOLLS};
 bounds.sent=window.probeSent||[];if(performance.now()-(window.probeSentAt||-1e9)<150)return;const text=JSON.stringify(bounds);if(text!==window.probeLast){window.probeLast=text;send('proberects',text)}}
{const s0=send;send=function(a,v){if(a!=='proberects'){window.probeSentAt=performance.now();(window.probeSent=window.probeSent||[]).push(a+'|'+String(v==null?'':v).slice(0,48));if(window.probeSent.length>16)window.probeSent.shift()}return s0(a,v)}}
setInterval(()=>{try{probeReport()}catch(e){}},250);
send('ready','');"""


def main():
    dolls = sys.argv[1] if len(sys.argv) > 1 else '1'
    tag = 'dolls-on' if dolls == '1' else 'dolls-off'
    result = {'checks': {}, 'scope': __doc__.strip().splitlines()[0], 'dolls': dolls, 'inputs': []}
    tests = ROOT / 'tests'
    slp, clp = tests / f'death-native-{tag}-server.log', tests / f'death-native-{tag}-client.log'
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-death-native-') as temp:
        base = Path(temp)
        world = base / 'world'
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        shutil.copy2(tests / 'death_native_probe.dm', world / 'death_native_probe.dm')
        fixture = world / 'death_native.dme'
        fixture.write_text(dme + '\n#include "death_native_probe.dm"\n', encoding='latin-1')
        html = world / 'Interface/remastered.html'
        html.write_text(html.read_text().replace("send('ready','');", INSTRUMENT))
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests / f'death-native-{tag}-compile.log').open('w') as log_file:
            subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=log_file, stderr=subprocess.STDOUT, check=True, timeout=180)
        probe = base / 'probe'
        probe.mkdir()
        hints = base / 'layout.json'
        write_hints(world / 'skin.dmf', hints)
        env.update(DM_TEST_DOLLS=dolls, DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(ROOT / 'engine/webview-webkit'))

        def log():
            path = world / 'ErrorLog.txt'
            return path.read_text(errors='replace') if path.exists() else ''

        def state():
            try:
                return json.loads((probe / 'state.json').read_text())
            except (ValueError, FileNotFoundError):
                return {}

        def rects():
            rows = re.findall(r'DEATH_NATIVE\|rects\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

        def observed():
            rows = re.findall(r'DEATH_NATIVE\|state\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

        def commands():
            return re.findall(r'DEATH_NATIVE\|cmd\|([^\r\n]+)', log())

        def specials(name):
            return log().count(f'DEATH_NATIVE|special|{name}')

        def until(predicate, timeout=15, what=''):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                try:
                    if predicate():
                        return True
                except (KeyError, IndexError, TypeError):
                    pass
                time.sleep(.1)
            raise TimeoutError('Timed out waiting for ' + what + ': ' + json.dumps(rects())[:900] + ' ' + json.dumps(observed())[:600])

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
            # Page coordinates -> this window's normalised coordinates, through the WebKit panel's frame.
            w = window()
            b = rects()
            panels = re.findall(r'panel\d+ hidden=false top-left=\((\d+),(\d+)\)\)? size=(\d+)x(\d+)', w['responder'])
            panel = min(panels, key=lambda p: abs(int(p[2]) - b['width']))
            x0, y0, pw, ph = map(int, panel)
            return dict(x=(x0 + px * pw / b['width']) / w['width'], y=(y0 + py * ph / b['height']) / w['height'])

        def spot(name):
            until(lambda: rects()['spots'][name], 15, f'a spot on screen for {name}')
            s = rects()['spots'][name]
            return to_window(s['x'], s['y'])

        def click_spot(name):
            action(kind=5, **spot(name))

        def right_click_spot(name):
            action(kind=6, **spot(name))

        def menu_button(prefix):
            until(lambda: any(b['t'].startswith(prefix) for b in rects()['menu']), 10, f'menu entry {prefix!r}')
            return next(b for b in rects()['menu'] if b['t'].startswith(prefix))

        def capture(name):
            prefix = f'death-native-{tag}-' + name
            (probe / 'capture-web.txt').write_text(prefix)
            until(lambda: (probe / f'{prefix}-panels.json').exists(), 10, 'HUD snapshot')
            time.sleep(1.5)
            for row in json.loads((probe / f'{prefix}-panels.json').read_text()):
                src = probe / row['file']
                if src.exists():
                    shutil.copy2(src, tests / row['file'])
                    result.setdefault('screenshots', []).append(str(tests / row['file']))

        checks = result['checks']
        def body(prefix):
            return next((q for q in rects().get('bodies', []) if (q['name'] or '').startswith(prefix)), None)

        def server_body(prefix):
            return any(b.startswith(prefix) for b in observed().get('bodies', []))

        def go(what):
            (world / f'death-native-go-{what}.txt').write_text('go')

        def steady_spot(prefix):
            # the camera may still be easing: wait till the body's spot holds still, then use it
            until(lambda: body(prefix) and body(prefix)['spot'], 15, f'{prefix} body on screen and pickable')
            last = None
            for _ in range(20):
                s = body(prefix)['spot']
                if last and abs(s['x'] - last['x']) <= 3 and abs(s['y'] - last['y']) <= 3:
                    return s
                last = s
                time.sleep(.5)
            return last

        def right_click_body(prefix, label):
            s = steady_spot(prefix)
            n0 = len(commands())
            action(kind=6, **to_window(s['x'], s['y']))
            until(lambda: rects()['menu'], 10, f'the menu on {prefix} body')
            menu = rects()['menu']
            result[label + '_menu'] = [b['t'] for b in menu]
            checks[label + '_menu_opens'] = bool(menu)
            capture(label + '-menu')
            # a harmless action (no unit sent walking): Use / open, else the first that isn't Close
            pick = next((m for m in menu if m['t'].startswith('Use')), None) or next((m for m in menu if not m['t'].startswith('Close')), menu[0])
            result[label + '_picked'] = pick['t'].split('\n')[0]
            action(kind=5, **to_window(pick['x'], pick['y']))
            time.sleep(1.5)
            got = [c for c in commands()[n0:] if not c.startswith(('hover3d', 'boxrefs', 'hudprefs', 'view3dsize'))]
            result[label + '_server_got'] = got
            checks[label + '_action_reaches_server'] = bool(got)
            close = next((m for m in rects().get('menu') or [] if m['t'].startswith('Close')), None)
            if close:
                action(kind=5, **to_window(close['x'], close['y']))

        try:
            with slp.open('w') as sl, clp.open('w') as cl:
                server = subprocess.Popen([str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'opendream.topic_port=25947', '--cvar', 'net.port=12447', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in slp.read_text(errors='replace'), 30, 'server')
                cd = client_copy()
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(RUNTIME / 'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12447', '--username', 'DeathNative', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: 'DEATH_NATIVE|ready' in log() and observed().get('hudReady') and state().get('windows') and rects().get('v3', {}).get('on'), 90, 'client and HUD')
                try:
                    until(lambda: rects()['v3']['inv'], 20, '3D view to draw')
                except TimeoutError:
                    action(kind=5, x=.3, y=.3)
                    until(lambda: rects()['v3']['inv'], 30, '3D view to draw after the wake click')
                checks['switch_as_asked'] = rects()['nodolls'] == (dolls != '1')
                until(lambda: rects()['spots']['park'], 10, 'open ground mid-view')
                action(kind=5, **to_window(rects()['spots']['park']['x'], rects()['spots']['park']['y']))
                time.sleep(2)
                capture('start')
                # 1. a blow death
                go('blow')
                until(lambda: server_body('Foe'), 10, "the foe's body")
                time.sleep(0.6)
                capture('blow-falling')
                time.sleep(3.5)
                result['after_blow'] = dict(dolls=rects()['dolls'], bodies=rects()['bodies'])
                checks['blow_nobody_standing'] = not any(d['alive'] and d['name'] == 'Foe' for d in rects()['dolls'])
                capture('blow-lying')
                right_click_body('Foe', 'blow_body')
                # 2. a bleed-out (a stump: Stumps.dm's death)
                go('bleed')
                until(lambda: server_body('Bleeder'), 10, "the bleeder's body")
                time.sleep(2.5)
                capture('bleed-slumping')
                time.sleep(3.5)
                result['after_bleed'] = dict(dolls=rects()['dolls'], bodies=rects()['bodies'])
                checks['bleed_nobody_standing'] = not any(d['alive'] and d['name'] == 'Bleeder' for d in rects()['dolls'])
                capture('bleed-lying')
                right_click_body('Bleeder', 'bleed_body')
                # 3. hit, then a step: no doll left behind, its own picture walks on
                go('step')
                time.sleep(0.4)
                result['step_at_0.4s'] = [d for d in rects()['dolls'] if d['name'] == 'Walker']
                time.sleep(2.0)
                capture('step-after')
                w = next((u for u in rects()['units'] if u['name'] == 'Walker'), None)
                result['step_after'] = dict(walker=w, dolls=[d for d in rects()['dolls'] if d['name'] == 'Walker'])
                checks['step_no_doll_left'] = not any(d['name'] == 'Walker' for d in rects()['dolls']) and bool(w) and not w['hidden']
                result['final'] = observed()
                (world / 'death-native-done.txt').write_text('done')
        except Exception as error:
            result['error'] = repr(error)
            result['last_rects'] = rects()
            result['last_observed'] = observed()
            result['server_got'] = commands()[-20:]
        finally:
            stop(client)
            stop(server)
        (tests / f'death-native-{tag}-world.log').write_text(log())
        result['errors'] = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + clp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
        result['known_unrelated'] = [e for e in result['errors'] if 'Cache was ensured for a file (/r3t-ground-' in e]
        result['errors'] = [e for e in result['errors'] if e not in result['known_unrelated']]
        result['passed'] = not result.get('error') and not result['errors'] and all(checks.values()) and len(checks) >= 8
        (tests / f'death-native-{tag}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'inputs'}, indent=2), flush=True)
        return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
