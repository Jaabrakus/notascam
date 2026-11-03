"""Parametric playable races, shared by the 3D exporter (export_units.py) and
the 2D sprite renderer (render_sprites.py). Runs inside Blender.

The orc is hand-built in blender_models.py; every other race is one
parametric humanoid: h = height scale, w = width, head = head size; skin,
top, legs colours; extras: beard, ears, snout, tail, eyes colour, cape.
"""

import math

import blender_models as bm

EXTRA = {
    "human_skin": ("#6e4a3a", "#d9a37a", "#f0c8a0", None),
    "dwarf_skin": ("#6a3e30", "#c98a68", "#e8b08c", None),
    "elf_skin": ("#16183a", "#2e3478", "#5260b0", None),  # night elf: dark blue, like Night Elf.dmi
    "goblin_skin": ("#3c4a1c", "#8aa83a", "#b8d060", None),
    "kobold_skin": ("#3e3410", "#7c6a1e", "#a8943a", None),  # olive, like Kobold.dmi
    "lizard_skin": ("#1e3a2a", "#3f8a5a", "#76b878", None),
    "frog_skin": ("#2a4a1e", "#5f9a34", "#9ccc52", None),
    "bone_white": ("#7a7466", "#d8d2c0", "#f4f0e2", None),
    "zombie_skin": ("#3a4438", "#7d8c6a", "#a4b088", None),
    "vamp_skin": ("#6a6070", "#d8d0dc", "#f2ecf4", None),
    "cloth_blue": ("#1a2a4a", "#2e4e8e", "#5a7cc4", None),
    "cloth_green": ("#1a3a20", "#2e6e38", "#5a9c58", None),
    "cloth_brown": ("#3a2614", "#6e4a26", "#9a7040", None),
    "cloth_black": ("#121216", "#2a2a32", "#4a4a56", None),
    "hair_brown": ("#2a1a10", "#5a3a20", "#86603a", None),
    "hair_ginger": ("#5a2410", "#b45a24", "#e08a44", None),
    "hair_blond": ("#7a6030", "#d8b860", "#f4e098", None),
    "hair_silver": ("#5a5e6e", "#a8acbc", "#e4e6f0", None),
    "cloth_purple": ("#1e1430", "#3e2a5e", "#6a4e8e", None),
}
bm.PALETTE.update(EXTRA)
FLAT = {"eye_red": "#ff2a18", "eye_dark": "#1a1414", "eye_yellow": "#f0d020", "eye_white": "#f4f4f0"}

# Parametric humanoid. h = height scale, w = width, head = head size; skin, top, legs colours;
# extras: beard, pointy ears, snout, tail, eyes colour.
RACES = {
    "Human": dict(h=1.0, w=1.0, head=1.0, skin="human_skin", top="cloth_blue", legs="cloth_brown", hair="hair_brown", ears="round"),
    "Dwarf": dict(h=0.78, w=1.25, head=1.1, skin="dwarf_skin", top="cloth_red", legs="leather", hair="hair_ginger", ears="round", beard=True),
    "Elf": dict(h=1.08, w=0.85, head=0.95, skin="elf_skin", top="cloth_purple", legs="cloth_black", hair="hair_silver", ears="long", eyes="eye_red"),
    "Goblin": dict(h=0.72, w=0.85, head=1.25, skin="goblin_skin", top="leather", legs="cloth_brown", hair=None, ears="long", eyes="eye_yellow"),
    "Kobold": dict(h=0.7, w=0.8, head=1.1, skin="kobold_skin", top="leather", legs="leather", hair=None, ears="horns", snout=True, tail=True, eyes="eye_yellow"),
    "Lizardman": dict(h=1.05, w=1.0, head=1.0, skin="lizard_skin", top="leather", legs="leather", hair=None, ears=None, snout=True, tail=True, eyes="eye_yellow"),
    "Frogman": dict(h=0.85, w=1.1, head=1.2, skin="frog_skin", top="cloth_brown", legs="frog_skin", hair=None, ears=None, eyes="eye_yellow"),
    "Skeleton": dict(h=1.0, w=0.7, head=1.0, skin="bone_white", top="bone_white", legs="bone_white", hair=None, ears=None, eyes="eye_red", thin=True),
    "Zombie": dict(h=0.98, w=0.95, head=1.0, skin="zombie_skin", top="cloth_brown", legs="cloth_black", hair="hair_black", ears="round", eyes="eye_white", hunch=True),
    "Vampire": dict(h=1.02, w=0.95, head=1.0, skin="vamp_skin", top="cloth_black", legs="cloth_black", hair="hair_black", ears="round", eyes="eye_red", cape=True),
}


def build_humanoid(rig_col, body_col, p):
    M = bm.toon_material
    skin, top, legs = M(p["skin"]), M(p["top"]), M(p["legs"])
    eye = bm.flat_material(p.get("eyes", "eye_dark"), FLAT[p.get("eyes", "eye_dark")])
    blood = M("blood")
    hh, ww, hd = p["h"], p["w"], p["head"]
    thin = 0.6 if p.get("thin") else 1.0
    K = 1.35  # limb thickness
    b = bm.Builder(body_col)
    root = bm.pivot("root", None, (0, 0, 0), rig_col)
    hips = bm.pivot("hips", root, (0, 0, 0), rig_col)
    chest = bm.pivot("chest", hips, (0, 0, 0), rig_col)
    if p.get("hunch"):
        chest.rotation_euler = (math.radians(7), 0, 0)
    leg_len = 0.36 * hh
    waist = leg_len + 0.04
    head = bm.pivot("head", chest, (0, -0.02, waist + 0.42 * hh), rig_col)
    head.scale = (hd * 1.2, hd * 1.2, hd * 1.2)
    # torso
    b.box("pelvis", hips, (0, 0, waist), (0.2 * ww, 0.13 * ww, 0.08), legs)
    b.box("torso", chest, (0, 0, waist + 0.2 * hh), (0.27 * ww * thin + 0.05, 0.16 * ww * thin + 0.03, 0.3 * hh), top)
    if p.get("thin"):
        for k in range(3):
            b.box(f"rib{k}", chest, (0, -0.01, waist + 0.12 * hh + k * 0.08 * hh), (0.26 * ww, 0.12, 0.025), skin)
    b.box("belt", hips, (0, -0.005, waist + 0.04), (0.22 * ww, 0.14 * ww, 0.03), M("leather"))
    # head
    b.sphere("skull", head, (0, 0, 0.0), (0.085, 0.09, 0.095), skin)
    eyes = [b.sphere(f"eye{s}", head, (0.032 * s, -0.082, 0.012), (0.021, 0.011, 0.018), eye) for s in (-1, 1)]
    brow = M(p["hair"]) if p.get("hair") else M(p["skin"])
    for s in (-1, 1):
        b.box(f"brow{s}", head, (0.033 * s, -0.084, 0.036), (0.04, 0.014, 0.012), brow)
    if not p.get("snout"):
        b.box("nose", head, (0, -0.094, -0.008), (0.022, 0.022, 0.03), skin)
        b.box("mouth", head, (0, -0.086, -0.045), (0.04, 0.008, 0.008), M("blood") if p.get("eyes") == "eye_red" else M("leather"))
    if p.get("snout"):
        b.box("snout", head, (0, -0.1, -0.025), (0.07, 0.09, 0.05), skin)
    if p.get("hair"):
        b.sphere("hair", head, (0, 0.012, 0.04), (0.09, 0.09, 0.07), M(p["hair"]))
    if p.get("beard"):
        b.box("beard", head, (0, -0.07, -0.07), (0.12, 0.05, 0.11), M(p["hair"]))
    if p.get("ears") == "long":
        for s in (-1, 1):
            b.limb(f"ear{s}", head, (0.07 * s, 0.0, 0.01), (0.16 * s, 0.02, 0.07), 0.025, 0.0, skin)
    elif p.get("ears") == "round":
        for s in (-1, 1):
            b.sphere(f"ear{s}", head, (0.085 * s, 0.0, 0.0), (0.02, 0.015, 0.03), skin)
    elif p.get("ears") == "horns":
        for s in (-1, 1):
            b.limb(f"horn{s}", head, (0.04 * s, 0.03, 0.07), (0.07 * s, 0.09, 0.14), 0.022, 0.0, M("ivory"))
    if p.get("tail"):
        tail = b.limb("tail", hips, (0, 0.08, waist), (0, 0.32, 0.08), 0.06, 0.015, skin)
    if p.get("cape"):
        b.box("cape", chest, (0, 0.1, waist + 0.15 * hh), (0.26 * ww, 0.02, 0.36 * hh), M("cloth_red"))
    rig = {"eyes": eyes, "leg_len": leg_len, "tail": [tail] if p.get("tail") else [], "root": root, "hips": hips, "chest": chest, "head": head, "arm": {}, "leg": {}, "hand": {}, "forearm": {}, "stump": {}, "limb_parts": {}}
    for side, s in (("R", -1), ("L", 1)):
        sh = bm.pivot(f"shoulder_{side}", chest, (((0.27 * ww * thin + 0.05) / 2 + 0.035 * ww * thin) * s, 0.0, waist + 0.33 * hh), rig_col)
        arm_len = 0.3 * hh
        parts = [
            b.limb(f"upper_{side}", sh, (0, 0, 0), (0, 0, -arm_len * 0.5), 0.045 * K * ww * thin, 0.04 * K * ww * thin, skin if p.get("thin") else top),
            b.limb(f"fore_{side}", sh, (0, 0, -arm_len * 0.5), (0, -0.01, -arm_len), 0.04 * K * ww * thin, 0.036 * K * ww * thin, skin),
            b.sphere(f"fist_{side}", sh, (0, -0.01, -arm_len - 0.02), (0.052, 0.052, 0.05), skin),
        ]
        rig["limb_parts"][f"arm_{side}"] = parts
        rig["stump"][f"arm_{side}"] = b.sphere(f"stump_arm_{side}", chest, (((0.27 * ww * thin + 0.05) / 2 + 0.035 * ww * thin) * s, 0.0, waist + 0.31 * hh),
                                               (0.05, 0.05, 0.045), blood)
        rig["arm"][side] = sh
        rig["hand"][side] = bm.pivot(f"hand_{side}", sh, (0, -0.01, -arm_len - 0.02), rig_col)
        rig["forearm"][side] = bm.pivot(f"forearm_{side}", sh, (0, -0.01, -arm_len * 0.75), rig_col)
    for side, s in (("R", -1), ("L", 1)):
        hp = bm.pivot(f"hip_{side}", hips, (0.08 * ww * s, 0, leg_len), rig_col)
        parts = [
            b.limb(f"thigh_{side}", hp, (0, 0, 0), (0, 0, -leg_len * 0.5), 0.06 * K * ww * thin, 0.05 * K * ww * thin, legs),
            b.limb(f"shin_{side}", hp, (0, 0, -leg_len * 0.5), (0, 0, -leg_len + 0.03), 0.05 * K * ww * thin, 0.045 * K * ww * thin, legs if not p.get("thin") else skin),
            b.box(f"foot_{side}", hp, (0, -0.03, -leg_len + 0.02), (0.09, 0.15, 0.06), M("leather") if not p.get("thin") else skin),
        ]
        rig["limb_parts"][f"leg_{side}"] = parts
        rig["stump"][f"leg_{side}"] = b.sphere(f"stump_leg_{side}", hips, (0.08 * ww * s, 0, leg_len - 0.04),
                                               (0.055, 0.055, 0.04), blood)
        rig["leg"][side] = hp
    return rig


