// Fog of war on the surface and the sky level (world-look, 2026-10-23; planning/NOTES_2026-10-23.md section 8).
// Sight comes from your units, never the camera: a soft circle round each of your units (the user, 20:1x: "more like a
// circle, like the mist"): 12 tiles, 3 more up on a wall walk, a tower or a mountain top (the sky level) and 3 more
// flying, 3 fewer at night unless its race sees in the dark, none when blind. Your workshops see 4. Allies share their
// sight. Each tile is never seen (a dim blue-grey mist in 3D), explored (lightly greyed: Explore.dm remembers it) or in
// sight. Other players' units, monsters and animals out of your sight are not sent to you at all; buildings you have
// seen stay drawn where you last saw them, greyed, until you see them again (rm_fog_mem, saved with you). The page
// draws the circles itself from the list sent (D["fog"]["c"]), following your units as they walk. Underground keeps
// its own line of sight (View3D.dm). A host setting turns it off for a world (remaster_fog, saved with the world).
//
// Cost: circles, no line of sight: the sources are bucketed in 16x16 cells each tick, and "can I see this tile" looks
// at the few circles in the cells round it. A source marks what it explores only when it moves to another tile, a
// row of bits at a time (no per-tile strings).

#define RM_FOG_SIGHT 12
#define RM_FOG_BUILDING 4

var/remaster_fog = 1   // the host's "Fog of war" setting (WorldSave.dm "Fog"); test worlds set it to 0
var/list/rm_fog_dark_sight = list("Dwarf", "Goblin", "Kobold", "Orc", "Vampire", "Spider", "Dragon")   // see as well by night

Player/var
	list/rm_fog_mem                  // "z" -> ("x,y" -> list of remembered building records): seen buildings, saved
Player/var/tmp
	list/rm_fog_circles              // your side's circles (list(x, y, z, r, the unit's HUD ref, its owner) a source)
	list/rm_fog_cells                // "cx,cy,z" (16x16 cells) -> list of those circles
	rm_fog_ver = 0                   // bumps when your sight changes
	rm_fog_clock = -1                // world.time your side's sight was built
	rm_fog_build = 0                 // which of its builds you are up to date with
	rm_fog_sight = 0                 // its sight's number: the same while what you see is (View3D.dm's move rows)
	rm_fog_mem_side                  // the side whose shared memory your remaster_explored and rm_fog_mem are (step C)
	rm_fog_bits_key
	rm_fog_bits

proc/RmFogOn(zz)
	return remaster_fog && (zz == GROUND_LAYER || zz == SKY_LAYER)

// How far a source sees.
proc/RmFogRadius(atom/movable/S)
	if(istype(S, /mob/WorkShops)) return RM_FOG_BUILDING
	var/mob/Monsters/M = S
	if(!M.CanSee) return 0
	var/r = RM_FOG_SIGHT
	if(M.z == SKY_LAYER) r += 3        // up on a wall walk, a tower or a mountain top
	if(M.Flying) r += 3
	if(night && !(M.Race in rm_fog_dark_sight)) r -= 3
	return r

// The players whose sight you share.
Player/proc/RmFogAllies()
	. = list()
	for(var/Player/O in Players) if(O != src && RemasterAllied(src, O)) . += O

// Everything that gives a side sight: its members' units and workshops (the workshops looked up every few seconds).
proc/RmFogSources(list/who, datum/rm_fog_side/D)
	var/list/now = list()
	for(var/Player/P in who)
		for(var/mob/Monsters/M in P.UnitList)
			if(M.Owner != P || !isturf(M.loc) || M.Egg || M.HP <= 0) continue
			now[M] = 1
	for(var/S in RmFogExtra(who, D)) now[S] = 1
	return now

// The sources that aren't units, in order: the side's workshops (looked up every few seconds) and its ships with people
// aboard (Ships.dm). Few, so looked at on every build.
proc/RmFogExtra(list/who, datum/rm_fog_side/D)
	. = list()
	if(world.time - D.shops_at > 50 || !D.shops)
		D.shops_at = world.time
		D.shops = list()
		for(var/mob/WorkShops/W in world) if(isturf(W.loc) && (W.Owner in who)) D.shops += W
	for(var/mob/WorkShops/W in D.shops) if(W && isturf(W.loc)) . += W
	for(var/mob/Monsters/RemasterSiege/Ship/S in rm_ships) if(S && isturf(S.loc) && (S.Owner in who) && (locate(/mob/Monsters) in S)) . += S

// Marks a circle explored, a row of chunk bits at a time (Explore.dm's memory: 16x16 chunks, one 16-bit number a row).
// On an engine of native version 32 the engine marks it (rm_fog_mark, RmFog.cs: the same marks; the owner, 10-31: "does
// things multiple itmes"; ~360 circles a second with 2,000 units on orders, ~50 us each here); RmFogMarkRows is the DM.
var/rm_fog_native = rm_native_version() >= 32 && world.GetConfig("env", "RM_FOG_NATIVE") != "0"
Player/proc/RmFogMarkCircle(cx, cy, zz, r)
	if(!remaster_explored) remaster_explored = list()
	var/list/L = remaster_explored["[zz]"]
	if(!L)
		L = list()
		remaster_explored["[zz]"] = L
	if(rm_fog_native)
		if(rm_once_verify) return RmFogMarkVerify(L, cx, cy, r)
		. = rm_fog_mark(L, cx, cy, r, world.maxx, world.maxy)
		if(!isnull(.)) return
	return RmFogMarkRows(L, cx, cy, r)

// RM_ONCE_VERIFY: the chunks the circle reaches copied and marked the DM way, then the map marked by the engine; the two
// must agree (what it answers, every row of those chunks, the chunks it made)
proc/RmFogMarkVerify(list/L, cx, cy, r)
	var/list/C = list()
	var/y0 = max(1, cy - r)
	var/y1 = min(world.maxy, cy + r)
	var/x0 = max(1, cx - r)
	var/x1 = min(world.maxx, cx + r)
	for(var/chy = round((y0 - 1) / 16), chy <= round((y1 - 1) / 16), chy++)
		for(var/chx = round((x0 - 1) / 16), chx <= round((x1 - 1) / 16), chx++)
			var/list/rows = L["[chx],[chy]"]
			if(rows) C["[chx],[chy]"] = rows.Copy()
	var/n = length(L)
	var/c = length(C)
	var/a = RmFogMarkRows(C, cx, cy, r)
	var/b = rm_fog_mark(L, cx, cy, r, world.maxx, world.maxy)
	if(isnull(b)) b = RmFogMarkRows(L, cx, cy, r)
	var/bad = a != b || length(L) - n != length(C) - c
	for(var/ck in C)
		var/list/rows = L[ck]
		if(!islist(rows) || jointext(rows, ",") != jointext(C[ck], ",")) bad = 1
	RmOnceCheck("fog", bad, "[cx],[cy] r [r]: [a] [b]")
	return b

proc/RmFogMarkRows(list/L, cx, cy, r)
	var/added = 0
	var/gy = -1
	var/list/gx      // this chunk row's chunks' rows, by chx + 1: a chunk looked up once a circle, not once a row (server cost)
	for(var/y = max(1, cy - r), y <= min(world.maxy, cy + r), y++)
		var/half = round(sqrt(max(0, r * r - (y - cy) * (y - cy))))
		var/x0 = max(1, cx - half)
		var/x1 = min(world.maxx, cx + half)
		var/row = ((y - 1) % 16) + 1
		var/chy = round((y - 1) / 16)
		if(chy != gy)
			gy = chy
			gx = new/list(round((world.maxx - 1) / 16) + 1)
		for(var/x = x0, x <= x1)
			var/chx = round((x - 1) / 16)
			var/end = min(x1, chx * 16 + 16)
			var/list/rows = gx[chx + 1]
			if(!rows)
				var/ck = "[chx],[chy]"
				rows = L[ck]
				if(!rows)
					rows = list(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)
					L[ck] = rows
				gx[chx + 1] = rows
			var/lo = (x - 1) % 16
			var/hi = (end - 1) % 16
			var/bits = ((1 << (hi + 1)) - 1) & ~((1 << lo) - 1)
			if((rows[row] & bits) != bits)
				rows[row] |= bits
				added = 1
			x = end + 1
	return added

// Sides (2026-10-24, the user: "team sight computed once"; planning/WORLD_SIGHT_PLAN.md step A). Everyone who shares
// sight (one alliance root, RemasterRootKey; a player alone is a side of one) has its circles built once, by whichever
// member's 3D tick comes first, and the others reuse them while they are younger than one track period (each player's
// track runs on its own clock, Spread.dm). A member's rm_fog_circles, cells, near and ask point at its side's lists.
#define RM_FOG_SHARE REMASTER_TRACK_DELAY
var/list/rm_fog_sides = list()     // side key -> /datum/rm_fog_side
var/rm_fog_sides_swept = 0
var/rm_fog_sight_serial = 0

/datum/rm_fog_side
	var/key
	var/list/members               // the players it was last built for
	var/list/circles               // list(x, y, z, r, the unit's HUD ref, its owner) for each source
	var/list/cells                 // "cx,cy,z" (16x16 cells) -> list of those circles
	var/list/near                  // RmFogLook's gathered circles
	var/list/ask                   // RmFogSees' answers
	var/list/now                   // source -> its circle
	var/clock = -1                 // world.time it was built
	var/build = 0
	var/sight = 0                  // new (rm_fog_sight_serial) whenever a source's circle changed, came or went
	var/reach = 1                  // cells round a look (two when a sight is over 16: flying, up high)
	var/list/shops                 // its members' workshops
	var/shops_at = -100
	var/list/explored              // its one explored map (Explore.dm's format), every member's remaster_explored
	var/list/mem                   // its remembered buildings (rm_fog_mem's format), every member's rm_fog_mem
	var/list/marked                // source -> "x,y,z,r" it last marked explored from
	var/list/at                    // source -> its place in circles (a build that keeps the sources keeps the places)
	var/list/extra                 // the sources that aren't units, in order, at the last build (RmFogExtra)
	var/maxr = 0                   // the widest sight among the circles
	var/night = -1                 // night as the circles were made (a sight's reach reads it)

Player/proc/RmFogSideKey()
	return key ? "[RemasterRootKey(key)]" : "\ref[src]"

// Brings your sight up to date (on the 3D tick): your side's, built now or reused, and what it explored for you.
Player/proc/RmFogTick()
	if(!remaster_fog)
		rm_fog_circles = null
		rm_fog_cells = null
		return
	if(rm_fog_circles && rm_fog_clock == world.time) return
	var/sk = RmFogSideKey()
	var/datum/rm_fog_side/D = rm_fog_sides[sk]
	if(!D)
		D = new
		D.key = sk
		rm_fog_sides[sk] = D
	var/fresh = !rm_fog_circles || rm_fog_clock < 0   // a cleared view (the host's switch, tests) is built afresh
	if(fresh || !D.circles || !(src in D.members) || world.time - D.clock >= (length(D.members) > 1 ? RM_FOG_SHARE : 1))
		RmFogBuildSide(D)
	else if(rm_fog_build == D.build) return   // up to date with it already
	rm_fog_build = D.build
	rm_fog_clock = D.clock
	rm_fog_circles = D.circles
	rm_fog_cells = D.cells
	rm_fog_near = D.near
	rm_fog_ask = D.ask
	rm_fog_ask_at = D.clock
	rm_fog_reach = D.reach
	rm_fog_sight = D.sight
	rm_fog_ver++

// A side's sight from all its members' sources (you are the member whose tick came first), bucketed in 16x16 cells for
// the "can I see" test. Sides nobody asked for in a minute are dropped.
Player/proc/RmFogBuildSide(datum/rm_fog_side/D)
	var/list/who = list(src) + RmFogAllies()
	var/same = length(D.members) == length(who)
	if(same) for(var/X in who) if(!(X in D.members)) same = 0
	if(!same) D.shops = null   // joined or left: its workshops looked up again
	RmFogSideMemory(D, who)   // one memory for the side (cheap when nothing changed)
	// built once (the owner, 10-31: "does things multiple itmes"): every source's circle was made again each build (2,000
	// units: ~10 ms of DM a game second, ~20 with the sources' walk and their sights), though only moved ones change. With
	// the sources the ones it had, in the same order, only those whose circle moved are made again (RmFogMoved)
	var/list/moved = RmFogMoved(D, who)
	D.members = who
	D.clock = world.time
	D.build++
	if(moved)
		RmFogApply(D, moved)
		if(rm_once_verify) RmFogVerify(D, who)
	else
		var/list/circles = list()
		var/list/cells = list()
		var/list/at = list()
		var/maxr = 0
		var/list/now = RmFogSources(who, D)
		for(var/atom/movable/S in now)
			var/turf/T = S.loc
			var/r = RmFogRadius(S)
			if(r > maxr) maxr = r
			var/mob/Monsters/M = istype(S, /mob/Monsters) ? S : null
			var/list/C = list(T.x, T.y, T.z, r, M ? RemasterUIRef(M) : null, M ? M.Owner : null)
			now[S] = C
			circles += list(C)
			at[S] = length(circles)
			var/ck = "[round((T.x - 1) / 16)],[round((T.y - 1) / 16)],[T.z]"
			if(!cells[ck]) cells[ck] = list()
			cells[ck] += list(C)
		D.circles = circles
		D.cells = cells
		D.now = now
		D.at = at
		D.extra = RmFogExtra(who, D)   // as RmFogSources just found them (its workshops looked up already)
		D.maxr = maxr
		D.night = night
		D.near = list()
		D.ask = list()
		D.reach = maxr > 16 ? 2 : 1   // cells are 16 wide: a sight over 16 (flying, up high: 18) reaches two cells off
		moved = now
	// what the side explored: a source's circle, once it moved since the side last marked it, into its one map
	if(!D.marked) D.marked = list()
	var/explored = 0
	var/sighted = 0
	for(var/atom/movable/S in moved)
		var/list/C = D.now[S]
		var/mk = "[C[1]],[C[2]],[C[3]],[C[4]]"
		if(D.marked[S] != mk)
			D.marked[S] = mk
			sighted = 1
			if(RmFogOn(C[3]) && RmFogMarkCircle(C[1], C[2], C[3], C[4])) explored = 1   // the fog's levels only: underground is explored by line of sight (Explore.dm; the user, 2026-10-25: no marks through rock)
			if(C[3] == SKY_LAYER && RmFogMarkCircle(C[1], C[2], GROUND_LAYER, C[4])) explored = 1   // from up high, the ground below too
	if(moved == D.now) for(var/S in D.marked.Copy()) if(!D.now[S])   // a build in full: the sources gone since
		D.marked -= S
		sighted = 1
	if(sighted) D.sight = ++rm_fog_sight_serial   // the circles (RmFogLook's only reads) are what they were otherwise
	if(explored) RmFogExploredNew()
	if(world.time - rm_fog_sides_swept > 600)
		rm_fog_sides_swept = world.time
		for(var/k in rm_fog_sides.Copy())
			var/datum/rm_fog_side/E = rm_fog_sides[k]
			if(E != D && world.time - E.clock > 600) rm_fog_sides -= k

// The sources whose circle moved since the side's last build, or null for a build in full: the first, other members or
// another order of them (the circles' order follows the members'), night come or gone, a source come or gone (a unit
// made one or no longer one, by its own vars; the workshops and ships as RmFogExtra finds them). The units come from the
// engine (rm_list_changed, native version 33: the units whose change counter moved, from each member's list, slot 1);
// each member's list is asked every build, so the next build asks about what changed since this one.
Player/proc/RmFogMoved(datum/rm_fog_side/D, list/who)
	var/full = !rm_list_on || !D.now || !D.at || D.night != night || length(D.members) != length(who)
	if(!full) for(var/i = 1, i <= length(who), i++) if(who[i] != D.members[i]) full = 1
	var/list/moved = list()
	for(var/Player/P in who)
		var/list/R = rm_list_on ? rm_list_changed(P, 1, P.UnitList, 0) : null
		if(full) continue
		if(!R || R[3])
			full = 1
			continue
		for(var/mob/Monsters/M in R[1])
			var/list/C = D.now[M]
			var/is = M.Owner == P && isturf(M.loc) && !M.Egg && M.HP > 0
			if(!is != !C) full = 1   // come or gone
			else if(C && RmFogCircleMoved(M, C)) moved += M
	if(full) return null
	var/list/extra = RmFogExtra(who, D)
	if(length(extra) != length(D.extra)) return null
	for(var/i = 1, i <= length(extra), i++)
		var/atom/movable/S = extra[i]
		if(S != D.extra[i]) return null
		if(RmFogCircleMoved(S, D.now[S])) moved += S
	return moved

// Whether a source's circle (list(x, y, z, r, its HUD ref, its owner)) is no longer where and what it is.
proc/RmFogCircleMoved(atom/movable/S, list/C)
	var/turf/T = S.loc
	if(T.x != C[1] || T.y != C[2] || T.z != C[3] || RmFogRadius(S) != C[4]) return 1
	var/mob/Monsters/M = istype(S, /mob/Monsters) ? S : null
	return C[6] != (M ? M.Owner : null)

// Those circles made again in copies of the side's lists, the rest as they were (the same lists, in the same order; a
// member still on the last build's lists keeps them as they were). Nothing moved: nothing new.
Player/proc/RmFogApply(datum/rm_fog_side/D, list/moved)
	if(!length(moved)) return
	var/list/circles = D.circles.Copy()
	var/list/cells = D.cells.Copy()
	var/list/now = D.now.Copy()
	var/list/copied = list()   // the cells whose lists were copied this build
	var/maxr = D.maxr
	var/again = 0
	for(var/atom/movable/S in moved)
		var/list/O = now[S]
		var/turf/T = S.loc
		var/r = RmFogRadius(S)
		var/mob/Monsters/M = istype(S, /mob/Monsters) ? S : null
		var/list/C = list(T.x, T.y, T.z, r, O[5], M ? M.Owner : null)   // its HUD ref is its own for good
		now[S] = C
		circles[D.at[S]] = C
		if(r > maxr) maxr = r
		else if(O[4] == maxr && r < maxr) again = 1
		var/ocx = round((O[1] - 1) / 16)
		var/ocy = round((O[2] - 1) / 16)
		var/ok = "[ocx],[ocy],[O[3]]"
		var/stay = ocx == round((T.x - 1) / 16) && ocy == round((T.y - 1) / 16) && O[3] == T.z
		var/list/L = cells[ok]
		if(!copied[ok])
			L = L.Copy()
			cells[ok] = L
			copied[ok] = 1
		var/j = L.Find(O)   // the engine's search (a list given to Find is the one thing looked for)
		if(stay)
			L[j] = C
			continue
		L.Cut(j, j + 1)
		var/nk = "[round((T.x - 1) / 16)],[round((T.y - 1) / 16)],[T.z]"
		if(!length(L)) cells -= ok
		var/list/N = cells[nk]
		if(!N)
			N = list()
			cells[nk] = N
			copied[nk] = 1
		else if(!copied[nk])
			N = N.Copy()
			cells[nk] = N
			copied[nk] = 1
		N += list(C)
	if(again)
		maxr = 0
		for(var/list/C in circles) if(C[4] > maxr) maxr = C[4]
	D.circles = circles
	D.cells = cells
	D.now = now
	D.maxr = maxr
	D.near = list()
	D.ask = list()
	D.reach = maxr > 16 ? 2 : 1

// RM_ONCE_VERIFY: the side's circles as a build in full would make them (its sources, their circles in order, each cell's)
Player/proc/RmFogVerify(datum/rm_fog_side/D, list/who)
	var/list/F = list()
	var/list/cells = list()
	var/maxr = 0
	var/list/now = list()
	for(var/Player/P in who) for(var/mob/Monsters/M in P.UnitList)
		if(M.Owner != P || !isturf(M.loc) || M.Egg || M.HP <= 0) continue
		now[M] = 1
	for(var/S in D.extra) now[S] = 1
	for(var/atom/movable/S in now)
		var/turf/T = S.loc
		var/r = RmFogRadius(S)
		if(r > maxr) maxr = r
		var/mob/Monsters/M = istype(S, /mob/Monsters) ? S : null
		var/list/C = list(T.x, T.y, T.z, r, M ? RemasterUIRef(M) : null, M ? M.Owner : null)
		F += list(C)
		var/ck = "[round((T.x - 1) / 16)],[round((T.y - 1) / 16)],[T.z]"
		if(!cells[ck]) cells[ck] = list()
		cells[ck] += "[json_encode(C)]"
	var/bad = json_encode(F) != json_encode(D.circles) || (maxr > 16 ? 2 : 1) != D.reach || length(cells) != length(D.cells)
	var/k = 1
	for(var/S in now)
		if(D.now[S] != D.circles[k] || D.at[S] != k) bad = 1
		k++
	if(!bad) for(var/ck in cells)
		var/list/A = cells[ck]
		var/list/B = list()
		for(var/list/C in D.cells[ck]) B += "[json_encode(C)]"
		if(length(A) != length(B)) bad = 1
		else for(var/c in A) if(!(c in B)) bad = 1
	RmOnceCheck("fogside", bad, "[length(F)] sources")

// Seen-before memory per side (2026-10-24, the user: "merge on join, each keeps everything at war"; the plan's step C).
// While allied, every member's remaster_explored and rm_fog_mem are the side's one map and one list, so a circle is
// marked once for all of them and each save holds it all. Someone who comes in has what they had seen OR-merged in; a
// member who left (or went to war) takes a full copy, before the side marks again. On load, sides form again this way.
Player/proc/RmFogSideMemory(datum/rm_fog_side/D, list/who)
	for(var/Player/F in D.members)   // gone since the last build: their own copy of everything up to now
		if(!(F in who) && F.rm_fog_mem_side == D.key && F.remaster_explored == D.explored)
			F.remaster_explored = RmFogCopyExplored(D.explored)
			F.rm_fog_mem = RmFogCopyMem(D.mem)
			F.rm_fog_mem_side = null
	var/added = 0
	for(var/Player/P in who)
		if(P.rm_fog_mem_side == D.key && D.explored && P.remaster_explored == D.explored) continue
		var/theirs = P.rm_fog_mem_side == null || P.rm_fog_mem_side == D.key   // not another side's shared lists
		if(!D.explored)
			D.explored = theirs && P.remaster_explored ? P.remaster_explored : RmFogCopyExplored(P.remaster_explored)
			D.mem = theirs && P.rm_fog_mem ? P.rm_fog_mem : RmFogCopyMem(P.rm_fog_mem)
		else
			if(RmFogMergeExplored(D.explored, P.remaster_explored)) added = 1
			RmFogMergeMem(D.mem, P.rm_fog_mem)
		P.remaster_explored = D.explored
		P.rm_fog_mem = D.mem
		P.rm_fog_mem_side = D.key
		P.remaster_explore_version++
	if(added) for(var/Player/P in who) P.remaster_explore_version++

// Something new explored: everyone sharing the map redraws it (their minimaps and 3D bits are kept by version).
Player/proc/RmFogExploredNew()
	var/datum/rm_fog_side/D = rm_fog_mem_side ? rm_fog_sides[rm_fog_mem_side] : null
	if(!D || D.explored != remaster_explored)
		remaster_explore_version++
		return
	for(var/Player/P in D.members) if(P.remaster_explored == D.explored) P.remaster_explore_version++

proc/RmFogCopyExplored(list/E)
	. = list()
	if(!E) return
	for(var/zk in E)
		var/list/L = E[zk]
		var/list/N = list()
		for(var/ck in L)
			var/list/rows = L[ck]
			N[ck] = rows.Copy()
		.[zk] = N

// The tiles' record lists are shared: they are replaced, never changed (RmFogRemembered).
proc/RmFogCopyMem(list/M)
	. = list()
	if(!M) return
	for(var/zk in M)
		var/list/L = M[zk]
		.[zk] = L.Copy()

// OR the explored bits of B into A; 1 if A learnt anything.
proc/RmFogMergeExplored(list/A, list/B)
	. = 0
	if(!B) return
	for(var/zk in B)
		var/list/LB = B[zk]
		var/list/LA = A[zk]
		if(!LA)
			LA = list()
			A[zk] = LA
		for(var/ck in LB)
			var/list/rb = LB[ck]
			var/list/ra = LA[ck]
			if(!ra)
				LA[ck] = rb.Copy()
				. = 1
				continue
			for(var/r = 1, r <= 16, r++)
				if(rb[r] & ~ra[r])
					ra[r] |= rb[r]
					. = 1

// B's remembered buildings for the tiles A has none for.
proc/RmFogMergeMem(list/A, list/B)
	if(!B) return
	for(var/zk in B)
		var/list/LB = B[zk]
		var/list/LA = A[zk]
		if(!LA)
			A[zk] = LB.Copy()
			continue
		for(var/tk in LB) if(!LA[tk]) LA[tk] = LB[tk]

// Is this tile in your sight now? Off the fog's levels (underground) or with fog off, always. Answers are kept for the
// tick (a big scene asks about the same tiles many times); the tile's own cell is looked at first.
Player/var/tmp/list/rm_fog_ask
Player/var/tmp/rm_fog_ask_at = -1
Player/proc/RmFogSees(turf/T)
	if(!T || !RmFogOn(T.z)) return 1
	if(!rm_fog_cells) RmFogTick()
	if(rm_fog_ask_at != rm_fog_clock)
		rm_fog_ask_at = rm_fog_clock
		rm_fog_ask = list()
	var/a = rm_fog_ask[T]
	if(!isnull(a)) return a
	a = RmFogLook(T)
	rm_fog_ask[T] = a
	return a

// The circles of a cell and the eight round it are gathered once a fog tick (rm_fog_near), so a look makes one key a
// level, not nine (server cost, 2026-10-24: the 3D list asks for every thing in view).
Player/var/tmp/list/rm_fog_near    // "cx,cy,z" -> the circles in that cell and the eight round it, this fog tick
Player/var/tmp/rm_fog_reach = 1    // how many cells round a look walks (RmFogTick)
Player/proc/RmFogLook(turf/T)
	var/cx = round((T.x - 1) / 16)
	var/cy = round((T.y - 1) / 16)
	if(!rm_fog_near) rm_fog_near = list()
	for(var/zz in (T.z == SKY_LAYER ? list(SKY_LAYER, GROUND_LAYER) : list(T.z, SKY_LAYER)))   // the sky sees down onto the ground
		var/nk = "[cx],[cy],[zz]"
		var/list/near = rm_fog_near[nk]
		if(!near)
			near = list()
			for(var/dy = -rm_fog_reach, dy <= rm_fog_reach, dy++)   // the cell and all eight round it (or two rings)
				for(var/dx = -rm_fog_reach, dx <= rm_fog_reach, dx++)
					var/list/L = rm_fog_cells["[cx + dx],[cy + dy],[zz]"]
					if(L) near += L
			rm_fog_near[nk] = near
		for(var/list/C in near)
			var/ex = C[1] - T.x
			var/ey = C[2] - T.y
			if(ex * ex + ey * ey <= C[4] * C[4] + 1) return 1
	return 0

// Is this unit of yours missing from your side's sight as last built (made, or come from elsewhere, since that fog tick)?
Player/proc/RmFogNotYet(mob/Monsters/M)
	if(!remaster_fog || !M || !isturf(M.loc)) return 0
	var/datum/rm_fog_side/D = rm_fog_sides[RmFogSideKey()]
	if(!D || !D.now) return 1
	if(D.clock == world.time) return 0   // built this tick already
	var/list/C = D.now[M]
	return !C || C[3] != M.z || abs(C[1] - M.x) + abs(C[2] - M.y) > 2

// Can you see this creature? Your own always.
Player/proc/RmFogSeesMob(mob/Monsters/M)
	if(!M || M.Owner == src) return 1
	var/atom/T = M.loc
	while(T && !isturf(T)) T = T.loc   // in a cage or carried: where that stands
	return RmFogSees(T)

// For the page: the area's explored memory (2 explored, 0 never seen) and the sight circles near it (x, y, r, and the
// HUD ref for your own units, so the page can follow them as they walk). 0 where the fog doesn't apply. The bits are
// built again only when your memory or the area changed; the circles are sent as they are.
Player/proc/RmFogBits(x0, y0, x1, y1, zz)
	if(!RmFogOn(zz)) return 0
	var/key = "[x0],[y0],[x1],[y1],[zz],[remaster_explore_version]"
	if(key != rm_fog_bits_key)
		var/list/L = remaster_explored ? remaster_explored["[zz]"] : null
		var/list/G = (zz == SKY_LAYER && remaster_explored) ? remaster_explored["[GROUND_LAYER]"] : null
		var/list/bits = list()
		for(var/ty = y0, ty <= y1, ty++)
			var/r = ((ty - 1) % 16) + 1
			var/cy = round((ty - 1) / 16)
			var/list/rows = null
			var/list/grows = null
			var/ccx = -1
			for(var/tx = x0, tx <= x1, tx++)
				var/cx = round((tx - 1) / 16)
				if(cx != ccx)
					ccx = cx
					rows = L ? L["[cx],[cy]"] : null
					grows = G ? G["[cx],[cy]"] : null
				var/b = 1 << ((tx - 1) % 16)
				bits += ((rows && (rows[r] & b)) || (grows && (grows[r] & b))) ? "2" : "0"
		rm_fog_bits_key = key
		rm_fog_bits = jointext(bits, "")
	var/list/near = list()
	for(var/list/C in rm_fog_circles)
		if(C[1] + C[4] < x0 || C[1] - C[4] > x1 || C[2] + C[4] < y0 || C[2] - C[4] > y1) continue
		if(C[3] != zz && !(C[3] == SKY_LAYER && zz == GROUND_LAYER)) continue
		near += list(list(C[1], C[2], C[4], C[6] == src ? C[5] : null))   // the HUD ref for your own units only
	return list("x0"=x0, "y0"=y0, "w"=x1 - x0 + 1, "h"=y1 - y0 + 1, "z"=zz, "s"=rm_fog_bits, "c"=near)

// Remembered buildings: what a tile held when you last saw it.
Player/proc/RmFogMemTile(zz)
	if(!rm_fog_mem) rm_fog_mem = list()
	var/list/M = rm_fog_mem["[zz]"]
	if(!M)
		M = list()
		rm_fog_mem["[zz]"] = M
	return M

// Called by Remaster3DThings with the buildings seen live this tick (tile key -> list of records) and the area;
// updates the memory for tiles in sight and returns the remembered ones for tiles out of sight, greyed ("mem").
Player/proc/RmFogRemembered(list/live, zz, x0, y0, x1, y1)
	var/list/out = list()
	var/list/M = RmFogMemTile(zz)
	for(var/tk in live) M[tk] = live[tk]
	for(var/tk in M.Copy())
		var/list/xy = splittext(tk, ",")
		var/tx = text2num(xy[1])
		var/ty = text2num(xy[2])
		if(tx < x0 || tx > x1 || ty < y0 || ty > y1) continue
		var/turf/T = locate(tx, ty, zz)
		if(RmFogSees(T))
			if(!live[tk]) M -= tk   // seen again and gone
			continue
		for(var/list/D in M[tk])
			var/list/C = D.Copy()
			C["mem"] = 1
			C["nopick"] = 1   // a picture of what was there, not the thing
			out += list(C)
	return out

// The host's setting: "Fog of war" on or off for this world.
Player/proc/RmFogSet(on)
	if(!RemasterIsHost() && (fexists("host-name") || RmPublicWorld()))
		RemasterNotice("Only the host can change fog of war.")
		return
	remaster_fog = on ? 1 : 0
	rm_fog_sides = list()
	for(var/Player/P in Players)
		P.rm_fog_circles = null
		P.rm_fog_cells = null
		P.rm_fog_bits_key = null
		P.remaster_3d_key = null
	RemasterNotice(remaster_fog ? "Fog of war is on: you see what your units see." : "Fog of war is off: you see everything round the camera.")

// The HUD's switch (Settings, the host only): "fogofwar" with 1 or 0.
Player/RemasterTouchCommand(action, value)
	if(action == "fogofwar")
		RmFogSet(value == "1")
		return 1
	return ..()

// An attack whose target walks out of your sight goes on to where it was last seen, then stops (or, on an attack-move,
// carries on with the move). Called from Attack.dm's tick; 1 when it handled the tick.
// A new order's target was in sight when it was chosen (clicked in your view, or picked from the unit's own), so its tile
// is where it was last seen. And an attacker made or come since your side's sight was built (it isn't in it yet) gets
// that sight built again, once an order, before its target counts as lost (server-cost, 2026-10-25: such an order
// dropped at once, Idle with no step).
datum/remaster_attack/var/turf/rm_last_seen
datum/remaster_attack/var/rm_fog_new = 1        // not looked at by the fog yet
datum/remaster_attack/var/rm_fog_looked = 0     // the side's sight built again for it once
mob/Monsters/proc/RmFogAttackLost(datum/remaster_attack/K, mob/Monsters/E)
	var/Player/P = K.issuer
	var/fresh = K.rm_fog_new
	K.rm_fog_new = 0
	if(istype(P) && !P.RmFogSeesMob(E) && !K.rm_fog_looked && P.RmFogNotYet(src))
		K.rm_fog_looked = 1
		P.rm_fog_clock = -1   // built afresh now (RmFogTick)
		P.RmFogTick()
	if(!istype(P) || P.RmFogSeesMob(E))
		if(isturf(E.loc)) K.rm_last_seen = E.loc
		return 0
	if(fresh && !K.rm_last_seen && isturf(E.loc)) K.rm_last_seen = E.loc   // just chosen: seen then
	if(length(K.pool))   // an attack box or A + click: on to the next of its foes in sight first (formations, Formations.dm)
		var/mob/Monsters/N = RemasterPoolNext()
		if(N)
			K.target = N
			K.path = null
			return 0
	var/turf/L = K.rm_last_seen
	if(L && L.z == z && get_dist(src, L) > 0 && RemasterAttackApproach(L, 0))
		remaster_order_status = "To where [RemasterCombatName(E)] was last seen"
		return 1
	K.target = null
	K.chosen = null
	K.rm_last_seen = null
	if(K.goal) return 0
	RemasterAttackStop()
	return 1
