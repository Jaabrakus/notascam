// World saving (Remastered). The map is 4 layers of 1000x1000 tiles loaded
// from the map files at startup, so only what players change is saved:
//  - tiles that differ from how the map started, in areas player units have
//    visited (built walls, floors, bridges, dug tunnels, felled trees);
//  - items and workshops created during play that sit on the ground
//    (stockpiles, dropped gear, furniture, workshops), with their contents;
//  - the calendar and land history.
// It runs from SaveUnits(), so it saves whenever the army does: the game's
// autosave and the engine's save on quit. Owners are stored by player key,
// never as object links (saving a link to a Player would copy the player).

#define REMASTER_WORLD_SAVE "units/remaster_world.sav"
#define REMASTER_CHUNK 16
#define RM_WORLD_STAMP "units/remaster_world.stamp"   // the last save's stamp: region files with it are its set (WorldRegions.dm)

var/remaster_world_ready = 0
var/list/remaster_chunks = list()        // "cx,cy,z" -> the pristine tiles' looks (RemasterTouchChunk, RmFirstLook)
var/list/remaster_dirty_turfs = list()   // "x,y,z" -> 1 for tiles restored from the save
var/list/remaster_map_items = list()     // items that came with the map (seen when an area is first visited)
var/list/remaster_map_shops = list()     // workshops that came with the map

obj/Items/var/remaster_runtime = 0
obj/Items/var/remaster_owner_key
mob/WorkShops/var/remaster_runtime = 0
mob/WorkShops/var/remaster_owner_key

var/remaster_repopping = 0
// The season change repopulates map objects; those are map items, not ones
// made during play (otherwise every restart would add another copy).
world/Repop()
	// Whatever Repop adds is map content: remember it as such, so it is never
	// saved as "made during play" (some item types skip the New() marker).
	var/list/before = list()
	for(var/obj/Items/I in world) before[I] = 1
	for(var/mob/WorkShops/W in world) before[W] = 1
	remaster_repopping = 1
	. = ..()
	remaster_repopping = 0
	for(var/obj/Items/I in world) if(!before[I])
		I.remaster_runtime = 0
		remaster_map_items[I] = 1
	for(var/mob/WorkShops/W in world) if(!before[W])
		W.remaster_runtime = 0
		remaster_map_shops[W] = 1

obj/Items/New()
	. = ..()
	if(remaster_world_ready && !remaster_repopping) remaster_runtime = 1
mob/WorkShops/New()
	. = ..()
	if(remaster_world_ready && !remaster_repopping) remaster_runtime = 1

// Changes away from your units: remember every area a creature is in (monsters
// breaking walls, fire spreading start next to someone), and treat any tile
// the game replaces during play as changed wherever it is.
var/remaster_creature_sweep_at = 0
proc/RemasterTouchCreatures()
	if(world.time < remaster_creature_sweep_at) return
	remaster_creature_sweep_at = world.time + 50
	// At most 20 new areas per sweep, so the first sweep doesn't stall the game.
	var/fresh = 0
	for(var/mob/Monsters/M in world) if(isturf(M.loc) && !M.Critter)
		var/key = "[round((M.x - 1) / REMASTER_CHUNK)],[round((M.y - 1) / REMASTER_CHUNK)],[M.z]"
		if(remaster_chunks[key]) continue
		RemasterTouchAround(M)
		if(++fresh >= 20) break

turf/New()
	. = ..()
	if(remaster_world_ready && !remaster_repopping) remaster_dirty_turfs["[x],[y],[z]"] = 1

// Supported is an atom var (Vars.dm), so it is read directly: ("Supported" in T.vars) made and kept a vars list on every
// tile signed (map memory, planning/MAP_MEMORY.md 6.2).
proc/RemasterTurfSig(turf/T)
	return "[T.type]|[T.icon_state]|[T.density]|[T.opacity]|[T.name]|[T.Supported]"

// Remember how a 16x16 area looked before anyone could change it: one character a tile, its look's number (10-31,
// planning/REGIONS_ON_DISK_PLAN_2026-10-31.md step A). An area kept 256 texts of its own, ~32 KB for as long as the
// server runs; now ~0.6 KB, and an area all of one look keeps a single character.
proc/RemasterTouchChunk(cx, cy, z)
	var/key = "[cx],[cy],[z]"
	if(remaster_chunks[key]) return
	var/list/looks = list()
	var/list/codes = list()
	var/over = 0
	for(var/ty = cy * REMASTER_CHUNK + 1, ty <= (cy + 1) * REMASTER_CHUNK, ty++)
		for(var/tx = cx * REMASTER_CHUNK + 1, tx <= (cx + 1) * REMASTER_CHUNK, tx++)
			var/turf/T = locate(tx, ty, z)
			var/look = T ? RemasterTurfSig(T) : ""
			var/n = RmLookNo(look)
			if(n < 0) over = 1
			looks += look
			codes += ascii2text(32 + n)
	if(over) remaster_chunks[key] = looks   // more looks than one character each can number: kept as a list, as before
	else if(RmAllSame(codes)) remaster_chunks[key] = codes[1]
	else remaster_chunks[key] = jointext(codes, "")

// Each look kept once, numbered from 1 ("" is 0): its character is ascii2text(32 + number), below the surrogates.
var/list/rm_look_no = list()     // look -> number
var/list/rm_look_text = list()   // number -> look
proc/RmLookNo(look)
	if(!look) return 0
	var/n = rm_look_no[look]
	if(n) return n
	if(length(rm_look_text) >= 55000) return -1
	rm_look_text += look
	n = length(rm_look_text)
	rm_look_no[look] = n
	return n

// Tile i's first look in an area's record: its text of numbers (one character if all alike), or a list of looks.
proc/RmFirstLook(sigs, i)
	if(!istext(sigs)) return sigs[i]
	var/n = text2ascii(sigs, length(sigs) == 1 ? 1 : i) - 32
	return n > 0 ? rm_look_text[n] : ""

proc/RmAllSame(list/L)
	var/a = L[1]
	for(var/x in L) if(x != a) return 0
	return 1

// A unit whose span of chunks is the one it touched last time skips it: touching only ever records a chunk the first
// time (remaster_chunks is never emptied), and the track touches round every unit twice a second (server cost). The
// tile it last touched from (rm_touched_x/y/z) lets the track skip the call for one that hasn't moved since.
mob/Monsters/var/tmp/list/rm_touched_span
mob/Monsters/var/tmp/rm_touched_x = -1
mob/Monsters/var/tmp/rm_touched_y = -1
mob/Monsters/var/tmp/rm_touched_z = -1
proc/RemasterTouchAround(atom/A)
	if(!A || !A.z) return
	if(istype(A, /mob/Monsters))
		A:rm_touched_x = A.x
		A:rm_touched_y = A.y
		A:rm_touched_z = A.z
	var/x0 = round((A.x - 4) / REMASTER_CHUNK)
	var/x1 = round((A.x + 2) / REMASTER_CHUNK)
	var/y0 = round((A.y - 4) / REMASTER_CHUNK)
	var/y1 = round((A.y + 2) / REMASTER_CHUNK)
	var/list/span = istype(A, /mob/Monsters) ? A:rm_touched_span : null
	if(span && span[1] == x0 && span[2] == x1 && span[3] == y0 && span[4] == y1 && span[5] == A.z) return
	for(var/cy = y0, cy <= y1, cy++)
		for(var/cx = x0, cx <= x1, cx++)
			if(cx >= 0 && cy >= 0) RemasterTouchChunk(cx, cy, A.z)
	if(istype(A, /mob/Monsters)) A:rm_touched_span = list(x0, x1, y0, y1, A.z)

// Changed during play: replaced or restored from the save, or no longer what its area looked like when
// first seen. Walls and fields that came with the map (ruins, NPC towns) are not.
proc/RemasterTileChanged(turf/T)
	if(remaster_dirty_turfs["[T.x],[T.y],[T.z]"]) return 1
	var/sigs = remaster_chunks["[round((T.x - 1) / REMASTER_CHUNK)],[round((T.y - 1) / REMASTER_CHUNK)],[T.z]"]
	if(!sigs) return 0
	return RmFirstLook(sigs, ((T.y - 1) % REMASTER_CHUNK) * REMASTER_CHUNK + ((T.x - 1) % REMASTER_CHUNK) + 1) != RemasterTurfSig(T)

var/list/remaster_turf_skip = list("x","y","z","loc","contents","type","parent_type","vars","verbs","overlays","underlays",
	"vis_contents","vis_locs","appearance","area","filters","transform","key","ckey","client","group","tag")

proc/RemasterTurfRecord(turf/T)
	var/list/V = list()
	for(var/v in T.vars)
		if(v in remaster_turf_skip) continue
		var/val = T.vars[v]
		if(v == "icon")
			if(val != initial(T.vars[v])) V[v] = "[val]"
			continue
		if(!(isnum(val) || istext(val) || isnull(val) || ispath(val))) continue
		if(val == initial(T.vars[v])) continue
		V[v] = val
	return list(T.x, T.y, T.z, "[T.type]", V)

proc/RemasterWorldOwnerKey(atom/A)
	if(!("Owner" in A.vars)) return null
	var/mob/O = A.vars["Owner"]
	if(ismob(O)) return O.key
	return ("remaster_owner_key" in A.vars) ? A.vars["remaster_owner_key"] : null

// Simple settings of a workshop (numbers and text that differ from the type).
proc/RemasterSimpleVars(atom/A)
	var/list/V = list()
	for(var/v in A.vars)
		if(v in remaster_turf_skip) continue
		var/val = A.vars[v]
		if(v == "icon")
			if(val != initial(A.vars[v])) V[v] = isnull(val) ? null : "[val]"
			continue
		if(!(isnum(val) || istext(val) || ispath(val) || isnull(val))) continue
		if(val == initial(A.vars[v])) continue
		V[v] = val
	return V

// Apply saved simple vars; icons come back from the game's own files.
proc/RemasterApplyVars(atom/A, list/V)
	for(var/v in V)
		if(!(v in A.vars)) continue
		if(v == "icon")
			if(isnull(V[v])) A.icon = null
			else if(fexists(V[v])) A.icon = file(V[v])
			else if(fexists("Icons/[V[v]]")) A.icon = file("Icons/[V[v]]")
			continue
		A.vars[v] = V[v]

// The station art the original Create procs add to the left half.
proc/RemasterWorkshopOverlay(mob/WorkShops/W)
	var/path = "[W.type]"
	if(!findtext(path, "/Left")) return
	var/list/art = list("Carpentry"=/obj/WSoverlays/Carpentry, "Forge"=/obj/WSoverlays/Forge, "Smelters"=/obj/WSoverlays/Smelter,
		"Kitchen"=/obj/WSoverlays/Kitchen, "LeatherWorks"=/obj/WSoverlays/Leather, "BoneCraft"=/obj/WSoverlays/Bone,
		"Masonary"=/obj/WSoverlays/Masonary, "GemCutter"=/obj/WSoverlays/Gem, "Melter"=/obj/WSoverlays/Forge,
		"PoisonStation"=/obj/WSoverlays/Poison, "PotionStation"=/obj/WSoverlays/Poison)
	for(var/k in art) if(findtext(path, "/[k]/"))
		W.overlays += art[k]
		return

// Items are saved as records (type, simple settings, owner key, contents),
// never as whole objects: the engine's saver follows links like loc/contents
// back and forth, and an object graph could also pull in units or players.
proc/RemasterItemRecord(obj/Items/I)
	var/list/inner = list()
	for(var/obj/Items/X in I.contents) inner += list(RemasterItemRecord(X))
	return list("[I.type]", RemasterSimpleVars(I), RemasterWorldOwnerKey(I), inner)

proc/RemasterItemRestore(list/R, atom/where)
	var/path = text2path(R[1])
	if(!path || !where) return null
	var/obj/Items/I = new path(where)
	RemasterApplyVars(I, R[2])
	I.remaster_runtime = 1
	I.remaster_owner_key = R[3]
	for(var/list/C in R[4]) RemasterItemRestore(C, I)
	return I

// turfs: the changed tiles' records when the spread save (RmSaveUnitsSpread, below) has made them; else made here.
proc/RemasterSaveWorld(list/turfs)
	RemasterTidyUnitLists()
	if(!remaster_world_ready) return 0 // never overwrite the save with a half-loaded world
	if(!islist(turfs)) turfs = RmSaveScan()
	// Things made during play that sit on the ground.
	var/list/things = list()
	// Items on the ground that were made or dropped during play: anything that
	// was not on the map when the world loaded (RemasterLoadWorld lists those).
	for(var/obj/Items/I in world) if(isturf(I.loc))
		if(I.remaster_runtime || !remaster_map_items[I]) things += I
	var/list/shops = list()
	for(var/mob/WorkShops/W in world) if(isturf(W.loc) && (W.remaster_runtime || !remaster_map_shops[W]))
		shops += list(list("[W.type]", W.x, W.y, W.z, RemasterWorldOwnerKey(W), RemasterSimpleVars(W)))
	var/list/G = RemasterWorldGlobals()
	var/list/siege = RemasterSiegeRecords()       // siege engines (Siege.dm)
	var/list/banners = RemasterBannerRecords()    // realm claims (Claims.dm)
	var/list/runes = RemasterRuneRecords()        // rune pieces (Runes.dm)
	var/list/items = list()
	for(var/obj/Items/I in things) items += list(list(I.x, I.y, I.z, RemasterItemRecord(I)))
	var/stamp = "[RemasterIdStamp()]-[rand(1000, 9999)]"   // this save's: the region files written with it go with this file
	// Written as the unit saves are (engine/save RmSaveLater.cs): to a fresh stand-in file that, once closed (del below),
	// the engine writes to the save itself (a temp file, then a swap, so a crash mid-save never leaves an empty world) and
	// lets go. A temp file of our own, opened again by the same name each save, came back as the first save's (the engine
	// keeps a file's contents by its path), so every save after a run's first wrote the first one's world again (10-31).
	var/stand_in = REMASTER_WORLD_SAVE + ".new"
	fdel(stand_in)
	var/savefile/S = new(stand_in)
	S.rm_later = REMASTER_WORLD_SAVE
	S["version"] << 1
	S["stamp"] << stamp
	S["turfs"] << turfs
	for(var/k in G) S[k] << G[k]               // the calendar, realms, wars, quests, moderation (RemasterWorldGlobals)
	S["shops"] << shops
	S["siege"] << siege
	S["banners"] << banners
	S["runes"] << runes
	S["items"] << items
	S["complete"] << 1
	// Keep three backups: .bak (newest), .bak2, .bak3 -- turned over before the new save goes in.
	if(fexists(REMASTER_WORLD_SAVE))
		fdel(REMASTER_WORLD_SAVE + ".bak3")
		if(fexists(REMASTER_WORLD_SAVE + ".bak2")) fcopy(REMASTER_WORLD_SAVE + ".bak2", REMASTER_WORLD_SAVE + ".bak3")
		fdel(REMASTER_WORLD_SAVE + ".bak2")
		if(fexists(REMASTER_WORLD_SAVE + ".bak")) fcopy(REMASTER_WORLD_SAVE + ".bak", REMASTER_WORLD_SAVE + ".bak2")
		fdel(REMASTER_WORLD_SAVE + ".bak")
		fcopy(REMASTER_WORLD_SAVE, REMASTER_WORLD_SAVE + ".bak")
	del(S)   // closed: the engine writes it to REMASTER_WORLD_SAVE
	fdel(REMASTER_WORLD_SAVE + ".tmp")   // the temp file of saves before 10-31, if one was left
	fdel(RM_WORLD_STAMP)   // text2file adds to a file: start it afresh
	text2file(stamp, RM_WORLD_STAMP)
	RmRegionsSave(turfs, shops, siege, banners, runes, items, G, stamp)   // the same as a file a region (WorldRegions.dm)
	remaster_last_save = RemasterNow()
	return length(turfs) + length(items) + length(shops)

// The world-wide values a save keeps, by their names in the save: the single file has each under its name, the region
// files' world file all of them (WorldRegions.dm). A value added here is restored in RemasterRestoreWorldGlobals and
// named in rm_world_global_keys (the names the single file is read by).
var/list/rm_world_global_keys = list("Date", "Ages", "Season", "Difficulty", "Fog", "Lieges", "Lairs", "Wars", "WarClock", "WorldName", "History", "Quests", "Moderation")
proc/RemasterWorldGlobals()
	return list("Date"=Date, "Ages"=Ages, "Season"=Season,
		"Difficulty"=remaster_difficulty,
		"Fog"=remaster_fog,               // the host's fog of war setting (Fog.dm)
		"Lieges"=rm_lieges, "Lairs"=rm_lair_state, "Wars"=rm_wars, "WarClock"=rm_war_now,
		"WorldName"=WorldName, "History"=History,
		"Quests"=RmQuestSaveData(),       // player-made quests (Quests.dm)
		"Moderation"=RmModSaveData(),     // the admin staff, mutes, posting bans, reports (Moderation.dm)
		"Bugs"=RmBugSaveData())           // bug reports and error rows (Bugs.dm)

// The world's facts for the launcher's world list (mac-app/LauncherWorlds.h; the world list, 10-31): world-info.json
// next to the saves, a few hundred bytes, so the launcher never opens the big saves: the land's name, season, year and
// age, and each player's company (race and size). Written after every SaveUnits (the autosave, the save on quit) with
// the companies it saved; players not online keep their last entry. The old file is read once a run (the engine keeps
// a file's first read). Never stops a save: anything wrong only leaves the file as it was. Returns the text written.
var/list/rm_world_info_players
proc/RmWorldInfo(list/saved)
	try
		if(!rm_world_info_players) rm_world_info_players = RmWorldInfoPlayers()
		for(var/mob/M in saved) if(M.ckey)
			rm_world_info_players[M.ckey] = list("key" = M.key, "race" = M.Race, "units" = length(M.UnitList))
		. = json_encode(list("version" = 1, "name" = WorldName, "season" = Season, "year" = Date, "age" = Ages, "players" = rm_world_info_players))
		fdel("world-info.json")   // text2file adds to a file, as in BYOND: start it afresh
		text2file(., "world-info.json")
	catch(var/exception/e)
		world.log << "Remastered: world-info.json not written: [e.name]"
		. = null

// The players in the last world-info.json (an empty list when there is none or it is broken).
proc/RmWorldInfoPlayers()
	. = list()
	if(!fexists("world-info.json")) return
	var/list/old
	try
		old = json_decode(file2text("world-info.json"))
	catch
		old = null
	if(islist(old) && islist(old["players"])) . = old["players"]

proc/RemasterLoadWorld()
	// Biomes first, so the saved world (digs, buildings) is restored on top of them
	// and biome tiles never count as player changes (Biomes.dm).
	RemasterPlaceBiomes()
	// Everything lying about now came with the map (map files, seasonal repop,
	// biomes). Whatever appears later is saved, including types whose New()
	// never reaches the markers above (ores, food, bodies, campfires).
	for(var/obj/Items/I in world) if(!I.remaster_runtime) remaster_map_items[I] = 1
	for(var/mob/WorkShops/W in world) if(!W.remaster_runtime) remaster_map_shops[W] = 1
	var/from_regions = RmRegionsLoad()   // the region files when they are the last save's whole set (WorldRegions.dm)
	if(!isnull(from_regions)) return from_regions
	var/path = REMASTER_WORLD_SAVE
	if(!fexists(path) && fexists(REMASTER_WORLD_SAVE + ".bak")) path = REMASTER_WORLD_SAVE + ".bak"
	if(!fexists(path))
		remaster_world_ready = 1
		return 0
	var/savefile/S = new(path)
	var/complete
	S["complete"] >> complete
	if(!complete && fexists(REMASTER_WORLD_SAVE + ".bak") && path != REMASTER_WORLD_SAVE + ".bak")
		world.log << "Remastered: world save incomplete, using the backup"
		S = new(REMASTER_WORLD_SAVE + ".bak")
	var/list/turfs
	S["turfs"] >> turfs
	var/list/shops
	S["shops"] >> shops
	var/list/SE
	S["siege"] >> SE
	var/list/BN
	S["banners"] >> BN
	var/list/RN
	S["runes"] >> RN
	var/list/items
	S["items"] >> items
	var/list/R = RemasterRestoreWorldThings(turfs, shops, SE, BN, RN, items)
	var/list/G = list()
	for(var/k in rm_world_global_keys)
		var/v
		S[k] >> v
		G[k] = v
	return RemasterRestoreWorldGlobals(G, R[1], R[2])

// A save's tiles and things back on the map (the single file's lists, or the region files' put together):
// list(restored, unreadable).
proc/RemasterRestoreWorldThings(list/turfs, list/shops, list/SE, list/BN, list/RN, list/items)
	var/restored = 0
	var/bad = 0
	if(turfs) for(var/list/R in turfs)
		try
			var/turf/T = locate(R[1], R[2], R[3])
			if(!T) continue
			var/tpath = text2path(R[4])
			if(tpath && T.type != tpath) T = new tpath(T)
			RemasterApplyVars(T, R[5])
			remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1
			restored++
		catch
			bad++
	if(shops) for(var/list/W in shops)
		var/path = text2path(W[1])
		var/turf/T = locate(W[2], W[3], W[4])
		if(!path || !T) continue
		try
			var/mob/WorkShops/M = new path(T)
			M.remaster_runtime = 1
			M.remaster_owner_key = W[5]
			RemasterApplyVars(M, W[6])
			RemasterWorkshopOverlay(M)
			restored++
		catch
			bad++
	if(islist(SE)) restored += RemasterSiegeRestore(SE)
	if(islist(BN)) restored += RemasterBannerRestore(BN)
	if(islist(RN)) restored += RemasterRuneRestore(RN)
	if(items) for(var/list/E in items)
		try
			if(RemasterItemRestore(E[4], locate(E[1], E[2], E[3]))) restored++
		catch
			bad++
	return list(restored, bad)

// A save's world-wide values back (RemasterWorldGlobals' names), then the world is ready.
proc/RemasterRestoreWorldGlobals(list/G, restored, bad)
	var/v
	v = G["Date"]; if(!isnull(v)) Date = v
	v = G["Ages"]; if(!isnull(v)) Ages = v
	v = G["Season"]; if(!isnull(v)) Season = v
	v = G["Difficulty"]; if(v in list("peaceful", "normal", "brutal")) remaster_difficulty = v
	v = G["Fog"]; if(!isnull(v)) remaster_fog = v ? 1 : 0
	var/list/LG = G["Lieges"]
	if(islist(LG)) rm_lieges = LG
	rm_realm_ver++   // War.dm
	var/list/LR = G["Lairs"]
	if(islist(LR)) rm_lair_state = LR
	var/list/WR = G["Wars"]
	if(islist(WR)) rm_wars = WR
	RmQuestLoadData(G["Quests"])   // player-made quests (Quests.dm)
	RmModLoadData(G["Moderation"])   // the admin staff, mutes, posting bans, reports (Moderation.dm)
	RmBugLoadData(G["Bugs"])         // bug reports and error rows (Bugs.dm)
	rm_realm_ver++   // War.dm
	v = G["WarClock"]; if(isnum(v)) rm_war_now = v
	v = G["WorldName"]; if(!isnull(v)) WorldName = v
	v = G["History"]; if(!isnull(v)) History = v
	RmGuestTidyLoaded()   // what a guest had when the world last saved (Guests.dm)
	remaster_world_ready = 1
	world.log << "Remastered: restored [restored] saved world changes[bad ? " ([bad] unreadable records skipped)" : ""]"
	return restored

// A unit deleted without dying the usual way leaves an empty slot in its
// owner's list. Drop those before SaveUnits() writes the army, so the save
// never carries them.
proc/RemasterTidyUnitLists()
	for(var/mob/M in world) if(M.key && islist(M.UnitList))
		var/list/keep = list()
		for(var/X in M.UnitList) if(X) keep += X
		if(length(keep) == length(M.UnitList)) continue
		M.UnitList.Cut()
		M.UnitList += keep

// Hand restored workshops and items back to their player when they log in.
Player/proc/RemasterClaimWorld()
	if(!key) return 0
	var/n = 0
	for(var/obj/Items/I in world) if(I.remaster_owner_key == key)
		I.Owner = src
		n++
	for(var/mob/WorkShops/W in world) if(W.remaster_owner_key == key)
		W.Owner = src
		n++
	for(var/mob/Monsters/RemasterSiege/E in rm_siege_engines) if(E.remaster_owner_key == key)
		E.Owner = src
		n++
	RmQuestOnLogin()   // coins owed by notices that came down while away (Quests.dm)
	RmModOnLogin()     // a mute still running (Moderation.dm)
	return n


// --- The autosave and the Save button spread over ticks (the spike hunt, 10-31: saving froze the server ~0.5 s every ~16
// minutes, the scan of the areas creatures have been through 276 ms of it, reports/spike-hunt). The scan and the dirty
// tiles' records go RM_SAVE_SLICE_MS a tick; then, in one tick, the tiles that changed or were dirtied meanwhile are
// recorded again and everything is written as before: the world (its items, workshops) and every player's units
// together, so nothing is saved twice. SaveUnits() with no records stays one tick: the app's save on quit waits for it to
// return. A tile that changes only its look (no dirty mark) in an area already scanned is kept by the next save.
#define RM_SAVE_SLICE_MS 8
var/rm_save_spreading = 0
// A savefile marked so is turned into text and written by the engine off the game thread when it closes (engine/save,
// RmSaveLater.cs; anything reading that file waits for it): the spread save's unit saves. The save on quit is not marked.
savefile/var/rm_later = 0

// The changed tiles' records, all in this tick (as the world save always made them).
proc/RmSaveScan()
	var/list/turfs = list()
	var/list/done = list()
	for(var/key in remaster_chunks)
		var/list/c = splittext(key, ",")
		var/cx = text2num(c[1]); var/cy = text2num(c[2]); var/cz = text2num(c[3])
		var/sigs = remaster_chunks[key]
		var/i = 0
		for(var/ty = cy * REMASTER_CHUNK + 1, ty <= (cy + 1) * REMASTER_CHUNK, ty++)
			for(var/tx = cx * REMASTER_CHUNK + 1, tx <= (cx + 1) * REMASTER_CHUNK, tx++)
				i++
				var/turf/T = locate(tx, ty, cz)
				if(!T) continue
				var/tkey = "[tx],[ty],[cz]"
				if(RmFirstLook(sigs, i) == RemasterTurfSig(T) && !remaster_dirty_turfs[tkey]) continue
				turfs += list(RemasterTurfRecord(T))
				done[tkey] = 1
	for(var/tkey in remaster_dirty_turfs) if(!done[tkey])
		var/list/c = splittext(tkey, ",")
		var/turf/T = locate(text2num(c[1]), text2num(c[2]), text2num(c[3]))
		if(T) turfs += list(RemasterTurfRecord(T))
	return turfs

// The same a slice a tick: list(the records, each one's tile key, each one's look then, the tiles done).
proc/RmSaveScanSpread()
	var/list/turfs = list()
	var/list/keys = list()
	var/list/looks = list()
	var/list/done = list()
	var/t0 = world.tick_usage
	for(var/key in remaster_chunks.Copy())   // an area first touched meanwhile is as it was: nothing in it to keep yet
		var/sigs = remaster_chunks[key]
		if(!sigs) continue
		var/list/c = splittext(key, ",")
		var/cx = text2num(c[1]); var/cy = text2num(c[2]); var/cz = text2num(c[3])
		var/i = 0
		for(var/ty = cy * REMASTER_CHUNK + 1, ty <= (cy + 1) * REMASTER_CHUNK, ty++)
			for(var/tx = cx * REMASTER_CHUNK + 1, tx <= (cx + 1) * REMASTER_CHUNK, tx++)
				i++
				var/turf/T = locate(tx, ty, cz)
				if(!T) continue
				var/tkey = "[tx],[ty],[cz]"
				var/look = RemasterTurfSig(T)
				if(RmFirstLook(sigs, i) == look && !remaster_dirty_turfs[tkey]) continue
				turfs += list(RemasterTurfRecord(T))
				keys += tkey
				looks += look
				done[tkey] = 1
		if((world.tick_usage - t0) * world.tick_lag >= RM_SAVE_SLICE_MS)
			sleep(world.tick_lag)
			t0 = world.tick_usage
	for(var/tkey in remaster_dirty_turfs.Copy()) if(!done[tkey])
		done[tkey] = 1
		var/list/c = splittext(tkey, ",")
		var/turf/T = locate(text2num(c[1]), text2num(c[2]), text2num(c[3]))
		if(!T) continue
		turfs += list(RemasterTurfRecord(T))
		keys += tkey
		looks += RemasterTurfSig(T)
		if((world.tick_usage - t0) * world.tick_lag >= RM_SAVE_SLICE_MS)
			sleep(world.tick_lag)
			t0 = world.tick_usage
	return list(turfs, keys, looks, done)

// In the writing tick: the records again for tiles that changed while the scan went on, and the tiles dirtied meanwhile.
proc/RmSaveScanFinish(list/S)
	var/list/turfs = S[1]
	var/list/keys = S[2]
	var/list/looks = S[3]
	var/list/done = S[4]
	for(var/i = 1, i <= length(keys), i++)
		var/list/c = splittext(keys[i], ",")
		var/turf/T = locate(text2num(c[1]), text2num(c[2]), text2num(c[3]))
		if(T && RemasterTurfSig(T) != looks[i]) turfs[i] = RemasterTurfRecord(T)
	for(var/tkey in remaster_dirty_turfs) if(!done[tkey])
		var/list/c = splittext(tkey, ",")
		var/turf/T = locate(text2num(c[1]), text2num(c[2]), text2num(c[3]))
		if(T) turfs += list(RemasterTurfRecord(T))
	return turfs

// SaveUnits() for the autosave and the Save button: the scan spread, the writing in one tick. One already under way
// saves everything: this one waits for it.
proc/RmSaveUnitsSpread()
	if(rm_save_spreading)
		while(rm_save_spreading) sleep(1)
		return 1
	if(!remaster_world_ready)
		SaveUnits()
		return 1
	rm_save_spreading = 1
	var/list/turfs
	try
		turfs = RmSaveScanFinish(RmSaveScanSpread())
	catch(var/exception/e)
		world.log << "Remastered: the spread save's scan failed ([e]); saving in one go"
		turfs = null
	rm_save_spreading = 0
	SaveUnits(turfs)
	return 1

// The Save button's: "Game saved." once it is.
proc/RmSaveNowSpread(Player/P)
	RmSaveUnitsSpread()
	if(P) P.RemasterNotice("Game saved.")
