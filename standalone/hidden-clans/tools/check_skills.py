#!/usr/bin/env python3
"""Run the Remastered skill layer logic in a bounded arena."""
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
    'SKILLS|first|drops=0',
    'SKILLS|rs|gain=1|kept=1|lvl2=83|lvl50=101333|lvl92=6517253|lvl99=13034431|from83=2|cap=120',
    'SKILLS|gain|xp=1|level=21',
    'SKILLS|direct|1',
    'SKILLS|boost|45',
    'SKILLS|loss|new_drops=0',
    'SKILLS|panel|level=33|progress=40|xp=1|next=1|rs99=1|total=1|tiles=1',
    'SKILLS|minimum|level=1',
    'SKILLS|hud|unique=1|count=1',
    'SKILLS|tool_none|1',
    'SKILLS|tools|gold_low=1|gold_high=1.5|metal=1.25|wooden=1|gold_pick=1.5|warned=1|hud=Gold,1',
    'SKILLS|complete',
]


def main():
    arena = ROOT/'tests/skills-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'skills.dme').write_text(dme + '\n#include "skills_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) SkillsRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/skills_test.dm', arena/'skills_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/'tests/skills-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'skills.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/'tests/skills-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-skills-') as data, server_log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"skills.json"}', '--cvar', 'opendream.topic_port=25601',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12101', '--cvar', 'status.enabled=false',   # not 12151: the app's own port
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline and server.poll() is None:
            if 'SKILLS|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    actual = re.findall(r'SKILLS\|[^\r\n]*', text + (errorlog.read_text(errors='replace') if errorlog.exists() else ''))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    result = dict(passed=actual == EXPECTED and not errors, expected=EXPECTED, actual=actual, errors=errors)
    (ROOT/'tests/skills-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
