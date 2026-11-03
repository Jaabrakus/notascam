#!/usr/bin/env python3
"""Werewolves' 64 px bodies: every Races64 sheet of a race that can catch lycanthropy, changed,
every state, frame and facing. The original has one werewolf picture for every race (its 32 px
Werewolf.dmi); here each race keeps its own shape and turns into its own wolf.

    python3 standalone/remastered/art/enhance/werewolf64.py [--only Human,Orc] [--preview DIR]

  fur      a wolf's brown coat at the skin's lightness, a third of the race's own colour kept (an
           orc's wolf is a grey-green brute, a kobold's a sandy one), hatched darker
  ears     two pointed wolf ears on the head (one, seen from the side)
  eyes     glowing red, as the original werewolf's
  fangs    white at the mouth
  claws    white hooks at the end of each arm, where the arm is (the pixels its "No<arm>" state
           lacks: limbs64.py), so they move with the walk

Reads game/Icons/Remastered/Races64/<sheet>.dmi and writes <sheet>-Werewolf.dmi beside it.
"""

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import game_export as ge  # noqa: E402
import halfdemon64 as hd  # noqa: E402
from limbs64 import cut  # noqa: E402

SHEETS = hd.SHEETS        # the living races: undead, vampires and devourers can't catch it
FUR = (112, 76, 44)
EAR_INNER = (196, 120, 116)
EYE, EYE_HOT = (220, 30, 20), (255, 150, 70)
WHITE = (240, 236, 224)
# A wolf ear, the left one in a front view: (dx, dy) from its base, up negative.
EAR = [(0, 0), (1, 0), (2, 0), (3, 0), (0, -1), (1, -1), (2, -1), (3, -1), (0, -2), (1, -2), (2, -2),
       (0, -3), (1, -3), (2, -3), (0, -4), (1, -4), (0, -5), (0, -6)]
INNER = {(1, -1), (1, -2), (1, -3), (2, -1)}


def fur_map(fam, v0):
    out = {}
    for k in fam:
        r = hd.hsv(k)[2] / v0
        out[k] = tuple(int(min(255, FUR[i] * r * 0.67 + k[i] * 0.33)) for i in range(3))
    return out


def ears(a, d, col):
    top = hd.top_of(a)
    y = top + 3
    xs = np.flatnonzero(a[y, :, 3] > 0)
    if not len(xs):
        return
    xl, xr = int(xs.min()), int(xs.max())
    if d in ("E", "W"):
        bases = [((xl + xr) // 2 + (1 if d == "W" else -1), d == "W")]
    else:
        bases = [(xl + 2, False), (xr - 2, True)]
    dark = tuple(int(v * 0.7) for v in col)
    for bx, mirror in bases:
        pts = []
        for dx, dy in EAR:
            x, y2 = bx + (-dx if mirror else dx), y + dy
            hd.put(a, x, y2, EAR_INNER if (dx, dy) in INNER and d != "N" else (dark if dx == 0 else col))
            pts.append((x, y2))
        hd.outline(a, pts)


def claws(a, arm):
    """Two white hooks under the lowest pixels of an arm."""
    ys, xs = np.nonzero(arm)
    if not len(ys):
        return
    y = int(ys.max())
    for x in sorted(set(int(v) for v in xs[ys == y]))[:3:2]:
        hd.put(a, x, y + 1, WHITE)
        if y + 2 < 64 and a[y + 2, x, 3] == 0:
            hd.put(a, x, y + 2, (40, 30, 24))


def were_cell(a, d, bubble, fam, cmap, eyes, mouth, arms):
    a = np.array(a, np.uint8, copy=True)
    if bubble or not (a[..., 3] > 0).any():
        return a
    skin = hd.is_skin(a, fam)
    out = a.copy()
    for y, x in zip(*np.nonzero(skin)):
        c = cmap.get(tuple(int(v) for v in a[y, x, :3]))
        if c:
            out[y, x, :3] = tuple(int(v * 0.78) for v in c) if (x + 2 * y) % 5 == 0 else c
    em = hd.eye_mask(a, d, eyes, mouth)
    for y, x in zip(*np.nonzero(em)):
        out[y, x, :3] = EYE_HOT if hd.hsv(a[y, x, :3])[2] > 0.8 else EYE
    top = hd.top_of(a)
    if d in ("S", "E", "W") and mouth and 0 <= top + mouth < 64:
        row = np.flatnonzero(skin[top + mouth])
        if len(row):
            for x in (row[len(row) // 3], row[2 * len(row) // 3]):
                hd.put(out, int(x), top + mouth, WHITE)
    for arm in arms:
        claws(out, arm)
    ears(out, d, FUR)
    return out


def were_sheet(sheet, src_dir):
    states = ge.read_dmi_full(os.path.join(src_dir, sheet + ".dmi"))
    by = {name: (meta, cells) for name, meta, cells in states}
    normal = by.get("Normal") or by.get("")
    first = [np.asarray(c) for c in normal[1]]
    front, side = hd.mouth_rows(sheet)
    fam, v0 = hd.skin_family(first)
    eyes = hd.eye_colours(first[0], fam, front)
    cmap = fur_map(fam, v0)
    out = []
    for name, meta, cells in states:
        dirs = int(meta.get("dirs", 1))
        new = []
        for k, c in enumerate(cells):
            d = ge.DIRS4[k % dirs] if dirs in (4, 8) and k % dirs < 4 else "S"
            bubble = "Sleep" in name and k // dirs > 0
            arms = []
            if name in ("Normal", "") and dirs == 4:   # claws on the standing body: its arms as cut from it
                for slot in ("LeftArm", "RightArm"):
                    miss = by.get("No" + slot)
                    if miss and k < len(miss[1]):
                        arms.append(cut(np.asarray(c), np.asarray(miss[1][k]))[..., 3] > 0)
            new.append(were_cell(c, d, bubble, fam, cmap, eyes, front if d == "S" else side, arms))
        out.append((name, meta, new))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", default=None, help="Races64 sheets (comma separated)")
    ap.add_argument("--preview", default=None, help="write the sheets under this folder instead of the game")
    a = ap.parse_args()
    out_dir = a.preview or ge.OUT_RACES
    os.makedirs(out_dir, exist_ok=True)
    for sheet in SHEETS:
        if a.only and sheet not in a.only.split(","):
            continue
        path = os.path.join(out_dir, f"{sheet}-Werewolf.dmi")
        ge.write_sheet(path, were_sheet(sheet, ge.OUT_RACES), 64)
        print(path)


if __name__ == "__main__":
    main()
