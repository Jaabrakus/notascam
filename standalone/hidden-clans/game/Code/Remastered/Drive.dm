// Hidden Clans: you play your own ninja (the owner, 2026-11-01: "do away with the click and move and do the normal wasd
// movement with click"). WASD steps your ninja: the page sends the way the held keys point on screen, as the camera
// faces, only when it changes ("drive|dx,dy"; "drive|0,0" when they are let go). A click on a foe sends it at the foe
// (View3D.dm Remaster3DClick).
// Your ninja: the one you made your hero ("Make my hero", remaster_hero_uid), else the one selected when you first drove,
// else your leader or first unit (PlayMode.dm RemasterHero); it is kept from then on. Driving stops its orders and work,
// as Stop does (Orders.dm RemasterStopOrders), and the camera follows it (PlayMode.dm lockcam). Each step is the unit's
// own Move at its own pace (Chains/Move.dm), with every ground, mountain and door rule a walk has.

// Hero mode (the owner, 11-01: "remove the click movement and the company of people ... hero mode"): you start as one
// ninja (Restart.dm), it walks only with WASD (a click on the ground does nothing, and an order to walk to something
// further than beside it is refused: Orders.dm RemasterOrder), a click on a foe attacks, and 1-4 cast its techniques at
// what is under the mouse (Diablo's way).
var/rm_hero_mode = 1

#define RM_DRIVE_LOST 15   // ticks without word from the page (a key-up lost with the window's focus) before it stops
#define RM_DRIVE_PACE 1    // your ninja's step time, of its walking pace: its own walk (the owner, 11-01: "responsive but doesnt speed up";
                           // 0.5 was too fast). The response is the first step going at once, not a faster walk.

mob/Monsters/var/tmp
	rm_drive_dx = 0
	rm_drive_dy = 0
	rm_drive_seen = 0
	rm_drive_next = 0
	rm_driving = 0

Player/proc/RmMyNinja()
	var/mob/Monsters/H
	if(remaster_hero_uid)
		for(var/mob/Monsters/M in UnitList) if(M.remaster_uid == remaster_hero_uid && M.Owner == src && M.HP > 0 && !Rm3DGone(M))
			H = M
			break
	if(!H)
		var/n = 0
		for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0)
			H = M
			n++
		if(n != 1) H = RemasterHero()
		if(H)
			if(!H.remaster_uid) H.RemasterLineageEnsure(src)
			remaster_hero_uid = H.remaster_uid
	return H

Player/proc/RmDriveCommand(value)
	var/list/p = splittext("[value]", ",")
	var/dx = clamp(round(text2num(p[1]) || 0), -1, 1)
	var/dy = length(p) > 1 ? clamp(round(text2num(p[2]) || 0), -1, 1) : 0
	var/mob/Monsters/H = RmMyNinja()
	if(!H) return 0
	var/turned = dx != H.rm_drive_dx || dy != H.rm_drive_dy
	H.rm_drive_dx = dx
	H.rm_drive_dy = dy
	H.rm_drive_seen = world.time
	if(!dx && !dy) return 1
	if(!H.rm_driving)
		H.RemasterStopOrders()
		H.remaster_order_status = "Moving"
		var/ref = RemasterUIRef(H)
		if(remaster_lock != ref) RemasterPlayModeCommand("lockcam", ref)   // lockcam on the one it is locked to lets go
		spawn() H.RmDriveLoop()
	// the first step of a press or a turn goes at once, in the tick the key came in, not at the loop's next pass
	if(turned || !H.rm_driving) H.RmDriveNow(1)
	return 1

// turn: a new way pressed (or a stop and go again). It steps at once even before its step time is up (the owner, 11-01:
// "cancel or switch movements instantly without committing to a tile"), one step early at most: the step after it waits
// the longer for it, so tapping or zigzagging never walks faster than its own pace.
mob/Monsters/proc/RmDriveNow(turn = 0)
	if(HP <= 0 || GoingToDie || Fainted || Sleeping || Stunned || remaster_root_until > world.time || rm_bound || !isturf(loc)) return 0
	var/pace = max(1, round(RemasterStepDelay() * RM_DRIVE_PACE))
	if(world.time < rm_drive_next)
		if(!turn || rm_drive_next - world.time > pace) return 0   // not a turn, or already a step ahead
		. = RmDriveStep()
		if(.) rm_drive_next += pace
		return
	. = RmDriveStep()
	rm_drive_next = world.time + (. ? pace : 2)

mob/Monsters/proc/RmDriveLoop()
	rm_driving = 1
	while((rm_drive_dx || rm_drive_dy) && world.time - rm_drive_seen <= RM_DRIVE_LOST)
		if(HP <= 0 || GoingToDie || Fainted || Sleeping || !isturf(loc) || Rm3DGone(src)) break
		if(world.time >= rm_drive_next) RmDriveNow()
		sleep(1)
	rm_drive_dx = 0
	rm_drive_dy = 0
	rm_driving = 0
	if(remaster_order_status == "Moving") remaster_order_status = "Idle"

// One step the way it is driven; a diagonal into a wall slides along it. 1 when it stepped.
mob/Monsters/proc/RmDriveStep()
	destination = null
	var/d = 0
	if(rm_drive_dy > 0) d |= NORTH
	else if(rm_drive_dy < 0) d |= SOUTH
	if(rm_drive_dx > 0) d |= EAST
	else if(rm_drive_dx < 0) d |= WEST
	if(!d) return 0
	var/list/tries = list(d)
	if((d & (NORTH|SOUTH)) && (d & (EAST|WEST))) tries += list(d & (NORTH|SOUTH), d & (EAST|WEST))
	var/mob/u = usr
	usr = src   // the ground rules see the walker, as a worker's step does (Chains/Move.dm, Orders)
	. = 0
	for(var/w in tries)
		var/turf/T = get_step(src, w)
		if(!T) continue
		remaster_push_step = 1   // the step goes to the 3D view this tick (View3D.dm)
		if(Move(T, w))
			. = 1
			break
		// one of its own people there: through them, as a walk goes through its side when its way goes on (Clip.dm),
		// so for this step its way is the tile beyond
		var/turf/B = get_step(T, w)
		if(B && (locate(/mob/Monsters) in T))
			destination = B
			var/ok = Move(T, w)
			destination = null
			if(ok)
				. = 1
				break
	if(!.) remaster_push_step = 0
	// The 3D slide onto the tile takes the step's own time, so the walk looks like a walk (the owner, 11-01: "slow down the
	// animation to make it look normal for the walk"; a 50 ms snap looked like hopping). It starts the tick the key came in.
	usr = u

// A click on a foe (View3D.dm Remaster3DClick): your ninja goes at it, as an attack order. 1 when it did.
Player/proc/RmNinjaClickFoe(atom/A)
	if(!istype(A, /mob/Monsters)) return 0
	var/mob/Monsters/H = RmMyNinja()
	var/mob/Monsters/E = A
	if(!H || E == H || E.HP <= 0 || E.GoingToDie || E.Owner == src || !RemasterHostile(H, E, 1)) return 0
	H.rm_drive_dx = 0
	H.rm_drive_dy = 0
	Selected = list(H)
	usr = src
	RemasterAttackOrder(E)
	return 1

// An order given by a click (Orders.dm RemasterOrder) in hero mode: refused, with a word, unless what it is for is beside
// your ninja (chop the tree it stands by, pick up what lies beside it). 1 when refused.
Player/proc/RmHeroOrderRefused(atom/A, kind)
	if(!kind && A) kind = RemasterClickKind(A)
	var/mob/Monsters/H = RmMyNinja()
	var/turf/T = A ? RemasterTurf(A) : null
	if(kind != "Move" && H && T && T.z == H.z && get_dist(H, T) <= 1) return 0
	RemasterNotice("Walk there with W A S D.")
	return 1

// --- Techniques on the number keys, at the mouse (the owner, 11-01: "like diablo how they do their skills and clicks") ---
// 1-4 are the card's techniques in its order. The page sends the key and what was under the mouse ("slot|x|y|ref", its
// v3target); the technique goes at once at that tile, or at the foe there.
var/list/rm_ninja_hotbar = list("substitution", "flashstep", "fireball", "kunai")

Player/proc/RmNinjaCastCommand(value)
	var/list/p = splittext("[value]", "|")
	var/slot = text2num(p[1])
	if(!slot || slot < 1 || slot > length(rm_ninja_hotbar)) return 0
	var/mob/Monsters/H = RmMyNinja()
	if(!H) return 0
	RmNinjaMerge()
	var/turf/T
	var/mob/Monsters/F
	if(length(p) >= 3) T = locate(text2num(p[2]), text2num(p[3]), H.z)
	if(length(p) >= 4 && length(p[4]))
		var/atom/A = locate(p[4])
		if(istype(A, /mob/Monsters) && A != H && !Rm3DGone(A)) F = A
	if(F) T = F.loc
	return H.RmNinjaCastAt(rm_ninja_hotbar[slot], T, F)

// A technique at a tile (and the foe on it, if any). 1 when it went.
mob/Monsters/proc/RmNinjaCastAt(id, turf/T, mob/Monsters/F)
	var/list/D = rm_moves[id]
	var/Player/P = istype(Owner, /Player) ? Owner : null
	if(!D || HP <= 0 || GoingToDie || Stunned || Fainted || Sleeping || !isturf(loc)) return 0
	if(RmMoveWait(src, id))
		if(P) P.RemasterNotice("[D["name"]] is ready in [round(RmMoveWait(src, id) / 10) + 1] s.")
		return 0
	if(D["kind"] != "self")
		if(!isturf(T) || T.z != z)
			if(P) P.RemasterNotice("Point at a tile or a foe for [D["name"]].")
			return 0
		if(get_dist(src, T) > D["range"])
			if(P) P.RemasterNotice("Too far for [D["name"]]: [D["range"]] tiles at most.")
			return 0
		if(F && !RemasterHostile(src, F, 1)) F = null
	if(!RmNinjaReady(id, D["kind"] == "self" ? null : T, 1)) return 0
	if(isturf(T) && T != loc) RmTurnToward(get_dir(src, T))
	var/done = 0
	switch(id)
		if("substitution") done = RmNinjaApply(id, null)
		if("fireball")
			remaster_root_until = max(remaster_root_until, world.time + D["seal"])
			destination = null
			RemasterHit(src, 0, "seal", src)
			var/turf/at = T
			spawn(D["seal"]) RmFireball(at)
			done = 1
		if("flashstep") done = F ? RmFlashStep(F) : RmBlinkTo(T)
		if("kunai")
			var/mob/Monsters/V = F
			if(!V)   // the first foe on its way to the tile
				for(var/turf/X in RemasterSpecialLine(T, get_dist(src, T)))
					var/list/L = RemasterSpecialFoes(list(X))
					if(length(L))
						V = L[1]
						break
			if(V) RmNinjaKunai(V)
			else RemasterHitAt(T.x, T.y, T.z, 0, "miss", src, null, "kunai")   // it lands on the tile
			done = 1
	if(!done) return 0
	RmNinjaPay(id)
	if(!rm_move_at) rm_move_at = list()
	rm_move_at[id] = world.time + (D["cool"] || 50) * rm_swing_pace
	rm_moves_last = lowertext(D["name"])
	rm_swung_at = world.time   // drawn as a blow (View3D.dm Remaster3DAct)
	return 1

// Flash step at an empty tile: there in a blink (beside it when it's taken).
mob/Monsters/proc/RmBlinkTo(turf/T)
	var/turf/L = RemasterSpecialOpen(T, src) ? T : null
	if(!L) for(var/turf/X in range(1, T)) if(RemasterSpecialOpen(X, src) && (!L || get_dist(src, X) < get_dist(src, L))) L = X
	if(!L) return 0
	var/sx = x
	var/sy = y
	loc = L
	destination = null
	RemasterSpecialFx("shadowstep", src, sx, sy, x, y, null)
	RemasterHit(src, 0, "flash", src)
	return 1

// --- Hits and effects this tick (the owner, 11-01: "make that as responsive as possible") ---
// The page plays every blow, damage number and technique effect from the HUD's model (Hits.dm rm_hits, Specials.dm
// rm_special_fx), which went to a player only on the track's half-second beat (QoL.dm), so a blow could show 0.5 s
// after it landed. Now a player whose unit strikes or is struck, or casts, gets an update at the end of that tick:
// at most one extra a tick, only for real players (a battle of NPCs costs nothing more).
var/list/rm_hud_hurry = list()
var/rm_hud_hurry_on = 0
Player/var/tmp/rm_hud_hurried_at = -1

proc/RmHudHurry(Player/P)
	if(!istype(P) || !P.client || !P.remaster_hud_ready || (P in rm_hud_hurry)) return
	rm_hud_hurry += P
	if(rm_hud_hurry_on) return
	rm_hud_hurry_on = 1
	spawn(0) RmHudHurryRun()

proc/RmHudHurryRun()
	var/list/L = rm_hud_hurry
	rm_hud_hurry = list()
	rm_hud_hurry_on = 0
	for(var/Player/P in L) if(P.client && P.rm_hud_hurried_at != world.time)
		P.rm_hud_hurried_at = world.time
		P.RemasterHUDTick()
