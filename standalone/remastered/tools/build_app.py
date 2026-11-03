#!/usr/bin/env python3
"""Compile Dungeon Master Remastered and package it as its own Mac app.

Uses the replica's engine runtime read-only (standalone/replica/runtime) and never
writes inside standalone/replica. Builds use the current Mac login identity;
legacy Classic save seeding is opt-in. --shareable leaves saves out and zips the app.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPLICA = ROOT.parent/'replica'
RUNTIME = REPLICA/'runtime/macos-x64'
sys.path.insert(0, str(REPLICA/'tools'))
from skin_layout import write_hints  # noqa: E402

NAME = 'Banners of the Deep'      # the .app folder (paths) and the name players see; the old 'Banners of the Deep.app' and 'Dungeon Master Remastered.app' paths are symlinks to it
DISPLAY = 'Banners of the Deep'
CLASSIC_SAVES = Path.home()/'Library/Application Support/Dungeon Master Standalone/world'

HOW_TO_OPEN = '''Banners of the Deep: A Dungeon Master Tale for Mac
============================================

A 3D colony and kingdom game based on Dungeon Master, with Warcraft-style controls. Needs macOS 15 or
later; Apple Silicon Macs run the engine through Rosetta 2 (the game says so if
it is missing).

FIRST TIME OPENING
------------------
The app is not signed with an Apple developer certificate. Once:
1. Unzip and drag "Banners of the Deep.app" into Applications.
2. In Terminal run:  xattr -dr com.apple.quarantine "/Applications/Lands of Lords.app"
3. Double-click it. The first launch takes about a minute.

CONTROLS
--------
R .................... choose your race and start
Arrow keys ........... move the view       , / . ... camera up / down a level
Click your unit ...... select it            Shift+click ... add/remove
Double-click unit .... select all your units of that race in view
Drag on the map ...... box-select your units (Shift+drag adds)
Click ground/tree .... move / chop / mine / collect ordinary resources
Right-click target ... original object and interaction menus
Add tasks ............ append targets to the selected unit's task queue
Shift+click target ... desktop queue shortcut
Drop off ............. queue delivery to the configured stockpile
Unload & resume ...... deliver cargo, then return to the interrupted task
Pause / Resume ....... retain the task list; Stop cancels tasks and pauses roles
1-9 .................. select control group (tap twice to jump to it)
Ctrl+1-9 / Shift+1-9 . set group / add selection to group
Backspace ............ jump to the last unit under attack
Space ................ pause/resume time   Shift+Space ... clear selection
B .................... build menu          F ... aim race special
F3 ................... Controls & Actions guide (every key and button)
Controls ............. labeled border commands and Hide/Show map border

The HUD shows unit state, pending tasks and delivery controls. Work assigns a
Woodcutter, Miner or Hauler within six tiles of the unit's assigned work area.
Selecting another unit leaves existing tasks running. Tools, equipment and food
are kept when delivering supplies. Work offers Wood, Stone, Wood + stone, or
Mining supplies (stone, ores, sand, uncut gems and bones). Fullness, fatigue and injuries still matter.
Original object menus and HUD controls remain available. ACTIONS.md lists the
top-level commands; ACTION_INTERACTION_INVENTORY.md maps the broader game.
Active task queues are session-only; role and stockpile settings are saved.
Saves are in ~/Library/Application Support/Dungeon Master Remastered.

SOURCE AND LICENSES
-------------------
Dungeon Master is copyright Aaron Davey and contributors under the GNU GPL v2.
Source/game is the Remastered game source; Source/engine-changes holds the
engine and Mac client changes. Engine licenses are inside the app at
Contents/Resources/licenses.
'''


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


# The server natively on Apple silicon (load-asleep-1030, 10-31; reports/load-asleep-1030/README.md): Apple silicon's own
# .NET runtime, the same version as the bundled x86-64 one, in runtime/dotnet-arm64, and runtime/server-arm64:
# runtime/server with arm64 builds of its two native libraries (engine/server-arm64/) and Robust.Server.dll and
# Robust.Packaging.dll marked arm64 (pure IL, published marked x86-64). Every other file there links to runtime/server.
# launch.zsh runs the server from them on an arm64 Mac, and from the x86-64 ones otherwise. Nothing else changes.
ARM64_DOTNET = Path.home()/'.dotnet10'
ARM64_NATIVES = ROOT/'engine/server-arm64'
ARM64_MARKED = ('Robust.Server.dll', 'Robust.Packaging.dll')


def mark_arm64(path):
    b = bytearray(path.read_bytes())
    pe = int.from_bytes(b[0x3c:0x40], 'little')
    if b[:2] != b'MZ' or b[pe:pe + 4] != b'PE\0\0' or int.from_bytes(b[pe + 4:pe + 6], 'little') != 0x8664:
        raise SystemExit(f'{path.name}: not an x86-64 PE image; check the arm64 server before building')
    b[pe + 4:pe + 6] = (0xAA64).to_bytes(2, 'little')   # IMAGE_FILE_MACHINE_ARM64; the IL is unchanged
    path.write_bytes(bytes(b))


def add_arm64_server(game):
    version = sorted(p.name for p in (game/'runtime/dotnet/shared/Microsoft.NETCore.App').iterdir())[-1]
    shared = ARM64_DOTNET/'shared/Microsoft.NETCore.App'/version
    libs = sorted(ARM64_NATIVES.glob('*.dylib'))
    if not shared.is_dir() or not (ARM64_DOTNET/'host/fxr'/version).is_dir() or len(libs) < 2:
        print(f'no arm64 server (wanted .NET {version} in {ARM64_DOTNET} and the libraries in {ARM64_NATIVES}): every Mac runs it through Rosetta')
        return
    arm = game/'runtime/dotnet-arm64'
    shutil.copytree(shared, arm/'shared/Microsoft.NETCore.App'/version)
    shutil.copytree(ARM64_DOTNET/'host/fxr'/version, arm/'host/fxr'/version)
    for name in ('dotnet', 'LICENSE.txt', 'ThirdPartyNotices.txt'): shutil.copy2(ARM64_DOTNET/name, arm/name)
    server, server_arm = game/'runtime/server', game/'runtime/server-arm64'
    server_arm.mkdir()
    own = {lib.name for lib in libs} | set(ARM64_MARKED)
    for entry in sorted(server.iterdir()):
        if entry.name not in own: (server_arm/entry.name).symlink_to(Path('../server')/entry.name)
    for lib in libs: shutil.copy2(lib, server_arm/lib.name)
    for name in ARM64_MARKED:
        shutil.copy2(server/name, server_arm/name)
        mark_arm64(server_arm/name)


# The game window natively on Apple silicon too (load-asleep-1030, 10-31): runtime/client-arm64 holds only what differs
# from runtime/client there, the arm64 builds of its native libraries (engine/client-arm64/ from nuget.org, the versions
# the client ships; libzstd and libe_sqlite3 from engine/server-arm64/, the same) and Robust.Client.dll marked arm64 (pure
# IL); launch.zsh lays them over the player's copy of the client. runtime/webview-webkit-arm64 is the client module with
# the arm64 WebKit bridge (engine/webview-webkit-arm64, tools/build_webview.py). libswnfd has no arm64 build and the
# client never loads it. Needs runtime/dotnet-arm64 (add_arm64_server).
ARM64_CLIENT_NATIVES = ROOT/'engine/client-arm64'
ARM64_WEBKIT = ROOT/'engine/webview-webkit-arm64/libdmwebkit.dylib'


def add_arm64_client(game):
    res = game/'runtime/client/Space Station 14.app/Contents/Resources'
    libs = sorted(ARM64_CLIENT_NATIVES.glob('*.dylib')) + [lib for lib in sorted(ARM64_NATIVES.glob('*.dylib')) if (res/lib.name).exists()]
    if not (game/'runtime/dotnet-arm64/dotnet').exists() or len(libs) < 7 or not ARM64_WEBKIT.exists():
        print(f'no arm64 game window (wanted runtime/dotnet-arm64, the libraries in {ARM64_CLIENT_NATIVES} and {ARM64_WEBKIT}): it runs through Rosetta')
        return
    own = {lib.name for lib in libs}
    for f in sorted(res.glob('*.dylib')):
        archs = subprocess.run(['/usr/bin/lipo', '-archs', str(f)], capture_output=True, text=True).stdout.split()
        if f.name not in own and f.name != 'libswnfd.dylib' and 'arm64' not in archs:
            raise SystemExit(f'{f.name}: the client has no arm64 build of it; add one to {ARM64_CLIENT_NATIVES} before building')
    for name in own - {f.name for f in res.glob('*.dylib')}:
        raise SystemExit(f'{name}: not in the client; check {ARM64_CLIENT_NATIVES} before building')
    arm = game/'runtime/client-arm64'; arm.mkdir()
    for lib in libs: shutil.copy2(lib, arm/lib.name)
    shutil.copy2(res/'Robust.Client.dll', arm/'Robust.Client.dll')
    mark_arm64(arm/'Robust.Client.dll')
    web = game/'runtime/webview-webkit-arm64'; web.mkdir()
    shutil.copy2(game/'runtime/webview-webkit/Robust.Client.WebView.dll', web/'Robust.Client.WebView.dll')
    shutil.copy2(ARM64_WEBKIT, web/'libdmwebkit.dylib')


def compile_game():
    # The labeled controls consume exact original pixels through the atlas.
    # Export before compilation so its catalog and thumbnails are packaged.
    subprocess.run([sys.executable, str(ROOT/'tools/export_sprite_assets.py')], check=True)
    subprocess.run([sys.executable, str(ROOT/'tools/export_border_icons.py')], check=True)
    log = ROOT/'compile.log'
    with log.open('w') as out:
        subprocess.run([str(RUNTIME/'dotnet/dotnet'), str(RUNTIME/'compiler/DMCompiler.dll'), str(ROOT/'game/Cave Crawlers.dme')],
                       env={'DOTNET_ReadyToRun': '0', 'PATH': '/usr/bin:/bin'}, stdout=out, stderr=subprocess.STDOUT, check=True)


# The build number the launcher's footer shows (owner 10-28): tools/release.sh N passes BOTD_BUILD=N; a build made
# outside a release says dev.
BUILD = os.environ.get('BOTD_BUILD', '').strip() or 'dev'


def build_app(app, shareable, import_classic_saves=False):
    contents = app/'Contents'; resources = contents/'Resources'; binary = contents/'MacOS/BannersOfTheDeep'
    binary.parent.mkdir(parents=True, exist_ok=True); resources.mkdir(parents=True, exist_ok=True)
    with (ROOT/'launcher-build.log').open('w') as log:
        subprocess.run(['/usr/bin/clang', '-arch', 'arm64', '-arch', 'x86_64', '-fobjc-arc', '-mmacosx-version-min=11.0', '-I', str(REPLICA/'mac-app'),
                        '-framework', 'Cocoa', str(ROOT/'mac-app/Launcher.m'), '-o', str(binary)],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    (contents/'Info.plist').write_bytes(plistlib.dumps(dict(
        CFBundleExecutable=binary.name, CFBundleIdentifier='local.dungeonmaster.remastered', CFBundleName=DISPLAY,
        CFBundleDisplayName=DISPLAY, CFBundleIconFile='AppIcon', CFBundlePackageType='APPL', CFBundleShortVersionString=BUILD, CFBundleVersion=BUILD,
        LSMinimumSystemVersion='15.0', NSHighResolutionCapable=True, NSPrincipalClass='NSApplication')))
    shutil.copy2(ROOT/'mac-app/launch.zsh', resources/'launch.zsh'); (resources/'launch.zsh').chmod(0o755)
    shutil.copy2(ROOT/'mac-app/launcher-art.png', resources/'launcher-art.png')
    shutil.copy2(ROOT/'art/hud/src/assets/screens-races.png', resources/'world-races.png')   # the world list's race pictures (Launcher.m DMRacePicture)
    shutil.copy2(ROOT/'art/brand/AppIcon.icns', resources/'AppIcon.icns')       # tools/make_client_brand.py
    shutil.copy2(REPLICA/'mac-app/local_save.zsh', resources/'local_save.zsh')
    for script in ('launch.zsh', 'local_save.zsh'):
        subprocess.run(['/bin/zsh', '-n', str(resources/script)], check=True)
    game = resources/'game'
    if game.exists(): shutil.rmtree(game)
    game.mkdir()
    def ignored(directory, names):
        return [n for n in names if n.endswith(('.upstream', '.log', '.pending')) or '.pre-' in n or n in ('.DS_Store', 'logs', 'user_data') or n.startswith('strings-')]
    for name in ('dotnet', 'server', 'client'):
        shutil.copytree(RUNTIME/name, game/'runtime'/name, ignore=ignored)
    # Remastered's own engine: the Classic fixes plus the game clock (pause and speed; tools/build_runtime.py).
    shutil.copy2(ROOT/'engine/server/OpenDreamRuntime.dll', game/'runtime/server/Resources/Assemblies/OpenDreamRuntime.dll')
    # Remastered's own title screen, window icons and window title (tools/make_client_brand.py).
    shutil.copy2(ROOT/'engine/client/Content.Client.zip', game/'runtime/server/Content.Client.zip')
    # Remastered's own client module (drag box etc.; tools/build_webview.py).
    shutil.copytree(ROOT/'engine/webview-webkit', game/'runtime/webview-webkit', ignore=ignored)
    add_arm64_server(game)   # after the server's engine and client zip: server-arm64 links to them
    add_arm64_client(game)   # after the client module and the arm64 runtime
    def ignore_world(directory, names):
        # a world's own files (the world list, 10-31: world-info.json, botd-world.json, .build-id) never ship either
        return [n for n in names if n in ('units', 'players', 'ErrorLog.txt', '.DS_Store', 'world-info.json', 'botd-world.json', '.build-id') or n in UNSHIPPED or
                n.endswith(('.dm', '.dme', '.dmm', '.dmb', '.sav', '.log')) or (n.endswith('.json') and n not in ('Cave Crawlers.json', 'border-controls.json') and not directory.endswith(('models', 'gear3d')))]   # gear3d: the 3D gear page's data (Gear3D.dm)
    shutil.copytree(ROOT/'game', game/'world', ignore=ignore_world)
    initial = game/'initial-saves'; initial.mkdir()
    if import_classic_saves and not shareable and (CLASSIC_SAVES/'units').exists():
        shutil.copytree(CLASSIC_SAVES/'units', initial/'units')   # a copy; Classic saves stay where they are
    # Personal and shared apps must open the same existing Remastered account.
    # The old personal-only Kiwi override selected an empty legacy roster.
    (game/'player-name').write_text('@login\n')
    write_hints(ROOT/'game/skin.dmf', game/'skin-layout-hints.json')
    licenses = resources/'licenses'; licenses.mkdir()
    for source, name in [(REPLICA/'source/LICENSE', 'Dungeon-Master-GPL-2.0.txt'), (REPLICA/'engine/LICENSE-OpenDream.txt', 'OpenDream-MIT.txt'),
                         (REPLICA/'engine/RobustToolbox-LICENSE-MIT.TXT', 'RobustToolbox-MIT.txt'), (REPLICA/'engine/RobustToolbox-LICENSE-ASSETS.TXT', 'RobustToolbox-assets.txt'),
                         (REPLICA/'engine/RobustToolbox-LICENSE-GPLv3.TXT', 'RobustToolbox-GPLv3.txt'), (RUNTIME/'dotnet/LICENSE.txt', 'dotnet-MIT.txt'),
                         (RUNTIME/'dotnet/ThirdPartyNotices.txt', 'dotnet-third-party-notices.txt')]:
        shutil.copy2(source, licenses/name)
    marker = (sha(game/'runtime/server/Resources/Assemblies/OpenDreamRuntime.dll') + sha(game/'runtime/server/Content.Client.zip') +
              sha(game/'runtime/client/Space Station 14.app/Contents/Resources/Robust.Client.dll') +
              sha(game/'runtime/webview-webkit/Robust.Client.WebView.dll'))
    for f in sorted((game/'runtime/client-arm64').glob('*')) + sorted((game/'runtime/webview-webkit-arm64').glob('*')):
        marker += f.name + sha(f)   # an arm64 window change alone copies the player's client again
    for asset in sorted(p for p in (game/'world').rglob('*') if p.is_file()):
        marker += str(asset.relative_to(game/'world')) + sha(asset)
    (game/'build-id').write_text(hashlib.sha256(marker.encode()).hexdigest() + '\n')


# Files in the original download that are someone else's copyrighted media and
# are not used by the game: never ship them.
UNSHIPPED = ('Futurama Soundtrack.wav',)


def package(app):
    dist = ROOT/'dist'; stage = dist/NAME
    if stage.exists(): shutil.rmtree(stage)
    stage.mkdir(parents=True)
    subprocess.run(['/usr/bin/ditto', str(app), str(stage/app.name)], check=True)
    (stage/'How to open.txt').write_text(HOW_TO_OPEN)
    shutil.copy2(ROOT/'ACTIONS.md', stage/'ACTIONS.md')
    source = stage/'Source'
    shutil.copytree(ROOT/'game', source/'game', ignore=shutil.ignore_patterns('Cave Crawlers.json', 'ErrorLog.txt', 'units', 'players', '*.log', '.DS_Store', *UNSHIPPED))
    changes = source/'engine-changes'; changes.mkdir()
    for path in sorted((REPLICA/'engine').glob('*')):
        if path.suffix in ('.patch', '.cs') or path.name.startswith(('LICENSE', 'RobustToolbox-LICENSE')): shutil.copy2(path, changes/path.name)
    for path in sorted((REPLICA/'mac-webview').glob('*')):
        if path.suffix in ('.cs', '.swift', '.md'): shutil.copy2(path, changes/('mac-webview-' + path.name))
    # The app ships Remastered's own client module and clock runtime: their sources
    # replace Classic's files of the same name, plus the Remastered-only ones.
    for path in sorted((ROOT/'mac-webview').glob('*')):
        if path.suffix in ('.cs', '.swift', '.md'): shutil.copy2(path, changes/('mac-webview-' + path.name))
    for path in sorted((ROOT/'engine').rglob('*.cs')): shutil.copy2(path, changes/path.name)
    for name in ('Launcher.m', 'launch.zsh', 'LauncherWorlds.h'):
        shutil.copy2(ROOT/'mac-app'/name, changes/('mac-app-' + name))
    for name in ('local_save.zsh', 'LauncherOutcome.h'):
        shutil.copy2(REPLICA/'mac-app'/name, changes/name)
    # The game source ships the original download's Maps/Full/map_backup.sav; player saves never belong here.
    leaks = [str(p) for p in stage.rglob('*.sav') if source/'game' not in p.parents]
    found = subprocess.run(['/usr/bin/grep', '-rIl', '-i', Path.home().name, str(stage)], capture_output=True, text=True).stdout.split()
    if leaks or found: raise SystemExit('Personal data in share folder: ' + repr((leaks + found)[:10]))
    archive = dist/'Banners-of-the-Deep-mac.zip'; archive.unlink(missing_ok=True)
    subprocess.run(['/usr/bin/ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(stage), str(archive)], check=True)
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shareable', action='store_true', help='build dist/ app without saves and zip it')
    parser.add_argument('--import-classic-saves', action='store_true', help='opt in to bundling a legacy Classic save copy for a new personal profile')
    args = parser.parse_args()
    if args.shareable and args.import_classic_saves:
        parser.error('--import-classic-saves cannot be used with --shareable')
    # The HUD page is built from art/hud/src (art/hud/hud.py, like gear3d.js from art/gear3d): package only a page
    # that is their join, so an edit in one place never ships without the other.
    hud = ROOT/'art/hud/hud.py'
    if hud.exists() and subprocess.run([sys.executable, str(hud), 'status']).returncode:
        raise SystemExit('build refused: game/Interface/remastered.html is not the join of art/hud/src '
                         '(python3 art/hud/hud.py status says which changed: build, or adopt)')
    compile_game()
    app = (ROOT/'dist'/f'{NAME}.app') if args.shareable else (ROOT/f'{NAME}.app')
    # Built under a name that isn't a .app, then renamed into place: macOS App Management refuses writes inside an app
    # bundle from a process without that permission (builds 70-72 failed half-way, 2026-10-27), but a whole bundle may
    # still be renamed. The old app is renamed out of .app first, so removing it is allowed too.
    stage = app.parent/(app.name + '.building')
    if stage.exists(): shutil.rmtree(stage)
    build_app(stage, args.shareable, args.import_classic_saves)
    if app.exists():
        old = app.parent/(app.name + '.old')
        if old.exists(): shutil.rmtree(old)
        app.rename(old)
        stage.rename(app)
        shutil.rmtree(old)
    else:
        stage.rename(app)
    # each file once: server-arm64's links to runtime/server's files are not counted again (they were: 444 MB for 385, 10-31)
    result = dict(app=str(app), shareable=args.shareable, bytes=sum(p.stat().st_size for p in app.rglob('*') if p.is_file() and not p.is_symlink()),
                  compiled_game_sha256=sha(app/'Contents/Resources/game/world/Cave Crawlers.json'))
    if args.shareable:
        archive = package(app)
        result.update(archive=str(archive), archive_bytes=archive.stat().st_size)
    (ROOT/('share-package.json' if args.shareable else 'app-package.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
