import build3d, render2, compose64
from PIL import Image, ImageDraw, ImageFont
M, full = build3d.build_knight()
sn = render2.smooth_normals(M)
try: font = ImageFont.load_default(size=22); small = ImageFont.load_default(size=16)
except TypeError: font = small = ImageFont.load_default()
BG = (52, 56, 66, 255)
views = [('front', 0, 'S'), ('iso, front-right', 45, 'S'), ('iso, front-left', 315, 'S'), ('iso, back-right', 135, 'N'), ('iso, back-left', 225, 'N')]
cell, lab = 320, 200
W = lab + cell * len(views) + 260; H = 46 + cell * 2
img = Image.new('RGBA', (W, H), BG); d = ImageDraw.Draw(img)
for j, (name, _, _) in enumerate(views): d.text((lab + j * cell + 14, 14), name, fill=(220, 220, 230), font=small)
d.text((lab + len(views) * cell + 14, 14), 'game size, iso', fill=(220, 220, 230), font=small)
rows = [('Sprite now', 'flat picture, nearest facing'), ('3D knight', 'built part by part')]
for i, (a, bb) in enumerate(rows):
    y0 = 46 + i * cell
    d.text((14, y0 + cell // 2 - 26), a, fill=(240, 220, 150), font=font)
    d.text((14, y0 + cell // 2 + 4), bb, fill=(200, 200, 210), font=small)
    for j, (_, yaw, face) in enumerate(views):
        if i == 0:
            im = full[face].resize((256, 256), Image.NEAREST)
            t = Image.new('RGBA', (cell, cell), (0, 0, 0, 0)); t.alpha_composite(im, ((cell - 256) // 2, (cell - 256) // 2)); im = t
        else:
            im = render2.render(M, yaw, 37, scale=4.4, size=cell, sn=sn)
        img.alpha_composite(im, (lab + j * cell, y0))
    if i == 0: g = full['S'].resize((72, 72), Image.LANCZOS)
    else: g = render2.render(M, 45, 37, scale=8, size=600, sn=sn).resize((84, 84), Image.LANCZOS)
    t = Image.new('RGBA', (260, cell), (0, 0, 0, 0)); t.alpha_composite(g, ((260 - g.width) // 2, (cell - g.height) // 2))
    img.alpha_composite(t, (lab + len(views) * cell, y0))
img.save('/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/art/out/knight-3d-test.png')
# turntable at the game's tilt
frames = []
for k in range(24):
    f = Image.new('RGBA', (360, 360), BG)
    f.alpha_composite(render2.render(M, k * 15, 37, scale=4.8, size=360, sn=sn))
    frames.append(f.convert('P', palette=Image.ADAPTIVE, colors=255))
frames[0].save('/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/art/out/knight-3d-turn.gif', save_all=True, append_images=frames[1:], duration=120, loop=0, disposal=2)
print(img.size)
