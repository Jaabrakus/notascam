// Far steps (owner fix 4, 10-27: "At larger scale, give units nobody is watching cheaper, coarser step... fix them",
// "Just do the fixes"; reports/movement-fixes/far-steps/DESIGN.md). Walking was the biggest server cost at 2,000 workers
// and the one-tile step itself most of it: the walk loop's look, the mob Move and turf Enter chains, the 2006 ground
// code, facing and the 3D move record, for every tile of every walk, watched or not.
// Now a unit nobody is watching, on a job's own task or a delivery along its route, takes up to rm_fs_max route tiles
// in one look of its walk loop and then waits as long as those steps take (WalkLoop.dm): the same pace, the same tick
// at every tile it stops on, the same arrival at its route's end. Each tile it passes is a legal step, checked cheaply
// here; the hop stops before the first tile that fails or needs the full step (a door, stairs or a wall walk, a road,
// ground whose 2006 code does something, a trap, a beast's foot, gas or fire, anyone not of its side), never lands on
// a friend's tile or on its route's last tile, and lands through the game's own Move (turf Enter, mob Move: the rules
// stay there). The tiles passed skip all per-step work, the visual kind included.
// Watched: within a margin of what a connected player's camera shows (their 3D view's area, on its layer and the layers
// drawn above and below it, plus RM_FS_MARGIN), for RM_FS_HOLD after the camera left; near a unit of another owner;
// fighting or struck lately; on a player's own order. A camera that jumps wakes the far units it now shows, so they
// step tile by tile at once and nobody sees a hop.

#define RM_FS_CHUNK 16      // the chunks watched are awake land's (Awake.dm) and the unit grid's (RmGrid.cs)
#define RM_FS_MARGIN 24     // tiles beyond the 3D view's edge still watched (fog circles 12-18 tiles, the 3D reach)
#define RM_FS_INNER 8       // tiles beyond it: a chunk this near the view that wasn't watched (the camera jumped) wakes its far units
#define RM_FS_HOLD 50       // ticks a chunk stays watched after the camera's margin left it
#define RM_FS_FOE (REMASTER_HELP_RADIUS + 1 + rm_fs_max)   // a unit of another owner this near: watched (a fight within 8 of a friend calls it to help, Defense.dm; a blow reaches 1; a hop)
#define RM_FS_AGAIN 10      // ticks a unit found watched or near a foe takes tile-by-tile steps before it is looked at again
#define RM_FS_HIT 100       // ticks after a blow taken (in a fight)
#define RM_FS_EVERY 2       // ticks between looks at the cameras

var/rm_fs_on = 1            // RM_FAR_STEPS=0: every step tile by tile, as before
var/rm_fs_max = 4           // route tiles a far unit's look takes at most (RM_FAR_STEPS_MAX): 2 s at an ordered move's pace
var/rm_fs_test_cams = 0     // tests (RM_FS_TEST_CAMS=1): a player with no client counts as a camera where it stands
var/list/rm_fs_cams         // ...those players
var/rm_fs_cams_at = -1000
var/rm_fs_env = 0
var/list/rm_fs_watch        // per chunk, layer by layer: world.time a camera's margin last covered it
var/rm_fs_watch_at = -1000
var/rm_fs_w = 0
var/rm_fs_h = 0
var/rm_fs_booked = 0        // the camera look is on the world clock (UnitClock.dm "FarSteps")
var/rm_fs_last_hop = -1000
var/list/rm_fs_never = list("Dragon", "Spider", "Golem", "Vampire", "Svartalfar")   // beasts and golems (feet, jaws), the sun-shy (SunLight per tile)
var/list/rm_fs_ground_fx = list("DeadGrass"=1, "Marsh"=1, "Tropical1"=1, "Tropical2"=1, "Tropical3"=1, "Tropical4"=1, "Tropical5"=1, "HellFloor"=1, "Desert"=1, "Snow"=1, "Sky"=1, "Chasm"=1)   // ground whose 2006 Entered code does something (Turfs.dm)
// counts, for tests and reports (RmFsStats)
var/rm_fs_looks = 0         // walk-loop looks of units on a job's route
var/rm_fs_hops = 0          // coarse steps taken
var/rm_fs_tiles = 0         // route tiles they covered
var/rm_fs_refused = 0       // coarse steps the game's Move refused (route put back, a normal step instead)
var/rm_fs_woken = 0         // far units a camera's jump woke
var/rm_fs_count = 0         // RM_FS_COUNT=1: why looks didn't take a coarse step (rm_fs_why, in RmFsStats)
var/list/rm_fs_why = list()
var/rm_fs_tile_why
mob/Monsters/var/tmp/rm_fs_hop = 0     // tiles its last look's coarse step took: WalkLoop.dm waits their steps
mob/Monsters/var/tmp/rm_fs_step = 0    // one route step's time in that wait
mob/Monsters/var/tmp/rm_fs_until = 0   // when that wait ends
mob/Monsters/var/tmp/rm_fs_far = 0     // a far unit's step is under way (the step's purely visual work can be skipped)
mob/Monsters/var/tmp/rm_fs_next = 0    // found watched or near a foe: tile by tile until then, with no look

proc/RmFsEnv()
	rm_fs_env = 1
	if(world.GetConfig("env", "RM_FAR_STEPS") == "0") rm_fs_on = 0
	var/m = text2num(world.GetConfig("env", "RM_FAR_STEPS_MAX"))
	if(m >= 1) rm_fs_max = round(m)
	if(world.GetConfig("env", "RM_FS_TEST_CAMS") == "1") rm_fs_test_cams = 1
	if(world.GetConfig("env", "RM_FS_COUNT") == "1") rm_fs_count = 1

// --- Watched ------------------------------------------------------------------------------------------------------

// Is M's place watched by a camera (now, or within RM_FS_HOLD)?
proc/RmFsWatched(mob/Monsters/M)
	if(world.time - rm_fs_watch_at >= RM_FS_EVERY) RmFsWatchRefresh()
	var/turf/T = M.loc
	var/v = rm_fs_watch[((T.z - 1) * rm_fs_h + round((T.y - 1) / RM_FS_CHUNK)) * rm_fs_w + round((T.x - 1) / RM_FS_CHUNK) + 1]
	return !isnull(v) && world.time - v <= RM_FS_HOLD

// The cameras' chunks marked with the time. A chunk near a view that wasn't watched (the camera jumped there, or a
// player came in) wakes its far units.
proc/RmFsWatchRefresh()
	rm_fs_watch_at = world.time
	var/w = round((world.maxx - 1) / RM_FS_CHUNK) + 1
	var/h = round((world.maxy - 1) / RM_FS_CHUNK) + 1
	if(w != rm_fs_w || h != rm_fs_h || length(rm_fs_watch) != w * h * world.maxz)
		rm_fs_w = w
		rm_fs_h = h
		rm_fs_watch = new /list(w * h * world.maxz)
	var/list/fresh = list()
	for(var/client/C)
		var/Player/P = C.mob
		if(istype(P) && P.z) RmFsCamera(P, fresh)
	if(rm_fs_test_cams)   // tests: the players with no client, looked up every 10 s (not a walk over the world every look)
		if(!rm_fs_cams || world.time - rm_fs_cams_at >= 100)
			rm_fs_cams_at = world.time
			rm_fs_cams = list()
			for(var/Player/P in world) if(!P.client) rm_fs_cams += P
		for(var/Player/P in rm_fs_cams) if(!P.client && P.z) RmFsCamera(P, fresh)
	if(length(fresh)) RmFsWakeIn(fresh)

proc/RmFsCamera(Player/P, list/fresh)
	var/v = max(P.remaster_3d_hw, P.remaster_3d_hh)
	for(var/zz in list(P.z, Remaster3DAbove(P.z), Remaster3DBelow(P.z))) if(zz)
		RmFsMark(P.x, P.y, zz, v + RM_FS_INNER, fresh)
		RmFsMark(P.x, P.y, zz, v + RM_FS_MARGIN)

// Marks every chunk with a tile within r (square) of x, y on layer zz; given fresh, the ones not watched until now go in
// it (as x0, y0, z for each).
proc/RmFsMark(x, y, zz, r, list/fresh)
	if(zz < 1 || zz > world.maxz) return
	var/c0 = max(0, round((x - r - 1) / RM_FS_CHUNK))
	var/c1 = min(rm_fs_w - 1, round((x + r - 1) / RM_FS_CHUNK))
	var/r0 = max(0, round((y - r - 1) / RM_FS_CHUNK))
	var/r1 = min(rm_fs_h - 1, round((y + r - 1) / RM_FS_CHUNK))
	var/base = (zz - 1) * rm_fs_h
	for(var/cy = r0, cy <= r1, cy++)
		var/row = (base + cy) * rm_fs_w + 1
		for(var/cx = c0, cx <= c1, cx++)
			if(fresh)
				var/old = rm_fs_watch[row + cx]
				if(isnull(old) || world.time - old > RM_FS_HOLD) fresh += list(list(cx * RM_FS_CHUNK + 1, cy * RM_FS_CHUNK + 1, zz))
			rm_fs_watch[row + cx] = world.time

// The far units in these chunks, in the middle of a coarse step's wait: their next look now (never sooner than a step
// after their last step), tile by tile from there. From the unit grid (Native.dm); without it they look when their wait
// ends, standing until then.
proc/RmFsWakeIn(list/fresh)
	if(!rm_grid || world.time - rm_fs_last_hop > 200) return   // no far unit has stepped lately: nobody to wake
	for(var/list/C in fresh)
		var/list/G = rm_grid_units(C[1], C[2], C[1] + RM_FS_CHUNK - 1, C[2] + RM_FS_CHUNK - 1, C[3])
		if(islist(G)) for(var/mob/Monsters/M in G) if(M.rm_fs_until > world.time) M.RmFsWake()

mob/Monsters/proc/RmFsWake()
	var/until = rm_fs_until
	rm_fs_until = 0
	if(rm_walk_running || rm_walk_parked || rm_walk_due != until) return   // its loop isn't in that wait any more
	rm_fs_woken++
	RmWalkLoopAt(max(world.time, remaster_stepped_at + max(1, rm_fs_step)))

// The cameras looked at every RM_FS_EVERY ticks while far units step (a jump wakes them), on the world clock.
proc/RmFsTick()
	if(world.time - rm_fs_last_hop > 200)
		rm_fs_booked = 0
		return
	RmClockWorldBook("FarSteps", RM_FS_EVERY)
	if(world.time - rm_fs_watch_at >= RM_FS_EVERY) RmFsWatchRefresh()

// --- The coarse step (the walk loop's look: WalkTick) --------------------------------------------------------------

// Included before WalkLoop.dm, so the walk tick's profiler wraps this too.
mob/Monsters/WalkTick()
	if(!rm_fs_on || !destination) return ..()
	var/h = RmFsHop()
	if(h > 0) return
	if(!h) return ..()
	rm_fs_far = 1   // far, this step tile by tile all the same (a door, a road, its route's end near)
	. = ..()
	rm_fs_far = 0

// Up to rm_fs_max tiles of its route at once, when nobody watches it: the tiles it took; -1 nobody watches it but this
// step is tile by tile (a tile on needs the full step); 0 watched, or not on a route walk of its own.
mob/Monsters/proc/RmFsHop()
	if(!rm_fs_env) RmFsEnv()
	if(!rm_fs_on || world.time < rm_fs_next) return 0
	// a job's own task or a delivery walking its route, nothing else on (as Formations.dm RmJobRouteStep)
	if(remaster_attack || remaster_defense || remaster_care || remaster_paused || remaster_wait_for_resume) return 0
	if((remaster_active && !remaster_active.automatic) || remaster_patrol) return 0   // a player's own order, or a guard on its rounds: watched
	var/datum/remaster_order/O = remaster_delivery || remaster_active
	if(!O || O.group) return 0
	var/list/path = O.path
	var/np = length(path)
	if(np < 3 || path[1] != destination || !isturf(loc)) return 0
	if(rm_prof)
		var/t0 = RmProfIn()
		var/w0 = world.time
		. = RmFsHopBody(O, path, np)
		RmProf("creature walk tick/far step", t0, w0)
		return
	return RmFsHopBody(O, path, np)

mob/Monsters/proc/RmFsHopBody(datum/remaster_order/O, list/path, np)
	rm_fs_looks++
	var/why
	// on its feet on the ground, nothing about it that steps another way
	if(Fainted || Stunned || Sleeping || !CanWalk || Flying || IsMist || !density || HP <= 0 || Wagon || OnFire || CliffClimber || InHole) why = "its state"
	else if(z == SKY_LAYER || rm_bound || rm_cap_state || rm_cap_leading || rm_dragging || rm_feet || CanBeSlaved || Coldness) why = "the sky level, bound, dragging, cold or warm"
	else if(remaster_ko_until > world.time || remaster_slow_until > world.time || remaster_root_until > world.time || world.time - rm_hit_at < RM_FS_HIT) why = "out cold, slowed, rooted or struck"
	else if((Race in rm_fs_never) || !istype(Owner, /Player)) why = "its race or owner"
	else if(RmFsWatched(src)) why = "watched"
	else if(rm_foe_near(src, RM_FS_FOE, /mob/Monsters)) why = "another owner's unit near"
	if(why == "watched" || why == "another owner's unit near") rm_fs_next = world.time + RM_FS_AGAIN
	if(why)
		if(rm_fs_count) rm_fs_why[why] = (rm_fs_why[why] || 0) + 1
		return 0
	// the tiles: each a legal step from the one before; lands on the last open one (never a friend's, never the route's end)
	var/list/side = RmSide(src)
	var/turf/prev = loc
	var/land = 0
	var/top = min(rm_fs_max, np - 1)
	for(var/i = 1, i <= top, i++)
		var/turf/T = path[i]
		var/w = RmFsTile(T, prev, side)
		if(!w)
			if(rm_fs_count) why = "tile [i]: [rm_fs_tile_why]"
			break
		if(w == 1) land = i
		prev = T
	if(land < 2)
		if(rm_fs_count)
			if(!why) why = top < 2 ? "route ends" : "no open tile to land on"
			rm_fs_why[why] = (rm_fs_why[why] || 0) + 1
		return -1
	var/turf/L = path[land]
	var/turf/before = path[land - 1]
	var/s = RmJobRouteStep(max(1, Delay))   // a step's time on the tiles passed (no road on them, nothing slowing it)
	var/list/passed = path.Copy(1, land)
	var/turf/was_at = loc
	path.Cut(1, land)          // its route from where it lands, as the Move chain's next step reads it (RemasterChainStep)
	destination = L
	rm_fs_far = 1              // the Move chain skips the 3D glide record (Chains/Move.dm)
	Move(L, get_dir(before, L))
	rm_fs_far = 0
	if(loc != L)   // refused after all: its route as it was, and a normal step
		rm_fs_refused++
		if(O.path == path && length(path) && path[1] == L)
			path.Insert(1, passed)
			destination = path[1]
		else if(destination == L) destination = null   // its route changed meanwhile (a bump): the orders pass gives it the next tile
		return -1
	// the ground's own step code for each tile passed, with the unit as usr as on its own steps (Turfs.dm turf/grounds/
	// Entered: on these tiles a no-op today, a step counted for the ground's timer once step-cost's lands)
	var/turf/T0 = was_at
	for(var/turf/T in passed)
		usr = src
		T.Entered(src, T0)
		T0 = T
	if(loc == destination) destination = null   // as WalkTick: nowhere on to go yet (its route's next tile isn't open)
	rm_fs_hop = land
	rm_fs_step = s
	rm_fs_hops++
	rm_fs_tiles += land
	rm_fs_last_hop = world.time
	if(!rm_fs_booked)
		rm_fs_booked = 1
		RmClockWorldBook("FarSteps", RM_FS_EVERY)
	return land

// A route tile one step on from prev: 0 no (or it needs the full step), 1 open, 2 only units of its side on it (gone
// through, never stopped on). Stricter than the ground's own rules (Chains/Enter.dm, Orders.dm RemasterWalkable).
mob/Monsters/proc/RmFsTile(turf/T, turf/prev, list/side)
	if(!isturf(T) || T.density || T.z != prev.z || get_dist(prev, T) != 1)
		rm_fs_tile_why = "dense or not one step on"
		return 0
	if(T.icon == 'Stairs.dmi' || T.remaster_wallwalk || T.remaster_road || T.OnFire || T.Content3 == "Liquid")
		rm_fs_tile_why = "stairs, a wall walk, a road, fire or liquid"
		return 0
	var/s = T.icon_state
	if((s && rm_fs_ground_fx[s]) || (s == "GoodGrass" && (Infects || Undead || Unholy || Race == "Demon")) || (length(rm_air_of) && rm_air_of[T]))   // gas or fire on it (Vapours.dm)
		rm_fs_tile_why = "its ground or air"
		return 0
	. = 1
	for(var/atom/movable/A in T)
		if(A == src) continue
		if(istype(A, /mob/Monsters))
			if(!RmSideUnit(A, side))
				rm_fs_tile_why = "a unit not of its side"
				return 0
			. = 2
		else if(A.density || istype(A, /obj/Items/Furniture) || istype(A, /obj/Items/Traps) || istype(A, /obj/RmBeastFoot))   // doors, beds, traps, a beast's feet
			rm_fs_tile_why = "a door, furniture, a trap or something dense"
			return 0

// Reports: the counts so far.
proc/RmFsStats()
	. = "on [rm_fs_on] max [rm_fs_max] looks [rm_fs_looks] hops [rm_fs_hops] tiles [rm_fs_tiles] refused [rm_fs_refused] woken [rm_fs_woken]"
	if(length(rm_fs_why))
		var/list/L = list()
		for(var/k in rm_fs_why) L += "[k] [rm_fs_why[k]]"
		. += "; not: [jointext(L, ", ")]"
