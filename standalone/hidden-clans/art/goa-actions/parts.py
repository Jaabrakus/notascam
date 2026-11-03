#!/usr/bin/env python3
"""Our race sprites cut into their own body parts, each made in 8 directions (owner 11-01: "take each body part";
"if we did 8 directional sprite of each body part then we can build anything").

    python3 standalone/hidden-clans/art/goa-actions/parts.py [Sheet] [facing]      (writes parts/<Sheet>-<facing>.png)

A part is the race's own pixels in one zone of its part map (head, torso, upper arm, forearm, thigh, shin). Each limb
part is turned about its root to the 8 directions (45 degree steps): its outline (the container) is turned, then its
own colours poured back in by their place along and across the part, so a turned part keeps its own shading and
line work instead of the jagged pixels a plain rotation leaves.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from heads import labels, standing  # noqa: E402

NAMES = {0: "head", 1: "torso", 2: "R upper arm", 3: "R forearm", 4: "L upper arm", 5: "L forearm",
         6: "R thigh", 7: "R shin", 8: "L thigh", 9: "L shin"}


def axis(mask):
    """A part's long axis: root (top end) and tip, from its pixels."""
    ys, xs = np.nonzero(mask)
    p = np.stack([xs + 0.5, ys + 0.5], 1)
    c = p.mean(0)
    u = np.linalg.svd(p - c, full_matrices=False)[2][0]
    if u[1] < 0:
        u = -u                                   # pointing down the body, root at the top
    t = (p - c) @ u
    return c + u * t.min(), c + u * t.max()


def turn(part, mask, root, tip, angle):
    """The part turned so root->tip points at angle (radians, 0 = right, pi/2 = down): each output pixel takes the
    part's own pixel at the same place along and across it."""
    v = tip - root
    L = max(np.linalg.norm(v), 1e-6)
    u, n = v / L, np.array([-v[1], v[0]]) / L
    du = np.array([np.cos(angle), np.sin(angle)])
    dn = np.array([-du[1], du[0]])
    S = 48
    out = np.zeros((S, S, 4), np.uint8)
    ys, xs = np.mgrid[0:S, 0:S]
    q = np.stack([xs + 0.5 - S / 2, ys + 0.5 - S / 2], -1)          # the root at the middle
    along, across = q @ du, q @ dn
    src = root + along[..., None] * u + across[..., None] * n
    sx, sy = np.floor(src[..., 0]).astype(int), np.floor(src[..., 1]).astype(int)
    ok = (sx >= 0) & (sx < 64) & (sy >= 0) & (sy < 64)
    ok[ok] &= mask[sy[ok], sx[ok]]
    out[ok] = part[sy[ok], sx[ok]]
    return out


def main():
    sheet = sys.argv[1] if len(sys.argv) > 1 else "Human"
    facing = sys.argv[2] if len(sys.argv) > 2 else "S"
    di = "SNEW".index(facing)
    a = standing(sheet)[0][di]
    lab = labels(sheet)[facing]
    al = a[..., 3] > 0
    Z, C = 3, 48
    rows = []
    for code, name in NAMES.items():
        mask = al & (lab == code)
        if mask.sum() < 4:
            continue
        part = np.zeros_like(a)
        part[mask] = a[mask]
        cells = [part]
        if code >= 2:                              # limbs: the 8 directions
            root, tip = axis(mask)
            for k in range(8):
                cells.append(turn(part, mask, root, tip, k * np.pi / 4))
        rows.append((name, cells))
    W = 110 + 9 * (C * Z + 6)
    im = Image.new("RGB", (W, len(rows) * (64 * Z + 8) + 20), (30, 32, 38))
    dr = ImageDraw.Draw(im)
    dr.text((110, 4), f"{sheet}, {facing}: the part as drawn, then turned to right, down-right, down, down-left, left, "
                      "up-left, up, up-right", fill=(230, 230, 230))
    y = 20
    for name, cells in rows:
        dr.text((4, y + 30), name, fill=(255, 230, 140))
        x = 110
        for c in cells:
            t = Image.new("RGBA", (c.shape[1], c.shape[0]), (70, 74, 84, 255))
            t.alpha_composite(Image.fromarray(c))
            t = t.resize((c.shape[1] * Z, c.shape[0] * Z), Image.NEAREST)
            im.paste(t, (x, y))
            x += t.width + 6
        y += 64 * Z + 8
    dest = os.path.join(HERE, "parts")
    os.makedirs(dest, exist_ok=True)
    im.save(os.path.join(dest, f"{sheet}-{facing}.png"))
    print(os.path.join(dest, f"{sheet}-{facing}.png"), im.size)


if __name__ == "__main__":
    main()


def _turn_mask(mask, root, tip, angle, S=48):
    """A part's mask (its container, or one material in it) turned like turn(): True where the turned part is."""
    m = np.zeros(mask.shape + (4,), np.uint8)
    m[mask] = 255
    return turn(m, mask, root, tip, angle)[..., 3] > 0


def _smooth(mask):
    """Close the pinholes and drop the stray pixels a turn leaves (a pixel takes what most of its 8 neighbours are)."""
    p = np.pad(mask, 1)
    n = sum(p[1 + dy:1 + dy + mask.shape[0], 1 + dx:1 + dx + mask.shape[1]].astype(int)
            for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)
    return (mask & (n >= 2)) | (~mask & (n >= 5))


def pour_turned(part, root, tip, angle):
    """The part in a new direction: its outline (the container) turned and smoothed, then its own colours poured in,
    in the light from the top-left, a material at a time (skin, and cloth where the part is cloth), outline black."""
    import draw
    al = part[..., 3] > 0
    rgb = part[..., :3].astype(float) / 255
    mx, mn = rgb.max(-1), rgb.min(-1)
    outline = al & (part[..., :3].astype(int).sum(-1) < 30)
    cloth = al & ~outline & ((mx - mn) / np.maximum(mx, 1e-6) < 0.3) & (mx < 0.45)
    skin = al & ~outline & ~cloth
    box = _smooth(_turn_mask(al, root, tip, angle))
    if not box.any():
        return np.zeros((48, 48, 4), np.uint8)
    cl = _turn_mask(cloth, root, tip, angle) & box if cloth.any() else np.zeros_like(box)
    if cl.any():
        cl = _smooth(cl) & box
    out = np.zeros((48, 48, 4), np.uint8)
    skin_r = draw.ramp(part[skin]) if skin.any() else draw.darker(draw.ramp(part[cloth]), 1.6)
    cloth_r = draw.ramp(part[cloth]) if cloth.any() else skin_r
    big = np.zeros((64, 64), bool)
    big[8:56, 8:56] = box                                  # draw.py works on 64 x 64
    cbig = np.zeros((64, 64), bool)
    cbig[8:56, 8:56] = cl
    canvas = np.zeros((64, 64, 4), np.uint8)
    draw.pour(canvas, big, skin_r, [(cbig, cloth_r)])
    out[:] = canvas[8:56, 8:56]
    return out
