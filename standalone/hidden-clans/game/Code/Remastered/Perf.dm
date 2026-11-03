// Server tick time with big selections (overnight QA, tools/stress_timing.py). The HUD model is built
// twice a second for each player, inside one server tick, and it carries the skill panel and stat sheet
// of every selected unit: with a whole large army selected (Ctrl+A on 200 people) that alone took
// ~75 ms of the 100 ms tick, a hitch every half second. With one unit selected (its card open) the
// stat sheet stays fresh on every update; in a bigger selection, where it feeds the Units list and the band
// card, each unit's copy is kept for up to REMASTER_PANEL_KEEP ticks, staggered at random so the
// rebuilds spread over the updates instead of all falling on the same one. The skill panel is kept by
// what it shows instead (below).

#define REMASTER_PANEL_KEEP 20

mob/Monsters/var/tmp
	list/remaster_skill_panel_kept
	remaster_skill_panel_at = -1000
	list/remaster_stat_sheet_kept
	remaster_stat_sheet_at = -1000

mob/Monsters/proc/RemasterPanelsShared()
	var/Player/P = Owner
	return istype(P) && length(P.Selected) > 1

// The skill panel (the costly part, ~0.15 ms a unit) is built again only when what it shows can have changed: the
// skill values, Attack (the weapon skills' cap), whether combat is seeded, the combat style and the XP banked at the
// cap are all Skills.dm RemasterSkillPanel reads (server cost, 2026-10-24). So a kept panel is the very one it would
// build, never stale, for one unit selected or many; the key takes ~0.03 ms.
mob/Monsters/var/tmp/remaster_skill_panel_key
proc/RmNumKey(v)
	return isnum(v) ? num2text(v, 12) : "[v]"
mob/Monsters/proc/RemasterSkillPanelKey()
	var/list/k = list()
	for(var/v in RemasterSkillValues()) k += RmNumKey(v)
	. = "[jointext(k, ",")]|[RmNumKey(AttackSkill)]|[remaster_combat_seeded]|[remaster_combat_style]"
	if(remaster_xp) for(var/id in rm_weapon_skill_ids) . += ",[RmNumKey(remaster_xp[id])]"

mob/Monsters/RemasterSkillPanel()
	var/key = RemasterSkillPanelKey()
	if(remaster_skill_panel_kept && key == remaster_skill_panel_key) return remaster_skill_panel_kept
	. = ..()
	remaster_skill_panel_kept = .
	remaster_skill_panel_key = key

mob/Monsters/RemasterStatSheet()
	if(remaster_stat_sheet_kept && RemasterPanelsShared() && world.time - remaster_stat_sheet_at < REMASTER_PANEL_KEEP)
		return remaster_stat_sheet_kept
	. = ..()
	remaster_stat_sheet_kept = .
	remaster_stat_sheet_at = world.time - rand(0, REMASTER_PANEL_KEEP / 2)
