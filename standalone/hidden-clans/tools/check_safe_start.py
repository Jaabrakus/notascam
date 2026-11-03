#!/usr/bin/env python3
"""A new start never lands beside hostile creatures (Code/Remastered/SafeStart.dm, fixture tests/safe_start_test.dm)."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

from check_combat import ROOT, run_world

EXPECTED = [
    'SS|undead|safe=1|together=1|open=1|moved=1|trees=1',
    'SS|clear|safe=1|together=1|open=1|moved=0|trees=1',
    'SS|kin|safe=1|together=1|open=1|moved=0|trees=1',
    'SS|bare|safe=1|together=1|open=1|moved=1|trees=1',
    'SS|grace|ignored=1|after_attack_order=1',
    'SS|swamp|moved=1|out=1|trees=1',
    'SS|roof|moved=1|under_rock=0',
    'SS|migrants|stayed=1',
    'SS|room|three_logs=1',
    'SS|complete|failures=0',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12477)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dm-safe-start-') as temp:
        arena = Path(temp)/'world'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        world = arena/'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        start = source.index('\tNew()'); end = source.index('\nvar/Season', start)
        world.write_text(source[:start] + '\tNew()\n\t\tspawn(0) SsRun()\n' + source[end:], encoding='latin-1')
        shutil.copy2(ROOT/'tests/safe_start_test.dm', arena/'safe_start_test.dm')
        fixture = arena/'safe_start.dme'
        fixture.write_text(dme + '\n#include "safe_start_test.dm"\n', encoding='latin-1')
        run_world(arena, fixture, 'safe-start', 120, prefix='SS', port=args.port)
    result = json.loads((ROOT/'tests/safe-start-checks.json').read_text())
    actual = result['observations']
    result['expected'] = EXPECTED
    result['passed'] = actual == EXPECTED and not result['errors'] and not result['timed_out']
    (ROOT/'tests/safe-start-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print('  ' if e == a else '!!', a, '' if e == a else f'   (expected {e})')
    print('passed' if result['passed'] else 'FAILED')
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
