#!/usr/bin/env python3
"""Read-only source inventory; writes only planning artifacts.

This is a navigable index, not a DM compiler or a passing playtest report.
Only included source is scanned; manual interpretation lives in the main plan.
"""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "dist/Dungeon Master Remastered/Source/game"
OUT = ROOT / "planning"
EVENTS = {"Click", "DblClick", "MouseDrag", "MouseDrop", "MouseDown", "MouseUp",
          "MouseEntered", "MouseExited", "MouseMove", "Bump", "Enter", "Entered",
          "Exit", "Exited", "Crossed", "Topic"}
RESERVED = {"if", "else", "for", "while", "switch", "spawn", "sleep", "return",
            "del", "set", "var", "break", "continue"}


def strip_comments(lines):
    block = False
    for line in lines:
        out, quoted, escaped, i = [], None, False, 0
        while i < len(line):
            ch, pair = line[i], line[i:i+2]
            if block:
                if pair == "*/":
                    block = False
                    i += 2
                else:
                    i += 1
                continue
            if quoted:
                out.append(ch)
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quoted:
                    quoted = None
                i += 1
                continue
            if pair == "//":
                break
            if pair == "/*":
                block = True
                i += 2
                continue
            if ch in "\"'":
                quoted = ch
            out.append(ch)
            i += 1
        yield "".join(out)


def includes():
    found, visited = [], set()
    def walk(path):
        path = path.resolve()
        if path in visited:
            return
        visited.add(path)
        if path.suffix == ".dm":
            found.append(path)
        for line in strip_comments(path.read_text(encoding="latin-1").splitlines()):
            match = re.match(r'\s*#include\s+"([^"]+)"', line)
            if not match:
                continue
            relative = match[1].replace("\\", "/")
            target = path.parent / relative
            if not target.exists():
                target = BASE / relative
            if target.suffix in (".dm", ".dme"):
                walk(target)
    walk(BASE / "Cave Crawlers.dme")
    return found


def scan(path):
    rel = str(path.relative_to(BASE.resolve()))
    records = {k: [] for k in ("verbs", "handlers", "choices", "modes", "prompts")}
    stack, current = [], None
    for number, raw in enumerate(strip_comments(path.read_text(encoding="latin-1").splitlines()), 1):
        if not raw.strip():
            continue
        indent, text = len(raw) - len(raw.lstrip("\t")), raw.strip()
        if current and indent <= current["indent"]:
            current = None
        if not current:
            while stack and stack[-1][0] >= indent:
                stack.pop()
            match = re.match(r"^(/?[\w/]+)\s*\((.*)", text)
            if match and match[1].split("/")[-1] not in RESERVED:
                name = match[1]
                parent = stack[-1][1] if stack and not name.startswith("/") else ""
                full = "/" + "/".join(p for p in (parent.strip("/"), name.strip("/")) if p)
                current = dict(file=rel, line=number, path=full, indent=indent, declaration=text[:280])
                if "/verb/" in full:
                    records["verbs"].append(current)
                if full.split("/")[-1] in EVENTS:
                    records["handlers"].append(current)
            elif re.fullmatch(r"/?[A-Za-z_][\w/]*", text) and text not in RESERVED - {"var"}:
                parent = stack[-1][1] if stack and not text.startswith("/") else ""
                full = "/" + "/".join(p for p in (parent.strip("/"), text.strip("/")) if p)
                stack.append((indent, full))
        context = current["path"] if current else "(declaration)"
        common = dict(file=rel, line=number, context=context)
        for match in re.finditer(r'\b((?:menu|option|choice)\w*)\s*\+=\s*"((?:\\.|[^"\\])*)"', text, re.I):
            records["choices"].append(dict(common, variable=match[1], label=match[2], expression=text[:360]))
        for match in re.finditer(r'\bFunction\s*=\s*"([^"]+)"', text):
            records["modes"].append(dict(common, mode=match[1], expression=text[:360]))
        if re.search(r"\b(?:input|alert)\s*\(", text):
            records["prompts"].append(dict(common, expression=text[:360]))
    return records


def md(value):
    return str(value).replace("|", r"\|").replace("\n", " ")


def link(row):
    return f'[{md(row["file"])}:{row["line"]}]({quote(str(BASE / row["file"]), safe="/")}:{row["line"]})'


def main():
    files = includes()
    report = dict(baseline=str(BASE), limits=[
        "Static index; not proof of runtime behavior or reachability.",
        "Only included files. Menu labels include recipes, submenus and Cancel.",
        "Generated choices and list(...) choices require manual interpretation.",
        "Distributed source is a reference, not certified reproducible source for every executable procedure.",
    ])
    report["compiled_app_sha256"] = hashlib.sha256((ROOT / "Dungeon Master Remastered.app/Contents/Resources/game/world/Cave Crawlers.json").read_bytes()).hexdigest()
    for k in ("sources", "verbs", "handlers", "choices", "modes", "prompts", "macros", "menu_commands", "actions"):
        report[k] = []
    for path in files:
        report["sources"].append(dict(file=str(path.relative_to(BASE.resolve())), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        for k, rows in scan(path).items():
            report[k].extend(rows)
    name, section = None, None
    for number, line in enumerate((BASE / "skin.dmf").read_text(encoding="latin-1").splitlines(), 1):
        if line.startswith("window "):
            break
        if line.startswith("macro "):
            section, name = "macros", None
        elif line.startswith("menu "):
            section, name = "menu_commands", None
        elif line.lstrip().startswith("elem "):
            name = None
        match = re.search(r'name = "([^"]*)"', line)
        if match:
            name = match[1]
        match = re.search(r'command = "(.*)"', line)
        if name and match and section:
            report[section].append(dict(name=name, command=match[1], file="skin.dmf", line=number))
            name = None
    for number, line in enumerate((BASE / "Code/Remastered/Actions.dm").read_text().splitlines(), 1):
        match = re.search(r'list\("([^"]+)", "([^"]+)", ("[^"]+"|null), ([01]), ([^)]+)\)', line)
        if match:
            report["actions"].append(dict(id=match[1], label=match[2], key=match[3], needs_units=bool(int(match[4])), hud=match[5], file="Code/Remastered/Actions.dm", line=number))
    report["counts"] = {k: len(report[k]) for k in ("sources", "verbs", "handlers", "choices", "modes", "prompts", "macros", "menu_commands", "actions")}
    OUT.mkdir(exist_ok=True)
    (OUT / "action-catalog.json").write_text(json.dumps(report, indent=2) + "\n")
    doc = ["# Existing action source catalog", "",
           "Generated from the distributed pre-redesign source by catalog_actions.py. Read [the planning inventory](../ACTION_INTERACTION_INVENTORY.md) for behavior, gates and touch proposals.", "",
           "**Source index, not a passing playtest report.** Repeated recipe names, submenus and Cancel are not independent mechanics. Counts must not be treated as a completion percentage.", "",
           "| Indexed item | Count |", "| --- | ---: |"]
    doc += [f"| {k} | {v} |" for k, v in report["counts"].items()]
    doc += ["", "## Actions panel", "", "| ID | Label | Key | Needs selection | HUD bridge | Source |", "| --- | --- | --- | --- | --- | --- |"]
    for a in report["actions"]:
        doc.append(f'| {a["id"]} | {md(a["label"])} | {md(a["key"])} | {a["needs_units"]} | {a["hud"]} | {link(a)} |')
    doc += ["", "## Keyboard macros", "", "| Key | Command | Source |", "| --- | --- | --- |"]
    for m in report["macros"]:
        doc.append(f'| {md(m["name"])} | {md(m["command"])} | {link(m)} |')
    doc += ["", "## Native menu commands", "", "| Menu item | Command | Source |", "| --- | --- | --- |"]
    for m in report["menu_commands"]:
        doc.append(f'| {md(m["name"])} | {md(m["command"])} | {link(m)} |')
    for section, key in [("Verb declarations (including host/admin)", "verbs"), ("Mouse, collision and Topic handlers", "handlers")]:
        doc += ["", "## " + section, "", "| Entry point | Source |", "| --- | --- |"]
        doc += [f'| {md(p["path"])} | {link(p)} |' for p in report[key]]
    doc += ["", "## Placement and targeting modes", "", "| Mode | Entry point | Source |", "| --- | --- | --- |"]
    doc += [f'| {md(m["mode"])} | {md(m["context"])} | {link(m)} |' for m in report["modes"]]
    doc += ["", "## Menu labels by included source file", "", "Repeated labels remain because targets and gates can differ. Source links lead to the conditions. Generated lists are indexed under prompt sites.", ""]
    for source in report["sources"]:
        rows = [c for c in report["choices"] if c["file"] == source["file"]]
        if not rows:
            continue
        doc += ["### " + source["file"], "", "| Literal option | Menu | Entry point | Source |", "| --- | --- | --- | --- |"]
        doc += [f'| {md(c["label"])} | {c["variable"]} | {md(c["context"])} | {link(c)} |' for c in rows]
        doc.append("")
    doc += ["## Prompt sites, including generated choices", "", "| Entry point | Input expression (abridged) | Source |", "| --- | --- | --- |"]
    doc += [f'| {md(p["context"])} | {md(p["expression"])} | {link(p)} |' for p in report["prompts"]]
    doc += ["", "## Included source manifest", "", "| File | SHA-256 |", "| --- | --- |"]
    doc += [f'| {s["file"]} | {s["sha256"]} |' for s in report["sources"]]
    (OUT / "ACTION_CATALOG.md").write_text("\n".join(doc) + "\n")
    print(json.dumps(report["counts"], indent=2))


if __name__ == "__main__":
    main()
