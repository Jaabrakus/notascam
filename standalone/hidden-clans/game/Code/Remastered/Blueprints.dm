// Building kit: blueprints and construction tasks.
// Painting a plan (3D, or 2D) with a build mode from the Build tab makes one
// construction task ("site"). Its tiles are blueprints, and the task shows what
// it still needs. Workers on it (the units selected while painting, units sent
// with the Build tab's Assign button, or villagers with the Builder job) fetch
// the material from the stockpiles, carry it over and build tile by tile with
// the original turf/MouseDrag code: same material, adjacency and Supported-sky
// rules. They take leftovers back afterwards. With no material anywhere the task
// says what is missing, posts a work order on the bulletin board and waits; it
// carries on by itself when stock arrives.
// Blueprints, tasks and the builder flags are saved with the player.

#define REMASTER_BLUEPRINT_MAX 400
#define REMASTER_BLUEPRINT_TRIES 3
#define REMASTER_SITE_DONE_KEPT 6
#define REMASTER_SITE_LOAD 5          // most pieces a worker fetches in one trip

Player/var
	list/remaster_blueprints      // saved: list of list("x","y","z","mode","note","tries","site")
	list/remaster_sites           // saved: construction tasks (RemasterSiteNew)
	remaster_site_serial = 0
Player/var/tmp/remaster_sites_had = 0
mob/Monsters/var
	remaster_builder = 0          // saved: on construction duty until no plan needs this unit
	remaster_site                 // saved: id of the construction this unit works on
	remaster_site_kept_pause = 0  // saved: the job's pause state when the duty began
mob/Monsters/var/tmp
	list/remaster_site_load       // pieces fetched for building (taken back if left over)
	remaster_site_fetching = 0
	remaster_site_standby = 0     // the task waits for material; the unit's job runs meanwhile
	remaster_site_return = 0      // carrying leftovers back to the stockpile
	turf/remaster_site_dest
	turf/remaster_site_goal
	list/remaster_site_path
	remaster_site_repath = 0
	remaster_bp_target
	remaster_bp_since = 0
	remaster_bp_seen = 0          // last tick it went on toward remaster_bp_target
	obj/Items/remaster_fetch_target
	remaster_fetch_since = 0
	remaster_fetch_seen = 0

// The painting shape (the 3D view previews it too). What a mode really makes is
// RemasterBuildShape (Construction.dm): fortress walls paint filled, so two or
// three rows side by side make one wide wall.
proc/RemasterBuildModeKind(mode)
	if(mode == "FortressWall" || mode == "Beam" || RemasterRoadMode(mode) || copytext(mode, 1, 7) == "Piece:" || RemasterIsHallMode(mode)) return "floor"
	if(copytext(mode, 1, 10) == "Workshop:") return "workshop"
	if(copytext(mode, 1, 8) == "Stairs:") return "stairs"
	if(findtext(mode, "Wall") || findtext(mode, "Spikes") || findtext(mode, "Ribcage") || mode == "PlaceStoneFall") return "wall"
	if(findtext(mode, "Floor") || mode == "DestroyFloor") return "floor"
	if(findtext(mode, "Bridge")) return "bridge"
	if(findtext(mode, "Autodig") || mode == "DigChannel") return "dig"
	return "other"

proc/RemasterBuildModeLabel(mode)
	var/list/E = RemasterBuildEntryForMode(mode)
	if(E) return copytext(mode, 1, 8) == "Stairs:" ? "[E["label"]] ([lowertext(RemasterStairsDir(mode))])" : E["label"]
	var/label = mode
	if(copytext(label, 1, 6) == "Place") label = copytext(label, 6)
	// Split CamelCase: "WoodenWall" -> "Wooden Wall"
	var/out = ""
	for(var/i = 1, i <= length(label), i++)
		var/c = copytext(label, i, i + 1)
		if(i > 1 && c == uppertext(c) && c != lowertext(c)) out += " "
		out += c
	return out

// Tiles a drag covers: floors fill the rectangle, walls follow its outline
// (a straight line when the drag is thin).
proc/RemasterPaintTiles(x0, y0, x1, y1, z, kind)
	var/list/out = list()
	var/ax = min(x0, x1); var/bx = max(x0, x1)
	var/ay = min(y0, y1); var/by = max(y0, y1)
	if((bx - ax + 1) * (by - ay + 1) > 600) return out
	for(var/ty = ay, ty <= by, ty++)
		for(var/tx = ax, tx <= bx, tx++)
			if(kind == "wall" && tx != ax && tx != bx && ty != ay && ty != by) continue
			var/turf/T = locate(tx, ty, z)
			if(T) out += T
	return out

Player/proc/RemasterBlueprintAt(turf/T)
	if(!remaster_blueprints) return null
	for(var/list/B in remaster_blueprints) if(B["x"] == T.x && B["y"] == T.y && B["z"] == T.z) return B
	return null

Player/proc/RemasterBuilderUnits()
	var/list/units = list()
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && (M in UnitList) && !M.Wagon) units += M
	return units

// paint3d value: "x0|y0|x1|y1"; uses the current build mode. The selected units
// become its workers; with nobody selected the task waits for builders.
Player/proc/RemasterPaint(value)
	var/list/p = splittext("[value]", "|")
	if(p.len != 4 || !RemasterTapPaintMode(Function))
		RemasterNotice("Choose something to place first (Place tab).")
		return 0
	var/list/units = RemasterBuilderUnits()
	var/kind = RemasterBuildModeKind(Function)
	var/list/tiles = RemasterPaintTiles(text2num(p[1]), text2num(p[2]), text2num(p[3]), text2num(p[4]), z, kind)
	if(RemasterIsHallMode(Function)) return RemasterPlanHall(text2num(p[1]), text2num(p[2]), text2num(p[3]), text2num(p[4])) // Buildings.dm
	if(Function == "Beam") tiles = RemasterBeamSpots(tiles, text2num(p[1]), text2num(p[2]), text2num(p[3]), text2num(p[4]), z)
	var/list/E = RemasterBuildEntryForMode(Function)
	// Designations and powers (dig marks, telekinesis...) need no walking: apply them now.
	if(!E || E["now"])
		if(!length(units))
			RemasterNotice("Select the units first.")
			return 0
		usr = src
		for(var/turf/T in tiles) if(RemasterMayWork(T, 1)) T.MouseDrag(T)
		return length(tiles)
	if(!remaster_blueprints) remaster_blueprints = list()
	var/list/S = RemasterSiteNew(Function, z)
	var/added = 0
	var/skipped = 0
	var/why
	var/list/undo = list()
	var/sx = 0
	var/sy = 0
	for(var/turf/T in tiles)
		if(length(remaster_blueprints) >= REMASTER_BLUEPRINT_MAX) break
		if(RemasterBlueprintAt(T)) continue
		var/blocked = RemasterBuildBlocked(T, Function)
		if(blocked || !RemasterMayWork(T, 1))
			skipped++
			why = blocked || "someone else's land"
			continue
		remaster_blueprints += list(list("x"=T.x, "y"=T.y, "z"=T.z, "mode"=Function, "note"="Waiting for a builder", "tries"=0, "site"=S["id"]))
		undo += "[T.x],[T.y],[T.z]"
		sx += T.x
		sy += T.y
		added++
	if(!added)
		remaster_sites -= list(S)
		RemasterNotice(skipped ? "Nothing to plan there: [why]." : "Those tiles are already planned.")
		return 0
	S["x"] = round(sx / added)
	S["y"] = round(sy / added)
	S["left"] = added
	S["total"] = added
	RemasterUndoPush(list("type"="blueprints", "keys"=undo))
	var/crew = RemasterSiteAssignUnits(S, units)
	var/text = "Planned [S["label"]]: [added] tile[added == 1 ? "" : "s"][skipped ? " ([skipped] skipped: [why])" : ""]. [RemasterSiteNeedText(S)]."
	if(crew) text += " [crew]"
	else text += " [RmBuildCrewHint(1)]"
	RemasterNotice(text)
	return added

// Who builds a plan nobody was selected for (the planning notices): the job board's Builders row when it wants hands, or
// villagers on the Builder job; else how to get some. The notices named only the Build tab and the Builder job, also
// when the board's Builders were about to take it up, and never the Builders row, which wants nobody until it's set.
Player/proc/RmBuildCrewHint(many = 0)
	var/list/BZ = RmJz("builders")
	if(BZ && BZ["want"] > 0 && !BZ["paused"]) return "Builders on the job board take it up."
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_job == "builder") return "Your builders take it up."
	return many ? "Set Builders on the job board (Work tab), assign workers in the Place tab, or give villagers the Builder job." : "Set Builders on the job board (Work tab), assign a worker in the Build tab, or give a villager the Builder job."

Player/proc/RemasterBlueprintCancel(value)
	if(value == "all")
		remaster_blueprints = list()
		RemasterSitesSync()
		for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_builder) M.RemasterSiteEndDuty(src)
		RemasterNotice("All blueprints cleared.")
		return 1
	var/list/p = splittext("[value]", "|")
	if(p.len != 2 || !remaster_blueprints) return 0
	for(var/list/B in remaster_blueprints.Copy()) if(B["x"] == text2num(p[1]) && B["y"] == text2num(p[2]) && B["z"] == z) remaster_blueprints -= list(B)
	return 1

// --- Construction tasks --------------------------------------------------------
Player/proc/RemasterSite(id)
	if(!id || !remaster_sites) return null
	for(var/list/S in remaster_sites) if(S["id"] == id) return S
	return null

Player/proc/RemasterSiteNew(mode, level)
	if(!remaster_sites) remaster_sites = list()
	remaster_site_serial++
	var/list/S = list("id"="c[remaster_site_serial]", "mode"=mode, "label"=RemasterBuildModeLabel(mode), "z"=level, "x"=x, "y"=y,
		"built"=0, "failed"=0, "left"=0, "total"=0, "workers"=3, "priority"=2, "posted"=RemasterLineageDate(), "note"=null, "done"=0)
	remaster_sites += list(S)
	return S

// Open tasks, most urgent first (priority, then oldest).
Player/proc/RemasterOpenSites()
	var/list/out = list()
	if(remaster_sites) for(var/priority = 1, priority <= 3, priority++)
		for(var/list/S in remaster_sites) if(!S["done"] && S["priority"] == priority) out += list(S)
	return out

Player/proc/RemasterSiteCrew(id)
	var/list/out = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_site == id) out += M
	return out

// Puts these units on the task (those whose race can build it). Returns a line for the notice.
Player/proc/RemasterSiteAssignUnits(list/S, list/units)
	var/list/names = list()
	var/list/cannot = list()
	for(var/mob/Monsters/M in units)
		if(!RemasterSiteEligible(S, M))
			cannot |= "[M.Race]"
			continue
		M.RemasterSiteJoin(src, S, 1)
		names += "[M.name]"
	if(length(names)) S["workers"] = max(S["workers"], length(RemasterSiteCrew(S["id"])))
	var/text = length(names) ? "[jointext(names, ", ")] will build it." : ""
	if(length(cannot)) text += "[length(names) ? " " : ""][jointext(cannot, ", ")] can't build [lowertext(S["label"])]."
	return text

Player/proc/RemasterSiteFinish(list/S, note)
	S["done"] = 1
	S["note"] = note
	S["finished"] = RemasterLineageDate()
	if(S["built"]) RemasterLog("Built: [S["label"]] ([S["built"]] piece[S["built"] == 1 ? "" : "s"])", "work", locate(S["x"], S["y"], S["z"]))
	if(RemasterSiteMixed(S)) RemasterBuildingFinished(S, note) // a building or lair (Buildings.dm)
	for(var/mob/Monsters/M in UnitList) if(M.remaster_site == S["id"]) M.RemasterSiteLeave(src)
	if(!S["built"] && !S["failed"] && note != "Cancelled")
		remaster_sites -= list(S) // undone before anything was built: no history
		return
	// Keep only a short history of finished tasks.
	var/list/done = list()
	for(var/list/X in remaster_sites) if(X["done"]) done += list(X)
	while(length(done) > REMASTER_SITE_DONE_KEPT)
		remaster_sites -= list(done[1])
		done.Cut(1, 2)

// Counts what each task has left; finishes empty ones. Plans from before
// construction tasks existed become one task per build mode.
Player/proc/RemasterSitesSync()
	var/list/left = list()
	var/list/older
	if(remaster_blueprints) for(var/list/B in remaster_blueprints)
		var/list/S = RemasterSite(B["site"])
		if(!S || S["done"])
			if(!older) older = list()
			S = older[B["mode"]]
			if(!S)
				S = RemasterSiteNew(B["mode"], B["z"])
				S["x"] = B["x"]
				S["y"] = B["y"]
				S["note"] = "From an earlier plan"
				older[B["mode"]] = S
			B["site"] = S["id"]
		left[S["id"]] = (left[S["id"]] || 0) + (B["then"] ? 2 : 1) // a floor with a piece to go on it
	if(remaster_sites) for(var/list/S in remaster_sites.Copy())
		if(S["done"]) continue
		var/n = left[S["id"]] || 0
		if(!n && S["ceil"]) n = length(RemasterBuildingRoofs(S))   // a high hall stays open while its ceiling is mined (Buildings.dm)
		S["left"] = n
		S["total"] = S["built"] + S["failed"] + n
		if(!n) RemasterSiteFinish(S, S["built"] ? "Finished: [S["built"]] built[S["failed"] ? ", [S["failed"]] couldn't be built" : ""]" : (S["failed"] ? "Couldn't be built" : "Plan removed"))
	// Units on duty for a task that no longer exists (undo, cancel) step off it.
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_site)
		var/list/S = RemasterSite(M.remaster_site)
		if(!S || S["done"]) M.RemasterSiteLeave(src)

// Pieces of this task other than B still to build.
Player/proc/RemasterSiteOthersLeft(list/S, list/B)
	if(remaster_blueprints) for(var/list/X in remaster_blueprints) if(X != B && X["site"] == S["id"]) return 1
	return 0

Player/proc/RemasterSiteDrop(list/S, list/B, why)
	remaster_blueprints -= list(B)
	S["failed"] += (B["then"] ? 2 : 1)
	S["left"] = max(0, S["left"] - (B["then"] ? 2 : 1))
	S["note"] = "Skipped a tile at [B["x"]], [B["y"]]: [why]"
	RemasterLog("[S["label"]]: skipped a tile ([why])", "problem", locate(B["x"], B["y"], B["z"]))

// --- Workers -----------------------------------------------------------------
mob/Monsters/proc/RemasterSiteStatus(text)
	remaster_work_status = text
	remaster_order_status = text

// Walk to T by a path round walls and water (Orders.dm's search, which keeps off
// stairs unless they are the goal), a step at a time as move orders do.
mob/Monsters/proc/RemasterSiteWalk(turf/T)
	if(!T) return
	if(T != remaster_site_goal)
		remaster_site_goal = T
		remaster_site_path = null
		remaster_site_repath = 0
		remaster_site_noway = 0
	while(length(remaster_site_path) && remaster_site_path[1] == loc) remaster_site_path.Cut(1, 2)
	if((!length(remaster_site_path) || !RemasterStepOpen(remaster_site_path, src, T)) && world.time >= remaster_site_repath)
		if(rm_nav_count) rm_path_who = "building site"
		remaster_site_path = RemasterOrderPath(src, T, 0, partial = 1)
		remaster_site_noway = rm_path_partial == 2   // no way there (a ledge, water): the site card says so at once (rts-feel)
		remaster_site_repath = world.time + 20
	var/turf/next = length(remaster_site_path) ? remaster_site_path[1] : T
	if(destination != next) destination = next
	remaster_site_dest = next

// Settlement jobs and the board leave this unit to construction.
mob/Monsters/proc/RemasterOnConstruction()
	if(remaster_site_return || remaster_job == "builder") return 1
	return remaster_builder && remaster_site && !remaster_site_standby

// Not free to build right now: asleep, eating, fighting, or doing a direct order
// (those come first). A job's own automatic task is not in the way.
mob/Monsters/proc/RemasterSiteBusy()
	if(HP <= 0 || GoingToDie || Sleeping || Fainted || Stunned || !isturf(loc)) return 1
	if(remaster_care || remaster_defense || remaster_delivery || remaster_paused || remaster_wait_for_resume) return 1
	if(remaster_active && !remaster_active.automatic) return 1
	if(length(remaster_orders)) return 1
	return 0

mob/Monsters/proc/RemasterSiteTakeOver()
	if(remaster_active && remaster_active.automatic) RemasterCancelOrders()
	if(remaster_work_destination) RemasterStopWork()
	if(remaster_board_claim) RemasterBoardRelease()

mob/Monsters/proc/RemasterSiteJoin(Player/P, list/S, direct)
	if(direct && !remaster_builder && remaster_job != "builder")
		remaster_builder = 1
		remaster_site_kept_pause = remaster_role_paused
	if(remaster_site == S["id"]) return
	var/list/old = P.RemasterSite(remaster_site)
	if(old) RemasterSiteLeave(P, S)
	remaster_site = S["id"]
	remaster_bp_target = null
	remaster_site_fetching = 0
	remaster_site_standby = 0
	if(remaster_board_claim) RemasterBoardRelease()

// Leaves the current task. Leftover pieces go back to the stockpile, unless
// the next task (next) uses the same material.
mob/Monsters/proc/RemasterSiteLeave(Player/P, list/next)
	var/list/old = P.RemasterSite(remaster_site)
	remaster_site = null
	remaster_bp_target = null
	remaster_fetch_target = null
	remaster_site_fetching = 0
	remaster_site_standby = 0
	if(remaster_site_dest && destination == remaster_site_dest) destination = null
	remaster_site_dest = null
	remaster_site_goal = null
	remaster_site_path = null
	var/kept = old ? RemasterBuildMaterial(old["mode"]) : null
	if(old && next && kept && kept == RemasterBuildMaterial(next["mode"])) return
	if(length(RemasterSiteLeftovers())) remaster_site_return = 1
	else remaster_site_load = null

// No more plans for this unit: its job carries on as before.
mob/Monsters/proc/RemasterSiteEndDuty(Player/P)
	if(remaster_site) RemasterSiteLeave(P)
	if(!remaster_builder) return
	remaster_builder = 0
	remaster_role_paused = remaster_site_kept_pause
	remaster_site_kept_pause = 0
	if(!remaster_site_return) RemasterSiteStatus(remaster_job == "manual" ? "Idle" : "Back to work")

mob/Monsters/proc/RemasterSiteLeftovers()
	var/list/out = list()
	if(remaster_site_load) for(var/obj/Items/I in remaster_site_load) if(I.loc == src) out += I
	return out

mob/Monsters/proc/RemasterCarriedCount(path)
	if(!path) return 0
	var/n = 0
	// Furniture counts only when fetched for building: never a unit's own sleeping bag.
	var/own = RemasterFurniturePath(path)
	for(var/obj/Items/I in src) if(istype(I, path) && I.suffix != "(Equipped)" && (!own || (I in remaster_site_load))) n++
	return n

// Where leftovers go: the main stockpile when it takes them, a zone that does,
// or the main stockpile anyway (they came from there).
Player/proc/RemasterStoreFor(obj/Items/I, level)
	var/turf/S = RemasterStockpile()
	if(S && S.z == level && !S.density && RemasterStockAccepts(I)) return S
	if(remaster_zones) for(var/list/Z in remaster_zones)
		var/turf/T = RemasterZoneTurf(Z)
		if(T && T.z == level && !T.density && RemasterZoneAccepts(Z, I)) return T
	if(S && S.z == level && !S.density) return S
	return null

mob/Monsters/proc/RemasterSiteReturnTick(Player/P)
	var/list/L = RemasterSiteLeftovers()
	if(!length(L))
		remaster_site_return = 0
		remaster_site_load = null
		return
	var/obj/Items/first = L[1]
	var/kind = RemasterMaterialKind(first.type)
	var/turf/S = P.RemasterStoreFor(first, z)
	if(!S)
		remaster_site_return = 0
		remaster_site_load = null
		RemasterSiteStatus("Kept [length(L)] leftover [kind]: no stockpile on this layer")
		return
	if(get_dist(src, S) > 1)
		var/key = "return [S.x],[S.y],[S.z]"
		if(remaster_bp_target != key || world.time - remaster_bp_seen > 50)   // a clock only while it keeps at it
			remaster_bp_target = key
			remaster_bp_since = world.time
		remaster_bp_seen = world.time
		if(world.time - remaster_bp_since > 600)
			remaster_site_return = 0
			remaster_site_load = null
			remaster_bp_target = null
			RemasterSiteStatus("Couldn't reach the stockpile; kept the leftover [kind]")
			return
		RemasterSiteWalk(S)
		RemasterSiteStatus("Taking [length(L)] leftover [kind] back to the stockpile")
		return
	if(remaster_site_dest && destination == remaster_site_dest) destination = null
	var/n = 0
	for(var/obj/Items/I in L) if(DropItem(I) && I)
		I.loc = S
		I.Owner = P
		n++
	remaster_site_return = 0
	remaster_site_load = null
	remaster_bp_target = null
	RemasterSiteStatus("Returned [n] leftover [kind] to the stockpile")

// The task this unit should work on: its own while it can, otherwise the most
// urgent one on its layer with room for another worker, preferring tasks whose
// material is at hand.
Player/proc/RemasterSiteFor(mob/Monsters/M, list/claims)
	var/list/cur = RemasterSite(M.remaster_site)
	if(cur && (cur["done"] || !RemasterSiteReach(cur, M) || cur["id"] == M.remaster_site_skip || !RemasterSiteEligible(cur, M))) cur = null
	if(cur && RemasterSiteReady(cur, M)) return cur
	var/list/best
	var/best_score = 1#INF
	var/list/wait          // none ready: the one it would take, to wait at (below)
	var/wait_score = 1#INF
	for(var/list/S in RemasterOpenSites())
		if(S == cur || S["id"] == M.remaster_site_skip || !RemasterSiteEligible(S, M) || !RemasterSiteReach(S, M)) continue
		if((claims[S["id"]] || 0) >= S["workers"]) continue
		var/score = S["priority"] * 1000 + get_dist(M, locate(S["x"], S["y"], S["z"]))
		if(!RemasterSiteReady(S, M))
			if(score < wait_score)
				wait = S
				wait_score = score
			continue
		if(score < best_score)
			best = S
			best_score = score
	// With nothing ready anywhere, a builder still takes a site and waits at it: there it says what the site lacks and the
	// site posts its order for it (RemasterSiteWork, RemasterSiteMissing). Taking only ready sites, a builder with none
	// stood wherever it was (often on the stockpile) as "no construction this unit can work on here", and a site no
	// builder had joined never asked for its stone: a dwarven hall waited 29 minutes with nothing on the board for it.
	return best || cur || wait

// On the task's level, or stairs within reach lead there.
Player/proc/RemasterSiteReach(list/S, mob/Monsters/M)
	if(S["z"] == M.z) return 1
	var/turf/goal = locate(S["x"], S["y"], S["z"])
	return goal && RemasterStairsTowards(M, goal)

proc/RemasterFlatDist(atom/A, atom/B)
	return max(abs(A.x - B.x), abs(A.y - B.y))

// Has the material (or needs none) for some piece it may build. A building's
// task holds several kinds of piece; the others hold one.
Player/proc/RemasterSiteReady(list/S, mob/Monsters/M)
	if(S["ceil"] && length(RemasterBuildingRoofs(S))) return 1   // a high hall's ceiling: needs no material (Buildings.dm)
	for(var/mode in RemasterSiteModes(S))
		if(!RemasterBuildEligible(mode, M) || M.RemasterSiteBodyNeed(mode)) continue
		var/path = RemasterBuildMaterial(mode)
		if(!path || !RmSiteNeedsAny(S, path) || M.RemasterCarriedCount(path) || RemasterSiteSource(S, path, M)) return 1
	return 0

// RemasterSiteNeedCount(S, path) > 0, stopping at the first piece that uses the material (every piece's need is 0 or more).
Player/proc/RmSiteNeedsAny(list/S, path)
	if(remaster_blueprints) for(var/list/B in remaster_blueprints) if(B["site"] == S["id"])
		for(var/mode in B["then"] ? list(B["mode"], B["then"]) : list(B["mode"]))
			if(path && RemasterBuildMaterial(mode) != path) continue
			if(RemasterBlueprintNeed(mode, locate(B["x"], B["y"], B["z"]))) return 1
	return 0

// The nearest piece of this material for this worker: on a stockpile or zone of
// the task's layer, or lying loose within 12 tiles.
Player/var/tmp/mob/Monsters/rm_bp_unit   // the builder whose step (RmBlueprintUnit) this is: its "none"s hold all step
Player/var/tmp/list/rm_bp_none           // "layer|material" -> 1: nothing of it for rm_bp_unit this step

Player/proc/RemasterSiteSource(list/S, path, mob/Monsters/M)
	var/memo = M == rm_bp_unit ? "[S["z"]]|[path]" : null   // the answer depends on the layer and material only
	if(memo && rm_bp_none && rm_bp_none[memo]) return null
	var/obj/Items/best
	var/best_d = 1#INF
	for(var/turf/T in RemasterStores())
		if(T.z != S["z"]) continue
		for(var/obj/Items/I in range(1, T))
			if(!istype(I, path) || !isturf(I.loc) || !RemasterMayCollect(I) || RemasterUnreachable(I) || I.remaster_placed) continue
			var/d = RemasterFlatDist(M, I)
			if(d < best_d)
				best = I
				best_d = d
	// Furniture comes from the stockpiles only: a bed lying about may be someone's.
	if(M.z == S["z"] && !RemasterFurniturePath(path)) for(var/obj/Items/I in range(12, M))
		if(!istype(I, path) || !isturf(I.loc) || !RemasterMayCollect(I) || RemasterUnreachable(I)) continue
		var/d = get_dist(M, I)
		if(d < best_d)
			best = I
			best_d = d
	if(!best && memo)
		if(!rm_bp_none) rm_bp_none = list()
		rm_bp_none[memo] = 1
	return best

// How many pieces this worker fetches: what the task still needs minus what its
// other workers already carry, at most REMASTER_SITE_LOAD. Floors only need one
// piece in the bag (the original floor code doesn't use it up).
Player/proc/RemasterSiteWant(list/S, mob/Monsters/M, path)
	if(!path) path = RemasterBuildMaterial(S["mode"])
	if(!RemasterBuildUses(S["mode"]) && !RemasterSiteMixed(S)) return 1
	var/need = RemasterSiteNeedCount(S, path)
	for(var/mob/Monsters/W in UnitList) if(W != M && W.Owner == src && W.remaster_site == S["id"]) need -= W.RemasterCarriedCount(path)
	// a piece that takes several at once (a ramp: 3 stone) is fetched whole
	var/most = 0
	for(var/list/B in remaster_blueprints) if(B["site"] == S["id"] && RemasterBuildMaterial(B["mode"]) == path) most = max(most, RemasterBlueprintNeed(B["mode"], locate(B["x"], B["y"], B["z"])))
	// furniture is heavy: one piece a trip
	if(RemasterFurniturePath(path)) return 1
	return max(most, clamp(need, 1, REMASTER_SITE_LOAD))

// The next tile for this worker: floors and bridges first, workshops next,
// walls last, so a room is never walled shut before its floor is laid; and one
// no other worker is on. A worker keeps the tile it is on until it is built.
// Floors go nearest first; walls farthest from the stockpile first, so a wall
// two or three rows thick is laid from the back row forward and no row ends up
// behind a finished one (units walk straight at their goal).
Player/proc/RemasterSiteNextTile(list/S, mob/Monsters/M)
	var/list/taken = list()
	for(var/mob/Monsters/W in UnitList) if(W != M && W.remaster_site == S["id"] && W.remaster_bp_target) taken[W.remaster_bp_target] = 1
	var/turf/stock = RemasterStockpile()
	var/atom/from = (stock && stock.z == S["z"]) ? stock : M
	var/list/best
	var/best_score = 1#INF
	var/wait
	// A building's pieces: only those this unit may build, and while some material
	// is at hand, the pieces it is for (the rest wait their turn, not the builder).
	var/mixed = RemasterSiteMixed(S)
	var/list/have = list()
	var/list/short
	var/dig = mixed ? RemasterBuildingDigWait(S) : null
	for(var/list/B in remaster_blueprints)
		if(B["site"] != S["id"]) continue
		var/turf/T = locate(B["x"], B["y"], B["z"])
		if(!T) continue
		if(mixed && !RemasterBuildEligible(B["mode"], M)) continue
		var/why = dig || RemasterBuildWait(T, B["mode"], M)
		// A building's door is hung last: a shut door keeps its own builders out (the
		// original doors open only when the player opens them).
		if(!why && mixed && RemasterBuildShape(B["mode"]) == "gate" && RemasterSiteOthersLeft(S, B)) why = "The door goes in last, once everything else is in"
		if(why)
			B["note"] = why
			wait = why
			continue
		var/key = "[B["x"]],[B["y"]],[B["z"]]"
		if(M.remaster_bp_target == key) return B
		var/score = RemasterBlueprintRank(B["mode"]) * 10000 + (RemasterBuildShape(B["mode"]) == "wall" ? 1000 - RemasterFlatDist(from, T) : RemasterFlatDist(M, T)) + (taken[key] ? 500 : 0)
		if(mixed)
			var/path = RemasterBuildMaterial(B["mode"])
			if(path && RemasterBlueprintNeed(B["mode"], T))
				if(isnull(have[path])) have[path] = (M.RemasterCarriedCount(path) || RemasterSiteSource(S, path, M)) ? 1 : 0
				if(!have[path])
					if(!short || score < short[2]) short = list(B, score)
					continue
		if(score < best_score)
			best = B
			best_score = score
	if(!best && short) best = short[1] // nothing at hand for any piece: report what's missing
	if(!best && wait) S["note"] = "Waiting: [lowertext(copytext(wait, 1, 2))][copytext(wait, 2)]"
	return best

Player/proc/RemasterSiteMissing(list/S, path)
	var/kind = RemasterMaterialKind(path)
	S["note"] = RemasterFurniturePath(path) || kind == "door" ? "Needs a [kind]: make one at a carpentry and put it on a stockpile" : "Needs [kind]: none in the stockpiles or nearby"
	for(var/list/B in remaster_blueprints) if(B["site"] == S["id"]) B["note"] = S["note"]
	if(!(kind in list("wood", "stone"))) return
	if(remaster_board_orders) for(var/list/O in remaster_board_orders) if(!O["done"] && O["standing"] == "build-[kind]") return
	var/need = 0
	for(var/list/X in RemasterOpenSites()) need += RemasterSiteNeedCount(X, path)
	var/list/O = RemasterBoardPost(kind, min(20, max(1, need)), 1, 2, null, null, "build-[kind]")
	if(O)
		O["label"] = "[kind == "wood" ? "Chop wood" : "Mine stone"] for building: [O["amount"]]"
		RemasterNotice("Building needs [kind]: posted a work order on the bulletin board.")

// A worker with nothing to do yet on a building waits in the middle of it, not in its doorway
// or the tunnel to it, where it would stand in the way of whoever brings the next piece.
mob/Monsters/proc/RemasterSiteWaitAside(list/S)
	if(!RemasterSiteMixed(S)) return
	var/turf/C = locate(S["x"], S["y"], S["z"])
	if(C && C.z == z && get_dist(src, C) > 2) RemasterSiteWalk(C)
	else if(isturf(loc) && istype(Owner, /Player) && Owner:RemasterSitePlanned(S, loc))
		// Never wait on a tile still to be built: in a hall's one doorway (the door's own tile) that shut out the
		// worker bringing the last piece, and the piece was given up after three tries. Step to the nearest free
		// tile towards the site's centre, preferring one that is not a corridor (it would block the way in).
		var/Player/P = Owner
		var/turf/best
		var/best_score
		for(var/turf/T in orange(2, src))
			if(T.density || (locate(/mob/Monsters) in T) || P.RemasterSitePlanned(S, T)) continue
			var/blocked = 0
			for(var/atom/movable/A in T) if(A.density)
				blocked = 1
				break
			if(blocked) continue
			var/score = (RemasterOpenSides(T) < 3 ? 100 : 0) + get_dist(src, T) + (C ? get_dist(T, C) : 0)
			if(isnull(best_score) || score < best_score)
				best = T
				best_score = score
		if(best) RemasterSiteWalk(best)

Player/proc/RemasterSitePlanned(list/S, turf/T)
	if(remaster_blueprints) for(var/list/B in remaster_blueprints)
		if(B["site"] == S["id"] && B["x"] == T.x && B["y"] == T.y && B["z"] == T.z) return 1
	return 0

proc/RemasterOpenSides(turf/T)
	. = 0
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/N = get_step(T, d)
		if(N && !N.density) .++



mob/Monsters/proc/RemasterSiteWork(Player/P, list/S)
	if(z != S["z"])
		// The task is on another level, or the original stairs carried this unit off on
		// its way (whoever steps on stairs changes level): take the nearest stairs there.
		var/turf/ST = RemasterStairsTowards(src, locate(S["x"], S["y"], S["z"]))
		if(!ST)
			remaster_site_standby = 1
			RemasterSiteStatus("[S["label"]] is on another level and no stairs lead there")
			return
		remaster_site_standby = 0
		RemasterSiteTakeOver()
		if(loc == ST)
			var/turf/off = RemasterBuildSpot(ST, src) // standing on the stairs it came by: step off, then on
			if(off) RemasterSiteWalk(off)
		else RemasterSiteWalk(ST)
		RemasterSiteStatus("Taking the stairs to [lowertext(S["label"])]")
		return
	var/list/B = P.RemasterSiteNextTile(S, src)
	if(!B)
		remaster_site_standby = 1
		if(RemasterSiteMixed(S)) P.RemasterBuildingDigTick(S, src) // a lair's rock: dig it out first
		if(remaster_site_standby && !length(P.RemasterBuildingRock(S)) && !length(P.RemasterBuildingRoofs(S))) RemasterSiteWaitAside(S)   // nothing to dig or mine
		RemasterSiteStatus("[S["label"]]: [S["note"] || "waiting"]")
		return
	var/mode = B["mode"]
	var/path = RemasterBuildMaterial(mode)
	var/kind = RemasterMaterialKind(path)
	var/carried = RemasterCarriedCount(path)
	var/need_now = RemasterBlueprintNeed(mode, locate(B["x"], B["y"], B["z"]))
	if(need_now && (carried < need_now || (remaster_site_fetching && carried < P.RemasterSiteWant(S, src, path))))
		var/obj/Items/I = P.RemasterSiteSource(S, path, src)
		if(I)
			remaster_site_standby = 0
			RemasterSiteTakeOver()
			RemasterSiteFetch(P, S, path, I)
			return
		remaster_site_fetching = 0
		if(carried < need_now)
			remaster_site_standby = 1
			RemasterSiteWaitAside(S)
			P.RemasterSiteMissing(S, path)
			RemasterSiteStatus("Waiting for [kind] for [lowertext(S["label"])]: none in the stockpiles")
			return
	var/need = RemasterSiteBodyNeed(mode)
	if(need)
		remaster_site_standby = 1
		B["note"] = need
		RemasterSiteStatus("[S["label"]]: [need]")
		return
	if(RemasterBuildCat(mode) == "traps" && ("Trap" in CoolDowns))
		RemasterSiteStatus("Setting the next trap in a moment")
		return
	remaster_site_standby = 0
	RemasterSiteTakeOver()
	RemasterSiteBuild(P, S, B)

mob/Monsters/proc/RemasterSiteFetch(Player/P, list/S, path, obj/Items/I)
	var/kind = RemasterMaterialKind(path)
	var/want = P.RemasterSiteWant(S, src, path)
	if(get_dist(src, I) > 1)
		if(remaster_fetch_target != I || world.time - remaster_fetch_seen > 50)   // the clock runs only while it keeps going for this
			remaster_fetch_target = I
			remaster_fetch_since = world.time
		remaster_fetch_seen = world.time
		if(world.time - remaster_fetch_since > 300)
			// 30 seconds without reaching it: blocked by water or walls.
			P.RemasterMarkUnreachable(I)
			remaster_fetch_target = null
			S["note"] = "[RemasterBareName()] couldn't reach that [kind]; looking for another pile"
			return
		RemasterSiteWalk(I.loc)
		remaster_site_fetching = 1
		var/from = RemasterOnStore(I) ? "the stockpile" : "a pile nearby"
		S["note"] = "[RemasterBareName()] is fetching [kind] from [from]"
		RemasterSiteStatus("Fetching [kind] from [from] for [lowertext(S["label"])]")
		return
	remaster_fetch_target = null
	if(remaster_site_dest && destination == remaster_site_dest) destination = null
	var/carried = RemasterCarriedCount(path)
	var/taken = 0
	for(var/obj/Items/X in range(1, src))
		if(carried + taken >= want) break
		if(!istype(X, path) || !isturf(X.loc) || !P.RemasterMayCollect(X)) continue
		if(X.weight + weight > weightmax) break
		if(PickUpItem(X))
			X.Owner = P
			if(!remaster_site_load) remaster_site_load = list()
			remaster_site_load += X
			taken++
	remaster_site_fetching = taken && carried + taken < want
	if(!taken && !carried)
		remaster_site_standby = 1
		S["note"] = "[RemasterBareName()] can't carry the [kind]: bag too heavy"
	RemasterSiteStatus(taken ? "Picked up [taken] [kind] for [lowertext(S["label"])]" : "Can't carry more [kind]")

mob/Monsters/proc/RemasterSiteBuild(Player/P, list/S, list/B)
	var/mode = B["mode"]
	var/turf/T = locate(B["x"], B["y"], B["z"])
	var/kind = RemasterBuildShape(mode)
	var/stand_on = kind in list("workshop", "stairs", "gate")
	var/key = "[B["x"]],[B["y"]],[B["z"]]"
	if(remaster_bp_target != key || world.time - remaster_bp_seen > 50)   // the clock runs only while it keeps at this piece
		remaster_bp_target = key
		remaster_bp_since = world.time
	remaster_bp_seen = world.time
	if(world.time - remaster_bp_since > (remaster_site_noway ? 100 : 600))
		// A minute without building it (10 s when the path search found no way at all): unreachable from here (water, walls).
		remaster_bp_since = world.time
		B["tries"]++
		B["note"] = "[name] can't reach this spot"
		if(B["tries"] >= REMASTER_BLUEPRINT_TRIES) P.RemasterSiteDrop(S, B, "nobody could reach it")
		return
	// Never wall in the builder: walls and traps are built from the tile beside.
	var/ready = stand_on ? loc == T : (get_dist(src, T) <= 1 && (loc != T || (kind in list("floor", "bridge", "ramp", "road", "beam"))))
	if(!ready)
		// one of ours on the very tile steps off it: one waiting there (a doorway), or one just standing there with nothing
		// to do; one busy there is named on the card (it silently blocked the builder: playtest r7) (rts-feel)
		var/mob/Monsters/inway
		if(stand_on) for(var/mob/Monsters/X in T) if(X != src && X.Owner == P && X.HP > 0)
			if(X.remaster_site_standby || !X.RemasterHasOrder())
				var/turf/O = RemasterBuildSpot(T, X)
				if(O) step_to(X, O, 0)
			if(X.loc == T) inway = X
		var/turf/W = stand_on ? T : RemasterBuildSpot(T, src)
		if(!W)
			B["note"] = "No free tile beside it to build from"
			RemasterSiteStatus("[S["label"]]: no free tile beside it to build from")
			return
		RemasterSiteWalk(W)
		if(inway)
			B["note"] = "[inway.name] is in the way"
			S["note"] = "[inway.RemasterBareName()] is standing on the spot: move them so [RemasterBareName()] can build"
			RemasterSiteStatus("[S["label"]]: [inway.RemasterBareName()] is in the way")
			return
		if(remaster_site_noway)
			B["note"] = "[name] can't reach this spot: no way there"
			S["note"] = "[RemasterBareName()] can't reach the site: no way there"
			RemasterSiteStatus("[S["label"]]: no way to reach the site")
			return
		B["note"] = "[name] is walking over"
		S["note"] = "[RemasterBareName()] is building"
		RemasterSiteStatus("Building [lowertext(S["label"])] ([S["built"]]/[S["total"]])")
		return
	if(remaster_site_dest && destination == remaster_site_dest) destination = null
	// The original build code pauses the unit's job and holds off its self-care,
	// as for a manual order. Here building is the job: keep both as they were.
	var/paused = remaster_role_paused
	var/hold = remaster_care_hold
	var/ok
	if(kind == "workshop") ok = P.RemasterBuildWorkshop(src, T, copytext(mode, 10))
	else if(kind == "stairs") ok = P.RemasterBuildStairs(src, T, mode)
	else if(kind == "gate") ok = P.RemasterBuildGate(src, T)
	else if(kind == "ramp") ok = P.RemasterBuildWallPiece(src, T, mode)
	else if(kind == "road") ok = P.RemasterBuildRoad(src, T, mode)
	else if(kind == "beam") ok = P.RemasterBuildBeam(src, T)
	else if(kind == "piece") ok = P.RemasterBuildPiece(src, T, mode)    // furniture, webs, a hoard (Buildings.dm)
	else ok = P.RemasterBuildNow(src, T, mode)
	remaster_role_paused = paused
	remaster_care_hold = hold
	if(ok)
		if(kind == "stairs")
			// The stairs carried the builder to their top: step off so they don't block them.
			var/turf/off = RemasterBuildSpot(loc, src)
			if(off) step_towards(src, off)
		// A building's floor under its furniture, workshop or door: that piece is next on the tile.
		if(B["then"])
			B["mode"] = B["then"]
			B["then"] = null
			B["tries"] = 0
			B["note"] = "Waiting for a builder"
		else P.remaster_blueprints -= list(B)
		S["built"]++
		rm_g3_built = T   // the 3D view hammers at it (Gear3D.dm RmG3Work)
		S["left"] = max(0, S["left"] - 1)
		S["note"] = "[RemasterBareName()] is building"
		remaster_bp_target = null
		RemasterSiteStatus("Building [lowertext(S["label"])] ([S["built"]]/[S["total"]])")
	else
		B["tries"]++
		var/why = P.RemasterBuildFailReason(src, T, mode)
		B["note"] = why
		S["note"] = why
		if(B["tries"] >= REMASTER_BLUEPRINT_TRIES) P.RemasterSiteDrop(S, B, lowertext(why))

Player/proc/RemasterBlueprintTick(spread = 0)
	RemasterSitesSync()
	RemasterGhostsTick()
	var/list/claims = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_site) claims[M.remaster_site] = (claims[M.remaster_site] || 0) + 1
	var/open = length(RemasterOpenSites())
	var/rm_n = 0   // units since the last safe point (Spread.dm)
	for(var/mob/Monsters/M in UnitList)
		RmBlueprintUnit(M, claims, open)
		if(spread && ++rm_n >= 16)   // a safe point every 16 units (Spread.dm compiles after this file)
			rm_n = 0
			RmTrackPause()
	if(remaster_sites_had && !open) RemasterNotice("All planned building is done.")
	remaster_sites_had = open
	RemasterLairTick() // what lairs do for the rare races (Buildings.dm)

// Builds one blueprint with the original build code, as if this unit alone
// were selected and the player clicked the tile in that build mode.
Player/proc/RemasterBuildNow(mob/Monsters/M, turf/T, mode)
	if(!RemasterMayWork(T)) return 0
	var/list/old_selected = Selected
	var/old_function = Function
	var/before = "[T.icon_state]|[T.density]|[T.type]|[RemasterTrapCount(T)]"
	Selected = list(M)
	Function = mode == "FortressWall" ? "PlaceStoneWall" : mode
	usr = src
	try
		T.MouseDrag(T)
	catch(var/exception/E)
		world.log << "Remastered: build failed at [T.x],[T.y]: [E]"
	Selected = old_selected
	Function = old_function
	return "[T.icon_state]|[T.density]|[T.type]|[RemasterTrapCount(T)]" != before

proc/RemasterTrapCount(turf/T)
	var/n = 0
	for(var/obj/Items/Traps/X in T) n++
	return n

// For the 3D view: each planned tile, its ghost shape, the original sprite it
// will become ("tex", a browse_rsc picture, to draw faded and flat) and its
// task's state (working, waiting for material, or no workers yet).
Player/proc/RemasterBlueprintData()
	var/list/out = list()
	var/list/states = list()
	if(remaster_blueprints) for(var/list/B in remaster_blueprints) if(B["z"] == z && abs(B["x"] - x) <= 25 && abs(B["y"] - y) <= 20)
		var/id = B["site"] || "none"
		if(isnull(states[id]))
			var/state = "unassigned"
			for(var/mob/Monsters/M in RemasterSiteCrew(id))
				if(!M.remaster_site_standby)
					state = "working"
					break
				state = "waiting"
			states[id] = state
		var/list/E = RemasterBuildEntryForMode(B["mode"])
		out += list(list("x"=B["x"], "y"=B["y"], "kind"=RemasterGhostKind(B["mode"]), "note"=B["note"], "site"=id, "state"=states[id], "tex"=(E ? RemasterBuildIcon(E) : "")))
	return out

// The 3D ghost shape: workshops take two tiles; stairs, channels and traps lie flat.
proc/RemasterGhostKind(mode)
	var/kind = RemasterBuildShape(mode)
	if(kind in list("stairs", "ramp", "gate", "road", "beam", "piece")) return "floor"
	if(mode == "DigChannel") return "floor"
	var/list/E = RemasterBuildEntryForMode(mode)
	if(E && E["cat"] == "traps") return "floor"
	if(kind == "workshop" && ((copytext(mode, 10) in list("campfire", "cauldron", "stall", "foodpot", "foodstall", "clinic", "surgery", "graveyard", "tavern", "notice")) || RemasterIsRune(copytext(mode, 10)))) return "floor"
	return kind

// A free tile right next to the blueprint (never the blueprint tile itself,
// so a builder is not walled in by their own wall).
proc/RemasterBuildSpot(turf/T, mob/M)
	var/turf/best
	var/best_d = 1#INF
	for(var/turf/S in orange(1, T))
		if(S.density) continue
		var/blocked = 0
		for(var/atom/movable/O in S) if(O.density && O != M)
			blocked = 1
			break
		if(blocked) continue
		var/d = get_dist(S, M)
		if(d < best_d)
			best = S
			best_d = d
	return best

// --- Workshops placed with the ghost ---------------------------------------
// id, label, original create proc, material type
proc/RemasterWorkshopDefs()
	return list(
		"carpentry"=list("Carpentry", "CreateCarpentry", /obj/Items/woods/wood),
		"kitchen"=list("Kitchen", "CreateKit", /obj/Items/woods/wood),
		"leather"=list("Leatherworks", "CreateWorkShopLeather", /obj/Items/woods/wood),
		"bone"=list("Bone crafting", "CreateBone", /obj/Items/woods/wood),
		"poison"=list("Poison station", "CreatePoison", /obj/Items/woods/wood),
		"potion"=list("Potion station", "CreatePotion", /obj/Items/woods/wood),
		"forge"=list("Forge", "CreateForge", /obj/Items/ores/stone),
		"smelter"=list("Smelter", "CreateSmelter", /obj/Items/ores/stone),
		"masonry"=list("Masonry", "CreateMasonary", /obj/Items/ores/stone),
		"gem"=list("Gem cutter", "CreateGem", /obj/Items/ores/stone),
		"melter"=list("Melter", "CreateMelter", /obj/Items/ores/stone),
		"campfire"=list("Campfire", null, /obj/Items/woods/wood),
		"cauldron"=list("Cauldron", null, /obj/Items/ores/stone),
		"altar"=list("Good altar", null, /obj/Items/ores/stone),   // with silver and gold (HalfDemons.dm)
		// Rune circuits (Runes.dm): built on the tile the builder stands on.
		"rune"=list("Rune line", null, null),
		"crystal"=list("Mana crystal", null, /obj/Items/gems),
		"runedoor"=list("Rune door", null, /obj/Items/ores/stone),
		"firejet"=list("Fire jet", null, /obj/Items/ores/stone),
		"spikes"=list("Spike trap", null, /obj/Items/ores/stone),
		"plate"=list("Pressure plate", null, /obj/Items/ores/stone),
		"lever"=list("Lever", null, /obj/Items/woods/wood),
		"lamp"=list("Rune lamp", null, /obj/Items/ores/stone),
		"bell"=list("Alarm bell", null, /obj/Items/ores/stone),
		"banner"=list("Claim banner", null, /obj/Items/woods/wood),
		"stall"=list("Market stall", null, /obj/Items/woods/wood),
		"notice"=list("Notice board", null, /obj/Items/woods/wood),   // player-made quests (Quests.dm)
		// Where villagers eat (FoodSupply.dm).
		"foodpot"=list("Food pot", null, /obj/Items/ores/stone),
		"foodstall"=list("Food stall", null, /obj/Items/woods/wood),
		"clinic"=list("Doctor's stall", null, /obj/Items/woods/wood),   // Doctor.dm
		"surgery"=list("Operating table", null, /obj/Items/woods/wood),   // Surgery.dm
		"graveyard"=list("Graveyard", null, /obj/Items/ores/stone),       // Graves.dm
		"tavern"=list("Tavern", null, /obj/Items/woods/wood))             // Tavern.dm

// The item a blueprint uses up (null = none, or the unit's own web or flesh).
proc/RemasterBuildMaterial(mode)
	if(copytext(mode, 1, 10) == "Workshop:")
		var/list/D = RemasterWorkshopDefs()[copytext(mode, 10)]
		return D ? D[3] : null
	var/list/E = RemasterBuildEntryForMode(mode)
	if(E) return RemasterMaterialPath(E["mat"])
	if(findtext(mode, "Wooden") || findtext(mode, "Tribal")) return /obj/Items/woods/wood
	if(findtext(mode, "Stone")) return /obj/Items/ores/stone
	if(findtext(mode, "Bone") || findtext(mode, "Rib")) return /obj/Items/Bones/Bones
	return null

proc/RemasterMaterialPath(mat)
	switch(mat)
		if("door") return /obj/Items/Furniture/Doors
		if("wood") return /obj/Items/woods/wood
		if("stone") return /obj/Items/ores/stone
		if("bones") return /obj/Items/Bones/Bones
		if("gem") return /obj/Items/gems
		if("bed") return /obj/Items/Furniture/Beds
		if("table") return /obj/Items/Furniture/Tables
		if("chair") return /obj/Items/Furniture/Chairs
	return null

proc/RemasterMaterialKind(path)
	if(ispath(path, /obj/Items/woods/wood)) return "wood"
	if(ispath(path, /obj/Items/ores/stone)) return "stone"
	if(ispath(path, /obj/Items/Bones)) return "bones"
	if(ispath(path, /obj/Items/gems)) return "gems"
	if(ispath(path, /obj/Items/Furniture/Doors)) return "door"
	if(ispath(path, /obj/Items/Furniture/Beds)) return "bed"
	if(ispath(path, /obj/Items/Furniture/Tables)) return "table"
	if(ispath(path, /obj/Items/Furniture/Chairs)) return "chair"
	return "material"

// placeworkshop value: "id|x|y" (x,y = the tile the builder stands on; the
// workshop also takes the tile to its left, like the original).
Player/proc/RemasterPlaceWorkshop(value)
	var/list/p = splittext("[value]", "|")
	if(p.len != 3) return 0
	var/list/D = RemasterWorkshopDefs()[p[1]]
	if(!D) return 0
	var/turf/T = locate(text2num(p[2]), text2num(p[3]), z)
	if(!T) return 0
	if(p[1] != "banner" && !RemasterMayWork(T)) return 0
	if(!remaster_blueprints) remaster_blueprints = list()
	if(RemasterBlueprintAt(T))
		RemasterNotice("That tile is already planned.")   // as the Build tab's other pieces say (a click there did nothing)
		return 0
	var/list/S = RemasterSiteNew("Workshop:[p[1]]", T.z)
	S["x"] = T.x
	S["y"] = T.y
	S["left"] = 1
	S["total"] = 1
	S["workers"] = 1
	remaster_blueprints += list(list("x"=T.x, "y"=T.y, "z"=T.z, "mode"="Workshop:[p[1]]", "note"="Waiting for a builder", "tries"=0, "site"=S["id"]))
	RemasterUndoPush(list("type"="blueprints", "keys"=list("[T.x],[T.y],[T.z]")))
	var/crew = RemasterSiteAssignUnits(S, RemasterBuilderUnits())
	RemasterNotice("Planned a [lowertext(D[1])]. [RemasterSiteNeedText(S)]. [crew ? crew : RmBuildCrewHint()]")
	return 1

Player/proc/RemasterBuildWorkshop(mob/Monsters/M, turf/T, id)
	if(RemasterIsRune(id)) return RemasterBuildRune(M, T, id)
	if(id == "banner") return RemasterBuildBanner(M, T)
	if(!RemasterMayWork(T)) return 0
	var/list/D = RemasterWorkshopDefs()[id]
	if(!D || M.loc != T) return 0
	for(var/mob/WorkShops/W in view(1, M)) return 0 // the original keeps workshops apart
	var/turf/left = locate(T.x - 1, T.y, T.z)
	if(!(id in list("campfire", "cauldron", "stall", "altar", "foodpot", "foodstall", "clinic", "surgery", "graveyard", "tavern", "notice")) && (!left || left.density)) return 0
	if(id == "gem" && M.Race == "Kobold") return 0
	var/material = D[3]
	var/obj/Items/W
	for(var/obj/Items/I in M) if(istype(I, material))
		W = I
		break
	if(!W) return 0
	if(id == "altar" && RmAltarNeed(M)) return 0
	if(!M.RemasterManualHandoff(src)) return 0
	if(id == "campfire") new /mob/WorkShops/CampFires/Fire(T)
	else if(id == "cauldron") new /mob/WorkShops/RemasterCauldron(T)
	else if(id == "stall") new /mob/WorkShops/RemasterStall(T)
	else if(id == "foodpot") new /mob/WorkShops/RemasterFood/Pot(T)
	else if(id == "foodstall") new /mob/WorkShops/RemasterFood/Stall(T)
	else if(id == "clinic") new /mob/WorkShops/RemasterClinic(T)
	else if(id == "surgery") new /mob/WorkShops/RemasterSurgery(T)
	else if(id == "graveyard") new /mob/WorkShops/RemasterGraveyard(T)
	else if(id == "tavern") new /mob/WorkShops/RemasterTavern(T)
	else if(id == "notice")
		var/mob/WorkShops/RemasterNoticeBoard/NB = new(T)
		NB.house = RemasterHouse()
	else if(id == "altar") RmAltarBuild(M, T)
	else call(M, D[2])()
	M.weight -= W.weight
	del(W)
	for(var/mob/WorkShops/S in T) S.Owner = src
	if(left) for(var/mob/WorkShops/S in left) S.Owner = src
	RemasterMilestone(id == "campfire" ? "camp" : "workshop")    // the Guide's goals, as the Work tab's quick place does (playtest)
	remaster_built_at = world.time
	return 1

Player/var/tmp/list/remaster_unreachable
Player/proc/RemasterMarkUnreachable(obj/Items/I)
	if(!remaster_unreachable) remaster_unreachable = list()
	remaster_unreachable[I] = world.time
Player/proc/RemasterUnreachable(obj/Items/I)
	if(!remaster_unreachable || !remaster_unreachable[I]) return 0
	if(world.time - remaster_unreachable[I] > 3000)
		remaster_unreachable -= I
		return 0
	return 1

proc/RemasterBlueprintRank(mode)
	if(mode == "Gate") return 4 // in a building: the door goes in last, once the walls stand
	if(copytext(mode, 1, 7) == "Piece:") return RemasterPieceRank(mode)
	switch(RemasterBuildShape(mode))
		if("floor", "bridge", "road") return 1
		if("workshop", "stairs", "gate", "ramp", "beam") return 2
	return 3

mob/Monsters/var/tmp/remaster_site_noway = 0   // the last path search to the building spot found no way (RemasterSiteWalk)

// One unit of the builders' pass (RemasterBlueprintTick), as the pass did it in one go (server cost, 2026-10-24).
Player/proc/RmBlueprintUnit(mob/Monsters/M, list/claims, open)
	if(M.Owner != src || M.HP <= 0) return
	if(locate(/obj/Items/Furniture/Pillars/WoodenBeam) in M) M.RemasterAutoBeam(src)
	var/duty = M.remaster_builder || M.remaster_job == "builder"
	if(!duty && M.remaster_site) M.RemasterSiteLeave(src) // job changed away from Builder
	if(M.RemasterSiteBusy()) return
	if(M.remaster_site_return)
		M.RemasterSiteReturnTick(src)
		return
	if(!duty) return
	rm_bp_unit = M   // RemasterSiteSource's "none"s hold for the rest of this step
	rm_bp_none = null
	var/list/S = open ? RemasterSiteFor(M, claims) : null
	if(!S)
		rm_bp_unit = null
		if(M.remaster_builder) M.RemasterSiteEndDuty(src)
		else if(M.remaster_site) M.RemasterSiteLeave(src)
		if(M.remaster_job == "builder" && !M.remaster_site_return)
			M.RemasterSiteStatus(open ? "Builder: no construction this unit can work on here" : "Builder: waiting for construction plans")
			if(!M.destination || M.rm_jz_clear) M.RmJzClearStore(src)   // and never waiting on a store, where carriers put their loads down (Jobs.dm)
		return
	if(M.remaster_site != S["id"])
		rm_bp_unit = null   // joining lets go of its orders and pieces: look afresh
		if(M.remaster_site) claims[M.remaster_site] = max(0, (claims[M.remaster_site] || 1) - 1)
		M.RemasterSiteJoin(src, S)
		claims[S["id"]] = (claims[S["id"]] || 0) + 1
	M.RemasterSiteWork(src, S)
	rm_bp_unit = null
