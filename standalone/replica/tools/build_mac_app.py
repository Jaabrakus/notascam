#!/usr/bin/env python3
"""Package the tested game with a native launcher; Python is build-time only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
from skin_layout import write_hints

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'Dungeon Master.app'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-dir',type=Path,default=ROOT/'runtime/macos-x64/server')
    parser.add_argument('--output',type=Path,default=APP,help='app bundle to (re)build')
    parser.add_argument('--shareable',action='store_true',
        help='omit your saves and name each player after their Mac account, for giving to others')
    args=parser.parse_args()
    app=args.output
    contents=app/'Contents';resources=contents/'Resources';binary=contents/'MacOS/DungeonMaster'
    binary.parent.mkdir(parents=True,exist_ok=True);resources.mkdir(parents=True,exist_ok=True)
    with (ROOT/'reports/mac-launcher-build.log').open('w') as log:
        subprocess.run(['/usr/bin/clang','-arch','arm64','-arch','x86_64','-fobjc-arc','-I',str(ROOT/'mac-app'),
            '-mmacosx-version-min=11.0','-framework','Cocoa',str(ROOT/'mac-app/Launcher.m'),
            '-o',str(binary)],stdout=log,stderr=subprocess.STDOUT,check=True)
    plist=dict(CFBundleExecutable='DungeonMaster',CFBundleIdentifier='local.dungeonmaster.standalone',
        CFBundleName='Dungeon Master',CFBundleDisplayName='Dungeon Master',CFBundlePackageType='APPL',
        CFBundleShortVersionString='0.2',CFBundleVersion='20261016',LSMinimumSystemVersion='15.0',
        NSHighResolutionCapable=True,NSPrincipalClass='NSApplication')
    (contents/'Info.plist').write_bytes(plistlib.dumps(plist))
    shutil.copy2(ROOT/'mac-app/launch.zsh',resources/'launch.zsh');(resources/'launch.zsh').chmod(0o755)
    shutil.copy2(ROOT/'mac-app/local_save.zsh',resources/'local_save.zsh')
    subprocess.run(['/bin/zsh','-n',str(resources/'local_save.zsh')],check=True)
    subprocess.run(['/bin/zsh','-n',str(resources/'launch.zsh')],check=True)
    game=resources/'game';game.mkdir(exist_ok=True)
    # Only app-owned generated package directories are replaced, never live saves.
    runtime=game/'runtime'
    if runtime.exists():shutil.rmtree(runtime)
    runtime.mkdir()
    def ignored(directory,names):
        return [n for n in names if n.endswith(('.upstream','.log','.pending')) or '.pre-' in n or n in ('.DS_Store','logs','user_data') or n.startswith('strings-')]
    for name in ('dotnet','server','client','webview-webkit'):
        shutil.copytree(args.server_dir if name=='server' else ROOT/'runtime/macos-x64'/name,runtime/name,ignore=ignored)
    world=game/'world'
    if world.exists():shutil.rmtree(world)
    def ignore_world(directory,names):
        return [n for n in names if n in ('units','players','ErrorLog.txt','.DS_Store') or
            n.endswith(('.dm','.dme','.dmm','.dmb','.sav','.log')) or
            (n.endswith('.json') and n!='Cave Crawlers.json')]
    shutil.copytree(ROOT/'opendream',world,ignore=ignore_world)
    initial=game/'initial-saves'
    if initial.exists():shutil.rmtree(initial)
    initial.mkdir()
    if not args.shareable:
        for name in ('units','players'):
            source=ROOT/'opendream'/name
            if source.exists():shutil.copytree(source,initial/name)
    # Saves are keyed by player name: keep yours as Kiwi; shared copies use the Mac account.
    (game/'player-name').write_text('@login\n' if args.shareable else 'Kiwi\n')
    licenses=resources/'licenses'
    if licenses.exists():shutil.rmtree(licenses)
    licenses.mkdir()
    for source,name in [(ROOT/'source/LICENSE','Dungeon-Master-GPL-2.0.txt'),(ROOT/'engine/LICENSE-OpenDream.txt','OpenDream-MIT.txt'),
            (ROOT/'engine/RobustToolbox-LICENSE-MIT.TXT','RobustToolbox-MIT.txt'),(ROOT/'engine/RobustToolbox-LICENSE-ASSETS.TXT','RobustToolbox-assets.txt'),
            (ROOT/'engine/RobustToolbox-LICENSE-GPLv3.TXT','RobustToolbox-GPLv3.txt'),(ROOT/'runtime/macos-x64/dotnet/LICENSE.txt','dotnet-MIT.txt'),
            (ROOT/'runtime/macos-x64/dotnet/ThirdPartyNotices.txt','dotnet-third-party-notices.txt')]:
        shutil.copy2(source,licenses/name)
    write_hints(ROOT/'opendream/skin.dmf',game/'skin-layout-hints.json')
    marker=sha(runtime/'server/Resources/Assemblies/OpenDreamRuntime.dll')+sha(runtime/'server/Content.Client.zip')+sha(runtime/'webview-webkit/Robust.Client.WebView.dll')
    for asset in sorted(p for p in world.rglob('*') if p.is_file()):
        marker+=str(asset.relative_to(world))+sha(asset)
    (game/'build-id').write_text(hashlib.sha256(marker.encode()).hexdigest()+'\n')
    license_source=Path('/private/tmp/dm-runtime-audit/opendream-source/OpenDream-latest/LICENSE')
    if license_source.exists():shutil.copy2(license_source,resources/'OpenDream-LICENSE.txt')
    files=[p for p in app.rglob('*') if p.is_file()]
    external=[]
    for p in app.rglob('*'):
        if p.is_symlink() and app.resolve() not in p.resolve().parents:external.append(str(p))
    if external:raise RuntimeError('Package has external symlinks: '+repr(external))
    result=dict(app=str(app),shareable=args.shareable,bytes=sum(p.stat().st_size for p in files),files=len(files),external_symlinks=external,
        runtime_sha256=sha(runtime/'server/Resources/Assemblies/OpenDreamRuntime.dll'),
        compiled_game_sha256=sha(world/'Cave Crawlers.json'),launcher_sha256=sha(binary),
        runtime_dependencies=['macOS 15 or later (this package tested only on the current Mac)','Rosetta 2 on Apple Silicon for bundled x64 engine'],
        bundled=['.NET runtime','game server','native client','WebKit bridge','original game assets and compiled game'],
        development_dependencies_required_to_play=[],
        save_location='~/Library/Application Support/Dungeon Master Standalone/world',
        initial_saves='None; each player starts fresh under their Mac account name.' if args.shareable else
            'Personal package includes a copy of existing standalone saves; first launch imports them without changing originals.',
        exact_replica_verified=False)
    (ROOT/('reports/mac-app-share-package.json' if args.shareable else 'reports/mac-app-package.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
