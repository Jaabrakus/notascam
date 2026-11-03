#!/usr/bin/env python3
"""Top-down pictures of formations (formations, 2026-10-25) from tests/real_formation_check.dm's files (RF_OUT): each
file "T,x,y" (the clicked tile), "W,x,y" (a wall) and "x,y,role" lines (a unit's slot, or where it stands). One picture
holds several panels side by side, each cropped round its own formation, the same scale in all of them.
  python3 tools/formations/formation_pictures.py OUT.png "Title" FILE:"panel title" [FILE:"panel title" ...]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

GROUND = (237, 232, 220)
WALL = (74, 74, 74)
INK = (34, 34, 34)
MUTED = (110, 106, 98)
ROLE = {'front': (213, 94, 0), 'ranged': (0, 114, 178), 'mage': (204, 121, 167), 'none': (150, 146, 138)}   # Okabe-Ito: safe for colour-blind eyes
NAMES = {'front': 'swords (front)', 'ranged': 'bows (ranged)', 'mage': 'magic (mage)', 'none': 'unarmed'}


def font(size, bold=False):
    for f in (['/System/Library/Fonts/Supplemental/Arial Bold.ttf'] if bold else []) + ['/System/Library/Fonts/Supplemental/Arial.ttf', '/Library/Fonts/Arial.ttf']:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def read(path):
    T, walls, units = None, [], []
    for line in Path(path).read_text().splitlines():
        p = line.split(',')
        if p[0] == 'T': T = (int(p[1]), int(p[2]))
        elif p[0] == 'W': walls.append((int(p[1]), int(p[2])))
        elif len(p) >= 3: units.append((int(p[0]), int(p[1]), p[2]))
    return T, walls, units


def main():
    out, title, panels = sys.argv[1], sys.argv[2], [a.split(':', 1) for a in sys.argv[3:]]
    data = [(read(f), t) for f, t in panels]
    boxes = []
    for (T, walls, units), _ in data:
        xs = [u[0] for u in units] + [w[0] for w in walls] + [T[0]]
        ys = [u[1] for u in units] + [w[1] for w in walls] + [T[1]]
        boxes.append((min(xs) - 3, max(xs) + 3, min(ys) - 3, max(ys) + 3))
    span = max(max(b[1] - b[0], b[3] - b[2]) for b in boxes) + 1
    s = max(1, min(14, 520 // span))   # pixels a tile, the same in every panel
    pad, head = 24, 64
    pw = [(b[1] - b[0] + 1) * s for b in boxes]
    ph = [(b[3] - b[2] + 1) * s for b in boxes]
    W = sum(pw) + pad * (len(pw) + 1)
    H = head + max(ph) + 40 + 56
    img = Image.new('RGB', (W, H), (250, 248, 243))
    d = ImageDraw.Draw(img)
    d.text((pad, 16), title, fill=INK, font=font(22, True))
    x = pad
    for ((T, walls, units), t), (x0, x1, y0, y1), w, h in zip(data, boxes, pw, ph):
        top = head + 26
        d.text((x, head), t, fill=INK, font=font(15, True))
        d.rectangle([x, top, x + w - 1, top + h - 1], fill=GROUND)
        px = lambda X: x + (X - x0) * s
        py = lambda Y: top + (y1 - Y) * s       # north up
        for X, Y in walls: d.rectangle([px(X), py(Y), px(X) + s - 1, py(Y) + s - 1], fill=WALL)
        for X, Y, r in units:
            c = ROLE.get(r, ROLE['front'])
            if s >= 3: d.rectangle([px(X), py(Y), px(X) + s - 2, py(Y) + s - 2], fill=c)
            else: d.rectangle([px(X), py(Y), px(X) + s - 1, py(Y) + s - 1], fill=c)
        k = max(3, s // 2 + 3)                  # the clicked tile
        cx, cy = px(T[0]) + s // 2, py(T[1]) + s // 2
        d.rectangle([cx - k, cy - k, cx + k, cy + k], outline=INK, width=2)
        d.text((x, top + h + 8), f'{len(units):,} units', fill=MUTED, font=font(13))
        x += w + pad
    # the legend: which colour is which role, and the clicked tile
    y = H - 34
    lx = pad
    roles = sorted({u[2] for (_, _, us), _ in data for u in us}, key=list(ROLE).index)
    for r in roles:
        d.rectangle([lx, y + 2, lx + 12, y + 14], fill=ROLE[r])
        d.text((lx + 18, y), NAMES[r], fill=INK, font=font(14))
        lx += 26 + int(d.textlength(NAMES[r], font=font(14)))
    d.rectangle([lx, y + 1, lx + 13, y + 15], outline=INK, width=2)
    d.text((lx + 20, y), 'the clicked tile', fill=INK, font=font(14))
    lx += 40 + int(d.textlength('the clicked tile', font=font(14)))
    if any(walls for (_, walls, _), _ in data):
        d.rectangle([lx, y + 2, lx + 12, y + 14], fill=WALL)
        d.text((lx + 18, y), 'wall', fill=INK, font=font(14))
    img.save(out)
    print('wrote', out, img.size, f'{s} px a tile')


if __name__ == '__main__':
    main()
