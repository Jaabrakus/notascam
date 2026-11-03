// Families and captives, from the unit frame (and the right-click list).
//
// Have a child: with one unit selected, the frame lists partners close by (the other
// sex, your own, of age, not already expecting, of a race that breeds). Choosing one
// walks the pair together and the original breeding (Breeding.dm) takes its course.
//
// Capture: an enemy you may fight (raiders and monsters, or a realm at war), once it is
// subdued - fainted, stunned, webbed or rooted, in a pit, or knocked out - can be taken
// by one of your people standing beside it, with a rope (Captives.dm). Bound, they never
// join by themselves: win them over or enslave them, and they keep trying to break free.
// Animals are tamed at once. Rulers cannot be captured.

mob/Monsters/var/tmp
	remaster_breed_with            // the partner this unit is walking to
	remaster_breed_until = 0

// --- Having a child ----------------------------------------------------------------
proc/RemasterBreedRace(mob/Monsters/M)
	return !(M.Race in list("Vampire", "Dragon", "Svartalfar", "Spider")) && !M.Wagon && !M.Egg && !RemasterIsSiege(M)

proc/RemasterOfAge(mob/Monsters/M)
	return M.Critter || (M.Age >= 5 && M.Age <= 100)

mob/Monsters/proc/RemasterExpecting()
	return !!(CHILDMALE || CHILDFEMALE)

mob/Monsters/proc/RemasterPartners(Player/P)
	. = list()
	if(!RemasterBreedRace(src) || !RemasterOfAge(src) || HP <= 0 || GoingToDie) return
	for(var/mob/Monsters/O in P.UnitList)
		if(O == src || O.Owner != P || O.z != z || get_dist(src, O) > 12 || O.HP <= 0 || O.GoingToDie || !isturf(O.loc) || O.RemasterIsDown()) continue
		if(O.Race != Race || !O.Gender || !Gender || O.Gender == Gender || !RemasterBreedRace(O) || !RemasterOfAge(O)) continue
		if(!!O.Critter != !!Critter) continue
		var/mob/Monsters/F = Gender == "Female" ? src : O
		if(F.RemasterExpecting()) continue
		. += O

Player/proc/RemasterBreedOrder(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	var/mob/Monsters/O = RemasterUIUnit(p[2])
	if(!istype(M) || !istype(O) || M.Owner != src || !(O in M.RemasterPartners(src)))
		RemasterNotice("They can't have a child together right now.")
		return 0
	M.RemasterCancelOrders()
	O.RemasterCancelOrders()
	M.remaster_breed_with = O
	M.remaster_breed_until = world.time + 300
	O.destination = null
	RemasterNotice("[M.RemasterBareName()] and [O.RemasterBareName()] go off together.")
	spawn(0) M.RemasterBreedWalk(src)
	return 1

mob/Monsters/proc/RemasterBreedWalk(Player/P)
	while(remaster_breed_with && world.time < remaster_breed_until)
		var/mob/Monsters/O = remaster_breed_with
		if(!O || O.HP <= 0 || Owner != P || O.Owner != P)
			break
		if(get_dist(src, O) <= 1)
			destination = null
			var/mob/Monsters/F = Gender == "Female" ? src : O
			BreedWith(O, 1)
			if(F && F.RemasterExpecting())
				P.RemasterNotice("[F.RemasterBareName()] is expecting!")
				P.RemasterLog("[F.RemasterBareName()] is expecting a child", "birth", F)
			else if(F) P.RemasterNotice("No child this time for [F.RemasterBareName()] (try again later).")
			break
		destination = O
		sleep(5)
	remaster_breed_with = null
	destination = null

// --- Capturing -----------------------------------------------------------------------
// Down and takeable: knocked out (Subdue.dm) or fainted, stunned, in a pit, webbed or rooted.
// Being badly hurt is not enough: knocking out is deliberate (the Non-lethal toggle).
mob/Monsters/proc/RemasterSubdued()
	return Fainted || Stunned || InHole || remaster_root_until > world.time || RemasterKnockedOut()

// Roughly what this unit's body health is when whole (HP and parts at their best seen).
mob/Monsters/var/tmp/remaster_body_max = 0
mob/Monsters/proc/RemasterBodyMax()
	var/h = RemasterBodyHealth(src)
	if(h > remaster_body_max) remaster_body_max = h
	return remaster_body_max

// Can C (one of P's people) capture T now? Returns null if yes, else the reason.
proc/RemasterCaptureWhyNot(mob/Monsters/C, mob/Monsters/T)
	var/why = RemasterCapturable(C, T)     // Subdue.dm
	if(why) return why
	if(get_dist(C, T) > 1) return "Stand right beside them to capture them."
	if(!T.RemasterSubdued()) return "Knock them out first (Non-lethal, or a Capture order), or web or trap them."
	return null

Player/proc/RemasterCapture(value)
	var/list/p = splittext("[value]", "|")
	var/mob/Monsters/C = length(p) >= 1 ? RemasterUIUnit(p[1]) : null
	var/mob/Monsters/T = length(p) >= 2 ? (RemasterUIUnit(p[2]) || locate(p[2])) : null
	if(!istype(C) || C.Owner != src || !(C in UnitList))
		RemasterNotice("Select one of your people beside the captive.")
		return 0
	var/why = RemasterCaptureWhyNot(C, T)
	if(why)
		RemasterNotice(why)
		return 0
	if(T.Critter)
		T.remaster_ko_until = 0
		T.Fainted = 0
		T.ChangeOwnership(src)
		T.Tame = 1
		T.Cantame = 0
		T.Target = null
		T.destination = null
		T.name = "{[src]} [T.RemasterBareName()]"
		RemasterNotice("[C.RemasterBareName()] tamed [T.RemasterBareName()].")
		RemasterLog("Tamed [T.RemasterBareName()]", "good", T)
		return 1
	// A person is tied with a rope (Captives.dm): the captor's, one carried beside them, or one fetched.
	var/obj/Items/R = RmCapRopeAtHand(src, C, T)
	if(!R)
		var/obj/Items/L = RmCapRopeLying(C)
		if(L && (!T.rm_cap_fetcher || T.rm_cap_fetcher.HP <= 0 || T.rm_cap_fetcher.Owner != src))
			spawn(0) C.RmCapFetchRope(src, T, L)
			RemasterNotice("[C.RemasterBareName()] goes for a rope ([get_dist(C, L)] tiles off); your people beside [T.RemasterBareName()] hold them down.")
		else if(!L) RemasterNotice(RmCapNoRopeText(T))
		return 0
	T.Target = null          // tying them doesn't wake them: a knocked-out captive lies roped until it comes to
	T.destination = null
	if(istype(T, /mob/Monsters) && T:remaster_attack) T:remaster_attack = null
	if(remaster_raiders[T]) remaster_raiders -= T
	return T.RmCapBind(src, C, R)

// Won over (Captives.dm): the rope comes off and they join your house under your name.
mob/Monsters/proc/RemasterJoinHouse(Player/P)
	var/was_slave = rm_cap_state == "slave"
	RmCapRopeOff()
	RmCapClear()
	rm_cap_from = null
	rm_cap_from_player = 0
	rm_cap_name = null
	rm_cap_home = null
	remaster_slow_until = 0
	remaster_root_until = 0
	if(Owner != P || HP <= 0) return
	var/bare = RmCapBareName()
	if(!bare || bare == "[Race]" || findtext(bare, "Scout") || findtext(bare, "Slave")) bare = RemasterMakeName(Race, Gender)
	name = "{[P]} [bare]"
	remaster_house = P.RemasterMainHouse(src)
	remaster_defense_mode = "assist"
	P.RemasterNotice("[bare] [was_slave ? "is a slave no longer and has" : "has"] joined your house.")
	P.RemasterLog("[bare] joined the house", "good", src)

// For the unit frame: who this unit could capture or have a child with right now.
mob/Monsters/proc/RemasterCaptureData(Player/P)
	. = list()
	for(var/mob/Monsters/T in orange(1, src)) if(!RemasterCaptureWhyNot(src, T))
		. += list(list("ref"="\ref[T]", "name"=T.RemasterBareName()))

// The unit card's Interact tab: creatures within 5 tiles in view, nearest first, and what this unit
// can do with each ("select", "child", "capture", "attack").
mob/Monsters/proc/RemasterNearbyData(Player/P)
	var/list/near = list()
	for(var/mob/Monsters/T in oview(5, src))
		if(T.HP <= 0 || T.GoingToDie || T.Wagon || T.Egg || RemasterIsSiege(T) || istype(T, /mob/Monsters/Chests) || !isturf(T.loc)) continue
		var/d = get_dist(src, T)
		var/i = 1
		while(i <= length(near) && get_dist(src, near[i]) <= d) i++
		near.Insert(i, T)
	var/list/partners = RemasterPartners(P)
	var/list/out = list()
	var/rope = -1
	for(var/mob/Monsters/T in near)
		if(length(out) >= 8) break
		var/mine = T.Owner == P
		var/hostile = !mine && RemasterHostile(src, T, 1)
		var/list/acts = list()
		if(mine)
			acts += "select"
			if(T in partners) acts += "child"
			if(T.rm_cap_state && !rm_cap_state && !Critter && !T.RmCapOutCold()) acts += "winover"   // Captives.dm (not while they're out cold)
		else
			if(!RemasterCapturable(src, T))
				acts += "capture"
				if(rope == -1) rope = P.RmCapRopeSource(src, null) || ""
			if(hostile) acts += "attack"
			if(T.rm_keeper && RmKeeperOk(T)) acts += "talk"   // a keeper (QuestKeepers.dm)
			if(istype(T.Owner, /Player) && !T.Critter) acts += "report"   // Moderation.dm
		var/kind = mine ? "yours" : T.Critter ? (T.Owner ? "tame animal" : "wild animal") : istype(T.Owner, /Player) ? (hostile ? "enemy realm" : "another realm") : (hostile ? "hostile" : "peaceful")
		out += list(list("ref"=(mine ? RemasterUIRef(T) : null), "id"="\ref[T]", "name"=T.RemasterBareName(), "race"="[T.Race]", "kind"=kind,
			"dist"=get_dist(src, T), "hp"=round(100 * T.HP / max(1, T.MAXHP)), "ko"=T.RemasterKnockedOut(), "critter"=!!T.Critter, "acts"=acts,
			"uses"=(mine ? P.RemasterUsesOn(src, T) : null), "captive"=T.rm_cap_state, "rope"=((!mine && !T.Critter && ("capture" in acts)) ? rope : null)))    // TargetActions.dm
	for(var/mob/Body/B in oview(5, src))
		if(length(out) >= 10) break
		if(!isturf(B.loc) || B.suffix) continue
		out += list(list("id"="\ref[B]", "name"=RemasterDeadName(B), "kind"="body", "dist"=get_dist(src, B), "acts"=list("carrybody")))
	return out

mob/Monsters/proc/RemasterFamilyData(Player/P)
	var/list/partners = list()
	for(var/mob/Monsters/O in RemasterPartners(P)) partners += list(list("ref"=RemasterUIRef(O), "name"=O.RemasterBareName()))
	return list("partners"=partners, "expecting"=RemasterExpecting(), "captive"=rm_cap_state, "kin"=(Critter ? null : RemasterKinData(P)))

// Kin for the unit card's Family tab: house, parents, partners, children and siblings, the living
// (with a ref to select them) and the dead (from the ledger, Lineage.dm).
mob/Monsters/proc/RemasterKinData(Player/P)
	RemasterLineageEnsure(P)
	var/list/living = list()
	for(var/mob/Monsters/M in P.UnitList) if(M.Owner == P && !M.Wagon && !M.Critter && !M.Egg && M.remaster_uid) living[M.remaster_uid] = M
	var/list/ledger = P.remaster_ledger || list()
	var/list/parents = list()
	var/list/names = remaster_parent_names || list()
	parents += RemasterKinEntry(P, remaster_father, length(names) >= 1 ? names[1] : null, living, ledger, "Father")
	parents += RemasterKinEntry(P, remaster_mother, length(names) >= 2 ? names[2] : null, living, ledger, "Mother")
	var/list/partners = list()
	for(var/uid in remaster_partners) partners += RemasterKinEntry(P, uid, null, living, ledger, "Partner")
	var/list/children = list()
	var/list/siblings = list()
	var/list/seen = list()
	for(var/uid in living)
		var/mob/Monsters/M = living[uid]
		if(M == src) continue
		if(remaster_uid && (M.remaster_father == remaster_uid || M.remaster_mother == remaster_uid)) children += RemasterKinEntry(P, uid, null, living, ledger, "Child")
		else if((remaster_father && M.remaster_father == remaster_father) || (remaster_mother && M.remaster_mother == remaster_mother)) siblings += RemasterKinEntry(P, uid, null, living, ledger, "Sibling")
		seen[uid] = 1
	for(var/uid in ledger)
		if(seen[uid] || uid == remaster_uid) continue
		var/list/R = ledger[uid]
		if(remaster_uid && (R["father"] == remaster_uid || R["mother"] == remaster_uid)) children += RemasterKinEntry(P, uid, null, living, ledger, "Child")
		else if((remaster_father && R["father"] == remaster_father) || (remaster_mother && R["mother"] == remaster_mother)) siblings += RemasterKinEntry(P, uid, null, living, ledger, "Sibling")
	var/list/H = remaster_house ? ((P.remaster_houses && P.remaster_houses[remaster_house]) || RemasterForeignHouse(remaster_house)) : null
	var/mob/Monsters/head = P.RemasterHero()
	return list("uid"=remaster_uid, "house"=(H ? H["name"] : null), "color"=(H ? H["color"] : null), "foreign"=(remaster_house && !(P.remaster_houses && P.remaster_houses[remaster_house])),
		"generation"=remaster_generation, "born"=remaster_born, "ruler"=(head == src), "heir"=(remaster_uid && P.remaster_heir_uid == remaster_uid),
		"canHeir"=(head != src && RemasterCanInherit(P) && !(remaster_uid && P.remaster_heir_uid == remaster_uid)),
		"parents"=parents, "partners"=partners, "children"=children.Copy(1, min(length(children), 12) + 1), "siblings"=siblings.Copy(1, min(length(siblings), 12) + 1))

// One relative: "name", "ref" when alive and yours, "dead" when in the ledger, "role".
proc/RemasterKinEntry(Player/P, uid, fallback, list/living, list/ledger, role)
	if(!uid && !fallback) return list()
	var/mob/Monsters/M = uid ? living[uid] : null
	if(M) return list(list("name"=M.RemasterBareName(), "ref"=RemasterUIRef(M), "role"=role, "gender"="[M.Gender]", "age"=M.Age))
	var/list/R = uid ? ledger[uid] : null
	if(R) return list(list("name"=RemasterStripTag("[R["name"]]"), "dead"=1, "role"=role, "gender"="[R["gender"]]"))
	return list(list("name"=RemasterStripTag("[fallback || "Unknown"]"), "away"=1, "role"=role))

proc/RemasterStripTag(t)
	var/i = findtext(t, "} ")
	return (copytext(t, 1, 2) == "{" && i) ? copytext(t, i + 2) : t
