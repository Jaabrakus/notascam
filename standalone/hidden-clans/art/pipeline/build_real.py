#!/usr/bin/env python3
"""Stage 2 of the "real" art style: hi-res renders -> game-size sprites.

    python3 standalone/remastered/art/pipeline/build_real.py [--sizes 128 64]

Reads art/build/renders-real/index.json (render_real.py) and writes
art/out/real<size>/<Name>/<state>_<dir>.png. Unlike the toon pipeline this keeps
the soft painted shading: each sprite pixel is the coverage-weighted average of
its block (anti-aliased colour), alpha is binary (the 3D view cuts at 50 %),
the outermost opaque ring is darkened a little and a soft dark outline is added
so figures stay readable on any ground.
"""

import argparse
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
RENDERS = os.path.join(ART, "build", "renders-real")
OUT = os.path.join(ART, "out")

COVERAGE = 0.45      # a pixel is solid when this much of its block is covered
EDGE_SHADE = 0.82    # the outermost solid ring, darkened
OUTLINE = 0.38       # outline colour = touching colour x this


def shrink(rgba, size):
    a = np.asarray(rgba, dtype=np.float32) / 255.0
    f = a.shape[0] // size
    blk = a.reshape(size, f, size, f, 4)
    al = blk[..., 3:4]
    cov = al.mean(axis=(1, 3))[..., 0]
    rgb = (blk[..., :3] * al).sum(axis=(1, 3)) / np.maximum(1e-6, al.sum(axis=(1, 3)))
    solid = cov >= COVERAGE
    out = np.zeros((size, size, 4), np.float32)
    out[..., :3] = rgb
    out[..., 3] = solid
    return out


def neighbours(mask):
    h, w = mask.shape
    pad = np.pad(mask, 1)
    return [pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))]


def finish(cell):
    solid = cell[..., 3] > 0
    nb = neighbours(solid)
    edge = solid & ~(nb[0] & nb[1] & nb[2] & nb[3])
    cell[edge, :3] *= EDGE_SHADE
    ring = ~solid & (nb[0] | nb[1] | nb[2] | nb[3])
    acc = np.zeros(cell.shape[:2] + (3,), np.float32)
    cnt = np.zeros(cell.shape[:2], np.float32)
    h, w = solid.shape
    padc = np.pad(cell[..., :3] * solid[..., None], ((1, 1), (1, 1), (0, 0)))
    pads = np.pad(solid.astype(np.float32), 1)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        acc += padc[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
        cnt += pads[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
    cell[ring, :3] = acc[ring] / cnt[ring][:, None] * OUTLINE
    cell[ring, 3] = 1.0
    return (np.clip(cell, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sizes", type=int, nargs="+", default=[128, 64])
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    path = os.path.join(RENDERS, "index.json")
    if os.path.exists(path):
        sheets = json.load(open(path))["sheets"]
    else:   # a render still running: take whatever cells are on disk
        sheets = []
        for name in sorted(os.listdir(RENDERS)):
            sdir = os.path.join(RENDERS, name)
            if not os.path.isdir(sdir):
                continue
            states = [{"name": st, "cells": [os.path.join(name, st, f) for f in sorted(os.listdir(os.path.join(sdir, st))) if f.endswith(".png")]}
                      for st in sorted(os.listdir(sdir)) if os.path.isdir(os.path.join(sdir, st))]
            if states and all(len(st["cells"]) == 4 for st in states):
                sheets.append({"name": name, "states": states})
    for sheet in sheets:
        if a.only and sheet["name"] not in a.only.split(","):
            continue
        for st in sheet["states"]:
            for rel in st["cells"]:
                im = Image.open(os.path.join(RENDERS, rel)).convert("RGBA")
                d = os.path.splitext(os.path.basename(rel))[0].split("_")[-1]
                for size in a.sizes:
                    path = os.path.join(OUT, f"real{size}", sheet["name"], f"{st['name']}_{d}.png")
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    Image.fromarray(finish(shrink(im, size))).save(path)
        print(sheet["name"])


if __name__ == "__main__":
    main()
