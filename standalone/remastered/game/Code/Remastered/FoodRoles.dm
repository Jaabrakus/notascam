#define RM_COOK_EVERY 30                  // deciseconds a cook spends on each meal at the fire (RuneScape: one every ~3 s)
mob/Monsters/var/tmp/remaster_cook_at = 0

// Food chain roles: Farmer, Hunter, Cook. They repeat the original game's own
// actions (the effects of the ClickFarm and Edibles HUD buttons, seed planting,
// Bump combat, TearMeat, the campfire/kitchen Cook option) without their input
// menus, inside a work area like the woodcutter/miner roles, and store the
// food on the stockpile. No new food rules: yields, growth time, winter seed
// loss, butchering gates and cooking success are all the original ones.

#define REMASTER_FOOD_AREA 10
#define REMASTER_FOOD_CARRY 4

// --- Stockpile items don't evaporate ---------------------------------------
// Dropped items count down to deletion (DeleteItem) unless picked up again.
// Items lying on a player's stockpile are kept.
atom/proc/RemasterOnStockpile()
	if(!isturf(loc)) return 0
	for(var/Player/P in world)
		for(var/turf/S in P.RemasterStores()) if(S.z == z && get_dist(S, src) <= 1) return 1
	return 0

// With the engine's timer (Native.dm rm_decay_native): the 2006 DeleteItem's start and its loop's first pass as they were,
// then the item to the timer, which makes every later pass 10 ticks after the last (RmDecay.cs). Without it, the 2006 loop.
atom/DeleteItem()
	if(!rm_decay_native) return ..()
	if(Content3) return
	spawn()
		if(icon_state == "Arm") Content3 = 80
		if(suffix)   // lifted before the loop's first look
			Content3 = null
			return
		Content3 += 1
		if(Content3 > 180) RmDecayOver(src)
		rm_decay_add(src, world.time)

// --- Shared helpers ---------------------------------------------------------
mob/Monsters/proc/RemasterFoodArea()
	var/turf/C = locate(remaster_area_x, remaster_area_y, remaster_area_z)
	return (C && C.z == z) ? C : loc

mob/Monsters/proc/RemasterCarriedFood(raw_only = 0, cooked_only = 0)
	var/list/out = list()
	for(var/obj/Items/Food/I in src) if(I.suffix == "(Carrying)")
		if(raw_only && I.icon_state != "RawMeat") continue
		if(cooked_only && I.icon_state != "CookedMeat") continue
		out += I
	return out

// Carry food to the stockpile and leave it there.
mob/Monsters/proc/RemasterStoreFood(Player/P, list/items, label)
	var/turf/S = P.RemasterStockpile()
	if(!S || S.z != z)
		remaster_work_status = "Set a stockpile on this level to store [label]"
		return 0
	if(!RemasterWorkToward(S, "stockpile")) return 1
	var/n = 0
	for(var/obj/Items/I in items) if(I.loc == src && DropItem(I))
		I.loc = S
		I.Owner = P
		n++
	remaster_work_status = "Stored [n] [label]"
	return 1

mob/Monsters/proc/RemasterFoodTick(Player/P)
	switch(remaster_job)
		if("farmer") RemasterFarmerTick(P)
		if("hunter") RemasterHunterTick(P)
		if("cook") RemasterCookTick(P)

// --- Farmer -----------------------------------------------------------------
mob/Monsters/proc/RemasterFarmerTick(Player/P)
	var/list/food = RemasterCarriedFood()
	if(length(food) >= REMASTER_FOOD_CARRY) return RemasterServeOrStore(P, food, "crops")   // a food stall or pot first (FoodSupply.dm)
	var/turf/A = RemasterFoodArea()
	// 1. Harvest ripe plants (Edibles HUD effect).
	var/obj/Items/Plants/ripe
	var/best = 1#INF
	for(var/obj/Items/Plants/G in range(REMASTER_FOOD_AREA, A))
		if(!(istype(G, /obj/Items/Plants/TomatoPlant) || istype(G, /obj/Items/Plants/GrapeVine)) || G.Content < 2) continue
		if(G.Owner && G.Owner != P) continue
		var/d = get_dist(src, G)
		if(d < best) { ripe = G; best = d }
	if(ripe)
		if(!RemasterWorkToward(ripe, "crop")) return
		RemasterHarvest(ripe)
		return
	if(length(food)) return RemasterServeOrStore(P, food, "crops")
	// 2. Plant carried seeds on free farmland (not in winter: winter kills seeds).
	var/obj/Items/Seeds/seed
	for(var/obj/Items/Seeds/S in src) if(S.suffix == "(Carrying)" && (istype(S, /obj/Items/Seeds/TomatoSeed) || istype(S, /obj/Items/Seeds/GrapeSeed)))
		seed = S
		break
	if(!seed && P.RmJzSeedsStored())   // a cheap look first: this one walks every item on every store (Jobs.dm, J2)
		// Take seeds from the stockpile.
		var/turf/ST = P.RemasterStoreWith(/obj/Items/Seeds, src) || P.RemasterStockpile()
		if(ST && ST.z == z) for(var/obj/Items/Seeds/S in range(1, ST))
			if(!isturf(S.loc) || !(istype(S, /obj/Items/Seeds/TomatoSeed) || istype(S, /obj/Items/Seeds/GrapeSeed))) continue
			if(!RemasterWorkToward(S, "seeds")) return
			if(PickUpItem(S)) remaster_work_status = "Took seeds from the stockpile"
			return
	if(seed && Season != "Winter")
		var/turf/F
		best = 1#INF
		for(var/turf/T in range(REMASTER_FOOD_AREA, A))
			if(T.icon_state != "FarmLand" || T.density || (("HasPlantIn" in T.vars) && T.vars["HasPlantIn"])) continue
			var/taken = 0
			for(var/obj/Items/Seeds/X in T) taken = 1
			for(var/obj/Items/Plants/X in T) taken = 1
			if(taken) continue
			var/d = get_dist(src, T)
			if(d < best) { F = T; best = d }
		if(F)
			if(loc != F)
				destination = F
				remaster_work_destination = F
				remaster_work_status = "Walking to farmland"
				return
			RemasterPlant(seed, F)
			return
		// 3. No free farmland: till grass next to the farmer (ClickFarm effect; needs a spade).
		if(RemasterHasSpade())
			var/turf/G
			best = 1#INF
			var/farmland = 0
			for(var/turf/T in range(REMASTER_FOOD_AREA, A)) if(T.icon_state == "FarmLand") farmland++
			if(farmland < 18) for(var/turf/T in range(REMASTER_FOOD_AREA - 2, A))
				if(!istype(T, /turf/grounds) || T.icon_state != "Grass" || T.density) continue
				var/d = get_dist(src, T)
				if(d < best) { G = T; best = d }
			if(G)
				if(get_dist(src, G) > 1)
					destination = G
					remaster_work_destination = G
					remaster_work_status = "Walking to till the soil"
					return
				var/n = 0
				for(var/turf/grounds/W in view(1, src)) if(W.icon_state == "Grass")
					W.icon = 'Cave.dmi'
					W.icon_state = "FarmLand"
					W.name = "FarmLand"
					W.Detailed = 1
					n++
				remaster_work_status = "Tilled [n] tile\s of farmland"
				return
			remaster_work_status = "No free farmland or grass to till in the work area"
			return
		remaster_work_status = "Needs a spade to make farmland (Carpentry: wooden spade)"
		return
	if(seed) remaster_work_status = "Waiting for spring: seeds die if planted in winter"
	else remaster_work_status = "Waiting for crops to ripen (put seeds on the stockpile to plant more)"

mob/Monsters/proc/RemasterHasSpade()
	for(var/obj/Items/Shafts/Spade/S in src) return 1
	for(var/obj/Items/Shafts/WoodenSpade/S in src) return 1
	return 0

// The planting effect of the original seed "Plant" menu (Turfs.dm).
mob/Monsters/proc/RemasterPlant(obj/Items/Seeds/S, turf/T)
	S.loc = T
	S.suffix = "(Planted)"
	weight -= S.weight
	S.icon_state = ""
	if("HasPlantIn" in T.vars) T.vars["HasPlantIn"] = 1
	if(istype(S, /obj/Items/Seeds/TomatoSeed)) spawn() S:TomatoGrow()
	else spawn() S:GrapeGrow()
	remaster_work_status = "Planted [S.name]"

// The harvest effect of the original Edibles HUD button, for one plant.
mob/Monsters/proc/RemasterHarvest(obj/Items/Plants/G)
	var/obj/Items/Food/F
	if(G.Content >= 2)
		G.Content -= 1
		F = istype(G, /obj/Items/Plants/GrapeVine) ? new/obj/Items/Food/Grape(loc) : new/obj/Items/Food/Tomato(loc)
	var/prefix = istype(G, /obj/Items/Plants/GrapeVine) ? "PPlant" : "Plant"
	if(G.Content >= 1) G.icon_state = "[prefix]5"
	if(G.Content >= 2) G.icon_state = "[prefix]4"
	if(G.Content >= 3) G.icon_state = "[prefix]3"
	if(G.Content >= 4) G.icon_state = "[prefix]2"
	if(G.Content <= 0)
		for(var/turf/e in view(0, G)) if("HasPlantIn" in e.vars) e.vars["HasPlantIn"] = 0
		del(G)
	if(F && PickUpItem(F))
		remaster_work_status = "Harvested [F.name]"
		if(rm_jz_id && istype(Owner, /Player)) Owner:RmJzCountOut(rm_jz_id)   // its farm row's +N a minute (it read +0 while the farm fed the village)

// --- Hunter -----------------------------------------------------------------
mob/Monsters/proc/RemasterCanButcher()
	return Carn || HoldingWeapon == "Butcher Knife" || HoldingWeapon == "Dagger"

mob/Monsters/proc/RemasterHunterTick(Player/P)
	var/list/meat = RemasterCarriedFood()
	if(length(meat) >= REMASTER_FOOD_CARRY) return RemasterStoreFood(P, meat, "meat")
	if(!RemasterCanButcher() && !RemasterHunterKnife())
		remaster_work_status = "Needs a dagger or butcher knife to butcher (only meat-eating races can tear meat by hand)"
		return
	var/turf/A = RemasterFoodArea()
	// 1. Butcher a carried body (TearMeat, knife in hand; one dragged beside it is taken up: BodyDrag.dm), then pick up the meat.
	for(var/mob/Body/B in RmHeldBodies()) if(B.suffix == "(Carrying)")
		if(!RemasterCanButcher()) RemasterHunterWield("knife")
		TearMeat(B)
		for(var/obj/Items/Food/Meat/M in range(0, src)) PickUpItem(M)
		remaster_work_status = "Butchered the catch"
		return
	// 2. Pick up a body lying nearby.
	for(var/mob/Body/B in range(REMASTER_FOOD_AREA, A)) if(isturf(B.loc) && (B.Critter || B.Race == "Fish"))
		if(!RemasterWorkToward(B, "the kill")) return
		if(PickUpItem(B))
			remaster_work_status = "Picked up the kill"
			return
		// Too heavy to carry: butchered where it lies (knife in hand), the meat taken along.
		if(!RemasterCanButcher()) RemasterHunterWield("knife")
		ForcePickUpItem(B)
		TearMeat(B)
		for(var/obj/Items/Food/Meat/M in range(1, src)) if(isturf(M.loc)) PickUpItem(M)
		remaster_work_status = "Butchered the kill where it lay"
		return
	// 3. Hunt an animal (plants and pets excluded): a bow from up to 5 tiles off when it has arrows
	//    (the original single shot, BowTarget, every 5 s as attack orders shoot), else thrown
	//    weapons from a few tiles off (javelins, throwing axes, stones: Throwing.dm), and Bump
	//    combat once it's beside it.
	var/mob/Monsters/prey
	var/best = 1#INF
	for(var/mob/Monsters/C in range(REMASTER_FOOD_AREA + 5, A))
		if(!C.Critter || C.HP <= 0 || C.Owner == Owner) continue
		if(istype(C, /mob/Monsters/Critters/TowerCap) || istype(C, /mob/Monsters/Critters/PoisonSporePlant) || istype(C, /mob/Monsters/Critters/CarnivorousPlant)) continue
		var/d = get_dist(src, C)
		if(d < best) { prey = C; best = d }
	// No arrows (with a bow) or nothing left to throw: pick up what was shot or thrown, else take
	// some from the stockpile.
	if(prey && RemasterHunterBow() && !RemasterQuiverCount(src) && RemasterHunterRearm(P, A, 0, 1)) return
	if(prey && !RemasterThrowable(2) && !(RemasterHunterBow() && RemasterQuiverCount(src)) && RemasterHunterRearm(P, A)) return
	if(prey && RemasterHunterBow() && RemasterQuiverCount(src) && RemasterHunterWield("Bow"))
		var/what = prey.name
		if(prey in oview(5, src))
			destination = null
			remaster_work_destination = null
			if(world.time >= remaster_hunt_shot_at)
				remaster_hunt_shot_at = world.time + 50
				Target = prey
				BowOn = 1
				BowTarget(1)
				BowOn = 0
				Target = null
				remaster_work_status = "Shooting at [what]"
			else remaster_work_status = "Nocking an arrow for [what]"
			return
		destination = prey
		remaster_work_destination = prey
		remaster_work_status = "Stalking [what]"
		return
	if(prey)
		var/d = get_dist(src, prey)
		if(d >= 2 && RemasterThrowable(d) && (prey in oview(6, src)))
			destination = null
			remaster_work_destination = null
			var/what = prey.name                // a killing throw deletes the prey
			if(RemasterTryThrow(prey)) remaster_work_status = "Throwing at [what]"
			else remaster_work_status = "Taking aim at [what]"
			return
		destination = prey
		remaster_work_destination = prey
		remaster_work_status = d >= 2 && RemasterThrowable(2) ? "Closing in on [prey.name]" : "Hunting [prey.name]"
		return
	// The hunt is over: arrows and thrown weapons lying about are picked up again.
	if(RemasterHunterBow() && RemasterHunterRearm(P, A, 1, 1)) return
	if(RemasterHunterRearm(P, A, 1)) return
	if(length(meat)) return RemasterStoreFood(P, meat, "meat")
	// 4. No animals: fish a fishing spot nearby (Fishing.dm), else bump fishing water.
	var/obj/RemasterFishSpot/spot
	best = 1#INF
	for(var/obj/RemasterFishSpot/S in rm_fish_spots) if(S.z == z && get_dist(S, A) <= REMASTER_FOOD_AREA && RemasterFishMethod(S))
		var/d = get_dist(src, S)
		if(d < best) { spot = S; best = d }
	if(spot)
		remaster_fish_spot = spot
		RemasterFishTick()
		return
	var/turf/water
	best = 1#INF
	for(var/turf/T in range(REMASTER_FOOD_AREA, A)) if(("CanFish" in T.vars) && T.vars["CanFish"] && T.density)
		var/d = get_dist(src, T)
		if(d < best) { water = T; best = d }
	if(water)
		destination = water
		remaster_work_destination = water
		remaster_work_status = "Fishing"
		return
	remaster_work_status = "No animals or fishing water in the work area"

mob/Monsters/var/tmp/remaster_hunt_shot_at = 0

// A dagger or butcher knife carried (butchering needs one in hand: RemasterCanButcher).
mob/Monsters/proc/RemasterHunterKnife()
	for(var/obj/Items/Equipment/Weapon/W in src) if((W.suffix == "(Carrying)" || W.suffix == "(Equipped)") && (W.ItemType in list("Dagger", "Butcher Knife"))) return W
	return null

// A bow carried or held.
mob/Monsters/proc/RemasterHunterBow()
	if(HoldingWeapon == "Bow") return 1
	for(var/obj/Items/Equipment/Weapon/W in src) if(W.suffix == "(Carrying)" && W.ItemType == "Bow") return 1
	return 0

// Take the bow (and put the quiver on), or a knife, in hand.
mob/Monsters/proc/RemasterHunterWield(kind)
	if(kind == "Bow")
		if(!WearingBack) for(var/obj/Items/Equipment/Armour/Quiver/LeatherQuiver/Q in src) if(Q.suffix == "(Carrying)")
			EquipItem(Q)
			break
		if(HoldingWeapon == "Bow") return 1
		for(var/obj/Items/Equipment/Weapon/W in src) if(W.suffix == "(Carrying)" && W.ItemType == "Bow")
			EquipItem(W)
			break
		return HoldingWeapon == "Bow"
	if(RemasterCanButcher()) return 1
	var/obj/Items/K = RemasterHunterKnife()
	if(K && K.suffix == "(Carrying)") EquipItem(K)
	return RemasterCanButcher()

// Arrows lying beside the hunter into its quiver (the original "pick up arrows" effect).
mob/Monsters/proc/RemasterHunterQuiverUp()
	var/n = 0
	for(var/obj/Items/Equipment/Armour/Quiver/LeatherQuiver/L in src) if(L.suffix == "(Equipped)" && L.Content <= 250)
		for(var/obj/Items/Arrows/X in range(1, src)) if(isturf(X.loc))
			X.loc = L
			X.Owner = Owner
			L.Content += 1
			n++
	return n

// Arrows (arrows = 1) or javelins and throwing axes for the hunt: the ones lying in the area (shot
// or thrown earlier), else from a store. Returns 1 while busy with it. ground_only: only pick up
// what lies about.
mob/Monsters/proc/RemasterHunterRearm(Player/P, turf/A, ground_only = 0, arrows = 0)
	if(arrows)
		RemasterHunterWield("Bow")
		if(!WearingBack) return 0
		var/obj/Items/Arrows/R
		var/best_r = 1#INF
		for(var/obj/Items/Arrows/X in range(REMASTER_FOOD_AREA + 5, A))
			if(!isturf(X.loc) || RemasterOnStore(X) || !P.RemasterMayCollect(X)) continue
			var/d = get_dist(src, X)
			if(d < best_r) { R = X; best_r = d }
		if(R)
			if(!RemasterWorkToward(R, "arrows")) return 1
			remaster_work_status = "Gathered [RemasterHunterQuiverUp()] arrows"
			return 1
		if(ground_only) return 0
		var/turf/AS = P.RemasterStoreWith(/obj/Items/Arrows, src)
		if(!AS || AS.z != z) return 0
		if(get_dist(src, AS) > 1 && !RemasterWorkToward(AS, "stockpile")) return 1
		var/got = RemasterHunterQuiverUp()
		remaster_work_status = got ? "Took [got] arrow\s from the stockpile" : "No room for arrows"
		return got > 0
	var/obj/Items/Thrown/J
	var/best = 1#INF
	for(var/obj/Items/Thrown/X in range(REMASTER_FOOD_AREA + 5, A))
		if(!isturf(X.loc) || RemasterOnStore(X) || !P.RemasterMayCollect(X) || X.weight + weight > weightmax) continue
		var/d = get_dist(src, X)
		if(d < best) { J = X; best = d }
	if(J)
		if(!RemasterWorkToward(J, "thrown weapon")) return 1
		if(PickUpItem(J)) remaster_work_status = "Picked up a [lowertext(J.name)]"
		return 1
	if(ground_only) return 0
	var/turf/ST = P.RemasterStoreWith(/obj/Items/Thrown, src)
	if(!ST || ST.z != z) return 0
	if(get_dist(src, ST) > 1)
		if(!RemasterWorkToward(ST, "stockpile")) return 1
	var/n = 0
	for(var/obj/Items/Thrown/X in range(1, ST)) if(isturf(X.loc) && n < 4 && P.RemasterMayCollect(X) && X.weight + weight <= weightmax)
		if(PickUpItem(X)) n++
	remaster_work_status = n ? "Took [n] [n == 1 ? "thing" : "things"] to throw from the stockpile" : "Can't carry anything to throw"
	return n > 0

// --- Cook -------------------------------------------------------------------
mob/Monsters/proc/RemasterCookTick(Player/P)
	if(Race == "Spider" || Wagon)
		remaster_work_status = "This unit can't cook"
		return
	var/list/cooked = RemasterCarriedFood(0, 1)
	var/list/raw = RemasterCarriedFood(1)
	// Cooked food goes to a food pot or stall when there is one (FoodSupply.dm), else the stockpile.
	if(length(cooked) && (!length(raw) || length(cooked) >= REMASTER_FOOD_CARRY)) return RemasterServeOrStore(P, cooked, "cooked meat")
	if(RemasterCookPressWine(P, 0)) return   // carrying fruit and fungus to press for the tavern (Tavern.dm)
	var/list/other = RemasterCarriedFood() - cooked - raw   // fruit and the like taken to restock them
	if(length(other)) return RemasterServeOrStore(P, other, "food")
	var/turf/ST = P.RemasterStoreWith(/obj/Items/Food/Meat, src, "RawMeat") || P.RemasterStockpile()
	if(!length(raw))
		if(!ST || ST.z != z)
			remaster_work_status = "Set a stockpile on this level"
			return
		for(var/obj/Items/Food/Meat/M in range(1, ST)) if(isturf(M.loc) && M.icon_state == "RawMeat" && P.RemasterMayCollect(M))
			if(!RemasterWorkToward(M, "raw meat")) return
			var/n = 0
			for(var/obj/Items/Food/Meat/X in range(1, src)) if(isturf(X.loc) && X.icon_state == "RawMeat" && n < REMASTER_FOOD_CARRY && P.RemasterMayCollect(X))
				if(PickUpItem(X)) n++
			remaster_work_status = n ? "Took [n] raw meat to cook" : "Can't carry more"
			RemasterCookTakeWood(P, ST)   // and wood for a Food pot's fire (FoodSupply.dm)
			return
		if(RemasterRestockFood(P)) return
		if(RemasterCookSaltTick(P)) return   // salt meat that's waiting (Ailments.dm)
		if(RemasterCookPressWine(P)) return  // wine for the tavern (Tavern.dm)
		remaster_work_status = "Waiting for raw meat on the stockpile"
		return
	// A Food pot near the stockpile with a fire to keep stews the meat without burning it (FoodSupply.dm).
	var/mob/WorkShops/RemasterFood/Pot/pot = P.RemasterCookPot(src, ST)
	if(pot && RemasterPotFire(P, pot)) return RemasterCookAtPot(P, pot, raw)
	// Nearest campfire or kitchen within 15 tiles of the stockpile or the cook.
	var/atom/C = (ST && ST.z == z) ? ST : src
	var/mob/WorkShops/fire
	var/best = 1#INF
	for(var/mob/WorkShops/W in range(15, C))
		if(!(istype(W, /mob/WorkShops/CampFires/Fire) || istype(W, /mob/WorkShops/Kitchen/Right))) continue
		if(W.Owner && W.Owner != P) continue
		var/d = get_dist(src, W)
		if(d < best) { fire = W; best = d }
	if(!fire)
		remaster_work_status = "Needs a campfire or kitchen near the stockpile"
		return
	if(!RemasterWorkToward(fire, "fire")) return
	// A meal takes a few seconds over the fire, as in RuneScape (one every 3 s), not one every tick.
	if(world.time < remaster_cook_at)
		remaster_work_status = "Cooking"
		return
	// The original Cook option's effect, one meat per step.
	for(var/obj/Items/Food/Meat/B in src) if(B.icon_state == "RawMeat" && B.suffix == "(Carrying)")
		remaster_cook_at = world.time + RM_COOK_EVERY
		if(!prob(CookingSkill * 4))
			weight -= B.weight
			del(B)
			CookingSkill += 2
			remaster_work_status = "Burnt a piece of meat"
		else
			B.name = "Cooked [B.name]"
			B.icon_state = "CookedMeat"
			CookingSkill += 1
			remaster_work_status = "Cooked [B.name]"
		break
