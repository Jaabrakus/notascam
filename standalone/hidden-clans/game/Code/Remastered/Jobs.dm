// Work zones and the job board (planning/MANAGEMENT_TOOLS.md): a village run by rules instead of clicks, the way
// Songs of Syx runs a city. The player paints work zones (wood, stone, a farm, a stockpile) and says how many hands
// each wants and how much it matters; villagers on the Any work role take the work up by themselves.
//  - Zones are rectangles painted with the build drag (Work tab > Job board > + Wood ..., then a drag in 3D), up to
//    25 x 25 (a farm up to 21 x 21, the farmer's reach). A stockpile zone is a store with a filter (Zones.dm).
//  - Job rows: every zone, plus Builders and Haulers (the jobs that aren't places). Each has workers wanted, a
//    priority (1 High, 2 Normal, 3 Low), "stop at" (the stores' total where it pauses) and Pause.
//  - The allocator (RmJobsTick, every 2 s in the settlement tick) fills rows by priority from the free pool, nearest
//    first, and releases the furthest members of rows over their count. It works on running totals (each row's
//    members, the free pool sorted into 16-tile cells) kept where a unit joins or leaves, a player changes its role,
//    or a record takes it (RmJobUnitGone / RmJobUnitBack, for the records session): a pass is O(rows + units moved).
//    A recount every 60 s, staggered, is the safety net; dead, captured or deleted units are dropped when met.
//  - A worker's step (RmJobStep, one proc with no loop of its own: the unit clock may run it later) takes its next
//    target from its zone's cached list (trees above their tend mark, rock faces) instead of scanning round itself,
//    and makes the same automatic Chop/Mine order the roles make; a farm worker borrows the farmer's own steps.
//    A direct order pauses it as it pauses any role (RemasterSettlementTick), and it goes back after.
//  - A zone's list is built when it's painted and refreshed every 60 s or when it runs dry; a target is checked again
//    when taken, so a felled tree or a broken block simply drops out.

#define RM_JZ_MAX_SIDE 25
#define RM_JZ_FARM_SIDE 21            // the farmer works REMASTER_FOOD_AREA (10) round its spot
#define RM_JZ_EVERY 20                // ticks between allocator passes (2 s)
#define RM_JZ_RECOUNT 600             // the safety-net recount (60 s)
#define RM_JZ_REFRESH 600             // a zone's target list is rebuilt this often
#define RM_JZ_STAY 600                // a worker stays on a row this long before a High row may take it
#define RM_JZ_CELL 16
#define RM_JZ_MOVES 25               // joins and leaves per pass: a big change fills over a few passes, none past ~20 ms
#define RM_JZ_CHECK 64               // workers on a row checked per pass (a rotating slice: no loop over everyone)
#define RM_JZ_PICK 48                // targets a worker's pick looks at, from where the last pick stopped
#define RM_JZ_LOOK 48               // a pick reads at most this many free villagers in a crowded ring: near enough

// kind -> list(label, good counted for "stop at", colour for the 3D outline)
var/list/rm_jz_kinds = list("wood"=list("Wood", "wood", "#6fbf5a"), "stone"=list("Stone", "stone", "#a8a8a0"),
	"farm"=list("Farm", "food", "#e0bb55"), "stock"=list("Stockpile", null, "#c9a36b"), "fish"=list("Fishing", "food", "#5aa9e6"),
	"builders"=list("Builders", null, null), "haulers"=list("Haulers", null, null), "make"=list("Make", null, null),
	"dig"=list("Dig", null, "#eba53c"), "build"=list("Build", null, "#6fa8dc"),   // dig and build plans from Plan mode (Plans.dm)
	"gather"=list("Gather", null, "#d9b45f"))   // trees and rock both: the Gather bar's Gather zone (gathering, 2026-10-26)

Player/var/list/rm_jz                       // saved: the job rows (lists of numbers and text)
Player/var/rm_jz_serial = 0
Player/var/tmp/list/rm_jz_members           // row id -> list of its workers
Player/var/tmp/rm_jz_nfree = 0              // the free pool's size: its units carry rm_jz_free_in and sit in rm_jz_cells
// (no unit -> 1 list: OpenDream searches a list before adding a key to it, so a pool of 28,000 took 1.1 s to rebuild)
Player/var/tmp/list/rm_jz_cells             // cell number (RmJzCellAt) -> free units in that 16-tile cell
Player/var/tmp/rm_jz_cw = 0                 // the cell grid's width and height, from the world's size
Player/var/tmp/rm_jz_ch = 0
Player/var/tmp/rm_jz_last_moves = 0
Player/var/tmp/list/rm_jz_vi                // row id -> where its rotating check got to
Player/var/tmp/list/rm_jz_zfree             // "z" -> free units on that level (a level with none isn't searched)
Player/var/tmp/list/rm_jz_targets           // zone id -> list of workable turfs
Player/var/tmp/list/rm_jz_built             // zone id -> world.time its list was built
Player/var/tmp/rm_jz_refused                // the zone a refused paint overlapped (its name, for the notice)
Player/var/tmp/list/rm_jz_ti                // zone id -> where the next pick starts in its target list
Player/var/tmp/list/rm_jz_doing             // row id -> RmJzDoing's counts, kept by the 2 s pass for the board
Player/var/tmp/list/rm_jz_stock             // good -> list(count, world.time): the stores counted at most every 2 s
Player/var/tmp/list/rm_jz_out               // row id -> gathered in each of six 10 s buckets (RmJzYield)
Player/var/tmp/list/rm_jz_out_t             // row id -> the bucket number each count belongs to
Player/var/tmp/list/rm_jz_hist              // the stores sampled every 10 s: list(world.time, wood, stone, food), last 7
Player/var/tmp/list/rm_jz_prob              // row id -> what needs the player (RmJzProblemOf), kept by the 2 s pass
Player/var/tmp/list/rm_jz_lognote           // row id -> list(came, went) since the last Village Log line
Player/var/tmp/rm_jz_log_at = 0             // world.time the next lines are due (one per row at most every 30 s)
Player/var/tmp/list/rm_jz_resting           // zone id -> trees and living ore in it resting at their tending mark
Player/var/tmp/list/rm_jz_res               // zone id -> list(turf = worker): targets taken
Player/var/tmp/rm_jz_next = 0
Player/var/tmp/rm_jz_recount_at = 0
Player/var/tmp/rm_jz_ready = 0              // the totals have been built since the world started
Player/var/tmp/rm_jz_last_ms = 0            // the last pass's cost, for the tests and the profiler
mob/Monsters/var/rm_jz_id                   // saved: the row this unit works for
mob/Monsters/var/tmp/rm_jz_since = 0
mob/Monsters/var/tmp/rm_jz_cell             // its cell key while in the free pool
mob/Monsters/var/tmp/rm_jz_block = 0        // why its last job step couldn't work: 1 no drop-off, 2 drop-off refuses the good, 3 another level
mob/Monsters/var/tmp/rm_jz_free_in = 0      // in its realm's free pool (Any work, on no row)
mob/Monsters/var/tmp/rm_jz_cz               // and that cell's level
mob/Monsters/var/tmp/turf/rm_jz_last        // the last target RmJzTake gave it (a mined-out block's new faces join the list)
turf/var/tmp/rm_jz_tid                      // the zone whose target list this tile is on (the nearest-target search reads it)

// --- Rows ----------------------------------------------------------------------------------------------------
Player/proc/RmJz(id)
	if(rm_jz) for(var/list/Z in rm_jz) if(Z["id"] == id) return Z
	return null

proc/RmJzIsZone(list/Z)
	return Z && (Z["kind"] in list("wood", "stone", "farm", "stock", "fish", "gather"))

// Builders and Haulers rows always exist.
Player/proc/RmJzFixedRows()
	if(!rm_jz) rm_jz = list()
	if(!RmJz("builders")) rm_jz += list(list("id"="builders", "kind"="builders", "name"="Builders", "want"=0, "prio"=2, "stop"=0, "paused"=0))
	if(!RmJz("haulers")) rm_jz += list(list("id"="haulers", "kind"="haulers", "name"="Haulers", "want"=0, "prio"=3, "stop"=0, "paused"=0))

Player/proc/RmJzAdd(kind, x0, y0, x1, y1, z)
	if(!RmJzIsZone(list("kind"=kind))) return null
	var/side = kind == "farm" ? RM_JZ_FARM_SIDE : RM_JZ_MAX_SIDE
	var/ax = min(x0, x1)
	var/bx = max(x0, x1)
	var/ay = min(y0, y1)
	var/by = max(y0, y1)
	bx = min(bx, ax + side - 1)
	by = min(by, ay + side - 1)
	// work zones don't share ground (a tree would be on two rows' lists at once); a store may sit inside one
	rm_jz_refused = null
	if(kind != "stock")
		for(var/list/X in rm_jz) if(RmJzIsZone(X) && X["kind"] != "stock" && X["z"] == z && ax <= X["x1"] && bx >= X["x0"] && ay <= X["y1"] && by >= X["y0"])
			rm_jz_refused = X["name"]
			return null
	RmJzFixedRows()
	rm_jz_serial++
	var/count = 0
	for(var/list/X in rm_jz) if(X["kind"] == kind) count++
	var/list/Z = list("id"="j[rm_jz_serial]", "kind"=kind, "name"="[rm_jz_kinds[kind][1]] [count + 1]", "x0"=ax, "y0"=ay, "x1"=bx, "y1"=by, "z"=z,
		"want"=kind == "stock" ? 0 : min(RmJzCap(list("x0"=ax, "y0"=ay, "x1"=bx, "y1"=by)), 4), "prio"=2, "stop"=0, "paused"=0)
	if(kind == "stock")
		// a store with a filter at the zone's middle (Zones.dm): the nearest open tile in the zone
		var/turf/C = RmJzOpenNear(round((ax + bx) / 2), round((ay + by) / 2), z, Z)
		if(C)
			if(!remaster_zones) remaster_zones = list()
			remaster_zone_serial++
			remaster_zones += list(list("id"="z[remaster_zone_serial]", "name"=Z["name"], "x"=C.x, "y"=C.y, "z"=C.z, "filter"="any", "x0"=ax, "y0"=ay, "x1"=bx, "y1"=by))   // its whole area (Zones.dm RemasterZoneCells)
			Z["store"] = "z[remaster_zone_serial]"
	rm_jz += list(Z)
	RmJzBuildTargets(Z)
	return Z

proc/RmJzOpenNear(x, y, z, list/Z)
	var/turf/best
	var/bd = 1#INF
	for(var/turf/T in block(locate(Z["x0"], Z["y0"], z), locate(Z["x1"], Z["y1"], z))) if(!T.density)
		var/d = abs(T.x - x) + abs(T.y - y)
		if(d < bd)
			bd = d
			best = T
	return best

// A zone can't swallow the village: one worker for every 4 tiles.
proc/RmJzCap(list/Z)
	return max(1, round((Z["x1"] - Z["x0"] + 1) * (Z["y1"] - Z["y0"] + 1) / 4))

Player/proc/RmJzRemove(list/Z)
	var/list/members = RmJzMembers(Z["id"])
	for(var/mob/Monsters/M in members.Copy()) RmJobLeave(M)
	if(Z["store"] && remaster_zones) for(var/list/S in remaster_zones.Copy()) if(S["id"] == Z["store"]) remaster_zones -= list(S)
	for(var/list/L in list(rm_jz_targets, rm_jz_res, rm_jz_built, rm_jz_resting, rm_jz_vi, rm_jz_lognote, rm_jz_ti, rm_jz_doing, rm_jz_prob, rm_ch_prog)) L -= Z["id"]
	if(rm_jz_loose) rm_jz_loose -= Z["id"]
	if(rm_jz_loose_at) rm_jz_loose_at -= Z["id"]
	if(Z["stock"]) RmSiteSpill(Z)   // a build plan's pile: its stone or logs lie there again (Sites.dm)
	rm_jz -= list(Z)

// --- A zone's work: its cached targets ------------------------------------------------------------------------
proc/RmJzRect(list/Z)
	return block(locate(Z["x0"], Z["y0"], Z["z"]), locate(Z["x1"], Z["y1"], Z["z"]))

// At its tending mark: left to grow back (Yield.dm). With no worker yet the realm's own setting decides (Yield.dm
// counts "no worker" as tending on); a tile's own mark (remaster_tend) always holds.
Player/proc/RmJzTended(turf/T, mob/Monsters/M)
	if(M || remaster_tend_living || T.remaster_tend > 0) return RemasterTendReached(T, M)
	return 0

// A gather zone's target goes by the rules of what it is: a tree a wood zone's, rock a stone zone's.
proc/RmJzKindAt(list/Z, turf/T)
	return Z["kind"] == "gather" ? (T && T.Tree ? "wood" : "stone") : Z["kind"]

// Workable but for tending: a tree or a living ore block resting (the board shows them as "resting").
Player/proc/RmJzRests(list/Z, turf/T, mob/Monsters/M)
	if(!T || !T.density || (T.Owner && T.Owner != src)) return 0
	var/kind = RmJzKindAt(Z, T)
	if(kind == "wood") return T.Tree && (T.remaster_tend == RM_TEND_SAPLING || RmJzTended(T, M) || RmJzTreeShort(T, M))
	if(kind == "stone") return T.CanDigAt && !T.Tree && !T.IsWall && !RmBuilt(T) && T.remaster_ore_max && RmJzTended(T, M)
	return 0

Player/proc/RmJzWorkable(list/Z, turf/T, mob/Monsters/M)
	if(!T || !T.density || (T.Owner && T.Owner != src)) return 0
	switch(RmJzKindAt(Z, T))
		if("wood") return T.Tree && T.remaster_tend != RM_TEND_SAPLING && !RmJzTended(T, M) && !RmJzTreeShort(T, M)
		if("stone")
			if(!T.CanDigAt || T.Tree || T.IsWall || RmBuilt(T)) return 0   // a built column is a wall, not a quarry (Plans.dm)
			if(RmJzTended(T, M)) return 0          // a living ore block at its mark rests, as trees do
			for(var/d in list(NORTH, SOUTH, EAST, WEST))     // a face someone can stand at
				var/turf/N = get_step(T, d)
				if(N && !N.density) return 1
	return 0

// A tended tree growing back with less than a log's work above its mark (far-records, 2026-10-24): a blow on it earns
// nothing before the mark stops it, restarts its 2-minute rest, and the growing loop then drops the work (Yield.dm), so
// a tree nibbled as it grew never came back. It rests until there's a log's work on it again.
proc/RemasterTreeGrowing(turf/T, mob/Monsters/M)
	if(!T || !T.Tree || !T.density) return 0
	var/share = T.remaster_tend > 0 ? T.remaster_tend : T.remaster_tend < 0 ? 0 : RemasterTendsLiving(M) ? RM_TEND_TREE : 0
	if(!share) return 0
	var/mark = RemasterTreeMax(T) * share / 100
	return T.HP > mark && T.HP - mark + T.remaster_yield_acc < RM_TREE_LOG_WORK

Player/proc/RmJzTreeShort(turf/T, mob/Monsters/M)
	if(!(M || remaster_tend_living || T.remaster_tend > 0)) return 0   // as RmJzTended
	return RemasterTreeGrowing(T, M)

Player/proc/RmJzBuildTargets(list/Z)
	if(!(Z["kind"] in list("wood", "stone", "gather"))) return
	if(!rm_jz_targets) rm_jz_targets = list()
	if(!rm_jz_built) rm_jz_built = list()
	var/list/L = list()
	var/rest = 0
	var/spotted = 0     // tiles with pieces lying found by this look (J2: as many waiting workers are called)
	var/list/old = rm_jz_targets[Z["id"]]
	if(old) for(var/turf/T in old) if(T.rm_jz_tid == Z["id"]) T.rm_jz_tid = null
	var/fill = Z["reach"] ? RmJzFill(Z) : null      // only once a worker found no way to one of its targets (RemasterGiveUpOrApproach)
	var/far = 0
	var/list/G = list()       // its stumps and saplings (the Tend redo: RmJzRegrowStep)
	var/regrows = Z["kind"] in list("wood", "gather")
	for(var/turf/T in RmJzRect(Z))
		if(RmJzWorkable(Z, T, null))
			if(fill && !RmJzReached(T, fill)) far++      // no way to it from outside the zone: not handed out (RmJzFill)
			else
				L += T
				T.rm_jz_tid = Z["id"]
		else if(RmJzRests(Z, T, null)) rest++
		if(regrows && T.remaster_tend == RM_TEND_SAPLING && !T.density) T.remaster_tend = RM_TEND_STUMP   // a sapling knocked down (a unit that walks into a tree chops it, Bump.dm): a stump again
		if(regrows && (T.remaster_tend == RM_TEND_STUMP && !T.density || T.remaster_tend == RM_TEND_SAPLING && T.density && T.Tree)) G += T   // the Tend redo
		if(!T.density && T.rm_jz_spot != Z["id"]) for(var/obj/Items/I in T) if(isnull(I.suffix) && (RemasterResourceKind(I) || RemasterRawKind(I)))
			if(RmJzSpot(Z["id"], T)) spotted++
			break
	rm_jz_targets[Z["id"]] = L
	if(!rm_jz_regrow) rm_jz_regrow = list()
	rm_jz_regrow[Z["id"]] = G      // its stumps and saplings (RmJzRegrowStep)
	// stumps to plant and saplings due a visit call as many waiting workers (not one a sapling: most were tended a moment
	// ago, and each woken worker only looked and waited again)
	if(length(G) && rm_jz_waiting && length(rm_jz_waiting[Z["id"]]))
		var/due = 0
		for(var/turf/S in G) if(RmJzRegrowWants(S, Z)) due++
		if(due) RmJzWakeRow(Z["id"], due)
	if((length(L) || spotted) && rm_jz_waiting && length(rm_jz_waiting[Z["id"]]))   // trees grown back, ore come back (as many as nobody's on), pieces found lying (J2)
		var/list/R = rm_jz_res ? rm_jz_res[Z["id"]] : null
		var/free = 0
		for(var/turf/T in L)
			var/mob/Monsters/H = R ? R[T] : null
			if(!(H && H.rm_jz_id == Z["id"] && H.remaster_active && H.remaster_active.target == T)) free++
		if(free + spotted) RmJzWakeRow(Z["id"], free + spotted)
	if(!rm_jz_resting) rm_jz_resting = list()
	rm_jz_resting[Z["id"]] = rest
	if(!rm_jz_far) rm_jz_far = list()
	rm_jz_far[Z["id"]] = far
	rm_jz_built[Z["id"]] = world.time

// Out of reach (polish-zones, 10-26): a zone painted over trees or rock with no way to some of them (walled in, across
// water) handed those out like any other, nearest first, and the workers stood "No way through yet; trying again" for
// good: 5 of 5 on a half-walled wood for the last 6 of 8 minutes, the row saying "5 chopping". When its list is built, the
// open ground in and round the zone that a walker gets to from outside it is filled (8 ways, from the open tiles of its
// ring); a target whose open neighbours are all beyond that fill is counted out of reach (the row says how many) and not
// handed out; one with no open neighbour at all (deep in a wood or the rock) stays on the list as before. A worker that
// still finds no way to its target gives up after 15 s, as a plan's do, and leaves that one to the others for 3 minutes.
// The fill costs ~10 ms on a 25 x 25 zone (the list itself ~4), so a zone fills only once one of its workers has found
// no way to a target (Z["reach"], kept with the row); its list is rebuilt at once then.
#define RM_JZ_NO_WAY 150
#define RM_JZ_SKIP 1800
Player/var/tmp/list/rm_jz_far               // zone id -> its targets out of reach, at the last build
mob/Monsters/var/tmp/list/rm_jz_skip        // targets it found no way to: turf -> when it may try again
datum/remaster_order/var/tmp/rm_jz = 0      // a zone's own Chop or Mine (RmJobStep)

// The fill over the zone and its ring: list(x0, y0, width, height, open, reached), the last two by tile index; null when
// the ring has no open tile (painted inside a wood or the rock): no test then. Numbers, not range() round each tile: a
// 25 x 25 zone's list was rebuilt in ~6 ms, and range() put ~9 ms on top.
proc/RmJzFill(list/Z)
	var/z = Z["z"]
	var/x0 = max(1, Z["x0"] - 1)
	var/y0 = max(1, Z["y0"] - 1)
	var/x1 = min(world.maxx, Z["x1"] + 1)
	var/y1 = min(world.maxy, Z["y1"] + 1)
	var/w = x1 - x0 + 1
	var/h = y1 - y0 + 1
	var/list/open = new/list(w * h)
	var/list/seen = new/list(w * h)
	var/list/Q = list()
	for(var/turf/T in block(locate(x0, y0, z), locate(x1, y1, z))) if(!T.density)
		var/i = (T.x - x0) + (T.y - y0) * w + 1
		open[i] = 1
		if(T.x == x0 || T.x == x1 || T.y == y0 || T.y == y1)
			seen[i] = 1
			Q += i
	if(!length(Q)) return null
	var/k = 1
	while(k <= length(Q))
		var/q = Q[k++]
		var/cx = (q - 1) % w
		var/cy = round((q - 1) / w)
		for(var/ny = max(0, cy - 1), ny <= min(h - 1, cy + 1), ny++) for(var/nx = max(0, cx - 1), nx <= min(w - 1, cx + 1), nx++)
			var/j = nx + ny * w + 1
			if(open[j] && !seen[j])
				seen[j] = 1
				Q += j
	return list(x0, y0, w, h, open, seen)

// A target reached by fill F: one of its open neighbours is, or it has none (worked from a neighbour once that's out).
proc/RmJzReached(turf/T, list/F)
	var/w = F[3]
	var/h = F[4]
	var/list/open = F[5]
	var/list/seen = F[6]
	var/cx = T.x - F[1]
	var/cy = T.y - F[2]
	var/any = 0
	for(var/ny = max(0, cy - 1), ny <= min(h - 1, cy + 1), ny++) for(var/nx = max(0, cx - 1), nx <= min(w - 1, cx + 1), nx++)
		if(nx == cx && ny == cy) continue
		var/j = nx + ny * w + 1
		if(open[j])
			if(seen[j]) return 1
			any = 1
	return !any

// "34 trees", "1 rock face": a zone's targets out of reach at its last build, or "" with none.
Player/proc/RmJzFarText(list/Z)
	var/n = rm_jz_far ? rm_jz_far[Z["id"]] : 0
	if(!n) return ""
	return "[n] [Z["kind"] == "wood" ? "tree" : Z["kind"] == "gather" ? "tree or rock face" : "rock face"][n == 1 ? "" : "s"]"

mob/Monsters/proc/RmJzSkip(turf/T)
	if(!isturf(T)) return
	if(!rm_jz_skip) rm_jz_skip = list()
	for(var/turf/K in rm_jz_skip.Copy()) if(rm_jz_skip[K] <= world.time) rm_jz_skip -= K
	rm_jz_skip[T] = world.time + RM_JZ_SKIP

// A zone's own target with no way to it: given up after RM_JZ_NO_WAY (other orders: Orders.dm, a minute).
mob/Monsters/RemasterGiveUpOrApproach(datum/remaster_order/O, atom/A, reach)
	if(!O || !O.rm_jz) return ..()
	if(!RemasterApproach(O, A, reach) && O.stuck_since && world.time - O.stuck_since > RM_JZ_NO_WAY)
		RmJzSkip(isturf(A) ? A : A.loc)
		var/Player/P = Owner
		var/list/Z = istype(P) && rm_jz_id ? P.RmJz(rm_jz_id) : null
		if(Z && !Z["reach"])
			Z["reach"] = 1
			if(P.rm_jz_built) P.rm_jz_built[Z["id"]] = -RM_JZ_REFRESH    // rebuilt with the fill at the next take
		RemasterFinishOrder("Couldn't get there: no way through")
		return 0
	return 1

Player/proc/RmJzTargetsLeft(list/Z)
	if(RmPlanKind(Z["kind"])) return RmPlanLeft(Z)   // a dig or build plan's blocks (Plans.dm)
	if(Z["kind"] == "fish") return length(RmJzFishSpots(Z))
	if(!(Z["kind"] in list("wood", "stone", "gather"))) return -1
	if(!rm_jz_targets || isnull(rm_jz_targets[Z["id"]]) || world.time - (rm_jz_built[Z["id"]] || 0) > RM_JZ_REFRESH) RmJzBuildTargets(Z)
	var/list/L = rm_jz_targets[Z["id"]]
	return length(L)

// The nearest target in the zone nobody else is working: checked again as it's taken (felled, broken, tended).
Player/proc/RmJzTake(list/Z, mob/Monsters/M)
	if(RmJzTargetsLeft(Z) <= 0 && world.time - (rm_jz_built[Z["id"]] || 0) > 50) RmJzBuildTargets(Z)   // ran dry: look again
	var/list/L = rm_jz_targets[Z["id"]]
	if(!length(L)) return null
	if(!rm_jz_res) rm_jz_res = list()
	var/list/R = rm_jz_res[Z["id"]]
	if(!R)
		R = list()
		rm_jz_res[Z["id"]] = R
	// at most RM_JZ_PICK targets looked at, from where the last pick stopped (a zone of 625 isn't read whole for each
	// log); the nearest of those, the dead dropped as they're met, the taken skipped
	// a mined-out block opens the blocks beside it: those that are faces now join the list at once
	if(M.rm_jz_last && (Z["kind"] in list("stone", "gather")) && !M.rm_jz_last.density) RmJzNewFaces(Z, M.rm_jz_last, L)
	var/turf/near = RmJzNearTarget(Z, M, L, R)
	if(near)
		R[near] = M
		M.rm_jz_last = near
		return near
	if(!rm_jz_ti) rm_jz_ti = list()
	var/i = rm_jz_ti[Z["id"]] || 1
	var/turf/best
	var/bd = 1#INF
	var/looked = 0
	while(length(L) && looked < min(RM_JZ_PICK, length(L)))
		if(i > length(L)) i = 1
		var/turf/T = L[i]
		if(!RmJzWorkable(Z, T, M))
			if(RmJzRests(Z, T, M))          // worked down to its mark: now resting (exact again at the next rebuild)
				if(!rm_jz_resting) rm_jz_resting = list()
				rm_jz_resting[Z["id"]] = rm_jz_resting[Z["id"]] + 1
			L.Cut(i, i + 1)
			R -= T
			if(T.rm_jz_tid == Z["id"]) T.rm_jz_tid = null
			continue
		looked++
		i++
		if(M.rm_jz_skip && M.rm_jz_skip[T] > world.time) continue   // it found no way to it lately
		var/mob/Monsters/H = R[T]
		if(H && H != M && H.rm_jz_id == Z["id"] && H.remaster_active && H.remaster_active.target == T) continue   // someone's on it
		var/d = abs(T.x - M.x) + abs(T.y - M.y)
		if(d < bd)
			bd = d
			best = T
	rm_jz_ti[Z["id"]] = i
	if(best) R[best] = M
	M.rm_jz_last = best
	return best

// The nearest target to the worker that nobody else is on: rings round it (from the zone's nearest edge when it's
// outside), over the tiles marked as this zone's targets. A target found no longer workable leaves the list there. At
// most RM_JZ_RING tiles read: then the list's rotating pick above.
#define RM_JZ_RING 60
Player/proc/RmJzNearTarget(list/Z, mob/Monsters/M, list/L, list/R)
	var/x0 = Z["x0"]
	var/x1 = Z["x1"]
	var/y0 = Z["y0"]
	var/y1 = Z["y1"]
	var/px = clamp(M.x, x0, x1)
	var/py = clamp(M.y, y0, y1)
	var/read = 0
	var/maxr = max(x1 - x0, y1 - y0)
	for(var/r = 0, r <= maxr && read < RM_JZ_RING, r++)
		var/turf/best
		var/bd = 1#INF
		// the ring's edge only: its top and bottom rows, then its two sides
		for(var/x = max(x0, px - r), x <= min(x1, px + r), x++)
			for(var/k = 1, k <= (r ? 2 : 1), k++)
				var/y = k == 1 ? py - r : py + r
				if(y < y0 || y > y1) continue
				read++
				var/turf/T = RmJzRingTile(Z, M, L, R, x, y)
				if(T && abs(T.x - M.x) + abs(T.y - M.y) < bd)
					bd = abs(T.x - M.x) + abs(T.y - M.y)
					best = T
		for(var/y = max(y0, py - r + 1), y <= min(y1, py + r - 1), y++)
			for(var/k = 1, k <= 2, k++)
				var/x = k == 1 ? px - r : px + r
				if(x < x0 || x > x1) continue
				read++
				var/turf/T = RmJzRingTile(Z, M, L, R, x, y)
				if(T && abs(T.x - M.x) + abs(T.y - M.y) < bd)
					bd = abs(T.x - M.x) + abs(T.y - M.y)
					best = T
		if(best) return best
	return null

// One tile of the search: the zone's target, workable and nobody else on it, or null (a target no longer workable leaves
// the list here, counted resting when it rests).
Player/proc/RmJzRingTile(list/Z, mob/Monsters/M, list/L, list/R, x, y)
	var/turf/T = locate(x, y, Z["z"])
	var/id = Z["id"]
	if(!T || T.rm_jz_tid != id) return null
	if(!RmJzWorkable(Z, T, M))
		if(RmJzRests(Z, T, M))
			if(!rm_jz_resting) rm_jz_resting = list()
			rm_jz_resting[id] = rm_jz_resting[id] + 1
		T.rm_jz_tid = null
		L -= T
		R -= T
		return null
	var/mob/Monsters/H = R[T]
	if(H && H != M && H.rm_jz_id == id && H.remaster_active && H.remaster_active.target == T) return null   // someone's on it
	if(M.rm_jz_skip && M.rm_jz_skip[T] > world.time) return null   // it found no way to it lately
	return T

// The blocks beside a mined-out one that are workable faces now: onto the zone's list.
Player/proc/RmJzNewFaces(list/Z, turf/D, list/L)
	var/n = 0
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/N = get_step(D, d)
		if(!N || N.rm_jz_tid == Z["id"] || N.x < Z["x0"] || N.x > Z["x1"] || N.y < Z["y0"] || N.y > Z["y1"] || N.z != Z["z"]) continue
		if(RmJzWorkable(Z, N, null))
			L += N
			N.rm_jz_tid = Z["id"]
			n++
	if(n && rm_jz_waiting && length(rm_jz_waiting[Z["id"]])) RmJzWakeRow(Z["id"], n)   // faces opened (J2)

// --- Pieces lying in the zones (the user, 2026-10-24: "we need to add a thing where they pick up resources from the
// ground in zone") ------------------------------------------------------------------------------------------------
// A full bag leaves what's dug or cut at the worker's feet, and pieces get dropped; they rot on the ground after about
// half an hour. A gather zone keeps the tiles where pieces may lie (added as each piece drops and at the 60 s rebuild;
// a tile found empty leaves), so finding the nearest is a look at a few tiles, never a search round each worker. Its
// workers lift them before cutting or digging anything new, the zone's own good first, and carry them in with the
// next full bag; the job board's haulers sweep every zone's (below).
Player/var/tmp/list/rm_jz_loose            // zone id -> tiles where pieces may lie (in the zone or a tile round it)
Player/var/tmp/rm_jz_found_d = 0           // RmJzLooseFind's distance to what it found
turf/var/tmp/rm_jz_spot                    // the zone whose list this tile is on
obj/Items/var/tmp/mob/Monsters/rm_jz_by    // the worker going for this piece

Player/proc/RmJzSpot(id, turf/T)
	if(!isturf(T) || T.rm_jz_spot == id || RmJzStored(T)) return
	T.rm_jz_spot = id
	if(!rm_jz_loose) rm_jz_loose = list()
	var/list/L = rm_jz_loose[id]
	if(!L)
		L = list()
		rm_jz_loose[id] = L
	L += T
	return 1

// Goods on T are in the stores, not lying: within a tile of one of the realm's store tiles, as the stores' counts read
// them (Board.dm RemasterStockCount). A store may sit in a zone or by it (a yard, "Stockpile here"), and its goods were
// lifted as "pieces lying in the zone" and put back a tile away, for good (polish-zones, 10-26: two zones side by side,
// one's yard inside the other: 1,230 trips of under a tile in 8 minutes, the wood row stalled 6 minutes).
Player/proc/RmJzStored(turf/T)
	if(!RemasterInStoreArea(T)) return 0      // the marked areas (Zones.dm): most tiles end here
	for(var/turf/S in RemasterStores()) if(S.z == T.z && get_dist(S, T) <= 1) return 1
	return 0

// A piece left lying in a zone (a full bag: Yield.dm RemasterYieldGive) calls one of its waiting workers (J2). Every
// piece made registers its tile (RmJzYield), lying or not, so the call is made only once one really lies there.
Player/proc/RmJzLying(id)
	if(rm_jz_waiting && length(rm_jz_waiting[id])) RmJzWakeRow(id, 1)

// A zone with nothing left to cut or dig keeps up to one worker for each tile where pieces still lie (dropped from full
// bags as it was worked), so they're lifted before its workers go: at 2,000 workers every quarry was dug out within 5
// minutes and its pieces lay there for good (tests/gather_score.dm GsDiag2000S, 2026-10-25). Its workers lift them
// first (RmJzPickUpStep). The list is checked here at most every 5 s (tiles with nothing left to lift leave it, as in
// RmJzLooseFind), so a zone nobody works any more never calls workers out for pieces already gone.
Player/var/tmp/list/rm_jz_loose_at         // zone id -> when RmJzLooseWant next checks its list

// Who goes first when a row wants fewer: a few over, the furthest from the zone; many at once (a row turned down), the
// newest joiners. A zone with nothing left keeps workers only for the pieces lying in it (RmJzLooseWant), so there the
// ones carrying a load in, or with no room for another piece, go first: the ones kept can lift the pieces now.
Player/proc/RmJzLeaver(list/Z, list/members, want)
	if(want > 0 && RmJzTargetsLeft(Z) == 0)
		for(var/k = length(members), k >= 1, k--)
			var/mob/Monsters/M = members[k]
			if(M && (M.remaster_delivery || M.weight + 25 > M.weightmax)) return M
	return length(members) - want <= 4 ? RmJzFurthest(Z, members) : members[length(members)]
Player/proc/RmJzLooseWant(list/Z, want)
	if(!(Z["kind"] in list("wood", "stone", "gather"))) return 0
	var/id = Z["id"]
	var/list/L = rm_jz_loose ? rm_jz_loose[id] : null
	if(!length(L)) return 0
	if(!rm_jz_loose_at) rm_jz_loose_at = list()
	if(world.time >= (rm_jz_loose_at[id] || 0))
		rm_jz_loose_at[id] = world.time + 50
		for(var/k = length(L), k >= 1, k--)
			var/turf/T = L[k]
			var/any = 0
			if(T.rm_jz_spot == id && !RmJzStored(T)) for(var/obj/Items/I in T) if(isnull(I.suffix) && RemasterMayCollect(I) && RemasterStockAccepts(I))
				any = 1
				break
			if(!any)
				if(T.rm_jz_spot == id) T.rm_jz_spot = null
				L.Cut(k, k + 1)
	return min(want, length(L))

// The nearest piece on the zone's tiles that the stockpile takes and nobody else is going for, its own good first (null:
// none). Tiles with nothing left leave the list.
Player/proc/RmJzLooseFind(list/Z, mob/Monsters/M)
	var/id = Z["id"]
	var/list/L = rm_jz_loose ? rm_jz_loose[id] : null
	if(!length(L)) return null
	var/own = Z["kind"] == "wood" ? /obj/Items/woods/wood : Z["kind"] == "stone" ? /obj/Items/ores/stone : /obj/Items   // a gather zone's: any
	var/obj/Items/best
	var/bd = 1#INF
	var/best_own = 0
	for(var/k = length(L), k >= 1, k--)     // from the end, so a tile dropped here doesn't move the ones still to read
		var/turf/T = L[k]
		if(T.rm_jz_spot != id || RmJzStored(T))     // a store painted over it since: what lies there is stored
			if(T.rm_jz_spot == id) T.rm_jz_spot = null
			L.Cut(k, k + 1)
			continue
		var/any = 0
		for(var/obj/Items/I in T)
			if(!isnull(I.suffix) || !RemasterMayCollect(I) || !RemasterStockAccepts(I)) continue
			any = 1
			if(M.RmShunsSilver(I)) continue     // left for the others (Delivery.dm)
			var/mob/Monsters/H = I.rm_jz_by
			if(H && H != M && H.remaster_active && H.remaster_active.target == I) continue
			var/mine = istype(I, own) ? 1 : 0
			var/d = abs(T.x - M.x) + abs(T.y - M.y)
			if(mine > best_own || (mine == best_own && d < bd))
				best = I
				bd = d
				best_own = mine
		if(!any)
			T.rm_jz_spot = null
			L.Cut(k, k + 1)
	rm_jz_found_d = bd
	return best

// Lift the nearest lying piece (1), or carry a full bag in first (1); 0: nothing lying, work on.
mob/Monsters/proc/RmJzPickUpStep(Player/P, list/Z)
	var/obj/Items/I = P.RmJzLooseFind(Z, src)
	if(!I) return 0
	if(weight + I.weight > weightmax)
		if(RemasterDeliveryWeight(P) <= 0) return 0       // a bag full of what no store takes: work on
		RemasterBeginDelivery(null)
		return 1
	RmJzLift(P, I)
	remaster_work_status = "[Z["name"]]: picking up [lowertext(I.name)] lying in the zone"
	return 1

mob/Monsters/proc/RmJzLift(Player/P, obj/Items/I)
	I.rm_jz_by = src
	var/datum/remaster_order/O = new
	O.issuer = P
	O.target = I
	O.kind = "Pick up"
	O.automatic = 1
	remaster_auto_unload = 1
	RemasterSuspendControllers()
	remaster_active = O
	RemasterStartOrder(O)
	RemasterOrderTick()

// Haulers on the job board sweep the gather zones, nearest piece first, filling the bag (with a load, only pieces within
// 10 tiles) before the trip in; with nothing lying in any zone they keep the stockpile's surroundings as before
// (Delivery.dm RemasterRoleTick, 6 tiles round their work area).
mob/Monsters/RemasterRoleTick(Player/P)
	if(remaster_job != "hauler" || rm_jz_id != "haulers" || !istype(P)) return ..()
	if(!length(P.rm_jz_loose))
		if(RmJzYardHaul(P)) return      // nothing lying in the zones: a yard's goods to the main stockpile (below)
		return ..()
	var/carrying = RemasterDeliveryWeight(P)
	var/obj/Items/best
	var/bd = carrying ? 10 : 1#INF
	for(var/list/Z in P.rm_jz) if((Z["kind"] in list("wood", "stone", "gather")) && Z["z"] == z)
		var/obj/Items/I = P.RmJzLooseFind(Z, src)
		if(I && P.rm_jz_found_d < bd)
			best = I
			bd = P.rm_jz_found_d
	if(best && weight + best.weight <= weightmax)
		RmJzLift(P, best)
		RemasterRoleStatus("Hauling [lowertext(best.name)] lying in a work zone")
		return
	if(carrying)
		RemasterBeginDelivery(null)
		return
	if(RmJzYardHaul(P)) return
	return ..()

// The haulers row carries the yards' goods in to the main stockpile, where the workshops are (the user, 2026-10-25:
// "haulers will move that stockpile to the like workhouse or a warehouse"): the nearest yard holding something the main
// stockpile takes, a bag of it, and that load goes to the main stockpile, never to the nearest store (that's the yard).
// Builders, crafters and cooks keep fetching from any store, so nothing waits on the haulers. 1 when it did something.
mob/Monsters/var/tmp/rm_jz_to_main = 0      // its next delivery goes to the main stockpile (RemasterBeginDelivery)
datum/remaster_order/var/tmp/to_main = 0    // a haul from a yard: never sent on to another store
mob/Monsters/proc/RmJzYardHaul(Player/P)
	var/turf/S = P.RemasterStockpile()
	if(!S || S.z != z || S.density || !P.remaster_zones) return 0
	var/turf/best
	var/bd = 1#INF
	var/list/BZ
	for(var/list/E in P.remaster_zones) if(E["yard"] && E["z"] == z)
		for(var/turf/C in P.RemasterZoneCells(E))
			var/d = get_dist(src, C)
			if(d >= bd) continue
			for(var/obj/Items/I in range(1, C)) if(isturf(I.loc) && P.RemasterMayCollect(I) && P.RemasterStockAccepts(I) && I.weight <= weightmax - weight && !RmShunsSilver(I))
				best = C
				bd = d
				BZ = E
				break
	if(!best) return 0
	if(get_dist(src, best) > 1)
		RemasterWorkToward(best, BZ["name"])
		return 1
	var/n = 0
	for(var/obj/Items/I in range(1, best))
		if(!isturf(I.loc) || !P.RemasterMayCollect(I) || !P.RemasterStockAccepts(I) || weight + I.weight > weightmax || RmShunsSilver(I)) continue
		if(PickUpItem(I)) n++
	if(!n) return 0
	rm_jz_to_main = 1
	RemasterBeginDelivery(null)
	RemasterRoleStatus("Hauling [n] from the [BZ["name"]] to the stockpile")
	return 1

// A villager with nothing to do never waits beside a store. Carriers stop on one of the tiles round it to put their
// loads down, and never on a friend's tile (Clip.dm), so a few idle villagers there held all of them off. It walks to
// an open tile 3 or 4 tiles from the store, the nearest, and waits there. 1 while it goes.
mob/Monsters/var/tmp/turf/rm_jz_clear
mob/Monsters/var/tmp/rm_jz_clear_next = 0      // the next look round for a store beside it (every 2 s, not every step)
mob/Monsters/proc/RmJzClearStore(Player/P, now = 0)
	if(rm_jz_clear)
		if(loc != rm_jz_clear && destination == rm_jz_clear) return 1
		if(remaster_work_destination == rm_jz_clear) remaster_work_destination = null
		rm_jz_clear = null
		return 0
	if(!isturf(loc) || (!now && world.time < rm_jz_clear_next)) return 0   // now: the look before it starts waiting
	rm_jz_clear_next = world.time + 20
	if(!P.RemasterInStoreArea(loc)) return 0   // beside no store (the tiles are marked, Zones.dm): no walk over the stores
	var/turf/S = P.RemasterStockpile()
	if(!S || S.z != z || get_dist(S, src) > 1)
		S = null
		if(P.remaster_zones) for(var/list/Z in P.remaster_zones) if(Z["z"] == z)
			for(var/turf/C in P.RemasterZoneCells(Z)) if(get_dist(C, src) <= 1)
				S = C
				break
			if(S) break
	if(!S) return 0
	var/turf/best
	var/bd = 1#INF
	for(var/turf/T in range(4, S))
		if(get_dist(T, S) < 3 || P.RemasterInStoreArea(T) || T.density || (locate(/mob/Monsters) in T) || RemasterWalkable(T, src) != 1) continue
		var/k = get_dist(T, src)
		if(k < bd)
			bd = k
			best = T
	if(!best)   // deep in a big stockpile: the nearest open tile outside it
		for(var/turf/T in range(8, src))
			if(P.RemasterInStoreArea(T) || T.density || (locate(/mob/Monsters) in T) || RemasterWalkable(T, src) != 1) continue
			var/k = get_dist(T, src)
			if(k < bd)
				bd = k
				best = T
	if(!best) return 0
	rm_jz_clear = best
	remaster_work_destination = best
	destination = best
	remaster_work_status = "Stepping away from the [S == P.RemasterStockpile() ? "stockpile" : "store"] to wait"
	return 1

// --- Waiting for the farm to call (J2) ---------------------------------------------------------------------------
// The user, 2026-10-25: "build J2 so zones and resources wake their workers when work is ready, and idle workers stop
// being checked". A farmer on the job board with nothing to do (crops still growing, no seeds, or seeds in winter) waits
// for its farm to call it: its step returns at once, with no looks. Before, each looked over its farm and then every
// item on every store for seeds every 0.5-2 s: at 2,000 workers the farmers took 2 s of every second (6 ms a look among
// 11,000 stored stones; reports/jobs/j2-design.md). It's woken by a plant in its farm ripening, seeds coming onto a store,
// the season turning, its row changing, being moved from where it waited, and at the latest a minute after it began.
#define RM_JZ_WAIT_MAX 600
mob/Monsters/var/tmp/rm_jz_wait              // the row it waits on, or null
mob/Monsters/var/tmp/rm_jz_wait_at = 0
mob/Monsters/var/tmp/turf/rm_jz_wait_loc
Player/var/tmp/list/rm_jz_waiting           // row id -> its waiting workers, oldest first (one woken meanwhile is skipped)
Player/var/tmp/rm_jz_season                 // the season at the last board pass
Player/var/tmp/rm_jz_seeds_was = 0          // seeds on a store at the last board pass
Player/var/tmp/list/rm_jz_seeds_c           // list(any seeds on a store, when looked)
var/list/rm_jz_wait_players = list()        // the players with someone waiting (a crop ripening looks only at theirs)

Player/proc/RmJzWait(mob/Monsters/M, id)
	M.rm_jz_wait = id
	M.rm_jz_wait_at = world.time
	M.rm_jz_wait_loc = M.loc
	if(!rm_jz_waiting) rm_jz_waiting = list()
	var/list/L = rm_jz_waiting[id]
	if(!L)
		L = list()
		rm_jz_waiting[id] = L
	L += M
	if(!(src in rm_jz_wait_players)) rm_jz_wait_players += src

// Wakes up to n of the row's waiting workers (0: all), oldest first; with older, only those waiting at least that long.
Player/proc/RmJzWakeRow(id, n = 0, older = 0)
	var/list/L = rm_jz_waiting && rm_jz_waiting[id]
	if(!length(L)) return
	var/woke = 0
	var/i = 1
	for(, i <= length(L), i++)
		var/mob/Monsters/M = L[i]
		if(!M || M.rm_jz_wait != id) continue
		if(older && world.time - M.rm_jz_wait_at < older) break
		M.rm_jz_wait = null
		if(n && ++woke >= n)
			i++
			break
	L.Cut(1, min(i, length(L) + 1))

// Any seeds a farmer plants (tomato, grape) lying on a store, looked at most every 2 s: the farmer's own look
// (FoodRoles.dm) walks every item on every store. Any lying there counts (its look takes from the main stockpile
// without asking whose), so this never skips a look that would have found some.
Player/proc/RmJzSeedsStored()
	if(rm_jz_seeds_c && world.time - rm_jz_seeds_c[2] < RM_JZ_EVERY) return rm_jz_seeds_c[1]
	var/any = 0
	for(var/turf/T in RemasterStores())
		for(var/obj/Items/Seeds/S in range(1, T)) if(isturf(S.loc) && (istype(S, /obj/Items/Seeds/TomatoSeed) || istype(S, /obj/Items/Seeds/GrapeSeed)))
			any = 1
			break
		if(any) break
	rm_jz_seeds_c = list(any, world.time)
	return any

// Each board pass (every 2 s): seeds coming onto a store or the season turning wakes every waiting worker; any that has
// waited a minute is woken to look again (for what doesn't call it yet).
Player/proc/RmJzWakeTick()
	var/seeds = RmJzSeedsStored()
	var/all = (seeds && !rm_jz_seeds_was) || (rm_jz_season && rm_jz_season != Season)
	rm_jz_seeds_was = seeds
	rm_jz_season = Season
	var/left = 0
	for(var/id in rm_jz_waiting)
		RmJzWakeRow(id, 0, all ? 0 : RM_JZ_WAIT_MAX)
		left += length(rm_jz_waiting[id])
	if(!left)
		rm_jz_waiting = null
		rm_jz_wait_players -= src

// A plant ripening calls one waiting farmer of each farm whose look reaches it (the farm step's REMASTER_FOOD_AREA round
// the zone's middle).
obj/Items/Plants/PlantRegen()
	var/was = Content
	. = ..()
	if(was < 2 && Content >= 2 && isturf(loc) && length(rm_jz_wait_players)) RmJzCropRipe(src)

proc/RmJzCropRipe(obj/Items/Plants/G)
	for(var/Player/P in rm_jz_wait_players) if(!G.Owner || G.Owner == P)
		for(var/list/Z in P.rm_jz) if(Z["kind"] == "farm" && Z["z"] == G.z && P.rm_jz_waiting && length(P.rm_jz_waiting[Z["id"]]))
			if(max(abs(G.x - round((Z["x0"] + Z["x1"]) / 2)), abs(G.y - round((Z["y0"] + Z["y1"]) / 2))) <= REMASTER_FOOD_AREA) P.RmJzWakeRow(Z["id"], 1)

// A farmer with nothing to do away from its farm walks to it to wait there (1 while it goes): ~400 farmers waiting where
// they started made a wall round the village's stockpile at 2,000 workers (tests/gather_score.dm GsRun2000A). Within 2
// tiles of the farm it's there; a farmer that can't get there in RM_JZ_GO_MAX waits where it is.
#define RM_JZ_GO_MAX 300
mob/Monsters/var/tmp/rm_jz_going = 0        // when it set off for its farm (0: not going)

mob/Monsters/proc/RmJzToFarm(list/Z)
	if(z != Z["z"]) return 0
	if(x >= Z["x0"] - 2 && x <= Z["x1"] + 2 && y >= Z["y0"] - 2 && y <= Z["y1"] + 2)
		if(rm_jz_going)
			rm_jz_going = 0
			if(destination == remaster_work_destination) destination = null
			remaster_work_destination = null
		return 0
	if(rm_jz_going)
		var/late = world.time - rm_jz_going >= RM_JZ_GO_MAX
		if(!late && destination && destination == remaster_work_destination) return 1   // on its way
		rm_jz_going = 0
		if(destination == remaster_work_destination) destination = null
		remaster_work_destination = null
		if(late) return 0           // it couldn't get there: it waits where it is
	// the nearest open tile of the farm with nobody on it, in rings round the farm's nearest point
	var/cx = clamp(x, Z["x0"], Z["x1"])
	var/cy = clamp(y, Z["y0"], Z["y1"])
	for(var/r = 0, r <= 4, r++)
		for(var/turf/T in block(locate(max(Z["x0"], cx - r), max(Z["y0"], cy - r), z), locate(min(Z["x1"], cx + r), min(Z["y1"], cy + r), z)))
			if(T.density || (locate(/mob/Monsters) in T) || RemasterWalkable(T, src) != 1) continue
			destination = T
			remaster_work_destination = T
			rm_jz_going = world.time
			remaster_work_status = "[Z["name"]]: going to the farm to wait for the crops"
			return 1
	return 0

// --- A yard by each wood and stone zone ----------------------------------------------------------------------------
// The user, 2026-10-25: "a yard by each wood and stone zone". A wood or stone zone painted gets its own yard, with no
// click: a stockpile of its good (the Zones list's Wood pile / Stone yard filters) 2 tiles out from the zone's edge
// nearest the main stockpile, 3 tiles deep and 3 long for each of its cells (Zones.dm RemasterZoneCells): one cell for
// every 40 workers the zone can take, 2 to 4. Its carriers' trips stay short and never cross the village. None when a
// store that takes the good is already within RM_YARD_NEAR of the zone (the main stockpile counts). A yard is a
// drop-off: goods are never moved out of the main stockpile into one (Zones.dm RemasterZoneKeep). Removing the zone
// leaves its yard, with what's on it.
#define RM_YARD_NEAR 8
var/rm_jz_auto_yards = 1     // 0: none made (tests/jobs_test.dm keeps the board's own layout; the yards have tests/yard_test.dm)
Player/RmJzAdd(kind, x0, y0, x1, y1, z)
	. = ..()
	if(. && rm_jz_auto_yards && (kind in list("wood", "stone", "gather"))) RmJzAutoYard(.)

Player/proc/RmJzAutoYard(list/Z)
	var/good = Z["kind"] == "gather" ? "any" : Z["kind"]   // a gather zone's yard takes anything
	var/zz = Z["z"]
	for(var/turf/T in RemasterStores()) if(T.z == zz && T.x >= Z["x0"] - RM_YARD_NEAR && T.x <= Z["x1"] + RM_YARD_NEAR && T.y >= Z["y0"] - RM_YARD_NEAR && T.y <= Z["y1"] + RM_YARD_NEAR)
		var/list/ZZ = RemasterZoneOfCell(T)
		if(!ZZ || (ZZ["filter"] in list("any", good)) || (good == "stone" && ZZ["filter"] == "mining")) return null
	var/turf/S = RemasterStockpile()
	var/cx = S && S.z == zz ? S.x : round((Z["x0"] + Z["x1"]) / 2)
	var/cy = S && S.z == zz ? S.y : Z["y0"] - RM_YARD_NEAR - 1        // no stockpile on this level: below the zone
	var/dx = cx < Z["x0"] ? Z["x0"] - cx : cx > Z["x1"] ? cx - Z["x1"] : 0
	var/dy = cy < Z["y0"] ? Z["y0"] - cy : cy > Z["y1"] ? cy - Z["y1"] : 0
	if(!dx && !dy) return null       // the stockpile is inside the zone
	var/len = clamp(round(RmJzCap(Z) / 40) + 1, 2, 4) * 3
	// the edge nearest the stockpile; when its strip would lie on another work zone (two zones side by side: the yard
	// was painted inside the neighbour, over its trees, polish-zones 10-26), the free edge nearest the stockpile
	var/first = dx >= dy ? (cx < Z["x0"] ? WEST : EAST) : (cy < Z["y0"] ? SOUTH : NORTH)
	var/list/R = RmJzYardRect(Z, first, cx, cy, len)
	if(R && RmJzOnWork(R, zz))
		var/list/free
		var/fd = 1#INF
		for(var/e in list(WEST, EAST, SOUTH, NORTH)) if(e != first)
			var/list/Q = RmJzYardRect(Z, e, cx, cy, len)
			if(!Q || RmJzOnWork(Q, zz)) continue
			var/d = max(abs((Q[1] + Q[3]) / 2 - cx), abs((Q[2] + Q[4]) / 2 - cy))
			if(d < fd)
				fd = d
				free = Q
		if(free) R = free      // none free: where it was (what it holds is stored all the same, RmJzStored)
	if(!R) return null
	var/ax = R[1]
	var/ay = R[2]
	var/bx = R[3]
	var/by = R[4]
	var/list/Y = RmJzAdd("stock", ax, ay, bx, by, zz)
	if(!Y) return null
	// its row goes just before the zone's, so the zone just painted is still the board's last row
	rm_jz -= list(Y)
	rm_jz.Insert(rm_jz.Find(Z), list(Y))
	Y["name"] = "[Z["name"]] yard"
	Y["yard_of"] = Z["id"]
	if(remaster_zones) for(var/list/E in remaster_zones) if(E["id"] == Y["store"])
		E["name"] = Y["name"]
		E["filter"] = good
		E["yard"] = Z["id"]
	RemasterNotice("[Y["name"]]: a [good == "wood" ? "wood pile" : "stone yard"] beside [Z["name"]] for its loads ([bx - ax + 1] by [by - ay + 1] tiles).")
	return Y

// A yard's strip along one edge of zone Z (WEST, EAST, SOUTH or NORTH), 2 tiles out and 3 deep, centred on the point of
// the edge nearest the stockpile at cx,cy: list(x0, y0, x1, y1), or null off the map.
proc/RmJzYardRect(list/Z, edge, cx, cy, len)
	var/ax
	var/ay
	var/bx
	var/by
	if(edge == WEST || edge == EAST)
		ax = edge == WEST ? Z["x0"] - 4 : Z["x1"] + 2
		bx = ax + 2
		ay = clamp(clamp(cy, Z["y0"], Z["y1"]) - round(len / 2), Z["y0"], max(Z["y0"], Z["y1"] - len + 1))
		by = ay + len - 1
	else
		ay = edge == SOUTH ? Z["y0"] - 4 : Z["y1"] + 2
		by = ay + 2
		ax = clamp(clamp(cx, Z["x0"], Z["x1"]) - round(len / 2), Z["x0"], max(Z["x0"], Z["x1"] - len + 1))
		bx = ax + len - 1
	if(ax < 1 || ay < 1 || bx > world.maxx || by > world.maxy) return null
	return list(ax, ay, bx, by)

// The rectangle R (list(x0, y0, x1, y1)) on level z lies on one of the realm's work zones or plans.
Player/proc/RmJzOnWork(list/R, z)
	for(var/list/X in rm_jz) if(((RmJzIsZone(X) && X["kind"] != "stock") || RmPlanKind(X["kind"])) && X["z"] == z && R[1] <= X["x1"] && R[3] >= X["x0"] && R[2] <= X["y1"] && R[4] >= X["y0"]) return 1
	return 0

// --- Fishing zones (the user, 2026-10-25: "lets add fishery lodges or workzones") -------------------------------
#define RM_JZ_FISH_PER_SPOT 1      // fishers to a spot: it's fished from the one shore tile beside it (Fishing.dm RemasterShoreLand)
mob/Monsters/var/tmp/rm_jz_fishing = 0      // its spot was given by its fishing row (left with the row)

// The fishing spots in the zone (they drift along the shore every few minutes, Fishing.dm).
Player/proc/RmJzFishSpots(list/Z)
	. = list()
	for(var/obj/RemasterFishSpot/S in rm_fish_spots) if(S.z == Z["z"] && S.x >= Z["x0"] && S.x <= Z["x1"] && S.y >= Z["y0"] && S.y <= Z["y1"]) . += S

// A spot drifting (or placed) into a zone calls one of its waiting fishers.
proc/RmJzFishSpotMoved(obj/RemasterFishSpot/S)
	if(!S || !isturf(S.loc)) return
	for(var/Player/P in rm_jz_wait_players) for(var/list/Z in P.rm_jz) if(Z["kind"] == "fish" && Z["z"] == S.z && S.x >= Z["x0"] && S.x <= Z["x1"] && S.y >= Z["y0"] && S.y <= Z["y1"])
		P.RmJzWakeRow(Z["id"], RM_JZ_FISH_PER_SPOT)

mob/Monsters/proc/RmJzFishStep(Player/P, list/Z)
	remaster_area_x = round((Z["x0"] + Z["x1"]) / 2)
	remaster_area_y = round((Z["y0"] + Z["y1"]) / 2)
	remaster_area_z = Z["z"]
	remaster_auto_unload = 1
	if(z != Z["z"])
		remaster_work_status = "[Z["name"]]: on another level"
		return
	// 1. a load of fish meat: in to the nearest food store (a stall or pot first, FoodSupply.dm)
	var/list/food = RemasterCarriedFood()
	if(length(food) >= REMASTER_FOOD_CARRY)
		RmJzStopFishing()          // the orders tick would walk it back to its spot (Orders.dm: any unit with a spot fishes)
		RemasterServeOrStore(P, food, "fish")
		remaster_work_status = "[Z["name"]]: [remaster_work_status]"
		return
	// 2. a catch lying in the zone: cleaned into meat (a knife, or teeth for a meat-eater) and the meat lifted
	var/mob/Body/B
	var/bd = 1#INF
	for(var/mob/Body/X in range(1, src)) if(isturf(X.loc) && X.Race == "Fish" && isnull(X.suffix))
		var/d = get_dist(src, X)
		if(d < bd)
			B = X
			bd = d
	if(B && (RemasterCanButcher() || RemasterHunterKnife()))
		if(!RemasterCanButcher()) RemasterHunterWield("knife")
		if(PickUpItem(B) || ForcePickUpItem(B))
			TearMeat(B)
			for(var/obj/Items/Food/Meat/M in range(1, src)) if(isturf(M.loc) && PickUpItem(M)) P.RmJzCountOut(Z["id"])   // the row's +N a minute (it read +0 while it fed the village)
			remaster_work_status = "[Z["name"]]: cleaned the catch"
			return
	// 3. fishing: its spot, while the spot is still in the zone and it can fish it
	var/list/spots = P.RmJzFishSpots(Z)
	var/obj/RemasterFishSpot/S = remaster_fish_spot
	if(S && (!(S in spots) || !RemasterFishMethod(S))) S = null
	if(!S)
		// the nearest spot it can fish with fewer than RM_JZ_FISH_PER_SPOT of its row on it
		var/list/members = P.RmJzMembers(Z["id"])
		bd = 1#INF
		var/fishable = 0
		for(var/obj/RemasterFishSpot/X in spots) if(RemasterFishMethod(X))
			fishable++
			var/n = 0
			for(var/mob/Monsters/M in members) if(M != src && M.remaster_fish_spot == X) n++
			if(n >= RM_JZ_FISH_PER_SPOT) continue
			var/d = get_dist(src, X)
			if(d < bd)
				S = X
				bd = d
		if(!S)
			remaster_fish_spot = null
			rm_jz_fishing = 0
			if(!fishable && length(spots))
				// none it can fish with what it carries: a tool from a store, or say what's needed
				if(RmJzFetchFishTool(P, spots)) return
				remaster_work_status = "[Z["name"]]: needs [jointext(RemasterFishTools(spots[1]:kind), " or ")] (Carpentry; a harpoon at the Forge)"
				return
			if(length(food))      // nothing to fish now: what it has goes in first
				RmJzStopFishing()
				RemasterServeOrStore(P, food, "fish")
				remaster_work_status = "[Z["name"]]: [remaster_work_status]"
				return
			remaster_work_status = "[Z["name"]]: every fishing spot is taken"
			if(!RmJzClearStore(P, 1) && !destination) P.RmJzWait(src, Z["id"])   // till a spot drifts in (RmJzFishSpotMoved)
			return
		remaster_fish_spot = S
		rm_jz_fishing = 1
		remaster_fish_at = world.time + 10
	RemasterFishTick()
	if(destination) remaster_work_destination = destination   // its walk to the shore is its work, not a player's order (the settlement pass)
	remaster_work_status = "[Z["name"]]: [remaster_work_status]"

mob/Monsters/proc/RmJzStopFishing()
	if(!rm_jz_fishing) return
	rm_jz_fishing = 0
	remaster_fish_spot = null

// The fishing tool for one of these spots, from the nearest store holding one: 1 while it goes or as it takes it.
mob/Monsters/proc/RmJzFetchFishTool(Player/P, list/spots)
	var/list/want = list()
	for(var/obj/RemasterFishSpot/X in spots) for(var/m in rm_fish[X.kind]) if(m != "hand") want[m] = 1
	var/obj/Items/RemasterTools/best
	var/bd = 1#INF
	for(var/turf/T in P.RemasterStores()) if(T.z == z && get_dist(T, src) < bd)
		for(var/obj/Items/RemasterTools/I in range(1, T)) if(isturf(I.loc) && want[I.remaster_method] && P.RemasterMayCollect(I))
			best = I
			bd = get_dist(T, src)
			break
	if(!best) return 0
	if(get_dist(src, best) > 1)
		destination = best.loc
		remaster_work_destination = best.loc
		remaster_work_status = "Fetching \a [lowertext(best.name)] from the stockpile"
		return 1
	if(PickUpItem(best)) remaster_work_status = "Took \a [lowertext(best.name)] from the stockpile"
	return 1

// --- The worker's step (from RemasterSettlementTick, for the Any work role) ---------------------------------------
mob/Monsters/proc/RmJobStep(Player/P, list/RESERVED)
	var/list/Z = rm_jz_id ? P.RmJz(rm_jz_id) : null
	if(rm_jz_wait)   // waiting for its farm to call it (above): still its row, and where it began waiting
		if(Z && rm_jz_wait == Z["id"] && loc == rm_jz_wait_loc) return
		rm_jz_wait = null
	if(rm_ch_aside && RmChAsideBack(P)) return   // tools set down to carry a heavy piece (Heavy pieces, below)
	// off a make row with goods it made or materials still in the bag (Board workers put them back, Board.dm): to the store
	if(!remaster_board_claim && (remaster_station_goods || remaster_station_mats) && RemasterStationPutBack(P)) return
	// a claim on a Bulletin board order goes with that order's make row: off it (freed, moved, taken by a High row) it's let go
	if(remaster_board_claim && (!Z || Z["order"] != remaster_board_claim)) RemasterBoardRelease()
	if(!Z)
		if(rm_jz_id) rm_jz_id = null
		// already waiting, with nothing of work's left on it: stopping work again would change nothing
		if(!remaster_work_destination && !remaster_work_item && !remaster_work_position && !remaster_work_since && !remaster_work_retry && remaster_work_status == "Job board: free, waiting for a job" && !(isturf(loc) && P.RemasterInStoreArea(loc))) return
		// newly free (the checks above keep a waiting one at no cost): never waiting beside a store (below), and goods
		// still in the bag go in first
		if(RmJzClearStore(P, 1)) return     // unthrottled: once it waits, nothing looks again
		if(RemasterDeliveryWeight(P) > 0 && RemasterBeginDelivery(null)) return
		RemasterStopWork()
		remaster_work_status = "Job board: free, waiting for a job"
		return
	switch(Z["kind"])
		if("wood", "stone", "gather")
			var/good = Z["kind"]
			var/turf/stock = P.RemasterStockpile()
			rm_jz_block = 0
			if((!stock || stock.z != z || stock.density) && !P.RemasterLoadStopOn(src))
				remaster_work_status = "[Z["name"]]: no drop-off on this level"
				rm_jz_block = 1
				return
			if(good == "gather" ? !P.RemasterStockAcceptsKind("wood") && !P.RemasterStockAcceptsKind("stone") : !P.RemasterStockAcceptsKind(good))
				remaster_work_status = "[Z["name"]]: the drop-off doesn't take [good == "gather" ? "wood or stone" : good]"
				rm_jz_block = 2
				return
			if(z != Z["z"])
				remaster_work_status = "[Z["name"]]: on another level"
				rm_jz_block = 3
				return
			if(RmJzPickUpStep(P, Z)) return     // pieces lying in the zone first (the user, 2026-10-24)
			var/turf/T = P.RmJzTake(Z, src)
			if(!T && RmJzRegrowStep(P, Z)) return   // nothing grown to cut: its stumps and saplings (the Tend redo)
			if(!T)
				if(RemasterDeliveryWeight(P) > 0) RemasterBeginDelivery(null)
				else if(!RmJzClearStore(P, 1))
					var/list/G = P.rm_jz_regrow ? P.rm_jz_regrow[Z["id"]] : null
					remaster_work_status = length(G) ? "[Z["name"]]: its saplings are tended; waiting for them to grow" : "[Z["name"]]: nothing left to [good == "wood" ? "cut" : good == "gather" ? "gather" : "dig"]"
					if(!destination) P.RmJzWait(src, Z["id"])   // till its zone calls it (J2: targets back, a face opened, a piece lying)
				return
			var/datum/remaster_order/O = new
			O.issuer = P
			O.target = T
			O.kind = RemasterOrderKind(T)
			if(O.kind == "Mine" && T.z == GROUND_LAYER && RemasterIsMountain(T)) O.block = RmJzFaceBlock(T)   // a mountain face from the top of reach down
			O.automatic = 1
			O.rm_jz = 1
			if(!O.kind) return
			remaster_auto_unload = 1
			RemasterSuspendControllers()
			remaster_active = O
			RemasterStartOrder(O)
			RemasterOrderTick()
		if("farm")
			if(rm_jz_going && RmJzToFarm(Z)) return    // on its way to wait at its farm: nothing to look at on the way
			// the farmer's own steps round the zone's middle
			remaster_area_x = round((Z["x0"] + Z["x1"]) / 2)
			remaster_area_y = round((Z["y0"] + Z["y1"]) / 2)
			remaster_area_z = Z["z"]
			remaster_auto_unload = 1
			remaster_job = "farmer"
			RemasterFoodTick(P)
			remaster_job = "any"
			// waiting for crops (or for spring): at its farm, never in the village or beside a store, where carriers put their
			// loads down (RmJzClearStore); then it waits for its farm to call it (J2, above)
			if(findtext("[remaster_work_status]", "Waiting for") == 1 && !RmJzToFarm(Z) && !RmJzClearStore(P, 1))
				// a walk left from its last task (a tile it couldn't step onto, a friend on it) would hold it stepping for good
				if(destination && destination == remaster_work_destination)
					destination = null
					remaster_work_destination = null
				if(!destination) P.RmJzWait(src, Z["id"])
			if(findtext("[remaster_work_status]", "[Z["name"]]: ") != 1) remaster_work_status = "[Z["name"]]: [remaster_work_status]"   // RmJzToFarm's own line has the name already ("Farm 1: Farm 1: going to the farm")
		if("fish")
			RmJzFishStep(P, Z)
		if("make")
			RmJzMakeStep(P, Z, RESERVED)
		if("dig", "build")
			RmPlanStep(P, Z)       // a dig or build plan (Plans.dm)

// A mountain column's block a zone worker takes from the ground: the highest it reaches (block 2, then 1, then the floor
// block), so a stone zone cuts a mountain face back three blocks high from the top down, the way a click on the face
// mines the block pointed at (Gather.dm). It took each column's floor block only: a one-block crawl under the rest, and
// the zone stopped with 556 of its 676 blocks still standing (polish-zones 10-26). Blocks above a worker's reach stay for
// Plan mode, which climbs to them. Null: the floor block, as an order with no block.
proc/RmJzFaceBlock(turf/T)
	for(var/k = RM_REACH_UP, k >= 1, k--) if(RemasterBlockThere(T, k)) return k
	return null

// A stone or Gather zone's rock left overhead, out of a worker's reach from the ground (tunnel roofs over its opened
// tiles): the row says so when nothing else is left, instead of "Nothing left to work" under a standing mountain.
Player/proc/RmJzAbove(list/Z)
	if(!(Z["kind"] in list("stone", "gather"))) return 0
	. = 0
	for(var/turf/T in RmJzRect(Z)) if(!T.density && T.remaster_roof > 0) . += T.remaster_roof

// --- Running totals ----------------------------------------------------------------------------------------------
Player/proc/RmJzMembers(id)
	if(!rm_jz_members) rm_jz_members = list()
	var/list/L = rm_jz_members[id]
	if(!L)
		L = list()
		rm_jz_members[id] = L
	return L

// Still one of ours, alive, here (deleted, dead or captured units drop out when met).
Player/proc/RmJzValid(mob/Monsters/M)
	return M && M.loc && M.Owner == src && M.HP > 0 && !M.GoingToDie

// A 16-tile cell's number, or 0 off the map: numbers, not text keys, since a search reads many cells.
Player/proc/RmJzCellAt(cx, cy, z)
	if(cx < 0 || cy < 0 || cx >= rm_jz_cw || cy >= rm_jz_ch || z < 1 || z > world.maxz) return 0
	return 1 + cx + cy * rm_jz_cw + (z - 1) * rm_jz_cw * rm_jz_ch

Player/proc/RmJzCellsReset()
	rm_jz_cw = round(world.maxx / RM_JZ_CELL) + 1
	rm_jz_ch = round(world.maxy / RM_JZ_CELL) + 1
	rm_jz_cells = new /list(rm_jz_cw * rm_jz_ch * world.maxz)

Player/proc/RmJzFreeAdd(mob/Monsters/M)
	if(!rm_jz_cells || rm_jz_cw != round(world.maxx / RM_JZ_CELL) + 1 || rm_jz_ch != round(world.maxy / RM_JZ_CELL) + 1)
		if(rm_jz_cells) rm_jz_ready = 0     // the map changed size: the next pass recounts into the new grid
		RmJzCellsReset()
	if(length(rm_jz_cells) < rm_jz_cw * rm_jz_ch * world.maxz) rm_jz_cells.len = rm_jz_cw * rm_jz_ch * world.maxz   // a new level
	if(M.rm_jz_free_in) return
	var/turf/T = RemasterGetTurf(M)
	if(!T) return
	var/k = RmJzCellAt(round(T.x / RM_JZ_CELL), round(T.y / RM_JZ_CELL), T.z)
	if(!k) return
	M.rm_jz_free_in = 1
	rm_jz_nfree++
	M.rm_jz_cell = k
	M.rm_jz_cz = "[T.z]"
	if(!rm_jz_zfree) rm_jz_zfree = list()
	rm_jz_zfree[M.rm_jz_cz] = rm_jz_zfree[M.rm_jz_cz] + 1
	var/list/C = rm_jz_cells[M.rm_jz_cell]
	if(!C)
		C = list()
		rm_jz_cells[M.rm_jz_cell] = C
	C += M

Player/proc/RmJzFreeDrop(mob/Monsters/M)
	if(!M || !M.rm_jz_free_in) return
	M.rm_jz_free_in = 0
	rm_jz_nfree = max(0, rm_jz_nfree - 1)
	var/list/C = rm_jz_cells && M.rm_jz_cell && M.rm_jz_cell <= length(rm_jz_cells) ? rm_jz_cells[M.rm_jz_cell] : null
	if(C) C -= M
	if(rm_jz_zfree && M.rm_jz_cz) rm_jz_zfree[M.rm_jz_cz] = max(0, rm_jz_zfree[M.rm_jz_cz] - 1)
	M.rm_jz_cell = null
	M.rm_jz_cz = null

Player/proc/RmJobJoin(mob/Monsters/M, list/Z)
	RmJzFreeDrop(M)
	if(M.rm_jz_id && M.rm_jz_id != Z["id"])
		var/list/was = RmJzMembers(M.rm_jz_id)
		was -= M
	var/here = M.rm_jz_id == Z["id"]
	M.rm_jz_id = Z["id"]
	M.rm_jz_since = world.time
	M.rm_jz_block = 0
	M.rm_jz_wait = null
	var/list/now = RmJzMembers(Z["id"])
	if(!here) now += M      // no search of the whole row: a unit that joins isn't on it
	M.RemasterStopWork()
	if(Z["kind"] == "builders") M.remaster_job = "builder"
	else if(Z["kind"] == "haulers")
		var/turf/S = RemasterStockpile()
		M.remaster_job = "hauler"
		if(S)
			M.remaster_area_x = S.x; M.remaster_area_y = S.y; M.remaster_area_z = S.z
		M.remaster_auto_unload = 1
	else M.remaster_job = "any"
	M.remaster_work_status = "[Z["name"]]: taking up the work"

// The units selected when the Gather bar's drag began start on Z: on Manual they go on the job board, as "put on the job
// board" does. queued (Add tasks, or Shift): their current orders first; a worker with orders waits on its row until
// they're done (RemasterSettlementTick), so Manual ones only change role, orders kept.
Player/var/tmp/list/rm_gz_pending   // a Gather bar drag under way: list("queued", "units"), till its paint makes the row
Player/proc/RmJzJoinSelected(list/Z, queued = 0, list/units = null)
	var/joined = 0
	for(var/mob/Monsters/M in (units || Selected)) if(!Rm3DGone(M) && M.Owner == src && RmJzValid(M) && !M.Wagon && !M.Critter && !M.Egg)
		if(M.remaster_job == "manual" && !length(M.remaster_production))
			if(queued && M.RemasterHasOrder())
				M.remaster_job = "any"
				M.remaster_role_paused = 0
				M.RmJobRoleChanged("manual")
			else M.RemasterAssignJob("any")
		if(M.remaster_job != "any") continue
		RmJobJoin(M, Z)
		joined++
	if(joined > Z["want"]) Z["want"] = joined
	rm_jz_next = 0
	return joined

// --- Regrowing, the zone's own work (the owner's Tend redo, 10-26) ------------------------------------------------
// Harvest takes everything (Yield.dm RemasterTendsLiving). A tree felled inside one of the realm's wood or gather zones
// leaves a stump (RemasterTreeFell); with no grown tree to cut, the zone's workers plant a sapling on each stump, then
// tend the saplings: a visit adds RM_TEND_GROW health, once in RM_TEND_AGAIN a sapling (at most double the natural 4
// every 30 s). Grown, a sapling is a tree to cut again (Yield.dm RemasterYieldGrow). One worker a stump or sapling.
#define RM_REGROW_WORK 3          // steps beside it (each 0.5-2 s) to plant a sapling or tend one
#define RM_REGROW_SAPLINGS 10     // saplings one worker looks after
#define RM_REGROW_STUMPS 3        // stumps one worker plants (a few seconds each)
#define RM_SAPLING_HP 10          // a sapling's health; grown at RemasterTreeMax (250): ~31 min untended
#define RM_TEND_GROW 20           // a tending visit's growth...
#define RM_TEND_AGAIN 1500        // ...at most once in 150 s a sapling
var/rm_zone_regrow = 1        // 0: zones don't regrow either: nothing grows back (living resources off)
Player/var/tmp/list/rm_jz_regrow             // zone id -> its stumps and saplings (RmJzBuildTargets)
turf/var/tmp/rm_tended_at = -100000
turf/var/tmp/mob/Monsters/rm_rg_by           // the worker on its way to it
mob/Monsters/var/tmp/turf/rm_rg_target
mob/Monsters/var/tmp/rm_rg_steps = 0

// A tree just felled at T: inside a wood or gather zone of this realm, a stump to replant.
Player/proc/RmJzStumpAt(turf/T)
	if(!rm_zone_regrow || !T || T.density || !rm_jz) return
	for(var/list/Z in rm_jz) if((Z["kind"] in list("wood", "gather")) && Z["z"] == T.z && T.x >= Z["x0"] && T.x <= Z["x1"] && T.y >= Z["y0"] && T.y <= Z["y1"])
		T.remaster_tend = RM_TEND_STUMP
		remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1
		// onto its regrow list as it is, and one waiting worker called (no look over the whole zone for one stump: with
		// 2,000 workers felling, that was most of the regrowing's cost)
		if(!rm_jz_regrow) rm_jz_regrow = list()
		var/list/G = rm_jz_regrow[Z["id"]]
		if(!G)
			G = list()
			rm_jz_regrow[Z["id"]] = G
		G += T
		if(rm_jz_waiting && length(rm_jz_waiting[Z["id"]])) RmJzWakeRow(Z["id"], 1)
		return

// The workers its regrowing wants: one for each RM_REGROW_STUMPS stumps to plant, one for each RM_REGROW_SAPLINGS
// saplings to tend (a sapling wants a visit once in 150 s, so one worker keeps up with several; the rest go back to the
// board).
Player/proc/RmJzRegrowLeft(list/Z)
	if(!(Z["kind"] in list("wood", "gather"))) return 0
	var/list/G = rm_jz_regrow ? rm_jz_regrow[Z["id"]] : null
	if(!length(G)) return 0
	var/stumps = 0
	for(var/turf/T in G) if(T.remaster_tend == RM_TEND_STUMP) stumps++
	return round((stumps + RM_REGROW_STUMPS - 1) / RM_REGROW_STUMPS) + round((length(G) - stumps + RM_REGROW_SAPLINGS - 1) / RM_REGROW_SAPLINGS)

// A stump becomes a sapling: a tree tile, small, that grows as a tree does.
Player/proc/RmJzPlant(turf/T)
	if(!T || T.density || T.remaster_tend != RM_TEND_STUMP || (locate(/mob/Monsters) in T) || RmJzPiecesOn(T)) return 0
	T.Tree = 1
	T.IsWood = 1
	T.density = 1
	T.opacity = 0
	T.name = "sapling"
	T.remaster_tree_max = RM_TREE_HP
	T.HP = RM_SAPLING_HP
	T.remaster_tend = RM_TEND_SAPLING
	T.remaster_yield_at = world.time - RM_TREE_REST    // it grows from now
	rm_yield_known[T] = 1
	remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1
	return 1

// Logs or stone lying on T, which the zone's workers lift before a sapling goes in. Seeds and other things don't count:
// nobody lifts those, so they would keep a stump bare for good (a felled tree drops its seeds at its feller's feet).
proc/RmJzPiecesOn(turf/T)
	for(var/obj/Items/I in T) if(isnull(I.suffix) && RemasterResourceKind(I)) return 1
	return 0

// How many stand on stump T besides its planter M. An idle one of the realm's is asked to step aside (an idle worker
// stands wherever its last job left it, and a sapling can't go in under it).
proc/RmJzStepOff(turf/T, mob/Monsters/M, Player/P)
	var/n = 0
	for(var/mob/Monsters/O in T) if(O != M)
		n++
		if(O.Owner != P || O.destination) continue
		for(var/d in list(NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST))
			var/turf/N = get_step(T, d)
			if(N && !N.density && N.remaster_tend != RM_TEND_STUMP && RemasterWalkable(N, O) == 1)
				O.destination = N
				O.RmWalkSoon()
				break
	return n

// A stump to plant, or a sapling due a visit, inside zone Z.
proc/RmJzRegrowWants(turf/T, list/Z)
	if(!T || T.z != Z["z"] || T.x < Z["x0"] || T.x > Z["x1"] || T.y < Z["y0"] || T.y > Z["y1"]) return 0
	if(T.remaster_tend == RM_TEND_STUMP) return !T.density
	return T.remaster_tend == RM_TEND_SAPLING && T.density && T.Tree && world.time - T.rm_tended_at >= RM_TEND_AGAIN

// One step of a zone worker with nothing grown to cut: the nearest stump to plant, else the nearest sapling ready to be
// tended; 1 while it does (or walks to) that.
mob/Monsters/proc/RmJzRegrowStep(Player/P, list/Z)
	if(!(Z["kind"] in list("wood", "gather"))) return 0
	var/list/G = P.rm_jz_regrow ? P.rm_jz_regrow[Z["id"]] : null
	if(!length(G)) return 0
	// the one it already picked, while that still wants it: the list is looked through once a job, not every step
	var/turf/best = rm_rg_target
	if(best && (best.rm_rg_by != src || !RmJzRegrowWants(best, Z))) best = null
	var/bd = best ? 0 : 1#INF
	if(!best) for(var/k = length(G), k >= 1, k--)
		var/turf/T = G[k]
		if(T.remaster_tend == RM_TEND_SAPLING && !T.density) T.remaster_tend = RM_TEND_STUMP   // knocked down: plant it again
		var/stump = T.remaster_tend == RM_TEND_STUMP && !T.density
		var/sap = T.remaster_tend == RM_TEND_SAPLING && T.density && T.Tree
		if(!stump && !sap)
			G.Cut(k, k + 1)
			continue
		if(sap && world.time - T.rm_tended_at < RM_TEND_AGAIN) continue
		var/mob/Monsters/W = T.rm_rg_by
		if(W && W != src && !Rm3DGone(W) && W.rm_rg_target == T) continue
		if(stump && RmJzPiecesOn(T)) continue          // the pieces lying there are lifted first
		var/d = abs(T.x - x) + abs(T.y - y) + (stump ? 0 : 6)   // stumps first
		if(d < bd)
			bd = d
			best = T
	if(!best) return 0
	if(rm_rg_target != best) rm_rg_steps = 0
	rm_rg_target = best
	best.rm_rg_by = src
	if(loc == best)    // standing on the stump: off it first
		for(var/d in list(NORTH, SOUTH, EAST, WEST))
			var/turf/N = get_step(best, d)
			if(N && !N.density && RemasterWalkable(N, src) == 1)
				destination = N
				remaster_work_destination = N
				break
		return 1
	if(!RemasterWorkToward(best, best.density ? "a sapling" : "a stump")) return 1   // on its way
	rm_rg_steps++
	remaster_work_status = "[Z["name"]]: [best.density ? "tending a sapling" : "planting a sapling"]"
	if(rm_rg_steps < RM_REGROW_WORK) return 1
	if(!best.density && RmJzStepOff(best, src, P) && rm_rg_steps < RM_REGROW_WORK + 20) return 1   // someone on the stump: asked aside, plant once it's clear (or give it up)
	rm_rg_steps = 0
	rm_rg_target = null
	best.rm_rg_by = null
	if(!best.density) P.RmJzPlant(best)
	else
		best.HP = min(RemasterTreeMax(best), best.HP + RM_TEND_GROW)
		best.rm_tended_at = world.time
		remaster_dirty_turfs["[best.x],[best.y],[best.z]"] = 1
	return 1

// Back to the free pool (released by the allocator, or its row went away).
// nofree: taken straight onto another row (RmJzTakeFromNormal), so not put in the free pool.
Player/proc/RmJobLeave(mob/Monsters/M, nofree = 0)
	if(M.rm_jz_fishing)
		M.rm_jz_fishing = 0
		M.remaster_fish_spot = null
	if(M.rm_jz_id)
		if(length(rm_jz_hshort) && rm_jz_hshort[M.rm_jz_id]) rm_jz_hshort[M.rm_jz_id] = max(1, world.time)   // a short High row someone left waits its own while again (first-house a)
		var/list/was = RmJzMembers(M.rm_jz_id)
		was -= M
	M.rm_jz_id = null
	if(M.remaster_job in list("builder", "hauler")) M.remaster_job = "any"
	if(M.remaster_board_claim && M.remaster_job == "any") M.RemasterBoardRelease()   // off a make row: the order is let go
	if(M.remaster_active && M.remaster_active.automatic) M.RemasterCancelOrders()
	M.RemasterStopWork()
	if(!nofree && M.remaster_job == "any" && RmJzValid(M)) RmJzFreeAdd(M)

// A player changed this unit's role (Settlement.dm RemasterAssignJob).
mob/Monsters/proc/RmJobRoleChanged(old)
	var/Player/P = Owner
	if(!istype(P)) return
	if(rm_jz_id)
		var/list/was = P.RmJzMembers(rm_jz_id)
		was -= src
		rm_jz_id = null
	P.RmJzFreeDrop(src)
	if(remaster_job == "any") P.RmJzFreeAdd(src)

// For the records session: a unit folded into a record, and woken again.
Player/proc/RmJobUnitGone(mob/Monsters/M)
	if(M.rm_jz_id)
		var/list/was = RmJzMembers(M.rm_jz_id)
		was -= M
	RmJzFreeDrop(M)
Player/proc/RmJobUnitBack(mob/Monsters/M)
	if(M.rm_jz_id && RmJz(M.rm_jz_id))
		var/list/now = RmJzMembers(M.rm_jz_id)
		now |= M
	else if(M.remaster_job == "any")
		M.rm_jz_id = null
		RmJzFreeAdd(M)

// For the records session too: what an asleep worker's row has it doing, so on waking it can live its asleep time
// through with Away.dm's work procs (FarRecords.dm maps the job to them). list("job", "x", "y", "z" = the centre to
// work round, "left" = how many more of the row's good before its stop at, null = no limit), or null: no row, or the
// row stands down now (paused, at its stop, nothing left), or builders (they wait, like other unmeasured jobs).
Player/proc/RmJobAsleep(mob/Monsters/M)
	if(!M || !M.rm_jz_id) return null
	var/list/Z = RmJz(M.rm_jz_id)
	if(!Z || !RmJzWantNow(Z)) return null
	var/job
	switch(Z["kind"])
		if("wood") job = "woodcutter"
		if("stone") job = "miner"
		if("farm") job = "farmer"
		if("haulers") job = "hauler"
	if(!job) return null
	var/turf/C = RmJzCentre(Z, src)
	if(!C) return null
	var/good = rm_jz_kinds[Z["kind"]][2]
	var/left = null
	if(good && Z["stop"]) left = max(0, Z["stop"] - RmJzStock(good))
	return list("job"=job, "x"=C.x, "y"=C.y, "z"=C.z, "left"=left)

// The safety net: totals rebuilt from the realm's units.
// With spread, a big realm's recount goes on over ticks (every 250 units it may pause, Spread.dm RmTrackPause).
Player/proc/RmJobsRecount(spread = 0)
	rm_jz_members = list()
	rm_ch_bclaims = list()
	rm_jz_nfree = 0
	RmJzCellsReset()
	rm_jz_zfree = list()
	var/i = 0
	for(var/mob/Monsters/M in UnitList)
		i++
		if(spread && !(i % 250))
			RmTrackPause()
			if(Rm3DGone(M)) continue   // died while the recount waited: the ref isn't null in OpenDream (polish-errors)
		M.rm_jz_free_in = 0     // added again below if it's free
		if(M.rm_ch_bc) M.rm_ch_bc = null
		if(!RmJzValid(M)) continue
		if(M.remaster_board_claim && M.remaster_job == "board")    // Board workers on an order (a make row wants the rest)
			M.rm_ch_bc = M.remaster_board_claim
			RmChBoardCount(M.rm_ch_bc, 1)
		if(M.rm_jz_id && RmJz(M.rm_jz_id))
			var/list/now = RmJzMembers(M.rm_jz_id)
			now += M
		else
			if(M.rm_jz_id)
				M.rm_jz_id = null
				if(M.remaster_job in list("builder", "hauler")) M.remaster_job = "any"
			if(M.remaster_job == "any") RmJzFreeAdd(M)
	rm_jz_ready = 1

// --- The allocator -----------------------------------------------------------------------------------------------
Player/RemasterSettlementTick()
	. = ..()
	if(rm_jz && world.time >= rm_jz_next)
		rm_jz_next = world.time + RM_JZ_EVERY
		RmJobsTick(rm_track_run ? 1 : 0)   // inside the player's spread track run (Spread.dm): may go on next tick
	if(world.time >= rm_pop_next)
		rm_pop_next = world.time + RM_JZ_EVERY
		RmPopTick(rm_track_run ? 1 : 0)
	if(rm_chain_tabs && world.time >= rm_ch_next)
		rm_ch_next = world.time + RM_JZ_EVERY
		RmChPass()

// A row whose number nobody set (the board's want): a plan wants a villager for every 6 blocks left, the Builders row one
// for every 4 tiles of the open sites; only villagers free on the job board come (Normal rows borrow from nobody).
#define RM_JZ_AUTO_PLAN 10
#define RM_JZ_AUTO_BUILD 8
// How many a row wants right now: none while paused, at its "stop at", or with nothing left to work.
Player/proc/RmJzWantNow(list/Z)
	if(Z["paused"] || Z["kind"] == "stock") return 0
	if(Z["kind"] == "make") return RmJzMakeWant(Z)
	var/want = Z["want"]
	if(!Z["set"])   // nobody set its number: idle villagers help with what there is to build (construction-3d, 10-30)
		if(Z["kind"] == "build" || Z["kind"] == "dig") want = max(want, min(RM_JZ_AUTO_PLAN, round(length(Z["cells"]) / 6) + 1))
		else if(Z["kind"] == "builders")
			var/tiles = 0
			for(var/list/S in RemasterOpenSites()) tiles += S["left"] || 0
			want = max(want, min(RM_JZ_AUTO_BUILD, round((tiles + 3) / 4)))
	if(RmJzIsZone(Z)) want = min(want, RmJzCap(Z))
	var/good = rm_jz_kinds[Z["kind"]][2]
	if(good && Z["stop"] && RmJzStock(good) >= Z["stop"]) return 0
	if(RmJzTargetsLeft(Z) == 0) return max(RmJzLooseWant(Z, want), min(want, RmJzRegrowLeft(Z)))   // nothing to cut or dig: for the pieces left lying, and its stumps and saplings (the Tend redo)
	if(Z["kind"] == "fish") want = min(want, RM_JZ_FISH_PER_SPOT * RmJzTargetsLeft(Z))
	if(Z["kind"] == "builders" && (!length(RemasterOpenSites()) || (want > 0 && RmJzBuildersIdle()))) return 0   // and while no open site can be worked (first-house b)
	if(Z["kind"] == "haulers")
		if(!RemasterStockpile()) return 0
		// until the player sets the row: a hauler for each yard holding goods, so the yards' goods reach the main
		// stockpile, where the workshops take their materials (StationCraft.dm), with no click (the lodge test: its
		// carpentry waited for wood that lay in the wood's yard)
		if(!Z["set"]) want = max(want, RmJzYardsHolding())
	return want

// With spread (in the player's track run), it may pause every 10 moves and go on next tick (Spread.dm), so a big change
// never holds one tick; rm_jz_last_ms then counts only the work, not the ticks between.
Player/proc/RmJobsTick(spread = 0)
	var/t0 = world.tick_usage
	var/ms = 0
	if(!rm_jz_ready || world.time >= rm_jz_recount_at)
		// staggered across players, and rarer in a big realm (every 60 s to 5,000 units, then longer: 6 min at 30,000): it's
		// the safety net, and the rows' checked slices and the free pool's own checks keep the totals right between
		rm_jz_recount_at = world.time + RM_JZ_RECOUNT * max(1, round(length(UnitList) / 5000)) + rand(0, 50)
		if(spread)
			ms += (world.tick_usage - t0) * world.tick_lag
			RmJobsRecount(1)
			RmTrackPause()
			t0 = world.tick_usage
		else RmJobsRecount()
	if(rm_jz_waiting) RmJzWakeTick()   // workers waiting for their farm (J2)
	RmJzFixedRows()
	RmJzFurnitureTidy()
	RmJzOrderRows()
	// rows by priority, High first; within it, in the order they were made
	var/moves = 0
	var/list/hshort = list()        // High rows still short after this pass -> since when (first-house a)
	moves += RmJzBuildersLetGo()    // builders with nothing to build go back before the rows fill (first-house b)
	for(var/prio = 1, prio <= 3, prio++)
		for(var/list/Z in rm_jz) if(Z["prio"] == prio)
			var/list/members = RmJzMembers(Z["id"])
			RmJzCheckSlice(Z, members)
			var/want = RmJzWantNow(Z)
			var/went = 0
			var/came = 0
			// over: a few go back furthest first; many at once (a row turned down), the newest joiners
			while(length(members) > want && moves < RM_JZ_MOVES)
				var/mob/Monsters/far = RmJzLeaver(Z, members, want)
				if(!far) break
				RmJobLeave(far)
				if(far in members) members -= far      // left over in the list (a deleted unit): drop it here
				went++
				moves++
				if(spread && !(moves % 10))
					ms += (world.tick_usage - t0) * world.tick_lag
					RmTrackPause()
					t0 = world.tick_usage
					if(!(Z in rm_jz)) break       // removed while this waited
			if(!(Z in rm_jz)) continue            // removed while a spread pass waited
			// short: the nearest free take it up
			var/short = want - length(members)
			var/hsince = prio == 1 && rm_jz_hshort ? (rm_jz_hshort[Z["id"]] || 0) : 0
			while(short > 0 && moves < RM_JZ_MOVES)
				var/mob/Monsters/M = RmJzNearestFree(Z)
				if(!M && prio == 1) M = RmJzTakeFromLow(Z)    // a High row may take from Low rows
				if(!M && hsince && world.time - hsince >= RM_JZ_STAY) M = RmJzTakeFromNormal(Z)   // and, short a while, from Normal rows (first-house a)
				if(!M) break
				RmJobJoin(M, Z)
				short--
				came++
				moves++
				if(spread && !(moves % 10))
					ms += (world.tick_usage - t0) * world.tick_lag
					RmTrackPause()
					t0 = world.tick_usage
					if(!(Z in rm_jz)) break
			if(prio == 1 && short > 0 && (hsince || moves < RM_JZ_MOVES)) hshort[Z["id"]] = hsince || max(1, world.time)   // short with nobody to take (not just the move cap): its while starts
			if(came || went)
				if(!rm_jz_lognote) rm_jz_lognote = list()
				var/list/note = rm_jz_lognote[Z["id"]]
				if(!note)
					note = list(0, 0)
					rm_jz_lognote[Z["id"]] = note
				note[1] += came
				note[2] += went
	rm_jz_hshort = hshort
	rm_jz_last_ms = ms + (world.tick_usage - t0) * world.tick_lag
	rm_jz_last_moves = moves
	RmJzSampleStores()
	// what needs the player, for the board's "Needs you" and the Work button's badge (60 workers a row at most)
	rm_jz_prob = list()
	for(var/list/Z in rm_jz)
		var/code = RmJzProblemOf(Z)
		if(code) rm_jz_prob[Z["id"]] = code
	if(moves >= RM_JZ_MOVES) rm_jz_next = min(rm_jz_next, world.time + 5)   // more to move: the next pass comes sooner
	// the Village Log: one line per row that changed, at most every 30 s (a busy board would fill it otherwise)
	if(length(rm_jz_lognote) && world.time >= rm_jz_log_at)
		rm_jz_log_at = world.time + 300
		for(var/id in rm_jz_lognote)
			var/list/note = rm_jz_lognote[id]
			var/list/Z = RmJz(id)
			if(!Z || !note) continue
			var/turf/C = RmJzCentre(Z, src)
			if(note[1]) RemasterLog("[Z["name"]]: [note[1]] villager[note[1] == 1 ? "" : "s"] took up the work", "work", C)
			if(note[2]) RemasterLog("[Z["name"]]: [note[2]] went back to the free villagers", "work", C)
		rm_jz_lognote = list()

// A slice of a row is checked each pass, carrying on where the last one stopped: the dead, captured and deleted drop
// out within a few passes, and a pass never reads every worker.
Player/proc/RmJzCheckSlice(list/Z, list/members)
	var/n = length(members)
	if(!n) return
	if(!rm_jz_vi) rm_jz_vi = list()
	var/i = rm_jz_vi[Z["id"]] || 1
	var/list/stale
	for(var/k = 1, k <= min(n, RM_JZ_CHECK), k++)
		if(i > n) i = 1
		var/mob/Monsters/M = members[i]
		if(!RmJzValid(M) || M.rm_jz_id != Z["id"])
			if(!stale) stale = list()
			stale += M
		i++
	rm_jz_vi[Z["id"]] = i
	for(var/S in stale) members -= S

proc/RmJzCentre(list/Z, Player/P)
	if(RmJzIsZone(Z)) return locate(round((Z["x0"] + Z["x1"]) / 2), round((Z["y0"] + Z["y1"]) / 2), Z["z"])
	if(Z["kind"] == "make")      // an order posted "where the camera is now" works round that spot (Board.dm)
		var/list/O = P.RemasterBoardOrder(Z["order"])
		var/list/A = O ? O["area"] : null
		if(islist(A) && length(A) == 3)
			var/turf/T = locate(A[1], A[2], A[3])
			if(T) return T
	var/turf/S = P.RemasterStockpile()
	if(S) return S
	return P.loc

Player/proc/RmJzFurthest(list/Z, list/members)
	var/turf/C = RmJzCentre(Z, src)
	var/mob/Monsters/far
	var/fd = -1
	for(var/mob/Monsters/M in members)
		var/d = C && M.z == C.z ? abs(M.x - C.x) + abs(M.y - C.y) : 100000
		if(d > fd)
			fd = d
			far = M
	return far

// The nearest free unit, searched outward cell by cell from the row's centre.
Player/proc/RmJzNearestFree(list/Z)
	if(rm_jz_nfree <= 0) return null
	var/mk = Z["kind"] == "make" ? Z["order"] : RmPlanKind(Z["kind"]) ? Z["id"] : null     // a make row passes over villagers who couldn't do its order lately; a plan those with nothing of it in reach (Plans.dm)
	var/turf/C = RmJzCentre(Z, src)
	if(!C) return null
	var/cx = round(C.x / RM_JZ_CELL)
	var/cy = round(C.y / RM_JZ_CELL)
	var/maxr = max(rm_jz_cw, rm_jz_ch)
	if(!rm_jz_cells || !rm_jz_zfree || rm_jz_zfree["[C.z]"] <= 0) maxr = -1     // nobody free on this level: straight to anyone free
	var/list/stale
	for(var/r = 0, r <= maxr, r++)
		var/mob/Monsters/best
		var/bd = 1#INF
		var/seen = 0
		// round the ring's edge only: east along the bottom, north up the right, west along the top, south down the left
		var/dx = -r
		var/dy = -r
		var/steps = r ? 8 * r : 1
		for(var/j = 0, j < steps && seen < RM_JZ_LOOK, j++)
			var/k = RmJzCellAt(cx + dx, cy + dy, C.z)
			var/list/L = k ? rm_jz_cells[k] : null
			if(length(L))
				for(var/mob/Monsters/M in L)
					if(!RmJzValid(M) || M.remaster_job != "any" || M.rm_jz_id)
						if(!stale) stale = list()
						stale += M
						continue
					if(mk && M.remaster_board_skip && M.remaster_board_skip[mk] > world.time) continue
					var/d = abs(M.x - C.x) + abs(M.y - C.y)
					if(d < bd)
						bd = d
						best = M
					seen++
					if(seen >= RM_JZ_LOOK) break
			if(dy == -r && dx < r) dx++
			else if(dx == r && dy < r) dy++
			else if(dy == r && dx > -r) dx--
			else dy--
		if(best)
			for(var/S in stale) RmJzFreeDrop(S)
			return best
	// none on this level's cells: anyone free, cell by cell
	for(var/list/L in rm_jz_cells) for(var/mob/Monsters/M in L)
		if(RmJzValid(M) && M.remaster_job == "any" && !M.rm_jz_id)
			if(mk && M.remaster_board_skip && M.remaster_board_skip[mk] > world.time) continue
			for(var/S in stale) RmJzFreeDrop(S)
			return M
		if(!stale) stale = list()
		stale += M
	for(var/S in stale) RmJzFreeDrop(S)
	return null

// A High row left short may take a worker who has been on a Low row a while.
Player/proc/RmJzTakeFromLow(list/Z)
	for(var/list/L in rm_jz) if(L["prio"] == 3 && L != Z)
		var/list/low = RmJzMembers(L["id"])
		for(var/mob/Monsters/M in low)
			if(RmJzValid(M) && world.time - M.rm_jz_since >= RM_JZ_STAY)
				low -= M
				M.rm_jz_id = null
				if(M.remaster_job in list("builder", "hauler")) M.remaster_job = "any"
				return M
	return null

// --- First house (the owner, 10-26: "High rows may take workers from Normal rows after a while, and the Builders row
// stops holding villagers while no site can be worked") ---------------------------------------------------------------
// With every villager on a Normal row, a building's own High orders (its table, its beds) got nobody, and builders
// with nothing they could build held the hands those orders needed: 8 Humans' house waited 14-26 minutes for its table
// and chair, an Orc lodge 24 for its beds. "A while" is RM_JZ_STAY (60 s), the wait a High row already has for Low rows.
#define RM_JZ_BLOOK 300                     // (b) a store sweep, a look round a site or a sum is reused this long (30 s)
Player/var/tmp/list/rm_jz_hshort            // (a) High row id -> when it began to be short with nobody free or Low
Player/var/tmp/list/rm_jz_bwork             // (b) list(1 = no open site can be worked, world.time, open sites)
Player/var/tmp/rm_jz_bidle = 0              // (b) when no open site could be worked any more (0: one can)
Player/var/tmp/rm_jz_bseen = 0              // (b) the last check: a gap (row paused, no sites, want 0) starts the wait again
Player/var/tmp/list/rm_jz_blook             // (b) key -> list(answer, world.time): sweeps and sums, for RM_JZ_BLOOK

// (a) A High row short for RM_JZ_STAY, with nobody free and nobody on a Low row, may take a worker who has been on a
// Normal row as long: builders waiting for material first, then the zone and plan rows (the one with the most hands
// first), then Normal make rows, food rows last and never their last worker. Never a builder at work, one who couldn't
// do this order lately or can't now, one whose row's work already counts for this order (a woodcutter for "Chop wood
// for building": the order counts what the stores gain), or one carrying a load in; when the best row's only takers
// are carrying, none this pass (one comes once its load is in).
Player/proc/RmJzTakeFromNormal(list/Z)
	var/list/O = Z["kind"] == "make" ? RemasterBoardOrder(Z["order"]) : null
	var/mk = Z["kind"] == "make" ? Z["order"] : RmPlanKind(Z["kind"]) ? Z["id"] : null     // as RmJzNearestFree
	var/good = O && (O["kind"] in list("wood", "stone", "food")) ? O["kind"] : null
	var/mob/Monsters/best
	var/best_rank = 5
	var/best_n = 0
	var/carry_rank = 5
	for(var/list/L in rm_jz) if(L["prio"] == 2 && L != Z)
		var/list/mem = RmJzMembers(L["id"])
		var/n = length(mem)
		if(!n) continue
		var/rank = L["kind"] == "builders" ? 1 : L["kind"] == "make" ? 3 : (L["kind"] in list("fish", "farm")) ? 4 : 2
		if(rank > best_rank || (rank == best_rank && n <= best_n)) continue
		if(rank == 4 && n < 2) continue                      // a food row keeps its last worker
		if(good && RmJzGivesGood(L, good)) continue          // its work counts for this order already
		var/k = 0
		for(var/mob/Monsters/M in mem)
			if(++k > RM_JZ_LOOK) break
			if(!RmJzValid(M) || M.rm_jz_id != L["id"]) continue
			if(world.time - M.rm_jz_since < RM_JZ_STAY) continue
			if(rank == 1 && M.remaster_site && !M.remaster_site_standby) continue      // building now
			if(mk && M.remaster_board_skip && M.remaster_board_skip[mk] > world.time) continue
			if(O && M.RmChCant(O, src)) continue
			if(M.remaster_delivery)
				carry_rank = min(carry_rank, rank)
				continue
			best = M
			best_rank = rank
			best_n = n
			break
	if(!best || carry_rank < best_rank) return null
	RmJobLeave(best, 1)
	return best

// Does this row's work count for an order of this good (wood, stone, food: the order counts what the stores gain)?
Player/proc/RmJzGivesGood(list/L, good)
	if(L["kind"] == "gather") return good == "wood" || good == "stone"
	if(L["kind"] == "make")
		var/list/X = RemasterBoardOrder(L["order"])
		return X && X["kind"] == good
	var/list/K = rm_jz_kinds[L["kind"]]
	return K && K[2] == good

// (b) 1 once no open site has been workable for RM_JZ_STAY: the Builders row then wants nobody until one is.
// The look is kept 2 s, and 10 s while no site can be worked (nothing changes then but what comes by itself: an order
// coming or going drops it at once, RmJzOrderRows; a site placed or done too, as the number of sites is part of it).
Player/proc/RmJzBuildersIdle()
	if(world.time - rm_jz_bseen > 5 * RM_JZ_EVERY) rm_jz_bidle = 0     // not checked for a while: the wait starts again
	rm_jz_bseen = world.time
	var/list/sites = RemasterOpenSites()
	var/list/c = rm_jz_bwork
	if(c && c[3] != length(sites)) rm_jz_blook = null      // a site placed or done: look afresh
	var/idle
	if(c && c[3] == length(sites) && world.time - c[2] < (c[1] ? 5 * RM_JZ_EVERY : RM_JZ_EVERY)) idle = c[1]
	else
		idle = length(sites) ? 1 : 0
		for(var/list/S in sites) if(RmJzSiteWorkable(S))
			idle = 0
			break
		rm_jz_bwork = list(idle, world.time, length(sites))
	if(!idle) rm_jz_bidle = 0
	else if(!rm_jz_bidle) rm_jz_bidle = max(1, world.time)
	return idle && world.time - rm_jz_bidle >= RM_JZ_STAY ? 1 : 0

// Something a builder could do there now (RemasterSiteReady without a unit), or something it lacks it hasn't asked for.
Player/proc/RmJzSiteWorkable(list/S)
	if(S["ceil"] && length(RemasterBuildingRoofs(S))) return 1
	var/mixed = RemasterSiteMixed(S)
	if(mixed && length(RemasterBuildingRock(S))) return 1
	// RemasterSiteModes and RmSiteNeedsAny in one look over its pieces: the kinds left and the materials still needed
	// (each kind's material looked up once: RemasterBuildMaterial searches the build catalogue)
	var/list/mat = list()
	var/list/modes = list()
	var/list/needs = list()
	if(remaster_blueprints) for(var/list/B in remaster_blueprints) if(B["site"] == S["id"])
		modes |= B["mode"]
		for(var/mode in B["then"] ? list(B["mode"], B["then"]) : list(B["mode"]))
			if(!(mode in mat)) mat[mode] = RemasterBuildMaterial(mode) || 0
			var/path = mat[mode]
			if(path && !(path in needs) && RemasterBlueprintNeed(mode, locate(B["x"], B["y"], B["z"]))) needs += path
	if(!mixed) modes = list(S["mode"])
	var/list/lack = list()
	for(var/mode in modes)
		if(mixed && length(modes) > 1 && RemasterBuildShape(mode) == "gate") continue   // the door goes in last
		var/path = (mode in mat) ? mat[mode] : RemasterBuildMaterial(mode)
		if(!path || !(path in needs)) return 1
		lack |= path
	if(!length(lack)) return 1                       // can't tell: it keeps its builders, as before
	for(var/path in lack) if(RmJzSiteHas(S, path)) return 1
	// a builder there reports one short piece at a time (RemasterSiteNextTile), and which one depends on the builder: the
	// site can't be worked only when nothing it lacks could be posted any more (each is asked, or can't be)
	for(var/path in lack) if(!RmJzSiteAsked(S, path)) return 1     // it hasn't asked for this yet: a builder goes there and asks
	return 0

// A piece for the site where its builders would fetch it (RemasterSiteSource's places and filters).
Player/proc/RmJzSiteHas(list/S, path)
	for(var/mob/Monsters/W in RmJzMembers("builders")) if(W.remaster_site == S["id"] && W.RemasterCarriedCount(path)) return 1
	var/kind = RemasterMaterialKind(path)
	if(kind == "wood" || kind == "stone")
		// the stores' count as last taken (RmJzSampleStores, every 10 s), not a count of its own: none there, no sweep; a new
		// count, a new look
		var/list/c = rm_jz_stock ? rm_jz_stock[kind] : null
		var/n = c ? c[1] : 1
		if(n > 0 && RmJzLook("s|[S["z"]]|[path]|[n]", S, path)) return 1
		return RmJzLook("l|[S["id"]]|[path]", S, path)
	return RmJzLook("s|[S["z"]]|[path]", S, path)    // furniture: from the stores only

Player/proc/RmJzLook(key, list/S, path)
	if(!rm_jz_blook || length(rm_jz_blook) > 64) rm_jz_blook = list()
	var/list/c = rm_jz_blook[key]
	if(c && world.time - c[2] < RM_JZ_BLOOK) return c[1]
	var/found = 0
	if(copytext(key, 1, 2) == "s")
		for(var/turf/T in RemasterStores()) if(T.z == S["z"])
			for(var/obj/Items/I in range(1, T)) if(istype(I, path) && isturf(I.loc) && !I.remaster_placed && RemasterMayCollect(I) && !RemasterUnreachable(I))
				found = 1
				break
			if(found) break
	else
		var/turf/C = locate(S["x"], S["y"], S["z"])
		if(C) for(var/obj/Items/I in range(12, C)) if(istype(I, path) && isturf(I.loc) && RemasterMayCollect(I) && !RemasterUnreachable(I))
			found = 1
			break
	rm_jz_blook[key] = list(found, world.time)
	return found

// A builder standing at the site could post nothing for it: the posters' own early returns.
Player/proc/RmJzSiteAsked(list/S, path)
	var/kind = RemasterMaterialKind(path)
	if(remaster_board_orders) for(var/list/O in remaster_board_orders) if(!O["done"] && O["standing"] == "build-[kind]") return 1
	if(kind == "wood" || kind == "stone") return 0           // a builder there posts it (Blueprints.dm RemasterSiteMissing)
	if(!(kind in list("bed", "table", "chair", "door"))) return 1
	var/key = "n|[S["z"]]|[path]"
	var/list/c = rm_jz_blook ? rm_jz_blook[key] : null
	if(c && world.time - c[2] < RM_JZ_BLOOK) return c[1]
	var/asked = 1
	if(RmJzFurnitureKnown(kind))                             // the furniture poster's sum (Player/RemasterSiteMissing)
		var/need = 0
		for(var/list/X in RemasterOpenSites()) need += RemasterSiteNeedCount(X, path)
		need -= RemasterStoreCount(path, S["z"]) + RmChOnTheWay(path)
		asked = need <= 0 ? 1 : 0
	if(!rm_jz_blook || length(rm_jz_blook) > 64) rm_jz_blook = list()
	rm_jz_blook[key] = list(asked, world.time)
	return asked

// RmJzFurnitureRecipe on the stations as last looked at (RemasterStationCatalog keeps them 10 s; a look of its own scans
// round the stockpile for every kind of station), or a fresh look when there's none yet.
Player/proc/RmJzFurnitureKnown(kind)
	if(!remaster_station_cached) return RmJzFurnitureRecipe(kind) ? 1 : 0
	var/word = kind == "bed" ? "Bed" : kind == "table" ? "Table" : kind == "chair" ? "Chair" : "Door"
	for(var/list/C in remaster_station_cached) if(C["id"] == "carpentry")
		for(var/list/R in C["recipes"]) if(findtext(R["label"], word)) return 1
	return 0

// (b) The Builders row stands down: its villagers go before the rows fill, so the High order for what the site lacks
// takes them first and the zone rows only what is left. Returns the moves made.
Player/proc/RmJzBuildersLetGo()
	var/list/Z = RmJz("builders")
	if(!Z || Z["paused"] || Z["want"] <= 0) return 0
	var/list/members = RmJzMembers("builders")
	if(!length(members) || !length(RemasterOpenSites()) || !RmJzBuildersIdle()) return 0
	var/went = 0
	while(length(members) && went < RM_JZ_MOVES)
		var/mob/Monsters/far = RmJzLeaver(Z, members, 0)
		if(!far) break
		RmJobLeave(far)
		if(far in members) members -= far      // left over in the list (a deleted unit): drop it here
		went++
	if(went)
		if(!rm_jz_lognote) rm_jz_lognote = list()
		var/list/note = rm_jz_lognote["builders"]
		if(!note)
			note = list(0, 0)
			rm_jz_lognote["builders"] = note
		note[2] += went
	return went

// --- Painting and the board's commands ---------------------------------------------------------------------------
// + Wood / + Stone / + Farm / + Stockpile put the game's own build drag into a zone mode ("Piece:jz_<kind>").
Player/RemasterPaint(value)
	if(copytext("[Function]", 1, 10) != "Piece:jz_") return ..()
	var/kind = copytext(Function, 10)
	var/list/p = splittext("[value]", "|")
	if(p.len != 4)
		RemasterCancelPlacement()
		return 0
	var/list/Z = RmJzAdd(kind, text2num(p[1]), text2num(p[2]), text2num(p[3]), text2num(p[4]), z)
	if(!Z)
		// the paint mode stays on: drag it again beside the other zone
		if(rm_jz_refused) RemasterNotice("That overlaps [rm_jz_refused]: work zones can't share ground. Drag it beside [rm_jz_refused], or remove that one first. Esc to stop.")
		return 0
	RemasterCancelPlacement()
	var/left = RmJzTargetsLeft(Z)
	var/rest = rm_jz_resting ? (rm_jz_resting[Z["id"]] || 0) : 0
	var/what = ""
	if(kind == "fish") what = left > 0 ? " with [left] fishing spot[left == 1 ? "" : "s"]" : " with no fishing spot: drag it along a shore where fish bubble"   // its targets are the spots (they said "rock faces")
	else if(left > 0) what = " with [left] [kind == "wood" ? "tree" : kind == "gather" ? "tree or rock face" : "rock face"][left == 1 ? "" : "s"] to work[rest ? " and [rest] resting" : ""]"
	else if(left == 0) what = rest ? " with [rest] resting (they grow back, then it works)" : " with nothing to [kind == "wood" ? "cut: drag it over trees" : kind == "gather" ? "gather: drag it over trees or rock" : "dig: drag it over rock faces"]"
	if(rm_gz_pending)   // made by the Gather bar (gatherzone): the units selected when its drag began join it
		var/list/GP = rm_gz_pending
		rm_gz_pending = null
		var/joined = RmJzJoinSelected(Z, GP["queued"], GP["units"])
		if(joined) what += "; [joined] of yours [GP["queued"] ? "take it up after their current tasks" : "started on it"]"
	RemasterNotice("[Z["name"]]: [Z["x1"] - Z["x0"] + 1] by [Z["y1"] - Z["y0"] + 1] tiles[what]. [kind == "stock" ? "A store for anything; set its filter in Stockpile zones." : "It wants [Z["want"]] workers; villagers on the job board take it up by themselves."]")
	RemasterLog("Work zone painted: [Z["name"]]", "work", locate(Z["x0"], Z["y0"], Z["z"]))
	rm_jz_next = 0
	return 1

Player/RemasterTouchCommand(action, value)
	// the Gather bar's Stockpile here (the owner approved "Places a stockpile at the selected unit, from the bar"):
	// "stockzone unit" puts the whole-area store Work's "+ Store" makes (RmJzAdd "stock"), 5 x 5 round the first selected
	// unit of yours. With no stockpile on that level it also becomes the drop-off (the main stockpile at its middle), so
	// gathering there has somewhere to go.
	if(action == "stockzone")
		var/mob/Monsters/SU
		if(value == "unit") for(var/mob/Monsters/M in Selected) if(M.Owner == src && isturf(M.loc))
			SU = M
			break
		if(!SU)
			RemasterNotice("Select a unit of yours where the stockpile should go.")
			return 0
		var/list/SZ = RmJzAdd("stock", max(1, SU.x - 2), max(1, SU.y - 2), min(world.maxx, SU.x + 2), min(world.maxy, SU.y + 2), SU.z)
		if(!SZ)
			RemasterNotice("No stockpile can go there.")
			return 0
		var/turf/MS = RemasterStockpile()
		var/main = 0
		if(!MS || MS.z != SU.z)
			var/turf/C = RmJzOpenNear(round((SZ["x0"] + SZ["x1"]) / 2), round((SZ["y0"] + SZ["y1"]) / 2), SU.z, SZ)
			if(C)
				remaster_stock_x = C.x
				remaster_stock_y = C.y
				remaster_stock_z = C.z
				main = 1
		RemasterNotice("[SZ["name"]]: 5 by 5 tiles round [SU.name], a store for anything[main ? "; your drop-off on this level" : ""]. Set its filter in Stockpile zones.")
		RemasterLog("Stockpile placed: [SZ["name"]]", "work", locate(SZ["x0"], SZ["y0"], SZ["z"]))
		rm_jz_next = 0
		RemasterHUDTick()
		return 1
	// the Gather bar's Gather zone (names agreed with hud-controls): "what|queued" starts the board's own drag (jobzone), so
	// the row is made the way Work > Gather makes it; what all (a "gather" row: trees and rock) | wood | stone | food (a
	// fishing zone). The units selected now join the row the drag makes: at once, or (queued 1: Add tasks, or Shift) after
	// their current orders.
	if(action == "gatherzone")
		var/list/g = splittext("[value]", "|")
		var/list/kinds = list("all"="gather", "wood"="wood", "stone"="stone", "food"="fish")
		var/kind = kinds[length(g) && g[1] ? g[1] : "all"]
		if(!kind) return 0
		. = RemasterTouchCommand("jobzone", kind)
		if(.) rm_gz_pending = list("queued"=(length(g) >= 2 && g[2] == "1"), "units"=(Selected ? Selected.Copy() : list()))
		return
	if(action == "jobzone")
		rm_gz_pending = null      // a bar drag not made (Esc), or the board's own button: nothing waits to join
		if(!RmJzIsZone(list("kind"=value))) return 0
		Function = "Piece:jz_[value]"
		RemasterNotice("Drag the [lowertext(rm_jz_kinds[value][1])] zone on the ground (up to [value == "farm" ? RM_JZ_FARM_SIDE : RM_JZ_MAX_SIDE] tiles a side). Esc to stop.")
		RemasterHUDTick()
		return 1
	if(action == "popselect")
		RmPopSelect(value)
		RemasterHUDTick()
		return 1
	if(action == "jobany")
		// the board's own way to staff it: the selected units, or the idle villagers on Manual not in a group (soldiers
		// kept in a control group stay as they are)
		var/list/grouped = list()
		if(value == "idle") for(var/k = 1, k <= 9, k++)
			var/list/G = RemasterGroupMembers(k)
			if(length(G)) grouped |= G
		var/n = 0
		var/list/pick = value == "selected" ? (Selected ? Selected.Copy() : list()) : value == "idle" ? RemasterIdleUnits() : list()
		for(var/mob/Monsters/M in pick)
			if(!RmJzValid(M) || !(M in UnitList) || M.Wagon || M.Critter || M.Egg || M.remaster_job == "any" || (M in grouped)) continue
			M.RemasterAssignJob("any")
			n++
		RemasterNotice(n ? "[n] villager[n == 1 ? " is" : "s are"] on the job board now: it finds them work." : value == "idle" ? "No idle villagers on Manual outside a group." : "Select villagers first.")
		rm_jz_next = 0
		RemasterHUDTick()
		return 1
	if(action == "jobrow")
		var/list/p = splittext("[value]", "|")
		var/list/Z = length(p) ? RmJz(p[1]) : null
		if(!Z) return 0
		var/what = length(p) >= 2 ? p[2] : null
		var/n = length(p) >= 3 ? text2num(p[3]) : 0
		var/list/O = Z["kind"] == "make" ? RemasterBoardOrder(Z["order"]) : null
		switch(what)
			if("want")
				if(length(p) >= 3 && copytext(p[3], 1, 2) == "=") Z["want"] = clamp(round(text2num(copytext(p[3], 2))), 0, 100000)
				else Z["want"] = clamp(Z["want"] + n, 0, 100000)
				Z["set"] = 1       // the player's own number: the haulers row's yard default stops (RmJzWantNow)
				if(O)          // the order's own workers: 1 to 10, one for a craft or a station (Board.dm)
					O["workers"] = clamp(Z["want"], 1, (O["kind"] in list("craft", "station")) ? 1 : 10)
					Z["want"] = O["workers"]
			if("prio")
				Z["prio"] = clamp(round(n), 1, 3)
				if(O) O["priority"] = Z["prio"]
			if("stop") Z["stop"] = clamp(Z["stop"] + n, 0, 100000)
			if("pause") Z["paused"] = !Z["paused"]
			if("name")      // a zone's own name ("King's Wood"): up to 24 plain characters
				if(!RmJzIsZone(Z)) return 0
				var/t = length(p) >= 3 ? RmJzCleanName(p[3]) : ""
				if(t) Z["name"] = t
			if("remove")
				if(O)
					RemasterBoardCommand("boardcancel", O["id"])
					RmJzOrderRows()
					RemasterNotice("Cancelled: [O["label"]]. Its villagers are free again.")
					rm_jz_next = 0
					RemasterHUDTick()
					return 1
				if(!RmJzIsZone(Z) && !RmPlanKind(Z["kind"])) return 0   // a zone, or a dig or build plan (Plans.dm)
				RmJzRemove(Z)
				RemasterNotice("[Z["name"]] removed; its workers are free again.")
				RemasterHUDTick()
				return 1
			if("select")
				RmPopSelectList(RmJzMembers(Z["id"]), "[Z["name"]] worker")
			if("look")
				var/turf/C = RmJzCentre(Z, src)
				if(C)
					loc = locate(C.x, C.y, C.z)
					RemasterCamTo(C)       // the 3D camera too: it follows the page's own camera otherwise (Attack.dm)
		rm_jz_next = 0
		RemasterHUDTick()       // as the base command does: the board shows the change at once
		return 1
	return ..()

// New villagers (births) join Any work once the realm uses the job board, so a growing village staffs itself. A unit
// given a role by hand keeps it; a realm with no zones is left as it always was.
Player/proc/RmJzUsed()
	for(var/list/Z in rm_jz) if(RmJzIsZone(Z)) return 1
	return 0

mob/Monsters/RemasterRecordBirth(mob/Monsters/F, mob/Monsters/M, mob/Monsters/carrier)
	. = ..()
	var/Player/P = Owner
	if(!Critter && !Egg && istype(P) && remaster_job == "manual" && P.RmJzUsed()) RemasterAssignJob("any")

// The unit card names the job a villager really has: the board's row while it works one ("Human - Wood 1").
mob/Monsters/RemasterUnitData(Player/P, list/selset = null)
	. = ..()
	if(rm_jz_id && islist(.) && istype(P))
		var/list/Z = P.RmJz(rm_jz_id)
		if(Z) .["jobrow"] = Z["name"]

// What a worker on a row is doing, for its row's line: its task's line while it has one, else its job's own (Board.dm
// words a Board worker's the same way). The task's line stays after the task ends, and a unit starts with "Idle", so the
// Fishing row said "Idle" while its fisher fished, and a row whose worker waited showed the last tree it cut.
mob/Monsters/proc/RmJzStatusNow()
	if(RemasterHasOrder() && remaster_order_status) return remaster_order_status
	return remaster_work_status || remaster_order_status

// An item's name as words for a status line: "MetalAxe - Quality" -> "metal axe" (it said "its metalaxe").
proc/RmJzThingName(obj/I)
	var/n = "[I.name]"
	var/k = findtext(n, " - ")
	if(k) n = copytext(n, 1, k)
	return lowertext(RemasterSpaced(n))

// Printable ASCII without the characters the game's text uses ([ ] | < > "), at most 24, trimmed.
proc/RmJzCleanName(t)
	var/out = ""
	for(var/i = 1, i <= length(t) && length(out) < 24, i++)
		var/c = text2ascii(t, i)
		if(c >= 32 && c <= 126 && !(c in list(34, 60, 62, 91, 93, 124))) out += ascii2text(c)
	return trimtext(out)

// --- HUD data ------------------------------------------------------------------------------------------------------
Player/proc/RmJobsData()
	RmJzFixedRows()
	var/list/rows = list()
	var/list/zones = list()
	var/work = remaster_hud_tab == "work"
	for(var/list/Z in rm_jz)
		var/zone = RmJzIsZone(Z)
		if(zone) zones += list(list(Z["x0"], Z["y0"], Z["x1"], Z["y1"], Z["z"], Z["kind"], Z["name"], length(RmJzMembers(Z["id"])), Z["paused"] ? -1 : Z["want"], Z["id"]))   // + workers, wanted (-1 paused), id: the 3D plates
		if(!work) continue
		if(Z["kind"] == "make")
			rows += list(RmJzMakeRowData(Z))
			continue
		var/good = rm_jz_kinds[Z["kind"]][2]
		var/left = RmJzTargetsLeft(Z)
		var/resting = rm_jz_resting ? (rm_jz_resting[Z["id"]] || 0) : 0
		var/list/members = RmJzMembers(Z["id"])
		var/status
		if(Z["kind"] == "stock") status = "A store"
		else if(Z["paused"]) status = "Paused"
		else if(good && Z["stop"] && RmJzStock(good) >= Z["stop"]) status = "Stopped: the stores have [RmJzStock(good)] [good] (stop at [Z["stop"]])"
		else if(left == 0 && resting) status = Z["kind"] == "stone" ? "Resting: the living ore is growing back" : "Growing: [resting] sapling[resting == 1 ? "" : "s"] on the stumps; its workers plant and tend them"   // the Tend redo: resting = saplings   // the tag counts them
		else if(left == 0) status = RmJzLooseWant(Z, 1) ? "Picking up the pieces left lying" : RmJzFarText(Z) ? "Nothing in reach: [RmJzFarText(Z)] with no way to them from outside the zone" : RmJzAbove(Z) ? "Nothing left in reach: [RmJzAbove(Z)] blocks overhead (Plan mode digs a mountain from the top)" : "Nothing left to work"
		else if(Z["kind"] == "builders" && !length(RemasterOpenSites())) status = "No plans to build"
		else if(Z["kind"] == "builders" && Z["want"] && RmJzBuildersIdle()) status = "Nothing can be built until materials come: its builders work elsewhere meanwhile"   // first-house b
		else if(!length(members)) status = RmJzWantNow(Z) ? "Waiting for free villagers" : "Wants no workers"   // what it wants now: the haulers row wants one a yard holding goods until the player sets it (it said "Wants no workers")
		else
			var/mob/Monsters/M = members[1]
			status = M ? "[M.RmJzStatusNow()]" : ""
		var/list/doing = (Z["kind"] in list("wood", "stone", "gather")) && length(members) && rm_jz_doing ? rm_jz_doing[Z["id"]] : null   // the 2 s pass's
		var/now = RmJzWantNow(Z)
		var/problem = rm_jz_prob ? (rm_jz_prob[Z["id"]] || 0) : 0
		rows += list(list("id"=Z["id"], "name"=Z["name"], "kind"=Z["kind"], "want"=Z["want"], "now"=now, "count"=length(members),
			"cap"=zone ? RmJzCap(Z) : null, "prio"=Z["prio"], "paused"=Z["paused"], "stop"=Z["stop"], "good"=good,
			"stock"=good ? RmJzStock(good) : null, "left"=left, "resting"=resting, "status"=status, "zone"=zone,
			"size"=zone ? list(Z["x1"] - Z["x0"] + 1, Z["y1"] - Z["y0"] + 1) : null, "doing"=doing, "problem"=problem, "rate"=RmJzRate(Z["id"]), "far"=rm_jz_far ? (rm_jz_far[Z["id"]] || 0) : 0))   // width, height: the HUD writes 25x25 (no non-ASCII in a [] string)
	var/needs = 0
	for(var/id in rm_jz_prob) if(rm_jz_prob[id] && copytext(id, 1, 2) != "o" && RmJz(id)) needs++   // Gather's (make rows are Make's)
	var/working = 0
	for(var/list/Z in rm_jz) working += length(RmJzMembers(Z["id"]))
	return list("zones"=zones, "rows"=(work ? rows : null), "free"=rm_jz_nfree, "working"=working, "out"=(work ? RmJzStoreRates() : null), "needs"=needs, "ms"=round(rm_jz_last_ms, 0.01), "pace"=RemasterSettlementParts())

// What a row needs from the player: 1-3 a block its workers share (see RmJzDoing), 4 haulers with no stockpile, 5 a
// High row short of workers with nobody free. 0: nothing.
Player/proc/RmJzProblemOf(list/Z)
	var/list/members = RmJzMembers(Z["id"])
	if(rm_jz_doing) rm_jz_doing -= Z["id"]
	if(Z["paused"]) return 0
	if((Z["kind"] in list("wood", "stone", "gather")) && length(members))
		var/list/d = RmJzDoing(members)
		if(!rm_jz_doing) rm_jz_doing = list()
		rm_jz_doing[Z["id"]] = d          // for the board between passes
		if(d[6]) return d[6]
	if(Z["kind"] == "haulers" && Z["want"] && !RemasterStockpile()) return 4
	if(Z["kind"] == "make")
		var/list/O = RemasterBoardOrder(Z["order"])
		if(O && !O["done"] && RmJzMakeBlock(O)) return 6
	if(Z["prio"] == 1 && RmJzWantNow(Z) > length(members) && rm_jz_nfree <= 0) return 5
	return 0

// What a row's workers gather (Yield.dm RemasterYieldNote calls it for each piece): six 10 s buckets, the last minute.
Player/proc/RmJzYield(mob/Monsters/M)
	var/id = M.rm_jz_id
	if(!id) return
	if(id != "haulers" && id != "builders") RmJzSpot(id, M.loc)   // where the piece lands if the bag is full
	RmJzCountOut(id)

// One piece into row id's six 10 s buckets (gathered, or a fishing row's meat as it's lifted: RmJzFishStep).
Player/proc/RmJzCountOut(id)
	var/b = round(world.time / 100)
	var/k = b % 6 + 1
	if(!rm_jz_out)
		rm_jz_out = list()
		rm_jz_out_t = list()
	var/list/c = rm_jz_out[id]
	var/list/t = rm_jz_out_t[id]
	if(!c)
		c = list(0, 0, 0, 0, 0, 0)
		t = list(0, 0, 0, 0, 0, 0)
		rm_jz_out[id] = c
		rm_jz_out_t[id] = t
	if(t[k] != b)
		t[k] = b
		c[k] = 0
	c[k]++

// A row's output in the last minute (the buckets still inside it).
Player/proc/RmJzRate(id)
	var/list/c = rm_jz_out ? rm_jz_out[id] : null
	if(!c) return 0
	var/list/t = rm_jz_out_t[id]
	var/b = round(world.time / 100)
	var/n = 0
	for(var/k = 1, k <= 6, k++) if(t[k] > b - 6) n += c[k]
	return n

// The realm's stores, a sample every 10 s (from the 2 s pass), and their change per minute: what's piling up or
// running down, as Songs of Syx shows it. Null until two samples a minute apart or so.
Player/proc/RmJzSampleStores()
	if(!rm_jz_hist) rm_jz_hist = list()
	if(length(rm_jz_hist))
		var/list/last = rm_jz_hist[length(rm_jz_hist)]
		if(world.time - last[1] < 100) return
	rm_jz_hist += list(list(world.time, RmJzStock("wood"), RmJzStock("stone"), RmJzStock("food")))
	if(length(rm_jz_hist) > 7) rm_jz_hist.Cut(1, 2)

Player/proc/RmJzStoreRates()
	if(length(rm_jz_hist) < 2) return null
	var/list/a = rm_jz_hist[1]
	var/list/z = rm_jz_hist[length(rm_jz_hist)]
	var/dt = (z[1] - a[1]) / 600      // minutes
	if(dt <= 0) return null
	return list(round((z[2] - a[2]) / dt), round((z[3] - a[3]) / dt), round((z[4] - a[4]) / dt), round(dt * 60))

// The stores' count of a good, at most every 2 s (RemasterStockCount reads every item round each store).
Player/proc/RmJzStock(good)
	if(!good) return 0
	if(!rm_jz_stock) rm_jz_stock = list()
	var/list/c = rm_jz_stock[good]
	if(c && world.time - c[2] < RM_JZ_EVERY) return c[1]
	var/n = RemasterStockCount(good)
	rm_jz_stock[good] = list(n, world.time)
	return n

// What a wood or stone row's workers are doing, from at most 60 of them (scaled up past that): list(working, carrying
// in, eating or resting, waiting, 1 if scaled). The page words it ("5 chopping, 3 carrying in").
Player/proc/RmJzDoing(list/members)
	var/n = length(members)
	var/look = min(n, 60)
	var/list/c = list(0, 0, 0, 0)
	var/list/b = list(0, 0, 0)
	var/seen = 0
	for(var/i = 1, i <= look, i++)
		var/mob/Monsters/M = members[i]
		if(!RmJzValid(M)) continue
		seen++
		if(M.rm_jz_block >= 1 && M.rm_jz_block <= 3) b[M.rm_jz_block]++
		if(M.remaster_delivery) c[2]++
		else if(M.remaster_active && (M.remaster_active.kind in list("Chop", "Mine"))) c[1]++
		else if(M.remaster_care) c[3]++
		else c[4]++
	if(n > look) for(var/k = 1, k <= 4, k++) c[k] = round(c[k] * n / look + 0.5)
	c += n > look ? 1 : 0
	// what blocks them, when a quarter of those seen share it (6th: 0 none, else RmJobStep's rm_jz_block)
	var/worst = 0
	for(var/k = 1, k <= 3, k++) if(b[k] && b[k] >= max(1, seen / 4) && (!worst || b[k] > b[worst])) worst = k
	c += worst
	return c

Player/RemasterHUDData()
	. = ..()
	if(islist(.))
		.["jobs"] = RmJobsData()
		.["plans"] = RmPlansData()   // Plan mode's tasks (Plans.dm)
		.["planStock"] = RmStoneWood()   // stone and logs in the stores for Plan mode's card (PlanPieces.dm)
		if(rm_chain_tabs) .["chain"] = remaster_hud_tab == "work" ? RmChainData() : list("needs"=rm_ch_needs)
		.["pop"] = list("c"=rm_pop, "roles"=rm_pop_roles, "age"=rm_pop_at ? round((world.time - rm_pop_at) / 10) : -1)

// --- The population overview (Village > Roster, the card on top) ----------------------------------------------------
// The whole realm by job, need and doing, for a village of thousands: counted RM_POP_SLICE units a pass (every 2 s,
// pausing in the spread track like the allocator), so it costs the same per pass at any size. The card shows the last
// full sweep and how old it is (about 2 s a thousand units). A count's chip selects those units (up to 500).
#define RM_POP_SLICE 1000
#define RM_POP_N 17
Player/var/tmp/rm_pop_next = 0
Player/var/tmp/rm_pop_i = 1              // where the sweep is in UnitList
Player/var/tmp/list/rm_pop_acc           // this sweep's counts so far
Player/var/tmp/list/rm_pop_roles_acc
Player/var/tmp/list/rm_pop               // the last full sweep: RM_POP_N counts (see RmPopCount)
Player/var/tmp/list/rm_pop_roles         // ...and the set roles' counts (woodcutter, doctor, ...)
Player/var/tmp/rm_pop_at = 0
Player/var/tmp/rm_pop_last_ms = 0

proc/RmPopNew()
	var/list/c = new /list(RM_POP_N)
	for(var/i = 1, i <= RM_POP_N, i++) c[i] = 0
	return c

// One unit into the counts: 1 all, 2 people, 3 animals and eggs; work: 4 on a job board row, 5 on Any work and free,
// 6 Manual, 7 of them idle; needs (as the unit card warns): 8 hungry, 9 needs rest, 10 low health, 11 bleeding, 12 cold,
// 13 a limb lost; doing: 14 asleep, 15 off eating or resting, 16 carrying in, 17 fighting. Set roles go in roles.
Player/proc/RmPopCount(mob/Monsters/M, list/c, list/roles)
	if(!M || M.Owner != src || M.Wagon || M.HP <= 0 || M.GoingToDie || !M.loc) return 0
	c[1]++
	if(M.Critter || M.Egg)
		c[3]++
		return 1
	c[2]++
	if(M.rm_jz_id) c[4]++
	else if(M.remaster_job == "any") c[5]++
	else if(M.remaster_job == "manual")
		c[6]++
		if(RemasterIdleEligible(M, 1)) c[7]++     // the same idle as Next idle (HUD.dm); M is from UnitList (both callers walk it)
	else if(roles) roles[M.remaster_job] = (roles[M.remaster_job] || 0) + 1
	if(M.Hunger <= 20) c[8]++
	if(M.Tiredness <= 20) c[9]++
	if(M.HP < M.MAXHP * 0.3) c[10]++
	if(M.BleedType) c[11]++
	if(M.Coldness > 0) c[12]++
	if(!M.HasLeftLeg || !M.HasRightLeg || !M.HasLeftArm || !M.HasRightArm) c[13]++
	if(M.Sleeping) c[14]++
	else if(M.remaster_care) c[15]++
	if(M.remaster_delivery) c[16]++
	if(M.remaster_attack || M.Target) c[17]++
	return 1

Player/proc/RmPopTick(spread = 0)
	var/t0 = world.tick_usage
	var/ms = 0
	if(!rm_pop_acc)
		rm_pop_acc = RmPopNew()
		rm_pop_roles_acc = list()
		rm_pop_i = 1
	var/stop = rm_pop_i + RM_POP_SLICE - 1
	for(var/i = rm_pop_i, i <= stop && i <= length(UnitList), i++)
		var/mob/Monsters/M = UnitList[i]
		if(istype(M)) RmPopCount(M, rm_pop_acc, rm_pop_roles_acc)
		if(spread && !(i % 250))
			ms += (world.tick_usage - t0) * world.tick_lag
			RmTrackPause()
			t0 = world.tick_usage
		rm_pop_i = i + 1
	if(rm_pop_i > length(UnitList))    // the sweep is done: it's the card's now, and the next begins
		rm_pop = rm_pop_acc
		rm_pop_roles = rm_pop_roles_acc
		rm_pop_at = world.time
		rm_pop_acc = null
	rm_pop_last_ms = ms + (world.tick_usage - t0) * world.tick_lag

// The idle villagers from the overview's last sweep (at most about a minute old at 30,000 units), for the HUD's idle
// badge instead of a walk over every unit on each send (the performance session's ask). Null before the first sweep.
Player/proc/RmIdleCount()
	return rm_pop ? rm_pop[7] : null

// Select the units a count counts (its number, or "role:<job>"), up to 500, through the game's own selection.
Player/proc/RmPopSelect(key)
	var/k = text2num(key)
	var/role = copytext("[key]", 1, 6) == "role:" ? copytext("[key]", 6) : null
	if(!role && !(k >= 1 && k <= RM_POP_N)) return 0
	var/list/hits = list()
	for(var/mob/Monsters/M in UnitList)
		var/list/c = RmPopNew()
		var/list/r = role ? list() : null
		if(!RmPopCount(M, c, r)) continue
		if(role ? r[role] : c[k]) hits += M
	RmPopSelectList(hits, "unit")
	return 1

Player/proc/RmPopSelectList(list/L, what)
	var/list/ok = list()
	for(var/mob/Monsters/M in L) if(RmJzValid(M) && (M in UnitList) && !M.Wagon) ok += M
	if(!length(ok))
		RemasterNotice("Nobody to select.")
		return
	RemasterClearSelection()
	var/added = 0
	for(var/i = 1, i <= min(length(ok), 500), i++) if(RemasterClickSelect(ok[i], added)) added = 1
	RemasterNotice(length(ok) > 500 ? "Selected the first 500 of [length(ok)] ([what]s). Ctrl+G makes them a group." : "Selected [length(Selected)] [what][length(Selected) == 1 ? "" : "s"]. Ctrl+G makes them a group.")

// --- The supply chain: Make rows and Serve (planning/MANAGEMENT_TOOLS.md section 11) ------------------------------
// The Work tab's Supply chain screen: Gather (the zones above), Make (the Bulletin board's orders) and Serve (food pots
// and stalls, Doctor's stalls, taverns, market stalls).
//  - Make: each open board order has a make row, staffed from the job board's free villagers like a zone; its workers
//    wanted and priority are the order's own. A villager on it claims the order and does the board's own work for it
//    (RemasterBoardWork, Board.dm). Board workers (the Board worker job) still claim orders as before: a row wants only
//    the workers they leave. One that can't do an order (a Spider at carpentry) or makes no progress for 2 minutes is
//    passed over for it for 5 minutes, as the board does with its own workers.
//  - Serve: each store counts what is put in (Put, PutIn, PourIn, Press) and is sampled every 10 s for how full it is;
//    what went out is what came in less the change. Who keeps it filled comes from the population overview's role
//    counts. Per player it's O(stores + orders) a pass, nothing per unit.
// Make and Serve on the screen: off until Gather is measured and tuned (the user, through the coordinator, 2026-10-24:
// raw materials first). Off, the HUD gets no Make/Serve data and their 2 s pass doesn't run; the page shows Gather alone.
// Board orders are still staffed by the job board's villagers (that's work, not the screen), and the stores still count.
var/rm_chain_tabs = 0
Player/var/tmp/list/rm_ch_bclaims          // order id -> Board workers on it (kept as they claim and let go; the recount rebuilds it)
Player/var/tmp/list/rm_ch_prog             // make row id -> its order's progress sampled every 10 s: list(world.time, progress), the last 7
Player/var/tmp/list/rm_ch_needs            // list(Make rows, Serve stores) that need the player, for the tabs and the Work button
Player/var/tmp/rm_ch_next = 0
Player/var/tmp/rm_ch_sample_at = 0
mob/Monsters/var/tmp/rm_ch_bc              // a Board worker's counted claim
mob/WorkShops/var/tmp
	rm_ch_in = 0                           // what was put in, all told
	rm_ch_gone = 0                         // what was thrown out (a cook emptying poisoned food): not eaten
	list/rm_ch_hist                        // a sample every 10 s: list(world.time, how full, in, gone), the last 7

// Each open order has a make row; a finished or cancelled order's row goes, and its villagers are free again.
Player/proc/RmJzOrderRows()
	if(!rm_jz) rm_jz = list()
	var/list/open = list()
	if(remaster_board_orders) for(var/list/O in remaster_board_orders) if(!O["done"]) open += O["id"]
	for(var/list/Z in rm_jz.Copy()) if(Z["kind"] == "make")
		if(!(Z["order"] in open))
			rm_jz_bwork = null       // what it brought may let a site be worked: the Builders row looks again this pass (first-house b)
			rm_jz_blook = null
			RmJzRemove(Z)
			continue
		var/list/O = RemasterBoardOrder(Z["order"])
		Z["want"] = O["workers"]
		Z["prio"] = O["priority"]
		Z["name"] = O["label"]
		open -= Z["order"]
	for(var/id in open)
		var/list/O = RemasterBoardOrder(id)
		rm_jz_bwork = null       // a new order may be what a site asked for: the Builders row looks again this pass (first-house b)
		rm_jz += list(list("id"="o[id]", "kind"="make", "name"=O["label"], "order"=id, "want"=O["workers"], "prio"=O["priority"], "stop"=0, "paused"=0))

// What stops anyone working an order (text for the row), or null.
Player/proc/RmJzMakeBlock(list/O)
	if((O["kind"] in list("wood", "stone", "food")) && !RemasterStockpile()) return "Place a stockpile first (Work tab)"
	if((O["kind"] in list("wood", "stone")) && !RemasterStockAcceptsKind(O["kind"])) return "The stockpile filter doesn't take [O["kind"]]"
	return null

Player/proc/RmJzMakeWant(list/Z)
	var/list/O = RemasterBoardOrder(Z["order"])
	if(!O || O["done"] || RmJzMakeBlock(O)) return 0
	return max(0, O["workers"] - RmChBoardOn(O["id"]))

Player/proc/RmChBoardOn(id)
	return rm_ch_bclaims ? (rm_ch_bclaims[id] || 0) : 0

Player/proc/RmChBoardCount(id, d)
	if(!id) return
	if(!rm_ch_bclaims) rm_ch_bclaims = list()
	rm_ch_bclaims[id] = max(0, (rm_ch_bclaims[id] || 0) + d)

mob/Monsters/RemasterBoardClaim(Player/P, list/O)
	. = ..()
	if(remaster_job == "board" && istype(P))
		if(rm_ch_bc) P.RmChBoardCount(rm_ch_bc, -1)
		rm_ch_bc = O["id"]
		P.RmChBoardCount(rm_ch_bc, 1)

mob/Monsters/RemasterBoardRelease()
	if(rm_ch_bc)
		var/Player/P = Owner
		if(istype(P)) P.RmChBoardCount(rm_ch_bc, -1)
		rm_ch_bc = null
	return ..()

// Why this villager can't take the order (the board's own test, worded), or null.
mob/Monsters/proc/RmChCant(list/O, Player/P)
	if(O["kind"] == "craft") return RemasterCanQueue(O["recipe"])
	if(!RemasterBoardCan(O, P)) return "the stockpile doesn't take [O["kind"]]"
	return null

// A villager's step on a make row (from RmJobStep).
mob/Monsters/proc/RmJzMakeStep(Player/P, list/Z, list/RESERVED)
	var/list/O = P.RemasterBoardOrder(Z["order"])
	if(!O || O["done"])
		RemasterStopWork()
		remaster_work_status = "[Z["name"]]: finished"
		return
	if(remaster_board_claim != O["id"])
		var/why = RmChCant(O, P)
		if(why)
			if(!remaster_board_skip) remaster_board_skip = list()
			remaster_board_skip[O["id"]] = world.time + 3000
			P.RmJobLeave(src)
			remaster_work_status = "Job board: couldn't take \"[O["label"]]\" ([why])"
			return
		RemasterBoardClaim(P, O)
	else if(O["kind"] != "craft" && world.time - remaster_board_since > 1200)
		// no progress for 2 minutes: someone else tries it (as with Board workers, Board.dm)
		if(!remaster_board_skip) remaster_board_skip = list()
		remaster_board_skip[O["id"]] = world.time + 3000
		O["note"] = "[name] couldn't make progress: [remaster_work_status]"
		P.RmJobLeave(src)
		remaster_work_status = "Job board: gave up on \"[O["label"]]\" for now"
		return
	RemasterBoardWork(P, RESERVED || list())

Player/proc/RmJzMakeRowData(list/Z)
	var/list/O = RemasterBoardOrder(Z["order"])
	var/list/members = RmJzMembers(Z["id"])
	var/board = O ? RmChBoardOn(O["id"]) : 0
	var/block = O ? RmJzMakeBlock(O) : null
	var/status
	if(!O || O["done"]) status = "Finished"
	else if(Z["paused"]) status = "Paused"
	else if(block) status = block
	else if(length(members))
		var/mob/Monsters/M = members[1]
		status = M ? "[M.RmJzStatusNow()]" : ""
	else if(board) status = "[board] Board worker[board == 1 ? "" : "s"] on it"
	else if(O["note"]) status = O["note"]
	else status = rm_jz_nfree > 0 ? "Waiting for a free villager" : "Nobody free on the job board"
	return list("id"=Z["id"], "name"=Z["name"], "kind"="make", "want"=Z["want"], "now"=RmJzWantNow(Z), "count"=length(members) + board,
		"board"=board, "prio"=Z["prio"], "paused"=Z["paused"], "stop"=0, "status"=status, "zone"=0,
		"problem"=rm_jz_prob ? (rm_jz_prob[Z["id"]] || 0) : 0, "order"=O ? O["id"] : null, "okind"=O ? O["kind"] : null,
		"progress"=O ? O["progress"] : 0, "amount"=O ? O["amount"] : 0, "standing"=O ? O["standing"] : null,
		"area"=O ? O["area"] : null, "rate"=RmChOrderRate(Z["id"]), "max"=O && (O["kind"] in list("craft", "station")) ? 1 : 10)

Player/proc/RmChSampleOrder(list/Z)
	var/list/O = RemasterBoardOrder(Z["order"])
	if(!O) return
	if(!rm_ch_prog) rm_ch_prog = list()
	var/list/h = rm_ch_prog[Z["id"]]
	if(!h)
		h = list()
		rm_ch_prog[Z["id"]] = h
	h += list(list(world.time, O["progress"]))
	if(length(h) > 7) h.Cut(1, 2)

// An order's progress a minute (null until two samples).
Player/proc/RmChOrderRate(id)
	var/list/h = rm_ch_prog ? rm_ch_prog[id] : null
	if(length(h) < 2) return null
	var/list/a = h[1]
	var/list/z = h[length(h)]
	var/dt = (z[1] - a[1]) / 600
	return dt > 0 ? round(max(0, z[2] - a[2]) / dt, 0.1) : null

// --- Serve: the stores --------------------------------------------------------------------------------------------
mob/WorkShops/RemasterFood/Put(obj/Items/Food/F)
	. = ..()
	if(.) rm_ch_in++

mob/WorkShops/RemasterFood/Empty()
	. = ..()
	rm_ch_gone += .

mob/WorkShops/RemasterClinic/PutIn(obj/Items/I)
	. = ..()
	if(.) rm_ch_in++

mob/WorkShops/RemasterTavern/PourIn(obj/Items/Potions/RemasterBrew/B)
	. = ..()
	if(.) rm_ch_in += .

mob/WorkShops/RemasterTavern/Press(mob/Monsters/M)
	. = ..()
	if(.) rm_ch_in += .

// Market stalls, kept in a list as they're made (Market.dm's merchants still look through the world for theirs).
var/list/rm_chain_stalls = list()
mob/WorkShops/RemasterStall/New()
	..()
	rm_chain_stalls += src
mob/WorkShops/RemasterStall/Del()
	rm_chain_stalls -= src
	return ..()

Player/proc/RmChStores()
	var/list/L = list()
	for(var/mob/WorkShops/RemasterFood/C in rm_food_places) if(C.Owner == src) L += C
	for(var/mob/WorkShops/RemasterClinic/K in rm_clinics) if(K.Owner == src) L += K
	for(var/mob/WorkShops/RemasterTavern/T in rm_taverns) if(T.Owner == src) L += T
	for(var/mob/WorkShops/RemasterStall/M in rm_chain_stalls) if(M.Owner == src) L += M
	return L

proc/RmChKind(mob/WorkShops/S)
	if(istype(S, /mob/WorkShops/RemasterFood/Pot)) return "pot"
	if(istype(S, /mob/WorkShops/RemasterFood)) return "stall"
	if(istype(S, /mob/WorkShops/RemasterClinic)) return "clinic"
	if(istype(S, /mob/WorkShops/RemasterTavern)) return "tavern"
	return "market"

proc/RmChFill(mob/WorkShops/S)
	if(istype(S, /mob/WorkShops/RemasterFood))
		var/mob/WorkShops/RemasterFood/C = S
		return length(C.Items())
	if(istype(S, /mob/WorkShops/RemasterClinic))
		var/mob/WorkShops/RemasterClinic/K = S
		return K.Total()
	if(istype(S, /mob/WorkShops/RemasterTavern))
		var/mob/WorkShops/RemasterTavern/T = S
		return T.drink
	return 0

proc/RmChCap(mob/WorkShops/S)
	if(istype(S, /mob/WorkShops/RemasterFood))
		var/mob/WorkShops/RemasterFood/C = S
		return C.Capacity()
	if(istype(S, /mob/WorkShops/RemasterClinic)) return RM_CLINIC_MAX
	if(istype(S, /mob/WorkShops/RemasterTavern)) return RM_TAVERN_MAX
	return 0

proc/RmChSample(mob/WorkShops/S)
	if(!RmChCap(S)) return
	if(!S.rm_ch_hist) S.rm_ch_hist = list()
	S.rm_ch_hist += list(list(world.time, RmChFill(S), S.rm_ch_in, S.rm_ch_gone))
	if(length(S.rm_ch_hist) > 7) S.rm_ch_hist.Cut(1, 2)

// list(put in a minute, gone out a minute: eaten, drunk, taken, used), or null until two samples.
proc/RmChRates(mob/WorkShops/S)
	var/list/h = S.rm_ch_hist
	if(length(h) < 2) return null
	var/list/a = h[1]
	var/list/z = h[length(h)]
	var/dt = (z[1] - a[1]) / 600
	if(dt <= 0) return null
	var/came = z[3] - a[3]
	var/went = max(0, came - (z[2] - a[2]) - (z[4] - a[4]))
	return list(round(came / dt, 0.1), round(went / dt, 0.1))

// Who keeps the stores filled: the overview's role counts (its last sweep) and the farm rows' workers.
Player/proc/RmChFillers()
	var/list/R = rm_pop_roles || list()
	var/farm = 0
	if(rm_jz) for(var/list/Z in rm_jz) if(Z["kind"] == "farm") farm += length(RmJzMembers(Z["id"]))
	return list("cook"=R["cook"] || 0, "farmer"=(R["farmer"] || 0) + farm, "hunter"=R["hunter"] || 0, "doctor"=R["doctor"] || 0, "merchant"=R["merchant"] || 0)

Player/proc/RmChNobody(kind, list/F)
	switch(kind)
		if("pot", "stall") return !F["cook"] && !F["farmer"]
		if("tavern") return !F["cook"]
		if("clinic") return !F["doctor"]
	return 0

// What a store needs: 1 empty and nobody fills it, 2 empty, 3 poison suspected, 4 raw meat in a pot with no fire, 5
// running out within 2 minutes, 6 a market stall with no merchant. 1, 3, 4 and 6 need the player.
Player/proc/RmChProblem(mob/WorkShops/S, kind, fill, list/r, list/F)
	if(kind == "market") return RemasterStallMerchant(S) ? 0 : 6
	if(istype(S, /mob/WorkShops/RemasterFood))
		var/mob/WorkShops/RemasterFood/C = S
		if(C.rm_suspect) return 3
		if(kind == "pot")
			var/mob/WorkShops/RemasterFood/Pot/P = C
			if(!P.lit) for(var/list/E in C.Items()) if(E[3] == "RawMeat") return 4
	if(!fill) return RmChNobody(kind, F) ? 1 : 2
	if(r && r[2] > r[1] && fill / (r[2] - r[1]) < 2) return 5
	return 0

Player/proc/RmChStoreRow(mob/WorkShops/S, list/F)
	var/kind = RmChKind(S)
	var/fill = RmChFill(S)
	var/list/r = RmChRates(S)
	var/list/what = list()
	var/note
	switch(kind)
		if("pot", "stall")
			var/mob/WorkShops/RemasterFood/C = S
			var/list/tally = list()
			for(var/list/E in C.Items()) tally["[E[2]]"] = (tally["[E[2]]"] || 0) + 1
			for(var/k in tally) what += "[tally[k]] [k]"
			if(kind == "pot")
				var/mob/WorkShops/RemasterFood/Pot/P = C
				note = P.lit ? (P.heat >= RM_POT_HOT ? "Hot: serves hot stew" : "The fire is lit, warming up") : "No fire: cold stew, raw meat waits"
		if("clinic")
			var/mob/WorkShops/RemasterClinic/K = S
			for(var/h in rm_herbs)
				var/list/H = rm_herbs[h]
				if(K.vars[H[3]]) what += "[K.vars[H[3]]] [H[4]]"
			for(var/h in rm_herbs) if(K.vars[h]) what += "[K.vars[h]] [rm_herbs[h][1]]"
		if("tavern")
			if(fill) what += "[fill] cup[fill == 1 ? "" : "s"] of wine"
		if("market")
			var/mob/Monsters/M = RemasterStallMerchant(S)
			if(M)
				for(var/obj/Items/I in M) if(I.suffix != "(Equipped)" && RemasterTradeValue(I)) fill++
				note = "[M.name] is selling"
	return list("kind"=kind, "name"="[S.name]", "x"=S.x, "y"=S.y, "z"=S.z, "fill"=fill, "cap"=RmChCap(S),
		"in"=r ? r[1] : null, "out"=r ? r[2] : null, "what"=what, "note"=note, "problem"=RmChProblem(S, kind, fill, r, F))

Player/proc/RmChainData()
	var/list/F = RmChFillers()
	var/list/serve = list()
	var/more = 0
	for(var/mob/WorkShops/S in RmChStores())
		if(length(serve) >= 60)      // a city's hundreds: the first 60 rows, and how many more
			more++
			continue
		serve += list(RmChStoreRow(S, F))
	var/list/standing = list()
	for(var/kind in list("wood", "stone", "food"))
		var/list/S = remaster_board_standing ? remaster_board_standing[kind] : null
		standing += list(list("kind"=kind, "keep"=S ? S["keep"] : 0, "priority"=S ? S["priority"] : 2, "enabled"=S ? S["enabled"] : 0, "count"=RmJzStock(kind)))
	var/list/done = list()
	if(remaster_board_orders) for(var/list/O in remaster_board_orders) if(O["done"]) done += list(list("id"=O["id"], "label"=O["label"], "note"=O["note"]))
	var/list/recipes = list()
	for(var/list/R in RemasterSettlementRecipes()) recipes += list(list("id"=R["id"], "label"=R["label"], "uses"=R["cost"]))
	return list("serve"=serve, "more"=more, "fill"=F, "standing"=standing, "done"=done, "recipes"=recipes,
		"stations"=RemasterStationCatalog(), "stockpile"=!!RemasterStockpile(), "needs"=rm_ch_needs)

// Every 2 s with the allocator: the samples (every 10 s) and what needs the player, for the tabs and the Work button.
Player/proc/RmChPass()
	var/sample = world.time >= rm_ch_sample_at
	if(sample) rm_ch_sample_at = world.time + 100
	var/list/F = RmChFillers()
	var/serve = 0
	for(var/mob/WorkShops/S in RmChStores())
		if(sample) RmChSample(S)
		var/kind = RmChKind(S)
		var/code = RmChProblem(S, kind, RmChFill(S), RmChRates(S), F)
		if(code == 1 || code == 3 || code == 4 || code == 6) serve++
	var/make = 0
	if(rm_jz) for(var/list/Z in rm_jz) if(Z["kind"] == "make")
		if(sample) RmChSampleOrder(Z)
		if(rm_jz_prob && rm_jz_prob[Z["id"]]) make++
	rm_ch_needs = list(make, serve)

// Go to a store (Serve's rows): the eye and the 3D camera, only onto one of the player's own.
Player/RemasterTouchCommand(action, value)
	if(action != "chainlook") return ..()
	var/list/p = splittext("[value]", "|")
	if(length(p) != 3) return 0
	var/turf/T = locate(text2num(p[1]), text2num(p[2]), text2num(p[3]))
	if(!T) return 0
	var/ok = 0
	for(var/mob/WorkShops/S in RmChStores()) if(S.loc == T) ok = 1
	if(!ok) return 0
	loc = T
	RemasterCamTo(T)
	RemasterHUDTick()
	return 1

// --- Buildings order their furniture (the user, 2026-10-24: "make sure we can make the lodges") ---------------------
// A site short of wood or stone posts "Chop wood for building" by itself (Blueprints.dm RemasterSiteMissing). Short of a
// bed, a table, a chair or a door, it now asks the carpentry the same way: a Bulletin board station order, standing
// "build-<kind>", that the job board's villagers (or Board workers) take, for what the open sites still need less what
// the stores hold and what's on its way (in a builder's or a crafter's bag, or made and waiting to be lifted). Without a
// carpentry near the stockpile the site's note says to build one, as before.
Player/var/tmp/list/rm_ch_furn_at          // kind -> when the next count may run (it looks at every unit)
Player/var/tmp/list/rm_ch_lying            // pieces made that nobody at the station could lift (counted as on their way)
Player/RemasterSiteMissing(list/S, path)
	. = ..()
	var/kind = RemasterMaterialKind(path)
	if(!(kind in list("bed", "table", "chair", "door"))) return
	if(remaster_board_orders) for(var/list/O in remaster_board_orders) if(!O["done"] && O["standing"] == "build-[kind]") return
	if(!rm_ch_furn_at) rm_ch_furn_at = list("bed"=0, "table"=0, "chair"=0, "door"=0)
	if(world.time < rm_ch_furn_at[kind]) return
	rm_ch_furn_at[kind] = world.time + 50
	var/recipe = RmJzFurnitureRecipe(kind)
	if(!recipe) return
	var/need = 0
	for(var/list/X in RemasterOpenSites()) need += RemasterSiteNeedCount(X, path)
	need -= RemasterStoreCount(path, S["z"]) + RmChOnTheWay(path)
	if(need <= 0) return
	var/list/O = RemasterBoardPost("station", min(20, need), 1, 1, recipe, null, "build-[kind]")
	if(!O) return
	O["label"] = "Make [O["amount"]] [kind][O["amount"] == 1 ? "" : "s"] for building"
	RemasterNotice("Building needs [kind == "bed" ? "beds" : kind == "door" ? "a door" : "[kind]s"]: posted a carpentry order on the bulletin board.")

// Pieces of a kind on their way to a site: in a builder's load, in a crafter's goods, or made and not lifted yet.
Player/proc/RmChOnTheWay(path)
	var/n = 0
	for(var/mob/Monsters/W in UnitList) if(W.Owner == src)
		if(W.remaster_site_load) for(var/obj/Items/X in W.remaster_site_load) if(X.loc == W && istype(X, path)) n++
		if(W.remaster_station_goods) for(var/obj/Items/X in W.remaster_station_goods) if(X.loc == W && istype(X, path)) n++
		if(W.rm_ch_left) for(var/obj/Items/X in W.rm_ch_left) if(X && isturf(X.loc) && istype(X, path)) n++
	if(rm_ch_lying)
		for(var/obj/Items/X in rm_ch_lying.Copy()) if(!X || !isturf(X.loc)) rm_ch_lying -= X
		for(var/obj/Items/X in rm_ch_lying) if(istype(X, path)) n++
	return n

// An open "for building" furniture order that no open site needs any more (the building was removed, or its pieces came
// from elsewhere) is cancelled, from the job board's 2 s pass. Wood and stone orders keep the board's own rules.
Player/proc/RmJzFurnitureTidy()
	if(!remaster_board_orders) return
	for(var/list/O in remaster_board_orders.Copy())
		if(O["done"] || !(O["standing"] in list("build-bed", "build-table", "build-chair", "build-door"))) continue
		var/path = RemasterMaterialPath(copytext(O["standing"], 7))
		var/need = 0
		for(var/list/X in RemasterOpenSites()) need += RemasterSiteNeedCount(X, path)
		if(!need) RemasterBoardFinish(O, "No building needs it now")

// The carpentry's recipe for a kind of furniture (its station order id), the plain wooden one first; null without a
// carpentry near the stockpile.
Player/proc/RmJzFurnitureRecipe(kind)
	var/word = kind == "bed" ? "Bed" : kind == "table" ? "Table" : kind == "chair" ? "Chair" : "Door"
	var/any
	for(var/list/C in RemasterStationCatalog()) if(C["id"] == "carpentry")
		for(var/list/R in C["recipes"])
			if(!findtext(R["label"], word)) continue
			if(findtext(R["label"], "Wooden [word]")) return R["id"]
			if(!any) any = R["id"]
	return any

// --- Heavy pieces --------------------------------------------------------------------------------------------------
// A door weighs 100 and an axe 25: an Elf carries 120 and a Human 110, so neither lifts a door with its axe on. By hand a
// player puts the axe down first; workers now do the same on a store: the goods in the bag go down there (they count as
// stored) and then the tools (an axe, a pick: never armour or a weapon), the piece is carried, and the tools are picked
// up again after (RmChAsideBack). A piece a crafter made but couldn't lift counts as made only once it's lifted: before,
// the order closed on a door left on the carpentry floor, no site saw it, and the board posted another, and another.
#define RM_CH_ROOM 20                       // room for the next materials (a log, a stone)
mob/Monsters/var/tmp/list/rm_ch_left       // pieces it made at a station and couldn't lift yet
mob/Monsters/var/tmp/list/rm_ch_aside      // tools (and goods off a store) it set down to lift one
mob/Monsters/var/tmp/rm_ch_aside_since = 0  // when it started back for them
Player/var/tmp/list/rm_ch_aside_units      // units with tools set down (builders off duty go back for them)

// Set down under src what's in the way of lifting I: goods first, then tools. 1 if I fits now.
mob/Monsters/proc/RmChSetAside(obj/Items/I, Player/P)
	if(!I || I.weight > weightmax) return 0
	if(weight + I.weight <= weightmax) return 1
	var/stored = RemasterOnStore(src)
	var/list/goods = list()
	var/list/tools = list()
	for(var/obj/Items/X in src) if(X != I)
		if(X.ItemType == "Axe" || X.ItemType == "Pickaxe") tools += X
		else if(X.suffix == "(Carrying)" && !X.EquipmentType())
			// goods (wood, stone, food...) stay on the store, where they count as stored; its own things (a bed roll, a
			// rope) go down with its tools and come back with them: a builder lifting a door left its bed roll on the
			// stockpile for good and slept rough after (polish-loops, 2026-10-26)
			if(RemasterResourceKind(X)) goods += X
			else tools += X
	for(var/list/L in list(goods, tools))
		while(weight + I.weight > weightmax && length(L))
			var/obj/Items/H = L[1]
			for(var/obj/Items/G in L) if(G.weight > H.weight) H = G
			L -= H
			if(!DropItem(H) || !H) continue
			H.Owner = P
			if(L == tools || !stored)
				if(!rm_ch_aside) rm_ch_aside = list()
				rm_ch_aside += H
	if(rm_ch_aside && istype(P))
		if(!P.rm_ch_aside_units) P.rm_ch_aside_units = list()
		if(!(src in P.rm_ch_aside_units)) P.rm_ch_aside_units += src
	return weight + I.weight <= weightmax

// Back for what it set down once it carries no piece for work (a builder's load, a crafter's goods). 1 while at it.
mob/Monsters/proc/RmChAsideBack(Player/P, builder = 0)
	if(!rm_ch_aside) return 0
	for(var/obj/Items/X in src) if(istype(X, /obj/Items/Furniture) && ((X in remaster_site_load) || (X in remaster_station_goods))) return 0
	if(rm_ch_left) for(var/obj/Items/X in rm_ch_left) if(X && isturf(X.loc)) return 0   // a piece it made still to lift first
	var/obj/Items/I
	for(var/obj/Items/X in rm_ch_aside.Copy())
		if(!X || !isturf(X.loc) || X.z != z) rm_ch_aside -= X       // someone took it, or it's on another level
		else if(!I || get_dist(X, src) < get_dist(I, src)) I = X
	if(!rm_ch_aside_since) rm_ch_aside_since = world.time
	if(!I || world.time - rm_ch_aside_since > 600)
		// a minute and not back to them: they stay where they are (on a store the game's tool fetching finds them)
		rm_ch_aside = null
		rm_ch_aside_since = 0
		return 0
	if(get_dist(src, I) > 1)
		if(builder)
			RemasterSiteWalk(I.loc)
			RemasterSiteStatus("Going back for its [RmJzThingName(I)]")
		else RemasterWorkToward(I, "its [RmJzThingName(I)]")
		return 1
	for(var/obj/Items/X in rm_ch_aside.Copy()) if(get_dist(X, src) <= 1)
		rm_ch_aside -= X
		if(X.weight + weight <= weightmax) PickUpItem(X)
	if(!length(rm_ch_aside))
		rm_ch_aside = null
		rm_ch_aside_since = 0
	return 1

// A builder at a pile it can't lift a piece from: onto the piece's tile (on the store), the bag set down, then the piece.
mob/Monsters/RemasterSiteFetch(Player/P, list/S, path, obj/Items/I)
	if(I && isturf(I.loc) && get_dist(src, I) <= 1 && I.weight + weight > weightmax && I.weight <= weightmax && !RemasterCarriedCount(path))
		if(loc != I.loc)
			RemasterSiteWalk(I.loc)
			RemasterSiteStatus("Stepping over to the [RemasterMaterialKind(path)]")
			return
		if(RmChSetAside(I, P)) RemasterSiteStatus("Put its tools down to carry the [RemasterMaterialKind(path)]")
	return ..()

// The site's next piece first; back for its tools only when there's nothing to build or fetch just now.
mob/Monsters/RemasterSiteWork(Player/P, list/S)
	. = ..()
	if(rm_ch_aside && remaster_site_standby) RmChAsideBack(P, 1)

// A crafter let go of its order (another took it, or it gave up) with pieces it made still lying: they count as made,
// and builders fetch them where they lie (RemasterSiteSource below), so no site waits on a piece nobody will carry.
mob/Monsters/RemasterBoardRelease()
	if(rm_ch_left)
		var/Player/P = Owner
		var/list/O = istype(P) && remaster_board_claim ? P.RemasterBoardOrder(remaster_board_claim) : null
		for(var/obj/Items/X in rm_ch_left) if(X && isturf(X.loc))
			if(O) O["progress"] = min(O["amount"], O["progress"] + 1)
			if(istype(P))
				if(!P.rm_ch_lying) P.rm_ch_lying = list()
				P.rm_ch_lying += X
		rm_ch_left = null
	return ..()

// Furniture comes from the stores only (Blueprints.dm: a bed lying about may be someone's), but a piece made for
// building and left where it was made (rm_ch_lying) is the realm's: with none in the stores, the nearest of those.
Player/RemasterSiteSource(list/S, path, mob/Monsters/M)
	. = ..()
	if(. || !rm_ch_lying) return
	var/bd = 1#INF
	for(var/obj/Items/I in rm_ch_lying.Copy())
		if(!I || !isturf(I.loc))
			rm_ch_lying -= I
			continue
		if(!istype(I, path) || I.z != S["z"] || RemasterUnreachable(I)) continue
		var/d = get_dist(M, I)
		if(d < bd)
			bd = d
			. = I

// Builders whose site is done go back for their tools too.
Player/RemasterBlueprintTick()
	. = ..()
	if(!rm_ch_aside_units) return
	for(var/mob/Monsters/M in rm_ch_aside_units.Copy())
		if(!M || M.Owner != src || !M.rm_ch_aside)
			rm_ch_aside_units -= M
			continue
		if(M.remaster_job == "builder" && !M.remaster_site && !M.RemasterSiteBusy()) M.RmChAsideBack(src, 1)

mob/Monsters/RemasterStationTick(Player/P, list/O)
	// a piece it made that the bag couldn't take: the bag goes down on the stockpile, then the piece is fetched
	if(rm_ch_left)
		for(var/obj/Items/X in rm_ch_left.Copy()) if(!X || !isturf(X.loc))
			rm_ch_left -= X                           // lifted by someone else (a builder fetching "from a pile nearby")
			O["progress"] = min(O["amount"], O["progress"] + 1)
		if(!length(rm_ch_left))
			rm_ch_left = null
		else
			var/obj/Items/I = rm_ch_left[1]
			if(weight + I.weight > weightmax)
				var/turf/S = P.RemasterStockpile()
				if(I.weight <= weightmax && S && S.z == z)
					if(!RemasterWorkToward(S, "the stockpile")) return
					if(RmChSetAside(I, P))
						remaster_board_since = world.time        // under way (the job board's 2-minute rule)
						remaster_work_status = "Put its tools down to carry the [lowertext(I.name)]"
						return
				// nobody here can lift it: counted made, left where it lies, and the site's note says so
				for(var/obj/Items/X in rm_ch_left)
					O["progress"] = min(O["amount"], O["progress"] + 1)
					if(!P.rm_ch_lying) P.rm_ch_lying = list()
					P.rm_ch_lying += X
				O["note"] = "[I.name] ([I.weight]) is too heavy for [name] to carry: bring it to the stockpile by hand"
				rm_ch_left = null
				return
			if(!RemasterWorkToward(I, lowertext(I.name))) return
			if(PickUpItem(I))
				rm_ch_left -= I
				if(!length(rm_ch_left)) rm_ch_left = null
				if(!remaster_station_goods) remaster_station_goods = list()
				remaster_station_goods += I
				O["progress"] = min(O["amount"], O["progress"] + 1)
				remaster_board_since = world.time
				remaster_work_status = "Picked up the [lowertext(I.name)] it made"
			return
	// made pieces that fill the bag (two beds and an axe: an Orc's 125) go in before the next materials: the station's own
	// rule waits for 4 pieces or the order done, and a full bag took no materials, made nothing and was given up
	var/list/goods = RemasterStationCarrying(remaster_station_goods)
	if(length(goods) && weight + RM_CH_ROOM > weightmax)
		RemasterStoreFood(P, goods, "goods")
		remaster_board_since = world.time
		return
	var/p0 = O["progress"]
	var/list/near = list()
	for(var/obj/Items/X in range(1, src)) if(isturf(X.loc)) near += X
	. = ..()
	if(O["progress"] <= p0) return
	for(var/obj/Items/X in range(1, src)) if(isturf(X.loc) && !(X in near) && !(X in remaster_station_goods))   // made, left lying
		if(!rm_ch_left) rm_ch_left = list()
		rm_ch_left += X
		O["progress"] = max(p0, O["progress"] - 1)

// --- Loads go to the nearest store that takes them (jobs, 2026-10-24) -------------------------------------------------
// One stockpile tile has eight tiles round it to put loads down from, and a village of thousands can't all come to it:
// at 2,000 workers the carriers queued round it for minutes (tests/gather_score.dm). A load now goes to the nearest store
// on its level that takes all of it: the main stockpile, or a store painted with + Store or set on the Zones list
// (Zones.dm), so a store by the wood or the quarry takes their loads. Everything on any store counts the same (Board.dm
// RemasterStockCount), doesn't rot, and is fetched from by builders, crafters and cooks. A cart stop nearer still wins
// (Carts.dm, the same way).
// A stockpile painted as an area has many cells (Zones.dm RemasterZoneCells): the one nearest counting the crowd, its
// distance plus RM_STORE_CROWD for each unit standing round it, so carriers spread over it instead of all making for
// the nearest. not_this: the cell it's stuck at.
#define RM_STORE_CROWD 2
datum/remaster_order/var/tmp/repick_at = 0     // a carrier held up at a store tile picks another no sooner (RemasterDepositTick below)
Player/proc/RmJzStoreFor(mob/Monsters/M, turf/not_this)
	if(!remaster_zones) return null
	if(!rm_store_native) return RmJzStoreForDM(M, not_this)
	var/turf/E = RmJzStoreForEngine(M, not_this)   // the engine's loop over each zone's cells, the same tile (Native.dm)
	if(!rm_store_verify) return E
	var/turf/D = RmJzStoreForDM(M, not_this)       // shadow mode: the DM loop's tile used
	if(!(++rm_store_checked % 200)) world.log << "RMSTORE|checked|[rm_store_checked]|differ|[rm_store_differ]"
	if(D != E && ++rm_store_differ <= 30) world.log << "RMSTORE|differs|[M.x],[M.y]|DM [D ? "[D.x],[D.y]" : "none"]|engine [E ? "[E.x],[E.y]" : "none"]"
	return D

Player/proc/RmJzStoreForEngine(mob/Monsters/M, turf/not_this)
	var/turf/best
	var/bc = 1#INF
	for(var/list/Z in remaster_zones)
		if(Z["z"] != M.z) continue
		var/list/cells = RemasterZoneCells(Z)
		var/R = rm_store_scan(cells, M, not_this, bc, -1, rm_cell_aim, RM_STORE_CROWD, /mob/Monsters)
		if(isnum(R) && R == -1)   // a cell could win: whether this zone takes the load, asked here as the DM loop asks it
			R = rm_store_scan(cells, M, not_this, bc, M.RmJzZoneTakesLoad(Z, src) ? 1 : 0, rm_cell_aim, RM_STORE_CROWD, /mob/Monsters)
		if(!islist(R)) return RmJzStoreForDM(M, not_this)
		var/list/L = R
		if(L[1])
			best = L[1]
			bc = L[2]
	return best

Player/proc/RmJzStoreForDM(mob/Monsters/M, turf/not_this)
	var/turf/best
	var/bc = 1#INF
	for(var/list/Z in remaster_zones)
		if(Z["z"] != M.z) continue
		var/takes = -1      // looked at once, and only when a cell could win
		for(var/turf/T in RemasterZoneCells(Z))
			if(T == not_this || T.density) continue
			var/d = get_dist(T, M)
			if(d >= bc) continue
			if(takes < 0) takes = M.RmJzZoneTakesLoad(Z, src)
			if(!takes) break
			var/c = d + RM_STORE_CROWD * (RmStoreCrowd(T, M) + RmJzAimed(T))
			if(c < bc)
				bc = c
				best = T
	return best

// The carriers on their way to each store tile, so a group sent at once spreads over the cells instead of all making
// for the nearest (the store-area test: 40 sent together all chose one cell). A list kept as they're sent; one gone
// elsewhere (put its load down, sent to another, its delivery dropped) leaves it when it's next read.
mob/Monsters/var/tmp/turf/rm_store_aim
Player/var/tmp/list/rm_cell_aim            // store tile -> carriers sent to it

Player/proc/RmJzAim(mob/Monsters/M, turf/T)
	if(M.rm_store_aim == T) return
	M.rm_store_aim = T
	if(!T) return
	if(!rm_cell_aim) rm_cell_aim = list()
	var/list/L = rm_cell_aim[T]
	if(!L)
		L = list()
		rm_cell_aim[T] = L
	L += M

Player/proc/RmJzAimed(turf/T)
	var/list/L = rm_cell_aim ? rm_cell_aim[T] : null
	if(!L) return 0
	for(var/i = length(L), i >= 1, i--)
		var/mob/Monsters/M = L[i]
		if(!M || M.rm_store_aim != T || !M.remaster_delivery || M.remaster_delivery.target != T) L.Cut(i, i + 1)
	return length(L)

// Units standing on the 8 tiles round a store tile (its middle holds the goods), M not counted.
proc/RmStoreCrowd(turf/T, mob/M)
	var/n = 0
	for(var/turf/R in block(locate(max(1, T.x - 1), max(1, T.y - 1), T.z), locate(min(world.maxx, T.x + 1), min(world.maxy, T.y + 1), T.z))) if(R != T)
		for(var/mob/Monsters/U in R) if(U != M && U.density) n++
	return n

// The zone takes everything in the bag that a delivery puts down (and there is some).
mob/Monsters/proc/RmJzZoneTakesLoad(list/Z, Player/P)
	var/n = 0
	for(var/obj/Items/I in src) if(I.suffix == "(Carrying)" && !I.EquipmentType() && P.RemasterStockAccepts(I))
		if(!RemasterZoneAccepts(Z, I)) return 0
		n++
	return n > 0

Player/proc/RmJzStoreZoneAt(turf/T)
	return RemasterZoneOfCell(T)

// How many yards hold something the main stockpile takes (looked at most every 2 s).
Player/var/tmp/list/rm_jz_yards_c       // list(count, when)
Player/proc/RmJzYardsHolding()
	if(rm_jz_yards_c && world.time - rm_jz_yards_c[2] < RM_JZ_EVERY) return rm_jz_yards_c[1]
	var/n = 0
	if(remaster_zones) for(var/list/E in remaster_zones) if(E["yard"])
		var/any = 0
		for(var/turf/C in RemasterZoneCells(E))
			for(var/obj/Items/I in range(1, C)) if(isturf(I.loc) && RemasterMayCollect(I) && RemasterStockAccepts(I))
				any = 1
				break
			if(any) break
		n += any
	rm_jz_yards_c = list(n, world.time)
	return n

mob/Monsters/RemasterBeginDelivery(obj/Items/needed)
	. = ..()
	if(rm_jz_to_main)      // a haul from a yard (RmJzYardHaul): to the main stockpile, as the delivery chose
		rm_jz_to_main = 0
		if(remaster_delivery) remaster_delivery.to_main = 1
		return
	if(!. || !remaster_delivery) return
	var/Player/P = Owner
	if(!istype(P)) return
	var/turf/S = remaster_delivery.target
	var/turf/T = P.RmJzStoreFor(src)
	if(T && T != S && (!S || get_dist(src, T) + 3 < get_dist(src, S)))
		remaster_delivery.target = T
		remaster_delivery.path = null
		P.RmJzAim(src, T)   // the cell's crowd counts it (RmJzStoreFor)
		var/list/ZZ = P.RmJzStoreZoneAt(T)
		var/nm = ZZ ? ZZ["name"] : "store"
		remaster_order_status = "Taking resources to the [nm], then back to the task"

mob/Monsters/RemasterDepositTick(datum/remaster_order/O, Player/P)
	var/turf/S = O ? O.target : null
	// held up 3 s on the way to a store tile it isn't beside: another tile of a store that takes the load, if one's
	// no further than 6 tiles more (a painted stockpile's other cells; Zones.dm)
	if(istype(S) && istype(P) && O.issuer == P && !O.to_main && get_dist(src, S) > 1 && O.last_progress && world.time - O.last_progress > 30 && world.time >= O.repick_at)
		O.repick_at = world.time + 30
		var/turf/T2 = P.RmJzStoreFor(src, S)
		if(T2 && get_dist(src, T2) <= get_dist(src, S) + 6)
			O.target = T2
			O.path = null
			O.last_progress = world.time
			P.RmJzAim(src, T2)
			S = T2
	var/list/Z = istype(S) && istype(P) && S != P.RemasterStockpile() ? P.RmJzStoreZoneAt(S) : null
	if(!Z) return ..()
	if(O.issuer != P || S.density || S.z != z)
		// the store went: on to the main stockpile
		O.target = P.RemasterStockpile()
		O.path = null
		return 0
	if(!RemasterLandForWork()) return 0
	if(get_dist(src, S) > 1)
		RemasterApproach(O, S, 1)
		return 0
	destination = null
	var/amount = 0
	for(var/obj/Items/I in contents.Copy())
		if(I.suffix != "(Carrying)" || I.EquipmentType() || !P.RemasterStockAccepts(I) || !RemasterZoneAccepts(Z, I)) continue
		if(DropItem(I) && I)
			I.loc = S
			I.Owner = P
			amount++
	remaster_blocked = null
	remaster_wait_for_resume = 0
	var/nm = Z["name"]
	if(O == remaster_active) RemasterFinishOrder("Stored [amount] resource item[amount == 1 ? "" : "s"] in the [nm]")
	return 1

// --- The tick profile ---------------------------------------------------------------------------------------------
// The job board's cost under its own names (TickProfile.dm; tools/tick_profile.py and check_arena.py --profile report
// them). Here rather than in TickProfile.dm: that file comes first, and an override placed before a proc's own
// definition is chained the wrong way round.
Player/RmJobsTick(spread = 0)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/jobs", t0, w0)

Player/RmJzBuildersIdle()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/jobs/builders idle", t0, w0)

Player/RmJzTakeFromNormal(list/Z)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/jobs/take from normal", t0, w0)

mob/Monsters/RmJobStep(Player/P, list/RESERVED)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/settlement/any work", t0, w0)
