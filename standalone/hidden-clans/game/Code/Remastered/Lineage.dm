// Families, houses and connections (planning/FAMILY_HOUSES.md, phase 1-3).
// Saved links are text ids and copied names only. Saving a reference from one
// unit to another would duplicate units in the player savefile, which is why
// the original breeding code keeps its parent links tmp.
// Defaults: children join the father's house (the mother's when the father is
// unknown); parents of a child are remembered as partners; captured units keep
// their own house.

var/remaster_uid_serial = 0

mob/Monsters/var
	remaster_uid
	remaster_house
	remaster_father
	remaster_mother
	list/remaster_parent_names
	list/remaster_partners
	remaster_born
	remaster_generation = 1
	// Eggs carry their parents' ids so a save during incubation keeps them.
	list/remaster_carried_parents

Player/var
	list/remaster_houses
	list/remaster_ledger
	remaster_main_house
Player/var/tmp
	remaster_lineage_focus
	remaster_village_view = "roster"

// Ids carry the real time as "day-tenths" (RemasterNow, Away.dm). They used world.realtime, which this
// engine breaks (0-9), and the serial restarts at 0 every boot, so ids could repeat after restarts.
// Ids already saved keep their old form (three parts; new ones have four), so the two never match.
proc/RemasterIdStamp()
	var/list/N = RemasterNow()
	return "[N[1]]-[num2text(N[2], 7)]"

proc/RemasterNewUID()
	remaster_uid_serial++
	return "u[RemasterIdStamp()]-[remaster_uid_serial]-[rand(1000, 9999)]"

// A house id no house in the list has (a house founded with a repeated id replaced the older one).
proc/RemasterNewHouseID(list/houses)
	var/id
	do
		remaster_uid_serial++
		id = "h[RemasterIdStamp()]-[remaster_uid_serial]-[rand(1000, 9999)]"
	while(houses && (id in houses))
	return id

proc/RemasterLineageDate()
	return "[Date] - [Ages]"

var/list/remaster_house_names = list(
	"Orc" = list("Bloodtusk", "Ironjaw", "Skullsplit", "Gorefang", "Ashmaw", "Blackhide"),
	"Human" = list("Ashford", "Blackwood", "Hartwell", "Greymoor", "Thornbury", "Westmarch"),
	"Dwarf" = list("Stonebeard", "Deepforge", "Ironhelm", "Coppervein", "Granitefist"),
	"Elf" = list("Silverleaf", "Moonbrook", "Starwhisper", "Dawnbough", "Ashenvale"),
	"Goblin" = list("Mudfang", "Snaggletooth", "Gutrot", "Sneakfoot", "Rustgrin"),
	"Lizardman" = list("Scalecrest", "Mirefang", "Sunscale", "Coldblood", "Reedtail"),
	"Kobold" = list("Tunnelclaw", "Sparkeye", "Dirtscale", "Pebblejaw"),
	"Ratman" = list("Gnawtail", "Sewerkin", "Plaguewhisker", "Scurry"))
var/list/remaster_house_colors = list("#8b2f2f", "#2f5b8b", "#2f7a46", "#7a5a1f", "#5b2f7a", "#2f7a7a", "#8b5a2f", "#55606a")

Player/proc/RemasterFoundHouse(race, founder_uid)
	if(!remaster_houses) remaster_houses = list()
	var/list/pool = remaster_house_names[race]
	if(!pool) pool = remaster_house_names["Human"]
	var/name = pick(pool)
	for(var/id in remaster_houses)
		var/list/H = remaster_houses[id]
		if(H["name"] == name) name = "[name] [length(remaster_houses) + 1]"
	var/id = RemasterNewHouseID(remaster_houses)
	remaster_houses[id] = list("name"=name, "founder"=founder_uid, "founded"=RemasterLineageDate(), "color"=pick(remaster_house_colors), "race"=race)
	return id

Player/proc/RemasterMainHouse(mob/Monsters/founder)
	if(remaster_main_house && remaster_houses && remaster_houses[remaster_main_house]) return remaster_main_house
	remaster_main_house = RemasterFoundHouse(founder ? founder.Race : "Human", founder ? founder.remaster_uid : null)
	return remaster_main_house

// Founders: units with no lineage yet (new armies, old saves) join the
// player's main house as generation 1 with unknown parents.
mob/Monsters/proc/RemasterLineageEnsure(Player/P)
	if(!remaster_uid) remaster_uid = RemasterNewUID()
	if(!remaster_house && istype(P)) remaster_house = P.RemasterMainHouse(src)
	if(!remaster_generation) remaster_generation = 1

mob/Monsters/proc/RemasterLineageOwner()
	return istype(Owner, /Player) ? Owner : null

// Called by Breeding() for eggs, before the parents' tmp links can be lost.
mob/Monsters/proc/RemasterCarryParents(mob/Monsters/F, mob/Monsters/M)
	if(istype(F)) F.RemasterLineageEnsure(F.RemasterLineageOwner())
	if(istype(M)) M.RemasterLineageEnsure(M.RemasterLineageOwner())
	remaster_carried_parents = list(istype(F) ? F.remaster_uid : null, istype(M) ? M.remaster_uid : null,
		istype(F) ? "[F.name]" : null, istype(M) ? "[M.name]" : null,
		istype(F) ? F.remaster_house : null, istype(M) ? M.remaster_house : null,
		istype(F) ? F.remaster_generation : 0, istype(M) ? M.remaster_generation : 0)

// Called by GiveBirth() for each child. FATHER/MOTHER may be the child itself
// when the original code lost the parents (for example after a reload).
mob/Monsters/proc/RemasterRecordBirth(mob/Monsters/F, mob/Monsters/M, mob/Monsters/carrier)
	if(Critter || Egg) return
	var/Player/P = RemasterLineageOwner()
	RemasterAutoName()
	if(!remaster_uid) remaster_uid = RemasterNewUID()
	if(F == src) F = null
	if(M == src) M = null
	// The original copies a lost parent's slot from the other; keep one parent, by gender.
	if(F && F == M)
		if(F.Gender == "Female") F = null
		else M = null
	var/fid; var/mid; var/fname; var/mname; var/fhouse; var/mhouse; var/fgen = 0; var/mgen = 0
	if(istype(F))
		F.RemasterLineageEnsure(F.RemasterLineageOwner())
		fid = F.remaster_uid; fname = "[F.name]"; fhouse = F.remaster_house; fgen = F.remaster_generation
	if(istype(M))
		M.RemasterLineageEnsure(M.RemasterLineageOwner())
		mid = M.remaster_uid; mname = "[M.name]"; mhouse = M.remaster_house; mgen = M.remaster_generation
	// Parents recorded when the pregnancy or egg began fill any side now missing.
	var/list/C = istype(carrier) ? carrier.remaster_carried_parents : null
	if(islist(C) && length(C) >= 8)
		if(!fid && C[1]) { fid = C[1]; fname = C[3]; fhouse = C[5]; fgen = C[7] }
		if(!mid && C[2]) { mid = C[2]; mname = C[4]; mhouse = C[6]; mgen = C[8] }
	remaster_father = fid
	remaster_mother = mid
	remaster_parent_names = list(fname, mname)
	remaster_house = fhouse ? fhouse : mhouse
	if(!remaster_house && P) remaster_house = P.RemasterMainHouse(src)
	remaster_generation = max(fgen, mgen) + 1
	remaster_born = RemasterLineageDate()
	if(istype(F) && istype(M) && F != M)
		if(!islist(F.remaster_partners)) F.remaster_partners = list()
		if(!islist(M.remaster_partners)) M.remaster_partners = list()
		if(!(mid in F.remaster_partners)) F.remaster_partners += mid
		if(!(fid in M.remaster_partners)) M.remaster_partners += fid
	if(P)
		var/house = P.RemasterHouseName(remaster_house)
		P.RemasterNotice("[name] was born[house ? " into House [house]" : ""].")
		P.RemasterLog("[name] was born[house ? " into House [house]" : ""]", "birth", src)

Player/proc/RemasterHouseName(id)
	if(!id) return null
	var/list/H = remaster_houses ? remaster_houses[id] : null
	if(!H) H = RemasterForeignHouse(id)
	return H ? H["name"] : null

// A house this player doesn't own (a captured or gifted unit's family):
// look it up among the players in the world.
proc/RemasterForeignHouse(id)
	if(!id) return null
	for(var/Player/Q in world) if(Q.remaster_houses && Q.remaster_houses[id]) return Q.remaster_houses[id]
	return null

// Called by Death() before the unit is removed. Dead relatives stay in the
// family tree through this capped ledger.
mob/Monsters/proc/RemasterRecordDeath()
	var/Player/P = RemasterLineageOwner()
	if(!P || Critter || Egg) return
	RemasterLineageEnsure(P)
	if(!P.remaster_ledger) P.remaster_ledger = list()
	var/killer = Killer ? RmKillerName(Killer, P) : null
	P.remaster_ledger[remaster_uid] = list("name"="[name]", "race"="[Race]", "gender"="[Gender]", "house"=remaster_house,
		"father"=remaster_father, "mother"=remaster_mother, "parentNames"=remaster_parent_names,
		"partners"=remaster_partners ? remaster_partners.Copy() : list(), "generation"=remaster_generation,
		"born"=remaster_born, "died"=RemasterLineageDate(), "age"=Age, "level"=Level, "killer"=killer,
		"royal"=!!IsRoyal)
	while(length(P.remaster_ledger) > 500) P.remaster_ledger.Cut(1, 2)
	if(!RmDeathLogged(P)) P.RemasterLog("[name] died[killer ? " ([killer])" : ""]", "death", src)
	RemasterSuccession(P)

// A death whose cause was logged this tick ("died of poison", "died of the fever") isn't logged a second time: the
// two lines made the day's summary count one death as two.
mob/Monsters/proc/RmDeathLogged(Player/P)
	var/list/L = P.remaster_village_log
	var/bare = "[RemasterBareName()] died"
	if(L) for(var/i = length(L), i >= 1 && i > length(L) - 3, i--)
		var/list/E = L[i]
		if(E[1] != world.time) break
		if(E[3] == "death" && findtext(E[2], bare) == 1) return 1
	return 0

// The killer as the family tree and the log show it: "Human Paladin", "Grak of House Bob", "Bob's poison"; never
// "{NPC Alliance} Human Paladin" (the tree showed the name tags as they are). Own units lose their tag.
proc/RmKillerName(K, Player/P)
	var/t = "[K]"
	var/i = findtext(t, "{")
	while(i)
		var/j = findtext(t, "} ", i)
		if(!j) break
		var/tag = copytext(t, i + 1, j)
		var/rest = copytext(t, j + 2)
		if(!length(tag) || findtext(tag, "NPC") == 1 || (P && tag == "[P]")) t = copytext(t, 1, i) + rest
		else
			var/e = findtext(rest, "'s ")
			t = e ? "[copytext(t, 1, i)][copytext(rest, 1, e)] of House [tag][copytext(rest, e)]" : "[copytext(t, 1, i)][rest] of House [tag]"
		i = findtext(t, "{")
	return t

// Payload for the Village > Lineage view: living units the player owns plus
// the dead in the ledger. Relations are worked out on the client.
// The tree only changes when people, the ledger, houses or the focus change;
// rebuild it then, or every 5 seconds for ages and levels.
Player/var/tmp/remaster_lineage_cache
Player/var/tmp/remaster_lineage_cache_key
Player/var/tmp/remaster_lineage_cache_at = 0
Player/proc/RemasterLineageDataCached()
	var/key = "[length(UnitList)]|[length(remaster_ledger)]|[remaster_lineage_focus]|[length(remaster_houses)]|[remaster_heir_uid]|[remaster_hero_uid]|[length(Selected)]"
	if(remaster_houses) for(var/id in remaster_houses) key += "|[remaster_houses[id]["name"]]"
	if(key != remaster_lineage_cache_key || world.time - remaster_lineage_cache_at > 50)
		remaster_lineage_cache_key = key
		remaster_lineage_cache_at = world.time
		remaster_lineage_cache = RemasterLineageData()
	return remaster_lineage_cache

Player/proc/RemasterLineageData()
	var/list/people = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && !M.Wagon && !M.Critter && !M.Egg)
		M.RemasterLineageEnsure(src)
		people[M.remaster_uid] = list("uid"=M.remaster_uid, "ref"=RemasterUIRef(M), "alive"=1, "name"="[M.name]", "race"="[M.Race]",
			"gender"="[M.Gender]", "age"=M.Age, "level"=M.Level, "house"=M.remaster_house, "father"=M.remaster_father,
			"mother"=M.remaster_mother, "parentNames"=M.remaster_parent_names, "partners"=M.remaster_partners,
			"generation"=M.remaster_generation, "born"=M.remaster_born, "royal"=!!M.IsRoyal, "portrait"=RemasterPortrait(M),
			"egg"=!!M.Egg)
	if(remaster_ledger)
		for(var/uid in remaster_ledger)
			if(people[uid]) continue
			var/list/R = remaster_ledger[uid]
			var/list/D = R.Copy()
			D["uid"] = uid
			D["alive"] = 0
			people[uid] = D
	var/list/houses = list()
	if(remaster_houses) for(var/id in remaster_houses)
		var/list/H = remaster_houses[id]
		houses[id] = list("id"=id, "name"=H["name"], "color"=H["color"], "founded"=H["founded"], "founder"=H["founder"], "main"=(id == remaster_main_house))
	// Units from other houses (captured, gifted): show their house, marked as foreign.
	for(var/uid in people)
		var/list/D = people[uid]
		var/hid = D["house"]
		if(!hid || houses[hid]) continue
		var/list/H = RemasterForeignHouse(hid)
		houses[hid] = list("id"=hid, "name"=(H ? H["name"] : "of another lord"), "color"=(H ? H["color"] : "#555555"), "founded"=(H ? H["founded"] : null), "founder"=null, "main"=0, "foreign"=1)
	return list("people"=people, "houses"=houses, "focus"=remaster_lineage_focus, "succession"=RemasterSuccessionData())

Player/proc/RemasterRenameHouse(value)
	var/list/parts = splittext("[value]", "|")
	if(parts.len != 2 || !remaster_houses || !remaster_houses[parts[1]]) return 0
	var/name = replacetext(replacetext(replacetext(parts[2], "<", ""), ">", ""), "\"", "")
	if(!length(name) || length(name) > 32)
		RemasterNotice("House names need 1 to 32 characters.")
		return 0
	var/list/H = remaster_houses[parts[1]]
	H["name"] = name
	RemasterNotice("Your house is now House [name].")
	return 1
