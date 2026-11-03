#!/usr/bin/env python3
"""Orders always go through: units in awkward states (asleep, flying, blind, legless,
no tool, full pack, walled in, defending, patrolling, ...) are given ordinary orders
through the same proc a map click uses, and must carry them out. One boot of an arena
on the packaged Remastered runtime; every OB| line must report 1."""
import json
import os
import socket
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CHECK_GAME = Path(os.environ['RM_CHECK_GAME']) if os.environ.get('RM_CHECK_GAME') else ROOT/'game'   # RM_CHECK_GAME: a frozen copy to test (engine A/Bs on one game)
APP_RUNTIME = Path(os.environ['RM_CHECK_RUNTIME']) if os.environ.get('RM_CHECK_RUNTIME') else ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'   # RM_CHECK_RUNTIME: a test engine's runtime copy
COMPILER = ROOT.parent/'replica/runtime/macos-x64/compiler/DMCompiler.dll'   # shared, used read-only



def free_port(kind):
    """A port nothing holds now (was a fixed 12293/25793: two runs at once failed, formations 10-25)."""
    with socket.socket(socket.AF_INET, kind) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entry', default='ObRun', help='Test proc to run (debugging).')
    parser.add_argument('--extra', help='Extra .dm file to include (debugging).')
    parser.add_argument('--overlay', help='Folder of Code/Remastered .dm files to test instead (e.g. older versions).')
    parser.add_argument('--report', default='obey-checks.json', help='Results file name in tests/.')
    args = parser.parse_args()
    tests = ROOT/'tests'
    with tempfile.TemporaryDirectory(prefix='dm-ob-') as temp:
        arena = Path(temp)/'arena'
        shutil.copytree(CHECK_GAME, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players'))
        (arena/'units').mkdir()
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        if args.overlay:
            for f in Path(args.overlay).glob('*.dm'): shutil.copy2(f, arena/'Code/Remastered'/f.name)
        extra = ''
        if args.extra:
            shutil.copy2(args.extra, arena/'ob_extra.dm')
            extra = '#include "ob_extra.dm"\n'
        (arena/'ob.dme').write_text(dme + '\n#include "obey_test.dm"\n' + extra, encoding='latin-1')
        world = arena/'Code/World.dm'
        text = world.read_text(encoding='latin-1')
        start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
        world.write_text(text[:start] + f'\tNew()\n\t\tspawn(0) {args.entry}()\n' + text[end:], encoding='latin-1')
        shutil.copy2(tests/'obey_test.dm', arena/'obey_test.dm')
        dotnet = APP_RUNTIME/'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        stem = 'obey' if args.report == 'obey-checks.json' else Path(args.report).stem   # logs named after the report, so two runs never share them
        with (tests/f'{stem}-compile.log').open('w') as out:
            subprocess.run([str(dotnet), str(COMPILER), str(arena/'ob.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
        log = tests/f'{stem}-server.log'
        with tempfile.TemporaryDirectory(prefix='dm-ob-data-') as data, log.open('w') as out:
            server = subprocess.Popen([str(dotnet), str(APP_RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={arena/"ob.json"}', '--cvar', f'opendream.topic_port={free_port(socket.SOCK_STREAM)}',
                '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={free_port(socket.SOCK_DGRAM)}', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
                env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
            deadline = time.monotonic() + 420
            while time.monotonic() < deadline and server.poll() is None and 'OB|complete' not in log.read_text(errors='replace'):
                time.sleep(.5)
            if server.poll() is None:
                server.terminate()
                try: server.wait(10)
                except subprocess.TimeoutExpired: server.kill()
        errorlog = arena/'ErrorLog.txt'
        text = log.read_text(errors='replace') + (errorlog.read_text(errors='replace') if errorlog.exists() else '')
    rows = re.findall(r'OB\|([^|\r\n]+)\|([01])\|([^\r\n]*)', text)
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*|runtime error[^\r\n]*', text)
    result = dict(passed=bool(rows) and all(r[1] == '1' for r in rows) and 'OB|complete' in text and not errors,
                  checks=[dict(name=r[0], ok=r[1] == '1', detail=r[2]) for r in rows], errors=errors[:10])
    (tests/args.report).write_text(json.dumps(result, indent=2) + '\n')
    for r in rows: print(('  ' if r[1] == '1' else '!!'), r[0], r[2])
    if errors: print('errors:', *errors[:5], sep='\n  ')
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
