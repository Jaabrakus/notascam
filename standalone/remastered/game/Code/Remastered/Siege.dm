// Siege weapons, built at the Carpentry:
//   Battering ram  3 wood          - pushed up to a wall or door and pounds it (300 a blow,
//                                    +100 for each extra crew member, up to 2)
//   Catapult       4 wood, 1 stone - hurls a boulder 3 to 10 tiles every 6 seconds (500 to
//                                    a wall; anyone within a tile of the impact is hurt)
//   Ballista       3 wood, 1 iron  - shoots a heavy bolt straight at an enemy 2 to 12 tiles off
//                                    every 5 seconds (40-70); built for great beasts: it hits the
//                                    part it was aimed at (Beasts.dm) and, at one in the air,
//                                    mostly its wings - enough of them and a dragon comes down
// An engine moves and fires only with one of its owner's people within 2 tiles (its
// crew). Select it (click it, or box-select it with its crew) and:
//   - click a wall or door, or Attack (A) and click one: it goes to work on it;
//   - Attack and click an enemy (catapult): it shells them;
//   - Attack and click the ground: attack-move, smashing walls of realms at war on the way;
//   - click the ground: it rolls there.
// Built walls have 1000 (wood) to 4500 (obsidian) HP, doors 10. A broken wall opens the
// way digging does and leaves rubble. Walls inside another realm's land may be attacked
// only at war (War.dm); your own and your allies' never.

#define RM_SIEGE_CREW 2
#define RM_CATAPULT_MIN 3
#define RM_CATAPULT_MAX 10
#define RM_BALLISTA_MAX 12

var/list/rm_siege_engines = list()
var/list/rm_wall_max = list()          // "x,y,z" -> HP the wall had when first hit (for the bars)
var/rm_siege_loop = 0

mob/Monsters/RemasterSiege
	name = "Siege engine"
	icon = 'Cave.dmi'
	icon_state = "Wagon"
	density = 0
	CantKill = 1
	DieAge = 1000000
	Gender = null
	layer = 3.5
	suffix = null
	HasLeftLeg = 1
	HasRightLeg = 1
	CanWalk = 1
	HumanParts = 0
	HP = 500
	MAXHP = 500
	var/remaster_siege_kind = "ram"
	var/tmp/remaster_siege_target          // a wall turf, a door, or (catapult) an enemy unit
	var/tmp/turf/remaster_siege_goal       // where to roll to
	var/tmp/remaster_siege_auto = 0        // attack-move: find enemy walls on the way
	var/tmp/remaster_siege_next = 0
	var/tmp/remaster_siege_status = "Idle"
	New()
		rm_siege_engines += src
		var/image/I = new('mob.dmi', src)
		Star = I
		spawn(1) WalkTo()
	Del()
		rm_siege_engines -= src
		..()
	Ram
		name = "Battering ram"
		Delay = 7
		remaster_siege_kind = "ram"
	Catapult
		name = "Catapult"
		Delay = 9
		remaster_siege_kind = "catapult"
	Ballista
		name = "Ballista"
		Delay = 8
		remaster_siege_kind = "ballista"

proc/RemasterIsSiege(M)
	return istype(M, /mob/Monsters/RemasterSiege)

// --- What may be hit -----------------------------------------------------------------
proc/RemasterSiegeDoor(turf/T)
	for(var/obj/Items/Furniture/Doors/D in T) if(D.Placed) return D
	return null

proc/RemasterSiegeWall(turf/T)
	return T && T.density && (T.IsWall || RmBuiltTopK(T) >= 0)   // or a column with a laid block on top (BuiltWalls.dm)

// The turf a siege target stands on, or null if it is gone.
proc/RemasterSiegeSpot(A)
	if(isturf(A)) return (RemasterSiegeWall(A) || RemasterSiegeDoor(A)) ? A : null
	if(istype(A, /obj/Items/Furniture/Doors))
		var/obj/O = A
		return isturf(O.loc) ? O.loc : null
	if(istype(A, /mob/Monsters))
		var/mob/Monsters/M = A
		return (M.HP > 0 && !M.GoingToDie && isturf(M.loc)) ? M.loc : null
	return null

// May this player's engines batter T? quiet = don't explain why not.
Player/proc/RemasterSiegeMay(turf/T, quiet = 0)
	if(!T.IsWall && RmBuiltTopK(T) >= 0 && RemasterAlliedKeys(RmBuiltOwnerKey(T), key))   // its laid blocks your realm's (BuiltWalls.dm)
		if(!quiet) RemasterNotice("That wall belongs to your own realm.")
		return 0
	var/obj/RemasterBanner/B = RemasterClaimAt(T)
	if(!B) return 1
	if(RemasterAlliedKeys(B.owner_key, key))
		if(!quiet) RemasterNotice("That wall belongs to your own realm.")
		return 0
	if(RemasterAtWarKeys(key, B.owner_key)) return 1
	if(!quiet) RemasterNotice("You are at peace with [B.owner_name]'s realm. Declare war in the Realm tab first.")
	return 0

// --- Orders ---------------------------------------------------------------------------
Player/proc/RemasterSelectedSiege()
	. = list()
	for(var/mob/Monsters/RemasterSiege/E in Selected) if(E.Owner == src) . += E

Player/proc/RemasterSiegeSelect(mob/Monsters/RemasterSiege/E, add)
	if(add && (E in Selected))
		E.Deselect(src)
		return
	if(!add) for(var/mob/Monsters/S in Selected.Copy()) S.Deselect(src)
	E.Select(src)
	if(RmIsShip(E))   // Ships.dm
		RemasterNotice("[E.name] selected ([length(E:RmShipAboard())] of [E:rm_ship_seats] aboard): click water to sail, land to sail there and put them ashore[E:rm_ship_ram ? ", an enemy ship to ram it" : ""]. Select people and click it to board.")
		return
	var/how = list("ram"="click a wall or door to batter it", "catapult"="click a wall or door, or Attack an enemy, to shell it ([RM_CATAPULT_MIN]-[RM_CATAPULT_MAX] tiles)",
		"ballista"="Attack an enemy to shoot at it (up to [RM_BALLISTA_MAX] tiles); right-click a great beast in 3D to aim at a part, its wings to bring a dragon down")[E.remaster_siege_kind]
	RemasterNotice("[E.name] selected: [how]. Keep one of your people beside it as crew.")

// Engines in the selection take an order on A. explicit: from Attack mode. Returns how many.
Player/proc/RemasterSiegeOrder(atom/A, explicit = 0)
	var/ns = RmShipOrder(A, explicit)   // ships in the selection (Ships.dm)
	var/list/E = RemasterSelectedSiege()
	for(var/mob/Monsters/RemasterSiege/Ship/X in E) E -= X
	if(!length(E) || !A) return ns
	var/turf/T = isturf(A) ? A : A.loc
	if(!isturf(T)) return 0
	var/door = RemasterSiegeDoor(T)
	var/n = 0
	for(var/mob/Monsters/RemasterSiege/S in E)
		if(S.z != T.z) continue
		S.remaster_siege_auto = 0
		S.remaster_siege_goal = null
		S.remaster_siege_target = null
		if((RemasterSiegeWall(T) || door) && S.remaster_siege_kind != "ballista")   // a ballista shoots at people, not walls
			if(!RemasterSiegeMay(T)) return 0
			S.remaster_siege_target = door || T
			S.remaster_siege_status = "Attacking [door ? "a door" : "a wall"] at [T.x],[T.y]"
		else if(istype(A, /mob/Monsters) && A:Owner != src && (S.remaster_siege_kind in list("catapult", "ballista")) && RemasterHostile(S, A, 1))
			S.remaster_siege_target = A
			S.remaster_siege_status = "[S.remaster_siege_kind == "ballista" ? "Shooting at" : "Shelling"] [RemasterCombatName(A)]"
			var/Player/PP = src
			for(var/mob/Monsters/U in PP.Selected) if(U.rm_aim_beast == A)   // the part the crew were sent at (Beasts.dm)
				S.rm_aim_beast = A
				S.rm_aim_part = U.rm_aim_part
				break
		else
			S.remaster_siege_goal = T
			S.remaster_siege_auto = explicit
			S.remaster_siege_status = explicit ? "Attack-move" : "Moving"
		n++
	if(n) RemasterNotice("[n] siege engine[n > 1 ? "s" : ""]: [E[1]:remaster_siege_status].")
	return n + ns

// --- The engines at work ----------------------------------------------------------------
mob/Monsters/RemasterSiege/proc/RemasterSiegeCrew()
	. = 0
	var/Player/P = Owner
	if(!istype(P)) return
	for(var/mob/Monsters/M in range(RM_SIEGE_CREW, src)) if(M.Owner == P && (M in P.UnitList) && M.HP > 0 && !M.GoingToDie && !M.Sleeping && !M.Fainted)
		.++

// Attack-move: the nearest wall or door of a realm at war with the owner, in reach of sight.
mob/Monsters/RemasterSiege/proc/RemasterSiegeFind()
	var/Player/P = Owner
	var/best
	var/bd = 99
	for(var/turf/T in range(8, src))
		if(!RemasterSiegeWall(T) && !RemasterSiegeDoor(T)) continue
		var/obj/RemasterBanner/B = RemasterClaimAt(T)
		var/owner = (!T.IsWall && RmBuiltTopK(T) >= 0) ? RmBuiltOwnerKey(T) : (B ? B.owner_key : null)   // a laid column: its builder's realm (BuiltWalls.dm)
		if(!owner || !RemasterAtWarKeys(P.key, owner)) continue
		var/d = get_dist(src, T)
		if(d < bd)
			bd = d
			best = T
	return best

mob/Monsters/RemasterSiege/proc/RemasterSiegeTick()
	if(!isturf(loc) || RmIsShip(src)) return   // ships: their own loop (Ships.dm)
	var/crew = RemasterSiegeCrew()
	RemasterSiegeDamageTick(crew)
	if(!src) return
	var/Player/P = Owner
	if(!istype(P)) return
	if(!crew)
		destination = null
		if(remaster_siege_target || remaster_siege_goal) remaster_siege_status = "Needs crew: keep one of your people beside it"
		return
	if(findtext(remaster_siege_status, "Needs crew") == 1) remaster_siege_status = RmSiegeDoing()   // crew back: it said so for good
	var/turf/T = remaster_siege_target ? RemasterSiegeSpot(remaster_siege_target) : null
	if(remaster_siege_target && !T)
		remaster_siege_target = null
		remaster_siege_status = remaster_siege_goal ? "Attack-move" : "Idle"
	if(!remaster_siege_target && remaster_siege_auto)
		var/turf/F = RemasterSiegeFind()
		if(F)
			remaster_siege_target = RemasterSiegeDoor(F) || F
			T = F
			remaster_siege_status = "Attacking a wall at [F.x],[F.y]"
	if(T)
		var/d = get_dist(src, T)
		if(remaster_siege_kind == "ram")
			if(d > 1)
				destination = T
				return
			destination = null
			dir = get_dir(src, T)
			if(world.time < remaster_siege_next) return
			remaster_siege_next = world.time + 25
			RemasterSiegeBlow(T, 300 + 100 * min(2, crew - 1), src, null)
			return
		if(remaster_siege_kind == "ballista")
			if(!ismob(remaster_siege_target))
				remaster_siege_target = null
				return
			if(d > RM_BALLISTA_MAX)
				destination = T
				return
			destination = null
			dir = get_dir(src, T)
			if(world.time < remaster_siege_next) return
			remaster_siege_next = world.time + 50
			RemasterBallistaFire(remaster_siege_target)
			return
		// catapult
		if(d > RM_CATAPULT_MAX)
			destination = T
			return
		destination = null
		if(d < RM_CATAPULT_MIN)
			remaster_siege_status = "Too close: a catapult needs [RM_CATAPULT_MIN] tiles"
			return
		if(findtext(remaster_siege_status, "Too close") == 1) remaster_siege_status = RmSiegeDoing()   // far enough again
		dir = get_dir(src, T)
		if(world.time < remaster_siege_next) return
		remaster_siege_next = world.time + 60
		RemasterCatapultFire(T)
		return
	if(remaster_siege_goal)
		if(get_dist(src, remaster_siege_goal) <= 0 || remaster_siege_goal.z != z)
			remaster_siege_goal = null
			remaster_siege_auto = 0
			remaster_siege_status = "Idle"
			destination = null
			return
		destination = remaster_siege_goal

// What it is doing, as the orders word it (RemasterSiegeOrder): for a status that waited on crew or range.
mob/Monsters/RemasterSiege/proc/RmSiegeDoing()
	var/atom/A = remaster_siege_target
	if(ismob(A)) return "[remaster_siege_kind == "ballista" ? "Shooting at" : "Shelling"] [RemasterCombatName(A)]"
	if(A) return "Attacking [isturf(A) ? "a wall" : "a door"] at [A.x],[A.y]"
	return remaster_siege_goal ? (remaster_siege_auto ? "Attack-move" : "Moving") : "Idle"

mob/Monsters/RemasterSiege/proc/RemasterCatapultFire(turf/T)
	var/turf/at = T
	if(prob(25))     // a miss lands a tile off
		at = locate(clamp(T.x + rand(-1, 1), 1, world.maxx), clamp(T.y + rand(-1, 1), 1, world.maxy), T.z) || T
	var/flight = 4 + round(get_dist(src, at) * 0.9)     // ticks, matching the 3D boulder's flight
	RemasterNativeSound(src, 'Arrow.wav')   // the HUD plays the launch (Audio.dm)
	var/sx = x
	var/sy = y
	spawn(flight)
		if(!src || !at) return
		RemasterSiegeBlow(at, 500, src, "boulder", sx, sy)
		// the impact hurts everyone around it
		for(var/mob/Monsters/M in range(1, at))
			if(M == src || M.HP <= 0 || M.GoingToDie || M.CantKill || M.Wagon || RemasterIsSiege(M)) continue
			var/before = RemasterBodyHealth(M)
			var/alive = M.HP > 0 && !M.GoingToDie
			M.RemasterThreatenedBy(src)
			var/kind = RemasterThrownWound(M, rand(10, 22), "boulder")
			if(!M || !M.loc)
				RemasterHitAt(at.x, at.y, at.z, before, "kill", src, null)
				continue
			if(alive && (M.HP <= 0 || M.GoingToDie)) kind = "kill"
			RemasterHitAt(M.x, M.y, M.z, max(0, round(before - RemasterBodyHealth(M))), kind, src, M.Owner)

// A bolt, straight at the target: it may miss; a great beast is hit at the part aimed at, one in
// the air mostly in the wings (Throwing.dm RemasterThrownWound with Beasts.dm's part).
mob/Monsters/RemasterSiege/proc/RemasterBallistaFire(mob/Monsters/E)
	var/turf/at = E.loc
	var/hit = prob(80)
	var/flight = 2 + round(get_dist(src, at) * 0.4)   // ticks, matching the 3D bolt's flight
	RemasterNativeSound(src, 'Arrow.wav')   // the HUD plays the launch (Audio.dm)
	var/sx = x
	var/sy = y
	spawn(flight)
		if(!src || !E || !E.loc) return
		if(!hit || get_dist(E, at) > 1)
			RemasterSiegeEvent(at, 0, src, "bolt", sx, sy, "miss")
			return
		var/before = RemasterBodyHealth(E)
		var/alive = E.HP > 0 && !E.GoingToDie
		E.RemasterThreatenedBy(src)
		var/kind = RemasterThrownWound(E, rand(40, 70), "bolt")
		if(!E || !E.loc)
			RemasterSiegeEvent(at, before, src, "bolt", sx, sy, "kill")
			return
		if(alive && (E.HP <= 0 || E.GoingToDie)) kind = "kill"
		RemasterSiegeEvent(E.loc, max(0, round(before - RemasterBodyHealth(E))), src, "bolt", sx, sy, kind)

// One blow (ram) or impact (boulder) on the wall or door at T.
proc/RemasterSiegeBlow(turf/T, dmg, mob/Monsters/RemasterSiege/E, proj, sx, sy)
	if(!T) return
	var/obj/Items/Furniture/Doors/D = RemasterSiegeDoor(T)
	var/key = "[T.x],[T.y],[T.z]"
	if(D)
		D.HP -= dmg
		RemasterSiegeEvent(T, dmg, E, proj, sx, sy, "wall")
		if(D.HP <= 0)
			view(T) << "<b><font color=red>The [D] is smashed to pieces!</font></b>"
			del(D)
		return
	if(!RemasterSiegeWall(T))
		if(proj) RemasterSiegeEvent(T, 0, E, proj, sx, sy, "miss")
		return
	if(!T.IsWall)   // a column of laid blocks: a block at a time, top first (BuiltWalls.dm)
		RmBuiltSiegeBlow(T, dmg, E, proj, sx, sy)
		return
	if(!rm_wall_max[key]) rm_wall_max[key] = max(1, T.HP)
	T.HP -= dmg
	RemasterSiegeEvent(T, dmg, E, proj, sx, sy, "wall")
	if(T.HP <= 0) RemasterSiegeBreak(T, E)

proc/RemasterSiegeEvent(turf/T, dmg, mob/E, proj, sx, sy, kind)
	var/w = RemasterIsSiege(E) ? E:remaster_siege_kind : RemasterWeaponClass(E)
	rm_hits += list(list(++rm_hit_id, T.x, T.y, T.z, dmg, kind, world.time, null, isnull(sx) ? E.x : sx, isnull(sy) ? E.y : sy, w, proj))
	if(length(rm_hits) > 160) rm_hits.Cut(1, length(rm_hits) - 159)

// The wall gives way: open floor and rubble, as digging leaves it.
proc/RemasterSiegeBreak(turf/T, mob/E)
	var/stone = !T.IsWood
	var/obj/RemasterBanner/B = RemasterClaimAt(T)
	T.density = 0
	T.opacity = 0
	T.IsWall = 0
	T.IsWood = 0
	T.CanDigAt = 0
	T.HP = 0
	if("Detailed" in T.vars) T.vars["Detailed"] = 0
	T.icon_state = initial(T.icon_state)
	T.name = initial(T.name)
	T.text = initial(T.text)
	if(T.Content3 == "Peak") T.icon_state = "Peak"
	if(T.Content == "Sky") T.icon_state = "Sky"
	if(T.z == 1)
		var/turf/U = locate(T.x, T.y, 3)
		if(U && U.Supported && !U.density) U.Supported = 0
	rm_wall_max -= "[T.x],[T.y],[T.z]"
	remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1
	if(stone && prob(60)) new /obj/Items/ores/stone(T)
	view(T) << "<b><font color=red>The wall at [T.x],[T.y] comes crashing down!</font></b>"
	if(B) RemasterRealmNotice(B.owner_key, "Siege: your wall at [T.x],[T.y] was smashed[E && E.Owner ? " by [E.Owner:RemasterHouse()]'s [lowertext(E.name)]" : ""]!")
	if(E && istype(E.Owner, /Player)) E.Owner:RemasterLog("Your [lowertext(E.name)] broke a wall at [T.x],[T.y].", "fight", T)

proc/RemasterSiegeLoop()
	while(1)
		sleep(5)
		for(var/mob/Monsters/RemasterSiege/E in rm_siege_engines.Copy())
			if(E) E.RemasterSiegeTick()

// world/New: this file's part is step RmChainWorldNew_Siege in Code/Remastered/Chains/WorldNew.dm

// For the 3D view: damaged walls near the camera (their health bars).
Player/proc/RemasterSiegeData()
	. = list()
	for(var/key in rm_wall_max)
		var/list/p = splittext(key, ",")
		var/turf/T = locate(text2num(p[1]), text2num(p[2]), text2num(p[3]))
		if(!T || T.z != z || abs(T.x - x) > 24 || abs(T.y - y) > 24) continue
		if(!RemasterSiegeWall(T))
			rm_wall_max -= key
			continue
		. += list(list("x"=T.x, "y"=T.y, "p"=round(100 * max(0, T.IsWall ? T.HP : RmBuiltWallHP(T)) / rm_wall_max[key])))

// --- Building one at the Carpentry ----------------------------------------------------
mob/Monsters/proc/RemasterCraftSiege(mob/WorkShops/W, Player/P, kind)
	if(!(src in range(1, W)) || !RemasterManualHandoff(P)) return
	var/list/wood = list()
	var/obj/Items/stone
	for(var/obj/Items/woods/wood/X in src) if(X.suffix != "(Equipped)") wood += X
	for(var/obj/Items/ores/stone/X in src) stone = X
	var/obj/Items/iron
	for(var/obj/Items/ores/Iron/X in src) iron = X
	var/need = kind == "catapult" ? 4 : 3
	if(length(wood) < need || (kind == "catapult" && !stone) || (kind == "ballista" && !iron))
		P << "[src] needs [need] wood[kind == "catapult" ? " and a stone" : kind == "ballista" ? " and a lump of iron" : ""] to build a [list("ram"="battering ram", "catapult"="catapult", "ballista"="ballista")[kind]]."
		return
	for(var/i = 1, i <= need, i++)
		var/obj/Items/X = wood[i]
		weight -= X.weight
		del(X)
	if(kind == "catapult")
		weight -= stone.weight
		del(stone)
	if(kind == "ballista")
		weight -= iron.weight
		del(iron)
	var/path = list("ram"=/mob/Monsters/RemasterSiege/Ram, "catapult"=/mob/Monsters/RemasterSiege/Catapult, "ballista"=/mob/Monsters/RemasterSiege/Ballista)[kind]
	var/mob/Monsters/RemasterSiege/E = new path(loc)
	E.Owner = P
	E.remaster_owner_key = P.key
	WoodCraftingSkill += 1
	P << "[src] built a [lowertext(E.name)]. Select it and click a wall; keep one of your people beside it as crew."
	P.RemasterLog("Built a [lowertext(E.name)]", "work", loc)

// --- Wrecking and burning ------------------------------------------------------------
// An engine with no crew beside it can be wrecked: enemy units at war with its owner,
// and raiders, standing next to it hack at it (25 a second each, up to 4) and may set it
// alight. Fire from anywhere (a fire brew, burning ground) catches it too. A burning
// engine loses 15 a second until one of its owner's people beside it beats the flames
// out (3 seconds). At 0 it falls apart into wood; at war that scores 2 for the wreckers.
mob/Monsters/RemasterSiege/var/remaster_owner_key       // saved: whose it is
mob/Monsters/RemasterSiege/var/remaster_siege_burning = 0
mob/Monsters/RemasterSiege/var/tmp/remaster_siege_wreck_at = 0
mob/Monsters/RemasterSiege/var/tmp/remaster_siege_douse = 0
mob/Monsters/RemasterSiege/var/tmp/remaster_siege_said = 0

mob/Monsters/RemasterSiege/Fire()
	if(remaster_siege_burning) return
	remaster_siege_burning = 1
	if(istype(Owner, /Player)) Owner:RemasterNotice("Your [lowertext(name)] at [x],[y] is on fire!")

// Someone who may wreck this engine.
mob/Monsters/RemasterSiege/proc/RemasterSiegeFoe(mob/Monsters/M)
	if(!istype(M) || M == src || RemasterIsSiege(M) || M.HP <= 0 || M.GoingToDie || !isturf(M.loc) || M.Wagon || M.Critter || M.Sleeping || M.Fainted) return 0
	if(istype(M.Owner, /Player)) return M.Owner != Owner && RemasterAtWar(M.Owner, Owner)
	return !!remaster_raiders[M]

mob/Monsters/RemasterSiege/proc/RemasterSiegeDamageTick(crew)
	if(world.time < remaster_siege_wreck_at) return
	remaster_siege_wreck_at = world.time + 10
	var/list/foes = list()
	for(var/mob/Monsters/M in range(1, src)) if(RemasterSiegeFoe(M)) foes += M
	var/dmg = 0
	var/mob/Monsters/by = length(foes) ? foes[1] : null
	if(length(foes))
		if(crew)
			// the crew stands guard: the wreckers have to deal with them first
			for(var/mob/Monsters/C in range(RM_SIEGE_CREW, src)) if(C.Owner == Owner) C.RemasterThreatenedBy(by)
		else
			dmg += 25 * min(4, length(foes))
			if(!remaster_siege_burning && prob(15)) Fire()
			if(world.time - remaster_siege_said > 300 && istype(Owner, /Player))
				remaster_siege_said = world.time
				Owner:RemasterNotice("Enemies are wrecking your unguarded [lowertext(name)] at [x],[y]!")
	if(remaster_siege_burning)
		dmg += 15
		var/near = 0
		for(var/mob/Monsters/C in range(1, src)) if(C.Owner == Owner && C.HP > 0 && !C.GoingToDie && !RemasterIsSiege(C)) near = 1
		if(near && ++remaster_siege_douse >= 3)
			remaster_siege_burning = 0
			remaster_siege_douse = 0
			view(src) << "The crew beats out the flames on the [name]."
		else if(!near) remaster_siege_douse = 0
	if(!dmg) return
	HP -= dmg
	RemasterSiegeEvent(loc, dmg, by || src, null, by ? by.x : x, by ? by.y : y, "wreck")
	if(HP <= 0) RemasterSiegeWrecked(by)

mob/Monsters/RemasterSiege/proc/RemasterSiegeWrecked(mob/Monsters/by)
	var/turf/T = loc
	for(var/i = 1, i <= 2, i++) new /obj/Items/woods/wood(T)
	view(src) << "<b><font color=red>The [name] [remaster_siege_burning ? "burns down" : "is wrecked"]!</font></b>"
	if(istype(Owner, /Player))
		Owner:RemasterNotice("Your [lowertext(name)] at [x],[y] was [remaster_siege_burning ? "burned" : "wrecked"]!")
		Owner:RemasterLog("Lost a [lowertext(name)]", "problem", T)
	if(by && istype(by.Owner, /Player) && istype(Owner, /Player)) RemasterWarScore(by.Owner:key, Owner:key, 2)
	del(src)

// --- Saved with the world (WorldSave.dm) ------------------------------------------------
proc/RemasterSiegeRecords()
	. = list()
	for(var/mob/Monsters/RemasterSiege/E in rm_siege_engines) if(isturf(E.loc))
		. += list(list("[E.type]", E.x, E.y, E.z, RemasterWorldOwnerKey(E), E.HP, E.remaster_siege_burning))

proc/RemasterSiegeRestore(list/L)
	. = 0
	for(var/list/R in L)
		var/path = text2path(R[1])
		var/turf/T = locate(R[2], R[3], R[4])
		if(!path || !T || !ispath(path, /mob/Monsters/RemasterSiege)) continue
		var/mob/Monsters/RemasterSiege/E = new path(T)
		E.remaster_owner_key = R[5]
		if(isnum(R[6])) E.HP = R[6]
		E.remaster_siege_burning = R[7] ? 1 : 0
		var/Player/P = R[5] ? RemasterPlayerByKey(R[5]) : null
		if(P) E.Owner = P
		.++
