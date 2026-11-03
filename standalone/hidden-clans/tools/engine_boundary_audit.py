#!/usr/bin/env python3
"""The engine/game boundary (U3 of planning/SERVER_UPGRADES_PLAN_2026-10-30.md, 2026-10-30).

    python3 -I tools/engine_boundary_audit.py                    exit 0 when engine/core holds nothing new of the game's
    python3 -I tools/engine_boundary_audit.py --update-baseline  take today's names as known (only after review)

engine/core/ is what any DM game could use; engine/game-botd/ is what knows Banners of the Deep. In a core file this
looks for the names that tie code to a game:
  var    a var read or written by name (TryGetVariable, GetVariable, SetVariable and RmNative's Truthy, VarEquals,
         VarString, VarIsObject), other than DM's own (x, loc, density...)
  proc   a global proc looked up by name (TryGetGlobalProc, GetGlobalProc), other than a native core itself implements
  type   a type path ("/mob/...")
  value  a text value compared against (new DreamValue("...") or new("..."))
Names already in tools/engine_boundary_baseline.json are known (each with why); anything else fails. It only matches
names: a rule can hide in plain numbers, so a new native's review still asks "is this a rule?" (OpenRealm's lesson).
It also checks the layout: no .cs left in engine/native/, no file in both folders."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE, GAME, OLD = ROOT/'engine/core', ROOT/'engine/game-botd', ROOT/'engine/native'
BASELINE = ROOT/'tools/engine_boundary_baseline.json'
# DM's own vars and the engine's own fields: any game has them
DM_VARS = {'x', 'y', 'z', 'loc', 'density', 'opacity', 'icon', 'icon_state', 'dir', 'name', 'desc', 'type', 'parent_type',
           'contents', 'vars', 'tag', 'layer', 'invisibility', 'overlays', 'underlays', 'appearance', 'verbs', 'key', 'ckey',
           'client', 'mob', 'step_x', 'step_y', 'pixel_x', 'pixel_y', 'luminosity', 'mouse_opacity', 'alpha', 'color'}
LIT = r'\$?"((?:[^"\\\n]|\\.)*)"'
PATTERNS = {
    'var': re.compile(r'\b(?:TryGetVariable|GetVariable|SetVariable|Truthy|VarEquals|VarString|VarIsObject)\(\s*(?:[^,()"]+,\s*)?' + LIT),
    'proc': re.compile(r'\b(?:TryGetGlobalProc|GetGlobalProc)\(\s*' + LIT),
    'type': re.compile(r'(?<![\w@])"(/[a-z_][\w/]*)"'),
    'value': re.compile(r'\bnew(?:\s+DreamValue)?\(\s*"((?:[^"\\\n]|\\.)*)"\s*\)'),   # not $"..." (a formatted report)
}
IMPL = re.compile(r'\[DreamProc\("([^"]+)"\)\]')


def code_lines(text):
    """Each line with its // comment cut off (outside string literals)."""
    for n, line in enumerate(text.split('\n'), 1):
        out, q = [], False
        i = 0
        while i < len(line):
            c = line[i]
            if q and c == '\\': out.append(line[i:i + 2]); i += 2; continue
            if c == '"': q = not q
            if not q and line.startswith('//', i): break
            out.append(c); i += 1
        yield n, ''.join(out)


def scan(folder):
    found = []
    implemented = set()
    for f in sorted(folder.glob('*.cs')):
        implemented |= set(IMPL.findall(f.read_text(encoding='utf-8-sig')))
    for f in sorted(folder.glob('*.cs')):
        for n, line in code_lines(f.read_text(encoding='utf-8-sig')):
            for kind, pat in PATTERNS.items():
                for m in pat.finditer(line):
                    name = m.group(1)
                    if kind == 'var' and name in DM_VARS: continue
                    if kind == 'proc' and name in implemented: continue
                    found.append({'file': f.name, 'line': n, 'kind': kind, 'name': name})
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--update-baseline', action='store_true', help="write today's core names as known (review them first)")
    a = ap.parse_args()
    bad = []
    stale = sorted(p.name for p in OLD.glob('*.cs'))
    if stale: bad.append(f'engine/native/ still holds {", ".join(stale)}: move each into engine/core or engine/game-botd')
    both = sorted({p.name for p in CORE.glob('*.cs')} & {p.name for p in GAME.glob('*.cs')})
    if both: bad.append(f'in both folders: {", ".join(both)}')
    found = scan(CORE)
    keys = sorted({f"{x['file']}|{x['kind']}|{x['name']}" for x in found})
    if a.update_baseline:
        old = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
        why = old.get('why', {})
        BASELINE.write_text(json.dumps({'why': why, 'known': keys}, indent=1) + '\n')
        print(f'baseline: {len(keys)} known names in engine/core ({BASELINE.relative_to(ROOT)})')
        return 0
    known = set(json.loads(BASELINE.read_text())['known']) if BASELINE.exists() else set()
    new = [x for x in found if f"{x['file']}|{x['kind']}|{x['name']}" not in known]
    for x in new: bad.append(f"engine/core/{x['file']}:{x['line']}: {x['kind']} {x['name']!r} names the game")
    gone = sorted(known - set(keys))
    game_files = sorted(p.name for p in GAME.glob('*.cs'))
    print(f'engine/core: {len(list(CORE.glob("*.cs")))} files, {len(keys)} known game names ({len(gone)} known ones gone); '
          f'engine/game-botd: {len(game_files)} files')
    if gone: print('  no longer in core (take them out of the baseline with --update-baseline):', ', '.join(gone))
    for line in bad: print('FAIL', line)
    print('PASS' if not bad else f'FAIL ({len(bad)})')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
