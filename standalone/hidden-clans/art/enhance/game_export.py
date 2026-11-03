#!/usr/bin/env python3
"""Put the enhanced 64 px races and the wearables catalogue into the game.

    python3 standalone/remastered/art/enhance/game_export.py [--only Human,Dwarves] [--no-old]

Writes, under game/:
  Icons/Remastered/Races64/<sheet>.dmi      enhanced bodies: every state, frame and facing of the
                                            race's original sheet, at 64 px (remaster64.py)
  Icons/Remastered/Gear64/<sheet>/<group>.dmi  every wearable fitted to that body, 64 px (what the
                                            3D view draws): the new catalogue items by tier, and
                                            the game's own gear (old-<icon>.dmi, same state names
                                            as the original), each in the original's three walk
                                            frames per facing, weapons and staffs also in an
                                            attack's wind-up and strike (frames 4 and 5); the
                                            game's own looks laid over a body (old-Female.dmi,
                                            old-Hair.dmi, old-Beards.dmi); and the magic items'
                                            animated effects (fx.dmi, fx_cells)
  Icons/Remastered/Gear/<group>.dmi         the new items at 32 px on the original body: their
                                            2D overlay and their inventory/ground picture
  Code/Remastered/GearData.dm               item types and recipe data from art/enhance/catalogue.json

Everything is read from the game's own icons (read only) and art/enhance/catalogue.json.
"""

import argparse
import json
import math
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "pipeline"))
import remaster64 as rm  # noqa: E402
import wearables64 as w  # noqa: E402
import mouths64 as mouths  # noqa: E402
from build_dmi import write_dmi  # noqa: E402

GAME = rm.GAME
OUT_RACES = os.path.join(GAME, "Icons", "Remastered", "Races64")
OUT_GEAR64 = os.path.join(GAME, "Icons", "Remastered", "Gear64")
OUT_GEAR = os.path.join(GAME, "Icons", "Remastered", "Gear")
OUT_DM = os.path.join(GAME, "Code", "Remastered", "GearData.dm")

# Races64 sheet (named as View3D.dm's remaster_3d_races64), the original sheet its states
# come from, and the race as wearables64 fits gear to it. Dwarves play with Human.dmi in the
# original; their sheet is Human's states in Dwarf.dmi's colours and rows, dwarf-shaped.
# A gargoyle's eyes: the original's dark dots (old) redrawn as a glowing glare, slanted down
# towards the nose, in one of three colours (Gear.dm picks one for each gargoyle):
# <sheet>-<colour>.dmi. Colours: (core, rim).
GARGOYLE_EYES = dict(old=(49, 49, 49), variants={"Amber": ((255, 226, 120), (232, 130, 24)),
                                                  "Red": ((255, 120, 90), (210, 20, 10)),
                                                  "Ice": ((210, 245, 255), (60, 150, 230))})
# Eye shapes: (dx, dy, part) for the viewer's left eye from the old eye's corner (the right one
# mirrored), and the eye in profile; part 0 the rim, 1 the glowing core, 2 a pupil.
EYE_SHAPES = {
    "glare": ([(0, 0, 0), (1, 0, 0), (1, 1, 1), (2, 1, 1), (3, 1, 1), (3, 2, 0), (4, 2, 0)],   # slanted down to the nose
              [(0, 0, 0), (1, 1, 1), (2, 1, 1), (3, 2, 0)]),
    "slit": ([(0, 0, 0), (1, 1, 0), (2, 1, 1), (3, 1, 0), (4, 2, 0)],                         # thin, a pinpoint of light
             [(0, 0, 0), (1, 1, 1), (2, 1, 0)]),
    "cat": ([(1, 0, 0), (2, 0, 2), (3, 0, 0), (0, 1, 0), (1, 1, 1), (2, 1, 2), (3, 1, 1), (4, 1, 0), (1, 2, 0), (2, 2, 2), (3, 2, 0)],
            [(0, 0, 0), (1, 0, 0), (0, 1, 1), (1, 1, 2), (2, 1, 1)]),                       # an almond with a slit pupil
}

# Vampires and demons: the original's red dots as cat's eyes, a vampire's red, a demon's
# yellow, both with a slit pupil (one look, in the sheet itself: cols, not variants).
VAMPIRE_EYES = dict(old=(255, 0, 0), shape="cat", cols=((236, 40, 40), (140, 0, 14), (20, 0, 0)))
DEMON_EYES = dict(old=(255, 0, 0), shape="cat", cols=((255, 226, 70), (226, 128, 16), (24, 0, 0)))

SHEETS = [
    dict(sheet="Human", src="Human.dmi", race=("Human", "Human.dmi", "", "standard", None), mouth=dict(style="small", front=17, width=6)),
    dict(sheet="HumanBlack", src="HumanBlack.dmi", race=("Human", "HumanBlack.dmi", "", "standard", None), gear=False,
         mouth=dict(style="small", front=17, width=6)),
    dict(sheet="Dwarves", src="Human.dmi", race=("Dwarf", "Dwarf.dmi", "", "dwarf", "Brown"), recolour="Dwarf.dmi",
         mouth=dict(style="small", front=16, width=6)),
    dict(sheet="Night Elf", src="Night Elf.dmi", race=("Elf", "Night Elf.dmi", "Normal", "tall", None), mouth=dict(style="smirk", front=19)),
    dict(sheet="Orc", src="Orc.dmi", race=("Orc", "Orc.dmi", "Normal", "orc", None), mouth=dict(style="orc", front=17, side=19)),
    dict(sheet="Goblins", src="Goblins.dmi", race=("Goblin", "Goblins.dmi", "", "goblin", None), mouth=dict(style="goblin", front=18)),
    dict(sheet="Kobold", src="Kobold.dmi", race=("Kobold", "Kobold.dmi", "Normal", "goblin", None), mouth=dict(style="kobold", front=22)),
    dict(sheet="LizardMan", src="LizardMan.dmi", race=("Lizardman", "LizardMan.dmi", "", "standard", None), mouth=dict(style="lizard", front=17)),
    dict(sheet="FrogMan", src="FrogMan.dmi", race=("Frogman", "FrogMan.dmi", "", "frog", None), mouth=dict(style="frog", front=15, side=18)),
    dict(sheet="Skeleton", src="Skeleton.dmi", race=("Skeleton", "Skeleton.dmi", "Normal", "standard", None)),   # its jaw's own teeth
    dict(sheet="DevourerZombie", src="DevourerZombie.dmi", race=("Zombie", "DevourerZombie.dmi", "", "standard", None), mouth=dict(style="zombie", front=17)),
    dict(sheet="Vampire", src="Vampire.dmi", race=("Vampire", "Vampire.dmi", "", "tall", None), mouth=dict(style="vampire", front=19), eyes=VAMPIRE_EYES),
    dict(sheet="Demon", src="Demon.dmi", race=("Demon", "Demon.dmi", "", "demon", None), mouth=dict(style="demon", front=23, side=22), eyes=DEMON_EYES),
    dict(sheet="Gargoyle", src="Gargoyle.dmi", race=("Gargoyle", "Gargoyle.dmi", "", "standard", None), mouth=dict(style="gargoyle", front=19, side=20),
         eyes=GARGOYLE_EYES),
    # Flying (Fly() puts these on): the race's own body with its wings spread, two wing beats a facing.
    # Gear.dm fits their gear as on the race's walking body. The wings rise over the head and
    # beat, so their mouths are placed from the head's top (head=True), not the picture's.
    dict(sheet="VampireFly", src="Fly.dmi", race=("Vampire", "Fly.dmi", "", "tall", None), gear=False, mouth=dict(style="vampire", front=17, head=True),
         eyes=VAMPIRE_EYES),
    dict(sheet="DemonFly", src="Fly2.dmi", race=("Demon", "Fly2.dmi", "", "demon", None), gear=False, mouth=dict(style="demon", front=17, side=18, head=True),
         eyes=DEMON_EYES),
    dict(sheet="GargoyleFly", src="Fly3.dmi", race=("Gargoyle", "Fly3.dmi", "", "standard", None), gear=False, mouth=dict(style="gargoyle", front=17, side=20, head=True),
         eyes=GARGOYLE_EYES),
]

SKILLVAR = {"Smithing": "MetalCraftingSkill", "Leatherwork": "LeatherCraftingSkill", "Bone craft": "BoneCraftingSkill",
            "Woodwork": "WoodCraftingSkill", "Gem cutting": "JewlCraftingSkill", "Attack": "AttackSkill",
            "Defence": "DefenceSkill", "Magic": "MagicSkill", "Mining": "MineingSkill"}
STATION = {"Forge": "forge", "Forge, then Gem cutter": "forge", "Forge beside lava": "forge", "Bone crafting": "bone",
           "Leatherworks": "leather", "Carpentry": "carpentry", "Gem cutter, beside a powered rune circuit": "gem"}
WEAPON_PARENT = {"arming sword": "Swords", "longsword": "Swords", "scimitar": "Swords", "dagger": "Daggers",
                 "hand axe": "Axes", "battle axe": "Axes", "warhammer": "Maces", "mace": "Maces", "morning star": "Maces",
                 "spear": "Spears", "halberd": "Spears", "pickaxe": "Picks", "bow": "Bows"}
ARMOUR_PARENT = {"helmet": "Helmet", "chest": "Chestplate", "legs": "Leggings", "shield": "Shield"}
GROUP_NAMES = {"cloth": "Cloth", "magic": "Magic"}
DIRS4 = rm.DIRS


# ---------------------------------------------------------------------------
# DMI reading with metadata
# ---------------------------------------------------------------------------

def read_dmi_full(path):
    """[(state, meta, cells)] in file order; cells frame-major then dir, RGBA arrays."""
    im = Image.open(path)
    desc = im.info["Description"]
    wd = int(re.search(r"\twidth = (\d+)", desc).group(1))
    ht = int(re.search(r"\theight = (\d+)", desc).group(1))
    sheet = np.asarray(im.convert("RGBA"))
    cols = sheet.shape[1] // wd
    out, idx = [], 0
    for m in re.finditer(r'state = "([^"]*)"\n((?:\t.*\n)*)', desc):
        meta = dict(re.findall(r"\t(\w+) = (.*)", m.group(2)))
        dirs, frames = int(meta.get("dirs", 1)), int(meta.get("frames", 1))
        cells = []
        for i in range(idx, idx + dirs * frames):
            y, x = divmod(i, cols)
            cells.append(sheet[y * ht:(y + 1) * ht, x * wd:(x + 1) * wd].copy())
        out.append((m.group(1), meta, cells))
        idx += dirs * frames
    return out


def write_sheet(path, states, size):
    """states: [(name, meta, cells)] -> a DMI of `size` px cells, metadata as given."""
    cells = [c for _, _, cs in states for c in cs]
    cols = max(1, math.ceil(math.sqrt(len(cells))))
    rows = max(1, math.ceil(len(cells) / cols))
    out = np.zeros((rows * size, cols * size, 4), np.uint8)
    for i, c in enumerate(cells):
        y, x = divmod(i, cols)
        out[y * size:(y + 1) * size, x * size:(x + 1) * size] = c
    lines = ["# BEGIN DMI", "version = 4.0", f"\twidth = {size}", f"\theight = {size}"]
    for name, meta, _ in states:
        lines.append(f'state = "{name}"')
        for k in ("dirs", "frames", "delay", "loop", "rewind", "movement", "hotspot"):
            if k in meta:
                lines.append(f"\t{k} = {meta[k]}")
    lines.append("# END DMI")
    write_dmi(path, out, "\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# bodies
# ---------------------------------------------------------------------------

def colour_map(src_cell, dst_cell, src_rows):
    """For each colour of src, the colour dst has in the same place (rows aligned). Whites and
    greys keep their own colour: they are the eyes, which Dwarf.dmi draws red (the game's own
    dwarves play with Human.dmi's eyes)."""
    a, b = rm.rgba(src_cell), rm.rgba(dst_cell)
    votes = {}
    for j, i in enumerate(src_rows):
        if i < 0:
            continue
        for x in range(a.shape[1]):
            if a[i, x, 3] and b[j, x, 3]:
                k = tuple(a[i, x, :3])
                v = tuple(b[j, x, :3])
                votes.setdefault(k, {}).setdefault(v, 0)
                votes[k][v] += 1
    grey = lambda c: max(c) > 60 and max(c) - min(c) < 0.1 * max(c)
    return {k: (k if grey(k) else max(v, key=v.get)) for k, v in votes.items()}


def arr_rgba(cell):
    """A numpy RGBA cell with binary alpha (as remaster64.rgba does for images)."""
    a = np.array(cell, np.uint8, copy=True)
    a[a[..., 3] < 128] = 0
    a[a[..., 3] > 0, 3] = 255
    return a


def recolour(cell, cmap):
    a = arr_rgba(cell)
    out = a.copy()
    for k, v in cmap.items():
        m = (a[..., 3] > 0) & np.all(a[..., :3] == np.array(k, np.uint8), axis=-1)
        out[m, :3] = v
    return out


def sheet_rows(spec):
    """(colour map, rows per facing) a recoloured sheet's cells go through, else (None, {})."""
    cmap, rows = None, {}
    if spec.get("recolour"):
        human = rm.read_dmi(os.path.join(rm.ICONS, "Human.dmi"))[""]
        target = rm.read_dmi(os.path.join(rm.ICONS, spec["recolour"]))[""]
        for i, d in enumerate(DIRS4):
            rows[d] = rm.row_map(human[i], target[i])
        cmap = colour_map(human[0], target[0], rows["S"])
    return cmap, rows


def body64(a, d, side, kind, cmap, rows):
    """One 32 px body cell (binary alpha, already recoloured) at 64 px, before its outline."""
    body = rm.form_light(rm.scale2x(a))
    if cmap:
        body = rm.register(body, rows[d])
    return rm.reshape(body, kind, side)


def head_top(c64, span):
    """Where the head's top is in a flyer's frame: `span` rows above its feet (its wings rise over
    the head and, beating, cover it, but the body keeps its height)."""
    ys = np.flatnonzero((c64[:, 20:44, 3] > 0).any(1))
    return int(ys.max()) - span if len(ys) else None


def head_span(c64):
    """Feet to the top of the head in a standing front view (the middle columns, between the wings)."""
    mid = np.flatnonzero((c64[:, 26:38, 3] > 0).any(1))
    body = np.flatnonzero((c64[:, 20:44, 3] > 0).any(1))
    return int(body.max() - mid.min())


def glare_eyes(c64, d, span, old, cols, shape="glare"):
    """The old eyes (colour `old`, on the face) painted out and new ones drawn in their place:
    `shape` from EYE_SHAPES, cols (core, rim[, pupil])."""
    if d == "N":
        return c64
    ht = head_top(c64, span)
    if ht is None:
        return c64
    pts = [(y, x) for y in range(max(0, ht + 6), min(64, ht + 18)) for x in range(18, 46)
           if c64[y, x, 3] and tuple(int(v) for v in c64[y, x, :3]) == old]
    if not pts:
        return c64
    a = c64.copy()
    for y, x in pts:   # painted out with the face beside them
        k = x - 1
        while k > 0 and tuple(int(v) for v in c64[y, k, :3]) == old:
            k -= 1
        a[y, x, :3] = c64[y, k, :3]
    ys, xs = [p[0] for p in pts], [p[1] for p in pts]
    y0 = min(ys)
    front, side = EYE_SHAPES[shape]
    def put(x, y, part):
        if 0 <= x < 64 and 0 <= y < 64:
            a[y, x, :3] = (cols[1], cols[0], cols[2] if len(cols) > 2 else (0, 0, 0))[part]
    if d in ("E", "W"):
        fwd = 1 if d == "E" else -1
        x0 = min(xs) if fwd > 0 else max(xs)
        for dx, dy, part in side:
            put(x0 + dx * fwd, y0 + dy, part)
        return a
    cx = (min(xs) + max(xs)) / 2.0
    lx0 = min(x for x in xs if x < cx) - 1
    rx1 = max(x for x in xs if x > cx) + 1
    for dx, dy, part in front:
        put(lx0 + dx, y0 + dy, part)
        put(rx1 - dx, y0 + dy, part)
    return a


def eye_sheets(spec, states):
    """{colour: states} with the eyes redrawn (spec["eyes"] variants), or {}; with eyes["cols"]
    instead, {None: states} (the sheet's own eyes)."""
    e = spec.get("eyes")
    if not e:
        return {}
    if "cols" in e:
        e = dict(e, variants={None: e["cols"]})
    first = next(cells for _, meta, cells in states if int(meta.get("dirs", 1)) == 4)
    span = head_span(first[0])
    out = {}
    for colour, cols in e["variants"].items():
        new = []
        for name, meta, cells in states:
            dirs = int(meta.get("dirs", 1))
            cs = []
            for k, c in enumerate(cells):
                d = DIRS4[k % dirs] if dirs in (4, 8) and k % dirs < 4 else "S"
                bubble = "Sleep" in name and k // dirs > 0
                cs.append(c if bubble else glare_eyes(c, d, span, e["old"], cols, e.get("shape", "glare")))
            new.append((name, meta, cs))
        out[colour] = new
    return out


def body_sheet(spec):
    """The race's every state at 64 px, enhanced and shaped (for Races64). Beards, hair and a
    woman's top are laid over it per unit, as in the original (look_sheets)."""
    name, f, st, kind, beard = spec["race"]
    src = read_dmi_full(os.path.join(rm.ICONS, spec["src"]))
    cmap, rows = sheet_rows(spec)
    states = []
    span = None
    for sname, meta, cells in src:
        dirs, frames = int(meta.get("dirs", 1)), int(meta.get("frames", 1))
        out = []
        for k, cell in enumerate(cells):
            fr, di = divmod(k, dirs)
            d = DIRS4[di] if dirs in (4, 8) and di < 4 else "S"
            side = d in ("E", "W")
            raw = np.asarray(cell)
            alpha_level = int(np.median(raw[..., 3][raw[..., 3] > 0])) if (raw[..., 3] > 0).any() else 255
            a = recolour(cell, cmap) if cmap else arr_rgba(cell)
            if not (a[..., 3] > 0).any():
                out.append(np.zeros((64, 64, 4), np.uint8))
                continue
            bubble = "Sleep" in sname and fr > 0
            if bubble or (dirs == 8 and di >= 4):
                c64 = rm.outline(rm.scale2x(a))
            else:
                c64 = rm.outline(rm.comp(body64(a, d, side, kind, cmap, rows)))
                m = spec.get("mouth")   # the race's own mouth (mouths64.py); rows below the sprite's top
                if m and dirs in (4, 8) and di < 4:
                    if m.get("head") and span is None:
                        span = head_span(c64)   # the first cell: standing, facing south
                    top = head_top(c64, span) if m.get("head") else None
                    if d == "S":
                        c64 = mouths.front(c64, m["style"], m["front"], m.get("width", 6), top=top)
                    elif d in ("E", "W") and "side" in m:
                        c64 = mouths.side(c64, m["style"], m["side"], 1 if d == "E" else -1, top=top)
            if alpha_level < 250:   # see-through states (a kobold sneaking) stay see-through
                c64[..., 3] = (c64[..., 3].astype(np.int32) * alpha_level // 255).astype(np.uint8)
            out.append(c64)
        states.append((sname, meta, out))
    return states


# The game's own looks laid over a body (OverlayBuilds.dm RebuildOverlays): a woman's top
# ("Unders" for Humans, Dwarves and Elves, "Shirt" for the rest), hair (women of every
# race that has it, and every elf), a dwarf's beard.
LOOKS = [("Female.dmi", ("Unders", "Shirt")), ("Hair.dmi", ("ElfMale", "ElfFemale", "HumanBrown", "HumanBlack")),
         ("Beards.dmi", ("Grey", "Black", "Brown"))]
WALK = 3   # the original walks in three frames per facing


def look_layer(fname, a, d, side, kind, rows, body=None, length=None):
    """One 32 px look cell drawn as the body's cells are, at 64 px. A dwarf's beard seen from
    the side is drawn anew on `body` (profile_beard), `length` rows long like the front view's."""
    big = rm.scale2x(a)
    layer = rm.form_light(big)
    if fname == "Beards.dmi":
        if kind == "dwarf" and side and body is not None and length:
            return profile_beard(a, rm.fit(layer, kind, side, rows.get(d), head=True), body, d, length)
        if kind == "dwarf":
            layer = rm.long_beard(layer, 9)
        return rm.fit(rm.strands(layer), kind, side, rows.get(d), head=True)
    if fname == "Hair.dmi":   # the hair texture, on the hair only (not an elf's face)
        bare = (big[..., None, :3] == ELF_FACE[None, None]).all(-1).any(-1)
        layer = np.where(bare[..., None], layer, rm.strands(layer))
    return rm.fit(layer, kind, side, rows.get(d))


def profile_beard(a, placed, body, d, length):
    """A dwarf's beard seen from the side (the original's side view is a band across the
    face, which at 64 px reads as a blob): it covers the jaw from the ear to the chin, then
    hangs down the front of the chest to a point. a: the original 32 px cell (its colours);
    placed: that cell fitted to the body (where the jaw is); body: the 64 px body."""
    al = placed[..., 3] > 0
    out = np.zeros((64, 64, 4), np.uint8)
    if not al.any():
        return out
    src = a[a[..., 3] > 0][:, :3]
    shades = np.unique(src, axis=0)
    shades = shades[np.argsort(shades @ np.array([0.3, 0.59, 0.11]))]
    colour = shades[len(shades) // 2]
    fwd = 1 if d == "E" else -1
    m = body[..., 3] > 0
    top = int(np.nonzero(al)[0].min())
    bottom = min(62, top + length - 1)
    head = [y for y in range(int(np.flatnonzero(m.any(1)).min()), top) if m[y].any()]
    ear = int(round(np.mean([(np.flatnonzero(m[y]).min() + np.flatnonzero(m[y]).max()) / 2 for y in head])))
    jaw = 4
    for y in range(top, bottom + 1):
        xs = np.flatnonzero(m[y])
        if not len(xs):
            continue
        front = (xs.max() if fwd > 0 else xs.min()) + fwd     # just in front of face and chest
        if y < top + jaw:
            x0, x1 = sorted((ear, front))
        else:
            u = (y - top - jaw) / max(1, bottom - top - jaw)
            tip = front - fwd * int(round(2 * u))                # the point tucks in a little
            x0, x1 = sorted((tip, tip - fwd * max(1, int(round(9 * (1 - u) ** 0.9)))))
        out[y, x0:x1 + 1, :3] = colour
        out[y, x0:x1 + 1, 3] = 255
    return rm.strands(rm.form_light(out))


# Hair.dmi's ElfMale and ElfFemale draw the elf's whole head: these are its face (skin, eye
# whites, blue eyes), which keeps its look; only the hair gets the hair texture.
ELF_FACE = np.array([(247, 204, 132), (250, 252, 252), (51, 51, 255)])


def look_sheets(spec):
    """{file: [(state, meta, cells)]}: each look fitted to this sheet's 64 px body for every walk
    frame and facing. A cell holds what drawing the look into the body adds (its pixels and the
    outline it grows), so laid over the body it looks drawn in, as on the original sprite."""
    name, f, st, kind, beard = spec["race"]
    src = {s: c for s, _, c in read_dmi_full(os.path.join(rm.ICONS, spec["src"]))}
    stand = src[st]
    cmap, rows = sheet_rows(spec)
    out = {}
    for fname, states in LOOKS:
        dmi = {s: c for s, _, c in read_dmi_full(os.path.join(rm.CREATURE_ICONS, fname))}
        for state in states:
            cells = []
            for fr in range(WALK):
                length = None
                for di, d in enumerate(DIRS4):
                    side = d in ("E", "W")
                    k = fr * 4 + di if len(stand) >= (fr + 1) * 4 else di
                    a = recolour(stand[k], cmap) if cmap else arr_rgba(stand[k])
                    body = body64(a, d, side, kind, cmap, rows)
                    look = arr_rgba(dmi[state][fr * 4 + di if len(dmi[state]) >= (fr + 1) * 4 else di])
                    layer = look_layer(fname, look, d, side, kind, rows, body, length)
                    if d == "S":   # the front view's length, for a side view drawn anew
                        ys = np.flatnonzero((layer[..., 3] > 0).any(1))
                        length = int(ys.max() - ys.min() + 1) if len(ys) else None
                    base, drawn = rm.outline(rm.comp(body)), rm.outline(rm.comp(body, layer))
                    if fname == "Hair.dmi" and state.startswith("Elf") and spec["sheet"] == "Human" and d == "S":
                        # the elf's face comes with its hair: its mouth, a fine line (row as the human's)
                        drawn = mouths.front(drawn, "small", 17, width=4, top=mouths.top_of(base))
                    added = (drawn != base).any(-1)
                    cells.append(np.where(added[..., None], drawn, 0).astype(np.uint8))
            out.setdefault(fname, []).append((state, walk_meta(WALK), cells))
    return out


def walk_meta(frames):
    return {"dirs": "4", "frames": str(frames), "delay": ",".join(["1"] * frames)}


# ---------------------------------------------------------------------------
# gear
# ---------------------------------------------------------------------------

def parse_old_gear():
    """(icon, state, ItemType) of every original wearable in Items/Equipment Lists.dm."""
    path = os.path.join(GAME, "Code", "Items", "Equipment Lists.dm")
    stack, nodes = [], []
    top = None
    for raw in open(path, encoding="latin-1"):
        line = raw.rstrip("\n")
        if not line.strip() or line.strip().startswith("//"):
            continue
        depth = len(line) - len(line.lstrip("\t"))
        text = line.strip()
        if depth == 0:
            top = text
            stack = [dict(path=text, vars={}, kids=0)]
            nodes.append(stack[0])
            continue
        m = re.match(r"(\w+)\s*=\s*(.+)$", text)
        while len(stack) > depth:
            stack.pop()
        if m:
            stack[-1]["vars"][m.group(1)] = m.group(2).strip()
        elif re.fullmatch(r"[A-Za-z_]\w*", text):
            parent = stack[-1]
            parent["kids"] += 1
            node = dict(path=parent["path"] + "/" + text, vars={}, kids=0, parent=parent)
            stack.append(node)
            nodes.append(node)
    def inherit(node, key):
        while node is not None:
            if key in node["vars"]:
                return node["vars"][key]
            node = node.get("parent")
        return None
    out = {}
    for n in nodes:
        if n["kids"] or not n["path"].startswith("obj/Items/Equipment"):
            continue
        icon, state, itype = inherit(n, "icon"), inherit(n, "icon_state"), inherit(n, "ItemType")
        if not icon or state is None or not itype:
            continue
        icon, state, itype = icon.strip("'"), state.strip('"'), itype.strip('"')
        if os.path.exists(os.path.join(rm.ICONS, icon)):
            out[(icon, state)] = itype
    return out


RIGID = ("Sword", "Spear", "Axe", "Mace", "Dagger", "Pickaxe", "Bow", "Butcher Knife", "Shield")


def shift(layer, dx, dy):
    out = np.zeros_like(layer)
    dx, dy = int(round(dx)), int(round(dy))
    ys, xs = slice(max(0, dy), 64 + min(0, dy)), slice(max(0, dx), 64 + min(0, dx))
    yd, xd = slice(max(0, -dy), 64 + min(0, -dy)), slice(max(0, -dx), 64 + min(0, -dx))
    out[ys, xs] = layer[yd, xd]
    return out


def item_template_layer(T, item, d, side=None):
    """An item on the template body (64 px): what the 32 px icon is made from."""
    slot, style, tier = item["slot"], item["style"], item["tier"]
    if item["id"].startswith("magic."):
        solid, fxs = w.magic_layers(T, d, style)
        return w.blend(solid, fxs[1])
    if slot == "weapon":
        return w.weapon_layer(T, d, style, tier)
    if slot == "shield":
        return w.shield_layer(T, d, style, tier)
    return armour_layer(T, item, d, side)


def armour_layer(T, item, d, side=None):
    slot, style, tier = item["slot"], item["style"], item["tier"]
    # Helmets and chests keep to the standing body's shape and move with it through the walk.
    if slot == "helmet":
        return T.on_still(d, "head", lambda S: w.helmet_layer("kettle (original)" if style == "kettle" else style, tier, d, S.heads, S.M))
    if slot == "chest":
        return T.on_still(d, "torso", lambda S: w.chest_layer2(S, d, "robe", tier) if style == "robe" else w.any_chest(S, d, style, tier))
    if slot == "legs":
        if style == "cloth":
            return w.leg_layer(T, d, "cloth", "wool")
        if style == "boots":
            return w.leg_layer(T, d, "boots", "leather")
        return w.leg_layer(T, d, style, tier)
    if slot == "arms":
        return w.arm_layer(T, d, style, tier, side)
    raise KeyError(item["id"])


def magic_race_layers(T, F, race, item, d):
    """A staff or enchanted weapon fitted to one race: (solid, [effect per frame])."""
    at = F.map_point(race, d, *T.grip(d)[0])
    sc = w.EXTRA.get(race[0], {}).get("scale", 1.0)
    return w.magic_layers(T, d, item["style"], at=at, body=F.body_mask(race, d), scale=sc)


def item_race_layer(T, F, race, item, d, side=None):
    """The item fitted to one race (64 px): what the 3D view draws. A magic item's effect
    is not in it: the 3D view lays that over the unit, animated (fx_cells)."""
    slot = item["slot"]
    mask = F.body_mask(race, d)
    sc = w.EXTRA.get(race[0], {}).get("scale", 1.0)
    if item["id"].startswith("magic."):
        return magic_race_layers(T, F, race, item, d)[0]
    if slot == "weapon":
        at = F.map_point(race, d, *T.grip(d)[0])
        return w.weapon_layer(T, d, item["style"], item["tier"], at=at, body=mask, scale=sc)
    if slot == "shield":
        at = F.map_point(race, d, *T.shield_at(d)[0])
        return w.shield_layer(T, d, item["style"], item["tier"], at=at, body=mask, scale=sc)
    return F.fit_layer(race, d, armour_layer(T, item, d, side), head=slot == "helmet")


def old_race_layer(T, F, race, icon, state, itype, d, cells_cache, frame=0, swing=None):
    """The game's own item fitted to one race (64 px), in walk `frame` (T and F are that
    frame's); with `swing` (a turned Template) a held weapon is turned about the hand as
    that template turns its grip, for an attack."""
    key = (icon, state)
    if key not in cells_cache:
        dmi = {s: c for s, _, c in read_dmi_full(os.path.join(rm.ICONS, icon))}
        cells_cache[key] = dmi.get(state)
    cells = cells_cache[key]
    if not cells:
        return None
    cells = w.walk_frame(cells, frame)
    i = rm.DIRS.index(d)
    cell = cells[i] if len(cells) >= 4 else cells[0]
    kind = {"Helmet": "helmet", "Shield": "shield", "Chestplate": "chest"}.get(itype)
    layer = rm.metal_finish(rm.scale2x(arr_rgba(cell)), kind)
    if itype in RIGID:   # held things keep their shape and move with the hand
        # where the overlay's own hand is, and where this race's hand is in this frame
        if itype == "Shield":
            drawn, anchor = T.shield_at(d, follow=False)[0], T.shield_at(d)[0]
        else:
            drawn, anchor = T.grip(d, follow=False)[0], T.grip(d)[0]
        x2, y2 = F.map_point(race, d, *anchor)
        layer = shift(layer, x2 - drawn[0], y2 - drawn[1])
        if swing is not None and itype in SWUNG:
            _, axis, outer, _ = T.grip(d)
            _, axis2, outer2, behind = swing.grip(d)
            layer = turn(layer, (x2, y2), axis, outer, axis2, outer2)
            if behind:   # held behind the body in this turn: only what shows past it
                layer[F.body_mask(race, d)] = 0
        return layer
    return F.fit_layer(race, d, layer, head=itype == "Helmet")


SWUNG = tuple(t for t in RIGID if t not in ("Shield", "Bow"))   # turned about the hand to strike
# An attack's two turns of the held weapon (radians, Template.swing): the wind-up up over the
# head, then the strike. Side views strike forward; front and back views chop down across
# the body (from behind, hidden by it).
SWING = {"S": (-0.9, -2.4), "N": (-0.9, -2.4), "E": (-0.9, 1.2), "W": (-0.9, 1.2)}
TURNS = 2


# Tilts tried, in order, when a held thing standing in a walk frame would run off the picture.
WALK_TURNS = (0.0, -0.15, 0.15, -0.3, 0.3, -0.45, 0.45, -0.6, 0.6, -0.8, 0.8)


def cut_off(layer):
    """Whether a held thing runs off the picture's sides or top (and is cut off there)."""
    al = layer[..., 3] > 0
    return bool(al[0].any() or al[:, 0].any() or al[:, -1].any())


def held_angles(TWS, FS, render):
    """{(picture frame, facing): radians} a held thing is turned about the hand by, so all of
    it stays inside the 64 px picture: in the walk frames the least tilt that fits (a long
    hammer or axe held out at the side would leave its head outside), in the wind-up and
    strike as much of the swing (SWING) as fits. render(T, F, d) draws it with T turned;
    TWS are the walk frames' Templates, turned in place."""
    out = {}
    for d in DIRS4:
        for k in range(WALK + TURNS):
            f = k if k < WALK else 0
            T = TWS[f]
            tries = WALK_TURNS if k < WALK else [SWING[d][k - WALK] * j / 10 for j in range(10, 0, -1)] + [0.0]
            out[(k, d)] = 0.0
            for a in tries:
                T.swing = a
                if not cut_off(render(T, FS[f], d)):
                    out[(k, d)] = a
                    break
            T.swing = 0.0
    return out


def held_rest(T0, F0, race, item, d, side=None):
    """A weapon or staff at rest on one race, its effect's reach included (for held_angles)."""
    if not item["id"].startswith("magic."):
        return item_race_layer(T0, F0, race, item, d, side)
    solid, fxs = magic_race_layers(T0, F0, race, item, d)
    out = solid.copy()
    for fx in fxs:
        out[fx[..., 3] > 0, 3] = 255
    return out


def turn(layer, hand, axis, outer, axis2, outer2):
    """A held thing turned rigidly about the hand: what lay along (axis, outer) now lies
    along (axis2, outer2). Nearest pixel, so it stays crisp."""
    yy, xx = np.mgrid[0:64, 0:64]
    px, py = xx + 0.5 - hand[0], yy + 0.5 - hand[1]
    t, s = px * axis2[0] + py * axis2[1], px * outer2[0] + py * outer2[1]
    sx = np.floor(hand[0] + t * axis[0] + s * outer[0]).astype(int)
    sy = np.floor(hand[1] + t * axis[1] + s * outer[1]).astype(int)
    ok = (sx >= 0) & (sx < 64) & (sy >= 0) & (sy < 64)
    out = np.zeros_like(layer)
    out[ok] = layer[sy[ok], sx[ok]]
    return out


def swung(item):
    return item["slot"] == "weapon" or item["id"].startswith("magic.")


def fx_cells(TWS, FS, race, item):
    """A magic item's effect fitted to one race, for the fx sheet: frame k * 4 + f is effect
    frame f (of w.FRAMES) at the item's picture frame k (three walk frames, wind-up, strike),
    frame-major then facing. Stored as light to add (colour times opacity, opaque), which
    the 3D view adds over the unit."""
    cells = []
    angles = held_angles(TWS, FS, lambda T, F, d: held_rest(T, F, race, item, d))   # as item_cells turns it
    for k in range(WALK + TURNS):
        per_dir = []
        for d in DIRS4:
            T = TWS[k if k < WALK else 0]
            T.swing = angles[(k, d)]
            per_dir.append(magic_race_layers(T, FS[k if k < WALK else 0], race, item, d)[1])
            T.swing = 0.0
        for f in range(w.FRAMES):
            for fxs in per_dir:
                fx = fxs[f]
                out = np.zeros_like(fx)
                lit = fx[..., 3] > 0
                out[lit, :3] = (fx[lit, :3].astype(np.uint16) * fx[lit, 3:4] // 255).astype(np.uint8)
                out[lit, 3] = 255
                cells.append(out)
    return cells


def item_cells(TS, TWS, FS, race, item, side):
    """The item fitted to one race in every walk frame and facing (frame-major), then, for a
    weapon or staff, the wind-up and the strike of an attack; a held thing turned so it
    stays inside the picture (held_angles, drawn with TWS turned)."""
    if not swung(item):
        return [item_race_layer(TS[f], FS[f], race, item, d, side) for f in range(WALK) for d in DIRS4]
    angles = held_angles(TWS, FS, lambda T, F, d: held_rest(T, F, race, item, d, side))
    cells = []
    for k in range(WALK + TURNS):
        f = k if k < WALK else 0
        for d in DIRS4:
            TWS[f].swing = angles[(k, d)]
            cells.append(item_race_layer(TWS[f], FS[f], race, item, d, side))
            TWS[f].swing = 0.0
    return cells


def to32(layer):
    """64 -> 32 px: a pixel is solid when two of its four are, coloured by their mean."""
    a = layer.astype(np.float32).reshape(32, 2, 32, 2, 4)
    al = (a[..., 3] > 0).astype(np.float32)
    n = al.sum(axis=(1, 3))
    rgb = (a[..., :3] * al[..., None]).sum(axis=(1, 3)) / np.maximum(n, 1)[..., None]
    out = np.zeros((32, 32, 4), np.uint8)
    solid = n >= 2
    out[solid, :3] = rgb[solid].astype(np.uint8)
    out[solid, 3] = 255
    return out


def group_of(item):
    if item["id"].startswith("magic."):
        return "magic"
    if item["tier"] in w.TIERS or item["tier"] in ("diamond",):
        return item["tier"]
    return "cloth"


def item_states(item):
    """(state name, side) per item: arms make a left and a right."""
    if item["slot"] == "arms":
        return [(item["id"] + ".L", "L"), (item["id"] + ".R", "R")]
    return [(item["id"], None)]


# ---------------------------------------------------------------------------
# DM data
# ---------------------------------------------------------------------------

def dm_name(s):
    return "rm_" + re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def dm_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def dm_list(d):
    return "list(" + ", ".join(f"{dm_str(k)}={v}" for k, v in d.items()) + ")"


def dm_types(item):
    """[(type path, state, name)] for an item (arms: left and right)."""
    slot = item["slot"]
    if item["id"].startswith("magic."):
        base = item.get("base")
        parent = "Weapon/" + (WEAPON_PARENT[base.split(".")[1]] if base else "Maces")
    elif slot == "weapon":
        parent = "Weapon/" + WEAPON_PARENT[item["style"]]
    elif slot == "arms":
        n = item["name"]
        return [(f"/obj/Items/Equipment/Armour/LeftArm/{dm_name(item['id'])}_left", item["id"] + ".L", n.replace(n.split()[-1], "Left " + n.split()[-1])),
                (f"/obj/Items/Equipment/Armour/RightArm/{dm_name(item['id'])}_right", item["id"] + ".R", n.replace(n.split()[-1], "Right " + n.split()[-1]))]
    else:
        parent = "Armour/" + ARMOUR_PARENT[slot]
    return [(f"/obj/Items/Equipment/{parent}/{dm_name(item['id'])}", item["id"], item["name"])]


def gear_cats(item):
    """Its categories for combining (planning/COMBINE_PLAN_2026-10-28.md): weapon or armour by its slot, then the row's
    own "cats" words."""
    base = ["weapon"] if item["slot"] == "weapon" or item["id"].startswith("magic.") else ["armour"]
    return base + [c for c in item.get("cats", []) if c not in base]


def gear_dm(items):
    L = ["// Generated by art/enhance/game_export.py from art/enhance/catalogue.json (planning/WEARABLES.md).",
         "// Do not edit: change the catalogue and run the exporter. Logic is in Gear.dm.", ""]
    defs = []
    for it in items:
        types = dm_types(it)
        group = group_of(it)
        icon = f"'Icons/Remastered/Gear/{group}.dmi'"
        for path, state, name in types:
            L.append(path)
            L.append(f"\tname = {dm_str(name)}")
            L.append(f"\ticon = {icon}")
            L.append(f"\ticon_state = {dm_str(state)}")
            L.append(f"\tweight = {int(it.get('weight') or 10)}")
            if "damage" in it:
                L.append(f"\tWeaponDamageMin = {it['damage'][0]}")
                L.append(f"\tWeaponDamageMax = {it['damage'][1]}")
            if "defence" in it:
                d = it["defence"] / (2 if it["slot"] == "arms" else 1) if False else it["defence"]
                L.append(f"\tDefence = {d}")
            if it["tier"] in ("silver", "diamond"):
                L.append("\tSilver = 1")
            L.append(f"\trm_gear = {dm_str(it['id'])}")
            L.append(f"\trm_group = {dm_str(group)}")
            L.append(f"\trm_use = {dm_str(SKILLVAR[it['use']['skill']])}")
            L.append(f"\trm_use_level = {it['use']['level']}")
            if it.get("use2"):
                L.append(f"\trm_use2 = {dm_str(SKILLVAR[it['use2']['skill']])}")
                L.append(f"\trm_use2_level = {it['use2']['level']}")
            L.append(f"\trm_hands = {it.get('hands', 1)}")
            L.append(f"\trm_cats = {dm_str(' '.join(gear_cats(it)))}")   # its categories for combining (UseOn.dm)
            L.append(f"\tdesc = {dm_str(it.get('notes') or '')}")
            L.append("")
        recipe = {}
        for r in it["recipe"]:
            if r["material"] == "mana":
                continue
            recipe[r["material"]] = r["count"]
        mana = next((r["count"] for r in it["recipe"] if r["material"] == "mana"), 0)
        entry = dict(id=dm_str(it["id"]), name=dm_str(it["name"]), slot=dm_str(it["slot"]), group=dm_str(group),
                     tier=dm_str(it["tier"]), station=dm_str(STATION[it["station"]]),
                     craft=dm_str(SKILLVAR[it["craft"]["skill"]]), craft_level=it["craft"]["level"],
                     use=dm_str(SKILLVAR[it["use"]["skill"]]), use_level=it["use"]["level"],
                     types="list(" + ", ".join(p for p, _, _ in types) + ")")
        if it.get("craft2"):
            entry.update(craft2=dm_str(SKILLVAR[it["craft2"]["skill"]]), craft2_level=it["craft2"]["level"])
        if it.get("use2"):
            entry.update(use2=dm_str(SKILLVAR[it["use2"]["skill"]]), use2_level=it["use2"]["level"])
        if it["who"].get("only"):
            entry["only"] = "list(" + ", ".join(dm_str(x) for x in it["who"]["only"]) + ")"
        if it["who"].get("not"):
            entry["not"] = "list(" + ", ".join(dm_str(x) for x in it["who"]["not"]) + ")"
        if it.get("base"):
            base = next(x for x in items if x["id"] == it["base"])
            entry["base"] = dm_types(base)[0][0]
            entry["base_name"] = dm_str(base["name"])
            recipe.pop(base["name"], None)
        if mana:
            entry["mana"] = mana
        if it["tier"] == "hell":
            entry["lava"] = 1
        entry["recipe"] = "list(" + ", ".join(f"{dm_str(k)}={v}" for k, v in recipe.items()) + ")"
        defs.append("\tlist(" + ", ".join(f"{dm_str(k)}={v}" for k, v in entry.items()) + ")")
    head = ["var/list/rm_gear_defs = list(", ",\n".join(defs), "\t)", ""]
    return "\n".join(L[:3] + head + L[3:]) + "\n"


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", default=None, help="Races64 sheets to build (comma separated)")
    ap.add_argument("--no-old", action="store_true", help="skip fitting the game's own gear")
    ap.add_argument("--no-bodies", action="store_true")
    ap.add_argument("--bodies-only", action="store_true", help="only the Races64 bodies, no gear")
    ap.add_argument("--items", default=None, help="only these catalogue ids (comma separated), for a quick look")
    ap.add_argument("--preview", default=None, help="write the 64 px sheets under this folder instead of the game")
    ap.add_argument("--data-only", action="store_true", help="only Code/Remastered/GearData.dm (a row's numbers, recipe or "
                    "categories changed, no picture): no 64 px sheets")
    a = ap.parse_args()
    global OUT_RACES, OUT_GEAR64
    if a.preview:
        OUT_RACES, OUT_GEAR64 = os.path.join(a.preview, "Races64"), os.path.join(a.preview, "Gear64")
    items = json.load(open(os.path.join(HERE, "catalogue.json")))["items"]
    if a.data_only:
        with open(OUT_DM + ".tmp", "w") as fh:
            fh.write(gear_dm(items))
        os.replace(OUT_DM + ".tmp", OUT_DM)
        print(OUT_DM)
        return
    if a.items:
        items = [it for it in items if it["id"] in a.items.split(",")]
    sheets = [s for s in SHEETS if not a.only or s["sheet"] in a.only.split(",")]
    races = [s["race"] for s in sheets if s.get("gear", True)]
    TS = [w.Template(frame=f) for f in range(WALK)]
    stand_rows = {s["race"][0] for s in sheets if s.get("recolour")}   # bodies moved onto the race's rows once
    FS = [w.Figures(Tf, races=races, frame=f, stand_rows=stand_rows) for f, Tf in enumerate(TS)]
    TWS = [w.Template(frame=f) for f in range(WALK)]   # turned to hold a weapon inside the picture (held_angles)
    T = TS[0]

    # data and 32 px icons (once)
    if not a.only and not a.preview and not a.items:
        with open(OUT_DM, "w") as fh:
            fh.write(gear_dm(items))
        print(OUT_DM)
        groups = {}
        for it in items:
            for state, side in item_states(it):
                cells = [to32(item_template_layer(T, it, d, side)) for d in DIRS4]
                groups.setdefault(group_of(it), []).append((state, {"dirs": "4", "frames": "1"}, cells))
        for g, states in groups.items():
            write_sheet(os.path.join(OUT_GEAR, g + ".dmi"), states, 32)
        print(OUT_GEAR, {g: len(s) for g, s in groups.items()})

    old = {} if a.no_old else parse_old_gear()
    print(len(old), "original wearables")
    cache = {}
    for spec in sheets:
        race = spec["race"]
        if not a.no_bodies:
            states = body_sheet(spec)
            write_sheet(os.path.join(OUT_RACES, spec["sheet"] + ".dmi"), states, 64)
            for colour, eyed in eye_sheets(spec, states).items():
                write_sheet(os.path.join(OUT_RACES, spec["sheet"] + (f"-{colour}" if colour else "") + ".dmi"), eyed, 64)
        if a.bodies_only:
            continue
        if not spec.get("gear", True):   # same body shape as another sheet: Gear.dm shares its gear
            print(spec["sheet"], "body only")
            continue
        groups = {}
        for fname, states in look_sheets(spec).items():
            groups["old-" + os.path.splitext(fname)[0]] = states
        for it in items:
            for state, side in item_states(it):
                cells = item_cells(TS, TWS, FS, race, it, side)
                groups.setdefault(group_of(it), []).append((state, walk_meta(len(cells) // 4), cells))
                if it["id"].startswith("magic."):
                    fx = fx_cells(TWS, FS, race, it)
                    groups.setdefault("fx", []).append((state, walk_meta(len(fx) // 4), fx))
        for (icon, state), itype in sorted(old.items()):
            cells = [old_race_layer(TS[f], FS[f], race, icon, state, itype, d, cache, f) for f in range(WALK) for d in DIRS4]
            if any(c is None for c in cells):
                continue
            if itype in SWUNG:   # held: turned to stay inside the picture, and swung to attack
                fr = lambda Tt: TWS.index(Tt)
                angles = held_angles(TWS, FS, lambda Tt, F, d: old_race_layer(TS[fr(Tt)], F, race, icon, state, itype, d, cache, fr(Tt), Tt))
                cells = []
                for k in range(WALK + TURNS):
                    f = k if k < WALK else 0
                    for d in DIRS4:
                        TWS[f].swing = angles[(k, d)]
                        cells.append(old_race_layer(TS[f], FS[f], race, icon, state, itype, d, cache, f, TWS[f]))
                        TWS[f].swing = 0.0
            groups.setdefault("old-" + os.path.splitext(icon)[0], []).append((state, walk_meta(len(cells) // 4), cells))
        for g, states in groups.items():
            write_sheet(os.path.join(OUT_GEAR64, spec["sheet"], g + ".dmi"), states, 64)
        print(spec["sheet"], "bodies" if not a.no_bodies else "", {g: len(s) for g, s in groups.items()})


if __name__ == "__main__":
    main()
