// The tavern (Remastered): drink and company, and the brawls that come with them.
//  - The Tavern (Build tab, 1 wood: a barrel counter) keeps drink, up to 40 cups. Wine is poured in
//    from bottles (a Wine brew, Brewing.dm: a cup for every 3 units), or pressed there: two pieces
//    of fruit and a fungus make three cups. Idle cooks press wine for it from the stockpile's fruit
//    and fungus when it runs low.
//  - Villagers go for a drink when there is some, at most every five minutes (care, Care.dm): at
//    night, when the day's work is done (with moods on: whenever their mood is under 50). Guards
//    on patrol stay sober. A visit is a round every few seconds: two or three cups alone, up to
//    five with friends there, which is how brawls start. A cup is drunk wine (Ailments.dm) and a
//    memory: "Had a drink at the tavern" (+6), "Drank with friends" (+10) with others there.
//  - Brawls: someone very drunk (50+) may pick a fight with anyone beside them. They trade the
//    non-lethal subdue blows of Subdue.dm for up to 20 seconds or until one is knocked out. A sober
//    villager on patrol within 6 tiles comes over and breaks it up. Speech bubbles taunt.

#define RM_TAVERN_MAX 40

var/list/rm_taverns = list()

mob/WorkShops/RemasterTavern
	name = "Tavern"
	icon = 'Cave.dmi'
	icon_state = "Table"
	density = 1
	var/drink = 0                  // cups of wine (saved)

	New()
		..()
		rm_taverns += src

	Del()
		rm_taverns -= src
		return ..()

	DblClick()
		if(istype(usr, /Player)) usr:RemasterNotice("Select a unit beside the Tavern: its box pours or presses wine.")

mob/Monsters/var/tmp
	rm_tavern_at = -6000
	rm_round_at = 0
	mob/Monsters/rm_brawl_with
	rm_brawl_until = 0

proc/RemasterTavernBeside(mob/M)
	for(var/mob/WorkShops/RemasterTavern/T in range(1, M)) return T
	return null

Player/proc/RemasterTavernWithDrink(mob/M, reach = 40)
	var/mob/WorkShops/RemasterTavern/best
	var/best_d = reach + 1
	for(var/mob/WorkShops/RemasterTavern/T in rm_taverns) if(T.Owner == src && T.z == M.z && T.drink >= 1)
		var/d = get_dist(T, M)
		if(d < best_d)
			best = T
			best_d = d
	return best

// Wine from a bottle into the tavern: a cup for every 3 units.
mob/WorkShops/RemasterTavern/proc/PourIn(obj/Items/Potions/RemasterBrew/B)
	var/u = B.brew["wine"] || 0
	var/cups = min(RM_TAVERN_MAX - drink, round(u / 3))
	if(cups < 1) return 0
	drink += cups
	B.brew["wine"] = u - cups * 3
	if(B.brew["wine"] < 0.5) B.brew -= "wine"
	RemasterBrewLook(B)
	return cups

// Two fruit and a fungus carried by M pressed into three cups.
mob/WorkShops/RemasterTavern/proc/Press(mob/Monsters/M)
	var/list/fruit = list()
	var/obj/Items/Food/Fungus/fungus
	for(var/obj/Items/Food/F in M) if(F.suffix == "(Carrying)" && !F.rm_rotten)
		if(istype(F, /obj/Items/Food/Grape) || istype(F, /obj/Items/Food/Tomato))
			if(length(fruit) < 2) fruit += F
		else if(istype(F, /obj/Items/Food/Fungus) && !fungus) fungus = F
	if(length(fruit) < 2 || !fungus || drink + 3 > RM_TAVERN_MAX) return 0
	for(var/obj/Items/Food/F in fruit + fungus)
		M.DropItem(F)
		del F
	drink += 3
	return 3

// --- Going for a drink (care) ---------------------------------------------------------------------
mob/Monsters/proc/RemasterTavernWanted(Player/P)
	if(rm_drunk >= 30 || world.time - rm_tavern_at < 3000 || remaster_patrol || !RemasterPoisonable()) return 0
	if(rm_moods_on ? remaster_mood >= 50 : (!night || !prob(25))) return 0
	if(Race in list("Gargoyle", "Vampire", "Zombie", "Devourer")) return 0
	var/mob/WorkShops/RemasterTavern/T = P.RemasterTavernWithDrink(src)
	var/turf/G = T ? RemasterTileNear(T, src) : null
	if(!G) return 0
	rm_tavern_at = world.time
	RemasterCareStart("tavern", T, G, "Going to the tavern for a drink")
	RemasterSay(RemasterLine(list("I need a drink.", "Tavern, anyone?", "One for the road...")))
	return 1

mob/Monsters/proc/RemasterCareTavern(Player/P)
	var/mob/WorkShops/RemasterTavern/T = remaster_care_target
	if(!istype(T) || T.z != z) return RemasterCareDone("The tavern is gone")
	if(get_dist(src, T) > 2)
		var/turf/G = RemasterTileNear(T, src)
		if(G && destination != G)
			destination = G
			remaster_care_dest = G
		return
	if(destination == remaster_care_dest) destination = null
	if(world.time - remaster_care_since > 400)
		return RemasterCareDone("Had a drink at the tavern")
	if(world.time < rm_round_at) return
	var/friends = 0
	for(var/mob/Monsters/O in range(3, T)) if(O != src && O.Owner == Owner && O.HP > 0) friends++
	if(rm_drunk >= (friends ? 55 : 30)) return RemasterCareDone("Had a drink at the tavern")
	if(T.drink < 1) return RemasterCareDone("The tavern ran dry")
	T.drink--
	RemasterDrinkWine(6)
	rm_round_at = world.time + 50
	if(friends) RemasterRemember("tavern", "Drank with friends", 10, 1)
	else RemasterRemember("tavern", "Had a drink at the tavern", 6, 1)
	remaster_care_status = "Having a drink at the tavern"
	RemasterSay(RemasterLine(friends ? list("Cheers!", "To friends!", "Another round!") : list("Ahh.", "That's the stuff.", "*gulp*")), 1)

// The cook keeps the tavern in drink (FoodRoles.dm): fruit and fungus from the stockpile, pressed.
// fetch: 0 only presses what is carried (checked before carried food is served).
mob/Monsters/proc/RemasterCookPressWine(Player/P, fetch = 1)
	var/mob/WorkShops/RemasterTavern/T
	for(var/mob/WorkShops/RemasterTavern/X in rm_taverns) if(X.Owner == P && X.z == z && X.drink < 6 && get_dist(X, src) <= RM_SERVE_REACH) T = X
	if(!T) return 0
	var/fruit = 0
	var/fungus = 0
	for(var/obj/Items/Food/F in src) if(F.suffix == "(Carrying)" && !F.rm_rotten)
		if(istype(F, /obj/Items/Food/Grape) || istype(F, /obj/Items/Food/Tomato)) fruit++
		else if(istype(F, /obj/Items/Food/Fungus)) fungus++
	if(fruit >= 2 && fungus >= 1)
		if(!RemasterWorkToward(T, "the tavern")) return 1
		var/n = T.Press(src)
		remaster_work_status = n ? "Pressed [n] cup\s of wine for the tavern" : "The tavern is full"
		return 1
	if(!fetch) return 0
	var/turf/S = P.RemasterStockpile()
	if(!S || S.z != z) return 0
	var/list/want = list()
	var/got_fruit = 0
	var/got_fungus = 0
	for(var/obj/Items/Food/F in range(1, S)) if(isturf(F.loc) && !F.rm_rotten && P.RemasterMayCollect(F))
		if((istype(F, /obj/Items/Food/Grape) || istype(F, /obj/Items/Food/Tomato)) && got_fruit + fruit < 2)
			want += F
			got_fruit++
		else if(istype(F, /obj/Items/Food/Fungus) && got_fungus + fungus < 1)
			want += F
			got_fungus++
	if(got_fruit + fruit < 2 || got_fungus + fungus < 1) return 0
	if(!RemasterWorkToward(S, "stockpile")) return 1
	for(var/obj/Items/Food/F in want) PickUpItem(F)
	remaster_work_status = "Took fruit and fungus to press wine"
	return 1

// --- Brawls (each care step, Ailments.dm) ---------------------------------------------------------
mob/Monsters/proc/RemasterBrawlTick(Player/P)
	var/mob/Monsters/O = rm_brawl_with
	if(O)
		// A brawl never knocks anyone out (only a deliberate Non-lethal or Capture order does, Subdue.dm): it ends when
		// one has had enough, about a third of their health gone, or the time is up.
		var/mob/Monsters/beaten = (O.HP <= O.MAXHP * RM_KO_MARK) ? O : ((HP <= MAXHP * RM_KO_MARK) ? src : null)
		if(O.HP <= 0 || O.z != z || O.rm_brawl_with != src || world.time > rm_brawl_until || RemasterKnockedOut() || O.RemasterKnockedOut() || beaten)
			RemasterBrawlEnd(beaten ? "[beaten.RemasterBareName()] had enough" : null)
			return
		// A guard on patrol nearby breaks it up.
		for(var/mob/Monsters/G in range(6, src))
			if(G == src || G == O || G.Owner != Owner || !G.remaster_patrol || G.rm_drunk >= 15 || G.HP <= 0 || G.Fainted) continue
			G.RemasterSay(RemasterLine(list("Break it up!", "Oi! Enough!", "Stop that, you two!")), 1)
			rm_drunk = max(0, rm_drunk - 10)
			O.rm_drunk = max(0, O.rm_drunk - 10)
			RemasterBrawlEnd("[G.RemasterBareName()] broke it up")
			return
		if(get_dist(src, O) > 1) step_towards(src, O)
		else if(prob(40))                 // a drunk's swing: most go wide
			dir = get_dir(src, O)
			RemasterSubdueBlow(O, 0)
			if(prob(30)) RemasterSay(RemasterLine(list("Take that!", "Hah!", "Come on then!", "You call that a punch?")))
		return
	if(rm_drunk < 50 || !isturf(loc) || Sleeping || Fainted || !prob(4)) return
	for(var/mob/Monsters/X in orange(1, src))
		if(X.HP <= 0 || X.Critter || X.Wagon || X.rm_brawl_with || X.Sleeping || X.Fainted || !X.RemasterPoisonable()) continue
		rm_brawl_with = X
		X.rm_brawl_with = src
		rm_brawl_until = world.time + 200
		X.rm_brawl_until = rm_brawl_until
		RemasterSay(RemasterLine(list("You looking at me?!", "Say that again!", "That's MY cup!")), 1)
		X.RemasterSay(RemasterLine(list("Oh, it's on!", "You'll regret that!", "Hey!")), 1)
		view(src) << "<font color=#e0a040>[src] starts a drunken brawl with [X]!</font>"
		if(istype(P)) P.RemasterLog("Brawl: [RemasterBareName()] picked a fight with [X.RemasterBareName()]", "fight", src)
		return

mob/Monsters/proc/RemasterBrawlEnd(note)
	var/mob/Monsters/O = rm_brawl_with
	rm_brawl_with = null
	if(O && O.rm_brawl_with == src) O.rm_brawl_with = null
	RemasterRemember("brawl", "Got into a fight", -4, 1)
	if(O) O.RemasterRemember("brawl", "Got into a fight", -4, 1)
	var/Player/P = Owner
	if(note && istype(P)) P.RemasterLog("Brawl over: [note]", "info", src)

// --- The tavern's box ---------------------------------------------------------------------------
Player/proc/RemasterTavernBoxData(mob/Monsters/M)
	var/mob/WorkShops/RemasterTavern/T = RemasterTavernBeside(M)
	if(!T) return null
	var/wine = 0
	for(var/obj/Items/Potions/RemasterBrew/B in M) wine += B.brew["wine"] || 0
	var/fruit = 0
	var/fungus = 0
	for(var/obj/Items/Food/F in M) if(F.suffix == "(Carrying)" && !F.rm_rotten)
		if(istype(F, /obj/Items/Food/Grape) || istype(F, /obj/Items/Food/Tomato)) fruit++
		else if(istype(F, /obj/Items/Food/Fungus)) fungus++
	return list("own"=(T.Owner == src), "drink"=T.drink, "max"=RM_TAVERN_MAX, "wine"=round(wine), "press"=(fruit >= 2 && fungus >= 1), "fruit"=fruit, "fungus"=fungus, "drunk"=M.rm_drunk)

// value: "unitref|action"
Player/proc/RemasterTavernCommand(value)
	var/list/p = splittext("[value]", "|")
	if(p.len < 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return 0
	var/mob/WorkShops/RemasterTavern/T = RemasterTavernBeside(M)
	if(!T || T.Owner != src)
		RemasterNotice("[M.RemasterBareName()] must stand beside your Tavern.")
		return 0
	switch(p[2])
		if("pour")
			var/n = 0
			for(var/obj/Items/Potions/RemasterBrew/B in M) n += T.PourIn(B)
			RemasterNotice(n ? "[M.RemasterBareName()] poured [n] cup\s of wine into the tavern." : "No wine to pour (a Wine brew: fruit juice and fungus), or the tavern is full.")
			return n > 0
		if("press")
			var/n = T.Press(M)
			RemasterNotice(n ? "[M.RemasterBareName()] pressed 3 cups of wine." : "Pressing wine takes 2 fruit and a fungus carried.")
			return n > 0
		if("drink")
			if(T.drink < 1)
				RemasterNotice("The tavern is out of wine: pour some in or press some first.")
				return 0
			T.drink--
			M.RemasterDrinkWine(6)
			M.RemasterRemember("tavern", "Had a drink at the tavern", 6, 1)
			M.RemasterSay("Cheers!", 1)
			return 1
	return 0

proc/Remaster3DTavern(mob/WorkShops/RemasterTavern/T)
	var/patrons = 0
	for(var/mob/Monsters/M in range(2, T)) if(M.remaster_care == "tavern") patrons++
	return list("drink"=T.drink, "max"=RM_TAVERN_MAX, "patrons"=patrons, "col"=(ismob(T.Owner) ? RemasterClaimColour(T.Owner:key) : "#c8a060"))
