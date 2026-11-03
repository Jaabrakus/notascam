#!/usr/bin/env python3
"""Fire in a crowd (Code/Remastered/Vapours.dm, fixture tests/fire_crowd_test.dm): one burning person does not set
the people round it alight, the burning person is not re-burned every second, and fire still runs along wood."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

from check_combat import ROOT, run_world

EXPECTED = ['FC|crowd|others_alight=0|first_alight=1|first_alive=1', 'FC|wood|spread=1', 'FC|complete|failures=0']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12505)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dm-fire-crowd-') as temp:
        arena = Path(temp)/'world'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        world = arena/'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        start = source.index('\tNew()'); end = source.index('\nvar/Season', start)
        world.write_text(source[:start] + '\tNew()\n\t\tspawn(0) FcRun()\n' + source[end:], encoding='latin-1')
        shutil.copy2(ROOT/'tests/fire_crowd_test.dm', arena/'fire_crowd_test.dm')
        fixture = arena/'fire_crowd.dme'
        fixture.write_text(dme + '\n#include "fire_crowd_test.dm"\n', encoding='latin-1')
        run_world(arena, fixture, 'fire-crowd', 120, prefix='FC', port=args.port)
    result = json.loads((ROOT/'tests/fire-crowd-checks.json').read_text())
    actual = result['observations']
    result['expected'] = EXPECTED
    result['passed'] = actual == EXPECTED and not result['errors'] and not result['timed_out']
    (ROOT/'tests/fire-crowd-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print('  ' if e == a else '!!', a, '' if e == a else f'   (expected {e})')
    print('passed' if result['passed'] else 'FAILED')
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
