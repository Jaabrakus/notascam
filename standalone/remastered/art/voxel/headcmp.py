# Heads, old against new (python3 headcmp.py OUT 'Race,..'): per race the sprite, then the previous
# round's head and this round's at both game corners, at game size blown up 3x
import sys
import inflate2, render3, numpy as np
from PIL import Image, ImageDraw
out, races = sys.argv[1], sys.argv[2].split(',')
W = 120
img = Image.new('RGBA', (W * 5, W * len(races)), (74, 92, 60, 255))
for i, rc in enumerate(races):
    M0, S = inflate2.inflate(rc, head_mode='r3'); M1, _ = inflate2.inflate(rc)
    img.alpha_composite(Image.fromarray(S.astype(np.uint8)).resize((112, 112), Image.NEAREST), (4, i * W + 4))
    for j, (M, y) in enumerate([(M0, 45), (M1, 45), (M0, 315), (M1, 315)]):
        img.alpha_composite(render3.render(M, y, 37, scale=1.6, size=W, stretch=1.2, foot=0.9, shadow=True, inner=True), ((j + 1) * W, i * W))
    print(rc, flush=True)
img = img.resize((img.width * 3, img.height * 3), Image.NEAREST)
d = ImageDraw.Draw(img)
for j, t in enumerate(['sprite', 'before 45', 'now 45', 'before 315', 'now 315']): d.text((j * W * 3 + 8, 4), t, fill=(255, 255, 255, 255))
img.save(out)
