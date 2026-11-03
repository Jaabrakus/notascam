#!/usr/bin/env python3
"""The 3D view's pixel particles: dragon breath (Beasts.dm) and the race specials' bursts, rings,
trails and clouds (Specials.dm, remastered.html v3breathFx), drawn with the magic weapons' own
effect painters (wearables64.py: flames, sparkles, glows), so a dragon's fire looks like a flame
sword's.

    python3 standalone/remastered/art/enhance/breath64.py

Writes game/Icons/Remastered/Fx/breath.png: 32 px cells, 4 animation frames across, and down
three looks each of every element in ELEMENTS (3 rows each, in that order: the page's ELS list
must match). Stored as light to add, as the weapons' effects are (colour times opacity, on
black), so the page blends it additively.
  fire, frost, poison      the breath of fire, ice and poison drakes; fire pots
  magma, sand, water       magma, sand and water drakes
  plague, holy, unholy     zombie, holy and unholy drakes; the plague cloud; the shadow step
  mind, acid               the mind blast; acid spit
  dust, web, spark         slams, leaps, charges and sweeps; webs; arrows striking home
"""

import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wearables64 as w  # noqa: E402

GAME = os.path.join(HERE, "..", "..", "game")
OUT = os.path.join(GAME, "Icons", "Remastered", "Fx", "breath.png")
CELL, FRAMES, LOOKS = 32, 4, 3
ELEMENTS = ("fire", "frost", "poison", "magma", "sand", "water", "plague", "holy", "unholy", "mind", "acid", "dust", "web", "spark")


def core(cx, cy, r):
    yy, xx = np.mgrid[0:64, 0:64]
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r


def particle(element, look, frame):
    """One 64 px effect layer (drawn at the weapons' scale), cropped to its middle 32 px."""
    rng = np.random.default_rng(look * 97 + frame * 13 + ELEMENTS.index(element) * 7)
    p = w.PULSE[frame]
    cx, cy = 32, 36
    if element == "fire":
        c = core(cx, cy, 3 + look)
        fx = w.glow(c, (255, 140, 40), p * 0.7)
        fx[c] = (255, 196, 80, 235)   # the hot heart the glow rings
        srcs = [(cx + rng.uniform(-4, 4), cy + rng.uniform(-1, 3)) for _ in range(3 + look)]
        w.flames(fx, srcs, frame, seed=look + 3, height=7.5 + 2 * look)
    elif element == "frost":
        c = core(cx, cy, 2 + look)
        fx = w.glow(c, (170, 230, 255), p * 0.8)
        fx[c] = (214, 242, 255, 170)
        for k in range(6 + 2 * look):   # frost motes swirling
            a = rng.uniform(0, 2 * np.pi)
            r = rng.uniform(1, 9)
            w.sparkle(fx, cx + r * np.cos(a), cy + r * np.sin(a) + frame, (190, 240, 255), big=(k + frame) % 2 == 0)
    elif element == "poison":
        c = core(cx, cy, 3 + look)
        fx = w.glow(c, (110, 210, 70), p * 0.7)
        fx[c] = (130, 220, 80, 150)
        for k in range(5 + 2 * look):   # a sickly cloud: motes and drifting wisps
            x, y = cx + rng.uniform(-8, 8), cy + rng.uniform(-6, 6) - frame
            w.put(fx, x, y, (160, 240, 90), 210)
            w.put(fx, x + 1, y - 1, (90, 170, 50), 150)
            if k % 3 == frame % 3:
                w.sparkle(fx, x, y - 2, (210, 255, 120))
    elif element == "magma":
        c = core(cx, cy, 2 + look)
        fx = w.glow(c, (200, 60, 18), p * 0.8)
        fx[c] = (255, 120, 30, 230)
        for k in range(6 + 2 * look):   # glowing drops falling, with dark crust
            x, y = cx + rng.uniform(-7, 7), cy + rng.uniform(-6, 2) + frame * 1.5
            w.put(fx, x, y, (255, 214, 90) if k % 3 == 0 else (255, 140, 36), 240)
            w.put(fx, x, y + 1, (190, 50, 16), 200)
            if k % 4 == frame:
                w.put(fx, x + 1, y, (60, 24, 14), 120)
    elif element == "sand":
        c = core(cx, cy, 2 + look)
        fx = w.glow(c, (170, 140, 90), p * 0.45)
        for k in range(14 + 4 * look):  # grains blown along
            x, y = cx + rng.uniform(-10, 10) + frame, cy + rng.uniform(-6, 6)
            w.put(fx, x, y, (226, 196, 132) if k % 2 else (178, 142, 86), 230)
    elif element == "water":
        c = core(cx, cy, 2 + look)
        fx = w.glow(c, (70, 140, 240), p * 0.7)
        fx[c] = (110, 170, 255, 180)
        for k in range(6 + 2 * look):   # droplets: blue, a white glint on top
            x, y = cx + rng.uniform(-8, 8), cy + rng.uniform(-7, 4) + frame
            w.put(fx, x, y, (220, 240, 255), 240)
            w.put(fx, x, y + 1, (80, 150, 250), 230)
            w.put(fx, x + 1, y + 1, (50, 110, 220), 180)
    elif element == "plague":
        c = core(cx, cy, 3 + look)
        fx = w.glow(c, (120, 140, 56), p * 0.65)
        fx[c] = (110, 130, 52, 140)
        for k in range(6 + 2 * look):   # a murky miasma: green-brown motes, slow
            x, y = cx + rng.uniform(-9, 9), cy + rng.uniform(-6, 6) - frame * 0.5
            w.put(fx, x, y, (160, 176, 84), 200)
            w.put(fx, x + 1, y, (104, 112, 48), 150)
    elif element == "holy":
        c = core(cx, cy, 2 + look)
        fx = w.glow(c, (255, 226, 130), p * 0.8)
        fx[c] = (255, 244, 190, 220)
        for k in range(5 + 2 * look):   # golden sparkles rising
            a = rng.uniform(0, 2 * np.pi)
            r = rng.uniform(2, 10)
            w.sparkle(fx, cx + r * np.cos(a), cy + r * np.sin(a) - frame, (255, 230, 140), big=(k + frame) % 2 == 0)
    elif element == "unholy":
        c = core(cx, cy, 3 + look)
        fx = w.glow(c, (150, 50, 200), p * 0.75)
        fx[c] = (90, 30, 130, 200)
        for k in range(6 + 2 * look):   # violet smoke and black flames
            x, y = cx + rng.uniform(-8, 8), cy + rng.uniform(-5, 5) - frame
            w.put(fx, x, y, (190, 90, 240), 210)
            w.put(fx, x, y - 1, (110, 40, 150), 170)
        w.flames(fx, [(cx - 2, cy + 3), (cx + 3, cy + 2)], frame, seed=look + 11, height=5 + look)
        lit = fx[..., 3] > 0
        fx[lit, :3] = (fx[lit, :3].astype(float) * np.array([0.75, 0.35, 1.0])).astype(np.uint8)
    elif element == "mind":
        fx = np.zeros((64, 64, 4), np.uint8)
        yy, xx = np.mgrid[0:64, 0:64]
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        for r in (2 + frame * 2 + look, 6 + frame * 2 + look):   # rings of psychic force, spreading
            ring = np.abs(d - r) < 0.75
            fx[ring, :3] = (230, 140, 255)
            fx[ring, 3] = 220 if r < 9 else 140
        w.sparkle(fx, cx, cy, (255, 200, 255), big=frame % 2 == 0)
    elif element == "acid":
        c = core(cx, cy, 2 + look)
        fx = w.glow(c, (110, 250, 60), p * 0.75)
        fx[c] = (170, 255, 100, 200)
        for k in range(5 + 2 * look):   # bubbles: rings of bright green
            x, y = cx + rng.uniform(-7, 7), cy + rng.uniform(-6, 4) - frame
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                w.put(fx, x + ox, y + oy, (190, 255, 120), 220)
    elif element == "dust":
        c = core(cx, cy, 3 + look)
        fx = w.glow(c, (150, 130, 104), p * 0.5)
        fx[c] = (120, 104, 84, 120)
        for k in range(10 + 3 * look):  # specks thrown up
            x, y = cx + rng.uniform(-10, 10), cy + rng.uniform(-6, 4) - frame
            w.put(fx, x, y, (206, 188, 156) if k % 2 else (150, 132, 104), 210)
    elif element == "web":
        fx = np.zeros((64, 64, 4), np.uint8)
        for k in range(3 + look):       # strands of silk, glinting
            a = rng.uniform(0, np.pi) + frame * 0.2
            for s in np.linspace(-7, 7, 15):
                w.put(fx, cx + s * np.cos(a), cy + s * np.sin(a), (236, 236, 236), 220)
        w.sparkle(fx, cx + rng.uniform(-4, 4), cy + rng.uniform(-4, 4), (255, 255, 255), big=True)
    else:   # spark
        fx = np.zeros((64, 64, 4), np.uint8)
        for k in range(4 + look):       # a star of hot sparks flying out
            a = k / (4 + look) * 2 * np.pi + frame * 0.4
            for s in range(1, 3 + frame + look):
                w.put(fx, cx + s * np.cos(a), cy + s * np.sin(a), (255, 236, 160) if s < 3 else (255, 170, 60), 240 if s < 3 else 170)
        w.sparkle(fx, cx, cy, (255, 250, 210), big=True)
    out = np.zeros_like(fx)
    lit = fx[..., 3] > 0
    out[lit, :3] = (fx[lit, :3].astype(np.uint16) * fx[lit, 3:4] // 255).astype(np.uint8)
    out[lit, 3] = 255
    return out[cy - 22:cy + 10, cx - 16:cx + 16]


def main():
    sheet = np.zeros((CELL * len(ELEMENTS) * LOOKS, CELL * FRAMES, 4), np.uint8)
    for e, element in enumerate(ELEMENTS):
        for look in range(LOOKS):
            for f in range(FRAMES):
                r = e * LOOKS + look
                sheet[r * CELL:(r + 1) * CELL, f * CELL:(f + 1) * CELL] = particle(element, look, f)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    Image.fromarray(sheet).save(OUT, optimize=True)
    print(OUT, sheet.shape)


if __name__ == "__main__":
    main()
