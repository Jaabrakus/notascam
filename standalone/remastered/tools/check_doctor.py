#!/usr/bin/env python3
"""Herbs, the Doctor's stall and the Doctor (Doctor.dm), and the ailments (Ailments.dm), in a bounded
arena: wild herbs, remedies, self-care, the Doctor treating the sick and cleansing poisoned food, the
Board order chain for missing herbs, wine and being drunk, rotten food, the fever, the HUD and away."""
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
    'DR|build|1|catalog=1',
    'DR|wild|1',
    'DR|make|picked=1|made=1',
    'DR|selfcare|1|note=1',
    'DR|doctor_treats|1|log=1',
    'DR|asks_board|1|priority=1|status=1',
    'DR|chain|order_done=1|cured=1|immune=1',
    'DR|cleanse|1|log=1',
    'DR|drunk|wine=1|warn=1|passout=1|sober=1',
    'DR|rot|rotten=1|refused=1|sick=1|vomit=1|over=1|boiled=1|gone=1|alert=Sickness',
    'DR|fever|cough=1|spread=1|immune=1|died=1|miasma=1|germs=1|count=1',
    'DR|hud|warn=1|conds=1|box=1|kinds=1|count=1|3d=1',
    'DR|use|bag=1|make=1|take=1',
    'DR|away|well=1|tonic=1|rot=1',
    'DR|salt|bag=1|aging=1|store=1|carried=1|cook=1|mined=1',
    'DR|save|1',
    'DR|complete',
]


def main():
    args = check_engine.parse(__doc__)
    RUNTIME = check_engine.runtime(args)
    arena = ROOT/'tests/doctor-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(CHECK_GAME, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'doctor.dme').write_text(dme + '\n#include "doctor_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + check_engine.world_new('DrRun', args) + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/doctor_test.dm', arena/'doctor_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/doctor-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(check_engine.COMPILER), str(arena/'doctor.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/doctor-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-doctor-') as data, server_log.open('w') as out:
        t_world = None
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"doctor.json"}', '--cvar', 'opendream.topic_port=25629',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12179', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 480
        while time.monotonic() < deadline and server.poll() is None:
            if 'DR|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            t_world = check_engine.mark(server_log, t_world)
            time.sleep(.2)
        t_end = time.monotonic()
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'DR\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    clock, clock_line = check_engine.report(text, args, t_world, t_end)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors, clock=clock)
    (ROOT/'tests/doctor-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print(clock_line)
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
