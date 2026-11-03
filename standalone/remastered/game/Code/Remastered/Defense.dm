// An attack may temporarily borrow a worker; its task objects and cargo stay put.
// Hearing is a square radius, independent of facing and line of sight.
#define REMASTER_HELP_RADIUS 8

datum/remaster_defense
	var/Player/issuer
	var/mob/Monsters/attacker
	var/mob/Monsters/caller
	var/turf/origin
	var/turf/anchor
	var/phase = "Responding"
	var/expires
	var/list/path
	var/turf/path_goal
	var/next_shot = 0
	var/atom/previous_destination
	var/previous_status
	var/last_position
	var/last_progress

mob/Monsters
	var/remaster_defense_mode = "assist"
	var/tmp/datum/remaster_defense/remaster_defense
	var/tmp/remaster_help_ready = 0
	var/tmp/remaster_defense_snooze = 0

mob/Monsters/proc/RemasterDefenseData()
	return list("mode"=remaster_defense_mode, "state"=(remaster_defense ? remaster_defense.phase : (remaster_defense_mode == "assist" ? "Help nearby" : remaster_defense_mode == "self" ? "Defend self" : "No response")), "responding"=!!remaster_defense, "target"=(remaster_defense && remaster_defense.attacker ? remaster_defense.attacker.name : ""), "radius"=REMASTER_HELP_RADIUS)

Player/proc/RemasterDefenseMode(mob/Monsters/M, mode)
	if(!M || M.Owner != src || !(M in UnitList) || M.Wagon || !(mode in list("assist", "self", "off"))) return 0
	M.remaster_defense_mode = mode
	if(M.remaster_defense && (mode == "off" || (mode == "self" && M.remaster_defense.caller != M))) M.RemasterCancelDefense(1)
	RemasterNotice("[M.name]: [mode == "assist" ? "helps nearby tribe members" : mode == "self" ? "defends itself only" : "automatic response disabled"].")
	return 1

mob/Monsters/proc/RemasterDefenseAble()
	var/Player/P = Owner
	return istype(P) && isturf(loc) && HP > 0 && !GoingToDie && !Wagon && !Critter && !istype(src, /mob/Monsters/Chests) && CanWalk && CanSee && !Fainted && !Stunned && !Sleeping && !InHole && !Meditating && !CanBeSlaved && (src in P.UnitList)   // the list search last (combat-speed, 10-26)

mob/Monsters/proc/RemasterDefenseAvailable(helping = 0)
	if(remaster_defense || remaster_defense_mode == "off" || world.time < remaster_defense_snooze || !RemasterDefenseAble()) return 0
	// A unit you sent away from a fight goes (Orders.dm: a retreat is never turned back).
	if(remaster_active && remaster_active.retreat) return 0
	if(helping)
		if(remaster_defense_mode != "assist" || remaster_paused || remaster_wait_for_resume) return 0
		if(remaster_role_paused && (remaster_job != "manual" || length(remaster_production))) return 0
		if(remaster_order_status in list("Stopped", "Holding", "Holding position")) return 0
		// A deliberate combat order already has an opponent; do not redirect it.
		if(ismob(destination) || Target) return 0
	return 1

// Called from actual combat, including fired arrows that miss or are blocked.
// This callback never sleeps, rolls randomness, or changes the attacker's orders.
mob/proc/RemasterThreatenedBy(mob/Monsters/enemy)
	if(!istype(src, /mob/Monsters) || !istype(enemy)) return
	if(rm_quest_hunting) RmQuestStruck(src, enemy)   // who struck it, while quests count deaths (QuestTargets.dm)
	var/mob/Monsters/victim = src
	var/Player/P = Owner
	if(!istype(P) || !(victim in P.UnitList)) return
	victim.RemasterNoteAttack(enemy)
	if(istype(enemy) && istype(enemy.Owner, /Player) && !RemasterAtWar(P, enemy.Owner) && !RmTryPair(victim, enemy) && !RmFortTruce(victim, enemy)) RemasterWarGrievance(victim, enemy)   // a fort try is no grievance (QuestForts.dm)
	if(victim.remaster_defense_mode == "off") return
	if(enemy.Owner == Owner || enemy.CantKill || enemy.WS || enemy.key || enemy.GoingToDie || enemy.HP <= 0 || !isturf(enemy.loc) || enemy.z != z) return
	if(!isturf(loc) || HP <= 0 || GoingToDie || Sleeping || Fainted || Stunned || world.time < victim.remaster_defense_snooze) return
	// A responder cannot relay an alarm into an ever-expanding chain.
	if(victim.remaster_defense) return
	if(victim.RemasterDefenseAvailable()) victim.RemasterBeginDefense(enemy, victim)
	if(world.time < victim.remaster_help_ready) return
	victim.remaster_help_ready = world.time + 50
	var/helpers = 0
	for(var/mob/Monsters/M in range(REMASTER_HELP_RADIUS, victim))
		if(M == victim || M.z != z || M.Owner != P || !M.RemasterDefenseAvailable(1)) continue   // it checks M in P.UnitList itself, last (RemasterDefenseAble; combat-speed, 10-26)
		if(M.RemasterBeginDefense(enemy, victim)) helpers++
	P.remaster_alert_unit = victim
	P.remaster_alert_at = world.time
	if(world.time >= P.remaster_alert_ready)
		P.remaster_alert_ready = world.time + REMASTER_ALERT_DELAY
		P << "<b><font color=red>[victim] calls for help at [x],[y]: [helpers] nearby helper[helpers == 1 ? "" : "s"] responding. Press Backspace to go there.</font></b>"
	P.RemasterNotice("[victim.name] attacked; [helpers] nearby helper[helpers == 1 ? "" : "s"] responding.")

mob/Monsters/proc/RemasterBeginDefense(mob/Monsters/enemy, mob/Monsters/source)
	if(remaster_defense || remaster_attack || !RemasterDefenseAble() || !enemy || !source || source.Owner != Owner || enemy.Owner == Owner || enemy.z != z) return 0
	var/datum/remaster_defense/D = new
	D.issuer = Owner
	D.attacker = enemy
	D.caller = source
	D.origin = loc
	D.anchor = source.loc
	D.expires = world.time + 200
	D.previous_destination = destination
	D.previous_status = remaster_order_status
	D.last_position = loc
	D.last_progress = world.time
	remaster_defense = D
	destination = null
	SavedDest = null
	Target = null
	BowOn = 0
	return 1

mob/Monsters/proc/RemasterCancelDefense(resume = 0)
	var/datum/remaster_defense/D = remaster_defense
	if(!D) return
	remaster_defense = null
	destination = null
	SavedDest = null
	Target = null
	BowOn = 0
	// Explicit orders win for ten seconds; normal completion has a short cooldown.
	remaster_defense_snooze = world.time + (resume ? 20 : 100)
	if(!resume || Owner != D.issuer || !RemasterDefenseAble()) return
	if(remaster_active) RemasterStartOrder(remaster_active)
	if(remaster_delivery) RemasterStartOrder(remaster_delivery)
	remaster_work_position = null
	remaster_work_since = world.time
	remaster_work_retry = 0
	remaster_order_status = D.previous_status
	if(!RemasterHasOrder() && !remaster_paused && D.previous_destination && !ismob(D.previous_destination) && D.previous_destination.z == z) destination = D.previous_destination

mob/Monsters/proc/RemasterDefenseReturn()
	var/datum/remaster_defense/D = remaster_defense
	if(!D || D.phase == "Returning") return
	D.phase = "Returning"
	D.expires = world.time + 100
	D.path = null
	D.path_goal = null
	D.last_position = loc
	D.last_progress = world.time
	destination = null
	Target = null
	BowOn = 0

mob/Monsters/proc/RemasterDefenseApproach(turf/goal, reach)
	var/datum/remaster_defense/D = remaster_defense
	if(!D || !goal || goal.z != z) return 0
	if(D.last_position != loc)
		D.last_position = loc
		D.last_progress = world.time
	if(world.time - D.last_progress > max(40, Delay * 5)) return 0
	while(length(D.path) && D.path[1] == loc) D.path.Cut(1, 2)
	if(D.path_goal != goal || !length(D.path) || !RemasterStepOpen(D.path, src))
		if(rm_nav_count) rm_path_who = "defence, " + RmNavChaseWhy(D.path_goal, goal, D.path)
		D.path = RemasterOrderPath(src, goal, reach, D.anchor, REMASTER_HELP_RADIUS)
		D.path_goal = goal
	if(!length(D.path)) return 0
	destination = D.path[1]
	return 1

mob/Monsters/proc/RemasterDefenseTick()
	var/datum/remaster_defense/D = remaster_defense
	if(!D) return
	if(Owner != D.issuer || !D.origin || !D.anchor || !RemasterDefenseAble() || remaster_defense_mode == "off")
		RemasterCancelDefense(1)
		return
	if(D.phase == "Responding")
		var/mob/Monsters/E = D.attacker
		if(!E || E.HP <= 0 || E.GoingToDie || E.Owner == Owner || E.CantKill || E.WS || E.key || !isturf(E.loc) || E.z != z || D.origin.z != z || world.time >= D.expires || get_dist(E, D.anchor) > REMASTER_HELP_RADIUS || get_dist(src, D.anchor) > REMASTER_HELP_RADIUS || E.RemasterSubdued())   // out of the fight (knocked out, stunned, webbed, in a pit): left to be taken (Captives.dm), not finished off
			RemasterDefenseReturn()
		else if(remaster_nonlethal ? RemasterBowToMelee(1) : (RemasterBowToMelee() || RemasterCastFirst(E) == 1))   // out of arrows: a blade or fists; a caster's spell from range (Formations.dm)
			D.last_progress = world.time
		else if(!remaster_nonlethal && RemasterCanShoot() && (E in oview(RemasterShotReach(E), src)))
			destination = null
			Target = E
			if(world.time >= D.next_shot)
				D.next_shot = world.time + 50
				BowOn = 1
				BowTarget(1)
				BowOn = 0
		else if(!remaster_nonlethal && RemasterTryThrow(E)) D.last_progress = world.time
		else if(HoldingWeapon == "Spear" && get_dist(src, E) == 2 && (E in oview(2, src)) && world.time >= remaster_reach_at)
			destination = null            // a spear strikes from two tiles away
			remaster_reach_at = world.time + 12
			RemasterStrike(E, "reach")
		else if(RmBeastPartFor(src, E))   // a great beast on the ground: fought at its parts (Beasts.dm)
			var/obj/RmBeastFoot/BF = RmBeastPartFor(src, E)
			if(get_dist(src, BF) <= 1)
				D.last_progress = world.time
				RmBeastStrikePart(E, BF)
			else if(!RemasterDefenseApproach(BF.loc, 1)) RemasterDefenseReturn()
		else if(RmJawStrike(E)) D.last_progress = world.time   // a great beast bites from where its head is (Beasts.dm)
		else if(get_dist(src, E) <= 1 && (E in oview(1, src)))
			// WalkTo/Bump owns melee and its original weapon/limb rules.
			destination = E
			D.last_progress = world.time
		else if(!RemasterDefenseApproach(E.loc, 1)) RemasterDefenseReturn()
	if(D.phase == "Returning")
		if(loc == D.origin || D.origin.z != z || world.time >= D.expires || !RemasterDefenseApproach(D.origin, 0)) RemasterCancelDefense(1)
