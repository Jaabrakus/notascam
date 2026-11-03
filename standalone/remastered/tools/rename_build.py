#!/usr/bin/env python3
"""Rename build (2026-10-24, Banners of the Deep; before that Land of Lords on 2026-10-23): brand art, the app, then
every older bundle path becomes a symlink to the new one so every script and session that still says
'Land of Lords.app' or 'Dungeon Master Remastered.app' keeps working. An older bundle that is a real folder is moved
to restore-points/, never deleted.
Run through the lock as a build:  python3 tools/runlock.py --who <you> -- python3 tools/rename_build.py"""
import shutil, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT/'tools/make_client_brand.py')], check=True)
subprocess.run([sys.executable, str(ROOT/'tools/build_app.py')], check=True)
new = ROOT/'Banners of the Deep.app'
if not new.is_dir() or new.is_symlink(): raise SystemExit('no new app built')
for old in (ROOT/'Land of Lords.app', ROOT/'Dungeon Master Remastered.app'):
    if old.is_symlink(): old.unlink()
    elif old.exists():
        keep = ROOT/'restore-points'/f'{old.stem.replace(" ", "-")}-app-{time.strftime("%Y%m%d-%H%M")}'
        keep.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old), str(keep/old.name))
        print('kept the old bundle in', keep)
    old.symlink_to(new.name)
    print('symlink', old.name, '->', new.name)
