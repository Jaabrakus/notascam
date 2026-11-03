// What a selected unit can do to another of your units, or to a body (the 3D right-click card's first
// buttons, and dropping a bag item on a unit, remastered.html):
//  - Carry them / Put them down: someone who is down (unconscious, knocked out, can't walk, near death)
//    is carried along behind, as the Doctor carries patients (Surgery.dm, rm_carried_by).
//  - Treat / Feed / Give to drink: a remedy, food or potion the unit carries is taken over and used on
//    them on arrival (Bag.dm's give).
//  - Carry the body: a body lying near is picked up, as the gravedigger does (Graves.dm). With rm_body_drag
//    (BodyDrag.dm) it is dragged along the ground instead: "Drag body" / "Let go".

proc/RemasterItemUseKind(obj/Items/I)
	if(!I) return null
	if(istype(I, /obj/Items/RemasterRemedy)) return "remedy"
	if(istype(I, /obj/Items/Potions/RemasterBrew)) return length(I:brew) ? "potion" : null
	if(I.IsPotion == 1 && !I.IsEmpty) return "potion"
	if(istype(I, /obj/Items/Food)) return "food"
	return null

// list(list(label, command, value, tip)) for M acting on T.
Player/proc/RemasterUsesOn(mob/Monsters/M, mob/Monsters/T)
	. = list()
	if(!M || !T || M == T || T.Owner != src || T.HP <= 0 || T.GoingToDie || T.Wagon) return
	var/pair = "[RemasterUIRef(M)]|[RemasterUIRef(T)]"
	if(T.rm_carried_by == M) . += list(list("Put them down", "carryunit", "[pair]|0", "Lay them down beside you."))
	else if(T.RemasterIsDown() && !T.rm_carried_by) . += list(list("Carry them", "carryunit", "[pair]|1", "Walk over, pick them up and carry them along; put them down from here again."))
	var/list/seen = list()
	for(var/obj/Items/I in M)
		if(I.suffix != "(Carrying)") continue
		var/k = RemasterItemUseKind(I)
		if(!k || seen["[I.name]"]) continue
		seen["[I.name]"] = 1
		if(k == "remedy") . += list(list("Treat: [I.name]", "giveitem", "[RemasterUIRef(I)]|[RemasterUIRef(T)]|1", "Walk over and treat them with it."))
		else if(k == "food") . += list(list("Feed: [I.name]", "giveitem", "[RemasterUIRef(I)]|[RemasterUIRef(T)]|1", "Walk over and feed it to them."))
		else . += list(list("Give to drink: [I.name]", "giveitem", "[RemasterUIRef(I)]|[RemasterUIRef(T)]|1", "Walk over and give it to them to drink."))
		if(length(.) >= 8) break

// What a unit of yours can do itself, on its own right-click card when it is the one selected (the owner, 10-28: a menu
// on your own unit, "its bag, eat, drink, sleep, equip"): each carried food, drink and remedy used at once and carried
// gear put on (Bag.dm RemasterUseFor, the bag's Use), and Sleep (RmSelfSleep). The page adds Open its bag.
Player/proc/RemasterSelfUses(mob/Monsters/M)
	. = list()
	if(!M || M.Owner != src || M.HP <= 0 || M.GoingToDie || M.Wagon) return
	. += list(list(M.rm_fav ? "Unfavourite" : "Favourite", "favunit", RemasterUIRef(M), M.rm_fav ? "Its fights go to the background log in a big battle, as everyone else's." : "Its fights, limbs and death always show in the corner, starred, even in a big battle."))
	var/list/seen = list()
	for(var/obj/Items/I in M)
		if(I.suffix != "(Carrying)" || seen["[I.name]"]) continue
		var/k = RemasterItemUseKind(I)
		var/label
		if(k == "remedy") label = "Treat itself: [I.name]"
		else if(k == "food") label = "Eat: [I.name]"
		else if(k == "potion") label = "Drink: [I.name]"
		else if(M.UsesEquipment && istype(I, /obj/Items/Equipment) && I.EquipmentType()) label = "Put on: [I.name]"
		if(!label) continue
		seen["[I.name]"] = 1
		. += list(list(label, "useitem", RemasterUIRef(I), "[M.RemasterBareName()] uses it now, from its bag."))
		if(length(.) >= 8) break
	if(M.RemasterNeedsSleep() && !M.Sleeping && !M.Flying && !M.IsMist)
		. += list(list("Sleep", "selfsleep", RemasterUIRef(M), M.RemasterCarriedBed() ? "Lies down in its sleeping bag where it is." : "Goes to its bed or the nearest free one, or sleeps rough where it is."))

// A favourite (the owner, 10-28: "keep big battles in the backgound logs and only highlight favorited units"): in a big
// battle near the camera the corner shows only lines naming a favourite, starred; the rest go to Village > Log (the page,
// remasterChat). Kept with the unit.
mob/Monsters/var/rm_fav = 0

Player/proc/RmFavToggle(value)
	var/mob/Monsters/M = RemasterUIUnit("[value]")
	if(!istype(M) || M.Owner != src) return 0
	M.rm_fav = !M.rm_fav
	RemasterNotice(M.rm_fav ? "[M.RemasterBareName()] is a favourite: its fights always show in the corner." : "[M.RemasterBareName()] is no longer a favourite.")
	return 1

// "unitref": Sleep on a unit's own card. In its sleeping bag where it stands; else to its bed or the nearest free one,
// or rough where it is, as when it is tired (Care.dm RemasterCareSleep); never with enemies near.
Player/proc/RmSelfSleep(value)
	var/mob/Monsters/M = RemasterUIUnit("[value]")
	if(!istype(M) || M.Owner != src || M.HP <= 0 || M.Sleeping || !M.RemasterNeedsSleep()) return 0
	M.RemasterCancelOrders()
	M.remaster_patrol = null
	var/obj/Items/Furniture/Beds/S = M.RemasterCarriedBed()
	if(S)
		if(M.Target || M.RemasterEnemyNear())
			RemasterNotice("[M.RemasterBareName()] won't sleep with enemies near.")
			return 0
		M.destination = null
		M.Sleep(max(40, 300 - S.CR))
		RemasterNotice("[M.RemasterBareName()] lies down in the [lowertext(S.name)].")
		return 1
	M.RemasterCareSleep(src, list())
	if(M.Sleeping) RemasterNotice("[M.RemasterBareName()] lies down to sleep.")
	else if(M.remaster_care == "sleep") RemasterNotice("[M.RemasterBareName()] goes to bed.")
	else RemasterNotice("[M.RemasterBareName()] can't sleep now[M.remaster_care_note ? ": [lowertext(M.remaster_care_note)]" : ""].")
	return 1

// "carrier|carried|1" picks them up (walking over first), "...|0" puts them down.
Player/proc/RemasterCarryUnit(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 3) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	var/mob/Monsters/T = RemasterUIUnit(p[2])
	if(!istype(M) || !istype(T) || M.Owner != src || T.Owner != src || M == T) return 0
	if(p[3] == "0")
		if(T.rm_carried_by != M) return 0
		T.rm_carried_by = null
		var/turf/D = RemasterTileNear(M, T)
		if(D) T.loc = D
		M.remaster_order_status = "Idle"   // the card said "Carrying" after they were put down
		RemasterNotice("[M.RemasterBareName()] puts [T.RemasterBareName()] down.")
		return 1
	if(!T.RemasterIsDown() || T.rm_carried_by) return 0
	M.RemasterCancelOrders()
	M.remaster_patrol = null   // a direct order ends a patrol, or the patrol tick sends it back out on its route (Patrol.dm)
	M.destination = T
	M.remaster_order_status = "Going to carry [T.RemasterBareName()]"
	spawn(0)
		for(var/t = 0, t < 120 && M && T, t++)
			if(get_dist(M, T) <= 1 && M.z == T.z)
				if(T.rm_carried_by || !T.RemasterIsDown()) return
				T.rm_carried_by = M
				rm_carry_list |= T
				T.destination = null
				M.destination = null
				M.remaster_order_status = "Carrying [T.RemasterBareName()]"
				RemasterNotice("[M.RemasterBareName()] picks up [T.RemasterBareName()].")
				return
			if(M.destination != T) return       // given another order on the way
			sleep(5)
	return 1

// "carrier|body ref": walk over and take the body up.
Player/proc/RemasterCarryBody(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	var/mob/Body/B = locate(p[2])
	if(!istype(M) || M.Owner != src || !istype(B) || !isturf(B.loc) || B.suffix) return 0
	M.RemasterCancelOrders()
	M.remaster_patrol = null   // a direct order ends a patrol (Patrol.dm)
	M.destination = B
	M.remaster_order_status = "Going to take up [RemasterDeadName(B)]"
	spawn(0)
		for(var/t = 0, t < 120 && M && B, t++)
			if(get_dist(M, B) <= 1 && M.z == B.z && isturf(B.loc))
				M.destination = null
				if(!M.PickUpItem(B)) M.ForcePickUpItem(B)
				M.remaster_order_status = "Carrying [RemasterDeadName(B)]"
				return
			if(M.destination != B || !isturf(B.loc)) return
			sleep(5)
	return 1

// Each track (QoL.dm): people carried by your units (not the Doctor, who carries its own) go along
// behind; when they are no longer down, or the carrier is, they are put down.
// Only units being carried can be moved by it: rm_carry_list holds those (added where rm_carried_by is set),
// and one no longer carried drops out (server cost, 2026-10-24: every unit was looked at every track run).
var/list/rm_carry_list = list()
Player/proc/RemasterCarryTick()
	var/list/keep = list()
	for(var/mob/Monsters/T in rm_carry_list) if(T.rm_carried_by) keep += T
	rm_carry_list = keep
	for(var/mob/Monsters/T in keep) if(T.Owner == src && (T in UnitList))
		var/mob/Monsters/C = T.rm_carried_by
		if(!C || C.remaster_job == "doctor") continue
		if(C.HP <= 0 || C.GoingToDie || C.z != T.z || !T.RemasterIsDown() || T.HP <= 0)
			T.rm_carried_by = null
			continue
		var/turf/behind = get_step(C, turn(C.dir, 180))
		var/turf/spot = (behind && !behind.density) ? behind : C.loc
		if(T.loc != spot) T.loc = spot
