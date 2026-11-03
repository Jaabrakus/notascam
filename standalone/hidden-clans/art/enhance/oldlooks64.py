#!/usr/bin/env python3
"""New 64 px pictures for the game's own special gear (Gear.dm RmGear64, GearOldLooks.dm), built
from the catalogue's fitted pieces so they fit every race in every frame and facing:

  * gold trim: the "Gold Trimmed" (Dragoon) set, iron with a gold edge; its helm, as the
    original's, a closed gold great helm with a gold fin;
  * gems: the Ruby, Emerald and Diamond Metal/Silver/Gold sets, the plain piece set with gems
    where the original Ruby set has them (helmet: brow and cheek guards, chest: shoulder tips
    and belly, legs: knees and shins);
  * Skorn: chitin's spiked pieces in steel, and a closed great helm with steel horns and red eyes;
  * the Supernatural Bone helm: the great helm in black steel, a gold edge, bone horns sweeping
    out and down and two spikes on top;
  * Bloodwhisker (a dark green spear) and Soul Eater (a green blade).

    python3 oldlooks64.py OUT [--src DIR ...]

Reads the unshaded sheets (the export's own output: restore-points/sprites-before-enhance-20261024/
Gear64, or each --src first), recolours with the pipeline's exact ramps (wearables64.RAMPS), shades
the result with the installed sheets' pass (art/voxel/enhance2d.py enhance_gear_cell), then lays the
gems and eyes on top, and writes OUT/<sheet>/oldlooks.dmi. Re-run after game_export.py changes the
pieces these are built from."""

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(ROOT, "art", "voxel"))
import game_export as ge  # noqa: E402
import wearables64 as w  # noqa: E402
import enhance2d as e2  # noqa: E402

RESTORE = os.path.join(ROOT, "restore-points", "sprites-before-enhance-20261024", "Gear64")
R = w.RAMPS
# a dark steel green for a haft, and the gems: rim, dark, mid, light, glint
DARK_GREEN = [(4, 16, 6), (12, 38, 16), (22, 62, 26), (36, 90, 40), (64, 128, 64)]
GEMS = {"ruby": [(70, 0, 10), (150, 10, 25), (215, 30, 45), (255, 110, 110), (255, 225, 225)],
        "emerald": [(0, 50, 20), (10, 120, 50), (30, 185, 80), (120, 240, 150), (230, 255, 235)],
        "diamond": [(24, 60, 110), (80, 150, 215), (165, 222, 255), (222, 246, 255), (255, 255, 255)]}   # blue-rimmed, to show on silver
EYE = [(150, 0, 0), (235, 30, 25), (255, 130, 110)]


class Source:
    """The unshaded fitted pieces of one race sheet, state -> cells (frame-major, then facing)."""

    def __init__(self, sheet, srcs):
        self.sheet, self.srcs, self.cache = sheet, srcs, {}

    def get(self, group, state):
        if group not in self.cache:
            for root in self.srcs:
                p = os.path.join(root, self.sheet, group + ".dmi")
                if os.path.exists(p):
                    self.cache[group] = {n: (m, c) for n, m, c in ge.read_dmi_full(p)}
                    break
        return self.cache[group][state]


def in_ramp(cell, ramp):
    """Per pixel: its level in the ramp (0-4), or -1."""
    lv = np.full(cell.shape[:2], -1)
    for i, col in enumerate(ramp):
        lv[(cell[..., 3] > 0) & (cell[..., :3] == np.array(col, np.uint8)).all(-1)] = i
    return lv


def recolour(cell, src, dst, where=None):
    out = cell.copy()
    lv = in_ramp(cell, src)
    for i, col in enumerate(dst):
        m = lv == i
        if where is not None:
            m &= where
        out[m, :3] = col
    return out


def n4(m):
    p = np.pad(m, 1)
    return p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]


def trim(cell, src, dst, width=1):
    """An edge just inside the outline in another metal, lifted to its bright levels (the edge
    of a piece mostly lies in shadow, where gold would read as brown): `width` pixels wide."""
    a = cell[..., 3] > 0
    edge = a & n4(~a)
    out = cell.copy()
    lv = in_ramp(cell, src)
    inner, prev = edge, edge
    for k in range(width):
        ring = a & ~inner & n4(prev)
        lift = np.clip(lv + 1 - k, 2 - k, 4 - k)
        for i, col in enumerate(dst):
            out[ring & (lv >= 0) & (lift == i)] = list(col) + [255]
        inner, prev = inner | ring, ring
    return out


def overlay(cell, top, ramp, recol=None):
    """top's pixels drawn in `ramp` (horns, a plume) laid over cell, optionally recoloured."""
    m = in_ramp(top, ramp) >= 0
    out = cell.copy()
    piece = top if recol is None else recolour(top, ramp, recol)
    out[m] = piece[m]
    return out


def components(m):
    """The 8-connected parts of a mask, each as its own mask."""
    left, out = m.copy(), []
    while left.any():
        y, x = map(int, np.argwhere(left)[0])
        part, todo = np.zeros_like(m), [(y, x)]
        left[y, x] = False
        while todo:
            y, x = todo.pop()
            part[y, x] = True
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < 64 and 0 <= xx < 64 and left[yy, xx]:
                        left[yy, xx] = False
                        todo.append((yy, xx))
        out.append(part)
    return out


def horns_down(top, ramp):
    """top's pixels in `ramp` (a horned helm's horns), each horn flipped about the row it grows
    from (its lowest) so it sweeps out and down instead of up."""
    out = np.zeros_like(top)
    for part in components(in_ramp(top, ramp) >= 0):
        ys, xs = np.nonzero(part)
        ny = 2 * ys.max() - ys
        ok = (ny >= 0) & (ny < 64)
        out[ny[ok], xs[ok]] = top[ys[ok], xs[ok]]
    return out


def shade(cell, metal=True):
    return e2.enhance_gear_cell(cell, metal_all=metal)


# --- gems and eyes, laid on the shaded piece ----------------------------------------------------

def inside(mask, x, y, r):
    """The mask pixel nearest (x, y) with its (2r+1)^2 neighbourhood all in the mask, or None."""
    core = mask.copy()
    for _ in range(r):   # eroded by a square of radius r
        p = np.pad(core, 1)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                core &= p[1 + dy:65 + dy, 1 + dx:65 + dx]
    ys, xs = np.nonzero(core)
    if not len(ys):
        return None
    d = (xs - x) ** 2 + (ys - y) ** 2
    j = int(np.argmin(d))
    return (int(xs[j]), int(ys[j])) if d[j] <= 36 else None


def gem(cell, mask, x, y, ramp, big):
    """A cut gem centred near (x, y): a core of 2 or 3 pixels square, lit from the top left, in a
    dark rim with its corners off; only where the piece is."""
    at = None
    for n, r in ((3, 2), (2, 1), (2, 0)) if big else ((2, 1), (2, 0)):   # smaller where the piece is thin (a helmet's brow band)
        at = inside(mask, x, y, r)
        if at is not None:
            break
    if at is None:
        return
    x0, y0 = at[0] - n // 2, at[1] - n // 2
    rim, dark, mid, light, glint = ramp
    for j in range(-1, n + 1):
        for i in range(-1, n + 1):
            xx, yy = x0 + i, y0 + j
            if not (0 <= xx < 64 and 0 <= yy < 64) or not mask[yy, xx]:
                continue
            corner = i in (-1, n) and j in (-1, n)
            if corner:
                continue
            if i in (-1, n) or j in (-1, n):
                col = rim
            elif i == 0 and j == 0:
                col = glint
            elif i + j <= 1:
                col = light
            elif i == n - 1 and j == n - 1:
                col = dark
            else:
                col = mid
            cell[yy, xx, :3] = col
            cell[yy, xx, 3] = 255


def runs(row):
    xs = np.flatnonzero(row)
    if not len(xs):
        return []
    out, start = [], xs[0]
    for a, b in zip(xs, xs[1:]):
        if b != a + 1:
            out.append((start, a))
            start = b
    out.append((start, xs[-1]))
    return out


def brow(mask, x):
    """The last row of the first run from the top in column x (a helmet's brow there), or None."""
    col = mask[:, x]
    ys = np.flatnonzero(col)
    if not len(ys):
        return None
    y = ys[0]
    while y + 1 < 64 and col[y + 1]:
        y += 1
    return y


def leg_spots(mask, y, k):
    """Gem spots on the leggings' row y: one over each leg from the front or back, the front
    leg's from the side (k: 1 facing east, -1 west, 0 front/back)."""
    rr = sorted(runs(mask[y]), key=lambda r: r[1] - r[0], reverse=True)[:2]
    if not rr:
        return []
    if k:
        a, b = max(rr, key=lambda r: r[1] if k > 0 else -r[0])
        return [(a + b) / 2 + 1.5 * k]
    if len(rr) == 1:   # joined on this row: a spot over each leg
        a, b = rr[0]
        return [a + 0.27 * (b - a), a + 0.73 * (b - a)]
    return [(a + b) / 2 for a, b in rr]


def set_gems(cell, slot, d, ramp):
    """Gems where the original game's Ruby set has them: a helmet's brow and cheek guards, a
    chest's shoulder tips and belly, the knees and shins."""
    out = cell.copy()
    mask = out[..., 3] > 0
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return out
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    w_, h_ = x1 - x0, y1 - y0
    k = {"E": 1, "W": -1}.get(d, 0)
    if slot == "chest":
        top = ys <= y0 + 0.45 * h_
        tips = [(-1, xs[top].argmin()), (1, xs[top].argmax())]
        for side, j in tips:   # the shoulders' outer tips (only the front one from the side)
            if k and side != k:
                continue
            gem(out, mask, xs[top][j] - 2 * side, ys[top][j] + 1, ramp, False)
        if d != "N":
            gem(out, mask, (x0 + x1) / 2 + 2 * k, y0 + 0.7 * h_, ramp, True)
    elif slot == "legs" and d != "N":
        for fy in (0.38, 0.82):
            y = int(round(y0 + fy * h_))
            for cx in leg_spots(mask, y, k):
                gem(out, mask, cx, y, ramp, False)
    elif slot == "helmet" and d != "N":
        cx = (x1 if k > 0 else x0) - 3 * k if k else int(round(xs.mean()))
        by = brow(mask, int(round(cx)))
        if by is not None:
            gem(out, mask, cx, by - 3 if not k else by - 2, ramp, not k)
        third = w_ / 3
        for side in ((-1, 1) if not k else (-k,)):   # the cheek guards' ends; from the side, the back one
            band = (xs <= x0 + third) if side < 0 else (xs >= x1 - third)
            if band.any():
                j = ys[band].argmax()
                gem(out, mask, xs[band][j] - side, ys[band][j] - 1, ramp, False)
    return out


def red_eyes(cell, plain, d):
    """Light the great helm's eye slit (its darkest pixels inside the helm, on `plain`, the helm
    before it was shaded): two eyes from the front, one from the side, none from behind."""
    out = cell.copy()
    if d == "N":
        return out
    a = plain[..., 3] > 0
    full = a.copy()
    p = np.pad(a, 1)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            full &= p[1 + dy:65 + dy, 1 + dx:65 + dx]
    slit = full & (in_ramp(plain, R["iron"]) == 0)
    ys, xs = np.nonzero(slit)
    if not len(ys):
        return out
    top = ys.min()
    row = slit[top:top + 2]
    rx = np.flatnonzero(row.any(0))
    if d == "S":
        cx = (rx.min() + rx.max()) / 2
        pick = [x for x in rx if 2.5 <= abs(x - cx) <= 7.5]
    else:
        front = rx.max() if d == "E" else rx.min()
        pick = [x for x in rx if abs(x - front) <= 2]
    for x in pick:
        for y in range(top, top + 2):
            if slit[y, x]:
                out[y, x, :3] = EYE[1] if y == top else EYE[0]
                out[y, x, 3] = 255
    for x in pick[:1] if d == "S" else pick[-1:]:
        out[top, x, :3] = EYE[2]
    return out


# --- the states ------------------------------------------------------------------------------------

def per_cell(S, group, state, fn):
    """(meta, cells) of state built cell by cell: fn(cell, facing, index)."""
    meta, cells = S.get(group, state)
    dirs = int(meta.get("dirs", 1))
    return meta, [fn(c, "SNEW"[i % dirs] if dirs == 4 else "S", i) for i, c in enumerate(cells)]


def build(S):
    out = []

    def add(name, meta, cells):
        out.append((name, meta, cells))

    # Gold Trimmed (Dragoon): iron edged in gold
    for name, st, wd in (("chest.banded.iron+gold trim", "chest.banded.iron", 2), ("legs.plate.iron+gold trim", "legs.plate.iron", 2),
                         ("arms.plate.iron.L+gold trim", "arms.plate.iron.L", 1), ("arms.plate.iron.R+gold trim", "arms.plate.iron.R", 1)):
        add(name, *per_cell(S, "iron", st, lambda c, d, i, wd=wd: shade(trim(c, R["iron"], R["gold"], wd))))
    # its helm, as the original's: all gold, closed, a gold fin (the crested helm's crest in gold)
    _, crest = S.get("gold", "helmet.crested.gold")
    add("helmet.great helm.gold+crest", *per_cell(S, "gold", "helmet.great helm.gold",
        lambda c, d, i: shade(overlay(c, crest[i], R["plume"], R["gold"]))))
    # gem-set pieces: the plain piece, shaded, with gems
    for metal in ("iron", "silver", "gold"):
        for slot, st in (("chest", f"chest.plate.{metal}"), ("legs", f"legs.plate.{metal}"), ("helmet", f"helmet.kettle.{metal}")):
            for g, ramp in GEMS.items():
                add(f"{st}+{g}", *per_cell(S, metal, st, lambda c, d, i, sl=slot, rp=ramp: set_gems(shade(c), sl, d, rp)))
    # Skorn: chitin's spikes in steel; a closed horned helm with red eyes
    for name, st in (("chest.skorn", "chest.plate.chitin"), ("legs.skorn", "legs.plate.chitin"),
                     ("arms.skorn.L", "arms.plate.chitin.L"), ("arms.skorn.R", "arms.plate.chitin.R")):
        add(name, *per_cell(S, "chitin", st, lambda c, d, i: shade(recolour(c, R["chitin"], R["iron"]))))
    _, horns = S.get("iron", "helmet.horned.iron")

    def skorn_helm(c, d, i):
        plain = overlay(c, horns[i], R["horn"], R["iron"])
        return red_eyes(shade(plain), c, d)
    add("helmet.skorn", *per_cell(S, "iron", "helmet.great helm.iron", skorn_helm))
    # the Supernatural Bone helm: black steel edged in gold, bone horns sweeping out and down at
    # its sides and two spikes on top (the dragon great helm's horns, in bone)
    _, spikes = S.get("dragon", "helmet.great helm.dragon")

    def superbone(c, d, i):
        helm = trim(recolour(c, R["iron"], R["black"]), R["black"], R["gold"], 2)
        helm = overlay(helm, horns_down(horns[i], R["horn"]), R["horn"])
        return shade(overlay(helm, spikes[i], R["dragonhorn"], R["horn"]))
    add("helmet.superbone", *per_cell(S, "iron", "helmet.great helm.iron", superbone))
    # the original picks are all one material, haft and head (the catalogue's have wooden hafts)
    add("weapon.pickaxe.iron+iron haft", *per_cell(S, "iron", "weapon.pickaxe.iron", lambda c, d, i: shade(recolour(c, R["wood"], R["iron"]))))
    add("weapon.pickaxe.gold+gold haft", *per_cell(S, "gold", "weapon.pickaxe.gold", lambda c, d, i: shade(recolour(c, R["wood"], R["gold"]))))
    add("weapon.pickaxe.wood", *per_cell(S, "iron", "weapon.pickaxe.iron", lambda c, d, i: shade(recolour(c, R["iron"], R["wood"]), metal=False)))
    # Bloodwhisker and Soul Eater
    add("weapon.bloodwhisker", *per_cell(S, "iron", "weapon.spear.iron",
        lambda c, d, i: shade(recolour(recolour(c, R["wood"], DARK_GREEN), R["iron"], R["green"]))))
    add("weapon.soul eater", *per_cell(S, "iron", "weapon.arming sword.iron",
        lambda c, d, i: shade(recolour(c, R["iron"], R["venom"]))))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out")
    ap.add_argument("--src", action="append", default=[], help="unshaded Gear64 folders read before the restore point")
    ap.add_argument("--only", default=None, help="sheets to build (comma separated)")
    a = ap.parse_args()
    srcs = a.src + [RESTORE]
    sheets = [s for s in sorted(os.listdir(RESTORE)) if os.path.isdir(os.path.join(RESTORE, s)) and (not a.only or s in a.only.split(","))]
    for sheet in sheets:
        states = build(Source(sheet, srcs))
        path = os.path.join(a.out, sheet, "oldlooks.dmi")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ge.write_sheet(path, states, 64)
        print(sheet, len(states), flush=True)


if __name__ == "__main__":
    main()
