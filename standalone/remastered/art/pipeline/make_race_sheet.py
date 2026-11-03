#!/usr/bin/env python3
"""Race comparison sheet: each playable race's original sprite next to the new
32 px and 64 px renders (S N E W walking, plus limb-loss and sleep states).

    python3 standalone/remastered/art/pipeline/make_race_sheet.py [Race ...]

Writes art/out/races.png. Cells sit on the game's grass tile.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_comparison import GAME, NEW32, NEW64, ART, read_dmi  # noqa: E402

RACES = [  # (label, new sheet, original sheet)
    ("Orc", "Orc.dmi", "Orc.dmi"), ("Human", "Human.dmi", "Human.dmi"), ("Dwarf", "Dwarves.dmi", "Human.dmi"),
    ("Elf", "Night Elf.dmi", "Night Elf.dmi"), ("Goblin", "Goblins.dmi", "Goblins.dmi"),
    ("Kobold", "Kobold.dmi", "Kobold.dmi"), ("Lizardman", "LizardMan.dmi", "LizardMan.dmi"),
    ("Frogman", "FrogMan.dmi", "FrogMan.dmi"), ("Skeleton", "Skeleton.dmi", "Skeleton.dmi"),
    ("Zombie", "DevourerZombie.dmi", "DevourerZombie.dmi"), ("Vampire", "Vampire.dmi", "Vampire.dmi"),
]
CELL = 96  # every cell is drawn 96 px: 32 px at 3x, 64 px at 1.5x


def walk_state(states):
    for k in ("", "Normal"):
        if k in states:
            return k
    return next(iter(states))


def main():
    pick = set(sys.argv[1:])
    rows = [r for r in RACES if not pick or r[0] in pick]
    rows = [r for r in rows if os.path.exists(os.path.join(NEW32, r[1]))]
    grass = read_dmi(os.path.join(GAME, "Code", "Building", "Grounds.dmi"))["Grass"][0].resize((CELL, CELL), Image.NEAREST)
    font = ImageFont.load_default()
    cols = ["original S", "N", "E", "W", "new 32 S", "N", "E", "W", "new 64 S", "N", "E", "W", "64 no arm", "64 legless", "64 sleep", "64 extra"]
    W, H = 110 + len(cols) * (CELL + 4), 24 + len(rows) * (CELL + 6)
    sheet = Image.new("RGBA", (W, H), (28, 26, 22, 255))
    d = ImageDraw.Draw(sheet)
    for i, c in enumerate(cols):
        d.text((110 + i * (CELL + 4), 6), c, fill=(220, 210, 180), font=font)
    for r, (label, new, orig) in enumerate(rows):
        y = 24 + r * (CELL + 6)
        d.text((8, y + CELL // 2 - 6), label, fill=(240, 226, 190), font=font)
        o, n32, n64 = (read_dmi(os.path.join(GAME, "Icons", orig)), read_dmi(os.path.join(NEW32, new)),
                       read_dmi(os.path.join(NEW64, new)))
        cells = []
        for src in (o, n32, n64):
            st = src[walk_state(src)]
            cells += [st[k] if k < len(st) else None for k in range(4)]
        sleep = next((n64[k] for k in n64 if "Sleep" in k), None)
        extra = next((n64[k] for k in ("Tail", "Sneak") if k in n64), None)
        cells += [n64.get("NoRightArm", [None])[0], n64.get("NoLegs", [None])[0],
                  sleep[0] if sleep else None, extra[0] if extra else None]
        for i, c in enumerate(cells):
            x = 110 + i * (CELL + 4)
            sheet.paste(grass, (x, y))
            if c is not None:
                sheet.alpha_composite(c.resize((CELL, CELL), Image.NEAREST), (x, y))
    out = os.path.join(ART, "out", "races.png")
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
