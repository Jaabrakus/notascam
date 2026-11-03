# Heads close up (python3 heads.py OUT 'Race,..' [kwargs]): per race the sprite's head, then the 3D
# head at the two game corners and from the front, big, so faces, eyes and ears can be judged
import sys
import inflate2, render3, numpy as np
from PIL import Image, ImageDraw
out, races = sys.argv[1], sys.argv[2].split(',')
kw = eval(sys.argv[3]) if len(sys.argv) > 3 else {}
W, H = 330, 330
img = Image.new('RGBA', (W * 4, H * len(races)), (52, 56, 66, 255))
for i, rc in enumerate(races):
    M, S = inflate2.inflate(rc, **kw); L = inflate2.LAST
    t, nk = L['top_r'], L['neck_r']
    r0 = max(0, t - 8); r1 = min(64, nk + 3)
    crop = Image.fromarray(S.astype(np.uint8)).crop((8, r0, 56, r1))
    sc = min((W - 20) / crop.width, (H - 20) / crop.height)
    crop = crop.resize((int(crop.width * sc), int(crop.height * sc)), Image.NEAREST)
    img.alpha_composite(crop, ((W - crop.width) // 2, i * H + (H - crop.height) // 2))
    for j, (y, p, st) in enumerate([(45, 37, 1.2), (315, 37, 1.2), (0, 0, 1.0)]):
        im = render3.render(M, y, p, scale=7.5, size=700, stretch=st, foot=0.97, inner=True)
        a = np.asarray(im)[:, :, 3] > 0
        ys = np.nonzero(a.any(1))[0]; top = ys.min()
        cx = 350
        img.alpha_composite(im.crop((cx - W // 2, top - 10, cx + W // 2, top - 10 + H)), ((j + 1) * W, i * H))
    print(rc, flush=True)
img.save(out)
