# Navigation plan: should the map keep the ways? (nav-plan, 10-27)

The owner asked whether routing lag should be "done by the world map instead". It mostly should. The full plan is in
`planning/NAVIGATION_PLAN_2026-10-27.md`. This was plan only: no code, no runs, no builds.

## Done
- Read today's route code (engine RmPath/RmWalk, the DM search, the mountain search, the walk loop, clip, Bump,
  attacks, group moves, zone reach) and today's measurements.
- Wrote the plan:
  - **N0 Count first** (exact): count searches by caller and outcome.
  - **N2 Chasers keep their route** (the pending call).
  - **N1 Reach map** per 16x16 chunk.
  - **N1b Mountain search in the engine** (exact).
  - **N3 Shared ways** (flow fields).
  - **N4 Long trips.**
  Each has what players see, memory, cost per map change, size and proof.

## Numbers the plan rests on
| What | Value | Source |
|---|---:|---|
| route searches in a 250 v 250 fight | 338 ms per game second | devlog/2026-10-27/combat-speed.md |
| attack ticks + their searches in that fight | ~800 of ~1,100 ms a game second | same |
| rerouting in a 1,000 blob | 1,522 µs per unit per game second | reports/server-cost/next-speed-list.md |
| search limit, ground / mountain | 512 / 768 tiles taken | RmPath.cs, Gather.dm |
| retry with no way: orders / attacks | every 3 s / every tick | Orders.dm, Attack.dm |
| reach map memory (estimate) | ~12-16 MB for today's world | plan section 4.4 |

## Second pass: ways it could break
The owner: "polish the plan look at ways it could break". I re-read the code the plan leans on and found these,
each now with a guard in the plan's section 7:
- **Clipping needs a route list.** `Chains/Enter.dm` lets a unit into a friend's tile only when its route goes on to
  an open tile within 12. A unit walking a shared way with no route list would jam: the old "100 frozen carriers" bug.
  Guard: field walkers keep their next 13 steps as a route.
- **Heights are cached the first time they're read** (`Breaking.dm` RemasterBlocksAt) and depend on rock up to 5
  tiles away. Guard: the map computes heights and never writes them, and rock changes mark chunks within 5 tiles.
- **Things that move must never count as map changes:** beast feet move every step, and clipping flips friends'
  density on every step. Guard: only fixed things count.
- **Door state changes nothing in the map,** so units waiting on a "no" could miss a door opening. Guard: door changes
  wake them.
- **Safety net:** a unit told "no" still checks with today's search every 30 s, and a wrong "no" is logged.
- Changed: N1 now has three stages (flat layers, then the Sky layer after N1b proves the mountain rules, then the rule
  changes). B3 (nearest reachable point) is now "not now", because an island goal could send units on a long detour.

## Third pass: other things I noticed
These need no reach map and change nothing a unit does (plan section 12):
- **E1.** Every walking unit's next-step check still runs in DM (35 places). Each one copies the tile's whole list of
  things, every stone on a store tile included. The engine already has the same check, proven by the tests, but the
  game doesn't use it.
- **E2.** The engine's search re-reads the walking unit's own details on every tile it looks at, and builds new
  tables for every search. Both can be done once, with the same answers.
- **E3.** Every search on the Sky layer runs in DM. Flyers, climbers and units on wall walks get the plain search
  there, which the engine already copies exactly.
- **H.** Every new tile under a player's mouse runs up to 6 route searches, or 25-tile stairs scans, for the selected
  units. In multiplayer, every mouse costs server time.

## Staged: E1, E3 and the N0 counters
The owner said to prewrite them, with no landing and no runs. They are in `reports/polish-night-1026/nav-plan/staged/`:
- **N0:** with `RM_NAV_COUNT=1`, every route search is counted by who asked and how it ended, plus walk and hover
  checks. It is off in play.
- **E1:** the step check asks the engine's proven copy of its rule first.
- **E3:** flyers, climbers and wall-walk units on the Sky layer get the engine's route search.

None of them changes what a unit does. They are written but not compiled or run. Their anchors match today's game,
and all six landing orders give the same files. The lead has been told they fit the hot-loop audit after build 69.

## Needs the owner
- The 10 questions in the plan's section 10, each with a recommended answer. The first one to answer is the pending
  chaser call (Q5).

## The reach map is in (N1 stage 1, landed 20:11)
The owner said "ah okay do it if its hopeful". The map now knows which ground connects, on the ground, underground and
hell levels. A search that can't succeed is answered at once: the hover check, a group's free-tile check, defence.
The rule it keeps: the map may only ever be too hopeful. Its "no" is always a true "no".

- **Built:**
  - engine v12 (`engine/native/RmReach.cs`, the change hooks in RmVer.cs, native version 12);
  - game side "nav-reach-map" (Native.dm, Chains/WorldNew.dm, Regions.dm).
  Work, proofs and tools are in `reports/polish-night-1026/nav-reach/`.
- **A real bug found and fixed before landing:**
  - OpenDream gives a replaced turf its new look only after the change hook runs.
  - A chasm, holy-ground or stairs tile turned into grass stayed blocked in the map: a wrong "no" in the making.
  - Now the hooks only mark a tile, and the map reads marked tiles again before its next answer.
- **Safety net:** 1 in 32 "no" answers is still searched, and every partial search that finds the whole way asks the
  map too. A wrong "no" would log `RMREACH|wrong-no` and turn the map off.

| Proof | Result |
|---|---|
| arena (levels 1, 2, 4; rock, walls, chasm, holy ground, stairs, 1,200 random edits, replaced bands), 6 runs | 64,800 map-vs-search pairs: wrong "no" 0; the wrapper's answers equal the search's (0 differences); kept map = fresh read in every audit |
| shadow runs, every "no" searched as well | walk latency pass, clip 11/11, 250 v 250 (180 s): wrong "no" 0, no errors |
| 2,000 workers at speed 32, base vs fix side by side | 333.8 vs 324.1 ms CPU a tick (no cost); the same work |
| landing gate | 11 of 11 checks pass |
| map in the 300x260 arena | built in 107 ms, 0.8 MB; a fresh labelling 2 ms |

**No speed gain in the worker scene, by design:** everything there is reachable, and stage 1 only cuts searches that
can't succeed. The gains come with the next steps, which need the owner: N2 (chasers), N3 (shared ways), B2 (units
with no way stop searching every 3 s).

## Chasers search less (idea 1 + N2), polished, waiting for the owner (10-27 evening)
In a big fight the server's heaviest job is units searching for a way to the foe they chase. The prewritten patch
(`reports/polish-night-1026/nav-plan/staged/chase-queue/`) cuts those searches: a unit whose foe is surrounded waits
near it instead of searching every pass, a foe that moved a step only has the route's end re-aimed, and a blocked step
is walked round. It went through five rounds of polish against 250 v 250 battles.

- **First rounds:** fights changed. Units held back behind a surrounded foe struck a quarter fewer blows; the budget and
  the shorter search made the first minute half as bloody. Those two parts are now off by default.
- **Two measuring traps, both fixed in how we test:**
  - The battle test's "dead" was always 0: units that bleed out are deleted, and its count skipped deleted units. Its
    "fallen" was only those still dying at the end. The combat team's battle test counts the same way.
  - Base and fix were run beside different neighbours. Each player's orders are spread over ticks by real time, so a
    busier machine makes a fight run slower in game time. Run side by side on the same seed, the gap disappeared.
- **Result, six seeds side by side:** fights match (out of the fight at 60 s 98 against 96, at 140 s 272 against 261;
  hits, limbs and the dying within noise). The route searches it targets take 57% less time; the whole orders pass 28%
  less.

It changes when chasers look for a way, so it waits for the owner's OK before it lands.

## Minimum spec and memory (10-27 night)
- **Minimum spec, from the current build:** macOS 15 or newer; Intel or Apple silicon (the game's engine is Intel code
  and runs through Rosetta 2 on Apple silicon); about 300 MB of disk. Only ever tested on a Mac mini M4 with 16 GB.
- **Memory today:** the game uses about 2.5-3.3 GB playing alone (server 1.3-1.6 GB, window 0.7 GB, 3D view
  0.5-1.1 GB), so 8 GB is the practical minimum. The owner wants it near 1 GB.
- **The server's slow climb is real data**, not spare room: with 200 units moving, after its free gaps fill it grows
  about 22 MB a minute. Whether it levels off is the next check (left for later by the owner).
