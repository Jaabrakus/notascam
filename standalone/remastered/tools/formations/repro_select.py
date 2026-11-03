#!/usr/bin/env python3
"""No-input repro of the real run's stall after the box select (formations, 2026-10-23). Prints the REPRO lines."""
import os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RT = ROOT.parent/'replica/runtime/macos-x64'
# --engine main: run on the app's own runtime (the main engine, with its native route search), copied for the run
MAIN = '--engine' in sys.argv and sys.argv[sys.argv.index('--engine') + 1] == 'main'
if MAIN: del sys.argv[sys.argv.index('--engine'):sys.argv.index('--engine') + 2]
DLL = None                       # --dll D: that OpenDreamRuntime.dll in the copied runtime (a test build)
if '--dll' in sys.argv:
    DLL = Path(sys.argv[sys.argv.index('--dll') + 1])
    del sys.argv[sys.argv.index('--dll'):sys.argv.index('--dll') + 2]
APP_RT = ROOT/'Banners of the Deep.app/Contents/Resources/game/runtime'
with tempfile.TemporaryDirectory(prefix='fm-repro-') as tmp:
    w = Path(tmp)/'world'
    shutil.copytree(ROOT/'game', w, ignore=shutil.ignore_patterns('Cave Crawlers.json', 'ErrorLog.txt', 'units', 'players', '*.log', '*.dmm'))
    dme = (w/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (w/'repro.dme').write_text(dme + '\n#include "repro_select.dm"\n', encoding='latin-1')
    world = w/'Code/World.dm'; text = world.read_text(encoding='latin-1')
    a = text.index('\tNew()'); b = text.index('\nvar/Season', a)
    world.write_text(text[:a] + '\tNew()\n\t\tspawn(0) ReproRun()\n' + text[b:], encoding='latin-1')
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('repro_select.dm')   # another repro: its path
    shutil.copy2(src, w/'repro_select.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    r = subprocess.run([str(RT/'dotnet/dotnet'), str(RT/'compiler/DMCompiler.dll'), str(w/'repro.dme')], env=env, capture_output=True, text=True)
    if r.returncode: print(r.stdout[-2000:]); sys.exit(1)
    SRV = RT
    if MAIN:
        SRV = Path(tmp)/'runtime'
        shutil.copytree(APP_RT, SRV, symlinks=True)
        if DLL: shutil.copy2(DLL, SRV/'server/Resources/Assemblies/OpenDreamRuntime.dll')
    log = Path(tmp)/'server.log'
    with log.open('w') as out:
        s = subprocess.Popen([str(SRV/'dotnet/dotnet'), str(SRV/'server/Robust.Server.dll'), '--data-dir', str(Path(tmp)/'data'),
            '--cvar', f'opendream.json_path={w/"repro.json"}', '--cvar', 'opendream.topic_port=25647', '--cvar', 'net.bindto=127.0.0.1',
            '--cvar', 'net.port=12197', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0',
            '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=out, stderr=subprocess.STDOUT, cwd=w)
        end = time.monotonic() + 240
        while time.monotonic() < end and s.poll() is None and 'REPRO|done' not in log.read_text(errors='replace'): time.sleep(.5)
        s.terminate()
        try: s.wait(10)
        except subprocess.TimeoutExpired: s.kill()
    t = log.read_text(errors='replace')
    el = (w/'ErrorLog.txt').read_text(errors='replace') if (w/'ErrorLog.txt').exists() else ''
    for l in re.findall(r'REPRO\|[^\r\n]*', t + el): print(l)
    for l in re.findall(r'(?:runtime error|Exception occurred)[^\r\n]*(?:\r?\n[^\r\n]*){0,4}', el + t)[:5]: print('ERROR', l)
    print('DONE' if 'REPRO|done' in t + el else 'HUNG OR FAILED')
