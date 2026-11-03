#!/usr/bin/env python3
"""Per-part timing of the per-player tick on the full maps (fixture tests/track_profile_test.dm, which uses the village
soak's helpers): what spikes in the first 240 tracks after a village appears. A report: fails only on errors."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from check_combat import ROOT, run_world


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12485)
    parser.add_argument('--label', default='track-profile')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dm-track-profile-') as temp:
        arena = Path(temp)/'world'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        world = arena/'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        world.write_text(source.replace('\t\tCallSave()', '\t\tCallSave()\n\t\tspawn() TpRun()'), encoding='latin-1')
        for name in ('track_profile_test.dm', 'village_soak_test.dm'):
            shutil.copy2(ROOT/'tests'/name, arena/name)
        # the soak's own runner stays unused here
        fixture = arena/'track_profile.dme'
        fixture.write_text((arena/'Cave Crawlers.dme').read_text(encoding='latin-1') + '\n#include "village_soak_test.dm"\n#include "track_profile_test.dm"\n', encoding='latin-1')
        passed = run_world(arena, fixture, args.label, 1500, prefix='TP', port=args.port)
    result = json.loads((ROOT/f'tests/{args.label}-checks.json').read_text())
    for line in result['observations']:
        print('  ', line)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
