# One race from six angles, big (python3 views.py OUT Race): sprite, front, side, top, both game
# corners, back corner
import sys
import inflate2, render3, numpy as np
from PIL import Image
out, rc = sys.argv[1], sys.argv[2]
M, S = inflate2.inflate(rc)
views = [(0, 0, 1.0), (90, 0, 1.0), (0, 89, 1.0), (45, 37, 1.2), (315, 37, 1.2), (135, 37, 1.2)]
W = 420
img = Image.new('RGBA', (W * 4, W * 2), (52, 56, 66, 255))
img.alpha_composite(Image.fromarray(S.astype(np.uint8)).resize((W, W), Image.NEAREST), (0, 0))
for i, (y, p, st) in enumerate(views):
    im = render3.render(M, y, p, scale=6.5, size=W, stretch=st, foot=0.9 if p < 80 else 0.6, inner=True)
    j = i + 1
    img.alpha_composite(im, ((j % 4) * W, (j // 4) * W))
img.save(out)
