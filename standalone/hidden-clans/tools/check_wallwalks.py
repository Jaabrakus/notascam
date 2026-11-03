#!/usr/bin/env python3
"""Run wall-walks, wall stairs, climbing orders and ranks in a bounded arena."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT.parent/'replica/runtime/macos-x64'   # shared engine, used read-only
EXPECTED = [
    'WALL|built|walls=6|walks=6',
    'WALL|rooms|house_walks=0|fort_walks=24/24',
    'WALL|hut|hut_walks=0|open_walks=0|yard_walks=31/31|moat_walks=8/8|moat_gate=2',
    'WALL|gate|arch=2|faces=12|portcullis_arch=2',
    'WALL|freestanding|alone=3|settled_north=2|end=6|fort=1,10',
    'WALL|stairs|ok=1|up=StoneUp|down=StoneDown|leads=3|3d=stairsup,stairsdown',
    'WALL|ramp|ok=1|ramp=12|head=StoneUp|walkable=1|kind=ramp',
    'WALL|cut|ok=1|ramp=1234|head=StoneUp|open=1|outer_walk=1|landing=StoneDown',
    'WALL|order|climb_first=3',
    'WALL|climb|up=3|on_walk=3|most_per_tile=2',
    'WALL|full|blocked=1',
    'WALL|3d|walk_kind=1|click_up=1',
    'WALL|bridge|kind=bridge|under=water',
    'WALL|breach|walk=0|sky=1|fell=2/2',
    'WALL|complete',
]


def main():
    arena = ROOT/'tests/wallwalk-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'wallwalk.dme').write_text(dme + '\n#include "wallwalk_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) WallWalkRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/wallwalk_test.dm', arena/'wallwalk_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/wallwalk-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'wallwalk.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/wallwalk-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-wallwalk-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"wallwalk.json"}', '--cvar', 'opendream.topic_port=25641',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12191', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline and server.poll() is None:
            if 'WALL|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'WALL\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/'tests/wallwalk-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
