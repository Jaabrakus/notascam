// Finite commands are owned by a unit, never by the current selection.
// Effects still use WalkTo/Bump and the original inventory procedures.
datum/remaster_order
	var/Player/issuer
	var/atom/target
	var/kind
	var/last_x
	var/last_y
	var/last_hp
	var/last_progress
	var/list/path
	var/list/harvest_items = list()
	var/phase = "Work"
	var/automatic = 0
	var/climb_z = 0          // "Climb": the level the stairs (target) lead to (WallWalks.dm)
	var/partial = 0          // the route is 1: part of a long one, 2: as close as it gets (no way through yet)
	var/repath_at = 0
	var/stuck_since = 0      // no way through since then
	var/stalls = 0           // work that made no progress
	var/by_hand = 0          // no tool: works by hand, slowly
	var/retreat = 0          // a move given while fighting: auto-defense leaves it alone (Defense.dm)
	var/dug0                 // "Mine"/"Mine roof": the rock's state when the order started, so two units
	var/roof0                // sent to one tile take one block between them, not one each
	var/block                // "Mine" on a rock column: the block pointed at, 0 the floor block or 1 the one above (null: the floor block first)

mob/Monsters
	var/tmp/list/remaster_orders
	var/tmp/datum/remaster_order/remaster_active
	var/tmp/remaster_order_status = "Idle"
	var/tmp/remaster_paused = 0
	var/tmp/remaster_blocked
	var/tmp/remaster_wait_for_resume = 0
	var/remaster_auto_unload = 0
	var/remaster_role_paused = 0

Player
	var/tmp/remaster_multi = 0
	var/tmp/remaster_queue = 0
	var/tmp/remaster_notice = ""    // no toast at login (playtest: it told a player with no people yet to select a unit)
	var/list/remaster_milestones = list()
	var/tmp/list/remaster_markers

Player/proc/RemasterNotice(message)
	remaster_notice = message

Player/proc/RemasterMilestone(id)
	if(!remaster_milestones) remaster_milestones = list()
	remaster_milestones[id] = 1

mob/Monsters/proc/RemasterHasOrder()
	return remaster_active || length(remaster_orders) || remaster_delivery

// mob/Monsters/Move: this file's part is step RmChainMove_Orders in Code/Remastered/Chains/Move.dm

mob/Monsters/var/tmp/remaster_stepped_at = -1000
mob/Monsters/var/tmp/remaster_step_gap = 0   // ticks its last step took (the 3D glide's length)
mob/Monsters/var/tmp/remaster_push_step = 0

mob/Monsters/proc/RemasterSuspendControllers()
	// Keep designations and guard rules, but suspend their running controllers.
	Dig = 0
	DigTarget = null
	HomeLoc = null
	RemasterStopWork()
	destination = null
	SavedDest = null
	Target = null
	BowOn = 0

mob/Monsters/proc/RemasterManualHandoff(Player/P = Owner)
	// A committed original action borrows this actor until explicit Resume.
	// Keep its task objects, job configuration and production attempts intact.
	if(!istype(P) || Owner != P || !(src in P.UnitList)) return 0
	if(P.remaster_preset_choices || P.remaster_auto_use) return 1 // station work or a use-it-yourself rule keeps the unit's order
	RemasterCareInterrupt()
	RemasterCancelDefense()
	if(RemasterHasOrder()) RemasterPauseOrders(1)
	else RemasterSuspendControllers()
	remaster_role_paused = 1
	return 1

mob/Monsters/proc/RemasterCancelOrders()
	remaster_fish_spot = null
	if(remaster_care) RemasterCareInterrupt()
	RemasterCancelDefense()
	remaster_active = null
	remaster_orders = list()
	remaster_delivery = null
	remaster_paused = 0
	remaster_blocked = null
	remaster_wait_for_resume = 0
	destination = null
	SavedDest = null
	Target = null
	remaster_order_status = "Idle"

mob/Monsters/proc/RemasterStopOrders()
	remaster_attack = null
	RemasterCancelOrders()
	RemasterSuspendControllers()
	remaster_role_paused = 1
	remaster_order_status = "Stopped"

mob/Monsters/proc/RemasterPauseOrders(paused)
	RemasterCancelDefense()
	remaster_paused = !!paused
	RemasterSuspendControllers()
	remaster_role_paused = !!paused
	remaster_wait_for_resume = 0
	remaster_blocked = null
	var/Player/P = Owner
	if(remaster_active)
		if(!paused && remaster_active.kind == "Drop off" && istype(P) && P.RemasterStockpile()) remaster_active.target = P.RemasterStockpile()
		remaster_active.last_progress = world.time
		remaster_active.path = null
	if(remaster_delivery)
		if(!paused && istype(P) && P.RemasterStockpile()) remaster_delivery.target = P.RemasterStockpile()
		remaster_delivery.last_progress = world.time
		remaster_delivery.path = null
	remaster_order_status = paused ? "Paused" : "Resuming"

mob/Monsters/proc/RemasterRemoveOrder(index)
	if(!isnum(index) || index != round(index) || index < 1 || index > length(remaster_orders)) return 0
	remaster_orders.Cut(index, index + 1)
	return 1

proc/RemasterResourceKind(atom/A)
	if(istype(A, /obj/Items/woods/wood)) return "wood"
	if(istype(A, /obj/Items/ores/stone)) return "stone"
	if(istype(A, /obj/Items/ores)) return "ores"
	if(istype(A, /obj/Items/gems)) return "gems"
	if(istype(A, /obj/Items/Ingots)) return "ingots"
	if(istype(A, /obj/Items/Food)) return "food"
	if(istype(A, /obj/Items/Skin)) return "skin"
	if(istype(A, /obj/Items/Seeds)) return "seeds"
	if(istype(A, /obj/Items/Bones)) return "bones"
	return null

proc/RemasterOrderKind(atom/A)
	// Anything loose on the ground is picked up. Planted things and placed fixtures
	// (beds, furniture, signs, traps) stay put: a click walks there.
	if(istype(A, /obj/Items) && isturf(A.loc))
		if(!isnull(A.suffix) || istype(A, /obj/Items/Furniture) || istype(A, /obj/Items/Shafts) || istype(A, /obj/Items/Traps)) return "Move"
		return "Pick up"
	if(isturf(A))
		if(A.Tree && A.density) return "Chop"
		if(A.CanDigAt && A.density) return "Mine"
		return "Move"     // walls, water, chasms: the nearest open tile beside them
	return null

// 1: ready (tool in hand, or none needed); 0: fetching one from the stockpile;
// -1: none anywhere, so the unit works by hand (RemasterHandWork).
mob/Monsters/proc/RemasterPrepareTool(kind)
	var/tool = RemasterToolFor(kind)
	if(!tool) return 1
	// The best tool this unit carries and has the skill for (tool tiers).
	var/obj/Items/best = RemasterBestTool(tool, src)
	var/obj/Items/held = RemasterHeldTool(tool)
	if(HoldingWeapon == tool && (!best || held == best || RemasterToolScore(held, tool) >= RemasterToolScore(best, tool))) return 1
	if(best && EquipItem(best) && HoldingWeapon == tool) return 1
	if(HoldingWeapon == tool) return 1
	// A hand that can't take one up (its right arm lost or useless) works by hand: off to fetch tools it can't hold, it only
	// filled its bag with them (polish 10-26: a one-armed woodcutter carried off all 4 axes on the stockpile).
	if(!HasRightArm || !CanUseRightArm) return -1
	// None carried: fetch the best one from the stockpile.
	var/Player/P = Owner
	var/obj/Items/stock
	if(istype(P))
		var/best_d = 1#INF
		for(var/turf/S in P.RemasterStores()) if(S.z == z)
			var/obj/Items/C = RemasterBestTool(tool, S, P)
			if(C && (!stock || RemasterToolScore(C, tool) > RemasterToolScore(stock, tool) || (RemasterToolScore(C, tool) == RemasterToolScore(stock, tool) && get_dist(C, src) < best_d)))
				stock = C
				best_d = get_dist(C, src)
	if(stock)
		if(get_dist(src, stock) <= 1)
			if(PickUpItem(stock) && EquipItem(stock) && HoldingWeapon == tool)
				remaster_order_status = "Took \an [lowertext(tool)] from the stockpile"
				return 1
		else
			destination = stock.loc
			remaster_order_status = "Fetching \an [lowertext(tool)] from the stockpile"
			if(remaster_active) remaster_active.last_progress = world.time
			return 0
	return -1

// How good a tool is for this unit: its tier speed if skilled enough, else basic.
mob/Monsters/proc/RemasterToolScore(obj/Items/I, tool)
	if(!I) return 0
	var/list/T = RemasterToolTier(I)
	if(!T) return 1
	var/skill = tool == "Axe" ? WoodCuttingSkill : MineingSkill
	return round(skill) >= T[3] ? T[4] : 1

// The best tool of this kind carried by src (where = src) or lying on/next to a tile.
mob/Monsters/proc/RemasterBestTool(tool, atom/where, Player/P)
	var/obj/Items/best
	var/best_score = 0
	var/list/pool = list()
	if(where == src)
		for(var/obj/Items/E in src)
			if(E.suffix == "(Carrying)") pool += E
	else
		for(var/obj/Items/E in range(1, where))
			if(isturf(E.loc) && (!P || P.RemasterMayCollect(E))) pool += E
	for(var/obj/Items/E in pool)
		// Dangerous cursed gear requires an explicit equipment interaction.
		if(E.ItemType != tool || E.icon == 'DemonicItems.dmi') continue
		var/score = RemasterToolScore(E, tool)
		if(score > best_score)
			best = E
			best_score = score
	return best

mob/Monsters/proc/RemasterBlock(reason, manual = 0)
	destination = null
	Target = null
	if(remaster_blocked != reason && istype(Owner, /Player)) Owner:RemasterLog("[name]: [reason]", "problem", src)
	remaster_blocked = reason
	remaster_wait_for_resume = manual
	remaster_order_status = reason
	if(remaster_active) remaster_active.path = null

// A big group's orders are given over a few ticks (formations, 10-25; the user on a 30,000-unit move at 1.7 s: "how
// can we optimize this"): up to RM_GIVE_NOW units all in the click's tick, as always; more, as many as RM_GIVE_MS of it
// gives, then RM_GIVE_LATER_MS of each tick after it until all have theirs (about 10 us a unit: 5,000 in the click's tick
// cost 100 ms of giving, 30,000 half a second). The group's slots and the notice come once all are given. A unit a newer
// order took meanwhile (rm_given_serial), or that died or changed hands, is left out.
#define RM_GIVE_NOW 200
#define RM_GIVE_MS 8
#define RM_GIVE_LATER_MS 25
Player/var/tmp/rm_order_serial = 0
mob/Monsters/var/tmp/rm_given_serial = 0
Player/proc/RemasterOrder(atom/A, queued = 0, kind = null)
	FmProf(null)
	var/plan_from = world.tick_usage   // the plan before the giving (the group, its formation), counted in the ledger, never held
	var/plan_at = world.time
	if(isobj(A) && !istype(A, /obj/Items) && isturf(A.loc)) A = A.loc   // other things on the ground: their tile
	if(!kind) kind = RemasterClickKind(A)     // "Mine roof" comes from the 3D menu (Mountains.dm); flyers fly over rock (Flying.dm)
	if(!A || !A.z || !kind || !length(Selected))
		RemasterNotice("Select a unit and a clear destination or resource.")
		return 0
	if(kind == "Move" && !isturf(A)) A = A.loc
	if(kind != "Move" && A.Owner && A.Owner != src)
		RemasterNotice("That resource belongs to someone else.")
		return 0
	if((kind in list("Chop", "Mine", "Mine roof", "Dig down", "Carve ramp")) && !RemasterMayWork(RemasterTurf(A))) return 0
	if((kind in rm_built_dig_kinds) && RmBuiltHeld(src, RmBuiltTurf(RemasterTurf(A))))   // another realm's built wall (BuiltWalls.dm)
		RemasterNotice(RM_BUILT_HELD_SAY)
		return 0
	// A ramp up on a mountain (Gather.dm): the click means walking onto it, up there, wherever on it the click was.
	if(kind == "Move" && isturf(A) && A.z == GROUND_LAYER && A.density && RemasterSlopeOn(A) && RemasterTopHeight(A) > 1) A = locate(A.x, A.y, SKY_LAYER)
	// Stairs: the click means the other end of them.
	if(kind == "Move" && RemasterStairsTo(A))
		var/turf/L = locate(A.x, A.y, RemasterStairsTo(A))
		if(L) A = L
	// Out over open sky on the Sky level (Flying.dm RmOpenSky): the flyers go, the walkers stay where they are. The order
	// is planned with the flyers as the selection (the selection itself is back before any unit is given its order).
	var/list/rm_sky_all
	if(kind == "Move" && RmSkyOpenFor(src, A))
		var/list/fly = list()
		var/walkers = 0
		for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0)
			if(M.Flying) fly += M
			else walkers++
		if(!length(fly))
			RemasterNotice("Only flyers can go out over open sky.")
			return 0
		if(walkers)
			RemasterNotice("[walkers == 1 ? "1 unit stays" : "[walkers] units stay"]: only flyers can go out over open sky.")
			rm_sky_all = Selected
			Selected = fly
	// A stale dying selection must not take an order: the engine's filter (Native.dm, the same), else DM's.
	var/list/group = rm_native_plan ? rm_plan_group(Selected, src, UnitList, /mob/Monsters, null) : null
	if(!islist(group) || rm_plan_verify)
		var/list/GD = list()
		for(var/mob/Monsters/M in Selected)
			if(M.Owner == src && (M in UnitList) && !M.Wagon && M.HP > 0 && !M.GoingToDie) GD += M
		if(islist(group)) RmPlanCheck("the order's units", group, GD)
		group = GD
	var/count = 0
	// A group sent to one spot forms up around it: each unit gets its own open
	// tile in the formation's shape (Formations.dm), instead of all crowding one tile.
	// Flyers sent onto rock all go on top of it, not to open ground round it.
	var/list/slots = kind == "Move" && !(A.density && RemasterOnlyFlyers()) ? RemasterFormation(A, queued) : null
	var/datum/remaster_group/G = slots ? remaster_forming : null   // this order's group, kept while it's given over ticks
	// Units on another level go by the nearest stairs, then spread along the far side.
	var/list/climbers = kind == "Move" && !slots ? RemasterLevelSlots(A) : null
	if(rm_sky_all) Selected = rm_sky_all
	// Several units sent to one loose item take the matching items lying with it.
	var/list/items = kind == "Pick up" ? RemasterPickupShare(A, group) : null
	var/list/undo = list()
	FmProf("o form")
	var/my = ++rm_order_serial
	var/spread = length(group) > RM_GIVE_NOW
	var/slice = world.tick_usage
	if(plan_at == world.time) RmTickCharge((slice - plan_from) * world.tick_lag)
	var/budget = RM_GIVE_MS
	var/datum/rm_give/give   // under way over ticks: the track holds back for its share (the one tick ledger, Spread.dm)
	if(spread)
		give = new
		give.at = world.time
		rm_give_live += give
	for(var/mob/Monsters/M in group)
		if(spread)
			if((world.tick_usage - slice) * world.tick_lag >= budget || (rm_tick_cap && rm_tick_ledger && RmTickUsed() + (world.tick_usage - slice) * world.tick_lag >= rm_tick_cap))   // this tick's share given: the rest next tick
				RmTickCharge((world.tick_usage - slice) * world.tick_lag)
				if(count && remaster_3d) Remaster3DMovesPushSoon()
				sleep(1)
				give.at = world.time
				slice = world.tick_usage
				budget = RM_GIVE_LATER_MS
			if(Rm3DGone(M) || M.rm_given_serial > my || M.Owner != src || !M.loc || M.HP <= 0 || M.GoingToDie) continue   // died while it waited: the ref isn't null in OpenDream (polish-errors)
		// Sent away while fighting or under attack: a retreat, not to be turned back.
		var/retreat = kind == "Move" && (M.remaster_defense || M.remaster_attack || (M.remaster_attacked_at && world.time - M.remaster_attacked_at < 100))
		M.RemasterCareInterrupt()
		M.RemasterWake()
		var/atom/target = (slots && slots[M]) ? slots[M] : (climbers && climbers[M]) ? climbers[M] : (items && items[M]) ? items[M] : A
		// One unit sent onto a tile it can't stand on goes beside it.
		if(kind == "Move" && target == A && M.z == A.z && !RemasterWalkable(A, M, A)) target = RemasterNearestOpen(A, M) || A
		// a block of a mountain (Gather.dm): from up there, worked from the top beside it; from the ground, three blocks up
		if(kind == "Mine" && isturf(A) && A.z == GROUND_LAYER && A.density && RemasterIsMountain(A))
			if(M.z == SKY_LAYER) target = locate(A.x, A.y, SKY_LAYER)
			else if(!isnull(remaster_click_block) && !RemasterReaches(0, remaster_click_block))
				RemasterNotice("Out of reach: a unit works three blocks up from where it stands. Higher blocks are mined from up on the mountain beside them.")
				continue
		if(kind == "Mine roof" && isturf(A) && M.z != SKY_LAYER && !RemasterReaches(0, isnull(remaster_click_block) ? (A:remaster_ceil || 2) : remaster_click_block))
			RemasterNotice("Out of reach: a unit works three blocks up from where it stands.")
			continue
		var/turf/stairs
		var/datum/remaster_order/scale
		if(M.z != target.z)
			stairs = RemasterStairsTowards(M, RemasterTurf(target))
			// off a mountain: a hop down a block, when that is nearer than the stairs (Gather.dm)
			var/datum/remaster_order/hop = RemasterHopOrder(src, M, RemasterTurf(target))
			if(hop && stairs && get_dist(M, stairs) < get_dist(M, hop.target)) hop = null
			if(hop)
				stairs = null
				scale = hop
			// no stairs: climbing gear (or a climbing race) goes up or down a cliff face (Mountains.dm)
			if(!stairs && !scale && RemasterCanClimb(M)) scale = RemasterScaleOrder(src, M, RemasterTurf(target))
			if(!stairs && !scale)
				if(kind == "Mine" || kind == "Chop") RemasterNotice("That spot is up on top of the rock, out of reach. Click the rock face at ground level instead.")   // playtest: the forge hint baffled a new player
				else RemasterNotice(RemasterCanClimb(M) ? "No cliff or stairs nearby lead to that level." : "No ramp or stairs nearby lead to that level: carve a ramp into a block (right-click it); climbing gear (made at a forge) would get up or down a cliff.")
				continue
		if(queued && length(M.remaster_orders) >= 32)
			RemasterNotice("Queue full (32 pending tasks).")
			continue
		// the same spot or slot again (a re-click): the route it is on goes with the new order, so spam-clicking a group
		// costs no search per unit per click (owner call D, 10-27); RemasterStartOrder puts it back
		var/datum/remaster_order/O0 = M.remaster_active
		var/list/kept = (!queued && kind == "Move" && O0 && O0.kind == "Move" && O0.target == target && O0.issuer == src && M.z == target.z && length(O0.path) && get_dist(M, O0.path[1]) <= 1) ? list(O0.path, O0.partial, O0.repath_at, O0.feet) : null
		if(!queued)
			M.RemasterCancelOrders()
			M.remaster_patrol = null      // a direct order ends a patrol (Patrol.dm)
		if(!M.remaster_defense && !(queued && M.remaster_paused)) M.RemasterSuspendControllers()
		if(!M.remaster_orders) M.remaster_orders = list()
		M.remaster_attack = null
		if(scale) M.remaster_orders += scale
		if(stairs)
			var/datum/remaster_order/C = new
			C.issuer = src
			C.target = stairs
			C.kind = "Climb"
			C.climb_z = target.z
			C.retreat = retreat
			M.remaster_orders += C
		var/datum/remaster_order/O = new
		O.issuer = src
		O.target = target
		O.kind = kind
		O.retreat = retreat
		if(kind == "Mine" || kind == "Mine roof" || kind == "Carve ramp") O.block = remaster_click_block   // the block the 3D click pointed at (View3D.dm, Gather.dm)
		if(kind == "Move" && isturf(target) && target.z == SKY_LAYER && target == A) O.feet = remaster_click_level   // a dug-out floor up there (Gather.dm)
		if(slots && slots[M] == target) O.group = G   // marches with the group (Formations.dm)
		if(kept && kept[4] == O.feet) O.rm_kept = kept   // the route it is on (above)
		M.remaster_orders += O
		M.remaster_push_step = 1
		undo += list(list(M, "\ref[O]", O.kind, "\ref[O.target]"))
		count++
		M.rm_given_serial = my
		FmProf("o give")
		if(queued || M.remaster_active) M.RemasterOrderTick()   // queued or busy: as before
		else RmFirstTick(M, O, count, 1)   // a big group's first steps over a few ticks (Formations.dm); its go is in this loop's ledger time
		FmProf("o first tick")
	RmTickCharge((world.tick_usage - slice) * world.tick_lag)   // the giving in this tick (the one tick ledger, Spread.dm)
	if(give) rm_give_live -= give
	slice = world.tick_usage
	if(slots) RemasterGroupFinish(G)   // who took the group's move; its slots to the page (Formations.dm)
	RmTickCharge((world.tick_usage - slice) * world.tick_lag)   // and that (its slots' send: 10-20 ms at 2,000), counted, never held
	FmProf("o finish")
	if(count)
		if(remaster_3d) Remaster3DMovesPushSoon()   // the first step on screen a tick after the order (View3D.dm)
		RemasterUndoPush(list("type"="order", "pairs"=undo))
		RemasterNotice("[queued ? "Added: " : "Started: "][kind]. Deselecting keeps the task running.")
		RemasterMilestone("order")
	return count

// The open tile nearest T (then nearest M) that M can stand on, within 6 tiles.
proc/RemasterNearestOpen(turf/T, mob/Monsters/M)
	var/turf/best
	var/best_d = 1#INF
	for(var/turf/C in range(6, T))
		if(!RemasterTilePlaces(C, list(M)) || !RemasterWalkable(C, M, C)) continue
		var/d = get_dist(C, T) * 100 + get_dist(C, M)
		if(d < best_d)
			best = C
			best_d = d
	return best

// Units sent to pick up one item: unit -> item. The unit nearest it takes it; the others
// take the same kind of item lying on or beside its tile, then share the clicked one.
proc/RemasterPickupShare(obj/Items/A, list/group)
	if(length(group) < 2) return null
	var/list/order = group.Copy()
	for(var/a = 1, a <= length(order), a++)
		for(var/b = a + 1, b <= length(order), b++)
			if(get_dist(order[b], A) < get_dist(order[a], A)) order.Swap(a, b)
	var/list/pile = list()
	for(var/obj/Items/I in range(1, A.loc))
		if(I != A && isturf(I.loc) && isnull(I.suffix) && (!I.Owner || I.Owner == A.Owner) && I.type == A.type) pile += I
	var/list/out = list()
	out[order[1]] = A
	for(var/i = 2, i <= length(order), i++)
		out[order[i]] = length(pile) ? pile[1] : A
		if(length(pile)) pile.Cut(1, 2)
	return out

// Formation tiles for the selected units moving to T: unit -> turf.
proc/RemasterOpenTile(turf/T, list/group)
	return RemasterTilePlaces(T, group) > 0

// How many of the group can still stand on T: one, or two on a wall-walk (WallWalks.dm).
proc/RemasterTilePlaces(turf/T, list/group)
	if(!T || T.density || (T.icon_state in list("Sky", "Chasm")) && !(RmOpenSky(T) && RmAllFly(group))) return 0   // open sky holds flyers (Flying.dm)
	if(T.icon == 'Stairs.dmi') return 0
	var/taken = 0
	for(var/atom/movable/X in T) if(X.density && !(X in group))
		if(!T.remaster_wallwalk || !istype(X, /mob/Monsters)) return 0
		taken++
	return max(0, (T.remaster_wallwalk ? 2 : 1) - taken)

// Targets for the selected units on another level than T: open places near T on its
// level (walk tiles twice), nearest first, nearest unit choosing first.
Player/proc/RemasterLevelSlots(turf/T)
	var/list/group = list()
	for(var/mob/Monsters/M in Selected)
		if(M.Owner == src && (M in UnitList) && !M.Wagon && M.HP > 0 && !M.GoingToDie && M.z != T.z) group += M
	if(!length(group)) return null
	var/list/free = list()
	for(var/turf/C in range(6, T)) for(var/k = RemasterTilePlaces(C, group), k > 0, k--) free += C
	var/list/out = list()
	for(var/mob/Monsters/M in group)
		var/turf/best
		var/best_d = 1#INF
		for(var/turf/C in free)
			var/d = get_dist(C, T) * 10 + abs(C.x - T.x) + abs(C.y - T.y)
			if(d < best_d)
				best = C
				best_d = d
		if(!best) break
		out[M] = best
		free -= best
	return out

// Formation shape for group moves: keep (the group's own shape), line, column or box.
Player/var/remaster_formation = "keep"

// The slots for a group move to T (Formations.dm RemasterGroupForm): unit -> turf. queued: from their last queued spots.
Player/proc/RemasterFormation(turf/T, queued = 0)
	return RemasterGroupForm(T, queued)

datum/remaster_order/var/tmp/list/rm_kept   // a re-click on the same spot or slot: the route it was on (RemasterOrder), once
mob/Monsters/proc/RemasterStartOrder(datum/remaster_order/O)
	if((O.kind == "Mine" || O.kind == "Mine roof") && isturf(O.target))
		O.dug0 = O.target:remaster_dug + 2 * O.target:remaster_dug_top
		O.roof0 = O.target:remaster_roof
	O.last_x = x
	O.last_y = y
	O.last_hp = O.target ? RemasterWorkProgress(O.target) : null
	O.last_progress = world.time
	O.path = null
	O.stuck_since = 0
	O.repath_at = 0
	if(O.rm_kept)
		O.path = O.rm_kept[1]
		O.partial = O.rm_kept[2]
		O.repath_at = O.rm_kept[3]
		O.rm_kept = null

mob/Monsters/proc/RemasterOrderTick()
	if(remaster_defense) return
	var/Player/P = Owner
	if(!istype(P))
		if(RemasterHasOrder() || remaster_delivery) RemasterStopOrders()
		return
	if(remaster_paused || remaster_wait_for_resume) return
	if(!remaster_active && length(remaster_orders))
		remaster_active = remaster_orders[1]
		remaster_orders.Cut(1, 2)
		RemasterStartOrder(remaster_active)
	if(remaster_active && remaster_active.issuer != P)
		RemasterStopOrders()
		return
	if(!remaster_active && !remaster_delivery) return
	if(remaster_care)
		// Looking after themselves (Care.dm): tasks are kept and resume afterwards.
		remaster_order_status = "[remaster_care_status]; carries on after"
		if(remaster_active) remaster_active.last_progress = world.time
		if(remaster_delivery) remaster_delivery.last_progress = world.time
		return
	if(GoingToDie || HP <= 0)
		RemasterStopOrders()
		return
	// Being asleep (an order wakes it: RemasterOrder), knocked out, stunned or trapped holds
	// tasks up; a unit that can't walk crawls (RemasterCrawlTick) and a blind one feels its way.
	if(!isturf(loc) || Fainted || Stunned || Sleeping || InHole)
		RemasterBlock(Sleeping ? "Asleep; carries on after waking" : InHole ? "Trapped; carries on once free" : Fainted ? "Knocked out; carries on after" : Stunned ? "Stunned; carries on after" : "Can't move; carries on after")
		if(remaster_active) remaster_active.last_progress = world.time
		if(remaster_delivery) remaster_delivery.last_progress = world.time
		return
	if(remaster_delivery)
		RemasterDeliveryTick(P)
		return
	var/datum/remaster_order/O = remaster_active
	var/atom/A = O.target
	if(O.kind == "Drop off")
		RemasterDepositTick(O, P)
		return
	if(!A || !A.z)
		RemasterFinishOrder("Skipped: target is gone")
		return
	if(O.kind == "Scale")
		RemasterScaleTick(O)    // up or down a cliff face (Mountains.dm)
		return
	if(O.kind == "Hop")
		RemasterHopTick(O)      // down a block off a mountain (Gather.dm)
		return
	if(O.kind == "Climb")
		// Walk up beside the stairs, then step onto their landing on the other level.
		// Set directly rather than by walking onto them: the original stairs move "usr"
		// (turf/grounds/Entered), which for an order may not be this unit, and the
		// landing's own stairs would otherwise send it straight back.
		if(z == O.climb_z)
			RemasterFinishOrder("Climbed the stairs")
		else if(z != A.z) RemasterBlock("Stairs are on another level")
		else if(A.density && RemasterSlopeOn(A) && loc != get_step(A, turn(RemasterSlopeOn(A), 180)) && RemasterWalkable(get_step(A, turn(RemasterSlopeOn(A), 180)), src))
			RemasterApproach(O, get_step(A, turn(RemasterSlopeOn(A), 180)), 0)   // a ramp at the ground: walked onto from its foot (Gather.dm)
		else if(get_dist(src, A) <= 1)
			var/turf/land = locate(A.x, A.y, O.climb_z)
			var/ramp = A.density && RemasterSlopeOn(A)
			if(land)
				if(ramp)
					remaster_feet = A:remaster_slope_h   // on the ramp's top, under any rock over it (Gather.dm)
					remaster_feet_on = land
					RemasterLevelStep(land)              // up a ramp: a step like any other, and straight on
				else
					loc = land
					remaster_feet = null
				destination = null
			RemasterFinishOrder(ramp ? "Up the ramp" : "Climbed the stairs")
			if(ramp && length(remaster_orders)) RemasterOrderTick()
		else if(!RemasterApproach(O, A, 1) && O.stuck_since && world.time - O.stuck_since > 100)
			RemasterStairsElsewhere(O)   // no way to these stairs for 10 s: others to that level, if there are any (WallWalks.dm)
		return
	if(z != A.z)
		// It changed level since the order: take the stairs back first (or hop down off a mountain, Gather.dm).
		if(O.nostairs_at && world.time < O.nostairs_at + rm_retry_gap && O.nostairs_ver == rm_ways_ver && RmRetryOn())   // B (Attack.dm): none under a second ago, none made since
			if(rm_prof) RmProfAdd("retry/no stairs held", 0)
			RemasterBlock("No stairs nearby lead to that level")
			return
		var/turf/S = RemasterStairsTowards(src, RemasterTurf(A))
		var/datum/remaster_order/HO = RemasterHopOrder(P, src, RemasterTurf(A))
		if(HO && (!S || get_dist(src, HO.target) <= get_dist(src, S)))
			if(!remaster_orders) remaster_orders = list()
			remaster_orders.Insert(1, O)
			remaster_active = HO
			RemasterStartOrder(HO)
			return
		if(!S && RemasterCanClimb(src))
			var/datum/remaster_order/SC = RemasterScaleOrder(P, src, RemasterTurf(A))
			if(SC)
				if(!remaster_orders) remaster_orders = list()
				remaster_orders.Insert(1, O)
				remaster_active = SC
				RemasterStartOrder(SC)
				return
		if(!S)
			if(O.rm_plan)      // a plan's order: the plan works out a way there, or another block (Plans.dm)
				RemasterFinishOrder("Couldn't get there: no stairs or ramp to that level")
				return
			O.nostairs_at = world.time   // B (Attack.dm): looked for again once a second, or at once when stairs or a ramp are made
			O.nostairs_ver = rm_ways_ver
			RemasterBlock("No stairs nearby lead to that level")
			return
		O.nostairs_at = 0
		var/datum/remaster_order/C = new
		C.issuer = P
		C.target = S
		C.kind = "Climb"
		C.climb_z = A.z
		C.automatic = O.automatic
		if(!remaster_orders) remaster_orders = list()
		remaster_orders.Insert(1, O)
		remaster_active = C
		RemasterStartOrder(C)
		return
	if(O.kind != "Move" && A.Owner && A.Owner != P)
		RemasterFinishOrder("Skipped: ownership changed")
		return
	if(O.kind == "Move")
		if(loc == A && (isnull(O.feet) || RemasterFeetOf(src) == O.feet))   // a dug-out floor up there: at its height (Gather.dm)
			RemasterFinishOrder("Arrived")
		else if(!RemasterApproach(O, A, 0) && O.partial == 2 && O.stuck_since && world.time - O.stuck_since > 300)
			RemasterFinishOrder("Got as close as it could")
		return
	if((O.kind in rm_built_dig_kinds) && isturf(A) && RmBuiltHeld(P, RmBuiltTurf(A)))   // another realm's built wall (BuiltWalls.dm)
		RemasterFinishOrder(RM_BUILT_HELD_SAY)
		return
	if(O.kind == "Dig down")
		RemasterDigDownTick(O)     // a mountain's top, from up there (Gather.dm)
		return
	if(O.kind == "Carve ramp")
		RemasterRampTick(O)        // a block carved into a ramp (Gather.dm)
		return
	if(O.kind == "Site")
		RmSiteTick(O)              // to or from a construction site's pile (Sites.dm)
		return
	if(O.kind == "Lay block")
		RmPlanLayTick(O)           // a block of a build plan (Plans.dm)
		return
	if(RemasterOneBlock(O))
		RemasterBlockTick(O)       // the one block pointed at, anywhere on the face (Gather.dm)
		return
	if(O.kind == "Mine roof")
		// from inside the tunnel or beside it, a blow at a time (Mountains.dm)
		if(A.density || A:remaster_roof <= 0)
			RemasterFinishOrder(A.density ? "Skipped: it filled in" : "Roof mined out")
			return
		if(get_dist(src, A) > 1)
			RemasterGiveUpOrApproach(O, A, 1)
			return
		if(!isnull(O.roof0) && A:remaster_roof != O.roof0)
			RemasterFinishOrder("Someone dug that block first; click the rock again for the next one")
			return
		var/tool = RemasterPrepareTool("Mine")
		if(!tool) return
		remaster_blocked = null
		destination = null
		remaster_order_status = tool < 0 ? "Mining the roof by hand" : "Mining the roof"
		if(world.time < remaster_hand_at) return
		remaster_hand_at = world.time + max(8, Delay * 2)
		dir = get_dir(src, A) || dir
		if(!RemasterRoofBlow(A, tool < 0)) RemasterFinishOrder(A:remaster_roof > 0 ? "Mined the block above" : "Mined out: open to the sky")
		return
	if(O.kind == "Pick up")
		if(!isturf(A.loc) || A.suffix)
			RemasterFinishOrder(A.loc == src ? "Collected" : "Skipped: already collected")
			return
		if(get_dist(src, A) > 1)
			RemasterGiveUpOrApproach(O, A, 1)
			return
		if(RemasterCollect(A, !O.automatic)) RemasterFinishOrder("Collected [A.name]")
		return
	if(O.kind == "Chop" || O.kind == "Mine")
		var/tended = RemasterTendReached(A, src)     // worked down to its tending mark: left to grow back (Yield.dm)
		if(!A.density || tended)
			O.phase = "Collecting"
			for(var/obj/Items/I in O.harvest_items.Copy())
				// A job's own digging lifts only what the stores take. Ore, gems and bones the drop-off doesn't take went in
				// the bag and never came out (no delivery takes them), so a miner's bag filled until every block's stone was
				// left lying ("pack full, the rest is left here"); now they stay where they fell, as the zone's own pickup
				// and the haulers leave them (polish-loops, 2026-10-26). A player's own order lifts everything, as before.
				if(!I || !isturf(I.loc) || I.suffix || (I.Owner && I.Owner != P) || (O.automatic && istype(P) && (!P.RemasterStockAccepts(I) || RmShunsSilver(I))))
					O.harvest_items -= I
					continue
				if(get_dist(src, I) > 1)
					// a piece it can't get to after half a minute is left
					if(!RemasterApproach(O, I, 1) && O.stuck_since && world.time - O.stuck_since > 300)
						O.harvest_items -= I
						O.stuck_since = 0
					return
				var/got = RemasterCollect(I)
				if(got) O.harvest_items -= I
				else if(isnull(got))
					// Pack full and no unloading: the rest stays where it fell.
					P.RemasterMilestone("gather")
					RemasterFinishOrder("Gathered; pack full, the rest is left here")
				return
			P.RemasterMilestone("gather")
			RemasterFinishOrder(tended ? (A.Tree ? "Gathered half: tended trees are left to grow back (Tend living: off in Work fells them)" : "Gathered; the vein is tended, the rest of its ore stays in the rock") : "Gathered")
			return
		var/tool = RemasterPrepareTool(O.kind)
		if(!tool) return
		if(tool < 0) O.by_hand = 1
		if(!RemasterLandForWork()) return
		if(get_dist(src, A) > 1)
			RemasterGiveUpOrApproach(O, A, 1)
			return
		if(O.last_hp != RemasterWorkProgress(A) || x != O.last_x || y != O.last_y)   // a holding vein counts its ore (Yield.dm)
			O.last_progress = world.time
			O.last_hp = RemasterWorkProgress(A)
			O.last_x = x
			O.last_y = y
		if(world.time - O.last_progress > max(100, Delay * 5))
			// No progress: try by hand, then give up rather than stand there for ever.
			O.stalls++
			O.by_hand = 1
			O.last_progress = world.time
			if(O.stalls >= 4)
				RemasterFinishOrder("Couldn't [lowertext(O.kind)] [A.name]: no progress")
				return
		remaster_blocked = null
		remaster_order_status = O.by_hand ? "[O.kind] by hand: [A.name]" : "[O.kind]: [A.name]"
		destination = A
		if(O.by_hand) RemasterHandWork(A, O.kind)

// 1: picked up; 0: not yet (unloading, landing); null: pack full and nothing to unload.
// An item you clicked (asked) is always made room for: a trip to the stockpile, or
// the unit puts down carried resources here.
mob/Monsters/proc/RemasterCollect(obj/Items/I, asked = 0)
	if(!RemasterLandForWork()) return 0
	if(I.weight + weight > weightmax)
		var/Player/P = Owner
		var/turf/S = istype(P) ? P.RemasterStockpile() : null
		var/spare = (S && !S.density && S.z == z) ? RemasterDeliveryWeight(P) : 0
		if((remaster_auto_unload || asked) && spare > 0 && weight + I.weight - spare <= weightmax)
			RemasterBeginDelivery(I)
			return 0
		if(!asked) return null
		if(!RemasterMakeRoom(I.weight))
			RemasterBlock("Too heavy to carry")
			return 0
	if(PickUpItem(I))
		remaster_blocked = null
		return 1
	RemasterBlock(RemasterPickupReason(I))
	return 0

// Put down carried resources (heaviest first, never gear or tools) until `need` fits.
mob/Monsters/proc/RemasterMakeRoom(need)
	var/list/goods = list()
	var/spare = 0
	for(var/obj/Items/I in src) if(I.suffix == "(Carrying)" && !I.EquipmentType() && RemasterResourceKind(I))
		goods += I
		spare += I.weight
	if(weight + need - spare > weightmax) return 0
	var/n = 0
	while(weight + need > weightmax && length(goods))
		var/obj/Items/H = goods[1]
		for(var/obj/Items/G in goods) if(G.weight > H.weight) H = G
		goods -= H
		if(DropItem(H)) n++
	if(n && istype(Owner, /Player)) Owner:RemasterLog("[name] put down [n] item\s to make room", "work", src)
	return weight + need <= weightmax

// mob/Monsters/Bump: this file's part is step RmChainBump_Orders in Code/Remastered/Chains/Bump.dm

mob/Monsters/proc/RemasterPickupReason(atom/A)
	if(Flying || IsMist) return "Can't land here"
	if(A.Silver && (Race == "Vampire" || SubRace == "Werewolf")) return "Can't carry silver"
	if(weight + A.weight > weightmax) return "Bag too full to carry it"
	return "Can't pick that up here"

mob/Monsters/proc/RemasterFinishOrder(message)
	// A job's own task (the job board, a role, a board order, a plan, a patrol leg: automatic) ends quietly: the unit's
	// card and its job's row say how it went. Each one toasted "<name>: Gathered ..." to the player, a line every few
	// seconds from a village at work, over the news the player needed (polish-loops, 2026-10-26).
	var/quiet = remaster_active && remaster_active.automatic
	remaster_active = null
	destination = null
	Target = null
	remaster_blocked = null
	remaster_wait_for_resume = 0
	remaster_order_status = message
	if(istype(Owner, /Player) && !quiet) Owner:RemasterNotice("[name]: [message]")

// Bounded path search uses clear tiles only. Harvest collision is issued only
// when adjacent to the actual work target, never to an intervening structure.
// Mirrored in the engine (engine/native/RmWalk.cs): change both together.
// With side (RmSide, Clip.dm) it is 2 where the only units in the way are of the mover's side: gone through, never
// stopped on. The engine's copy answers (rm_walk, Native.dm: 44,000 a second in a 1000 v 1000); this is the rule.
proc/RemasterWalkable(turf/T, mob/Monsters/M, turf/goal = null, list/side = null)
	if(rm_walk_native && !rm_nav_count)
		var/w = rm_walk(T, M, goal, side, rm_path_pass, rm_own_doors)
		if(!isnull(w))
			if(rm_walk_verify) RmWalkVerify(T, M, goal, side, w)
			return w
	return RemasterWalkableDM(T, M, goal, side)

proc/RemasterWalkableDM(turf/T, mob/Monsters/M, turf/goal = null, list/side = null)
	if(rm_nav_count && T) RmNavWalkCount(T)   // counted (Native.dm, navigation plan N0)
	if(RmFliesOver(M, T)) return 1   // a flyer goes over water, walls, rock and units (Flying.dm)
	if(!T || (T.density && !(rm_swim_on && RmSwimWater(T) && RmSwims(M)))) return 0   // deep water: swimmers go in (Swim.dm)
	if(T.icon == 'Stairs.dmi' && T != goal) return 0
	if(T.remaster_wallwalk) return RemasterWalkRoom(T, M)
	// Non-dense does not always mean safe ground. Entered applies the original
	// falling/death effects, so autonomous routes must go around these gaps.
	if(M.density && !M.Flying && (T.icon_state in list("Chasm", "Sky"))) return 0
	if(T.icon_state == "GoodGrass" && (M.Infects || M.Undead || M.Unholy || M.Race == "Svartalfar" || M.Race == "Demon")) return 0
	. = 1
	for(var/atom/movable/A in T)
		if(!A.density)
			if(rm_own_doors && istype(A, /obj/Items/Furniture/Doors) && RmOwnDoor(A, M)) . = 2   // its owner's door, open: through, never stopped on (Doors.dm)
			continue
		if(A == M || (istype(A, /obj/RmBeastFoot) && A:owner == M) || (rm_path_pass && rm_path_pass[A])) continue   // its own feet (Beasts.dm); a group's walking members (Formations.dm)
		if(rm_own_doors && istype(A, /obj/Items/Furniture/Doors) && RmOwnDoor(A, M))   // its owner's unlocked door, shut: through (it opens as the unit steps at it), never stopped on (Doors.dm)
			. = 2
			continue
		if(!RmSideUnit(A, side)) return 0
		. = 2

// With partial, a goal it can't reach (or too far for one search) still gives the route
// to the nearest point found; rm_path_partial says which: 0 the whole way, 1 part of a
// long way, 2 as close as it gets (no way through).
var/rm_path_partial = 0
// The DM route search. RemasterOrderPath (Native.dm) calls the engine's copy of it (engine/native/RmPath.cs, RmWalk.cs:
// change those with this and RemasterWalkable) or this one. With side (RmSide, Clip.dm) it goes through tiles holding
// only units of the mover's side but never ends on one, partial routes included.
proc/RemasterOrderPathDM(mob/Monsters/M, turf/goal, reach, turf/bounds = null, radius = 0, partial = 0, list/side = null, flat = 0)
	var/turf/start = M.loc
	if(!flat && start && start.z == SKY_LAYER && !RemasterCanClimb(M)) return RemasterLevelPathDM(M, goal, reach, bounds, radius, partial, side)   // up on a mountain: by place and height (Gather.dm)
	var/list/open = list(start)
	var/list/cost = list()
	var/list/parent = list()
	var/list/closed = list()       // turf -> 1
	var/list/fs = list()           // turf -> cost so far + distance left
	var/list/occ = list()          // turf -> 1: units of its side on it
	var/turf/closest = start
	var/closest_d = get_dist(start, goal)
	cost[start] = 0
	fs[start] = closest_d
	rm_path_partial = 0
	for(var/tries = 0, tries < 512 && open.len, tries++)
		var/turf/current
		var/best = 1000000
		for(var/turf/T in open)
			var/score = fs[T]
			if(score < best)
				best = score
				current = T
		open -= current
		var/d = get_dist(current, goal)
		if(d <= reach && !occ[current])
			var/list/path = list()
			while(current != start)
				path.Insert(1, current)
				current = parent[current]
			return path
		if(!occ[current] && (d < closest_d || (d == closest_d && cost[current] < cost[closest])))
			closest = current
			closest_d = d
		closed[current] = 1
		for(var/d in list(NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST))
			var/turf/next = get_step(current, d)
			if(!next) continue
			if(bounds && (next.z != bounds.z || get_dist(next, bounds) > radius)) continue
			if(closed[next]) continue
			var/w = RemasterWalkable(next, M, goal, side)
			if(!w) continue
			if(w == 2) occ[next] = 1
			var/sc = rm_swim_on ? RmSwimCost(next, M) : 1   // deep water swum: rm_swim_cost steps (Swim.dm)
			var/fresh = isnull(cost[next])     // not seen yet, so not in open (a seen one stays in open until closed)
			if(fresh || cost[next] > cost[current] + sc)
				cost[next] = cost[current] + sc
				fs[next] = cost[next] + get_dist(next, goal)
				parent[next] = current
				if(fresh) open += next
	// Nothing nearer than where it stands: as close as it gets.
	rm_path_partial = (open.len && closest != start) ? 1 : 2
	if(!partial || closest == start) return null
	var/list/part = list()
	while(closest != start)
		part.Insert(1, closest)
		closest = parent[closest]
	return part

mob/Monsters/proc/RemasterApproach(datum/remaster_order/O, atom/A, reach)
	var/turf/goal = isturf(A) ? A : A.loc
	if(!isturf(goal))
		RemasterBlock("Target is no longer on the ground")
		return 0
	if(O.group && O.kind == "Move") return RemasterGroupApproach(O, goal)   // with its group (Formations.dm)
	if(x != O.last_x || y != O.last_y)
		O.last_x = x
		O.last_y = y
		O.last_progress = world.time
	if(world.time - O.last_progress > max(100, Delay * 5))
		// Stuck: look for another way (never wait for Resume).
		O.path = null
		O.last_progress = world.time
	while(length(O.path) && O.path[1] == loc) O.path.Cut(1, 2)
	var/held = 0
	if(!length(O.path) || !RemasterStepOpen(O.path, src, goal))
		// a search that found no way is retried every 3 s, not every tick
		if(length(O.path) || !O.stuck_since || world.time >= O.repath_at)
			held = RmOrderRetry(O, goal)   // B (Attack.dm): its last search failed under a second ago, its next step shut: it waits
			if(!held)
				if(rm_nav_count) rm_path_who = RmNavOrderWho(O, length(O.path) ? "step blocked" : O.stuck_since ? "no way, again" : "no route")
				// further than it sees, with fog of war: from what its player knows (the route map, Native.dm); else the search,
				// and the route map's whole way where the search found only part of it
				if(!(RmRouteByKnowing(goal) && RmRouteInstead(O, goal, reach)))
					O.path = RemasterOrderPath(src, goal, reach, partial = 1)
					O.partial = rm_path_partial
					if(O.partial && !length(O.path) && rm_route && !RmReachNo(src, goal, reach)) RmRouteInstead(O, goal, reach)
				O.repath_at = world.time + 30
				RmOrderSearched(O, goal)
	else if(O.partial == 2 && world.time >= O.repath_at)
		// Heading for the nearest point: keep looking for the real way through.
		if(rm_nav_count) rm_path_who = RmNavOrderWho(O, "nearest point, look again")
		O.path = RemasterOrderPath(src, goal, reach, partial = 1) || O.path
		O.partial = rm_path_partial
		if(O.partial && !length(O.path) && rm_route && !RmReachNo(src, goal, reach)) RmRouteInstead(O, goal, reach)   // the route map's whole way (Native.dm)
		O.repath_at = world.time + 30
		RmOrderSearched(O, goal)
	if(held == 2)
		destination = null
		return 1
	if(!length(O.path))
		if(!O.stuck_since) O.stuck_since = world.time
		if(O.rm_plan && world.time - O.stuck_since > 150)    // a plan's order: the plan finds another block, or a way there (Plans.dm)
			RemasterFinishOrder("Couldn't get there: no way through")
			return 0
		RemasterBlock("No way through yet; trying again")
		O.last_progress = world.time
		return 0
	if(O.partial != 2) O.stuck_since = 0
	destination = O.path[1]
	remaster_blocked = null
	remaster_order_status = O.partial == 2 ? "[O.kind]: no way through yet, going as close as it can" : "[O.kind]: travelling"
	return 1

// Approach a work target; after a minute with no way to it, the order is dropped.
mob/Monsters/proc/RemasterGiveUpOrApproach(datum/remaster_order/O, atom/A, reach)
	if(!RemasterApproach(O, A, reach) && O.stuck_since && world.time - O.stuck_since > 600)
		RemasterFinishOrder("Gave up: no way to reach [A.name]")
		return 0
	return 1

// --- Doing what it was told --------------------------------------------------------

mob/Monsters/proc/RemasterWake()
	if(!Sleeping) return
	Sleeping = 0
	SavedDest = null
	RebuildOverlays()

// Flyers land and mist turns solid to work or pick things up.
mob/Monsters/proc/RemasterLandForWork()
	if(Flying)
		var/keep = weightmax
		Fly(0, "Land")
		if(isnull(weightmax)) weightmax = keep     // Fly restores Old, set only by a real take-off
	if(IsMist && !density && isturf(loc) && !loc.density) VampireMistForm()
	if(Flying || IsMist)
		RemasterBlock("Can't land here")
		return 0
	return 1

// No axe or pickaxe: a blow by hand every 2 s, about a quarter of the speed. The race's own
// chop/dig code (Bump) does the work, holding the tool for that one blow.
#define RM_HAND_EVERY 20
mob/Monsters/var/tmp/remaster_hand_at = 0
mob/Monsters/proc/RemasterHandWork(atom/A, kind)
	if(world.time < remaster_hand_at || get_dist(src, A) > 1) return
	remaster_hand_at = world.time + RM_HAND_EVERY
	var/weapon = HoldingWeapon
	HoldingWeapon = kind == "Chop" ? "Axe" : "Pickaxe"
	destination = A
	Bump(A)
	HoldingWeapon = weapon

// A unit that can't walk (legs lost or crippled) crawls where it's told: a tile every 2 s.
#define RM_CRAWL_EVERY 20
mob/Monsters/var/tmp/remaster_crawl_at = 0
mob/Monsters/proc/RemasterCrawlTick()
	if(CanWalk || !destination || !isturf(loc) || Fainted || Stunned || Sleeping || InHole || HP <= 0) return
	if(!RemasterHasOrder() && !remaster_attack) return
	if(world.time < remaster_crawl_at) return
	remaster_crawl_at = world.time + max(RM_CRAWL_EVERY, Delay * 4)
	if(remaster_order_status && !findtext(remaster_order_status, "crawling")) remaster_order_status += " (crawling)"
	step_towards(src, destination)
	if(loc == destination) destination = null

// With spread (the track's runs, Spread.dm) it goes on into the next tick between units once a tick's share is used.
// A unit with nothing on (no defence, attack, fishing spot, task, delivery or destination) skips the defence, attack,
// order and crawl ticks, which would each return at once for it (server cost, 2026-10-24: 5,000 units standing, 36 ms a
// pass before); the friend's-tile check runs for every unit as before. A tick that comes to do something for a unit with
// none of these (a defence scan for fights nearby, say) must add its reason to this test.
#define RM_ORDERS_IDLE_RUN 16   // idle units between spread pauses (a unit with something on pauses after itself)
Player/proc/RemasterOrdersTick(spread = 0)
	RemasterProgressTick()
	RemasterCaravanTick()
	RemasterClaimTick()
	RemasterMoodsTick()
	var/idle = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src)
		if(M.remaster_defense || M.remaster_attack || M.remaster_fish_spot || M.remaster_active || length(M.remaster_orders) || M.remaster_delivery || M.destination)
			M.RemasterDefenseTick()
			if(!Rm3DGone(M) && !M.RemasterAttackTick() && !Rm3DGone(M) && !(M.remaster_fish_spot && !M.remaster_defense && M.RemasterFishTick())) M.RemasterOrderTick()   // fishing: Fishing.dm
			if(!Rm3DGone(M)) M.RemasterCrawlTick()
			idle = RM_ORDERS_IDLE_RUN
			// Died in one of its own ticks (a blow, a fall): the ref isn't null in OpenDream, and the next call on it would
			// end this pass for every unit after it in the list (polish-errors, 10-26).
			if(Rm3DGone(M)) continue
		M.RmStepOffShared()   // never left standing on one of its side (Clip.dm)
		if(spread && ++idle >= RM_ORDERS_IDLE_RUN)
			idle = 0
			RmTrackPause()
	if(!client) return
	if(remaster_markers) for(var/image/I in remaster_markers) client.images -= I
	remaster_markers = list()
	if(remaster_3d) return   // the numbered targets on the 2D map: the 3D view hides it and draws them itself (HUD "targets")
	var/list/seen = list()
	for(var/mob/Monsters/M in Selected)
		var/list/tasks = list()
		if(M.remaster_active) tasks += M.remaster_active
		if(M.remaster_orders) tasks += M.remaster_orders
		var/number = 0
		for(var/datum/remaster_order/O in tasks)
			number++
			var/atom/A = O.target
			if(!A || !A.z || (A in seen)) continue
			seen += A
			var/image/I = image(null, locate(A.x, A.y, A.z))
			I.maptext = "<center><font color=#ffe1a1 size=3>[number]</font></center>"
			I.maptext_width = 32
			I.maptext_height = 32
			I.layer = FLY_LAYER + 1
			client.images += I
			remaster_markers += I

mob/Monsters/ChangeOwnership(WHO, FORCE)
	var/old_owner = Owner
	. = ..()
	if(Owner != old_owner)
		RemasterStopOrders()
		remaster_patrol = null   // its old owner's patrol route isn't its new owner's (Patrol.dm)
		remaster_job = "manual"
		if(!old_owner)
			remaster_role_paused = 0
			remaster_order_status = "Idle"

mob/verb/StopAll()
	var/n = 0
	var/mob/Monsters/one
	for(var/mob/Monsters/M in Selected) if(M.Owner == src)
		M.RemasterStopOrders()
		M.remaster_patrol = null   // Stop ends a patrol too, or the patrol tick sends it straight back out (Patrol.dm)
		n++
		one = M
	if(n && istype(src, /Player)) src:RemasterNotice(n == 1 ? "[one.RemasterBareName()] stopped." : "[n] units stopped.")   // it said nothing
	return ..()

// The original workshops' menus only work for a unit beside the bench, and said nothing otherwise (playtest: "I chose
// Wooden Spade twice and nothing happened"). A click on one with units selected and none beside it sends the nearest
// there, and its menu opens when it arrives; false when someone is already beside it (the menu opens now), nobody
// selected can go, or it is not one of those workshops (rts-feel).
proc/RemasterStationNeedsBeside(mob/WorkShops/W)
	if(istype(W, /mob/WorkShops/CampFires/GoodAltar) || istype(W, /mob/WorkShops/CampFires/EvilAltar)) return 1
	for(var/T in list(/mob/WorkShops/Carpentry, /mob/WorkShops/Masonary, /mob/WorkShops/Smelters, /mob/WorkShops/Kitchen, /mob/WorkShops/CampFires, /mob/WorkShops/Melter, /mob/WorkShops/Forge, /mob/WorkShops/PoisonStation, /mob/WorkShops/GemCutter, /mob/WorkShops/PotionStation, /mob/WorkShops/BoneCraft, /mob/WorkShops/LeatherWorks))
		if(istype(W, T)) return 1
	return 0

Player/proc/RemasterWalkToStation(mob/WorkShops/W)
	if(!W || !W.z || !isturf(W.loc) || !RemasterStationNeedsBeside(W)) return 0
	var/mob/Monsters/near
	for(var/mob/Monsters/M in Selected)
		if(!RemasterInteractActor(M) || M.HP <= 0 || M.GoingToDie || M.Wagon || M.z != W.z) continue
		if(get_dist(M, W) <= 1) return 0
		if(!near || get_dist(M, W) < get_dist(near, W)) near = M
	if(!near) return 0
	var/turf/spot
	for(var/turf/T in orange(1, W))
		if(!RemasterTilePlaces(T, list(near)) || !RemasterWalkable(T, near, T)) continue
		if(!spot || get_dist(T, near) < get_dist(spot, near)) spot = T
	if(!spot) return 0
	var/list/keep = Selected
	Selected = list(near)
	var/n = RemasterOrder(spot, 0, "Move")
	Selected = keep
	if(!n) return 0
	RemasterNotice("[near.RemasterBareName()] walks over to the [lowertext(RemasterStationName(W))]; its menu opens there.")
	spawn(0) RemasterOpenStationOnArrival(near, W)
	return 1

Player/proc/RemasterOpenStationOnArrival(mob/Monsters/M, mob/WorkShops/W)
	var/until = world.time + 300
	while(world.time < until)
		sleep(2)
		if(!M || !W || M.HP <= 0 || !(M in Selected)) return
		if(M.z == W.z && get_dist(M, W) <= 1)
			usr = src
			if(client) client.RemasterButton(W)
			else W.DblClick()
			return
		if(!M.remaster_active || M.remaster_active.kind != "Move") return   // given another order, or it gave up

// A right-click on the minimap with units selected (or a click in Attack mode): they go there ("x|y|shift"), however
// far the spot is from the camera (a 3D click only reaches what the view shows) (rts-feel).
Player/proc/RemasterMapMove(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 2 || !length(Selected)) return 0
	var/X = text2num(p[1])
	var/Y = text2num(p[2])
	if(isnull(X) || isnull(Y)) return 0
	var/turf/T = locate(clamp(round(X), 1, world.maxx), clamp(round(Y), 1, world.maxy), z)
	if(!T || get_dist(src, T) > 200) return 0
	usr = src
	if(remaster_attack_mode) return RemasterAttackOrder(T)   // A, then the minimap: attack-move there
	return RemasterOrder(T, length(p) >= 3 && p[3] == "1", "Move")
