// Wounds bleed by a formula, like armour (Remastered; the user, 2026-10-25: "should we do a similar wound progression
// system like how we do armor percentage?"). The original's body-part code (Combats.dm Attack) takes blood for every
// wound level a part is already at, again on every cut, whatever the cut's size: a leg at 30 health lost 50 blood to a
// nick or a full blow alike, so most fights ended in a bleed-out before a limb came off. Now a cut or stab costs
//     the health it took off the part x (0.5 + 2.5 x how hurt the part already was, 0 fresh to 1 nearly gone)
// and a part it takes off or destroys its own loss (an arm or leg rm_limb_blood, 45: the user, 2026-10-25, as severing
// made 80% of duel deaths bleed-outs at the original's 90; anything else 80). Armour lowers the damage first,
// so it holds back bleeding too. The wound words (Cut, Slashed, Broken...) are the original's. Blunt blows keep the
// original's blood (they crush: Blunt.dm), arrows too (Combat - Bows.dm). Measured with tools/check_pace.py.

var/rm_wound_formula = 1          // 0: the original's stacked blood loss
var/rm_wound_base = 0.5           // blood per health taken off a fresh part
var/rm_wound_hurt = 2.5           // more per health taken off, times how hurt the part already was
var/rm_sever_on = 1               // a cut can take off a hurt arm or leg before it reaches 0 (0: only at 0, the original's)
var/rm_sever_soft = 20            // sever chance = how hurt the limb is x damage / (damage + this)
var/rm_limb_blood = 45            // blood an arm or leg costs coming off to a cut (the original's 90; the stump drains on, Stumps.dm)
var/rm_maim_guard = 60            // veterans (the user, 2026-10-25: "defense should decrease maiming chances"): the sever chance x
                                  // this / (this + Defence - 1), half at Defence 61; 0: off
var/rm_bleed_guard = 100          // and a cut's blood x this / (this + Defence - 1), 0.62 at Defence 61; 0: off

// Severing (the user, 2026-10-25, "yes, add severing": limbs came off in only about half the duels, near the end, since a
// limb needs ~100 damage of its own while blows spread over 23 parts): a cut (a slashing blow) that hurts an arm or leg it
// leaves on can take it off, with chance how hurt the limb is now x damage / (damage + rm_sever_soft): a 10-damage cut on a
// limb at half health 17%, at 20 health 27%, never a fresh one. One limb a blow, as the original's own (Combats.dm).
// A trained defender is harder to maim and bleeds less (rm_maim_guard, rm_bleed_guard: its Defence skill, CombatSkills.dm
// RemasterCombatLevel), so a veteran walks out of fights a recruit wouldn't.

// The parts a blow takes blood for (Combats.dm: each "-= Damage"), and their Has flags when the part can be lost.
var/list/rm_wound_parts = list("HeadHP", "LeftArmHP", "RightArmHP", "LeftLegHP", "RightLegHP", "WingsHP", "BrainHP",
	"GutsHP", "HeartHP", "LeftEarHP", "RightEarHP", "LeftEyeHP", "RightEyeHP", "LeftKidneyHP", "RightKidneyHP",
	"LeftLungHP", "RightLungHP", "LiverHP", "NoseHP", "SpleenHP", "StomachHP", "TeethHP", "ThroatHP")
var/list/rm_wound_limbs = list("LeftArmHP", "RightArmHP", "LeftLegHP", "RightLegHP")

mob/Monsters/var/tmp/rm_wound_in = 0   // a strike on it is being measured (a weapon move's own blows inside it count once)

// What a blow's cuts cost in blood: before = the parts' health before it (rm_wound_parts order).
// How much a defender's Defence holds back (1 untrained, 0.5 at Defence soft + 1).
proc/RmDefenceGuard(mob/Monsters/T, soft)
	if(!soft) return 1
	return soft / (soft + RemasterCombatLevel(T, "Defence") - 1)

proc/RmWoundBlood(mob/Monsters/T, list/before)
	. = 0
	var/guard = RmDefenceGuard(T, rm_bleed_guard)
	for(var/i = 1, i <= length(rm_wound_parts), i++)
		var/was = before[i]
		var/hp = T.vars[rm_wound_parts[i]]
		if(!isnum(was) || !isnum(hp) || hp >= was || was <= 0) continue
		var/hurt = clamp((100 - was) / 100, 0, 1)
		. += (min(was, was - hp)) * (rm_wound_base + rm_wound_hurt * hurt) * guard
		if(hp <= 0) . += (rm_wound_parts[i] in rm_wound_limbs) ? rm_limb_blood : 80   // taken off or destroyed
	. = round(.)

// mob/RemasterStrike: this file's part is step RmChainStrike_Wounds in Code/Remastered/Chains/Strike.dm

// A cut's chance to take off an arm or leg it hurt and left on.
proc/RmSeverRoll(mob/Monsters/T, list/before, mob/by)
	if(T.CantLoseLimbs || (T.Race in list("Devourer", "Dragon", "Spider"))) return
	for(var/i = 1, i <= length(rm_wound_parts), i++)
		var/v = rm_wound_parts[i]
		if(!(v in rm_wound_limbs)) continue
		var/side = copytext(v, 1, length(v) - 1)   // LeftArm, RightLeg...
		var/hp = T.vars[v]
		var/was = before[i]
		if(!T.vars["Has[side]"] || !isnum(hp) || !isnum(was) || hp <= 0 || hp >= was) continue
		var/cut = was - hp
		if(!prob(100 * clamp((100 - hp) / 100, 0, 1) * cut / (cut + rm_sever_soft) * RmDefenceGuard(T, rm_maim_guard) * (istype(by, /mob/Monsters) ? by:RmMoraleSever() : 1))) continue   // its morale (Morale.dm)
		if(T.RmArmourSave(side, by)) return   // the armour turns the blade: crushed (below)
		RmSever(T, side)
		return

// Takes off an arm or leg as the original's own cut at 0 health does (Combats.dm Attack): gone, its blood, its arm
// armour dropped, the limb flung, the stump (Stumps.dm LimbLoss).
proc/RmSever(mob/Monsters/T, side)
	var/nice = findtext(side, "Left") ? "Left [copytext(side, 5)]" : "Right [copytext(side, 6)]"
	T.vars["[side]HP"] = 0
	T.vars["Has[side]"] = 0
	T.vars[side] = "Destroyed"
	T.BloodContent -= rm_limb_blood
	T.BloodLoss()
	if(side == "LeftArm" || side == "RightArm")
		for(var/obj/Items/Equipment/Armour/S in T)
			if(S.suffix != "(Equipped)") continue
			if(!(side == "LeftArm" ? istype(S, /obj/Items/Equipment/Armour/LeftArm) : istype(S, /obj/Items/Equipment/Armour/RightArm))) continue
			S.suffix = null
			if(side == "LeftArm") T.WearingLeftArm = 0
			else T.WearingRightArm = 0
			T.Defence -= S.Defence
			T.weight -= S.weight
			S.loc = T.loc
			if(!S.Content3) S.DeleteItem()
		T.RebuildOverlays()
	T.LimbFling(nice)
	T.LimbLoss()
	if(Rm3DGone(T)) return
	if(prob(0.5))
		T.Fainted = 1
		T.destination = null

// Armour turns the blade (the user, 2026-10-26: "maim should also depend on armor and defense right crush instead of
// sever", "Armour save as a d20"): a cut that would take off an arm or leg in armour rolls a d20 against that limb's armour
// % (the part's armour/(armour+100), CombatSkills.dm; 5% a face: 40% saves on 13 or more). Saved, the limb is crushed
// instead: it stays on, no stump and no limb's blood, useless until it mends (in sleep or with a poultice, Health.dm,
// Healing.dm): an arm can't be used (its shield drops; its weapon drops unless the other hand is good), and with both legs
// crushed or worse it can't walk. "Armour save 14" over it in 3D and one chat line; the game's own "crushes X's left arm"
// line follows (Chat.dm). A failed save severs, with no word.
var/rm_crush_on = 1
mob/Monsters/var/tmp/rm_crushes = 0   // armour saves on it (checks)
mob/Monsters/proc/RmArmourSave(side, mob/by)
	if(!rm_crush_on) return 0
	var/obj/Items/Equipment/Armour/worn
	for(var/obj/Items/Equipment/Armour/A in src) if(A.suffix == "(Equipped)")
		for(var/T in rm_part_armour[side]) if(istype(A, T)) worn = A
		if(worn) break
	if(!worn) return 0
	var/a = RemasterPartArmour(src, side)
	var/faces = round(a / (a + RM_ARMOUR_K) * 20) + RmMoraleSave()   // its morale (Morale.dm)
	if(faces <= 0) return 0
	var/roll = rand(1, 20)
	if(roll <= 20 - faces) return 0
	rm_crushes++
	vars["[side]HP"] = min(vars["[side]HP"], 40)
	vars[side] = "Crushed"
	if(findtext(side, "Arm"))
		vars["CanUse[side]"] = 0
		if(side == "LeftArm") for(var/obj/Items/Equipment/Armour/Shield/S in src) if(S.suffix == "(Equipped)") if(UnEquipItem(S)) DropItem(S)
		if(side == "RightArm" && !(HasLeftArm && CanUseLeftArm)) for(var/obj/Items/Equipment/Weapon/W in src) if(W.suffix == "(Equipped)") if(UnEquipItem(W)) DropItem(W)
	else if((!HasLeftLeg || LeftLegHP <= 40) && (!HasRightLeg || RightLegHP <= 40)) CanWalk = 0
	var/nm = "[worn.name]"
	var/i = findtext(nm, " - ")
	if(i) nm = copytext(nm, 1, i)
	RemasterHit(src, roll, "save", by)
	RmLimbSay(by, "Armour save [roll]: [RemasterBareName()]'s [lowertext(nm)] holds!")
	return 1
