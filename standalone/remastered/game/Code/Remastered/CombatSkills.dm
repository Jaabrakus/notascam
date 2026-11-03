// RuneScape combat skills (Skills.dm shows them). Five main skills sit over the game's
// own weapon skills, which stay as sub-skills with their own effects:
//   Attack   - land blows: the enemy dodges less
//   Strength - hit harder
//   Defence  - dodge more and take less
//   Ranged   - bows and throwing (sub-skills Bow and Throwing)
//   Magic    - race specials (fire breath, webs, ...) hit harder
// Melee XP (4 per point of damage dealt, as in RuneScape) goes by the unit's combat
// style: Accurate trains Attack, Aggressive Strength, Defensive Defence, Controlled
// all three evenly. Ranged and Magic train on their own hits.

#define RM_COMBAT_XP 1                 // XP per point of damage dealt (the user, 2026-10-26: "we can do runescapes pace": it was 4,
                                       // about 5x RuneScape's per minute of fighting as our blows hit about 5x harder)
// Training pays (the user, 2026-10-25: "the skills count about 4x as much"; at 4x a level 50 killed a recruit in 12 s, so the user chose 2x at 00:0x): a point every
// 4 levels where it was 8. Only the skills (the user chose "skills only" at 23:5x): the blow, Agility and knockback changes that came with it are out.
#define RM_ATTACK_DODGE 4              // Attack levels per point taken off the enemy's dodge chance
#define RM_STRENGTH_DMG 3              // Strength levels per point of extra damage
#define RM_DEFENCE_DMG 4               // Defence levels per point of damage taken off
#define RM_DEFENCE_DODGE 6             // Defence levels per point added to the dodge chance (and taken off a shot's chance to hit)
#define RM_RANGED_DMG 3                // Ranged levels per point of extra bow or throw damage
#define RM_RANGED_AIM 4                // Ranged levels per point added to the chance to hit
#define RM_MAGIC_PER_LEVEL 0.01        // race special damage: +1% per Magic level

mob/Monsters/var
	AttackSkill = 1
	StrengthSkill = 1
	DefenceSkill = 1
	RangedSkill = 1
	MagicSkill = 1
	ThrowingSkill = 1
	remaster_combat_style = "accurate"
	remaster_combat_seeded = 0

var/list/rm_combat_styles = list("accurate"="Accurate", "aggressive"="Aggressive", "defensive"="Defensive", "controlled"="Controlled")
var/list/rm_combat_parents = list("Sword"="Attack", "Axe"="Attack", "Mace"="Attack", "Spear"="Attack", "Dagger"="Attack",
	"UnArmed"="Attack", "Claw"="Attack", "Bow"="Ranged", "Throwing"="Ranged", "Shield"="Defence", "Armour"="Defence")

proc/RemasterCombatLevel(mob/M, id)
	if(!istype(M, /mob/Monsters)) return 1
	var/v = M.vars["[id]Skill"]
	return isnum(v) ? max(1, round(v)) : 1

// Units that existed before these skills start where their weapon skills already are.
mob/Monsters/proc/RemasterSeedCombatSkills()
	if(remaster_combat_seeded) return
	remaster_combat_seeded = 1
	var/melee = 1
	for(var/id in list("Sword", "Axe", "Mace", "Spear", "Dagger", "UnArmed", "Claw")) melee = max(melee, RmSeedLevel(id))
	var/attack = melee   // no weapon skill is above Attack (RemasterHoldWeaponSkills), so it starts at the best of them all
	for(var/id in list("Bow", "Throwing", "Shield", "Armour")) attack = max(attack, RmSeedLevel(id))
	var/list/seed = list("Attack"=attack, "Strength"=melee, "Defence"=max(RmSeedLevel("Armour"), RmSeedLevel("Shield")),
		"Ranged"=RmSeedLevel("Bow"))
	for(var/id in seed) if(seed[id] > 1)
		if(!remaster_xp) remaster_xp = list()
		remaster_xp[id] = RemasterRSXP(seed[id])
		vars["[id]Skill"] = seed[id]

// A weapon skill as seeding counts it (the user, 2026-10-26: "Yes, start at 1"): only what the unit trained past its race's
// start. So a new unit starts at 1 in Attack, Strength, Defence and Ranged, its race's weapon skills held there with their
// XP kept (RemasterHoldWeaponSkills: they come back as Attack rises); one from before these skills that trained starts where
// its training is. Saved units already seeded keep their levels (remaster_combat_seeded).
mob/Monsters/proc/RmSeedLevel(id)
	var/v = RemasterCombatLevel(src, id)
	return v > RmRaceStart(id) ? v : 1

mob/Monsters/proc/RmRaceStart(id)
	var/v = 0
	switch(id)
		if("Sword") v = initial(SwordSkill)
		if("Axe") v = initial(AxeSkill)
		if("Mace") v = initial(MaceSkill)
		if("Spear") v = initial(SpearSkill)
		if("Dagger") v = initial(DaggerSkill)
		if("UnArmed") v = initial(UnArmedSkill)
		if("Claw") v = initial(ClawSkill)
		if("Bow") v = initial(BowSkill)
		if("Throwing") v = initial(ThrowingSkill)
		if("Shield") v = initial(ShieldSkill)
		if("Armour") v = initial(ArmourSkill)
	return max(1, round(isnum(v) ? v : 1))

// Weapon skills never rise above Attack (the user's rule, 2026-10-23): Sword, Axe, Mace, Spear, Dagger,
// Bow, Unarmed, Claws, Shield, Armour and Throwing are held at the unit's Attack level, their bar just
// short of the next level. XP they earn by training there is kept (remaster_xp), so a held weapon skill
// rises with Attack as soon as Attack levels; a one-off jump (a potion, stolen thoughts) stops at Attack.
// An old save's weapon skill above Attack is held the same way the first time the unit is seen, its XP
// kept. Units whose combat skills aren't seeded (creatures and NPCs nobody owns: Attack 1) aren't held.
var/list/rm_weapon_skill_ids = list("Sword", "Axe", "Mace", "Spear", "Dagger", "Bow", "UnArmed", "Claw", "Shield", "Armour", "Throwing")

mob/Monsters/var/tmp/rm_held_at        // the Attack level the hold last ran at

// The highest value a weapon skill may have now (its level = the Attack level), or null when nothing holds it.
mob/Monsters/proc/RemasterWeaponCap(id)
	if(!remaster_combat_seeded) return null
	var/a = RemasterSkillLevel((id == "Bow" || id == "Throwing") ? RangedSkill : AttackSkill)   // bows and throws under Ranged (the user, 2026-10-25), the rest under Attack
	if(a >= RM_SKILL_MAX_LEVEL) return null
	var/d = RemasterRSXP(a + 1) - RemasterRSXP(a)
	return a + min(0.99, (d - 1) / d)

// A skill's value, held at the cap if it is a weapon skill.
mob/Monsters/proc/RemasterHeld(id, value)
	if(!(id in rm_weapon_skill_ids)) return value
	var/cap = RemasterWeaponCap(id)
	return isnull(cap) ? value : min(value, cap)

// Run by the skill tick (Skills.dm) every second and the first time a unit is seen (a loaded save): a weapon
// skill above the cap comes down to it with its XP kept; a held one whose cap has risen takes up its XP.
mob/Monsters/proc/RemasterHoldWeaponSkills(quiet = 0)
	if(!remaster_combat_seeded) return
	var/capA = RemasterWeaponCap()
	var/capR = RemasterWeaponCap("Bow")
	var/a = "[RemasterSkillLevel(AttackSkill)]|[RemasterSkillLevel(RangedSkill)]"
	var/rose = rm_held_at != a          // only then can a held one rise (and on first sight)
	rm_held_at = a
	// read directly, in rm_weapon_skill_ids order (vars by name for every unit every second is slow: Skills.dm)
	var/list/values = list(SwordSkill, AxeSkill, MaceSkill, SpearSkill, DaggerSkill, BowSkill, UnArmedSkill, ClawSkill, ShieldSkill, ArmourSkill, ThrowingSkill)
	for(var/k = 1, k <= length(values), k++)
		var/v = values[k]
		if(!isnum(v)) continue
		var/id = rm_weapon_skill_ids[k]
		var/cap = (id == "Bow" || id == "Throwing") ? capR : capA
		if(!isnull(cap) && v > cap)
			vars["[id]Skill"] = cap
			continue
		if(!rose || v < 1) continue   // a weapon the race never learnt (Bow 0) stays at 0
		var/xp = RemasterXPOf(id)
		if(xp - RemasterSkillXP(v) <= 1) continue
		var/up = RemasterSkillFromXP(xp)
		if(!isnull(cap)) up = min(up, cap)
		if(up <= v) continue
		vars["[id]Skill"] = up
		if(!quiet && istype(Owner, /Player)) Owner:RemasterSkillDrop(src, id, 0, RemasterSkillLevel(v), RemasterSkillLevel(up))

// The same hold at once, where a weapon skill rises: every swing, block, deflect and shot (Combats.dm, Combat -
// Bows.dm), a draught or stolen thoughts. A weapon skill that went over the cap gets what the skill tick would
// give it a second later: a swing's gain becomes XP (kept), a one-off jump stops at Attack. Nothing waits for the
// tick, so no blow ever lands with a weapon skill above Attack. Before a unit's first tick its first sight holds it.
mob/Monsters/proc/RemasterHoldNow()
	if(!remaster_skill_seen) return
	var/capA = RemasterWeaponCap()
	var/capR = RemasterWeaponCap("Bow")
	if(isnull(capA) && isnull(capR)) return
	var/list/values = list(SwordSkill, AxeSkill, MaceSkill, SpearSkill, DaggerSkill, BowSkill, UnArmedSkill, ClawSkill, ShieldSkill, ArmourSkill, ThrowingSkill)
	for(var/k = 1, k <= length(values), k++)
		var/v = values[k]
		var/id = rm_weapon_skill_ids[k]
		var/cap = (id == "Bow" || id == "Throwing") ? capR : capA
		if(!isnum(v) || isnull(cap) || v <= cap) continue
		var/i = RemasterSkillIndex(id)
		var/before = length(remaster_skill_seen) >= i ? remaster_skill_seen[i] : null
		if(!isnum(before) || before >= v)
			vars["[id]Skill"] = cap
		else if(v - before <= REMASTER_GRIND_MAX_STEP)
			// training: as the skill tick's (Skills.dm); RemasterAddXP holds it and tells the tick
			vars["[id]Skill"] = before
			RemasterAddXP(id, (v - before) * RemasterXPPerPoint(id) * RemasterXPRate(id, RemasterSkillLevel(before)))
		else
			// a one-off jump: as the skill tick's, stopping at Attack
			RemasterXPOf(id)
			remaster_xp[id] = max(remaster_xp[id], RemasterSkillXP(cap))
			var/now = min(cap, RemasterSkillFromXP(remaster_xp[id]))
			vars["[id]Skill"] = now
			remaster_skill_seen[i] = now
			if(istype(Owner, /Player)) Owner:RemasterSkillDrop(src, id, 0, RemasterSkillLevel(before), RemasterSkillLevel(now))

var/list/rm_skill_index   // skill id -> its place in RemasterSkillDefs() (and remaster_skill_seen)
proc/RemasterSkillIndex(id)
	if(!rm_skill_index)
		rm_skill_index = list()
		var/k = 0
		for(var/list/D in RemasterSkillDefs())
			k++
			rm_skill_index[D[1]] = k
	return rm_skill_index[id]

// The crown's health (ChangeRoyal, Crowning.dm). The user (2026-10-23): no more +25 to the weapon skills (they
// never go above Attack); the crown gives more health instead, +RM_CROWN_HEALTH where it was +100.
// A ruler crowned the old way (+100 health, +25 to seven weapon skills) has that taken off when stepping down:
// a held weapon skill first shows its full level from its XP (the skill tick is told, so the drop counts as a
// loss). Stepping down never kills: health stays at 1 or more.
// Rulership (Rulership.dm, the user's call 2026-10-23): the health now goes by the settlement's stage and the regalia
// worn, +50 at a Camp up to +RM_CROWN_HEALTH at a Kingdom (rm_seat_health), kept in line by RmSeatHealthSync. A
// ruler crowned before that (rm_seat_v 0) keeps the +150, or the old +100 and +25s, until stepping down.
#define RM_CROWN_HEALTH 150
var/list/rm_old_crown_skills = list("Spear", "Sword", "Mace", "Axe", "Dagger", "UnArmed", "Bow")
mob/Monsters/var/rm_crown_health = 0   // the health a crown gave; 0 for one crowned the old way

mob/Monsters/proc/RemasterCrownHealth(influence)
	if(influence > 0)
		rm_seat_v = 1
		rm_crown_health = 0
		RmSeatHealthSync()
		return
	var/gave = rm_crown_health
	var/seat = rm_seat_v
	rm_crown_health = 0
	rm_seat_v = 0
	if(!gave && !seat)   // crowned the old way
		gave = 100
		var/list/defs = RemasterSkillDefs()
		for(var/k = 1, k <= length(defs), k++)
			var/list/S = defs[k]
			if(!(S[1] in rm_old_crown_skills)) continue
			var/name = "[S[1]]Skill"
			var/v = vars[name]
			if(!isnum(v)) continue
			var/full = v >= 1 ? max(v, RemasterSkillFromXP(RemasterXPOf(S[1]))) : v
			if(full > v && remaster_skill_seen && length(remaster_skill_seen) >= k) remaster_skill_seen[k] = full
			vars[name] = full - 25
	MAXHP -= gave
	if(HP > 0) HP = max(1, HP - gave)
	HP = min(HP, MAXHP)

// Combat XP for damage dealt by a player's unit.
mob/Monsters/proc/RemasterCombatXP(kind, damage)
	if(damage <= 0 || !istype(Owner, /Player) || Critter || Wagon) return
	var/xp = damage * RM_COMBAT_XP
	switch(kind)
		if("melee")
			switch(remaster_combat_style)
				if("aggressive") RemasterAddXP("Strength", xp)
				if("defensive") RemasterAddXP("Defence", xp)
				if("controlled")
					RemasterAddXP("Attack", xp / 3, 1)
					RemasterAddXP("Strength", xp / 3, 1)
					RemasterAddXP("Defence", xp / 3)
				else RemasterAddXP("Attack", xp)
		if("bow") RemasterAddXP("Ranged", xp)
		if("throw")
			RemasterAddXP("Ranged", xp)
			RemasterAddXP("Throwing", xp, 1)
		if("magic") RemasterAddXP("Magic", xp)

// Hooks the combat code calls (Combats.dm, Combat - Bows.dm, Throwing.dm, Specials.dm).
// Dodging: Defence helps, the attacker's Attack cuts through. Injuries count: one lost
// leg halves it, both lost or blind and there is no dodging at all; a blind attacker
// swings wild. Only limbs actually lost count ("Destroyed"): legless creatures are
// built that way and still dodge.
proc/RemasterLost(mob/M, part)
	return (part in M.vars) && M.vars[part] == "Destroyed"
proc/RemasterDodgeChance(mob/attacker, mob/defender, base)
	if(!defender) return 0
	if(!defender.CanSee) return 0
	var/lost = (RemasterLost(defender, "LeftLeg") ? 1 : 0) + (RemasterLost(defender, "RightLeg") ? 1 : 0)
	if(lost >= 2) return 0
	var/c = base + (RemasterCombatLevel(defender, "Defence") - 1) / RM_DEFENCE_DODGE - (RemasterCombatLevel(attacker, "Attack") - 1) / RM_ATTACK_DODGE
	if(lost == 1) c /= 2
	if(attacker && !attacker.CanSee) c += 25
	return c
// A sword parry needs an arm to hold it and eyes to see the blow.
proc/RemasterCanParry(mob/M)
	return M && M.CanSee && !(RemasterLost(M, "LeftArm") && RemasterLost(M, "RightArm"))
// A melee swing past the shield and the dodge: does it land on a part at all (the user, 2026-10-26: "Yes, land roll + d20").
// About 27 in 100 untrained against untrained, as the original's part rolls came to; Attack adds a point every
// rm_melee_aim levels, the target's Defence takes one off every rm_melee_guard (as the dodge counts them).
var/rm_melee_d20 = 1     // 0: the original's part rolls (Combats.dm)
var/rm_melee_land = 27
var/rm_melee_aim = 4
var/rm_melee_guard = 6
// A weapon move's land roll (the user, 2026-10-26: "Skills chance of landing is based on attack and weapon level"): Attack
// and the move's weapon skill a point every 4 levels each, the target's Defence one off every 6.
var/rm_move_land = 30   // tuned from the duel table (40, 30, 25, 20 tried)
var/rm_move_aim = 4
var/rm_move_weapon = 4
proc/RmMoveLandChance(mob/attacker, mob/defender)
	return clamp(rm_move_land + (RemasterCombatLevel(attacker, "Attack") - 1) / rm_move_aim + (RemasterCombatLevel(attacker, attacker.rm_move_skill) - 1) / rm_move_weapon - (RemasterCombatLevel(defender, "Defence") - 1) / rm_melee_guard, 5, 95)

// A natural 20 on a land roll, a plain blow's or a move's (the user, 2026-10-26: "Natural 20 = critical"): it lands and
// does rm_crit_mult to its part.
var/rm_crit_on = 1
var/rm_crit_mult = 1.5
mob/var/tmp/rm_crit = 0     // this blow is a critical
mob/var/tmp/rm_crits = 0    // criticals it has struck (checks)

proc/RemasterMeleeLandChance(mob/attacker, mob/defender)
	return clamp(rm_melee_land + (RemasterCombatLevel(attacker, "Attack") - 1) / rm_melee_aim - (RemasterCombatLevel(defender, "Defence") - 1) / rm_melee_guard, 5, 95)

// Where a landed swing goes: one part, a d20 (Combats.dm Attack reads the Hit flags).
mob/proc/RmMeleeWhere(mob/M)
	HitHead = 0
	HitLeftArm = 0
	HitRightArm = 0
	HitLeftLeg = 0
	HitRightLeg = 0
	HitLowerBody = 0
	HitUpperBody = 0
	HitWings = 0
	rm_crit = 0
	var/chance = rm_move_sure ? RmMoveLandChance(src, M) : RemasterMeleeLandChance(src, M)   // a weapon move rolls its own (WeaponSkills.dm)
	if(rm_charge_blow) chance += rm_charge_land   // a charge's first blow (Facing.dm)
	var/ground = RmSurroundLand(src, M) + RmHighLand(src, M)   // foes round it, the higher ground (Surround.dm)
	if(ground) chance = min(95, chance + ground)
	chance = max(5, chance + RmMoraleLand(src))   // morale: shaken -3, broken -5 (Underdog.dm)
	if(rm_crit_on)
		var/low = min(rm_arc == 2 ? 18 : 20, RmMoraleCritLow(src))   // from behind 18-20 (Facing.dm); morale's: fury 18-20, emboldened 19-20 (Underdog.dm)
		if(!rm_underdog_on && istype(src, /mob/Monsters) && src:rm_mstate < 0) low = 21   // Underdog.dm off: shaken or broken, no criticals (Morale.dm)
		if(rand(1, 20) >= low)   // a natural 20: it lands whatever the odds, and hard (Combats.dm)
			rm_crit = 1
			rm_crits++
		else
			var/p = (21 - low) * 5
			if(!prob(max(0, chance - p) * 100 / (100 - p))) return   // the rest of the chance, so it lands as often as before
	else if(!prob(chance)) return
	var/d = rand(1, 20)
	if(d <= 6 && M.Race == "Spider") d = rand(7, 20)   // a spider's legs aren't struck (the original's)
	switch(d)
		if(1 to 3) HitLeftLeg = 1
		if(4 to 6) HitRightLeg = 1
		if(7 to 9) HitLeftArm = 1
		if(10 to 12) HitRightArm = 1
		if(13 to 14) HitHead = 1
		if(15 to 17) HitUpperBody = 1
		else HitLowerBody = 1

proc/RemasterMeleeBonus(mob/attacker, mob/defender)
	return (RemasterCombatLevel(attacker, "Strength") - 1) / RM_STRENGTH_DMG - (RemasterCombatLevel(defender, "Defence") - 1) / RM_DEFENCE_DMG
proc/RemasterRangedBonus(mob/attacker, mob/defender)
	return (RemasterCombatLevel(attacker, "Ranged") - 1) / RM_RANGED_DMG - (RemasterCombatLevel(defender, "Defence") - 1) / RM_DEFENCE_DMG
proc/RemasterRangedAim(mob/attacker)
	return (RemasterCombatLevel(attacker, "Ranged") - 1) / RM_RANGED_AIM - (attacker && !attacker.CanSee ? 40 : 0)
// A shot's chance to hit, the shooter's against the target's (the user, 2026-10-25: "the users range skill vs the
// defense skill"): the shooter's own (Bow or Throwing, Agility, Ranged) less the target's Defence, as melee's dodge takes
// it (RM_DEFENCE_DODGE levels a point).
proc/RemasterRangedGuard(mob/defender)
	return defender ? (RemasterCombatLevel(defender, "Defence") - 1) / RM_DEFENCE_DODGE : 0
proc/RemasterArrowHitChance(mob/archer, mob/target)
	return archer.BowSkill / 4 + archer.RmAgi() / 2 + RemasterRangedAim(archer) - RemasterRangedGuard(target)
proc/RemasterThrowHitChance(mob/thrower, mob/target, skill)
	return clamp(35 + thrower.RmAgi() + skill / 4 + RemasterRangedAim(thrower) - RemasterRangedGuard(target), 5, 95)
// Armour turning an arrow (worn chest armour, Combat - Bows.dm): the Defence and Armour skills, a tenth of each.
proc/RemasterArmourTurn(mob/defender)
	return (RemasterCombatLevel(defender, "Defence") + (isnum(defender.vars["ArmourSkill"]) ? defender.vars["ArmourSkill"] : 0)) / 10
proc/RemasterMagicScale(mob/caster)
	return 1 + (RemasterCombatLevel(caster, "Magic") - 1) * RM_MAGIC_PER_LEVEL

// HUD: the unit's style, and choosing it ("unitref|style").
Player/proc/RemasterCombatStyleCommand(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) != 2 || !(p[2] in rm_combat_styles)) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src) return 0
	M.remaster_combat_style = p[2]
	var/list/trains = list("accurate"="Attack", "aggressive"="Strength", "defensive"="Defence", "controlled"="Attack, Strength and Defence")
	var/what = trains[p[2]]
	RemasterNotice("[M.name] fights [lowertext(rm_combat_styles[p[2]])]: melee trains [what].")
	return 1

// --- Armour ---------------------------------------------------------------------------------------
// A blow loses a share to the armour covering the part it lands on, armour / (armour + RM_ARMOUR_K): 100 halves it, and
// each point helps a little less than the one before, never all the way (user, 2026-10-23: "per body part: a blow that
// hits the head is reduced by the helmet's armour, a leg hit by the leggings ... using armor / (armor + k) per piece").
// The original took Defence / 2 (arrows: all of it) off every blow, whatever was worn where. Which piece covers which
// part follows the original's own deflect check (Combats.dm CheckDefence): the head the helmet (and a crown), the upper
// and lower body and the wings the chestplate, each arm its arm piece, the legs the leggings. A unit's own toughness
// (its Defence with nothing on: a gargoyle's stone, a vampire's) covers every part; a creature that wears nothing has
// its hide everywhere. A piece counts RM_PIECE_WEIGHT times its Defence, a full suit being six pieces: a part under a
// Quality metal piece (12) is as safe as the whole body was in a full Quality suit before (72), and an uncovered part
// has only the unit's own toughness. k from the game's real armour (planning/NOTES_2026-10-23.md 7).
#define RM_ARMOUR_K 100
#define RM_PIECE_WEIGHT 6
var/list/rm_part_armour = list(
	"Head"=list(/obj/Items/Equipment/Armour/Helmet, /obj/Items/Equipment/Armour/Crown),
	"UpperBody"=list(/obj/Items/Equipment/Armour/Chestplate), "LowerBody"=list(/obj/Items/Equipment/Armour/Chestplate),
	"Wings"=list(/obj/Items/Equipment/Armour/Chestplate),
	"LeftArm"=list(/obj/Items/Equipment/Armour/LeftArm), "RightArm"=list(/obj/Items/Equipment/Armour/RightArm),
	"LeftLeg"=list(/obj/Items/Equipment/Armour/Leggings), "RightLeg"=list(/obj/Items/Equipment/Armour/Leggings))

// The armour on one part of a unit: its own toughness plus the worn pieces that cover that part.
proc/RemasterPartArmour(mob/M, region)
	if(!M) return 0
	if(!M.UsesEquipment) return max(0, M.Defence)
	var/worn = 0
	var/piece = 0
	var/list/covers = rm_part_armour[region] || rm_part_armour["UpperBody"]
	for(var/obj/Items/Equipment/Armour/A in M) if(A.suffix == "(Equipped)")
		worn += A.Defence
		for(var/T in covers) if(istype(A, T))
			piece += A.Defence * RmGearEff(A, M)   // below the unit's level, scaled (GearAny.dm)
			break
	return max(0, M.Defence - worn) + max(0, piece) * RM_PIECE_WEIGHT

// What's left of a hit on that part after its armour, when `share` of the armour counts: a javelin counts a third of
// it and a throwing axe half (Throwing.dm, as their old divisors did), a mace half (below).
proc/RemasterPartShare(mob/defender, region, share = 1)
	if(!defender) return 1
	return RM_ARMOUR_K / (RM_ARMOUR_K + RemasterPartArmour(defender, region) * max(0, share))

// A melee blow on that part. The original's special cases keep their meaning: a mace counts half the armour, so does a
// flying gargoyle's, and a mace against a gargoyle on the ground ignores it. A weapon-skill move strikes the body.
proc/RemasterArmourFactor(mob/attacker, mob/defender, region = "UpperBody")
	if(!defender) return 1
	var/share = 1
	var/mace = attacker && attacker.HoldingWeapon == "Mace"
	if(defender.Race == "Gargoyle")
		if(mace) share = 0
		else if(defender.Flying) share = 0.5
	else if(mace) share = 0.5
	return RemasterPartShare(defender, region, share)

// A creature with no body parts to hit takes the shot on its whole Defence.
proc/RemasterArmourShare(mob/defender, share = 1)
	if(!defender) return 1
	return RM_ARMOUR_K / (RM_ARMOUR_K + max(0, defender.Defence) * max(0, share))

// Where an arrow's limb roll (Combat - Bows.dm) lands: 1-2 a leg, 3-4 an arm, 5-6 an eye, 7 the heart, 8 the spleen,
// 9-10 a lung; anything else only bleeds the body.
proc/RmArrowRegion(Limb)
	switch(Limb)
		if(1) return "LeftLeg"
		if(2) return "RightLeg"
		if(3) return "RightArm"
		if(4) return "LeftArm"
		if(5, 6) return "Head"
		if(8) return "LowerBody"
	return "UpperBody"
