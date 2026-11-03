// Gates worked from a lever (Build tab, Fortress): a portcullis and a drawbridge. Both are rune
// devices (Runes.dm), kinds of rune door: a lever or pressure plate on their circuit (rune lines
// from it to the gate) raises or drops them. Gates of a kind touching side by side are one gate
// (a portcullis across a gap up to three wide, a drawbridge across a moat and as wide as its
// gateway): they move together, once a pull. Moving one takes 3 mana from the circuit's crystals,
// or nothing at all while it touches a turning drive train (Power.dm): the winch does the work.
// None of it closes while someone stands in any part of it.
//  - Portcullis: in a gap of up to three tiles between two walls (or rock: a tunnel mouth). Down
//    it bars the way but can be seen and shot through; up it lets anyone by.
//  - Drawbridge: on water or lava, built out from the bank across a moat up to five tiles wide,
//    hinged on the gate's side. Down it is the original bridge (Building.dm's turf change); up the
//    water is open again and no one crosses.

#define RM_GATE_MANA 3
#define RM_GATE_WIDE 3        // a portcullis gap, tiles across
#define RM_MOAT_WIDE 5        // a moat a drawbridge spans, tiles across

// world/New: this file's part is step RmChainWorldNew_Gates in Code/Remastered/Chains/WorldNew.dm

// The gate G belongs to: the pieces of its kind joined to it side by side.
proc/RemasterGateGroup(obj/RemasterRune/Door/G)
	. = list(G)
	var/list/todo = list(G)
	while(length(todo))
		var/obj/RemasterRune/Door/X = todo[length(todo)]
		todo.len--
		for(var/d in list(NORTH, SOUTH, EAST, WEST))
			for(var/obj/RemasterRune/Door/Y in get_step(X, d)) if(Y.type == G.type && !(Y in .))
				. += Y
				todo += Y

// Energy to move a gate: a turning drive train beside any piece of it, or mana from its circuit.
proc/RemasterGateEnergy(list/grp)
	for(var/obj/RemasterRune/G in grp) for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/obj/Items/Furniture/RemasterPower/X = RemasterPowerAt(get_step(G, d))
		if(X && X.pnet && X.pnet.on) return "power"
	if(rm_runes_dirty) RemasterRuneRebuild()
	var/obj/RemasterRune/F = grp[1]
	if(F.net && RemasterRuneSpend(F.net, RM_GATE_MANA)) return "mana"
	return null

// A pull: the whole gate goes the other way, or none of it (someone in it as it would close;
// no power or mana). A pull reaches every piece of the gate (they touch: one circuit), so its
// north-west piece moves it all and the others let it. A pull from the HUD's door button
// (no source) has paid already and moves the gate of the piece it was given.
proc/RemasterGateAct(obj/RemasterRune/Door/G, obj/RemasterRune/source)
	var/list/grp = RemasterGateGroup(G)
	if(source) for(var/obj/RemasterRune/Door/X in grp) if(X.y > G.y || (X.y == G.y && X.x < G.x)) return
	var/closing = G.open
	if(closing) for(var/obj/RemasterRune/Door/X in grp) for(var/mob/Monsters/M in X.loc) return   // units only (the player's own camera stands about too)
	if(source && !RemasterGateEnergy(grp)) return
	for(var/obj/RemasterRune/Door/X in grp)
		if(closing) X.Shut()
		else X.Open()

obj/RemasterRune/Door/Portcullis
	name = "portcullis"
	rune_id = "portcullis"
	opacity = 0
	RuneAct(obj/RemasterRune/source)
		RemasterGateAct(src, source)
	Open()
		open = 1
		density = 0
		opacity = 0
		icon_state = "door_open"
	Shut()
		open = 0
		density = 1
		opacity = 0      // a grating: seen and shot through
		icon_state = "door_shut"

obj/RemasterRune/Door/Drawbridge
	name = "drawbridge"
	rune_id = "drawbridge"
	density = 0
	opacity = 0
	RuneAct(obj/RemasterRune/source)
		RemasterGateAct(src, source)
	Open()    // down: the original wooden bridge over the water (Building.dm), stone over lava
		var/turf/T = loc
		open = 1
		density = 0
		opacity = 0
		icon_state = "door_open"
		if(!isturf(T) || T.isbridge) return
		var/lava = T.Content3 == "Lava" || findtext("[T.icon_state]", "Lava")
		T.density = 0
		T.CanFish = 0
		T.name = null
		T.isbridge = 1
		T.Detailed = !lava
		T.Cant = 1
		if(T.CaveWater == 1) T.CaveWater = 0
		T.icon = 'Cave.dmi'
		T.icon_state = lava ? "LavaBridge" : "WoodBridge"
		remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1
	Shut()    // up: the water as it was (the original taking-up of a bridge, ClearTurf)
		var/turf/T = loc
		open = 0
		density = 0
		opacity = 0
		icon_state = "door_shut"
		if(!isturf(T) || !T.isbridge) return
		T.ClearTurf()
		remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1

// --- Building (Buildings.dm's pieces) -----------------------------------------------------------
proc/RemasterGateMode(mode)
	if(mode == "Piece:portcullis") return "portcullis"
	if(mode == "Piece:drawbridge") return "drawbridge"
	return null

proc/RemasterGateCatalog()
	. = list()
	var/list/F = RemasterBuildDef("portcullis", "Portcullis", "fortress", "Piece:portcullis", "wood", 1, 'Icons/Remastered/Runes.dmi', "door_shut", "Anyone with hands; in a gap of up to 3 tiles between two walls, or in a tunnel mouth (paint the gap: its pieces move as one). Lay rune lines from a lever to it: the lever raises and drops it (3 mana a time, or free while an axle turning beside it drives it)")
	F["piececost"] = "4 wood"
	. += list(F)
	F = RemasterBuildDef("drawbridge", "Drawbridge", "fortress", "Piece:drawbridge", "wood", 1, 'Cave.dmi', "WoodBridge", "Anyone with hands; across a moat before a gate, up to 5 tiles wide and as wide as you like (paint it: it is built out from the bank and moves as one). Down it is a bridge, up no one crosses. Worked from a lever by rune lines, like a portcullis")
	F["piececost"] = "4 wood"
	. += list(F)

proc/RemasterGateLiquid(turf/T)
	return T && !T.isbridge && (T.Content3 == "Liquid" || T.Content3 == "Lava" || findtext("[T.icon_state]", "Water"))

// The way the gap runs (the walls either side): NORTH for walls north and south, EAST for
// walls east and west; 0 when T is in no gap of up to RM_GATE_WIDE tiles between two jambs.
proc/RemasterGateGap(turf/T)
	for(var/pair in list(list(NORTH, SOUTH), list(EAST, WEST)))
		var/run = 1
		var/ends = 0
		for(var/d in pair)
			var/turf/C = T
			for(var/k = 1, k <= RM_GATE_WIDE, k++)
				C = get_step(C, d)
				if(!C || RemasterGateLiquid(C)) break
				if(C.density && !(locate(/obj/RemasterRune/Door/Portcullis) in C))
					ends++
					break
				run++
		if(ends == 2 && run <= RM_GATE_WIDE) return pair[1]
	return 0

proc/RemasterGateDry(turf/T)
	return T && !T.density && !RemasterGateLiquid(T)

proc/RemasterGateBlocked(turf/T, mode)
	var/id = RemasterGateMode(mode)
	if(RemasterRuneAt(T)) return "a rune piece is there already"
	if(id == "drawbridge")
		if(!RemasterGateLiquid(T)) return "a drawbridge goes on a water or lava tile (a moat)"
		// across a moat: dry ground within RM_MOAT_WIDE tiles straight out from it
		for(var/d in list(NORTH, SOUTH, EAST, WEST))
			var/turf/C = T
			for(var/k = 1, k <= RM_MOAT_WIDE, k++)
				C = get_step(C, d)
				if(RemasterGateDry(C)) return null
				if(!RemasterGateLiquid(C) && !(locate(/obj/RemasterRune/Door/Drawbridge) in C)) break
		return "a drawbridge spans a moat up to [RM_MOAT_WIDE] tiles wide: no bank near enough"
	if(T.density) return "a portcullis goes in an open gap"
	if(!RemasterGateGap(T)) return "a portcullis goes in a gap of up to [RM_GATE_WIDE] tiles between two walls (or rock)"
	if(T.icon == 'Stairs.dmi') return "there are stairs there"
	for(var/obj/Items/Furniture/X in T) if(X.density || X.remaster_placed) return "something stands there already"
	for(var/mob/WorkShops/W in T) return "a workshop stands there"
	return null

// A drawbridge is built out from the bank: a tile with no bank beside it waits for the piece
// beside it (whose deck its builder stands on).
proc/RemasterGateWait(turf/T, mode)
	if(RemasterGateMode(mode) != "drawbridge") return null
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/N = get_step(T, d)
		if(RemasterGateDry(N) || (locate(/obj/RemasterRune/Door/Drawbridge) in N)) return null
	return "Built out from the bank: waits for the drawbridge beside it"

// The hinge of a drawbridge: the dry side, a gateway (a gate, door or portcullis beside it) first.
proc/RemasterDrawbridgeHinge(turf/T)
	var/best = 0
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/N = get_step(T, d)
		if(!N || N.density || RemasterGateLiquid(N)) continue
		if(RemasterGateGap(N) || (locate(/obj/RemasterRune/Door) in N) || (locate(/obj/Items/Furniture/Doors) in N)) return d
		if(!best) best = d
	return best || SOUTH

Player/proc/RemasterBuildGatePiece(mob/Monsters/M, turf/T, mode)
	var/id = RemasterGateMode(mode)
	if(!id || RemasterGateBlocked(T, mode)) return 0
	var/list/woods = list()
	for(var/obj/Items/woods/wood/X in M) if(X.suffix != "(Equipped)") woods += X
	if(length(woods) < 4) return 0
	for(var/k = 1, k <= 4, k++)
		var/obj/Items/X = woods[k]
		if(M.DropItem(X)) del(X)
	if(id == "portcullis")
		var/obj/RemasterRune/Door/Portcullis/G = new(T)
		G.owner_key = key
		G.dir = RemasterGateGap(T)     // NORTH: across a north-south gap... the walls' line
		G.Open()                       // built up, so no one is shut out
	else
		var/obj/RemasterRune/Door/Drawbridge/G = new(T)
		G.owner_key = key
		G.dir = RemasterDrawbridgeHinge(T)
		for(var/d in list(NORTH, SOUTH, EAST, WEST))   // part of a bridge already begun: its hinge
			var/obj/RemasterRune/Door/Drawbridge/N = locate() in get_step(T, d)
			if(N)
				G.dir = N.dir
				break
		G.Open()                       // built down: a bridge
	M.WoodCraftingSkill += 1
	return 1
