#!/usr/bin/env python3
"""Loose goods rot; goods on a stockpile or zone (or beside one) don't.

One boot of an arena on the packaged Remastered runtime. The fixture shortens
the rot timer to 30 seconds through remaster_rot_delay."""
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
COMPILER = ROOT.parent/'replica/runtime/macos-x64/compiler/DMCompiler.dll'   # shared, used read-only
EXPECTED = {
    'first': {'stockpile-wood': 'kept', 'beside-stone': 'kept', 'zone-ingot': 'kept', 'moved-off-seeds': 'kept',
              'two-away-gem': 'rotted', 'loose-wood': 'rotted', 'carried-wood': 'kept'},
    'second': {'stockpile-wood': 'kept', 'beside-stone': 'kept', 'zone-ingot': 'kept', 'moved-off-seeds': 'rotted',
               'two-away-gem': 'rotted', 'loose-wood': 'rotted', 'carried-wood': 'kept'},
}


def main():
    tests = ROOT/'tests'
    with tempfile.TemporaryDirectory(prefix='dm-rot-') as temp:
        arena = Path(temp)/'arena'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players'))
        (arena/'units').mkdir()
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        (arena/'rot.dme').write_text(dme + '\n#include "stockpile_rot_test.dm"\n', encoding='latin-1')
        world = arena/'Code/World.dm'
        text = world.read_text(encoding='latin-1')
        start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
        world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) RtRun()\n' + text[end:], encoding='latin-1')
        shutil.copy2(tests/'stockpile_rot_test.dm', arena/'stockpile_rot_test.dm')
        dotnet = APP_RUNTIME/'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (tests/'stockpile-rot-compile.log').open('w') as out:
            subprocess.run([str(dotnet), str(COMPILER), str(arena/'rot.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
        log = tests/'stockpile-rot-server.log'
        with tempfile.TemporaryDirectory(prefix='dm-rot-data-') as data, log.open('w') as out:
            server = subprocess.Popen([str(dotnet), str(APP_RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={arena/"rot.json"}', '--cvar', 'opendream.topic_port=25790',
                '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12290', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
                env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline and server.poll() is None and 'RT|complete' not in log.read_text(errors='replace'):
                time.sleep(.5)
            if server.poll() is None:
                server.terminate()
                try: server.wait(10)
                except subprocess.TimeoutExpired: server.kill()
        errorlog = arena/'ErrorLog.txt'
        text = log.read_text(errors='replace') + (errorlog.read_text(errors='replace') if errorlog.exists() else '')
    states = {}
    for tag, rest in re.findall(r'RT\|(start|first|second)((?:\|[^|\r\n]+)+)', text):
        states[tag] = dict(p.split('=') for p in rest.strip('|').split('|'))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*|runtime error[^\r\n]*', text)
    result = dict(passed=states.get('first') == EXPECTED['first'] and states.get('second') == EXPECTED['second'] and not errors,
                  expected=EXPECTED, actual=states, errors=errors[:10])
    (tests/'stockpile-rot-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for tag in ('first', 'second'):
        for k, v in EXPECTED[tag].items():
            got = states.get(tag, {}).get(k)
            print(('  ' if got == v else '!!'), f'{tag} check: {k} {got}' + ('' if got == v else f' (expected {v})'))
    if errors: print('errors:', *errors[:5], sep='\n  ')
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
