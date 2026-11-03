#!/usr/bin/env python3
"""Two compiled games, type by type: the proof that adopting kinds into the item catalogue changed nothing.

    python3 art/items/compare_compiled.py BEFORE.json AFTER.json [adopted type ...]

Compile a clone of game/ before and after (export_items.py --adopt ... --game CLONE); every type's values, its procs
(name, bytecode size, locals), parent, the global procs, globals and resources must match. The only difference
allowed is the adopted kinds' new rm_item (their row's id). Prints SAME or each difference."""
import json, sys
B, A = (json.load(open(p)) for p in sys.argv[1:3])
adopted = set(sys.argv[3:])
def types(d):
    T = d["Types"]
    out = {}
    for t in T:
        procs = [(d["Procs"][i]["Name"], len(d["Procs"][i].get("Bytecode") or ""), len(d["Procs"][i].get("Locals") or []), d["Procs"][i].get("Attributes")) for g in t.get("Procs", []) for i in g]
        out[t["Path"]] = (t.get("Variables", {}), procs, T[t["Parent"]]["Path"] if t.get("Parent") is not None else None, t.get("InitProc") is not None)
    return out
tb, ta = types(B), types(A)
bad = []
if set(tb) != set(ta): bad.append(("types differ", set(tb) ^ set(ta)))
for p in tb:
    vb, pb, parb, ib = tb[p]; va, pa, para, ia = ta.get(p, ({}, [], None, None))
    va2 = {k: v for k, v in va.items() if not (p in adopted and k == "rm_item")}
    if vb != va2: bad.append((p, "values", {k: (vb.get(k), va2.get(k)) for k in set(vb) | set(va2) if vb.get(k) != va2.get(k)}))
    if pb != pa: bad.append((p, "procs", pb, pa))
    if parb != para or ib != ia: bad.append((p, "parent/init"))
    if p in adopted and va.get("rm_item") is None: bad.append((p, "no rm_item"))
gp = lambda d: sorted((d["Procs"][i]["Name"], len(d["Procs"][i].get("Bytecode") or "")) for i in d["GlobalProcs"]) if isinstance(d["GlobalProcs"], list) else sorted(d["GlobalProcs"])
if gp(B) != gp(A): bad.append("global procs differ")
if sorted(map(str, B["Resources"])) != sorted(map(str, A["Resources"])): bad.append("resources differ")
if B.get("Globals", {}).keys() != A.get("Globals", {}).keys(): bad.append("globals differ")
sB, sA = set(B["Strings"]), set(A["Strings"])
print("strings only before:", sorted(sB - sA)[:10], " only after:", len(sA - sB), sorted(sA - sB)[:5])
print(f"{len(tb)} types compared, {len(adopted)} adopted:", "SAME" if not bad else f"{len(bad)} DIFFERENCES")
for b in bad[:20]: print(" ", b)
