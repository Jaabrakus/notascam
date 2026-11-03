#!/usr/bin/env python3
"""Bandages and torches for treating stumps (Stumps.dm), as 32 px item pictures drawn with the wearables' own painter
(wearables64.py: lit from the top-left, outlined in the part's darkest colour), so they sit beside the ropes.

    python3 standalone/remastered/art/enhance/stumpcare32.py [--preview out.png]

Writes game/Icons/Remastered/Items/stumpcare.dmi: a rolled bandage with its loose end (leather strips from the
Leatherworks, or pale spider silk), and a torch (a stick with a pitch-soaked wrap at its head).
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
import wearables64 as w  # noqa: E402
from game_export import write_sheet  # noqa: E402

GAME = os.path.join(HERE, "..", "..", "game")
OUT = os.path.join(GAME, "Icons", "Remastered", "Items", "stumpcare.dmi")

LINEN = [(64, 56, 46), (150, 138, 116), (204, 194, 170), (230, 222, 202), (250, 246, 232)]   # pale leather strips
PITCH = [(14, 10, 8), (36, 28, 22), (58, 46, 36), (84, 68, 52), (118, 98, 76)]


def outline(lay, ramp):
    al = lay[..., 3] > 0
    edge = w.dilate(al) & ~al
    lay[edge, :3] = ramp[0]
    lay[edge, 3] = 255
    return lay


def put(lay, m, ramp, kind):
    part = w.shade(m, ramp, kind)
    drawn = lay[..., 3] > 0
    lay[m] = part[m]
    lay[(w.dilate(m) & ~m) & drawn, :3] = ramp[0]   # a dark line where it lies over what is under it


def bandage(ramp):
    """A roll seen a little from the side: its round face with the wound layers, the roll's body behind it, and the
    loose end trailing off to the lower right."""
    lay = np.zeros((64, 64, 4), np.uint8)
    tail = w.stroke(w.bezier((16, 21.5), (23, 26.5), (30, 24), 12), [3.4] * 12)
    yy, xx = np.mgrid[0:64, 0:64]
    put(lay, tail, ramp, np.where(xx % 4 == 0, 2, 3) * tail)   # flat, with the weave across it
    body = w.ellipse((17.5, 16), 7.6, 7.2) | w.ellipse((12.5, 16), 7.6, 7.2)
    rows = np.zeros((64, 64), bool)
    rows[9:24, 12:18] = True
    body |= rows
    put(lay, body, w.dim(ramp), "round")
    face = w.ellipse((11.5, 16), 6.4, 7.0)
    lv = np.full((64, 64), 3)
    yy, xx = np.mgrid[0:64, 0:64]
    r = np.hypot((xx + 0.5 - 11.5) / 6.4, (yy + 0.5 - 16) / 7.0)
    lv[(r > 0.42) & (r < 0.55)] = 2           # the wound layers on the roll's face
    lv[(r > 0.75) & (r < 0.86)] = 2
    lv[r <= 0.2] = 1                          # the hole in the middle
    lv[(r > 0.86) & (xx + yy < 26)] = 4
    put(lay, face, ramp, lv * face)
    return outline(lay, ramp)[:32, :32].copy()


def torch():
    """A stick leaning to the upper right with a wrap of pitch-soaked rag at its head."""
    lay = np.zeros((64, 64, 4), np.uint8)
    stick = w.stroke([(9, 29), (21, 11)], [3.2, 3.6])
    put(lay, stick, w.RAMPS["wood"], "round")
    wrap = w.ellipse((22.5, 9), 4.6, 5.2)
    yy, xx = np.mgrid[0:64, 0:64]
    lv = np.full((64, 64), 2)
    lv[(yy + xx // 2) % 3 == 0] = 1           # the turns of the rag
    lv[(xx + yy < 28) & ((yy + xx // 2) % 3 != 0)] = 3
    put(lay, wrap, PITCH, lv * wrap)
    tie = w.stroke([(18.5, 13.5), (20.5, 15)], [1.6, 1.6])
    put(lay, tie, w.RAMPS["leather"], "round")
    return outline(lay, PITCH)[:32, :32].copy()


def states():
    return [("bandage-leather", bandage(LINEN)), ("bandage-silk", bandage(w.RAMPS["spidersilk"])), ("torch", torch())]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", default=None, help="also write an enlarged sheet on grass here")
    args = ap.parse_args()
    st = states()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    write_sheet(OUT, [(name, {"dirs": 1, "frames": 1}, [c]) for name, c in st], 32)
    print(OUT, [n for n, _ in st])
    if args.preview:
        k = 4
        sheet = Image.new("RGBA", (len(st) * 32 * k, 32 * k), (62, 92, 48, 255))
        for i, (_, c) in enumerate(st):
            im = Image.fromarray(c).resize((32 * k, 32 * k), Image.NEAREST)
            sheet.paste(im, (i * 32 * k, 0), im)
        sheet.save(args.preview)


if __name__ == "__main__":
    main()
