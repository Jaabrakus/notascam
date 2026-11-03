# Debug sheet: each race's standing and walk frames in every facing with the anchors drawn on
# (red fist, blue forearm, green head box). python3 check_anchors.py OUT.png
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'enhance'))
from game_export import read_dmi_full
R64 = os.path.join(HERE, '../../game/Icons/Remastered/Races64')
A = json.load(open(os.path.join(HERE, 'anchors.json')))
Z = 4
rows = []
for sheet, a in A.items():
    cells = next(c for n, m, c in read_dmi_full(os.path.join(R64, sheet + '.dmi')) if n == a['state'])
    rows.append((sheet, a, cells))
W = 12 * 64 * Z
img = Image.new('RGBA', (W, len(rows) * 64 * Z), (60, 64, 72, 255))
d = ImageDraw.Draw(img)
for ri, (sheet, a, cells) in enumerate(rows):
    for f in range(3):
        for di, dn in enumerate('SNEW'):
            c = cells[f * 4 + di] if len(cells) >= 12 else cells[di]
            x0, y0 = (f * 4 + di) * 64 * Z, ri * 64 * Z
            img.alpha_composite(Image.fromarray(c).resize((64 * Z, 64 * Z), Image.NEAREST), (x0, y0))
            v = a['views'][dn][f]
            P = lambda p: (x0 + p[0] * Z, y0 + p[1] * Z)
            hx, hy = P(v['hand']); d.ellipse([hx - 6, hy - 6, hx + 6, hy + 6], outline=(255, 40, 40), width=3)
            sx, sy = P(v['shield']); d.ellipse([sx - 6, sy - 6, sx + 6, sy + 6], outline=(60, 120, 255), width=3)
            h = v['head']; d.rectangle([*P((h['l'], h['top'])), *P((h['r'], h['brow']))], outline=(40, 230, 90), width=2)
    d.text((6, ri * 64 * Z + 4), sheet, fill=(255, 255, 255))
img.save(sys.argv[1])
print(sys.argv[1], img.size)
