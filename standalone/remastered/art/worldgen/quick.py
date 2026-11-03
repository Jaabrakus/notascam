"""Quick look while tuning: python3 quick.py [seed] [0|1 heartland]"""
import json
import sys

import numpy as np
from PIL import Image, ImageDraw

import worldgen as W
from heartland import *  # noqa

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1026
hl = (sys.argv[2] != "0") if len(sys.argv) > 2 else True
w = W.World(seed, hl)
print(json.dumps(w.summary()))
pal = np.zeros((NKINDS, 3), np.uint8)
for k, c in {K_DEEP: (28, 52, 78), K_WATER: (52, 92, 118), K_SAND: (205, 190, 145), K_GRASS: (108, 128, 68),
             K_FOREST: (54, 82, 44), K_JUNGLE: (40, 92, 52), K_DESERT: (198, 170, 112), K_MESA: (168, 102, 70),
             K_SNOW: (228, 230, 232), K_TUNDRA: (176, 182, 170), K_MARSH: (96, 108, 78), K_ROCK: (122, 114, 104),
             K_ASH: (70, 58, 54), K_SHORE: (150, 150, 140), K_BUILT: (200, 170, 120), K_SWAMPW: (70, 90, 70)}.items():
    pal[k] = c
im = Image.fromarray(pal[w.biome])
d = ImageDraw.Draw(im)
for r in w.rivers:
    d.line([tuple(q) for q in (r["pts"] / 16)[:, :2]], fill=(60, 110, 170), width=1)
for r in w.roads:
    d.line([tuple(q) for q in (r["pts"] / 16)[:, :2]], fill=(120, 80, 40) if r["kind"] == "main" else (150, 120, 90))
for p in w.places:
    x, y = p["x"] / 16, p["y"] / 16
    col = {"city": (200, 40, 40), "town": (200, 40, 40), "heartland": (255, 215, 0), "village": (230, 120, 120),
           "dungeon": (20, 20, 20), "mine": (90, 60, 160), "ruin": (140, 140, 140)}[p["kind"]]
    s = 4 if p["kind"] in ("city", "heartland") else 2 if p["kind"] == "town" else 1
    d.rectangle([x - s, y - s, x + s, y + s], fill=col)
im.save("out/test_overview_%d_%d.png" % (seed, hl))
