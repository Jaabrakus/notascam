// New weapons, armour, robes and magic items (planning/WEARABLES.md).
// Item types and recipes are generated into GearData.dm by art/enhance/game_export.py;
// this file makes them craftable, wearable and visible:
//   * every workshop that makes gear (Forge, Bone crafting, Leatherworks, Carpentry, Gem
//     cutter) offers "Craft new gear" beside its own Craft and Destroy. The original
//     menus are untouched: the unit being asked is noted (RemasterInteractActor), the
//     extra answer is handed back as Cancel, and the new menus run after the original
//     click has finished;
//   * crafting needs the workshop skill's level, the race the catalogue allows, the
//     materials carried by the unit (and lava beside the forge for hell-forged gear, mana
//     from a rune circuit beside the Gem cutter for enchanting). Success and quality
//     come from the skill as at the Forge;
//   * equipping needs the item's Remastered level (Attack, Defence, Magic or Mining), and a
//     two-handed weapon and a shield do not go together;
//   * in the 3D view every worn item is drawn from its 64 px picture fitted to that race's
//     body (Icons/Remastered/Gear64/<sheet>/), the game's own gear included.

obj/Items/var
	rm_gear            // catalogue id, e.g. "weapon.arming sword.iron"
	rm_group           // its picture sheet (tier, "cloth" or "magic")
	rm_use             // skill var needed to use it ("AttackSkill"...) and its level
	rm_use_level = 0
	rm_use2
	rm_use2_level = 0
	rm_hands = 1

#define RM_GEAR_OPTION "Craft new gear"
#define RM_GEAR_MANA_RANGE 3

var/list/rm_gear_materials = list("iron ingot"=/obj/Items/Ingots/IronIngot, "silver ingot"=/obj/Items/Ingots/SilverIngot,
	"gold ingot"=/obj/Items/Ingots/GoldIngot, "adamantium ingot"=/obj/Items/Ingots/AdamantiumIngot, "wood"=/obj/Items/woods/wood,
	"skin"=/obj/Items/Skin, "bones"=/obj/Items/Bones/Bones, "skull"=/obj/Items/Bones/Skull, "shell"=/obj/Items/Bones/Shell,
	"demon head"=/obj/Items/Bones/Head, "spider silk"=/obj/Items/Silks/SpiderSilk, "cut diamond"=/obj/Items/gems/Diamond,
	"cut ruby"=/obj/Items/gems/Ruby, "cut emerald"=/obj/Items/gems/Emerald, "poison gland"=/obj/Items/Glands/PoisonGland,
	"toxic gland"=/obj/Items/Glands/ToxicGland, "dragon scales"=/obj/Items/Bones/DragonScales, "dragon fang"=/obj/Items/Bones/BeastFang/DragonTooth, "spider fang"=/obj/Items/Bones/BeastFang/SpiderFang, "dragon bones"=/obj/Items/Bones/Bones/DragonBones, "wing hide"=/obj/Items/Skin/WingHide)   // BeastParts.dm
// a severed head is a Head showing its race (Death.dm, MakeHead)
var/list/rm_gear_material_state = list("demon head"="Demon")
var/list/rm_gear_skill_names = list("MetalCraftingSkill"="Smithing", "LeatherCraftingSkill"="Leatherwork",
	"BoneCraftingSkill"="Bone craft", "WoodCraftingSkill"="Woodwork", "JewlCraftingSkill"="Gem cutting",
	"AttackSkill"="Attack", "DefenceSkill"="Defence", "MagicSkill"="Magic", "MineingSkill"="Mining")
var/list/rm_gear_groups = list("wood"="Wood", "leather"="Leather", "bone"="Bone", "chitin"="Chitin", "iron"="Iron",
	"silver"="Silver", "gold"="Gold", "adamantium"="Adamantium", "diamond"="Diamond", "hell"="Hellforged",
	"cloth"="Robes and cloth", "magic"="Magic", "dragon"="Dragonscale", "dragonfang"="Dragonfang", "spiderfang"="Spiderfang", "dragonbone"="Dragonbone",
	"dragonhide"="Dragonhide", "spidersilk"="Spidersilk", "bonehide"="Bonehide", "supplies"="Supplies")   // supplies: art/items/catalogue.json's rows
var/list/rm_gear_slots = list("weapon"="Weapons", "helmet"="Helmets", "chest"="Chest", "legs"="Legs", "arms"="Arms", "shield"="Shields", "item"="Other items")
var/list/rm_gear_quality = list("Poor Quality"=0.85, "Average Quality"=0.93, "Quality"=1, "Impressive Quality"=1.05,
	"Grand Quality"=1.1, "Masterful Quality"=1.15, "Epic Quality"=1.2, "Legendary Quality"=1.3)

Player/var/tmp
	rm_gear_said                    // the last thing the gear menus told this player
	mob/WorkShops/rm_gear_station   // the workshop whose menu is open
	mob/Monsters/rm_gear_actor      // the unit that menu is asking about
	list/rm_gear_queue              // units that chose "Craft new gear"

// --- levels -------------------------------------------------------------------------

proc/RmGearLevel(mob/M, var_name)
	if(!M || !var_name || !(var_name in M.vars)) return 1
	var/v = M.vars[var_name]
	return isnum(v) ? max(1, round(v)) : 1

proc/RmGearSkillText(var_name, level)
	return "[rm_gear_skill_names[var_name] || var_name] [level]"

// What a unit lacks to use an item ("" when it may).
proc/RmGearUseNeed(obj/Items/I, mob/M)
	var/list/need = list()
	if(I.rm_use && RmGearLevel(M, I.rm_use) < I.rm_use_level) need += RmGearSkillText(I.rm_use, I.rm_use_level)
	if(I.rm_use2 && RmGearLevel(M, I.rm_use2) < I.rm_use2_level) need += RmGearSkillText(I.rm_use2, I.rm_use2_level)
	return jointext(need, " and ")

// --- the catalogue ----------------------------------------------------------------------

var/list/rm_gear_by_station = list()
proc/RmGearDefsAt(key)
	if(!rm_gear_by_station[key])
		var/list/L = list()
		for(var/list/G in rm_gear_defs + rm_item_defs) if(G["station"] == key) L += list(G)   // and the items catalogue's (ItemData.dm)
		rm_gear_by_station[key] = L
	return rm_gear_by_station[key]

var/list/rm_gear_station_names = list("forge"="Forge", "bone"="Bone crafting workshop", "leather"="Leatherworks",
	"carpentry"="Carpentry", "gem"="Gem cutter")
proc/RmGearStationName(mob/WorkShops/W)
	return rm_gear_station_names[RmGearStationKey(W)] || "workshop"

proc/RmGearStationKey(mob/WorkShops/W)
	if(istype(W, /mob/WorkShops/Forge)) return "forge"
	if(istype(W, /mob/WorkShops/BoneCraft)) return "bone"
	if(istype(W, /mob/WorkShops/LeatherWorks)) return "leather"
	if(istype(W, /mob/WorkShops/Carpentry)) return "carpentry"
	if(istype(W, /mob/WorkShops/GemCutter)) return "gem"
	return null

proc/RmGearRaceOK(list/G, mob/M)
	var/list/only = G["only"]
	var/list/no = G["not"]
	if(only && !(M.Race in only)) return 0
	if(no && (M.Race in no)) return 0
	return 1

proc/RmGearCanCraftHere(mob/WorkShops/W, mob/Monsters/M)
	var/key = RmGearStationKey(W)
	if(!key || !M) return 0
	for(var/list/G in RmGearDefsAt(key)) if(RmGearRaceOK(G, M)) return 1
	return 0

// What a unit lacks in skill to make it ("" when it may).
proc/RmGearCraftNeed(list/G, mob/M)
	var/list/need = list()
	if(RmGearLevel(M, G["craft"]) < G["craft_level"]) need += RmGearSkillText(G["craft"], G["craft_level"])
	if(G["craft2"] && RmGearLevel(M, G["craft2"]) < G["craft2_level"]) need += RmGearSkillText(G["craft2"], G["craft2_level"])
	return jointext(need, " and ")

proc/RmGearRecipeText(list/G)
	var/list/parts = list()
	if(G["base"]) parts += "a [G["base_name"]]"
	var/list/R = G["recipe"]
	var/pair = G["slot"] == "arms" ? 2 : 1
	for(var/m in R) parts += "[R[m] * pair] [m]"
	if(G["mana"]) parts += "[G["mana"]] mana"
	return jointext(parts, ", ")

// The menu line: name, then what it takes.
proc/RmGearLabel(list/G)
	var/name = G["slot"] == "arms" ? "[G["name"]]s (pair)" : G["name"]
	var/craft = RmGearSkillText(G["craft"], G["craft_level"])
	if(G["craft2"]) craft += ", [RmGearSkillText(G["craft2"], G["craft2_level"])]"
	return "[name] - [craft] - [RmGearRecipeText(G)]"

// --- materials ----------------------------------------------------------------------------

proc/RmGearCarried(mob/M, T, state = null)
	. = list()
	for(var/obj/Items/I in M) if(istype(I, T) && I.suffix == "(Carrying)" && (isnull(state) || I.icon_state == state)) . += I

proc/RmGearMissing(list/G, mob/M)
	var/list/missing = list()
	var/list/R = G["recipe"]
	var/pair = G["slot"] == "arms" ? 2 : 1
	for(var/m in R)
		var/have = length(RmGearCarried(M, rm_gear_materials[m], rm_gear_material_state[m]))
		if(have < R[m] * pair) missing += "[R[m] * pair - have] more [m]"
	if(G["base"] && !length(RmGearCarried(M, G["base"]))) missing += "a [G["base_name"]]"
	return missing

proc/RmGearUse(mob/M, T, count, state = null)
	for(var/obj/Items/I in RmGearCarried(M, T, state))
		if(count <= 0) break
		M.weight -= I.weight
		del(I)
		count--

proc/RmGearLavaNear(mob/WorkShops/W)
	for(var/turf/L in range(1, W)) if(findtext("[L.icon_state]", "Lava")) return 1
	return 0

// The rune circuit beside a workshop (Runes.dm), or null.
proc/RmGearCircuit(mob/WorkShops/W)
	if(rm_runes_dirty) RemasterRuneRebuild()
	for(var/obj/RemasterRune/R in range(RM_GEAR_MANA_RANGE, W)) if(R.net) return R.net
	return null

// --- crafting ---------------------------------------------------------------------------------

proc/RmGearRank(skill, list/G)
	if(G["tier"] == "adamantium") return "Legendary Quality"   // as the Forge's adamantium
	if(skill >= 100) return "Legendary Quality"
	if(skill > 75) return "Epic Quality"
	if(skill > 60) return "Masterful Quality"
	if(skill > 50) return "Grand Quality"
	if(skill > 40) return "Impressive Quality"
	if(skill > 30) return "Quality"
	if(skill > 20) return "Average Quality"
	return "Poor Quality"

proc/RmGearApplyRank(obj/Items/I, rank)
	var/f = rm_gear_quality[rank] || 1
	I.CraftRank = rank
	if(I.WeaponDamageMin) I.WeaponDamageMin = round(I.WeaponDamageMin * f)
	if(I.WeaponDamageMax) I.WeaponDamageMax = round(I.WeaponDamageMax * f)
	if(I.Defence) I.Defence = round(I.Defence * f, 0.1)
	I.name = "[I.name] - [rank]"

// Make one item (or a pair of arm pieces). 1 on success.
proc/RmGearSay(Player/P, text)
	P.rm_gear_said = text
	P << text

proc/RmGearCraft(Player/P, mob/Monsters/M, mob/WorkShops/W, list/G)
	if(!P || !M || !W || !G) return 0
	if(!(M in range(1, W)))
		RmGearSay(P, "[M] must stand next to the [RmGearStationName(W)] to make the [G["name"]].")
		return 0
	if(!RmGearRaceOK(G, M))
		RmGearSay(P, "[M] does not know how to make the [G["name"]].")
		return 0
	var/need = RmGearCraftNeed(G, M)
	if(need)
		RmGearSay(P, "[M] needs [need] to make the [G["name"]].")
		return 0
	if(G["lava"] && !RmGearLavaNear(W))
		RmGearSay(P, "Hellforged gear is made at a forge beside lava.")
		return 0
	var/list/missing = RmGearMissing(G, M)
	if(length(missing))
		RmGearSay(P, "[M] needs [jointext(missing, ", ")] to make the [G["name"]].")
		return 0
	var/datum/rm_runenet/N
	if(G["mana"])
		N = RmGearCircuit(W)
		if(!N || RemasterRuneNetMana(N) < G["mana"])
			RmGearSay(P, "Enchanting needs a rune circuit beside the [RmGearStationName(W)] holding [G["mana"]] mana.")
			return 0
	if(!M.RemasterManualHandoff(P)) return 0
	var/skill = M.vars[G["craft"]]
	var/list/R = G["recipe"]
	var/pair = G["slot"] == "arms" ? 2 : 1
	if(!prob(RemasterCraftOdds(skill, 4)))
		// a failed attempt spoils one piece of the main material, as the original recipes do
		for(var/m in R)
			RmGearUse(M, rm_gear_materials[m], 1, rm_gear_material_state[m])
			break
		M.vars[G["craft"]] += 1
		RmGearSay(P, "[M] failed to make the [G["name"]].")
		return 0
	var/rank = RmGearRank(skill, G)
	if(G["base"])   // an enchanted weapon keeps the quality of the weapon it was made from
		var/list/B = RmGearCarried(M, G["base"])
		var/obj/Items/base = B[1]
		if(base.CraftRank) rank = base.CraftRank
		M.weight -= base.weight
		del(base)
	var/colour = RmPartsColour(M, R)   // a dragon's scales or hide give it their colour (BeastParts.dm)
	for(var/m in R) RmGearUse(M, rm_gear_materials[m], R[m] * pair, rm_gear_material_state[m])
	if(N) RemasterRuneSpend(N, G["mana"])
	var/item = G["slot"] == "item"   // an items catalogue row (ItemData.dm): no quality, and it may make several
	for(var/k = 1, k <= (item ? max(1, G["makes"]) : 1), k++) for(var/T in G["types"])
		var/obj/Items/I = new T(M.loc)
		if(!item) RmGearApplyRank(I, rank)
		RmGiveColour(I, colour)
	M.vars[G["craft"]] += 0.5
	if(item) RmGearSay(P, "[M] made [G["makes"] > 1 ? "[G["makes"]] [G["name"]]" : "the [G["name"]]"].")
	else RmGearSay(P, "[M] made [G["slot"] == "arms" ? "a pair of [G["name"]]s" : "the [G["name"]]"] ([rank]).")
	return 1

// The new gear menus for one unit at one workshop: material, kind, item.
proc/RmGearMenu(Player/P, mob/Monsters/M, mob/WorkShops/W)
	var/key = RmGearStationKey(W)
	if(!key || !M) return 0
	var/list/defs = list()
	for(var/list/G in RmGearDefsAt(key)) if(RmGearRaceOK(G, M)) defs += list(G)
	if(!length(defs)) return 0
	var/list/groups = list()
	for(var/list/G in defs)
		var/g = rm_gear_groups[G["group"]]
		if(!(g in groups)) groups += g
	var/group = length(groups) == 1 ? groups[1] : P.RemasterActionChoice("Which material will [M] work?", "Craft new gear", groups + "Cancel")
	if(!group || group == "Cancel") return 0
	var/list/slots = list()
	for(var/list/G in defs) if(rm_gear_groups[G["group"]] == group)
		var/s = rm_gear_slots[G["slot"]]
		if(!(s in slots)) slots += s
	var/slot = length(slots) == 1 ? slots[1] : P.RemasterActionChoice("What kind?", "Craft new gear", slots + "Cancel")
	if(!slot || slot == "Cancel") return 0
	var/list/menu = list()
	var/list/pick = list()
	for(var/list/G in defs) if(rm_gear_groups[G["group"]] == group && rm_gear_slots[G["slot"]] == slot)
		var/label = RmGearLabel(G)
		menu += label
		pick[label] = G
	var/choice = P.RemasterActionChoice("What will [M] make?", "Craft new gear", menu + "Cancel")
	if(!choice || choice == "Cancel" || !pick[choice]) return 0
	return RmGearCraft(P, M, W, pick[choice])

// --- the workshop hook ----------------------------------------------------------------------

Player/RemasterInteractActor(mob/Monsters/M)
	. = ..()
	if(. && rm_gear_station) rm_gear_actor = M

mob/RemasterActionChoice(message, title, list/options, default = null)
	if(istype(src, /Player))
		var/Player/P = src
		if(P.rm_gear_station && islist(options) && ("Craft" in options) && ("Destroy" in options) && !(RM_GEAR_OPTION in options))
			var/mob/Monsters/M = P.rm_gear_actor
			if(M && RmGearCanCraftHere(P.rm_gear_station, M))
				var/list/O = options.Copy()
				O.Insert(O.Find("Craft") + 1, RM_GEAR_OPTION)
				. = ..(message, title, O, default)
				if(. == RM_GEAR_OPTION)
					if(!P.rm_gear_queue) P.rm_gear_queue = list()
					P.rm_gear_queue += M
					return "Cancel"   // the original menu does nothing for this unit
				return .
	return ..()

proc/RmGearBegin(Player/P, mob/WorkShops/W)
	P.rm_gear_station = W
	P.rm_gear_actor = null
	P.rm_gear_queue = null

proc/RmGearEnd(Player/P, mob/WorkShops/W)
	if(!P) return   // the original click may end with its player gone
	var/list/Q = P.rm_gear_queue
	P.rm_gear_station = null
	P.rm_gear_actor = null
	P.rm_gear_queue = null
	if(!W) return
	for(var/mob/Monsters/M in Q) if(P.RemasterInteractActor(M) && M.HP > 0) RmGearMenu(P, M, W)

mob/WorkShops/Forge/DblClick()
	var/Player/P = usr
	if(!istype(P)) return ..()
	RmGearBegin(P, src)
	. = ..()
	if(P) RmGearEnd(P, src)

mob/WorkShops/BoneCraft/DblClick()
	var/Player/P = usr
	if(!istype(P)) return ..()
	RmGearBegin(P, src)
	. = ..()
	if(P) RmGearEnd(P, src)

mob/WorkShops/LeatherWorks/DblClick()
	var/Player/P = usr
	if(!istype(P)) return ..()
	RmGearBegin(P, src)
	. = ..()
	if(P) RmGearEnd(P, src)

mob/WorkShops/Carpentry/DblClick()
	var/Player/P = usr
	if(!istype(P)) return ..()
	RmGearBegin(P, src)
	. = ..()
	if(P) RmGearEnd(P, src)

mob/WorkShops/GemCutter/DblClick()
	var/Player/P = usr
	if(!istype(P)) return ..()
	RmGearBegin(P, src)
	. = ..()
	if(P) RmGearEnd(P, src)

// --- equipping --------------------------------------------------------------------------------

mob/Monsters/EquipItem(obj/Items/ITEM, MANUAL)
	if(ITEM && ITEM.loc == src && ITEM.suffix == "(Carrying)")
		if(ITEM.rm_gear)
			var/need = RmGearUseNeed(ITEM, src)
			if(need && !rm_gear_any_on)
				if(Owner) Owner << "[src] needs [need] to use the [ITEM]."
				return 0
			if(need && Owner && MANUAL) Owner << "[src] uses the [ITEM] at [round(100 * RmGearEff(ITEM, src))]% until [need]."   // GearAny.dm
		// a two-handed weapon and a shield do not go together: the newer one wins
		if(ITEM.EquipmentType() == "Weapon" && ITEM.rm_hands >= 2)
			for(var/obj/Items/Equipment/Armour/Shield/S in src) if(S.suffix == "(Equipped)") UnEquipItem(S)
		else if(ITEM.ItemType == "Shield")
			for(var/obj/Items/Equipment/Weapon/X in src) if(X.suffix == "(Equipped)" && X.rm_hands >= 2) UnEquipItem(X)
	return ..()

// --- the 3D view ----------------------------------------------------------------------------

// An icon's file name, lower case and without its folder ("[icon]" here reads "Icons/Human.dmi").
proc/RmIconName(I)
	var/t = "[I]"
	var/slash = findlasttext(t, "/")
	return lowertext(slash ? copytext(t, slash + 1) : t)

// Bodies drawn the same shape share their gear sheets.
// Flying, a vampire, demon or gargoyle wears its gear as on its walking body.
var/list/rm_gear_sheet_alias = list("HumanBlack"="Human", "VampireFly"="Vampire", "DemonFly"="Demon", "GargoyleFly"="Gargoyle")

// A race's Races64 sheet, for a possessed half-demon whose picture is no longer its race's file
// (its red tint, icon += rgb() in Race.dm, is a picture of its own).
var/list/rm_race_sheets = list("Human"="Human", "Dwarf"="Dwarves", "Elf"="Human", "Svartalfar"="Night Elf", "Orc"="Orc",
	"Goblin"="Goblins", "Kobold"="Kobold", "Lizardman"="LizardMan", "Frogman"="FrogMan", "Demon"="Demon", "Gargoyle"="Gargoyle")

// The Races64 sheet a unit's 64 px body comes from (Remaster3DBody64), or null.
proc/RmRaceSheet(mob/M)
	var/name = remaster_3d_races64[RmIconName(M.icon)]
	if(!name && istype(M, /mob/Monsters) && M:SubRace == "HalfDemon")
		name = rm_race_sheets[M:Race]
		if(name == "Human" && M:Black) name = "HumanBlack"
	if(name && istype(M, /mob/Monsters) && M:Race == "Dwarf") name = "Dwarves"
	return name

proc/RmGearSheet(mob/M)
	return RmRaceSheet(M)

// A gargoyle's eyes glow one of three colours (art/enhance/game_export.py GARGOYLE_EYES), its
// own for life.
mob/Monsters/var/rm_eyes
proc/RmEyeSheet(mob/Monsters/M, name)
	if(!istype(M) || !(name in list("Gargoyle", "GargoyleFly"))) return null
	if(!M.rm_eyes) M.rm_eyes = pick("Amber", "Red", "Ice")
	return "Icons/Remastered/Races64/[name]-[M.rm_eyes].dmi"

var/list/rm_gear64_states = list()   // path -> its states (empty: no such file)
proc/RmGear64States(path)
	if(isnull(rm_gear64_states[path]))
		rm_gear64_states[path] = fexists(path) ? icon_states(file(path)) : list()
	return rm_gear64_states[path]

// A picture fitted to this unit's 64 px body (Gear64/<sheet>/<group>.dmi), or null.
proc/RmFitted64(mob/M, group, state)
	var/sheet = RmGearSheet(M)
	if(sheet in rm_gear_sheet_alias) sheet = rm_gear_sheet_alias[sheet]
	if(!sheet) return null
	var/path = "Icons/Remastered/Gear64/[sheet]/[group].dmi"
	if(state in RmGear64States(path)) return list(file(path), state)

// The Gear64 group of the game's own pictures from one icon file: "old-" and the file's
// name without ".dmi", in the file's own case.
proc/RmOldGroup(I)
	var/base = "[I]"
	var/slash = findlasttext(base, "/")
	if(slash) base = copytext(base, slash + 1)
	if(length(base) < 5) return null   // no icon file (a bare base-type item): no group; copytext threw on it (polish-errors)
	return "old-[copytext(base, 1, length(base) - 3)]"

// A worn item's picture for the 3D view: fitted to this race's 64 px body when there is
// one (new gear by its tier sheet; the game's own gear by its new look, GearOldLooks.dm,
// else by its icon file), else its own.
proc/RmGear64(mob/M, obj/Items/E, body64)
	if(body64)
		var/list/P
		if(E.rm_gear) P = RmFitted64(M, E.rm_group, E.icon_state)
		else
			var/old = RmOldGroup(E.icon)
			var/list/N = rm_old_gear_looks["[old]|[E.icon_state]"]
			if(N) P = RmFitted64(M, N[1], N[2])
			if(!P) P = RmFitted64(M, old, E.icon_state)
		if(P && E.rm_colour) P = RmDragonTint(P, E.rm_colour)
		if(P) return P
	return list(E.icon, E.icon_state)

// One of the game's own looks (a woman's top, hair, a beard) for a unit's layer list: the
// original on the original body; on a 64 px body its fitted picture, or nothing (the 32 px
// one would not sit on it).
proc/RmLook(mob/M, I, state, body64)
	if(!body64) return list(list(I, state))
	var/list/P = RmFitted64(M, RmOldGroup(I), state)
	return P ? list(P) : list()

// The animated effects (glow, sparks, flame) of the magic items a unit holds, fitted to its
// 64 px body (Gear64/<sheet>/fx.dmi: 4 effect frames for each frame of the unit's picture).
proc/RmGearFx(mob/M, body64)
	. = list()
	if(!body64) return
	for(var/obj/Items/Equipment/E in M) if(E.suffix == "(Equipped)" && E.rm_group == "magic")
		var/list/P = RmFitted64(M, "fx", E.icon_state)
		if(P) . += list(P)
