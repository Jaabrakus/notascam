#!/usr/bin/env python3
"""Great beasts crippled, never cut apart (Beasts.dm), butchered into parts (BeastParts.dm) and tamed
(Taming.dm): eggs stolen and hatched, chains, feeding, breaking free. A bounded arena."""
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
CHECKS = ['leg_never_cut', 'arrows_dont_cut', 'lame_cant_walk', 'health_says_crippled', 'butcher_dragon', 'butcher_spider', 'gear_tiers',
          'dragon_coloured_gear', 'dragonscale_fireproof', 'dragonheart_draught', 'forge_chains', 'map_dragon_grown_nest', 'egg_mother_hunts', 'egg_carrier_told', 'egg_hatches', 'young_dragon_status',
          'nest_egg_stays', 'guards_nest', 'chain_order', 'chain_needs_chains', 'chain_binds', 'bound_in_3d', 'chained_status', 'fed_and_tamed', 'snaps_free',
          'web_shot', 'webbed_in_3d', 'web_shot_needs_silk', 'web_wears_off', 'sticky_web_calls_spiders', 'sticky_web',
          'swing_times', 'swing_gate', 'damage_per_blow', 'chains_saved', 'part_prices', 'weapon_effects', 'bow_range', 'jaws_reach']


def main():
    arena = ROOT/'tests/taming-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', '*.sav', 'units', 'players', 'backup'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'taming.dme').write_text(dme + '\n#include "taming_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) TameRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/taming_test.dm', arena/'taming_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    with (ROOT/'tests/taming-compile.log').open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'taming.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/taming-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-taming-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"taming.json"}', '--cvar', 'opendream.topic_port=25923',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12423', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline and server.poll() is None:
            t = server_log.read_text(errors='replace')
            if 'TAME|complete' in t or '[ERRO]' in t: break
            time.sleep(.2)
        time.sleep(1)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    lines = re.findall(r'TAME\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    passed = {l.split('|')[2] for l in lines if l.startswith('TAME|PASS|')}
    result = dict(passed=all(c in passed for c in CHECKS) and 'TAME|complete|failures=0' in lines and not errors,
                  lines=lines, errors=errors)
    (ROOT/'tests/taming-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for l in lines: print(('  ' if '|PASS|' in l or 'complete' in l else '!!'), l)
    for c in CHECKS:
        if c not in passed: print('!! missing', c)
    if errors: print('\n'.join(errors[:8]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
