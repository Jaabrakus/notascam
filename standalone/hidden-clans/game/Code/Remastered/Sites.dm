// Construction sites (construction-3d, 10-30; the owner: "polish the construction to 3d", "has to work with the plan and
// building we have currently, or we have a thing in standalone call syx we could emulate"). A build plan (Plans.dm)
// works as a construction site does in Songs of Syx: its material is carried to the site first, in full loads, and the
// walls go up from there.
//  - The site's pile (Z["pile"], "x,y"): an open ground tile just outside the plan, on the side nearest the stockpile;
//    Z["stock"] is the stone or logs lying in it, Z["phase"] "build" once enough is there. Saved with the row (rm_jz).
//  - Delivering: while the stone at the site and in its workers' bags is short of the next RM_SITE_BATCH blocks (or of
//    all that are left) and the stores have some, a worker fetches a load from the stores (as before: one, then the
//    pieces beside it up to RM_BUILD_LOAD) and carries it to the pile.
//  - Building: then each worker takes a load from the pile and lays it, block by block (the "Lay block" order); the pile
//    empty with blocks left, delivering starts again. Stores empty: they build with what the site has.
//  - Up on a mountain (z SKY_LAYER), or no ground for a pile: the old way (stone straight from the stores).
//  - A finished or removed plan's leftover stock lies on the pile's tile as stone or logs again.
// The 3D view gets the sites (RmSites3D): the pile, stakes and string round the plan, scaffolding on the courses going
// up, and a block rising with each blow as it is laid (art/hud/src/045).
#define RM_SITE_BATCH 40      // blocks' worth delivered before building starts (a bigger plan: in rounds of this)
#define RM_SITE_NEAR 14       // a worker this far from the pile still takes its stone from it
#define RM_SITE_WAIT 150      // ticks the workers wait for stone carried by others before going on without it

datum/remaster_order/var/tmp/rm_site      // a "Site" order's plan row id
datum/remaster_order/var/tmp/rm_site_do   // "deliver" or "take"
datum/remaster_order/var/tmp/turf/rm_stand   // a Site order's own place in the ring round the pile (RmSiteStand)

// Its own place round the pile (from open-realm's harvest rings, 10-30): an open tile beside the pile, on the worker's
// own side first (a corner a little after), that no other worker's trip to this pile is making for. Null when all are
// taken: it goes to the pile as before (any tile beside it). Workers came in on one side and stood on one tile.
mob/Monsters/proc/RmSiteStand(Player/P, list/Z, turf/PL)
	var/list/taken = list()
	for(var/mob/Monsters/W in P.RmJzMembers(Z["id"])) if(W != src && W.remaster_active && W.remaster_active.kind == "Site" && W.remaster_active.rm_stand) taken[W.remaster_active.rm_stand] = 1
	var/turf/best
	var/bd = 1#INF
	for(var/turf/S in orange(1, PL))
		if(S.density || taken[S] || RemasterWalkable(S, src, S) != 1) continue
		var/d = get_dist(src, S) + ((S.x != PL.x && S.y != PL.y) ? 0.4 : 0)
		if(d < bd)
			bd = d
			best = S
	return best


// The plan row's pile: kept while its tile stays good, else a new one (its stock goes with it).
Player/proc/RmSitePile(list/Z)
	if(Z["kind"] != "build" || Z["z"] != GROUND_LAYER) return null
	if(Z["pile"])
		var/list/p = splittext(Z["pile"], ",")
		var/turf/T = locate(text2num(p[1]), text2num(p[2]), GROUND_LAYER)
		if(RmSitePileOK(T, Z)) return T
	var/turf/S = RemasterStockpile()
	var/cx = (Z["x0"] + Z["x1"]) / 2
	var/cy = (Z["y0"] + Z["y1"]) / 2
	var/turf/best
	var/bd = 1#INF
	for(var/r = 1, r <= 3 && !best, r++)
		var/x0 = Z["x0"] - r
		var/y0 = Z["y0"] - r
		var/x1 = Z["x1"] + r
		var/y1 = Z["y1"] + r
		for(var/x = x0, x <= x1, x++) for(var/y = y0, y <= y1, y++)
			if(x != x0 && x != x1 && y != y0 && y != y1) continue
			var/turf/T = locate(x, y, GROUND_LAYER)
			if(!RmSitePileOK(T, Z)) continue
			var/d = S ? get_dist(T, S) : abs(x - cx) + abs(y - cy)
			if(x == x0 || x == x1) if(y == y0 || y == y1) d += 0.5      // a corner last: it blocks least, but looks odd
			if(d < bd)
				bd = d
				best = T
	Z["pile"] = best ? "[best.x],[best.y]" : null
	return best

Player/proc/RmSitePileOK(turf/T, list/Z)
	if(!T || T.density || T.Tree || istype(T, /turf/grounds/waters) || Remaster3DKind(T) != "floor" || T.remaster_laid) return 0
	if(T.x >= Z["x0"] && T.x <= Z["x1"] && T.y >= Z["y0"] && T.y <= Z["y1"]) return 0     // never inside the plan
	if(rm_fh && rm_fh["dx"] && abs(T.x - rm_fh["dx"]) <= 1 && abs(T.y - rm_fh["dy"]) <= 1) return 0   // nor at the first house's door
	if(locate(/mob/WorkShops) in T) return 0
	for(var/d in list(NORTH, SOUTH, EAST, WEST))   // never in front of a doorway (a planned door, or a gap in the plan's walls)
		var/turf/N = get_step(T, d)
		if(!N) continue
		if(rm_plan_doors && rm_plan_doors["[N.x],[N.y]"]) return 0
		if(N.x >= Z["x0"] && N.x <= Z["x1"] && N.y >= Z["y0"] && N.y <= Z["y1"] && !N.density && !("[N.x],[N.y],0" in Z["cells"])) return 0
	return 1

// Stone (or logs) at the site and in the bags of the plan's workers.
Player/proc/RmSiteHeld(list/Z, mp)
	. = Z["stock"] || 0
	for(var/mob/Monsters/M in RmJzMembers(Z["id"])) if(M && M.rm_jz_id == Z["id"] && !M.remaster_site) . += M.RemasterCarriedCount(mp)   // its own workers only: not a builder's load for a floor

// One worker's step at a site (from Plans.dm RmPlanBuildStep, after it chose its block): 1 if it took an order (a
// trip for stone, to the pile, or to take from it), 0 to lay what it carries (or to go the old way).
mob/Monsters/proc/RmSiteStep(Player/P, list/Z, turf/PL, mp, word, left, again = 0)
	var/have = RemasterCarriedCount(mp)
	var/stock = Z["stock"] || 0
	if(Z["phase"] != "build")
		var/target = min(left, RM_SITE_BATCH)
		var/held = P.RmSiteHeld(Z, mp)
		if(have)      // what it carries goes onto the pile (a full load: the pieces beside it at the stores first)
			if(have < RM_BUILD_LOAD && held < target)
				var/obj/Items/X = RmSiteMoreAtHand(P, mp)
				if(X)
					RmPlanFetch(P, X)
					remaster_work_status = "[Z["name"]]: fetching [word] for the site"
					return 1
			RmSiteOrder(P, Z, PL, "deliver")
			remaster_work_status = "[Z["name"]]: carrying [word] to the site"
			return 1
		if(held < target)     // short of the next round's stone: fetch more while the stores have it
			var/obj/Items/S = P.RemasterSiteSource(list("z" = GROUND_LAYER), mp, src)
			if(S && weight + S.weight <= weightmax)
				Z["need"] = null
				RmPlanFetch(P, S)
				remaster_work_status = "[Z["name"]]: fetching [word] for the site"
				return 1
			if(!stock) return 0     // nothing anywhere: the old way says it waits for stone
		else if(!stock) return 0   // all of it in bags (on its way, or being laid): this one goes the old way, straight from the stores; never waits on others (a timber house hung on its last log, 10-30)
		Z["wait_at"] = null
		Z["phase"] = "build"     // enough at the site (or all there is): build
	if(have) return 0          // lay what it carries
	if(stock > 0 && get_dist(src, PL) <= RM_SITE_NEAR)
		RmSiteOrder(P, Z, PL, "take")
		remaster_work_status = "[Z["name"]]: taking [word] from the site"
		return 1
	if(stock > 0) return 0     // far off: the old way, from the stores
	Z["phase"] = null          // the pile is empty: deliver again
	return again ? 0 : RmSiteStep(P, Z, PL, mp, word, left, 1)

// More of it beside the worker (at the stores, as the old way tops up its load).
mob/Monsters/proc/RmSiteMoreAtHand(Player/P, mp)
	for(var/obj/Items/X in range(1, src))
		if(istype(X, mp) && isturf(X.loc) && P.RemasterMayCollect(X) && !X.remaster_placed && weight + X.weight <= weightmax) return X
	return null

mob/Monsters/proc/RmSiteOrder(Player/P, list/Z, turf/PL, what)
	var/datum/remaster_order/O = new
	O.issuer = P
	O.target = PL
	O.kind = "Site"
	O.rm_site = Z["id"]
	O.rm_site_do = what
	O.rm_stand = RmSiteStand(P, Z, PL)   // its own place round the pile
	O.automatic = 1
	O.rm_plan = 1
	remaster_auto_unload = 0       // the stone is for building: never a trip to put it back
	rm_plan_last = null            // a pile trip is no block: how it ends never sets a block aside (Plans.dm rm_plan_skip)
	RemasterSuspendControllers()
	remaster_active = O
	RemasterStartOrder(O)
	RemasterOrderTick()

// At the pile (Orders.dm RemasterOrderTick): what it carries goes onto it, or a load comes off it.
mob/Monsters/proc/RmSiteTick(datum/remaster_order/O)
	var/turf/T = O.target
	var/Player/P = Owner
	var/list/Z = istype(P) ? P.RmJz(O.rm_site) : null
	if(!Z || Z["kind"] != "build")
		RemasterFinishOrder("Skipped: that plan is gone")
		return
	if(get_dist(src, T) > 1)
		if(O.rm_stand && !O.rm_stand.density) RemasterGiveUpOrApproach(O, O.rm_stand, 0)   // to its own place in the ring
		else RemasterGiveUpOrApproach(O, T, 1)
		return
	var/mp = RmPlanMatPath(Z)
	var/word = RmPlanMatWord(Z)
	dir = get_dir(src, T) || dir
	var/n = 0
	if(O.rm_site_do == "deliver")
		for(var/obj/Items/X in src) if(istype(X, mp) && X.suffix != "(Equipped)")
			weight -= X.weight
			del X
			n++
		Z["stock"] = (Z["stock"] || 0) + n
		RemasterFinishOrder(n ? "Put [n] [word] on the site's pile" : "No [word] carried to put on the pile")
		return
	var/want = min(Z["stock"] || 0, RM_BUILD_LOAD)
	for(var/i = 1, i <= want, i++)
		var/obj/Items/X = new mp(src)
		if(weight + X.weight > weightmax && n)
			del X
			break
		weight += X.weight
		n++
	Z["stock"] = max(0, (Z["stock"] || 0) - n)
	RemasterFinishOrder(n ? "Took [n] [word] from the site's pile" : "The site's pile was empty")

// Someone of the plan's realm standing where block k of T goes (on the ground for block 0, up on the column at that
// height for a higher one) and free to move (no order of the player's, not fighting): sent to an open tile beside it,
// so the block can go in. Idle villagers and waiting workers stood on wall tiles for good (construction-3d, 10-30).
proc/RmPlanClearSpot(turf/T, k, mob/Monsters/M)
	var/list/who = list()
	if(k == 0) for(var/mob/Monsters/X in T) if(X != M) who += X
	var/turf/U = locate(T.x, T.y, SKY_LAYER)
	if(U && k > 0) for(var/mob/Monsters/X in U) if(X != M && RemasterFeetOf(X) == k) who += X
	for(var/mob/Monsters/X in who)
		if(X.Owner != M.Owner || X.remaster_attack || X.remaster_defense || length(X.remaster_orders)) continue
		if(X.remaster_active && (!X.remaster_active.automatic || istype(X.remaster_active, /datum/remaster_order/rm_step_off))) continue
		var/turf/S = (k > 0 && X.z == SKY_LAYER) ? RmPlanAsideUp(U, k, X, istype(M.Owner, /Player) ? M.Owner : null) : null   // up on a wall's top: a place beside it up there (the ground was out of reach: the real game 10-30)
		if(!S) S = RemasterBuildSpot(T, X)
		if(!S) continue
		if(RmAsideStep(X, S)) continue
		if(X.remaster_active) X.RemasterCancelOrders()
		var/datum/remaster_order/rm_step_off/O = new
		O.issuer = X.Owner
		O.target = S
		O.said = X.remaster_order_status
		X.remaster_active = O
		X.RemasterStartOrder(O)

// X steps onto S beside it on its own level, now (1), or 0: then it is sent there.
proc/RmAsideStep(mob/Monsters/X, turf/S)
	if(!X || !S || S.z != X.z || get_dist(X, S) != 1) return 0
	var/was = usr
	usr = X
	. = X.Move(S, get_dir(X, S))
	usr = was

// A place beside U up there for X standing at height f to step aside to: as high (never a hop down: two builders
// stepped down onto a one-storey house's wall tops had no way off, arena offset_room.dm 10-30), open, not a plan's
// block's place, not a building's first step; null when there is none.
proc/RmPlanAsideUp(turf/U, f, mob/Monsters/X, Player/P)
	for(var/turf/N in orange(1, U))
		if(N.z != SKY_LAYER || !RemasterSpotAt(N, f) || RmFirstStep(N) || (P && P.RmPlanWantsAt(N.x, N.y, f)) || RemasterWalkable(N, X, N) != 1) continue
		return N
	return null

// Idle own units on the place M works a block from, up there at height f, step aside to a place beside it as high
// (not a plan's block's place, not a building's first step), so M can stand there: the last block of a two-storey house
// waited for good behind a builder resting on the one place it could be laid from (arena tests/storeys.dm).
proc/RmPlanClearPlace(turf/U, f, mob/Monsters/M)
	if(!U || U.z != SKY_LAYER) return
	var/Player/P = istype(M.Owner, /Player) ? M.Owner : null
	for(var/mob/Monsters/X in U)
		if(X == M || X.Owner != M.Owner || RemasterFeetOf(X) != f || X.remaster_attack || X.remaster_defense || length(X.remaster_orders)) continue
		if(X.remaster_active && !X.remaster_blocked && (!X.remaster_active.automatic || istype(X.remaster_active, /datum/remaster_order/rm_step_off))) continue   // a stuck one moves too
		var/turf/S = RmPlanAsideUp(U, f, X, P) || RemasterBuildSpot(locate(U.x, U.y, GROUND_LAYER), X)   // none up there: down beside it (a villager with nothing to do stood on a building's second step and held its builders: played in the browser, 10-30)
		if(!S) continue
		if(RmAsideStep(X, S)) continue   // beside it up there: one step at once, its orders kept (an order to go there didn't move one stuck up a house: the real game 10-30)
		if(X.remaster_active && !X.remaster_active.automatic) continue   // a player's own order is never cancelled for it
		if(X.remaster_active) X.RemasterCancelOrders()
		var/datum/remaster_order/rm_step_off/O = new
		O.issuer = X.Owner
		O.target = S
		O.said = X.remaster_order_status
		X.remaster_active = O
		X.RemasterStartOrder(O)

// A block of plan Z that waits so one beside it goes on first, worked from its place. A wall's next course over a floor
// its stairs lead up to (level k + 1, k in Z["floors"]) may have no place to be worked from on that floor, the ground or
// steps but places where a block of the plan is still to go at k. Those places' blocks wait, and those of the plan's
// wall tops on the way to each from the floor (a room's corner by its stairs went on last, from the lower house's wall
// top, and its builder had no way off: arena offset_room.dm and offset_corner.dm, the real game 10-30). Meanwhile the
// places may be stood on to work (Gather.dm RemasterWorkSpot, Plans.dm RmPlanAccess). Never a step. Worked out once a
// tick for the plan; a block waits RM_PLAN_HOLD at most.
#define RM_PLAN_HOLD 3000
#define RM_PLAN_HOLD_WAY 8   // wall tops on the way from the floor to such a place, at most
Player/proc/RmPlanHoldFor(turf/T, k, list/Z)
	if(!T || k < 1 || !islist(Z) || !islist(Z["cells"]) || !islist(Z["floors"]) || !(k in Z["floors"])) return 0
	if(Z["hold_t"] != world.time) RmPlanHolds(Z)
	var/list/H = Z["hold"]
	var/c = "[T.x],[T.y],[k]"
	if(!H[c] || (rm_plan_steps && rm_plan_steps[c])) return 0
	var/list/A = Z["held_at"]
	if(!A[c]) A[c] = world.time
	return world.time - A[c] <= RM_PLAN_HOLD   // waited long enough: it goes on

// The blocks of plan Z that wait this tick (RmPlanHoldFor): Z["hold"].
Player/proc/RmPlanHolds(list/Z)
	Z["hold_t"] = world.time
	var/list/H = list()
	Z["hold"] = H
	var/list/W = list()
	for(var/cc in Z["cells"]) W[cc] = 1
	for(var/cc in W)
		var/list/q = RmPlanCell(cc)
		var/turf/N = q[1]
		var/k = q[2] - 1
		if(!N || !(k in Z["floors"])) continue
		if(!RmPlanCanLay(N, k + 1, src) && !(W["[N.x],[N.y],[k]"] && RmPlanCanLay(N, k, src))) continue
		if(RmPlanSpotBut(N, k + 1, null, k, W)) continue
		for(var/turf/S in orange(1, N))
			if(!W["[S.x],[S.y],[k]"] || !RemasterSpotAt(locate(S.x, S.y, SKY_LAYER), k)) continue
			var/list/way = RmPlanHoldWay(S, k, W, N)
			if(way) for(var/turf/X in way) H["[X.x],[X.y],[k]"] = 1
	var/list/A = Z["held_at"]
	if(!A)
		A = list()
		Z["held_at"] = A
	for(var/cc in A.Copy()) if(!H[cc]) A -= cc

// The way from S (a top at height k with a block of plan W still to go on it) over such tops to the floor at that height
// (a top no block of the plan is to go on), not through N: those tops, S first; null when there is none within
// RM_PLAN_HOLD_WAY.
proc/RmPlanHoldWay(turf/S, k, list/W, turf/N)
	var/list/prev = list()
	prev[S] = S
	var/list/front = list(S)
	for(var/d = 0, d <= RM_PLAN_HOLD_WAY && length(front), d++)
		var/list/next = list()
		for(var/turf/C in front) for(var/dd in list(NORTH, SOUTH, EAST, WEST))
			var/turf/G = get_step(C, dd)
			if(!G || G == N || prev[G] || !RemasterSpotAt(locate(G.x, G.y, SKY_LAYER), k)) continue
			prev[G] = C
			if(!W["[G.x],[G.y],[k]"])   // the floor
				var/list/way = list()
				for(var/turf/X = C, X != S, X = prev[X]) way.Insert(1, X)
				way.Insert(1, S)
				return way
			next += G
		front = next
	return null

// Whether block j of N can be worked from a place beside it other than T: a unit's feet at f in reach of j, on the
// ground, on steps, or at height k (the floor: a top there or to be), with no block of the plan (W) to go there.
proc/RmPlanSpotBut(turf/N, j, turf/T, k, list/W)
	for(var/turf/G in orange(1, N))
		if(G == T) continue
		var/turf/GU = locate(G.x, G.y, SKY_LAYER)
		var/slope = RemasterSlopeOn(G)
		for(var/f = max(0, j - RM_REACH_UP), f <= j + RM_REACH_DOWN, f++)
			if(f && f != k && !slope) continue
			if(W["[G.x],[G.y],[f]"]) continue
			if(!f ? RmAcStand(G, 0) : (RemasterSpotAt(GU, f) || (f == k && W["[G.x],[G.y],[f - 1]"] && !RemasterBlockThere(G, f)))) return 1
	return 0

// --- Upper floors (the layered builder, phase 3, 10-30; the owner: "begin phase 3 ... does it also include the beams")
// A block may go over open air when it is held: a chain of blocks at its height, at most RM_SPAN tiles long (four ways),
// reaches one standing on a column from the ground (a wall, a pillar). Laid blocks hold; with want (a plan being
// queued), its planned ones too, so a house's ceilings are planned with its walls and laid once the walls are up.
#define RM_SPAN 3
proc/RmPlanHeld(turf/T, k, list/want)
	if(!T || k <= 0) return 0
	var/list/seen = list()
	seen[T] = 1
	var/list/front = list(T)
	for(var/d = 1, d <= RM_SPAN && length(front), d++)
		var/list/next = list()
		for(var/turf/C in front) for(var/dd in list(NORTH, SOUTH, EAST, WEST))
			var/turf/N = get_step(C, dd)
			if(!N || seen[N]) continue
			seen[N] = 1
			if(!(RemasterBlockThere(N, k) || (want && want["[N.x],[N.y],[k]"]))) continue
			if(RmPlanStands(N, k, want)) return 1
			next += N
		front = next
	return 0

// Block k of N stands on its column: every block under it there (or planned).
proc/RmPlanStands(turf/N, k, list/want)
	for(var/j = k - 1, j >= 0, j--) if(!(RemasterBlockThere(N, j) || (want && want["[N.x],[N.y],[j]"]))) return 0
	return 1

// The sky over a room's new ceiling: a top to stand on (as a column closed from the ground makes one, Plans.dm).
proc/RmPlanPeak(turf/T)
	var/turf/U = locate(T.x, T.y, SKY_LAYER)
	if(!U || U.icon_state == "Peak") return
	U.icon = 'Cave.dmi'
	U.icon_state = "Peak"
	U.name = "MountainPeak"
	if(U.Content == "Sky") U.Content = 0
	remaster_dirty_turfs["[U.x],[U.y],[U.z]"] = 1

// A plan done or removed: what is left on its pile lies there as stone or logs again.
Player/proc/RmSiteSpill(list/Z)
	var/n = min(Z["stock"] || 0, RM_PLAN_MAX)
	Z["stock"] = 0
	if(n <= 0 || !Z["pile"]) return
	var/list/p = splittext(Z["pile"], ",")
	var/turf/T = locate(text2num(p[1]), text2num(p[2]), GROUND_LAYER)
	if(!T) return
	if(T.density)
		for(var/turf/N in orange(1, T)) if(!N.density)
			T = N
			break
	var/mp = RmPlanMatPath(Z)
	for(var/i = 1, i <= n, i++) new mp(T)

// The sites round the camera for the 3D view: list(pile x, pile y, 1 for wood, stock, blocks left, total, x0, y0, x1, y1,
// its name, 1 when it waits for stone or logs).
// Short of stone or logs, none in the stores: a board order for it, as the first house posts (FirstHouse.dm).
Player/proc/RmSitePostNeed(list/Z)
	var/kind = RmPlanWood(Z) ? "wood" : "stone"
	var/need = length(Z["cells"]) - (Z["stock"] || 0) - RemasterStockCount(kind)
	if(need <= 0) return
	if(remaster_board_orders) for(var/list/O in remaster_board_orders) if(!O["done"] && O["standing"] == "build-[kind]") return
	var/list/O = RemasterBoardPost(kind, min(20, need), 1, 2, null, null, "build-[kind]")
	if(O) O["label"] = "[kind == "wood" ? "Chop wood" : "Mine stone"] for [Z["name"]]: [O["amount"]]"

Player/proc/RmSites3D(cx, cy, r)
	var/list/out = list()
	if(rm_jz) for(var/list/Z in rm_jz) if(Z["kind"] == "build" && Z["z"] == GROUND_LAYER && length(Z["cells"]))
		if(Z["x1"] < cx - r || Z["x0"] > cx + r || Z["y1"] < cy - r || Z["y0"] > cy + r) continue
		var/px = 0
		var/py = 0
		if(Z["pile"])
			var/list/p = splittext(Z["pile"], ",")
			px = text2num(p[1])
			py = text2num(p[2])
		out += list(list(px, py, RmPlanWood(Z) ? 1 : 0, Z["stock"] || 0, length(Z["cells"]), Z["total"], Z["x0"], Z["y0"], Z["x1"], Z["y1"], "[Z["name"]]", Z["need"] ? 1 : 0, "p", Z["id"]))   // + its name, 1 when it waits for stone or logs, "p" and its row (the label's click)
		if(length(out) >= 40) break
	for(var/list/S in RemasterOpenSites())   // the placed sites too (Blueprints.dm): one record for both, its bounds from its blueprints
		if(length(out) >= 40) break
		var/sx0 = 1#INF
		var/sy0 = 1#INF
		var/sx1 = -1#INF
		var/sy1 = -1#INF
		if(remaster_blueprints) for(var/list/B in remaster_blueprints) if(B["site"] == S["id"] && B["z"] == GROUND_LAYER)
			sx0 = min(sx0, B["x"])
			sy0 = min(sy0, B["y"])
			sx1 = max(sx1, B["x"])
			sy1 = max(sy1, B["y"])
		if(sx0 == 1#INF || sx1 < cx - r || sx0 > cx + r || sy1 < cy - r || sy0 > cy + r) continue
		out += list(list(0, 0, 0, 0, S["left"] || 0, S["total"] || 0, sx0, sy0, sx1, sy1, "[S["label"]]", 0, "s", S["id"]))
	return out

// A block being laid, for the 3D view (View3D.dm "lay"): list(x, y, block, blows so far, blows it takes, 1 for wood),
// while the worker is beside it at work; else null.
proc/RmLay3D(mob/Monsters/M)
	var/datum/remaster_order/O = M.remaster_active
	if(!O || O.kind != "Lay block" || !isturf(O.target) || isnull(O.block)) return null
	var/turf/A = O.target
	if(max(abs(M.x - A.x), abs(M.y - A.y)) > 1 || M.remaster_order_status != "Laying a block") return null
	return list(A.x, A.y, O.block, O.lay, RM_BUILD_WORK, O.rm_mat == "wood" ? 1 : 0)
