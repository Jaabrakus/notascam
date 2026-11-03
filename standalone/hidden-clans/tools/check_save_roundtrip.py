#!/usr/bin/env python3
"""Save -> quit -> reload with work in progress: every saved var comes back.

Three boots of one arena (fixture tests/save_roundtrip_test.dm) on the Remastered server runtime
(the shared server with engine/server/OpenDreamRuntime.dll laid over it, as tools/build_app.py does).
Boot 1 settles a small village, lets it work, digests every saved var of the player and its units
(the engine's issaved()) and saves with the game's SaveUnits(). Boot 2 logs in through LoadUnits(),
digests at once, works on and saves again; boot 3 logs in and digests. Each reload must give back
the digest taken at the save, apart from the fields LoadUnits() resets on purpose; nothing may be
left nowhere or doubled on the ground, restored work must resume, and no runtime error may occur.
Private temp folders only: the player's saves are never touched."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent/'replica/runtime/macos-x64'   # used read-only
ERROR = re.compile(r'^.*(?:\[(?:ERRO|FATL)\]|runtime error|Exception occurred).*$', re.I | re.M)
# LoadUnits() (Code/Saves.dm) resets these on purpose; the Player's selection and login flags too.
RESET_ON_LOAD = {'Selected', 'Loaded', 'density', 'CoolDown', 'Sleeping', 'Stunned', 'Fainted', 'HomeLoc', 'Target',
                 'Meditating', 'CanWalk', 'Caged', 'InHole', 'Owner', 'savedx', 'savedy', 'savedz', 'key', 'ckey'}


def boot(arena, dotnet, server, log, port, count):
    with tempfile.TemporaryDirectory(prefix='dm-sr-data-') as data, log.open('a') as out:
        proc = subprocess.Popen([str(dotnet), str(server/'Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"saveroundtrip.json"}', '--cvar', f'opendream.topic_port={port + 13500}',
            '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={port}', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=dict(os.environ, DOTNET_ReadyToRun='0'), stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 420
        while time.monotonic() < deadline and proc.poll() is None:
            if log.read_text(errors='replace').count('SR|complete') >= count:
                break
            time.sleep(.3)
        timed_out = proc.poll() is None and time.monotonic() >= deadline
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                proc.kill()
        return not timed_out


def snapshot(text, tag):
    """Digest lines of one tag -> {'var': {(owner, var): value}, 'inv', 'where', 'ground', 'nowhere', ...}."""
    snap = dict(var={}, inv={}, where={}, ground={}, nowhere={}, other={})
    for line in re.findall(r'SR\|' + re.escape(tag) + r'\|([^\r\n]*)', text):
        kind, _, rest = line.partition('|')
        if kind == 'var':
            owner, var, value = rest.split('|', 2)
            snap['var'][(owner, var)] = value
        elif kind in ('inv', 'where'):
            owner, _, value = rest.partition('|')
            snap[kind][owner] = value
        elif kind in ('ground', 'nowhere'):
            key, _, n = rest.rpartition('|')
            snap[kind][key] = int(n)
        else:
            snap['other'][kind] = rest
    return snap


def compare(before, after):
    changed, missing, expected = [], [], []
    for key, value in before['var'].items():
        if key not in after['var']:
            missing.append('|'.join(key))
        elif after['var'][key] != value:
            row = dict(owner=key[0], var=key[1], saved=value[:300], loaded=after['var'][key][:300])
            (expected if key[1] in RESET_ON_LOAD else changed).append(row)
    added = ['|'.join(k) for k in after['var'] if k not in before['var']]
    inv = {o: [before['inv'][o], after['inv'].get(o)] for o in before['inv'] if after['inv'].get(o) != before['inv'][o]}
    where = {o: [before['where'][o], after['where'].get(o)] for o in before['where'] if after['where'].get(o) != before['where'][o]}
    ground = {k: [before['ground'].get(k, 0), after['ground'].get(k, 0)] for k in set(before['ground']) | set(after['ground'])
              if before['ground'].get(k, 0) != after['ground'].get(k, 0)}
    nowhere_grew = {k: [before['nowhere'].get(k, 0), n] for k, n in after['nowhere'].items() if n > before['nowhere'].get(k, 0)}
    return dict(changed=changed, missing=missing, added=added, reset_by_loadunits=expected, inventory=inv,
                where=where, ground=ground, nowhere_grew=nowhere_grew)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, default=ROOT/'game')
    parser.add_argument('--label', default='save-roundtrip')
    parser.add_argument('--port', type=int, default=12471)
    args = parser.parse_args()
    tests = ROOT/'tests'
    with tempfile.TemporaryDirectory(prefix='dm-sr-') as temp:
        temp = Path(temp)
        server = temp/'server'
        shutil.copytree(SHARED/'server', server)
        shutil.copy2(ROOT/'engine/server/OpenDreamRuntime.dll', server/'Resources/Assemblies/OpenDreamRuntime.dll')
        arena = temp/'arena'
        shutil.copytree(args.game, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players'))
        (arena/'units').mkdir()
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        (arena/'saveroundtrip.dme').write_text(dme + '\n#include "save_roundtrip_test.dm"\n', encoding='latin-1')
        world = arena/'Code/World.dm'
        text = world.read_text(encoding='latin-1')
        start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
        world.write_text(text[:start] + '\tNew()\n\t\tSrMap()\n\t\tspawn(0) SrRun()\n' + text[end:], encoding='latin-1')
        saves = arena/'Code/Saves.dm'   # LoadUnits() without a connected client
        source = saves.read_text(encoding='latin-1')
        assert source.count('\tclient.images = null') == 1
        saves.write_text(source.replace('\tclient.images = null', '\tif(client) client.images = null'), encoding='latin-1')
        shutil.copy2(tests/'save_roundtrip_test.dm', arena/'save_roundtrip_test.dm')
        dotnet = SHARED/'dotnet/dotnet'
        compile_log = tests/f'{args.label}-compile.log'
        with compile_log.open('w') as out:
            subprocess.run([str(dotnet), str(SHARED/'compiler/DMCompiler.dll'), str(arena/'saveroundtrip.dme')],
                           env=dict(os.environ, DOTNET_ReadyToRun='0'), stdout=out, stderr=subprocess.STDOUT, check=True)
        log = tests/f'{args.label}-server.log'
        log.write_text('')
        finished = [boot(arena, dotnet, server, log, args.port, n) for n in (1, 2, 3)]
        errorlog = arena/'ErrorLog.txt'
        world_log = errorlog.read_text(errors='replace') if errorlog.exists() else ''
        (tests/f'{args.label}-world.log').write_text(world_log)
    text = log.read_text(errors='replace') + '\n' + world_log
    errors = ERROR.findall(text)
    pre, post, pre2, post2 = (snapshot(text, t) for t in ('pre', 'post', 'pre2', 'post2'))
    first, second = compare(pre, post), compare(pre2, post2)
    def clean(c):
        return not (c['changed'] or c['missing'] or c['added'] or c['inventory'] or c['where'] or c['ground'] or c['nowhere_grew'])
    def num(snap, key, field):
        m = re.search(field + r'=(\d+)', snap['other'].get(key, ''))
        return int(m.group(1)) if m else None
    built_pre = (num(pre, 'terrain', 'walls') or 0) + (num(pre, 'terrain', 'floors') or 0)
    built_pre2 = (num(pre2, 'terrain', 'walls') or 0) + (num(pre2, 'terrain', 'floors') or 0)
    checks = {
        'three_boots_finished': all(finished),
        'issaved_works': len(pre['var']) > 100 and not any(v == 'remaster_board_clock' for _, v in pre['var']),
        'logged_in_twice': 'post|load=1' in text and 'post2|load=1' in text,
        'first_reload_restores_saved_vars': not first['changed'] and not first['missing'] and not first['added'],
        'second_reload_restores_saved_vars': not second['changed'] and not second['missing'] and not second['added'],
        'inventories_and_places_kept': not (first['inventory'] or first['where'] or second['inventory'] or second['where']),
        'ground_census_kept': not first['ground'] and not second['ground'],
        'nothing_left_nowhere': not first['nowhere_grew'] and not second['nowhere_grew'],
        'work_resumes_after_reload': built_pre2 > built_pre or (num(pre, 'progress', 'blueprints') or 0) > (num(pre2, 'progress', 'blueprints') or 0),
        'chopped_trees_stay_chopped': num(post, 'terrain', 'trees') == num(pre, 'terrain', 'trees') and num(post2, 'terrain', 'trees') == num(pre2, 'terrain', 'trees'),
        'no_runtime_errors': not errors,
    }
    result = dict(passed=all(checks.values()), checks=checks, first_reload=first, second_reload=second,
                  progress={t: s['other'].get('progress') for t, s in (('pre', pre), ('post', post), ('pre2', pre2), ('post2', post2))},
                  terrain={t: s['other'].get('terrain') for t, s in (('pre', pre), ('post', post), ('pre2', pre2), ('post2', post2))},
                  saved_vars=len(pre['var']), errors=errors[:20],
                  setup=re.findall(r'SR\|(?:planned|axes|zone|issaved)[^\r\n]*', text))
    (tests/f'{args.label}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for k, v in checks.items():
        print('  ' if v else '!!', k)
    for name, c in (('first reload', first), ('second reload', second)):
        if not clean(c):
            print(name + ':', json.dumps({k: v for k, v in c.items() if v and k != 'reset_by_loadunits'})[:3000])
    if errors:
        print('errors:', *errors[:10], sep='\n  ')
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
