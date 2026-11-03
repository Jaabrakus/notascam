# A 3D unit in the sprite's style, second pass. Like build3d.py (parts shaped on purpose,
# sized from the 64 px sprite, each painted only from its own sprite layer), but:
#  - finer blocks: each sprite pixel is SUB x SUB x SUB blocks, so shapes are rounder while
#    the paint keeps the sprite's chunky pixels (it samples whole sprite pixels);
#  - the held items are modelled as real objects (a sword with blade, guard, grip and pommel;
#    a curved shield with a rim) instead of being read off the pictures;
#  - only the outside blocks are painted.
# All sizes below are in sprite pixels: x across the front picture, row down it, z front->back.
import numpy as np, math
import compose64, carve
from build3d import deoutline, sector_order

P = 64

def arr(im): return np.asarray(im.convert('RGBA')).astype(np.int32)

def filled(a, reach=5):
    """Each transparent pixel takes the nearest opaque one in its row (within reach)."""
    out = a.copy(); al = a[:, :, 3] > 0
    for r in range(a.shape[0]):
        idx = np.nonzero(al[r])[0]
        if not len(idx): continue
        for c in np.nonzero(~al[r])[0]:
            j = idx[np.argmin(abs(idx - c))]
            if abs(j - c) <= reach: out[r, c] = a[r, j]
    return out

class Views:
    def __init__(self, layers, sN, sW, f=0):
        u = compose64.unit(layers, f)
        self.raw = {d: arr(u[d]) for d in 'SNEW'}
        self.img = {d: filled(deoutline(self.raw[d])) for d in 'SNEW'}
        self.sN, self.sW = sN, sW
    def lookup(self, d, pr, k):
        """Colours (n x 4) of facing d at sprite rows pr, columns from x (S, N) or z (E, W)."""
        if d == 'S': c = k
        elif d == 'N': c = P - 1 - k + self.sN
        elif d == 'E': c = P - 1 - k
        else: c = k - self.sW
        ok = (c >= 0) & (c < P)
        out = np.zeros((len(pr), 4), np.int32)
        out[ok] = self.img[d][pr[ok], c[ok]]
        return out

class Grid:
    def __init__(self, sub=2):
        self.sub = sub; n = P * sub; self.n = n
        R, X, Z = np.meshgrid(np.arange(n, dtype=np.float32), np.arange(n, dtype=np.float32), np.arange(n, dtype=np.float32), indexing='ij')
        self.r, self.x, self.z = (R + 0.5) / sub, (X + 0.5) / sub, (Z + 0.5) / sub   # block centres, sprite units
        self.owner = np.zeros((n, n, n), np.int16)
        self.parts = [None]
    def add(self, mask, painter):
        self.parts.append(painter); self.owner[mask] = len(self.parts) - 1
    def clear(self, mask): self.owner[mask] = 0
    def solid(self): return self.owner > 0
    def paint(self):
        s = self.solid(); pad = np.pad(s, 1)
        inner = pad[:-2, 1:-1, 1:-1] & pad[2:, 1:-1, 1:-1] & pad[1:-1, :-2, 1:-1] & pad[1:-1, 2:, 1:-1] & pad[1:-1, 1:-1, :-2] & pad[1:-1, 1:-1, 2:]
        surf = s & ~inner
        self.col = np.zeros(s.shape + (4,), np.int32)
        self.col[s] = (90, 90, 90, 255)      # never seen
        for i in range(1, len(self.parts)):
            m = surf & (self.owner == i)
            if not m.any(): continue
            idx = np.nonzero(m)
            self.col[idx] = self.parts[i](self.r[idx], self.x[idx], self.z[idx])
        self.part = self.owner

def by_sector(views, centre, front=45, back=45, fallback=(128, 128, 128, 255)):
    """Paint each block from the facing it looks toward, measured from the part's own axis."""
    def paint(r, x, z):
        cx, cz, rx, rz = centre(r)
        ax, az = (x - cx) / rx, (z - cz) / rz
        pr, px, pz = np.clip(r.astype(int), 0, P - 1), np.clip(x.astype(int), 0, P - 1), np.clip(z.astype(int), 0, P - 1)
        cand = {d: views.lookup(d, pr, px if d in 'SN' else pz) for d in 'SNEW'}
        out = np.zeros((len(r), 4), np.int32); out[:] = fallback
        done = np.zeros(len(r), bool)
        orders = [sector_order(a, b, front, back) for a, b in zip(ax, az)]
        for k in range(4):
            for d in 'SNEW':
                sel = ~done & np.array([o[k] == d for o in orders]) & (cand[d][:, 3] > 0)
                out[sel] = cand[d][sel]; done |= sel
        return out
    return paint

def flat(colour):
    def paint(r, x, z): return np.tile(np.array(colour, np.int32), (len(r), 1))
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
    body, face, hair, helm, shield = V(BODY, LEGS, CHEST, ARML, ARMR), V(BODY, HAIR), V(HAIR), V(HELM), V(SHIELD)
    # the side pictures draw the profile's eye and the far side's hair in front of the face;
    # the head's sides take the bare head's side instead (ear, hair at the back)
    bare = V(BODY)
    face.img['E'], face.img['W'] = bare.img['E'], bare.img['W']
    G = Grid(sub); r, x, z = G.r, G.x, G.z

    def col(r0, r1, cx, cz, rx, rz, p=2.0):
        return (np.abs((x - cx) / rx) ** p + np.abs((z - cz) / rz) ** p <= 1) & (r >= r0) & (r < r1)
    def ell(cr, cx, cz, rr, rx, rz, p=2.0, pfront=None, rzf=None):
        pz = p if pfront is None else np.where(z < cz, pfront, p)
        rzz = rz if rzf is None else np.where(z < cz, rzf, rz)
        return np.abs((r - cr) / rr) ** p + np.abs((x - cx) / rx) ** p + np.abs((z - cz) / rzz) ** pz <= 1

    cz = 31.5
    # --- body: legs, hips, torso, arms, neck; the armour is painted straight onto it ---
    for cx in (25.5, 38.5):
        leg = col(53, 64, cx, cz, 5.6, 6.2, 2.4) | col(59, 64, cx, cz - 2.5, 5.4, 7.5, 2.6)
        G.add(leg, by_sector(body, lambda rr, cx=cx: (cx, cz, 5.6, 6.2), front=50))
    G.add(col(49, 56, 32, cz, 11.2, 8.4, 2.6), by_sector(body, lambda rr: (32, cz, 11.2, 8.4), front=50))
    rx_t = np.where(r < 35, 6 + 4 * np.clip((r - 31) / 3, 0, 1), 10.0)
    torso = (np.abs((x - 32) / rx_t) ** 2.6 + np.abs((z - cz) / 8.6) ** 2.6 <= 1) & (r >= 32) & (r < 53)
    G.add(torso, by_sector(body, lambda rr: (32, cz, 10, 8.6), front=50))
    for cx in (19.8, 44.2):
        arm = col(33, 52, cx, cz, 4.0, 4.3, 2.2) | ell(35, cx, cz, 4.5, 4.8, 4.8)
        G.add(arm, by_sector(body, lambda rr, cx=cx: (cx, cz, 4.0, 4.3), front=55))
    G.add(col(30, 35, 32, cz, 4.5, 4.5), by_sector(face, lambda rr: (32, cz, 4.5, 4.5)))

    # --- head: a flat face on the front (the original face, only there, framed by the hair as
    #     the sprite draws it), round behind ---
    hc = (22.5, 32.0, 31.5, 11.2, 11.0, 11.0)
    head = ell(*hc, p=2.2, pfront=4.0)
    G.add(head, by_sector(face, lambda rr: (hc[1], hc[2], hc[4], hc[5]), front=78, back=60))

    # --- long hair: over the back and sides, hanging straight down behind the neck ---
    cr, cx0, cz0, rr_, rx_, rz_ = hc; t = 1.6
    shell = ell(cr, cx0, cz0, rr_ + t, rx_ + t, rz_ + t, p=2.2)
    hang = (np.abs((x - cx0) / (rx_ + t)) ** 2.2 + np.abs((z - cz0) / (rz_ + t)) ** 2.2 <= 1) & (r > cr) & (r < 37)
    inner = head | ((np.abs((x - cx0) / (rx_ - 0.5)) ** 2.2 + np.abs((z - cz0) / (rz_ - 0.5)) ** 2.2 <= 1) & (r > cr))
    hairm = (shell | hang) & ~inner & (r >= 15) & (z >= cz0 - 1.5) & ~((r > 31) & (z < cz0 + 1))
    G.add(hairm, by_sector(hair, lambda rr: (cx0, cz0, rx_, rz_), front=60, back=70))

    # --- helmet: dome hugging the brow (so the eyes show), rim, point, nose guard ---
    rim = 17.6 + (z - (hc[2] - hc[5])) * 0.17
    dome = ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 1.5, hc[4] + 1.8, hc[5] + 1.9, p=2.2, pfront=3.0, rzf=hc[5] + 0.7)
    tip = ((x - hc[1]) ** 2 + (z - hc[2]) ** 2 <= (0.8 + np.clip(r - 3, 0, 9) * 0.7) ** 2) & (r >= 3) & (r < 8.5)
    front_z = hc[2] - hc[5] - 0.6
    nasal = (np.abs(x - hc[1]) <= 1.0) & (r >= 17) & (r < 23.5) & (z >= front_z - 0.6) & (z < front_z + 1.5)
    G.clear((G.owner == len(G.parts) - 1) & ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 2.3, hc[4] + 2.6, hc[5] + 2.7, p=2.2) & (r <= rim))
    G.add((dome & (r <= rim)) | tip | nasal, by_sector(helm, lambda rr: (hc[1], hc[2], hc[4], hc[5]), front=50))

    # --- shield: the heater shape from the front picture as a curved plate on the left arm,
    #     turned 22 degrees outward; painted face on the front, the wooden back behind ---
    sa = shield.raw['S'][:, :, 3] > 0
    ys, xs = np.nonzero(sa); xcen = (xs.min() + xs.max() + 1) / 2; hwid = (xs.max() + 1 - xs.min()) / 2
    pr, px = np.clip(r.astype(int), 0, P - 1), np.clip(x.astype(int), 0, P - 1)
    u = np.clip((x - xcen) / hwid, -1, 1)
    zc = 19.0 + (x - 34) * math.tan(math.radians(22)) - 1.3 * (1 - u * u)
    plate = sa[pr, px] & (np.abs(z - zc) <= 0.75)
    def shield_paint(r, x, z):
        pr, px = np.clip(r.astype(int), 0, P - 1), np.clip(x.astype(int), 0, P - 1)
        u = np.clip((x - xcen) / hwid, -1, 1); zc = 19.0 + (x - 34) * math.tan(math.radians(22)) - 1.3 * (1 - u * u)
        front = shield.lookup('S', pr, px); back = shield.lookup('N', pr, px)
        wood = np.array([96, 60, 30, 255]); back[back[:, 3] == 0] = wood
        return np.where((z < zc)[:, None], front, back)
    G.add(plate, shield_paint)
    # the grip on the back, where the arm holds it
    G.add(col(38, 44, 41.5, 23.0, 1.0, 1.4) & ~plate, flat((74, 44, 24, 255)))

    # --- sword: blade, cross-guard, grip and pommel, held in the right hand, pointing up and
    #     out to the side like the front picture (leaning a little back, not toward the camera,
    #     so it shows from both front corners) ---
    hand = np.array([19.8, 50.5, 30.5])                       # x, row, z
    d = np.array([-0.42, -0.88, 0.12]); d /= np.linalg.norm(d)
    w = np.array([1.0, 0, 0]) - d[0] * d; w /= np.linalg.norm(w)
    tt = np.cross(d, w)
    px_, pr_, pz_ = x - hand[0], r - hand[1], z - hand[2]
    a = px_ * d[0] + pr_ * d[1] + pz_ * d[2]
    b = px_ * w[0] + pr_ * w[1] + pz_ * w[2]
    c = px_ * tt[0] + pr_ * tt[1] + pz_ * tt[2]
    L = 31.0
    hw = np.where(a < L - 5, 1.9, 1.9 * np.clip((L - a) / 5, 0.12, 1))
    blade = (a >= 2.6) & (a <= L) & (np.abs(b) <= hw) & (np.abs(c) <= 0.55)
    guard = (a >= 1.2) & (a < 2.6) & (np.abs(b) <= 4.2) & (np.abs(c) <= 0.9)
    grip = (a >= -4.0) & (a < 1.2) & (b * b + c * c <= 0.9 ** 2)
    pommel = (a + 4.9) ** 2 + b * b + c * c <= 1.45 ** 2
    LIGHT, MID, GROOVE, DARK = (206, 212, 220, 255), (148, 154, 163, 255), (104, 109, 118, 255), (66, 70, 78, 255)
    BROWN, BROWN_D = (110, 70, 40, 255), (74, 44, 24, 255)
    def local(xx, rr, zz):
        q = np.stack([xx - hand[0], rr - hand[1], zz - hand[2]], -1).astype(np.float64)
        return q @ d, q @ w, q @ tt
    def blade_paint(r, x, z):
        a, b, c = local(x, r, z)
        out = np.tile(np.array(MID), (len(r), 1))
        out[b < -0.9] = LIGHT                 # the bright edge, like the sprite's
        out[np.abs(b) < 0.4] = GROOVE         # the fuller down the middle
        return out
    def guard_paint(r, x, z):
        a, b, c = local(x, r, z)
        out = np.tile(np.array(GROOVE), (len(r), 1)); out[a < 1.7] = DARK; out[np.abs(b) > 3.4] = MID
        return out
    def grip_paint(r, x, z):
        a, b, c = local(x, r, z)
        out = np.tile(np.array(BROWN), (len(r), 1)); out[(np.floor(a * 1.2) % 2) == 0] = BROWN_D   # leather wraps
        return out
    G.add(blade, blade_paint); G.add(guard, guard_paint); G.add(grip, grip_paint); G.add(pommel, flat(MID))
    G.paint()
    return G, full
