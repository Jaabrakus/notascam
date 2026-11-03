#!/usr/bin/env python3
"""A gargoyle's broken-off limb (StoneLimbs.dm): the original's own severed-limb picture (Blood.dmi "Arm") in the
gargoyle's stone greys instead of red, with a few darker cracks, so a gargoyle's lost limb has no blood on it.

    python3 standalone/remastered/art/enhance/stonelimb32.py [--preview out.png]

Writes game/Icons/Remastered/Items/stonelimb.dmi (state "Arm", as the bloody limb's).
"""

import argparse
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
from game_export import write_sheet  # noqa: E402

GAME = os.path.join(HERE, "..", "..", "game")
SRC = os.path.join(GAME, "Icons", "Blood.dmi")
OUT = os.path.join(GAME, "Icons", "Remastered", "Items", "stonelimb.dmi")
STONE = [(32, 32, 32), (64, 64, 64), (98, 98, 98), (128, 128, 124), (158, 156, 150)]   # Gargoyle.dmi's own greys, lit


def frame(path, state):
    im = Image.open(path)
    d = im.info["Description"]
    w, h = int(re.search(r"width = (\d+)", d).group(1)), int(re.search(r"height = (\d+)", d).group(1))
    cols, i = im.width // w, 0
    rgba = im.convert("RGBA")
    for name, body in re.findall(r'state = "([^"]*)"((?:\n\t[^\n]*)*)', d):
        n = int(re.search(r"dirs = (\d+)", body).group(1)) * int(re.search(r"frames = (\d+)", body).group(1))
        if name == state:
            x, y = (i % cols) * w, (i // cols) * h
            return np.array(rgba.crop((x, y, x + w, y + h)))
        i += n
    raise KeyError(state)


def stone(src):
    out = np.zeros_like(src)
    m = src[..., 3] > 0
    lum = src[..., :3].astype(float) @ [0.3, 0.59, 0.11]
    dark = m & (lum < 24)                                       # the original's black outline stays dark
    lit = src[..., 0].astype(float) / 255                       # the red's own shading, as stone
    lv = np.where(lit > 0.85, 3, 2)
    yy, xx = np.mgrid[0:src.shape[0], 0:src.shape[1]]
    lv[m & ((xx * 3 + yy * 5) % 7 == 0)] -= 1                    # a few cracks
    pad = np.pad(~m, 1, constant_values=True)
    lv[m & (pad[:-2, 1:-1] | pad[1:-1, :-2])] = np.maximum(lv[m & (pad[:-2, 1:-1] | pad[1:-1, :-2])], 3)   # lit top-left edge
    lv = np.clip(lv, 1, 4)
    lv[dark] = 0
    pal = np.array(STONE, np.uint8)
    out[m, :3] = pal[lv[m]]
    out[m, 3] = 255
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", default=None, help="also write the bloody and the stone limb side by side, enlarged")
    args = ap.parse_args()
    src = frame(SRC, "Arm")
    st = stone(src)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    write_sheet(OUT, [("Arm", {"dirs": 1, "frames": 1}, [st])], 32)
    print(OUT, ["Arm"])
    if args.preview:
        k = 6
        sheet = Image.new("RGBA", (2 * 32 * k, 32 * k), (62, 92, 48, 255))
        for i, c in enumerate((src, st)):
            im = Image.fromarray(c).resize((32 * k, 32 * k), Image.NEAREST)
            sheet.paste(im, (i * 32 * k, 0), im)
        sheet.save(args.preview)


if __name__ == "__main__":
    main()
