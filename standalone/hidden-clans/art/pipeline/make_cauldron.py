#!/usr/bin/env python3
"""The Cauldron's 32 px map sprite (Icons/Remastered/Cauldron.dmi), drawn by
code: an iron pot on three legs with a dark brew surface. "cold" is one frame;
"lit" has two frames with flickering flames under it.

    python3 standalone/remastered/art/pipeline/make_cauldron.py
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_dmi import write_dmi, outline, description  # noqa: E402

GAME = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'game')


def pot(flame=None):
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if flame is not None:   # flames under the pot
        for i, (x, h) in enumerate(((10, 6), (14, 8), (18, 7), (22, 5))):
            h += (flame + i) % 2 * 2 - 1
            d.polygon([(x - 2, 29), (x + 2, 29), (x, 29 - h)], fill=(250, 140, 30))
            d.polygon([(x - 1, 29), (x + 1, 29), (x, 29 - h // 2)], fill=(255, 225, 90))
    for x in (9, 16, 23):   # legs
        d.rectangle([x - 1, 24, x, 29], fill=(40, 38, 42))
    d.ellipse([5, 11, 27, 27], fill=(52, 50, 56))          # bowl
    d.ellipse([7, 13, 25, 25], fill=(64, 62, 68))
    d.arc([6, 12, 26, 26], 200, 330, fill=(110, 108, 116))  # highlight
    d.ellipse([5, 9, 27, 15], fill=(36, 34, 38))            # rim
    d.ellipse([7, 10, 25, 14], fill=(60, 120, 70))          # brew surface
    d.point([(12, 11), (19, 12), (15, 12)], fill=(150, 220, 150))
    return outline(np.asarray(im).copy())


def main():
    frames = [pot(), pot(0), pot(1)]
    states = [{'name': 'cold', 'dirs': 1, 'frames': 1},
              {'name': 'lit', 'dirs': 1, 'frames': 2, 'delay': [3, 3]}]
    sheet = np.zeros((32, 96, 4), np.uint8)
    for i, f in enumerate(frames):
        sheet[:, i * 32:(i + 1) * 32] = f
    out = os.path.join(GAME, 'Icons', 'Remastered', 'Cauldron.dmi')
    write_dmi(out, sheet, description(32, states))
    print(out)


if __name__ == '__main__':
    main()
