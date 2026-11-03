#!/usr/bin/env python3
"""Units, workshops, rune pieces and ground items across saves and logins.

Three boots of one arena on the packaged Remastered runtime: boot 1 builds each
case and calls the game's own SaveUnits(); boots 2 and 3 log the player in through
the original LoadUnits(), and boot 2 saves again. Nothing may be lost or doubled.
The only source change in the arena copy lets LoadUnits() run without a connected
client (it clears client.images)."""
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
APP_RUNTIME = ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
COMPILER = ROOT.parent/'replica/runtime/macos-x64/compiler/DMCompiler.dll'   # shared, used read-only


def run(arena, dotnet, server_dir, log, needle, boot):
    with tempfile.TemporaryDirectory(prefix='dm-unitsave-') as data, log.open('a') as out:
        server = subprocess.Popen([str(dotnet), str(server_dir/'Robust.Server.dll'), '--data-dir', data,
            '--cvar', f'opendream.json_path={arena/"unitsave.json"}', '--cvar', 'opendream.topic_port=25787',
            '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12287', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=dict(os.environ, DOTNET_ReadyToRun='0'), stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline and server.poll() is None:
            if log.read_text(errors='replace').count(needle) >= boot: break
            time.sleep(.2)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()


def rows(text, tag):
    return [line.split('|', 2)[2] for line in re.findall(r'US\|' + tag + r'\|[^\r\n]*', text)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, default=ROOT/'game', help='Game source to test (default: the current source).')
    args = parser.parse_args()
    tests = ROOT/'tests'
    with tempfile.TemporaryDirectory(prefix='dm-unitsave-arena-') as temp:
        arena = Path(temp)/'arena'
        shutil.copytree(args.game, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players'))
        (arena/'units').mkdir()
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        (arena/'unitsave.dme').write_text(dme + '\n#include "unit_save_test.dm"\n', encoding='latin-1')
        world = arena/'Code/World.dm'
        text = world.read_text(encoding='latin-1')
        start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
        # UsMap() runs inside world/New, before the world save loads, like map content.
        world.write_text(text[:start] + '\tNew()\n\t\tUsMap()\n\t\tspawn(0) UsRun()\n' + text[end:], encoding='latin-1')
        saves = arena/'Code/Saves.dm'
        source = saves.read_text(encoding='latin-1')
        assert source.count('\tclient.images = null') == 1
        saves.write_text(source.replace('\tclient.images = null', '\tif(client) client.images = null'), encoding='latin-1')
        shutil.copy2(tests/'unit_save_test.dm', arena/'unit_save_test.dm')
        dotnet = APP_RUNTIME/'dotnet/dotnet'
        with (tests/'unit-save-compile.log').open('w') as out:
            subprocess.run([str(dotnet), str(COMPILER), str(arena/'unitsave.dme')], env=dict(os.environ, DOTNET_ReadyToRun='0'),
                           stdout=out, stderr=subprocess.STDOUT, check=True)
        log = tests/'unit-save-server.log'
        log.write_text('')
        for boot in (1, 2, 3):
            run(arena, dotnet, APP_RUNTIME/'server', log, 'US|complete', boot)
        saved = {}
        sav = arena/'units/alice_save.sav'
        if sav.exists():
            nodes = json.loads(sav.read_text())['_nodes']
            table = nodes['.opendream_graph']['Objects']
            for ref in table[nodes['UnitList']['Id']]['Values']:
                f = table[ref['Id']]['Fields']['_nodes'] if ref and ref.get('Id') is not None else {}
                name = f.get('name', {}).get('Value', {}).get('Value')
                xyz = [f.get(k, {}).get('Value', {}).get('Value') for k in ('savedx', 'savedy', 'savedz')]
                saved[str(name)] = xyz
        errorlog = arena/'ErrorLog.txt'
        world_log = errorlog.read_text(errors='replace') if errorlog.exists() else ''
    text = log.read_text(errors='replace') + world_log
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*|runtime error[^\r\n]*', text)
    def units(tag): return {r.split('|')[1]: r for r in rows(text, tag) if r.startswith('unit|')}
    def census(tag): return {r.rsplit('|', 1)[0]: int(r.rsplit('|', 1)[1]) for r in rows(text, tag) if r.startswith(('item ', 'obj ', 'shop '))}
    def diff(a, b):
        return ({k: [v, b.get(k, 0)] for k, v in a.items() if b.get(k, 0) < v},
                {k: [a.get(k, 0), v] for k, v in b.items() if a.get(k, 0) < v})
    pre, post, again = units('pre'), units('post'), units('again')
    lost1, gained1 = diff(census('pre'), census('post'))
    lost2, gained2 = diff(census('post'), census('again'))
    def place(row): return '|'.join(row.split('|')[2:4]) if row else None
    same = ['U-ok', 'U-z2', 'U-carrier', 'U-carried', 'U-asleep', 'U-builder']
    checks = {
        'units_restored_in_place': all(place(pre.get(n)) and place(pre[n]) == place(post.get(n)) == place(again.get(n)) for n in same),
        'caged_unit_back_on_its_tile': place(post.get('U-caged')) == 'turf|22,10,1',
        'dead_deleted_and_captured_stay_gone': not any(n in post or n in again for n in ('U-died', 'U-deleted', 'U-captured')),
        'no_empty_list_slots': not any(r.startswith('listnull') for r in rows(text, 'post') + rows(text, 'again')),
        'everything_built': all(b.endswith('|1') for b in re.findall(r'US\|built\|([^\r\n]*)', text)),
        'nothing_lost_on_reload': not lost1,
        'nothing_doubled_on_reload': not gained1,
        'second_restart_identical': not lost2 and not gained2,
        'map_things_stay_single': all(sum(v for k, v in census(t).items() if k.endswith(at)) == 1
                                      for t in ('pre', 'post', 'again') for at in ('@60,50,1', '@61,50,1', '@64,50,1')),
        'no_runtime_errors': not errors,
    }
    result = dict(passed=all(checks.values()), checks=checks, units_pre=pre, units_post=post, units_again=again,
                  lost_first_reload=lost1, gained_first_reload=gained1, lost_second_reload=lost2, gained_second_reload=gained2,
                  boot_order=re.findall(r'US\|map\|[^\r\n]*', text), errors=errors[:20])
    (tests/'unit-save-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for k, v in checks.items(): print('  ' if v else '!!', k)
    for label, d in (('lost on reload', lost1), ('doubled on reload', gained1), ('lost on 2nd reload', lost2), ('doubled on 2nd reload', gained2)):
        if d: print(label + ':', json.dumps(d))
    if errors: print('errors:', *errors[:10], sep='\n  ')
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
