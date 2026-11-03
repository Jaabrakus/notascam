#!/usr/bin/env python3
"""The village's SS13-style trades in a bounded arena: the Gravedigger (Graves.dm), forensics
(Forensics.dm), examine text and speech bubbles (Speech.dm), rescue and surgery with grafts and false
limbs including automail (Surgery.dm), and the tavern with its drunken brawls (Tavern.dm)."""
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
    'VG|build|surgery=1|graveyard=1|tavern=1|catalog=1',
    'VG|gravedigger|buried=1|plot=1|log=1|cheer=1|critter_left=1|clean=1|status=1',
    'VG|away|buried=1',
    'VG|forensics|poisoned=1|clue=1|tracks=1|read=1|realm=1|grievance=1|alert=Clue|emptied=1|traitor=1|noticed=1',
    'VG|look|text=1|healthy=1|say=1|gap=1|force=1|fades=1|hurt=1',
    'VG|rescue|carried=1|table=1|log=1',
    'VG|surgery|own=1|box=1|harvest=1|foreign=1|bonus=1|look=1|reject=1|undone=1',
    'VG|autoharvest|grafted=1|from_body=1|orc=1',
    'VG|automail|skill_needed=1|made=1|fitted=1|while_waiting=1|bonus=1|look=1|walks=1|lost=1',
    'VG|tavern|pour=1|press=1|box=1|drink=1|care=1|rounds=1|friends=1|day=1',
    'VG|cook|pressed=1',
    'VG|brawl|started=1|log=1|blows=1|guard=1|sobered=1|timeout=1|patrol_sober=1',
    'VG|brawl_ko|blow_ko=0|ended=1|down=0|alive=1',
    # no 'say': speech bubbles are no longer sent to the 3D view (the user, 2026-10-23); a unit still says its lines
    'VG|hud|table=1|tavern=1|look=1|3d=optable,tavern,graveyard,grave,trace,look,glow,brawl',
    'VG|limbs3d|state=NoLeftLegNoRightArm|orc=1|automail=1|tex=1',
    'VG|demonflesh|mad=1|possessed=1|either_not_both=1|most_fine=1',
    'VG|soulstone|kept=1|took=1|gave=1|woke=1|one_soul=1|rare=1',
    'VG|undead|zombie=1|breath=fire,frost,poison,magma,sand,water,plague,holy,unholy|magma_burns=1|werewolf=1|by_day=1',
    'VG|save|tavern=1|limbs=1',
    'VG|complete',
]


def main():
    arena = ROOT/'tests/village-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'village.dme').write_text(dme + '\n#include "village_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) VgRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/village_test.dm', arena/'village_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/village-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'village.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/village-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-village-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"village.json"}', '--cvar', 'opendream.topic_port=25637',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12187', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 720
        while time.monotonic() < deadline and server.poll() is None:
            if 'VG|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'VG\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/'tests/village-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
