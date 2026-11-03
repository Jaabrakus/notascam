// The old stats folded into the skills (the owner, 10-27: "Fold old stats into skills": old Strength -> the Strength
// skill, old Agility -> the Attack skill, old Intelligence -> the Magic skill; plan: planning/STAT_FOLD_PLAN_2026-10-27.md).
// For a player's unit every read of Strength, Agility or Intelligence reads that skill plus a bonus: what was added to
// the old stat after its own roll (a werewolf's +20, a vampire's +8, a crown, a tonic, surgery), the old stat less a base
// taken the first time it is read (saved with the unit). So the code that adds and takes back +20 works as before, and
// level-ups no longer add Strength and Agility to these units (Leveling.dm): their skills grow by use. NPCs, animals and
// great beasts keep their old stats: those are their only numbers, and raids are tuned on them (NPCLevels.dm).
var/rm_stats_folded = 1     // 0: the old stats, as before
#define RM_INT_CAP 15       // Intelligence where it scales odds and costs (captives, mind spells, building costs): today's top
mob/var/rm_stat_base_s      // the old stats at the fold: what is added above these is a bonus
mob/var/rm_stat_base_a
mob/var/rm_stat_base_i

mob/proc/RmFolds()
	return rm_stats_folded && istype(src, /mob/Monsters) && istype(src:Owner, /Player)

// Each read is on every blow (damage, dodge, block), so they read the skill fields directly (no name lookup).
mob/proc/RmStr()
	if(!rm_stats_folded || !istype(src, /mob/Monsters) || !istype(src:Owner, /Player)) return Strength
	if(isnull(rm_stat_base_s)) RmStatBase()
	return max(1, round(src:StrengthSkill)) + Strength - rm_stat_base_s

mob/proc/RmAgi()
	if(!rm_stats_folded || !istype(src, /mob/Monsters) || !istype(src:Owner, /Player)) return Agility
	if(isnull(rm_stat_base_s)) RmStatBase()
	return max(1, round(src:AttackSkill)) + Agility - rm_stat_base_a

mob/proc/RmInt()
	if(!RmFolds()) return Intelligence
	if(isnull(rm_stat_base_s)) RmStatBase()
	return max(1, round(src:MagicSkill)) + Intelligence - rm_stat_base_i

mob/proc/RmStatBase()
	rm_stat_base_s = Strength
	rm_stat_base_a = Agility
	rm_stat_base_i = Intelligence

// Intelligence where it scales odds and costs: a Magic 60 mage is not 60 Intelligence there.
mob/proc/RmIntC()
	return RmFolds() ? min(RmInt(), RM_INT_CAP) : Intelligence
