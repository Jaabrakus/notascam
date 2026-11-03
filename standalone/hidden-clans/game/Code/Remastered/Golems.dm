// Stone golems (the user, 2026-10-25: "make golems a great beast"): the mountain guardian of the animation arena
// (art/gear3d/bosses.js, drawn from the user's own Blender golem) walks the world as one of its great beasts (Beasts.dm).
// It stands on its two feet, each 2 x 2 tiles (RmBeastParts), and is fought foot by foot; huge, it knocks down the trees
// it walks into or puts a foot on (RmBeastFeetUpdate, Bump), as a grown dragon does. It never strikes anyone (the user:
// "these world bosses dont attack they just move and shake you off"):
//  - it stands a while, then walks a stretch and stands again (RM_GOLEM_REST, RM_GOLEM_WALK);
//  - a foot coming down knocks whoever stands there aside, alive;
//  - those at its feet fighting it are shaken off: three slow heaves, each a test of Strength + Defence (RM_GOLEM_GRIP);
//    one who fails is knocked back;
//  - with people before it, it turns to them and raises both fists overhead while the tiles they will strike are marked
//    (the page draws them red: time to run), then brings them down together (RM_GOLEM_HIT): whoever is on those tiles is
//    thrown far, those beside them knocked back, all alive; walls there come down as a siege breach does (Siege.dm
//    RemasterSiegeBreak), trees fall (RmKnockDownTree), and furniture, doors and workshops there are smashed; then it
//    stays bent over, fists on the ground, slow to rise (RM_GOLEM_RISEN).
// They are the mountains walking (the user: "they use up mountain tiles or becomes mountain tiles and then they stand up
// and roam leaving gaps in mountain tiles"; "multiple stone golems just roaming around all the time"): a golem rises out
// of a mountain's edge, its body's blocks taken out of the rock as mining takes them (Gather.dm RemasterTakeTopBlock: a
// golem-sized gap, saved with the world), and roams near where it rose; felled, it falls and a mountain of rock blocks
// rises where it lay (Plans.dm's blocks, as a builder lays them), whoever stands there carried up onto the tops. So they
// carry mountain from place to place. A few rise in each region over time (RmGolemRisePass), up to rm_golem_cap, from
// deep, untouched rock away from everyone's people; a region whose golem was felled rests an hour first. Nobody near,
// it stands still (Awake.dm: the wild creatures' rule), so the far ones cost nothing.
// The page draws it from its beast record (Player/RmBeast3D below: kind "golem"), with bosses.js in Interface/gear3d.js.
#define RM_GOLEM_SIZE 2.5        // its size as a great beast (Beasts.dm): 2 and up knocks down trees
#define RM_GOLEM_GRIP 110        // Strength + Defence for a sure footing against a heave (bosses.js BSGRIP)
#define RM_GOLEM_SHAKE 36        // ticks a shake lasts: heaves at 4, 13 and 22 (bosses.js)
#define RM_GOLEM_HIT 21.5        // ticks into its slam that the fists land (bosses.js BSSLAM)
#define RM_GOLEM_RISEN 72        // ...and that it has risen again
#define RM_GOLEM_FALL 34         // ticks its fall takes before the mountain rises (bosses.js)
var/rm_golems_on = 1             // 0: no golem wakes (those awake carry on)
var/list/rm_golems = list()
var/rm_golem_loop = 0
var/list/rm_golem_rest = list(300, 900)    // ticks it stands between walks (the arena: 6-10 s)
var/list/rm_golem_walk = list(6, 14)       // tiles a walk takes it
var/rm_golem_range = 24                    // how far from where it rose it roams
var/rm_golem_region = 100                  // tiles a side of a region
var/rm_golem_per_region = 2                // golems a region holds
var/rm_golem_cap = 24                      // golems in the world
var/rm_golem_fell_rest = 36000             // ticks a region rests after its golem is felled (an hour)
var/rm_golem_rise_every = 3000             // ticks between rising passes (5 min): at most one golem a region a pass
var/list/rm_golem_region_rest = list()     // "rx,ry" -> world.time it may raise another
#define RM_GOLEM_RISE 30                   // ticks it takes to stand up out of the rock
var/list/rm_golem_shake_gap = list(150, 250)
var/rm_golem_slam_gap = 300
var/rm_golem_break_rock = 1        // 1: its feet and fists break the mountain's rock they come down on (RmGolemBreakRock); 0: as before

mob/Monsters/StoneGolem
	name = "Stone Golem"
	icon = 'Gargoyle.dmi'   // its 2D picture (the 3D view draws the golem itself)
	density = 1
	Race = "Golem"
	Owner = "{Mountain Guardians}"
	HP = 4000
	MAXHP = 4000
	OrganMaxHP = 600
	BloodContent = 0
	MaxBloodContent = 0
	Defence = 120
	Delay = 8
	UsesEquipment = 0
	HoldingWeapon = "Fists"
	ImmuneToTemperature = 1
	ImmunePoison = 1
	CanBeSlaved = 0
	HasLeftArm = 1
	HasRightArm = 1
	HasLeftLeg = 1
	HasRightLeg = 1
	HasHead = 1
	DieAge = 1000000
	var/tmp
		rm_gmode = "idle"    // idle, walk, shake, slam, fall
		rm_gat = 0           // world.time it began
		rm_gnext = 0         // standing: when it walks again
		rm_gshake_at = 0     // when it may shake again
		rm_gslam_at = 0      // when it may slam again
		rm_gbeat = -1        // the heave last tested
		rm_gstruck = 0       // the slam's fists have landed
		list/rm_gzone        // the tiles its fists strike (the page marks them)
		rm_gdied = 0
		turf/rm_ghome        // where it rose
		atom/rm_gdest        // a walk paused while nobody is near
		rm_gregion           // "rx,ry"

mob/Monsters/StoneGolem/New()
	. = ..()
	Strength = 120
	Agility = 5
	FullHeal()
	spawn() WalkTo()
	rm_golems += src
	rm_gnext = world.time + rand(rm_golem_rest[1], rm_golem_rest[2])
	spawn(1) if(src && isturf(loc)) RmBeastFeetUpdate(src)
	if(!rm_golem_loop)
		rm_golem_loop = 1
		spawn(2) RmGolemLoop()

mob/Monsters/StoneGolem/Del()
	rm_golems -= src
	return ..()

// It never strikes: no blow of its own, whatever sets it a target.
mob/Monsters/StoneGolem/RemasterStrike(mob/M, kind_hint)
	return 0

proc/RmGolemLoop()
	while(length(rm_golems))
		for(var/mob/Monsters/StoneGolem/G in rm_golems) if(G && G.HP > 0 && !G.GoingToDie && isturf(G.loc)) G.RmGolemTick()
		sleep(2)
	rm_golem_loop = 0

proc/RmGolemFoe(mob/Monsters/U)
	return istype(U) && istype(U.Owner, /Player) && U.HP > 0 && !U.GoingToDie && isturf(U.loc)

mob/Monsters/StoneGolem/proc/RmGolemMode(m)
	rm_gmode = m
	rm_gat = world.time
	rm_gbeat = -1
	rm_gstruck = 0
	if(m != "slam") rm_gzone = null
	if(m != "walk") destination = null

mob/Monsters/StoneGolem/proc/RmGolemTick()
	Target = null   // whatever the original's fighting set (it never strikes back)
	if(world.time - rm_wild_seen >= 10) RmWildLook()   // nobody near: it stands still (WildClock.dm, Awake.dm)
	if(!rm_wild_was && rm_gmode != "slam" && rm_gmode != "shake" && rm_gmode != "rise")
		if(destination)   // its walk paused till someone comes
			rm_gdest = destination
			destination = null
		return
	if(rm_gdest)
		if(rm_gmode == "walk" && !destination) destination = rm_gdest
		rm_gdest = null
	var/t = world.time - rm_gat
	switch(rm_gmode)
		if("rise")
			if(t >= RM_GOLEM_RISE)
				RmGolemMode("idle")
				rm_gnext = world.time + rand(20, 60)   // then off it goes
			return
		if("shake")
			var/beat = round((t - 4) / 9)
			if(t >= 4 && beat <= 2 && beat != rm_gbeat)
				rm_gbeat = beat
				RmGolemHeave()
			if(t >= RM_GOLEM_SHAKE) RmGolemMode("idle")
			return
		if("slam")
			if(!rm_gstruck && t >= RM_GOLEM_HIT)
				rm_gstruck = 1
				RmGolemStrike()
			if(t >= RM_GOLEM_RISEN) RmGolemMode("idle")
			return
		if("walk")
			if(!destination || loc == destination || t > 600)   // there, or stuck a minute
				RmGolemMode("idle")
				rm_gnext = world.time + rand(rm_golem_rest[1], rm_golem_rest[2])
	// those fighting at its feet: it shakes them off; people before it: it slams
	if(world.time >= rm_gshake_at)
		var/n = 0
		for(var/obj/RmBeastFoot/F in rm_feet) if(isturf(F.loc))
			for(var/mob/Monsters/U in range(1, F)) if(RmGolemFoe(U) && (U.rm_aim_beast == src || U.Target == src || U.destination == src))   // fighting it at its feet (Beasts.dm RmBeastStrikePart)
				n++
				break
			if(n) break
		if(n)
			rm_gshake_at = world.time + rand(rm_golem_shake_gap[1], rm_golem_shake_gap[2])
			RmGolemMode("shake")
			return
	if(world.time >= rm_gslam_at)   // turned the way its fists would catch the most of them
		var/list/foes = list()
		for(var/mob/Monsters/U in range(7, src)) if(RmGolemFoe(U) && get_dist(src, U) >= 2) foes += U
		if(length(foes))
			var/best = 0
			var/bn = 0
			var/list/bz
			for(var/d in list(dir, NORTH, NORTHEAST, EAST, SOUTHEAST, SOUTH, SOUTHWEST, WEST, NORTHWEST))
				var/list/Z = RmGolemZone(d)
				var/n = 0
				for(var/mob/Monsters/U in foes) for(var/turf/T in Z) if(get_dist(T, U) <= 1)
					n++
					break
				if(n > bn)
					bn = n
					best = d
					bz = Z
			if(bn)
				dir = best
				RmBeastFeetUpdate(src)
				rm_gslam_at = world.time + rm_golem_slam_gap
				RmGolemMode("slam")
				rm_gzone = bz
				return
	if(rm_gmode == "idle" && world.time >= rm_gnext)   // a stretch, kept near where it rose
		var/n = rand(rm_golem_walk[1], rm_golem_walk[2])
		var/a = rand(0, 359)
		if(rm_ghome && get_dist(src, rm_ghome) > rm_golem_range / 2) a = arctan(rm_ghome.x - x, rm_ghome.y - y) + rand(-50, 50)   // far out: back toward home
		var/turf/T = locate(clamp(x + round(n * cos(a)), 2, world.maxx - 1), clamp(y + round(n * sin(a)), 2, world.maxy - 1), z)
		if(T && !T.density && (!rm_ghome || get_dist(T, rm_ghome) <= rm_golem_range))
			RmGolemMode("walk")
			destination = T
		else rm_gnext = world.time + 30

// The tiles its fists come down on, facing d: round each fist, 4.5 tiles ahead and 1.4 to either side, 2 tiles out
// (bosses.js bsSlamTiles: where the model's fists land).
mob/Monsters/StoneGolem/proc/RmGolemZone(d)
	. = list()
	var/fx = (d & EAST ? 1 : 0) - (d & WEST ? 1 : 0)
	var/fy = (d & NORTH ? 1 : 0) - (d & SOUTH ? 1 : 0)
	var/l = sqrt(fx * fx + fy * fy) || 1
	fx /= l
	fy /= l
	for(var/s in list(-1.4, 1.4))
		var/cx = x + fx * 4.5 + fy * s
		var/cy = y + fy * 4.5 - fx * s
		for(var/i = round(cx - 2), i <= round(cx + 2) + 1, i++) for(var/j = round(cy - 2), j <= round(cy + 2) + 1, j++)
			if((i - cx) ** 2 + (j - cy) ** 2 > 4) continue
			var/turf/T = locate(i, j, z)
			if(T && !(T in .)) . += T

// Knocked aside or thrown: up to n tiles along (dx, dy) while the way is open; down a moment, alive.
mob/Monsters/StoneGolem/proc/RmGolemThrow(mob/Monsters/U, dx, dy, n, how = "flying")   // how: the 3D view's launch (flying, hammer, throw)
	if(!dx && !dy)
		dx = (dir & EAST ? 1 : 0) - (dir & WEST ? 1 : 0)
		dy = (dir & NORTH ? 1 : 0) - (dir & SOUTH ? 1 : 0)
	var/turf/T = U.loc
	var/m = 0
	for(var/i = 1, i <= n, i++)
		var/turf/N = locate(T.x + dx, T.y + dy, T.z)
		if(!N || N.density) break
		var/taken = 0
		for(var/atom/movable/A in N) if(A.density && A != U) taken = 1
		if(taken) break
		T = N
		m++
	U.destination = null
	if(T != U.loc) U.loc = T
	U.Stunned = 1
	spawn(m >= 3 ? 30 : 18) if(U) U.Stunned = 0   // down while it flies, lands and gets up
	RemasterHitAt(U.x, U.y, U.z, 0, "stagger", src, U.Owner, m ? "knock|[dx]|[dy]|[m]|[how]" : null)
	RmGolemShowThrow(U, dx, dy, m, how, rm_hit_id)   // the page plays the launch now, from the tile it stood on (below)

// A heave: everyone at its feet tests their footing; one who fails is knocked back two tiles.
mob/Monsters/StoneGolem/proc/RmGolemHeave()
	var/list/done = list()
	for(var/obj/RmBeastFoot/F in rm_feet) if(isturf(F.loc))
		for(var/mob/Monsters/U in range(1, F)) if(RmGolemFoe(U) && !(U in done))
			done += U
			if(U.RmStr() + U.Defence >= RM_GOLEM_GRIP * 2 || prob(clamp(100 * (U.RmStr() + U.Defence) / RM_GOLEM_GRIP, 5, 96))) continue   // twice the grip: a sure footing
			RmGolemThrow(U, sign(U.x - x), sign(U.y - y), 2, "hammer")   // shaken off: a hammer launch, alive
			if(istype(U.Owner, /Player)) U.Owner:RemasterLog("[U] is shaken off [src]'s feet.", "fight", U.loc)

// The fists land: who is on their tiles is thrown far, who is beside them knocked back; what stands there breaks.
mob/Monsters/StoneGolem/proc/RmGolemStrike()
	var/list/Z = rm_gzone
	if(!length(Z)) return
	var/cx = 0
	var/cy = 0
	for(var/turf/T in Z)
		cx += T.x / length(Z)
		cy += T.y / length(Z)
	var/list/near = list()
	for(var/turf/T in Z) for(var/turf/N in range(1, T)) if(!(N in Z) && !(N in near)) near += N
	var/list/told = list()
	for(var/mob/Monsters/U in range(7, src)) if(RmGolemFoe(U))
		var/on = (U.loc in Z) ? 1 : (U.loc in near) ? 2 : 0
		if(!on) continue
		var/ox = U.x - cx
		var/oy = U.y - cy
		RmGolemThrow(U, sign(round(ox + (U.x - x) / 2)), sign(round(oy + (U.y - y) / 2)), on == 1 ? 5 : 2, on == 1 ? "throw" : "flying")   // under the fists: a dragon throw; beside them: knocked back
		if(on == 1 && istype(U.Owner, /Player) && !(U.Owner in told))
			told += U.Owner
			U.Owner:RemasterLog("[src]'s fists throw [U] across the ground!", "fight", U.loc)
	for(var/turf/T in Z)
		if(T.Tree && T.density) RmKnockDownTree(T, src)
		else if(T.IsWall && T.density) RemasterSiegeBreak(T, null)   // (no striker named: the realm's notice names a player's)
		else RmGolemBreakRock(T)   // the mountain's rock: broken to the ground (the owner: "golems need to break stone mountain tiles")
		for(var/obj/Items/Furniture/I in T) if(I.Placed)
			view(T) << "[src]'s fists smash the [I.name]."
			del I
		for(var/mob/WorkShops/W in T)
			view(T) << "[src]'s fists smash the [W.name]."
			del W
		remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1

// It walks: whoever stands where its feet come down is knocked aside first.
mob/Monsters/StoneGolem/Move(NewLoc, Dir = 0, step_x = 0, step_y = 0)
	if(isturf(NewLoc) && rm_gmode == "walk")
		var/turf/A = NewLoc
		var/d = get_dir(loc, A) || dir
		RmGolemBreakRock(A)   // walking into rock: it smashes through
		for(var/turf/T in RmGolemFeetAt(A, d)) RmGolemBreakRock(T)   // rock where a foot comes down breaks (whoever stood on it comes down, then is knocked aside)
		for(var/turf/T in RmGolemFeetAt(A, d)) for(var/mob/Monsters/U in T) if(U != src && U.HP > 0)
			RmGolemThrow(U, sign(U.x - A.x) || ((d & EAST ? 1 : 0) - (d & WEST ? 1 : 0)), sign(U.y - A.y) || ((d & NORTH ? 1 : 0) - (d & SOUTH ? 1 : 0)), 2)
	return ..()

// The mountain's rock where its foot or fist comes down (the owner, 2026-10-26: "golems need to break stone mountain
// tiles"): broken to the ground, block by block as mining takes them (Gather.dm RemasterTakeTopBlock: saved with the
// world, the column's height kept, whoever stood on top coming down), as a foot or a fist stands at ground level. A
// dug-out tile under rock loses its roof the same way. Walls go by the siege's breach (the fists), trees as before.
proc/RmGolemBreakRock(turf/T)
	if(!rm_golem_break_rock || !T || T.z != GROUND_LAYER || T.IsWall || T.Tree || !RemasterIsMountain(T)) return 0
	RmKeepHeight(T)
	for(var/i = 0, i < 16 && (T.density || T.remaster_roof > 0) && RemasterIsMountain(T), i++) RemasterTakeTopBlock(T)
	remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1
	return 1

// Its feet's tiles standing on A facing d (Beasts.dm RmBeastFeetUpdate's reckoning).
mob/Monsters/StoneGolem/proc/RmGolemFeetAt(turf/A, d)
	. = list()
	var/dx = (d & EAST ? 1 : 0) - (d & WEST ? 1 : 0)
	var/dy = (d & NORTH ? 1 : 0) - (d & SOUTH ? 1 : 0)
	if(!dx && !dy) dy = -1
	for(var/list/o in RmBeastParts("golem", RM_GOLEM_SIZE))
		var/turf/T = locate(A.x + round(o[1] * dx + o[2] * dy), A.y + round(o[1] * dy - o[2] * dx), A.z)
		if(T && T != A) . += T

// Its feet (Beasts.dm RmBeastParts): 2 x 2 a foot, one or two tiles to either side, level with it and a tile ahead
// (measured on the model, bosses.js bsFootTiles).
proc/RmGolemParts()
	return list(list(0, -1, "left foot"), list(0, -2, "left foot"), list(1, -1, "left foot"), list(1, -2, "left foot"),
		list(0, 1, "right foot"), list(0, 2, "right foot"), list(1, 1, "right foot"), list(1, 2, "right foot"))

// --- Felled: the mountain rises --------------------------------------------------------------------------------------
mob/Monsters/StoneGolem/CarryPartStats(atom/movable/PART)
	. = ..()
	if(!istype(PART, /mob/Body)) return
	var/mob/Body/B = PART
	B.rm_beast = list("golem", "", RM_GOLEM_SIZE)
	B.rm_beast_died = world.time
	B.dir = dir
	B.name = "[src]"
	if(rm_gregion) rm_golem_region_rest[rm_gregion] = world.time + rm_golem_fell_rest   // its region rests a while
	RmGolemFell(B)

// The mountain rises once its fall is played: timed from a global proc, as the golem is deleted with its own procs.
proc/RmGolemFell(mob/Body/B)
	spawn(RM_GOLEM_FALL) RmGolemMountain(B)

// Rock blocks where it lay, higher toward its middle (up to 7), on open ground (Plans.dm RmPlanGroundOK: not on water,
// walls, someone's floor...). Whoever stands there is carried up onto the top.
proc/RmGolemMountain(mob/Body/B)
	if(!B || !isturf(B.loc)) return
	var/turf/C = B.loc
	var/cz = C.z
	var/cx = C.x
	var/cy = C.y
	del B
	if(cz != GROUND_LAYER) return
	var/n = 0
	for(var/turf/T in range(4, locate(cx, cy, cz)))
		var/r = sqrt((T.x - cx) ** 2 + (T.y - cy) ** 2)
		if(r > 4.2) continue
		var/h = clamp(round(7 - r * 1.5 + RemasterHash(T.x, T.y, 7) * 1.6), 1, 7)
		var/list/up = list()
		for(var/mob/Monsters/U in T) up += U
		for(var/mob/Monsters/U in up) U.loc = null   // out of the way while the ground closes (RmPlanGroundOK)
		if(!RmPlanGroundOK(T, null))
			for(var/mob/Monsters/U in up) U.loc = T
			continue
		for(var/k = 0, k < h, k++) RmPlanPutBlock(T, k)
		var/turf/S = locate(T.x, T.y, SKY_LAYER)
		for(var/mob/Monsters/U in up) U.loc = S || T
		if(S) RemasterFeetCheck(T)
		n++
	if(n) for(var/mob/M in range(12, locate(cx, cy, cz))) if(M.client) M << "<b>The golem falls, and a mountain rises where it lay.</b>"

// --- Rising -----------------------------------------------------------------------------------------------------------
// Every rm_golem_rise_every ticks each region short of rm_golem_per_region golems (and not resting) may raise one, up to
// rm_golem_cap in the world: from the edge of a mountain, facing out onto open ground, where its whole footprint (5 tiles
// across, 3 deep) is untouched natural rock with nothing on it or on its tops, nobody's ground, and the land is asleep
// (nobody's people, workshops or camera within reach: Awake.dm). Its blocks come out of the rock as mining takes them,
// leaving open ground; it stands up out of the gap (the page sinks it in the rock at first) and walks out.
var/obj/rm_golem_probe = new   // asks Awake.dm about a tile
proc/RmGolemRisePass()
	if(!rm_golems_on || length(rm_golems) >= rm_golem_cap) return 0
	if(!RmUnitRoom()) return 0   // none rises while the world is crowded (UnitLimit.dm)
	var/list/have = list()
	for(var/mob/Monsters/StoneGolem/G in rm_golems) if(G.rm_gregion) have[G.rm_gregion] = (have[G.rm_gregion] || 0) + 1
	. = 0
	for(var/rx = 0, rx * rm_golem_region < world.maxx, rx++) for(var/ry = 0, ry * rm_golem_region < world.maxy, ry++)
		var/key = "[rx],[ry]"
		if((have[key] || 0) >= rm_golem_per_region || world.time < (rm_golem_region_rest[key] || 0)) continue
		if(length(rm_golems) >= rm_golem_cap) return
		if(RmGolemRiseIn(rx, ry)) .++

proc/RmGolemRiseIn(rx, ry)
	var/x0 = rx * rm_golem_region + 1
	var/y0 = ry * rm_golem_region + 1
	var/x1 = min(world.maxx, x0 + rm_golem_region - 1)
	var/y1 = min(world.maxy, y0 + rm_golem_region - 1)
	for(var/i = 1, i <= 200, i++)
		var/turf/X = locate(rand(x0, x1), rand(y0, y1), GROUND_LAYER)
		if(!X || !X.density || !istype(X, /turf/grounds/cavefloor)) continue
		var/list/ds = list(NORTH, EAST, SOUTH, WEST)
		var/o = rand(0, 3)
		for(var/j = 1, j <= 4, j++)   // out to the mountain's edge one way or another
			var/d = ds[(j + o - 1) % 4 + 1]
			var/turf/E = X
			for(var/k = 1, k <= 8 && E && E.density, k++) E = get_step(E, d)
			if(!E || E.density) continue
			var/turf/C = get_step(get_step(E, turn(d, 180)), turn(d, 180))   // two in from the edge: its front row against the open ground
			if(C && RmGolemRiseSpot(C, d))
				var/mob/Monsters/StoneGolem/G = RmGolemRise(C, d)
				G.rm_gregion = "[rx],[ry]"
				return G
	return null

// The tiles it rises from at C facing d: 5 across (side -2..2) and 3 deep (forward -1..1).
proc/RmGolemFootprint(turf/C, d)
	. = list()
	var/fx = (d & EAST ? 1 : 0) - (d & WEST ? 1 : 0)
	var/fy = (d & NORTH ? 1 : 0) - (d & SOUTH ? 1 : 0)
	for(var/f = -1, f <= 1, f++) for(var/s = -2, s <= 2, s++)
		var/turf/T = locate(C.x + f * fx + s * fy, C.y + f * fy - s * fx, C.z)
		if(!T) return null
		. += T

proc/RmGolemRiseSpot(turf/C, d)
	if(!C || C.z != GROUND_LAYER) return 0
	rm_golem_probe.loc = C
	var/awake = RmAwake(rm_golem_probe)
	rm_golem_probe.loc = null
	if(awake) return 0
	var/list/F = RmGolemFootprint(C, d)
	if(!F) return 0
	for(var/turf/T in F)
		if(!istype(T, /turf/grounds/cavefloor) || !T.density || !RemasterIsMountain(T) || T.Owner) return 0
		if(T.remaster_built || T.remaster_topcut || T.remaster_holes || T.remaster_dug || T.remaster_dug_top || T.remaster_roof || T.remaster_built_floor || T.remaster_carve || T.remaster_slope) return 0
		for(var/atom/movable/A in T) return 0
		var/turf/U = locate(T.x, T.y, SKY_LAYER)
		if(U && (U.density || U.icon_state != "Peak")) return 0
		if(U) for(var/atom/movable/A in U) return 0   // nothing built or standing up on its tops
	var/turf/B = locate(C.x - 2 * ((d & EAST ? 1 : 0) - (d & WEST ? 1 : 0)), C.y - 2 * ((d & NORTH ? 1 : 0) - (d & SOUTH ? 1 : 0)), C.z)
	if(!B || !B.density) return 0   // rock behind it too: deep rock, not a thin ridge
	var/turf/W = get_step(C, d)   // its front row; past it a way out onto open ground
	for(var/k = 2, k <= 4, k++)
		W = get_step(W, d)
		if(!W || W.density || findtext("[W.icon_state]", "Water")) return 0
	return 1

// It rises: its footprint's blocks taken out top first (the gap is open ground, saved as dug rock), and it stands there.
proc/RmGolemRise(turf/C, d)
	var/n = 0
	for(var/turf/T in RmGolemFootprint(C, d))
		RmKeepHeight(T)
		for(var/h = RemasterBlocksAt(T), h > 0 && T.density, h = RemasterBlocksAt(T))
			RemasterTakeTopBlock(T)
			n++
	var/mob/Monsters/StoneGolem/G = new(C)
	G.dir = d
	G.rm_ghome = C
	G.rm_gblocks = n
	G.RmGolemMode("rise")
	return G
mob/Monsters/StoneGolem/var/tmp/rm_gblocks = 0   // the blocks it rose with

// world/New: this file's part is step RmChainWorldNew_Golems in Code/Remastered/Chains/WorldNew.dm

// --- The 3D view -----------------------------------------------------------------------------------------------------
// Its beast record (Beasts.dm Player/RmBeast3D): what it is doing and how long since it began (the page plays bosses.js's
// moves from there), its feet (parts), and while it slams the tiles its fists will strike.
Player/RmBeast3D(mob/Monsters/M)
	if(!istype(M, /mob/Monsters/StoneGolem)) return ..()
	var/mob/Monsters/StoneGolem/G = M
	if(G.HP <= 0) return null
	RmGolemSend()
	. = list("kind"="golem", "anim"=(G.rm_gmode == "walk" && !G.destination ? "idle" : G.rm_gmode), "at"=round((world.time - G.rm_gat) / 10, 0.1), "size"=RM_GOLEM_SIZE)
	if(length(G.rm_feet))
		var/list/parts = list()
		for(var/obj/RmBeastFoot/F in G.rm_feet) if(isturf(F.loc)) parts += list(list(F.x, F.y, F.part, RmPartHealth(G, F.part)))
		.["parts"] = parts
	if(G.rm_gmode == "slam" && length(G.rm_gzone))
		var/list/Z = list()
		for(var/turf/T in G.rm_gzone) Z += list(list(T.x, T.y))
		.["zone"] = Z

Player/RmBeastCorpse3D(mob/Body/B)
	var/list/C = B.rm_beast
	if(!C || C[1] != "golem") return ..()
	RmGolemSend()
	return list("kind"="golem", "anim"="fall", "dead"=1, "size"=C[3], "at"=isnull(B.rm_beast_died) ? 99 : round((world.time - B.rm_beast_died) / 10, 0.1))

// The golem's stones for the page (art/gear3d/golem/boss-golem.json), once a connection, when it first sees one.
Player/proc/RmGolemSend()
	if(!client) return
	if(!remaster_3d_sent) remaster_3d_sent = list()
	if(remaster_3d_sent["boss-golem.json"]) return
	remaster_3d_sent["boss-golem.json"] = 1
	src << browse_rsc(file("Interface/gear3d/boss-golem.json"), "boss-golem.json")

// Its throws on the page (the user, 2026-10-26: "i notice we didnt add the launch animations when hit by golems"): each
// player whose 3D view shows the unit is told the moment it is thrown (knock3D: gear3d.js g3knock3D), ahead of its new
// tile (Remaster3DMovesPush) and of the HUD's record of the blow (RemasterHitData, up to half a second later). The record
// alone came after the new tile: the page looked for the unit on its new tile in a list made before it moved, found
// nobody and played nothing, and the picture jumped (5 tiles) or slid (2) there. Now the doll flies from the tile it
// stood on onto the one it was thrown to; one pinned where it stood (m 0: a wall or someone behind it) goes up and comes
// down there. The row: its ref as that player knows it, where it is now, the way it went, tiles, the launch (flying,
// hammer, throw), the hit's id (the page plays each once). rm_golem_launch 0: none sent; the page has only the HUD's
// record, as before.
#define RM_GOLEM_KNOCK3D 1   // (its checks look for it: reports/golem-launch)
var/rm_golem_launch = 1
proc/RmGolemShowThrow(mob/Monsters/U, dx, dy, m, how, id)
	if(!rm_golem_launch || !U || !isturf(U.loc)) return
	for(var/Player/P in Players) if(P.z == U.z && get_dist(P, U) <= 25 && P.RmGolemSees3D())
		if(U.Owner != P && !P.RmFogSees(U.loc)) continue   // fog of war: as its move3D (Fog.dm)
		P.RmGolemKnockOut(list(U.Owner == P ? RemasterUIRef(U) : "\ref[U]", U.x, U.y, dx, dy, m, how, id))

Player/proc/RmGolemSees3D()
	return client && remaster_3d && remaster_hud_ready

Player/proc/RmGolemKnockOut(list/row)
	src << output(url_encode(json_encode(list(row))), "mapwindow.hud:knock3D")
