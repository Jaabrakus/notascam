// PROTOTYPE, not part of the game (not in Cave Crawlers.dme): lodges, workplaces in the Songs of Syx way
// (planning/SONGS_OF_SYX_ECONOMY.md section 9). Loaded only into test arenas by run_prototype.py and
// watch_prototype.py.
//
// A banner declares a place, placed with one click (+ Banner, then a click on the ground); a builder puts
// it up (1 wood). What it declares:
//  - Woodcutter's lodge / Quarry lodge: a workplace. Its banner is its store (its workers unload there);
//    using the banner opens its card: zones to tend and upgrades.
//      Bench     one worker slot each (a new lodge comes with one planned)
//      Tool rack its workers work a quarter faster
//      Cart stop a loading stop on a tile of track, for a line to the stockpile
//    Upgrades go up round the banner (within 2 tiles), built by builders through the normal construction
//    tasks (Blueprints.dm), 1 wood each in this prototype.
//    Zones to tend are rectangles dragged from the card ("Add a zone"), within 15 tiles of the banner
//    and up to 13 by 13 each. Workers only work inside them (RemasterClaimed treats the rest as taken).
//    While the stores hold less than "stop at", the lodge keeps a board order open (Board.dm) for as many
//    workers as it has built benches; free board workers take it up by themselves. When the stores reach
//    the mark they first carry everything left lying in the zones in (as haulers), then stand down.
//  - Wood store / Stone store: a place to keep that good. No workers: anyone carrying it in unloads
//    there when it is nearer than the stockpile, and it counts as a store everywhere.
// The lodges go with the HUD model as "workplaces" (prototype HUD: village_stores.js).

#define RM_WP_MAX_SIDE 13            // a zone is worked from its centre, 6 tiles each way (Delivery.dm)
#define RM_LODGE_REACH 15            // zones lie within this of the banner

// --- The lodge's pieces (models by type path, View3D.dm Remaster3DModel) ---------------------------
obj/Items/Shafts/Sign/RmLodgeBanner
	name = "Banner"
	desc = "A banner that declares this place a lodge or a store. Use it to open its card."
	weight = 999
	remaster_placed = 1
	var/lodge
	DblClick()
		if(istype(usr, /Player) && lodge)
			usr:rm_wp_open = "[lodge]:[world.time]"
			usr:RemasterNotice("[name]: its card is open.")
			return
		return ..()
obj/Items/Furniture/Tables/RmBench
	name = "Lodge bench"
	icon = 'Cave.dmi'
	icon_state = "Table"
	weight = 999
	remaster_placed = 1
obj/Items/Furniture/Pillars/WoodenBeam/RmToolRack
	name = "Tool rack"
	weight = 999
	remaster_placed = 1
obj/Items/Furniture/Wagon_RmStoreShed
	name = "Store shed"
	icon = 'Cave.dmi'
	icon_state = "Wagon"
	weight = 999
	density = 0
	remaster_placed = 1

// mode -> list(label, type made)
var/list/rm_lodge_pieces = list(
	"Piece:rmbanner"=list("Lodge banner", /obj/Items/Shafts/Sign/RmLodgeBanner),
	"Piece:rmbench"=list("Lodge bench", /obj/Items/Furniture/Tables/RmBench),
	"Piece:rmrack"=list("Tool rack", /obj/Items/Furniture/Pillars/WoodenBeam/RmToolRack),
	"Piece:rmshed"=list("Store shed", /obj/Items/Furniture/Wagon_RmStoreShed))

// The pieces join the build catalog (1 wood each), so the construction tasks know them.
world/New()
	..()
	spawn(5)
		var/list/C = RemasterBuildCatalog()
		for(var/mode in rm_lodge_pieces)
			var/list/E = RemasterBuildDef("rm_[copytext(mode, 7)]", rm_lodge_pieces[mode][1], "lodge", mode, "wood", 1, 'Cave.dmi', "sign", "A lodge's piece, planned from its card")
			E["piececost"] = "1 wood"
			C += list(E)

// Builders put a piece up with the wood they carry.
Player/RemasterBuildPiece(mob/Monsters/M, turf/T, mode)
	if(!rm_lodge_pieces[mode]) return ..()
	if(!T || get_dist(M, T) > 1 || M.z != T.z || RemasterPieceBlocked(T, mode)) return 0
	var/obj/Items/woods/wood/W
	for(var/obj/Items/woods/wood/X in M) if(X.suffix != "(Equipped)")
		W = X
		break
	if(!W) return 0
	if(M.DropItem(W)) del(W)
	var/path = rm_lodge_pieces[mode][2]
	var/obj/Items/P = new path
	P.Owner = src
	P.remaster_owner_key = key
	P.suffix = null
	P.loc = T
	var/list/L = RmLodgeAt(T)
	if(L)
		if(istype(P, /obj/Items/Shafts/Sign/RmLodgeBanner)) P:lodge = L["id"]
		RemasterNotice("[L["name"]]: the [lowertext(rm_lodge_pieces[mode][1])] is up.")
	M.WoodCraftingSkill += 0.5
	return 1

// --- Lodges ---------------------------------------------------------------------------------------
Player/var/list/rm_workplaces          // the lodges (lists)
Player/var/rm_workplace_serial = 0
Player/var/tmp/rm_wp_open              // the card to open on the HUD: "id:serial"
mob/Monsters/var/tmp/list/rm_wp_rect   // list(x0, y0, x1, y1, z): this worker's zone
mob/Monsters/var/tmp/rm_wp_cleaning    // the lodge this worker is clearing up for
mob/Monsters/var/tmp/rm_wp_lodge       // the lodge this worker works for (order or clean-up)
mob/Monsters/var/tmp/rm_wp_boost = 0   // skill the tool rack lends, taken back when it leaves

// What a banner can declare: kind -> list(name, good, is a workplace)
var/list/rm_banner_kinds = list("woodlot"=list("Woodcutter's lodge", "wood", 1), "quarry"=list("Quarry lodge", "stone", 1),
	"woodstore"=list("Wood store", "wood", 0), "stonestore"=list("Stone store", "stone", 0))

proc/RmIsLodge(list/L)
	return L && rm_banner_kinds[L["kind"]] && rm_banner_kinds[L["kind"]][3]

// A banner at x, y: the place round it (2 tiles each way) is where its upgrades go up.
Player/proc/RmLodgeAdd(kind, x, y, z)
	if(!rm_banner_kinds[kind]) return null
	var/turf/T = locate(x, y, z)
	if(!T || T.density || RemasterBlueprintAt(T) || RemasterPieceBlocked(T, "Piece:rmbanner"))
		RemasterNotice("A banner goes on open, empty ground.")
		return null
	if(!rm_workplaces) rm_workplaces = list()
	rm_workplace_serial++
	var/count = 0
	for(var/list/X in rm_workplaces) if(X["kind"] == kind) count++
	var/list/L = list("id"="w[rm_workplace_serial]", "kind"=kind, "name"="[rm_banner_kinds[kind][1]][count ? " [count + 1]" : ""]",
		"x0"=max(1, x - 2), "y0"=max(1, y - 2), "x1"=min(world.maxx, x + 2), "y1"=min(world.maxy, y + 2), "z"=z, "bx"=x, "by"=y,
		"zones"=list(), "stop"=kind == "woodlot" ? 10 : 8, "made_total"=0, "last_count"=null, "phase"="work")
	rm_workplaces += list(L)
	RmLodgePlan(L, "Piece:rmbanner", T)
	if(RmIsLodge(L)) RmLodgePlan(L, "Piece:rmbench")    // and a first bench
	return L

Player/proc/RmWorkplace(id)
	if(rm_workplaces) for(var/list/L in rm_workplaces) if(L["id"] == id) return L
	return null

Player/proc/RmLodgeAt(turf/T)
	if(T && rm_workplaces) for(var/list/L in rm_workplaces)
		if(T.z == L["z"] && T.x >= L["x0"] && T.x <= L["x1"] && T.y >= L["y0"] && T.y <= L["y1"]) return L
	return null

proc/RmWorkplaceGood(list/L)
	return rm_banner_kinds[L["kind"]] ? rm_banner_kinds[L["kind"]][2] : "wood"

proc/RmInRect(atom/A, list/R)
	var/turf/T = RemasterGetTurf(A)
	return T && R && T.z == R[5] && T.x >= R[1] && T.x <= R[3] && T.y >= R[2] && T.y <= R[4]

Player/proc/RmLodgeYard(list/L)
	return block(locate(L["x0"], L["y0"], L["z"]), locate(L["x1"], L["y1"], L["z"]))

// Built pieces of a kind in the yard; planned ones not yet up.
Player/proc/RmLodgeBuilt(list/L, path)
	. = list()
	for(var/turf/T in RmLodgeYard(L)) for(var/obj/O in T) if(istype(O, path)) . += O
Player/proc/RmLodgePlanned(list/L, mode)
	. = 0
	if(remaster_blueprints) for(var/list/B in remaster_blueprints) if(B["mode"] == mode && RmInRect(locate(B["x"], B["y"], B["z"]), list(L["x0"], L["y0"], L["x1"], L["y1"], L["z"]))) .++

Player/proc/RmLodgeSlots(list/L)
	return length(RmLodgeBuilt(L, /obj/Items/Furniture/Tables/RmBench))

// The banner is the store, once it is up.
Player/proc/RmLodgeShed(list/L)
	var/list/S = RmLodgeBuilt(L, /obj/Items/Shafts/Sign/RmLodgeBanner)
	return length(S) ? RemasterGetTurf(S[1]) : null

// Plans a piece in the yard (at T, or the first free tile): a normal construction task for builders.
Player/proc/RmLodgePlan(list/L, mode, turf/T)
	if(!T)
		for(var/turf/X in RmLodgeYard(L))
			if(X.x == L["bx"] && X.y == L["by"]) continue
			if(RemasterBlueprintAt(X) || RemasterPieceBlocked(X, mode)) continue
			if(mode == "Piece:cartstop" && (X.x == L["x0"] || X.x == L["x1"] || X.y == L["y0"] || X.y == L["y1"]) == 0) continue   // a stop goes on the yard's edge, for the track
			T = X
			break
	if(!T) return 0
	var/old = Function
	Function = mode
	var/n = RemasterPaint("[T.x]|[T.y]|[T.x]|[T.y]")
	Function = old
	if(mode == "Piece:cartstop" && n)
		Function = "Piece:rail"
		RemasterPaint("[T.x]|[T.y]|[T.x]|[T.y]")
		Function = old
	return n

// --- Zones to tend -------------------------------------------------------------------------------
Player/proc/RmLodgeAddZone(list/L, x0, y0, x1, y1)
	var/ax = min(x0, x1)
	var/bx = max(x0, x1)
	var/ay = min(y0, y1)
	var/by = max(y0, y1)
	var/cx = round((ax + bx) / 2)
	var/cy = round((ay + by) / 2)
	ax = max(ax, cx - 6); bx = min(bx, cx + 6); ay = max(ay, cy - 6); by = min(by, cy + 6)
	var/turf/B = locate(L["bx"], L["by"], L["z"])
	if(get_dist(B, locate(cx, cy, L["z"])) > RM_LODGE_REACH) return null
	var/list/Z = list(ax, ay, bx, by, L["z"])
	L["zones"] += list(Z)
	return Z

// A worker with a zone treats anything outside it as taken: its role only works inside (Delivery.dm).
Player/RemasterClaimed(atom/A, mob/Monsters/worker)
	if(worker && worker.rm_wp_rect && !RmInRect(A, worker.rm_wp_rect)) return 1
	return ..()

// The board order this lodge keeps open, or null.
Player/proc/RmWorkplaceOrder(list/L)
	if(remaster_board_orders) for(var/list/O in remaster_board_orders) if(!O["done"] && O["standing"] == "wp:[L["id"]]") return O
	return null

// Loose goods lying in the lodge's zones, not on a store (what clean-up carries in).
Player/proc/RmWorkplaceLoose(list/L)
	. = list()
	var/list/stores = RemasterStores()
	for(var/list/Z in L["zones"])
		for(var/turf/T in block(locate(Z[1], Z[2], Z[5]), locate(Z[3], Z[4], Z[5])))
			var/on_store = 0
			for(var/turf/S in stores) if(get_dist(S, T) <= 1) on_store = 1
			if(on_store) continue
			for(var/obj/Items/I in T) if(!I.suffix && !I.remaster_placed && RemasterResourceKind(I) && RemasterMayCollect(I) && RemasterStockAccepts(I) && !(I in .)) . += I

// --- Stores and drop-off ---------------------------------------------------------------------------
// A banner that is up is a store: counted, eaten from, fetched from, and where its workers unload.
Player/RemasterStores()
	. = ..()
	if(rm_workplaces) for(var/list/L in rm_workplaces)
		var/turf/S = RmLodgeShed(L)
		if(S && !(S in .)) . += S

mob/Monsters/RemasterBeginDelivery(obj/Items/needed)
	. = ..()
	if(!. || !remaster_delivery || !istype(Owner, /Player)) return
	var/Player/P = Owner
	if(!P.rm_workplaces) return
	var/turf/T = remaster_delivery.target
	var/list/best
	var/turf/at
	for(var/list/L in P.rm_workplaces)
		var/turf/S = P.RmLodgeShed(L)
		if(!S || S.z != z) continue
		// a lodge's own workers unload at its banner; anyone carrying a store banner's good may use that
		if(RmIsLodge(L) ? rm_wp_lodge != L["id"] : !RmCarries(src, RmWorkplaceGood(L))) continue
		if((!T || get_dist(src, S) < get_dist(src, T)) && (!at || get_dist(src, S) < get_dist(src, at)))
			best = L
			at = S
	if(best)
		remaster_delivery.target = at
		remaster_order_status = "Taking it to the [best["name"]]; current task retained"

proc/RmCarries(mob/M, good)
	for(var/obj/Items/I in M) if(I.suffix == "(Carrying)" && RemasterResourceKind(I) == good) return 1
	return 0

mob/Monsters/RemasterDepositTick(datum/remaster_order/O, Player/P)
	var/turf/S = O ? O.target : null
	var/list/L = istype(S) && P.rm_workplaces ? P.RmLodgeAt(S) : null
	if(!L || P.RmLodgeShed(L) != S) return ..()
	if(!RemasterLandForWork()) return 0
	if(get_dist(src, S) > 1)
		RemasterApproach(O, S, 1)
		return 0
	destination = null
	var/amount = 0
	var/only = RmIsLodge(L) ? null : RmWorkplaceGood(L)     // a store banner keeps its own good
	for(var/obj/Items/I in contents.Copy())
		if(I.suffix != "(Carrying)" || I.EquipmentType() || !P.RemasterStockAccepts(I)) continue
		if(only && RemasterResourceKind(I) != only) continue
		if(DropItem(I) && I)
			I.loc = S
			I.Owner = P
			amount++
	remaster_blocked = null
	remaster_wait_for_resume = 0
	if(O == remaster_active) RemasterFinishOrder("Left [amount] thing[amount == 1 ? "" : "s"] at the [L["name"]]")
	return 1

// --- The work loop ---------------------------------------------------------------------------------
Player/RemasterBoardTick()
	if(rm_workplaces && !(remaster_board_clock % REMASTER_BOARD_EVERY))
		for(var/list/L in rm_workplaces) RmWorkplaceTick(L)
		RmWorkplaceZones()
	return ..()

Player/proc/RmWorkplaceTick(list/L)
	if(!RmIsLodge(L)) return
	var/good = RmWorkplaceGood(L)
	var/count = RemasterStockCount(good)
	if(!isnull(L["last_count"]) && count > L["last_count"] && L["phase"] != "idle") L["made_total"] += count - L["last_count"]
	L["last_count"] = count
	var/list/O = RmWorkplaceOrder(L)
	var/slots = RmLodgeSlots(L)
	if(count >= L["stop"])
		if(O) RemasterBoardFinish(O, "[L["name"]]: the stores have [count] [good] (stop at [L["stop"]])")
		var/list/loose = RmWorkplaceLoose(L)
		var/list/crew = RmWorkplaceCleaners(L)
		if(length(loose))
			L["phase"] = "cleanup"
			// free board workers clear up first: as haulers inside the zones, up to the lodge's benches
			if(length(crew) < max(1, slots))
				for(var/mob/Monsters/M in RmWorkplaceFree(L, max(1, slots) - length(crew)))
					M.rm_wp_cleaning = L["id"]
					M.remaster_job = "hauler"
					M.remaster_auto_unload = 1
					M.remaster_work_status = "[L["name"]]: clearing up"
		else
			var/busy = 0
			for(var/mob/Monsters/M in crew) if(M.RemasterDeliveryWeight(src) > 0) busy = 1
			if(!busy)
				for(var/mob/Monsters/M in crew) RmWorkplaceStandDown(M, L)
				L["phase"] = "idle"
		return
	// below the mark: clean-up hands go back to the board, and the order opens again
	for(var/mob/Monsters/M in RmWorkplaceCleaners(L)) RmWorkplaceStandDown(M, L)
	L["phase"] = "work"
	if(!slots || !length(L["zones"]))
		if(O) RemasterBoardFinish(O, "[L["name"]]: no bench or no zone")
		return
	var/list/Z1 = L["zones"][1]
	if(!O && RemasterStockpile())
		var/list/N = RemasterBoardPost(good, L["stop"] - count, 2, slots, null, list(round((Z1[1] + Z1[3]) / 2), round((Z1[2] + Z1[4]) / 2), Z1[5]), "wp:[L["id"]]")
		if(N) N["label"] = "[L["name"]]: [good] until the stores have [L["stop"]]"
	else if(O) O["workers"] = slots

Player/proc/RmWorkplaceCleaners(list/L)
	. = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.rm_wp_cleaning == L["id"]) . += M

// Free board workers, nearest the banner first.
Player/proc/RmWorkplaceFree(list/L, n)
	. = list()
	var/turf/C = locate(L["bx"], L["by"], L["z"])
	var/list/free = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_job == "board" && !M.remaster_board_claim && !M.rm_wp_cleaning && M.z == L["z"]) free += M
	while(length(.) < n && length(free))
		var/mob/Monsters/best
		for(var/mob/Monsters/M in free) if(!best || get_dist(M, C) < get_dist(best, C)) best = M
		free -= best
		. += best

Player/proc/RmWorkplaceStandDown(mob/Monsters/M, list/L)
	M.rm_wp_cleaning = null
	M.remaster_job = "board"
	M.RemasterStopWork()
	M.remaster_work_status = "Board worker: the [L["name"]]'s zones are cleared and its stores are full"

// Each lodge worker keeps to one of its zones (shared out in turn), and works a quarter faster with a
// tool rack built; everyone else is free.
Player/proc/RmWorkplaceZones()
	var/list/by_order = list()
	var/list/by_id = list()
	for(var/list/L in rm_workplaces)
		by_id[L["id"]] = L
		var/list/O = RmWorkplaceOrder(L)
		if(O) by_order[O["id"]] = L
	var/list/turns = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src)
		var/list/L = M.rm_wp_cleaning ? by_id[M.rm_wp_cleaning] : (M.remaster_board_claim ? by_order[M.remaster_board_claim] : null)
		if(M.rm_wp_cleaning && !L) M.rm_wp_cleaning = null
		var/rack = L && length(RmLodgeBuilt(L, /obj/Items/Furniture/Pillars/WoodenBeam/RmToolRack))
		// the tool rack's help: given while it works here, taken back when it leaves
		if(rack && !M.rm_wp_boost)
			M.rm_wp_boost = round(max(M.WoodCuttingSkill, M.MineingSkill) * 0.25)
			M.WoodCuttingSkill += M.rm_wp_boost
			M.MineingSkill += M.rm_wp_boost
		else if(!rack && M.rm_wp_boost)
			M.WoodCuttingSkill -= M.rm_wp_boost
			M.MineingSkill -= M.rm_wp_boost
			M.rm_wp_boost = 0
		if(!L || !length(L["zones"]))
			M.rm_wp_rect = null
			M.rm_wp_lodge = null
			continue
		M.rm_wp_lodge = L["id"]
		if(!M.rm_wp_rect || !(M.rm_wp_rect in L["zones"]))
			turns[L["id"]] = (turns[L["id"]] || 0) + 1
			M.rm_wp_rect = L["zones"][(turns[L["id"]] - 1) % length(L["zones"]) + 1]
		var/list/R = M.rm_wp_rect
		M.remaster_area_x = round((R[1] + R[3]) / 2); M.remaster_area_y = round((R[2] + R[4]) / 2); M.remaster_area_z = R[5]

Player/proc/RmWorkplaceRemove(list/L)
	var/list/O = RmWorkplaceOrder(L)
	if(O) RemasterBoardFinish(O, "[L["name"]] removed")
	for(var/mob/Monsters/M in RmWorkplaceCleaners(L)) RmWorkplaceStandDown(M, L)
	if(remaster_blueprints) for(var/list/B in remaster_blueprints.Copy()) if(RmLodgeAt(locate(B["x"], B["y"], B["z"])) == L) remaster_blueprints -= list(B)
	rm_workplaces -= list(L)
	RemasterSitesSync()

// --- Painting and the card ---------------------------------------------------------------------------
// + Woodcutter's lodge / + Quarry lodge drags the yard; a lodge's "Add a zone" drags a zone. Both use
// the game's own drag painting, in a lodge mode ("Piece:wp_...").
Player/RemasterPaint(value)
	if(copytext("[Function]", 1, 10) != "Piece:wp_") return ..()
	var/what = copytext(Function, 10)
	var/list/p = splittext("[value]", "|")
	if(p.len != 4) return 0
	RemasterCancelPlacement()
	if(copytext(what, 1, 6) == "zone_")
		var/list/L = RmWorkplace(copytext(what, 6))
		if(!L) return 0
		var/list/Z = RmLodgeAddZone(L, text2num(p[1]), text2num(p[2]), text2num(p[3]), text2num(p[4]))
		if(!Z)
			RemasterNotice("That's too far from the [L["name"]]'s banner: a zone lies within [RM_LODGE_REACH] tiles of it.")
			return 0
		var/inside = 0
		for(var/turf/T in block(locate(Z[1], Z[2], Z[5]), locate(Z[3], Z[4], Z[5])))
			if(L["kind"] == "woodlot" ? (T.Tree && T.density) : (T.CanDigAt && T.density && !T.Tree && !T.IsWall)) inside++
		RemasterNotice("[L["name"]]: a zone of [Z[3] - Z[1] + 1] by [Z[4] - Z[2] + 1] tiles with [inside] [L["kind"] == "woodlot" ? "tree" : "rock"][inside == 1 ? "" : "s"] to tend.")
		rm_wp_open = "[L["id"]]:[world.time]"
		RmWorkplaceTick(L)
		return 1
	// a click (or the end of a drag) is where the banner goes
	var/list/L = RmLodgeAdd(what, text2num(p[3]), text2num(p[4]), z)
	if(!L) return 0
	if(RmIsLodge(L)) RemasterNotice("[L["name"]]: a builder puts up its banner and a bench (1 wood each). Its banner is its store. Use the banner for its card: add zones to tend, and upgrades.")
	else RemasterNotice("[L["name"]]: a builder puts up its banner (1 wood). Whoever carries [RmWorkplaceGood(L)] unloads there when it's nearer than the stockpile.")
	rm_wp_open = "[L["id"]]:[world.time]"
	return 1

Player/RemasterTouchCommand(action, value)
	if(action == "wppaint")
		if(!rm_banner_kinds[value]) return 0
		Function = "Piece:wp_[value]"
		RemasterNotice("Click where the [lowertext(rm_banner_kinds[value][1])]'s banner goes. Esc to stop.")
		return 1
	if(action == "wp")
		var/list/p = splittext("[value]", "|")
		var/list/L = length(p) ? RmWorkplace(p[1]) : null
		if(!L) return 0
		var/what = length(p) >= 2 ? p[2] : null
		if(what == "stop" && length(p) >= 3) L["stop"] = clamp(L["stop"] + text2num(p[3]), 1, 200)
		else if(what == "upgrade" && length(p) >= 3)
			var/mode = list("bench"="Piece:rmbench", "rack"="Piece:rmrack", "cartstop"="Piece:cartstop")[p[3]]
			if(!mode || !RmIsLodge(L)) return 0
			if(p[3] != "bench" && (length(RmLodgeBuilt(L, p[3] == "rack" ? /obj/Items/Furniture/Pillars/WoodenBeam/RmToolRack : /obj/Items/Furniture/RemasterCartStop)) || RmLodgePlanned(L, mode)))
				RemasterNotice("[L["name"]] has one already.")
				return 0
			if(!RmLodgePlan(L, mode)) RemasterNotice("[L["name"]]: no free tile in the yard for it.")
		else if(what == "zone" && RmIsLodge(L))
			Function = "Piece:wp_zone_[L["id"]]"
			RemasterNotice("Drag a zone for the [L["name"]] to tend, within [RM_LODGE_REACH] tiles of its banner (up to 13 by 13). Esc to stop.")
		else if(what == "zonedrop")
			if(length(L["zones"])) L["zones"].len--
		else if(what == "remove")
			RmWorkplaceRemove(L)
			RemasterNotice("[L["name"]] removed. Its workers go back to the board; what it built stays.")
			return 1
		else if(what == "look") loc = locate(L["bx"], L["by"], L["z"])
		RmWorkplaceTick(L)
		return 1
	return ..()

// --- HUD data ----------------------------------------------------------------------------------------
Player/proc/RmWorkplaceData()
	. = list()
	if(!rm_workplaces) return
	for(var/list/L in rm_workplaces)
		var/list/O = RmWorkplaceOrder(L)
		var/list/names = list()
		var/status
		for(var/mob/Monsters/M in UnitList) if(M.Owner == src && ((O && M.remaster_board_claim == O["id"]) || M.rm_wp_cleaning == L["id"]))
			names += "[M.name]"
			if(!status) status = M.remaster_work_status
		var/good = RmWorkplaceGood(L)
		var/count = RemasterStockCount(good)
		var/loose = length(RmWorkplaceLoose(L))
		var/slots = RmLodgeSlots(L)
		var/list/banner = RmLodgeBuilt(L, /obj/Items/Shafts/Sign/RmLodgeBanner)
		if(!length(banner)) status = "Waiting for a builder to put up its banner"
		else if(!RmIsLodge(L))
			var/held = 0
			for(var/obj/Items/I in range(1, RmLodgeShed(L))) if(isturf(I.loc) && !I.remaster_placed && RemasterResourceKind(I) == good) held++
			status = "A store for [good]: [held] here now"
		else if(!slots) status = "Needs a bench: each bench is one worker"
		else if(!length(L["zones"])) status = "Add a zone to tend (drag it from this card)"
		else if(L["phase"] == "idle") status = "Idle: the stores have [count] [good] (stop at [L["stop"]])"
		else if(L["phase"] == "cleanup") status = "Clearing up: [loose] thing[loose == 1 ? "" : "s"] still lying in its zones"
		else if(!length(names)) status = "Waiting for workers: no free board worker"
		var/list/up = list()
		up["bench"] = list(slots, RmLodgePlanned(L, "Piece:rmbench"))
		up["rack"] = list(length(RmLodgeBuilt(L, /obj/Items/Furniture/Pillars/WoodenBeam/RmToolRack)), RmLodgePlanned(L, "Piece:rmrack"))
		up["cartstop"] = list(length(RmLodgeBuilt(L, /obj/Items/Furniture/RemasterCartStop)), RmLodgePlanned(L, "Piece:cartstop"))
		. += list(list("id"=L["id"], "name"=L["name"], "kind"=L["kind"], "good"=good, "slots"=slots, "stop"=L["stop"],
			"workers"="[length(names)]/[slots]", "who"=names, "stock"=count, "total"=L["made_total"], "loose"=loose,
			"phase"=L["phase"], "status"=status, "yard"=list(L["x0"], L["y0"], L["x1"], L["y1"], L["z"]),
			"zones"=L["zones"], "up"=up, "banner"=length(banner), "lodge"=RmIsLodge(L) ? 1 : 0, "what"=rm_banner_kinds[L["kind"]][1]))

Player/RemasterHUDData()
	. = ..()
	if(islist(.))
		.["workplaces"] = RmWorkplaceData()
		.["wpOpen"] = rm_wp_open
