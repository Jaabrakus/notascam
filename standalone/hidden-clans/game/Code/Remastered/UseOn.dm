// "Use on" (Remastered): an item held, then clicked onto what it is for. One mode for every item that
// works on something else. Click such an item in the unit's bag and it is held: the banner says what to
// click; what it can be used on is ringed in 3D, with what will happen when hovered; click one and the
// unit walks over and does it. Right-click or Esc lets it go. Some go on: a soul stone takes a soul,
// then the banner says to click a gargoyle to wake it. (Right-click on the item in the bag still opens
// its original choices, and a double-click still uses it at once.)
//
//   held item                   click on                               does
//   soul stone, empty           the body of a person                   takes the soul (SoulStone.dm)
//   soul stone, with a soul     a gargoyle of yours with no soul yet   wakes the soul in it
//   remedy                      a villager of yours                    treats them (Bag.dm, give)
//   potion or brew              a villager of yours                    gives it them to drink
//   food                        a villager of yours                    feeds them
//   food                        your food pot or stall                 puts it in (FoodSupply.dm)
//   poison                      a food pot or stall of a realm at war  slips it in
//   wine brew                   your tavern                            pours it in (Tavern.dm)
//   herb or remedy              your Doctor's stall                    puts it in (Doctor.dm)
//   severed or false limb       a villager missing that limb           hands it over; they go to the
//                                                                      Operating table (Surgery.dm)
//   weapon or armour            a villager of yours                    hands it over; they put it on

#define RM_USEON_REACH 15

Player/var/tmp/list/remaster_useon   // list(unit, item) while an item is held

// The id the page knows a thing by: a unit of yours its UI ref, anything else its \ref.
Player/proc/RemasterUseOnId(atom/A)
	if(istype(A, /mob/Monsters) && A:Owner == src) return RemasterUIRef(A)
	return "\ref[A]"

Player/proc/RemasterUseOnPoint(atom/A, label)
	return list("id"=RemasterUseOnId(A), "x"=A.x, "y"=A.y, "label"=label)

// What M can do with I, and to what: list("hint"=banner text, "targets"=list(list(id, x, y, label))),
// or null when the item works on nothing else.
Player/proc/RemasterUseOnTargets(mob/Monsters/M, obj/Items/I)
	if(!istype(M) || !I || I.loc != M || I.suffix == "(Equipped)") return null
	var/list/T = list()
	var/list/hints = list()
	var/kind = RemasterItemUseKind(I)   // remedy, potion, food (TargetActions.dm)
	if(istype(I, /obj/Items/RemasterSoulStone))
		var/obj/Items/RemasterSoulStone/S = I
		if(!S.soul)
			hints += "click the body of the dead to take their soul"
			for(var/mob/Body/B in range(RM_USEON_REACH, M)) if(isturf(B.loc) && B.rm_soul && !B.Critter && !B.suffix)
				T += list(RemasterUseOnPoint(B, "Take the soul of [RemasterDeadName(B)]"))
		else
			hints += "[S.soul["name"]]'s soul is in it: click a gargoyle of yours to wake it"
			for(var/mob/Monsters/G in range(RM_USEON_REACH, M)) if(G.Race == "Gargoyle" && G.Owner == src && !G.rm_soul && G.HP > 0)
				T += list(RemasterUseOnPoint(G, "Wake [S.soul["name"]]'s soul in it"))
		return list("hint"="[I.name]: [hints[1]]", "targets"=T)
	if(kind)
		var/verb = kind == "remedy" ? "Treat" : kind == "food" ? "Feed" : "Give to drink:"
		hints += kind == "remedy" ? "click a villager, this one too, to treat them" : kind == "food" ? "click a villager, this one too, to feed them" : "click a villager, this one too, to give it them to drink"
		// the one holding it as well (the owner, 10-28: "interact with the base unit as well or not just other things")
		T += list(RemasterUseOnPoint(M, kind == "remedy" ? "Treat [M.RemasterBareName()] itself" : kind == "food" ? "[M.RemasterBareName()] eats it" : "[M.RemasterBareName()] drinks it"))
		for(var/mob/Monsters/V in range(RM_USEON_REACH, M)) if(V != M && V.Owner == src && V.HP > 0 && !V.GoingToDie && !V.Wagon && !V.Critter)
			T += list(RemasterUseOnPoint(V, "[verb] [V.RemasterBareName()]"))
	if(istype(I, /obj/Items/Food))
		hints += "or your food pot or stall to put it in"
		for(var/mob/WorkShops/RemasterFood/C in range(RM_USEON_REACH, M)) if(C.Owner == src && C.Takes(I) && length(C.Items()) < C.Capacity())
			T += list(RemasterUseOnPoint(C, "Put it in the [lowertext(C.name)]"))
	if(RemasterPoisonDose(I))
		hints += "click a food pot or stall of a realm you are at war with to slip it in"
		for(var/mob/WorkShops/RemasterFood/C in range(RM_USEON_REACH, M)) if(C.Owner != src && RemasterMayPoison(src, C))
			T += list(RemasterUseOnPoint(C, "Slip it into [C.Owner ? "[C.Owner]'s " : "the "][lowertext(C.name)]"))
	if(istype(I, /obj/Items/Potions/RemasterBrew) && (I:brew["wine"] || 0) >= 3)
		hints += "or your tavern to pour it in"
		for(var/mob/WorkShops/RemasterTavern/V in range(RM_USEON_REACH, M)) if(V.Owner == src && V.drink < RM_TAVERN_MAX)
			T += list(RemasterUseOnPoint(V, "Pour it into the tavern"))
	if(istype(I, /obj/Items/RemasterHerb) || istype(I, /obj/Items/RemasterRemedy))
		hints += istype(I, /obj/Items/RemasterHerb) ? "click your Doctor's stall to put it in" : "or your Doctor's stall to put it in"
		for(var/mob/WorkShops/RemasterClinic/K in range(RM_USEON_REACH, M)) if(K.Owner == src && K.Total() < RM_CLINIC_MAX)
			T += list(RemasterUseOnPoint(K, "Put it in the Doctor's stall"))
	var/part = RemasterLimbPart(I)
	if(part)
		hints += "click a villager missing [part == "leg" ? "a leg" : "an arm"]: the Doctor fits it at the Operating table"
		for(var/mob/Monsters/V in range(RM_USEON_REACH, M)) if(V != M && V.Owner == src && V.HP > 0)
			for(var/s in V.RemasterMissingSlots()) if(findtext(s, part == "leg" ? "Leg" : "Arm"))
				T += list(RemasterUseOnPoint(V, "Bring it to [V.RemasterBareName()] for the Doctor"))
				break
	if(istype(I, /obj/Items/Equipment) && I.EquipmentType())
		hints += M.UsesEquipment ? "click a villager to give it them to wear, or this one to put it on" : "click a villager to give it them to wear"
		if(M.UsesEquipment) T += list(RemasterUseOnPoint(M, "[M.RemasterBareName()] puts it on"))
		for(var/mob/Monsters/V in range(RM_USEON_REACH, M)) if(V != M && V.Owner == src && V.HP > 0 && !V.Wagon && !V.Critter)
			T += list(RemasterUseOnPoint(V, "Give it to [V.RemasterBareName()] to wear"))
	if(!length(hints)) return null
	return list("hint"="[I.name]: [jointext(hints, ", ")]", "targets"=T)

// Whether an item is one that is used on something (the bag: a click holds it), cheaply, without
// looking round for what.
proc/RemasterUseOnAble(obj/Items/I)
	if(!I) return 0
	if(length(RmItemCats(I) & RmCombineCats())) return 1   // it combines with something: a click holds it (below)
	if(I.suffix == "(Equipped)") return 0
	if(istype(I, /obj/Items/RemasterSoulStone) || RemasterItemUseKind(I) || istype(I, /obj/Items/Food)) return 1
	if(istype(I, /obj/Items/RemasterHerb) || istype(I, /obj/Items/RemasterRemedy) || RemasterLimbPart(I)) return 1
	if(RemasterPoisonDose(I)) return 1
	return istype(I, /obj/Items/Equipment) && I.EquipmentType() ? 1 : 0

// For the HUD: what the held item can be used on.
Player/proc/RemasterUseOnData()
	if(!remaster_useon) return null
	var/mob/Monsters/M = remaster_useon[1]
	var/obj/Items/I = remaster_useon[2]
	var/list/U = RemasterUseOnTargets(M, I)
	var/list/C = RmCombineList(M, I)   // the bag's things it combines with (below)
	if((!U && !length(C)) || !(M in Selected))
		remaster_useon = null
		return null
	return list("item"="[I.name]", "ref"=RemasterUIRef(I), "unit"=RemasterUIRef(M), "hint"=U ? (length(C) ? "[U["hint"]] - or click an outlined thing in the bag to combine them" : U["hint"]) : "Click one of the outlined things in the bag to combine them", "targets"=U ? U["targets"] : list(), "combine"=C)

// The page: an item clicked in the bag ("item ref"), one of the ringed things clicked ("id"), let go.
Player/proc/RemasterUseOnCommand(action, value)
	switch(action)
		if("useonpick")
			var/obj/Items/I = RemasterUIItem("[value]")
			if(!I || !istype(I.loc, /mob/Monsters) || I.loc:Owner != src) return 0
			if(!RemasterUseOnTargets(I.loc, I) && !length(RmCombineList(I.loc, I)))
				RemasterNotice("The [I.name] isn't used on anything: right-click it for its choices.")
				return 0
			remaster_useon = list(I.loc, I)
			return 1
		if("useoncancel")
			remaster_useon = null
			return 1
		if("combine")   // "held ref|other ref": the held thing combined with one of the bag's (below)
			var/list/p = splittext("[value]", "|")
			if(length(p) != 2) return 0
			var/obj/Items/A = RemasterUIItem(p[1])
			var/obj/Items/B = RemasterUIItem(p[2])
			if(!A || !B || A == B || A.loc != B.loc || !istype(A.loc, /mob/Monsters)) return 0
			var/mob/Monsters/M = A.loc
			if(!RemasterInventoryActor(M, A)) return 0
			var/id
			for(var/list/X in RmCombineList(M, A)) if(X["ref"] == p[2]) id = X["id"]
			if(!id)
				RemasterNotice("The [A.name] and the [B.name] don't combine.")
				return 0
			remaster_useon = null
			return RmCombineDo(id, M, A, B, src)
		if("useonat")
			if(!remaster_useon) return 0
			var/mob/Monsters/M = remaster_useon[1]
			var/obj/Items/I = remaster_useon[2]
			var/list/U = RemasterUseOnTargets(M, I)
			var/list/hit
			if(U) for(var/list/X in U["targets"]) if(X["id"] == "[value]") hit = X
			if(!hit)
				RemasterNotice("The [I ? I.name : "item"] can't be used on that: click one of the ringed ones, or right-click to let it go.")
				return 0
			var/atom/A = RemasterUIUnit(hit["id"]) || locate(hit["id"])
			if(!A) return 0
			remaster_useon = null
			spawn(0) M.RemasterUseOnGo(I, A, hit["label"])
			return 1
	return 0

// A free tile right beside A (a unit, a stall) to stand on, the nearest to M; else one near it.
proc/RemasterUseOnSpot(atom/A, mob/M)
	var/turf/best
	var/best_d = 1#INF
	for(var/turf/T in orange(1, A))
		if(T.density) continue
		var/blocked = 0
		for(var/atom/movable/O in T) if(O.density && O != M)
			blocked = 1
			break
		if(blocked) continue
		var/d = get_dist(T, M)
		if(d < best_d)
			best = T
			best_d = d
	return best || RemasterTileNear(A, M)

// Walk over and do it; a soul stone that has just taken a soul is held again for its next step.
mob/Monsters/proc/RemasterUseOnGo(obj/Items/I, atom/A, label)
	var/Player/P = Owner
	if(!istype(P)) return
	RemasterCancelOrders()
	remaster_order_status = "[label]"
	var/turf/goal                    // where it walks to: beside the target, chosen again only if the target moves
	var/turf/at
	for(var/t = 0, t < 240 && I && A && I.loc == src && HP > 0, t++)
		if(z == A.z && get_dist(src, A) <= 1)
			destination = null
			var/done = RemasterUseOnDo(I, A)
			if(!done) P.RemasterNotice("[RemasterBareName()] couldn't: [lowertext(label)].")
			else if(I && I.loc == src && !P.remaster_useon && P.RemasterUseOnTargets(src, I) && istype(I, /obj/Items/RemasterSoulStone))
				P.remaster_useon = list(src, I)    // the next step of the chain: the banner says what
			return
		if(!goal || (!isturf(A) && A.loc != at))
			at = isturf(A) ? A : A.loc
			goal = isturf(A) ? A : (A.density ? RemasterUseOnSpot(A, src) : A.loc)
			destination = goal
		else if(destination && destination != goal) return   // another order on the way
		else if(!destination && get_dist(src, goal) > 0) destination = goal
		sleep(5)

mob/Monsters/proc/RemasterUseOnDo(obj/Items/I, atom/A)
	var/Player/P = Owner
	if(istype(I, /obj/Items/RemasterSoulStone))
		if(istype(A, /mob/Body)) return RemasterSoulTake(I, A)
		return RemasterSoulGive(I, A)
	if(istype(A, /mob/WorkShops/RemasterFood))
		if(A:Owner == P && istype(I, /obj/Items/Food)) return A:Put(I)
		return P.RemasterFoodPoison(src, A, I)
	if(istype(A, /mob/WorkShops/RemasterTavern)) return A:PourIn(I) > 0
	if(istype(A, /mob/WorkShops/RemasterClinic)) return A:PutIn(I)
	var/mob/Monsters/V = A
	if(!istype(V)) return 0
	if(V == src) return P.RemasterUseFor(src, I)   // on itself: eaten, drunk, applied or put on, as its bag's Use (Bag.dm)
	if(RemasterLimbPart(I))
		if(!RemasterHandOver(I, src, V)) return 0
		var/mob/WorkShops/RemasterSurgery/S = P.RemasterNearestTable(V)
		var/turf/G = S ? RemasterTileNear(S, V) : null
		if(G) V.destination = G
		P.RemasterNotice("[V.RemasterBareName()] has the [I.name][S ? " and goes to the Operating table for the Doctor" : ": build an Operating table near the Doctor's stall"].")
		return 1
	if(istype(I, /obj/Items/Equipment) && I.EquipmentType())
		if(!RemasterHandOver(I, src, V)) return 0
		V.ToggleEquipItem(ITEM=I, MANUAL=1)
		return 1
	// handed over and used at once, as a give from the bag (Bag.dm RemasterGiveTick)
	remaster_give_item = I
	remaster_give_extra = list()
	remaster_give_to = V
	remaster_give_use = 1
	remaster_give_since = world.time
	RemasterGiveTick()
	return 1

// --- Combine (the owner, 10-28: "build it it in a way where we can combine anything via catergories", "so this should
// allow us to build new items faster") -------------------------------------------------------------------------------
// Every kind of carried thing says what it is in its own definition: rm_cats, its categories as words ("poison",
// "weapon blade"...). A rule joins two categories (rm_combine_rules) and works on any thing of them, from what the
// category gives (a poison's dose, a weapon's damage): hold one (a click in the bag) and the bag's things it combines
// with are outlined; click one and the unit does it (HUD "combine"). A new kind joins every rule its categories are in
// with no code; a new combination is a row and its case in RmCombineDo. Plan: planning/COMBINE_PLAN_2026-10-28.md.
obj/Items/var/rm_cats = ""                       // its categories, as words: set in each kind's own definition
var/list/rm_cats_cache = list()                 // type -> its categories as a list (read once a kind)

// The original's kinds (their definitions are the 2006 files): the same as a new kind's own rm_cats line.
obj/Items/Poisons/rm_cats = "poison"
obj/Items/Equipment/Weapon/rm_cats = "weapon"
obj/Items/Equipment/Armour/Quiver/LeatherQuiver/rm_cats = "quiver"
obj/Items/Arrows/rm_cats = "arrows"
obj/Items/woods/rm_cats = "wood"
obj/Items/ores/rm_cats = "ore"
obj/Items/ores/stone/rm_cats = "stone"
obj/Items/Ingots/rm_cats = "ingot"
obj/Items/gems/rm_cats = "gem"
obj/Items/Bones/rm_cats = "bone"
obj/Items/Skin/rm_cats = "skin"
obj/Items/Seeds/rm_cats = "seed"
obj/Items/Food/rm_cats = "food"
obj/Items/RemasterHerb/rm_cats = "herb"
obj/Items/RmBeastEgg/rm_cats = "egg"

// id, category, category, what it is called, what it does. The first rows are the original's own (Click.dm: a toxic
// vial's "Arrows" and "Weapon"), for every poison (their descriptions: "can be used to add poison to weapons").
var/list/rm_combine_rules = list(
	list("tiparrows", "poison", "quiver", "Tip the arrows", "The poison on the quiver's arrows: ten arrows a vial."),
	list("coatweapon", "poison", "weapon", "Coat the weapon", "The poison on the weapon: 2 to 4 more damage; the vial is used up."))
var/list/rm_combine_cats   // every category a rule uses (RmCombineCats)

proc/RmCombineCats()
	if(!rm_combine_cats)
		rm_combine_cats = list()
		for(var/list/R in rm_combine_rules) rm_combine_cats |= list(R[2], R[3])
	return rm_combine_cats

// What a thing is, for combining: its kind's rm_cats (a resource sack is a quiver that holds no arrows: not one).
proc/RmItemCats(obj/Items/I)
	if(!I) return list()
	var/list/L = rm_cats_cache[I.type]
	if(!L)
		L = list()
		for(var/w in splittext("[I.rm_cats]", " ")) if(length(w)) L += w
		rm_cats_cache[I.type] = L
	if(("quiver" in L) && RemasterIsSack(I)) return L - "quiver"
	return L

// The two things in rule R's order (the first of its first category), or null.
proc/RmCombineRoles(list/R, obj/Items/A, obj/Items/B)
	var/list/ac = RmItemCats(A)
	var/list/bc = RmItemCats(B)
	if((R[2] in ac) && (R[3] in bc)) return list(A, B)
	if((R[2] in bc) && (R[3] in ac)) return list(B, A)

proc/RmCombineRule(id)
	for(var/list/R in rm_combine_rules) if(R[1] == id) return R

// A poison's dose for a weapon or an arrow: how strong it is (FoodSupply.dm RemasterPoisonDose: toxic 10-45, poison
// 8-40, strong poison 15-65).
proc/RmCombineDose(obj/Items/P)
	var/list/D = RemasterPoisonDose(P)
	return D ? D[1] : clamp(P.PoisonContent, 10, 45)

// Whether rule id can join these two now (in the rule's order).
proc/RmCombineCan(id, obj/Items/P, obj/Items/X)
	switch(id)
		if("tiparrows")
			for(var/obj/Items/Arrows/A in X) if(!A.Poisoned) return 1
			return 0
		if("coatweapon") return !X.Poisoned
	return 0

// The bag's things the held one combines with: list(ref, label, id, tip) each.
proc/RmCombineList(mob/Monsters/M, obj/Items/held)
	. = list()
	if(!istype(M) || !held || held.loc != M) return
	if(!length(RmItemCats(held) & RmCombineCats())) return
	for(var/obj/Items/X in M) if(X != held)
		for(var/list/R in rm_combine_rules)
			var/list/O = RmCombineRoles(R, held, X)
			if(O && RmCombineCan(R[1], O[1], O[2]))
				. += list(list("ref"=RemasterUIRef(X), "label"="[R[4]]: [X.name]", "id"=R[1], "tip"=R[5]))
				break

// Does it, the two in the rule's order whichever was held.
proc/RmCombineDo(id, mob/Monsters/M, obj/Items/A, obj/Items/B, Player/P)
	var/list/R = RmCombineRule(id)
	var/list/O = R ? RmCombineRoles(R, A, B) : null
	if(!O) return 0
	var/obj/Items/T = O[1]
	var/obj/Items/X = O[2]
	if(T.loc != M || X.loc != M || !RmCombineCan(id, T, X)) return 0
	switch(id)
		if("tiparrows")
			var/dose = RmCombineDose(T)
			var/n = 0
			var/empty = 0
			for(var/obj/Items/Arrows/Q in X) if(!Q.Poisoned)
				if(T.Content >= 10) break
				Q.Poisoned = 1
				Q.name = "[Q] - [T.name] Tipped"
				Q.PoisonContent = dose
				T.Content += 1
				n++
			if(T.Content >= 10)
				empty = 1
				M.weight -= T.weight
				del T
			if(P) P.RemasterNotice("[M.RemasterBareName()] tips [n] arrow[n == 1 ? "" : "s"][empty ? ": the vial is empty" : ""].")
			return n > 0
		if("coatweapon")
			var/obj/Items/Equipment/Weapon/W = X
			if(!istype(W)) return 0
			var/lo = rand(2, 4)
			var/hi = rand(2, 4)
			W.Poisoned = 1
			W.WeaponDamageMin += lo
			W.WeaponDamageMax += hi
			W.name = "[W] - [T.name] Tipped"
			W.PoisonContent = RmCombineDose(T)
			if(W.suffix == "(Equipped)")
				M.WeaponDamageMin += lo
				M.WeaponDamageMax += hi
			M.weight -= T.weight
			del T
			if(P) P.RemasterNotice("[M.RemasterBareName()] coats the [W.name].")
			return 1
	return 0
