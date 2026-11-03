"""Bake animated low-poly unit models for the 3D view (runs inside Blender).

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python standalone/remastered/art/pipeline/export_units.py [-- --only Orc]

For each race: build the body from primitives (orc from blender_models.py, the
others from one parametric humanoid), pose the rig for each animation frame,
and write every frame's triangles to game/Interface/models/<race>.json:

    {"race", "tris", "colors": base64 RGB per triangle,
     "anims": {"idle": {"fps", "frames": [base64 int16 xyz * 3 per triangle]}, ...}}

Game axes: x = east, y = up, z = south (Blender x, z, -y). 1 unit = 1 tile.
Everything is built here from code: no downloaded or extracted assets.
"""

import base64
import json
import math
import os
import struct
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_models as bm  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "game", "Interface", "models")
Q = 8000.0  # int16 quantisation: 1/8000 of a tile

# --- Low-poly: clamp the construction kit's detail (RuneScape-style facets) ---
_sphere, _limb, _dome, _disc, _torus = bm.Builder.sphere, bm.Builder.limb, bm.Builder.dome, bm.Builder.disc, bm.Builder.torus
bm.Builder.sphere = lambda self, name, parent, loc, scale, mat, seg=12, rings=8, smooth=True: _sphere(self, name, parent, loc, scale, mat, min(seg, 6), min(rings, 4), False)
bm.Builder.limb = lambda self, name, parent, start, end, r1, r2, mat, verts=10: _limb(self, name, parent, start, end, r1, r2, mat, min(verts, 5))
bm.Builder.dome = lambda self, name, parent, loc, scale, mat, seg=14, rings=8: _dome(self, name, parent, loc, scale, mat, min(seg, 7), min(rings, 3))
bm.Builder.disc = lambda self, name, parent, loc, radius, depth, normal, mat, verts=16: _disc(self, name, parent, loc, radius, depth, normal, mat, min(verts, 7))

from race_models import EXTRA, FLAT, RACES, build_humanoid  # noqa: E402,F401


# --- Gear: each piece is parented to a rig joint and exported in that joint's space ---
def grip(rig, col, name, tilt=18):
    g = bm.pivot(name, rig["hand"]["R"], (0, 0, 0), col)
    g.rotation_euler = (math.radians(tilt), math.radians(-6), 0)
    return g


def build_sword(rig, col):
    M = bm.toon_material
    b = bm.Builder(col)
    g = grip(rig, col, "sword_grip")
    b.limb("hilt", g, (0, 0, -0.07), (0, 0, 0.05), 0.022, 0.022, M("leather"))
    b.box("guard", g, (0, 0, 0.06), (0.15, 0.03, 0.025), M("iron"))
    b.box("blade", g, (0, 0, 0.3), (0.05, 0.012, 0.45), M("iron"))
    b.limb("tip", g, (0, 0, 0.52), (0, 0, 0.6), 0.03, 0.0, M("iron"))
    b.sphere("pommel", g, (0, 0, -0.085), (0.025, 0.025, 0.025), M("iron"))
    return b.objects


def build_spear(rig, col):
    M = bm.toon_material
    b = bm.Builder(col)
    g = grip(rig, col, "spear_grip", 8)
    b.limb("shaft", g, (0, 0, -0.45), (0, 0, 0.6), 0.02, 0.018, M("wood"))
    b.limb("head", g, (0, 0, 0.58), (0, 0, 0.78), 0.045, 0.0, M("iron"))
    return b.objects


def build_mace(rig, col):
    M = bm.toon_material
    b = bm.Builder(col)
    g = grip(rig, col, "mace_grip")
    b.limb("haft", g, (0, 0, -0.08), (0, 0, 0.3), 0.022, 0.02, M("wood"))
    b.sphere("head", g, (0, 0, 0.34), (0.07, 0.07, 0.07), M("iron"))
    for k in range(4):
        a = k * math.pi / 2
        b.limb(f"spike{k}", g, (math.cos(a) * 0.05, math.sin(a) * 0.05, 0.34), (math.cos(a) * 0.11, math.sin(a) * 0.11, 0.34), 0.02, 0.0, M("iron"))
    return b.objects


def build_dagger(rig, col):
    M = bm.toon_material
    b = bm.Builder(col)
    g = grip(rig, col, "dagger_grip", 28)
    b.limb("hilt", g, (0, 0, -0.05), (0, 0, 0.04), 0.02, 0.02, M("leather"))
    b.box("guard", g, (0, 0, 0.045), (0.08, 0.025, 0.02), M("iron"))
    b.box("blade", g, (0, 0, 0.14), (0.035, 0.01, 0.17), M("iron"))
    return b.objects


def build_pickaxe(rig, col):
    M = bm.toon_material
    b = bm.Builder(col)
    g = grip(rig, col, "pick_grip")
    b.limb("haft", g, (0, 0, -0.09), (0, 0, 0.38), 0.024, 0.022, M("wood"))
    # The pick points forward and back (along the swing), like the axe head.
    b.limb("pickA", g, (0, 0, 0.36), (0, -0.2, 0.3), 0.03, 0.006, M("iron"))
    b.limb("pickB", g, (0, 0, 0.36), (0, 0.2, 0.3), 0.03, 0.006, M("iron"))
    return b.objects


def build_bow(rig, col):
    M = bm.toon_material
    b = bm.Builder(col)
    g = bm.pivot("bow_grip", rig["hand"]["L"], (0, 0, 0), col)
    b.limb("upper", g, (0, 0, 0), (0, -0.08, 0.32), 0.022, 0.012, M("wood"))
    b.limb("lower", g, (0, 0, 0), (0, -0.08, -0.32), 0.022, 0.012, M("wood"))
    b.limb("string", g, (0, -0.08, 0.32), (0, -0.08, -0.32), 0.004, 0.004, M("leather"))
    return b.objects


GEAR = {
    "axe": ("handR", lambda rig, col: bm.build_axe(rig, col, "iron")),
    "sword": ("handR", build_sword),
    "spear": ("handR", build_spear),
    "mace": ("handR", build_mace),
    "dagger": ("handR", build_dagger),
    "pickaxe": ("handR", build_pickaxe),
    "bow": ("handL", build_bow),
    "shield": ("foreL", lambda rig, col: bm.build_buckler(rig, col, "wood", "iron")),
    "helmet": ("head", lambda rig, col: bm.build_helmet(rig, col, "iron")),
}
METALS = {"bronze", "iron", "steel", "mithril", "gold"}

# Body parts the armour recolours: 1 head, 2 torso, 3/4 right/left arm, 5 legs, 6/7 right/left hand.
def part_of(name):
    n = name.lower()
    side = "R" if n.endswith("_r") else "L" if n.endswith("_l") else ""
    if any(k in n for k in ("fist",)):
        return 6 if side == "R" else 7
    if any(k in n for k in ("upper", "fore", "delt", "bracer")):
        return 3 if side == "R" else 4
    if any(k in n for k in ("thigh", "shin")):
        return 5
    if any(k in n for k in ("chest", "belly", "hunch", "torso", "rib", "pelvis", "belt", "buckle", "flap")):
        return 2
    if any(k in n for k in ("skull", "jaw", "brow", "eye", "tusk", "ear", "knot", "hair", "beard", "snout", "horn")):
        return 1
    return 0


# Rig joints whose transform is exported each frame (game axes).
def joints(rig):
    return {"handR": rig["hand"]["R"], "handL": rig["hand"]["L"], "foreL": rig["forearm"]["L"], "head": rig["head"]}


def game_matrix(obj):
    """3x4 joint matrix in game axes (x, y=up, z=south): rows of [R|t]."""
    m = obj.matrix_world
    # C maps Blender (x, y, z) to game (x, z, -y).
    C = ((1, 0, 0), (0, 0, 1), (0, -1, 0))
    M3 = [[m[i][j] for j in range(3)] for i in range(3)]
    t = [m[0][3], m[1][3], m[2][3]]
    CM = [[sum(C[i][k] * M3[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    MG = [[sum(CM[i][k] * C[j][k] for k in range(3)) for j in range(3)] for i in range(3)]  # C M C^T
    tg = [sum(C[i][k] * t[k] for k in range(3)) for i in range(3)]
    return [round(v, 4) for row in range(3) for v in (MG[row] + [tg[row]])]


# --- Animations: joint angles per frame (degrees about x; + swings forward) ---
def anim_frames():
    walk = []
    for k in range(8):
        t = k / 8 * 2 * math.pi
        walk.append(dict(leg=(32 * math.sin(t), -32 * math.sin(t)), arm=(-26 * math.sin(t), 26 * math.sin(t)), bob=0.025 * abs(math.sin(t)), lean=4, tool=False))
    idle = []
    for k in range(4):
        t = k / 4 * 2 * math.pi
        idle.append(dict(leg=(0, 0), arm=(3 * math.sin(t), -3 * math.sin(t)), bob=0.006 * math.sin(t), lean=1.5 * math.sin(t), tool=False))
    work = []
    for a, lean in ((-40, 4), (-120, 0), (-165, -4), (-95, 6), (15, 16), (-10, 10)):
        work.append(dict(leg=(8, -8), arm=(a, -20), bob=0.0, lean=lean, tool=True))
    attack = []
    for a, lean in ((-70, 0), (-140, -4), (40, 18), (5, 8)):
        attack.append(dict(leg=(18, -14), arm=(a, 25), bob=0.0, lean=lean, tool=True))
    return {"idle": (4, idle), "walk": (10, walk), "work": (7, work), "attack": (9, attack)}


def pose(rig, f):
    for i, side in enumerate(("R", "L")):
        rig["leg"][side].rotation_euler.x = math.radians(f["leg"][i])
        rig["arm"][side].rotation_euler.x = math.radians(-f["arm"][i])
    rig["hips"].location.z = f["bob"]
    base = rig["chest"].get("base_x", rig["chest"].rotation_euler.x)
    rig["chest"]["base_x"] = base
    rig["chest"].rotation_euler.x = base + math.radians(f["lean"])


def color_of(mat):
    name = mat.name if mat else ""
    if name.startswith("M_") and name[2:] in bm.PALETTE:
        h = bm.PALETTE[name[2:]][1]
    elif name.startswith("F_") and name[2:] in FLAT:
        h = FLAT[name[2:]]
    else:
        h = "#888888"
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def bake(objects, tool_objects):
    """Triangles of the evaluated scene: list of (3 points in game axes), plus a colour per triangle."""
    dg = bpy.context.evaluated_depsgraph_get()
    tris, cols, parts = [], [], []
    for obj in objects + tool_objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        ev = obj.evaluated_get(dg)
        mesh = ev.to_mesh()
        mesh.calc_loop_triangles()
        mw = obj.matrix_world
        mat = obj.material_slots[0].material if obj.material_slots else None
        c = color_of(mat)
        for lt in mesh.loop_triangles:
            pts = []
            for vi in lt.vertices:
                co = mw @ mesh.vertices[vi].co
                pts.append((co.x, co.z, -co.y))
            tris.append(pts)
            cols.append(c)
            parts.append(part_of(obj.name))
        ev.to_mesh_clear()
    return tris, cols, parts


def build_race(race):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)
    rig_col = bpy.data.collections.new("rig")
    body_col = bpy.data.collections.new("body")
    tool_col = bpy.data.collections.new("tool")
    for c in (rig_col, body_col, tool_col):
        bpy.context.scene.collection.children.link(c)
    rig = bm.build_orc(rig_col, body_col) if race == "Orc" else build_humanoid(rig_col, body_col, RACES[race])
    for k, v in rig["stump"].items():
        v.hide_render = True
    gear = {}
    for name, (joint, builder) in GEAR.items():
        gc = bpy.data.collections.new("gear_" + name)
        bpy.context.scene.collection.children.link(gc)
        builder(rig, gc)
        gear[name] = (joint, [o for o in gc.objects if o.type == "MESH"])
    return rig, list(body_col.objects), gear


def export(race):
    rig, body, gear = build_race(race)
    colors = parts = None
    tri_count = None
    anims = {}
    J = joints(rig)
    for name, (fps, frames) in anim_frames().items():
        enc, jfr = [], []
        for f in frames:
            pose(rig, f)
            bpy.context.view_layer.update()
            tris, cols, prt = bake(body, [])
            if colors is None:
                colors, parts, tri_count = cols, prt, len(tris)
            assert len(tris) == tri_count, (race, name, len(tris), tri_count)
            flat = []
            for t in tris:
                for p in t:
                    flat += [max(-32767, min(32767, round(v * Q))) for v in p]
            enc.append(base64.b64encode(struct.pack("<%dh" % len(flat), *flat)).decode())
            jfr.append({k: game_matrix(o) for k, o in J.items()})
        anims[name] = {"fps": fps, "frames": enc, "joints": jfr}
    # Gear at the rest pose, in its joint's space (game axes).
    pose(rig, anim_frames()["idle"][1][0])
    bpy.context.view_layer.update()
    gear_out = {}
    for gname, (joint, objs) in gear.items():
        jm = J[joint].matrix_world.inverted()
        pos, mats, cols = [], [], []
        dg = bpy.context.evaluated_depsgraph_get()
        for obj in objs:
            ev = obj.evaluated_get(dg)
            mesh = ev.to_mesh()
            mesh.calc_loop_triangles()
            mat = obj.material_slots[0].material if obj.material_slots else None
            key = mat.name[2:] if mat and mat.name.startswith("M_") else ""
            code = 4 if key.endswith("_edge") else 0 if key in METALS else 1 if key == "wood" else 2 if key == "leather" else 3
            c = color_of(mat)
            for lt in mesh.loop_triangles:
                for vi in lt.vertices:
                    lo = jm @ (obj.matrix_world @ mesh.vertices[vi].co)
                    pos += [max(-32767, min(32767, round(v * Q))) for v in (lo.x, lo.z, -lo.y)]
                mats.append(code)
                cols += c
            ev.to_mesh_clear()
        gear_out[gname] = {"joint": joint, "tris": len(mats),
                           "pos": base64.b64encode(struct.pack("<%dh" % len(pos), *pos)).decode(),
                           "mat": base64.b64encode(bytes(mats)).decode(), "col": base64.b64encode(bytes(cols)).decode()}
    data = {"race": race, "tris": tri_count, "q": Q,
            "colors": base64.b64encode(bytes(v for c in colors for v in c)).decode(),
            "parts": base64.b64encode(bytes(parts)).decode(), "anims": anims, "gear": gear_out}
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{race.lower()}.json")
    with open(path, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    print(f"{race}: {tri_count} triangles, gear {sum(g['tris'] for g in gear_out.values())} triangles -> {os.path.relpath(path, ROOT)} ({os.path.getsize(path)//1024} KB)")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    for race in ["Orc"] + list(RACES):
        if only and race != only:
            continue
        export(race)


main()
