#!/usr/bin/env python3
"""Assert combat lifetime regressions and run a bounded full-map headless soak."""
import argparse
import hashlib
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
CHECK_GAME = Path(os.environ['RM_CHECK_GAME']) if os.environ.get('RM_CHECK_GAME') else ROOT/'game'   # RM_CHECK_GAME: a frozen copy to test (engine A/Bs on one game)
RUNTIME = check_engine.APP_RUNTIME   # the engine and game speed: --engine / --speed (tools/check_engine.py), set in main
ARGS = None
ERROR = re.compile(r'^.*(?:\[(?:ERRO|FATL)\]|runtime error|Exception occurred).*$', re.I | re.M)


def run_world(arena, fixture, label, timeout, prefix='COMBAT', port=12161):
    dotnet = RUNTIME / 'dotnet/dotnet'
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    with (ROOT / f'tests/{label}-compile.log').open('w') as out:
        subprocess.run([str(dotnet), str(check_engine.COMPILER), str(fixture)],
                       env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT / f'tests/{label}-server.log'
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='dm-combat-data-') as data, server_log.open('w') as out:
        server = subprocess.Popen([
            str(dotnet), str(RUNTIME / 'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}',
            '--cvar', f'opendream.topic_port={port + 13500}', '--cvar', f'net.port={port}',
            '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0',
            '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        timed_out = False
        t_world = None
        deadline = time.monotonic() + timeout
        while server.poll() is None and time.monotonic() < deadline:
            t_world = check_engine.mark(server_log, t_world)
            time.sleep(.2)
        t_end = time.monotonic()
        if server.poll() is None:
            timed_out = True
            server.terminate()
            try:
                server.wait(10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
    console = server_log.read_text(errors='replace')
    world_log = arena / 'ErrorLog.txt'
    world_text = world_log.read_text(errors='replace') if world_log.exists() else ''
    (ROOT / f'tests/{label}-world.log').write_text(world_text)
    text = console + '\n' + world_text
    observations = re.findall(re.escape(prefix) + r'\|[^\r\n]*', text)
    errors = ERROR.findall(text)
    completed = f'{prefix}|complete|failures=0' in observations
    clock, clock_line = check_engine.report(text, ARGS, t_world, t_end)
    result = dict(passed=completed and not timed_out and server.returncode == 0 and not errors and not any('|FAIL|' in s for s in observations),
                  server_exit_code=server.returncode, timed_out=timed_out,
                  seconds=round(time.monotonic() - started, 1), observations=observations, errors=errors,
                  runtime_sha256=hashlib.sha256((RUNTIME / 'server/Resources/Assemblies/OpenDreamRuntime.dll').read_bytes()).hexdigest(),
                  combat_source_sha256=hashlib.sha256((arena / 'Code/Creatures/Combats.dm').read_bytes()).hexdigest(), clock=clock)
    (ROOT / f'tests/{label}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)
    print(clock_line, flush=True)
    return result['passed']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ticks', type=int, default=1200, help='Full-world soak length; zero skips it.')
    parser.add_argument('--combat-source', type=Path, help='Alternative combat source for proving the regression.')
    check_engine.add_args(parser)   # its --label (default combat here) names the logs and results
    args = parser.parse_args()
    global RUNTIME, ARGS
    RUNTIME, ARGS = check_engine.runtime(args), args
    if args.ticks < 0:
        parser.error('ticks must be nonnegative')
    passed = True
    for soak in (False, True):
        if soak and not args.ticks:
            continue
        label = (args.label or 'combat') + ('-soak' if soak else '')
        with tempfile.TemporaryDirectory(prefix='dm-combat-world-') as temp:
            arena = Path(temp) / 'world'
            ignored = ['Cave Crawlers.json', '*.sav', 'ErrorLog.txt', 'units', 'saves']
            if not soak:
                ignored += ['*.dmm']
            shutil.copytree(CHECK_GAME, arena, ignore=shutil.ignore_patterns(*ignored))
            if args.combat_source:
                shutil.copy2(args.combat_source, arena / 'Code/Creatures/Combats.dm')
            dme = (arena / 'Cave Crawlers.dme').read_text(encoding='latin-1')
            world = arena / 'Code/World.dm'
            source = world.read_text(encoding='latin-1')
            if soak:
                speed = check_engine.speed(args)
                source = source.replace('\t\tCallSave()', '\t\tCallSave()\n' + (f'\t\tgame_state = {speed}\n' if speed != 1 else '') + '\t\tspawn() RmCheckClock()\n\t\tspawn() CombatSoak()')
                (arena / 'combat_test.dm').write_text(f'''var/parity_race
proc/CombatSoak()
\tvar/start = world.time
\twhile(world.time - start < {args.ticks})
\t\tvar/population = 0
\t\tfor(var/mob/Monsters/M in world) population++
\t\tworld.log << "COMBAT|sample|tick=[world.time-start]|population=[population]|season=[Season]|night=[night]"
\t\tsleep(min(100, {args.ticks} - (world.time - start)))
\tworld.log << "COMBAT|complete|failures=0"
\tshutdown()
proc/RmCheckClock()
\twhile(1)
\t\tworld.log << "CHECKCLOCK|[world.time]"
\t\tsleep(50)
''')
            else:
                dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
                start = source.index('\tNew()')
                end = source.index('\nvar/Season', start)
                source = source[:start] + check_engine.world_new('CombatRun', args) + source[end:]
                shutil.copy2(ROOT / 'tests/combat_test.dm', arena / 'combat_test.dm')
            world.write_text(source, encoding='latin-1')
            fixture = arena / 'combat.dme'
            fixture.write_text(dme + '\n#include "combat_test.dm"\n', encoding='latin-1')
            passed = run_world(arena, fixture, label, 180 + (args.ticks / 10 if soak else 0), port=check_engine.free_port_pair()) and passed   # a free port: copies never clash
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
