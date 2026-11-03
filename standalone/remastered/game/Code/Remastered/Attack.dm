// RTS attack orders. Select units, then:
//  - click an enemy: they all go for it (melee walks in, bows shoot from range);
//  - Attack (A) then click the ground: attack-move - they march there and fight
//    any hostile they meet on the way, then carry on;
//  - Attack (A) then click an enemy: the same as clicking it.
// The original combat code does the fighting (WalkTo/Bump melee, BowTarget):
// this only chooses targets and walks the units in, like the defense system.

#define REMASTER_ATTACK_SIGHT 6

datum/remaster_attack
	var/Player/issuer
	var/mob/Monsters/target      // what to kill now (null while marching)
	var/turf/goal                // attack-move destination, or null
	var/list/path
	var/turf/path_goal
	var/next_shot = 0
	var/last_position
	var/last_progress
	var/mob/Monsters/chosen      // the enemy you clicked: chased until it's dead or gone
	var/stuck_since = 0
	var/mob/Monsters/finish      // ordered on one already down: it finishes that one (Falls.dm RmDownOut)

Player/var/tmp/remaster_attack_mode = 0
mob/Monsters/var/tmp/datum/remaster_attack/remaster_attack

// A hostile this unit may fight. Explicit targets may be anything not ours;
// attack-move leaves animals and chests alone.
// pairs: a list the caller keeps for one look round, in which no war or alliance changes: each realm's answer (allied, at
// war) is worked out once and kept there (combat-speed, 10-26: a morale tick in a crowd asked it of ~40 units).
proc/RemasterHostile(mob/Monsters/me, mob/Monsters/E, explicit = 0, list/pairs = null)
	if(!istype(E) || !me || E == me) return 0
	if(RemasterIsSiege(E))      // a siege engine: fair game for a realm at war (Siege.dm)
		return isturf(E.loc) && E.z == me.z && istype(E.Owner, /Player) && istype(me.Owner, /Player) && E.Owner != me.Owner && RemasterAtWar(me.Owner, E.Owner) && (explicit || !E:RemasterSiegeCrew())
	if(E.HP <= 0 || E.GoingToDie || E.CantKill || E.WS || E.Wagon) return 0
	if(E.Owner == me.Owner && E.Owner) return 0
	if(pairs && istype(E.Owner, /Player) && istype(me.Owner, /Player))
		var/list/K = pairs[E.Owner]
		if(!K)
			K = list(RemasterAllied(E.Owner, me.Owner), RemasterAtWar(me.Owner, E.Owner))
			pairs[E.Owner] = K
		if(K[1]) return 0
		if(!K[2] && !RemasterWarAllows(me, E)) return 0   // at war it allows; at peace, as it reckons (War.dm)
	else
		if(istype(E.Owner, /Player) && istype(me.Owner, /Player) && RemasterAllied(E.Owner, me.Owner)) return 0
		if(!RemasterWarAllows(me, E)) return 0          // another realm at peace (War.dm)
	if(!isturf(E.loc) || E.z != me.z) return 0
	if(istype(E, /mob/Monsters/Chests)) return 0
	if(E.remaster_caravan && !explicit) return 0
	if(!explicit && E.Critter && !E.Owner) return 0
	return 1

// The attack tick's pairs (squad-split, the owner 10-29: "Build them anyway"): each realm's answer to another (allied, at war)
// once a tick for all its fighters, not once a fighter. Kept while rm_realm_ver stands (War.dm: it moves whenever a war's
// state or a liege changes), so a war declared mid-tick counts at once. null for a unit of no realm (as without pairs).
var/list/rm_atk_pairs
var/rm_atk_pairs_at = -1
var/rm_atk_pairs_ver = -1
proc/RmAtkPairs(owner)
	if(!istype(owner, /Player)) return null
	if(rm_atk_pairs_at != world.time || rm_atk_pairs_ver != rm_realm_ver || !rm_atk_pairs)
		rm_atk_pairs = list()
		rm_atk_pairs_at = world.time
		rm_atk_pairs_ver = rm_realm_ver
	var/list/L = rm_atk_pairs[owner]
	if(!L)
		L = list()
		rm_atk_pairs[owner] = L
	return L

Player/proc/RemasterAttackOrder(atom/A)
	if(remaster_attack_mode && istype(A, /mob/Monsters) && A:Owner != src && !RmDownOut(A))   // one already down: just that one
		var/alike = RemasterAttackAlike(A)   // Attack (A), then a click on a foe: all of its kind near it (Formations.dm)
		if(!isnull(alike)) return alike
	var/mob/Monsters/E = istype(A, /mob/Monsters) ? A : null
	var/turf/T = E ? null : RemasterTurf(A)
	if(!E && !T) return 0
	var/n = RemasterSiegeOrder(A, 1)        // siege engines in the selection (Siege.dm)
	var/list/slots = E ? null : RemasterGroupForm(T, 0, "Attack-move")   // attack-move keeps the formation (Formations.dm)
	var/datum/rm_reach/RM          // an attack-move's ground: round its units and the march's goal (Formations.dm RmReachFor)
	if(!E)
		var/list/U = list()
		for(var/mob/Monsters/M in Selected) if(M.Owner == src && isturf(M.loc)) U += M
		RM = RmReachFor(U, list(T))
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || M.HP <= 0 || RemasterIsSiege(M)) continue
		if(E && !RemasterHostile(M, E, 1)) continue
		M.RemasterCancelOrders()
		if(M.remaster_defense) M.RemasterCancelDefense(0)
		M.RemasterCareInterrupt()
		M.RemasterWake()
		M.remaster_patrol = null
		var/datum/remaster_attack/K = new
		K.issuer = src
		K.target = E
		K.chosen = E
		if(RmDownOut(E)) K.finish = E
		K.goal = (slots && slots[M]) || T
		K.reach = RM
		if(slots && slots[M]) K.group = remaster_forming
		K.last_position = M.loc
		K.last_progress = world.time
		// the same foe, or the same attack-move spot while marching, again (a re-click): its route kept (owner call D, 10-27)
		var/datum/remaster_attack/K0 = M.remaster_attack
		if(K0 && K0.issuer == src && length(K0.path) && get_dist(M, K0.path[1]) <= 1 && (E ? (K0.chosen == E && K0.target == E) : (!K0.target && !K0.chosen && K0.goal == K.goal)))
			K.path = K0.path
			K.path_goal = K0.path_goal
		M.remaster_attack = K
		M.remaster_push_step = 1
		M.remaster_order_status = E ? "Attacking [RemasterCombatName(E)]" : "Attack-move"
		if(!E) RmFirstTick(M, K, n + 1)    // an attack-move's first step this tick, as a move's (a big group's over a few ticks; Formations.dm)
		n++
	if(slots) RemasterGroupFinish(remaster_forming)
	remaster_attack_mode = 0
	if(n)
		if(remaster_3d) Remaster3DMovesPushSoon()   // the first step on screen a tick after the order (View3D.dm)
		RemasterNotice(E ? "Attack! [n] going for [RemasterCombatName(E)]." : "Attack-move: [n] march and fight anything hostile on the way.")
		RemasterLog(E ? "Attack ordered on [RemasterCombatName(E)]" : "Attack-move ordered", "fight", E || T)
	else if(E && istype(E.Owner, /Player) && !RemasterAllied(src, E.Owner)) RemasterNotice("You are at peace with [E.Owner:RemasterRealmName()]. Declare war in the Realm tab first.")
	else if(E) RemasterNotice("Your selected units can't attack [RemasterCombatName(E)].")
	return n

mob/Monsters/proc/RemasterAttackStop()
	remaster_attack = null
	destination = null
	Target = null
	BowOn = 0
	remaster_order_status = "Idle"

// Walk one step along a path to goal (like RemasterDefenseApproach, no leash).
// keep: what you ordered (the enemy you clicked, the attack-move spot) is never dropped
// for being hard to reach; the unit keeps looking for a way. Otherwise a target it
// can't get to for a few seconds is let go.
mob/Monsters/proc/RemasterAttackApproach(turf/goal, reach, keep = 0)
	var/datum/remaster_attack/K = remaster_attack
	if(!K || !goal || goal.z != z) return 0
	if(K.last_position != loc)
		K.last_position = loc
		K.last_progress = world.time
	if(world.time - K.last_progress > max(60, Delay * 8))
		if(!keep) return 0
		K.path = null
		K.last_progress = world.time
	while(length(K.path) && K.path[1] == loc) K.path.Cut(1, 2)
	// marching with a group: through its walking members, waiting behind one in the way (Formations.dm)
	var/datum/remaster_group/G = !K.target ? K.group : null
	var/held = 0   // B and C (below): 1 its route made without a search; 2 no search now: it keeps its old route, waiting while that route's next step is shut
	if(K.path_goal != goal || !length(K.path) || !(RemasterStepOpen(K.path, src) || RemasterWalkingMateOn(K.path[1], G, src)))
		if(K.target) held = RmChaseFirst(K, goal, reach)          // C (a), (b): a chase's cheaper ways
		if(!held && K.target) held = RmChaseThen(K, goal, reach)   // C (c), (e): the per-tick budget, a short detour
		if(!held) held = RmAttackRetry(K, goal)                    // B: after a search that found no step nearer, again at most once a second
		if(!held)
			// long or blocked routes go to the nearest point found, then look again
			if(rm_nav_count) rm_path_who = RmNavAttackWho(src, K, goal, reach)
			if(G) rm_path_pass = G.Pass(src)
			K.path = K.target ? RmChaseSearch(K, goal, reach) : RemasterOrderPath(src, goal, reach, partial = 1)   // C (d): a chase's search bounded
			rm_path_pass = null
			if(!K.target && rm_path_partial && !length(K.path) && rm_route && !RmReachNo(src, goal, reach))   // a march past the search's reach: the route map's whole way (Native.dm)
				var/list/MR = RmRouteMap(src, goal, reach)
				if(islist(MR) && length(MR))
					K.path = MR
					rm_path_partial = 0
			K.path_goal = goal
			RmAttackSearched(K, goal)
	if(held == 3) return 0   // C (a): a foe it picked itself has no free side: given up, the attack tick takes another
	if(held == 2 && length(K.path) && !(RemasterStepOpen(K.path, src) || RemasterWalkingMateOn(K.path[1], G, src)))   // B, C: its old route's next step shut: it waits
		destination = null
		return 1
	if(length(K.path))
		destination = K.path[1]
		K.stuck_since = 0
	else
		destination = null
		if(!keep) return 0
		if(!K.stuck_since) K.stuck_since = world.time
		remaster_order_status = "No way through yet; trying again"
	return 1

// --- B: after a route search that failed, again at most once a second (the owner, 10-27) ------------------------------
// The owner: "would it be cheaper to do a follow a friendly unit role for movement but we keep the attack order every
// second, maybe a nearby unit has a better route". After a route search that found no way or went only part of the way
// (an attack on a foe, an attack-move's march, an order: Orders.dm RemasterApproach), the unit searches again at most once a
// second (rm_retry_gap), and at once if its foe moved more than a tile since or stairs or a ramp were made (rm_ways_ver).
// Until then it keeps its old route while that route's next step is open, and waits while it is shut. A unit with no
// stairs to its order's level looks for them again once a second the same way (Orders.dm). The friend's route was
// measured and left out (reports/movement-fixes/search: in a 250 v 250 battle a nearby friend had a route a unit could take
// for 6% of tries, and none with the foes across a river; each try cost about as much as the search it would save).
// With the tick profiler on: "retry/held a second" and "retry/no stairs held" count the searches not made. RM_RETRY=0 in
// the server's environment: off, as before.
var/rm_retry_on = -1          // -1 until read (RM_RETRY)
var/rm_retry_gap = 10         // ticks between searches after one that failed or went part of the way
var/rm_ways_ver = 0           // moves when stairs or a ramp are made (Construction.dm, WallWalks.dm, Gather.dm, ...)
// a chase that gets no nearer (RmChaseLost): the foe, how near it came, since when
datum/remaster_attack/var/tmp/mob/Monsters/chase_of
datum/remaster_attack/var/tmp/chase_d = 0
datum/remaster_attack/var/tmp/chase_at = 0
mob/Monsters/proc/RmChaseLost(datum/remaster_attack/K, mob/Monsters/E)
	var/d = get_dist(src, E)
	if(K.chase_of != E || d < K.chase_d)
		K.chase_of = E
		K.chase_d = d
		K.chase_at = world.time
		return 0
	return world.time - K.chase_at > 80   // 8 s and no nearer
datum/remaster_attack/var/tmp/partial = 0          // its last search: 0 the whole way, 1 part of a long way, 2 as close as it gets
datum/remaster_attack/var/tmp/search_at = -1000
datum/remaster_attack/var/tmp/turf/search_goal
datum/remaster_attack/var/tmp/mob/search_of        // the foe that search was for (null: its march)
datum/remaster_attack/var/tmp/search_ver = 0
datum/remaster_attack/var/tmp/search_steps = 0     // how many steps the route that search found had (0: no step nearer)
datum/remaster_order/var/tmp/search_at = -1000
datum/remaster_order/var/tmp/turf/search_goal
datum/remaster_order/var/tmp/search_ver = 0
datum/remaster_order/var/tmp/nostairs_at = 0       // when it last looked for stairs to its target's level and found none
datum/remaster_order/var/tmp/nostairs_ver = 0

proc/RmRetryOn()
	if(rm_retry_on < 0) rm_retry_on = world.GetConfig("env", "RM_RETRY") == "0" ? 0 : 1
	return rm_retry_on

// In an attack's approach (RemasterAttackApproach): 2 when its last search for this foe or march failed or went part of
// the way under a second ago, its foe within a tile of where it was then and no stairs or ramp made since (no search now);
// else 0.
mob/Monsters/proc/RmAttackRetry(datum/remaster_attack/K, turf/goal)
	if(!K.partial || K.search_of != K.target || world.time >= K.search_at + rm_retry_gap || K.search_ver != rm_ways_ver) return 0
	if(!K.search_goal || K.search_goal.z != goal.z || get_dist(goal, K.search_goal) > 1 || !RmRetryOn()) return 0
	if(K.search_steps && !length(K.path)) return 0   // that search found steps nearer and it has walked them: it looks again at once
	if(K.target && !RmReachNo(src, goal, 1)) return 0   // a chase: held only when the ground has no way to its foe (the reach map, Native.dm), never for a crowd
	if(rm_prof) RmProfAdd("retry/held a second", 0)
	return 2

mob/Monsters/proc/RmAttackSearched(datum/remaster_attack/K, turf/goal)
	K.partial = rm_path_partial
	K.search_steps = length(K.path) - (length(K.path) && K.path[1] == loc)   // not counting its own tile
	K.search_at = world.time
	K.search_goal = goal
	K.search_of = K.target
	K.search_ver = rm_ways_ver

// In an order's approach (Orders.dm RemasterApproach): 2 when its route's next step is shut and its last search for the
// same goal failed or went part of the way under a second ago, no stairs or ramp made since (it waits); else 0.
mob/Monsters/proc/RmOrderRetry(datum/remaster_order/O, turf/goal)
	if(!O.partial || !length(O.path) || world.time >= O.search_at + rm_retry_gap || O.search_goal != goal || O.search_ver != rm_ways_ver || !RmRetryOn()) return 0
	if(rm_prof) RmProfAdd("retry/held a second", 0)
	return 2

mob/Monsters/proc/RmOrderSearched(datum/remaster_order/O, turf/goal)
	O.search_at = world.time
	O.search_goal = goal
	O.search_ver = rm_ways_ver

// --- C: a chase's cheaper ways before a route search (the owner, 10-27: all of (a)-(e)) -------------------------------
// A unit chasing a foe (an attack's approach to a foe's tile, its part or a siege engine; not an attack-move's march)
// searched a route again whenever the foe stepped, its route ran out or the route's next step was shut: the biggest cost
// of a big fight (route searches, 338 of ~1,100 ms a game second at 250 v 250). Before such a search now, in this order:
//  (a) a fighter whose foe has no open tile beside it (all 8 held or shut): no route could end beside it. It keeps its
//      old route (on along it while the next step is open, else it waits) and looks again next pass. Its first search
//      for that foe still runs, so it closes in as far as it can.
//  (b) the foe within 2 tiles of the route's end: the route is kept and only its last tile aimed again, at an open tile
//      beside the foe next to the tile before it (or one more tile on); with no route left, one step beside the foe.
//  (c) a budget: chase searches stop for the tick once they have taken rm_chase_ms; past it a unit keeps its old route
//      as in (a), once (the next time it searches whatever the budget).
//  (e) the route's next step shut, the rest of it still right: a short search round it to the route a few tiles on.
//  (d) the search itself goes no further than its foe's distance + rm_chase_margin from the unit.
// Every route is walked step by step with the usual checks (Clip.dm RemasterStepOpen: never ending on a friend's tile).
// Up on a mountain (block heights, Gather.dm) a unit that can't climb gets (a), (c) and (d) only. RM_CHASE=<bits> in the
// server's environment picks them (1 a, 2 b, 4 c, 8 d, 16 e; 0 none, as before); all by default. With the tick profiler
// on, "chase/<part>" counts what they did.
#define RM_CHASE_FULL 1
#define RM_CHASE_REAIM 2
#define RM_CHASE_BUDGET 4
#define RM_CHASE_BOUND 8
#define RM_CHASE_DETOUR 16
var/rm_chase_on = -1          // -1 until read (RM_CHASE)
var/rm_chase_ms = 20          // (c) ms of chase searches in a tick
var/rm_chase_margin = 6       // (d) tiles past the foe's distance a chase search may go
var/rm_detour_ahead = 3       // (e) tiles on past the shut one a detour rejoins the route
var/rm_chase_tick = -1
var/rm_chase_used = 0
var/list/rm_chase_dirs = list(NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST)
datum/remaster_attack/var/tmp/mob/chased          // the foe its last chase search was for
datum/remaster_attack/var/tmp/budget_held = 0     // (c) held back by the budget the last time

proc/RmChaseOn()
	if(rm_chase_on < 0)
		var/e = world.GetConfig("env", "RM_CHASE")
		rm_chase_on = (isnull(e) || e == "") ? 19 : (text2num(e) || 0)   // (a), (b), (e); the budget (c) and bound (d) slowed a fight's start
	return rm_chase_on

proc/RmChaseSpent(t0)
	if(rm_chase_tick != world.time)
		rm_chase_tick = world.time
		rm_chase_used = 0
	rm_chase_used += max(0, (world.tick_usage - t0) * world.tick_lag)   // tick_usage is a share of the tick, tick_lag 1 = 100 ms

// (a) and (b): 2 held (no search now), 1 its route aimed again, 0 neither.
mob/Monsters/proc/RmChaseFirst(datum/remaster_attack/K, turf/goal, reach)
	var/on = RmChaseOn()
	if(!on) return 0
	if((on & RM_CHASE_FULL) && reach == 1 && K.chased == K.target && RmChaseFull(goal))
		if(K.goal && K.target != K.chosen)   // a foe it picked itself on an attack-move: another with room
			if(rm_prof) RmProfAdd("chase/a: foe full, another foe", 0)
			return 3
		if(get_dist(src, goal) > 2 && world.time >= K.search_at + rm_retry_gap)   // not yet at the ring round it: closing in, once a second
			if(rm_prof) RmProfAdd("chase/a: foe full, closing in", 0)
			return 0
		if(rm_prof) RmProfAdd("chase/a: foe has no free side, held", 0)
		return 2
	if((on & RM_CHASE_REAIM) && (z != SKY_LAYER || RemasterCanClimb(src)) && RmChaseReaim(K, goal, reach))
		if(rm_prof) RmProfAdd("chase/b: end aimed again", 0)
		return 1
	return 0

// (c) and (e): 2 held by the budget, 1 a detour taken, 0 neither (it searches).
mob/Monsters/proc/RmChaseThen(datum/remaster_attack/K, turf/goal, reach)
	var/on = RmChaseOn()
	if(!on) return 0
	if(on & RM_CHASE_BUDGET)
		if(rm_chase_tick != world.time)
			rm_chase_tick = world.time
			rm_chase_used = 0
		if(rm_chase_used >= rm_chase_ms && !K.budget_held && K.chased == K.target)   // never a first search for a foe (a click's stays instant)
			K.budget_held = 1
			if(rm_prof) RmProfAdd("chase/c: over the budget, held", 0)
			return 2
		K.budget_held = 0
	if((on & RM_CHASE_DETOUR) && K.path_goal == goal && length(K.path) >= 2 && (z != SKY_LAYER || RemasterCanClimb(src)) && RmChaseDetour(K, goal))
		if(rm_prof) RmProfAdd("chase/e: a detour", 0)
		return 1
	return 0

// (d) The chase's own search: bounded round the unit to its foe's distance + rm_chase_margin.
mob/Monsters/proc/RmChaseSearch(datum/remaster_attack/K, turf/goal, reach)
	var/t0 = world.tick_usage
	. = (RmChaseOn() & RM_CHASE_BOUND) ? RemasterOrderPath(src, goal, reach, loc, get_dist(src, goal) + rm_chase_margin, 1) : RemasterOrderPath(src, goal, reach, partial = 1)
	RmChaseSpent(t0)
	K.chased = K.target

// (a) No tile beside goal is one this unit's route could end on (open, no unit on it), as Native.dm RmNavFoeFull.
mob/Monsters/proc/RmChaseFull(turf/goal)
	var/list/side = RmSide(src)
	for(var/d in rm_chase_dirs)
		var/turf/C = get_step(goal, d)
		if(C && RemasterWalkable(C, src, goal, side) == 1) return 0
	return 1

// (b) The route kept while its foe stands within 2 tiles of its end: the last tile aimed again, at an open tile within
// reach of the foe next to the tile before it (or one more tile on from the end); with no route left its own tile is the
// end, and it takes one step. 1: done and its next step open; 0: no such tile, or the next step shut (its end may have
// been set right: then (e) may go round).
mob/Monsters/proc/RmChaseReaim(datum/remaster_attack/K, turf/goal, reach)
	var/list/path = K.path
	var/n = length(path)
	var/turf/E = n ? path[n] : loc
	if(!isturf(E) || E.z != goal.z || get_dist(E, goal) > reach + 1) return 0
	var/list/side = RmSide(src)
	if(!n || get_dist(E, goal) > reach || RemasterWalkable(E, src, goal, side) != 1)
		var/turf/P = n > 1 ? path[n - 1] : loc
		var/turf/best
		for(var/d in rm_chase_dirs)
			var/turf/C = get_step(P, d)
			if(C && C != loc && get_dist(C, goal) <= reach && RemasterWalkable(C, src, goal, side) == 1 && (!best || get_dist(C, E) < get_dist(best, E))) best = C
		if(best)
			if(n) path[n] = best
			else K.path = list(best)
		else
			if(!n || !RemasterWalkable(E, src, goal, side)) return 0
			for(var/d in rm_chase_dirs)
				var/turf/C = get_step(E, d)
				if(C && C != loc && get_dist(C, goal) <= reach && RemasterWalkable(C, src, goal, side) == 1)
					best = C
					break
			if(!best) return 0
			path += best
	K.path_goal = goal
	return RemasterStepOpen(K.path, src)

// (e) Its route's next step shut, the rest still right: a short search round it to the route a few tiles on (the first
// open tile from rm_detour_ahead past the shut one), joined to the rest. 0: none (it searches in full).
mob/Monsters/proc/RmChaseDetour(datum/remaster_attack/K, turf/goal)
	var/list/path = K.path
	var/n = length(path)
	var/list/side = RmSide(src)
	for(var/i = min(n, rm_detour_ahead + 1), i <= min(n, rm_detour_ahead + 3), i++)
		var/turf/R = path[i]
		if(!isturf(R) || R.z != z || RemasterWalkable(R, src, goal, side) != 1) continue
		var/t0 = world.tick_usage
		var/list/S = RemasterOrderPath(src, R, 0, loc, get_dist(src, R) + 2)
		RmChaseSpent(t0)
		if(!length(S)) return 0
		K.path = S + path.Copy(i + 1)
		return RemasterStepOpen(K.path, src)
	return 0

// --- The battle ways: gang up (the owner, 10-28) ----------------------------------------------------------------------
// The owner: "or have the world preplan the best routes so everyone can fight gangup", then, told that such routes made
// in the game's script would cost more than they save but the engine could make them in about a millisecond, "then we
// should do it in native" and "should we do the gang reup picks?". A fighter closing in on a foe it picked itself (an
// attack-move's, an attack box's or an A-click's pool, one it found marching) within rm_gang_reach tiles takes the way the
// battle gives instead of a route search: its side's field (Native.dm RmFieldRoute, the engine's RmField.cs) leads it to
// the nearest free tile beside any standing foe of that realm, and there it fights a foe beside it, the one most of its
// side are already beside (gang up), then the weakest. One you clicked on its own (a plain click, no A) is still chased as
// before; while that one has no free side (it would wait), the fighter fights the nearest it can get beside instead, and
// goes back to it when that one falls (RemasterAttackTick). A capture order and a finishing blow keep their own foe. With
// no field (an older engine, RM_FIELD=0, the Sky layer's heights, a flyer, a foe of no realm) or no free side near, the
// chase runs as before. With the tick profiler on, "gang/<what>" counts what it did.
// A foe of an attack box or one found on an attack-move takes the field at any distance (the owner, 10-29, 1000 v 1000: a
// box shares its foes out, so a front-rank fighter was often given one deep in the other block, more than rm_gang_reach
// off with a foe right in front of it, and searched a route to it that the foes' ranks shut: ~0.5 ms a time, the biggest
// cost of the battle). Past the field's reach (RmField.cs MaxSteps) it chases as before.
var/rm_gang_reach = 12
datum/remaster_attack/var/tmp/field_at = -1000   // when its route came from the field (path_goal is null for one)

// No room near (squad-split, the owner 10-29: "Shared chase first"): every place to fight its realm from within the field's
// reach is taken, so a box's or an attack-move's fighter waits behind those in contact instead of searching a route to its
// foe through the full front (that chase was ~0.5 ms a time, 1,000-2,800 a second in a 1000 v 1000 from ~40 s in). Its
// step towards the foe decides: open, it takes it (closing up); a unit of its side there, it waits; anything else (water,
// rock, a foe, its own door), the chase as before. The field is asked again on its next pass. RM_GANG_WAIT=0 in the server's environment:
// the chase, as before. With the tick profiler on, "gang/no room near: closes up" and "...: waits behind" count them.
var/rm_gang_wait = -1   // -1 until read (RM_GANG_WAIT)
proc/RmGangWaitOn()
	if(rm_gang_wait < 0) rm_gang_wait = world.GetConfig("env", "RM_GANG_WAIT") == "0" ? 0 : 1
	return rm_gang_wait

// 1 when it closed up or waits (no search), 0 for the chase.
mob/Monsters/proc/RmGangWaitBehind(datum/remaster_attack/K, mob/Monsters/E)
	var/turf/T = get_step_towards(src, E)
	if(!T || T == loc) return 0
	var/list/side = RmSide(src)
	var/w = RemasterWalkable(T, src, null, side)
	if(!w) return 0
	if(w == 2)   // through only: a unit of its side there it waits behind; its own door there, the chase as before
		var/behind = 0
		for(var/mob/Monsters/F in T) if(F != src && RmSideUnit(F, side)) behind = 1
		if(!behind) return 0
	K.field_at = world.time
	K.path_goal = null
	K.last_position = loc
	K.last_progress = world.time
	if(w == 1)
		if(rm_prof) RmProfAdd("gang/no room near: closes up", 0)
		K.path = list(T)
		destination = T
	else
		if(rm_prof) RmProfAdd("gang/no room near: waits behind", 0)
		K.path = null
		destination = null
	remaster_order_status = "Waiting for room to fight [RemasterCombatName(E)]"
	return 1

mob/Monsters/proc/RmGangUp(datum/remaster_attack/K, mob/Monsters/E)
	if(!rm_field || !E.Owner || K.capture || K.finish || z == SKY_LAYER) return 0
	if(get_dist(src, E) > rm_gang_reach && !K.pool && !(K.goal && E != K.chosen)) return 0   // a box's or an attack-move's foe further off: the field still first
	if(E == K.chosen && !K.pool && !K.goal && !RmChaseFull(E.loc)) return 0   // a foe you clicked, with room beside it: the chase
	var/mob/Monsters/B = RmFoeBeside(E.Owner)
	if(B)
		if(rm_prof) RmProfAdd("gang/a foe beside it", 0)
		K.target = B
		K.path = null
		destination = B
		K.last_progress = world.time
		remaster_order_status = "Fighting [RemasterCombatName(B)]"
		return 1
	while(length(K.path) && K.path[1] == loc) K.path.Cut(1, 2)
	if(K.path_goal || world.time >= K.field_at + max(10, RmFieldKeepTicks()) || !length(K.path) || !RemasterStepOpen(K.path, src))   // its way kept a while (below)
		var/R = RmFieldRoute(src, E.Owner)
		if(!islist(R))   // none near, or not known: the chase
			if(!isnull(R) && (K.pool || (K.goal && E != K.chosen)) && RmGangWaitOn() && RmGangWaitBehind(K, E)) return 1   // no room near: behind its front
			if(rm_prof) RmProfAdd(isnull(R) ? "gang/not known: the chase" : "gang/no room near: the chase", 0)
			return 0
		K.path = R
		K.path_goal = null
		K.field_at = world.time
		if(rm_prof) RmProfAdd("gang/a route from the field", 0)
	K.last_position = loc
	K.last_progress = world.time
	if(!length(K.path) || !RemasterStepOpen(K.path, src))   // every place to fight from near is taken: it waits its turn
		destination = null
		remaster_order_status = "Waiting for room to fight [RemasterCombatName(E)]"
		return 1
	if(rm_field_noback && K.path[1] == rm_came_from && world.time - remaster_stepped_at < 20)   // never straight back (below): it waits a moment
		destination = null
		remaster_order_status = "Waiting for room to fight [RemasterCombatName(E)]"
		return 1
	destination = K.path[1]
	return 1

// No rubberbanding on the field (the owner, 10-29, watching a 1000 v 1000 in app 133: "pretty smooth only problem is the
// rubberbanding"): a fighter walking the field's way asked the field again every second, and on a crowded front the nearest
// free place to fight from flips between ahead and behind as places fill and open, so it walked forward and back: 12% of
// a battle's steps went straight back to the tile left under 2 s before, nine in ten after a new way from the field
// (reports/polish-night-1026/field-keep). Now it keeps its way for RM_FIELD_KEEP ticks (default 30) while the way's next
// step is open, and never steps straight back onto the tile it just left within 2 s while it walks the field: it waits a
// moment instead (the place it went for is likely taken; the field leads it on from where it stands). In a 1000 v 1000:
// 12% -> 4.6% of steps, the fighting about as before. RM_FIELD_KEEP=0 (asked again every second) and RM_FIELD_NOBACK=0
// (steps straight back allowed) in the server's environment: as before.
var/rm_field_keep = -1    // ticks; -1 until read (RM_FIELD_KEEP)
var/rm_field_noback = 1   // RM_FIELD_NOBACK=0: off
proc/RmFieldKeepTicks()
	if(rm_field_keep < 0)
		var/v = world.GetConfig("env", "RM_FIELD_KEEP")
		rm_field_keep = isnull(v) || v == "" ? 30 : max(0, text2num(v) || 0)
		rm_field_noback = world.GetConfig("env", "RM_FIELD_NOBACK") != "0"
	return rm_field_keep
mob/Monsters/var/tmp/atom/rm_came_from   // the tile its last step left (Chains/Move.dm)

// The foe beside it to fight, of that realm (or of an attack box's pool): standing and one it may fight; the one most of its
// own side are beside (gang up), then the weakest. Of a realm (no pool), the engine first says whether anyone of it stands
// on the tiles round it at all (Native.dm rm_foe_beside): nobody, and it answers null at once.
mob/Monsters/proc/RmFoeBeside(foe, list/pool = null)
	var/none = !pool && rm_foe_beside_native && rm_foe_beside(src, foe, /mob/Monsters) == 0
	if(none && !rm_foe_beside_verify) return null
	var/list/pairs = list()
	var/mob/Monsters/best
	var/best_n = -1
	for(var/mob/Monsters/O in RmUnitsNear(1, src)) if(O != src && O.Owner != Owner && (pool ? (O in pool) : O.Owner == foe) && !RmDownOut(O) && RemasterHostile(src, O, !!pool, pairs))
		var/n = 0
		for(var/mob/Monsters/F in RmUnitsNear(1, O)) if(F != src && F.Owner == Owner) n++
		if(n > best_n || (n == best_n && O.HP < best.HP))
			best = O
			best_n = n
	if(none) RmFoeBesideVerify(src, best)
	return best

// An attack box's next foe (RemasterAttackTick), before RemasterPoolNext's look over the whole box (5.5 ms in a 500 v 500,
// and with the battle ways foes fall twice as fast): one of the box beside it (RmFoeBeside), else the nearest of it within
// 6 tiles while the field has a way for it to a free side of that realm's line. Counted into the box's shares as
// RemasterPoolNext counts its own; null: the look over the box.
mob/Monsters/proc/RmPoolNear(datum/remaster_attack/K)
	var/mob/Monsters/B = RmFoeBeside(null, K.pool)
	if(!B)
		var/d = 1#INF
		for(var/mob/Monsters/O in RmUnitsNear(6, src)) if(O.Owner != Owner && O.z == z && get_dist(src, O) < d && (O in K.pool) && !RmDownOut(O) && RemasterHostile(src, O, 1))
			B = O
			d = get_dist(src, O)
		if(!B || !length(RmFieldRoute(src, B.Owner))) return null
	if(rm_prof) RmProfAdd(get_dist(src, B) <= 1 ? "gang/box: the one beside it" : "gang/box: the nearest", 0)
	K.pool_load[B] = (K.pool_load[B] || 0) + 1
	if(RemasterFormationRole() in list("ranged", "mage")) K.pool_far[B] = (K.pool_far[B] || 0) + 1
	K.target = B
	K.chosen = B
	K.path = null
	remaster_order_status = "Attacking [RemasterCombatName(B)]"
	return B

mob/Monsters/proc/RemasterAttackTick()
	var/datum/remaster_attack/K = remaster_attack
	if(!K) return 0
	if(Owner != K.issuer || HP <= 0 || GoingToDie)
		RemasterAttackStop()
		return 0
	if(Sleeping || Fainted || Stunned || InHole) return 1      // keeps the order until it can act
	var/mob/Monsters/E = K.target
	if(E && RmFogAttackLost(K, E)) return 1   // fog of war: out of sight, to where it was last seen (Fog.dm)
	E = K.target
	if(E && !RemasterHostile(src, E, 1, RmAtkPairs(Owner))) E = null
	if(!E && K.chosen && K.target != K.chosen && !K.pool && RemasterHostile(src, K.chosen, 1, RmAtkPairs(Owner)))   // the one it fought while the foe you clicked had no room fell: back to that one (RmGangUp)
		E = K.chosen
		K.target = E
		K.path = null
	var/mob/Monsters/fallen   // the foe it went for fell (its order is done; Falls.dm finishes it once none stand near)
	if(E && E != K.finish && !K.capture && !remaster_nonlethal && (E.Fainted || E.rm_dying_until || E.RemasterKnockedOut()) && RmStandingFoeNear(src))   // RmDownOut (Falls.dm); E passed RemasterHostile above   // down, a foe standing near: out of the fight for now (Falls.dm)
		fallen = E
		E = null
	if(!E && K.pool && rm_field) E = RmPoolNear(K)   // the battle ways: one of the box beside it or near it first (RmGangUp)
	if(!E && K.pool) E = RemasterPoolNext()   // an attack box: the next of its foes (Formations.dm)
	if(!E)
		K.target = null
		// attack-move: of the hostiles in sight and those its group fights or saw near it, one it can get at, shared out as
		// a box's are (Formations.dm RemasterMarchFoe, RemasterFoeScore)
		if(K.goal)
			E = RemasterMarchFoe(K)
			if(E)
				K.target = E
				K.path = null
				remaster_order_status = "Fighting [RemasterCombatName(E)]"
	if(E && istype(E, /mob/Monsters/RemasterSiege))   // RemasterIsSiege (Siege.dm)
		// a siege engine is wrecked from beside it (Siege.dm), never with weapons or throws
		if(get_dist(src, E) <= 1)
			destination = null
			K.last_progress = world.time
		else if(!RemasterAttackApproach(E.loc, 1))
			K.target = null
			K.path = null
			if(!K.goal) RemasterAttackStop()
		return 1
	if(E && (K.capture || remaster_nonlethal) && RemasterCaptureTick(K, E)) return 1     // Capture orders and non-lethal fighting (Subdue.dm)
	if(E)
		var/obj/RmBeastFoot/BF = length(E.rm_feet) ? RmBeastPartFor(src, E) : null   // a great beast on the ground: fought at its parts (Beasts.dm)
		if(HoldingWeapon == "Spear" && get_dist(src, E) == 2 && (E in oview(2, src)) && world.time >= remaster_reach_at)
			destination = null            // a spear strikes from two tiles away
			remaster_reach_at = world.time + 12
			RemasterStrike(E, "reach")
			return 1
		if(world.time >= remaster_throw_at && HoldingWeapon != "Bow" && HasRightArm && get_dist(src, E) >= 2 && RemasterTryThrow(E))       // javelins, throwing axes, rocks before closing in
			K.last_progress = world.time
			return 1
		// archers and casters: their spells from range while the mana lasts; out of arrows, a blade or fists (Formations.dm)
		if(HoldingWeapon == "Bow" && RemasterBowToMelee()) K.path = null
		var/cast = RemasterCastFirst(E)
		if(cast == 1)
			K.last_progress = world.time
			remaster_order_status = "[HoldingWeapon == "Bow" ? "Shooting at" : "Casting at"] [RemasterCombatName(E)]"   // a bow's moves are arrows
			return 1
		if(cast >= 2 && RemasterAttackApproach(E.loc, cast, E == K.chosen))
			remaster_order_status = "Closing in to [HoldingWeapon == "Bow" ? "shoot" : "cast"] at [RemasterCombatName(E)]"
			return 1
		// a shot reaches as far as the bow does (5-8 tiles, BeastParts.dm RmBowRange), so it stands within that, arrows in hand
		if(HoldingWeapon == "Bow" && RemasterCanShoot() && (E in oview(RemasterShotReach(E), src)))
			destination = null
			Target = E
			remaster_order_status = "Shooting at [RemasterCombatName(E)]"
			if(world.time >= K.next_shot)
				K.next_shot = world.time + 50
				BowOn = 1
				BowTarget(1)
				BowOn = 0
		else if(BF)
			if(get_dist(src, BF) <= 1)
				K.last_progress = world.time
				remaster_order_status = "Fighting [RemasterCombatName(E)]: its [BF.part]"
				RmBeastStrikePart(E, BF)
			else if(!RemasterAttackApproach(BF.loc, 1, E == K.chosen))
				K.target = null
				K.path = null
				if(!K.goal) RemasterAttackStop()
		else if(!Flying && RmBeastKind(src) && RmJawStrike(E))   // a great beast bites from where its head is (Beasts.dm)
			K.last_progress = world.time
			remaster_order_status = "Fighting [RemasterCombatName(E)]"
		else if(get_dist(src, E) <= 1)
			// WalkTo/Bump owns melee and its original weapon/limb rules.
			destination = E
			K.last_progress = world.time
			remaster_order_status = "Fighting [RemasterCombatName(E)]"
		else if(RmGangUp(K, E))   // the battle's way: to the nearest place to fight its realm from, and whoever is beside it there
			K.stuck_since = 0
		else if(K.goal && E != K.chosen && RmChaseLost(K, E))
			// one it picked itself on an attack-move that keeps away from it (a wanderer, a runner): left a while, on to its goal
			// (the owner, 10-28: "chasing all over the place"). One you clicked is still chased; a wild one stands and fights.
			if(!K.skip) K.skip = list()
			K.skip[E] = world.time + 150
			K.target = null
			K.path = null
		else if(!RemasterAttackApproach(E.loc, 1, E == K.chosen))
			// can't reach one it picked itself: drop it (attack-move carries on to its goal, and leaves that one a while)
			if(K.goal)
				if(!K.skip) K.skip = list()
				K.skip[E] = world.time + 100
			K.target = null
			K.path = null
			if(!K.goal) RemasterAttackStop()
		return 1
	if(K.goal)
		// at its slot in the group's formation (or beside it, taken), else within a tile of the spot
		var/there = K.group ? (loc == K.goal || (get_dist(src, K.goal) <= 1 && RemasterSlotTaken(K.goal, K.group, src))) : get_dist(src, K.goal) <= 1
		if(there || (K.stuck_since && world.time - K.stuck_since > 300))
			RemasterAttackStop()
			return 0
		remaster_order_status = "Attack-move"
		RemasterAttackApproach(K.goal, 0, 1)
		return 1
	RemasterAttackStop()
	if(fallen) remaster_order_status = "Brought down [RemasterCombatName(fallen)]"   // as a Non-lethal one's "Knocked out <foe>" (Subdue.dm)
	return 0

// Keys pressed while the game window, not the HUD page, has focus (skin.dmf bindings): Q/E turn the 3D
// camera, N faces it north, the arrow keys pan it (camera-relative, smoothed on the page), Esc does what Esc does in
// the page (cancel Attack mode, an aim, a placement, close a card...) (remastered.html window.key3d).
Player/verb/Remaster3DKeyVerb(k as text)
	set name = "Remaster-3D-Key"
	set hidden = 1
	set instant = 1
	// c (cutaway) and x (x-ray) are the page's keys too (rts-feel 2026-10-25: the 2006 letter keys off the keyboard)
	// b: the Build bar (hud-controls 2026-10-26, the owner: "Yes, B and T"; T went with the Tend button)
	if(client && (k in list("q", "e", "n", "north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest", "escape", "c", "x", "b"))) src << output(k, "mapwindow.hud:key3d")

// The 3D camera to a spot at once (remastered.html rfCamTo), for jumps the server makes: Z, a control group's
// second tap, Backspace to the last alert. The page would otherwise follow on its next 3D update.
Player/proc/RemasterCamTo(atom/A)
	if(client && A && RmViewLayer(A) == z) src << output("[A.x],[A.y]", "mapwindow.hud:rfCamTo")   // on the view's level (Peaks.dm)

// A: Attack mode for the selected units (next click picks the enemy or the attack-move spot).
Player/verb/RemasterAttackVerb()
	set name = "Remaster-Attack"
	set hidden = 1
	RemasterAttackModeToggle()

Player/proc/RemasterAttackModeToggle()
	if(!length(Selected))
		RemasterNotice("Select units first, then Attack.")
		remaster_attack_mode = 0
		return
	remaster_attack_mode = !remaster_attack_mode
	RemasterNotice(remaster_attack_mode ? "Attack: click an enemy, or the ground to attack-move. Esc or a right-click cancels." : "Attack cancelled.")
