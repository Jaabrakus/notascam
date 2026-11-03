#!/usr/bin/env python3
"""What each pixel of GOA's frames is (owner 11-01: "do a pixel overlay ... what each pixel is so you can expand it for
the bodies"): every pixel of an updated GOA frame gets a body part, from GOA's skeleton for that frame (goa-joints.json,
read off GOA's own frames) and GOA's draw order: a pixel inside several limbs belongs to the one drawn on top.

    python3 standalone/hidden-clans/art/goa-actions/partmap.py [E]      (writes partmap/<facing>-overlay.png)
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from updated import DIRS, GOA, NAMES, read_dmi, update  # noqa: E402

JOINTS = json.load(open(os.path.join(HERE, "goa-joints.json")))
# bone: (from, to, radius at 64 px); a foot runs from the ankle to the toe, which points the way the body faces
BONES = {"torso": ("N", "P", 9.0), "RUp": ("RS", "RE", 3.5), "RFore": ("RE", "RH", 3.5), "LUp": ("LS", "LE", 3.5),
         "LFore": ("LE", "LH", 3.5), "RThigh": ("RHp", "RK", 4.5), "RShin": ("RK", "RA", 3.5), "RFoot": ("RA", "RT", 2.5),
         "LThigh": ("LHp", "LK", 4.5), "LShin": ("LK", "LA", 3.5), "LFoot": ("LA", "LT", 2.5)}
# drawn on top first; from the side the near (right, East) arm is over everything, the far limbs under the body
ORDER = {"E": ["RFore", "RUp", "RFoot", "RShin", "RThigh", "torso", "LFoot", "LShin", "LThigh", "LFore", "LUp"],
         "W": ["LFore", "LUp", "LFoot", "LShin", "LThigh", "torso", "RFoot", "RShin", "RThigh", "RFore", "RUp"],
         # from the front and back the arms hang beside the body, over it where they cross; the shorts over the thighs
         "S": ["RFore", "LFore", "RUp", "LUp", "RFoot", "LFoot", "RShin", "LShin", "torso", "RThigh", "LThigh"],
         "N": ["RFore", "LFore", "RUp", "LUp", "RFoot", "LFoot", "RShin", "LShin", "torso", "RThigh", "LThigh"]}
TORSO_R = {"E": 9.0, "W": 9.0, "S": 11.0, "N": 11.0}     # the body is wider from the front
PARTS = ["head"] + list(BONES)
COLOURS = {"head": (200, 200, 200), "torso": (240, 200, 60), "RUp": (230, 60, 50), "RFore": (255, 140, 40),
           "LUp": (150, 70, 200), "LFore": (230, 90, 220), "RThigh": (50, 110, 240), "RShin": (60, 210, 240),
           "RFoot": (40, 160, 150), "LThigh": (60, 190, 80), "LShin": (170, 230, 60), "LFoot": (120, 130, 40)}
TOE = {"E": (5, 1), "W": (-5, 1), "S": (0, 2), "N": (0, -1)}


def skeleton(facing, state, frame):
    """The frame's joints at 64 px (pixel centres), toes added."""
    j = {k: np.array([2 * v[0] + 1.0, 2 * v[1] + 1.0]) for k, v in JOINTS[facing][state][frame].items()}
    t = np.array(TOE[facing], float)
    j["RT"], j["LT"] = j["RA"] + t, j["LA"] + t
    return j


def seg_dist(p, a, b):
    """Distance from points p (n, 2) to segment ab, and where along it (0..1)."""
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-6), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1), t


def part_map(img, head, j, facing):
    """img: the 64 px frame, head: its head mask. Returns an int map (index into PARTS, -1 empty)."""
    al = img[..., 3] > 0
    out = np.full(al.shape, -1, int)
    out[head & al] = 0
    ys, xs = np.nonzero(al & ~head)
    p = np.stack([xs + 0.5, ys + 0.5], 1)
    nd = {b: seg_dist(p, j[f], j[t])[0] / (TORSO_R[facing] if b == "torso" else r) for b, (f, t, r) in BONES.items()}
    best = np.full(len(p), -1)
    for b in reversed(ORDER[facing]):                         # later (lower) parts first, so the top one wins
        best = np.where(nd[b] <= 1.0, PARTS.index(b), best)
    nearest = np.argmin(np.stack([nd[b] for b in BONES]), 0)
    best = np.where(best < 0, np.array([PARTS.index(b) for b in BONES])[nearest], best)
    out[ys, xs] = best
    return out


def frames(facing):
    from heads import GOA_HEAD_ROWS, head_offset
    goa = read_dmi(os.path.join(GOA, "base_m1.dmi"))
    rest = goa[""][0][DIRS.index(facing)]
    t = np.asarray(rest.convert("RGBA"))[:GOA_HEAD_ROWS, :, 3] > 0
    for state, rows in JOINTS[facing].items():
        for f, j in enumerate(rows):
            cell = goa[state][f][DIRS.index(facing)]
            img = update(cell)
            dx, dy = head_offset(rest, cell)
            head = np.zeros(img.shape[:2], bool)
            for y, x in zip(*np.nonzero(t)):
                Y, X = (y + dy) * 2, (x + dx) * 2
                if 0 <= Y < 63 and 0 <= X < 63:
                    head[Y:Y + 2, X:X + 2] = True
            yield state, f, img, head & (img[..., 3] > 0), skeleton(facing, state, f)


def main():
    facing = sys.argv[1] if len(sys.argv) > 1 else "E"
    dest = os.path.join(HERE, "partmap")
    os.makedirs(dest, exist_ok=True)
    Z, cells = 3, []
    for state, f, img, head, j in frames(facing):
        pm = part_map(img, head, j, facing)
        np.save(os.path.join(dest, f"{NAMES.get(state, state)}-{facing}{f}.npy"), pm)
        col = np.zeros_like(img)
        for i, name in enumerate(PARTS):
            col[pm == i] = (*COLOURS[name], 255)
        over = img.astype(float).copy()
        m = pm >= 0
        over[m, :3] = over[m, :3] * 0.45 + col[m, :3] * 0.55
        trip = []
        for a in (img, col, over.astype(np.uint8)):
            t = Image.new("RGBA", (64, 64), (70, 74, 84, 255))
            t.alpha_composite(Image.fromarray(a))
            trip.append(t.resize((64 * Z, 64 * Z), Image.NEAREST))
        dr = ImageDraw.Draw(trip[2])
        for f_, t_, _ in BONES.values():
            dr.line([tuple(j[f_] * Z), tuple(j[t_] * Z)], fill=(255, 255, 255), width=1)
        cells.append((f"{NAMES.get(state, state)} {facing}{f}", trip))
    C = 64 * Z
    per = 2
    rows = (len(cells) + per - 1) // per
    sheet = Image.new("RGB", (per * (3 * (C + 4) + 20), rows * (C + 18)), (30, 32, 38))
    dr = ImageDraw.Draw(sheet)
    for i, (label, trip) in enumerate(cells):
        x0, y0 = (i % per) * (3 * (C + 4) + 20), (i // per) * (C + 18)
        dr.text((x0 + 2, y0 + 2), label + ": GOA | parts | overlay", fill=(230, 230, 230))
        for k, t in enumerate(trip):
            sheet.paste(t, (x0 + k * (C + 4), y0 + 16))
    sheet.save(os.path.join(dest, f"{facing}-overlay.png"))
    print(os.path.join(dest, f"{facing}-overlay.png"), sheet.size)


if __name__ == "__main__":
    main()
