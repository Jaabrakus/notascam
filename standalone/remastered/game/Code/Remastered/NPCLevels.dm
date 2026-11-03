// NPC combat levels by role (the user, 2026-10-26, via the coordinator: raiders and creatures nobody owns sat at Attack,
// Strength and Defence 1, so a recruit beat an Orc Scout 8 times in 8; levels from their old skills made scouts 25-40 and
// warriors and leaders 99, "raids and wondering scouts wiping out whole teams", so: "lets do our own what we think would be
// right"). An NPC (its name "{NPC ...}" or its type an NPC one) no player owns gets its role's levels the first time it
// strikes or is struck (melee or a shot), or as a raid musters it (Raids.dm: before a weak band is scaled down), with its
// race's offset, 1-99; its weapon skills are then held at Attack (CombatSkills.dm RemasterHoldWeaponSkills). The user's
// aims: a fresh 3-unit realm beats one lone scout together; three warriors wipe a fresh realm in the open but not one with
// level-15 units or walls; guards hold doors; bosses need a trained army. Animals and beasts (no role) stay as they are;
// player units are never touched; one already seeded keeps its levels, whoever owns it later.
var/rm_npc_levels_on = 1   // 0: NPCs stay at 1, as before
var/list/rm_npc_roles = list(   // Attack, Strength, Defence, Ranged
	"villager"=list(5, 5, 5, 1), "scout"=list(10, 10, 8, 10), "hunter"=list(12, 10, 8, 20), "warrior"=list(25, 25, 20, 10),
	"paladin"=list(30, 30, 30, 10),   // the Crusaders' raiders (Raids.dm): a warrior in plate, below a guard
	"guard"=list(35, 30, 45, 15), "commander"=list(50, 50, 40, 25), "boss"=list(75, 75, 65, 40))
var/list/rm_npc_role_words = list(   // in its name (the "{NPC ...}" part left out), first match wins
	"lich king"="boss", "warlord"="boss", "lord"="boss", "king"="boss", "noble"="boss",
	"commander"="commander", "chieftain"="commander", "cheiftain"="commander", "dragoon"="commander", "follower of skorn"="commander",
	"demon"="commander", "paladin"="paladin", "guard"="guard", "warrior"="warrior", "hunter"="hunter", "scout"="scout", "villager"="villager")
var/list/rm_npc_race_offsets = list("Orc"=list(0, 5, 0, 0), "Goblin"=list(5, 0, 0, 0), "Dwarf"=list(0, 0, 10, 0),
	"Lizardman"=list(0, 0, 0, 10), "Frogman"=list(0, 0, 0, 10), "Kobold"=list(-5, -5, -5, -5), "Ratman"=list(-5, -5, -5, -5))
mob/Monsters/var/tmp/rm_npc_checked = 0   // looked at once already (an animal: nothing to seed)

// Its role, or null: an NPC's rank from its name; one with none named (a plain "{NPC Orcs} Orc") is a scout.
mob/Monsters/proc/RmNPCRole()
	var/n = "[name]"
	if(!findtext(n, "{NPC") && !findtext("[type]", "/NPC")) return null
	var/i = findtext(n, "}")
	if(i) n = copytext(n, i + 1)
	n = lowertext(n)
	for(var/w in rm_npc_role_words) if(findtext(n, w)) return rm_npc_role_words[w]
	return "scout"

mob/Monsters/proc/RmSeedNPC()
	if(RmSeedDone()) return
	rm_npc_checked = 1
	var/role = RmNPCRole()
	if(!role) return
	remaster_combat_seeded = 1
	var/list/L = rm_npc_roles[role]
	var/list/off = rm_npc_race_offsets[Race] || list(0, 0, 0, 0)
	var/list/ids = list("Attack", "Strength", "Defence", "Ranged")
	for(var/k = 1, k <= 4, k++)
		var/v = clamp(L[k] + off[k], 1, 99)
		if(!remaster_xp) remaster_xp = list()
		remaster_xp[ids[k]] = RemasterRSXP(v)
		vars["[ids[k]]Skill"] = v
	RemasterHoldWeaponSkills(1)

// RmSeedNPC would do nothing now (the strike chain's Morale step reads it: Chains/Strike.dm).
mob/Monsters/proc/RmSeedDone()
	return remaster_combat_seeded || rm_npc_checked || !rm_npc_levels_on || istype(Owner, /Player)

// mob/RemasterStrike: this file's part is step RmChainStrike_NPCLevels in Code/Remastered/Chains/Strike.dm

mob/BowTarget(remaster_defensive_shot = 0, datum/remaster_bow_controller/controller = null)
	if(istype(src, /mob/Monsters) && !src:remaster_combat_seeded) src:RmSeedNPC()
	if(istype(Target, /mob/Monsters) && !Target:remaster_combat_seeded) Target:RmSeedNPC()
	return ..()
