// The Gravedigger (Remastered): SS13's janitor and the old village sexton in one job.
//  - People's bodies (not animals: hunters butcher those) left lying within 30 tiles are carried
//    to the graveyard and buried with the original Bury effect (a Grave with the body inside it;
//    a spade is needed, as in the original menu). A buried body no longer rots, so it gives off no
//    miasma and no fever (Ailments.dm). When one of the village's own is buried, everyone
//    remembers it ("Our dead were laid to rest").
//  - The Graveyard (Build tab, 1 stone: a stone marker for a plot) is where: graves go on free
//    tiles within 4 tiles of it. Without one, on the nearest free ground 8 or more tiles from the
//    stockpile.
//  - With nobody to bury, the gravedigger cleans up: blood, green vomit, and rotten food lying
//    about (not on the stores) within 20 tiles of the stockpile.

var/list/rm_graveyards = list()

mob/WorkShops/RemasterGraveyard
	name = "Graveyard"
	icon = 'StoneItems.dmi'
	icon_state = "TombStone1"
	density = 1

	New()
		..()
		rm_graveyards += src

	Del()
		rm_graveyards -= src
		return ..()

	DblClick()
		if(istype(usr, /Player)) usr:RemasterNotice("The Graveyard: a villager on the Gravedigger job buries the dead around it.")

// Where the next grave goes: a free tile near a graveyard (or out past the edge of the village).
Player/proc/RemasterGraveSpot(mob/Monsters/M)
	var/turf/best
	var/best_d = 1#INF
	for(var/mob/WorkShops/RemasterGraveyard/G in rm_graveyards) if(G.Owner == src && G.z == M.z)
		for(var/turf/T in range(4, G))
			if(!RemasterGraveFree(T, M)) continue
			var/d = get_dist(T, M)
			if(d < best_d)
				best = T
				best_d = d
	if(best) return best
	var/turf/S = RemasterStockpile()
	var/atom/C = (S && S.z == M.z) ? S : M
	for(var/turf/T in range(14, C))
		if(get_dist(T, C) < 8 || !RemasterGraveFree(T, M)) continue
		var/d = get_dist(T, M)
		if(d < best_d)
			best = T
			best_d = d
	return best

// digger: the one who will dig there (standing on the tile doesn't take it).
proc/RemasterGraveFree(turf/T, mob/digger)
	if(!T || T.density || T.Detailed || T.icon_state == "FarmLand") return 0
	for(var/atom/movable/O in T) if(O != digger && (O.density || istype(O, /obj/Items/Graves) || istype(O, /obj/Items/Plants))) return 0
	return 1

// "Maric" for "{Sexton} Maric's Body": the dead's own name, without the house.
proc/RemasterDeadName(mob/Body/B)
	var/n = replacetext("[B.name]", "'s Body", "")
	var/i = findtext(n, "} ")
	return i ? copytext(n, i + 2) : n

// A body laid beside an Operating table is left for the Doctor (its limbs, Surgery.dm).
proc/RemasterBodyForTable(mob/Body/B)
	for(var/mob/WorkShops/RemasterSurgery/S in range(1, B)) return 1
	return 0

mob/Monsters/proc/RemasterCarriedBody()
	for(var/mob/Body/B in src) if(B.suffix == "(Carrying)") return B
	return null

// The original Bury effect (the body's menu in Death.dm): a Grave where the digger stands, the
// body inside it.
mob/Monsters/proc/RemasterBury(mob/Body/B)
	if(!B || B.loc != src || !isturf(loc)) return 0
	var/obj/Items/Graves/Grave/G = new(loc)
	G.name = "Grave of [RemasterDeadName(B)]"
	B.loc = G
	weight -= B.weight
	B.suffix = "(Burried)"
	var/Player/P = Owner
	if(istype(P))
		var/own = B.Owner == "[P]"
		P.RemasterLog("[RemasterBareName()] buried [RemasterDeadName(B)]", own ? "good" : "info", G)
		if(own) P.RemasterCheer("buried", "Our dead were laid to rest", 3, 2)
	RemasterSay(RemasterLine(list("Rest well.", "Ashes to ashes...", "Sleep now.")), 1)
	return 1

// Something the gravedigger tidies away: blood, vomit, rotten food lying about.
proc/RemasterIsMess(atom/movable/A)
	if(istype(A, /obj/Bloods/RmBloodPool)) return 0   // a pool: its tiles, one by one (BloodPools.dm)
	if(istype(A, /obj/Bloods) || istype(A, /obj/RemasterVomit)) return 1
	if(istype(A, /obj/Items/Food) && A:rm_rotten && !RemasterOnStore(A)) return 1
	return 0

mob/Monsters/proc/RemasterGravediggerTick(Player/P)
	if(Race == "Spider" || Wagon)
		remaster_work_status = "This unit can't dig graves"
		return
	var/turf/S = P.RemasterStockpile()
	var/atom/C = (S && S.z == z) ? S : src
	// 1. Carrying someone: to the graveyard, then bury them.
	var/mob/Body/B = RemasterCarriedBody()
	if(B)
		if(!RemasterHasSpade())
			remaster_work_status = "Gravedigger: needs a spade to bury the dead (Carpentry: wooden spade)"
			return
		var/turf/G = P.RemasterGraveSpot(src)
		if(!G)
			remaster_work_status = "Gravedigger: no free ground for a grave"
			return
		if(loc != G)
			destination = G
			remaster_work_destination = G
			remaster_work_status = "Gravedigger: [B.loc == src ? "carrying" : "dragging"] [RemasterDeadName(B)] to the graveyard"
			return
		RemasterBury(B)
		remaster_work_status = "Gravedigger: buried [RemasterDeadName(B)]"
		return
	// 2. A body lying about: pick it up (the dead weigh what they weigh: carried anyway).
	var/mob/Body/found
	var/best = 1#INF
	for(var/mob/Body/X in range(30, C))
		if(!isturf(X.loc) || X.Critter || X.Race == "Fish" || X.suffix || RemasterBodyForTable(X)) continue
		var/d = get_dist(X, src)
		if(d < best)
			found = X
			best = d
	if(found)
		if(!RemasterWorkToward(found, "the dead")) return
		if(!(rm_body_drag && RmDragStart(found)))   // dragged to the graveyard (BodyDrag.dm)
			if(!PickUpItem(found)) ForcePickUpItem(found)
		remaster_work_status = "Gravedigger: [found.loc == src ? "took up" : "took hold of"] [RemasterDeadName(found)]"
		return
	// 3. Cleaning.
	var/atom/movable/mess
	best = 1#INF
	for(var/atom/movable/X in range(20, C)) if(isturf(X.loc) && RemasterIsMess(X))
		var/d = get_dist(X, src)
		if(d < best)
			mess = X
			best = d
	var/turf/pool_tile = RmBloodPoolNearest(C, 20, src)   // a pool's tile (BloodPools.dm)
	if(pool_tile && get_dist(pool_tile, src) < best) mess = pool_tile
	if(mess)
		if(!RemasterWorkToward(mess, "the mess")) return
		var/n = 0
		for(var/atom/movable/X in range(1, src)) if(isturf(X.loc) && RemasterIsMess(X))
			del X
			n++
		n += RmBloodPoolClearNear(src, 1)   // a pool's tiles beside it (BloodPools.dm)
		remaster_work_status = "Gravedigger: cleaned up [n] mess[n == 1 ? "" : "es"]"
		if(prob(30)) RemasterSay(RemasterLine(list("Who did this...", "Filthy.", "*scrub scrub*")))
		return
	remaster_work_status = "Gravedigger: the village is clean"

// The catch-up (Away.dm): the dead within reach are buried, the mess cleared, without the walking.
mob/Monsters/proc/RemasterAwayGravedig(Player/P)
	if(!RemasterHasSpade()) return
	var/turf/S = P.RemasterStockpile()
	var/atom/C = (S && S.z == z) ? S : src
	var/turf/home = loc
	var/n = 0
	for(var/mob/Body/X in range(30, C))
		if(!isturf(X.loc) || X.Critter || X.Race == "Fish" || X.suffix || n >= REMASTER_AWAY_JOBS || RemasterBodyForTable(X)) continue
		var/turf/G = P.RemasterGraveSpot(src)
		if(!G) break
		ForcePickUpItem(X)
		loc = G
		if(RemasterBury(X)) n++
	for(var/atom/movable/X in range(20, C)) if(isturf(X.loc) && RemasterIsMess(X)) del X
	RmBloodPoolClearNear(C, 20)   // pools' tiles (BloodPools.dm)
	loc = home
	P.RemasterAwayAdd("buried", n)
