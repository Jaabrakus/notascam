// A new people never starts beside hostile creatures, nor on bare ground with nothing to build from. The
// original LocateValidLocation (Restart.dm) only avoids spots with people in view, so a start could land
// next to wandering undead or a beast, or in open desert with no tree to chop for the first campfire.
// Restart() gives each new starting unit its fair start (RemasterStartSkills, Rarity.dm) right after
// making the army on one spot and before spreading it out; here the first of them picks the nearest spot
// with no threat within REMASTER_SAFE_START tiles and trees (water too, if it can) within
// REMASTER_START_LAND, and the rest of that start follows it.

#define REMASTER_SAFE_START 24
#define REMASTER_START_GRACE 6000   // 10 game minutes: see LocateTarget below
#define REMASTER_START_LAND 15

var/list/remaster_safe_starts = list()     // "time|x,y,z" of a start -> the safe turf it moved to (or 0)

mob/Monsters/RemasterStartSkills()
	. = ..()
	RemasterSafeStart()
	remaster_grace_until = world.time + REMASTER_START_GRACE
	spawn(1) RemasterStartRoom()   // once Restart() has handed out the kit

// Room in the pack for the first gathering (playtest: an Elf's starting kit, axe and wooden armour, all but filled
// its pack, so its first tree gave it no wood). Restart() gives an overloaded starter 30 more; every starter now has
// room for three logs (20 each) once its kit is in its bag.
#define REMASTER_START_ROOM 60
mob/Monsters/proc/RemasterStartRoom()
	if(weightmax - weight < REMASTER_START_ROOM) weightmax = weight + REMASTER_START_ROOM

// The first minutes: a start can be clear of hostiles and still be found by a roaming pack (playtest: seven
// skeletons killed a new Dwarf company in 90 s). For REMASTER_START_GRACE ticks after its start, wild creatures
// and NPC bands don't pick a new company's people as their target (LocateTarget, Monster AI.dm). It ends early
// for a unit its player sends to attack, and anyone can still fight back when struck.
mob/Monsters/var/tmp/remaster_grace_until = 0

mob/Monsters/LocateTarget(RANGE = 5)
	. = ..(RANGE)
	var/mob/Monsters/M = .
	if(istype(M) && M.remaster_grace_until > world.time && !istype(Owner, /Player)) return null

Player/RemasterAttackOrder(atom/A)
	for(var/mob/Monsters/M in Selected) if(M.Owner == src) M.remaster_grace_until = 0
	return ..()

// The frog and lizard swamp (Restart.dm's Lizardman and Frogman box) is their land: no one else starts in it.
proc/RemasterStartSwampOf(mob/Monsters/M, turf/T)
	return T && T.z == 1 && T.x >= 175 && T.x <= 365 && T.y >= 675 && T.y <= 785 && !(M.Race in list("Lizardman", "Frogman"))

// Creatures that would set on a new arrival: NPC bands of another race (undead: anyone living), and wild
// beasts. Critters, other players' people and NPCs of the arrival's own race leave it alone.
proc/RemasterStartThreat(mob/Monsters/M, mob/Monsters/E)
	if(!istype(E) || E == M || E.HP <= 0 || E.GoingToDie || E.Critter || E.CantKill || E.Wagon) return 0
	if(istype(E, /mob/Monsters/Chests) || RemasterIsSiege(E)) return 0
	if(ismob(E.Owner)) return 0
	if(istext(E.Owner))
		if(E.Owner == "{NPC Undead}") return !M.Undead
		if(E.Owner == "{NPC Alliance}") return 0
		return E.Race != M.Race
	return 1

// home: the spot the army was made on; the rest of that start (not owned yet) stands there.
proc/RemasterStartThreatNear(mob/Monsters/M, turf/T, turf/home, reach = REMASTER_SAFE_START)
	for(var/mob/Monsters/E in range(reach, T)) if(E.loc != home && RemasterStartThreat(M, E)) return E
	return null

proc/RemasterStartSpotOK(turf/T)
	if(!T || T.density || T.icon_state == "Sky" || findtext("[T.icon_state]", "Water") || istype(T, /turf/grounds/waters)) return 0
	if(T.x < 4 || T.y < 4 || T.x > world.maxx - 3 || T.y > world.maxy - 3) return 0
	for(var/turf/N in range(1, T)) if(N.density || N.remaster_roof) return 0   // open ground under the sky, not a tunnel in a mountain
	for(var/atom/movable/A in T) if(A.density) return 0
	return 1

// What the land round a spot offers a new people: 0 nothing, 1 trees to chop, 2 trees and water.
proc/RemasterStartLand(turf/T)
	var/trees = 0
	var/water = 0
	for(var/turf/N in range(REMASTER_START_LAND, T))
		if(N.Tree && !N.Cactus) trees++
		else if(!water && (istype(N, /turf/grounds/waters) || findtext("[N.icon_state]", "water"))) water = 1
	if(trees < 3) return 0
	return water ? 2 : 1

// Migrants joining a realm come in near its stockpile (RemasterMigrantChoice, Realms.dm), and anyone settling
// beside a neighbour chose to: a start that close to another player's stockpile stays where it is.
proc/RemasterStartNearRealm(turf/T)
	for(var/Player/R in world) if(R.key)
		var/turf/S = R.RemasterStockpile()
		if(S && S.z == T.z && get_dist(S, T) <= 30) return 1
	return 0

mob/Monsters/proc/RemasterSafeStart()
	if(!isturf(loc) || RemasterStartNearRealm(loc)) return
	var/turf/here = loc
	var/key = "[world.time]|[here.x],[here.y],[here.z]"
	if(!(key in remaster_safe_starts))
		var/turf/found = 0
		var/mob/Monsters/E = RemasterStartThreatNear(src, here, here)
		var/land = RemasterStartSwampOf(src, here) ? 0 : RemasterStartLand(here)
		if(E || !land)
			// rings outwards, so the start stays in the land its race was sent to: the nearest ring with a safe
			// spot with trees (one with water too, if that ring has one), else (only to get away from a threat)
			// the first safe spot
			var/turf/trees
			var/turf/safe
			// far enough to leave the swamp; a treeless start looks further (open desert: playtest r13) before giving up
			var/reach = RemasterStartSwampOf(src, here) ? 128 : (E ? 72 : 160)
			for(var/r = 8, r <= reach && !found, r += 8)
				for(var/tries = 0, tries < 16 && !found, tries++)
					var/a = rand(0, 359)
					var/turf/T = locate(round(here.x + cos(a) * r), round(here.y + sin(a) * r), here.z)
					if(!RemasterStartSpotOK(T) || RemasterStartSwampOf(src, T) || RemasterStartThreatNear(src, T, here, REMASTER_SAFE_START + 3)) continue   // + the army spreading out
					var/l = RemasterStartLand(T)
					if(l == 2) found = T
					else if(l == 1 && !trees) trees = T
					else if(!safe) safe = T
				if(!found && trees) found = trees   // no farther than the first ring with trees
			if(!found) found = trees || (E ? safe : 0)
			world.log << "Remastered: [E ? "[E.name] near the start" : (RemasterStartSwampOf(src, here) ? "a start in the swamp" : "no trees near the start")] at [here.x],[here.y],[here.z]; [found ? "moved it to [found.x],[found.y]" : "no better spot nearby"]"
		if(length(remaster_safe_starts) > 50) remaster_safe_starts.Cut()
		remaster_safe_starts[key] = found
	var/turf/spot = remaster_safe_starts[key]
	if(spot) loc = spot
