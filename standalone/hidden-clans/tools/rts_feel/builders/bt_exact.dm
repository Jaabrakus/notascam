// Builders' answers, old against new (rts-feel, 2026-10-25): tools/rts_feel/builders/apply_bp.py must give every builder
// the same task and every material look the same piece as the code before it. The old code is copied here (BtOld*, the
// game's Blueprints.dm and Jobs.dm as of 2026-10-25 10:xx) and asked alongside the game's at every call, while 25 builders
// work 10 tasks (stone walls, wooden walls, stone floors) and stone and wood come and go: dropped by builders, on the
// stockpile, gone again; builders put elsewhere. Then the "stone arrives" case: everyone waiting, stone on the stockpile,
// and the very next pass must send a builder for it. Run on the base too (the copy's fidelity: 0 differences there).
//   tools/check_arena.py --test bt_exact.dm --entry BtxRun          (BT_CAND defined: the memo's hits are counted too)
var/btx_calls = list("site"=0, "ready"=0, "source"=0)
var/btx_diff = list("site"=0, "ready"=0, "source"=0)
var/list/btx_notes = list()
var/btx_none = 0      // material looks that found nothing
var/btx_memo = 0      // of them, answered by the step's memo (candidate)

proc/BtxDiff(k, text)
	btx_diff[k]++
	if(length(btx_notes) < 12) btx_notes += "[k]: [text]"

Player/RemasterSiteFor(mob/Monsters/M, list/claims)
	. = ..()
	var/list/old = BtOldSiteFor(src, M, claims)
	var/list/nw = .
	btx_calls["site"]++
	if(old != nw) BtxDiff("site", "[M.name] new [nw ? nw["id"] : "none"] old [old ? old["id"] : "none"] t=[world.time]")

Player/RemasterSiteReady(list/S, mob/Monsters/M)
	. = ..()
	var/old = BtOldReady(src, S, M)
	btx_calls["ready"]++
	if(!!old != !!.) BtxDiff("ready", "[M.name] [S["id"]] new [.] old [old] t=[world.time]")

Player/RemasterSiteSource(list/S, path, mob/Monsters/M)
#ifdef BT_CAND
	var/memo = M == rm_bp_unit && rm_bp_none && rm_bp_none["[S["z"]]|[path]"]
#endif
	. = ..()
	var/old = BtOldSource(src, S, path, M)
	btx_calls["source"]++
	if(!.)
		btx_none++
#ifdef BT_CAND
		if(memo) btx_memo++
#endif
	if(old != .) BtxDiff("source", "[M.name] [S["id"]] [path] new [.] old [old] t=[world.time]")

// --- the code before (Blueprints.dm RemasterSiteFor, RemasterSiteReady, RemasterSiteSource; Jobs.dm's lying pieces) ---
proc/BtOldSiteFor(Player/P, mob/Monsters/M, list/claims)
	var/list/cur = P.RemasterSite(M.remaster_site)
	if(cur && (cur["done"] || !P.RemasterSiteReach(cur, M) || cur["id"] == M.remaster_site_skip || !P.RemasterSiteEligible(cur, M))) cur = null
	if(cur && BtOldReady(P, cur, M)) return cur
	var/list/best
	var/best_score = 1#INF
	for(var/list/S in P.RemasterOpenSites())
		if(S == cur || S["id"] == M.remaster_site_skip || !P.RemasterSiteEligible(S, M) || !P.RemasterSiteReach(S, M)) continue
		if((claims[S["id"]] || 0) >= S["workers"]) continue
		if(!BtOldReady(P, S, M)) continue
		var/score = S["priority"] * 1000 + get_dist(M, locate(S["x"], S["y"], S["z"]))
		if(score < best_score)
			best = S
			best_score = score
	return best || cur

proc/BtOldReady(Player/P, list/S, mob/Monsters/M)
	if(S["ceil"] && length(P.RemasterBuildingRoofs(S))) return 1
	for(var/mode in P.RemasterSiteModes(S))
		if(!RemasterBuildEligible(mode, M) || M.RemasterSiteBodyNeed(mode)) continue
		var/path = RemasterBuildMaterial(mode)
		if(!path || !P.RemasterSiteNeedCount(S, path) || M.RemasterCarriedCount(path) || BtOldSource(P, S, path, M)) return 1
	return 0

proc/BtOldSource(Player/P, list/S, path, mob/Monsters/M)
	var/obj/Items/best
	var/best_d = 1#INF
	for(var/turf/T in P.RemasterStores())
		if(T.z != S["z"]) continue
		for(var/obj/Items/I in range(1, T))
			if(!istype(I, path) || !isturf(I.loc) || !P.RemasterMayCollect(I) || P.RemasterUnreachable(I) || I.remaster_placed) continue
			var/d = RemasterFlatDist(M, I)
			if(d < best_d)
				best = I
				best_d = d
	if(M.z == S["z"] && !RemasterFurniturePath(path)) for(var/obj/Items/I in range(12, M))
		if(!istype(I, path) || !isturf(I.loc) || !P.RemasterMayCollect(I) || P.RemasterUnreachable(I)) continue
		var/d = get_dist(M, I)
		if(d < best_d)
			best = I
			best_d = d
	if(best || !P.rm_ch_lying) return best
	var/bd = 1#INF
	for(var/obj/Items/I in P.rm_ch_lying)
		if(!I || !isturf(I.loc)) continue
		if(!istype(I, path) || I.z != S["z"] || P.RemasterUnreachable(I)) continue
		var/d = get_dist(M, I)
		if(d < bd)
			bd = d
			best = I
	return best

// --- the world ---
var/list/btx_items = list()
proc/BtxDrop(path, turf/T)
	if(!T || T.density) return
	var/obj/Items/I = new path(T)
	btx_items += I

proc/BtxNear(atom/A, r)
	var/turf/T = locate(clamp(A.x + rand(-r, r), 2, world.maxx - 1), clamp(A.y + rand(-r, r), 2, world.maxy - 1), A.z)
	return T

proc/BtxRun()
	sleep(30)
	world.game_state = 4
	rand_seed(20261025)
	remaster_fog = 0
	var/Player/P = new(locate(60, 50, 1))
	P.UnitList = list()
	P.key = "bpexact"
	Players += P
	usr = P
	P.remaster_stock_x = 60
	P.remaster_stock_y = 50
	P.remaster_stock_z = 1
	var/list/U = list()
	for(var/i = 1, i <= 40, i++) U += ObHuman(P, rand(10, 110), rand(10, 90), 1, 0)
	var/list/B = list()
	for(var/i = 1, i <= 25, i++)
		var/mob/Monsters/M = U[i]
		M.remaster_job = "builder"
		B += M
	P.remaster_blueprints = list()
	P.remaster_sites = list()
	var/list/taken = list()
	var/list/modes = list("PlaceStoneWall", "PlaceStoneWall", "PlaceStoneWall", "PlaceStoneWall", "PlaceStoneWall", "PlaceStoneWall", "PlaceWoodenWall", "PlaceWoodenWall", "PlaceStoneFloor", "PlaceStoneFloor")
	for(var/mode in modes)
		var/list/S = P.RemasterSiteNew(mode, 1)
		var/cx = rand(15, 105)
		var/cy = rand(15, 85)
		S["x"] = cx
		S["y"] = cy
		for(var/k = 1, k <= 15, k++)
			var/x = clamp(cx + rand(-6, 6), 2, 118)
			var/y = clamp(cy + rand(-6, 6), 2, 98)
			if(taken["[x],[y]"] || (x == 60 && y == 50)) continue
			taken["[x],[y]"] = 1
			P.remaster_blueprints += list(list("x"=x, "y"=y, "z"=1, "mode"=mode, "note"="Waiting for a builder", "tries"=0, "site"=S["id"]))
			S["left"]++
			S["total"]++
	// 1. stone and wood come and go while they work
	var/max_waiting = 0
	for(var/run = 1, run <= 260, run++)
		if(prob(30))
			var/mob/Monsters/M = pick(B)
			var/turf/T = prob(40) ? BtxNear(P.RemasterStockpile(), 1) : BtxNear(M, 10)
			for(var/n = rand(1, 3), n > 0, n--) BtxDrop(/obj/Items/ores/stone, T)
		if(prob(12)) BtxDrop(/obj/Items/woods/wood, prob(50) ? BtxNear(P.RemasterStockpile(), 1) : BtxNear(pick(B), 10))
		if(prob(12))
			for(var/obj/Items/I in btx_items.Copy())
				btx_items -= I
				if(I && isturf(I.loc))
					del(I)
					break
		if(prob(6))
			var/mob/Monsters/M = pick(B)
			var/turf/T = BtxNear(M, 15)
			if(T && !T.density) M.loc = T
		usr = P
		P.RemasterBlueprintTick(0)
		var/waiting = 0
		for(var/mob/Monsters/M in B) if(M.remaster_site && M.remaster_site_standby) waiting++
		max_waiting = max(max_waiting, waiting)
		sleep(2)
	var/built = 0
	for(var/list/S in P.remaster_sites) built += S["built"]
	world.log << "CK|the builders worked|[built > 0 && max_waiting > 0]|[built] pieces built; up to [max_waiting] builders waiting at once; [length(P.RemasterOpenSites())] tasks open"
	// 2. no material anywhere: everyone waits; then stone on the stockpile
	var/list/gone = list()
	for(var/obj/Items/ores/stone/I in world) gone += I
	for(var/obj/Items/woods/wood/I in world) gone += I
	for(var/obj/Items/I in gone) del(I)
	for(var/k = 1, k <= 40, k++)
		usr = P
		P.RemasterBlueprintTick(0)
		sleep(2)
	var/fetching0 = 0
	for(var/mob/Monsters/M in B) if(M.remaster_site_fetching || findtext(M.remaster_work_status, "Fetching")) fetching0++
	var/turf/ST = P.RemasterStockpile()
	for(var/n = 1, n <= 6, n++) BtxDrop(/obj/Items/ores/stone, ST)
	usr = P
	P.RemasterBlueprintTick(0)
	var/fetching = 0
	for(var/mob/Monsters/M in B) if(findtext(M.remaster_work_status, "Fetching stone from the stockpile")) fetching++
	world.log << "CK|stone on the stockpile: a builder goes for it on the very next pass|[fetching > 0 && !fetching0]|[fetching] builders fetching after one pass ([fetching0] before)"
	var/total = 0
	var/diffs = 0
	for(var/k in btx_calls) total += btx_calls[k]
	for(var/k in btx_diff) diffs += btx_diff[k]
	var/list/parts = list()
	for(var/k in btx_calls) parts += "[k] [btx_calls[k]] ([btx_diff[k]] differ)"
	world.log << "CK|every answer the same as the old code's|[!diffs && total > 1000]|[jointext(parts, ", ")]; [btx_none] looks found nothing, [btx_memo] of them from the step's memo[length(btx_notes) ? "; " + jointext(btx_notes, " | ") : ""]"
	world.log << "CK|complete"
