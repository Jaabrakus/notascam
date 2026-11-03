# Walk cycle and sword swing of the rigged knight (build3d8, iron plate knight) at the game's iso camera, both
# front corners side by side, as GIFs, plus a sheet of the key frames.
import math, numpy as np
import build3d6, build3d8, render3
from build3d7 import Loadout
KNIGHT = Loadout.of('iron', chest='plate', legs='plate', arms='plate', helmet='nasal', shield='heater', weapon='longsword')
from PIL import Image, ImageDraw, ImageFont
OUT = '/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/art/out/'
BG = (52, 56, 66, 255); SIZE, SCALE, ST, PITCH, BASE = 380, 4.2, 1.2, 37, 0.74
VIEWS = (45, 315)
try: small = ImageFont.load_default(size=15)
except TypeError: small = ImageFont.load_default()

def project(pt, yaw):
    """Screen position of a model point (x, row, z) in render3's picture."""
    t = math.radians(yaw); p = math.radians(PITCH)
    rv = np.array([math.cos(t), 0, -math.sin(t)]); uv = np.array([math.sin(t) * math.sin(p), math.cos(p), math.cos(t) * math.sin(p)])
    w = np.array([pt[0] - 32, (64 - pt[1]) * ST, pt[2] - build3d6.CZ])
    return SIZE / 2 + (w @ rv) * SCALE, SIZE * BASE - (w @ uv) * SCALE

def tip(t):
    rig = build3d6.attack_rig(t)
    fist = np.array(rig.sword[1]) + np.array([0, -rig.rise, 0])
    d = np.array(rig.sword[2]); d /= np.linalg.norm(d)
    return fist + 29 * d

def frame(rig, swoosh=None):
    G, _ = build3d8.build(KNIGHT, rig)
    out = Image.new('RGBA', (SIZE * len(VIEWS), SIZE + 22), BG)
    for j, yaw in enumerate(VIEWS):
        im = render3.render(G, yaw, PITCH, scale=SCALE, size=SIZE, stretch=ST, shadow=True, foot=BASE)
        if swoosh:
            # a pale trail along the blade tip's path over the last moments of the cut
            t0, t1 = swoosh
            pts = [project(tip(t0 + (t1 - t0) * k / 14), yaw) for k in range(15)]
            sw = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(sw)
            for k in range(14):
                a = int(30 + 120 * k / 13)
                d.line([pts[k], pts[k + 1]], fill=(235, 240, 250, a), width=int(SCALE * (0.8 + 1.6 * k / 13)))
            im.alpha_composite(sw)
        out.alpha_composite(im, (j * SIZE, 0))
    dr = ImageDraw.Draw(out)
    for j, name in enumerate(('iso, front-right', 'iso, front-left')): dr.text((j * SIZE + 12, SIZE + 3), name, fill=(200, 200, 210), font=small)
    return out

def save_gif(frames, durations, name):
    pal = [f.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255) for f in frames]
    pal[0].save(OUT + name, save_all=True, append_images=pal[1:], duration=durations, loop=0, disposal=2)

walk = [frame(build3d6.walk_rig(k / 10)) for k in range(10)]
save_gif(walk, [85] * len(walk), 'knight-3d-walk.gif')

times = [0, 0, 0.08, 0.16, 0.24, 0.30, 0.30, 0.37, 0.43, 0.48, 0.55, 0.62, 0.67, 0.72, 0.79, 0.86, 0.93, 1.0, 1.0]
trail = {0.37: (0.30, 0.37), 0.43: (0.32, 0.43), 0.48: (0.37, 0.48), 0.55: (0.43, 0.55), 0.62: (0.50, 0.62)}
attack = [frame(build3d6.attack_rig(t), trail.get(t)) for t in times]
dur = [90 if t not in trail else 60 for t in times]; dur[0] = 300; dur[6] = 160; dur[-1] = 300
save_gif(attack, dur, 'knight-3d-attack.gif')

# key frames on one sheet
keys = [walk[0], walk[2], walk[5], walk[7], attack[0], attack[5], attack[8], attack[9], attack[11], attack[13]]
names = ['walk 1', 'walk 2', 'walk 3', 'walk 4', 'on guard', 'wind-up', 'cut', 'cut', 'follow-through', 'hold']
cols = 2; w, h = keys[0].size
sheet = Image.new('RGBA', (w * cols, (h + 24) * math.ceil(len(keys) / cols)), BG); dr = ImageDraw.Draw(sheet)
for i, (k, n) in enumerate(zip(keys, names)):
    x0, y0 = (i % cols) * w, (i // cols) * (h + 24)
    sheet.alpha_composite(k, (x0, y0 + 24)); dr.text((x0 + 12, y0 + 4), n, fill=(240, 220, 150), font=small)
sheet.save(OUT + 'knight-3d-anim-keys.png')
print('walk', len(walk), 'attack', len(attack), sheet.size)
