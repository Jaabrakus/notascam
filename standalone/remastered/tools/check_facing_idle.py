#!/usr/bin/env python3
"""Check real constructed units hold their game-side facing while idle."""
import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from check_combat import ROOT, RUNTIME, run_world


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12164)
    args = parser.parse_args()
    if not 1024 <= args.port <= 52035:
        parser.error('port must be 1024..52035')
    with tempfile.TemporaryDirectory(prefix='dm-facing-idle-') as temp:
        arena = Path(temp) / 'world'
        shutil.copytree(ROOT / 'game', arena, ignore=shutil.ignore_patterns(
            'Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        dme = (arena / 'Cave Crawlers.dme').read_text(encoding='latin-1')
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
        world = arena / 'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        start = source.index('\tNew()')
        end = source.index('\nvar/Season', start)
        world.write_text(source[:start] + '\tNew()\n\t\tspawn(0) FacingRun()\n' + source[end:],
                         encoding='latin-1')
        shutil.copy2(ROOT / 'tests/facing_idle_test.dm', arena / 'facing_idle_test.dm')
        fixture = arena / 'facing_idle.dme'
        fixture.write_text(dme + '\n#include "facing_idle_test.dm"\n', encoding='latin-1')
        runtime_assembly = RUNTIME / 'server/Resources/Assemblies/OpenDreamRuntime.dll'
        runtime_before = hashlib.sha256(runtime_assembly.read_bytes()).hexdigest()
        report_path = ROOT / 'tests/facing-idle-checks.json'
        report_path.write_text(json.dumps({'phase': 'before_run',
            'runtime_sha256_before_run': runtime_before}, indent=2) + '\n')
        passed = run_world(arena, fixture, 'facing-idle', 90, prefix='FACING', port=args.port)
        report = json.loads(report_path.read_text())
        report['runtime_sha256_before_run'] = runtime_before
        report['runtime_file_stable_across_run'] = runtime_before == report['runtime_sha256']
        report['runtime_hash_note'] = (
            'Runtime hashes were sampled before compilation/server launch and after completion. '
            'A mismatch means the loaded assembly hash is unverified.')
        report_path.write_text(json.dumps(report, indent=2) + '\n')
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
