# Map memory: a whole world's server under 1 GB

Written 2026-10-24 by the map-memory session. Design plus a working arena prototype; **nothing is in `game/` or the
engine yet** (the coordinator decides). The user: "design and prototype map memory, loading only regions near players
plus compact tile storage, aiming for a world under 1 GB, with an arena test first."

## In short

- The map, not the units, is the memory: every one of the 1000x1000x4 world's 4 million tiles is a full engine object
  graph, **286 bytes of live heap a tile awake** (218 B that sleeping frees, plus 68 B of tables that stay), so
  ~1.1 GB of live objects before anything lives on the map. Measured on the user's world (no client): 1.53 GB of
  heap in use, 1.84 GB for the whole process.
- **Tiles can sleep.** A tile nobody holds (no unit or thing on it, no DM value pointing at it, only plain values of its
  own) gives up its 218 B of objects for a packed record of **20 B** in the prototype (12 B once turf refs come from
  coordinates).
  Any read of it, from any DM or engine code, wakes it first with the same ref, values, appearance and area, so **the
  game does not change**. Measured (arena): the whole 262,144-tile map sleeps in 45-98 ms; a 128x128 region wakes in
  1.6-5.6 ms (engine) or 4-12 ms read tile by tile from DM.
- **Regions near players.** On top of that, the game puts a region's *things* (items on the ground, workshops,
  banners...) and its far-away units (FarRecords.dm) into records when nobody is near, so its tiles can sleep too. A
  region file keeps them on disk when the world is bigger than memory (the Daggerfall-scale land).
- **Measured on the user's world** (private copy, no client): the server's physical footprint goes from **2.56 GB**
  just after load to **1.02 GB** with every tile that can asleep, the areas' turf sets trimmed and **8 players' land
  awake** (each player's land ~21 MB); ~0.85 GB with one player. The heap in use: 1.54 GB -> 0.58 GB asleep -> 0.60,
  0.67, 0.76 GB with 1, 4, 8 players.
- Build first: the engine's sleeping tiles plus the area-set trim (one engine build with formations' v6; the trim alone,
  with no sleeping, is -75 MB), then a small DM sweep in Awake.dm. Then the game-side cleanups (world-save signatures,
  `T.vars` reads), the final layout and creatures as records (another ~0.2 GB), then regions for things, then region
  files.

Numbers marked (arena) are from `tests/map_memory_test.dm` on a 256x256 window of the real land, all four layers;
(world) from `tests/map_memory_world.dm` and `tests/map_memory_world2.dm` on the user's real world (a private copy of the
world and its save, no client: `tools/tick_profile.py --client none`; the user's saves checked unchanged afterwards).
Logs: `reports/server-cost/map-memory-world*` and `tests/map_memory_test-checks.json`.

## 1. Where a tile's memory goes

Every tile is a full engine object graph, made at load for all 4 million tiles:

| Part (per tile) | Bytes | Sleeping frees it? |
| --- | --- | --- |
| the turf object (`DreamObjectTurf`: DM object 48 + atom 40 + turf 40 + header 16) | 144 | yes |
| its cell (`IDreamMapManager.Cell`) | 40 | yes |
| the cell's things list (made even when empty) | 32 | yes |
| its own-vars table, once the game sets any non-appearance var | 200-400 | yes (kept as a small array) |
| a vars list object, once DM code reads `T.vars` | ~100 | yes (made again if asked for) |
| overlays / underlays list objects, once DM code reads them | ~100 each | yes |
| (before engine v5: its contents list) | ~170 | the v5 memory patch makes it on demand |
| its slot in the level's cell array | 8 | no (null while asleep) |
| its ref slot (the engine's turf bucket) | 8 | no (kept, so refs stay) |
| its area's turf set (`HashSet<DreamObjectTurf>`: 20 B a place; room for 1.8 places a tile in the arena, 2.1 on the user's world) | 36-43 | no: the set keeps its room (trimming it gives the room back) |
| the client map's tile (Robust grid: tile 8 + snap cell 8) | 16 | no (untouched) |

Measured (arena, the heap in use after a full collection, less the collector's free space): sleeping frees **218 B a
map-loaded tile**, and waking one allocates **216 B** (`rm_tiles_wake_cost`); a tile the game has worked (own values,
a vars list) frees more. `GC.GetTotalMemory` read ~430-460 B for the same tiles: it counts the collector's slack, which
is also why the process holds more than its live objects (1.84-2.66 GB here without a client; 2.3-3.3 GB in
server-cost's runs with a client and 200 units).

The game's own per-tile bookkeeping adds to it where the world has been touched (6.2): WorldSave.dm's signature lists
and vars lists on touched or explored tiles. On the user's world (world), a minute and a half after load: 58,347 tiles
carry a vars list (45,665 on the ground) and 2,274 have own values.

## 2. Tiles that sleep (compact tiles, engine)

### What sleeps
A tile can sleep when **only its cell holds its turf** (DM's reference count is 1: no unit, thing, list, var, running or
sleeping proc points at it), it has **no things on it**, no tag, and its own values are all **plain**: numbers, text,
types, files (icons) or null. Its lazily made lists (vars, overlays, underlays, filters, an empty vis_contents, the
contents list) are views of its appearance or empty, so they are dropped if nothing else holds them.

Measured (arena): 261,997 of 262,144 tiles can sleep at once; the other 147 have things on them (the map's objects and
creatures) or a DM value holding them. On the real world (world): 3,987,514 of 4,000,000 at once, in 4.1 s; 4,031 tiles
have things on them and 12,435 are held by DM values (5,933 of them in hell, 6,355 on the ground: lists of tiles,
destinations, the world save's lists).

### What a sleeping tile keeps
Per 128x128 block of a layer (made with its first sleeping tile, freed with its last), per tile, as small indexes:

| Field | Prototype v4 (measured) | Final |
| --- | --- | --- |
| type / definition (the map's per-tile one for var-edited tiles) | 2 (index into the world's definitions) | 2 |
| appearance | 2 (index into the block's own table, which holds them strongly: appearances are weakly registered) | 2 |
| area | 2 (index into the world's areas) | 1-2 |
| own values | 4 (index into the block's value sets; 0 for most tiles) | 4 |
| ref slot | 4, plus 4 in the slot map (ref slot -> tile) | 0 (turf refs computed from coordinates, as BYOND does) |
| density | 1 | 1 bit |
| **total** | **20 B** (arena: 5.23 MB for 261,997 sleeping tiles) | **~12 B** |

The first prototype held references instead of indexes: 42 B a tile. What stays for every tile, asleep or not, is the
level's cell-array slot (8 B), the ref slot (8 B), the area set's room (36 B: the sets keep their room when tiles
leave, and the world's default area had every turf in it while the levels were made) and the client map's tile
(16 B). Trimming the sets (`HashSet.TrimExcess`, measured in the arena: 9.45 MB back for 262,144 tiles, 36 B a tile)
leaves **52 B a sleeping tile in all** (20 + 8 + 8 + 16). The final build can take two more away (cell arrays only for
awake blocks, refs from coordinates) and keep the area as an index (made into a set on demand when DM asks for an
area's turfs): **~28 B a sleeping tile in all**. An awake tile is 286 B (218 + 8 + 8 + 16 + 36).

### Waking
`TryGetCellAt` (so `locate`, `block`, `range`, `view`, `get_step`, the route search, a unit stepping in), `SetTurf`
(`new /turf/X(T)`), a ref (`locate("\ref...")`), the world's turfs (`for(var/turf/T in world)`, in the same order) and an
area's turfs (area contents, area x/y) wake what they read. Waking makes a new turf object with the old ref slot, type,
appearance, density and values, a new cell in the same area, and no `New()`: to DM it is the same turf. Resizing the
world or adding layers wakes everything first.

### Why the game can't tell
- A turf that any DM value holds never sleeps, so object identity can't be observed.
- Refs are kept (the slot is reserved, not reused).
- `T.vars` order comes from the type, not the table, so it is unchanged.
- tmp vars sleep with the rest (caches like `remaster_blocks`, `remaster_vein` stay worked out).
- Proved in the arena (`tests/map_memory_test.dm`, all checks pass):
  - **Round trip, byte for byte**: every var of 73,984 tiles (region R and an 8-tile margin, four layers), their refs,
    areas and appearance vars, and every var of every thing on and in them (68 things, made again from records), dumped
    before R slept and after it woke: identical.
  - **3D and HUD across the edge**: the camera on R's edge (x 128, R from 129) zoomed out (101x81): the terrain on three
    layers, the things in view and the HUD's world map are identical with R's tiles asleep; building them woke 5,430 of
    R's 16,344 sleeping ground tiles (the ones they read). With R's *things* also turned into records, terrain and world
    map stay identical and R's things are missing from the view, as expected: a region must wake before anyone can see
    it (section 3).
  - **Play across the edge**: a Human walked 36 tiles from awake land into sleeping R and arrived; then mined a block of
    a mountain in sleeping R (the block came out).
  - **The game's own checks with the map asleep**: the obey arena (32 order cases: moves, chops, mining, pick-ups,
    attacks, stairs, walled-in, asleep, flying, legless...) with every tile that can put to sleep once a second
    (`tests/map_memory_sweep.dm`): the same verdict in all 32 cases as on the same engine without sleeping (26 pass; the
    6 that fail are the known chop cases that fail on every engine); the only differences are two random damage
    figures. 102,799 tiles slept over 80 sweeps and 78,901 were woken by the game while it played; 0 errors.

### Who puts tiles to sleep
A DM sweep, beside Awake.dm's chunk map (which already knows what is near players): every 10 s, for each 16-tile chunk
not awake for the last 60 s, `rm_tiles_sleep` over it. Putting a tile to sleep costs 0.17-0.38 µs (arena), so the
first pass over a whole 4-million-tile world (0.7-1.5 s) is spread a 128x128 block a tick (3-6 ms); after that most
passes only look at chunks that just fell asleep, and a tile already asleep costs one null check. On the real world
(world): a whole-map sweep after a minute of play put 418,493 tiles back to sleep in 334 ms; in that minute the world's
own loops (wild creatures looking for targets, NPCs, raids) had woken 26,721. With `RM_COMPACT_TILES=0` the native only
counts (the switch for the first weeks), and on an engine without it the DM fallback does nothing.

### What still wakes tiles needlessly (next engine step)
Engine readers that only want a tile's walkability or its things wake it anyway: the route search (`rm_path`, up to
512 tiles taken, ~4,000 read), `rm_walkable`, `view`/`range`, `GetMobsInRange`. RmWalk.cs needs only density, icon,
icon_state, `remaster_wallwalk` and the things (none on a sleeping tile), all in the packed record: a **peek** read that
answers from the record without waking.

The same goes for DM scans: `range(12, X)`, `view()`, `oview()` build a list of every turf in the box, so a
`for(var/obj/Items/I in range(12, S))` wakes 625 tiles to find a few things. Measured in the arena (a sleeping region,
the player's ticks one at a time, then a unit standing in it): care, patrol, orders and settlement ticks woke **0**
tiles; an idle unit's own loops woke **1,320** in 10 s (the box it looks round). A unit walking 36 tiles into the region
and mining there woke all 15,560 of its ground tiles over the walk. That land is awake by Awake.dm's rule anyway (32
tiles round every unit), so it costs nothing extra; it matters for wild creatures and NPCs in sleeping land, which
should rest (Awake.dm) or be records. A things-only search (ENGINE_PLAN.md phase B's `rm_near`, a 16-tile index of
creatures and things) would skip sleeping tiles entirely.

## 3. Regions near players (game)

A **region** is 128x128 tiles of one layer, the engine's block. Its state is *awake* or *asleep*:

- **Awake** while any 16-tile chunk of it is awake in Awake.dm's map (a connected player's camera plus 24 tiles beyond
  the 3D view, their units plus 48, their workshops plus 16, on the layer and the layers drawn above and below) or was in
  the last 60 s, or within one chunk of something on its way in (a raider, a caravan, a chasing creature: FarRecords'
  rule). So a region falls asleep a minute after the last player leaves, and wakes before anyone can see it.
- **Asleep**: its things and far-away units are records, its tiles sleep in the engine. Its land stays readable: a
  route can cross it, a claim lookup works, a world save reads it.

### What a region record holds
| Kind | Where it lives today | Asleep |
| --- | --- | --- |
| tiles: type and every own value (blocks and layers: `remaster_blocks`, `topcut`, `holes`, `dug`, `dug_top`, `roof`, `ceil`; ramps: `remaster_slope`, `slope_h`, `carve*`; trees: `HP`, `remaster_tree_max`, `remaster_tend`; ore: `remaster_ore_left/max`; roads, lifts, lairs, hoards; water and liquids as turf types, `Content3`, `isbridge`) | turf vars | engine packed record (memory); on disk, type + the values that differ from it |
| tile appearance (icon, icon_state, name, opacity, layer, dir) | the turf's appearance | the appearance (memory); its vars (disk) |
| things on the ground: items with what they hold, workshops (owner key, settings), campfires, corpses, crops and plants | movables | records like WorldSave's item records, but every var (the prototype's `MmRecord`) |
| buildings | walls, floors, bridges are turfs (above); workshops are things | as tiles / things |
| blueprints and construction sites | the player (`Player.remaster_blueprints`, `remaster_sites`, coordinates) | stay with the player; a site with workers keeps its region awake |
| claims (banners) | `obj/RemasterBanner` + `rm_banners` | the banner as a thing record, plus a claim entry (key, x, y, z, radius) in a small global index, so `RemasterClaimAt` answers without waking |
| far-away units | FarRecords.dm (with their owner, `Player.rm_far`) | as now; a region index of whose records stand in it |
| wild creatures, NPC towns | full mobs (resting asleep, Awake.dm) | FarRecords' next step (their lairs and spawners keep uids) |
| the game's lists keyed by tiles: `rm_yield_known` (turf refs), `remaster_wallwalks`, `remaster_walls` (turf refs), `rm_air_of` (gas), `rm_lair_state`, `rm_vein_hearts` (coordinates), explored maps (per player, per chunk) | global lists | coordinate keys instead of turf refs (a turf in a list never sleeps); gas only once it settles |
| time | - | "asleep since" (real time, `RemasterNow()`), for the catch-up on waking |

Measured for the lived-in arena region (4 layers of 128x128: mined columns, ramps, a road, tended and felled trees,
walls, floors, a lift, water, a lair, a dug cave hall, things, a campfire, a carpentry, a banner):

| | |
| --- | --- |
| tiles put to sleep | 65,516 of 65,536 in 4-21 ms (4 under the map's creatures, 16 held by DM lists) |
| things recorded and taken away | 68 in 43-75 ms |
| memory | its tiles' objects 16.8 MB awake, 1.6 MB of packed blocks asleep (v4) |
| woken (every tile read from DM) | 17-24 ms for the four layers; things made again in 15-18 ms |
| region file, deflated JSON | tiles 174 KB, things 0.9 KB (OpenDream's own savefile format: 23.9 MB, far too verbose for region files) |
| tiles that differ from their type | 7,223, of which ~7,000 only by the lazily worked-out caches `remaster_blocks` / `remaster_vein` (tmp: a file needs only the ~200 really changed) |

### Waking a region
Tiles wake by themselves (any read). Things are made again from their records (`MmRestore`: the type's `New()`, what
it put inside removed, the record's things put inside, every var set back, the type's own for the rest, and a
workshop's station art put back as WorldSave.dm's loader does), then units (section 4). In v1 an unloaded region's
things are frozen like its records (no rot, no growth); a later catch-up for things (crops grown, regrowth, rot by the
time away, capped at 8 hours as Away.dm) would pair with far-records' farmer catch-up.

## 4. Regions and far-away records: the contract

Agreed with far-records (`Code/Remastered/FarRecords.dm`, planning/FAR_UNIT_RECORDS.md) and the coordinator,
2026-10-24 23:1x. Two layers, two rules sets:

- **Tiles sleeping in the engine (section 2) needs no rule.** It is invisible to DM: a mob's own tile never sleeps
  (the mob holds it), and any tile anything reads wakes. Records and live units never see it.
- **Regions unloading (this section) follows four rules:**

1. **A region unloads only when every unit in it is a record, or there are none.** No live mob stands in it or within
   one 16-tile chunk of it. Counted natively from the cells' things lists, which never wakes a tile (a sleeping tile has
   no things). If a live mob comes within a chunk of an unloaded region (a raider, a caravan, a creature chasing:
   anything with a destination; resting wild creatures don't move, Awake.dm), the region loads: the same "something on
   its way" check FarRecords makes every few seconds. Wild creatures and NPC towns are live mobs until FarRecords'
   next step makes them records, so the regions they stand in stay loaded until then (their tiles still sleep).
2. **Waking order: the region first, then its records.** `Load` -> the region's things are made again from its
   records, a few ms a tick -> the region is marked loaded and the **region-loaded event** fires -> far-records wakes
   that box's records into mobs on real turfs (same identity, gear, wounds, links), in its own batches
   (`RmFarWakeOwner`, `RM_FAR_BATCH`, its tick share) -> their catch-up runs.
3. **v1: a record in an unloaded region only banks its time.** It makes no map changes unseen; it lives its time
   through on waking, after `Load`, with Away.dm's work procs on the real map (FarRecords' rule already). Its
   10-minute settle (`RmFarSettleDue`, so loose goods don't rot) skips records whose region isn't loaded: goods in an
   unloaded region are records and don't rot either. So **no change log in v1**. For v2 (regions kept on disk for days,
   the Daggerfall-scale world), records could work unseen against **per-region summaries** (trees ready, ore and
   blocks left, the stores' contents) and write an **ordered change log** (sequence number, game time, record uid,
   change: tree felled, block mined, ore taken, goods stored, field planted); `Load` applies it in order and keeps the
   last number applied, so nothing is lost or applied twice.
4. **Places by coordinates or ids, never live refs.** Records already hold tiles as `list("~T", x, y, z)`, their own
   things by index, their owner as a marker, other units by uid, a farmer's plants as "x,y,z" (FarRecords.dm). Jobs.dm
   zones by `rm_jz_id`. Region records hold coordinates; claims go in a small global index (key, x, y, z, radius) so
   `RemasterClaimAt` answers without loading anything.

### The hook map-memory provides (FarRecords.dm already calls it, guarded)
| Call | Answer |
| --- | --- |
| `rm_map_hook` (declared in FarRecords.dm) | set to map-memory's `/datum/rm_regions` at world start when regions are on; null means every tile counts as loaded (today) |
| `Loaded(x, y, z)` | 1 if that tile's region is in memory and has finished loading |
| `Load(x, y, z)` | asks for it: 1 if already loaded, else the load is queued and it returns 0 (FarRecords' `RmFarMapIn` then retries) |
| `Listen(datum/D)` | `D.RmRegionLoaded(x0, y0, x1, y1, z)` is called for each listener as soon as a region finishes loading. far-records won't use it in v1 (confirmed 23:3x): a region that loads because a player came near also wakes its chunks in Awake.dm, which is what wakes records, and its wake check retries `Loaded` every 2 s |

### Incremental loading, never a hitch
A queue, worked a few ms a tick (`RM_REGION_MS`, 4 by default; up to 20 while a connected player's camera is within
~60 tiles of the region): (1) its tiles: nothing to do while they are in memory (they wake on read); from disk later,
one ~200 KB packed block read; (2) its things made again from their records, measured 0.22-0.26 ms each (68 in
15-18 ms), so ~16 a tick at 4 ms: a region with 68 things loads in one tick, a town of 1,000 things in ~6 s at 4 ms a
tick or ~1.3 s at 20; (3) marked loaded, the event. Unloading the same way: records made and things taken away, 0.6-1.1
ms each measured (68 in 43-75 ms), ~5 a tick. A region is asked to load when a connected player's awake land (Awake.dm:
the 3D view plus 24 tiles) comes within one more chunk of it, so at 20 ms a tick it is ready before anyone can see it.

## 5. Routes over sleeping land

- In one 1000x1000 world every tile is always there (asleep or awake), so the route search works unchanged; it wakes
  what it reads, bounded by its 512-tile limit. With peek reads (2) it wakes nothing.
- Regions on disk (the Daggerfall-scale world, MMO_ARCHITECTURE.md section 11): a route into a region that isn't in
  memory loads its packed tiles (~200 KB a region in the tight layout, a few ms) without waking its things; long
  journeys use a region graph (the passable crossings on each region's edges, HPA* style) and only search tiles in the
  regions at either end and the one being walked.

## 6. World saves and the user's saves

### 6.1 Saves keep working
- `WorldSave.dm`'s file stays as it is: tiles that changed since load, things made in play, workshops, banners, siege
  engines, runes. A save reads sleeping tiles like any other code (it wakes the ones it lists; the next sweep puts them
  back), so its format and the user's existing saves are untouched. Loading is as now (map, biomes, then the save
  applied), before any tile sleeps.
- Region files are a new, separate format (one per region, `units/regions/r<x>_<y>_<z>.sav`), only for regions written
  to disk; the world save stays the source of truth until region files have been proved over many restarts.

### 6.2 Two game-side costs to fix first (the `T.vars` reads landed 2026-10-24 23:2x)
- **World-save signatures.** `RemasterTouchChunk` keeps a text signature for every tile of every 16x16 chunk a creature
  has been near (256 strings a chunk, never dropped) and reads each tile through `T.vars` (`"Supported" in T.vars`),
  which makes and keeps a vars list on each of them. On the user's world 90 s after load, 58,347 tiles already carried
  one (it grows as creatures wander, and is never dropped). Replace with a changed-since-load
  bit per tile from the engine (a saved var or the type written after load: 0.5 MB for the world), or at least read
  `T.Supported` directly (it is an atom var, Vars.dm).
- **`T.vars` reads.** `RemasterTileColor` (Explore.dm, the world map) read `Tree`, `CaveWater`, `IsWall`, `Detailed`
  through `T.vars` for every explored tile; all are atom vars, read directly as View3D.dm already does.
- **Landed** (the coordinator's OK; restore point `restore-points/before-tvars-reads-20261024`): `RemasterTurfSig` reads
  `T.Supported` and `RemasterTileColor` reads the four directly. Checked (`tests/map_memory_tvars_check.dm`, arena on
  the real land): signing 64 chunks made 16,384 vars lists the old way (+262 B a tile) and none the new way (+125 B a
  tile, the signatures alone); colouring an explored area, 1,024 and none; on all 262,144 tiles after play the old and
  new signatures and colours are the same; the world map JSON is the same on all four layers; a world save writes the
  same 456 tiles. `game/` compiles (295 warnings, as before). Still to do, outside that OK: the same reads in
  Buildings.dm (three places), and the signature lists themselves (the changed-since-load bit).

## 7. Full world estimate with N players

Measured on the user's world: the real 1000x1000x4 map with their world save (920 changed tiles), 886 creatures and
5,468 things, no client and no player units loaded (`tools/tick_profile.py --client none`, a private copy; their saves
checked unchanged). Two runs on the scratch engine: `reports/server-cost/map-memory-world` (v4) and `-world2` (v5, with
the area sets). A "player" here is a spot whose land is awake: a 181x181 box (the zoomed-out 3D view, Awake.dm's 24
tiles beyond it and a chunk more) on its layer and the two drawn above and below it, 98,010 tiles, all woken (an upper
bound: in play only what is read wakes).

| State | GC heap in use | GC committed | Process (physical footprint) |
| --- | --- | --- | --- |
| as loaded, every tile awake (today) | 1,536 MB | 1,614 MB | **2,560-2,662 MB** measured just after load; 1,843 MB measured later with the map awake |
| area sets trimmed, every tile awake | 1,461 MB | 1,476 MB | ~1.7 GB |
| every tile that can asleep | 663-730 MB | 804-832 MB | ~1.06 GB |
| asleep, area sets trimmed | 577 MB | 636 MB | ~0.87 GB |
| ... 1 player's land awake | 601 MB | 617 MB | ~0.85 GB |
| ... 4 players | 673 MB | 691 MB | ~0.92 GB |
| ... 8 players | 764 MB | 793 MB | **1,024 MB measured** |
| 4 players, then a minute of the world playing (v4, sets not trimmed) | 838 MB | 854 MB | ~1.1 GB |

The process holds ~230-260 MB outside the GC heap (footprint less committed, both runs' last samples), which is how
the estimated column is made. Each player's land costs ~21-23 MB (98,010 tiles at ~218 B) when all of it is awake.

So with sleeping tiles and trimmed area sets **a whole world with up to ~8 players' land awake fits in about 1 GB**,
from ~2.6 GB. What a real game adds and what takes it back:

| | MB |
| --- | --- |
| each player's units (200 units at 55-96 KB, UNIT_MEMORY_PLAN.md; ~10 KB after its steps 1-3) | +11-19 (+2 after) |
| each connected client's HUD and 3D state on the server | a few |
| final layout: cell arrays only for awake blocks, refs from coordinates (no ref slot, no slot map) | -80 |
| the world's 886 creatures and NPCs as records (FarRecords' next step; ~96 KB each today) | -80 |
| the world save's signature lists and vars lists (6.2) | -10 to -50, growing with play today |

Eight players with 200 units each today: ~1.0 GB + ~130 MB, and with the final layout and the creatures as records
back to ~0.9-1.0 GB. Beyond that, worlds grow by players' land (~21 MB each) and units, not by the map.

## 8. What to build first

0. **Engine, on its own and first: trim the areas' turf sets** once the map has loaded (`HashSet.TrimExcess` on every
   area). The world's default area held all 4 million turfs while the levels were made and kept the room: on the
   user's world the sets had room for 8.5 million turfs (171 MB); trimmed, 4.5 million (91 MB), and the heap in use
   fell 75 MB with every tile awake. No behaviour change; one line in the map loader.
1. **Engine: sleeping tiles** (the prototype's patch with its v4 layout, then refs from coordinates and cell arrays per
   awake block, peek reads for RmWalk/route search and view/range), behind `RM_COMPACT_TILES`, in the same engine build
   as formations' v6, the area sets trimmed as tiles sleep. Proof: this arena test (all passing), the one-second sweep
   over the obey checks (done: 32/32 the same), then the clip, formation, breaking and gather checks the same way, and
   the world run (done on the scratch engine: 2.56 GB -> 1.02 GB with 8 players' land awake).
2. **Game: the sweep** in Awake.dm (sleep chunks a minute after they fall out of the awake map), and the rest of 6.2
   (the `T.vars` reads in WorldSave.dm and Explore.dm are done). These need no new save format.
3. **Regions for things**: records for things on the ground of an asleep region, the claim index, coordinate keys for
   the tile-keyed lists, the catch-up. Then wild creatures as records (FarRecords' next step).
4. **Region files and generated regions** (MMO_ARCHITECTURE.md section 11): regions on disk, the region graph for long
   routes, regions generated from a seed.

## 9. Wiring it into game/ (the plan; each step its own restore point and checks, the coordinator's OK first)

**Step A, engine (one build, with formations' v6):**
1. After the map loads, `TrimExcess` every area's turf set (DreamMapManager, end of `InitializeAtoms`). Checks: the
   arena's area-set numbers, obey and clip unchanged.
2. Sleeping tiles: `compact_patch.py` + `DreamMapManager.RmTiles.cs` become a block of `tools/build_runtime.py` (on in
   the build; at run time `RM_COMPACT_TILES=0` makes `rm_tiles_sleep` only count); the natives go to
   `engine/native/RmTiles.cs` (`rm_tiles_sleep`, `rm_tiles_wake`, `rm_tiles_count`, `rm_tiles_stats`, `rm_area_sets`;
   `rm_heap_info`, `rm_turf_census`, `rm_now_ms` for tests), native version 6. Sets trimmed as tiles sleep.
3. Later (v7): peek reads for RmWalk/route search and range/view, a mob count in a box without waking
   (`rm_region_mobs`), refs from coordinates, cell arrays per awake block.

**Step B, game, the tile sweep (no new save format):**
1. `Code/Remastered/Native.dm`: the natives' declarations with DM fallbacks (null / 0: an old engine sweeps nothing).
2. `Code/Remastered/Regions.dm` (new, included after Awake.dm and FarRecords.dm): a switch `rm_regions_on`; every
   10 s, chunks out of Awake.dm's map for 60 s go to `rm_tiles_sleep`, at most one 128x128 block's worth a tick (3-6 ms);
   `rm_map_hook` set to `/datum/rm_regions` whose `Loaded` answers 1 everywhere until step C (regions never unload yet),
   `Load` 1, `Listen` kept.
3. Awake.dm (server-cost's file): a "chunk last awake at" list beside `rm_awake`, for the sweep. A few lines.
4. Checks: `tests/map_memory_test.dm` (arena), the one-second sweep (`tests/map_memory_sweep.dm`) over obey, then the
   same over clip, formation, breaking and gather, and one full-world run (`tests/map_memory_world2.dm`).

**Status 10-25 09:1x: steps A.2 and B built and checked, staged for the OKs** (`reports/map-memory/staged/engine-v10/`,
engine v10 = installed v8c + COMPACT, native version 10, sha256 `8a0148b5...`; game side `staged/game/game_side.py`).
As built, the sweep looks at 64 chunks of Awake.dm's map every tick (a 4-million-tile world in ~25 s) and stops for the
tick at 60% tick use. Every B.4 check passed or failed exactly as on v8 (obey's 6 chop cases, breaking's 8 mining/tree
cases fail on v8 too); the full world went 1,843 -> 937 MB footprint, 1,494 -> 593 MB live heap. Found on the way: the
gather test's stone numbers move with server time per tick (4 ms of plain busy work a tick does what the test-mode sweep
does), not with sleeping; a jobs finding. The proof table is the package README.

**Step C, game, regions for things:**
1. Regions.dm: unload a region when rule 1 holds and none of its chunks (or the chunk round it) was awake for 60 s:
   its things to records (the prototype's `MmRecord`/`MmRestore`, workshop art, banners into a claim index), kept per
   region in memory; incremental load/unload with the event; `Loaded`/`Load` for real.
2. WorldSave.dm: things in region records are saved from the records (a "regions" key in the same world save file),
   not from the ground loop, so nothing is written twice; an old save has no "regions" key and loads as today.
3. FarRecords.dm (far-records): optional `Listen` registration to wake a region's records on its event.
4. Checks: the arena round trip (byte-identical), a region unloaded with records in it, game time passed at speed 4,
   loaded back: tiles, things and records as a fully loaded run within far-records' calibration margin.

**Step D, later:** wild creatures and NPC towns as records (FarRecords' next step), then regions on disk and generated
regions (MMO_ARCHITECTURE.md section 11), with v2's summaries and change log if records must work unseen for long.

