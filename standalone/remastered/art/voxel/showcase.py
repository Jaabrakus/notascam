# A presentable lineup (python3 showcase.py OUT [yaw]): every race at the game camera, on a grass
# field with soft shadows, in two rows, with names - the sheet to show someone what they look like
import sys
import inflate2, render3, numpy as np
from PIL import Image, ImageDraw, ImageFilter
out = sys.argv[1]; yaw = float(sys.argv[2]) if len(sys.argv) > 2 else 45
RACES = ['Human', 'Dwarves', 'Night Elf', 'Orc', 'Goblins', 'Kobold', 'LizardMan',
         'FrogMan', 'Vampire', 'Demon', 'Gargoyle', 'Skeleton', 'DevourerZombie']
NAMES = {'Dwarves': 'Dwarf', 'Goblins': 'Goblin', 'LizardMan': 'Lizardman', 'FrogMan': 'Frogman', 'DevourerZombie': 'Zombie'}
W, H, per = 300, 380, 7
rows = [RACES[:per], RACES[per:]]
img = Image.new('RGBA', (W * per, H * 2 + 20), (0, 0, 0, 255))
# grass: two greens in soft noise, a little darker toward the top (distance)
rng = np.random.default_rng(3)
n = rng.random((img.height // 6 + 1, img.width // 6 + 1))
n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((img.width, img.height), Image.BICUBIC)).astype(float) / 255
g0, g1 = np.array([74, 104, 54]), np.array([92, 124, 62])
gr = g0[None, None] + (g1 - g0)[None, None] * n[..., None]
gr *= (0.86 + 0.14 * np.linspace(0, 1, img.height))[:, None, None]
img = Image.fromarray(np.dstack([gr.clip(0, 255).astype(np.uint8), np.full(n.shape, 255, np.uint8)]))
d = ImageDraw.Draw(img)
for j, row in enumerate(rows):
    x0 = (W * per - W * len(row)) // 2
    for i, rc in enumerate(row):
        M, S = inflate2.inflate(rc)
        im = render3.render(M, yaw, 37, scale=4.4, size=W + 40, stretch=1.2, foot=0.86, shadow=True, inner=True)
        img.alpha_composite(im, (x0 + i * W - 20, 10 + j * H))
        name = NAMES.get(rc, rc)
        tw = d.textlength(name)
        cx = x0 + i * W + W // 2
        d.rounded_rectangle([cx - tw / 2 - 8, j * H + H - 34, cx + tw / 2 + 8, j * H + H - 14], 6, fill=(20, 24, 20, 170))
        d.text((cx - tw / 2, j * H + H - 31), name, fill=(240, 236, 220, 255))
        print(rc, flush=True)
img.convert('RGB').save(out)
