// Each player's track spread over ticks (server cost, 2026-10-24). The track (QoL.dm RemasterTrack: orders, explore,
// the HUD and the 3D scene) took 150-290 ms with 200 units, all in one tick twice a second, and the whole game stood
// still for it: a stutter every half second (reports/server-cost/real-200-native.md). Now a run does at most
// RM_TRACK_SLICE ms of it in a tick, for all players together, then goes on next tick from a safe point: between the
// track's parts, between units in explore, orders and the HUD's unit list, and in the 3D scene before the units are
// listed (so they are sent as they stand). The work and its order are the same; only the ticks it happens in change. A run starts every
// REMASTER_TRACK_DELAY ticks as before, or when the last one is done if that took longer (the screen then updates a
// little less often instead of the game freezing). Calls from verbs and tests (no spread) run in one go as before.
#define RM_TRACK_SLICE 30      // ms of track work in one tick, all players together

// How far behind the server is (the coordinator's option 1, 2026-10-24): 0 keeping up; 1, 2, 3 the more it falls behind
// real time. Set once a tick by server-cost's orders-first code; the HUD's tiers (HudView.dm) and the 3D view's read it to
// let cosmetic work step back. Never delayed whatever it says: health, alerts, selection, orders, on-screen moves.
var/rm_shed_level = 0

var/rm_track_tick = -1         // the tick rm_track_used counts
var/rm_track_used = 0          // ms of track work done in it so far

// The one tick ledger (server cost, 10-25; planning/SYSTEMS_MAP.md Part 6 step 1, the user's "hitches first"): one count
// of the ms that the order hand-out (Orders.dm), first steps (Formations.dm) and the track (with its 3D view, View3D.dm)
// did in this tick, and the click's plan and its group's slots (counted, never held). Order work comes first: it keeps
// its own shares and minimums and adds what it did, and past its minimums it stops at the ledger's cap (rm_tick_cap). The
// track gives way: a safe point pauses once the ledger, plus the order work still due in this tick, reaches its line
// (RM_TRACK_SLICE; the 3D view's rm3d_slice). Same-tick wake order isn't fixed, so the order work still due is held back for: a later batch of
// first steps, or a hand-out, that had its share in the ledger's last tick and not yet in this one.
// rm_tick_ledger = 0: each part counts alone, as before.
var/rm_tick_ledger = 1
var/rm_tick_cap = 50           // ms: the ledger's cap; order work (past its minimums) stops there too (formations, 10-25; 0: only its own shares)
var/rm_tick_at = -1            // the tick rm_tick_used counts
var/rm_tick_prev = -1          // the ledger's tick before it
var/rm_tick_used = 0           // ms of ledger work done in it so far
var/list/rm_give_live = list()      // hand-outs under way over ticks (Orders.dm), one entry each: a player may have two
var/rm_first_at = -1           // the tick the first steps' later batch last ran (Formations.dm RmFirstLater)
/datum/rm_give
	var/at = -1               // the tick this hand-out last had its share

proc/RmTickUsed()
	if(rm_tick_at != world.time)
		if(rm_prof && rm_tick_used > 0) RmProfAdd("ledger in a tick", rm_tick_used)
		rm_tick_prev = rm_tick_at
		rm_tick_at = world.time
		rm_tick_used = 0
	return rm_tick_used

proc/RmTickCharge(ms)
	RmTickUsed()
	if(ms > 0) rm_tick_used += ms

// Order work still due in this tick (ms): it had its share in the ledger's last tick and hasn't yet in this one.
proc/RmTickOwed()
	RmTickUsed()
	. = 0
	if(rm_first_running && rm_first_at == rm_tick_prev) . += RM_FIRST_LATER_MS
	var/list/dead
	for(var/datum/rm_give/G in rm_give_live)
		if(G.at == rm_tick_prev) . += RM_GIVE_LATER_MS
		else if(world.time - G.at > 50)   // a hand-out that died (an error mid-way) never ended: dropped (S2b, 10-27)
			if(!dead) dead = list()
			dead += G
	if(dead) rm_give_live -= dead

// Optional work (hud-craft's new portraits and item icons, 10-25): it goes only while this tick has room under its line
// (RM_TICK_OPTIONAL, below the track's), the rest next time, and never ahead of orders or the track. Do one piece, then
// ask again. Inside a player's track run (between its safe points), ask that player: RmOptionalRoom() counts the run's
// work so far first, and the run's own counting covers the piece. Anywhere else, ask RmTickRoom() and RmTickCharge()
// what the piece took. A piece that can't be split (a first sheet decode) still runs whole once started.
#define RM_TICK_OPTIONAL 20    // ms: optional work's line on the ledger
proc/RmTickRoom(line = RM_TICK_OPTIONAL)
	return max(0, line - (rm_tick_ledger ? RmTickUsed() + RmTickOwed() : 0))

Player/proc/RmOptionalRoom(line = RM_TICK_OPTIONAL)
	RmTrackPiece()
	return max(0, line - (rm_tick_ledger ? rm_tick_used + RmTickOwed() : rm_track_used))

Player/var/tmp
	rm_track_run = 0           // the run under way (0: none)
	rm_track_runs = 0
	rm_track_seen = -1000      // world.time the run last went on (one that stops going on died with an error)
	rm_track_next = 0          // world.time the next run is due
	rm_track_from = 0          // world.tick_usage where the piece now running began
	rm_track_ms = 0            // ms the run has taken so far
	rm_track_tick_ms = 0       // ...of them in this tick, not yet counted by the profiler
	rm_track_paused = 0        // the run has gone on into another tick

// RemasterLoop (QoL.dm), every tick: start this player's run when it is due.
Player/proc/RmTrackDue()
	if(rm_track_run && world.time - rm_track_seen < 20) return
	if(world.time < rm_track_next) return
	rm_track_next = world.time + REMASTER_TRACK_DELAY
	rm_track_run = ++rm_track_runs
	rm_track_seen = world.time
	spawn(0) RmTrackRun(rm_track_run)

Player/proc/RmTrackRun(run)
	rm_track_from = world.tick_usage
	rm_track_ms = 0
	rm_track_tick_ms = 0
	rm_track_paused = 0
	RemasterTrack(1)
	RmTrackPiece()
	if(rm_prof)
		if(rm_track_paused) rm_prof_top += rm_track_tick_ms   // a run that went on was not timed as "track" (TickProfile.dm)
		RmProfAdd("track run", rm_track_ms)
	if(rm_track_run == run) rm_track_run = 0

// A safe point in a spread run: once this tick's share is used, the rest goes on next tick.
Player/proc/RmTrackPause(slice = RM_TRACK_SLICE)   // slice: a smaller share for a part (the 3D view's, View3D.dm)
	RmTrackPiece()
	if((rm_tick_ledger ? rm_tick_used + RmTickOwed() : rm_track_used) < slice) return   // the one tick ledger, above
	if(rm_prof) rm_prof_top += rm_track_tick_ms
	rm_track_tick_ms = 0
	rm_track_paused = 1
	var/depth = rm_prof_depth   // the profiler's open calls are this run's, not those of what runs while it waits
	rm_prof_depth = 0
	sleep(1)
	rm_prof_depth = depth
	rm_track_seen = world.time
	rm_track_from = world.tick_usage

// The work since the last safe point, counted to this tick's share.
Player/proc/RmTrackPiece()
	if(rm_track_tick != world.time)
		if(rm_prof && rm_track_used > 0) RmProfAdd("track in a tick", rm_track_used)
		rm_track_tick = world.time
		rm_track_used = 0
	var/ms = max(0, (world.tick_usage - rm_track_from) * world.tick_lag)   // tick_usage is a share of the tick, tick_lag 1 = 100 ms
	rm_track_from = world.tick_usage
	rm_track_used += ms
	RmTickCharge(ms)
	rm_track_ms += ms
	rm_track_tick_ms += ms

proc/RmProfAdd(name, ms)
	rm_prof_ms[name] += ms
	rm_prof_n[name] += 1
	if(ms > rm_prof_max[name]) rm_prof_max[name] = ms
