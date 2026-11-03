// Ordinary wounds, own means first (the user, 2026-10-26: "Bandage itself while up"): a unit bleeding badly from its wounds
// (no stump; Health.dm's "Badly" or worse, where its bleeding rolls can kill) uses what it carries on itself at once while
// it is on its feet: a bandage, an Athelas poultice, a torch (it hurts), a healing draught or the Elixir of Life, cheapest
// first. That stops the bleeding as the original's own stop does (Health.dm). With nothing of its own it calls for help
// once: a friend within 3 tiles with something for it does it at once, else the nearest free one who carries something
// walks over. Down (bleeding out or knocked out) it never treats itself (BleedOut.dm). Stumps keep their own care
// (Stumps.dm RemasterStumpCare).
var/list/rm_wound_bad = list("Badly", "Very Badly", "Extremly")
mob/Monsters/var/tmp/rm_wound_called = 0   // it called for help for this wound (once)

mob/Monsters/proc/RmWoundBad()
	return (BleedType in rm_wound_bad) && !rm_dying_until && !RemasterStumpBleeding() && HP > 0 && !GoingToDie

// What the holders carry that stops a wound's bleeding, cheapest first, for hand to use.
mob/Monsters/proc/RmWoundMeans(list/holders, mob/Monsters/hand)
	. = list()
	for(var/k in list("bandage", "poultice", "torch", "healing", "elixir"))
		var/obj/Items/best
		for(var/mob/Monsters/M in holders)
			if(best) break
			for(var/obj/Items/I in M)
				if(I.suffix != "(Carrying)") continue
				switch(k)
					if("bandage") if(istype(I, /obj/Items/RemasterBandage)) best = I
					if("poultice") if(istype(I, /obj/Items/RemasterRemedy) && I:remedy == "poultice") best = I
					if("torch") if(istype(I, /obj/Items/RemasterTorch)) best = I
					if("healing") if(istype(I, /obj/Items/Potions/RemasterBrew) && I:brew && I:brew["healing"] >= 5) best = I
					if("elixir") if(istype(I, /obj/Items/Potions/RemasterBrew) && I:brew && I:brew["elixir"]) best = I
				if(best) break
		if(best) . += list(list("kind"=k, "item"=best, "by"=hand))

mob/Monsters/proc/RmWoundTreat(list/O, Player/P)
	var/obj/Items/I = O["item"]
	var/mob/Monsters/by = O["by"]
	if(!I || Rm3DGone(I) || !ismob(I.loc)) return 0
	switch(O["kind"])
		if("bandage") RmStumpUseUp(I)
		if("torch")
			I:rm_burns--
			if(I:rm_burns <= 0) RmStumpUseUp(I)
			else I.desc = "[initial(I.desc)] [I:rm_burns] searing\s left."
			HP = max(1, HP - 10)   // searing hurts
		if("poultice")
			if(!RemasterApplyRemedy("poultice", by)) return 0
			RmStumpUseUp(I)
		if("healing", "elixir")
			if(!istype(P)) return 0
			var/mob/Monsters/holder = I.loc
			if(holder != src && !RemasterHandOver(I, holder, src)) return 0
			P.RemasterDrinkBrew(src, I)
	if(RemasterBleedStops()) BloodContent = MaxBloodContent   // as the original's own stop (Health.dm): its blood back, unless it is coming back slowly
	BleedType = null
	SaidBleed = 0
	rm_wound_called = 0
	remaster_care_note = by == src ? "Bound its own wound" : "[by.RemasterBareName()] bound its wound"
	return 1

// At once, as its blood drops (Combats.dm BloodLoss sets how badly it bleeds): its own means, while on its feet. A tick
// later, so a cut that takes a limb off (Wounds.dm RmSever: BloodLoss, then LimbLoss) is seen to as the stump it leaves.
mob/Monsters/BloodLoss()
	. = ..()
	if(RmWoundBad()) spawn(1) if(!Rm3DGone(src) && RmWoundBad()) RmWoundSelf(istype(Owner, /Player) ? Owner : null)

mob/Monsters/proc/RmWoundSelf(Player/P)
	if(!RemasterAutoUseOn("stump") || !RemasterStumpCanTreat()) return 0
	for(var/list/O in RmWoundMeans(list(src), src)) if(RmWoundTreat(O, P)) return 1
	return 0

// The care pass (Stumps.dm RemasterStumpCare, for its owner's units): its own means, else one call; and one who answered,
// walking over.
mob/Monsters/RemasterStumpCare(Player/P)
	if(remaster_care == "woundhelp") return RmWoundHelpStep(P)
	. = ..()
	if(. || remaster_care) return
	if(!RmWoundBad() || !isturf(loc))
		rm_wound_called = 0   // seen to: its next wound calls again
		return 0
	if(RmWoundSelf(P)) return 1
	if(rm_wound_called) return 0
	rm_wound_called = 1
	var/list/hands = list()
	var/list/holders = list()
	RemasterStumpNear(hands, holders)
	hands -= src
	if(length(hands)) for(var/list/O in RmWoundMeans(holders, hands[1])) if(RmWoundTreat(O, P)) return 1
	var/mob/Monsters/H = P.RmWoundHelper(src)
	if(H)
		H.RemasterCareStart("woundhelp", src, loc, "Going to bind [name]'s wound")
		remaster_care_note = "Bleeding: called for help, [H.name] is coming"
		return 0
	remaster_care_note = "Bleeding: called for help and no one could come (a bandage, a poultice or a torch)"
	return 0

// The nearest villager free to come who carries something for it (as Stumps.dm RemasterStumpHelper).
Player/proc/RmWoundHelper(mob/Monsters/H)
	var/mob/Monsters/best
	var/best_d = 21
	for(var/mob/Monsters/M in UnitList)
		if(M == H || M.Owner != src || M.remaster_care || M.Wagon || M.Egg || M.Critter || M.HP <= 0 || M.z != H.z || !isturf(M.loc)) continue
		if(M.remaster_job == "doctor" || M.Target || M.remaster_defense || world.time < M.remaster_care_hold || !M.CanWalk || !M.RemasterStumpCanTreat()) continue
		if(M.RemasterHasOrder() && !(M.remaster_active && M.remaster_active.automatic)) continue
		var/d = get_dist(M, H)
		if(d >= best_d || !length(H.RmWoundMeans(list(M), M))) continue
		best = M
		best_d = d
	return best

mob/Monsters/proc/RmWoundHelpStep(Player/P)
	var/mob/Monsters/H = remaster_care_target
	if(HP <= 0 || GoingToDie || Fainted || Stunned || Sleeping || !isturf(loc))
		RemasterCareDone()
		return 0
	if(!istype(H) || Rm3DGone(H) || H.HP <= 0 || H.GoingToDie || H.z != z) return RemasterCareDone() || 1
	if(!H.RmWoundBad()) return RemasterCareDone("[H.name]'s wound is seen to") || 1
	if(world.time - remaster_care_since > REMASTER_CARE_GIVE_UP) return RemasterCareDone("Gave up: couldn't reach [H.name]") || 1
	if(get_dist(src, H) <= 1)
		var/done = 0
		for(var/list/O in H.RmWoundMeans(list(src), src)) if(H.RmWoundTreat(O, P))
			done = 1
			break
		RemasterCareDone(done ? "Bound [H.name]'s wound" : "Had nothing for [H.name]'s wound")
		return 1
	if(destination != H.loc)
		destination = H.loc
		remaster_care_dest = H.loc
	return 1
