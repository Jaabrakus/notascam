# A race's 3D body that keeps its base sprite's exact outline (after build3d11, which built
# parts straight from the sprite's rows and broke them into fragments): rounded hand-made parts
# (racebody's head, torso, shoulders, arms, legs, feet, made a little too big) are trimmed to the
# race's own front and side outlines, each part in its own rest position, so seen from the front
# the body is the base sprite's silhouette, and from any side it is round. Unarmed, both arms
# hang as in the sprite. Painted with the sprite's own cleaned colours (build3d11), face on the
# front. Gear as before.
import numpy as np, math, copy
import compose64, build3d8, build3d9, build3d10, build3d11, landmarks, racebody
from build3d6 import Space, Grid, Rig, CZ
from build3d7 import limb_space

P = 64

def build(lo, rig=None, sub=2, zoff=12, grow=1.3):
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
    # the outlines: the front picture without its black inner lines (they part the arms and legs
    # from the body), the side picture whole
    Sa = (raw['S'][:, :, 3] > 0) & (raw['S'][:, :, :3].sum(2) >= 40)
    Ea = raw['E'][:, :, 3] > 0
    # the outer black outline belongs to the outline too
    pad = np.pad(raw['S'][:, :, 3] > 0, 1)
    edge = (raw['S'][:, :, 3] > 0) & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    Sa |= edge
    def hull(sp):
        pr = np.floor(sp.r).astype(int); px = np.floor(sp.x).astype(int); pz = np.floor(sp.z).astype(int)
        ok = (pr >= 0) & (pr < P) & (px >= 0) & (px < P) & (pz >= 0) & (pz < P)
        out = np.zeros(sp.r.shape, bool)
        out[ok] = Sa[pr[ok], px[ok]] & Ea[pr[ok], P - 1 - pz[ok]]
        return out
    hrows = sorted(S['head']); hcols = [c for r in hrows for c in S['head'][r]]
    face_box = ((hrows[0] + 2, S['neck'] + 1), (min(hcols) + 2, max(hcols) - 1))
    clean = {f: build3d11.clean_picture(raw[f], face_box if f == 'S' else None) for f in 'SNEW'}
    opq = clean['S'][raw['S'][:, :, 3] > 0][:, :3]
    cs, ks = np.unique(opq, axis=0, return_counts=True)
    skins = np.array([c for c, k in zip(cs.tolist(), ks.tolist()) if k >= 0.02 * len(opq) and sum(c) >= 100] or [cs[np.argmax(ks)].tolist()])
    head_pics = {}
    for f in 'NEW':
        im = clean[f].copy()
        dist = np.abs(im[:, :, None, :3] - skins[None, None]).sum(-1).min(-1)
        rr_, cc_ = np.mgrid[0:P, 0:P]
        bad = (dist > 60) & (im[:, :, 3] > 0) & (rr_ <= S['neck'] + 1)
        im[bad, :3] = skins[np.abs(skins.sum(1) - np.median(skins.sum(1))).argmin()]
        head_pics[f] = im
    colS = lambda v: v; colN = lambda v: P - 1 - v; colE = lambda v: P - 1 - v; colW = lambda v: v
    pics = {'S': (clean['S'], colS), 'N': (clean['N'], colN), 'E': (clean['E'], colE), 'W': (clean['W'], colW)}
    hpics = {'S': (clean['S'], colS), 'N': (head_pics['N'], colN), 'E': (head_pics['E'], colE), 'W': (head_pics['W'], colW)}
    painter = build3d11.painter
    G = Grid(sub); G.z = G.z - zoff; G.center = (32.0 * sub, (CZ + zoff) * sub)
    world = Space(G.r, G.x, G.z); B = world.lifted(rig.rise)
    dressed, cover, skin, body = build3d8.dressed, pp.cover, pp.skin, pp.body
    worn = any(getattr(lo, k) for k in ('chest', 'legs', 'arms'))
    m = racebody.measured(race)
    T = m['torso']; H = m['head']
    tcz = T['cz']
    def paint(centre, part_pics=pics, front=50, cov=None, sides='EW'):
        if worn and cov is not None:
            return dressed(cov, lambda rr: centre, front=front, sides=sides)
        return painter(part_pics, centre, front=front)
    # --- torso: a rounded column, a little too big, trimmed to the outlines ---
    r, x, z = B.r, B.x, B.z
    t0, t1 = T['top'] - 1.0, m['crotch'] + 2.0
    u = np.clip((r - t0) / (t1 - t0), 0, 1)
    rx_t = np.interp(u, [0, 0.15, 0.5, 1.0], [T['shoulder'] * 0.8, T['shoulder'] + 2, T['chest'] + 2.5, T['waist'] + 2]) * 1.0
    torso = (np.abs((x - T['cx']) / rx_t) ** 2.4 + np.abs((z - tcz) / (T['rz'] + grow)) ** 2.4 <= 1) & (r >= t0) & (r < t1)
    torso &= hull(B)
    tc = (T['cx'], tcz, T['chest'], T['rz'])
    # arms and legs claim their own outline columns first, so the torso does not swallow them
    arm_cols = np.zeros(P, bool)
    for k in ('armL', 'armR'):
        for row, (a, b) in S[k].items(): arm_cols[a:b + 1] = True
    # --- legs: round columns down the sprite's leg outlines, feet included ---
    hip = m['crotch'] - 1.0
    for key, (ang, lift) in zip(('legR', 'legL'), rig.legs):
        L = m['legs'].get(key)
        if L is None: continue
        S_ = B.lifted(lift).swung((L['x'], hip, tcz), ang)
        lr = L['r'] + grow
        leg = (np.abs((S_.x - L['x']) / (lr * 1.1)) ** 2.4 + np.abs((S_.z - tcz) / (lr * 1.25 + 1.5)) ** 2.4 <= 1) & (S_.r >= hip - 2) & (S_.r < m['sole'] + 1)
        leg &= hull(S_) & (np.abs(S_.x - L['x']) < lr * 1.6)
        lc = (L['x'], tcz, L['r'], L['r'])
        G.add(leg, paint(lc, cov=cover(pp.legs, bare=skin), sides='E' if key == 'legR' else 'W'), lit=True, space=S_)
        torso &= ~((B.r >= hip) & (np.abs(B.x - L['x']) < lr))
    G.add(torso, paint(tc, cov=cover(pp.chest, pp.legs)), lit=True, space=B)
    # --- arms: round limbs down the sprite's arm outlines; the shield arm swings with the shield;
    #     unarmed, the sword arm hangs too ---
    def hanging_arm(key, space_of):
        rows = S[key]
        if not rows: return None
        a = m['arms'][key]
        sp = space_of((a['x'], a['top'] + 1.0, tcz))
        ar = a['r'] + grow
        rs = sorted(rows)
        cx_r = np.polyval(np.polyfit(np.array(rs, float), [(rows[q][0] + rows[q][1] + 1) / 2 for q in rs], 1), sp.r) if len(rs) > 1 else a['x']
        arm = (np.abs((sp.x - cx_r) / ar) ** 2.2 + np.abs((sp.z - (tcz - 0.4)) / ar) ** 2.2 <= 1) & (sp.r >= rs[0] - 3) & (sp.r < rs[-1] + 2)
        arm &= hull(sp)
        return sp, arm, (a['x'], tcz, a['r'], a['r'])
    got = hanging_arm('armL', lambda piv: B.swung(piv, rig.shield))
    if got:
        sp, arm, ac = got
        G.add(arm, paint(ac, front=55, cov=cover(pp.armL, pp.chest, bare=skin), sides=''), lit=True, space=sp)
    if not lo.weapon:
        got = hanging_arm('armR', lambda piv: B)
        if got:
            sp, arm, ac = got
            G.add(arm, paint(ac, front=55, cov=cover(pp.armR, pp.chest, bare=skin), sides=''), lit=True, space=sp)
    elif S['armR']:
        a = m['arms']['armR']; br = a['r'] + 0.6
        J = M9.joints
        to_race = lambda p_: np.array([v[0] for v in W.to_race(np.array([p_[1]]), np.array([p_[0]]), np.array([p_[2]]))])[[1, 0, 2]]
        el, fi = to_race(J['elbow']), to_race(J['fist'])
        sh = np.array([a['x'], a['top'] + 1.5 - rig.rise, tcz])
        E0 = np.array([a['x'], (a['top'] + a['bot']) / 2, tcz]); W0 = np.array([a['x'], a['bot'] - 1.0, tcz])
        US = limb_space(world, sh, el, np.array([a['x'], a['top'] + 1.5, tcz]), E0); FS = limb_space(world, el, fi, E0, W0)
        upper = world.capsule(sh, el, br) | world.ell(sh[1], sh[0], sh[2], br * 1.15, br * 1.15, br * 1.15)
        fore = world.capsule(el, fi, br * 0.95)
        fist = world.ell(fi[1], fi[0], fi[2], br * 1.05, br * 1.05, br * 1.1, 2.6)
        bc = (a['x'], tcz, a['r'], a['r'])
        G.add(upper, paint(bc, front=55, cov=cover(pp.armR, pp.chest, bare=skin), sides=''), lit=True, space=US)
        G.add(fore | fist, paint(bc, front=55, cov=cover(pp.armR, pp.chest, bare=skin), sides=''), lit=True, space=FS)
    # --- head: a rounded head, a little too big, trimmed to the outlines - ears and all ---
    hr0, hr1 = m['top'] - 1.0, m['neck'] + 2.0
    hcr, hrr = (hr0 + hr1) / 2, (hr1 - hr0) / 2
    p = racebody.RACES.get(race, racebody.DEFAULT)['head']['p']
    rxh = H['rx'] + 6.0                                          # wide enough to keep the ears; the outline trims it
    head = (np.abs((r - hcr) / hrr) ** p + np.abs((x - H['cx']) / rxh) ** p + np.abs((z - H['cz']) / (H['rz'] + grow)) ** np.where(z < H['cz'], 4.0, p)) <= 1
    head &= hull(B) & (r < m['neck'] + 2)
    # ears stay thin: beyond the skull, only near the head's middle depth
    beyond = np.abs(x - H['cx']) > H['rx'] - 0.5
    head &= ~beyond | (np.abs(z - (H['cz'] + 0.8)) < 1.4)
    hc = (H['cx'], H['cz'], H['rx'], H['rz'])
    G.add(head, painter(hpics, hc, front=60), lit=True, space=B)
    ear_ids = [len(G.parts) - 1]
    G.paint()
    owner = np.where(G.owner > 0, G.owner, 0).astype(np.int32)
    col, lit = G.col.copy(), G.lit.copy()
    if M9.helmet:
        hm = np.isin(M9.owner, list(M9.helmet))
        if hm.any():
            n_ = hm.shape[0]
            cover_xz = hm.any(axis=0)
            rim = np.where(cover_xz, n_ - 1 - np.argmax(hm[::-1], axis=0), -1)
            rows = np.arange(n_)[:, None, None]
            pad2 = np.zeros_like(cover_xz); rim2 = rim.copy()
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    pad2 |= np.roll(np.roll(cover_xz, dx, 0), dz, 1); rim2 = np.maximum(rim2, np.roll(np.roll(rim, dx, 0), dz, 1))
            xs = (np.arange(n_) + 0.5) / sub
            near_skull = (np.abs(xs - H['cx']) <= H['rx'] + 0.5)[None, :, None]
            inside = pad2[None] & (rows <= rim2[None]) & (owner > 0) & (rows < int(m['neck'] * sub)) & near_skull
            owner[inside] = 0; col[inside] = 0; lit[inside] = False
    g = M9.owner > 0
    owner[g] = 10000 + M9.owner[g]; col[g] = M9.col[g]; lit[g] = M9.lit[g]
    return build3d9.Model(sub, G.n, owner, col, lit, G.center), full
