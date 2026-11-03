#!/usr/bin/env python3
"""GOA's own drawn body frames updated to 64 px (owner 11-01: "just make the original sprites updated").

    python3 standalone/hidden-clans/art/goa-actions/updated.py [base_m1]

The enhance pipeline the game's originals went through (art/enhance/remaster64.py): Scale2x, then form light from the
top-left in flat bands. Scale2x doubles GOA's 1 px outline; its outer half is dropped so the outline stays one pixel, as
on the 64 px bodies. No pixel is redrawn. Writes updated/<state>-<facing><frame>.png and updated/sheet.png.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "enhance"))
from remaster64 import form_light, rgba, up  # noqa: E402

GOA = os.path.expanduser("~/Downloads/GOA Source/icons")
STATES = ["", "Run", "PunchA-1", "PunchA-2", "KickA-1", "KickA-2"]
NAMES = {"": "Walk"}
DIRS = "SNEW"


def read_dmi(path):
    """{state: [frame][dir] -> 32 px RGBA image}; BYOND order is frame-major, directions inside."""
    im = Image.open(path)
    desc = im.info.get("Description", "")
    im = im.convert("RGBA")
    cols, out, i, cur = im.width // 32, {}, 0, None
    states = []
    for line in desc.splitlines():
        k, _, v = (s.strip() for s in line.partition("="))
        if k == "state":
            cur = {"name": v.strip('"'), "dirs": 1, "frames": 1}
            states.append(cur)
        elif cur and k in ("dirs", "frames"):
            cur[k] = int(v)
    for st in states:
        grid = []
        for _ in range(st["frames"]):
            row = []
            for _ in range(st["dirs"]):
                x, y = (i % cols) * 32, (i // cols) * 32
                row.append(im.crop((x, y, x + 32, y + 32)))
                i += 1
            grid.append(row)
        out[st["name"]] = grid
    return out


def thin_outline(a):
    """Drop the outer pixel of Scale2x's doubled outline: a dark pixel on the silhouette's edge whose inward
    neighbour is dark too."""
    al = a[..., 3] > 0
    dark = al & (a[..., :3].astype(int).sum(-1) < 120)
    pa, pd = np.pad(al, 1), np.pad(dark, 1)
    h, w = al.shape
    drop = np.zeros_like(al)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        outside = ~pa[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
        inward = pd[1 - dy:1 - dy + h, 1 - dx:1 - dx + w]
        drop |= dark & outside & inward
    out = a.copy()
    out[drop] = 0
    return out


def update(cell):
    return thin_outline(form_light(up(cell)))


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "base_m1"
    sheets = read_dmi(os.path.join(GOA, base + ".dmi"))
    dest = os.path.join(HERE, "updated")
    os.makedirs(dest, exist_ok=True)
    rows = []
    for st in STATES:
        nm = NAMES.get(st, st)
        for di, d in enumerate(DIRS):
            row = []
            for f, frame in enumerate(sheets[st]):
                b = Image.fromarray(update(frame[di]))
                b.save(os.path.join(dest, f"{nm}-{d}{f}.png"))
                row.append((frame[di], b))
            rows.append((f"{nm} {d}", row))
    # sheet: per row the originals doubled, then the updated frames, at 2x
    C, bg, cell = 128, (30, 32, 38), (70, 74, 84, 255)
    width = max(len(r) for _, r in rows) * 2 * (C + 4) + 120
    sheet = Image.new("RGB", (width, len(rows) * (C + 6) + 6), bg)
    dr = ImageDraw.Draw(sheet)
    for i, (label, row) in enumerate(rows):
        y = 6 + i * (C + 6)
        dr.text((4, y + C // 2 - 6), label, fill=(230, 230, 230))
        for j, (o, b) in enumerate(row):
            for k, im in enumerate((o.resize((64, 64), Image.NEAREST), b)):
                t = Image.new("RGBA", (64, 64), cell)
                t.alpha_composite(im.convert("RGBA"))
                x = 90 + (k * len(row) + j) * (C + 4) + (20 if k else 0)
                sheet.paste(t.resize((C, C), Image.NEAREST), (x, y))
    sheet.save(os.path.join(dest, "sheet.png"))
    print(dest, sheet.size)


if __name__ == "__main__":
    main()
