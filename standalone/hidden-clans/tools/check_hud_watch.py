#!/usr/bin/env python3
"""Breakage watch for the shared HUD page and game code (overnight polish, qa-stability).

1. Every inline <script> block of game/Interface/remastered.html passes `node --check`.
2. The game code compiles (arena copy without maps) and a capture fixture (tests/hud_capture_test.dm) runs a
   small working village with the current code, writing what RemasterHUDData() and the 3D scene builder
   really send; no runtime errors on the way.
3. Headless Chrome loads the page with ?overlay and is fed those captures: one unit selected, then three;
   every command tab (model.tab), every unit-card tab and band-card tab is opened, the 3D view gets the scene.
   Any page error or console error fails the check (updateHUD catches its own throws and logs them).
4. The same page in a real WKWebView, the engine the game's HUD runs in (tools/rts_feel/wkcheck.swift, no window shown,
   no input): no script errors, and the page's entry points and every late script block are defined. WebKit stops
   parsing at a byond:// navigation, so a script after send('ready','') runs in Chrome but never in the game.
The page is built as the server sends it (RemasterHUDPage, Audio.dm: audio.js inlined at <!--rm-audio-->).
Writes tests/<label>-checks.json and small stills under reports/polish-2026-10-22/qa-stability/hud-watch/."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent/'replica/runtime/macos-x64'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
ERROR = re.compile(r'^.*(?:\[(?:ERRO|FATL)\]|runtime error|Exception occurred).*$', re.I | re.M)
TABS = ['village', 'work', 'build', 'realm', 'units', 'orders', 'guide', 'settings', 'log']


def port_free(port):
    """The game port (UDP) and its topic port (TCP, +13500) are both unused."""
    for p, kind in ((port, socket.SOCK_DGRAM), (port + 13500, socket.SOCK_STREAM)):
        with socket.socket(socket.AF_INET, kind) as s:
            try:
                s.bind(('127.0.0.1', p))
            except OSError:
                return False
    return True


def script_blocks(html):
    return [m.group(2) for m in re.finditer(r'<script(\s[^>]*)?>(.*?)</script>', html, re.S)
            if not (m.group(1) and 'src=' in m.group(1))]


def node_check(html, tmp):
    bad = []
    for i, code in enumerate(script_blocks(html)):
        path = tmp/f'block{i}.js'
        path.write_text(code, encoding='utf-8')
        r = subprocess.run(['node', '--check', str(path)], capture_output=True, text=True)
        if r.returncode:
            bad.append(dict(block=i, error=(r.stderr or r.stdout).strip()[-800:]))
    return bad


WK_EXPR = "['updateHUD','update3D','move3D','rmSfx','rfStats'].map(n=>n+'='+typeof window[n]).join(' ')"


def wk_run(page_file, tmp):
    """Real WebKit: script errors and which entry points exist, from rts-feel's wkcheck."""
    src = ROOT/'tools/rts_feel/wkcheck.swift'
    binary = ROOT/'tests/qa-bin/wkcheck'
    if not src.exists():
        return dict(skipped='no wkcheck.swift')
    if not binary.exists() or binary.stat().st_mtime < src.stat().st_mtime:
        binary.parent.mkdir(exist_ok=True)
        r = subprocess.run(['swiftc', '-O', str(src), '-o', str(binary)], capture_output=True, text=True)
        if r.returncode:
            return dict(skipped='swiftc failed: ' + r.stderr[-300:])
    r = subprocess.run([str(binary), str(page_file), WK_EXPR, '4'], capture_output=True, text=True, timeout=60)
    lines = r.stdout.splitlines()
    result = next((l for l in lines if l.startswith('RESULT ')), '')
    defined = dict(kv.split('=', 1) for kv in result[7:].split() if '=' in kv)
    return dict(errors=[l for l in lines if l.startswith(('ERROR', 'console.error'))][:20], defined=defined, raw=result[:300])


def page_as_sent():
    """remastered.html as RemasterHUDPage() sends it: audio.js inlined at the marker."""
    html = (ROOT/'game/Interface/remastered.html').read_text(encoding='utf-8')
    audio = ROOT/'game/Interface/audio.js'
    if audio.exists() and '<!--rm-audio-->' in html:
        html = html.replace('<!--rm-audio-->', '<script>' + audio.read_text(encoding='utf-8') + '</script>')
    return html


def capture(tmp, port, label):
    arena = tmp/'arena'
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players'))
    (arena/'units').mkdir()
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
    (arena/'hudcapture.dme').write_text(dme + '\n#include "hud_capture_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) HcRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/hud_capture_test.dm', arena/'hud_capture_test.dm')
    dotnet = SHARED/'dotnet/dotnet'
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    comp = subprocess.run([str(dotnet), str(SHARED/'compiler/DMCompiler.dll'), str(arena/'hudcapture.dme')],
                          env=env, capture_output=True, text=True)
    compile_errors = [l for l in comp.stdout.splitlines() if re.match(r'\s*Error\b', l)]
    (ROOT/f'tests/{label}-compile.log').write_text(comp.stdout[-20000:])
    if comp.returncode:
        return dict(compiled=False, compile_errors=compile_errors[:20]), {}
    log = ROOT/f'tests/{label}-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-hc-data-') as data, log.open('w') as out:
        proc = subprocess.Popen([str(dotnet), str(SHARED/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"hudcapture.json"}', '--cvar', f'opendream.topic_port={port + 13500}',
            '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={port}', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        try:
            proc.wait(240)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                proc.kill()
    text = log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    world_text = errorlog.read_text(errors='replace') if errorlog.exists() else ''
    models = {}
    for name in ('hud-one', '3d-one', 'hud-band', '3d-band', 'hud-tab-build', 'hud-village-lineage', 'hud-village-board', 'hud-village-log'):
        f = arena/f'hc-{name}.json'
        if f.exists():
            models[name] = json.loads(f.read_text(errors='replace'))
    return dict(compiled=True, complete='HC|complete' in text, runtime_errors=ERROR.findall(text + '\n' + world_text)[:20],
                warnings=len(re.findall(r'Warning', comp.stdout))), models


def page_run(html, models, tmp, shots, label):
    from playwright.sync_api import sync_playwright
    errors, steps = [], []
    page_file = tmp/'remastered.html'
    page_file.write_text(html.replace('window.location.href=', 'window.testLastURL='), encoding='utf-8')
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, headless=True,
                                     args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        page = browser.new_page(viewport=dict(width=1440, height=900))
        where = ['load']
        page.on('pageerror', lambda e: errors.append(f'[{where[0]}] pageerror: {e}'[:400]))
        page.on('console', lambda c: errors.append(f'[{where[0]}] console: {c.text}'[:400])
                if c.type == 'error' and 'Failed to load resource' not in c.text and 'net::ERR_' not in c.text else None)
        page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
        page.wait_for_timeout(500)
        gl = page.evaluate('()=>typeof V3!=="undefined"&&!!V3.gl')
        drawn = {}

        def step(name, js, arg=None, wait=250):
            where[0] = name
            try:
                page.evaluate(js, arg) if arg is not None else page.evaluate(js)
            except Exception as e:
                errors.append(f'[{name}] evaluate: {e}'[:400])
            page.wait_for_timeout(wait)
            steps.append(name)

        for sel in ('one', 'band'):
            hud, scene = models.get(f'hud-{sel}'), models.get(f'3d-{sel}')
            if not hud:
                continue
            hud = dict(hud, view3d=1)   # the capture has no client, so 3D is off in it; the game is always 3D
            step(f'{sel}:updateHUD', 'm=>{updateHUD(JSON.stringify(m));updateHUD(JSON.stringify(m))}', hud)
            if scene:
                step(f'{sel}:update3D', 'm=>{window.update3D&&update3D(JSON.stringify(m))}', scene, 1500)
                gl = gl or page.evaluate('()=>typeof V3!=="undefined"&&!!V3.gl')
                drawn[sel] = page.evaluate('()=>typeof V3!=="undefined"?{on:!!V3.on,things:(V3.things||[]).length}:null')
            if sel == 'one':
                page.screenshot(path=str(shots/f'{label}-one.jpg'), type='jpeg', quality=60)
            # a nav click opens the page by adding panel-open to the body (only with the app's overlay host)
            for tab in TABS:
                m = dict(hud, tab=tab)
                step(f'{sel}:tab={tab}', 'm=>{updateHUD(JSON.stringify(m));document.body.classList.add("panel-open")}', m)
            step(f'{sel}:tab=none', 'm=>{updateHUD(JSON.stringify(m));document.body.classList.remove("panel-open")}', dict(hud, tab=''))
            attr = 'data-hftab' if sel == 'one' else 'data-gftab'
            names = page.evaluate(f'()=>[...new Set([...document.querySelectorAll("[{attr}]")].map(e=>e.getAttribute("{attr}")))]')
            for n in names:
                step(f'{sel}:card={n}', f'n=>{{const b=[...document.querySelectorAll("[{attr}]")].find(e=>e.getAttribute("{attr}")===n);if(b)b.click()}}', n)
                step(f'{sel}:card={n}:refresh', 'm=>updateHUD(JSON.stringify(m))', hud, 150)
            page.screenshot(path=str(shots/f'{label}-{sel}-last.jpg'), type='jpeg', quality=60)
        for name in ('hud-tab-build', 'hud-village-lineage', 'hud-village-board', 'hud-village-log'):
            if models.get(name):
                step(f'panel:{name}', 'm=>{updateHUD(JSON.stringify(m));document.body.classList.add("panel-open")}', dict(models[name], view3d=1), 400)
                if name in ('hud-tab-build', 'hud-village-log'):
                    page.screenshot(path=str(shots/f'{label}-{name}.jpg'), type='jpeg', quality=60)
        where[0] = 'idle'
        page.wait_for_timeout(1500)
        browser.close()
    return dict(webgl=gl, scene=drawn, steps=len(steps), errors=errors[:30], error_count=len(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', default='hud-watch')
    parser.add_argument('--port', type=int, default=12483, help='first port to try; the next free one is used')
    args = parser.parse_args()
    while not port_free(args.port):   # other sessions run this watch too
        args.port += 2
    shots = ROOT/'reports/polish-2026-10-22/qa-stability/hud-watch'
    shots.mkdir(parents=True, exist_ok=True)
    started = time.time()
    html = page_as_sent()
    with tempfile.TemporaryDirectory(prefix='dm-hudwatch-') as tmp:
        tmp = Path(tmp)
        syntax = node_check(html, tmp)
        server, models = capture(tmp, args.port, args.label)
        page = page_run(html, models, tmp, shots, args.label) if models else dict(errors=['no captured models'], error_count=1)
        wk_file = tmp/'wk'/'remastered.html'
        wk_file.parent.mkdir()
        wk_file.write_text(html, encoding='utf-8')
        webkit = wk_run(wk_file, tmp)
    checks = {'scripts_parse': not syntax, 'game_compiles': server.get('compiled', False),
              'capture_ran': server.get('complete', False) and len(models) == 8,
              'no_server_runtime_errors': server.get('compiled', False) and not server.get('runtime_errors'),
              'no_page_errors': not page.get('error_count'),
              'view3d_draws': bool(page.get('webgl')) and all(v and v['on'] and v['things'] > 0 for v in page.get('scene', {}).values()),
              'webkit_runs_every_script': 'skipped' not in webkit and not webkit['errors']
                  and all(webkit['defined'].get(n) == 'function' for n in ('updateHUD', 'update3D', 'move3D'))
                  and all(webkit['defined'].get(n) == 'function' for n in ('rmSfx', 'rfStats') if n in html)}
    result = dict(passed=all(checks.values()), checks=checks, syntax_errors=syntax, server=server, page=page, webkit=webkit,
                  seconds=round(time.time() - started), html_bytes=len(html.encode()))
    (ROOT/f'tests/{args.label}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=1)[:4000])
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
