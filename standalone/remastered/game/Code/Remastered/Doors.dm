// Own doors open for their own villagers (the user, 2026-10-24: "My own villagers open my own unlocked doors as they
// pass and close them behind; locked doors and enemies stay blocked").
//  - A placed door (Turfs.dm Furniture/Doors: wooden, stone, metal, gold, bone; not the trapdoor) that isn't locked is
//    gone through by units its owner owns: the route search counts its tile as one to pass, never to stop on
//    (RemasterWalkable gives 2, as for a tile holding units of its side: Orders.dm, Clip.dm), and the unit opens it as
//    it steps at it (Bump). Allies, enemies and wild creatures are stopped by it as before; a locked door stops everyone.
//  - It closes by itself once nobody has stood in the doorway for a second (RmDoorLoop, every half second), so a line
//    of villagers keeps it open until the last is through, and one alone has the moment between opening it and its
//    next step. A door the player opened by double-clicking it stays open, and the player
//    still opens, closes and locks any door as before (Turfs.dm DblClick).
//  - A roped captive is its captor's realm's while bound (Captives.dm ChangeOwnership), and it only moves on the rope,
//    so a led captive goes through behind its captor; one that breaks free is its old owner's again and is stopped.
//  - Siege engines and carts don't open doors (they batter them, Siege.dm, or wait). A shut door stops every walk that
//    isn't its owner's unit's, not only a unit's own steps as the ground's rule did (turf/grounds/Enter below).
// Mirrored in the engine's route search (engine/native/RmWalk.cs) from native version 8 (Native.dm rm_native_doors).

var/list/rm_doors_auto = list()     // doors opened for a unit passing: shut again when their tile is empty
var/rm_door_loop_on = 0             // RmDoorLoop booked (a job on the unit clock, UnitClock.dm): only while one of those is open
// On only where the route search knows the rule: the DM search (RM_NATIVE_PATH=0, or the engine's shadow mode, where the
// DM search decides), or an engine that mirrors it (Native.dm rm_native_doors, native version 8). With an older engine
// its search would plan past own doors as before while this said otherwise, so it waits for the engine.
var/rm_own_doors = 0
#define RM_DOOR_SHUT_AFTER 10           // the doorway empty this long (1 s) since it opened or someone stood in it
obj/Items/Furniture/Doors/var/tmp/rm_door_seen = 0

// A door its owner's unit walks through (open or shut), or 0.
proc/RmOwnDoor(atom/movable/A, mob/M)
	if(!istype(A, /obj/Items/Furniture/Doors) || istype(A, /obj/Items/Furniture/Doors/TrapDoor)) return 0
	var/obj/Items/Furniture/Doors/D = A
	if(!D.Placed || D.Locked || !D.Owner || !istype(M, /mob/Monsters)) return 0
	var/mob/Monsters/U = M
	if(D.Owner != U.Owner || istype(U, /mob/Monsters/RemasterSiege) || U.Wagon) return 0
	return 1

// The placed door that bumping A meets (the door, or one on the tile bumped).
proc/RmDoorAt(atom/A)
	if(istype(A, /obj/Items/Furniture/Doors)) return A
	if(isturf(A)) for(var/obj/Items/Furniture/Doors/D in A) if(D.Placed) return D
	return null

proc/RmDoorOpen(obj/Items/Furniture/Doors/D)
	D.density = 0
	D.opacity = 0
	D.icon_state = istype(D, /obj/Items/Furniture/Doors/StoneDoor) ? "StoneOpen" : "Open"   // as its double-click opens it
	D.rm_door_seen = world.time      // the opener's next step comes a moment after the bump that opened it
	if(!(D in rm_doors_auto)) rm_doors_auto += D
	if(!rm_door_loop_on)
		rm_door_loop_on = 1
		RmClockWorldBook("Doors", 5)

proc/RmDoorShut(obj/Items/Furniture/Doors/D)
	D.density = 1
	D.opacity = 1
	D.icon_state = initial(D.icon_state)

// turf/grounds/Enter: this file's part is step RmChainEnter_Doors in Code/Remastered/Chains/Enter.dm

// mob/Monsters/Bump: this file's part is step RmChainBump_Doors in Code/Remastered/Chains/Bump.dm

proc/RmDoorLoop()   // every 5 ticks on the unit clock while one is open: it ends on the run that shuts the last, as its loop did
	for(var/obj/Items/Furniture/Doors/D in rm_doors_auto.Copy())
		if(!D || !isturf(D.loc) || !D.Placed || D.density)   // gone, picked up, or shut by the player
			rm_doors_auto -= D
			continue
		if(locate(/mob/Monsters) in D.loc)
			D.rm_door_seen = world.time
			continue
		if(world.time - D.rm_door_seen < RM_DOOR_SHUT_AFTER) continue
		RmDoorShut(D)
		rm_doors_auto -= D
	if(length(rm_doors_auto)) RmClockWorldBook("Doors", 5)
	else rm_door_loop_on = 0

// world/New: this file's part is step RmChainWorldNew_Doors in Code/Remastered/Chains/WorldNew.dm

// --- Which tiles hold a placed door (step-cost, 10-27; the owner: "Skip the tile scans where there's no door or beast
// nearby") -----------------------------------------------------------------------------------------------------------
// Every unit's step into a tile looked for a door on it (turf/grounds/Enter, Chains/Enter.dm, step Doors). Now each tile
// counts the placed doors on it (rm_door_n) and the step looks only where there is one. A door's count is set where it
// is when it is made (New, once the proc that made it is done: the map, the world's load and tests set Placed after
// new()), when it is placed (Click.dm "Place" and Construction.dm RemasterBuildGate end with its Death(), below), when
// it goes (Del), and every second for any door moved or placed some other way (RmDoorCountLoop, the "DoorCount" job on
// the unit clock). A new way of placing a door: call RmDoorCount(D) after setting Placed. rm_step_scan_check = 1 also
// looks on every tile that counts none, and logs any placed door it finds there (STEPSCAN| lines, RmStepScanDoor).
turf/var/tmp/rm_door_n = 0                         // placed doors counted on this tile
obj/Items/Furniture/Doors/var/tmp/turf/rm_door_on   // the tile this door is counted on
var/list/rm_door_all = list()                      // every door there is (New, Del)
var/rm_door_count_on = 0                           // the "DoorCount" job is booked
var/rm_step_scan_check = 0                         // 1: the steps also scan the tiles the counts skip (doors, beast feet: Beasts.dm)
var/rm_scan_door_skips = 0                         // with rm_step_scan_check: steps that skipped the look, checked...
var/rm_scan_door_bad = 0                           // ...and those that found a placed door after all (each logged)

obj/Items/Furniture/Doors/New()
	. = ..()
	rm_door_all += src
	spawn(0) if(istype(src, /obj/Items/Furniture/Doors)) RmDoorCount(src)   // (deleted by then: istype is 0)
	if(!rm_door_count_on)
		rm_door_count_on = 1
		RmClockWorldBook("DoorCount", 10)

obj/Items/Furniture/Doors/Del()
	rm_door_all -= src
	var/turf/T = rm_door_on
	rm_door_on = null
	if(T) RmDoorRecount(T, src)
	return ..()

obj/Items/Furniture/Doors/Death()   // its placing ends with it (Click.dm "Place", Construction.dm), as does a blow to it
	RmDoorCount(src)
	return ..()

// The door counted where it is now: on its tile while it is placed there.
proc/RmDoorCount(obj/Items/Furniture/Doors/D)
	var/turf/T = (D.Placed && isturf(D.loc)) ? D.loc : null
	var/turf/O = D.rm_door_on
	if(T == O && (!T || T.rm_door_n > 0)) return
	D.rm_door_on = T
	if(T) RmDoorRecount(T)
	if(O && O != T)
		try
			RmDoorRecount(O)
		catch
			return

proc/RmDoorRecount(turf/T, obj/gone)
	var/n = 0
	for(var/obj/Items/Furniture/Doors/X in T) if(X != gone && X.Placed) n++
	T.rm_door_n = n

proc/RmDoorCountLoop()   // the "DoorCount" job: every 10 ticks while there are doors
	for(var/obj/Items/Furniture/Doors/D in rm_door_all) RmDoorCount(D)   // (a deleted one is skipped)
	if(length(rm_door_all)) RmClockWorldBook("DoorCount", 10)
	else rm_door_count_on = 0

// rm_step_scan_check: a step that skipped the look on T (no door counted there) looks after all.
proc/RmStepScanDoor(turf/T, atom/movable/m)
	rm_scan_door_skips++
	var/n = 0
	for(var/obj/Items/Furniture/Doors/X in T) if(X.Placed) n++
	if(!n) return
	rm_scan_door_bad++
	var/obj/Items/Furniture/Doors/D = locate() in T
	world.log << "STEPSCAN|door|[T.x],[T.y],[T.z]|[n] placed, none counted|the look would act: [(D && D.Placed && D.density && !istype(D, /obj/Items/Furniture/Doors/TrapDoor)) ? 1 : 0]|[m]"
