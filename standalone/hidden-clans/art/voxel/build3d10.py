# A race's own 3D body (after build3d9.py, which bent the human body into each race's shape and
# looked like lumpy tubes). Here every race's body is built from its own sprite:
#  - the front picture is cut into parts along the black lines the sprite draws between them:
#    the head (and ears beside it), the torso, each arm, each leg;
#  - each part is made of rounded slices, as wide as the front picture draws it and as deep as
#    the side picture draws it (the head flatter at the front, so the face faces forward);
#  - the parts move with the rig: the legs swing about the hips, the shield arm about its
#    shoulder, the sword arm goes through the posed shoulder, elbow and fist;
#  - everything is painted with build3d8's painter from the race's own sprites (its skin as
#    drawn, its fitted gear), the face only on the front.
# Armour pieces, helmets, hair, weapons and shields still come from build3d9 (the human model's
# pieces fitted to the race); only the bare body is replaced.
import numpy as np, math
import compose64, build3d8, build3d9, landmarks
from build3d6 import Space, Grid, Rig, CZ, swing_point
from build3d7 import limb_space

P = 64

def parts_of(race):
    """The race's bare front and side pictures cut into parts. Returns per-row runs for the
    head, torso, arms and legs, and the side picture's extent per row."""
    import dmi
    d_ = dmi.load(landmarks.R + race + '.dmi')[landmarks.body_state(race)]
    pic = {f: np.asarray(dmi.frame(d_, f).convert('RGBA')).astype(int) for f in 'SE'}
    # not the outline lines (black, and the dark browns some sprites outline with): those cut
    # the picture into parts
    S = (pic['S'][:, :, 3] > 0) & (pic['S'][:, :, :3].sum(2) >= 40)
    lum = pic['S'][:, :, :3].sum(2)
    S_strict = S & ~((lum < 100) & (pic['S'][:, :, 0] >= pic['S'][:, :, 1]))
    E = (pic['E'][:, :, 3] > 0)
    m = build3d9.measure(race)
    top, neck, sole = m['top'], m['neck'], m['sole']
    rows = np.nonzero(S.any(1))[0]; top_px = int(rows.min())
    # the crotch: the lowest row where the middle column is still drawn, above the feet
    crotch = sole
    for r in range(sole, neck, -1):
        if S[r, 31:33].all(): crotch = r; break
    runs = {r: landmarks.runs(S[r]) for r in range(P)}
    out = {'head': {}, 'torso': {}, 'armL': {}, 'armR': {}, 'legL': {}, 'legR': {}, 'side': {}, 'ears': {}}
    for r in range(P):
        rr = runs[r]
        if not rr: continue
        mid = [t for t in rr if t[0] <= 32 <= t[1] + 1] or [min(rr, key=lambda t: abs((t[0] + t[1]) / 2 - 32))]
        mid = mid[0]
        if r <= neck:
            # the head: the middle run cut at the dark outline; what lies beside it is ears
            hr = landmarks.runs(S_strict[r])
            hm = [t for t in hr if t[0] <= 32 <= t[1] + 1]
            ears = [t for t in hr if t not in hm and (t[1] < (hm[0][0] if hm else 32) or t[0] > (hm[0][1] if hm else 32))]
            a, b = mid
            if hm:                                  # the head keeps its full width, less the ears
                if any(t[1] < hm[0][0] for t in ears): a = hm[0][0] - 1
                if any(t[0] > hm[0][1] for t in ears): b = hm[0][1] + 1
            out['head'][r] = (a, b)
            if ears: out['ears'][r] = ears
        elif r <= crotch:
            out['torso'][r] = mid
            for t in rr:
                if t is mid or t[1] - t[0] < 1: continue
                (out['armL'] if (t[0] + t[1]) / 2 > 32 else out['armR'])[r] = t
        else:
            legs = sorted(rr, key=lambda t: -(t[1] - t[0]))[:2]
            for t in legs:
                (out['legL'] if (t[0] + t[1]) / 2 > 32 else out['legR'])[r] = t
        e = np.nonzero(E[r])[0]
        if len(e): out['side'][r] = (P - 1 - e.max(), P - 1 - e.min())     # depth z range (front .. back)
    # arms that merge into the torso at the shoulders: split the torso there at the body's width
    tw = np.median([b - a for r, (a, b) in out['torso'].items() if r > neck + 6 and r not in out['armL']] or [16]) / 2
    for r, (a, b) in list(out['torso'].items()):
        if r in out['armL'] or r in out['armR'] or (b - a) / 2 <= tw + 1.5: continue
        out['armR'].setdefault(r, (a, int(round(32 - tw)) - 1)); out['armL'].setdefault(r, (int(round(32 + tw)), b))
        out['torso'][r] = (int(round(32 - tw)), int(round(32 + tw)) - 1)
    out.update(top=top, top_px=top_px, neck=neck, crotch=crotch, sole=sole, m=m)
    return out

def slices(sp, runs, side, p=2.4, pfront=None, shrink=0.0, zrange=None, smooth=1):
    """Rounded slices through a part: at each row, an ellipse-like section as wide as its run in
    the front picture and as deep as the side picture (or zrange(row)), each averaged with its
    neighbours so the part is smooth, not a stack of rings."""
    r, x, z = sp.r, sp.x, sp.z
    m = np.zeros(r.shape, bool)
    ri = np.floor(r).astype(int)
    dims = {}
    for row, (a, b) in runs.items():
        zr = zrange(row) if zrange else side.get(row)
        if zr is None: continue
        dims[row] = ((a + b + 1) / 2, (b - a + 1) / 2, (zr[0] + zr[1] + 1) / 2, (zr[1] - zr[0] + 1) / 2)
    for row in dims:
        near = [dims[q] for q in range(row - smooth, row + smooth + 1) if q in dims]
        cx, rx, cz, rz = (float(np.mean([t[i] for t in near])) for i in range(4))
        rx, rz = rx - shrink, rz - shrink
        if rx <= 0.3 or rz <= 0.3: continue
        pz = p if pfront is None else np.where(z < cz, pfront, p)
        sel = ri == row
        m |= sel & (np.abs((x - cx) / rx) ** p + np.abs((z - cz) / rz) ** pz <= 1)
    return m

def centre_of(runs, side, rows=None):
    rs = [r for r in runs if (rows is None or r in rows) and r in side]
    if not rs: return 32.0, CZ, 4.0, 4.0
    cx = np.mean([(runs[r][0] + runs[r][1] + 1) / 2 for r in rs]); rx = np.median([(runs[r][1] - runs[r][0] + 1) / 2 for r in rs])
    cz = np.mean([(side[r][0] + side[r][1] + 1) / 2 for r in rs]); rz = np.median([(side[r][1] - side[r][0] + 1) / 2 for r in rs])
    return cx, cz, max(rx, 1.0), max(rz, 1.0)

def fit(runs, side, deg, zfun=None):
    """A part's shape along its rows as smooth curves (polynomials fitted to the sprite's runs):
    centre and half-width across (front picture), centre and half-depth (side picture, or zfun)."""
    zf = zfun or side.get
    rows = sorted(r for r in runs if zf(r) is not None)
    if len(rows) < 2: return None
    R = np.array(rows, float) + 0.5
    cx = [(runs[r][0] + runs[r][1] + 1) / 2 for r in rows]; rx = [(runs[r][1] - runs[r][0] + 1) / 2 for r in rows]
    cz = [(zf(r)[0] + zf(r)[1] + 1) / 2 for r in rows]; rz = [(zf(r)[1] - zf(r)[0] + 1) / 2 for r in rows]
    d = min(deg, len(rows) - 1)
    rx = [v + 0.7 for v in rx]; rz = [v + 0.5 for v in rz]          # the outline drawn round each part is part of its width
    polys = [np.polyfit(R, v, d) for v in (cx, rx, cz, rz)]
    return dict(r0=rows[0], r1=rows[-1] + 1, f=lambda rr: [np.polyval(p_, rr) for p_ in polys],
                mean=(float(np.mean(cx)), float(np.mean(cz)), float(np.median(rx)), float(np.median(rz))))

def smooth_part(sp, F, p=2.4, pfront=None, round_ends=(0.0, 0.0)):
    """The solid of a fitted part: at every height a superellipse of the fitted size; the ends
    rounded off over round_ends rows (top, bottom)."""
    if F is None: return np.zeros(sp.r.shape, bool)
    r, x, z = sp.r, sp.x, sp.z
    cx, rx, cz, rz = F['f'](r)
    k = np.ones(r.shape)
    for (n_, at, sgn) in ((round_ends[0], F['r0'], 1), (round_ends[1], F['r1'], -1)):
        if n_ > 0:
            t = np.clip((r - at) * sgn / n_, 0, 1)
            k = np.minimum(k, np.sqrt(np.clip(1 - (1 - t) ** 2, 0, 1)))
    rx, rz = np.maximum(rx * k, 0.01), np.maximum(rz * k, 0.01)
    pz = p if pfront is None else np.where(z < cz, pfront, p)
    return (r >= F['r0']) & (r < F['r1']) & (np.abs((x - cx) / rx) ** p + np.abs((z - cz) / rz) ** pz <= 1)

def build(lo, rig=None, sub=2, zoff=12):
    rig = rig or Rig()
    race = getattr(lo, 'race', 'Human')
    if race == 'Human':
        return build3d8.build(lo, rig, sub=sub, zoff=zoff)
    if not getattr(lo, 'body', None): lo.body = ('Races64/%s.dmi' % race, landmarks.body_state(race))
    # 1. the gear, helmet, hair, weapon and shield fitted to the race (build3d9), without its body
    M9, full = build3d9.build(lo, rig, sub=sub, zoff=zoff, keep_base=False)
    # 2. the race's own body
    pp = build3d8.prepare(lo)
    W = build3d9.Warp(race)
    S = parts_of(race); side = S['side']
    G = Grid(sub); G.z = G.z - zoff; G.center = (32.0 * sub, (CZ + zoff) * sub)
    world = Space(G.r, G.x, G.z); B = world.lifted(rig.rise)
    dressed, cover, skin, body = build3d8.dressed, pp.cover, pp.skin, pp.body
    # the body, made like the human's: hand-made parts at the race's proportions (racebody)
    import racebody
    hip_sw = lambda piv: B.swung(piv, rig.shield)
    BP = racebody.body_parts(race, B, world, hip_sw, rig)
    tcx, tcz, trx, trz = BP['torso_c']
    robe = lo.kind('chest') == 'robe'
    for L_ in BP['legs']:
        G.add(L_['leg'] | L_['foot'], dressed(cover(pp.chest if robe else None, pp.legs, bare=skin), lambda rr, c=L_['c']: c,
                                              front=50, sides='E' if L_['key'] == 'legR' else 'W'), lit=True, space=L_['space'])
    torso = BP['torso']
    if 'explicit' in BP['m']:
        # the shoulders run straight into the body, as in the sprite: one part, no line between them
        torso = torso | BP['shoulders']
        G.add(torso, dressed(cover(pp.chest, pp.legs), lambda rr: BP['torso_c'], front=50), lit=True, space=B)
    else:
        G.add(torso, dressed(cover(pp.chest, pp.legs), lambda rr: BP['torso_c'], front=50), lit=True, space=B)
        G.add(BP['shoulders'] & ~torso, dressed(cover(pp.armL, pp.armR, pp.chest), lambda rr: BP['torso_c'], front=55), lit=True, space=B)
    if BP['armL']:
        A = BP['armL']
        for part_ in (A['arm'], A['hand'] & ~A['arm']):           # the hand its own part: a line at the wrist, as drawn
            G.add(part_, dressed(cover(pp.armL, pp.chest, bare=skin), lambda rr: A['c'], front=55, sides=''), lit=True, space=A['space'])
    # the sword arm: with no weapon it hangs like the other, as in the sprite
    R_ = BP['armR']
    if not lo.weapon and 'armR_rest' in BP:
        arm_, hand_ = BP['armR_rest']
        for part_ in (arm_, hand_ & ~arm_):
            G.add(part_, dressed(cover(pp.armR, pp.chest, bare=skin), lambda rr: (BP['armR']['x'], BP['armR']['cz'], BP['armR']['r'], BP['armR']['r']), front=55, sides=''), lit=True, space=B)
    elif not lo.weapon:
        rest = racebody.body_parts(race, B, world, lambda piv: B, rig)['armL']
        if rest is not None:
            mx = 2 * BP['m']['torso']['cx'] - rest['c'][0]
            # mirror the shield arm's rest shape to the other side
            mir = Space(B.r, 2 * BP['m']['torso']['cx'] - B.x, B.z)
            BPm = racebody.body_parts(race, mir, mir, lambda piv: mir, rig)['armL']
            G.add(BPm['arm'] | BPm['hand'], dressed(cover(pp.armR, pp.chest, bare=skin), lambda rr: (mx,) + tuple(rest['c'][1:]), front=55, sides=''), lit=True, space=B)
    R_ = BP['armR'] if lo.weapon else None
    if R_ is None: pass
    else:
     R_ = BP['armR']
     J = M9.joints
     to_race = lambda p_: np.array([v[0] for v in W.to_race(np.array([p_[1]]), np.array([p_[0]]), np.array([p_[2]]))])[[1, 0, 2]]
     el, fi = to_race(J['elbow']), to_race(J['fist'])
     sh = np.array([R_['x'], R_['top'] + 1.5 - rig.rise, R_['cz']])
     rad = max(2.3, R_['r'])
     E0 = np.array([R_['x'], (R_['top'] + R_['bot']) / 2, R_['cz']]); W0 = np.array([R_['x'], R_['bot'] - 1.0, R_['cz']])
     US = limb_space(world, sh, el, np.array([R_['x'], R_['top'] + 1.5, R_['cz']]), E0); FS = limb_space(world, el, fi, E0, W0)
     upper = world.capsule(sh, el, rad) | world.ell(sh[1], sh[0], sh[2], rad * 1.1, rad * 1.1, rad * 1.1)
     fore = world.capsule(el, fi, rad * 0.88)
     fist = world.ell(fi[1], fi[0], fi[2], R_['hand'] * 1.05, R_['hand'] * 1.05, R_['hand'] * 1.15, 2.4)
     armc = lambda rr: (R_['x'], R_['cz'], R_['r'], R_['r'])
     G.add(upper, dressed(cover(pp.armR, pp.chest, bare=skin), armc, front=55, sides=''), lit=True, space=US)
     G.add(fore | fist, dressed(cover(pp.armR, pp.chest, bare=skin), armc, front=55, sides=''), lit=True, space=FS)
    # neck and head, the face only on the front
    hcx, hcz, hrx, hrz = BP['head_c']
    head = BP['head']
    face = (pp.face_img, 66)
    G.add(BP['neck'] & ~torso & ~head, dressed([body], lambda rr: (hcx, hcz, hrx, hrz), front=58), lit=True, space=B)
    G.add(head, dressed([body], lambda rr: (hcx, hcz, hrx, hrz), front=66, back=60, face=face), lit=True, space=B)
    if BP.get('cap') is not None:
        # the sprite's dark brown band over the top of the head, in its own browns
        tp = pp.face_img; top_px = tp[:int(BP['m']['top']) + 4][(tp[:int(BP['m']['top']) + 4, :, 3] > 0)]
        browns = [tuple(c) + (255,) for c in np.unique(top_px[:, :3], axis=0).tolist() if c[0] > c[1] + 15 and sum(c) > 40] or [(49, 8, 0, 255), (55, 27, 0, 255)]
        browns = sorted(browns, key=lambda c: sum(c[:3])) + [(88, 44, 16, 255)]
        G.add(BP['cap'], build3d8.lit(browns, np.array([0, 1, len(browns) - 1, len(browns) - 1])), lit=True, space=B)
    # the race's own features, made by hand
    ear_ids = []
    dw = body.drawn
    for mask, kind in racebody.features(race, B, BP, pp.face_img, dw.get('ramp')):
        mask = mask & ~head if kind != 'skin_dark' else mask
        if kind == 'skin':
            G.add(mask, dressed([body], lambda rr: (hcx, hcz, hrx, hrz), front=30, back=30), lit=True, space=B)
        elif kind == 'skin_dark':
            G.add(mask, build3d8.lit(dw['ramp'], np.maximum(np.asarray(dw['levels']) - 1, 0)), lit=True, space=B)
        else:
            G.add(mask, build3d8.lit(kind, np.array([1, 2, 3, 3])), lit=True, space=B)
            G.noline = getattr(G, 'noline', set()) | {len(G.parts) - 1}      # tusks sit on the face: no dark line round them
        ear_ids.append(len(G.parts) - 1)
    ear_id = ear_ids
    G.paint()
    # 3. one model: the race body, then the fitted gear over it
    owner = np.where(G.owner > 0, G.owner, 0).astype(np.int32)
    col, lit = G.col.copy(), G.lit.copy()
    # under a helmet the race's head is trimmed to the helmet: nothing above its rim, in any
    # column the helmet covers, pokes through it
    if M9.helmet:
        hm = np.isin(M9.owner, list(M9.helmet))
        if hm.any():
            cover_xz = hm.any(axis=0)
            rim = np.where(cover_xz, n_ - 1 - np.argmax(hm[::-1], axis=0), -1) if (n_ := hm.shape[0]) else None
            rows = np.arange(hm.shape[0])[:, None, None]
            inside = cover_xz[None] & (rows <= rim[None] + 1) & (owner > 0)
            # widen a little so the head does not show at the helmet's edges
            pad = np.zeros_like(cover_xz)
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1): pad |= np.roll(np.roll(cover_xz, dx, 0), dz, 1)
            rim2 = np.where(pad, np.maximum(rim, 0), -1)
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1): rim2 = np.maximum(rim2, np.roll(np.roll(rim, dx, 0), dz, 1))
            inside |= pad[None] & (rows <= rim2[None]) & (owner > 0) & (rows < int(S['neck'] * sub))
            inside &= ~np.isin(owner, ear_id if isinstance(ear_id, list) else [ear_id])   # ears, tusks: they stick out as drawn
            owner[inside] = 0; col[inside] = 0; lit[inside] = False
    g = M9.owner > 0
    owner[g] = 10000 + M9.owner[g]; col[g] = M9.col[g]; lit[g] = M9.lit[g]
    if not ear_id and not S['ears']: build3d9.add_features(owner, col, lit, W, lo, sub, zoff)   # horns and such for races without hand-made features yet
    M_ = build3d9.Model(sub, G.n, owner, col, lit, G.center)
    M_.noline = getattr(G, 'noline', set())
    return M_, full
