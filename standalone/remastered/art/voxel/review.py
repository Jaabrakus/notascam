# Big renders of a few gear sets next to the pass-6 knight, to judge the look.
import sys, importlib, build3d6, render3
from build3d7 import Loadout
build3d7 = importlib.import_module(sys.argv[2] if len(sys.argv) > 2 else "build3d8")
from PIL import Image, ImageDraw, ImageFont
OUT = sys.argv[1] if len(sys.argv) > 1 else '/private/tmp/claude-501/-Users-kiwimango-Downloads-Dungeon-Master-master/3521b5af-e9ad-4d42-b4d4-c9798a77902e/scratchpad/vox/review.png'
font = ImageFont.load_default(size=18)
sets = [('pass 6 knight', None),
        ('iron knight', Loadout.of('iron', chest='plate', legs='plate', arms='plate', helmet='nasal', shield='heater', weapon='longsword')),
        ('gold scale, horned, axe', Loadout.of('gold', chest='scale', legs='mail', arms='mail', helmet='horned', shield='round', weapon='battle axe')),
        ('iron tabard, great helm', Loadout.of('iron', chest='tabard', legs='mail', arms='mail', helmet='great helm', shield='kite', weapon='mace')),
        ('leather', Loadout.of('leather', chest='leather', legs='leather', arms='leather', helmet='kettle', shield='round')),
        ('hell lamellar, winged', Loadout.of('hell', chest='lamellar', legs='scale', arms='plate', helmet='winged', shield='tower', weapon='warhammer'))]
cell = 460
img = Image.new('RGBA', (len(sets) * cell, cell + 30), (52, 56, 66, 255)); d = ImageDraw.Draw(img)
for i, (name, lo) in enumerate(sets):
    G = build3d6.build_knight()[0] if lo is None else build3d7.build(lo)[0]
    img.alpha_composite(render3.render(G, 45, 37, scale=6, size=cell, stretch=1.2, foot=0.8, shadow=True), (i * cell, 30))
    d.text((i * cell + 10, 6), name, fill=(240, 220, 150), font=font)
img.save(OUT)
