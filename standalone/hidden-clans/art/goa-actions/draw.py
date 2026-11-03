"""Procedural pixel bodies (owner 11-01: "you cannot copy and paste it needs to be like water fluid procedural into the
container we draw"; "if we did 8 directional sprite of each body part then we can build anything").

A body part is a container: a shape drawn as a pixel mask. Limbs are tapered capsules at the race's own thickness,
laid along a skeleton with every bone snapped to one of 8 directions (45 degree steps, where pixel limbs read
cleanest), hands round, feet pointing the way the body faces; the torso's container is the race's own torso outline.
Colour then flows into each container: the race's own skin, shorts or top tones, in flat light bands from the
top-left that follow the container's shape, with a black outline round it. Nothing is copied from GOA's pixels; GOA
only gives the pose.
"""
import numpy as np

LIGHT = np.array([-0.6, -0.75])        # towards the light: top-left


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def ramp(colours, n=4):
    """n tones from a race's colours, dark to light (brightness quantiles)."""
    cs = sorted({tuple(int(v) for v in c[:3]) for c in colours}, key=lum)
    if not cs:
        return [(128, 128, 128)] * n
    qs = [0.12, 0.38, 0.62, 0.88] if n == 4 else np.linspace(0.15, 0.85, n)
    return [cs[min(len(cs) - 1, int(q * len(cs)))] for q in qs]


def darker(rmp, k=0.78):
    return [tuple(int(v * k) for v in c) for c in rmp]


def snap(v):
    """A bone's direction snapped to the nearest of 8 (45 degree steps), its length kept."""
    L = float(np.hypot(*v))
    if L < 1e-6:
        return np.zeros(2)
    a = np.round(np.arctan2(v[1], v[0]) / (np.pi / 4)) * (np.pi / 4)
    return np.array([np.cos(a), np.sin(a)]) * L


_YS, _XS = np.mgrid[0:64, 0:64]
_P = np.stack([_XS + 0.5, _YS + 0.5], -1)


def capsule(a, b, r0, r1):
    """A tapered capsule from a (radius r0) to b (radius r1)."""
    ab = b - a
    L2 = max(float(ab @ ab), 1e-6)
    t = np.clip(((_P - a) @ ab) / L2, 0, 1)
    d = np.linalg.norm(_P - (a + t[..., None] * ab), axis=-1)
    return d <= r0 + (r1 - r0) * t


def ellipse(c, rx, ry, along=(1.0, 0.0)):
    u = np.array(along, float)
    u = u / max(np.hypot(*u), 1e-6)
    n = np.array([-u[1], u[0]])
    q = _P - c
    return ((q @ u) / rx) ** 2 + ((q @ n) / ry) ** 2 <= 1.0


def depth(mask, cap=4):
    """How deep each pixel sits in its container: 1 on the edge, more inside."""
    d = np.zeros(mask.shape, int)
    m = mask.copy()
    for k in range(1, cap + 1):
        p = np.pad(m, 1)
        inner = m & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
        d[m & ~inner] = k
        m = inner
    d[m] = cap
    return d


def _blur(m, r=2):
    p = np.pad(m.astype(np.float32), r)
    c = np.pad(p.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    n = 2 * r + 1
    return (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]) / (n * n)


def light(mask):
    """The light on each pixel of a container (0 dark .. 1 lit): its outward slope towards the top-left light,
    and a little more the deeper inside (rounded forms)."""
    soft = _blur(mask, 2)
    gy, gx = np.gradient(soft)
    facing = np.clip((gx * -LIGHT[0] + gy * -LIGHT[1]) * 7.0, -1, 1)     # inward slope at the lit (top-left) edge
    return 0.5 + 0.4 * facing + 0.1 * (np.minimum(depth(mask), 4) - 1) / 3


def pour(canvas, mask, tones, material=None, outline=(0, 0, 0)):
    """Colour flowing into a container: each pixel the tone its light calls for (bands, no blending), from tones
    (one ramp) or, where material marks it, from that material's ramp; a black outline round the container."""
    if not mask.any():
        return
    v = light(mask)
    band = np.digitize(v, [0.33, 0.55, 0.78])
    out = np.zeros(mask.shape + (3,), np.uint8)
    t = np.array(tones, np.uint8)
    out[:] = t[band]
    if material is not None:
        for m, tn in material:
            tt = np.array(tn, np.uint8)
            out[m] = tt[band[m]]
    canvas[mask, :3] = out[mask]
    canvas[mask, 3] = 255
    edge = mask & (depth(mask) == 1)
    canvas[edge, :3] = outline
