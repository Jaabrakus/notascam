# Systems map: what runs when (the clean-up pass, 2026-10-25)

The user, 07:4x: "we need to do this accept". This is the clean-up pass. The game grew about a dozen separate
do-less-work systems and seven separate sight passes, each made by a different session. Each is right alone. Together
nobody could say what runs on a given tick, and they stack on the same ticks.

This is the one map. It is version 2 (10:3x), merged by the coordinator from the seven owners' entries:
`reports/{server-cost,world-look,rts-feel,formations,jobs,far-records,map-memory}/systems-map-entry.md`. The entries
have the detail (shares, seams, proofs); this file has the whole picture and the fold plan.

Costs at 200 units come from real-window runs of the user's world plus 200 Dwarves on today's builds (t3d-v10-after,
clientmem-after, user-200-select-test). Costs at 5,000 and 30,000 are arena before/after pairs on a loaded Mac.

## Part 1: the tick

A tick is 100 ms (10 a second at speed 1). Same-tick wake order isn't fixed, except where noted.

| What runs | Where (owner) | How often | Capped? |
|---|---|---|---|
| Moving units' walk loops | WalkLoop.dm (server-cost) | a step apart (each unit's delay) | no |
| Parked walk loops' sweep | WalkLoop.dm RmWalkParkSweep | every 4 ticks, only while something is parked | no (looks at the parked list only) |
| Wild creatures' loops (wander, guard, look round, way home) | Monster AI.dm, WildClock.dm (rts-feel) | own periods; in asleep land on the unit clock | no |
| Each player's track: orders, settlement, explore, HUD, 3D scene, fog, care, bags, builders, skills | QoL.dm RemasterTrack, Spread.dm | starts every 5 ticks | 30 ms a tick for all players (RM_TRACK_SLICE), **except the settlement pass** |
| ...the settlement pass and worker steps | Settlement.dm, Jobs.dm (jobs) | each track run | **NO: one block.** 200 workers ~18 ms a call; 2,000 workers ~0.7 s, worst 2.4 s |
| ...the 3D scene | View3D.dm (world-look) | each track run; terrain every 6th | 10 ms of the slice (rm3d_slice), 30 ms while new ground or pictures build (rm3d_slice_build); safe points inside chunks since 10-25 |
| ...fog (side sight) | Fog.dm (world-look) | on the 3D tick; a side reused for one track period | no |
| ...explored map | Explore.dm (world-look) | every 4th track run (~2 s) | no (B1, approved: with fog on, its per-unit view(5) goes) |
| The 3D moves push | View3D.dm (rts-feel's entry) | **every tick** per connected player | **no**: 2.8 ms median, 5.1 p90, one 84 ms at 200 units |
| The unit clock's ring: hunger, tiredness, bleeding, healing, bed, regen | UnitClock.dm (server-cost) | every tick, after the procs woken that tick | no (each body runs waitfor 0) |
| A click's first steps | Formations.dm RmFirstTick, RmFirstLater (formations, server-cost) | the click's tick, then later batches | 8 ms (x2 charge), later 25 ms a tick |
| Big orders handed out | Orders.dm (formations, candidate 5) | ticks after a click of > 200 units | 8 ms in the click's tick, then 25 ms a tick |
| Awake land redrawn | Awake.dm (server-cost) | every second; workshops every 30 s | no |
| Tile sleep sweep | Regions.dm (map-memory, v10) | every tick, 64 chunks | yes: stops once world.tick_usage passes 60% |
| Far records' loop | FarRecords.dm (far-records) | every 20 ticks; sleep sweep every 3rd | 10% of a tick, batches of 100 (**OFF**: rm_far_on = 0) |
| Shed level | Shed.dm (server-cost) | every tick (last 30 ticks) | n/a |
| Door loop | Jobs.dm RmDoorLoop (jobs) | on demand while a door is opening | no |
| Engine GC | engine/gc | between ticks | its own pause |
| ~~Stat panel~~ | ~~1 - Stat Proc.dm via OpenDream UpdateStat~~ | ~~every tick~~ | removed 10-25 (the 19 GB client) |

**Where hitches come from:** each capped part caps only itself. Nothing caps a tick as a whole. And two big parts are
uncapped: the settlement pass (the biggest single block at 2,000 workers) and the 3D moves push (every tick). Measured
over today's six 200-unit profiles (world-look, ONE_SIGHT_GRID.md):

| | slow ticks (over 100 ms) |
|---|---:|
| all | 277 |
| nothing named over 20 ms (unattributed DM, GC, the Mac) | 125 |
| the 3D view alone (mostly new ground: fixed 10-25) | 105 |
| unit looks alone | 18 |
| two or more systems together (stacking) | 19 (7%) |

Since then the stat panel fix took "other DM" at 200 units from 447 to 25 ms a second, and the map-load fix took
terrain-led slow ticks from 4 to 0.

## Part 2: the do-less-work systems

| # | System | Owner | What it skips | Cost / saving (200 units unless said) | Switch, DM twin | In the app since |
|---|---|---|---|---|---|---|
| 1 | Unit clock (+ bed skip) | server-cost | six sleeping procs a unit; rested units' bed checks | 30k standing 174.9 → 139.0 ms (bed skip) | none | 10-24 / 10-25 03:0x |
| 2 | Wild clock + far tier | rts-feel | wild loops' procs in asleep land | far from players about half | rm_wild_far_think | 10-24 |
| 3 | Parked walk loops (walk v2e) | server-cost | idle units' look every tick | 5k standing cpu 122% → 58%; 30k 1,158% → 372% | none | 10-25 00:5x |
| 4 | Spread track passes | server-cost | one-tick stalls (same work, spread) | 30k worst track tick 2.8 → 0.16 s | none | 10-24 / 10-25 03:2x |
| 5 | First-step budget | formations, server-cost | first steps beyond 8 ms of the click's tick | group of 30 mean first step 0.86 → 0.09 ticks | defines (WL_NOBUDGET in tests) | 10-24 / 10-25 03:55 |
| 6 | Big orders over ticks | formations | handing out > 200 units' orders in one tick | 5k click 208 → ~92 ms (with v8 natives) | defines | 10-25 02:5x |
| 7 | 3D budget + safe points | world-look | 3D work beyond its share | new mountain 117 → 43 ms a tick | rm3d_slice, rm3d_slice_build | 10-24 / 10-25 10:0x |
| 8 | Shed (step back when behind) | server-cost (reads: hud-craft, world-look) | cosmetic HUD and 3D tiers | up to 2/3 of those parts at level 2 | read only | 10-24 |
| 9 | Sleeping land | server-cost | resting wild creatures' looks | in "other DM" | rm_asleep_nap | 10-24 |
| 10 | Sleeping tiles (v10) | map-memory | full turf objects for quiet land | full world 1,843 → 937 MB | RM_REGIONS=0, RM_COMPACT_TILES=0 | 10-25 09:3x |
| 11 | Far records | far-records | whole mobs for offline players' far units | 1,000 records live 8 h in 308 s | rm_far_on (OFF) | in game, off |
| 12 | Change-driven passes (skills, orders) | server-cost | units with nothing changed | skills 3.7 ms/s; 5k orders pass 36 → 24 ms | none | 10-24 |
| 13 | 3D entry reuse, stage 2 | world-look | rebuilding or resending unchanged things | scene 21 → 13 → 6 ms; 30k 1.9 → 0.5 s | RM_3D_REUSE, RM_3D_DELTAS, RM_VER_VERIFY | 10-24 / 10-25 07:36 |
| 14 | Attack-look pre-check (rm_foe_near) | server-cost, rts-feel | oview scans that find nobody | 5k war 126 → 104 ms; wild near players 37 → 24 ms a tick | native, DM fallback | 10-25 07:2x |
| 15 | Settlement slices | jobs | stepping every worker every call | each worker steps every 0.5-2 s | none | 10-24 |
| 16 | Lodges' 5 s count, job allocator's 2 s period | jobs | per-tick checks | under 1-7 ms/s | none | 10-24 |

## Part 3: the sight passes

| Pass | Asks | Where | After the user's decisions (10-25) |
|---|---|---|---|
| Unit looks | is a target near this unit | Monster AI.dm, Attack.dm | keep rm_foe_near (exact, ~1 µs); later it reads the engine grid (B2) |
| Fog | what my side's units see | Fog.dm | the who-sees answer; underground marks only by line of sight (approved) |
| Awake land | which chunks are near a camera, unit or workshop | Awake.dm | keeps its own radii (32 round units vs sight 12-18); later "near units" reads the grid |
| 3D scene things | what my camera shows, filtered by fog | View3D.dm | reads fog; later the grid |
| 3D moves push | which units in my window moved | View3D.dm | the grid's first big reader: range(25) 3.25 → 0.1 ms a tick (B3) |
| Explored map | what my side has seen | Explore.dm, Fog.dm | B1 approved: with fog on, the per-unit view(5) goes (200 units 13 → 0 ms/s; 5,000 280 → 3) |
| Far view figures | units far off | View3D.dm | approved: shows the side's fog sight instead of view(7) per far unit (B4) |

Plan and proofs: `planning/ONE_SIGHT_GRID.md`. Order: B1 (+ underground line of sight) now; B2 the engine grid as v12
right after v11; then B3, B4; B5 (awake reads the grid) optional.

## Part 4: two copies of the hot loops

Engine natives with a DM twin of the same name (Native.dm), each switchable:

| Native | Installed | Run in the app with 0 differences since |
|---|---|---|
| rm_path, rm_walkable (route search) | v2, 10-24 | 10-24 |
| rm_slot_* (formation slots) | v4, 10-24 | 10-24 |
| rm_pack (HUD packing) | v5, 10-24 | 10-24 |
| counters (rm_ver, rm_chunk_ver) | v6e, 10-24 | 10-24 23:53 |
| rm_foe_near | v7f, 10-25 | 10-25 06:50 |
| own-door rule | v7f, 10-25 | 10-25 06:50 |
| plan loops (7 natives) | v8c, 10-25 | 10-25 07:36 |
| sleeping tiles (6) | v10, 10-25 | 10-25 09:3x |

**Rule for removing a twin:** a native's DM twin may go after it has run in the app for 7 days with no difference
logged, AND its shadow check still passes. The twin then moves into tests/ as the reference and leaves the game. First
candidates: rm_path, slots and rm_pack (10-31).

## Part 5: restore points

DONE 10-25 10:5x (the user: "we can do number 8 now"): 47 folders older than 10-24 (4.9 GB) moved to
~/.Trash/restore-points-before-20261024-coordinator/ (the space comes back when the user empties the Trash). Kept: everything
from 10-24 and 10-25 (the baseline, the engine rollbacks) and 7 older folders that hold save backups
(player-units; one is tools/check_recovery_save.py's fixture). restore-points/ is now 74 folders, 1.0 GB.

## Part 6: the fold plan (for the user)

From the owners' entries; server-cost's §3 and world-look's proposal are the core.

1. **One tick ledger.** The track slice, a click's first steps, the order hand-out and the 3D budget each keep their own
   ms count today. They move to one `rm_tick_used` with ONE cap per tick. Orders and first steps come first, then the
   track (HUD and 3D), then everything optional. This is the only fold that goes straight at stacking.
   Risk: a big click's first steps take more ticks when a track run is heavy. Proof: walk latency unit by unit, as for
   walk v2e.
2. **Cap the two uncapped blocks.**
   - The settlement pass: each worker's step becomes a unit-clock job (jobs' proposal). Each worker steps every
     0.5-2 s from the ring, so the cost spreads with no new budget. "High first" reservations become standing ones.
   - The 3D moves push reads the grid (B3) and joins the ledger.
3. **The ring takes the world's timers.** These become jobs on the one unit clock instead of their own loops:
   - the parked sweep;
   - the awake redraw;
   - the far records' loop;
   - RmDoorLoop;
   - the lodges' count and the job allocator's 2 s period;
   - the wild clock's asleep-land part.
   Shed stays its own loop, since it must measure at the start of a tick.
4. **The grid takes the "near a player's unit" questions** (v12, B2-B5): rm_foe_near, awake land, the 3D moves push, fog's
   "sees".
5. **One "behind" signal.** Every do-less part reads Shed's level; no part keeps its own load guess (Regions.dm's 60%
   tick_usage check becomes a shed read).
6. **Remove proven twins and switches** by Part 4's rule. Restore points pruned by Part 5.

Order, the USER's choice (10-25 10:3x, "B", hitches first): B1 (landed 10:26), then the ledger (1) and the settlement step (2) (server-cost and jobs, at the same time), then v11 chat, then v12 grid (B2-B4), then the ring (3), then 5 and 6.
Each step is its own landing: a restore point, the coordinator's OK, the owners' gates, and an app build.
