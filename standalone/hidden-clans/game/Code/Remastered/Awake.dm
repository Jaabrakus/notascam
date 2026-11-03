// Awake land (server cost, 2026-10-23). The user: "do it how daggerfall online handles their server and their huge
// map". The map is 4 layers of 1000x1000 tiles, and every wild creature and world loop used to run on all of it, with
// nobody near: a wall-walk pass every 3 s cost 0.1-1.1 s a time (tools/tick_profile.py, reports/server-cost/).
// Now only the land near players lives in full. 16-tile chunks (WorldSave.dm's) are awake round each connected
// player's camera (further than the 3D view reaches, on its layer and the layers drawn above and below it), round
// their units and round their workshops; the map is redrawn every second. A wild creature out of it with nowhere to
// go rests (Monster AI.dm RandomWalk): no looking round for gear or a target, no wandering step. One with a
// destination (a raider marching in from its muster 35-45 tiles out, Raids.dm; a creature chasing someone; a
// caravan) walks on as before. Hunger, bleeding and healing run everywhere as before: they are cheap and nothing has
// to catch up. Nothing anyone can see is ever asleep.

#define RM_AWAKE_CHUNK 16
#define RM_AWAKE_CAMERA 24    // tiles beyond the 3D view's edge (View3D.dm remaster_3d_hw/hh, up to 50x40)
#define RM_AWAKE_UNIT 32      // tiles round each of a player's units (they see 12, Fog.dm)
#define RM_AWAKE_SHOP 16      // tiles round each of their workshops
var/rm_asleep_nap = 20       // ticks a resting creature waits before looking again (a var: Monster AI.dm reads it)
var/list/rm_awake_keep = list()   // places kept awake as if a player's unit stood there (tests)

var/list/rm_awake            // one entry per chunk, layer by layer: 1 awake
var/list/rm_awake_last       // per chunk, the world.time it was last awake (Regions.dm sleeps the tiles of quiet ones)
var/rm_awake_w = 0
var/rm_awake_h = 0
var/rm_awake_at = -100
var/list/rm_awake_shops      // player key -> their workshops, looked up every 30 s
var/rm_awake_shops_at = -1000

// Is A's land awake? Anything not on the map (carried, in a cage, being made) counts as awake.
proc/RmAwake(atom/A)
	if(!A || !isturf(A.loc)) return 1
	if(world.time - rm_awake_at >= 10) RmAwakeRefresh()
	return rm_awake[((A.z - 1) * rm_awake_h + round((A.y - 1) / RM_AWAKE_CHUNK)) * rm_awake_w + round((A.x - 1) / RM_AWAKE_CHUNK) + 1]

proc/RmAwakeRefresh()
	rm_awake_at = world.time
	rm_awake_w = round((world.maxx - 1) / RM_AWAKE_CHUNK) + 1
	rm_awake_h = round((world.maxy - 1) / RM_AWAKE_CHUNK) + 1
	rm_awake = new /list(rm_awake_w * rm_awake_h * world.maxz)
	if(length(rm_awake_last) != length(rm_awake)) rm_awake_last = new /list(length(rm_awake))
	if(world.time - rm_awake_shops_at >= 300)
		rm_awake_shops_at = world.time
		rm_awake_shops = list()
		for(var/mob/WorkShops/W in world) if(isturf(W.loc) && ismob(W.Owner) && W.Owner:client)
			var/k = W.Owner:key
			if(!rm_awake_shops[k]) rm_awake_shops[k] = list()
			rm_awake_shops[k] += W
	var/list/players = rm_grid ? list() : null   // with the unit grid: their units' chunks from it, after the loop
	for(var/client/C)
		var/Player/P = C.mob
		if(!istype(P) || !P.z) continue
		var/r = max(P.remaster_3d_hw, P.remaster_3d_hh) + RM_AWAKE_CAMERA
		RmAwakeMark(P.x, P.y, P.z, r)
		var/up = Remaster3DAbove(P.z)
		var/down = Remaster3DBelow(P.z)
		if(up) RmAwakeMark(P.x, P.y, up, r)
		if(down) RmAwakeMark(P.x, P.y, down, r)
		if(players) players += P
		else RmAwakeUnits(P)
		for(var/mob/WorkShops/W in rm_awake_shops[P.key]) if(W && isturf(W.loc)) RmAwakeMark(W.x, W.y, W.z, RM_AWAKE_SHOP)
	if(length(players)) RmAwakeUnitsGrid(players)
	for(var/atom/A in rm_awake_keep) if(A.z) RmAwakeMark(A.x, A.y, A.z, RM_AWAKE_UNIT + RM_AWAKE_CHUNK)

// Round a player's units, one mark per chunk with a unit in it: from anywhere in the chunk, so the same mark wherever
// in it the unit stands. A unit inside something counts where that is (RemasterGetTurf).
proc/RmAwakeUnits(Player/P)
	var/list/done = list()
	for(var/mob/Monsters/M in P.UnitList)
		var/turf/T = RemasterGetTurf(M)
		if(!T) continue
		var/ck = "[round((T.x - 1) / RM_AWAKE_CHUNK)],[round((T.y - 1) / RM_AWAKE_CHUNK)],[T.z]"
		if(done[ck]) continue
		done[ck] = 1
		RmAwakeMark(T.x, T.y, T.z, RM_AWAKE_UNIT + RM_AWAKE_CHUNK)   // from anywhere in the chunk

// The same from the engine's unit grid (Native.dm, RmGrid.cs: its cells are these chunks): the cells holding a unit
// of theirs, and their units inside something (a few), with no loop over every unit.
proc/RmAwakeUnitsGrid(list/players)
	var/list/cells = rm_grid_cells(players)
	if(!islist(cells))   // the grid off meanwhile (rm_grid_off(), or an engine without it): the loop over every unit
		for(var/Player/P in players) RmAwakeUnits(P)
		return
	for(var/i = 1, i + 2 <= length(cells), i += 3) RmAwakeMark(cells[i] * RM_AWAKE_CHUNK + 1, cells[i + 1] * RM_AWAKE_CHUNK + 1, cells[i + 2], RM_AWAKE_UNIT + RM_AWAKE_CHUNK)
	var/list/held = rm_grid_held(players)
	for(var/mob/Monsters/M in held)
		var/turf/T = RemasterGetTurf(M)
		if(T) RmAwakeMark(T.x, T.y, T.z, RM_AWAKE_UNIT + RM_AWAKE_CHUNK)
	if(rm_grid_verify) RmAwakeGridCompare(players, cells, held)

// Shadow mode (RM_GRID_VERIFY=1): the unit chunks by the players' unit lists against the grid's.
var/rm_grid_awake_checked = 0
var/rm_grid_awake_differ = 0
proc/RmAwakeGridCompare(list/players, list/cells, list/held)
	var/list/by_list = list()
	for(var/Player/P in players) for(var/mob/Monsters/M in P.UnitList)
		var/turf/T = RemasterGetTurf(M)
		if(T) by_list["[round((T.x - 1) / RM_AWAKE_CHUNK)],[round((T.y - 1) / RM_AWAKE_CHUNK)],[T.z]"] = 1
	var/list/by_grid = list()
	for(var/i = 1, i + 2 <= length(cells), i += 3) by_grid["[cells[i]],[cells[i + 1]],[cells[i + 2]]"] = 1
	for(var/mob/Monsters/M in held)
		var/turf/T = RemasterGetTurf(M)
		if(T) by_grid["[round((T.x - 1) / RM_AWAKE_CHUNK)],[round((T.y - 1) / RM_AWAKE_CHUNK)],[T.z]"] = 1
	rm_grid_awake_checked++
	var/list/only_list = list()
	var/list/only_grid = list()
	for(var/k in by_list) if(!by_grid[k]) only_list += k
	for(var/k in by_grid) if(!by_list[k]) only_grid += k
	if(!length(only_list) && !length(only_grid)) return
	rm_grid_awake_differ++
	if(rm_grid_awake_differ <= 20) world.log << "RMGRID|awake differs|by the unit lists only [jointext(only_list, " ")]|by the grid only [jointext(only_grid, " ")]"

// Wakes every chunk that has a tile within r tiles (square) of x, y on layer z.
proc/RmAwakeMark(x, y, z, r)
	if(z < 1 || z > world.maxz) return
	var/c0 = max(0, round((x - r - 1) / RM_AWAKE_CHUNK))
	var/c1 = min(rm_awake_w - 1, round((x + r - 1) / RM_AWAKE_CHUNK))
	var/r0 = max(0, round((y - r - 1) / RM_AWAKE_CHUNK))
	var/r1 = min(rm_awake_h - 1, round((y + r - 1) / RM_AWAKE_CHUNK))
	var/base = (z - 1) * rm_awake_h
	for(var/cy = r0, cy <= r1, cy++)
		var/row = (base + cy) * rm_awake_w + 1
		for(var/cx = c0, cx <= c1, cx++)
			rm_awake[row + cx] = 1
			rm_awake_last[row + cx] = world.time
