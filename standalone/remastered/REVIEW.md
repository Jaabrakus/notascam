# Standalone review — October 16, 2026

The project has advanced into a playable Mac standalone with a separate
Remastered branch. The strongest direction is a small-army colony/kingdom game
with persistent individual units. The existing races, skills, equipment,
injuries, workshops, seasons and underground levels give it substantial depth.
Making those systems visible and giving reliable feedback should come first.

This review inspected the current source, packaged apps, recorded comparisons,
game captures and logs. It reran the Remastered arena and packaged
startup/save/reload checks using disposable profiles. The app bundles OpenDream
and its client/runtime; it is not a Godot port.

## Evidence and limits

| Area | Finding |
| --- | --- |
| Classic compatibility | The existing current-runtime report matches **7,001 ordered observations across 27 fixtures**. Maps, icons and open-terrain wandering checks also pass. This report explicitly says `full_checks_run: false` and `exact_replica_verified: false`; the full suite was not rerun for this review. |
| Remastered logic | Fresh arena run passes **16 behavior observations plus completion**: selection variants, health-bar states, ownership changes, attack alerts/throttling and jump-to-attack. This checks logic, not all physical input paths. |
| Packaged startup and persistence | Both fresh runs enter the game, save three Human units, and enter again with three saved units. This is a unit-count smoke check, not equality of every saved field. The corrected repeat reports **failed overall** because startup logged one `LimbFling` exception; its reload phase has no recorded runtime errors. See `tests/app-checks.json`. |
| Build consistency | The installed Classic runtime/client match the Classic comparison report; Remastered bundles those same runtime/client binaries. The Remastered app and share ZIP have matching compiled-game, runtime and client hashes; see `tests/review-share-hashes.json`. This is not a separate-machine installation test. |
| Actual mouse input | Existing real-window evidence records selecting U1, replacing with U3, and box-selecting all three. The right-click step records no orders, so it is still unverified. The capture alone does not establish a visible drag rectangle. |
| Actions | The recorded run exercises many command procedures and records some effects, but the checker has no complete outcome assertions. It also missed an exception in the world log. “Every action works” is unsupported. |

Current compiled game SHA-256:
`c44dd047be99b7a95b6479d429c7cd66e19039ae93bc6f86e9a824623c2b35b4`

Current runtime SHA-256:
`773e90dcb023251c7242aa1d2d98cbf338f4ccf81ab3386d21994e0bf383b0b8`

## Defects and verification gaps

- **Combat lifetime errors:** the first live review run logged three exceptions:
  removing an overlay from a deleted target (`Combats.dm:352`) and calling
  `LimbFling` on deleted targets (`Combats.dm:609` and `708`). The world continues
  running, but those combat procedures fail. Full traces were retained in
  `tests/review-first-run-world.log`. The source uses a delayed overlay cleanup
  and limb-loss calls that can outlive their targets; investigate those lifetimes.
  The corrected repeat reproduced `LimbFling` at `Combats.dm:942`, retained in
  `tests/app-new_army-world.log`.
- **Misleading error detection:** `tools/check_app.py` previously searched the
  world log only for the words `runtime error`, missing OpenDream's
  `[ERRO] ... Exception occurred` format. The review fixed this, retained full
  per-phase logs, separated phase logs, required screenshots and added build
  hashes and timestamps. The detector was checked against the three captured
  exceptions and both error formats. Game logic was not changed by this review.
- **Right-click evidence:** `tests/mouse-checks.json` contains no destination
  change for its right-click step. Add explicit assertions for all three units
  accepting the order and reaching an unobstructed target. Test enemy and object
  targets separately before calling move/attack/interact verified.
- **Actions error and weak assertions:** `tests/actions-world/ErrorLog.txt`
  contains `Cannot get field "IgnoreList" from null` in `SendMSG`, reached from
  the MSG action. The action currently calls a verb needing recipient/message
  arguments without supplying them. Verify that UI path and cancellation.
  Some pickup checks do not recover the dropped quantity; test range, capacity
  and item restrictions with explicit expected outcomes. `goto|near_unit=0`
  alone is not proof of a camera bug: the probe compares the first unit, whereas
  the original Goto procedure iterates the selection and finishes on the last.
- **Onboarding mismatch:** a captured native Guide popup still describes the
  old double-click workflow, while the new Actions guide describes Remastered.
  Present one accurate onboarding flow and keep it from obscuring play.

No completion percentage is assigned. Long-session stability, all race
progression paths, complete physical input coverage, multiplayer and exact
visual/timing parity remain separate work.

## HUD opportunities

The inspected 1280-pixel captures devote roughly half the window to the Actions
list and scrolling log. Small edge icons require prior knowledge, and a player
must switch tabs to understand fullness, cold, fatigue, injuries or carrying
capacity. The new health bars are a useful start.

Fresh captures: [new army](tests/app-new_army.png) and
[reloaded army](tests/app-reload.png). These are game framebuffer captures;
separate native popup windows are not included.

| Priority | Change | What it should accomplish |
| --- | --- | --- |
| 1 | Selected-unit strip | Portraits, health, fullness, fatigue, cold, carry capacity and current order in one place. Multi-selection shows individual warnings and an aggregate summary. Keep detailed skills/body parts available on demand. |
| 2 | Contextual command grid | A short set of relevant commands with existing sprites, hotkeys, tooltips, costs and disabled reasons. Surface existing guard/patrol/build/craft actions before adding more verbs. |
| 3 | World overview | Minimap, cave-layer control, season/day indicator, selected-unit markers, attack and idle-unit buttons. Use labels/icons as well as color. |
| 4 | Feedback and layout | More space for the world, a compact collapsible log, readable scalable UI, clear target markers and reasons an action failed. Keep pixel-art scaling separate from text scaling. |

For a first HUD pass, combine the unit strip and command grid with the existing
mechanics. A player should be able to select a worker, understand its condition,
issue an order and see the result without switching tabs or opening a guide.

## Mechanics worth developing after the controls are reliable

| Opportunity | Existing foundation | Proposed extension |
| --- | --- | --- |
| More deliberate army control | Selection, control groups, stop, guard and patrol | Visible orders, Shift-queued destinations, clear stance controls and blocked-order feedback. |
| Manageable settlements | Resource pickup, building, workshops and crafting skills | Worker job priorities, stockpiles/hauling and production queues that report missing materials or unreachable work. |
| A clear opening goal | Food, campfires, seasons and cold | A short optional sequence: establish camp, secure food, make tools, prepare for winter, defend the settlement. |
| Attachment to units | Names, equipment, persistent skills and detailed injuries | Promote meaningful unit stories in the UI: veteran workers, injured defenders and leaders with visible roles. |
| Distinct races | Existing race-dependent stats and crafting | Explain each race's strengths and available actions in selection/build panels; expand progression after the current paths have been played through. |

## Suggested next acceptance checklist

- [ ] Combat cleanup and limb loss survive target deletion without runtime exceptions; verify with a focused reproduction and a bounded full-world run.
- [ ] Real mouse input asserts selection and orders; each intended right-click action has an observable outcome.
- [ ] Actions tests check outcomes and both runtime error formats, including prompt cancellation and missing recipients.
- [ ] One accurate Remastered onboarding flow replaces conflicting instructions.
- [ ] Unit strip displays real game state for one unit, a mixed group and a damaged unit.
- [ ] Command grid executes existing actions and explains availability, costs and failures.
- [ ] Minimap and layer controls keep the player oriented above and below ground.
- [ ] An end-to-end play session covers gathering, building, crafting, combat, saving and reloading with explicit checks of persistent unit state.

Classic should remain the compatibility reference. Remastered is the appropriate
place for these intentional interface and mechanics changes.
