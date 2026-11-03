#!/usr/bin/env python3
"""Units' abilities clicked as a player would, with real macOS input on the real client (tests/abilities_native_probe.dm):
the gargoyle's card, Interact tab, Fly; the vampire's middle-bar Interact (and the I key) for the creature beside it,
Feed From Villager; the Skull Staff mage's Spells tab, Raise Skeleton. The fixture only selects a unit (as a
click on it would); every tab, button and key is a real click or key press in the game window, which is
brought to the front first (a covered window keeps its loading cover)."""
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

INSTRUMENT = """function probeBtn(b){const r=b.getBoundingClientRect(),cs=getComputedStyle(b);if(r.width<2||r.height<2||cs.visibility==='hidden'||cs.display==='none')return null;let p=b;while(p){if(p.hidden||getComputedStyle(p).display==='none')return null;p=p.parentElement}return {t:b.textContent.trim(),k:b.matches('[data-hftab]')?'tab':b.closest('#nearcard')?'near':b.closest('#heroframe')?'card':'bar',x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)}}
function probeReport(){const sel=arr(model&&model.units).filter(u=>u.selected),hf=document.getElementById('heroframe'),panes={};
 if(hf)hf.querySelectorAll('.hfpane').forEach(p=>panes[p.dataset.pane]=[...p.querySelectorAll('button.hfab')].map(b=>b.textContent));
 const bar=[...document.querySelectorAll('[data-do="unitability"]')].filter(b=>b.offsetParent&&!(hf&&hf.contains(b))).map(b=>b.textContent);
 const r={sel:sel.map(u=>u.name),ab:sel.length===1?arr(sel[0].abilities):null,special:sel.length===1&&sel[0].special?sel[0].special.name:null,tab:hf&&hf.dataset.tab,panes,
  shown:hf?[...hf.querySelectorAll('button.hfab')].filter(b=>b.offsetParent).map(b=>b.textContent):[],bar,hf:!!hf,v3:!!V3.on,width:innerWidth,height:innerHeight,zoom:hudKC(),layoutH:document.documentElement.getBoundingClientRect().height,hfRect:(()=>{const q=hf&&hf.getBoundingClientRect();return q?[Math.round(q.left),Math.round(q.top),Math.round(q.width),Math.round(q.height)]:null})(),near:!!($('nearcard')&&!$('nearcard').hidden),
  btns:[...document.querySelectorAll('#heroframe [data-hftab],#heroframe button.hfab,#nearcard button,[data-do="action"][data-value="interact"]')].map(probeBtn).filter(Boolean),cover:!!document.getElementById('bootcover'),clicks:window.probeClicks||[],nk:window.nearKeyCalls};
 const text=JSON.stringify(r);if(text!==window.probeLast){window.probeLast=text;send('proberects',text)}}
document.addEventListener('pointerdown',e=>{const t=e.target,d=t&&t.closest?t.closest('button'):null;(window.probeClicks=window.probeClicks||[]).push([Math.round(e.clientX),Math.round(e.clientY),t?(t.id||t.tagName):'',d?(d.textContent.trim().slice(0,20)+(d.disabled?' (disabled)':'')):''])},true);
window.nearKeyCalls=0;const probeNK=window.nearKey;window.nearKey=function(){window.nearKeyCalls++;return probeNK.apply(this,arguments)};
setInterval(()=>{try{if(V3.on&&document.getElementById('bootcover'))bootCoverOff();probeReport()}catch(e){}},300);   // the loading cover: lifted once the 3D view runs (this copy only)
send('ready','');"""


def main():
    result = {'checks': {}, 'scope': __doc__.strip().splitlines()[0], 'units': {}}
    tests = ROOT / 'tests'
    slp, clp = tests / 'abilities-input-server.log', tests / 'abilities-input-client.log'
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-abilities-input-') as temp:
        base = Path(temp)
        world = base / 'world'
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        shutil.copy2(tests / 'abilities_native_probe.dm', world / 'abilities_native_probe.dm')
        fixture = world / 'abilities_native.dme'
        fixture.write_text(dme + '\n#include "abilities_native_probe.dm"\n', encoding='latin-1')
        html = world / 'Interface/remastered.html'
        page = html.read_text().replace("send('ready','');", INSTRUMENT)
        page = page.replace("requestAnimationFrame(()=>requestAnimationFrame(()=>{c.classList.add('off');setTimeout(()=>c.remove(),900)}))", "c.classList.add('off');c.remove()")
        html.write_text(page)
        ab = world / 'Code/Remastered/Abilities.dm'   # this copy only: say when the I key's verb runs
        ab.write_text(ab.read_text(encoding='latin-1').replace('\tset name = "Remaster-Interact-Key"\n\tset hidden = 1\n', '\tset name = "Remaster-Interact-Key"\n\tset hidden = 1\n\tworld.log << "ABIL|ikey|[length(Selected)]|[remaster_hud_ready]"\n'), encoding='latin-1')
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests / 'abilities-input-compile.log').open('w') as log_file:
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
            rows = re.findall(r'ABIL\|rects\|([^\r\n]+)', log())
            return json.loads(rows[-1]) if rows else {}

        def hud_ready():
            rows = re.findall(r'ABIL\|state\|([^\r\n]+)', log())
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

        def capture(name):
            prefix = 'abilities-input-' + name
            (probe / 'capture-web.txt').write_text(prefix)
            until(lambda: (probe / f'{prefix}-panels.json').exists(), 10, 'HUD snapshot')
            time.sleep(1.5)
            for row in json.loads((probe / f'{prefix}-panels.json').read_text()):
                src = probe / row['file']
                if src.exists():
                    shutil.copy2(src, tests / row['file'])
                    result.setdefault('screenshots', []).append(str(tests / row['file']))

        def want_tab(tab):
            (world / 'abilities-input-tab.txt').write_text(tab)

        checks = result['checks']
        try:
            with slp.open('w') as sl, clp.open('w') as cl:
                server = subprocess.Popen([str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'opendream.topic_port=25895', '--cvar', 'net.port=12395', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in slp.read_text(errors='replace'), 30, 'server')
                cd = client_copy()
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(RUNTIME / 'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12395', '--username', 'AbilitiesInput', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: 'ABIL|ready' in log() and hud_ready() and state().get('windows') and rects().get('v3'), 90, 'client and HUD')
                def window():
                    return next((w for w in state()['windows'] if w.get('viewports')), None) or max(state()['windows'], key=lambda w: w['width'] * w['height'])

                def action(**values):
                    w = window()
                    payload = dict(window=w['id'], kind=5, x=0, y=0, code=0, modifiers=0, text='')
                    payload.update(values)
                    result.setdefault('inputs', []).append(dict(payload, time=time.time()))
                    (probe / 'action.pending').write_text(json.dumps(payload))
                    (probe / 'action.pending').replace(probe / 'action.json')
                    until(lambda: not (probe / 'action.json').exists(), 5, 'input delivery')
                    time.sleep(.4)

                def to_window(px, py):
                    w = window()
                    b = rects()
                    panels = re.findall(r'panel\d+ hidden=false top-left=\((\d+),(\d+)\)\)? size=(\d+)x(\d+)', w['responder'])
                    panel = min(panels, key=lambda p: abs(int(p[2]) - b['width']))
                    x0, y0, pw, ph = map(int, panel)
                    return dict(x=(x0 + px * pw / b['width']) / w['width'], y=(y0 + py * ph / b['height']) / w['height'])

                def button(text, kind):   # kind: 'tab' (the card's tabs), 'card', 'near' (the card for those near), 'bar'
                    found = lambda: [b for b in rects().get('btns', []) if b['t'] == text and b['k'] == kind]
                    until(found, 15, f'the {text!r} button ({kind}) on screen')
                    b = found()[0]
                    z = rects().get('zoom') or 1   # element rects are in the HUD's layout pixels (remastered.html hudKC)
                    return to_window(b['x'] * z, b['y'] * z)

                def click(text, kind):
                    action(kind=5, **button(text, kind))

                def game():
                    rows = re.findall(r'ABIL\|state\|([^\r\n]+)', log())
                    return json.loads(rows[-1]) if rows else {}

                def select(name):
                    (world / 'abilities-native-select.txt').write_text(name)
                    rows = lambda: re.findall(r'ABIL\|selected\|' + re.escape(name) + r'\|([^|\r\n]*)\|', log())
                    until(lambda: rows() and rects().get('sel') == [rows()[-1]] and rects().get('ab') is not None, 20, name + ' selected')
                    time.sleep(1)

                # the game window in front: a covered one barely draws (and keeps its loading cover)
                pid = client.pid
                subprocess.run(['osascript', '-e', f'tell application "System Events" to set frontmost of (first process whose unix id is {pid}) to true'], capture_output=True)
                time.sleep(1.5)
                until(lambda: not rects().get('cover'), 20, 'the loading cover to go')

                # 1. the gargoyle: its card's Interact tab, then Fly
                select('Gargoyle')
                click('Interact', 'tab')
                until(lambda: rects().get('tab') == 'interact', 10, 'the Interact tab open')
                checks['interact_tab_click'] = True
                button('Fly', 'card')
                capture('gargoyle-interact-tab')
                checks['gargoyle_buttons'] = all(any(b['t'] == t and b['k'] == 'card' for b in rects()['btns']) for t in ('Fly', 'Rest', 'Retract Wings'))
                click('Fly', 'card')
                until(lambda: game().get('gargoyleFlying'), 15, 'the gargoyle to fly')
                checks['fly_clicked'] = True

                # 2. the vampire: the I key and the middle bar's Interact open the card for those beside it
                select('Vampire')
                action(kind=4, code=34, text='i')
                try:
                    until(lambda: rects().get('near'), 10, 'the I key to open the card for those near')
                    checks['i_key_opens_near'] = True
                    capture('vampire-i-key')
                    click('Close', 'near')
                    until(lambda: not rects().get('near'), 10, 'the card closed')
                except TimeoutError as e:
                    checks['i_key_opens_near'] = False
                    result['i_key'] = dict(error=str(e)[:300], server=re.findall(r'ABIL\|ikey\|[^\r\n]+', log()))
                click('Interact', 'bar')
                until(lambda: rects().get('near'), 10, 'the middle Interact to open the card for those near')
                checks['middle_interact_opens_near'] = True
                button('Feed From Villager', 'near')
                capture('vampire-near-card')
                blood = game().get('villagerBlood')
                click('Feed From Villager', 'near')
                until(lambda: (game().get('villagerBlood') or 0) < blood, 20, 'the vampire to feed')
                checks['feed_clicked'] = True

                # 3. the Skull Staff mage: Spells tab, Raise Skeleton
                select('Staff mage')
                click('Spells', 'tab')
                until(lambda: rects().get('tab') == 'spells', 10, 'the Spells tab open')
                button('Raise Skeleton', 'card')
                capture('mage-spells-tab')
                click('Raise Skeleton', 'card')
                until(lambda: game().get('skeletons', 0) >= 1, 15, 'a skeleton raised')
                checks['raise_skeleton_clicked'] = True
                click('Interact', 'tab')
                until(lambda: rects().get('tab') == 'interact', 10, 'the Interact tab open')
                time.sleep(1)
                capture('mage-interact-tab')
                result['mage_buttons'] = [b['t'] for b in rects()['btns']]
                result['passed_probe'] = True
                (world / 'abilities-native-done.txt').write_text('done')
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
        (tests / 'abilities-input-world.log').write_text(log())
        result['errors'] = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + clp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
        (tests / 'abilities-input-checks.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
        result['passed'] = not result.get('error') and not result['errors'] and len(checks) == 7 and all(checks.values())
        (tests / 'abilities-input-checks.json').write_text(json.dumps(result, indent=2) + '\n')
        return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
