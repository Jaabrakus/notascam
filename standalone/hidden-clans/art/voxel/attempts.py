# The race attempts side by side, unarmed (both arms hanging as in the sprite): sprite, then each
# attempt's front and iso views.
import sys, importlib, render3
from build3d7 import Loadout
from PIL import Image, ImageDraw, ImageFont
OUT, rc = sys.argv[1], sys.argv[2]
font = ImageFont.load_default(size=20)
mods = [('A: designed parts', 'build3d10'), ('B: built from sprite rows', 'build3d11'), ('C: rounded, trimmed to sprite', 'build3d12')]
K = 6; C = 64 * K
img = Image.new('RGBA', (C * (1 + 2 * len(mods)), C + 40), (52, 56, 66, 255)); d = ImageDraw.Draw(img)
lo = Loadout.of('cloth', race=rc, hair=None)
G0, full = importlib.import_module('build3d12').build(Loadout.of('cloth', race=rc, hair=None))
bg = Image.new('RGBA', (C, C), (60, 64, 76, 255)); bg.alpha_composite(full['S'].resize((C, C), Image.NEAREST)); img.alpha_composite(bg, (0, 40))
d.text((8, 8), rc + ' base sprite', fill=(240, 220, 150), font=font)
for i, (name, mod) in enumerate(mods):
    G, _ = importlib.import_module(mod).build(Loadout.of('cloth', race=rc, hair=None))
    x0 = C * (1 + 2 * i)
    img.alpha_composite(render3.render(G, 0, 0, scale=K, size=C, foot=1.0), (x0, 40))
    img.alpha_composite(render3.render(G, 45, 37, scale=K * 0.9, size=C, stretch=1.2, foot=0.86, shadow=True), (x0 + C, 40))
    d.text((x0 + 8, 8), name, fill=(240, 220, 150), font=font)
img.save(OUT)
