# Reference turnarounds (python3 refsheet.py OUT 'Race,..'): per race front (S), 3/4 at the game's
# 45-degree corner, side (E) and back (N), all pixel art at the sprite's own pixel size. The 3/4 is
# drafted from the sprite's own pixels: per row the side picture's run (back to front) and the
# front picture's run laid side by side, each foreshortened by cos 45, the top of the head and
# shoulders shown as at the game's pitch. These are targets for the 3D, to approve or correct.
import sys
import numpy as np
import inflate2, landmarks
from PIL import Image, ImageDraw

P = 64; K = 0.7071
import os
REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ref') + '/'

def body_run(alpha_row):
    rs = landmarks.runs(list(alpha_row))
    if not rs: return None
    return rs[0][0], rs[-1][1]

def three_quarter(S, E, mirror=False):
    """The unit seen from its front-left corner (its right side, the E picture, on the left)."""
    W = 96; out = np.zeros((P, W, 4), np.int32)
    sa = S[:, :, 3] > 0; ea = E[:, :, 3] > 0
    X0 = 52                                                         # where the sprite's middle column lands
    for r in range(P):
        if not sa[r].any() and not ea[r].any(): continue
        fr = body_run(sa[r]); sr = body_run(ea[r])
        # front: every front pixel, foreshortened about the middle
        if fr:
            a, b = fr
            for xo in range(W):
                xs = 32 + (xo + 0.5 - X0) / K
                xi = int(np.floor(xs))
                if 0 <= xi < P and sa[r, xi]: out[r, xo] = S[r, xi]
        # side: from the front picture's left edge, running back (left) by the side depth x cos 45
        if sr and fr:
            c, d = sr                                               # E: back at c, front at d (faces right)
            seam = X0 + (fr[0] - 32) * K                            # the front's left edge
            for xo in range(W):
                if xo + 0.5 >= seam: break
                zs = d - (seam - (xo + 0.5)) / K                     # side column, counted back from its front
                zi = int(np.floor(zs))
                if c <= zi <= d and ea[r, zi] and out[r, xo, 3] == 0: out[r, xo] = E[r, zi]
    # crop to content
    cols = np.nonzero((out[:, :, 3] > 0).any(0))[0]
    if len(cols):
        cx = (cols.min() + cols.max() + 1) // 2
        lo = max(0, cx - 32); out = out[:, lo:lo + 64]
        if out.shape[1] < 64: out = np.pad(out, ((0, 0), (0, 64 - out.shape[1]), (0, 0)))
    return out

def pixel_view(rc, yaw=45, pitch=37, M=None):
    """The 3D at the sprite's own pixel size (one sprite pixel = one pixel), locked to the sprite's
    palette, with the sprite's 1-pixel dark outline: a pixel-art drawing of the unit from the game's
    corner, to correct by hand."""
    import render3
    raw = inflate2.pictures(rc)
    if M is None: M, _ = inflate2.inflate(rc, style='warm')       # the sprites' own edge: dark outline, brown band inside
    # as tall as the front sprite: fit the render's height to the sprite's drawn rows
    sa = raw['S'][:, :, 3] > 0; rows = np.nonzero(sa.any(1))[0]; hgt = rows.max() - rows.min() + 1
    probe = render3.render(M, yaw, pitch, scale=4, size=320, stretch=1.2, foot=0.9, inner=False, outline=None, rim={})
    pr = np.nonzero((np.asarray(probe)[:, :, 3] > 0).any(1))[0]
    sc = 4 * (hgt * 4) / (pr.max() - pr.min() + 1)
    big = render3.render(M, yaw, pitch, scale=sc, size=256, stretch=1.2, foot=(rows.max() + 1) / 64.0, inner=True, outline=None)
    a = np.asarray(big).astype(np.int32)
    # down to 64 px: each pixel takes the commonest colour of its 4x4 block (crisp, no blending)
    out = np.zeros((P, P, 4), np.int32)
    for y in range(P):
        for x in range(P):
            blk = a[y * 4:(y + 1) * 4, x * 4:(x + 1) * 4].reshape(-1, 4)
            blk = blk[blk[:, 3] > 0]
            if len(blk) < 7: continue
            cc, kk = np.unique(blk[:, :3], axis=0, return_counts=True)
            out[y, x, :3] = cc[kk.argmax()]; out[y, x, 3] = 255
    # the sprite's own colours only
    pal = np.unique(np.concatenate([raw[f][raw[f][:, :, 3] > 0][:, :3] for f in 'SNEW']), axis=0)
    m = out[:, :, 3] > 0
    dd = np.abs(out[m][:, None, :3] - pal[None]).sum(-1)
    out[m, :3] = pal[dd.argmin(-1)]
    # the sprite's edge: the outermost pixel ring in the sprite's outline colour (drawn on the
    # figure's own edge, as the sprites do, not outside it), and a band of the head/arm rim colour
    # just inside it, as wide as the sprite draws it
    olc = np.array(inflate2.LAST.get('outline') or (0, 0, 0))
    pm = np.pad(m, 1, constant_values=False)
    edge = m & ~(pm[:-2, 1:-1] & pm[2:, 1:-1] & pm[1:-1, :-2] & pm[1:-1, 2:])
    out[edge, :3] = olc
    return out
    return out

def sheet(out, races, Kz=6):
    C = 64 * Kz
    labels = ['front', '3/4 (game camera)', 'side', 'back']
    img = Image.new('RGBA', (C * 4, (C + 30) * len(races) + 30), (52, 56, 66, 255))
    d = ImageDraw.Draw(img)
    for j, t in enumerate(labels): d.text((j * C + 10, 8), t, fill=(255, 255, 255, 255))
    for i, rc in enumerate(races):
        raw = inflate2.pictures(rc)
        q = pixel_view(rc)
        Image.fromarray(q.astype(np.uint8)).save(REF + rc.replace(' ', '') + '-34.png')   # the editable 64 px 3/4 drawing
        views = [raw['S'], q, raw['E'], raw['N']]
        for j, v in enumerate(views):
            im = Image.fromarray(v.astype(np.uint8)).resize((C, C), Image.NEAREST)
            img.alpha_composite(im, (j * C, 30 + i * (C + 30)))
        d.text((10, 30 + i * (C + 30) + C + 6), rc, fill=(240, 236, 220, 255))
        print(rc, flush=True)
    img.save(out)

if __name__ == '__main__':
    sheet(sys.argv[1], sys.argv[2].split(','))
