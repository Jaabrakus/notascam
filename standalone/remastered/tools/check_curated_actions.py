#!/usr/bin/env python3
"""Exercise curated unit actions across yielding text and confirmation prompts in a private copied game."""
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
    parser.add_argument('--controller-only', action='store_true')
    parser.add_argument('--availability-only', action='store_true')
    parser.add_argument('--port', type=int, default=12195)
    parser.add_argument('--game-dir', type=Path, default=ROOT / 'game')
    parser.add_argument('--label', default='curated-actions-audit')
    args = parser.parse_args()
    if not 1024 <= args.port <= 52035:
        parser.error('port must be 1024..52035')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.label):
        parser.error('label must contain only letters, digits, underscores, and hyphens')
    game = args.game_dir.resolve()
    sources = ['Code/Verbs.dm', 'Code/Items/Crowning.dm', 'Code/Remastered/ControlGroups.dm', 'Code/1 - QuickProcs.dm', 'Code/Ownership.dm', 'Code/Mobs.dm', 'Code/Remastered/MagicTarget.dm', 'Code/Admin.dm', 'Code/Remastered/UIIdentity.dm', 'Code/Remastered/Defense.dm', 'Code/Remastered/Orders.dm',
               'Code/Remastered/Delivery.dm', 'Code/Remastered/Settlement.dm',
               'Code/Remastered/QoL.dm', 'Code/Creatures/Combats.dm',
               'Code/Creatures/Combat - Bows.dm', 'Code/Creatures/Monster AI.dm',
               'Code/Vars.dm', 'Code/Remastered/HUD.dm', 'Code/Saves.dm',
               'Code/Click.dm', 'Code/Remastered/Actions.dm', 'Code/Remastered/InventoryActions.dm', 'Code/Remastered/BorderControls.dm', 'Code/Remastered/Palette.dm',
               'Code/Turfs.dm', 'Code/Items/Food.dm', 'Code/Items/Item Procs.dm',
               'Code/Creatures/Interact.dm', 'Code/Login.dm', 'Cave Crawlers.dme']
    candidate = (game / 'Code/Remastered/SelectedActions.dm').exists()
    if (args.availability_only or args.controller_only) and not candidate:
        parser.error('focused scopes require the SelectedActions implementation')
    if candidate: sources.append('Code/Remastered/SelectedActions.dm')
    before = {name: sha(game / name) for name in sources}
    runtime = RUNTIME / 'server/Resources/Assemblies/OpenDreamRuntime.dll'
    runtime_before = sha(runtime)
    with tempfile.TemporaryDirectory(prefix='dm-curated-actions-audit-') as temporary:
        arena = Path(temporary) / 'world'
        shutil.copytree(game, arena, ignore=shutil.ignore_patterns(
            'Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        if not candidate:
            # Replace modal calls only in the private copy. Keep original action
            # bodies/effects unchanged and mutate real selection/ownership on yield.
            actions = arena / 'Code/Remastered/Actions.dm'
            text = actions.read_text(encoding='latin-1')
            for name, message, title in [('unitsay', 'What should your unit say?', 'Speak through a unit'), ('emote', 'What should your unit do?', 'Unit emote')]:
                old = f'input(U, "{message}", "{title}") as text|null'
                assert old in text, name
                text = text.replace(old, f'ActionAuditText(U, "{name}")', 1)
            actions.write_text(text, encoding='latin-1')
            verbs = arena / 'Code/Verbs.dm'
            text = verbs.read_text(encoding='latin-1')
            start = text.index('mob/verb/Rename()')
            end = text.index('mob/verb/Who()', start)
            block, count = re.subn(r'NAME=input[^\n]+ as text\|null', 'NAME=ActionAuditText(usr, "rename")', text[start:end])
            assert count == 2, count
            verbs.write_text(text[:start]+block+text[end:], encoding='latin-1')
            crowning = arena / 'Code/Items/Crowning.dm'
            text = crowning.read_text(encoding='latin-1')
            text, count = re.subn(r'alert\(Owner,[^\n]+?,"(Set|Remove) Leader","Yes","No"\)', lambda m: 'ActionAuditChoice(Owner,src,"'+('leader' if m[1]=='Set' else 'demote')+'")', text)
            assert count == 2, count
            crowning.write_text(text, encoding='latin-1')
        dme = (arena / 'Cave Crawlers.dme').read_text(encoding='latin-1')
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
        world = arena / 'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        start = source.index('\tNew()')
        end = source.index('\nvar/Season', start)
        world.write_text(source[:start] + '\tNew()\n\t\tspawn(0) ActionAuditRun()\n' + source[end:], encoding='latin-1')
        shutil.copy2(ROOT / 'tests/curated_actions_audit.dm', arena / 'curated_actions_audit.dm')
        fixture = arena / 'curated_actions_audit.dme'
        fixture.write_text(('#define REMASTER_ACTION_CONTROLLER_ONLY\n' if args.controller_only else '') + ('#define REMASTER_ACTION_AVAILABILITY_ONLY\n' if args.availability_only else '') + ('#define REMASTER_SELECTED_ACTIONS_TEST\n' if candidate else '') + dme + '\n#include "curated_actions_audit.dm"\n', encoding='latin-1')
        passed = run_world(arena, fixture, args.label, 240, prefix='ACTIONAUDIT', port=args.port)
        report_path = ROOT / 'tests' / (args.label + '-checks.json')
        report = json.loads(report_path.read_text())
        report.update(game_source=str(game), source_sha256=before, fixture_sha256=sha(arena / 'curated_actions_audit.dm'),
                      fixture_file_stable=sha(arena / 'curated_actions_audit.dm') == sha(ROOT / 'tests/curated_actions_audit.dm'),
                      source_files_stable=all(sha(game / name) == digest for name, digest in before.items()),
                      runtime_sha256_before_run=runtime_before,
                      runtime_stable=runtime_before == sha(runtime),
                      scope='Actual HUD curated-action dispatch, real Human constructors and original Rename/UnitSay/Emote/royalty effects. Only modal text/confirmation calls in the private copy use scripted replies and yield-time selection/ownership changes. No native input or normal saves.')
        report['passed'] = passed and report['source_files_stable'] and report['runtime_stable'] and report['fixture_file_stable']
        report_path.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({key: report[key] for key in ('passed', 'source_files_stable', 'runtime_stable')}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
