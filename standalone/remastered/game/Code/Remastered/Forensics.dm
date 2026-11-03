// Forensics (Remastered, SS13's detective): who poisoned the food?
//  - A poisoner leaves traces: footprints around the pot or stall (shaped by their race), and a clue
//    on the food itself: what was used, their realm, and whose hand it was.
//  - Footprints last 15 minutes (3D draws them). The clue stays until the food is emptied.
//  - An Inspect of the food (the button, the Doctor's and the cooks' checks) may read the clue,
//    and a villager walking past the footprints may read them: 20% plus cooking, poison and potion
//    skill (sneaking skill for tracks). A very good roll names the poisoner.
//  - What is found goes into the village log and a "Clue" alert. A rival realm found out gives you
//    cause to declare war at once, as an attack at peace does (War.dm). Someone of your own realm
//    is named a traitor.

obj/RemasterTrace
	name = "Footprints"
	icon = 'Blood.dmi'
	icon_state = "1"
	color = "#4a3a28"
	mouse_opacity = 0
	var/race                       // whose feet
	var/realm_key
	var/realm_name
	var/who
	var/made = 0
	var/seen = 0                   // read by the realm it was left on

	New()
		..()
		made = world.time
		spawn(9000) if(src) del src

mob/WorkShops/RemasterFood/var
	rm_clue = ""                   // saved: "race|realm key|realm name|who|what"
	rm_clue_found = 0

// When M poisons C (FoodSupply.dm): the clue on the food and footprints around it.
mob/WorkShops/RemasterFood/proc/RemasterLeaveClue(mob/Monsters/M, what, Player/by)
	rm_clue = "[M.Race]|[by ? by.key : ""]|[by ? by.RemasterHouse() : "nobody"]|[M.RemasterBareName()]|[what]"
	rm_clue_found = 0
	var/list/spots = list(M.loc)
	for(var/turf/T in orange(1, M)) if(!T.density && length(spots) < 3 && prob(60)) spots += T
	for(var/turf/T in spots)
		var/obj/RemasterTrace/F = new(T)
		F.race = M.Race
		F.realm_key = by ? by.key : null
		F.realm_name = by ? by.RemasterHouse() : null
		F.who = M.RemasterBareName()
		F.dir = M.dir

mob/Monsters/proc/RemasterClueChance(tracks = 0)
	return clamp(20 + CookingSkill + PoisonSkill * 2 + PotionSkill + (tracks ? SneakingSkill * 2 : 0), 5, 90)

// Read the clue on poisoned food (from an Inspect by the owner's villager).
mob/Monsters/proc/RemasterReadClue(mob/WorkShops/RemasterFood/C)
	if(!C.rm_clue || C.rm_clue_found || C.Owner != Owner) return 0
	var/chance = RemasterClueChance()
	if(!prob(chance)) return 0
	var/list/p = splittext(C.rm_clue, "|")
	if(length(p) < 5) return 0
	C.rm_clue_found = 1
	var/named = prob(chance / 3)
	RemasterSay(RemasterLine(list("Hmm... [lowertext(p[1])] tracks.", "Someone's been at this.", "I smell [lowertext(p[5])].")), 1)
	return RemasterReportClue(p[1], p[2], p[3], named ? p[4] : null, "the [lowertext(C.name)] at [C.x], [C.y]", p[5], C)

// Footprints of another realm's people, noticed in passing (each care step, Ailments.dm).
mob/Monsters/proc/RemasterNoticeTracks(Player/P)
	if(!isturf(loc) || Sleeping || Fainted || !istype(P)) return 0
	for(var/obj/RemasterTrace/F in range(1, src))
		if(F.seen || !F.realm_key || F.realm_key == P.key) continue
		if(!prob(RemasterClueChance(1) / 4)) continue
		F.seen = 1
		for(var/obj/RemasterTrace/X in range(3, F)) if(X.realm_key == F.realm_key) X.seen = 1
		RemasterSay(RemasterLine(list("Strange tracks...", "Who's been here?", "These aren't ours.")), 1)
		return RemasterReportClue(F.race, F.realm_key, F.realm_name, prob(RemasterClueChance(1) / 3) ? F.who : null, "footprints at [F.x], [F.y]", null, F)
	return 0

mob/Monsters/proc/RemasterReportClue(race, realm_key, realm_name, who, where, what, atom/A)
	var/Player/P = Owner
	if(!istype(P)) return 0
	var/sign = findtext("[where]", "footprints") == 1 ? "[lowertext(race)] [where]" : "[lowertext(race)] tracks by [where]"   // "goblin footprints at 12, 30", not "tracks by footprints"
	var/text = "Clue: [sign][what ? ", and the smell of [lowertext(what)]" : ""]: someone of [realm_name || "another realm"][who ? " - [who]" : ""] was here. [RemasterBareName()] found it."
	var/Player/R = RemasterPlayerByKey(RemasterRootKey(P.key)) || P
	if(realm_key && RemasterAlliedKeys(realm_key, P.key))
		text = "Traitor: [sign]: [who ? who : "someone"] of your own realm did this. [RemasterBareName()] found it."
	else if(realm_key && !RemasterAtWarKeys(realm_key, P.key))
		if(!R.remaster_grievances) R.remaster_grievances = list()
		R.remaster_grievances[RemasterRootKey(realm_key)] = world.time
		text += " You may declare war on them at once (Realm tab)."
	if(istype(A, /mob/WorkShops/RemasterFood) && A:Poisoned()) text += " The food is poisoned: empty it."
	P.RemasterFoodAlarm(A || src, text, "Clue")
	RemasterEvent("Found a clue: [realm_name || "someone"][who ? " ([who])" : ""]")
	return 1
