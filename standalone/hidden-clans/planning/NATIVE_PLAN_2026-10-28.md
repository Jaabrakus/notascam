# Next native work: plan (2026-10-28)

The owner: "we should rewrtie movement and other high tick things into native C# right?", then "i think game wide", then "lets plan the next native c# right?".

## Done today

- Battle routes and gang-up (engine v13).
- Morale's look-round (engine v14).
- Battle orders pass: 462 → 300–340 ms per game second.
- Morale: 114 → 35 ms per game second.

## How each piece is chosen and built

1. **Time it from inside.** Each piece is timed in a measurement copy before anything is built. All numbers below are windowless runs on build 117, in ms per game second.
2. **Native code where the time is a loop doing one simple check many times** (scans, searches, counting). Game rules (jobs, yields, blows) stay in the game's script, because two copies of a rule drift apart. A rule-heavy piece is made cheaper in place, or only its inner loop goes native.
3. **Proof before landing.** Each native piece has a shadow mode that runs both versions and logs any difference, or a check that its results are identical. It needs 0 differences on a big run.
4. **Measure, then land.** Old and new run side by side, then it lands through the lander and the app is built.

## Where the time is

### Battle (500 v 500, attack box)

| Piece | ms | Notes |
|---|---:|---|
| Attack box re-pick (RemasterPoolNext: scores every foe in the box for each pick) | ~90 | A loop over up to 500 foes per pick: **native** |
| Each fighter's own attack checks (fog, throw, cast, capture, spear, jaws...) | ~110 | Rules, run every half second per fighter: **cheaper in place** (skip checks that can't apply) |
| Closing in (field routes) | ~85 | Native since v13 |
| Blows (the strike chain) | ~100–125 | The fight's own rules: leave |
| Walking (mostly blows by bumping) | ~210 | The moving part is small |

### Village (2,000 workers)

| Piece | ms | Notes |
|---|---:|---|
| Harvest bookkeeping on each blow (copies the tile's contents before, compares after; yields) | ~36 | The chop itself is only 12. **The before/after scan native**, the yield rules stay |
| Putting goods into the store (RemasterDepositTick, 0.09 ms a call) | ~33 | Per-item drop and accept checks: **cheaper in place** first |
| Begin a delivery (0.5 ms a call, 26 a second) | ~14 | Looks like a scan over stores or items: time inside, likely **native** |
| Pieces lying in the zone | ~13 | Scan of the zone: likely **native** |
| Stumps and saplings | ~12 | Time inside |
| Clear of the store | ~10 | Time inside |
| Finding a tree or rock | ~9 | Already bounded to a few looks |
| Closing in on the work | ~21 | Search is native; the rest is small |
| The step itself (~38 µs a move) | — | Engine waste fixed but worth 0–2%: staged, not landed |

## Order

| # | Piece | Where | Kind | Expected saving |
|---|---|---|---|---|
| 1 | Attack box re-pick | Battle | **Done 10-28 21:23 (engine v15, app 118):** the engine ranks the box, the game looks cheapest first | 91 → 17 |
| 2 | Harvest blow | Village | **Done 10-28 21:46 (engine v16, app 119):** the tile copy was cheap; the cost was the worked-tiles list's tidy, now native | blow 50.5 → 30.5 |
| 3 | Begin a delivery | Village | **Done 10-28 22:29 (engine v17, app 120):** the store-tile scan native, and the zone-cells cache by numbers (asked ~24,000 times a second) | store tile 26 → 18, zone cells 83 → 54 |
| 3b | Pieces lying in the zone | Village | **Timed 10-29 on build 123, left as it is:** 8.1 ms a game second in all (453 looks a second, 18 µs each, about 2 tiles and 5 pieces a look; haulers ask too). A native would save about 1% of the village (reports/polish-night-1026/loose-native) | — |
| 6 | **Item timers** (found 10-28) | Village, all play | **Done 10-28 22:48 (engine v18, app 121):** one engine timer for every lying item, same ticks, the 2006 rule unchanged | 40,000 items: 8.7% → 1.1% of a tick |
| 4 | Deposit into the store | Village | **Done 10-29 10:47 (app 124, in place, zone-of-cell):** timing inside showed the accept checks were 0.1 ms; over half was finding a target tile's store zone on every step of the walk, now kept per tile (115,560 checked, 0 differences) | deposit 37 → 19.5 |
| 5 | Fighters' attack checks | Battle | **Landed 10-29 17:10 (atk-guards, squad-split; not built yet):** timed small on build 124 (1–3 µs a check), then built anyway at the owner's "Build them anyway": each check's first test before the call, the realms' answers once a tick (RmAtkPairs), each attack tick 8–14% cheaper. Correction: the earlier "half the battle is under no label" was the profiler's stuck open-call count; only ~10% is unlabelled (battle-other) | 8–14% of the attack tick |

| 8 | Stump ticks (battle-other's ~15 ms) | Battle | **Done 10-29 (app 126, in place, death-look-once):** the stump tick is ~20 µs; the time was the deaths it causes (Death ~6 ms each, ~4 deaths a second). A dying unit rebuilt its look for every piece it dropped; now once. Mourning off while moods are off (owner 10-29 "Yes, skip it", app 127: a death 4.58 → 2.60 ms). Left: the body's picture (~1.5 ms) (reports/polish-night-1026/stump-ticks) | deaths 23.8 → 9.7 |
| 9 | 1000 v 1000 (owner 10-29: "lets fix that") | Battle | **Done 10-29 (engine v20 + gang-far, app 128):** in the real app the battle ran at ~30% of real time; the cost was attack ticks' route searches to foes deep in the other block (box picks over 12 tiles off, and back ranks past the field's 16 steps). The field reaches 40 (RM_FIELD_REACH) and box/attack-move fighters take it at any distance (reports/polish-night-1026/gang-far) | closing in 383 → 42 ms/s; 1000 v 1000 2.27 → 1.97 real s per game s |
| 7 | **The order hitch** (owner 10-28: "a freeze and then a speed up on orders") | All play | Measured (reports/polish-night-1026/gather-hitch): every order puts 40-90 ms of work into one tick; windowless it stays under the 100 ms tick (a first reading of 150-190 ms ticks was wrong). **Fixed 10-29 08:27 (app 122, smooth-moves):** the server kept up; the moves reached the page unevenly. Each unit now walks its new tiles from a short queue at its own pace: stops mid-walk -71%, rushes -80% in the real app. **Group route map done 10-29 10:12 (engine v19, app 123):** members share one map to the group's target, and units go round mountains, from what their player has explored (reports/polish-night-1026/group-routes) | the hitch itself |

**Total expected:**
- Battle: about 100–110 ms off ~850 per game second (~12%, about 10 ms a tick).
- Village: about 60–70 ms off ~500 (~13%).

These are estimates until each piece is timed from inside.

## Not planned

- **A native rewrite of a whole step or of the job board.** Every movement and job rule would exist twice. A step's own cost is ~38 µs, of which the engine's tile change is 9.
- **Blows.** They are the fight's rules.

## Next: the step (timed 10-29 at 1000 v 1000, reports/polish-night-1026/step-native)

A measurement engine timed every proc's own time in a 1000 v 1000. Procs' own time is about 1,060 ms a game second. A soldier's step is ~250 of it (~55 µs a step), and the "can a unit stand here?" checks round it are another ~170. Rules stay in the game script; only loops and lookups move into the engine, each with a shadow check.

| # | Piece | Today (ms a game second) | Change | Kind | Expected saving |
|---|---|---:|---|---|---:|
| S1 | The game's own walkable checks (RemasterWalkable, 44,000 a second, and its RmSideUnit and RmFliesOver calls) | ~170 | Call the engine's twin, rm_walkable, which already exists rule for rule (the route search's, RmWalk.cs); a shadow mode checks every answer | Game side only: no new engine | ~120–140 |
| S2 | The standard library's Move: the cross calls on everything on both tiles, all /atom's empty ones | ~68 | The staged quiet-move (reports/polish-night-1026/native-move: rm_cross_types; the game's Move leaves out loops no type uses). Battle tiles hold bodies, blood and gear, so it is worth more here than the village's 0–2% | Engine (renumber to v21) + game | ~30–45, to measure |
| S3 | Friends passing through on each step (Enter's clip part: RmSide, the tile's units, the route's end) | ~45 | One engine call for the clip check, the same side rule as rm_walkable | Engine + game | ~30–40 |
| S4 | get_dist, written in DM in the standard library (22,000 a second) | 19.8 | A native get_dist, the same maths | Engine | ~17 |
| S5 | Morale's look (native already, 87 µs a look) | 67.9 | Faster C#: count from the grid's cells once a look | Engine | ~30–40, to measure |
| S6 | Stepping off a friend's tile (each attack tick) | 24.2 | Its walkable checks go through S1; its first test cheaper | Game | ~10–15 |

**Done 10-29 17:59 (engine v21, app 130): S1 and the whole plain step** (the owner: "Native plain step", which took the place of S2 and S3): the walkable checks by the engine's twin, and a step onto a plain tile by the engine. Shadow modes: 0 differences in 1.0 M steps and 2.95 M checks. Paired 1000 v 1000: 1.29 -> 1.07 real s per game s, walking 511 -> 330 ms a game second (reports/polish-night-1026/step-native). Left: S4 get_dist, S5 morale's look, S6; then fewer thinking ticks for fighters with nothing new to decide, and morale by group.

**Measured 10-29 18:50, not landed: fewer thinking ticks** (the owner: "Fewer fighter ticks"). A fighting or waiting fighter's decision stood for about one pass of two (reports/polish-night-1026/fighter-ticks, patch staged). Fighting the foe beside it was exact (0 of 56,731 rested passes would have differed) but small; waiting fighters would have moved half a second sooner in 19-46% of rested passes. Paired: attack ticks 289 -> 269 ms a game second, 1.03 -> 1.05 real s per game s (battles drift; inside the noise). Since v21 a waiting tick is ~57 µs, so the lever is worth ~2%, not the ~15-20% it was sized at. Exact savings left: morale's look 63, foes beside a fighter ~37, the step 43, orange 31, the field's way 30 ms a game second.

**Done 10-29 19:06 (engine v22, app 131): S5 morale's look and the foes-beside look** (the owner: "Morale + foe look"). Morale's look keeps what it read of each unit until the unit's change counter moves (95.5% kept); the foes-beside look asks the engine whether anyone of that realm stands round the fighter first. Shadow 60,000 / 240,000 looks, 0 differences. Measurement engine: 63 -> 22 and 37 -> 17 ms a game second; paired 1.08 -> 1.05 real s per game s, 102 -> 91 ms a tick (reports/polish-night-1026/morale-foe). Left (fp3): the step 37, the walkable checks 27, the field's way 27, stepping off a friend's tile 25 plus most of orange's 22, S4 get_dist 19.

**Done 10-29 19:55 (engine v23, app 132): the step-off and the plain step** (the owner: "Step-off + step"). Kept reads of movables for the walk checks and steps (RmKept.cs), no dir write when a step doesn't turn the unit, the step-off's two looks by the engine. Shadow 1.46 M step-off looks, 1.06 M steps, 6.65 M walk checks, 0 differences. Measurement engine: the parts touched 161 -> 89 ms a game second (reports/polish-night-1026/step-off). Left (fp4): the move itself (SetLoc, ~3.4 µs a step), the field's way 19, get_dist 18, RmStepOffShared's own checks 16.

**Done 10-29 20:26 (engine v24, app 133): S4 get_dist** (the owner: "Field way + get_dist"): 18 -> 3 ms a game second, 512 argument pairs 0 differences. **The field's way measured, left as it was:** ~20 builds a second at ~0.85 ms; kept reads for its foe check saved nothing (fighting foes change between builds) and were taken out; only fewer or shared builds would cut it, and those move routes a little (reports/polish-night-1026/field-way). Biggest left (fp5): the step 26, morale's look 25, the attack tick's own checks 21, Move's DM chain 19, range() 18, the field's way 18, the step-off's own checks 18.

**Together:** about 240–290 ms of ~1,060, a quarter of a 1000 v 1000's server time. These are estimates from the measurement engine; each piece is measured again, old and new side by side, before landing.
