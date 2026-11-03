#!/usr/bin/env python3
"""Rulership (Rulership.dm, planning/RULERSHIP.md; the user's decisions 2026-10-23): the seat by stage and its regalia,
titles from a list per race and stage, the five laws of succession, the heir's item stolen and the succession following
it (claims across players: pressed, refused into war, peace, yielded, a fallen realm, taken back, lapsed), old saves
through a savefile, the crown's health (+150 at a Kingdom), the gear menu and the HUD data. One boot of an arena
(tests/rulership_test.dm) on the shared engine, about a minute; every RS| line must report 1.

    python3 tools/runlock.py --who rulership --kind run -- python3 tools/check_rulership.py [--port 12377]
"""
import argparse
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=12377)
    args = ap.parse_args()
    tests = ROOT/'tests'
    with tempfile.TemporaryDirectory(prefix='dm-rs-') as temp:
        arena = Path(temp)/'arena'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players'))
        (arena/'units').mkdir()
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        (arena/'rs.dme').write_text(dme + '\n#include "rulership_test.dm"\n', encoding='latin-1')
        world = arena/'Code/World.dm'
        text = world.read_text(encoding='latin-1')
        start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
        world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) RsRun()\n' + text[end:], encoding='latin-1')
        shutil.copy2(tests/'rulership_test.dm', arena/'rulership_test.dm')
        dotnet = RUNTIME/'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests/'rulership-arena-compile.log').open('w') as out:
            subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'rs.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
        log = tests/'rulership-arena-server.log'
        with tempfile.TemporaryDirectory(prefix='dm-rs-data-') as data, log.open('w') as out:
            server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={arena/"rs.json"}', '--cvar', f'opendream.topic_port={args.port + 13500}',
                '--cvar', f'log.path={tests/"engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={args.port}',
                '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0',
                '--cvar', 'game.auto_pause_empty=false'],
                env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline and server.poll() is None and 'RS|complete' not in log.read_text(errors='replace'):
                time.sleep(.5)
            if server.poll() is None:
                server.terminate()
                try: server.wait(10)
                except subprocess.TimeoutExpired: server.kill()
        errorlog = arena/'ErrorLog.txt'
        text = log.read_text(errors='replace') + (errorlog.read_text(errors='replace') if errorlog.exists() else '')
    rows = re.findall(r'RS\|([^|\r\n]+)\|([01])\|([^\r\n]*)', text)
    rows = list(dict.fromkeys(rows))   # the engine log carries some world.log lines twice
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*|runtime error[^\r\n]*', text)
    result = dict(passed=bool(rows) and all(r[1] == '1' for r in rows) and 'RS|complete' in text and not errors,
                  checks=[dict(name=r[0], ok=r[1] == '1', detail=r[2]) for r in rows], errors=errors[:10])
    (tests/'rulership-arena-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for r in rows: print(('  ' if r[1] == '1' else '!!'), r[0], r[2])
    if errors: print('errors:', *errors[:5], sep='\n  ')
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
