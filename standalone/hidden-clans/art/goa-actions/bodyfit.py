"""Measuring a standing body (64 px): where its chin, crotch and feet are, and how wide it is at the chest and legs."""
import numpy as np


def span(row):
    xs = np.flatnonzero(row)
    return (xs[0], xs[-1]) if len(xs) else None


def measure(a, head, facing, leave_out=None):
    """a: the standing frame (RGBA), head: its head mask. Rows: chin (head's bottom), crotch (where the legs part, front
    and back views), feet; the body's width at the chest (side views: hair hanging down the back left out, or the waist
    where no hair is given) and its middle (at the waist from the side)."""
    al = a[..., 3] > 0
    chin = int(np.flatnonzero(head.any(1))[-1])
    feet = int(np.flatnonzero(al.any(1))[-1])
    body = al & ~head & (~leave_out if leave_out is not None else True)
    mid = span(body[chin + 3])
    cx = (mid[0] + mid[1]) / 2
    crotch = None
    if facing in "SN":
        for y in range(chin + (feet - chin) // 2, feet):
            x = int(round(cx))
            if not al[y, x - 1:x + 1].any():
                crotch = y
                break
    chest = chin + max(2, (feet - chin) // 4)
    m = {"chin": chin, "crotch": crotch, "feet": feet, "cx": cx, "chest": chest,
         "chest_w": (lambda s: s[1] - s[0] + 1)(span(body[chest]))}
    if facing in "EW":
        # side views: depth and middle at the waist, under hair that hangs down the back and clear of the arms
        waist = chin + (feet - chin) * 45 // 100
        w = span(body[waist])
        m.update(waist=waist, cx=(w[0] + w[1]) / 2)
        if leave_out is None:
            m["chest_w"] = w[1] - w[0] + 1
    return m


def warp_index(goa, race):
    """Where each pixel of a race-shaped frame comes from in GOA's (warp below): source rows, columns, inside, kx, ky."""
    ky = (race["feet"] - race["chin"]) / (goa["feet"] - goa["chin"])
    kx = min(1.45, max(0.6, race["chest_w"] / goa["chest_w"]))
    ys, xs = np.mgrid[0:64, 0:64]
    sy = np.floor(goa["chin"] + (ys - race["chin"]) / ky + 0.5).astype(int)
    sx = np.floor(goa["cx"] + (xs - race["cx"]) / kx + 0.5).astype(int)
    return sy, sx, (sy >= 0) & (sy < 64) & (sx >= 0) & (sx < 64), kx, ky


def warp_point(p, goa, race, kx, ky):
    """A point of GOA's frame in the race-shaped frame."""
    return np.array([race["cx"] + (p[0] - goa["cx"] - 0.5) * kx + 0.5, race["chin"] + (p[1] - goa["chin"] - 0.5) * ky + 0.5])


def hair_mask(a, head, skin):
    """Hair below the head: the head's own (non-skin) colours continuing below it, joined to it, holes filled."""
    al = a[..., 3] > 0
    key = lambda y, x: tuple(int(v) for v in a[y, x, :3])
    dark = al & (a[..., :3].astype(int).sum(-1) < 120)
    head_cols = {key(y, x) for y, x in zip(*np.nonzero(head & ~dark))} - set(skin)
    hairish = al & ~head & ~dark & np.array([[key(y, x) in head_cols for x in range(64)] for y in range(64)])
    hair = np.zeros_like(al)
    for c in components(hairish):
        if (c & grow(head)).any() and c.sum() >= 6:
            hair |= c
    for _ in range(3):
        p = np.pad(hair | head, 1)
        n = p[:-2, 1:-1].astype(int) + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]
        hair |= al & ~head & ~dark & (n >= 3)
    return hair


def warp(a, goa, race):
    """GOA's frame reshaped to a race's build: chin to feet stretched to the race's, widths scaled by the chests' ratio
    about the body's middle. Whole pixels are moved (nearest), none blended."""
    ky = (race["feet"] - race["chin"]) / (goa["feet"] - goa["chin"])
    kx = min(1.45, max(0.6, race["chest_w"] / goa["chest_w"]))
    ys, xs = np.mgrid[0:64, 0:64]
    sy = np.floor(goa["chin"] + (ys - race["chin"]) / ky + 0.5).astype(int)
    sx = np.floor(goa["cx"] + (xs - race["cx"]) / kx + 0.5).astype(int)
    ok = (sy >= 0) & (sy < 64) & (sx >= 0) & (sx < 64)
    out = np.zeros_like(a)
    out[ok] = a[sy[ok], sx[ok]]
    return out, kx, ky


def close_outline(a, dark=60):
    """Where shrinking dropped the outline, a coloured pixel touches the empty background: give it its dark edge back."""
    al = a[..., 3] > 0
    lit = al & (a[..., :3].astype(int).sum(-1) > dark * 3)
    pa = np.pad(lit, 1)
    h, w = al.shape
    ring = np.zeros_like(al)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ring |= pa[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
    ring &= ~al
    out = a.copy()
    out[ring] = (24, 22, 22, 255)
    return out


def components(mask):
    lab, n = np.zeros(mask.shape, int), 0
    h, w = mask.shape
    for y, x in zip(*np.nonzero(mask)):
        if lab[y, x]:
            continue
        n += 1
        lab[y, x], stack = n, [(y, x)]
        while stack:
            cy, cx = stack.pop()
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = n
                    stack.append((ny, nx))
    return [lab == i for i in range(1, n + 1)]


def grow(mask, n=1):
    for _ in range(n):
        p = np.pad(mask, 1)
        mask = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return mask


def extras(a, head, goa_body, skin, waist, labels, facing, cx):
    """What a race's standing frame has beyond its head and GOA's reshaped body: hair hanging below the head (the head's
    own hair colours, joined to it, with their outline) and, below the waist, a tail: solid, outside GOA's body, growing
    from the torso zone (not the arms: hands that hang wider than GOA's are not tails), behind the body from the side.
    Returns (hair, tail) masks."""
    al = a[..., 3] > 0
    key = lambda y, x: tuple(int(v) for v in a[y, x, :3])
    dark = al & (a[..., :3].astype(int).sum(-1) < 120)
    head_cols = {key(y, x) for y, x in zip(*np.nonzero(head & ~dark))} - set(skin)
    hairish = al & ~head & ~dark & np.array([[key(y, x) in head_cols for x in range(64)] for y in range(64)])
    hair = np.zeros_like(al)
    for c in components(hairish):
        if (c & grow(head)).any() and c.sum() >= 6:
            hair |= c
    # shading colours found only in the long hair leave holes: a pixel mostly surrounded by hair is hair
    for _ in range(3):
        p = np.pad(hair | head, 1)
        n = p[:-2, 1:-1].astype(int) + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]
        hair |= al & ~head & ~dark & (n >= 3)
    outside = al & ~head & ~hair & ~grow(goa_body)
    tail = np.zeros_like(al)
    for c in components(outside):
        inner = c & ~grow(~c)
        ys, xs = np.nonzero(c)
        # from the side, anything below the waist well behind the back is a tail, whatever a borrowed part map calls
        # it (a werewolf's tail sits where the male's forearm is) and however thin (a devil's tail)
        far_behind = facing in "EW" and ys.mean() > waist and (cx - xs.mean() if facing == "E" else xs.mean() - cx) > 8
        if far_behind and c.sum() >= 6:
            tail |= c
            continue
        if c.sum() >= 12 and inner.sum() >= 3:
            torso, arms = (c & (labels == 1)).sum(), (c & (labels >= 2) & (labels <= 5)).sum()
            behind = facing in "SN" or (xs.mean() < cx if facing == "E" else xs.mean() > cx)
            if ys.mean() > waist:
                if torso >= 4 and arms < 0.3 * c.sum() and behind:
                    tail |= c
            elif (c & grow(head | hair, 2)).any():
                hair |= c
    if facing == "N":
        # from behind the tail hangs over the shorts and legs, inside GOA's outline: the torso zone's coloured pixels
        # from the shorts down (not the shorts' own dull darks), in one piece that reaches past where the legs begin
        legs = np.flatnonzero(((labels >= 6) & (labels <= 9) & al).any(1))
        rgb = a[..., :3].astype(float) / 255
        mx, mn = rgb.max(-1), rgb.min(-1)
        dull = (mx - mn) / np.maximum(mx, 1e-6) < 0.3
        torso_rows = np.flatnonzero((labels == 1).any(1))
        shorts_top = next((y for y in torso_rows if ((labels[y] == 1) & dull[y] & ~dark[y] & al[y]).sum() >= 4), 64)
        if len(legs):
            low = al & (labels == 1) & ~dark & ~dull & (np.arange(64)[:, None] >= shorts_top)
            for c in sorted(components(low), key=lambda c: -c.sum()):
                if c.sum() >= 10 and np.nonzero(c)[0].max() > legs[0]:
                    tail |= c
                    break
    hair |= grow(hair) & dark & ~head
    tail |= grow(tail) & al & ~head & ~hair & (~goa_body if facing != "N" else True)
    return hair, tail
