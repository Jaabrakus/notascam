# Side check (python3 sidecheck.py OUT 'Race,Race'): sprite S | sprite E | 3D side (yaw 90, flat) | 3D yaw 90 at the game pitch | iso 45 | iso 315
import sys
import inflate2, render3, numpy as np
from PIL import Image
out, races = sys.argv[1], sys.argv[2].split(',')
kw = eval(sys.argv[3]) if len(sys.argv) > 3 else {}
W = 300
img = Image.new('RGBA', (W * 6, W * len(races)), (52, 56, 66, 255))
for i, rc in enumerate(races):
    M, S = inflate2.inflate(rc, **kw); raw = inflate2.pictures(rc)
    img.alpha_composite(Image.fromarray(S.astype(np.uint8)).resize((W, W), Image.NEAREST), (0, i * W))
    img.alpha_composite(Image.fromarray(raw['E'].astype(np.uint8)).resize((W, W), Image.NEAREST), (W, i * W))
    for j, (y, p, st, f) in enumerate([(90, 0, 1.0, 1.0), (90, 37, 1.2, 0.95), (45, 37, 1.2, 0.95), (315, 37, 1.2, 0.95)]):
        im = render3.render(M, y, p, scale=W / 64 * (1.0 if p == 0 else 0.9), size=W, stretch=st, foot=f, inner=True)
        img.alpha_composite(im, ((j + 2) * W, i * W))
img.save(out)
