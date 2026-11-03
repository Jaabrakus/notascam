"""Pictures of the generated world for the owner. python3 render.py [seed]

Writes into art/worldgen/out/: world map (with and without the old heartland), close-ups of a
few regions' tiles, the four layers of one region lined up, a seams check, and world.json.
"""
import json
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import worldgen as W
from heartland import *  # noqa: F401,F403
from noise import fbm, rand01

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FONT = "/System/Library/Fonts/Supplemental/Herculanum.ttf"

PAL = np.zeros((NKINDS, 3), np.float64)
for k, c in {
    K_DEEP: (30, 54, 80), K_WATER: (58, 98, 122), K_RIVER: (64, 108, 138), K_SWAMPW: (46, 76, 84),
    K_SAND: (206, 190, 146), K_SHORE: (150, 148, 136), K_GRASS: (112, 132, 72), K_FOREST: (52, 80, 42),
    K_JUNGLE: (38, 90, 50), K_DESERT: (200, 172, 114), K_MESA: (170, 104, 72), K_SNOW: (226, 228, 230),
    K_TUNDRA: (82, 102, 88), K_MARSH: (98, 110, 78), K_ROCK: (124, 116, 106), K_PEAK: (150, 142, 132),
    K_ASH: (72, 60, 56), K_BUILT: (190, 166, 124), K_SKY: (160, 196, 222), K_CAVEFLOOR: (54, 48, 44),
    K_LAVA: (232, 104, 32), K_CHASM: (8, 8, 10), K_DEADGRASS: (124, 112, 66), K_TUNNEL: (122, 108, 92),
    K_MOUTH: (16, 14, 14), K_WALL: (150, 144, 136), K_HOUSE: (140, 82, 60), K_FIELD: (176, 164, 92),
    K_ORE: (212, 180, 70), K_BRIDGE: (128, 96, 64), K_MUSHROOM: (138, 92, 150), K_STAIRSUP: (250, 220, 120),
    K_ROAD: (156, 128, 90), K_TOWN: (170, 156, 130), K_CLOUDSTONE: (214, 210, 200), K_FALLS: (236, 244, 248),
}.items():
    PAL[k] = c


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def hillshade(h, z):
    gy, gx = np.gradient(h)
    gx *= z
    gy *= z
    nz = 1 / np.sqrt(gx * gx + gy * gy + 1)
    L = np.array([-0.6, -0.6, 0.55])
    L /= np.linalg.norm(L)
    return np.clip((-gx * L[0] - gy * L[1] + L[2]) * nz, 0, 1)


def text(d, xy, s, f, fill=(40, 28, 16), halo=(236, 226, 200), anchor="mm"):
    x, y = xy
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            if dx or dy:
                d.text((x + dx, y + dy), s, font=f, fill=halo, anchor=anchor)
    d.text((x, y), s, font=f, fill=fill, anchor=anchor)


# ------------------------------------------------------------------------- world map
def world_image(w, px=2048, labels=True, title=None):
    t0 = time.time()
    tpp = W.WORLD / px
    c = (np.arange(px) + 0.5) * tpp
    wx, wy = np.meshgrid(c, c)
    h = w.height(wx, wy, 2 * tpp)
    t = w.sample(w.temp, wx, wy)
    m = w.sample(w.moist, wx, wy)
    k = w.heartland_blend(w.classify(h, t, m, w.ash(wx, wy)), wx, wy, 2 * tpp)
    if w.hl:
        sub = (wx >= W.HX0) & (wx < W.HX0 + W.HSIZE) & (wy >= W.HY0) & (wy < W.HY0 + W.HSIZE)
        k[sub] = w.hk[0][(wy[sub] - W.HY0).astype(int), (wx[sub] - W.HX0).astype(int)]
    col = PAL[k].copy()
    swampy = (k == K_MARSH) & (fbm(wx, wy, w.seed + 86, 300, 2 * tpp) * 2.6 > 0.2)
    col[swampy] = PAL[K_SWAMPW]
    # painted look: deeper sea darker, mountains lighter with height, snowy summits
    sea = h < 0
    depth = np.clip(-h / 0.5, 0, 1)[..., None]
    col[sea] = (np.array([66, 108, 130]) * (1 - depth) + np.array([22, 40, 62]) * depth)[sea]
    hi = np.clip((h - W.MOUNTAIN) / 0.5, 0, 1)[..., None]
    rock = k == K_ROCK
    col[rock] = (PAL[K_ROCK] * (1 - hi) + np.array([196, 190, 182]) * hi)[rock]
    col[rock & (h > W.PEAKS)] = (238, 238, 242)
    sh = hillshade(np.where(sea, 0, h), 900 / tpp * 2)
    shade = 0.62 + 0.55 * sh
    col[~sea] *= shade[~sea][:, None]
    col *= (1 + (rand01(np.arange(px)[None, :], np.arange(px)[:, None], 9) - 0.5) * 0.05)[..., None]
    sk, foam = w.sky_tiles(wx, wy, 2 * tpp)
    col[foam] = col[foam] * 0.3 + PAL[K_FALLS] * 0.7
    off = max(2, px // 300)
    shadow = np.roll(np.roll(sk > 0, off, 0), off, 1) & ~(sk > 0)
    col[shadow] *= 0.55
    col[sk > 0] = PAL[sk[sk > 0]] * (1.05 if px > 1500 else 1.0)
    img = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))
    # coastline ink
    edge = Image.fromarray(((sea ^ np.roll(sea, 1, 0)) | (sea ^ np.roll(sea, 1, 1))).astype(np.uint8) * 255)
    ink = Image.new("RGB", img.size, (38, 44, 50))
    img.paste(ink, mask=edge.filter(ImageFilter.GaussianBlur(0.6)))
    # borders of the old realms, dashed
    lo = w.land_of[np.minimum((wy / W.CELL).astype(int), W.G - 1), np.minimum((wx / W.CELL).astype(int), W.G - 1)]
    bd = ((lo != np.roll(lo, 1, 0)) | (lo != np.roll(lo, 1, 1))) & (lo >= 0) & (np.roll(lo, 1, 0) >= 0) & \
        (np.roll(lo, 1, 1) >= 0) & ~sea
    yy, xx = np.mgrid[0:px, 0:px]
    bd &= ((xx + yy) // max(2, px // 400)) % 2 == 0
    bimg = Image.fromarray(bd.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3 if px >= 1500 else 1))
    img.paste(Image.new("RGB", img.size, (126, 44, 32)), mask=bimg)
    S = 2  # draw lines at double size, then shrink for smooth edges
    big = img.resize((px * S, px * S), Image.BILINEAR)
    d = ImageDraw.Draw(big)
    sc = S / tpp
    for ln in w.lanes:
        p = ln["pts"][:, :2] * sc
        for i in range(0, len(p) - 1, 2):
            d.line([tuple(p[i]), tuple(p[i + 1])], fill=(196, 210, 222), width=S)
    for r in w.rivers:
        p = r["pts"]
        for i in range(len(p) - 1):
            wd = max(S, int(round(p[i, 2] * sc * 1.6)))
            d.line([tuple(p[i, :2] * sc), tuple(p[i + 1, :2] * sc)], fill=(66, 112, 146), width=wd)
    for r in w.roads:
        p = r["pts"][:, :2] * sc
        if r["kind"] == "main":
            d.line([tuple(q) for q in p], fill=(96, 62, 34), width=2 * S, joint="curve")
        else:
            d.line([tuple(q) for q in p], fill=(132, 104, 70), width=S)
    # the hex regions, faint
    over = Image.new("RGBA", big.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(over)
    for row in range(W.HROWS):
        for col in range(W.HCOLS):
            od.polygon(hex_corners(col, row, sc), outline=(235, 230, 215, 60))
    big = Image.alpha_composite(big.convert("RGBA"), over).convert("RGB")
    d = ImageDraw.Draw(big)
    for p in w.places:
        x, y = p["x"] * sc, p["y"] * sc
        kd = p["kind"]
        if kd == "lair":
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(150, 120, 40))
        elif kd == "hold":
            d.rectangle([x - 5, y - 5, x + 5, y + 5], fill=(110, 100, 92), outline=(250, 236, 200), width=2)
        elif kd in ("fallen_city", "heartland"):
            fc = (214, 170, 40) if kd == "heartland" else (96, 86, 80)
            d.rectangle([x - 10, y - 10, x + 10, y + 10], fill=fc, outline=(250, 236, 200), width=3)
            d.line([(x - 10, y - 10), (x + 10, y + 10)], fill=(250, 236, 200), width=2) if kd != "heartland" else None
            d.rectangle([x - 4, y - 4, x + 4, y + 4], fill=(250, 236, 200)) if kd == "heartland" else None
        elif kd == "delving":
            d.polygon([(x, y - 6), (x + 6, y), (x, y + 6), (x - 6, y)], fill=(120, 80, 170))
        elif kd == "ruin":
            d.line([(x - 4, y - 4), (x + 4, y + 4)], fill=(70, 66, 60), width=2)
            d.line([(x - 4, y + 4), (x + 4, y - 4)], fill=(70, 66, 60), width=2)
        elif kd == "dungeon":
            fc = {"dragon lair": (210, 40, 30), "hellgate": (250, 120, 20), "kobold warren": (40, 120, 200),
                  "goblin cave": (40, 120, 200)}.get(p.get("type"), (18, 16, 16))
            s = 9 if p.get("type") in ("dragon lair", "hellgate") else 6
            d.polygon([(x, y - s), (x + s, y + s * 0.8), (x - s, y + s * 0.8)], fill=fc)
    if w.hl:
        a, b = W.HX0 * sc, (W.HX0 + W.HSIZE) * sc
        d.rectangle([a, a, b, b], outline=(236, 196, 70), width=4)
    img = big.resize((px, px), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    if labels:
        f = font(max(14, px // 90))
        if w.hl:
            text(d, ((W.HX0 + 500) / tpp, (W.HY0 - 40) / tpp - px / 75), "The Old Heartland", font(max(16, px // 70)),
                 fill=(90, 40, 10))
        for p in w.places:
            if p["kind"] == "sky island" and p["great"]:
                isl = w.islands[0]
                ly = (p["y"] - isl["b"]) / tpp - px / 70
                if ly < px / 12:
                    ly = (p["y"] + isl["b"]) / tpp + px / 25
                text(d, (p["x"] / tpp, ly), p["name"], f, fill=(40, 70, 110))
                fx, fy = isl["falls"]
                text(d, (fx / tpp, fy / tpp + px / 60), "The Great Falls", font(max(12, px // 110)), fill=(40, 70, 110))
    if title:
        text(d, (px / 2, px / 34), title, font(px // 40), anchor="mm")
    w.log("world picture %.1fs" % (time.time() - t0))
    return img


def legend(img, w):
    d = ImageDraw.Draw(img)
    px = img.size[0]
    f = font(px // 80)
    rows = [("city", "Fallen city"), ("town", "Abandoned hold"), ("village", "Beast lair"), ("mine", "Old delving"),
            ("dungeon", "Cave or crypt"), ("folk", "Kobold or goblin cave"), ("lair", "Dragon lair"),
            ("gate", "Hellgate"), ("ruin", "Ruins"), ("road", "Old road"), ("river", "River"),
            ("lane", "Old sea lane")]
    lh = px // 46
    x0, y0 = px // 40 + 16, px - lh * len(rows) - px // 28
    d.rectangle([x0 - 16, y0 - 16, x0 + px // 4.3, y0 + lh * len(rows) + 8], fill=(232, 222, 196), outline=(90, 70, 40),
                width=3)
    for i, (kd, name) in enumerate(rows):
        x, y = x0 + 14, y0 + i * lh + lh / 2
        if kd == "city":
            d.rectangle([x - 9, y - 9, x + 9, y + 9], fill=(96, 86, 80), outline=(250, 236, 200), width=2)
            d.line([(x - 9, y - 9), (x + 9, y + 9)], fill=(250, 236, 200), width=2)
        elif kd == "town":
            d.rectangle([x - 5, y - 5, x + 5, y + 5], fill=(110, 100, 92))
        elif kd == "village":
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(150, 120, 40))
        elif kd == "folk":
            d.polygon([(x, y - 8), (x + 8, y + 6), (x - 8, y + 6)], fill=(40, 120, 200))
        elif kd == "border":
            for a in range(-12, 12, 5):
                d.line([(x + a, y), (x + a + 2, y)], fill=(120, 40, 30), width=3)
        elif kd == "mine":
            d.polygon([(x, y - 7), (x + 7, y), (x, y + 7), (x - 7, y)], fill=(120, 80, 170))
        elif kd in ("dungeon", "lair", "gate"):
            fc = {"dungeon": (18, 16, 16), "lair": (210, 40, 30), "gate": (250, 120, 20)}[kd]
            d.polygon([(x, y - 8), (x + 8, y + 6), (x - 8, y + 6)], fill=fc)
        elif kd == "ruin":
            d.line([(x - 5, y - 5), (x + 5, y + 5)], fill=(70, 66, 60), width=2)
            d.line([(x - 5, y + 5), (x + 5, y - 5)], fill=(70, 66, 60), width=2)
        elif kd == "road":
            d.line([(x - 12, y), (x + 12, y)], fill=(96, 62, 34), width=3)
        elif kd == "river":
            d.line([(x - 12, y), (x + 12, y)], fill=(66, 112, 146), width=4)
        elif kd == "lane":
            for a in range(-12, 12, 6):
                d.line([(x + a, y), (x + a + 3, y)], fill=(80, 110, 140), width=2)
        d.text((x + 24, y), name, font=f, fill=(40, 28, 16), anchor="lm")


# ------------------------------------------------------------------------- tiles
def tiles_image(k, h, scale=3, z=1):
    n = k.shape[0]
    col = PAL[k].copy()
    jit = rand01(np.arange(n)[None, :], np.arange(n)[:, None], 5 + z)
    col *= (0.94 + jit * 0.12)[..., None]
    if z == 1:
        sea = np.isin(k, [K_WATER, K_DEEP, K_RIVER, K_SWAMPW])
        sh = hillshade(np.where(sea, np.minimum(h, 0), h), 260)
        col[~sea] *= (0.7 + 0.45 * sh[~sea])[:, None]
        hi = np.clip((h - W.MOUNTAIN) / 0.45, 0, 1)
        rk = k == K_ROCK
        col[rk] = (col[rk] * (1 - hi[rk, None]) + np.array([200, 196, 190]) * hi[rk, None])
        dp = np.clip(-h / 0.3, 0, 1)[..., None]
        col[sea & (k != K_RIVER)] = (col * (1 - dp * 0.5))[sea & (k != K_RIVER)]
    big = np.repeat(np.repeat(col, scale, 0), scale, 1)
    if scale >= 3:
        # tree tops and roofs: a lighter middle pixel, a darker edge
        tree = np.isin(k, [K_FOREST, K_TUNDRA])
        if z == 1:
            tree |= (k == K_JUNGLE)
        ty, tx = np.nonzero(tree)
        big[ty * scale + 1, tx * scale + 1] *= 1.35
        big[ty * scale + scale - 1, tx * scale + scale - 1] *= 0.6
        hy, hx = np.nonzero(k == K_HOUSE)
        big[hy * scale, hx * scale] *= 1.2
        fy, fx = np.nonzero(k == K_FIELD)
        big[fy * scale + 1, fx * scale] *= 0.82
        reeds = (k == K_MARSH) & (jit > 0.7)
        ry, rx = np.nonzero(reeds)
        big[ry * scale, rx * scale + 1] = (150, 156, 96)
        big[ry * scale + 1, rx * scale + 1] = (120, 128, 80)
    return Image.fromarray(np.clip(big, 0, 255).astype(np.uint8))




# ------------------------------------------------------------------------- hexes
PAPER = np.array([236, 226, 200], float)


def hex_corners(col, row, sc=1.0, shrink=1.0):
    """Corners of a hex region in picture pixels (sc = pixels per tile), pointy top."""
    cx, cy = W.hex_center(col, row)
    return [((cx + W.HEX * shrink * np.cos(np.radians(60 * i - 30))) * sc,
             (cy + W.HEX * shrink * np.sin(np.radians(60 * i - 30))) * sc) for i in range(6)]


def hex_neighbours(col, row):
    """(direction, col, row) of the six neighbours; direction i shares corners i and i+1."""
    p = row & 1
    return [(0, col + 1, row), (1, col + p, row + 1), (2, col + p - 1, row + 1), (3, col - 1, row),
            (4, col + p - 1, row - 1), (5, col + p, row - 1)]


def hex_stats(w):
    """Per hex region: share of water and of mountain, the most common land, the realm at its centre."""
    hc, hr = W.hex_of(w.cwx, w.cwy)
    ok = (hc >= 0) & (hc < W.HCOLS) & (hr >= 0) & (hr < W.HROWS)
    idx = (hr * W.HCOLS + hc)[ok]
    N = W.HCOLS * W.HROWS
    tot = np.maximum(np.bincount(idx, minlength=N), 1)
    water = np.bincount(idx, weights=(w.h[ok] < 0), minlength=N) / tot
    deep = np.bincount(idx, weights=(w.h[ok] < -0.25), minlength=N) / tot
    mount = np.bincount(idx, weights=(w.h[ok] > W.MOUNTAIN), minlength=N) / tot
    b = w.biome[ok]
    land = ~np.isin(b, [K_ROCK, K_SAND, K_SHORE, K_WATER, K_DEEP, K_BUILT])
    counts = np.zeros((N, NKINDS))
    np.add.at(counts, (idx[land], b[land]), 1)
    major = counts.argmax(1)
    major[counts.sum(1) == 0] = K_ROCK
    col, row = np.meshgrid(np.arange(W.HCOLS), np.arange(W.HROWS))
    cx, cy = W.hex_center(col, row)
    realm = w.land_of[np.clip((cy // W.CELL).astype(int), 0, W.G - 1), np.clip((cx // W.CELL).astype(int), 0, W.G - 1)]
    heart = np.zeros((W.HROWS, W.HCOLS), bool)
    if w.hl:
        heart = (np.abs(cx - (W.HX0 + 500)) < 500 + W.HEX * 0.5) & (np.abs(cy - (W.HY0 + 500)) < 500 + W.HEX * 0.5)
    sh = (W.HROWS, W.HCOLS)
    return {"water": water.reshape(sh), "deep": deep.reshape(sh), "mount": mount.reshape(sh),
            "major": major.reshape(sh), "realm": realm, "heart": heart}


HEX_FILL = {K_GRASS: (126, 148, 80), K_FOREST: (64, 98, 52), K_JUNGLE: (44, 104, 58), K_MARSH: (74, 104, 96),
            K_DESERT: (212, 184, 124), K_MESA: (182, 112, 76), K_SNOW: (232, 234, 236), K_TUNDRA: (176, 186, 172),
            K_ASH: (78, 64, 60), K_ROCK: (140, 132, 120)}
PRIORITY = {"heartland": 0, "fallen_city": 1, "hellgate": 2, "dragon lair": 3, "hold": 4, "kobold warren": 5,
            "goblin cave": 5, "deep hall": 6, "delving": 7}


def hex_map(w, st, px, crop=None, title=None, detail=False):
    """The strategy map: every hex region one land, with signs for what is in it."""
    x0, y0, size = crop if crop else (0, 0, W.WORLD)
    sc = px / size
    S = 2
    img = Image.new("RGB", (px * S, px * S), (24, 44, 68))
    d = ImageDraw.Draw(img)
    T = sc * S
    rng = np.random.default_rng(5)
    hw = W.HEX_W * T
    inside = []
    for row in range(W.HROWS):
        for col in range(W.HCOLS):
            cx, cy = W.hex_center(col, row)
            if not (x0 - W.HEX < cx < x0 + size + W.HEX and y0 - W.HEX < cy < y0 + size + W.HEX):
                continue
            inside.append((col, row))
            corners = [((x - x0 * sc) * S, (y - y0 * sc) * S) for x, y in hex_corners(col, row, sc)]
            wat, mt = st["water"][row, col], st["mount"][row, col]
            if wat > 0.55:
                fill = (30, 56, 84) if st["deep"][row, col] > 0.4 else (52, 92, 118)
            elif mt > 0.3:
                fill = (150, 142, 130) if mt < 0.6 else (176, 170, 160)
            else:
                fill = HEX_FILL.get(int(st["major"][row, col]), (126, 148, 80))
            jit = 0.94 + 0.12 * rand01(np.array(col), np.array(row), 3)
            fill = tuple(int(min(255, c * jit)) for c in fill)
            d.polygon(corners, fill=fill, outline=(40, 40, 40) if wat <= 0.55 else (40, 64, 90))
            X, Y = (cx - x0) * T, (cy - y0) * T
            r = hw * 0.32
            if wat > 0.55:
                continue
            k = int(st["major"][row, col])
            if mt > 0.3:   # peaks
                for dx in (-0.55, 0.0, 0.55):
                    hgt = r * (1.1 if dx == 0 else 0.8)
                    bx = X + dx * r
                    d.polygon([(bx - r * 0.5, Y + r * 0.45), (bx, Y + r * 0.45 - hgt), (bx + r * 0.5, Y + r * 0.45)],
                              fill=(98, 90, 82), outline=(60, 54, 48))
                    d.polygon([(bx - r * 0.17, Y + r * 0.45 - hgt * 0.66), (bx, Y + r * 0.45 - hgt),
                               (bx + r * 0.17, Y + r * 0.45 - hgt * 0.66)], fill=(240, 240, 244))
            elif k in (K_FOREST, K_JUNGLE, K_TUNDRA):
                tc = {K_FOREST: (34, 66, 30), K_JUNGLE: (24, 76, 38), K_TUNDRA: (52, 82, 64)}[k]
                for dx, dy in ((-0.5, 0.2), (0.0, -0.25), (0.5, 0.2), (0.0, 0.55) if k == K_JUNGLE else (9, 9)):
                    if dx == 9:
                        continue
                    tx, ty = X + dx * r, Y + dy * r
                    d.polygon([(tx - r * 0.28, ty + r * 0.3), (tx, ty - r * 0.42), (tx + r * 0.28, ty + r * 0.3)],
                              fill=tc)
            elif k in (K_DESERT, K_MESA):
                for dy in (-0.25, 0.25):
                    d.arc([X - r * 0.6, Y + dy * r - r * 0.2, X + r * 0.6, Y + dy * r + r * 0.3], 200, 340,
                          fill=(150, 110, 60), width=max(1, int(T * 4)))
            elif k == K_MARSH:
                for dy in (-0.2, 0.2):
                    d.line([(X - r * 0.5, Y + dy * r), (X + r * 0.5, Y + dy * r)], fill=(60, 96, 104),
                           width=max(1, int(T * 5)))
            elif k == K_ASH:
                d.ellipse([X - r * 0.2, Y - r * 0.2, X + r * 0.2, Y + r * 0.2], fill=(236, 110, 30))
    # rivers and roads as they run
    for rv in w.rivers:
        p = (rv["pts"][:, :2] - (x0, y0)) * T
        if p[:, 0].max() < 0 or p[:, 1].max() < 0 or p[:, 0].min() > px * S or p[:, 1].min() > px * S:
            continue
        wd = max(S, int(T * 12 * (1 if not detail else 1.6)))
        d.line([tuple(q) for q in p], fill=(60, 110, 150), width=wd, joint="curve")
    for rd in w.roads:
        if rd["kind"] != "main" and not detail:
            continue
        p = (rd["pts"][:, :2] - (x0, y0)) * T
        d.line([tuple(q) for q in p], fill=(110, 72, 40), width=max(S, int(T * (10 if rd["kind"] == "main" else 6))))
    # realm borders along hex edges, and the old heartland's hexes in gold
    for col, row in inside:
        for di, nc, nr in hex_neighbours(col, row):
            if not (0 <= nc < W.HCOLS and 0 <= nr < W.HROWS):
                continue
            a, b = st["realm"][row, col], st["realm"][nr, nc]
            if a >= 0 and b >= 0 and a != b and st["water"][row, col] <= 0.55 and st["water"][nr, nc] <= 0.55:
                c = hex_corners(col, row, sc)
                p1 = ((c[di][0] - x0 * sc) * S, (c[di][1] - y0 * sc) * S)
                p2 = ((c[(di + 1) % 6][0] - x0 * sc) * S, (c[(di + 1) % 6][1] - y0 * sc) * S)
                d.line([p1, p2], fill=(150, 36, 28), width=max(2, int(T * 18)))
    for isl in w.islands:
        X, Y = (isl["x"] - x0) * T, (isl["y"] - y0) * T
        a_, b_ = isl["a"] * T, isl["b"] * T
        sh = max(3, int(T * 30))
        d.ellipse([X - a_ + sh, Y - b_ + sh, X + a_ + sh, Y + b_ + sh], fill=(20, 34, 50))
        d.ellipse([X - a_, Y - b_, X + a_, Y + b_], fill=(214, 210, 200), outline=(250, 250, 255), width=max(2, int(T * 8)))
        d.ellipse([X - a_ * 0.82, Y - b_ * 0.78, X + a_ * 0.82, Y + b_ * 0.78], fill=(110, 140, 76))
        if isl["great"]:
            fx, fy = (np.array(isl["falls"]) - (x0, y0)) * T
            d.ellipse([X - a_ * 0.3 - a_ * 0.25 * np.cos(isl["ang"]), Y - b_ * 0.3 - b_ * 0.25 * np.sin(isl["ang"]),
                       X + a_ * 0.3 - a_ * 0.25 * np.cos(isl["ang"]), Y + b_ * 0.3 - b_ * 0.25 * np.sin(isl["ang"])],
                      fill=(58, 98, 122))
            d.line([(X, Y), (fx, fy)], fill=(64, 108, 138), width=max(2, int(T * 14)))
            r_ = max(6, int(T * 26))
            d.ellipse([fx - r_, fy - r_, fx + r_, fy + r_], fill=(236, 244, 248))
    for col, row in inside:
        if st["heart"][row, col]:
            c = [((x - x0 * sc) * S, (y - y0 * sc) * S) for x, y in hex_corners(col, row, sc, 0.92)]
            d.polygon(c, outline=(236, 196, 70), width=max(2, int(T * 16)))
    # what is in each hex: the most important place, or all of them on the close map
    best = {}
    for p in w.places:
        key = p.get("type") if p.get("type") in PRIORITY else p["kind"]
        if key not in PRIORITY:
            if not detail:
                continue
            key = p.get("type", p["kind"])
        pr = PRIORITY.get(key, 9)
        hk = tuple(p["hex"])
        if detail:
            best.setdefault(hk, []).append((pr, key, p))
        elif hk not in best or pr < best[hk][0][0]:
            best[hk] = [(pr, key, p)]
    f = font(max(13, int(px / (55 if not detail else 75))))
    labels = []
    for hk, items in best.items():
        for pr, key, p in items:
            X, Y = (p["x"] - x0) * T, (p["y"] - y0) * T
            if not (0 <= X < px * S and 0 <= Y < px * S):
                continue
            r = hw * (0.16 if detail else 0.2)
            place_sign(d, key, X, Y, r)
            if key == "heartland":
                labels.append((X / S, Y / S - r / S - 10, p["name"]))
    img = img.resize((px, px), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    for x, y, name in labels:
        if y > px / 18:   # keep the title clear
            text(d, (x, y), name, f)
    for p in w.places:
        if p["kind"] == "sky island" and p["great"]:
            x, y = (p["x"] - x0) * sc, (p["y"] - y0 - w.islands[0]["b"]) * sc - px / 60
            if y < px / 12:   # near the top: under the isle, clear of the title
                y = (p["y"] - y0 + w.islands[0]["b"]) * sc + px / 60
            if 0 < x < px and 0 < y < px:
                text(d, (x, y), p["name"], f, fill=(40, 70, 110))
    fl = font(max(16, px // (60 if not detail else 40)))
    placed = []
    for ln in sorted(w.lands, key=lambda l: -l["regions"]):
        x, y = (ln["cx"] - x0) * sc, (ln["cy"] - y0) * sc + px / 50
        if 0 < x < px and 0 < y < px and ln["name"] != "The Heartland" and ln["regions"] >= 20 and \
                all(abs(x - a) > px / 6 or abs(y - b) > px / 30 for a, b in placed):
            placed.append((x, y))
            text(d, (x, y), " ".join(ln["name"].upper()), fl, fill=(120, 40, 30))
    if title:
        text(d, (px / 2, px / 34), title, font(px // 42))
    return img


def place_sign(d, key, X, Y, r):
    if key in ("fallen_city", "heartland"):
        fc = (214, 170, 40) if key == "heartland" else (110, 100, 94)
        d.rectangle([X - r, Y - r * 0.6, X + r, Y + r * 0.7], fill=fc, outline=(30, 26, 22), width=2)
        for i in range(-2, 3):   # battlements, broken on a fallen city
            if key == "fallen_city" and i in (-1, 2):
                continue
            d.rectangle([X + i * r * 0.4 - r * 0.15, Y - r, X + i * r * 0.4 + r * 0.15, Y - r * 0.6], fill=fc,
                        outline=(30, 26, 22))
        d.rectangle([X - r * 0.22, Y + r * 0.1, X + r * 0.22, Y + r * 0.7], fill=(30, 26, 22))
    elif key == "hold":
        d.rectangle([X - r * 0.45, Y - r * 0.8, X + r * 0.45, Y + r * 0.6], fill=(120, 110, 100), outline=(30, 26, 22),
                    width=2)
    elif key in ("hellgate", "dragon lair", "kobold warren", "goblin cave", "deep hall", "crypt", "barrow", "tomb",
                 "cave", "ice cave", "mushroom cavern"):
        fc = {"hellgate": (250, 120, 20), "dragon lair": (210, 40, 30), "kobold warren": (40, 120, 200),
              "goblin cave": (40, 120, 200), "deep hall": (120, 60, 160)}.get(key, (20, 18, 18))
        d.polygon([(X, Y - r * 0.8), (X + r * 0.8, Y + r * 0.6), (X - r * 0.8, Y + r * 0.6)], fill=fc,
                  outline=(250, 236, 200))
    elif key == "delving":
        d.polygon([(X, Y - r * 0.6), (X + r * 0.6, Y), (X, Y + r * 0.6), (X - r * 0.6, Y)], fill=(120, 80, 170),
                  outline=(250, 236, 200))
    elif key == "lair":
        d.ellipse([X - r * 0.35, Y - r * 0.35, X + r * 0.35, Y + r * 0.35], fill=(150, 120, 40), outline=(40, 30, 20))
    elif key == "ruin":
        d.line([(X - r * 0.4, Y - r * 0.4), (X + r * 0.4, Y + r * 0.4)], fill=(60, 56, 50), width=3)
        d.line([(X - r * 0.4, Y + r * 0.4), (X + r * 0.4, Y - r * 0.4)], fill=(60, 56, 50), width=3)


def hex_border_mask(x0, y0, n, step=1):
    """Tiles (every `step` tiles) on the edge between two hex regions."""
    c = x0 + (np.arange(n) + 0.5) * step
    r = y0 + (np.arange(n) + 0.5) * step
    wx, wy = np.meshgrid(c, r)
    hc, hr = W.hex_of(wx, wy)
    hid = hr * 1000 + hc
    return (hid != np.roll(hid, 1, 0)) | (hid != np.roll(hid, 1, 1))


def paint_border(img, mask, scale, colour=(255, 240, 160), dash=True):
    a = np.array(img)
    ys, xs = np.nonzero(mask)
    for y, x in zip(ys, xs):
        if dash and ((x + y) // 3) % 2:
            continue
        a[y * scale:(y + 1) * scale, x * scale:(x + 1) * scale] = colour
    return Image.fromarray(a)


def label_places(d, w, x0, y0, size, scale):
    f = font(max(14, scale * 6))
    for p in w.places:
        px_, py_ = (p["x"] - x0) * scale, (p["y"] - y0) * scale
        if 0 <= px_ < size * scale and 0 <= py_ < size * scale and "name" in p:
            label = p["name"]
            if p["kind"] == "delving":
                label += "  (%s)" % p["ore"]
            off = 48 if p["kind"] == "fallen_city" else 30
            text(d, (px_, py_ - off * scale / 3), label, f)


def hex_picture(w, col, row, title, scale=3, r=None):
    """One hex region's square tiles; tiles that belong to the neighbours are faded."""
    r = r or w.hex_region(col, row, layers=False)
    img = tiles_image(r[1], r["height"], scale)
    a = np.array(img).astype(float)
    out = ~np.repeat(np.repeat(r["inside"], scale, 0), scale, 1)
    a[out] = a[out] * 0.4 + PAPER * 0.6
    img = Image.fromarray(a.astype(np.uint8))
    x0, y0 = r["origin"]
    d = ImageDraw.Draw(img)
    c = [((x - x0) * scale, (y - y0) * scale) for x, y in hex_corners(col, row)]
    d.polygon(c, outline=(150, 36, 28), width=3)
    label_places(d, w, x0, y0, r[1].shape[0], scale)
    if title:
        text(d, (img.size[0] / 2, 26), title, font(max(18, scale * 7)))
    return img


def area_picture(w, x0, y0, size, title, scale=2):
    """A square of tiles across several hex regions, the hex edges dashed."""
    r = w.window(int(x0), int(y0), size, layers=False)
    img = tiles_image(r[1], r["height"], scale)
    img = paint_border(img, hex_border_mask(int(x0), int(y0), size), scale)
    d = ImageDraw.Draw(img)
    label_places(d, w, x0, y0, size, scale)
    if title:
        text(d, (img.size[0] / 2, 26), title, font(max(18, scale * 9)))
    return img


def layers_picture(w, col, row, scale=2):
    r = w.hex_region(col, row, layers=True)
    names = {1: "Ground", 2: "Caves", 4: "Depths", 3: "Sky"}
    x0, y0 = r["origin"]
    out_m = ~np.repeat(np.repeat(r["inside"], scale, 0), scale, 1)
    pics = []
    for z in [3, 1, 2, 4]:
        im = tiles_image(r[z], r["height"], scale, z)
        a = np.array(im).astype(float)
        a[out_m] = a[out_m] * 0.35 + PAPER * 0.65
        im = Image.fromarray(a.astype(np.uint8))
        d = ImageDraw.Draw(im)
        d.polygon([((x - x0) * scale, (y - y0) * scale) for x, y in hex_corners(col, row)], outline=(150, 36, 28),
                  width=3)
        for mx, my, kind, *_ in r["mouths"]:
            if r["inside"][min(my, r["inside"].shape[0] - 1), min(mx, r["inside"].shape[1] - 1)]:
                d.ellipse([mx * scale - 14, my * scale - 14, mx * scale + 14, my * scale + 14],
                          outline=(250, 230, 90), width=3)
        for cx, cy in r["chasms"]:
            if r["inside"][cy, cx]:
                d.ellipse([cx * scale - 16, cy * scale - 16, cx * scale + 16, cy * scale + 16],
                          outline=(240, 90, 220), width=3)
        text(d, (im.size[0] / 2, 22), names[z], font(26))
        pics.append(im)
    gap = 14
    W2 = pics[0].size[0] * 2 + gap
    out = Image.new("RGB", (W2, W2 + 104), (236, 226, 200))
    for i, im in enumerate(pics):
        out.paste(im, ((i % 2) * (im.size[0] + gap), 70 + (i // 2) * (im.size[1] + gap)))
    d = ImageDraw.Draw(out)
    text(d, (W2 / 2, 22), "One hex region, four layers, tile for tile", font(28))
    text(d, (W2 / 2, 52), "yellow rings: cave mouths (ground) = stairs up (caves);  pink rings: chasms (caves) = "
                          "landings (depths)", font(16))
    text(d, (W2 / 2, out.size[1] - 16), "caves: dark = solid rock, light = tunnels and halls;  depths: brown = open "
                                         "hell floor, grey = rock, orange = lava, olive = dead grass", font(16))
    return out, r


def find_hexes(w, st):
    picks = {}
    heart = st["heart"]
    best = None
    for p in w.places:
        c, rr = p["hex"]
        if p["kind"] == "fallen_city" and p.get("port") and 0.2 < st["water"][rr, c] < 0.55:
            s = w.rivmask[max(0, int(p["y"] // 32) - 5):int(p["y"] // 32) + 5,
                          max(0, int(p["x"] // 32) - 5):int(p["x"] // 32) + 5].sum()
            if best is None or s > best[0]:
                best = (s, c, rr)
    picks["coast"] = best[1:] if best else (10, 10)
    best = None
    chas = {}
    for cx, cy in w.chasms:
        c, rr = W.hex_of(cx, cy)
        chas[(int(c), int(rr))] = chas.get((int(c), int(rr)), 0) + 1
    byhex = {}
    for p in w.places:
        byhex.setdefault(tuple(p["hex"]), []).append(p)
    for (c, rr), here in byhex.items():
        if heart[rr, c] or not 0.2 < st["mount"][rr, c] < 0.6 or st["water"][rr, c] > 0.05:
            continue
        m = sum(p["kind"] == "delving" for p in here)
        dg = sum(p["kind"] == "dungeon" for p in here)
        ch = chas.get((c, rr), 0)
        s = min(m, 2) + min(dg, 2) + ch * 1.5
        if m and dg and ch and (best is None or s > best[0]):
            best = (s, c, rr)
    picks["mountain"] = best[1:] if best else (20, 20)
    best = None
    for rr in range(1, W.HROWS - 1):
        for c in range(1, W.HCOLS - 1):
            if heart[rr, c] or st["water"][rr, c] > 0.15:
                continue
            cx, cy = W.hex_center(c, rr)
            blk = w.racc[int(cy // 32) - 9:int(cy // 32) + 9, int(cx // 32) - 9:int(cx // 32) + 9] * \
                w.rivmask[int(cy // 32) - 9:int(cy // 32) + 9, int(cx // 32) - 9:int(cx // 32) + 9]
            s = np.log1p(blk.max()) + (blk > 0).sum() * 0.05 + len(byhex.get((c, rr), [])) * 0.1
            if best is None or s > best[0]:
                best = (s, c, rr)
    picks["seams"] = best[1:]
    return picks


# ------------------------------------------------------------------------- caves, depths, sky, dungeons
UNDER = {K_CAVEFLOOR: (40, 36, 34), K_TUNNEL: (150, 132, 108), K_WATER: (60, 104, 140), K_DEEP: (30, 50, 84),
         K_LAVA: (236, 108, 32), K_MUSHROOM: (150, 96, 168), K_ASH: (96, 64, 56), K_ROCK: (44, 34, 32),
         K_DEADGRASS: (120, 108, 62), K_WALL: (196, 180, 150), K_CHASM: (8, 8, 10), K_STAIRSUP: (250, 220, 120)}


def layer_image(w, z, px=2048, title=None):
    """The whole world's caves (z 2) or depths (z 4), with the ground's coasts drawn faint to find your way."""
    tpp = W.WORLD / px
    c = (np.arange(px) + 0.5) * tpp
    wx, wy = np.meshgrid(c, c)
    h = w.height(wx, wy, 2 * tpp)
    k = w.classify(h, w.sample(w.temp, wx, wy), w.sample(w.moist, wx, wy), w.ash(wx, wy))
    if z == 2:
        L = w.caves_field(wx, wy, k, k, h, min_wl=2 * tpp, widen=3.0)
    else:
        L = w.depths_field(wx, wy, min_wl=2 * tpp, widen=3.0)
    if w.hl:   # today's own caves and depths in the middle
        sub = (wx >= W.HX0) & (wx < W.HX0 + W.HSIZE) & (wy >= W.HY0) & (wy < W.HY0 + W.HSIZE)
        L[sub] = w.hk[z - 1][(wy[sub] - W.HY0).astype(int), (wx[sub] - W.HX0).astype(int)]
    col = np.zeros((px, px, 3))
    for kk, cc in UNDER.items():
        col[L == kk] = cc
    col[~np.isin(L, list(UNDER))] = PAL[L[~np.isin(L, list(UNDER))]] * 0.7
    col *= (0.92 + 0.16 * rand01(np.arange(px)[None, :], np.arange(px)[:, None], 21 + z))[..., None]
    sea = h < 0
    if z == 2:
        col[sea] = col[sea] * 0.35 + np.array([24, 34, 56]) * 0.65
    coast = (sea ^ np.roll(sea, 1, 0)) | (sea ^ np.roll(sea, 1, 1))
    col[coast] = col[coast] * 0.4 + np.array([170, 200, 220]) * 0.6
    img = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    f = font(max(13, px // 100))
    labels = []
    for p in w.places:
        X, Y = p["x"] / tpp, p["y"] / tpp
        kd, t = p["kind"], p.get("type")
        if z == 2:
            if kd == "underhall":
                r = p["r"] / tpp * 2.2
                d.ellipse([X - r, Y - r, X + r, Y + r], outline=(236, 196, 70), width=3)
            elif kd in ("dungeon", "delving"):
                fc = {"kobold warren": (60, 140, 220), "goblin cave": (60, 140, 220), "deep hall": (170, 90, 220),
                      "hellgate": (250, 120, 20), "dragon lair": (220, 50, 40)}.get(t, (250, 220, 120))
                d.rectangle([X - 2, Y - 2, X + 2, Y + 2], fill=fc)
        else:
            if kd == "demon keep":
                place_sign(d, "fallen_city", X, Y, 9)
            elif kd == "the wound":
                labels.append((X, Y - 50, "THE WOUND"))
            elif t == "hellgate":
                d.polygon([(X, Y - 7), (X + 7, Y + 5), (X - 7, Y + 5)], fill=(250, 120, 20), outline=(20, 10, 10))
    for cx, cy in w.chasms:
        X, Y = cx / tpp, cy / tpp
        d.point((X, Y), fill=(240, 90, 220))
    put = []
    for x, y, name in labels:
        if all(abs(x - a) > 140 or abs(y - b) > 22 for a, b in put):
            put.append((x, y))
            text(d, (x, y), name, f, fill=(250, 236, 200), halo=(30, 24, 20))
    if title:
        text(d, (px / 2, px / 34), title, font(px // 42), fill=(250, 236, 200), halo=(30, 24, 20))
    return img


def sky_isle_picture(w, scale=2):
    """The great sky isle: its own map at the sky height, the sea far below seen faint through the air."""
    isl = w.islands[0]
    size = int(2 * isl["a"] + 140)
    x0, y0 = int(isl["x"] - size / 2), int(isl["y"] - size / 2)
    r = w.window(x0, y0, size, layers=True)
    below = np.array(tiles_image(r[1], r["height"], scale)).astype(float)
    below = below * 0.45 + np.array([196, 222, 240]) * 0.55          # far below, through the air
    sky = r[3]
    on = ~np.isin(sky, [K_SKY, K_PEAK])
    top = np.array(tiles_image(np.where(on, sky, K_GRASS).astype(np.uint8), np.zeros(sky.shape) + 0.1, scale, 3))
    m = np.repeat(np.repeat(on, scale, 0), scale, 1)
    sh = np.roll(np.roll(m, 14, 0), 14, 1) & ~m
    below[sh] *= 0.6
    below[m] = top[m]
    img = Image.fromarray(below.astype(np.uint8))
    d = ImageDraw.Draw(img)
    fx, fy = isl["falls"]
    text(d, ((fx - x0) * scale, (fy - y0) * scale + 70), "The Great Falls: down to the sea", font(20), fill=(40, 70, 110))
    p = w.places[isl["place"]]
    text(d, (img.size[0] / 2, 26), p["name"] + "  (sky level, %d x %d tiles)" % (2 * isl["a"], 2 * isl["b"]), font(26))
    text(d, (img.size[0] / 2, img.size[1] - 22), "grass, woods, the lake and its river, a ruined sky temple, skystone "
                                                 "(gold) in the white rim", font(17))
    return img


def falls_side_view(w, width=1600, height=760):
    """A side view along the falls: the sea, the shore, the isle at the sky height, the water falling."""
    isl = w.islands[0]
    fx, fy = isl["falls"]
    ang = isl["ang"]
    img = Image.new("RGB", (width, height), (200, 224, 240))
    d = ImageDraw.Draw(img)
    for yy in range(height):   # sky fading to haze
        t = yy / height
        d.line([(0, yy), (width, yy)], fill=(int(150 + 70 * t), int(190 + 40 * t), int(232 + 10 * t)))
    span = 2600.0
    xs = np.linspace(-isl["a"] * 2.2, span - isl["a"] * 2.2, width)
    wx = isl["x"] + np.cos(ang) * xs
    wy = isl["y"] + np.sin(ang) * xs
    hh = w.height(wx, wy, 8)
    sea_y = height * 0.82
    unit = height * 0.62 / 1.0          # one unit of height
    sky_y = sea_y - height * 0.6       # the sky height
    ground = [(i, sea_y - max(hh[i], 0) * unit * 0.5) for i in range(width)]
    d.rectangle([0, sea_y, width, height], fill=(44, 86, 118))
    d.polygon(ground + [(width, height), (0, height)], fill=(96, 120, 70))
    d.rectangle([0, sea_y, width, height], fill=None)
    for i in range(width):
        if hh[i] < 0:
            d.line([(i, sea_y), (i, height)], fill=(44, 86, 118))
    # the isle: a slab with a hanging underside of rock
    xa = int(np.argmin(np.abs(xs + isl["a"])))
    xb = int(np.argmin(np.abs(xs - isl["a"])))
    under = [(x, sky_y + 18 + (x - xa) * (xb - x) / ((xb - xa) / 2) ** 2 * 120) for x in range(xa, xb + 1, 4)]
    d.polygon([(xa, sky_y + 10)] + under + [(xb, sky_y + 10)], fill=(150, 140, 128), outline=(90, 84, 76))
    d.rectangle([xa, sky_y - 4, xb, sky_y + 12], fill=(112, 140, 76))
    for t in range(xa + 20, xb - 20, 26):   # trees on top
        d.polygon([(t - 8, sky_y - 2), (t, sky_y - 26), (t + 8, sky_y - 2)], fill=(52, 80, 42))
    lx = int((xa + xb) / 2 - (xb - xa) * 0.12)
    d.rectangle([lx - 40, sky_y - 6, lx + 40, sky_y + 2], fill=(58, 98, 122))
    # the falls
    for k in range(20):
        jx = xb + 4 + k * 1.3
        d.line([(jx, sky_y), (jx + k * 0.6, sea_y)], fill=(230 - k * 2, 240 - k, 248), width=3)
    for k in range(60):
        rx_ = xb + 16 + np.sin(k * 1.7) * 40
        ry_ = sea_y - abs(np.cos(k * 2.3)) * 50
        d.ellipse([rx_ - 14, ry_ - 8, rx_ + 14, ry_ + 8], fill=(240, 246, 250))
    f = font(22)
    text(d, (width / 2, 30), "The Great Falls, side view: from the sky isle to the sea", font(30))
    d.line([(0, sky_y), (width, sky_y)], fill=(255, 255, 255), width=1)
    text(d, (width - 150, sky_y - 18), "sky height (10 blocks)", f)
    text(d, ((xa + xb) / 2, sky_y + 90), w.places[isl["place"]]["name"], f)
    text(d, (xb + 120, (sky_y + sea_y) / 2), "the Great Falls", f, fill=(40, 70, 110))
    text(d, (max(90, xb - 160), sea_y + 40), "the sea", f, fill=(230, 240, 250), halo=(30, 50, 70))
    return img


MARK = {"entrance": (250, 220, 120), "stairs up": (250, 220, 120), "stairs down": (120, 220, 250),
        "boss": (220, 40, 30), "treasure": (240, 200, 40), "hoard": (240, 200, 40), "monsters": (230, 120, 40),
        "sarcophagus": (200, 200, 200), "eggs": (250, 250, 220), "gate down to the depths": (250, 120, 20)}


def dungeon_image(L, f_i, cell=400):
    grid, marks = L["floors"][f_i]
    n = grid.shape[0]
    sc = max(2, cell // n)
    col = np.zeros((n, n, 3))
    for kk, cc in UNDER.items():
        col[grid == kk] = cc
    other = ~np.isin(grid, list(UNDER))
    col[other] = PAL[grid[other]]
    col *= (0.92 + 0.16 * rand01(np.arange(n)[None, :], np.arange(n)[:, None], 31))[..., None]
    img = Image.fromarray(np.repeat(np.repeat(col, sc, 0), sc, 1).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for y, x, what in marks:
        c = MARK.get(what, (255, 255, 255))
        r = sc * 1.6
        d.ellipse([(x + 0.5) * sc - r, (y + 0.5) * sc - r, (x + 0.5) * sc + r, (y + 0.5) * sc + r], fill=c,
                  outline=(20, 16, 14))
    return img


def dungeon_sheet(w):
    kinds = ["crypt", "tomb", "barrow", "cave", "ice cave", "mushroom cavern", "delving", "dragon lair",
             "kobold warren", "goblin cave", "hellgate", "deep hall"]
    picks = []
    for k in kinds:
        p = next((p for p in w.places if (p.get("type") == k) or (k == "delving" and p["kind"] == "delving")), None)
        if p:
            picks.append(p)
    cw, ch = 400, 470
    out = Image.new("RGB", (cw * 4 + 50, ch * 3 + 170), (236, 226, 200))
    d = ImageDraw.Draw(out)
    for i, p in enumerate(picks):
        L = w.dungeon(p)
        im = dungeon_image(L, 0, 384)
        x, y = 10 + (i % 4) * (cw + 10), 90 + (i // 4) * (ch + 10)
        out.paste(im.resize((384, 384), Image.NEAREST), (x + 8, y + 40))
        text(d, (x + cw / 2, y + 14), "%s  (%d floor%s)" % (p["name"].capitalize(), len(L["floors"]), "s" if len(L["floors"]) > 1 else ""),
             font(17))
        text(d, (x + cw / 2, y + 438), "%s: %s" % (L["kind"], L["foes"]), font(13))
        text(d, (x + cw / 2, y + 456), "boss: %s" % L["boss"], font(13))
    text(d, (out.size[0] / 2, 30), "A dungeon for every kind, first floor shown", font(30))
    text(d, (out.size[0] / 2, 64), "yellow: way in / stairs up   blue: stairs down   orange: monsters   red: boss   gold: "
                                   "treasure   white: tombs, eggs", font(16))
    return out


def dungeon_floors(w, kind):
    p = next(p for p in w.places if p.get("type") == kind or (kind == "delving" and p["kind"] == "delving"))
    L = w.dungeon(p)
    nf = len(L["floors"])
    out = Image.new("RGB", (nf * 520 + 20, 640), (236, 226, 200))
    d = ImageDraw.Draw(out)
    for f in range(nf):
        im = dungeon_image(L, f, 500).resize((500, 500), Image.NEAREST)
        out.paste(im, (10 + f * 520, 110))
        text(d, (10 + f * 520 + 250, 90), "floor %d%s" % (f + 1, "  (carved under its cave mouth in the world)"
                                                         if f == 0 else "  (instance)"), font(18))
    text(d, (out.size[0] / 2, 30), "A %s, every floor  (%s)" % (p["name"], L["foes"]), font(26))
    text(d, (out.size[0] / 2, 62), p.get("story", "")[:150], font(14))
    return out


def cached(seed, hl):
    """The world for a seed, kept in out/ while the pictures are tuned (made again if the code changed)."""
    import pickle
    src = max(os.path.getmtime(os.path.join(HERE, f)) for f in ("worldgen.py", "noise.py", "heartland.py", "lore.py"))
    path = os.path.join(OUT, "world_%d_%d.pkl" % (seed, hl))
    if os.path.exists(path) and os.path.getmtime(path) > src:
        with open(path, "rb") as f:
            w = pickle.load(f)
        w.log = print
        return w
    w = W.World(seed, hl)
    w.log = None
    with open(path, "wb") as f:
        pickle.dump(w, f)
    w.log = print
    return w


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1026
    only = sys.argv[2:]   # e.g. "hexmap" to remake only some pictures
    want = lambda k: not only or k in only
    od = OUT if seed == 1026 else os.path.join(OUT, "seed%d" % seed)   # other seeds keep their own folder
    os.makedirs(od, exist_ok=True)
    w = cached(seed, True)
    fresh = cached(seed, False)
    st = hex_stats(w)
    info = {"with_heartland": w.summary(), "fresh": fresh.summary(),
            "fingerprint": {"with_heartland": w.fingerprint(), "fresh": fresh.fingerprint()}}

    if want("world"):
        img = world_image(w, 2048, title="The World  (seed %d)" % seed)
        legend(img, w)
        img.save(os.path.join(od, "world_map.png"))
        a = world_image(w, 1024, labels=False, title="With today's map in the middle")
        b = world_image(fresh, 1024, labels=False, title="All new, nothing kept")
        both = Image.new("RGB", (2048 + 16, 1024), (236, 226, 200))
        both.paste(a, (0, 0))
        both.paste(b, (1024 + 16, 0))
        both.save(os.path.join(od, "world_both_ways.png"))
    if want("hexmap"):
        hex_map(w, st, 2048, title="The World in Hex Regions  (seed %d)" % seed).save(
            os.path.join(od, "world_hexes.png"))
        cx, cy = W.HX0 + 500, W.HY0 + 500
        hex_map(w, st, 1800, crop=(cx - 2600, cy - 2600, 5200), detail=True,
                title="Round the Old Heartland, hex by hex").save(os.path.join(od, "hexes_heartland.png"))

    picks = find_hexes(w, st)
    info["hexes_shown"] = {k: list(map(int, v)) for k, v in picks.items()}
    if want("close"):
        c, rr = picks["coast"]
        hex_picture(w, c, rr, "Hex %d,%d: a fallen port city on the coast" % (c, rr)).save(
            os.path.join(od, "hex_coast.png"))
        c, rr = picks["mountain"]
        hex_picture(w, c, rr, "Hex %d,%d: mountains, an old delving and caves" % (c, rr)).save(
            os.path.join(od, "hex_mountain.png"))
        lp, r = layers_picture(w, c, rr)
        lp.save(os.path.join(od, "hex_layers.png"))
        info["layers_hex"] = {"tiles_in_hex": int(r["inside"].sum()),
                              "sky_peaks_over_rock": int(((r[1] == K_ROCK) & (r[3] != K_PEAK)).sum()) == 0}
        c, rr = picks["seams"]
        cx, cy = W.hex_center(c, rr)
        area_picture(w, cx - 320, cy - 320, 640, "Hex regions round %d,%d: rivers and roads run across the edges"
                     % (c, rr)).save(os.path.join(od, "hexes_seams.png"))
        area_picture(w, W.HX0 - 420, W.HY0 + 220, 640, "Where today's map (right) meets the new land (left)").save(
            os.path.join(od, "heartland_edge.png"))
        sc_, sr_ = W.hex_of(W.SWAMP[0], W.SWAMP[1])
        hex_picture(w, int(sc_), int(sr_), "Hex %d,%d: the great swamp east of the heartland" % (sc_, sr_)).save(
            os.path.join(od, "hex_swamp.png"))
    if want("around"):
        ctx = Image.new("RGB", (12 * 128, 12 * 128))
        for j in range(12):
            for i in range(12):
                rr_ = w.region(26 + i, 26 + j, layers=False)
                ctx.paste(tiles_image(rr_[1], rr_["height"], 1).resize((128, 128), Image.LANCZOS), (i * 128, j * 128))
        ctx = paint_border(ctx, hex_border_mask(26 * 256, 26 * 256, 12 * 128, 2), 1, (255, 240, 160), dash=False)
        d = ImageDraw.Draw(ctx)
        a0, a1 = (W.HX0 - 26 * 256) / 2, (W.HX0 + W.HSIZE - 26 * 256) / 2
        d.rectangle([a0, a0, a1, a1], outline=(236, 196, 70), width=3)
        for p in w.places:
            x, y = (p["x"] - 26 * 256) / 2, (p["y"] - 26 * 256) / 2
            if 0 <= x < ctx.size[0] and 0 <= y < ctx.size[1] and p["kind"] in ("fallen_city", "sky island"):
                text(d, (x, y - 22), p["name"], font(18))
        text(d, (ctx.size[0] / 2, 26), "The old heartland and the hex regions around it, every tile drawn", font(26))
        ctx.save(os.path.join(od, "heartland_surroundings.png"))

    if want("under"):
        layer_image(w, 2, 2048, "The Caves  (seed %d)" % seed).save(os.path.join(od, "world_caves.png"))
        layer_image(w, 4, 2048, "The Depths  (seed %d)" % seed).save(os.path.join(od, "world_depths.png"))
    if want("sky") and w.islands:
        sky_isle_picture(w).save(os.path.join(od, "sky_isle.png"))
        falls_side_view(w).save(os.path.join(od, "falls_side.png"))
    if want("dungeons"):
        dungeon_sheet(w).save(os.path.join(od, "dungeons.png"))
        dungeon_floors(w, "tomb").save(os.path.join(od, "dungeon_tomb_floors.png"))
        dungeon_floors(w, "delving").save(os.path.join(od, "dungeon_delving_floors.png"))

    places = [{k: v for k, v in p.items() if k != "biome"} for p in w.places]
    with open(os.path.join(od, "world.json"), "w") as f:
        json.dump({"info": info, "places": places}, f, indent=1)
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
