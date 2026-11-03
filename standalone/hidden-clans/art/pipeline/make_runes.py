#!/usr/bin/env python3
"""Map sprites for the rune circuit pieces (Icons/Remastered/Runes.dmi), drawn
by code at 32 px: line, crystal, door (shut/open), fire jet, spikes (down/up),
pressure plate, lever (left/right), lamp (off/on), alarm bell.

    python3 standalone/remastered/art/pipeline/make_runes.py
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_dmi import write_dmi, outline, description  # noqa: E402

GAME = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'game')
GLOW = (150, 110, 255)
STONE = (110, 106, 112)
DARK = (60, 58, 64)


def cell(draw_fn, ring=True):
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    draw_fn(d)
    a = np.asarray(im).copy()
    return outline(a) if ring else a


def line(d):
    d.line([(4, 16), (28, 16)], fill=GLOW, width=2)
    d.line([(16, 4), (16, 28)], fill=GLOW, width=2)
    d.ellipse([12, 12, 20, 20], outline=GLOW)


def crystal(d):
    d.polygon([(16, 3), (23, 14), (16, 28), (9, 14)], fill=(120, 90, 240))
    d.polygon([(16, 3), (19, 14), (16, 28)], fill=(180, 160, 255))


def door(open_):
    def f(d):
        if open_:
            d.rectangle([4, 24, 28, 29], fill=DARK)
            d.line([(6, 26), (26, 26)], fill=GLOW)
        else:
            d.rectangle([5, 4, 27, 29], fill=STONE)
            d.rectangle([7, 6, 25, 27], outline=DARK)
            d.ellipse([13, 12, 19, 18], outline=GLOW)
    return f


def jet(d):
    d.rectangle([9, 18, 23, 29], fill=DARK)
    d.rectangle([11, 16, 21, 19], fill=STONE)
    d.polygon([(13, 16), (16, 8), (19, 16)], fill=(250, 140, 30))


def spikes(up):
    def f(d):
        d.rectangle([4, 18, 28, 28], fill=DARK)
        for x in (8, 13, 18, 23):
            h = 14 if up else 3
            d.polygon([(x - 2, 22), (x + 2, 22), (x, 22 - h)], fill=(200, 200, 210))
    return f


def plate(d):
    d.rectangle([6, 18, 26, 27], fill=STONE)
    d.rectangle([8, 20, 24, 25], outline=GLOW)


def lever(right):
    def f(d):
        d.rectangle([11, 22, 21, 28], fill=DARK)
        tip = (24, 8) if right else (8, 8)
        d.line([(16, 24), tip], fill=(140, 100, 60), width=3)
        d.ellipse([tip[0] - 3, tip[1] - 3, tip[0] + 3, tip[1] + 3], fill=(200, 60, 50))
    return f


def lamp(on):
    def f(d):
        d.rectangle([14, 12, 18, 29], fill=DARK)
        d.ellipse([10, 3, 22, 15], fill=(200, 180, 255) if on else (70, 64, 90))
    return f


def bell(d):
    d.line([(6, 6), (26, 6)], fill=(140, 100, 60), width=2)
    d.polygon([(10, 24), (13, 9), (19, 9), (22, 24)], fill=(210, 170, 70))
    d.ellipse([14, 23, 18, 27], fill=(120, 90, 40))


STATES = [('line', line, False), ('crystal', crystal, True), ('door_shut', door(0), True), ('door_open', door(1), True),
          ('jet', jet, True), ('spikes_down', spikes(0), True), ('spikes_up', spikes(1), True), ('plate', plate, True),
          ('lever_l', lever(0), True), ('lever_r', lever(1), True), ('lamp_off', lamp(0), True), ('lamp_on', lamp(1), True),
          ('bell', bell, True)]


def main():
    cells = [cell(f, ring) for _, f, ring in STATES]
    cols = 4
    rows = (len(cells) + cols - 1) // cols
    sheet = np.zeros((rows * 32, cols * 32, 4), np.uint8)
    for i, c in enumerate(cells):
        y, x = divmod(i, cols)
        sheet[y * 32:(y + 1) * 32, x * 32:(x + 1) * 32] = c
    out = os.path.join(GAME, 'Icons', 'Remastered', 'Runes.dmi')
    write_dmi(out, sheet, description(32, [{'name': n, 'dirs': 1, 'frames': 1} for n, _, _ in STATES]))
    print(out)


if __name__ == '__main__':
    main()
