// Ships (naval, 10-29; the owner: "i would love having a nice aweseome ships and naval stuff"). Built at a Carpentry
// within 8 tiles of deep water and launched onto it, they are crewed engines of their own kind (Siege.dm: owned, saved,
// wrecked and burnt as engines are), sailing only on water:
//   Rowboat   4 wood           4 aboard; quick (3 ticks a tile with 2 rowing); goes over shallows and fords too
//   Longship  12 wood, 1 iron  12 aboard; a war ship: rams enemy ships (160 a ram, +20 a rower up to 6, every 3 s);
//                              fastest of all with 6 rowing (2 ticks a tile), a crawl with one
//   Cog       16 wood          10 aboard; a broad sailing ship (4 ticks a tile with anyone at the helm), the toughest
// Select people and click your ship: they go to it (to the water's edge, or swimming) and board. Select the ship and
// click water: it sails there; click land: it sails beside it and everyone aboard steps ashore there. Attack-click an
// enemy ship with a longship (a realm at war, or nobody's): it closes and rams. A ship moves only with its owner's
// people aboard. One at 0 sinks: those aboard go into the water and swim (Swim.dm), those who can't are washed ashore;
// its timbers come ashore as wood. With people aboard it sees as a unit does (Fog.dm). Saved with people aboard, they
// come back ashore beside it (Captives.dm Write).
#define RM_SHIP_LAUNCH 8      // a carpentry this close to deep water can launch one
#define RM_SHIP_SEARCH 9000   // tiles a ship's route search looks at, at most
var/list/rm_ships = list()
var/rm_ship_loop = 0
proc/RmShipLoop()     // every tick: a ship steps at its own pace (2-12 ticks a tile), not the siege loop's half second
	while(1)
		sleep(1)
		for(var/mob/Monsters/RemasterSiege/Ship/S in rm_ships) if(S) S.RmShipTick()
mob/Monsters/var/tmp/mob/Monsters/RemasterSiege/Ship/rm_board       // the ship it is going to board
mob/Monsters/var/tmp/mob/Monsters/RemasterSiege/Ship/rm_aboard      // the ship it is aboard
mob/Monsters/var/tmp/rm_ship_job                                     // its job before it boarded

mob/Monsters/RemasterSiege/Ship
	name = "Ship"
	Delay = 3
	var/rm_ship_seats = 4
	var/rm_ship_pace = 3          // ticks a tile with its full rowing crew
	var/rm_ship_rowers = 2        // aboard for its full pace (1: sails, any helmsman)
	var/rm_ship_shallow = 1       // may go over shallows and fords
	var/rm_ship_ram = 0
	var/tmp/list/rm_ship_path
	var/tmp/rm_ship_next = 0
	var/tmp/turf/rm_ship_land     // the people aboard step ashore here on arriving
	var/tmp/mob/Monsters/RemasterSiege/Ship/rm_ship_foe
	New()
		..()
		rm_ships += src
		if(!rm_ship_loop)
			rm_ship_loop = 1
			spawn(1) RmShipLoop()
	Del()
		rm_ships -= src
		RmShipEmpty(1)
		..()
	Rowboat
		name = "Rowboat"
		remaster_siege_kind = "rowboat"
		HP = 300
		MAXHP = 300
	Longship
		name = "Longship"
		remaster_siege_kind = "longship"
		HP = 900
		MAXHP = 900
		rm_ship_seats = 12
		rm_ship_pace = 2
		rm_ship_rowers = 6
		rm_ship_shallow = 0
		rm_ship_ram = 1
	Cog
		name = "Cog"
		remaster_siege_kind = "cog"
		HP = 1400
		MAXHP = 1400
		rm_ship_seats = 10
		rm_ship_pace = 4
		rm_ship_rowers = 1
		rm_ship_shallow = 0

proc/RmIsShip(A)
	return istype(A, /mob/Monsters/RemasterSiege/Ship)

// Water this ship may sail onto (not up in the rock, not the Sky layer).
mob/Monsters/RemasterSiege/Ship/proc/RmShipWater(turf/T)
	if(!T || T.z != z || T.z == SKY_LAYER || !istype(T, /turf/grounds/waters) || T.remaster_waterlift) return 0
	return T.density || rm_ship_shallow

mob/Monsters/RemasterSiege/Ship/proc/RmShipAboard()
	. = list()
	for(var/mob/Monsters/M in src) if(M.HP > 0) . += M

// Ticks a tile for the crew aboard.
mob/Monsters/RemasterSiege/Ship/proc/RmShipStep(crew)
	if(rm_ship_rowers <= 1) return rm_ship_pace
	return round(rm_ship_pace * rm_ship_rowers / clamp(crew, 1, rm_ship_rowers))

// The way over water to the nearest tile of goals (turf -> 1): a list of tiles, or null.
mob/Monsters/RemasterSiege/Ship/proc/RmShipRoute(list/goals)
	var/turf/S = loc
	if(!isturf(S) || !length(goals)) return null
	if(goals[S]) return list()
	var/list/from = list()
	from[S] = S
	var/list/front = list(S)
	var/seen = 0
	while(length(front) && seen < RM_SHIP_SEARCH)
		var/list/next = list()
		for(var/turf/C in front)
			for(var/d in list(NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST))
				var/turf/N = get_step(C, d)
				if(!N || from[N] || !RmShipWater(N) || (locate(/mob/Monsters/RemasterSiege/Ship) in N)) continue   // round other ships
				from[N] = C
				seen++
				if(goals[N])
					var/list/way = list()
					for(var/turf/X = N, X != S, X = from[X]) way.Insert(1, X)
					return way
				next += N
		front = next
	return null

// Water tiles beside T a ship can lie at: turf -> 1.
mob/Monsters/RemasterSiege/Ship/proc/RmShipBeside(turf/T)
	. = list()
	if(RmShipWater(T)) .[T] = 1
	for(var/turf/N in orange(1, T)) if(RmShipWater(N)) .[N] = 1

// Water tiles near land T a ship can land from: the nearest ring (1-8 tiles out) with any: turf -> 1.
mob/Monsters/RemasterSiege/Ship/proc/RmShipNear(turf/T)
	. = list()
	for(var/r = 1, r <= 8 && !length(.), r++)
		for(var/turf/N in orange(r, T)) if(get_dist(N, T) == r && RmShipWater(N)) .[N] = 1

// --- Orders --------------------------------------------------------------------------
// Ships in the selection take an order on A (Siege.dm RemasterSiegeOrder): sail, sail and land, or ram. Returns how many.
Player/proc/RmShipOrder(atom/A, explicit = 0)
	var/turf/T = isturf(A) ? A : (A ? A.loc : null)
	if(!isturf(T)) return 0
	var/n = 0
	var/mob/Monsters/RemasterSiege/Ship/last
	for(var/mob/Monsters/RemasterSiege/Ship/S in Selected) if(S.Owner == src && S.z == T.z)
		last = S
		S.rm_ship_land = null
		S.rm_ship_foe = null
		var/list/goals
		if(RmIsShip(A) && A != S && A:Owner != src)
			if(!S.rm_ship_ram)
				RemasterNotice("[S.name]: only a longship can ram a ship.")
				continue
			if(!RmShipMayRam(src, A))
				RemasterNotice("You are at peace with that ship's realm. Declare war in the Realm tab first.")
				continue
			S.rm_ship_foe = A
			S.remaster_siege_status = "Ramming [A:name]"
			n++
			continue
		if(S.RmShipWater(T))
			goals = list()
			goals[T] = 1
		else
			goals = S.RmShipNear(T)
			if(length(goals)) S.rm_ship_land = T
		S.rm_ship_path = S.RmShipRoute(goals)
		if(isnull(S.rm_ship_path))
			S.rm_ship_land = null
			RemasterNotice("[S.name]: no way over water to there.")
			continue
		S.remaster_siege_status = S.rm_ship_land ? "Sailing to land at [T.x],[T.y]" : "Sailing"
		n++
	if(n) RemasterNotice("[n] ship[n > 1 ? "s" : ""]: [last.remaster_siege_status].")
	return n

proc/RmShipMayRam(Player/P, mob/Monsters/RemasterSiege/Ship/F)
	var/key = F.remaster_owner_key || (istype(F.Owner, /Player) ? F.Owner:key : null)
	if(!key) return 1
	if(RemasterAlliedKeys(key, P.key)) return 0
	var/turf/T = F.loc
	var/obj/RemasterBanner/B = isturf(T) ? RemasterClaimAt(T) : null
	return RemasterAtWarKeys(P.key, key) || !B

// Select people, click your ship: they go to it and board it as they reach it.
Player/proc/RmShipBoardOrder(mob/Monsters/RemasterSiege/Ship/S)
	var/list/go = list()
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && !RemasterIsSiege(M) && !M.Wagon && M.HP > 0 && isturf(M.loc)) go += M
	if(!length(go)) return 0
	var/room = S.rm_ship_seats - length(S.RmShipAboard())
	if(room <= 0)
		RemasterNotice("[S.name] is full ([S.rm_ship_seats] aboard).")
		return 1
	if(length(go) > room)
		RemasterNotice("[S.name] has room for [room] more: the first [room] go aboard.")
		go.Cut(room + 1)
	var/list/keep = Selected
	Selected = go
	RemasterOrder(S.loc, 0, "Move")   // the water's edge beside it, or swimming out to it
	Selected = keep
	for(var/mob/Monsters/M in go) M.rm_board = S
	RemasterNotice("[length(go)] going aboard the [lowertext(S.name)].")
	return 1

// --- The ship at work (Siege.dm's loop, every half second) -----------------------------
mob/Monsters/RemasterSiege/Ship/proc/RmShipTick()
	if(!isturf(loc)) return
	var/Player/P = Owner
	destination = null
	// people going aboard who have reached it (beside it, or swum out to it)
	if(istype(P) && !(world.time % 5)) for(var/mob/Monsters/M in range(2, src)) if(M.rm_board == src && M.Owner == P && M.HP > 0 && !M.GoingToDie && isturf(M.loc))
		if(length(RmShipAboard()) >= rm_ship_seats)
			M.rm_board = null
			continue
		RmShipTakeAboard(M)
	var/list/aboard = RmShipAboard()
	var/crew = length(aboard)
	RemasterSiegeDamageTick(crew)
	if(!src) return
	if(!crew)
		if(rm_ship_path || rm_ship_foe) remaster_siege_status = "Needs crew: board some of your people"
		return
	if(world.time < rm_ship_next) return
	// ramming
	if(rm_ship_foe)
		var/mob/Monsters/RemasterSiege/Ship/F = rm_ship_foe
		if(!F || !isturf(F.loc) || F.z != z)
			rm_ship_foe = null
			remaster_siege_status = "Idle"
			return
		if(get_dist(src, F) <= 1)
			dir = get_dir(src, F)
			rm_ship_next = world.time + 30
			var/dmg = 160 + 20 * min(6, crew)
			F.HP -= dmg
			RemasterSiegeEvent(F.loc, dmg, src, null, x, y, "wall")
			if(F.HP <= 0) F.RmShipSink(src)
			return
		if(!length(rm_ship_path) || get_dist(rm_ship_path[length(rm_ship_path)], F) > 1) rm_ship_path = RmShipRoute(RmShipBeside(F.loc))
		if(isnull(rm_ship_path))
			rm_ship_foe = null
			remaster_siege_status = "Can't reach it over water"
			return
	if(!length(rm_ship_path))
		if(rm_ship_path)
			rm_ship_path = null
			if(rm_ship_land) RmShipLand(rm_ship_land)
			else remaster_siege_status = "Anchored"
		return
	var/turf/N = rm_ship_path[1]
	if(length(rm_ship_path) == 1 && !rm_ship_land && (locate(/mob/Monsters/RemasterSiege/Ship) in N))   // its goal taken by another ship: it lies beside it
		rm_ship_path = list()
		return
	if(!RmShipWater(N) || (locate(/mob/Monsters/RemasterSiege/Ship) in N))   // something in the way: round it
		var/turf/G = rm_ship_path[length(rm_ship_path)]
		var/list/tg = list()
		tg[G] = 1
		rm_ship_path = RmShipRoute(rm_ship_land ? RmShipNear(rm_ship_land) : tg)
		rm_ship_next = world.time + 5
		return
	rm_ship_path.Cut(1, 2)
	usr = null                   // the ground's rule lets a step with no usr onto water (Chains/Enter.dm)
	Move(N, get_dir(src, N))
	remaster_step_gap = RmShipStep(crew)
	rm_ship_next = world.time + remaster_step_gap

// Aboard: off the job board and its care trips while at sea, its orders dropped.
mob/Monsters/RemasterSiege/Ship/proc/RmShipTakeAboard(mob/Monsters/M)
	M.rm_board = null
	M.RemasterCancelOrders()
	M.destination = null
	if(M.remaster_job != "manual")
		M.rm_ship_job = M.remaster_job
		M.RemasterAssignJob("manual")
	M.remaster_care_hold = world.time + 1000000
	M.rm_aboard = src
	M.loc = src
	if(istype(Owner, /Player)) Owner:RemasterNotice("[M.name] is aboard the [lowertext(name)] ([length(RmShipAboard())] of [rm_ship_seats]).")

// Everyone aboard steps ashore on the land beside the ship nearest T, and walks on to T when it lies further in.
mob/Monsters/RemasterSiege/Ship/proc/RmShipLand(turf/T)
	var/turf/L
	for(var/turf/N in orange(1, src)) if(!N.density && !istype(N, /turf/grounds/waters) && (!L || get_dist(N, T) < get_dist(L, T))) L = N
	var/list/landed = list()
	if(L) for(var/mob/Monsters/M in RmShipAboard())
		var/turf/D = RmShipShoreTile(L, M)
		if(!D) break
		RmShipLeave(M, D)
		landed += M
	rm_ship_land = null
	var/n = length(landed)
	remaster_siege_status = n ? "Landed [n]" : "No room ashore there"
	var/Player/P = Owner
	if(!istype(P)) return
	P.RemasterNotice("[name]: [n ? "[n] went ashore at [L.x],[L.y]" : "no shore to land on there"].")
	if(n && get_dist(L, T) > 1)   // on to where the click was
		var/list/keep = P.Selected
		P.Selected = landed
		usr = P
		P.RemasterOrder(T, 0, "Move")
		P.Selected = keep

proc/RmShipShoreTile(turf/T, mob/Monsters/M)
	for(var/r = 0, r <= 3, r++)
		for(var/turf/D in (r ? orange(r, T) : list(T)))
			if(D.density || istype(D, /turf/grounds/waters) || D.icon_state == "Sky" || D.icon_state == "Chasm") continue
			if(locate(/mob/Monsters) in D) continue
			return D
	return null

proc/RmShipLeave(mob/Monsters/M, turf/D)
	M.loc = D
	M.rm_aboard = null
	M.remaster_care_hold = 0
	if(M.rm_ship_job)
		M.RemasterAssignJob(M.rm_ship_job)
		M.rm_ship_job = null

// Everyone off it where it lies: ashore near it (sunk: swimmers into the water round it).
mob/Monsters/RemasterSiege/Ship/proc/RmShipEmpty(sinking)
	var/turf/T = isturf(loc) ? loc : null
	for(var/mob/Monsters/M in src)
		var/turf/D
		if(T && sinking && RmSwims(M))
			for(var/turf/W in orange(1, T)) if(RmSwimWater(W) && !(locate(/mob/Monsters) in W))
				D = W
				break
		if(!D && T)
			for(var/r = 1, r <= 12 && !D, r++) for(var/turf/X in orange(r, T))
				if(!X.density && !istype(X, /turf/grounds/waters) && !(locate(/mob/Monsters) in X))
					D = X
					break
		RmShipLeave(M, D || T)

mob/Monsters/RemasterSiege/Ship/proc/RmShipSink(mob/E)
	var/turf/T = loc
	if(!isturf(T)) return
	view(T) << "<b><font color=red>The [lowertext(name)] breaks apart and sinks!</font></b>"
	if(istype(Owner, /Player)) Owner:RemasterNotice("Your [lowertext(name)] at [T.x],[T.y] was sunk[E && E.Owner ? " by [E.Owner:RemasterHouse()]'s [lowertext(E.name)]" : ""]!")
	if(E && istype(E.Owner, /Player)) E.Owner:RemasterLog("Your [lowertext(E.name)] sank a [lowertext(name)] at [T.x],[T.y].", "fight", T)
	RmShipEmpty(1)
	var/turf/S = RmShipShoreTile(T, null)
	for(var/r = 1, r <= 8 && !S, r++) for(var/turf/X in orange(r, T)) if(!X.density && !istype(X, /turf/grounds/waters))
		S = X
		break
	if(S) for(var/i = 1, i <= 2, i++) new /obj/Items/woods/wood(S)
	del src

// --- Building one at the Carpentry ----------------------------------------------------
mob/Monsters/proc/RmCraftShip(mob/WorkShops/W, Player/P, kind)
	if(!(src in range(1, W)) || !RemasterManualHandoff(P)) return
	var/need = list("rowboat"=4, "longship"=12, "cog"=16)[kind]
	var/list/wood = list()
	for(var/obj/Items/woods/wood/X in src) if(X.suffix != "(Equipped)") wood += X
	var/obj/Items/iron
	for(var/obj/Items/ores/Iron/X in src) iron = X
	if(length(wood) < need || (kind == "longship" && !iron))
		P << "[src] needs [need] wood[kind == "longship" ? " and a lump of iron" : ""] to build a [kind]."
		return
	var/turf/water
	var/bd = 99
	for(var/turf/T in range(RM_SHIP_LAUNCH, W)) if(RmSwimWaterAny(T) && !(locate(/mob/Monsters/RemasterSiege/Ship) in T))
		var/d = get_dist(W, T)
		if(d < bd)
			bd = d
			water = T
	if(!water)
		P << "A ship is launched onto deep water: this carpentry has none within [RM_SHIP_LAUNCH] tiles."
		return
	for(var/i = 1, i <= need, i++)
		var/obj/Items/X = wood[i]
		weight -= X.weight
		del(X)
	if(kind == "longship")
		weight -= iron.weight
		del(iron)
	var/path = list("rowboat"=/mob/Monsters/RemasterSiege/Ship/Rowboat, "longship"=/mob/Monsters/RemasterSiege/Ship/Longship, "cog"=/mob/Monsters/RemasterSiege/Ship/Cog)[kind]
	var/mob/Monsters/RemasterSiege/Ship/E = new path(water)
	E.Owner = P
	E.remaster_owner_key = P.key
	WoodCraftingSkill += 2
	P << "[src] built a [lowertext(E.name)] and launched it at [water.x],[water.y]. Select people and click it to board; select it and click water to sail, or land to put them ashore."
	P.RemasterLog("Built a [lowertext(E.name)]", "work", water)

// Deep water anywhere a ship could lie (no rock lake, not the Sky layer), whether or not swimming is on.
proc/RmSwimWaterAny(turf/T)
	return T && T.density && T.z != SKY_LAYER && istype(T, /turf/grounds/waters) && !T.remaster_waterlift

// Saved aboard: its place is the shore beside the ship (Captives.dm Write).
proc/RmShipSaveTurf(mob/Monsters/RemasterSiege/Ship/S)
	var/turf/T = isturf(S.loc) ? S.loc : null
	if(!T) return null
	for(var/r = 1, r <= 12, r++) for(var/turf/X in orange(r, T)) if(!X.density && !istype(X, /turf/grounds/waters)) return X
	return T
