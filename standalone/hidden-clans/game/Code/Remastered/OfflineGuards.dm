// Guards that hold while their owner is away (quest maker plan phase Q4, planning/QUEST_MAKER_PLAN_2026-10-31.md; the
// owner, 10-31, question 5: every player's guards keep guarding while their owner is offline; fights stay real and only
// happen near players). Before this a guard's own loop (Creatures/Monster AI.dm GuardRun) went on after log-off, but what
// it leans on ran only in a connected player's track (QoL.dm RemasterTrack): a defence started by a blow (Defense.dm
// RemasterThreatenedBy) was never ticked, so the guard stood in it for good (GuardRun skips while one is on); patrols
// stopped; and a post (HomeLoc, tmp) was gone after a restart.
//  - The post: where a unit was set to guard (the guard or aggressive stance, HUD.dm; the old Guard On), saved with the
//    unit (rm_post, rm_post_kind). It goes when its guard ends (hold, an order, a capture: GuardRun's loop ends with no
//    HomeLoc). A unit loaded from a save takes its post again (LoadUnits), and the log-off guard of a posted unit is its
//    post's own guard (Login.dm Logout's Guarding(AUTO=1)), not the one that stops at once with no client.
//  - The world loop (RmOffGuardLoop, a job on the unit clock every 5 ticks, as the track's): an away owner's units with a
//    defence, an attack or a patrol, listed at log-off and when a defence starts while their owner is away. In awake land
//    (Awake.dm: another player's camera, units or workshops near) each gets the ticks the track would give it (patrol,
//    defence, attack, orders, crawl, stepping off a friend's tile). In asleep land a defence ends at once and the rest
//    waits for the land to wake: no fights where nobody watches. Units only on post aren't listed: their own loop guards
//    them, and in asleep land it starts no fight (RmPostMayLook, GuardRun's look for a target).
//  - Cost: only listed units, and only those in awake land do any work; the tick profiler's "offline guards" (TickProfile.dm
//    RmProfIn/RmProf, round each pass).
// Not here: an away owner's units after a restart (they come back with their owner's log-in, Saves.dm LoadUnits; far
// records, phase Q9), and the Garrison order (posts taken by themselves, phase Q5).

#define RM_OFFGUARD_EVERY 5                  // ticks between passes, as the track's (QoL.dm REMASTER_TRACK_DELAY)
mob/Monsters/var/rm_post                     // "x,y,z" of its guard post, saved with the unit; null: not posted
mob/Monsters/var/rm_post_kind                // "guard" or "aggressive"
mob/Monsters/var/tmp/rm_post_taking = 0      // RmPostTake is starting its guard: Guarding leaves the post as it is
mob/Monsters/var/tmp/rm_offguard_on = 0      // it has its one entry in rm_offguard
var/list/rm_offguard = list()                // an away owner's units the world loop ticks
var/rm_offguard_booked = 0                   // RmOffGuardLoop booked on the unit clock

// Is M's owner a player who is away?
proc/RmOwnerAway(mob/Monsters/M)
	var/Player/P = M.Owner
	return istype(P) && !P.client

// May a guard look for a foe (GuardRun)? Not an away owner's in asleep land.
proc/RmPostMayLook(mob/Monsters/M)
	var/Player/P = M.Owner
	return !istype(P) || P.client || RmAwake(M)

proc/RmPostTurf(mob/Monsters/M)
	if(!M.rm_post) return null
	var/list/c = splittext(M.rm_post, ",")
	if(length(c) != 3) return null
	return locate(text2num(c[1]), text2num(c[2]), text2num(c[3]))

// A player's unit set to guard where it stands has that as its post. The log-off guard (AUTO) of a posted unit is its
// post's own guard, which goes on while its owner is away.
mob/Monsters/Guarding(RANGE=5,RATE=10,AUTO=0)
	if(AUTO && rm_post && istype(Owner, /Player))
		RmPostTake()
		return
	var/fresh = !HomeLoc || !("Guard" in RunningProcs)   // as Guarding decides where home is: here, or as it was
	. = ..()
	var/turf/H = HomeLoc
	if(!AUTO && fresh && !rm_post_taking && !Critter && istype(Owner, /Player) && isturf(H))
		rm_post = "[H.x],[H.y],[H.z]"
		rm_post_kind = ("Agressive" in GuardRules) ? "aggressive" : "guard"

// Its guard over (no HomeLoc: hold, an order, a capture, Guard Off): no post either.
mob/Monsters/GuardRun(key, wait)
	. = ..()
	if(!HomeLoc && rm_post) rm_post = null

// Its guard going again at its post, with the aggressive rule when it was an aggressive one.
mob/Monsters/proc/RmPostTake()
	var/turf/T = RmPostTurf(src)
	if(!T || Critter || Wagon)
		rm_post = null
		return 0
	if(GuardRules) GuardRules -= "Agressive"   // made on first use (Monster AI.dm)
	if(rm_post_kind == "aggressive")
		if(!GuardRules) GuardRules = list()
		GuardRules += "Agressive"
	if(!HomeLoc || !("Guard" in RunningProcs))
		rm_post_taking = 1
		Guarding()
		rm_post_taking = 0
		remaster_order_status = rm_post_kind == "aggressive" ? "Aggressive guard" : "Guarding"
	if(!PatrolPoint1) HomeLoc = T   // the old two-point patrol moves HomeLoc between its points itself
	return 1

// Posts again after a load (the save keeps rm_post; LoadUnits clears HomeLoc and no loop came with the units).
mob/LoadUnits()
	. = ..()
	if(.) for(var/mob/Monsters/M in UnitList) if(M.rm_post && M.Owner == src) M.RmPostTake()

// Away: the units with something on that only the track ticked are the world loop's now (posted ones guard by
// themselves; Logout's Guarding(AUTO=1) above kept them on post).
Player/Logout()
	. = ..()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && (M.remaster_defense || M.remaster_attack || M.remaster_patrol)) RmOffGuardAdd(M)

// A defence started while its owner is away: ticked and ended by the world loop.
mob/Monsters/RemasterBeginDefense(mob/Monsters/enemy, mob/Monsters/source)
	. = ..()
	if(. && RmOwnerAway(src)) RmOffGuardAdd(src)

proc/RmOffGuardAdd(mob/Monsters/M)
	if(M.rm_offguard_on) return
	M.rm_offguard_on = 1
	rm_offguard += M
	if(!rm_offguard_booked)
		rm_offguard_booked = 1
		RmClockWorldBook("OfflineGuards", RM_OFFGUARD_EVERY)   // on the unit clock (UnitClock.dm)

// Every RM_OFFGUARD_EVERY ticks while any are listed: it ends on the run that finds none left, as the doors' loop does.
proc/RmOffGuardLoop()
	if(!length(rm_offguard))
		rm_offguard_booked = 0
		return
	RmClockWorldBook("OfflineGuards", RM_OFFGUARD_EVERY)   // the next one first: one that fails can't stop the loop for good
	if(!rm_prof) return RmOffGuardPass()
	var/t0 = RmProfIn()   // the tick profiler (TickProfile.dm)
	var/w0 = world.time
	RmOffGuardPass()
	RmProf("offline guards", t0, w0)

// In place and in order (as WalkLoop.dm's park sweep): the still listed are written back over the list, the rest cut
// off. One whose owner is back (the track has it again), gone, or with nothing on any more drops out. A unit listed
// during the pass (a defence started by a blow in it) is appended and gets its tick in the same pass.
proc/RmOffGuardPass()
	var/list/L = rm_offguard
	var/j = 0
	for(var/i = 1, i <= length(L), i++)
		var/mob/Monsters/M = L[i]
		if(!istype(M) || Rm3DGone(M)) continue   // deleted refs aren't null here (View3D.dm)
		var/Player/P = M.Owner
		if(!istype(P) || P.client || M.HP <= 0 || !(M.remaster_defense || M.remaster_attack || M.remaster_patrol))
			M.rm_offguard_on = 0
			continue
		j++
		L[j] = M
		if(!RmAwake(M))   // asleep land: no fight goes on where nobody watches; a patrol or an attack waits for it to wake
			if(M.remaster_defense) M.RemasterCancelDefense(1)
			continue
		M.RmOffGuardTick(P)
	if(j < length(L)) L.Cut(j + 1)

// What the track gives a unit with something on (QoL.dm RemasterTrack: Patrol.dm's patrol tick, then Orders.dm's).
mob/Monsters/proc/RmOffGuardTick(Player/P)
	if(remaster_patrol) RemasterPatrolNext(P)
	if(Rm3DGone(src)) return
	RemasterDefenseTick()
	if(!Rm3DGone(src) && !RemasterAttackTick() && !Rm3DGone(src)) RemasterOrderTick()
	if(!Rm3DGone(src)) RemasterCrawlTick()
	if(!Rm3DGone(src)) RmStepOffShared()   // never left standing on one of its side (Clip.dm)
