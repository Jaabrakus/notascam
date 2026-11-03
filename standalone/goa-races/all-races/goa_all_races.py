#!/usr/bin/env python3
"""Every Dungeon Master race in the GOA style, consolidated with the six GOA race drafts.

    python3 standalone/goa-races/all-races/goa_all_races.py

The six GOA drafts (../goa-races-lotr-v1.png: Human, Dwarf, Night Elf, Orc, Goblin, Kobold) are cut out
unchanged. Every other race keeps ITS OWN look and takes only the GOA style:
  * a GOA body sized to the race's own build (Demon bigger, Vampire leaner and taller, Gargoyle tall and
    stocky, FrogMan squat), its skin recoloured by brightness so the GOA shading stays;
  * its own silhouette features taken from its own current sprite (game/Icons/Remastered/Races64, read
    only), redrawn in the GOA style (goa_restyle.py): the Demon's horns, the Vampire's and Gargoyle's bat
    ears, the FrogMan's head, the Zombie's flayed pattern, the flyers' wings; the Skeleton is its own
    sprite restyled whole;
  * its own eye colour.

Writes into this folder:
  sprites/<Race>-<dir>.png   every race and facing at the drafts' size (transparent)
  goa-races-all-v1.png       the consolidated sheet: every race, south / north / east / west
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import goa_restyle as G

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(os.path.dirname(HERE), 'goa-races-lotr-v1.png')
DIRS = ['south', 'north', 'east', 'west']
P = 6                          # screen pixels per art pixel, as in the drafts
OUTLINE = np.array([12, 10, 12], np.float32)

# The six drafts: (race, top, bottom) row bands of the draft sheet, and its column bands.
ROWS = [('Human', 60, 310), ('Dwarf', 320, 520), ('Night Elf', 525, 790),
        ('Orc', 795, 1040), ('Goblin', 1045, 1255), ('Kobold', 1260, 1480)]
COLS = [(60, 300), (300, 530), (530, 740), (740, 960)]


# ---------------------------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------------------------

def cut_drafts():
    a = np.asarray(Image.open(DRAFT).convert('RGBA')).astype(np.float32)
    out = {}
    for race, y0, y1 in ROWS:
        for d, (x0, x1) in zip(DIRS, COLS):
            sub = a[y0:y1, x0:x1].copy()
            m = sub[..., 3] >= 128
            ys, xs = np.where(m)
            sub = sub[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            sub[..., 3] = np.where(sub[..., 3] >= 128, 255, 0)
            sub[sub[..., 3] == 0, :3] = 0
            out[(race, d)] = sub
    return out


def hsv(rgb):
    r, g, b = rgb[..., 0] / 255, rgb[..., 1] / 255, rgb[..., 2] / 255
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    return np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0), mx


def lum(rgb):
    return rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11


def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def ramp(values, stops):
    ts = [t for t, _ in stops]
    cs = np.stack([hexc(c) for _, c in stops])
    out = np.zeros(values.shape + (3,), np.float32)
    for k in range(3):
        out[..., k] = np.interp(values, ts, cs[:, k])
    return out


def dilate(m, r):
    out = m.copy()
    for _ in range(r):
        out = out | np.roll(out, 1, 0) | np.roll(out, -1, 0) | np.roll(out, 1, 1) | np.roll(out, -1, 1)
    return out


def components(m, min_area):
    """Keep the 8-connected parts of m with at least min_area pixels."""
    from collections import deque
    lab = np.zeros(m.shape, np.int32)
    keep = np.zeros(m.shape, bool)
    H, W = m.shape
    n = 0
    for y, x in zip(*np.where(m)):
        if lab[y, x]:
            continue
        n += 1
        q = deque([(y, x)]); lab[y, x] = n; pts = []
        while q:
            cy, cx = q.popleft(); pts.append((cy, cx))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < H and 0 <= nx < W and m[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = n; q.append((ny, nx))
        if len(pts) >= min_area:
            ys, xs = zip(*pts); keep[ys, xs] = True
    return keep


def regions(img):
    rgb, solid = img[..., :3], img[..., 3] > 0
    s, v = hsv(rgb)
    h = img.shape[0]
    yy = np.arange(h)[:, None] * np.ones((1, img.shape[1]))
    outline = solid & ((v < 0.12) | ((v < 0.2) & (s < 0.35)))
    shorts = solid & ~outline & (s < 0.2) & (v < 0.45) & (yy > h * 0.45)
    light = solid & ~outline & (s < 0.25) & (v > 0.78)
    red_eye = solid & (rgb[..., 0] > 150) & (rgb[..., 1] < 70) & (rgb[..., 2] < 70) & \
        (rgb[..., 0] > 2.5 * rgb[..., 1]) & (yy < h * 0.4)
    skin = solid & ~outline & ~shorts & ~light & ~red_eye
    return dict(solid=solid, outline=outline, shorts=shorts, light=light, skin=skin, red_eye=red_eye)


def recolour(img, mask, stops, keep_hue=0.0):
    """Brightness-preserving recolour: lightness within the region (3rd..97th percentile -> 0..1) is
    looked up on a new ramp, so the drawn shading and anatomy stay."""
    out = img.copy()
    L = lum(img[..., :3])
    vals = L[mask]
    if not len(vals):
        return out
    lo, mid, hi = np.percentile(vals, [3, 50, 97])
    t = np.where(L <= mid, 0.5 * (L - lo) / max(mid - lo, 1), 0.5 + 0.5 * (L - mid) / max(hi - mid, 1))
    out[mask, :3] = ramp(np.clip(t[mask], 0, 1), stops)
    return out


def scale(img, sx, sy):
    """Resize a sprite, keeping a crisp silhouette and soft colour."""
    h, w = img.shape[:2]
    W, H = max(1, round(w * sx)), max(1, round(h * sy))
    m = img[..., 3:4] / 255
    pre = Image.fromarray(np.clip(img[..., :3] * m, 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    al = Image.fromarray((m[..., 0] * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    a = np.asarray(al).astype(np.float32) / 255
    rgb = np.asarray(pre).astype(np.float32) / np.maximum(a[..., None], 1e-3)
    out = np.zeros((H, W, 4), np.float32)
    out[..., :3] = np.clip(rgb, 0, 255)
    out[..., 3] = (a >= 0.5) * 255
    return out


def measure(img):
    """Head and body landmarks (screen pixels): top, bottom, neck row, head centre x, body centre x."""
    m = img[..., 3] > 0
    ys, xs = np.where(m)
    top, bot = ys.min(), ys.max()
    h = bot - top + 1
    widths = m.sum(1)
    lo, hi = top + int(0.2 * h), top + int(0.5 * h)
    neck = lo + int(np.argmin(widths[lo:hi]))
    head_rows = m[top:neck]
    cols = np.where(head_rows.any(0))[0]
    # head centre from the rows just above the neck (ears and horns sit higher)
    band = m[max(top, neck - int(0.35 * (neck - top))):neck]
    bx = np.where(band.any(0))[0]
    hcx = (bx.min() + bx.max()) / 2 if len(bx) else (cols.min() + cols.max()) / 2
    hx0, hx1 = (bx.min(), bx.max()) if len(bx) else (cols.min(), cols.max())
    # the skull's own top: the head's middle columns (horns and ears stick up at the sides)
    half = max(2, int(0.18 * (hx1 - hx0)))
    mid = m[:, int(hcx) - half:int(hcx) + half + 1]
    skull = int(np.where(mid.any(1))[0].min()) if mid.any() else top
    return dict(top=top, bot=bot, h=h, neck=neck, hcx=hcx, cx=(xs.min() + xs.max()) / 2,
                hx0=hx0, hx1=hx1, skull=skull)


class Canvas:
    """A sprite being built: layers composited in B's frame; the canvas grows as parts stick out."""

    def __init__(self, img):
        self.img = img.copy()
        self.ox = self.oy = 0          # where B's (0, 0) is on the canvas

    def paste(self, part, x, y, behind=False, mask=None):
        x, y = int(round(x)) + self.ox, int(round(y)) + self.oy
        ph, pw = part.shape[:2]
        bh, bw = self.img.shape[:2]
        x0, y0 = min(0, x), min(0, y)
        x1, y1 = max(bw, x + pw), max(bh, y + ph)
        if x0 < 0 or y0 < 0 or x1 > bw or y1 > bh:
            can = np.zeros((y1 - y0, x1 - x0, 4), np.float32)
            can[-y0:-y0 + bh, -x0:-x0 + bw] = self.img
            self.img = can
            self.ox -= x0; self.oy -= y0
            x -= x0; y -= y0
        reg = self.img[y:y + ph, x:x + pw]
        m = part[..., 3] > 0
        if mask is not None:
            m &= mask
        if behind:
            m &= reg[..., 3] == 0
        reg[m] = part[m]

    def crop(self):
        ys, xs = np.where(self.img[..., 3] > 0)
        return self.img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


# ---------------------------------------------------------------------------------------------
# Pixel-art parts drawn on the drafts' grid, softened the way the drafts are
# ---------------------------------------------------------------------------------------------

def art(rows, pal):
    """ASCII pixel art -> RGBA (art pixels). '.' and ' ' are empty; other characters index pal."""
    h, w = len(rows), max(len(r) for r in rows)
    a = np.zeros((h, w, 4), np.float32)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in pal:
                a[y, x, :3] = hexc(pal[ch]); a[y, x, 3] = 255
    return a


def soften(a, scale=P):
    """Art pixels -> screen pixels: colour blends smoothly between art pixels, the silhouette stays crisp."""
    h, w = a.shape[:2]
    al = a[..., 3] > 0
    filled, known = a[..., :3].copy(), al.copy()
    for _ in range(3):            # bleed colour outward so the smooth resize pulls in no black from outside
        acc = np.zeros_like(filled); cnt = np.zeros(al.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(np.roll(filled * known[..., None], dy, 0), dx, 1)
            cnt += np.roll(np.roll(known, dy, 0), dx, 1)
        new = (~known) & (cnt > 0)
        filled[new] = acc[new] / cnt[new][:, None]
        known |= new
    rgb = Image.fromarray(np.clip(filled, 0, 255).astype(np.uint8)).resize((w * scale, h * scale), Image.BILINEAR)
    mask = np.repeat(np.repeat(al, scale, 0), scale, 1)
    out = np.zeros((h * scale, w * scale, 4), np.float32)
    out[..., :3] = np.asarray(rgb).astype(np.float32)
    # the black outline stays solid black, a full art pixel thick, as in the drafts
    ink = al & (a[..., :3].max(-1) < 30)
    ink_big = np.repeat(np.repeat(ink, scale, 0), scale, 1)
    out[ink_big, :3] = OUTLINE
    out[..., 3] = mask * 255
    return out


def mirror(rows):
    return [r[::-1] for r in rows]


def find(rows, ch='@'):
    """The anchor pixel (marked '@', drawn as the colour after it in the palette key '@')."""
    for y, r in enumerate(rows):
        x = r.find(ch)
        if x >= 0:
            return x, y
    raise KeyError(ch)


# Right-hand horn (viewer's right, facing south): root at '@' sits on the side of the skull.
HORN_S = [
    ".........KK.",
    "........K4K.",
    "........K3K.",
    ".......K32K.",
    ".......K32K.",
    "......K321K.",
    ".....K3221K.",
    "...KK32221K.",
    ".KK3322211K.",
    "@3332221KK..",
    "K222211KK...",
    "KK1111KK....",
    ".KKKKKK.....",
]
# Side view: the horn rises from the top of the skull and sweeps back (to the left when facing east).
HORN_E = [
    "KK.........",
    "K4K........",
    "K32K.......",
    ".K32K......",
    ".K321K.....",
    "..K3221KK..",
    "..K322211KK",
    "...K2222211@",
    "....KKKKKKKK",
]
# Bat ear (viewer's right, facing south): pointed up and out, its inner side showing.
EAR_S = [
    ".......KK",
    "......K3K",
    ".....K32K",
    "....K3i2K",
    "...K3ii2K",
    "..K3iii2K",
    ".K32ii2K.",
    "@322i22K.",
    "K22222K..",
    "KKKKKK...",
]
# Side view: the ear stands on the back of the skull, its outer side showing.
EAR_E = [
    "KK....",
    "K3K...",
    "K32K..",
    "K322K.",
    "K3212K",
    ".K3212K",
    ".K32211@",
    "..KKKKKK",
]
PAL = {
    'horn': {'K': '#0c0a0c', '1': '#7a6e5e', '2': '#c8bca2', '3': '#ece4cc', '4': '#ffffff', '@': '#c8bca2'},
    'vampire_ear': {'K': '#0c0a0c', '1': '#77738a', '2': '#bdb9c8', '3': '#efedf5', 'i': '#c48a9e', '@': '#bdb9c8'},
    'gargoyle_ear': {'K': '#0c0a0c', '1': '#2a2a30', '2': '#5c5c64', '3': '#8e8e96', 'i': '#3a363c', '@': '#5c5c64'},
}


def head_parts(canvas, d, south, east, pal, height_frac=0.28, inset=2, east_frac=0.12, east_inset=3):
    """Two parts on the sides of the skull (south / north) or one on the back of it (east / west),
    behind the head so its outline covers their roots."""
    B = canvas.img
    mb = measure(B)
    m = B[..., 3] > 0
    fx, fy = canvas.ox, canvas.oy          # canvas -> B's frame, fixed before anything is pasted
    if d in ('south', 'north'):
        row = int(mb['skull'] + height_frac * (mb['neck'] - mb['skull']))
        xs = np.where(m[row])[0]
        for rows, x_edge, sign in ((south, xs.max(), 1), (mirror(south), xs.min(), -1)):
            part = soften(art(rows, pal))
            ax, ay = find(rows)
            x = x_edge - sign * inset * P - ax * P - (P if sign < 0 else 0)
            canvas.paste(part, x - fx, row - ay * P - fy, behind=True)
    else:
        rows = east if d == 'east' else mirror(east)
        row = int(mb['skull'] + east_frac * (mb['neck'] - mb['skull']))
        xs = np.where(m[row])[0]
        part = soften(art(rows, pal))
        ax, ay = find(rows)
        if d == 'east':      # back of the head is to the left
            x = xs.min() + east_inset * P - ax * P
        else:
            x = xs.max() - east_inset * P - ax * P
        canvas.paste(part, x - fx, row - ay * P - fy, behind=True)


# ---------------------------------------------------------------------------------------------
# The race's own features, from its own sprite (restyled)
# ---------------------------------------------------------------------------------------------

def head_features(B, R, below_frac=0.55, min_art=3):
    """The parts of R's head (ears, horns) that stick out past B's head, placed on B: R is scaled so its
    head height matches B's and its head centre and top sit on B's. Returns (part, x, y, mask)."""
    mb, mr = measure(B), measure(R)
    s = (mb['neck'] - mb['skull']) / max(mr['neck'] - mr['skull'], 1)
    Rs = scale(R, s, s)
    ms = measure(Rs)
    x = mb['hcx'] - ms['hcx']
    y = mb['skull'] - ms['skull']
    # R's pixels in B's frame
    H, W = Rs.shape[:2]
    yy = np.arange(H)[:, None] + y
    cut = mb['skull'] + below_frac * (mb['neck'] - mb['skull'])   # only above this line: ears and horns
    inside_B = np.zeros((H, W), bool)
    bm = B[..., 3] > 0
    gy0, gx0 = int(round(y)), int(round(x))
    for ry in range(H):
        by = ry + gy0
        if 0 <= by < bm.shape[0]:
            xs0, xs1 = max(0, gx0), min(bm.shape[1], gx0 + W)
            if xs1 > xs0:
                inside_B[ry, xs0 - gx0:xs1 - gx0] = bm[by, xs0:xs1]
    feat = (Rs[..., 3] > 0) & (yy < cut) & ~dilate(inside_B, P)
    core = components(feat & ~dilate(inside_B, P * 2), min_art * P * P)
    feat &= dilate(core, P * 3)
    return Rs, x, y, feat


def own_head(B, R, width_scale=1.0):
    """Replace B's head with R's own head (restyled), sized to B's shoulders."""
    mb, mr = measure(B), measure(R)
    s = ((mb['hx1'] - mb['hx0']) / max(mr['hx1'] - mr['hx0'], 1)) * width_scale
    Rs = scale(R, s, s)
    ms = measure(Rs)
    head = Rs.copy()
    head[ms['neck']:, :, 3] = 0                        # R's own head, down to its jaw
    body = B.copy()
    body[:mb['neck'], :, 3] = 0                        # B without its head
    x = mb['hcx'] - ms['hcx']
    y = (mb['neck'] + 2 * P) - ms['neck']              # the jaw overlaps the shoulders a little
    return body, head, x, y


def pattern_from(B, R, skin_mask, colour, strength=0.85):
    """Lay R's light markings (a flayed or spotted pattern) over B's skin, R stretched over B's body."""
    mb, mr = measure(B), measure(R)
    sy = mb['h'] / mr['h']
    bw = (B[..., 3] > 0).any(0).sum(); rw = (R[..., 3] > 0).any(0).sum()
    Rs = scale(R, bw / rw, sy)
    ms = measure(Rs)
    ox, oy = int(round(mb['cx'] - ms['cx'])), int(round(mb['top'] - ms['top']))
    s, v = hsv(Rs[..., :3])
    mark = (Rs[..., 3] > 0) & (v > 0.72) & (s < 0.45)
    full = np.zeros(B.shape[:2], bool)
    H, W = mark.shape
    for ry in range(H):
        by = ry + oy
        if 0 <= by < full.shape[0]:
            x0, x1 = max(0, ox), min(full.shape[1], ox + W)
            if x1 > x0:
                full[by, x0:x1] = mark[ry, x0 - ox:x1 - ox]
    full &= skin_mask
    out = B.copy()
    L = lum(B[..., :3])[..., None] / 255
    tone = hexc(colour) * (0.7 + 0.5 * L)
    out[full, :3] = out[full, :3] * (1 - strength) + tone[full] * strength
    return out


def wings_from(walk_sheet, fly_sheet, d):
    """The race's own wings: its flying sprite minus its walking body, restyled. Returns the wings and
    the walking body (restyled), both with their positions in the same frame."""
    walk = G.read_state(walk_sheet)[d]
    fly = G.read_state(fly_sheet)[d]
    body = walk[..., 3] > 0
    grown = body.copy()
    for _ in range(1):
        grown = grown | np.roll(grown, 1, 0) | np.roll(grown, -1, 0) | np.roll(grown, 1, 1) | np.roll(grown, -1, 1)
    wing = fly.copy()
    wing[grown] = 0
    w_img, w_org = G.restyle(wing, origin=True)
    b_img, b_org = G.restyle(walk, origin=True)
    return w_img, w_org, b_img, b_org


# ---------------------------------------------------------------------------------------------
# Textures and eyes
# ---------------------------------------------------------------------------------------------

def art_noise(shape, seed, cell=P):
    rng = np.random.default_rng(seed)
    gh, gw = shape[0] // cell + 2, shape[1] // cell + 2
    g = rng.random((gh, gw)).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((gw * cell, gh * cell), Image.BILINEAR)
    return np.asarray(im).astype(np.float32)[:shape[0], :shape[1]] / 255


def stone(img, mask, seed=3):
    n = art_noise(img.shape, seed)
    n2 = art_noise(img.shape, seed + 1, cell=P * 3)
    k = 0.86 + 0.22 * n * 0.6 + 0.22 * n2 * 0.4
    out = img.copy()
    out[mask, :3] = np.clip(out[mask, :3] * k[mask][:, None], 0, 255)
    return out


def scales(img, mask, light, dark, seed=5):
    n = art_noise(img.shape, seed, cell=P * 2)
    n2 = art_noise(img.shape, seed + 7, cell=P)
    out = img.copy()
    L = lum(img[..., :3])[..., None] / 255
    spot = mask & (n > 0.62)
    out[spot, :3] = out[spot, :3] * 0.4 + (hexc(light) * (0.6 + 0.6 * L))[spot] * 0.6
    fleck = mask & (n2 < 0.18)
    out[fleck, :3] = out[fleck, :3] * 0.55 + hexc(dark) * 0.45
    return out


def eyes(img, R, kind, colour):
    """Recolour the eyes. kind: 'red' (the Orc's red eyes), 'iris' (the dark iris inside light eye
    whites), 'whole' (whites and iris together glow in one colour), 'slit' (yellow eye, dark slit)."""
    out = img.copy()
    rgb = img[..., :3]
    m = img[..., 3] > 0
    mb = measure(img)
    H, W = m.shape
    yy = np.arange(H)[:, None] * np.ones((1, W))
    head = m & (yy > mb['top']) & (yy < mb['neck'])
    c = hexc(colour)
    if kind == 'red':
        e = R['red_eye'] & head
        L = lum(rgb)[..., None] / 255
        out[e, :3] = np.clip(c * (0.55 + 0.9 * L[e]), 0, 255)
        return out
    face = m & (yy > mb['skull'] + 0.3 * (mb['neck'] - mb['skull'])) & (yy < mb['skull'] + 0.8 * (mb['neck'] - mb['skull']))
    whites = components(R['light'] & face, 8)
    box = dilate(whites, P)
    L = lum(rgb)
    iris = box & head & ~whites & (L > 18) & (L < 120) & ~R['outline']
    if kind == 'iris':
        out[iris, :3] = c * (0.7 + 0.6 * L[iris][:, None] / 120)
    elif kind == 'whole':
        e = whites | iris
        out[e, :3] = np.clip(c * (0.75 + 0.45 * L[e][:, None] / 255), 0, 255)
    elif kind == 'slit':
        out[whites, :3] = np.clip(c * (0.7 + 0.4 * L[whites][:, None] / 255), 0, 255)
        out[iris, :3] = np.array([20, 16, 10], np.float32)
    return out


# ---------------------------------------------------------------------------------------------
# Races
# ---------------------------------------------------------------------------------------------

SKIN = {
    'HumanBlack': [(0, '#2a160c'), (0.5, '#6b4126'), (1, '#a8714a')],
    'Vampire': [(0, '#5d5a6c'), (0.5, '#bdb9c8'), (1, '#f2f0f7')],
    'Demon': [(0, '#4a0a12'), (0.5, '#a3202a'), (1, '#e0584a')],
    'Gargoyle': [(0, '#26262c'), (0.5, '#64646c'), (1, '#a2a2aa')],
    'DevourerZombie': [(0, '#3a0610'), (0.5, '#8e1c26'), (1, '#cc4c50')],
    'FrogMan': [(0, '#1f4a14'), (0.5, '#4f9a2a'), (1, '#9ad458')],
    'LizardMan': [(0, '#0b2f33'), (0.5, '#1d6f68'), (1, '#5cb59a')],
}


def race_view(race, d, drafts):
    """One race in one facing."""
    if race == 'HumanBlack':
        B = drafts[('Human', d)]
        return recolour(B, regions(B)['skin'], SKIN[race])

    if race == 'Vampire':
        B = scale(drafts[('Human', d)], 0.94, 1.08)
        Rg = regions(B)
        B = recolour(B, Rg['skin'], SKIN[race])
        B = eyes(B, Rg, 'iris', '#e01a1a')
        C = Canvas(B)
        head_parts(C, d, EAR_S, EAR_E, PAL['vampire_ear'], height_frac=0.3, inset=2)
        return C.crop()

    if race == 'Demon':
        B = scale(drafts[('Orc', d)], 1.12, 1.12)
        Rg = regions(B)
        B = recolour(B, Rg['skin'], SKIN[race])
        B = eyes(B, Rg, 'red', '#ffc21e')
        C = Canvas(B)
        head_parts(C, d, HORN_S, HORN_E, PAL['horn'], height_frac=0.1, inset=3)
        return C.crop()

    if race == 'Gargoyle':
        B = scale(drafts[('Dwarf', d)], 1.08, 1.16)
        Rg = regions(B)
        B = recolour(B, Rg['skin'], SKIN[race])
        B = stone(B, Rg['skin'])
        if d != 'north':
            B = eyes(B, Rg, 'whole', '#ffae22')
        C = Canvas(B)
        head_parts(C, d, EAR_S, EAR_E, PAL['gargoyle_ear'], height_frac=0.3, inset=2)
        return C.crop()

    if race == 'FrogMan':
        B = drafts[('Dwarf', d)]
        Rg = regions(B)
        B = recolour(B, Rg['skin'], SKIN[race])
        R = G.restyle(G.read_state('FrogMan')[d])
        body, head, x, y = own_head(B, R, width_scale=1.5)
        C = Canvas(body)
        C.paste(head, x, y)
        return C.crop()

    if race == 'LizardMan':
        B = drafts[('Human', d)]
        Rg = regions(B)
        B = recolour(B, Rg['skin'], SKIN[race])
        B = scales(B, Rg['skin'], '#8fd26a', '#062226')
        B = eyes(B, Rg, 'slit', '#ffd21a')
        return B

    if race == 'DevourerZombie':
        B = drafts[('Human', d)]
        Rg = regions(B)
        B = recolour(B, Rg['skin'], SKIN[race])
        R = G.restyle(G.read_state('DevourerZombie')[d])
        B = pattern_from(B, R, Rg['skin'], '#f2d2c8')
        B = eyes(B, Rg, 'iris', '#ff3a2a')
        return B

    if race == 'Skeleton':
        R = G.restyle(G.read_state('Skeleton')[d])
        hum = drafts[('Human', d)]
        s = hum.shape[0] * (50 / 53) / R.shape[0]
        return scale(R, s, s)

    if race in ('DemonFly', 'GargoyleFly', 'VampireFly'):
        walk = race[:-3]
        body = race_view(walk, d, drafts)
        w_img, w_org, b_img, b_org = wings_from(walk, race, d)
        # the old walking body (restyled) tells us how the wings sit on a body: map it onto the new body
        mo, mn = measure(b_img), measure(body)
        s = mn['h'] / mo['h']
        wx = (w_org[0] - b_org[0]) * s
        wy = (w_org[1] - b_org[1]) * s
        ws = scale(w_img, s, s)
        x = (mn['cx'] - mo['cx'] * s) + wx
        y = (mn['bot'] - mo['bot'] * s) + wy
        C = Canvas(body)
        C.paste(ws, x, y, behind=True)
        return C.crop()

    raise KeyError(race)


DRAFTED = ['Human', 'Dwarf', 'Night Elf', 'Orc', 'Goblin', 'Kobold']
NEW = ['HumanBlack', 'Vampire', 'VampireFly', 'Demon', 'DemonFly', 'Gargoyle', 'GargoyleFly',
       'FrogMan', 'LizardMan', 'DevourerZombie', 'Skeleton']
ORDER = ['Human', 'HumanBlack', 'Dwarf', 'Night Elf', 'Orc', 'Goblin', 'Kobold', 'Vampire', 'VampireFly',
         'Demon', 'DemonFly', 'Gargoyle', 'GargoyleFly', 'FrogMan', 'LizardMan', 'DevourerZombie', 'Skeleton']
LABEL = {'HumanBlack': 'Human (dark)', 'DevourerZombie': 'Zombie', 'VampireFly': 'Vampire, flying',
         'DemonFly': 'Demon, flying', 'GargoyleFly': 'Gargoyle, flying', 'FrogMan': 'Frogman', 'LizardMan': 'Lizardman'}


def sheet(sprites, path, names, cw=330, ch=330):
    lab = 190
    S = Image.new('RGBA', (lab + 4 * cw, len(names) * ch), (20, 18, 22, 255))
    d = ImageDraw.Draw(S)
    try:
        font = ImageFont.load_default(size=22)
        small = ImageFont.load_default(size=15)
    except TypeError:
        font = small = ImageFont.load_default()
    for r, name in enumerate(names):
        d.text((14, r * ch + ch // 2 - 22), LABEL.get(name, name), fill=(232, 224, 202), font=font)
        d.text((14, r * ch + ch // 2 + 8), 'GOA draft' if name in DRAFTED else 'new, own look', fill=(150, 142, 126), font=small)
        for c, dname in enumerate(DIRS):
            im = sprites[name][dname]
            h, w = im.shape[:2]
            tile = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))
            S.alpha_composite(tile, (lab + c * cw + (cw - w) // 2, r * ch + ch - 14 - h))
    S.save(path)
    return S.size


def main(only=None):
    drafts = cut_drafts()
    sprites = {race: {d: drafts[(race, d)] for d in DIRS} for race in DRAFTED}
    for race in (only or NEW):
        sprites[race] = {d: race_view(race, d, drafts) for d in DIRS}
    os.makedirs(os.path.join(HERE, 'sprites'), exist_ok=True)
    for race, views in sprites.items():
        for d, im in views.items():
            Image.fromarray(np.clip(im, 0, 255).astype(np.uint8)).save(os.path.join(HERE, 'sprites', f'{race}-{d}.png'))
    names = [r for r in ORDER if r in sprites]
    print('sheet', sheet(sprites, os.path.join(HERE, 'goa-races-all-v1.png'), names))


if __name__ == '__main__':
    import sys
    main(sys.argv[1:] or None)
