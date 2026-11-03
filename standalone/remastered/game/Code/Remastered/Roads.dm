// Roads (Build tab, "Roads"): a cobbled road (1 stone per tile, used up) or a dirt track
// (free: a builder's labour), painted on open ground like a floor and laid by builders.
// Units walk faster along them: the time between steps is 0.7x on a road, 0.85x on a
// track (Specials.dm RemasterStepDelay). The ground under stays what it was; the road
// is turf/remaster_road, kept in world saves and drawn by the 3D view ("road").

#define REMASTER_ROAD_STONE 0.7
#define REMASTER_ROAD_DIRT 0.85

turf/var/remaster_road = null    // "stone" or "dirt"
mob/Monsters/var/tmp/remaster_step_carry = 0

proc/RemasterRoadMode(mode)
	return mode in list("PlaceStoneRoad", "PlaceDirtRoad", "RemoveRoad")

// Why a tile can't take this road (null when it can). A track can be cobbled over.
proc/RemasterRoadBlocked(turf/T, mode)
	if(mode == "RemoveRoad") return T.remaster_road ? null : "no road there"
	if(T.density) return "roads go on open ground"
	if(T.icon_state == "Sky") return "roads go on the ground"
	if(T.icon == 'Stairs.dmi') return "there are stairs there"
	if(T.Content3 == "Liquid" || T.Content3 == "Lava" || T.Content == "Chasm" || T.isbridge) return "roads don't go over water, lava or chasms (build a bridge)"
	if(T.Detailed) return "there's a built floor there"
	if(T.icon_state == "FarmLand") return "there's a field there"
	if(T.remaster_road == "stone") return "there's a cobbled road there already"
	if(T.remaster_road == "rail" && mode != "RemoveRoad") return "there's rail track there (Remove road takes it up)"
	if(T.remaster_road == "dirt" && mode == "PlaceDirtRoad") return "there's a track there already"
	return null

// A builder beside (or on) the tile lays it: a cobbled road uses up a stone from the bag.
Player/proc/RemasterBuildRoad(mob/Monsters/M, turf/T, mode)
	if(!T || !RemasterMayWork(T) || get_dist(M, T) > 1 || M.z != T.z) return 0
	if(RemasterRoadBlocked(T, mode)) return 0
	switch(mode)
		if("PlaceStoneRoad")
			var/obj/Items/ores/stone/S = locate() in M
			if(!S) return 0
			M.weight -= S.weight
			del(S)
			T.remaster_road = "stone"
		if("PlaceDirtRoad") T.remaster_road = "dirt"
		else T.remaster_road = null
	remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1    // a var only: the save's tile signature can't see it
	return 1

// Faster along roads. The fraction of a tick carries over to the next step, so the
// pace is right on average (a quick unit sometimes takes two steps in one tick).
mob/Monsters/proc/RemasterRoadDelay(d)
	var/turf/T = loc
	if(!isturf(T) || !T.remaster_road || Flying || T.remaster_road == "rail") return d   // rail track (Carts.dm): no faster on foot
	var/f = d * (T.remaster_road == "stone" ? REMASTER_ROAD_STONE : REMASTER_ROAD_DIRT) + remaster_step_carry
	var/whole = round(f)
	remaster_step_carry = f - whole
	return whole
