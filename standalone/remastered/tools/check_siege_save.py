#!/usr/bin/env python3
"""Siege engines survive a world save and a restart: two boots of one arena."""
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
    'SV|saved|1',
    'SV|complete',
    'SV|restored|ram=1|catapult=1|count=2',
    'SV|banner|1',
    'SV|owner|1',
    'SV|complete',
]


def main():
    arena = ROOT/'tests/siege-save-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'siegesave.dme').write_text(dme + '\n#include "siege_save_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) SvRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/siege_save_test.dm', arena/'siege_save_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/siege-save-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'siegesave.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/siege-save-server.log'
    server_log.write_text('')
    for boot in (1, 2):    # boot 1 saves the world, boot 2 loads it
        with tempfile.TemporaryDirectory(prefix='dm-siegesave-') as data, server_log.open('a') as out:
            server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={arena/"siegesave.json"}', '--cvar', 'opendream.topic_port=25786',
                '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12286', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
                env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline and server.poll() is None:
                if server_log.read_text(errors='replace').count('SV|complete') >= boot or '[ERRO]' in server_log.read_text(errors='replace'): break
                time.sleep(.2)
            if server.poll() is None:
                server.terminate()
                try: server.wait(10)
                except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'SV\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/'tests/siege-save-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
