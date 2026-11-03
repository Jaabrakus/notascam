// Map memory, step B (planning/MAP_MEMORY.md sections 2 and 9): the tiles of land nobody is near sleep in the engine.
// Engine version 10 (RmTiles.cs, the COMPACT patch) keeps a tile that only its cell holds (no unit or thing on it, no DM
// value pointing at it, only plain values of its own) as a packed record, ~52 bytes instead of ~286, and wakes it on
// any read with the same ref, values, look and area, so the game can't tell. This sweep puts to sleep the tiles of each
// 16-tile chunk Awake.dm hasn't had awake for rm_regions_quiet; reading them again (a route, the 3D view, a walker, the
// world save) wakes what is read, and a later pass puts it back.
//   rm_regions_on = 0     nothing is put to sleep (every tile stays awake, as before); RM_REGIONS=0 in the server's
//                         environment does the same, and so does an engine older than version 10
//   RM_COMPACT_TILES=0    the engine's own switch: nothing sleeps either (rm_tiles_sleep only counts)
//   RM_REGIONS_TEST=1     checks: a pass over the whole map every second, any chunk not awake now, from 2 s after start
//   RM_LOAD_SLEEP=0       no load pass (rm_regions_load_sleep = 0): the sweep alone puts the map to sleep, as before
// The load pass (2026-10-26, devlog/2026-10-26/memgc.md): the map is built with every tile awake, and waiting a minute
// and more for the sweep let those ~3.9 million tiles' objects age into the collector's oldest generation, whose room it
// kept once they slept: 2.5 GB held for 0.78 GB of live data with 200 units. So the moment the world has loaded, every
// tile that can sleep does, the areas' turf sets are trimmed, and one full compacting collection hands the room back.
// Since 10-30 the engine builds the map asleep, a level at a time (load-asleep, reports/load-asleep-1030; RM_LOAD_ASLEEP=0
// in the server's environment builds it awake, as before): the load pass finds only the ~0.2 million tiles the world's
// start woke, and still trims the area sets and compacts.
// The engine also makes one definition per map object, not one per tile it is placed on, lets the load's tile queue
// go and caps its proc-state pool (map-defs, reports/load-asleep-1030): the live heap after the load 817 -> 538 MB.
// Engine G3 (10-30 22:17): turf refs by position, a sleeping tile is one 2-byte kind, pools capped, and the hidden 2D
// map's tiles only in the chunks around each player's mob (RM_NEAR_TILES=0 keeps every tile).
// Engine G5 (10-30 23:55): a level's cells are kept in 16x16 blocks only where a tile is awake (was 8 bytes every tile).
// Engine G6 (10-31 02:30): the tick GC compacts gen2 once it is left full of holes (RM_GC_DEFRAG_MB=0 never does).
// Engine G7 (10-31 07:44): libbyond (call_ext's byondapi, x86-64 only) is optional, so the server runs on Apple silicon.
// Engine I (10-31 09:20): icons' decoded images unused for 5 minutes are let go (RM_ICON_IDLE_S), the reach map is leaner.
// Engine J2 (10-31 11:19): browser players share one copy of the HUD page (each kept two, ~9.7 MB a player).
// Engine K2 (10-31 13:0x): a per-chunk counter of the things on turfs (rm_chunk_things_ver), for scans that keep answers.
// Engine L (10-31 14:0x): natives let go of the lists they put inside lists (the 3D move rows leaked two a tick for
// every player in 3D, ~20 a second each, held only by the engine; routes, formations, foe pools too).
// Engine L2g (10-31 14:18): L rebuilt with guest mode's browser lobby (engine/web), which L's first build left out.
// Engine M (10-31 18:18): own-variable entries at exactly their type's default let go once a minute, tables trimmed,
// first tables smaller (RmPools.VarTrim; RM_VAR_TRIM=0 off): at 100 players those tables 82.8 -> 54.6 MB.
// Engine M2 (10-31 19:04): a write of exactly the default to a name with no own entry stores nothing and is no change
// (after M's trim such a write moved the change counters; found by the u5-hud session).
// Engine gc-hold (10-31 23:10, the owner: "Yes, hold it"): G6's compaction waits while any player is connected and runs
// once the world is empty (it froze the server 0.36-0.5 s with 10 players on; ~400 MB more stays committed meanwhile).
// RM_GC_DEFRAG_PLAYERS=1 in the server's environment: as before.
// Regions themselves (a region's things kept as records, Loaded/Load for real, section 4) are step C. Until then
// rm_map_hook (FarRecords.dm) says every region is loaded, as FarRecords.dm takes it when the hook is null.

var/rm_regions_on = 1
var/rm_regions_test = 0
var/rm_regions_load_sleep = 1     // the load pass: the whole map to sleep and one compacting collection once the world has loaded
var/rm_regions_quiet = 600        // ticks a chunk is out of Awake.dm's map before its tiles sleep (a minute)
var/rm_regions_start = 600        // ticks after the world is ready before the first pass
var/rm_regions_chunks = 64        // chunks looked at a tick (16,384 tiles): the first pass ~1-6 ms a tick, a null check a tile after
var/rm_regions_trim = 100000      // tiles put to sleep between trims of the areas' turf sets (they keep their room)
var/rm_regions_next = 0           // the next chunk the sweep looks at
var/rm_regions_slept = 0          // tiles put to sleep since the last trim
var/rm_regions_passes = 0         // passes over the whole map so far
var/datum/rm_regions/rm_regions

// Map memory's side of the region contract with FarRecords.dm (rm_map_hook, planning/MAP_MEMORY.md section 4).
/datum/rm_regions
	var/list/listeners = list()

// Is x, y, z's region in memory and loaded? (Every region, until step C.)
/datum/rm_regions/proc/Loaded(x, y, z)
	return 1

// Asks for x, y, z's region: 1 if it is loaded, else 0 and it is queued (step C loads over ticks).
/datum/rm_regions/proc/Load(x, y, z)
	return 1

// D.RmRegionLoaded(x0, y0, x1, y1, z) is called when a region finishes loading (from step C).
/datum/rm_regions/proc/Listen(datum/D)
	if(D && !(D in listeners)) listeners += D

// world/New: this file's part is step RmChainWorldNew_Regions in Code/Remastered/Chains/WorldNew.dm

proc/RmRegionsLoop()
	while(!remaster_world_ready && !rm_regions_test) sleep(1)
	if(rm_reach) RmReachBuild()   // the reach map (it reads sleeping tiles from their records: Native.dm, navigation plan N1)
	if(rm_regions_on && rm_regions_load_sleep && !rm_regions_test) RmRegionsLoadSleep()
	sleep(rm_regions_start)
	while(1)
		if(rm_reach_built) RmReachTick()   // first: the tiles it marked are read again before any can sleep
		if(rm_regions_on) RmRegionsTick()
		sleep(1)

// The load pass: every level's tiles that can sleep, the areas' turf sets trimmed, then one full compacting collection
// (rm_heap_info). One long tick, once, before players are about; the sweep takes over a minute later.
proc/RmRegionsLoadSleep()
	var/u0 = world.tick_usage
	var/slept = 0
	for(var/z = 1, z <= world.maxz, z++) slept += rm_tiles_sleep_box(1, 1, world.maxx, world.maxy, z)
	rm_area_sets(1)
	var/u1 = world.tick_usage
	var/heap = rm_heap_info()
	world.log << "Remastered: load pass put [slept] tiles to sleep in [round((u1 - u0) * world.tick_lag)] ms, heap compacted in [round((world.tick_usage - u1) * world.tick_lag)] ms ([heap])"

// One tick of the sweep: the next chunks of Awake.dm's map, in its order (layer by layer, row by row). It reads the one
// "behind" signal (planning/SYSTEMS_MAP.md Part 6 step 5): none at all while the server is well behind (Shed.dm level 2
// and up), and each chunk only while the tick ledger has optional room (Spread.dm RmTickRoom), what it took charged.
proc/RmRegionsTick()
	if(world.time - rm_awake_at >= 10) RmAwakeRefresh()
	if(rm_shed_level >= 2) return
	var/n = length(rm_awake)
	if(!n || length(rm_awake_last) != n) return
	var/w = rm_awake_w
	var/h = rm_awake_h
	var/look = rm_regions_test ? max(rm_regions_chunks, round(n / 10) + 1) : rm_regions_chunks
	for(var/k = 1, k <= look, k++)
		if(RmTickRoom() <= 0) return
		if(++rm_regions_next > n)
			rm_regions_next = 1
			rm_regions_passes++
			if(rm_regions_test && rm_regions_passes % 10 == 1) world.log << "CK|note|regions: [rm_regions_passes] passes, [rm_tiles_stats()]"
			if(rm_regions_slept >= rm_regions_trim && (!rm_shed_level || RmTickRoom() > 0))   // else at a later pass's end
				var/u1 = world.tick_usage
				rm_area_sets(1)
				RmTickCharge((world.tick_usage - u1) * world.tick_lag)
				rm_regions_slept = 0
		var/i = rm_regions_next
		if(rm_awake[i]) continue
		var/t = rm_awake_last[i]
		if(!isnull(t) && world.time - t < rm_regions_quiet) continue
		var/c = i - 1
		var/cx = c % w
		c = (c - cx) / w
		var/cy = c % h
		var/z = (c - cy) / h + 1
		var/u0 = world.tick_usage
		rm_regions_slept += rm_tiles_sleep_box(cx * RM_AWAKE_CHUNK + 1, cy * RM_AWAKE_CHUNK + 1, (cx + 1) * RM_AWAKE_CHUNK, (cy + 1) * RM_AWAKE_CHUNK, z)
		RmTickCharge((world.tick_usage - u0) * world.tick_lag)
