# Each race's fists read off its own pictures (python3 fists.py [check.png]): the whole body minus its "NoRightArm"
# (or "NoLeftArm") picture is that arm, pixel for pixel; its far end (the lowest few rows of the arm, where the hand
# hangs or swings) is the fist. Writes the fists into anchors.json as hand/fistL beside the template's points
# (anchors.py), keeping the template's where the arm is hidden (the far side of the body).
#
# Side on, the armless pictures only paint a red stump at the shoulder (the arm is drawn on the body there), so what
# they lack is the stump, not the arm. There the arm is cut the way the ragdolls cut it (parts.find_arm: its lines and
# stump with a standard armour's sleeve over them) and the fist is its far end from the shoulder; the weapon goes a
# pixel back from it, into the fist. Facing east the right arm is the near one; facing west the right arm is hidden
# right behind the left, so its weapon goes where the left fist is.
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'enhance'))
from game_export import read_dmi_full   # noqa: E402

R64 = os.path.join(HERE, '..', '..', 'game', 'Icons', 'Remastered', 'Races64')
# read off the pictures as they were before the 2026-10-24 reshade: each state was reshaded on its own, so the whole
# body and the armless one differ in shading well away from the arm; before it they differ at the arm only
R64_SRC = os.path.join(HERE, '..', '..', 'restore-points', 'sprites-before-enhance-20261024', 'Races64')
DIRS = 'SNEW'


def biggest(mask):
    """The largest 4-connected part of a mask."""
    lab = np.zeros(mask.shape, int); n = 0; best, bs = None, 0
    for y, x in zip(*np.nonzero(mask)):
        if lab[y, x]: continue
        n += 1; stack = [(y, x)]; lab[y, x] = n; size = 0
        while stack:
            cy, cx = stack.pop(); size += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = n; stack.append((ny, nx))
        if size > bs: best, bs = n, size
    return lab == best if best else np.zeros_like(mask)


def fist(arm):
    """The arm's far end: the middle of its lowest three rows. None when too little of the arm shows."""
    if arm.sum() < 12:
        return None
    ys, xs = np.nonzero(arm)
    low = ys >= ys.max() - 2
    return [round(float(xs[low].mean()) + 0.5, 2), round(float(ys[low].mean()) + 0.5, 2)]


SIDE_ARMOUR = ('iron', 'mail', 'mail', 'plate')   # tier, chest, legs, sleeves: a standard armour to find the arm with


def side_fists(A):
    sys.path.insert(0, HERE)
    import parts, wearables64 as w, remaster64 as rm, game_export as ge   # noqa: E401
    specs = {s['sheet']: s for s in ge.SHEETS}
    T = w.Template(frame=0)
    F = w.Figures(T, races=list({specs[s]['race'] for s in A if s in specs}), frame=0)
    for sheet, a in A.items():
        if sheet not in specs:
            continue
        race, st = specs[sheet]['race'], parts.states(sheet)
        body = st[a['state']]
        tops = [np.nonzero(parts.limb(body[0], st[n][0]))[0].min() for n in ('NoRightLeg', 'NoLeftLeg') if n in st and parts.limb(body[0], st[n][0]).any()]
        hip_row = int(min(tops)) if tops else 50   # where the legs start, from the front
        moved = []
        for d, side, name in (('E', 'R', 'NoRightArm'), ('W', 'L', 'NoLeftArm')):
            di = DIRS.index(d)
            chin = F.map_point(race, d, 32, rm.CHIN)[1]
            for f in range(3):
                k, v = f * 4 + di, a['views'][d][f]
                L = parts.layers(sheet, a['state'], SIDE_ARMOUR, di, f)
                pic = parts.compose(L)
                sh = parts.shoulders(T, F, race, d).get(side)
                m = parts.find_arm(L, parts.topmost(L), pic[..., 3] > 0, body[k], st[name][k] if name in st else None, chin, hip_row, d, side, sh)
                if not m.any():
                    continue
                S, E, H = parts.arm_joints(m, parts.stump(st[name][k] if name in st else None), sh)
                u = np.hypot(H[0] - E[0], H[1] - E[1]) or 1
                into = [round(H[0] - (H[0] - E[0]) / u, 2), round(H[1] - (H[1] - E[1]) / u, 2)]
                t = v.get('hand_t') or v['hand']
                if np.hypot(into[0] - t[0], into[1] - t[1]) <= 16:
                    v['fist_side'] = H
                    moved.append(np.hypot(into[0] - v['hand'][0], into[1] - v['hand'][1]))
                    v['hand'] = into
        print(f'{sheet:15s} side-on grips moved into the fist: {len(moved)} of 6, by {np.mean(moved) if moved else 0:.1f} px on average', flush=True)


def main(check=None):
    A = json.load(open(os.path.join(HERE, 'anchors.json')))
    for sheet, a in A.items():
        src = os.path.join(R64_SRC, sheet + '.dmi')
        st = {n: c for n, m, c in read_dmi_full(src if os.path.exists(src) else os.path.join(R64, sheet + '.dmi'))}
        body, nr, nl = st[a['state']], st['NoRightArm'], st['NoLeftArm']
        for di, d in enumerate(DIRS):
            for f in range(3):
                k = f * 4 + di
                B = body[k][..., 3] > 0
                for key, other in (('fistR', nr), ('fistL', nl)):
                    # the arm: what the armless picture lacks, or shows in other colours (an arm drawn over the body)
                    o = other[k]
                    changed = ~(o[..., 3] > 0) | (np.abs(body[k][..., :3].astype(int) - o[..., :3].astype(int)).sum(-1) > 24)
                    arm = biggest(B & changed)
                    a['views'][d][f][key] = fist(arm)
        diffs = []
        for d in DIRS:
            for f in range(3):
                v = a['views'][d][f]
                if 'hand_t' in v: v['hand'] = v['hand_t']
        for d in DIRS:
            for f in range(3):
                v = a['views'][d][f]
                if v['fistR']:
                    diffs.append(np.hypot(v['fistR'][0] - v['hand'][0], v['fistR'][1] - v['hand'][1]))
        worst = max(((np.hypot(v['fistR'][0] - v['hand'][0], v['fistR'][1] - v['hand'][1]), d, f) for d in DIRS for f, v in enumerate(a['views'][d]) if v['fistR']), default=(0, '', 0))
        print(f'{sheet:15s} right fist vs template hand: mean {np.mean(diffs):.1f} px, worst {worst[0]:.1f} px ({worst[1]} frame {worst[2]})', flush=True)
        # held weapons go in the found fist (a pixel up from the arm's end, into the fist), unless it is on the wrong
        # side of the body for that facing or far from the template's point: some armless pictures in the original
        # art have the other arm missing (the back view's second walk step)
        used = 0
        for d in DIRS:
            for f in range(3):
                v = a['views'][d][f]
                t = v.get('hand_t') or v['hand']
                v['hand_t'] = t
                g = v['fistR']
                cx = (v['head']['l'] + v['head']['r']) / 2
                ok = g is not None and np.hypot(g[0] - t[0], g[1] - t[1]) <= 14 and not (d == 'S' and g[0] > cx) and not (d == 'N' and g[0] < cx)
                v['hand'] = [g[0], round(g[1] - 1.0, 2)] if ok else t
                used += ok
        print(f'{"":15s} found fist used in {used} of 12 pictures', flush=True)
    side_fists(A)
    json.dump(A, open(os.path.join(HERE, 'anchors.json'), 'w'), separators=(',', ':'))
    if check:
        from PIL import Image, ImageDraw
        Z = 4
        img = Image.new('RGBA', (12 * 64 * Z, len(A) * 64 * Z), (60, 64, 72, 255)); dr = ImageDraw.Draw(img)
        for ri, (sheet, a) in enumerate(A.items()):
            body = next(c for n, m, c in read_dmi_full(os.path.join(R64, sheet + '.dmi')) if n == a['state'])
            for f in range(3):
                for di, d in enumerate(DIRS):
                    x0, y0 = (f * 4 + di) * 64 * Z, ri * 64 * Z
                    img.alpha_composite(Image.fromarray(body[f * 4 + di]).resize((64 * Z, 64 * Z), Image.NEAREST), (x0, y0))
                    v = a['views'][d][f]
                    P = lambda p: (x0 + p[0] * Z, y0 + p[1] * Z)
                    hx, hy = P(v.get('hand_t', v['hand'])); dr.ellipse([hx - 5, hy - 5, hx + 5, hy + 5], outline=(255, 40, 40), width=2)
                    ux, uy = P(v['hand']); dr.line([ux - 8, uy, ux + 8, uy], fill=(255, 255, 0), width=2); dr.line([ux, uy - 8, ux, uy + 8], fill=(255, 255, 0), width=2)
                    if v['fistR']:
                        gx, gy = P(v['fistR']); dr.ellipse([gx - 7, gy - 7, gx + 7, gy + 7], outline=(40, 255, 80), width=3)
                    if v['fistL']:
                        bx, by = P(v['fistL']); dr.rectangle([bx - 5, by - 5, bx + 5, by + 5], outline=(80, 160, 255), width=2)
            dr.text((6, ri * 64 * Z + 4), sheet, fill=(255, 255, 255))
        img.save(check); print(check)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
