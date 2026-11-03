# The 3D knight, rigged (after build3d5.py, same look, on-guard pose). Parts that move are
# built in their own space: a leg turns about its hip, the shield arm (with the shield) about
# its shoulder, the whole body rises and falls; a part's paint and plate lines are read in its
# own space, so they move with it. The sword arm is placed by keyframes (elbow, fist, blade
# direction), and the blade's cutting edge always leads the cut.
#   build_knight(rig) with rig = Rig(...) for one frame; walk_rig(phase), attack_rig(t) make them.
# Sizes are in sprite pixels: x across the front picture, row down it, z front->back.
import numpy as np, math
import compose64, carve
from build3d2 import P, arr, Views, by_sector
from build3d3 import Grid as _Grid, sprite, ramp_of, plate_rows, SEAM
from build3d4 import band, steel, skin_face

CZ = 31.5
SHOULDER_R, SHOULDER_L = np.array([19.8, 35.5, CZ]), np.array([44.2, 35.5, CZ])
HIP_ROW = 53.0

class Space:
    """Coordinates (sprite pixels) at which a part's rest shape is looked up."""
    def __init__(self, r, x, z): self.r, self.x, self.z = r, x, z
    def col(self, r0, r1, cx, cz, rx, rz, p=2.0):
        r, x, z = self.r, self.x, self.z
        return (np.abs((x - cx) / rx) ** p + np.abs((z - cz) / rz) ** p <= 1) & (r >= r0) & (r < r1)
    def ell(self, cr, cx, cz, rr, rx, rz, p=2.0, pfront=None, rzf=None):
        r, x, z = self.r, self.x, self.z
        pz = p if pfront is None else np.where(z < cz, pfront, p)
        rzz = rz if rzf is None else np.where(z < cz, rzf, rz)
        return np.abs((r - cr) / rr) ** p + np.abs((x - cx) / rx) ** p + np.abs((z - cz) / rzz) ** pz <= 1
    def capsule(self, p0, p1, rad):
        r, x, z = self.r, self.x, self.z
        p0, p1 = np.array(p0, float), np.array(p1, float); dv = p1 - p0; L2 = dv @ dv
        tq = np.clip(((x - p0[0]) * dv[0] + (r - p0[1]) * dv[1] + (z - p0[2]) * dv[2]) / L2, 0, 1)
        return (x - p0[0] - tq * dv[0]) ** 2 + (r - p0[1] - tq * dv[1]) ** 2 + (z - p0[2] - tq * dv[2]) ** 2 <= rad * rad
    def lifted(self, rise):
        """The space of something raised by rise pixels."""
        return Space(self.r + rise, self.x, self.z)
    def swung(self, pivot, ang):
        """The space of something turned forward by ang (radians) about a joint at pivot (x, row,
        z) on a left-right axis: below the joint, forward moves it toward the front (-z)."""
        c, s = math.cos(ang), math.sin(ang)
        dr, dz = self.r - pivot[1], self.z - pivot[2]
        return Space(pivot[1] + dr * c - dz * s, self.x, pivot[2] + dr * s + dz * c)

def swing_point(p, pivot, ang):
    """Where point p (x, row, z) goes when turned forward by ang about pivot (as Space.swung)."""
    c, s = math.cos(ang), math.sin(ang)
    dr, dz = p[1] - pivot[1], p[2] - pivot[2]
    return np.array([p[0], pivot[1] + dr * c + dz * s, pivot[2] - dr * s + dz * c])

class Grid(_Grid):
    """build3d3's Grid, with each part painted in its own space."""
    def __init__(self, sub=2):
        super().__init__(sub); self.spaces = [None]
    def add(self, mask, painter, lit=False, space=None):
        super().add(mask, painter, lit); self.spaces.append(space)
    def paint(self):
        from build3d3 import normals
        s = self.solid(); pad = np.pad(s, 1)
        inner = pad[:-2, 1:-1, 1:-1] & pad[2:, 1:-1, 1:-1] & pad[1:-1, :-2, 1:-1] & pad[1:-1, 2:, 1:-1] & pad[1:-1, 1:-1, :-2] & pad[1:-1, 1:-1, 2:]
        surf = s & ~inner
        self.sn = normals(s)
        self.col = np.zeros(s.shape + (4,), np.int32); self.col[s] = (90, 90, 90, 255)
        self.lit = np.zeros(s.shape, bool)
        for i in range(1, len(self.parts)):
            m = surf & (self.owner == i)
            if not m.any(): continue
            idx = np.nonzero(m); sp = self.spaces[i]
            self.col[idx] = self.parts[i](sp.r[idx], sp.x[idx], sp.z[idx], self.sn[idx])
            self.lit[idx] = self.litparts[i]
        self.part = self.owner

class Rig:
    """One frame's pose. rise: body up (px); legs: (left, right) forward swing (radians) and
    lift (px); shield: shield-arm swing; sword: (elbow, fist, blade direction) in x, row, z."""
    GUARD = ((15.0, 43.5, 26.0), (17.2, 38.5, 19.0), (-0.27, -0.95, 0.12))   # upright beside the head, leaning out a little so a head clears the helmet
    def __init__(self, rise=0.0, legs=((0, 0), (0, 0)), shield=0.0, sword=None, sword_swing=0.0):
        self.rise, self.legs, self.shield = rise, legs, shield
        self.sword = sword or Rig.GUARD; self.sword_swing = sword_swing

LEG = 64.0 - HIP_ROW
def walk_rig(phase, stride=0.52):
    """A walk cycle (phase 0..1, in place). Legs swing opposite each other; the body is lowest
    with the legs apart so the feet stay on the ground; the swinging leg lifts as it passes; the
    shield arm swings with the other leg; the sword stays on guard, moving a little."""
    s = math.sin(2 * math.pi * phase); c = math.cos(2 * math.pi * phase)
    aL, aR = stride * s, -stride * s
    rise = -LEG * (1 - math.cos(aL)) + 0.5 * (1 - abs(s))
    liftL, liftR = 2.4 * max(0.0, c) ** 2, 2.4 * max(0.0, -c) ** 2
    return Rig(rise, ((aL, liftL), (aR, liftR)), shield=0.35 * aR, sword_swing=0.12 * aL)

# The cut: on guard -> wound up over the right shoulder -> down and forward -> across to the
# left, low -> back on guard. Keys: (time 0..1, elbow, fist, blade direction).
ATTACK_KEYS = [
    (0.00, *Rig.GUARD),
    (0.30, (12.0, 33.0, 29.0), (16.5, 24.5, 27.0), (-0.15, -0.75, 0.64)),
    (0.48, (15.0, 38.0, 22.0), (19.5, 36.0, 16.0), (-0.05, -0.42, -0.90)),
    (0.62, (19.5, 41.0, 24.0), (25.5, 46.5, 16.0), (0.45, 0.35, -0.82)),
    (0.72, (19.5, 41.0, 24.0), (25.5, 46.5, 16.0), (0.45, 0.35, -0.82)),
    (1.00, *Rig.GUARD),
]
def attack_rig(t):
    for (t0, e0, f0, d0), (t1, e1, f1, d1) in zip(ATTACK_KEYS, ATTACK_KEYS[1:]):
        if t0 <= t <= t1:
            u = 0 if t1 == t0 else (t - t0) / (t1 - t0); u = u * u * (3 - 2 * u)
            lerp = lambda a, b: tuple(np.array(a) * (1 - u) + np.array(b) * u)
            d = np.array(lerp(d0, d1)); d /= np.linalg.norm(d)
            # the body dips into the cut and the shield arm braces
            dip = 0.8 * math.sin(math.pi * min(1, max(0, (t - 0.3) / 0.45)))
            return Rig(rise=-dip, shield=-0.12 * dip, sword=(lerp(e0, e1), lerp(f0, f1), tuple(d)))
    return Rig()

def build_knight(rig=None, sub=2, f=0, zoff=12):
    rig = rig or Rig()
    H = 'Gear64/Human/'
    BODY = ('Races64/Human.dmi', '')
    LEGS, CHEST = (H + 'iron.dmi', 'legs.plate.iron'), (H + 'iron.dmi', 'chest.plate.iron')
    ARML, ARMR = (H + 'iron.dmi', 'arms.plate.iron.L'), (H + 'iron.dmi', 'arms.plate.iron.R')
    HAIR = (H + 'old-Hair.dmi', 'HumanBrown')
    HELM = (H + 'iron.dmi', 'helmet.nasal.iron')
    SHIELD = (H + 'iron.dmi', 'shield.heater.iron')
    full = compose64.unit([BODY, LEGS, CHEST, HAIR, ARML, ARMR, HELM, SHIELD, (H + 'iron.dmi', 'weapon.longsword.iron')], f)
    aS, aN, aE, aW = (arr(full[d])[:, :, 3] > 0 for d in 'SNEW')
    sN = carve.best_shift(aS, aN[:, ::-1]); sW = carve.best_shift(aE[:, ::-1], aW)
    V = lambda *L: Views(list(L), sN, sW, f)
    body, hairv, helm, shield = V(BODY, LEGS, CHEST, ARML, ARMR), V(HAIR), V(HELM), V(SHIELD)
    face = V(BODY)
    face.img['S'] = skin_face(face.img['S'])
    STEEL = ramp_of(helm.raw['S'])
    HAIRC = np.array(ramp_of(hairv.raw['N'], lo=60))
    G = Grid(sub); G.z = G.z - zoff; G.center = (32.0 * sub, (CZ + zoff) * sub)
    world = Space(G.r, G.x, G.z)
    B = world.lifted(rig.rise)                          # everything rides on the body
    cz = CZ
    braw = body.raw['S']

    # --- legs, each turning about its hip (and lifted as it passes) ---
    for cx, (ang, lift) in zip((25.5, 38.5), rig.legs):
        S_ = B.lifted(lift).swung((cx, HIP_ROW, cz), ang)
        rows = plate_rows(braw, (int(cx) - 3, int(cx) + 3))
        thigh = S_.col(53, 57.6, cx, cz, 5.6, 6.2, 2.4)
        knee = S_.col(57.4, 59.6, cx, cz, 5.0, 5.5, 2.4) | S_.ell(58.2, cx, cz - 4.9, 1.6, 2.7, 1.7, 2.2)
        shin = S_.col(59.4, 61.2, cx, cz + 0.2, 4.6, 5.0, 2.4)
        toe_top = 61.0 + np.clip((cz - 2.0 - S_.z) * 0.38, 0, 2.2)
        boot = (np.abs((S_.x - cx) / 5.0) ** 2.4 + np.abs((S_.z - (cz - 2.4)) / 7.8) ** 2.2 <= 1) & (S_.r >= toe_top) & (S_.r < 64)
        cuff = S_.col(60.4, 61.6, cx, cz + 0.2, 5.3, 5.7, 2.4)
        def leg_extra(r, x, z, i):
            i = i.copy(); i[r >= 60.4] -= 1; i[r >= 63.3] = -100; i[(r >= 60.4) & (r < 61.0)] = -100
            return i
        G.add(thigh | knee | shin, steel(STEEL, rows), lit=True, space=S_)
        G.add(boot | cuff, steel(STEEL, extra=leg_extra), lit=True, space=S_)

    torso_rows = plate_rows(braw, (27, 37))
    G.add(B.col(49, 56, 32, cz, 11.2, 8.4, 2.6), steel(STEEL, torso_rows), lit=True, space=B)
    rx_t = np.where(B.r < 35, 6 + 4 * np.clip((B.r - 31) / 3, 0, 1), 10.0)
    torso = (np.abs((B.x - 32) / rx_t) ** 2.6 + np.abs((B.z - cz) / 8.6) ** 2.6 <= 1) & (B.r >= 32) & (B.r < 53)
    G.add(torso, steel(STEEL, torso_rows), lit=True, space=B)

    # --- shield arm and shield, turning together about the left shoulder ---
    SA = B.swung(SHOULDER_L, rig.shield)
    G.add(SA.col(33, 48.5, 44.2, cz, 4.0, 4.3, 2.2) | SA.ell(35, 44.2, cz, 4.5, 4.8, 4.8) | SA.col(48.5, 52, 44.2, cz - 0.5, 3.6, 3.9, 2.4),
          steel(STEEL, plate_rows(braw, (41, 48))), lit=True, space=SA)
    sa = shield.raw['S'][:, :, 3] > 0
    dist = np.zeros(sa.shape, int); cur = sa.copy(); k = 0
    while cur.any():
        k += 1; dist[cur] = k
        pad = np.pad(cur, 1); cur = cur & pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:]
    ys, xs = np.nonzero(sa); xcen = (xs.min() + xs.max() + 1) / 2; hwid = (xs.max() + 1 - xs.min()) / 2
    pr, px = np.clip(SA.r.astype(int), 0, P - 1), np.clip(SA.x.astype(int), 0, P - 1)
    inside = (SA.r >= 0) & (SA.r < P)
    zc_of = lambda x: 18.6 + (x - 34) * math.tan(math.radians(22)) - 2.0 * (1 - np.clip((x - xcen) / hwid, -1, 1) ** 2)
    zc = zc_of(SA.x)
    onrim = inside & sa[pr, px] & (dist[pr, px] <= 2)
    plate = inside & sa[pr, px] & (np.abs(SA.z - zc) <= 0.9)
    rimv = onrim & (SA.z >= zc - 1.7) & (SA.z <= zc + 1.5)
    def shield_face(r, x, z, n):
        pr, px = np.clip(r.astype(int), 0, P - 1), np.clip(x.astype(int), 0, P - 1)
        front = shield.lookup('S', pr, px)
        wood = np.tile(np.array((96, 60, 30, 255)), (len(r), 1)); wood[(x % 3.2) < 0.55] = (70, 42, 20, 255)
        return np.where((z < zc_of(x))[:, None], front, wood)
    G.add(plate & ~onrim, shield_face, space=SA)
    G.add(rimv, steel(STEEL), lit=True, space=SA)
    G.add(SA.col(38, 44, 41.8, 23.6, 1.0, 1.4) & ~plate & ~rimv, lambda r, x, z, n: np.tile(np.array((74, 44, 24, 255)), (len(r), 1)), space=SA)

    # --- sword arm from its keyframe (moved with the body, and swung a little when walking) ---
    elbow, fist_p, dvec = rig.sword
    sh = SHOULDER_R
    elbow = swing_point(np.array(elbow, float), sh, rig.sword_swing); fist_p = swing_point(np.array(fist_p, float), sh, rig.sword_swing)
    d = np.array(dvec, float); d /= np.linalg.norm(d)
    d = swing_point(sh + d, sh, rig.sword_swing) - sh
    lift = np.array([0, -rig.rise, 0])                  # keyframes are in body space; the world sees them raised
    elbow_w, fist_w, sh_w = elbow + lift, fist_p + lift, sh + lift
    upper = world.capsule(sh_w, elbow_w, 4.0) | world.ell(sh_w[1], sh_w[0], sh_w[2], 4.5, 4.8, 4.8) | world.ell(elbow_w[1], elbow_w[0], elbow_w[2], 3.6, 3.6, 3.6)
    forearm = world.capsule(elbow_w, fist_w, 3.3)
    def along(x, r, z, p0, p1):
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float); dv = p1 - p0
        return ((x - p0[0]) * dv[0] + (r - p0[1]) * dv[1] + (z - p0[2]) * dv[2]) / (dv @ dv)
    def arm_lines(r, x, z, i):
        # plate edges along the arm itself (it moves, so the sprite's rows no longer fit):
        # one across the upper arm, the elbow cop's rim, the wrist cuff
        i = i.copy()
        tu, tf = along(x, r, z, sh_w, elbow_w), along(x, r, z, elbow_w, fist_w)
        on_upper = (tu >= 0) & (tu <= 1) & ~((tf > 0) & (tf <= 1))
        i[on_upper & (np.abs(tu - 0.5) < 0.05)] = -100
        i[(tf > 0) & (tf <= 1) & ((np.abs(tf - 0.18) < 0.05) | (np.abs(tf - 0.72) < 0.05))] = -100
        return i
    G.add(upper | forearm, steel(STEEL, extra=arm_lines), lit=True, space=world)
    fx, fr, fz = fist_w
    fist = (np.abs((world.x - fx) / 2.7) ** 2.6 + np.abs((world.r - fr) / 2.7) ** 2.6 + np.abs((world.z - fz) / 3.0) ** 2.6) <= 1
    def fingers(r, x, z, i):
        i = np.maximum(i - 1, 1)                        # a darker gauntlet, but never a black lump
        i[(x < fx + 0.8) & (((r - fr + 2.7) % 1.8) < 0.5)] = -100   # three thin finger lines
        return i
    G.add(fist, steel(STEEL, extra=fingers), lit=True, space=world)
    G.add(B.col(30, 35, 32, cz, 4.5, 4.5), sprite(by_sector(face, lambda rr: (32, cz, 4.5, 4.5))), space=B)

    # --- head, hair, helmet: as build3d5, riding on the body ---
    hc = (22.5, 32.0, 31.5, 11.2, 11.0, 11.0)
    head = B.ell(*hc, p=2.2, pfront=3.2)
    G.add(head, sprite(by_sector(face, lambda rr: (hc[1], hc[2], hc[4], hc[5]), front=78, back=60)), space=B)
    cr, cx0, cz0, rr_, rx_, rz_ = hc; t = 1.7
    r, x, z = B.r, B.x, B.z
    th = np.arctan2(x - cx0, z - cz0)
    flare = np.clip(r - cr, 0, None) * 0.09
    rad_out = np.abs((x - cx0) / (rx_ + t + flare)) ** 2.2 + np.abs((z - cz0) / (rz_ + t + flare)) ** 2.2
    shell = (np.abs((r - cr) / (rr_ + t)) ** 2.2 + rad_out <= 1) | ((r > cr) & (rad_out <= 1))
    ends_of = lambda th: 34.5 - 3.0 * np.clip((np.abs(th) - 1.1) / 0.6, 0, 1) + 1.1 * np.sin(th * 7 + 0.6) + 0.7 * np.sin(th * 13)
    back_hair = shell & ~head & (r >= 15) & (z >= cz0 - 1.5) & (r < ends_of(th)) & ~((r > 31) & (z < cz0 + 0.5))
    locks = np.zeros_like(head)
    for s in (-1, 1):
        lx = cx0 + s * (rx_ - 0.4); wav = 0.5 * np.sin((z - cz0) * 1.3 + s)
        locks |= (np.abs(x - lx) <= 1.9) & (z >= cz0 - 6.2) & (z < cz0 + 1.0) & (r >= 18.4 + (z - (hc[2] - hc[5])) * 0.17) & (r < 30.5 + wav) & ~head
    def hair_paint(r, x, z, n):
        th = np.arctan2(x - cx0, z - cz0)
        i = band(n, len(HAIRC)) + np.round(1.2 * np.sin(th * 15 + 0.4 * np.sin(r * 0.7))).astype(int)
        i = i - ((r > ends_of(th) - 1.6) & (z >= cz0 - 1.5)); i = i - ((r > 28.5) & (z < cz0 + 1.0))
        return HAIRC[np.clip(i, 0, len(HAIRC) - 1)].copy()
    G.add(back_hair | locks, hair_paint, lit=True, space=B)
    rimf = lambda z: 17.6 + (z - (hc[2] - hc[5])) * 0.17
    rim = rimf(z)
    dome = B.ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 1.5, hc[4] + 1.8, hc[5] + 1.9, p=2.2, pfront=3.0, rzf=hc[5] + 0.7)
    rimband = B.ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 1.9, hc[4] + 2.3, hc[5] + 2.4, p=2.2, pfront=3.0, rzf=hc[5] + 1.1) & (r <= rim) & (r > rim - 1.7)
    tip = ((x - hc[1]) ** 2 + (z - hc[2]) ** 2 <= (0.8 + np.clip(r - 3, 0, 9) * 0.7) ** 2) & (r >= 3) & (r < 8.5)
    front_z = hc[2] - hc[5] - 0.6
    nasal = (np.abs(x - hc[1]) <= 1.0) & (r >= 17) & (r < 23.5) & (z >= front_z - 0.9) & (z < front_z + 1.5)
    G.clear((G.owner == len(G.parts) - 1) & B.ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 2.3, hc[4] + 2.6, hc[5] + 2.7, p=2.2) & (r <= rim))
    def helm_extra(r, x, z, i):
        i = i.copy(); rm = rimf(z); onr = (r > rm - 1.7) & (r <= rm); i[onr] -= 1
        ang = np.arctan2(x - hc[1], z - hc[2])
        i[onr & (np.abs(((ang * 11.5 / math.pi) % 1) - 0.5) < 0.13) & (np.abs(r - rm + 0.85) < 0.5)] = 99
        i[(np.abs(x - hc[1]) <= 1.0) & (r >= 17) & (z < hc[2] - hc[5] + 1)] += 1
        return i
    G.add((dome & (r <= rim)) | rimband | tip | nasal, steel(STEEL, extra=helm_extra), lit=True, space=B)

    # --- sword: grip through the fist, guard above, pommel below; bevelled blade, the cutting
    #     edge leading the cut (it faces where a forward cut moves the blade) ---
    hand = fist_w
    w = np.cross(np.array([1.0, 0, 0]), d); w = w - (w @ d) * d; w /= np.linalg.norm(w)
    tt = np.cross(d, w)
    L = 31.0
    def local(xx, rr, zz):
        q = np.stack([xx - hand[0], rr - hand[1], zz - hand[2]], -1).astype(np.float64)
        return q @ d, q @ w, q @ tt
    a, b, c = local(world.x, world.r, world.z)
    hw_of = lambda a: np.where(a < L - 5, 1.9, 1.9 * np.clip((L - a) / 5, 0.12, 1))
    hw = hw_of(a)
    blade = (a >= 4.2) & (a <= L) & (np.abs(b) <= hw) & (np.abs(c) <= 0.8 * (1 - np.abs(b) / hw) + 0.3)
    guard = (a >= 2.8) & (a < 4.2) & (np.abs(b) <= 4.8) & (np.abs(c) <= 1.1)
    grip = (a >= -5.2) & (a < 2.8) & (b * b + c * c <= 0.95 ** 2)
    pommel = (a + 6.1) ** 2 + b * b + c * c <= 1.5 ** 2
    def to_model(v): return np.stack([v[..., 0], -v[..., 1], v[..., 2]], -1)
    def blade_normal(r, x, z):
        a, b, c = local(x, r, z); hw = hw_of(a)
        v = np.sign(c + 1e-6)[:, None] * tt[None] + (np.sign(b + 1e-6) * 0.8 / hw)[:, None] * w[None]
        v = to_model(v); return v / np.linalg.norm(v, axis=1, keepdims=True)
    def blade_extra(r, x, z, i):
        a, b, c = local(x, r, z); hw = hw_of(a)
        i = i.copy(); i[np.abs(b) > hw - 0.45] = 99; i[np.abs(b) < 0.3] -= 1
        return i
    G.add(blade, steel(STEEL, extra=blade_extra, normal=blade_normal), lit=True, space=world)
    G.add(guard, steel(STEEL, extra=lambda r, x, z, i: i - 1), lit=True, space=world)
    def grip_paint(r, x, z, n):
        a, b, c = local(x, r, z)
        out = np.tile(np.array((110, 70, 40, 255)), (len(r), 1)); out[(np.floor(a * 1.2) % 2) == 0] = (74, 44, 24, 255)
        return out
    G.add(grip & ~fist, grip_paint, space=world)
    G.add(pommel, steel(STEEL), lit=True, space=world)
    G.paint()
    return G, full
