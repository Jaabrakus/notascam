#!/usr/bin/env python3
"""Run war between war in a bounded arena."""
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
    'WA|peace|1|order=0',
    'WA|declare|warning=1|notyet=1',
    'WA|war|1|hostile=1|work=1',
    'WA|grievance|1|now=1',
    'WA|siege|guarded=1|taken=1|colour=1|plunder=1|score=5',
    'WA|fallen|truce=1|norewar=1',
    'WA|kill|1',
    'WA|peace-offer|offered=1|truce=1',
    'WA|data|1',
    'WA|complete',
]


def main():
    arena = ROOT/'tests/war-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'war.dme').write_text(dme + '\n#include "war_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) WaRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/war_test.dm', arena/'war_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/war-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'war.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/war-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-war-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"war.json"}', '--cvar', 'opendream.topic_port=25783',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12283', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline and server.poll() is None:
            if 'WA|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'WA\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/'tests/war-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
