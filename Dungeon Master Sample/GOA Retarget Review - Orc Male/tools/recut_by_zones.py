#!/usr/bin/env python3
"""Recut a retarget package's limbs and torso from its OWN fine zones, from the original sprite pixels.

    python3 recut_by_zones.py <package> <inputs>

<inputs> holds sprites.png, fine.png, fine.json (the zones the package was cut from). The package profile's
zoneRowShift says how each zone cell lines up with the sheet.

What is cut, and from where
  Arms (all facings; the near arm in side views): the idle cell. Joints from this body's zones, not another
  character's proportions: shoulder = centre of the shoulder cap (the joint of the Orc sword-and-shield draft);
  the cap stays on the body and the arm piece keeps a round end of cap pixels about the pivot; elbow = centre of
  the pixels where upper-arm and forearm zones touch, wrist = where forearm and hand touch, hand = centre of the
  fist. Pieces are the zone pixels; upper arm and forearm also carry each other's skin within 2.5 px of the
  elbow, so a bent elbow shows drawn arm.
  Legs (front/back): the idle cell, the same way around the knee. The shorts legs ride on the thighs (the Orc's
  shorts reach the knee), the pelvis is the waistband. Side legs: the shorts below the waistband are split between
  the two legs at the midpoint between the shins (near shin at the back, far at the front); the far shin and
  foot reuse the near leg's pieces from the far knee.
  Far arm (side views): the idle cell hides it. It reuses the near arm's three pieces, with the near rest joints
  as source pivots, on a chain mirrored to the front of the body where the torso hides it at rest.
  Torso and shorts (side views): the near arm and fist cover part of them in the idle cell. Those pixels come from
  the walk frames of the same facing, where the arm has swung clear, with that frame's own body outline, lined up
  by best match on the visible torso. Pixels no frame shows are copied from the nearest body pixel of the row and
  counted in recut-report.json.

The one place pixels are added: piece ends that another piece covers at rest (the upper arm under the forearm,
the forearm under the fist, thigh under shorts and shin, shin under foot) are rounded to the limb's width and
closed with the sprite's own outline colour, as the Elf's "rounded complete limb ends" are. Hidden at rest; seen
only when the joint bends. No skin is painted, no colour is changed.
"""
import json
import os
import sys
from collections import Counter

import numpy as np
from PIL import Image

LIMB = ('upper arm', 'forearm', 'hand')
ARM_ZONES = [f'{p} {s}' for p in LIMB for s in 'RL']
# The shoulder caps (deltoids) stay on the body, as in the Orc sword-and-shield draft; the arm pivots under them.
BODY = ('neck', 'chest', 'belly', 'hips', 'shoulder R', 'shoulder L')
TORSO = ('neck', 'chest', 'belly', 'shoulder R', 'shoulder L')
DARK = 60


# ----------------------------------------------------------------------------------------------- basics
def load(inputs, shift):
    sheet = np.array(Image.open(os.path.join(inputs, 'sprites.png')).convert('RGBA'))
    zones_raw = np.array(Image.open(os.path.join(inputs, 'fine.png')).convert('P'))
    names = json.load(open(os.path.join(inputs, 'fine.json')))['zones']
    zones = np.zeros_like(zones_raw)
    for d in range(4):
        for f in range(3):
            dy = shift.get('SNEW'[d] + str(f), 0)
            b = zones_raw[f * 64:(f + 1) * 64, d * 64:(d + 1) * 64]
            m = np.roll(b, dy, 0)
            if dy < 0:
                m[dy:] = 0
            elif dy > 0:
                m[:dy] = 0
            zones[f * 64:(f + 1) * 64, d * 64:(d + 1) * 64] = m
    return sheet, zones, names


def skeleton_file(inputs):
    """The staged skeleton in <inputs>: the one JSON there with per-cell joints (rig/<Race>.json)."""
    for f in sorted(os.listdir(inputs)):
        if f.endswith('.json') and f != 'fine.json':
            try:
                data = json.load(open(os.path.join(inputs, f)))
            except ValueError:
                continue
            if isinstance(data, dict) and 'cells' in data:
                return f
    return None


def skeleton(inputs, d, shift, f=0):
    """Joints of one cell from the staged skeleton, moved into sheet rows by zoneRowShift."""
    name = skeleton_file(inputs)
    if not name:
        return {}
    cells = json.load(open(os.path.join(inputs, name))).get('cells', {})
    key = 'SNEW'[d] + str(f)
    dy = shift.get(key, 0)
    out = {}
    for k, v in cells.get(key, {}).get('joints', {}).items():
        out[k] = None if v is None else [float(v[0]), float(v[1]) + dy]
    return out


def cell(a, d, f=0):
    return a[f * 64:(f + 1) * 64, d * 64:(d + 1) * 64]


def adopt(z, px):
    """Opaque pixels the zones left unlabelled (mostly outline) join the zone most of their neighbours have."""
    z = z.copy()
    for _ in range(6):
        todo = (px[:, :, 3] > 0) & (z == 0)
        if not todo.any():
            break
        new = z.copy()
        for y, x in zip(*np.nonzero(todo)):
            nb = z[max(0, y - 1):y + 2, max(0, x - 1):x + 2]
            nb = nb[nb > 0]
            if len(nb):
                new[y, x] = np.bincount(nb).argmax()
        z = new
    return z


def zm(z, names, wanted):
    return np.isin(z, [i for i, n in enumerate(names) if n in wanted])


def opaque(px):
    return px[:, :, 3] > 0


def solid(px):
    """Body pixels proper; the sheet's faint anti-alias fringe (alpha below 128) is left out of edge tests."""
    return px[:, :, 3] >= 128


def dark(px):
    return opaque(px) & (px[:, :, :3].astype(int).sum(2) < DARK)


def skin(px):
    return opaque(px) & ~dark(px)


def adjacent(m):
    out = np.zeros_like(m)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def centre(m):
    ys, xs = np.nonzero(m)
    return [float(xs.mean() + .5), float(ys.mean() + .5)]


def contact(a, b):
    """Centre of the pixels of a and b that touch each other."""
    t = (a & adjacent(b)) | (b & adjacent(a))
    return centre(t) if t.any() else None


def disc(c, r):
    ys, xs = np.mgrid[0:64, 0:64]
    return np.hypot(xs + .5 - c[0], ys + .5 - c[1]) <= r


def placed(m, a0, a1, b0, b1):
    """Mask m moved by the rotation+translation that takes segment a0->a1 onto b0->b1 (as the engine places a
    reused piece), for the covered-at-rest tests."""
    import math
    ang = math.atan2(b1[1] - b0[1], b1[0] - b0[0]) - math.atan2(a1[1] - a0[1], a1[0] - a0[0])
    ca, sa = math.cos(ang), math.sin(ang)
    out = np.zeros_like(m)
    for y, x in zip(*np.nonzero(m)):
        px_, py_ = x + .5 - a0[0], y + .5 - a0[1]
        nx, ny = b0[0] + px_ * ca - py_ * sa, b0[1] + px_ * sa + py_ * ca
        ix, iy = int(np.floor(nx)), int(np.floor(ny))
        if 0 <= ix < 64 and 0 <= iy < 64:
            out[iy, ix] = True
    return out


def piece(px, m):
    out = np.zeros_like(px)
    out[m] = px[m]
    return out


def top_rows(m, n):
    ys = np.nonzero(m.any(1))[0]
    out = np.zeros_like(m)
    out[ys.min():ys.min() + n] = m[ys.min():ys.min() + n]
    return out


def outline_colour(px, m):
    """The piece's own outline colour: the most common solid dark pixel (the sheet's faint black fringe, alpha 1-127,
    would otherwise win and make every closure invisible)."""
    cols = Counter(tuple(int(v) for v in px[y, x]) for y, x in zip(*np.nonzero(m & dark(px) & (px[:, :, 3] >= 128))))
    return cols.most_common(1)[0][0] if cols else (0, 0, 0, 255)


def rint(p):
    return [round(float(p[0]), 2), round(float(p[1]), 2)]


# ----------------------------------------------------------------------------------------------- pieces
def complete_end(img, joint, other, outline, covered, draw_outline=True):
    """The end of a piece beyond `joint` (away from `other`): rounded to the limb's width there and closed with the
    outline colour. Only pixels the next piece covers at rest (`covered`) are changed, so the idle pose stays
    pixel-identical."""
    op = opaque(img)
    ys, xs = np.nonzero(op)
    if len(xs) == 0:
        return img
    j, o = np.array(joint, float), np.array(other, float)
    v = j - o
    n = np.hypot(*v)
    if n < 1e-6:
        return img
    u = v / n
    p = np.stack([xs + .5, ys + .5], 1) - j
    t = p @ u
    on_line = np.abs(t) <= 0.75
    width = max(2, int(on_line.sum()))
    r = max(1.5, width / 2 + .25)
    beyond = t > 0
    cov = covered[ys, xs]
    far = beyond & (np.hypot(*p.T) > r) & cov
    out = img.copy()
    out[ys[far], xs[far]] = 0
    end = np.zeros((64, 64), bool)
    end[ys[beyond & ~far & cov], xs[beyond & ~far & cov]] = True
    if draw_outline:
        edge = end & adjacent(~opaque(out)) & ~dark(out) & solid(out)     # never turn a faint fringe pixel solid
        out[edge] = outline
    return out


def arm_chain(z, names, S, skel):
    """Joints from this body's staged skeleton (shoulder = where the arm meets the body under the cap, elbow,
    wrist); the grip point is halfway from the wrist into the fist. Pieces are the zone pixels. An earlier cut put
    the shoulder on the arm's outer top, which swung the whole arm off the body at every bend."""
    cap = zm(z, names, [f'shoulder {S}'])
    up = zm(z, names, [f'upper arm {S}'])
    fo = zm(z, names, [f'forearm {S}'])
    ha = zm(z, names, [f'hand {S}'])
    if up.sum() < 10 or fo.sum() < 10 or ha.sum() < 6:
        return None
    s, e, w = skel.get('shoulder' + S), skel.get('elbow' + S), skel.get('wrist' + S)
    if not (s and e and w):
        return None
    c = centre(ha)
    h = [(w[0] + c[0]) / 2, (w[1] + c[1]) / 2]
    width = max(3, int(top_rows(up, 2).sum() / 2))
    up = up | (cap & disc(s, width / 2 + .5))   # a round shoulder end under the cap, so a raised arm keeps its shoulder
    return {'chain': [s, e, h], 'wrist': w, 'up': up, 'fo': fo, 'ha': ha, 'cap': cap}


def arm_pieces(px, a, north, body_m):
    s, e, h = a['chain']
    near = disc(e, 2.5) & skin(px)
    up_m = a['up'] | (a['fo'] & near)
    fo_m = (a['fo'] | (a['up'] & near)) & ~a['ha']
    ha_m = a['ha']
    up, fo, ha = piece(px, up_m), piece(px, fo_m), piece(px, ha_m)
    oc = outline_colour(px, a['up'] | a['fo'] | a['ha'])
    # Shoulder end: rounded about the pivot. The cap pixels the arm carries are the body's own cap pixels, so
    # rounding them changes nothing at rest. The engine draws the North arms behind the body, so there the end is
    # also closed with the outline (hidden under the cap at rest); in South and the side views the arm lies over
    # the body, so no outline is added there (it would show as a seam at rest).
    up = complete_end(up, s, e, oc, body_m, draw_outline=north)
    if north:                       # North draws forearm, upper arm, hand: the forearm's top end is covered
        fo = complete_end(fo, e, h, oc, up_m)
        up = complete_end(up, e, s, oc, fo_m, draw_outline=False)   # its end past the elbow lies over the forearm
    else:                           # elsewhere upper arm, forearm, hand: the upper arm's lower end is covered
        up = complete_end(up, e, s, oc, fo_m)
    fo = complete_end(fo, a['wrist'], e, oc, ha_m)   # under the fist
    # backing into the piece drawn after it, so separately rotated pieces leave no pin-holes along their seam
    fo, _ = backing(px, fo, opaque(fo), ha_m & ~opaque(fo))                       # forearm under the fist
    if north:                                                                     # North: forearm under the upper arm
        fo, _ = backing(px, fo, opaque(fo), up_m & ~opaque(fo), width=1)
    else:                                                                         # elsewhere: upper arm under the forearm
        up, _ = backing(px, up, opaque(up), fo_m & ~opaque(up), width=1)
    return {'UpperArm': up, 'Forearm': fo, 'Hand': ha}


def leg_chain(z, names, S, skel):
    th = zm(z, names, [f'thigh {S}'])
    sh = zm(z, names, [f'shin {S}'])
    ft = zm(z, names, [f'foot {S}'])
    if th.sum() < 10 or sh.sum() < 10 or ft.sum() < 6:
        return None
    hip, knee, ankle = skel.get('hip' + S), skel.get('knee' + S), skel.get('ankle' + S)
    if not (hip and knee and ankle):
        hip = centre(top_rows(th, 2))
        knee = contact(th, sh) or centre(sh)
        ankle = contact(sh, ft) or centre(ft)
    # The renderer bends front/back knees outward (away from the body's centre line). The Orc's drawn knees sit
    # about a pixel inward of the hip-ankle line, and a knee on the wrong side of that line is flipped across it by
    # the two-bone IK (3 px here), so the rest leg would not match the drawing. The chain's knee is therefore the
    # skeleton knee's height on the hip-ankle line (a straight rest leg); the pieces are still cut at the drawn knee.
    vx, vy = ankle[0] - hip[0], ankle[1] - hip[1]
    if abs(vy) > 1e-6:
        t = (knee[1] - hip[1]) / vy
        knee = [hip[0] + vx * t, knee[1]]
    return {'chain': [hip, knee, ankle], 'th': th, 'sh': sh, 'ft': ft}


def leg_pieces(px, l, pelvis_m):
    hip, knee, ankle = l['chain']
    near = disc(knee, 2.0) & skin(px)
    th_m = l['th'] | (l['sh'] & near)
    sh_m = (l['sh'] | (l['th'] & near)) & ~l['ft']
    ft_m = l['ft']
    th, sh, ft = piece(px, th_m), piece(px, sh_m), piece(px, ft_m)
    oc = outline_colour(px, l['th'] | l['sh'] | l['ft'])
    th = complete_end(th, knee, hip, oc, sh_m)        # under the shin
    th = complete_end(th, hip, knee, oc, pelvis_m)    # under the waistband
    sh = complete_end(sh, ankle, knee, oc, ft_m)      # under the foot
    # backing into the next piece down (drawn over it), so a bent knee or ankle opens no pin-holes
    th, _ = backing(px, th, opaque(th), sh_m & ~opaque(th))
    sh, _ = backing(px, sh, opaque(sh), ft_m & ~opaque(sh))
    return {'Thigh': th, 'Shin': sh, 'Foot': ft}


# ----------------------------------------------------------------------------------------------- side body
def best_shift(dst_px, dst_m, src_px, src_m, r=4):
    best, score = (0, 0), -1
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            sm = np.roll(np.roll(src_m, dy, 0), dx, 1)
            sp = np.roll(np.roll(src_px, dy, 0), dx, 1)
            both = sm & dst_m
            same = both & (np.abs(sp[:, :, :3].astype(int) - dst_px[:, :, :3].astype(int)).sum(2) <= 12)
            sc = int(same.sum())
            if sc > score:
                best, score = (dx, dy), sc
    return best


HEAD = ('skull', 'face', 'ears', 'horns', 'hair')


def runs(row, gap=1):
    """(start, end) of the True runs in a 1-D mask, joining runs separated by at most `gap` False pixels."""
    xs = np.nonzero(row)[0]
    out = []
    for x in xs:
        if out and x - out[-1][1] <= gap + 1:
            out[-1][1] = x
        else:
            out.append([x, x])
    return [tuple(r) for r in out]


def jaw_chin(px, base_rows_bottom, cols, d):
    """The chin the zones leave on the chest, cut along the jaw outline the artist drew. The jaw's bottom outline is
    the longest dark run (1-px gaps allowed) 2-6 rows under the head zones, within the head's columns; from its back
    end(s) a crease runs up to the head's bottom row (the nearest dark pixel there). The chin is everything between
    the crease line(s) and the silhouette, down to the jaw outline and its second row. South has a crease on each
    side; East's crease is on its left (the back), West's on its right; North shows the back of the head: no chin."""
    m = np.zeros((64, 64), bool)
    if d == 1:
        return m
    hb = base_rows_bottom
    dk = dark(px)
    op = opaque(px)
    cx0, cx1 = cols
    best = None
    for y in range(hb + 2, min(64, hb + 7)):
        for a, b in runs(dk[y, cx0:cx1 + 1]):
            a, b = a + cx0, b + cx0
            if best is None or b - a > best[3] - best[2]:
                best = (b - a + 1, y, a, b)
    if not best or best[0] < 5:
        return m
    _, jy, ja, jb = best
    left_crease, right_crease = d in (0, 2), d in (0, 3)
    row = np.nonzero(dk[hb + 1])[0]
    xl = max([x for x in row if x < ja], default=None) if left_crease else None
    xr = min([x for x in row if x > jb], default=None) if right_crease else None
    if (left_crease and xl is None) or (right_crease and xr is None):
        return m
    for y in range(hb + 1, jy + 1):
        t = (y - (hb + 1)) / max(1, jy - (hb + 1))
        lo = int(np.floor(xl + (ja - xl) * t)) if left_crease else cx0
        hi = int(np.ceil(xr + (jb - xr) * t)) if right_crease else cx1
        m[y, max(0, lo):hi + 1] = True
    m &= op
    m[jy + 1, ja:jb + 1] |= dk[jy + 1, ja:jb + 1]                      # the jaw outline's second row
    m |= dk & adjacent(m) & (np.arange(64)[:, None] > hb) & (np.arange(64)[:, None] <= jy)   # crease pixels just off the line
    return m


def head_mask(px, z, names, d=None):
    """The whole head: the head zones, the 'neck' rows (on this big-headed body they are inside the face), the
    tusks (white pixels just under them, within the face's width) and, given the facing d, the chin down to the
    jaw outline (jaw_chin). Without the chin the jaw stayed on the torso and split off when the head moved."""
    m = zm(z, names, HEAD)
    neck = zm(z, names, ['neck'])
    m |= neck
    rows = np.nonzero(m.any(1))[0]
    cols = np.nonzero(zm(z, names, ['face', 'skull']).any(0))[0]
    if len(rows) and len(cols):
        white = opaque(px) & (px[:, :, :3].astype(int).min(2) > 200)
        box = np.zeros_like(m)
        box[rows.max() + 1:rows.max() + 4, cols.min() - 1:cols.max() + 2] = True
        if d is not None:
            m |= jaw_chin(px, int(rows.max()), (int(cols.min()), int(cols.max())), d)
        m |= white & box
    return m


def under_head_fill(px, torso, torso_m, head_m, chin_m, band=2):
    """Backing for the torso under the head: the chin and the head's bottom `band` rows get torso pixels copied from
    the first skin pixel below in the same column (or the nearest torso skin of the row), and the body's outline
    colour where they sit on the silhouette. Hidden while the head sits as drawn; when the head tilts or lifts with a
    lean, the neck and shoulders stay whole instead of opening a gap or leaving a copy of the jaw behind."""
    out = torso.copy()
    op = solid(px)
    dk = dark(px)
    edge = op & adjacent(~op)
    oc = outline_colour(px, torso_m)
    want = chin_m.copy()
    for x in range(64):
        hy = np.nonzero(head_m[:, x])[0]
        # only where the torso continues straight under the head (not under the ear tips or the cheeks' overhang)
        if len(hy) and torso_m[hy.max() + 1:hy.max() + 3, x].any():
            want[max(0, hy.max() - band + 1):hy.max() + 1, x] |= head_m[max(0, hy.max() - band + 1):hy.max() + 1, x]
    want &= op                                   # no faint fringe pixels in the backing
    filled = np.zeros((64, 64), bool)
    for y, x in zip(*np.nonzero(want)):
        if edge[y, x]:
            out[y, x] = oc
        else:
            src = next((yy for yy in range(y + 1, min(64, y + 12)) if torso_m[yy, x] and not dk[yy, x] and not want[yy, x] and op[yy, x]), None)
            if src is not None:
                out[y, x] = px[src, x]
            else:
                xs = np.nonzero(torso_m[y] & ~dk[y] & ~want[y] & op[y])[0]
                if not len(xs):
                    continue
                out[y, x] = px[y, xs[int(np.argmin(np.abs(xs - x)))]]
        filled[y, x] = True
    return out, filled


def backing(px, img, m, toward, width=2):
    """Extend a piece by up to `width` px into `toward`, the region another piece covers at rest: the new pixels copy
    the piece's nearest own skin pixel, and its new outer edge takes the piece's outline colour. Hidden while the
    pose is as drawn; when the neighbour swings or tilts away, the piece shows a closed edge instead of a gap."""
    out = img.copy()
    grown = m.copy()
    new = np.zeros_like(m)
    toward = toward & solid(px)
    for _ in range(width):
        ring = adjacent(grown) & toward & ~grown
        new |= ring
        grown |= ring
    if not new.any():
        return out, new
    sk = m & skin(px) & solid(px)
    ys, xs = np.nonzero(sk)
    if not len(ys):
        return out, np.zeros_like(m)
    for y, x in zip(*np.nonzero(new)):
        k = int(np.argmin((ys - y) ** 2 + (xs - x) ** 2))
        out[y, x] = px[ys[k], xs[k]]
    out[new & adjacent(~grown)] = outline_colour(px, m)
    return out, new


def side_arm_chain(z, names, S, skel, neck, waist):
    """Side views: the arm hangs from the top of the body. The staged skeleton puts this shoulder where the staged
    zones start the 'upper arm', a third of the way down the arm (those side zones label the arm's top as chest),
    so the joint is matched to the body here: a quarter of the way from the neck to the waist (where the Elf and
    the approved Human have it, and where the Orc's own walk frames swing the arm from), at the centre of the arm in
    that row. Elbow and wrist are the skeleton's. The upper-arm piece is the arm from that row down plus a round
    end of the arm's width about the joint; the shoulder's top above it stays on the torso."""
    cap = zm(z, names, [f'shoulder {S}'])
    up = zm(z, names, [f'upper arm {S}'])
    fo = zm(z, names, [f'forearm {S}'])
    ha = zm(z, names, [f'hand {S}'])
    if up.sum() < 10 or fo.sum() < 10 or ha.sum() < 6:
        return None
    top = cap | up
    sy = float(neck[1] + .25 * (waist[1] - neck[1]))
    r0 = int(np.floor(sy))
    xs = np.nonzero(top[max(0, r0 - 1):r0 + 2].any(0))[0]
    if not len(xs):
        return None
    s = [float(xs.min() + xs.max() + 1) / 2, sy]
    rad = float(xs.max() - xs.min() + 1) / 2
    e = skel.get('elbow' + S) or contact(up, fo) or centre(fo)
    w = skel.get('wrist' + S) or contact(fo, ha) or centre(ha)
    c = centre(ha)
    h = [(w[0] + c[0]) / 2, (w[1] + c[1]) / 2]
    yy = np.arange(64)[:, None] + .5
    up_m = top & ((yy > sy) | disc(s, rad))
    return {'chain': [s, e, h], 'wrist': w, 'up': up_m, 'fo': fo, 'ha': ha, 'cap': top & ~up_m, 'radius': rad}


def forward_arm_frame(sheet, zones, names, d, S):
    """The walk frame in which the near arm swings forward, clear of the back: there the back and the seat of the
    shorts, hidden behind the hanging arm in the idle cell, are drawn (with their outline)."""
    best, score = None, None
    for g in (1, 2):
        spx = cell(sheet, d, g)
        sz = adopt(cell(zones, d, g), spx)
        m = zm(sz, names, [f'forearm {S}', f'hand {S}'])
        if not m.any():
            continue
        x = centre(m)[0]
        sc = x if d == 2 else -x               # East faces +x, West faces -x
        if score is None or sc > score:
            best, score = g, sc
    return best


def side_torso(sheet, zones, names, d, arm, head_m, chin_m):
    """Side views: the torso without the near arm. The arm hangs over the side of the body, so the back behind it is
    never drawn in the idle cell. It is taken from the walk frame in which the near arm swings forward (that frame's
    own arm zones, widened by a pixel, left out), lined up on the visible torso, with that frame's own back outline;
    pixels it does not show are copied from the nearest torso skin of the row, and any new edge is closed with the
    outline colour. An earlier build drew an invented back curving in to the visible edge of the shorts; when the
    arm lifted, the body caved in behind the hips. The shoulder's top above the arm joint stays as drawn."""
    px = cell(sheet, d)
    z = adopt(cell(zones, d), px)
    op = opaque(px)
    sk = skin(px) & solid(px)
    S = 'R' if d == 2 else 'L'
    arm_px = arm['up'] | arm['fo'] | arm['ha']
    hips = zm(z, names, ['hips'])
    y_waist = int(np.nonzero(hips.any(1))[0].min())
    body = (zm(z, names, ('neck', 'chest', 'belly')) | arm['cap']) & op
    own = body & ~arm_px & ~head_m
    rows_ok = np.zeros((64, 64), bool)
    rows_ok[int(np.nonzero(body.any(1))[0].min()):y_waist] = True
    used = {}
    shift = None
    g = forward_arm_frame(sheet, zones, names, d, S)
    out = piece(px, own)
    src = None
    if g is not None:
        spx = cell(sheet, d, g)
        sz = adopt(cell(zones, d, g), spx)
        s_arm = zm(sz, names, ARM_ZONES)
        s_arm = s_arm | adjacent(s_arm)
        s_body = zm(sz, names, ('neck', 'chest', 'belly', 'shoulder R', 'shoulder L')) & ~s_arm & ~head_mask(spx, sz, names, d) & solid(spx)
        s_m = s_body | (dark(spx) & solid(spx) & adjacent(s_body) & ~s_arm)
        dx, dy = best_shift(px, own & sk, spx, s_body & skin(spx))
        src = (np.roll(np.roll(spx, dy, 0), dx, 1), np.roll(np.roll(s_m, dy, 0), dx, 1))
        used['source'] = 'walk frame %d, shift %d,%d' % (g, dx, dy)
        shift = (int(dx), int(dy))
    # the torso: the idle body, plus the source frame's body where the idle arm hangs (rows above the waist)
    T = own.copy()
    cols = np.arange(64)[None, :]
    ax = np.nonzero(arm_px.any(0))[0]
    back_side = (cols <= ax.max()) if d == 2 else (cols >= ax.min())     # behind the arm's front edge only
    if src is not None:
        T |= src[1] & rows_ok & back_side & ~head_m & ~own
    T |= arm_px & rows_ok & solid(px) & ~head_m & adjacent(own)      # keep the torso closed up to the arm's inner edge
    # The back between the drawn shoulder and the seat of the shorts: a line from the silhouette's back edge two rows
    # under the arm joint down to the back edge of the seat (the walk frame's shorts) at the waist, so the back does
    # not dip in where the hanging arm used to be. The arm's elbow bulge stays outside it.
    if src is not None and shift is not None:
        g_px = cell(sheet, d, g)
        g_z = adopt(cell(zones, d, g), g_px)
        g_h = np.roll(np.roll(zm(g_z, names, ['hips']) & solid(g_px), shift[1], 0), shift[0], 1)
        hy = np.nonzero(hips.any(1))[0]
        y0 = int(np.floor(arm['chain'][0][1])) + 2
        ys = np.nonzero(sk[y0])[0]
        seat_row = g_h[y_waist:y_waist + 3].any(0)
        if len(ys) and seat_row.any():
            sx = np.nonzero(seat_row)[0]
            x0 = (ys.min() - 1) if d == 2 else (ys.max() + 1)
            x1 = (sx.min() - 1) if d == 2 else (sx.max() + 1)
            hx = np.nonzero(hips.any(0))[0]
            for y in range(y0 + 1, y_waist + 2):
                t = min(1.0, (y - y0) / max(1, y_waist - y0))
                xb = int(round(x0 + (x1 - x0) * t))
                row = np.zeros(64, bool)
                if d == 2:
                    row[max(0, xb):] = True
                else:
                    row[:xb + 1] = True
                if y >= y_waist:                       # the waistband rows: only behind the drawn shorts
                    row &= (np.arange(64) < hx.min()) if d == 2 else (np.arange(64) > hx.max())
                T[y] |= row & solid(px)[y] & ~head_m[y] & back_side[0]
                used['back line'] = used.get('back line', 0) + 1
    hidden = T & ~own
    done = np.zeros((64, 64), bool)
    if src is not None:
        m = hidden & src[1] & (src[0][:, :, 3] >= 128)
        out[m] = src[0][m]
        done |= m
        used['from source'] = int(m.sum())
    left = hidden & ~done
    for y, x in zip(*np.nonzero(left)):
        xs = np.nonzero(solid(out[y:y + 1])[0] & ~dark(out[y:y + 1])[0] & ~left[y])[0]
        if len(xs):
            out[y, x] = out[y, xs[int(np.argmin(np.abs(xs - x)))]]
            used['row copy'] = used.get('row copy', 0) + 1
    # close any new edge (filled pixels on the torso's silhouette) with the outline colour
    oc = outline_colour(px, body)
    tm = opaque(out)
    edge = hidden & tm & adjacent(~tm) & ~dark(out)
    out[edge] = oc
    used['edge closed'] = int(edge.sum())
    # drop loose bits (1-3 px islands the zones left on the torso, e.g. a scrap of the arm's back outline)
    out = drop_islands(out, 4)
    torso_m = opaque(out)
    out, filled = under_head_fill(px, out, torso_m, head_m, chin_m)
    used['under head'] = int(filled.sum())
    return out, used, (g, shift)


def side_seat(sheet, zones, names, d, hips, seat_src):
    """The seat of the side shorts, hidden behind the hanging fist in the idle cell, from the same walk frame as the
    torso's back: that frame's shorts (with their outline) behind the idle shorts' back edge, lined up with the same
    shift. It goes on the pelvis, so it stays put while the thighs swing; at rest the fist covers it."""
    g, shift = seat_src
    seat = np.zeros((64, 64, 4), np.uint8)
    if g is None or shift is None:
        return seat
    spx = cell(sheet, d, g)
    sz = adopt(cell(zones, d, g), spx)
    s_arm = zm(sz, names, ARM_ZONES)
    s_h = zm(sz, names, ['hips']) & solid(spx) & ~s_arm
    s_m = s_h | (dark(spx) & solid(spx) & adjacent(s_h) & ~adjacent(s_arm))
    dx, dy = shift
    spx = np.roll(np.roll(spx, dy, 0), dx, 1)
    s_m = np.roll(np.roll(s_m, dy, 0), dx, 1)
    hx = np.nonzero(hips.any(0))[0]
    cols = np.arange(64)[None, :]
    behind = (cols < hx.min()) if d == 2 else (cols > hx.max())
    rows = np.nonzero(hips.any(1))[0]
    band = np.zeros((64, 64), bool)
    band[rows.min():rows.max() + 1] = True
    m = s_m & behind & band
    seat[m] = spx[m]
    return seat


def drop_islands(img, min_px):
    """Remove 4-connected opaque islands smaller than min_px pixels."""
    m = opaque(img)
    seen = np.zeros_like(m)
    out = img.copy()
    for y, x in zip(*np.nonzero(m)):
        if seen[y, x]:
            continue
        stack, comp = [(y, x)], []
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            comp.append((cy, cx))
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < 64 and 0 <= nx < 64 and m[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(comp) < min_px:
            for cy, cx in comp:
                out[cy, cx] = 0
    return out


def side_walk_body(sheet, zones, names, d, f, torso, seat=None):
    """Side views, drawn frames (idle, walk): this frame's own shorts and legs and its own head (with the chin), and
    the side torso lined up on this frame's chest. The engine draws the arms as pieces over and behind it."""
    pxf = cell(sheet, d, f)
    zf = adopt(cell(zones, d, f), pxf)
    hmf = head_mask(pxf, zf, names, d)
    legs_m = zm(zf, names, ['hips', 'thigh R', 'shin R', 'foot R', 'thigh L', 'shin L', 'foot L', 'tail']) & ~hmf
    out = piece(pxf, legs_m)
    if f == 0:
        dx = dy = 0
    else:
        chest = zm(zf, names, ('chest', 'belly')) & skin(pxf) & ~adjacent(zm(zf, names, ARM_ZONES))
        dx, dy = best_shift(pxf, chest, torso, opaque(torso) & skin(torso), r=3)
    if seat is not None:                      # the shorts' seat behind the fist, under this frame's own shorts
        sm = np.roll(np.roll(seat, dy, 0), dx, 1)
        mm = opaque(sm) & ~opaque(out)
        out[mm] = sm[mm]
    t = np.roll(np.roll(torso, dy, 0), dx, 1)
    m = opaque(t)
    out[m] = t[m]
    return out, piece(pxf, hmf), (int(dx), int(dy))


def body_base(sheet, zones, names, d, f, own_zones):
    """Cell (d, f)'s own body pixels, plus the body the arms hide, taken from the other frames of the facing."""
    px = cell(sheet, d, f)
    z = adopt(cell(zones, d, f), px)
    own = zm(z, names, own_zones) & ~head_mask(px, z, names)
    arms = zm(z, names, ARM_ZONES)
    rows = np.nonzero(own.any(1))[0]
    row_ok = np.zeros(64, bool)
    row_ok[rows.min():rows.max() + 1] = True
    hidden = arms & row_ok[:, None] & opaque(px)
    arm_edge = own & dark(px) & adjacent(arms)          # the arm's outline that the zones gave to the body
    out = piece(px, own)
    sources = []
    for g in range(3):
        if g == f:
            continue
        spx = cell(sheet, d, g)
        sz = adopt(cell(zones, d, g), spx)
        body_g = zm(sz, names, own_zones)
        src_m = body_g | (dark(spx) & adjacent(body_g))   # the frame's body with its outline, whoever it touches
        dx, dy = best_shift(px, own & ~arm_edge, spx, body_g & skin(spx))
        sources.append((np.roll(np.roll(spx, dy, 0), dx, 1), np.roll(np.roll(src_m, dy, 0), dx, 1), (g, dx, dy)))
    sources.sort(key=lambda s: -int((s[1] & hidden).sum()))
    used = {}
    want = hidden | arm_edge
    for y, x in zip(*np.nonzero(want)):
        for spx, sm, tag in sources:
            if sm[y, x]:
                out[y, x] = spx[y, x]
                used[str(tag)] = used.get(str(tag), 0) + 1
                break
    # pixels inside the drawn body that no frame shows are copied from the nearest body pixel of the row
    filled = opaque(out)
    is_dark = dark(out)
    added_copy = np.zeros((64, 64), bool)
    for y in rows:
        xs = np.nonzero(filled[y])[0]
        if len(xs) == 0:
            continue
        lo, hi = xs.min(), xs.max()
        for x in np.nonzero(hidden[y])[0]:
            if lo <= x <= hi and not filled[y, x]:
                src = [xx for xx in xs if not is_dark[y, xx]]
                if src:
                    out[y, x] = out[y, src[int(np.argmin(np.abs(np.array(src) - x)))]]
                    added_copy[y, x] = True
                    used['row-copy'] = used.get('row-copy', 0) + 1
    out[~opaque(px)] = 0                                 # never wider than the drawn cell
    oc = outline_colour(px, own)
    edge = added_copy & adjacent(~opaque(out))           # a copied pixel on the body's edge gets the outline colour
    out[edge] = oc
    return out, used


# ----------------------------------------------------------------------------------------------- main
def main(pkg, inputs):
    pp = os.path.join(pkg, 'profiles/character.json')
    p = json.load(open(pp))
    sheet, zones, names = load(inputs, p.get('zoneRowShift', {}))
    assets = os.path.join(pkg, 'preview/assets')
    report = {'rule': 'original sprite pixels; joints from this body\'s zones; covered piece ends rounded and '
                      'closed with the outline colour', 'views': []}

    def save(name, im):
        Image.fromarray(im).save(os.path.join(assets, name))
        return name

    skel_name = skeleton_file(inputs)
    if not skel_name:
        sys.exit('no staged skeleton (a JSON with per-cell joints) in ' + inputs)
    for d, v in enumerate(p['views']):
        px = cell(sheet, d)
        z = adopt(cell(zones, d), px)
        skel = skeleton(inputs, d, p.get('zoneRowShift', {}))
        if not skel.get('shoulderR') and not skel.get('shoulderL'):
            sys.exit('skeleton %s has no joints for cell %s0' % (skel_name, 'SNEW'[d]))
        rv = {'view': v['name'], 'skeleton': 'inputs/%s %s0 (rows %+d)' % (skel_name, 'SNEW'[d], p.get('zoneRowShift', {}).get('SNEW'[d] + '0', 0))}
        ps = v.get('partSource', {})
        v.pop('smoothRotate', None)
        body_cols = np.nonzero(zm(z, names, BODY).any(0))[0]
        axis = (body_cols.min() + body_cols.max() + 1) / 2
        # ---- arms from the idle cell
        body_m = zm(z, names, BODY)
        chains = {}
        for side, S in (('right', 'R'), ('left', 'L')):
            a = side_arm_chain(z, names, S, skel, v['neck'], v['waist']) if d >= 2 else arm_chain(z, names, S, skel)
            if not a:
                continue
            chains[side] = a
            v['arms'][side] = [rint(pt) for pt in a['chain']]
            pieces = arm_pieces(px, a, d == 1, body_m)
            if d == 1:              # North draws the arms behind the body: back their body-side edge
                for k, mk in (('UpperArm', a['up']), ('Forearm', a['fo'])):
                    pieces[k], _ = backing(px, pieces[k], opaque(pieces[k]), body_m & ~opaque(pieces[k]))
            for k, im in pieces.items():
                v['parts'][side + k] = save(f'orc-{d}-{side}{k}.png', im)
                ps.pop(side + k, None)
            rv[side + 'Arm'] = v['arms'][side]
        # ---- far arm in side views
        if d >= 2:
            near = 'right' if d == 2 else 'left'
            far = 'left' if near == 'right' else 'right'
            if far not in chains:
                s, e, h = v['arms'][near]
                # the far shoulder sits just past the body's centre line, so the arm hangs inside the torso at rest
                fx = axis + (axis - s[0]) / 4
                v['arms'][far] = [rint([pt[0] + (fx - s[0]), pt[1] + 1]) for pt in (s, e, h)]
                for k, src in (('UpperArm', [s, e]), ('Forearm', [e, h]), ('Hand', [h, [h[0], h[1] + 1]])):
                    v['parts'][far + k] = v['parts'][near + k]
                    ps[far + k] = src
                rv['farArm'] = {'side': far, 'chain': v['arms'][far],
                                'from': 'the near arm pieces on a chain mirrored to the front of the body'}
        # ---- legs
        if d < 2:
            hips = zm(z, names, ['hips'])
            v['parts']['pelvis'] = save(f'orc-{d}-pelvis.png', piece(px, hips))   # waistband; shorts legs on the thighs
            hm = head_mask(px, z, names, d)
            chin = hm & ~head_mask(px, z, names)
            v['parts']['head'] = save(f'orc-{d}-head.png', piece(px, hm))
            tm = zm(z, names, TORSO) & ~hm                                   # with the shoulder caps
            torso, under = under_head_fill(px, piece(px, tm), tm, hm, chin, band=4)   # 4 rows: the East/West bow sets a side head here
            arm_region = np.zeros((64, 64), bool)
            for a in chains.values():
                arm_region |= a['up'] | a['fo'] | a['ha']
            side_back = np.zeros((64, 64), bool)
            if d == 0:              # South draws the arms over the body: back the torso's sides under them
                torso, side_back = backing(px, torso, tm, arm_region & ~tm, width=3)
            v['parts']['torso'] = save(f'orc-{d}-torso.png', torso)
            pel = piece(px, hips)
            ptop = int(np.nonzero(hips.any(1))[0].min())
            band = np.zeros((64, 64), bool)
            band[max(0, ptop - 2):ptop] = True
            pel, pel_back = backing(px, pel, hips, tm & band)
            v['parts']['pelvis'] = save(f'orc-{d}-pelvis.png', pel)
            rv['head'] = {'chinPixels': int(chin.sum()), 'torsoBackingUnderHead': int(under.sum())}
            rv['backing'] = {'torsoUnderArms': int(side_back.sum()), 'pelvisUnderTorso': int(pel_back.sum())}
            for f in range(3):
                pxf = cell(sheet, d, f)
                zf = adopt(cell(zones, d, f), pxf)
                hmf = head_mask(pxf, zf, names, d)
                body_m = zm(zf, names, TORSO + ('hips', 'thigh R', 'shin R', 'foot R', 'thigh L', 'shin L', 'foot L', 'tail')) & ~hmf
                body = piece(pxf, body_m)
                # The engine swings the idle arm pieces over this drawn frame, not the frame's own arms, so the
                # torso edge this frame's arms covered gets a 3-px backing (no slivers between torso and arm).
                if d == 0 or f > 0:   # North draws the arms behind the body: keep its idle frame exactly as drawn
                    body, _ = backing(pxf, body, zm(zf, names, TORSO) & ~hmf, zm(zf, names, ARM_ZONES) & ~body_m, width=3)
                v['walk'][f]['refined-torso'] = save(f'orc-{d}-walk-{f}-body.png', body)
                v['walk'][f]['render-head'] = save(f'orc-{d}-walk-{f}-head.png', piece(pxf, hmf))
            for side, S in (('right', 'R'), ('left', 'L')):
                l = leg_chain(z, names, S, skel)
                if not l:
                    continue
                v['legs'][side] = [rint(pt) for pt in l['chain']]
                for k, im in leg_pieces(px, l, hips).items():
                    v['parts'][side + k] = save(f'orc-{d}-{side}{k}.png', im)
                    ps.pop(side + k, None)
                rv[side + 'Leg'] = v['legs'][side]
        else:
            hm = head_mask(px, z, names, d)
            chin = hm & ~head_mask(px, z, names)
            v['parts']['head'] = save(f'orc-{d}-head.png', piece(px, hm))
            near_arm = 'right' if d == 2 else 'left'
            body, used, seat_src = side_torso(sheet, zones, names, d, chains[near_arm], hm, chin)
            v['parts']['torso'] = save(f'orc-{d}-torso.png', body)
            pel, used2 = body_base(sheet, zones, names, d, 0, ('hips',))
            rv['torsoFill'] = used
            rv['head'] = {'chinPixels': int(chin.sum())}
            # Side legs. The side shorts are one drawing over both thighs (rows 44-51 here): the top two rows are
            # the waistband and stay on the pelvis; the rest is split between the legs at the midpoint between the
            # two shins (the near shin is drawn at the back of the shorts, the far one at the front), so each leg
            # owns a thigh of one thigh's width and the idle composite is unchanged. An earlier build left the whole
            # shorts on the pelvis and gave the legs no thigh at all, so a stepping leg was a skin sliver and a foot.
            # The far shin and foot reuse the near leg's pieces with the near rest joints as source pivots (the
            # approved Human does the same; the far leg's own zones are slivers, a walk-frame far leg is a spike).
            near_leg = v['nearLeg']
            far_leg = 'left' if near_leg == 'right' else 'right'
            Sn = 'R' if near_leg == 'right' else 'L'
            Sf = 'L' if Sn == 'R' else 'R'
            hips = zm(z, names, ['hips'])
            top = int(np.nonzero(hips.any(1))[0].min())
            rows = np.arange(64)[:, None]
            cols = np.arange(64)[None, :] + .5
            waist_m = hips & (rows < top + 2)
            thigh_all = hips & ~waist_m
            sh_n, ft_n = zm(z, names, [f'shin {Sn}']), zm(z, names, [f'foot {Sn}'])
            sh_f, ft_f = zm(z, names, [f'shin {Sf}']), zm(z, names, [f'foot {Sf}'])
            cn, cf = centre(sh_n)[0], centre(sh_f)[0] if sh_f.any() else centre(sh_n)[0] + 6
            split = (cn + cf) / 2
            if cn <= cf:
                near_th, far_th = thigh_all & (cols <= split), thigh_all & (cols >= split - 1)
            else:
                near_th, far_th = thigh_all & (cols >= split), thigh_all & (cols <= split + 1)
            pel[~waist_m] = 0
            band = np.zeros((64, 64), bool)
            band[max(0, top - 2):top] = True
            pel, pel_back = backing(px, pel, waist_m, opaque(body) & band)
            seat = side_seat(sheet, zones, names, d, hips, seat_src)
            sm_ = opaque(seat) & ~opaque(pel)
            pel[sm_] = seat[sm_]
            rv['backing'] = {'pelvisUnderTorso': int(pel_back.sum()), 'seatFromWalkFrame': int(sm_.sum())}
            v['parts']['pelvis'] = save(f'orc-{d}-pelvis.png', pel)
            hip_n = skel.get('hip' + Sn) or centre(top_rows(near_th, 2))
            knee_n = skel.get('knee' + Sn) or contact(near_th, sh_n) or centre(top_rows(sh_n, 2))
            ankle_n = skel.get('ankle' + Sn) or contact(sh_n, ft_n) or centre(ft_n)
            hip_f = skel.get('hip' + Sf) or centre(top_rows(far_th, 2))
            knee_f = skel.get('knee' + Sf) or [hip_f[0] + (knee_n[0] - hip_n[0]), knee_n[1]]
            ankle_f = skel.get('ankle' + Sf) or [knee_f[0] + (ankle_n[0] - knee_n[0]), ankle_n[1]]
            oc = outline_colour(px, hips | sh_n | ft_n)
            # near leg: own thigh half, own shin and foot, closed where covered at rest
            near = disc(knee_n, 2.0) & skin(px)
            sh_m = (sh_n | (near_th & near)) & ~ft_n
            th = complete_end(piece(px, near_th), knee_n, hip_n, oc, sh_m)
            th = complete_end(th, hip_n, knee_n, oc, waist_m)
            sh = complete_end(piece(px, sh_m), ankle_n, knee_n, oc, ft_n)
            th, _ = backing(px, th, opaque(th), sh_m & ~opaque(th))      # into the shin, hidden under it at rest
            sh, _ = backing(px, sh, opaque(sh), ft_n & ~opaque(sh))      # into the foot
            v['parts'][near_leg + 'Thigh'] = save(f'orc-{d}-{near_leg}Thigh.png', th)
            v['parts'][near_leg + 'Shin'] = save(f'orc-{d}-{near_leg}Shin.png', sh)
            v['parts'][near_leg + 'Foot'] = save(f'orc-{d}-{near_leg}Foot.png', piece(px, ft_n))
            for k in ('Thigh', 'Shin', 'Foot'):
                ps.pop(near_leg + k, None)
            v['legs'][near_leg] = [rint(hip_n), rint(knee_n), rint(ankle_n)]
            # far leg: own thigh half; the near shin and foot placed from the far knee
            sh_f_rest = placed(sh_m, knee_n, ankle_n, knee_f, ankle_f)
            thf = complete_end(piece(px, far_th), knee_f, hip_f, oc, sh_f_rest)
            thf = complete_end(thf, hip_f, knee_f, oc, waist_m)
            thf, _ = backing(px, thf, opaque(thf), sh_f_rest & ~opaque(thf))
            v['parts'][far_leg + 'Thigh'] = save(f'orc-{d}-{far_leg}Thigh.png', thf)
            ps.pop(far_leg + 'Thigh', None)
            for k, src in (('Shin', [knee_n, ankle_n]), ('Foot', [ankle_n, [ankle_n[0], ankle_n[1] + 1]])):
                v['parts'][far_leg + k] = v['parts'][near_leg + k]
                ps[far_leg + k] = [rint(src[0]), rint(src[1])]
            v['legs'][far_leg] = [rint(hip_f), rint(knee_f), rint(ankle_f)]
            rv['sideLegs'] = {'split': round(float(split), 2), 'near': v['legs'][near_leg], 'far': v['legs'][far_leg],
                              'rule': 'thighs = shorts below the waistband, split between the shins; far shin and '
                                      'foot = near pieces from the far knee'}
            rv['walkTorsoShift'] = {}
            for f in range(3):
                wb, wh, sh = side_walk_body(sheet, zones, names, d, f, body, seat)
                v['walk'][f]['refined-torso'] = save(f'orc-{d}-walk-{f}-body.png', wb)
                v['walk'][f]['render-head'] = save(f'orc-{d}-walk-{f}-head.png', wh)
                rv['walkTorsoShift'][str(f)] = sh
        if ps:
            v['partSource'] = ps
        else:
            v.pop('partSource', None)
        report['views'].append(rv)
    json.dump(p, open(pp, 'w'), indent=2)
    json.dump(report, open(os.path.join(pkg, 'recut-report.json'), 'w'), indent=2)
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:3])
