#!/usr/bin/env python3
"""The devlog's chart for the wild creatures' AI change: DM time per phase (old loops vs new) and the procs held,
two panels with their own axes. Numbers from tests/stress_wild_ab.dm (reports/polish-2026-10-22/rts-feel/wild/README.md).
    python3 tools/rts_feel/wild/devlog_chart.py devlog/2026-10-24/img/rts-feel-wild-ai.png"""
import sys
from PIL import Image, ImageDraw, ImageFont

OLD, NEW = '#2a78d6', '#eb6834'          # categorical slots 1, 2 (validated: dataviz validate_palette.js)
SURF, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
F = '/System/Library/Fonts/SFNS.ttf'


def font(n):
    return ImageFont.truetype(F, n)


def panel(d, x0, y0, w, h, title, sub, groups, vmax, fmt):
    d.text((x0, y0), title, font=font(30), fill=INK)
    d.text((x0, y0 + 40), sub, font=font(22), fill=INK2)
    top, base = y0 + 110, y0 + h - 60
    for i in range(5):   # recessive grid
        y = base - (base - top) * i / 4
        d.line([(x0, y), (x0 + w, y)], fill=GRID, width=2)
        d.text((x0, y - 28), fmt(vmax * i / 4), font=font(18), fill=INK2)
    gw = w / len(groups)
    for gi, (label, a, b) in enumerate(groups):
        cx = x0 + gw * gi + gw / 2
        bw = min(70, gw / 4)
        for k, (v, c) in enumerate(((a, OLD), (b, NEW))):
            bx = cx - bw - 1 + k * (bw + 2)   # 2 px surface gap between the pair
            by = base - (base - top) * min(1, v / vmax)
            d.rounded_rectangle([bx, by, bx + bw, base], radius=4, fill=c)
            t = fmt(v)
            tw = d.textlength(t, font=font(20))
            d.text((bx + bw / 2 - tw / 2, by - 28), t, font=font(20), fill=INK)
        tw = d.textlength(label, font=font(22))
        d.text((cx - tw / 2, base + 12), label, font=font(22), fill=INK)


def main(out):
    W, H = 1400, 620
    im = Image.new('RGB', (W, H), SURF)
    d = ImageDraw.Draw(im)
    d.text((40, 24), "Wild creatures' AI: 5,000 NPC Goblins (half wandering, half guards), old loops vs new", font=font(30), fill=INK)
    for k, (c, t) in enumerate(((OLD, 'old loops (before)'), (NEW, 'new: asleep in their procs near players, on the shared clock far away'))):
        x = 40 + k * 330
        d.rounded_rectangle([x, 76, x + 22, 98], radius=4, fill=c)
        d.text((x + 32, 72), t, font=font(22), fill=INK)
    ms = lambda v: f'{v:.0f}'
    panel(d, 40, 120, 600, 480, 'DM time, ms a second', 'lower is better; same server, both orders, 2 rounds averaged',
          [('asleep land (no player near)', 126.5, 69.5), ('awake land (near players)', 445.5, 444.5)], 500, ms)
    k = lambda v: f'{v / 1000:.1f}k' if v >= 1000 else f'{v:.0f}'
    panel(d, 760, 120, 600, 480, 'Sleeping procs held, asleep land', 'the engine\'s memory report after the phase',
          [('asleep land', 17515, 15)], 20000, k)
    im.save(out, optimize=True)
    print('wrote', out)


def look(out):
    """The second change: the target look's pre-check (rm_foe_near), DM time near and far, old look vs new, on v7f."""
    W, H = 1400, 620
    im = Image.new('RGB', (W, H), SURF)
    d = ImageDraw.Draw(im)
    d.text((40, 24), "Wild creatures' target look: skip the scan when no other side is in reach (5,000 NPC Goblins)", font=font(30), fill=INK)
    for k, (c, t) in enumerate(((OLD, 'the look as it was'), (NEW, 'with the pre-check (engine rm_foe_near, v7f candidate)'))):
        x = 40 + k * 330
        d.rounded_rectangle([x, 76, x + 22, 98], radius=4, fill=c)
        d.text((x + 32, 72), t, font=font(22), fill=INK)
    ms = lambda v: f'{v:.0f}'
    panel(d, 40, 120, 600, 480, 'DM time near players, ms a second', 'lower is better; same server, the order turned in round 2',
          [('round 1', 415.6, 236.3), ('round 2', 391.2, 242.3)], 500, ms)
    panel(d, 760, 120, 600, 480, 'DM time far from players, ms a second', 'the far tier already looks every 3 s',
          [('round 1', 61.1, 36.0), ('round 2', 64.5, 37.3)], 100, ms)
    im.save(out, optimize=True)
    print('wrote', out)


if __name__ == '__main__':
    (look if len(sys.argv) > 2 and sys.argv[2] == 'look' else main)(sys.argv[1])
