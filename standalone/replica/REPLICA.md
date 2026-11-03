The current playable package is **Dungeon Master.app** in this directory. It
bundles its runtime and game assets; playing does not require BYOND or Godot.
Use `FOUNDATION.md` for launch/save instructions and `PARITY.md` for current
comparison evidence. Exact replication remains incomplete.

# Dungeon Master replica target

The requirement is an exact replica of the supplied Dungeon Master game, with the BYOND dependency replaced. Existing control schemes, map geometry, interface layouts, races, items, balancing, timing, AI, crafting, construction, world simulation, and persistence are the reference. New game design and merging Lands of Legend into these rules are outside this fidelity target.

## Current status

No exact replica is complete or verified. The earlier First Settlement prototype is a different game. The Godot source-based map/interface reproduction in `../frontier/` is a useful inspection build, but its simplified unit movement and incomplete simulation do not satisfy this requirement.

The original-code foundation is here. See `FOUNDATION.md` for local launch and verification commands:

Measured gameplay, movement and save fixes are now documented in `PARITY.md`.
Its current reports supersede the initial audit findings below; passing a bounded
comparison still does not certify full-game equivalence.

- `source/`: a byte-for-byte baseline of all 309 supplied game files, with hashes in `reports/source-baseline.json`.
- `opendream/`: a separate staged copy for running the original DM procedures through OpenDream.
- `tools/prepare_opendream.py`: reproducible adaptation of older inline switch cases, inline type property declarations, and one ambiguous nested conditional expression. It checks the frozen source before staging changes.
- `reports/opendream-syntax-adaptations.json`: the staged source changes, including structural conditional-binding fixes for equipment, collision, flight and NPC branches. No gameplay procedure was replaced with the prototype implementation. The bounded gameplay suite compares the frozen original against this adapted source.
- `reports/opendream-compile.log`: original source compilation result: 612 errors and 290 warnings.
- `reports/opendream-adapted-compile.log`: staged source compilation result: **success, zero errors** (current warning categories are in `reports/compiler-warning-audit.json`). `opendream/Cave Crawlers.json` is the compiler output.
- `reports/opendream-server.log`: the earlier startup reached Ready with 267 constructor errors. The compatibility runtime fixes the measured mob constructor context difference; `reports/opendream-server-foundation.log` records the fresh startup with zero initialization errors. A ready server is not a successful gameplay-equivalence test.
- `engine/`: a compiled compatibility runtime, upstream license and two small engine patches for mob constructor `usr` and FIFO ordering of equal-tick delays. The game procedures were not edited for these fixes.
- `reports/foundation-checks.json`: original/frozen hashes, 19 ordered observations compared against BYOND, and full-world initialization checks.
- `runtime/macos-x64/`: retained runtime and dependencies for the local launch/check commands; no temporary-directory dependency.
- `reports/opendream-resource-adaptations.json`: the 53 original legacy DMI files converted in the staged copy to PNG-backed DMI using their decoded pixels and animation data. Original files and hashes remain in `source/`.
- `reports/opendream-macro-adaptations.json`: the 34 original legacy macro command strings transferred into the staged `skin.dmf` macro group. The unsupported DMS file remains present for review of its styles.
- `native-mac/libbyond.dylib`: a Mac x64 build of the unmodified [OpenDream native API bridge](https://github.com/OpenDreamProject/OpenDreamByondApi), used for the startup check. This is OpenDream compatibility code, not the BYOND engine.

OpenDream is a candidate runtime, not a guarantee of BYOND compatibility. Its own documentation calls out incomplete features and primarily supports Windows and Linux. See the [OpenDream repository](https://github.com/OpenDreamProject/OpenDream).

## Fidelity checks required before calling this a replica

| Area | Reference | Acceptance |
| --- | --- | --- |
| Original maps | Four DME-included DMM files | All coordinates, atoms, per-instance overrides, level ordering, collision, overlays and travel links match |
| Observer movement | `Player.dm`, `Code/Login.dm`, turf `Enter()` | Invisible nondense observer; eight directions; original boundaries, repeat timing and camera behavior |
| Selection and orders | `Code/Mobs.dm`, `Code/Click.dm`, `Code/Selection.dm`, `BackGrounds.dms` | Double-click selection, Space deselection, click destinations, A/E/P/Z, control groups and autodig match |
| UI | `skin.dmf`, `Code/Login.dm`, `Code/Verbs.dm`, `Code/Building/HUD Building.dm` | Same pane layout, icon states, screen coordinates, text glyphs, menus, prompts and command bindings |
| New game and races | `Code/Restart.dm`, race definitions and constructors | Same choices, spawn restrictions, counts, formation, equipment, gender/stat initialization and special abilities |
| Units and AI | `Mob Procs.dm`, `Monster AI.dm`, `Bump.dm` | Original delays, collision responses, guarding, target choice, wandering, movement, doors, digging and climbing |
| Combat and anatomy | Combat, health, damage, death and overlay modules | Same formulas, RNG probabilities, cooldowns, limbs, equipment, injuries, death and transformations |
| Economy and building | Crafting stations, item making, equipment and construction modules | Same inputs, qualities, skill gain, inventories, workshops, structures and placement rules |
| World simulation | `Code/World.dm`, events, breeding and aging | Same repopulation, seasons, day/night, ages, hunger, fatigue, reproduction and event scheduling |
| Persistence | `Code/Saves.dm` and original save APIs | Original serialized fields and reconstruction behavior; preserve existing save semantics or explicitly resolve incompatibility |
| Multiplayer | Login, ownership, chat, identity and administration | Equivalent authority, unit ownership, player interactions and local/server lifecycle without a BYOND installation |
| Engine behavior | Original BYOND runtime | Differential checks of scheduling, `usr`/`src`, movement, rendering, resource paths, defaults, macros, browser UI and saves |

## Known compatibility findings

The successful compiler run reports:

- Legacy DMS files are unsupported. `BackGrounds.dms` command bindings have been carried over into the skin; its browser styling still needs compatibility review.
- `world.Repop()` and supervised `world.Reboot()` now have bounded original-engine comparisons; the two-client reboot harness also verifies independent army restoration. Full seasonal population equivalence remains open.
- Additional warnings cover parent-procedure calls, `in` precedence, and ambiguous switch cases. Warnings require review against original semantics rather than suppression.
- The published server is x64. Its managed executable runs under the Mac's existing x64 compatibility support with a temporary .NET 10 runtime. Sodium, Zstd and SQLite Mac libraries were obtained from the matching packages during the audit; the native OpenDream API bridge was built for Mac x64 from its unmodified source.
- The initial startup produced 389 invalid-image errors from legacy DMI resources. After converting the staged icons, a fresh startup reached Ready with **zero invalid-image errors**.
- The earlier runs produced 267 NPC constructor exceptions involving null `usr`. An isolated BYOND reference fixture confirmed that mob constructors should receive `usr == src`. An engine patch restores that context without changing game procedures. A second patch preserves measured FIFO ordering for equal-tick delays. The fixture covers mapped and dynamic mobs, a different caller, parent calls, delayed context and ordinary object constructors. All 19 output observations match in order after both patches. The full-world startup then reaches Ready with zero initialization errors. Broader scheduling and gameplay equivalence remain unverified.
- The Mac x64 client now connects, enters InGame and attaches to the original Player mob. Its engine version follows the official manifest redirect from 288.1.0 to 288.1.2. A native WebKit module now renders browser panels inside the Mac game windows. Default browser output, game images, relative and byond:// game links, named panels and closing passed integration checks. The original introduction and guide also loaded in the full game. See `reports/mac-browser-status.json`. The four legacy key names now register without warnings. See `reports/play-session.json`. UI and gameplay parity remain open.

Runtime downloads and dependency builds for this experiment are isolated under `/private/tmp/dm-runtime-audit`; a copy of the successfully built native bridge is retained here. The system .NET and Rust installations were not replaced. The compiler and server packages are from the official OpenDream `latest` release published October 13, 2026. Runtime archives were checked against the official .NET SHA-512 values. The Rust x64 standard-library archive was checked against its official SHA-256 value and used in a temporary sysroot. Temporary localhost-only test servers were stopped after recording their results. The tested compiler/server, Mac native dependencies and x64 .NET runtime are now retained in `runtime/macos-x64/`. The optional BYOND test oracle is isolated under `reference/` and is not required by the replacement server.

## Repeat the compile check

With a .NET 10 runtime and the official OpenDream compiler available:

```sh
python3 tools/prepare_opendream.py --dotnet /path/to/dotnet --compiler /path/to/DMCompiler.dll
```

This operates only on the staged copy. The original project folders and the frozen source baseline remain unchanged.
