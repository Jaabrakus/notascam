"""Our race's own body pixels on GOA's frames (owner 11-01: "a pixel overlay ... what each pixel is so you can expand it
for the bodies"). Each GOA pixel's part (partmap.py) and its place on that part's bone (how far along, how far across)
point at the same place on the race's standing sprite, along its own bone; the race's pixel there is taken. GOA keeps
its shape, its outline and its drawn lines (the race's dark lines would land in the wrong places); the body inside becomes the race's: chest, a woman's top, shorts, an Ashen's cracks, a
Marked's marks, bare feet.
"""
import numpy as np

from partmap import BONES, PARTS, TOE


def race_skeleton(a, lab, head, shorts_c, facing):
    """The race's standing skeleton (64 px), read off its own sprite."""
    al = a[..., 3] > 0
    hy, hx = np.nonzero(head)
    chin = hy.max()
    low = hx[hy >= chin - 1]
    j = {"N": np.array([(low.min() + low.max()) / 2 + 0.5, chin + 1.5])}
    key = np.array([[tuple(int(v) for v in a[y, x, :3]) in shorts_c for x in range(64)] for y in range(64)])
    shorts = al & key & ~head
    # the shorts' hem: the lowest row of dull dark cloth in the torso and leg zones (the sampled colours can miss it)
    rgb = a[..., :3].astype(float) / 255
    mx, mn = rgb.max(-1), rgb.min(-1)
    cloth = al & ~head & ((mx - mn) / np.maximum(mx, 1e-6) < 0.3) & (mx < 0.4) & (mx > 0.02) \
        & np.isin(lab, (1, 6, 7, 8, 9))
    rows = np.flatnonzero(shorts.sum(1) >= 3)
    feet = np.flatnonzero(al.any(1))[-1]
    if len(rows) >= 3:
        top = rows[0]
        # a hem row is mostly cloth (dark leg shadows and outline near the feet are not shorts)
        body_row = al & np.isin(lab, (1, 6, 7, 8, 9))     # not the hands hanging beside the shorts
        hem = [y for y in range(top, feet - 3) if cloth[y].sum() >= max(3, 0.5 * body_row[y].sum())]
        bot = max(rows[-1], hem[-1] if hem else rows[-1])
    else:                       # shorts not found (a colour the sample missed): GOA's share of the body below the chin
        top, bot = chin + int((feet - chin) * 0.45), chin + int((feet - chin) * 0.68)
    band = shorts[top + 1] if shorts[top + 1].any() else (al[top + 1] & (lab[top + 1] == 1))
    xs = np.flatnonzero(band if band.any() else al[top + 1])
    cx = (xs.min() + xs.max()) / 2 + 0.5
    j["P"] = np.array([cx, top + 0.5])
    half = (xs.max() - xs.min()) / 4
    side = {"S": (-1, 1), "N": (1, -1), "E": (0, 0), "W": (0, 0)}[facing]     # right, left: which way from the middle
    for s, sgn in zip("RL", side):
        hipx = cx + sgn * half
        def leg_x(y):
            xs = np.flatnonzero(al[y] & ((lab[y] == 1) | ((lab[y] >= 6) & (lab[y] <= 9))))
            xs = xs[(xs < cx) if sgn < 0 else (xs > cx)] if sgn else xs
            return (xs.min() + xs.max()) / 2 + 0.5 if len(xs) else hipx
        j[s + "Hp"] = np.array([hipx, top + 2.5])
        j[s + "K"] = np.array([leg_x(bot), bot + 0.5])
        j[s + "A"] = np.array([leg_x(feet - 3), feet - 2.5])
    for s, up, lo in (("R", 2, 3), ("L", 4, 5)):
        u, l = (lab == up) & al, (lab == lo) & al
        if not u.any() or not l.any():
            continue
        uy, ux = np.nonzero(u)
        ly, lx = np.nonzero(l)
        j[s + "S"] = np.array([ux[uy <= uy.min() + 1].mean() + 0.5, uy.min() + 1.5])
        j[s + "E"] = np.array([(ux[uy >= uy.max() - 1].mean() + lx[ly <= ly.min() + 1].mean()) / 2 + 0.5, (uy.max() + ly.min()) / 2 + 0.5])
        j[s + "H"] = np.array([lx[ly >= ly.max() - 1].mean() + 0.5, ly.max() - 1.5])
    for s, o in (("R", "L"), ("L", "R")):           # from the side one arm hides the other
        for k in "SEH":
            if s + k not in j:
                j[s + k] = j[o + k].copy()
    t = np.array(TOE[facing], float)
    j["RT"], j["LT"] = j["RA"] + t, j["LA"] + t
    return j


def thickness(img_alpha, pm_or_lab, parts, a, b):
    """Pixels of these parts per unit of bone length: twice the half-thickness."""
    n = sum(int(((pm_or_lab == p) & img_alpha).sum()) for p in parts)
    return n / max(np.linalg.norm(b - a), 1.0)


def texture(img, pm, gj, race, rj, half):
    """img: GOA's frame (64 px), pm: its part map, gj: its skeleton; race: the race's standing frame, rj: its skeleton;
    half: {part kind: (GOA half-width, race half-width)}. Returns img with the race's body pixels inside GOA's outline."""
    out = img.copy()
    ra = race[..., 3] > 0
    dark = img[..., :3].astype(int).sum(-1) < 120
    for i, b in enumerate(PARTS):
        if b == "head":
            continue
        f0, f1, _ = BONES[b]
        ys, xs = np.nonzero((pm == i) & ~dark)
        if not len(ys):
            continue
        p = np.stack([xs + 0.5, ys + 0.5], 1)
        g0, gv = gj[f0], gj[f1] - gj[f0]
        gL = max(np.linalg.norm(gv), 1e-6)
        gu = gv / gL
        gn = np.array([-gu[1], gu[0]])
        t = ((p - g0) @ gu) / gL
        s = (p - g0) @ gn
        r0, rv = rj[f0], rj[f1] - rj[f0]
        rL = max(np.linalg.norm(rv), 1e-6)
        ru = rv / rL
        rn = np.array([-ru[1], ru[0]])
        gw, rw = half["torso" if b == "torso" else "arm" if ("Up" in b or "Fore" in b) else "leg"]
        q = r0 + t[:, None] * rv + (s * rw / gw)[:, None] * rn
        qx, qy = np.floor(q[:, 0]).astype(int), np.floor(q[:, 1]).astype(int)
        ok = (qx >= 0) & (qx < 64) & (qy >= 0) & (qy < 64)
        ok[ok] &= ra[qy[ok], qx[ok]] & (race[qy[ok], qx[ok], :3].astype(int).sum(-1) >= 120)   # GOA keeps its own lines
        out[ys[ok], xs[ok], :3] = race[qy[ok], qx[ok], :3]
    return out


ZONES = {"torso": (1,), "arm": (2, 3, 4, 5), "leg": (1, 6, 7, 8, 9)}      # race part-map codes each GOA part draws from
LINKED = {frozenset(p) for p in (("RUp", "RFore"), ("LUp", "LFore"), ("RThigh", "RShin"), ("RShin", "RFoot"),
                                  ("LThigh", "LShin"), ("LShin", "LFoot"), ("torso", "RThigh"), ("torso", "LThigh"))}


def kind(b):
    return "torso" if b == "torso" else "arm" if ("Up" in b or "Fore" in b) else "leg"


def fill(img, pm, gj, race, lab, rj, half, borrowed=False, rest_gj=None):
    """The whole inside of a race-shaped GOA frame from the race's own sprite, at its own scale: each pixel's part and
    place along its bone point at the same place on the race's bone; the pixel there is taken if it is in the zone that
    part comes from (else a step nearer the bone). img, pm: the frame and its part map, already the race's size."""
    out = img.copy()
    ra = race[..., 3] > 0
    p = np.pad(ra, 1)
    inner = ra & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    for i, b in enumerate(PARTS):
        if b == "head":
            continue
        ys, xs = np.nonzero(pm == i)
        if not len(ys):
            continue
        p = np.stack([xs + 0.5, ys + 0.5], 1)
        if b == "torso" and rest_gj is not None:
            # the body itself is the race's own, carried as GOA's moves from its standing frame (GOA shifts a torso
            # rather than turning it): its chest, top, belly and markings exactly as drawn
            off = (gj["N"] + gj["P"] - rest_gj["N"] - rest_gj["P"]) / 2
            q = np.floor(p - off).astype(int)
            ok = (q[:, 0] >= 0) & (q[:, 0] < 64) & (q[:, 1] >= 0) & (q[:, 1] < 64)
            ok[ok] &= inner[q[ok, 1], q[ok, 0]] & (lab[q[ok, 1], q[ok, 0]] != 0)
            out[ys[ok], xs[ok], :3] = race[q[ok, 1], q[ok, 0], :3]
            ys, xs, p = ys[~ok], xs[~ok], p[~ok]
            if not len(ys):
                continue
        f0, f1, _ = BONES[b]
        g0, gv = gj[f0], gj[f1] - gj[f0]
        gL = max(np.linalg.norm(gv), 1e-6)
        gu = gv / gL
        gn = np.array([-gu[1], gu[0]])
        t = ((p - g0) @ gu) / gL
        s = (p - g0) @ gn
        r0, rv = rj[f0], rj[f1] - rj[f0]
        rL = max(np.linalg.norm(rv), 1e-6)
        rn = np.array([-rv[1], rv[0]]) / rL
        gw, rw = half[kind(b)]
        t = np.clip(t, 0.0, 1.0)            # a hand or foot past GOA's bone end takes the race's own hand or foot
        # the race's outer outline (the ring touching empty space) stays out, ours is drawn afterwards; its shading,
        # inner lines, clothes and markings come in
        # a borrowed part map (women, hybrids) is the man's: his arms lie over a woman's chest, so her torso takes
        # from her whole body
        zone = (np.isin(lab, ZONES[kind(b)]) | (borrowed and b == "torso")) & inner & (lab != 0)
        todo = np.ones(len(ys), bool)
        for shrink in (1.0, 0.75, 0.5, 0.25, 0.0):
            q = r0 + t[:, None] * rv + (s * rw / gw * shrink)[:, None] * rn
            qx, qy = np.floor(q[:, 0]).astype(int), np.floor(q[:, 1]).astype(int)
            ok = todo & (qx >= 0) & (qx < 64) & (qy >= 0) & (qy < 64)
            ok[ok] &= zone[qy[ok], qx[ok]]
            out[ys[ok], xs[ok], :3] = race[qy[ok], qx[ok], :3]
            todo &= ~ok
    return out


def clean_lines(img, lines):
    """Our sprites' line work: a black outline round the figure; inside it, GOA's own drawn lines where one part meets
    another (lines: those pixels, in the race-sized frame); stray pixels and pinholes gone."""
    out = img.copy()
    for _ in range(2):
        al = out[..., 3] > 0
        p = np.pad(al, 1)
        n = p[:-2, 1:-1].astype(int) + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]
        out[al & (n <= 1)] = 0
        hole = ~al & (n >= 3)
        if hole.any():
            src = np.pad(out, ((1, 1), (1, 1), (0, 0)))
            for dy, dx in ((0, 1), (1, 0), (2, 1), (1, 2)):
                nb = src[dy:dy + 64, dx:dx + 64]
                take = hole & (nb[..., 3] > 0) & (out[..., 3] == 0)
                out[take] = nb[take]
    al = out[..., 3] > 0
    p = np.pad(al, 1)
    edge = al & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    out[edge | (lines & al), :3] = 0
    return out


def part_lines(img, pm):
    """GOA's own black line pixels that sit between two different body parts (the artist's line where an arm crosses
    the body); a thin limb's own outline, with only one part beside it, is not one."""
    dark = (img[..., 3] > 0) & (img[..., :3].astype(int).sum(-1) < 30)
    pp = np.pad(pm, 1, constant_values=-1)
    nbs = [pp[dy:dy + 64, dx:dx + 64] for dy, dx in ((0, 1), (2, 1), (1, 0), (1, 2))]
    two = np.zeros(pm.shape, bool)
    for i in range(4):
        for j in range(i + 1, 4):
            two |= (nbs[i] >= 1) & (nbs[j] >= 1) & (nbs[i] != nbs[j])
    return dark & two
