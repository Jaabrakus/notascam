"""The playable races in the "real" art style (Lord of the Rings flavour). Runs inside Blender.

Every race keeps what made its original 32 px sprite recognisable (skin colour, eye
colour, ears, horns, tail, the one defining shape) on a realistically proportioned
body in plain, worn, earthy clothes. Gear is drawn as separate overlays.

Same rig contract as race_models.build_humanoid (root, hips, chest, head, arm/leg
pivots, hands, forearms, stumps, limb_parts, eyes, leg_len, tail), so the sprite
renderer and the 3D exporter can pose, state and dress these bodies.

Conventions as blender_models.py: 1 unit = 1 tile, ground z = 0, the model faces
-Y in its south pose, the character's right side is -X. Everything is built from
lofted rings and spheres in code: no downloaded, traced or extracted assets.
"""

import math

import bmesh
import bpy

import blender_models as bm

# (shadow, base, light, glint) like bm.PALETTE; materials use the base colour.
COLOURS = {
    # skins, from the original sprites
    "r_skin_human": ("#7a4c38", "#d6a07a", "#f0c8a0", None),
    "r_skin_dwarf": ("#6a3e30", "#c08a68", "#e0ac88", None),
    "r_skin_elf": ("#0e1030", "#26306e", "#3e4c9c", None),
    "r_skin_orc": ("#16380e", "#3f8a2a", "#6cb040", None),
    "r_skin_goblin": ("#26300c", "#55661e", "#7c8e34", None),
    "r_skin_kobold": ("#3a3008", "#806c1c", "#a8943a", None),
    "r_skin_lizard": ("#0e3a36", "#2a8478", "#56b0a0", None),
    "r_skin_lizard_belly": ("#5a6e3e", "#a8b878", "#ccd8a0", None),
    "r_skin_frog": ("#1e5a10", "#46b02a", "#7ee050", None),
    "r_skin_frog_belly": ("#7a8a3a", "#d0dc8a", "#eef4b8", None),
    "r_bone": ("#7a7466", "#dcd6c4", "#f6f2e6", None),
    "r_skin_zombie": ("#3e0c0c", "#8e2622", "#b8463a", None),
    "r_skin_vampire": ("#6a6070", "#d4ccd8", "#f2ecf4", None),
    "r_skin_demon": ("#3a0606", "#8a1410", "#b8301e", None),
    "r_wing_demon": ("#1e0404", "#4a0c0a", "#6e1a14", None),
    # hair
    "r_hair_brown": ("#20140c", "#4e3420", "#74523a", None),
    "r_hair_ginger": ("#4a1e0c", "#9a4e22", "#c87a40", None),
    "r_hair_silver": ("#4e525e", "#9a9eae", "#d4d8e4", None),
    "r_hair_black": ("#0a0808", "#1e1a1a", "#3a3232", None),
    # cloth and leather: worn, muted, earthy
    "r_linen": ("#8a7a5e", "#c9b994", "#e6dab8", None),
    "r_wool_brown": ("#3a3026", "#64543f", "#8a765a", None),
    "r_wool_red": ("#4a1c18", "#843628", "#ac5640", None),
    "r_wool_dark": ("#16161a", "#2e2e34", "#4a4a52", None),
    "r_elf_robe": ("#1c1428", "#3c2c58", "#5e4a82", None),
    "r_elf_trim": ("#5a4a2a", "#a08a52", "#cdb87e", None),
    "r_rag": ("#2e2418", "#5a4a34", "#7a684c", None),
    "r_leather": ("#24170f", "#4e3422", "#704c32", None),
    "r_leather_dark": ("#120c0a", "#2a1e18", "#463428", None),
    "r_noble_black": ("#0c0a0e", "#1e1a24", "#38303e", None),
    "r_noble_red": ("#3a0608", "#7a1218", "#a8282a", None),
    "r_brass": ("#5a3a14", "#a8822e", "#d8b458", None),
    "r_iron": ("#2c2a2e", "#5c5854", "#8a847c", None),
    "r_dark": ("#0c0808", "#181010", "#2a2018", None),
    "r_eye_white": ("#a0a098", "#ecece4", "#ffffff", None),
    "r_blood": ("#4a0a10", "#8a1a18", "#b83a2a", None),
}
bm.PALETTE.update(COLOURS)
GLOW = {"red": "#ff3018", "yellow": "#f4d020", "white": "#f4f4f0", "dark": None}

# h: height in tiles; w: width; head: head scale; leg/tor/arm: limb length factors;
# hunch: forward lean (degrees); see build_person for the rest.
RACES = {
    "Human": dict(h=0.9, skin="r_skin_human", eyes="dark", face="human", ears="round", hair="r_hair_brown",
                  style="short", outfit="tunic", feet="boots"),
    "Dwarf": dict(h=0.7, w=1.32, head=1.14, leg=0.86, skin="r_skin_dwarf", eyes="dark", face="human", ears="round",
                  hair="r_hair_ginger", style="short", beard="braids", outfit="dwarf", feet="heavy"),
    "Elf": dict(h=0.98, w=0.88, head=0.96, leg=1.06, skin="r_skin_elf", eyes="red", face="human", ears="long",
                hair="r_hair_silver", style="long", outfit="robe", feet="boots"),
    "Orc": dict(h=0.9, w=1.22, head=1.04, hunch=16, arm=1.08, skin="r_skin_orc", eyes="red", face="orc", ears="pointed",
                hair="r_hair_black", style="topknot", outfit="orc", feet="wraps"),
    "Goblin": dict(h=0.62, w=0.9, head=1.42, leg=0.92, hunch=18, arm=1.12, skin="r_skin_goblin", eyes="yellow", face="goblin",
                   ears="goblin", outfit="goblin", feet="bare"),
    "Kobold": dict(h=0.6, w=0.92, head=1.3, hunch=12, skin="r_skin_kobold", eyes="yellow", face="snout", ears="pointed",
                   horns=True, tail="thin", outfit="loin", feet="claws"),
    "Lizardman": dict(h=0.96, w=1.0, head=1.08, hunch=10, skin="r_skin_lizard", belly="r_skin_lizard_belly", eyes="yellow",
                      face="snout", ears=None, tail="thick", outfit="loin", feet="claws"),
    "Frogman": dict(h=0.74, w=1.18, head=1.3, leg=0.9, hunch=8, skin="r_skin_frog", belly="r_skin_frog_belly", eyes="frog",
                    face="frog", ears=None, outfit="loin", feet="webbed"),
    "Skeleton": dict(h=0.9, w=0.86, skin="r_bone", eyes="red", face="skull", ears=None, outfit="bones", feet="bones"),
    "Zombie": dict(h=0.88, w=0.98, hunch=14, skin="r_skin_zombie", eyes="white", face="human", ears="round",
                   hair="r_hair_black", style="ragged", outfit="torn", feet="bare"),
    "Vampire": dict(h=0.95, w=0.94, skin="r_skin_vampire", eyes="red", face="human", ears="pointed", hair="r_hair_black",
                    style="slick", outfit="noble", feet="boots", cape=True),
    "Demon": dict(h=0.98, w=1.12, hunch=6, skin="r_skin_demon", eyes="red", face="orc", tusks=False, ears="pointed",
                  horns="demon", outfit="orc", feet="hooves", tail="thin", wings="r_wing_demon"),
}

SUBDIV = 1        # subdivision level for sprites; the 3D exporter sets 0
HEROIC = (1.12, 1.2)   # width and head scale over true proportions, so bodies read at sprite size
SEG = 14          # ring resolution


# ---------------------------------------------------------------------------
# materials and shapes
# ---------------------------------------------------------------------------

def _hex_lin(hex_str):
    h = hex_str.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb)


def surface_kind(key, metal):
    """What a colour key is made of, for its texture: cloth, leather, skin, hair, scales, bone, metal."""
    if metal >= 0.5:
        return "metal"
    for prefix, kind in (("r_skin_lizard", "scales"), ("r_skin_kobold", "scales"), ("r_c_dragon_wing", "skin"),
                         ("r_c_dragon_belly", "scales"), ("r_c_dragon", "scales"), ("r_c_spider", "chitin"), ("r_wing", "skin"),
                         ("r_skin", "skin"), ("r_hair", "hair"), ("r_leather", "leather"), ("r_bone", "bone"),
                         ("r_brass", "metal"), ("r_iron", "metal"), ("r_dark", "skin"), ("r_eye", "skin"), ("r_blood", "skin")):
        if key.startswith(prefix):
            return kind
    return "cloth"


# texture per kind: (colour noise scale, colour variation, bump texture, bump scale, bump strength, AO distance)
SURFACE = {
    "cloth": (60, 0.10, "noise", 520, 0.22, 0.05),
    "leather": (45, 0.12, "noise", 160, 0.3, 0.04),
    "skin": (30, 0.06, "noise", 220, 0.08, 0.035),
    "hair": (40, 0.14, "wave", 260, 0.45, 0.04),
    "scales": (40, 0.1, "voronoi", 140, 0.45, 0.04),
    "chitin": (30, 0.08, "noise", 90, 0.12, 0.04),
    "bone": (35, 0.08, "noise", 140, 0.15, 0.04),
    "metal": (50, 0.06, "noise", 300, 0.08, 0.03),
}


def soft_material(key, rough=0.85, sheen=0.0, metal=0.0, glow=None):
    """A painted, lightly textured surface in the key's base colour: colour variation, a fine
    bump for weave, grain or scales, and darkening in creases (glow: emissive hex)."""
    name = "M_" + key + ("_glow" if glow else "")
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    N, Lk = nt.nodes, nt.links
    p = N.get("Principled BSDF")
    base = (*_hex_lin(glow or bm.PALETTE[key][1]), 1.0)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    for k in ("Specular IOR Level", "Specular"):
        if k in p.inputs:
            p.inputs[k].default_value = 0.2 if not metal else 0.5
    if sheen and "Sheen Weight" in p.inputs:
        p.inputs["Sheen Weight"].default_value = sheen
    if glow:
        p.inputs["Base Color"].default_value = base
        for k in ("Emission Color", "Emission"):
            if k in p.inputs:
                p.inputs[k].default_value = base
                break
        if "Emission Strength" in p.inputs:
            p.inputs["Emission Strength"].default_value = 2.2
        return mat
    kind = surface_kind(key, metal)
    csc, var, btex, bsc, bstr, aod = SURFACE[kind]
    tc = N.new("ShaderNodeTexCoord")
    # colour variation: base x (1 +- var) from a soft noise
    cn = N.new("ShaderNodeTexNoise")
    cn.inputs["Scale"].default_value = csc
    cn.inputs["Detail"].default_value = 4.0
    Lk.new(tc.outputs["Object"], cn.inputs["Vector"])
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.3, 0.7
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0 - var, 1.0 + var
    Lk.new(cn.outputs["Fac"], mr.inputs["Value"])
    mix = N.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    A = next(i for i in mix.inputs if i.identifier == "A_Color")
    B = next(i for i in mix.inputs if i.identifier == "B_Color")
    A.default_value = base
    Lk.new(mr.outputs["Result"], B)
    out_c = next(o for o in mix.outputs if o.identifier == "Result_Color")
    # creases and contacts darken (Cycles ambient occlusion)
    ao = N.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = aod
    Lk.new(out_c, ao.inputs["Color"])
    Lk.new(ao.outputs["Color"], p.inputs["Base Color"])
    # fine bump: weave, grain, strands or scales
    if btex == "voronoi":
        bt = N.new("ShaderNodeTexVoronoi")
        bt.feature = "DISTANCE_TO_EDGE"
        bt.inputs["Scale"].default_value = bsc
        hgt = bt.outputs["Distance"]
    elif btex == "wave":
        bt = N.new("ShaderNodeTexWave")
        bt.wave_type, bt.bands_direction = "BANDS", "Z"
        bt.inputs["Scale"].default_value = bsc
        bt.inputs["Distortion"].default_value = 6.0
        hgt = bt.outputs["Fac"]
    else:
        bt = N.new("ShaderNodeTexNoise")
        bt.inputs["Scale"].default_value = bsc
        bt.inputs["Detail"].default_value = 2.0
        hgt = bt.outputs["Fac"]
    Lk.new(tc.outputs["Object"], bt.inputs["Vector"])
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bstr
    bump.inputs["Distance"].default_value = 0.002
    Lk.new(hgt, bump.inputs["Height"])
    Lk.new(bump.outputs["Normal"], p.inputs["Normal"])
    if kind == "skin" and "Subsurface Weight" in p.inputs:
        p.inputs["Subsurface Weight"].default_value = 0.12
        if "Subsurface Scale" in p.inputs:
            p.inputs["Subsurface Scale"].default_value = 0.01
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


def loft(col, name, parent, rings, mat, seg=None, cap=(True, True), subdiv=None, loc=(0, 0, 0), rot=None, hem=None):
    """A smooth body of elliptical rings (z, rx, ry[, ox, oy]) along local z.
    rot turns the whole piece (e.g. (90 deg, 0, 0) points it at -Y, forwards).
    hem=(amplitude, folds, rings): cloth folds, strongest on the first ring."""
    seg = seg or (SEG * 2 if hem else SEG)
    me = bpy.data.meshes.new(name)
    b = bmesh.new()
    loops = []
    for i, r in enumerate(rings):
        z, rx, ry = r[:3]
        ox, oy = (r[3], r[4]) if len(r) > 3 else (0.0, 0.0)
        ring = []
        for k in range(seg):
            t = 2 * math.pi * k / seg
            f = 1.0
            if hem and i < hem[2]:
                f += hem[0] * (1 - i / hem[2]) * (math.sin(hem[1] * t + 0.7) * 0.7 + math.sin(hem[1] * 2.3 * t + 2.1) * 0.3)
            ring.append(b.verts.new((ox + rx * f * math.cos(t), oy + ry * f * math.sin(t), z)))
        loops.append(ring)
    for a, c in zip(loops, loops[1:]):
        for k in range(seg):
            b.faces.new((a[k], a[(k + 1) % seg], c[(k + 1) % seg], c[k]))
    if cap[0]:
        b.faces.new(list(reversed(loops[0])))
    if cap[1]:
        b.faces.new(loops[-1])
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    b.to_mesh(me)
    b.free()
    obj = bpy.data.objects.new(name, me)
    col.objects.link(obj)
    obj.location = loc
    if rot:
        obj.rotation_euler = rot
    return _finish(obj, parent, mat, subdiv=subdiv)


def ball(col, name, parent, loc, scale, mat, seg=12, rings=8, subdiv=None, rot=None):
    me = bpy.data.meshes.new(name)
    b = bmesh.new()
    bmesh.ops.create_uvsphere(b, u_segments=seg, v_segments=rings, radius=1.0)
    b.to_mesh(me)
    b.free()
    obj = bpy.data.objects.new(name, me)
    col.objects.link(obj)
    obj.location = loc
    obj.scale = scale
    if rot:
        obj.rotation_euler = rot
    return _finish(obj, parent, mat, subdiv=subdiv)


def dome(col, name, parent, loc, scale, mat, cut=0.0, seg=14, rings=8, face=False):
    """Sphere with everything below z = cut (unit sphere space) removed: caps, hair.
    face=True also opens the front below the brow (hoods, long hair)."""
    me = bpy.data.meshes.new(name)
    b = bmesh.new()
    bmesh.ops.create_uvsphere(b, u_segments=seg, v_segments=rings, radius=1.0)
    bmesh.ops.delete(b, geom=[v for v in b.verts if v.co.z < cut - 1e-4 or (face and v.co.y < -0.45 and v.co.z < 0.35)],
                     context="VERTS")
    b.to_mesh(me)
    b.free()
    obj = bpy.data.objects.new(name, me)
    col.objects.link(obj)
    obj.location = loc
    obj.scale = scale
    return _finish(obj, parent, mat)


def clumps(col, parent, mat, centre, radii, n, size, zmin=0.0, front=False, seed=1):
    """Small lumps scattered over an ellipsoid's surface: tousled hair, beard tufts."""
    import random
    rnd = random.Random(seed)
    made = 0
    while made < n:
        t, u = rnd.uniform(0, 2 * math.pi), rnd.uniform(-1, 1)
        x, y, z = math.sqrt(1 - u * u) * math.cos(t), math.sqrt(1 - u * u) * math.sin(t), u
        if z < zmin or (front and y > -0.2) or (not front and y < -0.55 and z < 0.4):
            continue
        sz = size * rnd.uniform(0.75, 1.25)
        ball(col, f"hair_clump{seed}_{made}", parent, (centre[0] + x * radii[0] * 0.9, centre[1] + y * radii[1] * 0.9, centre[2] + z * radii[2] * 0.9),
             (sz, sz, sz * 1.25), mat, seg=8, rings=6)
        made += 1


def spike(col, name, parent, base, tip, r, mat, bend=(0, 0, 0)):
    """Tapered horn/ear/tusk from base to tip (parent space), optionally bent at the middle."""
    from mathutils import Vector
    a, t = Vector(base), Vector(tip)
    m = (a + t) / 2 + Vector(bend)
    pts = [(a, r), (m, r * 0.55), (t, r * 0.08)]
    me = bpy.data.meshes.new(name)
    b = bmesh.new()
    seg = 8
    loops = []
    for i, (p, rad) in enumerate(pts):
        d = (pts[min(i + 1, 2)][0] - pts[max(i - 1, 0)][0]).normalized()
        q = d.to_track_quat("Z", "Y")
        loops.append([b.verts.new(p + q @ Vector((rad * math.cos(2 * math.pi * k / seg), rad * math.sin(2 * math.pi * k / seg), 0)))
                      for k in range(seg)])
    for x, y in zip(loops, loops[1:]):
        for k in range(seg):
            b.faces.new((x[k], x[(k + 1) % seg], y[(k + 1) % seg], y[k]))
    b.faces.new(list(reversed(loops[0])))
    b.faces.new(loops[-1])
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    b.to_mesh(me)
    b.free()
    obj = bpy.data.objects.new(name, me)
    col.objects.link(obj)
    return _finish(obj, parent, mat)


def tube(col, name, parent, pts, radii, mat, seg=8):
    """A tapering tube through several points (parent space): legs, necks, tails, wing bones."""
    from mathutils import Vector
    P = [Vector(q) for q in pts]
    me = bpy.data.meshes.new(name)
    b = bmesh.new()
    loops = []
    for i, (q, rad) in enumerate(zip(P, radii)):
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        rq = d.to_track_quat("Z", "Y")
        loops.append([b.verts.new(q + rq @ Vector((rad * math.cos(2 * math.pi * k / seg), rad * math.sin(2 * math.pi * k / seg), 0)))
                      for k in range(seg)])
    for x, y in zip(loops, loops[1:]):
        for k in range(seg):
            b.faces.new((x[k], x[(k + 1) % seg], y[(k + 1) % seg], y[k]))
    b.faces.new(list(reversed(loops[0])))
    b.faces.new(loops[-1])
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    b.to_mesh(me)
    b.free()
    obj = bpy.data.objects.new(name, me)
    col.objects.link(obj)
    return _finish(obj, parent, mat)


def membrane(col, name, parent, pts, mat):
    """A flat skin stretched over a fan of points (parent space): wing membranes."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(q) for q in pts], [], [(0, i, i + 1) for i in range(1, len(pts) - 1)])
    obj = bpy.data.objects.new(name, me)
    col.objects.link(obj)
    return _finish(obj, parent, mat, subdiv=0)


def build_wings(C, chest, skin_m, bone_m, w, Zc, span=1.0):
    """Bat wings, half open behind the shoulders, claw tips above the head."""
    for s in (-1, 1):
        A = (0.04 * s, 0.05, Zc(0.24))
        E = (0.17 * s * span, 0.12, Zc(0.36))
        T = (0.25 * s * span, 0.15, Zc(0.47))
        F = [(0.33 * s * span, 0.17, Zc(0.18)), (0.25 * s * span, 0.16, Zc(-0.02)), (0.12 * s * span, 0.11, Zc(-0.06))]
        tube(C, f"wing_arm{s}", chest, [A, E, T], [0.013, 0.011, 0.008], bone_m)
        for i, f in enumerate(F):
            tube(C, f"wing_finger{i}{s}", chest, [T, f], [0.006, 0.003], bone_m, seg=6)
        membrane(C, f"wing_skin{s}", chest, [A, E, T] + F, skin_m)


# ---------------------------------------------------------------------------
# heads
# ---------------------------------------------------------------------------

def build_head(C, head, p, M, skin):
    face, eyes_kind = p["face"], p["eyes"]
    glow = GLOW.get(eyes_kind)
    eye = M("r_dark", 0.3, glow=glow) if glow else M("r_dark", 0.3)
    eyes = []
    if face == "skull":
        bone = skin
        ball(C, "skull", head, (0, 0.004, 0.034), (0.04, 0.046, 0.05), bone)
        ball(C, "jaw", head, (0, -0.014, -0.006), (0.027, 0.03, 0.017), bone)
        for s in (-1, 1):
            ball(C, f"eye_socket{s}", head, (0.015 * s, -0.036, 0.03), (0.012, 0.008, 0.012), M("r_dark", 0.6))
            eyes.append(ball(C, f"eye{s}", head, (0.015 * s, -0.041, 0.03), (0.0055, 0.003, 0.0055), eye, subdiv=0))
        ball(C, "jaw_teeth", head, (0, -0.036, 0.002), (0.02, 0.006, 0.006), bone)
        return eyes
    if face == "frog":
        ball(C, "skull", head, (0, 0.0, 0.016), (0.056, 0.05, 0.034), skin)
        ball(C, "jaw", head, (0, -0.008, -0.004), (0.052, 0.044, 0.02), M(p.get("belly") or p["skin"], 0.6))
        ball(C, "jaw_mouth", head, (0, -0.045, 0.004), (0.04, 0.006, 0.003), M("r_dark", 0.5))
        for s in (-1, 1):
            ball(C, f"brow{s}", head, (0.03 * s, -0.016, 0.044), (0.018, 0.018, 0.016), skin)
            ball(C, f"eye_white{s}", head, (0.03 * s, -0.027, 0.048), (0.012, 0.009, 0.011), M("r_eye_white", 0.3))
            eyes.append(ball(C, f"eye{s}", head, (0.03 * s, -0.035, 0.049), (0.006, 0.003, 0.007), eye, subdiv=0))
        return eyes
    if face == "snout":
        ball(C, "skull", head, (0, 0.012, 0.032), (0.036, 0.044, 0.04), skin)
        loft(C, "snout", head, [(0.0, 0.03, 0.024), (0.03, 0.025, 0.02), (0.055, 0.018, 0.015), (0.062, 0.012, 0.01)],
             skin, loc=(0, -0.018, 0.018), rot=(math.radians(96), 0, 0))
        jawc = M(p.get("belly") or p["skin"], 0.7)
        loft(C, "jaw", head, [(0.0, 0.026, 0.012), (0.05, 0.016, 0.008)], jawc, loc=(0, -0.014, 0.004),
             rot=(math.radians(92), 0, 0), seg=10)
        for s in (-1, 1):
            ball(C, f"brow{s}", head, (0.02 * s, -0.02, 0.046), (0.013, 0.014, 0.01), skin)
            eyes.append(ball(C, f"eye{s}", head, (0.022 * s, -0.026, 0.04), (0.006, 0.005, 0.005), eye, subdiv=0))
        if p.get("horns"):
            for s in (-1, 1):
                spike(C, f"horn{s}", head, (0.018 * s, 0.01, 0.06), (0.03 * s, 0.07, 0.1), 0.011, M("r_bone", 0.5),
                      bend=(0.0, -0.0, 0.025))
        else:   # a crest of scales
            for k in range(3):
                spike(C, f"horn_crest{k}", head, (0, 0.0 + k * 0.022, 0.07 - k * 0.006), (0, 0.016 + k * 0.022, 0.09 - k * 0.008),
                      0.008, skin)
        return eyes
    # human-like heads: human, orc, goblin
    if face == "orc":
        ball(C, "skull", head, (0, 0.006, 0.03), (0.044, 0.048, 0.048), skin)
        ball(C, "jaw", head, (0, -0.016, 0.002), (0.039, 0.036, 0.03), skin)
        ball(C, "brow", head, (0, -0.032, 0.045), (0.036, 0.014, 0.011), skin)
        ball(C, "nose", head, (0, -0.046, 0.026), (0.011, 0.009, 0.01), skin, seg=8, rings=6)
        if p.get("tusks", True):
            for s in (-1, 1):
                spike(C, f"tusk{s}", head, (0.018 * s, -0.042, -0.004), (0.021 * s, -0.048, 0.018), 0.0055, M("r_bone", 0.5))
        ey = (0.017, -0.041, 0.034)
    elif face == "goblin":
        ball(C, "skull", head, (0, 0.006, 0.036), (0.042, 0.046, 0.05), skin)
        ball(C, "jaw", head, (0, -0.012, 0.004), (0.028, 0.03, 0.026), skin)
        spike(C, "nose", head, (0, -0.04, 0.03), (0, -0.07, 0.006), 0.011, skin, bend=(0, -0.006, 0.006))
        ball(C, "jaw_mouth", head, (0, -0.038, 0.0), (0.016, 0.004, 0.003), M("r_dark", 0.5))
        ey = (0.017, -0.039, 0.04)
    else:
        ball(C, "skull", head, (0, 0.002, 0.032), (0.039, 0.046, 0.054), skin)
        ball(C, "jaw", head, (0, -0.008, 0.004), (0.032, 0.037, 0.034), skin)
        ball(C, "nose", head, (0, -0.045, 0.024), (0.007, 0.009, 0.012), skin, seg=8, rings=6)
        ball(C, "brow", head, (0, -0.034, 0.047), (0.026, 0.008, 0.006), skin)
        for s in (-1, 1):
            ball(C, f"jaw_cheek{s}", head, (0.022 * s, -0.03, 0.02), (0.012, 0.01, 0.01), skin)
        ey = (0.016, -0.04, 0.036)
    for s in (-1, 1):
        eyes.append(ball(C, f"eye{s}", head, (ey[0] * s, ey[1], ey[2]), (0.0058, 0.0035, 0.0052 if glow else 0.0042), eye, subdiv=0))
    if p.get("horns") == "demon":
        for s in (-1, 1):
            spike(C, f"horn{s}", head, (0.026 * s, -0.004, 0.064), (0.07 * s, 0.01, 0.13), 0.016, M("r_bone", 0.45),
                  bend=(0.03 * s, 0.0, -0.01))
    ears = p.get("ears")
    for s in (-1, 1):
        if ears == "round":
            ball(C, f"ear{s}", head, (0.039 * s, 0.004, 0.028), (0.007, 0.011, 0.014), skin, seg=8, rings=6)
        elif ears == "pointed":
            spike(C, f"ear{s}", head, (0.036 * s, 0.006, 0.03), (0.07 * s, 0.018, 0.058), 0.013, skin)
        elif ears == "long":
            spike(C, f"ear{s}", head, (0.036 * s, 0.006, 0.03), (0.095 * s, 0.03, 0.07), 0.012, skin)
        elif ears == "goblin":
            spike(C, f"ear{s}", head, (0.036 * s, 0.006, 0.036), (0.11 * s, 0.02, 0.05), 0.022, skin, bend=(0, 0, 0.012))
    return eyes


def build_hair(C, head, chest, p, M, k, waist):
    hair = M(p["hair"], 0.8, 0.4) if p.get("hair") else None
    style = p.get("style")
    if hair and style == "short":
        dome(C, "hair_top", head, (0, 0.004, 0.04), (0.042, 0.049, 0.05), hair, cut=-0.1)
        ball(C, "hair_back", head, (0, 0.014, 0.026), (0.04, 0.038, 0.046), hair)
        clumps(C, head, hair, (0, 0.004, 0.04), (0.044, 0.05, 0.05), 16, 0.009, zmin=0.05, seed=3)
    elif hair and style == "long":
        dome(C, "hair_top", head, (0, 0.004, 0.04), (0.043, 0.05, 0.052), hair, cut=-0.3, face=True)
        clumps(C, head, hair, (0, 0.004, 0.04), (0.045, 0.052, 0.053), 12, 0.009, zmin=0.2, seed=5)
        loft(C, "hair_long", head, [(-0.1, 0.03, 0.014, 0, 0.034), (-0.04, 0.04, 0.02, 0, 0.034), (0.03, 0.042, 0.03, 0, 0.022)],
             hair, cap=(True, False))
    elif hair and style == "topknot":
        ball(C, "hair_knot", head, (0, 0.018, 0.088), (0.014, 0.014, 0.02), hair)
        loft(C, "hair_tail", head, [(-0.03, 0.006, 0.006, 0, 0.05), (0.04, 0.012, 0.012, 0, 0.044), (0.085, 0.012, 0.012, 0, 0.022)], hair)
    elif hair and style == "slick":
        dome(C, "hair_top", head, (0, 0.006, 0.042), (0.041, 0.048, 0.048), hair, cut=-0.15)
        spike(C, "hair_peak", head, (0, -0.03, 0.066), (0, -0.044, 0.05), 0.012, hair)
    elif hair and style == "ragged":
        dome(C, "hair_top", head, (0, 0.008, 0.042), (0.04, 0.046, 0.046), hair, cut=0.1)
        clumps(C, head, hair, (0, 0.008, 0.042), (0.042, 0.048, 0.047), 12, 0.009, zmin=-0.1, seed=9)
    beard = p.get("beard")
    if beard and hair:
        if beard == "short":
            ball(C, "beard", head, (0, -0.022, 0.002), (0.034, 0.024, 0.034), hair)
            clumps(C, head, hair, (0, -0.022, 0.002), (0.035, 0.025, 0.034), 6, 0.01, zmin=-1.0, front=True, seed=13)
        else:
            ball(C, "beard", head, (0, -0.028, -0.012), (0.042, 0.03, 0.05), hair)
            ball(C, "beard_mid", head, (0, -0.036, -0.06), (0.034, 0.024, 0.04), hair)
            ball(C, "beard_mous", head, (0, -0.044, 0.016), (0.026, 0.008, 0.008), hair)
            clumps(C, head, hair, (0, -0.03, -0.03), (0.042, 0.03, 0.06), 10, 0.013, zmin=-1.0, front=True, seed=11)
            if beard == "braids":
                for s in (-1, 1):
                    loft(C, f"beard_braid{s}", head, [(-0.15, 0.007, 0.007, 0.014 * s, -0.04), (-0.08, 0.009, 0.009, 0.016 * s, -0.044),
                                                       (-0.04, 0.011, 0.011, 0.02 * s, -0.04)], hair, seg=8)
                    ball(C, f"beard_bead{s}", head, (0.014 * s, -0.04, -0.13), (0.008, 0.008, 0.01), M("r_brass", 0.4, metal=0.8))


# ---------------------------------------------------------------------------
# the person
# ---------------------------------------------------------------------------

def build_person(rig_col, body_col, p):
    M = soft_material
    C = body_col
    H, w, hs = p["h"], p.get("w", 1.0) * HEROIC[0], p.get("head", 1.0) * HEROIC[1]
    k = H / 0.9
    outfit = p["outfit"]
    skin = M(p["skin"], 0.55 if outfit != "bones" else 0.7)
    belly = M(p["belly"], 0.6) if p.get("belly") else skin
    blood = M("r_blood", 0.4)
    leg_len = 0.44 * k * p.get("leg", 1.0)
    tor = k * (2.0 - p.get("leg", 1.0)) * 0.5 + 0.5 * k   # a shorter leg leaves a longer body
    waist = leg_len + 0.095 * tor
    Zc = lambda z: z * tor + leg_len - waist   # body heights (above the hip joint) -> chest space

    # outfit materials: top (torso), sleeve, skirt, trousers (thigh), shin, foot
    O = {
        "tunic": dict(top=M("r_linen", 0.9, 0.3), sleeve="top", skirt=0.30, legs=M("r_wool_brown", 0.9, 0.2)),
        "dwarf": dict(top=M("r_wool_red", 0.9, 0.3), sleeve="top", skirt=0.25, legs=M("r_wool_dark", 0.9, 0.2)),
        "robe": dict(top=M("r_elf_robe", 0.7, 0.5), sleeve="top", skirt=0.14, legs=M("r_wool_dark", 0.9, 0.2)),
        "orc": dict(top=skin, sleeve=None, skirt=0.33, legs=M("r_leather_dark", 0.8)),
        "goblin": dict(top=M("r_rag", 0.95, 0.2), sleeve=None, skirt=0.36, legs=skin),
        "loin": dict(top=skin, sleeve=None, skirt=0.36, legs=skin),
        "noble": dict(top=M("r_noble_black", 0.6, 0.4), sleeve="top", skirt=0.36, legs=M("r_noble_black", 0.7, 0.3)),
        "torn": dict(top=skin, sleeve=None, skirt=None, legs=M("r_wool_dark", 0.95)),
        "bones": dict(top=skin, sleeve=None, skirt=None, legs=skin),
    }[outfit]
    top, legs = O["top"], O["legs"]
    sleeve = top if O["sleeve"] == "top" else skin
    thin = 0.7 if outfit == "bones" else 1.0

    root = bm.pivot("root", None, (0, 0, 0), rig_col)
    hips = bm.pivot("hips", root, (0, 0, 0), rig_col)
    chest = bm.pivot("chest", hips, (0, 0, waist), rig_col)
    chest.rotation_euler = (math.radians(p.get("hunch", 0)), 0, 0)

    # --- torso
    if outfit == "bones":
        loft(C, "torso_spine", chest, [(Zc(0.05), 0.012, 0.012, 0, 0.02), (Zc(0.3), 0.012, 0.012, 0, 0.02)], skin, seg=8)
        for i in range(4):
            z = Zc(0.17 + i * 0.035)
            r = 0.07 * w - abs(i - 1.2) * 0.006
            loft(C, f"torso_rib{i}", chest, [(z - 0.007, r, r * 0.68), (z + 0.007, r, r * 0.68)], skin, cap=(False, False))
        ball(C, "torso_sternum", chest, (0, -0.045 * w, Zc(0.21)), (0.012, 0.008, 0.05), skin)
        loft(C, "torso_collar", chest, [(Zc(0.28), 0.085 * w, 0.03), (Zc(0.29), 0.085 * w, 0.03)], skin, cap=(False, False))
        ball(C, "pelvis", hips, (0, 0, leg_len + 0.03), (0.06 * w, 0.04, 0.03), skin)
    else:
        wide = 1.12 if outfit in ("orc",) else 1.0
        loft(C, "torso", chest, [(Zc(0.09), 0.075 * w, 0.056 * w), (Zc(0.16), 0.086 * w * wide, 0.062 * w),
                                 (Zc(0.225), 0.1 * w * wide, 0.064 * w), (Zc(0.26), 0.098 * w * wide, 0.058 * w),
                                 (Zc(0.285), 0.068 * w * wide, 0.047 * w), (Zc(0.3), 0.03, 0.028)], top)
        if top is skin and p.get("belly"):
            ball(C, "torso_belly", chest, (0, -0.03 * w, Zc(0.17)), (0.056 * w, 0.034 * w, 0.075 * tor), belly)
        if outfit == "orc":
            for s in (-1, 1):
                ball(C, f"torso_pec{s}", chest, (0.04 * s * w, -0.04 * w, Zc(0.215)), (0.042 * w, 0.026 * w, 0.03), skin)
            strap = M("r_leather", 0.6)
            for s in (-1, 1):   # crossed harness straps
                loft(C, f"torso_strap{s}", chest, [(-0.13, 0.006, 0.004), (0.13, 0.006, 0.004)], strap, seg=6,
                     loc=(0, -0.066 * w, Zc(0.19)), rot=(0, math.radians(40 * s), 0))
            ball(C, "torso_buckle", chest, (0, -0.07 * w, Zc(0.19)), (0.012, 0.006, 0.012), M("r_iron", 0.4, metal=0.8))
        if outfit == "goblin":
            ball(C, "torso_rag_tear", chest, (0.03, -0.05, Zc(0.1)), (0.03, 0.02, 0.025), skin)
        if outfit == "torn":
            for i in range(3):
                loft(C, f"torso_rib{i}", chest, [(Zc(0.17 + i * 0.03) - 0.004, 0.072 * w, 0.058 * w, 0, -0.004),
                                                 (Zc(0.17 + i * 0.03) + 0.004, 0.072 * w, 0.058 * w, 0, -0.004)],
                     M("r_bone", 0.6), cap=(False, False))
        if outfit == "noble":
            trim = M("r_noble_red", 0.6, 0.4)
            loft(C, "torso_trim", chest, [(Zc(0.115), 0.08 * w, 0.06 * w), (Zc(0.13), 0.082 * w, 0.061 * w)], trim, cap=(False, False))
        if outfit == "robe":
            trim = M("r_elf_trim", 0.5, 0.3, metal=0.3)
            loft(C, "torso_trim", chest, [(Zc(0.27), 0.075 * w, 0.052 * w), (Zc(0.29), 0.05 * w, 0.04 * w)], trim, cap=(False, False))

    # --- skirt / kilt / robe below the belt (on the hips, so it stays put when the body leans)
    hem = O["skirt"]
    if hem is not None:
        skirt_m = M("r_leather_dark", 0.8) if outfit == "orc" else M("r_rag", 0.95, 0.2) if outfit in ("goblin", "loin") else top
        if outfit in ("loin",):
            loft(C, "pelvis_loin", hips, [(leg_len + 0.0, 0.07 * w, 0.054 * w), (waist + 0.01, 0.076 * w, 0.057 * w)], skirt_m, cap=(False, True))
            loft(C, "belly_flap", hips, [(hem * k, 0.03 * w, 0.006, 0, -0.054 * w), (waist - 0.01, 0.034 * w, 0.006, 0, -0.056 * w)], skirt_m, seg=8)
        else:
            flare = 1.18 if outfit == "robe" else 1.0
            loft(C, "pelvis_skirt", hips, [(hem * k, 0.106 * w * flare, 0.086 * w * flare), (0.40 * k, 0.093 * w, 0.072 * w),
                                           (leg_len + 0.06 * tor, 0.081 * w, 0.06 * w), (waist + 0.01, 0.075 * w, 0.056 * w)],
                 skirt_m, cap=(False, True), hem=(0.09 if outfit in ("goblin", "orc") else 0.06, 7, 3))
            if outfit == "robe":   # the robe is slit front and back for walking: show it with darker panels
                for s in (-1, 1):
                    ball(C, f"pelvis_slit{s}", hips, (0, 0.09 * s * w, hem * k + 0.05), (0.012, 0.01, 0.06), M("r_wool_dark", 0.9))
    if outfit != "bones":
        bm_ = M("r_leather", 0.5) if outfit not in ("robe", "noble") else M("r_elf_trim" if outfit == "robe" else "r_noble_red", 0.5)
        bw = 1.06 if outfit == "dwarf" else 1.0
        bh = 0.026 if outfit == "dwarf" else 0.017
        loft(C, "belt", hips, [(waist - bh * k, 0.079 * w * bw, 0.06 * w * bw), (waist + bh * k, 0.078 * w * bw, 0.059 * w * bw)], bm_, subdiv=0)
        if outfit in ("tunic", "dwarf", "orc", "noble"):
            ball(C, "belt_buckle", hips, (0, -0.061 * w * bw, waist), (0.013 * bw, 0.005, 0.012 * bw),
                 M("r_brass" if outfit == "dwarf" else "r_iron", 0.35, metal=0.9))
        if outfit in ("tunic", "dwarf", "goblin"):
            ball(C, "belt_pouch", hips, (-0.07 * w, -0.03 * w, waist - 0.04 * k), (0.022, 0.012, 0.028), M("r_leather", 0.6))

    # --- neck and head
    if outfit != "bones":
        loft(C, "neck_skin", chest, [(Zc(0.27), 0.021 * hs, 0.022 * hs), (Zc(0.345), 0.019 * hs, 0.02 * hs)], skin, seg=10, cap=(False, False))
    else:
        loft(C, "neck_spine", chest, [(Zc(0.28), 0.01, 0.01), (Zc(0.35), 0.01, 0.01)], skin, seg=8)
    head = bm.pivot("head", chest, (0, -0.004, Zc(0.36)), rig_col)
    head.scale = (hs, hs, hs)
    head.rotation_euler = (-math.radians(p.get("hunch", 0)) * 0.8, 0, 0)
    eyes = build_head(C, head, p, M, skin)
    build_hair(C, head, chest, p, M, k, waist)

    # --- cape (vampire): high collar, black outside, red lining showing at the edges
    if p.get("cape"):
        cb, cr = M("r_noble_black", 0.7, 0.4), M("r_noble_red", 0.6, 0.4)
        lo = -leg_len + 0.05 - (waist - leg_len)
        loft(C, "torso_cape", chest, [(lo, 0.13 * w, 0.028, 0, 0.085), (Zc(0.0), 0.118 * w, 0.028, 0, 0.078),
                                      (Zc(0.25), 0.1 * w, 0.028, 0, 0.064)], cb, cap=(True, True), hem=(0.12, 5, 2))
        loft(C, "torso_cape_lining", chest, [(lo + 0.01, 0.124 * w, 0.02, 0, 0.07), (Zc(0.24), 0.094 * w, 0.02, 0, 0.052)], cr)
        loft(C, "torso_collar", chest, [(Zc(0.27), 0.068 * w, 0.048, 0, 0.014), (Zc(0.335), 0.08 * w, 0.056, 0, 0.026)], cr, cap=(False, False))

    if p.get("wings"):
        build_wings(C, chest, M(p["wings"], 0.7), M("r_bone", 0.5) if outfit == "bones" else skin, w, Zc)

    rig = {"eyes": eyes, "leg_len": leg_len, "tail": [], "root": root, "hips": hips, "chest": chest, "head": head,
           "arm": {}, "leg": {}, "hand": {}, "forearm": {}, "stump": {}, "limb_parts": {}}

    # --- tail
    if p.get("tail"):
        th = 1.0 if p["tail"] == "thick" else 0.55
        rig["tail"] = [loft(C, "tail", hips, [(0.0, 0.04 * th, 0.034 * th), (0.12, 0.03 * th, 0.026 * th), (0.24, 0.018 * th, 0.016 * th),
                                              (0.34, 0.006, 0.006)], skin, loc=(0, 0.04, leg_len + 0.02), rot=(math.radians(-118), 0, 0))]

    # --- arms: one shoulder joint each (the rig swings the whole arm)
    armf = p.get("arm", 1.0)
    sx_base = 0.084 * w * (1.12 if outfit == "orc" else 1.0) * (0.85 if outfit == "bones" else 1.0)
    for side, s in (("R", -1), ("L", 1)):
        sx = sx_base * s
        sh = bm.pivot(f"shoulder_{side}", chest, (sx, 0.0, Zc(0.26)), rig_col)
        out = 0.012 * w * s
        a = 0.33 * k * armf
        tw = w * thin
        if outfit == "bones":
            parts = [loft(C, f"upper_{side}", sh, [(0.0, 0.017, 0.017), (-a * 0.45, 0.015, 0.015, out * 0.5, 0)], skin, seg=8),
                     ball(C, f"fore_elbow_{side}", sh, (out * 0.5, 0, -a * 0.46), (0.014, 0.014, 0.014), skin),
                     loft(C, f"fore_{side}", sh, [(-a * 0.46, 0.015, 0.015, out * 0.5, 0), (-a * 0.88, 0.014, 0.014, out, -0.014)], skin, seg=8)]
        else:
            sl_end = 0.25 if O["sleeve"] else 0.0
            if O["sleeve"]:
                parts = [loft(C, f"upper_{side}", sh, [(0.016, 0.02 * tw, 0.024 * tw), (-0.012 * k, 0.031 * tw, 0.032 * tw, out * 0.1, 0),
                                                       (-0.08 * k, 0.027 * tw, 0.028 * tw, out * 0.35, -0.002),
                                                       (-0.15 * k * armf, 0.024 * tw, 0.025 * tw, out * 0.6, -0.004),
                                                       (-sl_end * k * armf, 0.023 * tw, 0.023 * tw, out, -0.012)], sleeve)]
                fore_top = sl_end
            else:   # bare arms with some muscle
                mus = 1.25 if outfit == "orc" else 0.85 if outfit == "goblin" else 1.0
                parts = [loft(C, f"upper_{side}", sh, [(0.016, 0.022 * tw * mus, 0.024 * tw * mus),
                                                       (-0.03 * k, 0.03 * tw * mus, 0.031 * tw * mus, out * 0.15, 0),
                                                       (-0.15 * k * armf, 0.02 * tw * mus, 0.022 * tw * mus, out * 0.6, -0.004)], skin)]
                fore_top = 0.14
            fore_m = M("r_leather", 0.6) if outfit == "orc" else skin
            parts.append(loft(C, f"fore_{side}", sh, [(-fore_top * k * armf, 0.021 * tw, 0.021 * tw, out * 0.7, -0.008),
                                                      (-0.25 * k * armf, 0.019 * tw * (1.15 if outfit == "orc" else 1), 0.019 * tw, out, -0.012),
                                                      (-0.295 * k * armf, 0.016 * tw, 0.016 * tw, out, -0.016)], fore_m, seg=10))
        hand = (0.019 * w, 0.023 * w, 0.03 * k) if outfit != "bones" else (0.014, 0.016, 0.024)
        if p["face"] in ("goblin", "snout") or outfit == "orc":
            hand = (hand[0] * 1.2, hand[1] * 1.2, hand[2] * 1.1)
        parts.append(ball(C, f"fist_{side}", sh, (out, -0.018, -a), hand, skin))
        parts.append(ball(C, f"fist_thumb_{side}", sh, (out - 0.011 * s * w, -0.03, -a + 0.008), (hand[0] * 0.42, hand[1] * 0.42, hand[2] * 0.5), skin))
        rig["limb_parts"][f"arm_{side}"] = parts
        rig["stump"][f"arm_{side}"] = ball(C, f"stump_arm_{side}", chest, (sx, 0, Zc(0.245)), (0.03, 0.03, 0.026), blood)
        rig["arm"][side] = sh
        rig["hand"][side] = bm.pivot(f"hand_{side}", sh, (out, -0.018, -a), rig_col)
        rig["forearm"][side] = bm.pivot(f"forearm_{side}", sh, (out, -0.014, -0.27 * k * armf), rig_col)

    # --- legs
    feet = p["feet"]
    for side, s in (("R", -1), ("L", 1)):
        hx = 0.042 * w * s
        hp = bm.pivot(f"hip_{side}", hips, (hx, 0, leg_len), rig_col)
        L = leg_len
        knee = L * 0.47
        tw = w * thin
        if outfit == "bones":
            parts = [loft(C, f"thigh_{side}", hp, [(0.0, 0.02, 0.02), (-knee, 0.017, 0.017)], skin, seg=8),
                     ball(C, f"shin_knee_{side}", hp, (0, -0.004, -knee), (0.017, 0.017, 0.016), skin),
                     loft(C, f"shin_{side}", hp, [(-knee, 0.017, 0.017), (-L + 0.02, 0.015, 0.015)], skin, seg=8)]
        else:
            frog = 1.25 if p["face"] == "frog" else 1.0
            parts = [loft(C, f"thigh_{side}", hp, [(0.03, 0.047 * tw * frog, 0.049 * tw * frog), (-L * 0.23, 0.041 * tw * frog, 0.043 * tw * frog),
                                                   (-knee, 0.031 * tw, 0.033 * tw)], legs)]
            if feet in ("boots", "heavy"):
                shin_m = legs
                boot = M("r_leather", 0.55)
                bt = 1.25 if feet == "heavy" else 1.0
                parts.append(loft(C, f"shin_{side}", hp, [(-knee + 0.005, 0.032 * tw, 0.034 * tw), (-L * 0.62, 0.031 * tw, 0.034 * tw, 0, 0.006)], shin_m, seg=12))
                parts.append(loft(C, f"shin_boot_{side}", hp, [(-L * 0.6, 0.034 * tw * bt, 0.036 * tw * bt, 0, 0.004),
                                                              (-L * 0.8, 0.026 * tw * bt, 0.028 * tw * bt), (-L + 0.03, 0.024 * tw * bt, 0.026 * tw * bt)], boot))
                parts.append(ball(C, f"foot_{side}", hp, (0, -0.008 * w, -L + 0.026), (0.026 * w * bt, 0.034 * w * bt, 0.027), boot))
                parts.append(ball(C, f"foot_toe_{side}", hp, (0, -0.036 * w * bt, -L + 0.017), (0.022 * w * bt, 0.028 * w * bt, 0.018), boot))
            elif feet == "wraps":
                wraps = M("r_rag", 0.95, 0.3)
                parts.append(loft(C, f"shin_{side}", hp, [(-knee + 0.005, 0.032 * tw, 0.034 * tw), (-L * 0.62, 0.031 * tw, 0.034 * tw, 0, 0.006),
                                                          (-L * 0.82, 0.022 * tw, 0.024 * tw), (-L + 0.024, 0.02 * tw, 0.021 * tw)], wraps))
                parts.append(ball(C, f"foot_{side}", hp, (0, -0.012 * w, -L + 0.022), (0.026 * w, 0.042 * w, 0.024), M("r_leather_dark", 0.7)))
            else:   # bare, claws, webbed: skin all the way down, bigger feet
                big = {"bare": 1.15, "claws": 1.2, "webbed": 1.5, "hooves": 0.95}[feet]
                shin_m = legs if outfit == "torn" else skin
                parts.append(loft(C, f"shin_{side}", hp, [(-knee + 0.005, 0.032 * tw, 0.034 * tw), (-L * 0.62, 0.03 * tw, 0.033 * tw, 0, 0.006),
                                                          (-L + 0.03, 0.02 * tw, 0.021 * tw)], shin_m))
                if outfit == "torn":   # ragged trouser ends over bare shins
                    parts.append(loft(C, f"shin_bare_{side}", hp, [(-L * 0.7, 0.022 * tw, 0.023 * tw), (-L + 0.026, 0.019 * tw, 0.02 * tw)], skin, seg=10))
                if feet == "hooves":
                    parts.append(loft(C, f"foot_{side}", hp, [(-L, 0.024 * w, 0.026 * w, 0, -0.008), (-L + 0.035, 0.02 * w, 0.022 * w, 0, -0.004)],
                                      M("r_dark", 0.4), seg=10))
                else:
                    parts.append(ball(C, f"foot_{side}", hp, (0, -0.02 * w, -L + 0.016), (0.026 * w * big, 0.046 * w * big, 0.018), skin))
                if feet in ("claws", "webbed"):
                    for t in (-1, 0, 1):
                        parts.append(spike(C, f"foot_claw{t}_{side}", hp, (0.012 * t * big, -0.05 * w * big, -L + 0.012),
                                           (0.018 * t * big, -0.075 * w * big, -L + 0.004), 0.006 * big,
                                           M("r_bone", 0.5) if feet == "claws" else skin))
        rig["limb_parts"][f"leg_{side}"] = parts
        rig["stump"][f"leg_{side}"] = ball(C, f"stump_leg_{side}", hips, (hx, 0, leg_len - 0.03), (0.034, 0.034, 0.024), blood)
        rig["leg"][side] = hp
    return rig
