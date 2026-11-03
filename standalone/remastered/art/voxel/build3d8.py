# The 3D human in any gear, cleaner (after build3d7.py, which copied each sprite's pixel pattern
# onto the 3D surfaces and came out as speckle). Now the sprites only say WHICH material is where
# (metal, cloth, leather, a belt, an emblem: the layer's colour ramps, with specks smaller than
# a few pixels merged away), and each armour type draws its own regular pattern in those
# colours: plate bands (from the sprite's rows), banded strips, mail rings, overlapping scales,
# lamellar slats with lacing, brigandine studs, leather studs; cloth is plain. Helmets are clean
# metal with a riveted rim and their own parts (no picture pasted on the dome). Same rig,
# weapons and shields as build3d7.
import numpy as np, math
import compose64, carve
import build3d7
from build3d2 import P, arr, filled
from build3d import deoutline
from build3d3 import SEAM, plate_rows, LIGHT
from build3d4 import skin_face
from build3d6 import Space, swing_point, Grid, Rig, CZ, SHOULDER_R, SHOULDER_L, HIP_ROW
from build3d7 import Loadout, Layer, sector, limb_space, hsv, GEAR, KNIGHT
import build3d7 as _b7

def band(n):
    """Light bands from the 3D light; the brightest only head-on to it (no white blotches)."""
    return np.searchsorted(np.array([-0.5, 0.6, 0.97]), n @ LIGHT)
build3d7.band = band          # lit() and the weapons/shields use the same bands

def levels_of(ks, n):
    """The shade (ramp index) for each light band -- shadow, plain, toward the light, head-on --
    taken from how the sprite spreads its own pixels over the ramp."""
    if not len(ks):
        m = (n - 1) // 2; return np.clip(np.array([m - 1, m, m + 1, m + 2]), 0, n - 1)
    q = np.round(np.percentile(ks, [8, 42, 68, 99])).astype(int)
    return np.maximum.accumulate(np.clip(q, 0, n - 1))

def lit(ramp, base, extra=None, normal=None):
    """A plain material from a ramp, shaded by the 3D light. base: the shade at the middle band,
    or the four band levels (levels_of)."""
    R = np.array(ramp)
    def paint(r, x, z, n):
        if normal is not None: n = normal(r, x, z)
        b = band(n)
        i = np.asarray(base)[b] if np.ndim(base) else base + b - 1
        if extra is not None: i = extra(r, x, z, i)
        out = R[np.clip(i, 0, len(R) - 1)].copy(); out[i <= -50] = SEAM
        return out
    return paint
build3d7.lit = lit

# ---------- which material is where ----------
def clean_regions(L, smallest=9):
    """Per facing: the layer's ramp id at each pixel, with specks (rivets, lace dots, ring
    highlights in another ramp) merged into what surrounds them. -1 where nothing is drawn."""
    L.region = {}
    for d in 'SNEW':
        g = L.gid[d].copy(); seen = np.zeros(g.shape, bool)
        for r0 in range(P):
            for c0 in range(P):
                if g[r0, c0] < 0 or seen[r0, c0]: continue
                comp, stack = [], [(r0, c0)]; seen[r0, c0] = True
                while stack:
                    r_, c_ = stack.pop(); comp.append((r_, c_))
                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        rr, cc = r_ + dr, c_ + dc
                        if 0 <= rr < P and 0 <= cc < P and not seen[rr, cc] and g[rr, cc] == g[r_, c_]:
                            seen[rr, cc] = True; stack.append((rr, cc))
                if len(comp) < smallest:
                    nb = [g[r_ + dr, c_ + dc] for r_, c_ in comp for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
                          if 0 <= r_ + dr < P and 0 <= c_ + dc < P and g[r_ + dr, c_ + dc] >= 0 and g[r_ + dr, c_ + dc] != g[r0, c0]]
                    if nb:
                        v = max(set(nb), key=nb.count)
                        for r_, c_ in comp: g[r_, c_] = v
        L.region[d] = g
    return L

METAL = ('plate', 'banded', 'mail', 'scale', 'lamellar')
def assign_roles(L, kind):
    """For each ramp of a layer: the pattern it is drawn with."""
    n = len(L.ramps); main = L.main()
    sat = [np.mean([hsv(c)[1] for c in R]) for R in L.ramps]
    big = [g for g in range(n) if L.weight[g] >= 0.12 * max(L.weight)]
    pat = {g: 'plain' for g in range(n)}
    if kind in METAL:
        pat[main] = kind
        if kind == 'plate':
            m = L.gid['S'] == main
            if m.any() and (np.abs(L.off['S'][m]) >= 1).mean() > 0.75: pat[main] = 'scale'      # scaly "plate" (dragon)
        if 'chitin' in L.src[0] and kind in ('plate', 'banded'): pat[main] = 'carapace'
    elif kind == 'tabard':
        metal = min(big, key=lambda g: sat[g]); pat[metal] = 'mail'
    elif kind == 'brigandine':
        pat[main] = 'studs'
    elif kind == 'leather':
        pat[main] = 'leather'
    L.pattern = pat
    greys = [g for g in range(n) if sat[g] < 0.16]
    L.metal_g = greys[0] if greys else main
    colours = sorted([g for g in range(n) if g != main and sat[g] >= 0.3], key=lambda g: -sat[g])
    L.accent_g = colours[0] if colours else main
    L.kind = kind
    return L

def pattern(name, u, v):
    """Shade offsets (-1, 0, +1) of a pattern at arc length u across the part and row v, and a
    mask of 'accent' blocks (lacing, studs) drawn in another ramp."""
    off = np.zeros(len(u), int); acc = np.zeros(len(u), bool)
    if name == 'banded':
        fv = (v / 2.4) % 1
        off[fv < 0.22] = 1; off[fv > 0.78] = -1
    elif name == 'mail':
        # rings: a small dark hole in each, the ring's upper half catching the light
        k = np.floor(v / 2.0); fu = ((u + 1.0 * (k % 2)) % 2.0) / 2.0; fv = (v % 2.0) / 2.0
        d = np.hypot(fu - 0.5, fv - 0.5)
        off[(d >= 0.24) & (d < 0.5) & (fv < 0.5)] = 1; off[d < 0.24] = -1; off[d >= 0.5] = -1
    elif name == 'scale':
        # overlapping round-bottomed scales, each row offset by half a scale: a lit top, a
        # dark curved lower rim where it overlaps the scale below
        h, w = 2.2, 3.0; k = np.floor(v / h); fu = ((u + (k % 2) * w / 2) % w) / w; fv = (v % h) / h
        rim = 0.62 + 0.3 * np.sqrt(np.clip(1 - (2 * fu - 1) ** 2, 0, 1))
        off[(fv < 0.34) & (np.abs(fu - 0.5) < 0.3)] = 1
        off[(fv > rim - 0.2) & (fv <= rim + 0.1)] = -1
    elif name == 'carapace':
        # an insect's segmented shell: glossy bands, each with a bright edge and a dark lip
        fv = (v % 3.0) / 3.0
        off[fv < 0.18] = 1; off[(fv >= 0.18) & (fv < 0.8)] = -1; off[fv >= 0.88] = -2
    elif name == 'lamellar':
        fu = (u % 2.0) / 2.0; fv = (v % 4.2) / 4.2
        off[fu < 0.2] = -1
        acc = (fv < 0.2) & (fu > 0.35) & (fu < 0.8)
    elif name == 'studs':
        fu = (u % 3.0) / 3.0; fv = (v % 3.0) / 3.0
        acc = (np.abs(fu - 0.5) < 0.18) & (np.abs(fv - 0.5) < 0.18)
    elif name == 'leather':
        k = np.floor(v / 3.5); fu = ((u + 1.75 * (k % 2)) % 3.5) / 3.5; fv = (v % 3.5) / 3.5
        acc = (np.abs(fu - 0.5) < 0.16) & (np.abs(fv - 0.5) < 0.16)       # light rivets, as the sprite
        off[(v % 7.0) < 0.35] = -1                                         # stitched seams
    return off, acc

def dressed(layers, centre, front=45, back=45, sides='EW', rows=None, face=None, reach=6):
    """Paint a body part: the topmost of `layers` drawn at the facing the block looks toward
    decides the material (a ramp of that layer); the layer's pattern for that ramp and the 3D
    light decide the shade. rows: plate bands for smooth plate (build3d3.plate_rows). face:
    (img, front) keeps the original face on the front of the head."""
    def paint(r, x, z, n):
        cx, cz, rx, rz = centre(r)
        ax, az = (x - cx) / rx, (z - cz) / rz
        sec = sector(ax, az, front, back)
        for si, dname in ((2, 'E'), (3, 'W')):
            if dname not in sides: sec = np.where(sec == si, np.where(z < cz, 0, 1), sec)
        u = np.arctan2(ax, -az) * (rx + rz) / 2; v = r
        pr = np.clip(r.astype(int), 0, P - 1); px = np.clip(x.astype(int), 0, P - 1); pz = np.clip(z.astype(int), 0, P - 1)
        out = np.zeros((len(r), 4), np.int32)
        # where no picture draws a colour (the sprites' dark outlines: feet, gaps), the darkest shade
        # of the part's own material, never a stray grey
        R0 = layers[0].ramps[layers[0].main()] if layers[0].ramps else [(52, 40, 34, 255)]
        out[:] = tuple(np.array(R0[0][:3]) * 0.8) + (255,) if len(R0) else (52, 40, 34, 255)
        todo = np.ones(len(r), bool); b = band(n)
        if face is not None:
            # the face first, straight from the sprite: its dark mouth and pupils are not a
            # material, so the lookup below would skip them
            fimg, ffront = face
            fsel = todo & (sec == 0) & (np.abs(np.degrees(np.arctan2(ax, -az))) <= ffront) & (fimg[pr, px, 3] > 0)
            if getattr(layers[0], 'drawn', None) is not None:
                # races: not on the top of the head, and not the brown outline drawn over the brow
                fp = fimg[pr, px]
                fsel &= (n[:, 1] <= 0.7) & ~((fp[:, :3].sum(1) < 90) & (fp[:, 0] > fp[:, 1] + 20))
                dw = layers[0].drawn
                if dw.get('clean'):
                    dskin = np.abs(fp[:, None, :3] - np.array(dw['ramp'])[None, :, :3]).sum(-1).min(-1)
                    fsel &= dskin > 40
                    if 'face_edge' in dw: fsel &= ~dw['face_edge'][pr, px]
            out[fsel] = fimg[pr[fsel], px[fsel]]; todo &= ~fsel
        for si, d in enumerate('SNEW'):
            sel = sec == si
            if not sel.any(): continue
            k = px if d in 'SN' else pz
            # gear first: sideways a little, or a few rows up (a sprite often stops a row or two
            # short of the sole or the fist); bare skin only where no gear is drawn near
            tries = [(o, 0, L) for o in [0] + [s * i for i in range(1, reach + 1) for s in (1, -1)] for L in layers[:-1]]
            tries = sorted(tries, key=lambda t: abs(t[0])) + [(0, dv, L) for dv in (1, 2, 3) for L in layers[:-1]] + \
                    [(o, 0, layers[-1]) for o in [0] + [s * i for i in range(1, reach + 1) for s in (1, -1)]]
            for o, dv, L in tries:
                if not (todo & sel).any(): break
                if True:
                    c = L.col(d, k + o); ok = sel & todo & (c >= 0) & (c < P)
                    if not ok.any(): continue
                    cc = np.clip(c, 0, P - 1); prr = np.clip(pr - dv, 0, P - 1)
                    drawn = getattr(L, 'drawn', None)
                    hit = ok & L.cover[d][prr, cc] & ((L.region[d][prr, cc] >= 0) | (drawn is not None))
                    if not hit.any(): continue
                    pr_save = pr; pr = prr
                    if drawn is not None and drawn.get('clean'):
                        # a race's skin as one clean material: its own skin colours, shaded by the 3D light
                        ramp_, lv_ = drawn['ramp'], drawn['levels']
                        if 'pix' in drawn:
                            pc_ = drawn['pix'][d][pr[hit], cc[hit]].astype(float)
                            nob = (pc_[:, 3] == 0) | (n[hit][:, 1] > 0.7)          # tops: a plain skin tone
                            if nob.any(): pc_[nob] = np.array(ramp_[min(lv_[1], len(ramp_) - 1)], float)
                            lk = np.array([0.8, 0.92, 1.0, 1.08])[b[hit]]
                            res = np.clip(pc_ * np.c_[lk, lk, lk, np.ones_like(lk)], 0, 255).astype(np.int32); res[:, 3] = 255
                        else:
                            tn = drawn['tone'][d][pr[hit], cc[hit]] if 'tone' in drawn else 0
                            res = np.array(ramp_)[np.clip(np.asarray(lv_)[b[hit]] + tn, 0, len(ramp_) - 1)].astype(np.int32)
                        up = n[hit][:, 1] > 0.7
                        if face is not None and d == 'S':
                            fimg, ffront = face
                            fsel = (np.abs(np.degrees(np.arctan2(ax[hit], -az[hit]))) <= ffront) & ~up
                            fpx = fimg[pr[hit], cc[hit]]
                            dskin = np.abs(fpx[:, None, :3] - np.array(ramp_)[None, :, :3]).sum(-1).min(-1)
                            # the face's own features (eyes, mouth, tusks, brows) as drawn; its skin stays clean
                            fsel &= (dskin > 40) & ~((fpx[:, :3].sum(1) < 90) & (fpx[:, 0] > fpx[:, 1] + 20))
                            if 'face_edge' in drawn: fsel &= ~drawn['face_edge'][pr[hit], cc[hit]]
                            res[fsel] = fpx[fsel]
                        out[hit] = res; todo &= ~hit
                        continue
                    if drawn is not None:
                        # a race's skin as its sprite draws it (muscles, scales, markings), lightly lit
                        img = L.img[d]; rh, ch = pr[hit], cc[hit]
                        px_ = img[rh, ch].astype(float)
                        up = n[hit][:, 1] > 0.7                                   # tops: the colour a few rows down
                        for k_ in range(1, 7):
                            dk = up & (px_[:, :3].sum(1) < 200)
                            if not dk.any(): break
                            px_[dk] = img[np.clip(rh[dk] + k_, 0, P - 1), ch[dk]]
                        dark = px_[:, :3].sum(1) < drawn['dark']                  # outline lines between limbs
                        for oc in drawn.get('outline', ()):                        # the sprite's outline colours
                            dark |= np.abs(px_[:, :3] - np.array(oc)).sum(1) <= 6
                        px_[dark, :3] = drawn['shade']
                        lk = np.array([0.8, 0.93, 1.0, 1.07])[b[hit]]
                        res = np.clip(px_ * np.c_[lk, lk, lk, np.ones_like(lk)], 0, 255).astype(np.int32); res[:, 3] = 255
                        if face is not None and d == 'S':
                            fimg, ffront = face
                            fsel = (np.abs(np.degrees(np.arctan2(ax[hit], -az[hit]))) <= ffront) & ~up
                            fpx = fimg[pr[hit], cc[hit]]
                            # keep black pupils and mouths; drop the brown outline drawn over the brow
                            fok = ~((fpx[:, :3].sum(1) < 90) & (fpx[:, 0] > fpx[:, 1] + 20))
                            fsel &= fok
                            res[fsel] = fpx[fsel]
                        out[hit] = res; todo &= ~hit; pr = pr_save
                        continue
                    gid = L.region[d][pr[hit], cc[hit]]
                    res = np.zeros((hit.sum(), 4), np.int32)
                    for gi in np.unique(gid):
                        m = gid == gi; pname = L.pattern.get(gi, 'plain')
                        off, acc = pattern(pname, u[hit][m], v[hit][m])
                        lv = L.levels[gi]; idx = lv[b[hit][m]]
                        if pname not in ('plate', 'plain'): idx = np.minimum(idx, lv[2])        # patterns: no big bright patches
                        idx = idx + off
                        if pname == 'plate' and rows is not None: idx = idx + rows[0][pr[hit][m]]
                        col = L.ramp_colour(gi, idx)
                        if acc.any():
                            ag = L.metal_g if pname in ('studs', 'leather') else L.accent_g
                            col[acc] = L.ramp_colour(ag, L.base[ag] + 1 + b[hit][m][acc] - 1)
                        if pname == 'plate':
                            sm = L.seam[d][pr[hit][m], cc[hit][m]]
                            if rows is not None: sm = sm | rows[1][pr[hit][m]]
                            col[sm] = SEAM
                        res[m] = col
                    if face is not None and d == 'S':
                        fimg, ffront = face
                        fsel = np.abs(np.degrees(np.arctan2(ax[hit], -az[hit]))) <= ffront
                        res[fsel] = fimg[pr[hit], cc[hit]][fsel]
                    out[hit] = res; todo &= ~hit
                    pr = pr_save
        return out
    return paint

def outline_colour(L):
    """The colour a layer draws its outline in (most common on its silhouette's edge)."""
    if not hasattr(L, '_outline'):
        raw = L.raw['S']; al = raw[:, :, 3] > 0; pad = np.pad(al, 1)
        edge = al & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        cols, cnt = np.unique(raw[edge][:, :3], axis=0, return_counts=True) if edge.any() else (np.zeros((1, 3)), [1])
        L._outline = tuple(cols[int(np.argmax(cnt))].tolist())
    return L._outline

def not_outline(L, a):
    o = np.array(outline_colour(L))
    return (np.abs(a[..., :3] - o).sum(-1) > 6) & (a[..., :3].sum(-1) >= 30)

def coherent(L, mask):
    """mask, keeping only the pixels of its dominant colour family (hue and saturation near the
    median): a dome sample without the horns or crest that grow out of it."""
    a = L.img['S'][:, :, :3] / 255.0
    sel = mask & L.cover['S'] & not_outline(L, L.img['S'])
    if not sel.any(): return mask
    import colorsys
    hs = np.array([colorsys.rgb_to_hsv(*a[r_, c_]) for r_, c_ in zip(*np.nonzero(sel))])
    mh, ms = np.median(hs[:, 0]), np.median(hs[:, 1])
    keep = np.zeros_like(sel)
    for (r_, c_), (h, s_, v) in zip(zip(*np.nonzero(sel)), hs):
        grey = ms < 0.16 and s_ < 0.2
        if grey or (min(abs(h - mh), 1 - abs(h - mh)) < 0.06 and abs(s_ - ms) < 0.3): keep[r_, c_] = True
    return keep

def local_ramp(L, mask):
    """A ramp of the colours a layer's front picture draws inside mask (not its dark lines),
    darkest first, and its middle shade: for parts whose colour the layer's ramps mix up (a
    gold rim round wooden planks, a gold axe head on a wooden haft)."""
    a = L.img['S'][mask & L.cover['S']]
    a = a[not_outline(L, a)] if len(a) else a
    if not len(a): return None
    cols, cnt = np.unique(a[:, :3], axis=0, return_counts=True)
    keep = cols[cnt >= 2] if (cnt >= 2).sum() >= 2 else cols
    ramp = sorted([tuple(c) + (255,) for c in keep.tolist()], key=lambda c: sum(c[:3]))
    # rest at the shade the picture mostly uses there
    pos = {c[:3]: i for i, c in enumerate(ramp)}
    idx = [pos[tuple(p[:3])] for p in a if tuple(p[:3]) in pos]
    return ramp, levels_of(np.array(idx), len(ramp))

# ---------- helmets: clean metal, a riveted rim, their own parts ----------
def add_helmet(G, B, kind, L, hc):
    r, x, z = B.r, B.x, B.z
    cr, cx, cz, rr, rx, rz = hc
    # the dome's colour: the ramp drawn at the top of the helmet's front picture
    # the dome's colours: what the front picture draws just above the rim, across the head
    # (below any crest or horns); the extras' colours: what it draws outside the dome (horns,
    # wings, a crest) -- taken from the pixels, since a layer's ramps can run gold into ivory
    rows_, cols_ = np.mgrid[0:P, 0:P]
    in_dome = ((cols_ + 0.5 - cx) / (rx + 2.5)) ** 2 + ((rows_ + 0.5 - (cr - 1)) / (rr + 2.5)) ** 2 <= 1
    off_mid = np.abs(cols_ + 0.5 - cx)
    dome_px = (rows_ >= 8) & (rows_ < 18) & (off_mid >= 1.6) & (off_mid < rx - 1)      # the dome, not a nose guard; crests/horns drop out (coherent)
    Mr = local_ramp(L, coherent(L, dome_px)) or (L.ramps[L.main()], L.base[L.main()])
    Ar = local_ramp(L, coherent(L, ~in_dome)) or Mr
    M, mb = Mr
    tier = L.src[0].rsplit('/', 1)[-1][:-4]
    metal = acc = None
    def ell(c_r, c_x, c_z, a, b, c, p=2.2, pf=None, czf=None):
        pz = p if pf is None else np.where(z < c_z, pf, p)
        cc = c if czf is None else np.where(z < c_z, czf, c)
        return np.abs((r - c_r) / a) ** p + np.abs((x - c_x) / b) ** p + np.abs((z - c_z) / cc) ** pz <= 1
    rimf = lambda z: 17.6 + (z - (cz - rz)) * 0.17
    def riveted(edge_of):
        def extra(r, x, z, i):
            i = i.copy(); e = edge_of(z)
            onrim = (r > e - 1.7) & (r <= e); i[onrim] -= 1
            ang = np.arctan2(x - cx, z - cz)
            i[onrim & (np.abs(((ang * 11.5 / math.pi) % 1) - 0.5) < 0.13) & (np.abs(r - e + 0.85) < 0.5)] = 99
            return i
        return extra
    # is (r, x, z) on the helmet in the picture facing that way?
    def drawn(r, x, z, below=0.0, solid=False):
        th = np.degrees(np.arctan2(x - cx, -(z - cz)))
        pr = np.clip((r + below).astype(int), 0, P - 1)
        out = np.zeros(r.shape, bool)
        for d, sel in (('S', np.abs(th) < 55), ('N', np.abs(th) > 125), ('E', (th < 0) & (np.abs(th) >= 55) & (np.abs(th) <= 125)),
                       ('W', (th > 0) & (np.abs(th) >= 55) & (np.abs(th) <= 125))):
            k = np.clip(x if d in 'SN' else z, 0, P - 1).astype(int)
            c = np.clip(L.col(d, k), 0, P - 1)
            hit = L.cover[d][pr, c] & (L.region[d][pr, c] >= 0) if solid else L.cover[d][pr, c]
            out |= sel & hit
        return out
    if tier == 'dragon' and kind != 'great helm':
        # a hood of dragon scales, carved to what the sprite covers, a knobbed crest on top and
        # dark horns sweeping back
        hood = ell(cr - 0.6, cx, cz, rr + 2.0, rx + 2.0, rz + 2.0, p=2.2, pf=2.8, czf=rz + 1.3) & (r < 31)
        hood &= drawn(r, x, z)
        def hood_ex(r, x, z, i):
            i = i.copy(); i[~drawn(r, x, z, below=1.4)] -= 1; return i
        G.add(hood, plate_paint((M, mb, 'scale'), hood_ex, centre=(cx, cz)), lit=True, space=B)
        knob = ((x - cx) ** 2 + (z - (cz - 1.5)) ** 2 <= 1.1 ** 2) & (r >= 5.5) & (r < 10.5)
        knob |= (x - cx) ** 2 + (r - 4.8) ** 2 + (z - (cz - 1.5)) ** 2 <= 1.9 ** 2
        G.add(knob & ~hood, plate_paint((M, mb, 'scale'), centre=(cx, cz)), lit=True, space=B)
        horns = np.zeros_like(hood)
        for s_ in (-1, 1):
            if kind == 'horned':
                pts = [(11.0, 12.6, 0.0), (16.0, 11.4, 0.0), (17.6, 9.0, 0.0), (17.4, 4.6, 0.0)]
            else:
                pts = [(5.5, 10.5, 0.5), (8.0, 5.5, 2.5), (9.5, 2.5, 6.0), (9.0, 1.5, 9.5)]
            for k in range(40):
                t = k / 39
                o, hr, hz = [(1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d
                             for a, b, c, d in zip(*pts)]
                rad = 1.5 * (1 - t) + 0.45
                horns |= (x - (cx + s_ * o)) ** 2 + (r - hr) ** 2 + (z - (cz - 1.0 + hz)) ** 2 <= rad * rad
        def ridges(r, x, z, i):
            i = i.copy(); i[(np.floor((r + z) * 0.8) % 2) == 0] -= 1; return i
        G.add(horns & ~hood, lit(Ar[0], Ar[1], extra=ridges), lit=True, space=B)
        return
    bone_px = None
    if tier == 'chitin':
        # the light bone-coloured pixels in front of the face are mandibles, not a face plate
        a = L.img['S']; lum = a[:, :, :3].sum(-1)
        bone_px = L.cover['S'] & (lum > 330) & (rows_ >= 19) & (rows_ <= 31) & (off_mid < 8)
        bone = local_ramp(L, bone_px)
        def mandibles():
            m = np.zeros(r.shape, bool)
            fz = cz - rz - 1.2
            for s_ in (-1, 1):
                for k in range(30):
                    t = k / 29
                    mx_ = cx + s_ * (3.6 - 1.4 * t ** 1.5); mr_ = 21.5 + 7.5 * t; mz_ = fz - 0.4 - 1.6 * math.sin(t * math.pi * 0.8)
                    rad = 1.05 * (1 - 0.5 * t) + 0.35
                    m |= (x - mx_) ** 2 + (r - mr_) ** 2 + (z - mz_) ** 2 <= rad * rad
            return m
        def bands(r, x, z, i):
            i = i.copy(); fv = ((r - 4.0) % 2.8) / 2.8
            i[fv < 0.2] += 1; i[fv > 0.8] -= 1; return i
        def gem_and_spine(top_r):
            gem = (np.abs(x - cx) + np.abs(r - top_r) * 0.8 + np.abs(z - (cz - 2.0))) <= 2.7
            spine = (np.abs(x - cx) <= 0.9) & ell(cr + 0.3, cx, cz, rr + 2.6, rx + 2.6, rz + 2.4, p=2.2, pf=3.0, czf=rz + 1.4) & \
                    ~ell(cr + 0.3, cx, cz, rr + 1.4, rx + 1.6, rz + 1.6, p=2.2, pf=3.0, czf=rz + 0.6) & (z < cz) & (r < 17.0)
            return gem | spine
    if kind == 'great helm':
        # a flared pot as the sprite draws it: narrow at the crown, widening to 28 px at the
        # bottom (rows 11-29); eye slits, a ridge down the middle, breathing holes
        t = np.clip((r - 11.0) / 12.0, 0, 1) ** 0.8
        radx = 8.6 + 5.4 * t; radzf = 9.2 + 3.2 * t; radzb = 9.8 + 3.2 * t
        pot = (np.abs((x - cx) / radx) ** 2.6 + np.abs((z - cz) / np.where(z < cz, radzf, radzb)) ** 2.6 <= 1)
        top = 10.6 + 1.4 * ((x - cx) / 9.0) ** 2
        body = pot & (r >= top) & (r < 29.5)
        def visor(r, x, z, i):
            i = i.copy(); front = z < cz - 4
            i[front & (np.abs(r - 19.6) < 0.7) & (np.abs(x - cx) > 1.2)] = -100            # eye slits
            i[front & (np.abs(x - cx) <= 1.0) & (r > 15)] += 1                             # the ridge
            br = front & (x > cx + 2.5) & (x < cx + 8.0) & (r > 22.5) & (r < 27.0)
            i[br & (((x - cx) % 1.6) < 0.6) & ((r % 1.6) < 0.6)] = -100                     # breaths
            i[(r < 29.5) & (r > 28.4)] -= 1                                                 # the lower edge
            return i
        if tier == 'chitin':
            G.add(body, lit(M, mb, extra=lambda r, x, z, i: bands(r, x, z, visor(r, x, z, i))), lit=True, space=B)
            G.add(gem_and_spine(10.0) & ~body, lit(Ar[0], Ar[1]), lit=True, space=B)
            if bone: G.add(mandibles() & ~body, lit(*bone), lit=True, space=B)
            return
        G.add(body, lit(M, mb, extra=visor), lit=True, space=B)
        return
    if kind == 'kettle':
        # a rounded cap carved by the sprite's own outline: from each side it covers exactly
        # what the picture facing that way covers (the iron one down over the face with eye
        # holes, the leather one to the brow with a nose guard)
        cap = ell(cr - 0.2, cx, cz, rr + 1.1, rx + 1.2, rz + 1.2, p=2.2, pf=2.8, czf=rz + 0.9) & (r < 30)
        cap &= drawn(r, x, z)
        def lower_edge(r, x, z, i):
            i = i.copy(); i[~drawn(r, x, z, below=1.6)] -= 1; return i     # the rim along its lower edge
        G.add(cap, lit(M, mb, extra=lower_edge), lit=True, space=B)
        return
    rim = rimf(z)
    dome = ell(cr + 0.3, cx, cz, rr + 1.5, rx + 1.8, rz + 1.9, p=2.2, pf=3.0, czf=rz + 0.7) & (r <= rim)
    rimband = ell(cr + 0.3, cx, cz, rr + 1.9, rx + 2.3, rz + 2.4, p=2.2, pf=3.0, czf=rz + 1.1) & (r <= rim) & (r > rim - 1.7)
    parts = dome | rimband
    if kind == 'nasal':
        parts |= ((x - cx) ** 2 + (z - cz) ** 2 <= (0.8 + np.clip(r - 3, 0, 9) * 0.7) ** 2) & (r >= 3) & (r < 8.5)
        fz = cz - rz - 0.6
        parts |= (np.abs(x - cx) <= 1.0) & (r >= 17) & (r < 23.5) & (z >= fz - 0.9) & (z < fz + 1.5)
    # whatever the helmet's pictures draw over the face below the rim (cheek guards, a visor,
    # a bug-eyed mask, a nose guard) becomes a thin plate over the face, in the drawn colours
    face_in = ell(cr, cx, cz, rr + 0.3, rx + 0.3, rz + 0.3, p=2.2, pf=3.2)
    face_out = ell(cr, cx, cz, rr + 1.5, rx + 1.5, rz + 1.6, p=2.2, pf=3.2)
    guard = face_out & ~face_in & (r > rim) & (r < 31) & (z < cz + 2.0) & drawn(r, x, z, solid=True) & ~parts
    if tier == 'chitin':
        pr_, px_ = np.clip(r.astype(int), 0, P - 1), np.clip(x.astype(int), 0, P - 1)
        guard &= ~(bone_px[pr_, px_] & (z < cz))
        G.add(parts, lit(M, mb, extra=bands), lit=True, space=B)
        if guard.any(): G.add(guard, lit(M, mb, extra=bands), lit=True, space=B)
        G.add(gem_and_spine(6.5) & ~parts, lit(Ar[0], Ar[1]), lit=True, space=B)
        if bone: G.add(mandibles() & ~parts, lit(*bone), lit=True, space=B)
        return
    G.add(parts, lit(M, mb, extra=riveted(rimf)), lit=True, space=B)
    if guard.any():
        G.add(guard, dressed([L], lambda rr_: (cx, cz, rx, rz), front=60), lit=True, space=B)
    if kind == 'horned':
        # out sideways from the dome at brow height, then turning straight up (as drawn)
        horn = np.zeros_like(parts)
        P0, P1, P2, P3 = (11.0, 12.6), (16.0, 11.4), (17.6, 9.0), (17.4, 4.6)     # (offset from the middle, row)
        for s_ in (-1, 1):
            for k in range(40):
                t = k / 39
                o = (1 - t) ** 3 * P0[0] + 3 * (1 - t) ** 2 * t * P1[0] + 3 * (1 - t) * t * t * P2[0] + t ** 3 * P3[0]
                hr = (1 - t) ** 3 * P0[1] + 3 * (1 - t) ** 2 * t * P1[1] + 3 * (1 - t) * t * t * P2[1] + t ** 3 * P3[1]
                rad = 1.9 * (1 - t) + 0.55
                horn |= (x - (cx + s_ * o)) ** 2 + (r - hr) ** 2 + (z - (cz - 1.0)) ** 2 <= rad * rad
        def rings(r, x, z, i):
            i = i.copy(); i[(np.floor(np.hypot(x - cx, r - 12.0) * 0.7) % 2) == 0] -= 1; return i
        G.add(horn & ~parts, lit(Ar[0], Ar[1] + 1, extra=rings), lit=True, space=B)
    if kind == 'winged':
        # big wings from the dome's sides, fanning up and out to the top of the picture
        wing = np.zeros_like(parts)
        for s_ in (-1, 1):
            for f_ in range(6):
                ang = math.radians(42 + 9 * f_); ln = 9.5 + 0.55 * f_
                for k in range(18):
                    t = k / 17
                    wx = cx + s_ * (rx + 0.8 + math.cos(ang) * ln * t); wr = 13.0 - math.sin(ang) * ln * t; wz = cz + 0.5 + 1.5 * t
                    wid = 1.35 * (1 - 0.5 * t)
                    wing |= ((x - wx) ** 2 + (r - wr) ** 2 <= wid * wid) & (np.abs(z - wz) <= 0.6)
        W = sorted(Ar[0], key=lambda c: sum(c[:3]))[-3:]           # white feathers: the lightest shades
        wb = len(W) - 2
        def quill(r, x, z, i):
            i = i.copy(); i[(np.hypot(x - cx, r - 13.0) * 0.9) % 2 < 0.35] -= 1; return i
        G.add(wing & ~parts, lit(W, wb, extra=quill), lit=True, space=B)
    if kind == 'crested':
        ang = np.arctan2(z - cz, -(r - (cr + 0.3))); rad = np.hypot(r - (cr + 0.3), z - cz)
        crest = (np.abs(x - cx) <= 2.1 - 0.5 * np.abs(ang - 0.3)) & (ang > -0.95) & (ang < 1.7) & (rad >= rr + 0.8) & (rad <= rr + 6.4 - 1.6 * np.abs(ang - 0.3))
        def plume(r, x, z, i):
            i = i.copy(); i[(np.floor(np.arctan2(z - cz, -(r - cr)) * 9) % 2) == 0] -= 1; return i     # tufts
        G.add(crest & ~parts, lit(Ar[0], Ar[1], extra=plume), lit=True, space=B)

def add_shield(G, SA, kind, L, steel):
    """build3d7's shield, with its rim (and boss) in the colours the sprite draws its rim in."""
    sa = L.cover['S']
    dist = np.zeros(sa.shape, int); cur = sa.copy(); k = 0
    while cur.any():
        k += 1; dist[cur] = k
        pad = np.pad(cur, 1); cur = cur & pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:]
    rim = local_ramp(L, (dist >= 2) & (dist <= 3))
    _b7.add_shield(G, SA, kind, L, rim[0] if rim else steel)

def add_weapon(G, world, kind, L, hand, d, steel):
    """build3d7's weapon, with head, haft and grip coloured from where the sprite draws them."""
    ys, xs = np.nonzero(L.cover['S'])
    if not len(ys): return
    dist = np.zeros(L.cover['S'].shape); dist[ys, xs] = np.hypot(xs - 20, ys - 50); m = dist.max()
    far, mid, near = L.cover['S'] & (dist > 0.62 * m), L.cover['S'] & (dist > 0.22 * m) & (dist < 0.5 * m), L.cover['S'] & (dist < 0.2 * m)
    # the head is what the far end draws that the haft does not (the haft's top runs into it)
    img = L.img['S'][:, :, :3].astype(int)
    haft_cols = {tuple(c) for c in img[mid].tolist()}
    not_haft = np.array([[tuple(img[r_, c_]) not in haft_cols for c_ in range(P)] for r_ in range(P)])
    head = local_ramp(L, far & not_haft) or local_ramp(L, far)
    parts = [head, local_ramp(L, mid), local_ramp(L, near)]
    parts = [p or parts[0] or (steel, 1) for p in parts]
    class Proxy: pass
    px = Proxy(); px.ramps = [p[0] for p in parts]; px.base = [p[1] for p in parts]
    keep = _b7.weapon_ramps
    _b7.weapon_ramps = lambda L_: (0, 1, 2)
    try: _b7.add_weapon(G, world, kind, px, hand, d, steel, broadside=_b7.WEAPONS[kind]['kind'] != 'blade')
    finally: _b7.weapon_ramps = keep

# ---------- plate armour, sculpted ----------
def plate_material(L):
    """The plate's metal (ramp, band levels) and its pattern ('plate', or 'scale' for scaly
    tiers such as dragon) from the chest layer."""
    g = L.main()
    return L.ramps[g], np.asarray(L.levels[g]), L.pattern.get(g, 'plate')

def plate_paint(mat, extra=None, centre=(32.0, CZ)):
    """Lit plate in the chest's metal; extra(r, x, z, i) adds edges, ridges and rivets; scaly
    tiers keep their scale pattern on top."""
    ramp, lv, pat = mat
    def ex(r, x, z, i):
        if pat != 'plate':
            u = np.arctan2(x - centre[0], -(z - centre[1])) * 9.0
            off, _ = pattern(pat, u, r); i = np.minimum(i, lv[2]) + off
        return extra(r, x, z, i) if extra is not None else i
    return lit(ramp, lv, extra=ex)

def rivets(r, x, z, i, row, cx, cz, step=2.4, rad=0.45, where=None):
    """Light rivets along a row, every `step` of arc length round (cx, cz)."""
    u = np.arctan2(x - cx, -(z - cz)) * 9.0
    m = (np.abs(r - row) < rad) & (np.abs((u % step) - step / 2) < rad)
    if where is not None: m &= where
    i = i.copy(); i[m] = 99; return i

def add_plate(G, B, SA, world, mat, cz, elbow_r, elbow_l):
    """A plate harness over the body: a keeled breastplate, a gorget, layered pauldrons, a
    fauld of overlapping lames over the hips, and elbow cops."""
    r, x, z = B.r, B.x, B.z
    taken = G.solid()
    # breastplate: rows 33-46, wider than the body, a keel down the middle of the front
    keel = 1.7 * np.clip(1 - np.abs(x - 32) / 8.5, 0, 1)
    rxb = np.where(r < 35, 7 + 3.8 * np.clip((r - 32) / 3, 0, 1), 10.8)
    breast = (np.abs((x - 32) / rxb) ** 2.6 + np.abs((z - cz) / np.where(z < cz, 9.2 + keel, 9.0)) ** 2.6 <= 1) & (r >= 32.6) & (r < 46.2)
    def breast_ex(r, x, z, i):
        i = i.copy()
        i[(np.abs(x - 32) < 0.8) & (z < cz)] += 1                       # the keel catches the light
        i[(r < 33.8)] += 1                                               # rolled upper edge
        i[(r > 45.2)] = -100                                             # lower edge
        return i
    G.add(breast & ~taken, plate_paint(mat, breast_ex), lit=True, space=B)
    # fauld: three overlapping lames over the hips, each a little wider than the one above
    for j in range(3):
        r0, r1 = 46.0 + 2.1 * j, 48.4 + 2.1 * j
        rad_x, rad_z = 10.9 + 0.45 * j, 9.1 + 0.45 * j
        lame = (np.abs((x - 32) / rad_x) ** 2.6 + np.abs((z - cz) / rad_z) ** 2.6 <= 1) & (r >= r0) & (r < r1)
        def lame_ex(r, x, z, i, r0=r0, r1=r1, j=j):
            i = i.copy(); i[r < r0 + 0.7] += 1; i[r > r1 - 0.6] = -100
            return rivets(r, x, z, i, r0 + 1.2, 32, cz, step=7.0) if j == 1 else i
        G.add(lame & ~taken, plate_paint(mat, lame_ex), lit=True, space=B)
    # gorget: a flared collar round the neck
    t = np.clip((r - 30.0) / 3.4, 0, 1)
    gorget = (np.hypot((x - 32) / (5.4 + 2.4 * t), (z - cz) / (5.2 + 2.2 * t)) <= 1) & (r >= 30.0) & (r < 33.4)
    def gorget_ex(r, x, z, i):
        i = i.copy(); i[r < 30.7] += 1; i[(r > 31.6) & (r < 32.1)] = -100; return i
    G.add(gorget & ~taken, plate_paint(mat, gorget_ex), lit=True, space=B)
    # pauldrons: three lames stepping down over each shoulder, rivets along their edges
    for pcx, side in ((18.6, -1), (45.4, 1)):
        for k in range(3):
            top, bot = 32.2 + 2.3 * k, 36.6 + 2.3 * k
            lame = B.ell(34.8 + 2.3 * k, pcx + side * 0.5 * k, cz, 3.6, 6.3 + 0.35 * k, 6.1 + 0.3 * k, 2.4) & (r >= top) & (r < bot)
            lame &= (side * (x - pcx) > -4.2)                             # not over the neck
            def p_ex(r, x, z, i, top=top, bot=bot, pcx=pcx, k=k):
                i = i.copy(); i[r < top + 0.8] += 1; i[r > bot - 0.8] = -100      # each lame: lit top, dark lower edge
                return rivets(r, x, z, i, bot - 1.6, pcx, cz, step=5.5) if k == 2 else i
            G.add(lame & ~G.solid(), plate_paint(mat, p_ex, centre=(pcx, cz)), lit=True, space=B)
    if mat[2] == 'scale':
        # dragon plate: a row of spikes along the top of each pauldron
        ramp, lv, _ = mat
        spikes = np.zeros(r.shape, bool)
        for pcx, side in ((18.6, -1), (45.4, 1)):
            for k, (dx, dz) in enumerate(((0.5, -3.0), (1.5, 0.0), (0.5, 3.0))):
                bx, br, bz = pcx + side * dx, 32.6, cz + dz
                tx, tr, tz = bx + side * 2.2, 28.6 - 0.6 * (k == 1), bz
                d_ = np.array([tx - bx, tr - br, tz - bz]); L_ = np.linalg.norm(d_); d_ /= L_
                q = np.stack([x - bx, r - br, z - bz], -1)
                tq = np.clip(q @ d_, 0, L_)
                perp = np.linalg.norm(q - tq[..., None] * d_, axis=-1)
                spikes |= (q @ d_ >= 0) & (q @ d_ <= L_) & (perp <= 1.3 * (1 - tq / L_) + 0.15)
        G.add(spikes & ~G.solid(), lit(ramp, np.minimum(lv + 1, len(ramp) - 1)), lit=True, space=B)
    # elbow cops: a fan-shaped disc on the outside of each elbow
    for (ex_, er_, ez_), out, sp in ((elbow_r, -1, world), (elbow_l, 1, SA)):
        cop = sp.ell(er_, ex_ + out * 3.3, ez_ + 0.4, 2.6, 1.3, 2.6, 2.2)
        def c_ex(r, x, z, i, er_=er_):
            i = i.copy(); i[np.abs(r - er_) < 0.6] += 1; return i
        G.add(cop & ~G.solid(), plate_paint(mat, c_ex), lit=True, space=sp)

def design_mouth(face):
    """The sprite's mouth (a dark line below the eyes) made into a mouth: a deep red-brown
    line, a soft lip tone under its middle, a faint shadow below that. Returns the new face
    picture and the mouth's pixels (row, column) to carve."""
    f = face.copy()
    lum = f[:, :, :3].sum(-1)
    rows, cols = np.mgrid[0:P, 0:P]
    m = (lum < 60) & (f[:, :, 3] > 0) & (rows >= 25) & (rows <= 30) & (np.abs(cols + 0.5 - 32) < 7)
    pts = list(zip(*np.nonzero(m)))
    if not pts: return f, []
    r0 = max(p[0] for p in pts); c0, c1 = min(p[1] for p in pts), max(p[1] for p in pts)
    def tint(px, c, a): return np.clip(px[:3] * (1 - a) + np.array(c) * a, 0, 255).astype(int)
    f[m, :3] = (70, 26, 22)                                           # the mouth line
    for c in (c0, c1): f[r0, c, :3] = (118, 52, 40)                   # softer corners
    for c in range(c0 + 1, c1):                                        # a full lower lip under it
        f[r0 + 1, c, :3] = tint(f[r0 + 1, c], (168, 70, 58), 0.6)
    for c in range(c0 + 2, c1 - 1):                                    # and its highlight
        f[r0 + 1, c, :3] = tint(f[r0 + 1, c], (230, 150, 120), 0.25)
    for c in range(c0 + 2, c1 - 1):                                    # a faint shadow under the lip
        f[r0 + 2, c, :3] = tint(f[r0 + 2, c], (120, 70, 40), 0.2)
    lip = [(r0 + 1, c) for c in range(c0 + 1, c1)]
    return f, pts + lip

# ---------- banded and lamellar armour, sculpted ----------
def torso_rx(r):
    """The body's half-width at a row (as the torso column is built)."""
    return np.where(r < 35, 6 + 4 * np.clip((r - 31) / 3, 0, 1), 10.0)

def hoop(B, cz, r0, r1, grow=0.5, out=0.4, rz_extra=0.0, rx_of=None):
    """A band round the body from row r0 to r1, flaring a little toward its lower edge so it
    laps over the band below."""
    r, x, z = B.r, B.x, B.z
    t = np.clip((r - r0) / max(r1 - r0, 1e-6), 0, 1)
    rx = (torso_rx(r) if rx_of is None else rx_of(r)) + out + grow * t
    rz = 8.6 + out + grow * t + rz_extra
    return (np.abs((x - 32) / rx) ** 2.6 + np.abs((z - cz) / rz) ** 2.6 <= 1) & (r >= r0) & (r < r1)

def two_tone(main, accent, extra=None, accent_at=None):
    """Lit main material with accent blocks (lacing, a buckle) where accent_at(r, x, z) says."""
    pm = lit(main[0], main[1], extra=extra)
    pa = lit(accent[0], accent[1])
    def paint(r, x, z, n):
        out = pm(r, x, z, n)
        if accent_at is not None:
            m = accent_at(r, x, z)
            if m.any(): out[m] = pa(r[m], x[m], z[m], n[m])
        return out
    return paint

def arc_u(x, z, cx, cz, rad=9.5):
    """Distance round the body (in sprite pixels) from the front middle."""
    return np.arctan2(x - cx, -(z - cz)) * rad

def accent_of(L, rows, cols):
    """The colours the chest sprite draws at given rows and columns (a belt, the lacing), or None."""
    rr, cc = np.mgrid[0:P, 0:P]
    m = np.isin(rr, rows) & (cc >= cols[0]) & (cc <= cols[1])
    a = L.img['S'][m & L.cover['S']]
    main = set(map(tuple, np.array(L.ramps[L.main()])[:, :3].tolist()))
    a = a[[tuple(p[:3]) not in main for p in a]] if len(a) else a
    if not len(a): return None
    mm = np.zeros(m.shape, bool)
    for (r_, c_) in zip(*np.nonzero(m & L.cover['S'])):
        if tuple(L.img['S'][r_, c_, :3]) not in main: mm[r_, c_] = True
    return local_ramp(L, coherent(L, mm))

def add_banded(G, B, mat, L, cz):
    """Banded armour: steel hoops wrapping the body, each lapping over the one below, banded
    shoulder guards, a leather belt with a buckle, two hoops below the belt."""
    r, x, z = B.r, B.x, B.z
    ramp, lv, _ = mat
    def band_ex(r0, r1):
        def ex(r, x, z, i):
            i = i.copy(); i[r < r0 + 0.6] += 1; i[r > r1 - 0.55] = -100; return i
        return ex
    rows = [33.0, 35.6, 38.2, 40.8, 43.4, 46.0]
    for r0, r1 in zip(rows[:-1], rows[1:]):
        G.add(hoop(B, cz, r0, r1) & ~G.solid(), lit(ramp, lv, extra=band_ex(r0, r1)), lit=True, space=B)
    for r0, r1 in ((48.2, 50.8), (50.8, 53.6)):
        hips = lambda r: np.full(r.shape, 11.0)
        G.add(hoop(B, cz, r0, r1, out=0.3, rx_of=hips) & ~G.solid(), lit(ramp, lv, extra=band_ex(r0, r1)), lit=True, space=B)
    # the belt and its buckle
    belt = accent_of(L, [46, 47], (22, 41)) or ([(74, 44, 24, 255), (110, 70, 40, 255), (146, 100, 62, 255)], np.array([0, 1, 1, 2]))
    buckle = accent_of(L, [45, 46, 47], (29, 34))
    if buckle is None or buckle[0] == belt[0]: buckle = (ramp, np.minimum(lv + 1, len(ramp) - 1))
    beltm = hoop(B, cz, 46.0, 48.2, grow=0.0, out=0.7)
    front_mid = (np.abs(x - 32) < 2.2) & (z < cz)
    def belt_ex(r, x, z, i):
        i = i.copy(); i[(r < 46.4) | (r > 47.8)] -= 1; return i
    G.add(beltm & ~front_mid & ~G.solid(), lit(belt[0], belt[1], extra=belt_ex), lit=True, space=B)
    bk = hoop(B, cz, 45.6, 48.6, grow=0.0, out=1.3) & front_mid
    def bk_ex(r, x, z, i):
        i = i.copy(); i[(np.abs(x - 32) < 1.0) & (r > 46.4) & (r < 47.8)] = -100; return i      # the frame's hole
    G.add(bk & ~G.solid(), lit(buckle[0], buckle[1], extra=bk_ex), lit=True, space=B)
    # shoulder guards: curved bands over each shoulder, each lower one lapping outward
    for pcx, side in ((19.0, -1), (45.0, 1)):
        for k in range(4):
            top, bot = 30.6 + 2.2 * k, 33.0 + 2.2 * k
            cap = B.ell(35.2, pcx + side * 0.4 * k, cz, 4.4 + 0.2 * k, 6.2 + 0.4 * k, 6.0 + 0.35 * k, 2.4) & (r >= top) & (r < bot)
            cap &= side * (x - pcx) > -4.0
            G.add(cap & ~G.solid(), lit(ramp, lv, extra=band_ex(top, bot)), lit=True, space=B)

def add_lamellar(G, B, mat, L, cz):
    """Lamellar armour: rows of small upright slats laced together (lacing every 5 rows, a lace
    every 3 pixels round), each row lapping over the one below, flared shoulder flaps and a
    slatted skirt over the hips."""
    r, x, z = B.r, B.x, B.z
    ramp, lv, _ = mat
    lace = accent_of(L, [35, 40, 45, 50], (14, 50))
    if lace is None:                                                   # lacing in the armour's own colour: its dark shades
        lace = (ramp, np.maximum(lv - 2, 0))
    def slats(cx_, rad):
        def ex(r, x, z, i):
            i = i.copy(); u = arc_u(x, z, cx_, cz, rad)
            i[(u % 1.9) < 0.42] -= 2                                    # the gap between slats
            i[((u % 1.9) > 1.45)] += 1                                  # each slat's lit edge
            return i
        return ex
    def laces(r0, cx_, rad):
        def at(r, x, z):
            u = arc_u(x, z, cx_, cz, rad)
            return (np.abs(r - (r0 + 0.55)) < 0.6) & (np.abs((u % 3.8) - 1.18) < 0.5)   # a lace on every other slat, in a tidy row
        return at
    rows = [32.6, 35.0, 40.0, 45.0, 50.0]
    for r0, r1 in zip(rows[:-1], rows[1:]):
        def row_ex(r, x, z, i, r0=r0, r1=r1):
            i = slats(32, 9.5)(r, x, z, i); i[r > r1 - 0.5] = -100; return i
        rx_of = (lambda r: np.maximum(torso_rx(r), 10.0)) if r0 >= 45 else None
        G.add(hoop(B, cz, r0, r1, grow=0.6, out=0.5, rx_of=rx_of) & ~G.solid(),
              two_tone((ramp, lv), lace, extra=row_ex, accent_at=laces(r0, 32, 9.5)), lit=True, space=B)
    # skirt over the hips: two rows, flaring, split at the front
    for r0, r1, wide in ((49.8, 52.6, 11.6), (52.6, 55.4, 12.2)):
        sk = hoop(B, cz, r0, r1, grow=0.8, out=0.0, rx_of=lambda r, wide=wide: np.full(r.shape, wide)) & ~((np.abs(x - 32) < 0.7) & (z < cz))
        def sk_ex(r, x, z, i, r1=r1):
            i = slats(32, 10.5)(r, x, z, i); i[r > r1 - 0.5] = -100; return i
        G.add(sk & ~G.solid(), two_tone((ramp, lv), lace, extra=sk_ex, accent_at=laces(r0, 32, 10.5)), lit=True, space=B)
    # shoulder flaps: two slatted rows hanging over the top of each arm, flaring outward
    for pcx, side in ((19.6, -1), (44.4, 1)):
        for k, (top, bot) in enumerate(((32.4, 36.2), (36.2, 40.0))):
            t = np.clip((r - top) / (bot - top), 0, 1)
            radx, radz = 5.0 + 0.8 * k + 0.7 * t, 5.6 + 0.6 * k + 0.5 * t
            flap = (np.abs((x - pcx) / radx) ** 2.4 + np.abs((z - cz) / radz) ** 2.4 <= 1) & (r >= top) & (r < bot) & (side * (x - pcx) > -1.5)
            def f_ex(r, x, z, i, bot=bot, pcx=pcx):
                i = slats(pcx, 5.5)(r, x, z, i); i[r > bot - 0.5] = -100; return i
            G.add(flap & ~G.solid(), two_tone((ramp, lv), lace, extra=f_ex, accent_at=laces(top, pcx, 5.5)), lit=True, space=B)

# ---------- mail hauberk and scale shirt, shaped ----------
def tube(sp, A, Bp, r0, r1, t0=0.0, t1=1.0):
    """A sleeve: everything within a radius growing from r0 to r1 of the segment A->B (x, row, z),
    from t0 to t1 along it."""
    A, Bp = np.asarray(A, float), np.asarray(Bp, float); d = Bp - A; L2 = d @ d
    qx, qr, qz = sp.x - A[0], sp.r - A[1], sp.z - A[2]
    t = (qx * d[0] + qr * d[1] + qz * d[2]) / L2
    px, pr, pz = qx - t * d[0], qr - t * d[1], qz - t * d[2]
    rad = r0 + (r1 - r0) * np.clip((t - t0) / max(t1 - t0, 1e-6), 0, 1)
    return (t >= t0) & (t <= t1) & (px * px + pr * pr + pz * pz <= rad * rad), t

def add_hauberk(G, B, SA, world, mat, L, cz, sh_r, elbow_r, scale=False, belt_on=True, HEM=57.4):
    """A mail hauberk or a scale shirt: a loose shirt over the body with a collar, short flared
    sleeves to the elbow, a belt at the waist and an A-line skirt to above the knee with a
    riding slit; mail rings that hang in soft folds below the belt, or overlapping scales with a
    scalloped hem."""
    r, x, z = B.r, B.x, B.z
    ramp, lv, pat = mat
    pat = 'scale' if scale else pat
    def paint(cx_=32.0, cz_=cz, folds=False, hem=None):
        def ex(r, x, z, i):
            i = i.copy()
            if folds:
                u = arc_u(x, z, cx_, cz_, 10.5)
                i[((u + 1.3 * np.sin(r * 0.35)) % 3.6) < 0.55] -= 1          # the mail hangs in folds
            if hem is not None: i[r > hem - 0.7] -= 1
            return i
        return plate_paint((ramp, lv, pat), ex, centre=(cx_, cz_))
    # the shirt over the chest, a little loose
    shirt = hoop(B, cz, 31.6, 46.0, grow=0.2, out=0.6)
    G.add(shirt & ~G.solid(), paint(), lit=True, space=B)
    # collar
    t = np.clip((r - 29.6) / 2.8, 0, 1)
    collar = (np.hypot((x - 32) / (5.2 + 1.4 * t), (z - cz) / (5.0 + 1.4 * t)) <= 1) & (r >= 29.6) & (r < 32.4)
    G.add(collar & ~G.solid(), paint(), lit=True, space=B)
    # skirt: A-line from the waist to above the knee, split front and back below the belt
    t = np.clip((r - 46.0) / (HEM - 46.0), 0, 1)
    rx, rz = 10.9 + 1.7 * t, 9.2 + 1.2 * t
    skirt = (np.abs((x - 32) / rx) ** 2.6 + np.abs((z - cz) / rz) ** 2.6 <= 1) & (r >= 46.0) & (r < HEM + 0.6)
    if scale:
        u = arc_u(x, z, 32, cz, 9.0); fu = ((u + 1.5 * (np.floor(HEM / 2.2) % 2)) % 3.0) / 3.0
        skirt &= r < HEM - 0.2 + 0.8 * np.sqrt(np.clip(1 - (2 * fu - 1) ** 2, 0, 1))   # scalloped: each scale's round bottom
    else:
        skirt &= r < HEM
    skirt &= ~((np.abs(x - 32) < 0.7) & (r > 51.5))                    # the riding slit
    G.add(skirt & ~G.solid(), paint(folds=not scale, hem=HEM), lit=True, space=B)
    # sleeves: short, flaring a little, to the elbow
    left, _ = tube(SA, (44.2, 32.6, cz), (44.2, 44.6, cz), 4.9, 5.7, -0.05, 1.0)
    G.add(left & ~G.solid(), paint(44.2, cz, hem=44.6), lit=True, space=SA)
    right, tr = tube(world, sh_r, elbow_r, 4.9, 5.7, -0.2, 0.92)
    def r_ex(r, x, z, i):
        _, tt = tube(Space(r, x, z), sh_r, elbow_r, 0, 0)
        i = i.copy(); i[tt > 0.82] -= 1; return i
    rp = plate_paint((ramp, lv, pat), r_ex, centre=(sh_r[0], sh_r[2]))
    G.add(right & ~G.solid(), rp, lit=True, space=world)
    if not belt_on: return
    # the belt and a small buckle
    belt = accent_of(L, [46], (20, 44)) or ([(74, 44, 24, 255), (110, 70, 40, 255), (146, 100, 62, 255)], np.array([0, 1, 1, 2]))
    bm = hoop(B, cz, 45.6, 47.2, grow=0.0, out=1.25)
    G.add(bm & ~G.solid(), lit(belt[0], belt[1]), lit=True, space=B)
    bk = hoop(B, cz, 45.3, 47.5, grow=0.0, out=1.8) & (np.abs(x - 32) < 1.4) & (z < cz)
    G.add(bk & ~G.solid(), lit(ramp, np.minimum(lv + 1, len(ramp) - 1)), lit=True, space=B)

# ---------- tabard and robe, cloth ----------
def front_depth(rz, rx, x, p=2.6):
    """How far in front of the body's middle its surface is at column x (body half-width rx,
    half-depth rz)."""
    return rz * np.clip(1 - np.clip(np.abs(x - 32) / rx, 0, 1) ** p, 0, 1) ** (1 / p)

def add_tabard(G, B, SA, world, L, cz, sh_r, elbow_r):
    """A tabard: a mail hauberk to row 55 and over it a cloth panel front and back where the
    sprite draws cloth, hanging straight from the belt in soft folds, the belt over it."""
    r, x, z = B.r, B.x, B.z
    # the mail: what the sprite draws at the sides, beside the panel (gold mail is not grey)
    side = L.region['S'][34:45, 17:24]; side = side[side >= 0]
    mg = int(np.bincount(side).argmax()) if len(side) else L.metal_g
    add_hauberk(G, B, SA, world, (L.ramps[mg], np.asarray(L.levels[mg]), 'mail'), L, cz, sh_r, elbow_r, belt_on=False, HEM=55.6)
    cloth = {g for g in range(len(L.ramps)) if g != mg}
    pr, px = np.clip(r.astype(int), 0, P - 1), np.clip(x.astype(int), 0, P - 1)
    in_front = np.isin(L.region['S'][pr, px], list(cloth))
    cn = np.clip(L.col('N', px), 0, P - 1)
    in_back = np.isin(L.region['N'][pr, cn], list(cloth))
    t_up = np.clip((r - 31.6) / 14.4, 0, 1)
    t_sk = np.clip((r - 46.0) / 9.6, 0, 1)
    shirt_rx, shirt_rz = torso_rx(r) + 0.6 + 0.2 * t_up, 8.6 + 0.6 + 0.2 * t_up
    skirt_rx, skirt_rz = 10.9 + 1.7 * t_sk, 9.2 + 1.2 * t_sk
    body = np.where(r < 46.0, front_depth(shirt_rz, shirt_rx, x), front_depth(skirt_rz, skirt_rx, x))
    hang = front_depth(9.6, 10.8, x)                                    # below the belt it hangs straight
    inner = np.where(r < 46.0, body, np.maximum(body, hang)) + 0.25
    fold = np.where(r > 46.5, 0.45 * np.sin((x - 32) * 1.25) * np.clip((r - 46.5) / 6.0, 0, 1), 0.0)
    depth = np.abs(z - cz)
    panel_f = in_front & (z < cz) & (depth >= inner + fold) & (depth < inner + fold + 0.9) & (r >= 32.6) & (r < 55.8)
    panel_b = in_back & (z >= cz) & (depth >= inner + fold) & (depth < inner + fold + 0.9) & (r >= 32.6) & (r < 55.8)
    G.add((panel_f | panel_b) & ~G.solid(), dressed([L], lambda rr: (32, cz, 10, 8.6), front=89, back=89, sides=''), lit=True, space=B)
    belt = accent_of(L, [46], (22, 42)) or ([(74, 44, 24, 255), (110, 70, 40, 255), (146, 100, 62, 255)], np.array([0, 1, 1, 2]))
    bm = hoop(B, cz, 45.6, 47.2, grow=0.0, out=2.2)
    G.add(bm & ~G.solid(), lit(belt[0], belt[1]), lit=True, space=B)

def add_robe(G, B, SA, world, L, cz, sh_r, elbow_r):
    """A robe: a bodice over the chest with a collar and cloth caps over the shoulders, a skirt
    flaring from the hips to the ankles in folds that deepen toward the hem, a trim strip down
    the front, a sash at the waist and a trimmed hem, as the sprite draws them."""
    r, x, z = B.r, B.x, B.z
    main = L.main()
    others = sorted([g for g in range(len(L.ramps)) if g != main], key=lambda g: -L.weight[g])
    cloth = (L.ramps[main], np.asarray(L.levels[main]))
    tg = others[0] if others else main
    trim = (L.ramps[tg], np.asarray(L.levels[tg]))
    th = np.arctan2(x - 32, -(z - cz))
    def robe_paint(front_strip=True, hem_from=None):
        def at(r, x, z):
            m = np.zeros(r.shape, bool)
            if front_strip: m |= (np.abs(x - 32) < 1.6) & (z < cz)
            if hem_from is not None: m |= r > hem_from
            m |= (r >= 45.6) & (r < 47.2)                                  # the sash
            return m
        return two_tone(cloth, trim, accent_at=at)
    bodice = hoop(B, cz, 31.0, 46.0, grow=0.2, out=0.5)
    t = np.clip((r - 29.6) / 2.4, 0, 1)
    collar = (np.hypot((x - 32) / (5.0 + 1.2 * t), (z - cz) / (4.8 + 1.2 * t)) <= 1) & (r >= 29.6) & (r < 32.0)
    G.add((bodice | collar) & ~G.solid(), robe_paint(), lit=True, space=B)
    G.add(hoop(B, cz, 45.6, 47.2, grow=0.0, out=1.1) & ~G.solid(), lit(*trim), lit=True, space=B)
    # skirt: from the hips to the ankles, folds deepening toward the hem
    HEM = 62.6
    t = np.clip((r - 46.0) / (HEM - 46.0), 0, 1) ** 1.3
    wave = 1 + 0.07 * t * np.sin(7 * th + 0.6) + 0.03 * t * np.sin(13 * th)
    rx, rz = (10.8 + 5.0 * t) * wave, (9.1 + 3.4 * t) * wave
    skirt = (np.abs((x - 32) / rx) ** 2.4 + np.abs((z - cz) / rz) ** 2.4 <= 1) & (r >= 46.0) & (r < HEM)
    skirt &= ~(np.abs((x - 32) / (rx - 1.2)) ** 2.4 + np.abs((z - cz) / (rz - 1.2)) ** 2.4 <= 1) | (r < 50)   # hollow below: legs walk inside
    G.add(skirt & ~G.solid(), robe_paint(hem_from=HEM - 2.8), lit=True, space=B)
    # cloth caps over the shoulders
    left, _ = tube(SA, (44.2, 31.8, cz), (44.2, 39.5, cz), 5.0, 5.6, -0.05, 1.0)
    G.add(left & ~G.solid(), lit(*cloth), lit=True, space=SA)
    right, _ = tube(world, sh_r, elbow_r, 5.0, 5.6, -0.2, 0.5)
    G.add(right & ~G.solid(), lit(*cloth), lit=True, space=world)

# ---------- leg armour and boots, shaped ----------
BROWN = ([(38, 22, 10, 255), (74, 44, 24, 255), (110, 70, 40, 255), (146, 100, 62, 255)], np.array([0, 1, 2, 3]))

def foot_of(S_, cx, cz, grow=0.0):
    """The foot: a boot-shaped block sloping down to the toe."""
    toe_top = 61.0 + np.clip((cz - 2.0 - S_.z) * 0.38, 0, 2.2) - grow * 0.6
    return (np.abs((S_.x - cx) / (5.0 + grow)) ** 2.4 + np.abs((S_.z - (cz - 2.4)) / (7.8 + grow)) ** 2.2 <= 1) & (S_.r >= toe_top) & (S_.r < 64)

def add_boot(G, S_, cx, cz, top, colour, cuff=True):
    """A leather boot: a shaft from row `top` down, a turned-down cuff, the foot and a dark sole."""
    ramp, lv = colour
    shaft = S_.col(top, 61.6, cx, cz + 0.2, 5.0, 5.4, 2.4)
    foot = foot_of(S_, cx, cz, grow=0.3)
    def ex(r, x, z, i):
        i = i.copy(); i[r > 63.3] = -100                               # the sole
        i[(r > 61.4) & (r < 61.9) & (z > cz - 1)] -= 1                 # the heel's crease
        return i
    G.add(shaft | foot, lit(ramp, lv, extra=ex), lit=True, space=S_)
    if cuff:
        c = S_.col(top - 0.3, top + 1.1, cx, cz + 0.2, 5.6, 6.0, 2.4)
        G.add(c, lit(ramp, np.minimum(np.asarray(lv) + 1, len(ramp) - 1)), lit=True, space=S_)

def add_leg_gear(G, S_, cx, cz, kind, L, skirt):
    """One leg's armour or clothing by kind, on the leg's own swinging space."""
    r, x, z = S_.r, S_.x, S_.z
    side = -1 if cx < 32 else 1
    main = L.main()
    M = (L.ramps[main], np.asarray(L.levels[main]))
    boots = accent_of(L, [61, 62, 63], (19, 44))
    if boots is None: boots = (M[0], np.maximum(M[1] - 1, 0))
    if kind == 'plate':
        if not skirt:
            cuisse = S_.col(52.6, 57.6, cx, cz, 6.1, 6.7, 2.4)
            def c_ex(r, x, z, i):
                i = i.copy(); i[(np.abs(x - cx) < 0.7) & (z < cz)] += 1; i[r > 57.0] = -100; return i
            G.add(cuisse, lit(*M, extra=c_ex), lit=True, space=S_)
        poleyn = S_.ell(58.3, cx, cz - 5.2, 2.0, 3.0, 2.0, 2.2) | S_.ell(58.4, cx + side * 3.6, cz - 2.8, 1.7, 0.9, 2.0, 2.2)
        poleyn |= S_.col(57.4, 59.6, cx, cz, 5.4, 5.9, 2.4)
        def p_ex(r, x, z, i):
            i = i.copy(); i[r < 57.9] += 1; return i
        G.add(poleyn, lit(*M, extra=p_ex), lit=True, space=S_)
        greave = S_.col(59.3, 61.8, cx, cz + 0.2, 5.0, 5.5, 2.4) | ((np.abs(x - cx) < 0.8) & S_.col(59.3, 61.8, cx, cz + 0.2, 5.4, 6.1, 2.4))
        def g_ex(r, x, z, i):
            i = i.copy(); i[(np.abs(x - cx) < 0.6) & (z < cz)] += 1; return i
        G.add(greave, lit(*M, extra=g_ex), lit=True, space=S_)
        sab = foot_of(S_, cx, cz, grow=0.4)
        def s_ex(r, x, z, i):
            i = i.copy() - 1
            i[(z < cz) & (((z - (cz - 10.0)) % 1.5) < 0.4)] = -100       # lames across the foot
            i[r > 63.4] = -100
            return i
        G.add(sab, lit(*M, extra=s_ex), lit=True, space=S_)
        return
    if kind in ('mail', 'scale', 'leather'):
        top = 52.6 if not skirt else 56.6
        tube_ = S_.col(top, 60.0, cx, cz, 5.9, 6.5, 2.4) & (r < 57.6) | S_.col(57.4, 60.0, cx, cz + 0.1, 5.3, 5.8, 2.4)
        if kind == 'leather':
            def l_ex(r, x, z, i):
                i = i.copy(); out = side * (x - cx) > 4.6
                i[out & ((r % 1.2) < 0.55)] -= 1                            # stitches down the outer seam
                return i
            G.add(tube_, lit(*M, extra=l_ex), lit=True, space=S_)
        else:
            G.add(tube_, plate_paint((M[0], M[1], kind), centre=(cx, cz)), lit=True, space=S_)
        add_boot(G, S_, cx, cz, 59.8, boots if kind != 'leather' else (M[0], np.maximum(M[1] - 1, 0)))
        return
    if kind == 'cloth':
        others = [g for g in range(len(L.ramps)) if g != main]
        wrap = (L.ramps[others[0]], np.asarray(L.levels[others[0]])) if others else M
        if not skirt:
            t = np.clip((r - 52.6) / 4.2, 0, 1)
            bulge = 0.9 * np.sin(np.pi * t)
            breeches = (np.abs((x - cx) / (6.0 + bulge)) ** 2.4 + np.abs((z - cz) / (6.6 + bulge)) ** 2.4 <= 1) & (r >= 52.6) & (r < 56.9)
            def b_ex(r, x, z, i):
                i = i.copy(); i[r > 56.3] -= 1                              # gathered at the calf
                i[(np.sin(np.arctan2(x - cx, z - cz) * 5 + r * 0.3)) > 0.75] -= 1   # creases
                return i
            G.add(breeches, lit(*M, extra=b_ex), lit=True, space=S_)
        wraps = S_.col(56.8, 60.0, cx, cz + 0.1, 5.3, 5.8, 2.4)
        def w_ex(r, x, z, i):
            i = i.copy(); u = np.arctan2(x - cx, -(z - cz)) * 5.5
            i[((r * 1.25 + u * 0.45) % 1.6) < 0.42] = -100                # the wrapping's spiral
            return i
        G.add(wraps, lit(*wrap, extra=w_ex), lit=True, space=S_)
        add_boot(G, S_, cx, cz, 59.9, (M[0], M[1]), cuff=False)
        return
    if kind == 'boots':
        add_boot(G, S_, cx, cz, 58.2, M)

# ---------- the unit ----------
def prepare(lo, f=0):
    """The sprite layers of a loadout, made ready to paint from (shared by build and build3d10)."""
    import types
    mouth_px = []
    race = getattr(lo, 'race', 'Human')
    BODY = getattr(lo, 'body', None) or ('Races64/%s.dmi' % race, '')
    HAIR = (('Gear64/%s/old-Hair.dmi' % race) if race != 'Human' else GEAR + 'old-Hair.dmi', lo.hair) if lo.hair else None
    srcs = [BODY] + [s for s in (lo.legs, lo.chest, HAIR) if s] + (list(lo.arms) if lo.arms else []) + \
           [s for s in (lo.helmet, lo.shield, lo.weapon) if s]
    full = compose64.unit(srcs, f)
    aS, aN, aE, aW = (arr(full[d])[:, :, 3] > 0 for d in 'SNEW')
    sN = carve.best_shift(aS, aN[:, ::-1]); sW = carve.best_shift(aE[:, ::-1], aW)
    Ly = lambda s: Layer(s, sN, sW, f) if s else None
    body, legs, chest = Ly(BODY), Ly(lo.legs), Ly(lo.chest)
    armL, armR = (Ly(lo.arms[0]), Ly(lo.arms[1])) if lo.arms else (None, None)
    helm, shield, weapon = Ly(lo.helmet), Ly(lo.shield), Ly(lo.weapon)
    hairL = Ly(HAIR)
    for L, slot in ((body, None), (legs, 'legs'), (chest, 'chest'), (armL, 'arms'), (armR, 'arms'), (helm, 'helmet')):
        if L:
            assign_roles(clean_regions(L), lo.kind(slot) if slot else 'skin')
            L.levels = []
            for gi in range(len(L.ramps)):            # shades as the front picture spreads them
                ks = L.k['S'][L.gid['S'] == gi]
                if len(ks): L.base[gi] = int(np.floor(np.median(ks)))
                L.levels.append(levels_of(ks, len(L.ramps[gi])))
            if slot is None:                          # bare skin: its brightest shades are eyes and teeth, not skin
                L.levels = [np.minimum(lv, lv[2]) for lv in L.levels]
    face_img = filled(deoutline(arr(compose64.unit([BODY], f)['S'])))
    if race in ('Human', 'HumanBlack', 'Dwarves'):          # human-like faces: hair off the cheeks, a designed mouth
        face_img = skin_face(face_img)
        face_img, mouth_px = design_mouth(face_img)
    STEEL = [(66, 70, 78, 255), (104, 109, 118, 255), (148, 154, 163, 255), (206, 212, 220, 255)]
    for L in (chest, legs, armR, helm):
        if L and L.kind in ('plate', 'banded', 'mail', 'scale', 'lamellar', 'tabard', 'brigandine'): STEEL = L.ramps[L.metal_g]; break
    # bare arms and legs are skin only (the body sprite draws dark shadow lines between limbs
    # and torso, and its underwear belongs on the hips)
    import copy
    skin = copy.copy(body); skin_g = body.main()
    skin.region = {d: np.where(body.region[d] >= 0, skin_g, -1) for d in 'SNEW'}
    if race not in ('Human', 'HumanBlack'):
        # other races keep their skin as drawn; on the limbs the dark gaps between limb and body
        # become the skin's shadow shade
        sh = tuple(np.array(body.ramps[skin_g][max(0, len(body.ramps[skin_g]) // 2 - 1)][:3]))
        # the outline colours: those the sprite draws along its silhouette's edge
        raw = body.raw['S']; al = raw[:, :, 3] > 0; pad = np.pad(al, 1)
        edge = al & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        ec, cnt = np.unique(raw[edge][:, :3], axis=0, return_counts=True)
        outl = [tuple(c) for c, k in zip(ec.tolist(), cnt.tolist()) if k >= 0.08 * cnt.sum() and sum(c) < 200]
        # anything darker than the skin's own darkest shade is outline (black lines, the brown brow line)
        # the skin's own colours: the most common in the front picture (the colour grouping chains
        # the sprites' near-black outline browns into the skin, so it can't say what skin is)
        opq = raw[al][:, :3]
        sc, sk = np.unique(opq, axis=0, return_counts=True)
        skins = [tuple(c) for c, k in zip(sc.tolist(), sk.tolist()) if k >= 0.02 * len(opq) and sum(c) >= 100]
        if skins:
            darkest = min(skins, key=sum); sh = darkest
            skin_dark = sum(darkest)
        else:
            skin_dark = 92
        body.drawn = {'dark': min(130, skin_dark - 2), 'shade': sh, 'outline': outl}
        skin.drawn = {'dark': min(130, skin_dark - 2), 'shade': sh, 'outline': outl}
        if skins:
            # clean skin: the common skin colours as a ramp, shaded the way the sprite spreads them
            ramp_ = sorted([s_ + (255,) for s_ in skins], key=lambda c: sum(c[:3]))
            idx = np.array([min(range(len(ramp_)), key=lambda i: np.abs(np.array(ramp_[i][:3]) - p_).sum()) for p_ in opq
                            if np.abs(np.array(ramp_)[:, :3] - p_).sum(1).min() < 40])
            lv_ = levels_of(idx, len(ramp_)) if len(idx) else np.array([0, 0, 0, 0])
            # the sprite's broad light and dark areas on the skin (muscles, a lighter chest), as a
            # shade offset of -1/0/+1, smoothed so single dark pixels don't speckle
            R_ = np.array(ramp_)[:, :3]; tone = {}
            for f_ in 'SNEW':
                im = body.img[f_]
                dd = np.abs(im[:, :, None, :3] - R_[None, None]).sum(-1)
                k_ = dd.argmin(-1); ok_ = (dd.min(-1) < 40) & (im[:, :, 3] > 0)
                kk = np.where(ok_, k_ - lv_[1], 0).astype(float)
                pad_ = np.pad(kk, 2, mode='edge')
                stack = np.stack([pad_[i:i + P, j:j + P] for i in range(5) for j in range(5)])   # broad areas, not single pixels
                tone[f_] = np.where(ok_, np.clip(np.round(np.median(stack, axis=0)), -1, 1), 0).astype(int)
            # the face's own features only: dark pixels joined (through dark pixels) to the outside are
            # outline - ears' and jaw's edges - not features
            fi = face_img; fal = fi[:, :, 3] > 0
            fdark = fal & ((fi[:, :, :3].sum(2) < 110) | ((fi[:, :, 0] > fi[:, :, 1] + 15) & (fi[:, :, :3].sum(2) < 200)))
            outside = ~np.pad(fal, 1)
            conn = np.zeros((P + 2, P + 2), bool); conn[outside] = True
            fd = np.pad(fdark, 1)
            for _ in range(P):
                grow = conn.copy()
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    grow |= np.roll(np.roll(conn, dy, 0), dx, 1)
                new_ = grow & fd & ~conn
                if not new_.any(): break
                conn |= new_
            face_edge = conn[1:-1, 1:-1] & fal
            for L_ in (body, skin): L_.drawn.update(clean=True, ramp=ramp_, levels=lv_, tone=tone, face_edge=face_edge)
            # the sprite's own colours, its outline lines filled in (build3d11.clean_picture): the
            # skin as drawn, with its contrast - darker limbs, lighter chest
            try:
                import build3d11, build3d10
                S_ = build3d10.parts_of(race)
                hrows = sorted(S_['head']); hcols = [c for r_ in hrows for c in S_['head'][r_]]
                fb = ((hrows[0] + 2, S_['neck'] + 1), (min(hcols) + 2, max(hcols) - 1))
                pix = {f_: build3d11.clean_picture(body.raw[f_], fb if f_ == 'S' else None) for f_ in 'SNEW'}
                # broad areas only: each pixel becomes the commonest colour round it (5x5), so the
                # sprite's light and dark areas stay but single-pixel noise goes; the face stays crisp
                rr_, cc_ = np.mgrid[0:P, 0:P]
                (fr0, fr1), (fc0, fc1) = fb
                for f_ in 'SNEW':
                    im = pix[f_]; al_ = im[:, :, 3] > 0
                    key = (im[:, :, 0].astype(np.int64) << 16) | (im[:, :, 1].astype(np.int64) << 8) | im[:, :, 2]
                    out_ = im.copy()
                    for y_ in range(P):
                        for x_ in range(P):
                            if not al_[y_, x_]: continue
                            if f_ == 'S' and fr0 <= y_ < fr1 and fc0 <= x_ < fc1: continue
                            ys = slice(max(0, y_ - 2), y_ + 3); xs = slice(max(0, x_ - 2), x_ + 3)
                            ks_ = key[ys, xs][al_[ys, xs]]
                            vals, cnt = np.unique(ks_, return_counts=True)
                            kk_ = vals[np.argmax(cnt)]
                            out_[y_, x_, :3] = ((kk_ >> 16) & 255, (kk_ >> 8) & 255, kk_ & 255)
                    pix[f_] = out_
                for L_ in (body, skin): L_.drawn['pix'] = pix
            except Exception:
                pass
    worn = [l for l in (chest, armR, armL, legs) if l]
    def cover(*first, bare=None):
        out = [l for l in first if l]
        return out + [l for l in worn if l not in out] + [bare or body]
    braw = arr(compose64.unit([BODY] + [s_ for s_ in (lo.legs, lo.chest) if s_] + (list(lo.arms) if lo.arms else []), f)['S'])
    prow = lambda cols: plate_rows(braw, cols)
    return types.SimpleNamespace(race=race, BODY=BODY, HAIR=HAIR, full=full, body=body, legs=legs, chest=chest, armL=armL, armR=armR, helm=helm, shield=shield, weapon=weapon, hairL=hairL, face_img=face_img, STEEL=STEEL, skin=skin, worn=worn, cover=cover, braw=braw, prow=prow, mouth_px=mouth_px)

def build(lo=None, rig=None, sub=2, f=0, zoff=12):
    lo = lo or KNIGHT; rig = rig or Rig()
    _p = prepare(lo, f)
    race, BODY, HAIR, full, body, legs, chest, armL, armR, helm, shield, weapon, hairL, face_img, STEEL, skin, worn, cover, braw, prow, mouth_px = _p.race, _p.BODY, _p.HAIR, _p.full, _p.body, _p.legs, _p.chest, _p.armL, _p.armR, _p.helm, _p.shield, _p.weapon, _p.hairL, _p.face_img, _p.STEEL, _p.skin, _p.worn, _p.cover, _p.braw, _p.prow, _p.mouth_px
    G = Grid(sub); G.z = G.z - zoff; G.center = (32.0 * sub, (CZ + zoff) * sub)
    G.base = set()                                    # the bare body's own parts (build3d10 swaps them for a race's)
    G.joints = {}
    world = Space(G.r, G.x, G.z); B = world.lifted(rig.rise); cz = CZ
    robe = lo.kind('chest') == 'robe'

    # legs
    for cx, (ang, lift) in zip((25.5, 38.5), rig.legs):
        S_ = B.lifted(lift).swung((cx, HIP_ROW, cz), ang)
        thigh = S_.col(53, 57.6, cx, cz, 5.6, 6.2, 2.4)
        knee = S_.col(57.4, 59.6, cx, cz, 5.0, 5.5, 2.4) | S_.ell(58.2, cx, cz - 4.9, 1.6, 2.7, 1.7, 2.2)
        shin = S_.col(59.4, 61.2, cx, cz + 0.2, 4.6, 5.0, 2.4)
        toe_top = 61.0 + np.clip((cz - 2.0 - S_.z) * 0.38, 0, 2.2)
        boot = (np.abs((S_.x - cx) / 5.0) ** 2.4 + np.abs((S_.z - (cz - 2.4)) / 7.8) ** 2.2 <= 1) & (S_.r >= toe_top) & (S_.r < 64)
        cuff = S_.col(60.4, 61.6, cx, cz + 0.2, 5.3, 5.7, 2.4)
        G.add(thigh | knee | shin | boot | cuff,
              dressed(cover(chest if robe else None, legs, bare=skin), lambda rr, cx=cx: (cx, cz, 5.6, 6.2), front=50,
                      sides='E' if cx < 32 else 'W', rows=prow((int(cx) - 3, int(cx) + 3))), lit=True, space=S_)
        G.base.add(len(G.parts) - 1)
        if legs and lo.kind('legs') in ('plate', 'mail', 'scale', 'leather', 'cloth', 'boots'):
            add_leg_gear(G, S_, cx, cz, lo.kind('legs'), legs, skirt=lo.kind('chest') in ('mail', 'scale', 'tabard', 'robe'))
    torso_rows = prow((27, 37))
    G.add(B.col(49, 56, 32, cz, 11.2, 8.4, 2.6), dressed(cover(chest, legs), lambda rr: (32, cz, 11.2, 8.4), front=50, rows=torso_rows), lit=True, space=B)
    G.base.add(len(G.parts) - 1)
    rx_t = np.where(B.r < 35, 6 + 4 * np.clip((B.r - 31) / 3, 0, 1), 10.0)
    torso = (np.abs((B.x - 32) / rx_t) ** 2.6 + np.abs((B.z - cz) / 8.6) ** 2.6 <= 1) & (B.r >= 32) & (B.r < 53)
    G.add(torso, dressed(cover(chest), lambda rr: (32, cz, 10, 8.6), front=50, rows=torso_rows), lit=True, space=B)
    G.base.add(len(G.parts) - 1)
    if False:   # the robe is shaped in add_robe
        rad = 10.6 + np.clip(B.r - 50, 0, None) * 0.22
        skirt = (np.abs((B.x - 32) / rad) ** 2.4 + np.abs((B.z - cz) / (rad - 1.6)) ** 2.4 <= 1) & (B.r >= 50) & (B.r < 61.5)
        G.add(skirt, dressed(cover(chest, legs), lambda rr: (32, cz, 11.5, 9.0), front=50), lit=True, space=B)

    if False:   # banded and lamellar have their own sculpted pieces now (add_banded, add_lamellar)
        # broad shoulder plates, out past the arms (the sprites draw them at x 14-24 and 40-50)
        for pcx in (19.0, 45.0):
            cap = B.ell(35.6, pcx, cz, 4.0, 6.0, 5.6, 2.4) & (B.r < 38.6)
            G.add(cap, dressed(cover(chest), lambda rr, pcx=pcx: (pcx, cz, 6.0, 5.6), front=55, rows=torso_rows), lit=True, space=B)
    SA = B.swung(SHOULDER_L, rig.shield)
    arm_l = SA.col(33, 48.5, 44.2, cz, 4.0, 4.3, 2.2) | SA.ell(35, 44.2, cz, 4.5, 4.8, 4.8) | SA.col(48.5, 52, 44.2, cz - 0.5, 3.6, 3.9, 2.4)
    G.add(arm_l, dressed(cover(armL, chest, bare=skin), lambda rr: (44.2, cz, 4.0, 4.3), front=55, sides='', rows=prow((41, 48))), lit=True, space=SA)
    G.base.add(len(G.parts) - 1)
    G.rigid = []
    if shield:
        a_ = len(G.parts); add_shield(G, SA, lo.kind('shield'), shield, STEEL); G.rigid.append(('shield', a_, len(G.parts), None))

    elbow, fist_p, dvec = rig.sword
    sh = SHOULDER_R
    elbow = swing_point(np.array(elbow, float), sh, rig.sword_swing); fist_p = swing_point(np.array(fist_p, float), sh, rig.sword_swing)
    d = np.array(dvec, float); d /= np.linalg.norm(d); d = swing_point(sh + d, sh, rig.sword_swing) - sh
    lift = np.array([0, -rig.rise, 0])
    elbow_w, fist_w, sh_w = elbow + lift, fist_p + lift, sh + lift
    G.joints.update(sh=sh_w, elbow=elbow_w, fist=fist_w, rise=rig.rise, legs=rig.legs, shield=rig.shield)
    E0, W0 = np.array([19.8, 42.5, cz]), np.array([19.8, 47.5, cz - 0.2])
    US = limb_space(world, sh_w, elbow_w, sh, E0); FS = limb_space(world, elbow_w, fist_w, E0, W0)
    upper = world.capsule(sh_w, elbow_w, 4.0) | world.ell(sh_w[1], sh_w[0], sh_w[2], 4.5, 4.8, 4.8) | world.ell(elbow_w[1], elbow_w[0], elbow_w[2], 3.6, 3.6, 3.6)
    forearm = world.capsule(elbow_w, fist_w, 3.3)
    fx, fr, fz = fist_w
    fist = (np.abs((world.x - fx) / 2.7) ** 2.6 + np.abs((world.r - fr) / 2.7) ** 2.6 + np.abs((world.z - fz) / 3.0) ** 2.6) <= 1
    armc = lambda rr: (19.8, cz, 4.0, 4.3)
    G.add(upper, dressed(cover(armR, chest, bare=skin), armc, front=55, sides='', rows=prow((16, 23))), lit=True, space=US)
    G.base.add(len(G.parts) - 1)
    G.add(forearm | fist, dressed(cover(armR, chest, bare=skin), armc, front=55, sides='', rows=prow((16, 23))), lit=True, space=FS)
    G.base.add(len(G.parts) - 1)
    if lo.kind('chest') == 'plate':
        add_plate(G, B, SA, world, plate_material(chest), cz, elbow_w, (44.2, 42.5, cz))
    elif lo.kind('chest') == 'banded':
        add_banded(G, B, plate_material(chest), chest, cz)
    elif lo.kind('chest') == 'lamellar':
        add_lamellar(G, B, plate_material(chest), chest, cz)
    elif lo.kind('chest') == 'tabard':
        add_tabard(G, B, SA, world, chest, cz, sh_w, elbow_w)
    elif lo.kind('chest') == 'robe':
        add_robe(G, B, SA, world, chest, cz, sh_w, elbow_w)
    elif lo.kind('chest') in ('mail', 'scale'):
        add_hauberk(G, B, SA, world, plate_material(chest), chest, cz, sh_w, elbow_w, scale=lo.kind('chest') == 'scale')
    G.add(B.col(30, 35, 32, cz, 4.5, 4.5), dressed(cover(chest), lambda rr: (32, cz, 4.5, 4.5)), lit=True, space=B)
    G.base.add(len(G.parts) - 1)

    hc = (22.5, 32.0, 31.5, 11.2, 11.0, 11.0)
    head = B.ell(*hc, p=2.2, pfront=np.where(B.r > 24.0, 4.2, 3.2))    # the lower face flat, so the mouth faces the camera
    G.add(head, dressed([body], lambda rr: (hc[1], hc[2], hc[4], hc[5]), front=78, back=60, face=(face_img, 78)), lit=True, space=B)
    G.base.add(len(G.parts) - 1)
    if hairL:
        HR = np.array(sorted(hairL.ramps[hairL.main()], key=lambda c: sum(c[:3])))
        hk = hairL.k['S'][hairL.gid['S'] == hairL.main()]
        hbase = int(np.floor(np.median(hk))) if len(hk) else len(HR) // 2          # the shade the sprite's hair mostly is
        cr, cx0, cz0, rr_, rx_, rz_ = hc; t = 1.1
        r, x, z = B.r, B.x, B.z
        th = np.arctan2(x - cx0, z - cz0)
        flare = np.clip(r - cr, 0, None) * 0.05 - np.clip(r - 28.0, 0, None) * 0.35     # tucks in toward the neck
        rad_out = np.abs((x - cx0) / (rx_ + t + flare)) ** 2.2 + np.abs((z - cz0) / (rz_ + t + flare)) ** 2.2
        shell = (np.abs((r - cr) / (rr_ + t)) ** 2.2 + rad_out <= 1) | ((r > cr) & (rad_out <= 1))
        ends_of = lambda th: 33.2 - 2.4 * np.clip((np.abs(th) - 1.1) / 0.6, 0, 1) + 0.9 * np.sin(th * 7 + 0.6) + 0.6 * np.sin(th * 13)
        back_hair = shell & ~head & (r >= 15) & (z >= cz0 - 1.5) & (r < ends_of(th)) & ~((r > 31) & (z < cz0 + 0.5))
        locks = np.zeros_like(head)
        top = 18.4 if helm else 13.0
        for s in (-1, 1):
            lx = cx0 + s * (rx_ - 0.4); wav = 0.5 * np.sin((z - cz0) * 1.3 + s)
            locks |= (np.abs(x - lx) <= 2.4) & (z >= cz0 - 8.6) & (z < cz0 + 1.5) & (r >= top + (z - (hc[2] - hc[5])) * 0.17) & (r < 32.5 + wav) & ~head
        # bare-headed: hair over the crown, and a fringe across the forehead down to the brows
        cap = (shell & ~head & ((r < 15) | ((z < cz0) & (r < 17.2)))) if not helm else np.zeros_like(head)
        def hair_paint(r, x, z, n):
            th = np.arctan2(x - cx0, z - cz0)
            i = hbase + band(n) - 1 + np.round(1.2 * np.sin(th * 15 + 0.4 * np.sin(r * 0.7))).astype(int)
            i = i - ((r > ends_of(th) - 1.6) & (z >= cz0 - 1.5)); i = i - ((r > 30.5) & (z < cz0 + 1.0))
            return HR[np.clip(i, 0, len(HR) - 1)].copy()
        G.add(back_hair | locks | cap, hair_paint, lit=True, space=B)
        if helm:
            edge = {'great helm': 29.5, 'kettle': 28.0}.get(lo.kind('helmet'), None)
            rim = 17.6 + (B.z - (hc[2] - hc[5])) * 0.17 if edge is None else edge
            G.clear((G.owner == len(G.parts) - 1) & B.ell(hc[0] + 0.3, hc[1], hc[2], hc[3] + 3.0, hc[4] + 3.4, hc[5] + 3.4, p=2.2) & (B.r <= rim))
    G.helmet = set()
    if helm:
        a_ = len(G.parts); add_helmet(G, B, lo.kind('helmet'), helm, hc); G.helmet = set(range(a_, len(G.parts)))
    if weapon:
        a_ = len(G.parts); add_weapon(G, world, lo.kind('weapon'), weapon, fist_w, d, STEEL); G.rigid.append(('weapon', a_, len(G.parts), np.array(fist_w, float)))
    G.paint()
    return G, full
