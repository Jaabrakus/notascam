#!/usr/bin/env python3
"""The resource sack's picture (Yield.dm's sack, game/Code/Remastered/Sack.dm): a bulging leather sack worn
on the back where the quiver sits. Drawn over the leather quiver's own frames (Quiver.dmi: 32 px, 4 dirs,
3 walking frames), so it sits and bobs exactly as the quiver does. Writes game/Icons/Remastered/Sack.dmi.

    /usr/bin/python3 art/sack/make_sack_icon.py
"""
from pathlib import Path
from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT/'game/Icons/Quiver.dmi'
OUT = ROOT/'game/Icons/Remastered/Sack.dmi'

OUTLINE = (46, 30, 16, 255)
DARK = (86, 60, 32, 255)
MID = (126, 92, 52, 255)
LIGHT = (164, 126, 76, 255)
TIE = (60, 40, 22, 255)


def width(t):
    """Half-width (0..1) of the sack t of the way down: pinched under the tie, a round full belly."""
    import math
    f = 0.38 + 0.62 * math.sin(min(t / 0.5, 1) * math.pi / 2)
    if t > 0.72: f *= math.sqrt(max(0.0, 1 - ((t - 0.72) / 0.28) ** 2 * 0.55))
    return f


def blob(frame, cx, top, w, h, facing):
    """A sack w x h with its neck at (cx, top): a flared, tied neck, a round belly, light from the upper left."""
    px = frame.load()
    neck = 3
    body_top = top + neck
    bh = h - neck
    rows = []
    for y in range(bh):
        t = (y + 0.5) / bh
        half = (w / 2) * width(t)
        rows.append((int(round(cx - half)), int(round(cx + half))))
    for y, (a, b) in enumerate(rows):
        for x in range(a, b):
            if not (0 <= x < 32 and 0 <= body_top + y < 32): continue
            u = (x + 0.5 - a) / max(1, b - a)
            t = (y + 0.5) / bh
            above = rows[y - 1] if y else (a + 1, b - 1)
            below = rows[y + 1] if y + 1 < len(rows) else None
            edge = x in (a, b - 1) or below is None or x < above[0] or x >= above[1] or (below and (x < below[0] or x >= below[1]))
            if edge: c = OUTLINE
            elif u < 0.4 and 0.12 < t < 0.65: c = LIGHT
            elif u > 0.68 or t > 0.8: c = DARK
            else: c = MID
            px[x, body_top + y] = c
    # the neck: a pinched cord with the tied top flaring out above it
    n = int(round(cx))
    for x in (n - 1, n, n + 1):
        if 0 <= x < 32:
            px[x, top] = OUTLINE if x != n else MID        # the flared top
            px[x, top + 2] = TIE                            # the cord
    if 0 <= n < 32: px[n, top + 1] = DARK
    # a patch on the back view
    if facing == 'N' and bh >= 7:
        py = body_top + bh // 2
        for x in (n, n + 1):
            for y in (py, py + 1):
                if 0 <= x < 32 and y < 32: px[x, y] = DARK


def main():
    src = Image.open(SRC)
    desc = src.info['Description']
    im = src.convert('RGBA')
    cols = im.size[0] // 32
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    for i in range(im.size[0] // 32 * (im.size[1] // 32)):
        x0, y0 = (i % cols) * 32, (i // cols) * 32
        tile = im.crop((x0, y0, x0 + 32, y0 + 32))
        box = tile.getbbox()
        if not box: continue
        facing = 'SNEW'[i % 4]
        frame = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        l, t, r, b = box
        cx = (l + r - 1) / 2
        if facing == 'S':
            # seen from the front: only its tied neck shows over the shoulder
            blob(frame, cx + 0.5, t - 2, 6, 6, facing)
        elif facing == 'N':
            blob(frame, cx, t - 2, 9, b - t + 3, facing)
        else:
            # from the side it bulges away from the body
            out_dx = 1 if facing == 'E' else -1
            blob(frame, cx + out_dx * 0.5, t - 2, 8, b - t + 3, facing)
        out.paste(frame, (x0, y0))
    info = PngImagePlugin.PngInfo()
    info.add_text('Description', desc, zip=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT, format='PNG', pnginfo=info)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
