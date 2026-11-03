// PROTOTYPE, not part of the game: the Village stores bar (planning/SONGS_OF_SYX_ECONOMY.md section 9).
// One pool you can see: everything your house holds, added up across the stockpile, every zone, the cart
// loading stops and the food pots and stalls, with what your villagers carry counted beside it. The goods
// stay real things in real places (they can rot, be carried off, be raided); the bar only adds them up.
// Each total also says where it all is, so the HUD can list the places and jump the camera to one.
// Sent with the HUD model as "stores" (village_stores.js draws it).

#define RM_STORES_EVERY 20     // ticks between recounts

Player/var/tmp/list/rm_stores_cache
Player/var/tmp/rm_stores_at = -1000

// kind -> label, in the bar's order
var/list/rm_store_kinds = list("wood"="Wood", "stone"="Stone", "ores"="Ore", "ingots"="Metal", "gems"="Gems",
	"food"="Food", "skin"="Hides", "bones"="Bones", "seeds"="Seeds")

Player/RemasterHUDData()
	. = ..()
	if(islist(.)) .["stores"] = RmVillageStores()

Player/proc/RmStoreName(turf/T)
	var/turf/S = RemasterStockpile()
	if(T == S) return "Stockpile"
	if(remaster_zones) for(var/list/Z in remaster_zones) if(RemasterZoneTurf(Z) == T)
		return "[Z["name"] || RemasterZoneFilters()[Z["filter"]] || "Zone"]"
	if(RemasterIsLoadStop(T)) return "Cart stop"
	var/list/L = rm_workplaces ? RmLodgeAt(T) : null      // a lodge's store shed (Workplaces.dm)
	if(L) return "[L["name"]]"
	return "Store"

Player/proc/RmVillageStores()
	if(rm_stores_cache && world.time - rm_stores_at < RM_STORES_EVERY) return rm_stores_cache
	rm_stores_at = world.time
	var/list/K = list()
	for(var/k in rm_store_kinds) K[k] = list("label"=rm_store_kinds[k], "stored"=0, "carried"=0, "where"=list())
	// the stores: each item counted once, at the store it lies by
	var/list/counted = list()
	for(var/turf/T in RemasterStores())
		var/list/here = list()
		for(var/obj/Items/I in range(1, T)) if(isturf(I.loc) && !counted[I] && !I.suffix)
			var/k = RemasterResourceKind(I)
			if(!k || !K[k]) continue
			counted[I] = 1
			here[k] = (here[k] || 0) + 1
		var/name = RmStoreName(T)
		for(var/k in here)
			K[k]["stored"] += here[k]
			K[k]["where"] += list(list(name, here[k], T.x, T.y, T.z))
	// food in the pots and stalls (FoodSupply.dm)
	var/served = RemasterServedCount()
	if(served)
		K["food"]["stored"] += served
		K["food"]["where"] += list(list("Food pots and stalls", served, null, null, null))
	// what the villagers carry (gear and tools are their own, never counted)
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && !M.Wagon)
		var/list/mine = list()
		for(var/obj/Items/I in M) if(I.suffix == "(Carrying)" && !I.EquipmentType())
			var/k = RemasterResourceKind(I)
			if(k && K[k]) mine[k] = (mine[k] || 0) + 1
		for(var/k in mine)
			K[k]["carried"] += mine[k]
			K[k]["where"] += list(list("Carried by [M.RemasterBareName()]", mine[k], M.x, M.y, M.z, 1))
	rm_stores_cache = list("order"=rm_store_kinds.Copy(), "kinds"=K)
	return rm_stores_cache
