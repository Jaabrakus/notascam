# Regions on disk: the plan (load-asleep-1030, 10-31)

The owner, 10-31: "Yes, plan it." Plan only; nothing is built. It builds on `planning/MAP_MEMORY.md` (sections 3-4: what a
region holds, waking, the far-records contract) and `planning/WORLDGEN_PLAN_2026-10-27.md` (steps 2-3: hex regions near
players, save only what players change). Measured on the native server's heap (real app, 07:15 build, engine G7, one
player, `lsArmB`; exact totals with the scratchpad `gcpath` tool).

## In short

- **On today's map, regions on disk saves little: ~20-30 MB.** Tile sleeping (engine G3-G5) already shrank the map's
  part of the server to ~45 MB of its 227 MB of live data. A far tile's tables are only ~6 bytes now (10 with the
  reach map).
- **For the big world it is the whole game.** Seed 1026 is 16,384 x 16,384 tiles x 4 layers, 1.07 billion tiles (268 of
  today's maps). At today's ~10 bytes a tile for the tables every tile keeps (sleep kind, area, flags, reach map) that is
  **~11 GB** before anyone plays, and the map file would run to gigabytes. With regions on disk, memory follows where players
  are, not how big the world is.
- **Bigger cuts today come from three small fixes (step A): ~30-45 MB, days of work, no save change.** The biggest is
  the world save's own memory of how explored land first looked: ~13 MB after a short game and growing with every
  area explored, up to hundreds of MB in a long-lived world. That one is a bug-sized fix.
- **Recommended order:** step A now (memory today), then regions R1-R4 as the first stage of the big world, with the
  worldgen and reach-map sessions. R3 changes the save format and needs the owner's OK first.

## What the server holds today (live data, 227 MB)

| part | MB | grows with |
|---|---:|---|
| type definitions, compiled game code, strings of the type tree | ~25 | nothing (fixed) |
| **generated icon images** (icon operations' results, ImageSharp) | 26 | icons made in play |
| **pooled byte buffers** (.NET's shared array pool: network, compression) | 21 | busy moments |
| **explored land's first look** (`remaster_chunks`, WorldSave.dm: 106,240 signature strings) | 13 | every 16x16 area anyone reaches |
| awake tiles near the player (77,463 turfs, their cells, lists, values) | ~20 | players and their spread |
| **the reach map's route labels** (one 4-byte number a tile, 3 levels; RmReach.cs) | 11.4 | world size |
| sleeping tiles' kinds (2 bytes a tile) | 8.0 | world size |
| proc state pool (capped, G) | 8 | nothing (capped) |
| level byte tables and flags | 5.8 | world size |
| units' own values, DM lists, the rest | ~90 | units, game state |

With its tile kinds, marks and queue the reach map is ~21 MB, and it grows with world size too.

## Step A: three small fixes for today (days, no save change)

**Done 10-31** (the owner: "Yes, small fixes first"): "shared-looks" 08:52, engine I 09:20, "buffer-pool" 09:23; results in
`reports/load-asleep-1030/README.md` ("Step A"). Not built into the app yet.

1. **Share the first-look signatures.** `RemasterTouchChunk` stores one text per tile, e.g.
   `/turf/grass|grass|0|0|grass|0`, made fresh each time, so 106,240 copies of a few hundred distinct texts. Keep one
   copy of each text in a pool and store that: ~11 MB of the 13 freed now. A 16x16 area then costs ~4 KB, not ~32 KB,
   so a world explored end to end stays near 60 MB instead of ~500 MB. Game code only (WorldSave.dm); saves unchanged
   (`remaster_chunks` isn't saved). Also worth a look: making a signature reads all 256 tiles, which wakes them.
2. **The reach map, leaner.** (Measured later: the 11.4 MB table is the reach map's route labels, not the tiles' areas.)
   Its changed marks become a bitset and its labelling queue is made only while labelling: ~6 MB, the same answers.
3. **Generated icons and pooled buffers.** Drop generated icon images unused for some minutes and make them again
   when asked (an earlier test dropped all of them, and the game reads some back on hot paths, so keep the recent
   ones), and trim the shared buffer pool after quiet minutes: up to ~20-30 MB together. Measure each.

Checks: load fingerprints identical (`load_run.py` + `compare.py`), obey 32/32, clip 11/11, combat, a save made before
and after loads the same, a real-app memory pair (`play.py --census`).

## Step B: regions on disk (the big world's foundation)

A **region** is one hex of the generated world (WORLDGEN: ~66,500 tiles in a 320x320 box). On today's map, a 256x256
block stands in for it. Each step leaves the game playable and is checked before the next.

**R1. Levels made of regions in the engine (3-4 days).** The tables every tile has (sleep kind, area, flags, level
bytes, the cells) move from one array per level into one block per region, made only when that region exists. No game
change: today's map has every region, so it plays the same. This is what lets a level be 16,384 tiles across without
16,384 x 16,384 of anything. The turf ids by position fit the big world (1.07 billion < 2.1 billion).

**R2. Far regions unloaded (1-2 weeks, game + engine).** MAP_MEMORY's rules: a region with no player's camera, units or
workshops near it for 60 s, and every unit in it a far record, has its things recorded and its tables freed. It comes
back a few ms a tick before anyone can see it (`RM_REGION_MS`), with a bigger margin for flyers and fast movers.
Small global indexes answer without loading anything: claims, the reach map's region links, whose far records stand
where. Game lists keyed by tile refs (`rm_yield_known`, `remaster_walls`, `rm_air_of`...) move to coordinate keys.
- Limit: wild creatures are live mobs today, and a region with one in it can't unload until creatures become records
  (FarRecords' next step).
- Today's map: ~20-30 MB playing alone, more in a lived-in world (far items, workshops and corpses become records).

**R3. Region files and the save format (3-5 days; the owner's OK first).** `world/regions/<z>/<rx>_<ry>` per region:
the tiles that differ from the source (the map file now, the generator later), the things on them as records, and
"asleep since" for the catch-up. The world save writes each changed region on its own, not one big file, and a start
reads only the regions near players.
- Old saves load as today and are written as region files on the first save. Restore point first.
- Checks: a save, load, save round trip gives identical files and fingerprints, on copies only (never a player's saves).

**R3 status (10-31 22:25): first part landed** ("regions-r3"; the owner: "Yes, start R3"; gate compile + jscheck +
hudjoin + combat 32/32). `R/WorldRegions.dm`:
- Each save also writes `units/regions/r<z>_<rx>_<ry>.<save>.sav` per region holding anything (256 x 256 blocks on
  today's map): changed tiles, items, workshops, siege engines, banners and runes (these three keep their world order
  by index), the quests on its boards (`Q["region"]`), "asleep since" and a fingerprint. Plus `world.<save>.sav`, which
  holds the calendar, realms, wars, the quests' own numbers and order (`RemasterWorldGlobals`), and each region's file.
  Records are put in order by place, so a region gives the same file whatever order the save's scan found it in.
- Only regions whose fingerprint moved are written; every file name is used once (see below), written through the
  engine's rm_later route (off the game thread). Files the last two sets don't name are let go.
- The single file is still written with the same stamp (`units/remaster_world.stamp`). A start reads the region files
  only when the newest world file is complete, carries that stamp and every file it names is there; otherwise the
  single file as before. RM_REGION_FILES=0: neither written nor read. An old save becomes region files at its next
  save.
- WorldSave.dm's save and load were split into shared pieces (`RemasterWorldGlobals` + `rm_world_global_keys`,
  `RemasterRestoreWorldThings`, `RemasterRestoreWorldGlobals`), so both ways restore with the same code.
- Checks: `tools/check_region_saves.py` (one arena world started six times on one folder: save, load from regions,
  single file only, a stale set, an old save migrated, load again; 19/19, every start the same world) and `--real`
  (the same on the real map).
- Found on the way, landed first ("world-save-close", 22:19): the single world save kept only a run's first save. The
  engine keeps a file's bytes by its path once read (fdel doesn't drop them) and an open savefile's contents by its path
  until it is deleted. The save's reused temp file therefore came back as the first save's, and fcopy copied that. It
  now goes the unit saves' way (a stand-in with rm_later, `del(S)`).
- Not yet: reading only the regions near players (needs R2), dropping the single file (after many restarts), the claim
  index for unloaded regions (R2).

**R4. Regions from the generator (with the worldgen session).** A region missing from disk is made from seed 1026 and
laid by the engine. Laying one hex from DM took ~1.2 s in the arena (10-27), too slow to do while playing; a native
loader from a packed file should take tens of ms. The reach map needs the same per-region shape (build-the-reach-map
session). Then the world's size is set by the generator, not by memory.

## Risks

- **A load hitch** when someone moves fast into an unloaded region: the wake margin grows with speed, and loads are
  spread over ticks. Checked with a run-in test that looks for gaps over 250 ms.
- **Many players spread out** keep many regions awake: memory follows the players (MAP_MEMORY measured ~21 MB of
  awake land per player).
- **Refs to tiles in game lists** stop a region unloading, or break when it does: R2 moves them to coordinates first.
- **Save format (R3):** a mistake there loses land changes. Round-trip checks and the old loader stay until it's proven.

## Decisions for the owner

1. **Order:** step A first (recommended: ~30-45 MB now, days), or straight to regions?
2. **R3's save format:** one file per region as above (OK before R3 starts).
3. **When the big world starts:** R4 joins WORLDGEN step 2. Today's map in the middle as the old heartland, or all
   new (WORLDGEN's open question)?
