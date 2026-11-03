#!/usr/bin/env python3
"""The player's own saves with the current code, in a throw-away full-map world (fixture tests/real_save_test.dm).

Copies the .sav files of ~/Library/Application Support/Dungeon Master Remastered/world/units (read only; their hashes
are checked unchanged afterwards) into a temporary world. Boot 1: the world save loads, every player save logs in,
the village plays a minute with the HUD model and 3D scene a client is sent, then every saved var is digested and
the game's SaveUnits() runs. Boot 2: everyone logs in again and is digested. Passes when every save loads with its
units, the reload gives back what was saved (apart from what LoadUnits() resets), the player's files are untouched,
and no runtime error occurs. Never writes to the player's folder."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from check_combat import ROOT, run_world

PLAYER_UNITS = Path.home()/'Library/Application Support/Dungeon Master Remastered/world/units'
RESET_ON_LOAD = {'Selected', 'Loaded', 'density', 'CoolDown', 'Sleeping', 'Stunned', 'Fainted', 'HomeLoc', 'Target',
                 'Meditating', 'CanWalk', 'Caged', 'InHole', 'savedx', 'savedy', 'savedz', 'remaster_seen'}


def digest(text, tag):
    out = {}
    for line in re.findall(r'RS\|' + tag + r'\|var\|([^\r\n]*)', text):
        owner, var, value = line.split('|', 2)
        out[(owner, var)] = value
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12489)
    parser.add_argument('--label', default='real-save')
    args = parser.parse_args()
    files = sorted(p for p in PLAYER_UNITS.glob('*.sav')) if PLAYER_UNITS.exists() else []
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    if not files:
        print('no player saves to test'); raise SystemExit(0)
    with tempfile.TemporaryDirectory(prefix='dm-real-save-') as temp:
        arena = Path(temp)/'world'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        (arena/'units').mkdir()
        for p in files:
            shutil.copy2(p, arena/'units'/p.name)
        world = arena/'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        assert source.count('\t\tCallSave()') == 1
        world.write_text(source.replace('\t\tCallSave()', '\t\tCallSave()\n\t\tspawn() RsRun()'), encoding='latin-1')
        saves = arena/'Code/Saves.dm'   # LoadUnits() without a connected client
        text = saves.read_text(encoding='latin-1')
        assert text.count('\tclient.images = null') == 1
        saves.write_text(text.replace('\tclient.images = null', '\tif(client) client.images = null'), encoding='latin-1')
        shutil.copy2(ROOT/'tests/real_save_test.dm', arena/'real_save_test.dm')
        fixture = arena/'real_save.dme'
        fixture.write_text((arena/'Cave Crawlers.dme').read_text(encoding='latin-1') + '\n#include "real_save_test.dm"\n', encoding='latin-1')
        ok1 = run_world(arena, fixture, args.label + '-1', 1500, prefix='RS', port=args.port)
        ok2 = run_world(arena, fixture, args.label + '-2', 1500, prefix='RS', port=args.port)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    r1 = json.loads((ROOT/f'tests/{args.label}-1-checks.json').read_text())
    r2 = json.loads((ROOT/f'tests/{args.label}-2-checks.json').read_text())
    text = '\n'.join(r1['observations'] + r2['observations'])
    full = (ROOT/f'tests/{args.label}-2-world.log').read_text(errors='replace') + (ROOT/f'tests/{args.label}-1-world.log').read_text(errors='replace')
    pre, post = digest(full, 'pre'), digest(full, 'post')
    in_file = {}   # units in each player's save file (an old save may hold none)
    for p in files:
        if p.name.endswith('_save.sav') and not p.name.startswith('remaster_'):
            nodes = json.loads(p.read_text())['_nodes']
            ref = nodes.get('UnitList') or {}
            table = nodes['.opendream_graph']['Objects']
            in_file[p.name[:-len('_save.sav')]] = len(table[ref['Id']].get('Values', [])) if ref.get('Id') is not None else 0
    changed = [dict(owner=k[0], var=k[1], saved=v[:160], loaded=post.get(k, '<missing>')[:160]) for k, v in pre.items()
               if post.get(k) != v and k[1] not in RESET_ON_LOAD]
    logins = re.findall(r'RS\|(pre|post)\|login\|([^|]*)\|ckey=[^|]*\|loaded=(\d)\|units=(\d+)', text)
    checks = {
        'both_boots_clean': ok1 and ok2,
        'every_save_loads_its_units': bool(logins) and all(l[2] == '1' and int(l[3]) == in_file.get(l[1], -1) for l in logins),
        'reload_gives_back_what_was_saved': bool(pre) and not changed,
        'player_files_untouched': before == after,
    }
    result = dict(passed=all(checks.values()), checks=checks, logins=logins, units_in_files=in_file, saved_vars=len(pre), changed=changed[:40],
                  players=re.findall(r'RS\|(?:pre|post)\|player\|[^\r\n]*', full), errors=(r1['errors'] + r2['errors'])[:20])
    (ROOT/f'tests/{args.label}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for line in result['players'] + [f'login {l}' for l in logins]:
        print('  ', line)
    for k, v in checks.items():
        print('  ' if v else '!!', k)
    if changed:
        print('changed on reload:', json.dumps(changed[:10])[:2000])
    print('passed' if result['passed'] else 'FAILED')
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
