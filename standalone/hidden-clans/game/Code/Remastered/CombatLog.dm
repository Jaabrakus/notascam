// What a unit is fighting, for the Company list, and a short log of what
// happened to it (attacked, fought back, went to help, won). Display only:
// nothing here changes combat.

#define REMASTER_EVENTS_KEPT 6
#define REMASTER_ATTACKED_SHOWN 100   // "Attacked by" shows 10 seconds after the last hit

mob/Monsters/var/tmp
	mob/Monsters/remaster_attacker
	remaster_attacked_at = 0
	list/remaster_events             // list(list(time, text))
	remaster_combat_last
	mob/Monsters/remaster_combat_foe

mob/Monsters/proc/RemasterEvent(text)
	if(!remaster_events) remaster_events = list()
	if(length(remaster_events))
		var/list/L = remaster_events[length(remaster_events)]
		if(L[2] == text && world.time - L[1] < 300) return
	remaster_events += list(list(world.time, text))
	while(length(remaster_events) > REMASTER_EVENTS_KEPT) remaster_events.Cut(1, 2)
	if(istype(Owner, /Player)) Owner:RemasterLog("[name]: [text]", findtext(text, "Won") ? "good" : "fight", src)

// Called from RemasterThreatenedBy (every real attack, arrows included).
mob/Monsters/proc/RemasterNoteAttack(mob/Monsters/enemy)
	if(!istype(enemy) || enemy.Owner == Owner) return
	if(enemy != remaster_attacker || world.time - remaster_attacked_at > REMASTER_ATTACKED_SHOWN)
		RemasterEvent("Attacked by [RemasterCombatName(enemy)]")
	remaster_attacker = enemy
	remaster_attacked_at = world.time

proc/RemasterCombatName(mob/M)
	if(!M) return "something"
	var/n = "[M.name]"
	return findtext(n, "}") ? copytext(n, findtext(n, "}") + 2) : n

proc/RemasterFoeAlive(mob/Monsters/M, mob/Monsters/near)
	return istype(M) && M.HP > 0 && !M.GoingToDie && !RmDownOut(M) && M.z == near.z && get_dist(M, near) <= 10   // a foe down is out of the fight (Falls.dm)

// One line: what this unit is fighting right now, or null.
mob/Monsters/proc/RemasterCombatText()
	if(HP <= 0 || RmDownOut(src)) return null   // down itself: its card says so (HUD.dm)
	var/datum/remaster_defense/D = remaster_defense
	if(D && RemasterFoeAlive(D.attacker, src))
		remaster_combat_foe = D.attacker
		if(D.caller && D.caller != src) return "Helping [RemasterCombatName(D.caller)] against [RemasterCombatName(D.attacker)]"
		return "Fighting back against [RemasterCombatName(D.attacker)]"
	if(ismob(Target) && RemasterFoeAlive(Target, src) && Target:Owner != Owner)
		remaster_combat_foe = Target
		return "Fighting [RemasterCombatName(Target)]"
	if(RemasterFoeAlive(remaster_attacker, src) && world.time - remaster_attacked_at < REMASTER_ATTACKED_SHOWN)
		remaster_combat_foe = remaster_attacker
		return "Attacked by [RemasterCombatName(remaster_attacker)]!"
	return null

// Called when the HUD reads the unit: logs fights starting and ending.
mob/Monsters/proc/RemasterCombatStatus()
	var/text = RemasterCombatText()
	if(text != remaster_combat_last)
		if(text && !findtext(text, "Attacked by")) RemasterEvent(text)
		else if(!text && remaster_combat_last)
			var/mob/Monsters/F = remaster_combat_foe
			if(RmDownOut(src)) F = null   // down itself: no word of how the fight ended (its fall is logged where it falls)
			else if(F && (F.HP <= 0 || F.GoingToDie || RmDownOut(F))) RemasterEvent("Won against [RemasterCombatName(F)]")   // fallen or out cold counts
			else if(remaster_combat_foe) RemasterEvent("Fight over")
			remaster_combat_foe = null
		remaster_combat_last = text
	return text

mob/Monsters/proc/RemasterEventData()
	var/list/out = list()
	if(remaster_events) for(var/list/L in remaster_events) out += list(list("ago"=round((world.time - L[1]) / 10), "text"=L[2]))
	return out
