# One-for-one completion checklist

Updated: 2026-10-16. Status: **incomplete; exact replica not verified**.

Target: reproduce the frozen Dungeon Master game, its maps, assets, interface,
controls and behavior in a standalone runtime that does not require BYOND to
play. BYOND may be used as an isolated comparison tool during development.
Combining Lands of Legend features is separate work: adding them must not change
the reference behavior used to certify this replica.

## How to check an item off

An unchecked item is unverified, not necessarily broken. Check it only after
comparing against the original and retaining evidence in `reports/`. Each new
report must identify the source/runtime builds, scenario, expected and actual
results, and any exclusions. A fix alone does not close an item. Reopen items
when later changes invalidate their evidence.

For visual checks, capture equivalent game states at the same viewport, scale
and animation frame; retain both images and a difference image. Include native
browser panels as well as the game framebuffer. A pixel difference remains open
until fixed or explicitly accepted as a departure from exact matching.

For timing checks, record reference ticks and wall-clock measurements separately.
For random behavior, compare rules and distributions using repeated runs; also
investigate sequence equivalence. Distribution agreement alone does not prove
identical random sequences. Record tolerances before evaluating results, and
label any accepted approximation as such.

Do not turn checkbox counts or passing observations into a fidelity
percentage. Passing this checklist establishes the tested scope; it is not a
mathematical proof of every possible game state.

## Already verified — bounded checks

These remain narrower than the system-wide acceptance items below.

- [x] B01 — All 309 original and frozen source files retain matching hashes; full-world startup reaches ready with zero reported world errors. Evidence: `reports/foundation-checks.json`.
- [x] B02 — Constructor context and scheduling match the recorded reference fixture. Evidence: `reports/foundation-checks.json`.
- [x] B03 — The original five-fixture baseline matches 69 ordered reference observations; the expanded installed suite now matches 1,336. Evidence: `reports/fidelity-checks.json` and its fixture reports.
- [x] B04 — Thirteen ordinary race setups match starting unit, inventory and equipment observations in the bounded arena. Evidence: `reports/gameplay-parity.json`; substitutions: `reports/gameplay-fixture-scope.json`.
- [x] B05 — A real client uses the race prompt, saves three units and reloads them after server restart with tested health, ownership, equipment, coordinates and icon resources restored. Evidence: `reports/client-gameplay-checks.json`.
- [x] B06 — Original browser routing, images, links, named panels and tested fill/layout behavior pass the complete-skin harness. Evidence: `reports/browser-checks.json`.
- [x] B07 — The connected test reports no invalid macro bindings, including the repaired legacy key names. Evidence: `reports/client-gameplay-checks.json`. Physical input behavior is still open below.

- [x] B08 — Ordinary RNG comparisons pass 316 observations, including 30,000 long-run draws across five seeds. Separate wandering randomness remains open. Evidence: `reports/randomness-parity.json`.
- [x] B09 — Extended systems pass 127 observations covering groups, ownership, limb masks, weapon types, flight and 15 bounded race save/load branches. Evidence: `reports/systems-parity.json`.
- [x] B10 — 698 bounded crafting scenarios match, with explicit exclusions for unavailable race choices, altar spells and an original smelter failure. Evidence: `reports/crafting-parity.json`, `reports/crafting-inventory.json`.
- [x] B11 — Two native clients preserve independent armies through an original-code world reboot and reconnect without client/server errors. Evidence: `reports/lifecycle-checks.json`.
- [x] B12 — Repopulation, reboot persistence and text-file behavior match the original fixtures. Evidence: `reports/repopulation-parity.json`, `reports/reboot-parity.json`, `reports/text_io-parity.json`.
- [x] B13 — Inventory ordering, recursive container deletion, deleted aliases, output recipients, icon quarter-turns and implicit self-call arguments match their minimal fixtures. Evidence: the corresponding reports listed in `PARITY.md`.
- [x] B14 — All four compiled map geometries, 4,000,000 cells and 1,396 object placements match the original DMM data; the runtime layout fixture also passes. Evidence: `reports/map-geometry-checks.json`, `reports/map_layout-parity.json`.
- [ ] B15 — Reopened: the earlier 1,200-tick run passed (`reports/world-short-checks.json`), but the current build’s fresh run reports four deleted-target LimbFling errors (`reports/world-soak-checks.json`). The original also produces this error family. A current error-free soak is not established.

## 1. Reference coverage and runtime semantics

- [x] R01 — Inventory every included DM source module, map, asset, skin control, macro and player/admin verb; map each to a comparison scenario so omissions are visible. Evidence: `COVERAGE.md`, `reports/coverage-inventory.json`; 47 included DM modules, 836 procedures, 177 verbs, 67 skin controls and 34 bindings. Scenarios are plans until evidence is linked.
- [ ] R02 — Record reproducible original sessions for startup, race selection, ordinary play, combat, crafting, world events and reconnect, with exact version, configuration and display settings.
- [ ] R03 — Audit all remaining compiler warnings and unsupported built-ins; classify each by reachable game behavior and resolve every behavior-affecting difference.
- [ ] R04 — Compare remaining ambiguous inline conditionals and `else` bindings; retain minimal original/staged fixtures for every adaptation.
- [ ] R05 — Extend semantic comparisons to game-used list ordering, inheritance, callbacks, deletion, delayed actions and resource operations; match ordering and returned values.
- [ ] R06 — Compare random selection rules, ranges, weighting and sequences used by the game; document and resolve any engine RNG mismatch affecting exact reproduction.

## 2. Exact visuals and interface

- [ ] V01 — Match every original map's dimensions, z-levels, initial turfs, objects and placements using a map/state comparison, not source hashes alone.
- [x] V02 — Compare all used DMI states, directions, frame delays, loops and transparency; resolve missing states or conversion differences. Evidence: `reports/icon-assets-checks.json`; all 163 DMI assets compare against original-engine exports, including 53 legacy conversions. Client rendering/animation timing remains V03–V05.
- [ ] V03 — Match terrain and unit rendering: layers, planes, offsets, facing, lighting/visibility and selection indicators across representative map states.
- [ ] V04 — Match equipment, hair, anatomy and other overlays before and after movement, damage, transformation and save/reload; specifically investigate the observed reload appearance discrepancy.
- [ ] V05 — Match fonts, text metrics, colors, spacing, scroll behavior and placement of the original skin, dialogs and HTML panels at recorded window sizes.
- [ ] V06 — Match resizing, split panes, popup placement, visibility changes and focus transitions without blank, clipped or misplaced panels.
- [ ] V07 — Compare every game-used sound/music trigger, asset, volume and repetition behavior; record an inventory if the game has no use of a category.

## 3. Controls, movement and selection

- [ ] I01 — Exercise every original macro through physical input, including CENTER, minus, equals, slash, modifiers and key release; match command dispatch and repeat behavior.
- [ ] I02 — Compare movement speed, diagonal movement, held keys, repeat delay, cancellation and input-to-action timing at the original tick rate.
- [ ] I03 — Compare mouse selection, multiselection and command targeting through the actual client, including browser/chat focus and popup dismissal.
- [ ] I04 — Verify numbered control groups: Shift adds, Ctrl replaces, number selects and double press moves the view, matching the original instructions and behavior.
- [ ] I05 — Compare observer camera movement, unit following, view changes and map-edge behavior on the full maps.
- [ ] I06 — Compare walls, doors, occupied tiles, stairs, z-level changes and other game-used transitions, including Enter/Exit/Cross/Bump callbacks and blocked orders.
- [ ] I07 — Match group movement, order replacement, arrival and obstruction behavior with multiple units on the original maps.

## 4. Races, combat and creature simulation

- [ ] G01 — Complete every race branch, including rare races and special forms, using original geographic spawning rules and starting-state comparisons.
- [ ] G02 — Compare melee attacks across relevant weapons, armor, skills, body parts and attacker/target types; match eligibility, damage, cooldowns and effects.
- [ ] G03 — Compare ranged attacks, ammunition, targeting, travel/hit behavior and obstruction wherever used by the original game.
- [ ] G04 — Compare injury, limb loss, bleeding, healing, unconsciousness, death, corpses and restoration through complete event sequences.
- [ ] G05 — Compare food, poison, potions, status effects, resistances and recovery rules present in the source.
- [ ] G06 — Compare experience, skills, leveling, breeding, aging and race-specific transformations where implemented, including saved state.
- [ ] G07 — Match ownership changes, friendly-fire rules, allegiance and selection permissions for all relevant unit states.

## 5. AI and world simulation

- [ ] A01 — Compare each NPC/monster behavior family: idle, target acquisition, pursuit, attack, retreat and loss of target, as implemented.
- [ ] A02 — Compare pathfinding and stuck recovery around real terrain, doors, stairs, occupied routes and unreachable targets.
- [ ] A03 — Compare escorts, traders, settlements, spawning and other special NPC scripts represented in the source inventory.
- [ ] W01 — Compare original world initialization and population counts/constraints across all maps with event loops enabled.
- [ ] W02 — Implement and compare game-used repopulation and reboot behavior, including player/session and save effects.
- [ ] W03 — Compare seasons, timed/random events and their world effects using accelerated deterministic scenarios plus an ordinary-speed run.
- [ ] W04 — Run a full-world soak test spanning the longest relevant event cycle; record duration, event coverage, errors and state drift against the reference.

## 6. Items, crafting and building

- [ ] C01 — Compare pickup, drop, equip, unequip, containers, transfer and item destruction for each relevant item family and invalid action.
- [ ] C02 — Inventory all recipes/workshops and compare required materials, quantities, duration, outputs, failure conditions and ownership restrictions.
- [ ] C03 — Compare gathering, mining, resource consumption and renewal wherever implemented, including full and missing inventories.
- [ ] C04 — Compare building placement, terrain changes, stairs, removal/destruction and construction UI; match costs, collision and resulting map state.
- [ ] C05 — Compare trading, crowning and other special item interactions found in the source inventory, including multiplayer ownership effects.

## 7. Persistence and multiplayer

- [ ] S01 — Extend original SaveUnits/LoadUnits tests to every race and relevant state: nested inventory, equipped items, injuries, skills, ownership and special forms.
- [ ] S02 — Compare every save operation used by the game, including overridden Read/Write and general object entries; resolve remaining graph/export behavior where reachable.
- [ ] S03 — Verify repeated save/reload, disconnect, normal shutdown and restart without duplication, loss or sprite changes; compare missing/corrupt-save handling to the original.
- [ ] S04 — Establish and verify migration of existing BYOND binary saves, including a retained original and field-by-field restored-state comparison. Until implemented, old-save compatibility remains explicitly unsupported.
- [ ] M01 — Connect at least two real clients; compare player identity, spawning, visibility, selection, chat and independent controls.
- [ ] M02 — Compare simultaneous movement, combat, item transfers, construction and contested ownership; check both clients and authoritative server state.
- [ ] M03 — Compare disconnect/reconnect and server restart with multiple players, including army ownership and save isolation.
- [ ] M04 — Compare behavior under latency and dropped connections, including stale orders, duplicate actions and recovery.
- [ ] M05 — Match original admin verbs, permissions, moderation and server controls identified in R01.

## 8. Release acceptance

- [x] F01 — Run the entire fidelity suite together on the final installed build with `Check Fidelity.command`; retain fresh reports and matching runtime/source hashes. Completed on the installed build: 1,336 ordered observations plus asset, map, browser, native-client and full-world startup checks. Evidence: `reports/fidelity-checks.json`, `reports/installed-fidelity-run.log`, `reports/installed-build.json`.
- [ ] F02 — Replay all newly added comparisons on that same build; resolve every failure and unexplained reference difference.
- [x] F03 — The relocated, self-contained Mac app launches, creates three Human units, saves and restarts with matching health, level, body state and equipment. The app bundle was read-only and access to the project/build/SDK paths was denied; tools were not uninstalled from the Mac. Evidence: `reports/mac-app-checks.json`, `reports/mac-app-package.json`. Live-session coordinate changes are recorded separately; this does not close exact immediate reload-position comparisons.
- [ ] F04 — Verify startup, shutdown, reconnect and an extended session without unexplained errors, increasing resource usage or performance differences affecting gameplay; record the machine and duration.
- [ ] F05 — Reconcile R01's inventory against evidence: no untested module, command, asset family or reachable gameplay branch remains silently omitted.
- [ ] F06 — Complete a side-by-side full gameplay walkthrough with the original, including visuals, physical controls, progression, combat, crafting, world events and multiplayer.
- [ ] F07 — Present the final evidence and any remaining differences for user review. Label the result an exact match only within the verified scope; explicitly accepted deviations still remain deviations.

## Working order and next action

Start with R01–R04 to make coverage and runtime blockers explicit. Then establish
V01–V06 and I01–I07 so the visible game and controls can be compared reliably.
Work through combat, AI, world events and crafting with regression checks after
each fix; extend persistence and multiplayer before final release acceptance.

**Next blocking comparisons:** original-client visual/input traces (R02, V03–V06,
I01–I03), remaining compiler semantics (R03), and the separate random-wandering
algorithm (R06/A01). Original source inventory and DMI asset comparisons are done.

### Progress retained without closing broader criteria

- I01/I04/V05 (2026-10-16): the real Mac client now passes `tools/check_native_ui.py`
  (`reports/native-ui-checks.json`): bounded, wrapped and scrollable alert text,
  multi-button/list/text/number prompts, eight-direction movement with release,
  all 27 Alt/Ctrl+Alt/Shift+Alt group macros and three window sizes. It found and
  fixed a client difference: quoted command arguments kept their quotes, so the
  skin's `Quick 1 "Select"` macros sent `"Select"` and the original Quick() verb
  rejected every control-group key (`engine/client-verb-quoted-args.patch`).
  Synthetic SDL input only; physical-input timing remains open.
- C02 (2026-10-16): `crafting_races` repeats every recipe scenario for Human,
  Elf, Orc, Goblin, Lizardman, Frogman, Kobold and Ratman workers; 5,600
  observations match BYOND, including race-specific menus
  (`reports/crafting_races-parity.json`). `tools/check_client_crafting.py`
  answers the original Carpentry prompts in the real client by clicking rows and
  Ok; the clicked Wooden Door is built with the original quality, wood and skill
  changes (`reports/client-crafting-checks.json`). The workshop DblClick() is
  invoked server-side; injected clicks into a just-opened prompt can use a stale
  pointer and are corrected from the highlight (recorded per click).
- I01/I02/I03 (2026-10-16): physical keyboard route. `tools/check_keys_world.py`
  posts real AppKit key/mouse events into the full game (SDL injection had
  bypassed AppKit focus). Fixed: +REP macros now run on key down (taps were
  dropped inside one 100 ms tick); `client/North() ..()`-style overrides keep the
  built-in verb name, so `.north` exists again; clicking outside a browser panel
  returns the AppKit responder to the game view; the skin's command input lets
  non-text keys reach macros like Dream Seeker (`mac-webview/DreamSeekerKeys.cs`);
  text/number prompts open with the default selected; `sound(null)` on channel 0
  stops all channels; MP3 data in Sounds/P1-P3.wav is staged as PCM WAV and
  `<< 'file.wav'` plays instead of printing. Arrow moves and the Rename prompt
  were confirmed in the full game; events posted while another app is active
  can be dropped by macOS, so counts in that report vary run to run.
- I06/I07 (2026-10-16): engine fix. When an Enter() override refuses without
  `..()` (the game's turf/grounds does), BYOND bumps a non-dense turf's first
  dense content; the replacement bumped the turf, so the original Bump() fell
  through to step_rand() and blocked units circled their destination forever
  (seen by the user as idle units moving/turning). `bump_target` (33 cases) and
  `pickup_crowd` now match BYOND (`tools/prepare_standard.py`).
- I03/C01 (2026-10-16): engine fix. Upstream paired any two clicks within 250 ms
  of server receipt as a double-click, so real double-clicks (item pickup, unit
  selection) were dropped under tick lag. Now: same atom and button within
  500 ms (Windows/Dream Seeker default), third click starts over
  (`tools/build_compat_runtime.py`, `tools/check_dblclick.py`). Item pickup
  through DblClick() matches BYOND in `pickup_crowd`.
- A01/G06 (2026-10-16): `idle` shows fresh Human/Orc armies and a saved/reloaded
  Orc army making no position or facing changes for 15 s with no orders, in both
  engines (`reports/idle-parity.json`). `turf_contents` matches typed tile
  iteration (`in loc`, `locate`, `range(0)`, `view(0)`, `contents`).
- F01 rerun (2026-10-16, client `778b05db…`): all 1,336 ordered observations,
  icons, maps, wandering, two-client reboot, connected save/reload, browser and
  foundation checks pass. The new native-UI step passed once in isolation but
  then failed intermittently (`reports/fidelity-checks.json` records the
  failure). It warps the real pointer and fronts windows, so live mouse activity
  races its injected press/release; rerun it on an idle Mac before re-closing F01.

- R04: structural compact-conditional expansion, the admin-editor ternary rewrite,
  switch defaults, membership precedence, `src` shadowing and parent no-ops have
  additional passing original/staged comparisons.
- R05: ordered inventories, deleted references, text I/O and icon quarter-turns
  have new differential fixtures; not every game-used operation is certified.
- R06: 316 ordinary RNG observations, including 30,000 long-run draws, pass.
  Wandering now has an independent stream, preserved map references and matching
  open-terrain forward-bias distributions over 80,000 draws per engine. Exact
  sequences and 5x5 edge-following remain open (`wandering-checks.json`).
- V01: all four map geometries, 4,000,000 cells and 1,396 object placements match
  compiled output. Full runtime post-constructor population comparison is open.
- I04/G01/G04/S01: 127 extended system observations cover control groups, flight,
  all 15 race branches, limb masks and bounded saves. Physical controls,
  geographic spawning and complete injury/event sequences remain open.
- C02: 14 workshop types and 239 menu choices inventoried; 698 bounded recipe
  scenarios match. Race restrictions, partial ingredient quantities, altar
  spells, original smelter failure, crafting timing and physical UI remain open.
- W02/M03: original repopulation/reboot fixtures and two native clients saving,
  reconnecting and restoring independent armies pass. Full world/session effects
  and original-client multiplayer comparison remain open.
- S03/F03: the native application now saves via the original SaveUnits before
  stopping its local server. A relocated package passes two native-client sessions
  with development access and bundle writes denied. Three Human units preserve
  health, level, body state and equipment. Live coordinate changes remain open.
- W04/F04: both engines completed 11,000+ ticks and reached Winter. The same three
  error families occur in both; populations were independently randomized. See
  `world-long-comparison.json`. Current-build short soak is not error-free.


Maintain this file as work proceeds: check the precise item, link its report and
record any remaining exclusions. Keep the narrower existing results in
`PARITY.md` accurate rather than replacing them with a blanket completion claim.
