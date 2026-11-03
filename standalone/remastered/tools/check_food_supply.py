#!/usr/bin/env python3
"""Food pots and food stalls (FoodSupply.dm) in a bounded arena: building, the pot's fire, filling,
eating there and the stockpile fallback, poisoning at war, tasting, falling sick, inspecting,
emptying, the Antidote and the offline catch-up."""
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
CHECK_GAME = Path(os.environ['RM_CHECK_GAME']) if os.environ.get('RM_CHECK_GAME') else ROOT/'game'   # RM_CHECK_GAME: a frozen copy to test (engine A/Bs on one game)
RUNTIME = ROOT.parent/'replica/runtime/macos-x64'   # shared engine, used read-only
EXPECTED = [
    'FS|build|pot=1|stall=1|catalog=1',
    'FS|pot_fire|lit=1|hot=1|stewed=1',
    'FS|cook_pot|filled=1|fed=1|raw_gone=1',
    'FS|farmer_stall|1',
    'FS|restock|1',
    'FS|eat_pot|ate=1|from_pot=1|stockpile_kept=1|note=1',
    'FS|hot_stew|1',
    'FS|eat_stall|ate=1|took_along=1',
    'FS|fallback|1',
    'FS|poison|peace_refused=1|war_ok=1|dose=1|unseen=1|box=1',
    'FS|sick|dosed=1|sick=1|hurt=1|blood=1|suspect=1|alert=1|log=1|avoided=1',
    'FS|vomit|1',
    'FS|hud|box=1|3d=1',
    'FS|witness|seen=1|alarm=1',
    'FS|taste|spat=1|suspect=1|alert=1',
    'FS|inspect|found=1|emptied=1',
    'FS|cook_throws|1',
    'FS|antidote_brew|1',
    'FS|antidote|cured=1|drank=1|log=1',
    'FS|death|died=1|score=1',
    'FS|away|served=1|poisoned=1|report=1',
    'FS|away_restock|1',
    'FS|stock|1',
    'FS|save|1',
    'FS|sleep|1',
    'FS|complete',
]


def main():
    arena = ROOT/'tests/foodsupply-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(CHECK_GAME, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'foodsupply.dme').write_text(dme + '\n#include "foodsupply_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) FsRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/foodsupply_test.dm', arena/'foodsupply_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/foodsupply-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'foodsupply.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/foodsupply-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-foodsupply-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"foodsupply.json"}', '--cvar', 'opendream.topic_port=25627',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12177', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 480
        while time.monotonic() < deadline and server.poll() is None:
            if 'FS|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'FS\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/'tests/foodsupply-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
