#!/usr/bin/env python3
"""Fog of war (Fog.dm) in a mapless arena, no client (tests/fog_test.dm): out of sight not sent, in sight sent, a wall
blocks sight, explored stays explored, night shortens sight (not for races that see in the dark), high ground sees
further, an ally's sight is shared, a building is remembered once gone, a save round trip, and the cost with 200 units.
    python3 tools/check_fog.py        exit status 1 on any failure"""
import os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT.parent/'replica/runtime/macos-x64'


def main():
    arena = ROOT/'tests/fog-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
    (arena/'fog.dme').write_text(dme + '\n#include "fog_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) FogTestRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/fog_test.dm', arena/'fog_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    comp = subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'fog.dme')], env=env, capture_output=True, text=True)
    if comp.returncode:
        print('\n'.join(l for l in comp.stdout.splitlines() if 'Error' in l)[:3000]); return 1
    log = ROOT/'tests/fog-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-fog-') as data, log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"fog.json"}', '--cvar', 'opendream.topic_port=25893',
            '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12393', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline and server.poll() is None:
            t = log.read_text(errors='replace')
            if 'FOG|complete' in t or '[ERRO]' in t: break
            time.sleep(.3)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = log.read_text(errors='replace')
    rows = re.findall(r'FOG\|([^|\r\n]*)\|([^|\r\n]*)\|([^\r\n]*)', text)
    for name, res, detail in rows: print(f'{res:5} {name}: {detail}')
    errors = re.findall(r'(?:\[(?:ERRO|FATL)\]|runtime error)[^\r\n]*', text)
    if errors: print('\n'.join(errors[:8]))
    shutil.rmtree(arena)
    ok = rows and all(r[1] == 'pass' for r in rows) and 'FOG|complete' in text and not errors
    print('PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
