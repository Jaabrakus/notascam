#!/usr/bin/env python3
"""Runs the workplaces PROTOTYPE (Workplaces.dm, not part of the game) in a throwaway copy of game/:
the copy gets the arena helpers (tests/obey_test.dm), the prototype and its scene (workplaces_test.dm),
compiles and runs headless, and prints every WP| line. Nothing in game/ or the app changes.

    nice -n 10 python3 tools/runlock.py --who workplaces --kind run -- python3 prototypes/workplaces/run_prototype.py
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
APP_RUNTIME = next((ROOT/a/'Contents/Resources/game/runtime' for a in ('Banners of the Deep.app', 'Land of Lords.app') if (ROOT/a).exists()), ROOT/'Banners of the Deep.app/Contents/Resources/game/runtime')
COMPILER = ROOT.parent/'replica/runtime/macos-x64/compiler/DMCompiler.dll'


def main():
    with tempfile.TemporaryDirectory(prefix='dm-wp-') as temp:
        arena = Path(temp)/'arena'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players'))
        (arena/'units').mkdir()
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        for f in ('Workplaces.dm', 'VillageStores.dm', 'workplaces_test.dm'): shutil.copy2(HERE/f, arena/f)
        shutil.copy2(ROOT/'tests/obey_test.dm', arena/'obey_test.dm')
        (arena/'wp.dme').write_text(dme + '\n#include "obey_test.dm"\n#include "Workplaces.dm"\n#include "VillageStores.dm"\n#include "workplaces_test.dm"\n', encoding='latin-1')
        world = arena/'Code/World.dm'
        text = world.read_text(encoding='latin-1')
        start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
        world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) WpRun()\n' + text[end:], encoding='latin-1')
        dotnet = APP_RUNTIME/'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0', DOTNET_gcServer='0')
        clog = HERE/'compile.log'
        with clog.open('w') as out:
            r = subprocess.run([str(dotnet), str(COMPILER), str(arena/'wp.dme')], env=env, stdout=out, stderr=subprocess.STDOUT)
        if r.returncode:
            print('compile failed:', *[l for l in clog.read_text(errors='replace').splitlines() if 'Error' in l][:8], sep='\n  ')
            raise SystemExit(1)
        log = HERE/'server.log'
        with tempfile.TemporaryDirectory(prefix='dm-wp-data-') as data, log.open('w') as out:
            server = subprocess.Popen([str(dotnet), str(APP_RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={arena/"wp.json"}', '--cvar', 'opendream.topic_port=25833',
                '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12333', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
                env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline and server.poll() is None and 'WP|complete' not in log.read_text(errors='replace'):
                time.sleep(.5)
            if server.poll() is None:
                server.terminate()
                try: server.wait(10)
                except subprocess.TimeoutExpired: server.kill()
        text = log.read_text(errors='replace')
    rows = re.findall(r'WP\|([^|\r\n]+)\|([01])\|([^\r\n]*)', text)
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*|runtime error[^\r\n]*', text)
    for r in rows: print(('  ' if r[1] == '1' else '!!'), r[0], r[2])
    if errors: print('errors:', *errors[:5], sep='\n  ')
    ok = bool(rows) and all(r[1] == '1' for r in rows) and 'WP|complete' in text and not errors
    print('passed' if ok else 'FAILED')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
