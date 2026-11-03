// Blood pools (the owner, 10-29: "what could save perfomance is if we combine blood instead of it being seperate tiles it
// can combine to make big pools", "one big pool if blood tiles are adjencent"; the look chosen from a mock-up, "Keep splat
// detail" and "Thinner, patchier": reports/polish-night-1026/blood-pools). A 1000 v 1000 left ~9,400 splats on ~1,200
// tiles in 3 minutes, each its own object, sleeping proc and picture on the 3D page. Now a plain red splat that settles
// (obj/proc/Delete, Turfs.dm) joins the pool of its 8x8 block of ground and goes: the pool keeps, for each tile, how many
// splats fell on it, its last two pictures, and when its last splat dries (each as long as before, 150-300 s). The 3D view
// draws each block's pool as one patchy surface that runs into the blocks round it, the tiles' last two splats on it
// (View3D.dm Remaster3DBloodPool, art/hud/src/023 v3poolDraw). Acid goo, black blight, infection and zombie blood, and
// acid blood of any kind, stay splats of their own. The gravedigger cleans a pool's tiles beside it (Graves.dm); a
// container fills with blood from a pool's tile beside the unit as from a splat (Turfs.dm, RmBloodNear).
// RM_BLOOD_POOLS=0 in the server's environment: splats as before.
#define RM_BLOOD_BLOCK 8
var/rm_blood_pools_on = -1
var/list/rm_blood_pools = list()   // "bx,by,z" -> the block's pool
var/rm_blood_drying = 0
var/list/rm_blood_pool_types = list(/obj/Bloods/Blood, /obj/Bloods/Blood1, /obj/Bloods/Blood2, /obj/Bloods/Blood3, /obj/Bloods/Blood4, /obj/Bloods/Blood5)

proc/RmBloodPoolsOn()
	if(rm_blood_pools_on < 0) rm_blood_pools_on = world.GetConfig("env", "RM_BLOOD_POOLS") != "0"
	return rm_blood_pools_on

obj/Bloods/RmBloodPool
	name = "Blood"
	icon = 'Blood.dmi'
	icon_state = "1"
	var/tmp/bx
	var/tmp/by
	var/tmp/list/amt     // the block's 64 tiles (row by row from its south-west corner): splats fallen on it
	var/tmp/list/dry     // ...when its last splat dries (world.time)
	var/tmp/list/s1      // ...its last splat's picture (an icon state of Blood.dmi)
	var/tmp/list/s2      // ...and the one before
	var/tmp/n = 0        // tiles with blood
	var/tmp/ver = 0      // a write each change: the 3D view's kept entry is built again (RmVer.cs)
	New()
		return
	Read(savefile/F)
		spawn(0) del(src)   // never kept in a save: its splats were never kept either

proc/RmBloodBlockKey(x, y, z)
	return "[round((x - 1) / RM_BLOOD_BLOCK)],[round((y - 1) / RM_BLOOD_BLOCK)],[z]"

// A splat that settled on T (state: its picture) joins T's block's pool, to dry life ticks from now.
proc/RmBloodPoolAdd(turf/T, state, life)
	var/key = RmBloodBlockKey(T.x, T.y, T.z)
	var/obj/Bloods/RmBloodPool/P = rm_blood_pools[key]
	if(!P || Rm3DGone(P))
		var/bx = round((T.x - 1) / RM_BLOOD_BLOCK)
		var/by = round((T.y - 1) / RM_BLOOD_BLOCK)
		var/turf/A = locate(min(world.maxx, bx * RM_BLOOD_BLOCK + RM_BLOOD_BLOCK / 2), min(world.maxy, by * RM_BLOOD_BLOCK + RM_BLOOD_BLOCK / 2), T.z)
		P = new(A || T)
		P.bx = bx
		P.by = by
		P.amt = new/list(RM_BLOOD_BLOCK * RM_BLOOD_BLOCK)
		P.dry = new/list(RM_BLOOD_BLOCK * RM_BLOOD_BLOCK)
		P.s1 = new/list(RM_BLOOD_BLOCK * RM_BLOOD_BLOCK)
		P.s2 = new/list(RM_BLOOD_BLOCK * RM_BLOOD_BLOCK)
		rm_blood_pools[key] = P
		if(!rm_blood_drying) spawn(0) RmBloodPoolsDry()
	var/i = ((T.y - 1) % RM_BLOOD_BLOCK) * RM_BLOOD_BLOCK + (T.x - 1) % RM_BLOOD_BLOCK + 1
	if(!P.amt[i]) P.n++
	P.amt[i] = (P.amt[i] || 0) + 1
	P.dry[i] = max(P.dry[i] || 0, world.time + life)
	P.s2[i] = P.s1[i]
	P.s1[i] = state
	P.ver++

// Splats on T's tile in its pool (0 none).
proc/RmBloodPoolAt(turf/T)
	if(!T) return 0
	var/obj/Bloods/RmBloodPool/P = rm_blood_pools[RmBloodBlockKey(T.x, T.y, T.z)]
	if(!P || Rm3DGone(P) || !P.amt) return 0
	return P.amt[((T.y - 1) % RM_BLOOD_BLOCK) * RM_BLOOD_BLOCK + (T.x - 1) % RM_BLOOD_BLOCK + 1] || 0

// A tile's blood gone (cleaned): 1 if there was any.
proc/RmBloodPoolClear(turf/T)
	if(!T) return 0
	var/key = RmBloodBlockKey(T.x, T.y, T.z)
	var/obj/Bloods/RmBloodPool/P = rm_blood_pools[key]
	if(!P || Rm3DGone(P) || !P.amt) return 0
	var/i = ((T.y - 1) % RM_BLOOD_BLOCK) * RM_BLOOD_BLOCK + (T.x - 1) % RM_BLOOD_BLOCK + 1
	if(!P.amt[i]) return 0
	P.amt[i] = null
	P.dry[i] = null
	P.s1[i] = null
	P.s2[i] = null
	P.n--
	P.ver++
	if(P.n <= 0)
		rm_blood_pools -= key
		del(P)
	return 1

// Pool tiles within r of C cleaned: how many.
proc/RmBloodPoolClearNear(atom/C, r)
	. = 0
	if(!C || !length(rm_blood_pools)) return
	for(var/dy = -r, dy <= r, dy++) for(var/dx = -r, dx <= r, dx++)
		var/turf/T = locate(C.x + dx, C.y + dy, C.z)
		if(T && RmBloodPoolClear(T)) .++

// The pool tile within r of C nearest to near_to, or null.
proc/RmBloodPoolNearest(atom/C, r, atom/near_to)
	if(!C || !length(rm_blood_pools)) return null
	var/best = 1#INF
	for(var/bx = round((C.x - r - 1) / RM_BLOOD_BLOCK), bx <= round((C.x + r - 1) / RM_BLOOD_BLOCK), bx++)
		for(var/by = round((C.y - r - 1) / RM_BLOOD_BLOCK), by <= round((C.y + r - 1) / RM_BLOOD_BLOCK), by++)
			var/obj/Bloods/RmBloodPool/P = rm_blood_pools["[bx],[by],[C.z]"]
			if(!P || Rm3DGone(P) || !P.amt) continue
			for(var/i = 1, i <= RM_BLOOD_BLOCK * RM_BLOOD_BLOCK, i++) if(P.amt[i])
				var/x = bx * RM_BLOOD_BLOCK + (i - 1) % RM_BLOOD_BLOCK + 1
				var/y = by * RM_BLOOD_BLOCK + round((i - 1) / RM_BLOOD_BLOCK) + 1
				if(abs(x - C.x) > r || abs(y - C.y) > r) continue
				var/d = max(abs(x - near_to.x), abs(y - near_to.y))
				if(d < best)
					best = d
					. = locate(x, y, C.z)

// Blood beside M: a splat of its own in view (as the menus looked) or a pool's tile within r.
proc/RmBloodNear(mob/M, r = 1)
	for(var/obj/Bloods/B in view(r, M)) if(!istype(B, /obj/Bloods/RmBloodPool)) return 1
	if(!isturf(M.loc) || !length(rm_blood_pools)) return 0
	for(var/dy = -r, dy <= r, dy++) for(var/dx = -r, dx <= r, dx++) if(RmBloodPoolAt(locate(M.x + dx, M.y + dy, M.z))) return 1
	return 0

// Each 5 s, the tiles whose last splat dried leave their pool; an empty pool goes.
proc/RmBloodPoolsDry()
	rm_blood_drying = 1
	while(length(rm_blood_pools))
		sleep(50)
		var/list/gone = list()
		for(var/key in rm_blood_pools)
			var/obj/Bloods/RmBloodPool/P = rm_blood_pools[key]
			if(!P || Rm3DGone(P) || !P.amt)
				gone += key
				continue
			var/changed = 0
			for(var/i = 1, i <= RM_BLOOD_BLOCK * RM_BLOOD_BLOCK, i++) if(P.amt[i] && P.dry[i] <= world.time)
				P.amt[i] = null
				P.dry[i] = null
				P.s1[i] = null
				P.s2[i] = null
				P.n--
				changed = 1
			if(P.n <= 0)
				gone += key
				del(P)
			else if(changed) P.ver++
		for(var/key in gone) rm_blood_pools -= key
	rm_blood_drying = 0

// A block's blood pool for the 3D view (View3D.dm Remaster3DEntry; art/hud/src/023 v3poolDraw): "pool" = list(the block's
// first x and y, then each tile with blood: list(dx, dy, splats, its last picture, the one before) as indexes into "pt",
// the pictures' files, -1 none); "pv", its version (it changes whenever a splat joins or a tile dries).
Player/proc/Remaster3DBloodPool(obj/Bloods/RmBloodPool/P, list/D)
	if(!P.amt || P.n <= 0) return null
	D["id"] = "\ref[P]"
	D["pv"] = P.ver
	var/list/pt = list()
	var/list/at = list()
	var/list/pool = list(P.bx * RM_BLOOD_BLOCK + 1, P.by * RM_BLOOD_BLOCK + 1)
	for(var/i = 1, i <= RM_BLOOD_BLOCK * RM_BLOOD_BLOCK, i++)
		var/n = P.amt[i]
		if(!n) continue
		var/a = -1
		var/b = -1
		var/s = P.s1[i]
		if(s)
			if(!at[s])
				var/list/X = Remaster3DTexture(P.icon, s)
				pt += (X && X["file"] ? X["file"] : "")
				at[s] = length(pt)
			a = at[s] - 1
		s = P.s2[i]
		if(s)
			if(!at[s])
				var/list/X2 = Remaster3DTexture(P.icon, s)
				pt += (X2 && X2["file"] ? X2["file"] : "")
				at[s] = length(pt)
			b = at[s] - 1
		pool += list(list((i - 1) % RM_BLOOD_BLOCK, round((i - 1) / RM_BLOOD_BLOCK), min(n, 99), a, b))
	D["pool"] = pool
	D["pt"] = pt
	return D
