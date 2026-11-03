#!/usr/bin/env python3
"""Fighting and taming great beasts with real input: a native client window, real AppKit mouse and keys.

A private, mapless arena (tests/beast_fight_native_probe.dm): four soldiers, a wild dragon on the
ground, the player's fire dragon, a crewed ballista under a wild dragon in the air (over its nest
of eggs), a dragon already chained down beside its keeper, butchered beast parts on the ground and
a knight in dragonscale. The test plays it as a player would:
  1. box-selects the soldiers with a mouse drag on the 3D view;
  2. right-clicks the wild dragon's left wing tile: the part ring and "Its left wing" show under
     the pointer, the menu's part grid lights the left wing and offers Chain it down; clicks the
     left wing, and the soldiers go for that wing and hurt it;
  3. clicks the fire dragon, presses F, clicks a spot: its breath special is cast there;
  4. clicks the ballista (its range ring and aim line show), right-clicks the dragon in the air
     and picks its left wing: the ballista shoots its wings;
  5. the wild dragon in the air, wings hurt, comes down and breathes on the ballista's crew;
  6. clicks the keeper, right-clicks the chained dragon, Feed it raw meat: he feeds it.
HTML instrumentation only reports positions and what is drawn; it sends no commands.
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
function probeNearest(t,mx,my){let bd=1e9,n=null;for(const q of arr(t.beast&&t.beast.parts)){const [PX,,PZ]=v3world({dx:q[0],dy:q[1]}),sp=v3project([PX,v3groundAt(q[0],q[1])+0.5,PZ]),d=sp?Math.hypot(sp[0]-mx,sp[1]-my):1e9;if(d<bd){bd=d;n=q[2]}}return n}
// A spot on screen where the page's own picking finds thing t (and, given a part, where that part is the nearest)
function probeSpot(t,part){const c=document.getElementById('world3d').getBoundingClientRect();let s;
 if(part){const q=arr(t.beast&&t.beast.parts).find(q=>q[2]===part);if(!q)return null;const [PX,,PZ]=v3world({dx:q[0],dy:q[1]});s=v3project([PX,v3groundAt(q[0],q[1])+0.5,PZ])}
 else{const kd=t.key&&V3.disp.get(t.key),alt=kd&&kd.alt||0,g=v3groundAt(t.dx,t.dy);s=v3project([t.dx,g+(alt>0.3?alt+(t.beast?0.5*(t.beast.size||1):0.55):0.55),-t.dy])}
 if(!s)return null;
 for(let r=0;r<=36;r+=3)for(let k=0;k<(r?16:1);k++){const mx=s[0]+r*Math.cos(k/16*6.283),my=s[1]+r*Math.sin(k/16*6.283),p=v3pickThing(mx,my);
  if(!p||p!==t&&p.id!==t.id)continue;if(part&&probeNearest(t,mx,my)!==part)continue;if(!probeOn(c.x+mx,c.y+my))continue;return {x:c.x+mx,y:c.y+my}}
 return null}
function probeReport(){
 const things=V3.things||[],by=n=>things.find(u=>u.name===n),c=document.getElementById('world3d').getBoundingClientRect();
 const wild=by('Wild dragon'),fire=by('Fire dragon'),sky=by('Sky dragon'),bal=things.find(u=>u.siege==='ballista'),chained=by('Chained dragon'),keeper=by('Keeper');
 const soldiers=things.filter(u=>u.kind==='mine'&&/^Soldier/.test(u.name||''));
 let box=null;{const pts=soldiers.map(u=>v3project([u.dx,0.55+v3groundAt(u.dx,u.dy),-u.dy])).filter(Boolean);
  if(pts.length===4){const xs=pts.map(p=>c.x+p[0]),ys=pts.map(p=>c.y+p[1]);box={x0:Math.min(...xs)-30,y0:Math.min(...ys)-45,x1:Math.max(...xs)+30,y1:Math.max(...ys)+25};box.canvas=probeOn(box.x0,box.y0)&&probeOn(box.x1,box.y1)}}
 let ground=null,park=null;{const s=v3project([33,v3groundAt(33,26)+0.05,-26]);if(s&&probeOn(c.x+s[0],c.y+s[1]))ground={x:c.x+s[0],y:c.y+s[1]}}
 {const s=v3project([31,v3groundAt(31,20)+0.05,-20]);if(s&&probeOn(c.x+s[0],c.y+s[1])&&!v3pickThing(s[0],s[1]))park={x:c.x+s[0],y:c.y+s[1]}}
 const m=document.getElementById('menu3d'),menu=m&&!m.hidden?[...m.querySelectorAll('button')].map(b=>{const r=b.getBoundingClientRect();return {t:b.title||b.textContent,here:b.classList.contains('here'),grid:!!b.closest('.m3grid'),x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}}):[];
 const tip=document.getElementById('partTip'),r2=p=>p&&{x:Math.round(p.x),y:Math.round(p.y)};
 const bounds={width:innerWidth,height:innerHeight,v3:{on:!!V3.on,inv:!!V3.inv,dist:Math.round(V3.dist*10)/10},box,
  spots:{wing:wild?r2(probeSpot(wild,'left wing')):null,fire:fire?r2(probeSpot(fire)):null,sky:sky?r2(probeSpot(sky)):null,ballista:bal?r2(probeSpot(bal)):null,ground:r2(ground),park:r2(park),chained:chained?r2(probeSpot(chained)):null,keeper:keeper?r2(probeSpot(keeper)):null},bonds:things.filter(u=>u.beast&&u.beast.bound).length,
  hover:V3.hoverPart?V3.hoverPart.n:null,tip:tip&&!tip.hidden?tip.textContent:null,tipSeen:window.probeTip||null,menu,aim:!!V3.aim,cone:(V3.fx||[]).filter(f=>f.sp==='breath').length,
  aimline:!!(bal&&bal.selected&&bal.starget&&bal.srange),bal:bal?{sel:!!bal.selected,st:bal.starget||null,sr:bal.srange||null,kind:bal.kind}:null,fired:Object.keys(V3.siegeAnim||{}).length,skyfly:sky&&sky.beast?!!sky.beast.fly:null,parts:wild&&wild.beast?arr(wild.beast.parts).map(q=>q[2]):[]};
 bounds.sent=window.probeSent||[];if(performance.now()-(window.probeSentAt||-1e9)<150)return;const text=JSON.stringify(bounds);if(text!==window.probeLast){window.probeLast=text;send('proberects',text)}}
// what the page sends (game commands only), and no report of ours in the same moment as one
{const s0=send;send=function(a,v){if(a!=='proberects'){window.probeSentAt=performance.now();(window.probeSent=window.probeSent||[]).push(a+'|'+String(v==null?'':v).slice(0,48));if(window.probeSent.length>16)window.probeSent.shift()}return s0(a,v)}}
{const hp=v3hoverPart;v3hoverPart=function(mx,my){hp(mx,my);const t=document.getElementById('partTip');if(t&&!t.hidden)window.probeTip=t.textContent}}   // the tag as the pointer showed it
setInterval(()=>{try{probeReport()}catch(e){}},250);
send('ready','');"""


def main():
    result = {'checks': {}, 'scope': __doc__.strip().splitlines()[0], 'inputs': []}
    tests = ROOT / 'tests'
    slp, clp = tests / 'fight-native-server.log', tests / 'fight-native-client.log'
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-fight-native-') as temp:
        base = Path(temp)
        world = base / 'world'
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        shutil.copy2(tests / 'beast_fight_native_probe.dm', world / 'beast_fight_native_probe.dm')
        fixture = world / 'fight_native.dme'
        fixture.write_text(dme + '\n#include "beast_fight_native_probe.dm"\n', encoding='latin-1')
        html = world / 'Interface/remastered.html'
        html.write_text(html.read_text().replace("send('ready','');", INSTRUMENT))
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests / 'fight-native-compile.log').open('w') as log_file:
            subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=log_file, stderr=subprocess.STDOUT, check=True, timeout=180)
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
            rows = re.findall(r'FIGHT_NATIVE\|rects\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

        def observed():
            rows = re.findall(r'FIGHT_NATIVE\|state\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

        def commands():
            return re.findall(r'FIGHT_NATIVE\|cmd\|([^\r\n]+)', log())

        def specials(name):
            return log().count(f'FIGHT_NATIVE|special|{name}')

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
            prefix = 'fight-native-' + name
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
                server = subprocess.Popen([str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'opendream.topic_port=25913', '--cvar', 'net.port=12413', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in slp.read_text(errors='replace'), 30, 'server')
                cd = client_copy()
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(RUNTIME / 'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12413', '--username', 'FightNative', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: 'FIGHT_NATIVE|ready' in log() and observed().get('hudReady') and state().get('windows') and rects().get('v3', {}).get('on'), 90, 'client and HUD')
                try:
                    until(lambda: rects()['v3']['inv'], 20, '3D view to draw')
                except TimeoutError:
                    result['wake_click'] = True
                    action(kind=5, x=.3, y=.3)
                    until(lambda: rects()['v3']['inv'], 30, '3D view to draw after the wake click')
                until(lambda: len(rects().get('parts', [])) >= 7, 30, 'the wild dragon and its parts in 3D')
                checks['parts_known'] = True
                # park the pointer on open ground mid-view (a click with nothing selected): resting by the
                # window's edge it would scroll the camera away
                until(lambda: rects()['spots']['park'], 10, 'open ground mid-view')
                click_spot('park')
                # zoom out with the mouse wheel, as a player would, until everyone in the arena is on screen
                for attempt in range(8):
                    time.sleep(1.5)
                    if all(v for k, v in rects()['spots'].items() if k != 'park') and rects()['box']['canvas']:
                        break
                    b = rects()['box']
                    action(kind=11, dy=-3, **to_window((b['x0'] + b['x1']) / 2, (b['y0'] + b['y1']) / 2))
                result['camera'] = dict(dist=rects()['v3']['dist'], spots=rects()['spots'])
                capture('arena')

                # 1. box-select the soldiers
                until(lambda: rects()['box'] and rects()['box']['canvas'], 15, 'the soldiers on screen')
                b = rects()['box']
                p, q = to_window(b['x0'], b['y0']), to_window(b['x1'], b['y1'])
                action(kind=7, x=p['x'], y=p['y'], x2=q['x'], y2=q['y'], modifiers=0)
                until(lambda: sorted(observed()['selected']) == [f'Soldier {i}' for i in range(1, 5)], 10, 'the soldiers selected')
                checks['box_select_soldiers'] = True

                # 2. right-click the wild dragon's left wing: ring, name by the pointer, the menu
                wings0 = observed()['Wild dragon']['wings']
                right_click_spot('wing')
                until(lambda: rects()['menu'], 10, 'the right-click menu')
                time.sleep(.4)
                r = rects()
                result['menu'] = [m['t'] for m in r['menu']]
                result['tip'] = r['tipSeen']
                result['wing_check'] = dict(hover=r['hover'], tip=r['tip'], tipSeen=r['tipSeen'])
                checks['hover_ring_on_wing'] = r['hover'] == 'left wing' and re.fullmatch(r'Its left wing · \d+%', r['tipSeen'] or '') is not None and not r['tip']
                attacks = [m['t'] for m in r['menu'] if m['t'].startswith('Attack its')]
                lit = [m['t'] for m in r['menu'] if m.get('here')]
                checks['menu_chain'] = 'Chain it down' in [m['t'] for m in r['menu']]
                checks['menu_lists_parts'] = len(attacks) == 7 and all(m['grid'] for m in r['menu'] if m['t'].startswith('Attack its')) and len(lit) == 1 and re.fullmatch(r'Attack its left wing \(\d+%\)', lit[0]) is not None
                capture('wing-menu')
                m = menu_button('Attack its left wing')
                action(kind=5, **to_window(m['x'], m['y']))
                until(lambda: sum(a == 'left wing:1' for a in observed()['aims']) == 4, 10, 'the soldiers ordered at the wing')
                checks['soldiers_go_for_wing'] = True
                until(lambda: observed()['Wild dragon']['wings'] < wings0, 60, 'the soldiers to hurt its wing')
                checks['wing_hurt'] = True
                result['wild_wings'] = [wings0, observed()['Wild dragon']['wings']]
                capture('wing-fight')

                # 3. the fire dragon's breath: click it, F, click a spot
                click_spot('fire')
                until(lambda: observed()['selected'] == ['Fire dragon'], 10, 'the fire dragon selected')
                checks['click_select_dragon'] = True
                action(kind=4, code=3, text='f')
                until(lambda: rects()['aim'] and observed()['aiming'], 10, 'aiming the special')
                checks['f_aims'] = True
                before = specials('Fire dragon')
                until(lambda: rects()['spots']['ground'], 10, 'the aimed spot on screen')
                g = rects()['spots']['ground']
                action(kind=5, **to_window(g['x'], g['y']))
                until(lambda: specials('Fire dragon') > before, 10, 'the breath to be cast')
                checks['f_breath_cast'] = True
                until(lambda: rects()['cone'] >= 1, 5, 'the breath stream in 3D')
                checks['breath_drawn'] = True
                capture('breath')

                # 4. the ballista: click it, right-click the dragon in the air, its left wing
                click_spot('ballista')
                until(lambda: observed()['selected'] == ['Ballista'], 10, 'the ballista selected')
                checks['click_select_ballista'] = True
                sky0 = observed()['Sky dragon']['wings']
                right_click_spot('sky')
                m = menu_button('Attack its left wing')
                result['sky_menu'] = [b['t'] for b in rects()['menu']]
                action(kind=5, **to_window(m['x'], m['y']))
                until(lambda: (observed().get('ballista') or {}).get('target') == 'Sky dragon' and observed()['ballista']['aim'] == 'left wing', 10, 'the ballista aimed at the wing')
                checks['ballista_aims_wing'] = True
                until(lambda: rects()['aimline'], 10, 'the ballista range ring and aim line')
                checks['ballista_aim_line'] = True
                capture('ballista')
                until(lambda: rects()['fired'] >= 1 and observed()['Sky dragon']['wings'] < sky0, 60, 'the ballista to hit its wings')
                checks['ballista_hits_wing'] = True

                # 5. the wild dragon's tricks: down while its wings carry it, its breath on the crew
                until(lambda: not observed()['Sky dragon']['flying'], 60, 'the wild dragon to come down')
                checks['wild_dragon_lands'] = True
                until(lambda: specials('Sky dragon') >= 1, 40, 'the wild dragon to breathe')
                checks['wild_dragon_breathes'] = True
                capture('wild')

                # 6. taming: the keeper (carrying meat) feeds the dragon chained beside him
                checks['chains_drawn'] = rects()['bonds'] >= 1 and observed()['Chained dragon']['bound'] == 1
                click_spot('keeper')
                until(lambda: observed()['selected'] == ['Keeper'], 10, 'the keeper selected')
                right_click_spot('chained')
                m = menu_button('Feed it raw meat (0/3)')
                checks['menu_feed'] = True
                capture('chained-menu')
                action(kind=5, **to_window(m['x'], m['y']))
                until(lambda: observed()['Chained dragon']['trust'] == 1, 30, 'the keeper to feed it')
                checks['fed'] = True
                capture('chained')
                result['final'] = observed()
                result['rects'] = rects()
                (world / 'fight-native-done.txt').write_text('done')
        except Exception as error:
            result['error'] = repr(error)
            result['last_rects'] = rects()
            result['last_observed'] = observed()
            result['page_sent'] = rects().get('sent')
            result['server_got'] = commands()[-20:]
        finally:
            stop(client)
            stop(server)
        (tests / 'fight-native-world.log').write_text(log())
        result['errors'] = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + clp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
        result['known_unrelated'] = [e for e in result['errors'] if 'Cache was ensured for a file (/r3t-ground-' in e]
        result['errors'] = [e for e in result['errors'] if e not in result['known_unrelated']]
        result['passed'] = not result.get('error') and not result['errors'] and len(checks) == 20 and all(checks.values())
        (tests / 'fight-native-checks.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'inputs'}, indent=2), flush=True)
        return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
