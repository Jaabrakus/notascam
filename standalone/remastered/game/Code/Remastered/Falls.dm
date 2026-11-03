// Every fall can be saved (the user, 2026-10-26, asked how a lethal fall should work: "Every fall can be saved
// (Recommended)": a unit brought down falls dying and has 60 s to be saved; asked who finishes a downed unit: "Lethal
// units do it": units on Lethal finish any downed foe next to them once no standing foe is left to fight nearby).
//  - A blow, shot or throw that would kill a unit downs it instead, dying as one bleeding out (BleedOut.dm), for 60 s:
//    a friend or the Doctor saves it as they would one bleeding out; unsaved, it dies. A blow on one dying kills it.
//  - Not spared: a head lost, the undead, animals and great beasts, siege engines, and deaths no foe dealt (starving,
//    old age, a fever...).
//  - A unit on Lethal beside a downed foe (dying, or knocked out by someone not of its side) finishes it once no standing
//    foe of its is within rm_finish_clear tiles. Units on Non-lethal, and those capturing it, never do.
//  - Its own seeing it fall lose their morale then, not again when it dies (Morale.dm).
// The owner, 10-27: "we just revert back to the old ways deaths happen but with our upgraded combats we just remove the
// bleeding" - "the 60 second bleeding": a killing blow kills at once again. The switch stays for tests (1 = the fall).
var/rm_falls_on = 0          // 0: a killing blow kills at once, as before
var/rm_finish_on = 1         // 0: no one finishes a downed foe on their own
var/rm_finish_clear = 5      // tiles round the finisher with no standing foe
mob/Monsters/var/tmp/rm_fall_spared = 0   // falls it was spared (and its own felt it then)
mob/Monsters/var/tmp/rm_ko_side           // the owner of whoever knocked it out: their side never finishes it
mob/Monsters/var/tmp/rm_finished = 0      // the finishing blow: it dies
mob/Monsters/var/tmp/rm_finishes = 0      // downed foes it finished (checks)
mob/Monsters/var/tmp/mob/rm_fall_by       // whose shot, throw or move kills it this tick, where Killer is only a name
mob/Monsters/var/tmp/rm_fall_at = -1

// A shot, throw or weapon move's killing hit (Combat - Bows.dm, Throwing.dm, WeaponSkills.dm), which names its killer as
// text: it falls dying as from a blow (polish 10-26: those killed at once, though the owner's rule spares them too).
mob/Monsters/proc/RmFallBy(mob/by)
	rm_fall_by = by
	rm_fall_at = world.time

proc/RmFallSpares(mob/Monsters/M)
	if(!rm_falls_on || !istype(M) || !M.GoingToDie || M.rm_finished || M.rm_dying_until) return 0
	if(M.DeathType == "Bleeding To Death") return 0   // the end of the 60 s (BleedOut.dm), or bleeding out with it off
	if(M.key || M.CantKill || M.Wagon || M.Critter || M.Undead || !M.HasHead || RemasterIsSiege(M) || RmBeastKind(M)) return 0
	return isturf(M.loc) && ((ismob(M.Killer) && M.Killer != M) || (ismob(M.rm_fall_by) && M.rm_fall_by != M && M.rm_fall_at == world.time))

// mob/Monsters/Death: this file's part is step RmChainDeath_Falls in Code/Remastered/Chains/Death.dm

// Morale.dm's "fell beside them", at the fall.
proc/RmFallMorale(mob/Monsters/M)
	if(!rm_morale_on || !rm_morale_group) return
	var/leader = M.IsRoyal || (M.RmNPCRole() in list("commander", "boss"))
	var/n = leader ? rm_morale_loss["leader"] : rm_morale_loss["death"]
	var/nm = M.RemasterBareName()
	for(var/mob/Monsters/O in RmUnitsNear(leader ? 6 : 4, M)) if(O != M && O.Owner == M.Owner && !isnull(O.rm_morale))
		O.RmMoraleAdd(-n, 1, ": [nm] fell[leader ? "" : " beside them"]")

mob/Monsters/RemasterKnockOut(mob/Monsters/by)
	rm_ko_side = by ? by.Owner : null
	. = ..()
	if(rm_finish_on) spawn(10) RmKOFinishLoop(src)
	RmDownLeft(src)

proc/RmKOFinishLoop(mob/Monsters/M)
	while(M && M.RemasterKnockedOut() && !M.rm_dying_until && M.HP > 0 && !M.GoingToDie)
		if(RmFinishOff(M)) return
		sleep(10)

// A Lethal foe beside the downed M with no standing foe of its near finishes it (BleedOut.dm's loop, the one above).
proc/RmFinishOff(mob/Monsters/M)
	if(!rm_finish_on || !istype(M) || !isturf(M.loc) || M.HP <= 0 || M.GoingToDie) return 0
	for(var/mob/Monsters/F in orange(1, M))
		if(F.HP <= 0 || F.GoingToDie || F.Fainted || F.Sleeping || F.RemasterSubdued() || F.Critter || F.Wagon || RemasterIsSiege(F)) continue
		if(F.rm_cap_state || F.RemasterFightsNonLethal(M)) continue
		if(!M.rm_dying_until && M.rm_ko_side && M.rm_ko_side == F.Owner) continue   // its own side knocked it out
		if(!RemasterHostile(F, M, 1)) continue
		if(M.z == SKY_LAYER && !F.RemasterStepSpot(M.loc)) continue   // up on the rock: no step at it, no blow (Gather.dm)
		if(RmStandingFoeNear(F)) continue
		M.rm_finished = 1
		M.rm_dying_until = 0
		F.rm_finishes++
		F.dir = get_dir(F, M)
		F.rm_swung_at = world.time   // its swing in 3D; no hit on the body, which keeps the pose it fell in (the owner, via the
		                             // coordinator: "the final animation frame of the death or knock out ... is the final pose")
		M.HP = 0
		M.GoingToDie = 1
		M.DeathType = "Finished off"
		M.Killer = F
		view(M) << "<b><font color=red>[F.RemasterBareName()] finishes off [M.RemasterBareName()].</font></b>"
		M.Death()
		return 1
	return 0

proc/RmStandingFoeNear(mob/Monsters/F)
	for(var/mob/Monsters/O in RmUnitsNear(rm_finish_clear, F))
		if(O == F || O.HP <= 0 || O.GoingToDie || O.Fainted || O.Sleeping || O.RemasterSubdued() || RemasterIsSiege(O)) continue
		if(O.Critter && O.Target != F) continue
		if(O.rm_cap_state && O.rm_cap_strike_until <= world.time) continue   // a captive, not rising (Captives.dm)
		if(RemasterHostile(F, O, 1)) return 1
	return 0

// Down (bleeding out, knocked out, fainted) is out of the fight while a standing foe is near: as the finisher above waits
// for none to stand near, attack orders, attack-moves and attack boxes (Attack.dm, Formations.dm) and the creatures' own
// AI (Monster AI.dm LocateTarget) go for a standing foe instead of striking the one down (polish 10-26: they hacked at
// the fallen while foes stood by, so no friend could save it). With no standing foe near they go on as before.
proc/RmDownOut(mob/Monsters/E)
	return istype(E) && (E.Fainted || E.rm_dying_until || E.RemasterKnockedOut())

// E just went down: those fighting it on their own AI (no order, not defending) leave it while a foe stands near them.
proc/RmDownLeft(mob/Monsters/E)
	if(!rm_finish_on || !istype(E) || !isturf(E.loc)) return
	for(var/mob/Monsters/F in orange(2, E))
		if(F.remaster_attack || F.remaster_defense || (F.destination != E && F.Target != E) || !RmStandingFoeNear(F)) continue
		if(F.destination == E) F.destination = null
		if(F.Target == E) F.Target = null
