"""Non-humanoid creatures in the "real" art style: dragons and spiders. Runs inside Blender.

Each keeps its original sprite's identity: the dragon's colour variants (sand, ice,
blue, black, green, zombie, red, dark, gold, navy, silver...) with an orange belly and
folded bat wings; the grey spider castes with red or blue back markings and the small
black widow with its red hourglass. Built from lofts, spheres and tubes in code (see
races_real.py); no downloaded, traced or extracted assets.

The rig is a root pivot (turned for each facing), plus empty limb/stump tables so the
sprite renderer's state code can run unchanged.
"""

import math

import bpy

import blender_models as bm
import races_real as rr

DRAGON_COLOURS = {   # body, membrane; the belly is always the original's orange
    "red": ("#8e1e14", "#5a1210"), "green": ("#1e7a2e", "#124a1c"), "black": ("#2a2a2e", "#18181c"),
    "blue": ("#2a5ec4", "#1a3a7a"), "gold": ("#d8b020", "#8a6a10"), "ice": ("#d8e8f0", "#9ab8c8"),
    "sand": ("#d8a640", "#8a6620"), "silver": ("#b8bcc8", "#6e7280"), "zombie": ("#5ac46a", "#2a6a34"),
    "navy": ("#2a3e6e", "#16223e"), "dark": ("#1a1010", "#0c0808"),
}
SPIDERS = {
    "Warrior": dict(size=1.0, body="#56565c", legs="#3a3a40", mark="#c8201a", mark_shape="bar"),
    "Queen": dict(size=1.15, body="#5e5e66", legs="#3e3e46", mark="#2a4ec8", mark_shape="bar"),
    "Widow": dict(size=0.62, body="#121216", legs="#0c0c10", mark="#d01818", mark_shape="hourglass"),
}


def _key(name, hex_body):
    k = "r_c_" + name
    bm.PALETTE[k] = (hex_body, hex_body, hex_body, None)
    return k


def build_dragon(rig_col, body_col, variant="red"):
    M, C = rr.soft_material, body_col
    body_hex, wing_hex = DRAGON_COLOURS[variant]
    hide = M(_key("dragon_" + variant, body_hex), 0.55, metal=0.1)
    wing = M(_key("dragon_wing_" + variant, wing_hex), 0.7)
    belly = M(_key("dragon_belly", "#e0802a"), 0.6)
    horn = M("r_bone", 0.45)
    root = bm.pivot("root", None, (0, 0, 0), rig_col)
    body = bm.pivot("hips", root, (0, 0, 0), rig_col)

    # torso: chest high at the front, haunches behind (loft runs backwards along +Y)
    rr.loft(C, "torso", body, [(0.0, 0.13, 0.12), (0.12, 0.15, 0.13, 0, 0.0), (0.26, 0.15, 0.12, 0, -0.01), (0.38, 0.11, 0.09, 0, 0.01)],
            hide, loc=(0, -0.16, 0.36), rot=(math.radians(-96), 0, 0))
    rr.ball(C, "torso_belly", body, (0, -0.08, 0.27), (0.1, 0.18, 0.07), belly)
    rr.ball(C, "torso_chest", body, (0, -0.15, 0.33), (0.1, 0.07, 0.1), belly)
    for i in range(5):   # spines down the back
        rr.spike(C, f"torso_spine{i}", body, (0, -0.1 + i * 0.07, 0.47 - i * 0.012), (0, -0.08 + i * 0.07, 0.53 - i * 0.012), 0.016, horn)
    # neck and head, raised and looking forward
    rr.tube(C, "neck", body, [(0, -0.16, 0.42), (0, -0.22, 0.56), (0, -0.25, 0.66)], [0.075, 0.06, 0.05], hide, seg=10)
    rr.ball(C, "neck_belly", body, (0, -0.21, 0.5), (0.05, 0.04, 0.09), belly)
    head = bm.pivot("head", body, (0, -0.27, 0.69), rig_col)
    rr.ball(C, "skull", head, (0, 0.0, 0.0), (0.055, 0.06, 0.045), hide)
    rr.loft(C, "snout", head, [(0.0, 0.042, 0.032), (0.07, 0.034, 0.024), (0.11, 0.024, 0.018)], hide,
            loc=(0, -0.03, -0.006), rot=(math.radians(100), 0, 0))
    rr.loft(C, "jaw", head, [(0.0, 0.036, 0.016), (0.1, 0.02, 0.01)], belly, loc=(0, -0.02, -0.03), rot=(math.radians(96), 0, 0), seg=10)
    glow = M("r_dark", 0.3, glow=rr.GLOW["red"] if variant != "ice" else "#40c8ff")
    eyes = [rr.ball(C, f"eye{s}", head, (0.034 * s, -0.04, 0.016), (0.009, 0.006, 0.006), glow, subdiv=0) for s in (-1, 1)]
    for s in (-1, 1):
        rr.spike(C, f"horn{s}", head, (0.03 * s, 0.02, 0.03), (0.06 * s, 0.12, 0.08), 0.016, horn, bend=(0.01 * s, 0, 0.02))
        rr.spike(C, f"horn_small{s}", head, (0.04 * s, 0.0, 0.0), (0.075 * s, 0.05, 0.01), 0.008, horn)
    # legs: front legs straight, hind legs folded under the haunches
    for s in (-1, 1):
        rr.tube(C, f"upper_front{s}", body, [(0.12 * s, -0.14, 0.33), (0.15 * s, -0.17, 0.18), (0.14 * s, -0.2, 0.03)],
                [0.045, 0.035, 0.03], hide)
        rr.tube(C, f"thigh_hind{s}", body, [(0.13 * s, 0.13, 0.33), (0.18 * s, 0.03, 0.2), (0.16 * s, 0.1, 0.04)],
                [0.07, 0.05, 0.034], hide)
        for fx, fy in ((0.14 * s, -0.2), (0.16 * s, 0.1)):
            rr.ball(C, f"foot{s}{fy}", body, (fx, fy - 0.02, 0.02), (0.035, 0.05, 0.022), hide)
            for t in (-1, 0, 1):
                rr.spike(C, f"foot_claw{s}{fy}{t}", body, (fx + 0.018 * t, fy - 0.06, 0.015), (fx + 0.026 * t, fy - 0.09, 0.004), 0.008, horn)
    # tail sweeping round to the side
    rr.tube(C, "tail", body, [(0, 0.2, 0.32), (0.03, 0.36, 0.2), (0.14, 0.46, 0.08), (0.3, 0.44, 0.04), (0.42, 0.36, 0.03)],
            [0.075, 0.055, 0.04, 0.022, 0.006], hide, seg=10)
    rr.spike(C, "tail_tip", body, (0.4, 0.37, 0.03), (0.47, 0.31, 0.03), 0.03, horn)
    # wings folded up over the back, like the original's cloak of wings
    for s in (-1, 1):
        A, E, T = (0.07 * s, -0.08, 0.45), (0.2 * s, -0.02, 0.66), (0.26 * s, 0.04, 0.82)
        F = [(0.34 * s, 0.18, 0.42), (0.27 * s, 0.26, 0.34), (0.15 * s, 0.22, 0.4)]
        rr.tube(C, f"wing_arm{s}", body, [A, E, T], [0.026, 0.02, 0.012], hide)
        rr.spike(C, f"wing_claw{s}", body, T, (0.27 * s, 0.02, 0.87), 0.012, horn)
        for i, f in enumerate(F):
            rr.tube(C, f"wing_finger{i}{s}", body, [T, f], [0.01, 0.004], hide, seg=6)
        rr.membrane(C, f"wing_skin{s}", body, [A, E, T] + F, wing)
    return {"root": root, "hips": body, "head": head, "eyes": eyes, "stump": {}, "limb_parts": {}, "tail": [], "leg_len": 0.3}


def build_spider(rig_col, body_col, caste="Warrior"):
    M, C = rr.soft_material, body_col
    p = SPIDERS[caste]
    z = p["size"]
    body_m = M(_key("spider_" + caste, p["body"]), 0.45 if caste == "Widow" else 0.7)
    leg_m = M(_key("spider_leg_" + caste, p["legs"]), 0.6)
    mark = M(_key("spider_mark_" + caste, p["mark"]), 0.5)
    root = bm.pivot("root", None, (0, 0, 0), rig_col)
    body = bm.pivot("hips", root, (0, 0, 0), rig_col)
    rr.ball(C, "torso_head", body, (0, -0.07 * z, 0.15 * z), (0.085 * z, 0.095 * z, 0.065 * z), body_m)
    rr.ball(C, "torso_abdomen", body, (0, 0.13 * z, 0.19 * z), (0.135 * z, 0.165 * z, 0.115 * z), body_m)
    if p["mark_shape"] == "bar":
        rr.ball(C, "torso_mark", body, (0, 0.1 * z, 0.3 * z), (0.065 * z, 0.03 * z, 0.012 * z), mark)
        for s in (-1, 1):
            rr.ball(C, f"torso_dot{s}", body, (0.05 * s * z, 0.18 * z, 0.28 * z), (0.016 * z, 0.016 * z, 0.01 * z), mark)
    else:   # hourglass
        for dy in (-0.03, 0.03):
            rr.ball(C, f"torso_mark{dy}", body, (0, (0.13 + dy) * z, 0.302 * z), (0.03 * z, 0.026 * z, 0.01 * z), mark)
    glow = M("r_dark", 0.3, glow=rr.GLOW["red"])
    eyes = []
    for i, (ex, ey) in enumerate(((-0.03, -0.14), (0.03, -0.14), (-0.015, -0.155), (0.015, -0.155))):
        eyes.append(rr.ball(C, f"eye{i}", body, (ex * z, ey * z, 0.19 * z), (0.011 * z, 0.008 * z, 0.009 * z), glow, subdiv=0))
    for s in (-1, 1):
        rr.spike(C, f"fang{s}", body, (0.022 * s * z, -0.15 * z, 0.13 * z), (0.016 * s * z, -0.18 * z, 0.06 * z), 0.012 * z, leg_m)
    for i, phi in enumerate((52, 20, -16, -48)):
        a = math.radians(phi)
        for s in (-1, 1):
            hip = (0.06 * s * z, (-0.075 - 0.015 * (1.5 - i)) * z, 0.15 * z)
            dx, dy = s * math.cos(a), -math.sin(a)
            knee = (hip[0] + dx * 0.16 * z, hip[1] + dy * 0.16 * z, 0.3 * z)
            foot = (hip[0] + dx * 0.36 * z, hip[1] + dy * 0.36 * z, 0.0)
            rr.tube(C, f"leg{i}{s}", body, [hip, knee, foot], [0.02 * z, 0.016 * z, 0.006 * z], leg_m)
    return {"root": root, "hips": body, "eyes": eyes, "stump": {}, "limb_parts": {}, "tail": [], "leg_len": 0.15}
