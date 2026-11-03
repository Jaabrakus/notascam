#!/usr/bin/env python3
"""Run the Build tab's construction tasks (stockpile hauling, waiting, stairs, saves) in a bounded arena."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT.parent/'replica/runtime/macos-x64'   # shared engine, used read-only
EXPECTED = [
    'CN|catalog|stone=1|stairs=1|forge=1|elf=0|silk=0|tribal=0',
    'CN|pick|PlaceStoneWall',
    'CN|planned|tiles=12|sites=1|crew=0|label=Stone wall',
    'CN|needs|need=12|stock=8|missing=4|text=12 stone: 8 in stockpiles, 4 missing',
    'CN|waiting|built=8|walls=8|left=4|stock=0|board=1|state=waiting|needs=1|missing=4',
    'CN|resumed|built=12|walls=12|done=1|stock=2|carried=0',
    'CN|support|12',
    'CN|sky_wait|1|wall=0',
    'CN|sky_built|ground=1|sky=1|done=1',
    'CN|stairs|mode=Stairs:Stone:Up|built=1|low=StoneUp|high=StoneDown',
    'CN|assigned|on=1|floors=4|wood_back=1|duty=0|job=manual',
    'CN|save|json=1|site=1|tiles=4|crew=1',
    'CN|cancel|tiles=0|note=Cancelled|duty=0',
    'CN|fortress_wall|planned=16|built=16|walls=16|walks=16|label=Fortress wall',
    'CN|wall_stairs|built=1|low=StoneUp|high=StoneDown',
    'CN|ramp_beside|need=3|built=1|ramp=2|top=StoneUp|stone_used=3',
    'CN|ramp_cut|built=1|open=1|need=Needs no material (the wall\'s own stone)',
    'CN|gate|built=1|door=1|arch=2',
    'CN|tower_merge|warned=1|clear=1',
    'CN|tower|built=9|walls=9|walks=9|label=Tower',
    'CN|beams|planned=3|at=9,18,24|need=3 wood: 3 in stockpiles|built=3|beams=3',
    'CN|cave_in|beamed_open=20/20|plain_fell=1',
    'CN|beam_auto|made=2|carried=2|placed_at=25,30|left=0|kept=1',
    'CN|complete',
]


def main():
    arena = ROOT/'tests/construction-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'construction.dme').write_text(dme + '\n#include "construction_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) ConstructionRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/construction_test.dm', arena/'construction_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/construction-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'construction.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/construction-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-construction-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"construction.json"}', '--cvar', 'opendream.topic_port=25841',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12341', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 1500
        while time.monotonic() < deadline and server.poll() is None:
            if 'CN|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'CN\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/'tests/construction-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
