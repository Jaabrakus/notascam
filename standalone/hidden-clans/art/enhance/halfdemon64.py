#!/usr/bin/env python3
"""The half-demon kinds' 64 px bodies (HalfDemons.dm): every Races64 sheet of a race that can
become one, redrawn three ways, every state, frame and facing.

    python3 standalone/remastered/art/enhance/halfdemon64.py [--only Human,Orc] [--preview DIR]

  Marked       the race's own colours; ember eyes, small ivory horns, shadows gone blood red
  Ashen        charcoal skin with glowing ember cracks, ember eyes, small dark horns tipped red
  Hellblooded  skin in the Demon's reds, curved ivory horns, ember eyes, a barbed tail

Reads game/Icons/Remastered/Races64/<sheet>.dmi (game_export.py writes them) and writes
<sheet>-Marked.dmi, <sheet>-Ashen.dmi and <sheet>-Hellblooded.dmi beside them. The original
half-demon (possessed at the hell portal) keeps the original game's look: its first two stages
on the 64 px body are <sheet>-Possessed1.dmi (red eyes, the original's RedEye.dmi) and
<sheet>-Possessed2.dmi (the whole picture redder, the original's icon += rgb(150,0,0)); its
third is the Demon.
The skin is found as the sheet's main colour family, so every frame is recoloured alike; eyes
by their colours above the mouth; horns and the tail are drawn per frame from the head's top
and the hips, so they move with the walk.
"""

import argparse
import colorsys
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import game_export as ge  # noqa: E402

KINDS = ("Marked", "Ashen", "Hellblooded")
# Sheets of races that can become a half-demon kind (undead and vampires can't), and the row
# below the sprite's top where the mouth is, front and side (game_export.SHEETS).
SHEETS = ["Human", "HumanBlack", "Dwarves", "Night Elf", "Orc", "Goblins", "Kobold", "LizardMan", "FrogMan"]
# The hell portal possesses only units with no subrace (Vars.dm Portal), so never the undead,
# vampires or devourers (the game sets theirs): the same sheets as the kinds.
POSSESSED = ("Possessed1", "Possessed2")
POSSESSED_SHEETS = SHEETS
OUTLINE = (0, 0, 0)
EMBER, EMBER_HOT = (235, 60, 20), (255, 214, 90)
IVORY = ((255, 250, 225), (226, 212, 172), (176, 156, 116))      # tip, middle, base
CHAR = ((168, 44, 24), (70, 52, 48), (40, 30, 28))
DEMON_RED, ASH = (165, 10, 6), (78, 68, 66)

# Horns, the left one in a front view: (dx, dy) from its base, up negative.
SMALL = [(-4, -7), (-4, -6), (-3, -6), (-3, -5), (-2, -5), (-3, -4), (-2, -4), (-1, -4), (-2, -3), (-1, -3),
         (0, -3), (-2, -2), (-1, -2), (0, -2), (1, -2), (-1, -1), (0, -1), (1, -1), (2, -1), (-1, 0), (0, 0),
         (1, 0), (2, 0)]
BIG = [(x, -dy) for dy, (x0, x1) in enumerate([(0, 4), (-1, 3), (-2, 2), (-3, 1), (-4, 0), (-5, -1), (-5, -2),
                                                (-6, -3), (-6, -4), (-6, -5), (-6, -5), (-5, -5)])
       for x in range(x0, x1 + 1)]


def hsv(c):
    return colorsys.rgb_to_hsv(*[v / 255 for v in c])


def colours(cells):
    n = {}
    for a in cells:
        for p in a[a[..., 3] > 0][:, :3]:
            k = tuple(int(v) for v in p)
            n[k] = n.get(k, 0) + 1
    return n


def skin_family(cells):
    """The skin's colours (the main colour and its shades) and the main colour's lightness."""
    n = colours(cells)
    c0 = max((m, k) for k, m in n.items() if hsv(k)[2] > 0.25 and hsv(k)[1] > 0.3)[1]
    h0, _, v0 = hsv(c0)
    tol = 0.16 if abs(h0 - 0.5) < 0.08 else 0.07   # a lizard's scales run from green to blue
    fam = set()
    for k in n:
        h, s, v = hsv(k)
        if min(abs(h - h0), 1 - abs(h - h0)) < tol and s >= 0.3 and 0.45 * v0 <= v <= 1.7 * v0 and v > 0.2:
            fam.add(k)
    if sum(n[k] for k in fam) < 0.2 * sum(n.values()):   # bone, a vampire's pallor: no coloured skin to go by
        raise ValueError("no skin colour")
    return fam, v0


def top_of(a):
    ys = np.flatnonzero((a[..., 3] > 0).any(1))
    return int(ys.min()) if len(ys) else None


def is_skin(a, fam):
    m = np.zeros(a.shape[:2], bool)
    for y, x in zip(*np.nonzero(a[..., 3])):
        m[y, x] = tuple(int(v) for v in a[y, x, :3]) in fam
    return m


def eye_colours(a, fam, mouth):
    """Colours of the eyes in a standing front view: bright, not skin, above the mouth."""
    top = top_of(a)
    out = set()
    for y in range(top + 5, top + mouth - 2):
        for x in range(64):
            if a[y, x, 3]:
                k = tuple(int(v) for v in a[y, x, :3])
                if k not in fam and hsv(k)[2] >= 0.5:
                    out.add(k)
    return out


def skin_map(kind, fam, v0):
    """Each skin colour -> the kind's colour at the same lightness."""
    out = {}
    for k in fam:
        r = hsv(k)[2] / v0
        if kind == "Marked":
            if r < 0.92:   # the shaded side: towards dark blood red
                t = min(1.0, (0.92 - r) * 3.5 + 0.35)
                out[k] = tuple(int(k[i] * (1 - t) + (120, 18, 14)[i] * t) for i in range(3))
        else:
            base = DEMON_RED if kind == "Hellblooded" else ASH
            out[k] = tuple(int(min(255, base[i] * r)) for i in range(3))
    return out


def put(a, x, y, c):
    if 0 <= x < 64 and 0 <= y < 64:
        a[y, x, :3] = c
        a[y, x, 3] = 255


def outline(a, pts, over=False):
    """A dark edge round pts where they meet the background (or anything, when `over` the body)."""
    S = set(pts)
    for x, y in pts:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in S and 0 <= nx < 64 and 0 <= ny < 64 and (over or a[ny, nx, 3] == 0):
                put(a, nx, ny, OUTLINE)


def horn(a, shape, bx, by, mirror, cols):
    pts = [(bx + (-dx if mirror else dx), by + dy) for dx, dy in shape]
    hmax = -min(dy for _, dy in shape)
    for (x, y), (_, dy) in zip(pts, shape):
        t = -dy / max(1, hmax)
        put(a, x, y, cols[0] if t > 0.66 else cols[1] if t > 0.3 else cols[2])
    outline(a, pts)


def horns(a, d, shape, cols):
    top = top_of(a)
    y = top + 4
    xs = np.flatnonzero(a[y, :, 3] > 0)
    if not len(xs):
        return
    xl, xr = int(xs.min()), int(xs.max())
    if d in ("E", "W"):   # one horn, sweeping back
        cx = (xl + xr) // 2
        horn(a, shape, cx - 1 if d == "E" else cx + 1, y, d == "W", cols)
    else:
        inset = 4 if shape is SMALL else 3
        horn(a, shape, xl + inset, y, False, cols)
        horn(a, shape, xr - inset, y, True, cols)


def tail(a, d, colour):
    m = a[..., 3] > 0
    ys = np.flatnonzero(m.any(1))
    top, bot = int(ys.min()), int(ys.max())
    hip = int(top + (bot - top) * 0.62)
    xs = np.flatnonzero(m[hip])
    if not len(xs):
        return
    over = False
    if d in ("E", "W"):   # from the back of the hip, down and out, then a barbed tip
        s = -1 if d == "E" else 1
        x0 = int(xs.min()) if d == "E" else int(xs.max())
        path = [(0, 0), (1, 1), (2, 2), (3, 4), (4, 6), (5, 7), (6, 7), (7, 6), (8, 5)]
        tip = [(9, 4), (10, 3), (9, 3), (8, 3), (10, 5), (9, 5)]
        pts = [(x0 + s * dx, hip + dy) for dx, dy in path]
        tip = [(x0 + s * dx, hip + dy) for dx, dy in tip]
    elif d == "S":        # peeking out beside a leg
        x0 = int(xs.max()) + 1
        pts = [(x0, hip + 6), (x0 + 1, hip + 5), (x0 + 2, hip + 4), (x0 + 2, hip + 3), (x0 + 3, hip + 2)]
        tip = [(x0 + 3, hip + 1), (x0 + 4, hip + 1), (x0 + 3, hip), (x0 + 2, hip + 1), (x0 + 4, hip + 2)]
    else:                 # from behind: over the legs, swinging out to one side
        cx = (int(xs.min()) + int(xs.max())) // 2
        over = True
        pts = [(cx, hip), (cx + 1, hip + 1), (cx + 2, hip + 3), (cx + 3, hip + 5), (cx + 4, hip + 7), (cx + 5, hip + 8),
               (cx + 6, hip + 8), (cx + 7, hip + 7)]
        tip = [(cx + 8, hip + 6), (cx + 9, hip + 5), (cx + 8, hip + 5), (cx + 7, hip + 5), (cx + 9, hip + 7), (cx + 8, hip + 7)]
    body = [p for x, y in pts for p in ((x, y), (x, y + 1))] + tip
    dark = tuple(int(v * 0.7) for v in colour)
    S = set(body)
    for x, y in body:
        if 0 <= x < 64 and 0 <= y < 64 and (over or not m[y, x]):
            put(a, x, y, colour if (x, y - 1) in S else dark)
    outline(a, body, over)   # from behind it lies over the body: edged all round


def crack_paths(a, skin, seed):
    """Ember cracks over the body's skin (not the face), as offsets from the head's top and the
    body's middle, so every frame of a facing has the same cracks."""
    rng = np.random.default_rng(seed)
    top = top_of(a)
    ys, xs = np.nonzero(a[..., 3])
    cx = (int(xs.min()) + int(xs.max())) // 2
    bot = int(ys.max())
    cand = [(int(y), int(x)) for y, x in zip(*np.nonzero(skin)) if top + 24 <= y <= bot - 8]
    out = []
    for _ in range(4 if cand else 0):
        y, x = cand[rng.integers(len(cand))]
        for step in range(int(rng.integers(4, 8))):
            out.append((x - cx, y - top, step % 3 == 1))
            y += 1
            x += int(rng.integers(-1, 2))
    return out


def cracks(a, skin, paths):
    top = top_of(a)
    xs = np.flatnonzero((a[..., 3] > 0).any(0))
    cx = (int(xs.min()) + int(xs.max())) // 2
    for dx, dy, hot in paths:
        x, y = cx + dx, top + dy
        if 0 <= x < 64 and 0 <= y < 64 and skin[y, x]:
            a[y, x, :3] = EMBER_HOT if hot else (230, 90, 20)


def eye_mask(a, d, eyes, mouth):
    """The eye pixels of a cell: the eyes' colours above the mouth (in profile, the front of the head)."""
    m = np.zeros(a.shape[:2], bool)
    top = top_of(a)
    if d not in ("S", "E", "W") or not mouth or not eyes:
        return m
    xs = np.flatnonzero((a[top + 6] > 0).any(-1)) if top + 6 < 64 else []
    for y in range(max(0, top + 5), min(64, top + mouth - 2)):
        for x in range(64):
            if not a[y, x, 3] or tuple(int(v) for v in a[y, x, :3]) not in eyes:
                continue
            if len(xs) and d != "S":
                edge = xs.min() + (xs.max() - xs.min()) * 0.55 if d == "E" else xs.max() - (xs.max() - xs.min()) * 0.55
                if (d == "E" and x < edge) or (d == "W" and x > edge):
                    continue
            m[y, x] = True
    return m


def possessed_cell(kind, a, d, eyes, mouth):
    out = a.copy()
    out[eye_mask(a, d, eyes, mouth), :3] = (255, 0, 0)
    if kind == "Possessed2":
        m = out[..., 3] > 0
        out[m, 0] = np.minimum(255, out[m, 0].astype(int) + 150).astype(np.uint8)
    return out


def kind_cell(kind, a, d, bubble, fam, cmap, eyes, mouth, paths):
    a = np.array(a, np.uint8, copy=True)
    if bubble or not (a[..., 3] > 0).any():   # a sleeper's bubble frames stay as they are
        return a
    if kind in POSSESSED:
        return possessed_cell(kind, a, d, eyes, mouth)
    skin = is_skin(a, fam)
    out = a.copy()
    for y, x in zip(*np.nonzero(skin)):
        c = cmap.get(tuple(int(v) for v in a[y, x, :3]))
        if c:
            out[y, x, :3] = c
    if kind == "Ashen" and paths is not None:
        cracks(out, skin, paths)
    for y, x in zip(*np.nonzero(eye_mask(a, d, eyes, mouth))):
        out[y, x, :3] = EMBER_HOT if hsv(a[y, x, :3])[2] > 0.8 else EMBER
    if kind == "Hellblooded":
        horns(out, d, BIG, IVORY)
        tail(out, d, DEMON_RED)
    else:
        horns(out, d, SMALL, IVORY if kind == "Marked" else CHAR)
    return out


def mouth_rows(sheet):
    for s in ge.SHEETS:
        if s["sheet"] == sheet:
            m = s.get("mouth") or {}
            return m.get("front", 17), m.get("side", m.get("front", 17))
    return 17, 17


def kind_sheet(sheet, kind, src_dir):
    states = ge.read_dmi_full(os.path.join(src_dir, sheet + ".dmi"))
    first = [np.asarray(c) for c in states[0][2]]
    if states[0][0] == "Sleep":   # a sheet that starts with its sleeper: the standing state is the first with facings
        first = [np.asarray(c) for c in next(st for st in states if int(st[1].get("dirs", 1)) == 4)[2]]
    front, side = mouth_rows(sheet)
    try:
        fam, v0 = skin_family(first)
        eyes = eye_colours(first[0], fam, front)
    except ValueError:
        raise SystemExit(f"{sheet}: no skin colour to go by")
    cmap = skin_map(kind, fam, v0)
    paths = {d: crack_paths(first[i], is_skin(first[i], fam), 7 + i) for i, d in enumerate(ge.DIRS4)} if kind == "Ashen" else {}
    out = []
    for name, meta, cells in states:
        dirs = int(meta.get("dirs", 1))
        new = []
        for k, c in enumerate(cells):
            d = ge.DIRS4[k % dirs] if dirs in (4, 8) and k % dirs < 4 else "S"
            bubble = "Sleep" in name and k // dirs > 0   # as game_export.body_sheet
            mouth = front if d == "S" else side
            new.append(kind_cell(kind, c, d, bubble, fam, cmap, eyes, mouth, paths.get(d)))
        out.append((name, meta, new))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", default=None, help="Races64 sheets (comma separated)")
    ap.add_argument("--preview", default=None, help="write the sheets under this folder instead of the game")
    a = ap.parse_args()
    out_dir = a.preview or ge.OUT_RACES
    os.makedirs(out_dir, exist_ok=True)
    for sheet in POSSESSED_SHEETS:
        if a.only and sheet not in a.only.split(","):
            continue
        for kind in (KINDS if sheet in SHEETS else ()) + POSSESSED:
            path = os.path.join(out_dir, f"{sheet}-{kind}.dmi")
            ge.write_sheet(path, kind_sheet(sheet, kind, ge.OUT_RACES), 64)
            print(path)


if __name__ == "__main__":
    main()
