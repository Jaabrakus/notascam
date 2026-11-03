// Rune circuits (Remastered alchemy, part 4): tgstation's power and wiring, as
// magic. Rune pieces sit one per tile. Pieces touching side by side form one
// circuit (like tg's powernets: connected cables, rebuilt when one is added or
// cut). A circuit's mana is held in its Mana crystals; every device that acts
// pays from it, so a circuit with no mana does nothing. Pressure plates and
// levers send a signal down their circuit and every device on it acts: doors
// open or close, fire jets burst, spikes stab, bells ring. Lamps glow while the
// circuit has mana. Scratching a rune out cuts the circuit.
// Pieces are built like workshops (Blueprints.dm: "Workshop:<id>").

#define RM_RUNE_TICK 10
#define RM_CRYSTAL_MAX 100
#define RM_CRYSTAL_RECHARGE 0.15   // mana per second per crystal, on its own
#define RM_PLATE_COOLDOWN 30

// id -> list(label, type, cost to act)
var/list/rm_rune_defs = list(
	"rune"=list("Rune line", /obj/RemasterRune/Line, 0),
	"crystal"=list("Mana crystal", /obj/RemasterRune/Crystal, 0),
	"runedoor"=list("Rune door", /obj/RemasterRune/Door, 2),
	"firejet"=list("Fire jet", /obj/RemasterRune/Jet, 6),
	"spikes"=list("Spike trap", /obj/RemasterRune/Spikes, 3),
	"plate"=list("Pressure plate", /obj/RemasterRune/Plate, 0),
	"lever"=list("Lever", /obj/RemasterRune/Lever, 0),
	"lamp"=list("Rune lamp", /obj/RemasterRune/Lamp, 0),
	"bell"=list("Alarm bell", /obj/RemasterRune/Bell, 1))

var/list/rm_runes = list()        // every rune piece
var/rm_runes_dirty = 1            // circuits need rebuilding
var/list/rm_rune_nets = list()    // /datum/rm_runenet
var/rm_rune_running = 0

/datum/rm_runenet
	var/list/members = list()
	var/list/crystals = list()

proc/RemasterRuneNetMana(datum/rm_runenet/N)
	. = 0
	for(var/obj/RemasterRune/Crystal/C in N.crystals) . += C.charge

proc/RemasterRuneNetMax(datum/rm_runenet/N)
	return length(N.crystals) * RM_CRYSTAL_MAX

// Pay from the circuit's crystals, fullest first. 0 if there isn't enough.
proc/RemasterRuneSpend(datum/rm_runenet/N, cost)
	if(cost <= 0) return 1
	if(!N || RemasterRuneNetMana(N) < cost) return 0
	var/left = cost
	while(left > 0.001)
		var/obj/RemasterRune/Crystal/best
		for(var/obj/RemasterRune/Crystal/C in N.crystals) if(!best || C.charge > best.charge) best = C
		if(!best || best.charge <= 0) break
		var/take = min(best.charge, left)
		best.charge -= take
		left -= take
	return 1

obj/RemasterRune
	name = "rune"
	icon = 'Icons/Remastered/Runes.dmi'
	density = 0
	layer = 3
	var/rune_id = "rune"
	var/owner_key          // the player who built it (plates ignore their units)
	var/datum/rm_runenet/net
	var/link = 0           // which neighbours it joins (N 1, S 2, E 4, W 8), for drawing
	New()
		..()
		rm_runes += src
		rm_runes_dirty = 1
		if(!rm_rune_running)
			rm_rune_running = 1
			spawn(0) RemasterRuneLoop()
	Del()
		rm_runes -= src
		rm_runes_dirty = 1
		..()

obj/RemasterRune/proc/RuneAct(obj/RemasterRune/source)
	return

obj/RemasterRune/Line
	name = "rune line"
	icon_state = "line"
	rune_id = "rune"

obj/RemasterRune/Crystal
	name = "mana crystal"
	icon_state = "crystal"
	rune_id = "crystal"
	var/charge = 20

obj/RemasterRune/Door
	name = "rune door"
	icon_state = "door_shut"
	rune_id = "runedoor"
	density = 1
	opacity = 1
	var/open = 0
	RuneAct()
		if(!open)
			Open()
			return
		if(RmRuneDoorHeld(src)) return    // never closes on someone
		Shut()
	proc/Open()
		open = 1
		density = 0
		opacity = 0
		icon_state = "door_open"
	proc/Shut()
		open = 0
		density = 1
		opacity = 1
		icon_state = "door_shut"

obj/RemasterRune/Jet
	name = "fire jet"
	icon_state = "jet"
	rune_id = "firejet"
	RuneAct()
		RemasterGasAdd(loc, "firedamp", 10)
		RemasterHeat(loc, 260)

// An open rune door with a creature in the way: it won't close on them (and closing it costs nothing then).
proc/RmRuneDoorHeld(obj/RemasterRune/Door/D)
	if(!istype(D) || !D.open) return 0
	for(var/mob/Monsters/M in D.loc) return 1
	return 0

obj/RemasterRune/Spikes
	name = "spike trap"
	icon_state = "spikes_down"
	rune_id = "spikes"
	var/raised_until = 0
	RuneAct()
		raised_until = world.time + 20
		icon_state = "spikes_up"
		for(var/mob/Monsters/M in loc)
			if(M.HP <= 0) continue
			M.HP -= 25
			M.BloodContent -= 20
			if(ismob(M.Owner)) M.Owner << "[M.name] is stabbed by a spike trap!"
			if(M.HP <= 0 && !M.GoingToDie)   // Death() does nothing unless it is going to die (Creatures/Death.dm)
				M.GoingToDie = 1
				M.Killer = "a spike trap"
				M.DeathType = "a spike trap"
				M.Death()
		spawn(20) if(src && world.time >= raised_until) icon_state = "spikes_down"

obj/RemasterRune/Plate
	name = "pressure plate"
	icon_state = "plate"
	rune_id = "plate"
	var/last = -1000
	var/anyone = 0     // 1: the owner's units set it off too

obj/RemasterRune/Lever
	name = "lever"
	icon_state = "lever_l"
	rune_id = "lever"
	var/pulled = 0

obj/RemasterRune/Lamp
	name = "rune lamp"
	icon_state = "lamp_off"
	rune_id = "lamp"

obj/RemasterRune/Bell
	name = "alarm bell"
	icon_state = "bell"
	rune_id = "bell"
	RuneAct(obj/RemasterRune/source)
		for(var/client/C)
			var/Player/P = C.mob
			if(istype(P) && P.key == owner_key)
				var/turf/T = source ? source.loc : loc
				P.RemasterNotice("Alarm! Something set off a trap at [T.x], [T.y].")
				P.RemasterLog("Alarm at [T.x], [T.y]!", "fight", T)

proc/RemasterRuneAt(turf/T)
	if(!T) return null
	return locate(/obj/RemasterRune) in T

// Circuits: flood fill over pieces touching side by side.
proc/RemasterRuneRebuild()
	rm_runes_dirty = 0
	rm_rune_nets = list()
	for(var/obj/RemasterRune/R in rm_runes) R.net = null
	for(var/obj/RemasterRune/R in rm_runes)
		if(R.net || !isturf(R.loc)) continue
		var/datum/rm_runenet/N = new
		rm_rune_nets += N
		var/list/todo = list(R)
		R.net = N
		while(length(todo))
			var/obj/RemasterRune/X = todo[length(todo)]
			todo.len--
			N.members += X
			if(istype(X, /obj/RemasterRune/Crystal)) N.crystals += X
			X.link = 0
			var/bit = 1
			for(var/d in list(NORTH, SOUTH, EAST, WEST))
				var/obj/RemasterRune/Y = RemasterRuneAt(get_step(X, d))
				if(Y)
					X.link |= bit
					if(!Y.net)
						Y.net = N
						todo += Y
				bit *= 2

// A signal from a plate or lever: every device on its circuit acts, if the
// circuit can pay for it.
proc/RemasterRunePulse(obj/RemasterRune/source)
	if(rm_runes_dirty) RemasterRuneRebuild()
	var/datum/rm_runenet/N = source.net
	if(!N) return 0
	var/acted = 0
	for(var/obj/RemasterRune/R in N.members)
		var/list/D = rm_rune_defs[R.rune_id]
		if(R == source || istype(R, /obj/RemasterRune/Line) || istype(R, /obj/RemasterRune/Crystal) || istype(R, /obj/RemasterRune/Lamp)) continue
		if(istype(R, /obj/RemasterRune/Plate) || istype(R, /obj/RemasterRune/Lever)) continue
		if(RmRuneDoorHeld(R)) continue   // someone in the doorway: it stays open, and its mana isn't spent
		if(!RemasterRuneSpend(N, D[3])) continue
		R.RuneAct(source)
		acted++
	acted += RmStoneDoorsPulse(N)   // the stone doors touching the circuit (StoneDoors.dm)
	return acted

proc/RemasterRuneLoop()
	rm_rune_running = 1
	while(length(rm_runes))
		sleep(RM_RUNE_TICK)
		if(rm_runes_dirty) RemasterRuneRebuild()
		for(var/datum/rm_runenet/N in rm_rune_nets)
			// crystals recharge; mana vapour on a crystal's tile soaks in fast
			for(var/obj/RemasterRune/Crystal/C in N.crystals)
				var/gain = RM_CRYSTAL_RECHARGE
				var/datum/rm_air/A = rm_air_of[C.loc]
				if(A && (A.gas["mana"] || 0) > 0)
					var/soak = min(A.gas["mana"], 3)
					A.gas["mana"] -= soak
					gain += soak * 2
				C.charge = min(RM_CRYSTAL_MAX, C.charge + gain)
			// lamps glow while the circuit has mana (and sip a little)
			var/powered = RemasterRuneNetMana(N) > 0.5
			for(var/obj/RemasterRune/Lamp/L in N.members)
				var/on = powered && RemasterRuneSpend(N, 0.02)
				L.icon_state = on ? "lamp_on" : "lamp_off"
				L.luminosity = on ? 4 : 0
			// plates: a creature on one (not the owner's, unless set to anyone) sets it off
			for(var/obj/RemasterRune/Plate/P in N.members)
				if(world.time - P.last < RM_PLATE_COOLDOWN) continue
				for(var/mob/Monsters/M in P.loc)
					if(M.HP <= 0) continue
					var/mine = ismob(M.Owner) && M.Owner:key == P.owner_key
					if(mine && !P.anyone) continue
					P.last = world.time
					RemasterRunePulse(P)
					break
	rm_rune_running = 0

// --- Building (from Blueprints.dm) -------------------------------------------
proc/RemasterIsRune(id)
	return id in rm_rune_defs

Player/proc/RemasterBuildRune(mob/Monsters/M, turf/T, id)
	var/list/D = rm_rune_defs[id]
	if(!D || M.loc != T || RemasterRuneAt(T)) return 0
	var/list/W = RemasterWorkshopDefs()[id]
	var/material = W ? W[3] : null
	var/obj/Items/used
	if(material)
		for(var/obj/Items/I in M) if(istype(I, material) && I.suffix != "(Equipped)")
			used = I
			break
		if(!used) return 0
	if(!M.RemasterManualHandoff(src)) return 0
	var/path = D[2]
	var/obj/RemasterRune/R = new path(T)
	R.owner_key = key
	R.dir = M.dir
	if(used)
		M.weight -= used.weight
		del(used)
	// step off a door just built so it can close
	if(istype(R, /obj/RemasterRune/Door))
		R:Open()
	return 1

// --- The HUD's Runes box: pieces beside the unit, and their circuit ----------
// value: "unitref|action|piece ref"
Player/proc/RemasterRuneCommand(value)
	var/list/p = splittext("[value]", "|")
	if(p.len < 3) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return 0
	var/obj/RemasterRune/R
	for(var/obj/RemasterRune/X in range(1, M)) if(RemasterUIRef(X) == p[3]) R = X
	if(!R)
		RemasterNotice("[M.name] must stand beside it.")
		return 0
	if(rm_runes_dirty) RemasterRuneRebuild()
	switch(p[2])
		if("pull")
			if(!istype(R, /obj/RemasterRune/Lever)) return 0
			var/obj/RemasterRune/Lever/L = R
			L.pulled = !L.pulled
			L.icon_state = L.pulled ? "lever_r" : "lever_l"
			var/n = RemasterRunePulse(L)
			RemasterNotice(n ? "[M.name] pulls the lever: [n] device[n == 1 ? " answers" : "s answer"]." : "[M.name] pulls the lever. Nothing happens: is the circuit connected, with mana in its crystals?")
			return 1
		if("door")
			if(!istype(R, /obj/RemasterRune/Door)) return 0
			if(RmRuneDoorHeld(R))
				RemasterNotice("Someone stands in the doorway: the rune door won't close on them.")
				return 0
			if(!RemasterRuneSpend(R.net, 2))
				RemasterNotice("The rune door needs mana: connect it to a charged crystal.")
				return 0
			R.RuneAct()
			return 1
		if("test")
			var/n = RemasterRunePulse(R)
			RemasterNotice("Signal sent: [n] device[n == 1 ? "" : "s"] answered.")
			return 1
		if("anyone")
			if(!istype(R, /obj/RemasterRune/Plate)) return 0
			R:anyone = !R:anyone
			RemasterNotice(R:anyone ? "The plate now goes off for anyone, your units too." : "The plate now ignores your units.")
			return 1
		if("scratch")
			RemasterNotice("[M.name] scratches out the [R.name].")
			del(R)
			return 1
	return 0

Player/proc/RemasterRuneData(mob/Monsters/M)
	var/list/pieces = list()
	for(var/obj/RemasterRune/R in range(1, M))
		if(length(pieces) >= 8) break
		var/list/D = rm_rune_defs[R.rune_id]
		var/list/E = list("ref"=RemasterUIRef(R), "id"=R.rune_id, "name"=D[1])
		if(istype(R, /obj/RemasterRune/Door)) E["open"] = R:open
		if(istype(R, /obj/RemasterRune/Plate)) E["anyone"] = R:anyone
		pieces += list(E)
	if(!length(pieces)) return null
	if(rm_runes_dirty) RemasterRuneRebuild()
	var/obj/RemasterRune/first = locate(/obj/RemasterRune) in range(1, M)
	var/datum/rm_runenet/N = first ? first.net : null
	return list("pieces"=pieces, "mana"=(N ? round(RemasterRuneNetMana(N)) : 0), "max"=(N ? RemasterRuneNetMax(N) : 0),
		"crystals"=(N ? length(N.crystals) : 0), "size"=(N ? length(N.members) : 0))

// What the 3D view needs about a piece.
proc/Remaster3DRune(obj/RemasterRune/R)
	var/list/D = list("id"=R.rune_id, "link"=R.link, "pow"=(R.net && RemasterRuneNetMana(R.net) > 0.5) ? 1 : 0)
	if(istype(R, /obj/RemasterRune/Door)) D["open"] = R:open
	if(istype(R, /obj/RemasterRune/Spikes)) D["up"] = world.time < R:raised_until
	if(istype(R, /obj/RemasterRune/Lever)) D["on"] = R:pulled
	if(istype(R, /obj/RemasterRune/Crystal)) D["charge"] = round(R:charge)
	return D

// --- Saving (WorldSave.dm) -------------------------------------------------------
// Pieces are saved as records: type, place, builder, facing and their own settings
// (charge, door open, lever pulled, plate trigger). Circuits are rebuilt from the
// pieces; timers (raised spikes, plate cooldown) start fresh.
var/list/rm_rune_unsaved = list("net", "link", "raised_until", "last")

proc/RemasterRuneRecords()
	. = list()
	for(var/obj/RemasterRune/R in rm_runes) if(isturf(R.loc))
		var/list/V = RemasterSimpleVars(R)
		for(var/v in rm_rune_unsaved) V -= v
		. += list(list("[R.type]", R.x, R.y, R.z, R.owner_key, R.dir, V))

proc/RemasterRuneRestore(list/L)
	. = 0
	for(var/list/E in L)
		if(length(E) < 7) continue
		var/path = text2path(E[1])
		var/turf/T = locate(E[2], E[3], E[4])
		if(!path || !T || !ispath(path, /obj/RemasterRune) || RemasterRuneAt(T)) continue
		var/obj/RemasterRune/R = new path(T)
		R.owner_key = E[5]
		if(isnum(E[6])) R.dir = E[6]
		if(islist(E[7])) RemasterApplyVars(R, E[7])
		.++
