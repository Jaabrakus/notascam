#!/usr/bin/env python3
"""Stage 2 of the Remastered sprite pipeline: hi-res renders -> .dmi files.

    python3 standalone/remastered/art/pipeline/build_dmi.py [--sizes 32 64]

Reads art/build/renders/index.json (written by render_sprites.py) and writes
art/out/dmi<size>/<Sheet>.dmi for each requested cell size. Needs Python 3.10+,
numpy and Pillow (the same Pillow the existing sprite exporter uses).

Per cell:
  1. Nearest-neighbour downscale. Colour is the render pixel at the centre of
     each block (never an average, so every pixel stays on a toon-ramp colour).
     A pixel is opaque when >= COVERAGE of its block is opaque, which keeps thin
     shapes such as axe hafts; if the centre sample is empty, the nearest
     opaque sample supplies the colour. Alpha is binary, like the originals.
  2. One-pixel exterior outline (4-neighbour) in a darkened, desaturated
     version of the touching colour ("selective outline"), clamped to a
     near-black ceiling so silhouettes read on grass, sand and snow alike.

Sheets follow BYOND DMI v4.0: cells ordered by frame then direction
(S, N, E, W), packed left-to-right in ceil(sqrt(n)) columns, PNG chunk order
IHDR, zTXt "Description", IDAT, IEND, the same as the game's Icons/*.dmi.
"""

import argparse
import json
import math
import os
import struct
import zlib

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
RENDERS = os.path.join(ART, "build", "renders")
OUT = os.path.join(ART, "out")

COVERAGE = 0.34
OUTLINE_DARKEN = 0.30            # outline = touching colour * this
OUTLINE_MAX = np.array([46, 34, 40])  # never lighter than this (sRGB)


# --------------------------------------------------------------------------
# cell processing
# --------------------------------------------------------------------------

def downscale(rgba, size):
    src = np.asarray(rgba, dtype=np.uint8)
    f = src.shape[0] // size
    assert src.shape[0] == src.shape[1] == size * f, "render must be a multiple of the cell size"
    blocks = src.reshape(size, f, size, f, 4).transpose(0, 2, 1, 3, 4).reshape(size, size, f * f, 4)
    solid = blocks[..., 3] >= 128
    coverage = solid.mean(axis=2)
    # samples ordered by distance from the block centre
    c = (f - 1) / 2.0
    order = sorted(range(f * f), key=lambda i: ((i // f - c) ** 2 + (i % f - c) ** 2, i))
    ordered_solid = solid[..., order]
    first = np.argmax(ordered_solid, axis=2)
    pick = np.take_along_axis(blocks[..., order, :], first[..., None, None], axis=2)[:, :, 0, :]
    out = np.zeros((size, size, 4), dtype=np.uint8)
    keep = coverage >= COVERAGE
    out[keep, :3] = pick[keep, :3]
    out[keep, 3] = 255
    return out


def outline(cell):
    a = cell[..., 3] > 0
    h, w = a.shape
    rgb = cell[..., :3].astype(np.float32)
    acc = np.zeros((h, w, 3), np.float32)
    cnt = np.zeros((h, w), np.float32)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sa = np.zeros_like(a)
        sr = np.zeros_like(rgb)
        ys, yd = (slice(0, h - dy), slice(dy, h)) if dy > 0 else (slice(-dy, h), slice(0, h + dy)) if dy < 0 else (slice(0, h), slice(0, h))
        xs, xd = (slice(0, w - dx), slice(dx, w)) if dx > 0 else (slice(-dx, w), slice(0, w + dx)) if dx < 0 else (slice(0, w), slice(0, w))
        sa[yd, xd] = a[ys, xs]
        sr[yd, xd] = rgb[ys, xs]
        acc += sr * sa[..., None]
        cnt += sa
    ring = (~a) & (cnt > 0)
    out = cell.copy()
    mean = acc[ring] / cnt[ring][:, None]
    grey = mean.mean(axis=1, keepdims=True)
    col = (mean * 0.6 + grey * 0.4) * OUTLINE_DARKEN
    col = np.minimum(col, OUTLINE_MAX)
    out[ring, :3] = col.astype(np.uint8)
    out[ring, 3] = 255
    return out


def process(path, size):
    with Image.open(path) as im:
        cell = downscale(im.convert("RGBA"), size)
    return outline(cell)


# --------------------------------------------------------------------------
# DMI writing
# --------------------------------------------------------------------------

def description(size, states):
    lines = ["# BEGIN DMI", "version = 4.0", f"\twidth = {size}", f"\theight = {size}"]
    for st in states:
        lines.append(f'state = "{st["name"]}"')
        lines.append(f"\tdirs = {st['dirs']}")
        lines.append(f"\tframes = {st['frames']}")
        if st.get("delay"):
            lines.append("\tdelay = " + ",".join(str(d) for d in st["delay"]))
        if st.get("movement") is not None:
            lines.append(f"\tmovement = {st['movement']}")
        if st.get("rewind") is not None:
            lines.append(f"\trewind = {st['rewind']}")
    lines.append("# END DMI")
    return "\n".join(lines) + "\n"


def _chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_dmi(path, sheet_rgba, desc):
    """PNG with IHDR, zTXt Description, IDAT, IEND (DMI chunk order)."""
    h, w = sheet_rgba.shape[:2]
    raw = b"".join(b"\x00" + sheet_rgba[y].tobytes() for y in range(h))
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += _chunk(b"zTXt", b"Description\x00\x00" + zlib.compress(desc.encode("latin-1"), 9))
    png += _chunk(b"IDAT", zlib.compress(raw, 9))
    png += _chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(png)


def build_sheet(sheet, size):
    cells = [process(os.path.join(RENDERS, rel), size) for st in sheet["states"] for rel in st["cells"]]
    cols = math.ceil(math.sqrt(len(cells)))
    rows = math.ceil(len(cells) / cols)
    out = np.zeros((rows * size, cols * size, 4), np.uint8)
    for i, cell in enumerate(cells):
        y, x = divmod(i, cols)
        out[y * size:(y + 1) * size, x * size:(x + 1) * size] = cell
    path = os.path.join(OUT, f"dmi{size}", sheet["file"])
    write_dmi(path, out, description(size, sheet["states"]))
    return path, len(cells)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sizes", type=int, nargs="+", default=[32, 64])
    args = ap.parse_args()
    with open(os.path.join(RENDERS, "index.json")) as fh:
        index = json.load(fh)
    for size in args.sizes:
        if index["render_px"] % size:
            raise SystemExit(f"render size {index['render_px']} is not a multiple of {size}")
        for sheet in index["sheets"]:
            path, n = build_sheet(sheet, size)
            print(f"{os.path.relpath(path, ART)}: {len(sheet['states'])} states, {n} cells")


if __name__ == "__main__":
    main()
