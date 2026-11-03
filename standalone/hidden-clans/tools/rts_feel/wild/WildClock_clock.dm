// The wild creatures' own loops on the shared clock (rts-feel, 2026-10-24; the coordinator's 30k list: "wild creature AI
// loops onto the shared clock + coarse far tier"). Each wild creature kept forever loops in Creatures/Monster AI.dm, a
// proc asleep for each: RandomWalk's wander (every Delay+1) and its 300-tick clear, a guard's walk (Delay+1) and gear
// look (200), Guarding's look round (RATE) and its way home (250, then 50), StayLocal's call home (ReturnDelay). Now
// each loop's body is a ...Tick(key) proc, unchanged, and the clock (Remastered/UnitClock.dm) runs it on the very ticks
// its loop would have woken: its first run as the loop's first sleep (or at once where the loop's body came first),
// then a period after each run. A loop's two parts (a wander's rest, a guard's 50 ticks heading home) are two runs, so
// the ticks match the old loops' exactly. A deleted creature drops out (the clock skips it); a loop whose condition
// fails ends as the loop did, with what came after it (WalkTo(1) once no longer wild; Guard leaving RunningProcs).
// Each loop keeps the usr it started with (a player's "Guard On" doesn't change the one its Hunger runs with), and a
// second loop of the same kind (one still asleep in the old game when a new one began) gets its own key ("Guard~2").
//
// The far tier: a creature nobody owns, in asleep land (Awake.dm: no player's camera, unit or workshop near, the same
// line far-records turns offline players' units into records at), with nothing to do, looks round every
// rm_wild_far_think ticks rather than every step: a guard's look for a target (RATE, 1 s) and its walk with nowhere
// to go (Delay+1). A wanderer already rests there (Awake.dm, rm_asleep_nap). Walking somewhere (a raider marching in,
// a chase, the way home) is never slowed, so nothing arrives later. Awake land reaches 32 tiles past each of a
// player's units and 24 past the camera's view, more than a unit walks in rm_wild_far_think, so every creature in
// sight runs fully.

var/rm_wild_far_think = 30     // ticks between looks for an idle wild creature in asleep land (3 s)
var/list/rm_wild_base = list("Wander" = "Wander", "WanderClear" = "WanderClear", "GuardWalk" = "GuardWalk", "GuardGear" = "GuardGear",
	"Guard" = "Guard", "GuardHome" = "GuardHome", "StayLocal" = "StayLocal")   // clock job key -> its loop
mob/var/tmp/list/rm_wild_usr          // job key -> the usr its loop started with; a key here is a loop running
mob/var/tmp/list/rm_wild_phase        // job key -> the part of a two-part loop it is in (a guard's "home")
mob/Monsters/var/tmp/rm_wander_rest = 0   // its wander is resting (one wander loop at a time: RandomWalk starts it only once the owned walk loop has ended)
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

// A loop starting with a sleep: its first run that many ticks from now.
proc/RmWildStart(mob/M, job, ticks)
	var/key = RmWildKey(M, job)
	RmWildBook(M, key, ticks)
	return key

// Its next run, ticks from now (as the loop's sleep(ticks)); a run from the clock books with RmClockBook itself.
proc/RmWildBook(mob/M, key, ticks)
	if(rm_clock_running) RmClockBook(M, key, ticks)
	else   // the clock's first job: RmClockStart starts its loop (and would take this usr for the unit's own jobs)
		var/u = M.rm_clock_usr
		RmClockStart(M, key, ticks)
		M.rm_clock_usr = u

// The loop going round: booked again while its condition holds, else it ends. 1 while it goes on.
proc/RmWildNext(mob/M, key, ticks, cond)
	if(cond)
		RmWildBook(M, key, ticks)
		return 1
	RmWildEnd(M, key)
	return 0

proc/RmWildEnd(mob/M, key)
	RmClockStop(M, key)
	if(M.rm_wild_usr) M.rm_wild_usr -= key
	if(M.rm_wild_phase) M.rm_wild_phase -= key

// Where a two-part loop is (RmWildSetPhase with null: back at its start).
proc/RmWildPhase(mob/M, key)
	return M.rm_wild_phase ? M.rm_wild_phase[key] : null

proc/RmWildSetPhase(mob/M, key, value)
	if(isnull(value))
		if(M.rm_wild_phase) M.rm_wild_phase -= key
		return
	if(!M.rm_wild_phase) M.rm_wild_phase = list()
	M.rm_wild_phase[key] = value

// Nobody's own, in asleep land, with nothing on: the far tier.
mob/Monsters/proc/RmWildFarIdle()
	if(istype(Owner, /Player) || remaster_defense || ReturningHome) return 0
	if(destination && destination != HomeLoc) return 0
	return !RmAwake(src)

// The clock's runs of these loops (the unit's own jobs go on to UnitClock.dm's). A run costs its proc calls (about
// 0.6 us each here, tests/wild_bench2.dm), more than a sleeping proc's wake, so the runs are kept short: one lookup,
// one call, and the loops' ends book straight with RmClockBook.
mob/RmClockRun(job)
	set waitfor = 0
	var/kind = rm_wild_base[job]
	if(!kind) return ..()
	usr = rm_wild_usr[job]
	var/mob/Monsters/M = src
	switch(kind)
		if("Wander") M.WanderTick(job)
		if("GuardWalk") M.GuardWalkTick(job)
		if("Guard") M.GuardTick(job)
		if("WanderClear") M.WanderClearTick(job)
		if("GuardGear") M.GuardGearTick(job)
		if("GuardHome") M.GuardHomeTick(job)
		if("StayLocal") M.StayLocalTick(job)
