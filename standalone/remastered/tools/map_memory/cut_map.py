#!/usr/bin/env python3
"""Cuts a window of the real world (game/Maps/1-Ground ... 4-Hell.dmm, all four layers) into one small .dmm, for
arena tests of the real land (planning/MAP_MEMORY.md): tools/map_memory/cut_map.py X0 Y0 W H OUT.dmm. Turfs, areas,
objects and mobs come as the map files have them (with their var edits); coordinates start again at 1,1.
--census prints what each 128x128 block of the window holds instead (no file written)."""
import argparse, collections, re
from pathlib import Path

MAPS = Path(__file__).resolve().parents[2]/'game/Maps'
FILES = ['1-Ground.dmm', '2-Underground.dmm', '3-Sky.dmm', '4-Hell.dmm']


def split_parts(body):
    parts, depth, cur, quote = [], 0, '', False
    for ch in body:
        if ch == '"' : quote = not quote
        if not quote:
            if ch == '{': depth += 1
            if ch == '}': depth -= 1
            if ch == ',' and depth == 0:
                parts.append(cur); cur = ''; continue
        cur += ch
    parts.append(cur)
    return parts


def load(name):
    t = (MAPS/name).read_text(encoding='latin-1')
    keys = {m.group(1): m.group(2) for m in re.finditer(r'^"(\w+)" = \((.*)\)\s*$', t, re.M)}
    (gx, gy, gz, body), = re.findall(r'^\((\d+),(\d+),(\d+)\) = \{"\n(.*?)\n"\}', t, re.M | re.S)
    assert (gx, gy) == ('1', '1')
    rows = body.split('\n')
    kl = len(next(iter(keys)))
    return keys, rows, kl


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('x0', type=int); ap.add_argument('y0', type=int); ap.add_argument('w', type=int); ap.add_argument('h', type=int)
    ap.add_argument('out', nargs='?')
    ap.add_argument('--census', action='store_true')
    a = ap.parse_args()
    defs, out_keys = {}, []          # definition text -> new key
    grids = []
    census = []
    for z, name in enumerate(FILES, 1):
        keys, rows, kl = load(name)
        H = len(rows)
        grid = []
        counts = collections.defaultdict(collections.Counter)
        for y in range(a.y0 + a.h - 1, a.y0 - 1, -1):            # top row first, as .dmm files have it
            row = rows[H - y]
            line = []
            for x in range(a.x0, a.x0 + a.w):
                k = row[(x - 1) * kl:x * kl]
                d = keys[k]
                if d not in defs: defs[d] = None
                line.append(d)
                blk = ((x - a.x0) // 128, (y - a.y0) // 128)
                for p in split_parts(d):
                    path = p.split('{')[0]
                    kind = 'turf ' + path.split('/')[-1] if path.startswith('/turf') else 'obj' if path.startswith('/obj') else 'mob' if path.startswith('/mob') else None
                    if kind: counts[blk][kind] += 1
            grid.append(line)
        grids.append(grid)
        census.append(counts)
    if a.census:
        for z, counts in enumerate(census, 1):
            for blk in sorted(counts):
                c = counts[blk]
                print(f'z{z} block{blk}:', ', '.join(f'{k} {v}' for k, v in c.most_common(9)))
        return
    letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    n = len(defs)
    kl = 1
    while len(letters) ** kl < n: kl += 1
    def key(i):
        s = ''
        for _ in range(kl):
            s = letters[i % len(letters)] + s; i //= len(letters)
        return s
    for i, d in enumerate(defs): defs[d] = key(i)
    lines = [f'"{k}" = ({d})' for d, k in defs.items()]
    for z, grid in enumerate(grids, 1):
        lines.append('')
        lines.append(f'(1,1,{z}) = {{"')
        lines.extend(''.join(defs[d] for d in row) for row in grid)
        lines.append('"}')
    Path(a.out).write_text('\n'.join(lines) + '\n', encoding='latin-1')
    print(f'wrote {a.out}: {a.w}x{a.h}x4, {n} cell kinds')


if __name__ == '__main__':
    main()
