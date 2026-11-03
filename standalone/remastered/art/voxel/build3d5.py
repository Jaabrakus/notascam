# Fifth pass of the 3D knight (after build3d4.py): the sword in an attacking pose instead of hanging
# flat at the side. The blade turns so its cutting edge faces the enemy (the front), so from the
# front it shows its edge and bevels, not its flat. Poses (pose=...):
#   'raised'  - wound up to strike: fist by the right shoulder, blade back over it;
#   'upright' - on guard: fist in front of the chest, blade upright beside the head (the one chosen);
#   'forward' - point toward the enemy: fist at the belly, blade forward and up;
#   'side'    - build3d4's pose (blade up and out at the side, flat to the front).
# The grid reaches 10 sprite pixels in front of the picture (zoff) so a blade held forward fits.
import numpy as np, math
import compose64, carve
from build3d2 import P, arr, Views, by_sector
from build3d3 import Grid, sprite, ramp_of, plate_rows, LIGHT, SEAM

def band(n, steps):
    """The sprite's flat light bands from the 3D light: mostly the darker middle shades, the
    next one up where it faces the light, the brightest only head-on to it."""
    d = n @ LIGHT
    cuts = np.array([-0.5, 0.6, 0.9]) if steps == 4 else np.linspace(-0.75, 0.85, steps - 1)
    return np.searchsorted(cuts, d)

def steel(ramp, rows=None, extra=None, normal=None):
    R = np.array(ramp)
    def paint(r, x, z, n):
        if normal is not None: n = normal(r, x, z)
        i = band(n, len(R))
        pr = np.clip(r.astype(int), 0, P - 1)
        if rows is not None: i = i + rows[0][pr]
        if extra is not None: i = extra(r, x, z, i)
        out = R[np.clip(i, 0, len(R) - 1)].copy()
        out[i <= -50] = SEAM
        if rows is not None: out[rows[1][pr]] = SEAM
        return out
    return paint

def skin_face(img):
    """The front picture of the bare head with everything beside the skin (side hair,
    sideburns) replaced by the skin at the edge of each row; eyes and mouth untouched."""
    a = img.copy()
    skin = (a[:, :, 0] > 180) & (a[:, :, 1] > 130) & (a[:, :, 0] - a[:, :, 2] > 50) & (a[:, :, 3] > 0)
    for r in range(8, 30):
        cs = np.nonzero(skin[r])[0]
        if len(cs) < 4: continue
        a[r, :cs[0]] = a[r, cs[0]]; a[r, cs[-1] + 1:] = a[r, cs[-1]]
    return a

def build_knight(sub=2, f=0, pose='upright', zoff=10):
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
    body, hairv, helm, shield = V(BODY, LEGS, CHEST, ARML, ARMR), V(HAIR), V(HELM), V(SHIELD)
    face = V(BODY)
    face.img['S'] = skin_face(face.img['S'])
    STEEL = ramp_of(helm.raw['S'])                      # the tier's steel, darkest first
    HAIRC = np.array(ramp_of(hairv.raw['N'], lo=60))
    G = Grid(sub); G.z = G.z - zoff; G.center = (32.0 * sub, (31.5 + zoff) * sub)
    r, x, z = G.r, G.x, G.z

    def col(r0, r1, cx, cz, rx, rz, p=2.0):
        return (np.abs((x - cx) / rx) ** p + np.abs((z - cz) / rz) ** p <= 1) & (r >= r0) & (r < r1)
    def ell(cr, cx, cz, rr, rx, rz, p=2.0, pfront=None, rzf=None):
        pz = p if pfront is None else np.where(z < cz, pfront, p)
        rzz = rz if rzf is None else np.where(z < cz, rzf, rz)
        return np.abs((r - cr) / rr) ** p + np.abs((x - cx) / rx) ** p + np.abs((z - cz) / rzz) ** pz <= 1
    def capsule(p0, p1, rad):
        p0, p1 = np.array(p0), np.array(p1); dv = p1 - p0; L2 = dv @ dv
        tq = np.clip(((x - p0[0]) * dv[0] + (r - p0[1]) * dv[1] + (z - p0[2]) * dv[2]) / L2, 0, 1)
        return (x - p0[0] - tq * dv[0]) ** 2 + (r - p0[1] - tq * dv[1]) ** 2 + (z - p0[2] - tq * dv[2]) ** 2 <= rad * rad

    cz = 31.5
    braw = body.raw['S']
    # --- legs: thigh, knee with a knee plate, shin, and a boot with a toe, a cuff and a sole ---
    for cx in (25.5, 38.5):
        rows = plate_rows(braw, (int(cx) - 3, int(cx) + 3))
        thigh = col(53, 57.6, cx, cz, 5.6, 6.2, 2.4)
        knee = col(57.4, 59.6, cx, cz, 5.0, 5.5, 2.4) | ell(58.2, cx, cz - 4.9, 1.6, 2.7, 1.7, 2.2)
        shin = col(59.4, 61.2, cx, cz + 0.2, 4.6, 5.0, 2.4)
        toe_top = 61.0 + np.clip((cz - 2.0 - z) * 0.38, 0, 2.2)          # the foot slopes down to the toe
        boot = (np.abs((x - cx) / 5.0) ** 2.4 + np.abs((z - (cz - 2.4)) / 7.8) ** 2.2 <= 1) & (r >= toe_top) & (r < 64)
        cuff = col(60.4, 61.6, cx, cz + 0.2, 5.3, 5.7, 2.4)
        def leg_extra(r, x, z, i, cx=cx):
            i = i.copy(); i[r >= 60.4] -= 1                                  # darker boots, as the sprite
            i[r >= 63.3] = -100                                              # the sole
            i[(r >= 60.4) & (r < 61.0)] = -100                               # the cuff's top edge
            return i
        G.add(thigh | knee | shin, steel(STEEL, rows), lit=True)
        G.add(boot | cuff, steel(STEEL, extra=leg_extra), lit=True)
    torso_rows = plate_rows(braw, (27, 37))
    G.add(col(49, 56, 32, cz, 11.2, 8.4, 2.6), steel(STEEL, torso_rows), lit=True)
    rx_t = np.where(r < 35, 6 + 4 * np.clip((r - 31) / 3, 0, 1), 10.0)
    torso = (np.abs((x - 32) / rx_t) ** 2.6 + np.abs((z - cz) / 8.6) ** 2.6 <= 1) & (r >= 32) & (r < 53)
    G.add(torso, steel(STEEL, torso_rows), lit=True)

    # --- arms: the shield arm hangs behind the shield; the sword arm takes the pose ---
    POSES = {   # elbow, fist (x, row, z), the blade's direction (x, row, z), blade length
        'raised': ((12.8, 37.0, 30.0), (14.6, 29.5, 27.0), (-0.30, -0.72, 0.62), 31.0),
        'upright': ((15.5, 43.5, 26.0), (18.0, 38.5, 19.0), (-0.18, -0.96, 0.12), 31.0),
        'forward': ((16.5, 44.5, 27.0), (18.5, 46.0, 18.5), (-0.12, -0.50, -0.86), 30.0),
        'side': ((18.6, 43.0, cz - 0.6), (18.0, 46.0, 23.0), (-0.48, -0.86, 0.05), 31.0),
    }
    elbow, (fx, fr, fz), dvec, L = POSES[pose]
    G.add(col(33, 48.5, 44.2, cz, 4.0, 4.3, 2.2) | ell(35, 44.2, cz, 4.5, 4.8, 4.8) | col(48.5, 52, 44.2, cz - 0.5, 3.6, 3.9, 2.4),
          steel(STEEL, plate_rows(braw, (41, 48))), lit=True)
    upper = capsule((19.8, 35.5, cz), elbow, 4.0) | ell(35, 19.8, cz, 4.5, 4.8, 4.8) | ell(elbow[1], elbow[0], elbow[2], 3.6, 3.6, 3.6)
    forearm = capsule(elbow, (fx, fr, fz), 3.3)
    G.add(upper | forearm, steel(STEEL, plate_rows(braw, (16, 23))), lit=True)
    fist = (np.abs((x - fx) / 2.7) ** 2.6 + np.abs((r - fr) / 2.7) ** 2.6 + np.abs((z - fz) / 3.0) ** 2.6) <= 1
    def fingers(r, x, z, i):
        i = i - 1
        i[(x < fx + 0.8) & (np.floor((r - fr + 2.7) * 1.15) % 2 == 1)] = -100     # finger lines on the outside
        return i
    G.add(fist, steel(STEEL, extra=fingers), lit=True)
    G.add(col(30, 35, 32, cz, 4.5, 4.5), sprite(by_sector(face, lambda rr: (32, cz, 4.5, 4.5))))

    # --- head: the original face on a gently rounded front, clean skin round to the cheeks ---
    hc = (22.5, 32.0, 31.5, 11.2, 11.0, 11.0)
    head = ell(*hc, p=2.2, pfront=3.2)
    G.add(head, sprite(by_sector(face, lambda rr: (hc[1], hc[2], hc[4], hc[5]), front=78, back=60)))

    # --- hair: the long hair at the back (rounded, flaring, strands, ragged ends) and a lock on
    #     each side of the face, where the sprite draws hair beside the cheeks ---
    cr, cx0, cz0, rr_, rx_, rz_ = hc; t = 1.7
    th = np.arctan2(x - cx0, z - cz0)
    flare = np.clip(r - cr, 0, None) * 0.09
    rad_out = np.abs((x - cx0) / (rx_ + t + flare)) ** 2.2 + np.abs((z - cz0) / (rz_ + t + flare)) ** 2.2
    shell = (np.abs((r - cr) / (rr_ + t)) ** 2.2 + rad_out <= 1) | ((r > cr) & (rad_out <= 1))
    ends_of = lambda th: 34.5 - 3.0 * np.clip((np.abs(th) - 1.1) / 0.6, 0, 1) + 1.1 * np.sin(th * 7 + 0.6) + 0.7 * np.sin(th * 13)
    back_hair = shell & ~head & (r >= 15) & (z >= cz0 - 1.5) & (r < ends_of(th)) & ~((r > 31) & (z < cz0 + 0.5))
    locks = np.zeros_like(head)
    for s in (-1, 1):
        lx = cx0 + s * (rx_ - 0.4)
        wav = 0.5 * np.sin((z - cz0) * 1.3 + s)
        locks |= (np.abs(x - lx) <= 1.9) & (z >= cz0 - 6.2) & (z < cz0 + 1.0) & (r >= 18.4 + (z - (hc[2] - hc[5])) * 0.17) & (r < 30.5 + wav) & ~head   # from under the helmet rim
    def hair_paint(r, x, z, n):
        th = np.arctan2(x - cx0, z - cz0)
        i = band(n, len(HAIRC)) + np.round(1.2 * np.sin(th * 15 + 0.4 * np.sin(r * 0.7))).astype(int)
        i = i - ((r > ends_of(th) - 1.6) & (z >= cz0 - 1.5))
        i = i - ((r > 28.5) & (z < cz0 + 1.0))                               # darker tips on the side locks
        return HAIRC[np.clip(i, 0, len(HAIRC) - 1)].copy()
    G.add(back_hair | locks, hair_paint, lit=True)

    # --- helmet: one smooth steel dome hugging the brow, a riveted rim, a point, a nose guard ---
    rimf = lambda z: 17.6 + (z - (hc[2] - hc[5])) * 0.17
    rim = rimf(z)
    dome = ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 1.5, hc[4] + 1.8, hc[5] + 1.9, p=2.2, pfront=3.0, rzf=hc[5] + 0.7)
    rimband = ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 1.9, hc[4] + 2.3, hc[5] + 2.4, p=2.2, pfront=3.0, rzf=hc[5] + 1.1) & (r <= rim) & (r > rim - 1.7)
    tip = ((x - hc[1]) ** 2 + (z - hc[2]) ** 2 <= (0.8 + np.clip(r - 3, 0, 9) * 0.7) ** 2) & (r >= 3) & (r < 8.5)
    front_z = hc[2] - hc[5] - 0.6
    nasal = (np.abs(x - hc[1]) <= 1.0) & (r >= 17) & (r < 23.5) & (z >= front_z - 0.9) & (z < front_z + 1.5)
    G.clear((G.owner == len(G.parts) - 1) & ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 2.3, hc[4] + 2.6, hc[5] + 2.7, p=2.2) & (r <= rim))
    def helm_extra(r, x, z, i):
        i = i.copy(); rm = rimf(z)
        onrim = (r > rm - 1.7) & (r <= rm)
        i[onrim] -= 1
        ang = np.arctan2(x - hc[1], z - hc[2])
        i[onrim & (np.abs(((ang * 11.5 / math.pi) % 1) - 0.5) < 0.13) & (np.abs(r - rm + 0.85) < 0.5)] = 99
        i[(np.abs(x - hc[1]) <= 1.0) & (r >= 17) & (z < hc[2] - hc[5] + 1)] += 1
        return i
    G.add((dome & (r <= rim)) | rimband | tip | nasal, steel(STEEL, extra=helm_extra), lit=True)

    # --- shield: the heater outline, thicker and more curved, with a raised steel rim round the
    #     painted face and a planked wooden back ---
    sa = shield.raw['S'][:, :, 3] > 0
    dist = np.zeros(sa.shape, int); cur = sa.copy(); k = 0
    while cur.any():
        k += 1; dist[cur] = k
        pad = np.pad(cur, 1); cur = cur & pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:]
    ys, xs = np.nonzero(sa); xcen = (xs.min() + xs.max() + 1) / 2; hwid = (xs.max() + 1 - xs.min()) / 2
    pr, px = np.clip(r.astype(int), 0, P - 1), np.clip(x.astype(int), 0, P - 1)
    zc_of = lambda x: 18.6 + (x - 34) * math.tan(math.radians(22)) - 2.0 * (1 - np.clip((x - xcen) / hwid, -1, 1) ** 2)
    zc = zc_of(x)
    onrim = sa[pr, px] & (dist[pr, px] <= 2)
    body_ = sa[pr, px] & (np.abs(z - zc) <= 0.9)
    rimv = onrim & (z >= zc - 1.7) & (z <= zc + 1.5)
    def shield_face(r, x, z, n):
        pr, px = np.clip(r.astype(int), 0, P - 1), np.clip(x.astype(int), 0, P - 1)
        front = shield.lookup('S', pr, px)
        wood = np.tile(np.array((96, 60, 30, 255)), (len(r), 1))
        wood[(x % 3.2) < 0.55] = (70, 42, 20, 255)                           # planks
        return np.where((z < zc_of(x))[:, None], front, wood)
    G.add(body_ & ~onrim, shield_face)
    G.add(rimv, steel(STEEL), lit=True)
    G.add(col(38, 44, 41.8, 23.6, 1.0, 1.4) & ~body_ & ~rimv, lambda r, x, z, n: np.tile(np.array((74, 44, 24, 255)), (len(r), 1)))

    # --- sword: grip through the fist, guard above it, pommel below; a bevelled blade (diamond
    #     section, ridge down the middle) with bright cutting edges, the edge toward the enemy ---
    hand = np.array([fx, fr, fz])
    d = np.array(dvec, float); d /= np.linalg.norm(d)
    fwd, up = np.array([0, 0, -1.0]), np.array([0, -1.0, 0])
    w0 = np.array([1.0, 0, 0]) if pose == 'side' else up if abs(fwd @ d) > 0.7 else fwd
    w = w0 - (w0 @ d) * d; w /= np.linalg.norm(w)
    tt = np.cross(d, w)
    def local(xx, rr, zz):
        q = np.stack([xx - hand[0], rr - hand[1], zz - hand[2]], -1).astype(np.float64)
        return q @ d, q @ w, q @ tt
    a, b, c = local(x, r, z)
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
        i = i.copy(); i[np.abs(b) > hw - 0.45] = 99                         # the cutting edges
        i[np.abs(b) < 0.3] -= 1                                              # the ridge line
        return i
    G.add(blade, steel(STEEL, extra=blade_extra, normal=blade_normal), lit=True)
    G.add(guard, steel(STEEL, extra=lambda r, x, z, i: i - 1), lit=True)
    def grip_paint(r, x, z, n):
        a, b, c = local(x, r, z)
        out = np.tile(np.array((110, 70, 40, 255)), (len(r), 1)); out[(np.floor(a * 1.2) % 2) == 0] = (74, 44, 24, 255)
        return out
    G.add(grip & ~fist, grip_paint)
    G.add(pommel, steel(STEEL), lit=True)
    G.paint()
    return G, full
