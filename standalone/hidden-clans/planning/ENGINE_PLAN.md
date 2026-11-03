# Engine plan: native work in the Remastered server runtime

Started 2026-10-24 (server-cost session), at the user's request: "make the plan for the engine modification, what
will yield best results for our desired outcome, run tests and make it built in good hierarchy".

**The outcome we want:** a server that never stalls, with as many fully active units per process as the MMO plan
needs (the board: "Toward 30,000 units", "Toward 1,000,000 player units"). The game's rules stay in DM. The engine
takes over only the few loops that are hot because the interpreter is slow at them, and every one keeps a DM fallback.

## Where server time goes (measured, `reports/server-cost/`)
At 200 units, all selected, a group move every 20 s, with a real client (`real-200b.md`, `astar-200-tick-profile.log`):

| part | ms per second | in the engine already? | engine helps? |
| --- | ---: | --- | --- |
| route search (`RemasterOrderPath`, A*) | ~157 (96 % of a group move's per-unit cost) | no, DM | **yes, most** |
| HUD model build (`RemasterUnitData` etc.) | ~85 | no, DM | no: it's game data. Fix is design: send changes only, page the selection |
| HUD encode and send (1.44 MB JSON twice a second) | ~45 | yes (`json_encode` is C#) | no: the size is the problem (same fix) |
| 3D things list (`Remaster3DThings`: `range()` + per-thing data) | 23–32 | the `range()` is | partly: a native "creatures in this square" query |
| position push every tick (`Remaster3DMovesPush`: `range(25)` = 2,601 turfs) | 11–16 | the `range()` is | **yes**: the same query, no turf list |
| exploring and fog marking (`view()` per unit, circles) | 18–35 | `view()` is | yes: native sight circles into the explored bits |
| NPC look-rounds (`oview(5)` per step) | 7–9 after active areas | `oview` is | yes: the same query |
| every creature's step, walk loop | ~35 | partly | no: game rules |

With nobody logged in, after the wall-walk fix and active areas, the whole world is ~8 ms of DM per 100 ms tick. So
the engine work is about armies and players, not the empty world.

**Tried and not worth it in DM:** a heap for the route search gave identical routes (6,248 searches, 0 differences)
but ran 7 % slower (`tests/rmpath_equiv.dm`). The interpreter's cost per list operation outweighs the better algorithm
at these sizes. That's the clearest sign that the gain is in native code.

## What goes native, in order of payoff
1. **Route search, `rm_path`** (phase A). The whole A* in C#: same expansion order, the same tie-break (the first
   lowest score in the order added), the same 512-expansion limit, partial routes, bounds, group pass lists. Expected
   **20–50x** on ~157 ms/s at 200 units (estimate), and a 203-unit order 340 → ~50 ms.
2. **Who is near, `rm_near`** (phase B). A 16-tile cell index of creatures, kept by the engine as they move (the
   movable's `loc` change already passes through the engine). Queries return the creatures in a square or circle without
   building turf lists. It feeds the moves push, the 3D things list, NPC target looks, the world sweeps
   (`RemasterTouchCreatures`, wing mending, rot), and later the active-areas map. Expected 5–10x on those parts.
3. **Sight, `rm_sight`** (phase B). Marking explored and fog circles into the per-player bitsets natively (Explore.dm,
   Fog.dm). Rock doesn't block sight in fog (circles), so it's a pure geometric fill.
4. **Time dilation** (phase C, small). The region slows its own clock smoothly when a tick runs over, instead of
   lurching (EVE Online's TiDi). Built on `RemasterClock.cs`, which already owns the game clock; clients get the factor.
5. **Region memory** (phase D, biggest MMO lever, biggest risk). 4 million turfs take ~3 GB because each is a full
   DM object. Compact turf storage, or layers made on first entry, is engine work on the object model itself. Plan
   only until phases A–C have proved the pipeline.

**Not native:** the HUD model and the 3D scene's per-thing data (game data: fixed by sending less, not computing faster),
units' rules and AI decisions (DM, so the rules stay one source of truth), the wall-walk pass (fixed in DM).

## Code layout
```
engine/
  clock/RemasterClock.cs        the game clock (exists)
  core/                         native procs any DM game could use (since U3, 2026-10-30; was native/)
    RmNative.cs                 binding: each native replaces the DM proc of the same name, only if the game declares it
    RmVer.cs, RmWatch.cs, ...   change counters, watched vars, packing, allocation, memory, get_dist, sleeping tiles
  game-botd/                    native procs that know Banners of the Deep's types, vars and rules
    RmPath.cs                   route search (phase A)
    RmWalk.cs                   walkability, mirrored rule for rule from Orders.dm RemasterWalkable (phase A)
    RmGrid.cs                   units by 16-tile cell (phase B)
    RmSight.cs                  foes near (phase B)
  server/OpenDreamRuntime.dll   the built runtime the app ships (tools/build_app.py copies it)
game/Code/Remastered/Native.dm  each native's DM declaration with its DM fallback body, the switches, shadow mode
tests/<native>_equiv.dm         old DM against native on the user's map, per native
tools/build_runtime.py          merges engine/core + engine/game-botd into the build and binds them (beside the clock patch)
tools/engine_boundary_audit.py  keeps engine/core free of the game's names (baseline: tools/engine_boundary_baseline.json)
```

## Rules for every native
- **Core or game (U3, 2026-10-30, `planning/SERVER_UPGRADES_PLAN_2026-10-30.md`):** a native goes in `engine/core/` only if
  any DM game could use it: no type paths, var names (other than DM's own), races, owner texts or rule numbers of
  this game. Everything else goes in `engine/game-botd/`. `python3 -I tools/engine_boundary_audit.py` must pass
  before a build is installed. It matches names only, so the review also asks "is this a rule?" A core native that
  needs a game's names takes them from the game (a table the game registers at boot), not from literals.
- **Same name, DM fallback:** the game declares `proc/rm_path(...)` in Native.dm with a DM body. The engine replaces
  it only if that name exists, so new game code runs on an old engine (DM body) and old game code on a new engine.
- **Switch and shadow mode:** `rm_native_path` picks native or DM. With `RM_PATH_VERIFY=1` both run and any difference
  is logged with its arguments. On by default only after zero differences over tens of thousands of real searches.
- **One rule, two copies, kept in step:** the DM procs a native mirrors carry a note naming the C# file, and shadow
  mode catches drift.
- **Never a crash for a missing var:** C# reads vars through the object's own lookup; any unexpected value means
  "fall back to DM for this call".
- **Restore point before each runtime build** (`restore-points/`), and test builds go to a scratch path. Only a checked
  build replaces `engine/server/OpenDreamRuntime.dll`, and the coordinator builds the app.

## Build and test pipeline
1. **Baseline:** rebuild the runtime unchanged from the in-repo sources (OpenDream `standalone/opendream` at 2e58532,
   RobustToolbox at af2a7d0, the build's expected commit) into a scratch path. Run the game's checks on it: compile,
   headless world profile, wall-walk, awake, route equivalence, a real-client run. They must match today's runtime.
2. **Phase A:** add RmNative + RmPath + RmWalk, rebuild, run `tests/rmpath_equiv.dm` with the native search as "new"
   (thousands of searches on the user's map, identical routes required), then shadow mode through a 200-unit
   real-client run, then measure. Hand the checked DLL to the coordinator.
3. **Phase B and on:** the same, per native.

## Status
- 08:1x: .NET 10 SDK 10.0.402 installed (the user's OK) in /private/tmp/dm-runtime-audit/sdk.
- 08:2x: phase A written, not built yet:
  - `engine/native/RmNative.cs` (binding, version, var helpers), `RmWalk.cs` (walkability), `RmPath.cs` (the search).
  - `tools/build_runtime.py`: `--native` (opt-in) copies them in and calls `RmNative.Register`; `--output` sends a test
    build to a scratch path.
  - `game/Code/Remastered/Native.dm`: the declarations with DM bodies, `RM_NATIVE_PATH` / `RM_PATH_VERIFY`, and the
    `RemasterOrderPath` wrapper. `Orders.dm`'s search is now `RemasterOrderPathDM`, its body unchanged.
  - With the switch off (the default) the game runs exactly the DM search, on any engine. game/ compiles.
- Baseline rebuild (unchanged, `--output` scratch) queued behind another session's run.
- 09:4x: **the new engine is the main engine** (the user: "no more current engine the new engine is the one now the
  main engine"). `engine/server/OpenDreamRuntime.dll` (sha f89f43a6…) = in-repo OpenDream 2e58532 + the Classic
  patches + the clock + engine/native. Route search proven: after the get_dist -1 fix, 18,792 random searches and 6,479
  on real 200-unit orders identical to DM; 22x per search; with 200 units ordered, order processing 79 → 11 ms/s.
  Native.dm uses it whenever the engine has it (`RM_NATIVE_PATH=0` turns it off); on an older engine the DM search runs.
  The engine before: `restore-points/engine-before-native-path-20261024/` (built from 5b186c2).
  `tools/build_runtime.py` now builds exactly this by default (in-repo sources, natives in, `--no-native` to leave
  them out, refuses if standalone/opendream isn't at 2e58532); a default rebuild matches the main engine name for name.
- 10:13: real client, 200 units, new main engine (`reports/server-cost/real-200-native.md`): DM per tick 49.0 → 38.3 ms,
  ticks over 100 ms 411 → 345, order processing 96 → 16 ms/s, 0 runtime errors, saves unchanged. What is left at 200 units
  is the HUD and 3D parts of the track (about 200 ms each run, every 5 ticks), not route search.
- 11:2x: **native version 2: friendly and allied units clip through each other** (the user: "allow units to go past but
  never on the same tile", "they can clip them no swap"). game/Code/Remastered/Clip.dm + RemasterWalkable's side list +
  RemasterOrderPathDM / engine RmPath: tiles holding only units of the mover's side (RmSide: its owner, a player's
  allies) are gone through but never ended on; siege engines and carts still block. Proven: 18,864 random searches
  (2,319 through a side unit) and 1,637 on real 200-unit orders, DM vs engine, 0 differences. Behaviour
  (tools/check_clip.py, tests/clip_check.dm): through friends in a one-tile corridor, an ally's unit, a doorway with
  friends in it; an enemy still blocks; those passed are never moved; no two stopped units of a side ever share a tile
  (a look-ahead before going into a friend's tile, and a step to an open tile if left on one). Groups arrive sooner:
  doorway 195 → 130 ticks, past a crowd of 30 195 → 140; the same 15 group orders needed 6,479 → 1,637 route searches.
  Main engine now sha256 f22da7b8; before: restore-points/before-clip-20261024/ (engine and the edited game files).

- 2026-10-28 19:45: **native version 13: the battle ways** (the owner: "have the world preplan the best routes so everyone
  can fight gangup", then "we should do it in native"). engine/native/RmField.cs: per side, foe realm and 32x32 chunk, a
  field of steps to the nearest free tile beside a standing foe, rebuilt at most every 5 ticks; Attack.dm RmGangUp walks
  it (and RmPoolNear for an attack box's next foe). 500 v 500 windowless: Approach 276 -> 83 ms a game second, ticks
  113 -> 99.5 ms, blows 465 -> 821 a second. Engine sha256 ad3bdd90; before: restore-points/before-engine-v13-field-20261028-194555.
  RM_FIELD=0 off. Details: reports/polish-night-1026/battle-ways/README.md.
- 2026-10-28 20:23: **native version 14: morale's look round** (the owner: "Yes, morale next"). engine/native/RmMorale.cs
  rm_morale_look: RmMoraleTick's counts (allies, foes, beside, a royal within 6) from the unit grid in one read; the game
  gives each tick's player verdicts (allied / war / peace). Shadow mode 155,000 looks, 0 differences. 500 v 500: morale
  103-114 -> 31-35 ms a game second. Engine sha256 9792e7b8; before: restore-points/before-engine-v14-morale-20261028-202332.
  RM_MORALE_NATIVE=0 off, RM_MORALE_VERIFY=1 shadow. Details: reports/polish-night-1026/morale-native/README.md.
- 2026-10-28 21:23: **native version 15: the attack box's next foe ranked** (the owner: "Yes, box re-pick").
  engine/native/RmPool.cs rm_pool_rank drops the gone and no-longer-hostile foes and ranks the rest by their lowest
  possible score; Formations.dm RmPoolWalk looks cheapest first and stops when none can win. Shadow 4,000+ picks, 0
  differences. 500 v 500: re-pick 91 -> 17 ms a game second, orders pass 337 -> 267. Engine sha256 2a2f4494; before:
  restore-points/before-engine-v15-pool-20261028-212341. RM_POOL_NATIVE=0 off, RM_POOL_VERIFY=1 shadow.
- 2026-10-28 21:46: **native version 16: the worked tiles' tidy** (the owner: "Yes, harvest next"). engine/native/RmWorked.cs
  rm_worked_tidy: Breaking.dm RemasterWorkTidy's loop (it ran ~175 times a game second over 400 entries in a 2,000-worker
  village). Shadow 53,200 tidies, 0 differences; same harvest. Harvest blow 50.5 -> 30.5 ms a game second, walking 129 -> 101.
  Engine sha256 16525c82; before: restore-points/before-engine-v16-worked-20261028-214649. RM_WORKED_NATIVE=0 off.
- 2026-10-28 22:29: **native version 17: a delivery's store tile** (the owner: "Yes, deliveries next"). engine/native/RmStore.cs
  rm_store_scan: one zone's cells in Jobs.dm RmJzStoreFor's loop (the crowd round each, carriers sent), plus Zones.dm
  RemasterZoneCells' cache compared by numbers, not a text key (asked ~24,000 times a game second). Shadow 8,400 tiles, 0
  differences. Store tile 26.4 -> 17.9 ms a game second, zone cells 82.7 -> 53.9. Engine sha256 142f5373; before:
  restore-points/before-engine-v17-store-20261028-222934. RM_STORE_NATIVE=0 off.
- 2026-10-28 22:48: **native version 18: one timer for every lying item** (the owner: "Yes, item timers").
  engine/native/RmDecay.cs: the 2006 DeleteItem countdown's later passes for all items in one timer on the same ticks;
  FoodRoles.dm atom/DeleteItem keeps the start and first pass, Native.dm RmDecayOver the 180 rule. decay_check.dm: logs
  identical to the 2006 loops over 210 s. 40,000 items lying: 8.7% -> 1.1% of a tick. Engine sha256 4d8766e6; before:
  restore-points/before-engine-v18-decay-20261028-224756. RM_DECAY_NATIVE=0 off.
- 2026-10-29 10:12: **native version 19: the route map** (the owner: "Yes, group routes", "we want them to go around the
  mountain", "we have to use fog of war and what they know"). engine/native/RmRoute.cs: a map spread from the goal (96
  tiles round, shared per player and goal for 5 s, from the explored memory when fog is on), read down for a whole way;
  RmWalk.cs IgnoreUnits. Asked only when the search finds no step nearer, past the unexplored, or for group members far
  from their slots; a way ends on a free goal tile. ridge_check.dm: 0 -> 100 of 100 round a 110-tile ridge; village even.
  Engine sha256 05dd9319; before: restore-points/before-engine-v19-route-20261029-101239. RM_ROUTE=0 off.
- 2026-10-29 17:59: **native version 21: the plain step** (the owner: "Native plain step"). engine/native/RmStep.cs:
  rm_step answers the ground's Enter chain rule for rule on a plain tile and moves the unit without the standard Move's
  no-op calls (Exit/Uncross/Exited/Uncrossed/Crossed: none in the game, checked at start); rm_walk is RemasterWalkable
  by the engine's RmWalk.cs with the types set once (rm_step_setup); RmWalk.SideUnit internal. Shadow modes: 320,000
  battle steps, 700,000 village steps, 2.95 M walkable checks, 0 differences. Paired 1000 v 1000: 1.29 -> 1.07 real s
  per game s, 127 -> 99.5 ms a tick. Engine sha256 2a4d6c61; before: restore-points/before-engine-v21-step-20261029-175944.
  RM_STEP_NATIVE=0 / RM_WALK_NATIVE=0 off.
- 2026-10-29 19:06: **native version 22: morale's look keeps its reads, and rm_foe_beside** (the owner: "Morale + foe
  look"). RmMorale.cs: what a look reads of a unit (HP, down flags, not-a-foe flags, IsRoyal, Owner) is kept until the
  unit's change counter (DreamObjectMovable.RmChanges, RmVer.cs) moves; 95.5% of reads kept in a 1000 v 1000. RmSight.cs
  rm_foe_beside: whether anyone of that realm stands round a fighter, so Attack.dm RmFoeBeside answers null at once.
  Shadow: 60,000 morale looks and 240,000 foe looks, 0 differences. Measurement engine: morale's look 63 -> 22 ms a game
  second (92 -> 31 us a look), the foe look 37 -> 17. Paired: 1.08 -> 1.05 real s per game s, 102 -> 91 ms a tick.
  Engine sha256 115addbf; before: restore-points/before-engine-v22-morale-foe-20261029-190611. RM_FOE_BESIDE=0 off.
- 2026-10-29 19:55: **native version 23: kept reads for the walk checks and steps, and the step-off's looks** (the owner:
  "Step-off + step"). RmKept.cs: movables' density, Flying, Wagon and Owner kept on the movable (DreamObjectMovable.RmKept,
  added by the VER patch in tools/build_runtime.py) while its RmChanges stands; RmWalk.cs reads a tile's icon_state once;
  RmStep.cs leaves dir when a step doesn't turn the unit, and adds rm_shares and rm_step_off_tile (Clip.dm
  RmStepOffShared's looks, orange's order). Shadow: 1.46 M step-off looks, 1.06 M steps, 6.65 M walk checks, 0
  differences. Measurement engine: rm_step 37 -> 24, rm_walk 27 -> 8, orange 22 -> 4, RmStepOffShared 25 -> 16 ms a game
  second (161 -> 89 for the parts touched). A native returning an existing object must IncRef it (the first try deleted
  a map tile). Engine sha256 f76824b2; before: restore-points/before-engine-v23-step-off-20261029-195520. RM_STEP_OFF=0 off.
- 2026-10-29 20:26: **native version 24: get_dist by the engine** (the owner: "Field way + get_dist"). RmDist.cs binds a
  get_dist line for line the standard library's when the game declares rm_get_dist_native: 18.1 -> 3.1 ms a game second
  (1.0 -> 0.2 us a call); 512 argument pairs, 0 differences. RmKept.cs check mode (RM_KEPT_VERIFY=1): 168 M kept reads,
  0 differences. The field's builds (~20 a second, ~0.85 ms each) were measured and kept reads tried for their foe check:
  no saving (the fighting foes change between builds), taken out. Engine sha256 c792d2f6; before:
  restore-points/before-engine-v24-get-dist-20261029-202644. RM_GET_DIST=0 off.
