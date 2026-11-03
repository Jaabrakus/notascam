# The 3D gear as smooth pictures from 16 facings (python3 smoothgear.py OUT [tiers] [--pixel]; --pixel: then made pixel
# art the dragons' way, at the units' own pixel size): as pixelgear.py (the same
# renders, poses, anchors and hidden head), but shaded smoothly instead of made pixel art: each piece's tier colours
# lit from the viewer's upper left, metal mirroring a sky over a darker ground with a glint, edges turning away
# darkened. Drawn on the page like the pixel strips (gear3d.js pixel mode reads the same gear3d-pix.json), so they
# cost the same. Each strip is sized to powers of two (the page then filters it smoothly, with mipmaps): a cell is
# about 2 to 4 picture pixels an art pixel, the strip padded on the right (fu: a cell's share of its width).
import json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pixelgear as pg   # noqa: E402

SUB = 2   # sub-pixels a picture pixel, each way
SHINE = {'iron': 0.55, 'silver': 0.8, 'gold': 0.75, 'bronze': 0.65, 'adamantium': 0.75, 'diamond': 0.95, 'hell': 0.5,
         'chitin': 0.45, 'dragon': 0.35, 'spiderfang': 0.4}
SOFT = pg.SOFT


def pot(n):
    p = 1
    while p < n:
        p *= 2
    return p


def smooth(mat, nb, c, rc, tier, up=None):
    """Colour and coverage per sub-pixel."""
    U = pg.U_ if up is None else up
    L = pg.nz(-0.6 * rc + 0.75 * U + 0.25 * c) if up is None else pg.nz(-0.5 * rc + 0.5 * U + 0.7 * c)
    H = pg.nz(L + c)
    n = nb / np.maximum(np.linalg.norm(nb, axis=-1, keepdims=True), 1e-6)
    nl, nv, nh = np.clip(n @ L, 0, 1), np.abs(n @ c), np.clip(n @ H, 0, 1)
    out = np.zeros(mat.shape + (3,))
    sp = SHINE.get(tier, 0.12 if tier in SOFT else 0.5)
    for m in np.unique(mat[mat >= 0]):
        m = int(m)
        rmp, sh = pg.ramp_for(m, tier)
        r = np.array(rmp, float)
        base = {0: r[1] + (r[2] - r[1]) * 0.75, 1: r[2] + (r[3] - r[2]) * 0.5}.get(sh + (0 if m in pg.METALLIC else 5), r[min(4, max(0, 2 + sh))])
        if m in pg.METALLIC and sh < 0:
            base = r[1] + (r[2] - r[1]) * 0.35
        sel = mat == m
        light = 0.5 + 0.7 * nl[sel]
        rim = 1 - 0.55 * (1 - nv[sel]) ** 3
        col = base[None, :] * (light * rim)[:, None]
        if m in pg.METALLIC:
            s = sp if tier not in SOFT or m in (pg.M['fit'], pg.M['rivet']) else 0.12
            Rv = 2 * (n[sel] @ c)[:, None] * n[sel] - c
            t = np.clip((Rv[:, 1] + 0.35) / 1.2, 0, 1); t = t * t * (3 - 2 * t)
            env = 0.65 + 0.7 * t
            col *= (1 + (env - 1) * s)[:, None]
            col += (s * 1.6 * nh[sel] ** 24 * 255)[:, None] * np.array([1, 0.97, 0.9])
        out[sel] = col
    return np.clip(out, 0, 255)


def pixelate(cells, colours=20):
    """Smooth cells (one strip's facings) made pixel art the dragons' way (beasts64.palette and pixelify): one fixed
    palette for the strip (so colours hold still as it turns), no dithering, hard edges, the dark outline."""
    import remaster64 as rm
    px = np.concatenate([c[c[..., 3] > 0][:, :3] for c in cells if (c[..., 3] > 0).any()])
    side = int(np.ceil(np.sqrt(len(px))))
    sample = np.zeros((side * side, 3), np.uint8); sample[:len(px)] = px; sample[len(px):] = px[0]
    pal = Image.fromarray(sample.reshape(side, side, 3)).quantize(colours, method=Image.Quantize.MEDIANCUT)
    out = []
    for c in cells:
        q = np.asarray(Image.fromarray(c[..., :3]).quantize(palette=pal, dither=Image.Dither.NONE).convert('RGB'))
        o = np.zeros_like(c); solid = c[..., 3] > 0
        o[solid, :3] = q[solid]; o[solid, 3] = 255
        out.append(rm.outline(o))
    return out


def base_col(m, tier):
    """A material's flat colour for a tier, the one smooth() lights (its ramp's middle; metal a little darker)."""
    rmp, sh = pg.ramp_for(m, tier)
    r = np.array(rmp, float)
    base = {0: r[1] + (r[2] - r[1]) * 0.75, 1: r[2] + (r[3] - r[2]) * 0.5}.get(sh + (0 if m in pg.METALLIC else 5), r[min(4, max(0, 2 + sh))])
    if m in pg.METALLIC and sh < 0:
        base = r[1] + (r[2] - r[1]) * 0.35
    return base


LUM = np.array([0.3, 0.59, 0.11])


def index_cell(mat, col, Hp, cw, sub, tier):
    """A cell as palette indices (INDEX): each pixel's material (R) and how bright it is against that material's flat
    colour (G, x100), so the page colours it for any tier or a player's own colours."""
    m4 = mat.reshape(Hp, sub, cw, sub).transpose(0, 2, 1, 3).reshape(Hp, cw, sub * sub)
    c4 = col.reshape(Hp, sub, cw, sub, 3).transpose(0, 2, 1, 3, 4).reshape(Hp, cw, sub * sub, 3)
    best = np.full((Hp, cw), -1); bn = np.zeros((Hp, cw))
    for m in np.unique(m4[m4 >= 0]):
        k = (m4 == m).sum(-1); better = k > bn; best[better] = m; bn[better] = k[better]
    cov = (m4 >= 0).mean(-1)
    out = np.zeros((Hp, cw, 4), np.uint8)
    for m in np.unique(best[best >= 0]):
        sel = (best == m) & (cov >= 0.5)
        if not sel.any():
            continue
        w = (m4[sel] == m)[..., None]
        avg = (c4[sel] * w).sum(1) / np.maximum(w.sum(1), 1)
        lv = (avg @ LUM) / max(1.0, float(base_col(int(m), tier) @ LUM))
        out[sel, 0] = m; out[sel, 1] = np.clip(lv * 100, 0, 255); out[sel, 3] = 255
    return out


def band_index(cells, k=5):
    """The strip's pixels banded the dragons' way: each material's brightness to at most k fixed levels for the whole
    strip (so they hold still as it turns), then the dark outline round it (R 254: G the material it borders, B its
    brightness)."""
    import remaster64 as rm
    allpx = np.concatenate([c.reshape(-1, 4) for c in cells])
    for m in np.unique(allpx[allpx[:, 3] > 0, 0]):
        v = allpx[(allpx[:, 3] > 0) & (allpx[:, 0] == m), 1].astype(float)
        ctr = np.unique(np.percentile(v, np.linspace(10, 90, min(k, len(np.unique(v))))))
        for _ in range(8):
            a = np.argmin(np.abs(v[:, None] - ctr[None]), 1)
            ctr = np.array([v[a == j].mean() if (a == j).any() else ctr[j] for j in range(len(ctr))])
        for c in cells:
            sel = (c[..., 3] > 0) & (c[..., 0] == m)
            if sel.any():
                c[sel, 1] = np.clip(np.round(ctr[np.argmin(np.abs(c[sel, 1][:, None].astype(float) - ctr[None]), 1)]), 0, 255)
    out = []
    for c in cells:
        al = c[..., 3] > 0
        o = c.copy()
        h, w_ = al.shape
        pa = np.pad(al, 1); pm = np.pad(c[..., 0], 1); pl = np.pad(c[..., 1], 1)
        ring = ~al & (sum(pa[1 + dy:1 + dy + h, 1 + dx:1 + dx + w_] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))) > 0)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):   # the touching material and its brightness
            nb_ = pa[1 + dy:1 + dy + h, 1 + dx:1 + dx + w_] & ring & (o[..., 0] != 254)
            o[nb_, 1] = pm[1 + dy:1 + dy + h, 1 + dx:1 + dx + w_][nb_]; o[nb_, 2] = pl[1 + dy:1 + dy + h, 1 + dx:1 + dx + w_][nb_]; o[nb_, 0] = 254
        o[ring, 3] = 255
        out.append(o)
    return out


def index_meta():
    """How the page colours index pictures: each tier's ramp for each material, each material's shift and whether it
    shines, and the ramps (wearables64.RAMPS) themselves, so a player's own colours are a ramp name a material."""
    import wearables64 as w
    names = {id(v): k for k, v in w.RAMPS.items()}
    use = {}
    for t in w.RAMPS:
        use[t] = [names.get(id(pg.ramp_for(m, t)[0]), 'iron') if m in pg.M.values() else 'iron' for m in range(32)]
    sh = [pg.ramp_for(m, 'iron')[1] if m in pg.M.values() else 0 for m in range(32)]
    return dict(ramps={k: [list(map(int, c)) for c in v] for k, v in w.RAMPS.items()}, use=use, sh=sh, met=sorted(int(m) for m in pg.METALLIC))


INDEX = False


def main(out, tiers, pixel=False):
    """pixel: the smooth renders made pixel art at the units' own pixel size (1 picture pixel an art pixel)."""
    os.makedirs(out, exist_ok=True)
    sys.path.insert(0, os.path.join(HERE, '..', 'enhance'))
    meta = dict(facings=pg.FACINGS, tiers=tiers, smooth=not pixel, pieces={})
    if INDEX:
        meta['index'] = index_meta()
    all_tiers = tiers
    for name, mesh, poses, basis in pg.pieces():
        tiers = pg.piece_tiers(name, all_tiers)
        meta['pieces'][name] = dict(poses=[], tiers=tiers)
        if INDEX:   # one picture for every tier, coloured on the page; drawn with its own tier's light (iron when it has it)
            ref = 'iron' if 'iron' in tiers else tiers[0]
            meta['pieces'][name]['ref'] = ref
            tiers = [ref]
        for pose in poses:
            B, off = basis(pose)
            P, N, Mt = pg.placed(mesh, B, off)
            if name.startswith('helmet.'):
                hp, hn, hm = pg.placed(pg.head(), np.eye(3), np.zeros(3))
                P, N, Mt = np.concatenate([P, hp]), np.concatenate([N, hn]), np.concatenate([Mt, hm])
            cams = [pg.camera(i) for i in range(pg.FACINGS)]
            vis = Mt >= 0
            xs = [P[vis] @ rc for c, rc, u in cams]; ys = [-(P[vis] @ pg.U_) for _ in cams]
            x0 = np.floor(min(a.min() for a in xs)) - 1; x1 = np.ceil(max(a.max() for a in xs)) + 1
            y0 = np.floor(min(a.min() for a in ys)) - 1; y1 = np.ceil(max(a.max() for a in ys)) + 1
            h = y1 - y0
            Hp = int(h) if pixel else pot(int(np.ceil(h * 2)))   # the strip's height: at least 2 picture pixels an art pixel
            R = Hp / h                               # picture pixels an art pixel
            cw = int(np.ceil((x1 - x0) * R))         # a cell's width in picture pixels
            Wp = cw * pg.FACINGS if pixel else pot(cw * pg.FACINGS)
            sub = 4 if pixel else SUB
            wa = cw / R                              # ... in art pixels
            strips = {t: np.zeros((Hp, Wp, 4), np.uint8) for t in tiers}
            cells = {t: [] for t in tiers}
            box = (x0, y0, x0 + wa, y1)
            old = pg.SS
            pg.SS = R * sub
            for i, (c, rc, u) in enumerate(cams):
                mat, nb = pg.raster(P, N, Mt, c, rc, box)
                mat[mat == -2] = -1
                Hs, Ws = mat.shape
                Hs2, Ws2 = Hp * sub, cw * sub
                mat = mat[:Hs2, :Ws2]; nb = nb[:Hs2, :Ws2]
                if mat.shape != (Hs2, Ws2):
                    pm = np.full((Hs2, Ws2), -1); pm[:mat.shape[0], :mat.shape[1]] = mat
                    pn = np.zeros((Hs2, Ws2, 3)); pn[:nb.shape[0], :nb.shape[1]] = nb
                    mat, nb = pm, pn
                cov = (mat >= 0).reshape(Hp, sub, cw, sub).mean((1, 3))
                if INDEX:
                    cells[tiers[0]].append(index_cell(mat, smooth(mat, nb, c, rc, tiers[0]), Hp, cw, sub, tiers[0]))
                    continue
                for t in tiers:
                    col = smooth(mat, nb, c, rc, t)
                    w = (mat >= 0)[..., None]
                    acc = (col * w).reshape(Hp, sub, cw, sub, 3).sum((1, 3))
                    k = np.maximum((mat >= 0).reshape(Hp, sub, cw, sub).sum((1, 3)), 1)[..., None]
                    cell = np.zeros((Hp, cw, 4), np.uint8)
                    cell[..., :3] = (acc / k).astype(np.uint8)
                    cell[..., 3] = np.where(cov >= 0.5, 255, 0)
                    cells[t].append(cell)
            for t in tiers:
                for i, cell in enumerate(band_index(cells[t]) if INDEX else pixelate(cells[t]) if pixel else cells[t]):
                    strips[t][:, i * cw:(i + 1) * cw] = cell
            pg.SS = old
            for t in tiers:
                Image.fromarray(strips[t]).save(os.path.join(out, pg.fname(name, 'idx' if INDEX else t, pose)), optimize=True)
            C = dict(w=round(wa, 3), h=h, ax=-x0, ay=-y0)
            if not pixel:
                C['fu'] = cw / Wp
            meta['pieces'][name]['poses'].append(C)
        print(name, len(poses), 'poses', flush=True)
    ground(out, all_tiers, pixel, meta)
    json.dump(meta, open(os.path.join(out, 'gear3d-pix.json'), 'w'), separators=(',', ':'))
    print(os.path.join(out, 'gear3d-pix.json'))


# Each piece lying on the ground, seen from above: what a dropped piece becomes once it lies still (the page stops
# drawing its 3D model then). A weapon flat side up along x, a shield face up, a helmet on its rim; the middle of the
# piece at the picture's anchor. Written as g3p-<piece>-<tier>-g.png, its size in meta pieces[..].ground.
def ground(out, tiers, pixel, meta):
    import meshes as ms
    X, Y, Z = np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])
    lying = {'weapon': np.stack([X, -Z, Y], 1), 'shield': np.stack([X, -Z, Y], 1), 'helmet': np.stack([-X, Y, Z], 1)}
    c, rc, up = Y, X, -Z   # the camera above, the picture's right east, its up north
    for name, mesh, poses, basis in pg.pieces():
        tiers_here = pg.piece_tiers(name, tiers)
        if INDEX:
            tiers_here = [meta['pieces'][name]['ref']]
        B = lying[name.split('.')[0]]
        P, N, Mt = pg.placed(mesh, B, np.zeros(3))
        mid = (P.min(0) + P.max(0)) / 2; P = P - np.array([mid[0], 0, mid[2]])
        x0 = np.floor((P @ rc).min()) - 1; x1 = np.ceil((P @ rc).max()) + 1
        y0 = np.floor((-(P @ up)).min()) - 1; y1 = np.ceil((-(P @ up)).max()) + 1
        w, h = x1 - x0, y1 - y0
        R = 1.0 if pixel else max(2.0, 64 / max(w, h))   # smooth: about 64 picture pixels across its long side
        cw, ch = int(np.ceil(w * R)), int(np.ceil(h * R))
        Wp, Hp = (cw, ch) if pixel else (pot(cw), pot(ch))
        sub = 4 if pixel else SUB
        old = pg.SS; pg.SS = R * sub
        mat, nb = pg.raster(P, N, Mt, c, rc, (x0, y0, x0 + cw / R, y0 + ch / R), up=up)
        pg.SS = old
        mat = mat[:ch * sub, :cw * sub]; nb = nb[:ch * sub, :cw * sub]
        cov = (mat >= 0).reshape(ch, sub, cw, sub).mean((1, 3))
        for t in tiers_here:
            col = smooth(mat, nb, c, rc, t, up=up)
            if INDEX:
                cell = band_index([index_cell(mat, col, ch, cw, sub, t)])[0]
                img = np.zeros((Hp, Wp, 4), np.uint8); img[:ch, :cw] = cell
                Image.fromarray(img).save(os.path.join(out, pg.fname(name, 'idx', 'g')), optimize=True)
                continue
            wgt = (mat >= 0)[..., None]
            acc = (col * wgt).reshape(ch, sub, cw, sub, 3).sum((1, 3))
            k = np.maximum((mat >= 0).reshape(ch, sub, cw, sub).sum((1, 3)), 1)[..., None]
            cell = np.zeros((ch, cw, 4), np.uint8); cell[..., :3] = (acc / k).astype(np.uint8); cell[..., 3] = np.where(cov >= 0.5, 255, 0)
            if pixel:
                cell = pixelate([cell])[0]
            img = np.zeros((Hp, Wp, 4), np.uint8); img[:ch, :cw] = cell
            Image.fromarray(img).save(os.path.join(out, pg.fname(name, t, 'g')), optimize=True)
        meta['pieces'][name]['ground'] = dict(w=round(cw / R, 3), h=round(ch / R, 3), ax=round(-x0, 3), ay=round(-y0, 3), u1=cw / Wp, v1=ch / Hp)
    print('ground pictures', len(meta['pieces']), flush=True)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a not in ('--pixel', '--index')]
    INDEX = '--index' in sys.argv   # palette pictures (pixel art): implies --pixel
    main(args[0], args[1].split(',') if len(args) > 1 else pg.TIERS, pixel='--pixel' in sys.argv or INDEX)
