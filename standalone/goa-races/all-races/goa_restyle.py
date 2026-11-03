#!/usr/bin/env python3
"""GOA-style restyle of a race's OWN sprite: its shape, face, ears, horns, wings and colours stay;
only the drawing style changes to match the GOA race drafts.

The race's current 64 px body (game/Icons/Remastered/Races64, read only) is
  1. enlarged x4 with EPX (keeps the pixel colours, rounds the stair steps),
  2. snapped to the drafts' art grid (6 screen pixels per art pixel), so it reads as the same chunky pixels,
  3. re-shaded as soft rounded volumes lit from the top left (warm light, cool shade), keeping its own
     colours and detail lines (eyes, mouth, muscle lines),
  4. given the drafts' thick black outline and their soft finish.
"""
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', 'remastered'))
RACES64 = os.path.join(ROOT, 'game', 'Icons', 'Remastered', 'Races64')
P = 6                     # screen pixels per art pixel (the drafts' grid)
UP = 4                    # Races64 pixel -> screen pixels (Races64 human 53 px -> 212, the drafts' 211)
DIRS = ['south', 'north', 'east', 'west']


def read_state(sheet, names=('', 'Normal'), frame=0):
    im = Image.open(os.path.join(RACES64, sheet + '.dmi'))
    desc = im.info['Description']
    w = int(re.search(r'\twidth = (\d+)', desc).group(1))
    a = np.asarray(im.convert('RGBA'))
    cols = a.shape[1] // w
    idx = 0
    for m in re.finditer(r'state = "([^"]*)"\n((?:\t.*\n)*)', desc):
        dirs = int(re.search(r'dirs = (\d+)', m.group(2)).group(1))
        frames = int(re.search(r'frames = (\d+)', m.group(2)).group(1))
        if m.group(1) in names and dirs == 4:
            out = {}
            for k, d in enumerate(DIRS):
                i = idx + frame * dirs + k
                out[d] = a[(i // cols) * w:(i // cols + 1) * w, (i % cols) * w:(i % cols + 1) * w].copy()
            return out
        idx += dirs * frames
    raise KeyError(sheet)


def epx(a):
    h, w = a.shape[:2]
    p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode='edge')
    E = p[1:-1, 1:-1]; B = p[:-2, 1:-1]; H = p[2:, 1:-1]; D = p[1:-1, :-2]; F = p[1:-1, 2:]
    eq = lambda x, y: np.all(x == y, axis=2)
    c = ~eq(B, H) & ~eq(D, F)
    e0 = np.where((c & eq(D, B))[..., None], D, E)
    e1 = np.where((c & eq(B, F))[..., None], F, E)
    e2 = np.where((c & eq(D, H))[..., None], D, E)
    e3 = np.where((c & eq(H, F))[..., None], F, E)
    out = np.zeros((2 * h, 2 * w, a.shape[2]), a.dtype)
    out[0::2, 0::2] = e0; out[0::2, 1::2] = e1; out[1::2, 0::2] = e2; out[1::2, 1::2] = e3
    return out


def lum(rgb):
    return rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11


def blur(img, r):
    """Box blur (separable, r passes of 3) on a float array (h, w[, c])."""
    out = img.astype(np.float32)
    for _ in range(r):
        out = (np.roll(out, 1, 0) + out + np.roll(out, -1, 0)) / 3
        out = (np.roll(out, 1, 1) + out + np.roll(out, -1, 1)) / 3
    return out


def masked_blur(rgb, mask, r):
    m = mask.astype(np.float32)
    num = blur(rgb * m[..., None], r)
    den = blur(m, r)[..., None]
    return np.where(den > 1e-3, num / np.maximum(den, 1e-3), rgb)


def distance(mask, cap):
    """Chamfer-ish distance (screen px) from each inside pixel to the outside, capped."""
    d = np.zeros(mask.shape, np.float32)
    cur = mask.copy()
    for k in range(1, cap + 1):
        d[cur] = k
        n4 = cur & np.roll(cur, 1, 0) & np.roll(cur, -1, 0) & np.roll(cur, 1, 1) & np.roll(cur, -1, 1)
        if k % 2 == 0:   # alternate 4- and 8-neighbour erosion: octagonal distance
            n4 &= np.roll(np.roll(cur, 1, 0), 1, 1) & np.roll(np.roll(cur, 1, 0), -1, 1) & \
                  np.roll(np.roll(cur, -1, 0), 1, 1) & np.roll(np.roll(cur, -1, 0), -1, 1)
        cur = n4
        if not cur.any():
            break
    return d


def restyle(cell, pad=3, origin=False):
    """One 64 px Races64 cell -> GOA-style RGBA (screen pixels). With origin=True also returns where
    the result's top-left sits in the cell, in screen pixels (cell pixel x UP)."""
    ys, xs = np.where(cell[..., 3] > 0)
    oy0, ox0 = max(ys.min() - pad, 0), max(xs.min() - pad, 0)
    a = cell[oy0:ys.max() + pad + 1, ox0:xs.max() + pad + 1]
    big = epx(epx(a))                                    # x4, palette kept
    H, W = big.shape[:2]
    # snap to the art grid: an art pixel is solid when most of it is
    gh, gw = -(-H // P), -(-W // P)
    padded = np.zeros((gh * P, gw * P, 4), np.uint8)
    padded[:H, :W] = big
    big = padded
    H, W = big.shape[:2]
    solid = big[..., 3] > 0
    art = solid.reshape(gh, P, gw, P).mean(axis=(1, 3)) >= 0.45
    mask = np.repeat(np.repeat(art, P, 0), P, 1)
    rgb = big[..., :3].astype(np.float32)
    # fill colour where the snapped mask grew past the source
    fill = masked_blur(rgb, solid, 6)
    rgb = np.where(solid[..., None], rgb, fill)
    L = lum(rgb)

    # the old drawing's dark rim (its outline) is replaced by ours; dark lines inside stay as detail
    inner = mask & (distance(mask, 10) > 7)
    # base colour: flatten the old banded light pass a little, keep detail lines
    base = masked_blur(rgb, inner, 2)
    base = rgb * 0.45 + base * 0.55

    # soft rounded volume: height from distance to the silhouette (and to dark detail lines)
    lines = inner & (L < np.percentile(L[inner], 12) if inner.any() else False)
    vol = mask & ~lines
    d = distance(vol, 30)
    R = 26.0
    h = np.sqrt(np.clip(d / R, 0, 1) * (2 - np.clip(d / R, 0, 1)))       # quarter circle profile
    h = blur(h, 3)
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * R / 3
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * R / 3
    n = np.stack([-gx, -gy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    l = np.array([-0.55, -0.62, 0.56]); l /= np.linalg.norm(l)
    lam = np.clip((n * l).sum(-1), 0, 1)
    # whole-body light: lighter up and to the left
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cy, cx = yy[mask].mean(), xx[mask].mean()
    span = max(W, H)
    glob = 1 - 0.35 * (xx - cx) / span - 0.25 * (yy - cy) / span
    shade = (0.58 + 0.55 * lam) * glob
    shade = blur(shade, 2)
    # warm light, cool shade
    warm = np.array([1.05, 1.0, 0.92]); cool = np.array([0.9, 0.93, 1.08])
    t = np.clip((shade - 0.7) / 0.5, 0, 1)[..., None]
    tint = cool * (1 - t) + warm * t
    col = base * shade[..., None] * tint
    # the drafts' contrast: a touch more saturation
    g = lum(col)[..., None]
    col = g + (col - g) * 1.12

    # thick black outline: the outer art pixels of the silhouette
    er = art.copy()
    er[1:-1, 1:-1] = art[1:-1, 1:-1] & art[:-2, 1:-1] & art[2:, 1:-1] & art[1:-1, :-2] & art[1:-1, 2:]
    er[0, :] = er[-1, :] = False; er[:, 0] = er[:, -1] = False
    rim = np.repeat(np.repeat(art & ~er, P, 0), P, 1)
    col[rim] = np.array([12, 10, 13], np.float32)
    # soft finish, as the drafts: colour blends across art pixels, the silhouette stays crisp
    col = masked_blur(col, mask, 2)
    out = np.zeros((H, W, 4), np.float32)
    out[..., :3] = np.clip(col, 0, 255)
    out[..., 3] = mask * 255
    ys, xs = np.where(mask)
    res = out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    if origin:
        return res, (ox0 * UP + xs.min(), oy0 * UP + ys.min())
    return res


if __name__ == '__main__':
    sheet = sys.argv[1]
    cells = read_state(sheet)
    for d in DIRS:
        Image.fromarray(restyle(cells[d]).astype(np.uint8)).save(f'/tmp/{sheet}-{d}.png')
