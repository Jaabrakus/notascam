// mob/Monsters/RemasterStepDelay: one chain, in the order DM ran it when it was spread over 5 files (cleanup, from
// chains.py). The call runs BodyDrag > TickProfile > Formations > Captives > Specials: each step below calls the next one down where it used to call ..().
// Add a feature's part as a new step at its place in this order, never as another override elsewhere.
mob/Monsters/proc/RemasterStepDelay()
	return RmChainStepDelay_BodyDrag(arglist(args))

// step 1 of 5: BodyDrag (was Code/Remastered/BodyDrag.dm:146)
mob/Monsters/proc/RmChainStepDelay_BodyDrag()
	. = RmChainStepDelay_TickProfile(arglist(args))
	if(rm_dragging && RmDragged() && !RemasterMarchGroup() && !RemasterChained() && remaster_mate_wait != world.time) . = RmDragPace(.)

// step 2 of 5: TickProfile (was Code/Remastered/TickProfile.dm:472)
mob/Monsters/proc/RmChainStepDelay_TickProfile()
	if(!rm_prof) return RmChainStepDelay_Formations(arglist(args))
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = RmChainStepDelay_Formations(arglist(args))
	RmProf("creature walk loop", t0, w0)   // its calls are the WalkTo loops going round

// step 3 of 5: Formations (was Code/Remastered/Formations.dm:128)
mob/Monsters/proc/RmChainStepDelay_Formations()
	. = RmChainStepDelay_Captives(arglist(args))
	if(remaster_root_until > world.time) return
	var/datum/remaster_group/G = RemasterMarchGroup()
	var/waited = remaster_mate_wait == world.time
	if(!G && !waited && !RemasterChained()) return
	var/s = RemasterOwnStep()
	if(G) s = max(s, G.Pace())
	// Nowhere to go yet, or it just walked into a group-mate: look again next tick, never sooner than a step's
	// time after its last step (so the group's pace holds, and a queue moves up the tick the one ahead steps).
	if(!destination || waited) return max(1, min(s, remaster_stepped_at + s - world.time))
	return s

// step 4 of 5: Captives (was Code/Remastered/Captives.dm:623)
// The hobble: a slave walks a quarter slower (at least a tick a step), on its own and as a group's pace (Formations.dm).
mob/Monsters/proc/RmChainStepDelay_Captives()
	. = RmChainStepDelay_Specials(arglist(args))
	if(rm_cap_state == "slave" && destination) . = max(. + 1, round(. * 1.25))

// step 5 of 5: Specials (was Code/Remastered/Specials.dm:46)
// Time between steps (WalkTo): a flying dragon is twice as fast; slowed units take
// twice as long; a rooted unit waits until the root wears off.
mob/Monsters/proc/RmChainStepDelay_Specials()
	var/d = Delay
	if(Flying && Race == "Dragon") d = max(1, round(d / 2))
	if(remaster_active || remaster_delivery) d = RmJobRouteStep(d)   // a job's walk along its route: an ordered move's pace (Formations.dm)
	d = RemasterRoadDelay(d)    // faster along roads (Roads.dm)
	if(rm_swim_on && RmSwimWater(loc)) d = RmSwimDelay(d)   // in deep water: its race's pace (Swim.dm)
	if(remaster_slow_until > world.time) d *= 2
	if(remaster_root_until > world.time) d = max(d, remaster_root_until - world.time)
	// Yours with nowhere to go look again a step later, as in the original: an order's first step still comes at once
	// because whatever gives a unit somewhere to go brings that look to now (WalkLoop.dm RmWalkSoon; it was a look
	// every tick, rts-feel's, 25,000 wakes a second at 5,000 units standing).
	return d
