#!/usr/bin/env python3
"""Combat pace in a bounded arena (tests/pace_test.dm): 8 pairs of humans per matchup (iron swords, swords in full
metal armour, bare fists) fight through the game's own attack orders. Prints, per matchup, when the first blow lands,
when the first limb comes off and when the fight ends (seconds: median and range), how fights end, swings per fight
and limbs lost; writes tests/pace-checks.json. A measuring tool, not a pass/fail check.
  python3 tools/check_pace.py            PC_ONLY=sword,fists python3 tools/check_pace.py
"""
import json, os, re, shutil, statistics, subprocess, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT.parent/'replica/runtime/macos-x64'   # shared engine, used read-only


def main():
    tag = os.environ.get('PC_TAG', '')   # another run beside this one: its own arena, logs and ports
    arena = ROOT/f'tests/pace{tag}-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'players', 'units', 'backup'))
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
    (arena/'pace.dme').write_text(dme + '\n#include "pace_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    a = text.index('\tNew()'); b = text.index('\nvar/Season', a)
    world.write_text(text[:a] + '\tNew()\n\t\tspawn(0) PcRun()\n' + text[b:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/pace_test.dm', arena/'pace_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    with (ROOT/f'tests/pace{tag}-compile.log').open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'pace.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    log = ROOT/f'tests/pace{tag}-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-pace-') as data, log.open('w') as out:
        server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"pace.json"}', '--cvar', f'opendream.topic_port={25949 + (2 if tag else 0)}', '--cvar', f'log.path={ROOT/"tests/engine-logs"}',
            '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={12449 + (2 if tag else 0)}', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false',
            '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 1500
        while time.monotonic() < deadline and server.poll() is None:
            if 'PC|complete' in log.read_text(errors='replace'): break
            time.sleep(1)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = log.read_text(errors='replace')
    fights = {}
    for m in re.finditer(r'PC\|fight\|(\w+)\|first=([^|]+)\|limb=([^|]+)\|end=([^|]+)\|how=(\w+)\|swings=(\d+)\|limbs_lost=(\d+)', text):
        kit, first, limb, end, how, swings, lost = m.groups()
        num = lambda v: None if v == '-' else float(v)
        fights.setdefault(kit, []).append(dict(first=num(first), limb=num(limb), end=num(end), how=how, swings=int(swings), lost=int(lost)))
    def spread(xs):
        xs = [x for x in xs if x is not None]
        return f'{statistics.median(xs):.0f} s ({min(xs):.0f}-{max(xs):.0f})' if xs else '-'
    summary = {}
    for kit, F in fights.items():
        hows = {h: sum(1 for f in F if f['how'] == h) for h in sorted({f['how'] for f in F})}
        summary[kit] = dict(fights=len(F), first_blow=spread([f['first'] for f in F]), first_limb=spread([f['limb'] for f in F]),
            limb_in=f"{sum(1 for f in F if f['limb'] is not None)}/{len(F)}", end=spread([f['end'] for f in F]), ends=hows,
            swings=spread([f['swings'] for f in F]).replace(' s', ''), limbs_lost=sum(f['lost'] for f in F))
        print(kit, json.dumps(summary[kit]))
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text)
    (ROOT/f'tests/pace{tag}-checks.json').write_text(json.dumps(dict(summary=summary, fights=fights, errors=errors[:10]), indent=2) + '\n')
    if errors: print('errors:', errors[:3])


if __name__ == '__main__':
    main()
