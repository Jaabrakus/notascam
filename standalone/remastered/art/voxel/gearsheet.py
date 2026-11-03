# Contact sheet of gear sprites (front and side facing) to design their 3D shapes from.
import sys, dmi
from PIL import Image, ImageDraw, ImageFont
R = '/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Icons/Remastered/'
def sheet(items, out, dirs='SE', k=3):
    font = ImageFont.load_default(size=13)
    cell = 64 * k; w = len(dirs) * cell + 8
    cols = 4; rows = (len(items) + cols - 1) // cols
    img = Image.new('RGBA', (cols * w, rows * (cell + 18)), (70, 74, 84, 255)); d = ImageDraw.Draw(img)
    cache = {}
    for i, (fn, st) in enumerate(items):
        if fn not in cache: cache[fn] = dmi.load(R + fn)
        x0, y0 = (i % cols) * w, (i // cols) * (cell + 18)
        body = dmi.load(R + 'Races64/Human.dmi')['']
        for j, dd in enumerate(dirs):
            base = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); base.alpha_composite(dmi.frame(body, dd).copy())
            ghost = base.copy(); ghost.putalpha(ghost.getchannel('A').point(lambda a: a // 4))
            c = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); c.alpha_composite(ghost); c.alpha_composite(dmi.frame(cache[fn][st], dd))
            img.alpha_composite(c.resize((cell, cell), Image.NEAREST), (x0 + j * cell, y0 + 18))
        d.text((x0 + 4, y0 + 2), st, fill=(255, 255, 255), font=font)
    img.save(out)
