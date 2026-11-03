"""Stage 1 of the "real" art style: render races and creatures with Cycles.

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \\
        --python standalone/remastered/art/pipeline/render_real.py -- [--only Human,Orc] [--px 512] [--samples 64] [--states]

Writes art/build/renders-real/<Name>/<state>/f0_<dir>.png (RGBA, transparent) for
the four facings (--states: every state of the race's original sheet, standing frame), plus <Name>.blend so the model can be opened and edited in
Blender, and index.json. Stage 2 (build_real.py) turns them into game sprites.

Look (planning/ART_DIRECTION_REAL.md): camera 37.2 degrees above the horizon, the
same angle as the 3D view's iso camera, orthographic, 1 tile across the frame,
feet on row 59 of 64. Warm key light from the screen's top-left, cool sky fill,
a rim light from behind so silhouettes separate from the ground, AgX colour.
The model turns for each facing; camera and lights never move.
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import creatures_real as cr  # noqa: E402
import races_real as rr  # noqa: E402

ART = os.path.dirname(HERE)
OUT = os.path.join(ART, "build", "renders-real")
ELEVATION = 37.2
FEET_ROW = 59.0 / 64.0
DIRS = [("south", 0.0), ("north", 180.0), ("east", 90.0), ("west", -90.0)]
KEY_FROM, KEY_COLOUR, KEY_POWER = Vector((-1.0, -0.8, 1.25)), (1.0, 0.93, 0.82), 3.6
RIM_FROM, RIM_COLOUR, RIM_POWER = Vector((0.75, 1.0, 0.7)), (1.0, 0.9, 0.78), 2.2
SKY, SKY_POWER = (0.38, 0.46, 0.6), 0.45

# The original sheet whose state list each body copies (missing limbs, sleep, sneak...).
# Dwarves use Human.dmi in the original.
STATE_SOURCE = {"Human": "Human.dmi", "Dwarf": "Human.dmi", "Elf": "Night Elf.dmi", "Orc": "Orc.dmi", "Goblin": "Goblins.dmi",
                "Kobold": "Kobold.dmi", "Lizardman": "LizardMan.dmi", "Frogman": "FrogMan.dmi", "Skeleton": "Skeleton.dmi",
                "Zombie": "DevourerZombie.dmi", "Vampire": "Vampire.dmi", "Demon": "Demon.dmi"}

DRAGONS = ["red", "green", "black", "blue", "gold", "ice", "sand", "silver", "zombie", "navy", "dark"]
SUBJECTS = list(rr.RACES) + ["Dragon" + d.capitalize() for d in DRAGONS] + ["Spider" + c for c in cr.SPIDERS]


def reset_scene(px, samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = px
    sc.render.film_transparent = True
    sc.render.filter_size = 1.2
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Base Contrast"
    except TypeError:
        sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("sky")
    sc.world = world
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (*SKY, 1.0)
    bg.inputs["Strength"].default_value = SKY_POWER
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 1.0
    cam_data.shift_y = FEET_ROW - 0.5
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    el = math.radians(ELEVATION)
    cam.rotation_euler = (math.pi / 2 - el, 0, 0)
    cam.location = (0, -10 * math.cos(el), 10 * math.sin(el))
    sc.camera = cam
    for name, frm, colour, power, angle in (("key", KEY_FROM, KEY_COLOUR, KEY_POWER, 3.0), ("rim", RIM_FROM, RIM_COLOUR, RIM_POWER, 8.0)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy, ld.color, ld.angle = power, colour, math.radians(angle)
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_mode = "QUATERNION"
        lo.rotation_quaternion = (-frm).normalized().to_track_quat("-Z", "Y")
        sc.collection.objects.link(lo)
    return sc


def build(name, rig_col, body_col):
    if name.startswith("Dragon"):
        return cr.build_dragon(rig_col, body_col, name[6:].lower())
    if name.startswith("Spider"):
        return cr.build_spider(rig_col, body_col, name[6:])
    return rr.build_person(rig_col, body_col, rr.RACES[name])


def state_poses(rig, body_col, src):
    """(state name, setup) for every state of the original sheet: the standing frame only,
    which is what the 3D view shows. Missing limbs show stumps; sleepers lie down."""
    import render_sprites as rs   # its state helpers (render_sprites only runs main() as a script)
    out = []
    for st in rs.original_states(src):
        name = st["name"]
        if name in ("Tail",) or "Wing" in name:
            continue
        out.append((name or "Normal", min(st["dirs"], 4), name))
    return out, rs


def render_subject(name, px, samples, states=False):
    sc = reset_scene(px, samples)
    rig_col = bpy.data.collections.new("Rig")
    body_col = bpy.data.collections.new("Body")
    sc.collection.children.link(rig_col)
    sc.collection.children.link(body_col)
    rig = build(name, rig_col, body_col)
    for st in rig["stump"].values():
        st.hide_render = True
    def shoot(state, dirs):
        cells = []
        for dname, deg in DIRS[:dirs]:
            rig["root"].rotation_euler.z = math.radians(deg)
            rel = os.path.join(name, state, f"f0_{dname}.png")
            sc.render.filepath = os.path.join(OUT, rel)
            bpy.ops.render.render(write_still=True)
            cells.append(rel)
        rig["root"].rotation_euler.z = 0
        return {"name": state, "dirs": dirs, "frames": 1, "cells": cells}

    out = []
    if states and name in STATE_SOURCE:
        poses, rs = state_poses(rig, body_col, STATE_SOURCE[name])
        for state, dirs, orig in poses:
            rs.set_missing(rig, rs.missing_limbs(orig))
            sleeping = "Sleep" in orig
            if sleeping:
                rs.lie_down(rig, body_col, True)
            elif all(f"leg_{x}" in rs.missing_limbs(orig) for x in "LR"):
                rig["root"].location.z = -(rig["leg_len"] - 0.05)
            out.append(shoot(state, dirs))
            if sleeping:
                rs.lie_down(rig, body_col, False)
            rig["root"].location.z = 0
        rs.set_missing(rig, [])
    else:
        out.append(shoot("Normal", 4))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, name + ".blend"))
    print("rendered", name, len(out), "states")
    return {"name": name, "states": out}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
    only = opt("--only", None)
    states = "--states" in argv
    px, samples = int(opt("--px", 512)), int(opt("--samples", 64))
    names = only.split(",") if only else SUBJECTS
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "index.json")
    index = json.load(open(path)) if os.path.exists(path) else {"sheets": []}
    old = {s["name"]: s for s in index["sheets"]}
    for n in names:
        old[n] = render_subject(n, px, samples, states)
    index = {"render_px": px, "elevation": ELEVATION, "dirs": [d for d, _ in DIRS], "sheets": [old[k] for k in sorted(old)]}
    with open(path, "w") as fh:
        json.dump(index, fh, indent=1)
    print("wrote", path)


main()
