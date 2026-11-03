// Gathering on or off, and a mountain mined all the way (Remastered; the user, 2026-10-24).
//  - The Gather switch (the quick dock's Gather button, key G): on, a click on rock mines it and one on a tree chops
//    it (single-click work orders, as before); off, the default, those clicks are plain moves. The right-click menu's
//    Mine here / Chop it, the jobs and carved steps or ramps work either way. Kept with the player.
//  - Every layer of every mountain tile is a block of its own (the user, 2026-10-24: "only that block ... we need to
//    give each mountain tile a mineable block"): a click mines exactly the block pointed at, anywhere on the face,
//    even with rock left above and below it (remaster_holes); the 3D view draws each block as its own stone.
//  - From the top: units up on a mountain (by a ramp or steps, Mountains.dm) dig its top down, a block an order,
//    with Gather on (the menu's Dig down here either way).

Player/var/remaster_gather = 0            // the Gather switch (saved with the player)
Player/var/tmp/remaster_gather_force = 0  // while a menu order runs: 1 gathers, -1 walks, whatever the switch says
Player/var/tmp/remaster_gather_at = -100

turf/var/remaster_topcut = 0              // blocks dug off a rock column's top from above (saved with the world)
turf/var/remaster_holes = 0               // blocks (2 and up) mined out one by one with rock still above them: bit k, block k (saved)
turf/var/tmp/remaster_top_hp = 0
turf/var/tmp/remaster_blk_hp = 0          // the work left in the block being mined out on its own

datum/remaster_order/var
	feet                 // a move up on a mountain to a dug-out floor: the height it ends at (null: the top)
	turf/spot            // where it stands to work a block up there (RemasterWorkSpot), and at what height
	spot_feet
	top0                 // "Dig down": the column's height when the order started, so two units take one block
	turf/top_off         // "Dig down": where the miner steps off the column before its last block

Player/proc/RemasterGathering()
	return remaster_gather_force ? remaster_gather_force > 0 : remaster_gather

// "1" on, "0" off, anything else turns it over. The page's G and the skin's G may both send one press: a second
// within 0.8 s is that same press, not a new one.
Player/proc/RemasterGatherToggle(value)
	if(value != "1" && value != "0")
		if(world.time - remaster_gather_at < 8) return remaster_gather
		remaster_gather_at = world.time
		value = remaster_gather ? "0" : "1"
	remaster_gather = value == "1"
	remaster_hover = null       // the pointer's verdict was for the old setting: worked out again on the next hover
	remaster_hover_key = null
	if(client) src << output(remaster_gather ? "1" : "0", "mapwindow.hud:gather3d")   // the page at once: its cut and outlines follow
	RemasterNotice(remaster_gather ? "Gather on: a click on rock mines it, on a tree chops it." : "Gather off: clicks on rock and trees walk there. Right-click them to mine or chop.")
	return remaster_gather

// The Gather bar's Auto unload (the owner picked it from hud-controls' bar stills, 10-26): the selected units carry what
// they gather to the stores by themselves when their bags fill ("on"), or keep it ("off"), as the unit card's Auto unload
// does (only what a store takes goes; tools, food and seeds stay carried). "selAutoUnload" in the HUD model: "on", "off",
// "mixed", or null with none selected.
Player/proc/RemasterSelAutoUnload(v)
	if(!(v in list("on", "off"))) return 0
	var/n = 0
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && !M.Wagon)
		M.remaster_auto_unload = v == "on"
		n++
	if(!n)
		RemasterNotice("Select units first.")
		return 0
	RemasterNotice(v == "on" ? "Auto unload on: [n] carry what they gather to the stores when their bags fill." : "Auto unload off: [n] keep what they gather.")
	return 1

Player/proc/RemasterSelAutoUnloadState()
	var/on = 0
	var/off = 0
	for(var/mob/Monsters/M in Selected) if(M.Owner == src)
		if(M.remaster_auto_unload) on++
		else off++
	return on && off ? "mixed" : on ? "on" : off ? "off" : null

// G with the game window in front (skin.dmf).
Player/verb/RemasterGatherVerb()
	set name = "Remaster-Gather"
	set hidden = 1
	RemasterGatherToggle("")

// A menu order (HUD.dm "work3d" / "walk3d"): a 3D click that gathers, or walks, whatever the switch says.
Player/proc/RemasterMenuClick(action, value)
	remaster_gather_force = action == "work3d" ? 1 : -1
	. = Remaster3DClick(value)
	remaster_gather_force = 0

// What a click on A orders, with the Gather switch: rock and trees are a plain move while it is off; a mountain top
// is dug down while it is on, by selected units already up there.
Player/proc/RemasterPointerKind(atom/A)
	. = RemasterClickKind(A)
	if(isturf(A) && (A.z == GROUND_LAYER || A.z == SKY_LAYER) && RemasterSlopeOn(locate(A.x, A.y, GROUND_LAYER))) return "Move"   // a ramp is a way; mined from the menu
	if(!RemasterGathering())
		if(. == "Chop" || . == "Mine") . = "Move"
	else if(. == "Move" && RemasterTopDigTurf(A) && RemasterSelectionOn(A.z)) . = "Dig down"

Player/proc/RemasterSelectionOn(level)
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.z == level) return 1
	return 0

// --- One block at a time, anywhere on the face -------------------------------------------------
// A rock column's blocks: a dense column's, less its two outside blocks once dug (remaster_dug, remaster_dug_top) and
// any dug off its top (remaster_topcut); a tunnel's roof (remaster_ceil up, remaster_roof of them); less the holes.

// Whether block k of T's column is there (0 the floor block).
proc/RemasterBlockThere(turf/T, k)
	if(!T || !isnum(k) || k < 0 || k > 15 || (T.remaster_holes & (1 << k))) return 0
	if(T.density)
		if(!RemasterIsMountain(T) || k >= RemasterBlocksAt(T)) return 0
		if(k == 0) return !T.remaster_dug
		if(k == 1) return !T.remaster_dug_top
		return 1
	if(T.remaster_roof <= 0) return 0
	var/c = T.remaster_ceil || 2
	return k >= c && k < c + T.remaster_roof

// How many blocks of T's column are still there.
proc/RemasterBlocksLeft(turf/T)
	. = 0
	for(var/k = 0, k < RemasterTopHeight(T), k++) if(RemasterBlockThere(T, k)) .++

// After a block comes out: a hole at the column's top makes it shorter, one at a tunnel's ceiling raises the ceiling,
// so the holes left are only ever between blocks. A tunnel's last roof block opens the mountain top over it to the sky.
proc/RemasterColumnSettle(turf/T)
	if(!T) return
	RmColumnSettleBlocks(T)
	RmLaidTidy(T)          // laid blocks no longer there: their marks go into "just gone" (Plans.dm, building rework L1)

proc/RmColumnSettleBlocks(turf/T)
	RmKeepHeight(T)        // the first change keeps its height with it (Breaking.dm)
	if(T.density)
		if(T.remaster_dug && RemasterIsMountain(T))   // a floor block out (from before one block of room was enough): a way in
			RemasterOpenColumn(T)
			return
		for(var/h = RemasterBlocksAt(T), h > 2 && (T.remaster_holes & (1 << (h - 1))), h = RemasterBlocksAt(T))
			T.remaster_holes &= ~(1 << (h - 1))
			T.remaster_topcut++
		// two blocks high with the upper one out: the floor block alone, a one-block rock (a ramp goes on it from the ground)
		if(RemasterBlocksAt(T) == 2 && T.remaster_dug_top && !T.remaster_dug)
			T.remaster_dug_top = 0
			T.remaster_topcut++
			T.HP = min(T.HP, initial(T.HP) / 2)
		return
	if(T.remaster_built_floor) RmBuiltFloorBack(T)   // a block laid on open ground dug out again: its ground comes back (Plans.dm)
	var/c = T.remaster_ceil || 2
	while(T.remaster_roof > 0 && (T.remaster_holes & (1 << c)))
		T.remaster_holes &= ~(1 << c)
		c++
		T.remaster_roof--
	while(T.remaster_roof > 0 && (T.remaster_holes & (1 << (c + T.remaster_roof - 1))))
		T.remaster_holes &= ~(1 << (c + T.remaster_roof - 1))
		T.remaster_roof--
	T.remaster_ceil = T.remaster_roof > 0 ? c : 0
	if(T.remaster_roof <= 0)
		T.remaster_holes = 0
		var/turf/U = locate(T.x, T.y, SKY_LAYER)
		if(U && U.icon_state == "Peak")
			RemasterDropOff(U, T)
			RemasterPeakOpen(U)

// The rock under a mountain top U is all gone: whoever stood up there comes down onto the ground under it (T), or the
// nearest open ground; what lay there falls with them.
proc/RemasterDropOff(turf/U, turf/T)
	for(var/obj/Items/I in U) I.loc = T
	for(var/mob/Monsters/M in U)
		var/turf/G = (T && !T.density && RemasterWalkable(T, M, T)) ? T : RemasterNearestOpen(T, M)
		if(!G) continue
		M.remaster_feet = null
		M.RemasterLevelStep(G)
		M.destination = null
		if(M.remaster_active) M.remaster_active.path = null

// A unit's reach (the user, 2026-10-24: "lets make it three"): the three blocks from its feet up, and two under its
// feet (the top of a column level with it, the one under that). On the ground or in a tunnel its feet are at 0: blocks
// 0 to 2. Higher blocks are worked from up on the mountain, a unit standing beside them high enough.
#define RM_REACH_UP 2
#define RM_REACH_DOWN 2

proc/RemasterReaches(feet, k)
	return k >= feet - RM_REACH_DOWN && k <= feet + RM_REACH_UP

// Up on a mountain: the tile beside (or on) the column under U where M can stand to work its block k, nearest M.
// Any place there will do, on a top or inside the mountain; the height chosen goes on M's order (spot, spot_feet), so
// its route ends standing at it (RemasterLevelPathDM).
proc/RemasterWorkSpot(mob/Monsters/M, turf/U, k, no_on = 0)
	var/datum/remaster_order/PO = M.remaster_active
	if(PO && PO.rm_spot && PO.rm_spot != U && max(abs(PO.rm_spot.x - U.x), abs(PO.rm_spot.y - U.y)) <= 1 && RemasterReaches(PO.rm_spot_f, k) && RemasterSpotAt(PO.rm_spot, PO.rm_spot_f))
		PO.spot = PO.rm_spot      // a plan's way there found this place, and a way to it (Plans.dm RmPlanAccess)
		PO.spot_feet = PO.rm_spot_f
		return PO.rm_spot
	var/turf/best
	var/best_f
	var/turf/stair
	var/stair_f
	var/here = RemasterFeetOf(M)
	var/Player/PW = M.rm_jz_id && istype(M.Owner, /Player) ? M.Owner : null   // a plan's worker
	var/list/WZ = PW ? PW.RmJz(M.rm_jz_id) : null
	var/no_down = WZ && WZ["stairs"] && M.z == SKY_LAYER   // up a building with its own stairs: never down a block to a place to work (a builder went down onto a lower house's wall top and had no way off: arena offset_room.dm, 10-30)
	for(var/turf/S in range(1, U))
		if(S.z != SKY_LAYER || (no_on && S == U)) continue
		if(S != M.loc && !RemasterWalkable(S, M, S)) continue
		for(var/list/s in RemasterSpotsAt(S))
			if(!RemasterReaches(s[2], k) || (S == U && s[2] <= k)) continue   // on its own column: only from under it
			if(PW && PW.RmPlanWantsAt(S.x, S.y, s[2]) && !(WZ && PW.RmPlanHoldFor(locate(S.x, S.y, GROUND_LAYER), s[2], WZ))) continue   // a plan's block still to go where its feet would be: not stood on to work (Plans.dm, phase 3), but one waiting for the blocks beside it (Sites.dm RmPlanHoldFor)
			if(no_down && s[2] < here) continue
			var/v = get_dist(M, S) * 4 + abs(s[2] - here)
			if(PW && ((s[2] == 1 && RmFirstStep(S)) || RmStairPassage(S)))   // a building's first step or a step with another over it: the way up and down (builders stopped on the stairs both ways and none passed, the real game 10-30); only when there is no other place
				if(!stair || v < get_dist(M, stair) * 4 + abs(stair_f - here))
					stair = S
					stair_f = s[2]
				continue
			if(!best || v < get_dist(M, best) * 4 + abs(best_f - here))
				best = S
				best_f = s[2]
	if(!best && stair)
		best = stair
		best_f = stair_f
	if(best && M.remaster_active)
		M.remaster_active.spot = best
		M.remaster_active.spot_feet = best_f
	return best

// Whether an order mines one block on its own (RemasterBlockTick) rather than the old way: a block above the two outside
// blocks of a standing column, any block worked from up on the mountain, or a roof block other than the one at the ceiling.
proc/RemasterOneBlock(datum/remaster_order/O)
	var/turf/A = O.target
	if(!isturf(A) || isnull(O.block)) return 0
	var/turf/T = A.z == SKY_LAYER ? locate(A.x, A.y, GROUND_LAYER) : A
	if(O.kind == "Mine") return A.z == SKY_LAYER || (T.density && O.block >= 2)
	if(O.kind == "Mine roof") return !T.density && T.remaster_roof > 0 && O.block != (T.remaster_ceil || 2)
	return 0

// Block k of T's column comes out: one of its two outside blocks (the column opens when both are out, a tunnel under
// what is left), or one higher up (a hole, or a shorter column: RemasterColumnSettle).
proc/RemasterTakeBlock(turf/T, k)
	remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1   // the world save keeps it (WorldSave.dm)
	if(T.density && k == 0)
		T.remaster_dug = 1
		RemasterOpenColumn(T)      // the floor block out: one block of room, a way in at the ground
	else if(T.density && k == 1)
		T.remaster_dug_top = 1
		T.HP = min(T.HP, initial(T.HP) / 2)   // one block left of the two outside ones: one block's work
		if(RemasterBlocksLeft(T) <= 0) RemasterOpenColumn(T)
	else T.remaster_holes |= 1 << k
	RemasterColumnSettle(T)
	RemasterFeetCheck(T)

// The floor block is out (one block of room is enough, "one block, everywhere"): the tile opens, a tunnel with what is
// left over it as its roof, its ceiling the lowest block still there.
proc/RemasterOpenColumn(turf/T)
	var/h = RemasterBlocksAt(T)
	var/c = 0
	var/gone = 0
	for(var/k = 1, k < h, k++)
		if(RemasterBlockThere(T, k))
			if(!c) c = k
		else if(c) gone |= 1 << k
	T.opacity = 0
	T.density = 0
	T.CanDigAt = 0
	T.Detailed = 0
	T.icon = 'Cave.dmi'
	T.icon_state = T.OIcon || "CaveFloor"
	T.remaster_dug = 0
	T.remaster_dug_top = 0
	T.remaster_ceil = c
	T.remaster_roof = c ? h - c : 0
	T.remaster_holes = gone
	rm_worked -= T
	RemasterColumnSettle(T)

// One tick of mining the block pointed at (O.block) out of a column: from the ground beside it (its three lowest
// blocks), or from up on the mountain (O.target the top over it), standing where the block is in reach. One block an order.
mob/Monsters/proc/RemasterBlockTick(datum/remaster_order/O)
	var/turf/A = O.target
	var/turf/T = A.z == SKY_LAYER ? locate(A.x, A.y, GROUND_LAYER) : A
	var/turf/U = locate(T.x, T.y, SKY_LAYER)
	var/k = O.block
	if(!RemasterBlockThere(T, k))
		RemasterFinishOrder("That block is already out; click another")
		return
	if(z != SKY_LAYER)
		if(!RemasterReaches(0, k))
			RemasterFinishOrder("Out of reach: a unit works three blocks up from where it stands; higher ones from up on the mountain")
			return
		if(get_dist(src, T) > 1)
			RemasterGiveUpOrApproach(O, T, 1)
			return
	else
		var/last = RemasterBlocksLeft(T) <= 1
		var/f = RemasterFeetOf(src)
		if(get_dist(src, U) > 1 || !RemasterReaches(f, k) || (loc == U && (last || f <= k)))
			var/turf/S = RemasterWorkSpot(src, U, k, last)
			if(!S)
				RemasterFinishOrder("Out of reach: nowhere beside it to stand with that block in reach (three blocks up from the feet)")
				return
			if(loc != S || f != O.spot_feet)
				RemasterApproach(O, S, 0)
				return
	if(RemasterBlocksLeft(T) <= 1 && U) for(var/mob/Monsters/X in U) if(X != src)
		RemasterBlock("Waiting: [X.name] is standing on the last block")
		O.last_progress = world.time
		return
	var/tool = RemasterPrepareTool("Mine")
	if(!tool) return
	remaster_blocked = null
	destination = null
	remaster_order_status = tool < 0 ? "Mining a block by hand" : "Mining a block"
	if(world.time < remaster_hand_at) return
	remaster_hand_at = world.time + max(8, Delay * 2)
	dir = get_dir(src, T) || dir
	if(T.remaster_blk_hp <= 0) T.remaster_blk_hp = RM_ROOF_LAYER_HP
	var/hp0 = T.remaster_blk_hp
	T.remaster_blk_hp -= RemasterWorkSkill(MineingSkill) / 4 * (tool < 0 ? 0.25 : 1)
	MineingSkill += 0.05
	T.remaster_dig_lvl = k
	RemasterWorkBlow(T, src, hp0)
	if(T.remaster_blk_hp > 0)
		RmStoneHalf(T, k, src, T.remaster_blk_hp, RM_ROOF_LAYER_HP)   // half-way: a stone (Yield.dm)
		return
	T.remaster_blk_hp = 0
	RemasterTakeBlock(T, k)
	MineingSkill += 0.1
	var/obj/Items/mined = RmStoneOut(T, k, src)   // its stone, as every natural block's (Yield.dm)
	var/got = mined ? RemasterCollect(mined) : 0
	if(got && istype(Owner, /Player)) Owner:RemasterMilestone("gather")
	RemasterFinishOrder(got ? "Mined the block and took its stone; click the rock for the next one" : mined ? "Mined the block; its stone is left here" : "Mined the block; click the rock for the next one")

// --- From the top: digging a mountain down ----------------------------------------------------

// The rock column under a mountain top U (the walkable peak on the sky layer), when it can be dug from above:
// natural rock or a tunnel's roof; not a carved run or its stairs.
proc/RemasterTopDigTurf(turf/U)
	if(!isturf(U) || U.z != SKY_LAYER || U.density || U.icon_state != "Peak" || findtext("[U.icon]", "Stairs.dmi")) return null
	var/turf/T = locate(U.x, U.y, GROUND_LAYER)
	if(!T || T.remaster_carve || T.remaster_carve_plan) return null
	if(T.density) return (T.CanDigAt && RemasterIsMountain(T) && RemasterBlocksAt(T) > 0) ? T : null
	return T.remaster_roof > 0 ? T : null

// The height of a column's top in blocks: its blocks, or a tunnel's ceiling and roof.
proc/RemasterTopHeight(turf/T)
	return T.density ? RemasterBlocksAt(T) : (T.remaster_ceil || 2) + T.remaster_roof

// Whether the next block off the top opens the tile to the sky.
proc/RemasterTopLast(turf/T)
	return RemasterBlocksLeft(T) <= 1

// A tile beside the mountain top U that M can stand on.
proc/RemasterStepOff(turf/U, mob/Monsters/M)
	for(var/turf/C in orange(1, U)) if(C.z == U.z && RemasterWalkable(C, M, C) && RemasterTilePlaces(C, list(M)) && (RemasterCanClimb(M) || RemasterStepHeights(U, C))) return C
	return null

// One tick of a Dig down order (target: the mountain top): beside it (or on it, but never for its last block), a blow
// at a time; one block an order, as from below.
mob/Monsters/proc/RemasterDigDownTick(datum/remaster_order/O)
	var/turf/U = O.target
	var/turf/T = RemasterTopDigTurf(U)
	if(!T)
		RemasterFinishOrder("Nothing left to dig there")
		return
	var/h = RemasterTopHeight(T)
	if(isnull(O.top0)) O.top0 = h
	else if(h != O.top0)
		RemasterFinishOrder("Someone dug that block first; click the top again for the next one")
		return
	if(get_dist(src, U) > 1 || !RemasterReaches(RemasterFeetOf(src), h - 1) || (loc == U && RemasterFeetOf(src) < h))
		var/turf/S = RemasterWorkSpot(src, U, h - 1)
		if(!S)
			RemasterFinishOrder("Out of reach: nowhere beside it to stand with its top block in reach")
			return
		if(loc != S || RemasterFeetOf(src) != O.spot_feet)
			RemasterApproach(O, S, 0)
			return
	if(RemasterTopLast(T))
		// the last block leaves a hole down to the ground: step off it first, and wait for anyone on it
		if(loc == U)
			if(!O.top_off || !RemasterWalkable(O.top_off, src, O.top_off)) O.top_off = RemasterStepOff(U, src)
			if(!O.top_off)
				RemasterFinishOrder("Couldn't dig the last block: nowhere to step off it")
				return
			remaster_order_status = "Stepping off the last block"
			RemasterApproach(O, O.top_off, 0)
			return
		for(var/mob/Monsters/X in U) if(X != src)
			RemasterBlock("Waiting: [X.name] is standing on the last block")
			O.last_progress = world.time
			return
	var/tool = RemasterPrepareTool("Mine")
	if(!tool) return
	remaster_blocked = null
	destination = null
	remaster_order_status = tool < 0 ? "Digging the top down by hand" : "Digging the top down"
	if(world.time < remaster_hand_at) return
	remaster_hand_at = world.time + max(8, Delay * 2)
	dir = get_dir(src, U) || dir
	if(!RemasterTopBlow(T, tool < 0)) RemasterFinishOrder(RemasterTopDigTurf(U) ? "Dug the top block off; click the top again for the next one" : "Dug down to the ground")

// One blow at the top block of T's column. 1 while it holds, 0 once it is off (its stone into the pack).
mob/Monsters/proc/RemasterTopBlow(turf/T, by_hand)
	if(T.remaster_top_hp <= 0) T.remaster_top_hp = RM_ROOF_LAYER_HP
	var/hp0 = T.remaster_top_hp
	var/k = RemasterTopHeight(T) - 1     // the top block, for its stone (Yield.dm)
	T.remaster_top_hp -= RemasterWorkSkill(MineingSkill) / 4 * (by_hand ? 0.25 : 1)
	MineingSkill += 0.05
	RemasterWorkBlow(T, src, hp0)
	if(T.remaster_top_hp > 0)
		RmStoneHalf(T, k, src, T.remaster_top_hp, RM_ROOF_LAYER_HP)
		return 1
	T.remaster_top_hp = 0
	RemasterTakeTopBlock(T)
	MineingSkill += 0.1
	var/obj/Items/ores/stone/S = RmStoneOut(T, k, src)
	if(S)
		var/got = RemasterCollect(S)
		if(got && istype(Owner, /Player)) Owner:RemasterMilestone("gather")
	return 0

// The top block of T's column comes off. A tunnel's roof thins; a rock column gets a block shorter, and an outside
// block already dug out under the new top goes with it (what is left settles as a shorter column). The last block
// leaves open ground, and the mountain top over it opens to the sky.
proc/RemasterTakeTopBlock(turf/T)
	remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1   // the world save keeps it (WorldSave.dm)
	var/turf/U = locate(T.x, T.y, SKY_LAYER)
	if(!T.density)
		T.remaster_roof = max(0, T.remaster_roof - 1)
		RemasterColumnSettle(T)
		return
	T.remaster_topcut++
	RemasterColumnSettle(T)
	for(var/k = RemasterBlocksAt(T), k > 0 && ((k == 2 && T.remaster_dug_top) || (k == 1 && T.remaster_dug)), k = RemasterBlocksAt(T))
		if(k == 2) T.remaster_dug_top = 0
		else T.remaster_dug = 0
		T.remaster_topcut++
	var/h = RemasterBlocksAt(T)
	if(h == 1) T.HP = min(T.HP, initial(T.HP) / 2)   // one block left: one block's work
	if(h > 0) return
	T.remaster_holes = 0
	T.remaster_dug = 0
	T.remaster_dug_top = 0
	T.opacity = 0
	T.density = 0
	T.CanDigAt = 0
	T.Detailed = 0
	T.icon = 'Cave.dmi'
	T.icon_state = T.OIcon || "CaveFloor"
	if(T.remaster_built_floor) RmBuiltFloorBack(T)   // a block laid on open ground (Plans.dm)
	rm_worked -= T
	if(U && U.icon_state == "Peak")
		RemasterDropOff(U, T)     // what lay or stood on top comes down to the ground
		RemasterPeakOpen(U)

// --- Walking on the blocks (the user, 2026-10-24) -------------------------------------------------
// Up on a mountain (the sky layer over the rock) a unit stands on a block with an open cell over it: one block of room
// ("one block, everywhere"), so on the top of the stack or inside it, in any gap dug at any height. Each unit up there
// keeps the height its feet are at (remaster_feet; unset: the top). It walks freely between places as high as each
// other, hops down one block where there is room to, and goes up one block only by a ramp carved into the block
// (remaster_slope), never two. Climbing gear, a climbing race or a flyer goes anywhere (RemasterCanClimb). From the
// ground, a ramp carved into the floor block of a rock is the way up (WallWalks.dm RemasterStairsTo); off a place a
// block up, a hop down to the ground beside it (RemasterHopSpot). Routes up there keep the heights: RemasterLevelPathDM.

turf/var/remaster_slope = 0       // a ramp carved into a block: the way it rises (NORTH...), 0 none (saved)
turf/var/remaster_slope_h = 0     // the height of the ramp's top: the ramp is block remaster_slope_h - 1 (saved)
mob/Monsters/var/tmp/remaster_feet          // up on a mountain: the height its feet are at, in blocks (null: the top)
mob/Monsters/var/tmp/turf/remaster_feet_on  // the tile that height was for (put somewhere else by other means: the top there)
mob/Monsters/var/tmp/list/remaster_plan_feet // its last route up there: turf -> the height it planned to stand at there

// T's ramp, while its block is there with room over it.
proc/RemasterSlopeOn(turf/T)
	if(!T || !T.remaster_slope) return 0
	var/k = T.remaster_slope_h - 1
	if(k < 0 || !RemasterBlockThere(T, k) || RemasterBlockThere(T, k + 1))
		T.remaster_slope = 0
		T.remaster_slope_h = 0
		return 0
	return T.remaster_slope

// The places to stand over U (the sky layer over a column): list(list(low, high), ...) from the bottom up, high the
// height the feet are at (a block there, an open cell over it), low a ramp's low edge (else high). Empty where U isn't
// over rock (a wall walk or a built floor has no heights: RemasterSpotsOrNull).
proc/RemasterSpotsAt(turf/U)
	. = list()
	if(!U || U.z != SKY_LAYER) return
	var/turf/T = locate(U.x, U.y, GROUND_LAYER)
	if(!T) return
	if(T.remaster_carve)       // a carved run's head (Mountains.dm): its landing on the top
		if(T.remaster_carve == T.remaster_carve_n && T.remaster_carve_top > 0) . += list(list(T.remaster_carve_top, T.remaster_carve_top))
		return
	if(!RemasterIsMountain(T)) return
	var/H = RemasterTopHeight(T)
	var/sl = RemasterSlopeOn(T) ? T.remaster_slope_h : -1
	for(var/f = 1, f <= H, f++)
		if(RemasterBlockThere(T, f - 1) && !RemasterBlockThere(T, f)) . += list(list(f == sl ? f - 1 : f, f))

// U's places, or null where there are no heights (not over rock).
proc/RemasterSpotsOrNull(turf/U)
	var/list/L = RemasterSpotsAt(U)
	return length(L) ? L : null

// Where a unit up on a mountain stands over U: list(low, high), its top place (null: not over rock).
proc/RemasterStandAt(turf/U)
	var/list/L = RemasterSpotsOrNull(U)
	return L ? L[length(L)] : null

// The place over U at height f (its high), or null.
proc/RemasterSpotAt(turf/U, f)
	for(var/list/s in RemasterSpotsAt(U)) if(s[2] == f) return s
	return null

// The place M stands at: list(low, high); on the ground or where there are no heights, list(0, 0) (or null up there).
mob/Monsters/proc/RemasterSpot()
	if(z != SKY_LAYER) return list(0, 0)
	var/list/L = RemasterSpotsOrNull(loc)
	if(!L) return null
	if(!isnull(remaster_feet) && remaster_feet_on && remaster_feet_on != loc) remaster_feet = null
	if(!isnull(remaster_feet))
		for(var/list/s in L) if(s[2] == remaster_feet) return s
		// its place is gone (mined out under it): the next one down, else the top
		for(var/i = length(L), i >= 1, i--)
			var/list/si = L[i]
			if(si[2] < remaster_feet)
				remaster_feet = si[2]
				remaster_feet_on = loc
				return si
	var/list/top = L[length(L)]
	remaster_feet = top[2]
	remaster_feet_on = loc
	return top

// The height M's feet are at, in blocks (0 on the ground).
proc/RemasterFeetOf(mob/Monsters/M)
	if(!M || M.z != SKY_LAYER) return 0
	var/list/s = M.RemasterSpot()
	return s ? s[2] : 0

// The height of the top of S's stack (its top place), for where no unit is in question.
proc/RemasterFeetAt(turf/S)
	if(!S || S.z != SKY_LAYER) return 0
	var/list/s = RemasterStandAt(S)
	return s ? s[2] : 0

// Whether a unit can step from place a over A to place b over B: up only as high as it stands (onto a ramp's low
// edge, or off a ramp's top), down one block at most, and only with room over the place it hops down into.
proc/RemasterSpotStep(turf/A, list/a, turf/B, list/b)
	if(!a || !b) return 1
	if(b[1] > a[2] || a[1] - b[2] > 1) return 0
	if(b[2] < a[2] && RemasterBlockThere(locate(B.x, B.y, GROUND_LAYER), a[2])) return 0   // no room to step off at its height
	return 1

// The place M would step to over B from where it stands (its planned one, else as high as it is, else down one,
// else up a ramp), or null when it can't; list(0, 0) where there are no heights.
mob/Monsters/proc/RemasterStepSpot(turf/B)
	var/list/b_all = RemasterSpotsOrNull(B)
	var/list/a = RemasterSpot()
	if(!b_all || !a) return b_all ? b_all[length(b_all)] : list(0, 0)
	if(RemasterCanClimb(src))
		var/want = remaster_plan_feet ? remaster_plan_feet[B] : null
		for(var/list/s in b_all) if(s[2] == want) return s
		return b_all[length(b_all)]
	var/want = remaster_plan_feet ? remaster_plan_feet[B] : null
	if(!isnull(want)) for(var/list/s in b_all) if(s[2] == want && RemasterSpotStep(loc, a, B, s)) return s
	for(var/d in list(0, -1, 1)) for(var/list/s in b_all) if(s[2] == a[2] + d && RemasterSpotStep(loc, a, B, s)) return s
	return null

// Whether there is any step from a place over A to one over B (for searches with no unit's place in hand).
proc/RemasterStepHeights(turf/A, turf/B)
	var/list/AL = RemasterSpotsOrNull(A)
	var/list/BL = RemasterSpotsOrNull(B)
	if(!AL || !BL) return 1
	for(var/list/a in AL) for(var/list/b in BL) if(RemasterSpotStep(A, a, B, b)) return 1
	return 0

// The units up over T's column after its blocks changed: each comes down to the place under its feet if its own is
// gone (RemasterSpot), and the view hears of it.
proc/RemasterFeetCheck(turf/T)
	var/turf/U = locate(T.x, T.y, SKY_LAYER)
	if(!U) return
	for(var/mob/Monsters/M in U)
		var/f = M.remaster_feet
		M.RemasterSpot()
		if(M.remaster_feet != f && istype(M.Owner, /Player) && M.Owner:remaster_3d) M.Owner:Remaster3DMovesPushNow()

// The route search up on a mountain, by place: the same search as Orders.dm RemasterOrderPathDM, each node a tile and
// the height stood at there, the steps RemasterSpotStep allows. The heights it plans go to M.remaster_plan_feet; the
// goal's height, when an order names one (a click on a dug-out floor: O.feet), is where it has to end.
proc/RemasterLevelPathDM(mob/Monsters/M, turf/goal, reach, turf/bounds = null, radius = 0, partial = 0, list/side = null)
	var/turf/start = M.loc
	var/list/s0 = M.RemasterSpot()
	if(!s0) return RemasterOrderPathDM(M, goal, reach, bounds, radius, partial, side, 1)
	var/datum/remaster_order/O = M.remaster_active
	var/goal_f = O ? (O.target == goal ? O.feet : (O.spot == goal ? O.spot_feet : null)) : null
	var/k0 = "[start.x],[start.y],[s0[2]]"
	var/list/node = list()         // key -> list(turf, spot)
	var/list/cost = list()
	var/list/parent = list()
	var/list/closed = list()
	var/list/fs = list()
	var/list/open = list(k0)
	node[k0] = list(start, s0)
	cost[k0] = 0
	fs[k0] = get_dist(start, goal)
	var/closest = k0
	var/closest_d = get_dist(start, goal)
	rm_path_partial = 0
	for(var/tries = 0, tries < 768 && open.len, tries++)
		var/ck
		var/best = 1000000
		for(var/k in open)
			if(fs[k] < best)
				best = fs[k]
				ck = k
		open -= ck
		var/list/cn = node[ck]
		var/turf/current = cn[1]
		var/list/cs = cn[2]
		var/d = get_dist(current, goal)
		if(d <= reach && (isnull(goal_f) || current != goal || cs[2] == goal_f))
			var/list/path = list()
			var/list/plan = list()
			while(ck != k0)
				var/list/pn = node[ck]
				var/list/ps = pn[2]
				path.Insert(1, pn[1])
				plan[pn[1]] = ps[2]
				ck = parent[ck]
			M.remaster_plan_feet = plan
			return path
		if(d < closest_d || (d == closest_d && cost[ck] < cost[closest]))
			closest = ck
			closest_d = d
		closed[ck] = 1
		for(var/dd in list(NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST))
			var/turf/next = get_step(current, dd)
			if(!next) continue
			if(bounds && (next.z != bounds.z || get_dist(next, bounds) > radius)) continue
			var/w = RemasterWalkable(next, M, goal, side)
			if(!w) continue
			var/list/NL = RemasterSpotsOrNull(next)
			if(!NL) NL = list(list(0, 0))
			for(var/list/ns in NL)
				if(!RemasterSpotStep(current, cs, next, ns)) continue
				if(dd & (dd - 1))      // a diagonal step: never round a corner of rock at that height
					var/turf/o1 = get_step(current, dd & (NORTH | SOUTH))
					var/turf/o2 = get_step(current, dd & (EAST | WEST))
					if(!o1 || !o2 || !RemasterSpotAt(o1, ns[2]) && RemasterSpotsOrNull(o1) || !RemasterSpotAt(o2, ns[2]) && RemasterSpotsOrNull(o2)) continue
				var/nk = "[next.x],[next.y],[ns[2]]"
				if(closed[nk]) continue
				var/fresh = isnull(cost[nk])
				if(fresh || cost[nk] > cost[ck] + 1)
					node[nk] = list(next, ns)
					cost[nk] = cost[ck] + 1
					fs[nk] = cost[nk] + get_dist(next, goal) + (isnull(goal_f) ? 0 : abs(ns[2] - goal_f))
					parent[nk] = ck
					if(fresh) open += nk
	rm_path_partial = (open.len && closest != k0) ? 1 : 2
	if(!partial || closest == k0) return null
	var/list/part = list()
	var/list/plan = list()
	var/ck = closest
	while(ck != k0)
		var/list/pn = node[ck]
		var/list/ps = pn[2]
		part.Insert(1, pn[1])
		plan[pn[1]] = ps[2]
		ck = parent[ck]
	M.remaster_plan_feet = plan
	return part

// A hop down off a mountain: list(the top to stand on, the ground beside it) for M up there to reach A on the ground,
// from a top a block high (or a ramp at the ground) nearest M plus nearest A; null if there is none near.
proc/RemasterHopSpot(mob/Monsters/M, turf/A)
	if(!M || !A || M.z != SKY_LAYER || A.z != GROUND_LAYER) return null
	var/list/best
	var/score = 1000000
	var/list/side = RmSide(M)   // its own side's units on a step don't shut it (Clip.dm; three builders on a building's first step held everyone upstairs: phase 3)
	for(var/turf/H in range(12, M))
		var/list/HL = RemasterSpotsOrNull(H)
		var/list/s = HL ? HL[1] : null
		if(!s || s[1] > 1 || (H != M.loc && !RemasterWalkable(H, M, H, side))) continue
		if(RemasterBlockThere(locate(H.x, H.y, GROUND_LAYER), 0) == 0) continue   // open at the ground under it: a tunnel's roof, not a step down
		var/slope = RemasterSlopeOn(locate(H.x, H.y, GROUND_LAYER))
		for(var/d in (slope ? list(turn(slope, 180)) : list(NORTH, SOUTH, EAST, WEST)))   // off a ramp: down its slope
			var/turf/G = get_step(locate(H.x, H.y, GROUND_LAYER), d)
			if(!G || G.density || !RemasterWalkable(G, M, G, side)) continue
			var/v = get_dist(M, H) + get_dist(G, A)
			if(v < score)
				score = v
				best = list(H, G)
	return best

proc/RemasterHopOrder(Player/P, mob/Monsters/M, turf/A)
	var/list/spot = RemasterHopSpot(M, A)
	if(!spot) return null
	var/datum/remaster_order/C = new
	C.issuer = P
	C.kind = "Hop"
	C.target = spot[1]
	C.climb_z = GROUND_LAYER
	C.scale_foot = spot[2]
	var/list/HL = RemasterSpotsOrNull(spot[1])
	var/list/low = HL ? HL[1] : null
	C.feet = low ? low[2] : null    // its lowest place, the one a block up
	return C

// One tick of a hop down: onto the top it hops from, then down beside it.
mob/Monsters/proc/RemasterHopTick(datum/remaster_order/O)
	if(z == GROUND_LAYER)
		RemasterFinishOrder("Hopped down")
		return
	var/turf/G = O.scale_foot
	if(!G || G.density || !RemasterWalkable(G, src, G, RmSide(src)))
		RemasterFinishOrder("Skipped: nowhere to hop down to")
		return
	if(loc != O.target || (!isnull(O.feet) && RemasterFeetOf(src) != O.feet))
		RemasterApproach(O, O.target, 0)
		return
	dir = get_dir(O.target, G) || dir
	remaster_feet = null
	RemasterLevelStep(G)
	destination = null
	RemasterFinishOrder("Hopped down")
	if(length(remaster_orders)) RemasterOrderTick()   // straight on, no pause at the foot

// A step onto the other level (up a ramp at the ground, a hop down): timed like a step, so the 3D view glides it
// (Orders.dm Move keeps the same rhythm), and pushed at once.
mob/Monsters/proc/RemasterLevelStep(turf/T)
	var/gap = world.time - remaster_stepped_at
	loc = T
	remaster_stepped_at = world.time
	remaster_step_gap = (gap > 0 && gap <= 3 * max(1, Delay)) ? gap : max(1, RemasterStepDelay())
	var/Player/P = Owner
	if(istype(P) && P.remaster_3d) P.Remaster3DMovesPushNow()

// --- Carving a ramp ----------------------------------------------------------------------------
// The menu's "Carve into a ramp": a block with room over it (the column's top block, or k, one inside the mountain with
// a dug-out place over it) becomes a slope rising away from the unit that carves it, which stands a block lower beside it
// (on the ground for the floor block, else up on the mountain). Free; the stone carved off is half a block's.
Player/proc/RemasterCarveRamp(turf/T, queued = 0, k = null)
	if(T && T.z == SKY_LAYER) T = locate(T.x, T.y, GROUND_LAYER)
	if(!T || T.z != GROUND_LAYER || !RemasterIsMountain(T) || T.remaster_carve || T.remaster_carve_plan)
		RemasterNotice("A ramp is carved into a block of a mountain with room over it, from a block lower beside it.")
		return 0
	if(RemasterSlopeOn(T))
		RemasterNotice("That block is a ramp already.")
		return 0
	if(isnull(k) || !RemasterBlockThere(T, k) || RemasterBlockThere(T, k + 1)) k = RemasterTopHeight(T) - 1
	if(!RemasterBlockThere(T, k) || RemasterBlockThere(T, k + 1))
		RemasterNotice("A ramp needs a block with room over it.")
		return 0
	var/turf/target = k > 0 ? locate(T.x, T.y, SKY_LAYER) : T      // carved from a block lower: up there, or the ground
	remaster_click_block = k
	var/n = RemasterOrder(target, queued, "Carve ramp")
	remaster_click_block = null
	if(n) RemasterNotice("Carving a ramp into the top block: units step up it, one block. Carved from the side it rises away from.")
	return n

// One tick of carving a ramp (target: the rock, or the mountain top over it).
mob/Monsters/proc/RemasterRampTick(datum/remaster_order/O)
	var/turf/A = O.target
	var/turf/T = locate(A.x, A.y, GROUND_LAYER)
	var/h = isnull(O.block) ? RemasterTopHeight(T) : O.block + 1     // the ramp's top: the block carved is h - 1
	if(!T || !RemasterIsMountain(T) || RemasterSlopeOn(T) || !RemasterBlockThere(T, h - 1) || RemasterBlockThere(T, h))
		RemasterFinishOrder(T && RemasterSlopeOn(T) ? "It is a ramp already" : "Skipped: no block with room over it to carve there")
		return
	var/d = get_dir(A, src)
	if(get_dist(src, A) > 1 || loc == A || !(d in list(NORTH, SOUTH, EAST, WEST)))
		// beside it, square on (a ramp rises straight away from its carver)
		var/turf/best
		for(var/dd in list(NORTH, SOUTH, EAST, WEST))
			var/turf/S = get_step(A, dd)
			if(!S || !RemasterWalkable(S, src, S)) continue
			if(z == SKY_LAYER && !RemasterSpotAt(S, h - 1)) continue
			if(!best || get_dist(src, S) < get_dist(src, best)) best = S
		if(!best)
			RemasterFinishOrder("Couldn't carve the ramp: no open spot a block lower beside it")
			return
		O.spot = best
		O.spot_feet = h - 1
		if(loc != best || (z == SKY_LAYER && RemasterFeetOf(src) != h - 1))
			RemasterApproach(O, best, 0)
			return
		d = get_dir(A, src)
	if((z == SKY_LAYER ? RemasterFeetOf(src) : 0) != h - 1)
		RemasterFinishOrder("A ramp goes up one block: carve it from a block lower beside it")
		return
	var/tool = RemasterPrepareTool("Mine")
	if(!tool) return
	remaster_blocked = null
	destination = null
	remaster_order_status = "Carving a ramp"
	if(world.time < remaster_hand_at) return
	remaster_hand_at = world.time + max(8, Delay * 2)
	dir = get_dir(src, A) || dir
	if(T.remaster_blk_hp <= 0) T.remaster_blk_hp = RM_ROOF_LAYER_HP
	var/hp0 = T.remaster_blk_hp
	T.remaster_blk_hp -= RemasterWorkSkill(MineingSkill) / 4 * (tool < 0 ? 0.25 : 1)
	MineingSkill += 0.05
	T.remaster_dig_lvl = h - 1
	RemasterWorkBlow(T, src, hp0)
	if(T.remaster_blk_hp > 0) return
	T.remaster_blk_hp = 0
	RmKeepHeight(T)        // (Breaking.dm)
	T.remaster_slope = turn(d, 180)
	T.remaster_slope_h = h
	rm_ways_ver++   // a ramp made: units held for a way up look again at once (Attack.dm, B)
	remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1
	if(!(RmLaidMask(T) & RmStoneBit(h - 1)) && prob(50)) new /obj/Items/ores/stone(loc)   // a laid block's carving gives nothing: it gives its 1 when dug (Plans.dm)
	RemasterFinishOrder("Carved a ramp: units step up it")
