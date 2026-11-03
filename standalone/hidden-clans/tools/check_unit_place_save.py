#!/usr/bin/env python3
"""Units saved inside an object keep their tile, and the soak trailer does not replay a stale scene."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT.parent/'replica/runtime/macos-x64'   # shared engine, used read-only
EXPECTED = [
    'UP|open|10,10,1',
    'UP|caged|7,8,1',
    'TR|stale|kingdom',   # the trailer loop starts at 5 s, after the save at 4 s
    'UP|complete',
]


def main():
    arena = ROOT/'tests/unit-place-save-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units'))
    (arena/'units').mkdir()
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'unitplace.dme').write_text(dme + '\n#include "ZZTrailer.dm"\n#include "unit_place_save_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) UpRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/unit_place_save_test.dm', arena/'unit_place_save_test.dm')
    shutil.copy2(ROOT/'tests/soak-arena/ZZTrailer.dm', arena/'ZZTrailer.dm')
    (arena/'trailer-scene.txt').write_text('kingdom\n')   # left over from before a restart
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/unit-place-save-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'unitplace.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/unit-place-save-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-unitplace-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"unitplace.json"}', '--cvar', 'opendream.topic_port=25977',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12477', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline and server.poll() is None:
            t = server_log.read_text(errors='replace')
            if 'UP|complete' in t or '[ERRO]' in t: break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    if errorlog.exists(): text += errorlog.read_text(errors='replace')
    actual = list(dict.fromkeys(re.findall(r'(?:UP|TR)\|[^\r\n]*', text)))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/'tests/unit-place-save-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
