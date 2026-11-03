#!/usr/bin/env python3
"""Village soak on the full maps: a 20-person village works for 30 game-minutes with the per-player systems a
connected player gets (RemasterTrack, plus the HUD model and 3D scene a client is sent), fixture
tests/village_soak_test.dm. The world soak (check_world_soak.py) has no players, so it never runs these.
Passes with no runtime errors, no deaths of the villagers, and progress on the planned room."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

from check_combat import ROOT, run_world


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12481)
    parser.add_argument('--label', default='village-soak')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dm-village-soak-') as temp:
        arena = Path(temp)/'world'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        (arena/'units').mkdir()
        world = arena/'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        assert source.count('\t\tCallSave()') == 1
        world.write_text(source.replace('\t\tCallSave()', '\t\tCallSave()\n\t\tspawn() VsRun()'), encoding='latin-1')
        shutil.copy2(ROOT/'tests/village_soak_test.dm', arena/'village_soak_test.dm')
        fixture = arena/'village_soak.dme'
        fixture.write_text((arena/'Cave Crawlers.dme').read_text(encoding='latin-1') + '\n#include "village_soak_test.dm"\n', encoding='latin-1')
        passed = run_world(arena, fixture, args.label, 3000, prefix='VSOAK', port=args.port)
    result = json.loads((ROOT/f'tests/{args.label}-checks.json').read_text())
    samples = [o for o in result['observations'] if '|sample|' in o]
    def field(line, name):
        m = re.search(name + r'=(\d+)', line)
        return int(m.group(1)) if m else None
    first, last = (samples[0], samples[-1]) if samples else ('', '')
    checks = {'ran_to_the_end': passed, 'samples': len(samples) >= 25,
              'nobody_died': bool(samples) and field(last, 'alive') >= field(first, 'alive'),   # births add people
              'room_progressed': bool(samples) and (field(last, 'built') or 0) > (field(first, 'built') or 0)}
    result['soak_checks'] = checks
    result['passed'] = all(checks.values())
    (ROOT/f'tests/{args.label}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for line in result['observations']:
        if '|sample|' not in line or line in (first, last) or samples.index(line) % 5 == 0:
            print('  ', line)
    for k, v in checks.items():
        print('  ' if v else '!!', k)
    print('passed' if result['passed'] else 'FAILED')
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
