#!/usr/bin/env python3
"""Elf | Human side by side at every clip's key and event times.

    python3 tools/compare_sheets.py <drop_dir> [suffix]

<drop_dir> holds elf-<clip>.png, human-<clip>.png (4 views per row, 192 px cells) and elf-times.json, rendered in the
viewer by the same script for both characters. Writes review/compare/<clip>.png: each row = one time; left four
cells = Elf (approved baseline), right four = Human; 2x nearest neighbour; time on the row.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

RIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROP = (24, 20, 168, 164)  # inside each 192 px cell; body origin is (64, 64)
S = 2


def main(drop, suffix=''):
    times = json.load(open(os.path.join(drop, f'elf-times{suffix}.json')))
    out_dir = os.path.join(RIG, 'review', 'compare' + (suffix or ''))
    os.makedirs(out_dir, exist_ok=True)
    cw, ch = (CROP[2] - CROP[0]) * S, (CROP[3] - CROP[1]) * S
    gap, head = 24, 22
    for clip, ts in times.items():
        safe = ''.join(c if c.isalnum() or c in '_-' else '_' for c in clip)
        ims = {}
        for who in ('elf', 'human'):
            p = os.path.join(drop, f'{who}-{safe}{suffix}.png')
            if not os.path.exists(p):
                break
            ims[who] = Image.open(p).convert('RGBA')
        if len(ims) < 2:
            continue
        W = 8 * cw + gap
        H = head + len(ts) * ch
        sheet = Image.new('RGBA', (W, H), (34, 51, 40, 255))
        d = ImageDraw.Draw(sheet)
        d.text((4, 4), f'{clip}   left: Elf (approved)   right: Human', fill=(255, 255, 255, 255))
        for r, t in enumerate(ts):
            for k, who in enumerate(('elf', 'human')):
                for v in range(4):
                    c = ims[who].crop((v * 192 + CROP[0], r * 192 + CROP[1], v * 192 + CROP[2], r * 192 + CROP[3]))
                    x = (k * 4 + v) * cw + (gap if k else 0)
                    sheet.alpha_composite(c.resize((cw, ch), Image.NEAREST), (x, head + r * ch))
            d.text((4, head + r * ch + 4), f'{t:.2f}s', fill=(255, 230, 120, 255))
        d.line([(4 * cw + gap // 2, head), (4 * cw + gap // 2, H)], fill=(120, 140, 120, 255), width=2)
        sheet.save(os.path.join(out_dir, safe + '.png'))
    print('wrote', len(os.listdir(out_dir)), 'sheets to', out_dir)


if __name__ == '__main__':
    main(*sys.argv[1:3])
