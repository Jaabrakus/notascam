// Group moves: formations, marching together and arriving tidily (Remastered, formations 2026-10-23).
// One click sends the selected units as one group (datum/remaster_group):
//  - Each gets its own slot in a tidy shape. "keep" moves the group's own shape over when it is close
//    together and makes a block facing the way they go when it is spread out; line, column and box are
//    built across and behind the direction of travel, snapped to the grid (clean on diagonals too).
//  - Slots are open tiles on the near side of the target (never across water or a wall from it); the
//    shape slides back towards the group when the target is up against an obstacle, and the slots are
//    handed out so no two routes cross.
//  - On the way they go through each other's tiles: a unit whose next tile holds a walking group-mate
//    waits for it (trying again each tick) instead of walking round it, and goes round only a mate that
//    has stopped. Each step goes straight on to the next tile of its route, so a unit walks at its own
//    speed rather than the order tick's; those that set off together march at the slowest one's pace,
//    unless a unit is set to its own pace (band card Orders tab, unit card Combat tab).
//  - A unit whose slot is taken or shut in takes the nearest free tile it can reach (twice at most).
//  - Attack-move and Shift-queued moves keep the shape (a queued leg starts from the last one's slots).
//  - A compact group crossing open ground plans one route and the others follow it side by side; other
//    route searches are spread over ticks for big groups.
// The page draws a marker on every slot at the click and fades each as its unit arrives (rmSlots3D).

#define RM_GROUP_TOGETHER 10   // tiles from the group's middle: who sets off together and keeps its pace
#define RM_MATE_WAIT 15        // ticks a unit waits for a group-mate that has stopped in its way
#define RM_GROUP_PATHS 16      // route searches for group moves in one tick; the rest step straight and plan next tick
#define RM_ORDER_STEP 5        // ticks a step at least on a move order or attack-move: the old 2 tiles a second (the user, 12:3x)

var/rm_group_serial = 0
var/rm_group_paths_at = -1
var/rm_group_paths = 0
var/list/rm_path_pass          // atoms a route search goes through (RemasterWalkable): a group's walking members

datum/remaster_group
	var/id
	var/kind = "Move"            // or "Attack-move"
	var/turf/target
	var/shape
	var/fx = 0                   // the direction of travel
	var/fy = 1
	var/list/members = list()
	var/list/slots = list()      // unit -> turf
	var/list/start = list()      // unit -> where it stood (or will stand) when the order was given
	var/list/together = list()   // unit -> 1: set off with the group, marches at its pace
	var/pace = 0
	var/pace_at = -1
	var/translate = 0            // a compact "keep" group: the same move for everyone, one route for all
	var/forming = 1              // orders still being given (RemasterOrder's loop): every member counts as walking
	var/queued = 0               // a Shift-queued leg (the page keeps the earlier leg's markers)
	var/mob/Monsters/lead
	var/list/lead_path
	var/lead_partial = 0

datum/remaster_group/New()
	id = ++rm_group_serial

datum/remaster_order/var/datum/remaster_group/group
datum/remaster_order/var/wait_since = 0         // waiting for a group-mate in the way since then
datum/remaster_order/var/mob/Monsters/wait_mate // that mate
datum/remaster_order/var/reslots = 0            // times it took another slot
datum/remaster_order/var/followed = 0           // tried the group's shared route
datum/remaster_attack/var/datum/remaster_group/group
mob/Monsters/var/remaster_own_pace = 0          // the player's switch: never slows to the group's pace
mob/Monsters/var/tmp/remaster_mate_wait = -1000 // world.time it last walked into a group-mate on its next tile
Player/var/tmp/datum/remaster_group/remaster_forming

// --- Who is walking with whom --------------------------------------------------------

// The group whose move this unit is on now (an attack-move only while marching, not fighting).
mob/Monsters/proc/RemasterGroupNow()
	if(remaster_active && remaster_active.kind == "Move") return remaster_active.group
	if(remaster_attack && !remaster_attack.target) return remaster_attack.group
	return null

// On its way, or about to set off: its move with this group still waiting for its first step (RmFirstTick) counts too,
// so the mates behind it don't find it in their way and give up until the next order tick (formations 10-24: 155 of a
// 200-unit block took 3+ ticks to step, 45 of them waiting for the order tick).
datum/remaster_group/proc/Walking(mob/Monsters/M)
	if(!istype(M) || !M.loc || M.HP <= 0 || M.loc == slots[M]) return 0
	return forming || M.RemasterGroupNow() == src || (M.remaster_orders && RemasterGroupQueued(M, src))

// Group-mates still on their way, to go through in a route search: atom -> 1. Made once a tick for the whole group and
// shared: made for every unit that asked, it was 633 us a call for 200, half of their first order ticks (formations,
// 10-24). `me` is in it too, which changes nothing: a route search never counts the mover in its own way (Orders.dm
// RemasterWalkable, RmWalk.cs). Callers only read it; it's made again when the members change (RemasterGroupFinish).
datum/remaster_group/var/tmp/pass_at = -1
datum/remaster_group/var/tmp/list/pass_all
datum/remaster_group/proc/Pass(mob/Monsters/me)
	if(pass_at != world.time || !pass_all)
		pass_at = world.time
		pass_all = list()
		for(var/mob/Monsters/M in members) if(Walking(M)) pass_all[M] = 1
	return pass_all

proc/RemasterWalkingMateOn(turf/T, datum/remaster_group/G, mob/Monsters/me)
	if(!G || !T) return null
	for(var/mob/Monsters/M in T) if(M != me && (M in G.members) && G.Walking(M)) return M
	return null

// --- Pace ----------------------------------------------------------------------------

// Ticks between this unit's own steps: as RemasterStepDelay (Specials.dm), without its look-again rule. On a move
// order or attack-move, never faster than RM_ORDER_STEP off a road: the pace orders always had (they stepped on the
// 0.5 s order tick), so a Delay 3 or 4 unit walks 2 tiles a second, as before; a road still speeds it up.
mob/Monsters/proc/RemasterOwnStep()
	var/d = Delay
	if(Flying && Race == "Dragon") d = max(1, round(d / 2))
	if(RemasterChained()) d = max(d, RM_ORDER_STEP)
	// faster along a road, as RemasterRoadDelay (Roads.dm) without its carried fraction: this is asked for every
	// member each tick, and the walk loop's own call keeps the carry
	var/turf/T = loc
	if(isturf(T) && T.remaster_road && !Flying && T.remaster_road != "rail") d = max(1, round(d * (T.remaster_road == "stone" ? REMASTER_ROAD_STONE : REMASTER_ROAD_DIRT) + 0.5))
	if(rm_swim_on && RmSwimWater(T)) d = RmSwimDelay(d)   // in deep water: its race's pace (Swim.dm)
	if(remaster_slow_until > world.time) d *= 2
	return max(1, d)

// The group it marches with, keeping its pace: set off together, not on its own pace, still on its way.
mob/Monsters/proc/RemasterMarchGroup()
	if(remaster_own_pace) return null
	var/datum/remaster_group/G = RemasterGroupNow()
	if(!G || !G.together[src] || loc == G.slots[src]) return null
	return G

datum/remaster_group/proc/Pace()
	if(pace_at == world.time) return pace
	pace_at = world.time
	pace = 0
	for(var/mob/Monsters/M in members)
		if(!M.loc || M.HP <= 0 || !M.CanWalk || M.RemasterMarchGroup() != src) continue
		pace = max(pace, M.RemasterOwnStep())
	return pace

// mob/Monsters/RemasterStepDelay: this file's part is step RmChainStepDelay_Formations in Code/Remastered/Chains/StepDelay.dm

// mob/Monsters/Bump: this file's part is step RmChainBump_Formations in Code/Remastered/Chains/Bump.dm

// On a player's move order or a marching attack-move: the orders that step straight on along their route.
mob/Monsters/proc/RemasterChained()
	if(remaster_active) return remaster_active.kind == "Move" && !remaster_active.automatic && !remaster_defense
	return remaster_attack && !remaster_attack.target && remaster_attack.goal

// After each step of a route: straight on to its next tile, rather than waiting for the order tick (Orders.dm Move).
// A job's own task (automatic) and a delivery go on too (the owner's call A, 10-27), at an ordered move's pace and never
// faster (RmJobRouteStep, below): they took one tile per orders pass, so the bigger the village the slower everyone walked
// (2,000 workers: 0.5-0.75 tiles a second instead of 2). The orders pass still does all their work and any new route.
// Only the walk loop's own step onto the route's next tile (its destination there) goes on: never a care walk's, a
// side-step's or another walk's that happens to cross the route, and none while it looks after itself, waits, defends
// or fights.
mob/Monsters/proc/RemasterChainStep()
	var/list/path
	var/datum/remaster_group/G
	var/turf/goal
	if(remaster_active && remaster_active.kind == "Move" && !remaster_active.automatic && !remaster_defense)
		path = remaster_active.path
		G = remaster_active.group
		goal = remaster_active.target
	else if(remaster_attack && !remaster_attack.target && remaster_attack.goal)
		path = remaster_attack.path
		G = remaster_attack.group
		goal = remaster_attack.goal
	else if(destination == loc && !remaster_attack && !remaster_defense && !remaster_care && !remaster_paused && !remaster_wait_for_resume)
		var/datum/remaster_order/O = remaster_delivery || remaster_active   // the orders tick walks the delivery first
		if(O && (O == remaster_delivery || O.automatic) && !O.group)
			path = O.path
			// its route's end for StepOpen's goal: a route never holds its goal before its end (stairs only as the goal),
			// so the rules read as for the order's own goal
			if(length(path)) goal = path[length(path)]
	if(!length(path) || path[1] != loc) return
	path.Cut(1, 2)
	if(!length(path)) return
	var/turf/N = path[1]
	if(N.z != z || get_dist(src, N) != 1) return
	if(RemasterStepOpen(path, src, goal) || RemasterWalkingMateOn(N, G, src)) destination = N   // through units of its side (Clip.dm)

// A job's own task's or a delivery's walk along its route (its next tile, as RemasterChainStep set it): never faster than
// RM_ORDER_STEP off a road, as RemasterOwnStep keeps the player's own moves (the owner, 10-27: "We don't want them to move
// faster, right?"). A road still speeds it up, after this (Chains/StepDelay.dm, Roads.dm RemasterRoadDelay). d: its step.
mob/Monsters/proc/RmJobRouteStep(d)
	if(remaster_attack || remaster_defense || remaster_care || remaster_paused || remaster_wait_for_resume || !isturf(destination)) return d
	var/datum/remaster_order/O = remaster_delivery || remaster_active
	if(!O || (O != remaster_delivery && !O.automatic) || O.group || !length(O.path) || O.path[1] != destination) return d
	return max(d, RM_ORDER_STEP)

// --- Shapes ---------------------------------------------------------------------------

// A direction snapped to the grid: one of the eight, or with four = 1 one of the four straight ones.
proc/RemasterSnapDir(fx, fy, four = 0)
	var/ax = abs(fx)
	var/ay = abs(fy)
	if(four) return ax >= ay ? list(fx >= 0 ? 1 : -1, 0) : list(0, fy >= 0 ? 1 : -1)
	if(ax > ay * 2.414) return list(fx >= 0 ? 1 : -1, 0)
	if(ay > ax * 2.414) return list(0, fy >= 0 ? 1 : -1)
	return list(fx >= 0 ? 1 : -1, fy >= 0 ? 1 : -1)

// How many abreast a shape's rows are for n units.
proc/RemasterShapePer(shape, n, width = 0)
	switch(shape)
		if("line")
			var/rows = round((n + 11) / 12)
			. = round((n + rows - 1) / rows)
		if("column") . = n <= 8 ? 1 : (n <= 24 ? 2 : 3)
		else . = max(1, round(sqrt(n) + 0.999))
	if(width > 0 && shape != "column") . = clamp(round(width), 1, n)    // a drag set the front row's width

// n slot points round (tx, ty) for a shape, front row first, each row right to left: list(list(x, y), ...).
// The front row of a line is on the target, a column's head is on it, a box is centred on it.
proc/RemasterShapePoints(shape, n, tx, ty, fx, fy, width = 0)
	var/list/F = RemasterSnapDir(fx, fy, shape == "box")
	var/sx = F[1]
	var/sy = F[2]
	var/ax = -sy       // across, to the left of the way they face
	var/ay = sx
	var/per = RemasterShapePer(shape, n, width)
	var/rows_all = round((n + per - 1) / per)
	var/list/P = list()
	for(var/i = 0, i < n, i++)
		var/r = round(i / per)
		var/c = i % per
		var/count = r == rows_all - 1 ? n - r * per : per
		var/off = c - round((count - 1) / 2)
		var/back = shape == "box" ? r - round((rows_all - 1) / 2) : r
		P += list(list(tx + ax * off - sx * back, ty + ay * off - sy * back))
	return P

// The player's own formations (Army, Formations): up to RM_FORMATIONS_MAX, each a name and its squares "dx,dy,role"
// (the clicked tile at 0,0, forward up, +dy; role front, ranged, mage or any). The "custom" formation is the one picked
// (remaster_formation_mine). In a move each unit takes a square of its role, by what it holds now
// (RemasterFormationRole): fighters to front squares, archers to ranged ones, casters to mage ones; anyone else, and
// any left over when a role's squares run out, to the rest, "any" squares first. Of each role's squares, those nearest
// the clicked tile are used first; more units than squares stand in rows behind. The clicked tile always has someone
// on it: left empty in the layout, the square nearest it goes there. Turned a quarter at a time to face the way they go,
// so the layout stays exact.
Player/var/list/remaster_formations = list()
Player/var/remaster_formation_mine = 1
#define RM_FORMATIONS_MAX 4
#define RM_GRID_MAX 60
#define RM_GRID_REACH 6
var/list/rm_formation_roles = list("front", "ranged", "mage", "any")

// The squares formation i has ("dx,dy,role"), or null; by default the one picked.
Player/proc/RemasterMyFormation(i = remaster_formation_mine)
	if(i < 1 || i > length(remaster_formations)) return null
	var/list/F = remaster_formations[i]
	return (islist(F) && length(F["cells"])) ? F["cells"] : null

// Its place in a formation with roles, and its kind for Attack-clicks, by what it holds now: the weapon decides first
// (the user: "enchant melee weapons are still melee weapons"), so an enchanted blade is still a fighter's and an
// enchanted bow an archer's; with neither, a caster (its own gift, or a staff or wand with mana) is a mage. A staff is
// a caster's though the game strikes with it as a mace (GearData.dm).
mob/Monsters/proc/RemasterFormationRole()
	var/c = RemasterWeaponClass(src)
	if(c == "bow") return "ranged"
	if(RmMoveClass(src) == "staff") return "mage"     // WeaponSkills.dm
	if(c in list("sword", "axe", "mace", "spear", "dagger", "claws")) return "front"
	var/obj/Items/W = RmHeldWeapon(src)
	if(MagicalAptitude || (W && RmManaMax(W))) return "mage"    // WeaponSkills.dm
	return "any"

// L in order of K1 (then K2), smallest first, equal keys kept in the order they came: a merge sort, n log n. The
// selection sorts it replaces were n squared: one order for 203 units took 210-376 ms in a tick (server-cost, 10-24).
// Keys are parallel lists (DM numbers are 32-bit: two keys, not one made of both). In place; returns L. The page's
// copy is fmSortBy (tools/formations/fm_module.js).
proc/RmSortBy(list/L, list/K1, list/K2 = null)
	if(length(L) < 2) return L
	if(rm_native_slots && rm_sort_by(L, K1, K2) == 1) return L   // the engine's (RmSlots.cs), the same order
	return RmSortByDM(L, K1, K2)

proc/RmSortByDM(list/L, list/K1, list/K2 = null)
	var/n = length(L)
	if(n < 2) return L
	var/list/idx = new /list(n)
	for(var/i = 1, i <= n, i++) idx[i] = i
	var/list/tmp = new /list(n)
	for(var/w = 1, w < n, w *= 2)
		for(var/lo = 1, lo <= n - w, lo += 2 * w)
			var/mid = lo + w - 1
			var/hi = min(lo + 2 * w - 1, n)
			var/i = lo
			var/j = mid + 1
			var/k = lo
			while(i <= mid && j <= hi)
				var/a = idx[i]
				var/b = idx[j]
				if(K1[b] < K1[a] || (K2 && K1[b] == K1[a] && K2[b] < K2[a]))
					tmp[k] = b
					j++
				else
					tmp[k] = a
					i++
				k++
			while(i <= mid)
				tmp[k] = idx[i]
				i++
				k++
			while(j <= hi)
				tmp[k] = idx[j]
				j++
				k++
			for(k = lo, k <= hi, k++) idx[k] = tmp[k]
	var/list/was = L.Copy()
	for(var/i = 1, i <= n, i++) L[i] = was[idx[i]]
	return L

proc/RemasterCellKey(list/C)    // nearest the clicked tile first, then the front, then the middle
	return max(abs(C[1]), abs(C[2])) * 1000 + (C[1] ** 2 + C[2] ** 2) * 10 - C[2]

// n slot points for a formation's squares round (tx, ty) for units of these roles (role -> count):
// list(list(x, y, role), ...), front row first, each row right to left.
proc/RemasterCustomPoints(list/grid, list/counts, n, tx, ty, fx, fy)
	var/list/pool = list()
	for(var/c in grid)
		var/list/v = splittext("[c]", ",")
		if(length(v) >= 2) pool += list(list(text2num(v[1]), text2num(v[2]), length(v) >= 3 && (v[3] in rm_formation_roles) ? v[3] : "any"))
	if(!length(pool)) return list()
	var/list/pk = list()
	for(var/list/C in pool) pk += RemasterCellKey(C)
	RmSortBy(pool, pk)
	// each role's own squares for its units, then the rest ("any" first) for whoever is left
	var/list/cells = list()
	for(var/r in list("mage", "ranged", "front"))
		var/want = counts && counts[r] ? counts[r] : 0
		for(var/list/C in pool.Copy())
			if(want <= 0 || length(cells) >= n) break
			if(C[3] != r) continue
			cells += list(C)
			pool -= list(C)
			want--
	for(var/pass = 1, pass <= 2, pass++)
		for(var/list/C in pool.Copy())
			if(length(cells) >= n) break
			if(pass == 1 && C[3] != "any") continue
			cells += list(C)
			pool -= list(C)
	// someone on the clicked tile: shift the squares so the one nearest it is there
	var/list/near
	for(var/list/C in cells) if(!near || RemasterCellKey(C) < RemasterCellKey(near)) near = C
	if(near && (near[1] || near[2]))
		var/ox = near[1]
		var/oy = near[2]
		for(var/list/C in cells)
			C[1] -= ox
			C[2] -= oy
	// more units than squares: rows behind, as wide as the layout
	var/x0 = 1#INF
	var/x1 = -1#INF
	var/y0 = 1#INF
	for(var/list/C in cells)
		x0 = min(x0, C[1])
		x1 = max(x1, C[1])
		y0 = min(y0, C[2])
	var/w = max(1, x1 - x0 + 1)
	for(var/k = 0, length(cells) < n, k++) cells += list(list(x0 + k % w, y0 - 1 - round(k / w), "any"))
	var/list/k1 = list()                 // front row first, each row right to left
	var/list/k2 = list()
	for(var/list/C in cells)
		k1 += -C[2]
		k2 += -C[1]
	RmSortBy(cells, k1, k2)
	var/list/F = RemasterSnapDir(fx, fy, 1)
	var/rx = F[2]       // to the right of the way they face
	var/ry = -F[1]
	var/list/P = list()
	for(var/list/C in cells) P += list(list(tx + C[1] * rx + C[2] * F[1], ty + C[1] * ry + C[2] * F[2], C[3]))
	return P

// Front first (along the facing), then right to left: L sorted in place; pos[item] = list(x, y).
proc/RemasterGeoOrder(list/L, list/pos, ox, oy, fx, fy)
	var/list/k1 = list()
	var/list/k2 = list()
	for(var/q in L)
		var/list/P = pos[q]
		k1 += -round((P[1] - ox) * fx + (P[2] - oy) * fy + 0.5)
		k2 += (P[1] - ox) * -fy + (P[2] - oy) * fx
	return RmSortBy(L, k1, k2)

// HUD commands (Army, Formations): "formationsave" "i|name|dx,dy,role/..." (i = how many there are + 1 adds one;
// squares split by "/": a HUD command's value can't hold ";", which BYOND's params split on, as on "&"),
// "formationuse" "i" (and the formation becomes "custom"), "formationdel" "i".
Player/proc/RemasterFormationCommand(action, value)
	var/list/p = splittext("[value]", "|")
	var/i = text2num(length(p) ? p[1] : null)
	if(isnull(i) || i != round(i) || i < 1) return 0
	switch(action)
		if("formationsave")
			if(i > min(length(remaster_formations) + 1, RM_FORMATIONS_MAX)) return 0
			var/name = length(p) >= 2 ? copytext(trimtext(replacetext(replacetext(replacetext(replacetext(replacetext(replacetext(p[2], "<", ""), ">", ""), ";", ""), "/", ""), "&", ""), "=", "")), 1, 25) : ""
			if(!length(name)) name = "Formation [i]"
			var/list/out = list()
			var/list/seen = list()
			for(var/c in splittext(replacetext(length(p) >= 3 ? p[3] : "", ";", "/"), "/"))
				var/list/v = splittext(c, ",")
				if(length(v) < 2) continue
				var/X = text2num(v[1])
				var/Y = text2num(v[2])
				if(isnull(X) || isnull(Y) || X != round(X) || Y != round(Y) || abs(X) > RM_GRID_REACH || abs(Y) > RM_GRID_REACH) continue
				var/role = length(v) >= 3 && (v[3] in rm_formation_roles) ? v[3] : "any"
				if(seen["[X],[Y]"]) continue
				seen["[X],[Y]"] = 1
				out += "[X],[Y],[role]"
				if(length(out) >= RM_GRID_MAX) break
			var/list/F = list("name"=name, "cells"=out)
			if(i > length(remaster_formations)) remaster_formations += list(F)
			else remaster_formations[i] = F
			return 1
		if("formationuse")
			if(i > length(remaster_formations)) return 0
			return RemasterFormationPick("custom", i)
		if("formationdel")
			if(i > length(remaster_formations)) return 0
			remaster_formations.Cut(i, i + 1)
			if(remaster_formation_mine > i || remaster_formation_mine > length(remaster_formations)) remaster_formation_mine = max(1, remaster_formation_mine - 1)
			// groups that used it go back to keeping their shape; the ones after it move down one
			for(var/k in remaster_group_formations)
				var/list/GF = remaster_group_formations[k]
				if(!islist(GF) || GF[1] != "custom") continue
				if(GF[2] == i) remaster_group_formations[k] = list("keep", 1)
				else if(GF[2] > i) remaster_group_formations[k] = list("custom", GF[2] - 1)
			return 1
	return 0

Player/RemasterHUDData()
	. = ..()
	if(!islist(.)) return
	var/list/L = list()
	for(var/list/F in remaster_formations)
		var/list/C = list()
		for(var/c in F["cells"])
			var/list/v = splittext("[c]", ",")
			if(length(v) >= 3) C += list(list(text2num(v[1]), text2num(v[2]), v[3]))
		L += list(list("name"=F["name"], "cells"=C))
	// the selection's formation: its control group's own, or the player's (the band card and Army show and set that one)
	var/list/now = RemasterFormationNow()
	// the selection's supplies and health on the left (the user, 10-24: "if we have a group highlighted we should have a
	// card on the left similar to group cards where we can see the shared resources maybe health"): two or more of yours
	var/list/SS = list()
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0 && !M.GoingToDie) SS += M
	if(length(SS) >= 2)
		var/list/SU = RemasterSuppliesCached("sel", SS)
		.["selSupply"] = list("supply"=SU[1], "bag"=SU[2], "group"=now[3])
	.["formations"] = L
	.["formation"] = now[1]
	.["formationMine"] = now[2]
	.["formationGroup"] = now[3]
	// the one in use, for hud-craft's "Your own" card and the band card's Mine button: [[dx, dy, role], ...]
	.["formationGrid"] = (now[2] >= 1 && now[2] <= length(L)) ? L[now[2]]["cells"] : list()

// Is the group close together (its own shape is kept) or spread out (it forms a block)?
proc/RemasterGroupCompact(list/anchors)
	var/n = length(anchors)
	if(n < 2) return 1
	var/x0 = 1#INF
	var/x1 = -1#INF
	var/y0 = 1#INF
	var/y1 = -1#INF
	for(var/k in anchors)
		var/list/a = anchors[k]
		x0 = min(x0, a[1])
		x1 = max(x1, a[1])
		y0 = min(y0, a[2])
		y1 = max(y1, a[2])
	var/w = x1 - x0 + 1
	var/h = y1 - y0 + 1
	var/limit = max(2, round(sqrt(n)) + 1)
	return max(w, h) <= 2 * limit + 1 && w * h <= 3 * n + 3

// Where a unit will stand when its earlier orders are done: the last queued spot, else where it is.
mob/Monsters/proc/RemasterPlannedSpot()
	var/turf/T
	if(remaster_active && isturf(remaster_active.target)) T = remaster_active.target
	if(remaster_orders) for(var/datum/remaster_order/O in remaster_orders) if(isturf(O.target)) T = O.target
	return T || loc

// --- Slots -----------------------------------------------------------------------------

// Timing runs only (tools/formations/repro_order.dm): with fm_prof on, FmProf("label") adds the time since the last mark
// (world.tick_usage: a share of the tick, in ms here) to that label. Off, it costs one check.
var/fm_prof = 0
var/list/fm_prof_ms = list()
var/fm_prof_at = 0
proc/FmProf(label)
	if(!fm_prof) return
	var/now = world.tick_usage * world.tick_lag      // tick_usage is a percent of tick_lag (ds): x tick_lag / 100 ds = ms
	if(label) fm_prof_ms[label] = (fm_prof_ms[label] || 0) + max(0, now - fm_prof_at)
	fm_prof_at = now

// The group for a move of the selected units to T (Orders.dm RemasterFormation, RemasterLevelSlots, Attack.dm):
// unit -> slot, for everyone that can stand near T. queued: they set off from their last queued spots.
Player/proc/RemasterGroupForm(turf/T, queued = 0, kind = "Move")
	if(!T) return null
	FmProf(null)
	var/list/group = rm_native_plan ? rm_plan_group(Selected, src, UnitList, /mob/Monsters, /mob/Monsters/RemasterSiege) : null   // the engine's (Native.dm), the same
	if(!islist(group) || rm_plan_verify)
		var/list/GD = list()
		for(var/mob/Monsters/M in Selected)
			if(M.Owner == src && (M in UnitList) && !M.Wagon && M.HP > 0 && !M.GoingToDie && !RemasterIsSiege(M)) GD += M
		if(islist(group)) RmPlanCheck("the group", group, GD)
		group = GD
	if(length(group) < 2) return null
	var/datum/remaster_group/G = new
	G.kind = kind
	G.target = T
	var/list/now = RemasterFormationNow()     // a control group's own formation, or the player's
	G.shape = now[1]
	var/mine_i = now[2]
	G.queued = !!queued
	// Where each sets off from: here, its last queued spot, or (another level) the top of the stairs it will take.
	var/list/anchors = list()
	var/list/climb_from = list()
	// the engine takes the units standing on T's level (Native.dm), in order, and hands back one on another level for
	// the stairs below; DM's loop is the fallback and the reference (shadow mode: the engine into its own lists)
	var/list/AN
	var/list/SN
	var/an_done = 0
	if(rm_native_plan && !queued && rm_plan_verify)
		AN = list()
		SN = list()
		an_done = rm_plan_anchors(group, 1, T.z, AN, SN) == length(group) + 1
	var/gk = 1
	while(gk <= length(group))
		if(rm_native_plan && !queued && !rm_plan_verify)
			var/nk = rm_plan_anchors(group, gk, T.z, anchors, G.start)
			if(!isnum(nk)) nk = gk
			gk = nk
			if(gk > length(group)) break
		var/mob/Monsters/M = group[gk]
		gk++
		if(!istype(M)) continue
		var/turf/S = queued ? M.RemasterPlannedSpot() : M.loc
		if(!isturf(S)) S = M.loc
		if(!isturf(S)) continue
		if(S.z != T.z)
			var/turf/stairs = RemasterStairsTowards(M, T)
			var/turf/land = stairs ? locate(stairs.x, stairs.y, T.z) : null
			if(!land && !RemasterCanClimb(M)) continue
			climb_from[M] = stairs || S
			S = land || locate(S.x, S.y, T.z) || S
		anchors[M] = list(S.x, S.y)
		G.start[M] = S
	if(an_done)
		RmPlanCheck("anchors", AN, anchors)
		RmPlanCheck("starts", SN, G.start)
	var/n = length(anchors)
	if(n < 2) return null
	FmProf("1 anchors")
	var/cx = 0
	var/cy = 0
	for(var/mob/Monsters/M in anchors)
		var/list/a = anchors[M]
		cx += a[1]
		cy += a[2]
	cx /= n
	cy /= n
	// The direction of travel: from the group's middle to the target; for a short shuffle on the spot, the way it went last.
	var/fx = T.x - cx
	var/fy = T.y - cy
	var/fl = sqrt(fx * fx + fy * fy)
	if(fl < 1.5)
		fx = 0
		fy = 1
	else
		fx /= fl
		fy /= fl
	var/shape = G.shape
	// A drag to face (formmove): the way they face, and how wide the front row is, from the drag.
	var/width = 0
	if(remaster_face && (remaster_face[1] || remaster_face[2]))
		var/l = sqrt(remaster_face[1] ** 2 + remaster_face[2] ** 2)
		fx = remaster_face[1] / l
		fy = remaster_face[2] / l
		width = remaster_face[3]
		if(!(shape in list("line", "column", "box", "custom"))) shape = width >= n ? "line" : "box"
	G.fx = fx
	G.fy = fy
	if(!(shape in list("line", "column", "box", "custom"))) shape = RemasterGroupCompact(anchors) ? "keep" : "box"
	// Ideal points: for "keep" each unit's own place moved over whole tiles (the shape exactly as it was).
	var/list/points = list()       // list(x, y, unit or null)
	var/list/mine = shape == "custom" ? RemasterMyFormation(mine_i) : null
	if(shape == "custom" && !mine) shape = RemasterGroupCompact(anchors) ? "keep" : "box"   // nothing laid out yet
	var/list/role_of = list()       // a formation with roles: unit -> its role now
	if(shape == "custom")
		var/list/counts = list()
		for(var/mob/Monsters/M in anchors)
			role_of[M] = M.RemasterFormationRole()
			counts[role_of[M]] = (counts[role_of[M]] || 0) + 1
		for(var/list/p in RemasterCustomPoints(mine, counts, n, T.x, T.y, fx, fy)) points += list(list(p[1], p[2], p[3]))
	else if(shape == "keep")
		// anchored on the click: the one nearest the group's middle stands on the clicked tile, the rest round it as they were
		// (ties: the one further north, then west, the same choice as the page's fmPredict)
		var/list/mid
		var/mid_d = 1#INF
		for(var/mob/Monsters/M in anchors)
			var/list/a = anchors[M]
			var/d = ((a[1] - cx) ** 2 + (a[2] - cy) ** 2) * 10000 - a[2] * 100 + a[1]
			if(d < mid_d)
				mid = a
				mid_d = d
		var/vx = T.x - mid[1]
		var/vy = T.y - mid[2]
		for(var/mob/Monsters/M in anchors)
			var/list/a = anchors[M]
			points += list(list(a[1] + vx, a[2] + vy, M))
	else
		var/list/NP
		if(rm_native_plan)   // the engine's loop (Native.dm), the same points; DM's below is the fallback and the reference
			var/list/SF0 = RemasterSnapDir(fx, fy, shape == "box")
			NP = rm_shape_points(n, T.x, T.y, SF0[1], SF0[2], RemasterShapePer(shape, n, width), shape == "box")
		if(islist(NP) && !rm_plan_verify) points = NP
		else
			for(var/list/p in RemasterShapePoints(shape, n, T.x, T.y, fx, fy, width)) points += list(list(p[1], p[2], null))
			if(islist(NP)) RmPlanCheck("shape points", NP, points)
	FmProf("2 points")
	// Open tiles round the target that the group can get to from its side: a flood from the open tile at (or
	// nearest) the target, through the group's own units.
	var/mob/Monsters/lead_unit = group[1]
	for(var/mob/Monsters/M in group) if(!M.Flying)    // the ground's rules (a flyer goes over water)
		lead_unit = M
		break
	var/ext = 0
	for(var/list/p in points) ext = max(ext, abs(p[1] - T.x), abs(p[2] - T.y))
	var/R = min(14, ext + 4)
	var/list/pass = list()
	for(var/mob/Monsters/M in group) pass[M] = 1
	rm_path_pass = pass
	// On a mountain top the block heights count (Gather.dm RemasterStepHeights: up only by a ramp, down a block at most),
	// unless all of the group can climb (Mountains.dm RemasterCanClimb). The slots go where the group can get to from
	// where it comes up (the top of the stairs, or where it stands), the clicked tile if it can, else the nearest it can
	// (coordinator, 10-24: they "got as close as they could" below a higher middle).
	var/heights = 0
	if(T.z == SKY_LAYER) for(var/mob/Monsters/M in group) if(!RemasterCanClimb(M)) heights = 1
	var/list/ureach = heights ? RemasterHeightReach(G.start, T, R, lead_unit) : null
	var/turf/seed
	if(RemasterTilePlaces(T, group) && RemasterWalkable(T, lead_unit, T) && (!ureach || ureach[T])) seed = T
	else
		var/best_d = 1#INF
		for(var/turf/C in range(R, T))
			if(ureach && !ureach[C]) continue
			if(!RemasterTilePlaces(C, group) || !RemasterWalkable(C, lead_unit, C)) continue
			var/d = get_dist(C, T) * 100 + abs(C.x - cx) + abs(C.y - cy)
			if(d < best_d)
				seed = C
				best_d = d
	// the open tiles round the target the group can get to, and their free places: the engine's when it has it
	// (RmSlots.cs, the same as RemasterSlotReachDM's), the DM flood up on a mountain top (the heights are DM's)
	var/list/RP
	// (all flyers on the Sky level: DM's, where open sky holds them, Orders.dm RemasterTilePlaces; RmSlots.cs doesn't yet)
	if(seed && !heights && rm_native_slots && !(T.z == SKY_LAYER && RmAllFly(group))) RP = rm_slot_reach(T, R, seed, lead_unit, group, pass, 'Stairs.dmi', /obj/RmBeastFoot, /mob/Monsters, GROUND_LAYER, SKY_LAYER, RmSide(lead_unit), /mob/Monsters/RemasterSiege)
	if(!(islist(RP) && length(RP) == 2)) RP = RemasterSlotReachDM(T, R, seed, lead_unit, group, heights)
	rm_path_pass = null
	var/list/reach = RP[1]         // tile -> 1
	var/list/places = RP[2]        // tile -> free places (two on a wall-walk)
	FmProf("3 flood")
	if(!length(places)) return null
	FmProf("4 places")
	// Up against water or a wall: slide the shape back towards the group until it fits.
	var/list/back = RemasterSnapDir(fx, fy)
	var/sx = 0
	var/sy = 0
	var/best_fit = -1
	for(var/k = 0, k <= 3, k++)
		var/fit = 0
		for(var/list/p in points)
			var/turf/C = locate(p[1] - back[1] * k, p[2] - back[2] * k, T.z)
			if(C && places[C]) fit++
		if(fit > best_fit)
			best_fit = fit
			sx = -back[1] * k
			sy = -back[2] * k
		if(fit >= n) break
	// Each point takes the free tile nearest it, the points nearest the middle first.
	var/mx = T.x + sx
	var/my = T.y + sy
	var/list/ordered
	var/list/ok
	var/list/PO = rm_native_plan ? rm_points_order(points, sx, sy, mx, my) : null   // the engine's order and keys (Native.dm), the same
	if(islist(PO) && length(PO) == 2 && !rm_plan_verify)
		ordered = PO[1]
		ok = PO[2]
	else
		ordered = points.Copy()
		ok = list()
		for(var/list/p in ordered) ok += max(abs(p[1] + sx - mx), abs(p[2] + sy - my))
		RmSortBy(ordered, ok)
		if(islist(PO) && length(PO) == 2)
			RmPlanCheck("middle-first order", PO[1], ordered)
			RmPlanCheck("middle-first keys", PO[2], ok)
	// each point the free tile nearest it: the engine's when it has it (RmSlots.cs), the same as RemasterSlotTilesDM
	var/list/TO = rm_native_slots ? rm_slot_tiles(ordered, sx, sy, mx, my, T.z, places) : null
	if(!(islist(TO) && length(TO) == 2)) TO = RemasterSlotTilesDM(ordered, sx, sy, mx, my, T.z, places)
	var/list/tiles = TO[1]        // the slot tiles, in points order
	var/list/owner = TO[2]        // "keep": the unit each tile was the place of
	FmProf("5 tiles")
	// Who goes where: "keep" units to their own places; a shape front units to the front row, right to left.
	var/list/units = list()
	for(var/mob/Monsters/M in anchors) units += M
	var/list/assign = list()      // unit -> turf
	var/list/key_of = list()      // unit -> its role's squares (a formation with roles): swaps stay within them
	if(shape == "keep")
		for(var/i = 1, i <= length(tiles), i++) if(owner[i]) assign[owner[i]] = tiles[i]
	else if(shape == "custom")
		// each role's units to its squares, front units to the front ones; then whoever is left to the rest
		var/list/pos = list()
		for(var/mob/Monsters/M in units) pos[M] = anchors[M]
		var/list/free_t = list()
		for(var/i = 1, i <= length(tiles), i++)
			var/turf/TT = tiles[i]
			pos["[i]"] = list(TT.x, TT.y)
			free_t += "[i]"
		var/list/left = units.Copy()
		for(var/r in list("mage", "ranged", "front", "fill"))
			var/list/U = list()
			for(var/mob/Monsters/M in left) if(r == "fill" || role_of[M] == r) U += M
			var/list/I = list()
			for(var/k in free_t) if(r == "fill" ? owner[text2num(k)] == "any" : owner[text2num(k)] == r) I += k
			if(r == "fill") for(var/k in free_t) if(!(k in I)) I += k     // "any" squares first, then any other left
			RemasterGeoOrder(U, pos, cx, cy, fx, fy)
			if(r != "fill") RemasterGeoOrder(I, pos, mx, my, fx, fy)
			for(var/q = 1, q <= length(U) && q <= length(I), q++)
				assign[U[q]] = tiles[text2num(I[q])]
				key_of[U[q]] = r
				left -= U[q]
				free_t -= I[q]
	else
		// the engine's hand-out (Native.dm), the same assign; DM's below is the fallback and the reference
		var/list/NA
		if(rm_native_plan)
			var/list/SFn = RemasterSnapDir(fx, fy, shape == "box")
			NA = rm_box_handout(units, anchors, cx, cy, SFn[1], SFn[2], ok, tiles, mx, my, RemasterShapePer(shape, n, width))
		if(islist(NA) && !rm_plan_verify) assign = NA
		else
			// along the shape's own rows (RemasterShapePoints snaps the facing): units sorted on the travel line itself, a
			// diagonal band of them went into a straight row of slots, their routes crossing (10-24)
			var/list/SF = RemasterSnapDir(fx, fy, shape == "box")
			var/ffx = SF[1]
			var/ffy = SF[2]
			var/ax = -ffy
			var/ay = ffx
			var/list/k1 = list()           // front first, then right to left
			var/list/k2 = list()
			for(var/mob/Monsters/M in units)
				var/list/a = anchors[M]
				k1 += -((a[1] - cx) * ffx + (a[2] - cy) * ffy)
				k2 += (a[1] - cx) * ax + (a[2] - cy) * ay
			RmSortBy(units, k1, k2)
			// tiles are in middle-first order; put them back in shape order (front row first) for the hand-out. Each point's
			// place in that order: its number sorted with the same keys (the sort is stable, so the same order); a Find per
			// point was n squared, 0.8 s of a 30,000-unit move (formations, 10-24)
			var/list/perm = new /list(length(points))
			for(var/j = 1, j <= length(points), j++) perm[j] = j
			RmSortBy(perm, ok)
			var/list/at = new /list(length(points))
			for(var/i = 1, i <= length(perm), i++) at[perm[i]] = i
			var/list/shape_tiles = list()
			for(var/j = 1, j <= length(points), j++)
				var/i = at[j]
				if(i && i <= length(tiles)) shape_tiles += tiles[i]
			// row by row: each row of slots takes the next units, front first, and each of them the slot across from it (right
			// to left): a group of other rows than the shape's (10 abreast into a block of 15) then needs few swaps, where
			// handing out one by one left most of them crossing (2,351 swaps for 200 in six passes, server-cost 10-24)
			var/per = RemasterShapePer(shape, n, width)
			var/m = min(length(units), length(shape_tiles))
			for(var/i0 = 1, i0 <= m, i0 += per)
				var/i1 = min(i0 + per - 1, m)
				var/list/RU = units.Copy(i0, i1 + 1)
				var/list/RT = shape_tiles.Copy(i0, i1 + 1)
				var/list/ku = list()
				var/list/kt = list()
				for(var/mob/Monsters/M in RU)
					var/list/a = anchors[M]
					ku += (a[1] - cx) * ax + (a[2] - cy) * ay
				for(var/turf/TT in RT) kt += (TT.x - mx) * ax + (TT.y - my) * ay
				RmSortBy(RU, ku)
				RmSortBy(RT, kt)
				for(var/q = 1, q <= length(RU), q++) assign[RU[q]] = RT[q]
			if(islist(NA)) RmPlanCheck("hand-out", NA, assign)
	FmProf("6 handout")
	// No two routes cross: swap any pair whose swap makes their two straight routes shorter in all.
	RemasterUncross(assign, anchors, key_of)
	FmProf("7 uncross")
	// Up the stairs one after another: the first up takes the slot furthest from the top of the stairs.
	if(length(climb_from))
		var/list/climbers = list()
		for(var/mob/Monsters/M in climb_from) if(assign[M]) climbers += M
		var/list/ctiles = list()
		for(var/mob/Monsters/M in climbers) ctiles += assign[M]
		for(var/a = 1, a <= length(climbers), a++)
			for(var/b = a + 1, b <= length(climbers), b++)
				if(get_dist(climbers[b], climb_from[climbers[b]]) < get_dist(climbers[a], climb_from[climbers[a]])) climbers.Swap(a, b)
		for(var/a = 1, a <= length(ctiles), a++)
			for(var/b = a + 1, b <= length(ctiles), b++)
				var/turf/CA = ctiles[a]
				var/turf/CB = ctiles[b]
				var/turf/LA = G.start[climbers[1]]
				if(get_dist(CB, LA) > get_dist(CA, LA)) ctiles.Swap(a, b)
		for(var/i = 1, i <= length(climbers), i++) assign[climbers[i]] = ctiles[i]
	// Each unit must be able to stand on its own tile (the undead and holy ground, flyers); else the nearest that it can.
	for(var/mob/Monsters/M in assign)
		var/turf/S = assign[M]
		if(RemasterWalkable(S, M, S)) continue
		var/list/taken = list()
		for(var/mob/Monsters/O in assign) taken[assign[O]] = 1
		var/turf/best
		var/best_d = 1#INF
		for(var/turf/C in reach)
			if(taken[C] || !RemasterTilePlaces(C, group) || !RemasterWalkable(C, M, C)) continue
			var/d = get_dist(C, S) * 10 + get_dist(C, T)
			if(d < best_d)
				best = C
				best_d = d
		if(best) assign[M] = best
		else assign -= M
	FmProf("8 stand")
	G.slots = assign
	for(var/mob/Monsters/M in assign) G.members += M
	G.translate = shape == "keep" && !queued && !length(climb_from) && sx == 0 && sy == 0
	// Who sets off together: those near the group's middle (one far away comes on at its own speed).
	for(var/mob/Monsters/M in assign)
		var/list/a = anchors[M]
		if(max(abs(a[1] - cx), abs(a[2] - cy)) <= RM_GROUP_TOGETHER) G.together[M] = 1
	if(G.translate)
		// One route for all: the one nearest the middle plans it, through the others; each of the others goes the same
		// way from where it stands, side by side (RemasterGroupApproach), unless something is in its own way.
		var/mob/Monsters/L
		for(var/mob/Monsters/M in G.members) if(!L || max(abs(M.x - cx), abs(M.y - cy)) < max(abs(L.x - cx), abs(L.y - cy))) L = M
		rm_path_pass = pass
		G.lead = L
		if(rm_nav_count) rm_path_who = "group: lead's route"
		G.lead_path = RemasterOrderPath(L, assign[L], 0, partial = 1)
		G.lead_partial = rm_path_partial
		if(G.lead_partial && !length(G.lead_path) && rm_route && !RmReachNo(L, assign[L], 0))   // past the search's reach: the group's route map (one for all of them, Native.dm), to near its slot
			var/list/LR = RmRouteMap(L, T, 1, assign[L], 3)
			if(islist(LR) && length(LR))
				G.lead_path = LR
				G.lead_partial = LR[length(LR)] == assign[L] ? 0 : 1
		rm_path_pass = null
	FmProf("9 lead route")
	remaster_forming = G
	return assign

// No two routes cross (RemasterGroupForm): swap any pair whose swap makes their two straight routes shorter in all,
// pass after pass until none does (six at most). Up to RM_SWAP_ALL units, every pair, as it always was; more, each
// with those whose slot is within 2 tiles of its own (a grid of the slots), so 200 units cost 200 x 12 checks a pass,
// not 20,000. Swaps stay within a role's squares (key_of). The page's copy is in fmPredict (fm_module.js).
#define RM_SWAP_ALL 60
// Do A-B and C-D cross (not just touch)?
proc/RmSegCross(ax, ay, bx, by, cx, cy, dx, dy)
	var/d1 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx)
	var/d2 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx)
	var/d3 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
	var/d4 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax)
	return ((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))

var/list/rm_uncross_last = list(0, 0, 0)     // the last one's passes, pair checks and swaps (for timing runs)
var/rm_uncross_ties = 1                      // also swap two crossing routes of the same length (a timing run can turn it off)
var/rm_uncross_big = 0                       // passes for more than RM_SWAP_ALL units: none (see RemasterUncross; a timing run can set some)
proc/RemasterUncross(list/assign, list/anchors, list/key_of)
	// more than RM_SWAP_ALL: none (the user, 10-24: units walk through their own side now, Clip.dm, so a crossing in a big
	// army only shows as two passing; the pass cost 24-77 ms of a 200-unit order, its row-by-row hand-out does without)
	if(length(assign) > RM_SWAP_ALL && !rm_uncross_big)
		rm_uncross_last = list(0, 0, 0)
		return
	// the engine's every-pair passes (Native.dm), the same swaps; DM's below is the fallback and the reference
	var/list/AU
	var/list/UR
	if(rm_native_plan && length(assign) <= RM_SWAP_ALL)
		AU = rm_plan_verify ? assign.Copy() : assign
		UR = rm_uncross_all(AU, anchors, key_of, rm_uncross_ties)
		if(islist(UR) && length(UR) == 3 && !rm_plan_verify)
			if(UR[1]) rm_uncross_last = UR      // two or more: DM's sets it too
			return
	var/checks = 0
	var/swaps = 0
	var/passes = 0
	var/list/who = list()
	for(var/mob/Monsters/M in assign) who += M
	var/n = length(who)
	if(n < 2) return
	var/list/AX = new /list(n)
	var/list/AY = new /list(n)
	var/list/S = new /list(n)            // each one's slot now
	var/list/K = new /list(n)
	for(var/i = 1, i <= n, i++)
		var/list/A = anchors[who[i]]
		AX[i] = A[1]
		AY[i] = A[2]
		S[i] = assign[who[i]]
		K[i] = key_of[who[i]]
	var/list/cell
	if(n > RM_SWAP_ALL)
		cell = list()                     // slot tile -> the ones on it
		for(var/i = 1, i <= n, i++)
			var/turf/T = S[i]
			if(!cell[T]) cell[T] = list()
			cell[T] += i
	// passes that shorten the routes in all until none does (or the cap: rm_uncross_big for a big group), then one that
	// also swaps two crossing routes of the same length (only then: those swaps could undo each other pass after pass)
	var/cap = n > RM_SWAP_ALL ? rm_uncross_big : 6
	var/ties = 0
	for(var/pass_n = 1, pass_n <= cap + 1, pass_n++)
		var/swapped = 0
		passes++
		for(var/a = 1, a <= n, a++)
			var/list/cand
			if(!cell)
				cand = list()
				for(var/b = a + 1, b <= n, b++) cand += b
			else
				cand = list()
				for(var/turf/C in range(2, S[a])) if(cell[C]) for(var/b in cell[C]) if(b > a) cand += b
				if(length(cand) > 1)
					var/list/ck = list()
					for(var/b in cand) ck += b
					RmSortBy(cand, ck)
			for(var/b in cand)
				if(K[a] != K[b]) continue      // an archer never swaps onto a front square
				checks++
				var/turf/TA = S[a]
				var/turf/TB = S[b]
				var/now = sqrt((TA.x - AX[a]) ** 2 + (TA.y - AY[a]) ** 2) + sqrt((TB.x - AX[b]) ** 2 + (TB.y - AY[b]) ** 2)
				var/then = sqrt((TB.x - AX[a]) ** 2 + (TB.y - AY[a]) ** 2) + sqrt((TA.x - AX[b]) ** 2 + (TA.y - AY[b]) ** 2)
				// shorter in all; or, on the last pass, as long and the two routes cross (side by side a swap is the same length)
				if(then < now - 0.01 || (ties && rm_uncross_ties && then < now + 0.01 && RmSegCross(AX[a], AY[a], TA.x, TA.y, AX[b], AY[b], TB.x, TB.y)))
					S[a] = TB
					S[b] = TA
					if(cell)
						var/list/LA = cell[TA]
						var/list/LB = cell[TB]
						LA[LA.Find(a)] = b
						LB[LB.Find(b)] = a
					swapped = 1
					swaps++
		if(ties) break
		if(!swapped || pass_n >= cap) ties = 1     // settled (or out of passes): the last pass, crossing ties too
	for(var/i = 1, i <= n, i++) assign[who[i]] = S[i]
	rm_uncross_last = list(passes, checks, swaps)
	if(islist(UR) && length(UR) == 3)
		RmPlanCheck("uncross", AU, assign)
		RmPlanCheck("uncross counts", UR, rm_uncross_last)

// A group move's open tiles: from the seed, those it can get to out to R of T, through its walking members (rm_path_pass,
// set by the caller) and its own side's units, by the heights' steps up on a mountain (heights); each tile looked at
// once. list(reach: tile -> 1, places: tile -> free places, those with some). The engine's copy is rm_slot_reach
// (engine/native/RmSlots.cs: change both together; tools/formations/repro_slots.dm compares them).
proc/RemasterSlotReachDM(turf/T, R, turf/seed, mob/Monsters/lead_unit, list/group, heights)
	var/list/reach = list()
	if(seed)
		var/list/front = list(seed)
		reach[seed] = 1
		var/list/side = RmSide(lead_unit)
		var/list/shut = list()        // tiles found closed: each is looked at once, not once from each neighbour (10-24)
		var/list/dirs = list(NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST)
		while(length(front))
			var/turf/C = front[length(front)]
			front.len--
			for(var/d in dirs)
				var/turf/N = get_step(C, d)
				if(!N || reach[N] || shut[N] || get_dist(N, T) > R) continue
				if(heights && !RemasterStepHeights(C, N)) continue          // a step it may take up there (Gather.dm)
				if(!RemasterWalkable(N, lead_unit, N, side) || RmSwimWater(N))      // through units of its side too (Clip.dm); on land (Swim.dm, RmSlots.cs)
					shut[N] = 1
					continue
				reach[N] = 1
				front += N
	var/list/places = list()
	for(var/turf/C in reach)
		var/k = RemasterTilePlaces(C, group)
		if(k > 0) places[C] = k
	return list(reach, places)

// Each slot point (ordered: list(x, y, owner), middle first) the free tile nearest it, shifted by (sx, sy), on level z:
// its own when free, else the best within 2 (the middle mx, my pulling a little), else the best anywhere free. places
// (tile -> free places) is used up as tiles are taken. list(tiles, owners). The engine's copy is rm_slot_tiles.
proc/RemasterSlotTilesDM(list/ordered, sx, sy, mx, my, z, list/places)
	var/list/tiles = list()
	var/list/owner = list()
	for(var/list/p in ordered)
		var/px = p[1] + sx
		var/py = p[2] + sy
		var/turf/best
		var/best_d = 1#INF
		var/turf/P0 = locate(clamp(round(px + 0.5), 1, world.maxx), clamp(round(py + 0.5), 1, world.maxy), z)
		// its own tile when that is free: it always wins below (any other is a tile or more off, the middle's pull 0.2 at
		// most), so the 25 needn't be looked at
		if(P0 && places[P0] && P0.x == px && P0.y == py) best = P0
		else for(var/turf/C in range(2, P0))     // near its point first; anywhere free only when none is
			if(!places[C]) continue
			var/d = (C.x - px) ** 2 + (C.y - py) ** 2 + 0.1 * max(abs(C.x - mx), abs(C.y - my))
			if(d < best_d)
				best = C
				best_d = d
		if(!best) for(var/turf/C in places)
			var/d = (C.x - px) ** 2 + (C.y - py) ** 2 + 0.1 * max(abs(C.x - mx), abs(C.y - my))
			if(d < best_d)
				best = C
				best_d = d
		if(!best) break
		if(--places[best] <= 0) places -= best
		tiles += best
		owner += p[3]
	return list(tiles, owner)

proc/rm_slot_tiles(list/ordered, sx, sy, mx, my, z, list/places)
	return null

proc/rm_sort_by(list/L, list/K1, list/K2)
	return null

// The engine's RemasterSlotReachDM (RmSlots.cs, native version 4): list(reach, places), or null where it isn't there.
proc/rm_slot_reach(turf/T, R, turf/seed, mob/Monsters/M, list/group, list/pass, stairs, foot, monsters, ground, sky, list/side, siege)
	return null

var/rm_native_slots = 0
// world/New: this file's part is step RmChainWorldNew_Formations in Code/Remastered/Chains/WorldNew.dm

// The tiles round T (on a mountain top) a group can walk to from where each of it starts on that level (starts: unit ->
// turf), by the heights' steps (Gather.dm RemasterStepHeights) and through its own side's units: tile -> 1. Out to R of
// T, and far enough to take in the starts (the top of the stairs a little way off), 24 at most.
proc/RemasterHeightReach(list/starts, turf/T, R, mob/Monsters/lead)
	. = list()
	var/far = R
	var/list/front = list()
	for(var/M in starts)
		var/turf/S = starts[M]
		if(!isturf(S) || S.z != T.z || .[S]) continue
		far = max(far, get_dist(S, T))
		.[S] = 1
		front += S
	far = min(far, 24)
	var/list/side = RmSide(lead)
	while(length(front))
		var/turf/C = front[length(front)]
		front.len--
		for(var/d in list(NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST))
			var/turf/N = get_step(C, d)
			if(!N || .[N] || get_dist(N, T) > far) continue
			if(!RemasterStepHeights(C, N) || !RemasterWalkable(N, lead, N, side)) continue
			.[N] = 1
			front += N

// Called by RemasterOrder / RemasterAttackOrder once the orders are given: the group is those who took its move;
// its slots go to the page.
Player/proc/RemasterGroupFinish(datum/remaster_group/G)
	if(remaster_forming == G) remaster_forming = null   // a newer order may be forming its own group (a big one's are given over ticks)
	if(!G) return
	G.forming = 0
	G.pass_all = null    // made again for the members who took the move (Pass)
	var/list/kept = list()
	for(var/mob/Monsters/M in G.members) if(M.RemasterGroupNow() == G || (M.remaster_orders && RemasterGroupQueued(M, G))) kept += M
	G.members = kept
	if(length(kept)) RemasterSlotsPush(G)

proc/RemasterGroupQueued(mob/Monsters/M, datum/remaster_group/G)
	for(var/datum/remaster_order/O in M.remaster_orders) if(O.group == G) return 1
	return 0

// The slots to the page (remastered.html rmSlots3D): a marker on each, faded as its unit gets there.
Player/proc/RemasterSlotsPush(datum/remaster_group/G)
	if(!G || !client || !remaster_3d || !remaster_hud_ready) return
	var/list/S = list()
	for(var/mob/Monsters/M in G.members)
		var/turf/T = G.slots[M]
		if(T) S += list(list(RemasterUIRef(M), T.x, T.y, T.z))
	src << output(url_encode(json_encode(list("id"=G.id, "kind"=G.kind == "Move" ? "move" : "attack", "q"=G.queued, "f"=list(round(G.fx, 0.01), round(G.fy, 0.01)), "s"=S))), "mapwindow.hud:rmSlots3D")

// --- On the way ---------------------------------------------------------------------------

proc/RemasterGroupPathBudget()
	if(rm_group_paths_at != world.time)
		rm_group_paths_at = world.time
		rm_group_paths = 0
	if(rm_group_paths >= RM_GROUP_PATHS) return 0
	rm_group_paths++
	return 1

// Is the slot taken by something that won't move off it (not a group-mate still walking)?
proc/RemasterSlotTaken(turf/S, datum/remaster_group/G, mob/Monsters/me)
	for(var/atom/movable/X in S)
		if(X == me || !X.density) continue
		if(istype(X, /mob/Monsters) && (X in G.members) && G.Walking(X)) continue
		if(S.remaster_wallwalk && RemasterTilePlaces(S, list(me)) > 0) continue
		return 1
	return 0

// The nearest free tile to a taken slot that the unit can get to: a few tiles round it, nearest the slot, then the unit.
mob/Monsters/proc/RemasterSlotNear(turf/S, datum/remaster_group/G)
	var/list/claimed = list()
	for(var/mob/Monsters/M in G.slots) if(M != src) claimed[G.slots[M]] = 1
	var/list/pass = G.Pass(src)
	var/list/cands = list()
	for(var/turf/C in range(3, S))
		if(C == S || claimed[C] || C.z != z) continue
		if(RemasterTilePlaces(C, list(src) + pass) <= 0 || !RemasterWalkable(C, src, C)) continue
		cands += C
	for(var/a = 1, a <= length(cands), a++)
		for(var/b = a + 1, b <= length(cands), b++)
			var/turf/CA = cands[a]
			var/turf/CB = cands[b]
			if(get_dist(CB, S) * 10 + get_dist(CB, src) < get_dist(CA, S) * 10 + get_dist(CA, src)) cands.Swap(a, b)
	rm_path_pass = pass
	for(var/i = 1, i <= min(3, length(cands)), i++)
		var/turf/C = cands[i]
		if(rm_nav_count && get_dist(src, C) > 1) rm_path_who = "group: free tile check"
		if(get_dist(src, C) <= 1 || RemasterOrderPath(src, C, 0))
			rm_path_pass = null
			return C
	rm_path_pass = null
	return null

#define RM_ROUTE_GROUP_FAR 16      // a member this far from its slot follows its group's route map (RmRouteMap, Native.dm)

// A group member's way from its group's route map: one map for all of them, made for the group's spot (its target), to
// within 3 tiles of its own slot, searched on from there; a member already near its slot, the map to its slot. 1 when taken.
mob/Monsters/proc/RmGroupRoute(datum/remaster_order/O, datum/remaster_group/G, turf/goal)
	var/turf/GT = G.target
	if(GT && get_dist(src, goal) > 3) return RmRouteInstead(O, goal, 0, goal, 3, GT)
	return RmRouteInstead(O, goal, 0)

// RemasterApproach for a unit on a group move (Orders.dm): through walking group-mates, waiting for one in the way,
// round anything else; a taken or shut-in slot gives way to the nearest free tile.
mob/Monsters/proc/RemasterGroupApproach(datum/remaster_order/O, turf/goal)
	var/datum/remaster_group/G = O.group
	if(x != O.last_x || y != O.last_y)
		O.last_x = x
		O.last_y = y
		O.last_progress = world.time
	if(world.time - O.last_progress > max(100, Delay * 5))
		O.path = null       // no headway for a while: look for another way
		O.last_progress = world.time
	// Its slot taken by one that has stopped there, or no way into it: the nearest free tile it can reach.
	if(O.reslots < 2 && get_dist(src, goal) <= 4 && (RemasterSlotTaken(goal, G, src) || (O.partial == 2 && O.stuck_since && world.time - O.stuck_since >= 20)))
		var/turf/S2 = RemasterSlotNear(goal, G)
		if(S2)
			O.reslots++
			O.target = S2
			G.slots[src] = S2
			O.path = null
			O.stuck_since = 0
			goal = S2
			if(istype(O.issuer, /Player)) O.issuer:RemasterSlotsPush(G)
	while(length(O.path) && O.path[1] == loc) O.path.Cut(1, 2)
	// A compact group's first steps: the shared route, moved over to where this one stands.
	if(!length(O.path) && G.translate && !O.followed && G.lead_path && G.start[src] == loc && G.lead && G.start[G.lead])
		O.followed = 1
		var/turf/L0 = G.start[G.lead]
		var/dx = x - L0.x
		var/dy = y - L0.y
		var/list/pass = G.Pass(src)
		rm_path_pass = pass
		var/list/mine = list()
		for(var/turf/P in G.lead_path)
			var/turf/Q = locate(P.x + dx, P.y + dy, z)
			if(!Q || !RemasterWalkable(Q, src, goal))
				mine = null
				break
			mine += Q
		rm_path_pass = null
		if(length(mine) && (G.lead_partial || mine[length(mine)] == goal))
			O.path = mine
			O.partial = G.lead_partial
	var/turf/N = length(O.path) ? O.path[1] : null
	var/searched = 0
	if(N && !RemasterStepOpen(O.path, src, goal))   // units of its side are gone through, unless the slot is theirs (Clip.dm)
		var/mob/Monsters/W = RemasterWalkingMateOn(N, G, src)
		if(W)
			// a group-mate on its way: wait behind it (trying each tick, RemasterStepDelay); one that has stood
			// there a while without stepping is gone round
			if(O.wait_mate != W || W.remaster_stepped_at > O.wait_since)
				O.wait_mate = W
				O.wait_since = world.time
			// on its own pace behind a slower one (slower as it walks now: marching at its group's pace, or on its own):
			// it goes round now, if there is a way round
			var/datum/remaster_group/WG = W.RemasterMarchGroup()
			var/overtake = remaster_own_pace && max(W.RemasterOwnStep(), WG ? WG.Pace() : 0) > RemasterOwnStep()
			if(!overtake && world.time - O.wait_since < RM_MATE_WAIT)
				destination = N
				remaster_blocked = null
				remaster_order_status = "[O.kind]: travelling"
				return 1
		// something else in the way, or a mate that has stopped: round it, with everyone counted as in the way
		var/list/old = O.path
		O.path = null
		if(RemasterGroupPathBudget())
			searched = 1
			if(rm_nav_count) rm_path_who = W ? "group: round a stopped mate" : "group: step blocked"
			O.path = RemasterOrderPath(src, goal, 0, partial = 1)
			O.partial = rm_path_partial
			if(O.partial && !length(O.path) && rm_route && !RmReachNo(src, goal, 0)) RmGroupRoute(O, G, goal)   // the group's route map (Native.dm)
			O.repath_at = world.time + 30
		if(W && (!length(O.path) || O.partial == 2))
			// no way round a mate (a doorway): keep waiting in line behind it
			O.path = old
			O.partial = 0
			O.wait_since = world.time
			destination = N
			return 1
	else O.wait_mate = null
	if(!searched && !length(O.path) && (!O.stuck_since || world.time >= O.repath_at))
		// far from its slot: the group's map (one for all of them, RmRouteMap) to near its slot, searched on from there;
		// else, or with no map, its own route search (a few a tick)
		if(rm_route && get_dist(src, goal) > RM_ROUTE_GROUP_FAR && RmGroupRoute(O, G, goal))
			O.repath_at = world.time + 30
		else if(RemasterGroupPathBudget())
			rm_path_pass = G.Pass(src)
			if(rm_nav_count) rm_path_who = "group: own route"
			O.path = RemasterOrderPath(src, goal, 0, partial = 1)
			rm_path_pass = null
			O.partial = rm_path_partial
			if(O.partial && !length(O.path) && rm_route && !RmReachNo(src, goal, 0)) RmGroupRoute(O, G, goal)   // the group's route map (Native.dm)
			O.repath_at = world.time + 30
		else
			// too many routes to plan this tick: a step straight towards the slot, the route next time
			var/turf/S = get_step_towards(src, goal)
			if(S && S != loc && (RemasterWalkable(S, src, goal) || RemasterWalkingMateOn(S, G, src)))
				destination = S
				remaster_blocked = null
				remaster_order_status = "[O.kind]: travelling"
				return 1
	if(!length(O.path))
		if(!O.stuck_since) O.stuck_since = world.time
		RemasterBlock("No way through yet; trying again")
		O.last_progress = world.time
		return 0
	if(O.partial != 2) O.stuck_since = 0
	else if(!O.stuck_since) O.stuck_since = world.time
	destination = O.path[1]
	remaster_blocked = null
	remaster_order_status = O.partial == 2 ? "[O.kind]: no way through yet, going as close as it can" : "[O.kind]: travelling"
	return 1

// --- Formations per control group: companies (the user, 13:1x) -------------------------------
// A control group (1-9) keeps its own formation, like a company: while the selection is exactly a group's members, the
// formation chosen (band card, Army) is that group's, and its moves use it; any other selection uses the player's own
// choice. Kept in the player's save, by group number (the members themselves are the original's, not saved).
Player/var/list/remaster_group_formations = list()    // "n" -> list(shape, which of your own formations)

// The control group the selection is, or 0: the one just recalled first, then 1 to 9.
Player/proc/RemasterSelectedGroup()
	if(!length(Selected)) return 0
	var/list/order = list()
	if(RemasterGroupNumber(remaster_group_recalled_number)) order += remaster_group_recalled_number
	for(var/k = 1, k <= 9, k++) if(!(k in order)) order += k
	for(var/k in order)
		var/list/M = RemasterGroupMembers(k)
		if(!length(M) || length(M) != length(Selected)) continue
		var/all = 1
		for(var/mob/Monsters/U in M) if(!(U in Selected))
			all = 0
			break
		if(all) return k
	return 0

// list(shape, which own formation, group or 0): the selection's control group's formation, or the player's own.
Player/proc/RemasterFormationNow()
	var/g = RemasterSelectedGroup()
	var/list/F = g ? remaster_group_formations["[g]"] : null
	if(islist(F) && length(F) >= 2) return list(F[1], F[2], g)
	return list(remaster_formation, remaster_formation_mine, g)

proc/RemasterShapeWords(shape, mine_name)
	switch(shape)
		if("keep") return "keep the group's shape"
		if("custom") return mine_name ? "[mine_name]" : "your own formation, once you lay one out (Army, Formations)"
	return "form a [shape]"

// The formation command (band card, Army's shape cards) and "Use this formation": the selection's control group's if
// it is one, else the player's own.
Player/proc/RemasterFormationPick(value, mine = 0)
	if(!(value in list("keep", "line", "column", "box", "custom"))) return 0
	if(!mine) mine = value == "custom" ? RemasterFormationNow()[2] : remaster_formation_mine
	var/list/F = (mine >= 1 && mine <= length(remaster_formations)) ? remaster_formations[mine] : null
	var/g = RemasterSelectedGroup()
	if(g)
		remaster_group_formations["[g]"] = list(value, mine)
		RemasterNotice("Group [g] moves: [RemasterShapeWords(value, F && F["name"])].")
	else
		remaster_formation = value
		remaster_formation_mine = mine
		RemasterNotice("Group moves: [RemasterShapeWords(value, F && F["name"])].")
	return 1

// --- Drag to face (the user, 13:1x) ------------------------------------------------------------
// Press on the ground with units selected and drag before letting go (Ctrl or Cmd with the left button, or the right
// button when right-click gives orders): the pressed tile is where they go, the drag's direction the way they face, its
// length how wide the front row is. The page sends "formmove" "x|y|fx|fy|width|shift".
Player/var/tmp/list/remaster_face      // the next group move's facing and width: list(fx, fy, width)

Player/proc/RemasterFormMove(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 5 || !length(Selected)) return 0
	var/X = text2num(p[1])
	var/Y = text2num(p[2])
	var/FX = text2num(p[3])
	var/FY = text2num(p[4])
	var/W = text2num(p[5])
	if(isnull(X) || isnull(Y) || isnull(FX) || isnull(FY) || (!FX && !FY)) return 0
	var/turf/T = locate(clamp(round(X), 1, world.maxx), clamp(round(Y), 1, world.maxy), z)
	if(!T || get_dist(src, T) > REMASTER_3D_REACH) return 0
	remaster_face = list(FX, FY, clamp(round(W || 0), 1, 12))
	usr = src
	. = RemasterOrder(T, (length(p) >= 6 && p[6] == "1") || remaster_queue, "Move")
	remaster_face = null

// --- Attack box (the user, 12:4x: "to have units attack a group of units without focusing all on one unit") -------
// Attack (A), then a box dragged over the map, as a box selects your own: every foe the box touches goes into one
// shared pool, and the selected units share them out, each of the ones it can get at (RemasterRoomAt), spread over
// them and ganging up when they outnumber them (RemasterFoeScore).
// When its foe falls it takes the next, until none it can get at is left. A click on one foe still sends everyone at
// that one. The page sends the foes it drew in the box: "attackbox" "ref,ref,...".
datum/remaster_attack/var/list/pool         // the box's foes, shared by everyone sent at them
datum/remaster_attack/var/list/pool_load    // foe -> how many of the group took it, shared too
datum/remaster_attack/var/list/pool_far     // foe -> how many of those shoot or cast, shared too
datum/remaster_attack/var/datum/rm_reach/reach   // the order's open ground (RmReachFor), shared by everyone it went to
datum/remaster_attack/var/list/skip         // an attack-move's foe -> till when it doesn't try that one again (no way found)

// Who can get at which foe (the user, 10-25: "with A attack drag we should have units attack things they can reach
// sometimes they have to gang up if possible"): an attack order's open ground, a flood from where its units stand (the
// engine's, rm_slot_reach, through their own side by the walking rules; up on a mountain top the DM flood, by the block
// heights), over the ground round them and their foes (an attack-move's: round them and the march's goal, a sight
// further). Foes stand in it as walls do, so one in a ring of others is out of reach until a way in opens; the floods
// are made again when RM_REACH_FRESH old. A fighter gets at a foe with an open tile beside it in its flood, as many of
// them as there are such tiles; an archer or caster also at one it can shoot or cast at from a tile of its flood (in its
// reach, in sight). A unit off the ground (across the river from the rest) gets a flood of its own.
#define RM_REACH_MAX 60        // the flood's reach round its middle, at most
#define RM_REACH_MARGIN 9      // past the units and foes it is made for (an attack-move's sight, and some)
#define RM_REACH_FRESH 50      // ticks a flood is kept (foes fall, a way in opens)
datum/rm_reach
	var/turf/mid
	var/R = 0
	var/at = -1000
	var/list/floods = list()   // each: tile -> 1
	var/list/known = list()    // "flood|x,y,z|what" -> the answer (the room beside a tile; a shot at it from the flood)

// The ground for units and spots (foes, or a march's goal): the square round them all, on the first unit's level.
proc/RmReachFor(list/units, list/spots)
	var/mob/Monsters/F
	for(var/mob/Monsters/M in units) if(isturf(M.loc))
		F = M
		break
	if(!F) return null
	var/x0 = 1#INF
	var/x1 = -1#INF
	var/y0 = 1#INF
	var/y1 = -1#INF
	for(var/atom/A in units + spots)
		var/turf/S = isturf(A) ? A : A.loc
		if(!isturf(S) || S.z != F.z) continue
		x0 = min(x0, S.x)
		x1 = max(x1, S.x)
		y0 = min(y0, S.y)
		y1 = max(y1, S.y)
	var/datum/rm_reach/RM = new
	RM.mid = locate(round((x0 + x1) / 2), round((y0 + y1) / 2), F.z)
	RM.R = min(RM_REACH_MAX, round(max(x1 - x0, y1 - y0) / 2 + 0.5) + RM_REACH_MARGIN)
	return RM

// Which flood M stands in (made when it is the first there), or 0: off the ground.
datum/rm_reach/proc/FloodOf(mob/Monsters/M)
	var/turf/S = M.loc
	if(!isturf(S) || !mid || S.z != mid.z || get_dist(S, mid) > R) return 0
	if(world.time - at > RM_REACH_FRESH)
		at = world.time
		floods = list()
		known = list()
	for(var/i = 1, i <= length(floods), i++)
		var/list/L = floods[i]
		if(L[S]) return i
	var/heights = S.z == SKY_LAYER && !RemasterCanClimb(M)
	var/list/RP
	var/list/was = rm_path_pass
	rm_path_pass = null
	if(!heights && rm_native_slots) RP = rm_slot_reach(mid, R, S, M, list(M), list(), 'Stairs.dmi', /obj/RmBeastFoot, /mob/Monsters, GROUND_LAYER, SKY_LAYER, RmSide(M), /mob/Monsters/RemasterSiege)
	if(!(islist(RP) && length(RP) == 2)) RP = RemasterSlotReachDM(mid, R, S, M, list(M), heights)
	rm_path_pass = was
	floods += list(RP[1])
	return length(floods)

// Open tiles of flood i beside T: where fighters can stand to strike at what stands on T.
datum/rm_reach/proc/Room(i, turf/T)
	var/k = "[i]|[T.x],[T.y],[T.z]|room"
	if(!isnull(known[k])) return known[k]
	var/list/L = floods[i]
	. = 0
	for(var/turf/C in orange(1, T)) if(L[C]) .++
	known[k] = .

// Can one of flood i shoot or cast at what stands on T from a tile of it r or nearer, in sight (the nearest few looked at)?
datum/rm_reach/proc/Shot(i, turf/T, r)
	var/k = "[i]|[T.x],[T.y],[T.z]|[r]"
	if(!isnull(known[k])) return known[k]
	var/list/L = floods[i]
	. = 0
	var/tries = 0
	for(var/turf/C in range(r, T))
		if(!L[C]) continue
		if(T in view(r, C))
			. = 1
			break
		if(++tries >= 12) break
	known[k] = .

// How far it fights from: its bow's reach while it has arrows, its longest spell's while it has the mana for one
// (RemasterCastFirst's moves), else 1 (beside its foe).
mob/Monsters/proc/RemasterFarReach()
	if(RemasterCanShoot()) return RemasterShotReach()
	var/role = RemasterFormationRole()
	if(role != "mage" && role != "ranged") return 1
	var/obj/Items/W = RmHeldWeapon(src)
	. = 1
	for(var/id in RmMovesFor(src))
		var/list/D = rm_moves[id]
		if(D["kind"] != "cast" || (rm_moves_off && (id in rm_moves_off)) || !RmMoveOpen(src, id)) continue
		if(D["mana"] && (!W || RmManaOf(W) < D["mana"])) continue
		. = max(., D["range"] || 1)

// How many fighters can stand at E to fight it, for this unit (in its flood of RM): E's open sides (1-8); 8 when it can
// shoot or cast at E from its flood (reach over 1); 0 when it can't get at E at all (behind a wall, across water, up
// a cliff it can't climb). With no ground (a click on one foe) or off it, 8: it goes and sees, as before. A great beast is
// fought at its parts (Beasts.dm): 8.
mob/Monsters/proc/RemasterRoomAt(datum/rm_reach/RM, mob/Monsters/E, reach)
	if(!E || !isturf(E.loc) || E.z != z) return 0
	if(!RM || RmBeastPartFor(src, E)) return 8
	var/i = RM.FloodOf(src)
	if(!i) return 8
	if(reach > 1 && RM.Shot(i, E.loc, reach)) return 8
	return RM.Room(i, E.loc)

// The foe to take, the lowest first. Spread over them (the user, 10-24: "attack a group of units without focusing all on
// one unit"): the one with the fewest of its kind on it (archers and casters among themselves, fighters among
// themselves), then the fewest in all, then the nearest. A fighter takes one only while a tile beside it is free, so
// with more fighters than foes they gang up, as many on each as its open sides allow (the user, 10-25: "sometimes they
// have to gang up if possible"); with all of them full, the nearest (it waits its turn). all: how many are on E; far_on:
// how many of them are archers or casters; room: E's open sides (RemasterRoomAt); far: it is an archer or a caster (by
// what it holds, RemasterFormationRole); melee: it fights from beside E (no arrows or mana left, or a fighter).
mob/Monsters/proc/RemasterFoeScore(mob/Monsters/E, all, far_on, room, far, melee)
	var/on = all - far_on
	return (melee && on >= room ? 100000 : 0) + (far ? far_on : on) * 1000 + all * 100 + get_dist(src, E)

// An attack-move's next foe (RemasterAttackTick): the hostiles in sight (with nobody of another owner within sight the
// look is skipped, rm_foe_near), and within RM_GANG_REACH those its group fights or a mate saw lately (RM_SEEN_FOR), so
// that a foe in one's sight draws in the others who can get at it (a fighter on the bank sees the goblins across the
// river; the archers behind it take them); of those it can get at, the best by RemasterFoeScore.
#define RM_GANG_REACH 12
#define RM_SEEN_FOR 50
mob/Monsters/proc/RemasterMarchFoe(datum/remaster_attack/K)
	var/datum/remaster_group/G = K.group
	var/list/C = list()
	var/list/pairs = list()   // each realm's war and alliance once in this look (Attack.dm RemasterHostile)
	if(rm_foe_near(src, REMASTER_ATTACK_SIGHT, /mob/Monsters))
		for(var/mob/Monsters/H in oview(REMASTER_ATTACK_SIGHT, src)) if(RemasterHostile(src, H, 0, pairs) && RmNotices(src, H))   // not one behind it, unnoticed (Facing.dm)
			C += H
			if(G)
				if(!G.seen) G.seen = list()
				G.seen[H] = world.time
	var/list/on = G ? G.Fighting() : null
	for(var/mob/Monsters/H in on) if(!(H in C) && get_dist(src, H) <= RM_GANG_REACH && RemasterHostile(src, H, 0, pairs)) C += H
	if(G && G.seen) for(var/mob/Monsters/H in G.seen) if(G.seen[H] > world.time - RM_SEEN_FOR && !(H in C) && get_dist(src, H) <= RM_GANG_REACH && RemasterHostile(src, H, 0, pairs)) C += H
	if(!length(C)) return null
	var/reach = RemasterFarReach()
	var/role = RemasterFormationRole()
	var/far = role == "ranged" || role == "mage"
	var/mob/Monsters/best
	var/best_s = 1#INF
	var/standing = -1   // a foe of its standing near (looked up once, at the first fallen one)
	for(var/mob/Monsters/H in C)
		if(K.skip && K.skip[H] > world.time) continue
		if(RmDownOut(H))   // down, a foe standing near: not now (Falls.dm)
			if(standing < 0) standing = RmStandingFoeNear(src)
			if(standing) continue
		var/room = RemasterRoomAt(K.reach, H, reach)
		if(!room) continue
		var/list/n = on ? on[H] : null
		var/s = RemasterFoeScore(H, n ? n[1] : 0, n ? n[2] : 0, room, far, reach <= 1)
		if(s < best_s)
			best = H
			best_s = s
	if(best && on)      // counted now: the others choosing this tick see it (Fighting is made once a tick)
		if(!on[best]) on[best] = list(0, 0)
		var/list/n = on[best]
		n[1] = n[1] + 1
		if(far) n[2] = n[2] + 1
	return best

// The foes a group's members fight now: foe -> list(how many, how many of them archers or casters); made once a tick.
datum/remaster_group/var/tmp/fight_at = -1
datum/remaster_group/var/tmp/list/fight_on
datum/remaster_group/var/tmp/list/seen         // an attack-move's foes its members saw: foe -> when (RemasterMarchFoe)
datum/remaster_group/proc/Fighting()
	if(fight_at != world.time || !fight_on)
		fight_at = world.time
		fight_on = list()
		for(var/mob/Monsters/M in members)
			var/datum/remaster_attack/A = M.remaster_attack
			var/mob/Monsters/E = A ? A.target : null
			if(!E || !E.loc) continue
			if(!fight_on[E]) fight_on[E] = list(0, 0)
			var/list/n = fight_on[E]
			n[1] = n[1] + 1
			if(M.RemasterFormationRole() in list("ranged", "mage")) n[2] = n[2] + 1
	return fight_on

mob/Monsters/proc/RemasterPoolNext()
	var/datum/remaster_attack/K = remaster_attack
	if(!K || !K.pool) return null
	var/reach = RemasterFarReach()
	var/role = RemasterFormationRole()
	var/far = role == "ranged" || role == "mage"
	var/mob/Monsters/best
	var/list/R = rm_pool_native ? RmPoolRank(src, K, far) : null   // the engine's ranking of the box (Native.dm): the same foe from a few looks
	if(R)
		best = RmPoolWalk(K, R, reach, far)
		if(rm_pool_verify)   // shadow mode: the whole look too, its foe used
			var/mob/Monsters/B = RmPoolLook(K, reach, far)
			RmPoolVerify(best, B)
			best = B
	else best = RmPoolLook(K, reach, far)
	if(!best) return null
	K.pool_load[best] = (K.pool_load[best] || 0) + 1
	if(far) K.pool_far[best] = (K.pool_far[best] || 0) + 1
	K.target = best
	K.chosen = best
	K.path = null
	remaster_order_status = "Attacking [RemasterCombatName(best)]"
	return best

// The whole look over the box (RemasterPoolNext): every foe, the gone and those it may no longer fight dropped from it.
mob/Monsters/proc/RmPoolLook(datum/remaster_attack/K, reach, far)
	var/mob/Monsters/best
	var/best_s = 1#INF
	var/standing = -1   // a foe of its standing near (looked up once, at the first fallen one)
	for(var/mob/Monsters/E in K.pool.Copy())
		if(!E.loc || !RemasterHostile(src, E, 1))     // fallen, fled into a hole, or made peace
			K.pool -= E
			K.pool_load -= E
			K.pool_far -= E
			continue
		if(E.z != z) continue
		if(RmDownOut(E))   // down, a foe standing near: later (Falls.dm)
			if(standing < 0) standing = RmStandingFoeNear(src)
			if(standing) continue
		var/Player/I = K.issuer
		if(istype(I) && !I.RmFogSeesMob(E)) continue   // in the fog of war: not now, perhaps later (Fog.dm)
		var/room = RemasterRoomAt(K.reach, E, reach)     // 0: behind a wall, across water, up a cliff (RmReachFor)
		if(!room) continue
		var/all = K.pool_load[E] || 0
		var/s = RemasterFoeScore(E, all, K.pool_far[E] || 0, room, far, reach <= 1)
		if(s < best_s)
			best = E
			best_s = s
	return best

// The engine's ranking walked (Native.dm RmPoolRank): foes by the lowest score each could have (a fighter's 100000 for a
// foe with no free side, and leaving out one it can't get at or see, only raise or drop a score), then by place in the
// box; each one's down, fog, room and score as the whole look finds them, until no later foe can score lower, or as low
// from an earlier place: the whole look's foe.
mob/Monsters/proc/RmPoolWalk(datum/remaster_attack/K, list/R, reach, far)
	var/list/C = R[1]
	var/list/LB = R[2]
	var/list/D = R[3]
	var/list/PL = R[6]
	var/Player/I = K.issuer
	var/mob/Monsters/best
	var/best_s = 1#INF
	var/best_p = 1#INF
	var/standing = -1
	for(var/n = 1, n <= length(C), n++)
		var/lb = LB[n]
		var/p = PL[n]
		if(lb > best_s || (lb == best_s && p > best_p)) break
		var/mob/Monsters/E = C[n]
		if(D[n])   // down, a foe standing near: later (Falls.dm)
			if(standing < 0) standing = RmStandingFoeNear(src)
			if(standing) continue
		if(istype(I) && !I.RmFogSeesMob(E)) continue
		var/room = RemasterRoomAt(K.reach, E, reach)
		if(!room) continue
		var/s = RemasterFoeScore(E, K.pool_load[E] || 0, K.pool_far[E] || 0, room, far, reach <= 1)
		if(s < best_s || (s == best_s && p < best_p))
			best = E
			best_s = s
			best_p = p
	return best

Player/proc/RemasterAttackBox(value)
	var/list/pool = list()
	for(var/ref in splittext("[value]", ","))
		var/mob/Monsters/E = locate(ref)
		if(istype(E) && E.z && isturf(E.loc) && !(E in pool) && RmFogSeesMob(E)) pool += E   // only what you can see (Fog.dm)
	return RemasterAttackPool(pool, "in the box")

// Attack (A), then a click on one foe without a drag (the user, 13:1x: "clicked on a unit attacks that unit type"):
// every foe within RM_ALIKE_REACH of it holding the same kind of weapon (fighters, archers or casters, by
// RemasterFormationRole) goes into one pool, shared out as the box's. A plain click (no A) still goes for that one foe.
#define RM_ALIKE_REACH 12
var/list/rm_role_words = list("front"="fighters", "ranged"="archers", "mage"="casters", "any"="foes like it")
Player/proc/RemasterAttackAlike(mob/Monsters/E)
	var/mob/Monsters/first
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0 && !RemasterIsSiege(M))
		first = M
		break
	if(!first || !RemasterHostile(first, E, 1)) return null
	var/sieges = RemasterSiegeOrder(E, 1)        // siege engines in the selection, as a plain attack (Siege.dm)
	var/role = E.RemasterFormationRole()
	var/list/pool = list(E)
	for(var/mob/Monsters/O in range(RM_ALIKE_REACH, E))
		if(O == E || !isturf(O.loc) || O.Owner != E.Owner || !RemasterHostile(first, O, 1)) continue
		if(O.RemasterFormationRole() == role && RmFogSeesMob(O)) pool += O   // only those you can see (Fog.dm)
	return RemasterAttackPool(pool, "([rm_role_words[role]])") + sieges

// The selected units share out a pool of foes (the box, or all of a kind): see RemasterPoolNext.
Player/proc/RemasterAttackPool(list/pool, words)
	var/list/load = list()
	var/list/far = list()
	var/n = 0
	var/list/U = list()            // the ground they get at their foes over (RmReachFor), made for all of them
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && isturf(M.loc)) U += M
	var/datum/rm_reach/RM = RmReachFor(U, pool)
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || !(M in UnitList) || M.HP <= 0 || M.GoingToDie || RemasterIsSiege(M)) continue
		var/fits = 0
		for(var/mob/Monsters/E in pool) if(RemasterHostile(M, E, 1))   // one foe it may fight is enough (bands, 10-29: it
			fits = 1                                                    // checked the whole box, 42 of a box order's 67 ms)
			break
		if(!fits) continue
		M.RemasterCancelOrders()
		if(M.remaster_defense) M.RemasterCancelDefense(0)
		M.RemasterCareInterrupt()
		M.RemasterWake()
		M.remaster_patrol = null
		var/datum/remaster_attack/K = new
		K.issuer = src
		K.pool = pool
		K.pool_load = load
		K.pool_far = far
		K.reach = RM
		K.last_position = M.loc
		K.last_progress = world.time
		M.remaster_attack = K
		M.remaster_push_step = 1
		if(!M.RemasterPoolNext())
			M.remaster_attack = null
			continue
		RmFirstTick(M, K, n + 1)   // its first step this tick, as a move's (the first RM_FIRST_NOW of them; Formations.dm)
		n++
	remaster_attack_mode = 0
	var/out = 0                    // foes none of them can get at
	for(var/mob/Monsters/E in pool)
		var/can = 0
		for(var/mob/Monsters/M in U) if(M.remaster_attack && M.remaster_attack.reach == RM && M.RemasterRoomAt(RM, E, M.RemasterFarReach()))
			can = 1
			break
		if(!can) out++
	if(n)
		if(remaster_3d) Remaster3DMovesPushSoon()
		RemasterNotice("Attack! [n] going for [length(pool) - out] foe\s [words][out ? "; [out] out of reach" : ""].")
		RemasterLog("Attack ordered on [length(pool)] foe\s [words]", "fight", pool[1])
	else RemasterNotice(length(pool) ? "Your selected units can't attack those." : "No foes in the box.")
	return n

// --- Archers and casters: their own first, then melee (the user, 2026-10-23) ----------------------
// "Ranged and mage units should exhaust all magic and throwable ammo, if none then use melee." In an attack order or
// fighting back (Attack.dm, Defense.dm): throwing weapons go first (RemasterTryThrow, as before); an archer shoots
// while its equipped quiver has arrows, from within its bow's reach (5-8 tiles, BeastParts.dm RmBowRange); an
// archer's or caster's spells ("cast" moves that reach 2 or more, WeaponSkills.dm) go from their range while the
// weapon has the mana, the unit waiting there for one to be ready again. With none of that left it closes in and
// fights: out of arrows, a bow can't strike (Combats.dm), so it takes up the best melee weapon it carries, or fists.
// A fighter with an enchanted blade stays a fighter: it goes in, and its blade's spells go off in the fight as before.
#define RM_SHOT_REACH 10   // a cap above the longest bow (7, and 8 at Ranged 60); each bow's own reach is RmBowRange

mob/Monsters/proc/RemasterCanShoot()
	return HoldingWeapon == "Bow" && HasRightArm && RemasterQuiverCount(src) > 0

mob/Monsters/proc/RemasterShotReach(mob/E)   // the files before this one can't see the define (included last); at E: a tile more from higher ground (Surround.dm)
	return min(RmBowRangeTo(src, E), RM_SHOT_REACH)

// Out of arrows with a bow in hand: the best melee weapon carried (a sword, an axe, a mace, a spear, a dagger), else
// fists. 1 when it changed. nonlethal: arrows or not, as a bow strikes no blow and a non-lethal fight (or a Capture) is hand
// to hand (Subdue.dm, Defense.dm; polish 10-26: such archers walked up and stood by their foe for good).
mob/Monsters/proc/RemasterBowToMelee(nonlethal = 0)
	if(HoldingWeapon != "Bow" || (!nonlethal && RemasterCanShoot())) return 0
	var/list/rank = list("Sword"=5, "Axe"=4, "Mace"=3, "Spear"=2, "Dagger"=1)
	var/obj/Items/Equipment/Weapon/best
	for(var/obj/Items/Equipment/Weapon/X in src)
		if(X.suffix != "(Carrying)" || !rank[X.ItemType]) continue
		if(!best || rank[X.ItemType] > rank[best.ItemType]) best = X
	var/obj/Items/Equipment/Weapon/bow
	for(var/obj/Items/Equipment/Weapon/B in src) if(B.suffix == "(Equipped)" && B.ItemType == "Bow") bow = B
	if(best) EquipItem(best)
	if(HoldingWeapon == "Bow" && bow) UnEquipItem(bow)
	if(HoldingWeapon == "Bow") return 0
	remaster_bow_away = bow                 // taken up again when there are arrows (RemasterBowBack)
	remaster_blade_taken = best && best.suffix == "(Equipped)" ? best : null
	remaster_order_status = "[nonlethal ? "Non-lethal" : "Out of arrows"]: fights with [best && best.suffix == "(Equipped)" ? best.name : "fists"]"
	if(!nonlethal && istype(Owner, /Player)) Owner:RemasterLog("[RemasterBareName()] is out of arrows and fights with [best && best.suffix == "(Equipped)" ? "a [lowertext(best.ItemType)]" : "fists"]", "fight", src)
	return 1

mob/Monsters/var/tmp
	obj/Items/remaster_bow_away       // the bow it put away when out of arrows
	obj/Items/remaster_blade_taken    // the blade it took up instead

// When a fight is over (its attack order ends, or it is done fighting back), one that put its bow away for want of
// arrows takes it up again if its quiver has arrows now, putting away the blade it took up; with none it keeps the
// blade (or fists) it fights with.
mob/Monsters/proc/RemasterBowBack()
	var/obj/Items/B = remaster_bow_away
	if(!B) return 0
	if(B.loc != src || B.suffix != "(Carrying)" || HoldingWeapon == "Bow")
		remaster_bow_away = null
		remaster_blade_taken = null
		return 0
	if(RemasterQuiverCount(src) <= 0) return 0
	var/obj/Items/S = remaster_blade_taken
	if(S && S.loc == src && S.suffix == "(Equipped)") UnEquipItem(S)
	EquipItem(B)
	remaster_bow_away = null
	remaster_blade_taken = null
	return HoldingWeapon == "Bow"

mob/Monsters/RemasterAttackStop()
	..()
	RemasterBowBack()

mob/Monsters/RemasterCancelDefense(resume = 0)
	..()
	RemasterBowBack()

// An archer's or caster's spells from their range while it has the mana for them: 1 cast now or waiting in reach for
// one to be ready (a caster with no arrows to shoot meanwhile, its foe not beside it); a reach (2 or more) to close
// in to; 0 none left (melee then).
mob/Monsters/proc/RemasterCastFirst(mob/Monsters/E)
	if(!E || remaster_nonlethal) return 0
	var/role = RemasterFormationRole()
	if(role != "mage" && role != "ranged") return 0
	var/obj/Items/W = RmHeldWeapon(src)
	var/d = get_dist(src, E)
	var/hold = 0
	var/reach = 0
	for(var/id in RmMovesFor(src))
		var/list/D = rm_moves[id]
		if(D["kind"] != "cast" || (rm_moves_off && (id in rm_moves_off)) || !RmMoveOpen(src, id)) continue
		var/r = RmMoveRange(src, D, E)   // a bow's, a tile further from higher ground (Surround.dm)
		if(r < 2) continue
		if(D["mana"] && (!W || RmManaOf(W) < D["mana"])) continue      // not enough left for this one
		if(d <= r && (E in oview(r, src)))
			if(!RmMoveWait(src, id) && RmUseMove(id, E))
				destination = null
				return 1
			hold = 1                                                     // in reach, ready again soon: wait here
		else if(d > r) reach = max(reach, r)   // in reach but out of sight (round a corner): the usual approach finds a way
	if(hold && d > 1 && !RemasterCanShoot())
		destination = null
		return 1
	return hold ? 0 : reach

// --- First steps of a big group's orders ------------------------------------------------------------
// Each unit's first order tick at the click (its route, its first step) cost 0.15-0.26 ms; for 200 that was 29-52 ms in
// the click's tick, the whole server waiting (server-cost, 10-24; the user: "single digits"). The click sets off as many
// as fit in RM_FIRST_MS of its tick (never fewer than RM_FIRST_NOW), so a group of a few dozen all step at once (the
// user, 10-24: "super responsive low latency like the best rts ever"); the rest RM_FIRST_BATCH a tick after it, in
// order. Each one counts twice its first tick: its first step comes later in the same tick, from its walk loop, and
// costs about the same (measured: 0.32 ms each on a loaded Mac), so the click's tick gets RM_FIRST_MS more in all. One
// whose order changed meanwhile, or that the orders tick (QoL.dm, every half second) set off already, is left alone.
#define RM_FIRST_NOW 2
#define RM_FIRST_MS 8         // ms of the click's tick for first steps (their first ticks and the steps after them)
#define RM_FIRST_BATCH 24        // later ticks: never fewer than this...
#define RM_FIRST_LATER_MS 25     // ...and more while they fit in this many ms of the tick (charged twice, as at the click)
var/list/rm_first_units = list()      // units waiting for their first tick...
var/list/rm_first_orders = list()     // ...and the order or attack it was for
var/rm_first_running = 0
var/rm_first_seen = -1000             // the tick the drain last went on, or was started (RmFirstTick starts a new one if it went silent)
var/rm_first_tick = -1                // the tick rm_first_ms counts
var/rm_first_ms = 0                   // ms of first steps set off in it
proc/RmFirstTick(mob/Monsters/M, datum/D, k, counted = 0)   // counted: its go is in the caller's own ledger time (Orders.dm's hand-out)
	if(rm_first_tick != world.time)
		rm_first_tick = world.time
		rm_first_ms = 0
	if(k <= RM_FIRST_NOW || (rm_first_ms < RM_FIRST_MS && !length(rm_first_units)))   // none waiting ahead of it
		var/t0 = world.tick_usage
		RmFirstGo(M, D)
		var/go = max(0, (world.tick_usage - t0) * world.tick_lag)   // tick_usage: a share of the tick (tick_lag 1 = 100 ms)
		rm_first_ms += 2 * go   // x2: and its step
		RmTickCharge(counted ? go : 2 * go)   // the one tick ledger (Spread.dm)
		return
	rm_first_units += M
	rm_first_orders += D
	if(rm_first_running && world.time - rm_first_seen <= 20) return   // a drain silent for 2 s died: a new one (S2b, 10-27)
	rm_first_running = 1
	rm_first_seen = world.time
	spawn(1) RmFirstLater()

proc/RmFirstLater()
	while(length(rm_first_units))
		rm_first_at = world.time
		rm_first_seen = world.time
		var/t0 = world.tick_usage
		var/i = 0
		while(i < length(rm_first_units) && (i < 1 || ((i < RM_FIRST_BATCH || 2 * (world.tick_usage - t0) * world.tick_lag < RM_FIRST_LATER_MS) && (!rm_tick_cap || !rm_tick_ledger || RmTickUsed() + 2 * (world.tick_usage - t0) * world.tick_lag < rm_tick_cap))))   // at least one a tick; the batch's minimum and its share both stop at the ledger's cap (Spread.dm)
			i++
			try   // one unit's error never stops the drain (it stayed "running" for good, and every later order queued)
				RmFirstGo(rm_first_units[i], rm_first_orders[i])
			catch(var/exception/FE)
				world.log << "Remastered: a first step failed: [FE]"
		RmTickCharge(2 * max(0, (world.tick_usage - t0) * world.tick_lag))   // the one tick ledger (Spread.dm)
		rm_first_units.Cut(1, i + 1)
		rm_first_orders.Cut(1, i + 1)
		if(length(rm_first_units)) sleep(1)
	rm_first_running = 0

proc/RmFirstGo(mob/Monsters/M, datum/D)
	if(!M || !M.loc || M.HP <= 0) return
	if(istype(D, /datum/remaster_attack))
		if(M.remaster_attack == D) M.RemasterAttackTick()
		return
	var/datum/remaster_order/O = D
	if(M.remaster_active == O) return             // the orders tick set it off already
	if(!M.remaster_active && (O in M.remaster_orders)) M.RemasterOrderTick()   // (a climb up stairs may come first)

// --- The player's switch: own pace ------------------------------------------------------------

// HUD command "unitpace": "ref,ref,...|own" or "...|group".
Player/proc/RemasterPaceCommand(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 2 || !(p[2] in list("own", "group"))) return 0
	var/n = 0
	for(var/ref in splittext(p[1], ","))
		var/mob/Monsters/M = RemasterUIUnit(ref)
		if(!istype(M) || M.Owner != src) continue
		M.remaster_own_pace = p[2] == "own"
		n++
	if(n) RemasterNotice(p[2] == "own" ? "[n == 1 ? "It walks" : "[n] units walk"] at [n == 1 ? "its" : "their"] own pace in group moves." : "[n == 1 ? "It keeps" : "[n] units keep"] to the group's pace: a group sent together marches at its slowest member's speed.")
	return n

mob/Monsters/RemasterUnitData(Player/P)
	. = ..()
	if(!islist(.)) return
	if(remaster_own_pace) .["ownPace"] = 1
	.["frole"] = RemasterFormationRole()     // its place in a formation with roles (the page's slot guess, the editor)
	// the arrows in its bag at a glance (the user, 16:3x: "the arrows in the bag of the unit"): the bag shows them as a slot
	// of their own after their quiver (how many, an arrow's picture, each kind in its tip); the quiver's tip says so too
	var/list/IT = .["items"]
	if(length(IT)) for(var/obj/Items/Equipment/Armour/Quiver/LeatherQuiver/Q in src)
		var/r = RemasterUIRef(Q)
		for(var/list/e in IT) if(e["ref"] == r)
			var/list/kinds = list()
			var/list/icons = list()
			for(var/obj/Items/Arrows/A in Q)
				var/k = "[A.name]"
				kinds[k] = (kinds[k] || 0) + 1
				if(!icons[k]) icons[k] = P.RemasterItemIcon(A)
			var/list/ak = list()
			for(var/k in kinds) ak += list(list(k, kinds[k], icons[k]))
			e["arrows"] = Q.Content
			e["arrowKinds"] = ak
			var/list/tip = list("Arrows [Q.Content]")
			if(e["info"]) tip += e["info"]
			e["info"] = jointext(tip, " · ")   // OpenDream: no "·" in a string with [] in it ("Invalid special character")

// --- Groups from the Company list (the user, 2026-10-23) -------------------------------------
// "Select units, right-click a unit in the Company list on the right and say Group, and that will be a group card we
// click and can expand"; "Ctrl+G to group up as well"; "Ctrl-click units on the screen and it will highlight all units
// in the group, and other groups so we can have several". The selected units (and the one right-clicked) become a group
// of their own: a card in the Company list (click: select them all; open it: their rows; right-click: ungroup). A unit
// is in one such group (grouping takes it out of any other). Ctrl-click (Cmd-click) on a grouped unit in the world
// selects its group; Ctrl-click on one of another group then adds that group. Shift-click still adds or takes one unit.
// These are the game's numbered control groups (ControlGroups.dm: a digit recalls, Ctrl+digit saves), so each keeps its
// own formation (RemasterFormationNow) and the digit keys work on them.

// HUD command "fmgroup": "make|ref" (ref: the unit right-clicked, or none), "select|n,n|add", "ungroup|n", "out|ref".
Player/proc/RemasterGroupCommand(value)
	var/list/p = splittext("[value]", "|")
	if(!length(p)) return 0
	switch(p[1])
		if("make") return RemasterGroupMake(length(p) >= 2 ? p[2] : null)
		if("select") return RemasterGroupSelect(length(p) >= 2 ? p[2] : "", length(p) >= 3 && p[3] == "1")
		if("ungroup") return RemasterGroupUngroup(length(p) >= 2 ? text2num(p[2]) : 0)
		if("out") return RemasterGroupOut(length(p) >= 2 ? RemasterUIUnit(p[2]) : null)
	return 0

// Ctrl+G in the game window (skin.dmf); the HUD page sends "fmgroup make" itself when it has the keyboard.
Player/verb/RemasterGroupVerb()
	set name = "Remaster-Group"
	set hidden = 1
	RemasterGroupMake()

Player/proc/RemasterGroupMake(ref)
	var/list/U = list()
	for(var/mob/Monsters/M in Selected) if(RemasterGroupActor(M)) U += M
	var/mob/Monsters/R = ref ? RemasterUIUnit(ref) : null
	if(istype(R) && RemasterGroupActor(R) && !(R in U))
		usr = src
		R.Select(src)                   // the one right-clicked joins them
		U += R
	if(!length(U))
		RemasterNotice("Select units first, then Group (Ctrl+G).")
		return 0
	var/n = 0
	for(var/k = 1, k <= 9 && !n, k++)
		var/list/G = RemasterGroupMembers(k)
		if(length(G) == length(U) && !length(G - U)) n = k
	if(n)
		RemasterGroupRecalled(n)
		RemasterNotice("They are group [n] already.")
		return n
	for(var/k = 1, k <= 9, k++)          // out of any other group
		var/list/G = RemasterGroupMembers(k)
		if(!length(G & U)) continue
		G -= U
		vars["Group[k]"] = G
		if(!length(G)) remaster_group_formations -= "[k]"
	for(var/k = 1, k <= 9 && !n, k++) if(!length(RemasterGroupMembers(k))) n = k
	if(!n)
		RemasterNotice("All nine groups are in use: right-click a group's card in the Company list to ungroup it.")
		return 0
	vars["Group[n]"] = U.Copy()
	remaster_group_formations -= "[n]"   // a new group starts with your own formation
	RemasterGroupRecalled(n)
	RemasterNotice("Group [n]: [length(U)] unit\s. Click its card in the Company list, press [n], or Ctrl-click one of them to select them all.")
	return n

// The selection is group n as recalled (the band card shows it as that group; its formation is the group's).
Player/proc/RemasterGroupRecalled(n)
	remaster_group_recalled = list()
	remaster_group_recalled_number = n
	for(var/mob/Monsters/M in Selected) remaster_group_recalled += RemasterUIRef(M)

// "n,n": select those groups' members; add: added to the selection (Ctrl-click on another group, Shift on a card).
Player/proc/RemasterGroupSelect(nums, add = 0)
	var/list/N = list()
	for(var/s in splittext("[nums]", ","))
		var/k = text2num(s)
		if(RemasterGroupNumber(k) && !(k in N)) N += k
	var/list/want = list()
	for(var/k in N) for(var/mob/Monsters/M in RemasterGroupMembers(k)) if(!(M in want)) want += M
	if(!length(want))
		RemasterNotice("That group is empty.")
		return 0
	RemasterNormalizeSelection()
	usr = src
	if(!add) for(var/mob/Monsters/S in Selected.Copy()) if(!(S in want)) S.Deselect(src)
	for(var/mob/Monsters/M in want) if(!(M in Selected)) M.Select(src)
	remaster_queue = 0
	if(length(N) == 1 && length(Selected) == length(want)) RemasterGroupRecalled(N[1])
	else remaster_group_recalled_number = 0
	var/list/in_sel = list()
	for(var/k = 1, k <= 9, k++)
		var/list/G = RemasterGroupMembers(k)
		if(length(G) && !length(G - Selected)) in_sel += "[k]"
	RemasterNotice(length(in_sel) > 1 ? "Groups [jointext(in_sel, " + ")]: [length(Selected)] selected." : "Group [N[1]]: [length(Selected)] selected.")
	return length(want)

Player/proc/RemasterGroupUngroup(k)
	if(!RemasterGroupNumber(k)) return 0
	var/n = length(RemasterGroupMembers(k))
	vars["Group[k]"] = list()
	remaster_group_formations -= "[k]"
	if(remaster_group_recalled_number == k) remaster_group_recalled_number = 0
	if(n) RemasterNotice("Group [k] ungrouped: [n] unit\s back in the Company list.")
	return n

Player/proc/RemasterGroupOut(mob/Monsters/M)
	if(!istype(M) || M.Owner != src) return 0
	for(var/k = 1, k <= 9, k++)
		var/list/G = RemasterGroupMembers(k)
		if(!(M in G)) continue
		G -= M
		vars["Group[k]"] = G
		if(!length(G)) remaster_group_formations -= "[k]"
		RemasterNotice("[M.RemasterBareName()] is out of group [k].")
		return k
	return 0

// The Company list's cards: each group's members (UI refs) and its own formation, if it has one.
Player/RemasterControlGroupsData()
	var/list/D = ..()
	for(var/list/g in D["groups"])
		var/k = g["number"]
		var/list/refs = list()
		for(var/mob/Monsters/M in RemasterGroupMembers(k)) refs += RemasterUIRef(M)
		g["refs"] = refs
		var/list/F = remaster_group_formations["[k]"]
		var/list/mine = islist(F) && F[1] == "custom" && F[2] >= 1 && F[2] <= length(remaster_formations) ? remaster_formations[F[2]] : null
		g["formation"] = islist(F) ? (F[1] == "custom" ? (mine ? "[mine["name"]]" : "your own") : F[1]) : ""
		if(length(refs))
			var/list/S = RemasterSuppliesCached("g[k]", RemasterGroupMembers(k))
			g["supply"] = S[1]
			g["bag"] = S[2]
	return D

// A group's supplies at a glance (the user, 16:4x: "small group cards on the left that tell us the resources of each
// group; we look in the bag"; "total arrows, and medical supplies"): its arrows (in its quivers and loose), things to
// throw, medical supplies (bandages, remedies, potions), food, how many of it hold a bow; and its combined bag: what its
// members carry (not what they wear), the same things together, who has how many.
Player/proc/RemasterGroupSupplies(list/M)
	var/list/sum = list("arrows"=0, "throws"=0, "medical"=0, "food"=0, "bandages"=0, "remedies"=0, "potions"=0, "archers"=0,
		"n"=0, "hp"=0, "maxhp"=0, "hurt"=0, "bleeding"=0, "hungry"=0, "tired"=0, "fighting"=0)
	var/list/count = list()
	var/list/pic = list()
	var/list/who = list()
	for(var/mob/Monsters/U in M)
		if(U.HoldingWeapon == "Bow") sum["archers"]++
		// its health and state, as its own card's warnings say them (HUD.dm RemasterUnitData)
		sum["n"]++
		sum["hp"] += max(0, U.HP)
		sum["maxhp"] += max(1, U.MAXHP)
		if(U.HP < U.MAXHP * 0.5) sum["hurt"]++
		if(U.BloodContent < 80) sum["bleeding"]++
		if(U.Hunger <= 20) sum["hungry"]++
		if(U.Tiredness <= 20) sum["tired"]++
		if(U.remaster_attack || U.remaster_defense) sum["fighting"]++
		var/nm = U.RemasterBareName()
		var/list/carried = list()
		for(var/obj/Items/I in U)
			if(istype(I, /obj/Items/Equipment/Armour/Quiver/LeatherQuiver))
				sum["arrows"] += I:Content
				for(var/obj/Items/Arrows/A in I) carried += A
			if(I.suffix == "(Equipped)") continue
			carried += I
		for(var/obj/Items/I in carried)
			if(istype(I, /obj/Items/Arrows) && !istype(I.loc, /obj/Items/Equipment/Armour/Quiver)) sum["arrows"]++
			if(istype(I, /obj/Items/Food)) sum["food"]++
			if(RemasterThrownKind(I)) sum["throws"]++
			if(I.IsPotion == 1 && !I.IsEmpty) sum["potions"]++
			if(istype(I, /obj/Items/RemasterBandage)) sum["bandages"]++
			if(istype(I, /obj/Items/RemasterRemedy)) sum["remedies"]++
			var/k = "[I.name]"
			if(!count[k])
				if(length(count) >= 40) continue
				count[k] = 0
				pic[k] = RemasterItemIcon(I)
				who[k] = list()
			count[k]++
			var/list/W = who[k]
			W[nm] = (W[nm] || 0) + 1
	sum["medical"] = sum["bandages"] + sum["remedies"] + sum["potions"]
	sum["hp"] = round(sum["hp"])
	sum["maxhp"] = round(sum["maxhp"])
	var/list/bag = list()
	for(var/k in count)
		var/list/W = who[k]
		var/list/parts = list()
		for(var/n in W)
			if(length(parts) >= 6)          // a big selection: the first six, then how many more
				parts += "and [length(W) - 6] more"
				break
			parts += "[n] [W[n]]"
		bag += list(list(k, count[k], pic[k], jointext(parts, " · ")))
	return list(sum, bag)

// The same, kept a second (the HUD asks twice a second; server-cost: one pass, not one per update): again sooner when
// its units change.
#define RM_SUPPLY_EVERY 10
Player/var/tmp/list/rm_supply_cache
Player/proc/RemasterSuppliesCached(key, list/M)
	if(!rm_supply_cache) rm_supply_cache = list()
	var/list/refs = list()
	for(var/mob/Monsters/U in M) refs += "\ref[U]"
	var/rk = jointext(refs, ",")
	var/list/C = rm_supply_cache[key]
	if(C && C[2] == rk && world.time - C[1] < RM_SUPPLY_EVERY) return C[3]
	var/list/S = RemasterGroupSupplies(M)
	rm_supply_cache[key] = list(world.time, rk, S)
	return S
