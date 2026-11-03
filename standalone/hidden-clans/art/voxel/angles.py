# One race's head from eight yaws (python3 angles.py OUT Race [kwargs])
import sys
import inflate2, render3, numpy as np
from PIL import Image, ImageDraw
out, rc = sys.argv[1], sys.argv[2]; kw = eval(sys.argv[3]) if len(sys.argv) > 3 else {}
M, S = inflate2.inflate(rc, **kw)
W = Image.new('RGBA', (4 * 330, 2 * 340), (52, 56, 66, 255)); d = ImageDraw.Draw(W)
for i, y in enumerate([0, 45, 90, 135, 180, 225, 270, 315]):
    im = render3.render(M, y, 37, scale=9, size=600, stretch=1.2, foot=0.99, inner=True)
    a = np.asarray(im)[:, :, 3] > 0; ys = np.nonzero(a.any(1))[0]; t = ys.min()
    W.alpha_composite(im.crop((135, t - 8, 465, t + 332)), ((i % 4) * 330, (i // 4) * 340)); d.text(((i % 4) * 330 + 6, (i // 4) * 340 + 4), 'yaw %d' % y, fill=(255, 255, 255, 255))
W.save(out)
