# Voxel gear for the 3D view's unit models (python3 voxgear.py OUTDIR): the held and worn pieces - sword, axe,
# mace, spear, dagger, pickaxe, bow, shield, helmet - built out of blocks one sprite pixel big, shaded like pixel
# art (bright edges, a darker fuller, wood grain, leather wraps), and written into copies of the race models
# (game/Interface/models/<race>.json) in place of the low-poly pieces, in the same joint frames, so they swing
# with the animations as before.
#
# Colours: metal blocks carry a brightness code (mat 10..40 = the tier's colour x (mat-10)/20, which the page's
# gear drawing needs to understand - see PAGE_PATCH); wood and leather carry their own colour (mat 1 / 2).
import base64, json, math, os, sys
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
MODELS = os.path.join(ROOT, 'game', 'Interface', 'models')
PX = 0.0185                       # one sprite pixel in tiles (a 64 px unit stands about a tile tall)

WOOD = (134, 86, 46); WOOD_D = (110, 68, 38); WOOD_L = (150, 100, 56)
LEATHER = (96, 58, 32); LEATHER_L = (122, 76, 42)
BONE = (214, 201, 160); BONE_D = (176, 162, 124)
STRING = (222, 214, 190)
PAINT = (150, 30, 28); PAINT_D = (118, 22, 22)

def M(k):  return ('m', float(k))            # metal at brightness k (1 = the tier's own colour)
def C(rgb, wood=False): return ('w' if wood else 'c', tuple(rgb))

# ---------------------------------------------------------------- shapes, in sprite pixels, grip at the origin
# Each returns {(x, y, z): colour} for voxels whose centre is (x+.5, y+.5, z+.5); y runs along the weapon.
def box(V, x0, x1, y0, y1, z0, z1, col):
    for x in range(x0, x1):
        for y in range(y0, y1):
            for z in range(z0, z1): V[(x, y, z)] = col(x, y, z) if callable(col) else col

def haft(V, y0, y1, r=1, wrap=None):
    for y in range(y0, y1):
        for x in range(-r, r):
            for z in range(-r, r):
                if wrap and wrap[0] <= y < wrap[1]: V[(x, y, z)] = C(LEATHER_L if y % 2 else LEATHER)
                else: V[(x, y, z)] = C(WOOD_D if (y % 3 == 0 or (x + z) % 3 == 0 and y % 5 == 2) else (WOOD_L if x == -r and z == -r else WOOD), wood=True)

def blade(V, y0, y1, hw, tip, th=1):
    """A straight blade from y0 to y1, half-width hw px, tapering over its last `tip` px; edges bright, the fuller dark."""
    for y in range(y0, y1):
        t = (y1 - y) / tip
        w = hw if t >= 1 else max(0.5, hw * t)
        for x in range(-math.ceil(hw), math.ceil(hw)):
            xc = x + 0.5
            if abs(xc) > w: continue
            edge = abs(xc) > w - 1.0
            for z in range(-th, th):
                k = 1.32 if edge else (0.86 if abs(xc) < 0.6 and y < y1 - tip else 1.05)
                V[(x, y, z)] = M(k)

def sword(L=31, hw=2.0, guard=4, grip=5):
    V = {}
    haft(V, -grip, 0, wrap=(-grip, 0))
    box(V, -1, 1, -grip - 2, -grip, -1, 1, M(1.15))                       # pommel
    box(V, -2, 2, -grip - 3, -grip - 2, -1, 1, M(1.0))
    box(V, -guard, guard, 0, 2, -1, 1, lambda x, y, z: M(1.25 if y == 1 else 0.9))   # crossguard
    blade(V, 2, L, hw, 6)
    return V

def dagger():
    V = {}
    haft(V, -3, 0, wrap=(-3, 0))
    box(V, -1, 1, -4, -3, -1, 1, M(1.1))
    box(V, -3, 3, 0, 1, -1, 1, M(0.95))
    blade(V, 1, 12, 1.5, 4)
    return V

def axe():
    V = {}
    haft(V, -8, 23)
    box(V, -1, 1, -9, -8, -1, 1, M(0.9))                                 # butt cap
    # the head: an eye round the haft, a cheek flaring out to a wide curved edge on +x, a short poll on -x
    for y in range(13, 23):
        for x in range(-3, 9):
            for z in range(-1, 1):
                yc = y + 0.5 - 18; xc = x + 0.5
                if xc < -1:
                    if abs(yc) <= 1.6 and xc > -3.2: V[(x, y, z)] = M(0.92)
                    continue
                half = 2.2 + 2.6 * max(0.0, xc - 1) / 7                     # flares toward the edge
                edge_x = 7.5 - 0.25 * yc * yc / 4
                if abs(yc) <= half and xc <= edge_x:
                    V[(x, y, z)] = M(1.35 if xc > edge_x - 1.2 else (0.88 if xc < 1.5 else 1.05))
    return V

def mace():
    V = {}
    haft(V, -5, 14, wrap=(-5, 0))
    for x in range(-4, 4):
        for y in range(12, 22):
            for z in range(-4, 4):
                xc, yc, zc = x + 0.5, y + 0.5 - 17, z + 0.5
                r = math.hypot(xc, zc); ang = math.atan2(zc, xc)
                core = yc * yc / 12.0 + r * r / 4.4 <= 1
                flange = abs(yc) <= 3.2 - 0.5 * max(0.0, r - 2.2) and r <= 3.9 and abs(((ang / (2 * math.pi) * 6) % 1) - 0.5) > 0.34
                if core or flange: V[(x, y, z)] = M(1.3 if (flange and r > 3.0) else (1.0 if not core else 0.88))
    return V

def spear():
    V = {}
    haft(V, -24, 31)
    box(V, -1, 1, -25, -24, -1, 1, M(0.9))
    box(V, -1, 1, 31, 33, -1, 1, M(0.85))                                # socket
    for y in range(33, 42):
        u = (y + 0.5 - 33) / 9
        w = 2.4 * math.sin(math.pi * min(1.0, u * 1.15)) + 0.4
        for x in range(-3, 3):
            xc = x + 0.5
            if abs(xc) <= w:
                for z in range(-1, 1): V[(x, y, z)] = M(1.3 if abs(xc) > w - 0.9 else (0.88 if abs(xc) < 0.6 else 1.05))
    return V

def pickaxe():
    V = {}
    haft(V, -6, 20)
    # the head runs crosswise (along +-x): a pick spike each side, curving down, thick at the eye
    for x in range(-10, 10):
        xc = x + 0.5; t = abs(xc) / 10
        th = max(0.5, 1.6 * (1 - t) + 0.4)
        yc_mid = 19.5 - 2.2 * t * t
        for y in range(15, 23):
            yc = y + 0.5
            if abs(yc - yc_mid) <= th:
                for z in range(-1, 1): V[(x, y, z)] = M(1.3 if abs(yc - yc_mid) > th - 0.8 or t > 0.85 else 0.95)
    return V

def bow():
    V = {}
    for y in range(-17, 17):
        u = (y + 0.5) / 17
        z = int(round(4.5 * (1 - u * u)))
        V[(0, y, z)] = C(WOOD_D if abs(y) < 3 else WOOD, wood=True)
        if abs(y) < 3: V[(0, y, z + 1)] = C(LEATHER)                       # the grip
        if abs(y) >= 15: V[(0, y, z)] = C(BONE_D)                           # tips
    for y in range(-15, 15): V[(0, y, -1)] = C(STRING)                     # the string, straight
    return V

def shield():
    # a heater shield facing +x (out from the left forearm): painted face, metal rim and boss, in (z, y)
    V = {}
    W, H = 6.5, 8.0
    for y in range(-8, 8):
        for z in range(-7, 7):
            yc, zc = y + 0.5, z + 0.5
            narrow = 1.0 if yc > -2 else max(0.15, 1 - ((-2 - yc) / 6.2) ** 1.6)
            if abs(zc) > W * narrow or yc > H - 0.2: continue
            rim = abs(zc) > W * narrow - 1.1 or yc > H - 1.2
            for x in range(0, 2):
                if rim: V[(x, y, z)] = M(1.28 if (zc < 0 or yc > H - 1.2) else 0.95)
                elif x == 1: V[(x, y, z)] = C(PAINT_D if (abs(zc) < 0.9 or abs(yc - 2.5) < 0.9) else PAINT)
                else: V[(x, y, z)] = C(WOOD_D, wood=True)
    for y in range(1, 4):
        for z in range(-1, 1): V[(2, y, z)] = M(1.3 if y == 3 else 1.05)    # boss
    return V

def helmet():
    # in head-joint pixels: x across, y up from the joint, z to the front. A cap over the crown with a rim band
    # and a ridge, open at the face (the old cap showed the face too), a nasal, and small bone horns
    V = {}
    RX, RY, RZ, CY = 10.2, 9.0, 7.2, 1.5
    for x in range(-11, 11):
        for y in range(0, 11):
            for z in range(-8, 8):
                xc, yc, zc = x + 0.5, y + 0.5, z + 0.5
                e = (xc / RX) ** 2 + ((yc - CY) / RY) ** 2 + (zc / RZ) ** 2
                if e > 1 or e < 0.58 or yc < CY + 1.0: continue
                if zc > 1.5 and yc < CY + 4.6: continue                      # the face stays open
                rim = yc < CY + 2.6 or (zc > 1.5 and yc < CY + 5.6)
                ridge = abs(xc) < 1.0 and yc > CY + 5.5
                V[(x, y, z)] = M(0.82 if rim else (1.25 if ridge else 1.0))
    for y in range(int(CY + 2), int(CY + 5)):
        V[(-1, y, 6)] = M(1.1); V[(0, y, 6)] = M(0.95)                        # nasal
    for s in (-1, 1):
        for i in range(6):
            x = s * (9 + i // 2); y = int(CY) + 5 + i
            V[(x if s > 0 else x - 1, y, 0)] = C(BONE if i < 4 else BONE_D)
            V[(x if s > 0 else x - 1, y, -1)] = C(BONE_D)
    return V

PIECES = dict(sword=sword, axe=axe, mace=mace, spear=spear, dagger=dagger, pickaxe=pickaxe, bow=bow, shield=shield, helmet=helmet)

# ---------------------------------------------------------------- meshing
FACES = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]), ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
         ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]), ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
         ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]), ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)])]

def mesh(V):
    """Exposed faces of the blocks, merged along rows where neighbours share a colour (fewer triangles)."""
    quads = []
    for n, corners in FACES:
        ax = [i for i in range(3) if n[i]][0]
        u, v = [i for i in range(3) if i != ax]
        faces = {}
        for p, col in V.items():
            q = tuple(p[i] + n[i] for i in range(3))
            if q in V: continue
            faces[p] = col
        # greedy along u, then v
        done = set()
        for p in sorted(faces, key=lambda p: (p[ax], p[v], p[u])):
            if p in done: continue
            col = faces[p]
            L = 1
            while True:
                q = list(p); q[u] += L; q = tuple(q)
                if faces.get(q) == col and q not in done: L += 1
                else: break
            Hh = 1
            while True:
                ok = True
                for k in range(L):
                    q = list(p); q[u] += k; q[v] += Hh; q = tuple(q)
                    if faces.get(q) != col or q in done: ok = False; break
                if not ok: break
                Hh += 1
            for a in range(L):
                for b in range(Hh):
                    q = list(p); q[u] += a; q[v] += b; done.add(tuple(q))
            size = [1, 1, 1]; size[u] = L; size[v] = Hh
            pts = [tuple(p[i] + c[i] * size[i] for i in range(3)) for c in corners]
            quads.append((pts, col, n))
    return quads

# ---------------------------------------------------------------- fitting into the model's joint frames
def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)

def frame_of(name, old):
    """Rotation (columns: piece x, y, z in joint space), pixel size and origin, matched to the old piece."""
    pos, mat = old
    if name == 'helmet':
        return np.eye(3), PX / 1.2, np.array([0.0, 0.004, -0.004])
    if name == 'shield':
        return np.eye(3), PX * 0.95, np.array([0.105, 0.0, 0.035])
    ctr = pos.mean(0); u, s, vt = np.linalg.svd(pos - ctr, full_matrices=False)
    a = unit(vt[0])
    # the main axis points away from the hand: toward the far end of the piece from the origin
    if (pos @ a).max() < -(pos @ a).min(): a = -a
    if name == 'bow': a = np.array([0.0, 1.0, 0.0])
    # the head's side (axe edge, pick, blade flat): where the metal sits off the line of the haft
    tri = np.repeat(mat, 3)
    met = pos[np.isin(tri, [0, 4])]
    side = None
    if len(met) and name in ('axe',):
        c = met.mean(0); off = c - (c @ a) * a
        if np.linalg.norm(off) > 1e-3: side = unit(off)
    if side is None:
        side = unit(np.array([1.0, 0, 0]) - a[0] * a)
    zz = unit(np.cross(side, a))
    R = np.stack([side, a, zz], 1)
    return R, PX, np.zeros(3)

def encode(name, V, old):
    R, s, t = frame_of(name, old)
    quads = mesh(V)
    tris, mats, cols = [], [], []
    for pts, col, n in quads:
        P = [R @ (np.array(p, float) * s) + t for p in pts]
        for tri in ((P[0], P[1], P[2]), (P[0], P[2], P[3])):
            tris.append(tri)
            kind, val = col
            if kind == 'm':
                mats.append(int(round(10 + max(0.5, min(1.5, val)) * 20))); cols.append((136, 136, 140))
            else:
                mats.append(1 if kind == 'w' else 2); cols.append(val)
    q = 8000.0
    pos = np.array(tris).reshape(-1, 3)
    pos_i = np.clip(np.round(pos * q), -32768, 32767).astype('<i2')
    return dict(tris=len(tris), pos=base64.b64encode(pos_i.tobytes()).decode(), mat=base64.b64encode(np.array(mats, 'u1').tobytes()).decode(),
                col=base64.b64encode(np.array(cols, 'u1').tobytes()).decode()), len(V)

def decode_old(g, q):
    pos = np.frombuffer(base64.b64decode(g['pos']), dtype='<i2').reshape(-1, 3) / q
    mat = np.frombuffer(base64.b64decode(g['mat']), dtype='u1')
    return pos, mat

# The page's gear colouring, taught the metal brightness codes (mat 10..40): tier colour x (mat-10)/20.
PAGE_OLD = "const mc=g.mat[j];const c=mc===0?"
PAGE_NEW = "const mc=g.mat[j];const c=mc>=10?[Math.min(1,metal[0]*(mc-10)/20),Math.min(1,metal[1]*(mc-10)/20),Math.min(1,metal[2]*(mc-10)/20),1]:mc===0?"

def build(outdir):
    os.makedirs(outdir, exist_ok=True)
    report = {}
    for f in sorted(os.listdir(MODELS)):
        if not f.endswith('.json'): continue
        d = json.load(open(os.path.join(MODELS, f)))
        q = d.get('q', 8000.0)
        for name, fn in PIECES.items():
            g = d.get('gear', {}).get(name)
            if not g: continue
            new, nvox = encode(name, fn(), decode_old(g, q))
            report.setdefault(name, (g['tris'], new['tris'], nvox))
            g.update(new)
        json.dump(d, open(os.path.join(outdir, f), 'w'), separators=(',', ':'))
    print(json.dumps({k: dict(old_tris=v[0], new_tris=v[1], blocks=v[2]) for k, v in report.items()}, indent=1))
    return report

if __name__ == '__main__':
    build(sys.argv[1])
