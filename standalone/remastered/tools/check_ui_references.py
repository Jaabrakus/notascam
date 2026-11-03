#!/usr/bin/env python3
"""Exercise HUD object-reference lifetime handling in a copied real game, without a native client/save."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from check_combat import ROOT, RUNTIME, run_world


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12174)
    parser.add_argument('--label', default='ui-reference-audit')
    args = parser.parse_args()
    if not 1024 <= args.port <= 52035:
        parser.error('port must be 1024..52035')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.label):
        parser.error('label must contain only letters, digits, underscores, and hyphens')
    sources = ['Code/Remastered/UIIdentity.dm', 'Code/Remastered/Defense.dm', 'Code/Remastered/Orders.dm',
               'Code/Remastered/Delivery.dm', 'Code/Remastered/Settlement.dm',
               'Code/Remastered/QoL.dm', 'Code/Creatures/Combats.dm',
               'Code/Creatures/Combat - Bows.dm', 'Code/Creatures/Monster AI.dm',
               'Code/Vars.dm', 'Code/Remastered/HUD.dm', 'Code/Saves.dm',
               'Code/Click.dm', 'Code/Remastered/Actions.dm', 'Code/Remastered/InventoryActions.dm', 'Code/Remastered/BorderControls.dm', 'Code/Remastered/Palette.dm',
               'Code/Turfs.dm', 'Code/Items/Food.dm', 'Code/Items/Item Procs.dm',
               'Code/Creatures/Interact.dm', 'Code/Login.dm', 'Cave Crawlers.dme']
    before = {name: sha(ROOT / 'game' / name) for name in sources}
    runtime = RUNTIME / 'server/Resources/Assemblies/OpenDreamRuntime.dll'
    runtime_before = sha(runtime)
    with tempfile.TemporaryDirectory(prefix='dm-ui-reference-audit-') as temporary:
        arena = Path(temporary) / 'world'
        shutil.copytree(ROOT / 'game', arena, ignore=shutil.ignore_patterns(
            'Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        dme = (arena / 'Cave Crawlers.dme').read_text(encoding='latin-1')
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
        world = arena / 'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        start = source.index('\tNew()')
        end = source.index('\nvar/Season', start)
        world.write_text(source[:start] + '\tNew()\n\t\tspawn(0) UIReferenceRun()\n' + source[end:], encoding='latin-1')
        shutil.copy2(ROOT / 'tests/ui_reference_audit.dm', arena / 'ui_reference_audit.dm')
        fixture = arena / 'ui_reference_audit.dme'
        fixture.write_text(dme + '\n#include "ui_reference_audit.dm"\n', encoding='latin-1')
        passed = run_world(arena, fixture, args.label, 240, prefix='UIREF', port=args.port)
        report_path = ROOT / 'tests' / (args.label + '-checks.json')
        report = json.loads(report_path.read_text())
        report.update(source_sha256=before, fixture_sha256=sha(arena / 'ui_reference_audit.dm'),
                      fixture_file_stable=sha(arena / 'ui_reference_audit.dm') == sha(ROOT / 'tests/ui_reference_audit.dm'),
                      source_files_stable=all(sha(ROOT / 'game' / name) == digest for name, digest in before.items()),
                      runtime_sha256_before_run=runtime_before,
                      runtime_stable=runtime_before == sha(runtime),
                      scope='Actual engine object/datum deletion and recreation, original Human constructors, real HUD requests, and original potion/sign/tombstone effects. Generic item DblClick has a dispatch marker; special-item choice/text prompts have scripted replies and yield before returning. Post-prompt ownership, selection, cargo, state, and deletion races are exercised. Isolated copied world; no normal save or native input.')
        report['passed'] = passed and report['source_files_stable'] and report['runtime_stable'] and report['fixture_file_stable']
        report_path.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({key: report[key] for key in ('passed', 'source_files_stable', 'runtime_stable')}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
