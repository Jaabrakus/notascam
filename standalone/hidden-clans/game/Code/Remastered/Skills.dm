// RuneScape-style skills. The game's own skill numbers stay the source of
// truth for every formula (chop speed, craft success, quality): a skill of
// 20.45 is level 20, 45% of the way to 21.
// XP shown to the player follows RuneScape's XP table (99 = 13,034,431 XP), so
// drops grow with level. Large one-off changes (crowning +25, inheritance,
// potions, stolen thoughts) are not scaled.
// Pace (planning/SKILLS_PACING.md): the game's own gains come every swing, so on
// their own they would level a skill at the same XP an hour from 1 to 99. In
// RuneScape the XP an hour grows with the level (better trees, rocks, fish), so
// training XP here is scaled by the level: about a sixth of it at level 1, all of
// it at 99. A fresh unit gets its first levels in minutes, 50 in an evening of
// work and 99 after a few hundred hours, like the real thing.

#define REMASTER_SKILL_EVERY 2      // RemasterTrack calls (about 1 second)
#define REMASTER_XP_PER_POINT 100
#define REMASTER_GRIND_MAX_STEP 5   // bigger jumps per second are not training
#define RM_XP_RATE_BASE 0.15        // share of training XP that counts at level 0...
#define RM_XP_RATE_PER_LEVEL 0.0086 // ...growing to the whole of it at 99

// Share of a training gain's XP that counts at this level. Only the skills that gain
// a little on every blow (chopping, mining) are paced this way: a craft, a cooked
// meal, a built wall is one item, worth its RuneScape XP whatever the level, and
// those skills are limited by materials, not time. Fishing and combat award their
// XP directly (Fishing.dm, CombatSkills.dm) and are not scaled either.
var/list/rm_xp_by_blow = list("WoodCutting", "Mineing")
proc/RemasterXPRate(id, level)
	if(!(id in rm_xp_by_blow)) return 1
	return min(1, RM_XP_RATE_BASE + RM_XP_RATE_PER_LEVEL * max(1, level))

// RuneScape XP table: total XP needed to reach each level 1-120 (the official values,
// written out: DM's 32-bit numbers drift when the formula is summed this high).
var/list/remaster_rs_xp = list(
	0, 83, 174, 276, 388, 512, 650, 801, 969, 1154,
	1358, 1584, 1833, 2107, 2411, 2746, 3115, 3523, 3973, 4470,
	5018, 5624, 6291, 7028, 7842, 8740, 9730, 10824, 12031, 13363,
	14833, 16456, 18247, 20224, 22406, 24815, 27473, 30408, 33648, 37224,
	41171, 45529, 50339, 55649, 61512, 67983, 75127, 83014, 91721, 101333,
	111945, 123660, 136594, 150872, 166636, 184040, 203254, 224466, 247886, 273742,
	302288, 333804, 368599, 407015, 449428, 496254, 547953, 605032, 668051, 737627,
	814445, 899257, 992895, 1096278, 1210421, 1336443, 1475581, 1629200, 1798808, 1986068,
	2192818, 2421087, 2673114, 2951373, 3258594, 3597792, 3972294, 4385776, 4842295, 5346332,
	5902831, 6517253, 7195629, 7944614, 8771558, 9684577, 10692629, 11805606, 13034431, 14391160,
	15889109, 17542976, 19368992, 21385073, 23611006, 26068632, 28782069, 31777943, 35085654, 38737661,
	42769801, 47221641, 52136869, 57563718, 63555443, 70170840, 77474828, 85539082, 94442737, 104273167)
proc/RemasterRSXP(level)
	level = max(1, min(length(remaster_rs_xp), round(level)))
	return remaster_rs_xp[level]

// XP for a skill value, including progress toward the next level.
proc/RemasterSkillXP(value)
	var/level = RemasterSkillLevel(value)
	var/frac = value >= 1 ? value - round(value) : 0
	return round(RemasterRSXP(level) + frac * (RemasterRSXP(level + 1) - RemasterRSXP(level)), 1)
#define REMASTER_XP_DROP_KEEP 30    // deciseconds a drop stays on screen

// id (the var is "[id]Skill"), label, group
var/list/remaster_skill_defs
proc/RemasterSkillDefs()
	if(!remaster_skill_defs) remaster_skill_defs = RemasterSkillDefList()
	return remaster_skill_defs
proc/RemasterSkillDefList()
	return list(
		list("WoodCutting", "Woodcutting", "Gathering"), list("Mineing", "Mining", "Gathering"),
		list("Fishing", "Fishing", "Gathering"), list("Butchery", "Butchery", "Gathering"),
		list("WoodCrafting", "Wood crafting", "Artisan"), list("MetalCrafting", "Metal crafting", "Artisan"),
		list("StoneCrafting", "Stone crafting", "Artisan"), list("BoneCrafting", "Bone crafting", "Artisan"),
		list("LeatherCrafting", "Leather crafting", "Artisan"), list("JewlCrafting", "Jewel crafting", "Artisan"),
		list("Cooking", "Cooking", "Artisan"), list("Potion", "Potions", "Artisan"), list("Poison", "Poison", "Artisan"),
		list("Building", "Building", "Support"), list("Sneaking", "Sneaking", "Support"), list("LockPicking", "Lock picking", "Support"),
		list("Sword", "Sword", "Sub"), list("Axe", "Axe", "Sub"), list("Mace", "Mace", "Sub"),
		list("Spear", "Spear", "Sub"), list("Dagger", "Dagger", "Sub"), list("Bow", "Bow", "Sub"),
		list("UnArmed", "Unarmed", "Sub"), list("Claw", "Claws", "Sub"), list("Shield", "Shield", "Sub"),
		list("Armour", "Armour", "Sub"),
		// RuneScape combat skills over the weapon sub-skills above (CombatSkills.dm)
		list("Attack", "Attack", "Combat"), list("Strength", "Strength", "Combat"), list("Defence", "Defence", "Combat"),
		list("Ranged", "Ranged", "Combat"), list("Magic", "Magic", "Combat"), list("Throwing", "Throwing", "Sub"))

proc/RemasterSkillLevel(value)
	return max(1, round(value))

mob/Monsters/var/tmp/list/remaster_skill_seen
Player/var/tmp
	remaster_skill_clock = 0
	list/remaster_xp_drops          // recent drops for the HUD

mob/Monsters/proc/RemasterSkillValue(id)
	var/name = "[id]Skill"
	if(!(name in vars)) return null
	var/v = vars[name]
	return isnum(v) ? v : 0

// All skills in RemasterSkillDefs() order, read directly (looking vars up by
// name for every unit every second was the slowest part of the HUD tick).
mob/Monsters/proc/RemasterSkillValues()
	return list(WoodCuttingSkill, MineingSkill, FishingSkill, ButcherySkill, WoodCraftingSkill, MetalCraftingSkill, StoneCraftingSkill, BoneCraftingSkill, LeatherCraftingSkill, JewlCraftingSkill, CookingSkill, PotionSkill, PoisonSkill, BuildingSkill, SneakingSkill, LockPickingSkill, SwordSkill, AxeSkill, MaceSkill, SpearSkill, DaggerSkill, BowSkill, UnArmedSkill, ClawSkill, ShieldSkill, ArmourSkill, AttackSkill, StrengthSkill, DefenceSkill, RangedSkill, MagicSkill, ThrowingSkill)

// RuneScape skills: every unit keeps real experience per skill (saved). The game's
// own skill gains (0.1 a swing of the axe, 0.5 a craft, 2 a cooked meal...) are turned
// into a fixed amount of XP per action, and the level comes from RuneScape's XP table:
// level 2 at 83 XP, 50 at 101,333, 92 at 6,517,253 (half of 99), 99 at 13,034,431.
// Levels go on past 99 to 120 (RuneScape 3's elite skills), for content gated at 100.
// Big one-off changes (crowning +25, inheritance) keep their level.
#define RM_SKILL_MAX_LEVEL 120
#define RM_SKILL_MAX_XP 200000000

mob/Monsters/var/list/remaster_xp          // saved: skill id -> experience

// XP per point of the game's own gain, per skill (so an action is worth about what it
// is in RuneScape: 4 XP a swing, 15-30 a craft, 30 a cooked meal, ~4 a combat hit).
var/list/rm_xp_per_point = list("WoodCutting"=40, "Mineing"=40, "Fishing"=33, "Butchery"=40, "Cooking"=15,
	"Building"=25, "Sneaking"=60, "LockPicking"=60, "Armour"=80, "Shield"=80,
	"Sword"=100, "Axe"=100, "Mace"=100, "Spear"=100, "Dagger"=100, "Bow"=100, "UnArmed"=100, "Claw"=100)
proc/RemasterXPPerPoint(id)
	return rm_xp_per_point[id] || 30

// Skill value (level + progress to the next) for an amount of XP.
proc/RemasterSkillFromXP(xp)
	xp = clamp(xp, 0, RM_SKILL_MAX_XP)
	var/lo = 1
	var/hi = RM_SKILL_MAX_LEVEL
	while(lo < hi)
		var/mid = round((lo + hi + 1) / 2)
		if(RemasterRSXP(mid) <= xp) lo = mid
		else hi = mid - 1
	if(lo >= RM_SKILL_MAX_LEVEL) return RM_SKILL_MAX_LEVEL
	var/a = RemasterRSXP(lo)
	var/b = RemasterRSXP(lo + 1)
	return lo + (b > a ? (xp - a) / (b - a) : 0)

mob/Monsters/proc/RemasterXPOf(id)
	if(!remaster_xp) remaster_xp = list()
	if(isnull(remaster_xp[id])) remaster_xp[id] = RemasterSkillXP(max(1, RemasterSkillValue(id) || 1))
	return remaster_xp[id]

// Award XP directly (fishing catches, and the tick below). Returns the XP given.
mob/Monsters/proc/RemasterAddXP(id, amount, quiet = 0)
	if(amount <= 0) return 0
	var/name = "[id]Skill"
	if(!(name in vars)) return 0
	var/before = vars[name]
	var/xp = min(RM_SKILL_MAX_XP, RemasterXPOf(id) + amount)
	remaster_xp[id] = xp
	var/now = RemasterHeld(id, RemasterSkillFromXP(xp))   // a weapon skill is held at Attack, its XP kept (CombatSkills.dm)
	vars[name] = now
	// keep the tick from counting this again
	var/k = 0
	for(var/list/D in RemasterSkillDefs())
		k++
		if(D[1] == id && remaster_skill_seen && length(remaster_skill_seen) >= k) remaster_skill_seen[k] = now
	if(!quiet && istype(Owner, /Player)) Owner:RemasterSkillDrop(src, id, round(amount), RemasterSkillLevel(before), RemasterSkillLevel(now))
	return amount

Player/var/tmp/list/remaster_level_said     // "unitref|skill" -> the last level announced

Player/proc/RemasterSkillDrop(mob/Monsters/M, id, xp, old_level, new_level)
	var/label = id
	for(var/list/D in RemasterSkillDefs()) if(D[1] == id) label = D[2]
	if(!remaster_xp_drops) remaster_xp_drops = list()
	if(xp > 0) remaster_xp_drops += list(list("unit"=RemasterUIRef(M), "name"="[M.name]", "skill"=label, "xp"=xp, "at"=world.time))
	// A level is announced once. The skill var the "before" level comes from can be lowered again between two
	// drops (the combat skills are averaged from their sub-skills each tick), which used to repeat "Attack level 7!"
	// on every blow; the last level said for this unit and skill is remembered instead.
	if(!remaster_level_said) remaster_level_said = list()
	var/sk = "[RemasterUIRef(M)]|[id]"
	var/said = remaster_level_said[sk]
	if(new_level > old_level && (isnull(said) || new_level > said))
		remaster_level_said[sk] = new_level
		remaster_xp_drops += list(list("unit"=RemasterUIRef(M), "name"="[M.name]", "skill"=label, "level"=new_level, "at"=world.time))
		RemasterNotice("[M.name]: [label] level [new_level]!")
		RemasterLog("[M.name] reached [label] level [new_level]!", "skill", M)
	while(length(remaster_xp_drops) > 12) remaster_xp_drops.Cut(1, 2)

Player/proc/RemasterSkillTick(spread = 0)
	remaster_skill_clock++
	if(remaster_skill_clock % REMASTER_SKILL_EVERY) return
	var/list/defs = RemasterSkillDefs()
	if(!remaster_xp_drops) remaster_xp_drops = list()
	for(var/list/D in remaster_xp_drops.Copy()) if(world.time - D["at"] > REMASTER_XP_DROP_KEEP) remaster_xp_drops -= list(D)
	for(var/mob/Monsters/M in UnitList)
		if(M.Owner != src || M.Wagon || M.Egg || M.Critter) continue
		RmSkillUnit(M, defs)
		if(spread) RmTrackPause()   // between units: the pass goes on next tick once this tick's share is used (Spread.dm)

// Skill panel data for one unit: RuneScape-style tiles plus the total level.
mob/Monsters/proc/RemasterSkillPanel()
	var/list/tiles = list()
	var/total = 0
	var/list/defs = RemasterSkillDefs()
	var/list/values = RemasterSkillValues()
	var/cap = RemasterWeaponCap()           // weapon skills are held at Attack (CombatSkills.dm), bows and throws at Ranged
	var/capR = RemasterWeaponCap("Bow")
	for(var/k = 1, k <= length(defs), k++)
		var/list/S = defs[k]
		var/v = values[k]
		if(!isnum(v)) v = 0
		var/cp = (S[1] == "Bow" || S[1] == "Throwing") ? capR : cap
		var/held = !isnull(cp) && (S[1] in rm_weapon_skill_ids)
		if(held) v = min(v, cp)             // also before the skill tick has seen a loaded unit
		var/level = RemasterSkillLevel(v)
		total += level
		var/progress = v >= 1 ? round((v - round(v)) * 100) : round(max(0, v) * 100)
		var/list/tile = list("id"=S[1], "label"=S[2], "group"=S[3], "parent"=rm_combat_parents[S[1]], "level"=level, "progress"=progress, "xp"=RemasterSkillXP(v), "next"=RemasterRSXP(level + 1))
		if(held && level >= RemasterSkillLevel(AttackSkill))
			tile["cap"] = RemasterSkillLevel(AttackSkill)   // at its Attack level: only Attack raises it
			var/bank = remaster_xp ? remaster_xp[S[1]] : 0
			tile["banked"] = isnum(bank) ? max(0, round(bank - tile["xp"])) : 0   // XP kept for when Attack levels
		tiles += list(tile)
	return list("tiles"=tiles, "total"=total, "style"=remaster_combat_style)

Player/proc/RemasterXPDropData()
	var/list/out = list()
	if(remaster_xp_drops) for(var/list/D in remaster_xp_drops)
		var/list/C = D.Copy()
		C["id"] = "[D["at"]]-[D["unit"]]-[D["skill"]]-[D["xp"]][D["level"]]"
		C -= "at"
		out += list(C)
	return out

// One unit of the skill pass (RemasterSkillTick): its gains become XP, its losses follow, as the pass did in one go
// (server cost, 2026-10-24: 103 ms with 200 units on a loaded Mac, now spread over ticks).
// Read once (the owner, 10-31: "does things multiple itmes"): everything the pass reads of a unit is its own vars (its
// skills, combat seeding, the hold's mark), so a unit whose state counter (rm_ver_state) stands since the pass last read
// it would read the same and do nothing; 1,600 reads a second with 2,000 units were nearly all of standing or walking units.
mob/Monsters/var/tmp/rm_skill_v = -1   // that counter just after the pass last read it (a quiet name, Native.dm)

Player/proc/RmSkillUnit(mob/Monsters/M, list/defs)
	var/first = !M.remaster_skill_seen
	if(!first && M.rm_skill_v == rm_ver_state(M))
		if(rm_once_verify) RmOnceCheck("skills", RmSkillWouldDo(M), M)
		return
	var/list/values = M.RemasterSkillValues()
	if(first)
		M.RemasterSeedCombatSkills()
		for(var/list/S in defs) M.RemasterXPOf(S[1])     // XP from the level they have
		M.RemasterHoldWeaponSkills(1)                      // a weapon skill above Attack (an old save) is held there, its XP kept
		M.remaster_skill_seen = M.RemasterSkillValues()
		M.rm_skill_seeded = M.remaster_combat_seeded
		M.rm_skill_v = rm_ver_state(M)
		return
	var/list/seen = M.remaster_skill_seen
	var/changed = 0
	for(var/k = 1, k <= length(defs), k++)
		var/now = values[k]
		var/before = seen[k]
		if(now != before) changed = 1
		if(!isnum(now) || !isnum(before) || now == before) continue
		var/list/S = defs[k]
		var/id = S[1]
		if(now < before)
			// a loss: experience follows the value down
			M.RemasterXPOf(id)
			M.remaster_xp[id] = RemasterSkillXP(max(1, now))
			continue
		if(now - before <= REMASTER_GRIND_MAX_STEP)
			// training: the game's gain becomes RuneScape-sized XP, less of it at low levels
			M.vars["[id]Skill"] = before
			M.RemasterAddXP(id, (now - before) * RemasterXPPerPoint(id) * RemasterXPRate(id, RemasterSkillLevel(before)))
		else
			// a one-off boost keeps its level (a weapon skill's stops at Attack: CombatSkills.dm)
			var/old_level = RemasterSkillLevel(before)
			M.RemasterXPOf(id)
			M.remaster_xp[id] = max(M.remaster_xp[id], RemasterSkillXP(M.RemasterHeld(id, now)))
			M.vars["[id]Skill"] = M.RemasterHeld(id, RemasterSkillFromXP(M.remaster_xp[id]))
			RemasterSkillDrop(M, id, 0, old_level, RemasterSkillLevel(M.vars["[id]Skill"]))
	// nothing changed since the last pass, which left no weapon skill above the cap and saw this Attack level: the hold
	// would change nothing and the values would read the same (server cost, 2026-10-24: only units that trained cost)
	// (rm_held_at is "Attack level|Ranged level", as RemasterHoldWeaponSkills writes it: compared as a number since the hold
	// took Ranged too, it never matched, and every unit ran the whole hold every second; server upgrades, 10-30)
	if(!changed && M.remaster_combat_seeded == M.rm_skill_seeded && M.rm_held_at == "[RemasterSkillLevel(M.AttackSkill)]|[RemasterSkillLevel(M.RangedSkill)]")
		M.rm_skill_v = rm_ver_state(M)
		return
	M.RemasterHoldWeaponSkills()                           // none above Attack; held ones rise when it does
	M.remaster_skill_seen = M.RemasterSkillValues()
	M.rm_skill_seeded = M.remaster_combat_seeded
	M.rm_skill_v = rm_ver_state(M)

// RM_ONCE_VERIFY: whether the pass would have done anything for a unit it skipped (a value moved since it was seen, a
// change in its combat seeding, or the hold's mark behind its Attack and Ranged levels)
Player/proc/RmSkillWouldDo(mob/Monsters/M)
	var/list/values = M.RemasterSkillValues()
	var/list/seen = M.remaster_skill_seen
	for(var/k = 1, k <= length(values), k++) if(values[k] != seen[k]) return 1
	if(M.remaster_combat_seeded != M.rm_skill_seeded) return 1
	if(M.remaster_combat_seeded && M.rm_held_at != "[RemasterSkillLevel(M.AttackSkill)]|[RemasterSkillLevel(M.RangedSkill)]") return 1
	return 0

mob/Monsters/var/tmp/rm_skill_seeded   // remaster_combat_seeded when the skill pass last read this unit in full
