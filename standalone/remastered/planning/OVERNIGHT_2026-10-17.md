# Remastered overnight work — October 17, 2026

User asked the lead developer and existing agents to continue autonomously until morning. Working target: **7:00 a.m. Eastern**. This file records actual progress, not a promise of unattended execution if the active session stops. No scheduled wakeup tool is exposed in this session.

## Boundaries

- Canonical game: `standalone/remastered/game`; canonical app: `standalone/remastered/Dungeon Master Remastered.app`.
- Classic gameplay, archived `dist`, and the Godot experiment stay unchanged. Engine/platform fixes belong to shared infrastructure.
- No injected input in the normal game. Tests use isolated worlds/profiles and actual game unit types.
- Normal game was closed at the start. Its current save has zero units; preserve it and the earlier three-Orc recovery copies. Do not silently restore or replace the user's world.
- Initial restore point: `restore-points/overnight-start-20261017-0116/`. Contains current source, hashes, copied player saves, and launcher sources.

## Current work

The **cumulative twelfth app is accepted**, compiled game `93f76efd`, after private Frogman startup/save/reload passed at 05:23 Eastern. All 56 exact combined suites pass 9,550 assertions with clean server exits and stable source/runtime. The complete 756-file app/source checkpoint was preserved at 05:25; tenth is also retained. Private eleventh 54/8,658 passed without a separate package. All 372 canonical source/resource files match the frozen original-game snapshot in the pending 60-minute world run. Unchanged HTML/HUD reuse 253 responsive and 144 projection checks. The frozen final 13-race matrix is running serially.

| Owner | Work | Evidence / status |
| --- | --- | --- |
| Lead | Integration, save safety and HUD | Twelfth 56-suite source and native Frogman lifecycle accepted; full backup retained. Fourth failed on old covered combat defect; sixth and frozen-final world checks running. |
| Combat stability | Workshop handoff | Forge/Poison/Gem/Potion installed. Bone1391+183 native and Leather892+145 native installed in twelfth. |
| Easy orders HUD | Selection, inventory and defense | Carried prompt and selection guards installed. Elemental/Holy/Poison/fire/Vampire notifications installed; Werewolf385 installed in twelfth. Remaining defense families documented. |
| Sprite pipeline | Original sprites and engine | Mixed-contents ordering installed; frozen final 13-race matrix running. Full-world observer compile-only rehearsal passed and the final 60-minute world is running. |

## Acceptance checklist

- [x] Restore point and current-save copy recorded before changes.
- [x] Reuse the existing three agents with explicit file ownership.
- [x] Reproduce stale save acknowledgment failure without touching a player save.
- [x] Verify fresh, stale, mismatched, empty, missing and failed acknowledgment handling with the actual shared helper.
- [x] Verify the helper through a real packaged save/reload lifecycle.
- [x] Verify committed manual Interact/autodig/guard actions suspend competing controllers and retain queues.
- [x] Verify opening/cancelling the tested Interact/Guard menus and deselecting leave independent work intact.
- [x] Verify stable HUD controls during live task/inventory changes at phone-sized widths.
- [x] Reproduce and resolve or precisely document remaining DMI variant loss.
- [x] Review original contextual build/magic palette routes before adding larger controls.
- [x] Add larger original-menu choices; verify real racial menus, native fallback, selection checks and stale-menu rejection.
- [x] Replace recycled raw references in modern unit/item/task requests with lifetime tokens, and verify stale requests cannot affect replacement objects.
- [x] Verify original potion/sign/tombstone choices, stale prompts and unchanged eligible effects through the shared inventory route.
- [x] Verify commit-only handoff for Carpentry and wood/stone floor/wall/bridge placement, including rejected gates and changed Carpentry actor profiles.
- [x] Verify and package the touch magic-target chooser, including native WebKit rendering and unchanged work.
- [x] Complete initial full-world simulation and review its log; distinguish its source/runtime snapshot from the final build. It completed its target but failed the clean-run requirement; see the seven terrain errors below.
- [x] Run focused integration checks on final source/runtime hashes: twelfth 56/9,550 with all server exits clean.
- [x] Rebuild the first canonical Remastered app from passing code; repeat after subsequent accepted increments.
- [ ] Record delivered changes, evidence, limitations and playable app path for morning.

## Verified so far

- `tests/save-ack-before.json`: original launcher reports `saved` despite different request/acknowledgment tokens.
- `../replica/reports/local-save-checks.json`: eight shared helper cases pass; shell syntax checked for both launchers. These are protocol tests, not an actual game save/reload test.
- `tests/manual-handoff-checks.json`: 35 checks pass; `easy-orders-manual-handoff-checks.json`: 72; `defense-manual-handoff-checks.json`: 103. Actual game controllers/units, isolated worlds. Legacy menu choices are supplied at the input boundary; native prompt UI is not certified by this fixture.
- `tests/hud-palette-controls-checks.json`: 134 browser checks pass at HTML `e865ce9c495536c054bf3c425027cffe25b3a8e8fcb00e7a73ba960171ec03fa`. Final image-only change has five focused checks in `tests/hud-portrait-checks.json`, HTML `ea1ca00dbb4bf70c600227752449ca2067a95fe50de40a5823031d6254a2e986`.
- `tests/palette-native-checks.json`: 27 assertions/fixture checks pass, no native input or world save created. Real original constructors and menu callbacks; no browser-pixel certification from the map framebuffer.
- `tests/ui-reference-audit-checks.json`: 20 identity checks pass after migration; failing baselines retained under `ui-reference-before-*`. Final core regressions use the `ui-identity` labels. Palette IDs now use the same temporary lifetime-token mechanism.
- Final native palette run verifies restoration through the production `HUDTick()` readiness path, not just direct palette-data generation: 27 checks, final HTML, stable source/runtime hashes, no client/server/world errors.
- Save failure notification on Cmd-Q now has a shared native outcome helper. Final 24-check report covers actual shell cleanup, success/failure outcomes and repeated Quit waiting for completion. The first packaged save/reload lifecycle now passes; see the preserved overnight-first-app report below.
- `tests/portraits-before-checks.json` reproduces five animation strips instead of single-frame portraits. `portraits-staged-checks.json` passes six real constructor/source-pixel comparisons plus completion/stability checks. Full composed hair/equipment portraits remain a separate task.
- `tests/bow-controller-before-corrected-checks.json` preserves five bow timing/state failures. `bow-controller-fixed-checks.json` passes 17 checks; `defense-bow-controller-checks.json` passes 103 checks with stable hashes and zero errors.
- Full previous app copied into the initial restore point before replacement. Normal game remains closed, and normal player-save hashes are checked by the updated packaged lifecycle harness.
- First integration build completed at about 01:39 Eastern with 288 existing compiler warnings and zero errors; packaged lifecycle test passed at about 01:43 Eastern. Installed-runtime checks passed: 72 Easy Orders, 20 identity, 30 game-side facing, eight portrait, and 36 native palette/capture assertions. Its HTML is the mental-abilities revision; later compact HUD/construction/inventory work is not in this first app yet.
- Real WebKit snapshots (not the engine's incomplete framebuffer) captured the original Human build/wall and Illithid menus with their original icons. They exposed the excessive short-screen header. `hud-compact-before-checks.json` preserves two failures; compact follow-up passes the full 162 browser checks, zero errors, stable final HTML.
- Scoped Carpentry/wood construction handoff pass: 41 assertions, zero errors; opening/cancelling keeps work and real craft/placement commits pause controllers. Other material branches are being migrated separately; see `BUILD_HANDOFF.md`.
- Special inventory before test reproduces potion/sign/tombstone buttons dropping those items instead of opening their original Click choices. Shared original-handler extraction now passes 42 identity/effect assertions, including the unchanged original LongLife effect and stale prompt rejection. Native dialog pointer input is not certified by that fixture.
- Initial world simulation uses 36,000 ticks, private copied server runtime, and original full maps. Source snapshot: `tests/overnight-world-initial-source.json`. In progress; no successful long-run result yet.

## Remaining limits carried into this work

The project is not certified as a 100% faithful replica. Responsive HUD checks are not a mobile export or physical touch test. Queued target references are currently session-only. Broad original crafting, world-event and context-menu parity still needs measured comparison. Existing test counts describe their specific checked cases, not overall completion percentages.

## First packaged integration evidence

`tests/overnight-first-app-checks.json` preserves the real first-app lifecycle: new Human army and reload both contain three units, both exit successfully with fresh save acknowledgments, host flush acknowledgment, no remaining instance lock, and zero client/server/world errors. The normal Kiwi save stayed unchanged (`368992a781598c7703b64091935e081666dd9052808ee4d881ba5fa98d74fac4`). App tests ran only in a private profile.

This app contains the first installed sprite variant/runtime, save reliability, identity, portrait, palette, manual handoff, bow and mental-action work. Its HTML hash is `3f82c1e5f6a722dbac09475e7bb412b24fe2fb182c07f0cdffba682005c41c12`; it predates compact layout, special inventory and the latest construction work. The app is closed after verification. Later source changes must not be described as already packaged.

## Second increment in source (not yet packaged)

- Compact HUD plus magic chooser: `tests/easy-orders-hud-checks.json` now passes **183 browser assertions**, zero errors, HTML `eef7e7df02e0e93e93664fb5163df34e9642e56f81ba57cdc688d1f3b97006ad`. Existing controls keep identity/focus as other command eligibility changes. Target chooser uses a session plus unit lifetime token, keeps Close visible at 320×568/390×625/768×844, and displays plain text. Game-side target validation and native capture are still in progress.
- Construction: `build-profile-fixed-checks.json` passes **50** assertions; `terrain-handoff-fixed-checks.json` passes **142**, both zero errors/stable sources. Lead reviewed the terrain diff: only successful-commit handoffs and removal of premature destination clearing; original material/race/range/sky/support gates and costs remain. Profile checks cover race/subrace/mist changes during all Carpentry prompts.
- A new private full-world input harness is being prepared to resolve the earlier inconclusive movement recording. It will use internal client hit-testing/network input in a separate process, without moving the OS pointer or touching the normal app.

## Integration at 01:57 Eastern

Reviewed rewind source/artifacts and the separately verified full-world diagnostic WebView are now installed in shared engine/runtime infrastructure. Exact writes/hashes are in `../replica/reports/dmi-rewind-install.json`; backup: `restore-points/overnight-second-engine-20261017-0158/` (folder label approximate; manifest records exact time). Runtime `569d6ae37dd4e29219f37d90a8025be9bf6fffdcc34dc4bfdca9b1d3fdaef42c`, client `8276138a5fbca0bb00daf2f105b16cb313b968b7d99cdeb14e0eb22eb5e23bdc`, ZIP `a28170d5085492fbf477897aacd6a4264e965a17200daba58530d82880adb0ca`, WebView `a1e402420655450cebc3ba0c8118c32b997856058a5d5fcfc0d93dadd702b5af`; Shared unchanged. The canonical app still contains the earlier first integration until the next build.

- Rewind: 22 focused, 51 native, 81 variant, 36 movement, 11 generated-icon checks pass. Original BYOND oracle establishes endpoint delays, forward-only flick and continuing global animation phase. All 164 original assets unchanged. See `../replica/engine/DMI_REWIND_PLAN.md` for finite-loop/phase limits.
- Full-world selection: `tests/full-world-selection-verified-checks.json` passes 23 assertions using original startup/three Human army/all maps. Actual client hit-test/network callback selects exactly one unit; its marker appears; one-tile North move leaves others idle; 167 arrived samples hold North/frame0. This bypasses OS event delivery and is not physical touch testing. It used the first installed runtime plus newly staged diagnostic module, before current group cleanup/rewind integration.
- Native Palette/Magic: `palette-magic-verified-checks.json` preserves 43 passing checks, including real WebKit target chooser and actual client.view change invalidation. `palette-actor-deletion-before-checks.json` reproduced a deleted-actor menu bug; Palette now captures every actor by lifetime token and rejects null-slot deletion. Actual short-screen Human portrait/vitals are visible. The same screenshot exposed a ghost selection count, preserved as `selection-ghost-before-webkit.png`.
- Groups/ghost selection: backend passes 42 checks plus original QoL regressions; root touch UI passes 18 focused + 18 compact checks at HTML `6c4acc251bc62a79837a788dc7834c15c44c1c3859aba4a6b1de524fb596382d`. Full browser/native integration pending. Lead review caught original privileged DE+FreeSelect semantics; a narrow preservation fix is under test before release.

### Second installed combination validated

- `easy-orders-hud-checks.json`: **201/201**, stable HTML `6c4acc251bc62a79837a788dc7834c15c44c1c3859aba4a6b1de524fb596382d`, zero browser errors. Group rows use separate Recall/Set/Add; Set/Add elements are replaced when the captured selection changes, preventing a held tap from being retargeted.
- `palette-native-checks.json`: **45/45**, six real WebKit phases including magic targets and groups, zero errors/observed input, all source/runtime hashes stable. Groups drawer opened through the existing output-to-JavaScript bridge for capture; native pointer delivery is not claimed. Final Human screenshot correctly shows one selected unit after deletion cleanup.
- `full-world-selection-integrated-rewind-groups-checks.json`: **23/23**, zero errors/input/threat interruptions and no source drift, on the newly installed rewind runtime/client/diagnostic module plus group cleanup. This repeats the original three-Human map selection/one-unit movement/highlight/facing acceptance on the integrated source.
- Original DE + FreeSelect developer selections are preserved only when both pre-existing flags apply; modern groups remain owned-only. Expanded group fixture passes **48** checks.
- First integrated app copied to `restore-points/overnight-first-integrated-app-20261017-0159/` before replacement. Second app build/save lifecycle remain pending completion of the last regression batch.

### Second app built; lifecycle running (02:02 Eastern)

- Canonical second app built successfully, compiled game `837cf877a4f54c3d94fdd39c42230571465df17bee8c06db36355f6971194fc1`, 193,443,900 bytes. The sprite asset build reconstructed 161 sheets, compared 9,311 cells and preserved original files; border assets passed all 45 control records. No shareable archive was replaced.
- `installed-regressions-20261017.json`: **341 gameplay assertions** pass (72 orders, 42 inventory/identity, 41 magic, 48 groups, 35 manual handoff, 103 defense); source/runtime/compiler hashes stayed fixed throughout.
- Second packaged save/reload lifecycle is running in its private profile. Normal app remains closed.
- A second bounded full-world simulation was started with **108,000 ticks / approximately three hours**, port 12162, copied current runtime `569d6ae…` and copied game source. Snapshot: `tests/overnight-world-second-source.json`; result pending. This runs original map/startup simulation, with no connected player and no player-save access.
- Next private candidates: context object-row click/release plus edge placement, modal actor validation for Rename/speech/royalty, and clearing newly allocated generated-icon pixels. Each has a reproduced before failure; none is in this second app.

### Second packaged lifecycle passed (02:05 Eastern)

`tests/overnight-second-app-checks.json`: both real packaged launches pass, three Human units survive save/reload, fresh distinct acknowledgments, successful host flushes, zero client/server/world errors, no remaining locks. Packaged game/runtime/client/HUD/WebView/launcher/helper hashes match tested source. Normal Kiwi save remains `368992a…`. Second proven app plus source archived under `restore-points/overnight-second-integrated-app-20261017-0205/`. The normal game remains closed.

Root also reproduced a commit-order defect in Unload & resume: empty cargo or cargo excluded by the stockpile filter canceled a defense response and overwrote work status before rejecting the request. `tests/delivery-commit-before-checks.json` retains four failing assertions and seven passing controls; no production change at this point.

### Third increment under review (02:06 Eastern)

- Shared runtime buffer initialization installed after exact builder/source review: `../replica/reports/icon-buffer-install.json`, runtime `783f6ad20cb1f578d57429d2c015587187f6ac59e88e6c8bce609858fff5b6f4`. Only the used pooled RGBA span is cleared; client/Shared unchanged. Second verified app and both ongoing soaks retain their own previous runtime snapshots.
- `tests/delivery-commit-final-checks.json`: **12/12**, real Human/Orc constructors. Empty/filter-excluded Unload & resume leaves defense, destination, FIFO and status intact. Accepted unload cancels the response, deposits real cargo and completes the prior FIFO while deselected. Before report retains four failures. Source fix is in Delivery.dm; app unchanged.
- Context candidate review caught focus-loss cancellation and a cosmetic accumulated hover highlight; those are being handled before shared-client promotion. No long-press implementation or physical touch claim.

### Controls and shared client update (02:09 Eastern)

- Root merged17 existing non-border Actions into the labeled Controls search with curated descriptions, normal eligibility reasons and unchanged `action` routes. The44 original border buttons retain `borderaction`. Unknown/privileged command IDs are not promoted. **25 focused browser checks** pass at320×568/390×625/768×844, including every action tap, disabled requests, plain-text labels and stable focus. Full suite running. Numbered groups retain their existing Units drawer.
- Context client installed after reviewing the full-chain patch and comparing ZIP entries: only `Assemblies/OpenDreamClient.dll` changed. Final native private check passes **22/22**, including canceled/cross-row/focus-loss taps, original SetTarget, unchanged queues, edge placement and no accumulated touch highlight. Manifest: `../replica/reports/context-click-install.json`; client `9a0a190a7ea1113e41c07cd20c4589a7a389452e4c474c42b1890ef9d1eb1e26`, ZIP `7e53b1fe05796177e3eae2594450fa3de7d0cecddce57f10f1c5dded51f45643`. Canonical app still the second integration; shared source/artifacts only updated.
- Next full-world acceptance uses the real starting Humans for queue→tree harvesting→collection after deselection. This supplements, and must not replace, the accepted selection/movement evidence. Tool availability and natural targets are being audited first.

- Controls integration full browser suite now passes **226/226** with zero errors and stable HTML `83859d13db4c2c5e34a748f32e64be55afd0344b768e9119e93ee6ca1d9df298`. Root visually inspected the narrow Rename search result: full-width action, readable explanation and fixed Close.

### Long-run failure found and isolated (02:12 Eastern)

Full world-log review found `Cannot dereference proc "SunLight" from <deleted>` in both ongoing snapshots, after Gremlin movement onto Desert/Snow. Server console logs alone were clean; earlier progress updates that described no runtime errors were incomplete. The initial hour run continues for wider diagnostics, but is already a failed clean-soak result. The second run was intentionally stopped after579.7seconds, with its failure and full logs retained in `tests/overnight-world-second-soak-checks.json`. Its108,000-tick target was **not completed**.

Root is reproducing the lethal temperature→SunLight call with real Gremlin/Human constructors. A verified narrow fix will be followed by a new long-run snapshot; neither failed run will be presented as passing.

### Third increment integrated into source (02:18 Eastern)

- Terrain lifetime regression: **24/24** in `tests/terrain-lifetime-fixed-checks.json`, real Gremlin/Human/Vampire boundary cases. Original heat/cold can delete the entering unit; Desert/Snow now return before a second call on that deleted unit. Damage/death effects and surviving-unit sunlight remain unchanged. Before report preserves four failures; no claim of a clean long simulation yet.
- Native list prompt: **51/51** passes after preserving the required selected row when it is tapped again. Before: six failures where default Potion Drop/Guard choices became unselected and OK did nothing. Original payload/effects/nullable lists remain unchanged; physical touch/typing and native prompt sizing are not certified. Client `5481500f…`, ZIP `21879127…` installed with six curated actor files; exact writes/backups in `../replica/reports/prompt-and-actors-install.json`.
- Curated actor validation: **139/139**, zero errors, stable candidate/runtime. Rename, speech, emote and royalty revalidate the original selected living actors after prompts; canceled/stale requests preserve work. Controller deletion, crown changes and existing DE+FreeSelect semantics have explicit cases. Pure HUD eligibility agrees with dispatch. Original Login dynamic verb grants remain a separate shared-engine investigation.
- Real original full-world orders: **22/22**, 254 observations, starting three-Human army. A selected Human chops two natural trees through the normal collision path, continues FIFO while deselected and unloads automatically: seven logs deposited, one carried, four seeds left on the ground, other two Humans idle. No capacity violations or runtime errors. Private snapshot kept pre-fix Turfs; exact scope is in `planning/FULL_WORLD_ORDERS_CHECK.md`.
- A third private three-hour world snapshot is starting with the terrain fix, latest actor files and runtime `783f6ad…`. This has no connected player, so it does not certify Login or HUD behavior. Canonical app remains the second verified build until the next passing integration.

### Native Controls acceptance and next candidates (02:23 Eastern)

- `tests/curated-controls-native-compact-receipt-checks.json`: **44/44**, actual WebKit Controls buttons → byond navigation → original Topic → native prompts/effects. All62 catalog rows (45classic records +17curated) remain; server eligibility agrees with the displayed curated rows. Seven prompt outcomes verify rename/speech/emote/leadership cancel/commit, exact queue retention and untouched second Human. No OS input or normal saves. Root visually inspected the native drawer capture. Early private probe placement and oversized diagnostic receipt attempts were test setup failures, corrected without production HTML changes.
- Private Masonry increment passes104 checks, plus50Carpentry/142terrain regressions. Before32 product failures retained; details in `BUILD_HANDOFF.md`. Candidate not yet promoted.
- Shared `typesof(/Targeting/verb/)` is confirmed wrong against original BYOND: standalone direct verbs are missing and `/Type/proc` wrongly includes verbs. A narrow private runtime candidate is being compared with actual Login; no unconditional grant or Login workaround was added.
- Staged original-stat defense acceptance is investigating a diagonal helper that receives the alert but drops the response on its next tick. This is not yet classified as a production defect.

### Initial hour completed; source integration at02:26 Eastern

- Initial simulation completed36,000ticks in3692.9seconds. Report `tests/overnight-world-initial-soak-checks.json` is correctly **FAIL** because seven deleted-unit SunLight exceptions occurred. No other exception signatures were found. The new third simulation continues on its fixed terrain snapshot; no successful long-run claim yet.
- Installed shared runtime `f81a365897c80b9cbb748ba821d6c6a4e3f77760465fee17c18c62fba87d060d` restores direct verb/proc group enumeration against BYOND. **52 focused** and **15 original-Login native** checks pass; actual initial three-Human army has SetTarget in the real submenu, and ordinary player admin/clan grants remain zero. Global `/proc` enumeration remains a documented separate limit.
- Masonry's tested two-file source increment is now installed; all104checks plus50Carpentry/142terrain regressions passed before promotion. Exact fivewrites/runtime/source backups: `../replica/reports/typesof-masonry-install.json`. Canonical app remains the second verified package.
- Diagonal-helper root cause: original BYOND uses square grid distance, but this compiler standard used rounded Euclidean distance. The agent is preparing a shared standard fix verified against a BYOND oracle; no defense-specific distance workaround was added.


### Grid distance, Paper, Guard and sprite integration (02:34 Eastern)

- Grid distance now follows original BYOND square-grid semantics. `../replica/reports/distance-install.json` records the shared compiler-standard installation and backups; standard SHA `56851ae14a16ccb715a723b595a894985f1e6c4cae3bdd3b176a297e8eb1093b`. **102 comparable oracle cases** pass (35 failed before); two area-constructor placement discrepancies remain excluded and explicitly incomplete. Native original-stat defense passes **22**: the diagonal eight-tile helper travels while deselected, returns to its interrupted tree, collects four logs, then completes its queued move. Nine-tile and other-level controls remain idle. No defense-specific distance workaround.
- Paper crafting now rechecks the original Human intelligence/Svartalfar requirement after the recipe prompt. **59** Carpentry assertions pass, including a newly reproduced stale-intelligence rejection and unchanged successful Human/Svartalfar effects. One-line source change and backup are in `restore-points/overnight-paper-eligibility-20261017-0231/`.
- Guard revalidates captured actor/controller lifetimes, ownership, profiles and the granted verb after prompts. Selection changes retain the original actors without redirecting orders. Clear Rules clears obsolete patrol destinations while preserving active task/delivery/role/defense destinations, including destinations sharing the old patrol tile. **53 Guard**, **35 manual**, **139 curated** checks passed before promotion.
- Sprite Blend now falls back to SOUTH when the source lacks a requested direction, matching **72 eligible direction oracle cases**. The focused checker passes **588** assertions plus generated 11, variants 81, rewind 22 and buffer 120. Female side-view corpses improve but remain partially different; destination expansion, frame expansion, missing-state construction and arithmetic differences are still open. Original art is unchanged.
- Exact five-file Guard/Blend promotion is in `../replica/reports/guard-blend-install.json`; runtime `3879e6f7ad058d41d6fd8e65082f188829696489136515b1aadbf5b0bef590db`, builder `794d0ee2d65ccbffb730d35f2535bbbb98e60c94bd7c35c4ff066aec654882e1`. Shared/client are unchanged. Canonical app remains the second verified package while a combined source/runtime/standard regression batch runs.
- Packaged app checker now supports unique report labels and all 13 original ordinary starting races. Counts/types were reviewed against Restart; checks require living saved units. These new race checks have not yet run. Deeper cage/inventory/royalty persistence is a separate agent investigation.


### Third app built; packaged verification running (02:38 Eastern)

- `tests/third-integrated-regressions.json`: **874/874** gameplay assertions pass on the installed combined source, runtime `3879e6f7`, grid standard `56851ae1`, and client `5481500f`. Covers Guard, curated actors, manual handoff, Carpentry/Paper, Masonry, terrain construction/lifetime, delivery, orders, defense, inventory, magic and groups. Source/artifact hashes are stable throughout. These are isolated behavior fixtures, not 874 GUI gestures.
- Third canonical app built: **193,461,782 bytes**, compiled game `4b04ddd47e4dccb4ac828cc7170389d09d6e741873351117230075e9c1275ed8`. Original sprite rebuild compares 9,311 cells with unchanged originals; all45 border records and47 glyphs pass. Actual packaged Human save/reload is running before other ordinary race checks. Second verified app backup remains available.
- Fourth bounded original full-world simulation started at06:36:49 UTC with current source/runtime and a **fully copied compiler** (including new grid standard). Target108,000 ticks; up to30 minutes extra wall time allows for slower loaded execution. Snapshot `tests/overnight-world-fourth-source.json`; result pending. Third fixed-terrain simulation also continues on its older source/runtime/standard snapshot.
- Smelter candidate remains private: **84** checks plus59 Carpentry/Paper pass. Actual LoadUnits cage-containment defect reproduced privately; correction is under test. Neither candidate is included in this third app.


### Third packaged lifecycle passed (02:40 Eastern)

`tests/overnight-third-app-checks.json` passes both launches: three living Human units, exact race/type, fresh distinct save acknowledgments, successful host flushes, clean client/server/world logs, no remaining locks, and stable app/current artifact hashes. Normal Kiwi save remains `368992a…`. Startup plus save took123.5seconds; reload plus save70.3seconds. Backup of the proven complete app and source: `restore-points/overnight-third-integrated-app-20261017-0240/`. The12 other ordinary races are being tested sequentially with unique private profiles/report labels; `tests/overnight-third-race-matrix.json` will record each completed case. No all-race claim until completed.

Native prompt sizing and an explicit mining-material stockpile filter are now private usability candidates. The existing mixed filter remains wood+stone by default. New mining delivery must exclude cut gems, rings, skulls, finished equipment, food and seeds, and retain real unit capacities and exact task objects. No private candidate has changed the frozen third app.


### Private acceptance at 02:50 Eastern

- The frozen third app has passed Human, Orc and Dwarf fresh-army/save/reload checks; the remaining ordinary races are still running. This is not an all-race result.
- Mining supplies candidate passes **65 backend assertions** against original Human/Orc capacities, with **24 baseline failures reproduced**, and **253 browser assertions** across three screen widths. The new filter accepts stone, ores, sand, uncut gems and bones; cut gems, rings, finished gear, food and seeds stay excluded. Default mixed remains wood+stone. Native original-world mining acceptance is in progress before promotion.
- Smelter candidate passes84 assertions plus59 Carpentry/Paper controls. Contained-unit save candidate passes34 two-launch checks, after reproducing three containment failures. Both remain private and have reviewed manifests. Ground containers outside the player save graph remain an explicit persistence limit.
- Sprite expansion and explicit-frame constructor candidates are reviewed privately. Destination expansion passes72 history cases; constructor matches192/193 oracle cases, fixing56 selector exceptions and66 delay differences. The remaining absent-state constructor behavior is under separate investigation. Exact evidence is preserved under replica/reference/blend-expansion and replica/reference/icon-frame.
- Native dialog sizing passes65 normal-scale checks. A150% follow-up exposed inherited hidden-window render-target bookkeeping and long-label clipping; those failures are retained. A separate minimal Robust candidate is being tested. No dialog-sizing candidate has entered the canonical app.
- Lead is testing Work-tab control continuity: role/recipe nodes are currently replaced whenever any worker status changes. Holding a tap through an update must not lose the intended action; a changed actor selection must cancel the held action. This is a private browser candidate, not a product change yet.


### Private candidates and native mining acceptance (02:57 Eastern)

- Native mining candidate passes **24/24** in `tests/full-world-mining-placed-checks.json`: one original Human mines two natural tiles, collects real stone20 and Iron20, auto-unloads at105/110, then completes exact Mine→Mine→Drop off→Move task objects while deselected. The original seven items and85weight survive, including its original25weight Quality PickAxe, and other starting Humans remain idle. No runtime errors or OS input. The explicit fixture aid moved only the original worker and camera once from its distant natural spawn to existing grass beside reachable mine tiles; no tools, stats, terrain, AI or RNG were changed. The earlier no-nearby-target attempt is retained as incomplete.
- Stable Work controls candidate passes **33/33** browser pointer/keyboard checks (9/33 before), plus253 combined HUD assertions. Two independent source reviews found no blocker. Native WebKit/workshop acceptance is being prepared; this HTML remains private. See `WORK_CONTROLS.md`.
- Missing icon-state constructor candidate passes475/475 original-executable cases and193/193 prior frame cases. All28 frame-zero direction cells for seven original MakeBody variants now match. Default SOUTH was already exact; this is generated-image fidelity, not a demonstrated new normal-play facing effect. All three sprite increments remain private, preserved under replica/reference/{blend-expansion,icon-frame,icon-missing}. Full animated frame expansion remains open.
- Fifth private world simulation started at06:54:44 UTC, target108,000ticks, runtime `b97db61030877015c9bda6cced4392defe3e85ce1cefb3f46123071f461946fd`, with the reviewed Smelter, containment, Mining supplies and stable Work controls overlays. Compiler/source/runtime are copied; no connected player or normal saves. Source manifest: `tests/overnight-world-fifth-source.json`. It does not certify GUI or save behavior.
- Lead stopped the older third world at06:57:25 UTC to reduce concurrent memory/CPU pressure on current native acceptance. Its result is **incomplete/false**, 22,800 observed ticks over2388.1seconds, zero runtime errors; it did not finish the three-hour target. Reason and exact process identity are in `tests/overnight-world-third-interrupted.json`. Fourth and fifth simulations continue; no completed long-run pass is claimed yet.

### Work and sprite acceptance under review (03:08 Eastern)

- Native Work/Carpentry candidate passes **29/29** in `tests/full-world-work-candidate-checks.json`, zero runtime errors. Real WebKit role/recipe nodes and focus survive live queue/status updates; changing selection detaches a held recipe and its stale release does not order the new unit. Those native pointer events are explicitly synthetic DOM diagnostics; the separate33-check browser suite uses browser input.
- One original Human chops a natural tree while deselected, builds the original two-part Carpentry workshop, then completes bucket→spike→spade in exact order. Recorded states show build consumes one of four logs and increases woodcraft25→26; each recipe consumes one remaining log and adds0.5, ending27.5skill and original85/110inventory. `full-world-work-candidate-effects.json` supplies **4/4 post-run checks** of those costs, not four extra game runs. Only aid: one original worker/camera placement on existing grass near reachable natural resources. Original stats/tools/RNG and the other two starters remain unchanged.
- Sprite frame-expansion candidate `ab778b9f` passes664 focused assertions,130 main and98 timing oracle cases. All84 original MakeBody cells and metadata match. Existing constructor475/frame193 and generated11/variants81/rewind22/portrait8 controls pass. Root reviewed the two-file generated delta and verified35 manifest file hashes; durable evidence is in `../replica/reference/blend-frames/`. Native renderer acceptance is now running separately. Nine pre-existing composition-boundary differences remain explicit; no broad icon-parity claim.
- Enlarged native dialogs pass internal geometry at100%,150%,200%, but the200% run revealed footer buttons beyond the screen edge. **Release remains blocked** for that dialog candidate until initial placement is corrected and verified against actual usable monitor bounds. Current app/source remain the proven third integration while its ordinary-race save/reload matrix continues.

- Sprite renderer acceptance subsequently passed **153/153**,330 actual client samples: seven original MakeBody variants complete0→1→2→0 in each cardinal direction, matching84 oracle cells, then hold frame zero at rest. Live Human idle/walk and Fire controls pass. Fixture-directed corpse movement is explicitly a rendering test, not normal gameplay. No injected/observed input and no runtime errors; private processes stopped. Exact source snapshot, reports and traces are retained in `../replica/reference/blend-frames/native/`. Canonical source/app remain unchanged pending the current race matrix.


### Fourth source integration and package (03:22 Eastern)

- Frozen third app completed **all13 ordinary starting races**: Human baseline plus12 sequential fresh-army/save/reload pairs. Every expected unit count/type and living state passed with fresh host-save acknowledgments and clean logs. `tests/overnight-third-race-matrix.json` is complete/true. This evidence belongs to that frozen third package, not to later DLLs.
- Installed the reviewed Smelter, mining stockpile, stable Work controls and contained-location source changes, together with cumulative sprite runtime `ab778b9f…`. Exact11 writes, predecessor hashes, cumulative builder lineage and backups are in `../replica/reports/fourth-source-install.json`. Source backup: `restore-points/overnight-fourth-source-20261017-031701/`.
- **1,023/1,023 gameplay assertions** pass on that combined source/runtime/standard, with stable hashes: `tests/fourth-integrated-regressions.json`. Covers the prior13 suites plus84 Smelter and65 Mining checks. **253 HUD** checks and **33 held-control** browser checks pass on HTML `6f00dae9…`, zero browser errors. Their uniquely labeled outputs preserve earlier reports.
- Native dialog final artifacts pass **92/92 at each of100%,150%,200% scale**, including actual screen-edge owner placement, footer bounds, repeated Show, Manual startup, destroyed-child queue rejection, original prompt outcomes and unchanged queues. Root reviewed source/IL scope, verified hashes and inspected Guard/long-choice captures. Initial offscreen and importer-access failures remain retained. Full builder→private install→rebuild passes11 checks with identical outputs; incomplete/sizing-only installs are rejected before mutation.
- Installed dialog source/build chain, client `ab734530…`, native Robust bootstrap `e265bd68…`, clientZIP `7a029970…`; Shared remains `9d35743a…`, production WebView `a1e40242…`. Only OpenDreamClient differs inside the content ZIP; Robust remains a separate native bootstrap. Exact13 writes and clean-bootstrap backup: `../replica/reports/prompt-targets-install.json`. Durable source/evidence: `../replica/reference/prompt-targets/`.
- App builder now includes the native Robust bootstrap in its build marker so a bootstrap-only change refreshes the profile's copied client. Packaged checker verifies both the packaged and actually copied bootstrap hashes. Build-date metadata is20261017 and stockpile help describes the new filter. The archived dist release is unchanged.
- Fourth canonical app built: **193,470,546bytes**, compiled game `bc43ddd62a8fceae1b19587f9c107e968594553223b8300e7d98206945f8fe1d`. Its actual packaged Human lifecycle is running; no packaged-pass claim yet. Third proven app backup remains available. Normal Kiwi save remains unchanged.
- Separate orphan-captive candidate passes37/37, including actual original pit→Capture→Drop→Save/reload and unit Select/move. Baseline retains five failures. The8-line proposed load reconciliation preserves carried cages and current occupied pits; no ground-world serialization or ownership changes. Root reviewed and preserved it under `reference/orphan-cage/`; it is **not in the fourth app**.
- Separate exact-name/movement Blend candidate fixes real Deer Death composition and retains absent-name behavior. Root reviewed its DreamIcon-only delta and preserved `../replica/reference/blend-variants/`; native renderer acceptance is running. It is **not in the fourth app**. A confirmed Movable-world enumeration omission is under separate oracle-based investigation; included turf/container callsites are unaffected.


### Fourth packaged lifecycle passed (03:24 Eastern)

`tests/overnight-fourth-app-checks.json` passes both launches: three living Human units, correct types, distinct fresh save acknowledgments, successful host flushes, clean client/server/world logs, no remaining locks, and stable current/package hashes. Both phases copied native Robust bootstrap `e265bd68…` exactly. Startup/save took99.0seconds; reload/save72.1seconds. Normal Kiwi save remains `368992a…`. The proven app and current source/tools/planning are backed up at `restore-points/overnight-fourth-integrated-app-20261017-0324/`; source archive SHA `810b9016316f6e00f93ff20682e961b50521cf16871e01b30d928fba4efab542`.

- Exact-name/movement Blend candidate now passes **64/64 native assertions**,327 renderer samples and eight complete body animation cycles. Actual original Deer/Human Death outputs match every observed BYOND cell, rest at frame zero, and retain facing; live Human/Fire controls pass. Evidence is in `../replica/reference/blend-variants/native/`. The test copied an older218 content ZIP and explicitly overlaid clientab734/Shared9d, with native bootstrape265. No input or animation-index forcing; fixture-driven corpse motion is a rendering diagnostic. Candidate remains private.
- Next-idle candidate passes **36/36 original Human/Orc behavior checks** and **18/18 responsive browser checks**, after reproducing24/34 behavior failures. Count and picker share a read-only eligibility predicate; repeated taps cycle one available worker, and an empty result preserves selection, camera, modes and work. Root reviewed the two-file delta; native acceptance is pending.
- Expanded Movable oracle rejected the first simple shared-helper fix: it corrected nine world-loop cases but changed three `locate(/atom/movable) in world` cases. That candidate will not be installed. The revision opts in from the world-loop consumer while preserving the existing helper's default semantics; eight preexisting container-order differences remain separately documented.


### Fifth source accepted; package rebuilding (03:33 Eastern)

- Installed7 exact source/artifact writes: Next idle count/picker/cycling, orphan-captive reconciliation, and cumulative runtime2bc7fca1 (exact-name/movement sprite Blend plus consumer-scoped Movable world iteration). Builderdb5d3965 retains the full previous chain. `../replica/reports/fifth-source-install.json` records hashes and `restore-points/overnight-fifth-source-20261017-033040/` backups. Client/Robust/Shared/WebView remain unchanged.
- **1,059/1,059** installed gameplay assertions pass across16 suites, source/artifact hashes stable. **253 responsive HUD**, **33 Work held-control**, and **18 Next idle browser** checks pass. Source HTML043c3472/HUD56da8bfc. The fourth proven app remains the last completed lifecycle while the fifth rebuild runs.
- Captive correction rerun on installed2bc7/ab734/e265 passes **37/37** through two real private client/server launches, including original Capture/Drop/Release prompts and saved containment. It uses canonical Savesbbd5 directly; no additional orphan patch was injected. Six logs are clean and source stayed stable. Retained in `reference/orphan-cage/fifth-integration/`.
- Next idle native acceptance passes **37/37** with three real WebKit button requests cycling Human→Orc→Human. Busy/contained/trapped/sleeping units are skipped. A separately labeled stale request through the production browser transport preserves exact work/defense, selection, camera and input modes; a disabled button emits no request. Root inspected the actual panel capture. No OS input or normal save. Durable evidence: `reference/idle/`.
- Follow-up direct selection candidate reproduces the same lost-selection pattern for rejected unit cards/map clicks. Its QoL-only hunk passes59 focused and20 existing checks, preserving original selectable busy/injured/held units and allowing removal of an already-selected sleeping/contained unit. Root reviewed and retained it in `reference/selection-commit/`; it is not in the fifth source/package.
- Kitchen/ordinary CampFire actions are being checked privately for premature cancellation handoff and stale actors. Composed portraits are under a separate API/cache audit. Neither is included in the fifth build.

### Fifth packaged lifecycle passed (03:37 Eastern)

`tests/overnight-fifth-app-checks.json` passes new Human army and reload: three living original Humans each time, fresh distinct save acknowledgments, correct copied native bootstrap, zero client/server/world errors, removed launcher locks and unchanged normal Kiwi save. All recorded package/source hashes match. The complete verified app and source are preserved in `restore-points/overnight-fifth-integrated-app-20261017-0337/`. Normal app remains closed.

The next private increment combines rejected-click selection preservation with cooking commit-only handoff; neither is in this package. Two-player HUD/save isolation is now being checked in separate private profiles.

### Private multiplayer, cooking and HUD status checks (03:42 Eastern)

- Two connected native clients pass **97/97** using parent original Login, distinct private profiles/ckeys, original Human/Orc constructors/capacities and real inventory. Ten deliberately forged cross-owner requests leave both exact queues untouched; real own-unit controls work; original SaveUnits writes separate correct rosters. `reference/two-client-isolation/` preserves all verified inputs and evidence. The fixture enables existing MultiKeyAllowed only to permit same-computer clients and creates the two units; it is not full multiplayer/network/mobile parity. Reload is a separate follow-up.
- Combined selection/cooking candidate passes **59 selection + 230 cooking + 20 group** headless checks. Native cooking then passes **79** using original Human/Orc, map renderer hit-tests/network dispatch and actual prompt callbacks: cancel/range rejection preserves the FIFO; successful attempts act on captured actors after deselection; milk/Fire paths work. Fixture supplies ingredients and a naturally blocked no-axe task, with no stat/RNG overrides. No OS input. These changes remain private until integration.
- Root reproduced four paused-production display failures: a manual worker retains paused crafting attempts after Stop/manual handoff but its card offers Pause instead of Resume. Private HUD/data clarification passes **18 original-unit state/effect + 60 browser** checks. Simulation is unchanged; retained production is explicitly explained. Source remains private pending review/merge.

### Sixth integration candidates (03:58 Eastern)

The canonical app remains the proven fifth build. A private combined sixth source is running regressions; no new packaged claim yet.

- Cooking + altar menus commit handoff only on real effects and keep captured, owned, living actors after menu yields. Original outcomes/costs remain. Altar408 headless and110 native checks pass; cooking250 headless and79 native pass. Exact inputs and failed baselines are preserved in `reference/{cooking,altars}/`. Native callbacks are internal diagnostics, not physical input.
- Rejected selection preserves existing work/selection;59 original-unit checks pass. Paused crafting displays Resume and queued attempts:18 state/effect plus60 browser checks. Worker death/dying blocks production/hauling effects:40 checks. Paused production-only units no longer answer nearby help while retaining self-defense:56 checks.
- Quick Campfire/Carpentry construction retains interrupted queues, delivery, role and production. Running production-only manual workers still craft automatically; other interrupted work pauses for Resume.240 focused original Human/Orc checks pass after108 final-baseline failures. Earlier four role-continuation failures remain preserved.
- Portraits compose original hair/equipment and refresh on real equipment changes.455 pixel/control,25 roster-cache and65 actual native browser assertions pass on current runtime.300-unit stable rosters send no repeated resources after initial load. Unsupported effects explicitly fall back to the previous base portrait; full appearance flattening is not claimed. `reference/portraits/` preserves1,143 verified inputs/evidence hashes.
- Two-player reload passes102/102 through original Login→LoadUnits using the exact previous saves, without recreating units or inventory. Both clients retain own roster/inventory; foreign requests remain rejected. Private MultiKeyAllowed enables two clients on one computer. Original temporary task queues are expected empty after reload. Earlier read-only-save and fixture LoggedIn assumptions remain documented; no original login semantics changed. `reference/two-client-isolation/reload/`.
- Held Pause/Resume retains its intended action through live state changes (28 browser checks). A separate concrete Stop timing defect was found: selection changing between receipt and deferred dispatch could stop the new actor. A bounded selection-intent fix is in private development.

Two older full-world simulations remain running with no observed errors; completion is not yet claimed. Normal app stays closed and the pre-existing zero-unit normal save remains unchanged.

### Long simulation found a combat lifetime failure (03:58 Eastern)

The fifth private long simulation is **failed/incomplete**, not a pass. Its actual ErrorLog contains a deleted-target `LeftLegHP` access in `Attack` at `Combats.dm:540`, through original Bump/RandomWalk, at tick19,800. Root found this while scanning the actual ErrorLog; the earlier no-observed-error statement did not detect it. Original source/log and exact process identity are preserved in `reference/overnight-combat-deleted-target/` and `tests/overnight-world-fifth-interrupted.json`. The failing run was stopped at last sample37,200ticks to free capacity for a corrected current-runtime run. Fourth long simulation remains active. Combat agent is reproducing this actual failure before lower-priority DragonBreath help coverage.

### Combined private regression and natural-world workflow (04:03 Eastern)

`/tmp/remastered-sixth-integration/tests/sixth-private-regressions.json` passes **2,130/2,130 across25 suites**, with all source/runtime hashes stable and zero errors. This exact pre-final merge contains selection commit, cooking/altars, portraits, paused-production display/helper policy, dead-worker gate, quick-build retention and held Pause intent; later selection-dispatch and combat-recursion fixes are separate. Its full-world native workflow passes29/29 plus4 recorded cost observations: original Human chops a natural tree while deselected, gets4wood/2seeds, creates the original two-part Carpentry, then attempts bucket→spike→spade. Original85/110 inventory is restored and woodcraft25→27.5; no skill/capacity/RNG overrides. Physical input is not claimed.

The actual long-soak deleted-target error was reproduced in nine cases using original recursive Attack and Death. A five-line candidate checks attacker/victim existence after the five existing recursive calls. Candidate144/144 passes versus135/144 and nine caught deleted-field errors before; controlled fixture hit-location and injured brain values are explicit. Living recursion, original damage, death/roster/cargo/reward controls remain. This candidate is not yet in the packaged app.

### Sixth source promoted (04:06 Eastern)

Eight reviewed game files are now installed; `reports/sixth-source-install.json` records exact predecessor/candidate hashes and `restore-points/overnight-sixth-source-20261017-040646/` backs up their predecessors. Shared engine/client/art, Classic game, archived release and Godot remain unchanged. The app is rebuilding; fifth remains the most recently completed packaged lifecycle.

The final merged source passes2,130 gameplay assertions,39 exact-selection dispatch assertions,253 full responsive HUD,21 held-selection,28 held Pause and60 production-display browser checks. Source/runtime remained stable throughout. Native selection receipt39/39 rejects missing/wrong/stale tokens and validates real visible controls; no physical input is claimed. The package includes original-item portraits and the five combat recursion guards, alongside the prior private6 changes.

A new copied full-world run started08:04:15UTC, with a72,000-tick/two-hour target and9,600-second deadline. `tests/overnight-world-sixth-source.json` and `overnight-world-sixth-tested-source.zip` identify every source and observer addition. No connected player, normal save, artificial populations or stats. Completion is still pending. The previous fourth long run continues separately.

Reproducible regression tools were promoted with the source. The altar helper defaults to the current game (explicit baseline overlays remain available); selection-intent checks accept a port argument. These test-only portability adjustments do not change game files or the completed observations.

### Sixth packaged lifecycle passed (04:10 Eastern)

`tests/overnight-sixth-app-checks.json` passes both private phases: three living original Humans, fresh distinct acknowledgments, correct copied native bootstrap, no client/server/world errors, removed locks, stable package/source hashes and unchanged normal save. Compiled game SHA256 is `397faae0d2f17f3a4606235ef202b7bdcfd2742f9e473e4e36cb5e23b417b3ea`. The normal app stays closed. Engine framebuffer screenshots omit native WebKit panels by design; dedicated native HUD snapshots provide separate UI evidence.

The next private increment covers direct Work selection receipts, Melter prompts and ordinary DragonBreath calls for nearby help. These are not in the sixth package.

The complete sixth app/source/tool/planning snapshot is preserved at `restore-points/overnight-sixth-integrated-app-20261017-0410/`; copied package hashes match the passing lifecycle. The next package checker adds optional read-only native WebKit panel captures, because framebuffer screenshots exclude them. It writes no input requests; actual next-package acceptance and visual inspection are pending.

### Seventh source promoted (04:17 Eastern)

Five exact source files extend selected-command receipts to direct Work routes, migrate Melter to committed handoff with three-prompt actor revalidation, and report ordinary hostile DragonBreath through the existing nearby-help policy. Source install report records predecessor/candidate hashes and a backup. The shared engine and original art remain unchanged. Rebuild/package acceptance is pending; sixth remains the last verified package.

Private combined acceptance passes **2,816 assertions across30 suites**, plus144 recursive combat checks and47 Work browser checks. The unchanged exact HTML also passed253 responsive HUD assertions. Native Work passes127 and Melter170 through actual UI/network callbacks without OS input; Melter headless458 preserves original filters, ranges, weights, EXP and Cancel/No group semantics. Durable evidence: `reference/work-selection-intent`, `reference/overnight-melter-handoff`, and `reference/dragon-defense`.

Next private audits: loose equipment tap/pickup, carried Food/Equipment prompt ownership changes, and a paused-role HUD projection that incorrectly offers Resume during active finite work. No such next-candidate changes are in seventh.

### Further interaction audits (04:20 Eastern)

The seventh package built successfully (compiled game`6fd4e02c80a544b354ac97381ff2cd7f92970e7e72b6163133287f33ade0ec11`). Its private Orc new-game phase has completed; reload is pending. Root visually reviewed its actual native WebKit HUD capture: original Orc portrait, dark green/gold interface, labeled commands and company cards render. The new optional package checker preserves native panels separately from engine screenshots and writes no input requests.

- Original-verb availability audit passes24 on frozen sixth/current runtime. Owned/foreign Humans expose SetTarget; loose stone/turf have no applicable native verbs; carried stone stays in inventory. Opening menus preserves exact work/cargo/selection/facing.389 durable files verified in`reference/context-availability/sixth`. This is availability evidence, not a universal interaction menu.
- Portrait fallback follow-up passes51, with original HolyShield/Slowdown fractional-alpha effects deliberately falling back to base; Fire/Sleep remain supported.57 durable files verified in`reference/composed-portraits/ordinary-effects`.
- Root reproduced18 paused-status failures across66 original Human/Orc checks: a stopped background role/production makes a subsequently running finite task show Resume. A one-expression HUD candidate passes66 plus144 exported-model browser checks; explicit order pause/wait remains authoritative, finite work shows Pause, completed queues reveal retained background Resume. Independent HUD-agent review found no blocker. This is private for the next increment (`reference/pause-projection`).
- Agents are reproducing loose equipment taps and ownership changes during Food/Equipment prompts, and auditing Forge's original effect branches before a committed-handoff migration. None of these candidates is installed yet.

### Seventh packaged lifecycle passed (04:20 Eastern)

`tests/overnight-seventh-app-checks.json` passes new Orc army and reload: three living original Orcs, fresh distinct save acknowledgments, no client/server/world errors, correct copied native bootstrap, removed locks, unchanged normal Kiwi save and stable source/package hashes. Native407×625 WebKit panel snapshots were captured read-only and visually reviewed in both phases. No OS input or physical mobile claim.

A new `tools/check_orders_integration.py` entry point preserves the31-suite isolated regression command for future increments, with unique labels, source/runtime hashes and aggregate reports. The underlying30+1 checks passed before promotion; this new entry point itself will run on the next merged candidate.

`planning/PERSISTENCE_SCOPE.md` separates tested player/unit saves from temporary queues and unimplemented whole-world persistence. Original calendar randomizes at each server restart; differing day labels in the two HUD captures are original behavior. Whole terrain/building/dropped-item restoration is not claimed by passing unit-save reports.

Seventh complete app/source snapshot is preserved at`restore-points/overnight-seventh-integrated-app-20261017-0420/`; copied app hashes match the accepted package and source archive SHA256 is`3748d677a7a28d97c4a4e3b9da6b0f65dcb06bd4cb8439920240072d2c1837d6`.

### Eighth private integration in progress (04:30 Eastern)

The seventh package remains canonical. Private eighth currently combines its exact source with the Pause/Resume projection candidate and captured carried Food/Equipment menus. The carried handoff's855 durable files were checksum-verified:182 focused headless,42 existing inventory and104 native checks pass. Native ownership-transfer rejection, cancel, original item effects and original unselected DblClick convention are verified;16 real menus used internal DOM/native callbacks, no physical input. Earlier fixture-expectation failures are retained and disclosed.

Loose equipment pickup passed65 focused,72 existing orders and Human/Orc native13+13 checks; its final handoff is pending. The four-line classifier extension uses the existing finite pickup queue and does not auto-equip or change stockpile policy. Forge is awaiting its native acceptance. The HTML help text is being corrected to distinguish workshop taps, carried Inventory, Interact and older ground-object double-click menus; its new equipment claim will only ship with accepted pickup.

The two independent long worlds remain incomplete. At04:29 Eastern the older fourth reached65,400 ticks and the sixth reached13,200, with no errors in their actual ErrorLog at that observation. No completed long-run pass is claimed.

### Eighth frozen combined candidate (04:32 Eastern)

Eight source files combine: captured Food/Equipment menus; one-tap finite loose-equipment pickup; dead/dying first-selection dispatch rejection; correct Pause display during finite work above a paused background role; committed Forge handoff; and accurate Guide routes. The canonical app remains seventh while39 isolated combined suites run. Eighth HTML passed253 responsive checks.

Forge durable446 headless+81 native artifacts were checksum-verified.904 headless checks pass. One native run completed134 checks; its initial131/134 report compared the surviving quiver to the first inventory entry, which was an ingot. Root independently reviewed all three original before/after item arrays and accepted the explicitly labeled reanalysis. The134/134 corrected report retains original costs, skills, random success/failure and exact quiver identity. No new native run or product change was claimed for that correction.

Equipment829 durable files and carried855 were verified. Dispatch eligibility44 before/after and combined86 unique checks are preserved separately; a first90-check report with four duplicate labels is retained, superseded by a fresh86-case run. Ground-object route audit27 durable evidence/source files verifies52 original-handler controls; chests already use single-click, while doors/cages have legacy permission/content/weight quirks. No partial cage adapter was added. These findings refine the remaining one-tap interaction scope.

### Eighth source promoted (04:38 Eastern)

Eight exact source files are installed; package rebuild/acceptance is pending. Combined acceptance passes4,263 across39 isolated suites,253 responsive HUD and144 real-unit-model Pause/Resume browser checks. The first aggregate retained38 passes and one equipment-runner failure before gameplay: root's portability edit shadowed argparse state with a text index. The corrected checker alone reran65 tests on identical source/runtime and passed. `tests/eighth-final-regressions.json` preserves the failed aggregate; `eighth-accepted-regressions.json` links that SHA and the corrected focused run. No game code changed for this correction.

Source install report`reports/eighth-source-install.json` records all predecessors, candidates, backup and unchanged normal save. Prior source is preserved at`restore-points/overnight-eighth-source-20261017-043802/`; the seventh full app backup remains the accepted rollback. Forge native134 is explicitly reanalysis of its one captured run; carried native104 and equipment13+13 remain separate component evidence.

Separate next candidates are under audit: PoisonStation prompts, elemental DragonBreath helper calls and a shared-engine mixed-contents insertion discrepancy. None is in eighth. The native slot is currently Poison's private arena; root eighth packaged Dwarf lifecycle follows.

### Eighth package accepted (04:41 Eastern)

`tests/overnight-eighth-app-checks.json` passes both private Dwarf phases:3 original living Dwarves, distinct fresh save acknowledgments, correct native bootstrap, stable/current source+package hashes, removed locks, zero client/server/world errors and unchanged normal save. Actual407×625 native WebKit panels were captured read-only and visually inspected in both phases; original Dwarf portrait, labeled dock and cards render. Compiled game SHA256`d338d69f33438732f2f8ccaa2ea28838ace4904161109f8b6fe445fc3735c12a`; app193,519,157bytes. Shared runtime stays2bc7; no original art changes.

Ninth is private: candidate69b727e3 contents insertion matches531 ordinary/lifecycle comparisons and18 actual Human/Orc inventory/Death fields. Original world/locate oracle72/72 now matches, with prior sprite outputs retained.93 direct-list method discrepancies remain explicitly outside scope; no universal contents parity claim. New helper candidates cover elemental/Holy-undead breath and Poison Bolt. PoisonStation native had an incorrect Illithid missing-axe fixture assumption; its failed run is retained and a natural capacity-blocked fixture is being verified. None of those changes is in eighth.

### Ninth combined acceptance underway (04:51 Eastern)

The eighth complete package/source snapshot is preserved at `restore-points/overnight-eighth-integrated-app-20261017-0441/`; all756 package files match the accepted app. Its source archive SHA256 is `77655e180d7d329caba96ccc260b835ba544be3be8d61de77c29d7e377f8fc42`.

Private ninth combines six changed Remastered files with shared runtime69b727e3. PoisonStation448 headless +210 native and GemCutter774 headless +151 native now pass. Root checksum-verified153+53 native evidence files and visually inspected an original Gem native choice dialog. The earlier Poison incorrect Illithid tool assumption and checker KeyError are retained; corrected acceptance uses original Illithid capacity, not an artificial missing-axe rule. Gem Human Emerald naturally failed twice then succeeded; original Orc0 failed with exact costs/skill effects, and no native ring-success claim is made.

Firebolt/Fireball/Fiery Death add exactly three accepted-attempt defense notifications.212 focused +50 Poison regression checks pass on69b; immunity, friendly/off policy, costs/cooldowns and queues remain intact. Root verified400 durable files. Combined ninth48-suite run is underway; canonical app/runtime remain eighth/2bc7 until acceptance and source promotion. The exact updated HTML passes253 responsive assertions; its group-order guide distinguishes one worker per resource tap from moving the selected group.

The serial13 starting-race runner is prepared but not launched; its final package freeze follows final source acceptance. Both existing long worlds remain incomplete, with no errors in actual ErrorLog at04:50. Potion and direct Vampire feeding are bounded next audits, not delivered changes.

### Ninth source/runtime promoted and packaged (04:56 Eastern)

All48 combined suites pass5,903 assertions on frozen69b727e3 runtime and exact six-file ninth source, plus253 responsive HUD and144 exported-model Pause/Resume DOM checks. Aggregate SHA256 `67c58cf90b0324522cc4eaff4c6184b4bf0c6862656616ae1b5761f0980ff756`. `reports/ninth-source-install.json` records source/engine predecessors, candidates and backup at `restore-points/overnight-ninth-source-20261017-045611/`; normal Kiwi save remains unchanged. Shared builder and both runtime DLL copies are updated once; Classic gameplay, original art, archived dist and Godot remain unchanged.

The rebuilt ninth package is193,524,627bytes, compiled game SHA256 `d9782b63997c1931ba3ba366f008a53b23f950be5e173d5975bd8f3306421ca9`. Private Elf new-army/save/reload with native panels is underway; package acceptance is pending. Eighth remains the last fully accepted rollback.

Private tenth adds the accepted Potion758 headless +187 native and Vampire221 +103 existing defense increments. Root verified410+59 Potion evidence files and418 Vampire files, and reviewed both exact patches. Potion native uses four fresh original Human10 workers for three failed Cure attempts and one success; this is not cumulative training. Vampire's corrected real Attack→Bite fixture uses original neckguard Equip/UnEquip to enter the original explicit-zero helmet state, and proves duplicate notifications keep the original response/deadline and exact work objects. Earlier fixture failures remain preserved.51 combined tenth suites are running on69b; none of these three source changes is canonical yet.

### Ninth package accepted and preserved (04:59 Eastern)

`tests/overnight-ninth-app-checks.json` passes both Elf phases:3 original units atHP350, fresh distinct save acknowledgments, zero launcher/server/client/world errors, stable source/package hashes, correct native bootstrap, removed locks and unchanged normal Kiwi save. Root visually inspected both407×625 native WebKit HUD panels. Full756-file app/source checkpoint: `restore-points/overnight-ninth-integrated-app-20261017-050008/`, source archive SHA256 `7f01ac59266bb2e2f116af084a2192d0628fca86c515247bbc2317825294aaa2`. `reports/ninth-full-restore.json` records its manifest checksum.

The complete generated engine patch is now also consistent with69b: `reports/ninth-engine-source-artifact-install.json` records replacing stale8803 patch with independently regeneratedbe20948d. The only changed patch section is the already reviewed DreamObjectMovable insertion fix. Its predecessor is backed up; original release manifests remain unchanged. This supplemental source artifact does not change app/runtime behavior.

A separate test-runner audit reproduced a false pass when a world printed its completion marker but then hung until timeout. A private correction additionally requires no timeout and server exit0. Fresh15-second baseline/candidate/clean controls all meet their expected outcomes; an initial5-second baseline that never reached the marker remains documented.49 evidence files are preserved in `reference/runner-clean-exit`; independent review found no blocker. The correction is not yet installed or retroactively attributed to earlier suites. There is no evidence that previous accepted suites hit this condition.

At04:58, the older fourth world reached84,000 ticks and the sixth31,800 with no errors in their actual ErrorLog; both remain incomplete. BoneCraft and Werewolf follow-ups remain private, and final package/source freeze is still targeted for05:30 before the current-build race matrix and final bounded long world.

### Tenth source promoted and rebuilt (05:03 Eastern)

Three Remastered files add captured/committed Potion menus and direct Vampire bite defense. Exact combined51 suites pass6,882 checks on unchanged69b; HTML/HUD are unchanged from the ninth253/144 acceptance. Aggregate SHA256 `11729c060a183cc6d27039db48f8b6dfae01cd662f2955b7fd2f6aebea7643d4`. Source backup: `restore-points/overnight-tenth-source-20261017-050338/`. The rebuilt app is193,526,549bytes, compiled game SHA256 `f82d2aa61e2c0f031bfd7e69aa10418d712ed292731ff1d41587fcf8594b7154`; its native packaged lifecycle waits for Bone's private native slot. Ninth remains the last fully accepted package checkpoint.

Private eleventh overlays BoneCraft and two Werewolf bite notification calls. Root verified432 Bone headless and403 Werewolf artifacts and reviewed the exact source patches. Bone1391 headless passes; its first native141/204 run timed out after the Goblin worker legitimately moved without an axe. Original Goblin95capacity with real ballast/pickup now supplies the corrected native fixture; no rule/stat change is made. The retained headless clarification separates one-tick callback evidence from naturally blocked native work. Native rerun is pending.

Werewolf385/385 passes against341/385 before. Actual delayed300/500-tick behavior, original infection/recovery/royal resistance and ownership cleanup are preserved. Earlier source-reading timing assumptions and fixture failures are corrected in the handoff, not implemented as gameplay changes. The two-line source patch leaves all original rolls/spawn statements intact; a disclosed private prob90 wrapper controls delayed test outcomes. Natural ownership transfer uses the existing immediate ChangeOwnership→StopOrders behavior. Eleventh54-suite combined acceptance is running with the reviewed clean-exit/no-timeout harness guard; no eleventh source is installed yet.

## Tenth packaged acceptance —05:09 Eastern

`tests/overnight-tenth-app-checks.json` passes actual original Lizardman prompt/new-army/save/reload on compiled game `f82d2aa61e2c0f031bfd7e69aa10418d712ed292731ff1d41587fcf8594b7154`, runtime69b. Both phases retain3 original350HP Lizardmen, fresh distinct save acknowledgments, removed launcher locks, matching bootstrap and stable package/source/runtime. Zero launcher/server/client/world errors; normal Kiwi SHA368992 remains unchanged. Lead inspected the map and both407×625 native HUD panels: original units and portraits, labeled dock, visible first unit card. No physical touch claim.

Bone fresh corrected native acceptance passes183/183 across17 phases106 internal native actions; all121 durable files independently hash-verified. Initial141/204 fixture-invalid Goblin run and timeout retained; Goblin naturally bypasses Axe requirements, so the fresh fixture uses original95capacity and real ballast to hold a pending pickup. No unit-stat or RNG boosts. Original Crown outcomes on fresh workers and Arrow inventory identity are recorded. Eleventh54-suite combined run uses the stronger clean-exit helper; pending.

Final soak runner `a9d318e0` reviewed for copied sources/runtime, original startup observer, port isolation, process-group cleanup, clean-exit/timeout guard, stable hashes and unchanged saves. Its exact full-map observer compiled successfully against frozen eleventh; all10 preserved rehearsal artifacts hash-verified. No third long world launched. Final current-package race matrix and45-minute world run remain pending source freeze.

Tenth full checkpoint: `restore-points/overnight-tenth-integrated-app-20261017-051009/`, all756 app files hash-match; source archive SHA `5f6325560ff828401e9b3ef8b9f563882d9e0fbb122e4151aecb773e656ece1c`. Source/docs snapshots are time-stamped artifacts, not a substitute for this changing status ledger. `reports/tenth-full-restore.json` locates the manifest.

At05:11, private twelfth cumulative source (frozen eleventh + Leather Crafta58e6180/QoLa2677953) enters56 combined suites with clean-exit helper7c147928. Leather focused892 passes (196 main +696 effects); original matching baseline718/892,174 failures. Initial effects fixture692/696 and wrong marker are retained, corrected symmetrically before696/696. Leather native currently running; no twelfth canonical promotion. The11 and12 source trees are frozen independently. Team source freeze remains05:30 followed by final package matrix and current-source bounded world run.

## Final cumulative build decision —05:13 Eastern

Private eleventh passes54/54 suites,8,658 assertions, stable source/runtime and corrected clean-exit guards. It will not receive a separate package: the final cumulative twelfth includes Bone, Werewolf and Leather and is running56 suites. This avoids replacing the accepted tenth app for an unnecessary intermediate lifecycle. All promotion guards now compare cumulative source directly against accepted tenth and require both private integration reports and preserved component evidence.

Leather native passes145/145 across15 phases78 internal actions on original Human/Orc workers, no skill/capacity/RNG boosts. Native Human Quiver naturally failed once then succeeded on a fresh worker; Orc succeeded once. Actual MakeBody/pickup/TearSkin preserves carried40weight body identity and creates original ground skin; no-body/already-skinned retain work. All54 native files and433 headless files hash-verified; independent source-review copies retained. Earlier failed preparation and symmetric fixture corrections remain documented. Native slot released; no further workshop product edits planned.

Read-only recovery audit at05:14 confirms normal Kiwi still0 units/SHA368992; two earlier three-Orc backups parse with all graph references resolved and living350/350/450HP rosters. The newer21:43 snapshot retains more progress than21:25. `SAVE_RECOVERY_OPTIONS.md` records paths, hashes and scope; neither was loaded or restored. Missing army is preserved saved state, not diagnosed as a new overnight loss.

## Long-world failure triage and final world launch —05:17 Eastern

The old fourth snapshot (`Combats.dm`bd285d34/runtime3879) logged one deleted-target `RightArmHP` error after recursive Attack. It is the same lifetime defect already guarded in installed Combats51486: the current code checks both actors immediately after `.()` before reading the limb. Independent comparison removes the five new guards to reconstruct the old file; prior144-check regression explicitly includes Human/Orc RightArm lethal and living controls. No new gameplay fix or test was required for classification.

Preserved complete375-file tested world ZIP, compiled world, old runtime DLL/helper/runner and logs under `reference/overnight-fourth-soak-deleted-target/`, then stopped only verified private server59362. Wrapper exited1 with FAIL at05:17:06,9,612.9 seconds, last sample94,800 of intended108,000 ticks, one error and no completion marker. This is failed and deliberately shortened old-source evidence, never a clean long-run pass. The sixth corrected snapshot remains running separately.

The released slot now runs `tools/check_world_soak.py --source /tmp/remastered-twelfth-integration/game --label overnight-final --ticks 36000 --port 12299 --timeout 4800 --launch`. It copied the frozen final candidate/full maps and69b runtime, launched05:17:33, and requires exact60-minute tick completion, clean exit0/no timeout, stable copies/origins/helpers and unchanged normal saves. `tests/overnight-final-world-soak/acceptance.json` is live; result pending. Current package equivalence will be checked after cumulative promotion; source is frozen. Still only two long-running worlds.

Test-only helpers were updated after review: check_combat7c147 requires clean exit/no timeout (all54 private-eleventh suites record exit0); check_full_world_ordersa060318 rejects source/runtime/compiler/bootstrap/tool/compiled-world drift, with17 real temporary-file analyzer cases and unchanged original22 gameplay assertions. Both prior helpers and all candidate evidence retained; no new actual-play claim. A final original-Human two-tree/deselection/delivery replay is planned after the13-race native matrix.

## Cumulative twelfth promoted and built —05:20 Eastern

`reports/twelfth-source-install.json` records the direct tenth→twelfth three-file promotion after all56 suites/9,550 checks passed with exit0/timed_outfalse. Aggregate SHA `1b6e07d791ef012709ccee3f9fec18435e96712111c50d6c6d4c104f7e761d51`; private eleventh SHA`f531ecedd129ee8b9fb097df59753fca757034cae334a713a595bd04e40069cd`. Source backup `restore-points/overnight-twelfth-source-20261017-052007/`. Craftinga58e6180, QoLa2677953, Interact60da8cb9; shared runtime69b unchanged.

Personal app rebuilt193,537,623bytes, compiled game `93f76efd56c2f45f6e6e3c70c1ae2c5536efbecf19b5c8f8dda85c49f89bd282`. Original sprites unchanged,45 controls/47 glyph assets pass; archiveddist untouched. `reports/final-source-soak-equivalence.json` verifies all372 original-game resource/source files equal the frozen final-world snapshot; observer-only changes are separate. Frogman package lifecycle/native panels pending. No further gameplay or engine features before final acceptance.

### Twelfth packaged lifecycle accepted (05:23 Eastern)

`tests/overnight-twelfth-app-checks.json` passes both private Frogman phases: three original Frogmen at HP 350 survive new-army/save/reload, distinct fresh save acknowledgments, clean logs, removed instance locks and unchanged normal Kiwi save. Root visually inspected both native 407×625 HUD panels; the original portrait and first unit card remain visible. Compiled game `93f76efd56c2f45f6e6e3c70c1ae2c5536efbecf19b5c8f8dda85c49f89bd282`; runtime remains `69b727e…`.

Complete app/source checkpoint: `restore-points/overnight-twelfth-integrated-app-20261017-052529/`, 756 packaged files verified, source archive SHA-256 `54dd8ef18dead0f7097f9fabb73a58dd27b180d622e71acb95b6a17033b6c1e4`; acceptance in `reports/twelfth-full-restore.json`. The package is now frozen. The serial 13-race runner uses `reports/final-starting-races-freeze.json` and label `overnight-final-races`; its 845-entry package file/symlink inventory SHA-256 is `7de95d5d418099c54448b4f55e98ac60a1635795635def7f5487258283438976`. Results remain pending.

### Durable final regression evidence

`reference/twelfth-final-regressions/` now retains all 543 test/tool/aggregate files from the exact frozen integration run. Each of the 56 raw result hashes matches the 9,550-assertion aggregate; every server exit is 0 and every timed_out field is false. Manifest SHA-256 `817f8244a2b11921718bda3a9910b3366d8b189c70bf0f59b3fa4a6c2ed38d82`. This is preservation of completed evidence, not a rerun. Original temporary paths remain in raw reports and are mapped to durable files by the manifest.
