#!/usr/bin/env python3
"""Painted, tileable ground textures for the 3D view (plain Python: numpy + Pillow).

    python3 standalone/remastered/art/pipeline/make_ground.py

Writes game/Interface/textures/ground-grass.png, ground-earth.png and ground-stone.png
(512 px, wrapping seamlessly; the ground ones span 4 x 4 tiles, the stone one 2 x 2). The 3D view multiplies the terrain's
own colour by these, so they are stored as *detail*: each texture's average colour
is mid grey and only its variation remains (hue and value shifts, tufts, pebbles).

Grass: mottled patches at three scales, a little yellow and blue-green drift, dark
blade tufts and pale flecks, a few small flowers. Earth: grit, pebbles and darker
damp patches; used for paths, sand, snow, rock and farmland. Stone: cut ashlar for
fortress walls, towers and ramps: six courses of large blocks with their own tone,
bevelled edges, dark recessed joints and faint weathering streaks.
Everything is generated from seeded noise: no downloaded or sampled images.
"""

import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "game", "Interface", "textures")
N = 512


def band(rng, period_lo, period_hi):
    """Seamless noise with features between two periods (pixels), scaled to -1..1."""
    w = rng.standard_normal((N, N))
    f = np.fft.fftfreq(N)
    r = np.hypot(*np.meshgrid(f, f))
    lo, hi = 1.0 / period_hi, 1.0 / period_lo
    mask = np.exp(-((np.log(np.maximum(r, 1e-9)) - np.log((lo * hi) ** 0.5)) ** 2) / (2 * (np.log(hi / lo) / 2.5) ** 2))
    mask[0, 0] = 0
    out = np.real(np.fft.ifft2(np.fft.fft2(w) * mask))
    return out / (np.abs(out).max() + 1e-9)


def stamp(img, rng, n, colour, alpha, length, width, angle_jitter, vertical=True):
    """Short strokes (grass blades) or dots, wrapping round the edges."""
    h, w = img.shape[:2]
    for _ in range(n):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        L = rng.uniform(*length)
        a = (-np.pi / 2 if vertical else rng.uniform(0, np.pi)) + rng.uniform(-angle_jitter, angle_jitter)
        steps = max(1, int(L * 2))
        for k in range(steps):
            px, py = x + np.cos(a) * L * k / steps, y + np.sin(a) * L * k / steps
            for dx in range(width):
                ix, iy = int(px + dx) % w, int(py) % h
                img[iy, ix] = img[iy, ix] * (1 - alpha) + np.array(colour) * alpha


def grass(rng):
    L, M, S = band(rng, 160, 512), band(rng, 24, 96), band(rng, 3, 10)
    warm = band(rng, 64, 256)
    base = np.array([96, 122, 70], np.float32)
    dark = np.array([66, 92, 50], np.float32)
    light = np.array([128, 146, 86], np.float32)
    yellow = np.array([140, 142, 82], np.float32)
    v = 0.55 * L + 0.35 * M + 0.1 * S
    img = base + np.clip(v, 0, 1)[..., None] * (light - base) + np.clip(-v, 0, 1)[..., None] * (dark - base)
    img += np.clip(warm, 0, 1)[..., None] * (yellow - base) * 0.5
    img += np.clip(-warm, 0, 1)[..., None] * np.array([-6, 2, 8]) * 0.6
    stamp(img, rng, 5200, (58, 82, 44), 0.55, (2, 6), 1, 0.5)
    stamp(img, rng, 1800, (150, 164, 100), 0.45, (1, 3), 1, 0.6)
    stamp(img, rng, 900, (176, 184, 124), 0.5, (0.5, 1), 1, 0.0, vertical=False)
    for colour in ((236, 230, 200), (226, 196, 90), (200, 160, 200)):   # small flowers, sparse
        stamp(img, rng, 70, colour, 0.8, (0.5, 1), 2, 0.0, vertical=False)
    return img


def earth(rng):
    L, M, S = band(rng, 160, 512), band(rng, 20, 80), band(rng, 2, 6)
    base = np.array([128, 124, 118], np.float32)
    v = 0.45 * L + 0.35 * M + 0.2 * S
    img = base + v[..., None] * 22
    damp = np.clip(band(rng, 40, 160), 0.2, 1) - 0.2
    img -= damp[..., None] * 26
    stamp(img, rng, 1400, (150, 146, 138), 0.6, (1, 2.5), 2, 3.0, vertical=False)   # pebbles
    stamp(img, rng, 900, (96, 92, 88), 0.5, (1, 2), 1, 3.0, vertical=False)         # pebble shade
    stamp(img, rng, 2500, (110, 106, 100), 0.35, (0.5, 1), 1, 0.0, vertical=False)  # grit
    return img


def stone(rng):
    img = np.zeros((N, N, 3), np.float32) + np.array([128, 124, 118], np.float32)
    rows, rh = 6, N // 6
    L, S, M, streak = band(rng, 60, 256), band(rng, 2, 8), band(rng, 10, 40), band(rng, 8, 64)
    for r in range(rows):
        shift = int(rng.uniform(0, N))
        x, blocks = 0, []
        while x < N:
            w = int(rh * rng.uniform(1.25, 2.5))
            blocks.append((x, min(N, x + w)))
            x += w
        y0, y1 = r * rh, (r + 1) * rh
        for a, b in blocks:
            tone, warm = rng.uniform(-22, 22), rng.uniform(-6, 6)
            xs = (np.arange(a, b) + shift) % N
            img[y0:y1][:, xs] += np.array([tone + warm, tone, tone - warm])
            img[y0 + 2:y0 + 5][:, xs] += 12      # lit top bevel
            img[y1 - 5:y1 - 2][:, xs] -= 16      # shaded bottom bevel
            jx = (a + shift) % N
            img[y0:y1, jx:jx + 3] *= 0.45         # vertical joint
            img[y0:y1, (jx + 3) % N:(jx + 5) % N] += 6
        img[y0:y0 + 3, :] *= 0.45                 # bed joint
    img += (0.35 * L + 0.3 * M + 0.35 * S)[..., None] * 18
    img -= np.clip(streak, 0, 1)[..., None] * np.linspace(0, 14, N)[:, None, None]
    return img


def as_detail(img):
    """Average colour -> mid grey, keep the variation (the terrain colour is multiplied in)."""
    img = np.clip(img, 0, 255)
    mean = img.reshape(-1, 3).mean(axis=0)
    out = np.clip(img / mean * 128.0, 0, 255)
    return Image.fromarray(out.astype(np.uint8))


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn, seed in (("grass", grass, 11), ("earth", earth, 23), ("stone", stone, 37)):
        rng = np.random.default_rng(seed)
        as_detail(fn(rng)).save(os.path.join(OUT, f"ground-{name}.png"))
        print("wrote", os.path.join(OUT, f"ground-{name}.png"))


if __name__ == "__main__":
    main()
