// Doors and floors in Plan mode (plan-doors-floors, 10-30; the owner: "so these buildings are like a set it and forget
// right i can drag tiles on the floor pick how high i want them and etc? pick door location and etc? what about the
// floor tiles"). Two more Plan mode tools, on the ground (art/hud/src/045):
//  - Door: a tile in a wall line kept open for a door. Queued, a build plan's blocks there on its two levels (0, 1) come
//    off it (the gap; any over it stay, a wall over the door held by the walls beside it: the layered builder phase 3),
//    and the door waits (rm_plan_doors) until the walls on two opposite sides of it are in with nothing more queued on
//    them; then it is planned as the Place tab's Gate is (Construction.dm: a door made at the carpentry, hung by the
//    builders). Built over meanwhile, or a door there already: it is dropped.
//  - Floor: stone or wooden floor tiles, planned at once as the Place tab's floors are (the builders lay them); never on
//    a tile a build plan still has its floor block queued on (a storey's floor over it is no matter).
// Waiting doors are drawn in 3D as a door frame (RmPlanDoors3D, art/hud/src/045); a floor's tiles show as the Place
// tab's blueprints do.

Player/var/list/rm_plan_doors           // saved: "x,y" -> 1, doors waiting for their walls
Player/var/tmp/rm_plan_door_next = 0

// "x,y/x,y/...": the door tiles marked in Plan mode.
Player/proc/RmPlanDoors(value)
	var/n = 0
	var/cut = 0
	var/bad = 0
	var/opened = 0
	for(var/c in splittext("[value]", "/"))
		var/list/p = splittext(c, ",")
		if(length(p) < 2) continue
		var/up = length(p) >= 3 ? text2num(p[3]) : 0
		if(up > 0)   // an opening in a wall upstairs (the layered builder, phase 2): its block there and the one over it off the build plans; no door
			var/turf/G = locate(text2num(p[1]), text2num(p[2]), GROUND_LAYER)
			var/got = 0
			if(G && RemasterMayWork(G, 1) && rm_jz) for(var/list/Z in rm_jz) if(Z["kind"] == "build" && islist(Z["cells"]))
				for(var/k = up, k <= min(up + 1, RM_BUILD_TOP), k++)
					var/kk = "[G.x],[G.y],[k]"
					if(!(kk in Z["cells"])) continue
					Z["cells"] -= kk
					Z["total"] = max(0, Z["total"] - 1)
					got++
			if(got)
				opened++
				cut += got
			else bad++
			continue
		var/turf/T = locate(text2num(p[1]), text2num(p[2]), GROUND_LAYER)
		if(!T || T.density || !RemasterMayWork(T, 1) || RemasterSiegeDoor(T))
			bad++
			continue
		if(!rm_plan_doors) rm_plan_doors = list()
		if(rm_plan_doors["[T.x],[T.y]"]) continue
		if(rm_jz) for(var/list/Z in rm_jz) if(Z["kind"] == "build" && islist(Z["cells"]))   // the gap: off the build plans, its two levels (a wall over it stays)
			for(var/k = 0, k <= 1, k++)
				var/kk = "[T.x],[T.y],[k]"
				if(!(kk in Z["cells"])) continue
				Z["cells"] -= kk
				Z["total"] = max(0, Z["total"] - 1)
				cut++
		rm_plan_doors["[T.x],[T.y]"] = 1
		n++
	if(opened) RemasterNotice("[opened] opening[opened > 1 ? "s" : ""] left in the walls upstairs: a doorway each, no door up there.")
	if(!n)
		if(!opened) RemasterNotice(bad ? "A door goes in a gap in a wall line (upstairs: in a wall still to be built), on your own land." : "Those doors are planned already.")
		return opened
	RemasterNotice("[n] door[n > 1 ? "s" : ""] planned: [n > 1 ? "each is" : "it is"] made at the carpentry and hung once the walls beside [n > 1 ? "them" : "it"] are up[cut ? " ([cut] planned block[cut > 1 ? "s" : ""] taken off for the gap)" : ""].")
	rm_plan_door_next = 0
	RmPlanDoorTick()
	return n

// A build plan still has a block queued on this column (up to level top).
Player/proc/RmPlanQueuedAt(turf/T, top = RM_BUILD_TOP)
	if(!T || !rm_jz) return 0
	for(var/list/Z in rm_jz) if(Z["kind"] == "build" && islist(Z["cells"]) && T.x >= Z["x0"] && T.x <= Z["x1"] && T.y >= Z["y0"] && T.y <= Z["y1"])
		for(var/k = 0, k <= top, k++) if("[T.x],[T.y],[k]" in Z["cells"]) return 1
	return 0

// Walls in on two opposite sides of T, nothing more queued on them.
Player/proc/RmPlanDoorWalls(turf/T)
	for(var/list/pr in list(list(WEST, EAST), list(NORTH, SOUTH)))
		var/turf/A = get_step(T, pr[1])
		var/turf/B = get_step(T, pr[2])
		if(A && B && RemasterBlockThere(A, 0) && RemasterBlockThere(B, 0) && !RmPlanQueuedAt(A) && !RmPlanQueuedAt(B)) return 1
	return 0

// Every 3 s from the settlement's tick: a door whose walls are up is planned (the Place tab's Gate).
Player/proc/RmPlanDoorTick()
	if((!length(rm_plan_doors) && !length(rm_plan_steps)) || world.time < rm_plan_door_next) return
	rm_plan_door_next = world.time + 30
	if(length(rm_plan_steps)) RmPlanStepTick()   // the stairs' steps (below)
	if(length(rm_plan_doors)) for(var/c in rm_plan_doors.Copy())
		var/list/p = splittext(c, ",")
		var/turf/T = locate(text2num(p[1]), text2num(p[2]), GROUND_LAYER)
		if(!T || T.density || RemasterSiegeDoor(T) || RemasterBlueprintAt(T))   // built over, or a door there already
			rm_plan_doors -= c
			continue
		if(!RmPlanDoorWalls(T)) continue
		rm_plan_doors -= c
		var/list/R = RmPlanPieces("Gate", list(T))
		if(R[1]) RemasterLog("The walls round your door at [T.x],[T.y] are up: its door is ordered from the carpentry.", "work", T)

// The stairs' steps (the layered builder, phase 3, 10-30; the owner: "if someone does a 2 story or 3 story house in one
// drag plan does it also include the beams and etc?"). The Building tool lays a flight of three blocks, one, two and
// three high, up each storey: "x,y,k,d/...", block k of x,y is a step, a one-block ramp rising d (Gather.dm's carved
// ramp: units step up it, a storey in three), made once that block is laid with room over it. A step built over, or its
// block on no plan any more: dropped.
Player/var/list/rm_plan_steps           // saved: "x,y,k" -> the way it rises (NORTH...)

Player/proc/RmPlanSteps(value)
	var/n = 0
	for(var/c in splittext("[value]", "/"))
		var/list/p = splittext(c, ",")
		if(length(p) < 4) continue
		var/turf/T = locate(text2num(p[1]), text2num(p[2]), GROUND_LAYER)
		var/k = text2num(p[3])
		var/d = text2num(p[4])
		if(!T || !isnum(k) || k < 0 || k >= RM_BUILD_TOP || !(d in list(NORTH, SOUTH, EAST, WEST)) || !RemasterMayWork(T, 1)) continue
		if(!rm_plan_steps) rm_plan_steps = list()
		rm_plan_steps["[T.x],[T.y],[k]"] = d
		if(rm_jz) for(var/list/Z in rm_jz) if(Z["kind"] == "build" && T.x >= Z["x0"] && T.x <= Z["x1"] && T.y >= Z["y0"] && T.y <= Z["y1"])
			Z["stairs"] = 1   // its workers go up by them (Plans.dm RmPlanAccess, RmPlanWayThere)
			if(!Z["stairs_k"] || k + 1 < Z["stairs_k"])   // the lowest step's foot: where they set off up
				var/turf/FT = get_step(T, turn(d, 180))
				Z["stairs_k"] = k + 1
				Z["stairs_at"] = FT ? "[FT.x],[FT.y]" : null
		n++
	if(n && rm_jz) for(var/c in splittext("[value]", "/"))   // the floors its flights lead up to: a top step's height + 1 (Sites.dm RmPlanHoldFor)
		var/list/p = splittext(c, ",")
		if(length(p) < 4) continue
		var/turf/T = locate(text2num(p[1]), text2num(p[2]), GROUND_LAYER)
		var/k = text2num(p[3])
		var/turf/N = T ? get_step(T, text2num(p[4])) : null
		if(!N || !rm_plan_steps["[T.x],[T.y],[k]"] || rm_plan_steps["[N.x],[N.y],[k + 1]"]) continue
		for(var/list/Z in rm_jz) if(Z["kind"] == "build" && T.x >= Z["x0"] && T.x <= Z["x1"] && T.y >= Z["y0"] && T.y <= Z["y1"])
			if(!islist(Z["floors"])) Z["floors"] = list()
			Z["floors"] |= k + 1
	if(n)
		rm_plan_door_next = 0
		RmPlanDoorTick()
	return n

// With the doors' tick (every 3 s): each step whose block is in becomes its ramp.
Player/proc/RmPlanStepTick()
	for(var/c in rm_plan_steps.Copy())
		var/list/p = splittext(c, ",")
		var/turf/T = locate(text2num(p[1]), text2num(p[2]), GROUND_LAYER)
		var/k = text2num(p[3])
		var/d = rm_plan_steps[c]
		if(!T || RemasterBlockThere(T, k + 1))
			rm_plan_steps -= c
			continue
		if(!RemasterBlockThere(T, k))
			var/on = 0
			if(rm_jz) for(var/list/Z in rm_jz) if(Z["kind"] == "build" && islist(Z["cells"]) && (c in Z["cells"]))
				on = 1
				break
			if(!on) rm_plan_steps -= c
			continue
		rm_plan_steps -= c
		if(RemasterSlopeOn(T)) continue
		T.remaster_slope = d
		T.remaster_slope_h = k + 1
		rm_ways_ver++   // a way up made: units held for one look again at once (Attack.dm, B)
		remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1
		RemasterFeetCheck(T)

// A ramp carved into a column's floor block (the first step of a building's stairs, or any ramp up from the ground):
// the one way between the ground and the tops there. Units only pass over it; a hop down starts from it (Gather.dm).
proc/RmFirstStep(turf/U)
	var/turf/G = U ? locate(U.x, U.y, GROUND_LAYER) : null
	return G && G.remaster_slope && G.remaster_slope_h == 1 && RemasterSlopeOn(G)

// A step of a flight with the next step up after it (a ramp, then one a block higher the way it rises): a way through,
// not a place to stop and work. In the real game six builders waited on a building's first step for its second, where
// one coming down waited for the first: nobody may stop on a friend's tile, so none moved (probe, 10-30).
proc/RmStairPassage(turf/U)
	var/turf/G = U ? locate(U.x, U.y, GROUND_LAYER) : null
	if(!G || !RemasterSlopeOn(G)) return 0
	var/turf/N = get_step(G, G.remaster_slope)
	return N && RemasterSlopeOn(N) && N.remaster_slope_h == G.remaster_slope_h + 1

// Whether a build plan of this player's still wants block k of the column at x,y (none laid there yet): nobody stands
// there to work (Gather.dm RemasterWorkSpot): a builder up a building's stairs stood on its unfinished walls and held
// back their next blocks (arena tests/storeys.dm).
Player/proc/RmPlanWantsAt(x, y, k)
	if(!rm_jz) return 0
	var/c = "[x],[y],[k]"
	for(var/list/Z in rm_jz) if(Z["kind"] == "build" && islist(Z["cells"]) && x >= Z["x0"] && x <= Z["x1"] && y >= Z["y0"] && y <= Z["y1"] && (c in Z["cells"])) return 1
	return 0

// A building's stairs still to come: a step of plan Z whose lowest block still to lay goes on from the ground (two up
// at most) and can go on now. The plan's workers wait for them rather than cut another way up (Plans.dm
// RmPlanWayThere): a way cut early stood a worker on a wall's unfinished corner and the house never finished (arena
// tests/storeys.dm). A flight higher up (on a storey's floor) is reached by the one under it: not waited for.
Player/proc/RmPlanStairsComing(list/Z)
	if(!length(rm_plan_steps) || !islist(Z["cells"])) return 0
	for(var/c in rm_plan_steps)
		var/list/p = splittext(c, ",")
		var/x = text2num(p[1])
		var/y = text2num(p[2])
		if(x < Z["x0"] || x > Z["x1"] || y < Z["y0"] || y > Z["y1"]) continue
		var/turf/T = locate(x, y, GROUND_LAYER)
		var/k = text2num(p[3])
		for(var/j = 0, j <= k, j++)
			if(RemasterBlockThere(T, j) || !("[x],[y],[j]" in Z["cells"])) continue
			if(j <= 2 && RmPlanCanLay(T, j, src)) return 1
			break
	return 0

// "stone or wood|x,y/x,y/...": the floor tiles marked in Plan mode.
Player/proc/RmPlanFloors(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 2) return 0
	var/wood = p[1] == "wood"
	var/mode = wood ? "PlaceWoodenFloor" : "PlaceStoneFloor"
	var/list/tiles = list()
	var/walls = 0
	for(var/c in splittext(p[2], "/"))
		var/list/q = splittext(c, ",")
		if(length(q) < 2) continue
		var/turf/T = locate(text2num(q[1]), text2num(q[2]), GROUND_LAYER)
		if(!T) continue
		if(RmPlanQueuedAt(T, 0) || (rm_plan_doors && rm_plan_doors["[T.x],[T.y]"]))
			walls++
			continue
		tiles += T
	var/list/R = RmPlanPieces(mode, tiles)
	var/n = R[1]
	if(!n)
		RemasterNotice("No floor planned: [walls ? "a wall or door is planned there" : (R[3] || "those tiles are planned already")].")
		return 0
	var/text = "Planned [n] tile[n > 1 ? "s" : ""] of [wood ? "wooden" : "stone"] floor"
	if(R[2] || walls) text += " ([R[2] + walls] skipped: [walls ? "a wall or door planned there" : R[3]])"
	text += ". [RemasterSiteNeedText(R[4])]. [RmBuildCrewHint(1)]"
	RemasterNotice(text)
	return n

// Pieces planned as the Place tab plans them (Blueprints.dm RemasterPaint): one construction task, a blueprint a tile.
// list(planned, skipped, why, the task).
Player/proc/RmPlanPieces(mode, list/tiles)
	if(!remaster_blueprints) remaster_blueprints = list()
	var/list/S = RemasterSiteNew(mode, GROUND_LAYER)
	var/added = 0
	var/skipped = 0
	var/why
	var/sx = 0
	var/sy = 0
	for(var/turf/T in tiles)
		if(length(remaster_blueprints) >= REMASTER_BLUEPRINT_MAX) break
		if(RemasterBlueprintAt(T)) continue
		var/blocked = RemasterBuildBlocked(T, mode)
		if(blocked || !RemasterMayWork(T, 1))
			skipped++
			why = blocked || "someone else's land"
			continue
		remaster_blueprints += list(list("x"=T.x, "y"=T.y, "z"=T.z, "mode"=mode, "note"="Waiting for a builder", "tries"=0, "site"=S["id"]))
		sx += T.x
		sy += T.y
		added++
	if(!added)
		remaster_sites -= list(S)
		return list(0, skipped, why, null)
	S["x"] = round(sx / added)
	S["y"] = round(sy / added)
	S["left"] = added
	S["total"] = added
	return list(added, skipped, why, S)

// The doors waiting for their walls round the camera, for the 3D view: list(x, y, 1 when it spans east-west).
Player/proc/RmPlanDoors3D(cx, cy, r)
	var/list/out = list()
	for(var/c in rm_plan_doors)
		var/list/p = splittext(c, ",")
		var/x = text2num(p[1])
		var/y = text2num(p[2])
		if(abs(x - cx) > r || abs(y - cy) > r) continue
		var/turf/T = locate(x, y, GROUND_LAYER)
		var/ew = 1
		if(T)
			var/turf/N = get_step(T, NORTH)
			var/turf/S = get_step(T, SOUTH)
			if((N && (RemasterBlockThere(N, 0) || RmPlanQueuedAt(N))) && (S && (RemasterBlockThere(S, 0) || RmPlanQueuedAt(S)))) ew = 0
		out += list(list(x, y, ew))
		if(length(out) >= 60) break
	return out

// Stone and logs in the stores, for the Place list's Structure and Plan mode's card (the board's counts, Board.dm), kept 5 s.
Player/var/tmp/list/rm_sw_cache
Player/var/tmp/rm_sw_at = -1000
Player/proc/RmStoneWood()
	if(!rm_sw_cache || world.time - rm_sw_at >= 50)
		rm_sw_cache = list(RemasterStockCount("stone"), RemasterStockCount("wood"))
		rm_sw_at = world.time
	return rm_sw_cache

// --- Saved designs (the layered builder, 10-30; the plan: "save what you made or generated, stamp it anywhere, turned")
// Plan mode's marks kept by name in the player's profile (Rarity.dm RemasterProfilePath), so they go with the player
// from game to game: name -> the page's text of them (remastered.html pmDesigns). The card's Designs tool places one
// anywhere, turned, as marks queued like any others. At most RM_DESIGNS, each RM_DESIGN_TEXT long at most.
#define RM_DESIGNS 24
#define RM_DESIGN_TEXT 16000
Player/var/tmp/list/rm_designs

Player/proc/RmDesignsLoad()
	if(rm_designs) return rm_designs
	rm_designs = list()
	if(ckey && fexists(RemasterProfilePath(ckey)))
		var/savefile/S = new(RemasterProfilePath(ckey))
		var/list/L
		S["designs"] >> L
		if(islist(L)) for(var/n in L) if(RmDesignName(n) == n && RmDesignText(L[n])) rm_designs[n] = L[n]
	return rm_designs

// "save|name|text", "del|name" or "list" from the page (HUD.dm "pmdesign"); the list goes back to it each time.
Player/proc/RmDesigns(value)
	var/list/p = splittext("[value]", "|")
	var/list/D = RmDesignsLoad()
	var/what = length(p) ? p[1] : ""
	var/changed = 0
	if(what == "save" && length(p) >= 3)
		var/name = RmDesignName(p[2])
		if(name && RmDesignText(p[3]))
			if(!(name in D) && length(D) >= RM_DESIGNS) RemasterNotice("You can keep [RM_DESIGNS] designs: delete one first.")
			else
				D[name] = p[3]
				changed = 1
	else if(what == "del" && length(p) >= 2 && (p[2] in D))
		D -= p[2]
		changed = 1
	if(changed && ckey)
		var/savefile/S = new(RemasterProfilePath(ckey))
		S["designs"] << D
	var/list/L = list()
	for(var/n in D) L += list(list(n, D[n]))
	if(client) src << output(url_encode(json_encode(L)), "mapwindow.hud:pmDesigns")

// A design's name as kept: letters, digits, spaces and - ' ( ), 32 at most, no spaces round it; null when none is left.
proc/RmDesignName(t)
	if(!istext(t)) return null
	var/out = ""
	for(var/i = 1, i <= length(t) && length(out) < 32, i++)
		var/c = text2ascii(t, i)
		if((c >= 48 && c <= 57) || (c >= 65 && c <= 90) || (c >= 97 && c <= 122) || c == 32 || c == 39 || c == 40 || c == 41 || c == 45) out += ascii2text(c)
	while(length(out) && text2ascii(out, 1) == 32) out = copytext(out, 2)
	while(length(out) && text2ascii(out, length(out)) == 32) out = copytext(out, 1, length(out))
	return length(out) ? out : null

// A design's text as the page writes it: digits, lowercase letters and , . / - only, RM_DESIGN_TEXT long at most (a ";"
// never comes through: the engine's link params split on it, as on "&").
proc/RmDesignText(t)
	if(!istext(t) || !length(t) || length(t) > RM_DESIGN_TEXT) return 0
	for(var/i = 1, i <= length(t), i++)
		var/c = text2ascii(t, i)
		if(!((c >= 48 && c <= 57) || (c >= 97 && c <= 122) || c == 44 || c == 45 || c == 46 || c == 47)) return 0
	return 1
