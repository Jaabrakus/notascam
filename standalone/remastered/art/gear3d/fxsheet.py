# The magic weapons' own 2D pixel effects, for the 3D pieces (python3 fxsheet.py OUT [OUT2 ...]): each staff's and
# enchanted weapon's effect frames as wearables64.magic_layers draws them (a staff's glow, sparkles, flames, wisps;
# a blade's runes, flames, frost, bolts, smoke, stars, without the glow round it), drawn round the weapon held
# straight up, so the page can lay them along the 3D piece
# as it turns and swings (magicfx.js). Stored as the game stores its effect sheet (game_export.fx_cells): light to
# add, colour times opacity.
#
# Writes OUT/g3fx-<style>.png (the FRAMES frames side by side) and OUT/g3fx.json: per style the cell's size, the
# weapon's origin in it (the top of the grip, where the 3D piece's frame starts; x across the piece, y down it) and
# the frames' count and time.
import json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'enhance'))
import wearables64 as w   # noqa: E402

HAND = np.array([32.0, 62.0])   # the fist, low in the cell, the weapon straight up from it


class Upright:
    """A template holding the weapon straight up from the fist, in front of an empty body."""
    def __init__(self):
        self.ref = {d: {'body': np.zeros((64, 64), bool)} for d in 'SNEW'}

    def grip(self, d):
        return HAND.copy(), np.array([0.0, -1.0]), np.array([1.0, 0.0]), False


def frames(style):
    """The effect's frames, as light to add, and the weapon's origin (the top of its grip) in the 64 px cell. An
    enchanted weapon's effect comes without its glow (the aura round the blade, user 2026-10-25: "the effects good
    the aura no"): only its runes, flames, frost, bolts, smoke or stars."""
    T = Upright()
    glow = w.glow
    if style not in w.STAFFS:
        w.glow = lambda src, colour, strength: np.zeros((64, 64, 4), np.uint8)
    try:
        _, fxs = w.magic_layers(T, 'S', style)
    finally:
        w.glow = glow
    base = None if style in w.STAFFS else w.MAGIC_BASE[style][0]
    o = HAND + np.array([0.0, -1.0]) * (w.GRIP_SHIFT.get(base, 0.0) if base else 0.0)
    out = []
    for fx in fxs:
        c = np.zeros_like(fx)
        lit = fx[..., 3] > 0
        c[lit, :3] = (fx[lit, :3].astype(np.uint16) * fx[lit, 3:4] // 255).astype(np.uint8)
        c[lit, 3] = 255
        out.append(c)
    return out, o


def main(outs):
    meta = {}
    sheets = {}
    for style in w.MAGIC:
        fr, o = frames(style)
        on = np.any([f[..., 3] > 0 for f in fr], axis=0)
        ys, xs = np.nonzero(on)
        x0, x1, y0, y1 = max(0, xs.min() - 1), min(64, xs.max() + 2), max(0, ys.min() - 1), min(64, ys.max() + 2)
        # odd sizes: the page filters a texture whose sides are powers of two smoothly; these stay hard pixels
        if (x1 - x0) % 2 == 0: x1 = x1 + 1 if x1 < 64 else x1; x0 = x0 - 1 if (x1 - x0) % 2 == 0 and x0 > 0 else x0
        if (y1 - y0) % 2 == 0: y1 = y1 + 1 if y1 < 64 else y1; y0 = y0 - 1 if (y1 - y0) % 2 == 0 and y0 > 0 else y0
        x0, x1, y0, y1 = int(x0), int(x1), int(y0), int(y1)
        cw, ch = x1 - x0, y1 - y0
        strip = np.zeros((ch, cw * len(fr), 4), np.uint8)
        for i, f in enumerate(fr):
            strip[:, i * cw:(i + 1) * cw] = f[y0:y1, x0:x1]
        sheets[style] = strip
        meta[style] = dict(w=cw, h=ch, ox=round(float(o[0] - x0), 2), oy=round(float(o[1] - y0), 2), frames=len(fr), dt=0.1)
        print(f'{style:14s} {cw}x{ch} origin ({meta[style]["ox"]}, {meta[style]["oy"]})', flush=True)
    for out in outs:
        os.makedirs(out, exist_ok=True)
        for style, strip in sheets.items():
            Image.fromarray(strip).save(os.path.join(out, f"g3fx-{style.replace(' ', '_')}.png"))
        json.dump(meta, open(os.path.join(out, 'g3fx.json'), 'w'), separators=(',', ':'))
        print(os.path.join(out, 'g3fx.json'))


if __name__ == '__main__':
    main(sys.argv[1:])
