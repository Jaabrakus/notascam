// While you were away (Remastered). A village only works while its player is connected
// (RemasterTrack runs for connected players), so when you come back after the game stopped
// running for you (the app was closed, or you logged out), it catches up on the work it would
// have done, and a "While you were away" card says what happened.
//  - Up to 8 hours count, at half the pace of live play (they eat, sleep and rest too), and
//    at most REMASTER_AWAY_JOBS pieces of work per villager.
//  - Woodcutters, miners, haulers, farmers, hunters, cooks, builders, carpenters (their queue)
//    and board workers on wood or stone orders do their jobs in their work areas with the game's
//    own procedures (each race's chop, dig and water code, Attack() and TearMeat for the hunt,
//    the harvest and cooking effects, the construction tasks' fetch and build steps, the
//    carpentry recipe), and the goods go to the stockpile.
//  - Everyone eats from the food pots and stalls, else the stockpile, as their hunger needs (the
//    original loses 1 every 40 s) and sleeps when tired, in a bed or rough. Health comes back only as it
//    does live: the meals eaten (+20), the sleep had, the Doctor's or the stall's remedies, potions it
//    uses by itself, a gargoyle's stone; a bleeding stump is treated or bleeds (FarRecords.dm
//    RmFarLiveThrough). Nobody starves while away: with no food left they come back hungry. Poisoned
//    food poisons them all the same (FoodSupply.dm).
//  - Miners leave rock beside water or lava (digging it floods the tunnel), and creatures the
//    digging turns up are driven off. Cave-ins can still happen (pillars hold tunnels), but
//    nobody is left inside the rock.
//  - Merchants and workshop orders wait for you.

#define REMASTER_AWAY_MIN 3000        // 5 minutes of real time, in tenths of a second
#define REMASTER_AWAY_MAX 288000      // 8 hours
#define REMASTER_AWAY_PACE 0.5
#define REMASTER_AWAY_JOBS 60         // trees, rock, loads, crafts or meat per villager
#define REMASTER_AWAY_PICKS 120       // fruit one farmer picks
#define REMASTER_AWAY_TRIP 20         // seconds to reach the next job and carry the goods home
#define REMASTER_AWAY_LIMIT 120       // stop after 12 s of real time spent catching up

Player/var/list/remaster_seen                  // RemasterNow() when the game last ran for this player (saved)
Player/var/tmp
	remaster_caught_up = 0
	remaster_catching_up = 0
	list/remaster_away_report                  // shown on the card until closed
	list/remaster_away_tally                   // what one catch-up did
	list/remaster_away_goods                   // goods made, by name
	remaster_away_started = 0

// The real time as list(day, time of day): days since 1 January 2000 and tenths of a second
// since midnight, UTC. This engine's world.realtime is broken (it gives only the milliseconds of
// the current second over 100), so the day comes from time2text, which counts small timestamps
// from today's UTC midnight, and the time of day from world.timeofday (UTC). Two numbers keep
// the precision a single count of tenths since 2000 would lose.
proc/RemasterNow()
	var/date = time2text(0, "YYYY-MM-DD", 0)
	var/t = world.timeofday
	var/again = time2text(0, "YYYY-MM-DD", 0)
	if(again != date)                          // midnight passed between the two reads
		date = again
		t = world.timeofday
	return list(RemasterDayNumber(date), t)

// Days since 1 January 2000 for "YYYY-MM-DD" (the civil-calendar day count).
proc/RemasterDayNumber(date)
	var/y = text2num(copytext(date, 1, 5))
	var/m = text2num(copytext(date, 6, 8))
	var/d = text2num(copytext(date, 9, 11))
	if(!y || !m || !d) return 0
	if(m <= 2) y--
	var/era = round(y / 400)
	var/yoe = y - era * 400
	var/doy = round((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1
	var/doe = yoe * 365 + round(yoe / 4) - round(yoe / 100) + doy
	return era * 146097 + doe - 730425

// Tenths of a second from then (a RemasterNow() list) until now; null without a time.
proc/RemasterSince(list/then)
	if(!islist(then) || length(then) != 2 || !then[1]) return null
	var/list/now = RemasterNow()
	return (now[1] - then[1]) * 864000 + (now[2] - then[2])

// First thing in RemasterTrack (QoL.dm). LoadUnits() reads remaster_seen back from the save,
// so the first check after loading sees how long the game wasn't running for this player.
Player/proc/RemasterAwayTick()
	if(!remaster_caught_up && Loaded && remaster_world_ready && length(UnitList))
		remaster_caught_up = 1
		var/gap = RemasterSince(remaster_seen)
		if(gap && gap >= REMASTER_AWAY_MIN)
			remaster_catching_up = 1
			spawn(10) RemasterCatchUp(gap)
	if(!remaster_catching_up) remaster_seen = RemasterNow()

Player/proc/RemasterAwayAdd(key, n = 1)
	if(!n) return
	if(!remaster_away_tally) remaster_away_tally = list()
	remaster_away_tally[key] = (remaster_away_tally[key] || 0) + n

Player/proc/RemasterAwayOver()
	var/t = world.timeofday - remaster_away_started
	if(t < 0) t += 864000
	return t > REMASTER_AWAY_LIMIT

// Onto the store that takes it (Blueprints.dm), counted as made while away when it is new.
Player/proc/RemasterAwayStore(obj/Items/I, made = 1)
	if(!I) return 0
	var/level = isturf(I.loc) ? I.z : (I.loc ? I.loc.z : 0)
	var/turf/S = RemasterStoreFor(I, level)
	if(!S) return 0
	if(ismob(I.loc))
		var/mob/H = I.loc
		H.DropItem(I)
	I.loc = S
	I.Owner = src
	if(made)
		if(!remaster_away_goods) remaster_away_goods = list()
		var/k = "[I.name]"
		remaster_away_goods[k] = (remaster_away_goods[k] || 0) + 1
	return 1

Player/proc/RemasterCatchUp(gap)
	remaster_catching_up = 1
	RemasterClaimWorld()
	var/worked = min(gap, REMASTER_AWAY_MAX)
	var/secs = worked / 10                       // real seconds that count
	var/budget = secs * REMASTER_AWAY_PACE       // seconds of work per villager
	remaster_away_tally = rm_far_tally || list()   // what units asleep as records did on waking (FarRecords.dm)
	remaster_away_goods = rm_far_goods || list()
	rm_far_tally = null
	rm_far_goods = null
	rm_far_settled = 0
	remaster_away_started = world.timeofday
	RemasterAwayRot(round(secs / 60))             // stored food ages (Ailments.dm)
	world.log << "Remastered: [key] was away [RemasterAwaySpan(gap)]; catching up"
	var/hit0 = rm_hit_id
	var/list/before = list()
	for(var/k in list("wood", "stone", "food")) before[k] = RemasterStockCount(k)
	// Board workers take the open orders first, as they would have (Board.dm).
	remaster_board_clock = REMASTER_BOARD_EVERY - 1
	RemasterBoardTick()
	var/list/workers = list()
	var/waiting = 0
	for(var/mob/Monsters/M in UnitList)
		if(M.Owner != src || M.HP <= 0 || M.GoingToDie || !isturf(M.loc) || M.Egg || M.Wagon) continue
		if(M.rm_far_woke) continue     // it was a record: it lived its time asleep through on waking (FarRecords.dm)
		workers += M
	// In passes, so what one job brings in is there for the next: gathering and building, then
	// cooking (the hunters' meat too), then the carpenters (the woodcutters' wood too).
	for(var/pass = 1, pass <= 3, pass++)
		for(var/mob/Monsters/M in workers)
			if(RemasterAwayOver()) break
			if(M.remaster_role_paused || M.remaster_paused) continue
			var/role = M.remaster_job
			if(role == "board") role = (M.remaster_board_role in list("woodcutter", "miner")) ? M.remaster_board_role : null
			if(pass == 1)
				switch(role)
					if("woodcutter", "miner") M.RemasterAwayHarvest(src, budget, role)
					if("hauler") M.RemasterAwayHaul(src, budget)
					if("farmer") M.RemasterAwayFarm(src, secs, budget)
					if("hunter") M.RemasterAwayHunt(src, budget)
					if("builder") M.RemasterAwayBuild(src, budget)
					if("gravedigger") M.RemasterAwayGravedig(src)   // Graves.dm
					if("merchant") waiting++
				if(M.remaster_builder && role != "builder") M.RemasterAwayBuild(src, budget)   // on construction duty
			else if(pass == 2)
				if(role == "cook") M.RemasterAwayCook(src, budget)
			else if(length(M.remaster_production)) M.RemasterAwayCraft(src, budget)
	// Eating, sleeping and healing take the whole time, not just the working part: as live, through the meals, sleep,
	// remedies and stone they get (FarRecords.dm RmFarLiveThrough, which records use too), never topped up for the time.
	var/list/span = list()
	for(var/mob/Monsters/M in workers)
		M.RemasterAwayLive(src, secs, 1)
		span[M] = secs
	RmFarLiveThrough(src, span)
	remaster_board_clock = REMASTER_BOARD_EVERY - 1
	RemasterBoardTick()
	var/list/gained = list()
	for(var/k in before)
		var/d = RemasterStockCount(k) - before[k]
		if(d) gained[k] = d
	for(var/list/H in rm_hits.Copy()) if(H[1] > hit0) rm_hits -= list(H)    // the hunt's throws: nobody saw them
	remaster_away_report = RemasterAwayReport(gap, worked, gained, waiting)
	RemasterLog("While you were away ([RemasterAwaySpan(gap)]): [jointext(remaster_away_report["lines"], " · ")]", "work", RemasterStockpile())
	var/took = world.timeofday - remaster_away_started
	world.log << "Remastered: [key] caught up in [(took < 0 ? took + 864000 : took) / 10] s"
	remaster_catching_up = 0
	remaster_seen = RemasterNow()

// An item's name for the card: "WoodenBucket" -> "Wooden bucket", "UnCutEmerald" -> "Uncut emerald".
proc/RemasterAwayName(n)
	n = replacetext("[n]", "UnCut", "Uncut")
	var/out = ""
	for(var/i = 1, i <= length(n), i++)
		var/c = copytext(n, i, i + 1)
		var/up = c != lowertext(c)
		if(up && i > 1 && copytext(n, i - 1, i) != " ") out += " "
		out += i == 1 ? uppertext(c) : lowertext(c)
	return out

proc/RemasterAwaySpan(t)
	var/m = round(t / 600)
	if(m < 60) return "[max(1, m)] min"
	var/h = round(m / 60)
	m -= h * 60
	return m ? "[h] h [m] min" : "[h] h"

Player/proc/RemasterAwayReport(gap, worked, list/gained, waiting)
	var/list/T = remaster_away_tally || list()
	var/list/lines = list()
	if(T["trees"]) lines += "Woodcutters felled [T["trees"]] tree\s"
	if(T["rock"]) lines += "Miners dug out [T["rock"]] tile\s of rock"
	if(T["hauled"]) lines += "Haulers brought in [T["hauled"]] thing\s"
	if(T["picked"] || T["planted"]) lines += "Farmers picked [T["picked"] || 0] fruit[T["planted"] ? " and planted [T["planted"]] seed\s" : ""]"
	if(T["cooked"] || T["burnt"]) lines += "Cooks cooked [T["cooked"] || 0] piece\s of meat[T["burnt"] ? " ([T["burnt"]] burnt)" : ""]"
	if(T["restocked"]) lines += "Cooks put out [T["restocked"]] food in the food pots and stalls"
	if(T["kills"] || T["fish"]) lines += "Hunters brought in [T["kills"] || 0] animal\s[T["fish"] ? " and [T["fish"]] fish" : ""]"
	if(T["built"]) lines += "Builders put up [T["built"]] planned piece\s"
	if(T["crafted"] || T["craftfail"]) lines += "Carpenters made [T["crafted"] || 0] thing\s[T["craftfail"] ? " ([T["craftfail"]] failed)" : ""]"
	var/list/goods = list()
	if(remaster_away_goods) for(var/k in remaster_away_goods) goods += list(list(RemasterAwayName(k), remaster_away_goods[k]))
	var/list/stock = list()
	for(var/k in gained) stock += "[gained[k] > 0 ? "+" : ""][gained[k]] [k]"
	var/life = T["meals"] ? "Everyone ate ([T["meals"]] meal\s, [T["served"] ? "[T["served"]] from the food pots and stalls" : "from the stockpile"]) and slept" : "Everyone slept"
	if(T["hungry"]) life = "Food ran out: [T["hungry"]] came back hungry"
	var/list/events = list()
	if(T["caveins"]) events += "A tunnel caved in [T["caveins"] == 1 ? "once" : "[T["caveins"]] times"] (pillars hold tunnels up)"
	if(T["creatures"]) events += "Digging turned up [T["creatures"]] creature\s; [T["creatures"] == 1 ? "it was" : "they were"] driven off"
	if(T["build_waiting"]) events += "Building stopped for want of material: it's on the board"
	if(T["no_knife"]) events += "A hunter had no dagger or butcher knife to butcher with"
	if(T["rotted"]) events += "[T["rotted"]] piece\s of food rotted away on the stores (food pots and stalls keep it fresh)"
	if(T["treated"]) events += "The Doctor's stall cured [T["treated"]] fever\s"
	if(T["buried"]) lines += "The gravedigger buried [T["buried"]] of the dead"
	if(T["poisoned"] || T["spat"]) events += "Poisoned food: [T["poisoned"] || 0] villager\s ate it[T["spat"] ? ", [T["spat"]] tasted it and spat it out" : ""][T["poison_deaths"] ? ", [T["poison_deaths"]] died of it" : ""]. Check your food pots and stalls"
	if(waiting) events += "Merchants waited for you"
	if(!length(lines)) lines += "Nobody had work to do. Give villagers jobs in the Village tab and they keep working while you're away."
	return list("away"=RemasterAwaySpan(gap), "worked"=RemasterAwaySpan(worked), "capped"=gap > worked, "lines"=lines, "goods"=goods, "stock"=stock, "life"=life, "events"=events)

// --- Work ------------------------------------------------------------------------------

// Rock beside water or lava floods the tunnel when it opens (each race's dig code).
proc/RemasterAwayWet(turf/T)
	for(var/turf/W in range(1, T))
		if(("CanFish" in W.vars) && W.vars["CanFish"]) return 1
		if(W.icon_state == "Lava" || ("Content" in W.vars) && W.vars["Content"] == "Lava") return 1
	return 0

// An open tile beside T to work it from, straight sides first.
proc/RemasterAwayFoot(turf/T)
	for(var/d in list(NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST))
		var/turf/G = get_step(T, d)
		if(!G || G.density || (G.icon_state in list("Chasm", "Sky"))) continue
		var/ok = 1
		for(var/atom/movable/A in G) if(A.density && !ismob(A)) ok = 0
		if(ok) return G
	return null

// Holding the right tool: one it carries, else the best on a store; 0 = works by hand.
mob/Monsters/proc/RemasterAwayTool(Player/P, tool)
	if(!tool || HoldingWeapon == tool) return 1
	var/obj/Items/best = RemasterBestTool(tool, src)
	if(!best) for(var/turf/S in P.RemasterStores()) if(S.z == z)
		best = RemasterBestTool(tool, S, P)
		if(best) break
	if(!best) return 0
	if(best.loc != src)
		if(best.weight + weight > weightmax) return 0
		ForcePickUpItem(best)
	EquipItem(best)
	return HoldingWeapon == tool

// Chop or dig T from F until it opens, the way the job does it (Orders.dm RemasterHandWork for
// the by-hand blow). Returns the blows, or -1 when it can't be worked.
mob/Monsters/proc/RemasterAwayWork(Player/P, turf/T, turf/F, tool, hand)
	loc = F
	dir = get_dir(F, T)
	var/hunger = Hunger
	var/tired = Tiredness
	var/list/near = list()                // what was there before: items and creatures
	for(var/atom/movable/A in range(2, F)) near[A] = 1
	for(var/obj/Items/I in src) near[I] = 1
	var/list/open = list()
	for(var/turf/X in range(3, F)) if(!X.density) open += X
	var/blows = 0
	var/stuck = 0
	remaster_away_working = 1     // its blows give as they are worked (Yield.dm)
	while(T.density && blows < 600 && !RemasterTendReached(T, src))   // stops at a tending mark (Yield.dm)
		if(rm_far_settling) RmFarPause()   // a record living its time through shares the tick out (FarRecords.dm)
		var/hp = RemasterWorkProgress(T)
		var/held = HoldingWeapon
		if(hand) HoldingWeapon = tool
		destination = T
		Bump(T)
		if(hand) HoldingWeapon = held
		blows++
		if(!T.density) break
		if(RemasterWorkProgress(T) < hp) stuck = 0     // a holding vein counts its ore
		else if(++stuck >= 3) break
	destination = null
	remaster_away_working = 0
	Hunger = hunger                       // meals are counted for the whole time (RemasterAwayLive)
	Tiredness = tired
	// A cave-in (each race's dig code) refills open tunnel round here: nobody stays inside it.
	var/caved = 0
	for(var/turf/X in open) if(X.density && X != T) caved = 1
	if(caved) P.RemasterAwayAdd("caveins")
	if(isturf(loc) && loc.density)
		var/turf/O = RemasterNearestOpen(loc, src)
		if(O) loc = O
	// Creatures the digging turned up are driven off.
	for(var/mob/Monsters/X in range(2, F)) if(!near[X] && !istype(X.Owner, /Player))
		P.RemasterAwayAdd("creatures")
		del X
	// The goods go to the stockpile.
	for(var/obj/Items/I in range(2, F)) if(!near[I] && isturf(I.loc)) P.RemasterAwayStore(I)
	for(var/obj/Items/I in src) if(!near[I] && I.suffix == "(Carrying)" && !I.EquipmentType()) P.RemasterAwayStore(I)
	return (T.density && !RemasterTendReached(T, src)) ? -1 : blows

// Woodcutters and miners (and board workers borrowing those roles): the nearest tree or rock to
// the work area, as RemasterRoleTick (Delivery.dm) picks it, one after another.
mob/Monsters/proc/RemasterAwayHarvest(Player/P, budget, role)
	var/turf/C = locate(remaster_area_x, remaster_area_y, remaster_area_z)
	if(!C) return
	var/kind = role == "woodcutter" ? "Chop" : "Mine"
	var/resource = role == "woodcutter" ? "wood" : "stone"
	var/list/O = remaster_job == "board" ? P.RemasterBoardOrder(remaster_board_claim) : null
	var/goal = O ? O["baseline"] + O["amount"] : 0
	var/tool = RemasterToolFor(kind)
	var/hand = tool && !RemasterAwayTool(P, tool)
	var/turf/home = loc
	var/done = 0
	while(budget > 0 && done < REMASTER_AWAY_JOBS && !P.RemasterAwayOver())
		if(rm_far_settling)
			RmFarPause()
			P.remaster_away_started = world.timeofday   // its own 12 s cap counts the work, not the waits
		if(O && P.RemasterStockCount(resource) >= goal) break
		var/turf/T
		var/turf/F
		var/best = 1#INF
		for(var/turf/X in range(6, C))
			if(!X.density || (X.Owner && X.Owner != P)) continue
			if(kind == "Chop" ? !X.Tree : (!X.CanDigAt || X.Tree || X.IsWall || RmBuilt(X) || RemasterAwayWet(X))) continue
			if(RemasterTendReached(X, src)) continue    // tended (Yield.dm)
			var/d = get_dist(X, C)
			if(d >= best) continue
			var/turf/G = RemasterAwayFoot(X)
			if(!G) continue
			T = X
			F = G
			best = d
		if(!T) break
		var/blows = RemasterAwayWork(P, T, F, tool, hand)
		if(blows < 0) break
		budget -= blows * (hand ? 2 : max(0.3, Delay / 10)) + REMASTER_AWAY_TRIP
		done++
		P.RemasterAwayAdd(kind == "Chop" ? "trees" : "rock")
	loc = home
	destination = null

// Haulers: loose things in the work area onto the store that takes them.
mob/Monsters/proc/RemasterAwayHaul(Player/P, budget)
	var/turf/C = locate(remaster_area_x, remaster_area_y, remaster_area_z)
	if(!C) return
	var/n = 0
	for(var/obj/Items/I in range(6, C))
		if(n >= REMASTER_AWAY_JOBS || budget <= 0) break
		if(!isturf(I.loc) || !P.RemasterMayCollect(I) || !P.RemasterStockAccepts(I) || I.weight > weightmax || RemasterOnStore(I) || RmShunsSilver(I)) continue
		if(P.RemasterAwayStore(I, 0))
			n++
			budget -= REMASTER_AWAY_TRIP
	P.RemasterAwayAdd("hauled", n)

// The growth timer of a planted seed (TomatoGrow/GrapeGrow, Vars.dm), without the wait.
proc/RemasterAwayGrow(obj/Items/Seeds/S)
	if(!S || !isturf(S.loc)) return
	if(istype(S, /obj/Items/Seeds/TomatoSeed))
		var/obj/Items/Plants/TomatoPlant/T = new(S.loc)
		T.name = "Tomato Plant"
	else
		var/obj/Items/Plants/GrapeVine/G = new(S.loc)
		G.name = "Grape Vine Plant"
	del S

// Farmers: seeds come up, each plant fills again (one fruit every 2 minutes, PlantRegen in
// Vars.dm) and is picked while the farmer has time, then seeds from the store go into free
// farmland (FoodRoles.dm). Not in winter, which kills seeds.
mob/Monsters/proc/RemasterAwayFarm(Player/P, secs, budget)
	var/turf/A = RemasterFoodArea()
	var/winter = Season == "Winter"
	if(!winter) for(var/obj/Items/Seeds/S in range(REMASTER_FOOD_AREA, A))
		if(S.suffix == "(Planted)" && isturf(S.loc) && (istype(S, /obj/Items/Seeds/TomatoSeed) || istype(S, /obj/Items/Seeds/GrapeSeed))) RemasterAwayGrow(S)
	var/regrow = round(secs / 120)
	var/picks = 0
	for(var/obj/Items/Plants/G in range(REMASTER_FOOD_AREA, A))
		if(!(istype(G, /obj/Items/Plants/TomatoPlant) || istype(G, /obj/Items/Plants/GrapeVine))) continue
		if(G.Owner && G.Owner != P) continue
		var/n = min(max(0, G.Content - 1) + regrow, REMASTER_AWAY_PICKS - picks, round(budget / 8))
		if(n <= 0) continue
		var/grape = istype(G, /obj/Items/Plants/GrapeVine)
		for(var/i = 1, i <= n, i++)
			var/obj/Items/Food/F = grape ? new/obj/Items/Food/Grape(G.loc) : new/obj/Items/Food/Tomato(G.loc)
			P.RemasterAwayStore(F)
		picks += n
		budget -= n * 8
		G.Content = 2                      // what ripened since the last picking
		G.icon_state = grape ? "PPlant4" : "Plant4"
	P.RemasterAwayAdd("picked", picks)
	if(winter) return
	var/planted = 0
	for(var/turf/T in range(REMASTER_FOOD_AREA, A))
		if(budget <= 0) break
		if(T.icon_state != "FarmLand" || T.density || (("HasPlantIn" in T.vars) && T.vars["HasPlantIn"])) continue
		var/taken = 0
		for(var/obj/Items/Seeds/X in T) taken = 1
		for(var/obj/Items/Plants/X in T) taken = 1
		if(taken) continue
		var/obj/Items/Seeds/seed
		for(var/turf/S in P.RemasterStores()) if(S.z == T.z)
			for(var/obj/Items/Seeds/X in range(1, S)) if(isturf(X.loc) && (istype(X, /obj/Items/Seeds/TomatoSeed) || istype(X, /obj/Items/Seeds/GrapeSeed)))
				seed = X
				break
			if(seed) break
		if(!seed) break
		seed.loc = T
		seed.suffix = "(Planted)"
		if("HasPlantIn" in T.vars) T.vars["HasPlantIn"] = 1
		RemasterAwayGrow(seed)
		planted++
		budget -= 10
	P.RemasterAwayAdd("planted", planted)

// Hunters (RemasterHunterTick in FoodRoles.dm): bodies lying in the area are butchered, then the
// animals in it are hunted: with a bow when it has arrows (the original single shot, BowTarget),
// else javelins, throwing axes or stones (RemasterThrowAt, Throwing.dm), from a few tiles off,
// taking arrows or throwing weapons from a store when it has none and picking them up again;
// else with the original Attack() beside them. Then butchered with TearMeat (knife in hand), the
// meat to the stockpile. With no game left, they fish the water with the race's own water
// code. Their prey can't strike back here, as nothing else moves.
mob/Monsters/proc/RemasterAwayHunt(Player/P, budget)
	if(!RemasterCanButcher() && !RemasterHunterKnife())
		P.RemasterAwayAdd("no_knife")
		return
	var/turf/A = RemasterFoodArea()
	var/turf/home = loc
	var/list/tried = list()
	var/kills = 0
	while(budget > 0 && kills < REMASTER_AWAY_JOBS && !P.RemasterAwayOver())
		var/mob/Body/B
		for(var/mob/Body/X in range(REMASTER_FOOD_AREA, A)) if(isturf(X.loc) && !tried[X] && (X.Critter || X.Race == "Fish"))
			B = X
			break
		if(B)
			tried[B] = 1
			RemasterAwayButcher(P, B)
			budget -= REMASTER_AWAY_TRIP
			continue
		var/mob/Monsters/prey
		var/best = 1#INF
		for(var/mob/Monsters/C in range(REMASTER_FOOD_AREA + 5, A))
			if(!C.Critter || C.HP <= 0 || C.GoingToDie || C.Owner == Owner || tried[C]) continue
			if(istype(C, /mob/Monsters/Critters/TowerCap) || istype(C, /mob/Monsters/Critters/PoisonSporePlant) || istype(C, /mob/Monsters/Critters/CarnivorousPlant)) continue
			var/d = get_dist(A, C)
			if(d < best)
				prey = C
				best = d
		if(!prey) break
		tried[prey] = 1
		if(!isturf(prey.loc)) continue
		var/turf/at = prey.loc
		var/strikes = 0
		// shot or thrown from a few tiles off, then picked up again where they landed
		var/bow = RemasterHunterBow()
		if(bow && !RemasterQuiverCount(src)) RemasterAwayRearm(P, 1)
		if(!(bow && RemasterQuiverCount(src)) && !RemasterThrowable(2)) RemasterAwayRearm(P)
		var/shoot = bow && RemasterQuiverCount(src) && RemasterHunterWield("Bow")
		var/turf/T = (shoot || RemasterThrowable(2)) ? RemasterAwayThrowSpot(prey) : null
		if(T)
			loc = T
			dir = get_dir(T, at)
			while(prey && prey.HP > 0 && !prey.GoingToDie && strikes < 40)
				if(shoot && RemasterQuiverCount(src))
					Target = prey
					BowOn = 1
					BowTarget(1)
					BowOn = 0
					Target = null
				else
					var/obj/Items/I = RemasterThrowable(get_dist(src, prey))
					if(!I) break
					RemasterThrowAt(prey, I)
				strikes++
			for(var/obj/Items/Thrown/X in range(1, at)) if(isturf(X.loc) && X.weight + weight <= weightmax) ForcePickUpItem(X)
			if(shoot)
				var/turf/stand = loc
				loc = at
				RemasterHunterQuiverUp()
				loc = stand
		// beside it, by hand or blade (Attack, as the Bump combat does)
		if(prey && prey.HP > 0 && !prey.GoingToDie && isturf(prey.loc))
			var/turf/F = RemasterAwayFoot(prey.loc)
			if(F)
				loc = F
				while(prey && prey.HP > 0 && !prey.GoingToDie && strikes < 60)
					Attack(prey)
					strikes++
		if(prey && prey.HP > 0 && !prey.GoingToDie) continue
		kills++
		budget -= 45 + strikes
		for(var/mob/Body/X in range(1, at)) if(!tried[X])
			tried[X] = 1
			RemasterAwayButcher(P, X)
	P.RemasterAwayAdd("kills", kills)
	if(budget > 0 && kills < REMASTER_AWAY_JOBS) RemasterAwayFish(P, A, budget)
	loc = home
	destination = null

// Up to four javelins or throwing axes, or (arrows = 1) the arrows, from a store (as RemasterHunterRearm).
mob/Monsters/proc/RemasterAwayRearm(Player/P, arrows = 0)
	if(arrows)
		RemasterHunterWield("Bow")
		var/turf/home = loc
		var/got = 0
		for(var/turf/S in P.RemasterStores()) if(S.z == z)
			loc = S
			got += RemasterHunterQuiverUp()
		loc = home
		return got
	var/n = 0
	for(var/turf/S in P.RemasterStores()) if(S.z == z)
		for(var/obj/Items/Thrown/X in range(1, S)) if(isturf(X.loc) && n < 4 && P.RemasterMayCollect(X) && X.weight + weight <= weightmax)
			ForcePickUpItem(X)
			n++
	return n

// An open tile 2 to 4 tiles from the prey with a clear view of it, to throw from.
mob/Monsters/proc/RemasterAwayThrowSpot(mob/Monsters/prey)
	var/turf/best
	var/best_d = 1#INF
	for(var/turf/T in range(4, prey))
		var/d = get_dist(T, prey)
		if(d < 2 || T.density || (T.icon_state in list("Chasm", "Sky"))) continue
		var/blocked = 0
		for(var/atom/movable/A in T) if(A.density && !ismob(A)) blocked = 1
		if(blocked || !(prey in view(6, T))) continue
		var/k = abs(d - 3) * 10 + get_dist(T, src)
		if(k < best_d)
			best = T
			best_d = k
	return best

// Butcher a body where it lies (TearMeat, Death.dm): the meat to the stockpile, the rest stays.
mob/Monsters/proc/RemasterAwayButcher(Player/P, mob/Body/B)
	var/turf/at = B.loc
	if(!isturf(at)) return
	loc = at
	var/list/near = list()
	for(var/obj/Items/I in at) near[I] = 1
	if(!RemasterCanButcher()) RemasterHunterWield("knife")
	ForcePickUpItem(B)
	TearMeat(B)
	if(B) del B
	for(var/obj/Items/Food/M in at) if(!near[M]) P.RemasterAwayStore(M)

// Fishing the water in the area with the race's own water code (Bump on the water).
mob/Monsters/proc/RemasterAwayFish(Player/P, turf/A, budget)
	var/turf/water
	var/best = 1#INF
	for(var/turf/T in range(REMASTER_FOOD_AREA, A)) if(("CanFish" in T.vars) && T.vars["CanFish"] && T.density)
		var/d = get_dist(A, T)
		if(d < best)
			water = T
			best = d
	if(!water) return
	var/turf/F = RemasterAwayFoot(water)
	if(!F) return
	loc = F
	dir = get_dir(F, water)
	var/hunger = Hunger
	var/fish = 0
	for(var/i = 1, i <= min(round(budget / 6), REMASTER_AWAY_JOBS), i++)
		var/list/before = list()
		for(var/mob/Body/X in range(1, F)) before[X] = 1
		destination = water
		Bump(water)
		for(var/mob/Body/X in range(1, F)) if(!before[X])
			fish++
			RemasterAwayButcher(P, X)
			loc = F
	destination = null
	Hunger = hunger
	P.RemasterAwayAdd("fish", fish)

// Builders (and units on construction duty): the construction tasks' own steps (Blueprints.dm:
// RemasterSiteFor, RemasterSiteNextTile, RemasterSiteFetch, RemasterSiteBuild with the original
// build code), without the walking. Leftovers go back to the stockpile.
mob/Monsters/proc/RemasterAwayBuild(Player/P, budget)
	var/turf/home = loc
	var/list/claims = list()
	for(var/mob/Monsters/X in P.UnitList) if(X != src && X.Owner == P && X.remaster_site) claims[X.remaster_site] = (claims[X.remaster_site] || 0) + 1
	var/built = 0
	var/stalls = 0
	while(budget > 0 && built < REMASTER_AWAY_JOBS && !P.RemasterAwayOver())
		var/list/S = length(P.RemasterOpenSites()) ? P.RemasterSiteFor(src, claims) : null
		if(!S || S["z"] != z) break
		if(remaster_site != S["id"]) RemasterSiteJoin(P, S)
		var/list/B = P.RemasterSiteNextTile(S, src)
		if(!B) break
		var/mode = B["mode"]
		var/turf/T = locate(B["x"], B["y"], B["z"])
		var/path = RemasterBuildMaterial(mode)
		var/need = RemasterBlueprintNeed(mode, T)
		if(need && RemasterCarriedCount(path) < need)
			var/obj/Items/I = P.RemasterSiteSource(S, path, src)
			if(!I)
				P.RemasterSiteMissing(S, path)
				P.RemasterAwayAdd("build_waiting")
				break
			loc = I.loc
			RemasterSiteFetch(P, S, path, I)
			budget -= REMASTER_AWAY_TRIP
			if(RemasterCarriedCount(path) < need) break
		if(RemasterSiteBodyNeed(mode)) break
		var/turf/W = (RemasterBuildShape(mode) in list("workshop", "stairs", "gate")) ? T : RemasterBuildSpot(T, src)
		if(!W) break
		loc = W
		var/had = S["built"]
		RemasterSiteBuild(P, S, B)
		if(S["built"] > had)
			built++
			stalls = 0
			budget -= 30
		else if(++stalls >= 3) break
	for(var/obj/Items/I in RemasterSiteLeftovers()) P.RemasterAwayStore(I, 0)
	remaster_site_load = null
	remaster_site_fetching = 0
	remaster_site_return = 0
	destination = null
	loc = home
	P.RemasterAwayAdd("built", built)

// Cooks: raw meat on the stores, at a campfire or kitchen near the stockpile (the original Cook
// option's effect, as RemasterCookTick in FoodRoles.dm).
mob/Monsters/proc/RemasterAwayCook(Player/P, budget)
	if(Race == "Spider" || Wagon) return
	var/turf/S = P.RemasterStockpile()
	if(!S) return
	var/fire = 0
	for(var/mob/WorkShops/W in range(15, S)) if(istype(W, /mob/WorkShops/CampFires/Fire) || istype(W, /mob/WorkShops/Kitchen/Right))
		if(!W.Owner || W.Owner == P) fire = 1
	if(!fire) return RemasterAwayRestock(P)
	var/n = 0
	for(var/turf/ST in P.RemasterStores()) for(var/obj/Items/Food/Meat/M in range(1, ST))
		if(n >= REMASTER_AWAY_JOBS || budget <= 0) break
		if(!isturf(M.loc) || M.icon_state != "RawMeat" || !P.RemasterMayCollect(M)) continue
		n++
		budget -= 15
		if(!prob(CookingSkill * 4))
			del M
			CookingSkill += 2
			P.RemasterAwayAdd("burnt")
		else
			M.name = "Cooked [M.name]"
			M.icon_state = "CookedMeat"
			CookingSkill += 1
			P.RemasterAwayAdd("cooked")
	RemasterAwayRestock(P)                         // the food pots and stalls (FoodSupply.dm)

// Carpenters: the queue (RemasterCraftTick in Settlement.dm), one wood an attempt.
mob/Monsters/proc/RemasterAwayCraft(Player/P, budget)
	var/n = 0
	while(length(remaster_production) && n < REMASTER_AWAY_JOBS && budget > 0)
		var/id = remaster_production[1]
		var/list/recipe = RemasterSettlementRecipe(id)
		if(!recipe)
			remaster_production.Cut(1, 2)
			continue
		if(Race == "Spider" || Wagon || (id == "spade" && Race == "Lizardman")) return
		var/turf/S = P.RemasterStockpile()
		var/mob/WorkShops/Carpentry/W
		for(var/mob/WorkShops/Carpentry/X in range(12, S || src)) if(!X.Owner || X.Owner == P)
			W = X
			break
		if(!W) return
		var/obj/Items/woods/wood/WOOD
		for(var/obj/Items/woods/wood/X in src) if(X.suffix == "(Carrying)")
			WOOD = X
			break
		if(!WOOD) for(var/obj/Items/woods/wood/X in range(12, W)) if(isturf(X.loc) && P.RemasterMayCollect(X))
			WOOD = X
			break
		if(!WOOD) return
		if(WOOD.loc == src) DropItem(WOOD)
		del WOOD
		remaster_production.Cut(1, 2)
		n++
		budget -= 30
		if(prob(WoodCraftingSkill * 4))
			var/output_type = recipe["output"]
			var/obj/Items/PRODUCT = new output_type(W.loc)
			P.RemasterAwayStore(PRODUCT)
			WoodCraftingSkill += 0.5
			P.RemasterAwayAdd("crafted")
		else
			if(id != "spike") WoodCraftingSkill += 0.5
			P.RemasterAwayAdd("craftfail")

// --- Living ------------------------------------------------------------------------------

// Something to eat on the stores: cooked meat and fruit first; raw meat only for meat eaters.
Player/proc/RemasterAwayFood(mob/Monsters/M)
	var/obj/Items/Food/pick
	var/rank = 0
	for(var/turf/S in RemasterStores()) if(S.z == M.z)
		for(var/obj/Items/Food/F in range(1, S)) if(isturf(F.loc) && RemasterMayCollect(F))
			var/r = F.icon_state == "CookedMeat" ? 4 : (F.icon_state in list("Tomato", "Grape")) ? 3 : F.icon_state == "RawMeat" ? (M.Carn ? 2 : 0) : 1
			if(r > rank)
				pick = F
				rank = r
	return pick

// The time away for one villager: off a wall that went up where it stood, poison eaten before run its course, the
// drink, food poisoning and a fever over the hours (Ailments.dm); then its meals, sleep and healing (RmFarLiveThrough).
// together: the catch-up lives everyone's needs through at once afterwards, so meals go round.
mob/Monsters/proc/RemasterAwayLive(Player/P, secs, together = 0)
	if(isturf(loc) && loc.density)                 // a wall went up where this villager stood
		var/turf/O = RemasterNearestOpen(loc, src)
		if(O) loc = O
	if(rm_poison > 0) RemasterPoisonResolve(P)     // poison eaten before, run its course (FoodSupply.dm)
	RemasterAwayAilments(P)                        // drink, food poisoning, fever (Ailments.dm)
	if(!together)
		var/list/span = list()
		span[src] = secs
		RmFarLiveThrough(P, span)
