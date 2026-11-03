"""Stage 1 of the Remastered sprite pipeline: render hi-res sprite cells.

Run headless (from anywhere):

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python standalone/remastered/art/pipeline/render_sprites.py -- [--only Orc] [--preview]

Writes art/build/renders/<sheet>/<state>/f<frame>_<dir>.png (RGBA, transparent)
plus art/build/renders/index.json describing every sheet, state, frame order
and DMI metadata. Stage 2 (build_dmi.py, plain Python + Pillow) downsamples,
outlines and packs those cells into .dmi files.

Rendering rules (planning/ART_DIRECTION.md):
  * orthographic camera, 30 degrees above the horizon, 1 tile = 32 px;
  * one fixed key light from the top-left of the screen. The *model* turns for
    each direction; camera and light never move;
  * flat toon ramps (3 bands, 4 for metals), no anti-aliasing;
  * equipment is rendered as its own layer with the base body as a holdout,
    so the overlay is cut where the body is in front of it.
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
import blender_models as bm  # noqa: E402
import race_models as rm  # noqa: E402

ART = os.path.dirname(HERE)
GAME_ICONS = os.path.join(os.path.dirname(ART), "game", "Icons")
OUT = os.path.join(ART, "build", "renders")

RENDER_PX = 256            # 8x of 32 px, 4x of 64 px
TILE_UNITS = 1.0           # world units visible across one tile
CAMERA_ELEVATION = 30.0    # degrees above the horizon
FEET_PX = 29.5             # ground origin, in 32 px rows from the top
KEY_LIGHT_FROM = Vector((-1.0, -0.9, 1.35))  # screen top-left, slightly in front
KEY_LIGHT_STRENGTH = 2.2
AMBIENT = (0.13, 0.14, 0.19)

# BYOND/DMI direction order and the model turn that shows each one.
DIRS = [("south", 0.0), ("north", 180.0), ("east", 90.0), ("west", -90.0)]

# Walk cycle in the original 3-frame layout: stand, left step, right step.
# Any translation is snapped to whole 32 px pixels (1/32 unit) so small
# features (eyes, tusks) land on the same sample grid in every frame.
BOB = 1.0 / 32.0
WALK = [
    {"bob": 0.0, "leg": {"L": 0, "R": 0}, "arm": {"L": 0, "R": 0}},
    {"bob": -BOB, "leg": {"L": -26, "R": 24}, "arm": {"L": 18, "R": -20}},
    {"bob": -BOB, "leg": {"L": 24, "R": -26}, "arm": {"L": -20, "R": 18}},
]
STAND = WALK[:1]

# Orc.dmi state list, in the original order, with the limbs each one lacks.
ORC_STATES = [
    ("Normal", []), ("NoLeftArm", ["arm_L"]), ("NoRightArm", ["arm_R"]),
    ("NoArms", ["arm_L", "arm_R"]), ("NoLeftLeg", ["leg_L"]), ("NoRightLeg", ["leg_R"]),
    ("NoLegs", ["leg_L", "leg_R"]), ("None", ["arm_L", "arm_R", "leg_L", "leg_R"]),
    ("NoRightLegNoLeftArm", ["leg_R", "arm_L"]), ("NoLeftLegNoRightArm", ["leg_L", "arm_R"]),
    ("NoRightArmNoRightLeg", ["arm_R", "leg_R"]), ("NoLeftArmNoLeftLeg", ["arm_L", "leg_L"]),
    ("NoLegsNoLeftArm", ["leg_L", "leg_R", "arm_L"]), ("NoLegsNoRightArm", ["leg_L", "leg_R", "arm_R"]),
    ("NoArmsNoRightLeg", ["arm_L", "arm_R", "leg_R"]), ("NoArmsNoLeftLeg", ["arm_L", "arm_R", "leg_L"]),
]

# Equipment overlay states. Original item states are 4 dirs x 3 frames,
# delay 2,2,2, movement = 1, and the same state is the inventory/ground icon.
ITEMS = [
    ("Bronze Axe", "weapon", lambda rig, col: bm.build_axe(rig, col, "bronze")),
    ("Iron Axe", "weapon", lambda rig, col: bm.build_axe(rig, col, "iron")),
    ("Steel Axe", "weapon", lambda rig, col: bm.build_axe(rig, col, "steel")),
    ("Wooden Buckler", "shield", lambda rig, col: bm.build_buckler(rig, col, "wood", "iron")),
    ("Iron War Helm", "helmet", lambda rig, col: bm.build_helmet(rig, col, "iron")),
]


# Playable races built from race_models.py: (race, output sheet, original sheet
# whose state list, frame counts and timing are copied). Dwarves have no body
# sheet of their own in the original (they use Human.dmi), so theirs is new.
RACE_SHEETS = [
    ("Human", "Human.dmi", "Human.dmi"),
    ("Dwarf", "Dwarves.dmi", "Human.dmi"),
    ("Elf", "Night Elf.dmi", "Night Elf.dmi"),
    ("Goblin", "Goblins.dmi", "Goblins.dmi"),
    ("Kobold", "Kobold.dmi", "Kobold.dmi"),
    ("Lizardman", "LizardMan.dmi", "LizardMan.dmi"),
    ("Frogman", "FrogMan.dmi", "FrogMan.dmi"),
    ("Skeleton", "Skeleton.dmi", "Skeleton.dmi"),
    ("Zombie", "DevourerZombie.dmi", "DevourerZombie.dmi"),
    ("Vampire", "Vampire.dmi", "Vampire.dmi"),
]


def original_states(file):
    """State list of an original DMI (PNG zTXt "Description"), read without Pillow."""
    import re
    import struct
    import zlib
    with open(os.path.join(GAME_ICONS, file), "rb") as fh:
        data = fh.read()
    pos, desc = 8, ""
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if kind == b"zTXt" and body.startswith(b"Description\0"):
            desc = zlib.decompress(body[len("Description") + 2:]).decode("latin-1")
        elif kind == b"tEXt" and body.startswith(b"Description\0"):
            desc = body[len("Description") + 1:].decode("latin-1")
        pos += 12 + n
    states = []
    for m in re.finditer(r'state = "([^"]*)"\n((?:\t.*\n?)*)', desc):
        meta = dict(re.findall(r"\t(\w+) = (.*)", m.group(2)))
        frames = int(meta.get("frames", 1))
        delay = [int(d) for d in meta["delay"].split(",")][:frames] if "delay" in meta else None
        states.append({"name": m.group(1), "dirs": int(meta.get("dirs", 1)), "frames": frames, "delay": delay,
                       "movement": int(meta["movement"]) if "movement" in meta else None,
                       "rewind": int(meta["rewind"]) if "rewind" in meta else None})
    return states


def missing_limbs(name):
    """Limbs a state lacks, from the original naming: NoLeftArm, NoLegs, None..."""
    import re
    if name == "None":
        return ["arm_L", "arm_R", "leg_L", "leg_R"]
    out = []
    for side, limb in re.findall(r"No(Left|Right)?(Arm|Leg)", name):
        sides = {"Left": ["L"], "Right": ["R"]}.get(side, ["L", "R"])
        out += [f"{limb.lower()}_{s}" for s in sides]
    return out


def body_meshes(rig_body):
    return [o for o in rig_body.all_objects if o.type == "MESH" and not o.hide_render]


def lie_down(rig, body_col, on):
    """Sleep pose, as the originals draw it: on the back, head to the north
    (away from the camera), face up, eyes shut, centred on the tile."""
    root = rig["root"]
    root.rotation_euler = (math.radians(-90) if on else 0, 0, 0)
    for e in rig.get("eyes", []):
        e.hide_render = on
    root.location = (0, 0, 0)
    bpy.context.view_layer.update()
    if not on:
        return
    ys, zs = [], []
    for o in body_meshes(body_col):
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            ys.append(w.y)
            zs.append(w.z)
    root.location = (0, -(min(ys) + max(ys)) / 2, -min(zs) + 0.01)
    bpy.context.view_layer.update()


def reset_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = scene.render.resolution_y = RENDER_PX
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.filter_size = 0.0
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.eevee.taa_render_samples = 1
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    try:
        world.use_nodes = True
    except Exception:
        pass
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (*AMBIENT, 1.0)
    bg.inputs["Strength"].default_value = 1.0

    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = TILE_UNITS
    cam_data.shift_y = (FEET_PX - 16.0) / 32.0
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    el = math.radians(CAMERA_ELEVATION)
    cam.rotation_euler = (math.pi / 2 - el, 0, 0)
    cam.location = (0, -10 * math.cos(el), 10 * math.sin(el))
    scene.camera = cam

    sun_data = bpy.data.lights.new("key", "SUN")
    sun_data.energy = KEY_LIGHT_STRENGTH
    sun_data.angle = 0.0
    sun_data.use_shadow = True
    sun = bpy.data.objects.new("key", sun_data)
    sun.rotation_mode = "QUATERNION"
    sun.rotation_quaternion = (-KEY_LIGHT_FROM).normalized().to_track_quat("-Z", "Y")
    scene.collection.objects.link(sun)
    return scene


def new_collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def layer_col(name):
    return bpy.context.view_layer.layer_collection.children[name]


def pose(rig, frame):
    rig["root"].location.z = frame.get("z", 0.0) + frame["bob"]
    if "lean" in frame:
        rig["chest"].rotation_euler.x = rig["chest"].get("base_x", 0.0) + math.radians(frame["lean"])
    for side in ("L", "R"):
        rig["leg"][side].rotation_euler.x = math.radians(frame["leg"][side])
        rig["arm"][side].rotation_euler.x = math.radians(frame["arm"][side])


def set_missing(rig, missing):
    for key, parts in rig["limb_parts"].items():
        gone = key in missing
        for obj in parts:
            obj.hide_render = gone
        rig["stump"][key].hide_render = not gone


def face(rig, degrees):
    rig["root"].rotation_euler.z = math.radians(degrees)


def render_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def render_state(rig, sheet, state, frames, rel_dir, dirs=4):
    cells = []
    for fi, frame in enumerate(frames):
        pose(rig, frame)
        for dname, deg in DIRS[:dirs]:
            face(rig, deg)
            rel = os.path.join(rel_dir, f"f{fi}_{dname}.png")
            render_to(os.path.join(OUT, rel))
            cells.append(rel)
    return cells


def build_coffin(col):
    """Closed coffin on the ground (the original Vampire "Sleep" states)."""
    b = bm.Builder(col)
    root = pivot_root = bm.pivot("coffin_root", None, (0, 0, 0), col)
    wood, trim = bm.toon_material("wood"), bm.toon_material("iron")
    outline = [(-0.1, -0.42), (-0.17, -0.12), (-0.13, 0.4), (0.13, 0.4), (0.17, -0.12), (0.1, -0.42)]
    # prism profile is (x, z); lay it flat with a 90 degree turn about X
    b.prism("coffin", root, (0, 0.0, 0.07), outline, 0.14, wood, rot=(math.radians(90), 0, 0))
    b.prism("lid", root, (0, 0.0, 0.15), [(x * 0.9, z * 0.9) for x, z in outline], 0.03, wood, rot=(math.radians(90), 0, 0))
    b.box("cross_v", root, (0, -0.05, 0.17), (0.03, 0.3, 0.01), trim)
    b.box("cross_h", root, (0, 0.05, 0.17), (0.14, 0.03, 0.01), trim)
    return pivot_root


def render_race(race, out_file, src_file, preview=False):
    reset_scene()
    rig_col = new_collection("Rig")
    body_col = new_collection("Body")
    tail_col = new_collection("Tail")
    rig = rm.build_humanoid(rig_col, body_col, rm.RACES[race])
    rig["chest"]["base_x"] = rig["chest"].rotation_euler.x
    for st in rig["stump"].values():
        st.hide_render = True
    states = original_states(src_file)
    # A separate "Tail" state means the tail is an overlay drawn over armour, so
    # the body states leave it out (OverlayBuilds.dm adds it back on top).
    tail_overlay = any(st["name"] == "Tail" for st in states)
    for obj in rig.get("tail", []):
        if tail_overlay:
            for c in obj.users_collection:
                c.objects.unlink(obj)
            tail_col.objects.link(obj)
    layer_col("Tail").exclude = True
    coffin_col = new_collection("Coffin")
    build_coffin(coffin_col)
    layer_col("Coffin").exclude = True
    name = os.path.splitext(out_file)[0]
    sheet = {"name": name, "file": out_file, "layer": "base", "race": race, "source": src_file, "states": []}
    for st in (states[:2] if preview else states):
        sname = st["name"]
        sleeping = "Sleep" in sname
        set_missing(rig, missing_limbs(sname))
        coffin = race == "Vampire" and sleeping
        if coffin:
            layer_col("Body").exclude = True
            layer_col("Coffin").exclude = False
            frames = STAND * st["frames"]
        elif sleeping:
            lie_down(rig, body_col, True)
            base = rig["root"].location.z
            frames = [{"z": base, "bob": (k % 2) / 64.0, "leg": {"L": 0, "R": 0}, "arm": {"L": 0, "R": 0}}
                      for k in range(st["frames"])]
        elif all(f"leg_{x}" in missing_limbs(sname) for x in "LR"):
            sit = -(rig.get("leg_len", 0.36) - 0.05)
            frames = [dict(f, z=sit) for f in (STAND * st["frames"])[:st["frames"]]]
        elif sname == "Sneak":
            frames = [dict(f, lean=28, z=-1.0 / 32.0) for f in WALK]
        elif st["frames"] == 3:
            frames = WALK
        else:
            frames = (STAND * st["frames"])[:st["frames"]]
        if sname == "Tail":
            layer_col("Body").holdout = True
            layer_col("Tail").exclude = False
        rel = os.path.join(name, sname or "_blank")
        cells = render_state(rig, name, sname, frames, rel, dirs=min(st["dirs"], 4))
        if sname == "Tail":
            layer_col("Body").holdout = False
            layer_col("Tail").exclude = True
        if coffin:
            layer_col("Body").exclude = False
            layer_col("Coffin").exclude = True
        elif sleeping:
            lie_down(rig, body_col, False)
        rig["chest"].rotation_euler.x = rig["chest"]["base_x"]
        sheet["states"].append(dict(st, cells=cells))
    set_missing(rig, [])
    print(f"{race}: {len(sheet['states'])} states -> {out_file}")
    return sheet


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    preview = "--preview" in argv  # Normal state + one item only, for quick looks

    index = {"render_px": RENDER_PX, "tile_px": 32, "camera_elevation": CAMERA_ELEVATION,
             "dirs": [d for d, _ in DIRS], "sheets": []}
    if only in (None, "Orc", "Items"):
        render_orc(only, preview, index)
    for race, out_file, src_file in RACE_SHEETS:
        if only not in (None, "Races", race):
            continue
        index["sheets"].append(render_race(race, out_file, src_file, preview))
    write_index(index, only)


def render_orc(only, preview, index):
    reset_scene()
    rig_col = new_collection("Rig")
    body_col = new_collection("Body")
    rig = bm.build_orc(rig_col, body_col)
    item_cols = {}
    for name, slot, build in ITEMS:
        col = new_collection("Item " + name)
        build(rig, col)
        item_cols[name] = col
        layer_col(col.name).exclude = True

    if only in (None, "Orc"):
        sheet = {"name": "Orc", "file": "Orc.dmi", "layer": "base", "states": []}
        for name, missing in (ORC_STATES[:1] if preview else ORC_STATES):
            moving = not any(m.startswith("leg") for m in missing)
            frames = WALK if moving else STAND
            set_missing(rig, missing)
            cells = render_state(rig, "Orc", name, frames, os.path.join("Orc", name))
            sheet["states"].append({
                "name": name, "dirs": 4, "frames": len(frames),
                "delay": [2] * len(frames) if moving else None,
                "movement": 1 if moving else 0, "rewind": 0, "cells": cells})
        set_missing(rig, [])
        index["sheets"].append(sheet)

    if only in (None, "Items"):
        # Base body becomes a holdout: it cuts the overlay but never draws.
        layer_col("Body").holdout = True
        sheet = {"name": "OrcGear", "file": "OrcGear.dmi", "layer": "overlay", "body": "Orc", "states": []}
        for name, slot, _ in (ITEMS[:2] if preview else ITEMS):
            layer_col(item_cols[name].name).exclude = False
            cells = render_state(rig, "OrcGear", name, WALK, os.path.join("OrcGear", name))
            layer_col(item_cols[name].name).exclude = True
            sheet["states"].append({
                "name": name, "slot": slot, "dirs": 4, "frames": 3, "delay": [2, 2, 2],
                "movement": 1, "rewind": None, "cells": cells})
        layer_col("Body").holdout = False
        index["sheets"].append(sheet)



def write_index(index, only):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "index.json")
    old = {}
    if os.path.exists(path) and only:
        with open(path) as fh:
            old = {s["name"]: s for s in json.load(fh).get("sheets", [])}
    merged = {**old, **{s["name"]: s for s in index["sheets"]}}
    index["sheets"] = [merged[k] for k in sorted(merged)]
    with open(path, "w") as fh:
        json.dump(index, fh, indent=1)
    print("wrote", path)


if __name__ == "__main__":   # importable for its state helpers (render_real.py)
    main()
