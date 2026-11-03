"""Read today's hand-made map layers (game/Maps/1-Ground.dmm and the other three) into grids of kinds.

Read-only: the map file is never written. Kinds are small ints shared with worldgen.py.
The .dmm lists rows top (y = max) first; the grid here is indexed [row from top][x].
"""
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MAPS = os.path.join(HERE, "..", "..", "game", "Maps")

# Tile kinds (shared with worldgen.py)
K_DEEP, K_WATER, K_SAND, K_GRASS, K_FOREST, K_DESERT, K_SNOW, K_MARSH, K_ROCK, K_JUNGLE, \
    K_MESA, K_TUNDRA, K_PEAK, K_RIVER, K_ROAD, K_TOWN, K_BUILT, K_ASH, K_SWAMPW, \
    K_SKY, K_CAVEFLOOR, K_LAVA, K_CHASM, K_DEADGRASS = range(24)
# kinds only the generator makes (K_CAVEFLOOR is the caves layer's solid rock, as today's cellarfloor)
K_TUNNEL, K_MOUTH, K_WALL, K_HOUSE, K_FIELD, K_ORE, K_BRIDGE, K_MUSHROOM, K_STAIRSUP, K_SHORE = range(24, 34)
K_CLOUDSTONE, K_FALLS = range(34, 36)   # a sky island's rock; falling water and its foam
NKINDS = 36
LAYERS = {1: "1-Ground", 2: "2-Underground", 3: "3-Sky", 4: "4-Hell"}


def kind_of(defn):
    turfs = re.findall(r"/turf/[A-Za-z0-9_/]+", defn)
    t = turfs[-1] if turfs else ""
    if "waters/underwater" in t:
        return K_DEEP
    if "waters/swamp" in t:
        return K_SWAMPW
    if "waters/river" in t:
        return K_RIVER
    if "waters" in t or "DesertWater" in t:
        return K_WATER
    if "lava" in t:
        return K_LAVA
    if "hellcliff" in t:
        return K_ROCK  # the Depths' rock walls
    if "hell" in t:
        return K_ASH
    if "Chasm" in t:
        return K_CHASM
    if t.endswith("/Sky"):
        return K_SKY
    if "MountainPeak" in t:
        return K_PEAK
    if "cellarfloor" in t:
        return K_CAVEFLOOR
    if "deadgrass" in t or "DeadTree" in t:
        return K_DEADGRASS
    if "goodgrass" in t:
        return K_GRASS
    if "TundraTree" in t:
        return K_TUNDRA
    if "Cactus" in t:
        return K_DESERT
    if "Bamboo" in t:
        return K_JUNGLE
    if "Trees" in t:
        return K_FOREST
    if t.endswith("/grass"):
        return K_GRASS
    if t.endswith("/marsh"):
        return K_MARSH
    if t.endswith("/desert"):
        return K_DESERT
    if t.endswith("/snow"):
        return K_SNOW
    if "cavefloor" in t or "NoDig" in t:
        return K_ROCK
    return K_BUILT  # walls, floors, stairs, tombs: hand-built places


def load(z=1):
    """Kinds grid of one of today's layers: 1 ground, 2 caves, 3 sky, 4 depths."""
    MAP = os.path.join(MAPS, LAYERS[z] + ".dmm")
    CACHE = os.path.join(HERE, "out", "heartland_z%d.npy" % z)
    if os.path.exists(CACHE) and os.path.getmtime(CACHE) > os.path.getmtime(MAP):
        return np.load(CACHE)
    keys = {}
    rows = []
    with open(MAP, encoding="latin-1") as f:
        in_grid = False
        for line in f:
            if not in_grid:
                m = re.match(r'^"(\w+)" = \((.*)\)\s*$', line)
                if m:
                    keys[m.group(1)] = kind_of(m.group(2))
                elif line.startswith("(1,1,1)"):
                    in_grid = True
                continue
            line = line.rstrip("\n")
            if line.startswith('"}'):
                break
            rows.append(line)
    w = len(next(iter(keys)))
    grid = np.array([[keys[r[i:i + w]] for i in range(0, len(r), w)] for r in rows], dtype=np.uint8)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    np.save(CACHE, grid)
    return grid


if __name__ == "__main__":
    for z in LAYERS:
        g = load(z)
        print(z, g.shape, np.bincount(g.ravel(), minlength=NKINDS))
