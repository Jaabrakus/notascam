#!/usr/bin/env python3
"""Open the armour showcase in the real client for recording: a private, mapless test world
(tests/armour_showcase.dm) with columns of defenders in different armour (bare, helmet only, leggings only, a
Quality suit, a Legendary suit, a bare gargoyle) and rows of your attackers striking them (recruit sword, veteran
sword, veteran mace, veteran archer). Nothing is clicked or typed for you: the window stays open until you close
it. Built from game/ as it is now, on the engine and HUD the app uses. Your saves are never touched.

    python3 tools/runlock.py --who showcase -- caffeinate -d -i python3 tools/showcase/armour_showcase.py
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from check_mouse import RUNTIME, client_copy, write_hints  # noqa: E402

PORT, TOPIC = 12431, 25931


def main():
    with tempfile.TemporaryDirectory(prefix='dm-armour-showcase-') as temp:
        base = Path(temp)
        world = base / 'world'
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        source = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
        shutil.copy2(ROOT / 'tests/armour_showcase.dm', world / 'armour_showcase.dm')
        fixture = world / 'armour_showcase.dme'
        fixture.write_text(dme + '\n#include "armour_showcase.dm"\n', encoding='latin-1')
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        print('showcase: compiling the test world...', flush=True)
        comp = subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(fixture)], env=env, capture_output=True, text=True, timeout=240)
        if comp.returncode:
            print('\n'.join(l for l in comp.stdout.splitlines() if 'Error' in l)[:3000])
            return 1
        hints = base / 'layout.json'
        write_hints(world / 'skin.dmf', hints)
        env.update(DM_SKIN_LAYOUT_HINTS=str(hints), ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(ROOT / 'engine/webview-webkit'))
        logs = ROOT / 'tests'
        with (logs / 'armour-showcase-server.log').open('w') as sl, (logs / 'armour-showcase-client.log').open('w') as cl:
            server = subprocess.Popen([str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'),
                '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', f'opendream.topic_port={TOPIC}',
                '--cvar', f'net.port={PORT}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
            server_log = logs / 'armour-showcase-server.log'
            deadline = time.monotonic() + 60
            while ' -> Ready' not in server_log.read_text(errors='replace'):
                if server.poll() is not None or time.monotonic() > deadline:
                    print('showcase: the server did not start; see tests/armour-showcase-server.log')
                    server.kill()
                    return 1
                time.sleep(.3)
            cd = client_copy()
            print('showcase: opening the client window. Close it when you are done recording.', flush=True)
            client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(RUNTIME / 'server/Content.Client.zip'),
                '--connect', '--connect-address', f'udp://127.0.0.1:{PORT}', '--username', 'Showcase', '--self-contained',
                '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
            try:
                client.wait()
            finally:
                for p in (client, server):
                    if p.poll() is None:
                        p.terminate()
                        try:
                            p.wait(10)
                        except subprocess.TimeoutExpired:
                            p.kill()
        errors = (world / 'ErrorLog.txt').read_text(errors='replace') if (world / 'ErrorLog.txt').exists() else ''
        bad = [l for l in errors.splitlines() if re.search(r'runtime error|\[ERRO\]|Exception', l)]
        print(f'showcase: closed. {len(bad)} runtime error lines in the world log' + (': ' + bad[0][:200] if bad else '.'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
