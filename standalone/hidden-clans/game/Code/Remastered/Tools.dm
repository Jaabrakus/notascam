// RuneScape-style tool tiers (Remastered gameplay change).
// In the original game an axe or pickaxe's material made no difference to
// chopping or digging. Here a better material chops/digs faster, but only once
// the villager has the skill level to use it well; below that it works at
// basic speed. The original skill growth, yields and requirements are kept.

// material, label, level needed, speed
proc/RemasterToolTiers()
	return list(
		list("HellForged", "Hell-Forged", 75, 2.2), list("Adamantium", "Adamantium", 50, 1.8),
		list("Gold", "Gold", 35, 1.5), list("Silver", "Silver", 25, 1.35),
		list("Bone", "Bone", 5, 1.1), list("Chitin", "Chitin", 5, 1.1),
		list("Wooden", "Wooden", 1, 1.0), list("Metal", "Metal", 15, 1.25))

proc/RemasterToolTier(obj/Items/I)
	var/path = "[I.type]"
	var/name = "[I.name]"
	for(var/list/T in RemasterToolTiers())
		var/key = T[1]
		if(key == "HellForged")
			if(findtext(name, "Hell Forged") || findtext(path, "Demonic")) return T
		else if(key == "Metal") return T // everything else is plain metal (iron)
		else if(findtext(path, key)) return T
	return null

// kind is "Axe" (Woodcutting) or "Pickaxe" (Mining).
mob/proc/RemasterHeldTool(kind)
	for(var/obj/Items/Equipment/E in src)
		if(E.suffix == "(Equipped)" && E.ItemType == kind) return E
	return null

mob/var/tmp/list/remaster_tool_warned

mob/proc/RemasterToolPower(kind)
	var/obj/Items/I = RemasterHeldTool(kind)
	if(!I) return 1
	var/list/T = RemasterToolTier(I)
	if(!T) return 1
	var/skill = kind == "Axe" ? vars["WoodCuttingSkill"] : vars["MineingSkill"]
	if(round(skill) >= T[3]) return T[4]
	// told once per player and tool, not once per unit (playtest: three identical lines as a new company's first chop)
	var/mob/W = ismob(Owner) ? Owner : src
	if(!W.remaster_tool_warned) W.remaster_tool_warned = list()
	if(!W.remaster_tool_warned["[kind][T[1]]"])
		W.remaster_tool_warned["[kind][T[1]]"] = 1
		if(ismob(Owner)) Owner << "Your people need [kind == "Axe" ? "Woodcutting" : "Mining"] [T[3]] to use a [lowertext(T[2])] [lowertext(kind)] well; until then they work at basic speed."
	return 1

// HUD: what each tool does for this unit.
mob/Monsters/proc/RemasterToolData()
	var/list/out = list()
	for(var/kind in list("Axe", "Pickaxe"))
		var/obj/Items/I = RemasterHeldTool(kind)
		if(!I) continue
		var/list/T = RemasterToolTier(I)
		if(!T) continue
		var/skill = kind == "Axe" ? WoodCuttingSkill : MineingSkill
		out += list(list("kind"=kind, "skill"=(kind == "Axe" ? "Woodcutting" : "Mining"), "tier"=T[2], "needs"=T[3], "speed"=T[4], "ok"=(round(skill) >= T[3])))
	return out
