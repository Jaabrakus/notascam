# A designed 3D unit in the sprite's style: parts shaped on purpose (head, body, arms, legs,
# hair, helmet, a flat shield, a straight sword), sized from the 64 px sprite, one block per
# sprite pixel, painted from that part's own sprite layer (front from the front facing, back
# from the back, sides from the sides) so nothing is painted twice.
import numpy as np, math
import compose64, carve
from PIL import Image

N = 64
R, X, Z = np.meshgrid(np.arange(N), np.arange(N), np.arange(N), indexing='ij')
Rc, Xc, Zc = R + 0.5, X + 0.5, Z + 0.5

def arr(im): return np.asarray(im.convert('RGBA')).astype(np.int32)

def deoutline(a, passes=2):
    # the sprite's own dark rim belongs to its outline, not to the surface: paint the
    # surface with the colour just inside it (the renderer draws a real outline)
    a = a.copy()
    for _ in range(passes):
        al = a[:, :, 3] > 0
        pad = np.pad(al, 1)
        edge = al & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        lum = a[:, :, :3].sum(2)
        dark = edge & (lum < 150)
        if not dark.any(): break
        b = a.copy()
        for r, c in zip(*np.nonzero(dark)):
            best = None
            for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < N and 0 <= cc < N and a[rr, cc, 3] > 0 and not dark[rr, cc] and a[rr, cc, :3].sum() >= 150:
                    best = a[rr, cc]; break
            if best is not None: b[r, c] = best
        a = b
    return a

class Views:
    """One part's four facings, lined up with the model: S by x, N by x (mirrored), E and W by z."""
    def __init__(self, layers, sN, sW, f=0, outline=False):
        u = compose64.unit(layers, f)
        self.raw = {d: arr(u[d]) for d in 'SNEW'}
        self.img = {d: (self.raw[d] if outline else deoutline(self.raw[d])) for d in 'SNEW'}
        self.sN, self.sW = sN, sW
    def col(self, d, x_or_z):
        if d == 'S': return x_or_z
        if d == 'N': return N - 1 - x_or_z + self.sN
        if d == 'E': return N - 1 - x_or_z
        return x_or_z - self.sW
    def pixel(self, d, r, k, reach=5):
        im = self.img[d]; c = self.col(d, k)
        for off in [0] + [s * i for i in range(1, reach + 1) for s in (1, -1)]:
            cc = c + off
            if 0 <= cc < N and im[r, cc, 3] > 0: return im[r, cc]
        return None

def sector_order(ax, az, front=45, back=45):
    # ax, az: the voxel's direction from the part's axis, (+x = unit's left, -z = front)
    t = math.degrees(math.atan2(ax, -az))
    if abs(t) <= front: first = 'S'
    elif abs(t) >= 180 - back: first = 'N'
    else: first = 'W' if t > 0 else 'E'
    rest = {'S': ['W', 'E', 'N'] if t > 0 else ['E', 'W', 'N'], 'N': ['W', 'E', 'S'] if t > 0 else ['E', 'W', 'S'],
            'E': ['S', 'N', 'W'] if abs(t) < 90 else ['N', 'S', 'W'], 'W': ['S', 'N', 'E'] if abs(t) < 90 else ['N', 'S', 'E']}[first]
    return [first] + rest

def paint(model, mask, views, centre, front=45, back=45, sides=True, fallback=(128, 128, 128, 255)):
    """centre(r) -> (cx, cz, rx, rz) of the part at that row (its axis and radii)."""
    for r, x, z in zip(*np.nonzero(mask)):
        cx, cz, rx, rz = centre(r)
        ax, az = (x + 0.5 - cx) / rx, (z + 0.5 - cz) / rz
        c = None
        for d in sector_order(ax, az, front, back):
            if not sides and d in 'EW': continue
            c = views.pixel(d, r, x if d in 'SN' else z)
            if c is not None: break
        model.col[r, x, z] = c if c is not None else fallback
        model.part[r, x, z] = model.cur

class Model:
    def __init__(self):
        self.col = np.zeros((N, N, N, 4), np.int32)
        self.part = np.zeros((N, N, N), np.int32)
        self.cur = 0
    def solid(self): return self.col[:, :, :, 3] > 0

def ellipsoid(cr, cx, cz, rr, rx, rz, p=2.0):
    return (np.abs((Rc - cr) / rr) ** p + np.abs((Xc - cx) / rx) ** p + np.abs((Zc - cz) / rz) ** p) <= 1

def column(r0, r1, cx, cz, rx, rz, p=2.0):
    m = (np.abs((Xc - cx) / rx) ** p + np.abs((Zc - cz) / rz) ** p) <= 1
    return m & (R >= r0) & (R <= r1)

def build_knight(f=0):
    H = 'Gear64/Human/'
    BODY = ('Races64/Human.dmi', '')
    LEGS, CHEST = (H + 'iron.dmi', 'legs.plate.iron'), (H + 'iron.dmi', 'chest.plate.iron')
    ARML, ARMR = (H + 'iron.dmi', 'arms.plate.iron.L'), (H + 'iron.dmi', 'arms.plate.iron.R')
    HAIR = (H + 'old-Hair.dmi', 'HumanBrown')
    HELM = (H + 'iron.dmi', 'helmet.nasal.iron')
    SHIELD = (H + 'iron.dmi', 'shield.heater.iron')
    SWORD = (H + 'iron.dmi', 'weapon.longsword.iron')
    full = compose64.unit([BODY, LEGS, CHEST, HAIR, ARML, ARMR, HELM, SHIELD, SWORD], f)
    _, _, sil = carve.carve(full, patch=False)
    aS = arr(full['S'])[:, :, 3] > 0; aN = arr(full['N'])[:, :, 3] > 0
    aE = arr(full['E'])[:, :, 3] > 0; aW = arr(full['W'])[:, :, 3] > 0
    sN = carve.best_shift(aS, aN[:, ::-1]); sW = carve.best_shift(aE[:, ::-1], aW)
    V = lambda *L: Views(list(L), sN, sW, f)
    body, face, hair, helm = V(BODY, LEGS, CHEST, ARML, ARMR), V(BODY), V(HAIR), V(HELM)
    shield, sword = V(SHIELD), V(SWORD)
    M = Model()

    # --- body (armour painted straight onto it) ---
    M.cur = 1
    cxL, cxR, cz = 25.5, 38.5, 31.5
    legs = column(53, 63, cxL, cz, 5.6, 6.2, 2.4) | column(53, 63, cxR, cz, 5.6, 6.2, 2.4)
    feet = (column(59, 63, cxL, cz - 2.5, 5.4, 7.5, 2.6) | column(59, 63, cxR, cz - 2.5, 5.4, 7.5, 2.6))
    hips = column(49, 55, 32, cz, 11.2, 8.4, 2.6)
    # each leg about its own axis
    for cx in (cxL, cxR):
        m = (legs | feet) & (np.abs(Xc - cx) < 6.5)
        paint(M, m, body, lambda r, cx=cx: (cx, cz, 5.6, 6.2), front=50)
    paint(M, hips, body, lambda r: (32, cz, 11.2, 8.4), front=50)
    torso = np.zeros_like(legs)
    for r in range(32, 53):
        rx = 6 + 4 * min(1, (r - 31) / 3) if r < 35 else 10.0
        rz = 8.6
        torso |= column(r, r, 32, cz, rx, rz, 2.6)
    paint(M, torso, body, lambda r: (32, cz, 10, 8.6), front=50)
    for cx in (19.8, 44.2):   # arms hang beside the body, hands at the bottom
        arm = column(33, 51, cx, cz, 4.0, 4.3, 2.2) | ellipsoid(35, cx, cz, 4.5, 4.8, 4.8)
        paint(M, arm, body, lambda r, cx=cx: (cx, cz, 4.0, 4.3), front=55)
    neck = column(30, 34, 32, cz, 4.5, 4.5)
    paint(M, neck, face, lambda r: (32, cz, 4.5, 4.5))

    # --- head: the face only on the front, never the profile's eye on the side ---
    M.cur = 2
    hc = (22.5, 32.0, 31.5, 11.2, 11.0, 11.0)
    head = (np.abs((Rc - hc[0]) / hc[3]) ** 2.2 + np.abs((Xc - hc[1]) / hc[4]) ** 2.2
            + np.abs((Zc - hc[2]) / hc[5]) ** np.where(Zc < hc[2], 3.2, 2.2)) <= 1
    paint(M, head, face, lambda r: (hc[1], hc[2], hc[4], hc[5]), front=68, back=60)

    # --- long hair: over the back and sides of the head, then hanging straight down to the shoulders ---
    M.cur = 3
    cr, cx0, cz0, rr, rx, rz = hc
    t = 1.6
    ell = ellipsoid(cr, cx0, cz0, rr + t, rx + t, rz + t, p=2.2)
    hang = (np.abs((Xc - cx0) / (rx + t)) ** 2.2 + np.abs((Zc - cz0) / (rz + t)) ** 2.2 <= 1) & (Rc > cr) & (R <= 36)
    inner = ellipsoid(cr, cx0, cz0, rr, rx, rz, p=2.2) | (np.abs((Xc - cx0) / (rx - 0.5)) ** 2.2 + np.abs((Zc - cz0) / (rz - 0.5)) ** 2.2 <= 1) & (Rc > cr)
    hairm = (ell | hang) & ~inner & (R >= 15) & (Zc >= cz0 - 1.5)
    # below the jaw only behind the neck, not in front of the shoulders
    hairm &= ~((R > 31) & (Zc < cz0 + 1))
    paint(M, hairm, hair, lambda r: (cx0, cz0, rx, rz), front=60, back=70)
    # --- helmet: a dome over the head down to the rim, a point on top, a nose guard ---
    M.cur = 4
    dome = (np.abs((Rc - hc[0] - 0.3) / (hc[3] + 1.5)) ** 2.2 + np.abs((Xc - hc[1]) / (hc[4] + 1.8)) ** 2.2
            + np.abs((Zc - hc[2]) / np.where(Zc < hc[2], hc[5] + 1.1, hc[5] + 1.9)) ** np.where(Zc < hc[2], 3.0, 2.2)) <= 1
    rimrow = 18.0 + (Zc - (hc[2] - hc[5])) * 0.17        # the rim dips a little toward the back
    helmm = dome & (Rc <= rimrow) & ~(M.solid() & (M.part == 2) & (Rc > rimrow))
    tip = ((Xc - hc[1]) ** 2 + (Zc - hc[2]) ** 2 <= (1.0 + np.clip(R - 3, 0, 9) * 0.7) ** 2) & (R >= 3) & (R <= 8)
    front_z = hc[2] - hc[5] - 1.0
    nasal = (np.abs(Xc - hc[1]) <= 1.0) & (R >= 18) & (R <= 23) & (Zc >= front_z - 0.5) & (Zc <= front_z + 2)
    hidden = (np.abs((Rc - hc[0] - 0.3) / (hc[3] + 2.3)) ** 2.2 + np.abs((Xc - hc[1]) / (hc[4] + 2.6)) ** 2.2
              + np.abs((Zc - hc[2]) / (hc[5] + 2.7)) ** 2.2 <= 1) & (Rc <= rimrow) & (M.part == 3)
    M.col[hidden] = 0; M.part[hidden] = 0
    paint(M, helmm | tip | nasal, helm, lambda r: (hc[1], hc[2], hc[4], hc[5]), front=50)

    # --- shield: a flat plate on the left arm, turned a little outward ---
    M.cur = 5
    M.plate = {}
    sa = shield.raw['S'][:, :, 3] > 0
    turn = math.tan(math.radians(22))
    for r, x in zip(*np.nonzero(sa)):
        z0 = 19.0 + (x - 34) * turn
        for k, zz in enumerate((int(z0), int(z0) + 1)):
            if 0 <= zz < N:
                if k == 0: c = shield.img['S'][r, x]
                else:
                    c = shield.pixel('N', r, x, reach=0)
                    if c is None: c = np.array([86, 52, 24, 255])     # bare wood on the back
                M.col[r, x, zz] = c; M.part[r, x, zz] = 5
                # shaded as one flat plate, front and back, not block by block
                pn = np.array([turn, 0.0, -1.0]) / math.hypot(turn, 1.0)
                M.plate[(r, x, zz)] = pn if k == 0 else -pn

    # --- sword: a straight blade from the right hand, where the front and side pictures meet ---
    M.cur = 6
    s_front = sword.raw['S'][:, :, 3] > 0
    s_side = (sword.raw['E'][:, ::-1, 3] > 0) | (np.roll(sword.raw['W'][:, :, 3] > 0, sW, axis=1))
    blade = np.zeros_like(legs)
    for r in range(N):
        xs = np.nonzero(s_front[r])[0]; zs = np.nonzero(s_side[r])[0]
        if len(xs) and len(zs):
            # keep it a blade: as deep as it is wide in the front picture, centred on the side picture
            zc = zs.mean(); w = max(1, min(len(zs), 3))
            for x in xs:
                for zz in range(int(round(zc - w / 2)), int(round(zc + w / 2))):
                    if 0 <= zz < N: blade[r, x, zz] = True
    for r, x, z in zip(*np.nonzero(blade)):
        c = sword.pixel('S', r, x, reach=2)
        M.col[r, x, z] = c if c is not None else (150, 150, 160, 255); M.part[r, x, z] = 6
    return M, full
