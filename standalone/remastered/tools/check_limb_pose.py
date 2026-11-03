#!/usr/bin/env python3
"""A unit missing a leg keeps showing it (fixture tests/limb_pose_test.dm): the original picture (icon_state from
LimbLoss()), the 3D view's 64 px body and no whole-bodied 3D model, after its overlays are rebuilt, a knock-out and
waking, being taken by another player, a werewolf's night, a half-demon's marks, and becoming a zombie. A kobold."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

from check_combat import ROOT, run_world

LEG = 'state=NoRightLeg|body3d=NoRightLeg|sheet=1|model=-'
EXPECTED = ['LP|whole|state=Normal|body3d=Normal|sheet=1|model=kobold', f'LP|lost|{LEG}', f'LP|overlays|{LEG}',
            f'LP|knocked_out|{LEG}', f'LP|woke|{LEG}', f'LP|taken|{LEG}', f'LP|werewolf|{LEG}', f'LP|marked|{LEG}',
            'LP|zombie|leg=0|state=NoRightLeg', 'LP|complete|failures=0']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12515)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dm-limb-pose-') as temp:
        arena = Path(temp)/'world'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        world = arena/'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        start = source.index('\tNew()'); end = source.index('\nvar/Season', start)
        world.write_text(source[:start] + '\tNew()\n\t\tspawn(0) LpRun()\n' + source[end:], encoding='latin-1')
        shutil.copy2(ROOT/'tests/limb_pose_test.dm', arena/'limb_pose_test.dm')
        fixture = arena/'limb_pose.dme'
        fixture.write_text(dme + '\n#include "limb_pose_test.dm"\n', encoding='latin-1')
        run_world(arena, fixture, 'limb-pose', 120, prefix='LP', port=args.port)
    result = json.loads((ROOT/'tests/limb-pose-checks.json').read_text())
    actual = result['observations']
    result['expected'] = EXPECTED
    result['passed'] = actual == EXPECTED and not result['errors'] and not result['timed_out']
    (ROOT/'tests/limb-pose-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print('  ' if e == a else '!!', a, '' if e == a else f'   (expected {e})')
    print('passed' if result['passed'] else 'FAILED')
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
