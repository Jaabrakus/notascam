#!/usr/bin/env python3
"""Limb pieces for grafts and false limbs (Surgery.dm), from the enhanced 64 px races.

    python3 standalone/remastered/art/enhance/limbs64.py

Writes game/Icons/Remastered/Limbs64/<sheet>.dmi for each race sheet of Races64. For each slot
(LeftArm, RightArm, LeftLeg, RightLeg) the piece is the race's own limb, cut from its whole body
(the pixels its "No<slot>" state lacks), in every facing (arms in their three walk frames, legs
standing, as the original's legless states are). The shape is always the wearer's own, so it fits
the body from the front, the back and the side (from the side, a far limb the original hides
behind the body is drawn peeking out behind it); what changes is what it is made of:
  "<slot>@<donor>"   a graft: in the donor race's skin colours (its own arm's palette), with its
                     look where it has one (a skeleton's bones, a lizardman's scales, a frogman's
                     spots, a gargoyle's stone), and a row of stitches where it was sewn on
  "<slot>:<kind>"    a false limb: iron, wood (a peg), bone, gem (glimmering), automail

Read only: game/Icons/Remastered/Races64/<sheet>.dmi.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from game_export import read_dmi_full, write_sheet  # noqa: E402

GAME = os.path.join(os.path.dirname(os.path.dirname(HERE)), "game")
SRC = os.path.join(GAME, "Icons", "Remastered", "Races64")
OUT = os.path.join(GAME, "Icons", "Remastered", "Limbs64")
SHEETS = ["Demon", "DevourerZombie", "Dwarves", "FrogMan", "Gargoyle", "Goblins", "Human", "HumanBlack",
          "Kobold", "LizardMan", "Night Elf", "Orc", "Skeleton", "Vampire"]
SLOTS = ["LeftArm", "RightArm", "LeftLeg", "RightLeg"]
DIRS = 4   # S, N, E, W, as the DMI stores them

# False limbs: a dark, mid and light colour; the limb's own shading is mapped onto them.
RAMPS = {
    "iron": [(46, 49, 56), (112, 118, 128), (190, 196, 206)],
    "wood": [(66, 40, 18), (128, 84, 42), (186, 134, 80)],
    "bone": [(132, 122, 98), (210, 200, 176), (244, 238, 222)],
    "gem": [(26, 84, 120), (84, 186, 228), (214, 246, 255)],
    "automail": [(60, 64, 72), (150, 158, 170), (228, 234, 242)],
}


def ramp(cols, t):
    """t 0..1 along dark -> mid -> light."""
    a, b, c = (np.array(x, float) for x in cols)
    t = t[..., None]
    lo = a + (b - a) * np.clip(t * 2, 0, 1)
    return np.where(t < 0.5, lo, b + (c - b) * np.clip(t * 2 - 1, 0, 1))


def pieces(mask):
    """Connected pieces of a mask (8-neighbour): [(size, y0, y1, x0, x1, pixels)], biggest first."""
    seen = np.zeros_like(mask)
    out = []
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        stack, pts = [(y, x)], []
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            pts.append((cy, cx))
            for ny in (cy - 1, cy, cy + 1):
                for nx in (cx - 1, cx, cx + 1):
                    if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        ys, xs = zip(*pts)
        out.append((len(pts), min(ys), max(ys), min(xs), max(xs), pts))
    return sorted(out, key=lambda p: -p[0])


def cut(normal, missing):
    """The limb: what the whole body has and the body without it lacks. Only the limb itself and
    what touches it are kept (a race's states may differ elsewhere too: a lizardman's jaw)."""
    diff = np.any(normal != missing, axis=2) & (normal[..., 3] > 0)
    keep = np.zeros_like(diff)
    P = pieces(diff)
    if P:
        _, y0, y1, x0, x1, _ = P[0]
        for size, a0, a1, b0, b1, pts in P:
            if a1 >= y0 - 3 and a0 <= y1 + 3 and b1 >= x0 - 3 and b0 <= x1 + 3:
                for y, x in pts:
                    keep[y, x] = True
    part = np.zeros_like(normal)
    part[keep] = normal[keep]
    return part


def false_limb(part, kind):
    a = part[..., 3] > 0
    out = np.zeros_like(part)
    if not a.any():
        return out
    rgb = part[..., :3].astype(float)
    lum = rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11
    lo, hi = lum[a].min(), lum[a].max()
    t = (lum - lo) / max(1.0, hi - lo)
    col = ramp(RAMPS[kind], t)
    ys, xs = np.nonzero(a)
    y0, y1 = ys.min(), ys.max()
    if kind == "automail":
        # jointed steel: dark seams at the elbow or knee and the wrist or ankle, a brass bolt
        for f in (0.38, 0.72):
            row = int(round(y0 + (y1 - y0) * f))
            on = a[row]
            col[row][on] = (34, 36, 42)
        row = int(round(y0 + (y1 - y0) * 0.38))
        xs_row = np.nonzero(a[max(0, row - 1)])[0]
        if len(xs_row):
            col[max(0, row - 1), xs_row[len(xs_row) // 2]] = (206, 166, 72)
    elif kind == "wood":
        # grain: every third row a shade darker
        for row in range(y0, y1 + 1, 3):
            col[row][a[row]] *= 0.82
    elif kind == "gem":
        # facets: a bright glint every few pixels
        glint = ((ys + xs) % 5 == 0)
        col[ys[glint], xs[glint]] = (240, 252, 255)
    out[..., :3] = np.clip(col, 0, 255).astype(np.uint8)
    out[..., 3] = np.where(a, 255, 0)
    return out


OTHER = {"LeftArm": "RightArm", "RightArm": "LeftArm", "LeftLeg": "RightLeg", "RightLeg": "LeftLeg"}


def side_peek(part, ncells, states, slot, f, d, mframes, body):
    """From the side the original draws only the near arm and leg; the far one is hidden behind
    the body, so a replaced far limb would not show. It is drawn as the near limb's shape moved
    back (arms up to 5 pixels, legs 3, so it stays attached) until a third of it shows past the
    body, a little darker, where it peeks out (body: the picture without it)."""
    if (part[..., 3] > 0).sum() >= 15:
        return part   # the near limb: it shows as it is
    other = states.get("No" + OTHER[slot])
    if not other:
        return part
    om = int(other[0].get("frames", 1))
    near = cut(ncells[f * DIRS + d], other[1][min(f, om - 1) * DIRS + d])
    n = (near[..., 3] > 0).sum()
    if not n:
        return part
    step = -1 if d == 2 else 1   # facing east the back is to the left
    for s in range(2, 6 if "Arm" in slot else 4):   # back until a third shows (arms 5 at most, legs 3: still attached)
        shifted = np.roll(near, step * s, axis=1)
        peek = (shifted[..., 3] > 0) & (body[..., 3] == 0)
        if peek.sum() >= n / 3:
            break
    out = part.copy()
    out[peek, :3] = (shifted[peek, :3].astype(float) * 0.9).astype(np.uint8)
    out[peek, 3] = 255
    return out


def outline(rgb):
    """The dark browns and black the enhanced sheets outline with."""
    return rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11 < 34   # #371b00 is 32; a demon's reds 37+


def skin(parts):
    """A race's skin: the three commonest colours of its arms (outline left out; claws and the like are
    rarer), as dark, mid, light."""
    counts = {}
    for p in parts:
        a = (p[..., 3] > 0) & ~outline(p[..., :3].astype(float))
        for c in map(tuple, p[a][:, :3]):
            counts[c] = counts.get(c, 0) + 1
    top = sorted(counts, key=lambda c: -counts[c])[:3]
    top.sort(key=lambda c: c[0] * 0.3 + c[1] * 0.59 + c[2] * 0.11)
    if not top:
        return [(90, 90, 90), (150, 150, 150), (210, 210, 210)]
    return [top[0], top[len(top) // 2], top[-1]]


def graft(part, cols, sheet):
    """The wearer's limb in another race's skin, with that race's look, stitched on at the top."""
    a = part[..., 3] > 0
    out = part.copy()
    if not a.any():
        return out
    rgb = part[..., :3].astype(float)
    line = outline(rgb) & a
    body = a & ~line
    lum = rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11
    if body.any():
        lo, hi = lum[body].min(), lum[body].max()
        col = ramp(cols, (lum - lo) / max(1.0, hi - lo))
        ys, xs = np.nonzero(body)
        dark = np.array(cols[0], float) * 0.7
        if sheet == "Skeleton":
            gap = (ys % 5 == 0)                                   # between the bones
        elif sheet == "LizardMan":
            gap = ((xs + ys) % 3 == 0)                            # scales
        elif sheet == "FrogMan":
            gap = ((xs * 7 + ys * 13) % 11 == 0)                  # spots
        elif sheet == "Gargoyle":
            gap = ((xs * 5 + ys * 3) % 7 == 0)                    # stone
        else:
            gap = np.zeros(len(ys), bool)
        col[ys[gap], xs[gap]] = dark
        out[body, :3] = np.clip(col[body], 0, 255).astype(np.uint8)
        # stitches across the top, where it was sewn on
        y0 = ys.min() + 1
        for x in np.nonzero(body[y0])[0]:
            if x % 2 == 0:
                out[y0, x, :3] = (138, 32, 32)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    cuts, skins = {}, {}
    for sheet in SHEETS:
        path = os.path.join(SRC, sheet + ".dmi")
        if not os.path.exists(path):
            continue
        states = {name: (meta, cells) for name, meta, cells in read_dmi_full(path)}
        normal = states.get("Normal") or states.get("")
        if not normal:
            continue
        nmeta, ncells = normal
        nframes = int(nmeta.get("frames", 1))
        cuts[sheet] = []
        for slot in SLOTS:
            miss = states.get("No" + slot)
            if not miss:
                continue
            mframes = int(miss[0].get("frames", 1))
            frames = nframes if mframes >= nframes else 1   # legless states stand still
            parts = []
            for f in range(frames):
                for d in range(DIRS):
                    part = cut(ncells[f * DIRS + d], miss[1][min(f, mframes - 1) * DIRS + d])
                    if d >= 2:   # a side view: the far limb is hidden behind the body; show it peeking out
                        part = side_peek(part, ncells, states, slot, f, d, mframes, miss[1][min(f, mframes - 1) * DIRS + d])
                    parts.append(part)
            meta = {"dirs": "4", "frames": str(frames)}
            if frames > 1 and "delay" in nmeta:
                meta["delay"] = nmeta["delay"]
            cuts[sheet].append((slot, meta, parts))
        arms = [p for slot, _, parts in cuts[sheet] if "Arm" in slot for p in parts[:DIRS]]
        skins[sheet] = skin(arms)
    for sheet, slots in cuts.items():
        out_states = []
        for slot, meta, parts in slots:
            for donor in cuts:
                out_states.append((f"{slot}@{donor}", meta, [graft(p, skins[donor], donor) for p in parts]))
            for kind in RAMPS:
                if kind == "wood" and "Arm" in slot:
                    continue   # pegs are legs
                out_states.append((f"{slot}:{kind}", meta, [false_limb(p, kind) for p in parts]))
        if out_states:
            write_sheet(os.path.join(OUT, sheet + ".dmi"), out_states, slots[0][2][0].shape[0])
            print(sheet, len(out_states), "states")
    stale = os.path.join(OUT, "anchors.json")
    if os.path.exists(stale):
        os.remove(stale)


if __name__ == "__main__":
    main()
