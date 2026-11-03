#!/usr/bin/env python3
"""Run the new gear (Gear.dm, GearData.dm) in a bounded arena: catalogue and pictures, crafting
through the real workshop clicks, refusals, equip levels, two hands, enchanting, the 3D layers."""
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
CHECKS = ['catalogue', 'pictures_64', 'level_refused', 'forge_sword', 'material_refused', 'race_rules', 'arm_pair',
          'hell_needs_lava', 'hell_beside_lava', 'equip_level', 'two_hands', 'leather_robe', 'enchant_mana',
          'original_menu', 'view3d']


def main():
    arena = ROOT/'tests/gear-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', '*.sav', 'units', 'players', 'backup'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'gear.dme').write_text(dme + '\n#include "gear_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) GearRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/gear_test.dm', arena/'gear_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    with (ROOT/'tests/gear-compile.log').open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'gear.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/gear-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-gear-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"gear.json"}', '--cvar', 'opendream.topic_port=25871',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12371', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline and server.poll() is None:
            t = server_log.read_text(errors='replace')
            if 'GEAR|complete' in t or '[ERRO]' in t: break
            time.sleep(.2)
        time.sleep(1)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    lines = re.findall(r'GEAR\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    passed = {l.split('|')[2] for l in lines if l.startswith('GEAR|PASS|')}
    result = dict(passed=all(c in passed for c in CHECKS) and 'GEAR|complete|failures=0' in lines and not errors,
                  lines=lines, errors=errors)
    (ROOT/'tests/gear-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for l in lines: print(('  ' if '|PASS|' in l or 'complete' in l else '!!'), l)
    for c in CHECKS:
        if c not in passed: print('!! missing', c)
    if errors: print('\n'.join(errors[:8]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
