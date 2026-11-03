// Raids (Remastered). The original game sends one NPC army a season to a random
// spot on the 1000x1000 map, so it almost never meets anyone. Remastered keeps
// that army and adds raids aimed at each player's settlement:
//  - a season change (about every 17 minutes) sends one raid per settlement;
//    Brutal sends a second one halfway through the season;
//  - the size follows the settlement (living units) and the difficulty;
//  - early days bring kobolds, goblins and ratmen, later ones skeletons, orcs
//    and crusaders;
//  - raiders gather 35-45 tiles out, the player is warned with the direction,
//    and they march on the stockpile (or the middle of the village), fighting
//    whatever they meet, using the NPCs' own "home" walking. After 10 minutes the
//    survivors give up and roam where they are.
// Difficulty is a world setting (saved with the world): Peaceful turns off every
// army, including the original random one.

#define REMASTER_RAID_GIVEUP 6000      // ticks before surviving raiders stop marching
#define REMASTER_RAID_GRACE_DAYS 2     // Normal: no raids before the settlement's third morning

var/remaster_difficulty = "normal"     // "peaceful", "normal", "brutal"
var/list/remaster_raiders = list()     // raider -> list(target turf, started, last x, last y, still)
var/remaster_raid_loop = 0
var/remaster_season_at = 0             // world.time of the last season change

proc/RemasterDifficultyLabel(d = remaster_difficulty)
	switch(d)
		if("peaceful") return "Peaceful"
		if("brutal") return "Brutal"
	return "Normal"

// Called from Seasons() (World.dm). Returns 1 if the original random army may come.
proc/RemasterSeasonChanged()
	remaster_season_at = world.time
	if(remaster_difficulty == "peaceful") return 0
	// The season timer also fires once as the world starts: no raid at boot.
	if(world.time > 3000)
		spawn(50) RemasterSeasonRaids()
		if(remaster_difficulty == "brutal") spawn(5000) RemasterSeasonRaids()
	if(!RmUnitRoom()) return 0   // the world is crowded: no army this season (UnitLimit.dm; each raid waits there too)
	RmUnitSoon()                 // the army comes: counted at the next look
	return 1

proc/RemasterSeasonRaids()
	if(remaster_difficulty == "peaceful") return
	for(var/client/C)
		var/Player/P = C.mob
		if(istype(P)) P.RemasterRaid()

// The settlement's heart: its stockpile, or the middle of its units on the surface.
Player/proc/RemasterRaidTarget()
	var/turf/S = RemasterStockpile()
	if(S && S.z == 1) return S
	var/sx = 0
	var/sy = 0
	var/n = 0
	for(var/mob/Monsters/M in UnitList)
		if(M.Owner != src || M.HP <= 0 || !isturf(M.loc) || M.z != 1) continue
		sx += M.x
		sy += M.y
		n++
	if(!n) return null
	return locate(round(sx / n), round(sy / n), 1)

// Open ground at 35-45 tiles in a random direction, clear for a few tiles around.
proc/RemasterRaidMuster(turf/T)
	for(var/tries = 1, tries <= 40, tries++)
		var/a = rand(0, 359)
		var/d = rand(35, 45)
		var/turf/G = locate(clamp(round(T.x + cos(a) * d), 2, world.maxx - 1), clamp(round(T.y + sin(a) * d), 2, world.maxy - 1), T.z)
		if(!G || G.density) continue
		var/open = 1
		for(var/turf/N in range(1, G)) if(N.density)
			open = 0
			break
		if(!open) continue
		var/near = 0
		for(var/mob/Monsters/M in range(8, G)) if(ismob(M.Owner))
			near = 1
			break
		if(near) continue
		return G
	return null

proc/RemasterRaidDirection(turf/origin, turf/home)
	var/dx = origin.x - home.x
	var/dy = origin.y - home.y
	var/ns = dy > abs(dx) / 2 ? "north" : dy < -abs(dx) / 2 ? "south" : ""
	var/ew = dx > abs(dy) / 2 ? "east" : dx < -abs(dy) / 2 ? "west" : ""
	return ns && ew ? "[ns]-[ew]" : ns || ew || "nearby"

Player/proc/RemasterRaid()
	var/living = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0) living++
	if(!living) return 0
	if(remaster_difficulty == "normal" && remaster_days < REMASTER_RAID_GRACE_DAYS) return 0
	var/turf/T = RemasterRaidTarget()
	if(!T) return 0
	var/turf/G = RemasterRaidMuster(T)
	if(!G) return 0
	var/brutal = remaster_difficulty == "brutal"
	var/count = brutal ? min(45, 8 + living * 3) : min(25, 3 + round(living * 1.5))
	// A young settlement (Normal): smaller bands until it is a Village or has beaten two raids
	var/young = !brutal && (remaster_rank < 3 && remaster_raids_won < 2)
	if(young) count = min(count, 1 + remaster_rank + round(living / 2))
	var/strength = brutal ? 1 : RemasterRaidStrength()
	var/late = remaster_days >= (brutal ? 4 : 8)
	var/list/kinds = late ? list("Undead", "Orcs", "Crusaders", "Goblins") : list("Kobolds", "Goblins", "Ratmen")
	var/kind = pick(kinds)
	var/soldier
	var/leader
	switch(kind)
		if("Kobolds")
			soldier = /mob/Monsters/Kobold/NPC/Scout
			leader = /mob/Monsters/Kobold/NPC/Chieftain
		if("Goblins")
			soldier = /mob/Monsters/Goblin/NPC/Scout
			leader = /mob/Monsters/Goblin/NPC/Commander
		if("Ratmen")
			soldier = /mob/Monsters/Ratman/NPC/Scout
			leader = /mob/Monsters/Ratman/NPC/King
		if("Undead")
			soldier = /mob/Monsters/Skeleton/NPC/Warrior
			leader = /mob/Monsters/Skeleton/NPC/Lord
		if("Orcs")
			soldier = /mob/Monsters/Orc/NPCOrc/Warrior
			leader = /mob/Monsters/Orc/NPCOrc/Warlord
		if("Crusaders")
			soldier = /mob/Monsters/Human/NPC/Paladin
			leader = /mob/Monsters/Human/NPC/Dragoon
	var/list/band = MakeMany(soldier, count, G)
	if(!islist(band)) band = list()
	if(count >= 10 && leader) band += new leader(G)
	for(var/mob/Monsters/R in band)
		R.RmSeedNPC()   // its role's combat levels first, so a weaker band's are scaled down too (NPCLevels.dm)
		if(strength < 1) R.RemasterWeaken(strength)
		R.HomeLoc = T
		R.destination = T
		remaster_raiders[R] = list(T, world.time, R.x, R.y, 0, src)   // 6th: the realm raided (its "raid beaten", Progress.dm)
	if(!remaster_raid_loop)
		remaster_raid_loop = 1
		spawn(0) RemasterRaidLoop()
	var/dir = RemasterRaidDirection(G, T)
	var/text = "Raid! [length(band) == 1 ? "A lone [list("Undead"="Undead", "Orcs"="Orc", "Crusaders"="Crusader", "Goblins"="Goblin", "Kobolds"="Kobold", "Ratmen"="Ratman")[kind] || kind] is" : "[length(band)] [kind] are"] coming from the [dir], about [get_dist(G, T)] tiles out.[strength < 0.7 ? " A ragged band: they look poorly trained." : ""]"
	RemasterNotice(text)
	RemasterLog(text, "fight", G)
	src << "<b><font color=#ff6a50>[text]</font></b>"
	return 1

// Every 5 seconds: raiders not busy fighting keep marching on their target;
// one stuck against a wall side-steps. After REMASTER_RAID_GIVEUP they stop.
proc/RemasterRaidLoop()
	remaster_raid_loop = 1
	while(length(remaster_raiders))
		sleep(50)
		for(var/mob/Monsters/R in remaster_raiders.Copy())
			var/list/D = remaster_raiders[R]
			if(!R || R.HP <= 0 || !isturf(R.loc))
				remaster_raiders -= R
				continue
			if(world.time - D[2] > REMASTER_RAID_GIVEUP)
				R.HomeLoc = R.loc
				if(R.destination == D[1]) R.destination = null
				remaster_raiders -= R
				continue
			if(ismob(R.destination)) continue   // fighting someone
			var/turf/T = D[1]
			R.HomeLoc = T
			R.destination = T
			if(R.x == D[3] && R.y == D[4])
				D[5]++
				if(D[5] >= 2)
					step_rand(R)
					D[5] = 0
			else D[5] = 0
			D[3] = R.x
			D[4] = R.y
		// A deleted raider leaves a null key behind, which a typed loop never visits.
		while(null in remaster_raiders) remaster_raiders -= null
	remaster_raid_loop = 0

// Settings: the world's difficulty. The page shows it, and the time to the next season.
Player/proc/RemasterDifficultyCommand(value)
	if(!(value in list("peaceful", "normal", "brutal"))) return 0
	if(RmPublicWorld() && RmModRank(RmModLevel()) < 2)   // a public server: the owner and Admins set it (Moderation.dm)
		RemasterNotice("Only an Admin sets this world's difficulty.")
		return 0
	if(value == remaster_difficulty) return 1
	remaster_difficulty = value
	world << "<b>Difficulty is now [RemasterDifficultyLabel()].</b>"
	RemasterNotice("Difficulty: [RemasterDifficultyLabel()]. " + (value == "peaceful" ? "No armies come." : value == "brutal" ? "Bigger raids, twice a season, from the first day." : "One raid a season on your settlement, from the third morning."))
	return 1

proc/RemasterRaidData()
	var/next = remaster_season_at ? max(0, round((remaster_season_at + 10000 - world.time) / 600)) : null
	var/n = 0
	for(var/mob/Monsters/R in remaster_raiders) if(R && R.HP > 0) n++
	return list("difficulty"=remaster_difficulty, "nextSeasonMin"=next, "raiders"=n)

// How strong raiders are against this settlement (Normal): 35% for a brand-new camp,
// growing with rank, raids beaten and the people's best combat skills, to full strength.
Player/proc/RemasterRaidStrength()
	var/best = 0
	var/n = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0)
		best += max(M.SwordSkill, M.AxeSkill, M.MaceSkill, M.SpearSkill, M.DaggerSkill, M.BowSkill, M.UnArmedSkill)
		n++
	var/avg = n ? best / n : 0
	return clamp(0.35 + 0.15 * (remaster_rank - 1) + 0.1 * remaster_raids_won + avg / 60, 0.35, 1)

// Raiders of a weaker band: skills and armour scaled down.
mob/Monsters/proc/RemasterWeaken(f)
	for(var/v in vars)
		if(length(v) <= 5 || copytext(v, length(v) - 4) != "Skill") continue
		if(isnum(vars[v])) vars[v] = max(1, round(vars[v] * f, 0.1))
	Defence = round(Defence * f)
	WeaponDamageMin = max(1, round(WeaponDamageMin * f))
	WeaponDamageMax = max(WeaponDamageMin, round(WeaponDamageMax * f))
