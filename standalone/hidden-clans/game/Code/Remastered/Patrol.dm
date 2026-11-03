// Patrol routes: press Patrol with units selected, click points (map or 3D),
// press Finish. The units walk the route as a loop of ordinary Move orders,
// queued again whenever they run out, so fights and self-care interrupt it
// like any other work. (The original two-point guard Patrol is unchanged.)

Player/var/tmp/list/remaster_patrol_draft     // turfs clicked so far, or null
mob/Monsters/var/list/remaster_patrol          // list of "x,y,z"; saved with the unit

Player/proc/RemasterPatrolCommand(action)
	switch(action)
		if("patrolstart")
			if(!length(Selected))
				RemasterNotice("Select the units that should patrol first.")
				return 0
			remaster_patrol_draft = list()
			RemasterNotice("Click the patrol points in order, then press Finish.")
			return 1
		if("patrolcancel")
			remaster_patrol_draft = null
			RemasterNotice("Patrol route cancelled.")
			return 1
		if("patrolfinish")
			var/list/D = remaster_patrol_draft
			remaster_patrol_draft = null
			if(length(D) < 2)
				RemasterNotice("A patrol needs at least two points.")
				return 0
			var/list/route = list()
			for(var/turf/T in D) route += "[T.x],[T.y],[T.z]"
			var/n = 0
			for(var/mob/Monsters/M in Selected) if(M.Owner == src && (M in UnitList) && !M.Wagon)
				M.remaster_patrol = route.Copy()
				M.RemasterCancelOrders()
				n++
			RemasterNotice("[n] unit[n == 1 ? "" : "s"] patrolling [length(route)] points.")
			RemasterLog("[n] unit[n == 1 ? "" : "s"] set to patrol [length(route)] points", "work", D[1])
			return 1
		if("patrolclear")
			var/n = 0
			for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.remaster_patrol)
				M.remaster_patrol = null
				M.RemasterCancelOrders()
				n++
			RemasterNotice(n ? "Patrol stopped for [n] unit[n == 1 ? "" : "s"]." : "None of the selected units are patrolling.")
			return 1
	return 0

// While drafting, clicks on the ground add points instead of giving orders.
Player/proc/RemasterPatrolClick(atom/A)
	if(!islist(remaster_patrol_draft)) return 0
	var/turf/T = RemasterGetTurf(A)
	if(!T || T.density)
		RemasterNotice("Patrol points go on open ground.")
		return 1
	var/level = 0
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.z == T.z) level = 1
	if(!level)   // the patrol tick walks only the points on a unit's own level: one elsewhere was taken, then never walked
		RemasterNotice("That point is on another level from the units: patrol points go on their own level.")
		return 1
	if(length(remaster_patrol_draft) >= 12)
		RemasterNotice("Up to 12 patrol points.")
		return 1
	remaster_patrol_draft += T
	RemasterNotice("Patrol point [length(remaster_patrol_draft)] at [T.x], [T.y]. Keep clicking, or press Finish.")
	return 1

// Units with a route and nothing to do queue the whole route again (and OfflineGuards.dm's world loop while their owner
// is away).
Player/proc/RemasterPatrolTick()
	for(var/mob/Monsters/M in UnitList) if(M.remaster_patrol) M.RemasterPatrolNext(src)

mob/Monsters/proc/RemasterPatrolNext(Player/P)
	if(Owner != P || !remaster_patrol || HP <= 0 || !isturf(loc)) return
	if(RemasterHasOrder() || remaster_defense || remaster_attack || remaster_care || remaster_give_item || remaster_take) return
	if(!remaster_orders) remaster_orders = list()
	for(var/key in remaster_patrol)
		var/list/c = splittext(key, ",")
		var/turf/T = locate(text2num(c[1]), text2num(c[2]), text2num(c[3]))
		if(!T || T.z != z) continue
		var/datum/remaster_order/O = new
		O.issuer = P
		O.target = T
		O.kind = "Move"
		O.automatic = 1
		remaster_orders += O
	RemasterOrderTick()

Player/proc/RemasterPatrolData()
	var/list/pts = list()
	if(islist(remaster_patrol_draft)) for(var/turf/T in remaster_patrol_draft) pts += list(list(T.x, T.y, T.z))
	return islist(remaster_patrol_draft) ? list("points"=pts) : null
