#!/usr/bin/env python3
"""Run lifts (Lifts.dm): a shaft from the surface down to a tunnel and a lift up a cliff, still without power, ridden by move orders both ways once a drive train turns them."""
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
    'LIFT|catalog|up=1|down=1|need=6',
    'LIFT|built|ok=1|top=LiftOffD|bottom=LiftOffU|bottom_open=1|winch=1|head=1|wood_left=0',
    'LIFT|off|stairs_to=0|towards=0',
    'LIFT|on|top=LiftDown|bottom=LiftUp|stairs_to=2|towards=1',
    'LIFT|ride_down|at=14,10,2',
    'LIFT|ride_up|at=12,12,1',
    'LIFT|cliff_rules|no_peak=the top must come out beside a mountain top or a wall walk|again=there are stairs there already',
    'LIFT|cliff|built=1|bottom=LiftUp|top=LiftDown|stairs_to=3',
    'LIFT|ride_cliff|at=27,13,3',
    'LIFT|ride_cliff_down|at=21,13,1',
    'LIFT|power_off|top=LiftOffD|bottom=LiftOffU|stairs_to=0',
    'LIFT|save|lift=2|dirty=1',
    'LIFT|complete',
]


def main():
    arena = ROOT/'tests/lifts-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'lifts.dme').write_text(dme + '\n#include "lifts_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) LiftsRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/lifts_test.dm', arena/'lifts_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/lifts-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'lifts.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/lifts-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-lifts-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"lifts.json"}', '--cvar', 'opendream.topic_port=25857',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12357', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 2400
        while time.monotonic() < deadline and server.poll() is None:
            if 'LIFT|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'LIFT\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/'tests/lifts-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
