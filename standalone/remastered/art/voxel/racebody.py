# A race's body made the way the human knight's is (build3d8): hand-made parts - a head with a
# flat face, a neck, a torso tapering from the shoulders, round shoulders, arms with hands, hips,
# legs with knees, shins and feet - set to each race's own proportions (measured from its sprite,
# then tuned by hand in RACES), plus the race's own features, made by hand: the orc's jaw, tusks
# and pointed ears, the goblin's big ears and nose, the dwarf's nose and ears.
import numpy as np, math
import build3d10
from build3d6 import Space

P = 64

def measured(race):
    """Starting proportions from the sprite (front and side pictures)."""
    S = build3d10.parts_of(race); side = S['side']
    def span(runs, rows):
        rs = [r for r in rows if r in runs]
        if not rs: return None
        c = np.array([(runs[r][0] + runs[r][1] + 1) / 2 for r in rs]); w = np.array([(runs[r][1] - runs[r][0] + 1) / 2 for r in rs])
        return float(np.median(c)), float(np.max(w)), float(np.median(w))
    def zspan(rows):
        zs = [side[r] for r in rows if r in side]
        if not zs: return 31.5, 9.0
        f = np.median([z[0] for z in zs]); b = np.median([z[1] for z in zs])
        return float((f + b + 1) / 2), float((b - f + 1) / 2)
    head_rows = sorted(S['head']); top, neck = head_rows[0], S['neck']
    hc, hw, _ = span(S['head'], head_rows)
    hz, hd = zspan(head_rows)
    jaw = span(S['head'], range(neck - 5, neck - 1))
    t_rows = sorted(S['torso'])
    tc, tw_max, tw = span(S['torso'], t_rows)
    tz, td = zspan(t_rows)
    sh = span(S['torso'], t_rows[:4])
    waist = span(S['torso'], t_rows[-5:])
    arms = {}
    for k in ('armL', 'armR'):
        rs = sorted(S[k])
        if rs:
            c, wmax, w = span(S[k], rs)
            arms[k] = dict(x=c, top=rs[0], bot=rs[-1], r=w + 0.6)
    legs = {}
    for k in ('legL', 'legR'):
        rs = sorted(S[k])
        if rs:
            c, wmax, w = span(S[k], rs)
            legs[k] = dict(x=c, r=w + 0.6)
    sole = S['sole']; crotch = S['crotch']
    foot = side.get(sole, side.get(sole - 1, (tz - 5, tz + 4)))
    return dict(top=top, neck=neck, crotch=crotch, sole=sole,
                head=dict(cx=hc, cz=hz, rx=hw + 0.4, rz=hd + 0.4, jaw=(jaw[1] + 0.4) if jaw else hw),
                torso=dict(cx=tc, cz=tz, rz=td + 0.4, shoulder=(sh[1] + 0.5) if sh else tw_max, chest=tw + 0.6,
                           waist=(waist[2] + 0.6) if waist else tw, top=t_rows[0], bot=t_rows[-1]),
                arms=arms, legs=legs, foot=dict(z0=foot[0], z1=foot[1]))

# Hand tuning per race, on top of what the sprite measures (sizes in sprite pixels).
RACES = {
    'Orc': dict(head=dict(p=3.0, jaw_out=1.4, jaw_rows=6), neck=dict(r=0.62), torso=dict(hunch=1.5, chest_out=0.8),
                arm_r=1.25, hand_r=1.35, leg_r=1.15, features=['tusks', 'pointed_ears', 'brow']),
    'Goblins': dict(head=dict(p=2.4, jaw_out=0.0, jaw_rows=4), neck=dict(r=0.38), torso=dict(hunch=1.0, chest_out=0.3),
                    arm_r=1.0, hand_r=1.15, leg_r=1.0, features=['big_ears', 'nose_point']),
    'Dwarves': dict(head=dict(p=2.6, jaw_out=0.8, jaw_rows=5), neck=dict(r=0.55), torso=dict(hunch=0.6, chest_out=0.6),
                    arm_r=1.2, hand_r=1.3, leg_r=1.2, features=['nose_round', 'small_ears']),
}
DEFAULT = dict(head=dict(p=2.4, jaw_out=0.0, jaw_rows=4), neck=dict(r=0.45), torso=dict(hunch=0.5, chest_out=0.3),
               arm_r=1.0, hand_r=1.15, leg_r=1.0, features=[])

def params(race):
    m = measured(race); t = RACES.get(race, DEFAULT)
    m['tune'] = t
    return m

# Races built to their sprite's numbers by hand (rows down the 64 px picture, columns across,
# depth z front->back from the side picture), the way the human knight is built.
EXPLICIT = {
    'Orc': dict(
        cx=32.0, cz=31.0,
        # head: rows, half-width, half-depth (outline included); flat-fronted, a squarish skull,
        # widest at the jaw, narrowing to the chin
        head=dict(rows=[10.4, 11.0, 12.0, 13.4, 15.5, 19.0, 23.0, 26.0, 28.5, 30.6],
                  rx=[5.0, 8.0, 10.0, 11.3, 11.8, 11.9, 12.0, 12.4, 10.6, 8.0],
                  rz=[5.0, 8.0, 9.8, 10.8, 11.2, 11.4, 11.3, 10.8, 9.2, 7.0], p=2.4, pfront=4.4),
        neck=dict(rows=(28.0, 33.0), rx=8.8, rz=8.4),
        # torso: sloping traps to the shoulders, a broad chest, the belly; arms hang beside it
        torso=dict(rows=[29.5, 31.0, 33.0, 35.0, 37.5, 40.0, 44.0, 48.0, 51.0, 53.0], rx=[8.5, 11.0, 13.2, 12.4, 10.2, 9.3, 9.1, 9.5, 10.2, 9.6],
                   rz=[8.0, 9.2, 10.0, 10.3, 10.3, 10.3, 10.5, 10.2, 9.6, 9.0], cz=31.2, p=2.6),
        shoulders=dict(x=(17.6, 46.4), row=34.6, r=3.9),
        arms=dict(x=(17.4, 46.6), top=34.0, bot=46.0, r=3.1, hand_row=47.2, hand_r=3.0,
                  # down the arm, as the sprite draws it: straight, tapering a little to the wrist
                  rows=[33.0, 36.0, 40.0, 44.0, 45.8], rx=[3.6, 3.4, 3.2, 3.0, 2.7], splay=1.0, fwd=0.9,
                  hand=dict(row=47.6, rx=3.3, ry=2.5, rz=3.6, fwd=0.8)),
        legs=dict(x=(23.6, 40.0), hip=51.0, knee=55.5, ankle=59.2, r=4.3, knee_r=4.0, shin_r=3.9,
                  # thigh, knee, calf, ankle
                  rows=[48.0, 51.5, 54.0, 55.6, 57.2, 59.8], rx=[5.0, 5.0, 4.6, 4.1, 4.5, 3.8]),
        feet=dict(rows=(58.8, 64.0), rx=5.3, rz=7.0, cz=30.4),
        ears=dict(root=(16.5, 10.6), tip=(10.4, 15.6), width=3.3, thick=0.9),
        tusks=dict(base_row=27.4, top_row=24.4, dx=4.8, r=0.62),
    ),
}

def lofted(sp, rows, rxs, rzs, cx, cz, p=2.6, pfront=None):
    """A smooth body through given half-widths and half-depths at given rows (interpolated)."""
    r, x, z = sp.r, sp.x, sp.z
    rx = np.interp(r, rows, rxs, left=0, right=0); rz = np.interp(r, rows, rzs, left=0, right=0)
    czr = np.interp(r, rows, cz, left=cz[0], right=cz[-1]) if np.ndim(cz) else cz
    pz = p if pfront is None else np.where(z < czr, pfront, p)
    ok = (r >= rows[0]) & (r <= rows[-1]) & (rx > 0.2) & (rz > 0.2)
    return ok & (np.abs((x - cx) / np.maximum(rx, 1e-3)) ** p + np.abs((z - czr) / np.maximum(rz, 1e-3)) ** pz <= 1)

def explicit_parts(race, B, world, SA_of, rig):
    """build3d10's body_parts for a race with hand-set numbers (EXPLICIT)."""
    E = EXPLICIT[race]; cx, cz = E['cx'], E['cz']
    out = {}
    h = E['head']
    out['head'] = lofted(B, h['rows'], h['rx'], h['rz'], cx, cz, p=h['p'], pfront=h['pfront'])
    out['head_c'] = (cx, cz, max(h['rx']), max(h['rz']))
    n = E['neck']
    out['neck'] = (np.abs((B.x - cx) / n['rx']) ** 2.4 + np.abs((B.z - (cz + 0.6)) / n['rz']) ** 2.4 <= 1) & (B.r >= n['rows'][0]) & (B.r < n['rows'][1])
    t = E['torso']
    out['torso'] = lofted(B, t['rows'], t['rx'], t['rz'], cx, t['cz'], p=2.3)
    out['torso_c'] = (cx, t['cz'], max(t['rx']), max(t['rz']))
    sh = E['shoulders']
    out['shoulders'] = np.zeros(B.r.shape, bool)
    for sx in sh['x']:
        out['shoulders'] |= (B.x - sx) ** 2 + ((B.r - sh['row']) * 1.1) ** 2 + (B.z - (t['cz'] - 0.2)) ** 2 <= sh['r'] ** 2
    L = E['legs']; F = E['feet']
    out['legs'] = []
    for key, lx, (ang, lift) in zip(('legR', 'legL'), L['x'], rig.legs):
        S_ = B.lifted(lift).swung((lx, L['hip'], t['cz']), ang)
        if 'rows' in L:
            leg = lofted(S_, L['rows'], L['rx'], [v * 1.04 for v in L['rx']], lx, t['cz'] + 0.3, p=2.15)
        else:
            leg = lofted(S_, [L['hip'] - 3.0, L['knee'] - 1.5, L['knee'], L['knee'] + 1.5, L['ankle'] + 0.6],
                         [L['r'], L['r'], L['knee_r'] + 0.3, L['shin_r'], L['shin_r'] - 0.2], [L['r'] * 1.05, L['r'], L['knee_r'] + 0.2, L['shin_r'], L['shin_r'] - 0.3],
                         lx, t['cz'] + 0.3, p=2.15)
        fr0, fr1 = F['rows']
        toe_top = fr0 + np.clip((F['cz'] - S_.z) * 0.22, 0, 1.4)
        foot = (np.abs((S_.x - lx) / F['rx']) ** 2.4 + np.abs((S_.z - F['cz']) / F['rz']) ** 2.2 <= 1) & (S_.r >= toe_top) & (S_.r < fr1)
        out['legs'].append(dict(key=key, space=S_, leg=leg, foot=foot, c=(lx, t['cz'], L['r'], L['r'])))
    A = E['arms']
    def hanging(ax, sp):
        if A.get('swing'):
            # arms carried a little forward (a brute's stance): the whole arm turned about the shoulder
            sp = sp.swung((ax, A['rows'][0] if 'rows' in A else A['top'], t['cz']), A['swing'])
        if 'rows' in A:
            # hanging a little forward and out from the body, so the arms read from the iso camera
            out_ = (-1 if ax < cx else 1) * A.get('splay', 0.0)
            spx = Space(sp.r, sp.x - out_ * np.clip((sp.r - A['rows'][0]) / (A['rows'][-1] - A['rows'][0]), 0, 1), sp.z)
            arm = lofted(spx, A['rows'], A['rx'], [v * 0.98 for v in A['rx']], ax, t['cz'] - 0.3 - A.get('fwd', 0.0), p=2.0)
        else:
            arm = lofted(sp, [A['top'] - 1.0, A['top'] + 2.0, (A['top'] + A['bot']) / 2, A['bot'] + 0.5],
                         [A['r'] + 0.2, A['r'] + 0.1, A['r'] - 0.1, A['r'] - 0.3], [A['r'] + 0.2, A['r'], A['r'] - 0.1, A['r'] - 0.3],
                         ax, t['cz'] - 0.3, p=2.0)
        if 'hand' in A:
            hd = A['hand']
            hx = ax + (-1 if ax < cx else 1) * A.get('splay', 0.0)
            hand = ((sp.x - hx) / hd['rx']) ** 2.4 + ((sp.r - hd['row']) / hd['ry']) ** 2.4 + ((sp.z - (t['cz'] - 0.3 - A.get('fwd', 0.0) - hd['fwd'])) / hd['rz']) ** 2.4 <= 1
        else:
            hand = ((sp.x - ax) / A['hand_r']) ** 2.4 + ((sp.r - A['hand_row']) / (A['hand_r'] * 0.95)) ** 2.4 + ((sp.z - (t['cz'] - 0.6)) / (A['hand_r'] * 1.05)) ** 2.4 <= 1
        return arm, hand
    SA = SA_of((A['x'][1], A['top'], t['cz']))
    arm, hand = hanging(A['x'][1], SA)
    out['armL'] = dict(space=SA, arm=arm, hand=hand, c=(A['x'][1], t['cz'], A['r'], A['r']))
    out['armR'] = dict(x=A['x'][0], top=A['top'], bot=A['bot'], r=A['r'], hand=A['hand_r'], cz=t['cz'])
    out['armR_rest'] = hanging(A['x'][0], B)
    if 'cap' in E:
        # a band round the crown's rim (not a lid): the head's outer shell in its top rows
        inner_ = lofted(B, h['rows'], [max(v - 1.6, 0.1) for v in h['rx']], [max(v - 1.6, 0.1) for v in h['rz']], cx, cz, p=h['p'], pfront=h['pfront'])
        out['cap'] = out['head'] & ~inner_ & (B.r >= h['rows'][0] + 0.9) & (B.r < h['rows'][0] + E['cap']['rows'] + 0.6)
    else:
        out['cap'] = None
    out['m'] = dict(top=h['rows'][0], neck=n['rows'][0], crotch=L['hip'], sole=F['rows'][1] - 1,
                    head=dict(cx=cx, cz=cz, rx=max(h['rx']), rz=max(h['rz']), jaw=max(h['rx'])),
                    torso=dict(cx=cx, cz=t['cz'], rz=max(t['rz']), shoulder=max(t['rx']), chest=10.0, waist=10.0, top=t['rows'][0], bot=t['rows'][-1]),
                    tune=RACES.get(race, DEFAULT), explicit=E)
    return out

def body_parts(race, B, world, SA_of, rig, sole_lift=0.0):
    """The solids of a race's bare body in the human style. Returns a dict of masks and the
    spaces they are painted in: head, jaw, neck, torso, shoulders, armL (with its space), legs
    (each with its space), feet, plus the joints the sword arm uses."""
    if race in EXPLICIT:
        return explicit_parts(race, B, world, SA_of, rig)
    m = params(race); t = m['tune']
    r, x, z = B.r, B.x, B.z
    out = {}
    H = m['head']; T = m['torso']
    # head: a rounded box-ish ellipsoid, flat in front for the face
    hr0, hr1 = m['top'], m['neck'] + 1.0
    hcr, hrr = (hr0 + hr1) / 2, (hr1 - hr0) / 2
    p = t['head']['p']
    pz = np.where(z < H['cz'], 4.2, p)
    head = np.abs((r - hcr) / hrr) ** p + np.abs((x - H['cx']) / H['rx']) ** p + np.abs((z - H['cz']) / H['rz']) ** pz <= 1
    # the jaw: wider and further forward at the bottom of the face (orc, dwarf)
    jr = t['head']['jaw_rows']
    jaw = (np.abs((r - (hr1 - jr / 2 - 0.5)) / (jr / 2 + 0.6)) ** 2.6 + np.abs((x - H['cx']) / max(H['jaw'], H['rx'] * 0.8)) ** 2.6
           + np.abs((z - (H['cz'] - t['head']['jaw_out'])) / (H['rz'] * 0.9)) ** np.where(z < H['cz'], 4.2, 2.4)) <= 1
    out['head'] = head | (jaw & (t['head']['jaw_out'] > 0))
    out['head_c'] = (H['cx'], H['cz'], H['rx'], H['rz'])
    # neck
    nr = max(2.4, H['rx'] * t['neck']['r'])
    out['neck'] = (np.abs((x - H['cx']) / nr) ** 2 + np.abs((z - (H['cz'] + 0.5)) / nr) ** 2 <= 1) & (r >= m['neck'] - 2) & (r < T['top'] + 3)
    # torso: from the shoulders' width at the top, through the chest, to the waist; a little
    # hunched (its top forward) and the chest out a little
    t0, t1 = T['top'], m['crotch'] + 1.0
    u = np.clip((r - t0) / max(t1 - t0, 1), 0, 1)
    rx_t = np.interp(u, [0, 0.12, 0.45, 1.0], [T['shoulder'] * 0.62, T['shoulder'] * 0.98, T['chest'] * 1.02, T['waist']])
    cz_t = T['cz'] - t['torso']['hunch'] * (1 - u) - t['torso']['chest_out'] * np.sin(np.pi * np.clip(u * 1.6, 0, 1)) * 0.5
    rz_t = T['rz'] * (0.92 + 0.08 * np.sin(np.pi * u))
    out['torso'] = (np.abs((x - T['cx']) / rx_t) ** 2.6 + np.abs((z - cz_t) / rz_t) ** 2.6 <= 1) & (r >= t0) & (r < t1)
    out['torso_c'] = (T['cx'], T['cz'], T['chest'], T['rz'])
    # round shoulders where the arms start
    out['shoulders'] = np.zeros(r.shape, bool)
    for k, a in m['arms'].items():
        sr = a['r'] * t['arm_r'] * 1.25
        out['shoulders'] |= (x - a['x']) ** 2 + (r - (a['top'] + 1.5)) ** 2 + (z - (T['cz'] - 0.3)) ** 2 <= sr * sr
    # legs: each a thigh, knee and shin column and a foot, in its own swinging space
    out['legs'] = []
    hip = m['crotch'] - 1.0
    sole = m['sole'] + 1.0
    knee_r = hip + (sole - hip) * 0.45; ankle = sole - 2.2
    for k, (ang, lift) in zip(('legR', 'legL'), rig.legs):
        L = m['legs'].get(k)
        if L is None: continue
        S_ = B.lifted(lift).swung((L['x'], hip, T['cz']), ang)
        lr = L['r'] * t['leg_r']
        rr_, xx, zz = S_.r, S_.x, S_.z
        thigh = (np.abs((xx - L['x']) / (lr * 1.05)) ** 2.4 + np.abs((zz - T['cz']) / (lr * 1.12)) ** 2.4 <= 1) & (rr_ >= hip - 3) & (rr_ < knee_r)
        knee = ((xx - L['x']) / (lr * 0.95)) ** 2 + ((rr_ - knee_r) / 1.6) ** 2 + ((zz - (T['cz'] - lr * 0.35)) / (lr * 1.0)) ** 2 <= 1
        shin = (np.abs((xx - L['x']) / (lr * 0.9)) ** 2.4 + np.abs((zz - (T['cz'] + 0.2)) / (lr * 0.95)) ** 2.4 <= 1) & (rr_ >= knee_r) & (rr_ < ankle + 0.5)
        fz0, fz1 = m['foot']['z0'], m['foot']['z1']
        fc, fl = (fz0 + fz1 + 1) / 2 - 0.6, max((fz1 - fz0 + 1) / 2, lr * 1.5) + 0.4
        toe_top = ankle + np.clip((fc - zz) * 0.3, 0, 1.6)
        foot = (np.abs((xx - L['x']) / (lr * 1.15)) ** 2.4 + np.abs((zz - fc) / fl) ** 2.2 <= 1) & (rr_ >= toe_top) & (rr_ < sole)
        out['legs'].append(dict(key=k, space=S_, leg=thigh | knee | shin, foot=foot, c=(L['x'], T['cz'], lr, lr)))
    # the shield arm: upper arm, forearm and a hand, hanging; in the shield's swinging space
    out['armL'] = None
    a = m['arms'].get('armL')
    if a:
        SA = SA_of((a['x'], a['top'] + 1.5, T['cz']))
        ar = a['r'] * t['arm_r']
        sp = (a['x'], a['top'] + 1.5, T['cz'] - 0.2); el = (a['x'] + 0.4, (a['top'] + a['bot']) / 2, T['cz'] + 0.2); wr = (a['x'] + 0.2, a['bot'] - 1.2, T['cz'] - 0.3)
        upper = SA.capsule(sp, el, ar); fore = SA.capsule(el, wr, ar * 0.9)
        hr_ = a['r'] * t['hand_r']
        hand = SA.ell(a['bot'] - 0.6, wr[0], wr[2], hr_ * 0.95, hr_, hr_ * 1.05, 2.4)
        out['armL'] = dict(space=SA, arm=upper | fore, hand=hand, c=(a['x'], T['cz'], ar, ar))
    # the sword arm's rest (where it hangs in the sprite) and size
    b = m['arms'].get('armR', dict(x=T['cx'] - T['shoulder'], top=T['top'], bot=m['crotch'] - 2, r=3.0))
    out['armR'] = dict(x=b['x'], top=b['top'], bot=b['bot'], r=b['r'] * t['arm_r'], hand=b['r'] * t['hand_r'], cz=T['cz'])
    out['m'] = m
    return out

def features(race, B, out, face_img, skin_ramp):
    """The race's own features, made by hand. Returns a list of (mask, kind) where kind is
    'skin' (painted as skin) or a colour ramp to paint with."""
    m = out['m']; t = m['tune']; H = m['head']
    r, x, z = B.r, B.x, B.z
    cx, cz, rx, rz = H['cx'], H['cz'], H['rx'], H['rz']
    hr0, hr1 = m['top'], m['neck'] + 1.0
    front = cz - rz                                          # the face's plane
    res = []
    def cone(base, tip, r0, r1=0.3):
        base, tip = np.asarray(base, float), np.asarray(tip, float); d = tip - base; L2 = d @ d
        q = np.stack([x - base[0], r - base[1], z - base[2]], -1)
        tq = np.clip((q @ d) / L2, 0, 1)
        perp = np.linalg.norm(q - tq[..., None] * d, axis=-1)
        return ((q @ d) >= 0) & ((q @ d) <= L2) & (perp <= r0 + (r1 - r0) * tq)
    def blade(root_r, root_x, tip_r, tip_x, width, thick, zc_root, zc_tip):
        """An ear: a flat leaf from its root on the head to a point."""
        mk = np.zeros(r.shape, bool)
        for k in range(32):
            u = k / 31
            cr_, cx_ = root_r + (tip_r - root_r) * u, root_x + (tip_x - root_x) * u
            w_ = width * (1 - 0.88 * u) + 0.3
            mk |= ((x - cx_) ** 2 + (r - cr_) ** 2 <= w_ * w_) & (np.abs(z - (zc_root + (zc_tip - zc_root) * u)) <= thick * (1 - 0.4 * u) + 0.25)
        return mk
    feats = t.get('features', [])
    E = m.get('explicit')
    if E:
        res = []
        ivory = face_img[(face_img[:, :, :3].sum(2) > 520) & (face_img[:, :, 3] > 0)]
        iv = sorted([tuple(c) + (255,) for c in (np.unique(ivory[:, :3], axis=0).tolist() if len(ivory) else [[230, 222, 190]])] +
                    [(150, 140, 110, 255)], key=lambda c: sum(c[:3]))
        hfront = E['cz'] - 11.4
        if 'ears' in E:
            e = E['ears']; er = np.zeros(r.shape, bool)
            for s_ in (-1, 1):
                er |= blade(e['root'][0], E['cx'] + s_ * e['root'][1], e['tip'][0], E['cx'] + s_ * e['tip'][1], e['width'], e['thick'], E['cz'] + 0.5, E['cz'] + 1.2)
            res.append((er, 'skin'))
        if 'tusks' in E:
            tk_ = E['tusks']; tk = np.zeros(r.shape, bool)
            for s_ in (-1, 1):
                bx = E['cx'] + s_ * tk_['dx']
                tk |= cone((bx, tk_['base_row'], hfront - 0.2), (bx + s_ * 0.2, tk_['top_row'], hfront - 0.9), tk_['r'], 0.22)
            res.append((tk, iv))
        return res
    # colours the face picture draws for teeth/tusks (light) - from the face itself
    light = face_img[(face_img[:, :, :3].sum(2) > 520) & (face_img[:, :, 3] > 0)]
    ivory = [tuple(c) for c in (np.unique(light[:, :3], axis=0).tolist() if len(light) else [[230, 222, 190]])]
    ivory_ramp = sorted([c + (255,) for c in ivory] + [(170, 158, 120, 255), (120, 108, 80, 255)], key=lambda c: sum(c[:3]))
    if 'tusks' in feats:
        # two tusks up out of the lower jaw, a little forward, where the sprite draws them
        tk = np.zeros(r.shape, bool)
        for s in (-1, 1):
            bx = cx + s * rx * 0.42
            tk |= cone((bx, hr1 - 2.2, front - 0.9), (bx + s * 0.4, hr1 - 6.2, front - 2.0), 1.15, 0.25)
        res.append((tk, ivory_ramp))
    if 'pointed_ears' in feats:
        er = np.zeros(r.shape, bool)
        for s in (-1, 1):
            er |= blade(hr0 + (hr1 - hr0) * 0.4, cx + s * (rx - 0.6), hr0 + 1.0, cx + s * (rx + 5.0), 2.6, 0.7, cz + 0.4, cz + 1.4)
        res.append((er, 'skin'))
    if 'brow' in feats:
        # a heavy brow over the eyes
        br = (np.abs((r - (hr0 + (hr1 - hr0) * 0.36)) / 1.2) ** 2 + np.abs((x - cx) / (rx * 0.8)) ** 4 + np.abs((z - (front - 0.2)) / 1.4) ** 2) <= 1
        res.append((br & (z < front + 0.6), 'skin_dark'))
    if 'big_ears' in feats:
        er = np.zeros(r.shape, bool)
        for s in (-1, 1):
            er |= blade(hr0 + (hr1 - hr0) * 0.45, cx + s * (rx - 0.8), hr0 + 0.2, cx + s * (rx + 6.8), 3.4, 0.7, cz + 0.6, cz + 2.0)
        res.append((er, 'skin'))
    if 'nose_point' in feats:
        res.append((cone((cx, hr0 + (hr1 - hr0) * 0.72, front + 0.4), (cx, hr0 + (hr1 - hr0) * 0.78, front - 2.4), 1.2, 0.35), 'skin'))
    if 'nose_round' in feats:
        nr_ = hr0 + (hr1 - hr0) * 0.66
        res.append((((x - cx) / 1.8) ** 2 + ((r - nr_) / 1.7) ** 2 + ((z - (front - 0.2)) / 1.6) ** 2 <= 1, 'skin'))
    if 'small_ears' in feats:
        er = np.zeros(r.shape, bool)
        for s in (-1, 1):
            er |= ((x - (cx + s * (rx + 0.6))) / 1.0) ** 2 + ((r - (hr0 + (hr1 - hr0) * 0.55)) / 2.2) ** 2 + ((z - (cz + 0.5)) / 1.8) ** 2 <= 1
        res.append((er, 'skin'))
    return res
