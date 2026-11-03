// Power (Build tab, "Power"). Water wheels and windmills turn axles; machines on the axles
// use what they make (lifts too: Lifts.dm). Pieces touching side by side (N, S, E, W) are one drive train, as rune
// pieces make one circuit (Runes.dm). A water wheel stands on the bank with water beside it
// (10 power); a windmill on open ground under the sky (6, or 10 on a mountain top). Bellows
// beside a forge, smelter or melter take 4: while their train turns, the smith there works
// twice as fast. A rune dynamo touching a rune circuit takes 5 and charges its crystals (a
// mana a second, several times their own trickle). A train that can't feed all its machines
// runs none of them. Lifts are meant to run on the same trains.

#define RM_POWER_TICK 10

var/list/rm_power_parts = list()
var/rm_power_dirty = 1
var/list/rm_power_nets = list()
var/rm_power_running = 0

/datum/rm_powernet
	var/list/parts = list()
	var/supply = 0
	var/demand = 0
	var/on = 0

// id -> list(label, type, material, pieces of it, build-menu sprite, who/what)
proc/RemasterPowerDefs()
	return list(
		"waterwheel"=list("Water wheel", /obj/Items/Furniture/RemasterPower/Wheel, "wood", 4, "Shaft", "On a bank with water beside it: 10 power"),
		"windmill"=list("Windmill", /obj/Items/Furniture/RemasterPower/Windmill, "wood", 5, "Shaft", "Under the open sky: 6 power, 10 on a mountain top"),
		"axle"=list("Axle", /obj/Items/Furniture/RemasterPower/Axle, "wood", 1, "Shaft", "Drag a line: carries power from wheels to machines"),
		"bellows"=list("Bellows", /obj/Items/Furniture/RemasterPower/Bellows, "wood", 2, "Shaft", "Beside a forge, smelter or melter: the smith works twice as fast. Takes 4 power"),
		"dynamo"=list("Rune dynamo", /obj/Items/Furniture/RemasterPower/Dynamo, "stone", 3, "Shaft", "Touching a rune circuit: charges its mana crystals. Takes 5 power"))

proc/RemasterPowerMode(mode)
	if(copytext(mode, 1, 7) != "Piece:") return null
	var/id = copytext(mode, 7)
	return (id in RemasterPowerDefs()) ? id : null

obj/Items/Furniture/RemasterPower
	// its values: art/items/catalogue.json row furniture.remasterpower (export_items.py writes ItemData.dm)
	var/power_id
	var/tmp/datum/rm_powernet/pnet
	var/tmp/link = 0            // which neighbours it joins (N 1, S 2, E 4, W 8), for drawing
	New()
		..()
		rm_power_parts += src
		rm_power_dirty = 1
		if(!rm_power_running)
			rm_power_running = 1
			spawn(0) RemasterPowerLoop()
	Del()
		rm_power_parts -= src
		rm_power_dirty = 1
		return ..()

obj/Items/Furniture/RemasterPower/proc/PowerSupply()
	return 0

obj/Items/Furniture/RemasterPower/proc/PowerDemand()
	return 0

obj/Items/Furniture/RemasterPower/Wheel
	// its values: art/items/catalogue.json row furniture.remasterpower.wheel (export_items.py writes ItemData.dm)
	PowerSupply()
		return RemasterPowerWater(loc) ? 10 : 0

obj/Items/Furniture/RemasterPower/Windmill
	// its values: art/items/catalogue.json row furniture.remasterpower.windmill (export_items.py writes ItemData.dm)
	PowerSupply()
		return RemasterPowerWind(loc)

obj/Items/Furniture/RemasterPower/Axle
	// its values: art/items/catalogue.json row furniture.remasterpower.axle (export_items.py writes ItemData.dm)

obj/Items/Furniture/RemasterPower/Bellows
	// its values: art/items/catalogue.json row furniture.remasterpower.bellows (export_items.py writes ItemData.dm)
	PowerDemand()
		return 4

obj/Items/Furniture/RemasterPower/Dynamo
	// its values: art/items/catalogue.json row furniture.remasterpower.dynamo (export_items.py writes ItemData.dm)
	PowerDemand()
		return 5

// The way to water beside T (0: none). Bridged water doesn't turn a wheel.
proc/RemasterPowerWater(turf/T)
	if(!isturf(T)) return 0
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/N = get_step(T, d)
		if(!N || N.isbridge) continue
		if(N.Content3 == "Liquid" || findtext("[N.icon_state]", "Water")) return d
	return 0

proc/RemasterPowerWind(turf/T)
	if(!isturf(T) || T.remaster_roof > 0) return 0
	if(T.z == SKY_LAYER) return 10
	if(T.z == GROUND_LAYER) return 6
	return 0

proc/RemasterPowerAt(turf/T)
	if(!T) return null
	return locate(/obj/Items/Furniture/RemasterPower) in T

// Drive trains: flood fill over pieces touching side by side.
proc/RemasterPowerRebuild()
	rm_power_dirty = 0
	rm_power_nets = list()
	for(var/obj/Items/Furniture/RemasterPower/R in rm_power_parts) R.pnet = null
	for(var/obj/Items/Furniture/RemasterPower/R in rm_power_parts)
		if(R.pnet || !isturf(R.loc)) continue
		var/datum/rm_powernet/N = new
		rm_power_nets += N
		var/list/todo = list(R)
		R.pnet = N
		while(length(todo))
			var/obj/Items/Furniture/RemasterPower/X = todo[length(todo)]
			todo.len--
			N.parts += X
			X.link = 0
			var/bit = 1
			for(var/d in list(NORTH, SOUTH, EAST, WEST))
				var/obj/Items/Furniture/RemasterPower/Y = RemasterPowerAt(get_step(X, d))
				if(Y)
					X.link |= bit
					if(!Y.pnet)
						Y.pnet = N
						todo += Y
				bit *= 2

proc/RemasterPowerCount(datum/rm_powernet/N)
	N.supply = 0
	N.demand = 0
	for(var/obj/Items/Furniture/RemasterPower/X in N.parts)
		N.supply += X.PowerSupply()
		N.demand += X.PowerDemand()
	N.on = N.supply > 0 && N.supply >= N.demand

proc/RemasterPowerLoop()
	rm_power_running = 1
	while(length(rm_power_parts))
		sleep(RM_POWER_TICK)
		RemasterPowerTick()
	rm_power_running = 0

proc/RemasterPowerTick()
	if(rm_power_dirty) RemasterPowerRebuild()
	for(var/datum/rm_powernet/N in rm_power_nets)
		RemasterPowerCount(N)
		for(var/obj/Items/Furniture/RemasterPower/Winch/W in N.parts) RemasterLiftSet(W.loc, N.on)   // Lifts.dm
		if(!N.on) continue
		for(var/obj/Items/Furniture/RemasterPower/Dynamo/D in N.parts) RemasterDynamoCharge(D)

// A turning dynamo: a mana a second into the emptiest crystal of the rune circuit it touches.
proc/RemasterDynamoCharge(obj/Items/Furniture/RemasterPower/Dynamo/D)
	var/obj/RemasterRune/R
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		R = RemasterRuneAt(get_step(D, d))
		if(R) break
	if(!R) return 0
	if(rm_runes_dirty) RemasterRuneRebuild()
	if(!R.net) return 0
	var/obj/RemasterRune/Crystal/low
	for(var/obj/RemasterRune/Crystal/C in R.net.crystals) if(!low || C.charge < low.charge) low = C
	if(!low || low.charge >= RM_CRYSTAL_MAX) return 0
	low.charge = min(RM_CRYSTAL_MAX, low.charge + RM_POWER_TICK / 10)
	return 1

// A forge, smelter or melter with turning bellows beside it (or beside its other half).
proc/RemasterStationPowered(mob/WorkShops/W)
	if(!W || !(istype(W, /mob/WorkShops/Forge) || istype(W, /mob/WorkShops/Smelters) || istype(W, /mob/WorkShops/Melter))) return 0
	if(rm_power_dirty) RemasterPowerRebuild()
	for(var/mob/WorkShops/X in range(1, W)) if(X == W || X.type == W.type || X.Owner == W.Owner)
		for(var/obj/Items/Furniture/RemasterPower/Bellows/B in range(1, X))
			if(!B.pnet) continue
			RemasterPowerCount(B.pnet)
			if(B.pnet.on) return 1
	return 0

// Bellows: a smith who just made something at a powered station has a second go.
mob/Monsters/RemasterStationTick(Player/P, list/O)
	var/before = remaster_board_since
	..()
	if(remaster_board_since == before || remaster_board_since != world.time) return
	for(var/mob/WorkShops/W in range(1, src)) if(RemasterStationPowered(W))
		..()
		return

// --- Building (Buildings.dm's pieces) ----------------------------------------------------------
proc/RemasterPowerCatalog()
	. = list()
	var/list/D = RemasterPowerDefs()
	for(var/id in D)
		var/list/E = D[id]
		var/list/F = RemasterBuildDef(id, E[1], "power", "Piece:[id]", E[3], 1, 'Cave.dmi', E[5], "Anyone with hands; [E[6]]")
		F["piececost"] = "[E[4]] [E[3]]"
		if(id == "axle") F["piececost"] = "1 wood per tile"
		. += list(F)

proc/RemasterPowerNeed(mode)
	if(RemasterLiftMode(mode)) return 6    // Lifts.dm
	if(RemasterGateMode(mode)) return 4    // Gates.dm
	var/id = RemasterPowerMode(mode)
	if(!id) return 0
	var/list/E = RemasterPowerDefs()[id]
	return E[4]

proc/RemasterPowerBlocked(turf/T, mode)
	var/id = RemasterPowerMode(mode)
	if(RemasterPowerAt(T)) return "there's a drive piece there already"
	if(T.icon_state == "Sky" || T.Content3 == "Liquid" || T.Content3 == "Lava" || T.Content == "Chasm" || T.icon == 'Stairs.dmi') return "it goes on the ground"
	if(id == "waterwheel" && !RemasterPowerWater(T)) return "a water wheel goes on the bank, beside water"
	if(id == "windmill" && !RemasterPowerWind(T)) return "a windmill needs the open sky (not underground or under rock)"
	for(var/obj/Items/Furniture/X in T) if(X.density || X.remaster_placed) return "something stands there already"
	for(var/mob/WorkShops/W in T) return "a workshop stands there"
	return null

Player/proc/RemasterBuildPower(mob/Monsters/M, turf/T, mode)
	var/id = RemasterPowerMode(mode)
	var/list/E = id ? RemasterPowerDefs()[id] : null
	if(!E) return 0
	var/path = RemasterMaterialPath(E[3])
	var/list/have = list()
	for(var/obj/Items/X in M) if(istype(X, path) && X.suffix != "(Equipped)") have += X
	if(length(have) < E[4]) return 0
	for(var/k = 1, k <= E[4], k++)
		var/obj/Items/X = have[k]
		if(M.DropItem(X)) del(X)
	var/ptype = E[2]
	var/obj/Items/Furniture/RemasterPower/P = new ptype
	P.Owner = src
	P.remaster_owner_key = key
	P.dir = id == "waterwheel" ? RemasterPowerWater(T) : SOUTH
	P.loc = T
	return 1

// What the HUD and hover say about a piece's train.
proc/RemasterPowerText(obj/Items/Furniture/RemasterPower/X)
	if(rm_power_dirty) RemasterPowerRebuild()
	var/datum/rm_powernet/N = X.pnet
	if(!N) return "Not connected"
	RemasterPowerCount(N)
	if(!N.supply) return "Not turning: no wheel or windmill turning on this train"
	if(!N.on) return "Not enough power: [N.supply] made, [N.demand] wanted"
	return "Turning: [N.supply] power, [N.demand] used"

// The 3D model (View3D.dm's Remaster3DObjModel): the piece, "on" while its train turns.
proc/Remaster3DPowerModel(obj/Items/Furniture/RemasterPower/X)
	if(istype(X, /obj/Items/Furniture/RemasterPower/Winch)) return Remaster3DLiftModel(X)   // Lifts.dm
	if(rm_power_dirty) RemasterPowerRebuild()
	var/on = 0
	if(X.pnet) on = X.pnet.on || (X.PowerSupply() > 0)   // counted each second by the power loop
	var/m = X.power_id
	if(m == "axle") m = "axle[X.link]"
	return list(m, on ? "on" : "off", null)
