// One clock for the units' timed jobs (server cost, planning/UNIT_MEMORY_PLAN.md step 1, 2026-10-24). Each unit kept its
// own forever loop for hunger, tiredness, bleeding, healing, its bed and (some races) regeneration: a proc asleep for
// each, holding its whole state, so every unit carried six sleeping procs and woke six times over, Bed every 5 ticks.
// Now each loop's body is a ...Tick() proc, unchanged, and the clock runs a unit's tick on the very ticks its loop would
// have woken: the first a period after the loop started, then a period after each run (Bed's period chosen after each
// run, as its loop chose its next sleep). A deleted unit drops out (the loop over a slot skips it); a job whose loop
// ended (bled to death) stops (RmClockStop). The bodies run with waitfor 0, so one that waits never holds the clock.
#define RM_CLOCK_SLOTS 1024     // the ring's ticks: a due time further off waits in its slot for the ring to come round

var/list/rm_clock_rings = list()   // job -> its ring: slot -> list of the units due on a tick of that slot
var/rm_clock_running = 0
mob/var/tmp/list/rm_clock_due        // job -> the tick it is next due on (no entry: not booked)
mob/var/tmp/rm_clock_usr             // the usr its loops started with (StartAllProcs starts them together), kept by a loop

// A job's loop starting: its first run a period from now, as the loop's first sleep.
proc/RmClockStart(mob/M, job, ticks)
	M.rm_clock_usr = usr   // the bodies' view() and usr are the loop's, as when each slept in its own proc
	RmClockBook(M, job, ticks)
	if(!rm_clock_running)
		rm_clock_running = 1
		spawn(0) RmClockLoop()

// Its next run, ticks from now (sleep(ticks): a tick is world.tick_lag, the clock counts world.time).
proc/RmClockBook(mob/M, job, ticks)
	if(!M.rm_clock_due) M.rm_clock_due = list()
	var/due = world.time + max(1, round(ticks)) * world.tick_lag
	M.rm_clock_due[job] = due
	RmClockSlot(M, job, due)

proc/RmClockSlot(mob/M, job, due)
	var/list/ring = rm_clock_rings[job]
	if(!ring)
		ring = new/list(RM_CLOCK_SLOTS)
		rm_clock_rings[job] = ring
	var/i = (round(due / world.tick_lag) % RM_CLOCK_SLOTS) + 1
	var/list/L = ring[i]
	if(!L)
		L = list()
		ring[i] = L
	L += M

// The job's loop ended (its body returned for good).
proc/RmClockStop(mob/M, job)
	if(M.rm_clock_due) M.rm_clock_due -= job

proc/RmClockLoop()
	var/last = world.time
	while(1)
		sleep(1)
		sleep(0)   // then after the procs woken this tick (no fixed order among them): the players' track and care first
		for(var/t = last + world.tick_lag, t <= world.time, t += world.tick_lag)   // a tick behind is still run, in order
			RmClockRunTick(t)
			RmClockWorldTick(t)   // then the world's timers due on it
		last = world.time

proc/RmClockRunTick(t)
	var/i = (round(t / world.tick_lag) % RM_CLOCK_SLOTS) + 1
	for(var/job in rm_clock_rings)
		var/list/ring = rm_clock_rings[job]
		var/list/L = ring[i]
		if(!L) continue
		ring[i] = null
		for(var/mob/M in L)       // a deleted unit is skipped here, and so dropped
			var/list/D = M.rm_clock_due
			var/due = D ? D[job] : null
			if(due != t)
				if(isnum(due) && due > t) RmClockSlot(M, job, due)   // a ring's turn away: back in its slot
				continue                                              // stopped, or booked again since
			if(job == "Bed" && M.Tiredness > 20)   // its run would only book the next one (Mob Procs.dm BedTick): booked here, no call
				RmClockBook(M, "Bed", M.CanBeSlaved ? 1000 : 5)
				continue
			M.RmClockRun(job)

mob/proc/RmClockRun(job)
	set waitfor = 0
	usr = rm_clock_usr
	switch(job)
		if("Hunger") src:HungerTick()
		if("Tiredness") src:TirednessTick()
		if("Bleeding") BleedingTick()
		if("Heal") HealTick()
		if("Bed") BedTick()
		if("Regen") RegenTick()
		if("Morale") src:RmMoraleTick()   // in combat only (Morale.dm)
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
		if("DoorCount") RmDoorCountLoop()       // Doors.dm: every door's tile count put right, every 10 ticks while there are doors
		if("FarRecords") RmFarLoop()            // FarRecords.dm: offline players' far units as records, every 20 ticks
		if("FarSteps") RmFsTick()               // FarSteps.dm: the cameras looked at every 2 ticks while far units take coarse steps
		if("Ground") RmGroundLoop()             // Turfs.dm: the ground's effects for the units that walked, every tick while any wait
		if("OfflineGuards") RmOffGuardLoop()    // OfflineGuards.dm: an away owner's defences, attacks and patrols, every 5 ticks while any are listed
