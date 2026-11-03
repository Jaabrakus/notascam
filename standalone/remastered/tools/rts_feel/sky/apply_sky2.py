#!/usr/bin/env python3
"""The sky job, parts 2 and 3 (rts-feel, 2026-10-25), server side; apply after apply_sky.py.
  2. Up to the Sky level by flying (the user: "yes thats perfect"; "the units dont fly high enough on sky level"): up there a
     flyer flies RM_SKY_CLEAR (2) higher, over the tallest sky peaks. Fly higher at a flyer's top surface height takes it
     to the same x, y on the Sky level at its lowest height there; Fly lower at its lowest sky height brings it back to
     the surface at its top height; at its top sky height there's no higher. A move under way goes on to the same spot
     on the new level; other orders stop. A camera locked on it goes with it (PlayMode.dm already follows a level change).
  3. The Sky is earned (the user: "that cant be for the normal users they have to earn it with units or ships"): a
     player sees the Sky level only while one of their own units is on it. The level change ("layer", the , key's ZUp,
     the world map's layer) is refused without one, and a player looking at the Sky when their last unit leaves is put
     back on the surface (a locked camera follows its unit instead). Host override: RM_SKY_OPEN=1 (env), or set
     rm_sky_open_all. The HUD model says "sky" so the page shows the Sky button only then.
  Flying.dm (the rules), HUD.dm (the "layer" command, the model's "sky"), Explore.dm (the world map's layer).
Exact-match edits, idempotent, Latin-1 safe.
    python3 tools/rts_feel/sky/apply_sky2.py <game folder>"""
import os, sys, tempfile
from pathlib import Path

EDITS = {
'Code/Remastered/Flying.dm': [
("""// The heights (tiles above the ground) a flyer can fly at, lowest first. The top dragon
// height still shows a dragon flying over its shadow with the camera zoomed all the way out.
proc/RmFlyHeights(mob/Monsters/M)
	if(M.Race == "Dragon") return list(3, 10, 20, 30)
	return list(2, 4, 6)

proc/RmFlyHeight(mob/Monsters/M)
	if(!M.Flying) return 0
	var/list/H = RmFlyHeights(M)
	return H[max(1, min(M.rm_fly_level, length(H)))]""",
"""// The heights (tiles above the ground) a flyer can fly at over the surface, lowest first. A dragon flies low over the
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
	return H[max(1, min(M.rm_fly_level, length(H)))]"""),
("""		RemasterNotice("[M.name] flies [H[M.rm_fly_level]] tiles up.")""",
"""		RemasterNotice(M.z == SKY_LAYER ? "[M.name] flies [RmFlyHeight(M)] tiles over the Sky level ([RM_SKY_H + RmFlyHeight(M)] up)." : "[M.name] flies [H[M.rm_fly_level]] tiles up.")"""),
("""		if(M.rm_fly_level < length(RmFlyHeights(M))) extra += list(list("Flying", "Fly higher"))
		if(M.rm_fly_level > 1) extra += list(list("Flying", "Fly lower"))""",
"""		if(M.rm_fly_level < length(RmFlyList(M)) || RmCanFlyUp(M)) extra += list(list("Flying", "Fly higher"))
		if(M.rm_fly_level > 1 || M.z == SKY_LAYER) extra += list(list("Flying", "Fly lower"))   // down to the surface from the Sky level"""),
("""		var/list/H = RmFlyHeights(M)
		M.rm_fly_level = max(1, min(M.rm_fly_level + (p[3] == "Fly higher" ? 1 : -1), length(H)))""",
"""		var/list/H = RmFlyList(M)
		if(p[3] == "Fly higher" && RmCanFlyUp(M)) return RmFlyLayer(M, SKY_LAYER, 1)                         // up to the Sky level
		if(p[3] == "Fly lower" && M.z == SKY_LAYER && M.rm_fly_level <= 1) return RmFlyLayer(M, GROUND_LAYER, length(RmFlyHeights(M)))   // down to the surface
		M.rm_fly_level = max(1, min(M.rm_fly_level + (p[3] == "Fly higher" ? 1 : -1), length(H)))"""),
("""// Open sky on the Sky level: no mountain top there, nothing built.""",
"""// --- Up to the Sky level by flying (the user, 2026-10-25: "yes thats perfect"; rts-feel) ---------------------------
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

// --- The Sky is earned (the user, 2026-10-25: "that cant be for the normal users they have to earn it with units or
// ships"): a player sees the Sky level only while one of their own units is on it (a flyer that flew up, a unit on a tall
// peak, later an airship). From the surface, flyers up there still show hovering above (View3D.dm D["air"]).
#ifndef RM_SKY_H
#define RM_SKY_H 10                      // the Sky level's height in blocks (planning/MOUNTAIN_HEIGHTS.md; ramps-gather's RmLevelOf will own it)
#endif
var/rm_sky_open_all = 0                  // the host's override: everyone sees the Sky (env RM_SKY_OPEN=1; tests)
Player/var/tmp/rm_sky_open = 0
Player/var/tmp/rm_sky_at = -100

world/New()
	. = ..()
	if(text2num(world.GetConfig("env", "RM_SKY_OPEN"))) rm_sky_open_all = 1

// One of their own units at the Sky level: up on layer 3 flying, or standing RM_SKY_H blocks up or more (a tall peak's
// summit, an island). A unit on an ordinary mountain top (layer 3, a few blocks up) is on the Surface level and doesn't
// earn it (planning/MOUNTAIN_HEIGHTS.md). Looked at once a second; a flight up or down looks again at once.
proc/RmSkyUnit(mob/Monsters/M)
	return M.z == SKY_LAYER && M.HP > 0 && (M.Flying || RemasterFeetOf(M) >= RM_SKY_H)

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

// Open sky on the Sky level: no mountain top there, nothing built."""),
],
'Code/Remastered/HUD.dm': [
("""		if("unitability") RemasterUseAbility(value)""",
"""		if("unitability") RemasterUseAbility(value)
		if("flylevel") RmFlySelection(value == "up")   // the selection's flyers up or down a step, the Sky level too (Flying.dm)"""),
("""		if("layer")
			var/level = text2num(value)
			if(level >= 1 && level <= world.maxz) loc = locate(x, y, level)""",
"""		if("layer")
			var/level = text2num(value)
			if(level == SKY_LAYER && !RmSkyOpen()) RmSkyShutNote()   // earned with a unit up there (Flying.dm)
			else if(level >= 1 && level <= world.maxz) loc = locate(x, y, level)"""),
("""		"x"=x, "y"=y, "z"=z, "maxx"=world.maxx, "maxy"=world.maxy, "maxz"=world.maxz,""",
"""		"x"=x, "y"=y, "z"=z, "maxx"=world.maxx, "maxy"=world.maxy, "maxz"=world.maxz, "sky"=RmSkyOpen(),"""),
],
'Code/Remastered/Explore.dm': [
("""			if(n >= 1 && n <= world.maxz) remaster_world_map_z = n""",
"""			if(n == SKY_LAYER && !RmSkyOpen()) RmSkyShutNote()   // the Sky is earned (Flying.dm)
			else if(n >= 1 && n <= world.maxz) remaster_world_map_z = n"""),
],
}


# ramps-gather's mountain heights step 1 (reports/ramps-gather/staged/heights_step1.py) gives RM_SKY_H as a constant
# (Peaks.dm var/const/RM_SKY_H) and RmLevelOf(atom): once they're in the game, the stand-ins here aren't put in.
SKY_H_STANDIN = """#ifndef RM_SKY_H
#define RM_SKY_H 10                      // the Sky level's height in blocks (planning/MOUNTAIN_HEIGHTS.md; ramps-gather's RmLevelOf will own it)
#endif
"""
SKY_UNIT_OLD = """	return M.z == SKY_LAYER && M.HP > 0 && (M.Flying || RemasterFeetOf(M) >= RM_SKY_H)"""
SKY_UNIT_LEVEL = """	return M.z == SKY_LAYER && M.HP > 0 && RmLevelOf(M) == "sky"   // Peaks.dm (ramps-gather): flying, or feet at RM_SKY_H or above"""


def adapt(game):
    code = ''.join(f.read_bytes().decode('latin-1') for f in (Path(game)/'Code/Remastered').glob('*.dm') if f.name != 'Flying.dm')
    const = 'var/const/RM_SKY_H' in code
    level = 'proc/RmLevelOf(' in code
    edits = EDITS['Code/Remastered/Flying.dm']
    for i, (old, new) in enumerate(edits):
        if const: new = new.replace(SKY_H_STANDIN, '')
        if level: new = new.replace(SKY_UNIT_OLD, SKY_UNIT_LEVEL)
        edits[i] = (old, new)
    return const, level


def main(game):
    const, level = adapt(game)
    if const or level: print(f'ramps-gather step 1 found: constant {const}, RmLevelOf {level}')
    for rel, edits in EDITS.items():
        p = Path(game)/rel
        t = p.read_bytes().decode('latin-1')
        done = 0
        for old, new in edits:
            if new in t: continue
            if t.count(old) != 1: sys.exit(f'{p}: no unique match for:\n{old[:160]}')
            t = t.replace(old, new); done += 1
        if done:
            fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.sky-'); os.write(fd, t.encode('latin-1')); os.close(fd)
            os.chmod(tmp, p.stat().st_mode); os.replace(tmp, p)
        print(f'{rel}: {done} edit(s)' if done else f'{rel}: already applied')


if __name__ == '__main__':
    main(sys.argv[1])
