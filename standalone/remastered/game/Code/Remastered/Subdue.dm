// Lethal or non-lethal, knock-outs, and capturing (Remastered).
//  - Every unit fights Lethal or Non-lethal: the toggle on the command bar, for the selected
//    units (saved). A non-lethal unit's melee blows are subdue blows: the weapon's damage
//    but never a killing blow, and a target brought down to about a third of its health
//    is knocked out: it lies down (3D: on its side with a "Zzz") for 30 seconds. Only these
//    deliberate blows, and Capture orders, knock anyone out. Non-lethal units don't shoot or
//    throw (that kills): they close in.
//  - Capture / Tame (right-click a creature, or click one that is knocked out): the selected
//    units fight non-lethal until it is knocked out, then the nearest one takes it. A person is
//    tied with a rope and led away by their captor, never joining by themselves: win them over or
//    enslave them, and they try to break free (Captives.dm); an animal is tamed at once.
//  - Dragons and grown spiders are too big to knock out by hand (webs, nets and chains will
//    be how, later).

#define RM_KO_TIME 300           // knocked out for 30 s
#define RM_KO_MARK 0.35          // at about a third of its health

mob/Monsters/var
	remaster_nonlethal = 0                   // saved: fights to knock out, never to kill
mob/Monsters/var/tmp
	remaster_ko_until = 0
	mob/Monsters/remaster_captive_lead       // the captor leading this captive on a rope
	remaster_ko_said = 0                     // "too big to knock out" said once
datum/remaster_attack/var/capture = 0        // a Capture / Tame order (Attack.dm)

mob/Monsters/proc/RemasterKnockedOut()
	return remaster_ko_until > world.time

// mob/Monsters/Move: this file's part is step RmChainMove_Subdue in Code/Remastered/Chains/Move.dm

proc/RemasterTooBigToKO(mob/Monsters/M)
	if(M.Race == "Dragon") return 1
	if(M.Race == "Spider" && RmBeastSize(M, "spider") >= 1.7) return 1
	return 0

// Does this unit fight M without killing it: non-lethal, or ordered to capture it.
mob/Monsters/proc/RemasterFightsNonLethal(mob/Monsters/M)
	return remaster_nonlethal || (remaster_attack && remaster_attack.capture && remaster_attack.target == M)

// A subdue blow (from RemasterStrike, Hits.dm): the weapon's damage (the flat of the blade, the
// haft), never taking the target below a tenth of its health, and a knock-out at about a third.
// The target may dodge, as in combat.
mob/Monsters/proc/RemasterSubdueBlow(mob/Monsters/M, ko = 1)     // ko = 0: a brawl's blow, which never knocks anyone out
	if(!istype(M) || M.HP <= 0 || M.GoingToDie || M.RemasterKnockedOut()) return
	M.RemasterThreatenedBy(src)
	GainEXP(2)
	if(!prob(clamp(70 + (RemasterCombatLevel(src, "Attack") - RemasterCombatLevel(M, "Defence")) / 2, 20, 95)))
		RemasterHit(M, 0, "miss", src)
		return
	DamageType()                       // the held weapon's damage, as Attack() sets it (Combats.dm)
	var/dmg = max(1, round((rand(WeaponDamageMin, WeaponDamageMax) + RmStr() / 2 + SkillDMG) * RmSwingDamage(src)))   // slower swings hit harder (Hits.dm)
	var/took = max(0, min(dmg, M.HP - max(1, round(M.MAXHP * 0.1))))
	M.HP -= took
	RemasterCombatXP("melee", took)
	if(RemasterTooBigToKO(M))
		RemasterHit(M, took, "hit", src)
		if(istype(Owner, /Player) && !M.remaster_ko_said)
			M.remaster_ko_said = 1
			Owner:RemasterNotice("[RemasterCombatName(M)] is too big to knock out by hand.")
		return
	if(ko && M.HP <= max(1, M.MAXHP * RM_KO_MARK)) M.RemasterKnockOut(src)
	else RemasterHit(M, took, "hit", src)

mob/Monsters/proc/RemasterKnockOut(mob/Monsters/by)
	remaster_ko_until = world.time + RM_KO_TIME
	Fainted = 1
	destination = null
	Target = null
	remaster_attack = null
	RemasterHit(src, 0, "ko", by)
	RmKoDrop(src)   // it lets go of its weapon (Gear3D.dm)
	view(src) << "[src] is knocked out!"
	var/Player/P = by ? by.Owner : null
	if(istype(P)) P.RemasterNotice("[RemasterCombatName(src)] is knocked out: click [Critter ? "it to tame it" : "them to capture them"]. They wake in 30 s.")
	if(istype(Owner, /Player) && Owner != P) Owner:RemasterNotice("[RemasterBareName()] was knocked out[by ? " by [RmKillerName(by, Owner)]" : ""]: they wake in [RM_KO_TIME / 10] s.")
	spawn(RM_KO_TIME + 1) if(src) RemasterWakeUp()

mob/Monsters/proc/RemasterWakeUp()
	if(!remaster_ko_until || world.time < remaster_ko_until) return
	remaster_ko_until = 0
	if(HP > 0 && !GoingToDie) Fainted = 0
	RmKoRetake(src)   // its weapon back, if it still lies where it fell (Gear3D.dm)
	if(HP > 0) view(src) << "[src] comes to."

// Why C can never take T captive (whatever the distance or state), or null.
proc/RemasterCapturable(mob/Monsters/C, mob/Monsters/T)
	if(!istype(T) || T == C || T.HP <= 0 || T.GoingToDie || !isturf(T.loc)) return "There is no one to capture."
	if(RemasterIsSiege(T) || T.Wagon || T.Egg || T.CantKill || istype(T, /mob/Monsters/Chests)) return "That can't be captured."
	if(T.rm_cap_state) return "[T.RemasterBareName()] is already a captive."
	if(T.IsRoyal) return "A ruler cannot be captured."
	if(T.Owner == C.Owner) return "That is one of your own."
	var/datum/rm_fort_try/FT = RmTryPair(C, T)   // a fort try: captives only where its maker allows them (QuestForts.dm)
	if(FT && !FT.captives) return "No captives are taken in this fort."
	if(!RemasterHostile(C, T, 1)) return istype(T.Owner, /Player) ? "You are at peace with them." : "You can't capture that."
	if(RemasterTooBigToKO(T) && !T.RemasterSubdued()) return "[RemasterCombatName(T)] is too big to knock out by hand."
	return null

// Capture / Tame: the selected units fight non-lethal until T is knocked out, then the nearest
// takes it (RemasterAttackTick, Attack.dm).
Player/proc/RemasterCaptureOrder(mob/Monsters/E)
	if(!istype(E)) return 0
	var/n = 0
	var/why
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || M.HP <= 0 || RemasterIsSiege(M) || M.Wagon) continue
		var/w = RemasterCapturable(M, E)
		if(w)
			why = w
			continue
		M.RemasterCancelOrders()
		if(M.remaster_defense) M.RemasterCancelDefense(0)
		M.RemasterCareInterrupt()
		M.RemasterWake()
		M.remaster_patrol = null
		var/datum/remaster_attack/K = new
		K.issuer = src
		K.target = E
		K.chosen = E
		K.capture = 1
		K.last_position = M.loc
		K.last_progress = world.time
		M.remaster_attack = K
		M.remaster_order_status = "[E.Critter ? "Taming" : "Capturing"] [RemasterCombatName(E)]"
		n++
	remaster_attack_mode = 0
	if(n) RemasterNotice("[E.Critter ? "Tame" : "Capture"]: [n] [E.RemasterSubdued() ? "go to take" : "go to knock out and take"] [RemasterCombatName(E)].")
	else RemasterNotice(why || "Select units to capture with.")
	return n

// The capture-order part of an attack tick: 1 when it handled this tick.
mob/Monsters/proc/RemasterCaptureTick(datum/remaster_attack/K, mob/Monsters/E)
	if(!E || RemasterIsSiege(E) || !(K.capture || remaster_nonlethal)) return 0
	if(E.RemasterSubdued())
		if(!K.capture)
			// a non-lethal fight is over once it's down
			K.target = null
			if(!K.goal) RemasterAttackStop()
			remaster_order_status = "Knocked out [RemasterCombatName(E)]"
			return 1
		if(get_dist(src, E) <= 1)
			destination = null
			var/Player/P = K.issuer
			var/name = RemasterCombatName(E)
			if(P.RemasterCapture("[RemasterUIRef(src)]|\ref[E]"))
				for(var/mob/Monsters/O in P.UnitList) if(O.remaster_attack && O.remaster_attack.target == E && O.remaster_attack.capture) O.RemasterAttackStop()
				remaster_order_status = E && E.Critter ? "Tamed [name]" : "Captured [name]"
			else RemasterAttackStop()
			return 1
		if(!RemasterAttackApproach(E.loc, 1, 1)) RemasterAttackStop()
		return 1
	// hand to hand only: shots and throws kill
	RemasterBowToMelee(1)   // a bow strikes no blow: a carried blade or fists, the bow back after (Formations.dm)
	if(get_dist(src, E) <= 1)
		destination = E
		K.last_progress = world.time
		remaster_order_status = "[K.capture ? "Subduing" : "Fighting non-lethal:"] [RemasterCombatName(E)]"
	else if(!RemasterAttackApproach(E.loc, 1, E == K.chosen))
		K.target = null
		K.path = null
		if(!K.goal) RemasterAttackStop()
	return 1

// Lethal / Non-lethal for the selected units: all non-lethal unless they all already are.
Player/proc/RemasterLethalToggle()
	var/list/U = list()
	var/off = 0
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && !M.Wagon && !RemasterIsSiege(M))
		U += M
		if(!M.remaster_nonlethal) off = 1
	if(!length(U))
		RemasterNotice("Select units first.")
		return 0
	for(var/mob/Monsters/M in U) M.remaster_nonlethal = off
	RemasterNotice(off ? "Non-lethal: [length(U)] will knock enemies and animals out instead of killing them (no shooting or throwing)." : "Lethal: [length(U)] fight to kill again.")
	return 1

// Lethal / Non-lethal for one unit (the Combat tab of its card).
Player/proc/RemasterUnitLethal(mob/Monsters/M, on)
	if(!istype(M) || M.Owner != src || M.Wagon || RemasterIsSiege(M)) return 0
	M.remaster_nonlethal = on ? 1 : 0
	RemasterNotice(on ? "[M.RemasterBareName()] fights non-lethal: knocks enemies and animals out instead of killing them (no shooting or throwing)." : "[M.RemasterBareName()] fights to kill again.")
	return 1

// From RemasterTrack (QoL.dm). Captives on a rope follow their leader in Captives.dm's own loop.
Player/proc/RemasterCaptiveTick()
	RemasterCarryTick()          // people your units carry (TargetActions.dm)
