// Saved configuration contains strings, numbers and recipe IDs. Runtime targets
// are tmp: loading an army resolves fresh targets instead of saving world items.
Player/var
	remaster_stock_x = 0
	remaster_stock_y = 0
	remaster_stock_z = 0
Player/var/tmp/remaster_settlement_message = "Assign workers and place a stockpile to begin."
mob/Monsters/var
	remaster_job = "manual"
	remaster_priority = 2
	list/remaster_production = list()
mob/Monsters/var/tmp
	remaster_work_status = "Manual control"
	atom/remaster_work_destination
	obj/Items/remaster_work_item
	remaster_work_position
	remaster_work_since = 0
	remaster_work_retry = 0
	remaster_craft_ready = 0

proc/RemasterSettlementRecipes()
	return list(
		list("id"="bucket", "label"="Wooden bucket", "output"=/obj/Items/Shafts/WoodenBucket),
		list("id"="spade", "label"="Wooden spade", "output"=/obj/Items/Shafts/WoodenSpade),
		list("id"="spike", "label"="Wooden spike", "output"=/obj/Items/Traps/Spikes/WoodenSpike),
		// Remastered (Construction.dm): carried into tunnels, it goes up by itself where needed.
		list("id"="beam", "label"="Support beam", "output"=/obj/Items/Furniture/Pillars/WoodenBeam))

proc/RemasterSettlementRecipe(ID)
	for(var/list/R in RemasterSettlementRecipes()) if(R["id"] == ID) return R

Player/proc/RemasterStockpile()
	if(remaster_stock_x < 1 || remaster_stock_y < 1 || remaster_stock_z < 1) return
	return locate(remaster_stock_x, remaster_stock_y, remaster_stock_z)

mob/Monsters/proc/RemasterStopWork()
	if(destination == remaster_work_destination) destination = null
	remaster_work_destination = null
	remaster_work_item = null
	remaster_work_position = null
	remaster_work_since = 0
	remaster_work_retry = 0

mob/Monsters/proc/RemasterWorkBlocked()
	if(HP <= 0 || GoingToDie) return "Worker is no longer alive"
	if(!isturf(loc)) return "Worker is inside something"
	if(Fainted) return "Worker has fainted"
	if(Stunned) return "Worker is stunned"
	if(Sleeping) return "Worker is sleeping"
	if(!CanWalk || InHole) return "Worker cannot walk"
	if(Flying || IsMist) return "Land before gathering or crafting"
	if(!CanUseLeftArm && !CanUseRightArm) return "Worker cannot use either arm"
	return null

mob/Monsters/proc/RemasterCanQueue(ID)
	if(!RemasterSettlementRecipe(ID)) return "Unknown recipe"
	if(Race == "Spider" || Wagon) return "This unit cannot use a carpentry workshop"
	if(ID == "spade" && Race == "Lizardman") return "Lizardmen cannot craft wooden spades"
	if(length(remaster_production) >= 10) return "Queue is full (10 attempts)"
	return null

// Never direct a worker at a dense workshop itself: Bump would attack it.
mob/Monsters/proc/RemasterWorkToward(atom/TARGET, LABEL)
	if(!TARGET || !isturf(TARGET.loc) && !isturf(TARGET))
		RemasterStopWork()
		remaster_work_status = "Work target is no longer available"
		return 0
	if(z != TARGET.z)
		RemasterStopWork()
		remaster_work_status = "Target is on another layer"
		return 0
	if(get_dist(src, TARGET) <= 1)
		if(destination == remaster_work_destination) destination = null
		remaster_work_destination = null
		remaster_work_position = null
		return 1
	if(world.time < remaster_work_retry)
		remaster_work_status = "Blocked path to [LABEL]; retrying shortly"
		return 0
	var/position = "[x],[y],[z]"
	if(position != remaster_work_position)
		remaster_work_position = position
		remaster_work_since = world.time
	else if(world.time - remaster_work_since >= 50)
		if(destination == remaster_work_destination) destination = null
		remaster_work_destination = null
		remaster_work_retry = world.time + 50
		remaster_work_since = world.time + 50
		remaster_work_status = "Blocked path to [LABEL]; retrying shortly"
		return 0
	var/turf/nearest
	var/distance = 100000
	for(var/turf/T in range(1, TARGET))
		if(T.density) continue
		var/blocked = 0
		for(var/atom/movable/A in T) if(A != src && A.density)
			blocked = 1
			break
		if(blocked) continue
		var/d = get_dist(src, T)
		if(d < distance)
			nearest = T
			distance = d
	if(!nearest)
		if(destination == remaster_work_destination) destination = null
		remaster_work_destination = null
		remaster_work_status = "No free tile beside [LABEL]"
		return 0
	remaster_work_destination = nearest
	destination = nearest
	remaster_work_status = "Walking to [LABEL]"
	return 0

Player/proc/RemasterMayCollect(obj/Items/I)
	return I && isturf(I.loc) && !I.suffix && (!I.Owner || I.Owner == src)

mob/Monsters/proc/RemasterHaulTick(Player/P, list/RESERVED)
	var/turf/STOCK = P.RemasterStockpile()
	if(!STOCK || STOCK.density)
		RemasterStopWork()
		remaster_work_status = "Place a stockpile on open ground"
		return
	if(z != STOCK.z)
		RemasterStopWork()
		remaster_work_status = "Stockpile is on another layer"
		return
	var/item_type
	switch(remaster_job)
		if("wood") item_type = /obj/Items/woods/wood
		if("stone") item_type = /obj/Items/ores/stone
		if("food") item_type = /obj/Items/Food
	if(!item_type) return
	for(var/obj/Items/I in contents)
		if(!istype(I, item_type) || I.suffix != "(Carrying)") continue
		if(!RemasterWorkToward(STOCK, "stockpile")) return
		if(DropItem(I))
			if(I)
				I.loc = STOCK
				I.Owner = P
			remaster_work_item = null
			remaster_work_status = "Delivered [remaster_job]"
		return
	var/obj/Items/ITEM = remaster_work_item
	if(!P.RemasterMayCollect(ITEM) || !istype(ITEM, item_type) || ITEM.loc == STOCK || (ITEM in RESERVED) || get_dist(STOCK, ITEM) > 12)
		ITEM = null
		var/distance = 100000
		var/too_heavy = 0
		for(var/obj/Items/I in range(12, STOCK))
			if(!istype(I, item_type) || !P.RemasterMayCollect(I) || I.loc == STOCK || (I in RESERVED)) continue
			if(I.weight + weight > weightmax)
				too_heavy = 1
				continue
			var/d = get_dist(src, I)
			if(d < distance)
				distance = d
				ITEM = I
		if(!ITEM)
			RemasterStopWork()
			remaster_work_status = too_heavy ? "Too heavy to carry the [remaster_job] nearby" : "No loose [remaster_job] within 12 tiles of stockpile"
			return
	remaster_work_item = ITEM
	RESERVED += ITEM
	if(!RemasterWorkToward(ITEM, remaster_job)) return
	// Revalidate after approaching: another worker/player may already have it.
	if(P.RemasterMayCollect(ITEM) && PickUpItem(ITEM))
		ITEM.Owner = P
		remaster_work_item = null
		remaster_work_status = "Carrying [remaster_job] to stockpile"
	else remaster_work_status = "Couldn't pick it up: too heavy, or not something this unit can carry"

mob/Monsters/proc/RemasterCarpentry(Player/P)
	for(var/mob/WorkShops/Carpentry/W in range(12, src))
		if(!W.Owner || W.Owner == P) return W

mob/Monsters/proc/RemasterCraftTick(Player/P, list/RESERVED)
	if(world.time < remaster_craft_ready || !length(remaster_production)) return
	var/id = remaster_production[1]
	var/list/recipe = RemasterSettlementRecipe(id)
	if(!recipe)
		remaster_production.Cut(1, 2)
		remaster_work_status = "Removed an unknown saved recipe"
		return
	if(Race == "Spider" || Wagon || id == "spade" && Race == "Lizardman")
		RemasterStopWork()
		remaster_work_status = "This race can't make the queued item; cancel it to go on"
		return
	var/mob/WorkShops/Carpentry/WORKSHOP = RemasterCarpentry(P)
	if(!WORKSHOP)
		RemasterStopWork()
		remaster_work_status = "Needs a carpentry workshop within 12 tiles"
		return
	var/obj/Items/woods/wood/WOOD
	for(var/obj/Items/woods/wood/W in contents) if(W.suffix == "(Carrying)")
		WOOD = W
		break
	if(!WOOD)
		for(var/obj/Items/woods/wood/W in range(12, WORKSHOP))
			if(!P.RemasterMayCollect(W) || (W in RESERVED) || W.weight + weight > weightmax) continue
			WOOD = W
			break
		if(!WOOD)
			RemasterStopWork()
			remaster_work_status = "Needs 1 loose wood near the carpentry, and room in the bag to carry it"
			return
		RESERVED += WOOD
		remaster_work_item = WOOD
		if(RemasterWorkToward(WOOD, "crafting wood"))
			if(P.RemasterMayCollect(WOOD) && PickUpItem(WOOD))
				WOOD.Owner = P
				remaster_work_item = null
				remaster_work_status = "Wood collected for [recipe["label"]]"
		return
	if(!RemasterWorkToward(WORKSHOP, "carpentry workshop")) return
	if(!WOOD || WOOD.loc != src || WOOD.suffix != "(Carrying)") return
	// These three existing Carpentry recipes each consume one wood and use
	// prob(WoodCraftingSkill * 4). DropItem maintains the inventory weight first.
	var/success = prob(WoodCraftingSkill * 4)
	if(!DropItem(WOOD))
		remaster_work_status = "Couldn't use the carried wood"
		return
	if(WOOD) del(WOOD)
	remaster_production.Cut(1, 2)
	if(success)
		var/output_type = recipe["output"]
		var/obj/Items/PRODUCT = new output_type(loc)
		PRODUCT.Owner = P
		WoodCraftingSkill += 0.5
		remaster_work_status = "Crafted [recipe["label"]]"
		P.RemasterMilestone("craft")    // the Guide's "Produce useful equipment" goal (playtest)
	else
		if(id != "spike") WoodCraftingSkill += 0.5
		remaster_work_status = "Spoiled an attempt at [recipe["label"]]; 1 wood used up"
	remaster_craft_ready = world.time + 10
	remaster_work_item = null
	P.remaster_settlement_message = "[name]: [remaster_work_status]"

Player/var/tmp/rm_settle_i = 0      // the slice taken last, 1 to RemasterSettlementParts() (realms over 1,000 units)

// J2 part 3 (gathering, 2026-10-26): inside the player's spread track run (Spread.dm) the pass goes on next tick between
// units once this tick's share is used: rm_settle_slice ms of the run's work in the tick, or the ledger's line
// (RM_TRACK_SLICE) as at the track's other safe points, whichever comes first. A unit is checked when its turn comes,
// after any wait, so an order given meanwhile is seen. Calls from verbs and tests (no run) go in one go as before.
// rm_settle_spread = 0: in one go, as before.
var/rm_settle_slice = 30                // ms (30: the ledger's own line decides; 15 is smoother but gathers ~5% less stone at 2,000 workers)
var/rm_settle_spread = 1
Player/var/tmp/rm_settle_live = -1000   // world.time a spread pass last went on: no second pass starts while one waits

// How many calls a full round of the realm's settlement steps takes: 1 up to 1,000 units, 2 up to 4,000, 4 above (each
// call is half a second apart: every unit steps every 0.5, 1 or 2 s).
Player/proc/RemasterSettlementParts()
	var/n = length(UnitList)
	return n <= 1000 ? 1 : n < 4000 ? 2 : 4

Player/proc/RemasterSettlementTick(spread = 0)
	if(rm_fh && rm_fh["state"] != "done") RmFirstHouseTick()   // the first house (FirstHouse.dm), every 30 s
	if(length(rm_plan_doors) || length(rm_plan_steps)) RmPlanDoorTick()   // Plan mode's doors waiting for their walls, stairs' steps for their blocks (PlanPieces.dm), every 3 s
	spread = spread && rm_settle_spread && rm_track_run
	if(world.time - rm_settle_live < 20) return   // a spread pass is under way, waiting between units: it has this work
	if(spread) rm_settle_live = world.time
	var/list/reserved = list()
	// priority 1 (High) first, so High villagers reserve shared work first, as building sites and board orders do
	// (it walked 3 → 1 while every label says 1 = High; rts-feel 2026-10-23, from hud-craft's board note)
	// One walk over UnitList sorts the realm's units by priority (it walked the list once per priority: 90,000 visits a
	// call at 30,000 units); each priority then runs in UnitList order, as before (jobs, 2026-10-24).
	// Up to 1,000 units every unit is taken every call, as always. A bigger realm's are taken a rotating slice a call (a
	// half up to 4,000 units, a quarter above), so a call stays under about 30 ms at 30,000 and each unit still steps
	// every 0.5-2 s. Player orders don't come through here: only automatic work pickup waits (jobs, 2026-10-24).
	var/n = length(UnitList)
	var/parts = RemasterSettlementParts()
	var/first = 1
	var/last = n
	if(parts > 1)
		// the k-th of parts fixed slices, k going round: every unit once in each round of parts calls, also when units
		// come and go (a moving start could end a round on a short slice and leave the first ones a call late)
		rm_settle_i = rm_settle_i % parts + 1
		var/size = round((n + parts - 1) / parts)
		first = (rm_settle_i - 1) * size + 1
		last = min(n, rm_settle_i * size)
	var/list/b1 = list()
	var/list/b2 = list()
	var/list/b3 = list()
	for(var/i = first, i <= last, i++)
		var/mob/Monsters/M = UnitList[i]
		if(!istype(M) || M.Owner != src) continue
		if(M.remaster_priority == 1) b1 += M
		else if(M.remaster_priority == 2) b2 += M
		else if(M.remaster_priority == 3) b3 += M
	var/w0 = world.time
	for(var/list/B in list(b1, b2, b3))
		for(var/mob/Monsters/M in B)
			if(spread)
				RmSettlePause()
				rm_settle_live = world.time
				if(world.time != w0 && Rm3DGone(M)) continue   // gone while the pass waited (a deleted unit's reference isn't null)
			if(!M || M.Owner != src) continue      // its owner changed earlier in this call
			if(M.remaster_defense || M.remaster_attack || M.remaster_role_paused || M.remaster_paused) continue
			// A Manual unit with nothing queued does no work here: skipped before the mood check (most units, and no proc
			// call), except where that check draws a random number (a captive, or moods on and it unhappy), so every later
			// roll of the dice stays the same (jobs, 2026-10-24)
			if(M.remaster_job == "manual" && !length(M.remaster_production) && !M.rm_cap_state && (!rm_moods_on || M.remaster_snap_until > world.time || M.remaster_mood >= rm_mood_unhappy)) continue
			if(M.RemasterMoodSkipsWork()) continue   // unhappy units work slower (Moods.dm)
			if(M.remaster_job == "manual" && !length(M.remaster_production)) continue
			if(M.remaster_care)
				M.remaster_work_status = "[M.remaster_care_status]; job resumes after"
				continue
			if(M.RemasterOnConstruction()) continue // Blueprints.dm runs construction and keeps its status
			if(M.RemasterHasOrder())   // Orders.dm (a direct call: hascall and call looked it up by name for every unit)
				if(M.remaster_delivery || (M.remaster_active && M.remaster_active.automatic)) M.remaster_work_status = M.remaster_order_status
				else M.remaster_work_status = "Paused for manual orders"
				continue
			if(M.destination && M.destination != M.remaster_work_destination)
				// tired and making for a bed (the original's walk to bed, Creatures/Mob Procs.dm TirednessTick) is no order of
				// the player's: it said "Paused for manual orders" (20: Care.dm's REMASTER_CARE_TIRED, defined after this file)
				M.remaster_work_status = M.Tiredness <= 20 && isturf(M.destination) && (locate(/obj/Items/Furniture/Beds) in M.destination) ? "Tired: going to bed" : "Paused for manual orders"
				continue
			var/blocked = M.RemasterWorkBlocked()
			if(blocked)
				M.RemasterStopWork()
				M.remaster_work_status = blocked
				continue
			if(length(M.remaster_production)) M.RemasterCraftTick(src, reserved)
			else if(M.remaster_job in list("woodcutter", "miner", "hauler")) M.RemasterRoleTick(src)
			else if(M.remaster_job == "any") M.RmJobStep(src, reserved)   // Any work: the job board's villagers (Jobs.dm; reserved for a make row's hauling)
			else if(M.remaster_job == "board") M.RemasterBoardWork(src, reserved)
			else if(M.remaster_job in list("farmer", "hunter", "cook")) M.RemasterFoodTick(src)
			else if(M.remaster_job == "merchant") M.RemasterMerchantTick(src)
			else if(M.remaster_job == "keeper") M.RmKeeperTick(src)   // a quest giver by its board (QuestKeepers.dm)
			else if(M.remaster_job == "doctor") M.RemasterDoctorTick(src)   // Doctor.dm
			else if(M.remaster_job == "gravedigger") M.RemasterGravediggerTick(src)   // Graves.dm
			else M.RemasterHaulTick(src, reserved)
	rm_settle_live = -1000

// A safe point between units (J2 part 3): the run goes on next tick once it did rm_settle_slice ms of work in this one,
// or at the ledger's line.
Player/proc/RmSettlePause()
	RmTrackPiece()
	if(rm_track_used >= rm_settle_slice) RmTrackPause(0)   // 0: always waits for the next tick
	else RmTrackPause()                                    // the ledger's line (Spread.dm, defined after this file)

// One worker's role change; shared by the Work page (selected units) and the
// Village roster (one row at a time).
mob/Monsters/proc/RemasterAssignJob(VALUE)
	var/rm_old_job = remaster_job     // the job board keeps its totals (Jobs.dm)
	RemasterCareInterrupt()
	if(remaster_board_claim) RemasterBoardRelease()
	RemasterStopWork()
	if(hascall(src, "RemasterCancelOrders")) call(src, "RemasterCancelOrders")()
	destination = null
	HomeLoc = null
	RemasterSuspendControllers()
	remaster_role_paused = 0
	remaster_job = VALUE
	if(VALUE in list("woodcutter", "miner", "hauler", "farmer", "hunter", "cook", "doctor", "gravedigger"))
		remaster_area_x = x
		remaster_area_y = y
		remaster_area_z = z
		remaster_auto_unload = 1
	remaster_work_status = VALUE == "manual" ? "Manual control" : VALUE == "board" ? "Board worker: waiting for work orders" : VALUE == "builder" ? "Builder: works on the planned construction" : VALUE == "any" ? "Job board: free, waiting for a job" : "Assigned [VALUE]; work area within 6 tiles"
	RmJobRoleChanged(rm_old_job)

Player/proc/RemasterSettlementCommand(ACTION, VALUE)
	if(ACTION == "tendliving")    // the realm's workers tend living resources (Yield.dm)
		if(!(VALUE in list("on", "off"))) return 0
		remaster_tend_living = VALUE == "on"
		remaster_settlement_message = remaster_tend_living ? "Workers tend living resources: they leave trees at half and living ore blocks their last ore, so they grow back." : "Workers take everything: whole trees are felled and living ore blocks dug out (they die). A unit can still be set to tend in its Orders."
		return 1
	if(ACTION == "stockfilter")
		if(!(VALUE in list("wood", "stone", "woodstone", "mixed", "mining"))) return 0
		remaster_stock_filter = VALUE
		remaster_settlement_message = "Drop-off accepts [RemasterStockDescription()]."
		return 1
	if(ACTION == "stockpile")
		if(VALUE == "clear")
			remaster_stock_x = 0
			remaster_stock_y = 0
			remaster_stock_z = 0
			remaster_settlement_message = "Stockpile cleared; carried items stay with workers."
			return 1
		var/turf/T
		if(VALUE == "camera" && isturf(loc)) T = loc
		if(VALUE == "unit") for(var/mob/Monsters/M in Selected)
			if(M.Owner == src && isturf(M.loc))
				T = M.loc
				break
		if(!T || T.density)
			remaster_settlement_message = "Choose open ground at the camera or select your own worker."
			return 0
		remaster_stock_x = T.x
		remaster_stock_y = T.y
		remaster_stock_z = T.z
		remaster_settlement_message = "Stockpile placed at [T.x], [T.y], layer [T.z]. Workers collect within 12 tiles."
		return 1
	if(ACTION == "workarea")
		var/changed = 0
		for(var/mob/Monsters/M in Selected) if(M.Owner == src && (M in UnitList) && isturf(M.loc))
			M.remaster_area_x = M.x
			M.remaster_area_y = M.y
			M.remaster_area_z = M.z
			changed++
		remaster_settlement_message = "Work area set within 6 tiles of each selected unit."
		return changed
	if(!(ACTION in list("job", "priority", "craft", "cancel"))) return 0
	if(ACTION == "job" && !(VALUE in list("manual", "wood", "stone", "food", "woodcutter", "miner", "hauler", "board", "builder", "farmer", "hunter", "cook", "merchant", "doctor", "gravedigger", "any"))) return 0
	if(ACTION == "priority" && !("[VALUE]" in list("1", "2", "3"))) return 0
	if(ACTION == "craft" && !RemasterSettlementRecipe(VALUE)) return 0
	if(ACTION == "cancel" && VALUE != "all") return 0
	var/changed = 0
	var/reason
	for(var/mob/Monsters/M in Selected)
		if(!M || M.Owner != src || !(M in UnitList)) continue
		switch(ACTION)
			if("job")
				M.RemasterAssignJob(VALUE)
				changed++
			if("priority")
				M.remaster_priority = text2num("[VALUE]")
				changed++
			if("craft")
				var/unavailable = M.RemasterCanQueue(VALUE)
				if(unavailable)
					reason = unavailable
					continue
				if(!islist(M.remaster_production)) M.remaster_production = list()
				M.remaster_production += VALUE
				M.remaster_role_paused = 0
				if(M.HomeLoc)
					M.HomeLoc = null
					M.destination = null
				M.RemasterStopWork()
				M.remaster_work_status = "Added to the work queue"
				changed++
			if("cancel")
				M.remaster_production = list()
				M.RemasterStopWork()
				M.remaster_work_status = "Work queue cleared"
				changed++
	remaster_settlement_message = changed ? "Updated [changed] worker[changed == 1 ? "" : "s"]. [reason]" : (reason ? reason : "Select your own workers first.")
	return changed

Player/proc/RemasterSettlementData()
	var/list/data = list()
	var/turf/S = RemasterStockpile()
	data["stockpile"] = list("set"=!!S, "x"=remaster_stock_x, "y"=remaster_stock_y, "z"=remaster_stock_z, "filter"=remaster_stock_filter, "accepts"=RemasterStockDescription())
	data["jobs"] = list(list("id"="manual", "label"="Manual"), list("id"="doctor", "label"="Doctor"), list("id"="gravedigger", "label"="Gravedigger"), list("id"="woodcutter", "label"="Woodcutter"), list("id"="miner", "label"="Miner"), list("id"="hauler", "label"="Hauler"), list("id"="builder", "label"="Builder"), list("id"="farmer", "label"="Farmer"), list("id"="hunter", "label"="Hunter"), list("id"="cook", "label"="Cook"), list("id"="merchant", "label"="Merchant"), list("id"="board", "label"="Board worker"), list("id"="any", "label"="Job board"))
	var/list/units = list()
	// the Work page's selected workers: the first 48 (HudView.dm's cap; a bigger selection shows its count and summary).
	// The selection was just normalized to the player's own units, so "M in UnitList" (a search of the whole company
	// for each one) is not needed (hud-craft, 10-24)
	var/nsel = 0
	for(var/mob/Monsters/M in Selected)
		if(!M || M.Owner != src) continue
		if(++nsel > 48) break
		units += list(list("ref"=RemasterUIRef(M), "name"=M.name, "job"=M.remaster_job, "priority"=M.remaster_priority, "status"=M.remaster_work_status, "paused"=M.remaster_role_paused, "area"=list("x"=M.remaster_area_x, "y"=M.remaster_area_y, "z"=M.remaster_area_z, "radius"=6), "queue"=islist(M.remaster_production) ? M.remaster_production.Copy() : list()))
	data["units"] = units
	var/list/recipes = list()
	for(var/list/R in RemasterSettlementRecipes())
		var/available = 0
		var/reason = "Select your own worker"
		var/nr = 0
		for(var/mob/Monsters/M in Selected)
			if(!M || M.Owner != src) continue
			if(++nr > 48) break   // whether one of the first 48 selected can make it (it was every selected unit, per recipe)
			var/block = M.RemasterCanQueue(R["id"])
			if(!block)
				available = 1
				reason = "Queues until worker has wood and reaches a carpentry workshop"
				break
			reason = block
		recipes += list(list("id"=R["id"], "label"=R["label"], "cost"="1 wood per attempt", "requirement"="Carpentry workshop within 12 tiles; success chance is woodcraft skill x 4%; failed attempts use up the wood.", "available"=available, "reason"=reason))
	data["recipes"] = recipes
	data["tendLiving"] = remaster_tend_living
	data["message"] = remaster_settlement_message
	return data
