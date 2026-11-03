#!/usr/bin/env python3
"""Enhanced originals: the game's own 32 px sprites, upscaled to 64 px with
Scale2x (keeps the pixel-art look, smooths stair-step edges), then given a
light pass the originals lack: a top-left key light (lighter top edges,
darker lower edges inside each colour region) and a clean dark outline in a
darkened version of the touching colour. Same states, frames and timing.

    python3 standalone/remastered/art/enhance/enhance.py   (writes a sample sheet)
"""
import os, re, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pipeline'))
from make_comparison import read_dmi, GAME  # noqa: E402


def scale2x(a):
    """EPX/Scale2x on an RGBA array (h, w, 4) -> (2h, 2w, 4)."""
    h, w = a.shape[:2]
    p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode='edge')
    E = p[1:-1, 1:-1]; B = p[:-2, 1:-1]; H = p[2:, 1:-1]; D = p[1:-1, :-2]; F = p[1:-1, 2:]
    eq = lambda x, y: np.all(x == y, axis=2)
    c = ~eq(B, H) & ~eq(D, F)
    e0 = np.where((c & eq(D, B))[..., None], D, E)
    e1 = np.where((c & eq(B, F))[..., None], F, E)
    e2 = np.where((c & eq(D, H))[..., None], D, E)
    e3 = np.where((c & eq(H, F))[..., None], F, E)
    out = np.zeros((2 * h, 2 * w, 4), a.dtype)
    out[0::2, 0::2] = e0; out[0::2, 1::2] = e1; out[1::2, 0::2] = e2; out[1::2, 1::2] = e3
    return out


def light(a):
    """Inside each flat colour region: a pixel whose upper-left neighbour is a
    different colour (or empty) is lit, one whose lower-right neighbour differs is
    shaded. Gives the flat originals form without changing their design."""
    rgb = a[..., :3].astype(np.float32); al = a[..., 3] > 0
    out = rgb.copy()
    same = lambda dy, dx: np.all(np.roll(np.roll(a, dy, 0), dx, 1) == a, axis=2)
    lit = al & ~(same(1, 0) & same(0, 1))      # upper / left neighbour differs
    dark = al & ~(same(-1, 0) & same(0, -1))   # lower / right neighbour differs
    out[lit & ~dark] = np.minimum(255, out[lit & ~dark] * 1.18 + 12)
    out[dark & ~lit] = out[dark & ~lit] * 0.78
    a = a.copy(); a[..., :3] = out.astype(np.uint8)
    return a


def outline(a):
    al = a[..., 3] > 0
    rgb = a[..., :3].astype(np.float32)
    acc = np.zeros_like(rgb); n = np.zeros(al.shape, np.float32)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sa = np.roll(np.roll(al, dy, 0), dx, 1); sr = np.roll(np.roll(rgb, dy, 0), dx, 1)
        acc += sr * sa[..., None]; n += sa
    ring = ~al & (n > 0)
    out = a.copy()
    out[ring, :3] = np.minimum(acc[ring] / n[ring][:, None] * 0.28, 40).astype(np.uint8)
    out[ring, 3] = 255
    return out


def enhance(cell):
    a = np.asarray(cell.convert('RGBA')).copy()
    a[a[..., 3] < 128] = 0
    # the originals already carry a black outline; Scale2x keeps it, light() works inside it
    return Image.fromarray(light(scale2x(a)))


def main():
    picks = [('Orc.dmi', 'Normal'), ('Human.dmi', ''), ('Goblins.dmi', ''), ('Kobold.dmi', 'Normal'), ('LizardMan.dmi', ''),
             ('Vampire.dmi', ''), ('Skeleton.dmi', 'Normal'), ('Night Elf.dmi', 'Normal'), ('Wolf.dmi', None), ('dragons.dmi', None)]
    grass = read_dmi(os.path.join(GAME, 'Code', 'Building', 'Grounds.dmi'))['Grass'][0]
    C = 128
    rows = []
    for f, st in picks:
        S = read_dmi(os.path.join(GAME, 'Icons', f))
        st = st if st in S else next(iter(S))
        cells = S[st][:4]
        rows.append((f, cells))
    W = 20 + 8 * (C + 6); H = 30 + len(rows) * (C + 8)
    sheet = Image.new('RGBA', (W, H), (26, 24, 20, 255))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    d.text((20, 8), 'original 32 px (S N E W)                                                        enhanced 64 px (S N E W)', fill=(230, 220, 190))
    for r, (f, cells) in enumerate(rows):
        y = 26 + r * (C + 8)
        for i, c in enumerate(cells):
            for k, im in enumerate((c.resize((C, C), Image.NEAREST), enhance(c).resize((C, C), Image.NEAREST))):
                x = 20 + (i + 4 * k) * (C + 6) + (14 if k else 0)
                g = Image.new('RGBA', (32, 32)); g.paste(grass, (0, 0)); g = g.resize((C, C), Image.NEAREST)
                sheet.paste(g, (x, y)); sheet.alpha_composite(im, (x, y))
    out = os.path.join(HERE, 'sample.png'); sheet.save(out); print(out, sheet.size)


if __name__ == '__main__':
    main()
