// Bulletin board (planning/VILLAGE_LIFE.md, part 2).
// Work orders are posted on the village board and claimed by villagers whose
// job is "Board worker". Standing orders ("keep at least 30 wood") post work
// orders by themselves whenever the stockpile drops below the number.
// Claimed work runs on the existing engine: a board worker borrows the
// woodcutter / miner role, the food haul job or the carpentry queue for the
// order, so there are no new movement or gathering rules.
// Saved data is strings and numbers only.

#define REMASTER_BOARD_EVERY 4   // RemasterTrack calls (about 2 seconds)
#define REMASTER_BOARD_DONE_KEPT 10

Player/var
	list/remaster_board_orders     // open and recently finished work orders
	list/remaster_board_standing   // kind -> list("keep", "priority", "enabled")
	remaster_board_serial = 0
Player/var/tmp/remaster_board_clock = 0
mob/Monsters/var/tmp
	remaster_board_claim           // claimed order id
	remaster_board_role            // role borrowed for the claimed order
	remaster_board_since = 0       // last time the claimed order made progress
	remaster_board_queued = 0      // craft attempts this claim added to the queue
	list/remaster_board_skip       // order id -> time before trying it again

// Kinds of work the board understands.
proc/RemasterBoardKinds()
	return RemasterHerbKinds() + list(   // herb orders come first: the Doctor posts them (Doctor.dm)
		"wood" = list("label"="Chop wood", "noun"="wood", "role"="woodcutter", "type"=/obj/Items/woods/wood),
		"stone" = list("label"="Mine stone", "noun"="stone", "role"="miner", "type"=/obj/Items/ores/stone),
		"food" = list("label"="Collect food", "noun"="food", "role"="food", "type"=/obj/Items/Food),
		"craft" = list("label"="Craft", "noun"="items", "role"="craft"),
		"station" = list("label"="Make", "noun"="items", "role"="station"))

var/rm_sc_serial = 0                      // RemasterStockCount's calls, for its per-call mark on items
obj/Items/var/tmp/rm_sc_mark = 0

Player/proc/RemasterStockCount(kind)
	var/turf/S = RemasterStockpile()
	if(!S) return 0
	var/list/K = RemasterBoardKinds()[kind]
	if(!K || !K["type"]) return 0
	var/item_type = K["type"]
	var/n = 0
	// The main stockpile and every zone count; an item round two stores counts once. The mark is this call's number on
	// the item (a list of counted items was O(items squared): OpenDream searches a list before adding a key to it).
	rm_sc_serial++
	var/mark = rm_sc_serial
	for(var/turf/T in RemasterStores())
		for(var/obj/Items/I in range(1, T)) if(isturf(I.loc) && istype(I, item_type) && I.rm_sc_mark != mark)
			I.rm_sc_mark = mark
			n++
	if(kind == "food") n += RemasterServedCount()   // food pots and stalls are food stores too (FoodSupply.dm)
	if(ispath(item_type, /obj/Items/RemasterHerb)) n += RemasterClinicHerbs(item_type)   // herbs in the Doctor's stalls (Doctor.dm)
	return n

Player/proc/RemasterBoardOrder(id)
	if(!remaster_board_orders) return null
	for(var/list/O in remaster_board_orders) if(O["id"] == id) return O
	return null

Player/proc/RemasterBoardPost(kind, amount, priority, workers, recipe, list/area, standing)
	var/list/K = RemasterBoardKinds()[kind]
	if(!K) return null
	amount = round(text2num("[amount]"))
	priority = round(text2num("[priority]"))
	workers = round(text2num("[workers]"))
	if(!amount || amount < 1 || amount > 200) return null
	if(!(priority in list(1, 2, 3))) priority = 2
	if(!workers || workers < 1 || workers > 10) workers = kind == "craft" ? 1 : 2
	if(kind == "craft")
		if(!RemasterSettlementRecipe(recipe)) return null
		workers = 1
	var/list/SR
	if(kind == "station")
		SR = RemasterStationParse(recipe)
		if(!SR) return null
		var/list/SD = SR["def"]
		var/list/SP = SR["path"]
		K = list("label"="Make [SP[length(SP)]] at the [SD[1]]")
		workers = 1
	if(!remaster_board_orders) remaster_board_orders = list()
	remaster_board_serial++
	var/list/R = kind == "craft" ? RemasterSettlementRecipe(recipe) : null
	var/list/O = list("id"="b[remaster_board_serial]", "kind"=kind, "amount"=amount, "priority"=priority, "workers"=workers,
		"recipe"=recipe, "label"=kind == "craft" ? "Craft [amount] [R["label"]]" : kind == "station" ? "[K["label"]] ×[amount]" : "[K["label"]]: [amount]",
		"baseline"=RemasterStockCount(kind), "progress"=0, "done"=0, "standing"=standing, "posted"=RemasterLineageDate(),
		"area"=area, "note"=null)
	remaster_board_orders += list(O)
	return O

Player/proc/RemasterBoardFinish(list/O, note)
	O["done"] = 1
	O["note"] = note
	// Orders the village posts by itself (a standing order's "keep at least", a building site's "for building") fill again
	// and again: they stay on the Work tab's done list, out of the village log (one hovering at its number wrote 25 lines
	// in 10 minutes). Orders the player posted are still logged.
	if(!O["standing"]) RemasterLog("Board: [O["label"]] · [note]", note == "Cancelled" ? "info" : "work", RemasterStockpile())
	for(var/mob/Monsters/M in UnitList) if(M.remaster_board_claim == O["id"]) M.RemasterBoardRelease()
	// Keep only a short history of finished orders.
	var/list/done = list()
	for(var/list/X in remaster_board_orders) if(X["done"]) done += list(X)
	while(length(done) > REMASTER_BOARD_DONE_KEPT)
		remaster_board_orders -= list(done[1])
		done.Cut(1, 2)

mob/Monsters/proc/RemasterBoardRelease()
	// Remove only the attempts this claim queued; crafts the player queued stay.
	if(remaster_board_role == "craft" && islist(remaster_production) && remaster_board_queued)
		var/list/O = istype(Owner, /Player) ? Owner:RemasterBoardOrder(remaster_board_claim) : null
		var/recipe = O ? O["recipe"] : null
		for(var/i = length(remaster_production), i >= 1 && remaster_board_queued > 0, i--)
			if(!recipe || remaster_production[i] == recipe)
				remaster_production.Cut(i, i + 1)
				remaster_board_queued--
	remaster_board_queued = 0
	if(remaster_active && remaster_active.automatic) RemasterCancelOrders()
	RemasterStopWork()
	remaster_board_claim = null
	remaster_board_role = null

Player/proc/RemasterBoardTick()
	remaster_board_clock++
	if(remaster_board_clock % REMASTER_BOARD_EVERY) return
	// 1. Standing orders post work when the stockpile is low.
	if(remaster_board_standing) for(var/kind in remaster_board_standing)
		var/list/S = remaster_board_standing[kind]
		if(!S["enabled"])
			for(var/list/O in remaster_board_orders) if(!O["done"] && O["standing"] == kind) RemasterBoardFinish(O, "Standing order turned off")
			continue
		var/count = RemasterStockCount(kind)
		var/list/open
		for(var/list/O in remaster_board_orders) if(!O["done"] && O["standing"] == kind) open = O
		if(open)
			if(count >= S["keep"]) RemasterBoardFinish(open, "Stockpile back to [count] [kind]")
		else if(count < S["keep"] && RemasterStockpile())
			RemasterBoardPost(kind, S["keep"] - count, S["priority"], 2, null, null, kind)
	// 2. Progress and completion.
	if(remaster_board_orders) for(var/list/O in remaster_board_orders.Copy())
		if(O["done"]) continue
		if(O["kind"] == "craft")
			var/claimed = 0
			for(var/mob/Monsters/M in UnitList) if(M.remaster_board_claim == O["id"])
				claimed = 1
				var/left = 0
				for(var/id in M.remaster_production) if(id == O["recipe"]) left++
				O["progress"] = O["amount"] - left
				if(!left) RemasterBoardFinish(O, "Crafted by [M.name]")
			if(!claimed && O["progress"] >= O["amount"]) RemasterBoardFinish(O, "Done")
		else if(O["kind"] == "station")
			if(O["progress"] >= O["amount"])
				var/carrying = 0
				for(var/mob/Monsters/M in UnitList) if(M.remaster_board_claim == O["id"] && length(M.RemasterStationCarrying(M.remaster_station_goods))) carrying = 1
				if(!carrying) RemasterBoardFinish(O, "Made [O["amount"]], stored on the stockpile")
		else
			var/gained = max(0, RemasterStockCount(O["kind"]) - O["baseline"])
			if(min(O["amount"], gained) > O["progress"])
				for(var/mob/Monsters/W in UnitList) if(W.remaster_board_claim == O["id"]) W.remaster_board_since = world.time
			O["progress"] = min(O["amount"], gained)
			if(gained >= O["amount"]) RemasterBoardFinish(O, "Stockpile gained [O["amount"]] [RemasterBoardKinds()[O["kind"]]["noun"] || O["kind"]]")
	// 3. Board workers claim open orders: priority 1 first, then oldest.
	var/list/claims = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_board_claim) claims[M.remaster_board_claim] = (claims[M.remaster_board_claim] || 0) + 1
	for(var/mob/Monsters/M in UnitList)
		if(M.Owner != src || M.remaster_job != "board") continue
		if(M.remaster_board_claim)
			var/list/C = RemasterBoardOrder(M.remaster_board_claim)
			// Stuck (no progress for 2 minutes) or paused workers let someone else try.
			var/stuck = C && !C["done"] && C["kind"] != "craft" && world.time - M.remaster_board_since > 1200
			if(C && !C["done"] && !stuck && !M.remaster_role_paused && !M.remaster_paused) continue
			if(stuck)
				if(!M.remaster_board_skip) M.remaster_board_skip = list()
				M.remaster_board_skip[C["id"]] = world.time + 3000
				C["note"] = "[M.name] couldn't make progress: [M.remaster_work_status]"
			claims[M.remaster_board_claim] = max(0, (claims[M.remaster_board_claim] || 1) - 1)
			M.RemasterBoardRelease()
		if(M.remaster_care || M.remaster_defense || M.remaster_role_paused || M.remaster_paused) continue
		if(M.RemasterOnConstruction()) continue
		var/list/best
		for(var/priority = 1, priority <= 3, priority++)
			for(var/list/O in remaster_board_orders)
				if(O["done"] || O["priority"] != priority) continue
				if((claims[O["id"]] || 0) >= O["workers"]) continue
				if(M.remaster_board_skip && M.remaster_board_skip[O["id"]] && world.time < M.remaster_board_skip[O["id"]]) continue
				if(!M.RemasterBoardCan(O, src)) continue
				best = O
				break
			if(best) break
		if(best)
			M.RemasterBoardClaim(src, best)
			claims[best["id"]] = (claims[best["id"]] || 0) + 1

Player/proc/RemasterBoardClaimers(id)
	var/n = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_board_claim == id) n++
	return n

// The nearest unclaimed tree (or diggable rock) within 25 tiles of the
// stockpile, or of this worker when there is no stockpile on this layer.
mob/Monsters/proc/RemasterBoardNextArea(Player/P, role)
	var/turf/S = P.RemasterStockpile()
	var/atom/C = (S && S.z == z) ? S : src
	var/turf/best
	var/best_d = 1#INF
	for(var/turf/T in range(25, C))
		if(!T.density || (T.Owner && T.Owner != P) || P.RemasterClaimed(T, src)) continue
		if(role == "woodcutter" && !T.Tree) continue
		if(role == "miner" && (!T.CanDigAt || T.Tree || T.IsWall || RmBuilt(T))) continue   // built columns too (Plans.dm)
		if(RemasterTendReached(T, src)) continue    // tended (Yield.dm)
		var/d = get_dist(T, C) + get_dist(T, src)
		if(d < best_d)
			best = T
			best_d = d
	return best

// A tree or rock face on one of the village's own work zones (wood or Gather zones for a woodcutter, stone or Gather for a
// miner), the nearest of the first 48 on each zone's list (Jobs.dm rm_jz_targets): where a board order's worker goes when
// nothing is in reach of its work area (first-house, 10-27).
Player/proc/RemasterBoardZoneSpot(role, mob/Monsters/M)
	if(!rm_jz || !rm_jz_targets) return null
	var/kind = role == "woodcutter" ? "wood" : "stone"
	var/turf/best
	var/bd = 1#INF
	for(var/list/Z in rm_jz) if((Z["kind"] == kind || Z["kind"] == "gather") && !Z["paused"] && Z["z"] == M.z)
		var/list/L = rm_jz_targets[Z["id"]]
		var/k = 0
		for(var/turf/T in L)
			if(++k > 48) break
			if(!T.density || (T.Owner && T.Owner != src)) continue
			if(role == "woodcutter" ? !T.Tree : (!T.CanDigAt || T.Tree || T.IsWall || RmBuilt(T))) continue
			var/d = get_dist(M, T)
			if(d < bd)
				best = T
				bd = d
	return best

mob/Monsters/proc/RemasterBoardCan(list/O, Player/P)
	if(O["kind"] == "craft") return !RemasterCanQueue(O["recipe"])
	if(P && (O["kind"] in list("wood", "stone")) && !P.RemasterStockAcceptsKind(O["kind"])) return 0
	return 1 // the borrowed role reports missing tools or blocked work

mob/Monsters/proc/RemasterBoardClaim(Player/P, list/O)
	var/list/K = RemasterBoardKinds()[O["kind"]]
	remaster_board_claim = O["id"]
	remaster_board_role = K["role"]
	var/turf/C
	var/list/A = O["area"]
	if(islist(A) && length(A) == 3) C = locate(A[1], A[2], A[3])
	if(!C) C = P.RemasterStockpile()
	if(C)
		remaster_area_x = C.x
		remaster_area_y = C.y
		remaster_area_z = C.z
	remaster_auto_unload = 1
	remaster_board_since = world.time
	if(remaster_board_role == "craft")
		// Only what is still needed; the player's own queued crafts stay.
		if(!islist(remaster_production)) remaster_production = list()
		remaster_board_queued = max(0, O["amount"] - O["progress"])
		for(var/i = 1, i <= remaster_board_queued, i++) remaster_production += O["recipe"]
	remaster_work_status = "Board: took \"[O["label"]]\""

// Called by RemasterSettlementTick for board workers.
mob/Monsters/proc/RemasterBoardWork(Player/P, list/RESERVED)
	var/list/O = remaster_board_claim ? P.RemasterBoardOrder(remaster_board_claim) : null
	if(!O || O["done"])
		if(remaster_board_claim) RemasterBoardRelease()
		RemasterStopWork()
		if(RemasterStationPutBack(P)) return
		if(RemasterZoneKeep(P)) return
		remaster_work_status = "Board worker: waiting for work orders"
		return
	if(remaster_board_role == "craft") return // the production queue runs it
	if(remaster_board_role == "station")
		RemasterStationTick(P, O)
		var/status = RemasterHasOrder() && remaster_order_status ? remaster_order_status : remaster_work_status
		remaster_work_status = "Board: [O["label"]] ([O["progress"]]/[O["amount"]]) · [status]"
		return
	// Borrow the matching role for this tick only.
	var/own = remaster_job
	remaster_job = remaster_board_role
	if(remaster_board_role in list("woodcutter", "miner")) RemasterRoleTick(P)
	else if(remaster_board_role == "herbs") RemasterHerbGatherTick(P, copytext(O["kind"], 6))   // Doctor.dm
	else RemasterHaulTick(P, RESERVED)
	remaster_job = own
	// Nearby trees or rock used up: move the work area to the nearest that's left.
	// The role's idle line became "Idle: no rock to mine within 6 tiles ..." (the playtest wording), so this never fired and an
	// order's workers stood at the stockpile with the rock 30 tiles off (first-house, 10-27): it fires on both, and goes to
	// the village's own zone for the good first.
	if((findtext("[remaster_work_status]", "No unclaimed work") || findtext("[remaster_work_status]", "Idle: no ")) && (remaster_board_role in list("woodcutter", "miner")))
		var/turf/T = P.RemasterBoardZoneSpot(remaster_board_role, src) || RemasterBoardNextArea(P, remaster_board_role)
		if(T)
			remaster_area_x = T.x; remaster_area_y = T.y; remaster_area_z = T.z
			remaster_work_status = "Moving to [remaster_board_role == "woodcutter" ? "trees" : "rock"] at [T.x], [T.y]"
	var/status = RemasterHasOrder() && remaster_order_status ? remaster_order_status : remaster_work_status
	remaster_work_status = "Board: [O["label"]] ([O["progress"]]/[O["amount"]]) · [status]"

Player/proc/RemasterBoardData()
	var/list/orders = list()
	if(remaster_board_orders) for(var/list/O in remaster_board_orders)
		var/list/names = list()
		var/stuck
		for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_board_claim == O["id"])
			names += "[M.name]"
			if(!stuck) stuck = M.remaster_work_status
		var/list/D = O.Copy()
		D["claimers"] = names
		D["status"] = O["done"] ? O["note"] : length(names) ? stuck : O["note"] ? O["note"] : RemasterBoardWaiting(O)
		orders += list(D)
	var/list/standing = list()
	for(var/kind in list("wood", "stone", "food"))
		var/list/S = remaster_board_standing ? remaster_board_standing[kind] : null
		standing += list(list("kind"=kind, "keep"=S ? S["keep"] : 0, "priority"=S ? S["priority"] : 2, "enabled"=S ? S["enabled"] : 0, "count"=RemasterStockCount(kind)))
	var/workers = 0
	var/waiting = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_job == "board")
		workers++
		if(!M.remaster_board_claim) waiting++
	var/list/recipes = list()
	for(var/list/R in RemasterSettlementRecipes()) recipes += list(list("id"=R["id"], "label"=R["label"], "uses"=R["cost"]))
	return list("orders"=orders, "standing"=standing, "workers"=workers, "waiting"=waiting, "stockpile"=!!RemasterStockpile(), "recipes"=recipes, "stations"=RemasterStationCatalog())

Player/proc/RemasterBoardWaiting(list/O)
	if(!RemasterStockpile()) return "Place a stockpile first (Work tab)"
	var/workers = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_job == "board") workers++
	if(!workers) return "No board workers: set a villager's job to Board worker"
	if((O["kind"] in list("wood", "stone")) && !RemasterStockAcceptsKind(O["kind"])) return "The stockpile filter doesn't accept [O["kind"]] (Work tab)"
	return "Waiting for a free board worker"

Player/proc/RemasterBoardCommand(action, value)
	var/list/parts = splittext("[value]", "|")
	switch(action)
		if("boardpost")
			// kind|amount|priority|workers|where|recipe
			if(parts.len < 5) return 0
			var/list/area
			if(parts[5] == "view" && isturf(loc)) area = list(x, y, z)
			var/recipe = parts.len >= 6 ? parts[6] : null
			var/list/O = RemasterBoardPost(parts[1], parts[2], parts[3], parts[4], recipe, area, null)
			RemasterNotice(O ? "Posted on the board: [O["label"]]." : "That work order isn't valid.")
			return !!O
		if("boardcancel")
			var/list/O = RemasterBoardOrder(value)
			if(!O || O["done"]) return 0
			RemasterBoardFinish(O, "Cancelled")
			if(O["standing"] && remaster_board_standing && remaster_board_standing[O["standing"]])
				var/list/S = remaster_board_standing[O["standing"]]
				S["enabled"] = 0
			return 1
		if("boardpriority")
			var/list/O = parts.len == 2 ? RemasterBoardOrder(parts[1]) : null
			if(!O || !(parts[2] in list("1", "2", "3"))) return 0
			O["priority"] = text2num(parts[2])
			return 1
		if("boardclear")
			if(!remaster_board_orders) return 0
			for(var/list/O in remaster_board_orders.Copy()) if(O["done"]) remaster_board_orders -= list(O)
			return 1
		if("standing")
			// kind|keep|priority|enabled
			if(parts.len != 4 || !(parts[1] in list("wood", "stone", "food"))) return 0
			var/keep = round(text2num(parts[2]))
			var/priority = text2num(parts[3])
			if(isnull(keep) || keep < 0 || keep > 500 || !(priority in list(1, 2, 3))) return 0
			if(!remaster_board_standing) remaster_board_standing = list()
			remaster_board_standing[parts[1]] = list("keep"=keep, "priority"=priority, "enabled"=(parts[4] == "1" && keep > 0))
			RemasterNotice(parts[4] == "1" && keep > 0 ? "Standing order: keep at least [keep] [parts[1]] in the stockpile." : "Standing order for [parts[1]] turned off.")
			return 1
	return 0
