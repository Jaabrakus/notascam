#!/usr/bin/env python3
"""Our races' heads and skins on GOA's updated frames (owner 11-01: "combine our sprites on this", our heads and skins).

    python3 standalone/hidden-clans/art/goa-actions/heads.py [Sheet ...]     (default: Human; any Races64 sheet,
                                                                              "Orc-Marked Female" and the like)

For each race: its own 64 px head per facing (the head the 3D doll cuts out, g3rig.json code 0, from the race sheet's
standing frame) and its skin colours. GOA's 32 px frames are recoloured to the race's skin (each GOA skin colour to the
race colour at the same brightness rank; the race's colours are its bare arms'), GOA's shorts to the race's shorts
colours and its sandals to bare feet (clothes()), updated to 64 px (updated.py) and GOA's head cleared. Then GOA's body is reshaped to the race's build (bodyfit.py: chin to
feet and chest width of the race's standing frame), and the race's head laid where its own sprite has it, moved as GOA's
head moves in that frame (found by matching GOA's standing head). Writes races/<Race>/<state>-<facing><frame>.png.
"""
import colorsys
import json
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bodyfit import extras, grow, hair_mask, measure, warp, warp_index, warp_point  # noqa: E402
from updated import DIRS, GOA, NAMES, STATES, read_dmi, update  # noqa: E402
from partmap import PARTS, part_map, skeleton  # noqa: E402
from uvmap import race_skeleton, thickness  # noqa: E402
from compose import frame as draw_frame, race_kit  # noqa: E402

HC = os.path.dirname(os.path.dirname(HERE))
RACES64 = os.path.join(HC, "game", "Icons", "Remastered", "Races64")
RIG = json.load(open(os.path.join(HC, "game", "Interface", "gear3d", "g3rig.json")))["sheets"]
SHEET = {"Elf": "Night Elf", "HumanBlack": "Human"}     # race -> its rig entry, where the names differ
GOA_HEAD_ROWS = 13                  # GOA's head: the 32 px rows above the shoulders
GOA_HIP_ROWS = (19, 25)             # GOA's waist and shorts: where a tail hangs from


def read64(path):
    im = Image.open(path)
    desc = im.info.get("Description", "")
    im = im.convert("RGBA")
    w = int(re.search(r"width = (\d+)", desc).group(1))
    cols, i, out, cur, states = im.width // w, 0, {}, None, []
    for line in desc.splitlines():
        k, _, v = (s.strip() for s in line.partition("="))
        if k == "state":
            cur = {"name": v.strip('"'), "dirs": 1, "frames": 1}
            states.append(cur)
        elif cur and k in ("dirs", "frames"):
            cur[k] = int(v)
    for st in states:
        grid = []
        for _ in range(st["frames"]):
            row = []
            for _ in range(st["dirs"]):
                row.append(np.asarray(im.crop(((i % cols) * w, (i // cols) * w, (i % cols + 1) * w, (i // cols + 1) * w))).copy())
                i += 1
            grid.append(row)
        out[st["name"]] = grid
    return out


def codes(rig, facing):
    s, out, i = rig[facing]["lab"], np.full(4096, 255, np.uint8), 0
    for c, n in re.findall(r"([A-L.])(\d+)", s):
        out[i:i + int(n)] = 255 if c == "." else ord(c) - 65
        i += int(n)
    return out.reshape(64, 64)


# GOA draws the far hand and arm in these near-black shadows: they become the race's darkest skin, halved.
GOA_SKIN_SHADOWS = {(40, 35, 5), (49, 8, 0)}


def skin_mask(a):
    """GOA's skin: warm and saturated, down to its darker shading (the belt's crimson and the greys are not)."""
    rgb = a[..., :3].astype(float) / 255
    out = np.zeros(a.shape[:2], bool)
    for y, x in zip(*np.nonzero(a[..., 3] > 0)):
        h, s, v = colorsys.rgb_to_hsv(*rgb[y, x])
        out[y, x] = (h < 0.14 or h > 0.97) and s > 0.18 and v > 0.2
    return out


def trim_neck(mask):
    """A head cut down to its neck: below the head's widest row (looked for in its top two thirds), the narrowest row
    is the neck; if rows widen again under it (the shoulder tops some races' head zones take in), they are cut."""
    w = mask.sum(1)
    ys = np.flatnonzero(w)
    top = ys[: max(1, len(ys) * 2 // 3)]
    widest = top[np.argmax(w[top])]
    below = [y for y in ys if y > widest]
    if not below:
        return mask
    neck = min(below, key=lambda y: (w[y], -y))
    if any(w[y] > w[neck] + 4 for y in below if y > neck):
        mask = mask.copy()
        mask[neck + 1:] = False
    return mask


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def skin_map(goa_cells, race_skin):
    """Each GOA skin colour -> the race skin colour at the same brightness rank."""
    goa = set()
    for a in goa_cells:
        m = skin_mask(a)
        goa |= {tuple(int(v) for v in a[y, x, :3]) for y, x in zip(*np.nonzero(m))}
    goa, ours = sorted(goa - GOA_SKIN_SHADOWS, key=lum), sorted(race_skin, key=lum)
    out = {g: ours[min(len(ours) - 1, int(i * len(ours) / len(goa)))] for i, g in enumerate(goa)}
    out.update({g: tuple(v // 2 for v in ours[0]) for g in GOA_SKIN_SHADOWS})
    out[GOA_CRIMSON] = ours[0]
    return out


GOA_CRIMSON = (102, 0, 51)          # GOA's deepest skin shadow (torso sides, waist): the race's darkest skin


def rank_map(src, dst):
    """Each colour of src -> the dst colour at the same brightness rank."""
    src, dst = sorted(src, key=lum), sorted(dst, key=lum)
    return {c: dst[min(len(dst) - 1, int(i * len(dst) / len(src)))] for i, c in enumerate(src)} if dst else {}


def clothes(a, skin):
    """GOA's grey clothes in a 32 px frame, split by shape: the biggest piece is the shorts (with a kicking leg GOA
    draws in them), the small separate pieces low on the body are the sandals. Outline and skin are not clothes."""
    cloth = (a[..., 3] > 0) & ~skin & (a[..., :3].astype(int).sum(-1) > 30)
    for c in (GOA_CRIMSON, *GOA_SKIN_SHADOWS):          # GOA's skin shadows (the far arm) are skin, not clothes
        cloth &= ~np.all(a[..., :3] == c, axis=-1)
    lab, n = np.zeros(cloth.shape, int), 0
    for y, x in zip(*np.nonzero(cloth)):
        if lab[y, x]:
            continue
        n += 1
        stack = [(y, x)]
        lab[y, x] = n
        while stack:
            cy, cx = stack.pop()
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < 32 and 0 <= nx < 32 and cloth[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = n
                    stack.append((ny, nx))
    if not n:
        return cloth, cloth
    sizes = np.bincount(lab.ravel())[1:]
    shorts = lab == (np.argmax(sizes) + 1)
    feet = cloth & ~shorts & (np.arange(32)[:, None] >= 22)
    return shorts, feet


def recolour(cell, cmap, shorts_map=None, feet_map=None):
    a = np.asarray(cell.convert("RGBA")).copy()
    sk = skin_mask(a) | np.isin(a[..., :3].view([("", a.dtype)] * 3).ravel(),
                                np.array(list(GOA_SKIN_SHADOWS), dtype=a.dtype).view([("", a.dtype)] * 3).ravel()).reshape(32, 32)
    shorts, feet = clothes(a, sk) if shorts_map else (None, None)
    out = a.copy()
    for y, x in zip(*np.nonzero(a[..., 3] > 0)):
        c = tuple(int(v) for v in a[y, x, :3])
        m = cmap if c in cmap and sk[y, x] or c == GOA_CRIMSON else feet_map if feet is not None and feet[y, x] else \
            shorts_map if shorts is not None and shorts[y, x] else cmap
        if m and c in m:
            out[y, x, :3] = m[c]
    return Image.fromarray(out)


def head_offset(rest, frame, rows=(0, GOA_HEAD_ROWS)):
    """Where GOA's standing head (its top rows; or another band of rows) best matches this frame, in 32 px (dx, dy)."""
    t = np.zeros((32, 32, 4), np.uint8)
    t[rows[0]:rows[1]] = np.asarray(rest.convert("RGBA"))[rows[0]:rows[1]]
    f = np.asarray(frame.convert("RGBA"))
    ys, xs = np.nonzero(t[..., 3] > 0)
    best, at = -1, (0, 0)
    for dy in range(-4, 6):
        for dx in range(-8, 9):
            Y, X = ys + dy, xs + dx
            ok = (Y >= 0) & (Y < 32) & (X >= 0) & (X < 32)
            score = np.sum(np.all(f[Y[ok], X[ok]] == t[ys[ok], xs[ok]], axis=1)) - 0.02 * (abs(dx) + abs(dy))
            if score > best:
                best, at = score, (dx, dy)
    return at


def bottom_centre(mask):
    ys, xs = np.nonzero(mask)
    return (xs.min() + xs.max()) / 2, ys.max()


def main_tone(counts):
    """A race's skin: the colours of its main tone. Markings on the arms (an Ashen's glowing cracks, a Marked's red
    marks) are other hues and stay out; a grey skin (Zombie, Ashen) keeps its greys."""
    hsv = {c: colorsys.rgb_to_hsv(*(q / 255 for q in c)) for c in counts}
    total = sum(counts.values())
    if sum(n for c, n in counts.items() if hsv[c][1] < 0.15) > total / 2:
        return {c for c in counts if hsv[c][1] < 0.25}
    vec = sum(n * np.exp(2j * np.pi * hsv[c][0]) for c, n in counts.items() if hsv[c][1] >= 0.15)
    hue = (np.angle(vec) / (2 * np.pi)) % 1
    near = lambda h: min(abs(h - hue), 1 - abs(h - hue)) < 0.07
    keep = {c for c in counts if hsv[c][1] >= 0.15 and near(hsv[c][0])}
    return keep or set(counts)


def standing(name):
    sheets = read64(os.path.join(RACES64, name + ".dmi"))
    return sheets[""] if "" in sheets else sheets["Normal"]      # some sheets name their walk "Normal"


def base_race(name):
    """'Orc-Marked Female' -> 'Orc': the race whose rig (and male sheet) a woman or hybrid borrows."""
    return name.replace(" Female", "").split("-")[0]


def labels(name):
    """The 3D doll's part map per facing. Women and hybrids have none of their own: each of their pixels takes the
    part of the nearest pixel of their race's male standing frame (the map spread outwards a ring at a time)."""
    if name in RIG:
        return {d: codes(RIG[name], d) for d in DIRS}
    base = base_race(name)
    male_sheet = base if os.path.exists(os.path.join(RACES64, base + ".dmi")) else SHEET.get(base, base)   # no male Elf yet
    rig, male, own = RIG[SHEET.get(base, base)], standing(male_sheet), standing(name)
    out = {}
    for di, d in enumerate(DIRS):
        lab = codes(rig, d).astype(int)
        lab[(male[0][di][..., 3] == 0) | (lab > 9)] = -1
        while (lab < 0).any():
            p = np.pad(lab, 1, constant_values=-1)
            for n in (p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]):
                lab = np.where((lab < 0) & (n >= 0), n, lab)
        lab[own[0][di][..., 3] == 0] = 255
        out[d] = lab.astype(np.uint8)
    return out


def top_mask(a, lab, skin, chin, waist):
    """A woman's top: the dull darks of her torso zone between her chin and waist (not skin), with their outline."""
    al = a[..., 3] > 0
    rgb = a[..., :3].astype(float) / 255
    mx, mn = rgb.max(-1), rgb.min(-1)
    dull = ((mx - mn) / np.maximum(mx, 1e-6) < 0.3) & (mx < 0.4) & (a[..., :3].astype(int).sum(-1) > 45)
    rows = (np.arange(64)[:, None] > chin + 1) & (np.arange(64)[:, None] < waist)
    keyed = np.array([[tuple(int(v) for v in a[y, x, :3]) not in skin for x in range(64)] for y in range(64)])
    m = al & dull & rows & keyed & (lab == 1)
    if m.sum() < 8:
        return np.zeros_like(al)
    dark = al & (a[..., :3].astype(int).sum(-1) <= 45) & rows
    return m | (grow(m) & dark)


def prepare(race, goa):
    """A race sheet's standing frame, part maps, heads, skin and the colour maps from GOA's to its own."""
    sheet = standing(race)
    labs = labels(race)
    heads, skin_count = {}, {}
    for di, d in enumerate(DIRS):
        a, c = sheet[0][di], labs[d]
        m = trim_neck((c == 0) & (a[..., 3] > 0))
        h = np.zeros_like(a)
        h[m] = a[m]
        heads[d] = h
        # the race's skin: its bare arms (codes 2-5), outline left out; any skin tone, not only warm ones
        arms = (c >= 2) & (c <= 5) & (a[..., 3] > 0)
        for y, x in zip(*np.nonzero(arms)):
            if lum(a[y, x]) > 45:
                col = tuple(int(v) for v in a[y, x, :3])
                skin_count[col] = skin_count.get(col, 0) + 1
    skins = main_tone(skin_count)
    # the race's shorts: the dull dark colours of its torso zone below the chest (not skin, not outline)
    shorts_c = set()
    for di, d in enumerate(DIRS):
        a, c = sheet[0][di], labs[d]
        ys = np.flatnonzero((c == 1).any(1))
        lo = ys[0] + (ys[-1] - ys[0]) * 2 // 3
        for y, x in zip(*np.nonzero((c == 1) & (a[..., 3] > 0))):
            col = tuple(int(v) for v in a[y, x, :3])
            h, sat, v = colorsys.rgb_to_hsv(*(q / 255 for q in col))
            if y >= lo and col not in skins and lum(col) > 12 and sat < 0.3 and v < 0.55:
                shorts_c.add(col)
    goa_cloth, goa_feet = set(), set()
    for st in STATES:
        for fr in goa[st]:
            for cell in fr:
                a = np.asarray(cell.convert("RGBA"))
                sm, fm = clothes(a, skin_mask(a))
                goa_cloth |= {tuple(int(v) for v in a[y, x, :3]) for y, x in zip(*np.nonzero(sm))}
                goa_feet |= {tuple(int(v) for v in a[y, x, :3]) for y, x in zip(*np.nonzero(fm))}
    shorts_map, feet_map = rank_map(goa_cloth, shorts_c), rank_map(goa_feet, skins)
    cmap = skin_map([np.asarray(f[di].convert("RGBA")) for st in STATES for f in goa[st] for di in range(4)], skins)
    return {"sheet": sheet, "labs": labs, "heads": heads, "skins": skins, "shorts_c": shorts_c, "cmap": cmap,
            "shorts_map": shorts_map, "feet_map": feet_map}


def main():
    races = sys.argv[1:] or ["Human"]
    goa = read_dmi(os.path.join(GOA, "base_m1.dmi"))
    rest = goa[""][0]
    for race in races:
        k = prepare(race, goa)
        sheet, labs, heads, skins, shorts_c, cmap, shorts_map, feet_map = (k[n] for n in (
            "sheet", "labs", "heads", "skins", "shorts_c", "cmap", "shorts_map", "feet_map"))
        dest = os.path.join(HERE, os.environ.get("GOA_OUT", "races"), race)
        os.makedirs(dest, exist_ok=True)
        for di, d in enumerate(DIRS):
            t = np.asarray(rest[di].convert("RGBA"))[:GOA_HEAD_ROWS, :, 3] > 0
            g64 = update(rest[di])
            g_head = np.zeros(g64.shape[:2], bool)
            g_head[:GOA_HEAD_ROWS * 2] = np.kron(t, np.ones((2, 2), bool)) & (g64[:GOA_HEAD_ROWS * 2, :, 3] > 0)
            ra, head = sheet[0][di], heads[d][..., 3] > 0
            # both at the chest (GOA has no hair down its back; the race's is left out)
            goa_m = measure(g64, g_head, d, np.zeros_like(g_head) if d in "EW" else None)
            race_m = measure(ra, head, d, hair_mask(ra, head, skins) if d in "EW" else None)
            # the race's hair below its head and its tail, from its standing frame beside GOA's reshaped standing body
            gb = g64.copy()
            gb[g_head] = 0
            gb, _, _ = warp(gb, goa_m, race_m)
            waist = race_m["chin"] + (race_m["feet"] - race_m["chin"]) * 45 // 100
            hair, tail = extras(ra, head, gb[..., 3] > 0, skins, waist, labs[d], d, race_m["cx"])
            sy, sx, inside, kx, ky = warp_index(goa_m, race_m)
            rj = race_skeleton(ra, labs[d], head, shorts_c, d)
            gj0 = skeleton(d, "", 0)
            race_al = ra[..., 3] > 0
            arm_r = thickness(race_al, labs[d], (2, 3), rj["RS"], rj["RH"]) or thickness(race_al, labs[d], (4, 5), rj["LS"], rj["LH"])
            pm0 = part_map(g64, g_head, gj0, d)
            arm_g = thickness(g64[..., 3] > 0, pm0, (PARTS.index("RUp"), PARTS.index("RFore")), gj0["RS"], gj0["RH"])
            legw = lambda al, y0, y1: al[int(y0):int(y1)].sum() / max(1, int(y1) - int(y0))
            # half-widths once GOA's frame is the race's size (GOA's scaled by kx) against the race's own
            half = {"torso": (goa_m["chest_w"] * kx / 2, race_m["chest_w"] / 2),
                    "arm": (arm_g * kx / 2, max(arm_r, 1) / 2),
                    "leg": (legw(g64[..., 3] > 0, gj0["RK"][1], gj0["RA"][1]) * kx / 2,
                            legw(race_al, rj["RK"][1], rj["RA"][1]) / 2)}
            kit = race_kit(ra, labs[d], head, rj, skins, shorts_c, d)
            if d == "S":
                front = (kit["arm_r"], kit["shin_r"])          # limbs as thick from every side as from the front
            kit["arm_r"], kit["shin_r"] = front
            gj0w = {k_: warp_point(v, goa_m, race_m, kx, ky) for k_, v in gj0.items()}
            for st in STATES:
                for f, frame in enumerate(goa[st]):
                    name = os.path.join(dest, f"{NAMES.get(st, st)}-{d}{f}.png")
                    if st == "":
                        # the walk is the race's own (its sheet's three steps), already clean and approved
                        Image.fromarray(sheet[min([0, 1, 0, 2][f], len(sheet) - 1)][di]).save(name)
                        continue
                    dx, dy = head_offset(rest[di], frame[di])
                    # the frame drawn from containers: GOA's pose, the race's own parts and colours poured in
                    gjw = {k_: warp_point(v, goa_m, race_m, kx, ky) for k_, v in skeleton(d, st, f).items()}
                    off = (gjw["N"] + gjw["P"] - gj0w["N"] - gj0w["P"]) / 2
                    body = draw_frame(kit, ra, rj, gj0w, gjw, d, off)
                    ox, oy = int(round(2 * dx * kx)), int(round(2 * dy * ky))

                    def lay(mask, mx, my, under):
                        ys, xs = np.nonzero(mask)
                        Y, X = ys + my, xs + mx
                        ok = (Y >= 0) & (Y < 64) & (X >= 0) & (X < 64)
                        if under:
                            ok[ok] &= body[Y[ok], X[ok], 3] == 0
                        body[Y[ok], X[ok]] = ra[ys[ok], xs[ok]]
                    px, py = head_offset(rest[di], frame[di], GOA_HIP_ROWS)      # the hips: GOA's waist band
                    tx, ty = int(round(px * 2 * kx)), int(round(py * 2 * ky))
                    if tail.any() and d in "EW":
                        # from the side, the tail's root keeps touching the body's back in this frame
                        ys, xs = np.nonzero(tail)
                        root_y = ys.min()
                        rx = xs[ys <= root_y + 2].max() if d == "E" else xs[ys <= root_y + 2].min()
                        row = np.flatnonzero(body[min(63, max(0, root_y + ty)), :, 3] > 0)
                        if len(row):
                            back = row.min() if d == "E" else row.max()
                            tx = int(np.clip(back - rx + (1 if d == "E" else -1), tx - 6, tx + 6))
                    lay(tail, tx, ty, d != "N")   # from the hips: behind, over the legs from behind
                    lay(hair, ox, oy, d != "N")   # hair goes with the head; over the back from behind
                    ys, xs = np.nonzero(head)
                    Y, X = ys + oy, xs + ox
                    ok = (Y >= 0) & (Y < 64) & (X >= 0) & (X < 64)
                    body[Y[ok], X[ok]] = heads[d][ys[ok], xs[ok]]
                    Image.fromarray(body).save(name)
        print(race, "->", dest, len(cmap), "skin,", len(shorts_map), "shorts,", len(feet_map), "feet colours mapped;",
              "race shorts", len(shorts_c))


if __name__ == "__main__":
    main()
