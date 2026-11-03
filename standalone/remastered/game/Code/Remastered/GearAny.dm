// Any unit can use any gear (the user, 2026-10-26, relayed by world-look-sky: "any unit can do any gear but its
// effectiveness is at the level they are at the full potential"; asked how strong below the gear's level: "Scaled, half at
// least (Recommended)"; asked when: "Into build 58"). Below an item's level (Gear.dm rm_use_level, rm_use2_level) a unit
// takes it up and it works at the unit's level / the item's, never below half: a weapon's own damage in a melee blow
// (Combats.dm, weapon moves too), an armour piece's protection of its part (CombatSkills.dm RemasterPartArmour). At its
// level or above, in full. Bows, picks and robes' magic aren't scaled yet: they work in full.
var/rm_gear_any_on = 1        // 0: below its level a unit can't take it up, as before
var/rm_gear_eff_floor = 0.5

proc/RmGearEff(obj/Items/I, mob/M)
	if(!rm_gear_any_on || !I || !M) return 1
	var/e = 1
	if(I.rm_use && I.rm_use_level > 1) e = min(e, RmGearLevel(M, I.rm_use) / I.rm_use_level)
	if(I.rm_use2 && I.rm_use2_level > 1) e = min(e, RmGearLevel(M, I.rm_use2) / I.rm_use2_level)
	return max(rm_gear_eff_floor, e)

// The held weapon's (a melee blow's weapon damage, Combats.dm).
proc/RmGearWeaponEff(mob/M)
	if(!rm_gear_any_on || !M) return 1
	for(var/obj/Items/Equipment/Weapon/W in M) if(W.suffix == "(Equipped)" && W.rm_gear) return RmGearEff(W, M)
	return 1
