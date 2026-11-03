"""A frame built from containers (draw.py): GOA's pose, the race's own parts.

The race's torso container is its own torso outline (where its arm hung over it, filled in), carried as GOA's body
moves, its materials (skin, shorts or top, markings) read off its sprite. Arms and legs are drawn fresh along the
frame's skeleton: shoulders and hips where the race's own are, each bone GOA's direction snapped to 8 and the race's
own length (shortened as GOA's is), the race's own thickness. The head, hair and tail are the race's own drawing.
"""
import colorsys

import numpy as np

from draw import capsule, darker, ellipse, lum, pour, ramp, snap

FAR = {"E": "L", "W": "R"}                       # the far side from the side; front and back have none
ORDER = {"E": ["L_arm", "L_leg", "torso", "R_leg", "R_arm"], "W": ["R_arm", "R_leg", "torso", "L_leg", "L_arm"],
         "S": ["L_leg", "R_leg", "torso", "L_arm", "R_arm"], "N": ["L_leg", "R_leg", "torso", "L_arm", "R_arm"]}
TOE = {"E": (1.0, 0.15), "W": (-1.0, 0.15), "S": (0.0, 1.0), "N": (0.0, 1.0)}


def dull_dark(a):
    rgb = a[..., :3].astype(float) / 255
    mx, mn = rgb.max(-1), rgb.min(-1)
    return ((mx - mn) / np.maximum(mx, 1e-6) < 0.3) & (mx < 0.4) & (mx > 0.02)


def race_kit(ra, lab, head, rj, skins, shorts_c, facing):
    """What a race brings for one facing: its torso container and materials, tones, limb thickness."""
    al = ra[..., 3] > 0
    torso = al & (lab == 1) & ~head
    full = torso.copy()
    for y in np.flatnonzero(torso.any(1)):            # where its arm hung over the body, the body goes on
        xs = np.flatnonzero(torso[y])
        full[y, xs.min():xs.max() + 1] |= al[y, xs.min():xs.max() + 1] & ~head[y, xs.min():xs.max() + 1]
    cloth = full & dull_dark(ra)
    skin_set = set(skins)
    marks = np.zeros_like(full)
    hsv = lambda c: colorsys.rgb_to_hsv(*(q / 255 for q in c))
    hues = [hsv(c)[0] for c in skin_set] or [0]
    hue = float(np.median(hues))
    for y, x in zip(*np.nonzero(full & ~cloth)):
        c = tuple(int(v) for v in ra[y, x, :3])
        h, s, v = hsv(c)
        if c not in skin_set and s > 0.35 and v > 0.45 and min(abs(h - hue), 1 - abs(h - hue)) > 0.08:
            marks[y, x] = True                      # an Ashen's glowing cracks, a Marked's red marks
    arms = al & np.isin(lab, (2, 3, 4, 5))
    legs = al & np.isin(lab, (6, 7, 8, 9))
    arm_len = max(np.linalg.norm(rj["RH"] - rj["RS"]), 1.0)
    arm_w = arms.sum() / arm_len / (2 if facing in "SN" else 1)
    ys = [y for y in range(int(rj["RK"][1]), int(rj["RA"][1]) + 1) if legs[y].any()]
    shin_w = (np.median([legs[y].sum() for y in ys]) if ys else 6) / (2 if facing in "SN" else 1.4)
    skin_r = ramp(skins)
    cloth_r = ramp(shorts_c) if shorts_c else darker(skin_r, 0.35)
    # the race's drawn line work inside its body (muscles, belly, the top's seams): a pixel clearly darker than
    # those around it; poured one band darker, so the form stays the race's
    lm = np.array([[lum(ra[y, x]) for x in range(64)] for y in range(64)])
    pad = np.pad(lm, 1, mode="edge")
    around = (pad[:-2, 1:-1] + pad[2:, 1:-1] + pad[1:-1, :-2] + pad[1:-1, 2:]) / 4
    lines = full & (lm < around - 22) & ~cloth
    return {"torso": full, "cloth": cloth, "marks": marks, "lines": lines, "skin": skin_r, "cloth_r": cloth_r,
            "arm_r": float(np.clip(arm_w / 2, 1.6, 5.0)), "shin_r": float(np.clip(shin_w / 2, 1.6, 5.0))}


def frame(kit, ra, rj, gj0, gj, facing, torso_off):
    """One frame (64 x 64 RGBA) from the race's kit and the frame's skeleton gj (GOA's, race-sized; gj0 its standing)."""
    out = np.zeros((64, 64, 4), np.uint8)
    far = FAR.get(facing)
    toe = np.array(TOE[facing])

    def bone(side, a, b, start):
        """The race's own bone a->b, turned to GOA's snapped direction and shortened as GOA's is in this frame."""
        g, g0 = gj[side + b] - gj[side + a], gj0[side + b] - gj0[side + a]
        ratio = np.linalg.norm(g) / max(np.linalg.norm(g0), 1e-6)
        L = np.linalg.norm(rj[side + b] - rj[side + a]) * min(1.15, ratio)
        d = snap(g)
        n = np.linalg.norm(d)
        return start + (d / n * L if n > 1e-6 else np.zeros(2))

    for part in ORDER[facing]:
        side, what = part.split("_") if part != "torso" else ("", "torso")
        if what == "torso":
            dx, dy = int(round(torso_off[0])), int(round(torso_off[1]))
            shift = lambda m: np.roll(np.roll(m, dy, 0), dx, 1)
            m = shift(kit["torso"])
            pour(out, m, kit["skin"], [(shift(kit["cloth"]), kit["cloth_r"])])
            ln = shift(kit["lines"]) & m
            out[ln, :3] = np.minimum(out[ln, :3], np.array(kit["skin"][0], np.uint8))
            mk = shift(kit["marks"])
            src = np.roll(np.roll(ra, dy, 0), dx, 1)
            out[mk & m] = src[mk & m]
            continue
        tones = darker(kit["skin"]) if side == far else kit["skin"]
        cloth = darker(kit["cloth_r"]) if side == far else kit["cloth_r"]
        if what == "arm":
            s = rj[side + "S"] + torso_off
            e = bone(side, "S", "E", s)
            h = bone(side, "E", "H", e)
            r = kit["arm_r"]
            m = capsule(s, e, r + 0.4, r) | capsule(e, h, r, r - 0.2) | ellipse(h, r + 0.7, r + 0.7)
            pour(out, m, tones)
        else:
            hp = rj[side + "Hp"] + torso_off
            k = bone(side, "Hp", "K", hp)
            a = bone(side, "K", "A", k)
            r = kit["shin_r"]
            thigh = capsule(hp, k, r + 1.2, r + 0.6)
            shin = capsule(k, a, r + 0.2, r - 0.2)
            foot = ellipse(a + toe * (r * 0.8), r + 0.9 if facing in "EW" else r + 0.4, r * 0.7 + 0.4, toe)
            m = thigh | shin | foot
            pour(out, m, tones, [(thigh & ~shin, cloth)])
    return out
