# Three arm-and-hand styles for the orc side by side: front, and the two iso fronts.
import copy, racebody, build3d10, render3
from build3d7 import Loadout
from PIL import Image, ImageDraw, ImageFont
OUT = '/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/art/out/orc-arm-styles.png'
base = copy.deepcopy(racebody.EXPLICIT['Orc'])
def style(**kw):
    E = copy.deepcopy(base); A = E['arms']
    for k, v in kw.items():
        if k == 'thick': A['rx'] = [x + v for x in A['rx']]
        elif k == 'hand': A['hand'].update(v)
        else: A[k] = v
    return E
styles = [('A: hanging close (now)', style()),
          ('B: thick arms, big fists, held out', style(thick=0.7, splay=2.4, fwd=0.6, hand=dict(rx=4.0, ry=3.0, rz=4.2, row=48.0))),
          ('C: brute stance, fists forward', style(thick=0.7, splay=2.0, fwd=0.4, swing=0.38, hand=dict(rx=4.0, ry=3.0, rz=4.2, row=48.0)))]
font = ImageFont.load_default(size=22)
C = 380
img = Image.new('RGBA', (len(styles) * 3 * C, C + 40), (52, 56, 66, 255)); d = ImageDraw.Draw(img)
for i, (name, E) in enumerate(styles):
    racebody.EXPLICIT['Orc'] = E
    G, full = build3d10.build(Loadout.of('cloth', race='Orc', hair=None))
    x0 = i * 3 * C
    d.text((x0 + 10, 8), name, fill=(240, 220, 150), font=font)
    img.alpha_composite(render3.render(G, 0, 0, scale=5.6, size=C, foot=0.98, inner=True), (x0, 40))
    for j, y in enumerate([45, 315]):
        img.alpha_composite(render3.render(G, y, 37, scale=5.2, size=C, stretch=1.2, foot=0.86, shadow=True, inner=True), (x0 + (j + 1) * C, 40))
racebody.EXPLICIT['Orc'] = base
img.save(OUT); print(img.size)
