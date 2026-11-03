#!/usr/bin/env python3
"""Run buildings and lairs (Buildings.dm): whole buildings, rotation, a spider's and a dragon's lair dug out underground, sticky webs, hoard healing, a dwarven hall dug into rock, walls holding the roof, mine carts (Carts.dm), power (Power.dm) and mountain tops (Peaks.dm)."""
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
    'BLD|catalog|hall=1|lair=0|bed=1|web=0|house=0',
    'BLD|rotate|placed=1|door=-2,0|facing=west|label=Timber house',
    'BLD|hall_planned|pieces=60|label=Dwarven forge-hall|mode=|needs=26 stone: 26 in stockpiles; 2 beds: 2 in stockpiles; 1 table: 1 in stockpiles; 1 chair: 1 in stockpiles; 1 door: 1 in stockpiles',
    'BLD|hall|built=60/60|walls=25|floor=28|forge=2|beds=2|table=1|chair=1|door=1|done=1',
    'BLD|hall_map|WWWWWWWWW/WFFfffBBW/WfffffffW/WffTCfffW/WfffffffW/WWWWDWWWW',
    'BLD|spider_catalog|lair=1|web=1|cocoon=1',
    'BLD|lair_planned|placed=1|dig=5|pieces=32',
    'BLD|lair|built=32/32|inside_rock=4|silk=25|cocoons=2|cobwebs=2|web=1|lair=1|digging=0|done=1',
    'BLD|lair_map|RRRRRRRRR/RWc*f*cWR/RfffffffR/RfffffffR/RRfffffRR/RRRRwRRRR',
    'BLD|lair_web|2|kind=spider',
    'BLD|web|held=1|called=1|holds=2|own_spider_free=1',
    'BLD|dragon_planned|placed=1|dig=7|pieces=1',
    'BLD|dragon|built=1/1|rock=8|hoard=1|lair=1|done=1',
    'BLD|dragon_map|RRR.....RRR/R.........R/R....H....R/R.........R/RRR.....RRR',
    'BLD|hoard_heal|plain=3|treasure=10|rich=5',
    'BLD|egg|ok=1',
    'BLD|dhall_planned|placed=1|label=Dwarven hall|door=49,9|pillars=2|dig=1',
    'BLD|dhall|built=39/39|pillars=2|beds=4|forge=2|door=1|rock_walls=8|cave_in_risk=7|done=1',
    'BLD|dhall_map|RRRRRRRRR/RBfBfBfBR/RffCTCffR/RfffffFFR/RfffffffR/RRRRDRRRR',
    'BLD|wall_holds|before=1|held=1|marks=3|after=1|left=0',
    'BLD|carts|laid=9|to_stop=1|at_stop=5|delivered=5|cart=22,22|note=Waiting for loads',
    'BLD|power|built=10/10|wheel_dir=8|parts=10|supply=10|demand=9|on=1|smith=1|mana=5|overload=0/0',
    'BLD|power_rules|dry=a water wheel goes on the bank, beside water|deep=a windmill needs the open sky (not underground or under rock)|text=Not enough power: 10 made, 14 wanted',
    'BLD|peaks|unheld=Sky|over_rock=Peak|over_tunnel=Peak|over_built_wall=Sky',
    'BLD|save|building=1|rot=1',
    'BLD|complete',
]


def main():
    # --label: its own arena, logs and results, so two runs at once never share them (ports are always free ones)
    label = sys.argv[sys.argv.index('--label') + 1] if '--label' in sys.argv else 'buildings'
    from check_engine import free_port
    arena = ROOT/f'tests/{label}-arena'
    if arena.exists(): shutil.rmtree(arena)
    game = Path(os.environ['RM_CHECK_GAME']) if os.environ.get('RM_CHECK_GAME') else ROOT/'game'   # RM_CHECK_GAME: a copy to test, as check_food.py
    shutil.copytree(game, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'buildings.dme').write_text(dme + '\n#include "buildings_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) BuildingsRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/buildings_test.dm', arena/'buildings_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/f'tests/{label}-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'buildings.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/f'tests/{label}-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-buildings-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"buildings.json"}', '--cvar', f'opendream.topic_port={free_port("tcp")}',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={free_port("udp")}', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 2400
        while time.monotonic() < deadline and server.poll() is None:
            if 'BLD|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'BLD\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/f'tests/{label}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
