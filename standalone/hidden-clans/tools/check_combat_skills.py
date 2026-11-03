#!/usr/bin/env python3
"""RuneScape combat skills: XP by style, Ranged/Throwing/Magic, injuries and dodging,
level bonuses, seeding from weapon skills and the HUD data. One boot of an arena on
the packaged Remastered runtime; every CS| line must report 1."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
APP_RUNTIME = ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
COMPILER = ROOT.parent/'replica/runtime/macos-x64/compiler/DMCompiler.dll'   # shared, used read-only



def main():
    tests = ROOT/'tests'
    with tempfile.TemporaryDirectory(prefix='dm-cs-') as temp:
        arena = Path(temp)/'arena'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players'))
        (arena/'units').mkdir()
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        (arena/'cs.dme').write_text(dme + '\n#include "combat_skills_test.dm"\n', encoding='latin-1')
        world = arena/'Code/World.dm'
        text = world.read_text(encoding='latin-1')
        start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
        world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) CsRun()\n' + text[end:], encoding='latin-1')
        shutil.copy2(tests/'combat_skills_test.dm', arena/'combat_skills_test.dm')
        dotnet = APP_RUNTIME/'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests/'combat-skills-compile.log').open('w') as out:
            subprocess.run([str(dotnet), str(COMPILER), str(arena/'cs.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
        log = tests/'combat-skills-server.log'
        with tempfile.TemporaryDirectory(prefix='dm-cs-data-') as data, log.open('w') as out:
            server = subprocess.Popen([str(dotnet), str(APP_RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={arena/"cs.json"}', '--cvar', 'opendream.topic_port=25791',
                '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12291', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
                env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline and server.poll() is None and 'CS|complete' not in log.read_text(errors='replace'):
                time.sleep(.5)
            if server.poll() is None:
                server.terminate()
                try: server.wait(10)
                except subprocess.TimeoutExpired: server.kill()
        errorlog = arena/'ErrorLog.txt'
        text = log.read_text(errors='replace') + (errorlog.read_text(errors='replace') if errorlog.exists() else '')
    rows = re.findall(r'CS\|([^|\r\n]+)\|([01])\|([^\r\n]*)', text)
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*|runtime error[^\r\n]*', text)
    result = dict(passed=bool(rows) and all(r[1] == '1' for r in rows) and 'CS|complete' in text and not errors,
                  checks=[dict(name=r[0], ok=r[1] == '1', detail=r[2]) for r in rows], errors=errors[:10])
    (tests/'combat-skills-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for r in rows: print(('  ' if r[1] == '1' else '!!'), r[0], r[2])
    if errors: print('errors:', *errors[:5], sep='\n  ')
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
