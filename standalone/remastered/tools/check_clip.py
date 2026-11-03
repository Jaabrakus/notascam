"""Friendly and allied units clip through each other (Clip.dm): runs tests/clip_check.dm in the obey arena (it uses its
helpers) and prints its CK| checks; every one must report 1. --game and --runtime-dll test a candidate (a game folder
with the change, an engine with native version 2) before it goes into game/ and engine/server/. Run it through
tools/runlock.py --kind run."""
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
APP_RUNTIME = ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
COMPILER = ROOT.parent/'replica/runtime/macos-x64/compiler/DMCompiler.dll'   # shared, used read-only


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--game', type=Path, default=ROOT/'game', help='game folder to test (default game/)')
    ap.add_argument('--runtime-dll', type=Path, help='OpenDreamRuntime.dll to run it on (default: the app\'s)')
    ap.add_argument('--port', type=int, default=12296)
    ap.add_argument('--report', default='clip-checks.json', help='results file name in tests/')
    args = ap.parse_args()
    tests = ROOT/'tests'
    with tempfile.TemporaryDirectory(prefix='dm-clip-') as temp:
        arena = Path(temp)/'arena'
        shutil.copytree(args.game, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players', 'tick-profile.log'))
        (arena/'units').mkdir()
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        (arena/'ck.dme').write_text(dme + '\n#include "obey_test.dm"\n#include "clip_check.dm"\n', encoding='latin-1')
        world = arena/'Code/World.dm'
        text = world.read_text(encoding='latin-1')
        start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
        world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) CkRun()\n' + text[end:], encoding='latin-1')
        shutil.copy2(tests/'obey_test.dm', arena/'obey_test.dm')
        shutil.copy2(tests/'clip_check.dm', arena/'clip_check.dm')
        runtime = APP_RUNTIME
        if args.runtime_dll:
            runtime = Path(temp)/'runtime'
            shutil.copytree(APP_RUNTIME, runtime, symlinks=True)
            shutil.copy2(args.runtime_dll, runtime/'server/Resources/Assemblies/OpenDreamRuntime.dll')
        dotnet = runtime/'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        stem = Path(args.report).stem   # logs named after the report, so two runs never share them
        with (tests/f'{stem}-compile.log').open('w') as out:
            subprocess.run([str(dotnet), str(COMPILER), str(arena/'ck.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
        log = tests/f'{stem}-server.log'
        with tempfile.TemporaryDirectory(prefix='dm-clip-data-') as data, log.open('w') as out:
            server = subprocess.Popen([str(dotnet), str(runtime/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={arena/"ck.json"}', '--cvar', f'opendream.topic_port={args.port + 13500}',
                '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={args.port}', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
                env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
            deadline = time.monotonic() + 900
            while time.monotonic() < deadline and server.poll() is None and 'CK|complete' not in log.read_text(errors='replace'):
                time.sleep(.5)
            if server.poll() is None:
                server.terminate()
                try: server.wait(10)
                except subprocess.TimeoutExpired: server.kill()
        errorlog = arena/'ErrorLog.txt'
        text = log.read_text(errors='replace') + (errorlog.read_text(errors='replace') if errorlog.exists() else '')
    rows = re.findall(r'CK\|([^|\r\n]+)\|([01])\|([^\r\n]*)', text)
    notes = re.findall(r'CK\|(?:note|time)\|[^\r\n]*', text)
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*|runtime error[^\r\n]*', text)
    result = dict(passed=bool(rows) and all(r[1] == '1' for r in rows) and 'CK|complete' in text and not errors,
                  game=str(args.game), runtime_dll=str(args.runtime_dll) if args.runtime_dll else None,
                  checks=[dict(name=r[0], ok=r[1] == '1', detail=r[2]) for r in rows], notes=notes, errors=errors[:10])
    (tests/args.report).write_text(json.dumps(result, indent=2) + '\n')
    for r in rows: print(('  ' if r[1] == '1' else '!!'), r[0], r[2])
    for n in notes: print('  ', n)
    if errors: print('errors:', *errors[:5], sep='\n  ')
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
