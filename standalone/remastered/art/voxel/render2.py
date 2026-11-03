import numpy as np, math
from PIL import Image, ImageDraw

DIRS = ((0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0), (0, 1, 0), (0, -1, 0))

def smooth_normals(M, sigma=1.4):
    solid = (M.col[:, :, :, 3] > 0).astype(float)
    k = np.exp(-0.5 * (np.arange(-4, 5) / sigma) ** 2); k /= k.sum()
    g = solid
    for ax in range(3): g = np.apply_along_axis(lambda m: np.convolve(m, k, mode='same'), ax, g)
    gr, gx, gz = np.gradient(g)
    # model space: x right, y up (= -row), z back; the normal points out of the solid
    nrm = np.stack([-gx, gr, -gz], -1)
    l = np.linalg.norm(nrm, axis=-1, keepdims=True); l[l == 0] = 1
    return nrm / l

def render(M, yaw, pitch, scale=4, size=300, outline=(30, 32, 38), light=True, sn=None):
    col = M.col; solid = col[:, :, :, 3] > 0; n = solid.shape[0]
    if sn is None and light: sn = smooth_normals(M)
    pad = np.pad(solid, 1)
    t = math.radians(yaw); p = math.radians(pitch)
    rv = np.array([math.cos(t), 0, -math.sin(t)])
    fv = np.array([math.sin(t) * math.cos(p), -math.sin(p), math.cos(t) * math.cos(p)])
    uv = np.array([math.sin(t) * math.sin(p), math.cos(p), math.cos(t) * math.sin(p)])
    Lt = np.array([-0.5, 0.75, -0.45]); Lt /= np.linalg.norm(Lt)
    rr, xx, zz = np.nonzero(solid)
    yy = n - 1 - rr
    items = []
    c0 = np.array([n / 2, n / 2, n / 2])
    for nrm in DIRS:
        nrm = np.array(nrm, float)
        if nrm @ fv >= 0: continue
        if nrm[2] == -1: nb = pad[rr + 1, xx + 1, zz]
        elif nrm[2] == 1: nb = pad[rr + 1, xx + 1, zz + 2]
        elif nrm[0] == -1: nb = pad[rr + 1, xx, zz + 1]
        elif nrm[0] == 1: nb = pad[rr + 1, xx + 2, zz + 1]
        elif nrm[1] == 1: nb = pad[rr, xx + 1, zz + 1]
        else: nb = pad[rr + 2, xx + 1, zz + 1]
        sel = ~nb
        for r, x, y, z in zip(rr[sel], xx[sel], yy[sel], zz[sel]):
            P = np.array([x, y, z], float)
            # face corners
            if nrm[2] != 0:
                zf = z + (1 if nrm[2] > 0 else 0); cs = [(x, y, zf), (x + 1, y, zf), (x + 1, y + 1, zf), (x, y + 1, zf)]
            elif nrm[0] != 0:
                xf = x + (1 if nrm[0] > 0 else 0); cs = [(xf, y, z), (xf, y, z + 1), (xf, y + 1, z + 1), (xf, y + 1, z)]
            else:
                yf = y + (1 if nrm[1] > 0 else 0); cs = [(x, yf, z), (x + 1, yf, z), (x + 1, yf, z + 1), (x, yf, z + 1)]
            cs = [np.array(c, float) for c in cs]
            ctr = sum(cs) / 4 - c0
            k = 1.0
            if light:
                # thin parts (shield plate, blade) by their face; the rest by the smoothed surface, so
                # a round helmet gets the sprite's flat light bands instead of block stripes
                pt = M.part[r, x, z]
                nn = getattr(M, 'plate', {}).get((r, x, z), nrm) if pt == 5 else nrm if pt == 6 else sn[r, x, z]
                d = nn @ Lt
                k = 1.0 if d > 0.55 else 0.93 if d > 0.15 else 0.83 if d > -0.25 else 0.74
                k *= 1.0 if nrm[1] > 0 else 0.95
            items.append((ctr @ fv, cs, tuple(int(min(255, v * k)) for v in col[r, x, z, :3])))
    items.sort(key=lambda t: -t[0])
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    for _, cs, c in items:
        pts = [(size / 2 + ((q - c0) @ rv) * scale, size * 0.52 - ((q - c0) @ uv) * scale) for q in cs]
        dr.polygon(pts, fill=c + (255,), outline=c + (255,))
    if outline:
        a = np.asarray(img)[:, :, 3] > 0
        o = np.zeros_like(a); k = max(1, int(round(scale * 0.9)))
        for dx in range(-k, k + 1):
            for dy in range(-k, k + 1):
                if dx * dx + dy * dy <= k * k + 1: o |= np.roll(np.roll(a, dx, 1), dy, 0)
        ring = o & ~a
        out = np.asarray(img).copy(); out[ring] = outline + (255,)
        img = Image.fromarray(out)
    return img
