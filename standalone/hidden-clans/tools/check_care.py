#!/usr/bin/env python3
"""Run the Remastered self-care and homes logic in a bounded arena."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

import check_engine

ROOT = Path(__file__).resolve().parents[1]
CHECK_GAME = Path(os.environ['RM_CHECK_GAME']) if os.environ.get('RM_CHECK_GAME') else ROOT/'game'   # RM_CHECK_GAME: a frozen copy to test (engine A/Bs on one game)
# The engine (the app's by default, or the replica's) and the game speed: --engine / --speed (tools/check_engine.py).
EXPECTED = [
    'CARE|cold_start|care=warm|status=1',
    'CARE|cold_done|warmed=1|near_fire=1|job=woodcutter|care=none',
    'CARE|bed_claim|home=8,14|t1=sleep|t2_note=Slept rough: no bed|t2_sleeping=1',
    'CARE|bed_sleep|slept=1|sleeping=1|on_bed=1|home_text=Bed at 8, 14|t2_home=No bed',
    'CARE|eat_start|care=eat',
    'CARE|eat_done|ate=1|fuller=1',
    'CARE|no_fire|care=none|note=Cold: no campfire within 25 tiles',
    'CARE|interrupt|was=warm|now=none|held=1',
    'CARE|saved_home|8,14,1',
    'CARE|complete',
]


def main():
    args = check_engine.parse(__doc__)
    RUNTIME = check_engine.runtime(args)
    arena = ROOT/'tests/care-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(CHECK_GAME, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'care.dme').write_text(dme + '\n#include "care_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + check_engine.world_new('CareRun2', args) + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/care_test.dm', arena/'care_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/care-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(check_engine.COMPILER), str(arena/'care.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/care-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-care-') as data, server_log.open('w') as out:
        t_world = None
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"care.json"}', '--cvar', 'opendream.topic_port=25599',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12149', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline and server.poll() is None:
            if 'CARE|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            t_world = check_engine.mark(server_log, t_world)
            time.sleep(.2)
        t_end = time.monotonic()
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'CARE\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    clock, clock_line = check_engine.report(text, args, t_world, t_end)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors, clock=clock)
    (ROOT/'tests/care-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print(clock_line)
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
