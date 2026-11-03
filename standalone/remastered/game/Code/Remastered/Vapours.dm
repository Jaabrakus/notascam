// Vapours and fire (Remastered alchemy, part 1).
// Tile gases spread the way tgstation's LINDA atmospherics does it: only tiles
// that hold gas are processed; each cycle every tile archives its contents, then
// shares with its open neighbours. The share is the archived difference times
// 1/(neighbours + 1); heat moves with the gas that moves, and conducts. Gases
// thin out (each has a decay rate). Tiles that empty and cool leave the list.
// Gases are fantasy ones: smoke, poison, sleeping mist, rot (miasma), raw mana,
// firedamp (burns), steam and healing mist. Each does something to a creature
// standing in it.
// Fire: a tile burns when it is hot enough and has fuel (firedamp, or wood on it,
// or a tree). Burning eats firedamp, makes heat and smoke, lights wood and
// creatures there with the game's own atom/Fire() (so dragons and gargoyles stay
// fireproof), and radiates heat to the tiles around it.

#define RM_AIR_TICK 10          // world ticks between cycles (1 second)
#define RM_AIR_SHARE 0.1        // half of tg's 1 / (4 neighbours + 1): clouds hang about long enough to see
#define RM_AIR_AMBIENT 20       // degrees
#define RM_AIR_MAX_TILES 4000   // safety cap on tiles holding gas
#define RM_FIRE_IGNITE 150      // a tile with fuel catches at this temperature
#define RM_FIRE_OUT 110         // and goes out below this

// id -> list(name, colour, decay per second, flammable)
var/list/rm_gases = list(
	"smoke"=list("Smoke", "#8f8f96", 0.035, 0),
	"firesmoke"=list("Smoke", "#8f8f96", 0.3, 0),   // a fire's: hangs over the burning tile only (not shared), gone soon after
	"poison"=list("Poison cloud", "#7ec850", 0.02, 0),
	"sleep"=list("Sleeping mist", "#b6a6ee", 0.025, 0),
	"miasma"=list("Rot", "#8a9a52", 0.015, 0),   // plague (Brewing.dm): a spreading cloud
	"rot"=list("Rot", "#7f8f4c", 0.03, 0),   // a body's: stays on its tile (not shared), about 2 at most
	"mana"=list("Mana vapour", "#55c0ff", 0.025, 0),
	"firedamp"=list("Firedamp", "#e0a848", 0.008, 1),
	"steam"=list("Steam", "#e6eef6", 0.06, 0),
	"heal"=list("Healing mist", "#ff9cc0", 0.03, 0))

/datum/rm_air
	var/turf/where
	var/list/gas = list()
	var/temp = RM_AIR_AMBIENT
	var/list/arch_gas
	var/arch_temp = RM_AIR_AMBIENT
	var/cycle = 0
	var/burning = 0
	var/obj/RemasterCloud/cloud
	var/obj/RemasterFlame/flame

var/list/rm_air_of = list()        // turf -> /datum/rm_air
var/list/rm_air_active = list()    // /datum/rm_air
var/rm_air_cycle = 0
var/rm_air_running = 0

proc/RemasterAir(turf/T, make = 1)
	if(!T) return null
	var/datum/rm_air/A = rm_air_of[T]
	if(A || !make) return A
	if(length(rm_air_active) >= RM_AIR_MAX_TILES) return null
	A = new
	A.where = T
	A.arch_gas = list()
	A.cycle = rm_air_cycle
	rm_air_of[T] = A
	rm_air_active += A
	if(!rm_air_running)
		rm_air_running = 1   // set before the loop starts, so only one loop ever runs
		spawn(0) RemasterAirLoop()
	return A

// Gas reaches open ground only: not rock, walls or closed doors.
proc/RemasterAirOpen(turf/T)
	if(!T || T.density) return 0
	for(var/obj/O in T) if(O.density && O.opacity) return 0
	return 1

proc/RemasterGasAdd(turf/T, id, amount, heat = null)
	if(!(id in rm_gases) || amount <= 0 || !RemasterAirOpen(T)) return 0
	var/datum/rm_air/A = RemasterAir(T)
	if(!A) return 0
	A.gas[id] = (A.gas[id] || 0) + amount
	if(!isnull(heat)) A.temp = max(A.temp, heat)
	return 1

// Heat a tile (a spark, a fire jet, dragon breath): it may catch.
proc/RemasterHeat(turf/T, heat)
	var/datum/rm_air/A = RemasterAir(T)
	if(!A) return 0
	A.temp = max(A.temp, heat)
	// a spark on fuel catches at once (before the heat can spread away)
	if(!A.burning && heat >= RM_FIRE_IGNITE && ((A.gas["firedamp"] || 0) >= 0.3 || RemasterTileFuel(T)))
		A.burning = 1
		RemasterLogFire(T)
	return 1

proc/RemasterAirTotal(datum/rm_air/A)
	. = 0
	for(var/g in A.gas) . += A.gas[g]

// Creatures carry the original's IsWood so they can catch fire, but they are not fuel: a crowd of people
// is not a woodpile (it let one dragon's breath run person to person through a whole village).
proc/RemasterTileFuel(turf/T)
	if(T.Tree || T.IsWood) return 1
	for(var/atom/movable/M in T) if(M.IsWood && !M.OnFire && !ismob(M)) return 1
	return 0

proc/RemasterAirLoop()
	rm_air_running = 1
	while(length(rm_air_active))
		sleep(RM_AIR_TICK)
		rm_air_cycle++
		var/list/run = rm_air_active.Copy()
		for(var/datum/rm_air/A in run)
			A.arch_gas = A.gas.Copy()
			A.arch_temp = A.temp
		for(var/datum/rm_air/A in run)
			if(!A.where) continue
			RemasterAirShare(A)
		for(var/datum/rm_air/A in run)
			RemasterAirReact(A)
			RemasterAirAffect(A)
			RemasterAirShow(A)
	rm_air_running = 0

// One tile's share with each open neighbour not yet handled this cycle
// (a pair shares once, from whichever side runs first).
proc/RemasterAirShare(datum/rm_air/A)
	A.cycle = rm_air_cycle
	var/turf/T = A.where
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/N = get_step(T, d)
		if(!RemasterAirOpen(N)) continue
		var/datum/rm_air/B = rm_air_of[N]
		if(B && B.cycle == rm_air_cycle) continue
		// Make the neighbour only if there is something to give it.
		if(!B)
			var/give = 0
			for(var/g in A.arch_gas) if(A.arch_gas[g] > 0.05) give = 1
			if(!give && A.arch_temp - RM_AIR_AMBIENT < 15) continue
			B = RemasterAir(N)
			if(!B) continue
			B.arch_gas = list()
			B.arch_temp = B.temp
		var/to_b = 0   // moles moving A -> B
		var/to_a = 0   // and B -> A
		for(var/g in A.arch_gas | B.arch_gas)
			if(g == "firesmoke" || g == "rot") continue
			var/delta = ((A.arch_gas[g] || 0) - (B.arch_gas[g] || 0)) * RM_AIR_SHARE
			if(!delta) continue
			A.gas[g] = max(0, (A.gas[g] || 0) - delta)
			B.gas[g] = (B.gas[g] || 0) + delta
			if(delta > 0) to_b += delta
			else to_a -= delta
		// Heat: gas arriving brings its tile's temperature (each tile counts as
		// holding one unit of plain air besides its gases), then a little conduction.
		var/hb = RemasterAirTotal(B) + 1 - to_b
		var/ha = RemasterAirTotal(A) + 1 - to_a
		if(to_b > 0) B.temp = (B.temp * hb + A.arch_temp * to_b) / (hb + to_b)
		if(to_a > 0) A.temp = (A.temp * ha + B.arch_temp * to_a) / (ha + to_a)
		var/dT = (A.arch_temp - B.arch_temp) * 0.05
		A.temp -= dT
		B.temp += dT

// Decay, burning, and dropping tiles that have nothing left.
proc/RemasterAirReact(datum/rm_air/A)
	var/turf/T = A.where
	for(var/g in A.gas.Copy())
		var/list/M = rm_gases[g]
		A.gas[g] *= (1 - M[3])
		if(A.gas[g] < 0.02) A.gas -= g
	// Fire
	var/fuel = (A.gas["firedamp"] || 0) >= 0.3 || RemasterTileFuel(T)
	if(!A.burning && fuel && A.temp >= RM_FIRE_IGNITE)
		A.burning = 1
		RemasterLogFire(T)
	if(A.burning)
		if(!fuel || A.temp < RM_FIRE_OUT)
			A.burning = 0
		else
			var/burn = min(A.gas["firedamp"] || 0, 0.4 + (A.gas["firedamp"] || 0) * 0.06)
			if(burn > 0)
				A.gas["firedamp"] -= burn
				A.temp += burn * 70
				A.gas["firesmoke"] = (A.gas["firesmoke"] || 0) + burn * 0.7
			if(RemasterTileFuel(T))
				A.temp = max(A.temp, 260)
				A.gas["firesmoke"] = (A.gas["firesmoke"] || 0) + 0.4
				if(T.Tree || T.IsWood) T.Fire()
			// catches fire once; the original Fire() burns it on from there (15 s, then death unless by water):
			// lighting it again every second burnt its limbs and blood each time, death in about 3 s
			for(var/atom/movable/M in T) if((M.IsWood || ismob(M)) && !(ismob(M) && M.OnFire)) M.Fire()
			// radiated heat lights the neighbours' fuel
			if(A.temp > 220) for(var/d in list(NORTH, SOUTH, EAST, WEST))
				var/turf/N = get_step(T, d)
				if(!N || N.density && !N.Tree) continue
				if(RemasterTileFuel(N) || rm_air_of[N]) RemasterHeat(N, A.temp * 0.6)
	// cool toward the ambient air
	A.temp += (RM_AIR_AMBIENT - A.temp) * 0.06
	if(!A.burning && !length(A.gas) && abs(A.temp - RM_AIR_AMBIENT) < 3)
		RemasterAirDrop(A)

proc/RemasterAirDrop(datum/rm_air/A)
	rm_air_active -= A
	if(A.where) rm_air_of -= A.where
	if(A.cloud) del(A.cloud)
	if(A.flame) del(A.flame)
	A.where = null

var/list/rm_fire_logged = list()   // chunk -> time, so a big fire is one log line
proc/RemasterLogFire(turf/T)
	var/k = "[round(T.x / 16)],[round(T.y / 16)],[T.z]"
	if(rm_fire_logged[k] && world.time - rm_fire_logged[k] < 600) return
	rm_fire_logged[k] = world.time
	for(var/client/C)
		var/Player/P = C.mob
		if(istype(P) && P.z == T.z && get_dist(P, T) <= 40) P.RemasterLog("Fire at [T.x], [T.y]!", "problem", T)

// What standing in each gas does. A little gas is used up by each creature.
proc/RemasterAirAffect(datum/rm_air/A)
	if(!length(A.gas)) return
	for(var/mob/Monsters/M in A.where)
		if(M.HP <= 0 || M.Wagon) continue
		var/why   // what hurt it, for its death below
		var/p = A.gas["poison"] || 0
		if(p > 0.5 && !M.Undead)
			M.HP -= min(6, p * 0.8)
			why = "a poison cloud"
			A.gas["poison"] = max(0, p - 0.15)
		var/s = A.gas["sleep"] || 0
		if(s > 2 && !M.Undead && !M.Sleeping)
			M.Sleep(60 + round(s * 20))
			A.gas["sleep"] = max(0, s - 1)
		var/m = A.gas["miasma"] || 0
		if(m > 2 && !M.Undead)
			M.HP -= min(1.5, m * 0.15)
			why = "rot"
		var/k = (A.gas["smoke"] || 0) + (A.gas["firesmoke"] || 0)
		if(k > 4 && !M.Undead)
			M.HP -= min(1, k * 0.05)
			why = "smoke"
		var/h = A.gas["heal"] || 0
		if(h > 0.3 && M.HP < M.MAXHP)
			M.HP = min(M.MAXHP, M.HP + min(8, h * 1.5))
			A.gas["heal"] = max(0, h - 0.2)
		var/n = A.gas["mana"] || 0
		if(n > 0.3 && M.MaxMana && M.Mana < M.MaxMana)
			M.Mana = min(M.MaxMana, M.Mana + n * 2)
			A.gas["mana"] = max(0, n - 0.2)
		if(A.temp > 70 && !A.burning)   // scalding steam / hot air
			M.HP -= min(4, (A.temp - 70) * 0.03)
			why = "scalding air"
		if(M.HP <= 0 && !M.GoingToDie)   // Death() does nothing unless it is going to die (Creatures/Death.dm)
			M.GoingToDie = 1
			M.Killer = why || "bad air"
			M.DeathType = M.Killer
			M.Death()

// The look: one cloud per tile, the colour of its main gas, as thick as it is;
// a flame while it burns. Both are seen on the map and in 3D.
obj/RemasterCloud
	icon = 'Cave.dmi'
	icon_state = "Smoke"
	layer = 49
	mouse_opacity = 0
	density = 0
	name = "vapour"
obj/RemasterFlame
	icon = 'Cave.dmi'
	icon_state = "Flame"
	layer = 50
	mouse_opacity = 0
	density = 0
	name = "fire"

proc/RemasterAirShow(datum/rm_air/A)
	if(!A.where) return
	var/total = RemasterAirTotal(A)
	if(total >= 0.15)
		var/main
		var/best = 0
		for(var/g in A.gas) if(A.gas[g] > best)
			best = A.gas[g]
			main = g
		if(!A.cloud) A.cloud = new(A.where)
		var/list/M = rm_gases[main]
		A.cloud.name = M[1]
		A.cloud.color = M[2]
		A.cloud.alpha = clamp(round(70 + total * 30), 70, 230)
	else if(A.cloud)
		del(A.cloud)
	if(A.burning && !A.flame) A.flame = new(A.where)
	else if(!A.burning && A.flame) del(A.flame)

// Rot: corpses give off a little rot while they lie unburied - once they have lain
// two minutes (fresh kills and fresh catches don't smell; fish keep five minutes).
mob/Body/var/tmp/remaster_rot_at = 0

proc/RemasterRotLoop()
	while(1)
		sleep(100)
		var/n = 0
		for(var/mob/Body/B in world)
			if(!isturf(B.loc)) continue
			if(!B.remaster_rot_at) B.remaster_rot_at = world.time + (B.Race == "Fish" ? 3000 : 1200)
			if(world.time < B.remaster_rot_at) continue
			RemasterGasAdd(B.loc, "rot", 0.6)   // stays on the body's tile: a smell near it, not a field of gas (user, 2026-10-23)
			if(++n >= 300) break
// world/New: this file's part is step RmChainWorldNew_Vapours in Code/Remastered/Chains/WorldNew.dm
