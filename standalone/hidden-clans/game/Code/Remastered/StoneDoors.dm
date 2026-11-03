// Heavy stone doors (the user, 2026-10-25: "it takes high magic or strength to open or the runic stones or power
// source"). A stone door is a slab of rock (the 3D view draws the climbing stone, Interface/gear3d.js): it stays shut
// until something strong enough opens it, then everyone goes through until it is shut again.
//  - A strong or magical unit beside it opens or shuts it (the door's double-click, with that unit selected): Strength
//    RM_STONE_DOOR_STRENGTH or more, or Magic RM_STONE_DOOR_MAGIC or more. A weaker one is told it is too heavy.
//  - A lever or pressure plate on a rune circuit touching it opens or shuts it, for 2 of the circuit's mana, as a rune
//    door (Runes.dm RemasterRunePulse).
//  - A turning power train touching it (an axle, a wheel... beside the door) drives it: an ordinary own door then, opened
//    for its owner's units as they come and shut behind them (Doors.dm).
// Shut and not driven, it is Locked to every walk, so the route searches (the engine's too: RmWalk.cs reads Locked) go
// round it; its Locked flag is the heavy door's, and the player's own lock on a stone door is its seal (rm_sealed): a
// sealed door opens for nothing until its owner unseals it. Open, anyone goes through, as through any open door.
#define RM_STONE_DOOR_STRENGTH 40
#define RM_STONE_DOOR_MAGIC 20
#define RM_STONE_DOOR_MANA 2
var/rm_heavy_doors = 1          // 0: stone doors as the original's
var/list/rm_stone_doors = list()
var/rm_stone_door_loop = 0
obj/Items/Furniture/Doors/StoneDoor/var/rm_sealed = 0     // the owner's lock (saved)
obj/Items/Furniture/Doors/StoneDoor/var/rm_heavy_seen = 0 // its Locked flag has been the heavy door's since (saved)
obj/Items/Furniture/Doors/StoneDoor/var/tmp/rm_driven = 0

obj/Items/Furniture/Doors/StoneDoor/New()
	..()
	rm_stone_doors += src
	if(!rm_heavy_doors && rm_heavy_seen)   // the rule switched off: the door is locked only if its owner sealed it
		Locked = rm_sealed
		rm_heavy_seen = 0
	if(rm_heavy_doors && !rm_stone_door_loop)
		rm_stone_door_loop = 1
		spawn(10) RmStoneDoorLoop()

obj/Items/Furniture/Doors/StoneDoor/Del()
	rm_stone_doors -= src
	..()

proc/RmStoneDoorLoop()
	while(rm_heavy_doors && length(rm_stone_doors))
		for(var/obj/Items/Furniture/Doors/StoneDoor/D in rm_stone_doors) RmStoneDoorSet(D)
		sleep(10)
	rm_stone_door_loop = 0

// A turning power train touching it.
proc/RmStoneDoorPowered(obj/Items/Furniture/Doors/StoneDoor/D)
	if(rm_power_dirty) RemasterPowerRebuild()
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/obj/Items/Furniture/RemasterPower/X = RemasterPowerAt(get_step(D, d))
		if(X && X.pnet)
			RemasterPowerCount(X.pnet)
			if(X.pnet.on) return 1
	return 0

// Its Locked flag as the rule says: shut, it opens for its people only when driven and not sealed; open, it is open.
proc/RmStoneDoorSet(obj/Items/Furniture/Doors/StoneDoor/D)
	if(!D.Placed || !isturf(D.loc)) return
	if(!D.rm_heavy_seen)   // a door from before the rule: one its owner had locked stays sealed
		D.rm_heavy_seen = 1
		if(D.Locked) D.rm_sealed = 1
	D.rm_driven = RmStoneDoorPowered(D)
	D.Locked = D.density ? ((D.rm_sealed || !D.rm_driven) ? 1 : 0) : 0

proc/RmStoneDoorStrong(mob/Monsters/M)
	return M && (M.RmStr() >= RM_STONE_DOOR_STRENGTH || RemasterSkillLevel(M.MagicSkill) >= RM_STONE_DOOR_MAGIC)

proc/RmStoneDoorToggle(obj/Items/Furniture/Doors/StoneDoor/D)
	if(D.density)
		D.density = 0
		D.opacity = 0
		D.icon_state = "StoneOpen"
	else
		D.density = 1
		D.opacity = 1
		D.icon_state = "StoneDoor"
	RmStoneDoorSet(D)

// A lever's or plate's signal on circuit N: the stone doors touching it open or shut (Runes.dm RemasterRunePulse).
proc/RmStoneDoorsPulse(datum/rm_runenet/N)
	. = 0
	if(!rm_heavy_doors || !N) return
	for(var/obj/Items/Furniture/Doors/StoneDoor/D in rm_stone_doors) if(D.Placed && isturf(D.loc) && !D.rm_sealed)
		var/on = 0
		for(var/d in list(NORTH, SOUTH, EAST, WEST))
			var/obj/RemasterRune/R = RemasterRuneAt(get_step(D, d))
			if(R && R.net == N) on = 1
		if(on && RemasterRuneSpend(N, RM_STONE_DOOR_MANA))
			RmStoneDoorToggle(D)
			.++

// Double-clicked with a unit beside it: a strong or magical one opens or shuts it; its owner's can seal or unseal it.
// With no unit of the player's beside it, the original's double-click (walking over, picking it up...).
obj/Items/Furniture/Doors/StoneDoor/DblClick()
	if(!rm_heavy_doors || !Placed || !isturf(loc) || !istype(usr, /Player)) return ..()
	var/Player/P = usr
	var/mob/Monsters/M
	for(var/mob/Monsters/X in P.Selected) if(X.Owner == P && X.HP > 0 && get_dist(X, src) <= 1)
		M = X
		break
	if(!M) return ..()
	M.destination = null
	if(rm_sealed)
		if(Owner != P)
			P << "The [name] is sealed."
			return
		var/U = RemasterChoose(P, "The [name] is sealed. Unseal it?", "Stone door", list("Unseal", "Cancel"), "Cancel")   // the HUD's ask card, as every door's menu (AskCard.dm; it was the native window)
		if(U == "Unseal")
			rm_sealed = 0
			RmStoneDoorSet(src)
			P << "[M] unseals the [name]."
		return
	if(!RmStoneDoorStrong(M))
		P << "The [name] is too heavy for [M]: it takes Strength [RM_STONE_DOOR_STRENGTH] or Magic [RM_STONE_DOOR_MAGIC], a lever on a rune circuit touching it, or a turning power train beside it."
		return
	RmStoneDoorToggle(src)
	P << (density ? "[M] heaves the [name] shut." : "[M] heaves the [name] open.")
	if(Owner == P && density)
		var/Result = RemasterChoose(P, "What Action Will You Choose?", "Choose", list("Seal", "Destroy", "Cancel"), "Cancel")
		if(Result == "Seal")
			rm_sealed = 1
			RmStoneDoorSet(src)
			P << "[src] sealed."
		else if(Result == "Destroy")
			del(src)
