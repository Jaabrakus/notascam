// The walk loop without a look every tick (server cost, 2026-10-24; the user: "move the walk/order-check loop onto the
// shared clock next, keeping the first step of a new order instant"). Each unit's WalkTo loop (Creatures/Mob Procs.dm)
// sleeps a step between looks, as in the original; a player's idle units looked every tick (Specials.dm, so an order's
// first step came at once): at 5,000 units standing, 25,000 wakes a second. Now the loop (WalkLoop) sleeps a step idle
// or not, and whatever gives a unit somewhere to go brings its next look to now (RmWalkSoon): a new loop that looks
// then, the one asleep ending when it wakes (rm_walk_gen). The hooks: the order, attack and defence ticks (a click's
// first ones run at the click: Formations.dm RmFirstGo), the jobs' step, the roles' steps (builders, haulers, farmers,
// hunters), a defence called off (the way back), each HUD command (once the walks it spawned have set off: a captive's
// escort), and each player's track pass (care, captives, the rest). Never sooner than a step after its last step, so
// nobody walks faster. The engine wakes each loop itself: a wake costs what the original's did (the shared clock's
// dispatch in DM cost about twice as much, so a marching army was dearer on it).
mob/Monsters/var/tmp/rm_walk_gen = 0        // the loop allowed to look; an older one ends when it wakes
mob/Monsters/var/tmp/rm_walk_due = 0        // when the loop next looks (0: no loop)
mob/Monsters/var/tmp/rm_walk_booked = 0     // when that look was set (the step it waits is due - this)
mob/Monsters/var/tmp/rm_walk_running = 0    // its body is running (and may wait in a Bump): no second loop meanwhile
mob/Monsters/var/tmp/rm_walk_idle = 1       // its last look had nowhere to go: something to do brings the next look forward
mob/Monsters/var/tmp/rm_walk_usr            // the usr the loop started with (WalkTo's caller's), as the loop's own proc kept it
mob/Monsters/var/tmp/rm_walk_parked = 0     // a player's unit with nowhere to go: no loop at all until something gives it somewhere
mob/Monsters/var/tmp/rm_walk_step = 1       // the step it parked with (never sooner than this after its last step)
var/list/rm_walk_park_list = list()         // the parked (and some that were: RmWalkParkSweep drops those)
var/rm_walk_sweeping = 0
var/rm_walk_sweep_pass = 0                  // RmWalkParkSweep's pass (1..1e6, wraps): a unit's entries after its first in a pass are dropped
mob/Monsters/var/tmp/rm_walk_swept = 0      // the sweep pass that last read this unit (0 when it parks)
mob/Monsters/var/tmp/rm_walk_listed = 0     // it has its one entry in rm_walk_park_list (the sweep that drops it clears this)
#define RM_WALK_SWEEP 4                      // ticks between looks over the parked: what set a destination without saying so

// The loop starting (WalkTo, after its caller yields as the loop's spawn did): not owned (CanBeSlaved), its wander loop
// as the loop's end; otherwise its first look a step from now.
mob/Monsters/proc/WalkStart()
	rm_walk_parked = 0   // a loop of its own again (or its wander): not parked; the sweep drops its entry
	if(CanBeSlaved)
		RandomWalk(1)
		return
	rm_walk_usr = usr
	RmWalkLoopAt(world.time + RemasterStepDelay())

// A loop that looks at due; the one before it, asleep, ends when it wakes.
mob/Monsters/proc/RmWalkLoopAt(due)
	rm_walk_booked = world.time
	rm_walk_due = due
	var/gen = ++rm_walk_gen
	spawn(max(0, due - world.time)) WalkLoop(gen)

// The original loop, a look then a step's sleep, while it is the loop allowed to look; once the unit isn't owned, its
// wander loop (the loop's while(!CanBeSlaved) ending, then RandomWalk(1)).
mob/Monsters/proc/WalkLoop(gen)
	usr = rm_walk_usr
	while(gen == rm_walk_gen)
		rm_walk_idle = !destination
		rm_walk_running = 1
		WalkTick()
		rm_walk_running = 0
		if(gen != rm_walk_gen) return
		if(CanBeSlaved)
			rm_walk_due = 0
			RandomWalk(1)
			return
		var/step = RemasterStepDelay()
		if(rm_fs_hop)   // a far unit's look took rm_fs_hop route tiles (FarSteps.dm): it waits as long as those steps take
			step += (rm_fs_hop - 1) * rm_fs_step
			rm_fs_hop = 0
			rm_fs_until = world.time + step
		if(!destination && istype(Owner, /Player))   // nowhere to go: parked, no proc asleep and no wake, until it has somewhere
			rm_walk_due = 0
			rm_walk_step = step
			rm_walk_parked = 1
			rm_walk_swept = 0
			if(!rm_walk_listed)   // one entry a unit: unparked and parked again before a sweep, it keeps its first place
				rm_walk_listed = 1
				rm_walk_park_list += src
			if(!rm_walk_sweeping)
				rm_walk_sweeping = 1
				RmClockWorldBook("WalkParkSweep", RM_WALK_SWEEP)   // on the unit clock (UnitClock.dm)
			return
		rm_walk_booked = world.time
		rm_walk_due = world.time + step
		sleep(step)

// Somewhere to go, for a unit whose last look had nowhere to go (the idle ones the original's every-tick look was for:
// one already on its way looks a step after its last look, as before): its next look now (once the proc giving it
// yields), never sooner than a step after its last step.
// RemasterStepDelay isn't asked (on a road it carries a fraction from one call to the next): the step is what its
// look waits, due - booked.
mob/Monsters/proc/RmWalkSoon()
	if(rm_walk_parked)
		RmWalkUnpark()
		return
	if(rm_walk_running || !rm_walk_due || !rm_walk_idle) return
	var/want = max(world.time, remaster_stepped_at + rm_walk_due - rm_walk_booked)
	if(want < rm_walk_due) RmWalkLoopAt(want)

// A parked one's loop again: its look now (once the proc giving it yields), never sooner than a step after its last step.
mob/Monsters/proc/RmWalkUnpark()
	// A unit set loose wanders (RandomWalk), and that loop may sleep at once and, its land awake, never end: the caller
	// (the sweep, an order tick) goes on, never held there for good (S2, 10-27).
	set waitfor = 0
	rm_walk_parked = 0
	if(CanBeSlaved)                 // not owned any more: its wander loop, as the walk loop's end
		RandomWalk(1)
		return
	rm_walk_idle = 1
	RmWalkLoopAt(max(world.time, remaster_stepped_at + rm_walk_step))

// What gives a parked unit somewhere to go without one of the hooks below (578 places set destination): every
// RM_WALK_SWEEP ticks, a parked unit with a destination, or no longer owned or a player's, starts its loop again. The
// unhooked ones set off within RM_WALK_SWEEP ticks, as an idle look a step later did; the hooked ones at once. A job on
// the unit clock (UnitClock.dm) while anything is parked: it ends on the run that finds nobody parked, as its loop did.
proc/RmWalkParkSweep()
	if(!length(rm_walk_park_list))
		rm_walk_sweeping = 0
		return
	RmClockWorldBook("WalkParkSweep", RM_WALK_SWEEP)   // the next one first: one that fails can't stop the sweeps for good
	rm_walk_sweep_pass = rm_walk_sweep_pass >= 1000000 ? 1 : rm_walk_sweep_pass + 1   // wraps: DM numbers are 32-bit floats
	var/pass = rm_walk_sweep_pass
	// in place and in order (S2, 10-27): the still parked are written back over the list and the rest cut off, with no
	// copy and no keep list (8-42k entries at 2,000 workers; a copy that size is a large-object allocation). A unit has
	// one entry (rm_walk_listed); the pass mark still skips a second, if one is ever there. Unparking only spawns its
	// loop (RmWalkUnpark), so nothing joins the list while this goes round it.
	var/list/L = rm_walk_park_list
	var/j = 0
	for(var/i = 1, i <= length(L), i++)
		var/mob/Monsters/M = L[i]
		if(!istype(M)) continue
		if(!M.rm_walk_parked || M.rm_walk_swept == pass)
			if(M.rm_walk_swept != pass) M.rm_walk_listed = 0   // not parked now: its entry goes
			continue
		M.rm_walk_swept = pass
		if(M.destination || M.CanBeSlaved || !istype(M.Owner, /Player))
			M.rm_walk_listed = 0
			M.RmWalkUnpark()
		else
			j++
			L[j] = M
	if(j < length(L)) L.Cut(j + 1)

// The player's units that have somewhere to go and are looking later than that.
Player/proc/RmWalkScan()
	for(var/mob/Monsters/M in UnitList) if(M.destination && M.Owner == src) M.RmWalkSoon()

// --- what gives a unit somewhere to go --------------------------------------------------------------------------------
mob/Monsters/RemasterOrderTick()
	. = ..()
	if(destination) RmWalkSoon()

mob/Monsters/RemasterAttackTick()
	. = ..()
	if(destination) RmWalkSoon()

mob/Monsters/RemasterDefenseTick()
	. = ..()
	if(destination) RmWalkSoon()

mob/Monsters/RmJobStep(Player/P)
	. = ..()
	if(destination) RmWalkSoon()

mob/Monsters/RemasterCancelDefense(resume = 0)   // the way back to what it was doing (also the defence-mode command, Defense.dm)
	. = ..()
	if(destination) RmWalkSoon()

mob/Monsters/RemasterSiteWork(Player/P, list/S)  // a builder at its site (Blueprints.dm; the jobs' Builders row)
	. = ..()
	if(destination) RmWalkSoon()

mob/Monsters/RemasterRoleTick(Player/P)          // a hauler's and the other roles' step (Delivery.dm; the jobs' Haulers row)
	. = ..()
	if(destination) RmWalkSoon()

mob/Monsters/RemasterFoodTick(Player/P)          // a farmer's or hunter's step (FoodRoles.dm; the jobs' farm rows)
	. = ..()
	if(destination) RmWalkSoon()

Player/RemasterTouchCommand(action, value)
	. = ..()
	spawn(0) RmWalkScan()   // after the walks the command spawned have set off (Captives.dm RmCapEscort)

Player/RemasterTrack(spread = 0)
	. = ..()
	RmWalkScan()

// The movement watcher (idea 4, step 1, from the crimson-grid survey: "one owner for a unit's movement"; staged 10-27):
// with RM_MOVE_WATCH=1 in the server's environment, every walk look with somewhere to go (WalkTick with a destination)
// notes which of the unit's drivers are active (an order, a delivery, an attack, a defence, a building site, a job's work
// spot; a wild or NPC unit's own AI) and whether its destination came from one of them (that driver's next route tile or
// its target). It counts two drivers active at once, and destinations none of the active drivers gave: set somewhere else
// (638 lines in 106 files can set one). Once a game minute RMMOVE|watch|t=..|looks=..|<what>=<n>;... goes to world.log, and
// the first examples as RMMOVE|example|... Off (the default): one var read a look. On: it only reads; nothing it does
// changes what any unit does.
var/rm_mw_on = -1             // -1 until read (RM_MOVE_WATCH)
var/list/rm_mw_counts = list()
var/list/rm_mw_seen = list()   // kinds already shown as an example (kept across lines)
var/rm_mw_looks = 0
var/rm_mw_at = 0
// The watcher's globals are named rm_mw_* and read as global.* inside unit procs: a unit var of the same name would win
// there (WeaponSkills.dm's mob var rm_move_at did, in the first try: every look wrote a line).

proc/RmMoveWatchOn()
	if(global.rm_mw_on < 0)
		global.rm_mw_on = world.GetConfig("env", "RM_MOVE_WATCH") == "1"
		global.rm_mw_at = world.time + 600
	return global.rm_mw_on

// Whether the destination comes from a driver going to T along route L: L's next tile, T itself, or a straight step at T
// (a tile beside the unit, nearer T: a group's step when its route waits for the per-tick budget, a melee step).
mob/Monsters/proc/RmMoveFrom(list/L, atom/T)
	if(length(L) && L[1] == destination) return 1
	if(!T) return 0
	if(T == destination) return 1
	if(ismovable(T) && Rm3DGone(T)) return 0   // a foe deleted since (deleted refs aren't null here: View3D.dm)
	var/atom/D = destination
	return isturf(D) && isturf(T.loc || T) && get_dist(src, D) <= 1 && get_dist(D, T) < get_dist(src, T)

// The unit's active drivers: name -> 1 when the destination comes from that driver (RmMoveFrom), else 0.
mob/Monsters/proc/RmMoveDrivers()
	. = list()
	var/datum/remaster_order/O = remaster_active
	if(O) .[O.automatic ? "order (automatic)" : "order (player)"] = RmMoveFrom(O.path, O.target)
	var/datum/remaster_order/V = remaster_delivery
	if(V) .["delivery"] = RmMoveFrom(V.path, V.target)
	var/datum/remaster_attack/K = remaster_attack
	if(K) .["attack"] = RmMoveFrom(K.path, K.target || K.goal)
	var/datum/remaster_defense/F = remaster_defense
	if(F) .["defence"] = RmMoveFrom(F.path, null)
	if(length(remaster_site_path)) .["building site"] = RmMoveFrom(remaster_site_path, null)
	if(remaster_work_destination) .["job work spot"] = RmMoveFrom(null, remaster_work_destination)
	if(!istype(Owner, /Player)) .["wild or NPC AI"] = 1

mob/Monsters/proc/RmMoveWatch()
	global.rm_mw_looks++
	var/list/A = RmMoveDrivers()
	var/names = ""
	var/from = 0
	for(var/k in A)
		names += (names ? " + " : "") + k
		if(A[k]) from++
	if(length(A) > 1) RmMoveCount("drivers at once: [names]")
	if(!from) RmMoveCount("destination from none of: [length(A) ? names : "no driver"]")
	if(world.time >= global.rm_mw_at) RmMoveFlush()

mob/Monsters/proc/RmMoveCount(what)
	global.rm_mw_counts[what] = (global.rm_mw_counts[what] || 0) + 1
	if(!global.rm_mw_seen[what] && length(global.rm_mw_seen) < 40)
		global.rm_mw_seen[what] = 1
		var/atom/D = destination
		world.log << "RMMOVE|example|[what]|[type] at [x],[y],[z] to [D ? "[D.x],[D.y],[D.z]" : "?"]|order [remaster_active ? remaster_active.kind : "-"]|status [remaster_order_status]"

proc/RmMoveFlush()
	global.rm_mw_at = world.time + 600
	var/list/out = list()
	for(var/k in global.rm_mw_counts) out += "[k]=[global.rm_mw_counts[k]]"
	world.log << "RMMOVE|watch|t=[world.time]|looks=[global.rm_mw_looks]|[jointext(out, ";")]"
	global.rm_mw_counts = list()
	global.rm_mw_looks = 0

// the tick profiler (TickProfile.dm): the walk loops' looks
mob/Monsters/WalkTick()
	if(global.rm_mw_on && destination && RmMoveWatchOn()) RmMoveWatch()   // the movement watcher (above): off unless RM_MOVE_WATCH=1
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("creature walk tick", t0, w0)
