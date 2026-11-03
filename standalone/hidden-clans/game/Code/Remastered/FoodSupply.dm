// Food pots and food stalls (Remastered): where villagers get their meals instead of off the
// stockpile, so a village's food supply can be poisoned the way Space Station 13 does it.
//  - Both are food stores like a stockpile: food in them never rots and counts in the village's
//    food stock; cooks, farmers and the cooks' restocking from the stockpile fill them.
//  - Food pot (1 stone): a cauldron for food. It has its own fire (wood as fuel, a minute per
//    piece, like the Cauldron) and holds 20 servings. Over the fire it stews raw meat and fungus
//    without burning them (a campfire burns meat the cook fails at), and a hot pot serves Hot
//    stew: a quarter more filling and a good meal for the eater's mood.
//  - Food stall (1 wood): a counter holding 30 pieces of food. A villager who eats there takes a
//    piece along for later, so fewer trips are made across the village.
//  - Hungry villagers walk to the nearest pot or stall with food for them (Care.dm) and eat a
//    serving with the original EatItem() (food values, raw meat only good for meat eaters, seeds,
//    moods). With none, the stockpile is the fallback, as before. The offline catch-up eats here
//    too (Away.dm).
//  - Poisoning: a unit carrying a poison - the original extracted Toxic, Poison and Strong Poison,
//    a raw poison gland or root from butchering (MakeGland), or a brew with Venom Draught, venom,
//    Plague or Sleeping Draught in it - can slip it into the food of a realm it is at war with
//    (War.dm). The pot's poison is stirred through the stew: every bowl carries a share, food added
//    later too, until the pot is emptied. A stall's is laced into the food lying on it, not into
//    what is put out later. Villagers nearby may see it done; sneaking skill helps.
//  - In the body poison works like tgstation's metabolism: it sets in after 15 seconds, then a
//    quarter of what is left acts every few seconds with the original poison effects (blood lost
//    and BloodLoss(), health; ImmunePoison halves it) until it is spent. Enough of it kills.
//  - Noticing it: an eater may taste it and spit the food out (strong doses taste bitter, a skilled
//    poisoner hides it, cooks taste it sooner); a villager who falls sick names where they ate;
//    anyone beside the food can Inspect it (cooking and poison skill); cooks inspect what they
//    fill. Food someone fell sick from or tasted wrong is avoided until it is checked.
//  - Dealing with it: empty the pot or clear the stall (cooks throw out food found or suspected
//    poisoned); drink an Antidote (bone dust and water heated to 100 degrees, Brewing.dm) or an
//    Elixir of Life; the original Potion of Poison Immunity halves poison.

#define RM_POT_MAX 20
#define RM_FOODSTALL_MAX 30
#define RM_POT_HEAT 120
#define RM_POT_HOT 60              // a pot this hot serves Hot stew
#define RM_POT_STEW 80             // and stews raw food
#define RM_POT_FUEL_TIME 600       // ticks one piece of wood burns, as the Cauldron's
#define RM_POT_STEW_TIME 200       // ticks to stew one raw serving
#define RM_POISON_ONSET 150        // ticks before a poison sets in
#define RM_POISON_HURT 6           // health and blood lost per unit of poison
#define RM_FOOD_REACH 60           // tiles a hungry villager walks for a meal (as to the stockpile)
#define RM_SERVE_REACH 40          // tiles workers carry food to a pot or stall

var/list/rm_food_places = list()

obj/Items/var
	rm_poison = 0                  // poison in this food (saved with it)
	rm_poison_kind
	rm_poison_taste = 1            // how easily it is tasted: the poison and the poisoner's skill
	rm_poisoner                    // key of the player whose unit poisoned it
obj/Items/var/tmp/atom/rm_served_from   // the pot or stall this serving came from

mob/Monsters/var
	rm_poison = 0                  // poison in the body (saved: logging out doesn't cure it)
	rm_poison_kind
	rm_poison_by
	rm_poison_from = ""            // where it was eaten, for the sick message
mob/Monsters/var/tmp
	rm_poison_at = 0               // when it sets in
	rm_poison_sick = 0
	atom/rm_poison_source
	rm_spat_at = -1

Player/var/tmp/list/remaster_food_alert    // list(text, x, y, z, time)

// --- The pot and the stall ---------------------------------------------------------------
mob/WorkShops/RemasterFood
	density = 1
	var/rm_food = ""               // saved: one serving per entry, "type|name|state|power|race|poison"
	var/rm_poison = 0              // the pot's poison, stirred through the stew
	var/rm_poison_kind
	var/rm_poison_taste = 1
	var/rm_poisoner
	var/rm_suspect = 0             // 1 someone fell sick or tasted it, 2 seen poisoned or found poisoned
	var/rm_suspect_why = ""
	var/tmp/list/rm_items

	New()
		..()
		rm_food_places += src

	Del()
		rm_food_places -= src
		return ..()

	DblClick()
		// The HUD's food box is its menu, as the Cauldron's; the original menus never open for it.
		if(istype(usr, /Player)) usr:RemasterNotice("Select a unit beside the [name]: its box shows the food in it and what can be done.")

	Pot
		name = "Food pot"
		icon = 'Icons/Remastered/Cauldron.dmi'
		icon_state = "cold"
		var/fuel = 0               // ticks of burning left
		var/lit = 0
		var/heat = 20
		var/stew_clock = 0

		New()
			..()
			spawn(10) RemasterPotLoop()

	Stall
		name = "Food stall"
		icon = 'Cave.dmi'
		icon_state = "Table"

mob/WorkShops/RemasterFood/proc/Capacity()
	return istype(src, /mob/WorkShops/RemasterFood/Pot) ? RM_POT_MAX : RM_FOODSTALL_MAX

// Any food: the pot stews what is raw.
mob/WorkShops/RemasterFood/proc/Takes(obj/Items/Food/F)
	return istype(F)

mob/WorkShops/RemasterFood/proc/Items()
	if(!rm_items)
		rm_items = list()
		for(var/e in splittext(rm_food || "", ";")) if(length(e))
			var/list/p = splittext(e, "|")
			if(length(p) < 6) continue
			var/path = text2path(p[1])
			if(!ispath(path, /obj/Items/Food)) continue
			rm_items += list(list(path, p[2], p[3], text2num(p[4]) || 0, p[5], text2num(p[6]) || 0, length(p) >= 7 ? text2num(p[7]) || 0 : 0))
	return rm_items

// The saved copy, after every change.
mob/WorkShops/RemasterFood/proc/Store()
	var/list/out = list()
	for(var/list/E in Items()) out += "[E[1]]|[RmFoodText(E[2])]|[E[3]]|[E[4]]|[RmFoodText(E[5])]|[round(E[6], 0.01)]|[E[7] ? 1 : 0]"
	rm_food = jointext(out, ";")

proc/RmFoodText(t)
	return replacetext(replacetext("[t]", "|", "/"), ";", ",")

mob/WorkShops/RemasterFood/proc/Poisoned()
	if(rm_poison > 0.05) return 1
	for(var/list/E in Items()) if(E[6] > 0.05) return 1
	return 0

mob/WorkShops/RemasterFood/proc/Suspect(level, why)
	if(level < rm_suspect) return
	rm_suspect = level
	rm_suspect_why = why

// Put a piece of food in; it leaves the world as an entry and comes back when served.
mob/WorkShops/RemasterFood/proc/Put(obj/Items/Food/F)
	if(!istype(F) || !Takes(F) || length(Items()) >= Capacity()) return 0
	var/list/E = list(F.type, "[F.name]", "[F.icon_state]", F.FoodPower, F.Race ? "[F.Race]" : "", 0, F.rm_rotten ? 1 : 0)
	if(F.rm_poison > 0)
		if(istype(src, /mob/WorkShops/RemasterFood/Pot)) rm_poison += F.rm_poison   // stirred in
		else E[6] = F.rm_poison
		rm_poison_kind = F.rm_poison_kind
		rm_poison_taste = F.rm_poison_taste
		rm_poisoner = F.rm_poisoner
	rm_items += list(E)
	Store()
	if(ismob(F.loc))
		var/mob/H = F.loc
		H.DropItem(F)
	del F
	return 1

// Which serving suits M best: cooked meat and stew first, then fruit; raw meat and fungus only
// for those the original EatItem() finds them healthy for. 0 when there is nothing for M.
mob/WorkShops/RemasterFood/proc/Pick(mob/Monsters/M)
	var/best = 0
	var/rank = 0
	var/list/L = Items()
	for(var/i = 1, i <= length(L), i++)
		var/list/E = L[i]
		var/s = E[3]
		var/r = (s in list("CookedMeat", "Stew")) ? 4 : (s in list("Tomato", "Grape")) ? 3 : 1
		if(s == "RawMeat") r = M.Carn ? 2 : 0
		if(s == "Fungus") r = (M.Carn || M.Race == "Dwarf") ? 1 : 0
		if(E[7]) r = M.Hunger <= 5 ? min(r, 0.5) : 0      // rotten: only when starving (Ailments.dm)
		if(r > rank)
			best = i
			rank = r
	return best

// Serving i as a real food item in where (a unit's bag): the pot's share of poison goes with it.
mob/WorkShops/RemasterFood/proc/Take(i, atom/where)
	var/list/L = Items()
	if(i < 1 || i > length(L)) return null
	var/list/E = L[i]
	var/path = E[1]
	var/obj/Items/Food/F = new path(where)
	F.name = E[2]
	F.icon_state = E[3]
	F.FoodPower = E[4]
	if(E[5]) F.Race = E[5]
	F.rm_poison = E[6]
	F.rm_rotten = E[7]
	if(istype(src, /mob/WorkShops/RemasterFood/Pot))
		var/mob/WorkShops/RemasterFood/Pot/P = src
		F.name = "[P.heat >= RM_POT_HOT ? "Hot stew" : "Bowl of stew"] ([E[2]])"
		if(P.heat >= RM_POT_HOT) F.FoodPower = round(F.FoodPower * 1.25)
		if(rm_poison > 0)
			var/share = rm_poison / length(L)
			rm_poison -= share
			F.rm_poison += share
			if(rm_poison < 0.05) rm_poison = 0
	if(F.rm_poison > 0)
		F.rm_poison_kind = rm_poison_kind
		F.rm_poison_taste = rm_poison_taste
		F.rm_poisoner = rm_poisoner
	F.rm_served_from = src
	L.Cut(i, i + 1)
	Store()
	if(ismob(where))
		var/mob/H = where
		F.suffix = "(Carrying)"
		H.weight += F.weight
	return F

// M eats one serving here with the original EatItem(). 1 ate, 2 spat it out, 0 nothing for M.
mob/WorkShops/RemasterFood/proc/Serve(mob/Monsters/M)
	var/i = Pick(M)
	if(!i) return 0
	var/obj/Items/Food/F = Take(i, M)
	if(!F) return 0
	M.EatItem(F)
	if(M.rm_spat_at == world.time) return 2
	if(F)                                      // not eaten after all: never left in the bag
		if(F.loc == M) M.DropItem(F)
		del F
		return 0
	// A stall: a piece taken along for later (the original Hunger loop eats carried food first).
	if(istype(src, /mob/WorkShops/RemasterFood/Stall) && length(Items()) > 3 && M.weight + 10 <= M.weightmax)
		var/has = 0
		for(var/obj/Items/Food/X in M) has = 1
		var/j = Pick(M)
		if(!has && j)
			var/list/E = rm_items[j]
			if(E[3] != "RawMeat") Take(j, M)
	return 1

mob/WorkShops/RemasterFood/proc/Empty()
	var/n = length(Items())
	rm_items = list()
	Store()
	rm_poison = 0
	rm_poison_kind = null
	rm_poison_taste = 1
	rm_poisoner = null
	rm_suspect = 0
	rm_suspect_why = ""
	rm_germs = 0
	rm_clue = ""
	return n

// The pot's fire, as the Cauldron's: wood burns a minute a piece, the stew warms toward 120
// degrees and cools when the fire is out. Hot enough, it stews one raw serving at a time.
mob/WorkShops/RemasterFood/Pot/proc/RemasterPotLoop()
	while(src && loc)
		sleep(10)
		if(lit && fuel > 0)
			fuel -= 10
			heat = min(RM_POT_HEAT, heat + max(3, (RM_POT_HEAT - heat) * 0.08))
			if(fuel <= 0)
				lit = 0
				fuel = 0
		else
			lit = 0
			heat = max(20, heat - max(1, (heat - 20) * 0.03))
		if(heat >= RM_POT_STEW)
			stew_clock += 10
			if(stew_clock >= RM_POT_STEW_TIME)
				stew_clock = 0
				StewOne()
		if(heat >= RM_POT_HOT) rm_germs = 0        // a fever's germs die in a hot pot (Ailments.dm)
		var/want = lit ? "lit" : "cold"
		if(icon_state != want) icon_state = want

// One raw serving stewed: meat cooked (as the original Cook option leaves it), fungus made a stew
// anyone can eat (all: every raw serving). 0 when nothing was raw.
mob/WorkShops/RemasterFood/Pot/proc/StewOne(all = 0)
	. = 0
	for(var/list/E in Items()) if(E[3] == "RawMeat" || E[3] == "Fungus" || E[7])
		if(E[7])                                   // boiled clean (Ailments.dm)
			E[7] = 0
			E[2] = replacetext(E[2], "Rotten ", "")
		if(E[3] == "RawMeat" || E[3] == "Fungus")
			E[2] = E[3] == "Fungus" ? "Fungus stew" : "Stewed [replacetext(E[2], "Raw ", "")]"
			E[3] = E[3] == "Fungus" ? "Stew" : "CookedMeat"
		. = 1
		if(!all) break
	if(.) Store()

// --- Finding them ---------------------------------------------------------------------------
proc/RemasterFoodBeside(mob/M)
	for(var/mob/WorkShops/RemasterFood/C in range(1, M)) return C
	return null

// Where a hungry villager eats: the nearest own pot or stall with food for them that nobody fell
// sick from or tasted wrong.
Player/proc/RemasterFoodPlace(mob/Monsters/M)
	var/mob/WorkShops/RemasterFood/best
	var/best_d = RM_FOOD_REACH + 1
	for(var/mob/WorkShops/RemasterFood/C in rm_food_places)
		if(C.Owner != src || C.z != M.z || C.rm_suspect || !C.Pick(M)) continue
		var/d = get_dist(C, M)
		if(d < best_d)
			best = C
			best_d = d
	return best

// Where a worker takes food: the nearest own pot or stall with room that takes some of it. Only a
// cook goes to one under suspicion (to check it or throw the food out).
Player/proc/RemasterServePlace(mob/Monsters/M, list/items)
	var/mob/WorkShops/RemasterFood/best
	var/best_d = RM_SERVE_REACH + 1
	for(var/mob/WorkShops/RemasterFood/C in rm_food_places)
		if(C.Owner != src || C.z != M.z || length(C.Items()) >= C.Capacity()) continue
		if(C.rm_suspect && M.remaster_job != "cook") continue
		var/takes = 0
		for(var/obj/Items/Food/F in items) if(C.Takes(F)) takes = 1
		if(!takes) continue
		var/d = get_dist(C, M)
		if(d < best_d)
			best = C
			best_d = d
	return best

// Servings in all of the player's pots and stalls (the village food stock, Board.dm).
Player/proc/RemasterServedCount()
	. = 0
	for(var/mob/WorkShops/RemasterFood/C in rm_food_places) if(C.Owner == src) . += length(C.Items())

// --- Workers ---------------------------------------------------------------------------------
// Food carried by a farmer or cook goes to a pot or stall when there is one, else to the stockpile.
mob/Monsters/proc/RemasterServeOrStore(Player/P, list/items, label)
	var/mob/WorkShops/RemasterFood/C = P.RemasterServePlace(src, items)
	if(!C) return RemasterStoreFood(P, items, label)
	if(!RemasterWorkToward(C, lowertext(C.name))) return 1
	if(remaster_job == "cook" && !RemasterCookChecks(P, C)) return 1
	var/n = 0
	for(var/obj/Items/Food/F in items) if(F.loc == src && C.Put(F)) n++
	if(!n) return RemasterStoreFood(P, items, label)
	remaster_work_status = "Put [n] [label] in the [lowertext(C.name)] ([length(C.Items())]/[C.Capacity()])"
	return 1

// A cook at a pot or stall checks it first: what was seen or found poisoned is thrown out, food
// under suspicion is inspected (and thrown out unless it is found clean), and now and then the
// cook notices poison nobody suspected. 0 when the food was thrown out.
mob/Monsters/proc/RemasterCookChecks(Player/P, mob/WorkShops/RemasterFood/C)
	var/result
	if(C.rm_suspect == 2) result = "poisoned"
	else if(C.rm_suspect == 1 || (C.Poisoned() && prob(50))) result = RemasterInspectFood(C)
	if(result == "clean" || (!result) || (result == "unsure" && !C.rm_suspect)) return 1
	var/n = C.Empty()
	var/what = result == "poisoned" ? "poisoned" : "suspect"
	P.RemasterFoodAlarm(C, "[RemasterBareName()] threw out the [what] food in the [lowertext(C.name)] at [C.x], [C.y] ([n] serving\s).")
	RemasterEvent("Threw out [what] food")
	remaster_work_status = "Threw out the [what] food in the [lowertext(C.name)]"
	return 0

// The cook's own pot: the nearest own Food pot within 15 tiles of the stockpile (or the cook) with
// room, which stews raw meat without burning it.
Player/proc/RemasterCookPot(mob/Monsters/M, turf/ST)
	var/atom/C = (ST && ST.z == M.z) ? ST : M
	var/mob/WorkShops/RemasterFood/Pot/best
	var/best_d = 1#INF
	for(var/mob/WorkShops/RemasterFood/Pot/X in rm_food_places)
		if(X.Owner != src || X.z != M.z || get_dist(X, C) > 15 || length(X.Items()) >= X.Capacity()) continue
		var/d = get_dist(X, M)
		if(d < best_d)
			best = X
			best_d = d
	return best

// The pot's fire can be kept: it burns, the cook carries wood, or the stores have some. Without,
// the cook cooks at a campfire or kitchen as before.
mob/Monsters/proc/RemasterPotFire(Player/P, mob/WorkShops/RemasterFood/Pot/pot)
	if(pot.fuel > 0) return 1
	for(var/obj/Items/woods/wood/W in src) if(W.suffix == "(Carrying)") return 1
	var/turf/WS = P.RemasterStoreWith(/obj/Items/woods/wood, src)
	return WS && WS.z == z

// A cook carrying raw meat with a Food pot near: into the stew it goes, and the fire is fed.
mob/Monsters/proc/RemasterCookAtPot(Player/P, mob/WorkShops/RemasterFood/Pot/pot, list/raw)
	if(!RemasterWorkToward(pot, "food pot")) return
	if(!RemasterCookChecks(P, pot)) return
	var/fed = 0
	if(pot.fuel < RM_POT_FUEL_TIME * 2) for(var/obj/Items/woods/wood/W in src) if(W.suffix == "(Carrying)")
		DropItem(W)
		del W
		pot.fuel += RM_POT_FUEL_TIME
		fed = 1
		break
	if(pot.fuel > 0) pot.lit = 1
	var/n = 0
	for(var/obj/Items/Food/F in raw) if(F.loc == src && pot.Put(F)) n++
	CookingSkill += n ? 0.5 : 0
	remaster_work_status = n ? "Put [n] raw meat in the stew[fed ? " and fed the fire" : ""]" : "The food pot is full"
	if(!pot.lit) remaster_work_status += " (the pot needs wood to cook: put wood on the stockpile)"

// With the raw meat from the stockpile, a piece of wood lying there for the cook's pot fire.
mob/Monsters/proc/RemasterCookTakeWood(Player/P, turf/ST)
	var/mob/WorkShops/RemasterFood/Pot/pot = P.RemasterCookPot(src, ST)
	if(!pot || pot.fuel >= RM_POT_FUEL_TIME * 2) return 0
	for(var/obj/Items/woods/wood/W in src) if(W.suffix == "(Carrying)") return 0
	for(var/obj/Items/woods/wood/W in range(1, src)) if(isturf(W.loc) && P.RemasterMayCollect(W)) return PickUpItem(W) ? 1 : 0
	return 0

// Idle cooks keep the pots and stalls stocked from the stockpile: cooked meat, fruit and cheese
// (raw meat waits there for cooking), and a piece of wood for a pot fire that is low.
mob/Monsters/proc/RemasterRestockFood(Player/P)
	var/mob/WorkShops/RemasterFood/C
	var/best_d = RM_SERVE_REACH + 1
	for(var/mob/WorkShops/RemasterFood/X in rm_food_places)
		if(X.Owner != P || X.z != z || X.rm_suspect || length(X.Items()) * 2 >= X.Capacity()) continue
		var/d = get_dist(X, src)
		if(d < best_d)
			C = X
			best_d = d
	if(C)
		var/turf/S = P.RemasterStoreWith(/obj/Items/Food, src)
		var/obj/Items/Food/pick
		if(S && S.z == z) for(var/obj/Items/Food/F in range(1, S)) if(isturf(F.loc) && P.RemasterMayCollect(F) && C.Takes(F) && F.icon_state != "RawMeat")
			pick = F
			break
		if(pick)
			if(!RemasterWorkToward(pick, "food for the [lowertext(C.name)]")) return 1
			var/n = 0
			for(var/obj/Items/Food/F in range(1, src)) if(isturf(F.loc) && P.RemasterMayCollect(F) && C.Takes(F) && F.icon_state != "RawMeat" && n < REMASTER_FOOD_CARRY)
				if(PickUpItem(F)) n++
			remaster_work_status = n ? "Took [n] food for the [lowertext(C.name)]" : "Can't carry more"
			return n > 0
	// A pot whose fire is about to go out, with stew in it: a piece of wood for it.
	for(var/mob/WorkShops/RemasterFood/Pot/pot in rm_food_places)
		if(pot.Owner != P || pot.z != z || pot.fuel >= RM_POT_FUEL_TIME / 2 || !length(pot.Items()) || get_dist(pot, src) > RM_SERVE_REACH) continue
		var/has = 0
		for(var/obj/Items/woods/wood/W in src) if(W.suffix == "(Carrying)") has = 1
		if(has)
			RemasterCookAtPot(P, pot, list())
			return 1
		var/turf/WS = P.RemasterStoreWith(/obj/Items/woods/wood, src)
		if(!WS || WS.z != z) return 0
		for(var/obj/Items/woods/wood/W in range(1, WS)) if(isturf(W.loc) && P.RemasterMayCollect(W))
			if(!RemasterWorkToward(W, "wood for the pot fire")) return 1
			if(PickUpItem(W)) remaster_work_status = "Took wood for the pot fire"
			return 1
	return 0

// The catch-up's cook (Away.dm): food from the stores into the pots and stalls with room (raw meat
// only into a pot, which stews it over the hours), at most REMASTER_AWAY_JOBS pieces.
mob/Monsters/proc/RemasterAwayRestock(Player/P)
	var/n = 0
	for(var/mob/WorkShops/RemasterFood/C in rm_food_places)
		if(C.Owner != P || C.z != z || C.rm_suspect) continue
		var/pot = istype(C, /mob/WorkShops/RemasterFood/Pot)
		for(var/turf/S in P.RemasterStores()) if(S.z == z)
			for(var/obj/Items/Food/F in range(1, S))
				if(n >= REMASTER_AWAY_JOBS || length(C.Items()) >= C.Capacity()) break
				if(!isturf(F.loc) || !P.RemasterMayCollect(F) || (F.icon_state == "RawMeat" && !pot)) continue
				if(C.Put(F)) n++
		if(pot) C:StewOne(1)
	P.RemasterAwayAdd("restocked", n)

// --- Eating ----------------------------------------------------------------------------------
// Care's eat step at a pot or stall (Care.dm).
mob/Monsters/proc/RemasterCareEatServed(Player/P)
	var/mob/WorkShops/RemasterFood/C = remaster_care_target
	if(!istype(C) || !C.z || C.z != z) return RemasterCareDone("The food is gone")
	if(C.rm_suspect) return RemasterCareDone("Won't eat from the [lowertext(C.name)]: [C.rm_suspect_why]")
	if(!C.Pick(src)) return RemasterCareDone("The [lowertext(C.name)] ran out of food")
	if(get_dist(src, C) <= 2)
		if(destination == remaster_care_dest) destination = null
		var/where = lowertext(C.name)
		switch(C.Serve(src))
			if(2) return RemasterCareDone("Spat out the food at the [where]: it tasted bitter")
			if(0) return RemasterCareDone("Couldn't eat at the [where]")
		if(Hunger > REMASTER_CARE_HUNGRY) return RemasterCareDone("Ate at the [where]")
		return
	var/turf/T = RemasterTileNear(C, src)
	if(T && destination != T)
		destination = T
		remaster_care_dest = T

// The offline catch-up's meal (Away.dm): one serving from the nearest pot or stall, its food value
// as EatItem() gives it (without the announcement and the seeds) and its poison, which runs its
// course at once. 1 when eaten.
mob/Monsters/proc/RemasterAwayMeal(Player/P)
	var/mob/WorkShops/RemasterFood/C = P.RemasterFoodPlace(src)
	if(!C) return 0
	var/obj/Items/Food/F = C.Take(C.Pick(src), src)
	if(!F) return 0
	P.RemasterAwayAdd("served")
	if(F.rm_poison > 0 && RemasterPoisonable() && prob(RemasterTasteChance(F)))
		C.Suspect(1, "[RemasterBareName()] tasted something bitter in it")
		P.RemasterAwayAdd("spat")
		RemasterTakePoison(F.rm_poison * 0.2, F.rm_poison_kind, F.rm_poisoner, C)
	else
		var/healthy = !((F.icon_state == "RawMeat" && !Carn) || (F.icon_state == "Fungus" && !Carn && Race != "Dwarf"))
		Hunger = min(MaxHunger, Hunger + (healthy ? F.FoodPower : F.FoodPower / 2))
		if(F.rm_poison > 0 && RemasterTakePoison(F.rm_poison, F.rm_poison_kind, F.rm_poisoner, C)) P.RemasterAwayAdd("poisoned")
	DropItem(F)
	del F
	if(rm_poison > 0) RemasterPoisonResolve(P)
	return 1

// --- Poison ----------------------------------------------------------------------------------
// What a carried item puts into food: list(dose, kind, taste) or null.
proc/RemasterPoisonDose(obj/Items/I)
	if(!I) return null
	if(istype(I, /obj/Items/Poisons/Toxic)) return list(clamp(I.PoisonContent, 10, 45), "Toxic", 0.6)
	if(istype(I, /obj/Items/Poisons/StrongPoison)) return list(clamp(I.PoisonContent, 15, 65), "Strong poison", 0.8)
	if(istype(I, /obj/Items/Poisons/Poison)) return list(clamp(I.PoisonContent, 8, 40), "Poison", 1)
	if(istype(I, /obj/Items/Glands)) return list(15, istype(I, /obj/Items/Glands/PoisonRoots) ? "Crushed poison root" : "Crushed poison gland", 1.6)
	if(istype(I, /obj/Items/Potions/RemasterBrew))
		var/list/B = I:brew
		var/draught = B["poison"] || 0
		var/venom = B["venom"] || 0
		var/plague = B["plague"] || 0
		var/dose = draught + venom * 0.5 + plague * 1.2
		if(dose >= 1)
			var/kind = plague > draught && plague > venom ? "Plague" : (draught >= venom ? "Venom Draught" : "Venom")
			return list(round(dose, 0.1), kind, kind == "Venom" ? 1.2 : (kind == "Plague" ? 0.9 : 0.5))
		if((B["sleepdraught"] || 0) >= 1) return list(round(B["sleepdraught"], 0.1), "Sleeping Draught", 0.7)
	return null

proc/RemasterMayPoison(Player/P, mob/WorkShops/RemasterFood/C)
	if(!C.Owner) return 1
	return istype(C.Owner, /Player) && C.Owner != P && RemasterAtWar(P, C.Owner)

// M secretly puts the poison item I into C's food.
Player/proc/RemasterFoodPoison(mob/Monsters/M, mob/WorkShops/RemasterFood/C, obj/Items/I)
	var/list/D = RemasterPoisonDose(I)
	if(!D || I.loc != M) return 0
	if(!RemasterMayPoison(src, C))
		RemasterNotice(C.Owner == src ? "That is your own food." : "Only the food of a realm you are at war with can be poisoned.")
		return 0
	var/list/L = C.Items()
	var/pot = istype(C, /mob/WorkShops/RemasterFood/Pot)
	if(!pot && !length(L))
		RemasterNotice("There is no food on the stall to poison.")
		return 0
	var/dose = D[1]
	if(istype(I, /obj/Items/Potions/RemasterBrew))
		I:brew = list()
		RemasterBrewLook(I)
	else
		M.DropItem(I)
		del I
	if(pot) C.rm_poison += dose
	else for(var/list/E in L) E[6] += dose / length(L)
	C.Store()
	C.rm_poison_kind = D[2]
	C.rm_poison_taste = D[3] * max(0.3, 1 - M.PoisonSkill / 100)
	C.rm_poisoner = key
	C.RemasterLeaveClue(M, D[2], src)   // footprints and a clue (Forensics.dm)
	M.PoisonSkill += 1
	var/where = "[C.Owner ? "[C.Owner]'s " : ""][lowertext(C.name)] at [C.x], [C.y]"
	M.RemasterEvent("Slipped [D[2]] into the [where]")
	// Seen doing it? Each villager of the owner awake within 6 tiles might be.
	var/Player/O = C.Owner
	var/mob/Monsters/seen_by
	if(istype(O)) for(var/mob/Monsters/W in view(6, C))
		if(W.Owner != O || W.HP <= 0 || W.Sleeping || W.Fainted) continue
		if(prob(max(10, 50 - M.SneakingSkill)))
			seen_by = W
			break
	if(seen_by)
		C.Suspect(2, "[seen_by.RemasterBareName()] saw [M.RemasterBareName()] put something in it")
		O.RemasterFoodAlarm(C, "[seen_by.RemasterBareName()] saw [M.RemasterBareName()] of [RemasterHouse()] slip something into the [lowertext(C.name)] at [C.x], [C.y]! Throw that food out.")
		RemasterNotice("[M.RemasterBareName()] slipped the [D[2]] into the [where] - but [seen_by.RemasterBareName()] saw it done!")
		RemasterLog("[M.RemasterBareName()] was seen poisoning the [where]", "problem", C)
	else
		M.SneakingSkill += 0.5
		RemasterNotice("[M.RemasterBareName()] slipped the [D[2]] ([round(dose)]) into the [where] unseen.")
		RemasterLog("[M.RemasterBareName()] poisoned the [where] unseen", "fight", C)
	return 1

mob/Monsters/proc/RemasterPoisonable()
	return HP > 0 && !Undead && !(Race in list("Gargoyle", "Skeleton", "SandKing", "Zombie", "Devourer"))

// The tgstation taste test: strong doses taste, a skilled poisoner's hide, cooks know food.
mob/Monsters/proc/RemasterTasteChance(obj/Items/I)
	return clamp(I.rm_poison * (isnull(I.rm_poison_taste) ? 1 : I.rm_poison_taste) * 2.5 + CookingSkill / 5, 0, 90)

// From the original EatItem() (Food.dm), before the meal: tasted, it is spat out and thrown away
// (a little poison still gets down). 1 when spat out.
mob/Monsters/proc/RemasterTastePoison(obj/Items/ITEM)
	if(!RemasterPoisonable() || !prob(RemasterTasteChance(ITEM))) return 0
	rm_spat_at = world.time
	view(src) << "[src] spits out the [ITEM]: it tastes bitter!"
	var/atom/from = ITEM.rm_served_from
	RemasterTakePoison(ITEM.rm_poison * 0.2, ITEM.rm_poison_kind, ITEM.rm_poisoner, from || "the [ITEM.name]")
	if(istype(from, /mob/WorkShops/RemasterFood)) from:Suspect(1, "[RemasterBareName()] tasted something bitter in it")
	RemasterEvent("Spat out bitter food")
	var/Player/P = Owner
	if(istype(P)) P.RemasterFoodAlarm(from || src, "[RemasterBareName()] spat out [istype(from, /mob/WorkShops/RemasterFood) ? "food from the [lowertext(from.name)] at [from.x], [from.y]" : "the [ITEM.name]"]: it tasted bitter. It may be poisoned.")
	if(DropItem(ITEM)) del ITEM
	return 1

// From the original EatItem(), after the meal: the poison that went down with it.
mob/Monsters/proc/RemasterAtePoison(obj/Items/ITEM)
	RemasterTakePoison(ITEM.rm_poison, ITEM.rm_poison_kind, ITEM.rm_poisoner, ITEM.rm_served_from || "the [ITEM.name]")

mob/Monsters/proc/RemasterTakePoison(dose, kind, by, from)
	if(dose <= 0 || !RemasterPoisonable() || GoingToDie) return 0
	var/atom/A = istype(from, /atom) ? from : null
	var/where = A ? "the [lowertext(A.name)] at [A.x], [A.y]" : "[from]"
	if(kind == "Sleeping Draught")
		// A spiked meal: the Sleeping Draught's own effect (Brewing.dm).
		if(!Sleeping) Sleep(100 + round(dose * 20))
		if(istype(A, /mob/WorkShops/RemasterFood)) A:Suspect(1, "[RemasterBareName()] fell asleep after eating from it")
		var/Player/P = Owner
		if(istype(P)) P.RemasterFoodAlarm(A || src, "[RemasterBareName()] fell into a deep sleep after eating [where]. The food may be drugged.")
		return 1
	if(kind == "Plague") RemasterCatchFever("plague in the food")   // Ailments.dm
	if(rm_poison <= 0)
		rm_poison_at = world.time + RM_POISON_ONSET
		rm_poison_sick = 0
	rm_poison += dose
	rm_poison_kind = kind || "Poison"
	rm_poison_by = by
	rm_poison_source = A
	rm_poison_from = where
	return 1

// Every care step (Care.dm), and at once while catching up: the poison takes its course with the
// original effects - blood lost (BloodLoss() and the bleeding it starts) and health.
mob/Monsters/proc/RemasterPoisonTick(Player/P, instant = 0)
	if(rm_poison <= 0) return 0
	if(HP <= 0 || GoingToDie)
		rm_poison = 0
		return 0
	if(!instant && world.time < rm_poison_at) return 0
	var/onset = !rm_poison_sick
	if(!rm_poison_sick)
		rm_poison_sick = 1
		if(!instant)
			view(src) << "<font color=#9be05a>[src] doubles over, pale and sweating.</font>"
			RemasterSay("I don't feel so good...", 1)
		RemasterEvent("Fell sick: [rm_poison_kind][rm_poison_from ? " from [rm_poison_from]" : ""]")
		var/atom/S = rm_poison_source
		if(istype(S, /mob/WorkShops/RemasterFood)) S:Suspect(1, "[RemasterBareName()] fell sick after eating from it")
		if(istype(P)) P.RemasterFoodAlarm(S || src, "[RemasterBareName()] is sick: poisoned[rm_poison_from ? " by food from [rm_poison_from]" : ""]. An Antidote cures it; check that food.")
	if(!instant && RemasterAntidoteNow(P) && rm_poison <= 0)
		rm_poison_sick = 0
		return 1
	if(!instant && (onset || prob(30))) RemasterVomit()
	var/take = min(rm_poison, max(1, rm_poison * 0.25))
	rm_poison -= take
	var/hurt = take * RM_POISON_HURT * (ImmunePoison ? 0.5 : 1)
	BloodContent -= hurt
	BloodLoss()
	HP -= hurt
	if(HP <= 0)
		var/by = rm_poison_by
		var/where = rm_poison_from
		rm_poison = 0
		GoingToDie = 1
		Killer = by ? "[by]'s poison" : "Poison"
		DeathType = "Poison"
		if(istype(P))
			P.RemasterLog("[RemasterBareName()] died of poison[where ? " from [where]" : ""]", "death", src)
			if(instant) P.RemasterAwayAdd("poison_deaths")
			if(by && RemasterAtWarKeys(P.key, by)) RemasterWarScore(by, P.key, 1)
		Death()
		return 1
	if(rm_poison < 0.05)
		rm_poison = 0
		rm_poison_sick = 0
		RemasterEvent("Got over the poison")
		if(istype(P) && !instant) P.RemasterLog("[RemasterBareName()] got over the poison", "good", src)
	return 1

// Green vomit, as in SS13: a puddle of bile beside the poisoned villager for two minutes; some of
// the poison comes up with it, and a little of the last meal.
obj/RemasterVomit
	name = "Vomit"
	icon = 'Blood.dmi'
	icon_state = "1"
	color = "#8fd14f"
	mouse_opacity = 0
	var/made = 0

	New()
		..()
		made = world.time
		spawn(1200) if(src) del src

mob/Monsters/proc/RemasterVomit()
	if(!isturf(loc)) return 0
	var/obj/RemasterVomit/V = new(loc)   // at their feet, toward where they face (3D draws it so)
	V.dir = dir
	view(src) << "<font color=#8fd14f>[src] throws up green bile!</font>"
	RemasterSay("*hurk*", 1)
	rm_poison = max(0, rm_poison - max(1, rm_poison * 0.15))
	Hunger = max(0, Hunger - 10)
	RemasterEvent("Threw up green bile")
	return 1

// The catch-up: the whole poison at once; whoever lives through it has rested it off by the time
// the player is back.
mob/Monsters/proc/RemasterPoisonResolve(Player/P)
	var/n = 0
	while(rm_poison > 0 && HP > 0 && !GoingToDie && n++ < 100) RemasterPoisonTick(P, 1)
	if(HP > 0 && !GoingToDie)
		HP = MAXHP
		BloodContent = MaxBloodContent
		BleedType = null

// Drink an Antidote (or an Elixir of Life) from the bag or a friend's within 3 tiles, unless the
// player unticked it (Bag.dm).
mob/Monsters/proc/RemasterAntidoteNow(Player/P)
	if(!istype(P) || !rm_poison_sick || !RemasterAutoUseOn("antidote")) return 0
	var/obj/Items/Potions/RemasterBrew/B
	for(var/obj/Items/Potions/RemasterBrew/X in src) if((X.brew["antidote"] || 0) >= 1 || (X.brew["elixir"] || 0) >= 1) B = X
	if(!B && isturf(loc)) for(var/mob/Monsters/F in range(REMASTER_SHARE_RANGE, src))
		if(F == src || F.Owner != P || F.HP <= 0) continue
		for(var/obj/Items/Potions/RemasterBrew/X in F) if((X.brew["antidote"] || 0) >= 1 || (X.brew["elixir"] || 0) >= 1)
			if(RemasterHandOver(X, F, src)) B = X
			break
		if(B) break
	if(!B) return 0
	var/label = "[B.name]"
	P.RemasterDrinkBrew(src, B)
	P.RemasterLog("[RemasterBareName()] drank [label] against the poison", "good", src)
	return 1

// --- Inspecting ------------------------------------------------------------------------------
// "poisoned", "clean" or "unsure". Cooking and poison skill find it; a skilled poisoner's work is
// harder to find. For the owner's units the finding marks the food.
mob/Monsters/proc/RemasterInspectFood(mob/WorkShops/RemasterFood/C)
	var/poisoned = C.Poisoned()
	var/chance = 30 + CookingSkill * 2 + PoisonSkill * 3 + PotionSkill * 2
	if(poisoned) chance *= clamp(C.rm_poison_taste * 1.25, 0.5, 1.5)
	. = "unsure"
	if(prob(min(95, chance)))
		if(C.Owner != Owner) return poisoned ? "poisoned" : "clean"
		if(poisoned)
			C.Suspect(2, "[RemasterBareName()] found it poisoned ([C.rm_poison_kind || "poison"])")
			. = "poisoned"
		else
			C.rm_suspect = 0
			C.rm_suspect_why = ""
			. = "clean"
	if(C.Owner == Owner) RemasterReadClue(C)   // who did it (Forensics.dm): its alert is the last word

// --- Alerts ----------------------------------------------------------------------------------
Player/proc/RemasterFoodAlarm(atom/where, text, kind = "Food alert")
	var/turf/T = RemasterGetTurf(where)
	RemasterLog(text, "problem", T)
	RemasterNotice(text)
	src << "<b><font color=#a8e05a>[text]</font></b>"
	remaster_food_alert = list(text, T ? T.x : x, T ? T.y : y, T ? T.z : z, world.time, kind)

Player/proc/RemasterFoodAlertData()
	if(!remaster_food_alert || world.time - remaster_food_alert[5] > 1200) return null
	return list("text"=remaster_food_alert[1], "x"=remaster_food_alert[2], "y"=remaster_food_alert[3], "z"=remaster_food_alert[4], "kind"=remaster_food_alert[6])

// --- HUD -------------------------------------------------------------------------------------
// The box for the pot or stall beside a unit, like the Cauldron's.
Player/proc/RemasterFoodBoxData(mob/Monsters/M)
	var/mob/WorkShops/RemasterFood/C = RemasterFoodBeside(M)
	if(!C) return null
	var/own = C.Owner == src
	var/list/L = C.Items()
	var/list/counts = list()
	for(var/list/E in L) counts["[E[2]]"] = (counts["[E[2]]"] || 0) + 1
	var/list/contents = list()
	for(var/k in counts) contents += list(list("name"=k, "n"=counts[k]))
	var/war = !own && C.Owner && RemasterMayPoison(src, C)
	var/list/poisons = list()
	if(!own) for(var/obj/Items/I in M) if(I.suffix != "(Equipped)")
		var/list/dose = RemasterPoisonDose(I)
		if(dose) poisons += list(list("ref"=RemasterUIRef(I), "name"="[I.name]", "kind"=dose[2], "dose"=round(dose[1])))
	var/add = 0
	var/wood = 0
	if(own)
		for(var/obj/Items/Food/F in M) if(F.suffix == "(Carrying)" && C.Takes(F)) add++
		for(var/obj/Items/woods/wood/W in M) if(W.suffix == "(Carrying)") wood++
	var/list/D = list("kind"=(istype(C, /mob/WorkShops/RemasterFood/Pot) ? "pot" : "stall"), "name"="[C.name]", "own"=own, "owner"=(C.Owner ? "[C.Owner]" : null),
		"n"=length(L), "max"=C.Capacity(), "contents"=contents, "suspect"=(own ? C.rm_suspect : 0), "why"=(own ? C.rm_suspect_why : null),
		"add"=add, "wood"=wood, "eat"=(own && C.Pick(M) > 0 && M.Hunger < M.MaxHunger), "war"=war, "poisons"=poisons)
	if(istype(C, /mob/WorkShops/RemasterFood/Pot))
		var/mob/WorkShops/RemasterFood/Pot/P = C
		D["temp"] = round(P.heat)
		D["lit"] = P.lit
		D["fuel"] = round(P.fuel / 600, 0.1)
	return D

// value: "unitref|action|arg"; the pot or stall is the one beside the unit.
Player/proc/RemasterFoodCommand(value)
	var/list/p = splittext("[value]", "|")
	if(p.len < 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return 0
	var/mob/WorkShops/RemasterFood/C = RemasterFoodBeside(M)
	if(!C)
		RemasterNotice("[M.RemasterBareName()] must stand beside a food pot or stall.")
		return 0
	var/own = C.Owner == src
	var/what = lowertext(C.name)
	switch(p[2])
		if("inspect")
			switch(M.RemasterInspectFood(C))
				if("poisoned")
					// A clue found in the same look (Forensics.dm) already raised the alarm, with who did it.
					var/clued = remaster_food_alert && remaster_food_alert[6] == "Clue" && remaster_food_alert[5] == world.time
					if(own && !clued) RemasterFoodAlarm(C, "[M.RemasterBareName()] inspected the [what] at [C.x], [C.y]: the food is poisoned ([C.rm_poison_kind || "poison"])! Empty it.")
					else RemasterNotice("[M.RemasterBareName()] can tell this food is poisoned.")
				if("clean") RemasterNotice("[M.RemasterBareName()] inspected the [what]: the food smells and tastes fine.")
				else RemasterNotice("[M.RemasterBareName()] can't tell whether anything is wrong with the [what]. Cooking or poison skill would help.")
			return 1
		if("poison")
			var/obj/Items/I
			for(var/obj/Items/X in M) if(X.remaster_ui_id && X.remaster_ui_id == (p.len >= 3 ? p[3] : ""))
				I = X
				break
			return RemasterFoodPoison(M, C, I)
	if(!own)
		RemasterNotice("That [what] belongs to [C.Owner ? "[C.Owner]" : "nobody"].")
		return 0
	switch(p[2])
		if("add")
			var/n = 0
			for(var/obj/Items/Food/F in M) if(F.suffix == "(Carrying)" && C.Put(F)) n++
			RemasterNotice(n ? "[M.RemasterBareName()] put [n] food in the [what]." : "The [what] is full or takes none of that.")
			return n > 0
		if("eat")
			switch(C.Serve(M))
				if(1) RemasterNotice("[M.RemasterBareName()] ate at the [what].")
				if(2) RemasterNotice("[M.RemasterBareName()] spat the food out!")
				else RemasterNotice("Nothing in the [what] that [M.RemasterBareName()] can eat.")
			return 1
		if("empty")
			var/n = C.Empty()
			RemasterNotice("[M.RemasterBareName()] threw out the food in the [what] ([n] serving\s).")
			RemasterLog("Emptied the [what] at [C.x], [C.y] ([n] serving\s thrown out)", "work", C)
			return 1
	if(!istype(C, /mob/WorkShops/RemasterFood/Pot)) return 0
	var/mob/WorkShops/RemasterFood/Pot/pot = C
	switch(p[2])
		if("fuel")
			for(var/obj/Items/woods/wood/W in M) if(W.suffix == "(Carrying)")
				M.DropItem(W)
				del W
				pot.fuel += RM_POT_FUEL_TIME
				pot.lit = 1
				return 1
			RemasterNotice("[M.RemasterBareName()] has no wood to feed the fire.")
			return 0
		if("light")
			if(pot.fuel <= 0)
				RemasterNotice("Put wood under the pot first.")
				return 0
			pot.lit = !pot.lit
			return 1
	return 0

Player/proc/RemasterFoodAlertCommand(value)
	if(value == "go" && remaster_food_alert)
		var/turf/T = locate(remaster_food_alert[2], remaster_food_alert[3], remaster_food_alert[4])
		if(T) loc = T
	remaster_food_alert = null
	return 1

// What the 3D view draws: how full, what lies on the stall, the pot's fire, and for the owner
// whether the food is under suspicion.
proc/Remaster3DFood(mob/WorkShops/RemasterFood/C, Player/viewer)
	var/list/L = C.Items()
	var/list/states = list()
	for(var/i = 1, i <= min(length(L), 12), i++)
		var/list/E = L[i]
		states += E[3]
	var/list/D = list("kind"=(istype(C, /mob/WorkShops/RemasterFood/Pot) ? "pot" : "stall"), "n"=length(L), "max"=C.Capacity(), "items"=states,
		"warn"=(C.Owner == viewer ? C.rm_suspect : 0), "col"=(ismob(C.Owner) ? RemasterClaimColour(C.Owner:key) : "#c8a060"))
	if(istype(C, /mob/WorkShops/RemasterFood/Pot))
		var/mob/WorkShops/RemasterFood/Pot/P = C
		D["lit"] = P.lit
		D["temp"] = round(P.heat)
	return D
