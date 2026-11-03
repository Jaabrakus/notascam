"""Seeded gradient noise in numpy. A pure function of world tile position and seed,
so any window of the world (a whole-world thumbnail or one region's tiles) samples
the same field and neighbouring regions meet without seams."""
import numpy as np

M64 = (1 << 64) - 1


def _mix(h):
    h ^= h >> np.uint64(33)
    h *= np.uint64(0xFF51AFD7ED558CCD)
    h ^= h >> np.uint64(33)
    h *= np.uint64(0xC4CEB9FE1A85EC53)
    h ^= h >> np.uint64(33)
    return h


def hash2(ix, iy, seed):
    """uint64 hash of integer lattice points (arrays of int64)."""
    ix, iy = np.broadcast_arrays(ix, iy)
    with np.errstate(over="ignore"):
        h = ix.astype(np.int64).view(np.uint64) * np.uint64(0x9E3779B97F4A7C15)
        h ^= iy.astype(np.int64).view(np.uint64) * np.uint64(0xC2B2AE3D27D4EB4F)
        h ^= np.uint64((seed * 0x165667B19E3779F9) & M64)
        return _mix(h)


def rand01(ix, iy, seed):
    return (hash2(np.asarray(ix), np.asarray(iy), seed) >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def perlin(x, y, seed):
    """2D gradient noise, roughly -0.7..0.7, lattice spacing 1."""
    x0 = np.floor(x)
    y0 = np.floor(y)
    fx = x - x0
    fy = y - y0
    ix = x0.astype(np.int64)
    iy = y0.astype(np.int64)

    def grad(cx, cy, dx, dy):
        a = (hash2(cx, cy, seed) >> np.uint64(40)).astype(np.float64) * (2 * np.pi / (1 << 24))
        return np.cos(a) * dx + np.sin(a) * dy

    n00 = grad(ix, iy, fx, fy)
    n10 = grad(ix + 1, iy, fx - 1, fy)
    n01 = grad(ix, iy + 1, fx, fy - 1)
    n11 = grad(ix + 1, iy + 1, fx - 1, fy - 1)
    u = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
    v = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
    a = n00 + u * (n10 - n00)
    b = n01 + u * (n11 - n01)
    return a + v * (b - a)


def fbm(x, y, seed, wavelength, min_wavelength=None, persistence=0.5, ridged=False):
    """Octaves from `wavelength` down to `min_wavelength` (tiles). Output about -1..1
    (ridged: 0..1, sharp crests). Stopping at a coarser min_wavelength only drops the
    finest octaves, so a thumbnail is the same land with less fine detail."""
    if min_wavelength is None:
        min_wavelength = wavelength / 16
    total = np.zeros(np.broadcast(x, y).shape)
    norm = 1.0 / (1.0 - persistence)  # fixed, so dropping fine octaves keeps the scale
    amp = 1.0
    wl = float(wavelength)
    o = 0
    while wl >= min_wavelength * 0.999:
        n = perlin(x / wl + o * 17.31, y / wl - o * 9.77, seed + o * 101)
        if ridged:
            n = 1.0 - np.abs(n) * 1.6
            n = np.clip(n, 0, 1) ** 2
        else:
            n = n * 1.45
        total += n * amp
        amp *= persistence
        wl /= 2
        o += 1
    return total / norm


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)
