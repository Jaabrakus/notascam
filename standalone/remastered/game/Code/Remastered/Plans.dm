// Plan mode (ramps-gather, 2026-10-25; tried out first in tools/plan_mode/arena.html): the player marks blocks of the
// mountain grid level by level (Gather.dm: block k of the column at x,y) and queues them as a plan. A plan is a row on
// the job board, kind "dig", that villagers on the Any role take up by themselves by priority, like a zone (Jobs.dm).
// The user: "we don't have to control individual workers, we make a plan and then they set it in motion".
//  - A plan's blocks are "x,y,k" texts in Z["cells"], pruned as they come out; Z["total"] is how many it began with.
//  - A worker's step (RmPlanStep, from Jobs.dm RmJobStep) takes the block that suits it: one it can reach (the ground:
//    the three lowest of a face beside open ground; up on the mountain: Gather.dm's work spots), the higher first so a
//    face comes down from the top, never one someone stands on, nor one another worker is on. It makes the Mine order
//    a click on that block makes (Gather.dm RemasterBlockTick); a block it couldn't get to waits a while for it.
//  - The selected units, when the plan is queued, join it at once; the allocator does the rest.
//  - A build plan (kind "build", below) lays blocks the same way, one stone each, from the bottom up.

#define RM_PLAN_MAX 600          // blocks in one plan
#define RM_PLAN_SKIP 300         // a block a worker couldn't get to waits this long before that worker tries it again

Player/var/tmp/list/rm_plan_res          // plan id -> list("x,y,k" -> the worker on it)
var/rm_plan_debug = 0                    // 1: each plan order is logged (RMPLAN| lines; tests only)
mob/Monsters/var/tmp/rm_plan_last        // the block its last plan order was for
mob/Monsters/var/tmp/list/rm_plan_skip   // "x,y,k" -> world.time it may try that block again

proc/RmPlanCell(c)
	var/list/p = splittext("[c]", ",")
	if(length(p) != 3) return null
	var/turf/T = locate(text2num(p[1]), text2num(p[2]), GROUND_LAYER)
	return T ? list(T, text2num(p[3])) : null

proc/RmPlanKind(kind)
	return kind == "dig" || kind == "build"

// "x,y,k/x,y,k/..." from the page, once each, at most RM_PLAN_MAX: to dig, the blocks still there; to build, the
// blocks that can go on (now, or once the plan's blocks under them are in: RmPlanBuildable).
Player/proc/RmPlanAdd(cells_text, prio = 2, mode = "dig", mat = "stone")
	var/build = mode == "build"
	var/wood = build && mat == "wood"     // a build plan in wood: one log a block (building rework L1, below)
	var/list/want = list()
	// cells "x,y,k" split by "/" (a ";" breaks the page's link into fields; tests may still pass ";")
	for(var/c in splittext(replacetext("[cells_text]", ";", "/"), "/"))
		if(length(want) >= RM_PLAN_MAX) break
		if(RmPlanCell(c)) want[c] = 1
	var/list/ok = list()
	var/list/all = want
	if(build && rm_jz)   // the other build plans' blocks hold it up too (a room on a house still going up, a wooden floor in a stone house: phase 3)
		all = want.Copy()
		for(var/list/X in rm_jz) if(X["kind"] == "build" && islist(X["cells"])) for(var/c in X["cells"]) all[c] = 1
	for(var/c in want)
		var/list/q = RmPlanCell(c)
		if(build ? !RmPlanBuildable(q[1], q[2], all) : !RemasterBlockThere(q[1], q[2])) continue
		ok += c
	if(!length(ok))
		RemasterNotice(build ? "Nothing in that plan can be built: a block needs open ground or a block under it." : "Nothing in that plan to dig.")
		return null
	RmJzFixedRows()
	rm_jz_serial++
	var/n = 0
	for(var/list/X in rm_jz) if(X["kind"] == (build ? "build" : "dig")) n++
	var/x0 = 1#INF
	var/y0 = 1#INF
	var/x1 = -1#INF
	var/y1 = -1#INF
	for(var/c in ok)
		var/list/p = splittext(c, ",")
		var/x = text2num(p[1])
		var/y = text2num(p[2])
		x0 = min(x0, x); y0 = min(y0, y); x1 = max(x1, x); y1 = max(y1, y)
	var/list/Z = list("id"="j[rm_jz_serial]", "kind"=(build ? "build" : "dig"), "name"="[build ? "Build" : "Dig"] [n + 1]", "x0"=x0, "y0"=y0, "x1"=x1, "y1"=y1, "z"=GROUND_LAYER,
		"want"=min(4, length(ok)), "prio"=clamp(round(text2num("[prio]") || 2), 1, 3), "stop"=0, "paused"=0, "cells"=ok, "total"=length(ok))
	if(build) Z["mat"] = wood ? "wood" : "stone"     // saved with the row (Jobs.dm rm_jz); a row with none lays stone
	rm_jz += list(Z)
	var/joined = 0
	// the selected start on it: on Manual, they go on the job board (as its "put on the job board" does) and take it up
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && RmJzValid(M) && (M in UnitList) && !M.Wagon && !M.Critter && !M.Egg)
		if(M.remaster_job == "manual" && !length(M.remaster_production)) M.RemasterAssignJob("any")
		if(M.remaster_job != "any") continue
		RmJobJoin(M, Z)
		joined++
	if(joined > Z["want"]) Z["want"] = joined
	RemasterNotice("[Z["name"]]: [length(ok)] block[length(ok) > 1 ? "s" : ""] to [build ? (wood ? "build in wood" : "build in stone") : "dig"], on the job board[joined ? "; [joined] of yours started on it" : ""].")
	return Z

// The blocks a plan has left (the dug ones dropped from its list, or the laid ones, and those whose ground can no longer
// take a block); a finished plan goes from the board after 30 s.
Player/proc/RmPlanLeft(list/Z)
	var/list/C = Z["cells"]
	if(!islist(C)) return 0
	var/build = Z["kind"] == "build"
	for(var/i = length(C), i >= 1, i--)
		var/list/q = RmPlanCell(C[i])
		if(!q || (build ? (RemasterBlockThere(q[1], q[2]) || !RmPlanGroundOK(q[1], src, q[2])) : !RemasterBlockThere(q[1], q[2]))) C.Cut(i, i + 1)
	if(!length(C))
		if(!Z["done_at"]) Z["done_at"] = world.time
		else if(world.time - Z["done_at"] > 300 && !Z["going"])
			Z["going"] = 1
			spawn(1) if(src && (Z in rm_jz)) RmJzRemove(Z)
	return length(C)

// Whether someone stands on block k of T's column (on its top, or on that block inside the mountain).
proc/RmPlanStoodOn(turf/T, k)
	var/turf/U = locate(T.x, T.y, SKY_LAYER)
	if(U) for(var/mob/Monsters/M in U) if(RemasterFeetOf(M) == k + 1) return 1
	return 0

// One step of a worker on a dig plan (it has no order: Settlement.dm only calls the job step then).
mob/Monsters/proc/RmPlanStep(Player/P, list/Z)
	if(Z["kind"] == "build") return RmPlanBuildStep(P, Z)
	var/list/C = Z["cells"]
	if(!islist(C) || !length(C) || !P.RmPlanLeft(Z))
		RemasterStopWork()
		remaster_work_status = "[Z["name"]]: finished"
		return
	if(RmPlanAccessStep(P, Z)) return       // the plan's way up first, for the worker cutting it
	// the last order's block, if it is still there and the order gave up: left for a while
	if(rm_plan_last && (rm_plan_last in C) && remaster_order_status && (findtext(remaster_order_status, "Out of reach") || findtext(remaster_order_status, "No way") || findtext(remaster_order_status, "Couldn't") || findtext(remaster_order_status, "Skipped")))
		if(!rm_plan_skip) rm_plan_skip = list()
		rm_plan_skip[rm_plan_last] = world.time + RM_PLAN_SKIP
	rm_plan_last = null
	if(world.time < rm_plan_wait) return
	if(!P.rm_plan_res) P.rm_plan_res = list()
	var/list/R = P.rm_plan_res[Z["id"]]
	if(!R)
		R = list()
		P.rm_plan_res[Z["id"]] = R
	var/up = z == SKY_LAYER
	var/feet = up ? RemasterFeetOf(src) : 0
	var/best
	var/bk
	var/turf/bt
	var/bs = 1#INF
	var/list/held
	for(var/c in C)
		if(rm_plan_skip && rm_plan_skip[c] && rm_plan_skip[c] > world.time) continue
		var/mob/Monsters/H = R[c]
		if(H && H != src && H.rm_jz_id == Z["id"] && H.remaster_active && H.remaster_active.automatic && H.rm_plan_last == c) continue   // someone's on it
		var/list/q = RmPlanCell(c)
		var/turf/T = q[1]
		var/k = q[2]
		if(RmPlanStoodOn(T, k)) continue
		if(T.remaster_laid && RmBuiltHeld(P, T))   // another realm's built wall: off the plan (BuiltWalls.dm)
			if(!held) held = list()
			held += c
			continue
		if(up)
			if(abs(T.x - x) > 12 || abs(T.y - y) > 12 || !RemasterReaches(feet, k)) continue    // other heights: the way there (RmPlanWayThere)
		else
			if(T.z != z || !RemasterReaches(0, k)) continue      // from the ground: its three lowest blocks
			var/face = 0
			for(var/d in list(NORTH, SOUTH, EAST, WEST))
				var/turf/N = get_step(T, d)
				if(N && !N.density) face = 1
			if(!face) continue
		var/s = get_dist(src, T) - k * 0.6 + (up ? abs(k - feet) * 0.3 : 0)    // the higher first: a face comes down from the top
		if(s < bs)
			bs = s
			best = c
			bk = k
			bt = T
	if(held)
		C -= held
		P.RemasterNotice("[Z["name"]]: [length(held)] block\s of another realm's wall left out. [RM_BUILT_HELD_SAY]")
	var/aim_up = up
	if(!best)
		switch(RmPlanWayThere(P, Z))
			if(1) return
			if(2)
				best = rm_ac_cell      // up there with no work on the way: it walks up to it
				var/list/q = RmPlanCell(best)
				bt = q[1]
				bk = q[2]
				aim_up = 1
	if(!best)
		// nothing of it in reach: off the plan for a minute, so the allocator gives the place to someone who can get there
		RemasterStopWork()
		remaster_work_status = "[Z["name"]]: nothing in reach from here"
		Z["stuck_at"] = world.time
		if(!remaster_board_skip) remaster_board_skip = list()
		remaster_board_skip[Z["id"]] = world.time + 600
		P.RmJobLeave(src)
		return
	R[best] = src
	rm_plan_last = best
	var/datum/remaster_order/O = new
	O.issuer = P
	O.target = aim_up ? locate(bt.x, bt.y, SKY_LAYER) : bt
	if(rm_plan_debug) world.log << "RMPLAN|dig|[name]|[best]|at [x],[y],[z] feet=[feet] aim_up=[aim_up] remaster_feet=[remaster_feet]"
	O.kind = (!aim_up && !bt.density) ? "Mine roof" : "Mine"     // the floor block out: the blocks over it are a tunnel's roof
	O.block = bk
	O.automatic = 1
	O.rm_plan = 1
	if(aim_up && best == rm_ac_cell)
		O.rm_spot = rm_ac_spot      // where its way there leads
		O.rm_spot_f = rm_ac_spot_f
	remaster_auto_unload = 1
	RemasterSuspendControllers()
	remaster_active = O
	RemasterStartOrder(O)
	remaster_work_status = "[Z["name"]]: digging a block"
	RemasterOrderTick()

// For the page's Plan mode: every dig and build plan (the board sends its rows only on the Work tab).
Player/proc/RmPlansData()
	var/list/out = list()
	if(rm_jz) for(var/list/Z in rm_jz) if(RmPlanKind(Z["kind"]))
		var/left = RmPlanLeft(Z)
		var/list/members = RmJzMembers(Z["id"])
		var/status
		if(!left) status = "Done"
		else if(Z["paused"]) status = "Paused"
		else if(!length(members) && Z["stuck_at"] && world.time - Z["stuck_at"] < 700) status = "Nothing in reach yet: no way there"
		else if(!length(members)) status = rm_jz_nfree > 0 ? "Waiting for free villagers" : "Waiting: nobody free on the job board (select villagers when you queue a plan)"
		else
			var/mob/Monsters/M = members[1]
			var/mob/Monsters/AB = Z["access_by"]
			if(length(Z["access"]) && AB && (AB in members)) M = AB      // the worker cutting the way up says what is going on
			status = M ? "[M.remaster_work_status]" : ""
			if(Z["stuck_at"] && world.time - Z["stuck_at"] < 40 && findtext(status, "nothing in reach")) status = "Nothing in reach yet: no way there"
		var/list/lv = list()
		for(var/c in Z["cells"])
			var/list/p = splittext(c, ",")
			if(!(p[3] in lv)) lv += p[3]
		out += list(list("id"=Z["id"], "kind"=Z["kind"], "name"=Z["name"], "total"=Z["total"], "left"=left, "prio"=Z["prio"], "paused"=Z["paused"], "count"=length(members), "status"=status, "levels"=jointext(lv, ", "), "mat"=(Z["kind"] == "build" ? (RmPlanWood(Z) ? "wood" : "stone") : null), "stock"=(Z["stock"] || 0), "want"=RmJzWantNow(Z)))   // stock: on its pile (Sites.dm); want: the workers it wants now (Jobs.dm)
	return out

Player/proc/RmPlanAny()
	if(rm_jz) for(var/list/Z in rm_jz) if(RmPlanKind(Z["kind"]) && length(Z["cells"])) return 1
	return 0

// The queued blocks round the camera for the 3D view: list(x, y, k, the plan's place in the list, 1 for a block to build,
// 1 for a wood block).
Player/proc/RmPlanCells3D(cx, cy, r)
	var/list/out = list()
	var/i = 0
	if(rm_jz) for(var/list/Z in rm_jz) if(RmPlanKind(Z["kind"]))
		i++
		var/b = Z["kind"] == "build" ? 1 : 0
		var/w = RmPlanWood(Z) ? 1 : 0
		for(var/c in Z["cells"])
			var/list/p = splittext(c, ",")
			var/x = text2num(p[1])
			var/y = text2num(p[2])
			if(abs(x - cx) > r || abs(y - cy) > r) continue
			out += list(list(x, y, text2num(p[3]), i, b, w))
			if(length(out) >= 1500) return out
	return out

// --- Building block by block (stage 3, 2026-10-25) -----------------------------------------------------------------
// A build plan's cells are blocks to lay, one stone each, from the bottom up. A block goes on open ground (the tile
// becomes a column of rock one block high, the sky over it a mountain top to stand on), on a column's top (up to
// RM_BUILD_TOP), into a hole in a face, or under a tunnel's ceiling; never in the air, on water, trees, stairs, ramps,
// a built wall, someone else's ground or where something is set down, nor where someone stands. A worker fetches
// stone (from the stores, else pieces lying within 12 tiles), walks beside the block and lays it (the "Lay block"
// order, RmPlanLayTick); the stone is used up. The ground's look goes with the tile (remaster_built_floor) and comes
// back when the block is dug out again; built rock holds no vein.

#define RM_BUILD_TOP 8           // the highest a column is built, as high as the highest natural ones
#define RM_BUILD_LOAD 4          // stone a worker fetches in one trip
#define RM_BUILD_WORK 3          // blows to lay a block

turf/var/remaster_built = 0          // a column's height before any dug off its top, kept once it changes or is built up (saved; Breaking.dm RmKeepHeight, RemasterBlocksAt)
turf/var/remaster_built_floor        // a block laid on open ground: what the ground was, "icon|icon_state|name|Detailed|Content3" (saved)
turf/var/tmp/rm_built_icon           // that ground's icon itself, while the world runs
datum/remaster_order/var/tmp/lay = 0 // "Lay block": blows into the block so far
datum/remaster_order/var/tmp/rm_plan = 0   // a plan's order: gives up when there is no way to it (Orders.dm RemasterApproach)
datum/remaster_order/var/tmp/turf/rm_spot  // ...and the place up there its way leads to, with its height (Gather.dm RemasterWorkSpot)
datum/remaster_order/var/tmp/rm_spot_f
mob/Monsters/var/tmp/rm_plan_wait = 0    // waiting for stone: when it looks again

// --- Material and builder on the plan, saved per block (building rework L1, 2026-10-27;
// planning/BUILDING_REWORK_PLAN_2026-10-27.md step 1a) ---------------------------------------------------------------
// A build plan lays stone or wood (its row's "mat"; a row with none lays stone), one stone or one log a block. Each laid
// block's material is a letter on its tile, one for each block index from the floor: s stone, w wood, . not laid ("..ss":
// two laid stone blocks on two natural ones); a laid bit (Yield.dm remaster_laid) with no letter is stone. The tile also
// keeps the realm (root key, Realms.dm) of the player who laid its laid blocks: written when a block goes on a tile with
// none laid left, kept while any are left. Both are text vars the world save keeps when they are set (WorldSave.dm
// RemasterTurfRecord); old saves have neither and load as before. Dug out, however it is dug, a laid block gives back
// exactly one of what it was made of (Yield.dm RmStoneOut). One tidy, RmLaidTidy, at the end of RemasterColumnSettle
// (Gather.dm), which every taker goes through, moves the marks of laid blocks no longer there into tmp "just gone" marks,
// read once by RmStoneOut. Readers use RmLaidMask: the laid bits of the blocks present.
turf/var/remaster_mat                  // the laid blocks' letters (saved)
turf/var/remaster_laid_by              // the realm root key of who laid them (saved)
turf/var/tmp/rm_laid_gone = 0          // laid blocks that just vanished: bit k, paid back once (Yield.dm RmStoneOut)
turf/var/tmp/rm_mat_gone               // ...and their letters
datum/remaster_order/var/tmp/rm_mat    // a Lay block order's material: "wood", else stone

proc/RmPlanWood(list/Z)
	return Z && Z["kind"] == "build" && Z["mat"] == "wood"

proc/RmPlanMatPath(list/Z)
	return RmPlanWood(Z) ? /obj/Items/woods/wood : /obj/Items/ores/stone

proc/RmPlanMatWord(list/Z)
	return RmPlanWood(Z) ? "logs" : "stone"

// Letter k of a letters text ("." past its end).
proc/RmMatLetter(t, k)
	return (istext(t) && isnum(k) && k >= 0 && k < length(t)) ? copytext(t, k + 1, k + 2) : "."

// The letters text with letter k set to ch (padded with "."), the trailing "." dropped; nothing left is null.
proc/RmMatPut(t, k, ch)
	if(!isnum(k) || k < 0 || k > 15) return t
	t = istext(t) ? t : ""
	while(length(t) <= k) t += "."
	t = copytext(t, 1, k + 1) + ch + copytext(t, k + 2)
	var/n = length(t)
	while(n > 0 && copytext(t, n, n + 1) == ".") n--
	return n ? copytext(t, 1, n + 1) : null

// The laid bits of T's blocks still there.
proc/RmLaidMask(turf/T)
	. = 0
	if(!T || !T.remaster_laid) return
	for(var/k = 0, k <= 15 && (T.remaster_laid >> k), k++)
		if((T.remaster_laid & (1 << k)) && RemasterBlockThere(T, k)) . |= 1 << k

// A column with laid blocks still there, its natural base under them included (building rework L2, step 1b: built blocks
// are walls, not a quarry): no automatic digging takes it (a stone zone, the miner job, board and delivery orders, away
// workers); only a Plan dig or a direct order does. Two or more laid blocks high it is a built wall for the village's
// progress (Progress.dm); it holds an underground roof as a wall does (Buildings.dm) and shows as one on the minimap.
proc/RmBuilt(turf/T)
	return (T && T.remaster_laid) ? RmLaidMask(T) : 0

// How many laid blocks T has still there.
proc/RmLaidCount(turf/T)
	. = 0
	var/m = RmBuilt(T)
	while(m)
		if(m & 1) .++
		m >>= 1

// Laid block k's material: "w" wood, else "s" (just gone or still there).
proc/RmLaidMatOf(turf/T, k)
	if(T.rm_laid_gone & RmStoneBit(k)) return RmMatLetter(T.rm_mat_gone, k) == "w" ? "w" : "s"
	return RmMatLetter(T.remaster_mat, k) == "w" ? "w" : "s"

// Block k was laid by a plan (P's): its bit and letter; the builder's realm when no other laid block is left there.
proc/RmLaidMark(turf/T, k, ch, Player/P)
	var/bit = RmStoneBit(k)
	if(!T || !bit) return
	if(!(RmLaidMask(T) & ~bit)) T.remaster_laid_by = (istype(P) && P.key) ? RemasterRootKey(P.key) : null
	T.remaster_laid |= bit
	if(istype(P) && RmGuestKey(P.key))   // a guest's: down when they leave (Guests.dm)
		if(!P.rm_guest_laid) P.rm_guest_laid = list()
		P.rm_guest_laid[T] = 1
	T.remaster_mat = RmMatPut(T.remaster_mat, k, ch == "w" ? "w" : "s")
	remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1

// Block k's laid marks are spent (paid back, or a fresh block goes there): its bit and letter, now and just gone, and the
// builder's realm with the last of them.
proc/RmLaidForget(turf/T, k)
	var/bit = RmStoneBit(k)
	if(!T || !bit) return
	T.rm_laid_gone &= ~bit
	if(T.rm_mat_gone) T.rm_mat_gone = RmMatPut(T.rm_mat_gone, k, ".")
	if(!T.remaster_laid && !T.remaster_mat && !T.remaster_laid_by) return
	T.remaster_laid &= ~bit
	T.remaster_mat = T.remaster_laid ? RmMatPut(T.remaster_mat, k, ".") : null
	if(!T.remaster_laid) T.remaster_laid_by = null
	remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1

// After any block of T comes out (RemasterColumnSettle): the laid blocks no longer there go into the "just gone" marks
// with their letters; with none laid left, the letters and the builder's realm go too.
proc/RmLaidTidy(turf/T)
	if(!T || (!T.remaster_laid && !T.remaster_mat && !T.remaster_laid_by)) return
	var/changed = 0
	for(var/k = 0, k <= 15 && (T.remaster_laid >> k), k++)
		var/bit = 1 << k
		if(!(T.remaster_laid & bit) || RemasterBlockThere(T, k)) continue
		T.rm_laid_gone |= bit
		T.rm_mat_gone = RmMatPut(T.rm_mat_gone, k, RmMatLetter(T.remaster_mat, k) == "w" ? "w" : "s")
		T.remaster_laid &= ~bit
		T.remaster_mat = RmMatPut(T.remaster_mat, k, ".")
		changed = 1
	if(!T.remaster_laid && (T.remaster_mat || T.remaster_laid_by))
		T.remaster_mat = null
		T.remaster_laid_by = null
		changed = 1
	if(changed) remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1

// Whether T's column can take blocks at all (the ground, or rock already there).
proc/RmPlanGroundOK(turf/T, Player/P, k = 0)
	if(!T || T.z != GROUND_LAYER) return 0
	if(T.Owner && P && T.Owner != P && !RmQuestWorkLets(P, T)) return 0   // a work notice's taker lays on its maker's floor (QuestTargets.dm)
	if(T.remaster_carve || T.remaster_carve_plan || T.remaster_slope || T.remaster_wallwalk || T.remaster_ramp || T.Tree || T.IsWall || T.isbridge) return 0
	if(Remaster3DIsStairs(T)) return 0
	if(T.density) return RemasterIsMountain(T)
	var/state = "[T.icon_state]"
	if((state in list("Chasm", "Sky", "FarmLand")) || T.HasPlantIn) return 0
	if(T.Content3 == "Liquid" || findtext(state, "Water") || findtext(state, "Swamp") || findtext(state, "Lava") || findtext(state, "Hole")) return 0
	if(k > 0 && !T.density) return 1   // a block over a room (the layered builder, phase 3): what stands on the floor under it doesn't matter
	for(var/atom/movable/A in T)
		if(istype(A, /mob/Monsters)) continue           // units step aside (RmPlanOccupied)
		if(istype(A, /obj/Items))
			var/obj/Items/I = A
			if(!I.remaster_placed && !I.density && !istype(I, /obj/Items/Furniture)) continue   // loose pieces are moved aside
		else if(isobj(A) && !A.density) continue
		return 0
	var/turf/U = locate(T.x, T.y, SKY_LAYER)
	if(U && (U.density || !(U.icon_state in list("Sky", "Peak")))) return 0   // a built floor or roof over it
	return 1

// Whether block k can go on T's column now: on open ground (k 0), on the top of a column, into a hole, or under a
// tunnel's ceiling (the block under the ceiling, or the floor block).
proc/RmPlanCanLay(turf/T, k, Player/P)
	if(!isnum(k) || k < 0 || k >= RM_BUILD_TOP || RemasterBlockThere(T, k) || !RmPlanGroundOK(T, P, k)) return 0
	if(T.density)
		var/h = RemasterBlocksAt(T)
		if(k == 0 || k > h) return 0
		if(k < h) return 1                       // a hole: the rock over it holds it
		return RemasterBlockThere(T, k - 1)      // on its top
	if(T.remaster_roof > 0 && (k == 0 || k == (T.remaster_ceil || 2) - 1)) return 1
	if(k > 0 && T.remaster_roof > 0 && RemasterBlockThere(T, k - 1)) return 1   // on a ceiling's blocks: they hold it
	if(k > 0 && !RemasterBlockThere(T, k - 1) && RmPlanHeld(T, k)) return 1   // over open air, held by the walls or a pillar (Sites.dm, phase 3)
	return k == 0

// For a plan being queued: block k can go on now, or the plan's blocks under it (or over it, up to a tunnel's
// ceiling) lead to one that can.
Player/proc/RmPlanBuildable(turf/T, k, list/want)
	if(RmPlanCanLay(T, k, src)) return 1
	if(!isnum(k) || k < 0 || k >= RM_BUILD_TOP || RemasterBlockThere(T, k) || !RmPlanGroundOK(T, src, k)) return 0
	if(k > 0 && !T.density && RmPlanHeld(T, k, want)) return 1   // over open air: held once the plan's walls or pillars are in (phase 3)
	for(var/j = k - 1, j >= 0, j--)
		if(!want["[T.x],[T.y],[j]"]) break
		if(RmPlanCanLay(T, j, src)) return 1
		if(j > 0 && !T.density && RmPlanHeld(T, j, want)) return 1   // on a planned block held over open air (a room's wall on its floor sticking out past a house: phase 3)
	if(!T.density && T.remaster_roof > 0) for(var/j = k + 1, j < (T.remaster_ceil || 2), j++)
		if(!want["[T.x],[T.y],[j]"]) break
		if(RmPlanCanLay(T, j, src)) return 1
	return 0

// Whether someone (other than M) is where block k of T's column would go: on the ground there (the floor block),
// or up there with its feet at that height.
proc/RmPlanOccupied(turf/T, k, mob/Monsters/M)
	if(k == 0) for(var/mob/Monsters/X in T) if(X != M) return 1
	var/turf/U = locate(T.x, T.y, SKY_LAYER)
	if(U) for(var/mob/Monsters/X in U) if(X != M && RemasterFeetOf(X) == k) return 1
	return 0

// Block k goes on T's column (RmPlanCanLay said it can).
proc/RmPlanPutBlock(turf/T, k)
	remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1   // the world save keeps it (WorldSave.dm)
	RmLaidForget(T, k)       // a fresh block: natural rock's stone, unless a build plan marks it laid (Yield.dm); no stale letter
	T.rm_stone_half &= ~RmStoneBit(k)
	RmKeepHeight(T)
	if(!T.density)
		if(k == 0) RmPlanCloseColumn(T)
		else if(T.remaster_roof <= 0)   // over open air, held (phase 3): a room's ceiling, the room under it left open, stood on above
			T.remaster_ceil = k
			T.remaster_roof = 1
			T.remaster_holes &= ~(1 << k)
			RmPlanPeak(T)
		else                      // under a tunnel's ceiling, or over it (another storey's): the gap between stays open
			var/c = T.remaster_ceil || 2
			if(k < c)
				for(var/j = k + 1, j < c, j++) T.remaster_holes |= 1 << j
				T.remaster_roof += c - k
				T.remaster_ceil = k
			else if(k >= c + T.remaster_roof)
				for(var/j = c + T.remaster_roof, j < k, j++) T.remaster_holes |= 1 << j
				T.remaster_roof = k - c + 1
			T.remaster_holes &= ~(1 << k)
	else
		var/h = RemasterBlocksAt(T)
		if(k < h)
			if(k == 1 && T.remaster_dug_top)
				T.remaster_dug_top = 0
				T.HP = max(T.HP, initial(T.HP), 40)
		else if(T.remaster_topcut > 0) T.remaster_topcut--
		else
			T.remaster_built = h + 1
			T.remaster_blocks = T.remaster_built
		T.remaster_holes &= ~(1 << k)
	RemasterFeetCheck(T)

// The floor block on open ground: the tile closes into a column of rock (one block, or up to a tunnel's roof with the
// room under its ceiling left open), and the sky over it becomes a mountain top.
proc/RmPlanCloseColumn(turf/T)
	var/c = T.remaster_roof > 0 ? (T.remaster_ceil || 2) : 0
	var/h = c ? c + T.remaster_roof : 1
	var/gaps = c ? T.remaster_holes : 0
	for(var/j = 2, j < c, j++) gaps |= 1 << j
	T.remaster_built_floor = "[T.icon]|[T.icon_state]|[T.name]|[T.Detailed ? 1 : 0]|[T.Content3]"
	T.rm_built_icon = T.icon
	var/turf/side = RemasterBuildSpot(T, null)
	if(side) for(var/obj/Items/I in T) I.loc = side
	T.icon = 'Cave.dmi'
	T.icon_state = "CaveWall"
	T.name = "Mountain"
	T.density = 1
	T.opacity = 1
	T.CanDigAt = 1
	T.IsWall = 0
	T.Detailed = 0
	T.Content3 = "CanClimb"
	T.HP = max(T.HP, initial(T.HP), 40)
	T.remaster_vein = ""
	T.remaster_built = h
	T.remaster_blocks = h
	T.remaster_topcut = 0
	T.remaster_holes = gaps
	T.remaster_dug = 0
	T.remaster_dug_top = c > 1
	T.remaster_roof = 0
	T.remaster_ceil = 0
	var/turf/U = locate(T.x, T.y, SKY_LAYER)
	if(U && U.icon_state != "Peak")
		U.icon = 'Cave.dmi'
		U.icon_state = "Peak"
		U.name = "MountainPeak"
		if(U.Content == "Sky") U.Content = 0
		remaster_dirty_turfs["[U.x],[U.y],[U.z]"] = 1

// A block laid on open ground is dug out again: the ground it was laid on comes back (Gather.dm calls this).
proc/RmBuiltFloorBack(turf/T)
	var/list/p = splittext("[T.remaster_built_floor]", "|")
	T.remaster_built_floor = null
	if(length(p) < 5) return
	if(T.rm_built_icon) T.icon = T.rm_built_icon
	else if(fexists(p[1])) T.icon = file(p[1])
	else if(fexists("Icons/[p[1]]")) T.icon = file("Icons/[p[1]]")
	T.rm_built_icon = null
	T.icon_state = p[2]
	T.name = p[3]
	T.Detailed = p[4] == "1"
	T.Content3 = (p[5] == "0" || p[5] == "") ? 0 : p[5]

// One step of a worker on a build plan: the lowest block it can lay first (a wall goes up course by course), with
// stone in the bag; without, a trip for stone.
mob/Monsters/proc/RmPlanBuildStep(Player/P, list/Z)
	var/list/C = Z["cells"]
	if(!islist(C) || !length(C) || !P.RmPlanLeft(Z))
		if(Z["stock"]) P.RmSiteSpill(Z)   // what is left on the site's pile (Sites.dm)
		RemasterStopWork()
		remaster_work_status = "[Z["name"]]: finished"
		return
	if(rm_plan_last && (rm_plan_last in C) && remaster_order_status && (findtext(remaster_order_status, "Out of reach") || findtext(remaster_order_status, "No way") || findtext(remaster_order_status, "Couldn't") || findtext(remaster_order_status, "Skipped")))
		if(!rm_plan_skip) rm_plan_skip = list()
		rm_plan_skip[rm_plan_last] = world.time + RM_PLAN_SKIP
	rm_plan_last = null
	if(world.time < rm_plan_wait) return
	if(RmPlanAccessStep(P, Z)) return       // the plan's way up first, for the worker cutting it
	if(!P.rm_plan_res) P.rm_plan_res = list()
	var/list/R = P.rm_plan_res[Z["id"]]
	if(!R)
		R = list()
		P.rm_plan_res[Z["id"]] = R
	var/up = z == SKY_LAYER
	var/feet = up ? RemasterFeetOf(src) : 0
	var/best
	var/bk
	var/turf/bt
	var/bs = 1#INF
	var/layable = 0
	var/stood = 0
	for(var/c in C)
		if(rm_plan_skip && rm_plan_skip[c] && rm_plan_skip[c] > world.time) continue
		var/mob/Monsters/H = R[c]
		if(H && H != src && H.rm_jz_id == Z["id"] && H.remaster_active && H.remaster_active.automatic && H.rm_plan_last == c) continue
		var/list/q = RmPlanCell(c)
		var/turf/T = q[1]
		var/k = q[2]
		if(!RmPlanCanLay(T, k, P)) continue      // not yet: the blocks under it first
		if(P.RmPlanHoldFor(T, k, Z)) continue   // the one beside it first, from its place (Sites.dm)
		layable++
		if(RmPlanOccupied(T, k, src))
			RmPlanClearSpot(T, k, src)   // whoever stands there and is free to steps aside (Sites.dm)
			stood++
			continue
		if(up)
			if(abs(T.x - x) > 12 || abs(T.y - y) > 12 || !RemasterReaches(feet, k)) continue
		else
			if(!RemasterReaches(0, k) || !RemasterBuildSpot(T, src)) continue   // from the ground: its three lowest, from beside it
		var/s = get_dist(src, T) + k * 3 + (up ? abs(k - feet) * 0.3 : 0)
		if(s < bs)
			bs = s
			best = c
			bk = k
			bt = T
	var/aim_up = up
	if(!best && layable && stood >= layable)
		// all it could lay has someone on it: they step away in time
		RemasterStopWork()
		remaster_work_status = "[Z["name"]]: waiting, someone is standing where a block goes"
		rm_plan_wait = world.time + 20
		return
	if(!best && layable)
		switch(RmPlanWayThere(P, Z))
			if(1) return
			if(2)
				best = rm_ac_cell
				var/list/q = RmPlanCell(best)
				bt = q[1]
				bk = q[2]
				aim_up = 1
	if(!best)
		RemasterStopWork()
		if(layable)
			// nothing of it in reach: off the plan for a minute, so the allocator gives the place to someone who can get there
			remaster_work_status = "[Z["name"]]: nothing in reach from here"
			Z["stuck_at"] = world.time
			if(!remaster_board_skip) remaster_board_skip = list()
			remaster_board_skip[Z["id"]] = world.time + 600
			P.RmJobLeave(src)
		else
			remaster_work_status = "[Z["name"]]: waiting for the blocks under the rest"
			rm_plan_wait = world.time + 20
		return
	var/turf/PL = up ? null : P.RmSitePile(Z)   // a construction site (Sites.dm): the stone carried to a pile at the site first, the walls built from it
	if(PL && RmSiteStep(P, Z, PL, RmPlanMatPath(Z), RmPlanMatWord(Z), length(C))) return
	var/mp = RmPlanMatPath(Z)       // stone, or logs for a wood plan (building rework L1)
	var/word = RmPlanMatWord(Z)
	var/obj/Items/S
	var/have = RemasterCarriedCount(mp)
	if(!have)
		var/turf/PU = up ? P.RmSitePile(Z) : null   // up there with none: back down to the site's pile for more (its stone is often all on the pile, none left in the stores: the real game 10-30)
		if(PU) for(var/obj/Items/X in PU) if(istype(X, mp) && P.RemasterMayCollect(X))
			S = X
			break
		if(!S) S = P.RemasterSiteSource(list("z" = GROUND_LAYER), mp, src)
		if(!S)
			RemasterStopWork()
			remaster_work_status = "[Z["name"]]: waiting for [word] (none in the stores)"
			if(!Z["need"]) P.RmSitePostNeed(Z)   // a board order for it (Sites.dm)
			Z["need"] = word
			rm_plan_wait = world.time + 30
			return
		Z["need"] = null
		if(weight + S.weight > weightmax)
			RemasterStopWork()
			remaster_work_status = "[Z["name"]]: the bag is too heavy to carry [word]"
			rm_plan_wait = world.time + 30
			return
		RmPlanFetch(P, S)
		remaster_work_status = "[Z["name"]]: fetching [word]"
		return
	// at a pile: a few more for the next blocks
	if(have < min(RM_BUILD_LOAD, length(C)) && !up)
		for(var/obj/Items/X in range(1, src))
			if(!istype(X, mp) || !isturf(X.loc) || !P.RemasterMayCollect(X) || weight + X.weight > weightmax) continue
			RmPlanFetch(P, X)
			remaster_work_status = "[Z["name"]]: fetching [word]"
			return
	R[best] = src
	rm_plan_last = best
	var/datum/remaster_order/O = new
	O.issuer = P
	O.target = aim_up ? locate(bt.x, bt.y, SKY_LAYER) : bt
	if(rm_plan_debug) world.log << "RMPLAN|lay|[name]|[best]|at [x],[y],[z] feet=[feet] aim_up=[aim_up] remaster_feet=[remaster_feet]"
	O.kind = "Lay block"
	O.block = bk
	O.rm_mat = RmPlanWood(Z) ? "wood" : null
	O.automatic = 1
	O.rm_plan = 1
	if(aim_up && best == rm_ac_cell)
		O.rm_spot = rm_ac_spot      // where its way there leads
		O.rm_spot_f = rm_ac_spot_f
	RemasterSuspendControllers()
	remaster_active = O
	RemasterStartOrder(O)
	remaster_work_status = "[Z["name"]]: laying a block"
	RemasterOrderTick()

mob/Monsters/proc/RmPlanFetch(Player/P, obj/Items/I)
	var/datum/remaster_order/O = new
	O.issuer = P
	O.target = I
	O.kind = "Pick up"
	O.automatic = 1
	O.rm_plan = 1
	remaster_auto_unload = 0        // the stone is for building: never a trip to put it back
	RemasterSuspendControllers()
	remaster_active = O
	RemasterStartOrder(O)
	RemasterOrderTick()

// One tick of a Lay block order (Orders.dm RemasterOrderTick): beside the column (from the ground its three lowest
// blocks; up on the mountain, a place beside it with the block in reach, never on the column itself), a few blows,
// then the block is in and a stone is used up.
mob/Monsters/proc/RmPlanLayTick(datum/remaster_order/O)
	var/turf/A = O.target
	var/turf/T = A.z == SKY_LAYER ? locate(A.x, A.y, GROUND_LAYER) : A
	var/turf/U = locate(T.x, T.y, SKY_LAYER)
	var/k = O.block
	if(RemasterBlockThere(T, k))
		RemasterFinishOrder("That block is in already")
		return
	if(!RmPlanCanLay(T, k, Owner))
		RemasterFinishOrder("Skipped: that block can't go there now")
		return
	var/mp = O.rm_mat == "wood" ? /obj/Items/woods/wood : /obj/Items/ores/stone     // building rework L1
	var/word = O.rm_mat == "wood" ? "logs" : "stone"
	if(!RemasterCarriedCount(mp))
		RemasterFinishOrder("Skipped: no [word] carried")
		return
	if(z != SKY_LAYER)
		if(!RemasterReaches(0, k))
			RemasterFinishOrder("Out of reach: a unit lays three blocks up from where it stands; higher ones from up on the mountain")
			return
		if(loc == T)
			var/turf/off = RemasterBuildSpot(T, src)
			if(!off)
				RemasterFinishOrder("Skipped: nowhere beside it to stand")
				return
			RemasterApproach(O, off, 0)
			return
		if(get_dist(src, T) > 1)
			RemasterGiveUpOrApproach(O, T, 1)
			return
	else
		var/f = RemasterFeetOf(src)
		if(get_dist(src, U) > 1 || !RemasterReaches(f, k) || loc == U)
			var/turf/S = RemasterWorkSpot(src, U, k, 1)
			if(!S)
				RemasterFinishOrder("Out of reach: nowhere beside it to stand with that block in reach (three blocks up from the feet)")
				return
			if(loc != S || f != O.spot_feet)
				RmPlanClearPlace(S, O.spot_feet, src)   // someone idle on the place to work from: aside (Sites.dm, phase 3)
				RemasterApproach(O, S, 0)
				return
	if(RmPlanOccupied(T, k, src))
		RmPlanClearSpot(T, k, src)   // whoever stands there and is free to steps aside (Sites.dm)
		RemasterBlock("Waiting: someone is standing where the block goes")
		O.last_progress = world.time
		return
	remaster_blocked = null
	destination = null
	remaster_order_status = "Laying a block"
	if(world.time < remaster_hand_at) return
	remaster_hand_at = world.time + max(8, Delay * 2)
	dir = get_dir(src, T) || dir
	O.last_progress = world.time
	O.lay++
	if(O.lay < RM_BUILD_WORK) return
	var/obj/Items/S
	for(var/obj/Items/X in src) if(istype(X, mp) && X.suffix != "(Equipped)")
		S = X
		break
	if(!S)
		RemasterFinishOrder("Skipped: no [word] carried")
		return
	weight -= S.weight
	del S
	RmPlanPutBlock(T, k)
	RmLaidMark(T, k, O.rm_mat == "wood" ? "w" : "s", Owner)     // dug out again, it gives back the 1 stone or log it cost (Yield.dm RmStoneOut)
	if(rm_quest_working) RmQuestLaid(src, T, k)   // a work notice's block: the maker's, counted for its taker (QuestTargets.dm)
	if(istype(Owner, /Player))   // a stair's step: its ramp at once (PlanPieces.dm), so the way up is there for the plan's next search
		var/Player/SP = Owner
		if(SP.rm_plan_steps && SP.rm_plan_steps["[T.x],[T.y],[k]"]) SP.RmPlanStepTick()
	RemasterFinishOrder("Laid a block")

// --- Cutting a way there (2026-10-25; tried out first as the arena's planAccess) ---------------------------------------
// A plan's blocks nobody can reach (more than three up from the ground, nobody up there): a worker works out the
// cheapest way from where it stands to a place with one of them in reach, by tile and height, and puts the work on the
// plan as its own jobs (Z["access"], in route order): walking where it can (along, down a block, up a ramp), tunnelling
// (dig the block ahead at its height), cutting a step (dig the room over the block ahead and carve it into a ramp: one
// block up), and on a build plan building a step (lay a block where it can go and carve it into a ramp). Only rock no
// plan wants for anything else is cut, never a plan's block or a ramp. One worker does the access jobs; the others wait
// for the way, or work what they reach.

#define RM_ACCESS_R 12           // tiles round the worker searched
#define RM_ACCESS_ITER 8000      // places looked at, at most
#define RM_ACCESS_EVERY 50       // ticks between two searches for one plan

// Whether a unit can stand at height f over G (G on the ground layer): open ground at 0, else a block under it and room
// in it up on the mountain.
proc/RmAcStand(turf/G, f)
	if(!G) return 0
	if(f == 0)
		if(G.density || (G.icon_state in list("Chasm", "Sky")) || G.Content3 == "Liquid" || findtext("[G.icon_state]", "Water") || G.icon == 'Stairs.dmi') return 0
		for(var/atom/movable/A in G) if(A.density && !istype(A, /mob/Monsters)) return 0
		return 1
	var/turf/U = locate(G.x, G.y, SKY_LAYER)
	if(!U || U.density || (U.icon_state in list("Sky", "Chasm")) || !RemasterIsMountain(G)) return 0
	return RemasterBlockThere(G, f - 1) && !RemasterBlockThere(G, f)

// Whether the route may cut block k of G's column: rock no plan wants for anything else, not a ramp, nobody on it.
Player/proc/RmAcFree(turf/G, k, list/Z)
	if(!RemasterIsMountain(G) || !RemasterBlockThere(G, k) || RmPlanStoodOn(G, k)) return 0
	if(G.remaster_carve || G.remaster_carve_plan || (G.remaster_slope && G.remaster_slope_h == k + 1)) return 0
	var/c = "[G.x],[G.y],[k]"
	for(var/list/X in rm_jz) if(RmPlanKind(X["kind"]) && (c in X["cells"]) && (X != Z || X["kind"] == "build")) return 0
	return 1

mob/Monsters/var/tmp/rm_ac_cell      // a block of the plan M can walk to with no work (RmPlanAccess)
mob/Monsters/var/tmp/rm_ac_from      // where M stood for that search: "x,y,z,feet"
mob/Monsters/var/tmp/turf/rm_ac_spot // the place the way leads to (up there), and its height
mob/Monsters/var/tmp/rm_ac_spot_f

// The route for M to the plan's blocks it can't reach: puts the jobs on the plan and returns how many; 0 when there is
// no way, or when the way needs no work (then M.rm_ac_cell is the block it can walk up to).
Player/proc/RmPlanAccess(list/Z, mob/Monsters/M)
	M.rm_ac_cell = null
	M.rm_ac_spot = null
	M.rm_ac_from = "[M.x],[M.y],[M.z],[RemasterFeetOf(M)]"
	var/build = Z["kind"] == "build"
	var/list/C = Z["cells"]
	if(!length(C)) return 0
	var/turf/S0 = M.z == SKY_LAYER ? locate(M.x, M.y, GROUND_LAYER) : M.loc
	if(!S0 || S0.z != GROUND_LAYER) return 0
	var/f0 = M.z == SKY_LAYER ? RemasterFeetOf(M) : 0
	var/W = RM_ACCESS_R * 2 + 1
	var/x0 = S0.x - RM_ACCESS_R
	var/y0 = S0.y - RM_ACCESS_R
	var/H = RM_BUILD_TOP + 1
	var/N = W * W * H
	var/list/dist = new /list(N)
	var/list/prev = new /list(N)
	var/list/how = new /list(N)
	var/list/goal = new /list(N)
	var/list/sgoal = new /list(N)   // goals on a building's stairs: taken only when no other is reached
	// the places with a block of the plan in reach: beside its column, at most two blocks under it or over it
	var/list/plan = list()
	for(var/c in C) plan[c] = 1
	var/goals = 0
	for(var/c in C)
		var/list/q = RmPlanCell(c)
		var/turf/T = q[1]
		var/k = q[2]
		if(build ? (!RmPlanCanLay(T, k, src) || RmPlanHoldFor(T, k, Z)) : !RemasterBlockThere(T, k)) continue
		var/turf/TU = locate(T.x, T.y, SKY_LAYER)
		var/other = 0          // someone on that block, M too (mining takes the block under a miner's feet), or, to build,
		                       // someone else where it goes (M steps aside to lay it): not a block to go for
		if(TU) for(var/mob/Monsters/X in TU) if((X != M || !build) && RemasterFeetOf(X) == (build ? k : k + 1)) other = 1
		if(other) continue
		var/list/gs = list()
		var/list/st = list()   // places on a building's stairs: only when there is no other for this block (a wall beside the stairs)
		for(var/dx = -1, dx <= 1, dx++) for(var/dy = -1, dy <= 1, dy++)
			if(!dx && !dy) continue
			var/gx = T.x + dx - x0
			var/gy = T.y + dy - y0
			if(gx < 0 || gy < 0 || gx >= W || gy >= W) continue
			var/turf/GU = locate(T.x + dx, T.y + dy, SKY_LAYER)
			for(var/f = max(1, k - RM_REACH_UP), f <= min(H - 1, k + RM_REACH_DOWN), f++)   // up there only: work from the ground is the plan step's own
				if(plan["[T.x + dx],[T.y + dy],[f]"] && !(build && RmPlanHoldFor(locate(T.x + dx, T.y + dy, GROUND_LAYER), f, Z))) continue   // a block of the plan still to go where its feet would be: never a place to work from (phase 3), but one waiting for the blocks beside it (RmPlanHoldFor)
				if((f == 1 && RmFirstStep(GU)) || RmStairPassage(GU)) st += 1 + gx + gy * W + f * W * W   // a building's first step, a step with another over it
				else gs += 1 + gx + gy * W + f * W * W
		for(var/gi in gs)
			goal[gi] = c
			goals++
		for(var/gi in st) if(!goal[gi])
			goal[gi] = c
			sgoal[gi] = 1
			goals++
	if(!goals) return 0
	var/i0 = 1 + (S0.x - x0) + (S0.y - y0) * W + f0 * W * W
	dist[i0] = 0
	var/list/B = list(list(i0))     // bucket d + 1: the places d away
	var/found = 0
	var/sfound = 0
	var/seen = 0
	for(var/d = 0, d < length(B) && !found && seen < RM_ACCESS_ITER, d++)
		var/list/bucket = B[d + 1]
		for(var/bi = 1, bi <= length(bucket) && !found, bi++)
			var/i = bucket[bi]
			if(dist[i] != d) continue
			seen++
			if(goal[i] && d > 0)
				if(!sgoal[i])
					found = i
					break
				if(!sfound) sfound = i   // on the stairs: kept in case no other place is reached (a wall beside them: arena offset_room.dm 10-30)
			var/f = round((i - 1) / (W * W))
			var/r = (i - 1) % (W * W)
			var/x = x0 + r % W
			var/y = y0 + round(r / W)
			for(var/dd in list(NORTH, SOUTH, EAST, WEST))
				var/nx = x + (dd == EAST ? 1 : dd == WEST ? -1 : 0)
				var/ny = y + (dd == NORTH ? 1 : dd == SOUTH ? -1 : 0)
				if(nx < x0 || ny < y0 || nx >= x0 + W || ny >= y0 + W) continue
				var/turf/G = locate(nx, ny, GROUND_LAYER)
				if(!G) continue
				var/base = 1 + (nx - x0) + (ny - y0) * W
				// along, down a block, up a ramp that is there
				if(RmAcStand(G, f)) RmAcGo(B, dist, prev, how, base + f * W * W, d + 1, i, null)
				if(f >= 1 && !Z["stairs"] && RmAcStand(G, f - 1) && !RemasterBlockThere(G, f)) RmAcGo(B, dist, prev, how, base + (f - 1) * W * W, d + 1, i, null)   // (a building with its own stairs: no way planned down a block, onto a roof with no way off)
				if(f + 1 < H && RmAcStand(G, f + 1) && RemasterSlopeOn(G) && G.remaster_slope_h == f + 1) RmAcGo(B, dist, prev, how, base + (f + 1) * W * W, d + 1, i, null)
				if(Z["stairs"]) continue   // a building with its own stairs (PlanPieces.dm): its way up is them, nothing cut or built for it (a way cut through its own wall stalled it: arena tests/storeys.dm)
				var/c = "[nx],[ny],[f]"
				var/at = "[x],[y],[f]"        // where on the route a job here is done from
				var/under = f == 0 || RemasterBlockThere(G, f - 1)
				var/held = G.remaster_laid && RmBuiltHeld(src, G)   // another realm's built wall: never dug or carved (BuiltWalls.dm)
				// tunnel ahead: the block at its height out (one block of room), the one under it the floor
				if(under && !held && RmAcFree(G, f, Z) && (!plan[c] || !build) && (f == 0 || RmAcStandOver(G))) RmAcGo(B, dist, prev, how, base + f * W * W, d + 3, i, list("[c],dig,[at]"))
				if(f + 1 >= H) continue
				var/c1 = "[nx],[ny],[f + 1]"
				// a step up: the room over the block ahead dug, the block carved into a ramp
				if(under && !held && RemasterIsMountain(G) && RemasterBlockThere(G, f) && !plan[c] && !(G.remaster_slope && G.remaster_slope_h == f + 1) && !G.remaster_carve && !G.remaster_carve_plan)
					var/room = !RemasterBlockThere(G, f + 1)
					if((room || (RmAcFree(G, f + 1, Z) && (!plan[c1] || !build))) && RmAcStandOver(G))
						RmAcGo(B, dist, prev, how, base + (f + 1) * W * W, d + (room ? 5 : 7), i, room ? list("[c],ramp,[at]") : list("[c1],dig,[at]", "[c],ramp,[at]"))
				// a built step (build plans): the column ahead laid up to this height (open ground, or a lower column of
				// rock), its top block carved into a ramp
				if(build && !RemasterBlockThere(G, f + 1))
					var/t = G.density ? RemasterTopHeight(G) : (G.remaster_roof > 0 ? -1 : 0)
					if(t >= 0 && t <= f && t >= f - RM_REACH_DOWN && RmPlanCanLay(G, t, src) && !RmPlanOccupied(G, t, M))   // all laid from here
						var/list/lay = list()
						for(var/j = t, j <= f && lay, j++) lay = plan["[nx],[ny],[j]"] ? null : lay + "[nx],[ny],[j],lay,[at]"
						if(lay) RmAcGo(B, dist, prev, how, base + (f + 1) * W * W, d + 4 + 2 * length(lay), i, lay + "[c],ramp,[at]")
	if(!found) found = sfound
	if(!found) return 0
	var/list/jobs = list()
	for(var/i = found, i && i != i0, i = prev[i]) if(how[i]) jobs.Insert(1, how[i])
	if(!length(jobs))
		M.rm_ac_cell = goal[found]
		var/ff = round((found - 1) / (W * W))
		var/rr = (found - 1) % (W * W)
		M.rm_ac_spot = locate(x0 + rr % W, y0 + round(rr / W), ff ? SKY_LAYER : GROUND_LAYER)
		M.rm_ac_spot_f = ff
		return 0
	Z["access"] = jobs
	Z["access_by"] = M
	Z["access_fail"] = 0
	return length(jobs)

proc/RmAcGo(list/B, list/dist, list/prev, list/how, i, d, from, list/jobs)
	if(!isnull(dist[i]) && dist[i] <= d) return
	dist[i] = d
	prev[i] = from
	how[i] = jobs
	while(length(B) < d + 1) B += list(list())
	var/list/bucket = B[d + 1]
	bucket += i

// The mountain top over G a unit can stand on (not open sky over a lone block's ground: Peak, or Sky that a laid
// block makes a top of).
proc/RmAcStandOver(turf/G)
	var/turf/U = locate(G.x, G.y, SKY_LAYER)
	return U && !U.density && U.icon_state == "Peak"

// Whether an access job is done: "x,y,k,what,sx,sy,sf" (block k of x,y; done from height sf over sx,sy).
proc/RmAcDone(j)
	var/list/p = splittext(j, ",")
	var/turf/T = locate(text2num(p[1]), text2num(p[2]), GROUND_LAYER)
	var/k = text2num(p[3])
	if(!T) return 1
	switch(p[4])
		if("dig") return !RemasterBlockThere(T, k)
		if("lay") return RemasterBlockThere(T, k)
		if("ramp") return RemasterSlopeOn(T) && T.remaster_slope_h == k + 1
	return 1

// Nothing of the plan in reach for M: 1 when the plan's way up is being cut (M waits for it, or has just started on
// it), 2 when M can walk up to a block (rm_ac_cell), 0 when there is no way from here.
mob/Monsters/proc/RmPlanWayThere(Player/P, list/Z)
	if(P.RmPlanStairsComing(Z))   // its own stairs are its way up (the layered builder, phase 3): wait for them, cut no other
		RemasterStopWork()
		remaster_work_status = "[Z["name"]]: waiting for its stairs"
		rm_plan_wait = world.time + 20
		return 1
	if(Z["stairs_at"] && z == GROUND_LAYER)   // its stairs are its way up: over to their foot first (the way is looked for 12 tiles round)
		var/list/sa = splittext(Z["stairs_at"], ",")
		var/turf/F = locate(text2num(sa[1]), text2num(sa[2]), GROUND_LAYER)
		if(F && get_dist(src, F) > 5)
			var/datum/remaster_order/GO = new
			GO.issuer = P
			GO.target = F
			GO.kind = "Move"
			GO.automatic = 1
			GO.rm_plan = 1
			RemasterSuspendControllers()
			remaster_active = GO
			RemasterStartOrder(GO)
			remaster_work_status = "[Z["name"]]: going up its stairs"
			return 1
	if(length(Z["access"]))
		RemasterStopWork()
		remaster_work_status = "[Z["name"]]: waiting for the way up"
		rm_plan_wait = world.time + 20
		return 1
	if(world.time < (Z["access_at"] || 0))
		// searched a moment ago (for someone): the block it found to walk up to, else a wait for the next search
		if(rm_ac_cell && rm_ac_from == "[x],[y],[z],[RemasterFeetOf(src)]" && (rm_ac_cell in Z["cells"]) && !(rm_plan_skip && rm_plan_skip[rm_ac_cell] > world.time)) return 2
		RemasterStopWork()
		remaster_work_status = "[Z["name"]]: looking for a way up"
		rm_plan_wait = world.time + 20
		return 1
	Z["access_at"] = world.time + RM_ACCESS_EVERY
	if(P.RmPlanAccess(Z, src) && RmPlanAccessStep(P, Z)) return 1
	return rm_ac_cell ? 2 : 0

// One step on the plan's way there, for the worker doing it: the first job not done yet. 1 when it gave an order (or is
// on its way to stone); 0 when there is none for it.
mob/Monsters/proc/RmPlanAccessStep(Player/P, list/Z)
	var/list/AC = Z["access"]
	if(!islist(AC)) return 0
	while(length(AC) && RmAcDone(AC[1])) AC.Cut(1, 2)
	if(!length(AC))
		Z["access"] = null
		Z["access_by"] = null
		rm_plan_skip = null       // the way is there: the blocks it couldn't get to are worth another go
		return 0
	var/mob/Monsters/by = Z["access_by"]
	if(by && by != src && by.rm_jz_id == Z["id"] && by.HP > 0) return 0
	Z["access_by"] = src
	var/j = AC[1]
	// its last order was for this job and the job isn't done: it gave up; three times and the way is dropped (worked
	// out again later)
	if(rm_plan_last == "acc:[j]")
		Z["access_fail"] = (Z["access_fail"] || 0) + 1
		if(Z["access_fail"] >= 3)
			Z["access"] = null
			Z["access_by"] = null
			Z["stuck_at"] = world.time
			rm_plan_last = null
			return 0
	var/list/p = splittext(j, ",")
	var/turf/T = locate(text2num(p[1]), text2num(p[2]), GROUND_LAYER)
	var/k = text2num(p[3])
	var/what = p[4]
	if(what == "lay" && !RemasterCarriedCount(RmPlanMatPath(Z)))
		var/obj/Items/S = P.RemasterSiteSource(list("z" = GROUND_LAYER), RmPlanMatPath(Z), src)
		if(!S || weight + S.weight > weightmax)
			remaster_work_status = "[Z["name"]]: waiting for [RmPlanMatWord(Z)] to build a step"
			rm_plan_wait = world.time + 30
			return 1
		RmPlanFetch(P, S)
		remaster_work_status = "[Z["name"]]: fetching [RmPlanMatWord(Z)] for a step"
		return 1
	// from the place on the route the job is done from: on the ground there, or up there at its height (the work spot)
	var/sf = length(p) >= 7 ? text2num(p[7]) : (z == GROUND_LAYER ? 0 : RemasterFeetOf(src))
	var/ground = sf == 0
	var/datum/remaster_order/O = new
	O.issuer = P
	O.target = ground ? T : locate(T.x, T.y, SKY_LAYER)
	if(!ground && length(p) >= 7)
		O.rm_spot = locate(text2num(p[5]), text2num(p[6]), SKY_LAYER)
		O.rm_spot_f = sf
	O.kind = what == "dig" ? ((ground && !T.density) ? "Mine roof" : "Mine") : what == "ramp" ? "Carve ramp" : "Lay block"
	O.block = k
	O.automatic = 1
	O.rm_plan = 1
	if(what == "lay") O.rm_mat = RmPlanWood(Z) ? "wood" : null     // the plan's material (building rework L1)
	remaster_auto_unload = what == "dig"
	rm_plan_last = "acc:[j]"
	if(rm_plan_debug) world.log << "RMPLAN|way|[name]|[j]|at [x],[y],[z] feet=[RemasterFeetOf(src)] ground=[ground] jobs=[jointext(AC, " ")]"
	RemasterSuspendControllers()
	remaster_active = O
	RemasterStartOrder(O)
	remaster_work_status = "[Z["name"]]: cutting a way up ([length(AC)] to go)"
	RemasterOrderTick()
	return 1

// --- The blocks being worked (the user, 2026-10-25: "we should see a yellow highlight of what blocks are being worked
// on") ---------------------------------------------------------------------------------------------------------------
// An own unit's 3D record (View3D.dm, "wk") carries the block it is mining right now, whoever gave the order (a click,
// a dig plan, the job board): list(x, y, block), block -1 the face's next outside block (the old two-block way), -2 the
// column's top (Dig down). Null while it walks there or does anything else. The record is built again whenever the
// unit moves or its order changes, so this costs nothing in between.
proc/RmWorkedBlock3D(mob/Monsters/M)
	var/datum/remaster_order/O = M.remaster_active
	if(!O || !(O.kind in list("Mine", "Mine roof", "Dig down")) || !isturf(O.target)) return null
	var/turf/A = O.target
	if(max(abs(M.x - A.x), abs(M.y - A.y)) > 1) return null      // not at it yet
	if(O.kind == "Dig down") return list(A.x, A.y, -2)
	var/turf/T = A.z == SKY_LAYER ? locate(A.x, A.y, GROUND_LAYER) : A
	if(!isnull(O.block)) return list(T.x, T.y, O.block)
	if(O.kind == "Mine roof") return list(T.x, T.y, T.remaster_ceil || 2)
	return list(T.x, T.y, -1)
