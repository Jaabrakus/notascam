// Getting onto mountains, and mining tunnel roofs (Remastered). Mining is one block an order
// (Breaking.dm): two orders open a rock tile into a two-high tunnel; then each Mine roof order
// takes the next block up.
// A surface mountain's top is the walkable peak on the sky layer above it (the 3D view
// draws the rock in layers: Breaking.dm). Units that can't climb get up by a run carved
// into the mountain:
//  - steps: dug straight in from the edge, rising up to two layers a tile;
//  - a ramp: dug along the mountain's face, rising a layer a tile.
// Each tile of the run is mined like any rock; once open it is a carved step, and the
// peak over it opens to the sky (a cut). The head of the run is the original stair pair
// onto the peak (Stairs.dmi Up here, Down on the peak), so move orders onto a mountain
// top climb it by themselves (Orders.dm). A tunnel's roof is mined from inside, a layer
// at a time; each layer lifts the ceiling, and with the last one the tile is open sky.
// Roof mining keeps the original cave-in rule: 5% a layer, with any pillar within four
// tiles holding the tunnel up (as when digging).

turf/var/remaster_carve = 0          // step k of a carved run (1..n); the head (n) is the stairs
turf/var/remaster_carve_n = 0        // tiles in the run
turf/var/remaster_carve_dir = 0      // the way the run climbs, towards its head
turf/var/remaster_carve_top = 0      // the mountain top it reaches, in layers
turf/var/remaster_carve_ramp = 0     // 1 a smooth ramp, 0 steps
turf/var/remaster_ceil = 0           // a tunnel's ceiling in layers (0: two, as dug)
turf/var/tmp/list/remaster_carve_plan     // list(k, n, dir, top, ramp) while it is being dug
turf/var/tmp/remaster_roof_hp = 0


// The way into the mountain at T, from the open side nearest the selected units.
Player/proc/RemasterCarveDir(turf/T)
	var/best = 0
	var/best_d = 1#INF
	var/mob/Monsters/F
	for(var/mob/Monsters/M in Selected) if(M.Owner == src)
		F = M
		break
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/O = get_step(T, turn(d, 180))
		if(!O || O.density) continue
		var/dd = F ? get_dist(F, O) : 0
		if(dd < best_d)
			best = d
			best_d = dd
	return best

Player/proc/RemasterCarve(turf/T, ramp, queued = 0)
	if(!T || T.z != GROUND_LAYER || !T.density || !T.CanDigAt || !RemasterIsMountain(T))
		RemasterNotice("Steps and ramps are carved into the rock at a mountain's edge.")
		return 0
	if(!RemasterMayWork(T)) return 0
	var/inward = RemasterCarveDir(T)
	if(!inward)
		RemasterNotice("Start at the mountain's edge, from open ground beside it.")
		return 0
	// steps go straight in; a ramp runs along the face (whichever way needs fewer tiles)
	var/list/run
	var/way
	var/top
	for(var/w in (ramp ? list(turn(inward, 90), turn(inward, -90)) : list(inward)))
		var/list/R = list()
		var/turf/C = T
		var/t = 0
		for(var/k = 1, k <= 6 && C, k++)
			if(!C.density || !C.CanDigAt || !RemasterIsMountain(C) || C.remaster_carve_plan) break
			R += C
			t = RemasterBlocksAt(C)
			if(length(R) >= 2 && length(R) * (ramp ? 1 : 2) >= t) break
			C = get_step(C, w)
		if(length(R) < 2 || length(R) * (ramp ? 1 : 2) < t) continue
		var/turf/head = R[length(R)]
		var/turf/U = locate(head.x, head.y, SKY_LAYER)
		if(!U || U.density || U.icon_state != "Peak") continue
		if(!run || length(R) < length(run))
			run = R
			way = w
			top = t
	if(!run)
		RemasterNotice(ramp ? "Not enough rock along the face here for a ramp up (it climbs a layer a tile, up to 6)." : "Not enough rock straight in from here for steps up (they climb two layers a tile, up to 6).")
		return 0
	var/n = length(run)
	var/k = 0
	for(var/turf/C in run)
		k++
		C.remaster_carve_plan = list(k, n, way, top, ramp ? 1 : 0)
	// dig them in order: the first now (or queued), the rest after it
	var/count = 0
	k = 0
	for(var/turf/C in run)
		k++
		count = RemasterOrder(C, k > 1 ? 1 : queued) || count
	if(!count)
		for(var/turf/C in run) C.remaster_carve_plan = null
		return 0
	RemasterNotice("[ramp ? "A ramp" : "Steps"] up the mountain: [n] tile\s to dig; the last becomes stairs onto the top.")
	return n

// A planned tile has just been dug out: it becomes a step of the run.
proc/RemasterCarveDone(turf/T)
	var/list/p = T.remaster_carve_plan
	T.remaster_carve_plan = null
	if(!p) return
	T.remaster_carve = p[1]
	T.remaster_carve_n = p[2]
	T.remaster_carve_dir = p[3]
	T.remaster_carve_top = p[4]
	T.remaster_carve_ramp = p[5]
	T.remaster_roof = 0
	T.remaster_ceil = 0
	var/turf/U = locate(T.x, T.y, SKY_LAYER)
	if(!U) return
	if(T.remaster_carve < T.remaster_carve_n)
		// the cut: the peak over it opens to the sky
		if(U.icon_state == "Peak")
			U.icon_state = "Sky"
			U.name = "Sky"
			U.Content = "Sky"
		return
	// the head: the original stair pair onto the peak
	U.ClearTurf()
	rm_ways_ver++   // stairs made: units held for a way to another level look again at once (Attack.dm, B)
	for(var/turf/X in list(T, U))
		X.underlays += icon(X.icon, X.icon_state)
		X.icon = 'Stairs.dmi'
		X.Detailed = 1
	T.icon_state = "StoneUp"
	U.icon_state = "StoneDown"
	U.Supported = 1

// --- Mining a tunnel's roof ---------------------------------------------------------------

Player/proc/RemasterMineRoof(turf/T, queued = 0)
	if(!T || T.density || T.remaster_roof <= 0)
		RemasterNotice("There is no block overhead to mine there.")
		return 0
	if(!RemasterMayWork(T)) return 0
	var/n = RemasterOrder(T, queued, "Mine roof")
	if(n) RemasterNotice("Mining the block above ([T.remaster_roof] overhead). Shift queues the next one.")
	return n

// One blow at the block over T (the order tick paces them). Returns 1 while that block holds,
// 0 once it is down (the order is then done: one block an order).
mob/Monsters/proc/RemasterRoofBlow(turf/T, by_hand)
	if(!T || T.density || T.remaster_roof <= 0) return 0
	if(T.remaster_roof_hp <= 0) T.remaster_roof_hp = RM_ROOF_LAYER_HP
	var/hp0 = T.remaster_roof_hp
	var/k = T.remaster_ceil || 2         // the block at the ceiling, for its stone (Yield.dm)
	T.remaster_roof_hp -= RemasterWorkSkill(MineingSkill) / 4 * (by_hand ? 0.25 : 1)
	MineingSkill += 0.05
	RemasterWorkBlow(T, src, hp0)
	if(T.remaster_roof_hp > 0)
		RmStoneHalf(T, k, src, T.remaster_roof_hp, RM_ROOF_LAYER_HP)
		return 1
	// a layer comes down: the ceiling rises
	T.remaster_roof_hp = 0
	T.remaster_roof--
	T.remaster_ceil = (T.remaster_ceil || 2) + 1
	RemasterColumnSettle(T)    // blocks above already mined out on their own: the ceiling goes on up to the next (Gather.dm)
	RmStoneOut(T, k, src)      // its stone, as every natural block's (Yield.dm); the last piece lies here as before
	if(T.remaster_roof <= 0)
		T.remaster_roof = 0
		T.remaster_ceil = 0
		var/turf/U = locate(T.x, T.y, SKY_LAYER)
		if(U && U.icon_state == "Peak")
			U.icon_state = "Sky"
			U.name = "Sky"
			U.Content = "Sky"
	if(prob(5)) RemasterCaveIn(src)
	return 0

// The original cave-in (the race dig code): open cave floor within three tiles of the miner
// may fill with rock again, half of it, unless a pillar stands within four tiles of it.
proc/RemasterCaveIn(mob/M)
	if(!M) return
	view(M) << "Cave In!"
	for(var/turf/grounds/cavefloor/CF in view(3, M))
		if(CF.density || CF == M.loc || CF.remaster_laid || (locate(/mob/Monsters) in CF)) continue   // never a tile with laid blocks (Plans.dm)
		if(locate(/obj/Items/Furniture/Pillars) in range(4, CF)) continue
		if(!prob(50)) continue
		CF.opacity = 1
		CF.density = 1
		CF.CanDigAt = 1
		CF.icon_state = "CaveWall"
		CF.HP = 200
		CF.Detailed = 0
		CF.remaster_roof = 0
		CF.remaster_ceil = 0
		CF.remaster_carve = 0
		CF.remaster_dug = 0
		CF.remaster_dug_top = 0
		CF.remaster_topcut = 0     // the rock comes back whole (Gather.dm)
		CF.remaster_holes = 0
		CF.rm_laid_gone = 0       // ...natural rock, its stone by the block (Yield.dm)
		CF.rm_mat_gone = null
		CF.rm_stone_half = 0

// Hover hint: digging here can bring tunnels down nearby (no pillar within four tiles).
proc/RemasterCaveInRisk(turf/T)
	if(!T) return 0
	for(var/turf/grounds/cavefloor/CF in range(3, T)) if(!CF.density && CF != T)
		if(!(locate(/obj/Items/Furniture/Pillars) in range(4, CF))) return 1
	return 0

// --- Climbing gear ---------------------------------------------------------------------------
// Pitons, hooks and a rope (made at a forge). A unit carrying it, a climbing race (Kobolds,
// Vampires, Spiders: CliffClimber) or a flyer goes up a cliff face onto the peak, or down
// one, where there are no stairs: it takes 2 s and about a second per layer of rock (half
// that for climbing races; flyers just fly up). Move orders onto or off a mountain use it
// by themselves (RemasterOrder).
obj/Items/RemasterTools/ClimbingGear
	// its values: art/items/catalogue.json row remastertools.climbinggear (export_items.py writes ItemData.dm)

proc/RemasterCanClimb(mob/Monsters/M)
	if(!M) return 0
	if(M.Flying || M.CliffClimber) return 1
	return !!(locate(/obj/Items/RemasterTools/ClimbingGear) in M)

proc/RemasterClimbTime(mob/Monsters/M, layers)
	if(M.Flying) return 10
	return round((20 + 10 * layers) * (M.CliffClimber ? 0.5 : 1))

// Where M climbs to reach A on the other level: list(foot (open ground), top (the peak), rock).
// Up: a mountain rock tile with a walkable peak over it and open ground beside it, nearest
// M plus nearest A. Down: the same, seen from the peak side.
proc/RemasterClimbSpot(mob/Monsters/M, turf/A)
	if(!M || !A) return null
	var/up = A.z == SKY_LAYER && M.z == GROUND_LAYER
	var/down = A.z == GROUND_LAYER && M.z == SKY_LAYER
	if(!up && !down) return null
	var/turf/near = locate(up ? A.x : M.x, up ? A.y : M.y, GROUND_LAYER)
	var/list/best
	var/score = 1000000
	for(var/turf/R in range(12, near))
		if(!R.density || !RemasterIsMountain(R)) continue
		var/turf/U = locate(R.x, R.y, SKY_LAYER)
		if(!U || U.density || U.icon_state != "Peak") continue
		for(var/d in list(NORTH, SOUTH, EAST, WEST))
			var/turf/F = get_step(R, d)
			if(!F || F.density || !RemasterWalkable(F, M, F)) continue
			var/s = up ? get_dist(M, F) + get_dist(U, A) : get_dist(M, U) + get_dist(F, A)
			if(s < score)
				score = s
				best = list(F, U, R)
	return best

// A climb order (kind "Scale"): target the rock; the unit goes to the foot (up) or the peak
// over the rock (down), climbs for a while, then stands at the other end.
proc/RemasterScaleOrder(Player/P, mob/Monsters/M, turf/A)
	var/list/spot = RemasterClimbSpot(M, A)
	if(!spot) return null
	var/datum/remaster_order/C = new
	C.issuer = P
	C.kind = "Scale"
	C.target = spot[3]
	C.climb_z = A.z
	C.scale_foot = spot[1]
	C.scale_top = spot[2]
	return C

datum/remaster_order/var
	turf/scale_foot
	turf/scale_top
	scale_start = 0

// One tick of a climb. Returns 1 while it goes on.
mob/Monsters/proc/RemasterScaleTick(datum/remaster_order/O)
	var/turf/R = O.target
	var/up = O.climb_z == SKY_LAYER
	var/turf/here = up ? O.scale_foot : O.scale_top
	var/turf/there = up ? O.scale_top : O.scale_foot
	if(!R || !here || !there || (up && !R.density))
		RemasterFinishOrder("Skipped: the cliff is gone")
		return 0
	if(z == O.climb_z)
		RemasterFinishOrder("Climbed [up ? "up" : "down"]")
		return 0
	if(!O.scale_start)
		if(loc != here)
			RemasterGiveUpOrApproach(O, here, 0)
			return 1
		O.scale_start = world.time
		destination = null
	var/layers = RemasterBlocksAt(R) || 3
	var/need = RemasterClimbTime(src, layers)
	dir = get_dir(src, locate(R.x, R.y, z)) || dir
	remaster_order_status = "Climbing [up ? "up" : "down"] ([round(100 * min(1, (world.time - O.scale_start) / need))]%)"
	if(world.time - O.scale_start < need) return 1
	loc = there
	destination = null
	RemasterFinishOrder("Climbed [up ? "up" : "down"]")
	return 0
