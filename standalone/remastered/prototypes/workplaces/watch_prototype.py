#!/usr/bin/env python3
"""Opens the workplaces PROTOTYPE in a real game window (a test arena, not the game): a throwaway copy of
game/ gets Workplaces.dm and watch_scene.dm, a local server runs it, and a game client connects. Close the
window to end it; the server stops with it. Nothing in game/, the app or the saves changes.

    nice -n 10 python3 tools/runlock.py --who workplaces --kind run -- python3 prototypes/workplaces/watch_prototype.py
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from check_mouse import RUNTIME, client_copy, write_hints  # noqa: E402


def main():
    with tempfile.TemporaryDirectory(prefix='dm-wp-watch-') as temp:
        base = Path(temp)
        world = base/'world'
        shutil.copytree(ROOT/'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world/'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world/'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        for f in ('Workplaces.dm', 'VillageStores.dm', 'watch_scene.dm'): shutil.copy2(HERE/f, world/f)
        # the Village stores bar goes into this copy's HUD only
        page = world/'Interface/remastered.html'
        html = page.read_text(encoding='utf-8')
        # before the page's last script: its send('ready') is a navigation, and WebKit stops reading the page there
        at = html.rfind('<script>', 0, html.rindex("send('ready','');"))
        page.write_text(html[:at] + '<script>' + (HERE/'village_stores.js').read_text(encoding='utf-8') + '</script>\n' + html[at:], encoding='utf-8')
        fixture = world/'workplaces_watch.dme'
        fixture.write_text(dme + '\n#include "Workplaces.dm"\n#include "VillageStores.dm"\n#include "watch_scene.dm"\n', encoding='latin-1')
        dotnet = RUNTIME/'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0', DOTNET_gcServer='0')
        clog = HERE/'watch-compile.log'
        with clog.open('w') as out:
            r = subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=out, stderr=subprocess.STDOUT)
        if r.returncode:
            print('compile failed:', *[l for l in clog.read_text(errors='replace').splitlines() if 'Error' in l][:8], sep='\n  ')
            raise SystemExit(1)
        hints = base/'layout.json'
        write_hints(world/'skin.dmf', hints)
        env.update(DM_SKIN_LAYOUT_HINTS=str(hints), ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(ROOT/'engine/webview-webkit'))
        slp, clp = HERE/'watch-server.log', HERE/'watch-client.log'
        server = client = None
        try:
            with slp.open('w') as sl, clp.open('w') as cl:
                server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', str(base/'data'),
                    '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'opendream.topic_port=25891',
                    '--cvar', 'net.port=12391', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
                    '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                end_at = time.monotonic() + 60
                while ' -> Ready' not in slp.read_text(errors='replace'):
                    if time.monotonic() > end_at or server.poll() is not None:
                        print('server did not start; see', slp)
                        raise SystemExit(1)
                    time.sleep(.3)
                cd = client_copy()
                client = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(RUNTIME/'server/Content.Client.zip'),
                    '--connect', '--connect-address', 'udp://127.0.0.1:12391', '--username', 'Workplaces', '--self-contained',
                    '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                print('window open; close it to end the prototype', flush=True)
                client.wait()
        finally:
            for p in (client, server):
                if p and p.poll() is None:
                    p.terminate()
                    try: p.wait(10)
                    except subprocess.TimeoutExpired: p.kill()
        err = (world/'ErrorLog.txt')
        if err.exists():
            bad = [l for l in err.read_text(errors='replace').splitlines() if 'runtime error' in l]
            if bad: print('runtime errors:', *bad[:5], sep='\n  ')
    print('prototype closed')


if __name__ == '__main__':
    main()
