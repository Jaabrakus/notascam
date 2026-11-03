#!/usr/bin/env python3
"""Weapon skills never above Attack (CombatSkills.dm, the user's rule 2026-10-23): seeding, training at the cap,
Attack levelling, one-off jumps, an old save through a savefile, the crown (health now, no weapon skills), the stoneskin draught (it wears off
after 3 minutes, so a run takes about 3.5), creatures nobody owns and the HUD data. One boot of an arena
(tests/weapon_cap_test.dm) on the shared engine; every WC| line must report 1.

    python3 tools/check_weapon_cap.py [--port 12297]
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
    ap.add_argument('--port', type=int, default=12297)
    args = ap.parse_args()
    tests = ROOT/'tests'
    with tempfile.TemporaryDirectory(prefix='dm-wc-') as temp:
        arena = Path(temp)/'arena'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players'))
        (arena/'units').mkdir()
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        (arena/'wc.dme').write_text(dme + '\n#include "weapon_cap_test.dm"\n', encoding='latin-1')
        world = arena/'Code/World.dm'
        text = world.read_text(encoding='latin-1')
        start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
        world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) WcRun()\n' + text[end:], encoding='latin-1')
        shutil.copy2(tests/'weapon_cap_test.dm', arena/'weapon_cap_test.dm')
        dotnet = RUNTIME/'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests/'weapon-cap-compile.log').open('w') as out:
            subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'wc.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
        log = tests/'weapon-cap-server.log'
        with tempfile.TemporaryDirectory(prefix='dm-wc-data-') as data, log.open('w') as out:
            server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={arena/"wc.json"}', '--cvar', f'opendream.topic_port={args.port + 13500}',
                '--cvar', f'log.path={tests/"engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={args.port}',
                '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0',
                '--cvar', 'game.auto_pause_empty=false'],
                env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
            deadline = time.monotonic() + 420
            while time.monotonic() < deadline and server.poll() is None and 'WC|complete' not in log.read_text(errors='replace'):
                time.sleep(.5)
            if server.poll() is None:
                server.terminate()
                try: server.wait(10)
                except subprocess.TimeoutExpired: server.kill()
        errorlog = arena/'ErrorLog.txt'
        text = log.read_text(errors='replace') + (errorlog.read_text(errors='replace') if errorlog.exists() else '')
    rows = re.findall(r'WC\|([^|\r\n]+)\|([01])\|([^\r\n]*)', text)
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*|runtime error[^\r\n]*', text)
    result = dict(passed=bool(rows) and all(r[1] == '1' for r in rows) and 'WC|complete' in text and not errors,
                  checks=[dict(name=r[0], ok=r[1] == '1', detail=r[2]) for r in rows], errors=errors[:10])
    (tests/'weapon-cap-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for r in rows: print(('  ' if r[1] == '1' else '!!'), r[0], r[2])
    if errors: print('errors:', *errors[:5], sep='\n  ')
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
