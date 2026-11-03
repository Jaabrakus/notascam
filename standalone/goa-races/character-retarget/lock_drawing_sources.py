#!/usr/bin/env python3
"""Freeze exact original sprite bytes for consistent pixel-copy animation work.

No image resizing, filtering, regeneration, palette conversion or source edits.
An existing master is never silently replaced if the original changes.
"""
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Dungeon Master Sample/GOA Drawn Animation Library'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inventory = json.loads((ROOT / 'Dungeon Master Sample/GOA Race Rig Inventory/inventory.json').read_text())
    entries = []
    for family in inventory['families']:
        source = ROOT / family['baseSource']
        target = OUT / 'source-masters' / family['id'] / 'sprites.png'
        if target.exists() and sha(target) != sha(source):
            raise ValueError('Master differs from source; select a version explicitly: ' + family['id'])
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(source, target)
        assert target.read_bytes() == source.read_bytes()
        with Image.open(source) as image:
            width, height = image.size
            colors = sorted(set(pixel for pixel in image.convert('RGBA').getdata() if pixel[3]))
        palette = target.with_name('source-palette.json')
        palette.write_text(json.dumps(dict(rgba=colors, note='Exact source colors, including original alpha. Do not add smoothing colors.')) + '\n')
        entries.append(dict(character=family['id'], original=str(source.relative_to(ROOT)),
                            master=str(target.relative_to(OUT)), sha256=sha(target),
                            size=[width, height], nativeCellSize=64,
                            sourcePalette=str(palette.relative_to(OUT)), exactByteCopy=True))
    result = dict(version=1, entries=entries, rules=[
        'Original sprites are the identity master. Reuse actual pixels; do not regenerate a whole character per action.',
        'New poses are body-only. Right-hand weapon grips and left-arm shield holds/blocks/bashes are retained, with no equipment painted into the body.',
        'Reuse source head, torso details and existing usable limb pixels; integer translations preserve those copied pixels.',
        'Any newly drawn exposed anatomy must use the source palette and native pixel scale.',
        'No smoothing, interpolation, gradients or automatic beauty pass. Enlarged review images must not be confused with native game sprites.',
        'Generated concept sheets are not identity masters or finished atlases.'
    ])
    (OUT / 'source-lock.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(lockedMasters=len(entries), exactByteCopies=True)))


if __name__ == '__main__':
    main()
