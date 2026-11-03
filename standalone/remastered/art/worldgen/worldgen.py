"""Banners of the Deep world generator (offline, pictures only; no game files are written).

One seed makes the whole world. The world is 64 x 64 regions, one region = 256 x 256 tiles,
so 16,384 tiles across (today's hand-made map is 1,000 across). Every region has four layers
that line up tile for tile, the same four as today's game: ground (z1), caves (z2), sky (z3,
a peak above every ground mountain tile, open sky elsewhere, as today) and depths (z4).

Everything comes from pure functions of world tile position and the seed, so any region can
be made on its own, it is the same every run, and neighbouring regions meet without seams.
The whole-world parts that need the big picture (rivers, places, roads, sea lanes) are worked
out once on a coarse grid and kept as lists; a region's tiles draw the parts that cross it.

World tile coordinates: (wx, wy), wy grows southwards (rows of a picture). With the heartland
on, today's 1000 x 1000 map sits at (HX0, HY0): its .dmm row r, column c is world (HX0+c, HY0+r).
"""
import hashlib
import heapq
import json
import math
import os
import time
from collections import deque

import numpy as np

import heartland as HL
import lore
from heartland import *  # noqa: F401,F403  tile kinds
from noise import fbm, rand01, smoothstep

REGION = 256
NREG = 64
WORLD = REGION * NREG          # 16,384 tiles
CELL = 16                      # coarse map: one cell = 16 x 16 tiles
G = WORLD // CELL              # 1024 cells across
RCELL = 32                     # rivers and roads grid
RG = WORLD // RCELL            # 512 cells across
HX0 = HY0 = 30 * REGION + 12   # heartland sits in regions 30..33
HSIZE = 1000
# Regions are hexagons (owner, 10-27): six equal neighbours. Pointy-top hexes in rows, every odd
# row pushed half a hex right. HEX is the centre-to-corner size in tiles: a hex holds ~66,500 tiles,
# about one 256 x 256 square. Inside a hex the game's tiles stay square; a tile belongs to the hex
# whose centre is nearest.
HEX = 160.0
HEX_W = HEX * math.sqrt(3)     # 277 tiles across, flat side to flat side
HEX_ROW = HEX * 1.5            # 240 tiles from one row of centres to the next
HCOLS = int(WORLD // HEX_W)    # 59
HROWS = int(WORLD // HEX_ROW)  # 68
SWAMP = (HX0 + 1650, HY0 + 650, 1000, 800)   # centre and size of the great swamp beside the heartland
MOUNTAIN = 0.42                # height above this is mountain rock
PEAKS = 0.9                    # snowy summits on the pictures
DEEP = -0.12                   # deeper than this is deep water

RACES = {
    "human": "Humans", "dwarf": "Dwarves", "elf": "Night Elves", "lizard": "Lizardmen",
    "frog": "Frogmen", "orc": "Orcs", "goblin": "Goblins", "kobold": "Kobolds",
}


def blur(a, r):
    """Box blur (twice, close to a gaussian) with edges held."""
    for _ in range(2):
        p = np.pad(a, r, mode="edge")
        c = p.cumsum(0)
        c = np.vstack([np.zeros((1, c.shape[1])), c])
        a1 = (c[2 * r + 1:] - c[:-2 * r - 1]) / (2 * r + 1)
        c = a1.cumsum(1)
        c = np.hstack([np.zeros((c.shape[0], 1)), c])
        a = (c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)
    return a


def gauss(wx, wy, cx, cy, sx, sy=None):
    sy = sx if sy is None else sy
    return np.exp(-(((wx - cx) / sx) ** 2 + ((wy - cy) / sy) ** 2))


SYL_A = ["Ald", "Bel", "Cor", "Dun", "Eld", "Fen", "Gal", "Har", "Ith", "Kel", "Lan", "Mar", "Nes", "Orm",
         "Pel", "Ros", "Sar", "Tal", "Ul", "Var", "Wen", "Yr", "Bran", "Cael", "Gorm", "Hal", "Ash", "Brin",
         "Cran", "Fal", "Gild", "Karn", "Lith", "Mael", "Ost", "Stav", "Thorn", "Wex", "Ebon", "Frost",
         "Grim", "Hollow", "Iron", "Kest", "Raven", "Salt", "Stone", "Umber", "Wyr", "Bryn", "Dray"]
SYL_B = ["ford", "haven", "holm", "stead", "wick", "mere", "by", "ton", "gard", "fell", "more", "rest",
         "watch", "hollow", "brook", "crag", "moor", "reach", "vale", "march", "dale", "barrow", "keep",
         "spire", "garth", "wall", "bridge", "well", "hold", "mouth", "cross", "field", "stone", "wood"]


def place_name(rng):
    a = SYL_A[rng.integers(len(SYL_A))]
    b = SYL_B[rng.integers(len(SYL_B))]
    if a[-1] == b[0]:
        b = b[1:]
    return a + b


class World:
    def __init__(self, seed=1026, heartland=True, log=print):
        self.seed = seed
        self.hl = heartland
        self.log = log
        t0 = time.time()
        if heartland:
            self.hk = [HL.load(z) for z in (1, 2, 3, 4)]
            self._heartland_height()
        self._coarse()
        log("coarse map %.1fs" % (time.time() - t0))
        self._volcanoes()
        self._biomes()
        self._sky_islands()
        self._rivers()
        log("rivers %.1fs (%d)" % (time.time() - t0, len(self.rivers)))
        self._places()
        log("places %.1fs (%d)" % (time.time() - t0, len(self.places)))
        self._roads()
        log("roads %.1fs (%d)" % (time.time() - t0, len(self.roads)))
        self._sea_lanes()
        self._links()
        self.lands = []                 # no realms or borders: players conquer and claim the land
        self.land_of = np.full(self.h.shape, -1, np.int16)
        lore.stories(self)
        log("done %.1fs" % (time.time() - t0))

    # ---------------------------------------------------------------- height and climate
    def _heartland_height(self):
        k = self.hk[0]
        hh = np.full(k.shape, 0.10)
        hh[k == K_ROCK] = 0.62
        hh[k == K_DEEP] = -0.22
        hh[(k == K_WATER) | (k == K_RIVER)] = -0.08
        hh[k == K_SWAMPW] = -0.02
        hh[k == K_SNOW] = 0.14
        hh[k == K_DESERT] = 0.12
        self.hh = blur(hh, 6)
        self.hh_far = blur(hh, 28)

    def _heartland_mix(self, wx, wy, min_wl=32):
        dx = np.maximum(np.maximum(HX0 - wx, wx - (HX0 + HSIZE)), 0)
        dy = np.maximum(np.maximum(HY0 - wy, wy - (HY0 + HSIZE)), 0)
        dist = np.hypot(dx, dy)
        # outside, the edge of today's map is carried outward along wandering lines, not straight streaks
        sx = wx - HX0 + fbm(wx, wy, self.seed + 14, 300, max(min_wl, 16)) * dist * 1.2
        sy = wy - HY0 + fbm(wx, wy, self.seed + 15, 300, max(min_wl, 16)) * dist * 1.2
        # outside, read from just inside today's map: its outermost tiles are a thin rock frame
        m = np.where(dist > 0, 16, 0)
        c = np.clip(np.floor(sx), m, HSIZE - 1 - m).astype(int)
        r = np.clip(np.floor(sy), m, HSIZE - 1 - m).astype(int)
        # the blend reaches out a ragged distance, but always starts from today's map at its edge
        reach = np.maximum(420 + fbm(wx, wy, self.seed + 13, 420, max(min_wl, 16)) * 1400, 240)
        w = 1 - smoothstep(0, 1, dist / reach)
        self._hl_last = (r, c, w, dist)
        a = smoothstep(0, 120, dist)   # further out, a smoothed copy: no streaks drawn out of the edge
        return self.hh[r, c] * (1 - a) + self.hh_far[r, c] * a, w

    def heartland_blend(self, k, wx, wy, min_wl):
        """The mixed band round today's map (owner, 10-27: "maybe allow for a hybrid setting"): its own
        land (snow, grass, desert, woods) spills outward in patches that thin out with distance, so its
        winter breaks up into snow patches over the green instead of stopping at a line."""
        if not self.hl:
            return k
        self._heartland_mix(wx, wy, min_wl)
        r, c, w, dist = self._hl_last
        hk = self.hk[0][r, c]
        natural = [K_GRASS, K_FOREST, K_SNOW, K_TUNDRA, K_DESERT, K_MARSH, K_JUNGLE, K_MESA]
        n = np.clip(0.5 + fbm(wx, wy, self.seed + 18, 110, max(min_wl, 4)) * 2.4, 0, 1)
        take = (dist > 0) & (n < w ** 0.7) & np.isin(hk, natural) & np.isin(k, natural)
        return np.where(take, hk, k).astype(np.uint8)

    def height(self, wx, wy, min_wl):
        s = self.seed
        C = WORLD / 2
        cont = fbm(wx, wy, s + 1, 6000, min_wl) * 2.6 + 0.34
        d = np.hypot((wx - C) / C, (wy - C) / C) + fbm(wx, wy, s + 9, 3000, max(min_wl, 300)) * 0.5
        cont = cont - smoothstep(0.7, 1.0, d) * 1.7
        if self.hl:
            cont = cont + 0.55 * gauss(wx, wy, HX0 + 500, HY0 + 500, 2600) \
                - 1.2 * gauss(wx, wy, HX0 - 1150, HY0 + 520, 900, 560)
        base = cont * 0.5
        land = smoothstep(-0.02, 0.18, base)
        belt = smoothstep(0.0, 0.32, fbm(wx, wy, s + 2, 4500, max(min_wl, 1100)) * 2.6)
        # ranges: the crest lines of a warped noise, strongest in its first octave
        qx = wx + fbm(wx, wy, s + 10, 2200, max(min_wl, 250)) * 900
        qy = wy + fbm(wx, wy, s + 11, 2200, max(min_wl, 250)) * 900
        ridge = fbm(qx, qy, s + 3, 1900, min_wl, persistence=0.42, ridged=True)
        mount = belt * land * smoothstep(0.5, 0.9, ridge) ** 1.4 * 1.25
        hills = fbm(wx, wy, s + 4, 520, min_wl) * 0.45 * land
        if self.hl:   # the great swamp is a wide, flat lowland
            sw = gauss(wx, wy, *SWAMP) * land
            mount = mount * (1 - sw)
            hills = hills * (1 - 0.75 * sw)
            base = base * (1 - 0.85 * sw) + 0.07 * 0.85 * sw
        h = base + mount + hills
        if self.hl:
            hv, w = self._heartland_mix(wx, wy, min_wl)
            rough = fbm(wx, wy, s + 12, 260, min_wl) * 1.1 * smoothstep(0.3, 0.6, hv)   # crags on the rock
            h = h * (1 - w) + (hv + hills * 0.25 + rough) * w
        return h

    def _coarse(self):
        s = self.seed
        c = (np.arange(G) + 0.5) * CELL
        wx, wy = np.meshgrid(c, c)
        self.cwx, self.cwy = wx, wy
        self.h = self.height(wx, wy, 32)
        water = self.h < 0
        self.ocean = self._flood_border(water)
        coast = blur(self.ocean.astype(float), 24)
        t = 0.21 + wy / WORLD * 0.85 + fbm(wx, wy, s + 5, 3500, 400) * 1.0 \
            - np.maximum(self.h - 0.25, 0) * 0.35
        m = 0.42 + fbm(wx, wy, s + 6, 3000, 300) * 1.3 + coast * 0.35
        if self.hl:
            t = t + 0.08 * gauss(wx, wy, HX0 + 500, HY0 + 500, 1200)
            m = m + 0.5 * gauss(wx, wy, *SWAMP)   # the great swamp east of the heartland (owner, 10-27)
        self.temp = np.clip(t, 0, 1)
        self.moist = np.clip(m, 0, 1)
        self.hmask = np.zeros((G, G), bool)
        if self.hl:
            a, b = HX0 // CELL, (HX0 + HSIZE) // CELL
            self.hmask[a:b + 1, a:b + 1] = True

    @staticmethod
    def _flood_border(mask):
        n = mask.shape[0]
        seen = np.zeros_like(mask)
        q = deque()
        for i in range(n):
            for (y, x) in ((0, i), (n - 1, i), (i, 0), (i, n - 1)):
                if mask[y, x] and not seen[y, x]:
                    seen[y, x] = True
                    q.append((y, x))
        while q:
            y, x = q.popleft()
            for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= yy < n and 0 <= xx < n and mask[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True
                    q.append((yy, xx))
        return seen

    def sample(self, a, wx, wy):
        """Bilinear sample of a coarse-grid field at world tile positions."""
        fx = np.clip(wx / CELL - 0.5, 0, G - 1.001)
        fy = np.clip(wy / CELL - 0.5, 0, G - 1.001)
        x0 = fx.astype(int)
        y0 = fy.astype(int)
        u = fx - x0
        v = fy - y0
        return (a[y0, x0] * (1 - u) * (1 - v) + a[y0, x0 + 1] * u * (1 - v)
                + a[y0 + 1, x0] * (1 - u) * v + a[y0 + 1, x0 + 1] * u * v)

    # ---------------------------------------------------------------- volcanoes and biomes
    def _volcanoes(self):
        rng = np.random.default_rng(self.seed + 300)
        cand = np.argwhere((self.h > 0.72) & (self.temp > 0.3) & ~self.hmask)
        rng.shuffle(cand)
        self.volcanoes = []
        for y, x in cand:
            wx, wy = (x + 0.5) * CELL, (y + 0.5) * CELL
            if all(math.hypot(wx - v[0], wy - v[1]) > 3000 for v in self.volcanoes):
                self.volcanoes.append((wx, wy, float(rng.uniform(320, 620))))
            if len(self.volcanoes) >= 7:
                break

    def ash(self, wx, wy):
        a = np.zeros(np.shape(wx), bool)
        wob = fbm(wx, wy, self.seed + 40, 260, 32) * 1.6
        for vx, vy, r in self.volcanoes:
            a |= np.hypot(wx - vx, wy - vy) < r * (1 + wob)
        return a

    def classify(self, h, t, m, ash):
        """Ground biome kind for height/temperature/moisture (forest here = woodland biome)."""
        k = np.full(h.shape, K_GRASS, np.uint8)
        k[(t > 0.68) & (m > 0.6)] = K_JUNGLE
        k[(t > 0.62) & (m < 0.38)] = K_DESERT
        k[(t > 0.6) & (m < 0.42) & (h > 0.26)] = K_MESA
        k[(t <= 0.68) & (t >= 0.3) & (m > 0.6)] = K_FOREST
        k[(t >= 0.3) & (m > 0.66) & (h < 0.14)] = K_MARSH   # swamp lands: low, flat and wet
        k[t < 0.3] = K_TUNDRA
        k[t < 0.16] = K_SNOW
        k[ash] = K_ASH
        k[h > MOUNTAIN] = K_ROCK
        beach = (h >= 0) & (h < 0.022)
        k[beach & (t > 0.22) & (k != K_MARSH)] = K_SAND
        k[beach & (t <= 0.22)] = K_SHORE
        k[h < 0] = K_WATER
        k[h < DEEP] = K_DEEP
        return k

    def _biomes(self):
        self.biome = self.heartland_blend(self.classify(self.h, self.temp, self.moist, self.ash(self.cwx, self.cwy)),
                                          self.cwx, self.cwy, 32)
        if self.hl:
            # the heartland's own ground, by the most common kind in each cell
            a = HX0 // CELL + 1            # first coarse cell wholly inside the heartland
            o = a * CELL - HX0             # its first heartland column (HX0 == HY0)
            sub = self.hk[0][o:o + 61 * CELL, o:o + 61 * CELL]
            sub = sub.reshape(61, CELL, 61, CELL).transpose(0, 2, 1, 3).reshape(61, 61, CELL * CELL)
            counts = np.stack([(sub == i).sum(-1) for i in range(NKINDS)], -1)
            self.biome[a:a + 61, a:a + 61] = counts.argmax(-1)

    # ---------------------------------------------------------------- sky islands
    def _sky_islands(self):
        """Land in the sky (z 3), at the sky height. The great one hangs over the open sea (owner, 10-27:
        "put it in the ocean"), far out at the edge of the world, to be discovered; its lake's river runs off
        the edge as the Great Falls, straight down into the waves. A dozen small ones float over sea and open land."""
        rng = np.random.default_rng(self.seed + 800)
        ocean = self.ocean & ~blur(~self.ocean & (self.h >= 0), 2).astype(bool)
        land = (self.h >= 0)
        near_land = blur(land.astype(float), 30) > 0.002       # within ~500 tiles of a coast
        A, B = 200, 145
        ey, ex = np.mgrid[-B // CELL - 2:B // CELL + 3, -A // CELL - 2:A // CELL + 3]
        ell = (ex * CELL / (A + 40)) ** 2 + (ey * CELL / (B + 40)) ** 2 <= 1
        best = None
        hcx, hcy = HX0 + 500, HY0 + 500
        far_out = ~blur(land.astype(float), 30).astype(bool)   # open sea, out of sight of any coast
        for y, x in np.argwhere(ocean & far_out)[::5]:
            if y + ey.min() < 0 or y + ey.max() >= G or x + ex.min() < 0 or x + ex.max() >= G:
                continue
            if not ocean[y + ey[ell], x + ex[ell]].all():
                continue
            wx, wy = (x + 0.5) * CELL, (y + 0.5) * CELL
            # out at the edge of the world, to be discovered (owner, 10-27), but inside its last ring
            d = math.hypot(wx - WORLD / 2, wy - WORLD / 2)
            edge = min(wx, wy, WORLD - wx, WORLD - wy)
            if edge < 700:
                continue
            score = -abs(edge - 1000) + rng.random() * 400   # along the outer ring, not jammed in a corner
            if best is None or score > best[0]:
                best = (score, wx, wy)
        self.islands = []
        if best:
            _, cx, cy = best
            # the falls face the nearest shore, so they can be seen from land
            ly, lx = np.nonzero(land)
            k = np.argmin((ly - cy / CELL) ** 2 + (lx - cx / CELL) ** 2)
            ang = math.atan2(ly[k] - cy / CELL, lx[k] - cx / CELL)
            fx, fy = cx + math.cos(ang) * A * 1.02, cy + math.sin(ang) * B * 1.02
            self.islands.append({"n": 0, "x": cx, "y": cy, "a": A, "b": B, "great": True,
                                 "falls": (fx, fy), "ang": ang})
        # small islands, over sea or open land (never over mountains: a mountain's top is already there)
        open_ = (self.h < MOUNTAIN - 0.08) & ~self.hmask
        cand = np.argwhere(open_)
        rng.shuffle(cand)
        for y, x in cand:
            if len(self.islands) >= 13:
                break
            a, b = float(rng.uniform(40, 85)), float(rng.uniform(30, 65))
            wx, wy = (x + 0.5) * CELL, (y + 0.5) * CELL
            r = int((a + 30) // CELL) + 1
            if y - r < 0 or x - r < 0 or y + r >= G or x + r >= G or not open_[y - r:y + r + 1, x - r:x + r + 1].all():
                continue
            if any(math.hypot(wx - i["x"], wy - i["y"]) < 1400 for i in self.islands):
                continue
            self.islands.append({"n": len(self.islands), "x": wx, "y": wy, "a": a, "b": b, "great": False,
                                 "falls": None, "over_sea": bool(self.h[y, x] < 0),
                                 "near_peak": bool((self.h[y - r - 6:y + r + 7, x - r - 6:x + r + 7] > MOUNTAIN).any())})

    def sky_tiles(self, wx, wy, min_wl=8):
        """Sky-island kinds at world tile positions (0 where there is no island), and the foam of the
        falls on the water below (a mask)."""
        s = self.seed
        out = np.zeros(np.shape(wx), np.uint8)
        foam = np.zeros(np.shape(wx), bool)
        for isl in self.islands:
            pad = 40
            if not ((wx > isl["x"] - isl["a"] - pad) & (wx < isl["x"] + isl["a"] + pad) &
                    (wy > isl["y"] - isl["b"] - pad) & (wy < isl["y"] + isl["b"] + pad)).any():
                continue
            d = np.hypot((wx - isl["x"]) / isl["a"], (wy - isl["y"]) / isl["b"])
            d = d * (1 + fbm(wx, wy, s + 90 + isl["n"], 90, max(min_wl, 8)) * 0.55)
            inside = d < 1
            k = np.full(np.shape(wx), K_GRASS, np.uint8)
            k[fbm(wx, wy, s + 91, 34, max(min_wl, 4)) * 2.6 > 0.3] = K_FOREST
            k[d > 0.86] = K_CLOUDSTONE
            sky_ore = (d > 0.86) & (rand01(np.floor(wx).astype(np.int64), np.floor(wy).astype(np.int64), s + 92) < 0.03)
            k[sky_ore] = K_ORE                          # skystone in the rim
            if isl["great"]:
                lx = isl["x"] - math.cos(isl["ang"]) * isl["a"] * 0.25
                ly = isl["y"] - math.sin(isl["ang"]) * isl["b"] * 0.25
                lake = np.hypot((wx - lx) / (isl["a"] * 0.3), (wy - ly) / (isl["b"] * 0.3)) * \
                    (1 + fbm(wx, wy, s + 93, 50, max(min_wl, 4)) * 0.5) < 1
                k[lake] = K_WATER
                fx, fy = isl["falls"]
                # the river: lake to lip, straight enough to read, a little wobble
                t = np.clip(((wx - lx) * (fx - lx) + (wy - ly) * (fy - ly)) / ((fx - lx) ** 2 + (fy - ly) ** 2), 0, 1)
                off = np.hypot(wx - (lx + t * (fx - lx)), wy - (ly + t * (fy - ly)))
                river = off < 6 + 3 * t
                k[river] = K_RIVER
                # a ruined sky temple beside the lake
                tx, ty = lx + math.sin(isl["ang"]) * isl["b"] * 0.45, ly - math.cos(isl["ang"]) * isl["b"] * 0.45
                ring = (np.abs(np.abs(wx - tx) - 9) < 1.2) & (np.abs(wy - ty) < 10) | \
                    (np.abs(np.abs(wy - ty) - 9) < 1.2) & (np.abs(wx - tx) < 10)
                k[ring & inside & (rand01(np.floor(wx).astype(np.int64), np.floor(wy).astype(np.int64), s + 94) < 0.7)] = K_WALL
                # the falling water just past the lip, and the foam where it lands
                lip = np.hypot(wx - fx, wy - fy)
                k[(lip < 10) & ~inside] = K_FALLS
                inside |= (lip < 10)
                foam |= lip < 26 * (1 + fbm(wx, wy, s + 95, 30, max(min_wl, 4)) * 0.6)
            out[inside] = k[inside]
        return out, foam

    def _deep_places(self, rng, hm):
        """Places under the ground: the Underhalls in the caves (the peoples' old homes before they climbed
        out), and in the depths the demon keeps by the hellgates and the Wound at the heart of the Deep."""
        h = self.h
        cand = np.argwhere((h > MOUNTAIN + 0.05) & ~hm)
        rng.shuffle(cand)
        halls = []
        for y, x in cand:
            wx, wy = float((x + 0.5) * CELL), float((y + 0.5) * CELL)
            if all(math.hypot(wx - a, wy - b) > 1500 for a, b in halls):
                halls.append((wx, wy))
                b = self._biome_at(wx, wy)
                self.places.append({"kind": "underhall", "z": 2, "x": round(wx), "y": round(wy), "biome": int(b),
                                    "r": float(rng.uniform(55, 95)), "race": self._race(b, wx, wy, rng),
                                    "name": "The Underhalls of " + place_name(rng)})
            if len(halls) >= 26:
                break
        gates = [p for p in self.places if p.get("type") == "hellgate"]
        for i, g in enumerate(gates[::2]):
            a = rng.uniform(0, 2 * np.pi)
            self.places.append({"kind": "demon keep", "z": 4, "x": int(np.clip(g["x"] + math.cos(a) * 260, 60, WORLD - 60)),
                                "y": int(np.clip(g["y"] + math.sin(a) * 260, 60, WORLD - 60)), "biome": int(K_ASH),
                                "gate": g["name"], "name": "Keep of " + place_name(rng)})
        if self.volcanoes:
            vx, vy, vr = max(self.volcanoes, key=lambda v: v[2])
            self.places.append({"kind": "the wound", "z": 4, "x": int(vx), "y": int(vy), "biome": int(K_ASH),
                                "name": "The Wound"})
        for isl in self.islands:
            p = {"kind": "sky island", "z": 3, "x": int(isl["x"]), "y": int(isl["y"]), "biome": int(K_GRASS),
                 "island": isl["n"], "great": isl["great"],
                 "name": ("The Sky Isle of " if isl["great"] else "Skyrock of ") + place_name(rng)}
            self.places.append(p)
            if isl["great"]:
                fx, fy = isl["falls"]
                self.places.append({"kind": "falls", "z": 1, "x": int(fx), "y": int(fy), "biome": int(K_WATER),
                                    "name": "The Great Falls"})

    # ---------------------------------------------------------------- rivers
    def _rivers(self):
        n = RG
        hr = self.h.reshape(n, 2, n, 2).mean((1, 3))
        # a little unevenness so water on a gentle slope gathers and wanders, not straight parallel lines
        c = (np.arange(n) + 0.5) * RCELL
        rx_, ry_ = np.meshgrid(c, c)
        hr = hr + fbm(rx_, ry_, self.seed + 16, 600, 64) * 0.25 + rand01(np.arange(n)[None, :], np.arange(n)[:, None],
                                                                       self.seed + 17) * 0.004
        ocean = self.ocean.reshape(n, 2, n, 2).any((1, 3))
        moist = self.moist.reshape(n, 2, n, 2).mean((1, 3))
        hm = self.hmask.reshape(n, 2, n, 2).any((1, 3))
        flat = hr.ravel()
        filled = flat.copy()
        down = np.full(n * n, -1, np.int64)
        seen = np.zeros(n * n, bool)
        seen[hm.ravel()] = True
        heap = []
        for i in np.flatnonzero(ocean.ravel() & ~hm.ravel()):
            seen[i] = True
            heap.append((flat[i], int(i)))
        for i in range(n):
            for j in (i, (n - 1) * n + i, i * n, i * n + n - 1):
                if not seen[j]:
                    seen[j] = True
                    heap.append((flat[j], j))
        heapq.heapify(heap)
        nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        while heap:
            fh, i = heapq.heappop(heap)
            y, x = divmod(i, n)
            for dy, dx in nb:
                yy, xx = y + dy, x + dx
                if 0 <= yy < n and 0 <= xx < n:
                    j = yy * n + xx
                    if not seen[j]:
                        seen[j] = True
                        f = flat[j] if flat[j] > fh + 1e-6 else fh + 1e-6
                        filled[j] = f
                        down[j] = i
                        heapq.heappush(heap, (f, j))
        rain = (moist.ravel() ** 1.6) * (1 + 0.6 * (flat > MOUNTAIN))
        rain[ocean.ravel() | hm.ravel()] = 0
        acc = rain.copy()
        order = np.argsort(-filled)
        for i in order:
            d = down[i]
            if d >= 0:
                acc[d] += acc[i]
        self.racc = acc.reshape(n, n)
        thr = 26.0
        isriv = (acc >= thr) & (down >= 0)
        up = np.zeros(n * n, np.int32)
        for i in np.flatnonzero(isriv):
            if isriv[down[i]]:
                up[down[i]] += 1
        owner = np.full(n * n, -1, np.int64)
        rivers = []
        srcs = np.flatnonzero(isriv & (up == 0))
        srcs = srcs[np.argsort(-acc[srcs])]
        for s0 in srcs:
            pts = []
            i = int(s0)
            rid = len(rivers)
            join = None
            while True:
                pts.append(i)
                if owner[i] >= 0:
                    join = int(owner[i])
                    break
                owner[i] = rid
                d = down[i]
                if d < 0:
                    break
                if not isriv[d]:
                    pts.append(int(d))  # into the sea
                    break
                i = int(d)
            if len(pts) < 4:
                for p in pts[:-1]:
                    if owner[p] == rid:
                        owner[p] = -1
                continue
            rivers.append({"cells": pts, "join": join})
        # points in world tiles, wobbled by a smooth position field so shared points agree
        self.rivers = []
        for r in rivers:
            cells = np.array(r["cells"])
            y, x = np.divmod(cells, n)
            wx = (x + 0.5) * RCELL
            wy = (y + 0.5) * RCELL
            ox = fbm(wx, wy, self.seed + 50, 380, 48) * 70
            oy = fbm(wx, wy, self.seed + 51, 380, 48) * 70
            a = acc[cells]
            w = np.clip(1.6 + 1.9 * np.sqrt(a / thr), 2, 30)
            pts = np.stack([wx + ox, wy + oy, w], 1)
            pts = chaikin(pts, 3)
            self.rivers.append({"pts": pts, "join": r["join"], "len_tiles": float(len(cells) * RCELL)})
        for r in self.rivers:
            if r["join"] is not None and r["join"] < len(self.rivers):
                m = self.rivers[r["join"]]["pts"]
                e = r["pts"][-1]
                k = np.argmin(np.hypot(m[:, 0] - e[0], m[:, 1] - e[1]))
                r["pts"] = np.vstack([r["pts"], m[k:k + 1]])
        self.rivmask = np.zeros((n, n), bool)
        for r in rivers:
            for c in r["cells"]:
                self.rivmask[c // n, c % n] = True

    # ---------------------------------------------------------------- places
    def _biome_at(self, wx, wy):
        return int(self.biome[min(G - 1, int(wy // CELL)), min(G - 1, int(wx // CELL))])

    def _race(self, b, wx, wy, rng):
        hh = self.h[int(wy // CELL), int(wx // CELL)]
        near_sea = blur_lookup(self.coastnear, wx, wy)
        if b in (K_JUNGLE,) or (b == K_MARSH and rng.random() < 0.5):
            return "lizard"
        if b == K_MARSH or (near_sea and rng.random() < 0.18):
            return "frog"
        if hh > 0.3 or self.near_mountain[int(wy // CELL), int(wx // CELL)]:
            return "dwarf" if rng.random() < 0.65 else "goblin"
        if b in (K_DESERT, K_MESA, K_ASH):
            return "orc"
        if b in (K_SNOW, K_TUNDRA):
            return "kobold" if rng.random() < 0.6 else "human"
        if b == K_FOREST:
            return "elf" if rng.random() < 0.6 else "human"
        return "human" if rng.random() < 0.85 else "goblin"

    def _places(self):
        rng = np.random.default_rng(self.seed + 500)
        h = self.h
        land = (h > 0.025) & ~self.hmask
        # spread the heartland block a little so nothing is put on its edge
        hm = blur(self.hmask.astype(float), 3) > 0.01
        rivnear = blur(np.repeat(np.repeat(self.rivmask, 2, 0), 2, 1).astype(float), 3) > 0.02
        self.coastnear = blur(self.ocean.astype(float), 3) > 0.02
        self.near_mountain = blur((h > MOUNTAIN).astype(float), 5) > 0.05
        gy, gx = np.gradient(h)
        slope = np.hypot(gx, gy)
        temper = 1 - np.abs(self.temp - 0.5) * 2
        score = 1 + 1.3 * rivnear + 0.9 * self.coastnear + 0.6 * temper - slope * 60
        ok = land & ~hm & (h < MOUNTAIN - 0.04)
        self.places = []
        taken = []  # (wx, wy, spacing, kind)
        settled = ("fallen_city", "hold", "heartland")

        def free(wx, wy, r, kind):
            # the same kind keeps its own spacing; anything else just needs elbow room
            for (x, y, rr, k) in taken:
                if k == kind or (k in settled and kind in settled):
                    lim = min(r, rr) if k in settled and kind in settled else r
                else:
                    lim = 110 if (k in settled or kind in settled) else 60
                if (wx - x) ** 2 + (wy - y) ** 2 < lim * lim:
                    return False
            return True

        def pick(kind, mask, sc, count, r, extra=None):
            cand = np.argwhere(mask)
            s = sc[mask] + rng.random(len(cand)) * 0.8
            cand = cand[np.argsort(-s)]
            made = 0
            for y, x in cand:
                wx = float((x + rng.random()) * CELL)
                wy = float((y + rng.random()) * CELL)
                if not free(wx, wy, r, kind):
                    continue
                taken.append((wx, wy, r, kind))
                b = self._biome_at(wx, wy)
                p = {"kind": kind, "x": min(round(wx), WORLD - 1), "y": min(round(wy), WORLD - 1), "biome": int(b)}
                if extra:
                    p.update(extra(p, b))
                self.places.append(p)
                made += 1
                if made >= count:
                    break

        def settle(p, b):
            port = bool(self.coastnear[int(p["y"] // CELL), int(p["x"] // CELL)])
            return {"name": place_name(rng), "race": self._race(b, p["x"], p["y"], rng), "port": port}

        if self.hl:
            self.places.append({"kind": "heartland", "x": HX0 + 500, "y": HY0 + 500, "biome": int(K_GRASS),
                                "name": "The Old Heartland", "race": "human", "port": True})
            taken.append((HX0 + 500, HY0 + 500, 900, "heartland"))
        # Nobody lives in the old realms' cities and holds any more (see LORE.md): they are ruins
        # the players can retake. "race" is the people who built them.
        pick("fallen_city", ok & (score > 2.2), score, 18, 1500, settle)
        pick("hold", ok & (score > 1.4), score, 150, 620, settle)

        def lair(p, b):
            r = rng.random()
            if b in (K_SNOW, K_TUNDRA):
                beast = "wolves"
            elif b in (K_JUNGLE, K_MARSH):
                beast = "giant spiders" if r < 0.55 else "death beetles"
            elif b in (K_DESERT, K_MESA):
                beast = "a sand king"
            elif b == K_FOREST:
                beast = "giant spiders" if r < 0.4 else "wolves"
            elif b == K_ASH:
                beast = "demons"
            else:
                beast = ["wolves", "ratmen", "giant moles", "wolves"][int(r * 4)]
            return {"beast": beast}

        pick("lair", land & (h < MOUNTAIN + 0.05), rng.random(h.shape), 420, 320, lair)

        mt = ~hm & (h > MOUNTAIN - 0.03) & (h < MOUNTAIN + 0.1)

        def mine(p, b):
            nb = self.biome[max(0, int(p["y"] // CELL) - 8):int(p["y"] // CELL) + 8,
                            max(0, int(p["x"] // CELL) - 8):int(p["x"] // CELL) + 8]
            if (nb == K_ASH).any():
                ore = "adamantium"
            elif (nb == K_MESA).any() or (nb == K_DESERT).any():
                ore = "gold" if rng.random() < 0.6 else "silver"
            elif (nb == K_SNOW).any() or (nb == K_TUNDRA).any():
                ore = "iron"
            else:
                ore = ["iron", "iron", "silver", "stone", "gold"][rng.integers(5)]
            return {"name": place_name(rng) + " Delving", "ore": ore}

        pick("delving", mt, rng.random(h.shape), 340, 300, mine)

        def dungeon(p, b):
            hh = self.h[int(p["y"] // CELL), int(p["x"] // CELL)]
            hills = self.near_mountain[int(p["y"] // CELL), int(p["x"] // CELL)]
            r = rng.random()
            if b == K_ASH:
                t = "hellgate"
            elif hh > MOUNTAIN + 0.14 and r < 0.35:
                t = "dragon lair"
            elif b in (K_SNOW, K_TUNDRA) and r < 0.3 or hills and r < 0.08:
                t = "kobold warren"      # the only folk still living out here
            elif hills and r < 0.2:
                t = "goblin cave"
            elif hh > MOUNTAIN - 0.05 and r < 0.3:
                t = "deep hall"          # stairs to the dark elves' and mind-eaters' halls
            elif b in (K_FOREST, K_JUNGLE, K_MARSH) and rng.random() < 0.5:
                t = "mushroom cavern"
            elif b in (K_DESERT, K_MESA):
                t = "tomb"
            elif b in (K_SNOW, K_TUNDRA):
                t = "ice cave"
            elif hh > MOUNTAIN - 0.05:
                t = "cave"
            else:
                t = ["crypt", "barrow", "cave"][rng.integers(3)]
            return {"name": place_name(rng), "type": t}

        dmask = ~hm & (h > 0.04) & (h < MOUNTAIN + 0.25)
        dscore = rng.random(h.shape) + 1.2 * self.near_mountain
        pick("dungeon", dmask, dscore, 680, 250, dungeon)
        pick("ruin", land & (h < MOUNTAIN), rng.random(h.shape), 460, 280,
             lambda p, b: {"name": "Ruins of " + place_name(rng)})
        self._deep_places(rng, hm)
        for i, p in enumerate(self.places):
            p["id"] = i
            c, r = hex_of(p["x"], p["y"])
            p["hex"] = [int(c), int(r)]
        for isl in self.islands:
            isl["place"] = next(q["id"] for q in self.places if q.get("island") == isl["n"])

    # ---------------------------------------------------------------- roads
    def _cost(self):
        n = RG
        hr = self.h.reshape(n, 2, n, 2).mean((1, 3))
        gy, gx = np.gradient(hr)
        c = 1 + np.hypot(gx, gy) * 120
        c[hr > MOUNTAIN] = 14
        c[hr > MOUNTAIN + 0.15] = 45
        c[self.rivmask] += 7          # a bridge or a ford
        c[hr < 0] = np.inf
        hm = self.hmask.reshape(n, 2, n, 2).any((1, 3))
        c[hm] = np.inf
        return c

    def _gates(self):
        """Ways out of the old heartland: open ground on its edge that leads outside."""
        k = self.hk[0]
        gates = []
        for side, line in (("east", k[:, HSIZE - 1]), ("north", k[0, :]), ("south", k[HSIZE - 1, :]),
                           ("west", k[:, 0])):
            open_ = np.flatnonzero(np.isin(line, [K_GRASS, K_SNOW, K_DESERT, K_FOREST, K_BUILT, K_TUNDRA]))
            if len(open_) == 0:
                continue
            m = int(open_[len(open_) // 2])
            if side == "east":
                gates.append((HX0 + HSIZE + 20, HY0 + m))
            elif side == "west":
                gates.append((HX0 - 20, HY0 + m))
            elif side == "north":
                gates.append((HX0 + m, HY0 - 20))
            else:
                gates.append((HX0 + m, HY0 + HSIZE + 20))
        return gates

    def _astar(self, cost, a, b, roadcells):
        n = RG
        ay, ax = a
        by, bx = b
        start = ay * n + ax
        goal = by * n + bx
        cmin = 0.35
        g = {start: 0.0}
        prev = {}
        heap = [(0.0, start)]
        nb = [(-1, -1, 1.414), (-1, 0, 1), (-1, 1, 1.414), (0, -1, 1), (0, 1, 1), (1, -1, 1.414), (1, 0, 1),
              (1, 1, 1.414)]
        closed = set()
        while heap:
            f, i = heapq.heappop(heap)
            if i == goal:
                break
            if i in closed:
                continue
            closed.add(i)
            y, x = divmod(i, n)
            ci = cost[y, x] * (0.35 if i in roadcells else 1)
            for dy, dx, dl in nb:
                yy, xx = y + dy, x + dx
                if not (0 <= yy < n and 0 <= xx < n):
                    continue
                cj = cost[yy, xx]
                if not np.isfinite(cj):
                    continue
                j = yy * n + xx
                if j in roadcells:
                    cj *= 0.35
                ng = g[i] + (ci + cj) * 0.5 * dl
                if ng < g.get(j, 1e18):
                    g[j] = ng
                    prev[j] = i
                    hgt = math.hypot(yy - by, xx - bx) * cmin
                    heapq.heappush(heap, (ng + hgt, j))
            if len(closed) > 120000:
                return None
        if goal not in prev and goal != start:
            return None
        path = [goal]
        while path[-1] != start:
            path.append(prev[path[-1]])
        return path[::-1]

    def _cell_of(self, wx, wy, cost):
        n = RG
        x, y = int(wx // RCELL), int(wy // RCELL)
        best = None
        for r in range(0, 6):
            for yy in range(y - r, y + r + 1):
                for xx in range(x - r, x + r + 1):
                    if 0 <= yy < n and 0 <= xx < n and np.isfinite(cost[yy, xx]):
                        d = (yy - y) ** 2 + (xx - x) ** 2
                        if best is None or d < best[0]:
                            best = (d, yy, xx)
            if best:
                return best[1], best[2]
        return None

    def _roads(self):
        cost = self._cost()
        n = RG
        nodes = [p for p in self.places if p["kind"] in ("fallen_city", "hold")]
        pts = [(p["x"], p["y"]) for p in nodes]
        if self.hl:
            for gx, gy in self._gates():
                pts.append((gx, gy))
                nodes.append({"kind": "gate", "x": gx, "y": gy})
        cells = [self._cell_of(x, y, cost) for x, y in pts]
        # Prim's tree over straight distances, plus a few short loops
        N = len(pts)
        P = np.array(pts, float)
        D = np.hypot(P[:, None, 0] - P[None, :, 0], P[:, None, 1] - P[None, :, 1])
        intree = np.zeros(N, bool)
        intree[0] = True
        best = D[0].copy()
        par = np.zeros(N, int)
        edges = []
        for _ in range(N - 1):
            best[intree] = np.inf
            j = int(np.argmin(best))
            edges.append((par[j], j))
            intree[j] = True
            upd = D[j] < best
            par[upd] = j
            best = np.minimum(best, D[j])
        for i in range(N):
            order = np.argsort(D[i])
            for j in order[1:3]:
                if D[i, j] < 1300 and (i, j) not in edges and (j, i) not in edges:
                    edges.append((i, int(j)))
        edges = [e for e in edges if D[e] < 2600]
        edges.sort(key=lambda e: D[e])
        roadcells = set()
        self.roads = []
        self.unroaded = []
        for a, b in edges:
            if cells[a] is None or cells[b] is None:
                continue
            path = self._astar(cost, cells[a], cells[b], roadcells)
            if path is None:
                self.unroaded.append((a, b))
                continue
            roadcells.update(path)
            self.roads.append({"cells": path, "kind": "main"})
        # delvings and some dungeons join the nearest road by a track (the old cart ways)
        dist = np.full(n * n, np.inf)
        prev = np.full(n * n, -1, np.int64)
        heap = []
        for c in roadcells:
            dist[c] = 0
            heap.append((0.0, c))
        for p in nodes:
            c = self._cell_of(p["x"], p["y"], cost)
            if c:
                i = c[0] * n + c[1]
                dist[i] = 0
                heap.append((0.0, i))
        heapq.heapify(heap)
        while heap:
            d, i = heapq.heappop(heap)
            if d > dist[i] or d > 160:
                continue
            y, x = divmod(i, n)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if (dy or dx) and 0 <= yy < n and 0 <= xx < n and np.isfinite(cost[yy, xx]):
                        j = yy * n + xx
                        nd = d + (cost[y, x] + cost[yy, xx]) * 0.5 * (1.414 if dx and dy else 1)
                        if nd < dist[j]:
                            dist[j] = nd
                            prev[j] = i
                            heapq.heappush(heap, (nd, j))
        for p in self.places:
            if p["kind"] != "delving" and not (p["kind"] == "dungeon" and p["id"] % 3 == 0):
                continue
            c = self._cell_of(p["x"], p["y"], cost)
            if not c:
                continue
            i = c[0] * n + c[1]
            if not np.isfinite(dist[i]) or dist[i] > 110:
                continue
            path = [i]
            while prev[path[-1]] >= 0 and dist[path[-1]] > 0:
                path.append(int(prev[path[-1]]))
            if len(path) > 1:
                self.roads.append({"cells": path, "kind": "track"})
        for r in self.roads:
            cl = np.array(r["cells"])
            y, x = np.divmod(cl, n)
            wx = (x + 0.5) * RCELL
            wy = (y + 0.5) * RCELL
            ox = fbm(wx, wy, self.seed + 60, 300, 48) * 30
            oy = fbm(wx, wy, self.seed + 61, 300, 48) * 30
            r["pts"] = chaikin(np.stack([wx + ox, wy + oy, np.full(len(wx), 3.0 if r["kind"] == "main" else 2.0)],
                                        1), 3)

    # ---------------------------------------------------------------- sea lanes
    def _sea_lanes(self):
        """Ships: ports joined across open water (straight hops of a coarse sea grid)."""
        S = 128
        f = G // S
        sea = self.ocean.reshape(S, f, S, f).mean((1, 3)) > 0.5
        ports = [p for p in self.places if p.get("port") and p["kind"] in ("fallen_city", "hold", "heartland")]
        self.lanes = []
        if not ports:
            return
        cell = WORLD / S

        def near_sea(p):
            x, y = int(p["x"] // cell), int(p["y"] // cell)
            best = None
            for r in range(1, 8):
                for yy in range(y - r, y + r + 1):
                    for xx in range(x - r, x + r + 1):
                        if 0 <= yy < S and 0 <= xx < S and sea[yy, xx]:
                            d = (yy - y) ** 2 + (xx - x) ** 2
                            if best is None or d < best[0]:
                                best = (d, yy, xx)
                if best:
                    return best[1], best[2]
            return None

        cells = [near_sea(p) for p in ports]
        P = np.array([(p["x"], p["y"]) for p in ports], float)
        done = set()
        for i, p in enumerate(ports):
            if cells[i] is None:
                continue
            d = np.hypot(P[:, 0] - P[i, 0], P[:, 1] - P[i, 1])
            for j in np.argsort(d)[1:4]:
                j = int(j)
                if cells[j] is None or (j, i) in done or d[j] < 900 or d[j] > 5200:
                    continue
                path = bfs_path(sea, cells[i], cells[j])
                if path is None or len(path) * cell > d[j] * 2.2:
                    continue
                done.add((i, j))
                pts = np.array([((x + 0.5) * cell, (y + 0.5) * cell, 2.0) for y, x in path])
                pts = np.vstack([[P[i, 0], P[i, 1], 2.0], pts, [P[j, 0], P[j, 1], 2.0]])
                self.lanes.append({"a": ports[i]["id"], "b": ports[j]["id"], "pts": chaikin(pts, 3)})

    # ---------------------------------------------------------------- links between layers
    def _links(self):
        """Chasms from the caves down to the depths: up to two per hex region, from a hash of the
        hex, so any hex knows its own without the others. Cave mouths come from the places list."""
        hc, hr = np.meshgrid(np.arange(HCOLS), np.arange(HROWS))
        self.chasms = []
        for k in range(2):
            a = rand01(hc * 7 + k, hr * 13 - k, self.seed + 70) * 2 * np.pi
            d = np.sqrt(rand01(hc * 5 - k, hr * 11 + k, self.seed + 71)) * HEX * 0.6
            on = rand01(hc + k * 99, hr, self.seed + 72) < 0.35
            for y, x in np.argwhere(on):
                cx, cy = hex_center(x, y)
                wx = int(cx + np.cos(a[y, x]) * d[y, x])
                wy = int(cy + np.sin(a[y, x]) * d[y, x])
                if self.hl and HX0 - 40 < wx < HX0 + HSIZE + 40 and HY0 - 40 < wy < HY0 + HSIZE + 40:
                    continue
                self.chasms.append((wx, wy))

    # ---------------------------------------------------------------- one region's tiles
    def region(self, rx, ry, layers=True):
        """A 256 x 256 square of tiles at (rx * 256, ry * 256) (for wide pictures)."""
        return self.window(rx * REGION, ry * REGION, REGION, layers)

    def hex_region(self, col, row, layers=True):
        """One hex region: the square tiles of its bounding box (320 x 320), plus 'inside', a mask of
        the tiles whose nearest hex centre is this one. 'origin' is the box's world tile corner."""
        cx, cy = hex_center(col, row)
        x0, y0 = int(math.floor(cx - HEX)), int(math.floor(cy - HEX))
        n = int(2 * HEX)
        res = self.window(x0, y0, n, layers)
        c = np.arange(n) + 0.5
        wx, wy = np.meshgrid(x0 + c, y0 + c)
        hc, hr = hex_of(wx, wy)
        res["inside"] = (hc == col) & (hr == row)
        res["origin"] = (x0, y0)
        return res

    def window(self, wx0, wy0, size, layers=True, pad=48):
        """Tile kinds of the square of tiles from world (wx0, wy0), size across:
        dict of z -> uint8 [size, size], plus 'height', 'mouths' and 'chasms' (window coordinates)."""
        x0, y0 = wx0 - pad, wy0 - pad
        n = size + 2 * pad
        c = np.arange(n) + 0.5
        wx, wy = np.meshgrid(x0 + c, y0 + c)
        s = self.seed
        h = self.height(wx, wy, 4)
        t = self.sample(self.temp, wx, wy) + fbm(wx, wy, s + 80, 120, 8) * 0.1
        m = self.sample(self.moist, wx, wy) + fbm(wx, wy, s + 81, 120, 8) * 0.12
        g = self.heartland_blend(self.classify(h, t, m, self.ash(wx, wy)), wx, wy, 4)
        # trees and plants
        tn = fbm(wx, wy, s + 82, 40, 4) * 3 + rand01(np.floor(wx).astype(np.int64), np.floor(wy).astype(np.int64),
                                                        s + 83) * 0.9
        dens = {K_FOREST: 0.75, K_JUNGLE: 0.95, K_GRASS: -0.25, K_TUNDRA: 0.0, K_MARSH: -0.1}
        trees = np.zeros_like(g, dtype=bool)
        for kk, dv in dens.items():
            trees |= (g == kk) & (tn + dv > 1.05)
        ground = g.copy()
        ground[g == K_FOREST] = K_GRASS
        ground[trees & (g != K_TUNDRA) & (g != K_JUNGLE)] = K_FOREST
        ground[(g == K_JUNGLE) & ~trees] = K_GRASS
        ground[(g == K_TUNDRA) & ~trees] = K_SNOW
        # swamps: pools of black water among the reeds and drowned trees
        pools = fbm(wx, wy, s + 86, 36, 4) * 2.6 + rand01(np.floor(wx).astype(np.int64), np.floor(wy).astype(np.int64),
                                                           s + 87) * 0.3 > 0.42
        ground[(g == K_MARSH) & pools & ~trees] = K_SWAMPW
        mesa_ore = (g == K_MESA) & (rand01(np.floor(wx).astype(np.int64), np.floor(wy).astype(np.int64), s + 84) < 0.004)
        ground[mesa_ore] = K_ORE
        # rivers carve through everything but the sea
        riv = np.zeros_like(g, dtype=bool)
        bank = np.zeros_like(g, dtype=bool)
        wob = 1 + fbm(wx, wy, s + 85, 60, 8) * 0.8
        for r in self.rivers:
            draw_line(r["pts"], x0, y0, n, riv, bank, wob, 1.0, 1.6)
        ground[bank & (ground != K_WATER) & (ground != K_DEEP) & (ground != K_ROCK)] = K_SAND
        ground[bank & (g == K_ROCK)] = K_SHORE
        ground[riv & (ground != K_DEEP)] = K_RIVER
        h = np.where(riv, np.minimum(h, -0.03), h)
        # places
        rng_for = lambda p: np.random.default_rng((self.seed * 1000003 + p["id"] * 7919) & 0xFFFFFFFF)
        near = [p for p in self.places if x0 - 120 < p["x"] < x0 + n + 120 and y0 - 120 < p["y"] < y0 + n + 120]
        for p in near:
            if p["kind"] in ("fallen_city", "hold"):
                stamp_settlement(ground, p, x0, y0, rng_for(p))
            elif p["kind"] == "ruin":
                stamp_ruin(ground, p, x0, y0, rng_for(p))
            elif p["kind"] == "lair":
                stamp_lair(ground, p, x0, y0, rng_for(p))
        road = np.zeros_like(g, dtype=bool)
        dummy = np.zeros_like(g, dtype=bool)
        one = np.ones_like(h)
        for r in self.roads:
            draw_line(r["pts"], x0, y0, n, road, dummy, one, 1.0, 0)
        ground[road & ((ground == K_RIVER) | (ground == K_WATER))] = K_BRIDGE
        ground[road & ~np.isin(ground, [K_BRIDGE, K_DEEP, K_HOUSE, K_WALL])] = K_ROAD
        mouths = []
        for p in near:
            if p["kind"] in ("dungeon", "delving"):
                mouths.append(stamp_mouth(ground, p, x0, y0, rng_for(p)))
        out = {"height": h, 1: ground}
        if layers:
            out[2], out[4] = self._underground(wx, wy, ground, g, h, x0, y0, n, mouths)
            out[3] = np.where(np.isin(ground, [K_ROCK, K_ORE]), K_PEAK, K_SKY).astype(np.uint8)
            sk, foam = self.sky_tiles(wx, wy, 4)
            out[3][sk > 0] = sk[sk > 0]
            ground[foam & np.isin(ground, [K_WATER, K_DEEP])] = K_FALLS
        # today's hand-made map wins inside the heartland, on every layer
        if self.hl:
            hx0, hy0 = HX0 - x0, HY0 - y0
            a0, a1 = max(0, hx0), min(n, hx0 + HSIZE)
            b0, b1 = max(0, hy0), min(n, hy0 + HSIZE)
            if a0 < a1 and b0 < b1:
                for z in (1, 2, 3, 4):
                    if z in out:
                        out[z][b0:b1, a0:a1] = self.hk[z - 1][b0 - hy0:b1 - hy0, a0 - hx0:a1 - hx0]
        crop = slice(pad, pad + size)
        res = {k: v[crop, crop] for k, v in out.items()}
        res["mouths"] = [(mx - pad, my - pad, kind, pid) for mx, my, kind, pid in mouths
                         if 0 <= mx - pad < size and 0 <= my - pad < size]
        res["chasms"] = [(cx - wx0, cy - wy0) for cx, cy in self.chasms
                         if wx0 <= cx < wx0 + size and wy0 <= cy < wy0 + size]
        return res

    def caves_field(self, wx, wy, ground, g, h, min_wl=8, widen=1.0):
        """The caves layer from the noise alone (no places): tunnels, halls, lakes, flooded passages,
        lava, mushroom caverns. widen > 1 thickens the thin tunnels so a whole-world picture shows them."""
        s = self.seed
        system = smoothstep(-0.05, 0.3, fbm(wx, wy, s + 20, 1500, 200) * 2.6) + (h > MOUNTAIN) * 0.2
        tun = np.abs(fbm(wx, wy, s + 21, 150, min_wl)) < (0.008 + 0.022 * system) * widen
        cav = fbm(wx, wy, s + 22, 260, min_wl) * 2.6 > 0.7 - 0.18 * system
        open_ = tun | cav
        caves = np.where(open_, K_TUNNEL, K_CAVEFLOOR).astype(np.uint8)
        wet = fbm(wx, wy, s + 23, 420, max(min_wl, 16)) * 2.6 > 0.35
        caves[open_ & wet] = K_WATER
        caves[open_ & np.isin(ground, [K_DEEP, K_WATER, K_RIVER])] = K_DEEP  # under water: flooded
        hot = self.ash(wx, wy)
        caves[open_ & hot & (fbm(wx, wy, s + 24, 200, min_wl) > 0.02)] = K_LAVA
        shroom = (np.isin(g, [K_FOREST, K_JUNGLE, K_MARSH])) & cav & ~wet
        caves[shroom] = K_MUSHROOM
        return caves

    def depths_field(self, wx, wy, min_wl=8, widen=1.0):
        """The depths (the Deep): wide halls of hellfloor, rock walls, lava rivers and lakes, dead grass,
        and lava seas under the volcanoes."""
        s = self.seed
        depths = np.full(np.shape(wx), K_ASH, np.uint8)
        rock = (fbm(wx, wy, s + 30, 220, min_wl) * 2.6 < -0.5) | (fbm(wx, wy, s + 31, 1500, 100) * 2.6 < -0.55)
        depths[rock] = K_ROCK
        lava = (np.abs(fbm(wx, wy, s + 32, 700, max(min_wl, 16))) < 0.008 * min(widen, 1.6)) | \
            (fbm(wx, wy, s + 33, 300, max(min_wl, 16)) * 2.6 > 0.95)
        sea = np.zeros(np.shape(wx), bool)
        for vx, vy, r in self.volcanoes:   # a lava sea under each volcano
            sea |= np.hypot(wx - vx, wy - vy) < r * 1.3 * (1 + fbm(wx, wy, s + 35, 200, max(min_wl, 16)) * 1.2)
        depths[(lava | sea) & ~rock] = K_LAVA
        depths[sea] = K_LAVA
        depths[(fbm(wx, wy, s + 34, 200, min_wl) * 2.6 > 0.75) & (depths == K_ASH)] = K_DEADGRASS
        return depths

    def dungeon(self, p):
        """The layout of a dungeon or delving place (kept, as it is asked for again and again)."""
        import dungeons
        if not hasattr(self, "_dcache"):
            self._dcache = {}
        if p["id"] not in self._dcache:
            self._dcache[p["id"]] = dungeons.layout(p, self.seed)
        return self._dcache[p["id"]]

    def _underground(self, wx, wy, ground, g, h, x0, y0, n, mouths):
        caves = self.caves_field(wx, wy, ground, g, h)
        depths = self.depths_field(wx, wy)
        yy, xx = np.mgrid[0:n, 0:n]
        near = [p for p in self.places if p.get("z") in (2, 4) and x0 - 400 < p["x"] < x0 + n + 400
                and y0 - 400 < p["y"] < y0 + n + 400]
        for p in near:
            px, py = p["x"] - x0, p["y"] - y0
            d = np.hypot(xx - px, yy - py)
            if p["kind"] == "underhall":
                stamp_underhall(caves, p, d, xx, yy, px, py)
            elif p["kind"] == "demon keep":
                stamp_keep(depths, d, xx, yy, px, py)
            elif p["kind"] == "the wound":
                wob = 1 + fbm(xx + x0, yy + y0, self.seed + 36, 60, 8) * 0.8
                depths[d < 180 * wob] = K_LAVA
                depths[(d < 46 * wob) & (d >= 26)] = K_ASH
                depths[d < 26] = K_CHASM
        # every cave mouth opens onto its dungeon's first floor, carved into the caves right below it,
        # and the dungeon is joined to the nearest cave tunnel
        for mx, my, kind, pid in mouths:
            L = self.dungeon(self.places[pid])
            grid, marks = L["floors"][0]
            S = grid.shape[0]
            oy, ox = my - (S - 4), mx - S // 2          # the entrance sits under the mouth
            ya, yb, xa, xb = max(0, oy), min(n, oy + S), max(0, ox), min(n, ox + S)
            if ya < yb and xa < xb:
                sub = grid[ya - oy:yb - oy, xa - ox:xb - ox]
                tgt = caves[ya:yb, xa:xb]
                tgt[sub != K_CAVEFLOOR] = sub[sub != K_CAVEFLOOR]
            d = np.hypot(xx - mx, yy - my)
            far = (caves == K_TUNNEL) & (d >= S * 0.8) & (d < S * 0.8 + 120)
            if far.any():
                ty, tx = np.unravel_index(np.argmin(np.where(far, d, 1e9)), d.shape)
                carve_line(caves, mx, my, tx, ty, 2)
            if kind == "hellgate":   # straight down to the depths as well
                caves[(d < 3)] = K_CHASM
                depths[(d < 9) & (depths != K_LAVA)] = K_ASH
                depths[(d < 2)] = K_STAIRSUP
            caves[(np.abs(xx - mx) <= 1) & (np.abs(yy - my) <= 1)] = K_STAIRSUP
        for cx, cy in self.chasms:
            mx, my = cx - x0, cy - y0
            if -20 <= mx < n + 20 and -20 <= my < n + 20:
                d = np.hypot(xx - mx, yy - my)
                caves[(d < 9) & (caves == K_CAVEFLOOR)] = K_TUNNEL
                caves[d < 3.5] = K_CHASM
                depths[(d < 10) & (depths != K_LAVA)] = K_ASH
                depths[d < 2] = K_STAIRSUP
        return caves, depths

    def hex_land(self):
        """Per hex region, the share of its coarse cells that are land (rows x cols)."""
        hc, hr = hex_of(self.cwx, self.cwy)
        ok = (hc >= 0) & (hc < HCOLS) & (hr >= 0) & (hr < HROWS)
        idx = hr[ok] * HCOLS + hc[ok]
        tot = np.bincount(idx, minlength=HCOLS * HROWS)
        land = np.bincount(idx, weights=(self.h[ok] >= 0), minlength=HCOLS * HROWS)
        return (land / np.maximum(tot, 1)).reshape(HROWS, HCOLS) > 0.05

    # ---------------------------------------------------------------- summary
    def summary(self):
        kinds = {}
        for p in self.places:
            key = p.get("type", p["kind"])
            kinds[key] = kinds.get(key, 0) + 1
        land = float((self.h >= 0).mean())
        return {
            "seed": self.seed, "heartland": self.hl, "regions": NREG * NREG, "region_tiles": REGION,
            "world_tiles": WORLD, "land_share": round(land, 3),
            "hex_regions": HCOLS * HROWS, "land_hexes": int(self.hex_land().sum()),
            "land_regions": int(round(land * NREG * NREG)),
            "mountain_share": round(float((self.h > MOUNTAIN).mean()), 3),
            "rivers": len(self.rivers), "roads": len([r for r in self.roads if r["kind"] == "main"]),
            "tracks": len([r for r in self.roads if r["kind"] == "track"]), "sea_lanes": len(self.lanes),
            "chasms": len(self.chasms), "volcanoes": len(self.volcanoes), "places": kinds,
            "built_by": {RACES[r]: sum(1 for p in self.places if p.get("race") == r) for r in RACES},
            "lands": len(self.lands), "beast_lairs": {b: sum(1 for p in self.places if p.get("beast") == b)
                                                     for b in sorted({p.get("beast") for p in self.places} - {None})},
        }

    def fingerprint(self):
        hsh = hashlib.sha256()
        hsh.update(np.round(self.h, 6).tobytes())
        hsh.update(self.biome.tobytes())
        hsh.update(json.dumps([[p["kind"], p["x"], p["y"], p.get("name")] for p in self.places]).encode())
        for r in self.rivers + self.roads:
            hsh.update(np.round(r["pts"], 3).tobytes())
        return hsh.hexdigest()[:16]


def hex_center(col, row):
    """World tile position of a hex region's centre."""
    return (HEX_W * (np.asarray(col) + 0.5 * (np.asarray(row) & 1)) + HEX_W / 2,
            HEX_ROW * np.asarray(row) + HEX)


def hex_of(wx, wy):
    """The hex region (col, row) whose centre is nearest each world tile position."""
    x = np.asarray(wx, float) - HEX_W / 2
    y = np.asarray(wy, float) - HEX
    q = (math.sqrt(3) / 3 * x - y / 3) / HEX
    r = (2 / 3 * y) / HEX
    s_ = -q - r
    rq, rr, rs = np.round(q), np.round(r), np.round(s_)
    dq, dr, ds = np.abs(rq - q), np.abs(rr - r), np.abs(rs - s_)
    fix_q = (dq > dr) & (dq > ds)
    fix_r = ~fix_q & (dr > ds)
    rq = np.where(fix_q, -rr - rs, rq)
    rr = np.where(fix_r, -rq - rs, rr)
    rr = rr.astype(int)
    rq = rq.astype(int)
    col = rq + (rr - (rr & 1)) // 2
    return col, rr


def blur_lookup(mask, wx, wy):
    return bool(mask[min(G - 1, int(wy // CELL)), min(G - 1, int(wx // CELL))])


def chaikin(p, it):
    for _ in range(it):
        if len(p) < 3:
            return p
        q = 0.75 * p[:-1] + 0.25 * p[1:]
        r = 0.25 * p[:-1] + 0.75 * p[1:]
        mid = np.empty((2 * len(q), p.shape[1]))
        mid[0::2] = q
        mid[1::2] = r
        p = np.vstack([p[:1], mid, p[-1:]])
    return p


def bfs_path(sea, a, b):
    S = sea.shape[0]
    prev = {a: None}
    q = deque([a])
    while q:
        c = q.popleft()
        if c == b:
            break
        y, x = c
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            nb = (y + dy, x + dx)
            if 0 <= nb[0] < S and 0 <= nb[1] < S and sea[nb] and nb not in prev:
                prev[nb] = c
                q.append(nb)
    if b not in prev:
        return None
    path = [b]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    return path[::-1]


def draw_line(pts, x0, y0, n, mask, bank, wob, scale, bankw):
    """Paint a polyline of (wx, wy, width) into a window of tiles starting at (x0, y0)."""
    if len(pts) < 2:
        return
    xs = pts[:, 0] - x0
    ys = pts[:, 1] - y0
    m = 40
    if xs.max() < -m or xs.min() > n + m or ys.max() < -m or ys.min() > n + m:
        return
    for i in range(len(pts) - 1):
        ax, ay, aw = xs[i], ys[i], pts[i, 2] * scale
        bx, by, bw = xs[i + 1], ys[i + 1], pts[i + 1, 2] * scale
        r = max(aw, bw) / 2 + bankw + 2
        lo_x, hi_x = int(max(0, min(ax, bx) - r)), int(min(n, max(ax, bx) + r + 1))
        lo_y, hi_y = int(max(0, min(ay, by) - r)), int(min(n, max(ay, by) + r + 1))
        if lo_x >= hi_x or lo_y >= hi_y:
            continue
        yy, xx = np.mgrid[lo_y:hi_y, lo_x:hi_x] + 0.5
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy or 1e-9
        t = np.clip(((xx - ax) * dx + (yy - ay) * dy) / L2, 0, 1)
        d = np.hypot(xx - (ax + t * dx), yy - (ay + t * dy))
        w = (aw + (bw - aw) * t) / 2 * wob[lo_y:hi_y, lo_x:hi_x]
        mask[lo_y:hi_y, lo_x:hi_x] |= d <= np.maximum(w, 0.5)
        if bankw:
            bank[lo_y:hi_y, lo_x:hi_x] |= d <= w + bankw


def carve_line(a, x0, y0, x1, y1, r):
    nsteps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(nsteps + 1):
        x = int(round(x0 + (x1 - x0) * i / nsteps))
        y = int(round(y0 + (y1 - y0) * i / nsteps))
        sl = a[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1]
        sl[sl == K_CAVEFLOOR] = K_TUNNEL


def stamp_settlement(gr, p, x0, y0, rng):
    """A fallen city or an old hold: broken walls, roofless houses, a few halls still standing,
    the square half grassed over. Nobody lives there."""
    R = {"fallen_city": 46, "hold": 26}[p["kind"]]
    cx, cy = p["x"] - x0, p["y"] - y0
    n = gr.shape[0]
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.hypot(xx - cx, yy - cy)
    if not (d < R * 2).any():
        return
    dry = ~np.isin(gr, [K_WATER, K_DEEP, K_RIVER, K_ROCK])
    noise = rand01(xx + p["x"], yy + p["y"], p["id"] + 7)
    gr[(d < R * 0.22) & dry & (noise < 0.55)] = K_TOWN      # the old square, cracked and overgrown
    ang = np.arctan2(yy - cy, xx - cx)
    breach = np.sin(ang * (5 + p["id"] % 4) + p["id"]) > 0.55  # long fallen stretches
    ring = (d >= R) & (d < R + 2) & dry & ~breach & (noise < 0.8)
    gr[ring] = K_WALL
    gr[(d >= R) & (d < R + 4) & dry & breach & (noise < 0.25)] = K_DEADGRASS   # rubble where it fell
    if p["kind"] == "fallen_city":                           # the keep in the middle
        k = (np.abs(xx - cx) <= 7) & (np.abs(yy - cy - R * 0.45) <= 6)
        edge = k & ((np.abs(xx - cx) == 7) | (np.abs(yy - cy - R * 0.45) == 6))
        gr[k & dry] = K_HOUSE
        gr[edge & dry] = K_WALL
    nh = {"fallen_city": 70, "hold": 28}[p["kind"]]
    for _ in range(nh * 3):
        a = rng.uniform(0, 2 * np.pi)
        rr = rng.uniform(R * 0.25, R * 0.9)
        hx, hy = int(cx + np.cos(a) * rr), int(cy + np.sin(a) * rr)
        w, h = int(rng.integers(4, 8)), int(rng.integers(4, 7))
        if hx < 1 or hy < 1 or hx + w >= n - 1 or hy + h >= n - 1:
            continue
        box = gr[hy - 1:hy + h + 1, hx - 1:hx + w + 1]
        if np.isin(box, [K_HOUSE, K_WALL, K_WATER, K_DEEP, K_RIVER, K_ROCK, K_TOWN]).any():
            continue
        if rng.random() < 0.18:
            gr[hy:hy + h, hx:hx + w] = K_HOUSE               # a hall still under its roof
        else:
            gr[hy + 1:hy + h - 1, hx + 1:hx + w - 1] = K_DEADGRASS
            shell = np.zeros((h, w), bool)
            shell[0, :] = shell[-1, :] = shell[:, 0] = shell[:, -1] = True
            shell &= rng.random((h, w)) < 0.65
            gr[hy:hy + h, hx:hx + w][shell] = K_WALL
        nh -= 1
        if nh <= 0:
            break


def stamp_underhall(caves, p, d, xx, yy, px, py):
    """The old underground home of a people: a great round cavern, its ruined halls in rows, pillars."""
    R = p["r"]
    if not (d < R + 4).any():
        return
    ang = np.arctan2(yy - py, xx - px)
    caves[d < R * (1 + 0.12 * np.sin(ang * 6 + p["id"]))] = K_TUNNEL
    rnd = rand01(xx + p["x"], yy + p["y"], p["id"] + 11)
    for hy in range(-int(R * 0.6), int(R * 0.6), 16):
        for hx in range(-int(R * 0.6), int(R * 0.6), 18):
            if hx * hx + hy * hy > (R * 0.62) ** 2:
                continue
            box = (np.abs(xx - px - hx) <= 6) & (np.abs(yy - py - hy) <= 5)
            edge = box & ((np.abs(xx - px - hx) == 6) | (np.abs(yy - py - hy) == 5))
            caves[edge & (rnd < 0.7)] = K_WALL
    pil = (d < R * 0.92) & ((xx - px) % 9 == 0) & ((yy - py) % 9 == 0) & (d > R * 0.7)
    caves[pil] = K_WALL


def stamp_keep(depths, d, xx, yy, px, py):
    """A demon keep: a square of thick walls and towers in a ring of lava, one way in."""
    if not (d < 70).any():
        return
    ax, ay = np.abs(xx - px), np.abs(yy - py)
    sq = np.maximum(ax, ay)
    depths[(d < 62) & (d >= 44)] = K_LAVA                    # the moat
    depths[(sq < 34)] = K_ASH
    depths[(sq < 34) & (sq >= 30)] = K_WALL                  # the walls
    for tx in (-30, 30):
        for ty in (-30, 30):
            depths[(np.abs(xx - px - tx) < 6) & (np.abs(yy - py - ty) < 6)] = K_WALL   # towers
    depths[(ax < 10) & (ay < 10)] = K_WALL                   # the inner hall
    depths[(ax < 7) & (ay < 7)] = K_ASH
    depths[(ax < 3) & (yy > py) & (sq < 64)] = K_ASH         # the gate and its causeway over the lava


def stamp_lair(gr, p, x0, y0, rng):
    """A beast lair: trampled, bare ground and bones round a den."""
    cx, cy = int(p["x"] - x0), int(p["y"] - y0)
    n = gr.shape[0]
    ya, yb, xa, xb = max(0, cy - 9), min(n, cy + 10), max(0, cx - 9), min(n, cx + 10)
    if ya >= yb or xa >= xb:
        return
    yy, xx = np.mgrid[ya:yb, xa:xb]
    d = np.hypot(xx - cx, yy - cy)
    sub = gr[ya:yb, xa:xb]
    bare = (d < 7 * (0.8 + 0.4 * rand01(xx, yy, p["id"]))) & ~np.isin(sub, [K_WATER, K_DEEP, K_RIVER, K_ROCK])
    sub[bare] = K_DEADGRASS


def stamp_ruin(gr, p, x0, y0, rng):
    cx, cy = int(p["x"] - x0), int(p["y"] - y0)
    n = gr.shape[0]
    for _ in range(int(rng.integers(3, 7))):
        hx = cx + int(rng.integers(-10, 10))
        hy = cy + int(rng.integers(-10, 10))
        w, h = int(rng.integers(4, 9)), int(rng.integers(4, 8))
        for (ax, ay, bx, by) in ((hx, hy, hx + w, hy), (hx, hy + h, hx + w, hy + h), (hx, hy, hx, hy + h),
                                 (hx + w, hy, hx + w, hy + h)):
            for x in range(ax, bx + 1):
                for y in range(ay, by + 1):
                    if 0 <= x < n and 0 <= y < n and rng.random() < 0.6 and gr[y, x] not in (K_WATER, K_DEEP, K_RIVER):
                        gr[y, x] = K_WALL
        for x in range(hx + 1, hx + w):
            for y in range(hy + 1, hy + h):
                if 0 <= x < n and 0 <= y < n and gr[y, x] in (K_GRASS, K_FOREST, K_SAND, K_DESERT, K_SNOW):
                    gr[y, x] = K_DEADGRASS


def stamp_mouth(gr, p, x0, y0, rng):
    cx, cy = int(p["x"] - x0), int(p["y"] - y0)
    n = gr.shape[0]
    big = p.get("type") == "dragon lair"
    r = 3 if big else 1
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.hypot(xx - cx, yy - cy)
    if p["kind"] == "delving":
        yard = (d < 7) & (d >= 2) & ~np.isin(gr, [K_WATER, K_DEEP, K_RIVER, K_ROCK, K_HOUSE])
        gr[yard & (rand01(xx, yy, p["id"] + 3) < 0.6)] = K_TOWN  # the old yard, weeds through it
        lumps = (d < 16) & (gr == K_ROCK) & (rand01(xx + p["x"], yy + p["y"], p["id"]) < 0.08)
        gr[lumps] = K_ORE
    elif p.get("type") in ("kobold warren", "goblin cave"):   # a crude stake wall round the door
        ring = (d >= 6) & (d < 7.2) & ~np.isin(gr, [K_WATER, K_DEEP, K_RIVER, K_ROCK])
        gr[ring & (rand01(xx, yy, p["id"]) < 0.75)] = K_WALL
        gr[(d < 6) & np.isin(gr, [K_GRASS, K_FOREST, K_SNOW, K_SAND, K_DESERT])] = K_DEADGRASS
    elif p.get("type") in ("crypt", "barrow", "tomb"):
        ring = (np.abs(xx - cx) <= 4) & (np.abs(yy - cy) <= 4) & ((np.abs(xx - cx) == 4) | (np.abs(yy - cy) == 4))
        gr[ring & (rand01(xx, yy, p["id"]) < 0.7)] = K_WALL
    gr[(np.abs(xx - cx) <= r) & (np.abs(yy - cy) <= r)] = K_MOUTH
    return (cx, cy, p.get("type", p["kind"]), p["id"])
