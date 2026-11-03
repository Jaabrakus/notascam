# A race's 3D body that looks like its own sprite body (after build3d10/racebody, whose bodies
# looked nothing like the race's base sprite). Each body part follows the sprite exactly:
#  - the front picture is cut into parts along the black lines the sprite draws between them
#    (build3d10.parts_of); each part keeps the sprite's own width at every row (made symmetric
#    about the part's middle, a median over three rows so single pixels don't make lumps) and a
#    depth from the side picture, smoothed; arms and legs are round;
#  - the colours are the sprite's own (muscles, light and dark areas): its black outline lines
#    and the dark rim inside them are filled in from the colours next to them, the face keeps
#    its eyes and mouth; the 3D light only shades them a little;
#  - the face only on the front; the head's sides without the profile's eye.
# Gear, helmets, weapons and shields come from build3d9 as before.
import numpy as np, math, copy
import compose64, build3d8, build3d9, build3d10, landmarks
from build3d6 import Space, Grid, Rig, CZ
from build3d7 import limb_space
from build3d3 import LIGHT

P = 64

def clean_picture(img, face_box=None, share=0.02, min_sum=100, keep=None):
    """The picture with its outline lines and dark edge rim filled in from the colours beside
    them. Small dark spots inside face_box (rows, cols) - eyes, mouth - stay. keep: extra colours
    that are the unit's own (hair), never filled in."""
    a = img.astype(float).copy(); al = a[:, :, 3] > 0
    lum = a[:, :, :3].sum(2)
    opq = a[al][:, :3]
    cs, ks = np.unique(opq, axis=0, return_counts=True)
    common = [c for c, k in zip(cs.tolist(), ks.tolist()) if k >= share * len(opq) and sum(c) >= min_sum]
    if keep is not None: common = common + [list(c) for c in keep]
    dark_cut = (min(sum(c) for c in common) - 2) if common else 100
    dark = al & (lum < min(dark_cut, 130))
    pad = np.pad(al, 2)
    near_edge = np.zeros_like(al)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            near_edge |= ~pad[2 + dy:2 + dy + P, 2 + dx:2 + dx + P]
    # also anything far from every common colour (the dark-brown rim along the edges), except the face
    far = al & (np.abs(a[:, :, None, :3] - np.array(common or [[128, 128, 128]])[None, None]).sum(-1).min(-1) > 70)
    line = dark | far
    if face_box is not None:
        (r0, r1), (c0, c1) = face_box
        rr, cc = np.mgrid[0:P, 0:P]
        in_face = (rr >= r0) & (rr < r1) & (cc >= c0) & (cc < c1) & ~near_edge
        line &= ~in_face                                       # eyes, brows and mouth stay
    fill = al & ~line
    out = a.copy()
    todo = line.copy()
    for _ in range(12):
        if not todo.any(): break
        acc = np.zeros(a.shape[:2] + (3,)); n = np.zeros(a.shape[:2])
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            sh = np.roll(np.roll(out[:, :, :3], dy, 0), dx, 1); sf = np.roll(np.roll(fill, dy, 0), dx, 1)
            acc += sh * sf[:, :, None]; n += sf
        can = todo & (n > 0)
        out[can, :3] = acc[can] / n[can][:, None]
        fill |= can; todo &= ~can
    out[todo, :3] = np.array(common[0]) if common else out[todo, :3]
    return out.astype(np.int32)

def profile(runs, side_of, smooth=1, symmetric=True):
    """Per row: (cx, rx, cz, rz) of a part. Widths symmetric about the part's middle and a median
    over 2*smooth+1 rows; depths from side_of(row) smoothed with a low polynomial."""
    rows = sorted(r for r in runs if side_of(r) is not None)
    if not rows: return {}
    cxs = np.array([(runs[r][0] + runs[r][1] + 1) / 2 for r in rows]); w = np.array([(runs[r][1] - runs[r][0] + 1) / 2 for r in rows])
    cx0 = float(np.median(cxs))
    if symmetric: cxs = np.full(len(rows), cx0)
    ws = np.array([np.median(w[max(0, i - smooth - 1):i + smooth + 2]) for i in range(len(rows))])
    ws = np.array([np.mean(ws[max(0, i - 1):i + 2]) for i in range(len(rows))]) + 0.5      # softened steps
    zs = np.array([side_of(r) for r in rows], float)
    czs = (zs[:, 0] + zs[:, 1] + 1) / 2; rzs = (zs[:, 1] - zs[:, 0] + 1) / 2 + 0.4
    R = np.array(rows, float)
    d = min(2, len(rows) - 1)
    czs = np.polyval(np.polyfit(R, czs, d), R); rzs = np.polyval(np.polyfit(R, rzs, min(3, len(rows) - 1)), R)
    return {r: (float(cxs[i]), float(ws[i]), float(czs[i]), float(max(rzs[i], 1.0))) for i, r in enumerate(rows)}

def solid(sp, prof, p=2.4, pfront=None):
    """A part from its profile: at each row a superellipse; rows blended for smooth sides."""
    r, x, z = sp.r, sp.x, sp.z
    m = np.zeros(r.shape, bool)
    if not prof: return m
    rows = sorted(prof)
    for i, row in enumerate(rows):
        cx, rx, cz, rz = prof[row]
        sel = (r >= row) & (r < row + 1)
        if not sel.any(): continue
        frac = r - row
        nxt = prof.get(row + 1, prof[row])
        rx_ = rx + (nxt[1] - rx) * np.clip(frac - 0.5, 0, 1) * 0.5        # a little blending toward the next row
        rz_ = rz + (nxt[3] - rz) * np.clip(frac - 0.5, 0, 1) * 0.5
        pz = p if pfront is None else np.where(z < cz, pfront, p)
        m |= sel & (np.abs((x - cx) / rx_) ** p + np.abs((z - cz) / rz_) ** pz <= 1)
    return m

def painter(pics, centre, front=50, back=50, face=None, light=True):
    """Paints from the cleaned pictures by the direction a block faces (front from the front
    picture, back from the back, sides from the sides), lightly lit."""
    def paint(r, x, z, n):
        cx, cz, rx, rz = centre
        ang = np.degrees(np.arctan2((x - cx) / max(rx, 1e-3), -(z - cz) / max(rz, 1e-3)))
        sec = np.where(np.abs(ang) <= front, 0, np.where(np.abs(ang) >= 180 - back, 1, np.where(ang > 0, 3, 2)))
        pr = np.clip(r.astype(int), 0, P - 1)
        out = np.zeros((len(r), 4), np.int32)
        for si, d in enumerate('SNEW'):
            m = sec == si
            if not m.any(): continue
            img, colf = pics[d]
            c = np.clip(colf(np.where(np.isin(d, ['S', 'N']), x, z)[m]).astype(int), 0, P - 1)
            rr = pr[m]
            px_ = img[rr, c].copy()
            # where the picture is empty (a part sticks out past the drawn outline), the nearest drawn pixel in the row
            empty = px_[:, 3] == 0
            if empty.any():
                for k in np.nonzero(empty)[0]:
                    row = img[rr[k]]; ok = np.nonzero(row[:, 3] > 0)[0]
                    if len(ok): px_[k] = row[ok[np.argmin(np.abs(ok - c[k]))]]
            out[m] = px_
        if light:
            d = n @ LIGHT
            k = np.select([d > 0.6, d > 0.0, d > -0.4], [1.08, 1.0, 0.9], 0.8)
            out[:, :3] = np.clip(out[:, :3] * k[:, None], 0, 255)
        out[:, 3] = 255
        return out
    return paint

def build(lo, rig=None, sub=2, zoff=12):
    rig = rig or Rig()
    race = getattr(lo, 'race', 'Human')
    if race == 'Human':
        return build3d8.build(lo, rig, sub=sub, zoff=zoff)
    if not getattr(lo, 'body', None): lo.body = ('Races64/%s.dmi' % race, landmarks.body_state(race))
    M9, full = build3d9.build(lo, rig, sub=sub, zoff=zoff, keep_base=False)
    pp = build3d8.prepare(lo)
    W = build3d9.Warp(race)
    S = build3d10.parts_of(race); side = S['side']
    import dmi
    d_ = dmi.load(landmarks.R + race + '.dmi')[landmarks.body_state(race)]
    raw = {f: np.asarray(dmi.frame(d_, f).convert('RGBA')).astype(np.int32) for f in 'SNEW'}
    hrows = sorted(S['head']); hcols = [c for r in hrows for c in S['head'][r]]
    face_box = ((hrows[0] + 2, S['neck'] + 1), (min(hcols) + 2, max(hcols) - 1))
    clean = {f: clean_picture(raw[f], face_box if f == 'S' else None) for f in 'SNEW'}
    # the head's sides and back without the profile's eye: anything not like the skin there becomes skin
    opq = clean['S'][raw['S'][:, :, 3] > 0][:, :3]
    cs, ks = np.unique(opq, axis=0, return_counts=True)
    skins = np.array([c for c, k in zip(cs.tolist(), ks.tolist()) if k >= 0.02 * len(opq) and sum(c) >= 100] or [cs[np.argmax(ks)].tolist()])
    head_pics = {}
    for f in 'NEW':
        im = clean[f].copy()
        dist = np.abs(im[:, :, None, :3] - skins[None, None]).sum(-1).min(-1)
        bad = (dist > 60) & (im[:, :, 3] > 0)
        rr_, cc_ = np.mgrid[0:P, 0:P]; bad &= rr_ <= S['neck'] + 1
        im[bad, :3] = skins[np.abs(skins.sum(1) - np.median(skins.sum(1))).argmin()]
        head_pics[f] = im
    # alignment of the pictures with the model: S by x, N mirrored, E and W by depth
    sN = 0; sW = 0
    colS = lambda v: v; colN = lambda v: P - 1 - v + sN; colE = lambda v: P - 1 - v; colW = lambda v: v - sW
    pics = {'S': (clean['S'], colS), 'N': (clean['N'], colN), 'E': (clean['E'], colE), 'W': (clean['W'], colW)}
    hpics = {'S': (clean['S'], colS), 'N': (head_pics['N'], colN), 'E': (head_pics['E'], colE), 'W': (head_pics['W'], colW)}
    G = Grid(sub); G.z = G.z - zoff; G.center = (32.0 * sub, (CZ + zoff) * sub)
    world = Space(G.r, G.x, G.z); B = world.lifted(rig.rise)
    dressed, cover, skin, body = build3d8.dressed, pp.cover, pp.skin, pp.body
    worn_gear = any(getattr(lo, k) for k in ('chest', 'legs', 'arms'))
    def paint_part(centre, front=50, sides='EW', bare_only=None):
        """The sprite's own colours where no gear is worn; with gear, build3d8's painter (the gear's own colours)."""
        if worn_gear:
            return None
        return painter(pics, centre, front=front)
    # torso
    tprof = profile(S['torso'], lambda row: side.get(row))
    tcx = float(np.median([v[0] for v in tprof.values()])) if tprof else 32.0
    tcz = float(np.median([v[2] for v in tprof.values()])) if tprof else CZ
    trz = float(np.median([v[3] for v in tprof.values()])) if tprof else 8.0
    trx = float(np.median([v[1] for v in tprof.values()])) if tprof else 8.0
    torso = solid(B, tprof, p=2.6)
    tcen = (tcx, tcz, trx, trz)
    G.add(torso, painter(pics, tcen) if not worn_gear else dressed(cover(pp.chest, pp.legs), lambda rr: tcen, front=50), lit=True, space=B)
    # legs: round, from the sprite's leg widths, each swinging about its hip; feet from the side picture
    hip = S['crotch'] - 1.0
    for key, (ang, lift) in zip(('legR', 'legL'), rig.legs):
        runs = S[key]
        if not runs: continue
        lp = profile(runs, lambda row: (tcz - 4, tcz + 3), symmetric=True)
        if not lp: continue
        lcx = float(np.median([v[0] for v in lp.values()])); lr = float(np.median([v[1] for v in lp.values()]))
        lp = {r: (lcx, v[1], tcz - 0.5, v[1] * 1.05) for r, v in lp.items()}
        for r_ in range(int(hip) - 2, min(lp)):                     # up into the hips
            lp[r_] = (lcx, lr, tcz - 0.5, lr * 1.05)
        S_ = B.lifted(lift).swung((lcx, hip, tcz), ang)
        leg = solid(S_, lp, p=2.3)
        fz = side.get(S['sole'], (tcz - 5, tcz + 4))
        fc, fl = (fz[0] + fz[1] + 1) / 2, max((fz[1] - fz[0] + 1) / 2 + 0.4, lr * 1.3)
        foot = (np.abs((S_.x - lcx) / (lr * 1.12)) ** 2.4 + np.abs((S_.z - fc) / fl) ** 2.2 <= 1) & (S_.r >= S['sole'] - 2.0) & (S_.r < S['sole'] + 1)
        lc = (lcx, tcz, lr, lr)
        G.add(leg | foot, painter(pics, lc) if not worn_gear else dressed(cover(pp.legs, bare=skin), lambda rr, c=lc: c, front=50,
              sides='E' if key == 'legR' else 'W'), lit=True, space=S_)
    # the shield arm: round, from the sprite's arm widths, hanging and swinging with the shield
    if S['armL']:
        ap = profile(S['armL'], lambda row: (tcz - 3, tcz + 2))
        acx = float(np.median([v[0] for v in ap.values()])); ar = float(np.median([v[1] for v in ap.values()]))
        ap = {r: (acx, v[1], tcz - 0.3, v[1]) for r, v in ap.items()}
        top = min(ap)
        for r_ in range(top - 3, top):                                # up into the shoulder
            ap[r_] = (acx, ar * 1.1, tcz - 0.3, ar * 1.1)
        SA = B.swung((acx, top + 1.0, tcz), rig.shield)
        arm = solid(SA, ap, p=2.2)
        ac = (acx, tcz, ar, ar)
        G.add(arm, painter(pics, ac, front=55) if not worn_gear else dressed(cover(pp.armL, pp.chest, bare=skin), lambda rr: ac, front=55, sides=''),
              lit=True, space=SA)
    # the sword arm: with no weapon it hangs like the other, as in the sprite
    if S['armR'] and not lo.weapon:
        bp = profile(S['armR'], lambda row: (tcz - 3, tcz + 2))
        bcx = float(np.median([v[0] for v in bp.values()])); br = float(np.median([v[1] for v in bp.values()]))
        bp = {r: (bcx, v[1], tcz - 0.3, v[1]) for r, v in bp.items()}
        top = min(bp)
        for r_ in range(top - 3, top):
            bp[r_] = (bcx, br * 1.1, tcz - 0.3, br * 1.1)
        arm = solid(B, bp, p=2.2)
        bc = (bcx, tcz, br, br)
        G.add(arm, painter(pics, bc, front=55) if not worn_gear else dressed(cover(pp.armR, pp.chest, bare=skin), lambda rr: bc, front=55, sides=''),
              lit=True, space=B)
    # the sword arm: posed; its colours from where it hangs in the sprite
    elif S['armR']:
        rr_ = S['armR']
        bp = profile(rr_, lambda row: (tcz - 3, tcz + 2))
        bcx = float(np.median([v[0] for v in bp.values()])); br = float(np.median([v[1] for v in bp.values()]))
        top, bot = min(rr_), max(rr_)
        J = M9.joints
        to_race = lambda p_: np.array([v[0] for v in W.to_race(np.array([p_[1]]), np.array([p_[0]]), np.array([p_[2]]))])[[1, 0, 2]]
        el, fi = to_race(J['elbow']), to_race(J['fist'])
        sh = np.array([bcx, top + 1.5 - rig.rise, tcz])
        hand_r = max(br, max(v[1] for r, v in bp.items() if r >= bot - 3))
        E0 = np.array([bcx, (top + bot) / 2, tcz]); W0 = np.array([bcx, bot - 1.0, tcz])
        US = limb_space(world, sh, el, np.array([bcx, top + 1.5, tcz]), E0); FS = limb_space(world, el, fi, E0, W0)
        upper = world.capsule(sh, el, br) | world.ell(sh[1], sh[0], sh[2], br * 1.15, br * 1.15, br * 1.15)
        fore = world.capsule(el, fi, br * 0.95)
        fist = world.ell(fi[1], fi[0], fi[2], hand_r, hand_r, hand_r * 1.05, 2.6)
        bc = (bcx, tcz, br, br)
        G.add(upper, painter(pics, bc, front=55) if not worn_gear else dressed(cover(pp.armR, pp.chest, bare=skin), lambda rr: bc, front=55, sides=''), lit=True, space=US)
        G.add(fore | fist, painter(pics, bc, front=55) if not worn_gear else dressed(cover(pp.armR, pp.chest, bare=skin), lambda rr: bc, front=55, sides=''), lit=True, space=FS)
    # head: the sprite's head outline, flat in front; the face on the front only
    hprof = profile(S['head'], lambda row: side.get(row))
    hcx = float(np.median([v[0] for v in hprof.values()])); hcz = float(np.median([v[2] for v in hprof.values()]))
    hrx = float(np.max([v[1] for v in hprof.values()])); hrz = float(np.median([v[3] for v in hprof.values()]))
    head = solid(B, hprof, p=2.4, pfront=4.0)
    neck = B.col(S['neck'] - 1, S['neck'] + 3, tcx, tcz, max(hrx * 0.5, 2.5), max(hrz * 0.5, 2.5)) & ~torso & ~head
    hcen = (hcx, hcz, hrx, hrz)
    G.add(head | neck, painter(hpics, hcen, front=60, back=60), lit=True, space=B)
    # ears: what the front picture draws beside the head, swept out from the head to their tips
    ear_ids = []
    if S['ears']:
        er = np.zeros(B.r.shape, bool)
        for side_ in (-1, 1):
            pts = [(r, (a + b + 1) / 2, (b - a + 1) / 2) for r, runs_ in S['ears'].items() for (a, b) in runs_ if (((a + b) / 2 > 32) == (side_ > 0))]
            if len(pts) < 2: continue
            pts = np.array(pts, float); d_ = np.abs(pts[:, 1] - 32)
            rootr = float(np.mean(pts[d_ <= d_.min() + 1, 0])); rootx = float(np.mean(pts[d_ <= d_.min() + 1, 1])) - side_ * 0.5
            far = pts[np.argmax(np.abs(pts[:, 1] - 32) + 0.01 * (32 - pts[:, 0]))]
            tipr, tipx = far[0], far[1] + side_ * far[2]
            width = max(np.ptp(pts[:, 0]) / 2, 1.5)
            for k in range(30):
                t = k / 29
                cr, cx_ = rootr + (tipr - rootr) * t, rootx + (tipx - rootx) * t
                w_ = width * (1 - 0.85 * t) + 0.35; th_ = 0.9 * (1 - 0.5 * t) + 0.35
                er |= ((B.x - cx_) ** 2 + (B.r - cr) ** 2 <= w_ * w_) & (np.abs(B.z - (hcz + 0.6 + 1.4 * t)) <= th_)
        G.add(er & ~head, painter(pics, hcen, front=88, back=88), lit=True, space=B)
        ear_ids.append(len(G.parts) - 1)
    G.paint()
    # one model: the body, gear over it, the head trimmed under a helmet (not the ears)
    owner = np.where(G.owner > 0, G.owner, 0).astype(np.int32)
    col, lit = G.col.copy(), G.lit.copy()
    if M9.helmet:
        hm = np.isin(M9.owner, list(M9.helmet))
        if hm.any():
            n_ = hm.shape[0]
            cover_xz = hm.any(axis=0)
            rim = np.where(cover_xz, n_ - 1 - np.argmax(hm[::-1], axis=0), -1)
            rows = np.arange(n_)[:, None, None]
            pad = np.zeros_like(cover_xz); rim2 = rim.copy()
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    pad |= np.roll(np.roll(cover_xz, dx, 0), dz, 1); rim2 = np.maximum(rim2, np.roll(np.roll(rim, dx, 0), dz, 1))
            inside = pad[None] & (rows <= rim2[None]) & (owner > 0) & (rows < int(S['neck'] * sub)) & ~np.isin(owner, ear_ids)
            owner[inside] = 0; col[inside] = 0; lit[inside] = False
    g = M9.owner > 0
    owner[g] = 10000 + M9.owner[g]; col[g] = M9.col[g]; lit[g] = M9.lit[g]
    return build3d9.Model(sub, G.n, owner, col, lit, G.center), full
