// Explored-map memory. Each player remembers the tiles their units and their
// own view have seen. 3D draws seen-before tiles dim and never-seen tiles dark;
// the minimap and the world map show explored land only.
// Saved per layer as 16x16 chunks, one number per chunk row (16 bits).

#define REMASTER_EXPLORE_EVERY 4     // RemasterTrack calls (about 2 seconds)
#define REMASTER_EXPLORE_UNIT_SIGHT 5

Player/var
	list/remaster_explored          // "z" -> ("cx,cy" -> list of 16 row bitmasks)
Player/var/tmp
	remaster_explore_mask
	remaster_explore_mask_key
	remaster_explore_clock = 0
	remaster_explore_version = 0    // bumps when something new is explored
	remaster_world_map_open = 0
	remaster_world_map_z = 0
	list/remaster_world_map_cache    // "z|version" -> data

Player/proc/RemasterMarkExplored(turf/T)
	if(!T) return 0
	if(!remaster_explored) remaster_explored = list()
	var/zk = "[T.z]"
	var/list/L = remaster_explored[zk]
	if(!L)
		L = list()
		remaster_explored[zk] = L
	var/ck = "[round((T.x - 1) / 16)],[round((T.y - 1) / 16)]"
	var/list/rows = L[ck]
	if(!rows)
		rows = list(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)
		L[ck] = rows
		RmMaskChunkAdded(T.z, round((T.x - 1) / 16), round((T.y - 1) / 16), L)
	var/r = ((T.y - 1) % 16) + 1
	var/bit = 1 << ((T.x - 1) % 16)
	if(rows[r] & bit) return 0
	rows[r] |= bit
	return 1

// RemasterMarkExplored for every turf in a list (a view), the same marks, with a chunk's rows looked up only when the
// next tile is in another chunk: two key strings a tile made the explore pass 40-86 ms with 200 units (server cost,
// 2026-10-24). Returns how many were new.
Player/proc/RemasterMarkExploredAll(list/turfs)
	if(!remaster_explored) remaster_explored = list()
	. = 0
	var/lz = -1
	var/lcx = -1
	var/lcy = -1
	var/list/L
	var/list/rows
	for(var/turf/T in turfs)
		if(T.z != lz)
			lz = T.z
			lcx = -1
			L = remaster_explored["[lz]"]
			if(!L)
				L = list()
				remaster_explored["[lz]"] = L
		var/cx = round((T.x - 1) / 16)
		var/cy = round((T.y - 1) / 16)
		if(cx != lcx || cy != lcy)
			lcx = cx
			lcy = cy
			var/ck = "[cx],[cy]"
			rows = L[ck]
			if(!rows)
				rows = list(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)
				L[ck] = rows
				RmMaskChunkAdded(lz, cx, cy, L)
		var/r = ((T.y - 1) % 16) + 1
		var/bit = 1 << ((T.x - 1) % 16)
		if(!(rows[r] & bit))
			rows[r] |= bit
			.++

Player/proc/RemasterIsExplored(x, y, z)
	if(!remaster_explored) return 0
	var/list/L = remaster_explored["[z]"]
	if(!L) return 0
	var/list/rows = L["[round((x - 1) / 16)],[round((y - 1) / 16)]"]
	if(!rows) return 0
	return (rows[((y - 1) % 16) + 1] & (1 << ((x - 1) % 16))) ? 1 : 0

// With spread (the track's runs, Spread.dm) it goes on into the next tick between units once a tick's share is used.
Player/proc/RemasterExploreTick(spread = 0)
	remaster_explore_clock++
	if(remaster_explore_clock % REMASTER_EXPLORE_EVERY) return
	var/added = 0
	// What the map window shows from the camera, and what each unit can see.
	if(isturf(loc) && !RmFogOn(z)) added += RemasterMarkExploredAll(view(client ? 12 : 0, src))   // with fog of war, only your units explore (Fog.dm)
	for(var/mob/Monsters/M in UnitList)
		if(M.Owner != src || !isturf(M.loc) || M.Egg || M.HP <= 0) continue
		if(RmFogOn(M.z)) continue   // the fog's circle round it marks more than this, once (Fog.dm; world-look 2026-10-25)
		added += RemasterMarkExploredAll(view(REMASTER_EXPLORE_UNIT_SIGHT, M))
		if(spread) RmTrackPause()
	if(added) RmFogExploredNew()   // everyone sharing your map (Fog.dm, allies)

// Kept while the level's explored chunks are the same: a cell of the mask is a chunk with anything explored, chunks are
// added with their first explored tile and never taken away (RemasterMarkExplored, Fog.dm's merges copy them), and a
// shared map (Fog.dm) is another list. So it is made again when a chunk is first explored, not each new tile (server
// cost, 2026-10-24: 37 ms a HUD send while units explored).
Player/proc/RemasterExploredMaskCached()
	var/list/L = remaster_explored ? remaster_explored["[z]"] : null
	var/key = "[z]|\ref[remaster_explored]|\ref[L]|[length(L)]"
	if(key != remaster_explore_mask_key)
		remaster_explore_mask_key = key
		remaster_explore_mask = RemasterExploredMask(z)
	return remaster_explore_mask

// A chunk first explored (its first tile marked, just now, in the same proc): the kept mask, if it is this level's and
// was up to date before the chunk came, gets that chunk's cells at once (usually one, or none) and its key moves on;
// otherwise it is made again when next asked for (RemasterExploredMaskCached). A chunk is in the mask once any tile of
// it is explored, and the tile is marked before the mask is next read.
Player/proc/RmMaskChunkAdded(level, cx, cy, list/L)
	if(!istext(remaster_explore_mask) || remaster_explore_mask_key != "[level]|\ref[remaster_explored]|\ref[L]|[length(L) - 1]") return
	var/m = remaster_explore_mask
	for(var/gy = 1, gy <= 48, gy++)
		if(round((clamp(world.maxy - round((gy - 0.5) * world.maxy / 48), 1, world.maxy) - 1) / 16) != cy) continue
		for(var/gx = 1, gx <= 48, gx++)
			if(round((clamp(round((gx - 0.5) * world.maxx / 48), 1, world.maxx) - 1) / 16) != cx) continue
			var/i = (gy - 1) * 48 + gx
			m = copytext(m, 1, i) + "1" + copytext(m, i + 1)
	remaster_explore_mask = m
	remaster_explore_mask_key = "[level]|\ref[remaster_explored]|\ref[L]|[length(L)]"

// --- Minimap: 48x48 cells, "1" where anything in the cell's chunk is explored.
Player/proc/RemasterExploredMask(level)
	var/list/out = list()
	for(var/gy = 1, gy <= 48, gy++)
		for(var/gx = 1, gx <= 48, gx++)
			var/tx = clamp(round((gx - 0.5) * world.maxx / 48), 1, world.maxx)
			var/ty = clamp(world.maxy - round((gy - 0.5) * world.maxy / 48), 1, world.maxy)
			out += RemasterChunkExplored(tx, ty, level) ? "1" : "0"
	return jointext(out, "")

Player/proc/RemasterChunkExplored(x, y, z)
	if(!remaster_explored) return 0
	var/list/L = remaster_explored["[z]"]
	if(!L) return 0
	var/list/rows = L["[round((x - 1) / 16)],[round((y - 1) / 16)]"]
	if(!rows) return 0
	for(var/r in rows) if(r) return 1
	return 0

// --- World map: every explored chunk as a 4x4 block of colours.
proc/RemasterTileColor(turf/T)
	if(!T) return "#000000"
	var/s = lowertext("[T.icon_state]")
	var/color = "#314c35"
	if(T.density) color = "#655e4a"
	// Tree, CaveWater, IsWall and Detailed are atom vars (Vars.dm), read directly: ("x" in T.vars) made and kept a vars
	// list on every tile coloured (map memory, planning/MAP_MEMORY.md 6.2).
	if(T.Tree) color = "#25442c"
	if(findtext(s, "water") || T.CaveWater) color = "#31586a"
	if(findtext(s, "desert") || findtext(s, "sand")) color = "#9c8757"
	if(findtext(s, "snow")) color = "#a2b8bb"
	if(findtext(s, "cave")) color = T.density ? "#3c3c44" : "#64616b"
	if(findtext(s, "lava")) color = "#a35032"
	if(s == "sky") color = "#6f93a0"
	if(T.IsWall || RmBuilt(T)) color = "#8a6a44"   // a laid column too (Plans.dm)
	if(T.Detailed && !T.density) color = "#7a6448"
	return color

Player/proc/RemasterWorldMapData()
	var/zz = remaster_world_map_z || z
	var/key = "[zz]|[remaster_explore_version]"
	if(!remaster_world_map_cache) remaster_world_map_cache = list()
	var/list/chunks = remaster_world_map_cache[key]
	if(!chunks)
		chunks = RemasterWorldMapChunks(zz)
		remaster_world_map_cache = list()
		remaster_world_map_cache[key] = chunks
	var/list/units = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.z == zz && isturf(M.loc)) units += list(list(M.x, M.y))
	var/turf/S = RemasterStockpile()
	var/list/qm = list()   // quest markers on this level (QuestTargets.dm)
	var/list/QMS = RmQuestMarksData()
	if(QMS) for(var/list/QR in QMS) if(QR["z"] in RmQuestLayers(zz)) qm += list(QR)
	return list("z"=zz, "maxx"=world.maxx, "maxy"=world.maxy, "chunks"=chunks, "units"=units,
		"stockpile"=(S && S.z == zz ? list(S.x, S.y) : null), "x"=x, "y"=y, "quests"=qm, "pick"=rm_quest_pick)

Player/proc/RemasterWorldMapChunks(zz)
	var/list/chunks = list()
	var/list/L = remaster_explored ? remaster_explored["[zz]"] : null
	if(L) for(var/ck in L)
		var/list/xy = splittext(ck, ",")
		var/cx = text2num(xy[1])
		var/cy = text2num(xy[2])
		var/list/rows = L[ck]
		var/list/cells = list()
		for(var/j = 0, j < 4, j++)
			for(var/i = 0, i < 4, i++)
				// A cell is drawn if any of its 4x4 tiles was seen.
				var/seen = 0
				for(var/r = j * 4 + 1, r <= j * 4 + 4, r++) if(rows[r] & (15 << (i * 4))) seen = 1
				if(!seen)
					cells += ""
					continue
				cells += RemasterTileColor(locate(cx * 16 + i * 4 + 2, cy * 16 + j * 4 + 2, zz))
		chunks += list(list(cx, cy, cells))
	return chunks

Player/proc/RemasterWorldMapCommand(action, value)
	switch(action)
		if("worldmap")
			remaster_world_map_open = value == "1"
			remaster_world_map_z = z
			return 1
		if("worldmaplayer")
			var/n = text2num(value)
			if(n == SKY_LAYER && !RmSkyOpen()) RmSkyShutNote()   // the Sky is earned (Flying.dm)
			else if(n >= 1 && n <= world.maxz) remaster_world_map_z = n
			return 1
	return 0
