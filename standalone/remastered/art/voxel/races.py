# Each race in the same gear: its sprite (front, side) next to the 3D model (front, side, iso).
import sys, importlib, render3, landmarks
build3d9 = importlib.import_module(sys.argv[4] if len(sys.argv) > 4 else 'build3d10')
from build3d7 import Loadout
from PIL import Image, ImageDraw, ImageFont
OUT = sys.argv[1]; RACES = sys.argv[2].split(',') if len(sys.argv) > 2 else ['Human', 'Dwarves', 'Night Elf', 'Orc', 'Goblins']
GEAR = sys.argv[3] if len(sys.argv) > 3 else 'knight'
font = ImageFont.load_default(size=18); small = ImageFont.load_default(size=14)
def loadout(rc):
    hair = 'HumanBrown' if rc in ('Human',) else None
    if GEAR == 'bare':
        lo = Loadout.of('cloth', race=rc, hair=hair); return lo
    return Loadout.of('iron', chest='plate', legs='plate', arms='plate', helmet='nasal', shield='heater', weapon='longsword', race=rc, hair=hair)
K = 4; C = 64 * K
heads = ['sprite front', '3D front', 'sprite side', '3D side', '3D iso right', '3D iso left']
img = Image.new('RGBA', (C * len(heads), 30 + (C + 40) * len(RACES)), (52, 56, 66, 255)); d = ImageDraw.Draw(img)
for j, h in enumerate(heads): d.text((j * C + 8, 6), h, fill=(200, 200, 210), font=small)
for i, rc in enumerate(RACES):
    lo = loadout(rc)
    G, full = build3d9.build(lo)
    y0 = 30 + i * (C + 40)
    d.text((8, y0 + 4), rc, fill=(240, 220, 150), font=font)
    cells = [full['S'].resize((C, C), Image.NEAREST), render3.render(G, 0, 0, scale=K, size=C, stretch=1.0, foot=1.0, inner=True),
             full['E'].resize((C, C), Image.NEAREST), render3.render(G, 90, 0, scale=K, size=C, stretch=1.0, foot=1.0, inner=True),
             render3.render(G, 45, 37, scale=K * 0.9, size=C, stretch=1.2, foot=0.86, shadow=True, inner=True),
             render3.render(G, 315, 37, scale=K * 0.9, size=C, stretch=1.2, foot=0.86, shadow=True, inner=True)]
    for j, c in enumerate(cells):
        if j in (0, 2):
            bg = Image.new('RGBA', (C, C), (60, 64, 76, 255)); bg.alpha_composite(c); c = bg
        img.alpha_composite(c, (j * C, y0 + 32))
    print(rc, flush=True)
img.save(OUT)
