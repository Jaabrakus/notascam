"""Where the game's DM source sets each type's values and defines its procs (art/items: the item list, the exporter's
adopt mode and its check that a row and the old files never both set the same value).

    src = dmsource.read(game_dir)      # only the files the .dme includes
    src.assigns["/obj/Items/ores/Iron"]  -> [Assign(var, file, first, last)]   name = "Iron", icon = 'Cave.dmi' ...
    src.headers["/obj/Items/ores/Iron"]  -> [(file, line)]                    where a block for the type starts
    src.procs                            -> [Proc(owner, name, file, line, body)]  body: [(line, code)]

It reads the source the way the compiler lays it out (indentation, paths written whole or nested, proc bodies,
var blocks) with comments, strings and file names blanked, so a path inside a string or a comment is never taken for
code. It doesn't evaluate anything: values come from the compiled game (Cave Crawlers.json)."""
import os
import re
from collections import defaultdict, namedtuple

Assign = namedtuple("Assign", "var file first last")
Proc = namedtuple("Proc", "owner name file line body")
PATH = re.compile(r"^(/?[A-Za-z_]\w*(?:/[A-Za-z_]\w*)*)\s*(.*)$")


def included(game):
    """The .dm files the .dme compiles, relative to the game folder, in its order."""
    dme = next(f for f in os.listdir(game) if f.endswith(".dme"))
    out = []
    for ln in open(os.path.join(game, dme), encoding="latin-1"):
        m = re.match(r'\s*#include\s+"([^"]+\.dm)"', ln)
        if m: out.append(m.group(1).replace("\\", "/"))
    return out


def _string(t, i, n, close):
    """Skip a string from just inside its opening quote; returns (index after it, newlines in it)."""
    nl, depth = 0, 0
    while i < n:
        c = t[i]
        if c == "\n":
            nl += 1
            if close == '"' and depth == 0: return i, nl - 1     # a plain string never spans lines: stop at the end
        if c == "\\": i += 2; continue
        if depth == 0 and t.startswith(close, i): return i + len(close), nl
        if c == "[": depth += 1
        elif c == "]" and depth: depth -= 1
        elif c == '"' and depth:                                    # a string inside an embedded [expression]
            i, k = _string(t, i + 1, n, '"'); nl += k; continue
        i += 1
    return i, nl


def logical_lines(text):
    """[(first line, last line, code)]: comments dropped, strings and file names blanked to "" and '', and a {" "}
    string, a /* */ comment or a line ending in \\ joining physical lines into one."""
    out, buf, i, n, line, start, depth = [], [], 0, len(text), 1, 1, 0
    while i < n:
        c = text[i]
        if c == "\n":
            s = "".join(buf)
            if s.rstrip().endswith("\\"):
                buf = [s.rstrip()[:-1]]
            elif depth > 0:                       # an open list( ... ) carries on to the next line
                buf.append(" ")
            else:
                out.append((start, line, s)); buf = []; start = line + 1
            line += 1; i += 1
            continue
        if text.startswith("//", i):
            j = text.find("\n", i); i = n if j < 0 else j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2); j = n if j < 0 else j + 2
            line += text.count("\n", i, j); i = j
            continue
        if text.startswith('{"', i):
            i, k = _string(text, i + 2, n, '"}'); line += k; buf.append('""')
            continue
        if c == '"':
            i, k = _string(text, i + 1, n, '"'); line += k; buf.append('""')
            continue
        if c == "'":
            j = text.find("'", i + 1); j = n if j < 0 else j + 1
            i = j; buf.append("''")
            continue
        if c in "([": depth += 1
        elif c in ")]" and depth: depth -= 1
        buf.append(c); i += 1
    if buf: out.append((start, line, "".join(buf)))
    # #if 0 ... #endif is never compiled
    keep, off = [], 0
    for a, b, s in out:
        d = s.strip()
        if off:
            if d.startswith("#if"): off += 1
            elif d.startswith("#endif"): off -= 1
            continue
        if re.match(r"#if\s+0\b", d): off = 1; continue
        keep.append((a, b, s))
    return keep


def _indent(s):
    w = 0
    for c in s:
        if c == "\t": w += 4
        elif c == " ": w += 1
        else: break
    return w


def _join(base, p):
    return "/" + p.strip("/") if p.startswith("/") or not base else base + "/" + p


class Source:
    def __init__(self):
        self.assigns = defaultdict(list)
        self.headers = defaultdict(list)
        self.procs = []

    def read_file(self, rel, text):
        stack = []      # (indent, kind, path): kind type | proc | var | procs
        for a, b, code in logical_lines(text):
            s = code.strip()
            if not s or s.startswith("#"): continue
            ind = _indent(code)
            while stack and stack[-1][0] >= ind: stack.pop()
            proc = next((x for x in reversed(stack) if x[1] == "proc"), None)
            if proc:
                proc[2].body.append((a, s))
                continue
            kind = stack[-1][1] if stack else None
            base = stack[-1][2] if stack else ""
            m = PATH.match(s)
            if not m: continue
            p, rest = m.groups()
            if kind == "var":
                stack.append((ind, "var", base))        # a var block: declarations, not values of a type
                continue
            full = _join(base, p)
            segs = full.strip("/").split("/")
            if rest.startswith("("):
                owner = segs[:-1]
                if owner and owner[-1] in ("proc", "verb"): owner = owner[:-1]
                P = Proc("/" + "/".join(owner), segs[-1], rel, a, [])
                self.procs.append(P)
                stack.append((ind, "proc", P))
            elif "var" in segs:
                if not rest: stack.append((ind, "var", "/" + "/".join(segs[:segs.index("var")])))   # var/tmp/list: a block
            elif kind == "procs":
                pass
            elif segs[-1] in ("proc", "verb") and not rest:
                stack.append((ind, "procs", "/" + "/".join(segs[:-1])))
            elif rest.startswith("=") and not rest.startswith("=="):
                self.assigns["/" + "/".join(segs[:-1])].append(Assign(segs[-1], rel, a, b))
            elif not rest:
                self.headers[full].append((rel, a))
                stack.append((ind, "type", full))


def read(game):
    src = Source()
    for rel in included(game):
        path = os.path.join(game, rel)
        if os.path.exists(path):
            src.read_file(rel, open(path, encoding="latin-1").read())
    return src
