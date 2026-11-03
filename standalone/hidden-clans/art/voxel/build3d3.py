# Third pass of the 3D knight (after build3d2.py), from the user's notes:
#  - the sword sits in a gauntleted fist at the end of the arm (guard above it, pommel below);
#  - helmet and armour are one smooth steel, lit in the sprite's own steel shades by the 3D
#    light, instead of four pictures pasted round them; the armour keeps the sprite's plate
#    rows (collar, plate bands, belt, knee band, boots), read off the front picture;
#  - the long hair is rounded, flares a little, has strands and an uneven bottom edge.
# The face and the shield's painted front still come straight from the sprite.
# Sizes are in sprite pixels: x across the front picture, row down it, z front->back.
import numpy as np, math
import compose64, carve
from build3d2 import P, arr, Views, by_sector, flat

LIGHT = np.array([-0.72, 0.5, -0.48]); LIGHT /= np.linalg.norm(LIGHT)   # upper left front, as the sprites are lit
SEAM = (40, 42, 50, 255)

def normals(solid, sigma=1.3):
    rad = int(3 * sigma); k = np.exp(-0.5 * (np.arange(-rad, rad + 1) / sigma) ** 2); k /= k.sum()
    g = solid.astype(np.float32)
    for ax in range(3):
        acc = np.zeros_like(g); pad = [(0, 0)] * 3; pad[ax] = (rad, rad); gp = np.pad(g, pad)
        for i, kv in enumerate(k):
            sl = [slice(None)] * 3; sl[ax] = slice(i, i + g.shape[ax]); acc += kv * gp[tuple(sl)]
        g = acc
    gr, gx, gz = np.gradient(g)
    n = np.stack([-gx, gr, -gz], -1)          # x right, y up, z back; pointing out of the solid
    l = np.linalg.norm(n, axis=-1, keepdims=True); l[l == 0] = 1
    return n / l

class Grid:
    """Blocks, the part owning each, and per part a painter(r, x, z, n) -> colours. Parts
    painted with their own light (lit=True) are not shaded again by the renderer."""
    def __init__(self, sub=2):
        self.sub = sub; n = P * sub; self.n = n
        R, X, Z = np.meshgrid(*(np.arange(n, dtype=np.float32),) * 3, indexing='ij')
        self.r, self.x, self.z = (R + 0.5) / sub, (X + 0.5) / sub, (Z + 0.5) / sub
        self.owner = np.zeros((n, n, n), np.int16)
        self.parts = [None]; self.litparts = [False]
    def add(self, mask, painter, lit=False):
        self.parts.append(painter); self.litparts.append(lit); self.owner[mask] = len(self.parts) - 1
    def clear(self, mask): self.owner[mask] = 0
    def solid(self): return self.owner > 0
    def paint(self):
        s = self.solid(); pad = np.pad(s, 1)
        inner = pad[:-2, 1:-1, 1:-1] & pad[2:, 1:-1, 1:-1] & pad[1:-1, :-2, 1:-1] & pad[1:-1, 2:, 1:-1] & pad[1:-1, 1:-1, :-2] & pad[1:-1, 1:-1, 2:]
        surf = s & ~inner
        self.sn = normals(s)
        self.col = np.zeros(s.shape + (4,), np.int32); self.col[s] = (90, 90, 90, 255)
        self.lit = np.zeros(s.shape, bool)
        for i in range(1, len(self.parts)):
            m = surf & (self.owner == i)
            if not m.any(): continue
            idx = np.nonzero(m)
            self.col[idx] = self.parts[i](self.r[idx], self.x[idx], self.z[idx], self.sn[idx])
            self.lit[idx] = self.litparts[i]
        self.part = self.owner

def sprite(painter):
    """A by_sector painter (r, x, z) as a Grid painter (r, x, z, n)."""
    return lambda r, x, z, n: painter(r, x, z)

def ramp_of(img, lo=150):
    """The distinct colours of a picture (not its dark outline), darkest first."""
    a = img.reshape(-1, 4); a = a[(a[:, 3] > 0) & (a[:, :3].sum(1) >= lo)]
    cols, cnt = np.unique(a[:, :3], axis=0, return_counts=True)
    keep = cols[cnt >= 3] if (cnt >= 3).sum() >= 3 else cols
    return [tuple(c) + (255,) for c in sorted(keep.tolist(), key=lambda c: sum(c))]

def band(n, steps):
    """The sprite's flat light bands: index 0 (shade) .. steps-1 (lit) from the 3D light."""
    d = n @ LIGHT
    # mostly the middle shades, as the sprite: the brightest only where it faces the light
    cuts = np.linspace(-0.75, 0.85, steps - 1) if steps > 4 else np.array([-0.6, 0.4, 0.88])
    return np.searchsorted(cuts, d)

def plate_rows(raw, cols):
    """Per sprite row of a part's front picture: -1 where it is darker than the part's usual
    (0 otherwise), and whether the row is a seam (a dark line across it)."""
    tone = np.zeros(P); seam = np.zeros(P, bool); have = np.zeros(P, bool)
    for r in range(P):
        px = raw[r, cols[0]:cols[1]]; px = px[px[:, 3] > 0]
        if len(px) < 2: continue
        lum = px[:, :3].sum(1); have[r] = True
        seam[r] = (lum < 150).mean() >= 0.6
        tone[r] = np.median(lum[lum >= 150]) if (lum >= 150).any() else 0
    ok = have & ~seam
    mid = np.median(tone[ok]) if ok.any() else 0
    off = np.zeros(P, int)
    off[ok & (tone < mid - 60)] = -1
    return off, seam

def steel(ramp, rows=None, extra=None):
    """Smooth steel: the 3D light picks the shade from the sprite's ramp, the sprite's plate rows
    shift it, seams are drawn dark. extra(r, x, z, i) may change the index (rim, rivets...)."""
    R = np.array(ramp)
    def paint(r, x, z, n):
        i = band(n, len(R))
        pr = np.clip(r.astype(int), 0, P - 1)
        if rows is not None: i = i + rows[0][pr]
        if extra is not None: i = extra(r, x, z, i)
        out = R[np.clip(i, 0, len(R) - 1)].copy()
        out[i <= -50] = SEAM                               # lines an extra() asked for
        if rows is not None: out[rows[1][pr]] = SEAM
        return out
    return paint

def build_knight(sub=2, f=0):
    H = 'Gear64/Human/'
    BODY = ('Races64/Human.dmi', '')
    LEGS, CHEST = (H + 'iron.dmi', 'legs.plate.iron'), (H + 'iron.dmi', 'chest.plate.iron')
    ARML, ARMR = (H + 'iron.dmi', 'arms.plate.iron.L'), (H + 'iron.dmi', 'arms.plate.iron.R')
    HAIR = (H + 'old-Hair.dmi', 'HumanBrown')
    HELM = (H + 'iron.dmi', 'helmet.nasal.iron')
    SHIELD = (H + 'iron.dmi', 'shield.heater.iron')
    SWORD = (H + 'iron.dmi', 'weapon.longsword.iron')
    full = compose64.unit([BODY, LEGS, CHEST, HAIR, ARML, ARMR, HELM, SHIELD, SWORD], f)
    aS, aN, aE, aW = (arr(full[d])[:, :, 3] > 0 for d in 'SNEW')
    sN = carve.best_shift(aS, aN[:, ::-1]); sW = carve.best_shift(aE[:, ::-1], aW)
    V = lambda *L: Views(list(L), sN, sW, f)
    body, face, hairv, helm, shield = V(BODY, LEGS, CHEST, ARML, ARMR), V(BODY, HAIR), V(HAIR), V(HELM), V(SHIELD)
    bare = V(BODY)
    face.img['E'], face.img['W'] = bare.img['E'], bare.img['W']
    STEEL = ramp_of(helm.raw['S'])                      # the tier's steel, darkest first
    HAIRC = ramp_of(hairv.raw['N'], lo=60)
    G = Grid(sub); r, x, z = G.r, G.x, G.z

    def col(r0, r1, cx, cz, rx, rz, p=2.0):
        return (np.abs((x - cx) / rx) ** p + np.abs((z - cz) / rz) ** p <= 1) & (r >= r0) & (r < r1)
    def ell(cr, cx, cz, rr, rx, rz, p=2.0, pfront=None, rzf=None):
        pz = p if pfront is None else np.where(z < cz, pfront, p)
        rzz = rz if rzf is None else np.where(z < cz, rzf, rz)
        return np.abs((r - cr) / rr) ** p + np.abs((x - cx) / rx) ** p + np.abs((z - cz) / rzz) ** pz <= 1

    cz = 31.5
    braw = body.raw['S']
    # --- armoured body: smooth steel with the sprite's plate rows ---
    for cx in (25.5, 38.5):
        leg = col(53, 64, cx, cz, 5.6, 6.2, 2.4) | col(59, 64, cx, cz - 2.5, 5.4, 7.5, 2.6)
        G.add(leg, steel(STEEL, plate_rows(braw, (int(cx) - 3, int(cx) + 3))), lit=True)
    torso_rows = plate_rows(braw, (27, 37))
    G.add(col(49, 56, 32, cz, 11.2, 8.4, 2.6), steel(STEEL, torso_rows), lit=True)
    rx_t = np.where(r < 35, 6 + 4 * np.clip((r - 31) / 3, 0, 1), 10.0)
    torso = (np.abs((x - 32) / rx_t) ** 2.6 + np.abs((z - cz) / 8.6) ** 2.6 <= 1) & (r >= 32) & (r < 53)
    G.add(torso, steel(STEEL, torso_rows), lit=True)
    fist_c = (16.6, 50.4, 26.0)                         # the sword hand, out and forward of the hip: x, row, z
    for cx, cols in ((19.8, (16, 23)), (44.2, (41, 48))):
        arm = col(33, 45.5 if cx < 32 else 48.5, cx, cz, 4.0, 4.3, 2.2) | ell(35, cx, cz, 4.5, 4.8, 4.8)
        if cx > 32: arm |= col(48.5, 52, cx, cz - 0.5, 3.6, 3.9, 2.4)      # the shield hand, behind the shield
        G.add(arm, steel(STEEL, plate_rows(braw, cols)), lit=True)
    # the sword arm bends forward at the elbow into a gauntlet fist closed round the grip
    fx, fr, fz = fist_c
    def capsule(p0, p1, rad):
        p0, p1 = np.array(p0), np.array(p1); dv = p1 - p0; L2 = dv @ dv
        q = (x - p0[0]) * dv[0] + (r - p0[1]) * dv[1] + (z - p0[2]) * dv[2]
        tq = np.clip(q / L2, 0, 1)
        return (x - p0[0] - tq * dv[0]) ** 2 + (r - p0[1] - tq * dv[1]) ** 2 + (z - p0[2] - tq * dv[2]) ** 2 <= rad * rad
    forearm = capsule((19.8, 44.5, cz), (fx + 0.4, fr - 2.2, fz + 1.2), 3.3)
    G.add(forearm, steel(STEEL, plate_rows(braw, (16, 23))), lit=True)
    fist = (np.abs((x - fx) / 2.7) ** 2.6 + np.abs((r - fr) / 2.7) ** 2.6 + np.abs((z - fz) / 3.0) ** 2.6) <= 1
    def fingers(r, x, z, i):
        i = i - 1                                                                 # a darker gauntlet than the arm
        fing = (z < fz + 0.6) & (np.floor((r - fr + 2.7) * 1.15) % 2 == 1)      # finger lines round the front
        i[fing] = -100
        return i
    G.add(fist, steel(STEEL, extra=fingers), lit=True)
    G.add(col(30, 35, 32, cz, 4.5, 4.5), sprite(by_sector(face, lambda rr: (32, cz, 4.5, 4.5))))

    # --- head: the original face on a flat front, framed by the hair as the sprite draws it ---
    hc = (22.5, 32.0, 31.5, 11.2, 11.0, 11.0)
    head = ell(*hc, p=2.2, pfront=4.0)
    G.add(head, sprite(by_sector(face, lambda rr: (hc[1], hc[2], hc[4], hc[5]), front=78, back=60)))

    # --- long hair: rounded over the back and sides, flaring a little as it falls, strands,
    #     an uneven bottom edge; filled behind the neck so it reads as one mass ---
    cr, cx0, cz0, rr_, rx_, rz_ = hc; t = 1.7
    th = np.arctan2(x - cx0, z - cz0)                   # 0 straight back, +-pi/2 the sides
    flare = np.clip(r - cr, 0, None) * 0.09
    outer_rx, outer_rz = rx_ + t + flare, rz_ + t + flare
    rad_out = np.abs((x - cx0) / outer_rx) ** 2.2 + np.abs((z - cz0) / outer_rz) ** 2.2
    shell = (np.abs((r - cr) / (rr_ + t)) ** 2.2 + rad_out <= 1) | ((r > cr) & (rad_out <= 1))
    ends = 34.5 - 3.2 * (np.abs(th) / math.pi < 0.45) * 0 - 3.0 * np.clip((np.abs(th) - 1.1) / 0.6, 0, 1) \
        + 1.1 * np.sin(th * 7 + 0.6) + 0.7 * np.sin(th * 13)
    hairm = shell & ~head & (r >= 15) & (z >= cz0 - 1.5) & (r < ends) & ~((r > 31) & (z < cz0 + 0.5))
    def hair_paint(r, x, z, n):
        R_ = np.array(HAIRC)
        th = np.arctan2(x - cx0, z - cz0)
        i = band(n, len(R_)) + np.round(1.2 * np.sin(th * 15 + 0.4 * np.sin(r * 0.7))).astype(int)   # strands
        ends = 34.5 - 3.0 * np.clip((np.abs(th) - 1.1) / 0.6, 0, 1) + 1.1 * np.sin(th * 7 + 0.6) + 0.7 * np.sin(th * 13)
        i = i - (r > ends - 1.6)                                                                    # darker tips
        return R_[np.clip(i, 0, len(R_) - 1)].copy()
    G.add(hairm, hair_paint, lit=True)

    # --- helmet: one smooth steel dome hugging the brow, a riveted rim, a point, a nose guard ---
    rim = 17.6 + (z - (hc[2] - hc[5])) * 0.17
    dome = ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 1.5, hc[4] + 1.8, hc[5] + 1.9, p=2.2, pfront=3.0, rzf=hc[5] + 0.7)
    rimband = ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 1.9, hc[4] + 2.3, hc[5] + 2.4, p=2.2, pfront=3.0, rzf=hc[5] + 1.1) & (r <= rim) & (r > rim - 1.7)
    tip = ((x - hc[1]) ** 2 + (z - hc[2]) ** 2 <= (0.8 + np.clip(r - 3, 0, 9) * 0.7) ** 2) & (r >= 3) & (r < 8.5)
    front_z = hc[2] - hc[5] - 0.6
    nasal = (np.abs(x - hc[1]) <= 1.0) & (r >= 17) & (r < 23.5) & (z >= front_z - 0.9) & (z < front_z + 1.5)
    G.clear((G.owner == len(G.parts) - 1) & ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 2.3, hc[4] + 2.6, hc[5] + 2.7, p=2.2) & (r <= rim))
    def helm_extra(r, x, z, i):
        i = i.copy()
        onrim = (r > (17.6 + (z - (hc[2] - hc[5])) * 0.17) - 1.7) & (r <= 17.6 + (z - (hc[2] - hc[5])) * 0.17)
        i[onrim] -= 1
        ang = np.arctan2(x - hc[1], z - hc[2])
        rivet = onrim & (np.abs(((ang * 11.5 / math.pi) % 1) - 0.5) < 0.13) & (np.abs(r - (17.6 + (z - (hc[2] - hc[5])) * 0.17) + 0.85) < 0.5)
        i[rivet] = 99                                    # the lightest shade
        i[(np.abs(x - hc[1]) <= 1.0) & (r >= 17) & (z < hc[2] - hc[5] + 1)] += 1      # nose guard catches the light
        return i
    G.add((dome & (r <= rim)) | rimband | tip | nasal, steel(STEEL, extra=helm_extra), lit=True)

    # --- shield: the heater outline as a curved plate turned 22 degrees outward; the painted
    #     face from the front picture, the wooden back from the back picture ---
    sa = shield.raw['S'][:, :, 3] > 0
    ys, xs = np.nonzero(sa); xcen = (xs.min() + xs.max() + 1) / 2; hwid = (xs.max() + 1 - xs.min()) / 2
    pr, px = np.clip(r.astype(int), 0, P - 1), np.clip(x.astype(int), 0, P - 1)
    zc_of = lambda x: 19.0 + (x - 34) * math.tan(math.radians(22)) - 1.3 * (1 - np.clip((x - xcen) / hwid, -1, 1) ** 2)
    plate = sa[pr, px] & (np.abs(z - zc_of(x)) <= 0.75)
    def shield_paint(r, x, z, n):
        pr, px = np.clip(r.astype(int), 0, P - 1), np.clip(x.astype(int), 0, P - 1)
        front = shield.lookup('S', pr, px); back = shield.lookup('N', pr, px)
        back[back[:, 3] == 0] = (96, 60, 30, 255)
        return np.where((z < zc_of(x))[:, None], front, back)
    G.add(plate, shield_paint)
    G.add(col(38, 44, 41.5, 23.0, 1.0, 1.4) & ~plate, lambda r, x, z, n: np.tile(np.array((74, 44, 24, 255)), (len(r), 1)))

    # --- sword: grip through the fist, guard just above it, pommel just below, the blade up
    #     and out to the side (leaning a little back so it shows from both front corners) ---
    hand = np.array([fx, fr, fz])
    d = np.array([-0.42, -0.88, 0.12]); d /= np.linalg.norm(d)
    w = np.array([1.0, 0, 0]) - d[0] * d; w /= np.linalg.norm(w)
    tt = np.cross(d, w)
    def local(xx, rr, zz):
        q = np.stack([xx - hand[0], rr - hand[1], zz - hand[2]], -1).astype(np.float64)
        return q @ d, q @ w, q @ tt
    a, b, c = local(x, r, z)
    L = 33.0
    hw = np.where(a < L - 5, 1.9, 1.9 * np.clip((L - a) / 5, 0.12, 1))
    blade = (a >= 4.2) & (a <= L) & (np.abs(b) <= hw) & (np.abs(c) <= 0.55)
    guard = (a >= 2.8) & (a < 4.2) & (np.abs(b) <= 4.8) & (np.abs(c) <= 1.0)
    grip = (a >= -5.2) & (a < 2.8) & (b * b + c * c <= 0.95 ** 2)
    pommel = (a + 6.1) ** 2 + b * b + c * c <= 1.5 ** 2
    LIGHT_, MID, GROOVE, DARK = STEEL[-1], STEEL[-2], STEEL[-3], STEEL[0]
    def blade_paint(r, x, z, n):
        a, b, c = local(x, r, z)
        out = np.tile(np.array(MID), (len(r), 1)); out[b < -0.9] = LIGHT_; out[np.abs(b) < 0.4] = GROOVE
        return out
    def guard_paint(r, x, z, n):
        a, b, c = local(x, r, z)
        out = np.tile(np.array(DARK), (len(r), 1)); out[a > 3.7] = GROOVE; out[np.abs(b) > 4.0] = MID
        return out
    def grip_paint(r, x, z, n):
        a, b, c = local(x, r, z)
        out = np.tile(np.array((110, 70, 40, 255)), (len(r), 1)); out[(np.floor(a * 1.2) % 2) == 0] = (74, 44, 24, 255)
        return out
    G.add(blade, blade_paint); G.add(guard, guard_paint); G.add(grip & ~fist, grip_paint)
    G.add(pommel, lambda r, x, z, n: np.tile(np.array(MID), (len(r), 1)))
    G.paint()
    return G, full
