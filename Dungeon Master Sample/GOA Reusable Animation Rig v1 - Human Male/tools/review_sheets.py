#!/usr/bin/env python3
"""Review pictures for a cut character, written to review/:

  parts-<View>.png       every part per facing at 6x, joints in green
  idle-reassembly.png    the 15 idle parts composited in the engine's draw order (top: source cell, bottom: parts;
                         red = source pixel missing or recoloured, cyan = pixel the parts add outside the source)

    python3 tools/review_sheets.py profiles/human-male.json inputs/sprites.png
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

RIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = ['head', 'torso', 'pelvis', 'rightUpperArm', 'rightForearm', 'rightHand', 'leftUpperArm', 'leftForearm',
         'leftHand', 'rightThigh', 'rightShin', 'rightFoot', 'leftThigh', 'leftShin', 'leftFoot']
LEGS = ['leftThigh', 'leftShin', 'leftFoot', 'rightThigh', 'rightShin', 'rightFoot']
R = ['rightUpperArm', 'rightForearm', 'rightHand']
L = ['leftUpperArm', 'leftForearm', 'leftHand']
BODY = ['pelvis', 'torso', 'head']
# engine.js render order at rest: South arms over the body, North arms behind, side views far arm behind
ORDER = {0: LEGS + BODY + L + R, 1: R + L + LEGS + BODY, 2: L + LEGS + BODY + R, 3: R + LEGS + BODY + L}


def main(profile_path, sheet_path):
    p = json.load(open(profile_path))
    assets = os.path.join(RIG, 'preview/assets')
    S, X0, X1 = 6, 12, 52
    W, H = (X1 - X0) * S, 64 * S
    for v, view in enumerate(p['views']):
        sheet = Image.new('RGBA', (8 * W, 2 * H), (40, 60, 50, 255))
        d = ImageDraw.Draw(sheet)
        pts = {'head': [view['neck']], 'torso': [view['neck'], view['waist']], 'pelvis': [view['waist']]}
        for side, (s, e, h) in view['arms'].items():
            pts[side + 'UpperArm'], pts[side + 'Forearm'], pts[side + 'Hand'] = [s, e], [e, h], [h]
        for side, (hp, k, a) in view['legs'].items():
            pts[side + 'Thigh'], pts[side + 'Shin'], pts[side + 'Foot'] = [hp, k], [k, a], [a]
        for c, n in enumerate(NAMES + ['walk0']):
            f = view['parts'][n] if n in view['parts'] else view['walk'][0]['refined-torso']
            im = Image.open(os.path.join(assets, f)).convert('RGBA')
            ox, oy = (c % 8) * W, (c // 8) * H
            sheet.alpha_composite(im.crop((X0, 0, X1, 64)).resize((W, H), Image.NEAREST), (ox, oy))
            d.text((ox + 4, oy + 4), n, fill=(255, 255, 0, 255))
            for pt in pts.get(n, []):
                x, y = ox + (pt[0] - X0) * S, oy + pt[1] * S
                d.ellipse([x - 3, y - 3, x + 3, y + 3], outline=(0, 255, 0, 255), width=2)
        sheet.save(os.path.join(RIG, 'review', f'parts-{view["name"]}.png'))
    src_sheet = np.array(Image.open(sheet_path).convert('RGBA'))
    out = Image.new('RGBA', (4 * 256, 2 * 256), (40, 60, 50, 255))
    rep = {}
    for v, view in enumerate(p['views']):
        comp = np.zeros((64, 64, 4), np.uint8)
        for n in ORDER[v]:
            im = np.array(Image.open(os.path.join(assets, view['parts'][n])).convert('RGBA'))
            m = im[:, :, 3] > 0
            comp[m] = im[m]
        src = src_sheet[0:64, v * 64:(v + 1) * 64]
        so, co = src[:, :, 3] > 0, comp[:, :, 3] > 0
        diff = so & ((comp[:, :, :3] != src[:, :, :3]).any(2) | ~co)
        extra = co & ~so
        rep[view['name']] = {'source_px': int(so.sum()), 'wrong_or_missing': int(diff.sum()),
                             'added_outside_source': int(extra.sum())}
        vis = comp.copy()
        vis[diff] = (255, 0, 0, 255)
        vis[extra] = (0, 255, 255, 255)
        out.alpha_composite(Image.fromarray(src).resize((256, 256), Image.NEAREST), (v * 256, 0))
        out.alpha_composite(Image.fromarray(vis).resize((256, 256), Image.NEAREST), (v * 256, 256))
    out.save(os.path.join(RIG, 'review', 'idle-reassembly.png'))
    json.dump(rep, open(os.path.join(RIG, 'review', 'idle-reassembly.json'), 'w'), indent=1)
    print(json.dumps(rep))


if __name__ == '__main__':
    main(*(sys.argv[1:3] if len(sys.argv) > 2 else (os.path.join(RIG, 'profiles/human-male.json'), os.path.join(RIG, 'inputs/sprites.png'))))
