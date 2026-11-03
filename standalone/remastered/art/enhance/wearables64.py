#!/usr/bin/env python3
"""Wearables drawn as 64 px pixel art on the shared humanoid body (remaster64.py).

    python3 standalone/remastered/art/enhance/wearables64.py     (writes art/out/helmets-test.png)

A wearable is a list of parts (masks) in draw order. Each part is shaped from the
template's own landmarks for that facing (head outline, brow, eyes, face side), shaded
as lit metal, horn, feather or cloth with a five-colour ramp per material (dark, shadow,
mid, light, glint), and outlined. Parts are designed once on the standard 64 px body;
remaster64.reshape() then fits the finished layer to dwarves and goblins like every
other overlay, so one design serves every body type.

Materials follow the game's tiers (Remaster3DGear in View3D.dm): wood, bone, leather,
iron, silver, gold, adamantium, diamond, chitin, hell; plus horn, feather and plume
colours for details.
"""

import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import remaster64 as rm  # noqa: E402

# five-colour ramps: dark (outline), shadow, mid, light, glint
RAMPS = {
    "iron": [(30, 32, 38), (66, 70, 78), (104, 109, 118), (148, 154, 163), (206, 212, 220)],
    "silver": [(40, 44, 54), (102, 108, 122), (154, 160, 174), (200, 206, 218), (244, 247, 252)],
    "gold": [(58, 34, 8), (132, 86, 22), (198, 146, 40), (234, 198, 86), (255, 242, 176)],
    "bronze": [(46, 22, 10), (110, 58, 26), (164, 98, 44), (208, 144, 78), (246, 208, 152)],
    "adamantium": [(18, 44, 52), (48, 108, 122), (94, 174, 186), (154, 222, 230), (226, 252, 255)],
    "diamond": [(56, 86, 108), (132, 192, 222), (186, 232, 248), (224, 250, 255), (255, 255, 255)],
    "leather": [(32, 18, 10), (74, 44, 24), (110, 70, 40), (146, 100, 62), (184, 138, 96)],
    "wood": [(38, 22, 10), (90, 56, 28), (130, 86, 46), (168, 120, 72), (202, 158, 108)],
    "bone": [(64, 56, 42), (138, 126, 102), (194, 184, 158), (228, 220, 198), (250, 246, 234)],
    "chitin": [(10, 8, 14), (32, 28, 40), (56, 50, 68), (88, 80, 106), (148, 138, 168)],
    "dragon": [(34, 8, 6), (92, 22, 16), (144, 42, 26), (192, 82, 42), (242, 168, 96)],   # dragon scales (BeastParts.dm)
    "fang": [(74, 58, 32), (154, 134, 96), (210, 194, 152), (236, 228, 198), (255, 252, 238)],   # teeth, claws, fangs
    "dragonfang": [(74, 58, 32), (154, 134, 96), (210, 194, 152), (236, 228, 198), (255, 252, 238)],   # a dragon's tooth
    "spiderfang": [(8, 6, 10), (30, 24, 36), (54, 46, 64), (88, 78, 102), (150, 140, 170)],   # a great spider's fang
    "venom": [(14, 34, 8), (40, 90, 22), (76, 146, 40), (128, 196, 70), (212, 248, 150)],
    "dragonbone": [(56, 44, 28), (126, 108, 78), (186, 170, 134), (222, 210, 176), (248, 242, 220)],   # a dragon's bones over its scales
    "dragonhorn": [(16, 8, 6), (52, 26, 18), (92, 50, 34), (140, 90, 62), (200, 160, 120)],   # its horns and spines
    "ember": [(70, 8, 4), (150, 30, 10), (230, 90, 20), (255, 170, 60), (255, 236, 170)],
    "spidereye": [(60, 0, 4), (140, 8, 12), (220, 30, 34), (255, 96, 90), (255, 210, 200)],
    "silk": [(70, 70, 78), (150, 150, 160), (204, 204, 212), (232, 232, 238), (255, 255, 255)],
    "dragonhide": [(28, 8, 6), (72, 22, 16), (112, 38, 26), (150, 62, 40), (196, 104, 72)],   # a dragon's wing leather
    "spidersilk": [(58, 54, 70), (126, 122, 142), (182, 178, 196), (218, 216, 230), (250, 248, 255)],
    "bonehide": [(36, 22, 12), (82, 52, 30), (120, 80, 46), (158, 114, 72), (198, 156, 108)],
    "hell": [(26, 6, 6), (78, 16, 14), (122, 28, 22), (174, 58, 30), (255, 148, 58)],
    "horn": [(62, 52, 38), (140, 124, 96), (198, 184, 150), (230, 220, 192), (250, 246, 230)],
    "feather": [(66, 66, 72), (156, 156, 164), (204, 204, 210), (234, 234, 238), (255, 255, 255)],
    "plume": [(48, 8, 8), (118, 20, 20), (174, 40, 34), (212, 78, 58), (240, 138, 108)],
    "red": [(40, 6, 8), (100, 18, 20), (150, 30, 30), (188, 54, 46), (222, 100, 84)],
    "blue": [(10, 16, 40), (26, 44, 96), (40, 70, 142), (66, 104, 182), (120, 156, 216)],
    "purple": [(22, 8, 34), (58, 24, 84), (92, 44, 128), (132, 74, 172), (182, 128, 214)],
    "green": [(10, 28, 12), (28, 66, 30), (46, 100, 44), (74, 136, 64), (122, 178, 104)],
    "white": [(70, 68, 72), (150, 146, 150), (204, 200, 204), (232, 230, 232), (252, 252, 252)],
    "black": [(8, 8, 10), (24, 24, 30), (40, 40, 48), (62, 62, 74), (100, 100, 116)],
    "wool": [(30, 24, 20), (70, 56, 44), (104, 86, 66), (138, 116, 90), (170, 148, 118)],
    "runesteel": [(22, 30, 44), (58, 74, 98), (96, 116, 144), (142, 164, 192), (204, 222, 244)],
    "ice": [(40, 70, 96), (110, 170, 210), (170, 220, 244), (210, 242, 255), (250, 255, 255)],
    "void": [(10, 4, 18), (34, 14, 56), (60, 28, 96), (96, 54, 148), (160, 112, 220)],
}
CLOTH = ("red", "blue", "purple", "green", "white", "black", "wool")
TIERS = ["wood", "bone", "leather", "iron", "silver", "gold", "adamantium", "diamond", "chitin", "hell", "dragon", "dragonfang",
         "spiderfang", "dragonbone", "dragonhide", "spidersilk", "bonehide"]
# weapons with a beast's look (weapon_layer): grips, guards, pommels, blades and hafts
WTHEME = {"dragonfang": "dragon", "spiderfang": "spider", "chitin": "spider", "dragonbone": "bone"}
# tiers (and robes) drawn with their beast's look over the style (theme() below): dragon, spider or a dragon's bones
THEME = {"dragon": "dragon", "dragonhide": "dragon", "dragonrobe": "dragon", "chitin": "spider", "spidersilk": "spider",
         "spiderrobe": "spider", "dragonbone": "bone", "bonehide": "bone", "bonerobe": "bone"}
THEMED = tuple(THEME)
LEATHER_TIERS = ("dragonhide", "spidersilk", "bonehide")   # beast leathers: the leather styles in the tier's own colours
STUDS = {"dragonhide": "dragonhorn", "spidersilk": "chitin", "bonehide": "dragonbone"}
METAL = ("iron", "silver", "gold", "bronze", "adamantium", "diamond", "hell")


# ---------------------------------------------------------------------------
# landmarks of the standard 64 px template, per facing
# ---------------------------------------------------------------------------

class Head:
    """The head on the standard template in one facing: its mask and where the face is."""

    def __init__(self, body, d):
        al = body[..., 3] > 0
        self.d = d
        self.mask = al.copy()
        self.mask[rm.CHIN:] = False
        ys, xs = np.nonzero(self.mask)
        self.top, self.bottom = ys.min(), ys.max()
        self.left, self.right = xs.min(), xs.max()
        self.cx = (self.left + self.right) / 2.0
        # brow and eyes (measured on Human.dmi): the side views carry the face lower
        self.brow = {"S": 18, "N": 20, "E": 21, "W": 21}[d]
        self.eye = {"S": 21, "N": 21, "E": 24, "W": 24}[d]
        self.front = {"E": self.right, "W": self.left}.get(d)    # the face edge in profile

    def rows(self, y):
        xs = np.flatnonzero(self.mask[y])
        return (xs.min(), xs.max()) if len(xs) else (None, None)


def template_heads():
    H = rm.read_dmi(os.path.join(rm.ICONS, "Human.dmi"))[""]
    return {d: Head(rm.up(H[i]), d) for i, d in enumerate(rm.DIRS)}


# ---------------------------------------------------------------------------
# drawing parts
# ---------------------------------------------------------------------------

def empty():
    return np.zeros((64, 64), bool)


def dilate(m, n=1):
    for _ in range(n):
        p = np.pad(m, 1)
        m = m | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return m


def stroke(points, widths):
    """A tapering pixel stroke through points (x, y) with widths per point: horns, plumes."""
    m = empty()
    yy, xx = np.mgrid[0:64, 0:64]
    pts = np.array(points, float)
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        n = int(max(2, np.hypot(*(b - a)) * 3))
        for t in np.linspace(0, 1, n):
            c = a + (b - a) * t
            r = (widths[i] + (widths[i + 1] - widths[i]) * t) / 2.0
            m |= (xx - c[0] + 0.5) ** 2 + (yy - c[1] + 0.5) ** 2 <= r * r + 0.15
    return m


def bezier(p0, p1, p2, n=12):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in np.linspace(0, 1, n)]


def shade(mask, ramp, kind="round", rivets=None):
    """Lit pixels for one part: u across each run and v down the part, light from the
    top-left, a glint on the lit outer edge (round), lengthwise streaks (strand)."""
    out = np.zeros((64, 64, 4), np.uint8)
    if not mask.any():
        return out
    u = rm.runs(mask)
    ys, xs = np.nonzero(mask)
    top, bot = ys.min(), ys.max()
    v = np.clip((np.arange(64)[:, None] - top) / max(1, bot - top), 0, 1) * np.ones((1, 64))
    if isinstance(kind, np.ndarray):   # levels given by the part's own shape (blades, patterns)
        lvl = kind.astype(int).copy()
    else:
        lvl = np.full((64, 64), 2)
        lvl[u < 0.34] = 3
        lvl[u > 0.7] = 1
        lvl[(v < 0.2) & (lvl < 3)] += 1
        lvl[(v > 0.86) & (lvl > 1)] -= 1
    pad = np.pad(~mask, 1, constant_values=True)
    up_out, left_out = pad[:-2, 1:-1], pad[1:-1, :-2]
    down_out, right_out = pad[2:, 1:-1], pad[1:-1, 2:]
    if isinstance(kind, str) and kind == "round":
        lvl[mask & (up_out | left_out) & (u < 0.55) & (v < 0.6)] = 4
    if isinstance(kind, str) and kind == "strand":   # feathers, plume, hair: streaks along the part
        lvl[mask & ((np.arange(64)[None, :] + np.arange(64)[:, None]) % 3 == 0)] -= 1
        lvl[mask & (up_out | left_out)] = 3
    if not isinstance(kind, np.ndarray):
        lvl[mask & (down_out | right_out)] = np.minimum(lvl[mask & (down_out | right_out)], 1)
    if rivets is not None:
        lvl[rivets & mask] = 4
    lvl = np.clip(lvl, 1, 4)
    pal = np.array(ramp, np.uint8)
    out[mask, :3] = pal[lvl[mask]]
    out[mask, 3] = 255
    return out


def render(parts):
    """parts: [(mask, ramp, kind[, rivets])] in draw order -> RGBA layer, outlined in each
    part's own darkest colour where it meets nothing."""
    out = np.zeros((64, 64, 4), np.uint8)
    edge_colour = np.zeros((64, 64, 3), np.uint8)
    for p in parts:
        mask, ramp, kind = p[:3]
        riv = p[3] if len(p) > 3 else None
        lay = shade(mask, ramp, kind, riv)
        m = lay[..., 3] > 0
        out[m] = lay[m]
        ring = dilate(mask) & ~mask
        edge_colour[ring] = ramp[0]
    al = out[..., 3] > 0
    ring = dilate(al) & ~al
    out[ring, :3] = edge_colour[ring]
    out[ring, 3] = 255
    # a part laid over another gets a dark line where it starts
    return out


# ---------------------------------------------------------------------------
# helmet parts
# ---------------------------------------------------------------------------

def brim_line(h, back_drop=3, front=None):
    """Row of the helmet's lower edge for each column: just over the brow at the front,
    lower at the back of the head (profile) and all round the back (north)."""
    y = np.full(64, h.brow - 1 if front is None else front, float)
    if h.d == "N":
        y[:] = h.brow + 2
    elif h.d in ("E", "W"):
        span = max(1, h.right - h.left)
        for x in range(64):
            t = (x - h.left) / span if h.d == "E" else (h.right - x) / span     # 0 at the back, 1 at the face
            y[x] = (h.brow - 1) + back_drop * (1 - np.clip(t, 0, 1))
    return y


def dome(h, brim, lift=0, peak=0):
    """The skull cap: the head above the brim, one pixel proud of it; lift raises the
    crown, peak draws it up into a point (spangenhelm)."""
    m = empty()
    for y in range(64):
        for x in range(64):
            if h.mask[y, x] and y <= brim[x]:
                m[y, x] = True
    m = dilate(m) & (np.arange(64)[:, None] <= brim[None, :])
    if lift:
        for x in range(64):
            ys = np.flatnonzero(m[:, x])
            if len(ys):
                m[max(0, ys.min() - lift):ys.min(), x] = True
    if peak:
        cx = h.cx if h.d in ("S", "N") else h.cx - (2 if h.d == "E" else -2)
        ys, xs = np.nonzero(m)
        top = ys.min()
        half = (xs.max() - xs.min()) / 2.0
        for x in range(64):
            t = 1 - abs(x - cx) / max(1.0, half * 0.9)
            if t > 0 and m[:, x].any():
                m[max(0, int(round(top - peak * t ** 1.6))):top + 1, x] = True
    return m


def band(dome_m, rows=3):
    """The bottom rows of a dome: the rim band."""
    m = empty()
    for x in range(64):
        ys = np.flatnonzero(dome_m[:, x])
        if len(ys):
            m[max(ys.min(), ys.max() - rows + 1):ys.max() + 1, x] = True
    return m


def rivet_dots(band_m, every=4):
    r = empty()
    for x in range(64):
        ys = np.flatnonzero(band_m[:, x])
        if len(ys) and x % every == 1:
            r[ys[len(ys) // 2], x] = True
    return r


def nasal(h, brim, length=6, width=2):
    m = empty()
    if h.d == "S":
        x0 = int(round(h.cx)) - width // 2 + 1
        y0 = int(brim[x0])
        m[y0:y0 + length, x0 - 1 + (width == 1):x0 + width - 1 + 1] = True
    elif h.d in ("E", "W"):
        x = h.front - 1 if h.d == "E" else h.front + 1
        y0 = int(brim[x])
        xs = slice(x - 1, x + 1) if h.d == "E" else slice(x, x + 2)
        m[y0:y0 + length, xs] = True
    return m


def cheek_guards(h, brim, down=8):
    m = empty()
    if h.d == "S":
        for y in range(int(brim[int(h.cx)]), int(brim[int(h.cx)]) + down):
            a, b = h.rows(y)
            if a is None:
                continue
            m[y, a - 1:a + 4] = True
            m[y, b - 3:b + 2] = True
    elif h.d in ("E", "W"):   # a plate over the cheek, behind the eye, its front edge slanting back
        k = 1 if h.d == "E" else -1
        for i in range(down):
            x_front = h.front - k * (5 + i // 2)
            y = int(brim[x_front]) + 1 + i
            xs = range(x_front - k * 5, x_front + k) if k > 0 else range(x_front, x_front + 6)
            for x in xs:
                m[y, x] = True
    elif h.d == "N":
        for y in range(int(brim[int(h.cx)]), int(brim[int(h.cx)]) + down - 2):
            a, b = h.rows(y)
            if a is not None:
                m[y, a - 1:b + 2] = True
    return m & dilate(h.mask)


def horns(h, near=True, far=True, size=1.0):
    """Curved horns out of the sides of the helmet (front and back views: both; profile:
    the near horn in front of the dome, the far one's tip behind it)."""
    s = size
    out_far, out_near = empty(), empty()
    if h.d in ("S", "N"):
        y0 = h.brow - 5
        for k in (-1, 1):
            x0 = (h.left + 1) if k < 0 else (h.right - 1)
            pts = bezier((x0, y0), (x0 + k * 9 * s, y0 + 1), (x0 + k * 8 * s, y0 - 8 * s), 10)
            out_near |= stroke(pts, [4.2, 3.6, 3.2, 2.8, 2.4, 2.0, 1.7, 1.4, 1.2, 1.0])
    else:   # profile: a crescent from the side of the helm, sweeping back then up and forward
        k = 1 if h.d == "E" else -1
        x0 = int(round(h.cx)) - k * 2
        y0 = h.brow - 4
        pts = bezier((x0, y0), (x0 - k * 9 * s, y0 - 1), (x0 - k * 6 * s, y0 - 10 * s), 10)
        out_near = stroke(pts, [5.0, 4.4, 3.8, 3.2, 2.8, 2.4, 2.0, 1.6, 1.3, 1.0])
        pts = bezier((x0 + k * 3, y0 - 3), (x0 - k * 4 * s, y0 - 5), (x0 - k * 1 * s, y0 - 11 * s), 10)
        out_far = stroke(pts, [3.6, 3.2, 2.8, 2.4, 2.1, 1.8, 1.5, 1.3, 1.1, 1.0])
    return out_far, out_near


def wings(h):
    """Small swept wings at the temples, feathers in steps."""
    out_far, out_near = empty(), empty()
    if h.d in ("S", "N"):
        y0 = h.brow - 4
        for k in (-1, 1):
            x0 = (h.left + 1) if k < 0 else (h.right - 1)
            for i, (dx, dy, w) in enumerate(((6, -2, 3.2), (8, -5, 2.8), (7, -8, 2.4), (5, -10, 2.0))):
                pts = [(x0, y0 - i), (x0 + k * dx, y0 + dy - i)]
                out_near |= stroke(pts, [3.0, w * 0.7])
    else:
        k = 1 if h.d == "E" else -1
        x0 = int(round(h.cx)) - k * 2
        y0 = h.brow - 5
        for i, (dx, dy, w) in enumerate(((-7, -1, 3.0), (-8, -4, 2.6), (-7, -7, 2.2), (-5, -9, 1.8))):
            out_near |= stroke([(x0, y0 - i), (x0 + k * dx, y0 + dy - i)], [3.2, w * 0.7])
    return out_far, out_near


def plume(h):
    """A crest of horsehair from brow to nape (red)."""
    m = empty()
    ys, xs = np.nonzero(h.mask)
    top = ys.min()
    if h.d in ("S", "N"):
        cx = h.cx
        m |= stroke([(cx, top + 2), (cx, top - 6)], [4.5, 3.5])
        m |= stroke([(cx, top - 6), (cx + (1 if h.d == "S" else -1) * 1.5, top - 8)], [3.5, 2.0])
    else:
        k = 1 if h.d == "E" else -1
        pts = bezier((h.cx + k * 7, top + 1), (h.cx, top - 9), (h.cx - k * 11, top + 6), 14)
        m |= stroke(pts, [3, 4, 4.5, 5, 5, 5, 5, 5, 4.5, 4.5, 4, 3.5, 3, 2.5])
    return m


def visor_slits(h):
    """Great helm: the eye slit and a breathing line, as dark pixels inside the helm."""
    m = empty()
    if h.d == "S":
        cx = int(round(h.cx))
        m[h.eye - 1:h.eye + 1, cx - 9:cx + 11] = True
        m[h.eye + 1:h.eye + 6, cx:cx + 2] = True
        for y in (h.eye + 3, h.eye + 5):
            for x in (cx - 6, cx - 4, cx + 5, cx + 7):
                m[y, x] = True
    elif h.d in ("E", "W"):
        k = 1 if h.d == "E" else -1
        x1 = h.front
        xs = range(x1 - 8, x1 + 1) if k > 0 else range(x1, x1 + 9)
        for x in xs:
            m[h.eye - 2:h.eye, x] = True
        for y in (h.eye + 2, h.eye + 4):
            m[y, x1 - 3 * k] = True
            m[y, x1 - 5 * k] = True
    return m


# ---------------------------------------------------------------------------
# helmet styles
# ---------------------------------------------------------------------------

def helm_nasal(h, tier, extra=None):
    ramp = RAMPS[tier]
    brim = brim_line(h)
    d = dome(h, brim, lift=1, peak=4)
    b = band(d, 3)
    parts = [(d, ramp, "round"), (b, [ramp[0], ramp[1], ramp[1], ramp[2], ramp[3]], "flat", rivet_dots(b)),
             (nasal(h, brim), ramp, "round")]
    return parts


def helm_horned(h, tier):
    ramp = RAMPS[tier]
    brim = brim_line(h)
    d = dome(h, brim, lift=1)
    b = band(d, 3)
    far, near = horns(h)
    return [(far, RAMPS["horn"], "round"), (d, ramp, "round"),
            (b, [ramp[0], ramp[1], ramp[1], ramp[2], ramp[3]], "flat", rivet_dots(b)),
            (nasal(h, brim, 5), ramp, "round"), (near, RAMPS["horn"], "round")]


def helm_winged(h, tier):
    ramp = RAMPS[tier]
    brim = brim_line(h)
    d = dome(h, brim, lift=2)
    b = band(d, 2)
    far, near = wings(h)
    return [(far, RAMPS["feather"], "strand"), (d, ramp, "round"),
            (b, [ramp[0], ramp[1], ramp[2], ramp[3], ramp[4]], "flat"), (near, RAMPS["feather"], "strand")]


def helm_great(h, tier):
    """Flat-topped great helm: the whole head, an eye slit and breathing holes."""
    ramp = RAMPS[tier]
    m = dilate(h.mask.copy())
    ys, xs = np.nonzero(h.mask)
    top = ys.min()
    m[:top + 1] = False
    for y in range(top + 1, rm.CHIN):
        a, b = h.rows(y)
        if a is not None:
            m[y, a - 1:b + 2] = True
    m[top, :] = False
    xs = np.flatnonzero(m[top + 2])
    m[top, xs.min() + 1:xs.max()] = True
    slits = visor_slits(h)
    rim = band(m, 2)
    return [(m & ~slits, ramp, "round"), (rim & ~slits, [ramp[0], ramp[1], ramp[1], ramp[2], ramp[3]], "flat", rivet_dots(rim, 5)),
            (slits & m, [ramp[0]] * 5, "flat")]


def helm_crested(h, tier):
    ramp = RAMPS[tier]
    brim = brim_line(h)
    d = dome(h, brim, lift=1)
    b = band(d, 2)
    return [(d, ramp, "round"), (b, [ramp[0], ramp[1], ramp[2], ramp[3], ramp[4]], "flat"),
            (cheek_guards(h, brim) & ~d, ramp, "round"), (plume(h), RAMPS["plume"], "strand")]


def helm_kettle(h, tier):
    """The original Metal Helmet, finished as lit metal (for comparison)."""
    return None


HELMETS = {"kettle (original)": helm_kettle, "nasal": helm_nasal, "horned": helm_horned, "winged": helm_winged,
           "great helm": helm_great, "crested": helm_crested}


def helmet_layer(style, tier, d, heads, M):
    if style == "horned" and THEME.get(tier) == "spider":   # a spider's helm wears its legs, not horns (theme())
        return theme(render([p for p in HELMETS["horned"](heads[d], tier) if p[1] is not RAMPS["horn"]]), "helmet", tier, d, style=style)
    if style.startswith("kettle"):
        i = rm.DIRS.index(d)
        return theme(rm.metal_finish(rm.up(M["Metal Helmet"][i]), "helmet", RAMPS[tier] if tier in RAMPS else rm.IRON), "helmet", tier, d, style=style)
    return theme(render(HELMETS[style](heads[d], tier)), "helmet", tier, d, style=style)


# ---------------------------------------------------------------------------
# the template's references, per facing (all in the human template's 64 px frame)
# ---------------------------------------------------------------------------

def moved(a, dx, dy):
    """a (a layer or a mask) moved by whole pixels, what leaves the cell dropped."""
    out = np.zeros_like(a)
    h, w_ = a.shape[:2]
    ys, yd = slice(max(0, dy), h + min(0, dy)), slice(max(0, -dy), h + min(0, -dy))
    xs, xd = slice(max(0, dx), w_ + min(0, dx)), slice(max(0, -dx), w_ + min(0, -dx))
    out[ys, xs] = a[yd, xd]
    return out


def best_shift(now, still, r=3):
    """(dx, dy) within r pixels that best lays mask `still` over mask `now` (the smallest on a tie)."""
    best, score = (0, 0), (still & now).sum()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            s = (moved(still, dx, dy) & now).sum()
            if s > score or (s == score and abs(dx) + abs(dy) < abs(best[0]) + abs(best[1])):
                best, score = (dx, dy), s
    return best


def head_of(body):
    """The top 15 rows of a body mask: its head."""
    out = np.zeros_like(body)
    ys = np.flatnonzero(body.any(1))
    if len(ys):
        out[ys.min():ys.min() + 15] = body[ys.min():ys.min() + 15]
    return out


def trunk_of(body):
    """The middle of a body mask, below the head and between the arms."""
    out = np.zeros_like(body)
    out[24:48, 22:42] = body[24:48, 22:42]
    return out


def hand_end(mask):
    """Where an arm (its arm guard's mask) ends: the middle of its lowest rows, or None."""
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return None
    low = ys >= ys.max() - 3
    return np.array([xs[low].mean(), ys[low].mean()])


def walk_frame(cells, frame):
    """The four facings (S, N, E, W) of one walk frame of a state (frame-major, as read_dmi
    gives them); a state with fewer frames gives its first."""
    if len(cells) >= 4 * (frame + 1):
        return cells[4 * frame:4 * frame + 4]
    return cells[:4] if len(cells) >= 4 else cells


class Template:
    """Human.dmi's body and the original iron set's silhouettes, which say where a chest,
    a shield or a sword goes on the shared body in each facing.
    frame: the walk frame (0-2) they come from (the original walks in three).
    swing: radians the held weapon is turned about the hand, outward (an attack's strike)
    or, negative, back over the shoulder (the wind-up)."""

    def __init__(self, frame=0, swing=0.0):
        self.swing = swing
        metal = rm.read_dmi(os.path.join(rm.ICONS, "MetalObjects.dmi"))
        self.M = {k: walk_frame(v, frame) for k, v in metal.items()}
        stand = {k: walk_frame(metal[k], 0) for k in ("MLeftArm", "MRightArm")}
        self.frames = walk_frame(rm.read_dmi(os.path.join(rm.ICONS, "Human.dmi"))[""], frame)
        self.heads, self.ref, self.hand_moved = {}, {}, {}
        for i, d in enumerate(rm.DIRS):
            body = rm.up(self.frames[i])
            self.heads[d] = Head(body, d)
            al = lambda k: rm.up(self.M[k][i])[..., 3] > 0
            self.ref[d] = dict(body=body[..., 3] > 0, chest=al("Metal ChestPlate"), legs=al("Metal Leggings"),
                               arm_L=al("MLeftArm"), arm_R=al("MRightArm"), shield=al("Metal Buckler"), sword=al("Sword"))
            # How far each hand has swung from where it is standing (the bottom of the
            # original arm guard): the original's sword and shield overlays stand still in
            # some facings while the arms swing, so held things follow the hand instead.
            self.hand_moved[d] = {}
            for side, k in (("L", "MLeftArm"), ("R", "MRightArm")):
                now, still = hand_end(al(k)), hand_end(rm.up(stand[k][i])[..., 3] > 0)
                self.hand_moved[d][side] = now - still if now is not None and still is not None else np.zeros(2)
        # Helmets and chests are drawn on the standing body (their shapes keep to its brow,
        # eyes and neck) and moved as the head or torso moves in this walk frame.
        # The upper body rises and falls with the head (the whole silhouette from crown to
        # shoulders moves as one); the trunk's own sideways sway is read off its middle.
        self.still = self if frame == 0 else Template(0)
        self.moved = {}
        for d in rm.DIRS:
            head = best_shift(head_of(self.ref[d]["body"]), head_of(self.still.ref[d]["body"]))
            sway = best_shift(trunk_of(self.ref[d]["body"]), trunk_of(self.still.ref[d]["body"]))[0]
            self.moved[d] = {"head": head, "torso": (sway, head[1])}

    def on_still(self, d, part, draw):
        """draw(template) on the standing body, moved as `part` ("head" or "torso") is in this frame."""
        return moved(draw(self.still), *self.moved[d][part])

    def grip(self, d, follow=True):
        """Right hand: (hand point, unit axis up the weapon, unit 'outer' side, held behind the body).
        Measured on the original Sword overlay; the north and west views mirror south and east.
        follow: in the front and back views, where that overlay stands still through the walk,
        the hand point follows the swinging arm (False: where the overlay itself is)."""
        base = {"S": "S", "N": "S", "E": "E", "W": "E"}[d]
        ys, xs = np.nonzero(self.ref[base]["sword"])
        P = np.stack([xs + 0.5, ys + 0.5], 1)
        c = P.mean(0)
        ax = np.linalg.svd(P - c)[2][0]
        t = (P - c) @ ax
        e1, e2 = c + ax * t.min(), c + ax * t.max()
        ay, axx = np.nonzero(self.ref[base]["arm_R"])
        ac = np.array([axx.mean() + 0.5, ay.mean() + 0.5])
        hand, tip = (e1, e2) if np.linalg.norm(e1 - ac) < np.linalg.norm(e2 - ac) else (e2, e1)
        axis = (tip - hand) / np.linalg.norm(tip - hand)
        if d != base:
            hand, axis = np.array([64 - hand[0], hand[1]]), np.array([-axis[0], axis[1]])
        if follow and d in ("S", "N"):
            hand = hand + self.hand_moved[d]["R"]
        outer = np.array([-axis[1], axis[0]])
        if outer[0] * (hand[0] - 32) < 0:
            outer = -outer
        if self.swing:
            # Positive turns outward, negative back over the head; side views turn the way the
            # body faces. A chop seen from behind comes down in front of the body, hidden by it.
            a = self.swing
            if d in ("E", "W") and outer[0] * (1 if d == "E" else -1) < 0:
                a = -a
            c, s = np.cos(a), np.sin(a)
            axis, outer = axis * c + outer * s, outer * c - axis * s
            return hand, axis, outer, d == "W" or (d == "N" and self.swing < -1.5)
        return hand, axis, outer, d == "W"

    def shield_at(self, d, follow=True):
        """Left forearm: (centre, view): front (S, W), back (N, seen edge-on) or behind (E).
        follow: the shield moves with the swinging arm through the walk (the original's
        shield overlay stands still)."""
        base = {"S": "S", "N": "S", "E": "W", "W": "W"}[d]
        ys, xs = np.nonzero(self.ref[base]["shield"])
        c = np.array([xs.mean() + 0.5, ys.mean() + 0.5])
        if d != base:
            c = np.array([64 - c[0], c[1]])
        if follow:
            c = c + self.hand_moved[d]["L"]
        return c, {"S": "front", "W": "front", "N": "back", "E": "behind"}[d]


def erode(m, n=1):
    for _ in range(n):
        p = np.pad(m, 1)
        m = m & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m


def ellipse(c, rx, ry):
    yy, xx = np.mgrid[0:64, 0:64]
    return ((xx + 0.5 - c[0]) / rx) ** 2 + ((yy + 0.5 - c[1]) / ry) ** 2 <= 1.0


def dim(ramp, k=1):
    """The same ramp k steps darker (for bands and seams)."""
    return [ramp[0]] * k + ramp[:5 - k]


# ---------------------------------------------------------------------------
# chest armour
# ---------------------------------------------------------------------------

def skirt(T, d, depth, flare=0.4):
    """Below the breastplate to `depth` rows past the top of the hips, as wide as the hips
    and flaring a little; the arms hanging beside it stay in front of it."""
    r = T.ref[d]
    ys = np.nonzero(r["chest"])[0]
    top = ys.max() + 1
    ly = np.nonzero(r["legs"])[0]
    hips = np.flatnonzero(r["legs"][ly.min()])
    x0, x1 = hips.min(), hips.max()
    m = empty()
    for y in range(top, min(63, ly.min() + depth)):
        f = int(flare * (y - top))
        m[y, max(0, x0 - f):min(64, x1 + 1 + f)] = True
    arms = dilate(r["arm_L"] | r["arm_R"])
    body = r["body"]
    beside = body & ~(np.arange(64)[None, :] >= x0) | body & ~(np.arange(64)[None, :] <= x1)
    return m & ~arms & ~beside


def pauldrons(T, d, big=1.0):
    """Shoulder plates: a small dome on the point of each shoulder, over the top of the arm,
    with one lame below it. (dome mask, lame mask)."""
    r = T.ref[d]
    chest, arms = r["chest"], r["arm_L"] | r["arm_R"]
    top = np.nonzero(chest)[0].min()
    yy = np.arange(64)[:, None] * np.ones((1, 64))
    if d in ("S", "N"):
        y = top + 6
        xs = np.flatnonzero((chest | arms)[y])
        centres = [(xs.min() + 3.6, y), (xs.max() + 1 - 3.6, y)]
    else:   # profile: the near shoulder, where the arm starts
        ay = np.nonzero(arms)[0].min()
        xs = np.flatnonzero(arms[ay + 1])
        centres = [((xs.min() + xs.max() + 1) / 2.0, ay + 1)]
    dome_m, lame_m = empty(), empty()
    for cx, cy in centres:
        dome_m |= ellipse((cx, cy), 4.2 * big, 3.3 * big) & (yy <= cy + 0.5)
        lame_m |= ellipse((cx, cy + 0.6), 3.9 * big, 3.3 * big) & (yy > cy + 0.5) & (yy <= cy + 2.6 * big)
    return dome_m, lame_m


def pattern_levels(mask, kind):
    """Surface patterns as levels over the cylinder shading: mail rings, scales, plate bands."""
    u = rm.runs(mask)
    yy, xx = np.mgrid[0:64, 0:64]
    lvl = np.where(u < 0.34, 3, np.where(u > 0.7, 1, 2))
    if kind == "mail":
        lvl = lvl - ((xx + yy) % 2)
        lvl[(yy % 2 == 0) & ((xx + yy) % 2 == 0)] += 1
    elif kind == "scale":
        ly = yy % 3
        lx = (xx + ((yy // 3) % 2) * 2) % 4
        lvl = lvl + (ly == 0) - ((ly == 2) & ((lx == 0) | (lx == 3))) * 2
    elif kind == "bands":
        lvl = lvl - (yy % 4 == 0) * 2 + (yy % 4 == 1)
    return np.clip(lvl, 1, 4)


def chest_layer(T, d, style, tier):
    r = T.ref[d]
    ramp = RAMPS[tier] if style != "leather" or tier in LEATHER_TIERS else RAMPS["leather"]
    chest = r["chest"]
    cx = int(round(np.nonzero(chest)[1].mean()))
    parts = []
    if style == "plate":
        lames = skirt(T, d, 6, 0.3)
        parts += [(lames, ramp, pattern_levels(lames, "bands")), (chest, ramp, "round")]
        if d == "S":
            ys = np.nonzero(chest)[0]
            ridge = empty()
            ridge[ys.min() + 4:ys.max() - 1, cx] = True
            parts.append((ridge & chest, [ramp[0], ramp[4], ramp[4], ramp[4], ramp[4]], "flat"))
        dome_m, lame_m = pauldrons(T, d)
        parts += [(lame_m, dim(ramp, 1), "round"), (dome_m, ramp, "round")]
    elif style == "banded":   # dwarvish: banded plate, broad riveted pauldrons, a heavy belt
        lames = skirt(T, d, 7, 0.4)
        body = chest | lames
        parts.append((body, ramp, pattern_levels(body, "bands")))
        belt = lames & (np.arange(64)[:, None] <= np.nonzero(lames)[0].min() + 1)
        parts.append((belt, RAMPS["leather"], "flat"))
        dome_m, lame_m = pauldrons(T, d, 1.12)
        parts += [(lame_m, dim(ramp, 1), "round"), (dome_m, ramp, "round", band(dome_m, 1) & (np.arange(64)[None, :] % 3 == 0))]
        if d in ("S", "E", "W"):
            by = np.nonzero(belt)[0].min()
            bx = cx if d == "S" else (np.flatnonzero(belt[by]).max() - 1 if d == "E" else np.flatnonzero(belt[by]).min() + 1)
            buckle = empty()
            buckle[by:by + 2, bx - 1:bx + 1] = True
            parts.append((buckle, RAMPS["gold"], "round"))
    elif style in ("mail", "scale"):
        coat = chest | skirt(T, d, 11, 0.45)
        hem = coat & ~np.pad(coat, ((0, 1), (0, 0)))[1:]
        if style == "mail":
            coat &= ~(hem & (np.arange(64)[None, :] % 2 == 0))
        parts.append((coat, ramp, pattern_levels(coat, style)))
        belt = skirt(T, d, 1, 0) & coat
        parts.append((belt, RAMPS["leather"], "flat"))
    elif style == "leather":
        coat = chest | skirt(T, d, 4, 0.3)
        parts.append((coat, ramp, "round"))
        if d in ("S", "N"):
            st = empty()
            ys = np.nonzero(coat)[0]
            st[ys.min() + 2:ys.max(), cx] = (np.arange(ys.min() + 2, ys.max()) % 2 == 0)
            parts.append((st & coat, [ramp[0], ramp[4], ramp[4], ramp[4], ramp[4]], "flat"))
        belt = skirt(T, d, 1, 0) & coat
        parts.append((belt, dim(RAMPS["leather"], 1), "flat"))
        studs = coat & ~belt & (np.arange(64)[:, None] % 4 == 1) & (np.arange(64)[None, :] % 4 == 2)
        parts.append((studs, RAMPS[STUDS.get(tier, "iron")], np.full((64, 64), 4)))
    return render(parts)


CHESTS = ["plate", "banded", "mail", "scale", "leather"]


# ---------------------------------------------------------------------------
# shields
# ---------------------------------------------------------------------------

def shield_shape(style, c, scale=1.0):
    yy, xx = np.mgrid[0:64, 0:64]
    x, y = (xx + 0.5 - c[0]) / scale, (yy + 0.5 - c[1]) / scale
    r = np.hypot(x, y)
    if style == "round":
        return r <= 12.2
    if style == "buckler":
        return r <= 7.4
    if style == "kite":
        top = np.hypot(x, y + 5) <= 9.2
        t = np.clip((y + 5) / 22.0, 0, 1)
        low = (y >= -5) & (y <= 17) & (np.abs(x) <= 9.2 * (1 - t) ** 0.9)
        return top | low
    if style == "heater":
        upper = (y >= -11) & (y <= 1) & (np.abs(x) <= 10)
        t = np.clip((y - 1) / 13.0, 0, 1)
        lower = (y > 1) & (y <= 14) & (np.abs(x) <= 10 * np.sqrt(np.clip(1 - t ** 1.6, 0, 1)))
        return upper | lower
    if style == "tower":
        box = (np.abs(x) <= 11) & (y >= -16) & (y <= 15)
        corner = (np.abs(x) > 8) & ((y < -13) | (y > 12))
        return box & ~(corner & (np.hypot(np.abs(x) - 8, np.where(y < 0, y + 13, y - 12)) > 3))
    raise KeyError(style)


def shield_layer(T, d, style, tier, at=None, body=None, scale=1.0):
    """at: where the forearm is on the wearer (default: the template); body: the wearer's
    mask, which hides a shield on the far arm; scale: the size of the shield (small folk)."""
    c, view = T.shield_at(d)
    if at is not None:
        c = np.array(at, float)
    body = T.ref[d]["body"] if body is None else body
    ramp = RAMPS[tier]
    wood = RAMPS["wood"]
    yy, xx = np.mgrid[0:64, 0:64]
    x, y = (xx + 0.5 - c[0]) / scale, (yy + 0.5 - c[1]) / scale
    shape = lambda st, cc: shield_shape(st, cc, scale)
    if view == "back":   # seen from behind, almost edge-on: the back of the board and its strap
        full = shape(style, c)
        m = empty()
        for yr in range(64):
            xs = np.flatnonzero(full[yr])
            if len(xs):
                w = max(1, int(round((xs.max() - xs.min() + 1) * 0.42)))
                mid = (xs.min() + xs.max()) / 2.0
                m[yr, int(mid - w / 2):int(mid - w / 2) + w] = True
        strap = m & (np.abs(y) <= 1.2)
        return render([(m, dim(wood, 1), "round"), (m & ~erode(m, 1), ramp, "flat"), (strap, RAMPS["leather"], "flat")])
    m = shape(style, c)
    low = np.nonzero(m)[0].max()
    if low > 61:   # on a short body a tall shield is carried higher, clear of the ground
        c = c - np.array([0.0, low - 61])
        x, y = (xx + 0.5 - c[0]) / scale, (yy + 0.5 - c[1]) / scale
        m = shape(style, c)
    rim = m & ~erode(m, 2 if style != "buckler" else 1)
    face = m & ~rim
    parts = []
    if style in ("round", "tower"):
        planks = face & (np.abs(x) % 4 < 0.9)
        parts += [(face, wood, "round"), (planks, dim(wood, 1), "flat")]
        if style == "tower":
            band_m = face & (np.abs(y) <= 1.2)
            parts.append((band_m, ramp, "flat"))
        boss = np.hypot(x, y) <= 3.2
        parts += [(rim, ramp, "round", rim & ((xx + yy) % 4 == 0)), (boss & m, ramp, "round")]
    elif style == "buckler":
        boss = np.hypot(x, y) <= 3.4
        ring = (np.hypot(x, y) > 3.4) & (np.hypot(x, y) <= 4.4)
        parts += [(face, ramp, "round"), (ring & m, dim(ramp, 1), "flat"), (rim, ramp, "round"), (boss, ramp, "round")]
    elif tier in ("dragon", "chitin", "dragonbone") and style in ("kite", "heater"):   # its beast's face in place of a herald's colours
        parts += [(face, dim(ramp if tier != "dragonbone" else RAMPS["dragon"], 1), "round"), (rim, RAMPS["dragonhorn"] if tier == "dragon" else ramp, "round")]
        parts += shield_emblem(tier, x, y, face)
    elif style == "kite":
        cross = face & ((np.abs(x) <= 1.2) | (np.abs(y + 3) <= 1.2))
        parts += [(face, RAMPS["red"], "round"), (cross, RAMPS["gold"], "flat"), (rim, ramp, "round")]
    elif style == "heater":
        chevron = face & (np.abs(y - (-1 + 0.9 * np.abs(x))) <= 1.8)
        parts += [(face, RAMPS["blue"], "round"), (chevron, RAMPS["gold"], "flat"), (rim, ramp, "round")]
    out = theme(render(parts), "shield", tier, d)
    if view == "behind":   # on the far arm: only what shows past the body
        out[body] = 0
    return out


SHIELDS = ["round", "kite", "heater", "tower", "buckler"]


# ---------------------------------------------------------------------------
# weapons
# ---------------------------------------------------------------------------

def weapon_layer(T, d, style, tier, at=None, body=None, scale=1.0):
    """at: the wearer's right hand (default: the template's); body: the wearer's mask, which
    closes the fist over the grip and hides a weapon held behind the body; scale: weapon
    size (goblins and kobolds carry smaller ones, dwarves full-size ones)."""
    hand, axis, outer, behind = T.grip(d)
    if at is not None:
        hand = np.array(at, float)
    body = T.ref[d]["body"] if body is None else body
    if style in POLE:   # long hafts stand more upright so they stay in the tile
        axis = axis + np.array([0.0, -POLE[style]])
        axis /= np.linalg.norm(axis)
        outer = np.array([-axis[1], axis[0]])
        if outer[0] * (hand[0] - 32) < 0:
            outer = -outer
    yy, xx = np.mgrid[0:64, 0:64]
    hx, hy = xx + 0.5 - hand[0], yy + 0.5 - hand[1]   # from the hand: where the fist is
    o = hand + axis * GRIP_SHIFT.get(style, 0.0) * scale   # the weapon's own origin, the top of its grip
    px, py = xx + 0.5 - o[0], yy + 0.5 - o[1]
    t = (px * axis[0] + py * axis[1]) / scale
    s = (px * outer[0] + py * outer[1]) / scale
    lit = 1.0 if (outer @ np.array([-1.0, -1.0])) > 0 else -1.0     # which side faces the top-left light
    side_lvl = np.where(s * lit > 0.55, 3, np.where(s * lit < -0.55, 1, 2))
    metal, wood, grip = RAMPS[tier], RAMPS["wood"], RAMPS["leather"]
    fittings = metal if tier not in ("wood", "leather") else RAMPS["iron"]
    kind = WTHEME.get(tier)
    guard_r = pommel_r = fittings
    if kind == "dragon":   # a scale-wrapped grip, a guard of horns, a claw for a pommel
        grip, guard_r, pommel_r = RAMPS["dragon"], RAMPS["dragonhorn"], RAMPS["dragonhorn"]
    elif kind == "spider":   # silk-bound grip, a guard of little legs, a red eye for a pommel
        grip, guard_r, pommel_r = RAMPS["silk"], RAMPS["chitin"], RAMPS["spidereye"]
    elif kind == "bone":   # dragonhide grip, horn guard and haft, a skull for a pommel
        grip, guard_r, pommel_r, wood = RAMPS["dragonhide"], RAMPS["dragonhorn"], RAMPS["dragonbone"], RAMPS["dragonhorn"]
    seg = lambda t0, t1, h: (t >= t0) & (t < t1) & (np.abs(s) <= h)
    parts = []

    def tsline(t0, s0, t1, s1, w):
        """A stroke in the weapon's own frame (t along it, s across), w wide."""
        dt, ds = t1 - t0, s1 - s0
        k = np.clip(((t - t0) * dt + (s - s0) * ds) / (dt * dt + ds * ds), 0, 1)
        return (t - t0 - k * dt) ** 2 + (s - s0 - k * ds) ** 2 <= (w * (1 - 0.6 * k)) ** 2

    def blade(t0, t1, w, curve=0.0):
        curve += {"dragonfang": 0.012, "spiderfang": 0.008}.get(tier, 0.0)   # a tooth's curve, a fang's
        sc = s + curve * np.clip(t - t0, 0, None) ** 2
        taper = np.clip((t1 + 1.5 - t) / 6.0, 0.3, 1.0)
        m = (t >= t0) & (t <= t1 + 1) & (np.abs(sc) <= w * taper)
        if kind == "spider":   # barbed: notches up both edges
            m &= ~((np.abs(sc) > w * taper - 1.1) & (np.floor(t) % 3 == 0) & (t > t0 + 2) & (t < t1 - 1))
        lv = np.where(sc * lit > 0.5, 3, np.where(sc * lit < -0.5, 1, 2))
        lv[m & (sc * lit > w * taper - 1.0) & (t > t0 + 3)] = 4
        return m, lv

    def hilt(grip_len, guard, pommel=True):
        out = [(seg(-grip_len, 0.6, 1.1), grip, side_lvl)]
        out.append((seg(0.6, 2.0, guard), guard_r, side_lvl))
        if kind in ("dragon", "bone"):   # the guard's ends sweep back as horns
            for k in (-1, 1):
                out.append((tsline(1.3, k * guard, -2.4, k * (guard + 2.2), 1.1), guard_r, side_lvl))
        elif kind == "spider":   # or reach forward as a spider's legs
            for k in (-1, 1):
                out.append((tsline(1.3, k * guard, 4.0, k * (guard + 1.6), 0.9), guard_r, side_lvl))
        if pommel:
            pm = (t + grip_len + 1.2) ** 2 + s ** 2 <= 2.3 ** 2
            out.append((pm, pommel_r, "round"))
            if kind == "dragon":   # a claw
                out.append((tsline(-grip_len - 2.5, 0, -grip_len - 5.0, 1.2, 0.9), guard_r, side_lvl))
            elif kind == "bone":   # a skull: its eye sockets
                out.append((pm & ((t + grip_len + 1.0) ** 2 + (np.abs(s) - 0.9) ** 2 <= 0.5 ** 2), [RAMPS["dragonbone"][0]] * 5, "flat"))
        return out

    def haft(t0, t1, h=1.1):
        if kind in ("dragon", "spider"):   # bound with the beast's own: scale or silk bands up the haft
            bands = seg(t0, t1, h) & (np.floor(t) % 5 == 0)
            return [(seg(t0, t1, h), wood, side_lvl), (bands, grip, side_lvl)]
        return (seg(t0, t1, h), wood, side_lvl)

    if style == "arming sword":
        m, lv = blade(2.0, 25, 1.8)
        parts = hilt(5, 4.5) + [(m, metal, lv)]
    elif style == "longsword":
        m, lv = blade(2.0, 33, 2.0)
        parts = hilt(8, 5.5) + [(m, metal, lv)]
    elif style == "scimitar":
        m, lv = blade(2.0, 24, 2.3, curve=0.014)
        parts = hilt(5, 3.5) + [(m, metal, lv)]
    elif style == "dagger":
        m, lv = blade(1.8, 12, 1.5)
        parts = hilt(4, 3.0) + [(m, metal, lv)]
    elif style in ("hand axe", "battle axe"):
        top = 24 if style == "hand axe" else 28
        parts = [haft(-6 if style == "hand axe" else -9, top + 1)]
        for k in ((1,) if style == "hand axe" else (1, -1)):
            sk = s * k
            smax = 9.2 - 0.3 * (t - (top - 3)) ** 2
            head = (t >= top - 10) & (t <= top + 1) & (sk >= 0.5) & (sk <= smax)
            if kind == "spider":   # a serrated edge
                head &= ~((sk > smax - 1.3) & (np.floor(t) % 2 == 0))
            edge = head & (sk > smax - 2.2)
            parts += [(head, metal, np.where(t < top - 4, 1, 2) + (sk < 3)), (edge, metal, np.full((64, 64), 3) + (t > top - 6))]
        if style == "hand axe":
            parts.append(((t >= top - 5) & (t <= top - 2) & (s <= -0.5) & (s >= -4), metal, side_lvl))
    elif style == "warhammer":
        parts = [haft(-7, 21)]
        head = (t >= 19.5) & (t <= 27.5) & (np.abs(s) <= 5.6)
        lv = np.where(t < 21.5, 3, np.where(t > 25.5, 1, 2))
        lv[head & (np.abs(s) > 4.4)] = 1
        lv[head & (np.abs(t - 23.5) < 0.6)] = 1
        parts += [(head, metal, lv), ((np.abs(t - 23.5) < 0.7) & (np.abs(s) < 5.6) & (np.abs(s) % 3 < 0.8), RAMPS["gold"], np.full((64, 64), 4))]
    elif style == "mace":
        parts = [haft(-5, 18)]
        head = ((t - 22.0) / 4.6) ** 2 + (s / 3.4) ** 2 <= 1.0
        flanges = (np.abs(s) <= 5.2) & ((np.abs(t - 19.5) < 0.7) | (np.abs(t - 22) < 0.7) | (np.abs(t - 24.5) < 0.7))
        parts += [(head | flanges, metal, side_lvl), ((t >= 26.3) & (t <= 28.5) & (np.abs(s) <= 1.0), metal, side_lvl)]
    elif style == "morning star":
        parts = [haft(-5, 17)]
        ball = (t - 21.5) ** 2 + s ** 2 <= 4.2 ** 2
        spikes = empty()
        for a in np.linspace(0, 2 * np.pi, 8, endpoint=False):
            dt, ds = np.cos(a), np.sin(a)
            along = (t - 21.5) * dt + s * ds
            across = -(t - 21.5) * ds + s * dt
            spikes |= (along > 3.8) & (along < 7.0) & (np.abs(across) < 0.9 * (7.0 - along) / 3.2)
        parts += [(ball, metal, side_lvl), (spikes, metal, np.full((64, 64), 3))]
    elif style == "spear":
        parts = [haft(-16, 39, 0.95), (seg(36, 39.5, 1.5), metal, side_lvl)]
        tt = np.clip((t - 39) / 12.0, 0, 1)
        leaf = (t >= 39) & (t <= 51) & (np.abs(s) <= 2.8 * np.sin(np.pi * tt) ** 0.7 + 0.3)
        parts.append((leaf, metal, side_lvl + (leaf & (s * lit > 0.5) & (t > 42))))
    elif style == "halberd":
        parts = [haft(-14, 40, 0.95)]
        smax = 7.5 - 0.25 * (t - 33) ** 2
        blade_m = (t >= 28) & (t <= 38) & (s >= 0.5) & (s <= smax)
        spike = (t >= 38) & (t <= 47) & (np.abs(s) <= 1.5 * np.clip((47.5 - t) / 4, 0.3, 1))
        hook = (t >= 31) & (t <= 33) & (s <= -0.5) & (s >= -4.5 + (t - 31))
        parts += [(blade_m, metal, np.where(s > smax - 2, 3, 2)), (spike, metal, side_lvl), (hook, metal, side_lvl)]
    elif style == "pickaxe":
        parts = [haft(-6, 22)]
        # a T: the head arches over the haft, thick at its socket, tapering to points that curve
        # down towards the hand (the original game's picks)
        tc = 23.0 - 0.04 * s ** 2
        head = (np.abs(s) <= 9.5) & (np.abs(t - tc) <= 2.4 * np.clip(1 - np.abs(s) / 10.0, 0.2, 1))   # narrow enough to stand upright inside the picture
        socket = (np.abs(s) <= 2.2) & (t >= 19.5) & (t <= 25.8)
        parts.append((head | socket, metal, np.where(t > tc, 3, 1)))
    elif style == "bow":   # a recurve bow upright in the fist: limbs bent back, tips curling forward, the string taut
        L = 17.0
        so = s - 2.0   # held a little out from the body, so the arm doesn't hide it
        bend = 0.02 * t ** 2 - np.clip(np.abs(t) - (L - 3.5), 0, None) * 1.3
        limb = (np.abs(t) <= L) & (np.abs(so + bend) <= np.clip(2.4 - np.abs(t) / L * 1.4, 0.9, 2.4))
        tip_s = -(0.02 * L ** 2 - 3.5 * 1.3)
        string = (np.abs(t) <= L - 0.6) & (np.abs(so - tip_s) <= 0.5)
        tips = limb & (np.abs(t) > L - 3.5)
        parts = [(string, RAMPS["silk"], "flat"), (limb, metal, side_lvl), (tips, guard_r, side_lvl), (seg(-2.6, 2.6, 1.9), grip, side_lvl)]
    else:
        raise KeyError(style)
    parts = [q for p in parts for q in (p if isinstance(p, list) else [p])]   # a themed haft is two parts
    # the fist closes over the grip: leave the hand's own pixels showing
    fist = (hx ** 2 + hy ** 2 <= 2.6 ** 2) & body
    parts = [(p[0] & ~fist,) + tuple(p[1:]) for p in parts]
    out = render(parts)
    if tier == "spiderfang":   # its venom along the edge
        edge = (out[..., :3] == np.array(RAMPS["spiderfang"][4], np.uint8)).all(-1) & (out[..., 3] > 0)
        out[edge, :3] = RAMPS["venom"][3]
    if behind:
        out[body] = 0
    return out


POLE = {"spear": 1.4, "halberd": 1.4, "longsword": 0.7, "bow": 2.4, "pickaxe": 2.6}   # a pick stands upright, its head a T over the fist
# Bladed weapons slide up their axis so the fist closes on the middle of the grip, the guard
# just above it (at 0 the hand sat at the guard and the grip and pommel hung below the fist).
# Half the grip's length (hilt(grip_len, ...) in weapon_layer).
GRIP_SHIFT = {"arming sword": 2.2, "longsword": 3.7, "scimitar": 2.2, "dagger": 1.7}
WEAPONS = ["arming sword", "longsword", "scimitar", "dagger", "hand axe", "battle axe", "warhammer", "mace",
           "morning star", "spear", "halberd", "pickaxe", "bow"]


# ---------------------------------------------------------------------------
# leg armour
# ---------------------------------------------------------------------------

def fractions(m):
    """Row position within a region, 0 at its top row and 1 at its bottom row."""
    ys = np.nonzero(m)[0]
    y0, y1 = ys.min(), ys.max()
    return np.clip((np.arange(64)[:, None] - y0) / max(1, y1 - y0), 0, 1) * np.ones((1, 64))


def run_centres(m, y):
    """Centres of the horizontal runs of m in row y (one per leg or arm)."""
    xs = np.flatnonzero(m[y])
    if not len(xs):
        return []
    return [seg.mean() + 0.5 for seg in np.split(xs, np.flatnonzero(np.diff(xs) > 1) + 1)]


def leg_layer(T, d, style, tier):
    """Leggings on the template's legs (the original Metal Leggings' outline): hips,
    legs and feet by height. plate, mail, leather, scale, cloth; boots: feet only."""
    L = T.ref[d]["legs"]
    f = fractions(L)
    hips, feet = L & (f < 0.3), L & (f > 0.8)
    legs = L & ~hips & ~feet
    ramp = RAMPS[tier]
    leather = RAMPS[tier] if tier in LEATHER_TIERS else RAMPS["leather"]
    boots = dim(RAMPS["leather"], 1)
    knee_y = int(np.round(np.nonzero(L & (f > 0.5) & (f < 0.58))[0].mean()))
    cops = empty()
    for cx in run_centres(L, knee_y):
        cops |= ellipse((cx, knee_y + 0.5), 2.6, 2.0)
    cops &= L
    if style == "plate":
        parts = [(hips, ramp, pattern_levels(hips, "bands")), (legs, ramp, "round"), (cops, ramp, "round"), (feet, dim(ramp, 1), "round")]
    elif style == "mail":
        parts = [(hips | legs, ramp, pattern_levels(hips | legs, "mail")), (feet, boots, "round")]
    elif style == "leather":
        parts = [(hips | legs, leather, "round"), (cops, dim(leather, 1), "flat"), (feet | (L & (f > 0.7)), boots, "round")]
    elif style == "scale":
        upper = L & (f < 0.55)
        parts = [(upper, ramp, pattern_levels(upper, "scale")), (L & ~upper & ~feet, ramp, "round"), (cops & ~upper, ramp, "round"),
                 (feet, boots, "round")]
    elif style == "cloth":
        wraps = L & (f >= 0.6) & (f <= 0.8)
        lines = wraps & ((np.arange(64)[:, None] + np.arange(64)[None, :]) % 3 == 0)
        parts = [(L & ~wraps & ~feet, RAMPS["wool"], "round"), (wraps, RAMPS["white"], "round"), (lines, RAMPS["wool"], "flat"),
                 (feet, boots, "round")]
    elif style == "boots":
        parts = [(feet | (L & (f > 0.72)), boots, "round")]
    else:
        raise KeyError(style)
    return theme(render(parts), "legs", tier, d, T=T, knees=cops)


LEGS = ["plate", "mail", "leather", "scale", "cloth"]


# ---------------------------------------------------------------------------
# arm armour (the game's LeftArm / RightArm items)
# ---------------------------------------------------------------------------

def arm_layer(T, d, style, tier, side):
    A = T.ref[d]["arm_" + side]
    if not A.any():   # the far arm in a profile view is hidden behind the body
        return np.zeros((64, 64, 4), np.uint8)
    f = fractions(A)
    upper, lower, hand = A & (f < 0.42), A & (f >= 0.42) & (f <= 0.8), A & (f > 0.8)
    ramp, leather = RAMPS[tier], RAMPS[tier] if tier in LEATHER_TIERS else RAMPS["leather"]
    band_rows = np.nonzero(A & (f > 0.36) & (f < 0.5))[0]
    elbow_y = int(np.round(band_rows.mean())) if len(band_rows) else int(np.nonzero(A)[0].mean())
    cop = empty()
    for cx in run_centres(A, elbow_y):
        cop |= ellipse((cx, elbow_y + 0.5), 2.2, 1.8)
    cop &= A
    if style == "plate":
        parts = [(upper, ramp, "round"), (lower, ramp, "round"), (cop, ramp, "round"), (hand, dim(ramp, 1), "round")]
    elif style == "mail":
        parts = [(upper | lower, ramp, pattern_levels(upper | lower, "mail")), (hand, dim(leather, 1), "round")]
    elif style == "leather":
        straps = lower & ((np.arange(64)[:, None] - elbow_y) % 4 == 2)
        parts = [(lower, leather, "round"), (straps, dim(leather, 2), "flat"), (hand, dim(leather, 1), "round")]
    else:
        raise KeyError(style)
    return theme(render(parts), "arms", tier, d, T=T, knees=cop)


ARMS = ["plate", "mail", "leather"]


def arms_layers(T, d, style, tier):
    return [arm_layer(T, d, style, tier, "L"), arm_layer(T, d, style, tier, "R")]


# ---------------------------------------------------------------------------
# more chest armour
# ---------------------------------------------------------------------------

def chest_layer2(T, d, style, tier):
    """brigandine, lamellar, tabard (over mail), robe (cloth colour in place of a tier)."""
    r = T.ref[d]
    chest = r["chest"]
    cx = int(round(np.nonzero(chest)[1].mean()))
    yy, xx = np.mgrid[0:64, 0:64]
    if style == "brigandine":
        coat = chest | skirt(T, d, 5, 0.3)
        cloth = RAMPS["red"]
        rivets = coat & (xx % 4 == 1) & (yy % 4 == 2)
        edge = coat & ~erode(coat, 1)
        return render([(coat, cloth, "round"), (edge, RAMPS[tier], "flat"), (rivets, RAMPS[tier], np.full((64, 64), 4))])
    if style == "lamellar":
        coat = chest | skirt(T, d, 8, 0.4)
        u = rm.runs(coat)
        lv = np.where(u < 0.34, 3, np.where(u > 0.7, 1, 2)) - (xx % 3 == 0)
        lace = coat & (yy % 5 == 0) & (xx % 3 == 1)
        return render([(coat, RAMPS[tier], np.clip(lv, 1, 4)), (lace, RAMPS["red"], np.full((64, 64), 3))])
    if style == "tabard":
        coat = chest | skirt(T, d, 9, 0.45)
        ys = np.nonzero(coat)[0]
        if d in ("S", "N"):
            panel = coat & (np.abs(xx + 0.5 - (cx + 0.5)) <= 6.5) & (yy >= ys.min() + 3)
        else:
            k = 1 if d == "E" else -1
            panel = coat & ((xx - cx) * k >= -2) & (yy >= ys.min() + 3)
        device = empty()
        if d == "S":
            device = panel & (((np.abs(xx - cx) <= 0) | (np.abs(xx - cx - 1) <= 0)) & (yy >= ys.min() + 6) & (yy <= ys.min() + 16) |
                              (np.abs(yy - (ys.min() + 9)) <= 0.5) & (np.abs(xx + 0.5 - cx) <= 4))
        belt = skirt(T, d, 1, 0) & coat
        return render([(coat, RAMPS[tier], pattern_levels(coat, "mail")), (panel, RAMPS["blue"], "round"),
                       (device, RAMPS["gold"], "flat"), (belt, RAMPS["leather"], "flat")])
    if style == "robe":   # to the ankles: `tier` names a robe from the catalogue (ROBE_LOOK) or a cloth colour
        look = ROBE_LOOK.get(tier, (tier if tier in CLOTH else "blue", "gold"))
        cloth = RAMPS[look[0]]
        coat = chest | skirt(T, d, 17, 0.5)
        coat &= np.arange(64)[:, None] <= 61
        ys = np.nonzero(coat)[0]
        hem = coat & (yy >= ys.max() - 1)
        front = empty()
        if d == "S":
            front = coat & (np.abs(xx + 0.5 - (cx + 0.5)) <= 1) & (yy >= ys.min() + 2)
        elif d in ("E", "W"):   # the opening runs down the front edge
            pad = np.pad(coat, 1)
            edge = coat & ~(pad[1:-1, 2:] if d == "E" else pad[1:-1, :-2])
            front = edge & (yy >= ys.min() + 4)
        sash = skirt(T, d, 1, 0) & coat
        trim = RAMPS[look[1]] if look[1] in RAMPS else dim(cloth, 1)
        sash_r = RAMPS[look[2]] if len(look) > 2 else dim(cloth, 1)
        return theme(render([(coat, cloth, "round"), (hem | front, trim, "flat"), (sash, sash_r, "flat")]), "chest", tier, d, T=T)
    raise KeyError(style)


CHESTS2 = ["brigandine", "lamellar", "tabard", "robe"]

# robe -> (cloth, trim, sash), keyed as in catalogue.py's ROBES: the game's plain silk robes
# (self-coloured hems) and the school robes (a metal or bone trim)
ROBE_LOOK = {"black": ("black", "plain"), "red": ("red", "plain"), "white": ("white", "plain"), "brown": ("wool", "plain"),
             "blue": ("blue", "silver", "silver"), "purple": ("purple", "gold", "gold"), "crimson": ("red", "gold", "black"),
             "gold": ("white", "gold", "gold"), "green": ("green", "gold", "wood"), "grey": ("black", "bone", "bone"),
             "dragonrobe": ("red", "dragon", "dragonhorn"), "spiderrobe": ("black", "silk", "chitin"), "bonerobe": ("wool", "dragonbone", "black")}
ROBE_NAMES = {"black": "Black Robe", "red": "Red Robe", "white": "White Robe", "brown": "Plain Robe", "blue": "Astral Robe",
              "purple": "Chaos Robe", "crimson": "Robe of Flames", "gold": "Priest's Robe", "green": "Druid's Robe",
              "grey": "Necromancer's Robe", "dragonrobe": "Dragonscale Robe", "spiderrobe": "Spider Silk Robe", "bonerobe": "Dragonbone Robe"}


def any_chest(T, d, style, tier):
    return theme(chest_layer(T, d, style, tier) if style in CHESTS else chest_layer2(T, d, style, tier), "chest", tier, d, T=T)


# ---------------------------------------------------------------------------
# beast themes: Dragonscale looks like a dragon, chitin like a spider, dragonbone like a dragon's skeleton
# ---------------------------------------------------------------------------
# theme() runs on every finished piece of a THEMED tier: its surface takes the beast's pattern (scales, a
# carapace's segments, bone grain), then the beast's ornaments go on top (horns, spines, spider legs, eyes,
# fangs, ribs, claws). Shields carry the beast as an emblem (shield_emblem).

def nearest_level(layer, ramp):
    """Each pixel's place on the ramp (0-4), and where it is on the ramp at all (other materials keep theirs)."""
    rgb = layer[..., :3].astype(np.int32)
    pal = np.array(ramp, np.int32)
    dist = ((rgb[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(-1)
    lvl = dist.argmin(-1)
    near = (dist.min(-1) <= 30 ** 2) & (layer[..., 3] > 0)
    return lvl, near


def blobs(mask):
    """The separate pieces of a mask (4-connected): [(ys, xs)]."""
    seen = np.zeros_like(mask, bool)
    out = []
    for y0, x0 in zip(*np.nonzero(mask)):
        if seen[y0, x0]:
            continue
        stack, ys, xs = [(y0, x0)], [], []
        seen[y0, x0] = True
        while stack:
            y, x = stack.pop()
            ys.append(y)
            xs.append(x)
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < mask.shape[0] and 0 <= xx < mask.shape[1] and mask[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True
                    stack.append((yy, xx))
        out.append((np.array(ys), np.array(xs)))
    return out


def spike(base, tip, width=2.4):
    """A tapering spike from base to tip."""
    return stroke([base, tip], [width, 0.6])


def theme(layer, slot, tier, d, T=None, style=None, knees=None):
    kind = THEME.get(tier)
    if not kind:
        return layer
    ramp = RAMPS.get(tier)   # a robe has none of its own: its cloth keeps its look, the ornaments go on
    yy, xx = np.mgrid[0:64, 0:64]
    light = tier in LEATHER_TIERS
    if ramp is not None:
        lvl, near = nearest_level(layer, ramp)
        inner = near & (lvl >= 1)
        if kind == "dragon":   # overlapping scales over every plate: each a U, lit at its crown, rows offset
            tile = np.array([[0, 1, 1, 0], [0, 1, 0, 0], [-2, 0, 0, -2], [0, -2, -2, 0]])
            off = tile[yy % 4, (xx + ((yy // 4) % 2) * 2) % 4]
        elif kind == "spider":   # a carapace in segments, a seam then a glossy edge; on silk, a weave
            off = -1 * ((xx + yy) % 3 == 0) + ((xx - yy) % 6 == 0) if light else -2 * (yy % 5 == 0) + (yy % 5 == 1)
        else:   # bone: a grain along the length
            off = -1 * ((xx * 3 + yy // 4) % 7 == 0)
        if light:
            off = np.clip(off, -1, 1)
        if slot != "shield":
            nl = np.clip(lvl + off, 1, 4)
            pal = np.array(ramp, np.uint8)
            layer = layer.copy()
            layer[inner, :3] = pal[nl[inner]]
    else:
        ramp = RAMPS["chitin" if kind == "spider" else "dragon" if kind == "dragon" else "dragonbone"]
    al = layer[..., 3] > 0
    if not al.any():
        return layer
    ys, xs = np.nonzero(al)
    top, bot, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    cx = (x0 + x1) / 2.0
    horn, ivory = RAMPS["dragonhorn"], RAMPS["dragonbone"]
    parts = []
    side = 1 if d == "E" else -1   # where it faces in a profile; its back is the other way
    if slot == "helmet":
        if kind in ("dragon", "bone"):   # horns swept back, a low crest of spikes
            hr = horn if kind == "dragon" else ivory
            if style == "horned":   # the helm's own horns, in the beast's horn
                hl, hn = nearest_level(layer, RAMPS["horn"])
                layer = layer.copy()
                layer[hn, :3] = np.array(hr, np.uint8)[np.clip(hl[hn], 0, 4)]
            elif d in ("S", "N"):
                for k in (-1, 1):
                    bx = (x0 + 2) if k < 0 else (x1 - 1)
                    pts = [(bx, top + 4), (bx + k * 2.5, top + 1), (bx + k * 4, top - 1.5), (bx + k * 5, top - 2)]
                    parts.append((stroke(pts, [3.0, 2.4, 1.4, 0.6]), hr, "round"))
            else:
                back = x0 + 2 if d == "E" else x1 - 1
                pts = [(back + side * 3, top + 3), (back - side * 1, top + 1), (back - side * 4.5, top), (back - side * 7, top + 1.5)]
                parts.append((stroke(pts, [3.2, 2.6, 1.6, 0.6]), hr, "round"))
            if d in ("S", "N"):
                for k in (-2, 0, 2):
                    parts.append((spike((cx + k + 0.5, top + 1.5), (cx + k + 0.5, top - 0.5 - (k == 0)), 1.8), horn, "round"))
            else:
                for k in (1, 3.5, 6):
                    bx = (x1 - k) if d == "E" else (x0 + k)
                    parts.append((spike((bx + 0.5, top + 1.5), (bx - side * 0.8 + 0.5, top - 1.0), 1.8), horn, "round"))
        if kind == "bone" and style == "great helm":   # a dragon's skull: sockets with embers, nostrils, teeth
            if d == "S":
                eye_y = top + 7
                for ex in (cx - 3, cx + 3):
                    sock = ellipse((ex + 0.5, eye_y + 0.5), 2.0, 1.4)
                    parts.append((sock & al, [ivory[0]] * 5, "flat"))
                    parts.append((ellipse((ex + 0.5, eye_y + 0.6), 0.8, 0.6), RAMPS["ember"], np.full((64, 64), 4)))
                teeth = al & (yy == bot - 1) & (xx % 2 == 0)
                parts.append((teeth, ivory, np.full((64, 64), 4)))
            elif d in ("E", "W"):
                ex = (x1 - 3) if d == "E" else (x0 + 3)
                parts.append((ellipse((ex + 0.5, top + 7.5), 1.6, 1.3) & al, [ivory[0]] * 5, "flat"))
                parts.append((ellipse((ex + 0.5, top + 7.6), 0.7, 0.6), RAMPS["ember"], np.full((64, 64), 4)))
        if kind == "spider" and style == "horned":   # its legs where the horns were: two a side, up and out
            legs = RAMPS["chitin"]
            sides = (-1, 1) if d in ("S", "N") else (-side,)
            for k in sides:
                bx = (x0 + 2) if k < 0 else (x1 - 1)
                if d in ("E", "W"):
                    bx = cx - side * 1.5
                for j, spread in enumerate((1.0, 0.6)):
                    knee = (bx + k * (2.0 + 1.5 * spread), top - 3 - j * 1.5)
                    tip = (bx + k * (5.0 + 3.5 * spread), top + 3 - j * 2)
                    parts.append((stroke([(bx, top + 4), knee], [2.6, 2.0]), legs, "round"))
                    parts.append((stroke([knee, tip], [2.0, 0.6]), legs, "round"))
                    parts.append((ellipse((knee[0], knee[1]), 0.9, 0.9), RAMPS["spidereye"], np.full((64, 64), 2)))
        if kind == "spider":   # a spider's eyes on the brow, fangs at the cheeks
            eye = RAMPS["spidereye"]
            if d == "S":
                ey = top + 7
                for ex in (cx - 2, cx + 1):
                    parts.append((ellipse((ex + 0.5, ey + 0.5), 1.1, 1.1), eye, "round"))
                for ex, dy in ((cx - 4, -1), (cx + 3, -1), (cx - 1, -3), (cx + 2, -3)):
                    parts.append((ellipse((ex + 0.5, ey + dy + 0.5), 0.6, 0.6), eye, np.full((64, 64), 3)))
                for k in (-1, 1):
                    fx0 = cx + k * 3
                    parts.append((stroke([(fx0 + 0.5, bot - 1), (fx0 + k * 0.5 + 0.5, bot + 2), (fx0 - k * 0.8 + 0.5, bot + 4)], [2.2, 1.6, 0.6]), ivory, "round"))
            elif d in ("E", "W"):
                ex = (x1 - 2) if d == "E" else (x0 + 2)
                parts.append((ellipse((ex + 0.5, top + 5.5), 1.1, 1.1), eye, "round"))
                parts.append((ellipse((ex - side * 2 + 0.5, top + 4.5), 0.6, 0.6), eye, np.full((64, 64), 3)))
                parts.append((stroke([(ex + 0.5, bot - 1), (ex + side * 0.8 + 0.5, bot + 2), (ex - side * 0.5 + 0.5, bot + 4)], [2.2, 1.6, 0.6]), ivory, "round"))
    elif slot == "chest" and T is not None:
        dome_m, _ = pauldrons(T, d)
        shoulders = []
        for py, px in blobs(dome_m):
            shoulders.append((px.mean(), py.min()))
        chest = T.ref[d]["chest"]
        cy0, cy1 = np.nonzero(chest)[0].min(), np.nonzero(chest)[0].max()
        ccx = np.nonzero(chest)[1].mean()
        if kind == "dragon":   # spines on the shoulders, and down the back
            for sx, sy in shoulders:
                k = -1 if sx < ccx else 1
                if d in ("E", "W"):
                    k = -side
                for dx, h in ((-1.0, 5.5), (2.6, 4.5)):   # two curved spines a shoulder, leaning out
                    bx = sx + dx * k
                    parts.append((stroke([(bx, sy + 1.5), (bx + k * 1.0, sy - h * 0.55), (bx + k * 2.6, sy - h)], [2.8, 1.8, 0.6]), horn, "round"))
            if d == "N":
                for yv in range(cy0 + 3, cy1 - 1, 4):
                    parts.append((spike((ccx + 0.5, yv + 1.5), (ccx + 0.5, yv - 2.5), 3.0), horn, "round"))
            elif d in ("E", "W"):
                bx = (np.nonzero(chest)[1].min()) if d == "E" else (np.nonzero(chest)[1].max() + 1)
                for yv in range(cy0 + 3, cy1 - 1, 4):
                    parts.append((spike((bx + side * 1.0, yv + 1.5), (bx - side * 2.5, yv - 1.0), 2.2), horn, "round"))
        elif kind == "spider":   # a spider's jointed legs rising from the shoulders
            for sx, sy in shoulders:
                k = -1 if sx < ccx else 1
                if d in ("E", "W"):
                    k = -side
                for j, spread in enumerate((1.0, 0.6)):   # two legs a side: up past the head, then down and out
                    knee = (sx + k * (2.0 + 1.5 * spread), sy - 9 - j * 2)
                    tip = (sx + k * (6.0 + 4.0 * spread), sy - 1 - j * 3)
                    parts.append((stroke([(sx, sy + 1), knee], [2.8, 2.2]), RAMPS["chitin"], "round"))
                    parts.append((stroke([knee, tip], [2.2, 0.6]), RAMPS["chitin"], "round"))
                    parts.append((ellipse((knee[0], knee[1]), 1.0, 1.0), RAMPS["spidereye"], np.full((64, 64), 2)))
        else:   # dragonbone: ribs across the chest, a sternum, claws for pauldrons, a spine
            if d == "S":
                for yv in range(cy0 + 3, cy1 - 1, 3):
                    rib = chest & (yy == yv) & (np.abs(xx + 0.5 - ccx) >= 1.5)
                    parts.append((rib, ivory, np.full((64, 64), 4)))
                parts.append((chest & (np.abs(xx + 0.5 - ccx) < 1.2) & (yy > cy0 + 1), ivory, "round"))
            elif d == "N":
                for yv in range(cy0 + 2, cy1, 3):
                    parts.append((ellipse((ccx, yv + 0.5), 1.4, 1.0), ivory, "round"))
                    parts.append((spike((ccx, yv + 0.5), (ccx, yv - 2.0), 1.6), ivory, "round"))
            for sx, sy in shoulders:
                k = -1 if sx < ccx else 1
                if d in ("E", "W"):
                    k = -side
                for j in range(2):
                    parts.append((stroke([(sx + k * j * 1.5, sy + 1), (sx + k * (3 + j), sy - 1.5), (sx + k * (5 + j * 1.5), sy + 1.5)], [2.4, 1.6, 0.6]), ivory, "round"))
    elif slot in ("legs", "arms") and knees is not None and knees.any():
        for py, px in blobs(knees):
            kx, ky = px.mean(), py.mean()
            out_k = 1 if d == "E" else -1 if d == "W" else (-1 if kx < cx else 1)
            if kind == "spider":
                parts.append((ellipse((kx + 0.5, ky + 0.5), 1.0, 1.0), RAMPS["chitin"], np.full((64, 64), 4)))
            else:
                hr = horn if kind == "dragon" else ivory
                parts.append((spike((kx + 0.5, ky + 0.5), (kx + out_k * 3.0 + 0.5, ky - 1.5), 2.0), hr, "round"))
    if not parts:
        return layer
    deco = render(parts)
    m = deco[..., 3] > 0
    layer = layer.copy()
    layer[m] = deco[m]
    return layer


def shield_emblem(tier, x, y, face):
    """The beast on a themed shield's face: a dragon's eye, a spider's web, a dragon's skull."""
    r = np.hypot(x, y)
    if tier == "dragon":
        iris = ((x / 3.2) ** 2 + (y / 2.0) ** 2 <= 1) & face
        pupil = iris & (np.abs(x) <= 0.5)
        return [(iris, RAMPS["ember"], "round"), (pupil, [RAMPS["dragonhorn"][0]] * 5, "flat")]
    if tier == "chitin":
        ang = np.arctan2(y, x)
        spokes = face & (np.abs(((ang + np.pi) * 8 / (2 * np.pi)) % 1 - 0.5) > 0.42) & (r > 1)
        rings = face & ((np.abs(r - 3) < 0.5) | (np.abs(r - 6) < 0.5))
        body = (r <= 1.6) & face
        return [(spokes | rings, RAMPS["silk"], np.full((64, 64), 3)), (body, RAMPS["spidereye"], "round")]
    skull = (((x / 3.0) ** 2 + ((y + 1) / 3.4) ** 2 <= 1) | ((np.abs(x) <= 1.6) & (y > 0) & (y <= 5))) & face
    sockets = (((np.abs(x) - 1.4) / 1.0) ** 2 + ((y + 1.2) / 0.9) ** 2 <= 1) & skull
    return [(skull, RAMPS["dragonbone"], "round"), (sockets, [RAMPS["dragonbone"][0]] * 5, "flat")]


# ---------------------------------------------------------------------------
# magic: staffs and enchanted weapons, with animated effects
# ---------------------------------------------------------------------------
# A magic item is a solid layer (drawn like any weapon) plus an effect layer for each
# of FRAMES frames: glows (part-transparent rings), and particles (flames, frost,
# sparks, runes, wisps) that move from frame to frame. In the game the effect is its
# own animated overlay state, so it can loop while the solid sprite stays still.

FRAMES = 4
PULSE = [0.7, 1.0, 0.8, 0.55]
MAGIC_BASE = {"rune sword": ("longsword", "runesteel"), "flame sword": ("arming sword", "iron"), "frost axe": ("battle axe", "ice"),
              "storm spear": ("spear", "silver"), "void blade": ("scimitar", "void"), "holy mace": ("mace", "gold")}
STAFFS = ["crystal staff", "orb staff", "skull staff", "flame staff", "nature staff", "dragon staff", "spider staff"]
MAGIC = STAFFS + list(MAGIC_BASE)


def frame_axes(T, d, at, scale, pole, shift=0.0):
    """A held weapon's frame as weapon_layer lays it out; shift: its GRIP_SHIFT (the origin
    returned as `hand` is then the top of the grip, not the fist)."""
    hand, axis, outer, behind = T.grip(d)
    if at is not None:
        hand = np.array(at, float)
    if pole:
        axis = axis + np.array([0.0, -pole])
        axis /= np.linalg.norm(axis)
        outer = np.array([-axis[1], axis[0]])
        if outer[0] * (hand[0] - 32) < 0:
            outer = -outer
    hand = hand + axis * shift * scale
    yy, xx = np.mgrid[0:64, 0:64]
    px, py = xx + 0.5 - hand[0], yy + 0.5 - hand[1]
    t = (px * axis[0] + py * axis[1]) / scale
    s = (px * outer[0] + py * outer[1]) / scale
    return hand, axis, outer, behind, t, s, px, py


def to_xy(hand, axis, outer, t, s, scale=1.0):
    p = hand + (axis * t + outer * s) * scale
    return p[0], p[1]


def glow(src, colour, strength):
    """A soft halo round src: three rings of falling opacity."""
    out = np.zeros((64, 64, 4), np.uint8)
    prev = src
    for alpha in (200, 130, 70, 28):
        ring = dilate(prev) & ~prev
        out[ring, :3] = colour
        out[ring, 3] = np.maximum(out[ring, 3], int(alpha * strength))
        prev = prev | ring
    return out


# An enchanted weapon's glow ring round its blade (the halo above). Off: the user, 2026-10-25, "fix the effects
# good, the aura no" - its runes, flames, frost, lightning, smoke and stars stay.
BLADE_AURA = False


def aura(blade, colour, strength):
    return glow(blade, colour, strength) if BLADE_AURA else np.zeros((64, 64, 4), np.uint8)


def put(fx, x, y, colour, alpha=255):
    xi, yi = int(np.floor(x)), int(np.floor(y))
    if 0 <= xi < 64 and 0 <= yi < 64 and alpha >= fx[yi, xi, 3]:
        fx[yi, xi, :3] = colour
        fx[yi, xi, 3] = alpha


def flames(fx, sources, frame, seed=0, up=(0.0, -1.0), height=5.0):
    """Tongues of fire rising from source points: yellow at the root, orange, red tips;
    each frame different."""
    rng = np.random.default_rng(seed * 31 + frame)
    cols = [(255, 236, 140), (255, 176, 48), (236, 96, 24), (170, 40, 18)]
    for i, (x, y) in enumerate(sources):
        h = height * rng.uniform(0.6, 1.25)
        sway = rng.uniform(-1.2, 1.2)
        n = int(h) + 1
        for k in range(n):
            u = k / max(1, n - 1)
            c = cols[min(3, int(u * 3.99))]
            w = 1 if u > 0.6 else 2 if u > 0.25 else 3
            for j in range(w):
                put(fx, x + up[0] * k + sway * u * 2 + j - (w - 1) / 2.0, y + up[1] * k, c, 255 if u < 0.85 else 170)


def sparkle(fx, x, y, colour, big=False):
    put(fx, x, y, (255, 255, 255))
    if big:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            put(fx, x + dx, y + dy, colour, 210)


def bolt(fx, a, b, rng, colour=(255, 250, 190), edge=(140, 200, 255)):
    """A jagged lightning arc from a to b."""
    pts = [np.array(a, float)]
    n = 5
    for k in range(1, n):
        p = np.array(a, float) + (np.array(b, float) - np.array(a, float)) * k / n
        pts.append(p + rng.normal(0, 1.3, 2))
    pts.append(np.array(b, float))
    for p, q in zip(pts, pts[1:]):
        for t in np.linspace(0, 1, 6):
            x, y = p + (q - p) * t
            put(fx, x + 1, y, edge, 150)
            put(fx, x, y + 1, edge, 150)
            put(fx, x, y, colour)


def staff_solid(T, d, style, at, body, scale):
    """A staff stands upright in the fist; its head sits at t = 33 so the effect above it
    stays inside the tile."""
    hand, axis, outer, behind, t, s, px, py = frame_axes(T, d, at, scale, 2.2)
    wood = RAMPS["wood"]
    lit = 1.0 if (outer @ np.array([-1.0, -1.0])) > 0 else -1.0
    side_lvl = np.where(s * lit > 0.5, 3, np.where(s * lit < -0.5, 1, 2))
    gn = 0.5 * np.sin(t / 3.0) if style == "nature staff" else 0.0      # gnarled
    H = 33.0
    u = t - H                                                            # along the head
    shaft = (t >= -12) & (t < H - 4) & (np.abs(s - gn) <= 1.1)
    parts = [(shaft, wood, side_lvl)]
    head_c = (H, 0.0)
    src = empty()
    if style == "crystal staff":
        prongs = (u >= -6) & (u <= -1) & (np.abs(np.abs(s) - (u + 6) * 0.75 - 0.8) <= 0.75)
        crystal = (np.abs(s) / 3.3 + np.abs(u - 1.0) / 6.5 <= 1.0)
        parts += [(prongs, RAMPS["silver"], side_lvl), (crystal, RAMPS["adamantium"], np.where(s * lit > 0, 4, np.where(s * lit < -1, 1, 2)))]
        src, head_c = crystal, (H + 1, 0.0)
    elif style == "orb staff":
        claw = (u >= -6) & (u <= 0) & (np.abs(np.abs(s) - 4.0 + (u + 6) * 0.15) <= 0.75)
        orb = u ** 2 + s ** 2 <= 4.2 ** 2
        parts += [(claw, RAMPS["gold"], side_lvl), (orb, RAMPS["purple"], "round")]
        src = orb
    elif style == "skull staff":
        cap = (u >= -6) & (u <= -4) & (np.abs(s) <= 2.0)
        skull = ((u - 0.5) / 4.4) ** 2 + (s / 3.9) ** 2 <= 1.0
        jaw = (u >= -4.5) & (u <= -2.5) & (np.abs(s) <= 2.4)
        parts += [(cap, RAMPS["iron"], side_lvl), (skull | jaw, RAMPS["bone"], "round")]
        src, head_c = skull, (H + 0.5, 0.0)
    elif style == "flame staff":
        bowl = (u >= -4) & (u <= 0.5) & (np.abs(s) <= 1.4 + (u + 4) * 0.85)
        parts += [(bowl, RAMPS["iron"], side_lvl)]
        src, head_c = bowl, (H + 0.5, 0.0)
    elif style == "dragon staff":   # a dragon's skull side-on atop the shaft: snout and jaw to the front, horns swept back
        bone, horn = RAMPS["dragonbone"], RAMPS["dragonhorn"]
        def ln(u0, s0, u1, s1, w):
            du, ds = u1 - u0, s1 - s0
            kk = np.clip(((u - u0) * du + (s - s0) * ds) / (du * du + ds * ds), 0, 1)
            return (u - u0 - kk * du) ** 2 + (s - s0 - kk * ds) ** 2 <= (w * (1 - 0.6 * kk)) ** 2
        cranium = ((u - 0.5) / 3.6) ** 2 + ((s + 0.5) / 3.6) ** 2 <= 1.0
        snout = (s >= 1.5) & (s <= 8.5) & (u >= -0.8) & (u <= 2.8 - (s - 1.5) * 0.28)
        jaw = (s >= 1.5) & (s <= 7.5) & (u <= -1.6) & (u >= -3.2 + (s - 1.5) * 0.18)
        teeth = (s >= 2.5) & (s <= 7.5) & (np.abs(u + 1.2) <= 0.4) & (np.floor(s) % 2 == 0)
        horns = ln(2.6, -1.0, 7.5, -5.5, 1.3) | ln(1.5, -2.6, 4.5, -7.0, 1.1)
        socket = ((u - 1.4) ** 2 + (s - 1.0) ** 2 <= 0.9 ** 2)
        bands = (t >= H - 9) & (t < H - 4) & (np.abs(s) <= 1.4) & (np.floor(t) % 2 == 0)
        parts += [(bands, horn, side_lvl), (horns, horn, "round"), (cranium | snout | jaw, bone, "round"),
                  (teeth, bone, np.full((64, 64), 4)), (socket, [horn[0]] * 5, "flat")]
        src, head_c = socket, (H + 1.4, 1.0)
    elif style == "spider staff":   # a spider clutching the head of the staff, its legs wrapped round
        chit, eye = RAMPS["chitin"], RAMPS["spidereye"]
        abdomen = ((u + 0.5) / 3.6) ** 2 + (s / 3.0) ** 2 <= 1.0
        cephal = ((u - 4.0) / 2.0) ** 2 + (s / 1.8) ** 2 <= 1.0
        legs = empty()
        for k in (-1, 1):
            for j, a0 in enumerate((-3.0, -1.0, 1.0, 3.0)):
                knee_u, knee_s = a0 + 1.0, k * 5.2
                tip_u, tip_s = a0 - 1.5, k * 3.2
                for (u0, s0, u1, s1) in ((a0 + 2.0, k * 1.8, knee_u, knee_s), (knee_u, knee_s, tip_u, tip_s)):
                    du, ds = u1 - u0, s1 - s0
                    kk = np.clip(((u - u0) * du + (s - s0) * ds) / (du * du + ds * ds), 0, 1)
                    legs |= (u - u0 - kk * du) ** 2 + (s - s0 - kk * ds) ** 2 <= 0.5 ** 2
        eyes = ((u - 5.0) ** 2 + (np.abs(s) - 0.7) ** 2 <= 0.45 ** 2)
        silk = (t >= H - 9) & (t < H - 4) & (np.abs(s) <= 1.3) & (np.floor(t) % 2 == 0)
        parts += [(silk, RAMPS["silk"], side_lvl), (legs, chit, side_lvl), (abdomen | cephal, chit, "round"), (eyes, eye, np.full((64, 64), 4))]
        src, head_c = abdomen, (H, 0.0)
    elif style == "nature staff":
        branch = empty()
        for k in (-1, 1):
            branch |= (u >= -5) & (u <= 4) & (np.abs(s - k * 0.2 * np.clip(u + 5, 0, None) ** 1.4) <= 0.95)
        seed = u ** 2 + s ** 2 <= 2.2 ** 2
        leaves = ((u + 2) ** 2 + (s - 4.4) ** 2 <= 2.0 ** 2) | ((u - 1.5) ** 2 + (s + 4.8) ** 2 <= 2.0 ** 2) | \
                 ((u - 5) ** 2 + (s - 2.6) ** 2 <= 1.7 ** 2)
        parts += [(branch, wood, side_lvl), (leaves, RAMPS["green"], "round"), (seed, RAMPS["gold"], "round")]
        src = seed
    fist = (px ** 2 + py ** 2 <= 2.6 ** 2) & body
    parts = [(p[0] & ~fist,) + tuple(p[1:]) for p in parts]
    out = render(parts)
    return out, src, (hand, axis, outer, behind, head_c)


def magic_layers(T, d, style, at=None, body=None, scale=1.0):
    """(solid layer, [effect layer per frame]) for a staff or an enchanted weapon."""
    body = T.ref[d]["body"] if body is None else body
    fxs = []
    if style in STAFFS:
        solid, src, (hand, axis, outer, behind, head_c) = staff_solid(T, d, style, at, body, scale)
        hx, hy = to_xy(hand, axis, outer, head_c[0], head_c[1], scale)
        for fr in range(FRAMES):
            p = PULSE[fr]
            rng = np.random.default_rng(fr + 7)
            if style == "crystal staff":
                fx = glow(src, (120, 230, 255), p)
                for k in range(3):
                    a = fr * np.pi / 2 + k * 2.1
                    sparkle(fx, hx + 8 * np.cos(a), hy + 6 * np.sin(a), (140, 230, 255), big=True)
            elif style == "orb staff":
                fx = glow(src, (190, 120, 255), p)
                for k in range(3):
                    a = -fr * np.pi / 2 + k * 2.1
                    sparkle(fx, hx + 7 * np.cos(a), hy + 7 * np.sin(a), (220, 160, 255), big=True)
                put(fx, hx - 1 + (fr % 2), hy - 1, (255, 255, 255))
            elif style == "skull staff":
                fx = glow(src, (110, 255, 120), p * 0.6)
                for k in (-1, 1):   # eyes that burn green
                    ox, oy = to_xy(hand, axis, outer, 34.0, k * 1.5, scale)
                    put(fx, ox, oy, (170, 255, 150))
                    put(fx, ox, oy + 1, (90, 220, 90), 220)
                for k in range(6):   # wisps rising and fading
                    yy_ = hy - 5 - ((fr + k) % 4) * 3
                    xx_ = hx + np.sin(fr * 0.8 + k * 1.7) * 3.5
                    put(fx, xx_, yy_, (130, 240, 130), int(230 - ((fr + k) % 4) * 45))
                    put(fx, xx_ + 1, yy_, (90, 200, 100), int(150 - ((fr + k) % 4) * 30))
            elif style == "flame staff":
                fx = glow(src, (255, 150, 40), p * 0.7)
                sx, sy = to_xy(hand, axis, outer, 33.5, 0.0, scale)
                flames(fx, [(sx - 3, sy), (sx - 1, sy - 1), (sx + 1, sy - 1), (sx + 3, sy)], fr, seed=3, height=9)
            elif style == "dragon staff":   # embers in its eyes, sparks rising from the jaws
                fx = glow(src, (255, 120, 30), p)
                for k in range(3):   # embers drifting up from between the jaws
                    ex, ey = to_xy(hand, axis, outer, 33.0 - 1.2, 7.5 - k * 1.6, scale)
                    put(fx, ex, ey - ((fr + k) % 4), (255, 170 - 30 * ((fr + k) % 3), 60), 230 - 40 * ((fr + k) % 4))
            elif style == "spider staff":   # a venom-green glow and drops of venom falling
                fx = glow(src, (120, 230, 80), p * 0.35)
                for k in range(3):
                    dx_, dy_ = to_xy(hand, axis, outer, 33.0 - 3.0, (k - 1) * 2.0, scale)
                    drop = (fr + k * 2) % 4
                    put(fx, dx_, dy_ + 2 + drop * 2, (150, 240, 90), 230 - drop * 40)
            elif style == "nature staff":
                fx = glow(src, (200, 255, 120), p)
                for k in range(5):   # fireflies
                    a = fr * 0.9 + k * 1.3
                    sparkle(fx, hx + 9 * np.cos(a), hy - 2 + 6 * np.sin(a * 1.3), (210, 255, 120), big=(fr + k) % 2 == 0)
            if behind:
                fx[body] = 0
            fxs.append(fx)
        return solid, fxs
    base, tier = MAGIC_BASE[style]
    solid = weapon_layer(T, d, base, tier, at=at, body=body, scale=scale)
    hand, axis, outer, behind, t, s, px, py = frame_axes(T, d, at, scale, POLE.get(base, 0), GRIP_SHIFT.get(base, 0.0))
    span = {"longsword": (3, 33), "arming sword": (3, 25), "battle axe": (18, 29), "spear": (39, 51), "scimitar": (3, 24), "mace": (17, 27)}[base]
    blade = (solid[..., 3] > 0) & (t >= span[0]) & (t <= span[1])
    for fr in range(FRAMES):
        p = PULSE[fr]
        rng = np.random.default_rng(fr * 13 + len(style))
        if style == "rune sword":
            fx = aura(blade, (110, 190, 255), p * 0.6)
            for i, tt in enumerate(np.arange(6, 31, 4)):   # runes along the fuller light up in turn
                x, y = to_xy(hand, axis, outer, tt, 0.0, scale)
                on = (i - fr) % 4 == 0
                put(fx, x, y, (200, 240, 255) if on else (90, 150, 230), 255 if on else 200)
        elif style == "flame sword":
            fx = aura(blade, (255, 140, 40), p * 0.6)
            srcs = [to_xy(hand, axis, outer, tt, 0.0, scale) for tt in np.arange(5, 26, 2.6)]
            flames(fx, srcs, fr, seed=5, height=6.5)
        elif style == "frost axe":
            fx = aura(blade, (170, 230, 255), p * 0.8)
            for k in range(9):   # frost motes drifting down
                tt, ss = 16 + rng.uniform(0, 14), rng.uniform(-11, 11)
                x, y = to_xy(hand, axis, outer, tt, ss, scale)
                sparkle(fx, x, y + fr * 1.2, (190, 240, 255), big=(k % 2 == fr % 2))
        elif style == "storm spear":
            fx = aura(blade, (180, 210, 255), p * 0.5)
            for k in range(3):
                a = to_xy(hand, axis, outer, rng.uniform(40, 50), rng.uniform(-1, 1), scale)
                b = to_xy(hand, axis, outer, rng.uniform(26, 52), rng.choice([-1, 1]) * rng.uniform(5, 11), scale)
                bolt(fx, a, b, rng)
        elif style == "void blade":
            fx = aura(blade, (150, 70, 220), p * 0.8)
            for k in range(7):   # smoke curling off the edge and rising
                tt = 4 + ((k * 3 + fr * 2) % 20)
                x, y = to_xy(hand, axis, outer, tt, 3 + (fr % 2), scale)
                put(fx, x, y - 1 - (k + fr) % 3, (140, 80, 210), 200)
                put(fx, x + 1, y - 2 - (k + fr) % 3, (90, 40, 150), 140)
        elif style == "holy mace":
            fx = aura(blade, (255, 240, 170), p)
            x, y = to_xy(hand, axis, outer, 22, 0, scale)
            for k in range(4):
                a = fr * np.pi / 4 + k * np.pi / 2
                sparkle(fx, x + 8 * np.cos(a), y + 8 * np.sin(a), (255, 240, 170), big=True)
        if behind:
            fx[body] = 0
        fxs.append(fx)
    return solid, fxs


def blend(base, fx):
    """Lay a part-transparent effect layer over a finished figure."""
    out = base.copy()
    a = fx[..., 3:4].astype(np.float32) / 255.0
    m = fx[..., 3] > 0
    solid = base[..., 3] > 0
    mix = base[..., :3] * (1 - a) + fx[..., :3] * a
    out[m & solid, :3] = mix[m & solid].astype(np.uint8)
    out[m & ~solid] = fx[m & ~solid]
    return out


# ---------------------------------------------------------------------------
# figures and sheets
# ---------------------------------------------------------------------------

RACES = [("Human", "Human.dmi", "", "standard", None), ("Dwarf", "Dwarf.dmi", "", "dwarf", "Brown"),
         ("Goblin", "Goblins.dmi", "", "goblin", None), ("Orc", "Orc.dmi", "Normal", "orc", None),
         ("Elf", "Night Elf.dmi", "Normal", "tall", None), ("Kobold", "Kobold.dmi", "Normal", "goblin", None),
         ("Lizardman", "LizardMan.dmi", "", "standard", None), ("Frogman", "FrogMan.dmi", "", "frog", None),
         ("Skeleton", "Skeleton.dmi", "Normal", "standard", None), ("Zombie", "DevourerZombie.dmi", "", "standard", None),
         ("Vampire", "Vampire.dmi", "", "tall", None), ("Demon", "Demon.dmi", "", "demon", None)]

# per race: scale of held things, an overlay state drawn over everything, and a kit
# (helmet, chest, shield, weapon as (style, tier) or None) for the review sheets
def K(helmet=None, chest=None, legs=None, arms=None, shield=None, weapon=None, magic=None):
    return dict(helmet=helmet, chest=chest, legs=legs, arms=arms, shield=shield, weapon=weapon, magic=magic)


EXTRA = {
    "Human": dict(kit=K(("nasal", "iron"), ("mail", "iron"), ("mail", "iron"), ("plate", "iron"), ("kite", "iron"), ("longsword", "iron")),
                  mage=K(chest=("robe", "blue"), legs=("boots", "leather"), magic="crystal staff")),
    "Dwarf": dict(kit=K(("horned", "iron"), ("banded", "iron"), ("plate", "iron"), ("plate", "iron"), ("round", "iron"), ("warhammer", "iron")),
                  mage=K(chest=("robe", "crimson"), legs=("boots", "leather"), magic="flame staff")),
    "Goblin": dict(scale=0.75, kit=K(("nasal", "leather"), ("leather", "leather"), ("leather", "leather"), ("leather", "leather"),
                                     ("buckler", "iron"), ("scimitar", "iron")),
                   mage=K(chest=("robe", "grey"), legs=("boots", "leather"), magic="skull staff")),
    "Orc": dict(kit=K(("great helm", "iron"), ("scale", "iron"), ("scale", "iron"), ("plate", "iron"), None, ("battle axe", "iron")),
                mage=K(chest=("robe", "crimson"), legs=("boots", "leather"), magic="flame staff")),
    "Elf": dict(kit=K(("winged", "silver"), ("scale", "silver"), ("mail", "silver"), ("plate", "silver"), ("heater", "silver"), magic="rune sword"),
                mage=K(chest=("robe", "purple"), legs=("boots", "leather"), magic="orb staff")),
    "Kobold": dict(scale=0.75, kit=K(("nasal", "leather"), ("leather", "leather"), ("leather", "leather"), ("leather", "leather"),
                                     ("buckler", "wood"), ("spear", "bone")),
                   mage=K(chest=("robe", "green"), legs=("boots", "leather"), magic="nature staff")),
    "Lizardman": dict(top="Tail", kit=K(("crested", "gold"), ("lamellar", "iron"), ("scale", "iron"), ("leather", "leather"), ("round", "iron"),
                                        magic="storm spear"),
                      mage=K(chest=("robe", "blue"), legs=("boots", "leather"), magic="crystal staff")),
    "Frogman": dict(kit=K(None, ("brigandine", "iron"), ("cloth", "wool"), ("leather", "leather"), None, ("halberd", "iron")),
                    mage=K(chest=("robe", "green"), legs=("boots", "leather"), magic="nature staff")),
    "Skeleton": dict(kit=K(("nasal", "iron"), ("tabard", "iron"), ("mail", "iron"), ("mail", "iron"), ("round", "iron"), ("arming sword", "iron")),
                     mage=K(chest=("robe", "grey"), legs=("boots", "leather"), magic="skull staff")),
    "Zombie": dict(kit=K(None, ("leather", "leather"), ("cloth", "wool"), None, None, ("morning star", "iron")),
                   mage=K(chest=("robe", "black"), legs=("boots", "leather"), magic="skull staff")),
    "Vampire": dict(kit=K(None, ("plate", "chitin"), ("plate", "chitin"), ("plate", "chitin"), ("heater", "chitin"), magic="void blade"),
                    mage=K(chest=("robe", "purple"), legs=("boots", "leather"), magic="orb staff")),
    "Demon": dict(kit=K(None, ("plate", "hell"), ("plate", "hell"), ("plate", "hell"), ("tower", "hell"), magic="flame sword"),
                  mage=K(chest=("robe", "crimson"), legs=("boots", "leather"), magic="flame staff")),
}


class Figures:
    """Bodies (enhanced, in their body type) and the row maps that fit template overlays to them."""

    def __init__(self, T, races=None, frame=0, stand_rows=()):
        """frame: the walk frame of the races' bodies (T should be the same frame's template).
        stand_rows: races whose 64 px body is the template's own walk moved onto the race's
        rows once, with the standing frame's rows (game_export's recoloured Dwarves): their
        bodies and overlays here go the same way, so the gear keeps to the body as it walks."""
        self.T = T
        self.beards = rm.read_dmi(os.path.join(rm.CREATURE_ICONS, "Beards.dmi"))
        self.cache, self.tops = {}, {}
        human = rm.read_dmi(os.path.join(rm.ICONS, "Human.dmi"))[""]
        for race in (races or RACES):
            name, f, st, kind, beard = race
            cells = rm.read_dmi(os.path.join(rm.ICONS, f))[st]
            frames = walk_frame(cells, frame)
            for i, d in enumerate(rm.DIRS):
                side = i >= 2
                if name in stand_rows:
                    src = rm.row_map(walk_frame(human, 0)[i], walk_frame(cells, 0)[i])
                    body = rm.reshape(rm.register(rm.form_light(rm.up(T.frames[i])), src), kind, side)
                else:
                    src = rm.row_map(T.frames[i], frames[i])
                    body = rm.reshape(rm.form_light(rm.up(frames[i])), kind, side)
                beard_l = None
                if beard:
                    bf = walk_frame(self.beards[beard], frame)
                    bc = bf[i] if len(bf) > i else bf[0]
                    beard_l = rm.fit(rm.strands(rm.long_beard(rm.form_light(rm.up(bc)), 9 if not side else 7)), kind, side, src, head=True)
                self.cache[(name, d)] = (body, src, kind, side, beard_l)
                tail = EXTRA.get(name, {}).get("top")
                if tail:
                    cells = walk_frame(rm.read_dmi(os.path.join(rm.ICONS, f))[tail], frame)
                    self.tops[(name, d)] = rm.reshape(rm.form_light(rm.up(cells[i])), kind, side)

    def fit_layer(self, race, d, layer, head=False):
        """A template overlay fitted to this race (its rows, then its body type)."""
        body, src, kind, side, _ = self.cache[(race[0], d)]
        return rm.fit(layer, kind, side, src, head)

    def body_mask(self, race, d):
        return self.cache[(race[0], d)][0][..., 3] > 0

    def map_point(self, race, d, x, y):
        """Where a point of the template lands on this race (its rows, then its body type)."""
        body, src, kind, side, _ = self.cache[(race[0], d)]
        i, frac = int(y) // 2, y - 2 * (int(y) // 2)
        rows = [(abs(si - i), j) for j, si in enumerate(src) if si >= 0]
        yr = 2 * min(rows)[1] + frac
        t = rm.BODY_TYPES[kind]
        out_rows = rm.row_list(kind)
        live = [(abs(r - int(yr)), k) for k, r in enumerate(out_rows) if r >= 0]
        y2 = min(live)[1] + (yr - int(yr))
        n = t["head_cols"] if yr < rm.CHIN else t["body_cols"]
        if side:
            n = int(round(n / 2.0))
        k = abs(n) // 2
        if n > 0:
            x2 = x - k if x < 32 else x + (n - k)
        elif n < 0:
            x2 = x + k if x < 32 else x - (-n - k)
        else:
            x2 = x
        return x2, y2

    def figure(self, race, d, under=(), over=(), head=None, held=(), frame=0):
        """body, `under` layers (legs, chest), the beard, the helmet, `over` layers (arms),
        all template layers fitted to this race; then `held` things (("shield"|"weapon",
        style, tier) or ("magic", style)), drawn rigid where this race's forearm and hand
        are, and the magic's effect for `frame` laid over the finished figure."""
        body, src, kind, side, beard_l = self.cache[(race[0], d)]
        layers = [rm.fit(l, kind, side, src) for l in under]
        if beard_l is not None:
            layers.append(beard_l)
        if head is not None:
            layers.append(rm.fit(head, kind, side, src, head=True))
        layers += [rm.fit(l, kind, side, src) for l in over]
        mask = body[..., 3] > 0
        sc = EXTRA.get(race[0], {}).get("scale", 1.0)
        fx = []
        for item in held:
            if item is None:
                continue
            what, style, tier = (tuple(item) + (None,))[:3]
            if what == "magic":
                at = self.map_point(race, d, *self.T.grip(d)[0])
                solid, frames = magic_layers(self.T, d, style, at=at, body=mask, scale=sc)
                layers.append(solid)
                fx.append(frames[frame % FRAMES])
            elif what == "shield":
                at = self.map_point(race, d, *self.T.shield_at(d)[0])
                layers.append(shield_layer(self.T, d, style, tier, at=at, body=mask, scale=sc))
            else:
                at = self.map_point(race, d, *self.T.grip(d)[0])
                layers.append(weapon_layer(self.T, d, style, tier, at=at, body=mask, scale=sc))
        top = self.tops.get((race[0], d))
        if top is not None:   # drawn over everything, as RebuildOverlays() adds the lizardman's tail
            layers.append(top)
        out = rm.outline(rm.comp(body, *layers))
        for f in fx:
            out = blend(out, f)
        return out


def iron_under(T, d, chest=True):
    i = rm.DIRS.index(d)
    out = [rm.metal_finish(rm.up(T.M["Metal Leggings"][i]))]
    if chest:
        out.append(rm.metal_finish(rm.up(T.M["Metal ChestPlate"][i]), "chest"))
    return out


def iron_arms(T, d):
    i = rm.DIRS.index(d)
    return [rm.metal_finish(rm.up(T.M[k][i])) for k in ("MLeftArm", "MRightArm")]


def draw_sheet(path, title, header, rows, cell=128, lab=170, gap=4, group_gap=18, note=None):
    """rows: [(label, [group: [64 px RGBA arrays]])]; header: a title per group."""
    from PIL import ImageFont
    font, big = ImageFont.load_default(size=15), ImageFont.load_default(size=20)
    ngroups = max(len(gs) for _, gs in rows)
    widths = [max(len(gs[gi]) for _, gs in rows if len(gs) > gi) for gi in range(ngroups)]
    starts = [lab + sum(w * (cell + gap) + group_gap for w in widths[:gi]) for gi in range(ngroups)]
    W = starts[-1] + widths[-1] * (cell + gap) + group_gap
    H = 70 + len(rows) * (cell + 12) + (30 if note else 0)
    sheet = Image.new("RGBA", (W, H), (26, 24, 20, 255))
    d = ImageDraw.Draw(sheet)
    d.text((12, 10), title, font=big, fill=(240, 228, 196))
    for gi, h in enumerate(header):
        d.text((starts[gi], 42), h, font=font, fill=(232, 220, 190))
    for r, (label, groups) in enumerate(rows):
        y = 70 + r * (cell + 12)
        d.text((12, y + cell // 2 - 8), label, font=font, fill=(240, 228, 196))
        for gi, g in enumerate(groups):
            for ci, im in enumerate(g):
                x = starts[gi] + ci * (cell + gap)
                sheet.paste((92, 118, 70, 255), (x, y, x + cell, y + cell))
                sheet.alpha_composite(Image.fromarray(im).resize((cell, cell), Image.NEAREST), (x, y))
    if note:
        d.text((12, H - 26), note, font=font, fill=(200, 190, 170))
    sheet.save(path)
    print(path, sheet.size)


def game_size_strip(path, title, rows, grass):
    """rows: [(label, [64 px RGBA])] shown at 1x on the game's grass."""
    from PIL import ImageFont
    font, big = ImageFont.load_default(size=15), ImageFont.load_default(size=20)
    n = max(len(c) for _, c in rows)
    sheet = Image.new("RGBA", (170 + n * 70, 50 + len(rows) * 74), (26, 24, 20, 255))
    d = ImageDraw.Draw(sheet)
    d.text((12, 10), title, font=big, fill=(240, 228, 196))
    tile = Image.fromarray(grass)
    for r, (label, cells) in enumerate(rows):
        y = 46 + r * 74
        d.text((12, y + 24), label, font=font, fill=(240, 228, 196))
        for i, im in enumerate(cells):
            x = 170 + i * 70
            sheet.paste(tile, (x, y))
            sheet.alpha_composite(Image.fromarray(im), (x, y))
    sheet.save(path)
    print(path, sheet.size)


def save_gif(path, frames, scale=1, ms=160):
    """frames: RGBA PIL images of one size -> a looping GIF (composited on their own background)."""
    ims = [f.convert("RGB") for f in frames]
    if scale != 1:
        ims = [im.resize((im.width * scale, im.height * scale), Image.NEAREST) for im in ims]
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=ms, loop=0, disposal=2)
    print(path, ims[0].size, len(ims), "frames")


def grid_image(title, labels, cells_rows, header=None, cell=128):
    """One frame of an animated sheet: labelled rows of 64 px cells drawn at `cell` size."""
    from PIL import ImageFont
    font, big = ImageFont.load_default(size=15), ImageFont.load_default(size=19)
    n = max(len(r) for r in cells_rows)
    W, H = 150 + n * (cell + 4), 64 + len(cells_rows) * (cell + 8)
    im = Image.new("RGBA", (W, H), (26, 24, 20, 255))
    d = ImageDraw.Draw(im)
    d.text((12, 10), title, font=big, fill=(240, 228, 196))
    if header:
        d.text((150, 38), header, font=font, fill=(232, 220, 190))
    for r, (lab, cells) in enumerate(zip(labels, cells_rows)):
        y = 60 + r * (cell + 8)
        d.text((12, y + cell // 2 - 8), lab, font=font, fill=(240, 228, 196))
        for c, a in enumerate(cells):
            x = 150 + c * (cell + 4)
            im.paste((92, 118, 70, 255), (x, y, x + cell, y + cell))
            im.alpha_composite(Image.fromarray(a).resize((cell, cell), Image.NEAREST), (x, y))
    return im


def main():
    T = Template()
    F = Figures(T)
    out = os.path.join(rm.ART, "out")
    grass = rm.up(rm.read_dmi(os.path.join(rm.GAME, "Code", "Building", "Grounds.dmi"))["Grass"][0])
    D = rm.DIRS

    def kit_fig(r, d, k, frame=0):
        under = [leg_layer(T, d, *k["legs"]) if k.get("legs") else None, any_chest(T, d, *k["chest"]) if k.get("chest") else None]
        head = helmet_layer(k["helmet"][0], k["helmet"][1], d, T.heads, T.M) if k.get("helmet") else None
        over = arms_layers(T, d, *k["arms"]) if k.get("arms") else []
        held = [("shield",) + k["shield"] if k.get("shield") else None, ("weapon",) + k["weapon"] if k.get("weapon") else None,
                ("magic", k["magic"]) if k.get("magic") else None]
        return F.figure(r, d, [u for u in under if u is not None], over, head=head, held=held, frame=frame)

    def dressed(r, d, legs=None, chest=None, arms=None, held=(), frame=0):
        under = [x for x in (legs, chest) if x is not None]
        return F.figure(r, d, under, arms or [], held=held, frame=frame)

    orig = {r[0]: rm.rgba(rm.read_dmi(os.path.join(rm.ICONS, r[1]))[r[2]][0]) for r in RACES}

    # every race: original, body, warrior kit, mage kit
    rows = [(r[0], [[orig[r[0]]], [F.figure(r, d) for d in D], [kit_fig(r, d, EXTRA[r[0]]["kit"]) for d in D],
                    [kit_fig(r, d, EXTRA[r[0]]["mage"]) for d in D]]) for r in RACES]
    draw_sheet(os.path.join(out, "races-kits.png"), "All races: original | enhanced body | warrior kit | mage kit  (S N E W, close up 2x)",
               ["original", "enhanced body", "warrior kit", "mage kit"], rows)
    game_size_strip(os.path.join(out, "races-gamesize.png"), "Game size (64 px tile, on grass): body S, warrior kit S N E W, mage kit S N E W",
                    [(r[0], [F.figure(r, "S")] + [kit_fig(r, d, EXTRA[r[0]]["kit"]) for d in D] +
                      [kit_fig(r, d, EXTRA[r[0]]["mage"]) for d in D]) for r in RACES], grass)
    # legs and arms on every race
    draw_sheet(os.path.join(out, "races-legs.png"), "Leg armour on every race (metal parts in iron): south | east",
               [", ".join(LEGS) + "   (south)", "(east)"],
               [(r[0], [[dressed(r, d, legs=leg_layer(T, d, st, "iron")) for st in LEGS] for d in ("S", "E")]) for r in RACES])
    draw_sheet(os.path.join(out, "races-arms.png"), "Arm armour on every race (iron), with mail chest: south | east",
               [", ".join(ARMS) + "   (south)", "(east)"],
               [(r[0], [[dressed(r, d, chest=chest_layer(T, d, "mail", "iron"), arms=arms_layers(T, d, st, "iron")) for st in ARMS]
                        for d in ("S", "E")]) for r in RACES])
    allchest = CHESTS + CHESTS2
    draw_sheet(os.path.join(out, "races-chest.png"), "Chest armour on every race (iron; leather; robe in blue), south",
               [", ".join(allchest)],
               [(r[0], [[dressed(r, "S", legs=leg_layer(T, "S", "boots", "leather") if st == "robe" else leg_layer(T, "S", "mail", "iron"),
                                 chest=any_chest(T, "S", st, "blue" if st == "robe" else ("leather" if st == "leather" else "iron")))
                         for st in allchest]]) for r in RACES])
    # the catalogue's robes
    draw_sheet(os.path.join(out, "robes.png"), "Robes (planning/WEARABLES.md): the game's plain silk robes, then the school robes",
               [" | ".join(ROBE_NAMES.values())],
               [(r[0], [[dressed(r, "S", legs=leg_layer(T, "S", "boots", "leather"), chest=chest_layer2(T, "S", "robe", k)) for k in ROBE_NAMES]])
                for r in (RACES[0], RACES[4], RACES[1])])
    # magic: a still sheet (4 frames south + the other facings) and animated previews
    mage = RACES[0]
    robe = lambda d: dict(legs=leg_layer(T, d, "boots", "leather"), chest=chest_layer2(T, d, "robe", "blue"))
    rows = [(m, [[dressed(mage, "S", held=[("magic", m)], frame=fr, **robe("S")) for fr in range(FRAMES)],
                 [dressed(mage, d, held=[("magic", m)], **robe(d)) for d in ("N", "E", "W")]]) for m in MAGIC]
    draw_sheet(os.path.join(out, "magic.png"), "Magic staffs and enchanted weapons: 4 effect frames (south) | north, east, west",
               ["frames 1-4 (south)", "N  E  W"], rows)
    frames = []
    for fr in range(FRAMES):
        cells = [[dressed(r, d, held=[("magic", m)], frame=fr, **robe(d)) for d in D] for m, r in zip(MAGIC, [mage] * len(MAGIC))]
        frames.append(grid_image("Magic items, animated (S N E W)", MAGIC, cells))
    save_gif(os.path.join(out, "magic.gif"), frames)
    frames = []
    for fr in range(FRAMES):
        cells = [[kit_fig(r, d, EXTRA[r[0]]["mage"], fr) for d in D] + [kit_fig(r, d, EXTRA[r[0]]["kit"], fr) for d in D] for r in RACES]
        frames.append(grid_image("Every race: mage kit | warrior kit, animated (S N E W)", [r[0] for r in RACES], cells, cell=96))
    save_gif(os.path.join(out, "races-kits.gif"), frames)


if __name__ == "__main__":
    main()
