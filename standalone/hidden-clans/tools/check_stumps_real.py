#!/usr/bin/env python3
"""Stumps in the real client (run through tools/runlock.py): the packaged app's own engine, client and WebKit HUD
(Dungeon Master Remastered.app/Contents/Resources/game/runtime) on a temporary copy of game/ with a mapless scene
(tests/stumps_real_probe.dm): one villager with a fresh leg stump, a Silk Bandage and a Torch in its bag, selected.
Clicks go into the client window through its test probe (as hud-craft's hud_real.py does; the OS pointer is not
moved): the unit card's Health tab, then "Bandage it", then "Sear with a torch". The window is brought to the front
before each HUD still. Writes tests/stumps-real-checks.json and stills in reports/polish-2026-10-22/stump-care/real/.

  python3 tools/runlock.py --who stump-care -- caffeinate -d -i python3 tools/check_stumps_real.py
"""
import json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPRT = ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
REPLICA = ROOT.parent/'replica'
sys.path.insert(0, str(REPLICA/'tools'))
from skin_layout import write_hints  # noqa: E402
OUT = ROOT/'reports/polish-2026-10-22/stump-care/real'
OUT.mkdir(parents=True, exist_ok=True)

INSTRUMENT = """window.srErr=[];addEventListener('error',e=>window.srErr.push(String(e.message).slice(0,200)),true);
{const ce=console.error.bind(console);console.error=(...a)=>{window.srErr.push(a.map(String).join(' ').slice(0,200));ce(...a)}}
function srReport(){const hf=document.querySelector('#heroframe');const w0=document.documentElement.getBoundingClientRect().width,z=w0?w0/innerWidth:1;
 const shown=e=>e&&e.getClientRects().length&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden';
 const pos=e=>{if(!shown(e))return null;const b=e.getBoundingClientRect();return [Math.round(b.x+b.width/2),Math.round(b.y+b.height/2)]};
 const out={w:innerWidth*z,h:innerHeight*z,card:!!shown(hf),tab:hf?hf.dataset.tab||'':'',health:pos(hf&&hf.querySelector('[data-hftab=health]')),
  rows:hf?[...hf.querySelectorAll('.hfstump')].map(r=>r.textContent):[],btns:hf?[...hf.querySelectorAll('button[data-do=stump]')].map(b=>[b.textContent,pos(b)]):[],err:window.srErr.slice(0,5)};
 const t=JSON.stringify(out);if(t!==window.srLast){window.srLast=t;send('proberects',t)}}
setInterval(()=>{try{srReport()}catch(e){send('proberects',JSON.stringify({error:String(e)}))}},500);
send('ready','');"""


def main():
    result = {'checks': {}, 'scope': __doc__.strip().splitlines()[0]}
    checks = result['checks']
    work = Path(tempfile.mkdtemp(prefix='dm-stumps-real-'))
    world, probe = work/'world', work/'probe'
    probe.mkdir()
    shutil.copytree(ROOT/'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
    src = (world/'Code/World.dm').read_text(encoding='latin-1')
    a, b = src.index('\tNew()'), src.index('\nvar/Season')
    (world/'Code/World.dm').write_text(src[:a] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + src[b:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/stumps_real_probe.dm', world/'stumps_real_probe.dm')
    fixture = world/'stumps_real.dme'
    fixture.write_text(dme + '\n#include "stumps_real_probe.dm"\n', encoding='latin-1')
    hud = world/'Interface/remastered.html'
    h = hud.read_text(encoding='utf-8')
    k = "send('ready','');"
    assert h.count(k) == 1
    # the boot cover goes at once (its rAF removal stalls while the window is covered), as hud_real.py does
    h = h.replace("requestAnimationFrame(()=>requestAnimationFrame(()=>{c.classList.add('off');setTimeout(()=>c.remove(),900)}))", "c.classList.add('off');c.remove()")
    hud.write_text(h.replace(k, INSTRUMENT), encoding='utf-8')
    dotnet = APPRT/'dotnet/dotnet'
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    with (OUT/'compile.log').open('w') as out:
        subprocess.run([str(dotnet), str(REPLICA/'runtime/macos-x64/compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=out, stderr=subprocess.STDOUT, check=True, timeout=180)
    hints = work/'layout.json'
    write_hints(world/'skin.dmf', hints)
    cd = work/'client'
    shutil.copytree(APPRT/'client/Space Station 14.app/Contents/Resources', cd, ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
    cenv = dict(env, DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), DM_GAME_SNAPSHOT=str(probe/'game.png'),
                ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(APPRT/'webview-webkit'))
    slp, clp, elog = OUT/'server.log', OUT/'client.log', world/'ErrorLog.txt'

    def wait(cond, t):
        d = time.monotonic() + t
        while time.monotonic() < d:
            try:
                v = cond()
            except (KeyError, IndexError, TypeError, ValueError):
                v = None
            if v: return v
            time.sleep(.25)
        return None

    def log(): return elog.read_text(errors='replace') if elog.exists() else ''

    def rects():
        rows = re.findall(r'SR\|rects\|([^\r\n]+)', log())
        return json.loads(rows[-1]) if rows else {}

    def state():
        rows = re.findall(r'SR\|state\|([^\r\n]+)', log())
        return json.loads(rows[-1]) if rows else {}

    def win():
        st = json.loads((probe/'state.json').read_text())
        w = ([w for w in st['windows'] if w.get('viewports')] or [max(st['windows'], key=lambda w: w['width'] * w['height'])])[0]
        m = re.findall(r'panel\d+ hidden=false top-left=\((\d+),(\d+)\)\)? size=(\d+)x(\d+)', w['responder'])
        return w, tuple(map(int, m[0])) if m else (0, 0, w['width'], w['height'])

    def click(pt):
        R = rects()
        w, (ox, oy, pw, ph) = win()
        a = dict(window=w['id'], kind=5, x=(ox + pt[0]*pw/R['w'])/w['width'], y=(oy + pt[1]*ph/R['h'])/w['height'], code=0, modifiers=0, text='')
        (probe/'action.pending').write_text(json.dumps(a))
        (probe/'action.pending').replace(probe/'action.json')
        wait(lambda: not (probe/'action.json').exists(), 10)
        time.sleep(1.2)

    def front():
        subprocess.run(['osascript', '-e', f'tell application "System Events" to set frontmost of (first process whose unix id is {client.pid}) to true'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def capture(name):
        front()
        time.sleep(1.2)
        prefix = 'stumps-real-' + name
        (probe/'capture-web.txt').write_text(prefix)
        if not wait(lambda: (probe/f'{prefix}-panels.json').exists(), 15): return
        time.sleep(1.5)
        for row in json.loads((probe/f'{prefix}-panels.json').read_text()):
            f = probe/row['file']
            if f.exists():
                shutil.copy2(f, OUT/row['file'])
                result.setdefault('stills', []).append(str(OUT/row['file']))
        if (probe/'game.png').exists(): shutil.copy2(probe/'game.png', OUT/f'{prefix}-game.png')

    def button(label):
        for t, p in rects().get('btns', []):
            if t == label and p: return p
        return None

    server = client = None
    try:
        with slp.open('w') as sl, clp.open('w') as cl:
            server = subprocess.Popen([str(dotnet), str(APPRT/'server/Robust.Server.dll'), '--data-dir', str(work/'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}',
                '--cvar', 'opendream.topic_port=25947', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12447', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=sl, stderr=subprocess.STDOUT, cwd=world)
            assert wait(lambda: ' -> Ready' in slp.read_text(errors='replace'), 120), 'server not ready'
            client = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(APPRT/'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12447',
                '--username', 'StumpCare', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=cenv, stdout=cl, stderr=subprocess.STDOUT)
            checks['card_open'] = bool(wait(lambda: rects().get('card') and (probe/'state.json').exists() and state().get('hud'), 150))
            front()
            if rects().get('tab') != 'health':
                p = wait(lambda: rects().get('health'), 20)
                if p: click(p)
            checks['health_tab_by_click'] = bool(wait(lambda: rects().get('tab') == 'health' and rects().get('rows'), 15))
            checks['stump_line'] = rects().get('rows') == ['Left leg stump, bleeding: needs fire or a bandage']
            checks['buttons_now'] = [t for t, _ in rects().get('btns', [])] == ['Sear with a torch', 'Bandage it']
            result['open'] = rects()
            capture('open')
            p = button('Bandage it')
            if p: click(p)
            checks['bandaged_by_click'] = bool(wait(lambda: state().get('stump') == 'bandaged', 15))
            wait(lambda: rects().get('rows') == ['Left leg stump, bandaged: still bleeding slowly'], 10)
            result['bandaged'] = rects()
            checks['bandaged_line'] = rects().get('rows') == ['Left leg stump, bandaged: still bleeding slowly']
            capture('bandaged')
            hp = state().get('hp', 0)
            p = button('Sear with a torch')
            if p: click(p)
            checks['seared_by_click'] = bool(wait(lambda: state().get('stump') == 'sealed', 15))
            wait(lambda: rects().get('rows') == ['Left leg stump, seared shut'], 10)
            result['sealed'] = rects()
            result['hp'] = [hp, state().get('hp')]
            checks['sealed_line'] = rects().get('rows') == ['Left leg stump, seared shut'] and not rects().get('btns')
            capture('sealed')
            checks['hud_no_script_errors'] = not rects().get('err')
            (world/'stumps-real-done.txt').write_text('done')
    except Exception as error:
        result['error'] = repr(error)
    finally:
        for p in (client, server):
            if p and p.poll() is None:
                p.terminate()
                try: p.wait(10)
                except subprocess.TimeoutExpired: p.kill()
    (OUT/'world.log').write_text(log())
    errs = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
    result['known_unrelated'] = [e for e in errs if 'Cache was ensured for a file (/r3t-ground-' in e]
    result['errors'] = [e for e in errs if e not in result['known_unrelated']][:10]
    result['passed'] = not result.get('error') and not result['errors'] and len(checks) == 9 and all(checks.values())
    (ROOT/'tests/stumps-real-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)
    shutil.rmtree(work, ignore_errors=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
