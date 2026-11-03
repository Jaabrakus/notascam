# Faithful foundation

This foundation runs the supplied Dungeon Master DM gameplay on a replacement
engine. It preserves the original maps, sprites and procedures as the reference.
The Mac client now connects to the original-code server with native embedded
WebKit browser panels. Complete interface and gameplay parity are still to finish.
The simplified Godot inspection build is separate.

## Run on this Mac

- Double-click **Dungeon Master.app** to start the local world and open the Mac client.
  **Play.command** also opens this app.
  Press **R** to choose a race, use arrow keys to move the observer, double-click
  your units to select them, and click terrain to issue movement orders. Space
  clears selection. Original HTML browser panels and game links are enabled.
  The original save procedures now have native object-graph support. See
  `PARITY.md` and the connected-client save/reload report for the verified scope.
  The app imports a copy of existing standalone saves on first launch and saves
  units before closing its local server. Player data lives in
  `~/Library/Application Support/Dungeon Master Standalone/world`.
  Existing BYOND binary saves are not supported.
- Double-click **Check Foundation.command** to verify original file hashes,
  compare constructor/scheduling observations and start/stop the original world.
- Double-click **Start Server.command** to leave the replacement server running
  on localhost port 12121. Stop it with Control-C. This opens no game window.
- To rebuild the staged game: `python3 tools/local_runtime.py compile`.

The app bundles everything needed to play; Python and development SDKs are only
used by the development/check commands. The retained `runtime/macos-x64/` contains the tested .NET runtime, OpenDream
compiler/server and Mac native dependencies. It uses this Mac's existing x64
compatibility support. It does not require a BYOND installation, Docker or files
in `/private/tmp` for these commands. Docker and the isolated BYOND reference are
only needed when refreshing the original-engine comparison with
`python3 tools/local_runtime.py check --reference`.

## Share with others

`python3 tools/package_share.py` builds `dist/Dungeon Master.app` with
`build_mac_app.py --shareable` (no personal saves; each player is named after
their Mac account) and zips it as `dist/Dungeon-Master-mac.zip` with
`How to open.txt`, the GPL-2.0 game source (original and adapted) and the
engine changes. The app is unsigned, so recipients clear quarantine once as the
instructions describe. `tools/check_mac_app.py --shared --app <path>` runs the
relocated save/reload check against a shareable build. Results:
`reports/share-package.json`, `reports/mac-app-share-checks.json`.

## Engine fixes

The isolated BYOND 516.1655 fixture established two differences:

1. A mob's `New()` runs with `usr == src`, including mapped mobs, dynamic
   creation and creation by a different mob. Ordinary object constructors retain
   the caller's `usr`. The compatibility runtime sets the constructor context for
   mobs without changing the game's `usr` references.
2. The fixture's equal-tick delayed tasks resume in registration order in BYOND.
   OpenDream's priority queue reordered them. The compatibility runtime adds an
   insertion counter to priorities so equal-tick delays retain FIFO order.

The fixture also observes context after a parent constructor call, inside delayed
code, and in the caller after construction. The check compares all output lines
in order. These are specific measured behaviors, not proof of complete engine
equivalence. See `reports/foundation-checks.json` and the paired context logs.

A third engine fix routes unnamed `browse()` output to the skin's existing
default browser. The Mac WebKit module renders its original HTML, images and
links inside the game windows. See `mac-webview/README.md` and
`reports/mac-browser-status.json` for the implementation and integration checks.

`source/` and the original project files remain unchanged and are checked against
all 309 frozen SHA-256 entries. Syntax, legacy icons and macro adaptations are
staged separately by `tools/prepare_opendream.py`.

## Rebuild the engine fixes

`tools/build_compat_runtime.py --help` lists the required local inputs: the
matching OpenDream source/server release, its RobustToolbox source, a .NET 10 SDK,
and the JetBrains annotations assembly. The script builds the matching Robust
serializer generator, applies the checked runtime patches in a separate build folder,
and compiles against the published server assemblies. `--install` keeps an
upstream assembly backup before installing the result. No upstream checkout is
edited. The patch files are in `engine/`; build logs and hashes are in `reports/`.

The tested OpenDream release was published October 13, 2026. Its RobustToolbox
submodule is `af2a7d0406b410c4d960f0f4b34513651c6dc742`. Dependencies used for this
build: .NET SDK 10.0.402, runtime 10.0.13, JetBrains.Annotations 2026.2.0.

## Remaining acceptance work

The measured gameplay and persistence comparisons are documented in `PARITY.md`.
The four previously unsupported legacy key names are registered by the Mac module.
Remaining milestones include exact visual/input behavior, full combat and AI,
complete crafting/building coverage and world simulation. Repopulation and supervised reboot now pass bounded checks, including two native clients reconnecting. The full
acceptance matrix is in `REPLICA.md`. A server reaching Ready with no initialization
errors does not establish that those systems behave exactly like BYOND.

The 32-bit BYOND reference runs inside an isolated, network-disabled ARM Docker
container using QEMU. The harness records its completion marker and then stops
the container; its emulated shutdown is unreliable. The replacement runtime does
not load the proprietary reference engine. `native-mac/libbyond.dylib` is the
open-source OpenDream API bridge, despite its library name.

## Native application package

`tools/build_mac_app.py` builds `Dungeon Master.app` with a native universal Mac
launcher. Its game engine is bundled x64 and uses Rosetta 2 on Apple Silicon.
The package targets macOS 15+ and has been tested on this Mac (26.3.1), not every
supported OS version. The .NET platform requirements are documented by
[Microsoft](https://github.com/dotnet/core/blob/main/release-notes/10.0/supported-os.md).

`tools/check_mac_app.py` copies the app to a temporary location, denies reads of
the project and development tools, denies writes to the app bundle, then runs a
Human race session and a separate reload. The resulting character fields and
limitations are in `reports/mac-app-checks.json`. Native app saves use the original
SaveUnits procedure through an opt-in local host request. Existing binary BYOND
save files remain unsupported. This personal package includes a copy of your
existing standalone saves for first-launch import; your originals are preserved.
