#!/usr/bin/env python3
"""Families and captives in a bounded arena."""
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
EXPECTED = [   # prefixes: a line passes when it starts with one of these (details after it are logged as they come)
    'CP|partners|1',
    'CP|child|expecting=1',
    'CP|skill|partner_unlisted=1',
    'CP|ko_still|1|walks_awake=1',
    'CP|subdue|first=1',
    'CP|norope|1|says=1',
    'CP|bind|1|owner=1|state=bound|rope_used=1|rope=Iron Chains|walk=0|strike=0|house=0|disarmed=1|captor_has=1',
    'CP|nogear|1',
    'CP|led|1',
    'CP|guarded_odds|0',
    'CP|nojoin|1',
    'CP|fetch|1|rope=plant',
    'CP|dragged|1|ko=1',
    'CP|outcold|refused=1|nogain=1|why=1|says=1',
    'CP|winover|1|name=1|house=1|rope_back=1',
    'CP|slave|1|name=1|works=1|house=0|heir=0|attack=0|stance=off|slower=1',
    'CP|armed|fights_loyal=1|armed=1|turned=1',
    'CP|odds|1',
    'CP|breakfree|1',
    'CP|guarded_holds|1',
    'CP|release|1|rope_left=1',
    'CP|revolt|guarded=0|unguarded_rose=1|untied=1|armed=1|struck=1|ran=1',
    'CP|strike|1',
    'CP|unarmed|1',
    'CP|peace|1',
    'CP|ruler|1',
    'CP|tame|1',
    'CP|craft|1',
    'CP|lines|two=1|behind=1|noring=1|followed=1|closeup=1|nostack=1',
    'CP|tree|1',
    'CP|stake|1|refused=1|wood_used=1|card=1|model=1|rope3d=1|stays=1',
    'CP|stake2|1',
    'CP|tieto|1|bare_refused=1',
    'CP|cage3d|1',
    'CP|cage|1|noescape=1|nocarry=1|card=1|ropeback=1|undrawn=1|refused=1|out=1|picked=1',
    'CP|cagewalk|1|name=metal cage',
    'CP|limbs|bound=1|joined=1|slave=1|leg=1',
    'CP|ropelook|bound=1|slave=1|joined=1',
    'CP|model|1',
    'CP|save|bound=1|slave=1|loyalty=1|rope=1|tied=1|from=1|limbs=1',
    'CP|complete',
]


def main():
    arena = ROOT/'tests/capture-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'capture.dme').write_text(dme + '\n#include "capture_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) CpRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/capture_test.dm', arena/'capture_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/capture-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'capture.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/capture-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-capture-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"capture.json"}', '--cvar', 'opendream.topic_port=25789',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12289', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline and server.poll() is None:
            log_text = server_log.read_text(errors='replace')
            if 'CP|complete' in log_text or '[ERRO]' in log_text or 'rosetta error' in log_text: break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'CP\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    ok = len(actual) == len(EXPECTED) and all(a == e or a.startswith(e + '|') for a, e in zip(actual, EXPECTED))
    result = dict(passed=ok and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/'tests/capture-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        good = e == a or (e and a.startswith(e + '|'))
        print(('  ' if good else '!!'), a, '' if good else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
