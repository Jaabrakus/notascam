#!/usr/bin/env python3
"""Check catalog completeness, reversible border visibility and original effects."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from check_combat import ROOT, RUNTIME, run_world


def main():
    with tempfile.TemporaryDirectory(prefix='dm-border-controls-') as temp:
        arena = Path(temp) / 'world'
        shutil.copytree(ROOT / 'game', arena, ignore=shutil.ignore_patterns(
            'Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        dme = (arena / 'Cave Crawlers.dme').read_text(encoding='latin-1')
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
        world = arena / 'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        start = source.index('\tNew()')
        end = source.index('\nvar/Season', start)
        world.write_text(source[:start] + '\tNew()\n\t\tspawn(0) BorderRun()\n' + source[end:], encoding='latin-1')
        shutil.copy2(ROOT / 'tests/border_controls_test.dm', arena / 'border_controls_test.dm')
        fixture = arena / 'border_controls.dme'
        fixture.write_text(dme + '\n#include "border_controls_test.dm"\n', encoding='latin-1')
        hashes = {str(p.relative_to(arena)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(arena.rglob('*')) if p.is_file() and p.suffix in ('.dm', '.dme', '.html', '.json')}
        (ROOT / 'tests/border-controls-sources.json').write_text(json.dumps(hashes, indent=2) + '\n')
        assembly = RUNTIME / 'server/Resources/Assemblies/OpenDreamRuntime.dll'
        runtime_before = hashlib.sha256(assembly.read_bytes()).hexdigest()
        tracked = ['Code/Remastered/BorderControls.dm', 'Code/Remastered/HUD.dm',
                   'Code/Remastered/Orders.dm', 'Code/Remastered/QoL.dm',
                   'Interface/border-controls.json', 'Cave Crawlers.dme']
        source_before = {name: hashlib.sha256((arena/name).read_bytes()).hexdigest() for name in tracked}
        passed = run_world(arena, fixture, 'border-controls', 50, prefix='BORDER', port=12166)
        report_path = ROOT / 'tests/border-controls-checks.json'
        report = json.loads(report_path.read_text())
        report['runtime_sha256_before_run'] = runtime_before
        report['runtime_file_stable_across_run'] = runtime_before == report['runtime_sha256']
        report['source_sha256'] = source_before
        report['source_files_stable'] = all(hashlib.sha256((ROOT/'game'/name).read_bytes()).hexdigest() == digest for name,digest in source_before.items())
        report['fixture_sha256'] = hashlib.sha256((arena/'border_controls_test.dm').read_bytes()).hexdigest()
        report['fixture_file_stable'] = report['fixture_sha256'] == hashlib.sha256((ROOT/'tests/border_controls_test.dm').read_bytes()).hexdigest()
        report['scope'] = 'Headless real-unit gameplay effects, catalog validation, visibility object state and mode-model gating.'
        report['limitations'] = [
            'No connected native client: original F5/Tab/+/- handlers requiring usr.client.screen were not invoked.',
            'Screen membership uses the existing remaster_screen stand-in; rendering and actual pointer hit-testing are not covered.']
        report['passed'] = passed and report['runtime_file_stable_across_run'] and report['source_files_stable'] and report['fixture_file_stable']
        report_path.write_text(json.dumps(report, indent=2) + '\n')
        raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
