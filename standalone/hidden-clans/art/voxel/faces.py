# Close-ups of the 3D head next to the sprite's, to judge the face.
import sys, build3d8, render3
from build3d7 import Loadout
from PIL import Image
OUT = sys.argv[1]
bare = Loadout.of('cloth'); bare.legs = ('Gear64/Human/cloth.dmi', 'legs.cloth')
knight = Loadout.of('iron', chest='plate', legs='plate', arms='plate', helmet='nasal', shield='heater', weapon='longsword')
img = Image.new('RGBA', (5 * 360, 380), (52, 56, 66, 255))
G2, full2 = build3d8.build(bare); G, full = build3d8.build(knight)
img.alpha_composite(full2['S'].resize((640, 640), Image.NEAREST).crop((140, 60, 500, 440)), (0, 0))
for j, (g, y, p) in enumerate([(G2, 0, 0), (G2, 45, 37), (G2, 315, 37), (G, 315, 37)]):
    im = render3.render(g, y, p, scale=10, size=900, stretch=1.0 if not p else 1.2, foot=1.0 if not p else 0.9)
    bb = im.getbbox(); top = bb[1]
    img.alpha_composite(im.crop((270, top - 10, 630, top + 370)), ((j + 1) * 360, 0))
img.save(OUT)
