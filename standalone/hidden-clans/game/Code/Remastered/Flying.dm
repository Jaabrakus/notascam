// Flying (Remastered). What flies goes over what stops walkers on the surface and in the
// sky - water, walls, rock, trees, other units - and is drawn in the air in 3D at its
// height (View3D.dm sends it as "fly"; the page eases it up for a take-off and down for a
// landing). The player sets the height with Fly higher / Fly lower on the skill bar: a
// dragon can climb as high as the camera can zoom out to follow it. A flyer can't land on
// top of what it flew over.

mob/Monsters/var/tmp/rm_fly_level = 1   // which of RmFlyHeights it flies at

// The heights (tiles above the ground) a flyer can fly at over the surface, lowest first. A dragon flies low over the
// surface and high on the Sky level (the user, 2026-10-25: "Surface low, Sky high"): Fly higher from its top here takes it
// up there, so higher always goes up.
proc/RmFlyHeights(mob/Monsters/M)
	if(M.Race == "Dragon") return list(3, 6, 9)
	return list(2, 4, 6)

// Up on the Sky level, over the sky plane (the 3D view draws D["fly"] above the ground under it: the sky plane up there,
// world-look). A dragon 2/12/22 (12/22/32 from the surface, over its 9 here); the others their surface heights plus
// RM_SKY_CLEAR, over the tallest sky peaks (12 high, 2 over the Sky height; the user: "the units dont fly high enough on
// sky level").
#define RM_SKY_CLEAR 2
proc/RmSkyFlyHeights(mob/Monsters/M)
	if(M.Race == "Dragon") return list(2, 12, 22)
	. = list()
	for(var/h in RmFlyHeights(M)) . += h + RM_SKY_CLEAR

// The heights for the layer it's on.
proc/RmFlyList(mob/Monsters/M)
	return M.z == SKY_LAYER ? RmSkyFlyHeights(M) : RmFlyHeights(M)

proc/RmFlyHeight(mob/Monsters/M)
	if(!M.Flying) return 0
	var/list/H = RmFlyList(M)
	return H[max(1, min(M.rm_fly_level, length(H)))]

proc/RmFliesOver(atom/movable/A, turf/T)
	if(!istype(A, /mob/Monsters) || !T || !A:Flying) return 0
	return T.z == GROUND_LAYER || T.z == SKY_LAYER

// turf/grounds/Enter: this file's part is step RmChainEnter_Flying in Code/Remastered/Chains/Enter.dm

// Something under a flyer it can't stand on: dense ground (water, a wall, rock) or a
// dense thing that isn't flying too.
proc/RmLandingBlocked(mob/Monsters/M)
	var/turf/T = M.loc
	if(!isturf(T)) return 0
	if(T.density) return 1
	if(RmOpenSky(T)) return 1   // over open sky: nothing below to land on
	for(var/atom/movable/A in T) if(A != M && A.density && !(istype(A, /mob/Monsters) && A:Flying)) return 1
	return 0

mob/Fly(SAY = 1, FLY)
	var/was = Flying
	if(!Flying && (FLY == null || FLY == "Fly") && istype(src, /mob/Monsters) && src:rm_bound) return   // chained down (Taming.dm)
	if(!Flying && (FLY == null || FLY == "Fly") && RmWingsBroken(src))   // Beasts.dm
		if(SAY && ismob(Owner)) Owner << "[src]'s wings are too badly hurt to fly."
		return
	if(Flying && (FLY == null || FLY == "Land") && istype(src, /mob/Monsters) && RmLandingBlocked(src))
		if(SAY && ismob(Owner)) Owner << "[src] can't land here: there's no open ground below."
		return
	. = ..()
	if(istype(src, /mob/Monsters))
		if(!was && Flying) src:rm_fly_level = 1   // takes off low
		RmBeastFeetUpdate(src)                     // a beast's feet leave the ground, or come down (Beasts.dm)

// --- Up to the Sky level by flying (the user, 2026-10-25: "yes thats perfect"; rts-feel) ---------------------------
// At its top height over the surface a flyer can climb on to the Sky level, the same x, y, at its lowest height there.
proc/RmCanFlyUp(mob/Monsters/M)
	if(!M.Flying || M.z != GROUND_LAYER || world.maxz < SKY_LAYER || M.rm_fly_level < length(RmFlyHeights(M))) return 0
	var/turf/U = locate(M.x, M.y, SKY_LAYER)
	return U && !U.density

// To level z at height level: a move under way goes on to the same spot there, other orders stop (they were for the
// level it left). The view follows a locked camera (PlayMode.dm); the Sky opens for its player (RmSkyOpen).
proc/RmFlyLayer(mob/Monsters/M, z, level)
	var/turf/T = locate(M.x, M.y, z)
	if(!T || (z == SKY_LAYER && T.density)) return 0
	M.loc = T
	RmBeastFeetUpdate(M)   // a great beast's feet go with it (Beasts.dm)
	M.rm_fly_level = level
	M.remaster_abilities_at = -1000
	var/list/moves = (M.remaster_active ? list(M.remaster_active) : list()) + (M.remaster_orders || list())
	var/keep = 1
	for(var/datum/remaster_order/O in moves) if(O.kind != "Move" || !isturf(O.target)) keep = 0
	if(keep && length(moves))
		for(var/datum/remaster_order/O in moves)
			O.target = locate(O.target.x, O.target.y, z)
			O.path = null
			O.partial = 0
		M.destination = null
		M.RmWalkSoon()
	else if(length(moves) || M.remaster_attack)
		M.RemasterAttackStop()
		M.RemasterCancelOrders()
	var/Player/P = M.Owner
	if(istype(P))
		P.rm_sky_at = -100   // look again
		var/list/H = RmFlyHeights(M)
		P.RemasterNotice(z == SKY_LAYER ? "[M.name] flies up to the Sky level, [RM_SKY_H + RmFlyHeight(M)] tiles up." : "[M.name] flies down to the surface, [H[level]] tiles up.")
	return 1

// The selection's flyers a step up or down together (a group's Fly higher / Fly lower, HUD "flylevel"): walkers stay.
Player/proc/RmFlySelection(up)
	. = 0
	var/said = remaster_notice
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.Flying && M.HP > 0)
		var/list/H = RmFlyList(M)
		if(up && RmCanFlyUp(M)) . += RmFlyLayer(M, SKY_LAYER, 1)
		else if(!up && M.z == SKY_LAYER && M.rm_fly_level <= 1) . += RmFlyLayer(M, GROUND_LAYER, length(RmFlyHeights(M)))
		else
			var/was = M.rm_fly_level
			M.rm_fly_level = max(1, min(M.rm_fly_level + (up ? 1 : -1), length(H)))
			M.remaster_abilities_at = -1000
			if(M.rm_fly_level != was) .++
	if(!.) RemasterNotice(up ? "None of the selected can fly higher." : "None of the selected can fly lower.")
	else if(remaster_notice == said) RemasterNotice("[. == 1 ? "1 flyer flies" : "[.] flyers fly"] [up ? "higher" : "lower"].")   // it said nothing when it worked (a flight up or down a level says its own)

// --- The Sky is earned (the user, 2026-10-25: "that cant be for the normal users they have to earn it with units or
// ships"): a player sees the Sky level only while one of their own units is on it (a flyer that flew up, a unit on a tall
// peak, later an airship). From the surface, flyers up there still show hovering above (View3D.dm D["air"]).
var/rm_sky_open_all = 0                  // the host's override: everyone sees the Sky (env RM_SKY_OPEN=1; tests)
Player/var/tmp/rm_sky_open = 0
Player/var/tmp/rm_sky_at = -100

// world/New: this file's part is step RmChainWorldNew_Flying in Code/Remastered/Chains/WorldNew.dm

// One of their own units at the Sky level: up on layer 3 flying, or standing RM_SKY_H blocks up or more (a tall peak's
// summit, an island). A unit on an ordinary mountain top (layer 3, a few blocks up) is on the Surface level and doesn't
// earn it (planning/MOUNTAIN_HEIGHTS.md). Looked at once a second; a flight up or down looks again at once.
proc/RmSkyUnit(mob/Monsters/M)
	return M.z == SKY_LAYER && M.HP > 0 && RmLevelOf(M) == "sky"   // Peaks.dm (ramps-gather): flying, or feet at RM_SKY_H or above

Player/proc/RmSkyOpen()
	if(rm_sky_open_all) return 1
	if(world.time - rm_sky_at < 10) return rm_sky_open
	rm_sky_at = world.time
	rm_sky_open = 0
	for(var/mob/Monsters/M in UnitList) if(M.z == SKY_LAYER && M.Owner == src && RmSkyUnit(M))
		rm_sky_open = 1
		break
	return rm_sky_open

Player/proc/RmSkyShutNote()
	RemasterNotice("The Sky is out of reach: get one of your units up there first (a flyer flying up, or a unit on a tall peak).")

// Looking at the Sky with no unit left there: back to the surface (a locked camera follows its unit instead).
Player/RemasterPlayModeTick()
	. = ..()
	if(z == SKY_LAYER && !remaster_lock && !RmSkyOpen())
		loc = locate(x, y, GROUND_LAYER)
		RemasterNotice("None of your units are in the sky now: the camera is back on the surface.")

// The , key (Actions.dm "zup"): from the surface up to the Sky only once it's open.
obj/Hud/ZUp/DblClick()
	if(istype(usr, /Player) && usr.z == GROUND_LAYER && !usr:RmSkyOpen())
		usr:RmSkyShutNote()
		return
	return ..()

// Open sky on the Sky level: no mountain top there, nothing built. Only flyers go out over it, and they can stop
// there (they hover); a walker can't (the user, 2026-10-25: "so make the sky level clickable tiles"; rts-feel).
proc/RmOpenSky(turf/T)
	return istype(T) && T.z == SKY_LAYER && T.icon_state == "Sky" && !T.density

proc/RmAllFly(list/group)
	. = 0
	for(var/atom/A in group)
		if(!istype(A, /mob/Monsters) || !A:Flying) return 0
		. = 1

// Only flyers selected (of your own, alive): a click on rock flies them over it, on top,
// instead of mining it (Orders.dm RemasterOrder, HoverCheck.dm).
Player/proc/RemasterOnlyFlyers()
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0)
		if(!M.Flying) return 0
		. = 1

// What a click on A orders the selected units to do: the order kind (RemasterOrderKind),
// but rock is no mine to a flyer: it flies there.
Player/proc/RemasterClickKind(atom/A)
	. = RemasterOrderKind(A)
	if(. == "Mine" && RemasterOnlyFlyers()) . = "Move"

// The skill bar: a flyer's height, next to the game's own Fly / Land.
Player/RemasterAbilities(mob/Monsters/M)
	. = ..()
	if(istype(M) && M.Flying && M.Owner == src)
		var/list/extra = list()
		if(M.rm_fly_level < length(RmFlyList(M)) || RmCanFlyUp(M)) extra += list(list("Flying", "Fly higher"))
		if(M.rm_fly_level > 1 || M.z == SKY_LAYER) extra += list(list("Flying", "Fly lower"))   // down to the surface from the Sky level
		. = . + extra

Player/RemasterUseAbility(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) == 3 && p[2] == "Flying")
		var/mob/Monsters/M = RemasterUIUnit(p[1])
		if(!istype(M) || M.Owner != src || !M.Flying) return 0
		var/list/H = RmFlyList(M)
		if(p[3] == "Fly higher" && RmCanFlyUp(M)) return RmFlyLayer(M, SKY_LAYER, 1)                         // up to the Sky level
		if(p[3] == "Fly lower" && M.z == SKY_LAYER && M.rm_fly_level <= 1) return RmFlyLayer(M, GROUND_LAYER, length(RmFlyHeights(M)))   // down to the surface
		M.rm_fly_level = max(1, min(M.rm_fly_level + (p[3] == "Fly higher" ? 1 : -1), length(H)))
		M.remaster_abilities_at = -1000
		RemasterNotice(M.z == SKY_LAYER ? "[M.name] flies [RmFlyHeight(M)] tiles over the Sky level ([RM_SKY_H + RmFlyHeight(M)] up)." : "[M.name] flies [H[M.rm_fly_level]] tiles up.")
		return 1
	return ..()
