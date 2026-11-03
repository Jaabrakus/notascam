#!/usr/bin/env python3
"""The devlog's chart for the chop hitch: the orders window's slow frames and the Controls drawer's time, the page as it
was (chop-hitch-chop1.json) against the landed one (chop-hitch-chop3-game.json), both real-client chop runs.
    python3 tools/rts_feel/chop/devlog_chart.py devlog/2026-10-25/img/rts-feel-chop-hitch.png"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'wild'))
from devlog_chart import OLD, NEW, SURF, INK, font, panel

ROOT = Path(__file__).resolve().parents[3]
R = ROOT/'reports/polish-2026-10-22/rts-feel'


def main(out):
    a = json.loads((R/'chop-hitch-chop1.json').read_text())['page']
    b = json.loads((R/'chop-hitch-chop3-game.json').read_text())['page']
    W, H = 1400, 620
    im = Image.new('RGB', (W, H), SURF)
    d = ImageDraw.Draw(im)
    d.text((40, 24), 'The chop hitch: 30 units ordered to chop, then split to two more groves as they walk', font=font(30), fill=INK)
    for k, (c, t) in enumerate(((OLD, 'before (the drawer rebuilt while closed)'), (NEW, 'landed (built only while open)'))):
        x = 40 + k * 480
        d.rounded_rectangle([x, 76, x + 22, 98], radius=4, fill=c)
        d.text((x + 32, 72), t, font=font(22), fill=INK)
    n = lambda v: f'{v:.0f}'
    panel(d, 40, 120, 600, 480, 'Slow frames while giving the orders', 'the 10 s of the three orders; fewer is better',
          [('over 33 ms', a['orders']['over33'], b['orders']['over33']), ('over 50 ms', a['orders']['over50'], b['orders']['over50']),
           ('worst, ms', a['orders']['worst'], b['orders']['worst'])], 80, n)
    rb = lambda p: (p['totals'].get('renderBorderControls') or [0, 0])[1]
    panel(d, 760, 120, 600, 480, 'Page time over the 35 s, ms', 'the HUD update and, inside it, the closed drawer',
          [('HUD update', a['totals']['updateHUD'][1], b['totals']['updateHUD'][1]), ('Controls drawer', rb(a), rb(b))], 480, n)
    im.save(out, optimize=True)
    print('wrote', out)


if __name__ == '__main__':
    main(sys.argv[1])
