// Soul stones (Remastered): a dead villager's soul moved into a gargoyle.
//  - A Soul stone is a rare stone of the mountains: about one rock tile in 150 mined on the
//    surface gives one up (Biomes.dm RemasterBiomeMined). Empty, it is a dull grey-violet.
//  - Used beside the body of a person, not an animal (held and clicked onto the body, UseOn.dm, or
//    double-clicked in the bag beside it): the stone
//    drinks the soul. It glows and bears the dead's name, and the body crumbles to dust. What a
//    body keeps of who it was is taken when it falls (Death.dm MakeBody: RemasterSoulOf).
//  - Used beside a Gargoyle of yours that has no soul yet: the soul wakes in the stone body. The
//    gargoyle takes the dead's name and gender, their level, strength, agility, intelligence and
//    defence where higher than its own, and every skill they had, and it remembers who it was
//    (its examine text, Speech.dm). The stone crumbles. Like the original Form Gargoyle (a caged
//    creature's soul for a fresh gargoyle, CraftingStations.dm), but a person's whole self.

obj/Items/RemasterSoulStone
	// its values: art/items/catalogue.json row remastersoulstone (export_items.py writes ItemData.dm)
	var/list/soul                    // saved: what the stone holds (RemasterSoulOf), or null

obj/Items/RemasterSoulStone/proc/RemasterSoulLook()
	if(soul)
		name = "Soul stone ([soul["name"]])"
		color = "#c69cff"
		desc = "It glows: the soul of [soul["name"]], [RmAn(lowertext(soul["race"]))] of level [soul["level"]]. Used beside a gargoyle of yours with no soul, it wakes in the stone."
	else
		name = initial(name)
		color = initial(color)
		desc = initial(desc)

mob/Body/var/list/rm_soul            // who the body was (RemasterSoulOf), while it lies unburied
mob/Monsters/var/rm_soul             // saved: a gargoyle's: whose soul woke in it

// What a body keeps of the person: name, race, gender, level, stats and skills.
mob/Monsters/proc/RemasterSoulOf()
	if(Critter || Egg || Wagon) return null
	var/list/skills = list()
	for(var/v in vars) if(length(v) > 5 && copytext(v, length(v) - 4) == "Skill" && isnum(vars[v]) && vars[v] > 0) skills[v] = vars[v]
	return list("name"=RemasterBareName(), "race"="[Race]", "gender"="[Gender]", "level"=Level, "str"=Strength,
		"agi"=Agility, "int"=Intelligence, "def"=Defence, "skills"=skills, "uid"=remaster_uid)

// The stone used (Bag.dm RemasterUseFor, double-click): take a soul from a body beside the unit, or
// give the one it holds to a gargoyle beside it. Held and clicked onto them (UseOn.dm) it does the same
// to the one clicked.
mob/Monsters/proc/RemasterUseSoulStone(obj/Items/RemasterSoulStone/S)
	var/Player/P = Owner
	if(!istype(P) || S.loc != src) return 0
	if(!S.soul)
		for(var/mob/Body/B in range(1, src)) if(isturf(B.loc) && B.rm_soul && !B.Critter)
			return RemasterSoulTake(S, B)
		P.RemasterNotice("[RemasterBareName()] must stand beside the body of the dead to take their soul.")
		return 0
	for(var/mob/Monsters/G in range(1, src)) if(G.Race == "Gargoyle" && G.Owner == P && !G.rm_soul && G.HP > 0)
		return RemasterSoulGive(S, G)
	P.RemasterNotice("[RemasterBareName()] must stand beside a gargoyle of yours that has no soul yet.")
	return 0

mob/Monsters/proc/RemasterSoulTake(obj/Items/RemasterSoulStone/S, mob/Body/B)
	var/Player/P = Owner
	if(!istype(P) || S.loc != src || S.soul || !B || !isturf(B.loc) || !B.rm_soul || B.Critter || get_dist(src, B) > 1) return 0
	S.soul = B.rm_soul
	S.RemasterSoulLook()
	view(src) << "<font color=#c69cff>[RemasterBareName()] holds the soul stone over [B]: it drinks the soul and glows. The body crumbles to dust.</font>"
	P.RemasterLog("[RemasterBareName()] took the soul of [S.soul["name"]] into a soul stone", "info", src)
	RemasterSay("Your soul is safe with me.", 1)
	del B
	return 1

mob/Monsters/proc/RemasterSoulGive(obj/Items/RemasterSoulStone/S, mob/Monsters/G)
	var/Player/P = Owner
	if(!istype(P) || S.loc != src || !S.soul || !G || G.Race != "Gargoyle" || G.Owner != P || G.rm_soul || G.HP <= 0 || get_dist(src, G) > 1) return 0
	var/list/soul = S.soul
	G.RemasterTakeSoul(soul)
	weight -= S.weight
	del S
	view(G) << "<font color=#c69cff>The soul stone crumbles. Light runs into the gargoyle's cracks and its eyes open: [soul["name"]] lives again, in stone.</font>"
	P.RemasterLog("[soul["name"]]'s soul woke in a gargoyle", "good", G)
	P.RemasterCheer("soulstone", "[soul["name"]] came back to us in stone", 3, 2)
	return 1

mob/Monsters/proc/RemasterTakeSoul(list/S)
	rm_soul = S["name"]
	RemasterSetName(S["name"])
	if(S["gender"]) Gender = S["gender"]
	Level = max(Level, S["level"])
	Strength = max(Strength, S["str"])
	Agility = max(Agility, S["agi"])
	Intelligence = max(Intelligence, S["int"])
	Defence = max(Defence, S["def"])
	var/list/K = S["skills"]
	if(K) for(var/v in K) if(v in vars) vars[v] = max(vars[v], K[v])
	RemasterRemember("soul", "Remembers living as [S["name"]], [RmAn(lowertext(S["race"]))]", 0, 3650)
	RemasterSay("I... remember.", 1)
