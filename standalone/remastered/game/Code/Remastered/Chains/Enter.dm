// turf/grounds/Enter: one chain, in the order DM ran it when it was spread over 5 files (cleanup, from
// chains.py). The call runs Doors > Clip > Flying > WallWalks > TurfTypes. Since step-cost (10-27) the 5 steps are this
// one proc, with no call and no args list between them: each step's part below in this order, the first of Flying,
// WallWalks and TurfTypes that answers giving the answer (each returned before the next one down), then Clip's end.
// Add a feature's part as a new step at its place in this order, never as another override elsewhere.
// Mirrored in the engine for plain tiles (engine/native/RmStep.cs, the plain step): change both together; RM_STEP_VERIFY=1
// logs any step that differs.
turf/grounds/Enter(atom/movable/m)
	// step 1 of 5: Doors (was Code/Remastered/Doors.dm:62, RmChainEnter_Doors)
	// Every step into a door's tile, whoever's step it is. The ground's own rule (Building/TurfTypes.dm) stops a unit only on
	// its own steps (usr: an order, guard duty); a step on a rope, a work walk or a creature's wander has someone else's usr
	// or none, and went through shut doors, locked ones and enemies' too. Now a shut door stops every unit that isn't its
	// owner's (an ally's, an enemy's, a wild creature's), and a locked one stops everyone; its owner's units open it as they
	// step in. Until the route search knows the rule (rm_own_doors off), a shut door stops its owner's units too, on every
	// walk, as the search plans: no step goes through a door its route says won't open. Flyers and mist pass as before.
	// It looks only on a tile that counts a placed door (Doors.dm rm_door_n, step-cost 10-27).
	if(rm_door_n)
		if(istype(m, /mob/Monsters) && m.density && !m:Flying && !m:IsMist)
			var/obj/Items/Furniture/Doors/D = locate() in src
			if(D && D.Placed && D.density && !istype(D, /obj/Items/Furniture/Doors/TrapDoor))
				if(!rm_own_doors || !RmOwnDoor(D, m)) return 0
				RmDoorOpen(D)
	else if(rm_step_scan_check && istype(m, /mob/Monsters) && m.density && !m:Flying && !m:IsMist) RmStepScanDoor(src, m)

	// step 2 of 5: Clip (was Code/Remastered/Clip.dm:63, RmChainEnter_Clip), its start: the units it goes through aren't
	// dense for the steps below; its end, the last part, makes them dense again
	// A unit on its way into a tile that holds only units of its side goes through them, unless its route ends there. The
	// ground's own rules (Building/TurfTypes.dm, WallWalks.dm, Flying.dm) still apply: those units just don't count.
	var/list/clip
	if(usr == m && (!density || RmSwimWater(src)) && istype(m, /mob/Monsters) && m.density && !m:Flying)
		var/list/side = RmSide(m)
		if(side)
			for(var/atom/movable/A in src) if(A != m && A.density)
				if(!RmSideUnit(A, side))
					clip = null
					break
				if(!clip) clip = list()
				clip += A
			if(clip)
				var/list/L = m:RmRouteInto(src)
				var/datum/remaster_order/HO = m:remaster_active
				if(!(HO && HO.kind == "Hop" && HO.target == src) && (length(L) <= 1 || !RmClipLands(L, m, L[length(L)], side))) clip = null   // (the top a hop goes down from: onto its own people there, and straight down; a builder on a building's second step and two on its first waited for each other for good: the real game 10-30)
				else
					for(var/atom/movable/A in clip) A.density = 0

	// step 3 of 5: Flying (was Code/Remastered/Flying.dm:42, RmChainEnter_Flying)
	// The game's ground rule (Building/TurfTypes.dm: every map turf is a /turf/grounds) keeps
	// units off dense tiles and tiles holding something dense; a flyer goes over both.
	if(RmFliesOver(m, src)) . = 1
	// step 4 of 5: WallWalks (was Code/Remastered/WallWalks.dm:332, RmChainEnter_WallWalks)
	else if(remaster_wallwalk && istype(m, /mob/Monsters)) . = RemasterWalkRoom(src, m)
	// step 5 of 5: TurfTypes (was Code/Building/TurfTypes.dm:2, RmChainEnter_TurfTypes): the original's ground rule, for a
	// step under a usr that isn't a player's mob; no answer (null) stops the step
	else if(!usr || usr.key) . = 1
	else if(icon_state == "GoodGrass" && (usr.Infects || usr.Undead || usr.Unholy || usr.Race == "Svartalfar" || usr.Race == "Demon"))
		if(!density)
			density = 1
			spawn() density = 0
	else if(m.IsMist) . = 1
	else if(!density || (RmSwimWater(src) && RmSwims(m)))   // deep water: a swimmer goes in as onto open ground (Swim.dm; the engine's plain step leaves water to this)
		. = 1
		for(var/atom/M in src) if(M.density) if(m.density)
			. = null
			break

	// step 2 of 5: Clip, its end
	if(clip) for(var/atom/movable/A in clip) A.density = 1
