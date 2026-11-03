// Lifts (Build tab, Power). A lift carries units between levels: from the surface down to the
// tunnels, from the tunnels up, or up a cliff onto a mountain top or a wall walk. Underneath it
// is the original stair pair (Stairs.dmi at the same spot on both levels, Building/Stairs.dm),
// so move orders, builders and the hover use a lift as they use stairs (WallWalks.dm's
// RemasterStairsTowards, the original turf Entered). Its winch stands at the end it was built
// from and takes 6 power from the drive train beside it (Power.dm). While the train turns the
// pair are lift stairs ("LiftUp" below, "LiftDown" above); without power they are a still shaft
// ("LiftOffU", "LiftOffD"), which is no stair: no one is carried and routes go round it.

turf/var/remaster_lift = 0      // the level at the other end (0: not a lift); kept in world saves

obj/Items/Furniture/RemasterPower/Winch
	// its values: art/items/catalogue.json row furniture.remasterpower.winch (export_items.py writes ItemData.dm)
	PowerDemand()
		return 6
	Del()
		if(isturf(loc)) RemasterLiftSet(loc, 0)
		return ..()

// The other end, for the 3D view (the head frame over a shaft, the landing at a cliff top).
obj/Items/Furniture/RemasterLiftHead
	// its values: art/items/catalogue.json row furniture.remasterlifthead (export_items.py writes ItemData.dm)

// The level a lift from z goes to, up or down (0: none).
proc/RemasterLiftLevel(z, up)
	if(up)
		if(z == UNDERGROUND_LAYER) return GROUND_LAYER
		if(z == GROUND_LAYER) return SKY_LAYER
		return 0
	if(z == GROUND_LAYER) return UNDERGROUND_LAYER
	if(z == SKY_LAYER) return GROUND_LAYER
	return 0

// Deepest first: the tunnels, the surface, the sky layer.
proc/RemasterLevelRank(z)
	if(z == UNDERGROUND_LAYER) return 0
	if(z == GROUND_LAYER) return 1
	if(z == SKY_LAYER) return 2
	return -1

proc/RemasterLiftOther(turf/T)
	if(!T || !T.remaster_lift) return null
	var/turf/O = locate(T.x, T.y, T.remaster_lift)
	if(!O || O.remaster_lift != T.z) return null
	return O

// Powered or still: both ends' states (the lower end is the "Up" stair, the upper the "Down").
proc/RemasterLiftSet(turf/T, on)
	var/turf/O = RemasterLiftOther(T)
	if(!O) return
	var/turf/low = RemasterLevelRank(T.z) < RemasterLevelRank(O.z) ? T : O
	var/turf/high = low == T ? O : T
	var/ls = on ? "LiftUp" : "LiftOffU"
	var/hs = on ? "LiftDown" : "LiftOffD"
	if(low.icon_state == ls && high.icon_state == hs) return
	low.icon_state = ls
	high.icon_state = hs
	for(var/turf/X in list(low, high)) remaster_dirty_turfs["[X.x],[X.y],[X.z]"] = 1

proc/RemasterLiftOn(turf/T)
	return T && T.remaster_lift && T.icon == 'Stairs.dmi' && (T.icon_state == "LiftUp" || T.icon_state == "LiftDown")

proc/RemasterLiftMode(mode)
	if(mode == "Piece:liftup") return "up"
	if(mode == "Piece:liftdown") return "down"
	return null

proc/RemasterLiftCatalog()
	. = list()
	var/list/F = RemasterBuildDef("lift_up", "Lift up", "power", "Piece:liftup", "wood", 1, 'Stairs.dmi', "WoodUp", "Anyone with hands; from here up a level: from the tunnels to the surface, or at the foot of a cliff or a wall walk up onto it. The winch stands here and takes 6 power from an axle beside it")
	F["piececost"] = "6 wood"
	. += list(F)
	F = RemasterBuildDef("lift_down", "Lift down", "power", "Piece:liftdown", "wood", 1, 'Stairs.dmi', "WoodDown", "Anyone with hands; from here down a level: a shaft down to the tunnels, or from a mountain top or wall walk down. The winch stands here and takes 6 power from an axle beside it")
	F["piececost"] = "6 wood"
	. += list(F)

proc/RemasterLiftBlocked(turf/T, mode)
	var/up = RemasterLiftMode(mode) == "up"
	var/L = RemasterLiftLevel(T.z, up)
	if(!L) return up ? "there is no level above here" : "there is no level below here"
	if(T.icon == 'Stairs.dmi') return "there are stairs there already"
	var/turf/O = locate(T.x, T.y, L)
	if(!O) return "there is no level [up ? "above" : "below"] here"
	if(O.icon == 'Stairs.dmi') return "there are stairs at the other end"
	if((O.density || O.opacity) && O.icon_state != "CaveWall") return "something blocks the other end"
	if(up && O.Detailed) return "a floor is built over it"
	// up to the sky layer: the top lands beside a mountain top or a wall walk
	var/turf/top = L == SKY_LAYER ? O : (T.z == SKY_LAYER ? T : null)
	if(top)
		var/ok = 0
		for(var/d in list(NORTH, SOUTH, EAST, WEST))
			var/turf/N = get_step(top, d)
			if(N && !N.density && (N.icon_state == "Peak" || N.remaster_wallwalk || N.Detailed)) ok = 1
		if(!ok) return "the top must come out beside a mountain top or a wall walk"
	if(RemasterPowerAt(T)) return "a drive piece stands there"
	for(var/obj/Items/Furniture/X in T) if(X.density || X.remaster_placed) return "something stands there already"
	for(var/mob/WorkShops/W in T) return "a workshop stands there"
	return null

// Builds the lift from the tile beside T: six wood, both ends made the original stair pair, the
// winch on T, the head on the other end. It starts still; the power loop sets it going.
Player/proc/RemasterBuildLift(mob/Monsters/M, turf/T, mode)
	var/up = RemasterLiftMode(mode) == "up"
	var/L = RemasterLiftLevel(T.z, up)
	var/turf/O = L ? locate(T.x, T.y, L) : null
	if(!O || RemasterLiftBlocked(T, mode)) return 0
	var/list/woods = list()
	for(var/obj/Items/woods/wood/X in M) if(X.suffix != "(Equipped)") woods += X
	if(length(woods) < 6) return 0
	for(var/k = 1, k <= 6, k++)
		var/obj/Items/X = woods[k]
		if(M.DropItem(X)) del(X)
	O.ClearTurf()
	rm_ways_ver++   // stairs made: units held for a way to another level look again at once (Attack.dm, B)
	for(var/turf/X in list(T, O))
		X.underlays += icon(X.icon, X.icon_state)
		X.icon = 'Stairs.dmi'
		X.Detailed = 1
	T.remaster_lift = O.z
	O.remaster_lift = T.z
	RemasterLiftSet(T, 0)
	var/obj/Items/Furniture/RemasterPower/Winch/W = new
	W.Owner = src
	W.remaster_owner_key = key
	W.loc = T
	var/obj/Items/Furniture/RemasterLiftHead/H = new
	H.Owner = src
	H.remaster_owner_key = key
	H.loc = O
	M.WoodCraftingSkill += 1
	return 1

// The 3D model of either end: the lower end of a cliff lift (a timber tower up to the top), of
// a shaft up from the tunnels (a frame to the ceiling), the head frame over a shaft down, the
// landing at a cliff top; "on" while it runs.
proc/Remaster3DLiftModel(atom/movable/A)
	var/turf/T = A.loc
	var/turf/O = RemasterLiftOther(T)
	var/on = RemasterLiftOn(T) ? "on" : "off"
	if(!O) return list("liftshaft", on, null)
	if(RemasterLevelRank(T.z) < RemasterLevelRank(O.z)) return list(O.z == SKY_LAYER ? "liftcliff" : "liftshaft", on, null)
	return list(T.z == SKY_LAYER ? "liftlanding" : "liftheadframe", on, null)
