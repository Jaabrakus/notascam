#!/usr/bin/env python3
"""Run gates (Gates.dm): a portcullis in a wall gap and a drawbridge over a moat, worked from a lever by rune lines with mana or power, never closing on someone, saved."""
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
    'GATE|catalog|portcullis=1|drawbridge=1|need=4',
    'GATE|portcullis_built|ok=1|open=1|dense=0|gap=1|field=a portcullis goes in a gap of up to 3 tiles between two walls (or rock)',
    'GATE|lever_drops|open=0|dense=1|opaque=0|walkable=0|mana=17',
    'GATE|lever_raises|open=1|walkable=1|mana=14',
    'GATE|not_on_someone|open=1',
    'GATE|no_mana|open=1',
    'GATE|by_power|open=0|mana=0',
    'GATE|3d|id=portcullis|open=0|dir=1',
    'GATE|drawbridge_built|ok=1|down=1|bridge=1|tile_dense=0|state=WoodBridge|dry=a drawbridge goes on a water or lava tile (a moat)',
    'GATE|bridge_up|down=0|bridge=0|tile_dense=1|state=water|content=Water|walkable=0|mana=17',
    'GATE|bridge_down|down=1|bridge=1|walkable=1',
    'GATE|bridge_not_on_someone|down=1|bridge=1',
    'GATE|hinge|dir=4',
    'GATE|wide_build|portcullis=3|gap=4|wait_far=Built out from the bank: waits for the drawbridge beside it|drawbridge=9|dirs=1|lake=a drawbridge spans a moat up to 5 tiles wide: no bank near enough',
    'GATE|wide_groups|portcullis=3|drawbridge=9',
    'GATE|wide_portcullis_pull|down=3/3|mana=17',
    'GATE|wide_someone_on_it|up=0/9|mana=20',
    'GATE|wide_bridge_pull|up=9/9|water=9|mana=17',
    'GATE|save|portcullis=1|drawbridge=1|moat_dirty=1',
    'GATE|complete',
]


def main():
    arena = ROOT/'tests/gates-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'gates.dme').write_text(dme + '\n#include "gates_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) GatesRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/gates_test.dm', arena/'gates_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/gates-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'gates.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/gates-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-gates-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"gates.json"}', '--cvar', 'opendream.topic_port=25859',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12359', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 2400
        while time.monotonic() < deadline and server.poll() is None:
            if 'GATE|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'GATE\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/'tests/gates-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
