#!/usr/bin/env python3
"""A showcase window for the user to watch and play (not a check): tests/showcase_probe.dm in a real native client.

A private, mapless world built from game/ on the app's own engine (Banners of the Deep.app's runtime: server, client,
webview): a stone golem by a mountain with the gap it rose out of, a second rising 45 s in, elves by the camera, and
elves with each weapon fighting orcs (their weapon moves, the dolls on). Your saves are never touched: the world is a
copy in a scratch folder and the client runs self-contained from its own copy. The window is brought to the front once;
after that it is yours. Closing it ends the showcase (server stopped, scratch folder removed).
    python3 tools/showcase_native.py [SCRATCH]
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'Banners of the Deep.app/Contents/Resources/game/runtime'
COMPILER = ROOT.parent / 'replica/runtime/macos-x64/compiler/DMCompiler.dll'
sys.path.insert(0, str(ROOT.parent / 'replica/tools'))
from skin_layout import write_hints  # noqa: E402


def main():
    base = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/botd-showcase')
    shutil.rmtree(base, ignore_errors=True)
    world = base / 'world'
    shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup', 'runtime'))
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
    source = (world / 'Code/World.dm').read_text(encoding='latin-1')
    start, end = source.index('\tNew()'), source.index('\nvar/Season')
    (world / 'Code/World.dm').write_text(source[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + source[end:], encoding='latin-1')
    shutil.copy2(ROOT / 'tests/showcase_probe.dm', world / 'showcase_probe.dm')
    fixture = world / 'showcase.dme'
    fixture.write_text(dme + '\n#include "showcase_probe.dm"\n', encoding='latin-1')
    dotnet = APP / 'dotnet/dotnet'
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    with (base / 'compile.log').open('w') as log_file:
        subprocess.run([str(dotnet), str(COMPILER), str(fixture)], env=env, stdout=log_file, stderr=subprocess.STDOUT, check=True, timeout=240)
    hints = base / 'layout.json'
    write_hints(world / 'skin.dmf', hints)
    env.update(DM_SKIN_LAYOUT_HINTS=str(hints), ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(APP / 'webview-webkit'))
    client_dir = base / 'client'
    subprocess.run(['cp', '-cR', str(APP / 'client'), str(client_dir)], check=True)   # its own copy: its user data stays in here
    cd = client_dir / 'Space Station 14.app/Contents/Resources'
    slp, clp = base / 'server.log', base / 'client.log'
    server = client = None
    try:
        with slp.open('w') as sl, clp.open('w') as cl:
            server = subprocess.Popen([str(dotnet), str(APP / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}',
                                       '--cvar', 'opendream.topic_port=25949', '--cvar', 'net.port=12451', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
                                       '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
            for _ in range(60):
                if ' -> Ready' in slp.read_text(errors='replace'):
                    break
                time.sleep(1)
            client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(APP / 'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12451',
                                       '--username', 'Showcase', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
            print('SHOWCASE client', client.pid, flush=True)
            time.sleep(25)   # its window up and the page loaded: then to the front, once (after that it is the user's)
            subprocess.run(['osascript', '-e', f'tell application "System Events" to set frontmost of (first process whose unix id is {client.pid}) to true'], capture_output=True)
            print('SHOWCASE up', flush=True)
            client.wait()
    finally:
        for p in (client, server):
            if p and p.poll() is None:
                p.terminate()
                try:
                    p.wait(10)
                except subprocess.TimeoutExpired:
                    p.kill()
        shutil.rmtree(world, ignore_errors=True)   # the logs stay
        shutil.rmtree(client_dir, ignore_errors=True)
        print('SHOWCASE closed', flush=True)


if __name__ == '__main__':
    main()
