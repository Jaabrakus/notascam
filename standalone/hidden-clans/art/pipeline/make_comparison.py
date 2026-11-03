#!/usr/bin/env python3
"""Comparison sheet: original game sprites next to the new renders.

    python3 standalone/remastered/art/pipeline/make_comparison.py

Reads the original .dmi files from standalone/remastered/game/Icons (read
only) and the new ones from art/out/dmi32 and art/out/dmi64. Writes
art/out/comparison.png. Every cell sits on the game's own grass tile so
contrast is judged in context. Columns: original 1x, original 4x (S N E W),
new 32 px at 1x, new 32 px at 4x, and the 64 px build shown at 2x (the same
on-screen size as 32 px at 4x) for the size evaluation.
"""

import os
import re

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
GAME = os.path.join(os.path.dirname(ART), "game")
NEW32 = os.path.join(ART, "out", "dmi32")
NEW64 = os.path.join(ART, "out", "dmi64")


def read_dmi(path):
    """Return {state_name: [cells...]} using frame-major, S/N/E/W order."""
    im = Image.open(path)
    desc = im.info["Description"]
    w = int(re.search(r"\twidth = (\d+)", desc).group(1))
    h = int(re.search(r"\theight = (\d+)", desc).group(1))
    sheet = im.convert("RGBA")
    cols = sheet.width // w
    states, idx = {}, 0
    for m in re.finditer(r'state = "([^"]*)"\n((?:\t.*\n)*)', desc):
        body = m.group(2)
        n = int(re.search(r"dirs = (\d+)", body).group(1)) * int(re.search(r"frames = (\d+)", body).group(1))
        cells = [sheet.crop(((i % cols) * w, (i // cols) * h, (i % cols + 1) * w, (i // cols + 1) * h))
                 for i in range(idx, idx + n)]
        states.setdefault(m.group(1), cells)
        idx += n
    return states


def stack(*layers):
    out = layers[0].copy()
    for layer in layers[1:]:
        out.alpha_composite(layer)
    return out


def main():
    orig_orc = read_dmi(os.path.join(GAME, "Icons", "Orc.dmi"))
    metal = read_dmi(os.path.join(GAME, "Icons", "MetalObjects.dmi"))
    grounds = read_dmi(os.path.join(GAME, "Code", "Building", "Grounds.dmi"))
    grass = grounds["Grass"][0]
    n32, g32 = read_dmi(os.path.join(NEW32, "Orc.dmi")), read_dmi(os.path.join(NEW32, "OrcGear.dmi"))
    n64, g64 = read_dmi(os.path.join(NEW64, "Orc.dmi")), read_dmi(os.path.join(NEW64, "OrcGear.dmi"))

    def kit(body, gear, names):
        return [stack(body[i], *[gear[n][i] for n in names]) for i in range(4)]

    rows = [
        ("Orc base body", "Orc.dmi  Normal", orig_orc["Normal"][:4], n32["Normal"][:4], n64["Normal"][:4]),
        ("Bronze Axe", "closest: MetalOrcAxe", metal["MetalOrcAxe"][:4], g32["Bronze Axe"][:4], g64["Bronze Axe"][:4]),
        ("Iron Axe", "closest: MetalOrcAxe", metal["MetalOrcAxe"][:4], g32["Iron Axe"][:4], g64["Iron Axe"][:4]),
        ("Steel Axe", "closest: Adamantium Axe", metal["Adamantium Axe"][:4], g32["Steel Axe"][:4], g64["Steel Axe"][:4]),
        ("Wooden Buckler", "closest: Metal Buckler", metal["Metal Buckler"][:4], g32["Wooden Buckler"][:4], g64["Wooden Buckler"][:4]),
        ("Iron War Helm", "closest: Metal Helmet", metal["Metal Helmet"][:4], g32["Iron War Helm"][:4], g64["Iron War Helm"][:4]),
        ("Kit on body", "Orc + axe + buckler + helmet",
         kit(orig_orc["Normal"], metal, ["MetalOrcAxe", "Metal Buckler", "Metal Helmet"]),
         kit(n32["Normal"], g32, ["Iron Axe", "Wooden Buckler", "Iron War Helm"]),
         kit(n64["Normal"], g64, ["Iron Axe", "Wooden Buckler", "Iron War Helm"])),
        ("Tier strip (S)", "bronze / iron / steel on body",
         [stack(orig_orc["Normal"][0], metal["MetalOrcAxe"][0]), stack(orig_orc["Normal"][0], metal["Adamantium Axe"][0]),
          stack(orig_orc["Normal"][0], metal["Metal Buckler"][0]), stack(orig_orc["Normal"][0], metal["Metal Helmet"][0])],
         [stack(n32["Normal"][0], g32[t][0]) for t in ("Bronze Axe", "Iron Axe", "Steel Axe")] + [stack(n32["Normal"][0], g32["Wooden Buckler"][0])],
         [stack(n64["Normal"][0], g64[t][0]) for t in ("Bronze Axe", "Iron Axe", "Steel Axe")] + [stack(n64["Normal"][0], g64["Wooden Buckler"][0])]),
    ]

    pad, label_w, big = 10, 210, 128
    grass2 = grass.resize((64, 64), Image.NEAREST)
    grass4 = grass.resize((big, big), Image.NEAREST)
    col_x = [label_w, label_w + 4 * 34 + pad, label_w + 4 * 34 + pad + 4 * (big + 4) + pad * 3]
    col_x += [col_x[2] + 4 * 34 + pad, col_x[2] + 4 * 34 + pad + 4 * (big + 4) + pad * 3]
    width = col_x[4] + 4 * (big + 4) + pad
    head_h = 70
    row_h = big + 2 * pad
    sheet = Image.new("RGBA", (width, head_h + row_h * len(rows) + 40), (24, 22, 26, 255))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=15)
        small = ImageFont.load_default(size=12)
    except TypeError:
        font = small = ImageFont.load_default()
    d.text((pad, 12), "Dungeon Master Remastered: original vs prototype 3D-rendered sprites (S, N, E, W; frame 0)",
           fill=(240, 230, 200), font=font)
    for x, title in zip(col_x, ["Original 1x", "Original 4x", "New 32 px 1x", "New 32 px 4x", "New 64 px at 2x"]):
        d.text((x, 44), title, fill=(200, 190, 160), font=small)
    d.line((col_x[2] - pad * 2, 40, col_x[2] - pad * 2, sheet.height - 30), fill=(90, 80, 70), width=2)
    d.line((col_x[4] - pad * 2, 40, col_x[4] - pad * 2, sheet.height - 30), fill=(70, 70, 90), width=1)

    for r, (name, note, orig, new32, new64) in enumerate(rows):
        y = head_h + r * row_h + pad
        d.text((pad, y + 40), name, fill=(240, 230, 200), font=font)
        d.text((pad, y + 62), note, fill=(150, 145, 130), font=small)
        for i in range(4):
            for cells, x0 in ((orig, col_x[0]), (new32, col_x[2])):
                t = grass.copy()
                t.alpha_composite(cells[i])
                sheet.alpha_composite(t, (x0 + i * 34, y + big - 32))
            for cells, x0, scale_bg in ((orig, col_x[1], grass4), (new32, col_x[3], grass4)):
                t = scale_bg.copy()
                t.alpha_composite(cells[i].resize((big, big), Image.NEAREST))
                sheet.alpha_composite(t, (x0 + i * (big + 4), y))
            t = Image.new("RGBA", (64, 64))
            for gy in (0, 32):
                for gx in (0, 32):
                    t.alpha_composite(grass, (gx, gy))
            t.alpha_composite(new64[i])
            sheet.alpha_composite(t.resize((big, big), Image.NEAREST), (col_x[4] + i * (big + 4), y))
    d.text((pad, sheet.height - 26),
           "Original art: the game's own Icons/*.dmi. New art: procedural Blender models, art/pipeline. "
           "64 px column is for the size decision only; the game today is 32 px per tile.",
           fill=(130, 125, 115), font=small)
    out = os.path.join(ART, "out", "comparison.png")
    sheet.save(out)
    print(os.path.relpath(out, ART), sheet.size)


if __name__ == "__main__":
    main()
