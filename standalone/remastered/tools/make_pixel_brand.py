#!/usr/bin/env python3
"""Pixel-art Discord icon and banner for Banners of the Deep (the user: "if you made it in pixels it would look better").
Both are drawn at low resolution on a small fixed palette with hard edges, then scaled up with nearest-neighbour so
every art pixel stays a crisp square: the icon 64x64 -> 1024x1024 (x16), the banner 340x120 -> 1360x480 (x4), lettered in its own 5x7 pixel alphabet.
Writes art/brand/discord-app-icon-pixel-1024.png and art/brand/discord-banner-pixel-1360x480.png."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from make_client_brand import LINE1, LINE2, TITLE_FONT  # noqa: E402

INK = (16, 11, 8)
STONE = [(24, 20, 16), (33, 27, 21), (43, 35, 27), (55, 45, 34)]          # dark to light
GOLD = [(122, 86, 34), (184, 138, 58), (240, 200, 104), (255, 236, 170)]  # shadow, base, light, glint
RED = [(70, 12, 18), (110, 20, 28), (148, 32, 38), (178, 58, 56)]
SNOW = (246, 238, 214)

def stone(img, box, seed=7):
    """Stone: a top-lit gradient in four shades, broken up with an ordered dither and a few speckles."""
    x0, y0, x1, y1 = box
    bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    px = img.load()
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        for x in range(x0, x1):
            v = (1 - t) * 2.6 + (bayer[y % 4][x % 4] / 16 - 0.5)
            px[x, y] = STONE[max(0, min(3, int(v + 0.5)))]
    r = seed
    for _ in range((x1 - x0) * (y1 - y0) // 60):     # speckles
        r = (r * 1103515245 + 12345) & 0x7fffffff
        x, y = x0 + r % (x1 - x0), y0 + (r // 97) % (y1 - y0)
        px[x, y] = STONE[3] if (r >> 5) & 1 else STONE[0]

def frame(d, box, inset=1):
    """Ink outline, then a gold rim with a light top-left edge and a dark bottom-right one."""
    x0, y0, x1, y1 = box
    d.rectangle(box, outline=INK)
    for i, (a, b) in enumerate(((GOLD[2], GOLD[0]), (GOLD[1], GOLD[1]))):
        k = inset + i
        d.line((x0 + k, y0 + k, x1 - k, y0 + k), fill=a); d.line((x0 + k, y0 + k, x0 + k, y1 - k), fill=a)
        d.line((x0 + k, y1 - k, x1 - k, y1 - k), fill=b); d.line((x1 - k, y0 + k, x1 - k, y1 - k), fill=b)
    d.rectangle((x0 + inset + 2, y0 + inset + 2, x1 - inset - 2, y1 - inset - 2), outline=INK)

def emblem(img, ox, oy, s=1):
    """The hanging banner: gold pole and finials, crimson swallowtail cloth with a gold border and folds, a gold
    mountain with a snow cap and a dark cave mouth. Designed on a 40x54 grid, drawn at s pixels per grid cell."""
    d = ImageDraw.Draw(img)
    def P(pts): return [(ox + x * s, oy + y * s) for x, y in pts]
    def R(x0, y0, x1, y1, c): d.rectangle((ox + x0 * s, oy + y0 * s, ox + (x1 + 1) * s - 1, oy + (y1 + 1) * s - 1), fill=c)
    # shadow behind the cloth
    d.polygon(P([(9, 6), (34, 6), (34, 53), (21, 46), (9, 53)]), fill=STONE[0])
    # cloth: ink outline, gold border, crimson field
    d.polygon(P([(6, 4), (33, 4), (33, 51), (19.5, 44), (6, 51)]), fill=INK)
    d.polygon(P([(7, 4), (32, 4), (32, 49), (19.5, 42), (7, 49)]), fill=GOLD[1])
    d.polygon(P([(9, 5), (30, 5), (30, 45), (19.5, 39), (9, 45)]), fill=RED[1])
    for x in (12, 16, 23, 27):                      # folds
        R(x, 5, x, 40, RED[0])
    R(9, 5, 10, 44, RED[2]); R(9, 5, 9, 43, RED[3])  # lit left edge
    R(7, 4, 7, 48, GOLD[2])                          # gold border highlight
    # pole and finials
    R(3, 2, 36, 3, GOLD[1]); R(3, 2, 36, 2, GOLD[2]); R(3, 4, 36, 4, INK)
    for fx in (1, 36):
        R(fx, 1, fx + 2, 4, GOLD[1]); R(fx, 1, fx + 1, 1, GOLD[3]); R(fx + 2, 3, fx + 2, 4, GOLD[0])
    # mountain: ink silhouette, gold faces, a lit left slope, a snow cap, the cave
    m = [(10, 33), (16, 18), (19, 22), (23, 14), (29, 33)]
    d.polygon(P([(x, y + 1) for x, y in m]), fill=INK)
    d.polygon(P(m), fill=GOLD[1])
    d.polygon(P([(10, 33), (16, 18), (17, 20), (13, 33)]), fill=GOLD[2])
    d.polygon(P([(23, 14), (29, 33), (26, 33), (24, 20)]), fill=GOLD[0])
    d.polygon(P([(23, 14), (25, 18), (24, 17.5), (23, 19), (21.5, 17)]), fill=SNOW)
    R(17, 27, 21, 33, INK); R(18, 26, 20, 26, INK)  # cave mouth
    R(9, 34, 30, 34, INK)                            # ground line

def icon():
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    stone(img, (2, 2, 62, 62))
    d = ImageDraw.Draw(img)
    frame(d, (1, 1, 62, 62))
    for x, y in ((1, 1), (62, 1), (1, 62), (62, 62), (2, 1), (1, 2), (61, 1), (62, 2), (1, 61), (2, 62), (62, 61), (61, 62)):
        img.putpixel((x, y), (0, 0, 0, 0))                       # rounded corners
    emblem(img, 12, 6, 1)
    return img.resize((1024, 1024), Image.NEAREST)

def text_pixels(text, size):
    """The brand's title lettering at pixel size, hard-edged (no anti-aliasing), as a 1-bit mask."""
    f = ImageFont.truetype(TITLE_FONT, size)
    l, t, r, b = f.getbbox(text)
    m = Image.new('1', (r - l + 2, b - t + 2), 0)
    dm = ImageDraw.Draw(m); dm.fontmode = '1'
    dm.text((1 - l, 1 - t), text, font=f, fill=1)
    return m

# A small 5x7 pixel alphabet for the banner's lettering (only the letters the name needs; add more as names change).
GLYPHS = {
 'A': ['.###.', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
 'B': ['####.', '#...#', '#...#', '####.', '#...#', '#...#', '####.'],
 'D': ['####.', '#...#', '#...#', '#...#', '#...#', '#...#', '####.'],
 'E': ['#####', '#....', '#....', '####.', '#....', '#....', '#####'],
 'F': ['#####', '#....', '#....', '####.', '#....', '#....', '#....'],
 'G': ['.####', '#....', '#....', '#..##', '#...#', '#...#', '.###.'],
 'H': ['#...#', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
 'L': ['#....', '#....', '#....', '#....', '#....', '#....', '#####'],
 'M': ['#...#', '##.##', '#.#.#', '#.#.#', '#...#', '#...#', '#...#'],
 'N': ['#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#', '#...#'],
 'O': ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
 'P': ['####.', '#...#', '#...#', '####.', '#....', '#....', '#....'],
 'R': ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'],
 'S': ['.####', '#....', '#....', '.###.', '....#', '....#', '####.'],
 'T': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
 'U': ['#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
}

def pixel_text(text, scale=1, gap=1, space=3):
    """The text in the pixel alphabet as a 1-bit mask, each font pixel scale x scale."""
    cols = []
    for ch in text.upper():
        if ch == ' ': cols += [[0] * 7] * space; continue
        g = GLYPHS[ch]
        cols += [[1 if g[r][c] == '#' else 0 for r in range(7)] for c in range(5)] + [[0] * 7] * gap
    cols = cols[:-gap] if cols else cols
    m = Image.new('1', (len(cols) * scale, 7 * scale), 0)
    d = ImageDraw.Draw(m)
    for c, col in enumerate(cols):
        for r, on in enumerate(col):
            if on: d.rectangle((c * scale, r * scale, (c + 1) * scale - 1, (r + 1) * scale - 1), fill=1)
    return m

def stamp(img, mask, x, y, fill, shade, outline):
    """Lettering with a one-pixel ink outline, a drop shadow and a darker lower half."""
    W, H = mask.size; mp = mask.load(); px = img.load()
    for dx, dy in ((1, 1), (2, 2)):
        for j in range(H):
            for i in range(W):
                if mp[i, j]: px[x + i + dx, y + j + dy] = outline
    for j in range(H):
        for i in range(W):
            if mp[i, j]:
                for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    if not (0 <= i + ox < W and 0 <= j + oy < H and mp[i + ox, j + oy]): px[x + i + ox, y + j + oy] = outline
    for j in range(H):
        for i in range(W):
            if mp[i, j]: px[x + i, y + j] = fill if j < H * 0.55 else shade

def banner():
    W, H = 340, 120                                  # x4 up to 1360x480
    img = Image.new('RGBA', (W, H))
    stone(img, (0, 0, W, H), seed=11)
    d = ImageDraw.Draw(img)
    frame(d, (0, 0, W - 1, H - 1)); frame(d, (2, 2, W - 3, H - 3))
    emblem(img, 12, 6, 2)
    t1 = pixel_text(LINE1, 2); t2 = pixel_text(LINE2, 1)
    cx = 100 + (W - 14 - 100) // 2
    stamp(img, t1, cx - t1.size[0] // 2, 36, GOLD[2], GOLD[1], INK)
    y2 = 36 + t1.size[1] + 12
    x2 = cx - t2.size[0] // 2
    stamp(img, t2, x2, y2, (232, 220, 190), (196, 180, 146), INK)
    d = ImageDraw.Draw(img)
    ry = y2 + 3
    for a, b in ((x2 - 22, x2 - 6), (x2 + t2.size[0] + 5, x2 + t2.size[0] + 21)):
        d.line((a, ry, b, ry), fill=GOLD[1]); d.line((a, ry + 1, b, ry + 1), fill=INK)
    return img.resize((W * 4, H * 4), Image.NEAREST)

if __name__ == '__main__':
    out = ROOT/'art/brand'
    icon().save(out/'discord-app-icon-pixel-1024.png', optimize=True)
    banner().convert('RGB').save(out/'discord-banner-pixel-1360x480.png', optimize=True)
    print('wrote', out/'discord-app-icon-pixel-1024.png', 'and', out/'discord-banner-pixel-1360x480.png')
