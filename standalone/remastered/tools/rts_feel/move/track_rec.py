#!/usr/bin/env python3
"""Track units in a screen recording of the game, frame by frame, by their yellow selection rings.

    python3 tools/rts_feel/move/track_rec.py REC.mov --from 14 --to 20 [--out DIR]

Decodes every frame (no resampling, real timestamps from ffmpeg's showinfo) at half size, finds the selection
rings by colour, follows each ring from frame to frame, and takes the camera's own movement out by matching the
grass between frames. Writes DIR/<name>-<from>-<to>.json (per-frame ring centres in screen px, camera shift)
and prints, per unit track: pauses > 150 ms while the unit is otherwise walking, snaps (a jump bigger than 0.3
tile in one frame), speed and its spread, and the times of each, so the moments can be looked at frame by frame.
"""
import argparse, json, os, re, subprocess, sys
import numpy as np

FF = None
try:
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    sys.exit("needs imageio_ffmpeg")


def probe_size(path):
    out = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", out)
    return int(m.group(1)), int(m.group(2))


def frames(path, t0, t1, scale):
    W, H = probe_size(path)
    w, h = W // scale, H // scale
    cmd = [FF, "-hide_banner", "-loglevel", "info", "-ss", str(t0), "-to", str(t1), "-i", path,
           "-vf", f"scale={w}:{h},showinfo", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    import threading, queue
    q = queue.Queue()

    def rd():
        for line in p.stderr:
            m = re.search(rb"pts_time:\s*([0-9.]+)", line)
            if m:
                q.put(float(m.group(1)))
        q.put(None)
    threading.Thread(target=rd, daemon=True).start()
    n = w * h * 3
    i = 0
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        t = q.get()
        if t is None:
            t = i / 60.0
        yield t0 + t, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        i += 1
    p.wait()


def ring_mask(f):
    r, g, b = f[..., 0].astype(np.int16), f[..., 1].astype(np.int16), f[..., 2].astype(np.int16)
    # the selection ring: saturated gold/yellow (r high, g fairly high, b low)
    return (r > 185) & (g > 130) & (g < 235) & (b < 90) & (r - b > 120)


def ring_kernel(a, shape):
    """An ellipse outline (the selection ring seen from the camera), semi-axes a and 0.72a, as an FFT-ready kernel."""
    b = a * 0.72
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    yy = np.where(yy > h // 2, yy - h, yy).astype(float)
    xx = np.where(xx > w // 2, xx - w, xx).astype(float)
    r = np.sqrt((xx / a) ** 2 + (yy / b) ** 2)
    k = (np.abs(r - 1.0) < 1.6 / a).astype(float)
    return np.fft.rfft2(k / k.sum())


_kcache = {}


def ring_score(mask, a):
    key = (a, mask.shape)
    if key not in _kcache:
        _kcache[key] = ring_kernel(a, mask.shape)
    return np.fft.irfft2(np.fft.rfft2(mask.astype(float)) * _kcache[key], s=mask.shape)


def rings(mask, a, thr=0.2):
    """Centres of selection rings: peaks of the ring-outline match, at least a ring's width apart."""
    sc = ring_score(mask, a)
    out = []
    flat = np.argsort(sc, axis=None)[::-1]
    h, w = sc.shape
    for idx in flat[:4000]:
        v = sc.flat[idx]
        if v < thr:
            break
        y, x = divmod(int(idx), w)
        if any((x - ox) ** 2 / (1.5 * a) ** 2 + (y - oy) ** 2 / (1.1 * a) ** 2 < 1 for ox, oy, _ in out):
            continue
        # sub-pixel: centroid of the score around the peak
        y0, y1, x0, x1 = max(0, y - 2), min(h, y + 3), max(0, x - 2), min(w, x + 3)
        win = np.clip(sc[y0:y1, x0:x1] - thr * 0.8, 0, None)
        gy, gx = np.mgrid[y0:y1, x0:x1]
        sw = win.sum() or 1
        out.append(((gx * win).sum() / sw, (gy * win).sum() / sw, float(v)))
    return out


def best_size(mask, sizes):
    best, bs = sizes[0], -1
    for a in sizes:
        r = rings(mask, a)
        q = sum(v for _, _, v in r[:8])
        if q > bs:
            best, bs = a, q
    return best


def cam_shift(prev, cur, box):
    """Camera movement between two frames from the ground (phase correlation on a grey crop)."""
    x0, y0, x1, y1 = box
    a = prev[y0:y1, x0:x1].mean(axis=2)
    b = cur[y0:y1, x0:x1].mean(axis=2)
    a = a - a.mean()
    b = b - b.mean()
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    A = np.fft.fft2(a * win)
    B = np.fft.fft2(b * win)
    R = A * np.conj(B)
    R /= np.abs(R) + 1e-9
    c = np.fft.ifft2(R).real
    py, px = np.unravel_index(np.argmax(c), c.shape)
    if py > c.shape[0] // 2:
        py -= c.shape[0]
    if px > c.shape[1] // 2:
        px -= c.shape[1]
    return -px, -py, float(c.max())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rec")
    ap.add_argument("--from", dest="t0", type=float, default=0)
    ap.add_argument("--to", dest="t1", type=float, default=1e9)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--tile", type=float, default=0, help="tile size in screen px (full size); default: measured")
    ap.add_argument("--out", default="reports/polish-2026-10-22/rts-feel/movement/recordings")
    a = ap.parse_args()
    W, H = probe_size(a.rec)
    s = a.scale
    # the play area: leave out the HUD panels (left band/goal cards, right minimap/company, top bars, bottom bar)
    play = (int(0.23 * W / s), int(0.17 * H / s), int(0.83 * W / s), int(0.80 * H / s))
    gbox = (int(0.30 * W / s), int(0.20 * H / s), int(0.75 * W / s), int(0.62 * H / s))
    rows = []
    prev = None
    camx = camy = 0.0
    size = None
    x0, y0, x1, y1 = play
    for i, (t, f) in enumerate(frames(a.rec, a.t0, a.t1, s)):
        if prev is not None:
            dx, dy, q = cam_shift(prev, f, gbox)
            if q > 0.08 and (abs(dx) + abs(dy)) < 60:
                camx += dx
                camy += dy
        prev = f
        m = ring_mask(f)
        mm = np.zeros_like(m)
        mm[y0:y1, x0:x1] = m[y0:y1, x0:x1]
        if size is None or i % 60 == 0:
            size = best_size(mm, [x / s for x in (12, 14, 16, 18, 20, 23, 26)])
        bl = [(bx * s, by * s, v) for bx, by, v in rings(mm, size)]
        rows.append({"t": round(t, 4), "cam": [camx * s, camy * s], "a": size * s,
                     "rings": [[round(b[0], 1), round(b[1], 1), round(b[2], 2)] for b in bl]})
    name = os.path.basename(a.rec)
    m = re.search(r"at (\d+)\.(\d+)\.(\d+)", name)
    tag = f"{m.group(1)}.{m.group(2)}" if m else "rec"
    os.makedirs(a.out, exist_ok=True)
    dst = os.path.join(a.out, f"track-{tag}-{a.t0:g}-{a.t1:g}.json")
    json.dump({"rec": name, "size": [W, H], "rows": rows}, open(dst, "w"))
    print("wrote", dst, len(rows), "frames")
    analyse(rows, a.tile)


def link(rows, maxd=30.0):
    """Follow rings from frame to frame (in world px: screen minus camera shift); returns tracks."""
    tracks = []   # each: list of (t, wx, wy, sx, sy)
    live = []
    for r in rows:
        cx, cy = r["cam"]
        pts = [(x + cx, y + cy, x, y) for x, y, v in r["rings"]]
        used = set()
        nl = []
        for tr in live:
            lt, lx, ly = tr[-1][0], tr[-1][1], tr[-1][2]
            if r["t"] - lt > 0.5:
                continue
            best, bd = None, maxd
            for i, p in enumerate(pts):
                if i in used:
                    continue
                d = ((p[0] - lx) ** 2 + (p[1] - ly) ** 2) ** 0.5
                if d < bd:
                    best, bd = i, d
            if best is not None:
                used.add(best)
                p = pts[best]
                tr.append((r["t"], p[0], p[1], p[2], p[3]))
            nl.append(tr)
        for i, p in enumerate(pts):
            if i not in used:
                tr = [(r["t"], p[0], p[1], p[2], p[3])]
                tracks.append(tr)
                nl.append(tr)
        live = nl
    return [t for t in tracks if len(t) > 30]


def analyse(rows, tile):
    tracks = link(rows)
    if not tile:
        # measured: the typical gap between neighbouring rings in a frame (units stand a tile apart in formation)
        gaps = []
        for r in rows[::10]:
            P = [(x, y) for x, y, v in r["rings"]]
            for i, p in enumerate(P):
                d = sorted(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 for j, q in enumerate(P) if j != i)
                if d:
                    gaps.append(d[0])
        tile = float(np.median(gaps)) if gaps else 44.0
    print(f"tile ~ {tile:.1f} px, {len(tracks)} tracks")
    for k, tr in enumerate(tracks):
        a = np.array(tr)
        t, x, y = a[:, 0], a[:, 1], a[:, 2]
        # smooth the ring centre a little (the ring is found to about a pixel)
        d = np.hypot(np.diff(x), np.diff(y))
        dt = np.diff(t)
        total = d.sum() / tile
        if total < 1.0:
            continue
        sp = d / np.maximum(dt, 1e-3) / tile   # tiles/s
        moving = sp > 0.4
        # pauses: runs of near-still frames longer than 150 ms between moving stretches
        pauses = []
        i = 0
        n = len(sp)
        first = np.argmax(moving) if moving.any() else n
        last = n - 1 - np.argmax(moving[::-1]) if moving.any() else -1
        i = first
        while i <= last:
            if not moving[i]:
                j = i
                while j <= last and not moving[j]:
                    j += 1
                dur = t[j] - t[i]
                if dur > 0.15:
                    pauses.append((round(t[i], 2), round(dur * 1000)))
                i = j
            else:
                i += 1
        snaps = [(round(t[i], 2), round(d[i] / tile, 2)) for i in range(n) if d[i] / tile > 0.3]
        walk = sp[first:last + 1]
        # speed over 0.25 s windows while walking
        win = []
        j0 = first
        while j0 < last:
            j1 = j0
            while j1 < last and t[j1] - t[j0] < 0.25:
                j1 += 1
            seg = d[j0:j1].sum() / tile / max(1e-3, t[j1] - t[j0])
            win.append(seg)
            j0 = j1
        win = np.array(win) if win else np.array([0])
        print(f"track {k}: {t[0]:.2f}-{t[-1]:.2f}s  {total:.1f} tiles  walking {t[first]:.2f}-{t[min(last + 1, n)]:.2f}s"
              f"  speed {win.mean():.2f} t/s cv {win.std() / max(1e-6, win.mean()):.2f}"
              f"  pauses>150ms {len(pauses)} {pauses[:8]}  snaps {len(snaps)} {snaps[:6]}")


if __name__ == "__main__":
    main()
