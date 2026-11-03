#!/usr/bin/env python3
"""Every kind of item in the game, in one list (the owner, 2026-10-28: "List, then adopt").

    python3 standalone/remastered/art/items/list_items.py [--game DIR] [--json FILE]

Reads the compiled game (game/Cave Crawlers.json, as the last build or compile left it) for each kind's name, picture,
weight and categories, and the source (dmsource.py) for where its values are written, what code of its own it has
and where the code makes it. Writes, beside this file:
  ITEM_LIST.md     a table per group: what each kind is, where it comes from, and whether it can be adopted into
                   the item catalogue as it is (export_items.py --adopt: same type name, so saves and every line of
                   code that names it still find it; only its values move into the row)
  item_list.json   the same, for tools"""
import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import dmsource  # noqa: E402

ITEMS = "/obj/Items/"
GEAR, ITEMDATA, CATS = "Code/Remastered/GearData.dm", "Code/Remastered/ItemData.dm", "Code/Remastered/UseOn.dm"
FACTS = ("name", "icon", "icon_state", "weight", "desc")
SETS_FACT = re.compile(r"^(?:src\.)?(name|icon|icon_state|weight|desc)\s*[+-]?=(?!=)")
MENTION = re.compile(r"\bvar/(?:(?:tmp|const|global|static)/)*(obj/Items(?:/\w+)+)/\w+|(?<![\w/])/(obj/Items(?:/\w+)+)")


class Game:
    def __init__(self, game, json_path):
        d = json.load(open(json_path))
        self.game = game
        self.types = d["Types"]
        self.by_path = {t["Path"]: t for t in self.types}
        self.procs = d["Procs"]
        self.src = dmsource.read(game)
        self.children = defaultdict(list)
        for t in self.types:
            if t.get("Parent") is not None: self.children[self.types[t["Parent"]]["Path"]].append(t["Path"])
        self.made_by, self.news = defaultdict(set), defaultdict(list)
        for P in self.src.procs:
            if P.name == "New": self.news[P.owner].append(P)
            for _, code in P.body:
                if "new" not in code: continue
                for m in MENTION.finditer(code):
                    self.made_by["/" + (m.group(1) or m.group(2))].add((P.owner, P.name))

    def chain(self, path):
        t = self.by_path.get(path)
        while t is not None:
            yield t
            t = self.types[t["Parent"]] if t.get("Parent") is not None else None

    def value(self, path, var):
        for t in self.chain(path):
            if var in t.get("Variables", {}): return t["Variables"][var]
        return None

    def own_procs(self, path):
        t = self.by_path[path]
        return sorted({self.procs[i]["Name"] for grp in t.get("Procs", []) for i in grp})

    def adopt_block(self, path):
        """(file, header line, [Assign]) when the kind's own values are one block right under its header in one file,
        each a plain value the compiler kept as it is; otherwise (None, reason)."""
        own = self.by_path[path].get("Variables", {})
        A = [a for a in self.src.assigns.get(path, []) if not (a.file == CATS and a.var == "rm_cats")]
        if not A: return None, "no values of its own"
        files = {a.file for a in A}
        if files & {GEAR, ITEMDATA}: return None, "already a catalogue row"
        if len(files) > 1: return None, "values in " + ", ".join(sorted(files))
        f = A[0].file
        heads = [h for hf, h in self.src.headers.get(path, []) if hf == f and h < A[0].first]
        if not heads: return None, "values written as a path, not under the kind"
        h = max(heads)
        lines = open(os.path.join(self.game, f), encoding="latin-1").read().split("\n")
        taken = {ln for a in A for ln in range(a.first, a.last + 1)}
        for ln in range(h + 1, max(taken) + 1):
            if ln not in taken and lines[ln - 1].strip() and not lines[ln - 1].strip().startswith("//"):
                return None, f"values mixed with code ({f}:{ln})"
        for a in A:
            if a.var not in own: return None, f"{a.var} is worked out when made"
            v = own[a.var]
            if isinstance(v, dict) and not (a.var == "icon" and "resourcePath" in v): return None, f"{a.var} isn't a plain value"
            if isinstance(v, list): return None, f"{a.var} is a list"
        for t in self.chain(path):
            for P in self.news.get(t["Path"], []):
                if any(SETS_FACT.match(c) for _, c in P.body):
                    return None, f"New() in {P.owner[len(ITEMS) - 1:] or P.owner} changes its values when made"
            if t["Path"] == "/obj/Items": break
        return (f, h, A), None


def where(G, path):
    A = G.src.assigns.get(path, [])
    files = sorted({a.file for a in A if not (a.file == CATS and a.var == "rm_cats")})
    if GEAR in files: return "gear row", GEAR
    if ITEMDATA in files: return "item row", ITEMDATA
    f = files[0] if files else next((hf for hf, _ in G.src.headers.get(path, [])), "")
    return ("Remastered" if f.startswith("Code/Remastered/") else "2006"), f


def short_proc(owner, name):
    return (owner.rstrip("/").split("/")[-1] + " › " if owner.strip("/") else "") + name


def rows(G):
    out = []
    for t in G.types:
        p = t["Path"]
        if not p.startswith(ITEMS) or "/var" in p[len(ITEMS) - 1:] or "/proc" in p[len(ITEMS) - 1:]: continue
        src, f = where(G, p)
        icon = G.value(p, "icon")
        block, why = G.adopt_block(p) if src in ("2006", "Remastered") else (None, "already a row")
        lines = [ln for hf, ln in G.src.headers.get(p, []) if hf == f] or [a.first for a in G.src.assigns.get(p, []) if a.file == f]
        out.append({
            "path": p, "code": p[len(ITEMS):], "group": p[len(ITEMS):].split("/")[0],
            "name": G.value(p, "name") or p.split("/")[-1], "dmi": icon.get("resourcePath") if isinstance(icon, dict) else icon,
            "state": G.value(p, "icon_state"), "weight": G.value(p, "weight"), "desc": G.value(p, "desc"),
            "cats": (G.value(p, "rm_cats") or "").split(), "kinds_below": len(G.children.get(p, [])),
            "from": src, "file": f, "line": min(lines) if lines else None,
            "own_code": G.own_procs(p),
            "made_by": sorted(short_proc(o, n) for o, n in G.made_by.get(p, ())),
            "adopt": "yes" if block else why})
    return out


def cell(v):
    return str(v if v is not None else "").replace("|", "/").replace("\n", " ")


def write_md(R, path, stamp):
    by = defaultdict(list)
    for r in R: by[r["group"]].append(r)
    n = Counter(r["from"] for r in R)
    can = [r for r in R if r["adopt"] == "yes"]
    L = ["# Every item in the game", "",
         f"Made by `python3 art/items/list_items.py` from the compiled game ({stamp}). Run it again after a build.", "",
         f"**{len(R)} kinds:** {n['gear row']} from the gear catalogue (art/enhance/catalogue.json), "
         f"{n['item row']} from the item catalogue (art/items/catalogue.json), {n['2006']} written in the 2006 files and "
         f"{n['Remastered']} hand-written for Remastered. {len(can)} could be adopted into the item catalogue as they are.", "",
         "- **From:** where its values are written. A catalogue row, or the 2006 or Remastered code (file and line).",
         "- **Own code:** what it does that others of its group don't (its own procs). Adopting never moves code.",
         "- **Made by:** the code that creates it (a workshop's menu, mining, a spell...).",
         "- **Adopt:** yes, if its values are a plain block that can move into a catalogue row, keeping its type name.",
         "  Otherwise, why not.", "",
         "| Group | Kinds | Gear rows | Item rows | 2006 | Remastered | Can adopt |", "|---|---|---|---|---|---|---|"]
    order = sorted(by, key=lambda g: -len(by[g]))
    for g in order:
        c = Counter(r["from"] for r in by[g])
        L.append(f"| [{g}](#{g.lower()}) | {len(by[g])} | {c['gear row']} | {c['item row']} | {c['2006']} | {c['Remastered']} | "
                 f"{sum(1 for r in by[g] if r['adopt'] == 'yes')} |")
    for g in order:
        L += ["", f"## {g}", "", "| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in sorted(by[g], key=lambda r: r["code"]):
            pic = f"{os.path.basename(r['dmi'] or '')}: {r['state'] or ''}" if r["dmi"] else ""
            frm = r["from"] if r["from"] in ("gear row", "item row") else f"{r['from']} ({r['file'].replace('Code/', '')}:{r['line']})"
            made = ", ".join(r["made_by"][:3]) + (f" +{len(r['made_by']) - 3}" if len(r["made_by"]) > 3 else "")
            name = cell(r["name"]) + (f" *(group of {r['kinds_below']})*" if r["kinds_below"] else "")
            L.append("| " + " | ".join(cell(x) for x in (name, r["code"], pic, r["weight"], " ".join(r["cats"]), frm,
                                                          ", ".join(r["own_code"]), made, r["adopt"])) + " |")
    open(path, "w").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--game", default=os.path.join(ROOT, "game"))
    ap.add_argument("--json", help="the compiled game (default: Cave Crawlers.json in the game folder)")
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()
    j = a.json or os.path.join(a.game, "Cave Crawlers.json")
    G = Game(a.game, j)
    R = rows(G)
    stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(j)))
    write_md(R, os.path.join(a.out, "ITEM_LIST.md"), stamp)
    json.dump(R, open(os.path.join(a.out, "item_list.json"), "w"), indent=1)
    c = Counter(r["from"] for r in R)
    print(f"{len(R)} kinds ({dict(c)}), {sum(1 for r in R if r['adopt'] == 'yes')} can be adopted -> {a.out}/ITEM_LIST.md")


if __name__ == "__main__":
    main()
