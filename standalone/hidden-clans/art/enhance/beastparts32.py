#!/usr/bin/env python3
"""What a dead great beast is butchered into (BeastParts.dm), as 32 px item pictures drawn with
the wearables' own painter (wearables64.py: tapering strokes, lit from the top-left, outlined in
each part's darkest colour), so they sit beside the remastered gear.

    python3 standalone/remastered/art/enhance/beastparts32.py [--preview out.png]

Writes game/Icons/Remastered/Items/beastparts.dmi: dragon scales in each dragon's colours
(scales-<variant>), a dragon tooth, a dragon claw, a dragon heart, a piece of wing hide, a spider
fang and a venom sac; and for taming (Taming.dm) dragon eggs (egg-<variant>), a spider egg sac,
and the nests they lie in.
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
OUT = os.path.join(GAME, "Icons", "Remastered", "Items", "beastparts.dmi")

# the dragons' colours (BeastData.dm variants): dark, shadow, mid, light, glint
SCALES = {
    "red": [(46, 8, 8), (108, 22, 18), (162, 40, 28), (204, 76, 44), (246, 148, 98)],
    "red2": [(52, 16, 6), (120, 40, 14), (176, 72, 22), (218, 116, 40), (250, 186, 96)],
    "black": [(8, 8, 12), (28, 26, 36), (48, 44, 60), (76, 70, 94), (132, 124, 156)],
    "ice": [(40, 64, 92), (96, 148, 190), (148, 200, 232), (196, 232, 250), (250, 255, 255)],
    "green": [(10, 30, 12), (30, 74, 30), (52, 112, 46), (86, 152, 70), (156, 206, 120)],
    "sand": [(60, 42, 18), (132, 100, 54), (184, 152, 96), (220, 194, 138), (250, 236, 192)],
    "blue": [(10, 18, 46), (24, 48, 110), (40, 80, 160), (72, 120, 204), (140, 182, 240)],
    "zombie": [(30, 36, 26), (70, 82, 60), (108, 122, 92), (146, 158, 120), (196, 204, 164)],
}
IVORY = [(70, 56, 30), (150, 130, 92), (208, 192, 150), (236, 226, 194), (255, 252, 236)]
GUM = [(52, 8, 10), (112, 26, 28), (160, 52, 50), (196, 92, 84), (232, 150, 140)]
TALON = [(8, 8, 10), (30, 28, 34), (54, 50, 58), (88, 82, 94), (160, 154, 168)]
HEART = [(40, 4, 10), (96, 12, 22), (150, 24, 34), (198, 52, 58), (246, 130, 122)]
VESSEL = [(30, 6, 26), (70, 18, 54), (104, 34, 80), (140, 60, 108), (190, 120, 160)]
MEMBRANE = [(30, 10, 8), (72, 26, 20), (110, 44, 32), (150, 70, 50), (196, 120, 92)]
CHITIN = w.RAMPS["chitin"]
VENOM = [(14, 34, 8), (40, 90, 22), (76, 146, 40), (128, 196, 70), (212, 248, 150)]


def ell(cx, cy, rx, ry):
    yy, xx = np.mgrid[0:64, 0:64]
    return ((xx - cx + 0.5) / rx) ** 2 + ((yy - cy + 0.5) / ry) ** 2 <= 1.0


def poly(points):
    from PIL import ImageDraw
    im = Image.new("L", (64, 64), 0)
    ImageDraw.Draw(im).polygon(points, fill=1)
    return np.array(im, bool)


def cell(layer):
    """The 64 px layer's top-left 32 px, where the item is drawn."""
    return layer[:32, :32].copy()


def scale_shape(cx, cy, rx=3.3, ry=2.8):
    """One scale: rounded above, coming to a point below."""
    return ell(cx, cy, rx, ry) | poly([(cx - rx + 0.4, cy + 0.3), (cx + rx - 0.4, cy + 0.3), (cx, cy + ry + 2.6)])


def scales(ramp):
    """A patch of scales as they lie on the hide: staggered rows, each row overlapping the one
    below it, every scale lit on its own with a dark line where it overlaps."""
    lay = np.zeros((64, 64, 4), np.uint8)
    edge = np.zeros((64, 64), bool)
    rows = [(8.5, [9, 15.5, 22]), (13, [6, 12.5, 19, 25.5]), (17.5, [9, 15.5, 22]), (22, [12.5, 19])]
    for cy, xs in reversed(rows):   # the lowest row first: each row above lies over it
        for cx in xs:
            m = scale_shape(cx, cy)
            part = w.shade(m, ramp, "round")
            drawn = lay[..., 3] > 0
            lay[m] = part[m]
            ring = w.dilate(m) & ~m
            lay[ring & drawn, :3] = ramp[0]   # where it overlaps the scales below
            edge |= m
    al = lay[..., 3] > 0
    ring = w.dilate(al) & ~al
    lay[ring, :3] = ramp[0]
    lay[ring, 3] = 255
    return cell(lay)


def tooth():
    path = w.bezier((10, 8), (13, 20), (23, 23), 14)
    m = w.stroke(path, list(np.linspace(5.5, 0.8, len(path))))
    root = w.stroke(w.bezier((8.5, 6), (9.5, 7.5), (11, 9.5), 5), [5.5] * 5)
    return cell(w.render([(root & ~m, GUM, "round"), (m, IVORY, "round")]))


def claw():
    path = w.bezier((8, 12), (21, 6), (23, 22), 16)
    m = w.stroke(path, list(np.linspace(6, 0.8, len(path))))
    knuckle = ell(8, 13, 4, 3.6)
    return cell(w.render([(knuckle, SCALES["red"], "round"), (m, TALON, "round")]))


def fang():
    path = w.bezier((10, 7), (11, 20), (22, 23), 16)
    widths = list(np.linspace(5, 0.8, len(path)))
    m = w.stroke(path, widths)
    tip = w.stroke(path[10:], widths[10:])
    return cell(w.render([(m & ~tip, CHITIN, "round"), (tip, IVORY, "round")]))


def heart():
    m = ell(12.5, 14, 5, 5.5) | ell(19.5, 14, 5, 5.5) | poly([(8, 16), (24, 16), (16.5, 26)])
    vw = list(np.linspace(3, 2, 6))
    vessels = w.stroke(w.bezier((13, 10), (12, 7), (11, 5), 6), vw) | w.stroke(w.bezier((18, 10), (19, 7), (21, 5), 6), vw)
    lay = w.render([(vessels, VESSEL, "round"), (m, HEART, "round")])
    # a vein across it
    for x, y in ((14, 15), (15, 16), (16, 17), (17, 17), (18, 18), (18, 19)):
        lay[y, x, :3] = HEART[1]
    return cell(lay)


def wing_hide():
    """A piece of wing: the leading bone along the top, finger bones fanning down, and the
    membrane between them hanging in scallops."""
    tips = [(9, 24), (18, 25), (26, 20)]
    m = poly([(4, 9), (27, 6), (27.5, 19.5), (23, 16.5), (18.5, 24.5), (14, 18.5), (9.5, 24), (6, 17)])
    spar = w.stroke([(3.5, 9), (27, 5.5)], [2.8, 1.8])
    fingers = np.zeros((64, 64), bool)
    for (sx, sy), (tx, ty) in zip(((7, 8.4), (15, 7.2), (23, 6.2)), tips):
        fingers |= w.stroke([(sx, sy), (tx, ty)], [1.6, 1.0])
    lay = w.render([(m, MEMBRANE, "round"), (fingers & m, IVORY, "round"), (spar, IVORY, "round")])
    return cell(lay)


def venom_sac():
    m = ell(15.5, 18, 6, 5.2) | poly([(11, 15), (20, 15), (15.5, 10)])
    duct = w.stroke(w.bezier((15.5, 11), (14, 8), (11, 5), 6), list(np.linspace(2.4, 1.6, 6)))
    lay = w.render([(duct, VENOM, "round"), (m, VENOM, "round")])
    for x, y in ((13, 19), (17, 20), (15, 17), (18, 17)):   # the venom inside, darker
        lay[y, x, :3] = VENOM[1]
    return cell(lay)


SILK = [(70, 70, 78), (150, 150, 160), (204, 204, 212), (232, 232, 238), (255, 255, 255)]
STONE = [(26, 24, 22), (62, 58, 54), (96, 90, 84), (132, 126, 118), (176, 170, 160)]
SCORCH = (46, 34, 26)


def egg(ramp):
    """A dragon's egg in its mother's colours, scaled like her hide."""
    m = ell(16, 18.5, 5.7, 5.8) | ell(16, 16, 5.1, 7.2)   # narrower at the top
    lay = w.render([(m, ramp, "round")])
    inner = w.erode(m, 1)
    for row, y in enumerate(range(12, 25, 3)):   # rows of scale edges, staggered
        for x in range(10 + (row % 2) * 2, 23, 4):
            for dx in (0, 1, 2):
                yy = y + (1 if dx == 1 else 0)
                if 0 <= yy < 64 and inner[yy, x + dx]:
                    lay[yy, x + dx, :3] = ramp[1]
    return cell(lay)


def egg_sac():
    """A great spider's eggs, a cluster bound in silk: each egg outlined where it lies over another."""
    lay = np.zeros((64, 64, 4), np.uint8)
    for cx, cy, r in ((15.5, 22, 3.6), (11, 19, 3.8), (20, 19, 3.8), (15.5, 15, 4)):   # back to front
        m = ell(cx, cy, r, r * 0.92)
        part = w.shade(m, SILK, "round")
        drawn = lay[..., 3] > 0
        lay[m] = part[m]
        lay[(w.dilate(m) & ~m) & drawn, :3] = SILK[1]
    al = lay[..., 3] > 0
    for a, b in (((7, 17), (24, 22)), ((10, 25), (21, 12))):   # silk bound round them
        for t in np.linspace(0, 1, 30):
            x, y = int(round(a[0] + (b[0] - a[0]) * t)), int(round(a[1] + (b[1] - a[1]) * t))
            if al[y, x]:
                lay[y, x, :3] = SILK[4]
    ring = w.dilate(al) & ~al
    lay[ring, :3] = SILK[0]
    lay[ring, 3] = 255
    return cell(lay)


def nest():
    """A dragon's nest, seen from above: scorched ground in a ring of stones and gnawed bones."""
    lay = np.zeros((64, 64, 4), np.uint8)
    ground = ell(16, 16, 13, 11)
    lay[ground, :3] = SCORCH
    lay[ground, 3] = 255
    lay[ell(16, 16, 8, 6.5), :3] = (34, 26, 20)
    parts = []
    for k in range(11):
        a = k / 11 * 2 * np.pi
        cx, cy = 16 + 11 * np.cos(a), 16 + 9.4 * np.sin(a)
        if k in (2, 7):   # a bone in the ring
            d = np.array([-np.sin(a), np.cos(a)]) * 3.2
            parts.append((w.stroke([(cx - d[0], cy - d[1]), (cx + d[0], cy + d[1])], [1.8, 1.8]), IVORY, "round"))
        else:
            parts.append((ell(cx, cy, 2.4, 2.0), STONE, "round"))
    ring = w.render(parts)
    m = ring[..., 3] > 0
    lay[m] = ring[m]
    return cell(lay)


def web_nest():
    """A great spider's nest: a mound of silk with threads run out over the ground."""
    lay = np.zeros((64, 64, 4), np.uint8)
    for k in range(8):   # threads first, under the mound
        a = k / 8 * 2 * np.pi + 0.2
        for t in np.linspace(0, 1, 30):
            x, y = int(round(16 + np.cos(a) * 15 * t)), int(round(16 + np.sin(a) * 13 * t))
            if 0 <= x < 32 and 0 <= y < 32:
                lay[y, x, :3] = SILK[2]
                lay[y, x, 3] = 255
    mound = w.render([(ell(16, 16, 8.5, 7), SILK, "round")])
    m = mound[..., 3] > 0
    lay[m] = mound[m]
    return cell(lay)


def chains():
    """A coil of heavy iron chain: oval links, each lit on its own, the near ones over the far."""
    IRON = w.RAMPS["iron"]
    lay = np.zeros((64, 64, 4), np.uint8)
    yy, xx = np.mgrid[0:64, 0:64]
    links = []
    for k in range(9):   # a loose spiral of links, the outer coil first
        a = k * 0.85
        r = 8.5 - k * 0.7
        links.append((16 + r * np.cos(a), 17 + r * 0.75 * np.sin(a), a + np.pi / 2))
    for cx, cy, ang in links:
        u = (xx - cx + 0.5) * np.cos(ang) + (yy - cy + 0.5) * np.sin(ang)
        v = -(xx - cx + 0.5) * np.sin(ang) + (yy - cy + 0.5) * np.cos(ang)
        outer = (u / 3.6) ** 2 + (v / 2.3) ** 2 <= 1
        inner = (u / 1.9) ** 2 + (v / 0.8) ** 2 <= 1
        m = outer & ~inner
        part = w.shade(m, IRON, "round")
        drawn = lay[..., 3] > 0
        lay[m] = part[m]
        lay[(w.dilate(m) & ~m) & drawn & ~inner, :3] = IRON[0]
    al = lay[..., 3] > 0
    ring = w.dilate(al) & ~al
    lay[ring, :3] = IRON[0]
    lay[ring, 3] = 255
    return cell(lay)


def dragon_bones():
    """A dragon's bones: a great curved rib over a thigh bone, worn ivory."""
    BONE = w.RAMPS["dragonbone"]
    femur = w.stroke([(7, 22), (24, 12)], [3.2, 3.2]) | ell(7, 22.5, 2.6, 2.4) | ell(24.5, 11.5, 2.6, 2.4) | ell(6, 20.5, 2.0, 2.0) | ell(25.5, 13.5, 2.0, 2.0)
    rib = w.stroke(w.bezier((6, 12), (16, 2), (27, 20), 14), list(np.linspace(2.6, 1.4, 14)))
    return cell(w.render([(femur, BONE, "round"), (rib, BONE, "round")]))


def states():
    out = [(f"scales-{k}", v) for k, v in ((k, scales(r)) for k, r in SCALES.items())]
    out += [("tooth", tooth()), ("claw", claw()), ("heart", heart()), ("winghide", wing_hide()),
            ("fang", fang()), ("venomsac", venom_sac())]
    out += [(f"egg-{k}", egg(r)) for k, r in SCALES.items()]
    out += [("eggsac", egg_sac()), ("nest", nest()), ("webnest", web_nest()), ("chains", chains()), ("dragonbones", dragon_bones())]
    return out


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
