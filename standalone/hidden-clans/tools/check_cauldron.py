#!/usr/bin/env python3
"""Run the Remastered Cauldron in a bounded arena."""
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
    'CA|build|1|stone_used=1',
    'CA|batch|juice=1|water=1|cold=1',
    'CA|fire|lit=1|hot=1|healing=1|juice_left=1',
    'CA|advanced|elixir=1',
    'CA|bottle_cant|1',
    'CA|bottle|n=1|full=1|taken=1',
    'CA|data|1|3d=1',
    'CA|cool|out=1|cooling=1',
    'CA|complete',
]


def main():
    arena = ROOT/'tests/cauldron-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'cauldron.dme').write_text(dme + '\n#include "cauldron_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) CaRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/cauldron_test.dm', arena/'cauldron_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/cauldron-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'cauldron.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/cauldron-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-cauldron-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"cauldron.json"}', '--cvar', 'opendream.topic_port=25669',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12219', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline and server.poll() is None:
            if 'CA|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'CA\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/'tests/cauldron-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
