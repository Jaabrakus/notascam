// Resource delivery is a finite task or a detour that retains the active task.
Player/var/remaster_stock_filter = "mixed"
mob/Monsters/var/tmp/datum/remaster_order/remaster_delivery

// The raw materials every store and worker reads (ore-stores, 10-27), so a new raw good is added here once. Minerals are
// what a quarry gives besides stone: the five ores, the three uncut gems (never cut gems or rings: the gems family holds
// those too) and rock salt. Bones are in Mining supplies only (one piece in 40; haulers would go after fish and corpse
// bones). Soul stones are not raw goods.
var/list/rm_raw_minerals = list(/obj/Items/ores/Iron, /obj/Items/ores/Silver, /obj/Items/ores/Gold, /obj/Items/ores/Adamantium, /obj/Items/ores/Sand, /obj/Items/gems/UnCutRuby, /obj/Items/gems/UnCutEmerald, /obj/Items/gems/UnCutDiamond, /obj/Items/RemasterSalt)
proc/RemasterRawKind(obj/Items/I)
	if(istype(I, /obj/Items/woods/wood)) return "wood"
	if(istype(I, /obj/Items/ores/stone)) return "stone"
	if(istype(I, /obj/Items/Bones/Bones)) return "bones"
	if(I && (I.type in rm_raw_minerals)) return "minerals"
	return null

// What each drop-off setting takes. The default keeps its id "mixed", so a saved village on it takes minerals at once
// (the owner, 10-27); "woodstone" is the old "Wood + stone".
var/list/rm_stock_sets = list("wood"=list("wood"), "stone"=list("stone"), "woodstone"=list("wood", "stone"), "mixed"=list("wood", "stone", "minerals"), "mining"=list("stone", "minerals", "bones"))

Player/proc/RemasterStockDescription()
	switch(remaster_stock_filter)
		if("wood") return "Wood"
		if("stone") return "Stone"
		if("woodstone") return "Wood + stone only"
		if("mixed") return "Wood, stone and minerals"
		if("mining") return "Stone, ores, sand, uncut gems, rock salt and bones"
	return "No resources (choose a filter)"

Player/proc/RemasterStockAcceptsKind(kind)
	if(!(remaster_stock_filter in rm_stock_sets)) return 0
	if(kind in list("ores", "gems")) kind = "minerals"     // RemasterResourceKind's names
	return kind in rm_stock_sets[remaster_stock_filter]

Player/proc/RemasterStockAccepts(obj/Items/I)
	if(!I || I.EquipmentType()) return 0
	var/raw = RemasterRawKind(I)
	return raw && (remaster_stock_filter in rm_stock_sets) && (raw in rm_stock_sets[remaster_stock_filter])

// Vampires and werewolves are never sent to silver (ore-stores, 10-27): it burns them. Raw silver ore has no Silver flag
// of its own (Turfs.dm), so it is named here.
mob/Monsters/proc/RmShunsSilver(obj/Items/I)
	return (Race == "Vampire" || SubRace == "Werewolf") && (I.Silver || istype(I, /obj/Items/ores/Silver))

mob/Monsters/proc/RemasterDeliveryWeight(Player/P)
	var/amount = 0
	for(var/obj/Items/I in src)
		if(I.suffix == "(Carrying)" && !I.EquipmentType() && P.RemasterStockAccepts(I)) amount += I.weight
	return amount

mob/Monsters/proc/RemasterBeginDelivery(obj/Items/needed)
	var/Player/P = Owner
	if(!istype(P)) return 0
	var/turf/S = P.RemasterStockpile()
	if(S && !S.density && z == SKY_LAYER && S.z == GROUND_LAYER)   // up on a building or a mountain: down first (a hop off its first step), the delivery after (the real game 10-30: a delivery started up there stood stuck, "The drop-off moved or is gone")
		var/datum/remaster_order/HO = RemasterHopOrder(P, src, S)
		if(HO)
			HO.automatic = 1
			RemasterSuspendControllers()
			remaster_active = HO
			RemasterStartOrder(HO)
			remaster_order_status = "Going down to the stockpile"
			return 1
	if(!S || S.density || S.z != z)
		RemasterBlock("Choose a reachable drop-off on this level")
		return 0
	var/released = RemasterDeliveryWeight(P)
	if(released <= 0 || (needed && weight + needed.weight - released > weightmax))
		RemasterBlock("Unloading what the stockpile takes wouldn't free enough room")
		return 0
	if(!remaster_delivery)
		remaster_delivery = new
	remaster_delivery.issuer = P
	remaster_delivery.kind = "Drop off"
	remaster_delivery.target = S
	RemasterStartOrder(remaster_delivery)
	RemasterSuspendControllers()
	remaster_blocked = null
	remaster_order_status = "Delivering resources, then back to the task"
	return 1

Player/proc/RemasterDropOff(queued = 0, interrupt = 0)
	var/turf/S = RemasterStockpile()
	if(!S || S.density)
		RemasterNotice("Set a stockpile on open ground first.")
		return 0
	var/count = 0
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || !(M in UnitList) || M.Wagon || M.z != S.z) continue
		if(interrupt)
			// An unavailable unload is only feedback; keep the current response
			// and task status until a delivery can actually take over.
			if(M.RemasterDeliveryWeight(src) <= 0) continue
			if(M.RemasterBeginDelivery(null))
				M.RemasterCancelDefense()
				M.remaster_paused = 0
				M.remaster_wait_for_resume = 0
				count++
			continue
		if(queued && length(M.remaster_orders) >= 32) continue
		if(!queued) M.RemasterCancelOrders()
		if(!M.remaster_defense && !(queued && M.remaster_paused)) M.RemasterSuspendControllers()
		if(!M.remaster_orders) M.remaster_orders = list()
		var/datum/remaster_order/O = new
		O.issuer = src
		O.kind = "Drop off"
		O.target = S
		M.remaster_orders += O
		M.RemasterOrderTick()
		count++
	RemasterNotice(count ? (interrupt ? "Unloading, then back to work." : "Drop-off task added.") : "None of the selected on this level carries anything the stockpile takes.")
	return count

mob/Monsters/proc/RemasterDepositTick(datum/remaster_order/O, Player/P)
	var/turf/S = O.target
	if(O.issuer != P || !S || S != P.RemasterStockpile() || S.density || S.z != z)
		RemasterBlock("The drop-off moved or is gone: choose one and try again")
		return 0
	if(!RemasterLandForWork()) return 0
	if(get_dist(src, S) > 1)
		RemasterApproach(O, S, 1)
		return 0
	destination = null
	var/amount = 0
	for(var/obj/Items/I in contents.Copy())
		if(I.suffix != "(Carrying)" || I.EquipmentType() || !P.RemasterStockAccepts(I)) continue
		if(DropItem(I) && I)
			I.loc = S
			I.Owner = P
			amount++
	remaster_blocked = null
	remaster_wait_for_resume = 0
	if(O == remaster_active) RemasterFinishOrder("Delivered [amount] resource item[amount == 1 ? "" : "s"]")
	return 1

mob/Monsters/proc/RemasterDeliveryTick(Player/P)
	var/datum/remaster_order/O = remaster_delivery
	if(RemasterDepositTick(O, P))
		remaster_delivery = null
		if(remaster_active)
			RemasterStartOrder(remaster_active)
			remaster_order_status = "Returning to [remaster_active.kind]"
		else remaster_order_status = "Delivered"

// Small local role presets use the same finite tasks as direct commands.
// Their work area is fixed when assigned; they never expand to the whole world.
mob/Monsters
	var/remaster_area_x = 0
	var/remaster_area_y = 0
	var/remaster_area_z = 0

Player/proc/RemasterClaimed(atom/A, mob/Monsters/worker)
	for(var/mob/Monsters/M in UnitList)
		if(M == worker || M.Owner != src) continue
		if(M.remaster_active)
			if(M.remaster_active.target == A || (A in M.remaster_active.harvest_items)) return 1
		for(var/datum/remaster_order/O in M.remaster_orders) if(O.target == A) return 1
	return 0

mob/Monsters/proc/RemasterRoleStatus(message)
	remaster_work_status = message
	remaster_order_status = message

mob/Monsters/proc/RemasterRoleTick(Player/P)
	var/turf/area_center = locate(remaster_area_x, remaster_area_y, remaster_area_z)
	var/turf/stock = P.RemasterStockpile()
	if(!area_center || area_center.z != z)
		RemasterRoleStatus("Set a work area on this level")
		return
	if((!stock || stock.z != z || stock.density) && !P.RemasterLoadStopOn(src))   // a cart loading stop down here will do (Carts.dm)
		RemasterRoleStatus("Set a drop-off on this level")
		return
	var/expected_resource = remaster_job == "woodcutter" ? "wood" : "stone"
	if(remaster_job != "hauler" && !P.RemasterStockAcceptsKind(expected_resource))
		RemasterRoleStatus("Drop-off must accept [expected_resource]")
		return
	// Haulers deliver each collected item; harvesters batch until capacity.
	if(remaster_job == "hauler" && RemasterDeliveryWeight(P) > 0)
		RemasterBeginDelivery(null)
		return
	var/atom/target
	var/distance = 1000000
	if(remaster_job == "hauler")
		for(var/obj/Items/I in range(6, area_center))
			if(!P.RemasterMayCollect(I) || !P.RemasterStockAccepts(I) || I.loc == stock || P.RemasterClaimed(I, src) || RmShunsSilver(I)) continue
			if(I.weight > weightmax) continue
			var/d = get_dist(src, I)
			if(d < distance)
				distance = d
				target = I
	else
		for(var/turf/T in range(6, area_center))
			if(!T.density || (T.Owner && T.Owner != P) || P.RemasterClaimed(T, src)) continue
			if(remaster_job == "woodcutter" && !T.Tree) continue
			if(RemasterTendReached(T, src)) continue    // tended down to its mark: growing back (Yield.dm)
			// Player-made walls are never incidental autonomous mining targets.
			if(remaster_job == "miner" && (!T.CanDigAt || T.Tree || T.IsWall || RmBuilt(T))) continue   // nor built columns (Plans.dm)
			var/d = get_dist(src, T)
			if(d < distance)
				distance = d
				target = T
	if(!target)
		if(RemasterDeliveryWeight(P) > 0) RemasterBeginDelivery(null)
		else
			// say what's missing and how to fix it (playtest: the old line left a new player stuck)
			var/what = remaster_job == "woodcutter" ? "no trees" : remaster_job == "miner" ? "no rock to mine" : remaster_job == "hauler" ? "nothing to carry" : "no work"
			RemasterRoleStatus("Idle: [what] within 6 tiles of its work area. Move the area with Work → Centre work area on selected units.")
		return
	var/datum/remaster_order/O = new
	O.issuer = P
	O.target = target
	O.kind = RemasterOrderKind(target)
	O.automatic = 1
	if(!O.kind) return
	RemasterSuspendControllers()
	remaster_active = O
	RemasterStartOrder(O)
	RemasterOrderTick()
