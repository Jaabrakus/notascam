// The wild creatures' own loops off their procs while nobody is near (rts-feel, 2026-10-24; the coordinator's 30k list:
// "wild creature AI loops onto the shared clock + coarse far tier"). Each wild creature keeps forever loops in
// Creatures/Monster AI.dm: RandomWalk's wander (every Delay+1) and its 300-tick clear, a guard's walk (Delay+1) and gear
// look (200), Guarding's look round (RATE) and its way home (250, then 50), StayLocal's call home (ReturnDelay). Each
// used to sleep in its own proc wherever the creature was, so every wild creature in the world held up to four
// sleeping procs. Now each loop sleeps in its proc only while its land is awake (Awake.dm: a player's camera, units or
// workshops near); where it would sleep in asleep land it books the shared clock (Remastered/UnitClock.dm) for that very
// tick and leaves its proc, and the clock calls the loop again then (RmWildRun below), which carries on in a proc once
// its land is awake again. So the loops wake on the old ticks either way (tests/wildclock_check.dm), and the creatures
// far from everyone, most of them on a big map, hold no procs. Not all of it on the clock: a clock run costs its proc
// calls (about 0.6 us each here, tests/wild_bench2.dm), more than a sleeping proc's wake for loops that come round every
// step, so near players the loops stay as they were (tests/stress_wild_ab.dm).
// A loop's two parts (a wander's rest, a guard's 50 ticks heading home) are two runs. A deleted creature drops out (the
// clock skips it); a loop whose condition fails ends as it did, with what came after it (WalkTo(1) once no longer
// wild; Guard leaving RunningProcs). Each loop keeps the usr it started with, and a second loop of the same kind (one
// still asleep in the old game when a new one began) gets its own key ("Guard~2").
//
// The far tier: in asleep land a creature nobody owns with nothing to do looks round every rm_wild_far_think ticks
// rather than every step: a guard's look for a target (RATE, 1 s) and its walk with nowhere to go (Delay+1). A wanderer
// already rests there (Awake.dm, rm_asleep_nap). Walking somewhere (a raider marching in, a chase, the way home) is never
// slowed, so nothing arrives later. Awake land reaches 32 tiles past each of a player's units and 24 past the camera's
// view, more than a unit walks in rm_wild_far_think, so every creature anyone can see runs fully. The same line far-records
// turns offline players' units into records at (FarRecords.dm).

var/rm_wild_far_think = 30     // ticks between looks for an idle wild creature in asleep land (3 s)
// Is its land awake, at a loop's sleep: the answer kept for 10 ticks (Awake.dm redraws its map every 10), so a creature's
// loops don't each ask at every sleep (a proc call is ~0.6 us; up to four loops a creature, every step near players).
// (RM_WILD_AWAKE, in Creatures/Monster AI.dm where the loops use it: the macro has to come before them)
mob/Monsters/var/tmp/rm_wild_seen = -100
mob/Monsters/var/tmp/rm_wild_was = 1
mob/Monsters/proc/RmWildLook()
	rm_wild_seen = world.time
	rm_wild_was = RmAwake(src)
	return rm_wild_was
var/list/rm_wild_base = list("Wander" = "Wander", "WanderClear" = "WanderClear", "GuardWalk" = "GuardWalk", "GuardGear" = "GuardGear",
	"Guard" = "Guard", "GuardHome" = "GuardHome", "StayLocal" = "StayLocal")   // clock job key -> its loop
mob/var/tmp/list/rm_wild_usr          // job key -> the usr its loop started with; a key here is a loop running
mob/var/tmp/list/rm_wild_phase        // job key -> the part of a two-part loop it is in on the clock (a guard's "home", a second wander's "rest")
mob/Monsters/var/tmp/rm_wander_rest = 0   // its first wander loop is resting on the clock (a second one's rest: its phase; RmWanderRest)
mob/Monsters/var/tmp/rm_guard_range = 5   // Guarding's arguments, for its loop's runs
mob/Monsters/var/tmp/rm_guard_rate = 10
mob/Monsters/var/tmp/rm_guard_auto = 0

// A loop starting: its key on the clock, with the usr it runs with.
proc/RmWildKey(mob/M, job)
	var/key = job
	var/n = 1
	while(M.rm_wild_usr && (key in M.rm_wild_usr))
		n++
		key = "[job]~[n]"
	if(!rm_wild_base[key]) rm_wild_base[key] = job
	if(!M.rm_wild_usr) M.rm_wild_usr = list()
	M.rm_wild_usr[key] = usr
	return key

// The loop's sleep, on the clock: its next run ticks from now (its land is asleep, so it leaves its proc).
proc/RmWildBook(mob/M, key, ticks)
	if(rm_clock_running) RmClockBook(M, key, ticks)
	else   // the clock's first job: RmClockStart starts its loop (and would take this usr for the unit's own jobs)
		var/u = M.rm_clock_usr
		RmClockStart(M, key, ticks)
		M.rm_clock_usr = u

proc/RmWildEnd(mob/M, key)
	RmClockStop(M, key)
	if(M.rm_wild_usr) M.rm_wild_usr -= key
	if(M.rm_wild_phase) M.rm_wild_phase -= key

// Where a two-part loop is on the clock (RmWildSetPhase with null: back at its start).
proc/RmWildPhase(mob/M, key)
	return M.rm_wild_phase ? M.rm_wild_phase[key] : null

proc/RmWildSetPhase(mob/M, key, value)
	if(isnull(value))
		if(M.rm_wild_phase) M.rm_wild_phase -= key
		return
	if(!M.rm_wild_phase) M.rm_wild_phase = list()
	M.rm_wild_phase[key] = value

// Nobody's, with nothing on: in asleep land, the far tier's wait.
mob/Monsters/proc/RmWildIdle()
	if(istype(Owner, /Player) || remaster_defense || ReturningHome) return 0
	return !destination || destination == HomeLoc

// The clock's runs of these loops, each where its sleep ended: UnitClock.dm's RmClockRun hands every job that isn't the
// unit's own to this (inside RmClockRun, so waitfor 0 and the clock never waits: a loop that finds its land awake
// sleeps on in its own proc from here).
mob/proc/RmWildRun(job)
	var/kind = rm_wild_base[job]
	if(!kind) return
	usr = rm_wild_usr[job]
	var/mob/Monsters/M = src
	switch(kind)
		if("Wander") M.WanderRun(job, 0)
		if("GuardWalk") M.GuardWalkRun(job, 0)
		if("Guard") M.GuardRun(job, 0)
		if("WanderClear") M.WanderClearRun(job, 0)
		if("GuardGear") M.GuardGearRun(job, 0)
		if("GuardHome") M.GuardHomeRun(job, 0)
		if("StayLocal") M.StayLocalRun(job, 0)

// A wander loop's rest on the clock: the first wander loop's in rm_wander_rest, a second one's (RandomWalk(1) on a
// wanderer) in its phase, so each has its own, as each old loop did.
mob/Monsters/proc/RmWanderRest(key, on)
	if(key == "Wander") rm_wander_rest = on
	else RmWildSetPhase(src, key, on ? "rest" : null)
