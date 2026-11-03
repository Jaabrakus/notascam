#!/usr/bin/env python3
"""Run flying (Flying.dm) and the room beasts take (Beasts.dm) in a bounded arena: crossing water
and walls, route planning, landing, heights and the skill bar, a dragon's feet, trees knocked down."""
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
CHECKS = ['takes_off', 'flies_over_water', 'walker_stopped_by_water', 'flies_over_wall', 'route_over',
          'no_landing_on_water', 'lands_on_grass', 'dragon_feet', 'feet_block_others', 'foot_is_the_beast', 'feet_lift_flying', 'dragon_heights',
          'fly_higher', 'dragon_lands', 'dragon_knocks_down_tree', 'young_spider_leaves_trees', 'spider_feet', 'dragon_grows', 'dead_dragon_lies', 'dead_spider_lies', 'breath_area', 'fight_splash',
          'part_strike', 'wings_ground', 'arrow_wings', 'right_click_part', 'ballista_built', 'ballista_wings',
          'health_rows', 'wild_dragon_lands', 'wild_dragon_breathes', 'wild_dragon_backs_off', 'wing_blows_end', 'part_health',
          'flyer_click_on_rock_flies_on_top', 'walkers_still_mine_rock']


def main():
    arena = ROOT/'tests/flying-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', '*.sav', 'units', 'players', 'backup'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'flying.dme').write_text(dme + '\n#include "flying_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) FlyRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/flying_test.dm', arena/'flying_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    with (ROOT/'tests/flying-compile.log').open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'flying.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/flying-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-flying-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"flying.json"}', '--cvar', 'opendream.topic_port=25873',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12373', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline and server.poll() is None:
            t = server_log.read_text(errors='replace')
            if 'FLY|complete' in t or '[ERRO]' in t: break
            time.sleep(.2)
        time.sleep(1)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    lines = re.findall(r'FLY\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    passed = {l.split('|')[2] for l in lines if l.startswith('FLY|PASS|')}
    result = dict(passed=all(c in passed for c in CHECKS) and 'FLY|complete|failures=0' in lines and not errors,
                  lines=lines, errors=errors)
    (ROOT/'tests/flying-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for l in lines: print(('  ' if '|PASS|' in l or 'complete' in l else '!!'), l)
    for c in CHECKS:
        if c not in passed: print('!! missing', c)
    if errors: print('\n'.join(errors[:8]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
