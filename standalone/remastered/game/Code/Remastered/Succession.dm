// Heirs and succession (planning/FAMILY_HOUSES.md, phase 4).
// The head of the family is the hero (PlayMode.dm): the chosen hero, else the
// King or Queen, else the first living unit. When the head dies, the heir
// takes over the hero frame at once. Crowning still goes through the
// original Declare Leader rules (one ruler of each title, the one-hour wait).
// Rulership (Rulership.dm, 2026-10-23): whoever of the realm holds its heir's item
// inherits first; then the realm's law of succession (bloodline is the rule below).

Player/var/remaster_heir_uid             // heir named by the player
Player/var/tmp/list/remaster_succession  // last succession, for the event banner

mob/Monsters/proc/RemasterCanInherit(Player/P)
	return Owner == P && HP > 0 && !GoingToDie && !Wagon && !Egg && !Critter && !rm_cap_state   // never a captive or a slave

proc/RemasterEldest(list/L)
	var/mob/Monsters/best
	for(var/mob/Monsters/M in L) if(!best || M.Age > best.Age) best = M
	return best

// The heir of R: whoever of the realm holds its heir's item (or, under the Regalia
// law, its regalia), else the realm's law (Rulership.dm).
Player/proc/RemasterHeirOf(mob/Monsters/R)
	var/list/living = list()
	for(var/mob/Monsters/M in UnitList) if(M != R && M.RemasterCanInherit(src)) living += M
	if(!length(living)) return null
	return RmItemHeir(living) || RmLawHeir(R, living)

// The house rule, the Bloodline law: named heir, eldest child, eldest sibling,
// eldest of the house, then the eldest of anyone.
Player/proc/RmBloodlineHeir(mob/Monsters/R, list/living)
	if(remaster_heir_uid) for(var/mob/Monsters/M in living) if(M.remaster_uid == remaster_heir_uid) return list(M, "named heir")
	if(R && R.remaster_uid)
		var/list/kids = list()
		var/list/sibs = list()
		var/list/house = list()
		for(var/mob/Monsters/M in living)
			if(M.remaster_father == R.remaster_uid || M.remaster_mother == R.remaster_uid) kids += M
			else if((R.remaster_father && M.remaster_father == R.remaster_father) || (R.remaster_mother && M.remaster_mother == R.remaster_mother)) sibs += M
			else if(R.remaster_house && M.remaster_house == R.remaster_house) house += M
		if(length(kids)) return list(RemasterEldest(kids), "eldest child")
		if(length(sibs)) return list(RemasterEldest(sibs), "eldest sibling")
		if(length(house)) return list(RemasterEldest(house), "eldest of the house")
	return list(RemasterEldest(living), "chosen by the village")

// Called from RemasterRecordDeath.
mob/Monsters/proc/RemasterSuccession(Player/P)
	var/mob/Monsters/head = P.RemasterHero()
	// A chosen head counts first; without one, the ruler (or the last unit) does.
	var/was_head = P.remaster_hero_uid ? (remaster_uid == P.remaster_hero_uid) : (IsRoyal || !head)
	if(remaster_uid && remaster_uid == P.remaster_heir_uid) P.remaster_heir_uid = null
	if(IsRoyal) P.RmSeatCheck(src)   // the last ruler gone: another realm holding our heir's item has a claim (Rulership.dm)
	if(!was_head) return
	var/list/H = P.RemasterHeirOf(src)
	var/house = P.RemasterHouseName(remaster_house)
	if(!H)
		P.remaster_succession = list("dead"="[RemasterBareName()]", "heir"=null, "house"=house)
		P.RemasterNotice("[RemasterBareName()] has died, and House [house] has no one left to lead it.")
		return
	var/mob/Monsters/N = H[1]
	if(!N.remaster_uid) N.RemasterLineageEnsure(P)
	P.remaster_hero_uid = N.remaster_uid
	if(P.remaster_heir_uid == N.remaster_uid) P.remaster_heir_uid = null
	P.remaster_succession = list("dead"="[RemasterBareName()]", "heir"=RemasterUIRef(N), "heirName"="[N.RemasterBareName()]", "why"=H[2],
		"house"=house, "royal"=!!IsRoyal, "title"=N.RmOfferTitle(P), "claim"=P.RmClaimText())
	P.RemasterNotice("[RemasterBareName()] has died. [N.RemasterBareName()], [H[2]], now leads House [house].")
	P.RemasterLog("[N.RemasterBareName()] now leads House [house]", "birth", N)   // (no chat line too: the notice and the banner say it; polish-start 10-26)

Player/proc/RemasterSuccessionCommand(action, value)
	switch(action)
		if("designateheir")
			for(var/mob/Monsters/M in UnitList) if(M.remaster_uid == value && M.RemasterCanInherit(src))
				var/mob/Monsters/head = RemasterHero()
				if(M == head) return 0
				remaster_heir_uid = value
				RemasterNotice("[M.name] is now the named heir.")
				return 1
			return 0
		if("crownheir")
			var/mob/Monsters/N = RemasterHero()
			if(!N || N.IsRoyal) return 0
			// The original crowning, with its own question and rules.
			for(var/mob/Monsters/S in Selected.Copy()) S.Deselect(src)
			Selected = list()
			N.Select(src)
			remaster_succession = null
			RemasterDeclareSelected(1)
			return 1
		if("succession_ok")
			remaster_succession = null
			return 1
	return 0

Player/proc/RemasterSuccessionData()
	var/mob/Monsters/head = RemasterHero()
	var/list/H = head ? RemasterHeirOf(head) : null
	var/mob/Monsters/heir = H ? H[1] : null
	return list("ruler"=(head ? head.remaster_uid : null), "heir"=(heir ? heir.remaster_uid : null),
		"heirName"=(heir ? "[heir.name]" : null), "heirWhy"=(H ? H[2] : null), "named"=remaster_heir_uid, "event"=remaster_succession)

// The head of the family is pinned as it stands: the ruler, else the first of the people, kept until
// they die or lose the throne to a crowned ruler. There is no chosen hero since Hero mode was removed,
// and Death() takes a unit off the unit list before RemasterRecordDeath, so without the pin the head
// was worked out after its death (as whoever was next) and no one ever succeeded a head who wasn't crowned.
Player/RemasterPlayModeTick()
	..()
	RemasterPinHead()

Player/proc/RemasterPinHead()
	var/mob/Monsters/H = RemasterHero()
	if(!H) return
	if(!H.IsRoyal) for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0 && M.IsRoyal)
		H = M
		break
	if(!H.remaster_uid) H.RemasterLineageEnsure(src)
	if(H.remaster_uid && H.remaster_uid != remaster_hero_uid) remaster_hero_uid = H.remaster_uid
