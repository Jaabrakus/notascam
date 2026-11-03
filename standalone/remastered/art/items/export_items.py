#!/usr/bin/env python3
"""Every carried item that isn't gear, one row each (the owner, 2026-10-28: "Yes, one row each").

    python3 standalone/remastered/art/items/export_items.py [--catalogue FILE] [--game DIR]
    python3 standalone/remastered/art/items/export_items.py --adopt /obj/Items/ores/Iron ... [--json FILE]

Reads art/items/catalogue.json (weapons and armour are art/enhance/catalogue.json, game_export.py) and writes, under
game/ (or DIR, a clone of it to test first):
  Code/Remastered/ItemData.dm             each item's type (name, picture, weight, description, its categories for
                                          combining, its own numbers) and, for those made at a workshop, a recipe row in
                                          rm_item_defs: the same shape as a gear row, so the workshops' "Craft new gear"
                                          offers it under "Supplies" (Gear.dm) with the same skill, race and material
                                          checks
  Icons/Remastered/Items/catalogue.dmi    the rows' own pictures (art/items/pictures/<file>.png, 32 x 32), when any row
                                          has one; a row may use a picture the game already has instead

A row (see the catalogue's "fields"):
  id        unique, lower case: "potion.ember draught"
  name      what the game calls it
  kind      food | potion | poison | herb | material | tool | misc  (where it sits: what the game already does with that
            kind, eating food, drinking a potion..., comes with it)
  picture   "pictures/<file>.png" (packed into catalogue.dmi), or {"dmi": "Cave.dmi", "state": "Toxic"}
  weight    as the game's items (a log is 10)
  desc      what Inspect says
  cats      its categories for combining ("poison", "herb", ...): planning/COMBINE_PLAN_2026-10-28.md
  vars      its own numbers, by the game's variable names: {"FoodPower": 30, "PoisonContent": 25}
  recipe    optional: {"station": "Carpentry", "skill": "Woodwork", "level": 5, "materials": {"wood": 2}, "makes": 1,
            "who": {"only": ["Elf"]}}  - stations, skills and materials as the gear catalogue's
  adopt     an item the game already has, by its type name: "/obj/Items/ores/Iron". The row then holds that kind's
            values and needs only id; kind is its place already, and anything the row leaves out it keeps from its
            group. Its type name never changes, so saves, and every line of code that names it, still find it, and
            all its code (its menu, what it does) stays where it is.

--adopt PATH ... moves kinds the game already has into rows (the owner, 2026-10-28: "List, then adopt"): each kind's own
values come out of the old file (they must be a plain block right under the kind, as list_items.py's Adopt column
says) and into a new row, with the values the compiled game (--json, default Cave Crawlers.json) has for them; then
the export runs. A row and the old files may never both set the same value: the export stops if they do.
"""
import argparse
import json
import os
import re
import struct
import sys
import zlib
from collections import defaultdict

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import dmsource  # noqa: E402
KINDS = {"food": "/obj/Items/Food", "potion": "/obj/Items/Potions", "poison": "/obj/Items/Poisons",
         "herb": "/obj/Items/RemasterHerb", "material": "/obj/Items", "tool": "/obj/Items/RemasterTools", "misc": "/obj/Items"}
SKILLVAR = {"Smithing": "MetalCraftingSkill", "Leatherwork": "LeatherCraftingSkill", "Bone craft": "BoneCraftingSkill",
            "Woodwork": "WoodCraftingSkill", "Gem cutting": "JewlCraftingSkill"}   # as art/enhance/game_export.py
STATION = {"Forge": "forge", "Bone crafting": "bone", "Leatherworks": "leather", "Carpentry": "carpentry", "Gem cutter": "gem"}
DMI = "Icons/Remastered/Items/catalogue.dmi"
ITEMDATA = "Code/Remastered/ItemData.dm"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def dm_str(s):
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("[", "\\[").replace("\n", "\\n")
    return '"' + s + '"'


def dm_val(v):
    if v is None: return "null"
    if isinstance(v, bool): return "1" if v else "0"
    if isinstance(v, (int, float)): return repr(v)
    return dm_str(v)


def materials(game):
    """The gear crafting's material names (Gear.dm rm_gear_materials): a recipe may use only these."""
    t = open(os.path.join(game, "Code", "Remastered", "Gear.dm"), encoding="latin-1").read()
    m = re.search(r"var/list/rm_gear_materials = list\((.*?)\)\n", t, re.S)
    return set(re.findall(r'"([^"]+)"=', m.group(1)))


def row_path(r):
    return r["adopt"] if r.get("adopt") else f"{KINDS[r['kind']]}/rm_item_{slug(r['id'])}"


def row_vars(r):
    """The values a row writes on its kind, by the game's variable names."""
    p = r.get("picture")
    v = [k for k in ("name", "weight", "desc") if k in r] + ["rm_item"] + list(r.get("vars", {}))
    if isinstance(p, str) or (isinstance(p, dict) and "dmi" in p): v.append("icon")
    if isinstance(p, str) or (isinstance(p, dict) and "state" in p): v.append("icon_state")
    if r.get("cats"): v.append("rm_cats")
    return v


def check(rows, mats, base):
    errs, seen, paths = [], set(), set()
    for i, r in enumerate(rows):
        at = f"row {i + 1} ({r.get('id', '?')})"
        need = ("id",) if r.get("adopt") else ("id", "name", "kind", "picture", "weight", "desc")
        for k in need:
            if k not in r: errs.append(f"{at}: no {k}")
        if r.get("id") in seen: errs.append(f"{at}: id used twice")
        seen.add(r.get("id"))
        if r.get("adopt"):
            if not str(r["adopt"]).startswith("/obj/Items/"): errs.append(f"{at}: adopt is a type under /obj/Items/")
            if r["adopt"] in paths: errs.append(f"{at}: {r['adopt']} adopted twice")
            paths.add(r["adopt"])
        elif r.get("kind") not in KINDS: errs.append(f"{at}: kind must be one of {', '.join(KINDS)}")
        if not isinstance(r.get("cats", []), list): errs.append(f"{at}: cats is a list of words")
        for k in r.get("vars", {}):
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k): errs.append(f"{at}: var {k!r} isn't a variable name")
        rc = r.get("recipe")
        if rc:
            if rc.get("station") not in STATION: errs.append(f"{at}: station must be one of {', '.join(STATION)}")
            if rc.get("skill") not in SKILLVAR: errs.append(f"{at}: skill must be one of {', '.join(SKILLVAR)}")
            for m in rc.get("materials", {}):
                if m not in mats: errs.append(f"{at}: material {m!r} isn't one the workshops know (Gear.dm rm_gear_materials)")
            if not rc.get("materials"): errs.append(f"{at}: a recipe needs materials")
        p = r.get("picture")
        if isinstance(p, str) and not os.path.exists(os.path.join(base, p)): errs.append(f"{at}: no picture file {p} (beside the catalogue)")
        if isinstance(p, dict) and not (({"dmi", "state"} <= set(p)) or (r.get("adopt") and set(p) and set(p) <= {"dmi", "state"})):
            errs.append(f"{at}: a picture is a file or dmi + state")
    return errs


def clash(rows, src):
    """A row and the old files never both set a value of the same kind; an adopted kind must exist already."""
    errs = []
    for r in rows:
        path, mine = row_path(r), set(row_vars(r))
        if r.get("adopt") and not any(f != ITEMDATA for f, _ in src.headers.get(path, [])):
            errs.append(f"{r['id']}: the game has no {path} to adopt")
        for a in src.assigns.get(path, []):
            if a.file != ITEMDATA and a.var in mine:
                errs.append(f"{r['id']}: {a.var} is still set in {a.file}:{a.first} (export_items.py --adopt moves it)")
    return errs


def write_dmi(path, cells):
    """cells: [(state, 32x32 RGBA array)]: one frame, one direction each (art/pipeline/build_dmi.py's layout)."""
    cols = max(1, int(np.ceil(np.sqrt(len(cells)))))
    rows = int(np.ceil(len(cells) / cols))
    sheet = np.zeros((rows * 32, cols * 32, 4), np.uint8)
    desc = ["# BEGIN DMI", "version = 4.0", "\twidth = 32", "\theight = 32"]
    for i, (state, a) in enumerate(cells):
        y, x = divmod(i, cols)
        sheet[y * 32:(y + 1) * 32, x * 32:(x + 1) * 32] = a
        desc += [f'state = "{state}"', "\tdirs = 1", "\tframes = 1"]
    desc.append("# END DMI")
    raw = b"".join(b"\x00" + sheet[y].tobytes() for y in range(sheet.shape[0]))
    chunk = lambda k, d: struct.pack(">I", len(d)) + k + d + struct.pack(">I", zlib.crc32(k + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", sheet.shape[1], sheet.shape[0], 8, 6, 0, 0, 0))
    png += chunk(b"zTXt", b"Description\x00\x00" + zlib.compress(("\n".join(desc) + "\n").encode("latin-1"), 9))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh: fh.write(png)


def item_dm(rows):
    L = ["// Generated by art/items/export_items.py from art/items/catalogue.json: every carried item that isn't gear, one",
         "// row each (gear: GearData.dm). Do not edit: change the catalogue and run the exporter. Crafting is Gear.dm's.", ""]
    defs = []
    for r in rows:
        path = row_path(r)
        p = r.get("picture")
        icon, state = (f"'{DMI}'", slug(r["id"])) if isinstance(p, str) else \
            ((f"'{p['dmi']}'" if "dmi" in p else None), p.get("state")) if p else (None, None)
        L.append(path)
        if "name" in r: L.append(f"\tname = {dm_str(r['name'])}")
        if icon: L.append(f"\ticon = {icon}")
        if state is not None: L.append(f"\ticon_state = {dm_str(state)}")
        if "weight" in r: L.append(f"\tweight = {dm_val(r['weight'])}")
        if "desc" in r: L.append(f"\tdesc = {dm_val(r['desc'])}")
        L.append(f"\trm_item = {dm_str(r['id'])}")
        if r.get("cats"): L.append(f"\trm_cats = {dm_str(' '.join(r['cats']))}")
        for k, v in r.get("vars", {}).items(): L.append(f"\t{k} = {dm_val(v)}")
        L.append("")
        rc = r.get("recipe")
        if not rc: continue
        e = {"id": dm_str(r["id"]), "name": dm_str(r["name"]), "slot": '"item"', "group": '"supplies"', "tier": '"item"',
             "station": dm_str(STATION[rc["station"]]), "craft": dm_str(SKILLVAR[rc["skill"]]), "craft_level": int(rc.get("level", 1)),
             "types": f"list({path})", "makes": int(rc.get("makes", 1)),
             "recipe": "list(" + ", ".join(f"{dm_str(k)}={int(v)}" for k, v in rc["materials"].items()) + ")"}
        who = rc.get("who", {})
        if who.get("only"): e["only"] = "list(" + ", ".join(dm_str(x) for x in who["only"]) + ")"
        if who.get("not"): e["not"] = "list(" + ", ".join(dm_str(x) for x in who["not"]) + ")"
        defs.append("\tlist(" + ", ".join(f"{dm_str(k)}={v}" for k, v in e.items()) + ")")
    head = ["obj/Items/var/rm_item   // its row's id (art/items/catalogue.json)", "",
            "var/list/rm_item_defs = list(" + ("\n" + ",\n".join(defs) + "\n\t" if defs else "") + ")", ""]
    return "\n".join(L[:3] + head + L[3:]) + "\n"


def save_catalogue(path, cat):
    """The catalogue with one line a row."""
    txt = json.dumps({**cat, "items": "@@ITEMS@@"}, indent=1, ensure_ascii=False)
    rows = ",\n".join("  " + json.dumps(r, ensure_ascii=False) for r in cat["items"])
    txt = txt.replace('"@@ITEMS@@"', "[\n" + rows + "\n ]" if rows else "[]")
    with open(path + ".tmp", "w") as fh: fh.write(txt + "\n")
    os.replace(path + ".tmp", path)


def adopt(paths, game, catalogue, json_path):
    """Move kinds the game already has into rows: their own values out of the old file, into the catalogue."""
    from list_items import Game
    G = Game(game, json_path)
    cat = json.load(open(catalogue))
    have, ids = {r.get("adopt") for r in cat["items"]}, {r["id"] for r in cat["items"]}
    cut, text, new, errs = defaultdict(dict), {}, [], []      # cut: file -> {line: what replaces it, None: nothing}
    for path in paths:
        if path in have: errs.append(f"{path}: already a row"); continue
        if path not in G.by_path: errs.append(f"{path}: the compiled game has no such kind"); continue
        block, why = G.adopt_block(path)
        if not block: errs.append(f"{path}: {why}"); continue
        f, _, A = block
        own = G.by_path[path]["Variables"]
        rid = ".".join(s.lower() for s in path[len("/obj/Items/"):].split("/"))
        if rid in ids: errs.append(f"{path}: id {rid} is taken"); continue
        vals, pic, more = {}, {}, {}
        for a in A:
            v = own[a.var]
            if any(ord(c) > 126 for c in json.dumps(v, ensure_ascii=False)):
                errs.append(f"{path}: {a.var} has letters beyond plain ASCII"); break
            if a.var == "icon" and v is not None: pic["dmi"] = v["resourcePath"]
            elif a.var == "icon_state" and v is not None: pic["state"] = v
            elif a.var in ("name", "weight", "desc"): vals[a.var] = v
            else: more[a.var] = v
        else:
            row = {"id": rid, "adopt": path}
            if "name" in vals: row["name"] = vals["name"]
            if pic: row["picture"] = pic
            for k in ("weight", "desc"):
                if k in vals: row[k] = vals[k]
            if more: row["vars"] = more
            new.append(row); ids.add(rid)
            for a in A: cut[f].update(dict.fromkeys(range(a.first, a.last + 1)))
            if f not in text: text[f] = open(os.path.join(game, f), encoding="latin-1").read().split("\n")
            tabs = re.match(r"\t*", text[f][A[0].first - 1]).group()
            cut[f][A[0].first] = f"{tabs}// its values: art/items/catalogue.json row {rid} (export_items.py writes ItemData.dm)"
    if errs:
        sys.exit("nothing adopted:\n  " + "\n  ".join(errs))
    for f, gone in cut.items():
        p = os.path.join(game, f)
        out = [gone[i] if i in gone else x for i, x in enumerate(text[f], 1)]
        with open(p + ".tmp", "w", encoding="latin-1") as fh: fh.write("\n".join(x for x in out if x is not None))
        os.replace(p + ".tmp", p)
    cat["items"] += new
    save_catalogue(catalogue, cat)
    print(f"adopted {len(new)} kinds: their values left {', '.join(sorted(cut))} for {catalogue}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--catalogue", default=os.path.join(HERE, "catalogue.json"))
    ap.add_argument("--game", default=os.path.join(ROOT, "game"), help="the game folder (a clone of it to test first)")
    ap.add_argument("--adopt", nargs="+", metavar="PATH", help="kinds the game already has, to move into rows first")
    ap.add_argument("--json", help="the compiled game, for --adopt (default: Cave Crawlers.json in the game folder)")
    a = ap.parse_args()
    if a.adopt:
        adopt(a.adopt, a.game, a.catalogue, a.json or os.path.join(a.game, "Cave Crawlers.json"))
    rows = json.load(open(a.catalogue))["items"]
    errs = check(rows, materials(a.game), os.path.dirname(os.path.abspath(a.catalogue)))
    errs = errs or clash(rows, dmsource.read(a.game))
    if errs:
        sys.exit("catalogue not exported:\n  " + "\n  ".join(errs))
    out = os.path.join(a.game, "Code", "Remastered", "ItemData.dm")
    with open(out + ".tmp", "w", encoding="latin-1") as fh: fh.write(item_dm(rows))
    os.replace(out + ".tmp", out)
    cells = []
    for r in rows:
        if isinstance(r.get("picture"), str):
            im = Image.open(os.path.join(os.path.dirname(a.catalogue), r["picture"])).convert("RGBA")
            if im.size != (32, 32): im = im.resize((32, 32), Image.NEAREST)
            cells.append((slug(r["id"]), np.array(im)))
    if cells: write_dmi(os.path.join(a.game, DMI), cells)
    print(f"{len(rows)} items, {sum(1 for r in rows if r.get('recipe'))} with a recipe, {len(cells)} pictures -> {out}")


if __name__ == "__main__":
    main()
