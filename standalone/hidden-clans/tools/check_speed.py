#!/usr/bin/env python3
"""Pause and game speed on Remastered's engine (engine/server/OpenDreamRuntime.dll):
world time runs about 1x/2x/3x real time, stands still while paused, and a command
arriving while paused (a world Topic, like a player's order) still runs."""
import os, re, shutil, socket, struct, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT.parent/'replica/runtime/macos-x64'

def topic(port, query):
    data = query.encode() 
    pkt = b'\x00\x83' + struct.pack('>H', len(data) + 6) + b'\x00' * 5 + data + b'\x00'
    with socket.create_connection(('127.0.0.1', port), timeout=5) as s:
        s.sendall(pkt)
        try: s.recv(1024)
        except Exception: pass

def main():
    arena = ROOT/'tests/speed-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'speed.dme').write_text(dme + '\n#include "speed_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'; text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) SpRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/speed_test.dm', arena/'speed_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'speed.dme')], env=env, stdout=open(ROOT/'tests/speed-compile.log', 'w'), stderr=subprocess.STDOUT, check=True)
    server_dir = Path(tempfile.mkdtemp(prefix='rm-server-'))/'server'
    shutil.copytree(RUNTIME/'server', server_dir)
    shutil.copy2(ROOT/'engine/server/OpenDreamRuntime.dll', server_dir/'Resources/Assemblies/OpenDreamRuntime.dll')
    log = ROOT/'tests/speed-server.log'
    port = 25695
    with tempfile.TemporaryDirectory(prefix='dm-speed-') as data, log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(server_dir/'Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"speed.json"}', '--cvar', f'opendream.topic_port={port}',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12245', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        read = lambda: log.read_text(errors='replace')
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline and 'SP|pause' not in read(): time.sleep(.5)
        time.sleep(5)                       # paused for 5 real seconds
        beats_paused = read().count('SP|beat|')
        time.sleep(3)
        still = read().count('SP|beat|') == beats_paused
        topic(port, '?resume')
        t0 = time.monotonic()
        while time.monotonic() - t0 < 15 and 'SP|after' not in read(): time.sleep(.5)
        server.terminate()
        try: server.wait(10)
        except subprocess.TimeoutExpired: server.kill()
    text = read()
    sp = [(int(a), float(b), float(c)) for a, b, c in re.findall(r'SP\|speed\|(\d)\|([\d.]+)\|([\d.]+)', text)]
    pz = re.search(r'SP\|pause\|([\d.]+)\|([\d.]+)', text)
    marks = sp + ([(0, float(pz.group(1)), float(pz.group(2)))] if pz else [])
    ok = len(marks) == 4
    for (s, wt, rt), (_, wt2, rt2) in zip(marks, marks[1:]):
        ratio = (wt2 - wt) / max(1, (rt2 - rt))
        print(f'speed {s}: world time {wt2 - wt:.0f} ds over real {rt2 - rt:.0f} ds -> x{ratio:.2f}')
        ok = ok and abs(ratio - s) < 0.35 * s
    print('paused: no beats for 3 s:', still)
    print('resumed by a command while paused:', 'SP|resumed' in text, '| sleeps woke again:', 'SP|after' in text)
    ok = ok and still and 'SP|resumed' in text and 'SP|after' in text
    print('passed' if ok else 'FAILED')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
