# Navigation plan: the map keeps the ways, units read them (2026-10-27)

The owner asked on 10-27 whether movement and routing lag that builds up over play should be "done by the world map
instead". This is the answer and the plan. It is a plan only: nothing in `game/`, `engine/` or `art/` has changed, and
nothing was built or run. The feature freeze holds, so everything here lands after it, and after the hot-loop audit
that follows build 69. The owner already set that order on 10-26: "the biggest cost is unit rerouting we will fix
this later make sure all the smaller ones are done first" (`reports/server-cost/next-speed-list.md`).

Second pass (10-27, the owner: "polish the plan look at ways it could break"):
- Section 7 lists every way found that this could break, what a player would see, and what stops it.
- The design sections now carry those fixes.
- Sizes and the order were corrected.
- The recommendation on B3 changed to "not now".

Sizes: **S** is about one session-day with its proof, **M** is 2-4 days, **L** is a week or more, landed in stages.

## The short answer

Yes, mostly. The map should keep what it knows about the ground for everyone:
- which places connect to which;
- a ready "way to here" for goals many units share;
- a coarse map for long trips.

Each unit then does only the last few tiles itself. Those tiles are where other units, friends' tiles, doors and
formation slots matter. The map can't keep those, because units move every tick. Strong games split it the same way
(section 3).

What we would gain:
- "No way there" is answered at once. Today it takes a 512-tile search that fails, and that search comes back every
  3 seconds, or on every attack tick for a chaser.
- Chasing units stop searching from scratch each time their foe takes a step. That is the biggest measured cost:
  338 ms of every game second at 250 v 250.
- The 2,000 workers stop making their own searches to the same few stores, yards and zones.
- Long trips stop running out of search and getting stuck in dead ends. That matters more as the world grows.

**The one rule that keeps it safe:** the map may only ever be too hopeful. It calls a place blocked only when today's
search would call it blocked for that mover too; anything it isn't sure of counts as open. So a "no" from the map is
always a true "no", and any mistake in the other direction costs one ordinary search, which is what happens today.
Behind that rule there is a safety net (section 4.5): a unit told "no" still checks with today's search now and then,
and a wrong "no" is logged and fixed.

### Ranked recommendation

| # | Step | What players see | Size | Exact, or a named rule change | When |
|---|---|---|---|---|---|
| 1 | **N0 Count first**: count every route search by who asked and how it ended, plus hover checks and per-step walk checks | nothing | S | exact (counters only) | with the hot-loop audit's labels, if the lead agrees |
| 1b | **E1-E3 Exact wins found on the way** (section 12): per-step walk checks in the engine; a cheaper engine search; the engine search for flyers, climbers and wall walks on the Sky layer | nothing | S each | exact, proven by today's fixtures | prewritten now, landed first after the freeze, if N0 shows they pay |
| 2 | **N2 Chasers keep their route** (the call already waiting on the owner) | chasers turn a step later sometimes; an attack-move fighter whose foe is full picks another foe | S-M | rule change, B6 | first after the freeze |
| 3 | **N1 stage 1, the reach map on flat layers** (ground, underground, hell) | nothing (exact uses first) | M | exact | next |
| 4 | **N1b The mountain search in the engine** (today DM-only up on the rock) | nothing | M | exact, proven like rm_path | before N1 stage 2: it proves the C# copy of the mountain rules first |
| 5 | **N1 stage 2, the Sky layer and links between layers** | nothing (exact uses) | M | exact | after N1b |
| 6 | **N1 stage 3, the rule changes the owner picks** (B1, B2, B4, B5) | "can't get there" at once; stuck units stop re-searching; zones and stairs know what's reachable | S each | rule changes | after stage 2 |
| 7 | **N3 Shared ways** (flow fields) to stores, yards, zones and enemy groups | the same routes in length; different tiles among equal ones | L | rule change, B7-B8 | after N1 |
| 8 | **N4 Long trips** (a corridor over the area map, then region to region) | long walks go round lakes and ranges and never stall in a bay | M, then L | rule change, B9 | step 1 after N3; step 2 with the Daggerfall regions |

Group moves stay as they are while formations are on hold (B10).

The questions only the owner can answer are in section 10. Each one has a recommended answer.

## 1. How a unit finds its way today

What follows is what the code does, read on 10-27.

- **One search per unit per need.** `RemasterOrderPath` (`game/Code/Remastered/Native.dm:45`) calls the engine's
  `rm_path` (`engine/native/RmPath.cs`). That search works like this:
  - it is A* on the unit's own layer only, eight directions, with every step (diagonals too) costing 1;
  - the distance guess is the game's `get_dist` in x and y (-1 on the same tile; the layer isn't counted);
  - ties go to the tile found first;
  - it stops after **512 tiles taken**.
  - With `partial`, a failed search still returns a route to the closest tile it saw. `rm_path_partial` then says
    "part of a long way" (1) or "no way through" (2).
  - The DM copy (`Orders.dm:784` RemasterOrderPathDM) is the fallback and the reference. It is proven identical and
    22x slower.
- **Up on the rock it's DM only.** On the Sky layer, the native search is skipped (`Native.dm:47`).
  `RemasterLevelPathDM` (`Gather.dm:553`) searches by place: a tile plus the height a unit stands at there. It has
  these rules:
  - up one block only by a ramp;
  - a free hop down one;
  - no diagonal round a rock corner;
  - it stops at 768 tiles;
  - every node key is a text string.
  Climbers use the flat search up there.
- **A column's height is worked out the first time it is read, and stored then** (`Breaking.dm:164`
  RemasterBlocksAt). It depends on rock up to 5 tiles round it, plus a hash, and isn't saved unless the column was
  dug, carved or built. Reading a ramp whose block is gone clears it (`Gather.dm` RemasterSlopeOn). So some reads
  write.
- **Walkable depends on the mover** (`RmWalk.cs` / `Orders.dm:756` RemasterWalkable):
  - A flying unit goes over anything, but only on the ground and Sky layers. Underground and in hell it walks like
    anyone.
  - Chasm and open-sky tiles stop dense walkers.
  - Holy ground ("GoodGrass") stops the undead, unholy, infecting, Svartalfar and Demons.
  - Stairs only count as the goal. Wall walks hold two units a tile.
  - Dense things block, with exceptions that are passed: the unit's own feet, its group's walking members,
    its owner's unlocked doors, and units of its side (2: through, never stopped on).
  - Enemies, wild creatures, siege engines, carts and other beasts' feet block.
- **Changing level is not in the search.** An order to another layer becomes a Climb, Hop or Scale order first
  (`Orders.dm:552-589`). That order picks stairs by straight distance within 25 tiles (`WallWalks.dm:346`
  RemasterStairsTowards). If they lead nowhere, it tries other stairs after 10 s stuck (`RemasterStairsElsewhere`).
- **Who searches:**
  - Orders (`RemasterApproach`, `Orders.dm:841`): a search that found no way is retried every 3 s. A unit stuck for
    10 s searches again.
  - Attacks (`Attack.dm:111` RemasterAttackApproach):
    - they search again **whenever the foe's tile changes**, or whenever the route is empty;
    - nothing slows the retry;
    - every search there is partial.
  - Group moves (`Formations.dm:1076`): a compact group shares its lead's route, moved over. Big groups get 16
    searches a tick; the rest step straight.
  - Building sites read "no way" from `rm_path_partial` right after their search (`Blueprints.dm:289`).
  - Others: defence (bounded), and the hover check (`HoverCheck.dm:55`: a search on hover). Jobs go through orders.
- **Clipping needs a route list.** A unit may step into a friend's tile only when its route, read by `RmRouteInto`,
  goes on to an open tile within 12 (`Chains/Enter.dm:35-37`). While it steps through, the friends are made
  non-dense for that moment (`Chains/Enter.dm:38`).
- **Some connectivity already exists, built separately for each use:**
  - the zone reach fill (`Jobs.dm:260` RmJzFill: ~10 ms a 25x25 zone in DM, density only, run only after a worker
    failed);
  - the attack-move floods (`Formations.dm` rm_reach, RemasterRoomAt);
  - per-unit skip lists (`rm_jz_skip`);
  - "other stairs" retries.
- **The engine already sees map changes in 16x16 chunks:**
  - `RmVer.cs` counts every turf var write and turf swap per chunk;
  - `RmGrid.cs` keeps units in 16x16 cells;
  - Awake.dm, WorldSave.dm and the sleeping tiles (`RmTiles.cs`) all use the same chunks.
  The map is 4 layers of 1000x1000: 63x63 = 3,969 chunks a layer, 15,876 in all.

## 2. What it costs, and why it grows

- **Battles.** At 250 v 250 (`devlog/2026-10-27/combat-speed.md`):
  - approaching the foe (route searches) takes **338 ms per game second**;
  - the first-step batch after each attack order is most of another ~494 ms;
  - together, attack ticks and their searches are about 800 of the ~1,100 ms a game second takes.
  - In a 1,000 blob, rerouting cost 1,522 µs per unit per game second (`next-speed-list.md`).
- **Why chasers are dear:**
  - A foe in melee steps often, so `K.path_goal != goal` is true on most attack ticks.
  - A foe already ringed by others has no free tile beside it, so the search can't succeed. It takes all 512 tiles
    exploring the crowd, returns "as close as it gets", and does it again next tick.
  - N0 will count how many searches end that way.
- **No-way loops.** An order with no way searches the full 512 every 3 s until it gives up (30-60 s). A zone job
  searches for 15 s before it gives up on a target. With hundreds of workers on a half-walled wood, or an army sent
  across a river, that is steady load that does nothing.
- **Long trips.**
  - 512 tiles taken covers a few hundred tiles of open ground. Round a lake or a mountain range it can run out.
  - The unit then walks to the closest tile it saw. If that's a bay with no way on, it stays stuck until the 3-second
    retries happen to find more.
  - On a Daggerfall-scale world, with trips of thousands of tiles, today's search can't plan the trip at all.
- **Scale.** Every one of these costs grows with the number of units: one search each, again and again. Shared ways
  grow with the number of goals, which is far smaller.

## 3. How strong games do it, and what we take

- **RimWorld.**
  - **What it does:** it splits the map into small regions, flood-filled inside 12x12 blocks. Each door is a region
    of its own. Regions connect by links on their edges. A cache answers "can this pawn reach there?" from region to
    region, with the pawn's rules (doors, faction). A map edit marks only nearby regions dirty. The tile search still
    runs per pawn, after reachability says yes.
  - **What we take:** regions per 16x16 chunk, doors as their own region (our own-door rule fits exactly), dirty
    marking per chunk, and "reach first, search second".
- **Dwarf Fortress.**
  - **What it does:** it keeps a connected-area number for every walkable tile and checks it before any path search,
    so impossible jobs are refused at once. Walls that split a big area force a costly renumbering. That is the known
    trap.
  - **What we take:** the instant "no way" answer, plus renumbering only the area that split, and only when asked.
- **Supreme Commander 2 and Planetary Annihilation.**
  - **What they do:** flow fields. A flow field is a map of arrows pointing toward one goal. SupCom 2 builds them
    only for the sectors on the route ("flow field tiles", Elijah Emerson, *Game AI Pro*, 2013). A search over sector
    portals picks which sectors. Units with the same goal share the field, and local steering keeps them apart.
  - **What we take:** fields for goals many units share, built lazily only along the way, shared by goal, with Bump
    and clipping as our steering.
- **HPA\*** (Botea, Müller and Schaeffer, 2004).
  - **What it does:** clusters with their border crossings form a small abstract map. A long trip is planned on it,
    then refined cluster by cluster as the unit walks. Paths come out within a few percent of the shortest.
  - **What we take:** long trips over chunks now, and over 1000x1000 regions later. MAP_MEMORY.md section 5 already
    plans this for regions on disk.
- **Factorio** (2019 pathfinder rewrite, Friday Facts #317).
  - **What it does:** a coarse search over connected pieces of each chunk gives the tile search a far better
    distance guess, so the tile search stays exact to the rules but stops getting lost round big obstacles.
  - **What we take:** the option to keep today's tile search for long trips but guide it with the area map. That is
    closer to today's routes than HPA*.
- **StarCraft 2.**
  - **What it does:** one route for a group. Units steer apart and push idle friends aside, so they don't each plan
    round each other.
  - **What we take:** we already do this. Compact groups share the lead's route (Formations.dm). Friends clip and
    step off. Fields extend it to spread-out groups.

What none of them do is put moving units in the shared map. Units are handled where they meet, and so will ours be.

## 4. The design: one way map, kept by the engine

### 4.1 What it holds
- **A walk kind per tile:** open, blocked, drop (chasm or sky: blocked for dense walkers), holy ground, stairs (a link
  between layers, never walked through), wall walk, a door (whose, locked or not), or a place on the rock (below).
  - It holds 1 byte a tile.
  - It is computed by the same C# code as RmWalk.cs: the unit-free half of `RmWalkRules.Walkable`, split out so
    there is one copy, not two.
- **Fixed things only.** A dense thing counts only if it is fixed: placed doors, gates, built walls and placed
  furniture, listed by type. These never count, because they move:
  - units;
  - beast feet (dense, moving with their beast every step);
  - bodies;
  - carts and siege engines;
  - anything carried.
  An unlisted dense thing counts as open, which is the safe side of the rule.
- **Regions per 16x16 chunk.** A region is a set of tiles of one kind that reach each other without leaving the
  chunk. Up on the rock, the nodes are places (a tile plus a standing height, as RemasterSpotsAt gives them), and
  a region is places of one height that join by flat steps.
- **Links between regions:**
  - edges where two regions touch;
  - ramps (up one);
  - hops (down one, **one way**);
  - stairs, lifts and cave mouths between layers;
  - climbing, for climbers only.
- **Areas per mover kind.** The kinds are:
  - walker;
  - unholy walker (holy ground);
  - climber (gear or race);
  - flyer (on the ground and Sky layers only; it walks elsewhere);
  - non-dense mover (chasm and sky tiles don't stop it).
  A unit's kind is read fresh at every question, so a unit that turns undead or takes off its climbing gear is asked
  about as what it is now. Hop-downs make some ways one-way, so "can A reach B" is answered over a directed graph of
  areas, not by comparing two numbers.
- **Doors and owners.** Doors stay their own regions. Whether a mover passes depends on the door's owner, lock state
  and whether a player opened it, checked when asked (RimWorld's "traverse parms"). The own-door rule follows the
  game's `rm_own_doors` switch, as the engine's search does.

### 4.2 What it never holds
- Units (friends, enemies, wild creatures), a group's walking members, beast feet, and how full a wall walk is. These
  change every tick. They stay with the unit's own last-tiles search and step checks: `RemasterStepOpen`, clip,
  `RmStepOffShared`, Bump.
- So the map answers "is there a way through the ground", never "is it free right now". Units can only block more.
  That makes a "no" from the map a "no" for today's search too, which is what lets N1's first uses be exact.

### 4.3 Two questions, kept apart
- **`rm_nav_reach(M, T, reach)`** asks today's question, for exact uses:
  - only on M's own layer, with T's x and y, as today's search does;
  - with the same goal set (any tile within `reach` that M may end on).
- **`rm_nav_route_levels(M, T)`** asks the cross-layer question (stairs, ramps, hops, lifts), for B5 only.
  Mixing the two would make an exact use answer a different question from today's search.

### 4.4 Keeping it current, chunk by chunk
- **What marks a chunk dirty:**
  - a turf var write that walking reads: density, opacity, icon, icon_state, `remaster_wallwalk`, `IsWall`, `Tree`,
    and the block, ramp and carve vars (holes, dug, dug_top, roof, ceil, topcut, blocks, built, built_floor, slope,
    slope_h, carve);
  - a turf swapped;
  - a fixed thing (4.1) arriving on, leaving, or changing density on a tile.
- **The hooks:**
  - The engine already hears all of these: the VER hook for writes and swaps, and SetLoc for things (as RmGrid
    does).
  - The thing hook does one type check per move and acts only for the fixed types. It must not act on units: every
    clip step makes friends non-dense and dense again (`Chains/Enter.dm:38`), and every huge beast's step moves its
    feet.
- **Mountains reach further.** A column's height depends on rock up to 5 tiles away (RemasterBlocksAt), so a change
  to rock marks every chunk within 5 tiles, up to 4 chunks. Turf vars that are lists changed in place aren't seen by
  the VER hook. The walk-relevant vars above are numbers, and a fixture checks that stays true (7.A2).
- **The C# never writes game vars.**
  - Where DM caches a height on first read, the map computes the same number without storing it.
  - Where DM clears a dead ramp on read, the map treats the ramp as gone.
  A write from the map would move the 3D view's chunk counters and its own dirty marks, and loop.
- **How a dirty chunk is rebuilt:**
  - it is rebuilt the first time a question needs it, within a per-tick budget (2 ms to start);
  - a chunk still dirty when its turn comes answers "not known", and today's search runs;
  - then its links to its neighbours are redone;
  - then areas are updated. A join (a block mined through) merges two areas at once. A split (a wall closing a
    valley) marks the area unsure. Questions inside it get a bounded walk over the regions until a background pass
    renumbers it. A walk that runs out of budget answers "not known", never "no".
- **Changes that don't rebuild but still wake waiters.** Some changes alter who may pass but not the ground:
  - a door opened, shut, locked or unlocked;
  - a stone door driven or sealed;
  - a door's owner changing (a village taken);
  - a gate raised.
  Each of these is a "ways changed" event for the areas on both sides. Units waiting on a "no" there look again (B2).
- **Big changes come in batches.** These write thousands of tiles at once:
  - a cave instance made or wiped;
  - a felled golem becoming a mountain;
  - the world save applied at load;
  - biome placement;
  - the map growing (`world.maxx`/`maxz`).
  Each marks its chunks dirty once and rebuilds over ticks. A grown map rebuilds its index first, as RmGrid does.
- **Sleeping land stays asleep.**
  - The map keeps its own bytes. It reads tiles only to build or rebuild a chunk, so asking it never wakes land.
  - The first build shares the load-sleep pass's reads (Regions.dm), so the tiles aren't held awake longer. The
    memgc lesson: tiles held awake for a minute aged into the oldest GC generation, and 2.5 GB was held for 0.78 GB
    of live data.
  - A sleeping chunk that changes (rare: regrowth timers) stays dirty until a question needs it. It is rebuilt then
    through peek reads (MAP_MEMORY.md, planned, not built) or by waking that one chunk.
  - Regions on disk (the Daggerfall world) save their map bytes with the region record, or rebuild on first use.
- **Until a chunk is built, or with the map off (`RM_NAV=0`):** today's search runs. That is the fallback the native
  rule asks for.

Cost per change (estimates, to be measured in N1):

| Change | What is redone | Estimate |
|---|---|---|
| a block mined, dug down, or a ramp carved | its chunks on the ground and Sky layers, within 5 tiles | ~0.1-0.5 ms a chunk (256 tiles, plus the places on the rock) |
| a tree felled or grown, a wall or floor built | its chunk | ~0.1-0.3 ms |
| a door placed or removed | its chunk | same |
| a door opened, shut, locked, unlocked or taken | no rebuild; waiters on both sides look again | ~0 |
| units moving, clipping, beasts' feet | nothing | 0 (one type check a move) |
| a valley walled off (a split) | that area renumbered over ticks | ~1-5 ms worst, spread out |
| a cave instance, a golem's mountain, the load | a batch, over ticks | spread; today's search meanwhile |

How often:
- 2,000 miners take roughly 14-50 blocks a second (GsRun2000S stored ~37 stone a second).
- Many fall in the same chunks and the same tick, so expect a few ms per game second.
- The zone regrow spikes are the case to watch (`reports/polish-night-1026/regrow-spikes/`).

### 4.5 The safety net
- A unit told "no" by the map still runs today's search now and then, every 30 s instead of today's 3.
- If that search finds a full route, the game:
  - logs `RMNAV|wrong-no` with the tiles;
  - marks those chunks dirty;
  - lets the unit go.
- In tests and the shadow mode, every "no" is checked at once.
- A slow audit (one chunk a tick, rebuilt and compared) runs in the gates. In live play it can stay on cheaply.
- So a missed hook or a drifted rule shows as a log line and a 30 s delay, never a unit stuck for good.

### 4.6 Memory, today's 1000x1000x4 world

| Part | Size |
|---|---|
| walk kind, 1 byte a tile | 4 MB |
| region number inside its chunk, 1 byte a tile | 4 MB |
| places on the rock (heights, region per place) | ~1-2 MB |
| regions and links (est. 2-6 regions a chunk) | ~3-6 MB |
| areas per mover kind, and the one-way links between them | < 1 MB |
| **reach map in all** | **~12-16 MB** (live heap with 200 units is ~0.78 GB) |
| a shared way (flow field), per chunk it covers | ~0.5 KB (256 steps-left numbers) |
| shared ways in a 2,000-worker village (est. 10-20 fields x ~40 chunks) | < 1 MB |
| long-trip crossings and their distances, built lazily | a few MB at most |

Building the whole map at load: about 1-5 s (estimate: 15,876 chunks at 0.1-0.3 ms). If that's too slow at start, it
builds over the first minute, and today's search answers until it's done.

## 5. The pieces

### N0 Count first (S, exact)
- **What it does:** count every route search by who asked (order, attack, group, defence, site, hover, mountain) and
  by how it ended:
  - found;
  - part of a long way;
  - no way through;
  - tiles taken;
  - and, for attacks, "foe had no free side".
  Also counted:
  - hover checks, with their searches and their stairs and hop scans (section 12, H);
  - DM walk checks (`RemasterWalkable`) per second and the things they loop over (section 12, E1);
  - searches on the Sky layer by mover (flyer, climber, over rock or not: section 12, E3).
  These are counters and tick-profile labels only.
- **Players:** nothing changes.
- **Scenes:** walk latency (`tests/walk_latency_check.dm` WlRun), 2,000 workers (`pw_run.sh ... g2000`, GsRun2000S),
  250 v 250 (`reports/polish-night-1026/combat-speed/tests/cs_battle.dm`).
- **Why first:** it tells us how much is failing searches, chasing, mountains and long trips, so the order below can
  be checked before engine work starts. It fits the hot-loop plan's "labels first" step.

### N2 Chasers keep their route (S-M; rule change B6; the owner's pending call)
- **What it does,** in `RemasterAttackApproach`, four parts. The owner can take any of them.
  1. **Keep.** While the foe stands within 1 tile of the route's end, keep the route. Each step is still checked
     as today.
  2. **Repair.** If the foe moved further but is within 4 tiles of the route's end, join the old route to the foe's
     new tile with a short search, limited to 8 tiles round the foe. The joint follows today's rules (never ending
     on a friend's tile). Search in full only if that fails.
  3. **Full foe.** If every tile beside the foe is held (eight units round it, or walls):
     - on an attack-move, the fighter takes another foe with room (`RemasterFoeScore` already counts room);
     - for a foe the player clicked, it holds and looks at those 8 tiles again next tick (8 checks, not 512).
     Spears (reach 2), archers and casters never hold.
  4. **Slow retries.** A chase search that found no way is retried after 1 s, not every tick.
- **Players:**
  - routes come out the same length or a step longer;
  - a chaser sometimes turns a step later after a dodging foe;
  - a fighter no longer walks to "as close as it gets" and back behind a foe it can't reach.
  It doesn't need the reach map, which is why it's first.
- **Memory:** nothing new. **Cost per map change:** none.
- **Proof:**
  - route ms per game second at 250 v 250 should drop. Aim: most of the 338.
  - Fight results, 60 fights with `combat-rules/tests/cr_fair.dm`: winner, time to finish, falls and maims the same
    within noise. Chasing decides when blows land, and the owner tuned fight length.
  - Gates: attack_reach_check, obey, combat, clip, walk latency.
  - Each part has its own switch (`RM_CHASE_KEEP`, `RM_CHASE_REPAIR`, `RM_CHASE_FULL`, `RM_CHASE_RETRY`, 0 = today's
    way), so the owner can take some and not others.

### N1 The reach map (three stages)
**Status 10-27 20:11:** stage 1 is built and landed, on the owner's "ah okay do it if its hopeful". That covers:
- engine v12, RmReach.cs;
- the game side "nav-reach-map";
- proofs in `reports/polish-night-1026/nav-reach/`, and the devlog.
How it differs from the design below:
- Movables are left out entirely for now (doors too: hopeful).
- The kinds come only from the turf: density, the stairs icon, wall walk, Chasm or Sky, GoodGrass.
- Hooks mark tiles and the map reads them before its next answer: OpenDream sets a replaced turf's look after its hook.

Stage 2 (the Sky layer) and stage 3 (the rule changes) wait for the owner.

**What it does:** sections 4.1-4.5 in the engine (`engine/native/RmNav.cs`, new native versions). The DM side calls
`rm_nav_reach`, `rm_nav_route_levels` and `rm_nav_near`. Their DM bodies answer "not known", and the game runs today's
code.

- **Stage 1 (M, exact): flat layers.**
  - **Layers:** ground, underground and hell. There are no heights there, and flyers fly only on the ground layer of
    the three.
  - **First uses,** with the same answer as today, proven:
    - a search that only reads whether a route came back returns null at once when the map says no. That covers the
      hover check (`HoverCheck.dm:55`) and the formations check (`Formations.dm:1068`).
    - No caller that reads `rm_path_partial` after its search is shortcut: building sites, orders, attacks and group
      moves all read it.
  - **Shadow count** (`RM_NAV_VERIFY=1`): today's search runs anyway, and any route found where the map said none
    is logged. It must be zero.
- **Stage 2 (M, exact): the Sky layer, its places on the rock, and the links between layers.**
  - It comes after N1b, which proves the C# copy of the mountain rules (heights, ramps, hops, the corner rule) against
    the DM search first.
  - Its uses are the same exact ones, on every layer.
- **Stage 3 (S each): the rule changes the owner picks.**
  - **B1.** The click's red "can't" ping, and "Couldn't get there", come at once.
  - **B2.** A unit whose goal has no way through the ground:
    - it walks once to the nearest point, as today;
    - then it waits, and looks again when a "ways changed" event or a rebuild touches its area or the goal's, or
      when its own kind changes;
    - give-up times and messages stay the same;
    - the safety net checks every 30 s;
    - when it's units in the way rather than ground, the 3 s retries stay.
  - **B3, not recommended now.** "Nearest point" for an unreachable goal would be the nearest place in the unit's
    whole connected area, not the nearest of the ≤512 tiles a search looked at. The catch: for an island goal, the
    nearest point by straight line can be a far peninsula, a long walk off, where today the unit stops at the near
    shore. If wanted later: only when that point's walk is no longer than today's partial route plus a margin, found
    over region boxes, never by scanning tiles.
  - **B4.** Zone targets with no way to them are found by the map, for every zone at once. The map counts doors,
    chasms, holy ground and rock steps, which today's fill doesn't. It replaces RmJzFill and its 15 s worker failures.
  - **B5.** Climb, Hop and Scale orders pick stairs, ramps or hops that lead to the goal's area, by walking
    distance, not the nearest by straight line within 25 tiles. Units may now walk further to stairs that lead
    somewhere, instead of standing stuck by near ones that don't.
- **Memory:** ~12-16 MB. **Cost per change:** section 4.4.
- **Proof:**
  - **Reach equals search:** on the owner's map, 20,000 random pairs per layer and mover kind, compared with an
    uncapped, directed flood of today's walk rules with the unit checks switched off. Zero differences.
  - **Kept current equals built fresh,** after each kind of change:
    - mine a block, mine near a chunk corner (the 5-tile height reach), dig down, carve a ramp, mine a ramp's block
      away;
    - fell a tree, grow a tree;
    - build a wall or floor;
    - place, open, lock or capture a door; drive a stone door;
    - make and wipe a cave instance; fell a golem;
    - load a world save; grow the map.
    The kept map is compared with one built from scratch after each. Zero differences.
  - **Heights:** the map's height for every rock column equals RemasterBlocksAt's, after load and after digs.
  - **Engine cost:** one type check per move, measured as RmGrid's was (`tests/grid_bench_ab.dm` style).
  - **Scenes:**
    - walk latency the same;
    - g2000 (pieces stored within 5%, ms a tick, heap minus fragmented);
    - 250 v 250;
    - the gates: `door_test`, `stone_door_check`, `mountain_levels_test`, `mountain_heights_test`,
      `plan_access_test`, `gather_zone_test`, `clip_check`, `wallwalk_test`.

### N1b The mountain search in the engine (M, exact)
- **What it does:** `RemasterLevelPathDM` in C#, step for step, as RmPath.cs did for the ground. Its rules:
  - node = tile plus height, 768 cap;
  - the RemasterSpotStep rules and the corner rule;
  - the goal height term;
  - `remaster_plan_feet` returned too.
  The DM search stays as the fallback and the reference.
- **Its place-reading code** (heights computed without the cache write, dead ramps treated as gone) is the code N1
  stage 2 builds on.
- **Players:** nothing changes.
- **Memory:** none. **Cost per change:** none.
- **Proof:**
  - like `tests/rmpath_equiv.dm`, on the Sky layer with mountains, ramps, dug floors, hops, and columns never read
    before;
  - identical routes and identical planned heights;
  - a shadow mode.
  - **Trap:** the DM search writes heights as it reads them, so in the fixture the C# side must run first on fresh
    columns, or both read cached ones.

### N3 Shared ways: flow fields (L; rule changes B7-B8)
- **What a shared way is:** a field of "steps left to the goal". It is built from the goal outward over the walk
  map, only in the chunks the area map says the way crosses, and only when a unit first asks there.
- **Shared by key:** the goal, the owner (doors differ by owner) and the mover kind. Goals many units share:
  - a stockpile or yard (all its tiles);
  - a zone's open edge;
  - an enemy group (seeded from its units' tiles, refreshed every second while chased);
  - a banner or rally point;
  - later, a group move's slot area.
- **How a unit walks one:**
  - Next tile: the neighbour with fewer steps left, ties in today's order (N, S, E, W, NE, NW, SE, SW).
  - **It keeps its next 13 field steps as its route list**, refreshed each step, so clipping (`RmRouteInto`,
    `RmClipLands`) and `RemasterStepOpen` work exactly as with a searched route.
  - On a friend's tile: clip through as today, never ending there.
  - Anything else in the way: a short search round it, within 8 tiles, then back onto the field. If that fails, a
    full search, as today.
  - The last few tiles to its exact spot (a slot, a work face, a free store tile): its own search, as today.
- **Lifetime and limits:**
  - a field is dropped 30 s after its last user leaves;
  - it is rebuilt per chunk when that chunk's map version moves;
  - there is a cap of live fields per player and of field chunks built per tick. Past the cap, today's search runs.
- **Players:**
  - **B7.**
    - Routes are the same length (the fields use the same step costs).
    - Among equal-length routes, units take different tiles.
    - Enemies standing far ahead no longer bend the whole route: units go round them when they get there, as they
      do round friends who stopped.
  - **B8** (if the owner wants it). "Nearest store" becomes nearest by walking, not by straight line. A store across
    a river stops pulling carriers.
- **Order inside N3:** stores and yards first (2,000 workers), then attack-moves on an enemy group (the first-step
  batch), then zones. Group moves only when formations resume (B10).
- **Memory:** section 4.6. **Cost per change:** one chunk of each field that covers it, rebuilt on its next read.
- **Proof:**
  - every field step lies on a shortest route: on random pairs, field route length equals the uncapped search's.
    Zero longer.
  - g2000: pieces stored per hour not lower, frozen carriers no more than today (the "100 frozen carriers" jam
    must not come back), the most units on one tile, deliveries' walk time, ms a tick, heap.
  - 250 v 250: first-step batch ms.
  - walk latency: building a field on the click must fit in the click's tick, or the first step comes from today's
    search while the field builds.
  - `tools/check_clip.py` (corridor, head-on, doorway, ally, enemy, crowd), door, gather and lodge gates.

### N4 Long trips (step 1: M; step 2: L; rule change B9)
- **Step 1, one world:**
  - A trip longer than one search, or one the area map says goes round an obstacle, is first planned over regions.
    That is a short search over thousands of nodes, not millions of tiles.
  - It gives a corridor of chunks. The tile search then runs inside the corridor a few chunks ahead, so the 512 cap
    applies to each leg, not to the trip.
  - The Factorio-style variant keeps today's tile search and only guides it with region distances. It is closer to
    today's routes; try it first.
- **Step 2, the Daggerfall world:** the same idea one level up. A graph of region crossings between 1000x1000
  regions, loaded on demand, with only the regions at either end and the one being walked held in tiles. It ties
  into MMO_ARCHITECTURE.md section 11 and MAP_MEMORY.md section 5.
- **Players (B9):**
  - long walks go round lakes and ranges, and units no longer stop at "part of a long way" or in a dead-end bay;
  - "Got as close as it could" means there really is no way;
  - long routes look different from today's.
- **Memory:** crossings and their distances per chunk, lazily: a few MB.
- **Cost per change:** a dirty chunk's crossings redone with it.
- **Proof:**
  - on random long pairs (100-900 tiles), route length within 3% of the shortest;
  - a bays-and-lakes arena where today's search stalls, and the new one arrives;
  - raids marching in, caravans, the far-records wake walk.

## 6. Every behaviour change, in one list

| | Today | After | Recommended |
|---|---|---|---|
| B1 | "can't get there" known after a search (hover, click) | at once, same wording | yes |
| B2 | no way through: full search again every 3 s (orders), every tick (attacks) | walk once to the nearest point, then wait for a change near it; 30 s safety check; same give-up times and messages; unit-blocked ways keep 3 s retries | yes |
| B3 | unreachable goal: nearest of the ≤512 tiles looked at | nearest place in the unit's connected area | not now (long detours to far points) |
| B4 | zone targets with no way found by a density-only fill, after a worker fails 15 s | found by the map for every zone at once (doors, chasms, holy ground, rock steps counted) | yes |
| B5 | stairs chosen by straight distance within 25; others tried after 10 s stuck | stairs, ramps or hops that lead to the goal's area, by walking distance | yes |
| B6 | chasers search again whenever the foe steps, or every tick with no way | keep, repair, another foe or hold, retry after 1 s (N2) | all four |
| B7 | each unit's own route; enemies far ahead bend it | shared fields: same lengths, other tiles among equal ones; enemies stepped round when reached | yes, stores and yards first |
| B8 | nearest store by straight line | nearest by walking | yes |
| B9 | long trips cut at 512 tiles, can stall in a bay | corridor over the area map; arrives | after N3 |
| B10 | group moves: slots, shape, hand-out, the lead's route shared | unchanged until formations resume | wait |

Not changed by anything here:
- friends clip and never rest on one tile;
- own doors open for own units;
- heavy stone doors stay shut;
- the mountain step rules;
- flyers and the Sky level;
- steps stay tile to tile (no sliding);
- each step is still checked as today (`RemasterStepOpen`, Bump).

## 7. Ways it could break, and what stops each

Grouped by how bad they would be for a player.

### A. The map says "no way" when there is one (worst: units stand and give up)

| | How it breaks | What stops it |
|---|---|---|
| A1 | **A rule kept in three places drifts.** A walk rule changes in DM and RmWalk.cs but not in the map; units refuse a real way. | The map calls RmWalk.cs's own code (its unit-free half), so there are two copies, as today, not three. The DM rule's comment names the map. The shadow count runs inside the clip, obey, door and mountain gates, so a drift fails a gate. The safety net catches what's left. |
| A2 | **A change the engine doesn't hear.** VER misses vars set straight on new objects, engine-set vars, and lists changed in place. | The walk vars are plain numbers (a fixture asserts it). The "kept equals fresh" fixture covers every kind of change in N1's list. A slow audit rebuilds and compares one chunk a tick in gates. The safety net. |
| A3 | **Reads that write.** DM stores a column's height on first read, and clears a dead ramp on read. If the C# wrote too, it would loop its own dirty marks and the 3D chunk counters. If it computed differently, heights would disagree. | The C# computes, never writes (4.4). Heights fixture over the whole map. Rock changes dirty everything within 5 tiles. The N1b fixture runs the C# first on fresh columns. |
| A4 | **The mover changes.** A unit turns undead, takes off climbing gear, lands, changes race, or its owner loses a door to capture. | The kind and the door owners are read fresh at each question. A waiting unit looks again when its own kind changes. |
| A5 | **A door opens and nobody notices.** Opening changes nothing in the map, so waiters keyed to rebuilds would never retry. | Door, stone door and gate state changes and owner changes are "ways changed" events for both sides (4.4). |
| A6 | **Wrong question.** Today's search measures x and y only and stays on the unit's layer. A reach answer "via the stairs" would differ. | Two questions kept apart (4.3). The fixture uses today's question. |
| A7 | **One-way hops.** Treating areas as two-way would claim a unit on a ledge can climb back. Treating them too strictly would refuse a hop-down way. | Directed reach over areas, proven against a directed flood. |
| A8 | **A split not yet renumbered.** | Bounded walk, "not known" when it runs out, never a guess of "no". |
| A9 | **Map off or half built** (old engine, start-up, a batch rebuilding). | "Not known" → today's search. Each switch's off state is today's code. |

### B. The map says "yes" but units still can't get there

That's the safe side: units, full wall walks, beast feet, bounds and the 512 cap all block more. Each costs one
ordinary search, as today. N0 and the shadow count show how often.

### C. It costs more than it saves

| | How it breaks | What stops it |
|---|---|---|
| C1 | **Rebuild storms**: 2,000 miners, zone regrow spikes, a cave instance, a golem's mountain, the load | Lazy rebuild on first question; 2 ms a tick budget; "not known" meanwhile; batches marked once. Watch the regrow-spike scene. |
| C2 | **The hook on every move**: every unit step goes through SetLoc; every clip flips friends' density | One type check per move, fixed types only, never units, feet or bodies. Measured as RmGrid's was. |
| C3 | **Load time and old memory**: a 1-5 s build that holds tiles awake | Build on the load-sleep pass's own reads, or after it, over a minute. Heap minus fragmented after load, before and after. |
| C4 | **Waking sleeping land**: rebuilding a sleeping chunk reads its tiles | Rebuild only when a question needs it. Peek reads when the engine has them. Count woken tiles (`rm_tiles_stats`). |
| C5 | **Nearest-point scans** (B3): an island goal makes a ring scan huge | B3 not now; if later, over region boxes only, capped. |
| C6 | **Too many fields**: per goal x owner x kind, plus battle fields refreshed every second | A cap per player and per tick; today's search past it. N3 counts fields live. |
| C7 | **Engine builds**: the .NET SDK lives in /private/tmp and is wiped on reboot. Other sessions build engines too. | Reinstalling the SDK needs the owner's OK. Native version numbers agreed on the board before building. Always built on build_runtime defaults (or the save patch is dropped). A restore point and the owner's OK per install. |

### D. Movement that plays or looks worse

| | How it breaks | What stops it |
|---|---|---|
| D1 | **Field walkers can't clip**: Enter lets a unit into a friend's tile only with a route list of 2+ tiles reaching an open tile within 12. Without one, the carrier jam comes back (200 workers once had ~100 frozen). | Field walkers keep their next 13 steps as their route list. Clip check plus the g2000 frozen-carrier count in N3's proof. |
| D2 | **One-file lanes**: every worker on one field takes the same tiles, so more friend-clipping and crowding at store tiles | Measure (most units on a tile, frozen carriers). If it shows, spread ties by unit (routes still shortest). |
| D3 | **Enemies not in fields**: a field leads into a wide enemy line, the 8-tile search round fails, and units mill | Fall back to today's full search for that unit. B7 is the owner's call. |
| D4 | **Idle fighters** (N2 hold): a fighter holds behind a full foe while others have room | Attack-moves take another foe with room. Only a clicked foe makes it hold. Reach-2 and ranged never hold. |
| D5 | **Repaired routes ending on a friend** | The joint is a real search with today's never-end-on-a-friend rule. |
| D6 | **Fight balance moves**: chasing decides when blows land | 60-fight table before and after. Any move beyond noise goes to the owner before landing. |
| D7 | **Long detours** (B3, B5): a far "nearest point", or far stairs | B3 not now. B5 by walking distance, named to the owner. |
| D8 | **Group moves**: formations read routes (`RemasterWalkingMateOn` on path[1], the lead's route moved over) | Group moves untouched until formations resume (B10). |
| D9 | **Building sites**: "no way" is read from `rm_path_partial` right after the search | Not shortcut by any exact use. A site gets the instant answer only with B1. |

### E. Owner rules this must not break

| Rule | How it stays |
|---|---|
| Friends clip, never rest together | field walkers' route lists; ends by today's search |
| Own doors, very owner only; stone doors locked when shut | doors checked when asked, by today's rule and switch |
| Mountain steps (ramp up 1, hop down 1, climbers) | N1b proves the rules first; directed reach |
| No sliding | steps stay tile to tile |
| Every native keeps a DM fallback, proven or differences named | exact parts shadowed; each rule change has its own switch whose off state is today |
| Build exactly what was approved | one switch and one landing per B, so the owner can take some and not others |
| No 30k runs; one big run at a time | 5k is the biggest stress size; runlock |

## 8. How each step is proven (summary)

- **Exact parts** (N0, N1 stages 1-2, N1b):
  - equivalence fixtures on the owner's map with zero differences;
  - "kept equals fresh" after every kind of change;
  - a shadow switch in live runs, as RmPath was proven.
  Every native keeps its DM fallback. For the nav map, that fallback is today's search.
- **Rule changes** (B1-B10): the scenes, run interleaved A/B, one big run at a time, at speed 4 for behaviour and
  speed 1 for timing:
  - walk latency (first step must not get later);
  - 2,000 workers (pieces stored within 5%, frozen carriers, ms a tick, heap minus fragmented);
  - 250 v 250 (route ms per game second, first-step batch, fight results over 60 fights);
  - the movement gates: clip, door, stone door, wall walk, mountain heights and levels, plan access, gather zone,
    formations, attack reach, obey. A flaky obey or parry failure is rerun as A/B before blaming a landing.
  - No 30k runs: 5k is the biggest stress size.
- **Each engine build:** a new native version, a restore point, the owner's OK to install, `RM_NAV=0` to turn it
  off.

## 9. Order and timing

1. **Now, during the freeze:** nothing lands.
   - N0's counters can ride with the hot-loop audit's label landing if the lead agrees. It is exact, with no
     behaviour change.
   - Once the owner answers section 10, the picked steps can be prewritten and staged (C# plus fixtures) without
     landing.
2. **After the freeze and the hot-loop audit:**
   - N2 (S-M), if the owner says yes;
   - then N1 stage 1 (M), N1b (M) and N1 stage 2 (M), all exact;
   - then the stage 3 changes the owner picked.
3. **Then N3:** stores and yards, then enemy groups, then zones.
4. **Then N4 step 1.** N4 step 2 comes with the Daggerfall regions (MMO roadmap phase 2-3), not before.
5. Group moves on fields only when formations come off hold.

## 10. Questions only the owner can answer

Each has a recommended answer. They match the B list.

1. **Units with no way through the ground** (B2): should they walk to the nearest point, then wait for a change near
   them instead of searching every 3 s? There is a 30 s safety check, and give-up times and messages stay the same.
   *Recommended: yes.*
2. **Nearest reachable spot** (B3): should it be chosen from the unit's whole connected area? *Recommended: not now.*
   It can send units on long detours to a far point.
3. **Zone reach** (B4): should the map decide which zone targets are out of reach, for every zone at once (doors,
   chasms, holy ground and rock steps counted)? *Recommended: yes.*
4. **Stairs** (B5): should units pick stairs, ramps or hops that actually lead to the goal, by walking distance, even
   when they are further than the nearest? *Recommended: yes.*
5. **Chasers** (B6, the pending call): which parts of keep, repair, another foe or hold, and 1 s retries?
   *Recommended: all four,* landed only if the 60-fight table stays within noise.
6. **Shared ways** (B7): may units heading for the same place share one way, with enemies far ahead stepped round
   only when reached? *Recommended: yes, stores and yards first.*
7. **Stores by walking** (B8): should "nearest store" mean nearest by walking? *Recommended: yes.* It changes which
   store some loads go to.
8. **Long trips** (B9): build step 1 after shared ways, or wait for the Daggerfall regions? *Recommended: after
   shared ways.*
9. **Group moves** (B10): leave them on today's routes until formations resume? *Recommended: yes.*
10. **N0 now:** may its counters ride with the hot-loop audit's label landing during the freeze? *Recommended: yes.*
    No behaviour changes.

## 11. Not in this plan

- Moving units into the shared map, or a navigation mesh. Units change every tick. The map and the game are tiles,
  and block-by-block mining changes tiles one at a time, so tile regions fit and a mesh doesn't.
- Changing any walk rule (doors, clip, heights, flyers) or formation shape.
- Big-army formation work (on hold).
- Wild creatures' own walking (`Monster AI.dm` steps straight at its target; it doesn't search). It could use the
  reach map later, but that's a separate change.
- An off-screen route engine for far records. Far land stays asleep. Records don't walk.

## 12. Found on the way: exact wins, and the hover cost

Third pass (10-27, the owner: "anything else you notice and see"). None of these needs the reach map, and none changes
what any unit does.

**Staged (10-27, the owner: "prewrite E1 and E3 plus the N0 counters as staged patches in reports, no landing and no
runs"):**
- `reports/polish-night-1026/nav-plan/staged/` holds `n0-search-counts/`, `e1-native-walk/` and
  `e3-sky-flat-native/`. Each has a `patch.json` for land_polish.py, a `gen.py` that rebuilds it from the game as it is,
  and a README with its proof.
- Not compiled or run. The anchors check out against today's game, and the three apply in any order with identical
  results.
- They go to the lead's hot-loop audit after build 69. E2 waits for the next engine build.

- **E1. Per-step walk checks are still DM (S, exact).**
  - The game has 35 `RemasterWalkable` calls, all in DM:
    - each order tick's next-step check (`RemasterStepOpen`);
    - the clip look-ahead (up to 12 tiles, `RmClipLands`);
    - step-off (`RmStepOffShared`: 8 tiles);
    - slot looks, hops and climbs.
  - Each DM check loops over the tile's things with `for(var/atom/movable/A in T)`, which copies the tile's whole
    contents list (hotloops PLAN.md, engine facts). Every tile of a stockpile area now takes goods, so a carrier's
    check on a store tile copies every stone lying there. `RemasterTilePlaces` does the same loop.
  - The engine already has the same rule as a native, `rm_walkable` (RmPath.cs), which reads the tile's things in
    place. Only the tests declare it (`tests/rmpath_clip_equiv.dm`, `tests/rmpath_equiv.dm`), and they already
    compare it with the DM rule.
  - **Fix:** declare it in Native.dm with the DM body as the fallback, behind `RM_NATIVE_PATH`, with door types
    passed as RemasterOrderPath does. Call it from RemasterWalkable's callers through one wrapper.
  - **Proof:** the existing fixtures, and a shadow count.
  - **Measure first** (N0): on bare tiles the call's argument cost may eat the gain. On store tiles it should win
    clearly.
- **E2. The engine search has headroom of its own (S, exact; an engine build).**
  - For every tile it looks at (up to ~4,000 a search), `RmWalkRules.Walkable` reads the mover's own vars again:
    its type and `Flying` (FliesOver), and its `density`. Those can't change during one native call.
  - Each search also makes two dictionaries, a queue and one node object per tile.
  - **Fix:** read the mover's vars once, and reuse the search's tables between searches. The answers are the same.
  - **Proof:** `tests/rmpath_equiv.dm`, `tests/rmpath_clip_equiv.dm` and the shadow mode, with zero differences, plus
    route ms per game second at 250 v 250.
  - Unmeasured. It speeds up every search left after N2 and N1, so it pays on top of them, not instead.
- **E3. The engine search is skipped for everyone on the Sky layer, even where the DM uses the flat search (S,
  exact).**
  - `Native.dm:47` sends every unit on the Sky layer to the DM. But the DM search only uses the mountain search for
    a unit standing over rock that can't climb (`Orders.dm:786`, `Gather.dm:556`). Everything else on that layer gets
    the flat DM search, the one `rm_path` copies exactly:
    - flyers and dragons on the Sky level;
    - cliff climbers and units with climbing gear on the tops;
    - units on wall walks and upper floors.
  - **Fix:** use the engine for those, with the same test the DM makes (`RemasterCanClimb`, or no places over the
    unit's tile). The same side effects happen either way: both run `RemasterSpotsOrNull` on the start tile.
  - **Proof:** a shadow run on the Sky layer (flyers up, climbers on tops, units on wall walks), with zero
    differences.
  - Small today. It grows with flying units, wall walks and the parked wall and cliff archers.
- **H. The hover check is a route search per player's mouse.**
  - Each new tile under the mouse (the page waits 180 ms, so up to ~5 a second while it moves) runs
    `RemasterHoverVerdict` (`HoverCheck.dm`) for up to 6 selected units. For each unit, that is either:
    - a route search; over water or into a walled place, it takes the full 512 tiles and fails; or
    - for a unit on another layer, a 25-tile stairs scan (`range(25)`: 2,601 tiles, each copied) and a 12-tile hop
      scan.
  - In multiplayer, every player's mouse is server time.
  - N1 stage 1 makes the route part instant (an exact use). Until then, N0 will show what it costs. Caching each
    unit's stairs answer for the 2 s the verdict already keeps would be a small rule change (a hover text up to 2 s
    old).

---
Read for this plan:
- engine: `engine/native/RmPath.cs`, `RmWalk.cs`, `RmGrid.cs`, `RmSight.cs`, `RmSlots.cs`, `RmPlan.cs`, `RmVer.cs`,
  `RmTiles.cs`, `RmWatch.cs`;
- game: `game/Code/Remastered/Native.dm`, `Orders.dm`, `Gather.dm` (places and level search), `Breaking.dm`
  (heights), `WalkLoop.dm`, `Clip.dm`, `Chains/Bump.dm`, `Chains/Enter.dm`, `Attack.dm`, `Formations.dm`, `Jobs.dm`
  (zone reach), `WallWalks.dm` (stairs), `Beasts.dm` (feet), `Flying.dm`, `Blueprints.dm`, `Awake.dm`, `Regions.dm`;
- planning: `ENGINE_PLAN.md`, `MAP_MEMORY.md`, `MMO_ARCHITECTURE.md` section 11, `SCALING.md`, `MOUNTAIN_HEIGHTS.md`;
- reports and devlog: `devlog/2026-10-27/combat-speed.md`, `reports/server-cost/next-speed-list.md`,
  `reports/polish-night-1026/hotloops/PLAN.md`.

`reports/polish-night-1026/movement-lag/PLAN.md` wasn't written yet at 09:30. When the lead's plan lands, N0's
counters should use its labels.
