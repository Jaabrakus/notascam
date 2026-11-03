# The balloon, refined (after inflate.py): the sprite's front picture blown up into 3D, now
#  - round from the game camera too: each row is blown up to the side picture's depth with a
#    smooth scale (not row by row), so the crown and shoulders round off instead of standing up
#    as flat-topped slabs;
#  - with a flat face: the face region of the head is pushed forward to an even plane, so the
#    eyes, tusks and mouth face the camera rather than bending round a curve;
#  - painted on every side: each surface block takes the picture facing the way it faces -
#    front, back, left or right - the side pictures for the sides (the head's sides in skin only,
#    as the side pictures draw the eye in profile).
import sys, numpy as np, dmi, landmarks, build3d9, build3d10, build3d11, render3, carve
from build3d3 import normals
from inflate import distance
from PIL import Image

P = 64
LAST = {}

def pictures(race):
    st = dmi.load(landmarks.R + race + '.dmi')[landmarks.body_state(race)]
    return {f: np.asarray(dmi.frame(st, f).convert('RGBA')).astype(np.int32) for f in 'SNEW'}

def blur(a, n=2):
    k1 = np.array([1, 4, 6, 4, 1], float); k1 /= k1.sum()
    for _ in range(n):
        a = np.apply_along_axis(lambda v: np.convolve(v, k1, 'same'), 0, a)
        a = np.apply_along_axis(lambda v: np.convolve(v, k1, 'same'), 1, a)
    return a

def occlusion(solid, sn, rad=3, out=4.0, strength=2.2, base=0.12, floor=0.5):
    """How shut in each surface block is: the share of solid in a box (rad blocks each way) set
    out from the surface along its normal. On open surfaces the box is in the air whatever the
    blocks' little steps (sampling at the surface itself striped every terrace); in a crease - arm
    against body, between the legs, under the chin - it reaches the other side and the block goes
    darker, the way the sprites draw those places black."""
    s = solid.astype(np.float32)
    for ax in range(3):
        c = np.cumsum(np.pad(s, [(rad + 1, rad) if a_ == ax else (0, 0) for a_ in range(3)]), axis=ax)
        hi = [slice(None)] * 3; lo = [slice(None)] * 3
        hi[ax] = slice(2 * rad + 1, None); lo[ax] = slice(0, -(2 * rad + 1))
        s = c[tuple(hi)] - c[tuple(lo)]
    occ = s / (2 * rad + 1) ** 3
    n = solid.shape[0]
    ao = np.ones(solid.shape, np.float32)
    R, X, Z = np.nonzero(solid)
    nr = sn[R, X, Z]
    # normals are (x, y up, z); the grid is (row down, x, z)
    rr = np.clip(np.round(R - nr[:, 1] * out), 0, n - 1).astype(int)
    xx = np.clip(np.round(X + nr[:, 0] * out), 0, n - 1).astype(int)
    zz = np.clip(np.round(Z + nr[:, 2] * out), 0, n - 1).astype(int)
    ao[R, X, Z] = np.clip(1.0 - strength * (occ[rr, xx, zz] - base), floor, 1.0)
    return ao

RACE_SETTINGS = {'FrogMan': dict(web_gap=3)}          # per-race defaults (webbed feet)

def inflate(race, sub=2, **kw):
    for k, v in RACE_SETTINGS.get(race, {}).items(): kw.setdefault(k, v)
    return _inflate(race, sub, **kw)

def _inflate(race, sub=2, face_flat=0.9, scale_smooth=9, body_depth=1.0, limb_depth=1.0, ao_strength=0.0, cap_rows=0, dome_p=3.2, head_mode='r2', body_mode='new', leg_cap=1.3, torso_cap=1.3, head_fill=0.5, foot_len=0.72, head_scale=1.1, head_p=2.8, head_scale_y=0.9, style='grey', normal_sigma=2.8, web_gap=0, smooth_light=True, bright=1.06, ear_rim=True, ear_grow=8, eye_pop=0.6, ear_thick=2.0, ear_cup=0.25, ear_edge=True, ear_full=True, ear_sweep=0.15, head_outline_depth=False, arm_back=0.0, arm_deep=0.0, pronounce=1.4, pronounce_chest=0.0, horn_follow=True, horn_len=1.0, horn_curve=False, horn_proc=False, horn_bend=1.0, horn_thick=0.6, horn_lean=1.0, horn_smear=True, horn_edge=(60, 26, 22), horn_taper=0.08, part_lines=True, tones=1, min_line=4):
    raw = pictures(race)
    S = raw['S']; alpha = S[:, :, 3] > 0; lum = S[:, :, :3].sum(2)
    # black gaps joined to the outside are empty space (arms and legs come apart); pupils stay
    black = alpha & (lum < 40)
    gap = np.zeros((P + 2, P + 2), bool); gap[np.pad(~alpha, 1)] = True
    bl = np.pad(black, 1)
    for _ in range(P):
        g2 = gap.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)): g2 |= np.roll(np.roll(gap, dy, 0), dx, 1)
        new_ = g2 & bl & ~gap
        if not new_.any(): break
        gap |= new_
    gapm = gap[1:-1, 1:-1] & (raw['S'][:, :, 3] > 0)
    alpha &= ~gap[1:-1, 1:-1]
    # ...but the black line across an ankle (between leg and foot) is the leg: drawn pixels with
    # body above and below in the lower body join them, or the feet float
    lowr = int(np.nonzero(alpha.any(1))[0].max()) if alpha.any() else P - 1
    ankle = np.zeros((P, P), bool)
    for r in range(max(lowr - 8, 1), lowr):
        for c in np.nonzero(gapm[r] & ~alpha[r])[0]:
            up = alpha[max(r - 2, 0):r, c].any(); dn = alpha[r + 1:r + 3, c].any()
            if up and dn: alpha[r, c] = True; ankle[r, c] = True
    # webbed feet (the frog): the sprite draws a splayed foot as a black wedge with green toe
    # lines in it - the black IS the foot, and gap removal (which frees arms and legs) took it away,
    # leaving thin diagonal sticks. In the lowest web_gap rows the drawn silhouette stays whole.
    if web_gap:
        for r in range(lowr - web_gap + 1, lowr + 1):
            alpha[r] = raw['S'][r, :, 3] > 0
    alpha0 = alpha.copy()
    # the round profile: distance to the edge, the local half-width, smoothed
    d = distance(alpha)
    w = d.copy()
    for _ in range(3):
        p = np.pad(w, 1)
        w = np.maximum(np.maximum.reduce([p[1:-1, 1:-1], p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]]) * (d > 0), d)
    h = np.sqrt(np.clip(w ** 2 - (w - d) ** 2, 0, None))
    m_ = alpha.astype(float)
    for _ in range(2):
        h = np.where(alpha, blur(h * m_, 1) / np.maximum(blur(m_, 1), 1e-3), 0)
        h = np.minimum(h, np.sqrt(np.clip(d * (2 * np.maximum(w, d) - d), 0, None)) * 1.15 + 0.5)
    # as deep as the side picture, with a smooth scale down the body
    E = raw['E']
    # the side picture's depth without its outline, as the front's width is without its own (with
    # the outline the torso came out 22 px deep, as deep as it is wide)
    Ea = (E[:, :, 3] > 0); Eb = Ea & (E[:, :, :3].sum(2) < 40)
    eg = np.zeros((P + 2, P + 2), bool); eg[np.pad(~Ea, 1)] = True; ebl = np.pad(Eb, 1)
    for _ in range(1):                                                  # just the outline: its dark shading is body (legs, heels)
        g2 = eg.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)): g2 |= np.roll(np.roll(eg, dy, 0), dx, 1)
        eg |= g2 & ebl
    Ea &= ~eg[1:-1, 1:-1]
    # per row the side picture's own run (the longest, small breaks closed; not a tail or a hand
    # drawn apart from the body): its depth and where its middle is - unsmoothed but for single
    # rows that jump, so the side view keeps the sprite's profile (chin, belly, feet forward)
    # (head_mode 'r3': the previous round's head, for comparing - depth from the whole side
    # picture with its outline, centre smoothed over 7 rows, shaped by a vertical profile)
    halfA = np.zeros(P); zcA = np.full(P, 31.5)
    for r in range(P):
        cA = np.nonzero(E[r, :, 3] > 0)[0]
        if len(cA): halfA[r] = (cA.max() - cA.min() + 1) / 2; zcA[r] = P - 1 - (cA.min() + cA.max()) / 2
    zcA = np.convolve(np.pad(zcA, 3, mode='edge'), np.ones(7) / 7, 'valid')
    half = np.zeros(P); zc = np.full(P, 31.5)
    for r in range(P):
        rs_ = landmarks.runs(list(Ea[r]))
        if not rs_: continue
        mg = [list(rs_[0])]
        for t in rs_[1:]:
            if t[0] - mg[-1][1] <= 2: mg[-1][1] = t[1]
            else: mg.append(list(t))
        a_, b_ = max(mg, key=lambda t: t[1] - t[0])
        half[r] = (b_ - a_ + 1) / 2; zc[r] = P - 1 - (a_ + b_) / 2
    okE = half > 0
    for arr in (half, zc):
        sm3 = arr.copy()
        for r in range(1, P - 1):
            if okE[r - 1] and okE[r] and okE[r + 1]: sm3[r] = np.median(arr[r - 1:r + 2])
        arr[:] = sm3
    hmax = h.max(1)
    rows = np.nonzero((hmax > 1.5) & (half > 0))[0]
    k = np.ones(P)
    if len(rows):
        hk = halfA if body_mode == 'r3' else half
        kr = np.interp(np.arange(P), rows, hk[rows] / hmax[rows])
        pad = scale_smooth // 2
        kp = np.pad(kr, pad, mode='edge')
        k = np.clip(np.array([np.median(kp[i:i + scale_smooth]) for i in range(P)]), 0.7, 2.2)
    # thin parts (arms, legs, ears: small half-width) stay round - the side picture's depth is the
    # body's, and scaling them by it turned arms into planks
    k_eff = 1 + (k[:, None] - 1) * np.clip((w - 3.0) / 4.0, 0, 1)
    h = h * k_eff
    Sp = build3d10.parts_of(race)
    # the head is not a balloon: a balloon's top edge is thin, which from above reads as a ridge.
    # Each head row is a rounded section as wide as the front picture and as deep as the side
    # picture, its depth rounding off over the crown's top rows (a dome, not a slab)
    top_r = min(Sp['head']); neck_r = Sp['neck']
    # the body is not a balloon either: a balloon's section is a lens, thin at its sides - the
    # torso came out as thin at the sides as the arms beside it, and arms and torso read as one
    # sack. Each run of the front picture below the neck gets its own section: the run through
    # the middle is the torso, a rounded barrel as deep as the side picture; the others (arms,
    # legs, hands) round tubes; feet as long as the side picture draws them
    halfs = np.array([np.median(half[max(0, i - 1):i + 2]) for i in range(P)])
    sole_r = max(np.nonzero(alpha0.any(1))[0]) if alpha0.any() else P - 1
    def sm(v, ok):
        # a per-row value smoothed over the rows that have it (median of 3, then mean of 3)
        idx = np.nonzero(ok)[0]
        if not len(idx): return v
        vv = np.interp(np.arange(P), idx, v[idx])
        vv = np.array([np.median(vv[max(0, i - 1):i + 2]) for i in range(P)])
        return np.where(ok, np.convolve(np.pad(vv, 1, mode='edge'), np.ones(3) / 3, 'valid'), v)
    # rows of the torso, and where the arms hang free of it (a run each side of the middle one)
    mid = {}; side = {}
    for r in range(neck_r + 1, sole_r + 1):
        rs_ = landmarks.runs(list(alpha0[r]))
        m_ = [t for t in rs_ if t[0] <= 31 and t[1] >= 32 and t[1] - t[0] >= 7]
        if not m_: continue
        mid[r] = m_[0]
        L_ = [t for t in rs_ if t[1] < m_[0][0]]; R_ = [t for t in rs_ if t[0] > m_[0][1]]
        if L_ and R_: side[r] = (L_[-1], R_[0])
    gap_rows = sorted(side)
    Tw = np.zeros(P); Tok = np.zeros(P, bool)
    armc = np.zeros((P, 2)); armr = np.zeros((P, 2)); Aok = np.zeros(P, bool)
    for r in gap_rows:
        a_, b_ = mid[r]; Tw[r] = (b_ - a_ + 1) / 2; Tok[r] = True
        for k_, (ra, rb) in enumerate(side[r]):
            armc[r, k_] = (ra + rb + 1) / 2; armr[r, k_] = (rb - ra + 1) / 2 + 0.5
        Aok[r] = True
    g0 = gap_rows[0] if gap_rows else None
    # over the arms (the shoulders) the middle run is torso and arm tops together: the torso there
    # is as wide as the rows above and below it say, the rest is the arms' rounded tops
    merged = set()
    if g0 is not None:
        above = [r for r in sorted(mid) if r < g0]
        tw0 = Tw[g0]; last = None
        for r in above:
            hw_r = (mid[r][1] - mid[r][0] + 1) / 2
            if hw_r <= tw0 + 3.0 and r < g0 - 1 and not merged: Tw[r] = hw_r; Tok[r] = True; last = r
            else: merged.add(r)
        for r in merged:
            if last is None: Tw[r] = tw0
            else: Tw[r] = Tw[last] + (tw0 - Tw[last]) * (r - last) / max(g0 - last, 1)
            Tok[r] = True
        top_arms = [r for r in gap_rows[:4]]
        for r in merged:
            for k_ in range(2):
                armc[r, k_] = np.mean([armc[q, k_] for q in top_arms])
                ra0 = np.mean([armr[q, k_] for q in top_arms])
                edge = mid[r][0] if k_ == 0 else mid[r][1] + 1
                armr[r, k_] = min(max(abs(armc[r, k_] - edge) + 0.3, ra0 * 0.8), ra0 + 1.5)
            Aok[r] = True
    for r in mid:                                                         # below the arms: hips
        if not Tok[r]: Tw[r] = (mid[r][1] - mid[r][0] + 1) / 2; Tok[r] = True
    Tw = sm(Tw, Tok)
    for k_ in range(2):
        armc[:, k_] = sm(armc[:, k_], Aok); armr[:, k_] = sm(armr[:, k_], Aok)
    bzT = sm(np.array([max(min(halfs[r], (Tw[r] + 0.6) * torso_cap), Tw[r] * 0.5) for r in range(P)]), Tok) * body_depth   # as deep as the side picture, no deeper than wide
    # the hips round in under the torso to the legs' depth (a barrel ending square drew a ledge,
    # and its line read as shorts)
    if mid:
        hip = max(mid)
        for i_ in range(4):
            r = hip - i_
            if r in mid: bzT[r] *= 1 - 0.09 * (4 - i_)
    hb = np.zeros((P, P)); cols = np.arange(P) + 0.5
    # a pronounced body (the skeleton's parts read best): down the torso a deep chest, a pinched
    # waist, flared hips, and in the lowest third the thighs run up into it as two tubes with a
    # groove between - depth changes mostly, so the front stays the sprite's
    tor_rows = sorted(mid); t0_, t1_ = (tor_rows[0], max(tor_rows)) if tor_rows else (neck_r + 1, neck_r + 2)
    def tfrac(r): return np.clip((r - t0_) / max(t1_ - t0_, 1), 0, 1)
    # (pronounce_chest: the skeleton's deep chest, which looked wrong on the fleshed races; the
    # waist, hips and thighs keep their shaping)
    dep_k = lambda r: 1 + pronounce * (np.interp(tfrac(r), [0, 0.25, 0.55, 0.8, 1.0], [1.0 + 0.04 * pronounce_chest, 1.0 + 0.14 * pronounce_chest, 0.80, 1.02, 0.96]) - 1)
    wid_k = lambda r: 1 + pronounce * 0.5 * (np.interp(tfrac(r), [0, 0.25, 0.55, 0.8, 1.0], [1.0, 1.0, 0.9, 1.0, 1.0]) - 1)
    thigh_px = np.zeros((P, P), bool)
    legs0 = []
    for r in range((max(mid) if mid else neck_r) + 1, min((max(mid) if mid else neck_r) + 7, sole_r - 2)):
        rs0 = landmarks.runs(list(alpha0[r]))
        if len(rs0) == 2 and all(t[1] - t[0] >= 3 for t in rs0): legs0.append(rs0)
    lc0 = [np.mean([(t[k_][0] + t[k_][1] + 1) / 2 for t in legs0]) for k_ in range(2)] if legs0 else None
    lr0 = [np.mean([(t[k_][1] - t[k_][0] + 1) / 2 + 0.5 for t in legs0]) for k_ in range(2)] if legs0 else None
    zoff = np.zeros((P, P)); foot_rows = []                               # per-pixel shift in depth (feet)
    def tube(cx, rad, depth):
        u = np.clip(np.abs(cols - cx) / max(rad, 0.5), 0, 1)
        return np.where(np.abs(cols - cx) < rad, depth * np.sqrt(1 - u ** 2), 0)
    for r in range(neck_r + 1, P):
        for a_, b_ in landmarks.runs(list(alpha0[r])):
            sl = slice(a_, b_ + 1)
            if r in mid and (a_, b_) == mid[r]:
                cx = (a_ + b_ + 1) / 2; ax_ = Tw[r] * wid_k(r) + 0.6
                u = np.clip(np.abs(cols - cx) / ax_, 0, 1)
                v_ = bzT[r] * dep_k(r) * (1 - u ** 2.5) ** (1 / 2.5) * (np.abs(cols - cx) < ax_)
                tf = tfrac(r)
                if pronounce and lc0 is not None and tf > 0.62 and r not in merged:
                    # the thighs: the pelvis sinks between them toward the crotch
                    sink = pronounce * 0.5 * np.clip((tf - 0.62) / 0.38, 0, 1)
                    pel = v_ * (1 - sink)
                    tubes = np.zeros(P)
                    for k_ in range(2): tubes = np.maximum(tubes, tube(lc0[k_], lr0[k_] * 1.15, bzT[r] * dep_k(r) * 0.95))
                    v_ = np.maximum(pel, tubes * (np.abs(cols - cx) < ax_))
                    thigh_px[r] = (tubes > pel) & (np.abs(cols - cx) < ax_)   # where the thighs stand proud of the pelvis
                if r in merged:
                    for k_ in range(2):
                        v_ = np.maximum(v_, tube(armc[r, k_], armr[r, k_], armr[r, k_] * 1.05 * limb_depth))
                hb[r, sl] = v_[sl]
            else:
                wd = b_ - a_ + 1; ax_ = wd / 2 + 0.5; cx = (a_ + b_ + 1) / 2
                is_arm = r in side and (a_, b_) in side[r]
                if is_arm:                                                # a free arm: the smoothed tube
                    k_ = side[r].index((a_, b_)); cx, ax_ = armc[r, k_], armr[r, k_]
                if r >= sole_r - 3 and halfs[r] > ax_ * 1.2:              # a foot: as long as the side picture draws it
                    # the toes where the side picture draws them, the heel short of its back edge:
                    # feet the side picture's whole length doubled their size from the game's
                    # corners and the heads looked small above them
                    bz = halfs[r] * foot_len; pe = 3.0; foot_rows.append(r)
                    fwd = halfs[r] - bz
                    # a foot, not a box: narrower at the heel (the outer columns start further
                    # forward), the toes rounded
                    uu = np.clip(np.abs(cols - cx) / ax_, 0, 1)
                    cut = 0.45 * uu ** 2
                    zoff[r, sl] = (-cut * bz - fwd)[sl]
                    hb[r, sl] = (bz * (1 - cut) * (1 - uu ** pe) ** (1 / pe))[sl]
                    continue
                elif mid and r > max(mid):                              # a leg: as deep as the side picture nearly (thigh, calf)
                    # (no deeper than 1.3x its width: legs as deep as the side picture's thighs
                    # bulked the body up until the head looked small on it)
                    bz = min(max(min(ax_ * 1.05, halfs[r]), halfs[r] * 0.85), ax_ * leg_cap) * limb_depth; pe = 2.2
                elif is_arm:
                    # the arm as the side pictures draw it: a deep shape filling the back half of
                    # the body, its back flush with the body's back, so in profile only its front
                    # edge draws a line (a round tube in the body's middle drew a loop on the side)
                    az = min(max(ax_ * 1.05, arm_deep * halfs[r]), max(halfs[r], 1.0)) * limb_depth
                    bz = az; pe = 2.0
                    ramp = min(1.0, (r - gap_rows[0] + 1) / 3.0) if gap_rows else 1.0
                    if arm_deep > 0: zoff[r, sl] = (halfs[r] - az) * ramp
                else:                                                   # a hand or stray piece: round, no deeper than the side picture
                    bz = min(ax_ * 1.05, max(halfs[r], 1.0)) * limb_depth; pe = 2.0
                u = np.clip(np.abs(cols - cx) / ax_, 0, 1)
                hb[r, sl] = (bz * (1 - u ** pe) ** (1 / pe))[sl]
    # the thighs as deep at their top as the hips above them (else the torso's lower edge hung over
    # the legs like the hem of a pair of shorts)
    if mid:
        hip = max(mid); hsec = hb[hip].copy()
        for i_ in range(1, 4):
            r = hip + i_
            if r < P: hb[r] = np.where(alpha0[r], np.maximum(hb[r], hsec * (1 - 0.22 * i_)), hb[r])
        # ...and the legs run on up into the hips, as the arms run up into the shoulders (the legs
        # stand wider than the hips' own run, where the barrel is thinnest)
        legs = []
        for r in range(hip + 1, min(hip + 7, sole_r - 2)):
            rs_ = landmarks.runs(list(alpha0[r]))
            if len(rs_) == 2 and all(t[1] - t[0] >= 3 for t in rs_): legs.append(rs_)
        if legs:
            lc = [np.mean([(t[k_][0] + t[k_][1] + 1) / 2 for t in legs]) for k_ in range(2)]
            lr = [np.mean([(t[k_][1] - t[k_][0] + 1) / 2 + 0.5 for t in legs]) for k_ in range(2)]
            for r in range(hip - 3, hip + 3):
                if not (0 <= r < P): continue
                for k_ in range(2):
                    hb[r] = np.where(alpha0[r], np.maximum(hb[r], tube(lc[k_], lr[k_], lr[k_] * 1.05 * limb_depth)), hb[r])
    # the instep: the top rows of the foot stop short of the toes, so the foot slopes down to them
    fr_ = sorted(set(foot_rows))
    for i_, r in enumerate(fr_[:2]):
        cut = (0.42, 0.22)[i_] if len(fr_) >= 3 else 0.0
        if cut:
            m_ = alpha0[r]
            zoff[r] = np.where(m_, zoff[r] + cut * hb[r], zoff[r]); hb[r] = np.where(m_, hb[r] * (1 - cut), hb[r])
    body = np.zeros((P, P), bool); body[neck_r + 1:] = alpha0[neck_r + 1:]
    if body_mode == 'r3': zoff[:] = 0                                   # (comparing: the round-3 balloon body)
    else: h = np.where(body, np.maximum(hb, 0.6), h)
    tmid, tside, tmerged, tgap = dict(mid), dict(side), set(merged), list(gap_rows)   # (the head block reuses these names)
    # the skull's own width (from the race's fitted helmet): what the head rows draw beyond it
    # is ears or horns, even where no line parts them from the head
    try:
        mm = build3d9.measure(race); hws = mm['head_w'] + 1.2
        top_r = max(top_r, int(mm['top']) - 1)                      # the skull's top: above it is ears and horns
        while top_r > 0 and alpha[top_r - 1, 30:34].all(): top_r -= 1  # ...unless the middle goes on up (hair)
    except Exception:
        hws = 12.0
    skull = {}
    full_alpha = raw['S'][:, :, 3] > 0
    eye_row = top_r + 0.3 * (neck_r - top_r)
    for r in range(top_r, neck_r + 1):
        # the head's own run in the row: where the sprite draws a line between head and ear, the
        # run inside it (goblin, orc); otherwise the whole drawn run through the middle, no wider
        # than the skull - except above the eyes, where a narrower run means the rest is ears
        # rising beside the head (vampire, gargoyle)
        runs_ = [t for t in landmarks.runs(list(full_alpha[r])) if t[0] <= 32 <= t[1] + 1]
        if not runs_: continue
        run = runs_[0]; mid = 32.0
        full_run = (int(max(run[0] + 1, np.floor(mid - hws))), int(min(run[1] - 1, np.ceil(mid + hws) - 1)))
        own = Sp['head'].get(r)
        if own is not None:
            ratio = (own[1] - own[0] + 1) / (2 * hws)
            # (not a sliver between the skeleton's eye sockets: a crown narrower than a third
            # of the skull is not the crown)
            if ratio >= 0.6 or (r < eye_row and ratio >= 0.33 and own[1] - own[0] < full_run[1] - full_run[0] - 3):
                skull[r] = (max(own[0], full_run[0]), min(own[1], full_run[1]))
                continue
        skull[r] = full_run
    # a smooth skull: below the eyes the drawn width, a row that juts out (an ear's lobe or root
    # run into the cheek) evened out with its neighbours; above the eyes never wider than the row
    # below - what juts out over it is ears (the kobold's, the goblin's) - and domed at the crown
    er = int(np.ceil(eye_row))
    hw_ = {r: (b - a + 1) / 2 for r, (a, b) in skull.items()}
    # a skull is never a sliver: holes in the face (the skeleton's nose and eye sockets) cut the
    # drawn run down to a few pixels, and the rows above copied it
    for r in range(top_r + 2, neck_r - 2):
        if r in hw_ or full_alpha[r, 28:36].any(): hw_[r] = max(hw_.get(r, 0), 0.6 * hws)
    for r in sorted(hw_):
        if r < er: continue
        med = float(np.median([hw_[q] for q in range(r - 2, r + 3) if q in hw_]))
        if hw_[r] > med + 1.5: hw_[r] = med
    for r in sorted([q for q in hw_ if q < er], reverse=True):
        below = [hw_[q] for q in range(r + 1, r + 3) if q in hw_]
        if below: hw_[r] = min(hw_[r], min(below[0] + 0.5, max(below)))
    HW = max([hw_[q] for q in hw_ if er <= q <= er + 4] or list(hw_.values()) or [8.0])
    for r in hw_:
        if r < er:
            t = np.clip((er - r - 0.5) / (er - top_r + 0.5), 0, 1)
            hw_[r] = min(hw_[r], max(HW * (1 - t ** 2.4) ** (1 / 2.4) + 0.5, hw_[r] - 1.0))
    skull = {r: (int(round(32 - v_)), int(round(32 + v_)) - 1) for r, v_ in hw_.items()}
    # the side picture draws the crown a row or two higher than the front does: a domed cap up to
    # it, or the head stops flat where the front picture's top edge is
    e_top = top_r
    while e_top - 1 >= 0 and half[e_top - 1] > 0 and top_r - e_top < cap_rows: e_top -= 1
    if e_top < top_r and top_r in skull:
        a0_, b0_ = skull[top_r]; hw0 = (b0_ - a0_ + 1) / 2
        for r in range(e_top, top_r):
            t = (top_r - r) / (top_r - e_top + 1.0)
            v_ = hw0 * (1 - t ** 2) ** 0.5 - 0.5
            if v_ < 1.5: continue
            skull[r] = (int(round(32 - v_)), int(round(32 + v_)) - 1)
        top_r = min(skull)
    # above the crown (horns, ear tips) the side picture's run is the horn in profile, jumping
    # back and forth: those rows sit where the crown does
    if top_r > 0: zc[:top_r] = zc[top_r]
    if head_mode in ('r2', 'r3'): zc[:neck_r + 1] = zcA[:neck_r + 1]
    if body_mode == 'r3': zc[neck_r + 1:] = zcA[neck_r + 1:]
    for r in range(top_r, neck_r + 1):
        run = skull.get(r)
        if run is None or half[r] <= 0: continue
        a, b = run; cx_ = (a + b + 1) / 2; hw = (b - a + 1) / 2 + 0.6
        # each row as deep as the side picture draws the head there (its dome, its chin), a full
        # rounded section across - not shrunk again by a profile of its own, which made the head
        # flat; no deeper than it is wide (the side picture's ears and horns are not skull)
        # ...and over the crown a dome: both pictures draw the top of the head flat, and the two
        # together made a lid; the dome rounds the crown's corners off toward the top
        # (and about as deep as it is wide, a little more than the side picture says: seen from
        # the game's corners a head shallower than it is wide reads as a tall egg)
        # (halfway: all the way to round made the side view a mushroom over the body)
        fill = lambda e_, w_: e_ + head_fill * max(0.95 * w_ - e_, 0)
        dep = fill(min(half[r], 1.1 * hw), hw)
        if head_mode == 'r2':
            # the head you liked (the round before the brown band): as deep as the whole side
            # picture, deepest at mid-height, a squarish round across, flat-topped
            hm_ = (top_r + neck_r) / 2; hh_ = (neck_r - top_r) / 2 + 1.0
            v = (r + 0.5 - hm_) / hh_
            vert = (1 - np.clip(abs(v), 0, 1) ** 2.2) ** (1 / 2.2) if v < 0 else 0.72 + 0.28 * (1 - np.clip(v, 0, 1) ** 2) ** 0.5
            # (the side picture's head without its outline: with it, and the head a size up,
            # the head stood two pixels proud of the body front and back in profile)
            dep = (halfA[r] if head_outline_depth else max(half[r], halfA[r] - 1.0)) * max(vert, 0.25)
        elif head_mode == 'r3':
            hm_ = (top_r + neck_r) / 2; hh_ = (neck_r - top_r) / 2 + 0.6
            v = (r + 0.5 - hm_) / hh_
            vert = (1 - np.clip(abs(v), 0, 1) ** 2.0) ** 0.5 if v < 0 else 0.72 + 0.28 * (1 - np.clip(v, 0, 1) ** 2) ** 0.5
            vert = max(vert, 0.3)
            if r >= er: vert *= min(1.0, max((b - a + 1) / (2 * HW), 0.45) ** 0.6)
            dep = halfA[r] * vert
        elif r < er:
            Dm = max(fill(min(half[q], 1.1 * HW), HW) for q in range(er, min(er + 4, neck_r + 1))) if er <= neck_r else dep
            t = np.clip((er - r - 0.5) / (er - top_r + 1.0), 0, 1)
            dep = min(dep, Dm * (1 - t ** dome_p) ** (1 / dome_p) + 0.5)
        u = np.clip(np.abs((np.arange(P) + 0.5 - cx_) / hw), 0, 1)
        pe_ = head_p if head_mode == 'r2' else 2.0
        sec = dep * (1 - u ** pe_) ** (1 / pe_)
        cols_ = np.arange(P)
        on = (cols_ >= a) & (cols_ <= b)
        alpha[r, on] = True
        h[r, on] = np.maximum(sec[on], 0.5)
    # ears (and horns): what the head rows draw beside the head keeps its outline as part of it -
    # removing the black lines left them as specks - and gets a little thickness
    ears = np.zeros((P, P), bool)
    for r in range(0, neck_r + 1):
        run = skull.get(r)
        for c in range(P):
            if not alpha[r, c]: continue
            if run is None:
                if r <= top_r + 1: ears[r, c] = True                  # horns and ear tips above the head
            elif c < run[0] - 1 or c > run[1] + 1: ears[r, c] = True
    # an ear's root, just beside the skull, is ear too; above the eyes, what else lies beside the
    # skull is the crown's corner the dome rounds off
    for r in range(0, neck_r + 1):
        run = skull.get(r)
        if run is None: continue
        for c, nxt in ((run[0] - 1, run[0] - 2), (run[1] + 1, run[1] + 2)):
            if not (0 <= nxt < P) or not alpha[r, c]: continue
            if ears[r, nxt]: ears[r, c] = True
            elif r < er: alpha[r, c] = False
    # the ear as big as the sprite draws it: its dark rim too (the orc's, the vampire's ears are
    # mostly outline) - all but the outermost pixel, which the renderer's own outline redraws
    dfull = distance(full_alpha)
    ear_zone = np.zeros((P, P), bool)
    for r in range(0, neck_r + 1):
        run = skull.get(r)
        if run is None: ear_zone[r] = r <= top_r + 1
        else: ear_zone[r, :max(run[0] - 1, 0)] = True; ear_zone[r, run[1] + 2:] = True
    # ...and only beside the rows the ear itself is drawn on: left to run along the head's dark
    # outline, the orc's small ears grew down to its jaw
    for sd in (slice(0, 32), slice(32, P)):
        rows_e = np.nonzero(ears[:, sd].any(1))[0]
        if len(rows_e):
            lo_, hi_ = rows_e.min() - 2, rows_e.max() + 3
            ear_zone[:, sd] &= ((np.arange(P) >= lo_) & (np.arange(P) <= hi_))[:, None]
        else: ear_zone[:, sd] = False
    grow = ears.copy()
    # (on along the whole dark edge the sprite draws down from the ear beside the head - the
    # vampire's and the gargoyle's ears run down the head's sides as a thick black band)
    for i_ in range(ear_grow):
        p_ = np.pad(grow, 1); g_ = grow | p_[:-2, 1:-1] | p_[2:, 1:-1] | p_[1:-1, :-2] | p_[1:-1, 2:]
        # the whole drawn ear, its thick black outline too: without it an ear seen from the game's
        # corners was a thin strip (the sprites draw an ear as outline round a little colour)
        lim = full_alpha & ~alpha & (ear_zone if i_ else True) & ((dfull > 1.0) if (i_ and not ear_full) else True)
        g2 = grow | (g_ & lim)
        if (g2 == grow).all(): break
        grow = g2
    grow &= ~alpha
    alpha |= grow; ears |= grow
    ear_tilt = np.zeros((P, P)); horn = np.zeros((P, P), bool)
    for r in range(P):
        run = skull.get(r) or skull.get(min(skull, key=lambda q: abs(q - r))) if skull else None
        if run is None: continue
        for c in np.nonzero(ears[r])[0]:
            out_ = (run[0] - c) if c < run[0] else (c - run[1])
            h[r, c] = max(ear_thick - 0.07 * out_, 0.9)               # thick enough to read seen edge on (a thin leaf was just its outline)
            ear_tilt[r, c] = ear_sweep * out_                             # swept back
    # cupped, not flat: the ear's middle sits further back than its rim, so from the game's
    # corners an ear shows its hollow and rim instead of a flat blade seen edge on
    if ears.any():
        de = distance(ears); we = de.copy()
        for _ in range(3):
            p_ = np.pad(we, 1)
            we = np.maximum(np.maximum.reduce([p_[1:-1, 1:-1], p_[:-2, 1:-1], p_[2:, 1:-1], p_[1:-1, :-2], p_[1:-1, 2:]]) * (de > 0), de)
        cup = np.where(ears, ear_cup * we * (1 - ((we - de) / np.maximum(we, 1)) ** 2), 0)
        ear_tilt += blur(cup, 1) * ears
        # horns are not ears: a piece drawn in other than the skin's colour (the demon's bone
        # horns) is a round tube standing up beside the head, not a leaf laid back along it
        hd = raw['S'][top_r:neck_r + 1][full_alpha[top_r:neck_r + 1] & ~ears[top_r:neck_r + 1]][:, :3]
        cs_, ks_ = np.unique(hd, axis=0, return_counts=True); sk_ = cs_[ks_.argmax()] if len(cs_) else np.array([128, 128, 128])
        fa0 = raw['S'][:, :, 3] > 0; bc_, bk_ = np.unique(raw['S'][fa0 & (np.arange(P)[:, None] > neck_r)][:, :3], axis=0, return_counts=True)
        body_cols = bc_[bk_ >= 0.05 * bk_.sum()] if len(bk_) else np.zeros((1, 3))
        lab = np.zeros((P, P), int); nl_ = 0
        for r0, c0_ in zip(*np.nonzero(ears)):
            if lab[r0, c0_]: continue
            nl_ += 1; st_ = [(r0, c0_)]; lab[r0, c0_] = nl_
            while st_:
                y_, x_ = st_.pop()
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y_ + dy, x_ + dx
                    if 0 <= yy < P and 0 <= xx < P and ears[yy, xx] and not lab[yy, xx]: lab[yy, xx] = nl_; st_.append((yy, xx))
        for k_ in range(1, nl_ + 1):
            m_ = lab == k_
            px = raw['S'][m_][:, :3]; lit_ = px[px.sum(1) > 150]
            if len(lit_) < 4: continue
            # (bone-bright: the elf's grey hair is not a horn; and not the race's own skin colour:
            # the skeleton's white skull sides are not horns)
            if np.median(np.abs(lit_ - sk_).sum(1)) > 150 and np.median(lit_.sum(1)) > 500 and np.median(np.abs(lit_[:, None] - body_cols[None]).sum(-1).min(-1)) > 90:
                h[m_] = np.maximum(we[m_] * 0.9, 0.8); ear_tilt[m_] = 0.0; horn |= m_
    # a horn's root drawn inside the skull's columns is horn too (the demon's horns rise from
    # the head's top corners): bone-coloured pixels joined to a horn
    if horn.any():
        hc0 = raw['S'][horn][:, :3]; hc0 = hc0[hc0.sum(1) > 450]
        if len(hc0):
            bonep = full_alpha & (np.abs(raw['S'][:, :, None, :3] - hc0[None, None]).sum(-1).min(-1) < 60) & (np.arange(P)[:, None] <= neck_r)
            grow_h = horn.copy()
            for _ in range(12):
                p_ = np.pad(grow_h, 1); g_ = (grow_h | p_[:-2, 1:-1] | p_[2:, 1:-1] | p_[1:-1, :-2] | p_[1:-1, 2:]) & (bonep | grow_h)
                if (g_ == grow_h).all(): break
                grow_h = g_
            new_h = grow_h & ~horn
            if new_h.any():
                horn |= new_h; ears |= new_h; alpha |= new_h
                h[new_h] = 1.0; ear_tilt[new_h] = 0.0
    # procedural horns: each horn is a curved cone built from two points, not from the sprite's
    # pixels (whose pale strip runs down the head's side and read as a blade from the side):
    # tip = the horn mask's top (x, row) at the depth the side picture draws the tip; root = the
    # head's top corner at the head's own depth; round, tapering to a point
    horn_specs = []
    if horn.any() and horn_proc:
        Ez_ = raw['E']; hcol_ = raw['S'][horn][:, :3]; hcol_ = hcol_[hcol_.sum(1) > 450]
        bone_ = (Ez_[:, :, 3] > 0) & (np.abs(Ez_[:, :, None, :3] - hcol_[None, None]).sum(-1).min(-1) < 60) if len(hcol_) else np.zeros((P, P), bool)
        for sd in (0, 1):
            msk = horn & ((np.arange(P)[None, :] < 32) if sd == 0 else (np.arange(P)[None, :] >= 32))
            if not msk.any(): continue
            rows_h = np.nonzero(msk.any(1))[0]; r_top = rows_h.min()
            cols_t = np.nonzero(msk[r_top])[0]; x_tip = cols_t.mean() + 0.5
            span = min(rows_h.max() - r_top, 9)
            r_mid = r_top + 0.5 * span
            cm = np.nonzero(msk[int(r_top + 0.5 * span)])[0] if msk[int(r_top + 0.5 * span)].any() else cols_t
            x_mid = cm.mean() + 0.5
            wmax = max((msk[q].sum() for q in rows_h[:10]), default=3)
            zt = [P - 1 - (np.nonzero(bone_[q])[0].min() + np.nonzero(bone_[q])[0].max()) / 2 for q in range(max(r_top - 1, 0), r_top + 4) if bone_[q].any()]
            z_tip = float(np.mean(zt)) if zt else float(zc[r_top])
            r_root = float(min(top_r + 3.0, r_top + max(span, 4))); x_root = float(x_mid)   # the head's top corner
            if r_root - r_top < 3: r_root = r_top + 3.0
            z_root = float(zc[min(int(r_root), P - 1)])
            horn_specs.append(dict(tip=(r_top - 1.2, x_tip + (-1.0 if sd == 0 else 1.0) * horn_lean, z_tip), root=(r_root, x_root, z_root), rad=min(max(wmax / 2.0 * horn_thick, 1.3), 2.2), side=sd))
        alpha &= ~horn; ears &= ~horn
    # the sprite's bone strip down the head's side below the horn is the head's lit edge, not horn:
    # the horn is the cone above (horn_len of its rows); the strip is dropped
    if horn.any() and horn_follow:
        hrw = [q for q in range(P) if horn[q].any()]
        cut0 = min(hrw) + horn_len * (max(hrw) - min(hrw))
        strip = horn & (np.arange(P)[:, None] > cut0)
        horn &= ~strip; ears &= ~strip; alpha &= ~strip
    # a flat face: in the face region the front is pushed out to an even plane
    hrows = sorted(Sp['head']); hcols = [c for r_ in hrows for c in Sp['head'][r_]]
    fr0, fr1 = hrows[0] + 3, Sp['neck'] + 1; fc0, fc1 = min(hcols) + 2, max(hcols) - 1
    hf = h.copy()
    head_max = h[hrows[0]:Sp['neck'] + 1].max() if hrows else h.max()
    rr_, cc_ = np.mgrid[0:P, 0:P]
    # only as wide as the face's features (eyes, mouth, tusks): a face pushed flat to the head's
    # edges made the head a box
    sk_ = np.array([[c for c in raw['S'][r, c_, :3]] for r in range(fr0, fr1) for c_ in range(fc0, fc1 + 1) if raw['S'][r, c_, 3]] or [[0, 0, 0]])
    cs0, ks0 = np.unique(sk_, axis=0, return_counts=True); skin_f = cs0[ks0.argmax()]
    feat = np.zeros((P, P), bool)
    feat[fr0:fr1, fc0:fc1 + 1] = (np.abs(raw['S'][fr0:fr1, fc0:fc1 + 1, :3] - skin_f).sum(-1) > 120) & (raw['S'][fr0:fr1, fc0:fc1 + 1, 3] > 0)
    for r in range(fr0, fr1):                                           # not the head's own edge band
        run = skull.get(r)
        if run is None: feat[r] = False
        else: feat[r, :run[0] + 3] = False; feat[r, run[1] - 2:] = False
    feat &= ~ears
    fx = np.nonzero(feat.any(0))[0]
    fhalf = max(np.abs(fx + 0.5 - 32).max() + 1.0, 3.0) if len(fx) else (fc1 - fc0) / 2
    uf = np.abs((cc_ + 0.5 - 32) / fhalf)
    in_face = (rr_ >= fr0) & (rr_ < fr1) & (cc_ >= fc0) & (cc_ <= fc1) & alpha & (uf <= 1.3)
    plane = face_flat * head_max * (1 - 0.16 * np.clip(uf, 0, 1) ** 2 - 0.6 * np.clip(uf - 1, 0, None))
    lift = np.clip(np.minimum(plane, h * 1.2 + 0.3) - h, 0, None)       # flatter, not jutting: a jaw pushed out to the plane made a box
    if head_mode == 'r2':                                               # (the liked head: the face flat right across)
        in_face = (rr_ >= fr0) & (rr_ < fr1) & (cc_ >= fc0) & (cc_ <= fc1) & alpha
        plane = face_flat * head_max * (1 - 0.18 * np.clip(np.abs((cc_ + 0.5 - 32) / max((fc1 - fc0) / 2, 1)), 0, 1) ** 2)
        lift = np.clip(np.minimum(plane, h * 1.5 + 0.3) - h, 0, None)
    lift *= np.clip((rr_ - fr0 + 1) / 3.0, 0, 1)                         # eased in below the crown: no step
    hf = np.where(in_face & ~ears, h + lift, h)
    # the eyes stand a little proud of the face: from the game's corners a flat face is seen at an
    # angle and the eyes shrank to slits; standing out, their sides show too
    eye_rows = rr_ < (fr0 + fr1) / 2 + 1
    eyes_m = feat & eye_rows & alpha & ~ears
    hf = np.where(eyes_m, hf + eye_pop, hf)
    global LAST
    LAST = dict(alpha=alpha.copy(), ears=ears.copy(), h=h.copy(), hf=hf.copy(), skull=dict(skull), top_r=top_r, neck_r=neck_r)
    # what each pixel is (the part map, for checking and for a rig later; not the line ids):
    # 1 torso, 2 head, 3 ears, 4 legs, 5 web, 6/7 left/right arm, 8 feet, 9 horns, 10 neck,
    # 11 shoulders (the arms' tops over the torso), 12 hands, 13 ankle
    limb = np.zeros((P, P), np.int16)
    limb[alpha & (rr_ <= neck_r)] = 2
    limb[ears] = 3; limb[horn] = 9
    hip = max(tmid) if tmid else neck_r
    for r in tmid:
        a_, b_ = tmid[r]; limb[r, a_:b_ + 1] = 1
    sh_w = max([Tw[r] for r in tmerged] or [0])
    for r in tmid:
        if r < (tgap[0] if tgap else hip) and r not in tmerged and Tw[r] < 0.72 * sh_w: limb[r, tmid[r][0]:tmid[r][1] + 1] = 10
    for r in tmerged:
        a_, b_ = tmid[r]
        for k_ in range(2):
            c0_ = int(np.floor(armc[r, k_] - armr[r, k_])); c1_ = int(np.ceil(armc[r, k_] + armr[r, k_]))
            limb[r, max(a_, c0_):min(b_, c1_) + 1] = 11
    hr_ = sorted(tside)
    for r in hr_:
        for k_, (ra, rb) in enumerate(tside[r]): limb[r, ra:rb + 1] = 12 if r in hr_[-3:] else 6 + k_
    lower = alpha0 & (rr_ > hip)
    limb[lower & (limb == 0)] = 4
    for r in set(foot_rows): limb[r, alpha0[r]] = 8
    limb[ankle] = 13
    LAST['limb'] = limb
    # the arms hang a little behind the body's middle, as the side pictures draw them (the arm's
    # dark shape runs down the back half of the body in profile); eased in below the shoulder
    if arm_back and hr_:
        r_free = hr_[0]
        for r in hr_:
            ramp = min(1.0, (r - r_free + 1) / 3.0)
            zoff[r] = np.where(np.isin(limb[r], [6, 7, 12]), zoff[r] + arm_back * ramp, zoff[r])
    # parts: body 1, head 2, ears and horns 3 (lines where one passes in front of another, and
    # each its own band of colour inside the outline)
    part = np.ones((P, P), np.int16)
    part[rr_ <= neck_r] = 2                                              # (what rises over the crown is head too, or ears)
    part[ears] = 3
    # the sprite's own way of drawing its edge: a warm near-black outline and, inside it, a band
    # of brown (two pixels round the head - what reads as hair on the light-skinned races)
    fa = raw['S'][:, :, 3] > 0; dfa = distance(fa); lum_ = raw['S'][:, :, :3].sum(2)
    a_ = raw['S'][fa][:, :3]; c_, k__ = np.unique(a_, axis=0, return_counts=True)
    skins0 = np.array([c for c, kk in zip(c_.tolist(), k__.tolist()) if kk >= 0.02 * len(a_) and sum(c) >= 100] or [[200, 160, 120]])
    def common(mask):
        if not mask.any(): return None, 0
        cc, kk = np.unique(raw['S'][mask][:, :3], axis=0, return_counts=True)
        return tuple(cc[kk.argmax()].tolist()), int(kk.max())
    edge = fa & (dfa <= 1.0) & (lum_ < 90)
    outline_col, _ = common(edge)
    far = np.abs(raw['S'][:, :, None, :3] - skins0[None, None]).sum(-1).min(-1) > 60
    band = (lum_ >= 40) & (lum_ <= 220) & far
    rim = {}
    head_rows = (rr_ >= top_r - 2) & (rr_ <= neck_r)
    for pid, m_ in ((2, head_rows & ~ears), (3, ears), (1, ~head_rows)):
        # (an ear's band may be black: the orc's and the vampire's ears are drawn dark-edged)
        bd = ((lum_ <= 220) & far) if pid == 3 else band
        c2, n2 = common(m_ & bd & (dfa > 1.5) & (dfa <= 2.5))
        if c2 is None: continue
        ring = (m_ & (dfa > 1.5) & (dfa <= 2.5)).sum()
        if n2 < max(6, 0.12 * ring): continue
        same = np.all(raw['S'][:, :, :3] == np.array(c2), -1)
        n3 = (m_ & same & (dfa > 2.5) & (dfa <= 3.5)).sum()
        wd = 1.0 + min(n3 / max(n2, 1), 1.0)
        if pid == 1:
            # the body has its band only where the sprite draws one (the shoulders and the arms'
            # outer sides); below, the legs and feet are body without it (part 4)
            br = np.nonzero((m_ & same & (dfa > 1.5) & (dfa <= 2.5)).any(1))[0]
            part[(rr_ > neck_r) & ((rr_ < br.min()) | (rr_ > br.max() + 1))] = 4
            wd = min(wd, 1.25)
        if pid == 3: wd = min(wd, 0.6 if sum(c2) < 40 else 1.0)         # an ear's edge, thin: seen edge on, a wide band blacked the whole ear out
        rim[pid] = (c2, wd)
    # the sprite's black between arm and body and between the legs: not empty space but a thin
    # dark web set back between the parts, so from the game's corners the arms and legs keep the
    # sprite's deep shadow beside them (part 5)
    web = np.zeros((P, P), bool)
    for r in range(neck_r + 2, sole_r - 3):                             # (not between the feet: a floating dot)
        for c in np.nonzero(gapm[r])[0]:
            if alpha0[r, max(0, c - 5):c].any() and alpha0[r, c + 1:c + 6].any(): web[r, c] = True
    web &= ~alpha
    part[web] = 5; limb[web] = 5
    if pronounce and part_lines:
        # the thighs are legs where they stand out of the pelvis, so a line marks them off (the
        # skeleton's parts read best: each its own shape with a line between)
        part[thigh_px] = 4; limb[thigh_px & (limb == 1)] = 4
    h = np.where(web, 0.8, h); hf = np.where(web, 0.8, hf)
    LAST['web'] = web.copy()
    # the solid
    n = P * sub
    owner = np.zeros((n, n, n), np.int16)
    zz = (np.arange(n) + 0.5) / sub
    # horns follow the side picture: each row's horn sits where the side picture draws the horn
    # (bone-coloured pixels in that row), a round tube as thick as the front picture draws it -
    # the demon's horns sweep up and back from the brow, not stand as slabs at the front
    hz = np.full((P, P), np.nan); hcx = np.zeros((P, P)); hrad = np.zeros((P, P))
    if horn.any() and horn_follow and not horn_specs:
        hcol = raw['S'][horn & (raw['S'][:, :, :3].sum(2) > 150)][:, :3]
        if len(hcol):
            Ez = raw['E']; bone = (Ez[:, :, 3] > 0) & (np.abs(Ez[:, :, None, :3] - hcol[None, None]).sum(-1).min(-1) < 60)
            # (the bone's dark outline in the side picture is horn too)
            bp = np.pad(bone, 1); bone2 = bone | bp[:-2, 1:-1] | bp[2:, 1:-1] | bp[1:-1, :-2] | bp[1:-1, 2:]
            bone2 &= Ez[:, :, 3] > 0
            for r in range(P):
                if not horn[r].any(): continue
                zs_ = np.nonzero(bone2[r])[0]
                if not len(zs_):
                    near = [q for q in range(max(0, r - 3), min(P, r + 4)) if bone2[q].any()]
                    if not near: continue
                    zs_ = np.nonzero(bone2[min(near, key=lambda q: abs(q - r))])[0]
                ztarget = P - 1 - (zs_.min() + zs_.max()) / 2
                for a_, b_ in landmarks.runs(list(horn[r])):
                    cx_ = (a_ + b_ + 1) / 2; rad = (b_ - a_ + 1) / 2
                    depth_r = min(max((zs_.max() - zs_.min() + 1) / 2 - 1.0, rad * 0.8), rad * 1.1)   # round, the side picture's outline not counted
                    # pointed: thinner toward the tip (the horn's top row), full at its root
                    hr_rows = [q for q in range(P) if horn[q].any()]
                    cut_ = min(hr_rows) + horn_len * (max(hr_rows) - min(hr_rows))
                    if r > cut_: continue                 # below the cone: the sprite's bone strip down the head's side - a flat fin, not horn
                    tt_ = (r - min(hr_rows)) / max(cut_ - min(hr_rows), 1)
                    taper = horn_taper + (1 - horn_taper) * min(tt_ * 1.15, 1.0)
                    rad *= taper; depth_r *= taper
                    if horn_curve:
                        # a cone's axis runs straight from its root (the head's middle depth) to its
                        # tip (where the side picture draws the tip), and the cone is round
                        zt0 = [P - 1 - (np.nonzero(bone2[q])[0].min() + np.nonzero(bone2[q])[0].max()) / 2 for q in range(min(hr_rows), min(hr_rows) + 3) if bone2[q].any()]
                        z_tip = zt0[0] if zt0 else ztarget
                        z_root = zc[min(int(cut_), P - 1)]
                        ztarget = z_tip + (z_root - z_tip) * (1 - taper) / (1 - horn_taper + 1e-6)
                        depth_r = max(rad, 0.8)
                    for c in range(a_, b_ + 1):
                        hz[r, c] = ztarget; hcx[r, c] = cx_
                        uu = min(abs(c + 0.5 - cx_) / rad, 1.0)
                        hrad[r, c] = max(depth_r * (1 - uu ** 2) ** 0.5, 0.6)
    for r in range(P):
        for c in range(P):
            if not (alpha[r, c] or web[r, c]): continue
            if not np.isnan(hz[r, c]):
                zm = hz[r, c]; hb_ = hrad[r, c]
                ks = np.nonzero((zz >= zm - hb_) & (zz <= zm + hb_))[0]
                if not len(ks): ks = np.array([int(zm * sub)])
                owner[r * sub:(r + 1) * sub, c * sub:(c + 1) * sub, ks] = 6          # horns: their own part (a dark edge of their own)
                continue
            zm = zc[r] + ear_tilt[r, c] + zoff[r, c] + (0.6 if web[r, c] else 0.0)
            ks = np.nonzero((zz >= zm - hf[r, c]) & (zz <= zm + h[r, c]))[0]
            if not len(ks): ks = np.array([int(zm * sub)])
            owner[r * sub:(r + 1) * sub, c * sub:(c + 1) * sub, ks] = part[r, c]
    # stamp the horn cones
    horn_vox = np.zeros(owner.shape, bool)
    for hs in horn_specs:
        (r0_, x0_, z0_), (r1_, x1_, z1_) = hs['root'], hs['tip']
        out_ = -1.0 if hs['side'] == 0 else 1.0
        # a bow: the horn leans out from the root, then up and back toward the tip (bend moves the control point)
        cr, cx_c, cz_c = (r0_ + r1_) / 2, (x0_ + x1_) / 2 + out_ * 1.6 * horn_bend, (z0_ + z1_) / 2 + (z0_ - z1_) * 0.15 * horn_bend
        N_ = 60
        for k in range(N_ + 1):
            t = k / N_
            rr_p = (1 - t) ** 2 * r0_ + 2 * (1 - t) * t * cr + t ** 2 * r1_
            xx_p = (1 - t) ** 2 * x0_ + 2 * (1 - t) * t * cx_c + t ** 2 * x1_
            zz_p = (1 - t) ** 2 * z0_ + 2 * (1 - t) * t * cz_c + t ** 2 * z1_
            rad_p = max(hs['rad'] * (1 - t) ** 0.9, 0.35)
            cR, cX, cZ = rr_p * sub, xx_p * sub, zz_p * sub; rv = rad_p * sub
            lo = np.floor([cR - rv, cX - rv, cZ - rv]).astype(int); hi = np.ceil([cR + rv, cX + rv, cZ + rv]).astype(int)
            lo = np.clip(lo, 0, n - 1); hi = np.clip(hi, 0, n - 1)
            gr_, gx_, gz_ = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1), np.arange(lo[2], hi[2] + 1), indexing='ij')
            m_ = (gr_ + 0.5 - cR) ** 2 + (gx_ + 0.5 - cX) ** 2 + (gz_ + 0.5 - cZ) ** 2 <= rv ** 2
            horn_vox[gr_[m_], gx_[m_], gz_[m_]] = True
    if horn_vox.any(): owner[horn_vox] = 6
    # the pictures: outlines filled in; the side pictures' head rows in skin only
    fb = ((fr0 - 1, fr1), (fc0, fc1))
    # the unit's own colours, hair included: colours the front and back pictures use often (the
    # shades of hair are each rare, so a colour family counts together), not the dark outline
    own = []
    for f_ in 'SN':
        a_ = raw[f_][raw[f_][:, :, 3] > 0][:, :3]
        c_, k__ = np.unique(a_, axis=0, return_counts=True)
        own += [tuple(c) for c, kk in zip(c_.tolist(), k__.tolist()) if kk >= 0.006 * len(a_) and sum(c) >= 90]
    pic = {f: build3d11.clean_picture(raw[f], fb if f == 'S' else None, keep=own) for f in 'SNEW'}
    # the body's skin in broad areas: each pixel below the neck takes the commonest colour round
    # it (3x3), so the sprite's lit side and shadow side stay but single-pixel speckle doesn't
    # turn into blotches once it wraps round the 3D body
    for f in 'SNEW':
        im = pic[f]; out = im.copy()
        for r in range(neck_r + 2, P - 1):
            for c in range(1, P - 1):
                if im[r, c, 3] == 0 or (f == 'S' and web[r, c]): continue
                blk = im[r - 1:r + 2, c - 1:c + 2].reshape(-1, 4)
                blk = blk[blk[:, 3] > 0]
                cc, kk = np.unique(blk[:, :3], axis=0, return_counts=True)
                if kk.max() >= 4: out[r, c, :3] = cc[kk.argmax()]
        pic[f] = out
    # a few flat tones: every skin pixel (not the face's features, not the ears' edge) snaps to
    # the nearest of the race's commonest colours - the renderer's light does the shading, and
    # the sprite's own speckle wrapped round a 3D body read as dirt
    if tones:
        allpx = np.concatenate([pic[f][pic[f][:, :, 3] > 0][:, :3] for f in 'SN'])
        cs_t, ks_t = np.unique(allpx, axis=0, return_counts=True)
        order_ = np.argsort(-ks_t); pal_ = []
        for i_ in order_:
            c_ = cs_t[i_]
            if c_.sum() < 60: continue
            if all(np.abs(c_ - q).sum() > 36 for q in pal_): pal_.append(c_)
            if len(pal_) >= tones: break
        pal_ = np.array(pal_)
        keepm = np.zeros((P, P), bool)
        keepm[fr0:fr1, fc0:fc1 + 1] = feat[fr0:fr1, fc0:fc1 + 1]
        for f in 'SNEW':
            im = pic[f]; a_m = im[:, :, 3] > 0
            dd = np.abs(im[:, :, None, :3] - pal_[None, None]).sum(-1)
            near = dd.argmin(-1); dmin = dd.min(-1)
            snap = a_m & (dmin < 110) & ~(keepm if f == 'S' else np.zeros_like(keepm))
            im[snap, :3] = pal_[near[snap]]
    opq = pic['S'][alpha][:, :3]
    cs, ks_ = np.unique(opq, axis=0, return_counts=True)
    skins = np.array([c for c, k_ in zip(cs.tolist(), ks_.tolist()) if k_ >= 0.02 * len(opq) and sum(c) >= 100] or [cs[np.argmax(ks_)].tolist()])
    skin_mid = skins[np.abs(skins.sum(1) - np.median(skins.sum(1))).argmin()]
    keep = [tuple(c) for c in skins.tolist()] + list(own)
    for f_ in 'SN':                                                      # hair, scales, markings: common colours of front and back
        a_ = pic[f_][pic[f_][:, :, 3] > 0][:, :3]
        c_, k__ = np.unique(a_, axis=0, return_counts=True)
        keep += [tuple(c) for c, kk in zip(c_.tolist(), k__.tolist()) if kk >= 0.012 * len(a_) and sum(c) >= 60]
    keep = np.array(sorted(set(keep)))
    # the head's sides take only what the back of the head shows (skin, hair, scales): the side
    # pictures draw the eye in profile, and eye-white is common enough in the front to be kept
    nh = pic['N'][:Sp['neck'] + 2]; a_ = nh[nh[:, :, 3] > 0][:, :3]
    cN, kN = np.unique(a_, axis=0, return_counts=True)
    # (not the ears' and horns' own colours either: the side pictures draw the horn over the head)
    sa = raw['S'][:, :, 3] > 0
    def share_in_ears(c):
        m = sa & np.all(raw['S'][:, :, :3] == np.array(c), -1)
        return (m & ears).sum() / max(m.sum(), 1)
    keep_side = np.array(sorted(set([tuple(c) for c in skins.tolist() if share_in_ears(c) < 0.3] + [tuple(c) for c, kk in zip(cN.tolist(), kN.tolist()) if kk >= 0.02 * len(a_) and share_in_ears(c) < 0.3])))
    pic_ear = {f: pic[f].copy() for f in 'EW'}                           # ears and horns keep theirs
    for f in 'EW':
        im = pic[f]
        dist_ = np.abs(im[:, :, None, :3] - keep_side[None, None]).sum(-1).min(-1)
        bad = (dist_ > 50) & (im[:, :, 3] > 0) & (rr_ <= Sp['neck'] + 1)
        if horn.any():
            # the side picture draws the near horn's root across the head's side: never horn there
            hc_ = raw['S'][horn][:, :3]; hc_ = hc_[hc_.sum(1) > 450]
            if len(hc_):
                bad |= (np.abs(im[:, :, None, :3] - hc_[None, None]).sum(-1).min(-1) < 40) & (im[:, :, 3] > 0) & (rr_ <= Sp['neck'] + 1)
        im[bad, :3] = skin_mid
    sW = carve.best_shift(raw['E'][:, ::-1, 3] > 0, raw['W'][:, :, 3] > 0)
    # paint every surface block from the picture facing its way
    solid = owner > 0
    pd = np.pad(solid, 1)
    inner = pd[:-2, 1:-1, 1:-1] & pd[2:, 1:-1, 1:-1] & pd[1:-1, :-2, 1:-1] & pd[1:-1, 2:, 1:-1] & pd[1:-1, 1:-1, :-2] & pd[1:-1, 1:-1, 2:]
    surf = solid & ~inner
    sn = normals(solid, sigma=1.6)
    R, X, Z = np.nonzero(surf)
    nx, nz = sn[R, X, Z, 0], sn[R, X, Z, 2]
    ang = np.degrees(np.arctan2(nx, -nz))
    pr, pxl, pzl = R // sub, X // sub, Z // sub
    col = np.zeros(solid.shape + (4,), np.int32)
    def look(f, rows_, cols_):
        im = pic[f]; cols_ = np.clip(cols_, 0, P - 1)
        out = im[rows_, cols_].copy()
        empty = out[:, 3] == 0
        for i in np.nonzero(empty)[0]:
            row = im[rows_[i]]; ok = np.nonzero(row[:, 3] > 0)[0]
            out[i] = row[ok[np.argmin(np.abs(ok - cols_[i]))]] if len(ok) else np.append(skin_mid, 255)
        return out
    ny = sn[R, X, Z, 1]
    up = ny > 0.75
    sel = np.abs(ang) <= 52
    col[R[sel], X[sel], Z[sel]] = look('S', pr[sel], pxl[sel])
    sel = np.abs(ang) >= 128
    col[R[sel], X[sel], Z[sel]] = look('N', pr[sel], P - 1 - pxl[sel])
    sel = (np.abs(ang) > 52) & (np.abs(ang) < 128) & (ang < 0)
    col[R[sel], X[sel], Z[sel]] = look('E', pr[sel], P - 1 - pzl[sel])
    sel = (np.abs(ang) > 52) & (np.abs(ang) < 128) & (ang >= 0)
    col[R[sel], X[sel], Z[sel]] = look('W', pr[sel], pzl[sel] - sW)
    eo = owner[R, X, Z] == 3
    for f, sg in (('E', -1), ('W', 1)):
        sel = (np.abs(ang) > 52) & (np.abs(ang) < 128) & ((ang < 0) if sg < 0 else (ang >= 0)) & eo
        if sel.any():
            pic[f], keep_pic = pic_ear[f], pic[f]
            col[R[sel], X[sel], Z[sel]] = look(f, pr[sel], (P - 1 - pzl[sel]) if sg < 0 else (pzl[sel] - sW))
            pic[f] = keep_pic
    if up.any():
        # the crown's top takes the colour a little way down the head, not the outline-dark top row
        # of hair (the elf's dark grey edge came out as stripes over the crown)
        hr_ = pr[up] <= Sp['neck']
        prt = np.where(hr_, np.minimum(pr[up] + 2, Sp['neck']), pr[up])
        tops = look('S', prt, pxl[up])
        dd_ = np.abs(tops[:, None, :3] - keep[None, :, :3]).sum(-1).min(-1)
        tops[dd_ > 50, :3] = skin_mid                                  # tops: no outline-coloured lids
        # the top of the head: the colour the back picture draws there (hair), not the forehead
        if hr_.any():
            tb = look('N', prt[hr_], P - 1 - pxl[up][hr_])
            ok_ = np.abs(tb[:, None, :3] - keep[None, :, :3]).sum(-1).min(-1) <= 50
            tt = tops[hr_]; tt[ok_] = tb[ok_]; tops[hr_] = tt
        col[R[up], X[up], Z[up]] = tops
    col[owner == 5] = (10, 5, 2, 255)
    if horn_vox.any():
        hb_ = (horn_specs and tuple(int(v) for v in np.median(raw['S'][horn][:, :3][raw['S'][horn][:, :3].sum(1) > 450], axis=0))) or (240, 238, 214)
        col[horn_vox, :3] = hb_; col[horn_vox, 3] = 255
    # bone-coloured paint that landed on the head itself (the side and back pictures draw the horn
    # across the head) goes back to the head's colour above the mouth: it smeared down the head's
    # side as a cream streak from the horn's root
    if horn.any() and horn_smear:
        hcb = raw['S'][horn][:, :3]; hcb = hcb[hcb.sum(1) > 450]
        if len(hcb):
            cut_row = int(top_r + 0.62 * (neck_r - top_r))
            hv2 = (owner == 2) & (np.arange(n)[:, None, None] // sub <= cut_row)
            R2, X2, Z2 = np.nonzero(hv2)
            dd2 = np.abs(col[R2, X2, Z2, :3][:, None] - hcb[None]).sum(-1).min(-1)
            bad2 = dd2 < 90
            col[R2[bad2], X2[bad2], Z2[bad2], :3] = skin_mid
    # the sprite's black line across the ankle, kept as a dark ring where leg meets foot
    if ankle.any():
        av = solid & ankle[np.arange(n)[:, None] // sub, np.arange(n)[None, :] // sub][:, :, None]
        ar_, ax_, az_ = np.nonzero(av); col[ar_, ax_, az_, :3] = raw['S'][ar_ // sub, ax_ // sub, :3]
    # an ear's dark edge is its own colour, as the sprite draws it (mostly outline round a little
    # colour) - cleaned to skin, the orc's and goblin's ears came out as plain round mitts
    if ear_edge:
        rawS = raw['S'][:, :, :3].copy(); dark_ = (rawS.sum(2) < 130) & (raw['S'][:, :, 3] > 0) & ears & ~horn
        # ...all but its outermost pixel, which takes the colour inside it: the renderer draws its
        # own outline round the ear, and the two together blacked the ear out
        outer = dark_ & (dfull <= 1.0)
        inner_c = ears & ~dark_
        for _ in range(4):
            todo = outer & ~inner_c
            if not todo.any(): break
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                src = np.roll(np.roll(inner_c, dy, 0), dx, 1) & todo
                rawS[src] = np.roll(np.roll(rawS, dy, 0), dx, 1)[src]; inner_c = inner_c | src; todo &= ~src
        paint = dark_ & ~(outer & ~inner_c) | (outer & inner_c)
        ev = (owner == 3) & paint[np.arange(n)[:, None] // sub, np.arange(n)[None, :] // sub][:, :, None]
        if ev.any():
            er_, ex_, ez_ = np.nonzero(ev)
            col[er_, ex_, ez_, :3] = rawS[er_ // sub, ex_ // sub]
    # a horn is bone all round: every side of it takes the front picture's colour there
    hv = solid & horn[np.arange(n)[:, None] // sub, np.arange(n)[None, :] // sub][:, :, None]
    if hv.any():
        hr, hx, hz = np.nonzero(hv)
        col[hr, hx, hz] = look('S', hr // sub, hx // sub)
    col[..., 3] = np.where(solid, 255, 0)
    # the head a size bigger than the front picture draws it, grown from the neck: the sprites'
    # big heads came out small on the full 3D bodies at the game's corners (the bodies and feet
    # took on their side pictures' depth, the head kept the front picture's width)
    # the face's features (eyes, mouth, tusks) take full light: shaded, the eye-whites went grey
    featv = solid & feat[np.arange(n)[:, None] // sub, np.arange(n)[None, :] // sub][:, :, None] & (np.arange(n)[None, None, :] < (zc[np.arange(n) // sub] * sub)[:, None, None])
    hsy = head_scale if head_scale_y is None else head_scale_y            # (a squatter head: less up than across)
    if head_scale != 1.0 or hsy != 1.0:
        hv = np.isin(owner, [2, 3])
        if hv.any():
            # the inside of the head gets its surface's colour first: resizing brings inner
            # blocks out to the surface, and unpainted they showed as a black patch
            painted = surf.copy()
            for _ in range(12):
                if not (hv & ~painted).any(): break
                for ax in range(3):
                    for sh in (1, -1):
                        fill_ = hv & ~painted & np.roll(painted, sh, axis=ax)
                        col[fill_] = np.roll(col, sh, axis=ax)[fill_]; painted |= fill_
            pr0 = (neck_r + 1) * sub; px0 = 32.0 * sub; pz0 = zc[neck_r] * sub
            HR, HX, HZ = np.nonzero(hv)
            r0 = max(0, int(pr0 - (pr0 - HR.min()) * max(hsy, 1.0)) - 1)
            x0 = max(0, int(px0 - (px0 - HX.min()) * head_scale) - 1); x1 = min(n, int(px0 + (HX.max() - px0) * head_scale) + 2)
            z0 = max(0, int(pz0 - (pz0 - HZ.min()) * head_scale) - 1); z1 = min(n, int(pz0 + (HZ.max() - pz0) * head_scale) + 2)
            tr, tx, tz = np.meshgrid(np.arange(r0, pr0), np.arange(x0, x1), np.arange(z0, z1), indexing='ij')
            sr = np.clip(np.round(pr0 + (tr + 0.5 - pr0) / hsy - 0.5), 0, n - 1).astype(int)
            sx = np.clip(np.round(px0 + (tx + 0.5 - px0) / head_scale - 0.5), 0, n - 1).astype(int)
            sz = np.clip(np.round(pz0 + (tz + 0.5 - pz0) / head_scale - 0.5), 0, n - 1).astype(int)
            take = hv[sr, sx, sz]
            ow2 = owner.copy(); col2 = col.copy(); fv2 = featv.copy()
            ow2[hv] = 0; col2[hv] = 0; fv2[hv] = False
            free = ow2[tr, tx, tz] == 0                                   # (never over the body)
            m_ = take & free
            ow2[tr[m_], tx[m_], tz[m_]] = owner[sr[m_], sx[m_], sz[m_]]
            col2[tr[m_], tx[m_], tz[m_]] = col[sr[m_], sx[m_], sz[m_]]
            fv2[tr[m_], tx[m_], tz[m_]] = featv[sr[m_], sx[m_], sz[m_]]
            owner, col, featv = ow2, col2, fv2
            solid = owner > 0
    M = build3d9.Model(sub, n, owner.astype(np.int32), col, featv & solid, (32.0 * sub, 31.5 * sub))
    M.limb = limb                                                        # the part map (see LAST['limb'])
    M.min_line = min_line
    M.outline_col = outline_col or (30, 32, 38); M.rim = rim; M.noline = (5,) if (pronounce and part_lines) else (4, 5)
    M.line_col = (34, 14, 4)                                             # lines inside the figure: dark brown, as the sprites draw the arm over the body
    if style == 'grey':
        # (the look you liked: a thin cool dark outline and lines, no brown band inside it)
        M.outline_col = (30, 32, 38); M.line_col = (30, 32, 38)
        # ...but the ears keep their dark edge: the sprites draw most of an ear as its outline,
        # and without it the ears shrank to small rounded tabs
        M.rim = {3: rim[3]} if (3 in rim and ear_rim and not ear_edge) else {}
    # light from broader normals: the balloon's surface steps pixel by pixel, and fine normals
    # broke the light bands into blotches
    if (owner == 6).any() and horn_edge:
        M.rim = dict(M.rim); M.rim[6] = (tuple(horn_edge), 1.0)
    M.sn = render3.smooth_normals(M, sigma=normal_sigma); M.slope_lines = True
    M.smooth_light = smooth_light
    if bright != 1.0:
        sv = owner > 0
        col[sv, :3] = np.clip(col[sv, :3].astype(float) * bright, 0, 255).astype(np.int32)
    M.ao = occlusion(solid, M.sn, strength=ao_strength) if ao_strength > 0 else None
    LAST.update(outline=M.outline_col, rim=rim)
    return M, raw['S']

def sheet(out, races, K=5):
    C = 64 * K
    img = Image.new('RGBA', (C * 5, C * len(races)), (52, 56, 66, 255))
    for i, rc in enumerate(races):
        M, S = inflate(rc)
        bg = Image.new('RGBA', (C, C), (60, 64, 76, 255)); bg.alpha_composite(Image.fromarray(S.astype(np.uint8)).resize((C, C), Image.NEAREST))
        img.alpha_composite(bg, (0, i * C))
        img.alpha_composite(render3.render(M, 0, 0, scale=K, size=C, foot=1.0, inner=True), (C, i * C))
        img.alpha_composite(render3.render(M, 90, 0, scale=K, size=C, foot=1.0, inner=True), (2 * C, i * C))
        img.alpha_composite(render3.render(M, 45, 37, scale=K * 0.9, size=C, stretch=1.2, foot=0.86, shadow=True, inner=True), (3 * C, i * C))
        img.alpha_composite(render3.render(M, 315, 37, scale=K * 0.9, size=C, stretch=1.2, foot=0.86, shadow=True, inner=True), (4 * C, i * C))
        print(rc, flush=True)
    img.save(out)

if __name__ == '__main__':
    sheet(sys.argv[1], sys.argv[2].split(','))
