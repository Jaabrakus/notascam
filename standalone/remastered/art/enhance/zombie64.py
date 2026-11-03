#!/usr/bin/env python3
"""Zombies' 64 px bodies: every Races64 sheet of a living race, rotted, every state, frame and
facing (the Devourer's plague zombies keep the body they had: Vars.dm Infection).

    python3 standalone/remastered/art/enhance/zombie64.py [--only Human,Orc] [--preview DIR]

  skin      grey-green rot at the same lightness, a quarter of the race's own colour left in it
            (an orc still a little green, a kobold olive), with darker patches of decay
  bone      a few places where the flesh is gone: ribs, a forearm, the shin
  clothes   darker and torn: holes show the rotting skin beneath
  eyes      milky and dead
  mouth     dried blood about it

Reads game/Icons/Remastered/Races64/<sheet>.dmi and writes <sheet>-Zombie.dmi beside it. The
skin, eyes and mouth are found as halfdemon64.py finds them; patches, bone and tears are placed
as offsets from the head's top and the body's middle, so every frame of a facing rots alike.
"""

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import game_export as ge  # noqa: E402
import halfdemon64 as hd  # noqa: E402

SHEETS = hd.SHEETS        # the living races (undead, vampires and devourers can't turn)
ROT = (126, 142, 106)     # grey-green flesh
DECAY = (66, 76, 50)
BONE = ((236, 230, 206), (196, 188, 160))
DEAD_EYE = (214, 224, 196)
BLOOD = (128, 24, 20)


def zombie_map(fam, v0):
    """Each skin colour -> rot at its lightness, a quarter of the old colour left in."""
    out = {}
    for k in fam:
        r = hd.hsv(k)[2] / v0
        out[k] = tuple(int(min(255, ROT[i] * r * 0.75 + k[i] * 0.25)) for i in range(3))
    return out


def marks(a, skin, seed):
    """Where the rot shows, as offsets from the head's top and the body's middle: decay patches,
    bare bone and tears in the clothes, the same for every frame of a facing."""
    rng = np.random.default_rng(seed)
    top = hd.top_of(a)
    ys, xs = np.nonzero(a[..., 3])
    cx = (int(xs.min()) + int(xs.max())) // 2
    bot = int(ys.max())
    body = [(int(y), int(x)) for y, x in zip(*np.nonzero(skin)) if top + 22 <= y <= bot - 2]
    cloth = [(int(y), int(x)) for y, x in zip(*np.nonzero(a[..., 3])) if not skin[y, x]
             and top + 22 <= y <= bot - 4 and a[y, x, :3].astype(int).sum() > 90]
    patches, bones, tears = [], [], []
    for _ in range(8 if body else 0):
        y, x = body[rng.integers(len(body))]
        patches += [(x - cx + dx, y - top + dy) for dx in (-1, 0, 1) for dy in (0, 1) if rng.random() < 0.75]
    for _ in range(2 if body else 0):
        y, x = body[rng.integers(len(body))]
        bones += [(x - cx, y - top + k, k % 2) for k in range(int(rng.integers(2, 4)))]
    for _ in range(4 if cloth else 0):
        y, x = cloth[rng.integers(len(cloth))]
        tears += [(x - cx + dx, y - top + dy) for dx in (0, 1) for dy in (0, 1, 2) if rng.random() < 0.7]
    return patches, bones, tears


def zombie_cell(a, d, bubble, fam, cmap, eyes, mouth, mk):
    a = np.array(a, np.uint8, copy=True)
    if bubble or not (a[..., 3] > 0).any():
        return a
    skin = hd.is_skin(a, fam)
    out = a.copy()
    for y, x in zip(*np.nonzero(skin)):
        c = cmap.get(tuple(int(v) for v in a[y, x, :3]))
        if c:
            out[y, x, :3] = c
    # the rest that isn't outline (clothes, hair): duller and darker
    rest = (a[..., 3] > 0) & ~skin & (a[..., :3].astype(int).sum(-1) > 90)
    out[rest, :3] = (out[rest, :3].astype(float) * 0.62 + np.array(DECAY) * 0.18).astype(np.uint8)
    top = hd.top_of(a)
    xs = np.flatnonzero((a[..., 3] > 0).any(0))
    cx = (int(xs.min()) + int(xs.max())) // 2
    patches, bones, tears = mk
    for dx, dy in patches:
        x, y = cx + dx, top + dy
        if 0 <= x < 64 and 0 <= y < 64 and skin[y, x]:
            out[y, x, :3] = DECAY
    for dx, dy in tears:
        x, y = cx + dx, top + dy
        if 0 <= x < 64 and 0 <= y < 64 and rest[y, x]:
            out[y, x, :3] = ROT if (x + y) % 3 else DECAY
    for dx, dy, shade in bones:
        x, y = cx + dx, top + dy
        if 0 <= x < 64 and 0 <= y < 64 and skin[y, x]:
            out[y, x, :3] = BONE[shade]
    em = hd.eye_mask(a, d, eyes, mouth)
    out[em, :3] = DEAD_EYE
    if d in ("S", "E", "W") and mouth:
        y = top + mouth
        row = np.flatnonzero(skin[y]) if 0 <= y < 64 else []
        for x in row[::3]:
            out[y, x, :3] = BLOOD
            if y + 1 < 64 and skin[y + 1, x]:
                out[y + 1, x, :3] = BLOOD
    return out


def zombie_sheet(sheet, src_dir):
    states = ge.read_dmi_full(os.path.join(src_dir, sheet + ".dmi"))
    first = [np.asarray(c) for c in states[0][2]]
    if states[0][0] == "Sleep":
        first = [np.asarray(c) for c in next(st for st in states if int(st[1].get("dirs", 1)) == 4)[2]]
    front, side = hd.mouth_rows(sheet)
    fam, v0 = hd.skin_family(first)
    eyes = hd.eye_colours(first[0], fam, front)
    cmap = zombie_map(fam, v0)
    mks = {d: marks(first[i], hd.is_skin(first[i], fam), 31 + i) for i, d in enumerate(ge.DIRS4)}
    out = []
    for name, meta, cells in states:
        dirs = int(meta.get("dirs", 1))
        new = []
        for k, c in enumerate(cells):
            d = ge.DIRS4[k % dirs] if dirs in (4, 8) and k % dirs < 4 else "S"
            bubble = "Sleep" in name and k // dirs > 0
            new.append(zombie_cell(c, d, bubble, fam, cmap, eyes, front if d == "S" else side, mks.get(d, ([], [], []))))
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
        path = os.path.join(out_dir, f"{sheet}-Zombie.dmi")
        ge.write_sheet(path, zombie_sheet(sheet, ge.OUT_RACES), 64)
        print(path)


if __name__ == "__main__":
    main()
