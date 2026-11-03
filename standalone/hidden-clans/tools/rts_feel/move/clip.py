#!/usr/bin/env python3
"""A side-by-side GIF of the two walk runs (real_feel.py --only walk): before | after, 3.2 s at 15 frames a second, cropped
round the walking units.  python3 tools/rts_feel/move/clip.py CASE [OUT.gif]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
R = Path(__file__).resolve().parents[3]/'reports/polish-2026-10-22/rts-feel'
case = sys.argv[1]; out = Path(sys.argv[2]) if len(sys.argv) > 2 else R/'movement'/f'{case}-before-after.gif'
def frames(tag):
    return [Image.open(f).convert('RGB') for f in sorted((R/f'real-frames-{tag}').glob(f'{case}-*.png'))]
A, B = frames('walk-before'), frames('walk-after')
n = min(len(A), len(B))
if not n: sys.exit('no frames')
w, h = A[0].size; box = (int(w*0.18), int(h*0.22), int(w*0.82), int(h*0.78))   # the middle of the view, where they walk
cw, ch = box[2] - box[0], box[3] - box[1]; sc = 420/cw
G = []
for i in range(n):
    o = Image.new('RGB', (2*int(cw*sc) + 8, int(ch*sc) + 22), (20, 20, 20))
    for j, (im, label) in enumerate(((A[i], 'before'), (B[i], 'after'))):
        o.paste(im.crop(box).resize((int(cw*sc), int(ch*sc))), (j*(int(cw*sc) + 8), 22))
        ImageDraw.Draw(o).text((j*(int(cw*sc) + 8) + 6, 4), label, fill=(242, 210, 122))
    G.append(o)
out.parent.mkdir(parents=True, exist_ok=True)
G[0].save(out, save_all=True, append_images=G[1:], duration=67, loop=0, optimize=True)
print(out, n, 'frames')
