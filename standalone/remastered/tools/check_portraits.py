#!/usr/bin/env python3
"""Compare actual HUD portrait PNG bytes with one south-facing source-art cell.

Uses real unit constructors in an isolated world. No native client, user input,
normal save, or synthetic art. This is not a browser/native layout test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

from PIL import Image
import check_combat
from check_combat import ROOT, RUNTIME, run_world

sys.path.insert(0, str(ROOT.parent / 'replica/tools'))
from check_generated_icons import read_states, pixel_hash


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', default='portraits')
    parser.add_argument('--server-dir', type=Path, default=RUNTIME/'server')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.label): parser.error('Invalid label')
    source = ROOT/'game/Code/Remastered/HUD.dm'
    fixture_source = ROOT/'tests/portrait_probe.dm'
    runtime = args.server_dir/'Resources/Assemblies/OpenDreamRuntime.dll'
    before = {str(p): sha(p) for p in (source, fixture_source, runtime)}
    with tempfile.TemporaryDirectory(prefix='dm-portraits-') as temporary:
        runner = Path(temporary)/'runtime'
        runner.mkdir()
        for name, target in [('dotnet', RUNTIME/'dotnet'), ('compiler', RUNTIME/'compiler'), ('server', args.server_dir)]:
            (runner/name).symlink_to(target.resolve(), target_is_directory=True)
        check_combat.RUNTIME = runner
        world = Path(temporary)/'world'
        shutil.copytree(ROOT/'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.sav', '*.dmm', 'units', 'saves', 'ErrorLog.txt'))
        (world/'portraits').mkdir()
        dm = world/'Code/World.dm'
        text = dm.read_text(encoding='latin-1')
        start, end = text.index('\tNew()'), text.index('\nvar/Season')
        dm.write_text(text[:start]+'\tNew()\n\t\tlog = file("ErrorLog.txt")\n\t\tspawn(0) PortraitRun()\n'+text[end:], encoding='latin-1')
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        shutil.copy2(fixture_source, world/fixture_source.name)
        fixture = world/'portraits.dme'
        fixture.write_text(dme+'\n#include "portrait_probe.dm"\n', encoding='latin-1')
        run_passed = run_world(world, fixture, args.label, 60, prefix='PORTRAIT', port=12177)
        out = ROOT/'tests'/args.label
        out.mkdir(exist_ok=True)
        shutil.copytree(world/'portraits', out, dirs_exist_ok=True)
    observations = json.loads((out/'observations.json').read_text())
    checks = {'fixture_completed_without_runtime_errors': run_passed}
    for row in observations:
        states = read_states(out/row['source'])
        candidates = [s for s in states if s['name'] == row['state']] or [s for s in states if s['name'] == '']
        state = next((s for s in candidates if not s['movement']), candidates[0])
        cell = next(c for c in state['cells'] if c['direction'] == 'south')
        with Image.open(out/row['source']) as source_image:
            header = source_image.info.get('Description', '').split('state =', 1)[0]
            dimensions = [int(re.search(r'^\s*'+key+r'\s*=\s*(\d+)', header, re.M).group(1))
                          if re.search(r'^\s*'+key+r'\s*=\s*(\d+)', header, re.M) else 32 for key in ('width', 'height')]
        with Image.open(out/row['portrait']) as image:
            row['png_size'] = list(image.size)
            row['expected_cell'] = cell
            row['expected_size'] = dimensions
            checks[row['type']+'_single_source_cell'] = list(image.size) == dimensions and pixel_hash(image) == cell['sha256']
    checks['source_runtime_fixture_stable'] = before == {p: sha(Path(p)) for p in before}
    result = dict(scope=__doc__, passed=all(checks.values()), checks=checks, observations=observations, hashes=before)
    (ROOT/'tests'/(args.label+'-checks.json')).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
