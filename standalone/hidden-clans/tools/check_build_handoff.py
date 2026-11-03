#!/usr/bin/env python3
"""Audit real workshop/terrain handoffs; copied prompt delivery, no native UI or user saves."""
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
    parser.add_argument('--port', type=int, default=12179)
    parser.add_argument('--label', default='build-handoff-before')
    parser.add_argument('--game-overlay', type=Path, help='Private candidate files to copy into the disposable game only.')
    parser.add_argument('--terrain', action='store_true', help='Run the additional stone construction and bridge cases.')
    args = parser.parse_args()
    if not 1024 <= args.port <= 52035 or not re.fullmatch(r'[A-Za-z0-9_-]+', args.label):
        parser.error('invalid port or label')
    sources = ['Code/Remastered/QoL.dm', 'Code/Remastered/Orders.dm', 'Code/Remastered/Actions.dm',
               'Code/Remastered/Defense.dm', 'Code/Remastered/Delivery.dm', 'Code/Remastered/Settlement.dm',
               'Code/Items/CraftingStations.dm', 'Code/Building/Building.dm',
               'Code/Building/HUD Building.dm', 'Code/Items/Item Procs.dm', 'Cave Crawlers.dme']
    before = {name: sha(ROOT / 'game' / name) for name in sources}
    installed = check_combat.RUNTIME
    with tempfile.TemporaryDirectory(prefix='dm-build-handoff-') as temporary:
        temporary = Path(temporary)
        # Server assemblies are private so a coordinated runtime installation
        # cannot replace files underneath this audit. Compiler/dotnet are read-only.
        runtime = temporary / 'runtime'
        runtime.mkdir()
        shutil.copytree(installed / 'server', runtime / 'server')
        for component in ('dotnet', 'compiler'):
            (runtime / component).symlink_to(installed / component, target_is_directory=True)
        check_combat.RUNTIME = runtime
        runtime_dll = runtime / 'server/Resources/Assemblies/OpenDreamRuntime.dll'
        private_hash = sha(runtime_dll)
        arena = temporary / 'world'
        shutil.copytree(ROOT / 'game', arena, ignore=shutil.ignore_patterns(
            'Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        copied_hashes = {name: sha(arena / name) for name in sources}
        if args.game_overlay:
            for name in sources:
                candidate = args.game_overlay / name
                if candidate.is_file():
                    shutil.copy2(candidate, arena / name)
        tested_hashes = {name: sha(arena / name) for name in sources}
        dme = (arena / 'Cave Crawlers.dme').read_text(encoding='latin-1')
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
        world = arena / 'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        start = source.index('\tNew()')
        end = source.index('\nvar/Season', start)
        entry = 'BuildTerrainRun' if args.terrain else 'BuildAuditRun'
        world.write_text(source[:start] + f'\tNew()\n\t\tspawn(0) {entry}()\n' + source[end:], encoding='latin-1')
        workshop = arena / 'Code/Items/CraftingStations.dm'
        original = workshop.read_text(encoding='latin-1')
        start = original.index('\n\t\tCarpentry\n')
        match = re.search(r'\n\t\t\w+\n', original[start + 1:])
        end = start + 1 + match.start() if match else len(original)
        section = original[start:end]
        # Preserve every recipe, gate, side effect and option. Only deliver the
        # two list-prompt choices through the existing production prompt adapter.
        old = 'input("What Action Will You Choose?", "Choose", null) in '
        pattern = re.escape(old) + r'(menu2?)(?=\n)'
        section, count = re.subn(pattern, r'usr.RemasterActionChoice("What Action Will You Choose?", "Choose", \1)', section)
        if count != 2 and not (count == 0 and section.count('P.RemasterActionChoice(') == 2):
            raise RuntimeError(f'Carpentry prompt structure changed: expected two input/adapter calls, found {count}')
        section, amount_count = re.subn(r'input\("Amount\?"\)as null\|num', r'usr:BuildAuditAmount()', section)
        if amount_count != 1:
            raise RuntimeError('Carpentry amount prompt changed; review fixture')
        workshop.write_text(original[:start] + section + original[end:], encoding='latin-1')
        wrapper = (arena / 'Code/Remastered/QoL.dm').read_text(encoding='latin-1')
        start = wrapper.index('\tif(istype(mob, /Player) && !mob.Function && istype(m, /mob/WorkShops))')
        end = wrapper.index('\n\tif(', start + 1)
        wrapper_branch = wrapper[start:end]
        if 'RemasterButton(m)' not in wrapper_branch:
            raise RuntimeError('Workshop click dispatch changed; review fixture call sequence')
        eager = 'mob:RemasterLegacyHandoff()' in wrapper_branch
        # Match this workshop's explicit deferred-handoff clause independently
        # of additional migrated workshop families on the same condition.
        if '!istype(m, /mob/WorkShops/Carpentry)' in wrapper_branch:
            eager = False
        shutil.copy2(ROOT / 'tests/build_handoff_audit.dm', arena / 'build_handoff_audit.dm')
        (arena / 'audit_config.dm').write_text(f'var/buildaudit_eager_handoff = {int(eager)}\n')
        fixture = arena / 'build_handoff.dme'
        extra = ''
        if args.terrain:
            shutil.copy2(ROOT / 'tests/terrain_handoff_test.dm', arena / 'terrain_handoff_test.dm')
            extra = '#include "terrain_handoff_test.dm"\n'
        fixture.write_text(dme + '\n#include "audit_config.dm"\n#include "build_handoff_audit.dm"\n' + extra, encoding='latin-1')
        passed = check_combat.run_world(arena, fixture, args.label, 120, prefix='BUILDAUDIT', port=args.port)
        report_path = ROOT / 'tests' / (args.label + '-checks.json')
        report = json.loads(report_path.read_text())
        report.update(source_sha256=tested_hashes, original_source_sha256=copied_hashes, copy_matches_start_hashes=copied_hashes == before,
                      source_changes_during_run=[name for name, digest in copied_hashes.items() if sha(ROOT / 'game' / name) != digest],
                      fixture_sha256=sha(arena / 'build_handoff_audit.dm'),
                      terrain_fixture_sha256=sha(arena / 'terrain_handoff_test.dm') if args.terrain else None,
                      private_runtime_sha256=private_hash, private_runtime_stable=sha(runtime_dll) == private_hash,
                      workshop_prompt_delivery_replacements=count, amount_prompt_delivery_replacements=amount_count,
                      private_candidate_overlay=str(args.game_overlay) if args.game_overlay else None,
                      workshop_adapted_sha256=sha(workshop),
                      workshop_click_source_branch=wrapper_branch,
                      scope=('Real Human/Goblin/Illithid/Sand_Humanoid constructors and original terrain MouseDrag handlers; stone floor/wall and stone/wood bridge success and rejection gates. No prompt or native client input is exercised.' if args.terrain else 'Real Human/Orc constructors, inventory and original Carpentry DblClick/wooden terrain MouseDrag handlers. Original list choices are scripted through the production adapter (or copy-only adapters for pre-migration baselines); one quantity prompt is adapted only in the disposable copy. Single-tap handoff is tested through the actual handoff+workshop procedure sequence verified against source, not a native client click.') + ' Private runtime/server and game; no normal saves.')
        report['passed'] = passed and report['copy_matches_start_hashes'] and report['private_runtime_stable']
        report_path.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
