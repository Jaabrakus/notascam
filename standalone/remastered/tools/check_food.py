#!/usr/bin/env python3
"""Run the Remastered blueprints logic in a bounded arena."""
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
    'FOOD|stockpile_keeps|kept=1|elsewhere_cleaned=1',
    'FOOD|hunter|meat_stored=1|status=1',
    'FOOD|cook|cooked_stored=1',
    'FOOD|farmer|tilled=1|planted=1',
    'FOOD|harvest|stored=1',
    'FOOD|needs_blade|1',
    'FOOD|complete',
]


def main():
    args = check_engine.parse(__doc__)
    RUNTIME = check_engine.runtime(args)
    label = args.label or 'food'   # --label: its own arena, logs and results, so two runs at once never share them
    arena = ROOT/f'tests/{label}-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(CHECK_GAME, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'food.dme').write_text(dme + '\n#include "food_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + check_engine.world_new('FoodRun', args) + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/food_test.dm', arena/'food_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/f'tests/{label}-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(check_engine.COMPILER), str(arena/'food.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/f'tests/{label}-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-food-') as data, server_log.open('w') as out:
        t_world = None
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"food.json"}', '--cvar', f'opendream.topic_port={check_engine.free_port("tcp")}',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={check_engine.free_port("udp")}', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline and server.poll() is None:
            if 'FOOD|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            t_world = check_engine.mark(server_log, t_world)
            time.sleep(.2)
        t_end = time.monotonic()
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'FOOD\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    clock, clock_line = check_engine.report(text, args, t_world, t_end)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors, clock=clock)
    (ROOT/f'tests/{label}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print(clock_line)
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
