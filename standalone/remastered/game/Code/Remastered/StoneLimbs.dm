// Stone limbs (Remastered; the user's rules of 2026-10-23). Gargoyles are stone:
//  - They never bleed (the original already leaves them out of BloodLoss() and the bleeding loop), and a limb broken
//    off falls as a stone limb (Icons/Remastered/Items/stonelimb.dmi, art/enhance/stonelimb32.py): no red on it and
//    no blood trail behind it. It is still a limb for grafting (Surgery.dm), but gives no blood to a brew.
//  - Their limbs mend and come back only with stone: a cracked or broken limb takes 1 stone to mend, a lost one 2
//    to rebuild. Stone they carry is used by itself (the "stone" use-it-yourself rule, on by default), or by one
//    of yours within 3 tiles; the Doctor brings stone from a store; the Health tab has a button. Nothing else
//    mends a gargoyle's limbs (the original's Heal() never runs for them), and a graft at the Operating table
//    only takes on a gargoyle that has stone on it (it uses one).

#define RM_STONE_MEND 1
#define RM_STONE_REBUILD 2

mob/Monsters/var/tmp/rm_stone_try_at = 0

mob/Monsters/proc/RemasterStoneBody()
	return Race == "Gargoyle"

// --- A limb breaks off --------------------------------------------------------------------------
mob/Monsters/LimbFling(NAME)
	if(!RemasterStoneBody()) return ..()
	if(Fling) return
	var/obj/Items/Bones/BloodyLimb/A = new(loc)
	A.name = "[src]'s [NAME]"
	A.rm_from_race = Race
	A.icon = 'Icons/Remastered/Items/stonelimb.dmi'
	A.icon_state = "Arm"
	A.desc = "A stone limb broken off a gargoyle."
	var/fd = pick(NORTH, SOUTH, WEST, EAST, SOUTHEAST, SOUTHWEST, NORTHEAST, NORTHWEST)
	RmG3Limb(src, NAME, fd, 2, A)   // the 3D view flies the figure's limb off, as for anyone (Combats.dm LimbFling); drawn as A, stone
	A.Fling(DIR=fd, DIST=2, BLEED=0)

// --- What needs stone ---------------------------------------------------------------------------
mob/Monsters/proc/RemasterStoneLimbMax(L)
	return max(OrganMaxHP, RemasterRaceVar("[L]MaxHP"))

// limb -> "rebuild" (gone) or "mend" (cracked or broken), legs first.
mob/Monsters/proc/RemasterStoneNeeds()
	. = list()
	if(!RemasterStoneBody() || HP <= 0 || GoingToDie) return
	for(var/L in rm_stump_limbs)
		if(!vars["Has[L]"]) .[L] = "rebuild"
		else if(vars["[L]HP"] < RemasterStoneLimbMax(L) * 0.9 || !(vars[L] in list("Good", "", null))) .[L] = "mend"

proc/RemasterStoneCost(kind)
	return kind == "rebuild" ? RM_STONE_REBUILD : RM_STONE_MEND

proc/RemasterStonesIn(list/holders)
	. = list()
	for(var/mob/Monsters/H in holders) for(var/obj/Items/ores/stone/S in H) if(S.suffix == "(Carrying)") . += S

// by mends or rebuilds limb L with stones from stones. 1 when done.
mob/Monsters/proc/RemasterStoneTreat(mob/Monsters/by, L, list/stones)
	var/list/N = RemasterStoneNeeds()
	var/kind = N[L]
	if(!kind || length(stones) < RemasterStoneCost(kind)) return 0
	for(var/i = 1, i <= RemasterStoneCost(kind), i++) RmStumpUseUp(stones[i])
	vars["Has[L]"] = 1
	vars["[L]HP"] = RemasterStoneLimbMax(L)
	vars[L] = "Good"
	if(findtext(L, "Arm")) vars["CanUse[L]"] = 1
	else if(HasLeftLeg && HasRightLeg) CanWalk = 1
	if(kind == "rebuild") LimbLoss()
	var/limb = lowertext(rm_stump_limbs[L])
	var/who = by && by != src ? "[by.RemasterBareName()] [kind == "rebuild" ? "rebuilds" : "mends"] [RemasterBareName()]'s [limb]" : "[RemasterBareName()] [kind == "rebuild" ? "rebuilds" : "mends"] the [limb]"
	view(src) << "[who] with stone."
	RemasterEvent("[who] with stone")
	var/Player/P = Owner
	if(istype(P)) P.RemasterLog("[who] with [RemasterStoneCost(kind)] stone", "good", src)
	return 1

// The first limb that the stones at hand cover, done by the first of hands. 1 when one was done.
mob/Monsters/proc/RemasterStoneTreatNow(list/hands, list/holders)
	if(!length(hands)) return 0
	var/list/N = RemasterStoneNeeds()
	var/list/S = RemasterStonesIn(holders)
	for(var/L in N) if(length(S) >= RemasterStoneCost(N[L])) return RemasterStoneTreat(hands[1], L, S)
	return 0

// --- By themselves, a friend, the Doctor ----------------------------------------------------------
mob/Monsters/RemasterCareStep(Player/P, list/claimed)
	if(RemasterStoneBody() && world.time >= rm_stone_try_at && HP > 0 && isturf(loc) && RemasterAutoUseOn("stone"))
		rm_stone_try_at = world.time + 20
		if(length(RemasterStoneNeeds()))
			var/list/hands = list()
			var/list/holders = list()
			RemasterStumpNear(hands, holders)
			if(RemasterStoneTreatNow(hands, holders)) return
	return ..()

// The Doctor brings stone to a gargoyle whose limbs need it (after any bleeding stump: Stumps.dm).
mob/Monsters/RemasterDoctorTick(Player/P)
	if(RemasterDoctorStone(P)) return
	return ..()

mob/Monsters/proc/RemasterDoctorStone(Player/P)
	if(Race == "Spider" || Wagon || !RemasterStumpCanTreat()) return 0
	var/mob/Monsters/pat
	var/pd = RM_DOCTOR_REACH + 1
	for(var/mob/Monsters/M in P.UnitList)
		if(M.Owner != P || M.z != z || M.HP <= 0 || M.Wagon || M.Egg) continue
		if(M.RemasterStumpBleeding() && get_dist(M, src) <= RM_DOCTOR_REACH) return 0   // a bleeding stump comes first
		if(!length(M.RemasterStoneNeeds())) continue
		var/d = get_dist(M, src)
		if(d < pd)
			pat = M
			pd = d
	if(!pat) return 0
	var/list/N = pat.RemasterStoneNeeds()
	var/need = RemasterStoneCost(N[N[1]])
	var/why = "[pat.RemasterBareName()]'s stone [lowertext(rm_stump_limbs[N[1]])]"
	if(length(RemasterStonesIn(list(src, pat))) >= need)
		if(pat == src || RemasterWorkToward(pat, "patient"))
			if(pat.RemasterStoneTreatNow(list(src), list(src, pat))) remaster_work_status = "Doctor: mended [why] with stone"
		else remaster_work_status = "Doctor: taking stone to [why]"
		return 1
	var/turf/S = P.RemasterStoreWith(/obj/Items/ores/stone, src)
	if(!S || get_dist(S, src) > RM_DOCTOR_REACH)
		remaster_work_status = "Doctor: [why] needs stone (mine some rock: no stone in the stores)"
		return 0
	if(!RemasterWorkToward(S, "the stone at the store"))
		remaster_work_status = "Doctor: fetching stone for [why]"
		return 1
	var/got = length(RemasterStonesIn(list(src)))
	for(var/obj/Items/ores/stone/X in range(1, S)) if(got < need && P.RemasterMayCollect(X) && PickUpItem(X)) got++
	remaster_work_status = "Doctor: took stone for [why]"
	return 1

// --- Grafts at the Operating table (Surgery.dm) -----------------------------------------------------
// A gargoyle takes a limb only with stone on it: without, it has no slot the table could fill.
mob/Monsters/RemasterMissingSlots()
	. = ..()
	if(RemasterStoneBody() && !length(RemasterStonesIn(list(src)))) return list()

mob/Monsters/RemasterAttachLimb(slot, obj/Items/I)
	if(!RemasterStoneBody()) return ..()
	var/list/S = RemasterStonesIn(list(src))
	if(!length(S)) return null
	. = ..()
	if(.) RmStumpUseUp(S[1])   // set in with stone

// --- The unit card ---------------------------------------------------------------------------------
mob/Monsters/RemasterHealthData()
	. = ..()
	if(!RemasterStoneBody()) return
	var/list/N = RemasterStoneNeeds()
	var/list/rows = list()
	for(var/L in N)
		var/c = RemasterStoneCost(N[L])
		rows += list(list("limb"=rm_stump_limbs[L], "st"="sealed",   // stone: the grey bar, never a bleeding stump's red or a bandage's amber
			"text"=(N[L] == "rebuild" ? "broken off: rebuilt only with stone ([c])" : "cracked: mended only with stone ([c])"),
			"tip"="A gargoyle's limbs mend only with stone. Stone it carries is used by itself; one of yours beside it, or the Doctor, can bring some."))
	var/list/acts = list()
	var/hint
	if(length(N))
		var/list/hands = list()
		var/list/holders = list()
		RemasterStumpNear(hands, holders)
		var/list/S = RemasterStonesIn(holders)
		for(var/L in N) if(length(hands) && length(S) >= RemasterStoneCost(N[L]))
			acts += list(list("stone", N[L] == "rebuild" ? "Rebuild with stone" : "Mend with stone", "[hands[1] == src ? "[RemasterBareName()] does it" : "[hands[1]:RemasterBareName()] does it"]: [RemasterStoneCost(N[L])] stone for the [lowertext(rm_stump_limbs[L])]."))
			break
		if(!length(acts)) hint = "No stone at hand: mined rock gives stone. Stone carried is used by itself; the Doctor fetches it from a store."
	.["stumpHead"] = "Stone limbs"
	.["stumps"] = rows
	.["stumpActs"] = acts
	.["stumpHint"] = hint
	.["ref"] = RemasterUIRef(src)

// The Health tab's "stone" button (HUD.dm "stump" command, Stumps.dm).
Player/RemasterStumpCommand(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 2 || p[2] != "stone") return ..()
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return 0
	var/list/hands = list()
	var/list/holders = list()
	M.RemasterStumpNear(hands, holders)
	if(M.RemasterStoneTreatNow(hands, holders)) return 1
	RemasterNotice("Not enough stone at hand.")
	return 0
