#!/usr/bin/env python3
"""Private recursive melee lifetime regression; actual Attack and Death with targeted hit selection."""
import argparse, hashlib, json, re, shutil, sys, tempfile, zipfile
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE
sys.path.insert(0, str(ROOT / 'tools'))
import check_combat as core

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label', required=True)
    p.add_argument('--candidate', action='store_true', help='Compatibility flag; current game is the default')
    p.add_argument('--baseline', type=Path)
    p.add_argument('--port', type=int, default=12245)
    a = p.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+', a.label): p.error('simple label required')
    if list((STAGE / 'tests').glob(a.label + '-checks.json')): p.error('evidence exists; choose a new label')
    source = a.baseline or STAGE / 'game'
    sources = {str(f.relative_to(source)): sha(f) for f in source.rglob('*.dm')}
    runtime = STAGE / 'runtime' if (STAGE / 'runtime/server').exists() else STAGE.parent / 'replica/runtime/macos-x64'
    artifacts = ['server/Resources/Assemblies/OpenDreamRuntime.dll', 'server/Resources/Assemblies/OpenDreamShared.dll', 'compiler/DMCompiler.dll', 'compiler/DMStandard/_Standard.dm']
    hashes = {n: sha(runtime / n) for n in artifacts}
    fixture_source = STAGE / 'tests/combat_recursion_test.dm'
    fixture_hash = sha(fixture_source)
    core.ROOT, core.RUNTIME = STAGE, runtime
    with tempfile.TemporaryDirectory(prefix='dm-combat-recursion-') as tmp:
        arena = Path(tmp) / 'game'
        shutil.copytree(source, arena)
        # Private deterministic branch selection after the original RNG calls.
        # No Attack/Death/cost/recursion body is replaced; this hook never ships.
        combat = arena / 'Code/Creatures/Combats.dm'
        combat_text = combat.read_text(encoding='latin-1')
        anchor = '\t\t\tsrc.HitThroat = prob(4)\n'
        if combat_text.count(anchor) != 1: raise RuntimeError('Head selection structure changed')
        combat.write_text(combat_text.replace(anchor, anchor + '\t\t\tsrc.RecursionHeadChoice()\n'), encoding='latin-1')
        w = arena / 'Code/World.dm'
        s = w.read_text(encoding='latin-1')
        start = s.index('\tNew()'); end = s.index('\nvar/Season', start)
        w.write_text(s[:start] + '\tNew()\n\t\tspawn(0) RecursiveCombatRun()\n' + s[end:], encoding='latin-1')
        shutil.copy2(fixture_source, arena / fixture_source.name)
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        fixture = arena / 'recursion.dme'
        fixture.write_text(dme + '\n#include "combat_recursion_test.dm"\n', encoding='latin-1')
        with zipfile.ZipFile(STAGE / 'tests' / (a.label + '-source.zip'), 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for f in arena.rglob('*.dm'): z.write(f, f.relative_to(arena))
            z.write(fixture, fixture.name)
        passed = core.run_world(arena, fixture, a.label, 100, prefix='RECURSION', port=a.port)
    report_path = STAGE / 'tests' / (a.label + '-checks.json')
    report = json.loads(report_path.read_text())
    report.update(source_sha256=sources, runtime_sha256_before=hashes,
        runtime_stable=hashes == {n: sha(runtime / n) for n in artifacts},
        source_stable=sources == {str(f.relative_to(source)): sha(f) for f in source.rglob('*.dm')},
        fixture_sha256=fixture_hash, fixture_stable=fixture_hash == sha(fixture_source),
        runner_sha256=sha(Path(__file__)),
        scope='Private isolated grass arena. Original Human/Orc/Dragon victim constructors and Orc attacker constructor. Test attacker overrides only DamageType and hit selection, plus one private hook after original head-location RNG rolls to select Brain, to exercise actual recursive Attack, original injury/Death/MakeBody and inventory/roster effects. Deterministic damage and injury flags are disclosed fixture injections, not natural combat balance. No override of Attack, Death or deletion. No native client/profile/app/saves.',
        test_only_instrumentation='After the sole src.HitThroat = prob(4), invoke src.RecursionHeadChoice() to choose the nested brain hit. The fixture supplies the method; this line is absent from both production candidate and baseline sources.')
    report['counts'] = {'passed': sum('|PASS|' in x for x in report['observations']), 'failed': sum('|FAIL|' in x for x in report['observations'])}
    report['passed'] = passed and report['runtime_stable'] and report['source_stable'] and report['fixture_stable']
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'counts': report['counts'], 'report': str(report_path)}, indent=2))
    return 0 if report['passed'] else 1

if __name__ == '__main__': raise SystemExit(main())
