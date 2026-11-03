#!/usr/bin/env python3
"""Enhanced originals at 64 px: the game's own 32 px sprites, made bigger and better
without redrawing their design.

    python3 standalone/remastered/art/enhance/remaster64.py      (writes art/out/enhanced-test.png)

1. Scale2x to 64 px (keeps the pixel-art look, smooths stair-step edges).
2. Form shading: the whole figure is lit from the screen's top-left, so the body
   reads as round, in a few flat bands per colour (no airbrushing).
3. Body types: every humanoid original shares one body; dwarves and goblins get
   their own proportions by deleting or doubling whole rows and columns that
   Scale2x made in pairs, so no pixel is resampled. The same edit is applied to
   every overlay (armour, beards, weapons), so equipment still fits.
4. Metal finish for armour: the flat grey of the originals becomes a lit metal
   ramp with a glint along the lit edges and darker seams.
"""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ART, "pipeline"))
from make_comparison import GAME, read_dmi  # noqa: E402

from enhance import scale2x  # noqa: E402

ICONS = os.path.join(GAME, "Icons")
CREATURE_ICONS = os.path.join(GAME, "Code", "Creatures", "Icons")
DIRS = ("S", "N", "E", "W")


def rgba(cell):
    a = np.asarray(cell.convert("RGBA")).copy()
    a[a[..., 3] < 128] = 0
    a[a[..., 3] > 0, 3] = 255
    return a


def up(cell):
    return scale2x(rgba(cell))


# ---------------------------------------------------------------------------
# shading
# ---------------------------------------------------------------------------

def box_blur(m, r):
    """Mean over a (2r+1)^2 box, edges padded with zeros."""
    p = np.pad(m.astype(np.float32), r)
    c = p.cumsum(0).cumsum(1)
    c = np.pad(c, ((1, 0), (1, 0)))
    n = 2 * r + 1
    return (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]) / (n * n)


def form_light(a, strength=0.22, bands=(0.82, 1.0, 1.14), mask=None):
    """Light the figure from the top-left: a soft 'normal' from the blurred silhouette,
    quantised to a few bands so pixels stay flat colours. Dark outline pixels are left."""
    al = a[..., 3] > 0 if mask is None else mask
    rgb = a[..., :3].astype(np.float32)
    lum = rgb.mean(-1)
    inner = al & (lum > 24)
    soft = box_blur(al, 4)
    gy, gx = np.gradient(soft)
    shade = -(gx * -0.7 + gy * -0.7) * 9.0     # facing the top-left light -> positive
    edge = box_blur(al, 1) < 0.999              # last ring inside the outline
    shade = np.clip(shade, -1, 1)
    q = np.where(shade > 0.25, bands[2], np.where(shade < -0.2, bands[0], bands[1]))
    out = rgb.copy()
    out[inner] = np.clip(rgb[inner] * q[inner][:, None], 0, 255)
    # a rim of shadow along the lower-right inside edge, a little light top-left
    pa = np.pad(~al, 1, constant_values=True)
    lr = inner & edge & (pa[2:, 1:-1] | pa[1:-1, 2:])
    out[lr] *= 0.86
    a = a.copy()
    a[..., :3] = out.astype(np.uint8)
    return a


IRON = [(30, 32, 38), (66, 70, 78), (104, 109, 118), (148, 154, 163), (206, 212, 220)]


def runs(mask):
    """u: position (0 left .. 1 right) of each pixel within its horizontal run of the mask."""
    h, w = mask.shape
    u = np.zeros(mask.shape, np.float32)
    for y in range(h):
        xs = np.flatnonzero(mask[y])
        if not len(xs):
            continue
        breaks = np.flatnonzero(np.diff(xs) > 1)
        for seg in np.split(xs, breaks + 1):
            n = len(seg)
            u[y, seg] = (np.arange(n) + 0.5) / n
    return u


def metal_finish(a, kind=None, ramp=IRON):
    """Flat grey armour -> lit metal. Each plate is shaded like a cylinder lit from the
    top-left (u across it), the top of a piece catches light and its bottom falls into
    shade; only the piece's outer lit edge gets a glint, the original's black inner
    lines become dark seams. kind adds a detail: helmet rim, shield rim and boss,
    breastplate ridge."""
    al = a[..., 3] > 0
    rgb = a[..., :3].astype(np.int32)
    lum = rgb.mean(-1)
    grey = al & (np.abs(rgb[..., 0] - rgb[..., 2]) < 12) & (lum > 30)
    dark = al & (lum <= 30)
    if not grey.any():
        return a
    h, w = al.shape
    u = runs(al)
    ys, xs = np.nonzero(al)
    top, bot = ys.min(), ys.max()
    v = np.clip((np.arange(h)[:, None] - top) / max(1, bot - top), 0, 1) * np.ones((1, w))
    level = np.full((h, w), 2)
    level[u < 0.34] = 3
    level[u > 0.72] = 1
    level[(v < 0.18) & (level < 3)] += 1
    level[(v > 0.88) & (level > 1)] -= 1
    outside = ~al
    up_out = np.zeros_like(al)
    up_out[1:] = outside[:-1]
    up_out[0] = True
    left_out = np.zeros_like(al)
    left_out[:, 1:] = outside[:, :-1]
    left_out[:, 0] = True
    glint = grey & (up_out | left_out) & (u < 0.6)
    level[glint] = 4
    # a seam's lower edge catches a little light: the pixel under a dark inner line
    below_dark = np.zeros_like(al)
    below_dark[1:] = dark[:-1]
    level[grey & below_dark & (level < 3)] = 3
    cy, cx = ys.mean(), xs.mean()
    if kind == "shield":   # rim ring and boss
        r = np.hypot(np.arange(h)[:, None] - cy, np.arange(w)[None, :] - cx)
        R = np.percentile(r[al], 98)
        rim = grey & (r > R - 3.2)
        level[rim] = np.where(u[rim] < 0.5, 4, 1)
        level[grey & (r > R - 4.5) & (r <= R - 3.2)] = 0
        boss = grey & (r < 3.6)
        level[boss] = np.where((np.arange(h)[:, None] - cy + np.arange(w)[None, :] - cx)[boss] < 0, 4, 1)
        level[grey & (r >= 3.6) & (r < 4.6)] = 0
    if kind == "helmet":   # dark rim band along the bottom edge of the dome, with rivets
        col_bot = np.full(w, -1)
        for x in range(w):
            yy = np.flatnonzero(grey[:, x])
            if len(yy):
                col_bot[x] = yy.max()
        for x in range(w):
            if col_bot[x] >= 0:
                y0 = col_bot[x]
                band = [y for y in range(y0 - 2, y0 + 1) if grey[y, x]]
                for y in band:
                    level[y, x] = 1
                if band and x % 4 == 1:
                    level[band[0], x] = 3
        top_mask = grey & (v < 0.45) & (u > 0.2) & (u < 0.42)
        level[top_mask] = 4
    if kind == "chest":    # a ridge down the middle of the breastplate
        mid = int(round(cx))
        for y in range(h):
            if grey[y, mid - 1] and grey[y, mid]:
                level[y, mid - 1] = 4
                level[y, mid] = 1
    out = a.copy()
    pal = np.array(ramp, np.uint8)
    out[grey, :3] = pal[np.clip(level, 0, 4)[grey]]
    out[dark, :3] = pal[0]
    return out


def strands(a):
    """Hair texture: every third column a shade darker, a dark rim along the bottom."""
    al = a[..., 3] > 0
    out = a.copy()
    cols = (np.arange(a.shape[1]) % 3 == 1)[None, :] & al
    out[cols, :3] = (out[cols, :3] * 0.8).astype(np.uint8)
    pa = np.pad(~al, 1, constant_values=True)
    bottom = al & pa[2:, 1:-1]
    out[bottom, :3] = (out[bottom, :3] * 0.7).astype(np.uint8)
    return out


def long_beard(a, extra=10):
    """Lengthen a beard overlay downwards into a point: each column of hair grows on,
    longest in the middle and tapering to the sides, with darker strands every other
    column and a lighter tip of lit hair on the left."""
    al = a[..., 3] > 0
    if not al.any():
        return a
    out = a.copy()
    xs = np.flatnonzero(al.any(0))
    x0, x1 = xs.min(), xs.max()
    cx = (x0 + x1) / 2.0
    half = max(1.0, (x1 - x0 + 1) / 2.0)
    for x in xs:
        yy = np.flatnonzero(al[:, x])
        yb = yy.max()
        t = abs(x + 0.5 - (cx + 0.5)) / half
        n = int(round(extra * max(0.0, 1 - t) ** 1.3))
        c = a[yy.min():yb + 1, x, :3][a[yy.min():yb + 1, x, 3] > 0].astype(np.float32).mean(0)
        strand = 0.8 if (x - x0) % 3 == 1 else 1.0
        lit = 1.12 if x < cx - half * 0.3 else 1.0
        for k in range(1, n + 1):
            y = yb + k
            if y >= a.shape[0]:
                break
            out[y, x, :3] = np.clip(c * strand * lit * (1 - 0.18 * k / max(n, 1)), 0, 255).astype(np.uint8)
            out[y, x, 3] = 255
    return out


# ---------------------------------------------------------------------------
# body types
# ---------------------------------------------------------------------------
# Rows and columns of the 64 px figure (S view of the shared humanoid body): head
# rows 10-27, neck 28-31, torso 32-51, legs 52-59, feet 60-63; centre between
# columns 31 and 32. Scale2x makes every source row and column a pair, so deleting
# one row of a pair (or doubling one) keeps every pixel crisp.

BODY_TYPES = {
    # rows to drop (one of each pair) or to double, through the legs and torso; columns
    # added (+) or removed (-) at the centre below the chin, and in the head
    "standard": dict(drop=[], body_cols=0, head_cols=0),
    "dwarf": dict(drop=[53, 55, 57, 59, 35, 41, 47, 29], body_cols=6, head_cols=2),
    "goblin": dict(drop=[53, 55, 57, 33, 37, 41, 45, 49, 29], body_cols=-4, head_cols=0),
    "orc": dict(dup=[45, 55], body_cols=4, head_cols=2),               # big and broad
    "demon": dict(dup=[41, 53, 57], body_cols=6, head_cols=2),         # bigger still
    "tall": dict(dup=[47, 55, 59], body_cols=-2, head_cols=0),         # elves, vampires: long-legged, lean
    "frog": dict(drop=[53, 55, 57], body_cols=4, head_cols=2),         # squat and wide
}


def row_list(kind):
    """The source row for each of the 64 output rows (-1: empty), feet kept on the ground."""
    t = BODY_TYPES[kind]
    drop, dup = set(t.get("drop", ())), set(t.get("dup", ()))
    rows = []
    for r in range(64):
        if r in drop:
            continue
        rows.append(r)
        if r in dup:
            rows.append(r)
    if len(rows) > 64:   # doubled rows push the top up into the empty margin
        rows = rows[len(rows) - 64:]
    return [-1] * (64 - len(rows)) + rows
CHIN = 28   # first row below the head


def reshape(a, kind, side=False, head=False):
    """Apply a body type to one 64 px cell (body or overlay). Feet stay on the ground.
    side: the E/W views are a body's depth, so only half the width change. head: the
    layer hangs from the head (a beard), so it keeps the head's width all the way down."""
    t = BODY_TYPES[kind]
    h, w = a.shape[:2]
    rows = row_list(kind)
    out = np.zeros_like(a)
    for y, src in enumerate(rows):
        if src < 0:
            continue
        line = a[src]
        n = t["head_cols"] if src < CHIN or head else t["body_cols"]
        if side:
            n = int(round(n / 2.0))
        if n > 0:   # double the centre columns
            k = n // 2
            line = np.concatenate([line[k:32], np.repeat(line[31:32], k, 0), np.repeat(line[32:33], n - k, 0), line[32:w - (n - k)]])
        elif n < 0:
            k = -n // 2
            line = np.concatenate([np.zeros((k, 4), a.dtype), line[:32 - k], line[32 + (-n - k):], np.zeros((-n - k, 4), a.dtype)])
        out[y] = line[:w]
    return out


# ---------------------------------------------------------------------------
# fitting overlays drawn for the human template to another race's sprite
# ---------------------------------------------------------------------------
# Every equipment overlay in the game is drawn for Human.dmi's body. Some race sheets
# move that body: Dwarf.dmi is the same figure with three or four torso rows taken
# out, so its head sits lower. row_map() finds, for each row of a race's frame, the
# template row it was drawn from (an edit-distance alignment of the rows), and
# register() moves an overlay's rows the same way, so it lands on that race's body.

def _sig(cell):
    a = np.asarray(cell.convert("RGBA"))
    al = a[..., 3] >= 128
    return al, al & (a[..., :3].astype(int).sum(-1) < 100)


def row_map(template, race, DEL=6.0, INS=6.0, CAP=5.0):
    """For each 32 px row of `race`, the row of `template` it matches (-1: none). A row
    drawn differently in the same place (ribs, hair, horns) costs at most CAP, less than
    taking a row out and putting one back, so only real shifts move rows."""
    ha, hd = _sig(template)
    ra, rd = _sig(race)
    n, m = ha.shape[0], ra.shape[0]
    D = np.full((n + 1, m + 1), 1e9)
    D[0, 0] = 0
    B = np.zeros((n + 1, m + 1), int)
    for i in range(n + 1):
        for j in range(m + 1):
            if i and j:
                c = D[i - 1, j - 1] + min(CAP, (ha[i - 1] != ra[j - 1]).sum() + 0.5 * (hd[i - 1] != rd[j - 1]).sum())
                if c < D[i, j]:
                    D[i, j], B[i, j] = c, 0
            if i and D[i - 1, j] + DEL < D[i, j]:
                D[i, j], B[i, j] = D[i - 1, j] + DEL, 1
            if j and D[i, j - 1] + INS < D[i, j]:
                D[i, j], B[i, j] = D[i, j - 1] + INS, 2
    src = [-1] * m
    i, j = n, m
    while i or j:
        b = B[i, j]
        if b == 0:
            src[j - 1] = i - 1
            i, j = i - 1, j - 1
        elif b == 1:
            i -= 1
        else:
            j -= 1
    return src


def register(layer64, src):
    """Move a 64 px overlay drawn for the template onto a race's rows (src from row_map)."""
    out = np.zeros_like(layer64)
    for j, i in enumerate(src):
        if i >= 0:
            out[2 * j:2 * j + 2] = layer64[2 * i:2 * i + 2]
    return out


def fit(layer64, kind, side, src, head=False):
    """A template overlay fitted to a race: its rows, then its body type."""
    return reshape(register(layer64, src) if src is not None else layer64, kind, side, head)


# ---------------------------------------------------------------------------
# outline
# ---------------------------------------------------------------------------

def outline(a, keep_existing=True):
    """Outer ring in the darkened touching colour (the originals' own outline stays)."""
    al = a[..., 3] > 0
    rgb = a[..., :3].astype(np.float32)
    acc = np.zeros_like(rgb)
    n = np.zeros(al.shape, np.float32)
    pa, pr = np.pad(al, 1), np.pad(rgb, ((1, 1), (1, 1), (0, 0)))
    h, w = al.shape
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sa = pa[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
        acc += pr[1 + dy:1 + dy + h, 1 + dx:1 + dx + w] * sa[..., None]
        n += sa
    ring = ~al & (n > 0)
    out = a.copy()
    out[ring, :3] = np.minimum(acc[ring] / n[ring][:, None] * 0.3, 40).astype(np.uint8)
    out[ring, 3] = 255
    return out


# ---------------------------------------------------------------------------
# the test sheet
# ---------------------------------------------------------------------------

KIND = {"Metal Helmet": "helmet", "Metal Buckler": "shield", "Metal ChestPlate": "chest"}


def comp(*layers):
    out = layers[0].copy()
    for l in layers[1:]:
        m = l[..., 3] > 0
        out[m] = l[m]
    return out


def cells(name, f, st, kind, beard, M, beards, kit):
    """For each facing: (original, original + iron, enhanced, enhanced + iron) RGBA arrays,
    originals at 32 px and enhanced at 64 px."""
    body = read_dmi(os.path.join(ICONS, f))[st]
    human = read_dmi(os.path.join(ICONS, "Human.dmi"))[""]
    out = []
    for di in range(4):
        side = di >= 2
        src = row_map(human[di], body[di])
        b32 = rgba(body[di])
        o_iron = comp(b32, *[rgba(M[k][di]) for k in kit])
        b64 = reshape(form_light(up(body[di])), kind, side)
        extra = []
        if beard:
            bc = beards[beard][di] if len(beards[beard]) > di else beards[beard][0]
            extra.append(fit(strands(long_beard(form_light(up(bc)), 9 if not side else 7)), kind, side, src, head=True))
        g = [fit(metal_finish(up(M[k][di]), KIND.get(k)), kind, side, src) for k in kit]
        # beard over the chestplate and under the helmet, as RebuildOverlays() stacks them
        e_iron = outline(comp(b64, g[0], g[1], *extra, *g[2:]))
        out.append((b32, o_iron, outline(comp(b64, *extra)), e_iron))
    return out


def main():
    from PIL import ImageFont
    M = read_dmi(os.path.join(ICONS, "MetalObjects.dmi"))
    beards = read_dmi(os.path.join(CREATURE_ICONS, "Beards.dmi"))
    grass = up(read_dmi(os.path.join(GAME, "Code", "Building", "Grounds.dmi"))["Grass"][0])
    kit = ["Metal Leggings", "Metal ChestPlate", "MLeftArm", "MRightArm", "Metal Helmet", "Metal Buckler", "Sword"]
    races = [("Human", "Human.dmi", "", "standard", None), ("Dwarf", "Dwarf.dmi", "", "dwarf", "Brown"),
             ("Goblin", "Goblins.dmi", "", "goblin", None)]
    data = [cells(*r, M, beards, kit) for r in races]
    font, big = ImageFont.load_default(size=15), ImageFont.load_default(size=20)
    Z, C, gap, lab = 2, 128, 4, 110          # close-ups: 64 px drawn at 2x
    group = 4 * (C + gap) + 24
    titles = ["original 32 px", "original + iron set", "enhanced 64 px", "enhanced 64 px + iron set"]
    W = lab + 4 * group
    H1 = 70 + len(races) * (C + 16)
    H2 = 60 + len(races) * (64 + 12)
    sheet = Image.new("RGBA", (W, H1 + H2 + 20), (26, 24, 20, 255))
    d = ImageDraw.Draw(sheet)
    d.text((12, 10), "Close up (2x): S  N  E  W", font=big, fill=(240, 228, 196))
    for i, t in enumerate(titles):
        d.text((lab + i * group, 42), t, font=font, fill=(232, 220, 190))
    for r, (race, rows) in enumerate(zip(races, data)):
        y = 70 + r * (C + 16)
        d.text((12, y + C // 2 - 8), race[0], font=big, fill=(240, 228, 196))
        for di, cs in enumerate(rows):
            for ci, im in enumerate(cs):
                x = lab + ci * group + di * (C + gap)
                sheet.paste((92, 118, 70, 255), (x, y, x + C, y + C))
                sheet.alpha_composite(Image.fromarray(im).resize((C, C), Image.NEAREST), (x, y))
    # game size: one tile = 64 screen px; the original drawn at 2x so it covers the same tile
    y0 = H1 + 10
    d.text((12, y0), "Game size (one tile = 64 px, on the game's grass): S  N  E  W", font=big, fill=(240, 228, 196))
    for i, t in enumerate(titles):
        d.text((lab + i * group, y0 + 30), t, font=font, fill=(232, 220, 190))
    tile = Image.fromarray(grass)
    for r, (race, rows) in enumerate(zip(races, data)):
        y = y0 + 56 + r * (64 + 12)
        d.text((12, y + 24), race[0], font=font, fill=(240, 228, 196))
        for di, cs in enumerate(rows):
            for ci, im in enumerate(cs):
                x = lab + ci * group + di * (64 + 6)
                sheet.paste(tile, (x, y))
                img = Image.fromarray(im)
                if img.width == 32:
                    img = img.resize((64, 64), Image.NEAREST)
                sheet.alpha_composite(img, (x, y))
    out = os.path.join(ART, "out", "enhanced-test.png")
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
