#!/usr/bin/env python3
"""Original Poison Bolt defense regression; no native client."""
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
    p.add_argument('--port', type=int, default=12272)
    p.add_argument('--runtime', type=Path)
    a = p.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+', a.label): p.error('simple label required')
    if list((STAGE / 'tests').glob(a.label + '-checks.json')): p.error('evidence exists; choose a new label')
    source = a.baseline or STAGE / 'game'
    sources = {str(f.relative_to(source)): sha(f) for f in source.rglob('*.dm')}
    runtime = a.runtime or (STAGE / 'runtime' if (STAGE / 'runtime/server').exists() else STAGE.parent / 'replica/runtime/macos-x64')
    artifacts = ['server/Resources/Assemblies/OpenDreamRuntime.dll', 'server/Resources/Assemblies/OpenDreamShared.dll', 'compiler/DMCompiler.dll', 'compiler/DMStandard/_Standard.dm']
    hashes = {n: sha(runtime / n) for n in artifacts}
    fixture_source = STAGE / 'tests/projectile_defense_test.dm'
    fixture_hash = sha(fixture_source)
    core.ROOT, core.RUNTIME = STAGE, runtime
    with tempfile.TemporaryDirectory(prefix='dm-dragon-defense-') as tmp:
        arena = Path(tmp) / 'game'
        shutil.copytree(source, arena)
        w = arena / 'Code/World.dm'
        s = w.read_text(encoding='latin-1')
        start = s.index('\tNew()'); end = s.index('\nvar/Season', start)
        w.write_text(s[:start] + '\tNew()\n\t\tspawn(0) ProjectileRun()\n' + s[end:], encoding='latin-1')
        shutil.copy2(fixture_source, arena / fixture_source.name)
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        fixture = arena / 'dragon.dme'
        fixture.write_text(dme + '\n#include "projectile_defense_test.dm"\n', encoding='latin-1')
        with zipfile.ZipFile(STAGE / 'tests' / (a.label + '-source.zip'), 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for f in arena.rglob('*.dm'): z.write(f, f.relative_to(arena))
            z.write(fixture, fixture.name)
        passed = core.run_world(arena, fixture, a.label, 100, prefix='DRAGON', port=a.port)
    report_path = STAGE / 'tests' / (a.label + '-checks.json')
    report = json.loads(report_path.read_text())
    report.update(source_sha256=sources, runtime_sha256_before=hashes,
        runtime_stable=hashes == {n: sha(runtime / n) for n in artifacts},
        source_stable=sources == {str(f.relative_to(source)): sha(f) for f in source.rglob('*.dm')},
        fixture_sha256=fixture_hash, fixture_stable=fixture_hash == sha(fixture_source),
        runner_sha256=sha(Path(__file__)),
        scope='Isolated grass arena; original Gargoyle, Human and Orc constructors. Earned GargEmerald15 unlock prerequisite is fixture setup, not a claim of playing15gem meals. Original Interact menu with scripted offered replies, actual magic-target assignment, original damage/cooldown. Explicit invalid range/flying/off/friendly and helper controls. No native input, full-map startup, normal profiles or saves.')
    report['counts'] = {'passed': sum('|PASS|' in x for x in report['observations']), 'failed': sum('|FAIL|' in x for x in report['observations'])}
    report['passed'] = passed and report['runtime_stable'] and report['source_stable'] and report['fixture_stable']
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'counts': report['counts'], 'report': str(report_path)}, indent=2))
    return 0 if report['passed'] else 1

if __name__ == '__main__': raise SystemExit(main())
