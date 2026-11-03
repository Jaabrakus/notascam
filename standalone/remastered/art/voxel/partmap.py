# The part map (python3 partmap.py OUT 'Race,..'): what inflate2 decided each pixel is, drawn
# over the sprite and on the 3D at the game's corner - so limbs can be checked by eye
import sys
import inflate2, render3, numpy as np
from PIL import Image, ImageDraw
NAMES = {1: 'torso', 2: 'head', 3: 'ears', 4: 'legs', 5: 'web', 6: 'arm L', 7: 'arm R', 8: 'feet', 9: 'horns', 10: 'neck', 11: 'shoulders', 12: 'hands', 13: 'ankle'}
PAL = {1: (200, 60, 60), 2: (240, 200, 80), 3: (255, 120, 200), 4: (70, 110, 230), 5: (20, 20, 20), 6: (80, 200, 90), 7: (40, 150, 60),
       8: (130, 80, 220), 9: (250, 250, 250), 10: (240, 140, 50), 11: (120, 220, 200), 12: (160, 255, 120), 13: (255, 255, 0)}
out, races = sys.argv[1], sys.argv[2].split(',')
W = 320
img = Image.new('RGBA', (W * 4, W * len(races) + 40), (52, 56, 66, 255))
for i, rc in enumerate(races):
    M, S = inflate2.inflate(rc); L = inflate2.LAST; limb = L['limb']
    pic = S.astype(np.uint8).copy()
    for k, c in PAL.items():
        m = limb == k
        pic[m, :3] = (0.45 * pic[m, :3] + 0.55 * np.array(c)).astype(np.uint8); pic[m, 3] = 255
    img.alpha_composite(Image.fromarray(S.astype(np.uint8)).resize((W, W), Image.NEAREST), (0, 40 + i * W))
    img.alpha_composite(Image.fromarray(pic).resize((W, W), Image.NEAREST), (W, 40 + i * W))
    # the 3D in part colours: head parts from the voxel ids (the head is resized), the rest from the map
    n = M.n; sub = M.sub
    l3 = limb[np.arange(n)[:, None] // sub, np.arange(n)[None, :] // sub][:, :, None].repeat(n, 2)
    l3 = np.where(M.owner == 2, 2, np.where(M.owner == 3, np.where(l3 == 9, 9, 3), l3))
    col = np.zeros(M.col.shape, np.int32)
    for k, c in PAL.items(): col[l3 == k, :3] = c
    col[..., 3] = np.where(M.owner > 0, 255, 0)
    keep = M.col; M.col = col; M.rim = {}; M.lit = None
    for j, (y, p, st) in enumerate([(45, 37, 1.2), (0, 0, 1.0)]):
        img.alpha_composite(render3.render(M, y, p, scale=4.4, size=W, stretch=st, foot=0.95, inner=True), ((j + 2) * W, 40 + i * W))
    M.col = keep
    print(rc, flush=True)
d = ImageDraw.Draw(img); x = 8
for k in sorted(NAMES):
    d.rectangle([x, 10, x + 18, 28], fill=PAL[k] + (255,)); d.text((x + 24, 12), NAMES[k], fill=(255, 255, 255, 255)); x += 24 + 7 * len(NAMES[k]) + 16
img.save(out)
