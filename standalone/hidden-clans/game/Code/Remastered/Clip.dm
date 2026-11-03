// Friendly and allied units walk through each other (the user, 2026-10-24: "allow units to go past but never on the
// same tile", then "they can clip them no swap"). A unit on its way goes through a tile that holds only units of its
// side (its owner's, or an ally's: RemasterAllied), with no swap and no waiting, and never stops on one: routes go
// through them but never end on one (Orders.dm RemasterWalkable's side list and RemasterOrderPathDM, and the engine's
// copy, engine/native/RmWalk.cs and RmPath.cs), a step onto one is let through only when the route goes on from it to
// an open tile it can stop on, and a unit left standing on one anyway (its way on blocked meanwhile, or another
// stopping where it stood) steps to an open tile beside it. Siege engines and carts still block; enemies and wild
// creatures block as before.

Player/var/tmp/list/rm_side          // this tick's RmSide for this player's units
Player/var/tmp/rm_side_at = -1

// The owners whose units M goes through: its own owner and, for a player, its allies.
proc/RmSide(mob/Monsters/M)
	if(!M || !M.Owner) return null
	var/Player/P = M.Owner
	if(!istype(P)) return list(M.Owner)
	if(P.rm_side_at != world.time || !P.rm_side)
		P.rm_side_at = world.time
		P.rm_side = list(P)
		if(P.key)
			var/list/groups = RmSideGroups()
			var/list/g = groups[RemasterRootKey(P.key)]
			if(g) for(var/Player/O in g) if(O != P) P.rm_side += O
	return P.rm_side

// This tick's players by their realm's root (Realms.dm): allies are exactly the players of one root. Each player's side
// was made by asking RemasterAllied of every other player, every tick: 100 players moving made ~100,000 asks a
// second (load-asleep-1030, 10-31, planning/MANY_PLAYERS_PLAN_2026-10-31.md); now one pass a tick.
var/list/rm_side_groups = list()
var/rm_side_groups_at = -1
proc/RmSideGroups()
	if(rm_side_groups_at == world.time) return rm_side_groups
	rm_side_groups_at = world.time
	rm_side_groups = list()
	for(var/Player/O in Players)
		if(!O.key) continue
		var/r = RemasterRootKey(O.key)
		var/list/g = rm_side_groups[r]
		if(!g)
			g = list()
			rm_side_groups[r] = g
		g += O
	return rm_side_groups

// A unit that one with this side goes through. Mirrored in the engine (engine/native/RmWalk.cs SideUnit).
proc/RmSideUnit(atom/movable/A, list/side)
	return side && istype(A, /mob/Monsters) && !istype(A, /mob/Monsters/RemasterSiege) && !A:Wagon && A:Owner && (A:Owner in side)

// The next tile of a route (path[1]) can be stepped onto: open, or holding only units of its side with the route
// going on from it, through no more than RM_CLIP_AHEAD of them, to an open tile (so it is never left on one).
#define RM_CLIP_AHEAD 12
proc/RemasterStepOpen(list/path, mob/Monsters/M, turf/goal = null)
	if(!length(path)) return 0
	var/list/side = RmSide(M)
	var/w = RemasterWalkable(path[1], M, goal, side)
	if(w != 2) return w == 1
	if(path[1] == goal && M.remaster_active && M.remaster_active.kind == "Hop" && M.remaster_active.target == goal) return 1   // the top it hops down from: onto its own people there and straight down (a building's first step is its one way down: six builders upstairs waited for good while one stood on it, the real game 10-30)
	return RmClipLands(path, M, goal, side)

// Going on from path[1] (a tile of its side), the first tile that isn't is open, before the route ends.
proc/RmClipLands(list/path, mob/Monsters/M, turf/goal, list/side)
	if(path[1] == goal) return 0
	for(var/i = 2, i <= min(length(path), RM_CLIP_AHEAD + 1), i++)
		var/w = RemasterWalkable(path[i], M, goal, side)
		if(w == 1) return 1
		if(!w || path[i] == goal) return 0
	return 0

// The way this unit is going whose next tile is T, or null: a bag going in (a delivery, kept beside the job's own order
// while it goes, Delivery.dm), an order's route, an attack's, guard duty's, a building site's; or a walk straight at a
// spot (a tool on the stockpile, an item beside it) that only passes T. The user, 2026-10-24: "we should allow clipping
// to pick up items and etc we just do not allow units on the same tile on rest place". So every way a unit goes passes
// its own side, and where it stops is never a friend's tile (RmClipLands; RmStepOffShared steps it off one). Before, a
// delivery's route wasn't here: a villager carrying goods in stopped behind anyone of its own in the way and the ones
// behind it stopped too (200 workers: about a hundred carriers stood for minutes; 2,000: nothing came in).
mob/Monsters/proc/RmRouteInto(turf/T)
	if(remaster_delivery && length(remaster_delivery.path) && remaster_delivery.path[1] == T) return remaster_delivery.path
	for(var/list/L in list(remaster_active && remaster_active.path, remaster_attack && remaster_attack.path, remaster_defense && remaster_defense.path, remaster_site_path))
		if(length(L) && L[1] == T) return L
	if(isturf(destination) && destination != T && destination:z == T.z && get_dist(T, destination) < get_dist(src, destination)) return list(T, destination)
	return null

// turf/grounds/Enter: this file's part is step RmChainEnter_Clip in Code/Remastered/Chains/Enter.dm

// Never left standing on one of its side (the orders tick, Orders.dm RemasterOrdersTick): sharing a tile with one and
// not stepping for a second, it steps to an open tile beside it, the one nearest where it is going. Of two sharing,
// one with an order moves first; of two with none, the one that came last, at once (not on its own turn in the pass).
// With no open tile beside it (a corridor full of its side), one with nothing to do walks on (RmStepOffWalk).
// One asked by an older one (nested) doesn't ask the ones newer than itself in turn: the older one asks each of them
// itself. That chain went through every subset of a tile's units, 2^k calls for k stopped on one tile (jobs,
// 2026-10-25: the 500-villager job check by one stockpile piled 60 on one tile; with more on a tile it froze).
mob/Monsters/proc/RmStepOffShared(nested = 0)
	if(!isturf(loc) || !density || Flying || HP <= 0 || !CanWalk || Sleeping || Fainted || Stunned || world.time - remaster_stepped_at < 10) return
	var/list/side = RmSide(src)
	if(!side) return
	// the engine's two looks first (Native.dm rm_shares, rm_step_off_tile): nobody of its side on its tile, it's done
	var/sh = rm_step_off_native ? rm_shares(src, side) : null
	if(sh == 0 && !rm_step_off_verify) return
	var/busy = remaster_active || remaster_attack || remaster_defense
	var/shared = 0
	var/any = 0
	for(var/mob/Monsters/O in loc) if(O != src && O.density && !O.Flying && RmSideUnit(O, side))
		any = 1
		if(!busy && (O.remaster_active || O.remaster_attack || O.remaster_defense || O.remaster_stepped_at > remaster_stepped_at))
			if(!O.remaster_active && !O.remaster_attack && !O.remaster_defense && !nested) O.RmStepOffShared(1)
			continue
		shared = 1
	if(!isnull(sh)) RmStepOffVerify(src, "shares", sh, any)
	if(!shared) return
	var/turf/aim = (remaster_active && isturf(remaster_active.target)) ? remaster_active.target : loc
	var/turf/best
	var/nb = rm_step_off_native && !rm_nav_count && z != SKY_LAYER ? rm_step_off_tile(src, aim, rm_path_pass, rm_own_doors) : null   // up on the rock or a building: the heights are the DM's (below)
	if(isnull(nb) || rm_step_off_verify)
		for(var/turf/T in orange(1, src))
			if(T.z != z || RemasterWalkable(T, src, T) != 1 || RemasterTilePlaces(T, list(src)) <= 0) continue
			if(z == SKY_LAYER && !RmLevelAside(src, T)) continue   // up there: only as high as it stands (a builder stepped off a room's floor onto a lower house's wall top and had no way off: arena offset_room.dm, 10-30)
			if(!best || get_dist(T, aim) < get_dist(best, aim)) best = T
		if(!isnull(nb)) RmStepOffVerify(src, "tile", nb || null, best)
	else if(nb) best = nb
	if(!best)
		if(!busy && !length(remaster_orders)) RmStepOffWalk(side)
		return
	var/was = usr
	usr = src
	Move(best, get_dir(src, best))
	usr = was

// No open tile beside it: it walks, through tiles of its side only, to the nearest tile it can stop on within
// RM_CLIP_AHEAD steps (back the way it came, or on), as a move of its own that ends quietly and says again what the unit
// said before ("Got as close as it could"). So it is never left on a friend's tile, whatever order a tick's units step
// in (server cost, 2026-10-24: with the walk loop's v2 a packed head-on corridor left two friends stopped on one tile
// with a friend on each side).
#define RM_STEP_OFF_LOOK 120   // tiles looked at, at most
#define RM_STEP_OFF_AGAIN 30   // a look that found none is tried again 3 s later, not every pass
datum/remaster_order/rm_step_off
	kind = "Move"
	automatic = 1
	var/said

mob/Monsters/var/tmp/rm_step_off_at = 0

// Up on the rock or a building, whether M can step onto T at the height it stands at (stepping off a friend's tile there
// never goes down a block: it may be a roof with no way off).
proc/RmLevelAside(mob/Monsters/M, turf/T)
	var/list/sp = M.RemasterStepSpot(T)
	return sp && sp[2] == RemasterFeetOf(M)

mob/Monsters/proc/RmStepOffWalk(list/side)
	if(!istype(Owner, /Player) || world.time < rm_step_off_at) return 0
	var/list/seen = list(loc)
	var/list/ring = list(loc)
	for(var/d = 1, d <= RM_CLIP_AHEAD && length(ring) && length(seen) < RM_STEP_OFF_LOOK, d++)
		var/list/next = list()
		for(var/turf/C in ring) for(var/turf/T in orange(1, C)) if(T.z == z && !(T in seen))
			seen += T
			var/w = RemasterWalkable(T, src, null, side)
			if(w == 1 && RemasterTilePlaces(T, list(src)) > 0 && (z != SKY_LAYER || RemasterSpotAt(T, RemasterFeetOf(src))))   // up there: a place as high as it stands
				var/datum/remaster_order/rm_step_off/O = new
				O.issuer = Owner
				O.target = T
				O.said = remaster_order_status
				remaster_active = O
				RemasterStartOrder(O)
				return 1
			if(w == 2) next += T
		ring = next
	rm_step_off_at = world.time + RM_STEP_OFF_AGAIN
	return 0

mob/Monsters/RemasterFinishOrder(message)
	var/datum/remaster_order/rm_step_off/O = remaster_active
	if(!istype(O)) return ..()
	remaster_active = null
	destination = null
	Target = null
	remaster_blocked = null
	remaster_wait_for_resume = 0
	remaster_order_status = O.said

// mob/Monsters/Bump: this file's part is step RmChainBump_Clip in Code/Remastered/Chains/Bump.dm
