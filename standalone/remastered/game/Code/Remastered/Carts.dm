// Mine carts (Build tab, "Rails"). Rail track is laid like a road (turf/remaster_road =
// "rail", Roads.dm: kept in saves, sent to the 3D view, a little faster to walk on), a
// wood a tile. Cart stops stand on the rails: one beside a stockpile is where carts
// unload; any other is a loading stop, where miners and haulers drop what they carry
// when it is nearer than the stockpile (their delivery goes there instead). A mine cart
// on the rails runs by itself: it waits at a loading stop until it is full (or half a
// minute has passed with something in it), rolls along the track to the unloading stop,
// tips its load onto the stockpile and goes back to the stop with the most waiting.
// Up and down: a running lift (Lifts.dm) is part of the track. A cart that rolls onto one rides it to the
// other level and carries on along the rails there, so a line can run from a mine in the tunnels up the
// shaft to the stockpile on the surface; miners below drop their loads at the loading stops there.
// Later the same stops and carts can serve a rail line to another town (trade).

#define RM_CART_LOAD 20           // pieces a cart takes
#define RM_CART_WAIT 300          // ticks it waits at a stop with a part load
#define RM_CART_STEP 3            // ticks a tile
#define RM_CART_RIDE 30           // ticks a ride up or down a lift takes

var/list/rm_cart_stops = list()

obj/Items/Furniture/RemasterCartStop
	// its values: art/items/catalogue.json row furniture.remastercartstop (export_items.py writes ItemData.dm)
	New()
		..()
		rm_cart_stops += src
	Del()
		rm_cart_stops -= src
		return ..()

obj/Items/Furniture/RemasterCart
	// its values: art/items/catalogue.json row furniture.remastercart (export_items.py writes ItemData.dm)
	var/tmp/list/remaster_cart_path
	var/tmp/remaster_cart_goal       // the stop it is heading for
	var/tmp/remaster_cart_since = 0  // when it began waiting with a part load
	var/tmp/remaster_cart_note
	New()
		..()
		spawn(10) RemasterCartRun()

// The player who owns a cart or stop (its Owner, or whoever has its key when back).
proc/RemasterCartOwner(obj/O)
	if(istype(O.Owner, /Player)) return O.Owner
	if(O:remaster_owner_key) return RemasterPlayerByKey(O:remaster_owner_key)
	return null

proc/RemasterIsRail(turf/T)
	return T && !T.density && T.remaster_road == "rail"

// Track a cart may be on: rails, or a running lift (it rides it to the other end).
proc/RemasterCartWay(turf/T)
	return RemasterIsRail(T) || RemasterLiftOn(T)

// Unloading stop: a store (the stockpile or a zone) within two tiles of it.
Player/proc/RemasterCartUnloadAt(obj/Items/Furniture/RemasterCartStop/S)
	for(var/turf/T in RemasterBaseStores()) if(T.z == S.z && get_dist(T, S) <= 2) return T
	return null

// The stockpile and zones (Zones.dm RemasterStores), without the loading stops.
Player/proc/RemasterBaseStores()
	. = list()
	var/turf/S = RemasterStockpile()
	if(S) . += S
	if(remaster_zones) for(var/list/Z in remaster_zones)
		for(var/turf/T in RemasterZoneCells(Z)) if(!(T in .)) . += T   // a painted stockpile's every cell (Zones.dm)

Player/proc/RemasterCartStops(load_only)
	. = list()
	for(var/obj/Items/Furniture/RemasterCartStop/S in rm_cart_stops)
		if(!isturf(S.loc) || RemasterCartOwner(S) != src) continue
		if(load_only && RemasterCartUnloadAt(S)) continue
		. += S

// Loading stops count as stores: goods left there don't rot, and builders may fetch from them.
Player/RemasterStores()
	. = ..()
	for(var/obj/Items/Furniture/RemasterCartStop/S in RemasterCartStops(1)) if(!(S.loc in .)) . += S.loc

Player/proc/RemasterIsLoadStop(turf/T)
	for(var/obj/Items/Furniture/RemasterCartStop/S in T) if(RemasterCartOwner(S) == src && !RemasterCartUnloadAt(S)) return S
	return null

// The way along the rails from A to B (both on track): a list of turfs after A, or null. A running
// lift joins the rails beside it on both levels: the path goes up or down it.
proc/RemasterRailPath(turf/A, turf/B)
	if(!A || !B) return null
	if(A == B) return list()
	var/list/prev = list()
	prev[A] = A
	var/list/q = list(A)
	var/n = 0
	while(length(q) && n < 2000)
		var/turf/T = q[1]
		q.Cut(1, 2)
		n++
		var/list/next = list()
		for(var/d in list(NORTH, SOUTH, EAST, WEST)) next += get_step(T, d)
		if(RemasterLiftOn(T))
			var/turf/O = RemasterLiftOther(T)
			if(RemasterLiftOn(O)) next += O
		for(var/turf/N in next)
			if(!RemasterCartWay(N) || prev[N]) continue
			prev[N] = T
			if(N == B)
				var/list/path = list()
				for(var/turf/X = B, X != A, X = prev[X]) path.Insert(1, X)
				return path
			q += N
	return null

// What a cart carries: resources the stockpile takes (stone, ore, wood...), nothing placed.
proc/RemasterCartCargo(Player/P, obj/Items/I)
	return I && !I.remaster_placed && !istype(I, /obj/Items/Furniture/RemasterCart) && I.suffix != "(Equipped)" && P.RemasterStockAccepts(I)

// What rides in a cart is in the stores' keeping. A thing off a store is cleared away after three minutes on the ground
// (Items/Item Procs.dm DeleteItem, FoodRoles.dm RemasterOnStockpile) and that clock ran on in the cart, so a piece that
// had lain at the loading stop a while vanished on the way (polish 10-26: a full cart brought 10 of its 20).
obj/Items/RemasterOnStockpile()
	if(istype(loc, /obj/Items/Furniture/RemasterCart)) return 1
	return ..()

obj/Items/Furniture/RemasterCart/proc/RemasterCartRun()
	while(src)
		sleep(RM_CART_STEP)
		if(!isturf(loc)) continue
		var/Player/P = RemasterCartOwner(src)
		if(!P || !RemasterCartWay(loc))
			remaster_cart_note = "Off the rails"
			sleep(20)
			continue
		// rolling along to a stop
		if(length(remaster_cart_path))
			var/turf/N = remaster_cart_path[1]
			if(!RemasterCartWay(N))
				remaster_cart_path = null    // the track was taken up, or the lift stopped: think again
				continue
			remaster_cart_path.Cut(1, 2)
			if(N.z != z)
				// up or down the lift's shaft
				remaster_cart_note = N.z == RemasterLiftLevel(z, 1) ? "Riding the lift up" : "Riding the lift down"
				sleep(RM_CART_RIDE)
				if(!src || !RemasterLiftOn(loc) || !RemasterLiftOn(N)) continue
				loc = N
				continue
			dir = get_dir(loc, N)
			loc = N
			continue
		var/obj/Items/Furniture/RemasterCartStop/here = locate() in loc
		var/turf/unload = here ? P.RemasterCartUnloadAt(here) : null
		var/load = 0
		for(var/obj/Items/X in src) load++
		if(here && unload && load)
			// tip the load out onto the stockpile
			for(var/obj/Items/X in src)
				X.loc = unload
				X.Owner = P
			P.RemasterLog("A mine cart brought [load] load[load == 1 ? "" : "s"] to the stockpile", "work", unload)
			remaster_cart_note = "Unloaded [load]"
			load = 0
		if(here && !unload)
			// take on what is waiting at this stop
			for(var/obj/Items/X in loc)
				if(load >= RM_CART_LOAD) break
				if(!RemasterCartCargo(P, X)) continue
				X.loc = src
				load++
			if(load && !remaster_cart_since) remaster_cart_since = world.time
			var/full = load >= RM_CART_LOAD || (load && world.time - remaster_cart_since >= RM_CART_WAIT)
			if(!full)
				// nothing here: is more waiting at another stop?
				if(!load)
					var/obj/Items/Furniture/RemasterCartStop/best = RemasterCartBusiest(P, here)
					if(best) RemasterCartGo(best)
				remaster_cart_note = load ? "Loading ([load]/[RM_CART_LOAD])" : "Waiting for loads"
				continue
		// full, or not at a loading stop: off to unload (or to the busiest loading stop)
		var/obj/Items/Furniture/RemasterCartStop/dest
		if(load)
			// the unloading stop nearest along the track, on this level or up or down a lift
			var/best_n = 1#INF
			for(var/obj/Items/Furniture/RemasterCartStop/S in P.RemasterCartStops()) if(P.RemasterCartUnloadAt(S))
				var/list/way = S.loc == loc ? list() : RemasterRailPath(loc, S.loc)
				if(way && length(way) < best_n)
					dest = S
					best_n = length(way)
			if(!dest)
				remaster_cart_note = "No stop beside a stockpile on this track"
				sleep(20)
				continue
		else
			dest = RemasterCartBusiest(P, null) || RemasterCartNearestLoad(P)   // empty: back to wait at a loading stop
			if(!dest)
				remaster_cart_note = "No loading stop on this track"
				sleep(20)
				continue
		if(!RemasterCartGo(dest))
			remaster_cart_note = "No track to [dest.name]"
			sleep(20)

obj/Items/Furniture/RemasterCart/proc/RemasterCartGo(obj/Items/Furniture/RemasterCartStop/S)
	if(!S || S.loc == loc) return 0
	var/list/path = RemasterRailPath(loc, S.loc)
	if(!path) return 0
	remaster_cart_path = path
	remaster_cart_goal = S
	remaster_cart_since = 0
	return 1

// The loading stop on this track with the most waiting (other than "not"), or null.
obj/Items/Furniture/RemasterCart/proc/RemasterCartBusiest(Player/P, not)
	var/obj/Items/Furniture/RemasterCartStop/best
	var/most = 0
	for(var/obj/Items/Furniture/RemasterCartStop/S in P.RemasterCartStops(1))
		if(S == not) continue
		var/n = 0
		for(var/obj/Items/X in S.loc) if(RemasterCartCargo(P, X)) n++
		if(n > most && RemasterRailPath(loc, S.loc))
			most = n
			best = S
	return best

// The loading stop nearest along the track (null: none it can reach).
obj/Items/Furniture/RemasterCart/proc/RemasterCartNearestLoad(Player/P)
	var/obj/Items/Furniture/RemasterCartStop/best
	var/best_n = 1#INF
	for(var/obj/Items/Furniture/RemasterCartStop/S in P.RemasterCartStops(1))
		var/list/path = RemasterRailPath(loc, S.loc)
		if(path && length(path) < best_n)
			best = S
			best_n = length(path)
	return best

// The loading stop nearest M on its level, or null.
Player/proc/RemasterLoadStopOn(mob/M)
	var/turf/best
	for(var/obj/Items/Furniture/RemasterCartStop/X in RemasterCartStops(1)) if(X.z == M.z)
		if(!best || get_dist(M, X) < get_dist(M, best)) best = X.loc
	return best

// --- Deliveries go to the nearer loading stop ----------------------------------------------
// A miner or hauler taking what it carries to the stockpile goes to a loading stop instead
// when one is nearer (by more than a few tiles); the cart brings it the rest of the way.
mob/Monsters/RemasterBeginDelivery(obj/Items/needed)
	// down a mine with the stockpile up on the surface: the loading stop on this level takes the load
	var/Player/Q = Owner
	var/turf/home = istype(Q) ? Q.RemasterStockpile() : null
	if(istype(Q) && (!home || home.density || home.z != z))
		var/turf/stop = Q.RemasterLoadStopOn(src)
		if(stop)
			var/released = RemasterDeliveryWeight(Q)
			if(released <= 0 || (needed && weight + needed.weight - released > weightmax))
				RemasterBlock("Unloading what the stockpile takes wouldn't free enough room")
				return 0
			if(!remaster_delivery) remaster_delivery = new
			remaster_delivery.issuer = Q
			remaster_delivery.kind = "Drop off"
			remaster_delivery.target = stop
			RemasterStartOrder(remaster_delivery)
			RemasterSuspendControllers()
			remaster_blocked = null
			remaster_order_status = "Taking resources to the cart stop, then back to the task"
			return 1
	. = ..()
	if(!. || !remaster_delivery) return
	var/Player/P = Owner
	var/turf/S = remaster_delivery.target
	var/turf/best
	for(var/obj/Items/Furniture/RemasterCartStop/X in P.RemasterCartStops(1)) if(X.z == z)
		if(!best || get_dist(src, X) < get_dist(src, best)) best = X.loc
	if(best && (!S || get_dist(src, best) + 3 < get_dist(src, S)))
		remaster_delivery.target = best
		remaster_order_status = "Taking resources to the cart stop, then back to the task"

mob/Monsters/RemasterDepositTick(datum/remaster_order/O, Player/P)
	var/turf/S = O ? O.target : null
	if(!istype(S) || !P.RemasterIsLoadStop(S)) return ..()
	if(!RemasterLandForWork()) return 0
	if(get_dist(src, S) > 1)
		RemasterApproach(O, S, 1)
		return 0
	destination = null
	var/amount = 0
	for(var/obj/Items/I in contents.Copy())
		if(I.suffix != "(Carrying)" || I.EquipmentType() || !P.RemasterStockAccepts(I)) continue
		if(DropItem(I) && I)
			I.loc = S
			I.Owner = P
			amount++
	remaster_blocked = null
	remaster_wait_for_resume = 0
	if(O == remaster_active) RemasterFinishOrder("Left [amount] resource item[amount == 1 ? "" : "s"] at the cart stop")
	return 1
