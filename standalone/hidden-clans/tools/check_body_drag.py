#!/usr/bin/env python3
"""Dragging bodies (BodyDrag.dm; capture-rope, 2026-10-25) in a bounded arena: the Drag / Carry card act, Drag body
(walks over, takes hold, the body stays on the ground, nobody else can pick it up, Let go offered), it follows a tile
behind (never on the dragger's tile or another body), slower going (less when strong), Let go, the gravedigger drags
the dead to the graveyard and buries them, let go when killed / down / on another level, the Operating table and the
workshops' corpse menus, a save, and rm_body_drag = 0 (carried as before).

    RM_CHECK_GAME=<a game copy with reports/capture-rope/staged/body-drag/patch_body_drag.py applied> python3 tools/check_body_drag.py

Writes tests/<label>-checks.json (label body-drag by default)."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

import check_engine

ROOT = Path(__file__).resolve().parents[1]
CHECK_GAME = Path(os.environ['RM_CHECK_GAME']) if os.environ.get('RM_CHECK_GAME') else ROOT/'game'
EXPECTED = [
    'BD|menu|drag=1|off_carry=1',
    'BD|drag|1|blocked=1|letgo_act=1',
    'BD|follow|1',
    'BD|slow|1',
    'BD|letgo|1',
    'BD|bury|1|dragged=1|plot=1',
    'BD|release|killed=1|down=1|level=1',
    'BD|use|table=1|taken=1|back=1',
    'BD|off|1',
    'BD|complete',
]


def main():
    args = check_engine.parse(__doc__)
    RUNTIME = check_engine.runtime(args)
    label = args.label or 'body-drag'
    arena = ROOT/f'tests/{label}-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(CHECK_GAME, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'players', 'units', 'backup'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'bodydrag.dme').write_text(dme + '\n#include "body_drag_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + check_engine.world_new('BdRun', args) + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/body_drag_test.dm', arena/'body_drag_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/f'tests/{label}-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(check_engine.COMPILER), str(arena/'bodydrag.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/f'tests/{label}-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-bodydrag-') as data, server_log.open('w') as out:
        t_world = None
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"bodydrag.json"}', '--cvar', f'opendream.topic_port={check_engine.free_port("tcp")}',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={check_engine.free_port("udp")}', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline and server.poll() is None:
            if 'BD|complete' in server_log.read_text(errors='replace'): break
            t_world = check_engine.mark(server_log, t_world)
            time.sleep(.5)
        t_end = time.monotonic()
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'BD\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    clock, clock_line = check_engine.report(text, args, t_world, t_end)
    ok = len(actual) == len(EXPECTED) and all(a == e or a.startswith(e + '|') for a, e in zip(actual, EXPECTED))
    result = dict(passed=ok and not errors, expected=EXPECTED, actual=actual, errors=errors, clock=clock)
    (ROOT/f'tests/{label}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        good = e == a or (e and a.startswith(e + '|'))
        print(('  ' if good else '!!'), a, '' if good else f'   (expected {e})')
    if errors: print('\n'.join(errors[:8]))
    print(clock_line)
    print('passed' if result['passed'] else 'FAILED')
    shutil.rmtree(arena, ignore_errors=True)   # keep the disk clean (memory: disk-fills-from-test-copies)
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
