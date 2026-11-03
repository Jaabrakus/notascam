#!/usr/bin/env python3
"""Stumps (Stumps.dm) in a bounded arena: an untreated stump bleeds until it kills; a bandage slows it but it still
bleeds; a torch, a fire beside, a fire spell and catching fire seal it; the poultice, brews and the Potion of
Restoration; self-care from the bag, a helper, the Doctor; blood back slowly; ordinary wounds as the original;
crafting at the stations; the Health tab data and buttons; savefile round trip and older saves.

Writes tests/stumps-checks.json, and the Health tab data the arena produced (stump-health*.json) into
tests/stumps-arena/ for tools/check_stumps_hud.py. SC_ONLY=doctor_torch,save runs just those scenarios.
SCDEBUG lines in tests/stumps-server.log say why a scenario failed."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

import check_engine

ROOT = Path(__file__).resolve().parents[1]
CHECK_GAME = Path(os.environ['RM_CHECK_GAME']) if os.environ.get('RM_CHECK_GAME') else ROOT/'game'   # RM_CHECK_GAME: a frozen copy to test (engine A/Bs on one game)
# The engine (the app's by default, or the replica's) and the game speed: --engine / --speed (tools/check_engine.py).
EXPECTED = [
    'SC|open|stump=1|nostop=1|drain=1|kills=1|log=1',
    'SC|bandage|self=1|hold=70|slower=1|still=1',
    'SC|torch|sealed=1|hurt=1|burns=2|nobleed=1|back=1|slow=1',
    'SC|fire|sealed=1|log=1',
    'SC|walkfire|sealed=1|near=1',
    'SC|spell|offered=1|sealed=1|cooldown=1',
    'SC|firebolt|sealed=1|onfire=1',
    'SC|helper|sealed=1|by=1',
    'SC|doctor|sealed=1|poultice=1|healed=1|slowblood=1',
    'SC|doctor_torch|sealed=1|burns=1',
    'SC|poultice|sealed=1|healed=1|kept_bandage=1|slowblood=1',
    'SC|restore|regrown=1|gone=1|nobleed=1',
    'SC|brew|elixir=1|healing=1',
    'SC|wound|stops=1|refill=1',
    'SC|fester|festers=1|warn=1|cleared=1',
    'SC|craft|leather=2|silk=2|holds=65,80|torches=2|menu=1',
    'SC|hud|row=Right leg: stump, bleeding: needs fire or a bandage|acts=torch,bandage|warn=1|cmd=bandaged',
    'SC|save|same=1|bandage=1|oldsave=healed|nobleed=1',
    'SC|vampire|cut=1|nobleed=1|nodrip=1|nodrain=1|alive=1|nostump=1|limb_red=1|human_bleeds=1',
    'SC|gargoyle|stone_limb=1|no_blood=1|no_bleed=1|no_stump=1|no_brew_blood=1|no_stone_no_mend=1|graft_needs_stone=1|hud=Stone limbs: Right leg broken off: rebuilt only with stone (2)|mended=1|rebuilt=1|stones_used=3',
    'SC|gargoyle_doctor|rebuilt=1|stones_taken=2',
    'SC|heal|awake_none=1|meal=20|bed=20|rough=10|poultice=80|arm_set=1',
    'SC|complete',
]


def expected():
    only = [x for x in os.environ.get('SC_ONLY', '').split(',') if x]
    if 'spell' in only: only.append('firebolt')
    if 'gargoyle' in only: only.append('gargoyle_doctor')
    return [e for e in EXPECTED if not only or e == 'SC|complete' or e.split('|')[1] in only]


def main():
    args = check_engine.parse(__doc__)
    RUNTIME = check_engine.runtime(args)
    want = expected()
    label = args.label or 'stumps'   # --label: its own arena, logs and results, so two runs at once never share them
    arena = ROOT/f'tests/{label}-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(CHECK_GAME, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'players', 'units', 'backup'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'stumps.dme').write_text(dme + '\n#include "stumps_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + check_engine.world_new('StumpRun', args) + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/stumps_test.dm', arena/'stumps_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/f'tests/{label}-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(check_engine.COMPILER), str(arena/'stumps.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/f'tests/{label}-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-stumps-') as data, server_log.open('w') as out:
        t_world = None
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"stumps.json"}', '--cvar', f'opendream.topic_port={check_engine.free_port("tcp")}',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={check_engine.free_port("udp")}', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline and server.poll() is None:
            if 'SC|complete' in server_log.read_text(errors='replace'): break
            t_world = check_engine.mark(server_log, t_world)
            time.sleep(.5)
        t_end = time.monotonic()
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'SC\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    clock, clock_line = check_engine.report(text, args, t_world, t_end)
    result = dict(passed=actual == want and not errors, only=os.environ.get('SC_ONLY', ''), expected=want, actual=actual, errors=errors, clock=clock)
    (ROOT/f'tests/{label}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(want + [''] * (len(actual) - len(want)), actual + [''] * (len(want) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:8]))
    print(clock_line)
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
