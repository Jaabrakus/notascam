#!/usr/bin/env python3
"""Create isolated, bounded arenas around the original gameplay procedures.

The oracle uses frozen original code; OpenDream uses the staged syntax/icon
adaptations. Only world startup, interactive race input and test arena bounds
are substituted, with each substitution recorded. No playable copy is edited.
"""
import hashlib
import argparse
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', default='gameplay')
    args = parser.parse_args()
    name = args.fixture
    if not re.fullmatch(r'[a-z_]+', name): parser.error('Invalid fixture basename')
    report = {}
    for engine, source in [('byond', ROOT/'source'), ('opendream', ROOT/'opendream')]:
        target = ROOT/'reference'/f'{name}-{engine}'
        target.mkdir(exist_ok=True)
        entries = json.loads((ROOT/'reports/source-baseline.json').read_text())
        for entry in entries:
            path = Path(entry['path'])
            if path.suffix.lower() in ('.dmm', '.sav', '.log'): continue
            dest = target/path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source/path, dest)
        dme = (source/'Cave Crawlers.dme').read_text()
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
        (target/f'{name}.dme').write_text(dme+f'\n#include "{name}.dm"\n')
        if name == 'gameplay':
            (target/'gameplay_reload.dme').write_text('#define PARITY_RELOAD\n'+dme+'\n#include "gameplay.dm"\n')
        world = target/'Code/World.dm'
        text = world.read_text(encoding='latin1')
        start = text.index('\tNew()')
        end = text.index('\nvar/Season', start)
        text = text[:start]+'\tNew()\n\t\tspawn(0) ParityRun()\n'+text[end:]
        world.write_text(text, encoding='latin1')
        restart = target/'Code/Restart.dm'
        text = restart.read_text(encoding='latin1')
        # Preserve the actual location algorithm, but constrain its search to
        # the arena. Geographic spawn ranges are explicitly outside this test.
        text = text.replace('\tvar/TRIES=0', '\tX=4\n\tXX=16\n\tY=4\n\tYY=16\n\tvar/TRIES=0', 1)
        text = text.replace('\t\tif(client)\n', '\t\tif(parity_race)\n', 1)
        text = text.replace('Race=input("Which Race Would You Like To Play?", "Choose", null) in menu',
                            'Race=parity_race')
        restart.write_text(text, encoding='latin1')
        shutil.copy2(ROOT/'reference/fixtures'/f'{name}.dm', target/f'{name}.dm')
        report[engine] = {'source': str(source), 'arena': '20x20x2',
            'substitutions': ['world.New runs ParityRun instead of global event loops',
                              'Restart client gate uses parity_race; input uses scripted choice',
                              'LocateValidLocation x/y search bounded to 4..16'],
            'fixture_sha256': hashlib.sha256((target/f'{name}.dm').read_bytes()).hexdigest()}
    (ROOT/'reports'/f'{name}-fixture-scope.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__': main()
