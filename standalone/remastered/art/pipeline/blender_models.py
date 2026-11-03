"""Procedural low-poly models for the Remastered sprite pipeline.

Runs inside Blender (imported by render_sprites.py). Every mesh here is built
from primitives in code: no downloaded, traced or extracted assets.

Conventions (see planning/ART_DIRECTION.md):
  * 1 Blender unit = 1 map tile (32 px at 1x).
  * The model faces -Y (towards the camera) in its SOUTH pose.
  * The character's right side is -X (screen left when facing south).
  * Ground is z = 0. The rig is a tree of empties ("pivots"); body parts and
    equipment are parented to pivots, so overlays line up with the body in
    every pose and direction automatically.
"""

import math

import bmesh
import bpy
from mathutils import Vector

# ---------------------------------------------------------------------------
# Palette: every material is a 3-band (4 for metals) toon ramp.
# shadow = cool and dark, base = local colour, light = warm and bright,
# hi = specular glint (metals only). Hex sRGB.
# ---------------------------------------------------------------------------

PALETTE = {
    # skin / organics
    "orc_skin": ("#2e5638", "#5f9438", "#a6c757", None),
    "leather": ("#3b2320", "#6e4426", "#a0703c", None),
    "cloth_red": ("#4a1a26", "#8e2e2a", "#c4523a", None),
    "hair_black": ("#141016", "#2b2224", "#4a3a34", None),
    "ivory": ("#7d6e5c", "#d6c9a0", "#f6eed2", None),
    "blood": ("#4a0a10", "#a01818", "#d83a2a", None),
    # material tiers (RuneScape-style colour language; one shape, many metals)
    "wood": ("#43281e", "#86562e", "#bd8a4e", None),
    "bone": ("#7d6e5c", "#d6c9a0", "#f6eed2", None),
    "bronze": ("#5a3022", "#a8692e", "#dda04c", "#fbe3a0"),
    "iron": ("#2c2a2e", "#58534f", "#837b72", "#a89e92"),
    "steel": ("#3b4560", "#8794a8", "#c6d2e2", "#ffffff"),
    "mithril": ("#25296e", "#5266c4", "#94b0ff", "#eaf2ff"),
    "gold": ("#6e3e14", "#c8952a", "#f5d55c", "#fffbe0"),
}

# Ramp thresholds on lit diffuse intensity (tuned for the fixed key light).
RAMP_T = (0.3, 0.62, 0.8)


def _rgb(hex_str):
    h = hex_str.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    # Blender ramp colours are scene-linear; convert from sRGB.
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, 1.0)


def toon_material(key):
    name = "M_" + key
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    if key.endswith("_edge") and key not in PALETTE:
        # honed edge: the same metal one band brighter, so a blade reads even in shadow
        _, b0, l0, h0 = PALETTE[key[:-5]]
        PALETTE[key] = (b0, l0, h0 or l0, "#ffffff" if h0 else None)
    shadow, base, light, hi = PALETTE[key]
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:  # Blender 5 always uses nodes
        pass
    nt = mat.node_tree
    nt.nodes.clear()
    diffuse = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.inputs["Color"].default_value = (1, 1, 1, 1)
    to_rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    els[0].position = 0.0
    els[0].color = _rgb(shadow)
    els[1].position = RAMP_T[0]
    els[1].color = _rgb(base)
    e = els.new(RAMP_T[1])
    e.color = _rgb(light)
    if hi:
        e = els.new(RAMP_T[2])
        e.color = _rgb(hi)
    emit = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(diffuse.outputs[0], to_rgb.inputs[0])
    nt.links.new(to_rgb.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs[0], out.inputs["Surface"])
    return mat


def flat_material(key, hex_str):
    """Unlit colour (eyes, glows)."""
    name = "F_" + key
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    nt.nodes.clear()
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = _rgb(hex_str)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(emit.outputs[0], out.inputs["Surface"])
    return mat


# ---------------------------------------------------------------------------
# Small construction kit
# ---------------------------------------------------------------------------

class Builder:
    """Creates objects into one collection, parented to rig pivots."""

    def __init__(self, collection):
        self.col = collection
        self.objects = []

    def _link(self, obj, parent, loc, mat, smooth):
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        self.col.objects.link(obj)
        obj.parent = parent
        obj.location = loc
        if mat is not None:
            obj.data.materials.clear()
            obj.data.materials.append(mat)
        if smooth and obj.type == "MESH":
            for p in obj.data.polygons:
                p.use_smooth = True
        self.objects.append(obj)
        return obj

    def sphere(self, name, parent, loc, scale, mat, seg=12, rings=8, smooth=True):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1.0)
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = scale
        return self._link(obj, parent, loc, mat, smooth)

    def dome(self, name, parent, loc, scale, mat, seg=14, rings=8):
        """Upper half of a sphere (helmets, caps). Open at the bottom."""
        bm_ = bmesh.new()
        bmesh.ops.create_uvsphere(bm_, u_segments=seg, v_segments=rings, radius=1.0)
        bmesh.ops.delete(bm_, geom=[v for v in bm_.verts if v.co.z < -1e-4], context="VERTS")
        mesh = bpy.data.meshes.new(name)
        bm_.to_mesh(mesh)
        bm_.free()
        obj = bpy.data.objects.new(name, mesh)
        obj.scale = scale
        self.col.objects.link(obj)
        return self._link(obj, parent, loc, mat, True)

    def box(self, name, parent, loc, size, mat, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = size
        obj.rotation_euler = rot
        return self._link(obj, parent, loc, mat, False)

    def limb(self, name, parent, start, end, r1, r2, mat, verts=10):
        """Tapered cylinder from start to end (pivot-local coordinates)."""
        start, end = Vector(start), Vector(end)
        d = end - start
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=d.length)
        obj = bpy.context.active_object
        obj.name = name
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = d.normalized().to_track_quat("Z", "Y")
        return self._link(obj, parent, (start + end) / 2, mat, True)

    def disc(self, name, parent, loc, radius, depth, normal, mat, verts=16):
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth)
        obj = bpy.context.active_object
        obj.name = name
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector(normal).normalized().to_track_quat("Z", "Y")
        return self._link(obj, parent, loc, mat, True)

    def torus(self, name, parent, loc, major, minor, normal, mat):
        bpy.ops.mesh.primitive_torus_add(major_segments=16, minor_segments=6,
                                         major_radius=major, minor_radius=minor)
        obj = bpy.context.active_object
        obj.name = name
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector(normal).normalized().to_track_quat("Z", "Y")
        return self._link(obj, parent, loc, mat, True)

    def prism(self, name, parent, loc, profile_xz, thickness, mat, rot=(0, 0, 0)):
        """Extrude a 2D outline (x, z) along Y. Used for blades."""
        mesh = bpy.data.meshes.new(name)
        bm = bmesh.new()
        h = thickness / 2
        front = [bm.verts.new((x, -h, z)) for x, z in profile_xz]
        back = [bm.verts.new((x, h, z)) for x, z in profile_xz]
        bm.faces.new(front)
        bm.faces.new(list(reversed(back)))
        n = len(profile_xz)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((front[i], back[i], back[j], front[j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(name, mesh)
        obj.rotation_euler = rot
        self.col.objects.link(obj)
        return self._link(obj, parent, loc, mat, False)


def pivot(name, parent, loc, collection):
    e = bpy.data.objects.new(name, None)
    collection.objects.link(e)
    e.parent = parent
    e.location = loc
    return e


# ---------------------------------------------------------------------------
# Orc base body
# ---------------------------------------------------------------------------

def build_orc(rig_col, body_col):
    """Chunky orc: huge shoulders and forearms, hunched small head, short legs.

    Returns a dict of named pivots and limb groups for posing/states.
    """
    skin = toon_material("orc_skin")
    leather = toon_material("leather")
    cloth = toon_material("cloth_red")
    ivory = toon_material("ivory")
    hair = toon_material("hair_black")
    blood = toon_material("blood")
    eye = flat_material("eye_red", "#ff2a18")

    b = Builder(body_col)
    root = pivot("root", None, (0, 0, 0), rig_col)
    hips = pivot("hips", root, (0, 0, 0.0), rig_col)
    chest = pivot("chest", hips, (0, 0.0, 0.0), rig_col)
    head = pivot("head", chest, (0, -0.08, 0.785), rig_col)
    head.scale = (1.28, 1.28, 1.28)  # oversized for readability at 32 px

    # torso
    b.box("pelvis", hips, (0, 0.0, 0.40), (0.24, 0.17, 0.09), leather)
    b.box("belt", hips, (0, -0.005, 0.445), (0.27, 0.19, 0.035), leather)
    b.box("buckle", hips, (0, -0.1, 0.445), (0.05, 0.02, 0.04), toon_material("iron"))
    b.box("flap", hips, (0, -0.088, 0.35), (0.11, 0.02, 0.12), cloth)
    b.sphere("belly", chest, (0, -0.01, 0.48), (0.16, 0.125, 0.11), skin)
    b.sphere("chest", chest, (0, 0.0, 0.6), (0.235, 0.155, 0.14), skin)
    b.sphere("hunch", chest, (0, 0.06, 0.68), (0.15, 0.1, 0.07), skin)

    # head (low and forward), jaw, tusks, brow, ears, eyes, topknot
    b.sphere("skull", head, (0, 0, 0.01), (0.08, 0.085, 0.085), skin)
    b.box("jaw", head, (0, -0.055, -0.045), (0.12, 0.07, 0.06), skin)
    b.box("brow", head, (0, -0.072, 0.03), (0.12, 0.03, 0.025), skin)
    for s in (-1, 1):
        b.sphere(f"eye{s}", head, (0.03 * s, -0.08, 0.012), (0.024, 0.012, 0.018), eye, seg=6, rings=4)
        b.limb(f"tusk{s}", head, (0.045 * s, -0.088, -0.045), (0.056 * s, -0.1, 0.012), 0.019, 0.0, ivory, verts=6)
        b.limb(f"ear{s}", head, (0.07 * s, 0.0, 0.015), (0.14 * s, 0.03, 0.05), 0.028, 0.0, skin, verts=6)
    b.sphere("knot", head, (0, 0.075, 0.06), (0.035, 0.035, 0.035), hair, seg=8, rings=5)
    b.limb("tail", head, (0, 0.09, 0.06), (0, 0.13, -0.04), 0.025, 0.008, hair, verts=6)

    rig = {"root": root, "hips": hips, "chest": chest, "head": head,
           "arm": {}, "leg": {}, "hand": {}, "forearm": {}, "stump": {}, "limb_parts": {}}

    # arms: pivot at shoulder, hanging slightly outwards
    for side, s in (("R", -1), ("L", 1)):
        sh = pivot(f"shoulder_{side}", chest, (0.22 * s, 0.01, 0.65), rig_col)
        sh.rotation_euler = (0, -math.radians(6) * s, 0)
        parts = [
            b.sphere(f"delt_{side}", sh, (0.015 * s, 0, 0.0), (0.095, 0.09, 0.085), skin),
            b.limb(f"upper_{side}", sh, (0, 0, -0.03), (0, 0, -0.17), 0.058, 0.052, skin),
            b.limb(f"fore_{side}", sh, (0, 0, -0.17), (0, -0.01, -0.31), 0.066, 0.06, skin),
            b.limb(f"bracer_{side}", sh, (0, 0, -0.22), (0, -0.01, -0.29), 0.071, 0.067, leather),
            b.sphere(f"fist_{side}", sh, (0, -0.01, -0.345), (0.068, 0.068, 0.062), skin),
        ]
        rig["arm"][side] = sh
        rig["hand"][side] = pivot(f"hand_{side}", sh, (0, -0.01, -0.345), rig_col)
        rig["forearm"][side] = pivot(f"forearm_{side}", sh, (0, -0.01, -0.25), rig_col)
        rig["limb_parts"][f"arm_{side}"] = parts
        rig["stump"][f"arm_{side}"] = b.sphere(f"stump_arm_{side}", chest, (0.22 * s, 0.01, 0.63),
                                               (0.07, 0.07, 0.06), blood)

    # legs: pivot at hip
    for side, s in (("R", -1), ("L", 1)):
        hp = pivot(f"hip_{side}", hips, (0.095 * s, 0, 0.38), rig_col)
        parts = [
            b.limb(f"thigh_{side}", hp, (0, 0, 0), (0, 0, -0.18), 0.085, 0.07, skin),
            b.limb(f"shin_{side}", hp, (0, 0, -0.18), (0, 0, -0.33), 0.07, 0.062, leather),
            b.box(f"foot_{side}", hp, (0.005 * s, -0.035, -0.345), (0.1, 0.17, 0.065), leather),
        ]
        rig["leg"][side] = hp
        rig["limb_parts"][f"leg_{side}"] = parts
        rig["stump"][f"leg_{side}"] = b.sphere(f"stump_leg_{side}", hips, (0.095 * s, 0, 0.33),
                                               (0.075, 0.075, 0.05), blood)
    return rig


# ---------------------------------------------------------------------------
# Equipment. Each builder parents into the rig so it follows every pose.
# ---------------------------------------------------------------------------

AXE_BLADE = [(0.0, 0.04), (-0.045, 0.065), (-0.1, 0.1), (-0.13, 0.05),
             (-0.135, -0.015), (-0.12, -0.065), (-0.075, -0.06), (-0.03, -0.022), (0.0, -0.032)]
# the cutting edge: the outer curve of the blade, as a band 2 cm deep
_EDGE = [(-0.1, 0.1), (-0.13, 0.05), (-0.135, -0.015), (-0.12, -0.065)]
AXE_EDGE = _EDGE + [(x + 0.022, z) for x, z in reversed(_EDGE)]


def build_axe(rig, col, tier):
    """One-handed bearded axe. Same silhouette for every tier; only the
    metal changes (bronze -> iron -> steel -> mithril ...)."""
    metal = toon_material(tier)
    wood = toon_material("wood")
    leather = toon_material("leather")
    b = Builder(col)
    tilt = pivot(f"axe_grip_{tier}", rig["hand"]["R"], (0, 0, 0), col)
    # haft runs up out of the fist, leaning slightly forward and in
    tilt.rotation_euler = (math.radians(18), math.radians(-6), 0)
    # The head faces forward (-Y), the way an axe is carried and swung, not out to the side.
    grip = pivot(f"axe_head_{tier}", tilt, (0, 0, 0), col)
    grip.rotation_euler = (0, 0, math.radians(30))
    b.limb("haft", grip, (0, 0, -0.09), (0, 0, 0.37), 0.025, 0.022, wood, verts=8)
    b.limb("wrap", grip, (0, 0, -0.045), (0, 0, 0.045), 0.024, 0.024, leather, verts=8)
    b.sphere("pommel", grip, (0, 0, -0.11), (0.026, 0.026, 0.022), metal, seg=8, rings=5)
    b.box("socket", grip, (0, 0, 0.305), (0.05, 0.045, 0.1), metal)
    b.prism("blade", grip, (-0.02, 0, 0.3), AXE_BLADE, 0.03, metal)
    b.prism("edge", grip, (-0.022, 0, 0.3), AXE_EDGE, 0.036, toon_material(tier + "_edge"))
    b.box("spike", grip, (0.035, 0, 0.305), (0.04, 0.02, 0.03), metal)
    return b.objects


def build_buckler(rig, col, face="wood", rim="iron"):
    """Round strapped buckler on the left forearm, face turned towards the
    camera-forward/outward so it reads as a disc in the SOUTH view."""
    wood = toon_material(face)
    metal = toon_material(rim)
    dark = toon_material("leather")
    b = Builder(col)
    mount = pivot("buckler_mount", rig["forearm"]["L"], (0.075, -0.03, 0.0), col)
    normal = Vector((0.75, -0.66, 0.0)).normalized()
    b.disc("board", mount, (0, 0, 0), 0.125, 0.028, normal, wood, verts=18)
    b.torus("rim", mount, normal * 0.006, 0.125, 0.014, normal, metal)
    b.sphere("boss", mount, normal * 0.02, (0.04, 0.04, 0.04), metal, seg=10, rings=6)
    # two plank seams across the face (visible at 64 px, a hint at 32 px)
    side = normal.cross(Vector((0, 0, 1))).normalized()
    for k in (-1, 1):
        b.limb(f"seam{k}", mount, (side * 0.045 * k) + normal * 0.0145 + Vector((0, 0, -0.11)),
                      (side * 0.045 * k) + normal * 0.0145 + Vector((0, 0, 0.11)), 0.006, 0.006, dark, verts=4)
    return b.objects


def build_helmet(rig, col, metal_key="iron"):
    """Horned war-helm: dome, rim band, nasal guard, bone horns."""
    metal = toon_material(metal_key)
    bone = toon_material("bone")
    b = Builder(col)
    head = rig["head"]
    # brim sits just above the eyes so the face still reads under the helm
    b.dome("dome", head, (0, 0.01, 0.056), (0.094, 0.097, 0.075), metal)
    b.torus("band", head, (0, 0.008, 0.058), 0.093, 0.012, (0, 0, 1), metal)
    b.box("nasal", head, (0, -0.092, 0.03), (0.02, 0.016, 0.05), metal)
    b.box("crest", head, (0, 0.01, 0.13), (0.022, 0.15, 0.03), metal)
    for s in (-1, 1):
        b.limb(f"horn_a{s}", head, (0.085 * s, 0.0, 0.075), (0.14 * s, -0.005, 0.1), 0.03, 0.02, bone, verts=8)
        b.limb(f"horn_b{s}", head, (0.14 * s, -0.005, 0.1), (0.17 * s, -0.02, 0.165), 0.02, 0.0, bone, verts=8)
    return b.objects
