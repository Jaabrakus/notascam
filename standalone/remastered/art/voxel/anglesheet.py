# Every race from eight yaws at the game's pitch (python3 anglesheet.py OUT [head]): rows are races,
# columns yaw 0..315, labelled - one sheet to share. 'head' crops to the head like angles.py.
import sys
import inflate2, render3, numpy as np
from PIL import Image, ImageDraw
out = sys.argv[1]; head = len(sys.argv) > 2 and sys.argv[2] == 'head'
RACES = ['Human', 'Dwarves', 'Night Elf', 'Orc', 'Goblins', 'Kobold', 'LizardMan',
         'FrogMan', 'Vampire', 'Demon', 'Gargoyle', 'Skeleton', 'DevourerZombie']
NAMES = {'Dwarves': 'Dwarf', 'Goblins': 'Goblin', 'LizardMan': 'Lizardman', 'FrogMan': 'Frogman', 'DevourerZombie': 'Zombie'}
YAWS = [0, 45, 90, 135, 180, 225, 270, 315]
TW, TH = (220, 210) if head else (200, 270)
LW = 110
img = Image.new('RGB', (LW + TW * len(YAWS), 30 + TH * len(RACES)), (52, 56, 66)); d = ImageDraw.Draw(img)
for j, y in enumerate(YAWS): d.text((LW + j * TW + 8, 8), 'yaw %d' % y, fill=(255, 255, 255))
for i, rc in enumerate(RACES):
    M, S = inflate2.inflate(rc)
    d.text((8, 30 + i * TH + TH // 2 - 6), NAMES.get(rc, rc), fill=(240, 236, 220))
    for j, y in enumerate(YAWS):
        if head:
            im = render3.render(M, y, 37, scale=6, size=420, stretch=1.2, foot=0.99, inner=True)
            a = np.asarray(im)[:, :, 3] > 0; t = np.nonzero(a.any(1))[0].min()
            tile = im.crop((210 - TW // 2, t - 6, 210 + TW // 2, t - 6 + TH))
        else:
            tile = render3.render(M, y, 37, scale=3.6, size=TH, stretch=1.2, foot=0.9, shadow=True, inner=True)
            tile = tile.crop(((TH - TW) // 2, 0, (TH - TW) // 2 + TW, TH))
        img.paste(tile, (LW + j * TW, 30 + i * TH), tile)
    print(rc, flush=True)
img.save(out)
