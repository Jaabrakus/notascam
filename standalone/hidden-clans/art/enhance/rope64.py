#!/usr/bin/env python3
"""A captive's rope on its 64 px body (Captives.dm, View3D.dm Remaster3DLayers): fitted to every pose, facing and walk
frame of each race's body sheet, so it stays on whatever the body does (walking on the leash, lying knocked out).

    python3 standalone/remastered/art/enhance/rope64.py [--preview out.png]

Writes game/Icons/Remastered/Rope64/<sheet>.dmi for the body sheets the gear is fitted to (Gear64/<sheet>):
  "<kind>|<pose>"         bound: two turns of rope lashing the arms to the body (upper arms, then forearms and
                          waist), a knot with a loose end; chains as heavy links
  "hobble-<kind>|<pose>"  a slave's hobble: a turn round each ankle and a short slack length between them
kind: plant, leather, silk, chains; pose: the body sheet's state ("" for the whole body). Drawn in the wearables'
manner (lit from the top-left, outlined in the material's darkest colour, the rope's laid strands as a twist).
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
from game_export import read_dmi_full, write_sheet  # noqa: E402

GAME = os.path.join(HERE, "..", "..", "game")
RACES = os.path.join(GAME, "Icons", "Remastered", "Races64")
OUT = os.path.join(GAME, "Icons", "Remastered", "Rope64")
SHEETS = ["Demon", "DevourerZombie", "Dwarves", "FrogMan", "Gargoyle", "Goblins", "Human", "Kobold", "LizardMan",
          "Night Elf", "Orc", "Skeleton", "Vampire"]
FIBRE = [(40, 36, 14), (92, 86, 38), (140, 130, 64), (182, 170, 98), (220, 210, 146)]
KINDS = {"plant": FIBRE, "leather": w.RAMPS["leather"], "silk": w.RAMPS["spidersilk"], "chains": w.RAMPS["iron"]}


def body_box(mask):
    ys = np.flatnonzero(mask.any(1))
    return (int(ys.min()), int(ys.max())) if len(ys) else (None, None)


def span(mask, y):
    xs = np.flatnonzero(mask[y])
    return (int(xs.min()), int(xs.max())) if len(xs) else (None, None)


def arm_rows(mask, top, bot):
    """The rows where the arms hang beside the body: the widest part of its middle."""
    h = bot - top
    rows = list(range(top + int(h * 0.36), top + int(h * 0.82) + 1))
    widths = [(span(mask, y)[1] - span(mask, y)[0]) if span(mask, y)[0] is not None else 0 for y in rows]
    wmax = max(widths) if widths else 0
    wide = [y for y, wd in zip(rows, widths) if wd >= wmax * 0.72]
    return wide if len(wide) >= 4 else rows


def band(lay, mask, y, ramp, kind, knot=False, front=True):
    """One turn of rope (2 px) across row y and y+1 of the body, a px past each side (it goes round), outlined."""
    rope = np.zeros((64, 64), bool)
    for yy in (y, y + 1):
        x0, x1 = span(mask, yy)
        if x0 is None:
            continue
        rope[yy, max(0, x0 - 1):min(64, x1 + 2)] = True
    if not rope.any():
        return
    lv = np.zeros((64, 64), int)
    lv[y] = 3
    lv[y + 1] = 2
    xx = np.arange(64)[None, :]
    if kind == "chains":   # links: a bright stud every third pixel, dark gaps between links
        lv[y:y + 2] = np.where((xx % 3) == 0, 4, np.where((xx % 3) == 2, 1, lv[y:y + 2]))
    else:                   # laid strands: a dark diagonal every third pixel, the twist running the other way below
        lv[y] = np.where((xx[0] % 3) == 0, 1, lv[y])
        lv[y + 1] = np.where(((xx[0] + 1) % 3) == 0, 1, lv[y + 1])
    if knot and kind != "chains":
        x0, x1 = span(mask, y + 1)
        if x0 is not None:
            cx = (x0 + x1) // 2 + (1 if front else -1)
            for dy, dx, l in ((-1, 0, 3), (0, -1, 3), (0, 0, 4), (0, 1, 2), (1, -1, 2), (1, 0, 3), (1, 1, 1),
                              (2, 1, 2), (3, 1, 2), (4, 2, 1), (2, 0, 2), (3, -1, 2), (4, -1, 1)):
                yy, xx2 = y + dy, cx + dx
                if 0 <= yy < 64 and 0 <= xx2 < 64:
                    rope[yy, xx2] = True
                    lv[yy, xx2] = l
    pal = np.array(ramp, np.uint8)
    lay[rope, :3] = pal[np.clip(lv[rope], 1, 4)]
    lay[rope, 3] = 255
    ring = w.dilate(rope) & ~rope
    edge = ring & (np.arange(64)[:, None] != -1)
    lay[edge & ((np.arange(64)[:, None] < y) | (np.arange(64)[:, None] > y + 1) | ~mask), :3] = ramp[0]
    lay[edge & ((np.arange(64)[:, None] < y) | (np.arange(64)[:, None] > y + 1) | ~mask), 3] = 255


def hobble(lay, mask, top, bot, ramp, kind, facing):
    """A turn round each ankle (2 px, a little above the feet) and, facing you or away, a slack length between."""
    y = bot - 4
    legs = []
    xs = np.flatnonzero(mask[y])
    if not len(xs):
        return
    run = [xs[0]]
    for x in xs[1:]:
        if x == run[-1] + 1:
            run.append(x)
        else:
            legs.append((run[0], run[-1]))
            run = [x]
    legs.append((run[0], run[-1]))
    rope = np.zeros((64, 64), bool)
    lv = np.zeros((64, 64), int)
    for x0, x1 in legs:
        rope[y:y + 2, max(0, x0 - 1):min(64, x1 + 2)] = True
    lv[y] = 3
    lv[y + 1] = 2
    if facing in (0, 1) and len(legs) >= 2:   # between the feet: the slack, sagging a pixel
        a, b = legs[0][1] + 2, legs[-1][0] - 1
        for x in range(a, b):
            sag = 1 if a + 1 <= x < b - 1 else 0
            rope[y + 1 + sag, x] = True
            lv[y + 1 + sag, x] = 2 if (x % 2) else 3
    xx = np.arange(64)[None, :]
    if kind == "chains":
        lv = np.where(rope & ((xx % 3) == 0), 4, lv)
    else:
        lv = np.where(rope & ((xx % 3) == 0), 1, lv)
    pal = np.array(ramp, np.uint8)
    lay[rope, :3] = pal[np.clip(lv[rope], 1, 4)]
    lay[rope, 3] = 255
    ring = w.dilate(rope) & ~rope & ~mask
    lay[ring, :3] = ramp[0]
    lay[ring, 3] = 255


def rope_cell(body, ramp, kind, facing, hob=False):
    mask = body[..., 3] > 0
    lay = np.zeros((64, 64, 4), np.uint8)
    top, bot = body_box(mask)
    if top is None or bot - top < 12:
        return lay
    if hob:
        hobble(lay, mask, top, bot, ramp, kind, facing)
        return lay
    rows = arm_rows(mask, top, bot)
    y1 = rows[int(len(rows) * 0.22)]
    y2 = rows[min(len(rows) - 2, int(len(rows) * 0.72))]
    if y2 - y1 < 4:
        y2 = min(bot - 3, y1 + 4)
    band(lay, mask, y1, ramp, kind)
    band(lay, mask, y2, ramp, kind, knot=facing in (0, 2, 3), front=facing != 3)
    return lay


def sheet_states(sheet):
    out = []
    for name, meta, cells in read_dmi_full(os.path.join(RACES, f"{sheet}.dmi")):
        if name == "Sleep":   # lying asleep: a captive knocked out lies as it stood (the 3D view turns it on its side)
            continue
        pose = "" if name in ("", "Normal") else name
        dirs = int(meta.get("dirs", 1))
        m = {"dirs": meta.get("dirs", 1), "frames": meta.get("frames", 1)}
        if "delay" in meta: m["delay"] = meta["delay"]
        for kind, ramp in KINDS.items():
            out.append((f"{kind}|{pose}", m, [rope_cell(c, ramp, kind, i % dirs if dirs == 4 else 0) for i, c in enumerate(cells)]))
            out.append((f"hobble-{kind}|{pose}", m, [rope_cell(c, ramp, kind, i % dirs if dirs == 4 else 0, hob=True) for i, c in enumerate(cells)]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", default=None, help="also write the bodies with their rope, enlarged, on grass")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for sheet in SHEETS:
        st = sheet_states(sheet)
        write_sheet(os.path.join(OUT, f"{sheet}.dmi"), st, 64)
        print(sheet, len(st), "states")
        if args.preview and sheet in ("Human", "Goblins", "Orc", "Dwarves", "Kobold", "LizardMan"):
            body = {("" if n in ("", "Normal") else n): c for n, _, c in read_dmi_full(os.path.join(RACES, f"{sheet}.dmi"))}
            ropes = {n: c for n, _, c in st}
            row = []
            for state in ("leather|", "silk|", "chains|", "hobble-plant|", "plant|NoRightLeg"):
                pose = state.split("|")[1]
                for i in range(4):
                    b = Image.fromarray(body[pose][i])
                    r = Image.fromarray(ropes[state][i])
                    c = Image.new("RGBA", (64, 64), (62, 92, 48, 255))
                    c.paste(b, (0, 0), b)
                    c.paste(r, (0, 0), r)
                    row.append(c)
            rows.append(row)
    if args.preview and rows:
        k = 2
        sheet = Image.new("RGBA", (len(rows[0]) * 64 * k, len(rows) * 64 * k), (62, 92, 48, 255))
        for j, row in enumerate(rows):
            for i, c in enumerate(row):
                sheet.paste(c.resize((64 * k, 64 * k), Image.NEAREST), (i * 64 * k, j * 64 * k))
        sheet.save(args.preview)


if __name__ == "__main__":
    main()
