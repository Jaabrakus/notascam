# The 3D human in any of the game's gear (after build3d6.py: same rig, same look for the iron
# knight). A Loadout names the sprite layer for each slot (Gear64/Human/<tier>.dmi states).
#  - Shapes: the body and limbs as before; helmets, shields and weapons each have a 3D shape per
#    type (kettle/nasal/horned/winged/great helm/crested; any shield from its outline; dagger,
#    swords, scimitar, axes, hammer, mace, morning star, spear, halberd, pickaxe); robes add a
#    skirt.
#  - Colours: "relit" from the sprite layers. Each layer's colours are split into ramps (greys;
#    each hue), every pixel becomes (ramp, shade); the sprite's own broad light is taken out
#    (shade minus the local average shade) so only its pattern stays (mail rings, scales,
#    rivets, the tabard's cross), and the 3D light picks the shade. Dark neutral lines stay as
#    seams. So every tier recolours itself from its own sprites.
#  - Which layer covers a body part is read from the sprites (the topmost layer drawn there);
#    limbs that move are read at their resting place (so a raised arm keeps its own colours).
# Sizes are in sprite pixels: x across the front picture, row down it, z front->back.
import numpy as np, math, colorsys
import compose64, carve
from build3d2 import P, arr, filled
from build3d import deoutline
from build3d3 import ramp_of, SEAM, plate_rows
from build3d4 import skin_face
from build3d6 import (Space, swing_point, Grid, Rig, walk_rig, attack_rig, CZ, SHOULDER_R, SHOULDER_L,
                      HIP_ROW)
from build3d3 import LIGHT

GEAR = 'Gear64/Human/'

class Loadout:
    """Sprite layers per slot: (file, state) or None. tier files are Gear64/Human/<tier>.dmi."""
    def __init__(self, chest=None, legs=None, arms=None, helmet=None, shield=None, weapon=None, hair='HumanBrown'):
        self.chest, self.legs, self.arms, self.helmet, self.shield, self.weapon, self.hair = chest, legs, arms, helmet, shield, weapon, hair
    @staticmethod
    def of(tier, chest=None, legs=None, arms=None, helmet=None, shield=None, weapon=None, hair='HumanBrown', race='Human'):
        """Loadout.of('iron', chest='plate', legs='plate', arms='plate', helmet='nasal', ...); race picks
        the gear fitted to that race's body (Gear64/<race>/) and its body sheet."""
        f = 'Gear64/%s/%s.dmi' % (race, tier) if race != 'Human' else GEAR + tier + '.dmi'
        g = lambda kind, name: (f, '%s.%s.%s' % (kind, name, tier)) if name else None
        lo = Loadout(g('chest', chest), g('legs', legs), None, g('helmet', helmet), g('shield', shield), g('weapon', weapon), hair)
        lo.arms = ((f, 'arms.%s.%s.L' % (arms, tier)), (f, 'arms.%s.%s.R' % (arms, tier))) if arms else None
        lo.race = race
        return lo
    race = 'Human'
    def kind(self, slot):
        L = getattr(self, slot)
        if L and slot == 'arms': L = L[0]
        return L[1].split('.')[1] if L else None

KNIGHT = Loadout.of('iron', chest='plate', legs='plate', arms='plate', helmet='nasal', shield='heater', weapon='longsword')

# ---------- colour analysis ----------
def band(n):
    d = n @ LIGHT
    return np.searchsorted(np.array([-0.5, 0.6, 0.9]), d)       # 0 shade .. 3 facing the light

def hsv(c): return colorsys.rgb_to_hsv(*(np.asarray(c[:3]) / 255.0))

class Layer:
    """One sprite layer's four facings, lined up with the model, split into colour ramps."""
    def __init__(self, src, sN, sW, f=0):
        self.src = src
        u = compose64.unit([src], f)
        raw = {d: arr(u[d]) for d in 'SNEW'}
        self.sN, self.sW = sN, sW
        self.cover = {d: raw[d][:, :, 3] > 0 for d in 'SNEW'}
        img = {d: deoutline(raw[d]) for d in 'SNEW'}
        self.raw, self.img = raw, img
        # ramps: greys together, colours by hue; dark neutral lines are seams
        px = np.concatenate([img[d][self.cover[d]] for d in 'SNEW'])
        cols, cnt = np.unique(px[:, :3], axis=0, return_counts=True)
        info = []
        for c, n_ in zip(cols.tolist(), cnt.tolist()):
            h, s, v = hsv(c)
            seam = sum(c) < 120 and s < 0.35
            info.append((tuple(c), n_, h, s, seam))
        # one material's shades: colours join (chained) when close in hue (hue does not count
        # for near-whites and near-blacks), saturation and brightness -- skin and hair browns
        # share a hue but not saturation; a material's highlight and shadow share both
        colours = [i for i in info if not i[4]]
        parent = list(range(len(colours)))
        def root(a):
            while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
            return a
        vals = [hsv(i[0]) for i in colours]
        for a in range(len(colours)):
            for b in range(a + 1, len(colours)):
                (h1, s1, v1), (h2, s2, v2) = vals[a], vals[b]
                hue_ok = min(abs(h1 - h2), 1 - abs(h1 - h2)) < 0.06 or min(s1, s2) < 0.06
                if hue_ok and abs(s1 - s2) < 0.25 and abs(v1 - v2) < 0.5:
                    parent[root(a)] = root(b)
        bucket = {}
        for a, i in enumerate(colours): bucket.setdefault(root(a), []).append(i)
        groups = list(bucket.values())
        self.ramps = [sorted([g[0] + (255,) for g in grp], key=lambda c: sum(c[:3])) for grp in groups]
        self.weight = [sum(g[1] for g in grp) for grp in groups]
        lut = {}
        for gi, ramp in enumerate(self.ramps):
            for k, c in enumerate(ramp): lut[c[:3]] = (gi, k)
        seams = {i[0] for i in info if i[4]}
        # per facing: ramp id, shade, pattern offset, seam
        self.gid, self.k, self.off, self.seam = {}, {}, {}, {}
        for d in 'SNEW':
            a = img[d]; cv = self.cover[d]
            gid = np.full((P, P), -1); kk = np.zeros((P, P)); sm = np.zeros((P, P), bool)
            for r_ in range(P):
                for c_ in np.nonzero(cv[r_])[0]:
                    t = tuple(a[r_, c_, :3])
                    if t in seams: sm[r_, c_] = True
                    elif t in lut: gid[r_, c_], kk[r_, c_] = lut[t]
            off = np.zeros((P, P))
            for gi in range(len(self.ramps)):
                m = (gid == gi).astype(float)
                if not m.any(): continue
                ker = np.ones(7)
                cs = lambda q: np.apply_along_axis(lambda v: np.convolve(v, ker, 'same'), 1, np.apply_along_axis(lambda v: np.convolve(v, ker, 'same'), 0, q))
                mean = cs(kk * m) / np.maximum(cs(m), 1e-6)
                off[gid == gi] = np.round(kk - mean)[gid == gi]
            self.gid[d], self.k[d], self.off[d], self.seam[d] = gid, kk, np.clip(off, -2, 2), sm
        self.base = []
        for gi in range(len(self.ramps)):
            ks = np.concatenate([self.k[d][self.gid[d] == gi] for d in 'SNEW'])
            mid = (len(self.ramps[gi]) - 1) // 2             # the darker middle shade, as the sprites
            self.base.append(min(int(np.floor(np.median(ks))), mid) if len(ks) else mid)
    def set_smooth(self, smooth):
        """Smooth gear (plate, helmets) keeps only its drawn lines and strong highlights (rivets);
        patterned gear (mail, scales...) keeps its pattern, softened to one shade either way."""
        for d in 'SNEW':
            o = self.off[d]
            self.off[d] = np.where(o >= 2, 1, 0) if smooth else np.clip(o, -1, 1)
        return self
    def col(self, d, k):
        if d == 'S': return k
        if d == 'N': return P - 1 - k + self.sN
        if d == 'E': return P - 1 - k
        return k - self.sW
    def main(self):
        return int(np.argmax(self.weight)) if self.weight else 0
    def ramp_colour(self, gi, idx):
        R = self.ramps[gi]; return np.array(R)[np.clip(idx, 0, len(R) - 1)]

def sector(ax, az, front=45, back=45):
    t = np.degrees(np.arctan2(ax, -az))
    return np.where(np.abs(t) <= front, 0, np.where(np.abs(t) >= 180 - back, 1, np.where(t > 0, 3, 2)))   # S N E W

def relit(layers, centre, front=45, back=45, face=None, reach=6, sides='EW', rows=None, top=None):
    """Paint from the topmost of `layers` (top first) drawn at the facing the block looks toward,
    relit by the 3D light. centre(r) -> (cx, cz, rx, rz) of the part. face: (img, front) to
    keep the original front picture (the face) where the S facing is used. sides: the side
    facings this part may use (a limb's inner side is hidden by the body in the side picture,
    so it takes the front or back instead). rows: (offset, seam) per sprite row, the plate
    bands of smooth armour read off the front picture (build3d3.plate_rows). top: (ramp, base)
    for blocks facing up, which no picture shows (a helmet's crown)."""
    def paint(r, x, z, n):
        cx, cz, rx, rz = centre(r)
        sec = sector((x - cx) / rx, (z - cz) / rz, front, back)
        for si, dname in ((2, 'E'), (3, 'W')):
            if dname not in sides: sec = np.where(sec == si, np.where(z < cz, 0, 1), sec)
        pr = np.clip(r.astype(int), 0, P - 1); px = np.clip(x.astype(int), 0, P - 1); pz = np.clip(z.astype(int), 0, P - 1)
        out = np.zeros((len(r), 4), np.int32); out[:] = (128, 128, 128, 255)
        todo = np.ones(len(r), bool)
        b = band(n)
        for si, d in enumerate('SNEW'):
            sel = sec == si
            if not sel.any(): continue
            k = px if d in 'SN' else pz
            # look sideways a little if nothing is drawn exactly there
            for off in [0] + [s * i for i in range(1, reach + 1) for s in (1, -1)]:
                for L in layers:
                    c = L.col(d, k + off); ok = sel & todo & (c >= 0) & (c < P)
                    if not ok.any(): continue
                    cc = np.clip(c, 0, P - 1)
                    hit = ok & L.cover[d][pr, cc]
                    if not hit.any(): continue
                    gid = L.gid[d][pr[hit], cc[hit]]; sm = L.seam[d][pr[hit], cc[hit]]
                    res = np.zeros((hit.sum(), 4), np.int32)
                    for gi in np.unique(gid[gid >= 0]):
                        m = gid == gi
                        idx = L.base[gi] + b[hit][m] - 1 + L.off[d][pr[hit][m], cc[hit][m]].astype(int)
                        res[m] = L.ramp_colour(gi, idx)
                    res[sm | (gid < 0)] = SEAM
                    if rows is not None:
                        rh = pr[hit]; dark = rows[0][rh] < 0
                        for gi in np.unique(gid[dark & (gid >= 0)]):
                            m = dark & (gid == gi)
                            idx = L.base[gi] + b[hit][m] - 2 + L.off[d][pr[hit][m], cc[hit][m]].astype(int)
                            res[m] = L.ramp_colour(gi, idx)
                        res[rows[1][rh]] = SEAM
                    if face is not None and d == 'S':
                        fimg, ffront = face
                        fsel = np.abs(np.degrees(np.arctan2((x[hit] - cx) / rx, -(z[hit] - cz) / rz))) <= ffront
                        fc = fimg[pr[hit], cc[hit]]
                        res[fsel] = fc[fsel]
                    out[hit] = res; todo &= ~hit
                if not (todo & sel).any(): break
        if top is not None:
            up = n[:, 1] > 0.72
            if up.any(): out[up] = lit(*top)(r[up], x[up], z[up], n[up])
        return out
    return paint

def lit(ramp, base, extra=None, normal=None):
    """A plain material from a ramp, shaded by the 3D light (index base at the middle band)."""
    R = np.array(ramp)
    def paint(r, x, z, n):
        if normal is not None: n = normal(r, x, z)
        i = base + band(n) - 1
        if extra is not None: i = extra(r, x, z, i)
        out = R[np.clip(i, 0, len(R) - 1)].copy(); out[i <= -50] = SEAM
        return out
    return paint

def limb_space(world, A, B, A0, B0):
    """The space of a limb segment that has moved from A0->B0 (rest) to A->B (now): each block
    is looked up where it was at rest (along the limb, and turned with it)."""
    A, B, A0, B0 = (np.asarray(v, float) for v in (A, B, A0, B0))
    u = B - A; L = np.linalg.norm(u); u /= L
    u0 = B0 - A0; L0 = np.linalg.norm(u0); u0 /= L0
    v = np.cross(u, u0); s = np.linalg.norm(v); c = u @ u0
    if s < 1e-9: Rm = np.eye(3)
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        Rm = np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)
    qx, qr, qz = world.x - A[0], world.r - A[1], world.z - A[2]
    t = qx * u[0] + qr * u[1] + qz * u[2]
    px_, pr_, pz_ = qx - t * u[0], qr - t * u[1], qz - t * u[2]
    t0 = t * (L0 / L)
    rx = A0[0] + t0 * u0[0] + Rm[0, 0] * px_ + Rm[0, 1] * pr_ + Rm[0, 2] * pz_
    rr = A0[1] + t0 * u0[1] + Rm[1, 0] * px_ + Rm[1, 1] * pr_ + Rm[1, 2] * pz_
    rz = A0[2] + t0 * u0[2] + Rm[2, 0] * px_ + Rm[2, 1] * pr_ + Rm[2, 2] * pz_
    return Space(rr.astype(np.float32), rx.astype(np.float32), rz.astype(np.float32))

# ---------- helmets ----------
def add_helmet(G, B, kind, L, hc):
    """A helmet of the given kind on the head (hc: row, x, z, radii); painted from its layer,
    relit, with designed extras (brim, horns, wings, crest, visor) in the layer's own ramps."""
    r, x, z = B.r, B.x, B.z
    cr, cx, cz, rr, rx, rz = hc
    def ell(c_r, c_x, c_z, a, b, c, p=2.2, pf=None, czf=None):
        pz = p if pf is None else np.where(z < c_z, pf, p)
        cc = c if czf is None else np.where(z < c_z, czf, c)
        return np.abs((r - c_r) / a) ** p + np.abs((x - c_x) / b) ** p + np.abs((z - c_z) / cc) ** pz <= 1
    rimf = lambda z: 17.6 + (z - (cz - rz)) * 0.17
    rim = rimf(z)
    centre = lambda rr_: (cx, cz, rx, rz)
    main = L.main()
    accents = sorted([g for g in range(len(L.ramps)) if g != main], key=lambda g: -L.weight[g])
    acc = accents[0] if accents else main
    paint = relit([L], centre, front=55, top=(L.ramps[main], L.base[main]))
    dome_p = dict(p=2.2, pf=3.0, czf=rz + 0.7)
    if kind == 'great helm':
        # a flat-topped cylinder over the whole head, the visor (eye slits) on the front
        cyl = (np.abs((x - cx) / (rx + 1.6)) ** 2.4 + np.abs((z - cz) / np.where(z < cz, rz + 1.0, rz + 1.8)) ** 2.4 <= 1)
        top = 9.5 + 1.2 * ((x - cx) / (rx + 1.6)) ** 2
        body = cyl & (r >= top) & (r < 31.0)
        G.add(body, paint, lit=True, space=B)
        return
    if kind == 'kettle':
        dome = ell(cr + 1.0, cx, cz, rr + 1.0, rx + 1.6, rz + 1.6, **dome_p) & (r <= 19.0)
        brim = (np.abs((x - cx) / (rx + 4.6)) ** 2 + np.abs((z - cz) / (rz + 4.6)) ** 2 <= 1) & \
               (np.abs(r - (18.6 + 0.08 * np.hypot(x - cx, z - cz))) <= 0.7)
        G.add(dome | brim, paint, lit=True, space=B)
        return
    # the rest share the nasal dome (a point only on the nasal)
    dome = ell(cr + 0.3, cx, cz, rr + 1.5, rx + 1.8, rz + 1.9, **dome_p) & (r <= rim)
    rimband = ell(cr + 0.3, cx, cz, rr + 1.9, rx + 2.3, rz + 2.4, p=2.2, pf=3.0, czf=rz + 1.1) & (r <= rim) & (r > rim - 1.7)
    parts = dome | rimband
    if kind == 'nasal':
        parts |= ((x - cx) ** 2 + (z - cz) ** 2 <= (0.8 + np.clip(r - 3, 0, 9) * 0.7) ** 2) & (r >= 3) & (r < 8.5)
        fz = cz - rz - 0.6
        parts |= (np.abs(x - cx) <= 1.0) & (r >= 17) & (r < 23.5) & (z >= fz - 0.9) & (z < fz + 1.5)
    if kind == 'crested':
        parts |= ((np.abs(x - cx) <= 2.6) & (r >= 15) & (r < 25) & (z < cz - rz + 2.5) &
                  ell(cr + 0.3, cx, cz, rr + 2.8, rx + 3.0, rz + 2.6))                        # cheek-and-brow guard
    G.add(parts, paint, lit=True, space=B)
    if kind == 'horned':
        # a horn out of each side, curving up and outward (the layer's horn colour)
        horn = np.zeros_like(parts)
        for s in (-1, 1):
            for k in range(26):
                t = k / 25
                hx = cx + s * (rx + 1.0 + 6.5 * t)
                hr = 14.5 - 9.0 * t ** 1.6
                hz = cz - 1.0 - 1.5 * t
                rad = 1.9 * (1 - t) + 0.35
                horn |= (x - hx) ** 2 + (r - hr) ** 2 + (z - hz) ** 2 <= rad * rad
        G.add(horn & ~parts, lit(L.ramps[acc], L.base[acc] + 1), lit=True, space=B)
    if kind == 'winged':
        # a wing on each side: five long feathers fanning up and outward, a little back
        wing = np.zeros_like(parts); top_ = L.ramps[main]
        for s_ in (-1, 1):
            for f_ in range(5):
                ang = math.radians(28 + 15 * f_)               # from near-outward to near-upright
                ln = 9.5 - 0.9 * f_
                for k in range(16):
                    t = k / 15
                    wx = cx + s_ * (rx + 1.4 + math.cos(ang) * ln * t)
                    wr = 15.0 - math.sin(ang) * ln * t
                    wz = cz + 0.5 + 1.8 * t
                    wid = 1.25 * (1 - 0.55 * t)
                    wing |= ((x - wx) ** 2 + (r - wr) ** 2 <= wid * wid) & (np.abs(z - wz) <= 0.55)
        lightest = sorted(top_, key=lambda c: -sum(c[:3]))[:3][::-1]
        def quill(r, x, z, i):
            i = i.copy(); i[(np.floor(np.hypot(x - cx, r - 15.0) * 0.9) % 2) == 0] -= 1; return i   # feather lines
        G.add(wing & ~parts, lit(lightest, 1, extra=quill), lit=True, space=B)
    if kind == 'crested':
        # a plume ridge from brow to nape (the layer's colour)
        ang = np.arctan2(z - cz, -(r - (cr + 0.3)))           # 0 straight up, + toward the back
        rad = np.hypot(r - (cr + 0.3), z - cz)
        crest = (np.abs(x - cx) <= 1.1) & (ang > -0.9) & (ang < 1.6) & (rad >= rr + 0.8) & (rad <= rr + 4.6 - 1.2 * np.abs(ang - 0.35))
        G.add(crest & ~parts, lit(L.ramps[acc], L.base[acc]), lit=True, space=B)

# ---------- shields ----------
def add_shield(G, SA, kind, L, steel):
    """Any shield from its front outline: a curved plate turned outward on the left arm, the
    painted face kept as drawn, a raised rim in the steel, a boss on round ones, wood behind."""
    sa = L.cover['S']
    dist = np.zeros(sa.shape, int); cur = sa.copy(); k = 0
    while cur.any():
        k += 1; dist[cur] = k
        pad = np.pad(cur, 1); cur = cur & pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:]
    ys, xs = np.nonzero(sa); xcen = (xs.min() + xs.max() + 1) / 2; hwid = (xs.max() + 1 - xs.min()) / 2
    rcen = (ys.min() + ys.max() + 1) / 2; hhei = (ys.max() + 1 - ys.min()) / 2
    pr, px = np.clip(SA.r.astype(int), 0, P - 1), np.clip(SA.x.astype(int), 0, P - 1)
    inside = (SA.r >= 0) & (SA.r < P)
    curve = 2.0 if kind in ('heater', 'kite', 'round') else 1.0 if kind == 'tower' else 1.4
    zc_of = lambda x: 18.6 + (x - 34) * math.tan(math.radians(22)) - curve * (1 - np.clip((x - xcen) / hwid, -1, 1) ** 2)
    zc = zc_of(SA.x)
    onrim = inside & sa[pr, px] & (dist[pr, px] <= 2)
    plate = inside & sa[pr, px] & (np.abs(SA.z - zc) <= 0.9)
    rimv = onrim & (SA.z >= zc - 1.7) & (SA.z <= zc + 1.5)
    front_img = filled(L.img['S'])
    def face(r, x, z, n):
        pr, px = np.clip(r.astype(int), 0, P - 1), np.clip(x.astype(int), 0, P - 1)
        front = front_img[pr, px].copy()
        wood = np.tile(np.array((96, 60, 30, 255)), (len(r), 1)); wood[(x % 3.2) < 0.55] = (70, 42, 20, 255)
        return np.where((z < zc_of(x))[:, None], front, wood)
    G.add(plate & ~onrim, face, space=SA)
    G.add(rimv, lit(steel, 1), lit=True, space=SA)
    if kind in ('round', 'buckler'):
        rb = 2.2 if kind == 'round' else 2.0
        boss = ((SA.x - xcen) ** 2 + (SA.r - rcen) ** 2 + ((SA.z - (zc_of(xcen) - 0.6)) * 1.3) ** 2 <= rb * rb) & (SA.z < zc)
        G.add(boss, lit(steel, 2), lit=True, space=SA)
    G.add(SA.col(rcen - 3, rcen + 3, xcen - 2.0, 23.6, 1.0, 1.4) & ~plate & ~rimv,
          lambda r, x, z, n: np.tile(np.array((74, 44, 24, 255)), (len(r), 1)), space=SA)

# ---------- weapons ----------
def weapon_ramps(L):
    """The weapon layer's head (far from the hand), haft (middle) and grip (at the hand) ramps."""
    a = L.gid['S']; ys, xs = np.nonzero(a >= 0)
    if not len(ys): return (0, 0, 0)
    dist = np.hypot(xs - 20, ys - 50); m = dist.max()
    mode = lambda sel: int(np.bincount(a[ys[sel], xs[sel]]).argmax()) if sel.any() else L.main()
    return mode(dist > 0.62 * m), mode((dist > 0.22 * m) & (dist < 0.5 * m)), mode(dist < 0.2 * m)

WEAPONS = {   # blade/haft from the grip centre along the weapon, in sprite pixels
    'dagger': dict(kind='blade', L=13.0, hw=1.4, guard=3.0, grip=(-3.0, 2.2)),
    'arming sword': dict(kind='blade', L=24.0, hw=1.6, guard=4.2, grip=(-4.0, 2.6)),
    'longsword': dict(kind='blade', L=31.0, hw=1.9, guard=4.8, grip=(-5.2, 2.8)),
    'scimitar': dict(kind='blade', L=25.0, hw=1.8, guard=3.6, grip=(-4.0, 2.6), curve=0.022),
    'hand axe': dict(kind='axe', haft=(-4.5, 18.0), head=(12.5, 18.0), reach=5.5, double=False),
    'battle axe': dict(kind='axe', haft=(-6.0, 23.0), head=(15.0, 23.0), reach=7.0, double=True),
    'warhammer': dict(kind='hammer', haft=(-6.0, 21.0), head=20.0),
    'mace': dict(kind='mace', haft=(-4.5, 15.0), head=17.0),
    'morning star': dict(kind='star', haft=(-4.5, 15.0), head=18.0),
    'spear': dict(kind='spear', haft=(-17.0, 31.0), head=(31.0, 39.0)),
    'halberd': dict(kind='halberd', haft=(-17.0, 31.0), head=(31.0, 38.0)),
    'pickaxe': dict(kind='pick', haft=(-4.5, 19.0), head=19.0),
}

def add_weapon(G, world, kind, L, hand, d, steel, broadside=False):
    spec = WEAPONS[kind]
    w = np.cross(np.array([1.0, 0, 0]), d); w = w - (w @ d) * d; w /= np.linalg.norm(w)    # edge / head side
    if broadside:      # the head reaches outward (its flat face to the front, as the sprites draw it)
        w = np.array([-1.0, 0, 0]) - d[0] * d; w /= np.linalg.norm(w)
    tt = np.cross(d, w)
    def local(xx, rr, zz):
        q = np.stack([xx - hand[0], rr - hand[1], zz - hand[2]], -1).astype(np.float64)
        return q @ d, q @ w, q @ tt
    a, b, c = local(world.x, world.r, world.z)
    head_g, haft_g, grip_g = weapon_ramps(L)
    HEAD, HAFT, GRIP = L.ramps[head_g], L.ramps[haft_g], L.ramps[grip_g]
    hb, fb, gb = L.base[head_g], L.base[haft_g], L.base[grip_g]
    def to_model(v): return np.stack([v[..., 0], -v[..., 1], v[..., 2]], -1)
    def wood(R, base_):
        def extra(r, x, z, i):
            a, b, c = local(x, r, z); i = i.copy(); i[(np.floor(a * 0.8) % 3) == 0] -= 1; return i   # grain
        return lit(R, base_, extra=extra)
    def wraps(R, base_):
        def extra(r, x, z, i):
            a, b, c = local(x, r, z); i = i.copy(); i[(np.floor(a * 1.2) % 2) == 0] -= 1; return i
        return lit(R, base_, extra=extra)
    k = spec['kind']
    if k == 'blade':
        Lb, hw0 = spec['L'], spec['hw']; g0, g1 = spec['grip']
        bend = spec.get('curve', 0.0)
        bb = b + bend * np.clip(a - g1, 0, None) ** 2          # a scimitar's blade curves back
        hw = np.where(a < Lb - 5, hw0 + (0.35 if bend else 0) * np.clip((a - g1) / (Lb - g1), 0, 1), hw0 * np.clip((Lb - a) / 5, 0.12, 1))
        blade = (a >= g1 + 1.4) & (a <= Lb) & (np.abs(bb) <= hw) & (np.abs(c) <= 0.8 * (1 - np.abs(bb) / hw) + 0.3)
        guard = (a >= g1) & (a < g1 + 1.4) & (np.abs(b) <= spec['guard']) & (np.abs(c) <= 1.1)
        grip = (a >= g0) & (a < g1) & (b * b + c * c <= 0.95 ** 2)
        pommel = (a - (g0 - 0.9)) ** 2 + b * b + c * c <= (1.2 + 0.1 * spec['guard']) ** 2
        def bn(r, x, z):
            a, b, c = local(x, r, z); bb = b + bend * np.clip(a - g1, 0, None) ** 2
            hw = np.where(a < Lb - 5, hw0, hw0 * np.clip((Lb - a) / 5, 0.12, 1))
            v = np.sign(c + 1e-6)[:, None] * tt[None] + (np.sign(bb + 1e-6) * 0.8 / hw)[:, None] * w[None]
            v = to_model(v); return v / np.linalg.norm(v, axis=1, keepdims=True)
        def edges(r, x, z, i):
            a, b, c = local(x, r, z); bb = b + bend * np.clip(a - g1, 0, None) ** 2
            hw = np.where(a < Lb - 5, hw0, hw0 * np.clip((Lb - a) / 5, 0.12, 1))
            i = i.copy(); i[np.abs(bb) > hw - 0.45] = 99; i[np.abs(bb) < 0.3] -= 1; return i
        G.add(blade, lit(HEAD, hb, extra=edges, normal=bn), lit=True, space=world)
        G.add(guard, lit(steel, 0), lit=True, space=world)
        G.add(grip, wraps(GRIP, gb), lit=True, space=world)
        G.add(pommel, lit(steel, 1), lit=True, space=world)
        return
    h0, h1 = spec['haft']
    haft = (a >= h0) & (a <= h1) & (b * b + c * c <= 0.95 ** 2)
    G.add(haft, wood(HAFT, fb), lit=True, space=world)
    G.add((a >= h0 - 0.8) & (a < h0) & (b * b + c * c <= 1.2 ** 2), lit(steel, 1), lit=True, space=world)   # butt cap
    head = np.zeros_like(haft)
    if k == 'axe':
        a0, a1 = spec['head']; reach = spec['reach']; mid = (a0 + a1) / 2
        sides = (1, -1) if spec['double'] else (1,)
        for s in sides:
            bs = s * b
            half = (a1 - a0) / 2 * (0.45 + 0.75 * np.clip((bs - 0.6) / reach, 0, 1) ** 1.3)   # flares to a wide edge
            head |= (bs >= 0.6) & (bs <= reach + 0.6 - 0.12 * ((a - mid) / max(half.max(), 1)) ** 2 * reach) & (np.abs(a - mid) <= half) & \
                    (np.abs(c) <= 0.95 - 0.55 * np.clip((bs - 0.6) / reach, 0, 1))
        if not spec['double']:
            head |= (b <= -0.6) & (b >= -2.2) & (np.abs(a - mid) <= 1.3) & (np.abs(c) <= 1.0)                     # the poll
        head |= (np.abs(a - mid) <= (a1 - a0) / 2 * 0.55) & (b * b + c * c <= 1.35 ** 2)                          # the eye round the haft
        def edge(r, x, z, i):
            a, b, c = local(x, r, z); i = i.copy(); i[np.abs(b) > reach - 0.4] = 99; return i
        G.add(head, lit(HEAD, hb, extra=edge), lit=True, space=world)
    elif k == 'hammer':
        h = spec['head']
        head = (np.abs(a - h) <= 2.0) & (b >= -3.6) & (b <= 3.6) & (np.abs(c) <= 1.9)
        head |= (b < -3.6) & (b > -6.5) & (np.abs(a - h) <= 1.5 * (1 - (-b - 3.6) / 2.9) + 0.2) & (np.abs(c) <= 1.4 * (1 - (-b - 3.6) / 2.9) + 0.2)   # back spike
        def studs(r, x, z, i):
            a, b, c = local(x, r, z); i = i.copy(); i[(b > 3.2) & (np.abs(a - h) < 1.2) & (np.abs(c) < 1.2) & ((np.floor(a * 1.4 + 9) + np.floor(c * 1.4 + 9)) % 2 == 0)] -= 1; return i
        G.add(head, lit(HEAD, hb, extra=studs), lit=True, space=world)
    elif k == 'mace':
        h = spec['head']
        rad = np.hypot(b, c); ang = np.arctan2(c, b)
        core = (a - h) ** 2 / 3.2 ** 2 + rad ** 2 / 2.0 ** 2 <= 1
        flanges = (np.abs(a - h) <= 2.8 - 0.5 * np.clip(rad - 2.0, 0, 3)) & (rad <= 3.8) & (np.abs(((ang / (2 * math.pi) * 6) % 1) - 0.5) > 0.36)
        G.add(core | flanges, lit(HEAD, hb), lit=True, space=world)
    elif k == 'star':
        h = spec['head']
        ball = (a - h) ** 2 + b * b + c * c <= 2.8 ** 2
        spikes = np.zeros_like(ball)
        dirs = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)] + [(sx, sy, sz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        for v in dirs:
            v = np.array(v, float); v /= np.linalg.norm(v)
            q = np.stack([a - h, b, c], -1); t = q @ v
            perp = np.linalg.norm(q - t[..., None] * v, axis=-1)
            spikes |= (t > 2.2) & (t < 4.8) & (perp <= 0.9 * (4.8 - t) / 2.6)
        G.add(ball | spikes, lit(HEAD, hb), lit=True, space=world)
    elif k in ('spear', 'halberd'):
        a0, a1 = spec['head']
        u = np.clip((a - a0) / (a1 - a0), 0, 1)
        leaf = (a >= a0) & (a <= a1) & (np.abs(b) <= 1.9 * np.sin(math.pi * np.clip(u * 1.15, 0, 1)) + 0.25) & (np.abs(c) <= 0.6)
        collar = (a >= a0 - 1.6) & (a < a0) & (b * b + c * c <= 1.25 ** 2)
        head = leaf | collar
        if k == 'halberd':
            ax_ = (b >= 0.6) & (b <= 6.2) & (np.abs(a - (a0 - 4.5)) <= 2.0 + 1.6 * np.clip((b - 0.6) / 5.6, 0, 1)) & (np.abs(c) <= 0.7)
            hook = (b <= -0.6) & (b >= -3.8) & (np.abs(a - (a0 - 4.0) - 0.45 * (-b)) <= 0.8) & (np.abs(c) <= 0.7)
            head |= ax_ | hook
        G.add(head, lit(HEAD, hb), lit=True, space=world)
    elif k == 'pick':
        h = spec['head']
        bs = np.abs(b)
        arc = h - 0.05 * b ** 2                                  # the pick's points droop
        head = (bs <= 8.5) & (np.abs(a - arc) <= 1.2 * (1 - bs / 9.5) + 0.3) & (np.abs(c) <= 0.9 * (1 - bs / 10) + 0.25)
        G.add(head, lit(HEAD, hb), lit=True, space=world)

# ---------- the unit ----------
def build(lo=None, rig=None, sub=2, f=0, zoff=12):
    lo = lo or KNIGHT; rig = rig or Rig()
    BODY = ('Races64/Human.dmi', '')
    HAIR = (GEAR + 'old-Hair.dmi', lo.hair) if lo.hair else None
    srcs = [BODY] + [s for s in (lo.legs, lo.chest, HAIR) if s] + (list(lo.arms) if lo.arms else []) + \
           [s for s in (lo.helmet, lo.shield, lo.weapon) if s]
    full = compose64.unit(srcs, f)
    aS, aN, aE, aW = (arr(full[d])[:, :, 3] > 0 for d in 'SNEW')
    sN = carve.best_shift(aS, aN[:, ::-1]); sW = carve.best_shift(aE[:, ::-1], aW)
    Ly = lambda s: Layer(s, sN, sW, f) if s else None
    body, legs, chest = Ly(BODY), Ly(lo.legs), Ly(lo.chest)
    armL, armR = (Ly(lo.arms[0]), Ly(lo.arms[1])) if lo.arms else (None, None)
    helm, shield, weapon = Ly(lo.helmet), Ly(lo.shield), Ly(lo.weapon)
    SMOOTH = ('plate', 'banded')
    for L, slot in ((legs, 'legs'), (chest, 'chest'), (armL, 'arms'), (armR, 'arms')):
        if L: L.set_smooth(lo.kind(slot) in SMOOTH)
    if helm: helm.set_smooth(True)
    body.set_smooth(True)
    hairL = Ly(HAIR)
    face_img = skin_face(filled(deoutline(arr(compose64.unit([BODY], f)['S']))))
    STEEL = [(66, 70, 78, 255), (104, 109, 118, 255), (148, 154, 163, 255), (206, 212, 220, 255)]
    for L in (helm, chest, legs, shield):          # the tier's own metal if it has one
        if L: STEEL = L.ramps[L.main()]; break
    worn = [l for l in (chest, armR, armL, legs) if l]
    braw = arr(compose64.unit([BODY] + [s_ for s_ in (lo.legs, lo.chest) if s_] + (list(lo.arms) if lo.arms else []), f)['S'])
    smooth = lambda slot: lo.kind(slot) in SMOOTH
    prow = lambda slot, cols: plate_rows(braw, cols) if smooth(slot) else None
    def cover(*first):
        """The part's own layers first, then any other worn gear (a layer may leave a hole where
        another is drawn over it), bare skin last."""
        out = [l for l in first if l and l is not body]
        return out + [l for l in worn if l not in out] + [body]
    torso_c = cover(chest); legs_c = cover(chest if lo.kind('chest') == 'robe' else None, legs)
    G = Grid(sub); G.z = G.z - zoff; G.center = (32.0 * sub, (CZ + zoff) * sub)
    world = Space(G.r, G.x, G.z); B = world.lifted(rig.rise); cz = CZ

    # legs
    for cx, (ang, lift) in zip((25.5, 38.5), rig.legs):
        S_ = B.lifted(lift).swung((cx, HIP_ROW, cz), ang)
        thigh = S_.col(53, 57.6, cx, cz, 5.6, 6.2, 2.4)
        knee = S_.col(57.4, 59.6, cx, cz, 5.0, 5.5, 2.4) | S_.ell(58.2, cx, cz - 4.9, 1.6, 2.7, 1.7, 2.2)
        shin = S_.col(59.4, 61.2, cx, cz + 0.2, 4.6, 5.0, 2.4)
        toe_top = 61.0 + np.clip((cz - 2.0 - S_.z) * 0.38, 0, 2.2)
        boot = (np.abs((S_.x - cx) / 5.0) ** 2.4 + np.abs((S_.z - (cz - 2.4)) / 7.8) ** 2.2 <= 1) & (S_.r >= toe_top) & (S_.r < 64)
        cuff = S_.col(60.4, 61.6, cx, cz + 0.2, 5.3, 5.7, 2.4)
        G.add(thigh | knee | shin | boot | cuff, relit(legs_c, lambda rr, cx=cx: (cx, cz, 5.6, 6.2), front=50, sides='E' if cx < 32 else 'W', rows=prow('legs', (int(cx) - 3, int(cx) + 3))), lit=True, space=S_)
    G.add(B.col(49, 56, 32, cz, 11.2, 8.4, 2.6), relit(cover(chest, legs), lambda rr: (32, cz, 11.2, 8.4), front=50, rows=prow('chest', (27, 37))), lit=True, space=B)
    rx_t = np.where(B.r < 35, 6 + 4 * np.clip((B.r - 31) / 3, 0, 1), 10.0)
    torso = (np.abs((B.x - 32) / rx_t) ** 2.6 + np.abs((B.z - cz) / 8.6) ** 2.6 <= 1) & (B.r >= 32) & (B.r < 53)
    G.add(torso, relit(torso_c, lambda rr: (32, cz, 10, 8.6), front=50, rows=prow('chest', (27, 37))), lit=True, space=B)
    if lo.kind('chest') == 'robe':
        # the robe's skirt, flaring a little, down over the legs
        rad = 10.6 + np.clip(B.r - 50, 0, None) * 0.22
        skirt = (np.abs((B.x - 32) / rad) ** 2.4 + np.abs((B.z - cz) / (rad - 1.6)) ** 2.4 <= 1) & (B.r >= 50) & (B.r < 61.5)
        G.add(skirt, relit(cover(chest, legs), lambda rr: (32, cz, 11.5, 9.0), front=50), lit=True, space=B)

    # shield arm (and shield) about the left shoulder
    SA = B.swung(SHOULDER_L, rig.shield)
    arm_l = SA.col(33, 48.5, 44.2, cz, 4.0, 4.3, 2.2) | SA.ell(35, 44.2, cz, 4.5, 4.8, 4.8) | SA.col(48.5, 52, 44.2, cz - 0.5, 3.6, 3.9, 2.4)
    G.add(arm_l, relit(cover(armL, chest), lambda rr: (44.2, cz, 4.0, 4.3), front=55, sides='', rows=prow('arms', (41, 48))), lit=True, space=SA)
    if shield: add_shield(G, SA, lo.kind('shield'), shield, STEEL)

    # sword arm from its keyframe, painted where it hangs at rest
    elbow, fist_p, dvec = rig.sword
    sh = SHOULDER_R
    elbow = swing_point(np.array(elbow, float), sh, rig.sword_swing); fist_p = swing_point(np.array(fist_p, float), sh, rig.sword_swing)
    d = np.array(dvec, float); d /= np.linalg.norm(d); d = swing_point(sh + d, sh, rig.sword_swing) - sh
    lift = np.array([0, -rig.rise, 0])
    elbow_w, fist_w, sh_w = elbow + lift, fist_p + lift, sh + lift
    E0, W0 = np.array([19.8, 42.5, cz]), np.array([19.8, 47.5, cz - 0.2])   # rest elbow and wrist: the fist lands on the drawn hand
    US = limb_space(world, sh_w, elbow_w, sh, E0); FS = limb_space(world, elbow_w, fist_w, E0, W0)
    upper = world.capsule(sh_w, elbow_w, 4.0) | world.ell(sh_w[1], sh_w[0], sh_w[2], 4.5, 4.8, 4.8) | world.ell(elbow_w[1], elbow_w[0], elbow_w[2], 3.6, 3.6, 3.6)
    forearm = world.capsule(elbow_w, fist_w, 3.3)
    fx, fr, fz = fist_w
    fist = (np.abs((world.x - fx) / 2.7) ** 2.6 + np.abs((world.r - fr) / 2.7) ** 2.6 + np.abs((world.z - fz) / 3.0) ** 2.6) <= 1
    armc = lambda rr: (19.8, cz, 4.0, 4.3)
    # arms read only the front and back pictures: the side pictures draw the chest's side
    # panel (a tabard, a robe) across where the arm is
    G.add(upper, relit(cover(armR, chest), armc, front=55, sides='', rows=prow('arms', (16, 23))), lit=True, space=US)
    G.add(forearm | fist, relit(cover(armR, chest), armc, front=55, sides='', rows=prow('arms', (16, 23))), lit=True, space=FS)
    G.add(B.col(30, 35, 32, cz, 4.5, 4.5), relit(cover(chest), lambda rr: (32, cz, 4.5, 4.5)), lit=True, space=B)

    # head with the original face, hair, helmet
    hc = (22.5, 32.0, 31.5, 11.2, 11.0, 11.0)
    head = B.ell(*hc, p=2.2, pfront=3.2)
    G.add(head, relit([body], lambda rr: (hc[1], hc[2], hc[4], hc[5]), front=78, back=60, face=(face_img, 78)), lit=True, space=B)
    if hairL:
        HAIRC = sorted(hairL.ramps[hairL.main()], key=lambda c: sum(c[:3]))
        cr, cx0, cz0, rr_, rx_, rz_ = hc; t = 1.7
        r, x, z = B.r, B.x, B.z
        th = np.arctan2(x - cx0, z - cz0)
        flare = np.clip(r - cr, 0, None) * 0.09
        rad_out = np.abs((x - cx0) / (rx_ + t + flare)) ** 2.2 + np.abs((z - cz0) / (rz_ + t + flare)) ** 2.2
        shell = (np.abs((r - cr) / (rr_ + t)) ** 2.2 + rad_out <= 1) | ((r > cr) & (rad_out <= 1))
        ends_of = lambda th: 34.5 - 3.0 * np.clip((np.abs(th) - 1.1) / 0.6, 0, 1) + 1.1 * np.sin(th * 7 + 0.6) + 0.7 * np.sin(th * 13)
        back_hair = shell & ~head & (r >= 15) & (z >= cz0 - 1.5) & (r < ends_of(th)) & ~((r > 31) & (z < cz0 + 0.5))
        locks = np.zeros_like(head)
        top = 18.4 if helm else 13.0
        for s in (-1, 1):
            lx = cx0 + s * (rx_ - 0.4); wav = 0.5 * np.sin((z - cz0) * 1.3 + s)
            locks |= (np.abs(x - lx) <= 1.9) & (z >= cz0 - 6.2) & (z < cz0 + 1.0) & (r >= top + (z - (hc[2] - hc[5])) * 0.17) & (r < 30.5 + wav) & ~head
        cap = shell & ~head & (r < 15) if not helm else np.zeros_like(head)     # bare-headed: hair over the top too
        HR = np.array(HAIRC)
        def hair_paint(r, x, z, n):
            th = np.arctan2(x - cx0, z - cz0)
            i = len(HR) // 2 + band(n) - 1 + np.round(1.2 * np.sin(th * 15 + 0.4 * np.sin(r * 0.7))).astype(int)
            i = i - ((r > ends_of(th) - 1.6) & (z >= cz0 - 1.5)); i = i - ((r > 28.5) & (z < cz0 + 1.0))
            return HR[np.clip(i, 0, len(HR) - 1)].copy()
        G.add(back_hair | locks | cap, hair_paint, lit=True, space=B)
        if helm:
            hk = lo.kind('helmet')
            edge = {'great helm': 31.0, 'kettle': 19.6}.get(hk, None)
            rim = 17.6 + (B.z - (hc[2] - hc[5])) * 0.17 if edge is None else edge
            G.clear((G.owner == len(G.parts) - 1) & B.ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 3.0, hc[4] + 3.4, hc[5] + 3.4, p=2.2) & (B.r <= rim))
    if helm: add_helmet(G, B, lo.kind('helmet'), helm, hc)

    if weapon: add_weapon(G, world, lo.kind('weapon'), weapon, fist_w, d, STEEL)
    G.paint()
    return G, full
