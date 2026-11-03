#!/usr/bin/env python3
"""Run the half-demon kinds (HalfDemons.dm) in a bounded arena: building a Good Altar, desecrating it into an
Evil Altar, Unholy Blood (Marked), Holy Water, embers and Hellfire (Ashen), Hellblooded births, and each kind's
3D body sheet."""
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
CHECKS = ['altar_in_catalog', 'altar_needs_gold', 'altar_built', 'altar_darkens', 'altar_turns_evil', 'unholy_vampire', 'drink_unholy_offered',
          'marked', 'marked_sheet', 'marked_feeds', 'holy_washes_out', 'embers_filled', 'hellfire_blessed', 'ashen',
          'ashen_sheet', 'ashen_no_burn', 'ashen_no_heat', 'hellfire_kills_weak', 'hellblooded_from_demon_father',
          'hellblooded_from_demon_mother', 'hellblooded_sheet', 'hellblood_not_washed', 'original_kept',
          'possessed_stages', 'kind_on_panel', 'flyers_64', 'gargoyle_eyes_kept']


def main():
    arena = ROOT/'tests/halfdemons-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', '*.sav', 'units', 'players', 'backup'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'halfdemons.dme').write_text(dme + '\n#include "halfdemons_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) HDRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/halfdemons_test.dm', arena/'halfdemons_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    with (ROOT/'tests/halfdemons-compile.log').open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'halfdemons.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/halfdemons-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-halfdemons-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"halfdemons.json"}', '--cvar', 'opendream.topic_port=25893',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12393', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline and server.poll() is None:
            t = server_log.read_text(errors='replace')
            if 'HD|complete' in t or '[ERRO]' in t: break
            time.sleep(.2)
        time.sleep(1)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    lines = re.findall(r'HD\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    passed = {l.split('|')[2] for l in lines if l.startswith('HD|PASS|')}
    result = dict(passed=all(c in passed for c in CHECKS) and 'HD|complete|failures=0' in lines and not errors,
                  lines=lines, errors=errors)
    (ROOT/'tests/halfdemons-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for l in lines: print(('  ' if '|PASS|' in l or 'complete' in l else '!!'), l)
    for c in CHECKS:
        if c not in passed: print('!! missing', c)
    if errors: print('\n'.join(errors[:8]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
