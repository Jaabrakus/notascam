#!/usr/bin/env python3
"""Exercise original Masonary recipes and commit-only order handoff in a private world."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

import check_combat

ROOT = check_combat.ROOT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12200)
    parser.add_argument('--label', default='masonary-handoff')
    parser.add_argument('--game-overlay', type=Path)
    args = parser.parse_args()
    if not 1024 <= args.port <= 52035 or not re.fullmatch(r'[A-Za-z0-9_-]+', args.label):
        parser.error('invalid port or label')
    names = ['Code/Items/CraftingStations.dm', 'Code/Remastered/QoL.dm',
             'Code/Remastered/Orders.dm', 'Code/Remastered/Defense.dm',
             'Code/Remastered/Delivery.dm', 'Code/Remastered/Settlement.dm',
             'Code/Items/Item Procs.dm', 'Code/Creatures/Death.dm', 'Cave Crawlers.dme']
    before = {name: sha(ROOT / 'game' / name) for name in names}
    installed = check_combat.RUNTIME
    with tempfile.TemporaryDirectory(prefix='dm-masonary-handoff-') as temporary:
        temporary = Path(temporary)
        runtime = temporary / 'runtime'
        runtime.mkdir()
        shutil.copytree(installed / 'server', runtime / 'server')
        for component in ('dotnet', 'compiler'):
            (runtime / component).symlink_to(installed / component, target_is_directory=True)
        check_combat.RUNTIME = runtime
        runtime_dll = runtime / 'server/Resources/Assemblies/OpenDreamRuntime.dll'
        runtime_hash = sha(runtime_dll)
        arena = temporary / 'world'
        shutil.copytree(ROOT / 'game', arena, ignore=shutil.ignore_patterns(
            'Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        copied = {name: sha(arena / name) for name in names}
        if args.game_overlay:
            for name in names:
                candidate = args.game_overlay / name
                if candidate.is_file():
                    shutil.copy2(candidate, arena / name)
        tested = {name: sha(arena / name) for name in names}
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        world = arena / 'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        start = source.index('\tNew()')
        end = source.index('\nvar/Season', start)
        world.write_text(source[:start] + '\tNew()\n\t\tspawn(0) MasonAuditRun()\n' + source[end:], encoding='latin-1')
        workshop = arena / 'Code/Items/CraftingStations.dm'
        original = workshop.read_text(encoding='latin-1')
        start = original.index('\n\t\tMasonary\n')
        end = original.index('\n\t\tBoneCraft\n', start)
        section = original[start:end]
        section, count = re.subn(r'input\("What Action Will You Choose\?", "Choose", null\) in (menu2?)(?=\n)',
                                 r'usr.RemasterActionChoice("What Action Will You Choose?", "Choose", \1)', section)
        if count != 2 and not (count == 0 and section.count('P.RemasterActionChoice(') == 2):
            raise RuntimeError('Masonary prompt structure changed')
        workshop.write_text(original[:start] + section + original[end:], encoding='latin-1')
        wrapper = (arena / 'Code/Remastered/QoL.dm').read_text(encoding='latin-1')
        start = wrapper.index('\tif(istype(mob, /Player) && !mob.Function && istype(m, /mob/WorkShops))')
        end = wrapper.index('\n\tif(', start + 1)
        branch = wrapper[start:end]
        assert 'RemasterButton(m)' in branch
        eager = '/mob/WorkShops/Masonary' not in branch
        fixture_names = ['build_handoff_audit.dm', 'masonary_handoff_test.dm']
        for name in fixture_names:
            shutil.copy2(ROOT / 'tests' / name, arena / name)
        (arena / 'audit_config.dm').write_text(f'var/buildaudit_eager_handoff = {int(eager)}\n')
        fixture = arena / 'masonary_handoff.dme'
        fixture.write_text(dme + '\n#include "audit_config.dm"\n' + ''.join(f'#include "{name}"\n' for name in fixture_names), encoding='latin-1')
        passed = check_combat.run_world(arena, fixture, args.label, 180, prefix='BUILDAUDIT', port=args.port)
        path = ROOT / 'tests' / (args.label + '-checks.json')
        report = json.loads(path.read_text())
        report.update(source_sha256=tested, original_source_sha256=copied,
                      copy_matches_start_hashes=copied == before,
                      canonical_changes_during_run=[n for n, h in copied.items() if sha(ROOT / 'game' / n) != h],
                      fixture_sha256={n: sha(arena / n) for n in fixture_names},
                      fixture_files_stable=all(sha(arena / n) == sha(ROOT / 'tests' / n) for n in fixture_names),
                      private_runtime_sha256=runtime_hash, private_runtime_stable=sha(runtime_dll) == runtime_hash,
                      list_prompt_delivery_replacements=count, workshop_click_branch=branch,
                      scope='Original Human constructors, actual inventory and Masonary DblClick recipes. Isolated high-capacity actors have deterministic crafting skills; no combat is tested. Two modal list replies are scripted, including yield-time actor mutations. Single-tap dispatch follows the captured production wrapper branch, not native pointer input. Private source/runtime; normal saves untouched.')
        report['passed'] = passed and report['copy_matches_start_hashes'] and report['fixture_files_stable'] and report['private_runtime_stable']
        path.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'passed': report['passed'], 'checks': sum('|PASS|' in v or '|FAIL|' in v for v in report.get('observations', []))}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
