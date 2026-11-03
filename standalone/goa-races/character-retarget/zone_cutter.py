#!/usr/bin/env python3
"""Cut a race's 15 rig parts per facing from its GOA sheet and fine zones, and write its profile.

    python3 tools/cut_from_finezones.py Human human-male "GOA Human male"

Inputs (read only), looked for in inputs/ first, then in the Dungeon-Master-master repository:
  sprites.png   256x192, columns S,N,E,W, rows idle / walk A / walk B, 64 px cells
  fine.png + fine.json   one body part per pixel (the game team's fine zones), same layout
  <Race>.json   the staged rig file (only its walk order is read; joints are measured here, see below)

Outputs:
  preview/assets/<slug>-<d>-<part>.png         15 parts per facing, 64x64, drawn at their source place
  preview/assets/<slug>-<d>-walk-<f>-*.png     drawn walk bodies (no arms, no head) and heads, 3 frames
  profiles/<slug>.json                          joints, grips, joint colours, action targets, part references

Second version, after the rig creator's review (README-REVIEW.md):
  * Joints are measured on the idle pixels, not taken from the zone boundaries. The zones only say which pixels
    belong to which arm or leg. Each hanging arm gets shoulder = 2 rows under its top, wrist = 3 rows above its
    bottom (6 in side views, where the fist is seen tall), elbow 8/15 of the way down, the same proportions as the
    approved Elf profile; x is the arm's centre on that row. Both arms therefore get the same physical length.
  * Segments overlap at the joints with the sprite's own pixels (upper arm runs 2 rows past the elbow, forearm
    starts 1 row above it and ends 2 rows into the fist, hand starts 2 rows above the wrist; legs alike), so a bent
    joint shows drawn shading and outlines, not a flat cap. The only invented pixels are surfaces the sheet never
    shows: thighs under the shorts (the leg's top rows carried up to the hip), the torso and shorts under a near
    arm or fist (mirrored from the other side in front/back views, carried across the row in side views), and the
    far arm of a side view (the near arm's parts moved behind the body by half the torso depth, recoloured with the
    sheet's own darker palette colours).
  * Outline = any near-black pixel (the sheet uses several near-black values).
"""
import json
import os
import sys
from collections import Counter

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RIG = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(RIG, '..', '..'))
STAGED = os.path.join(ROOT, 'standalone/remastered/reports/goa-sprite-test/staged')
FACINGS = ['South', 'North', 'East', 'West']
F = 'SNEW'
PARTS = ['head', 'torso', 'pelvis',
         'rightUpperArm', 'rightForearm', 'rightHand', 'leftUpperArm', 'leftForearm', 'leftHand',
         'rightThigh', 'rightShin', 'rightFoot', 'leftThigh', 'leftShin', 'leftFoot']
HEAD_ZONES = ['skull', 'face', 'ears', 'horns', 'hair']
BODY_ZONES = ['neck', 'chest', 'belly']
OUTLINE_SUM = 60  # r+g+b below this = outline
# Side legs from walk frame A instead of the idle cell (only needed when the idle cell hides one leg).
# 'far' (default): the leg behind, which the idle cell shows only as a slice; 'both'; 'off'
SIDE_LEGS_FROM_WALK = os.environ.get('SIDE_LEGS_FROM_WALK', 'far')

# The Elf package's action targets, as they sit in the packaged engine (profiles/elf-male.json keeps them verbatim).
ELF = {
    'neck': [[32, 25], [32, 25], [34, 25], [29, 25]],
    'shoulders': [{'right': [23, 29], 'left': [40, 29]}, {'right': [40, 29], 'left': [23, 29]},
                  {'right': [29, 29], 'left': [36, 30]}, {'right': [27, 30], 'left': [34, 29]}],
    'reach': 15.32,
    'grips': [{'right': [19.0, 37.0], 'left': [44.0, 39.0]}, {'right': [44.0, 37.0], 'left': [24.0, 33.0]},
              {'right': [42.47, 35.74], 'left': [39.0, 38.0]}, {'right': [18.0, 32.0], 'left': [23.0, 37.0]}],
    'actions': {
        'bow': [{'bow': [38, 32], 'nock': [32, 32], 'cheek': [28, 29], 'flung': [26, 28]},
                {'bow': [26, 31], 'nock': [31, 31], 'cheek': [36, 30], 'flung': [38, 29]},
                {'bow': [54, 28], 'nock': [45, 28], 'cheek': [36, 27], 'flung': [32, 26]},
                {'bow': [9, 28], 'nock': [18, 28], 'cheek': [27, 27], 'flung': [29, 28]}],
        'throwFront': {'windup': [5, -5], 'release': [3, 1], 'follow': [1, 7]},
        'throwSouth': {'hand': [-3, -4], 'elbow': [0, 6]},
        'throwNorth': {'elbow': [6, 0], 'hand': [0, -7]},
    },
}


def staged_joints(race):
    """Staged joints per cell, moved by the same row offset as the zones (load() must run first)."""
    for p in [os.path.join(RIG, 'inputs', race + '.json'), os.path.join(STAGED, 'rig', race + '.json')]:
        if os.path.exists(p):
            return {k: {j: [xy[0], xy[1] + load.shift.get(k, 0)] for j, xy in v['joints'].items()}
                    for k, v in json.load(open(p))['cells'].items()}
    sys.exit('no staged joints for ' + race)


def load(race):
    inp = os.path.join(RIG, 'inputs')
    if os.path.exists(os.path.join(inp, 'sprites.png')):
        p = os.path.join(inp, 'sprites.png')
        fine = json.load(open(os.path.join(inp, 'fine.json')))
        zones = np.array(Image.open(os.path.join(inp, 'fine.png')).convert('P'))
    else:
        for base in ['Dungeon Master Sample/Approved Sprites/Male', 'Dungeon Master Sample/Sprites/Male']:
            p = os.path.join(ROOT, base, race, 'base', 'sprites.png')
            if os.path.exists(p):
                break
        else:
            sys.exit('no sheet for ' + race)
        zdir = os.path.join(STAGED, 'rig/finezones', race)
        fine = json.load(open(os.path.join(zdir, 'fine.json')))
        zones = np.array(Image.open(os.path.join(zdir, 'fine.png')).convert('P'))
    sheet = np.array(Image.open(p).convert('RGBA'))
    # The staged zones were drawn on the game's copy of the sheet, whose bodies sit lower than the approved pack
    # sheet (zones.json: row_shift 2). Find each cell's row offset by best overlap with the sheet's pixels and move
    # the zones, their landmarks and the staged joints onto the approved art.
    cells = {k: dict(v) for k, v in fine.get('cells', {}).items()}
    load.shift = {}
    aligned = np.zeros_like(zones)
    for d in range(4):
        for f in range(sheet.shape[0] // 64):
            a = sheet[f * 64:(f + 1) * 64, d * 64:(d + 1) * 64, 3] > 0
            b = zones[f * 64:(f + 1) * 64, d * 64:(d + 1) * 64]
            def iou(dy):
                bb = np.roll(b > 0, dy, 0)
                return (a & bb).sum() / max(1, (a | bb).sum())
            dy = max(range(-4, 5), key=iou)
            moved = np.roll(b, dy, 0)
            if dy < 0:
                moved[dy:] = 0
            elif dy > 0:
                moved[:dy] = 0
            aligned[f * 64:(f + 1) * 64, d * 64:(d + 1) * 64] = moved
            key = 'SNEW'[d] + str(f)
            load.shift[key] = int(dy)
            for lm in ('neck', 'brow', 'skull_top', 'chest_end', 'waist', 'crotch'):
                if key in cells and lm in cells[key]:
                    cells[key][lm] += dy
    load.cells = cells
    return sheet, aligned, fine['zones'], p


def cell(a, d, f):
    return a[f * 64:(f + 1) * 64, d * 64:(d + 1) * 64]


def adopt_unzoned(z, px):
    """Opaque pixels the zones left unlabelled (mostly the outer outline) join the zone most of their neighbours
    have, so every part keeps its contour."""
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


def mask_of(z, names, wanted):
    return np.isin(z, [i for i, n in enumerate(names) if n in wanted])


def opaque(px):
    return px[:, :, 3] > 0


def outline_mask(px):
    return opaque(px) & (px[:, :, :3].astype(int).sum(2) < OUTLINE_SUM)


def rint(p):
    return [int(round(p[0])), int(round(p[1]))]


def row_centre(m, y):
    xs = np.nonzero(m[y])[0]
    return float(xs.mean() + .5) if len(xs) else None


def seg_dist(p, a, b):
    """Distance from points p (n, 2) to segment a-b."""
    a, b = np.array(a, float), np.array(b, float)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(1e-6, float(ab @ ab)), 0, 1)
    return np.hypot(*(p - (a + t[:, None] * ab)).T)


def part_image(px, mask):
    out = np.zeros_like(px)
    out[mask] = px[mask]
    return out


def band(m, y0, y1):
    """Rows y0..y1 of mask m (inclusive)."""
    out = np.zeros_like(m)
    out[max(0, y0):min(64, y1 + 1)] = m[max(0, y0):min(64, y1 + 1)]
    return out


def carry_rows(canvas, src_mask, px, y_from, y_to):
    """Copy the pixels of row y_from (within src_mask) into every empty row between y_to and y_from."""
    row = src_mask[y_from]
    if not row.any():
        return
    step = 1 if y_to > y_from else -1
    for y in range(y_from + step, y_to + step, step):
        for x in np.nonzero(row)[0]:
            if canvas[y, x, 3] == 0:
                canvas[y, x] = px[y_from, x]


def outline_edge(canvas, added):
    """Added pixels on the silhouette edge become outline pixels, so a filled body keeps its contour."""
    a = opaque(canvas)
    edge = np.zeros_like(a)
    edge[1:, :] |= ~a[:-1, :]
    edge[:-1, :] |= ~a[1:, :]
    edge[:, 1:] |= ~a[:, :-1]
    edge[:, :-1] |= ~a[:, 1:]
    canvas[added & a & edge] = (0, 0, 0, 255)


def erase_inner_outlines(canvas):
    """An outline pixel with body colour 1-2 px on both sides on its row (the carved arm's edge) takes the colour
    beside it, so a limb swung away leaves no dark stripe on the body."""
    op = opaque(canvas)
    is_out = outline_mask(canvas)
    skin = op & ~is_out
    for y in range(64):
        for x in range(2, 62):
            if is_out[y, x] and skin[y, x - 1] and skin[y, x + 1]:
                xs = np.nonzero(skin[y])[0]
                canvas[y, x] = canvas[y, xs[np.argmin(np.abs(xs - x))]]


def complete_body(px, z, names, own_zones, d, axis, span, arm_side=0):
    """The torso or shorts with the surfaces under the arms and fists put back."""
    own = mask_of(z, names, own_zones)
    canvas = part_image(px, own)
    added = np.zeros((64, 64), bool)
    ys = np.nonzero(own.any(1))[0]
    if len(ys) == 0:
        return canvas
    out_m = outline_mask(px)
    for y in range(ys.min(), ys.max() + 1):
        xs = np.nonzero(own[y])[0]
        if len(xs) == 0:
            continue
        if d < 2:
            # front/back: the body is symmetric about its axis; take the other side's pixel
            for x in xs:
                mx = int(round(2 * axis - x - 1))
                # only a real bite (2 px or more from the row's own pixels), never 1 px of drawn asymmetry
                if 0 <= mx < 64 and canvas[y, mx, 3] == 0 and np.abs(xs - mx).min() >= 2:
                    canvas[y, mx] = px[y, x]
                    added[y, mx] = True
        else:
            # side: carry the row across the body's depth under the near arm
            lo, hi = span
            inner = [x for x in xs if not out_m[y, x]]
            if not inner:
                continue
            # only on the near arm's side of the body
            lo, hi = (lo, int(xs.min()) - 1) if arm_side < 0 else (int(xs.max()) + 1, hi)
            for x in range(lo, hi + 1):
                if canvas[y, x, 3] == 0:
                    src = inner[int(np.argmin(np.abs(np.array(inner) - x)))]
                    canvas[y, x] = px[y, src]
                    added[y, x] = True
    outline_edge(canvas, added)
    erase_inner_outlines(canvas)
    return canvas


def palette_shade(px, canvas):
    """Recolour a copied far limb with the sheet's own darker colours: for every colour pick the palette colour of
    the same hue family that is 15-45 % darker; outline stays outline."""
    op = opaque(px)
    cols = Counter(tuple(int(v) for v in c[:3]) for c in px[op])
    pal = [np.array(c, float) for c, n in cols.items() if n >= 3 and sum(c) >= OUTLINE_SUM]
    out = canvas.copy()
    m = opaque(canvas) & ~outline_mask(canvas)
    cache = {}
    for y, x in zip(*np.nonzero(m)):
        c = tuple(int(v) for v in canvas[y, x, :3])
        if c not in cache:
            cf = np.array(c, float)
            lum = cf.sum()
            best, score = None, None
            for q in pal:
                ql = q.sum()
                if not (.55 * lum <= ql <= .85 * lum):
                    continue
                # same hue family: compare the colour's normalised chroma
                hue = np.abs(cf / max(lum, 1) - q / max(ql, 1)).sum()
                if score is None or hue < score:
                    best, score = q, hue
            cache[c] = tuple(int(v) for v in best) if best is not None and score < .12 else tuple(int(v * .82) for v in c)
        out[y, x, :3] = cache[c]
    return out


def cut(race, slug, name):
    global STAGED_JOINTS
    sheet, zones, names, sheet_path = load(race)
    STAGED_JOINTS = staged_joints(race)
    assets = os.path.join(RIG, 'preview/assets')
    views, grips, actions_bow = [], [], []
    report = {}
    for d in range(4):
        px = cell(sheet, d, 0).copy()
        z = adopt_unzoned(cell(zones, d, 0), px)
        files = {}
        notes = []

        def save(key, canvas):
            fn = f'{slug}-{d}-{key}.png'
            Image.fromarray(canvas).save(os.path.join(assets, fn))
            files[key] = fn

        side = 1 if d == 2 else -1
        neck_m = mask_of(z, names, ['neck'])
        hips_m = mask_of(z, names, ['hips'])
        body_m = mask_of(z, names, BODY_ZONES + ['hips'])
        bxs = np.nonzero(body_m.any(0))[0]
        span = (int(bxs.min()), int(bxs.max()))
        axis = (span[0] + span[1] + 1) / 2
        torso_top = int(np.nonzero(mask_of(z, names, BODY_ZONES).any(1))[0].min())
        hips_rows = np.nonzero(hips_m.any(1))[0]
        neck = [axis, torso_top + 1]
        waist = [axis, int(hips_rows.min())]
        hip_y = int(hips_rows.min()) + 1

        # ---- head, torso, pelvis ------------------------------------------------------------------------
        arm_m = mask_of(z, names, ['shoulder R', 'upper arm R', 'forearm R', 'hand R', 'shoulder L', 'upper arm L', 'forearm L', 'hand L'])
        arm_side = -1 if (np.nonzero(arm_m.any(0))[0].mean() + .5) < axis else 1
        save('head', part_image(px, mask_of(z, names, HEAD_ZONES)))
        save('torso', complete_body(px, z, names, BODY_ZONES, d, axis, span, arm_side))

        # ---- arms: measured on the pixels ---------------------------------------------------------------
        arms, arm_imgs = {}, {}
        masks = {sd: mask_of(z, names, [f'shoulder {S}', f'upper arm {S}', f'forearm {S}', f'hand {S}'])
                 for sd, S in [('right', 'R'), ('left', 'L')]}
        z_raw0 = cell(zones, d, 0)  # landmarks from the zones as labelled; the outline adoption would add rows
        raw_masks = {sd: mask_of(z_raw0, names, [f'shoulder {S}', f'upper arm {S}', f'forearm {S}', f'hand {S}'])
                     for sd, S in [('right', 'R'), ('left', 'L')]}
        # front/back: both hanging arms are one drawing mirrored, so they share top and bottom rows
        shared = [np.nonzero(m.any(1))[0] for m in raw_masks.values() if m.sum() >= 20]
        shared_top = int(round(np.mean([r.min() for r in shared]))) if d < 2 else None
        shared_bot = int(round(np.mean([r.max() for r in shared]))) if d < 2 else None
        for sd, S in [('right', 'R'), ('left', 'L')]:
            m = masks[sd]
            if m.sum() < 20:
                continue
            rows = np.nonzero(raw_masks[sd].any(1))[0]
            top, bot = (shared_top, shared_bot) if d < 2 else (int(rows.min()), int(rows.max()))
            sy = top + 2
            wy = bot - (3 if d < 2 else 6)
            ey = sy + int(round(8 / 15 * (wy - sy)))
            if d < 2:
                cx = float(np.nonzero(band(m, top, wy).any(0))[0].mean() + .5)
                sx, ex, hx = cx + (1 if cx < axis else -1), cx, cx
            else:
                sx = row_centre(m, sy) + (1 if row_centre(m, sy) < axis else -1)  # a touch inside, like the Elf
                ex, hx = row_centre(m, ey), row_centre(m, wy)
            s, e, h = [sx, sy], [ex, ey], [hx, wy]
            arms[sd] = [s, e, h]
            arm_imgs[sd] = {'UpperArm': band(m, 0, ey + 2), 'Forearm': band(m, ey - 1, wy + 1), 'Hand': band(m, wy - 2, 63)}
            for key, mm in arm_imgs[sd].items():
                save(sd + key, part_image(px, mm))
        synth = None
        part_source = {}
        if d >= 2 and len(arms) == 1:
            # The idle side cell hides the far arm. Walk frame A swings it forward and draws its fist in front of the
            # chest; the staged joints of that frame give its elbow. The far shoulder sits at the near shoulder's
            # height, one upper-arm length from that elbow. Upper arm and forearm are the near arm's pixels moved to
            # that shoulder and recoloured with the sheet's own darker colours; the fist is the sheet's drawing.
            near = next(iter(arms))
            far = 'left' if near == 'right' else 'right'
            FS = 'L' if far == 'left' else 'R'
            s_n, e_n, h_n = arms[near]
            A = float(np.hypot(*(np.array(e_n) - s_n)))
            j1 = STAGED_JOINTS[F[d] + '1']
            dy01 = int(load.cells[F[d] + '1']['neck']) - int(load.cells[F[d] + '0']['neck'])  # frame A sits lower
            e1 = j1['elbow' + FS]
            sy1 = s_n[1] + dy01
            sx1 = e1[0] - (1 if d == 2 else -1) * float(np.sqrt(max(0.0, A * A - (e1[1] - sy1) ** 2)))
            s_f = [round(sx1), s_n[1] + 1]
            dx = int(s_f[0] - round(s_n[0]))
            arms[far] = [[s_n[0] + dx, s_n[1] + 1], [e_n[0] + dx, e_n[1] + 1], [h_n[0] + dx, h_n[1] + 1]]
            for key in ['UpperArm', 'Forearm']:
                im = np.array(Image.open(os.path.join(assets, files[near + key])))
                out = np.zeros_like(im)
                out[1:, max(0, dx):64 + min(0, dx)] = im[:63, max(0, -dx):64 + min(0, -dx)]
                save(far + key, palette_shade(px, out))
            px1 = cell(sheet, d, 1)
            z1 = adopt_unzoned(cell(zones, d, 1), px1)
            hand1 = mask_of(z1, names, [f'hand {FS}'])
            top1 = int(np.nonzero(hand1.any(1))[0].min())
            fist = part_image(px1, band(hand1 | mask_of(z1, names, [f'forearm {FS}']), top1 - 2, 63))
            fist[:top1 - 2] = 0
            save(far + 'Hand', fist)
            w1 = [row_centre(hand1, top1 + 2), float(top1 + 2)]
            part_source[far + 'Hand'] = [w1, [w1[0], w1[1] + 1]]
            synth = (near, far, dx, 1)
            notes.append(f'far {far} arm: shoulder {dx:+d} px from the near one (from walk frame A elbow {e1}); '
                         f'upper arm and forearm = near arm palette-shaded; fist = walk frame A drawing')

        # near leg (drawn last): front/back as the Elf profile; side views = the leg the idle drawing shows more of,
        # since the leg behind is partly hidden (and shaded darker)
        if d < 2:
            near_leg = 'right'
        else:
            vis = {sd: int(mask_of(cell(zones, d, 0), names, [f'thigh {S}', f'shin {S}', f'foot {S}']).sum())
                   for sd, S in [('right', 'R'), ('left', 'L')]}
            near_leg = max(vis, key=vis.get)
            notes.append(f'near leg {near_leg} (visible px {vis})')

        # ---- legs: measured on the pixels ---------------------------------------------------------------
        # The shorts below the crotch line belong to the thighs (the Elf profile splits its shorts the same way), so a
        # lifted or bent leg carries its own shorts leg. The zones label the whole side-view shorts as hips; front and
        # back views already give the shorts legs to the thighs.
        legs = {}
        hem = int(hips_rows.max())
        crotch = int(load.cells.get(F[d] + '0', {}).get('crotch', hip_y + 2))
        # The hip joint sits at the crotch line, as on the Elf (waist 42, hip 49): the waistband above it belongs to
        # the pelvis. Knee = the first row under the shorts leg; ankle = 3 rows above the sole.
        raw = {}
        z_raw = cell(zones, d, 0)  # landmarks from the zones as labelled (the outline adoption would shift rows)
        hem = int(np.nonzero(mask_of(z_raw, names, ['hips']).any(1))[0].max())
        for sd, S in [('right', 'R'), ('left', 'L')]:
            th_m = mask_of(z_raw, names, [f'thigh {S}'])
            leg = mask_of(z_raw, names, [f'thigh {S}', f'shin {S}', f'foot {S}'])
            rows = np.nonzero(leg.any(1))[0]
            ky = (int(np.nonzero(th_m.any(1))[0].max()) + 1) if th_m.sum() >= 20 else hem + 1
            raw[sd] = {'leg': leg, 'top': int(rows.min()), 'ky': ky, 'ay': int(rows.max()) - 3}
        if d < 2:
            # front/back: both legs are one drawing mirrored about the body axis; share rows and mirror the x offsets
            ky = int(round(np.mean([r['ky'] for r in raw.values()])))
            ay = int(round(np.mean([r['ay'] for r in raw.values()])))
            off = {}
            for sd, r in raw.items():
                off[sd] = [abs(row_centre(r['leg'], y) - axis) for y in (crotch + 1, ky, ay)]
            mean_off = np.mean([off['right'], off['left']], axis=0)
            for sd, r in raw.items():
                sign = -1 if row_centre(r['leg'], ky) < axis else 1
                legs[sd] = [[axis + sign * mean_off[0], crotch], [axis + sign * mean_off[1], ky], [axis + sign * mean_off[2], ay]]
        else:
            # side: both hips under the middle of the pelvis, 2 px either side (the Elf's are 4 px apart); the leg
            # whose foot is further forward takes the forward hip
            fwd = 1 if d == 2 else -1
            foot_x = {sd: row_centre(r['leg'], r['ay']) for sd, r in raw.items()}
            front = max(foot_x, key=lambda k: foot_x[k] * fwd)
            for sd, r in raw.items():
                hx = axis + (2 if sd == front else -2) * fwd
                legs[sd] = [[hx, crotch], [row_centre(r['leg'], r['ky']), r['ky']], [row_centre(r['leg'], r['ay']), r['ay']]]
        for sd in legs:
            legs[sd] = [[float(p[0]), float(p[1])] for p in legs[sd]]
        # Side views: in the idle cell one leg hides most of the other, so a cut-out of the hidden leg is slivers.
        # Walk frame A draws both legs whole and apart; the side leg parts are cut there and keep that frame's joints
        # as their source joints (profile `partSource`). Rest joints stay the idle cell's.
        leg_src = None
        if d >= 2 and SIDE_LEGS_FROM_WALK != 'off':
            px1 = cell(sheet, d, 1)
            z1 = adopt_unzoned(cell(zones, d, 1), px1)
            z1r = cell(zones, d, 1)
            b1 = np.nonzero(mask_of(z1, names, BODY_ZONES + ['hips']).any(0))[0]
            span1 = (int(b1.min()), int(b1.max()))
            ch1 = np.nonzero(mask_of(z1, names, ['chest']).any(0))[0]
            axis1 = (ch1.min() + ch1.max() + 1) / 2
            crotch1 = int(load.cells[F[d] + '1']['crotch'])
            hip_y1 = int(np.nonzero(mask_of(z1, names, ['hips']).any(1))[0].min()) + 1
            near_arm1 = mask_of(z1, names, [f'{p} {"R" if d == 2 else "L"}' for p in ('upper arm', 'forearm', 'hand')])
            arm_side1 = -1 if (np.nonzero(near_arm1.any(0))[0].mean() + .5) < axis1 else 1
            fwd = 1 if d == 2 else -1
            # Bone lengths stay the idle cell's (rest joints = the idle drawing). In walk frame A each knee is the point
            # of the leg's centre line one idle thigh length from the hip; the ankle is 3 rows above the sole, as in the
            # idle cell. The walk legs are drawn about a pixel longer, so the shin is marked to fit its bone.
            src = {}
            for sd, S in [('right', 'R'), ('left', 'L')]:
                leg1 = mask_of(z1r, names, [f'thigh {S}', f'shin {S}', f'foot {S}'])
                rows1 = np.nonzero(leg1.any(1))[0]
                a_y = int(rows1.max()) - 3
                src[sd] = {'leg': leg1, 'ankle': [row_centre(leg1, a_y), float(a_y)]}
            front1 = max(src, key=lambda k: src[k]['ankle'][0] * fwd)
            for sd, v in src.items():
                T = float(np.hypot(*(np.array(legs[sd][1]) - legs[sd][0])))
                v['hip'] = [float(axis1 + (2 if sd == front1 else -2) * fwd), float(crotch1)]
                cands = [(row_centre(v['leg'], y), float(y)) for y in range(crotch1 + 2, int(v['ankle'][1]))
                         if v['leg'][y].any()]
                v['knee'] = list(min(cands, key=lambda q: abs(np.hypot(q[0] - v['hip'][0], q[1] - v['hip'][1]) - T)))
            notes.append('side legs cut from walk frame A at the idle bone lengths; shins fitted to their bones '
                         + ', '.join(f"{sd} shin drawn {np.hypot(*(np.array(v['ankle']) - v['knee'])):.1f} / bone "
                                     f"{np.hypot(*(np.array(legs[sd][2]) - legs[sd][1])):.1f}" for sd, v in src.items()))
            leg_src = (px1, z1, src, crotch1, hip_y1, complete_body(px1, z1, names, ['hips'], d, axis1, span1, arm_side1))
        # complete the whole shorts first (pixels under the near hand put back), then split the completed shorts
        full_shorts = complete_body(px, z, names, ['hips'], d, axis, span, arm_side)
        shorts_m = opaque(full_shorts)
        shorts = shorts_m & (np.arange(64)[:, None] >= crotch)
        ys, xs = np.nonzero(shorts)
        pts = np.stack([xs + .5, ys + .5], 1)
        dist = {sd: seg_dist(pts, hp, kn) for sd, (hp, kn, _) in legs.items()}
        owner = np.where(dist['right'] <= dist['left'], 'right', 'left')
        if leg_src:
            lpx, lz, src, l_crotch, l_hip_y, l_shorts = leg_src
            l_m = opaque(l_shorts) & (np.arange(64)[:, None] >= l_crotch)
            lys, lxs = np.nonzero(l_m)
            lpts = np.stack([lxs + .5, lys + .5], 1)
            ldist = {sd: seg_dist(lpts, v['hip'], v['knee']) for sd, v in src.items()}
            lowner = np.where(ldist['right'] <= ldist['left'], 'right', 'left')
        for sd, S in [('right', 'R'), ('left', 'L')]:
            if leg_src and (SIDE_LEGS_FROM_WALK == 'both' or sd != near_leg):
                cpx, cz, hip, knee, ankle = lpx, lz, src[sd]['hip'], src[sd]['knee'], src[sd]['ankle']
                c_shorts, c_hip_y = l_shorts, l_hip_y
                oys, oxs = lys[lowner == sd], lxs[lowner == sd]
                part_source[sd + 'Thigh'] = [hip, knee]
                part_source[sd + 'Shin'] = [knee, ankle, 'fit']
                part_source[sd + 'Foot'] = [ankle, [ankle[0], ankle[1] + 1]]
            else:
                cpx, cz, (hip, knee, ankle) = px, z, legs[sd]
                c_shorts, c_hip_y = full_shorts, hip_y
                oys, oxs = ys[owner == sd], xs[owner == sd]
            ky, ay = int(knee[1]), int(ankle[1])
            leg = mask_of(cz, names, [f'thigh {S}', f'shin {S}', f'foot {S}'])
            own_shorts = np.zeros((64, 64), bool)
            own_shorts[oys, oxs] = True
            th = band(leg, 0, ky + 2) | own_shorts
            thigh = part_image(cpx, band(leg, 0, ky + 2))
            thigh[own_shorts] = c_shorts[own_shorts]
            # under the waistband: the thigh's top row carried up to the hip, so a swung thigh shows no gap
            top_row = int(np.nonzero(th.any(1))[0].min())
            for y in range(top_row - 1, c_hip_y - 1, -1):
                for x in np.nonzero(opaque(thigh)[top_row])[0]:
                    if thigh[y, x, 3] == 0:
                        thigh[y, x] = thigh[top_row, x]
            save(sd + 'Thigh', thigh)
            save(sd + 'Shin', part_image(cpx, band(leg, ky - 1, ay + 1)))
            save(sd + 'Foot', part_image(cpx, band(leg, ay - 2, 63)))
        pelvis = full_shorts.copy()
        pelvis[np.arange(64) > crotch + 1] = 0
        save('pelvis', pelvis)

        # ---- walk rows ----------------------------------------------------------------------------------
        walk = []
        for f in range(3):
            wpx = cell(sheet, d, f)
            wz = adopt_unzoned(cell(zones, d, f), wpx)
            body = complete_body(wpx, wz, names, BODY_ZONES, d, axis, span, arm_side)
            shorts = complete_body(wpx, wz, names, ['hips'], d, axis, span, arm_side)
            legs_img = part_image(wpx, mask_of(wz, names, ['thigh R', 'shin R', 'foot R', 'thigh L', 'shin L', 'foot L', 'tail']))
            for layer in (shorts, body):
                m = opaque(layer)
                legs_img[m] = layer[m]
            fn_b = f'{slug}-{d}-walk-{f}-refined-torso.png'
            fn_h = f'{slug}-{d}-walk-{f}-render-head.png'
            Image.fromarray(legs_img).save(os.path.join(assets, fn_b))
            Image.fromarray(part_image(wpx, mask_of(wz, names, HEAD_ZONES))).save(os.path.join(assets, fn_h))
            walk.append({'refined-torso': fn_b, 'render-head': fn_h})

        # ---- joint colours, grips, bow targets --------------------------------------------------------
        out_m = outline_mask(px)

        def colour_at(p, m):
            ys, xs = np.nonzero(m & ~out_m)
            if len(xs) == 0:
                return [0, 0, 0, 0]
            i = np.argmin(np.hypot(xs + .5 - p[0], ys + .5 - p[1]))
            return [int(v) for v in px[ys[i], xs[i]]]

        jc = {}
        for sd, S in [('right', 'R'), ('left', 'L')]:
            am = mask_of(z, names, [f'upper arm {S}', f'forearm {S}', f'hand {S}'])
            if am.sum() == 0:
                am = mask_of(z, names, ['upper arm R', 'forearm R', 'upper arm L', 'forearm L'])
            lm = mask_of(z, names, [f'shin {S}', f'foot {S}'])
            jc[sd + 'Elbow'] = colour_at(arms[sd][1], am)
            jc[sd + 'Wrist'] = colour_at(arms[sd][2], am)
            jc[sd + 'Knee'] = colour_at(legs[sd][1], lm)
            jc[sd + 'Ankle'] = colour_at(legs[sd][2], lm)

        reach = {sd: np.hypot(*(np.array(e) - s)) + np.hypot(*(np.array(h) - e)) for sd, (s, e, h) in arms.items()}
        scale = float(np.mean(list(reach.values()))) / ELF['reach']
        grip = {}
        for sd in ['right', 'left']:
            es, eg = np.array(ELF['shoulders'][d][sd], float), np.array(ELF['grips'][d][sd], float)
            g = np.array(arms[sd][0], float) + (eg - es) * scale
            grip[sd] = [int(round(float(g[0]))), int(round(float(g[1])))]
        grips.append(grip)
        en = np.array(ELF['neck'][d], float)
        # whole pixels, like the Elf's targets: a fractional nock or bow hand puts the 1 px arrow shaft between rows
        actions_bow.append({k: [int(round(float(v))) for v in (np.array(neck) + (np.array(t, float) - en) * scale)]
                            for k, t in ELF['actions']['bow'][d].items()})

        views.append({
            'name': FACINGS[d],
            'arms': {k: [rint(p) for p in v] for k, v in arms.items()},
            'legs': {k: [rint(p) if d < 2 else [round(p[0], 2), round(p[1], 2)] for p in v] for k, v in legs.items()},
            'waist': rint(waist), 'neck': rint(neck), 'nearLeg': near_leg,
            'parts': {k: files[k] for k in PARTS},
            'walk': walk,
            'jointColors': jc,
            **({'partSource': {k: [[round(float(c), 2) for c in p] if not isinstance(p, str) else p for p in v]
                               for k, v in part_source.items()}}
               if part_source else {}),
        })
        report[FACINGS[d]] = {'reach': {k: round(float(v), 2) for k, v in reach.items()}, 'notes': notes,
                              'neck': rint(neck), 'waist': rint(waist), 'span': span}
    actions = {'bow': actions_bow,
               **{k: {n: [int(round(v * scale)) for v in t] for n, t in ELF['actions'][k].items()}
                  for k in ('throwFront', 'throwSouth', 'throwNorth')}}
    profile = {'name': name, 'source': os.path.relpath(sheet_path, ROOT), 'zones': f'fine zones for {race}',
               'zoneRowShift': load.shift,
               'calibration': 'joints measured on the idle pixels (tools/cut_from_finezones.py); bow/throw targets = '
                              'the Elf targets moved to this body\'s neck and shoulders and scaled by arm reach '
                              f'({scale:.3f}); not yet fitted by eye',
               'views': views, 'grips': grips, 'actions': actions}
    out = os.path.join(RIG, 'profiles', slug + '.json')
    json.dump(profile, open(out, 'w'), indent=1)
    print('wrote', out)
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    race, slug, name = (sys.argv + ['Human', 'human-male', 'GOA Human male'])[1:4]
    cut(race, slug, name)
