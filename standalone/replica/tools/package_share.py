#!/usr/bin/env python3
"""Build the shareable app and zip it with player instructions and the GPL source."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'

HOW_TO_OPEN='''Dungeon Master for Mac
======================

Needs macOS 15 (Sequoia) or later. On Apple Silicon Macs the game engine runs
through Rosetta 2; if Rosetta is missing the game will say so and tell you how
to install it.

FIRST TIME OPENING
------------------
This app is not signed with an Apple developer certificate, so macOS blocks it
the first time. Do this once:

1. Unzip, then drag "Dungeon Master.app" into your Applications folder.
2. Open Terminal and paste this line, then press Return:

   xattr -dr com.apple.quarantine "/Applications/Dungeon Master.app"

3. Double-click Dungeon Master. The first launch takes about a minute.

(Instead of step 2 you can double-click the app, click Done on the warning,
then go to System Settings > Privacy & Security, scroll down and click
"Open Anyway". Step 2 is more reliable because it also clears the engine files
inside the app.)

PLAYING
-------
- R: choose your race and start
- Arrow keys / numpad: move the view
- Double-click your units to select them; click the ground to send them there
- Space: clear the selection
- Alt+1-9: select group, Ctrl+Alt+1-9: set group, Shift+Alt+1-9: add to group

Closing the game saves your units. Saves are in
~/Library/Application Support/Dungeon Master Standalone
This build is single-player on your own Mac.

SOURCE AND LICENSES
-------------------
Dungeon Master is copyright Aaron Davey and contributors, under the GNU GPL
version 2 (see Source/original/LICENSE). The game runs on OpenDream and
RobustToolbox (MIT) with the .NET runtime (MIT); their licenses are inside the
app at Contents/Resources/licenses. Source/original is the unmodified game,
Source/adapted is the copy compiled into this app, and Source/engine-changes
holds the engine and Mac-client modifications.
'''


def copy_tree(source,target,ignore=None):
    shutil.copytree(source,target,ignore=ignore,symlinks=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-build',action='store_true',help='zip the existing dist/Dungeon Master.app')
    args=parser.parse_args()
    app=DIST/'Dungeon Master.app'
    if not args.skip_build:
        subprocess.run([sys.executable,str(ROOT/'tools/build_mac_app.py'),'--shareable','--output',str(app)],check=True,stdout=subprocess.DEVNULL)
    if (app/'Contents/Resources/game/player-name').read_text().strip()!='@login' or any((app/'Contents/Resources/game/initial-saves').iterdir()):
        raise SystemExit('dist app is a personal build; rebuild with --shareable')
    stage=DIST/'Dungeon Master'
    if stage.exists():shutil.rmtree(stage)
    stage.mkdir()
    subprocess.run(['/usr/bin/ditto',str(app),str(stage/app.name)],check=True)
    (stage/'How to open.txt').write_text(HOW_TO_OPEN)
    source=stage/'Source'
    copy_tree(ROOT/'source',source/'original',ignore=shutil.ignore_patterns('.DS_Store'))
    # Generated output, logs and saves are not source.
    copy_tree(ROOT/'opendream',source/'adapted',ignore=lambda d,names:[n for n in names if n in ('units','players','ErrorLog.txt','.DS_Store','Cave Crawlers.json') or n.endswith(('.log','.sav','.dmb'))])
    changes=source/'engine-changes';changes.mkdir()
    for path in sorted((ROOT/'engine').glob('*')):
        if path.suffix in ('.patch','.cs') or path.name.startswith(('LICENSE','RobustToolbox-LICENSE')):shutil.copy2(path,changes/path.name)
    for name in ('MacWebViewManager.cs','NativeUiProbe.cs','WebKitBridge.swift','README.md'):
        shutil.copy2(ROOT/'mac-webview'/name,changes/('mac-webview-'+name))
    for name in ('Launcher.m','launch.zsh','local_save.zsh'):shutil.copy2(ROOT/'mac-app'/name,changes/('mac-app-'+name))
    shutil.copy2(ROOT/'mac-app/LauncherOutcome.h',changes/'LauncherOutcome.h')
    for name in ('prepare_opendream.py','compact_conditionals.py','build_compat_runtime.py','build_client_compat.py','build_mac_webview.py','build_mac_app.py','skin_layout.py','package_share.py'):
        shutil.copy2(ROOT/'tools'/name,changes/('tools-'+name))
    # Refuse to ship personal files or paths.
    # Source/original is the hash-frozen download (it ships its own map_backup.sav).
    leaks=[]
    for path in stage.rglob('*'):
        if path.is_file() and source/'original' not in path.parents and (path.suffix=='.sav' or 'kiwi' in path.name.lower()):leaks.append(str(path))
    found=subprocess.run(['/usr/bin/grep','-rIl','-i',Path.home().name,str(stage)],capture_output=True,text=True).stdout.split()
    leaks+=found
    if leaks:raise SystemExit('Personal data in share folder: '+repr(leaks[:10]))
    archive=DIST/'Dungeon-Master-mac.zip'
    archive.unlink(missing_ok=True)
    subprocess.run(['/usr/bin/ditto','-c','-k','--sequesterRsrc','--keepParent',str(stage),str(archive)],check=True)
    result=dict(archive=str(archive),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        contents=sorted(p.name for p in stage.iterdir()),
        notes=['Unsigned and not notarized; recipients clear quarantine once (see How to open.txt).',
               'Bundled engine is x64; Apple Silicon needs Rosetta 2.','Includes GPL-2.0 game source.'])
    (ROOT/'reports/share-package.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
