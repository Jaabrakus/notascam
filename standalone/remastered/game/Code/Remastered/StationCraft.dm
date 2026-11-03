// Village crafting at every workshop, through the original menu code.
// The stations ask the player through RemasterActionChoice (Actions.dm). A
// player can be given answers in advance (remaster_preset_choices), so a board
// worker can run any original recipe: stand next to the station and "click"
// it with the answers pre-filled. Recipe lists are read from the real menus by
// a stand-in unit that is nowhere near the station and carries nothing, so
// reading a menu never makes anything.

Player/var/tmp
	list/remaster_preset_choices   // answers to use instead of asking
	remaster_preset_record = 0     // 1 = record the next question's options and cancel
	list/remaster_preset_seen      // options recorded in record mode
	remaster_preset_asked = 0      // questions asked during the current run
	list/remaster_station_catalog  // "type|race" -> list of recipes

// Called from RemasterActionChoice before it would ask the player.
// Returns null when no preset is active (ask normally).
Player/proc/RemasterPresetAnswer(list/options)
	if(!remaster_preset_choices) return null
	remaster_preset_asked++
	var/cancel = ("Cancel" in options) ? "Cancel" : "__none__"
	// Sticky (Abilities.dm): the menu asks once per creature nearby; keep the answer
	// until the question that offers it, and never ask the rest of the round.
	if(remaster_preset_sticky)
		if(!length(remaster_preset_choices)) return cancel
		if(!(remaster_preset_choices[1] in options) && remaster_preset_asked > 1) return cancel
	if(!length(remaster_preset_choices))
		if(remaster_preset_then_ask)
			// A skill bar run (Abilities.dm): its answers are used up; ask the rest normally.
			remaster_preset_choices = null
			remaster_preset_then_ask = 0
			return null
		if(remaster_preset_record) remaster_preset_seen = options.Copy()
		return cancel
	var/c = remaster_preset_choices[1]
	remaster_preset_choices.Cut(1, 2)
	return (c in options) ? c : cancel

// The workshops whose menus can be run. id -> list(label, type, material hints)
// The smelter fetches only real ore (stone is in the ores family), the gem cutter only uncut gems (never cut gems or
// rings, which it fetched back): ore-stores, 10-27.
proc/RemasterStationDefs()
	return list(
		"forge"=list("Forge", /mob/WorkShops/Forge, list(/obj/Items/Ingots/IronIngot, /obj/Items/Ingots/GoldIngot, /obj/Items/Ingots/SilverIngot, /obj/Items/Ingots/AdamantiumIngot, /obj/Items/woods/wood)),
		"smelter"=list("Smelter", /mob/WorkShops/Smelters, list(/obj/Items/ores/Iron, /obj/Items/ores/Silver, /obj/Items/ores/Gold, /obj/Items/ores/Adamantium, /obj/Items/ores/Sand)),
		"carpentry"=list("Carpentry", /mob/WorkShops/Carpentry, list(/obj/Items/woods/wood)),
		"bone"=list("Bone crafting", /mob/WorkShops/BoneCraft, list(/obj/Items/Bones, /obj/Items/Silks/SpiderSilk)),
		"leather"=list("Leatherworks", /mob/WorkShops/LeatherWorks, list(/obj/Items/Skin, /obj/Items/Silks/SpiderSilk)),
		"masonry"=list("Masonry", /mob/WorkShops/Masonary, list(/obj/Items/ores/stone)),
		"gem"=list("Gem cutter", /mob/WorkShops/GemCutter, list(/obj/Items/gems/UnCutRuby, /obj/Items/gems/UnCutEmerald, /obj/Items/gems/UnCutDiamond)),
		"kitchen"=list("Kitchen", /mob/WorkShops/Kitchen, list(/obj/Items/Food/Meat, /obj/Items/Shafts/WoodenBucket)),
		"potion"=list("Potion station", /mob/WorkShops/PotionStation, list(/obj/Items/Glands, /obj/Items/Potions)),
		"poison"=list("Poison station", /mob/WorkShops/PoisonStation, list(/obj/Items/Glands)))

proc/RemasterSkipOption(o)
	return o in list("Cancel", "Destroy", "Info", "Tear all Meat from Corpses")

Player/proc/RemasterNearestStation(type, atom/C, range = 25)
	var/mob/WorkShops/best
	var/best_d = 1#INF
	for(var/mob/WorkShops/W in range(range, C))
		if(!istype(W, type) || (W.Owner && W.Owner != src)) continue
		var/d = get_dist(W, C)
		if(d < best_d)
			best = W
			best_d = d
	return best

// Run a station's menu as the given unit, with answers given in advance.
Player/proc/RemasterRunStation(mob/WorkShops/W, mob/Monsters/M, list/path, record = 0)
	var/list/old = Selected
	var/oldusr = usr
	Selected = list(M)
	remaster_preset_choices = path.Copy()
	remaster_preset_record = record
	remaster_preset_seen = null
	remaster_preset_asked = 0
	usr = src
	try
		W.DblClick()
	catch(var/exception/E)
		world.log << "Remastered: station run failed: [E]"
	remaster_preset_choices = null
	remaster_preset_record = 0
	Selected = old
	usr = oldusr
	return remaster_preset_seen

// Read a workshop's recipes from its real menus (up to three levels) with a
// stand-in of the given race that is nowhere near the station.
Player/proc/RemasterStationRecipes(mob/WorkShops/W, race)
	var/key = "[W.type]|[race]"
	if(!remaster_station_catalog) remaster_station_catalog = list()
	if(remaster_station_catalog[key]) return remaster_station_catalog[key]
	var/path = text2path("/mob/Monsters/[race]")
	if(!path) path = /mob/Monsters/Human
	var/mob/Monsters/D = new path(null)
	D.Owner = src
	UnitList += D
	var/list/recipes = list()
	var/list/queue = list(list())
	var/runs = 0
	while(length(queue) && runs < 200)
		var/list/p = queue[1]
		queue.Cut(1, 2)
		runs++
		var/list/seen = RemasterRunStation(W, D, p, 1)
		if(!seen)
			if(length(p) >= 2) recipes += list(list("label"=p[length(p)], "path"=p))
			continue
		if(length(p) >= 3) continue
		for(var/o in seen) if(!RemasterSkipOption(o)) queue += list(p + o)
	UnitList -= D
	D.Owner = null
	del(D)
	remaster_station_catalog[key] = recipes
	return recipes

// --- Board "station" orders -------------------------------------------------
// recipe text: "stationid>answer>answer", e.g. "forge>Craft>Metal Axe".
mob/Monsters/var/tmp
	list/remaster_station_goods    // things this worker made and still carries
	list/remaster_station_mats     // materials this worker took from the stockpile
	remaster_station_idle = 0      // runs in a row that changed nothing

proc/RemasterStationParse(recipe)
	var/list/parts = splittext("[recipe]", ">")
	if(length(parts) < 2) return null
	var/list/D = RemasterStationDefs()[parts[1]]
	if(!D) return null
	for(var/o in parts) if(!o || RemasterSkipOption(o) || o == "Wooden Arrows") return null
	return list("id"=parts[1], "def"=D, "path"=parts.Copy(2))

Player/proc/RemasterStationOrigin()
	var/turf/S = RemasterStockpile()
	if(S) return S
	return loc

// Every recipe the village can post: stations near the stockpile, read with
// the races of the village's units.
Player/var/tmp
	list/remaster_station_cached
	remaster_station_cached_at = -1#INF

Player/proc/RemasterStationCatalog()
	// Looking for stations scans the area, so only every 10 seconds.
	if(remaster_station_cached && world.time - remaster_station_cached_at < 100) return remaster_station_cached
	remaster_station_cached_at = world.time
	remaster_station_cached = RemasterStationCatalogNow()
	return remaster_station_cached

Player/proc/RemasterStationCatalogNow()
	var/list/races = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.Race && !(M.Race in races) && text2path("/mob/Monsters/[M.Race]")) races += M.Race
	if(!length(races)) return list()
	var/atom/C = RemasterStationOrigin()
	if(!C) return list()
	var/list/out = list()
	var/list/defs = RemasterStationDefs()
	for(var/id in defs)
		var/list/D = defs[id]
		var/mob/WorkShops/W = RemasterNearestStation(D[2], C)
		if(!W) continue
		var/list/seen = list()
		var/list/recipes = list()
		for(var/race in races) for(var/list/R in RemasterStationRecipes(W, race))
			var/list/p = R["path"]
			var/key = "[id]>[jointext(p, ">")]"
			if(seen[key]) continue
			seen[key] = 1
			var/list/C = remaster_station_costs["[id]>[R["label"]]"]
			recipes += list(list("id"=key, "label"=R["label"], "uses"=(C ? C[1] : ""), "skill"=(C ? C[2] : "")))
		if(length(recipes)) out += list(list("id"=id, "label"=D[1], "recipes"=recipes))
	return out

mob/Monsters/proc/RemasterStationCarrying(list/L)
	var/list/out = list()
	if(L) for(var/obj/Items/I in L) if(I.loc == src) out += I
	return out

mob/Monsters/proc/RemasterStationPutBack(Player/P)
	var/list/carry = RemasterStationCarrying(remaster_station_goods) + RemasterStationCarrying(remaster_station_mats)
	if(!length(carry))
		remaster_station_goods = null
		remaster_station_mats = null
		return 0
	RemasterStoreFood(P, carry, "items")
	return 1

#define RM_CRAFT_EVERY 30                 // deciseconds between crafts at a station (RuneScape: one item every ~3 s)
mob/Monsters/var/tmp/remaster_craft_at = 0

mob/Monsters/proc/RemasterStationTick(Player/P, list/O)
	var/list/R = RemasterStationParse(O["recipe"])
	if(!R)
		P.RemasterBoardFinish(O, "That recipe can't be made")
		return
	var/list/D = R["def"]
	var/list/goods = RemasterStationCarrying(remaster_station_goods)
	remaster_station_goods = goods
	if(length(goods) >= 4 || (length(goods) && O["progress"] >= O["amount"]))
		RemasterStoreFood(P, goods, "goods")
		return
	if(O["progress"] >= O["amount"]) return
	var/mob/WorkShops/W = P.RemasterNearestStation(D[2], P.RemasterStationOrigin())
	if(!W)
		remaster_work_status = "Needs a [D[1]] near the stockpile"
		return
	// Materials: what the station uses, taken from the stockpile.
	var/list/hints = D[3]
	var/has = 0
	for(var/obj/Items/I in src) for(var/t in hints) if(istype(I, t)) has = 1
	if(!has)
		var/turf/S = P.RemasterStockpile()
		if(!S || S.z != z)
			remaster_work_status = "Set a stockpile on this level"
			return
		// from the store nearest the station that holds them, as builders and cooks fetch from any store: the drop-off's
		// own tile alone missed what carriers put on a painted stockpile's other cells (Zones.dm), and the order waited
		// "for materials on the stockpile" beside wood the board counted there (polish-loops, 2026-10-26)
		var/list/found = list()
		var/fd = 1#INF
		for(var/turf/T in P.RemasterStores()) if(T.z == z && get_dist(T, W) < fd)
			var/list/here = list()
			for(var/obj/Items/I in range(1, T)) if(isturf(I.loc) && P.RemasterMayCollect(I) && !RmShunsSilver(I)) for(var/t in hints) if(istype(I, t))
				here += I
				break
			if(length(here))
				found = here
				fd = get_dist(T, W)
		if(!length(found))
			remaster_work_status = "Waiting for materials on the stockpile"
			return
		if(!RemasterWorkToward(found[1], "materials")) return
		var/n = 0
		if(!remaster_station_mats) remaster_station_mats = list()
		for(var/obj/Items/I in found) if(n < 6 && get_dist(I, src) <= 1 && PickUpItem(I))
			remaster_station_mats += I
			n++
		remaster_work_status = n ? "Took [n] material\s for [O["label"]]" : "Can't carry the materials"
		return
	if(!RemasterWorkToward(W, D[1])) return
	// A craft takes a few seconds, as in RuneScape (one item every 3 s), not one every tick.
	if(world.time < remaster_craft_at)
		remaster_work_status = "Making [O["label"]]"
		return
	// One go at the original menu, answers given in advance.
	var/list/before = list()
	for(var/obj/Items/I in src) before += I
	for(var/obj/Items/I in range(1, src)) if(isturf(I.loc)) before += I
	P.RemasterRunStation(W, src, R["path"])
	var/list/after = list()
	for(var/obj/Items/I in src) after += I
	for(var/obj/Items/I in range(1, src)) if(isturf(I.loc)) after += I
	var/list/made = after - before
	var/changed = length(made) || length(before - after)
	if(changed) remaster_craft_at = world.time + RM_CRAFT_EVERY
	if(!changed)
		remaster_station_idle++
		remaster_work_status = "Trying [O["label"]]"
		if(remaster_station_idle >= 3)
			remaster_station_idle = 0
			O["note"] = "[name] is missing materials or skill for it"
			if(!remaster_board_skip) remaster_board_skip = list()
			remaster_board_skip[O["id"]] = world.time + 3000
			remaster_role_paused = 0
			RemasterBoardRelease()
			RemasterStationPutBack(P)
		return
	remaster_station_idle = 0
	remaster_board_since = world.time
	if(!remaster_station_goods) remaster_station_goods = list()
	for(var/obj/Items/I in made)
		if(I.loc != src && !PickUpItem(I)) continue
		remaster_station_goods += I
	if(length(made))
		O["progress"] = min(O["amount"], O["progress"] + 1)
		remaster_work_status = "Made [made[1]:name] ([O["progress"]]/[O["amount"]])"
	else remaster_work_status = "Spoiled an attempt at [O["label"]]"
