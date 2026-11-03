#!/usr/bin/env python3
"""The clean-up fold, step 3 (planning/SYSTEMS_MAP.md Part 6; rts-feel, 2026-10-25): the world's own timers become jobs on
the one unit clock (UnitClock.dm) instead of loops of their own.
  UnitClock.dm  world jobs beside the units' ones: RmClockWorldBook(job, ticks), RmClockWorldStop(job), run after the
                units' jobs of their tick in the order booked, with waitfor 0 and the usr they were booked with (a loop
                kept its spawner's); the one list of the world's timers is RmClockWorldRun's switch.
  WalkLoop.dm   RmWalkParkSweep: every RM_WALK_SWEEP ticks while something is parked, as its while() did.
  Doors.dm      RmDoorLoop: every 5 ticks while a door it opened is open, as its while() did.
  FarRecords.dm RmFarLoop: RM_FAR_EVERY after each run ends, the first 150 + RM_FAR_EVERY after world start.
Bodies unchanged. Exact-match edits, idempotent, Latin-1 safe.
    python3 tools/rts_feel/ring/apply_ring.py <game folder>"""
import os, sys, tempfile
from pathlib import Path

EDITS = {
'Code/Remastered/UnitClock.dm': [
("""		if("Regen") RegenTick()
		else RmWildRun(job)   // the wild creatures' loops (Remastered/WildClock.dm)""",
"""		if("Regen") RegenTick()
		else RmWildRun(job)   // the wild creatures' loops (Remastered/WildClock.dm)

// The world's own timers on this clock (rts-feel, 2026-10-25; the clean-up fold, planning/SYSTEMS_MAP.md Part 6 step 3):
// each was a loop of its own, asleep between runs. Now a job by name: its first run ticks from its booking (the loop's
// sleep), and its body books the next one, or doesn't (the loop ended). They run after the units' jobs of their tick, in
// the order they were booked, with waitfor 0, and with the usr they were booked with (a loop kept its spawner's).
var/list/rm_clock_world = new/list(RM_CLOCK_SLOTS)   // slot -> the world jobs due on a tick of that slot
var/list/rm_clock_world_due = list()                 // job -> the tick it is next due on (no entry: not booked)
var/list/rm_clock_world_usr = list()                 // job -> the usr it was booked with

proc/RmClockWorldBook(job, ticks)
	var/due = world.time + max(1, round(ticks)) * world.tick_lag
	rm_clock_world_due[job] = due
	rm_clock_world_usr[job] = usr
	var/i = (round(due / world.tick_lag) % RM_CLOCK_SLOTS) + 1
	var/list/L = rm_clock_world[i]
	if(!L)
		L = list()
		rm_clock_world[i] = L
	L += job
	if(!rm_clock_running)
		rm_clock_running = 1
		spawn(0) RmClockLoop()

proc/RmClockWorldStop(job)
	rm_clock_world_due -= job

proc/RmClockWorldTick(t)
	var/i = (round(t / world.tick_lag) % RM_CLOCK_SLOTS) + 1
	var/list/L = rm_clock_world[i]
	if(!L) return
	rm_clock_world[i] = null
	for(var/job in L)
		var/due = rm_clock_world_due[job]
		if(due != t)
			if(isnum(due) && due > t)   // a ring's turn away: back in its slot
				var/list/A = rm_clock_world[i]
				if(!A)
					A = list()
					rm_clock_world[i] = A
				A += job
			continue
		rm_clock_world_due -= job   // run once: its body books the next
		RmClockWorldRun(job, rm_clock_world_usr[job])

// The world's timers, all of them (Shed.dm keeps its own loop: it measures at the start of a tick).
proc/RmClockWorldRun(job, who)
	set waitfor = 0
	usr = who
	switch(job)
		if("WalkParkSweep") RmWalkParkSweep()   // WalkLoop.dm: parked units given somewhere to go, every 4 ticks while any are parked
		if("Doors") RmDoorLoop()                // Doors.dm: own doors opened for passing units shut again, every 5 ticks while any are open
		if("FarRecords") RmFarLoop()            // FarRecords.dm: offline players' far units as records, every 20 ticks"""),
("""		for(var/t = last + world.tick_lag, t <= world.time, t += world.tick_lag) RmClockRunTick(t)   // a tick behind is still run, in order""",
"""		for(var/t = last + world.tick_lag, t <= world.time, t += world.tick_lag)   // a tick behind is still run, in order
			RmClockRunTick(t)
			RmClockWorldTick(t)   // then the world's timers due on it"""),
],
'Code/Remastered/WalkLoop.dm': [
("""			if(!rm_walk_sweeping)
				rm_walk_sweeping = 1
				spawn(RM_WALK_SWEEP) RmWalkParkSweep()
			return""",
"""			if(!rm_walk_sweeping)
				rm_walk_sweeping = 1
				RmClockWorldBook("WalkParkSweep", RM_WALK_SWEEP)   // on the unit clock (UnitClock.dm)
			return"""),
("""// unhooked ones set off within RM_WALK_SWEEP ticks, as an idle look a step later did; the hooked ones at once.
proc/RmWalkParkSweep()
	while(length(rm_walk_park_list))
		var/list/keep = list()
		for(var/mob/Monsters/M in rm_walk_park_list) if(M.rm_walk_parked)
			if(M.destination || M.CanBeSlaved || !istype(M.Owner, /Player)) M.RmWalkUnpark()
			else keep += M
		rm_walk_park_list = keep
		sleep(RM_WALK_SWEEP)
	rm_walk_sweeping = 0""",
"""// unhooked ones set off within RM_WALK_SWEEP ticks, as an idle look a step later did; the hooked ones at once. A job on
// the unit clock (UnitClock.dm) while anything is parked: it ends on the run that finds nobody parked, as its loop did.
proc/RmWalkParkSweep()
	if(!length(rm_walk_park_list))
		rm_walk_sweeping = 0
		return
	var/list/keep = list()
	for(var/mob/Monsters/M in rm_walk_park_list) if(M.rm_walk_parked)
		if(M.destination || M.CanBeSlaved || !istype(M.Owner, /Player)) M.RmWalkUnpark()
		else keep += M
	rm_walk_park_list = keep
	RmClockWorldBook("WalkParkSweep", RM_WALK_SWEEP)"""),
],
'Code/Remastered/Doors.dm': [
("""var/rm_door_loop_on = 0             // RmDoorLoop running: only while one of those is open, so no loop sleeps for nothing""",
"""var/rm_door_loop_on = 0             // RmDoorLoop booked (a job on the unit clock, UnitClock.dm): only while one of those is open"""),
("""	if(!rm_door_loop_on)
		rm_door_loop_on = 1
		spawn(0) RmDoorLoop()""",
"""	if(!rm_door_loop_on)
		rm_door_loop_on = 1
		RmClockWorldBook("Doors", 5)"""),
("""proc/RmDoorLoop()
	while(length(rm_doors_auto))
		sleep(5)
		for(var/obj/Items/Furniture/Doors/D in rm_doors_auto.Copy())
			if(!D || !isturf(D.loc) || !D.Placed || D.density)   // gone, picked up, or shut by the player
				rm_doors_auto -= D
				continue
			if(locate(/mob/Monsters) in D.loc)
				D.rm_door_seen = world.time
				continue
			if(world.time - D.rm_door_seen < RM_DOOR_SHUT_AFTER) continue
			RmDoorShut(D)
			rm_doors_auto -= D
	rm_door_loop_on = 0""",
"""proc/RmDoorLoop()   // every 5 ticks on the unit clock while one is open: it ends on the run that shuts the last, as its loop did
	for(var/obj/Items/Furniture/Doors/D in rm_doors_auto.Copy())
		if(!D || !isturf(D.loc) || !D.Placed || D.density)   // gone, picked up, or shut by the player
			rm_doors_auto -= D
			continue
		if(locate(/mob/Monsters) in D.loc)
			D.rm_door_seen = world.time
			continue
		if(world.time - D.rm_door_seen < RM_DOOR_SHUT_AFTER) continue
		RmDoorShut(D)
		rm_doors_auto -= D
	if(length(rm_doors_auto)) RmClockWorldBook("Doors", 5)
	else rm_door_loop_on = 0"""),
],
'Code/Remastered/FarRecords.dm': [
("""world/New()
	spawn(150) RmFarLoop()
	return ..()""",
"""world/New()
	spawn(150) RmClockWorldBook("FarRecords", RM_FAR_EVERY)   // RmFarLoop, a job on the unit clock (UnitClock.dm)
	return ..()"""),
("""proc/RmFarLoop()
	var/n = 0
	while(1)
		sleep(RM_FAR_EVERY)
		if(!rm_far_auto || !remaster_world_ready) continue
		if(!rm_far_on)
			for(var/Player/P in rm_far_owners.Copy()) RmFarWakeOwner(P)
			continue
		n++
		RmFarWakeCheck(n % 3 == 0)
		RmFarSettleDue()
		if(n % RM_FAR_SWEEPS == 0) RmFarSleepSweep()""",
"""var/rm_far_loop_n = 0
proc/RmFarLoop()   // every RM_FAR_EVERY ticks after each run ends (a run may pause, RmFarPause), on the unit clock
	if(rm_far_auto && remaster_world_ready)
		if(!rm_far_on)
			for(var/Player/P in rm_far_owners.Copy()) RmFarWakeOwner(P)
		else
			rm_far_loop_n++
			RmFarWakeCheck(rm_far_loop_n % 3 == 0)
			RmFarSettleDue()
			if(rm_far_loop_n % RM_FAR_SWEEPS == 0) RmFarSleepSweep()
	RmClockWorldBook("FarRecords", RM_FAR_EVERY)"""),
],
}
# far-records' behind signal (their step 5 copy, 2026-10-25 14:15): the same loop with the shed skip, if it landed first
FAR_BEHIND = ("""proc/RmFarLoop()
	var/n = 0
	while(1)
		sleep(RM_FAR_EVERY)
		if(!rm_far_auto || !remaster_world_ready) continue
		if(!rm_far_on)
			for(var/Player/P in rm_far_owners.Copy()) RmFarWakeOwner(P)
			continue
		n++
		rm_far_piece_tick = world.time
		rm_far_piece_at = world.tick_usage
		RmFarWakeCheck(n % 3 == 0)            // wakes always: they must be done before anyone sees the land
		if(rm_shed_level >= 1) continue       // behind (Shed.dm): no self-settle and no new sleeping until it catches up
		RmFarSettleDue()
		if(n % RM_FAR_SWEEPS == 0) RmFarSleepSweep()""",
"""var/rm_far_loop_n = 0
proc/RmFarLoop()   // every RM_FAR_EVERY ticks after each run ends (a run may pause, RmFarPause), on the unit clock
	if(rm_far_auto && remaster_world_ready)
		if(!rm_far_on)
			for(var/Player/P in rm_far_owners.Copy()) RmFarWakeOwner(P)
		else
			rm_far_loop_n++
			rm_far_piece_tick = world.time
			rm_far_piece_at = world.tick_usage
			RmFarWakeCheck(rm_far_loop_n % 3 == 0)            // wakes always: they must be done before anyone sees the land
			if(rm_shed_level < 1)   // behind (Shed.dm): no self-settle and no new sleeping until it catches up
				RmFarSettleDue()
				if(rm_far_loop_n % RM_FAR_SWEEPS == 0) RmFarSleepSweep()
	RmClockWorldBook("FarRecords", RM_FAR_EVERY)""")
ALTS = {'Code/Remastered/FarRecords.dm': [FAR_BEHIND]}


def main(game):
    for rel, edits in EDITS.items():
        p = Path(game)/rel
        t = p.read_bytes().decode('latin-1')
        done = 0
        for old, new in edits:
            if new in t: continue
            alt = [(o, n) for o, n in ALTS.get(rel, []) if o in t or n in t]
            if t.count(old) != 1 and alt and old.split('\n')[0] == alt[0][0].split('\n')[0]:
                old, new = alt[0]
                if new in t: continue
            if t.count(old) != 1: sys.exit(f'{p}: no unique match for:\n{old[:160]}')
            t = t.replace(old, new); done += 1
        if done:
            fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.ring-'); os.write(fd, t.encode('latin-1')); os.close(fd)
            os.chmod(tmp, p.stat().st_mode); os.replace(tmp, p)
        print(f'{rel}: {done} edit(s)' if done else f'{rel}: already applied')


if __name__ == '__main__':
    main(sys.argv[1])
