# The 3D gear made pixel art the way the dragons were (art/enhance/beasts64.py), python3 pixelgear.py OUT [tiers]:
# every weapon, shield and helmet (meshes.py) rendered from 16 facings round the wearer (weapons also in an
# attack's poses), seen face-on like the unit pictures; each pixel coloured from its material's five-colour ramp
# (the 2D gear's ramps, wearables64.RAMPS) in flat bands, hard-edged at the units' own pixel size (64 a tile), a
# dark outline round it. Writes, under OUT:
#   g3p-<piece>-<tier>-<pose>.png   a strip of the 16 facings (facing 0: seen from in front, then round toward the
#                                   wearer's right, 22.5 degrees a step), each cell cropped to the pose's extent so
#                                   every facing shares one anchor (the fist, the forearm, the middle of the head)
#   gear3d-pix.json                 the cells' sizes and anchors, for the page (gear3d.js, pixel mode)
import json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'enhance'))
import meshes as ms           # noqa: E402
import wearables64 as w       # noqa: E402
import remaster64 as rm       # noqa: E402
from beasts64 import save_indexed   # noqa: E402

FACINGS = 16
SS = 4   # rendered at four times the art's size, then taken down to hard pixels
WIND, STRIKE = np.array([0.45, -0.12, 0.88]), np.array([-0.15, 0.9, -0.4])   # as gear3d.js (right, front, up)
TIERS = ['wood', 'bone', 'leather', 'iron', 'silver', 'gold', 'adamantium', 'diamond', 'chitin', 'hell']
SOFT = ('wood', 'leather', 'bone', 'bonehide', 'dragonhide', 'spidersilk', 'dragonbone', 'dragonfang')


def game_tiers():
    """The tiers the game makes each piece in ({'weapon.longsword': {'iron', ...}}), from GearData.dm's rm_gear."""
    import re
    src = os.path.join(HERE, '..', '..', 'game', 'Code', 'Remastered', 'GearData.dm')
    out = {}
    if os.path.exists(src):
        for m in re.finditer(r'rm_gear = "(weapon|shield|helmet)\.([a-z ]+)\.([a-z]+)"', open(src, encoding='latin-1').read()):
            out.setdefault(m.group(1) + '.' + m.group(2), set()).add(m.group(3))
    return out


GAME = game_tiers()


def piece_tiers(name, tiers):
    """The tiers a piece is drawn in: those asked for and every one the game makes it in; a magic piece its own."""
    st = name.split('.', 1)[1]
    if st in ms.MAGIC_TIER:
        return [ms.MAGIC_TIER[st]]
    return list(tiers) + sorted(GAME.get(name, set()) - set(tiers))
M = ms.MAT


def nz(v):
    v = np.asarray(v, float); n = np.linalg.norm(v)
    return v / (n or 1)


def slerp(a, b, k):
    d = np.clip(a @ b, -1, 1); th = np.arccos(d)
    if th < 1e-3: return a
    return (a * np.sin((1 - k) * th) + b * np.sin(k * th)) / np.sin(th)


# The wearer's frame here: x to its right, y up, z forward.
R_, U_, F_ = np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])


def weapon_basis(style, pose):
    """A held weapon's x, y, z (up the weapon, toward its edge, across its flat) in the wearer's frame, as
    gear3d.js turns it: at rest, wound up, half way through the blow, at the blow."""
    rest = np.array(ms.rest_axis(style))
    a, ws = {0: (rest, 0.0), 1: (WIND, 0.0), 2: (slerp(WIND, STRIKE, 0.5), 0.5), 3: (STRIKE, 1.0)}[pose]
    A = nz([a[0], a[2], a[1]])   # (right, front, up) -> x, y, z
    e0 = F_ if style == 'bow' else F_ * 0.8 + R_ * 0.6 - U_ * 1.2 * ws
    E = nz(e0 - A * (e0 @ A))
    return np.stack([A, E, np.cross(A, E)], 1), np.zeros(3)


def shield_basis():
    Z = nz(F_ - R_); X = np.cross(U_, Z)
    return np.stack([X, U_, Z], 1), Z * 1.3


def helmet_basis():
    return np.stack([-R_, U_, F_], 1), np.zeros(3)


def placed(mesh, B, off):
    P = np.array(mesh.P) @ B.T + off
    N = np.array(mesh.N) @ B.T
    return P, N, np.array(mesh.M)


def camera(i):
    """Facing i: the camera's direction from the wearer, its right, up (face-on, as the pictures are drawn)."""
    ph = 2 * np.pi * i / FACINGS
    c = np.array([np.sin(ph), 0, np.cos(ph)])
    return c, np.cross(U_, -c), U_


def raster(P, N, Mt, c, rc, box, up=None):
    """Material, normal and coverage at SS times the art's pixels over box (x0, y0, x1, y1 in art pixels, y down)."""
    x0, y0, x1, y1 = box
    W, H = int(round((x1 - x0) * SS)), int(round((y1 - y0) * SS))   # the box may start part way into a pixel (an anchor)
    up = U_ if up is None else up   # the picture's up (looking down on a piece lying on the ground, north)
    X = (P @ rc - x0) * SS; Y = (-(P @ up) - y0) * SS; Zd = P @ c
    zb = np.full((H, W), -1e9); mat = np.full((H, W), -1, int); nb = np.zeros((H, W, 3))
    for t in range(0, len(P), 3):
        xs, ys = X[t:t + 3], Y[t:t + 3]
        bx0, bx1 = max(0, int(np.floor(xs.min()))), min(W - 1, int(np.ceil(xs.max())))
        by0, by1 = max(0, int(np.floor(ys.min()))), min(H - 1, int(np.ceil(ys.max())))
        if bx1 < bx0 or by1 < by0: continue
        gx, gy = np.meshgrid(np.arange(bx0, bx1 + 1) + 0.5, np.arange(by0, by1 + 1) + 0.5)
        (ax, bx_, cx), (ay, by_, cy) = xs, ys
        den = (by_ - cy) * (ax - cx) + (cx - bx_) * (ay - cy)
        if abs(den) < 1e-9: continue
        l0 = ((by_ - cy) * (gx - cx) + (cx - bx_) * (gy - cy)) / den
        l1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        l2 = 1 - l0 - l1
        ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not ins.any(): continue
        z = l0 * Zd[t] + l1 * Zd[t + 1] + l2 * Zd[t + 2]
        sub = zb[by0:by1 + 1, bx0:bx1 + 1]
        win = ins & (z > sub)
        if not win.any(): continue
        sub[win] = z[win]
        mat[by0:by1 + 1, bx0:bx1 + 1][win] = Mt[t]   # -2: the hidden head (hides what is behind it, draws nothing)
        n = l0[..., None] * N[t] + l1[..., None] * N[t + 1] + l2[..., None] * N[t + 2]
        nb[by0:by1 + 1, bx0:bx1 + 1][win] = n[win]
    return mat, nb


METALLIC = set(ms.METALLIC)


def shade(mat, nb, c, rc, up=None):
    """Light from the viewer's upper left, a little in front (as the pictures are lit); metal also glints.
    Returns brightness 0-1 and the glint, per sub-pixel."""
    up = U_ if up is None else up
    L = nz(-0.6 * rc + 0.75 * up + 0.25 * c) if up is U_ else nz(-0.5 * rc + 0.5 * up + 0.7 * c)
    H = nz(L + c)
    n = nb / np.maximum(np.linalg.norm(nb, axis=-1, keepdims=True), 1e-6)
    nl, nh, nv = n @ L, n @ H, np.abs(n @ c)
    v = 0.3 + 0.7 * np.clip(nl, 0, 1)
    v *= 1 - 0.3 * (1 - nv) ** 3
    met = np.isin(mat, list(METALLIC))
    mat[mat == -2] = -1
    glint = met & (np.clip(nh, 0, 1) ** 28 > 0.45)
    return v, glint


def down(mat, v, glint):
    """SS x SS sub-pixels to one hard pixel: covered if half are; its material the most common; brightness the mean."""
    H, W = mat.shape; h, w = H // SS, W // SS
    m4 = mat.reshape(h, SS, w, SS).transpose(0, 2, 1, 3).reshape(h, w, SS * SS)
    v4 = v.reshape(h, SS, w, SS).transpose(0, 2, 1, 3).reshape(h, w, SS * SS)
    g4 = glint.reshape(h, SS, w, SS).transpose(0, 2, 1, 3).reshape(h, w, SS * SS)
    cov = (m4 >= 0).mean(-1)
    solid = cov >= 0.45
    best = np.full((h, w), -1); bestn = np.zeros((h, w))
    for m in np.unique(m4[m4 >= 0]):
        k = (m4 == m).sum(-1)
        better = k > bestn
        best[better] = m; bestn[better] = k[better]
    vm = np.where(m4 >= 0, v4, 0).sum(-1) / np.maximum((m4 >= 0).sum(-1), 1)
    gm = (g4 & (m4 >= 0)).sum(-1) >= max(2, SS * SS // 4)
    best[~solid] = -1
    return best, vm, gm


def ramp_for(m, tier):
    """A material's ramp (dark, shadow, mid, light, glint) and a shift (brighter or darker than its ramp's usual
    band) for this piece's tier."""
    R = w.RAMPS
    met = R[tier] if tier in R else R['iron']
    fit = R['iron'] if tier in SOFT else met
    return {M['metal']: (met, 0), M['bright']: (met, 1), M['fit']: (fit, 0), M['wood']: (R['wood'], 0), M['grip']: (R['leather'], 0),
            M['dark']: (R['black'], -1), M['string']: (R['silk'], 0), M['red']: (R['red'], 0), M['blue']: (R['blue'], 0),
            M['gold']: (R['gold'], 0), M['horn']: (R['horn'], 0), M['feather']: (R['feather'], 0), M['plume']: (R['plume'], 0),
            M['wooddark']: (R['wood'], -1), M['back']: (R['wood'], 0), M['fuller']: (met, -1), M['gripdark']: (R['leather'], -1),
            M['rivet']: (fit, 1), M['crystal']: (R['adamantium'], 1), M['orb']: (R['purple'], 0), M['bone']: (R['bone'], 0),
            M['leaf']: (R['green'], 0), M['chitin']: (R['chitin'], 0), M['eye']: (R['spidereye'], 1), M['dbone']: (R['dragonbone'], 0),
            M['dhorn']: (R['dragonhorn'], 0), M['ember']: (R['ember'], 1), M['greenwood']: (R['green'], -1), M['rock']: (R['iron'], -1), M['ore']: (R['bronze'], 0), M['sack']: (R['wool'], 0), M['fish']: (R['silver'], 1)}[m]


def colour(best, vm, gm, tier):
    """Hard pixels in their ramps' bands: shadow, mid and light by brightness, the glint on metal's highlights,
    the ramp's darkest in deep shade; then the dragons' outline round the outside."""
    h, w_ = best.shape
    out = np.zeros((h, w_, 4), np.uint8)
    band = np.where(vm < 0.22, 0, 1 + np.round(np.clip((vm - 0.42) / 0.5, 0, 1) * 2)).astype(int)
    for m in np.unique(best[best >= 0]):
        rmp, sh = ramp_for(int(m), tier)
        sel = best == m
        b = np.clip(band[sel] + sh, 0, 4)
        if int(m) in METALLIC:
            b = np.where(gm[sel], 4, np.minimum(b, 3 if sh <= 0 else 4))
        else:
            b = np.minimum(b, 3)
        out[sel, :3] = np.array(rmp, np.uint8)[b]
        out[sel, 3] = 255
    return rm.outline(out)


def pieces():
    for s in ms.WEAPONS:
        yield 'weapon.' + s, ms.weapon(s), ([0] if s == 'bow' else [0, 1, 2, 3]), lambda pose, s=s: weapon_basis(s, pose)
    for s in ms.MAGIC + list(ms.SPECIAL):
        yield 'weapon.' + s, ms.magic(s), [0, 1, 2, 3], lambda pose, s=s: weapon_basis(s, pose)
    for s in ms.SHIELDS:
        yield 'shield.' + s, ms.shield(s), [0], lambda pose: shield_basis()
    for s in ms.HELMETS:
        yield 'helmet.' + s, ms.helmet(s), [0], lambda pose: helmet_basis()


def head():
    """The head a helmet sits on (meshes.HX, HY, HZ round its middle), drawn into the depth only: the back of the
    helmet behind it is hidden, as the picture's own head hides it in the game."""
    m = ms.ellipsoid([0, 0, 0], [ms.HY, ms.HX, ms.HZ], -2, seg=18, rings=10)
    return m.moved(np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1.0]]))


def fname(name, tier, pose):
    return f"g3p-{name.replace(' ', '_')}-{tier}-{pose}.png"


def main(out, tiers):
    os.makedirs(out, exist_ok=True)
    meta = dict(facings=FACINGS, tiers=tiers, pieces={})
    for name, mesh, poses, basis in pieces():
        meta['pieces'][name] = dict(poses=[])
        for pose in poses:
            B, off = basis(pose)
            P, N, Mt = placed(mesh, B, off)
            if name.startswith('helmet.'):
                hp, hn, hm = placed(head(), np.eye(3), np.zeros(3))
                P, N, Mt = np.concatenate([P, hp]), np.concatenate([N, hn]), np.concatenate([Mt, hm])
            cams = [camera(i) for i in range(FACINGS)]
            vis = Mt >= 0
            xs = [P[vis] @ rc for c, rc, u in cams]; ys = [-(P[vis] @ U_) for _ in cams]
            pad = 2
            x0 = int(np.floor(min(a.min() for a in xs))) - pad; x1 = int(np.ceil(max(a.max() for a in xs))) + pad
            y0 = int(np.floor(min(a.min() for a in ys))) - pad; y1 = int(np.ceil(max(a.max() for a in ys))) + pad
            cells = []
            for c, rc, u in cams:
                mat, nb = raster(P, N, Mt, c, rc, (x0, y0, x1, y1))
                v, g = shade(mat, nb, c, rc)
                cells.append(down(mat, v, g))
            W, H = x1 - x0, y1 - y0
            for tier in tiers:
                strip = np.zeros((H, W * FACINGS, 4), np.uint8)
                for i, (best, vm, gm) in enumerate(cells):
                    strip[:, i * W:(i + 1) * W] = colour(best, vm, gm, tier)
                save_indexed(strip, os.path.join(out, fname(name, tier, pose)))
            meta['pieces'][name]['poses'].append(dict(w=W, h=H, ax=-x0, ay=-y0))
        print(name, len(poses), 'poses', flush=True)
    json.dump(meta, open(os.path.join(out, 'gear3d-pix.json'), 'w'), separators=(',', ':'))
    print(os.path.join(out, 'gear3d-pix.json'))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2].split(',') if len(sys.argv) > 2 else TIERS)
