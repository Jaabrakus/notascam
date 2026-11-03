#!/usr/bin/env python3
"""Full Remastered game + real client + real AppKit mouse events: click-select,
drag-box select and right-click orders."""
import json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REPLICA = ROOT.parent/'replica'; RUNTIME = REPLICA/'runtime/macos-x64'
sys.path.insert(0, str(REPLICA/'tools'))
from check_browser import stop  # noqa: E402
from skin_layout import write_hints  # noqa: E402


def client_copy():
    target = ROOT/'tests/client'
    if not target.exists():
        shutil.copytree(RUNTIME/'client', target, ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
    return target/'Space Station 14.app/Contents/Resources'


def main():
    world = ROOT/'tests/mouse-world'
    if world.exists(): shutil.rmtree(world)
    shutil.copytree(ROOT/'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', 'ErrorLog.txt'))
    shutil.copy2(ROOT/'tests/mouse_probe.dm', world/'mouse_probe.dm')
    with (world/'Cave Crawlers.dme').open('a', encoding='latin-1') as dme: dme.write('\n#include "mouse_probe.dm"\n')
    dotnet = RUNTIME/'dotnet/dotnet'
    subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(world/'Cave Crawlers.dme')], env=dict(os.environ, DOTNET_ReadyToRun='0'),
                   stdout=subprocess.DEVNULL, check=True)
    probe = ROOT/'tests/mouse-probe'; probe.mkdir(exist_ok=True)
    for n in ('state.json', 'action.json'): (probe/n).unlink(missing_ok=True)
    hints = ROOT/'tests/mouse-layout.json'; write_hints(world/'skin.dmf', hints)
    env = dict(os.environ, DOTNET_ReadyToRun='0', DM_SKIN_LAYOUT_HINTS=str(hints), DM_TEST_RACE='Human', DM_NATIVE_UI_PROBE=str(probe),
               DM_GAME_SNAPSHOT=str(ROOT/'tests/mouse.png'), ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(ROOT/'engine/webview-webkit'))
    slp = ROOT/'tests/mouse-server.log'; clp = ROOT/'tests/mouse-client.log'; el = world/'ErrorLog.txt'
    def log(): return re.findall(r'MOUSE\|[^\r\n]*', el.read_text(errors='replace')) if el.exists() else []
    def state():
        try: return json.loads((probe/'state.json').read_text())
        except Exception: return {}
    def act(window, **a):
        payload = dict(window=window['id'], x=0, y=0, code=0, modifiers=0, text=''); payload.update(a)
        (probe/'action.pending').write_text(json.dumps(payload)); (probe/'action.pending').replace(probe/'action.json')
        while (probe/'action.json').exists(): time.sleep(.1)
        time.sleep(1.5)
    result = dict(steps=[])
    server = client = None
    try:
        with tempfile.TemporaryDirectory(prefix='dm-mouse-') as data, slp.open('w') as sl, clp.open('w') as cl:
            server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={world/"Cave Crawlers.json"}', '--cvar', 'opendream.topic_port=25655',
                '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12155', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=sl, stderr=subprocess.STDOUT, cwd=world)
            while ' -> Ready' not in slp.read_text(errors='replace'): time.sleep(.5)
            cd = client_copy()
            client = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(RUNTIME/'server/Content.Client.zip'),
                '--connect', '--connect-address', 'udp://127.0.0.1:12155', '--username', 'MouseTest', '--self-contained',
                '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline and not any(l.startswith('MOUSE|ready') for l in log()): time.sleep(1)
            time.sleep(3)
            ready = next(l for l in log() if l.startswith('MOUSE|ready'))
            offsets = [tuple(int(v) for v in o.split(',')) for o in ready.split('|')[2].split(';') if o]
            window = next((w for w in state()['windows'] if w.get('viewports')), None) or max(state()['windows'], key=lambda w: w['width'] * w['height'])
            view = max(window['viewports'] or [{'rect': {'x': 0, 'y': 0, 'width': window['width'], 'height': window['height']}}], key=lambda v: v['rect']['width'] * v['rect']['height'])['rect']
            tile = view['width'] / 19
            cx, cy = view['x'] + view['width'] / 2, view['y'] + view['height'] / 2
            def at(dx, dy): return (cx + dx * tile) / window['width'], (cy - dy * tile) / window['height']
            result.update(offsets=offsets, viewport=view)
            def step(name, **action):
                before = len(log()); act(window, **action)
                result['steps'].append(dict(name=name, observations=log()[before:]))
            x, y = at(-6, 6); step('activate_window', kind=5, x=x, y=y)
            x, y = at(*offsets[0]); step('click_unit_1', kind=5, x=x, y=y)
            x, y = at(*offsets[2]); step('click_unit_3', kind=5, x=x, y=y)
            minx = min(o[0] for o in offsets) - 1; maxx = max(o[0] for o in offsets) + 1
            miny = min(o[1] for o in offsets) - 1; maxy = max(o[1] for o in offsets) + 1
            x, y = at(minx, maxy); x2, y2 = at(maxx, miny)
            payload = dict(window=window['id'], kind=8, x=x, y=y, x2=x2, y2=y2, code=0, modifiers=0, text='')
            before = len(log())
            (probe/'action.pending').write_text(json.dumps(payload)); (probe/'action.pending').replace(probe/'action.json')
            pointer = []
            wins = subprocess.run([os.environ.get('TMPDIR', '/tmp') + '/winlist'], capture_output=True, text=True).stdout.splitlines()
            wid = next((l.split()[0] for l in wins if 'Remastered' in l or 'Dream Seeker' in l), None)
            for i in range(40):
                if i == 9 and wid: subprocess.run(['screencapture', '-x', '-o', '-l' + wid, str(ROOT/'tests/drag-box.png')])
                st = state(); pointer.append((round(st.get('mouse', {}).get('x', -1)), round(st.get('mouse', {}).get('y', -1))))
                time.sleep(.05)
            time.sleep(1)
            result['steps'].append(dict(name='drag_box_all', observations=log()[before:], pointer_during_drag=pointer,
                                        expected_from=(round(x * window['width']), round(y * window['height'])), expected_to=(round(x2 * window['width']), round(y2 * window['height']))))
            x, y = at(0, 3); step('right_click_ground', kind=6, x=x, y=y)
            (world/'mouse-done.txt').write_text('done'); time.sleep(1)
    except Exception as error: result['error'] = repr(error)
    finally:
        stop(client); stop(server)
    result['client_errors'] = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', clp.read_text(errors='replace'))
    result['server_errors'] = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', slp.read_text(errors='replace'))
    (ROOT/'tests/mouse-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
