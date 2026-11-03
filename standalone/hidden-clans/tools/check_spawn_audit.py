#!/usr/bin/env python3
"""Spawn audit on the full maps: 20 starts per race area through Restart()'s own steps (fixture
tests/spawn_audit_test.dm); reports threats near the start, starts with no trees in reach, and how far
SafeStart.dm moved them. A report, not a pass/fail gate: it fails only on errors or no completion."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

from check_combat import ROOT, run_world


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12479)
    parser.add_argument('--label', default='spawn-audit')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dm-spawn-audit-') as temp:
        arena = Path(temp)/'world'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        world = arena/'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        assert source.count('\t\tCallSave()') == 1
        world.write_text(source.replace('\t\tCallSave()', '\t\tCallSave()\n\t\tspawn() SaRun()'), encoding='latin-1')
        shutil.copy2(ROOT/'tests/spawn_audit_test.dm', arena/'spawn_audit_test.dm')
        fixture = arena/'spawn_audit.dme'
        fixture.write_text((arena/'Cave Crawlers.dme').read_text(encoding='latin-1') + '\n#include "spawn_audit_test.dm"\n', encoding='latin-1')
        passed = run_world(arena, fixture, args.label, 900, prefix='SA', port=args.port)
    result = json.loads((ROOT/f'tests/{args.label}-checks.json').read_text())
    for line in result['observations']:
        print('  ', line)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
