// Self-care and homes (planning/VILLAGE_LIFE.md, part 1).
// The original game already eats carried/nearby food, heals, and sleeps on a
// bed within 20 tiles or a carried sleeping bag. This adds what was missing:
// a saved home bed, sleeping rough when there is no bed, walking to a fire
// when cold, and walking to the stockpile for food. Care briefly takes over a
// villager; their orders and job are kept and resume afterwards.

#define REMASTER_CARE_EVERY 6      // RemasterTrack calls (about 3 seconds)
#define REMASTER_CARE_TIRED 20
#define REMASTER_CARE_COLD 40
#define REMASTER_CARE_WARM 5
#define REMASTER_CARE_HUNGRY 20
#define REMASTER_CARE_GIVE_UP 1200 // 2 minutes

mob/Monsters/var
	list/remaster_home              // list(x, y, z) of the villager's own bed
mob/Monsters/var/tmp
	remaster_care                   // null, "sleep", "warm" or "eat"
	remaster_care_status
	atom/remaster_care_target
	remaster_care_since = 0
	remaster_care_note              // last care outcome, shown in the roster
	remaster_care_hold = 0          // a player command holds care off until this time
	list/remaster_care_retry        // kind -> time before trying that kind of care again
	remaster_care_dest              // the destination care itself set
Player/var/tmp/remaster_care_clock = 0

mob/Monsters/proc/RemasterNeedsSleep()
	return !(Race in list("Gargoyle", "Elf", "Zombie", "Svartalfar", "Devourer")) && !Undead

mob/Monsters/proc/RemasterFeelsCold()
	return !ImmuneToTemperature && !Undead && !CanBeSlaved

mob/Monsters/proc/RemasterCarriedBed()
	for(var/obj/Items/Furniture/Beds/B in src) return B
	return null

proc/RemasterBedAt(list/H)
	if(!islist(H) || length(H) != 3) return null
	var/turf/T = locate(H[1], H[2], H[3])
	if(!T) return null
	for(var/obj/Items/Furniture/Beds/B in T) return B
	return null

mob/Monsters/proc/RemasterHomeText()
	if(RemasterCarriedBed()) return "Sleeping bag"
	if(RemasterBedAt(remaster_home)) return "Bed at [remaster_home[1]], [remaster_home[2]]"
	if(!RemasterNeedsSleep()) return "Doesn't sleep"
	return "No bed"

mob/Monsters/proc/RemasterCareStart(kind, atom/target, turf/walk_to, status)
	remaster_care = kind
	remaster_care_target = target
	remaster_care_since = world.time
	remaster_care_status = status
	if(walk_to)
		destination = walk_to
		remaster_care_dest = walk_to

mob/Monsters/proc/RemasterCareDone(note)
	// Only clear a destination care set itself (never a defense or player move).
	if(destination && destination == remaster_care_dest) destination = null
	remaster_care_dest = null
	remaster_care = null
	remaster_care_target = null
	remaster_care_status = null
	if(note) remaster_care_note = note

// A free, walkable tile next to a dense target (fires are dense).
proc/RemasterTileNear(atom/A, mob/M)
	var/turf/best
	var/best_d = 1#INF
	for(var/turf/T in range(2, A))
		if(T.density) continue
		var/blocked = 0
		for(var/atom/movable/O in T) if(O.density && O != M)
			blocked = 1
			break
		if(blocked) continue
		var/d = get_dist(T, M)
		if(d < best_d)
			best = T
			best_d = d
	return best

Player/proc/RemasterCareTick(spread = 0)
	remaster_care_clock++
	if(remaster_care_clock % REMASTER_CARE_EVERY) return
	var/list/claimed = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && islist(M.remaster_home) && length(M.remaster_home) == 3)
		claimed["[M.remaster_home[1]],[M.remaster_home[2]],[M.remaster_home[3]]"] = M
	var/rm_n = 0   // units since the last safe point (Spread.dm)
	for(var/mob/Monsters/M in UnitList)
		RmCareUnit(M, claimed)
		if(spread && ++rm_n >= 16)   // a safe point every 16 units (Spread.dm compiles after this file)
			rm_n = 0
			RmTrackPause()

// A player command (order, stop, job change, manual action) wins over care.
mob/Monsters/proc/RemasterCareInterrupt()
	if(remaster_care) RemasterCareDone("Stopped by your order")
	remaster_care_hold = world.time + 600

mob/Monsters/proc/RemasterCareBlocked(kind)
	return remaster_care_retry && remaster_care_retry[kind] && world.time < remaster_care_retry[kind]

mob/Monsters/proc/RemasterEnemyNear(range = 7)
	for(var/mob/Monsters/E in oview(range, src))
		if(E.HP <= 0 || E.Critter || E.Owner == Owner) continue
		return 1
	return 0

mob/Monsters/proc/RemasterCareStep(Player/P, list/claimed)
	if(HP <= 0 || GoingToDie || !isturf(loc) || InHole || remaster_defense || Fainted || Stunned)
		if(remaster_care) RemasterCareDone()
		return
	if(Sleeping)
		if(remaster_care) RemasterCareDone("Slept")
		return
	if(remaster_care && world.time - remaster_care_since > REMASTER_CARE_GIVE_UP)
		// Unreachable: wait 5 minutes before trying this kind of care again.
		if(!remaster_care_retry) remaster_care_retry = list()
		remaster_care_retry[remaster_care] = world.time + 3000
		if(remaster_care == "sleep") remaster_home = null
		var/what = remaster_care == "warm" ? "the fire" : remaster_care == "sleep" ? "bed" : "food"
		if(istype(Owner, /Player)) Owner:RemasterLog("[name] couldn't reach [what]", "problem", src)
		RemasterCareDone("Gave up: couldn't reach [what]")
		return
	switch(remaster_care)
		if("warm") return RemasterCareWarm()
		if("sleep") return RemasterCareSleep(P, claimed)
		if("eat") return RemasterCareEat(P)
		if("help") return RemasterCareHelp()
		if("remedy") return RemasterCareRemedy(P)       // Doctor.dm
		if("tavern") return RemasterCareTavern(P)       // Tavern.dm
	// Nothing in progress. Never take over a unit the player is directing.
	if(world.time < remaster_care_hold || Target) return
	if(RemasterHasOrder() && !(remaster_active && remaster_active.automatic)) return
	var/automatic = (remaster_active && remaster_active.automatic) || remaster_delivery
	if(destination && destination != remaster_work_destination && !automatic) return
	// Most dangerous first.
	if(RemasterFeelsCold() && Coldness >= REMASTER_CARE_COLD && !RemasterCareBlocked("warm"))
		var/mob/WorkShops/CampFires/F = RemasterNearestFire()
		if(F)
			var/turf/T = RemasterTileNear(F, src)
			if(T)
				RemasterCareStart("warm", F, T, "Cold: going to the fire at [F.x], [F.y]")
				return
		remaster_care_note = "Cold: no campfire within 25 tiles"
	if(RemasterNeedsSleep() && Tiredness <= REMASTER_CARE_TIRED && !IsMist && !Flying && !(Race in list("Spider", "Dragon")) && !RemasterCarriedBed() && !RemasterCareBlocked("sleep"))
		RemasterCareSleep(P, claimed)
		return
	// Ill or badly hurt, and no Doctor: a remedy from the Doctor's stall, or one carried (Doctor.dm).
	var/list/need = RemasterNeeds()
	if(need && !RemasterCareBlocked("remedy"))
		var/obj/Items/RemasterRemedy/carried = RemasterCarriedRemedy(need[1])
		if(carried && RemasterAutoUseOn("remedy") && RemasterApplyRemedy(need[1], src))
			weight -= carried.weight
			del carried
			return
		if(!P.RemasterHasDoctor())
			var/mob/WorkShops/RemasterClinic/K = P.RemasterClinicWith(need[1], src)
			var/turf/KT = K ? RemasterTileNear(K, src) : null
			if(KT)
				RemasterCareStart("remedy", K, KT, "Ill ([need[3]]): going to the Doctor's stall for the [RemasterRemedyName(need[1])]")
				return
	if(Hunger <= REMASTER_CARE_HUNGRY && !(Race in list("Gargoyle", "Vampire", "Zombie", "Devourer")) && !RemasterCareBlocked("eat"))
		var/has_food = 0
		for(var/obj/Items/Food/I in src)
			has_food = 1
			break
		if(!has_food)
			// A food pot or stall first (FoodSupply.dm); the stockpile when there is none with food.
			var/mob/WorkShops/RemasterFood/C = P.RemasterFoodPlace(src)
			var/turf/CT = C ? RemasterTileNear(C, src) : null
			if(CT)
				RemasterCareStart("eat", C, CT, "Hungry: going to the [lowertext(C.name)] for food")
				return
			var/turf/S = P.RemasterStockpile()
			if(!S || S.z != z || !RemasterFoodNear(S)) S = P.RemasterStoreWith(/obj/Items/Food, src) || S
			if(S && S.z == z && get_dist(S, src) <= 60 && RemasterFoodNear(S))
				RemasterCareStart("eat", S, S, "Hungry: going to the stockpile for food")
				return
			RemasterSay(RemasterLine(list("I'm starving...", "Is there no food?", "My belly aches.")))
			var/mob/Monsters/helper = P.RemasterFoodHelper(src)
			if(helper)
				helper.RemasterCareStart("help", src, loc, "Bringing food to [name]")
				remaster_care_note = "Hungry: [helper.name] is bringing food"
			else remaster_care_note = "Hungry: no food carried or in the stockpile"
	else if(RemasterTavernWanted(P)) return             // off duty: a drink at the tavern (Tavern.dm)

mob/Monsters/proc/RemasterNearestFire()
	var/mob/WorkShops/CampFires/best
	var/best_d = 26
	for(var/mob/WorkShops/CampFires/F in range(25, src))
		var/d = get_dist(F, src)
		if(d < best_d)
			best = F
			best_d = d
	return best

proc/RemasterFoodNear(turf/S)
	for(var/obj/Items/Food/I in range(2, S)) if(isturf(I.loc)) return 1
	return 0

mob/Monsters/proc/RemasterCareWarm()
	var/atom/F = remaster_care_target
	if(Coldness <= REMASTER_CARE_WARM) return RemasterCareDone("Warmed up by the fire")
	if(!F || !F.z || F.z != z) return RemasterCareDone("The fire went out")
	if(get_dist(src, F) > 3)
		var/turf/T = RemasterTileNear(F, src)
		if(T && destination != T) destination = T
	else
		destination = null
		remaster_care_status = "Warming up by the fire"

mob/Monsters/proc/RemasterCareSleep(Player/P, list/claimed)
	var/obj/Items/Furniture/Beds/B = RemasterBedAt(remaster_home)
	if(!B && remaster_home)
		remaster_home = null // the bed was moved or destroyed
	if(!B)
		var/best_d = 31
		for(var/obj/Items/Furniture/Beds/C in range(30, src))
			if(!isturf(C.loc)) continue
			if(C.Owner && C.Owner != P) continue // not someone else's bed
			var/key = "[C.x],[C.y],[C.z]"
			if(claimed[key] && claimed[key] != src) continue
			var/d = get_dist(C, src)
			if(d < best_d)
				B = C
				best_d = d
		if(B)
			remaster_home = list(B.x, B.y, B.z)
			claimed["[B.x],[B.y],[B.z]"] = src
			P.RemasterNotice("[name] claimed the bed at [B.x], [B.y] as home.")
	if(!B || B.z != z)
		// Never fall asleep next to enemies; rough sleep is less restful than a bed.
		if(Target || RemasterEnemyNear())
			remaster_care_note = "Tired, but enemies are near"
			return
		RemasterCareDone("Slept rough: no bed")
		destination = null
		Sleep(450)
		spawn(460) if(src && !Sleeping) Tiredness = min(Tiredness, 70)
		return
	if(loc == B.loc)
		RemasterCareDone("Slept in own bed")
		destination = null
		Sleep(max(40, 300 - B.CR))
		return
	if(remaster_care != "sleep") RemasterCareStart("sleep", B, B.loc, "Tired: going home to bed at [B.x], [B.y]")
	else if(destination != B.loc) destination = B.loc

mob/Monsters/proc/RemasterCareEat(Player/P)
	var/turf/S = remaster_care_target
	if(Hunger > REMASTER_CARE_HUNGRY) return RemasterCareDone("Ate")
	if(istype(S, /mob/WorkShops/RemasterFood)) return RemasterCareEatServed(P)   // FoodSupply.dm
	if(!S || !RemasterFoodNear(S)) return RemasterCareDone("The stockpile ran out of food")
	if(get_dist(src, S) <= 2)
		if(EatSomething()) return RemasterCareDone("Ate from the stockpile")
		return RemasterCareDone("Couldn't eat the stockpile food")
	if(destination != S) destination = S

// --- Neighbours help ---------------------------------------------------------
// Someone hungry with no food anywhere: the nearest villager with food to spare
// walks over. The original EatSomething() lets a hungry unit take food from
// anyone within 5 tiles, so once the helper is close the original rule feeds them.
Player/proc/RemasterFoodHelper(mob/Monsters/H)
	for(var/mob/Monsters/M in UnitList) if(M.remaster_care == "help" && M.remaster_care_target == H) return null
	var/mob/Monsters/best
	var/best_d = 21
	for(var/mob/Monsters/M in UnitList)
		if(M == H || M.Owner != src || M.remaster_care || M.Wagon || M.Egg || M.Critter || M.HP <= 0 || M.z != H.z || !isturf(M.loc)) continue
		if(M.Target || M.remaster_defense || world.time < M.remaster_care_hold) continue
		if(M.RemasterHasOrder() && !(M.remaster_active && M.remaster_active.automatic)) continue
		var/food = 0
		for(var/obj/Items/Food/I in M) food++
		// Keep one for themselves when they're getting hungry too.
		if(food < (M.Hunger <= REMASTER_CARE_HUNGRY * 2 ? 2 : 1)) continue
		var/d = get_dist(M, H)
		if(d < best_d)
			best = M
			best_d = d
	return best

mob/Monsters/proc/RemasterCareHelp()
	var/mob/Monsters/H = remaster_care_target
	if(!istype(H) || H.HP <= 0 || H.z != z) return RemasterCareDone()
	if(H.Hunger > REMASTER_CARE_HUNGRY) return RemasterCareDone("[H.name] has eaten")
	var/has = 0
	for(var/obj/Items/Food/I in src) has = 1
	if(!has) return RemasterCareDone("Ran out of food to share")
	if(get_dist(src, H) <= 1)
		var/before = H.Hunger
		H.EatSomething()
		if(H.Hunger > before)
			H.remaster_care_note = "[name] shared food"
			return RemasterCareDone("Shared food with [H.name]")
		return RemasterCareDone("[H.name] couldn't eat")
	if(destination != H.loc)
		destination = H.loc
		remaster_care_dest = H.loc

// One unit of the care pass (RemasterCareTick), as the pass did it in one go (server cost, 2026-10-24).
Player/proc/RmCareUnit(mob/Monsters/M, list/claimed)
	if(M.Owner != src || M.Wagon || M.Egg || M.Critter) return
	if(M.rm_poison > 0) M.RemasterPoisonTick(src)   // poisoned food (FoodSupply.dm)
	if(Rm3DGone(M)) return                          // died of it: the ref isn't null in OpenDream, and a call on it ends the whole pass
	M.RemasterAilmentTick(src)                      // drink, rotten food, fever (Ailments.dm)
	if(Rm3DGone(M)) return
	M.RemasterCareStep(src, claimed)
