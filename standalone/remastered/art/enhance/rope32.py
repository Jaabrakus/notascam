#!/usr/bin/env python3
"""Rope for tying captives (Captives.dm), as 32 px item pictures drawn with the wearables' own painter
(wearables64.py: lit from the top-left, outlined in the part's darkest colour), so they sit beside the
chains and the remastered gear.

    python3 standalone/remastered/art/enhance/rope32.py [--preview out.png]

Writes game/Icons/Remastered/Items/rope.dmi: a coil of rope with its loose end, laid strands showing as a
twist, in three materials: plant rope (log fibre, straw and green), leather rope (plaited hide) and silk rope
(spider silk, pale and fine). Also "stake": a pointed wooden stake with a band of plant rope round its head, the
stake a captive is tied to in open ground (Captives.dm "Stake here").
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
OUT = os.path.join(GAME, "Icons", "Remastered", "Items", "rope.dmi")

FIBRE = [(40, 36, 14), (92, 86, 38), (140, 130, 64), (182, 170, 98), (220, 210, 146)]
ROPES = {"plant": (FIBRE, 2.6), "leather": (w.RAMPS["leather"], 2.6), "silk": (w.RAMPS["spidersilk"], 2.1)}


def ring(cx, cy, rx, ry, width, a0=0.0, a1=2 * np.pi, n=40):
    pts = [(cx + rx * np.cos(a), cy + ry * np.sin(a)) for a in np.linspace(a0, a1, n)]
    return w.stroke(pts, [width] * len(pts))


def twist(mask):
    """Laid strands: a darker diagonal every few pixels along the rope."""
    yy, xx = np.mgrid[0:64, 0:64]
    lv = np.full((64, 64), 2)
    ys, xs = np.nonzero(mask)
    if len(ys):
        top, bot = ys.min(), ys.max()
        v = np.clip((yy - top) / max(1, bot - top), 0, 1)
        lv[v < 0.3] = 3
        lv[v > 0.75] = 1
    lv[(xx + yy * 2) % 4 == 0] -= 1
    lv[(xx + yy * 2) % 4 == 1] += 1
    return np.clip(lv, 1, 4) * mask


def coil(ramp, width):
    """Three loops of rope lying on each other (the far loop first, each nearer one outlined where it crosses the
    one under it) round an open middle, and a loose end trailing down to the right."""
    lay = np.zeros((64, 64, 4), np.uint8)

    def put(m, kind):
        part = w.shade(m, ramp, kind)
        drawn = lay[..., 3] > 0
        lay[m] = part[m]
        lay[(w.dilate(m) & ~m) & drawn, :3] = ramp[0]   # a dark line where it lies over the loop below

    for cy, rx, ry in [(13.5, 9.6, 4.6), (16.5, 10.4, 5.0), (19.5, 11.0, 5.4)]:
        m = ring(16, cy, rx, ry, width)
        put(m, twist(m))
    end = w.stroke(w.bezier((26.5, 20), (30, 25), (26, 29.5), 10), [width] * 10)
    put(end, twist(end))
    tuft = w.stroke([(26, 29.5), (24.5, 31)], [width * 0.9, 1.2])
    put(tuft, "strand")
    al = lay[..., 3] > 0
    edge = w.dilate(al) & ~al
    lay[edge, :3] = ramp[0]
    lay[edge, 3] = 255
    return lay[:32, :32].copy()


def stake():
    """A stake lying on the ground: point down to the left, a split head up to the right, with a band of rope."""
    lay = np.zeros((64, 64, 4), np.uint8)
    wood = w.RAMPS["wood"]
    pts = w.bezier((6.5, 27.5), (15.5, 18.5), (25.5, 7.5), 12)
    m = w.stroke(pts, [0.6, 1.4, 2.2, 2.8, 3.2, 3.4, 3.5, 3.6, 3.6, 3.7, 3.8, 3.8])
    part = w.shade(m, wood, "strand")
    lay[m] = part[m]
    head = w.stroke([(23.6, 8.4), (26.2, 6.0)], [3.9, 3.9]) & m
    lay[head, :3] = wood[3]
    for a, b in [((20.0, 14.4), (17.0, 10.6)), ((21.6, 12.6), (18.6, 8.8))]:
        band = w.stroke([(a[0] - 0.4, a[1] + 2.6), (a[0] + 2.4, a[1] - 0.4)], [1.6, 1.6])
        r = w.shade(band, FIBRE, "strand")
        lay[band] = r[band]
    al = lay[..., 3] > 0
    edge = w.dilate(al) & ~al
    lay[edge, :3] = wood[0]
    lay[edge, 3] = 255
    return lay[:32, :32].copy()


def states():
    return [(f"rope-{k}", coil(r, wd)) for k, (r, wd) in ROPES.items()] + [("stake", stake())]


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
