#!/usr/bin/env python3
"""Orders out over open sky on the Sky level (rts-feel, 2026-10-25; the user: "so make the sky level clickable tiles"):
flyers fly there and spread over it, walkers stay. Server half (the page's half: apply_sky_page.py).
  Flying.dm      RmOpenSky(T), RmAllFly(group); a flyer can't land over open sky (nothing below to land on)
  Orders.dm      RemasterTilePlaces: open sky holds a group that all flies (they hover); RemasterOrder: a Move out over
                 open sky takes the flyers only, the walkers stay (a notice says so); none fly: no order
  Formations.dm  an all-flyer group on the Sky level plans its slots with the DM flood: the engine's (RmSlots.cs Places)
                 doesn't know open sky holds flyers yet
  HoverCheck.dm  the verdict: "Fly there" for the flyers, "can't fly, stays" for each walker (bad); none fly: bad
Exact-match edits, idempotent, Latin-1 safe.
    python3 tools/rts_feel/sky/apply_sky.py <game folder>"""
import os, sys, tempfile
from pathlib import Path

EDITS = {
'Code/Remastered/Flying.dm': [
("""proc/RmLandingBlocked(mob/Monsters/M)
	var/turf/T = M.loc
	if(!isturf(T)) return 0
	if(T.density) return 1
""", """proc/RmLandingBlocked(mob/Monsters/M)
	var/turf/T = M.loc
	if(!isturf(T)) return 0
	if(T.density) return 1
	if(RmOpenSky(T)) return 1   // over open sky: nothing below to land on
"""),
("""// Only flyers selected (of your own, alive): a click on rock flies them over it, on top,
// instead of mining it (Orders.dm RemasterOrder, HoverCheck.dm).""",
"""// Open sky on the Sky level: no mountain top there, nothing built. Only flyers go out over it, and they can stop
// there (they hover); a walker can't (the user, 2026-10-25: "so make the sky level clickable tiles"; rts-feel).
proc/RmOpenSky(turf/T)
	return istype(T) && T.z == SKY_LAYER && T.icon_state == "Sky" && !T.density

proc/RmAllFly(list/group)
	. = 0
	for(var/atom/A in group)
		if(!istype(A, /mob/Monsters) || !A:Flying) return 0
		. = 1

// Only flyers selected (of your own, alive): a click on rock flies them over it, on top,
// instead of mining it (Orders.dm RemasterOrder, HoverCheck.dm)."""),
],
'Code/Remastered/Orders.dm': [
("""proc/RemasterTilePlaces(turf/T, list/group)
	if(!T || T.density || (T.icon_state in list("Sky", "Chasm"))) return 0""",
"""proc/RemasterTilePlaces(turf/T, list/group)
	if(!T || T.density || (T.icon_state in list("Sky", "Chasm")) && !(RmOpenSky(T) && RmAllFly(group))) return 0   // open sky holds flyers (Flying.dm)"""),
("""	// A stale dying selection must not take an order: the engine's filter (Native.dm, the same), else DM's.
	var/list/group = rm_native_plan ? rm_plan_group(Selected, src, UnitList, /mob/Monsters, null) : null""",
"""	// Out over open sky on the Sky level (Flying.dm RmOpenSky): the flyers go, the walkers stay where they are. The order
	// is planned with the flyers as the selection (the selection itself is back before any unit is given its order).
	var/list/rm_sky_all
	if(kind == "Move" && RmOpenSky(A))
		var/list/fly = list()
		var/walkers = 0
		for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0)
			if(M.Flying) fly += M
			else walkers++
		if(!length(fly))
			RemasterNotice("Only flyers can go out over open sky.")
			return 0
		if(walkers)
			RemasterNotice("[walkers == 1 ? "1 unit stays" : "[walkers] units stay"]: only flyers can go out over open sky.")
			rm_sky_all = Selected
			Selected = fly
	// A stale dying selection must not take an order: the engine's filter (Native.dm, the same), else DM's.
	var/list/group = rm_native_plan ? rm_plan_group(Selected, src, UnitList, /mob/Monsters, null) : null"""),
("""	// Units on another level go by the nearest stairs, then spread along the far side.
	var/list/climbers = kind == "Move" && !slots ? RemasterLevelSlots(A) : null""",
"""	// Units on another level go by the nearest stairs, then spread along the far side.
	var/list/climbers = kind == "Move" && !slots ? RemasterLevelSlots(A) : null
	if(rm_sky_all) Selected = rm_sky_all"""),
],
'Code/Remastered/Formations.dm': [
("""	if(seed && !heights && rm_native_slots) RP = rm_slot_reach(T, R, seed, lead_unit, group, pass, 'Stairs.dmi', /obj/RmBeastFoot, /mob/Monsters, GROUND_LAYER, SKY_LAYER, RmSide(lead_unit), /mob/Monsters/RemasterSiege)""",
"""	// (all flyers on the Sky level: DM's, where open sky holds them, Orders.dm RemasterTilePlaces; RmSlots.cs doesn't yet)
	if(seed && !heights && rm_native_slots && !(T.z == SKY_LAYER && RmAllFly(group))) RP = rm_slot_reach(T, R, seed, lead_unit, group, pass, 'Stairs.dmi', /obj/RmBeastFoot, /mob/Monsters, GROUND_LAYER, SKY_LAYER, RmSide(lead_unit), /mob/Monsters/RemasterSiege)"""),
],
'Code/Remastered/HoverCheck.dm': [
("""		var/why
		if(M.z != T.z) why =""",
"""		var/why
		if(kind == "Move" && RmOpenSky(T) && !M.Flying) why = "can't fly, stays"   // open sky: flyers only (Flying.dm)
		else if(M.z != T.z) why ="""),
("""		if(why == "no stairs to that level nearby") bad++""",
"""		if(why == "no stairs to that level nearby" || why == "can't fly, stays") bad++"""),
("""	var/text = (kind == "Move" && T && T.density && RemasterOnlyFlyers()) ? "Fly on top" : kind""",
"""	var/text = (kind == "Move" && T && T.density && RemasterOnlyFlyers()) ? "Fly on top" : kind
	if(kind == "Move" && RmOpenSky(T)) text = ok ? "Fly there" : "Only flyers can go out over open sky\""""),
],
}


# ramps-gather's mountain heights step 2 (Peaks.dm RmSkyOpenFor(P, T)): open sky as the Sky level sees it for orders
# given from the Sky view (an ordinary mountain's top too, drawn below with the surface). Where a Player is at hand (the
# order, the hover verdict) it asks that once it's in the game; RmOpenSky stays for the rest (landing, room to stop).
def adapt(game):
    code = ''.join(f.read_bytes().decode('latin-1') for f in (Path(game)/'Code/Remastered').glob('*.dm'))
    if 'proc/RmSkyOpenFor(' not in code: return False
    for rel, a, b in (('Code/Remastered/Orders.dm', 'if(kind == "Move" && RmOpenSky(A))', 'if(kind == "Move" && RmSkyOpenFor(src, A))'),
                      ('Code/Remastered/HoverCheck.dm', 'RmOpenSky(T)', 'RmSkyOpenFor(src, T)')):
        EDITS[rel] = [(old, new.replace(a, b)) for old, new in EDITS[rel]]
    return True


def main(game):
    if adapt(game): print('ramps-gather step 2 found: the order and the hover verdict ask RmSkyOpenFor')
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
