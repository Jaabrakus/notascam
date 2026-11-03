# Renders a Grid (build3d2) the way the game camera would see it: orthographic, turned by yaw,
# tilted by pitch, optionally stretched up (stretch) so it stands as tall on screen as the
# sprite does. Light comes in flat bands from smoothed normals; a dark outline goes round it.
import numpy as np, math
from PIL import Image, ImageDraw

def smooth_normals(G, sigma=1.3):
    s = G.solid().astype(np.float32)
    rad = int(3 * sigma); k = np.exp(-0.5 * (np.arange(-rad, rad + 1) / sigma) ** 2); k /= k.sum()
    g = s
    for ax in range(3):
        acc = np.zeros_like(g); pad = [(0, 0)] * 3; pad[ax] = (rad, rad); gp = np.pad(g, pad)
        for i, kv in enumerate(k):
            sl = [slice(None)] * 3; sl[ax] = slice(i, i + g.shape[ax]); acc += kv * gp[tuple(sl)]
        g = acc
    gr, gx, gz = np.gradient(g)
    nrm = np.stack([-gx, gr, -gz], -1)          # model space: x right, y up, z back; out of the solid
    l = np.linalg.norm(nrm, axis=-1, keepdims=True); l[l == 0] = 1
    return nrm / l

NORMALS = [(0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0), (0, 1, 0), (0, -1, 0)]
# corners of each face of the unit cube at the origin (x, y, z), y up
CORNERS = {
    (0, 0, -1): [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], (0, 0, 1): [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
    (-1, 0, 0): [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)], (1, 0, 0): [(1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)],
    (0, 1, 0): [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)], (0, -1, 0): [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]}

def render(G, yaw, pitch, scale=4, size=300, stretch=1.0, outline=None, sn=None, bands=True, shadow=False, foot=0.84, inner=False, rim=None):
    """scale: screen pixels per sprite pixel; foot: how far down the picture the ground sits.
    outline: the line colour (default the model's own, else a dark grey); rim: {part: (colour,
    width in sprite pixels)} - a band of that colour just inside the silhouette, like the brown
    band the sprites draw inside their outline round the head (default the model's own)."""
    if outline is None: outline = tuple(getattr(G, 'outline_col', (30, 32, 38)))
    if rim is None: rim = getattr(G, 'rim', None)
    sub = G.sub; n = G.n; solid = G.solid()
    if sn is None: sn = getattr(G, 'sn', None)
    if sn is None: sn = smooth_normals(G)
    lit = getattr(G, 'lit', None); ao = getattr(G, 'ao', None)
    pad = np.pad(solid, 1)
    t = math.radians(yaw); p = math.radians(pitch)
    rv = np.array([math.cos(t), 0, -math.sin(t)])
    fv = np.array([math.sin(t) * math.cos(p), -math.sin(p), math.cos(t) * math.cos(p)])
    uv = np.array([math.sin(t) * math.sin(p), math.cos(p), math.cos(t) * math.sin(p)])
    Lt = np.array([-0.5, 0.75, -0.45]); Lt /= np.linalg.norm(Lt)
    rr, xx, zz = np.nonzero(solid)
    gc = getattr(G, 'center', (n / 2, n / 2)); c0 = np.array([gc[0], 0, gc[1]])   # turn about the unit's middle
    polys, depths, cols, pids, facs = [], [], [], [], []
    slope = getattr(G, 'slope_lines', False)
    for nrm in NORMALS:
        if np.array(nrm) @ fv >= 0: continue
        dx, dy, dz = nrm
        nb = pad[rr + 1 - dy, xx + 1 + dx, zz + 1 + dz]
        sel = ~nb
        r, x, z = rr[sel], xx[sel], zz[sel]
        base = np.stack([x, n - 1 - r, z], -1).astype(float)
        cs = base[:, None, :] + np.array(CORNERS[nrm], float)[None]          # (m, 4, 3) blocks
        w = (cs - c0) / sub; w[..., 1] *= stretch                             # sprite pixels
        sx = size / 2 + (w @ rv) * scale; sy = size * foot - (w @ uv) * scale
        ctr = w.mean(1); depths.append(ctr @ fv)
        polys.append(np.stack([sx, sy], -1))
        c = G.col[r, x, z, :3].astype(float)
        if bands:
            dd = sn[r, x, z] @ Lt
            if getattr(G, 'smooth_light', False):
                # soft light: a smooth ramp from the shadow side to the lit side, no bands (the
                # bands drew terraces across round heads)
                k = 0.70 + 0.36 * np.clip((dd + 0.45) / 1.3, 0, 1) ** 0.9
            else:
                k = np.select([dd > 0.55, dd > 0.15, dd > -0.25], [1.0, 0.93, 0.83], 0.74)
            if nrm[1] <= 0: k = k * 0.96
            if lit is not None: k = np.where(lit[r, x, z], 1.0 if nrm[1] > 0 else 0.97, k)   # already lit by its painter
            if ao is not None: k = k * ao[r, x, z]                         # creases darker (the sprites' shadow between parts)
            c = c * k[:, None]
        cols.append(np.clip(c, 0, 255).astype(int))
        pids.append(getattr(G, 'part', G.owner)[r, x, z] if hasattr(G, 'owner') else np.zeros(len(r), int))
        if slope:
            facs.append(np.clip(-(sn[r, x, z] @ fv), 0, 1))                 # how squarely it faces the camera
    P_ = np.concatenate(polys); D = np.concatenate(depths); C = np.concatenate(cols)
    order = np.argsort(-D)
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    ids_on = inner or bool(rim)
    if ids_on:
        dimg = Image.new('I', (size, size), 0); dd_ = ImageDraw.Draw(dimg)
        iimg = Image.new('I', (size, size), 0); di_ = ImageDraw.Draw(iimg)
        PID = np.concatenate(pids)
        if slope:
            fimg = Image.new('I', (size, size), 1000); df_ = ImageDraw.Draw(fimg); FAC = np.concatenate(facs)
    for i in order:
        q = P_[i]; c = tuple(C[i]) + (255,)
        dr.polygon([tuple(q[0]), tuple(q[1]), tuple(q[2]), tuple(q[3])], fill=c, outline=c)
        if ids_on:
            dd_.polygon([tuple(q[0]), tuple(q[1]), tuple(q[2]), tuple(q[3])], fill=int(100000 + D[i] * 100), outline=int(100000 + D[i] * 100))
            di_.polygon([tuple(q[0]), tuple(q[1]), tuple(q[2]), tuple(q[3])], fill=int(PID[i]), outline=int(PID[i]))
            if slope: df_.polygon([tuple(q[0]), tuple(q[1]), tuple(q[2]), tuple(q[3])], fill=int(FAC[i] * 1000), outline=int(FAC[i] * 1000))
    if rim:
        # the band inside the silhouette, on the parts that have one
        a0 = np.asarray(img)[:, :, 3] > 0; ids = np.asarray(iimg)
        out_ = np.asarray(img).copy()
        for pid, (rc_, wd) in rim.items():
            k = max(1, int(round(scale * wd)))
            op = np.pad(~a0, k, constant_values=True); near = np.zeros_like(a0)
            for ox in range(-k, k + 1):
                for oy in range(-k, k + 1):
                    if ox * ox + oy * oy <= k * k: near |= op[k + oy:k + oy + a0.shape[0], k + ox:k + ox + a0.shape[1]]
            out_[near & a0 & (ids == pid)] = tuple(rc_) + (255,)
        img = Image.fromarray(out_)
    if inner:
        # where a nearer part covers a farther one, a dark line on the farther side - the sprites'
        # black lines between arm and body, under the chin, between the legs
        dep = np.asarray(dimg).astype(float); a0 = np.asarray(img)[:, :, 3] > 0
        line = np.zeros(dep.shape, bool)
        # a surface turned away from the camera (the crown's dome seen from the front) steps far in
        # depth from pixel to pixel without anything covering it: there the step must be larger
        jmp = 220.0 / np.clip(np.asarray(fimg) / 1000.0, 0.3, 1.0) if slope else 220.0
        for oy, ox in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = np.roll(np.roll(dep, oy, 0), ox, 1); nba = np.roll(np.roll(a0, oy, 0), ox, 1)
            line |= a0 & nba & (dep - nb > jmp)                         # this pixel is over 2.2 px behind its neighbour
            ids = np.asarray(iimg); nbi = np.roll(np.roll(ids, oy, 0), ox, 1)
            nl = list(getattr(G, 'noline', ()))
            if nl: nbi = np.where(np.isin(nbi, nl) | np.isin(ids, nl), ids, nbi)
            line |= a0 & nba & (ids != nbi) & (dep - nb > 90) & (np.abs(ids - nbi) < 9000)   # where two parts meet (not gear on skin), on the farther one
        ml = getattr(G, 'min_line', 0)
        if ml:
            # no stray dashes: a line shorter than ml sprite pixels is a crease of the voxel steps,
            # not one of the sprite's lines
            lim = ml * scale; lab = np.zeros(line.shape, np.int32); seen = 0
            ys, xs = np.nonzero(line)
            for y0, x0 in zip(ys, xs):
                if lab[y0, x0]: continue
                seen += 1; st = [(y0, x0)]; lab[y0, x0] = seen; comp = [(y0, x0)]
                while st:
                    y, x = st.pop()
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            yy, xx = y + dy, x + dx
                            if 0 <= yy < line.shape[0] and 0 <= xx < line.shape[1] and line[yy, xx] and not lab[yy, xx]:
                                lab[yy, xx] = seen; st.append((yy, xx)); comp.append((yy, xx))
                cy = [q[0] for q in comp]; cx = [q[1] for q in comp]
                if max(max(cy) - min(cy), max(cx) - min(cx)) < lim:
                    for q in comp: line[q] = False
        k = max(1, int(round(scale * 0.8)))                              # as thick as the sprites' own lines
        lp = np.pad(line, k); grown = np.zeros_like(line)
        for oy in range(-k + 1, 1):
            for ox in range(-k + 1, k):
                grown |= lp[k + oy:k + oy + line.shape[0], k + ox:k + ox + line.shape[1]]
        lc = tuple(getattr(G, 'line_col', outline))
        out_ = np.asarray(img).copy(); out_[grown & a0 & (dep >= 0)] = lc + (255,)
        img = Image.fromarray(out_)
    if outline:
        a = np.asarray(img)[:, :, 3] > 0
        k = max(1, int(round(scale * 0.85)))
        ap = np.pad(a, k); o = np.zeros_like(a)
        for ox in range(-k, k + 1):
            for oy in range(-k, k + 1):
                if ox * ox + oy * oy <= k * k + 1: o |= ap[k + oy:k + oy + a.shape[0], k + ox:k + ox + a.shape[1]]
        out = np.asarray(img).copy(); out[o & ~a] = outline + (255,)
        img = Image.fromarray(out)
    if shadow:
        # a soft dark patch on the ground under the unit's middle, drawn beneath it
        g = (np.array([gc[0], -0.5, gc[1]]) - c0) / sub
        gx, gy = size / 2 + (g @ rv) * scale, size * foot - (g @ uv) * scale
        rx, ry = 13 * scale, 13 * scale * math.sin(p)
        sh = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([gx - rx, gy - ry, gx + rx, gy + ry], fill=(0, 0, 0, 70))
        sh.alpha_composite(img); img = sh
    return img
