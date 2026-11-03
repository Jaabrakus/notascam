#!/usr/bin/env python3
"""Worn gear over a lost limb in 3D (Code/Remastered/LimbGear.dm, fixture tests/limb_gear_test.dm): a kobold, a
human and an orc in iron greaves and vambraces lose the right leg, then the left arm too. No gear may cover where
the limb was, the lost arm's own vambrace is not drawn, the gear over the rest of the body stays as it was, and
the other arm's vambrace stays whole.
Writes before/after stills at 4x (every facing, frame 1) to reports/polish-2026-10-22/qa-stability/limbs/."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

from check_combat import ROOT, run_world

RACES = ['Kobold', 'Human', 'Orc']
STAGES = [('whole', '-'), ('no_right_leg', 'NoRightLeg'), ('no_right_leg_no_left_arm', 'NoRightLegNoLeftArm')]
EXPECTED = [f'LG|{r}|{s}|cut={c}|covered_before={0 if c == "-" else 1}|gone_after=0|shared_kept=1|other_arm_kept=1|left_vambrace={0 if "Arm" in c else 1}|sword=1'
            for r in RACES for s, c in STAGES] + ['LG|complete|failures=0']
OUT = ROOT/'reports/polish-2026-10-22/qa-stability/limbs'


def stills(dump):
    from PIL import Image, ImageDraw
    OUT.mkdir(parents=True, exist_ok=True)
    scale, pad = 4, 8
    cell = 64 * scale
    for race in RACES:
        stages = dump.get(race) or {}
        cols = len(STAGES) * 4
        img = Image.new('RGBA', (pad + cols * (cell + pad) + 40, 2 * (cell + pad) + pad + 24), (96, 120, 72, 255))
        d = ImageDraw.Draw(img)
        for si, (stage, _) in enumerate(STAGES):
            d.text((40 + pad + si * 4 * (cell + pad), 4), stage.replace('_', ' '), fill=(255, 255, 255, 255))
            for row, kind in enumerate(['before', 'after']):
                d.text((4, 24 + pad + row * (cell + pad) + cell // 2), kind, fill=(255, 255, 255, 255))
                for di, pix in enumerate((stages.get(stage) or {}).get(kind) or []):
                    px = pix.split(',')
                    tile = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
                    for i, c in enumerate(px[:4096]):
                        if len(c) >= 7:
                            a = int(c[7:9], 16) if len(c) >= 9 else 255
                            tile.putpixel((i % 64, i // 64), (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), a))
                    tile = tile.resize((cell, cell), Image.NEAREST)
                    img.alpha_composite(tile, (40 + pad + (si * 4 + di) * (cell + pad), 24 + pad + row * (cell + pad)))
        path = OUT/f'gear-cut-{race.lower()}-4x.png'
        img.convert('RGB').save(path)
        print('still:', path.relative_to(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12525)
    parser.add_argument('--no-stills', action='store_true')
    args = parser.parse_args()
    dump = None
    with tempfile.TemporaryDirectory(prefix='dm-limb-gear-') as temp:
        arena = Path(temp)/'world'
        shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        world = arena/'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        start = source.index('\tNew()'); end = source.index('\nvar/Season', start)
        world.write_text(source[:start] + '\tNew()\n\t\tspawn(0) LgRun()\n' + source[end:], encoding='latin-1')
        shutil.copy2(ROOT/'tests/limb_gear_test.dm', arena/'limb_gear_test.dm')
        fixture = arena/'limb_gear.dme'
        fixture.write_text(dme + '\n#include "limb_gear_test.dm"\n', encoding='latin-1')
        run_world(arena, fixture, 'limb-gear', 240, prefix='LG', port=args.port)
        found = list(arena.rglob('lg-dump.json'))
        if found:
            dump = json.loads(found[0].read_text())
    result = json.loads((ROOT/'tests/limb-gear-checks.json').read_text())
    actual = [o for o in result['observations'] if not o.startswith('LGINFO|')]
    result['info'] = [o for o in result['observations'] if o.startswith('LGINFO|')]
    result['expected'] = EXPECTED
    result['passed'] = actual == EXPECTED and not result['errors'] and not result['timed_out']
    (ROOT/'tests/limb-gear-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print('  ' if e == a else '!!', a, '' if e == a else f'   (expected {e})')
    for i in result['info']:
        print('  ', i)
    if dump and not args.no_stills:
        stills(dump)
    print('passed' if result['passed'] else 'FAILED')
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
