#!/usr/bin/env python3
"""The map-memory arena (planning/MAP_MEMORY.md): tools/check_arena.py's light world, but on a window of the real land
(tools/map_memory/cut_map.py, all four layers) instead of plain grass, so region tests see real mountains, water,
trees, caves and the map's own things. Prints the test's CK|name|ok|detail checks (each must be 1, ending CK|complete)
and keeps them in tests/<report>. Run it through tools/runlock.py --kind run:

    python3 tools/runlock.py --who map-memory --kind run -- python3 tools/map_memory/arena.py \\
        --test tests/map_memory_test.dm --entry MmRun --cut 369,620,256,256 --runtime-dll <scratch engine>
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_RUNTIME = ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
COMPILER = ROOT.parent/'replica/runtime/macos-x64/compiler/DMCompiler.dll'   # shared, used read-only


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', type=Path, default=ROOT/'game')
    ap.add_argument('--runtime-dll', type=Path, help="OpenDreamRuntime.dll to run it on (default: the app's)")
    ap.add_argument('--port', type=int, default=12396)
    ap.add_argument('--test', type=Path, required=True)
    ap.add_argument('--entry', required=True)
    ap.add_argument('--cut', default='369,620,256,256', help='X0,Y0,W,H of the real map (default: mountains, desert, grass, water by 496,747)')
    ap.add_argument('--report', help='results file in tests/ (default: the test name + -checks.json)')
    ap.add_argument('--env', action='append', default=[], help='NAME=VALUE for the server (repeatable)')
    ap.add_argument('--timeout', type=float, default=1200)
    ap.add_argument('--dumps', type=Path, help='folder to keep the test\'s mm-*.txt dumps in (they can be hundreds of MB; default: not kept)')
    ap.add_argument('--compile-only', action='store_true', help='compile the arena and stop (prints the compiler\'s errors)')
    a = ap.parse_args()
    if not a.report: a.report = a.test.stem + '-checks.json'
    tests = ROOT/'tests'
    x0, y0, w, h = (int(v) for v in a.cut.split(','))
    with tempfile.TemporaryDirectory(prefix='dm-mm-') as temp:
        arena = Path(temp)/'arena'
        shutil.copytree(a.game, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players', 'tick-profile.log', 'backup'))
        (arena/'units').mkdir()
        subprocess.run([sys.executable, str(ROOT/'tools/map_memory/cut_map.py'), str(x0), str(y0), str(w), str(h), str(arena/'Maps/cut.dmm')], check=True)
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        (arena/'ck.dme').write_text(dme + f'\n#include "obey_test.dm"\n#include "Maps\\cut.dmm"\n#include "{a.test.name}"\n', encoding='latin-1')
        world = arena/'Code/World.dm'
        text = world.read_text(encoding='latin-1')
        start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
        world.write_text(text[:start] + f'\tNew()\n\t\tspawn(0) {a.entry}()\n' + text[end:], encoding='latin-1')
        shutil.copy2(tests/'obey_test.dm', arena/'obey_test.dm')
        shutil.copy2(a.test, arena/a.test.name)
        runtime = APP_RUNTIME
        if a.runtime_dll:
            runtime = Path(temp)/'runtime'
            shutil.copytree(APP_RUNTIME, runtime, symlinks=True)
            shutil.copy2(a.runtime_dll, runtime/'server/Resources/Assemblies/OpenDreamRuntime.dll')
        dotnet = runtime/'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        env.pop('RM_MAX_SPEED', None)
        for kv in a.env:
            k, v = kv.split('=', 1); env[k] = v
        stem = Path(a.report).stem
        with (tests/f'{stem}-compile.log').open('w') as out:
            r = subprocess.run([str(dotnet), str(COMPILER), str(arena/'ck.dme')], env=env, stdout=out, stderr=subprocess.STDOUT)
        if r.returncode or a.compile_only:
            lines = (tests/f'{stem}-compile.log').read_text(errors='replace').splitlines()
            print(*[l for l in lines if 'error' in l.lower()][:30] or lines[-5:], sep='\n')
            raise SystemExit(r.returncode)
        log = tests/f'{stem}-server.log'
        t0 = time.monotonic()
        with tempfile.TemporaryDirectory(prefix='dm-mm-data-') as data, log.open('w') as out:
            server = subprocess.Popen([str(dotnet), str(runtime/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={arena/"ck.json"}', '--cvar', f'opendream.topic_port={a.port + 13500}',
                '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={a.port}', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
                env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
            deadline = time.monotonic() + a.timeout
            while time.monotonic() < deadline and server.poll() is None and 'CK|complete' not in log.read_text(errors='replace'):
                time.sleep(.5)
            if server.poll() is None:
                server.terminate()
                try: server.wait(10)
                except subprocess.TimeoutExpired: server.kill()
        if a.dumps:   # the test's dumps, for diffing
            a.dumps.mkdir(parents=True, exist_ok=True)
            for f in arena.glob('mm-*.txt'): shutil.copy2(f, a.dumps/f'{stem}-{f.name}')
        errorlog = arena/'ErrorLog.txt'
        text = log.read_text(errors='replace') + (errorlog.read_text(errors='replace') if errorlog.exists() else '')
    rows = re.findall(r'CK\|([^|\r\n]+)\|([01])\|([^\r\n]*)', text)
    notes = re.findall(r'CK\|(?:note|time)\|[^\r\n]*', text)
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*|runtime error[^\r\n]*', text)
    result = dict(passed=bool(rows) and all(r[1] == '1' for r in rows) and 'CK|complete' in text and not errors,
                  cut=a.cut, runtime_dll=str(a.runtime_dll) if a.runtime_dll else None, seconds=round(time.monotonic() - t0),
                  checks=[dict(name=r[0], ok=r[1] == '1', detail=r[2]) for r in rows], notes=notes, errors=errors[:10])
    (tests/a.report).write_text(json.dumps(result, indent=2) + '\n')
    for r in rows: print(('  ' if r[1] == '1' else '!!'), r[0], r[2])
    for n in notes: print('  ', n)
    if errors: print('errors:', *errors[:5], sep='\n  ')
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
