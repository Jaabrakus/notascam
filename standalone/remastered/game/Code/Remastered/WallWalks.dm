// Wall-walks (Remastered). In Lord of the Rings fortresses every wall carries a
// walkway its defenders man. Here every built wall on the surface that is not the
// wall of a house gets one on the layer above (the Sky layer, which the 3D view
// stacks on top of the surface at storey height):
//  - it is the floor the original game already lets you lay on a supported sky tile
//    above a wall (Building.dm), laid by itself when the wall is finished;
//  - stairs lead up to it (the original stairs, or quick wall stairs: Remaster
//    WallStairs below), and move orders climb them by themselves (Orders.dm);
//  - two units fit on each walk tile, a front and a back rank;
//  - it falls when the wall under it is breached or dug out, and whoever stood on
//    it comes down; when a house closes round a wall, its empty walk is taken up.
// Walks are worked out from the walls (once at start, then as walls change), so
// they need no saving of their own.

turf/var/tmp/remaster_wallwalk = 0       // 1 on a wall, 2 over a gate between two walls
turf/var/tmp/remaster_ramp = 0           // a ramp tile leading up to wall stairs (walked on; 3D draws the slope)
turf/var/tmp/remaster_walkface = 0       // outer sides (N 1, S 2, E 4, W 8) + 16 once worked out: crenellated in 3D
var/list/remaster_wallwalks = list()     // walk tiles (sky turfs) -> 1
var/list/remaster_walls = list()         // surface walls that may carry a walk -> 1
var/remaster_wall_cursor = 1

// world/New: this file's part is step RmChainWorldNew_WallWalks in Code/Remastered/Chains/WorldNew.dm

// A house wall: an enclosed room (Rooms.dm) beside it, corners included, whose floor
// is mostly built; or a hut: a small room (up to REMASTER_HUT_MAX tiles) whatever its
// floor, with a way in (a placed door, or an open doorway: a one-tile gap in a wall line).
// A fort's courtyard is enclosed too, but bigger (or sealed): its walls keep their walks.
#define REMASTER_HUT_MAX 40
#define REMASTER_HUT_MIN 4
proc/RemasterWallIsHouse(turf/T)
	for(var/d in list(NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST))
		var/turf/N = get_step(T, d)
		if(!N || RemasterRoomWall(N)) continue
		var/list/room = RemasterRoomFill(N)
		if(room)
			var/floors = 0
			for(var/turf/F in room) if(F.Detailed && F.icon != 'Stairs.dmi' && F.icon_state != "FarmLand") floors++
			if(floors * 2 >= length(room)) return 1
		var/list/hut = RemasterHutFill(N)
		if(hut && length(hut) >= REMASTER_HUT_MIN && RemasterHutEntrance(hut)) return 1
	return 0

// An open doorway: a gap between two solid tiles in a line. Water and lava are no jambs (a
// strip of bank between a wall and a moat is not a doorway).
proc/RemasterDoorway(turf/T)
	if(!T || T.density) return 0
	for(var/pair in list(list(NORTH, SOUTH), list(EAST, WEST)))
		var/turf/A = get_step(T, pair[1])
		var/turf/B = get_step(T, pair[2])
		if(RemasterJamb(A) && RemasterJamb(B)) return 1
	return 0

proc/RemasterJamb(turf/T)
	return T && T.density && T.Content3 != "Liquid" && T.Content3 != "Lava"

// A hut's floor: flooded like a room (Rooms.dm), but open doorways close it too; null past
// REMASTER_HUT_MAX tiles.
proc/RemasterHutFill(turf/T)
	if(RemasterRoomWall(T) || RemasterDoorway(T)) return null
	var/list/seen = list()
	seen[T] = 1
	var/list/q = list(T)
	while(length(q))
		var/turf/C = q[length(q)]
		q.len--
		for(var/d in list(NORTH, SOUTH, EAST, WEST))
			var/turf/N = get_step(C, d)
			if(!N || seen[N] || RemasterRoomWall(N) || RemasterDoorway(N)) continue
			seen[N] = 1
			if(length(seen) > REMASTER_HUT_MAX) return null
			q += N
	. = list()
	for(var/turf/X in seen) . += X

// A way into the hut: a placed door or an open doorway on its edge.
proc/RemasterHutEntrance(list/hut)
	for(var/turf/F in hut)
		for(var/d in list(NORTH, SOUTH, EAST, WEST))
			var/turf/E = get_step(F, d)
			if(RemasterGateLeaf(E) || RemasterDoorway(E)) return 1
	return 0

proc/RemasterWallStands(turf/T)
	return T && T.z == GROUND_LAYER && T.IsWall && T.density

// What shuts a gate: a placed door, or a portcullis (Gates.dm), up or down.
proc/RemasterGateLeaf(turf/T)
	return T && (RemasterSiegeDoor(T) || (locate(/obj/RemasterRune/Door/Portcullis) in T))

// A gate: a placed door (or a portcullis) in a one-tile gap between two standing walls in a line. Its walk is
// carried over it like an arch, when the walls on both sides have walks. A gap without a door
// (a breach) stays open to the sky.
proc/RemasterGateStands(turf/G)
	if(!G || G.z != GROUND_LAYER || G.density || !RemasterGateLeaf(G)) return 0
	for(var/pair in list(list(NORTH, SOUTH), list(EAST, WEST)))
		var/turf/A = get_step(G, pair[1])
		var/turf/B = get_step(G, pair[2])
		if(RemasterWallStands(A) && RemasterWallStands(B))
			var/turf/AS = locate(A.x, A.y, SKY_LAYER)
			var/turf/BS = locate(B.x, B.y, SKY_LAYER)
			if(AS && BS && AS.remaster_wallwalk == 1 && BS.remaster_wallwalk == 1) return 1
	return 0

// Which sides of a wall face out: open ground beside it that runs on (more than 3000 tiles,
// not enclosed by walls, doors and rock). Those are crenellated; a side facing an enclosed
// court gets a low lip. A free-standing wall (enclosing nothing) is crenellated only on the
// sides turned away from the nearest settlement (claim banner within 80 tiles), with a lip
// towards it; with no settlement near, on every open side. +16 marks the answer as worked out
// (0 means not yet: the 3D view crenellates both).
proc/RemasterWallOuter(turf/W)
	var/list/bits = list("[NORTH]"=1, "[SOUTH]"=2, "[EAST]"=4, "[WEST]"=8)
	var/out = 0
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/N = get_step(W, d)
		if(!N || N.density || RemasterGateStands(N)) continue   // a gate beside it carries the walk on
		if(RemasterRegionLeaks(N, 3000)) out |= bits["[d]"]
	if(out)
		var/obj/RemasterBanner/B = RemasterNearestBanner(W, 80)
		if(B)
			// the faces turned towards the settlement (it lies north: the north face)
			var/toward = (B.y > W.y ? 1 : B.y < W.y ? 2 : 0) | (B.x > W.x ? 4 : B.x < W.x ? 8 : 0)
			if((out & toward) && RemasterWallFree(W, out)) out &= ~toward
	return out | 16

// A wall that encloses nothing here: every open tile round it (diagonals too, for corners) and the
// land across it (thick walls, up to three tiles) runs on into open country.
proc/RemasterWallFree(turf/W, out)
	var/list/bits = list("[NORTH]"=1, "[SOUTH]"=2, "[EAST]"=4, "[WEST]"=8)
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/N = get_step(W, d)
		if(!N || N.density || RemasterGateStands(N)) continue
		if(!(out & bits["[d]"])) return 0    // an enclosed court beside it
	for(var/d in list(NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST))
		var/turf/N = get_step(W, d)
		if(!N || N.density || RemasterGateStands(N)) continue
		if(out & (bits["[d & (NORTH|SOUTH)]"] | bits["[d & (EAST|WEST)]"])) continue    // joins open land beside it
		if(!RemasterRegionLeaks(N, 3000)) return 0    // the inside of a corner
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		if(!(out & bits["[d]"])) continue
		var/turf/A = get_step(W, turn(d, 180))
		for(var/k = 1, k <= 3 && A && A.density, k++) A = get_step(A, turn(d, 180))
		if(!A || A.density || A == get_step(W, turn(d, 180)) || RemasterGateStands(A)) continue
		if(!RemasterRegionLeaks(A, 3000)) return 0    // a thick wall round a court
	return 1

proc/RemasterNearestBanner(turf/T, range)
	var/obj/RemasterBanner/best
	var/bd = range + 1
	for(var/obj/RemasterBanner/B in rm_banners)
		if(!B.loc || B.z != T.z) continue
		var/d = max(abs(B.x - T.x), abs(B.y - T.y))
		if(d < bd)
			bd = d
			best = B
	return best

// The pass's floods share their answers (server cost, 2026-10-23): a flood's answer holds for every tile it reached
// (they are one region), so the walls of a town share a few floods instead of up to a dozen each. The answers are kept
// for the pass's 3 s and used only by its own checks (RemasterWallWalkChecks), so no wall's answer is older than when
// the pass checked all forty at one moment, and a wall just built (RemasterWallBuilt) is still worked out afresh. Only
// floods from an open tile are shared (one started on a door crosses it).
var/list/rm_leak_memo         // during a pass: turf -> 1 (leaks) or 0 (enclosed)
var/rm_leak_memo_on = 0       // set only while the pass's checks run

proc/RemasterRegionLeaks(turf/T, limit)
	var/list/memo = (rm_leak_memo_on && rm_leak_memo && limit == 3000 && T && !T.density && !RemasterGateLeaf(T)) ? rm_leak_memo : null
	if(memo && !isnull(memo[T])) return memo[T]
	var/list/seen = list()
	var/list/q = list(T)
	seen[T] = 1
	var/leaks = 0
	// Breadth first: the answer is the same whichever way the flood goes (more than limit tiles, or the map's edge), and
	// a flood that stops at the limit has covered the land round where it started, which the town's other walls share.
	for(var/i = 1, i <= length(q) && !leaks, i++)
		var/turf/C = q[i]
		for(var/d in list(NORTH, SOUTH, EAST, WEST))
			var/turf/N = get_step(C, d)
			if(!N)
				leaks = 1
				break
			if(seen[N] || N.density || RemasterGateLeaf(N)) continue   // doors close a court, as they close rooms
			seen[N] = 1
			if(length(seen) > limit)
				leaks = 1
				break
			q += N
	if(memo) for(var/turf/X in seen) memo[X] = leaks
	return leaks

// Lay the walk on the sky tile above a standing wall. Only an empty sky tile:
// anything already built up there (a floor, a wall, stairs) is left as it is.
proc/RemasterWallWalkRaise(turf/W, turf/S)
	if(!S || S.remaster_wallwalk) return S && S.remaster_wallwalk
	if(S.icon_state != "Sky" || S.density || S.Detailed) return 0
	S.remaster_wallwalk = 1
	S.Supported = 1
	S.Detailed = 1
	S.density = 0
	S.opacity = 0
	S.IsWood = W.IsWood ? 1 : 0
	S.icon_state = W.IsWood ? "WoodFloor" : "DetailedFloor"
	S.name = "Wall walk"
	S.text = "<font color=#888888>="
	remaster_wallwalks[S] = 1
	return 1

// Take a walk up. breached: the wall under it is gone, so whoever stood there falls.
proc/RemasterWallWalkLower(turf/S, breached)
	remaster_wallwalks -= S
	if(!S || !S.remaster_wallwalk) return
	S.remaster_wallwalk = 0
	S.Detailed = 0
	S.IsWood = 0
	S.icon_state = "Sky"
	S.name = "Sky"
	S.text = "<font color=#33FFFF>M-W"
	var/turf/G = locate(S.x, S.y, GROUND_LAYER)
	for(var/mob/Monsters/M in S)
		if(M.Flying) continue
		var/turf/D = (G && !G.density) ? G : null
		if(!D && G)
			for(var/turf/N in orange(1, G))
				if(!N.density)
					D = N
					break
		if(!D) continue
		M.loc = D
		M.destination = null
		if(breached)
			M.HP = max(1, M.HP - round(M.MAXHP / 10))
			if(istype(M.Owner, /Player)) M.Owner:RemasterNotice("[M.name] falls from the broken wall.")

proc/RemasterWallWalkCheck(turf/W)
	var/turf/S = locate(W.x, W.y, SKY_LAYER)
	if(!S) return
	var/house = RemasterWallIsHouse(W)
	if(!house && !S.remaster_wallwalk) RemasterWallWalkRaise(W, S)
	else if(house && S.remaster_wallwalk && !(locate(/mob/Monsters) in S)) RemasterWallWalkLower(S, 0)
	if(S.remaster_wallwalk) S.remaster_walkface = RemasterWallOuter(W)
	// Gates beside this wall: carry the walk over them.
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/G = get_step(W, d)
		if(!RemasterGateStands(G)) continue
		var/turf/GS = locate(G.x, G.y, SKY_LAYER)
		if(GS && !GS.remaster_wallwalk && RemasterWallWalkRaise(W, GS))
			GS.remaster_wallwalk = 2
			GS.remaster_walkface = S.remaster_walkface

// What a click means at T: on a surface wall top (3D "up"), the walk above it.
proc/RemasterWalkClickTurf(turf/T, up)
	if(up && T && T.z == GROUND_LAYER)
		var/turf/U = locate(T.x, T.y, SKY_LAYER)
		if(U && U.remaster_wallwalk) return U
		if(U && !U.density && U.icon_state == "Peak" && RemasterIsMountain(T)) return U    // a mountain top (Mountains.dm)
	return T

proc/RemasterWallBuilt(turf/T)
	remaster_walls[T] = 1
	RemasterWallWalkCheck(T)
	// the walls it joins lose an open side at once (their teeth on that side go)
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/N = get_step(T, d)
		if(N && remaster_walls[N]) RemasterWallWalkCheck(N)

// Walls are built through the original turf/MouseDrag (map drags and blueprints alike).
turf/MouseDrag(atom/over)
	var/turf/T = isturf(over) ? over : src
	var/was = RemasterWallStands(T)
	. = ..()
	if(T && !was && RemasterWallStands(T)) RemasterWallBuilt(T)

proc/RemasterWallWalkLoop()
	set background = 1
	if(world.maxz < SKY_LAYER) return
	// The walls already standing (a loaded world), found once, a few rows at a time.
	for(var/ty = 1, ty <= world.maxy, ty++)
		for(var/tx = 1, tx <= world.maxx, tx++)
			var/turf/T = locate(tx, ty, GROUND_LAYER)
			if(T && T.IsWall && T.density) remaster_walls[T] = 1
		if(!(ty % 25)) sleep(1)
	// Every 3 s: breached walks fall, then forty walls are looked at, four every 3 ticks, so no tick carries all
	// forty (one pass of them cost 0.1-1.1 s in one tick on the full map; reports/server-cost/).
	while(1)
		RemasterWallWalkFalls()
		rm_leak_memo = list()
		for(var/part = 1, part <= 10, part++)
			RemasterWallWalkChecks(4)
			sleep(3)
		rm_leak_memo = null

// The same in one go (tests).
proc/RemasterWallWalkPass()
	RemasterWallWalkFalls()
	rm_leak_memo = list()
	RemasterWallWalkChecks(40)
	rm_leak_memo = null

// A walk whose wall is gone falls at once.
proc/RemasterWallWalkFalls()
	for(var/turf/S in remaster_wallwalks.Copy())
		var/turf/B = locate(S.x, S.y, GROUND_LAYER)
		if(S.remaster_wallwalk == 2 ? !RemasterGateStands(B) : !RemasterWallStands(B)) RemasterWallWalkLower(S, 1)

// Walls are looked at forty a pass: houses close and open slowly. (Nobody falls in these checks: a walk is only
// taken up here with no one on it, so the checks themselves never change the ground the floods look at.)
proc/RemasterWallWalkChecks(n)
	var/list/L = remaster_walls
	rm_leak_memo_on = 1
	for(var/k = 1, k <= n && length(L), k++)
		if(remaster_wall_cursor > length(L)) remaster_wall_cursor = 1
		var/turf/W = L[remaster_wall_cursor]
		if(!RemasterWallStands(W))
			L.Cut(remaster_wall_cursor, remaster_wall_cursor + 1)
			continue
		remaster_wall_cursor++
		RemasterWallWalkCheck(W)
	rm_leak_memo_on = 0

// --- Ranks -------------------------------------------------------------------------
// Two units to a walk tile: a front and a back rank (the 3D view draws them so).
proc/RemasterWalkRoom(turf/T, atom/movable/mover)
	if(!T || T.density) return 0
	var/n = 0
	for(var/atom/movable/A in T)
		if(A == mover || !A.density) continue
		if(!istype(A, /mob/Monsters)) return 0
		n++
	return n < 2

// turf/grounds/Enter: this file's part is step RmChainEnter_WallWalks in Code/Remastered/Chains/Enter.dm

// --- Stairs ------------------------------------------------------------------------
// The level a stairs tile leads to (turf/grounds/Entered's rule), or 0.
proc/RemasterStairsTo(turf/S)
	if(S && S.z == GROUND_LAYER && S.density && RemasterSlopeOn(S) && S.remaster_slope_h == 1) return SKY_LAYER   // a ramp carved into a rock's floor block (Gather.dm)
	if(!S || S.icon != 'Stairs.dmi') return 0
	if(copytext(S.icon_state, -2) == "Up")
		if(S.z == GROUND_LAYER) return SKY_LAYER
		if(S.z == UNDERGROUND_LAYER) return GROUND_LAYER
	if(copytext(S.icon_state, -4) == "Down")
		if(S.z == GROUND_LAYER) return UNDERGROUND_LAYER
		if(S.z == SKY_LAYER) return GROUND_LAYER
	return 0

// The stairs that best take M towards A on another level: near M, landing near A.
proc/RemasterStairsTowards(mob/Monsters/M, turf/A, list/skip = null)
	var/turf/best
	var/score = 1000000
	for(var/turf/S in range(25, M))
		if(RemasterStairsTo(S) != A.z || (skip && (S in skip))) continue
		var/s = get_dist(M, S) + get_dist(locate(S.x, S.y, A.z), A)
		if(s < score)
			score = s
			best = S
	return best

// The stairs a "Climb" (O) can find no way to: others that lead to the same level, the best of those it hasn't tried for
// the way it is going. The nearest pair is chosen by distance alone, so a pair walled in (a closed building, someone's
// yard) held a unit beside it for good, "No way through yet; trying again", with free stairs a few tiles off. None left
// to try: it keeps trying these, as before, and looks no more (no cost after that).
datum/remaster_order/var/list/stairs_tried
datum/remaster_order/var/stairs_none = 0   // tried every other pair in reach: it keeps to these, with no more looking
mob/Monsters/proc/RemasterStairsElsewhere(datum/remaster_order/O)
	if(O.stairs_none) return 0
	if(!O.stairs_tried) O.stairs_tried = list()
	O.stairs_tried |= O.target
	var/datum/remaster_order/N = length(remaster_orders) ? remaster_orders[1] : null
	var/turf/goal = N ? RemasterTurf(N.target) : null
	if(!goal || goal.z != O.climb_z) goal = locate(O.target.x, O.target.y, O.climb_z)
	var/turf/S = goal ? RemasterStairsTowards(src, goal, O.stairs_tried) : null
	if(!S)
		O.stairs_none = 1
		return 0
	O.target = S
	RemasterStartOrder(O)
	return 1

// A ramp up the inside of a wall (Helm's Deep): three tiles along a wall that has a walk,
// starting at T. The two lower tiles are walkable ramp floor, the top one is the original
// stair pair onto the walk, so units walk up the slope and step onto the wall at its head.
// A selected unit beside the spot carrying three stone builds it.
Player/proc/RemasterWallRamp(turf/T)
	if(RemasterWallStands(T)) return RemasterWallRampInto(T)
	if(!T || T.z != GROUND_LAYER || T.density || T.icon == 'Stairs.dmi')
		RemasterNotice("A ramp starts on open ground beside a wall.")
		return 0
	var/wall_dir = 0
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/W = get_step(T, d)
		var/turf/WW = W ? locate(W.x, W.y, SKY_LAYER) : null
		if(WW && WW.remaster_wallwalk == 1)
			wall_dir = d
			break
	if(!wall_dir)
		RemasterNotice("Ramps go beside a wall that has a walk.")
		return 0
	var/list/run
	var/list/along = (wall_dir == NORTH || wall_dir == SOUTH) ? list(EAST, WEST) : list(NORTH, SOUTH)
	for(var/a in along)
		var/list/R = list(T)
		var/turf/C = T
		for(var/k = 1, k < 3, k++)
			C = get_step(C, a)
			var/turf/CW = C ? get_step(C, wall_dir) : null
			var/turf/CWW = CW ? locate(CW.x, CW.y, SKY_LAYER) : null
			if(!C || C.density || C.icon == 'Stairs.dmi' || !CWW || CWW.remaster_wallwalk != 1) break
			R += C
		if(length(R) == 3)
			run = R
			break
	var/turf/top = run ? run[3] : null
	var/turf/U = top ? locate(top.x, top.y, SKY_LAYER) : null
	if(!run || !U || U.density || U.icon == 'Stairs.dmi' || (U.Detailed && !U.remaster_wallwalk))
		RemasterNotice("A ramp needs three open tiles along the wall.")
		return 0
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || M.z != T.z || get_dist(M, T) > 1) continue
		var/list/stone = list()
		for(var/obj/Items/ores/stone/S in M) if(length(stone) < 3) stone += S
		if(length(stone) < 3) continue
		for(var/obj/Items/ores/stone/S in stone) if(M.DropItem(S)) del(S)
		if(U.remaster_wallwalk) RemasterWallWalkLower(U, 0)
		U.ClearTurf()
		rm_ways_ver++   // stairs made: units held for a way to another level look again at once (Attack.dm, B)
		for(var/turf/X in list(top, U))
			X.underlays += icon(X.icon, X.icon_state)
			X.icon = 'Stairs.dmi'
			X.Detailed = 1
		top.icon_state = "StoneUp"
		U.icon_state = "StoneDown"
		U.Supported = 1
		for(var/k = 1, k <= 2, k++)
			var/turf/X = run[k]
			X.icon_state = "DetailedFloor"
			X.name = "Ramp"
			X.Detailed = 1
			X.remaster_ramp = k
		RemasterNotice("[M.name] builds a ramp up the wall.")
		return 1
	RemasterNotice("A selected unit beside the spot must carry three stone.")
	return 0

// A ramp cut into a wall (Helm's Deep): on a wall at least two tiles thick, the inner row from T
// along the wall (five tiles where there is room, at least three) becomes the ramp, inside the
// wall's own thickness, flush with its inner face; the rows behind stay full wall with their
// walk. The lower tiles turn into walkable ramp floor, the last into the stair pair onto the walk. The wall's own stone is
// reused, so it costs nothing; a selected unit must stand beside the spot.
Player/proc/RemasterWallRampInto(turf/T)
	var/front = 0
	var/back = 0
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/N = get_step(T, d)
		if(N && !N.density && RemasterWallStands(get_step(T, turn(d, 180))))
			front = d
			back = turn(d, 180)
			break
	if(!front)
		RemasterNotice("Cut a ramp into the inner row of a wall at least two tiles thick.")
		return 0
	var/list/run
	var/list/along = (front == NORTH || front == SOUTH) ? list(EAST, WEST) : list(NORTH, SOUTH)
	for(var/a in along)
		var/list/R = list()
		var/turf/C = T
		for(var/k = 1, k <= 5 && C, k++)
			var/turf/F = get_step(C, front)
			if(!RemasterWallStands(C) || !RemasterWallStands(get_step(C, back)) || !F || F.density) break
			R += C
			C = get_step(C, a)
		if(length(R) >= 3 && length(R) > length(run))
			run = R
	if(!run)
		RemasterNotice("A ramp needs three tiles of the wall's inner row, with wall behind them.")
		return 0
	var/mob/Monsters/builder
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.z == T.z && get_dist(M, T) <= 1) builder = M
	if(!builder)
		RemasterNotice("Select a unit standing beside the wall there.")
		return 0
	for(var/turf/C in run)
		var/turf/S = locate(C.x, C.y, SKY_LAYER)
		if(S && (locate(/mob/Monsters) in S))
			RemasterNotice("Clear the wall walk above first.")
			return 0
	for(var/k = 1, k <= length(run), k++)
		var/turf/C = run[k]
		var/turf/S = locate(C.x, C.y, SKY_LAYER)
		if(S && S.remaster_wallwalk) RemasterWallWalkLower(S, 0)
		remaster_walls -= C
		C.density = 0
		C.opacity = 0
		C.IsWall = 0
		C.CanDigAt = 0
		C.Detailed = 1
		C.icon_state = "DetailedFloor"
		C.name = "Ramp"
		C.text = "<font color=#888888>/"
		if(k < length(run)) C.remaster_ramp = k
		else
			S.ClearTurf()
			rm_ways_ver++   // stairs made: units held for a way to another level look again at once (Attack.dm, B)
			for(var/turf/X in list(C, S))
				X.underlays += icon(X.icon, X.icon_state)
				X.icon = 'Stairs.dmi'
				X.Detailed = 1
			C.icon_state = "StoneUp"
			S.icon_state = "StoneDown"
			S.Supported = 1
	for(var/turf/C in run) for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/W = get_step(C, d)
		if(RemasterWallStands(W)) RemasterWallWalkCheck(W)
	RemasterNotice("[builder.name] cuts a ramp into the wall.")
	return 1

// Quick wall stairs: the selected unit carrying stone (or wood) puts up a stairway
// against a wall that carries a walk, without the original's two questions. It is
// the original stair pair (Stairs.dm): Up here, Down on the walk level.
Player/proc/RemasterWallStairs(turf/T)
	if(!T || T.z != GROUND_LAYER || T.density || T.Detailed || T.icon == 'Stairs.dmi')
		RemasterNotice("Wall stairs go on open ground beside a wall.")
		return 0
	var/turf/U = locate(T.x, T.y, SKY_LAYER)
	var/beside = 0
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/W = get_step(T, d)
		var/turf/WW = W ? locate(W.x, W.y, SKY_LAYER) : null
		if(WW && WW.remaster_wallwalk) beside = 1
	if(!beside || !U || U.density || U.Detailed || U.icon == 'Stairs.dmi')
		RemasterNotice("Wall stairs need a wall with a walk next to them.")
		return 0
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || get_dist(M, T) > 1 || M.z != T.z) continue
		var/obj/Items/MAT = M.HasItem(/obj/Items/ores/stone/)
		var/kind = "Stone"
		if(!MAT)
			MAT = M.HasItem(/obj/Items/woods/wood/)
			kind = "Wood"
		if(!MAT) continue
		if(M.DropItem(MAT)) del(MAT)
		U.ClearTurf()
		rm_ways_ver++   // stairs made: units held for a way to another level look again at once (Attack.dm, B)
		for(var/turf/X in list(T, U))
			X.underlays += icon(X.icon, X.icon_state)
			X.icon = 'Stairs.dmi'
			X.Detailed = 1
		T.icon_state = "[kind]Up"
		U.icon_state = "[kind]Down"
		U.Supported = 1
		RemasterNotice("[M.name] puts up wall stairs.")
		return 1
	RemasterNotice("A selected unit next to the spot must carry stone or wood.")
	return 0
