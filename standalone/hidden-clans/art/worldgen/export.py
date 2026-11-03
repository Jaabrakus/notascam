"""Turn one hex region into game tiles: a small text file the game (or the arena test) reads.

    python3 export.py [seed] [col row]        # default: a land hex with a dungeon mouth and a chasm

Writes out/hex_<col>_<row>.txt: a header, then four layers (ground, caves, sky, depths) of one letter a
tile, rows from the top, '.' for tiles that belong to a neighbouring hex. The letters stand for the
same turf types the hand-made maps use (LEGEND below), so nothing new is needed in the game to load
it, except sky-island ground ("Cloudstone", planned in planning/SKY_CLOUDS_AIRSHIPS.md (c)). Also
writes out/hex_<col>_<row>.json with the counts of each turf and the cave mouths, for the test.
"""
import json
import os
import sys

import numpy as np

import worldgen as W
from heartland import *  # noqa: F401,F403

HERE = os.path.dirname(os.path.abspath(__file__))

# letter -> turf type
LEGEND = {
    "g": "/turf/grounds/grass", "G": "/turf/grounds/goodgrass", "t": "/turf/grounds/Trees/Tree1",
    "p": "/turf/grounds/Trees/TundraTree", "s": "/turf/grounds/snow", "d": "/turf/grounds/desert",
    "m": "/turf/grounds/marsh", "k": "/turf/grounds/waters/swamp", "w": "/turf/grounds/waters/water",
    "S": "/turf/grounds/waters/sea", "h": "/turf/grounds/waters/shallows", "r": "/turf/grounds/waters/river",
    "f": "/turf/grounds/waters/ford", "M": "/turf/grounds/cavefloor", "a": "/turf/grounds/hellfloor",
    "A": "/turf/grounds/hellcliff", "l": "/turf/grounds/lavas/lava", "x": "/turf/grounds/deadgrass",
    "F": "/turf/grounds/DetailedFloor", "W": "/turf/grounds/DetailedWall2", "H": "/turf/grounds/WoodWall",
    "b": "/turf/grounds/WoodFloor", "D": "/turf/grounds/Stairs/Down", "U": "/turf/grounds/Stairs/Up",
    "c": "/turf/grounds/cellarfloor", "o": "/turf/grounds/cavefloor2", "C": "/turf/grounds/Chasm",
    "K": "/turf/grounds/Sky", "P": "/turf/grounds/MountainPeak", "u": "/turf/grounds/waters/underwater",
}


def ground_letters(k, h, ocean):
    L = np.full(k.shape, "g", "<U1")
    put = {K_GRASS: "g", K_FIELD: "G", K_FOREST: "t", K_JUNGLE: "t", K_TUNDRA: "p", K_SNOW: "s", K_DESERT: "d",
           K_MESA: "d", K_SAND: "d", K_SHORE: "d", K_MARSH: "m", K_SWAMPW: "k", K_RIVER: "r", K_BRIDGE: "f",
           K_ROCK: "M", K_ORE: "M", K_ASH: "a", K_LAVA: "l", K_DEADGRASS: "x", K_ROAD: "F", K_TOWN: "F",
           K_BUILT: "F", K_WALL: "W", K_HOUSE: "H", K_MOUTH: "D", K_FALLS: "h", K_CHASM: "C"}
    for kk, ch in put.items():
        L[k == kk] = ch
    water = np.isin(k, [K_WATER, K_DEEP])
    L[water & ~ocean] = "w"                       # lakes
    L[water & ocean] = "S"                        # the sea
    L[water & ocean & (h > -0.035)] = "h"         # shallows by the shore can be waded
    return L


def under_letters(k, z):
    L = np.full(k.shape, "c" if z == 2 else "a", "<U1")
    put = {K_CAVEFLOOR: "c", K_TUNNEL: "o", K_MUSHROOM: "o", K_WATER: "w", K_DEEP: "u", K_LAVA: "l",
           K_WALL: "W", K_STAIRSUP: "U", K_CHASM: "C", K_SNOW: "s", K_ORE: "c", K_ASH: "a",
           K_ROCK: "A" if z == 4 else "c", K_DEADGRASS: "x"}
    for kk, ch in put.items():
        L[k == kk] = ch
    return L


def sky_letters(k):
    L = np.full(k.shape, "K", "<U1")
    put = {K_SKY: "K", K_PEAK: "P", K_GRASS: "g", K_FOREST: "t", K_WATER: "w", K_RIVER: "r", K_WALL: "W",
           K_CLOUDSTONE: "o", K_ORE: "o", K_FALLS: "w"}  # island rock stands in as open cave floor for now
    for kk, ch in put.items():
        L[k == kk] = ch
    return L


def pick_hex(w):
    best = None
    for p in w.places:
        if p["kind"] in ("dungeon", "delving") and p.get("z", 1) == 1:
            c, r = p["hex"]
            ch = sum(1 for cx, cy in w.chasms if tuple(map(int, W.hex_of(cx, cy))) == (c, r))
            n = sum(1 for q in w.places if tuple(q["hex"]) == (c, r) and q.get("z", 1) == 1)
            if ch and (best is None or n > best[0]):
                best = (n, c, r)
    return best[1], best[2]


def export(w, col, row):
    r = w.hex_region(col, row, layers=True)
    x0, y0 = r["origin"]
    n = r[1].shape[0]
    c = np.arange(n) + 0.5
    wx, wy = np.meshgrid(x0 + c, y0 + c)
    ocean = w.ocean[np.clip((wy // W.CELL).astype(int), 0, W.G - 1), np.clip((wx // W.CELL).astype(int), 0, W.G - 1)]
    layers = {1: ground_letters(r[1], r["height"], ocean), 2: under_letters(r[2], 2), 3: sky_letters(r[3]),
              4: under_letters(r[4], 4)}
    out = r["inside"]
    for z in layers:
        layers[z][~out] = "."
    name = "hex_%d_%d" % (col, row)
    path = os.path.join(HERE, "out", name + ".txt")
    with open(path, "w") as f:
        f.write("HEX %d %d %d %d %d %d\n" % (col, row, x0, y0, n, n))
        for z in (1, 2, 3, 4):
            f.write("LAYER %d\n" % z)
            for line in layers[z]:
                f.write("".join(line) + "\n")
    counts = {z: {LEGEND[ch]: int((layers[z] == ch).sum()) for ch in LEGEND if (layers[z] == ch).any()} for z in layers}
    mouths = [(int(mx), int(my), kind) for mx, my, kind, *_ in r["mouths"] if out[my, mx]]
    rock = np.argwhere(out & (layers[1] == "M"))
    meta = {"hex": [col, row], "origin": [x0, y0], "size": n, "tiles": int(out.sum()), "counts": counts,
            "mouths": mouths, "rock_samples": [[int(x), int(y)] for y, x in rock[:: max(1, len(rock) // 20)][:20]],
            "legend": LEGEND}
    with open(os.path.join(HERE, "out", name + ".json"), "w") as f:
        json.dump(meta, f, indent=1)
    return path, meta


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1026
    w = W.World(seed, True, log=lambda *a: None)
    if len(sys.argv) > 3:
        col, row = int(sys.argv[2]), int(sys.argv[3])
    else:
        col, row = pick_hex(w)
    path, meta = export(w, col, row)
    print(path, meta["tiles"], "tiles;", "mouths", meta["mouths"])
    for z, c in meta["counts"].items():
        print(z, sorted(c.items(), key=lambda kv: -kv[1])[:8])
