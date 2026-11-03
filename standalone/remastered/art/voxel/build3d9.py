# The 3D unit for any race (after build3d8.py, which builds the human). Each race's sprites are
# drawn on the same 64 px layout as the human's but with their own proportions (a dwarf's head
# sits low, a goblin's head is big, an elf is tall). So:
#  1. landmarks are measured from the race's bare body sprite and the human's (head top, neck,
#     sole; head, body and leg half-widths and depths);
#  2. every sprite layer of the race is remapped onto the human layout and the unit is built by
#     build3d8 exactly like a human (all the sculpted armour fits);
#  3. the finished model is remapped back to the race's proportions, voxel by voxel;
#  4. the weapon and the shield are not reshaped: they follow the hand (or the shield's middle)
#     and keep their shape (goblins and kobolds carry 0.75-size ones);
#  5. anything the race's body sprite draws outside the model (ears, horns, a snout, a crest of
#     hair) is added from the race's own pictures.
import numpy as np, math
import compose64, build3d8, landmarks
from build3d3 import normals
from build3d6 import CZ, Rig

P = 64
SMALL = {'Goblins': 0.75, 'Kobold': 0.75}

def measure(race):
    S, E = landmarks.alpha(race, 'S'), landmarks.alpha(race, 'E')
    width = np.array([S[r].sum() for r in range(P)])
    rows = np.nonzero(S.any(1))[0]; top, sole = int(rows.min()), int(rows.max())
    H = sole - top
    head_max = top + int(np.argmax(width[top:top + int(0.35 * H) + 1]))
    seg = width[head_max + 1:top + int(0.75 * H)]
    lo_ = seg.min()
    neck = head_max + 1 + int(np.nonzero(seg <= lo_)[0].max())          # the lowest of the narrowest rows
    def span(img, r0, r1):
        ws, cs = [], []
        for r in range(r0, r1 + 1):
            if img[r].any():
                xs = np.nonzero(img[r])[0]; ws.append((xs.max() - xs.min() + 1) / 2); cs.append((xs.max() + xs.min() + 1) / 2)
        return (float(np.median(ws)), float(np.median(cs))) if ws else (1.0, 32.0)
    head_w, _ = span(S, top, neck - 1); head_d, head_c = span(E, top, neck - 1)
    body_w, _ = span(S, neck + 2, sole - 6); body_d, body_c = span(E, neck + 2, sole - 6)
    leg_d, leg_c = span(E, sole - 4, sole)
    lr = sorted(landmarks.runs(S[sole - 2]), key=lambda t: -(t[1] - t[0]))[:2]
    leg_sp = (abs((lr[0][0] + lr[0][1]) - (lr[1][0] + lr[1][1])) / 4) if len(lr) == 2 else 6.5
    # the skull (not ears, horns or a crest): where and how big the race's own fitted helmet is
    try:
        import dmi
        hm = dmi.load(landmarks.R.replace('Races64/', 'Gear64/') + race + '/iron.dmi')['helmet.nasal.iron']
        hs = np.asarray(dmi.frame(hm, 'S').convert('RGBA'))[:, :, 3] > 0
        he = np.asarray(dmi.frame(hm, 'E').convert('RGBA'))[:, :, 3] > 0
        top = 11 + int(np.nonzero(hs.any(1))[0].min()) - 5             # the human's helmet tip is 6 rows above its head
        head_w = max(hs[r].sum() for r in range(P)) / 2 - 1.0
        head_d = max(he[r].sum() for r in range(P)) / 2 - 2.0
    except Exception:
        pass
    return dict(top=top, neck=neck, sole=sole, head_w=head_w, head_d=head_d, head_z=P - head_c, body_w=body_w,
                body_d=body_d, body_z=P - body_c, leg_sp=leg_sp, leg_d=leg_d, leg_z=P - leg_c)

class Warp:
    """Race layout <-> human layout. Rows: piecewise linear through head top, neck and sole.
    Across and in depth: per-row scales about per-row centres, blended between head, body and
    legs."""
    def __init__(self, race):
        self.race = race
        self.r, self.h = measure(race), measure('Human')
    def _knots(self, a, b):
        return np.array([a['top'], a['neck'], a['sole']], float), np.array([b['top'], b['neck'], b['sole']], float)
    def to_human_row(self, rr):
        kr, kh = self._knots(self.r, self.h)
        s0 = (kh[1] - kh[0]) / max(kr[1] - kr[0], 1e-6)
        return np.where(rr < kr[0], kh[0] + (rr - kr[0]) * s0, np.interp(rr, kr, kh))
    def to_race_row(self, hr):
        kr, kh = self._knots(self.r, self.h)
        s0 = (kr[1] - kr[0]) / max(kh[1] - kh[0], 1e-6)
        return np.where(hr < kh[0], kr[0] + (hr - kh[0]) * s0, np.interp(hr, kh, kr))
    def _blend(self, rr, head, body, legs):
        """A value along the race's rows: head above the neck, body below it, legs at the feet."""
        n, s = self.r['neck'], self.r['sole']
        t1 = np.clip((rr - (n - 1.5)) / 3.0, 0, 1)                       # head -> body round the neck
        t2 = np.clip((rr - (n + 0.62 * (s - n))) / (0.3 * (s - n)), 0, 1) # body -> legs toward the feet
        return head * (1 - t1) + (body * (1 - t2) + legs * t2) * t1
    def sx(self, rr):
        r, h = self.r, self.h
        return self._blend(rr, h['head_w'] / r['head_w'], h['body_w'] / r['body_w'], h['leg_sp'] / r['leg_sp'])
    def sz(self, rr):
        r, h = self.r, self.h
        return self._blend(rr, h['head_d'] / r['head_d'], h['body_d'] / r['body_d'], h['leg_d'] / r['leg_d'])
    def zc(self, rr, who):
        m = self.r if who == 'r' else self.h
        return self._blend(rr, m['head_z'], m['body_z'], m['leg_z'])
    # race coordinates -> human coordinates (and back)
    def to_human(self, rr, rx, rz):
        hr = self.to_human_row(rr)
        return hr, 32 + (rx - 32) * self.sx(rr), CZ + (rz - self.zc(rr, 'r')) * self.sz(rr)
    def to_race(self, hr, hx, hz):
        rr = self.to_race_row(hr)
        return rr, 32 + (hx - 32) / self.sx(rr), self.zc(rr, 'r') + (hz - CZ) / self.sz(rr)
    # a race picture -> the same picture on the human layout
    def picture(self, im, facing):
        a = np.asarray(im.convert('RGBA'))
        hr, hc = np.mgrid[0:P, 0:P].astype(float); hr += 0.5; hc += 0.5
        if facing in 'SN':
            hx = hc if facing == 'S' else P - hc
            rr, rx, _ = self.to_race(hr, hx, np.full_like(hr, CZ))
            col = rx if facing == 'S' else P - rx
        else:
            hz = P - hc if facing == 'E' else hc
            rr, _, rz = self.to_race(hr, np.full_like(hr, 32.0), hz)
            col = P - rz if facing == 'E' else rz
        ri, ci = np.floor(rr).astype(int), np.floor(col).astype(int)
        ok = (ri >= 0) & (ri < P) & (ci >= 0) & (ci < P)
        out = np.zeros_like(a); out[ok] = a[ri[ok], ci[ok]]
        from PIL import Image
        return Image.fromarray(out.astype(np.uint8))

class Model:
    """A finished voxel model (what render3 draws)."""
    def __init__(self, sub, n, owner, col, lit, center):
        self.sub, self.n, self.owner, self.col, self.lit, self.center = sub, n, owner, col, lit, center
        self.part = owner; self.sn = normals(owner > 0)
    def solid(self): return self.owner > 0

def build(lo, rig=None, sub=2, zoff=12, keep_base=True):
    race = getattr(lo, 'race', 'Human')
    if race == 'Human':
        return build3d8.build(lo, rig, sub=sub, zoff=zoff)
    if not getattr(lo, 'body', None): lo.body = ('Races64/%s.dmi' % race, landmarks.body_state(race))
    W = Warp(race)
    compose64.WARP = W.picture
    try:
        G, full_h = build3d8.build(lo, rig, sub=sub, zoff=zoff)
    finally:
        compose64.WARP = None
    n = G.n
    if not keep_base:                                 # build3d10 brings the race's own body
        for pid in G.base: G.owner[G.owner == pid] = 0
    rigid = np.zeros(G.owner.shape, bool)
    for name, a, b, anchor in G.rigid:
        rigid |= (G.owner >= a) & (G.owner < b)
    # 3. race grid <- human grid
    Ri, Xi, Zi = np.meshgrid(*(np.arange(n),) * 3, indexing='ij')
    rr, rx, rz = (Ri + 0.5) / sub, (Xi + 0.5) / sub, (Zi + 0.5) / sub - zoff
    hr, hx, hz = W.to_human(rr, rx, rz)
    HR, HX, HZ = np.floor(hr * sub).astype(int), np.floor(hx * sub).astype(int), np.floor((hz + zoff) * sub).astype(int)
    ok = (HR >= 0) & (HR < n) & (HX >= 0) & (HX < n) & (HZ >= 0) & (HZ < n)
    owner = np.zeros(G.owner.shape, G.owner.dtype); col = np.zeros(G.col.shape, G.col.dtype); lit = np.zeros(G.owner.shape, bool)
    src = (HR[ok], HX[ok], HZ[ok])
    keep = ~rigid[src]
    idx = tuple(a[keep] for a in np.nonzero(ok))
    s2 = tuple(a[keep] for a in src)
    owner[idx] = G.owner[s2]; col[idx] = G.col[s2]; lit[idx] = G.lit[s2]
    # ears, horns and crests first, judged against the body and head only (not the weapon or shield)
    if keep_base: add_features(owner, col, lit, W, lo, sub, zoff)
    # 4. weapon and shield: moved with their anchor, shape kept (smaller for small races)
    k = SMALL.get(race, 1.0)
    for name, a, b, anchor in G.rigid:
        m = (G.owner >= a) & (G.owner < b)
        if not m.any(): continue
        pr, px, pz = [np.asarray(v, float) for v in np.nonzero(m)]
        hr_, hx_, hz_ = (pr + 0.5) / sub, (px + 0.5) / sub, (pz + 0.5) / sub - zoff
        A = anchor if anchor is not None else np.array([hx_.mean(), hr_.mean(), hz_.mean()])
        ar, ax, az = W.to_race(np.array([A[1]]), np.array([A[0]]), np.array([A[2]]))
        nr, nx, nz = ar[0] + k * (hr_ - A[1]), ax[0] + k * (hx_ - A[0]), az[0] + k * (hz_ - A[2])
        NR, NX, NZ = np.floor(nr * sub).astype(int), np.floor(nx * sub).astype(int), np.floor((nz + zoff) * sub).astype(int)
        good = (NR >= 0) & (NR < n) & (NX >= 0) & (NX < n) & (NZ >= 0) & (NZ < n)
        sidx = tuple(np.nonzero(m)[i][good] for i in range(3))
        didx = (NR[good], NX[good], NZ[good])
        owner[didx] = G.owner[sidx]; col[didx] = G.col[sidx]; lit[didx] = G.lit[sidx]
    M = Model(sub, n, owner, col, lit, G.center)
    M.joints = G.joints; M.helmet = getattr(G, 'helmet', set())
    return M, compose64.unit(race_layers(lo))

def add_features(owner, col, lit, W, lo, sub, zoff):
    """Ears, horns, crests: what the race's bare body sprite draws around its head that the model
    does not fill. Each such pixel of the front picture becomes a thin fin at the head's depth
    (ears are flat), filling only empty space, so the head, helmet and arms are untouched;
    above the model (horn tips) it takes the side picture's depth. Painted from the pictures."""
    race = lo.race
    S = landmarks.alpha(race, 'S'); E = landmarks.alpha(race, 'E')
    import dmi
    d_ = dmi.load(landmarks.R + race + '.dmi')[landmarks.body_state(race)]
    from build3d import deoutline
    from build3d2 import filled
    pics = {f: filled(deoutline(np.asarray(dmi.frame(d_, f).convert('RGBA')).astype(np.int32))) for f in 'SE'}
    n = owner.shape[0]
    neck = int(W.r['neck'])
    for row in range(0, neck + 1):
        cols = np.nonzero(S[row])[0]; zcols = np.nonzero(E[row])[0]
        if not len(cols) or not len(zcols): continue
        zs = P - 1 - zcols
        zmid = float(np.median(zs))
        r0 = row * sub
        rowblk = owner[r0:r0 + sub] > 0
        for c in cols:
            if abs(c + 0.5 - 32) > 22: continue
            X0 = int(c * sub)
            pc = pics['S'][row, c]
            if pc[:3].sum() < 120: continue                           # the sprite's outline: the renderer draws its own
            # thicker at the root, thin at the tip
            dist = max(0.0, abs(c + 0.5 - 32) - W.r['head_w']) + max(0.0, W.r['top'] - row)
            half = max(0.5, 1.6 - 0.18 * dist)
            band = zs[np.abs(zs - zmid) <= half]
            for zz in band:
                Z0 = int((zz + zoff) * sub)
                blk = (slice(r0, r0 + sub), slice(X0, X0 + sub), slice(Z0, Z0 + sub))
                if Z0 < 0 or Z0 + sub > n or X0 + sub > n: continue
                if (owner[blk] > 0).any(): continue
                owner[blk] = 1; col[blk] = pc; lit[blk] = True

def race_layers(lo):
    """The race's own sprite layers (not remapped), for side-by-sides."""
    race = getattr(lo, 'race', 'Human')
    BODY = getattr(lo, 'body', None) or ('Races64/%s.dmi' % race, landmarks.body_state(race))
    srcs = [BODY] + [s for s in (lo.legs, lo.chest) if s] + (list(lo.arms) if lo.arms else []) + [s for s in (lo.helmet, lo.shield, lo.weapon) if s]
    return srcs
