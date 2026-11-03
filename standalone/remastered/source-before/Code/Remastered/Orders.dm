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
	var/tmp/remaster_notice = "Select a unit, then a destination or resource."
	var/list/remaster_milestones = list()
	var/tmp/list/remaster_markers

Player/proc/RemasterNotice(message)
	remaster_notice = message

Player/proc/RemasterMilestone(id)
	if(!remaster_milestones) remaster_milestones = list()
	remaster_milestones[id] = 1

mob/Monsters/proc/RemasterHasOrder()
	return remaster_active || length(remaster_orders) || remaster_delivery

mob/Monsters/Move(NewLoc, Dir = 0, step_x = 0, step_y = 0)
	// WalkTo can inherit the logged-in player's usr from Login. Terrain uses
	// usr for collision exemptions and environmental effects, so queued work
	// must enter as its physical worker rather than the free-moving camera.
	if(RemasterHasOrder() || remaster_defense) usr = src
	return ..()

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
	RemasterCancelDefense()
	if(RemasterHasOrder()) RemasterPauseOrders(1)
	else RemasterSuspendControllers()
	remaster_role_paused = 1
	return 1

mob/Monsters/proc/RemasterCancelOrders()
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
	// Explicit loose equipment is a finite pickup, never an equip/resource role.
	if(istype(A, /obj/Items/Equipment) && isturf(A.loc) && isnull(A.suffix))
		var/obj/Items/Equipment/E = A
		if(E.ItemType) return "Pick up"
	if(istype(A, /obj/Items) && isturf(A.loc) && RemasterResourceKind(A)) return "Pick up"
	if(isturf(A))
		if(A.Tree && A.density) return "Chop"
		if(A.CanDigAt && A.density) return "Mine"
		if(!A.density) return "Move"
	return null

mob/Monsters/proc/RemasterPrepareTool(kind)
	var/tool
	if(kind == "Chop" && UsesPicks && Race != "Goblin" && !Werepowers && !VampPick) tool = "Axe"
	if(kind == "Mine" && UsesPicks && !Werepowers && !VampPick) tool = "Pickaxe"
	if(!tool || HoldingWeapon == tool) return 1
	for(var/obj/Items/E in src)
		// Dangerous cursed gear requires an explicit equipment interaction.
		if(E.icon == 'DemonicItems.dmi') continue
		if(E.ItemType == tool && E.suffix == "(Carrying)" && EquipItem(E))
			if(HoldingWeapon == tool) return 1
	RemasterBlock("Needs [tool]")
	return 0

mob/Monsters/proc/RemasterBlock(reason, manual = 0)
	destination = null
	Target = null
	remaster_blocked = reason
	remaster_wait_for_resume = manual
	remaster_order_status = reason
	if(remaster_active) remaster_active.path = null

Player/proc/RemasterOrder(atom/A, queued = 0)
	var/kind = RemasterOrderKind(A)
	if(!A || !A.z || !kind || !length(Selected))
		RemasterNotice("Select a unit and a clear destination or resource.")
		return 0
	if(A.Owner && A.Owner != src)
		RemasterNotice("That resource belongs to someone else.")
		return 0
	var/count = 0
	for(var/mob/Monsters/M in Selected)
		// A stale dying selection must not consume the only resource assignment.
		if(M.Owner != src || !(M in UnitList) || M.Wagon || M.HP <= 0 || M.GoingToDie) continue
		if(M.z != A.z)
			RemasterNotice("Use stairs to reach that level first.")
			continue
		if(queued && length(M.remaster_orders) >= 32)
			RemasterNotice("Queue full (32 pending tasks).")
			continue
		if(!queued) M.RemasterCancelOrders()
		if(!M.remaster_defense && !(queued && M.remaster_paused)) M.RemasterSuspendControllers()
		if(!M.remaster_orders) M.remaster_orders = list()
		var/datum/remaster_order/O = new
		O.issuer = src
		O.target = A
		O.kind = kind
		M.remaster_orders += O
		count++
		M.RemasterOrderTick()
		// One resource target goes to one actor. Ground moves can address a group.
		if(kind != "Move") break
	if(count)
		RemasterNotice("[queued ? "Added: " : "Started: "][kind]. Deselecting keeps the task running.")
		RemasterMilestone("order")
	return count

mob/Monsters/proc/RemasterStartOrder(datum/remaster_order/O)
	O.last_x = x
	O.last_y = y
	O.last_hp = O.target ? O.target.HP : null
	O.last_progress = world.time
	O.path = null

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
		remaster_order_status = "[remaster_care_status]; tasks retained"
		if(remaster_active) remaster_active.last_progress = world.time
		if(remaster_delivery) remaster_delivery.last_progress = world.time
		return
	if(GoingToDie || HP <= 0)
		RemasterStopOrders()
		return
	if(!isturf(loc) || !CanWalk || Fainted || Stunned || Sleeping || InHole)
		RemasterBlock(Sleeping ? "Sleeping; tasks retained" : "Cannot move; tasks retained")
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
	if(z != A.z)
		RemasterBlock("Target is on another level")
		return
	if(A.Owner && A.Owner != P)
		RemasterFinishOrder("Skipped: ownership changed")
		return
	if(!CanSee)
		RemasterBlock("Cannot see the target")
		return
	if(O.kind == "Move")
		if(loc == A)
			RemasterFinishOrder("Arrived")
		else RemasterApproach(O, A, 0)
		return
	if(O.kind == "Pick up")
		if(!isturf(A.loc) || A.suffix)
			RemasterFinishOrder(A.loc == src ? "Collected" : "Skipped: already collected")
			return
		if(get_dist(src, A) > 1)
			RemasterApproach(O, A, 1)
			return
		if(RemasterCollect(A)) RemasterFinishOrder("Collected [A.name]")
		return
	if(O.kind == "Chop" || O.kind == "Mine")
		if(!A.density)
			O.phase = "Collecting"
			for(var/obj/Items/I in O.harvest_items.Copy())
				if(!I || !isturf(I.loc) || I.suffix || (I.Owner && I.Owner != P))
					O.harvest_items -= I
					continue
				if(get_dist(src, I) > 1)
					RemasterApproach(O, I, 1)
					return
				if(RemasterCollect(I)) O.harvest_items -= I
				return
			P.RemasterMilestone("gather")
			RemasterFinishOrder("Gathered")
			return
		if(!RemasterPrepareTool(O.kind)) return
		if(Flying || IsMist)
			RemasterBlock("Land before gathering")
			return
		if(get_dist(src, A) > 1)
			RemasterApproach(O, A, 1)
			return
		if(O.last_hp != A.HP || x != O.last_x || y != O.last_y)
			O.last_progress = world.time
			O.last_hp = A.HP
			O.last_x = x
			O.last_y = y
		if(world.time - O.last_progress > max(100, Delay * 5))
			RemasterBlock("Work is blocked; check the target, then Resume", 1)
			return
		remaster_blocked = null
		remaster_order_status = "[O.kind]: [A.name]"
		destination = A

mob/Monsters/proc/RemasterCollect(obj/Items/I)
	if(Flying || IsMist)
		RemasterBlock("Land before collecting")
		return 0
	if(I.weight + weight > weightmax)
		if(remaster_auto_unload)
			RemasterBeginDelivery(I)
			return 0
		RemasterBlock("Carry capacity reached; unload or free space")
		return 0
	if(PickUpItem(I))
		remaster_blocked = null
		return 1
	RemasterBlock(RemasterPickupReason(I))
	return 0

// Record only fresh resource outputs created by this unit's actual harvest.
// Unrelated nearby items and seeds stay where they were.
mob/Monsters/Bump(atom/A)
	var/datum/remaster_order/O = remaster_active
	var/capture = O && O.target == A && (O.kind == "Chop" || O.kind == "Mine") && A.density && !remaster_paused
	var/list/before
	var/turf/workplace = loc
	if(capture) before = workplace.contents.Copy()
	. = ..()
	if(capture && src && O == remaster_active && workplace)
		for(var/obj/Items/I in workplace)
			if(I in before) continue
			var/resource = RemasterResourceKind(I)
			if(resource == "wood" || (O.kind == "Mine" && (resource in list("stone", "ores", "gems", "bones"))))
				O.harvest_items += I

mob/Monsters/proc/RemasterPickupReason(atom/A)
	if(Flying || IsMist) return "Land before picking up items"
	if(A.Silver && (Race == "Vampire" || SubRace == "Werewolf")) return "Cannot carry silver"
	if(weight + A.weight > weightmax) return "Carry capacity reached"
	return "Item cannot be picked up here"

mob/Monsters/proc/RemasterFinishOrder(message)
	remaster_active = null
	destination = null
	Target = null
	remaster_blocked = null
	remaster_wait_for_resume = 0
	remaster_order_status = message
	if(istype(Owner, /Player)) Owner:RemasterNotice("[name]: [message]")

// Bounded path search uses clear tiles only. Harvest collision is issued only
// when adjacent to the actual work target, never to an intervening structure.
proc/RemasterWalkable(turf/T, mob/Monsters/M)
	if(!T || T.density) return 0
	// Non-dense does not always mean safe ground. Entered applies the original
	// falling/death effects, so autonomous routes must go around these gaps.
	if(M.density && !M.Flying && (T.icon_state in list("Chasm", "Sky"))) return 0
	if(T.icon_state == "GoodGrass" && (M.Infects || M.Undead || M.Unholy || M.Race == "Svartalfar" || M.Race == "Demon")) return 0
	for(var/atom/movable/A in T) if(A != M && A.density) return 0
	return 1

proc/RemasterOrderPath(mob/Monsters/M, turf/goal, reach, turf/bounds = null, radius = 0)
	var/turf/start = M.loc
	var/list/open = list(start)
	var/list/cost = list()
	var/list/parent = list()
	var/list/closed = list()
	cost[start] = 0
	for(var/tries = 0, tries < 512 && open.len, tries++)
		var/turf/current
		var/best = 1000000
		for(var/turf/T in open)
			var/score = cost[T] + get_dist(T, goal)
			if(score < best)
				best = score
				current = T
		open -= current
		if(get_dist(current, goal) <= reach)
			var/list/path = list()
			while(current != start)
				path.Insert(1, current)
				current = parent[current]
			return path
		closed += current
		for(var/d in list(NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST))
			var/turf/next = get_step(current, d)
			if(bounds && next && (next.z != bounds.z || get_dist(next, bounds) > radius)) continue
			if(!RemasterWalkable(next, M) || (next in closed)) continue
			if(isnull(cost[next]) || cost[next] > cost[current] + 1)
				cost[next] = cost[current] + 1
				parent[next] = current
				if(!(next in open)) open += next
	return null

mob/Monsters/proc/RemasterApproach(datum/remaster_order/O, atom/A, reach)
	var/turf/goal = isturf(A) ? A : A.loc
	if(!isturf(goal))
		RemasterBlock("Target is no longer on the ground")
		return 0
	if(x != O.last_x || y != O.last_y)
		O.last_x = x
		O.last_y = y
		O.last_progress = world.time
	if(world.time - O.last_progress > max(100, Delay * 5))
		RemasterBlock("Path blocked; clear a route, then Resume", 1)
		return 0
	while(length(O.path) && O.path[1] == loc) O.path.Cut(1, 2)
	if(!length(O.path) || !RemasterWalkable(O.path[1], src)) O.path = RemasterOrderPath(src, goal, reach)
	if(!length(O.path))
		RemasterBlock("No clear route; choose a nearer target or Resume", 1)
		return 0
	destination = O.path[1]
	remaster_blocked = null
	remaster_order_status = "[O.kind]: travelling"
	return 1

Player/proc/RemasterOrdersTick()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src)
		M.RemasterDefenseTick()
		M.RemasterOrderTick()
	if(!client) return
	if(remaster_markers) for(var/image/I in remaster_markers) client.images -= I
	remaster_markers = list()
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
		remaster_job = "manual"
		if(!old_owner)
			remaster_role_paused = 0
			remaster_order_status = "Idle"

mob/verb/StopAll()
	for(var/mob/Monsters/M in Selected) if(M.Owner == src) M.RemasterStopOrders()
	return ..()
