// The world's timers on the unit clock (rts-feel, 2026-10-25; tools/rts_feel/ring/apply_ring.py): each job runs on the
// very ticks its old loop woke. The old loops are copied here (RcOld*, WalkLoop.dm, Doors.dm, FarRecords.dm as of
// 2026-10-25 12:xx), their bodies only noting what they would do, and run beside the game's jobs from the same starts:
//   - the parked walk sweep: 80 player units park and are given somewhere to go, some by a hook (an order: RmWalkSoon),
//     most by setting destination alone (only the sweep sees those);
//   - the door loop: three own doors opened, someone in the doorway a while, then empty;
//   - the far records' loop (off, as in the game: its wake-all branch).
// The jobs' runs are read off the clock's own book (a probe job on each tick, before the world's jobs run), and what the
// sweep did off its effects (RmWalkUnpark not from a hook). Also: an unparked unit's first look comes on its due tick.
// On the base (no world jobs) only the first-look check means anything.
//   tools/check_arena.py --test ring_check.dm --entry RcRun
var/list/rc_old = list("WalkParkSweep"=list(), "Doors"=list(), "FarRecords"=list())   // job -> ticks the old loop woke
var/list/rc_new = list("WalkParkSweep"=list(), "Doors"=list(), "FarRecords"=list())   // job -> ticks the job ran
var/list/rc_old_sets = list()   // tick -> the units the old sweep would set off
var/list/rc_new_sets = list()   // tick -> the units the sweep set off
var/list/rc_hook_sets = list()  // tick -> the units a hook set off (an order: RmWalkSoon)
var/list/rc_dest_at = list()    // unit -> when this test last gave it somewhere to go without a hook
var/list/rc_old_still = list()  // tick -> the parked units the old sweep saw with nowhere to go
var/list/rc_probe_state = list() // tick -> unit -> its state just before the job's run (for the old loop's would-sets)
var/rc_tw_sweeping = 0
var/rc_tw_door_on = 0
var/rc_soon = 0
var/list/rc_lags = list()       // an unparked unit's first look: ticks after its due
mob/Monsters/var/tmp/rc_unparked = 0

// --- the probe: on the clock's tick, before the world's jobs of that tick, which of them are due ---
mob/RmClockRun(job)
	if(job != "RcProbe") return ..()
	var/t = world.time
	var/list/D = ("rm_clock_world_due" in global.vars) ? global.vars["rm_clock_world_due"] : null
	if(D) for(var/k in rc_new) if(D[k] == t) rc_new[k] += t
	var/list/S = rc_old_sets["[t]"]   // the units the old loop would set off this tick, as they are just before the job runs
	if(S)
		var/list/st = list()
		for(var/r in S)
			var/mob/Monsters/M = locate(r)
			st[r] = !M ? "gone" : (!M.rm_walk_parked ? "set off already" : (!M.destination ? "its destination taken away" : "parked, somewhere to go"))
		rc_probe_state["[t]"] = st
	RmClockBook(src, "RcProbe", 1)

// --- the sweep's effects ---
mob/Monsters/RmWalkSoon()
	rc_soon++
	. = ..()
	rc_soon--
mob/Monsters/RmWalkUnpark()
	var/k = "[world.time]"
	var/list/sets = rc_soon ? rc_hook_sets : rc_new_sets
	if(!sets[k]) sets[k] = list()
	sets[k] += "\ref[src]"
	rc_unparked = 1
	return ..()
mob/Monsters/WalkLoop(gen)
	if(rc_unparked && gen == rm_walk_gen)
		rc_unparked = 0
		rc_lags += world.time - rm_walk_due
	. = ..()
	if(rm_walk_parked && !rc_tw_sweeping)   // the old loop's start, as WalkLoop.dm's
		rc_tw_sweeping = 1
		spawn(RM_WALK_SWEEP) RcOldSweep()

// --- the old loops, their bodies only noting ---
proc/RcOldSweep()
	while(1)
		rc_old["WalkParkSweep"] += world.time
		if(!length(rm_walk_park_list)) break
		var/list/S = list()
		var/list/N = list()
		for(var/mob/Monsters/M in rm_walk_park_list) if(M.rm_walk_parked)
			if(M.destination || M.CanBeSlaved || !istype(M.Owner, /Player)) S += "\ref[M]"
			else N += "\ref[M]"
		if(length(S)) rc_old_sets["[world.time]"] = S
		rc_old_still["[world.time]"] = N
		sleep(RM_WALK_SWEEP)
	rc_tw_sweeping = 0

proc/RcOldDoors()   // the old loop checked its list right after its body: read it once this tick's job has run (a tick on)
	if(!length(rm_doors_auto))
		rc_tw_door_on = 0
		return
	sleep(5)
	while(1)
		rc_old["Doors"] += world.time
		sleep(1)
		if(!length(rm_doors_auto)) break
		sleep(4)
	rc_tw_door_on = 0

proc/RcOldFar()
	while(1)
		sleep(RM_FAR_EVERY)
		rc_old["FarRecords"] += world.time
		if(world.time > 1200) return

proc/RcOpen(obj/Items/Furniture/Doors/D)   // a unit's step opening it (Doors.dm RmDoorOpen), the old loop started as it was
	var/was = rm_door_loop_on
	RmDoorOpen(D)
	if(!was && !rc_tw_door_on)
		rc_tw_door_on = 1
		spawn(0) RcOldDoors()

proc/RcDoor(Player/P, x, y)
	var/turf/T = locate(x, y, 1)
	T.density = 0
	T.opacity = 0
	var/obj/Items/Furniture/Doors/WoodenDoor/D = new(T)
	D.Placed = 1
	D.Door = 1
	D.Owner = P
	D.density = 1
	D.opacity = 1
	return D

proc/RcSame(list/A, list/B)
	if(length(A) != length(B)) return 0
	for(var/i = 1, i <= length(A), i++) if(A[i] != B[i]) return 0
	return 1

proc/RcRun()
	if(world.time < 150) spawn(150 - world.time) RcOldFar()   // the far loop's start (FarRecords.dm world/New: spawn(150))
	sleep(30)
	remaster_fog = 0
	rand_seed(1025)
	var/mob/probe = new /mob(locate(1, 1, 2))
	RmClockStart(probe, "RcProbe", 1)
	var/Player/P = new(locate(60, 50, 1))
	P.UnitList = list()
	P.key = "ringcheck"
	Players += P
	usr = P
	var/list/U = list()
	for(var/i = 1, i <= 80, i++) U += ObHuman(P, rand(10, 110), rand(10, 90), 1, 0)
	var/list/doors = list(RcDoor(P, 20, 95), RcDoor(P, 60, 95), RcDoor(P, 100, 95))
	var/mob/Monsters/stand = U[1]
	sleep(20)
	var/t0 = world.time
	while(world.time - t0 < 700)
		var/dt = world.time - t0
		if(prob(30))   // somewhere to go without a hook: only the sweep sees it
			var/mob/Monsters/M = pick(U)
			if(M.rm_walk_parked && M != stand)
				M.destination = locate(clamp(M.x + rand(-8, 8), 2, 118), clamp(M.y + rand(-8, 8), 2, 90), 1)
				rc_dest_at["\ref[M]"] = world.time
		if(prob(6))    // an order: the hook
			var/mob/Monsters/M = pick(U)
			if(M != stand) ObClick(P, list(M), locate(clamp(M.x + rand(-8, 8), 2, 118), clamp(M.y + rand(-8, 8), 2, 90), 1))
		// the doors: opened at 50, 53 and 230; someone in the first one's doorway from 51 to 90; all opened again at 400
		if(dt == 50 || dt == 400) RcOpen(doors[1])
		if(dt == 53 || dt == 400) RcOpen(doors[2])
		if(dt == 230 || dt == 401) RcOpen(doors[3])
		if(dt == 51)
			var/obj/D1 = doors[1]
			stand.loc = D1.loc
		if(dt == 91) stand.loc = locate(20, 80, 1)
		sleep(1)
	sleep(60)
	// the comparison
	var/list/parts = list()
	var/ok = 1
	for(var/k in rc_old)
		var/list/A = rc_old[k]
		var/list/B = rc_new[k]
		var/same = RcSame(A, B)
		ok &= same
		parts += "[k]: old [length(A)] wakes, new [length(B)] runs[same ? ", the same ticks" : " DIFFER (old [jointext(A.Copy(1, min(length(A), 12) + 1), ",")] | new [jointext(B.Copy(1, min(length(B), 12) + 1), ",")])"]"
	world.log << "CK|the world's timers run on the ticks their old loops woke|[ok && length(rc_old["WalkParkSweep"]) > 20 && length(rc_old["Doors"]) > 5]|[jointext(parts, "; ")]"
	// The old loop woke among the tick's procs in no fixed order; the job runs after them. A unit given somewhere to go
	// within that tick, after the old loop's look, is set off by the job that tick instead of the next sweep (the order
	// the old loop had whenever it woke last). Never later: the old loop never sets off one the job doesn't (or an order did).
	var/n = 0
	var/same = 0
	var/sooner = 0
	var/sooner_test = 0
	var/hooked = 0
	var/changed = 0
	var/list/changed_notes = list()
	var/list/odd = list()
	for(var/k in rc_old_sets | rc_new_sets)
		n++
		var/list/A = rc_old_sets[k] || list()
		var/list/B = rc_new_sets[k] || list()
		same += length(A & B)
		for(var/r in B - A)
			if(isnull(rc_old_still[k]))   // the old loop didn't look that tick (the ticks check above says so too)
				if(length(odd) < 6) odd += "t=[k] only the job, the old loop not awake: [r]"
			else if(rc_dest_at[r] == text2num(k)) sooner_test++
			else sooner++                 // parked with nowhere to go at the old loop's look, or parked after it
		for(var/r in A - B)
			var/list/H = rc_hook_sets[k]
			var/list/st = rc_probe_state[k]
			var/why = st ? st[r] : null
			if(H && (r in H)) hooked++
			else if(why == "set off already" || why == "its destination taken away" || why == "gone")
				changed++
				if(length(changed_notes) < 4) changed_notes += "t=[k]: [why]"
			else if(length(odd) < 6) odd += "t=[k] only the old loop: [r] ([why || "no probe"])"
	world.log << "CK|the sweep sets off the same units, never later|[n > 20 && !length(odd)]|[n] sweeps that set someone off: [same] units the same; set off that tick instead of 4 later (somewhere to go given within the tick, after the old loop's look): [sooner_test] by this test, [sooner] by the game; [hooked] by an order within that tick; [changed] changed within the tick before the job looked[length(changed_notes) ? " ([jointext(changed_notes, ", ")])" : ""][length(odd) ? "; UNEXPLAINED: " + jointext(odd, "; ") : ""]"
	var/worst = 0
	var/late = 0
	for(var/v in rc_lags)
		worst = max(worst, v)
		if(v > 0) late++
	world.log << "CK|an unparked unit's first look comes on its due tick|[length(rc_lags) > 50 && !late]|[length(rc_lags)] unparked, [late] late, worst [worst] ticks"
	world.log << "CK|complete"
