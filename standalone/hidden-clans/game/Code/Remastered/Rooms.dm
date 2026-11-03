// Rooms that matter. A room is an enclosed floor area (walls and doors around it)
// with furniture that says what it is:
//   bedroom      one or two beds          (three or more: a dormitory)
//   dining hall  a table and two chairs or more
//   throne room  a throne
// Its grade (Plain, Decent, Fine, Grand) comes from built floors, a sensible size,
// decoration (pillars, statues, tapestries, light) and gold furniture. Sleeping in a
// good bedroom and eating in a dining hall lift moods (Moods.dm); a throne room with
// a crowned ruler cheers the whole realm. Towns need a dining hall and Kingdoms a
// throne room (Progress.dm). Rooms are found again every few seconds near the
// settlement, so building or breaking a wall changes them at once.

#define RM_ROOM_MAX 160

var/list/rm_room_grades = list("Plain", "Decent", "Fine", "Grand")

proc/RemasterRoomWall(turf/T)
	if(!T) return 1
	if(T.density) return 1
	for(var/obj/Items/Furniture/Doors/D in T) return 1   // a doorway closes the room
	return 0

// Flood the floor from T; null if it leaks (too big: not enclosed).
proc/RemasterRoomFill(turf/T)
	if(RemasterRoomWall(T)) return null
	var/list/seen = list()
	var/list/q = list(T)
	seen[T] = 1
	while(length(q))
		var/turf/C = q[length(q)]
		q.len--
		for(var/d in list(NORTH, SOUTH, EAST, WEST))
			var/turf/N = get_step(C, d)
			if(N && rm_room_read) rm_room_read["[round((N.x - 1) / 16)],[round((N.y - 1) / 16)],[N.z]"] = 1   // what a kept flood read (RemasterRoomsScan)
			if(!N || seen[N] || RemasterRoomWall(N)) continue
			seen[N] = 1
			if(length(seen) > RM_ROOM_MAX) return null
			q += N
	. = list()
	for(var/turf/X in seen) . += X

proc/RemasterRoomDescribe(list/tiles)
	var/beds = 0
	var/tables = 0
	var/chairs = 0
	var/throne = 0
	var/decor = 0
	var/gold = 0
	var/light = 0
	var/built = 0
	var/list/bedspots = list()
	for(var/turf/T in tiles)
		if(("Detailed" in T.vars && T.vars["Detailed"]) || findtext("[T.icon_state]", "Floor") && !findtext("[T.icon_state]", "Cave")) built++
		for(var/obj/O in T)
			if(istype(O, /obj/Items/Furniture/Beds) && !istype(O, /obj/Items/Furniture/Beds/SleepingBag))
				beds++
				bedspots += "[T.x],[T.y],[T.z]"
			else if(istype(O, /obj/Items/Furniture/Tables)) tables++
			else if(istype(O, /obj/Items/Furniture/Chairs/BoneThrone) || istype(O, /obj/Items/Furniture/Chairs/GoldenThrone)) throne++
			else if(istype(O, /obj/Items/Furniture/Chairs)) chairs++
			else if(istype(O, /obj/Items/Furniture/Pillars) || istype(O, /obj/Tapestry)) decor++
			else if(istype(O, /obj/RemasterRune/Lamp)) light++
			if(findtext("[O.type]", "Gold")) gold++
		for(var/mob/WorkShops/CampFires/F in T) light++
	var/type
	if(throne) type = "throne"
	else if(tables && chairs >= 2) type = "hall"
	else if(beds >= 3) type = "dorm"
	else if(beds) type = "bedroom"
	if(!type) return null
	var/size = length(tiles)
	var/q = 0
	q += round(3 * built / max(1, size))
	if(type == "bedroom") q += (size >= 4 && size <= 25) ? 1 : 0
	else q += size >= 12 ? 1 : 0
	q += min(4, decor) + min(2, light) + min(4, gold * 2)
	var/grade = q >= 7 ? 4 : (q >= 5 ? 3 : (q >= 3 ? 2 : 1))
	var/turf/A = tiles[1]
	return list("type"=type, "grade"=grade, "quality"=q, "size"=size, "x"=A.x, "y"=A.y, "z"=A.z, "beds"=bedspots)

proc/RemasterRoomName(type)
	return list("bedroom"="Bedroom", "dorm"="Dormitory", "hall"="Dining hall", "throne"="Throne room")[type]

Player/var/tmp
	list/remaster_rooms              // list of room descriptions near the settlement
	list/remaster_room_at            // "x,y,z" of each tile -> its room description

// Find every room around the settlement (from its furniture). Kept chunk by chunk (load-asleep-1030, 10-31, the owner:
// "Exact, engine counter"): each 16x16 chunk's seed tiles (RmRoomSeed) while its RmChunkKey and bounds hold, and each
// seed's flood (its room, or a leak) while every chunk the flood read holds, so a scan floods only round what changed.
// The seeds are visited in block()'s order (rows, x along each), as before, so the rooms and their order are the same.
// It read every tile of the 81x81 box and flooded every room about every 3 s for every player. RM_SCAN_VERIFY=1: found
// whole too (RmRoomsWhole), a different answer logged (RMSCAN|).
Player/var/tmp
	list/rm_room_seeds    // "cx,cy,z" -> list(key, "y" -> that row's seed tiles in x order)
	list/rm_room_floods   // seed tile -> list(its room's tiles or null (it leaked), its description or null, "cx,cy,z" -> key read)
var/list/rm_room_read     // while a flood runs for RemasterRoomsScan: the chunks it read, "cx,cy,z" -> 1
Player/proc/RemasterRoomsScan()
	var/list/rooms = list()
	var/list/at = list()
	var/turf/C = RemasterProgressCenter()
	var/list/floods = list()
	if(C)
		var/r = RM_PROGRESS_RANGE
		var/x0 = max(1, C.x - r)
		var/y0 = max(1, C.y - r)
		var/x1 = min(world.maxx, C.x + r)
		var/y1 = min(world.maxy, C.y + r)
		var/cx0 = round((x0 - 1) / 16)
		var/cx1 = round((x1 - 1) / 16)
		var/list/seeds = list()
		for(var/cy = round((y0 - 1) / 16), cy <= round((y1 - 1) / 16), cy++)
			for(var/cx = cx0, cx <= cx1, cx++)
				var/ck = "[cx],[cy],[C.z]"
				var/sx0 = max(x0, cx * 16 + 1)
				var/sy0 = max(y0, cy * 16 + 1)
				var/sx1 = min(x1, cx * 16 + 16)
				var/sy1 = min(y1, cy * 16 + 16)
				var/key = "[sx0],[sy0],[sx1],[sy1]|" + RmChunkKey(cx, cy, C.z, ck)
				var/list/K = rm_room_seeds && rm_room_seeds[ck]
				if(!K || K[1] != key)
					var/list/rows = list()
					for(var/turf/T in block(locate(sx0, sy0, C.z), locate(sx1, sy1, C.z)))
						if(!RmRoomSeed(T)) continue
						var/list/row = rows["[T.y]"]
						if(!row)
							row = list()
							rows["[T.y]"] = row
						row += T
					K = list(key, rows)
				seeds[ck] = K
		rm_room_seeds = seeds
		var/list/done = list()
		var/list/kept = rm_room_floods || list()
		for(var/y = y0, y <= y1, y++)
			var/cy = round((y - 1) / 16)
			for(var/cx = cx0, cx <= cx1, cx++)
				var/list/K = seeds["[cx],[cy],[C.z]"]
				var/list/rows = K[2]
				var/list/row = rows["[y]"]
				if(!row) continue
				for(var/turf/T in row)
					if(done[T]) continue
					var/list/F = kept[T]
					if(!F || !RmReadHolds(F[3]))
						rm_room_read = list()
						rm_room_read["[round((T.x - 1) / 16)],[round((T.y - 1) / 16)],[T.z]"] = 1
						var/list/flood = RemasterRoomFill(T)
						var/list/read = list()
						for(var/rk in rm_room_read)
							var/list/c = splittext(rk, ",")
							read[rk] = RmChunkKey(text2num(c[1]), text2num(c[2]), text2num(c[3]), rk)
						rm_room_read = null
						F = list(flood, flood ? RemasterRoomDescribe(flood) : null, read)
					floods[T] = F
					var/list/tiles = F[1]
					if(!tiles)
						done[T] = 1
						continue
					for(var/turf/X in tiles) done[X] = 1
					var/list/D = F[2]
					if(!D) continue
					rooms += list(D)
					for(var/turf/X in tiles) at["[X.x],[X.y],[X.z]"] = D
	rm_room_floods = floods
	if(RmScanVerify() && json_encode(rooms) != json_encode(RmRoomsWhole(C)))
		rm_scan_differ++
		world.log << "RMSCAN|rooms differ|[C ? "[C.x],[C.y],[C.z]" : "-"]|kept [length(rooms)]|whole [length(RmRoomsWhole(C))]"
	remaster_rooms = rooms
	remaster_room_at = at
	return rooms

// A tile with furniture that makes a room (a bed, a table or a chair) of the realm's own, not the map's.
proc/RmRoomSeed(turf/T)
	for(var/obj/Items/Furniture/F in T)
		if(!F.remaster_runtime && remaster_map_items[F]) continue   // an NPC town's or a ruin's, from the map (WorldSave.dm)
		if(istype(F, /obj/Items/Furniture/Beds) || istype(F, /obj/Items/Furniture/Tables) || istype(F, /obj/Items/Furniture/Chairs)) return 1
	return 0

// Every chunk a flood read is as it was then.
proc/RmReadHolds(list/read)
	for(var/rk in read)
		var/list/c = splittext(rk, ",")
		if(RmChunkKey(text2num(c[1]), text2num(c[2]), text2num(c[3]), rk) != read[rk]) return 0
	return 1

// What a scan of chunk (cx, cy, z) read is as it was while this text is: its tiles' vars (rm_chunk_ver), the things on
// them (rm_chunk_things_ver), and whether the world save has noted its first looks (RemasterTileChanged). Map items are
// noted only at the start and when a season repopulates, which makes them there: that chunk's things move with it. On an
// engine without the counters every call is a new number: always scanned.
proc/RmChunkKey(cx, cy, z, ck)
	return "[rm_chunk_ver(cx, cy, z)].[rm_chunk_things_ver(cx, cy, z)].[remaster_chunks[ck] ? 1 : 0]"

// RM_SCAN_VERIFY=1 in the server's environment: kept scans are checked against whole ones, any difference logged (RMSCAN|).
var/rm_scan_verify = -1
var/rm_scan_differ = 0
proc/RmScanVerify()
	if(rm_scan_verify < 0) rm_scan_verify = world.GetConfig("env", "RM_SCAN_VERIFY") == "1"
	return rm_scan_verify

// The rooms round C found whole, every tile and every flood, as RemasterRoomsScan found them before it kept them (its check).
Player/proc/RmRoomsWhole(turf/C)
	var/list/rooms = list()
	if(C)
		var/list/done = list()
		var/r = RM_PROGRESS_RANGE
		for(var/turf/T in block(locate(max(1, C.x - r), max(1, C.y - r), C.z), locate(min(world.maxx, C.x + r), min(world.maxy, C.y + r), C.z)))
			if(done[T]) continue
			var/key = 0
			for(var/obj/Items/Furniture/F in T)
				if(!F.remaster_runtime && remaster_map_items[F]) continue   // an NPC town's or a ruin's, from the map (WorldSave.dm)
				if(istype(F, /obj/Items/Furniture/Beds) || istype(F, /obj/Items/Furniture/Tables) || istype(F, /obj/Items/Furniture/Chairs)) key = 1
			if(!key) continue
			var/list/tiles = RemasterRoomFill(T)
			if(!tiles)
				done[T] = 1
				continue
			for(var/turf/X in tiles) done[X] = 1
			var/list/D = RemasterRoomDescribe(tiles)
			if(!D) continue
			rooms += list(D)
	return rooms

Player/proc/RemasterRoomAt(turf/T)
	if(!T || !remaster_room_at) return null
	return remaster_room_at["[T.x],[T.y],[T.z]"]

Player/proc/RemasterRoomCount(type)
	. = 0
	for(var/list/D in remaster_rooms) if(D["type"] == type) .++

// Mood thoughts from rooms (called from Moods.dm).
mob/Monsters/proc/RemasterRoomThoughts(Player/P)
	. = list()
	if(!istype(P)) return
	if(islist(remaster_home) && length(remaster_home) == 3)
		var/list/D = P.remaster_room_at && P.remaster_room_at["[remaster_home[1]],[remaster_home[2]],[remaster_home[3]]"]
		if(D)
			var/g = rm_room_grades[D["grade"]]
			if(D["type"] == "bedroom") . += list(list("Sleeps in a [lowertext(g)] bedroom", list(3, 6, 9, 12)[D["grade"]]))
			else if(D["type"] == "dorm") . += list(list("Sleeps in a [lowertext(g)] dormitory", list(1, 2, 4, 6)[D["grade"]]))
	if(P.RemasterRoomCount("throne"))
		for(var/mob/Monsters/R in P.UnitList) if(R.Owner == P && R.IsRoyal && R.HP > 0)
			. += list(list("Our ruler holds court", 4))
			break

// Eating in the dining hall is remembered (EatItem -> Moods.dm).
mob/Monsters/proc/RemasterRoomMeal()
	var/Player/P = Owner
	if(!istype(P)) return
	var/list/D = P.RemasterRoomAt(loc)
	if(D && D["type"] == "hall")
		var/g = rm_room_grades[D["grade"]]
		RemasterRemember("hall", "Ate in a [lowertext(g)] dining hall", list(3, 5, 7, 10)[D["grade"]], 1)

Player/proc/RemasterRoomsData()
	. = list()
	for(var/list/D in remaster_rooms)
		. += list(list("type"=D["type"], "name"=RemasterRoomName(D["type"]), "grade"=rm_room_grades[D["grade"]], "size"=D["size"], "x"=D["x"], "y"=D["y"]))
