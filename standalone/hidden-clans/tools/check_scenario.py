#!/usr/bin/env python3
"""Real-map scenario: two launches of the full Remastered world (map files
included). Launch 1 settles a village by a real forest and lets the real tick
build, gather, breed and save; launch 2 restores and verifies."""
import os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT.parent/'replica/runtime/macos-x64'

def launch(world, label, limit):
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/f'tests/scenario-{label}-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-scn-') as data, log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={world/"scenario.json"}', '--cvar', 'opendream.topic_port=25611',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12161',
            '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0',
            '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=out, stderr=subprocess.STDOUT, cwd=world)
        deadline = time.monotonic() + limit
        errlog = world/'ErrorLog.txt'
        start_size = errlog.stat().st_size if errlog.exists() else 0
        def game_log():
            # This game writes world.log to its ErrorLog.txt.
            return log.read_text(errors='replace') + (errlog.read_text(errors='replace')[start_size:] if errlog.exists() else '')
        while time.monotonic() < deadline and server.poll() is None:
            text = game_log()
            if 'SCN|complete' in text or 'Stack overflow' in text: break
            time.sleep(2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(15)
            except subprocess.TimeoutExpired: server.kill()
    text = game_log()
    lines = re.findall(r'SCN\|[^\r\n]*', text)
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    errlog = world/'ErrorLog.txt'
    runtime = re.findall(r'runtime error[^\r\n]*', text)
    return lines, errors, runtime

def main():
    world = ROOT/'tests/scenario-world'
    if world.exists(): shutil.rmtree(world)
    shutil.copytree(ROOT/'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', 'ErrorLog.txt', 'units', 'players'))
    dme = (world/'Cave Crawlers.dme').read_text(encoding='latin-1')
    (world/'scenario.dme').write_text(dme + '\n#include "scenario_test.dm"\n', encoding='latin-1')
    shutil.copy2(ROOT/'tests/scenario_test.dm', world/'scenario_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    with (ROOT/'tests/scenario-compile.log').open('w') as out:
        subprocess.run([str(RUNTIME/'dotnet/dotnet'), str(RUNTIME/'compiler/DMCompiler.dll'), str(world/'scenario.dme')],
                       env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    ok = True
    for label, limit in (('launch1', 1200), ('launch2', 300)):
        lines, errors, runtime = launch(world, label, limit)
        print(f'--- {label}')
        for l in lines: print('  ', l[:260])
        for e in (errors + runtime)[:6]: print('  !!', e[:200])
        if not any('SCN|complete' in l for l in lines): ok = False
    print('finished' if ok else 'INCOMPLETE')

if __name__ == '__main__':
    main()
