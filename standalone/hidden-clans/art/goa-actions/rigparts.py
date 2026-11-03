#!/usr/bin/env python3
"""The approved Human rig's own parts (rig/, cut and approved 2026-10-31: whole head, torso, pelvis, upper arm, forearm,
hand, thigh, shin, foot per facing), each limb part made in 8 directions (owner 11-01: "take each body part", "8
directional sprite of each body part then we can build anything").

    python3 standalone/hidden-clans/art/goa-actions/rigparts.py [S|N|E|W]      (writes parts/rig-Human-<facing>.png)

A limb part's outline (its container) turns about its joint to the 8 directions; its own colours are then poured back
into the turned shape (parts.pour_turned), skin and cloth each from the part's own tones, light from the top-left.
"""
import base64
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parts import pour_turned  # noqa: E402

s = open(os.path.join(HERE, "data.js")).read()
DATA = json.loads(s[s.index("{"):].rstrip().rstrip(";"))
IMG = {k: np.asarray(Image.open(io.BytesIO(base64.b64decode(v.split(",", 1)[1]))).convert("RGBA"))
       for k, v in DATA["images"].items()}
LIMBS = [("rightUpperArm", "arms", "right", 0, 1), ("rightForearm", "arms", "right", 1, 2),
         ("leftUpperArm", "arms", "left", 0, 1), ("leftForearm", "arms", "left", 1, 2),
         ("rightThigh", "legs", "right", 0, 1), ("rightShin", "legs", "right", 1, 2),
         ("leftThigh", "legs", "left", 0, 1), ("leftShin", "legs", "left", 1, 2)]


def main():
    facing = sys.argv[1] if len(sys.argv) > 1 else "S"
    view = DATA["views"]["SNEW".index(facing)]
    Z, C = 3, 48
    rows = []
    for name in ("head", "torso", "pelvis"):
        rows.append((name, [IMG[view["parts"][name]]]))
    for name, group, side, i0, i1 in LIMBS:
        part = IMG[view["parts"][name]]
        src = (view.get("partSource") or {}).get(name)
        j = view[group][side]
        root, tip = (np.array(src[0]), np.array(src[1])) if src else (np.array(j[i0], float), np.array(j[i1], float))
        cells = [part] + [pour_turned(part, root, tip, k * np.pi / 4) for k in range(8)]
        rows.append((name, cells))
    for name in ("rightHand", "leftHand", "rightFoot", "leftFoot"):
        rows.append((name, [IMG[view["parts"][name]]]))
    W = 120 + 9 * (C * Z + 6)
    im = Image.new("RGB", (W, len(rows) * (64 * Z + 8) + 20), (30, 32, 38))
    dr = ImageDraw.Draw(im)
    dr.text((120, 4), f"Approved Human rig, {facing}: the part as cut, then poured into its turned shape: right, down-right, down, down-left, "
                      "left, up-left, up, up-right", fill=(230, 230, 230))
    y = 20
    for name, cells in rows:
        dr.text((4, y + 30), name, fill=(255, 230, 140))
        x = 120
        for c in cells:
            t = Image.new("RGBA", (c.shape[1], c.shape[0]), (70, 74, 84, 255))
            t.alpha_composite(Image.fromarray(c))
            t = t.resize((c.shape[1] * Z, c.shape[0] * Z), Image.NEAREST)
            im.paste(t, (x, y))
            x += t.width + 6
        y += 64 * Z + 8
    os.makedirs(os.path.join(HERE, "parts"), exist_ok=True)
    out = os.path.join(HERE, "parts", f"rig-Human-{facing}.png")
    im.save(out)
    print(out, im.size)


if __name__ == "__main__":
    main()
