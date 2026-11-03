#!/usr/bin/env python3
"""Placeholder pictures for the rulership regalia (planning/RULERSHIP.md): the game has only two crown sprites,
RoyalItems.dmi "BoneCrown" and GoldItems.dmi "Crown", so each new item is one of them, tinted. Writes
game/Icons/Remastered/Regalia.dmi (32 px, 4 dirs, the source's frames). Replace with real art when there is some.

    python3 art/regalia/make_regalia_icons.py
"""
from pathlib import Path
import re
from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[2]
ICONS = ROOT/'game/Icons'
OUT = ICONS/'Remastered/Regalia.dmi'

# state -> (source file, source state, tint rgb, how much of the tint to take)
STATES = {
    'totem': ('RoyalItems.dmi', 'BoneCrown', (150, 104, 60), 0.75),          # Camp: wood and bone
    'staff': ('RoyalItems.dmi', 'BoneCrown', (120, 140, 70), 0.6),           # Hamlet: wood and leather
    'chain': ('GoldItems.dmi', 'Crown', (112, 116, 126), 0.9),             # Village: iron
    'silvercirclet': ('GoldItems.dmi', 'Crown', (172, 180, 198), 0.9),     # Town: silver
    'heircirclet': ('GoldItems.dmi', 'Crown', (120, 152, 214), 0.9),        # the heir's, silver
    'heirband': ('RoyalItems.dmi', 'BoneCrown', (214, 150, 166), 0.7),      # the heir's, bone
}


def states(path):
    im = Image.open(path)
    desc = im.info['Description']
    w = int(re.search(r'width = (\d+)', desc).group(1))
    h = int(re.search(r'height = (\d+)', desc).group(1))
    out, index = {}, 0
    for m in re.finditer(r'state = "([^"]*)"\n((?:\t[^\n]*\n)*)', desc):
        dirs = int(re.search(r'dirs = (\d+)', m.group(2)).group(1))
        frames = int(re.search(r'frames = (\d+)', m.group(2)).group(1))
        delay = re.search(r'delay = ([^\n]*)', m.group(2))
        out[m.group(1)] = dict(start=index, count=dirs * frames, dirs=dirs, frames=frames, delay=delay and delay.group(1))
        index += dirs * frames
    return im.convert('RGBA'), w, h, out


def tint(px, rgb, k):
    r, g, b, a = px
    if not a: return px
    lum = (0.3 * r + 0.59 * g + 0.11 * b) / 255
    lift = 0.4 + 0.7 * lum
    return tuple(min(255, round((1 - k) * c + k * t * lift)) for c, t in zip((r, g, b), rgb)) + (a,)


def main():
    cache, cells, lines = {}, [], ['# BEGIN DMI', 'version = 4.0', '\twidth = 32', '\theight = 32']
    for name, (src, state, rgb, k) in STATES.items():
        if src not in cache: cache[src] = states(ICONS/src)
        im, w, h, S = cache[src]
        s = S[state]
        cols = im.width // w
        for i in range(s['start'], s['start'] + s['count']):
            cell = im.crop(((i % cols) * w, (i // cols) * h, (i % cols + 1) * w, (i // cols + 1) * h))
            cell.putdata([tint(p, rgb, k) for p in cell.getdata()])
            cells.append(cell)
        lines += [f'state = "{name}"', f'\tdirs = {s["dirs"]}', f'\tframes = {s["frames"]}']
        if s['delay']: lines.append(f'\tdelay = {s["delay"]}')
        lines += ['\tmovement = 0', '\trewind = 0']
    lines.append('# END DMI')
    cols = 6
    rows = -(-len(cells) // cols)
    sheet = Image.new('RGBA', (cols * 32, rows * 32), (0, 0, 0, 0))
    for i, c in enumerate(cells): sheet.paste(c, ((i % cols) * 32, (i // cols) * 32))
    info = PngImagePlugin.PngInfo()
    info.add_text('Description', '\n'.join(lines) + '\n', zip=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT, format="PNG", pnginfo=info)
    print(OUT, sheet.size, len(cells), 'cells')


if __name__ == '__main__':
    main()
