#!/usr/bin/env python3
"""Earlier versions of the game's icons, for the save patch (engine/save/save_patch.py; reports/map-memory/join-hitch.md).

Unit saves written before the patch hold nameless copies of packaged icons: byte for byte the icon file as it was when
the thing was first saved (the user's: the original game's Cave.dmi, Human.dmi, LeatherItems.dmi). The patched engine
takes a nameless copy as a packaged icon only when its SHA-256 is one of the versions listed here, so a composed or turned
icon (a different picture) can never be mistaken for one. Writes <game>/icon-history.txt:
    {"version": 1, "icons": {"<sha256>": "<file name>.dmi", ...}}
The engine resolves each file name to the one packaged icon with that name (skipped if none or several).
A .txt file (its content is JSON): the app build ships the world folder's .txt files, not its .json ones.

    python3 tools/icon_history.py            # writes game/icon-history.txt
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # standalone/remastered
SOURCES = [ROOT.parent / 'replica/dist/Dungeon Master/Source/original',   # the original game
           ROOT / 'restore-points',                                     # every saved state of the game since
           ROOT / 'game']                                               # and the icons as they are now


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', type=Path, default=ROOT / 'game', help='the game folder to write icon-history.txt into')
    a = ap.parse_args()
    names = {p.name for p in a.game.rglob('*.dmi')}   # only icons the game still has
    icons, files = {}, 0
    for src in SOURCES:
        for p in src.rglob('*.dmi'):
            if p.name not in names: continue
            files += 1
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            if icons.setdefault(h, p.name) != p.name: icons[h] = None   # the same bytes under two names: no proof of either
    icons = {h: n for h, n in sorted(icons.items()) if n}
    out = a.game / 'icon-history.txt'
    out.write_text(json.dumps({'version': 1, 'icons': icons}, separators=(',', ':')) + '\n')
    print(f'{out}: {len(icons)} versions of {len(set(icons.values()))} icons, from {files} files')


if __name__ == '__main__':
    main()
