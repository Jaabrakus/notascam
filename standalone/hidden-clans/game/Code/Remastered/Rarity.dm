// A fair start and rare races.
// Everyone of the common races starts at skill level 1; the rare races (Dragon, Spider,
// Devourer, Svartalfar, Illithid) keep their own gifts. Rare races only appear in the
// race list when they are drawn: each has its own chance every time you choose a race,
// 4% plus 3% for every achievement (milestone) you have ever reached, in any game
// (up to 49% with all 15). The draw holds while you choose, so Cancel does not re-roll.
// Low skills are softened so the start is not a wall of failures: crafting succeeds
// 45% of the time at level 1 (the original 4% a level reaches 100% at 25; this reaches
// it at 19), and chopping and mining work as if at least level 12.

var/list/rm_rare_races = list("Dragon", "Spider", "Devourer", "Svartalfar", "Illithid")
#define RM_RARE_BASE 4
#define RM_RARE_PER 3
#define RM_RARE_HOLD 6000              // ticks a draw holds (one sitting at the race menu)
#define RM_RARE_NEWCOMER 10            // percent: a Dragon or a Spider offered as well (the owner, 11-01: "give them a chance to get a rare
                                       // race of dragon or spider", "1 in 10 players")

Player/var/tmp
	list/remaster_rare_drawn
	remaster_rare_drawn_at = -1#INF

// --- Achievements kept across games ------------------------------------------------
// The profile lives outside the world when the launcher says where (RM_PROFILE_DIR, mac-app/launch.zsh): one profile
// for every world on this Mac (the world list, 10-31). Unset (arena checks, older launchers): inside the world, as before.
var/rm_profile_dir
proc/RemasterProfilePath(ckey)
	if(isnull(rm_profile_dir))
		var/d = world.GetConfig("env", "RM_PROFILE_DIR")
		rm_profile_dir = (istext(d) && length(d)) ? d : ""
	return length(rm_profile_dir) ? "[rm_profile_dir]/remaster_profile_[ckey].sav" : "units/remaster_profile_[ckey].sav"

Player/proc/RemasterAchievementsEver()
	var/list/L
	if(ckey && fexists(RemasterProfilePath(ckey)))
		var/savefile/S = new(RemasterProfilePath(ckey))
		S["achievements"] >> L
	. = islist(L) ? L : list()
	if(remaster_achieved) for(var/id in remaster_achieved) if(!(id in .)) . += id

Player/proc/RemasterRecordAchievement(id)
	if(!ckey) return
	var/list/L = RemasterAchievementsEver()
	if(!(id in L)) L += id
	var/savefile/S = new(RemasterProfilePath(ckey))
	S["achievements"] << L

Player/proc/RemasterRareOdds()
	return min(RM_RARE_BASE + RM_RARE_PER * length(RemasterAchievementsEver()), 49)

// The rare races drawn for this sitting at the race menu.
Player/proc/RemasterRareDraw()
	if(remaster_rare_drawn && world.time - remaster_rare_drawn_at < RM_RARE_HOLD) return remaster_rare_drawn
	var/odds = RemasterRareOdds()
	remaster_rare_drawn = list()
	for(var/r in rm_rare_races) if(prob(odds)) remaster_rare_drawn += r
	if(prob(RM_RARE_NEWCOMER))   // 1 in 10: a Dragon or a Spider, whatever the achievements
		var/r = pick("Dragon", "Spider")
		if(!(r in remaster_rare_drawn)) remaster_rare_drawn += r
	remaster_rare_drawn_at = world.time
	var/n = length(RemasterAchievementsEver())
	if(length(remaster_rare_drawn)) src << "<b><font color=#f2d27a>A rare people answers your call: [jointext(remaster_rare_drawn, ", ")]! Look for the star in the list.</font></b>"
	// no line when none is drawn: at every new start it was noise about a rule a new player hasn't met (playtest);
	// the Guide explains the odds
	return remaster_rare_drawn

// --- A fair start --------------------------------------------------------------------
// Every skill at level 1 (any number var ending in "Skill").
mob/Monsters/proc/RemasterStartSkills()
	for(var/v in vars)
		if(length(v) <= 5 || copytext(v, length(v) - 4) != "Skill") continue
		if(isnum(vars[v])) vars[v] = 1

// Craft success in percent: 45 at level 1, +3 a level, certain from 19. per: the
// original's percent per level (most recipes 4), kept for higher levels.
proc/RemasterCraftOdds(skill, per = 4)
	return min(100, max(skill * per, 42 + skill * 3))

// Chopping and mining power: at least as strong as level 12.
proc/RemasterWorkSkill(skill)
	return max(skill, 12)
