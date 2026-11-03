# Where 3D gear attaches to each race's 64 px sprite (python3 anchors.py OUT.json): for every gear-carrying
# Races64 sheet, facing (S, N, E, W, the order of the unit's picture strips) and walk frame (0 standing, 1 and 2
# walking; the attack frames use the standing body), the right fist, the left forearm (shield) and the head, in
# the picture's pixels (x right, y down, 0-64). They come from the same template measurements and race fitting
# that drew the 2D gear (art/enhance/wearables64.py, game_export.py), so a 3D piece lands where the drawn one was.
#
# Also, per sheet, the 3D offsets the page needs to put a piece in front of or behind the flat picture: how far
# the fist, forearm and head sit to the unit's right (r) and front (f), in pixels, read off the front (S) and
# side (E) views; and the head's half-width across (S view) and front to back (E view).
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'enhance'))
import wearables64 as w     # noqa: E402
import game_export as ge    # noqa: E402

DIRS = ge.DIRS4   # S, N, E, W
WALK = 3


def head_box(T, F, race, d):
    """The head on this race in one facing: centre x, top, brow, left, right (race pixels)."""
    h = T.heads[d]
    cx, top = F.map_point(race, d, h.cx, h.top + 0.5)
    lx, brow = F.map_point(race, d, h.left + 0.5, h.brow + 0.5)
    rx, _ = F.map_point(race, d, h.right + 0.5, h.brow + 0.5)
    # the race's own outline decides the top (a dwarf's or goblin's head is not the template's)
    body = F.body_mask(race, d)
    cols = body[:, int(max(0, lx)):int(min(64, rx + 1))]
    ys = np.flatnonzero(cols.any(1))
    if len(ys):
        top = float(ys.min())
    return dict(cx=round(float(cx), 2), top=round(float(top), 2), brow=round(float(brow), 2), l=round(float(lx), 2), r=round(float(rx), 2))


def main(out):
    TS = [w.Template(frame=f) for f in range(WALK)]
    sheets = [s for s in ge.SHEETS if s.get('gear', True)]
    races = [s['race'] for s in sheets]
    FS = [w.Figures(Tf, races=races, frame=f) for f, Tf in enumerate(TS)]
    res = {}
    for spec in sheets:
        race = spec['race']
        sc = w.EXTRA.get(race[0], {}).get('scale', 1.0)
        views = {}
        for d in DIRS:
            fr = []
            for f in range(WALK):
                T, F = TS[f], FS[f]
                hand = F.map_point(race, d, *T.grip(d)[0])
                c, view = T.shield_at(d)
                sh = F.map_point(race, d, *c)
                fr.append(dict(hand=[round(float(hand[0]), 2), round(float(hand[1]), 2)],
                               shield=[round(float(sh[0]), 2), round(float(sh[1]), 2)], head=head_box(T, F, race, d)))
            views[d] = fr
        # 3D offsets from the front and side views (standing frame): S shows the unit's right on the picture's
        # left, E shows its front on the picture's right
        S, E = views['S'][0], views['E'][0]
        loc = dict(
            hand=[round(32 - S['hand'][0], 2), round(E['hand'][0] - 32, 2)],
            shield=[round(32 - S['shield'][0], 2), round(E['shield'][0] - 32, 2)],
            head=[0.0, round((E['head']['l'] + E['head']['r']) / 2 - 32, 2)],
            headw=round((S['head']['r'] - S['head']['l']) / 2, 2), headd=round((E['head']['r'] - E['head']['l']) / 2, 2))
        res[spec['sheet']] = dict(race=race[0], state=race[2], scale=sc, views=views, loc=loc)
        print(spec['sheet'], loc, flush=True)
    json.dump(res, open(out, 'w'), indent=None, separators=(',', ':'))
    print(out)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'anchors.json'))
