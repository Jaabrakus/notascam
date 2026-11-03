# Big balloon close-ups: for each race the sprite, then the 3D from the game's two front
# corners and a back corner.
import sys, inflate2, render3, numpy as np
from PIL import Image
out, races = sys.argv[1], sys.argv[2].split(',')
W = 400
img = Image.new('RGBA', (4 * W, len(races) * 500), (52, 56, 66, 255))
for i, rc in enumerate(races):
    M, S = inflate2.inflate(rc)
    img.alpha_composite(Image.fromarray(S.astype(np.uint8)).resize((448, 448), Image.NEAREST).crop((24, 0, 424, 448)), (0, i * 500 + 26))
    for j, y in enumerate([45, 315, 160]):
        im = render3.render(M, y, 37, scale=6.6, size=600, stretch=1.2, foot=0.86, shadow=True, inner=True)
        bb = im.getbbox(); img.alpha_composite(im.crop((100, bb[1] - 6, 500, bb[1] + 494)), ((j + 1) * W, i * 500))
img.save(out)
