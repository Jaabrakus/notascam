"""Realistic-proportion people for the "real" art style. Runs inside Blender.

Same rig contract as race_models.build_humanoid (root, hips, chest, head, arm/leg
pivots, hands, forearms, stumps, limb_parts), so render_sprites.py and
export_units.py can pose, state and dress these bodies the same way.

Look: about seven and a half heads tall, smooth soft-shaded forms, plain medieval
clothes (linen tunic over trousers, belt, leg wraps, leather shoes, felt cap).
Built from lofted rings in code: no downloaded, traced or extracted assets.

Conventions as blender_models.py: 1 unit = 1 tile, ground z = 0, the model faces
-Y in its south pose, the character's right side is -X.
"""

import math

import bmesh
import bpy

import blender_models as bm

# Base colours ("M_<key>" materials; export_units reads the middle entry).
COLOURS = {
    "real_skin": ("#7a4c38", "#c8916c", "#e6b896", None),
    "real_linen": ("#8a7a5e", "#cdbd98", "#e8dcbc", None),
    "real_trousers": ("#3a3026", "#6a5a46", "#8e7a60", None),
    "real_wraps": ("#5e574a", "#8f8673", "#b2a990", None),
    "real_shoe": ("#24170f", "#4a3020", "#6a4a32", None),
    "real_belt": ("#1e140e", "#3e2a1c", "#5e4430", None),
    "real_cap": ("#4a1812", "#963826", "#c45a3a", None),
    "real_hair": ("#20140c", "#4e3420", "#74523a", None),
    "real_ginger": ("#4a1e0c", "#9a4e22", "#c87a40", None),
    "real_tunic_red": ("#4a1c18", "#8a3a2c", "#b25a44", None),
    "real_apron": ("#2e2016", "#5a4230", "#7e6248", None),
    "real_hood": ("#2c3428", "#56634a", "#7a8a68", None),
    "real_eye": ("#0c0808", "#1a1210", "#2a2018", None),
    "real_blood": ("#4a0a10", "#8a1a18", "#b83a2a", None),
}
bm.PALETTE.update(COLOURS)

# h: height (tiles); w: width scale; head: head scale; tunic/hair: colour keys;
# cap: "cap", "hood" or None; beard: None, "short" or "long".
PEOPLE = {
    "Human": dict(h=0.9, w=1.0, head=1.0, tunic="real_linen", hair="real_hair", cap="cap", beard="short"),
    "Dwarf": dict(h=0.7, w=1.3, head=1.12, tunic="real_tunic_red", hair="real_ginger", cap="hood", beard="long", apron=True),
}

SUBDIV = 1        # subdivision level for sprites; export_units sets 0 (flat low-poly)
SEG = 14          # ring resolution


def _hex_lin(hex_str):
    h = hex_str.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb)


def soft_material(key, rough=0.85, sheen=0.0):
    """Plain painted surface: Principled BSDF in the key's base colour."""
    name = "M_" + key
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    p = mat.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*_hex_lin(bm.PALETTE[key][1]), 1.0)
    p.inputs["Roughness"].default_value = rough
    for k in ("Specular IOR Level", "Specular"):
        if k in p.inputs:
            p.inputs[k].default_value = 0.2
    if sheen and "Sheen Weight" in p.inputs:
        p.inputs["Sheen Weight"].default_value = sheen
    return mat


def _finish(obj, parent, mat, smooth=True, subdiv=None):
    obj.parent = parent
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = smooth
    lvl = SUBDIV if subdiv is None else subdiv
    if lvl:
        m = obj.modifiers.new("subd", "SUBSURF")
        m.levels = m.render_levels = lvl
    return obj


def loft(col, name, parent, rings, mat, seg=None, cap=(True, True), subdiv=None):
    """A smooth body of elliptical rings: (z, rx, ry[, ox, oy]) in parent space."""
    seg = seg or SEG
    me = bpy.data.meshes.new(name)
    b = bmesh.new()
    loops = []
    for r in rings:
        z, rx, ry = r[:3]
        ox, oy = (r[3], r[4]) if len(r) > 3 else (0.0, 0.0)
        loops.append([b.verts.new((ox + rx * math.cos(2 * math.pi * k / seg),
                                   oy + ry * math.sin(2 * math.pi * k / seg), z)) for k in range(seg)])
    for a, c in zip(loops, loops[1:]):
        for k in range(seg):
            b.faces.new((a[k], a[(k + 1) % seg], c[(k + 1) % seg], c[k]))
    if cap[0]:
        b.faces.new(list(reversed(loops[0])) if rings[0][0] < rings[-1][0] else loops[0])
    if cap[1]:
        b.faces.new(loops[-1] if rings[0][0] < rings[-1][0] else list(reversed(loops[-1])))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    b.to_mesh(me)
    b.free()
    obj = bpy.data.objects.new(name, me)
    col.objects.link(obj)
    return _finish(obj, parent, mat, subdiv=subdiv)


def ball(col, name, parent, loc, scale, mat, seg=12, rings=8, subdiv=None):
    me = bpy.data.meshes.new(name)
    b = bmesh.new()
    bmesh.ops.create_uvsphere(b, u_segments=seg, v_segments=rings, radius=1.0)
    b.to_mesh(me)
    b.free()
    obj = bpy.data.objects.new(name, me)
    col.objects.link(obj)
    obj.location = loc
    obj.scale = scale
    return _finish(obj, parent, mat, subdiv=subdiv)


def dome(col, name, parent, loc, scale, mat, cut=0.0, seg=14, rings=8, face=False):
    """Sphere with everything below z = cut (unit sphere space) removed: caps, hair.
    face=True also opens the front below the brow (a hood)."""
    me = bpy.data.meshes.new(name)
    b = bmesh.new()
    bmesh.ops.create_uvsphere(b, u_segments=seg, v_segments=rings, radius=1.0)
    bmesh.ops.delete(b, geom=[v for v in b.verts if v.co.z < cut - 1e-4 or (face and v.co.y < -0.5 and v.co.z < 0.35)], context="VERTS")
    b.to_mesh(me)
    b.free()
    obj = bpy.data.objects.new(name, me)
    col.objects.link(obj)
    obj.location = loc
    obj.scale = scale
    return _finish(obj, parent, mat)


def build_person(rig_col, body_col, p):
    M = soft_material
    skin, linen = M("real_skin", 0.6), M(p["tunic"], 0.9, 0.3)
    trousers, wraps, shoe = M("real_trousers", 0.9, 0.2), M("real_wraps", 0.95, 0.3), M("real_shoe", 0.55)
    belt, hair, eye, blood = M("real_belt", 0.5), M(p["hair"], 0.8, 0.4), M("real_eye", 0.3), M("real_blood", 0.4)
    H, w, hs = p["h"], p["w"], p["head"]
    k = H / 0.9                      # all heights scale with the person
    C = body_col

    root = bm.pivot("root", None, (0, 0, 0), rig_col)
    hips = bm.pivot("hips", root, (0, 0, 0), rig_col)
    chest = bm.pivot("chest", hips, (0, 0, 0), rig_col)
    leg_len = 0.44 * k
    waist = 0.535 * k

    # --- skirt of the tunic (hips) and the upper tunic (chest); the belt hides the seam
    hem = 0.30 * k if not p.get("apron") else 0.27 * k
    loft(C, "pelvis_skirt", hips, [(hem, 0.106 * w, 0.086 * w), (0.40 * k, 0.093 * w, 0.072 * w),
                                   (0.50 * k, 0.081 * w, 0.06 * w), (waist + 0.01, 0.075 * w, 0.056 * w)], linen, cap=(False, True))
    loft(C, "torso", chest, [(waist - 0.01, 0.075 * w, 0.056 * w), (0.60 * k, 0.086 * w, 0.062 * w),
                             (0.665 * k, 0.1 * w, 0.064 * w), (0.70 * k, 0.098 * w, 0.058 * w),
                             (0.725 * k, 0.068 * w, 0.047 * w), (0.74 * k, 0.03, 0.028)], linen)
    loft(C, "belt", hips, [(waist - 0.018 * k, 0.079 * w, 0.06 * w), (waist + 0.016 * k, 0.078 * w, 0.059 * w)], belt, subdiv=0)
    ball(C, "belt_pouch", hips, (-0.07 * w, -0.03 * w, waist - 0.04 * k), (0.022, 0.012, 0.028), belt)
    if p.get("apron"):
        loft(C, "belly_apron", hips, [(hem + 0.01, 0.085 * w, 0.02, 0, -0.062 * w), (waist, 0.07 * w, 0.015, 0, -0.058 * w)],
             M("real_apron", 0.7), seg=10)

    # --- neck and head
    loft(C, "neck_skin", chest, [(0.715 * k, 0.021 * hs, 0.022 * hs), (0.785 * k, 0.019 * hs, 0.02 * hs)], skin, seg=10, cap=(False, False))
    head = bm.pivot("head", chest, (0, -0.004, 0.80 * k), rig_col)
    head.scale = (hs, hs, hs)
    ball(C, "skull", head, (0, 0.002, 0.032), (0.039, 0.046, 0.054), skin)
    ball(C, "jaw", head, (0, -0.008, 0.004), (0.032, 0.037, 0.034), skin)
    ball(C, "nose", head, (0, -0.045, 0.024), (0.007, 0.008, 0.011), skin, seg=8, rings=6)
    for s in (-1, 1):
        ball(C, f"ear{s}", head, (0.039 * s, 0.004, 0.028), (0.007, 0.011, 0.014), skin, seg=8, rings=6)
    eyes = [ball(C, f"eye{s}", head, (0.016 * s, -0.04, 0.036), (0.0065, 0.004, 0.0055), eye, seg=8, rings=6, subdiv=0)
            for s in (-1, 1)]
    ball(C, "hair_back", head, (0, 0.012, 0.03), (0.042, 0.042, 0.05), hair)
    if p.get("beard") == "short":
        ball(C, "beard", head, (0, -0.022, 0.002), (0.034, 0.024, 0.034), hair)
    elif p.get("beard") == "long":
        ball(C, "beard", head, (0, -0.03, -0.02), (0.04, 0.03, 0.058), hair)
        ball(C, "beard_tip", head, (0, -0.036, -0.07), (0.026, 0.02, 0.03), hair)
    if p.get("cap") == "cap":
        capm = M("real_cap", 0.9, 0.4)
        dome(C, "hair_cap", head, (0, 0.006, 0.05), (0.045, 0.052, 0.05), capm, cut=-0.05)
        loft(C, "hair_capband", head, [(0.044, 0.045, 0.052, 0, 0.006), (0.058, 0.047, 0.054, 0, 0.006)], capm, cap=(False, False))
    elif p.get("cap") == "hood":
        hood = M("real_hood", 0.9, 0.4)
        dome(C, "hair_hood", head, (0, 0.01, 0.03), (0.05, 0.056, 0.064), hood, cut=-0.55, face=True)
        loft(C, "torso_mantle", chest, [(0.62 * k, 0.104 * w, 0.072 * w), (0.68 * k, 0.106 * w, 0.07 * w),
                                        (0.72 * k, 0.078 * w, 0.056 * w), (0.75 * k, 0.04, 0.036)], hood, cap=(False, True))
    else:
        dome(C, "hair_top", head, (0, 0.004, 0.04), (0.042, 0.049, 0.05), hair, cut=-0.1)

    rig = {"eyes": eyes, "leg_len": leg_len, "tail": [], "root": root, "hips": hips, "chest": chest, "head": head,
           "arm": {}, "leg": {}, "hand": {}, "forearm": {}, "stump": {}, "limb_parts": {}}

    # --- arms: one shoulder joint each (the rig swings the whole arm)
    for side, s in (("R", -1), ("L", 1)):
        sx = 0.084 * w * s
        sh = bm.pivot(f"shoulder_{side}", chest, (sx, 0.0, 0.70 * k), rig_col)
        out = 0.012 * w * s       # arms hang just clear of the hips
        a = 0.33 * k              # shoulder to the middle of the hand
        parts = [
            loft(C, f"upper_{side}", sh, [(0.016, 0.02 * w, 0.024 * w), (-0.012 * k, 0.031 * w, 0.032 * w, out * 0.1, 0), (-0.08 * k, 0.027 * w, 0.028 * w, out * 0.35, -0.002),
                                          (-0.15 * k, 0.024 * w, 0.025 * w, out * 0.6, -0.004), (-0.25 * k, 0.023 * w, 0.023 * w, out, -0.012)], linen),
            loft(C, f"fore_{side}", sh, [(-0.245 * k, 0.018 * w, 0.018 * w, out, -0.012), (-0.295 * k, 0.016 * w, 0.016 * w, out, -0.016)],
                 skin, seg=10, cap=(False, False)),
            ball(C, f"fist_{side}", sh, (out, -0.018, -a), (0.019 * w, 0.023 * w, 0.03 * k), skin),
        ]
        rig["limb_parts"][f"arm_{side}"] = parts
        rig["stump"][f"arm_{side}"] = ball(C, f"stump_arm_{side}", chest, (sx, 0, 0.685 * k), (0.03, 0.03, 0.026), blood)
        rig["arm"][side] = sh
        rig["hand"][side] = bm.pivot(f"hand_{side}", sh, (out, -0.018, -a), rig_col)
        rig["forearm"][side] = bm.pivot(f"forearm_{side}", sh, (out, -0.014, -0.27 * k), rig_col)

    # --- legs: trousers to the knee, wrapped shins, shoes
    for side, s in (("R", -1), ("L", 1)):
        hx = 0.042 * w * s
        hp = bm.pivot(f"hip_{side}", hips, (hx, 0, leg_len), rig_col)
        L = leg_len
        parts = [
            loft(C, f"thigh_{side}", hp, [(0.03, 0.047 * w, 0.049 * w), (-0.1 * k, 0.041 * w, 0.043 * w),
                                          (-0.205 * k, 0.031 * w, 0.033 * w)], trousers),
            loft(C, f"shin_{side}", hp, [(-0.195 * k, 0.032 * w, 0.034 * w), (-0.27 * k, 0.031 * w, 0.034 * w, 0, 0.006),
                                         (-0.36 * k, 0.022 * w, 0.024 * w), (-L + 0.024, 0.02 * w, 0.021 * w)], wraps),
            ball(C, f"foot_{side}", hp, (0, -0.006 * w, -L + 0.024), (0.024 * w, 0.032 * w, 0.026), shoe),
            ball(C, f"foot_toe_{side}", hp, (0, -0.034 * w, -L + 0.016), (0.021 * w, 0.026 * w, 0.017), shoe),
        ]
        rig["limb_parts"][f"leg_{side}"] = parts
        rig["stump"][f"leg_{side}"] = ball(C, f"stump_leg_{side}", hips, (hx, 0, leg_len - 0.03), (0.034, 0.034, 0.024), blood)
        rig["leg"][side] = hp
    return rig
