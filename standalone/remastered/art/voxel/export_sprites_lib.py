# One labelled preview sheet for a .dmi (shared by export_sprites.py and enhance2d.py): a row per
# state, its facings and frames (up to 8 frames) at 3x, with the state names.
import os
import dmi
from PIL import Image, ImageDraw

def sheet(path, out, title, Z=3):
    sts = dmi.load(path)
    if not sts: return False
    w, h = next(iter(sts.values()))['icons'][0].size
    ncol = max(st['dirs'] * min(st['frames'], 8) for st in sts.values())
    LW = 150; CW, CH = w * Z + 6, h * Z + 6
    img = Image.new('RGBA', (LW + CW * ncol, 22 + CH * len(sts)), (52, 56, 66, 255)); d = ImageDraw.Draw(img)
    d.text((6, 4), title, fill=(255, 255, 255, 255))
    for i, (name, st) in enumerate(sts.items()):
        y = 22 + i * CH
        d.text((6, y + CH // 2 - 6), (name or '(blank)')[:22], fill=(240, 236, 220, 255))
        k = 0
        for f in range(min(st['frames'], 8)):
            for di in range(st['dirs']):
                ic = st['icons'][f * st['dirs'] + di].resize((w * Z, h * Z), Image.NEAREST)
                img.alpha_composite(ic, (LW + k * CW + 3, y + 3)); k += 1
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    return True
