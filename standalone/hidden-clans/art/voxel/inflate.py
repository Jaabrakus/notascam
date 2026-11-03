# "Balloon" a sprite into 3D: every pixel of the front picture becomes a column of blocks whose
# thickness grows with its distance from the picture's edge (and from the sprite's own black
# lines, so arms and body stay apart with a crease between), like blowing up a balloon in the
# sprite's shape. The front half shows the front picture, pixel for pixel; the back half the
# back picture. Seen straight on it IS the sprite; from the iso camera it is a puffy figure.
import sys, numpy as np, dmi, landmarks, build3d9, render3
from PIL import Image

P = 64

def distance(mask):
    """Distance (in pixels) from each pixel in mask to the nearest pixel outside it."""
    INF = 1e9
    d = np.where(mask, INF, 0.0)
    # two-pass chamfer (good enough at 64 px)
    a, b = 1.0, 1.4142
    for y in range(P):
        for x in range(P):
            if d[y, x] == 0: continue
            v = d[y, x]
            if y > 0: v = min(v, d[y - 1, x] + a, d[y - 1, x - 1] + b if x > 0 else INF, d[y - 1, x + 1] + b if x < P - 1 else INF)
            else: v = 0.5
            if x > 0: v = min(v, d[y, x - 1] + a)
            else: v = min(v, 0.5)
            d[y, x] = v
    for y in range(P - 1, -1, -1):
        for x in range(P - 1, -1, -1):
            if d[y, x] == 0: continue
            v = d[y, x]
            if y < P - 1: v = min(v, d[y + 1, x] + a, d[y + 1, x + 1] + b if x < P - 1 else INF, d[y + 1, x - 1] + b if x > 0 else INF)
            else: v = min(v, 0.5)
            if x < P - 1: v = min(v, d[y, x + 1] + a)
            else: v = min(v, 0.5)
            d[y, x] = v
    return d

def inflate(race, sub=2, depth_scale=1.0, line_crease=True):
    st = dmi.load(landmarks.R + race + '.dmi')[landmarks.body_state(race)]
    S = np.asarray(dmi.frame(st, 'S').convert('RGBA')).astype(np.int32)
    N = np.asarray(dmi.frame(st, 'N').convert('RGBA')).astype(np.int32)
    E = np.asarray(dmi.frame(st, 'E').convert('RGBA')).astype(np.int32)
    alpha = S[:, :, 3] > 0
    lum = S[:, :, :3].sum(2)
    # the sprite's black gaps (between arms and body, between the legs) are empty space, not
    # skin: black pixels joined to the outside through black pixels. Pupils and mouths stay.
    black = alpha & (lum < 40)
    gap = np.zeros((P + 2, P + 2), bool); gap[np.pad(~alpha, 1)] = True
    bl = np.pad(black, 1)
    for _ in range(P):
        g2 = gap.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            g2 |= np.roll(np.roll(gap, dy, 0), dx, 1)
        new_ = g2 & bl & ~gap
        if not new_.any(): break
        gap |= new_
    gap = gap[1:-1, 1:-1] & alpha
    alpha = alpha & ~gap
    inside = alpha
    d = distance(inside)
    # the colours: the outline's dark rim filled in from the colours beside it, so the balloon's
    # sides are skin (the renderer draws its own outline); the face keeps its eyes and mouth
    import build3d10, build3d11
    Sp = build3d10.parts_of(race); hrows = sorted(Sp['head']); hcols = [c for r_ in hrows for c in Sp['head'][r_]]
    fb = ((hrows[0] + 2, Sp['neck'] + 1), (min(hcols) + 2, max(hcols) - 1))
    S_raw = S
    S = build3d11.clean_picture(S, fb); N = build3d11.clean_picture(N, None)
    S[:, :, 3] = np.where(alpha, 255, 0)
    # local half-width: the largest distance nearby (so a tube gets a round cross-section)
    w = d.copy()
    for _ in range(3):
        p = np.pad(w, 1)
        w = np.maximum.reduce([p[1:-1, 1:-1], p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]]) * (d > 0)
        w = np.maximum(w, d)
    h = np.sqrt(np.clip(w ** 2 - (w - d) ** 2, 0, None))
    # smoothed, so the balloon is round, not ridged along the middle of each part
    k1 = np.array([1, 4, 6, 4, 1], float); k1 /= k1.sum()
    def blur(a):
        a = np.apply_along_axis(lambda v: np.convolve(v, k1, 'same'), 0, a)
        return np.apply_along_axis(lambda v: np.convolve(v, k1, 'same'), 1, a)
    for _ in range(2):
        m_ = alpha.astype(float)
        h = np.where(alpha, blur(h * m_) / np.maximum(blur(m_), 1e-3), 0)
        h = np.minimum(h, np.sqrt(np.clip(d * (2 * np.maximum(w, d) - d), 0, None)) * 1.15 + 0.5)   # still round at the edges
    # as deep as the side picture: each row's thickest point is blown up to the side picture's
    # half-depth at that row (thinner parts - arms, ears - in proportion)
    for r in range(P):
        zcols = np.nonzero(E[r, :, 3] > 0)[0]
        if not len(zcols) or h[r].max() <= 0: continue
        half = (zcols.max() - zcols.min() + 1) / 2
        h[r] *= min(half / h[r].max(), 3.0)
    h = np.where(alpha, np.maximum(h * depth_scale, 0.5), 0)
    # the body's middle in depth, per row, from the side picture (so a hunch or a belly shows)
    zc = np.full(P, 31.5)
    for r in range(P):
        cols = np.nonzero(E[r, :, 3] > 0)[0]
        if len(cols): zc[r] = P - 1 - (cols.min() + cols.max()) / 2
    zc = np.convolve(np.pad(zc, 3, mode='edge'), np.ones(7) / 7, 'valid')
    n = P * sub
    owner = np.zeros((n, n, n), np.int32); col = np.zeros((n, n, n, 4), np.int32)
    zz = (np.arange(n) + 0.5) / sub
    for r in range(P):
        for c in range(P):
            if not alpha[r, c]: continue
            z0, z1 = zc[r] - h[r, c], zc[r] + h[r, c]
            ks = np.nonzero((zz >= z0) & (zz <= z1))[0]
            if not len(ks): ks = np.array([int(zc[r] * sub)])
            front = zz[ks] < zc[r]
            back_c = N[r, P - 1 - c]
            if back_c[3] == 0: back_c = S[r, c]
            for a in range(sub):
                for b in range(sub):
                    R_, X_ = r * sub + a, c * sub + b
                    owner[R_, X_, ks] = 1
                    col[R_, X_, ks[front]] = S[r, c]
                    col[R_, X_, ks[~front]] = back_c
    lit = np.zeros(owner.shape, bool)
    M = build3d9.Model(sub, n, owner, col, lit, (32.0 * sub, 31.5 * sub))
    return M, S_raw

if __name__ == '__main__':
    out, races = sys.argv[1], sys.argv[2].split(',')
    K = 5; C = 64 * K
    img = Image.new('RGBA', (C * 5, C * len(races)), (52, 56, 66, 255))
    for i, rc in enumerate(races):
        M, S = inflate(rc)
        bg = Image.new('RGBA', (C, C), (60, 64, 76, 255)); bg.alpha_composite(Image.fromarray(S.astype(np.uint8)).resize((C, C), Image.NEAREST))
        img.alpha_composite(bg, (0, i * C))
        img.alpha_composite(render3.render(M, 0, 0, scale=K, size=C, foot=1.0, inner=True), (C, i * C))
        img.alpha_composite(render3.render(M, 90, 0, scale=K, size=C, foot=1.0, inner=True), (2 * C, i * C))
        img.alpha_composite(render3.render(M, 45, 37, scale=K * 0.9, size=C, stretch=1.2, foot=0.86, shadow=True, inner=True), (3 * C, i * C))
        img.alpha_composite(render3.render(M, 315, 37, scale=K * 0.9, size=C, stretch=1.2, foot=0.86, shadow=True, inner=True), (4 * C, i * C))
        print(rc, flush=True)
    img.save(out)
