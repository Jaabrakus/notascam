// Stumps (Remastered; the user's rules of 2026-10-23, planning/NOTES_2026-10-23.md §6). A lost arm or leg
// leaves a stump that bleeds until it is treated:
//  - Open, it never stops by itself (the original's one-in-five chance to stop is held off: the hook in
//    Health.dm Bleeding()) and drains blood steadily, a leg 6 and an arm 4 every 5 s, on top of the 90 lost
//    with the limb. As the blood runs low the original's bleeding-to-death rolls take over; with none left
//    the unit dies.
//  - A bandage (Leatherworks: two from a skin, or two of spider silk) cuts the bleeding a lot but never
//    stops it: leather holds back 70 %, silk 80 %, times the maker's quality (Poor 0.85 .. Legendary 1.3),
//    at most 92 %. A better bandage can replace a worse one.
//  - Fire seals it: a torch the unit or a helper carries (Carpentry: two from a log, three searings each),
//    standing beside a campfire, forge, smelter, kitchen or burning ground, a fire spell cast on it by one of
//    your casters (Firebolt and its kin from rubies, a Flame Staff or Flametongue, a fire dragon's breath),
//    or the unit catching fire. It hurts (health, a bad memory, now and then a faint) and may fester a little
//    (a slow loss of health for three minutes; a poultice clears it).
//  - The Athelas poultice seals it and heals (Doctor.dm); an Elixir of Life or a full Healing Draught seals it
//    too (Brewing.dm); the Potion of Restoration grows the limb back, which ends the stump.
//  - Once a stump stops bleeding the blood comes back slowly (3 every 5 s), not all at once.
//  - Who treats it, by themselves: the unit with a working arm, from its own bag (a bandage, torch or poultice:
//    the "stump" use-it-yourself rule, on by default) or at a fire beside it, even under orders; with no
//    working arm, someone within 3 tiles does it. Otherwise a villager carrying something for it walks over,
//    the unit walks to a fire close by if it can still walk, and the Doctor puts stumps before all other work
//    (a poultice from its bag or the stall, else a torch or bandage from a store). No table is needed.
//  - The unit card's Health tab lists the stumps and a button for each thing that can be done right now.
//  - Saved with the army: each stump and its bandage, festering, and the blood still to come back. Units
//    loaded from a save made before stumps existed keep their long-lost limbs as healed.

#define RM_STUMP_LEG 6
#define RM_STUMP_ARM 4
#define RM_STUMP_BLOOD_BACK 3
#define RM_STUMP_FESTER 36        // stump ticks (3 minutes)
#define RM_STUMP_FIRE_WALK 15     // walks to a fire this close by itself

var/rm_stump_every = 50           // ticks between stump ticks (the arena check runs them faster)
var/rm_units_loading = 0          // LoadUnits() is running (since rm_units_loading_at)
var/rm_units_loading_at = 0
var/list/rm_stump_limbs = list("LeftLeg"="Left leg", "RightLeg"="Right leg", "LeftArm"="Left arm", "RightArm"="Right arm")

mob/Monsters/var
	list/rm_stumps                // limb -> "open", "bandaged", "sealed" or "healed"; null until first looked at
	list/rm_stump_hold            // limb -> how much of its bleeding the bandage on it holds back (percent)
	rm_stump_fester = 0           // stump ticks of festering left
	rm_blood_back = 0             // 1 while lost blood comes back slowly
mob/Monsters/var/tmp
	rm_stump_ticking = 0
	rm_stump_try_at = 0

// --- Bandages and torches --------------------------------------------------------------------------
obj/Items/RemasterBandage
	// its values: art/items/catalogue.json row remasterbandage (export_items.py writes ItemData.dm)
	var/rm_hold = 70
	Leather
		// its values: art/items/catalogue.json row remasterbandage.leather (export_items.py writes ItemData.dm)
	Silk
		// its values: art/items/catalogue.json row remasterbandage.silk (export_items.py writes ItemData.dm)

obj/Items/RemasterBandage/proc/RmSetQuality(rank)
	CraftRank = rank
	rm_hold = min(92, round(initial(rm_hold) * (rm_gear_quality[rank] || 1)))
	name = "[initial(name)] - [rank]"
	desc = "[initial(desc)] Holds back [rm_hold]% of the bleeding."

obj/Items/RemasterTorch
	name = "Torch"
	icon = 'Icons/Remastered/Items/stumpcare.dmi'
	icon_state = "torch"
	weight = 2
	var/rm_burns = 3
	desc = "A stick with a pitch-soaked rag at its head, from the Carpentry. Lit with flint and tinder when it's needed, it sears a bleeding stump shut (it hurts). Good for three searings."

// Made at the Carpentry (torches) and the Leatherworks (bandages): their menus (CraftingStations.dm).
mob/Monsters/proc/RemasterCraftStumpCare(mob/WorkShops/W, Player/P, kind)
	if(!(src in range(1, W)) || !RemasterManualHandoff(P)) return
	var/list/D = list("torch"=list(/obj/Items/RemasterTorch, /obj/Items/woods/wood, "a log of wood", "WoodCraftingSkill", "Wood crafting"),
		"leather"=list(/obj/Items/RemasterBandage/Leather, /obj/Items/Skin, "a piece of skin", "LeatherCraftingSkill", "Leather crafting"),
		"silk"=list(/obj/Items/RemasterBandage/Silk, /obj/Items/Silks/SpiderSilk, "spider silk", "LeatherCraftingSkill", "Leather crafting"))[kind]
	if(!D) return
	var/obj/Items/X
	for(var/obj/Items/Y in src) if(istype(Y, D[2]) && Y.suffix != "(Equipped)")
		X = Y
		break
	if(!X)
		P << "[src] needs [D[3]] to make [kind == "torch" ? "torches" : "bandages"]."
		return
	weight -= X.weight
	del X
	var/skill = vars[D[4]]
	vars[D[4]] += 1
	if(!prob(RemasterCraftOdds(skill)))
		P << "The attempt failed and the material is used up. [D[5]] rises with every try."
		return
	var/path = D[1]
	var/obj/Items/made
	for(var/i = 1, i <= 2, i++)
		made = new path(loc)
		if(istype(made, /obj/Items/RemasterBandage)) made:RmSetQuality(RmGearRank(skill, list()))   // Gear.dm: the skill sets the quality
	P << "[src] makes two [kind == "torch" ? "torches" : "[kind] bandages ([lowertext(made.CraftRank)], holding back [made:rm_hold]% of a stump's bleeding)"]."

proc/RmStumpUseUp(obj/Items/I)
	var/mob/H = I.loc
	if(ismob(H)) H.weight -= I.weight
	del I

// --- The stump -----------------------------------------------------------------------------------
mob/Monsters/proc/RemasterStumpsAllowed()
	return HumanParts && !CantLoseLimbs && !Undead && !Wagon && !(Race in list("Devourer", "Dragon", "Spider", "Gargoyle", "Skeleton")) && !RemasterNeverBleeds()   // a unit turned vampire isn't Undead, but never bleeds either

mob/Monsters/proc/RemasterStumpBleeding()
	if(rm_stumps) for(var/L in rm_stumps) if(rm_stumps[L] == "open" || rm_stumps[L] == "bandaged") return 1
	return 0

mob/Monsters/proc/RemasterStumpOpen()
	if(rm_stumps) for(var/L in rm_stumps) if(rm_stumps[L] == "open") return 1
	return 0

// Every path that takes a limb (or gives one back: Restoration, a graft, regrowth) calls LimbLoss() after
// it (qa-stability keeps those calls); the stumps follow from what is missing now.
mob/Monsters/LimbLoss()
	. = ..()
	if(RemasterNeverBleeds())   // a save from before the rule: LoadUnits() calls this for each unit
		BleedType = null
		rm_stumps = null   // turned vampire with a stump: it stops bleeding (RemasterStumpsAllowed)
	if(HP > 0 && !GoingToDie) RemasterStumpCheck()

// Vampires don't bleed (the user, 2026-10-23): blows still take their blood (feeding works as the original's) and
// their wounds and lost limbs keep the original's blood pictures, but they never start bleeding, so no drip, no
// "is bleeding" and no bleeding to death. Gargoyles and skeletons the original already leaves out of BloodLoss().
mob/Monsters/proc/RemasterNeverBleeds()
	return Race == "Vampire"

mob/Monsters/BloodLoss()
	if(RemasterNeverBleeds())
		BleedType = null
		return
	return ..()

// Units loaded from a save: a limb missing but not on record was lost before stumps existed (or long ago).
mob/LoadUnits()
	rm_units_loading = 1
	rm_units_loading_at = world.time
	. = ..()
	rm_units_loading = 0

mob/Monsters/proc/RemasterStumpCheck()
	if(!RemasterStumpsAllowed()) return
	if(!rm_stumps) rm_stumps = list()
	var/loading = rm_units_loading && world.time - rm_units_loading_at < 100
	for(var/L in rm_stump_limbs)
		if(vars["Has[L]"])
			if(L in rm_stumps) RemasterStumpGone(L)
			continue
		if(L in rm_stumps) continue
		rm_stumps[L] = loading ? "healed" : "open"
		if(!loading) RemasterStumpOpened(L)
	if(RemasterStumpBusy()) RemasterStumpLoop()

mob/Monsters/proc/RemasterStumpOpened(L)
	RemasterStumpBleedLevel()
	RemasterEvent("Lost the [lowertext(rm_stump_limbs[L])]: the stump bleeds")
	var/Player/P = Owner
	if(istype(P)) P.RemasterLog("[RemasterBareName()]'s [lowertext(rm_stump_limbs[L])] stump is bleeding: it needs fire or a bandage", "problem", src)

// Grown or grafted back: that stump is gone.
mob/Monsters/proc/RemasterStumpGone(L)
	var/was = rm_stumps[L] == "open" || rm_stumps[L] == "bandaged"
	rm_stumps -= L
	if(rm_stump_hold) rm_stump_hold -= L
	if(was && !RemasterStumpBleeding()) RemasterStumpStopped()

mob/Monsters/proc/RemasterStumpStopped()
	BleedType = null
	SaidBleed = 0
	if(BloodContent < MaxBloodContent) rm_blood_back = 1

mob/Monsters/proc/RemasterStumpBusy()
	if(RemasterStumpBleeding() || rm_blood_back || rm_stump_fester > 0) return 1
	if(rm_stumps) for(var/L in rm_stumps) if(rm_stumps[L] == "sealed") return 1
	return 0

// The original's bleeding words, from the blood left (Combats.dm BloodLoss()), without its message.
mob/Monsters/proc/RemasterStumpBleedLevel()
	var/t = "Very Mildly"
	if(BloodContent <= 260) t = "Mildly"
	if(BloodContent <= 130) t = "Badly"
	if(BloodContent <= 90) t = "Very Badly"
	if(BloodContent <= 20) t = "Extremly"
	BleedType = t

// The original's bleeding stops by itself one time in five (Health.dm Bleeding()): not while a stump bleeds,
// and while lost blood is coming back slowly it isn't all put back at once.
mob/proc/RemasterBleedStops()
	return 1

mob/Monsters/RemasterBleedStops()
	if(RemasterStumpBleeding()) return 0
	if(rm_blood_back)
		BleedType = null
		Owner << "<b><font color=red>[src] has stopped bleeding!!"
		return 0
	return 1

mob/Monsters/proc/RemasterStumpLoop()
	if(rm_stump_ticking) return
	rm_stump_ticking = 1
	spawn(rm_stump_every)
		while(src && RemasterStumpTick()) sleep(rm_stump_every)
		if(src) rm_stump_ticking = 0

// One stump tick: 1 to keep going.
mob/Monsters/proc/RemasterStumpTick()
	if(HP <= 0 || GoingToDie || !rm_stumps) return 0
	if(RemasterNeverBleeds())   // turned vampire with a stump open: vampires never bleed (RemasterStumpsAllowed)
		rm_stumps = null
		BleedType = null
		return 0
	var/drain = 0
	for(var/L in rm_stumps)
		var/s = rm_stumps[L]
		if(s != "open" && s != "bandaged") continue
		var/r = findtext(L, "Leg") ? RM_STUMP_LEG : RM_STUMP_ARM
		if(s == "bandaged" && rm_stump_hold) r = r * (100 - (rm_stump_hold[L] || 0)) / 100
		drain += r
	if(drain && OnFire)   // the flames sear it
		RemasterStumpSeal(src, "the flames", 0, 12)
		drain = 0
	if(drain)
		BloodContent -= drain
		RemasterStumpBleedLevel()
		if(BloodContent <= 0)
			if(RmBleedOut(src)) return 1   // down and dying, a minute to be saved (BleedOut.dm)
			RemasterStumpDeath("Bled to death from a stump")
			return 0
	else if(rm_blood_back)
		BloodContent = min(MaxBloodContent, BloodContent + RM_STUMP_BLOOD_BACK)
		if(BloodContent >= MaxBloodContent) rm_blood_back = 0
	if(rm_stump_fester > 0)
		rm_stump_fester--
		HP -= 1
		if(HP <= 0)
			RemasterStumpDeath("A festering stump")
			return 0
	if(!drain && !rm_blood_back && rm_stump_fester <= 0)
		for(var/L in rm_stumps) if(rm_stumps[L] == "sealed") rm_stumps[L] = "healed"
		return 0
	return 1

mob/Monsters/proc/RemasterStumpDeath(why)
	DeathType = why
	GoingToDie = 1
	view(src) << "<b><font color=red>[src] [findtext(why, "Bled") ? "has bled to death" : "dies of a festering wound"]!!"
	Death()

// --- Treating it ---------------------------------------------------------------------------------
// Fire seals every bleeding stump. by: who did it; what: "a torch", "the campfire"...; pain: health lost;
// festers: the chance in 100 that the burn festers.
mob/Monsters/proc/RemasterStumpSeal(mob/Monsters/by, what, pain = 20, festers = 12)
	var/n = 0
	for(var/L in rm_stumps) if(rm_stumps[L] == "open" || rm_stumps[L] == "bandaged")
		rm_stumps[L] = "sealed"
		n++
	if(!n) return 0
	if(rm_stump_hold) rm_stump_hold.Cut()
	RemasterStumpStopped()
	var/fester = festers && prob(festers)
	if(fester) rm_stump_fester = RM_STUMP_FESTER
	var/who = by && by != src ? "[by:RemasterBareName()] sears [RemasterBareName()]'s stump with [what]" : "[RemasterBareName()] sears the stump with [what]"
	if(pain)
		HP -= pain
		RemasterHit(src, pain, "burn", by)
		RemasterRemember("seared", "Had a stump seared shut", -10, 2)
		if(prob(15) && HP > 0 && !Fainted)
			Fainted = 1
			view(src) << "[src] passes out from the pain!"
			spawn(100) if(src && Fainted && !RemasterKnockedOut()) Fainted = 0
	view(src) << "<font color=#e0802a>[who]: the bleeding stops.</font>"
	RemasterEvent("[who]: the bleeding stopped[fester ? "; the burn festers" : ""]")
	var/Player/P = Owner
	if(istype(P)) P.RemasterLog("[who]: the bleeding stopped[fester ? ", but the burn is festering (a poultice clears it)" : ""]", "good", src)
	if(HP <= 0)
		RemasterStumpDeath("The shock of a searing")
		return n
	RemasterStumpLoop()
	return n

// A bandage on the worst stump it helps: an open one (legs first), or one held by a worse bandage.
mob/Monsters/proc/RemasterStumpBandageSpot(hold)
	if(!rm_stumps) return null
	for(var/L in rm_stump_limbs) if(rm_stumps[L] == "open") return L
	for(var/L in rm_stump_limbs) if(rm_stumps[L] == "bandaged" && (!rm_stump_hold || (rm_stump_hold[L] || 0) < hold)) return L
	return null

mob/Monsters/proc/RemasterStumpBandage(mob/Monsters/by, obj/Items/RemasterBandage/B)
	var/L = RemasterStumpBandageSpot(B.rm_hold)
	if(!L) return 0
	if(!rm_stump_hold) rm_stump_hold = list()
	rm_stumps[L] = "bandaged"
	rm_stump_hold[L] = B.rm_hold
	var/what = lowertext(B.name)
	RmStumpUseUp(B)
	rm_bandaged_until = world.time + 36000
	var/limb = lowertext(rm_stump_limbs[L])
	var/who = by && by != src ? "[by:RemasterBareName()] binds [RemasterBareName()]'s [limb] stump" : "[RemasterBareName()] binds the [limb] stump"
	view(src) << "[who] with a [what]: it still bleeds, slowly."
	RemasterEvent("[who] with a [what]")
	var/Player/P = Owner
	if(istype(P)) P.RemasterLog("[who] with a [what] (holds [rm_stump_hold[L]]%): it still bleeds slowly until it's seared or dressed with a poultice", "good", src)
	return 1

// The Athelas poultice seals a stump and heals as before (Doctor.dm); the stump's blood comes back slowly.
mob/Monsters/RemasterApplyRemedy(remedy, mob/Monsters/by)
	var/stump = remedy == "poultice" && RemasterStumpBleeding()
	var/fester = remedy == "poultice" && rm_stump_fester > 0
	var/blood = BloodContent
	. = ..()
	if(!. || remedy != "poultice") return
	if(fester) rm_stump_fester = 0
	if(stump)
		BloodContent = blood
		RemasterStumpSeal(by || src, "an Athelas poultice", 0, 0)
	else if(fester) RemasterEvent("The festering burn is cleaned and dressed")

// Brews (Brewing.dm): an Elixir of Life makes them whole, a full Healing Draught closes the wound.
// Alchemist's Fire and Dragonfire set the drinker alight, which sears it (RemasterStumpTick).
Player/RemasterDrinkBrew(mob/Monsters/M, obj/Items/Potions/RemasterBrew/B)
	var/list/had = B && B.brew ? B.brew.Copy() : list()
	var/stump = M && M.RemasterStumpBleeding()
	. = ..()
	if(!M || Rm3DGone(M) || M.HP <= 0 || M.GoingToDie) return   // a bad brew may have killed it (Brewing.dm)
	if(had["elixir"])
		M.rm_stump_fester = 0
		if(stump) M.RemasterStumpSeal(M, "an Elixir of Life", 0, 0)
	else if(stump && had["healing"] >= 5) M.RemasterStumpSeal(M, "a Healing Draught", 0, 0)

// A fire spell from the original's ruby magic (Interact.dm Firebolt, Fireball, Fiery Death) cast by one of
// yours on one of yours: the wound is seared shut (the spell has already hurt them).
mob/Monsters/proc/RemasterSpellSear(mob/Monsters/C, what)
	if(!istype(C) || C.Owner != Owner || HP <= 0 || GoingToDie || !RemasterStumpBleeding()) return 0
	return RemasterStumpSeal(C, what, 0, 6)

// --- What can be done now ------------------------------------------------------------------------
mob/Monsters/proc/RemasterStumpCanTreat()
	return HP > 0 && !GoingToDie && !Fainted && !Stunned && !Sleeping && !RemasterKnockedOut() && !Wagon && !Egg && HumanParts && rm_cap_state != "bound" && ((HasLeftArm && CanUseLeftArm) || (HasRightArm && CanUseRightArm))

proc/RemasterFireBeside(atom/A)
	if(!A || !isturf(A.loc)) return null
	for(var/atom/F in range(1, A))
		if(istype(F, /mob/WorkShops/CampFires/Fire) || istype(F, /mob/WorkShops/Forge) || istype(F, /mob/WorkShops/Smelters) || istype(F, /mob/WorkShops/Melter) || istype(F, /mob/WorkShops/Kitchen) || istype(F, /obj/Fire) || istype(F, /obj/RemasterFlame)) return F
		if(isturf(F))
			var/datum/rm_air/G = rm_air_of[F]
			if((G && G.burning) || F.icon_state == "Lava") return F
	return null

proc/RemasterFireNear(mob/M, reach)
	var/atom/best
	var/best_d = reach + 1
	for(var/mob/WorkShops/W in range(reach, M))
		if(!istype(W, /mob/WorkShops/CampFires/Fire) && !istype(W, /mob/WorkShops/Forge) && !istype(W, /mob/WorkShops/Smelters) && !istype(W, /mob/WorkShops/Kitchen)) continue
		var/d = get_dist(W, M)
		if(d < best_d)
			best = W
			best_d = d
	return best

proc/RemasterFireName(atom/F)
	if(istype(F, /mob/WorkShops/CampFires/Fire)) return "campfire"
	if(istype(F, /mob/WorkShops/Forge)) return "forge"
	if(istype(F, /mob/WorkShops/Smelters)) return "smelter"
	if(istype(F, /mob/WorkShops/Melter)) return "melter"
	if(istype(F, /mob/WorkShops/Kitchen)) return "kitchen fire"
	if(isturf(F) && F.icon_state == "Lava") return "lava"
	return "fire"

// A walkable tile beside (range 1 of) a fire or a patient.
proc/RemasterTileBeside(atom/A, mob/M)
	var/turf/best
	var/best_d = 1#INF
	for(var/turf/T in range(1, A))
		if(T.density || T == A) continue
		var/blocked = 0
		for(var/atom/movable/O in T) if(O.density && O != M)
			blocked = 1
			break
		if(blocked) continue
		var/d = get_dist(T, M)
		if(d < best_d)
			best = T
			best_d = d
	return best

// The best carried item of a kind among holders (their bags), or null.
mob/Monsters/proc/RemasterStumpFind(kind, list/holders)
	var/obj/Items/best
	var/best_v = 0
	for(var/mob/Monsters/H in holders) for(var/obj/Items/I in H)
		if(I.suffix != "(Carrying)") continue
		var/v = 0
		switch(kind)
			if("bandage") if(istype(I, /obj/Items/RemasterBandage) && RemasterStumpBandageSpot(I:rm_hold)) v = I:rm_hold
			if("torch") if(istype(I, /obj/Items/RemasterTorch)) v = 4 - I:rm_burns   // a used one first
			if("poultice") if(istype(I, /obj/Items/RemasterRemedy) && I:remedy == "poultice") v = 1
			if("elixir") if(istype(I, /obj/Items/Potions/RemasterBrew) && I:brew && I:brew["elixir"]) v = 1
			if("healing") if(istype(I, /obj/Items/Potions/RemasterBrew) && I:brew && I:brew["healing"] >= 5) v = I:brew["healing"]
			if("restore") if(I.name == "Potion of Restoration" && !I.IsEmpty) v = 1
		if(v > best_v)
			best = I
			best_v = v
	return best

// Fire casters of yours within 5 tiles (the original spells' reach) that can sear now:
// list(list(caster, spell id, label, pain, weapon)).
mob/Monsters/proc/RemasterStumpCasters()
	. = list()
	if(!isturf(loc)) return
	for(var/mob/Monsters/C in range(5, src))
		if(C.Owner != Owner || C.HP <= 0 || C.GoingToDie || C.Fainted || C.Stunned || C.Sleeping || C.RemasterKnockedOut() || C.rm_cap_state == "bound") continue
		if(C.GargRuby >= 15 && !C.PracticeSkill && !C.Flying)
			. += list(list(C, "ruby", C.GargRuby >= 100 ? "Fiery Death" : C.GargRuby >= 30 ? "a fireball" : "a firebolt", C.GargRuby >= 100 ? 30 : C.GargRuby >= 30 ? 20 : 15, null))
			continue
		var/obj/Items/W = RmHeldWeapon(C)
		if(W && (W.rm_gear == "magic.flame staff" || W.rm_gear == "magic.flame sword") && RmManaOf(W) >= 5)
			. += list(list(C, "weapon", W.rm_gear == "magic.flame staff" ? "the Flame Staff's fire" : "Flametongue's flame", 15, W))
			continue
		if(C.Race == "Dragon" && C.RemasterBreathElement() == "fire" && C.RemasterSpecialAble() && world.time >= C.remaster_special_at)
			. += list(list(C, "breath", "a breath of dragonfire", 30, null))

// What can be done for this unit's bleeding stumps right now, best first. hands: who may do it (the first
// is used); holders: whose bags count; casters: include fire spells. Each: list("kind", "label", "tip",
// "by", "item"); "item" is the thing used up, the fire, or the caster's weapon.
mob/Monsters/proc/RemasterStumpChoices(list/hands, list/holders, casters = 1)
	. = list()
	if(!RemasterStumpBleeding()) return
	var/mob/Monsters/hand = length(hands) ? hands[1] : null
	var/hn = hand ? (hand == src ? "[RemasterBareName()] does it" : "[hand.RemasterBareName()] does it") : ""
	if(hand)
		var/atom/F = RemasterFireBeside(src)
		if(F) . += list(list("kind"="fire", "label"="Sear at the [RemasterFireName(F)]", "tip"="Holds the stump to the [RemasterFireName(F)]: the bleeding stops. It hurts and may fester. [hn].", "by"=hand, "item"=F))
		var/obj/Items/I = RemasterStumpFind("poultice", holders)
		if(I) . += list(list("kind"="poultice", "label"="Athelas poultice", "tip"="Stops the bleeding and heals (+80 health). [hn].", "by"=hand, "item"=I))
		I = RemasterStumpFind("elixir", holders)
		if(I) . += list(list("kind"="elixir", "label"="Elixir of Life", "tip"="Drink it: made whole, the bleeding stops.", "by"=hand, "item"=I))
		I = RemasterStumpFind("healing", holders)
		if(I) . += list(list("kind"="healing", "label"="Healing Draught", "tip"="Drink it: the wound closes and the bleeding stops.", "by"=hand, "item"=I))
		I = RemasterStumpFind("torch", holders)
		if(I) . += list(list("kind"="torch", "label"="Sear with a torch", "tip"="Stops the bleeding. It hurts and may fester. [hn] ([I:rm_burns] searing\s left in it).", "by"=hand, "item"=I))
	if(casters) for(var/list/C in RemasterStumpCasters())
		var/mob/Monsters/K = C[1]
		. += list(list("kind"="spell", "label"="Sear with fire magic", "tip"="[K.RemasterBareName()] casts [C[3]] on the wound: the bleeding stops. It hurts.", "by"=K, "item"=C[5], "spell"=C[2], "what"=C[3], "pain"=C[4]))
		break
	if(hand)
		var/obj/Items/B = RemasterStumpFind("bandage", holders)
		if(B) . += list(list("kind"="bandage", "label"="Bandage it", "tip"="A [lowertext(B.name)] holds back [B:rm_hold]% of the bleeding; it still bleeds slowly. [hn].", "by"=hand, "item"=B))
		var/obj/Items/R = RemasterStumpFind("restore", holders)
		if(R) . += list(list("kind"="restore", "label"="Potion of Restoration", "tip"="Drink it: the limb grows back.", "by"=hand, "item"=R))

// Who can help right here: the unit itself first, then yours within 3 tiles; and whose bags count.
mob/Monsters/proc/RemasterStumpNear(list/hands, list/holders)
	if(RemasterStumpCanTreat()) hands += src
	holders += src
	if(!istype(Owner, /Player) || !isturf(loc)) return
	for(var/mob/Monsters/F in range(REMASTER_SHARE_RANGE, src))
		if(F == src || F.Owner != Owner || F.HP <= 0 || F.Wagon) continue
		holders += F
		if(F.RemasterStumpCanTreat()) hands += F

mob/Monsters/proc/RemasterStumpDo(list/O, Player/P)
	var/mob/Monsters/by = O["by"]
	var/obj/Items/I = O["item"]
	switch(O["kind"])
		if("fire") return RemasterStumpSeal(by, "the [RemasterFireName(I)]", 20, 12)
		if("torch")
			I:rm_burns--
			if(I:rm_burns <= 0) RmStumpUseUp(I)
			else I.desc = "[initial(I.desc)] [I:rm_burns] searing\s left."
			return RemasterStumpSeal(by, "a torch", 20, 12)
		if("spell")
			switch(O["spell"])
				if("ruby")
					if(by.PracticeSkill) return 0
					by.PracticeSkill = 1
					spawn(100) if(by) by.PracticeSkill = 0
				if("weapon") if(!RmManaSpend(I, 5)) return 0
				if("breath")
					if(world.time < by.remaster_special_at) return 0
					by.remaster_special_at = world.time + rm_specials["Dragon"][6] * 10
			view(by) << "[by] casts [O["what"]] on [src]'s stump!"
			return RemasterStumpSeal(by, O["what"], O["pain"], 6)
		if("bandage") return RemasterStumpBandage(by, I)
		if("poultice")
			if(!RemasterApplyRemedy("poultice", by)) return 0
			if(I) RmStumpUseUp(I)
			return 1
		if("elixir", "healing", "restore")
			if(!istype(P)) return 0
			var/mob/Monsters/holder = I.loc
			if(holder != src && !RemasterHandOver(I, holder, src)) return 0
			if(O["kind"] == "restore") return P.RemasterUseFor(src, I)
			P.RemasterDrinkBrew(src, I)
			return 1
	return 0

// --- By themselves: self-care, a helper, the Doctor ------------------------------------------------
// Runs before the rest of care (Care.dm RemasterCareStep); 1 when it took this care step.
mob/Monsters/RemasterCareStep(Player/P, list/claimed)
	if(RemasterStumpCare(P)) return
	return ..()

mob/Monsters/proc/RemasterStumpCare(Player/P)
	if(remaster_care == "stumphelp") return RemasterStumpHelpStep(P)
	if(remaster_care == "stumpfire") return RemasterStumpFireStep(P)
	if(HP <= 0 || GoingToDie || !isturf(loc)) return 0
	if(!RemasterStumpBleeding())
		rm_help_called = 0   // seen to: its next wound calls again
		return 0
	// Its own means first, at once, even under orders (it doesn't move): its own bag, or a fire beside it (the user,
	// 2026-10-26: "Stay instant and treating a friend only happens when the injured doesn't have a way to heal themselves
	// they call nearby units once").
	if(RemasterAutoUseOn("stump") && RemasterStumpCanTreat() && rm_mstate != 2)   // battle fury: no bandaging itself (Morale.dm)
		var/list/own = RemasterStumpChoices(list(src), list(src), 0)
		for(var/list/O in own.Copy()) if(O["kind"] == "restore") own -= list(O)   // the "restore" rule drinks that (Bag.dm)
		if(length(own))
			if(world.time < rm_stump_try_at) return 0   // tried a moment ago: again shortly, and no call meanwhile
			rm_stump_try_at = world.time + 20
			for(var/list/O in own) if(RemasterStumpDo(O, P)) return 1
	if(!RemasterStumpBleeding() || remaster_care) return 0
	// Else to a fire close by, while it can walk and isn't being directed.
	if(CanWalk && RemasterStumpCanTreat() && world.time >= remaster_care_hold && !Target && !RemasterCareBlocked("stumpfire") && !(RemasterHasOrder() && !(remaster_active && remaster_active.automatic)))
		var/atom/F = RemasterFireNear(src, RM_STUMP_FIRE_WALK)
		var/turf/T = F ? RemasterTileBeside(F, src) : null
		if(T)
			RemasterCareStart("stumpfire", F, T, "Bleeding: going to the [RemasterFireName(F)] to sear the stump")
			return 1
	// No way of its own: it calls for help, once. A friend within 3 tiles with something for it does it now (from its
	// own bag or the hurt one's); else the nearest who is free and carries something comes over.
	if(rm_help_called) return 0
	rm_help_called = 1
	var/list/hands = list()
	var/list/holders = list()
	RemasterStumpNear(hands, holders)
	hands -= src
	if(length(hands)) for(var/list/O in RemasterStumpChoices(hands, holders, 0))
		if(O["kind"] == "restore") continue
		if(RemasterStumpDo(O, P)) return 1
	if(RemasterStumpHelperComing()) return 0
	var/mob/Monsters/H = P.RemasterStumpHelper(src)
	if(H)
		H.RemasterCareStart("stumphelp", src, loc, "Going to treat [name]'s stump")
		remaster_care_note = "Bleeding: called for help, [H.name] is coming"
		return 0
	remaster_care_note = "Bleeding: called for help and no one could come (fire, a bandage or a Doctor)"
	return 0

mob/Monsters/proc/RemasterStumpHelperComing()
	for(var/mob/Monsters/M in range(30, src)) if(M.remaster_care == "stumphelp" && M.remaster_care_target == src) return M
	return null

// The nearest villager free to come who carries something for this stump (the Doctor comes by its job).
Player/proc/RemasterStumpHelper(mob/Monsters/H)
	var/mob/Monsters/best
	var/best_d = 21
	for(var/mob/Monsters/M in UnitList)
		if(M == H || M.Owner != src || M.remaster_care || M.Wagon || M.Egg || M.Critter || M.HP <= 0 || M.z != H.z || !isturf(M.loc)) continue
		if(M.remaster_job == "doctor" || M.Target || M.remaster_defense || world.time < M.remaster_care_hold || !M.CanWalk || !M.RemasterStumpCanTreat()) continue
		if(M.RemasterHasOrder() && !(M.remaster_active && M.remaster_active.automatic)) continue
		var/d = get_dist(M, H)
		if(d >= best_d) continue
		if(!length(H.RemasterStumpChoices(list(M), list(M), 0))) continue
		best = M
		best_d = d
	return best

mob/Monsters/proc/RemasterStumpHelpStep(Player/P)
	var/mob/Monsters/H = remaster_care_target
	if(HP <= 0 || GoingToDie || Fainted || Stunned || Sleeping || !isturf(loc))
		RemasterCareDone()
		return 0
	if(!istype(H) || H.HP <= 0 || H.GoingToDie || H.z != z) return RemasterCareDone() || 1
	if(!H.RemasterStumpBleeding()) return RemasterCareDone("[H.name]'s stump is seen to") || 1
	if(world.time - remaster_care_since > REMASTER_CARE_GIVE_UP) return RemasterCareDone("Gave up: couldn't reach [H.name]") || 1
	if(get_dist(src, H) <= 1)
		var/done = 0
		for(var/list/O in H.RemasterStumpChoices(list(src), list(src), 0)) if(H.RemasterStumpDo(O, P))
			done = 1
			break
		RemasterCareDone(done ? "Treated [H.name]'s stump" : "Had nothing for [H.name]'s stump")
		return 1
	if(destination != H.loc)
		destination = H.loc
		remaster_care_dest = H.loc
	return 1

mob/Monsters/proc/RemasterStumpFireStep(Player/P)
	var/atom/F = remaster_care_target
	if(HP <= 0 || GoingToDie || Fainted || Stunned || !isturf(loc))
		RemasterCareDone()
		return 0
	if(!RemasterStumpBleeding()) return RemasterCareDone("Stump seared") || 1
	if(!F || !F.z || F.z != z) return RemasterCareDone("The fire went out") || 1
	if(world.time - remaster_care_since > REMASTER_CARE_GIVE_UP)
		if(!remaster_care_retry) remaster_care_retry = list()
		remaster_care_retry["stumpfire"] = world.time + 3000
		return RemasterCareDone("Gave up: couldn't reach the fire") || 1
	if(RemasterFireBeside(src) && RemasterStumpCanTreat())
		var/list/C = RemasterStumpChoices(list(src), list(), 0)
		if(length(C) && C[1]["kind"] == "fire") RemasterStumpDo(C[1], P)
		return RemasterCareDone("Seared the stump at the [RemasterFireName(F)]") || 1
	var/turf/T = RemasterTileBeside(F, src)
	if(T && destination != T)
		destination = T
		remaster_care_dest = T
	return 1

// A bleeding stump is the gravest case: the Doctor and self-care fetch a poultice for it (Doctor.dm).
mob/Monsters/RemasterNeeds()
	. = ..()
	if(HP > 0 && !GoingToDie && RemasterStumpBleeding() && (!. || .[2] < 7)) return list("poultice", 7, "a bleeding stump")

// The Doctor puts stumps first: with something for it in hand (or a fire beside the patient) it goes and
// treats it; else it fetches a poultice from the stall (its usual remedy run), or a torch or a bandage from
// a store. No table needed.
mob/Monsters/RemasterDoctorTick(Player/P)
	if(RemasterDoctorStump(P)) return
	return ..()

mob/Monsters/proc/RemasterDoctorStump(Player/P)
	if(Race == "Spider" || Wagon || !RemasterStumpCanTreat()) return 0
	var/mob/Monsters/pat
	var/pd = RM_DOCTOR_REACH + 1
	for(var/mob/Monsters/M in P.UnitList)
		if(M.Owner != P || M.z != z || M.Wagon || M.Egg || M.HP <= 0 || !M.RemasterStumpBleeding()) continue
		var/d = get_dist(M, src)
		if(d < pd)
			pat = M
			pd = d
	if(!pat) return 0
	var/why = "[pat.RemasterBareName()]'s bleeding stump"
	var/list/C = pat.RemasterStumpChoices(list(src), list(src), 0)
	for(var/list/O in C.Copy()) if(O["kind"] == "restore") C -= list(O)
	if(length(C))
		if(pat == src || RemasterWorkToward(pat, "patient"))
			for(var/list/O in C) if(pat.RemasterStumpDo(O, P))
				remaster_work_status = "Doctor: treated [why]"
				break
		else remaster_work_status = "Doctor: going to [why]"
		return 1
	if(P.RemasterClinicWith("poultice", src) || P.RemasterClinicWith("athelas", src))
		if(RemasterDoctorGet(P, "poultice", why) != -1) return 1
	var/obj/Items/I = P.RemasterStumpKitLying(src, pat)
	if(I)
		if(RemasterWorkToward(I, lowertext(I.name)))
			PickUpItem(I)
			remaster_work_status = "Doctor: took a [lowertext(I.name)] for [why]"
		else remaster_work_status = "Doctor: fetching a [lowertext(I.name)] for [why]"
		return 1
	remaster_work_status = "Doctor: [why] needs fire, a bandage or a poultice (bandages: a Leatherworks; torches: a Carpentry)"
	return 0

// A torch (or a bandage that helps) lying on a store or zone, nearest first.
Player/proc/RemasterStumpKitLying(mob/Monsters/D, mob/Monsters/pat)
	var/obj/Items/best
	for(var/kind in list(/obj/Items/RemasterTorch, /obj/Items/RemasterBandage))
		for(var/turf/S in RemasterStores()) if(S.z == D.z && get_dist(S, D) <= RM_DOCTOR_REACH)
			for(var/obj/Items/I in range(1, S))
				if(!istype(I, kind) || !RemasterMayCollect(I)) continue
				if(istype(I, /obj/Items/RemasterBandage) && !pat.RemasterStumpBandageSpot(I:rm_hold)) continue
				if(!best || get_dist(D, I) < get_dist(D, best)) best = I
		if(best) return best
	return null

// --- The unit card ---------------------------------------------------------------------------------
mob/Monsters/proc/RemasterStumpWarnings()
	. = list()
	if(RemasterStumpOpen()) . += "Bleeding stump"
	else if(RemasterStumpBleeding()) . += "Bandaged stump"
	if(rm_stump_fester > 0) . += "Festering burn"

mob/Monsters/RemasterAilmentWarnings()
	. = ..()
	. += RemasterStumpWarnings()

mob/Monsters/RemasterHealthData()
	. = ..()
	if(!rm_stumps && !rm_blood_back) return
	var/list/rows = list()
	for(var/L in rm_stump_limbs)
		var/s = rm_stumps ? rm_stumps[L] : null
		if(!s || s == "healed") continue
		var/text
		var/tip
		switch(s)
			if("open")
				text = "stump, bleeding: needs fire or a bandage"
				tip = "Bleeding [findtext(L, "Leg") ? RM_STUMP_LEG : RM_STUMP_ARM] blood every 5 s, and it won't stop by itself.\nFire seals it (a torch, a campfire or forge beside it, a fire spell); a bandage slows it; a poultice or a Potion of Restoration ends it."
			if("bandaged")
				var/h = rm_stump_hold ? (rm_stump_hold[L] || 0) : 0
				text = "stump, bandaged: still bleeding slowly"
				tip = "The bandage holds back [h]% of the bleeding. It still needs fire or a poultice to stop."
			if("sealed")
				text = "stump, seared shut"
				tip = "The bleeding has stopped[rm_blood_back ? "; the lost blood comes back slowly" : ""]."
		rows += list(list("limb"=rm_stump_limbs[L], "st"=s, "text"=text, "tip"=tip))
	var/list/acts = list()
	var/hint
	if(RemasterStumpBleeding())
		var/list/hands = list()
		var/list/holders = list()
		RemasterStumpNear(hands, holders)
		for(var/list/O in RemasterStumpChoices(hands, holders)) acts += list(list(O["kind"], O["label"], O["tip"]))
		var/Player/P = Owner
		var/atom/F = RemasterFireBeside(src) ? null : RemasterFireNear(src, RM_STUMP_FIRE_WALK)
		if(F && CanWalk && RemasterStumpCanTreat()) acts += list(list("walkfire", "Go to the [RemasterFireName(F)]", "[get_dist(src, F)] tiles off: walks there and sears the stump."))
		if(istype(P) && !RemasterStumpHelperComing())
			var/mob/Monsters/H = P.RemasterStumpHelper(src)
			if(H) acts += list(list("call", "Call [H.RemasterBareName()]", "[H.RemasterBareName()] carries something for it and comes over."))
		if(!length(acts)) hint = "Nothing at hand: bandages come from a Leatherworks (a skin or spider silk), torches from a Carpentry (a log). A Doctor's poultice, a Potion of Restoration or a fire close by also work."
	var/list/conds = list()
	if(rm_stump_fester > 0) conds += list(list("Festering burn", 3))
	if(rm_blood_back) conds += list(list("Blood coming back", 1))
	.["conds"] = conds + .["conds"]
	.["stumps"] = rows
	.["stumpActs"] = acts
	.["stumpHint"] = hint
	.["ref"] = RemasterUIRef(src)

// value: "unitref|kind" from the Health tab's buttons (HUD.dm "stump").
Player/proc/RemasterStumpCommand(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || M.HP <= 0 || !M.RemasterStumpBleeding()) return 0
	switch(p[2])
		if("walkfire")
			var/atom/F = RemasterFireNear(M, RM_STUMP_FIRE_WALK)
			var/turf/T = F ? RemasterTileBeside(F, M) : null
			if(!T || !M.CanWalk) return 0
			if(M.remaster_care) M.RemasterCareDone()
			M.RemasterCareStart("stumpfire", F, T, "Bleeding: going to the [RemasterFireName(F)] to sear the stump")
			RemasterNotice("[M.RemasterBareName()] goes to the [RemasterFireName(F)] to sear the stump.")
			return 1
		if("call")
			var/mob/Monsters/H = RemasterStumpHelper(M)
			if(!H) return 0
			H.RemasterCareStart("stumphelp", M, M.loc, "Going to treat [M.name]'s stump")
			RemasterNotice("[H.RemasterBareName()] comes to treat [M.RemasterBareName()]'s stump.")
			return 1
	var/list/hands = list()
	var/list/holders = list()
	M.RemasterStumpNear(hands, holders)
	for(var/list/O in M.RemasterStumpChoices(hands, holders)) if(O["kind"] == p[2])
		usr = src
		if(M.RemasterStumpDo(O, src)) return 1
		RemasterNotice("That can't be done just now.")
		return 0
	RemasterNotice("That isn't at hand any more.")
	return 0
