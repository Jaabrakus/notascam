# Sprite vs the 3D knight at the game camera's angles, plus a turntable. Default: the latest pass.
import sys, importlib, render3
build = importlib.import_module(sys.argv[1] if len(sys.argv) > 1 else 'build3d3')
from PIL import Image, ImageDraw, ImageFont
OUT = '/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/art/out/'
G, full = build.build_knight()
sn = getattr(G, 'sn', None)
if sn is None: sn = render3.smooth_normals(G)
try: font = ImageFont.load_default(size=22); small = ImageFont.load_default(size=16)
except TypeError: font = small = ImageFont.load_default()
BG = (52, 56, 66, 255); ST = 1.2
views = [('front', 0, 'S'), ('iso, front-right', 45, 'S'), ('iso, front-left', 315, 'S'), ('iso, back-right', 135, 'N'), ('iso, back-left', 225, 'N')]
cell, lab, gw = 340, 200, 240
img = Image.new('RGBA', (lab + cell * len(views) + gw, 46 + cell * 2), BG); d = ImageDraw.Draw(img)
for j, (name, _, _) in enumerate(views): d.text((lab + j * cell + 14, 14), name, fill=(220, 220, 230), font=small)
d.text((lab + len(views) * cell + 14, 14), 'game size, iso', fill=(220, 220, 230), font=small)
for i, (a, b) in enumerate([('Sprite now', 'flat picture, nearest facing'), ('3D knight', 'parts and items in 3D')]):
    y0 = 46 + i * cell
    d.text((14, y0 + cell // 2 - 26), a, fill=(240, 220, 150), font=font); d.text((14, y0 + cell // 2 + 4), b, fill=(200, 200, 210), font=small)
    for j, (_, yaw, face) in enumerate(views):
        if i == 0:
            im = full[face].resize((256, 256), Image.NEAREST); t = Image.new('RGBA', (cell, cell), (0, 0, 0, 0))
            t.alpha_composite(im, ((cell - 256) // 2, (cell - 256) // 2 + 20)); im = t
        else: im = render3.render(G, yaw, 37, scale=4, size=cell, stretch=ST, sn=sn)
        img.alpha_composite(im, (lab + j * cell, y0))
    # game size: the sprite as the 3D view stretches it today; the model at the same scale
    if i == 0: g = full['S'].resize((72, 90), Image.LANCZOS)
    else: g = render3.render(G, 45, 37, scale=9, size=720, stretch=ST, sn=sn).resize((90, 90), Image.LANCZOS)
    t = Image.new('RGBA', (gw, cell), (0, 0, 0, 0)); t.alpha_composite(g, ((gw - g.width) // 2, (cell - g.height) // 2)); img.alpha_composite(t, (lab + len(views) * cell, y0))
img.save(OUT + 'knight-3d-test.png')
frames = []
for k in range(24):
    f = Image.new('RGBA', (380, 380), BG); f.alpha_composite(render3.render(G, k * 15, 37, scale=4.6, size=380, stretch=ST, sn=sn))
    frames.append(f.convert('P', palette=Image.ADAPTIVE, colors=255))
frames[0].save(OUT + 'knight-3d-turn.gif', save_all=True, append_images=frames[1:], duration=110, loop=0, disposal=2)
print(img.size)
