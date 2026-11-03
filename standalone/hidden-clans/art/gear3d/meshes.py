# Smooth 3D gear for the 2D sprite units (python3 meshes.py OUT.json): every weapon, shield and helmet style of the
# 64 px gear (art/enhance/wearables64.py), modelled from the same measurements in the picture's pixels, so a piece
# is the size and shape of the one drawn today. Round parts (grips, hafts, pommels, mace heads, domes, rims) are
# smooth-shaded; blade bevels, axe heads and hammer faces keep crisp edges.
#
# Frames (pixels): a weapon's origin is the fist on its grip, x up the weapon (t), y toward its edge or head (s), z
# across its flat (n). A shield's origin is the forearm: x across, y up, z out of its face. A helmet's origin is the
# middle of the head (the Human head is 23 px across, 21 tall, 19 front to back): x to the wearer's right, y up, z
# forward. The page turns and places them (gear3d.js).
#
# Each vertex carries a material code; the page colours it from the piece's tier (TIERS below, the 2D ramps).
import base64, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'enhance'))
import wearables64 as w   # noqa: E402

MAT = dict(metal=0, bright=1, fit=2, wood=3, grip=4, dark=5, string=6, red=7, blue=8, gold=9, horn=10, feather=11,
           plume=12, wooddark=13, back=14, fuller=15, gripdark=16, rivet=17,
           # the magic pieces' own stuff, the same whatever the piece's tier (wearables64's ramps of those names)
           crystal=18, orb=19, bone=20, leaf=21, chitin=22, eye=23, dbone=24, dhorn=25, ember=26, greenwood=27,
           # work: rough stone, ore, sackcloth, a fish's scales (the same whatever the piece's tier)
           rock=28, ore=29, sack=30, fish=31)
METALLIC = (0, 1, 2, 9, 15, 17, 18, 19)   # what shines like metal (the page's glint and sky reflection); crystal and orb gleam


def nz(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n < 1e-9, 1, n)


class Mesh:
    """A triangle soup: three vertices a triangle, each with a normal and a material."""

    def __init__(self):
        self.P, self.N, self.M = [], [], []

    def tri(self, a, b, c, m, na=None, nb=None, nc=None):
        a, b, c = (np.asarray(x, float) for x in (a, b, c))
        if na is None:
            fn = np.cross(b - a, c - a)
            if np.linalg.norm(fn) < 1e-12:
                return
            na = nb = nc = nz(fn)
        self.P += [a, b, c]
        self.N += [nz(na), nz(nb), nz(nc)]
        self.M += [m, m, m]

    def quad(self, a, b, c, d, m, ns=None):
        if ns is None:
            self.tri(a, b, c, m); self.tri(a, c, d, m)
        else:
            self.tri(a, b, c, m, ns[0], ns[1], ns[2]); self.tri(a, c, d, m, ns[0], ns[2], ns[3])

    def add(self, o):
        self.P += o.P; self.N += o.N; self.M += o.M
        return self

    def outward(self, ref):
        """Flat normals turned away from ref(point) (a point inside the part)."""
        for i in range(0, len(self.P), 3):
            c = (self.P[i] + self.P[i + 1] + self.P[i + 2]) / 3
            if np.dot(self.N[i], c - ref(c)) < 0:
                for k in range(3):
                    self.N[i + k] = -self.N[i + k]
        return self

    def moved(self, R=None, t=(0, 0, 0)):
        o = Mesh()
        R = np.eye(3) if R is None else np.asarray(R, float)
        o.P = [R @ p + np.asarray(t, float) for p in self.P]
        o.N = [R @ n for n in self.N]
        o.M = list(self.M)
        return o

    def mirrored(self, axis):
        o = Mesh()
        S = np.ones(3); S[axis] = -1
        for i in range(0, len(self.P), 3):   # mirroring flips the winding: swap two corners
            for k in (0, 2, 1):
                o.P.append(self.P[i + k] * S); o.N.append(self.N[i + k] * S); o.M.append(self.M[i + k])
        return o


def surf(G, m, ref, closed=True, smooth=True, mats=None):
    """A grid of points G (rows, cols, 3) as a surface; normals averaged over the faces round each point (a row
    whose points all meet, a pole, gets one normal), turned away from ref(point)."""
    G = np.asarray(G, float)
    R, C = G.shape[:2]
    cols = C if closed else C - 1
    acc = np.zeros_like(G)
    fns = {}
    for i in range(R - 1):
        for j in range(cols):
            j1 = (j + 1) % C
            a, b, c, d = G[i, j], G[i, j1], G[i + 1, j1], G[i + 1, j]
            fn = np.cross(c - a, b - d)
            if np.linalg.norm(fn) < 1e-12:
                fn = np.cross(b - a, d - a)
            ctr = (a + b + c + d) / 4
            if np.dot(fn, ctr - ref(ctr)) < 0:
                fn = -fn
            fns[(i, j)] = fn
            for (y, x) in ((i, j), (i, j1), (i + 1, j1), (i + 1, j)):
                acc[y, x] += fn
    for i in range(R):   # poles
        if np.ptp(G[i], axis=0).max() < 1e-6:
            acc[i] = acc[i].sum(0)
    Nn = nz(acc)
    out = Mesh()
    for (i, j), fn in fns.items():
        j1 = (j + 1) % C
        idx = [(i, j), (i, j1), (i + 1, j1), (i + 1, j)]
        pts = [G[y, x] for y, x in idx]
        mm = mats(i, j) if mats else m
        if smooth:
            out.quad(*pts, mm, [Nn[y, x] for y, x in idx])
        else:
            out.quad(*pts, mm, [nz(fn)] * 4)
    return out


# ---------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------

def lathe(prof, m, seg=12, sx=1.0, sy=1.0, caps=True, mats=None):
    """Turned about the x axis: prof [(x, radius)]; sx, sy stretch the ring across y and z; mats(row, col) a band's material."""
    ph = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    G = np.array([[[x, r * sx * np.cos(p), r * sy * np.sin(p)] for p in ph] for x, r in prof])
    out = surf(G, m, lambda p: np.array([p[0], 0, 0]), mats=mats)
    if caps:
        for k, sgn in ((0, -1), (-1, 1)):
            x, r = prof[k]
            if r > 1e-6:
                c = np.array([x, 0, 0])
                for j in range(seg):
                    out.tri(c, G[k, j], G[k, (j + 1) % seg], m, *([np.array([sgn, 0, 0])] * 3))
    return out


def ellipsoid(c, r, m, seg=14, rings=9, mats=None):
    c, r = np.asarray(c, float), np.asarray(r, float)
    th = np.linspace(0, np.pi, rings + 1)
    ph = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    G = np.array([[c + r * np.array([np.cos(t), np.sin(t) * np.cos(p), np.sin(t) * np.sin(p)]) for p in ph] for t in th])
    return surf(G, m, lambda p: c, mats=mats)


def frames_along(path):
    """Unit tangents and a parallel-transported normal along a polyline."""
    path = np.asarray(path, float)
    T = nz(np.gradient(path, axis=0))
    up = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([0, 1.0, 0])
    N = [nz(up - T[0] * np.dot(up, T[0]))]
    for i in range(1, len(path)):
        n = N[-1] - T[i] * np.dot(N[-1], T[i])
        N.append(nz(n))
    N = np.array(N)
    B = np.cross(T, N)
    return T, N, B


def tube(path, radii, m, seg=10, side=None, flat=1.0, caps=True):
    """A tube along path, radii per point; side: a fixed direction the tube is flattened across (flat < 1)."""
    path = np.asarray(path, float)
    radii = np.broadcast_to(np.asarray(radii, float), (len(path),))
    T, N, B = frames_along(path)
    if side is not None:
        side = nz(side)
        N = nz(side - T * (T @ side)[:, None])
        B = np.cross(T, N)
    ph = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    G = np.array([[path[i] + radii[i] * (np.cos(p) * N[i] * flat + np.sin(p) * B[i]) for p in ph] for i in range(len(path))])

    def ref(p):
        i = int(np.argmin(np.linalg.norm(path - p, axis=1)))
        return path[i]
    out = surf(G, m, ref)
    if caps:
        for k, sgn in ((0, -1), (-1, 1)):
            if radii[k] > 1e-6:
                for j in range(seg):
                    out.tri(path[k], G[k, j], G[k, (j + 1) % seg], m, *([T[k] * sgn] * 3))
    return out


def box(c, h, m, R=None):
    """A box of half sizes h at c (turned by R), flat faces."""
    c, h = np.asarray(c, float), np.asarray(h, float)
    R = np.eye(3) if R is None else np.asarray(R, float)
    P = lambda sx, sy, sz: c + R @ (h * np.array([sx, sy, sz]))
    out = Mesh()
    for ax in range(3):
        for sg in (-1, 1):
            corners = []
            for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                s = [0, 0, 0]; s[ax] = sg; s[(ax + 1) % 3] = u; s[(ax + 2) % 3] = v
                corners.append(P(*s))
            n = np.zeros(3); n[ax] = sg
            out.quad(*corners, m, [R @ n] * 4)
    return out


def bar(a, b, half_w, half_h, m, up=(0, 0, 1)):
    """A box from point a to point b, half_w across and half_h along up."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    x = nz(b - a); z = nz(np.asarray(up, float) - x * np.dot(up, x)); y = np.cross(z, x)
    return box((a + b) / 2, (np.linalg.norm(b - a) / 2, half_w, half_h), m, np.stack([x, y, z], 1))


def rivet(c, r=0.55, n=None):
    """A round rivet head at c, its dome toward n (default: away from the origin's axis)."""
    return ellipsoid(c, [r, r, r], MAT['rivet'], seg=6, rings=2)


def wrap(t0, t1, r, bands=8, seg=10):
    """A leather binding from t0 to t1 round a grip or haft: ridged turns in two shades."""
    prof = []
    for i in range(bands * 2 + 1):
        t = t0 + (t1 - t0) * i / (bands * 2)
        prof.append((t, r * (1.0 if i % 2 == 0 else 1.09)))
    return lathe(prof, MAT['grip'], seg=seg, mats=lambda i, j: MAT['grip'] if (i // 2) % 2 == 0 else MAT['gripdark'])


def blade(sections, m, m_edge, back=False, fuller_to=None):
    """A blade lofted through hexagonal sections [(t, s_mid, half width, half thickness)], flat-shaded: two bevels
    each side meeting at the edges (the edge bevels in m_edge). back: one edge only (the s<0 side is a flat spine)."""
    out = Mesh()
    ring = lambda t, s0, wd, th: [np.array(p) for p in (
        (t, s0 + wd, 0), (t, s0 + wd * 0.38, th), (t, s0 - (wd * 0.6 if back else wd * 0.38), th),
        (t, s0 - (wd * 0.75 if back else wd), 0 if not back else 0), (t, s0 - (wd * 0.6 if back else wd * 0.38), -th),
        (t, s0 + wd * 0.38, -th))]
    rings = [ring(*s) for s in sections]
    edge_faces = {0, 5} if back else {0, 5, 2, 3}
    for a, b in zip(rings, rings[1:]):
        for k in range(6):
            k1 = (k + 1) % 6
            mm = m_edge if k in edge_faces else m
            if fuller_to is not None and k in (1, 4) and b[0][0] <= fuller_to:   # the groove down the middle
                mm = MAT['fuller']
            out.quad(a[k], b[k], b[k1], a[k1], mm)
    c = np.mean(rings[0], 0)
    for k in range(6):
        out.tri(c, rings[0][(k + 1) % 6], rings[0][k], m)
    mid = lambda p: np.array([p[0], np.interp(p[0], [s[0] for s in sections], [s[1] for s in sections]), 0])
    return out.outward(mid)


def extrude(poly, half, m, side_m=None, side_of=None):
    """A flat shape (poly: [(x, y)] round its outline) given thickness: half(x, y) each side of z = 0. Top and
    bottom fanned from the middle; side_of(i) picks a side wall's material (an axe's cutting edge)."""
    poly = [np.asarray(p, float) for p in poly]
    c2 = np.mean(poly, 0)
    hc = half(*c2)
    top, bot = Mesh(), Mesh()
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ha, hb = half(*a), half(*b)
        top.tri([*c2, hc], [*a, ha], [*b, hb], m)
        bot.tri([*c2, -hc], [*b, -hb], [*a, -ha], m)
        top.quad([*a, ha], [*a, -ha], [*b, -hb], [*b, hb], side_of(i) if side_of else (side_m if side_m is not None else m))
    out = top.add(bot)
    return out.outward(lambda p: np.array([c2[0], c2[1], 0]))


def sweep_profile(path2d, prof_fn, m):
    """For a shape drawn as a closed outline in (x, y): unused helper slot."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# weapons (wearables64.weapon_layer's numbers)
# ---------------------------------------------------------------------------

# The drawn pieces carry a dark outline a pixel wide each side; the 3D ones have none, so round and flat parts are
# made that much fuller (OUT) to read the same size at game zoom.
OUT = 0.55
GRIP_R = 1.05 + OUT


def hilt(grip_len, guard, pommel=True):
    o = wrap(-grip_len, 0.6, GRIP_R, bands=max(3, int(grip_len)), seg=10)
    # the cross-guard: its arms swept a little toward the blade, a block where it meets the blade
    ss = np.linspace(-guard, guard, 7)
    o.add(tube([[1.3 + 0.9 * (abs(v) / guard) ** 2, v, 0] for v in ss], [0.85, 1.0, 1.1, 1.2, 1.1, 1.0, 0.85], MAT['fit'], seg=8, side=(1, 0, 0), flat=0.9))
    for sg in (-1, 1):
        o.add(ellipsoid([2.2, sg * guard, 0], [1.05, 1.05, 1.05], MAT['fit'], seg=8, rings=4))
    o.add(box([1.4, 0, 0], [0.9, 1.6, 0.95], MAT['fit']))
    if pommel:
        o.add(ellipsoid([-grip_len - 1.2, 0, 0], [1.7, 2.1, 1.6], MAT['fit'], seg=10, rings=6))
        o.add(ellipsoid([-grip_len - 3.0, 0, 0], [0.7, 0.8, 0.8], MAT['bright'], seg=6, rings=3))
        o.add(lathe([(-grip_len - 0.2, GRIP_R + 0.35), (0.0 - grip_len + 0.4, GRIP_R + 0.35)], MAT['fit'], seg=10))   # the collar
    return o


def sword_blade(t0, t1, wd, curve=0.0, th=0.42):
    wd, th = wd + OUT, th + OUT * 0.35
    secs = []
    n = 14
    for i in range(n + 1):
        t = t0 + (t1 + 1 - t0) * i / n
        taper = min(1.0, max(0.3, (t1 + 1.5 - t) / 6.0))
        ww = wd * taper if i < n else 0.05
        secs.append((t, -curve * (t - t0) ** 2, ww, th * (0.6 + 0.4 * taper) if i < n else 0.05))
    secs.insert(0, (t0 - 0.2, 0.0, wd * 0.95, th))
    return blade(secs, MAT['metal'], MAT['bright'], back=curve > 0, fuller_to=None if curve > 0 else t0 + (t1 - t0) * 0.72)


def haft(t0, t1, r=1.05, grip=True):
    """A wooden haft, bound with leather where the fist holds it (round t = 0) and capped with metal at the foot."""
    r += OUT
    o = lathe([(t0 + 0.9, r * 0.98), (t0 + 2, r), (t1 - 0.6, r), (t1, r * 0.9)], MAT['wood'], seg=10)
    o.add(lathe([(t0, r * 0.6), (t0 + 0.4, r * 1.12), (t0 + 1.4, r * 1.12), (t0 + 2.0, r * 0.98)], MAT['fit'], seg=10))
    if grip:
        o.add(wrap(-3.4, 3.4, r * 1.06, bands=4, seg=10))
    return o


def axe_head(top, k=1, poll=False):
    """One side of an axe head (k=1 toward +s): the 2D shape s <= 9.2 - 0.3 (t - (top - 3))^2, thin at the edge."""
    ts = np.linspace(top - 10, top + 1, 14)
    smax = lambda t: 9.2 - 0.3 * (t - (top - 3)) ** 2
    ok = [t for t in ts if smax(t) > 1.2]
    inner = [(t, 0.6) for t in ok]
    outer = [(t, smax(t)) for t in reversed(ok)]
    poly = inner + outer
    half = lambda t, s: 0.4 + 1.25 * max(0.0, 1 - (s - 0.6) / max(0.5, smax(t) - 0.6)) ** 1.3
    nin = len(inner)
    side_of = lambda i: MAT['bright'] if nin - 1 <= i < len(poly) - 1 else MAT['metal']
    o = extrude(poly, half, MAT['metal'], side_of=side_of)
    o.add(lathe([(top - 6.5, 1.55), (top - 5.5, 1.75), (top + 0.5, 1.75), (top + 1.3, 1.5)], MAT['metal'], seg=10))   # the eye round the haft
    if poll:
        o.add(box([top - 3.5, -2.3, 0], [1.5, 1.8, 1.1], MAT['metal']))
    for tt in (top - 4.6, top - 0.6):
        for zz in (-1.8, 1.8):
            o.add(rivet([tt, 0.0, zz], 0.45))
    if k < 0:
        o = o.mirrored(1)
    return o


def weapon(style):
    o = Mesh()
    if style == 'arming sword':
        o.add(hilt(5, 4.5)).add(sword_blade(2.0, 25, 1.8))
    elif style == 'longsword':
        o.add(hilt(8, 5.5)).add(sword_blade(2.0, 33, 2.0, th=0.46))
    elif style == 'scimitar':
        o.add(hilt(5, 3.5)).add(sword_blade(2.0, 24, 2.3, curve=0.014))
    elif style == 'dagger':
        o.add(hilt(4, 3.0)).add(sword_blade(1.8, 12, 1.5, th=0.4))
    elif style == 'hand axe':
        o.add(haft(-6, 25)).add(axe_head(24, 1, poll=True))
    elif style == 'battle axe':
        o.add(haft(-9, 29)).add(axe_head(28, 1)).add(axe_head(28, -1))
        o.add(ellipsoid([29.6, 0, 0], [1.2, 1.2, 1.2], MAT['metal'], seg=8, rings=5))
    elif style == 'warhammer':
        o.add(haft(-7, 21))
        o.add(box([23.5, 0, 0], [4.0, 5.6, 2.6], MAT['metal']))
        for sg in (-1, 1):   # bevelled striking faces
            o.add(box([23.5, sg * 5.9, 0], [3.4, 0.35, 2.2], MAT['bright']))
        o.add(box([23.5, 0, 0], [0.7, 5.75, 2.75], MAT['gold']))
        for yy in (-3.6, 0.0, 3.6):
            for zz in (-2.85, 2.85):
                o.add(rivet([23.5, yy, zz], 0.5))
        o.add(lathe([(27.5, 1.2), (29.5, 0.3), (29.8, 0.0)], MAT['metal'], seg=8))
    elif style == 'mace':
        o.add(haft(-5, 18))
        o.add(ellipsoid([22.0, 0, 0], [4.4, 3.2, 3.2], MAT['metal'], seg=14, rings=9))
        for a in np.linspace(0, 2 * np.pi, 6, endpoint=False):   # flanges round the head
            R = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
            fl = extrude([(18.6, 2.0), (20.5, 5.2), (23.5, 5.2), (25.4, 2.0)], lambda x, y: 0.42 * (1.2 - (y - 2) / 6), MAT['bright'])
            o.add(fl.moved(np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]) @ np.eye(3)).moved(R))
        o.add(lathe([(26.0, 1.1), (27.6, 1.0), (28.6, 0.0)], MAT['metal'], seg=8))
    elif style == 'morning star':
        o.add(haft(-5, 17))
        o.add(ellipsoid([21.5, 0, 0], [4.2, 4.2, 4.2], MAT['metal'], seg=16, rings=10))
        dirs = []
        g = (1 + 5 ** 0.5) / 2
        for v in ((0, 1, g), (0, -1, g), (0, 1, -g), (0, -1, -g), (1, g, 0), (-1, g, 0), (1, -g, 0), (-1, -g, 0),
                  (g, 0, 1), (-g, 0, 1), (g, 0, -1), (-g, 0, -1)):
            dirs.append(nz(v))
        for d in dirs:
            if d[0] < -0.8:
                continue   # where the haft goes in
            c = np.array([21.5, 0, 0])
            o.add(tube([c + d * 3.6, c + d * 5.4, c + d * 7.0], [0.95, 0.5, 0.04], MAT['bright'], seg=6))
    elif style == 'spear':
        o.add(haft(-13.5, 39, 0.95))
        o.add(lathe([(-13.6, 1.3), (-15, 1.0), (-18.5, 0.05)], MAT['metal'], seg=8))   # the butt spike
        o.add(wrap(32.5, 35.8, 0.95 + OUT + 0.1, bands=3))
        o.add(lathe([(35.6, 1.55), (37, 1.95), (39.5, 1.6)], MAT['metal'], seg=10))
        secs = [(39 + 12 * i / 12, 0.0, 2.8 * np.sin(np.pi * (i / 12)) ** 0.7 + 0.3 if i < 12 else 0.05, 0.55 if i < 12 else 0.05)
                for i in range(13)]
        o.add(blade(secs, MAT['metal'], MAT['bright']))
    elif style == 'halberd':
        o.add(haft(-14, 40, 0.95))
        ts = np.linspace(28, 38, 12)
        smax = lambda t: 7.5 - 0.25 * (t - 33) ** 2
        ok = [t for t in ts if smax(t) > 1.0]
        poly = [(t, 0.6) for t in ok] + [(t, smax(t)) for t in reversed(ok)]
        nin = len(ok)
        o.add(extrude(poly, lambda t, s: 0.25 + 0.8 * max(0, 1 - (s - 0.6) / max(0.5, smax(t) - 0.6)), MAT['metal'],
                      side_of=lambda i: MAT['bright'] if nin - 1 <= i < len(poly) - 1 else MAT['metal']))
        o.add(blade([(38, 0, 1.5, 0.6), (41, 0, 1.4, 0.55), (44, 0, 1.0, 0.45), (46.5, 0, 0.5, 0.3), (47.5, 0, 0.05, 0.05)],
                    MAT['metal'], MAT['bright']))
        o.add(extrude([(31, -0.5), (33, -0.5), (33.4, -2.5), (31.6, -4.6)], lambda t, s: 0.45, MAT['metal']))
        o.add(lathe([(27.4, 1.15), (28, 1.35), (38.4, 1.35), (39, 1.15)], MAT['metal'], seg=10))
    elif style == 'pickaxe':
        o.add(haft(-6, 22))
        ss = np.linspace(-10.5, 10.5, 15)
        path = [[23.0 - 0.04 * s * s, s, 0] for s in ss]   # an arch over the haft, its points curving down toward the hand (the 2D pick's)
        rad = [1.9 * min(1, max(0.12, 1 - abs(s) / 11.5)) for s in ss]
        rad[0] = rad[-1] = 0.05
        o.add(tube(path, rad, MAT['metal'], seg=8, side=(1, 0, 0), flat=0.85))
        o.add(lathe([(20.8, 1.6), (21.5, 1.85), (24.0, 1.85), (24.6, 1.5)], MAT['metal'], seg=10))
    elif style == 'bow' or style.startswith('bow@'):
        o.add(bow(float(style[4:]) if style.startswith('bow@') else 0.0))
    elif style == 'hammer':   # a smith's and builder's hammer: a short haft, a square face, a wedge peen
        o.add(haft(-5, 13, 0.85))
        o.add(box([14.3, 0.8, 0], [1.7, 3.3, 1.7], MAT['metal']))
        o.add(box([14.3, 4.4, 0], [1.9, 0.35, 1.9], MAT['bright']))   # the striking face
        o.add(extrude([(12.7, -2.4), (15.9, -2.4), (14.6, -5.6), (14.0, -5.6)], lambda t, y: 1.5 - 0.22 * (-y - 2.4), MAT['metal']))   # the peen
        o.add(lathe([(12.0, 1.2), (12.6, 1.35), (16.0, 1.35), (16.4, 1.1)], MAT['fit'], seg=8))
    elif style == 'harpoon':   # the game's Harpoon (spear fishing): a long haft, a narrow head with two barbs back
        o.add(haft(-14, 34, 0.9))
        o.add(lathe([(33.6, 1.3), (34.6, 1.55), (36.5, 1.2)], MAT['metal'], seg=10))
        o.add(blade([(36 + 9 * i / 9, 0.0, 1.6 * np.sin(np.pi * (i / 9)) ** 0.6 + 0.25 if i < 9 else 0.05, 0.5 if i < 9 else 0.05) for i in range(10)], MAT['metal'], MAT['bright']))
        for k in (-1, 1):   # the barbs, swept back from the head
            o.add(extrude([(37.5, 0.3 * k), (39.0, 0.6 * k), (36.2, 2.7 * k), (35.9, 2.2 * k)][::k], lambda t, y: 0.35, MAT['bright']))
        o.add(lathe([(-14.2, 1.1), (-15.4, 0.6)], MAT['metal'], seg=8))
    elif style == 'spade':   # the farmer's wooden spade: a long haft, a T grip, a flat blade
        o.add(haft(-6, 26, 0.85, grip=False))
        o.add(bar(np.array([-6.8, -2.6, 0]), np.array([-6.8, 2.6, 0]), 0.9, 0.9, MAT['wood']))
        o.add(extrude([(25.5, -3.3), (34.5, -3.0), (36.0, 0.0), (34.5, 3.0), (25.5, 3.3)], lambda t, y: 0.45, MAT['metal'], side_of=lambda i: MAT['bright'] if i in (1, 2, 3) else MAT['metal']))
    elif style == 'fishing rod':   # a long thin rod, a cork grip, rings for the line, a reel at the grip
        o.add(lathe([(-9, 1.0), (-8, 1.15), (4, 1.05), (12, 0.75), (30, 0.45), (44, 0.22), (45, 0.0)], MAT['wood'], seg=8))
        o.add(wrap(-7.5, 3.0, 1.35, bands=5, seg=8))
        for tt, r in ((14, 0.9), (24, 0.75), (34, 0.6), (42, 0.45)):   # the line's rings
            o.add(tube([[tt, 0.4, 0], [tt, 0.4 + r * 2, 0]], [0.18, 0.18], MAT['fit'], seg=5))
        o.add(lathe([(4.5, 0.0), (4.6, 2.0), (6.6, 2.0), (6.7, 0.0)], MAT['fit'], seg=10, sx=1.0, sy=1.0).moved(np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0.0]]), (0, -2.2, 0)))   # the reel
    else:
        raise KeyError(style)
    # the fist a little down the grip, not at its top, as the 2D weapons are held (wearables64.GRIP_SHIFT): a sword
    # sits that much higher in the hand
    sh = w.GRIP_SHIFT.get(style, 0.0)
    return o.moved(t=(sh, 0, 0)) if sh else o


# ---------------------------------------------------------------------------
# work: what is carried (loads) and, for the animation arena, what is worked at (props); x along a load's length
# ---------------------------------------------------------------------------
LOADS = ['log', 'stone', 'ore', 'sack', 'barrel', 'fish', 'net', 'piton', 'coil']
PROPS = ['rock', 'trunk', 'anvil', 'bush', 'herb', 'mushrooms', 'crop', 'cliff']


def rough(c, r, m, seed, bumps=0.22, seg=9, rings=6):
    """A faceted lump (stone, ore): an ellipsoid pushed in and out in flat facets (no smooth shading)."""
    rng = np.random.default_rng(seed)
    o = ellipsoid(c, r, m, seg=seg, rings=rings)
    keep = {}
    P = []
    for p in o.P:
        k = tuple(np.round(p, 3))
        if k not in keep:
            keep[k] = 1 + rng.uniform(-bumps, bumps)
        P.append(c + (p - c) * keep[k])
    out = Mesh()
    for i in range(0, len(P), 3):
        out.tri(P[i], P[i + 1], P[i + 2], o.M[i])
    return out.outward(lambda p: np.asarray(c, float))


def load(style):
    o = Mesh()
    if style == 'log':   # bark round, the cut ends pale
        o.add(lathe([(-12, 0.0), (-12, 3.4), (12, 3.4), (12, 0.0)], MAT['wooddark'], seg=12, caps=False))
        for x in (-12, 12):
            o.add(lathe([(x, 0.0), (x, 3.3)] if x < 0 else [(x, 3.3), (x, 0.0)], MAT['back'], seg=12, caps=False))
        for x, a in ((-4, 0.6), (5, 2.4)):   # knots
            o.add(ellipsoid([x, 3.3 * np.cos(a), 3.3 * np.sin(a)], [0.9, 0.7, 0.7], MAT['wood'], seg=6, rings=4))
    elif style == 'stone':
        o.add(rough(np.zeros(3), [5.2, 3.6, 4.2], MAT['rock'], 7))
    elif style == 'ore':
        o.add(rough(np.zeros(3), [3.6, 3.0, 3.2], MAT['rock'], 11))
        for k in range(5):
            a = k * 1.3
            o.add(rough(np.array([np.cos(a) * 2.6, np.sin(a * 1.7) * 2.0, np.sin(a) * 2.4]), [1.1, 0.9, 1.0], MAT['ore'], 20 + k, seg=6, rings=4))
    elif style == 'sack':   # a filled sack, tied at the neck
        o.add(lathe([(-6.5, 0.0), (-6.2, 3.2), (-3, 4.6), (2, 4.4), (4.5, 3.2), (5.5, 1.4), (6.2, 0.9), (7.4, 1.4), (7.6, 0.0)], MAT['sack'], seg=12))
        o.add(lathe([(5.4, 1.5), (5.8, 1.6), (6.4, 1.5)], MAT['string'], seg=8))
    elif style == 'barrel':   # staves bulging round, two iron hoops, a lid (x up its height)
        o.add(lathe([(-6.0, 0.0), (-6.0, 3.8), (-3.0, 4.6), (0, 4.9), (3.0, 4.6), (6.0, 3.8), (6.0, 0.0)], MAT['wood'], seg=14,
                    mats=lambda i, j: MAT['wood'] if j % 2 == 0 else MAT['wooddark']))
        for x, r in ((-4.2, 4.35), (4.2, 4.35)):
            o.add(lathe([(x - 0.6, r + 0.05), (x, r + 0.25), (x + 0.6, r + 0.05)], MAT['metal'], seg=14, caps=False))
    elif style == 'net':   # a fishing net bundled up in the hands: folds of cord, lead weights on its edge
        o.add(rough(np.zeros(3), [4.0, 3.0, 3.0], MAT['string'], 5, bumps=0.25, seg=10, rings=6))
        for k in range(6):
            a = k * 1.05
            o.add(ellipsoid([3.2 * np.cos(a), -2.2, 3.0 * np.sin(a)], [0.45, 0.45, 0.45], MAT['dark'], seg=6, rings=3))
    elif style == 'piton':   # the climbing gear's piton: a spike driven into the rock (x out of it), an eye for the rope
        o.add(lathe([(-3.0, 0.0), (-2.6, 0.45), (0.0, 0.7), (0.4, 0.5)], MAT['metal'], seg=6))
        o.add(tube([[0.6, 0, -0.9], [1.6, 0, -0.7], [1.9, 0, 0], [1.6, 0, 0.7], [0.6, 0, 0.9]], 0.3, MAT['bright'], seg=5, caps=False))
    elif style == 'coil':   # its rope, coiled on the shoulder
        for k in range(3):
            o.add(tube([[np.cos(a) * 3.2, np.sin(a) * 3.8, k * 0.55 - 0.55] for a in np.linspace(0, 2 * np.pi, 17)], 0.55, MAT['string'], seg=5, caps=False))
    elif style == 'fish':
        o.add(ellipsoid([0, 0, 0], [4.2, 1.6, 0.9], MAT['fish'], seg=12, rings=7))
        o.add(extrude([(-3.8, 0), (-6.2, 1.8), (-6.2, -1.8)], lambda x, y: 0.25, MAT['fish']))   # the tail
        o.add(ellipsoid([3.0, 0.45, 0.6], [0.35, 0.35, 0.3], MAT['dark'], seg=6, rings=3))
        o.add(ellipsoid([3.0, 0.45, -0.6], [0.35, 0.35, 0.3], MAT['dark'], seg=6, rings=3))
    return o


def prop(style):
    o = Mesh()
    if style == 'rock':   # a rock face to mine (y up)
        o.add(rough(np.array([0, 9, 0]), [13, 10, 11], MAT['rock'], 3, bumps=0.18, seg=11, rings=7))
        o.add(rough(np.array([6, 4, 6]), [2.2, 1.8, 2.0], MAT['ore'], 9, seg=6, rings=4))
    elif style == 'trunk':   # a tree's trunk to chop, and a stub of branch
        o.add(lathe([(0, 5.6), (2, 4.4), (30, 3.9), (31, 0.0)], MAT['wood'], seg=12,
                    mats=lambda i, j: MAT['wood'] if (i + j) % 3 else MAT['wooddark']).moved(np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1.0]])))   # bark, streaked
        o.add(tube([[0, 22, 0], [5, 26, 1], [8, 27, 1.5]], [1.3, 0.9, 0.2], MAT['wood'], seg=6))
    elif style == 'bush':   # a berry bush: a mound of leaves, berries dotted on it
        rng = np.random.default_rng(4)
        for k in range(9):
            a = k * 0.7
            o.add(rough(np.array([np.cos(a) * 4.5 * (k % 3) / 2, 6 + (k % 3) * 2.2, np.sin(a) * 4.5 * (k % 3) / 2]), [5.2, 4.2, 5.2], MAT['leaf'], 30 + k, seg=8, rings=5))
        for k in range(16):
            a, h = rng.uniform(0, 2 * np.pi), rng.uniform(3, 11)
            o.add(ellipsoid([np.cos(a) * 7.6, h, np.sin(a) * 7.6], [0.75, 0.75, 0.75], MAT['red'], seg=6, rings=4))
    elif style == 'herb':   # a low wild herb: a tuft of leaves, small flowers
        for k in range(7):
            a = k * 0.9
            o.add(tube([[0, 0, 0], [np.cos(a) * 1.5, 3.2, np.sin(a) * 1.5], [np.cos(a) * 3.0, 4.5, np.sin(a) * 3.0]], [0.5, 0.45, 0.1], MAT['leaf'], seg=5))
            o.add(ellipsoid([np.cos(a) * 3.0, 4.8, np.sin(a) * 3.0], [0.5, 0.5, 0.5], MAT['feather'], seg=6, rings=3))
    elif style == 'mushrooms':   # a cluster of mushrooms on the ground
        for k, (x, z, h, r) in enumerate(((0, 0, 4.2, 2.4), (3.2, 1.4, 3.0, 1.7), (-2.4, 2.2, 2.4, 1.4), (1.2, -2.8, 2.0, 1.2))):
            o.add(lathe([(0, 0.6), (h - 0.5, 0.5)], MAT['bone'], seg=8).moved(np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1.0]]), (x, 0, z)))
            o.add(ellipsoid([x, h, z], [r, r * 0.55, r], MAT['red'] if k % 2 == 0 else MAT['wooddark'], seg=10, rings=5))
    elif style == 'crop':   # a row of ripe wheat on tilled earth
        o.add(box([0, 0.3, 0], [10, 0.4, 3.2], MAT['wooddark']))
        for x in np.linspace(-8, 8, 9):
            for z in (-1.6, 1.6):
                o.add(tube([[x, 0.5, z], [x + 0.4, 6.5, z], [x + 0.8, 9.5, z]], [0.25, 0.22, 0.15], MAT['gold'], seg=4))
                o.add(ellipsoid([x + 0.9, 10.2, z], [0.55, 1.4, 0.55], MAT['gold'], seg=6, rings=4))
    elif style == 'cliff':   # a cliff face to climb, two tiles high (y up; its face toward -x)
        o.add(rough(np.array([20.0, 60, 0]), [20, 62, 40], MAT['rock'], 40, bumps=0.07, seg=14, rings=12))   # one tall faceted block
        for k, (y, z) in enumerate(((22, -14), (58, 10), (92, -6))):   # a few ledges standing out of it
            o.add(rough(np.array([3.0, y, z]), [5, 4, 9], MAT['rock'], 50 + k, bumps=0.15, seg=8, rings=5))
    elif style == 'anvil':
        o.add(box([0, 1.5, 0], [4.5, 1.5, 3.2], MAT['wooddark']))   # its block
        o.add(box([0, 4.6, 0], [2.0, 1.6, 1.7], MAT['metal']))
        o.add(box([0, 7.0, 0], [5.0, 0.9, 2.2], MAT['metal']))
        o.add(box([0, 8.0, 0], [4.6, 0.15, 2.0], MAT['bright']))
        o.add(lathe([(5.0, 0.9), (6.5, 0.7), (9.0, 0.05)], MAT['metal'], seg=8).moved(np.eye(3), (0, 7.0, 0)))   # the horn
    return o


BOW_PULL = 16.0   # pixels the string comes back at full draw (about half the bow's length, as a real bow is drawn)


def bow(draw=0.0):
    """A recurve bow upright in the fist (the grip at the origin, x up its limbs, y toward the string's far side):
    limbs bent back, tips curling forward, the string taut; draw 0 to 1 pulls the string back to the archer
    (toward -y) and bends the limbs further."""
    o = Mesh()
    L = 17.0
    ts = np.linspace(-L, L, 23)
    bend = lambda t: (0.02 + 0.022 * draw) * t * t - max(0.0, abs(t) - (L - 3.5)) * 1.3
    path = [[t, 2.0 - bend(t), 0] for t in ts]
    rad = [max(0.55, min(1.5, 1.5 - abs(t) / L * 0.9)) for t in ts]
    o.add(tube(path, rad, MAT['wood'], seg=8, side=(0, 1, 0), flat=0.7))
    tip_t = L - 0.6 - 2.0 * draw
    tip_s = 2.0 - bend(tip_t)
    o.add(tube([[-tip_t, tip_s, 0], [0, -1.6 - BOW_PULL * draw, 0], [tip_t, tip_s, 0]], [0.22, 0.22, 0.22], MAT['string'], seg=5))
    o.add(lathe([(-2.6, 1.55), (-2.0, 1.75), (2.0, 1.75), (2.6, 1.55)], MAT['grip'], seg=10, sx=1.0, sy=0.9).moved(t=(0, 2.0, 0)))
    for sg in (-1, 1):
        o.add(ellipsoid([sg * (tip_t + 0.3), tip_s + 0.2, 0], [0.8, 0.6, 0.6], MAT['fit'], seg=8, rings=5))
    return o


def arrow():
    """An arrow along x, its point at +x, its nock at the origin (on the string)."""
    o = lathe([(0.0, 0.5), (0.6, 0.42), (24.0, 0.42), (24.4, 0.5)], MAT['wood'], seg=6)
    o.add(lathe([(24.0, 0.7), (25.0, 1.2), (28.5, 0.05)], MAT['metal'], seg=6))   # the head
    for a in np.linspace(0, 2 * np.pi, 3, endpoint=False):   # three fletches
        R = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
        o.add(extrude([(1.0, 0.4), (6.5, 0.4), (5.0, 2.2), (1.6, 2.0)], lambda x, y: 0.08, MAT['feather']).moved(R))
    o.add(lathe([(-0.6, 0.55), (0.0, 0.6), (0.8, 0.55)], MAT['dark'], seg=6))   # the nock
    return o


WEAPONS = ['dagger', 'arming sword', 'longsword', 'scimitar', 'hand axe', 'battle axe', 'warhammer', 'mace', 'morning star',
           'spear', 'halberd', 'pickaxe', 'bow', 'hammer', 'fishing rod', 'harpoon', 'spade']


# ---------------------------------------------------------------------------
# magic: the staffs (wearables64.staff_solid) and the enchanted weapons on their base weapons
# ---------------------------------------------------------------------------
# A staff stands in the fist (its pole 2.2 as the 2D one), its head round t = 33 (H); s (y) is the way the wearer
# faces, so a skull or a dragon's snout looks ahead. The effects (flames, glows, sparks) are the page's (magicfx.js).
STAFFS = ['crystal staff', 'orb staff', 'skull staff', 'flame staff', 'nature staff', 'dragon staff', 'spider staff']
MAGIC_BASE = {'rune sword': 'longsword', 'flame sword': 'arming sword', 'frost axe': 'battle axe', 'storm spear': 'spear',
              'void blade': 'scimitar', 'holy mace': 'mace'}
# each magic piece's one tier (the colour of its metal): the 2D ones' (wearables64.MAGIC_BASE and staff_solid)
MAGIC_TIER = {'crystal staff': 'silver', 'orb staff': 'gold', 'skull staff': 'iron', 'flame staff': 'iron', 'nature staff': 'wood',
              'dragon staff': 'dragonbone', 'spider staff': 'chitin', 'rune sword': 'runesteel', 'flame sword': 'iron',
              'frost axe': 'ice', 'storm spear': 'silver', 'void blade': 'void', 'holy mace': 'gold'}
MAGIC = STAFFS + list(MAGIC_BASE)
SH = 33.0   # a staff's head
# the game's own special weapons, as the 2D ones (oldlooks64.py): a stock piece in another metal, no effect
SPECIAL = {'soul eater': 'arming sword', 'bloodwhisker': 'spear'}
MAGIC_TIER.update({'soul eater': 'venom', 'bloodwhisker': 'green'})


def bipyramid(t0, tm, t1, r, m, n=6, twist=0.0):
    """A cut crystal: n flat facets up to its widest at tm and n down to points at t0 and t1."""
    o = Mesh()
    ring = [np.array([tm, r * np.cos(twist + 2 * np.pi * k / n), r * np.sin(twist + 2 * np.pi * k / n)]) for k in range(n)]
    lo, hi = np.array([t0, 0, 0.0]), np.array([t1, 0, 0.0])
    for k in range(n):
        a, b = ring[k], ring[(k + 1) % n]
        o.tri(hi, a, b, m); o.tri(lo, b, a, m)
    return o.outward(lambda p: np.array([tm, 0, 0.0]))


def limb_tube(pts, r0, r1, m, seg=6):
    return tube([np.asarray(p, float) for p in pts], list(np.linspace(r0, r1, len(pts))), m, seg=seg)


def around(o, n, start=0.0):
    """n copies of a part turned round the staff's axis."""
    out = Mesh()
    for k in range(n):
        a = start + 2 * np.pi * k / n
        R = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
        out.add(o.moved(R))
    return out


def shaft(t0, t1, r=1.0, gnarl=0.0):
    """A staff's wooden shaft, leather-bound at the fist, a metal shoe at its foot; gnarl: a wandering, knotty one."""
    if not gnarl:
        return haft(t0, t1, r)
    ts = np.linspace(t0, t1, 22)
    path = [[t, gnarl * np.sin(t / 3.0), gnarl * 0.6 * np.cos(t / 4.1)] for t in ts]
    rad = [r + OUT + 0.25 * np.sin(t * 1.3) ** 2 for t in ts]
    o = tube(path, rad, MAT['wood'], seg=9)
    for tk in (t0 + 9, t0 + 21, t0 + 31):   # knots
        i = int(np.argmin(np.abs(ts - tk)))
        o.add(ellipsoid(path[i], [1.3, 1.5, 1.4], MAT['wooddark'], seg=8, rings=5))
    o.add(wrap(-3.4, 3.4, r + OUT + 0.15, bands=4, seg=10))
    return o


def staff(style):
    o = Mesh()
    H = SH
    if style == 'crystal staff':
        o.add(shaft(-12, H - 5))
        prong = limb_tube([[H - 6, 0.8, 0], [H - 4.5, 2.4, 0], [H - 2.5, 3.9, 0], [H - 0.8, 4.0, 0], [H + 0.6, 3.0, 0]], 0.75, 0.35, MAT['metal'])
        o.add(around(prong, 4, np.pi / 4))
        o.add(lathe([(H - 7, 1.4), (H - 6.2, 1.9), (H - 5.2, 1.7)], MAT['bright'], seg=10))
        o.add(bipyramid(H - 5.5, H + 1.0, H + 7.5, 3.3, MAT['crystal'], n=6))
        for k, (tt, a) in enumerate(((H - 2.0, 0.6), (H + 0.5, 2.7), (H - 1.0, 4.6))):   # small crystals at its foot
            sm = bipyramid(-1.2, 0.4, 2.6, 0.9, MAT['crystal'], n=5)
            R = np.array([[np.cos(0.5), -np.sin(0.5), 0], [np.sin(0.5), np.cos(0.5), 0], [0, 0, 1]])   # leaning out
            Ra = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
            o.add(sm.moved(R).moved(t=(tt, 2.0, 0)).moved(Ra))
    elif style == 'orb staff':
        o.add(shaft(-12, H - 5))
        o.add(lathe([(H - 6.5, 1.3), (H - 5.6, 2.1), (H - 4.6, 1.9)], MAT['gold'], seg=10))
        claw = limb_tube([[H - 5.2, 1.5, 0], [H - 3.6, 3.9, 0], [H - 1.4, 4.7, 0], [H + 0.8, 4.2, 0], [H + 2.2, 3.0, 0]], 0.7, 0.3, MAT['gold'])
        o.add(around(claw, 4))
        o.add(ellipsoid([H, 0, 0], [4.2, 4.2, 4.2], MAT['orb'], seg=18, rings=12))
    elif style == 'skull staff':
        o.add(shaft(-12, H - 5))
        o.add(lathe([(H - 7, 1.5), (H - 6, 2.2), (H - 4, 2.2), (H - 3.4, 1.6)], MAT['metal'], seg=10))
        o.add(ellipsoid([H + 0.5, -0.3, 0], [4.4, 3.9, 3.6], MAT['bone'], seg=16, rings=10))
        o.add(box([H - 3.2, 1.0, 0], [1.1, 2.4, 2.6], MAT['bone']))   # the jaw
        for zz in (-1.5, 1.5):
            o.add(ellipsoid([H + 1.2, 3.2, zz], [1.0, 0.7, 0.85], MAT['dark'], seg=8, rings=5))   # eye sockets, ahead
        o.add(ellipsoid([H - 1.0, 3.5, 0], [0.7, 0.5, 0.5], MAT['dark'], seg=6, rings=4))   # the nose
        for zz in np.linspace(-1.6, 1.6, 5):   # teeth
            o.add(box([H - 2.3, 3.45, zz], [0.45, 0.25, 0.28], MAT['bone']))
    elif style == 'flame staff':
        o.add(shaft(-12, H - 4))
        o.add(lathe([(H - 4.6, 1.1), (H - 4.0, 1.5), (H - 1.6, 3.0), (H + 0.6, 5.1), (H + 0.9, 5.3)], MAT['metal'], seg=14, caps=False))
        o.add(lathe([(H + 0.9, 5.3), (H + 0.3, 4.6), (H - 1.4, 2.6)], MAT['dark'], seg=14, caps=False))   # its inside, sooty
        o.add(tube([[H + 0.8, 5.25 * np.cos(a), 5.25 * np.sin(a)] for a in np.linspace(0, 2 * np.pi, 25)], 0.45, MAT['bright'], seg=5, caps=False))
        rng = np.random.default_rng(3)
        for k in range(7):   # coals in the bowl
            a, rr = rng.uniform(0, 2 * np.pi), rng.uniform(0, 2.6)
            o.add(ellipsoid([H - 0.4, rr * np.cos(a), rr * np.sin(a)], [0.9, 1.1, 1.0], MAT['ember'], seg=7, rings=4))
    elif style == 'nature staff':
        o.add(shaft(-12, H - 4, 0.95, gnarl=0.5))
        for k, a in enumerate((0.3, 2.4, 4.5)):   # the branches, forking out and up round the seed
            pts = [[H - 5 + u, 0.2 * (u) ** 1.4 * 0.95, 0] for u in np.linspace(0, 9, 7)]
            br = limb_tube(pts, 0.95, 0.35, MAT['wood'])
            R = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
            o.add(br.moved(R))
            tip = R @ np.array(pts[-1])
            for j, (dt, dr) in enumerate(((-1.5, 0.4), (0.8, 1.2))):   # leaves at each tip
                c = tip + R @ np.array([dt, dr, (j - 0.5) * 1.6])
                Rl = np.array([[np.cos(a + j), -np.sin(a + j), 0], [np.sin(a + j), np.cos(a + j), 0], [0, 0, 1]])
                o.add(ellipsoid([0, 0, 0], [2.7, 1.5, 0.4], MAT['leaf'], seg=10, rings=5).moved(R @ Rl, c))
        o.add(ellipsoid([H, 0, 0], [2.2, 2.2, 2.2], MAT['gold'], seg=12, rings=8))   # the seed
    elif style == 'dragon staff':
        o.add(shaft(-12, H - 4))
        for tb in np.arange(H - 9, H - 4, 2.0):   # horn bands
            o.add(lathe([(tb, 1.5), (tb + 0.5, 1.75), (tb + 1.0, 1.5)], MAT['dhorn'], seg=10))
        o.add(ellipsoid([H + 0.5, -0.5, 0], [3.6, 3.6, 3.0], MAT['dbone'], seg=16, rings=10))   # the cranium
        sn = extrude([(H - 0.8, 1.5), (H + 2.8, 1.5), (H + 2.1, 5.0), (H + 0.8, 8.5), (H - 0.8, 8.5)], lambda t, y: 1.7 - 0.08 * (y - 1.5), MAT['dbone'])
        o.add(sn)   # the snout, ahead
        o.add(extrude([(H - 3.2, 1.5), (H - 1.6, 1.5), (H - 1.6, 7.5), (H - 2.1, 7.5)], lambda t, y: 1.3 - 0.06 * (y - 1.5), MAT['dbone']))   # the jaw
        for y in np.arange(2.6, 7.6, 1.2):   # teeth
            for zz in (-0.9, 0.9):
                o.add(lathe([(H - 1.6, 0.35), (H - 0.7, 0.0)], MAT['bone'], seg=5).moved(t=(0, y, zz)))
        for (a, b, wdt) in (((H + 2.6, -1.0), (H + 7.5, -5.5), 1.3), ((H + 1.5, -2.6), (H + 4.5, -7.0), 1.1)):   # horns swept back
            for zz in (-1.6, 1.6):
                mid = [(a[0] + b[0]) / 2 + 0.8, (a[1] + b[1]) / 2 + 0.4, zz * 1.1]
                o.add(tube([[a[0], a[1], zz], mid, [b[0], b[1], zz * 1.3]], [wdt, wdt * 0.6, 0.08], MAT['dhorn'], seg=7))
        for zz in (-1.6, 1.6):
            o.add(ellipsoid([H + 1.4, 1.0, zz * 1.05], [0.9, 0.9, 0.5], MAT['ember'], seg=8, rings=5))   # eyes, an ember in each
    elif style == 'spider staff':
        o.add(shaft(-12, H - 4))
        for tb in np.arange(H - 9, H - 4, 2.0):   # silk bound round it
            o.add(lathe([(tb, 1.4), (tb + 0.5, 1.6), (tb + 1.0, 1.4)], MAT['string'], seg=10))
        o.add(ellipsoid([H - 0.5, 0, 0], [3.6, 3.0, 3.0], MAT['chitin'], seg=16, rings=10))   # the abdomen
        o.add(ellipsoid([H + 4.0, 0, 0], [2.0, 1.8, 1.8], MAT['chitin'], seg=12, rings=8))    # the head and thorax
        for a0 in (-3.0, -1.0, 1.0, 3.0):
            for k in (-1, 1):
                for zk in (-1, 1):   # four legs a side, front and back pairs, wrapped round the staff
                    o.add(limb_tube([[H + a0 * 0.6 + 1.5, k * 1.6, zk * 1.0], [H + a0 + 1.5, k * 6.2, zk * 2.6], [H + a0 - 2.6, k * 3.6, zk * 3.6]], 0.65, 0.3, MAT['chitin']))
        for zz in (-0.7, 0.7):
            o.add(ellipsoid([H + 5.0, 1.4, zz], [0.45, 0.45, 0.45], MAT['eye'], seg=6, rings=4))
            o.add(ellipsoid([H + 5.6, 1.0, zz * 1.6], [0.3, 0.3, 0.3], MAT['eye'], seg=6, rings=3))
    else:
        raise KeyError(style)
    return o


def magic(style):
    if style in SPECIAL:
        o = weapon(SPECIAL[style])
        if style == 'bloodwhisker':   # its haft stained dark green
            o.M = [MAT['greenwood'] if m == MAT['wood'] else m for m in o.M]
        return o
    return staff(style) if style in STAFFS else weapon(MAGIC_BASE[style])


# ---------------------------------------------------------------------------
# shields (wearables64.shield_shape, y up here)
# ---------------------------------------------------------------------------

def outline(style, n=44):
    """The shield's outline, counter-clockwise from the right, (x, y) with y up."""
    if style in ('round', 'buckler'):
        r = 12.2 if style == 'round' else 7.4
        a = np.linspace(0, 2 * np.pi, n, endpoint=False)
        return np.stack([r * np.cos(a), r * np.sin(a)], 1)
    if style == 'kite':
        n = 30
        pts = [(9.2 * np.cos(a), 5 + 9.2 * np.sin(a)) for a in np.linspace(0, np.pi, n // 2)]
        for i in range(1, n // 2):
            t = i / (n // 2)
            y = 5 - 22 * t
            pts.append((-9.2 * (1 - t) ** 0.9, y))
        pts.append((0.0, -17.0))
        for i in range(n // 2 - 1, 0, -1):
            t = i / (n // 2)
            pts.append((9.2 * (1 - t) ** 0.9, 5 - 22 * t))
        return np.array(pts)
    if style == 'heater':
        pts = [(10, -1 + 12 * i / 4) for i in range(5)]   # right side, bottom up to the top
        pts += [(10 - 20 * i / 6, 11) for i in range(1, 6)]
        pts += [(-10, 11 - 12 * i / 4) for i in range(5)]
        for i in range(1, 10):
            t = i / 10
            pts.append((-10 * np.sqrt(max(0, 1 - t ** 1.6)), -1 - 13 * t))
        pts.append((0.0, -14.0))
        for i in range(9, 0, -1):
            t = i / 10
            pts.append((10 * np.sqrt(max(0, 1 - t ** 1.6)), -1 - 13 * t))
        return np.array(pts)
    if style == 'tower':
        pts = []
        for cx, cy, a0 in ((8, 13, 0), (-8, 13, 90), (-8, -12, 180), (8, -12, 270)):
            for a in np.radians(np.linspace(a0, a0 + 90, 7)):
                pts.append((cx + 3 * np.cos(a), cy + 3 * np.sin(a)))
        return np.array(pts)
    raise KeyError(style)


def shield(style):
    ol = outline(style)
    ctr = np.array([0.0, 0.0]) if style != 'kite' else np.array([0.0, 1.0])
    size = np.max(np.linalg.norm(ol - ctr, axis=1))
    bulge = {'buckler': 2.2, 'round': 2.4, 'kite': 1.8, 'heater': 1.6, 'tower': 1.4}[style]
    th = 0.7
    face_m = {'round': MAT['wood'], 'tower': MAT['wood'], 'buckler': MAT['metal'], 'kite': MAT['red'], 'heater': MAT['blue']}[style]
    K = 6
    scales = [0.96 * (1 - k / K) ** 0.85 for k in range(K)] + [0.0]
    zf = lambda p: th + bulge * (1 - min(1.0, (np.linalg.norm(np.asarray(p) - ctr) / size)) ** 2)
    G = np.array([[[*(ctr + (q - ctr) * s), zf(ctr + (q - ctr) * s)] for q in ol] for s in scales])
    o = surf(G, face_m, lambda p: np.array([p[0], p[1], -50.0]))
    # back: flat boards, their joins, two leather arm straps with rivets and a grip between them
    back = np.array([[[*(ctr + (q - ctr) * s), -th] for q in ol] for s in (0.96, 0.0)])
    o.add(surf(back, MAT['back'], lambda p: np.array([p[0], p[1], 50.0]), smooth=False))
    bz = -th - 0.02
    span = lambda x: [q[1] for q in ol * 0.9 if abs(q[0] - x) < 1.6]
    for x in np.arange(-12.0, 12.1, 4.0):
        ys = span(x)
        if len(ys) >= 2 and max(ys) - min(ys) > 3:
            o.add(bar([x, min(ys) + 0.6, bz], [x, max(ys) - 0.6, bz], 0.45, 0.08, MAT['wooddark'], up=(0, 0, -1)))
    sw = {'buckler': 3.6, 'round': 6.5, 'kite': 5.5, 'heater': 6.0, 'tower': 7.0}[style]
    for yy in (3.2, -3.2):
        o.add(bar([-sw, yy, bz - 0.3], [sw, yy, bz - 0.3], 1.0, 0.32, MAT['grip'], up=(0, 0, -1)))
        for sg in (-1, 1):
            o.add(rivet([sg * sw, yy, bz - 0.55], 0.5))
    o.add(bar([0, -2.4, bz - 0.95], [0, 2.4, bz - 0.95], 0.75, 0.6, MAT['gripdark'], up=(0, 0, -1)))
    # the rim: a rolled edge all round
    rim_path = [[*(ctr + (q - ctr) * 0.975), zf(ctr + (q - ctr) * 0.975) * 0.45] for q in ol]
    rim_path.append(rim_path[0])
    o.add(tube(rim_path, 1.05 if style != 'buckler' else 0.8, MAT['metal'] if style != 'buckler' else MAT['bright'], seg=5, caps=False))
    if style != 'buckler':   # rivets round the rim
        L = np.cumsum([0] + [np.linalg.norm(np.subtract(rim_path[i + 1][:2], rim_path[i][:2])) for i in range(len(rim_path) - 1)])
        for d0 in np.arange(2.0, L[-1] - 1.0, 5.2):
            i = int(np.searchsorted(L, d0)) - 1
            q = np.array(rim_path[i][:2]) * 0.93
            o.add(rivet([q[0], q[1], zf(q) + 0.15], 0.5))
    if style in ('kite', 'heater'):   # a fine trim inside the rim
        trim = [[*(ctr + (q - ctr) * 0.84), zf(ctr + (q - ctr) * 0.84) + 0.08] for q in ol]
        o.add(tube(trim + [trim[0]], 0.32, MAT['gold'], seg=4, caps=False))
    top = lambda x, y: zf((x, y))
    if style in ('round', 'tower', 'buckler'):
        br = 3.2 if style != 'buckler' else 3.4
        o.add(ellipsoid([0, 0, zf((0, 0)) - 0.6], [br, br, br * 0.7], MAT['bright'] if style == 'buckler' else MAT['metal'], seg=14, rings=8)
              .moved(np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]]).T))
    if style == 'buckler':
        ring = [[3.9 * np.cos(a), 3.9 * np.sin(a), zf((3.9 * np.cos(a), 3.9 * np.sin(a))) + 0.1] for a in np.linspace(0, 2 * np.pi, 25)]
        o.add(tube(ring, 0.45, MAT['metal'], seg=6, caps=False))
    if style in ('round', 'tower'):   # the planks' joins
        xmax = 11.5 if style == 'round' else 10.5
        for x in np.arange(-xmax + (xmax % 4), xmax, 4.0):
            if abs(x) < 3.5:
                continue
            ys = [q[1] for q in ol if abs(q[0] - x) < 1.2]
            if style == 'round':
                y1 = np.sqrt(max(0, 11.4 ** 2 - x * x))
                y0 = -y1
            else:
                y0, y1 = -14.2, 14.2
            if y1 - y0 < 2:
                continue
            for a, b in zip(np.linspace(y0, y1, 6), np.linspace(y0, y1, 6)[1:]):
                o.add(bar([x, a, top(x, a) + 0.02], [x, b, top(x, b) + 0.02], 0.5, 0.12, MAT['wooddark'], up=(0, 0, 1)))
        if style == 'tower':
            for a, b in zip(np.linspace(-10.5, 10.5, 7), np.linspace(-10.5, 10.5, 7)[1:]):
                o.add(bar([a, 0, top(a, 0) + 0.05], [b, 0, top(b, 0) + 0.05], 1.2, 0.35, MAT['metal']))
    if style == 'kite':   # a gold cross
        for a, b in zip(np.linspace(-13.5, 11.5, 9), np.linspace(-13.5, 11.5, 9)[1:]):
            o.add(bar([0, a, top(0, a) + 0.05], [0, b, top(0, b) + 0.05], 1.2, 0.3, MAT['gold']))
        for a, b in zip(np.linspace(-6.8, 6.8, 6), np.linspace(-6.8, 6.8, 6)[1:]):
            o.add(bar([a, 3, top(a, 3) + 0.06], [b, 3, top(b, 3) + 0.06], 1.2, 0.3, MAT['gold']))
    if style == 'heater':   # a gold chevron
        for sg in (-1, 1):
            xs = np.linspace(0, sg * 9.0, 6)
            for a, b in zip(xs, xs[1:]):
                ya, yb = 1 - 0.9 * abs(a), 1 - 0.9 * abs(b)
                o.add(bar([a, ya, top(a, ya) + 0.05], [b, yb, top(b, yb) + 0.05], 1.6, 0.3, MAT['gold']))
    return o


SHIELDS = ['buckler', 'round', 'heater', 'kite', 'tower']


# ---------------------------------------------------------------------------
# helmets (the Human head: 11.5 across, 10.5 tall, 9.5 front to back, from its middle)
# ---------------------------------------------------------------------------

HX, HY, HZ = 11.5, 10.5, 9.5


def brim_y(z, front=5.0, back=2.0):
    """The helmet's lower edge: just over the brow at the front, lower at the back (wearables64.brim_line)."""
    k = (np.clip(z / HZ, -1, 1) + 1) / 2
    return back + (front - back) * k ** 1.4


def dome(pad=1.0, lift=0.0, front=5.0, back=2.0, seg=22, rows=7, m=None, peak=0.0):
    """The skull cap: the head's ellipsoid made pad larger, down to the brim; lift raises the crown."""
    rx, ry, rz = HX + pad, HY + pad + lift, HZ + pad
    ph = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    G = []
    for i in range(rows + 1):
        row = []
        for p in ph:
            dx, dz = np.cos(p), np.sin(p)
            # latitude from the top down to where the shell meets the brim
            lo = np.arcsin(np.clip(brim_y(dz * rz, front, back) / ry, -1, 1))
            lat = np.pi / 2 - (np.pi / 2 - lo) * (i / rows)
            y = ry * np.sin(lat)
            if peak:
                y += peak * max(0.0, np.sin(lat) - 0.6) / 0.4 * 1.0
            row.append([rx * np.cos(lat) * dx, y, rz * np.cos(lat) * dz])
        G.append(row)
    G = np.array(G)
    return surf(G, MAT['metal'] if m is None else m, lambda q: np.array([0, 0, 0])), G


def helmet(style):
    o = Mesh()
    if style == 'great helm':
        ph = np.linspace(0, 2 * np.pi, 22, endpoint=False)
        rx, rz = HX + 1.2, HZ + 1.2
        ys = [-HY * 0.98, -HY * 0.7, 0, HY * 0.55, HY * 0.82, HY * 0.98, HY + 1.6]
        sc = [0.96, 1.0, 1.0, 1.0, 0.94, 0.8, 0.0]
        G = np.array([[[rx * s * np.cos(p), y, rz * s * np.sin(p)] for p in ph] for y, s in zip(ys, sc)])
        eye_y = 22.5 - 21   # the eyes' row (21 in the picture) above the middle
        mats = lambda i, j: MAT['metal']
        o.add(surf(G, MAT['metal'], lambda q: np.array([0, q[1] * 0.5, 0])))
        # the eye slit and breathing holes, across the front
        for p0, p1 in zip(np.linspace(np.radians(35), np.radians(145), 8), np.linspace(np.radians(35), np.radians(145), 8)[1:]):
            a = [rx * 1.01 * np.cos(p0), eye_y, rz * 1.01 * np.sin(p0)]
            b = [rx * 1.01 * np.cos(p1), eye_y, rz * 1.01 * np.sin(p1)]
            o.add(bar(a, b, 0.9, 0.25, MAT['dark'], up=[np.cos((p0 + p1) / 2), 0, np.sin((p0 + p1) / 2)]))
        o.add(bar([0, -HY * 0.8, rz + 0.3], [0, HY * 0.9, rz + 0.3], 0.9, 0.4, MAT['bright'], up=(0, 0, 1)))   # the front ridge
        for k in range(3):
            for sg in (-1, 1):
                o.add(ellipsoid([sg * 2.5, -3.5 - k * 1.8, rz * 0.98], [0.45, 0.45, 0.3], MAT['dark'], seg=6, rings=4))
        band = [[rx * 1.01 * np.cos(p), -HY * 0.7, rz * 1.01 * np.sin(p)] for p in np.linspace(0, 2 * np.pi, 25)]
        o.add(tube(band, 0.55, MAT['bright'], seg=6, caps=False))
        for q in band[:-1:2]:
            o.add(rivet(np.array(q) * np.array([1.03, 1, 1.03]) + np.array([0, 1.1, 0]), 0.42))
        return o
    front, back = 5.0, 2.0
    lift = {'kettle': 0.5, 'nasal': 1.0, 'horned': 0.5, 'winged': 0.5, 'crested': 0.8}.get(style, 0.5)
    d, G = dome(pad=0.8, lift=lift, front=front, back=back, peak=1.6 if style == 'nasal' else 0.0)
    o.add(d)
    brim = list(G[-1]) + [G[-1][0]]
    o.add(tube(brim, 0.8, MAT['bright'], seg=6, caps=False))
    for j in range(0, len(G[-1]), 3):   # rivets along the brow band
        q = G[-1][j]
        o.add(rivet(q * np.array([1.06, 1, 1.06]) + np.array([0, 0.9, 0]), 0.48))
    if style in ('nasal', 'horned', 'crested'):   # a banded cap: strips over the crown, front to back and side to side
        ry = HY + 0.8 + lift
        for ax in (0, 2):
            arc = []
            for a in np.linspace(-1.0, 1.0, 11):
                th = a * (np.pi / 2 - 0.25)
                r = np.array([HX + 0.8, 0, HZ + 0.8])
                pnt = np.zeros(3); pnt[1] = ry * np.cos(th) + (1.6 * max(0, np.cos(th) - 0.6) / 0.4 if style == 'nasal' else 0) + 0.25
                pnt[ax] = r[ax] * np.sin(th) * 1.02
                arc.append(pnt)
            if style == 'crested' and ax == 2:
                continue
            o.add(tube(arc, 0.55, MAT['bright'], seg=5, side=(0, 1, 0), flat=0.6))
            for q in arc[1:-1:3]:
                o.add(rivet(q * 1.02, 0.42))
    if style == 'kettle':   # a wide brim all round
        ph = np.linspace(0, 2 * np.pi, 23)
        inner = [[(HX + 1.2) * np.cos(p), brim_y((HZ + 1) * np.sin(p), front, back) - 0.2, (HZ + 1.2) * np.sin(p)] for p in ph]
        outer = [[(HX + 3.8) * np.cos(p), brim_y((HZ + 1) * np.sin(p), front, back) - 1.4, (HZ + 3.4) * np.sin(p)] for p in ph]
        Gb = np.array([inner, [[(a + b)[0] / 2, (a[1] + b[1]) / 2 + 0.15, (a + b)[2] / 2] for a, b in zip(np.array(inner), np.array(outer))], outer])
        o.add(surf(Gb, MAT['metal'], lambda q: np.array([0, q[1] - 3, 0]), closed=False))
        o.add(surf(Gb - np.array([0, 0.45, 0]), MAT['metal'], lambda q: np.array([0, q[1] + 3, 0]), closed=False))
        o.add(tube(outer, 0.45, MAT['bright'], seg=6, caps=False))
        for q in outer[:-1:3]:
            o.add(rivet(np.array(inner[outer.index(q)]) * 0.5 + np.array(q) * 0.5 + np.array([0, 0.45, 0]), 0.42))
    if style == 'nasal':
        o.add(bar([0, front + 0.6, HZ + 1.3], [0, front - 6.0, HZ + 1.6], 1.0, 0.45, MAT['bright'], up=(0, 0, 1)))
        o.add(bar([0, front + 0.5, HZ + 1.0], [0, HY + 2.2, 0.0], 0.7, 0.3, MAT['bright'], up=(0, 1, 1)))
    if style == 'horned':
        for sg in (-1, 1):
            ts = np.linspace(0, 1, 10)
            p0, p1, p2 = np.array([sg * (HX - 0.5), 4.5, 0.5]), np.array([sg * (HX + 6.5), 6.0, 1.5]), np.array([sg * (HX + 7.5), 14.5, 2.5])
            path = [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2 for t in ts]
            o.add(tube(path, [2.3 * (1 - t) ** 0.8 + 0.08 for t in ts], MAT['horn'], seg=9))
            o.add(tube([p0 * np.array([0.96, 1, 1]) + [0, -0.2, 0], p0 + [sg * 0.9, 0, 0]], [2.6, 2.6], MAT['bright'], seg=9))
    if style == 'winged':
        for sg in (-1, 1):
            for k, (ang, ln) in enumerate(((0.35, 9.5), (0.7, 11.5), (1.05, 10.5), (1.35, 8.0))):
                base = np.array([sg * (HX + 0.2), 4.5 + k * 0.6, -1.0 - k * 0.9])
                tip = base + np.array([sg * np.cos(ang) * 0.55, np.sin(ang), -0.55 * np.cos(ang)]) * ln
                mid = (base + tip) / 2 + np.array([sg * 0.8, 0.6, 0])
                ts = np.linspace(0, 1, 7)
                path = [(1 - t) ** 2 * base + 2 * (1 - t) * t * mid + t * t * tip for t in ts]
                o.add(tube(path, [1.5 * np.sin(np.pi * (0.15 + 0.85 * t)) + 0.05 for t in ts], MAT['feather'], seg=8,
                           side=(0, 0, 1), flat=0.3))
    if style == 'crested':
        ts = np.linspace(-0.85, 0.95, 16)
        ry = HY + 1 + lift
        path = [[0, ry * np.cos(t * 1.25) + 0.6, (HZ + 1) * np.sin(t * 1.25)] for t in ts]
        o.add(tube(path, [1.2] * len(ts), MAT['bright'], seg=6, side=(1, 0, 0), flat=0.6))
        plume = [[0, ry * np.cos(t * 1.25) + 2.6 + 1.8 * np.sin((t + 0.85) / 1.8 * np.pi), (HZ + 1) * np.sin(t * 1.25) - 1.0] for t in ts]
        o.add(tube(plume, [1.5 + 1.6 * np.sin((t + 0.85) / 1.8 * np.pi) for t in ts], MAT['plume'], seg=10, side=(0, 1, 0), flat=1.0))
    return o


HELMETS = ['kettle', 'nasal', 'horned', 'winged', 'great helm', 'crested']


# ---------------------------------------------------------------------------

def pack(mesh, q=64):
    mesh = mesh.moved(np.diag([-1.0, 1, 1])) if getattr(mesh, 'mirror_x', False) else mesh
    P = np.round(np.array(mesh.P) * q).astype('<i2')
    N = np.round(np.array(mesh.N) * 127).astype('i1')
    M = np.array(mesh.M, dtype='u1')
    b = lambda a: base64.b64encode(a.tobytes()).decode()
    return dict(v=len(mesh.P), pos=b(P), nrm=b(N), mat=b(M))


# How a weapon is held at rest, as a direction in the wearer's frame (right, front, up): from the drawn pieces'
# grip in the front (S) and side (E) views (Template.grip), long hafts more upright (wearables64.POLE). Seen from
# the corner cameras a weapon held out at 45 degrees both ways reads as level, so it is raised a little.
def rest_axis(style):
    style = MAGIC_BASE.get(style, SPECIAL.get(style, style))
    pole = 2.2 if style in STAFFS else 2.4 if style == 'fishing rod' else 1.4 if style in ('harpoon', 'spade') else w.POLE.get(style, 0.0)
    sx, sy = -0.71, -0.70 - pole   # S view
    ex, ey = 0.72, -0.70 - pole    # E view
    a = np.array([(-sx) / (-sy), ex / (-ey), 1.6])
    return [round(float(v), 4) for v in nz(a)]


TIERS = {k: [list(c) for c in v] for k, v in w.RAMPS.items()}


def main(out):
    pieces, rest = {}, {}
    for s in WEAPONS:
        m = weapon(s); pieces['weapon.' + s] = pack(m); rest[s] = rest_axis(s)
        print('weapon', s, len(m.P) // 3, 'tris')
    for s in MAGIC + list(SPECIAL):
        m = magic(s); pieces['weapon.' + s] = pack(m); rest[s] = rest_axis(s)
        print('magic', s, len(m.P) // 3, 'tris')
    for d in (0.25, 0.5, 0.75, 1.0):   # the bow drawn, for shooting (the arena's archer)
        pieces[f'weapon.bow@{d}'] = pack(bow(d))
    for s in LOADS:
        m = load(s); pieces['load.' + s] = pack(m)
        print('load', s, len(m.P) // 3, 'tris')
    for s in PROPS:
        m = prop(s); pieces['prop.' + s] = pack(m)
        print('prop', s, len(m.P) // 3, 'tris')
    m = arrow(); pieces['arrow'] = pack(m)
    print('arrow', len(m.P) // 3, 'tris')
    for s in SHIELDS:
        m = shield(s); pieces['shield.' + s] = pack(m)
        print('shield', s, len(m.P) // 3, 'tris')
    for s in HELMETS:
        m = helmet(s); pieces['helmet.' + s] = pack(m)
        print('helmet', s, len(m.P) // 3, 'tris')
    json.dump(dict(q=64, mat=MAT, metallic=METALLIC, tiers=TIERS, rest=rest, magic=MAGIC_TIER, pieces=pieces), open(out, 'w'), separators=(',', ':'))
    print(out, os.path.getsize(out) // 1024, 'KB')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'gear3d.json'))
