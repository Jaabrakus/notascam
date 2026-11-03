// Mountain tops with no mountain under them (Remastered). A surface mountain's top is the
// walkable peak on the sky layer above it (Mountains.dm). Where the rock below is gone (dug
// out by the original dig code, or before tunnels kept a roof, or broken) and no tunnel roof
// is left, nothing holds the peak up: it opens to the sky, as it does when a tunnel's last
// roof block is mined. That goes for ground built on since (a village's walls and floors) as
// well: the 3D view would take the old peak for an upper floor, leave the houses without
// roofs, put a wall walk on their walls and draw the peak as a flat brown floor over them.
// Tunnels keep theirs (their roof holds it), and so do carved steps (Mountains.dm sees to
// those) and peaks something stands on. Checked round each player's view every few
// seconds; the change is kept in world saves.

#define RM_PEAK_SWEEP 50      // ticks between checks
#define RM_PEAK_HALF 20       // tiles each way from the player's view

Player/var/tmp/remaster_peak_next = 0

proc/RemasterPeakUnheld(turf/U)
	if(!U || U.z != SKY_LAYER || U.density || U.icon_state != "Peak") return 0
	var/turf/T = locate(U.x, U.y, GROUND_LAYER)
	if(!T || RemasterIsMountain(T) || T.remaster_carve || T.remaster_carve_plan) return 0   // rock, or a tunnel's roof (Breaking.dm)
	if(locate(/atom/movable) in U) return 0
	return 1

proc/RemasterPeakOpen(turf/U)
	U.icon_state = "Sky"
	U.name = "Sky"
	U.Content = "Sky"
	remaster_dirty_turfs["[U.x],[U.y],[U.z]"] = 1

Player/proc/RemasterPeakTick()
	if(world.time < remaster_peak_next || world.maxz < SKY_LAYER) return
	remaster_peak_next = world.time + RM_PEAK_SWEEP
	if(z != GROUND_LAYER && z != SKY_LAYER) return
	var/turf/A = locate(max(1, x - RM_PEAK_HALF), max(1, y - RM_PEAK_HALF), SKY_LAYER)
	var/turf/B = locate(min(world.maxx, x + RM_PEAK_HALF), min(world.maxy, y + RM_PEAK_HALF), SKY_LAYER)
	if(!A || !B) return
	for(var/turf/U in block(A, B)) if(RemasterPeakUnheld(U)) RemasterPeakOpen(U)

Player/RemasterLairTick()
	..()
	RemasterPeakTick()

// --- Levels by height (planning/MOUNTAIN_HEIGHTS.md, plan B; ramps-gather 2026-10-25) ----------------------------------
// Every place up on the sky layer has a height: a mountain's top or a gap dug in it, a wall walk, an upper floor. The
// Sky level is what is at the sky height or above (sky peak summits, sky islands, flyers up there). Below it, up on a
// mountain or a wall is the Surface level in everything the player sees and does: the camera's level, the level label
// (the page names it from the camera's layer), the camera following a unit up a mountain.
var/const/RM_SKY_H = 10      // the sky height in blocks, above every ordinary mountain (8 at most): the one source

// The level something is on: "surface", "sky", "caves" or "depths".
proc/RmLevelOf(atom/A)
	if(!A) return null
	switch(A.z)
		if(UNDERGROUND_LAYER) return "caves"
		if(HELL_LAYER) return "depths"
		if(SKY_LAYER)
			if(istype(A, /mob/Monsters))
				var/mob/Monsters/M = A
				return (M.Flying || RemasterFeetOf(M) >= RM_SKY_H) ? "sky" : "surface"
			var/turf/T = isturf(A) ? A : (isturf(A.loc) ? A.loc : null)
			var/list/top = T ? RemasterStandAt(T) : null      // a place to stand there: as high as its top
			if(top) return top[2] >= RM_SKY_H ? "sky" : "surface"
			return (T && (T.icon_state in list("Sky", "Chasm"))) ? "sky" : "surface"   // open sky; built floors and wall walks are a storey up
	return "surface"

// The layer the view shows for it: up on an ordinary mountain or a wall, the Surface's.
proc/RmViewLayer(atom/A)
	var/l = RmLevelOf(A)
	return l == "sky" ? SKY_LAYER : l == "caves" ? UNDERGROUND_LAYER : l == "depths" ? HELL_LAYER : GROUND_LAYER

// --- The sky layer over ordinary mountains (step 2) ---------------------------------------------------------------------
// A mountain's top below the sky height is the Surface's: the 3D's sky layer leaves it out (the rock's own top is drawn
// from the ground layer), and from the Sky view it is open sky for orders (only flyers go out there, at the sky height).
// RM_SKY_SPLIT=0 in the env turns it off: the peaks as before.
var/rm_sky_split = -1

proc/RmSkySplit()
	if(rm_sky_split < 0) rm_sky_split = world.GetConfig("env", "RM_SKY_SPLIT") == "0" ? 0 : 1
	return rm_sky_split

// The height of the top of the column under a mountain-top tile U (0 where there is no rock under it).
proc/RmPeakHeight(turf/U)
	var/turf/G = U ? locate(U.x, U.y, GROUND_LAYER) : null
	return (G && RemasterIsMountain(G)) ? RemasterTopHeight(G) : 0

// Open sky as the Sky level sees it, for orders given from the Sky view (P looking at the sky layer): open sky, or an
// ordinary mountain's top. rts-feel's open-sky rule (Flying.dm RmOpenSky) asks this where a player is at hand.
proc/RmSkyOpenFor(Player/P, turf/T)
	if(!istype(T) || T.z != SKY_LAYER || T.density) return 0
	if(T.icon_state == "Sky") return 1
	return RmSkySplit() && P && P.z == SKY_LAYER && T.icon_state == "Peak" && RmPeakHeight(T) < RM_SKY_H
