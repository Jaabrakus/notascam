// Warn before ordering the impossible: when the mouse rests on something with
// units selected, say what the order would be and who can't do it (other
// layer, missing tool, no route). Same rules the order itself uses.

Player/var/tmp
	list/remaster_hover            // verdict shown by the HUD
	remaster_hover_key
	remaster_hover_at = 0

mob/Monsters/proc/RemasterToolFor(kind)
	if(kind == "Chop" && UsesPicks && Race != "Goblin" && !Werepowers && !VampPick) return "Axe"
	if(kind == "Mine" && UsesPicks && !Werepowers && !VampPick) return "Pickaxe"
	return null

mob/Monsters/proc/RemasterHasTool(tool)
	if(!tool || HoldingWeapon == tool) return 1
	for(var/obj/Items/E in src) if(E.ItemType == tool && E.suffix == "(Carrying)" && E.icon != 'DemonicItems.dmi') return 1
	return 0

Player/proc/RemasterHoverVerdict(atom/A)
	if(!A || !A.z || !length(Selected)) return null
	// a fishing spot (Fishing.dm): a click has the selected fish it from the shore (QoL.dm); it said "Move" (rts-feel)
	if(RemasterGathering() && (istype(A, /obj/RemasterFishSpot) || (isturf(A) && (locate(/obj/RemasterFishSpot) in A)))) return list("kind"="Fish", "text"="Fish", "ok"=1, "bad"=0)
	if(isobj(A) && !istype(A, /obj/Items) && isturf(A.loc)) A = A.loc
	// a workshop (or its part): a click opens its menu (QoL.dm client/Click → RemasterButton)
	if(istype(A, /mob/WorkShops)) return list("kind"="Use", "text"="Open", "ok"=1, "bad"=0)
	var/kind = RemasterPointerKind(A)     // with the Gather switch (Gather.dm)
	var/turf/T = RemasterGetTurf(A)
	if(!kind)
		if(istype(A, /mob/Monsters) && A:Owner != src && A:HP > 0)
			kind = "Attack"
			// knocked out: a click takes it; non-lethal units knock out instead (Subdue.dm)
			var/mob/Monsters/F = Selected[1]
			if(istype(F) && !RemasterCapturable(F, A))
				if(A:RemasterSubdued()) return list("kind"="Capture", "text"=A:Critter ? "Tame" : "Capture", "ok"=1, "bad"=0)
				var/soft = 1
				for(var/mob/Monsters/M in Selected) if(M.Owner == src && !M.remaster_nonlethal) soft = 0
				if(soft) return list("kind"="Knock out", "text"="Knock out (non-lethal)", "ok"=1, "bad"=0)
		else return list("kind"="", "text"="Nothing to do there", "ok"=0, "bad"=1)
	if(A.Owner && A.Owner != src && kind != "Attack" && kind != "Move") return list("kind"=kind, "text"="Belongs to someone else", "ok"=0, "bad"=1)
	var/ok = 0
	var/checked = 0
	var/list/problems = list()
	var/bad = 0
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || !(M in UnitList) || M.Wagon || M.HP <= 0) continue
		if(++checked > 6) break
		if(rm_nav_count)   // counted (Native.dm, navigation plan N0); a unit on another layer looks for stairs and hops instead
			RmNavCount(M.z != T.z ? "hover: unit on another layer" : "hover: unit")
			rm_path_who = "hover"
		// Units always go; these are only how (Orders.dm).
		var/why
		if(kind == "Move" && RmSkyOpenFor(src, T) && !M.Flying) why = "can't fly, stays"   // open sky: flyers only (Flying.dm)
		else if(M.z != T.z) why = RemasterStairsTowards(M, T) ? "takes the stairs" : RemasterHopSpot(M, T) ? "hops down" : (RemasterCanClimb(M) && RemasterClimbSpot(M, T)) ? "climbs the cliff" : "no stairs to that level nearby"
		else
			var/tool = M.RemasterToolFor(kind == "Dig down" ? "Mine" : kind)
			if(tool && !M.RemasterHasTool(tool)) why = "no [lowertext(tool)]: by hand, slowly"
			else if(get_dist(M, T) > 1 && !RemasterOrderPath(M, T, kind == "Move" && !T.density ? 0 : 1)) why = "may not get through: goes as close as it can"
		// grouped by reason, so a selection gives one short line ("3 units: may not get through ..."), not one per unit
		if(why)
			if(!problems[why]) problems[why] = list()
			problems[why] += M.name
		if(why == "no stairs to that level nearby" || why == "can't fly, stays") bad++
		else ok++
	if(rm_nav_count) rm_path_who = null   // a unit above that didn't search leaves no name for the next search
	var/text = (kind == "Move" && T && T.density && RemasterOnlyFlyers()) ? "Fly on top" : kind
	if(kind == "Move" && RmSkyOpenFor(src, T)) text = ok ? "Fly there" : "Only flyers can go out over open sky"
	if(kind == "Move" && !RemasterGathering() && (RemasterClickKind(A) in list("Mine", "Chop"))) text = "Move" + " · " + "Gather is off (G to [lowertext(RemasterClickKind(A))])"   // Gather.dm (no · in a string with [] in it)
	var/list/lines = list()
	for(var/why in problems)
		var/list/who = problems[why]
		lines += length(who) == 1 ? "[who[1]]: [why]" : "[length(who)] units: [replacetext(replacetext(why, "goes as close as it can", "they go as close as they can"), "by hand, slowly", "they work by hand, slowly")]"
	if(length(lines)) text += " · " + jointext(lines.Copy(1, min(3, length(lines) + 1)), " · ")
	// digging near open tunnels with no pillar holding them up (Mountains.dm)
	if(kind == "Mine" && RemasterCaveInRisk(T)) text += " · no pillar within 4 tiles: cave-ins possible"
	return list("kind"=kind, "text"=text, "ok"=ok, "bad"=bad)

// From the 3D view ("x|y|ref") and from the map (client/MouseEntered).
Player/proc/RemasterHoverAt(atom/A)
	var/key = "\ref[A]|[length(Selected)]|[A ? A.x : 0],[A ? A.y : 0]"
	if(key == remaster_hover_key && world.time - remaster_hover_at < 20) return
	remaster_hover_key = key
	remaster_hover_at = world.time
	remaster_hover = A ? RemasterHoverVerdict(A) : null
	// where the verdict is for, so the page's pointer and ring trust it only over that spot (remastered.html rfPredict)
	if(remaster_hover)
		remaster_hover["x"] = A.x
		remaster_hover["y"] = A.y
		remaster_hover["on"] = isturf(A) ? "tile" : "thing"
		remaster_hover["g"] = remaster_gather   // the Gather switch it was worked out with (the page drops it once that changes)

client/MouseEntered(object, location, control, params)
	if(istype(mob, /Player) && control == "mapwindow.map" && istype(object, /atom) && !istype(object, /obj/Hud) && !istype(object, /obj/HUD))
		mob:RemasterHoverAt(object)
	return ..()
