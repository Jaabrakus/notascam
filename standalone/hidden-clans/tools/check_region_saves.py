#!/usr/bin/env python3
"""Regions on disk R3's round trip (game/Code/Remastered/WorldRegions.dm, tests/region_saves_check.dm): one arena world
started five times on the same folder, so each start loads what the one before saved:
  save -> load (from the region files) -> single (RM_REGION_FILES=0) -> stale (the stamp file changed) -> migrate (the
  region files moved away: an old save) -> load again.
Every stage's checks must pass and every RG|fp fingerprint must equal the first save's. Prints CK lines; writes
tests/region_saves_check-checks.json.

    python3 tools/runlock.py --kind run --who quest-maker -- python3 tools/check_region_saves.py [--game DIR] [--port N]"""
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
COMPILER = ROOT.parent/'replica/runtime/macos-x64/compiler/DMCompiler.dll'
TEST = ROOT/'tests/region_saves_check.dm'

ap = argparse.ArgumentParser()
ap.add_argument('--game', type=Path, default=ROOT/'game')
ap.add_argument('--port', type=int, default=12481)
ap.add_argument('--timeout', type=float, default=600)
ap.add_argument('--real', action='store_true', help='the real map (game/\'s .dmm files, 256-tile regions), not the arena')
args = ap.parse_args()

dotnet = APP_RUNTIME/'dotnet/dotnet'
env0 = dict(os.environ, DOTNET_ReadyToRun='0', RG_DUMP='1')
if args.real: env0['RG_REAL'] = '1'
env0.pop('RM_MAX_SPEED', None)
rows, fps, errors = [], [], []
with tempfile.TemporaryDirectory(prefix='dm-regions-') as temp:
    arena = Path(temp)/'arena'
    shutil.copytree(args.game, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players', 'tick-profile.log'))
    (arena/'units').mkdir()
    if args.real:   # the real map and world start; the test's world/New spawns RgRun (RG_REAL)
        for m in args.game.rglob('*.dmm'):
            (arena/m.relative_to(args.game)).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(m, arena/m.relative_to(args.game))
        dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
        (arena/'ck.dme').write_text(dme + f'\n#include "obey_test.dm"\n#include "{TEST.name}"\n', encoding='latin-1')
        ob = (ROOT/'tests/obey_test.dm').read_text(encoding='latin-1')
        block = 'world\n\tmaxx = 120\n\tmaxy = 100\n\tmaxz = 2\n\tturf = /turf/grounds/grass\n\tfps = 10\n'
        if block not in ob: raise SystemExit('obey_test.dm\'s world block changed; review --real')
        (arena/'obey_test.dm').write_text(ob.replace(block, ''), encoding='latin-1')   # its helpers only, on the real map
    else:
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        (arena/'ck.dme').write_text(dme + f'\n#include "obey_test.dm"\n#include "{TEST.name}"\n', encoding='latin-1')
        world = arena/'Code/World.dm'
        text = world.read_text(encoding='latin-1')
        start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
        world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) RgRun()\n' + text[end:], encoding='latin-1')
    if not args.real: shutil.copy2(ROOT/'tests/obey_test.dm', arena/'obey_test.dm')
    shutil.copy2(TEST, arena/TEST.name)
    log_c = ROOT/'tests/region_saves_check-compile.log'
    with log_c.open('w') as out:
        subprocess.run([str(dotnet), str(COMPILER), str(arena/'ck.dme')], env=env0, stdout=out, stderr=subprocess.STDOUT, check=True)

    runs = []

    def stage(name, extra=None):
        env = dict(env0, RG_STAGE=name, **(extra or {}))
        runs.append(name)
        log = ROOT/f'tests/region_saves_check{"-real" if args.real else ""}-{len(runs)}-{name}-server.log'
        (arena/'ErrorLog.txt').unlink(missing_ok=True)
        with tempfile.TemporaryDirectory(prefix='dm-regions-data-') as data, log.open('w') as out:
            server = subprocess.Popen([str(dotnet), str(APP_RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={arena/"ck.json"}', '--cvar', f'opendream.topic_port={args.port + 13500}',
                '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={args.port}', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
                env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
            deadline = time.monotonic() + args.timeout
            try:
                done = lambda: 'CK|complete' in log.read_text(errors='replace') + ((arena/'ErrorLog.txt').read_text(errors='replace') if (arena/'ErrorLog.txt').exists() else '')   # the real world logs to its ErrorLog.txt
                while time.monotonic() < deadline and server.poll() is None and not done():
                    time.sleep(.5)
            finally:
                if server.poll() is None:
                    server.terminate()
                    try: server.wait(10)
                    except subprocess.TimeoutExpired: server.kill()
        t = log.read_text(errors='replace') + ((arena/'ErrorLog.txt').read_text(errors='replace') if (arena/'ErrorLog.txt').exists() else '')
        got = re.findall(r'CK\|([^|\r\n]+)\|([01])\|([^\r\n]*)', t)
        if 'CK|complete' not in t: got.append((f'{name}: the stage finished', '0', 'no CK|complete'))
        rows.extend(got)
        for m in re.findall(r'RG\|fp\|([0-9a-f]+)\|([^\r\n]*)', t): fps.append((name, m[0], m[1]))
        errors.extend(e for e in re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*|runtime error[^\r\n]*', t)[:5])
        print(f'-- {name}: {len(got)} checks, fingerprints {[f[1][:8] for f in fps if f[0] == name]}', flush=True)

    stage('save')
    keep = ROOT/'reports/quest-maker-1031/r3/units-after-save'
    if keep.exists(): shutil.move(str(keep), str(Path.home()/'.Trash'/f'units-after-save-{int(time.time())}'))
    shutil.copytree(arena/'units', keep)
    stage('load')
    for f in (arena).glob('rg-state-*.json'): shutil.copy2(f, ROOT/'reports/quest-maker-1031/r3'/f.name)
    stage('single', {'RM_REGION_FILES': '0'})
    for f in (arena).glob('rg-state-*.json'): shutil.copy2(f, ROOT/'reports/quest-maker-1031/r3'/f.name)
    shutil.copy2(arena/'rg-state-save.json', ROOT/'reports/quest-maker-1031/r3/rg-state-save.json')
    stamp = arena/'units/remaster_world.stamp'
    kept = stamp.read_text()
    stamp.write_text('a-later-single-save\r\n')
    stage('stale')
    stamp.write_text(kept)
    moved = Path(temp)/'regions-moved'
    shutil.move(str(arena/'units/regions'), str(moved))
    stage('migrate')
    stage('load')

first = fps[0][1] if fps else None
rows.append(('every start: the same world as the first save', '1' if fps and all(f[1] == first for f in fps) and len(fps) >= 6 else '0',
             '; '.join(f'{f[0]} {f[1][:8]} ({f[2]})' for f in fps)))
passed = bool(rows) and all(r[1] == '1' for r in rows) and not errors
(ROOT/('tests/region_saves_check-real-checks.json' if args.real else 'tests/region_saves_check-checks.json')).write_text(json.dumps(dict(passed=passed, game=str(args.game),
    checks=[dict(name=r[0], ok=r[1] == '1', detail=r[2]) for r in rows], errors=errors[:10]), indent=2) + '\n')
for r in rows: print(('  ' if r[1] == '1' else '!!'), r[0], r[2])
if errors: print('errors:', *errors[:5], sep='\n  ')
print('passed' if passed else 'FAILED')
if not passed: raise SystemExit(1)
