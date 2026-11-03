// SS13-style ailments (Remastered): being drunk, food poisoning from rotten food, and a contagious
// fever. They run on each care step (Care.dm, about every 3 seconds) for the player's villagers,
// use the original effects where the game has them (Sleep(), Hunger, Tiredness, HP, the green vomit
// of FoodSupply.dm), show in the unit's warnings, the Health tab and in 3D, and are treated with the
// Doctor's remedies (Doctor.dm).
//  - Drunk (rm_drunk, 0-100): from Wine, a new brew (fruit juice 2 + fungus 1, Brewing.dm), drunk by
//    hand, handed over, or by unhappy villagers who carry some. Tipsy villagers are merrier; drunk
//    ones stagger now and then; very drunk ones throw up; past 85 they pass out. It wears off by 1 a
//    step; a Thistle purge sobers them up.
//  - Rotten food: food ages a minute at a time wherever it lies or is carried. After an hour it is
//    Rotten, and after two it rots away, even on a stockpile. Food pots and stalls keep food fresh,
//    and a hot pot boils rotten food clean. Villagers smell rot and won't eat it unless starving;
//    eaten, it gives food poisoning (rm_foodsick): retching and green vomit for about a minute,
//    hunger lost, and a chance of the fever. A Thistle purge settles it.
//  - Salt keeps food: rock salt comes out of mined rock now and then (more in the mesa) and with
//    caravans. Salted food (a lump salts four pieces carried by the same unit: use the salt from the
//    bag; cooks salt meat waiting on the stockpile) rots eight times slower. Salt needs no combining
//    to keep food: food lying on a stockpile or zone with salt on it, and food in a bag with salt in
//    it, rots four times slower; a lump keeps ten pieces an hour, then it's used up.
//  - Fever (rm_fever: stage 1 coughing, 2 fever, 3 very ill, like SS13's virus stages): caught from
//    rotten food, from rot in the air (miasma from bodies left lying, Vapours.dm), from Plague, or
//    from the sick. A minute after catching it they start coughing, and then spread it to anyone
//    within a tile, to sleepers within two, and to the pot or stall they eat from (a hot pot kills
//    the germs). It worsens every two minutes unless it breaks; rest in bed makes that three times
//    likelier. At stage 3 it drains health and can kill ("Fever"). Feverfew tonic cures it; after
//    it they are immune for a while.

#define RM_ROT_AGE 60              // minutes until food is rotten
#define RM_ROT_GONE 120            // minutes until it rots away
#define RM_FEVER_STAGE 40          // care steps (about two minutes) to the next stage
#define RM_FEVER_INCUBATE 20       // care steps from catching it to the first cough

obj/Items/var
	rm_age = 0                     // food: minutes old (saved)
	rm_rotten = 0
	rm_salted = 0
mob/Monsters/var
	rm_drunk = 0
	rm_foodsick = 0                // care steps of food poisoning left
	rm_fever = 0                   // 0 well, 1 coughing, 2 fever, 3 very ill
	rm_fever_t = 0                 // care steps at this stage
	rm_fever_incub = 0             // care steps until the first cough
	rm_fever_from = ""
	rm_immune = 0                  // care steps of immunity to the fever left
mob/WorkShops/RemasterFood/var/rm_germs = 0   // servings that may still pass a fever on
mob/Monsters/var/tmp/rm_cough_at = -100

// --- Each care step ------------------------------------------------------------------------
mob/Monsters/proc/RemasterAilmentTick(Player/P)
	if(HP <= 0 || GoingToDie) return
	RemasterSayHurt()                 // "Ow!" (Speech.dm)
	RemasterLimbCheck(P)              // grafts and false limbs (Surgery.dm)
	RemasterNoticeTracks(P)           // strangers' footprints (Forensics.dm)
	RemasterBrawlTick(P)              // drunken brawls (Tavern.dm)
	if(rm_immune > 0) rm_immune--
	if(rm_drunk > 0) RemasterDrunkTick(P)
	else RemasterWineWhenSad(P)
	if(rm_foodsick > 0) RemasterFoodSickTick(P)
	if(rm_fever || rm_fever_incub) RemasterFeverTick(P)
	else RemasterFeverExposure()

// What's wrong, for the unit card's warnings (HUD.dm) and the Health tab (Health.dm).
mob/Monsters/proc/RemasterAilmentWarnings()
	. = list()
	if(rm_poison > 0 && rm_poison_sick) . += "Poisoned"
	if(rm_fever >= 2) . += "Fever"
	else if(rm_fever) . += "Coughing"
	if(rm_foodsick > 0) . += "Food poisoning"
	if(rm_drunk >= 35) . += "Drunk"

mob/Monsters/proc/RemasterAilmentConds()
	. = list()
	if(rm_poison > 0) . += list(list(rm_poison_sick ? "Poisoned ([rm_poison_kind || "poison"])" : "Ate something bad", rm_poison > 20 ? 4 : 3))
	if(rm_fever) . += list(list(list("Coughing (fever, stage 1)", "Fever (stage 2)", "Very ill with fever (stage 3)")[rm_fever], rm_fever + 1))
	else if(rm_fever_incub) . += list(list("Feeling unwell", 1))
	if(rm_foodsick > 0) . += list(list("Food poisoning", 2))
	if(rm_drunk >= 85) . += list(list("Blind drunk", 3))
	else if(rm_drunk >= 35) . += list(list("Drunk", 2))
	else if(rm_drunk >= 15) . += list(list("Tipsy", 0))
	if(rm_immune > 0 && !rm_fever) . += list(list("Immune to the fever", 0))

// For 3D: 1-3 fever, 1 food poisoning or poison sickness (a cough or a retch now and then).
mob/Monsters/proc/RemasterIllLevel()
	if(rm_fever) return rm_fever
	if(rm_foodsick > 0 || (rm_poison > 0 && rm_poison_sick)) return 1
	return 0

// --- Drunk ---------------------------------------------------------------------------------------
mob/Monsters/proc/RemasterDrinkWine(u)
	if(!RemasterPoisonable()) return 0
	rm_drunk = min(100, rm_drunk + u * 2)
	RemasterRemember("drink", "Merry with wine", 6, 1)
	return 1

mob/Monsters/proc/RemasterDrunkTick(Player/P)
	rm_drunk = max(0, rm_drunk - 1)
	if(!isturf(loc) || Sleeping) return
	if(rm_drunk >= 85)
		view(src) << "[src] passes out drunk."
		rm_drunk -= 25
		RemasterEvent("Passed out drunk")
		Sleep(300)
		return
	if(rm_drunk >= 60 && prob(10)) RemasterVomit()
	// A stagger: a step the wrong way while walking (Move keeps every original rule).
	if(rm_drunk >= 35 && destination && prob(rm_drunk >= 60 ? 50 : 25))
		var/d = pick(NORTH, SOUTH, EAST, WEST)
		var/turf/T = get_step(src, d)
		if(T && !T.density) step(src, d)
	if(rm_drunk >= 35 && prob(6))
		view(src) << "[src] hiccups."
		RemasterSay("*hic*")
	else if(rm_drunk >= 35 && prob(4)) RemasterSay(RemasterLine(list("La la laaa!", "I love you all!", "Who moved the ground?")))

// An unhappy villager carrying wine has a drink (unless the player unticked it, Bag.dm).
mob/Monsters/proc/RemasterWineWhenSad(Player/P)
	if(!rm_moods_on || remaster_mood >= 35 || !prob(5) || !RemasterAutoUseOn("wine")) return
	for(var/obj/Items/Potions/RemasterBrew/B in src) if((B.brew["wine"] || 0) >= 1)
		P.RemasterDrinkBrew(src, B)
		P.RemasterLog("[RemasterBareName()] had a drink to cheer up", "info", src)
		return

// --- Rotten food -----------------------------------------------------------------------------
proc/RemasterFoodRotLoop()
	while(1)
		sleep(600)
		RemasterFoodRotStep()

// A minute on every piece of food in the world. Salted food ages an eighth as fast, food on a
// salted store a quarter (the store's salt is used up as it keeps it).
proc/RemasterFoodRotStep()
	var/list/kept = RemasterSaltedStoreFood(1)
	for(var/obj/Items/Food/F in world)
		F.rm_age += F.rm_salted ? 0.125 : kept[F] ? 0.25 : 1
		if(F.rm_age >= RM_ROT_GONE && isturf(F.loc))
			del F
			continue
		if(F.rm_age >= RM_ROT_AGE && !F.rm_rotten) RemasterMakeRotten(F)

// world/New: this file's part is step RmChainWorldNew_Ailments in Code/Remastered/Chains/WorldNew.dm

// Food kept by salt (food -> 1): lying on a store that has salt on it, or in a bag with salt in it.
// minutes: salt used up for that long (a lump keeps ten pieces for 60 minutes).
proc/RemasterSaltedStoreFood(minutes)
	var/list/kept = list()
	// Salt carried: the food in the same bag.
	var/list/bags = list()
	for(var/obj/Items/RemasterSalt/X in world) if(istype(X.loc, /mob/Monsters))
		if(!bags[X.loc]) bags[X.loc] = list()
		bags[X.loc] += X
	for(var/mob/Monsters/M in bags)
		var/n = 0
		for(var/obj/Items/Food/F in M) if(!kept[F])
			kept[F] = 1
			n++
		RemasterUseSalt(bags[M], -round(-n / 10) * minutes)
	for(var/Player/P in world) for(var/turf/S in P.RemasterStores())
		var/list/salt = list()
		for(var/obj/Items/RemasterSalt/X in range(1, S)) if(isturf(X.loc)) salt += X
		if(!length(salt)) continue
		var/n = 0
		for(var/obj/Items/Food/F in range(1, S)) if(isturf(F.loc) && !kept[F])
			kept[F] = 1
			n++
		RemasterUseSalt(salt, -round(-n / 10) * minutes)
	return kept

proc/RemasterUseSalt(list/salt, use)
	for(var/obj/Items/RemasterSalt/X in salt)
		if(use <= 0) break
		var/t = min(X.rm_salt_left, use)
		X.rm_salt_left -= t
		use -= t
		if(X.rm_salt_left <= 0)
			if(ismob(X.loc))
				var/mob/H = X.loc
				H.DropItem(X)
			del X

obj/Items/RemasterSalt
	// its values: art/items/catalogue.json row remastersalt (export_items.py writes ItemData.dm)
	var/rm_salt_left = 60          // minutes it keeps ten pieces of food on a store

	New()
		..()
		ItemDecay()

proc/RemasterSalt(obj/Items/Food/F)
	if(!F || F.rm_salted || F.rm_rotten) return 0
	F.rm_salted = 1
	F.name = "Salted [F.name]"
	F.desc = "Salted: it keeps eight times longer."
	return 1

// Salt the food this unit carries with one lump: up to four pieces, meat first.
mob/Monsters/proc/RemasterSaltFood(obj/Items/RemasterSalt/S)
	var/n = 0
	for(var/pass = 1, pass <= 2, pass++) for(var/obj/Items/Food/F in src)
		if(n >= 4 || F.suffix != "(Carrying)" || (pass == 1) != istype(F, /obj/Items/Food/Meat)) continue
		if(RemasterSalt(F)) n++
	if(n)
		if(S.loc == src) DropItem(S)
		del S
		RemasterEvent("Salted [n] piece\s of food")
	return n

// A cook with nothing to cook salts meat waiting on a store with salt on it (Food roles).
mob/Monsters/proc/RemasterCookSaltTick(Player/P)
	for(var/turf/S in P.RemasterStores()) if(S.z == z)
		var/obj/Items/RemasterSalt/salt
		for(var/obj/Items/RemasterSalt/X in range(1, S)) if(isturf(X.loc) && P.RemasterMayCollect(X))
			salt = X
			break
		if(!salt) continue
		var/list/meat = list()
		for(var/obj/Items/Food/Meat/F in range(1, S)) if(isturf(F.loc) && !F.rm_salted && !F.rm_rotten && F.rm_age >= 20 && length(meat) < 4) meat += F
		if(!length(meat)) continue
		if(!RemasterWorkToward(S, "stockpile")) return 1
		for(var/obj/Items/Food/F in meat) RemasterSalt(F)
		del salt
		remaster_work_status = "Salted [length(meat)] meat on the stockpile"
		return 1
	return 0

proc/RemasterMakeRotten(obj/Items/Food/F)
	F.rm_rotten = 1
	F.name = "Rotten [F.name]"
	F.desc = "This has gone off. Eating it will make you sick."

// The catch-up (Away.dm): the player's stored food ages over the time away.
Player/proc/RemasterAwayRot(minutes)
	var/n = 0
	var/list/kept = RemasterSaltedStoreFood(minutes)
	for(var/turf/S in RemasterStores()) for(var/obj/Items/Food/F in range(1, S)) if(isturf(F.loc))
		F.rm_age += minutes * (F.rm_salted ? 0.125 : kept[F] ? 0.25 : 1)
		if(F.rm_age >= RM_ROT_GONE)
			del F
			n++
		else if(F.rm_age >= RM_ROT_AGE && !F.rm_rotten) RemasterMakeRotten(F)
	RemasterAwayAdd("rotted", n)

// From the original EatItem() (Food.dm), before the meal: the smell of rot (refused unless
// starving: thrown away), and the poison's taste (FoodSupply.dm). 1 when not eaten.
mob/Monsters/proc/RemasterBeforeEat(obj/Items/ITEM)
	if(ITEM.rm_rotten && Hunger > 5 && RemasterPoisonable() && prob(70 + CookingSkill / 2))
		rm_spat_at = world.time
		view(src) << "[src] throws away the [ITEM]: it smells rotten."
		if(DropItem(ITEM)) del ITEM
		return 1
	if(ITEM.rm_poison > 0 && RemasterTastePoison(ITEM)) return 1
	return 0

// From the original EatItem(), after the meal: poison, rot, and a sick eater's germs.
mob/Monsters/proc/RemasterAfterEat(obj/Items/ITEM)
	if(ITEM.rm_poison > 0) RemasterAtePoison(ITEM)
	if(ITEM.rm_rotten && RemasterPoisonable())
		var/first = rm_foodsick <= 0
		rm_foodsick = max(rm_foodsick, 20)
		RemasterEvent("Ate rotten food")
		if(first)
			var/Player/P = Owner
			if(istype(P)) P.RemasterFoodAlarm(src, "[RemasterBareName()] ate rotten food and has food poisoning. Throw old food out, keep food in pots and stalls; a Thistle purge settles it.", "Sickness")
		if(prob(15)) RemasterCatchFever("rotten food")
	var/mob/WorkShops/RemasterFood/C = ITEM.rm_served_from
	if(istype(C))
		if(rm_fever) C.rm_germs = 3
		else if(C.rm_germs > 0)
			C.rm_germs--
			if(prob(30)) RemasterCatchFever("the [lowertext(C.name)]")

mob/Monsters/proc/RemasterFoodSickTick(Player/P)
	rm_foodsick--
	if(prob(8)) RemasterSay(RemasterLine(list("My stomach...", "Urgh...", "Never eating that again.")))
	if(prob(25)) RemasterVomit()
	Hunger = max(0, Hunger - 1)
	Tiredness = max(0, Tiredness - 0.5)
	if(rm_foodsick <= 0)
		rm_foodsick = 0
		RemasterEvent("Got over the food poisoning")

// --- Fever ---------------------------------------------------------------------------------------
mob/Monsters/proc/RemasterCatchFever(from)
	if(rm_fever || rm_fever_incub || rm_immune > 0 || !RemasterPoisonable() || GoingToDie) return 0
	rm_fever_incub = RM_FEVER_INCUBATE
	rm_fever_from = "[from]"
	return 1

mob/Monsters/proc/RemasterInBed()
	for(var/obj/Items/Furniture/Beds/B in loc) return 1
	return 0

mob/Monsters/proc/RemasterFeverTick(Player/P)
	if(rm_fever_incub > 0)
		if(--rm_fever_incub > 0) return
		rm_fever = 1
		rm_fever_t = 0
		view(src) << "[src] starts to cough."
		RemasterEvent("Caught a fever[rm_fever_from ? " from [rm_fever_from]" : ""]")
		if(istype(P))
			var/n = P.RemasterFeverCount()
			P.RemasterFoodAlarm(src, "[RemasterBareName()] has caught a fever[rm_fever_from ? " (from [rm_fever_from])" : ""]: [n] villager\s sick. It spreads to anyone near; keep the sick apart. A Doctor's Feverfew tonic cures it.", "Sickness")
		return
	rm_fever_t++
	// It spreads: anyone within a tile, sleepers within two (other realms' people too).
	if(isturf(loc)) for(var/mob/Monsters/O in range(2, src))
		if(O == src || O.HP <= 0 || O.rm_fever || O.rm_fever_incub) continue
		if(get_dist(O, src) > 1 && !O.Sleeping) continue
		if(prob(rm_fever >= 3 ? 6 : 3)) O.RemasterCatchFever(RemasterBareName())
	if(prob(rm_fever * 6))
		rm_cough_at = world.time
		view(src) << "[src] coughs."
		RemasterSay(rm_fever >= 3 ? "*hack* *hack*" : "*cough*")
	else if(rm_fever >= 2 && prob(3)) RemasterSay(RemasterLine(list("I feel terrible...", "So hot...", "Is it cold in here?")))
	// It breaks (resting in bed or asleep, three times likelier), or worsens with time.
	var/chance = list(2, 1.5, 1)[rm_fever] * ((Sleeping || RemasterInBed()) ? 3 : 1)
	if(prob(chance))
		RemasterFeverCured("The fever broke")
		return
	if(rm_fever_t >= RM_FEVER_STAGE && rm_fever < 3)
		rm_fever++
		rm_fever_t = 0
		view(src) << "[src] [rm_fever == 2 ? "is burning with fever" : "is gravely ill"]."
		if(rm_fever == 3 && istype(P)) P.RemasterFoodAlarm(src, "[RemasterBareName()] is gravely ill with the fever and may die. Feverfew tonic, or bed rest.", "Sickness")
	if(rm_fever >= 2) Tiredness = max(0, Tiredness - 0.5)
	if(rm_fever >= 3)
		HP -= 3
		if(prob(10)) RemasterVomit()
		if(HP <= 0)
			rm_fever = 0
			GoingToDie = 1
			Killer = "Fever"
			DeathType = "Fever"
			if(istype(P)) P.RemasterLog("[RemasterBareName()] died of the fever", "death", src)
			Death()

mob/Monsters/proc/RemasterFeverCured(note)
	rm_fever = 0
	rm_fever_incub = 0
	rm_fever_t = 0
	rm_immune = 600
	RemasterEvent(note)
	var/Player/P = Owner
	if(istype(P)) P.RemasterLog("[RemasterBareName()]: [lowertext(note)]", "good", src)

// Rot in the air: a body left lying smells on its own tile ("rot", Vapours.dm), so only those on it or right
// beside it can catch it from there; a plague cloud ("miasma") where they stand.
mob/Monsters/proc/RemasterFeverExposure()
	if(rm_immune > 0 || !isturf(loc)) return
	var/datum/rm_air/A = rm_air_of[loc]
	if(A && (A.gas["miasma"] || 0) > 1.5 && prob(4)) RemasterCatchFever("rot in the air")
	else
		for(var/turf/T in range(1, loc))
			var/datum/rm_air/R = rm_air_of[T]
			if(R && (R.gas["rot"] || 0) > 1 && prob(4))
				RemasterCatchFever("rot in the air")
				break

Player/proc/RemasterFeverCount()
	. = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0 && M.rm_fever) .++

// The catch-up (Away.dm): hours pass. The drink and the food poisoning wear off; a fever is cured
// with a tonic from the Doctor's stall when there is one, else rested off.
mob/Monsters/proc/RemasterAwayAilments(Player/P)
	rm_drunk = 0
	rm_foodsick = 0
	if(rm_fever || rm_fever_incub)
		var/mob/WorkShops/RemasterClinic/S = P.RemasterClinicWith("tonic", src)
		if(S)
			S.tonic--
			P.RemasterAwayAdd("treated")
		RemasterFeverCured(S ? "Cured of the fever with a Feverfew tonic" : "Rested off the fever")
