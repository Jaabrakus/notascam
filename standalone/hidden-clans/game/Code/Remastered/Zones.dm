// Stockpile zones: extra named stockpiles on top of the main one, each with a
// filter (food store, ore yard, armoury...). The main stockpile works exactly
// as before; board workers with nothing to do carry items from the main
// stockpile to the zone that takes them. Counts, eating, cooking, seeds and
// tool fetching look in every store. Items on any store don't expire.

#define REMASTER_ZONES_MAX 8

Player/var
	list/remaster_zones          // list(list("id","name","x","y","z","filter"))
	remaster_zone_serial = 0

proc/RemasterZoneFilters()
	return list("food"="Food store", "mining"="Ore yard", "equipment"="Armoury", "wood"="Wood pile", "stone"="Stone yard", "seeds"="Seed store", "any"="Anything")

proc/RemasterZoneAccepts(list/Z, obj/Items/I)
	if(!Z || !I) return 0
	switch(Z["filter"])
		if("any") return 1
		if("food") return istype(I, /obj/Items/Food)
		if("seeds") return istype(I, /obj/Items/Seeds)
		if("wood") return istype(I, /obj/Items/woods/wood)
		if("stone") return istype(I, /obj/Items/ores/stone) || (Z["yard"] && RemasterRawKind(I) == "minerals")   // a quarry's yard takes what a quarry gives (ore-stores, 10-27)
		if("mining") return istype(I, /obj/Items/ores) || istype(I, /obj/Items/gems) || istype(I, /obj/Items/Ingots) || istype(I, /obj/Items/Bones) || RemasterRawKind(I) == "minerals"   // + rock salt
		if("equipment") return !!I.EquipmentType()
	return 0

Player/proc/RemasterZoneTurf(list/Z)
	return Z ? locate(Z["x"], Z["y"], Z["z"]) : null

// A stockpile painted on the job board (Jobs.dm, + Store) is its whole area (the user, 2026-10-25: "wouldnt we just
// expand the stockpile?"). Its rectangle is covered by 3 x 3 cells, each a store tile with the 8 round it, as every store
// is read (counts, rot, fetching: range(1) round each), so a 9 x 9 one has 9 cells and 72 tiles to put loads down from.
// Before, however big it was painted, it was one tile at its middle: 2,000 carriers shared its 9 tiles. A zone set on the
// Zones list (at a unit or the camera) stays one tile.
Player/var/tmp/list/rm_zone_cells          // zone id -> list(x0, y0, x1, y1, z of its rectangle, its cell tiles)

Player/proc/RemasterZoneCells(list/Z)
	if(!Z) return list()
	if(isnull(Z["x0"]))
		// saved before areas: the job board's painted rectangle, if it was painted
		for(var/list/J in rm_jz) if(J["store"] == Z["id"])
			Z["x0"] = J["x0"]; Z["y0"] = J["y0"]; Z["x1"] = J["x1"]; Z["y1"] = J["y1"]
			break
	if(isnull(Z["x0"]))
		var/turf/C0 = RemasterZoneTurf(Z)
		return C0 ? list(C0) : list()
	// its cells kept while its rectangle is the same: the five numbers compared, not made into text first (asked ~24,000
	// times a game second at 2,000 workers: the store finder, the zone of a tile, idle villagers' waiting places)
	var/x0 = Z["x0"]
	var/y0 = Z["y0"]
	var/x1 = Z["x1"]
	var/y1 = Z["y1"]
	var/zz = Z["z"]
	if(!rm_zone_cells) rm_zone_cells = list()
	var/list/K = rm_zone_cells[Z["id"]]
	if(K && K[1] == x0 && K[2] == y0 && K[3] == x1 && K[4] == y1 && K[5] == zz) return K[6]
	var/turf/C = RemasterZoneTurf(Z)
	var/list/cells = list()
	for(var/y = Z["y0"] + 1, y - 1 <= Z["y1"], y += 3) for(var/x = Z["x0"] + 1, x - 1 <= Z["x1"], x += 3)
		var/turf/T = locate(min(x, Z["x1"]), min(y, Z["y1"]), Z["z"])
		if(T && T.density)        // a wall or a tree on the cell's middle: an open tile of the cell instead
			var/turf/O
			for(var/turf/N in block(locate(max(Z["x0"], T.x - 1), max(Z["y0"], T.y - 1), T.z), locate(min(Z["x1"], T.x + 1), min(Z["y1"], T.y + 1), T.z))) if(!N.density)
				O = N
				break
			T = O
		if(T && !(T in cells)) cells += T
	if(C && !(C in cells) && !C.density)   // the tile it had (goods may lie round it)
		var/near = 0
		for(var/turf/T in cells) if(get_dist(T, C) <= 1) near = 1
		if(!near) cells += C
	rm_zone_cells[Z["id"]] = list(x0, y0, x1, y1, zz, cells)
	rm_zone_cells_built++      // a tile's zone is read again (RemasterZoneOfCell)
	return cells

// The zone a store tile belongs to, or null (the main stockpile's isn't a zone's).
// It's asked on every step of every carrier's walk to a store (the deposit tick, Jobs.dm: 338 a game second at 2,000
// workers, 48 us each, walking every zone's cells: 16 ms of the deposit tick's 30, the owner's "next plan item", 10-29).
// So each tile's answer is kept while the zones are the same ones with the same cell lists: looked at once a tick, and at
// once when a zone is added or taken away or any zone's cells are made again (RemasterZoneCells). A zone painted over or
// moved within one tick counts from the next (a tenth of a second). RM_ZOC=0: the walk every time; RM_ZOC_VERIFY=1 asks
// both ways and logs any difference (ZOCDIFF).
var/rm_zoc_on = 1
var/rm_zoc_verify = 0
var/rm_zoc_checks = 0
var/rm_zoc_diffs = 0
var/rm_zone_cells_built = 0                // cell lists made (RemasterZoneCells)
Player/var/tmp
	list/rm_zoc                            // tile -> its zone, or 0: none
	list/rm_zoc_keys                       // the zones and their cell lists the answers were read from
	rm_zoc_tick = -1
	rm_zoc_n = -1                          // how many zones then
	rm_zoc_built = -1                      // rm_zone_cells_built then

Player/proc/RemasterZoneOfCell(turf/T)
	if(!rm_zoc_on) return RmZoneOfCellDM(T)
	if(!T) return null
	if(rm_zoc_tick != world.time || length(remaster_zones) != rm_zoc_n || rm_zone_cells_built != rm_zoc_built) RmZocCheck()
	if(!rm_zoc) rm_zoc = list()
	var/v = rm_zoc[T]
	if(isnull(v))
		v = RmZoneOfCellDM(T) || 0
		rm_zoc[T] = v
	if(rm_zoc_verify)
		rm_zoc_checks++
		var/list/D = RmZoneOfCellDM(T)
		if(D != (v || null))
			rm_zoc_diffs++
			world.log << "ZOCDIFF|[world.time]|[T.x],[T.y],[T.z]|kept [v ? v["name"] : "none"]|now [D ? D["name"] : "none"]"
	return v || null

// The zones, in order, and the cell list each reads now (a zone kept as one tile: that tile): any change, and the kept
// answers go.
Player/proc/RmZocCheck()
	rm_zoc_tick = world.time
	var/list/K = list()
	if(remaster_zones) for(var/list/Z in remaster_zones)
		var/list/C = RemasterZoneCells(Z)
		K.len += 2
		K[K.len - 1] = Z
		K[K.len] = isnull(Z["x0"]) ? (length(C) ? C[1] : 0) : C
	rm_zoc_n = length(remaster_zones)
	rm_zoc_built = rm_zone_cells_built
	var/same = rm_zoc_keys && length(rm_zoc_keys) == length(K)
	if(same) for(var/i = 1, i <= length(K), i++) if(K[i] != rm_zoc_keys[i])
		same = 0
		break
	if(same) return
	rm_zoc_keys = K
	rm_zoc = null

Player/proc/RmZoneOfCellDM(turf/T)
	if(remaster_zones) for(var/list/Z in remaster_zones) if(T in RemasterZoneCells(Z)) return Z
	return null

// Inside a store's area, or a tile round it: where nobody waits (Jobs.dm RmJzClearStore). It's asked on every idle
// villager's step and for each tile round one looking for a place to wait (81 or 289 a look), and walking every store
// for each answer took ~100 ms a second at 2,000 workers (gathering, 2026-10-26). So the tiles are marked with this
// player's serial, and marked again only when the stores change (looked at once a tick). Two realms' store areas on one
// tile: the last marked wins, and the other's villagers may wait there.
turf/var/tmp/rm_store_mark = 0
var/rm_store_serials = 0
Player/var/tmp
	rm_store_serial = 0      // this player's marks
	rm_store_tick = -1       // the tick the stores were last looked at
	rm_store_sig             // their layout then
Player/proc/RemasterInStoreArea(turf/T)
	if(!T) return 0
	if(rm_store_tick != world.time) RmStoreMarks()
	return T.rm_store_mark == rm_store_serial

// The stores' layout; the marks are made again when it changed: the main stockpile and the tiles round it, a painted
// area and the ring round it, a one-tile store and the tiles round it.
Player/proc/RmStoreMarks()
	rm_store_tick = world.time
	var/turf/S = RemasterStockpile()
	var/sig = S ? "[S.x],[S.y],[S.z]" : "-"
	if(remaster_zones) for(var/list/Z in remaster_zones) sig += isnull(Z["x0"]) ? "|[Z["x"]],[Z["y"]],[Z["z"]]" : "|[Z["x0"]],[Z["y0"]],[Z["x1"]],[Z["y1"]],[Z["z"]]"
	if(rm_store_serial && sig == rm_store_sig) return
	rm_store_sig = sig
	rm_store_serial = ++rm_store_serials
	if(S) for(var/turf/T in range(1, S)) T.rm_store_mark = rm_store_serial
	if(remaster_zones) for(var/list/Z in remaster_zones)
		if(!Z["z"]) continue
		if(!isnull(Z["x0"]))
			var/turf/A = locate(max(1, Z["x0"] - 1), max(1, Z["y0"] - 1), Z["z"])
			var/turf/B = locate(min(world.maxx, Z["x1"] + 1), min(world.maxy, Z["y1"] + 1), Z["z"])
			if(A && B) for(var/turf/T in block(A, B)) T.rm_store_mark = rm_store_serial
		else
			var/turf/C = locate(Z["x"], Z["y"], Z["z"])
			if(C) for(var/turf/T in range(1, C)) T.rm_store_mark = rm_store_serial

// Main stockpile first, then the zones' cells.
Player/proc/RemasterStores()
	var/list/out = list()
	var/turf/S = RemasterStockpile()
	if(S) out += S
	if(remaster_zones) for(var/list/Z in remaster_zones)
		for(var/turf/T in RemasterZoneCells(Z)) if(T != S) out += T
	return out

// Goods lying on a store (the main stockpile or a zone, or a tile beside it) don't
// rot. Same timer and test as the original ItemDecay() (Vars.dm), which deletes
// loose wood, ore, ingots, gems, seeds, food and glands about half an hour after
// they were made, plus the store check.
var/remaster_rot_delay = 19000

obj/ItemDecay()
	spawn(remaster_rot_delay)
		if(isnull(suffix) && !RemasterOnStore(src)) del(src)
		else ItemDecay()

proc/RemasterOnStore(atom/movable/A)
	var/turf/T = A ? A.loc : null
	if(!isturf(T)) return 0
	for(var/Player/P in world)
		for(var/turf/S in P.RemasterStores()) if(S.z == T.z && get_dist(S, T) <= 1) return 1
	return 0

// Nearest store on this unit's level holding something of type.
Player/proc/RemasterStoreWith(type, mob/M, icon_state)
	var/turf/best
	var/best_d = 1#INF
	for(var/turf/S in RemasterStores())
		if(S.z != M.z) continue
		var/found = 0
		for(var/obj/Items/I in range(1, S))
			if(isturf(I.loc) && istype(I, type) && (!icon_state || I.icon_state == icon_state) && RemasterMayCollect(I))
				found = 1
				break
		if(!found) continue
		var/d = get_dist(S, M)
		if(d < best_d)
			best = S
			best_d = d
	return best

Player/proc/RemasterZoneCommand(action, value)
	var/list/parts = splittext("[value]", "|")
	switch(action)
		if("zoneadd")
			// filter|unit or filter|camera
			if(length(parts) != 2 || !(parts[1] in RemasterZoneFilters())) return 0
			if(length(remaster_zones) >= REMASTER_ZONES_MAX)
				RemasterNotice("Up to [REMASTER_ZONES_MAX] stockpile zones.")
				return 0
			var/turf/T
			if(parts[2] == "unit")
				for(var/mob/Monsters/M in Selected) if(M.Owner == src && isturf(M.loc))
					T = M.loc
					break
			else if(isturf(loc)) T = loc
			if(!T || T.density)
				RemasterNotice("Choose open ground for the zone (select a unit standing there, or centre the view on it).")
				return 0
			if(!remaster_zones) remaster_zones = list()
			remaster_zone_serial++
			var/list/names = RemasterZoneFilters()
			remaster_zones += list(list("id"="z[remaster_zone_serial]", "name"=names[parts[1]], "x"=T.x, "y"=T.y, "z"=T.z, "filter"=parts[1]))
			RemasterNotice("[names[parts[1]]] placed at [T.x], [T.y]. Board workers bring matching items from the main stockpile.")
			return 1
		if("zoneremove")
			if(remaster_zones) for(var/list/Z in remaster_zones) if(Z["id"] == value)
				remaster_zones -= list(Z)
				return 1
			return 0
		if("zonefilter")
			if(length(parts) != 2 || !(parts[2] in RemasterZoneFilters())) return 0
			if(remaster_zones) for(var/list/Z in remaster_zones) if(Z["id"] == parts[1])
				Z["filter"] = parts[2]
				return 1
			return 0
	return 0

Player/proc/RemasterZoneData()
	var/list/out = list()
	if(remaster_zones) for(var/list/Z in remaster_zones)
		var/n = 0
		for(var/turf/T in RemasterZoneCells(Z)) for(var/obj/Items/I in range(1, T)) if(isturf(I.loc)) n++
		out += list(list("id"=Z["id"], "name"=Z["name"], "x"=Z["x"], "y"=Z["y"], "z"=Z["z"], "filter"=Z["filter"], "items"=n))
	return list("zones"=out, "filters"=RemasterZoneFilters())

// --- Keeping the zones: an idle board worker moves one load. -----------------
mob/Monsters/var/tmp
	list/remaster_zone_load        // items being carried to a zone
	remaster_zone_target           // zone id

// Returns 1 when it did something this tick.
mob/Monsters/proc/RemasterZoneKeep(Player/P)
	if(!P.remaster_zones || !length(P.remaster_zones)) return 0
	var/list/load = list()
	if(remaster_zone_load) for(var/obj/Items/I in remaster_zone_load) if(I.loc == src) load += I
	remaster_zone_load = load
	if(length(load))
		var/list/Z
		for(var/list/X in P.remaster_zones) if(X["id"] == remaster_zone_target) Z = X
		var/turf/T = P.RemasterZoneTurf(Z)
		if(!T || T.z != z)
			for(var/obj/Items/I in load) if(DropItem(I)) I.loc = loc
			remaster_zone_load = null
			return 1
		if(!RemasterWorkToward(T, Z["name"])) return 1
		var/n = 0
		for(var/obj/Items/I in load) if(DropItem(I))
			I.loc = T
			I.Owner = P
			n++
		remaster_zone_load = null
		remaster_work_status = "Stored [n] item[n == 1 ? "" : "s"] in the [Z["name"]]"
		return 1
	// Something on the main stockpile that a zone takes?
	var/turf/S = P.RemasterStockpile()
	if(!S || S.z != z) return 0
	for(var/obj/Items/I in range(1, S))
		if(!isturf(I.loc) || !P.RemasterMayCollect(I) || P.RemasterClaimed(I, src) || RmShunsSilver(I)) continue
		for(var/list/Z in P.remaster_zones)
			if(Z["z"] != z || Z["yard"] || !RemasterZoneAccepts(Z, I)) continue   // a yard is a drop-off (Jobs.dm RmJzAutoYard)
			var/turf/T = P.RemasterZoneTurf(Z)
			if(!T || get_dist(T, I) <= 1) continue
			if(!RemasterWorkToward(I, "items for the [Z["name"]]")) return 1
			var/list/took = list()
			for(var/obj/Items/X in range(1, S))
				if(length(took) >= 6) break
				if(isturf(X.loc) && P.RemasterMayCollect(X) && RemasterZoneAccepts(Z, X) && !RmShunsSilver(X) && PickUpItem(X)) took += X
			remaster_zone_load = took
			remaster_zone_target = Z["id"]
			remaster_work_status = length(took) ? "Taking [length(took)] item[length(took) == 1 ? "" : "s"] to the [Z["name"]]" : "Can't carry more"
			return 1
	return 0
