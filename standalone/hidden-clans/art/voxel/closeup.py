# One race large: its sprite (front, side) next to the 3D (front, side, iso right, iso left).
import sys, importlib, render3, landmarks
from build3d7 import Loadout
from PIL import Image
OUT, rc = sys.argv[1], sys.argv[2]
build = importlib.import_module(sys.argv[3] if len(sys.argv) > 3 else 'build3d11')
lo = Loadout.of('cloth', race=rc, hair=None)
G, full = build.build(lo)
K = 8; C = 64 * K
img = Image.new('RGBA', (C * 6, C), (52, 56, 66, 255))
for j, c in enumerate([full['S'].resize((C, C), Image.NEAREST), render3.render(G, 0, 0, scale=K, size=C, foot=1.0, inner=True),
                       full['E'].resize((C, C), Image.NEAREST), render3.render(G, 90, 0, scale=K, size=C, foot=1.0, inner=True),
                       render3.render(G, 45, 37, scale=K * 0.9, size=C, stretch=1.2, foot=0.86, shadow=True, inner=True),
                       render3.render(G, 315, 37, scale=K * 0.9, size=C, stretch=1.2, foot=0.86, shadow=True, inner=True)]):
    if j in (0, 2):
        bg = Image.new('RGBA', (C, C), (60, 64, 76, 255)); bg.alpha_composite(c); c = bg
    img.alpha_composite(c, (j * C, 0))
img.save(OUT)
