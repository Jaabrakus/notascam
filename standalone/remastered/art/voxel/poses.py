# The sword poses of build3d5 side by side at the game camera's angles.
import build3d5, render3
from PIL import Image, ImageDraw, ImageFont
OUT = '/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/art/out/'
try: font = ImageFont.load_default(size=22); small = ImageFont.load_default(size=16)
except TypeError: font = small = ImageFont.load_default()
poses = [('side', 'Now', 'blade at the side, flat to the front'), ('raised', 'A: raised to strike', 'wound up, blade back over the shoulder'),
         ('upright', 'B: on guard', 'blade upright beside the head'), ('forward', 'C: point at the enemy', 'blade forward and up')]
views = [('front', 0), ('iso, front-right', 45), ('iso, front-left', 315), ('side', 90)]
cell, lab = 330, 250
img = Image.new('RGBA', (lab + cell * len(views), 46 + cell * len(poses)), (52, 56, 66, 255)); d = ImageDraw.Draw(img)
for j, (name, _) in enumerate(views): d.text((lab + j * cell + 14, 14), name, fill=(220, 220, 230), font=small)
for i, (pose, title, sub) in enumerate(poses):
    G, full = build3d5.build_knight(pose=pose)
    y0 = 46 + i * cell
    d.text((14, y0 + cell // 2 - 26), title, fill=(240, 220, 150), font=font); d.text((14, y0 + cell // 2 + 4), sub, fill=(200, 200, 210), font=small)
    for j, (_, yaw) in enumerate(views):
        img.alpha_composite(render3.render(G, yaw, 37, scale=4, size=cell, stretch=1.2), (lab + j * cell, y0))
img.save(OUT + 'knight-3d-poses.png'); print(img.size)
