// Dungeon Master Remastered: every player action in one place.
//  - Info > "Actions" tab: the commands for your selection and the general ones,
//    each with its key; a single click runs it (the same code as the original
//    HUD button or verb, called unchanged).
//  - HUD icons run on a single click (the original needed a double-click).
//  - F3 (or the Actions tab) opens the Controls & Actions guide.

/datum/remaster_screen
	var/list/screen = list()   // stands in for client.screen while a HUD button runs

// Original menus call this only after their final choice. Opening a submenu,
// cancelling it, or changing selection must never interrupt assigned work.
Player/proc/RemasterInteractActor(mob/Monsters/M)
	return M && M.Owner == src && RmInCompany(M)   // HudView.dm: no search of the whole company

// Touch access to the original F6 command. Keep its whole-selection racial
// and mist restrictions, and reject actors no longer controlled by this player.
Player/proc/RemasterMentalReason()
	if(!length(Selected)) return "Select an Illithid unit first."
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || !RmInCompany(M) || M.HP <= 0 || M.GoingToDie) return "Select your own living units."
		if(M.SubRace != "Illithid") return "Every selected unit must have Illithid mental abilities."
		if(M.IsMist) return "Leave mist form before using mental abilities."
	return ""

mob/proc/RemasterActionChoice(message, title, list/options, default = null)
	// Village crafting (StationCraft.dm) may answer in advance.
	if(istype(src, /Player))
		var/Player/P = src
		var/preset = P.RemasterPresetAnswer(options)
		if(!isnull(preset)) return preset
	return RemasterChoose(src, message, title, options, default)   // the HUD's question card (AskCard.dm)

Player/proc/RemasterInteractHandoff(mob/Monsters/M, choice)
	if(!choice || choice == "Cancel" || !RemasterInteractActor(M)) return 0
	return M.RemasterManualHandoff(src)

mob/Monsters/proc/RemasterToggleAutodig(Player/P)
	var/was_digging = Dig
	if(!RemasterManualHandoff(P)) return 0
	if(!was_digging)
		Dig = 1
		Dig()
		P << "[src]'s auto dig is on."
	else
		Dig = 0
		destination = null
		DigTarget = null
		P << "[src]'s auto dig is off."
		for(var/obj/DigAt/DD in world) if(DD.Owner == src) del(DD)
	return 1

obj/Hud/DigOnUnit/DblClick()
	if(!istype(usr, /Player)) return ..()
	for(var/mob/Monsters/M in usr.Selected.Copy()) M.RemasterToggleAutodig(usr)

/obj/RemasterAction
	var/action_id
	var/key
	var/needs_units
	var/hud_type

var/list/remaster_action_list

proc/RemasterActions()
	if(remaster_action_list) return remaster_action_list
	remaster_action_list = list()
	// id, label, key, needs selected units, original HUD button (or null for a verb)
	var/list/table = list(
		// keys as the skin binds them today (rts-feel 2026-10-23): N faces the 3D camera north, A is Attack, Q/E turn the
		// camera and Ctrl+A selects all, so Rename, Select nearby and Waypoint have no key of their own. The 2006 letter
		// keys are off the keyboard (rts-feel 2026-10-25, the user's call): these commands are in the menus only
		list("stop", "Stop: cancel orders and targets", "P", 1, /obj/Hud/Stop),
		list("guard", "Guard / guard rules", null, 1, null),
		list("interact", "Interact with something nearby", "I", 1, /obj/Hud/Interact),
		list("goto", "Centre view on selected unit", "Z", 1, /obj/Hud/Find),
		list("rename", "Rename selected units", null, 1, null),
		list("unitsay", "Speak through a unit", null, 1, null),
		list("emote", "Unit emote", null, 1, null),
		list("leader", "Declare a king/queen", null, 1, null),
		list("equip", "Equip all armour", null, 1, /obj/Hud/EquipArmor),
		list("unequip", "Unequip all armour", null, 1, /obj/Hud/RemoveArmor),
		list("autodig", "Auto dig on/off", null, 1, /obj/Hud/DigOnUnit),
		list("pickwood", "Pick up nearby wood", null, 1, /obj/Hud/Wood),
		list("pickstone", "Pick up nearby stone", null, 1, /obj/Hud/Stone),
		list("pickores", "Pick up nearby ores", null, 1, /obj/Hud/Ores),
		list("pickgems", "Pick up nearby gems", null, 1, /obj/Hud/Gem),
		list("pickingots", "Pick up nearby ingots", null, 1, /obj/Hud/Ingots),
		list("pickfood", "Pick up nearby food", null, 1, /obj/Hud/Edibles),
		list("pickbones", "Pick up nearby bones", null, 1, /obj/Hud/Bones),
		list("pickskin", "Pick up nearby skin", null, 1, /obj/Hud/Skin),
		list("pickseeds", "Pick up nearby seeds", null, 1, /obj/Hud/Seeds),
		list("pickarmour", "Pick up nearby armour", null, 1, /obj/Hud/Armor),
		list("pickarrows", "Pick up nearby arrows (needs a quiver)", null, 1, /obj/Hud/Arrows),
		list("dropwood", "Drop all wood", null, 1, /obj/Hud/DropWood),
		list("dropstone", "Drop all stone", null, 1, /obj/Hud/DropStone),
		list("dropores", "Drop all ores", null, 1, /obj/Hud/DropOres),
		list("dropgems", "Drop all gems", null, 1, /obj/Hud/DropGems),
		list("dropingots", "Drop all ingots", null, 1, /obj/Hud/DropIngots),
		list("dropfood", "Drop all food", null, 1, /obj/Hud/DropEdibles),
		list("dropbones", "Drop all bones", null, 1, /obj/Hud/DropBones),
		list("droparmour", "Drop all armour", null, 1, /obj/Hud/DropArmor),
		list("tearmeat", "Tear meat from carried corpses", null, 1, /obj/Hud/TearMeat),
		list("tearskin", "Tear skin from carried corpses", null, 1, /obj/Hud/TearSkin),
		list("build", "Build menu (needs stone or wood)", null, 0, /obj/Hud/Build),
		list("mental", "Illithid mental abilities", "F6", 1, null),
		list("magictarget", "Choose magic target", null, 1, null),
		list("area", "Select your units nearby", null, 0, /obj/Hud/Area),
		list("all", "Select all your units", "Ctrl+A", 0, /obj/Hud/All),
		list("clear", "Deselect · keep working", "Shift+Space", 0, null),
		list("waypoint", "Create or go to waypoint", null, 0, /obj/Hud/Way),
		list("jump", "Go to last unit under attack", "Backspace", 0, null),
		list("zup", "Camera up a level", ",", 0, /obj/Hud/ZUp),
		list("zdown", "Camera down a level", ".", 0, /obj/Hud/ZDown),
		list("coords", "Show my coordinates", null, 0, /obj/Hud/Cords),
		list("warp", "Go to coordinates", null, 0, /obj/Hud/Warp),
		list("race", "Choose your people / start over", null, 0, /obj/Hud/Restart),
		list("say", "Say to the world", null, 0, /obj/Hud/Say),
		list("msg", "Message a player", null, 0, /obj/Hud/MSG),
		list("worldchat", "World chat on/off", null, 0, null),
		list("clanchat", "Clan chat", null, 0, null),
		list("who", "Who is online", null, 0, /obj/Hud/Who),
		list("allyadd", "Add an ally", null, 0, null),
		list("allyremove", "Remove an ally", null, 0, null),
		list("allylist", "List allies", null, 0, null),
		list("legends", "Legends of the world", null, 0, null),
		// Only the Classic tabs had these; the modern HUD needs them now Classic is gone.
		list("createclan", "Create a clan", null, 0, null),
		list("clanmembers", "Check clan members", null, 0, null),
		list("shrines", "Check shrines", null, 0, null),
		list("tapestry", "Place or remove tapestries", null, 1, null),
		list("event", "Join the current event", null, 0, null),
		list("updates", "Game updates", null, 0, /obj/Hud/Updates),
		list("music", "Music off", null, 0, null),
		list("help", "Controls & Actions guide", "F3", 0, null))
	for(var/list/row in table)
		var/obj/RemasterAction/A = new
		A.action_id = row[1]
		A.name = row[2]
		A.key = row[3]
		A.needs_units = row[4]
		A.hud_type = row[5]
		remaster_action_list += A
	return remaster_action_list

obj/RemasterAction/proc/Run(mob/U)
	usr = U
	if(!istype(U, /Player)) return
	var/availability = U:RemasterCuratedActionReason(action_id)
	if(length(availability))
		U:RemasterNotice(availability)
		return 0
	if(action_id == "magictarget") return U:RemasterMagicTargetOpen()
	if(action_id == "mental")
		var/reason = U:RemasterMentalReason()
		if(length(reason))
			U:RemasterNotice(reason)
			return 0
		U.MindFlayer()
		return 1
	if(action_id in list("clear", "area", "all")) U:remaster_queue = 0
	if(needs_units && !length(U.Selected))
		U << "Select one or more of your units first."
		return
	if(action_id == "msg")
		U:RemasterMessage()
		return
	if(action_id == "warp")
		U:RemasterCoordinates()
		return
	if(copytext(action_id, 1, 5) == "pick" && action_id != "pickarrows")
		U:RemasterPickupNearby(src)
		return
	if(hud_type)
		var/item_type = RemasterItemType()
		var/before = item_type ? RemasterCarried(U, item_type) : 0
		var/nearby = (item_type && copytext(action_id, 1, 5) == "pick") ? RemasterNearby(U, item_type) : 0
		var/obj/Hud/H = new hud_type(new /datum/remaster_screen)
		H.DblClick()
		if(H) del(H)
		if(item_type) RemasterFeedback(U, before, RemasterCarried(U, item_type), nearby)
		return
	switch(action_id)
		if("guard") U.Guard()
		if("rename") U:RemasterRenameSelected()
		if("unitsay", "emote") U:RemasterSpeakSelected(action_id)
		if("leader") U:RemasterDeclareSelected()
		if("clear") U.Zip()
		if("jump") U:RemasterJump()
		if("worldchat") U.WorldChat()
		if("clanchat") U.ClanChat()
		if("allyadd") U.AddAlly()
		if("allyremove") U.RemoveAlly()
		if("allylist") U.ListAllies()
		if("legends") U.Legends()
		if("createclan") U.Create_A_Clan()
		if("clanmembers") U.Check_Clan_Members()
		if("shrines") U.Check_Shrines()
		if("tapestry") U.PlaceTapestry()
		if("event") U.EVENT()
		if("music") U.MusicOff()
		if("help") U:RemasterHelp()

// Feedback the original buttons never gave (they fail silently).
obj/RemasterAction/proc/RemasterItemType()
	var/list/types = list("wood"=/obj/Items/woods/wood, "stone"=/obj/Items/ores/stone, "ores"=/obj/Items/ores,
		"gems"=/obj/Items/gems, "ingots"=/obj/Items/Ingots, "food"=/obj/Items/Food, "bones"=/obj/Items/Bones,
		"skin"=/obj/Items/Skin, "seeds"=/obj/Items/Seeds, "armour"=/obj/Items/Equipment, "arrows"=/obj/Items/Arrows)
	var/prefix = copytext(action_id, 1, 5)
	if(prefix != "pick" && prefix != "drop") return null
	return types[copytext(action_id, 5)]

proc/RemasterCarried(mob/U, type)
	var/n = 0
	for(var/mob/Monsters/M in U.Selected) for(var/obj/O in M) if(istype(O, type)) n++
	return n

proc/RemasterNearby(mob/U, type)
	var/n = 0
	for(var/mob/Monsters/M in U.Selected) for(var/obj/O in oview(1, M)) if(istype(O, type) && !O.suffix) n++
	return n

obj/RemasterAction/proc/RemasterFeedback(mob/U, before, after, nearby)
	var/what = copytext(action_id, 5)
	if(copytext(action_id, 1, 5) == "drop")
		if(after == before) U << "Your selected units carry no [what]."
		else U << "Dropped [before - after] [what]."
	else if(after > before) U << "Picked up [after - before] [what]."
	else if(!nearby) U << "Nothing to pick up: no [what] next to your selected units."
	else U << "Could not pick up [what]. Check distance, carrying capacity, flight and material restrictions."

// --- The Actions tab ---------------------------------------------------------

Player
	var/tmp/remaster_actions_shown = 0

Player/Stat()
	if(!remaster_classic_info) return   // the classic Info pane is never shown (HUD.dm): its panels went every tick anyway, ~45 lines for each unit selected (world-look 2026-10-25: 200 selected, the client grew to 19 GB and lost the server)
	if(statpanel("Actions"))
		var/count = length(Selected)
		stat("Selected", count ? "[count] unit[count == 1 ? "" : "s"]" : "none (click, drag or press A)")
		if(count)
			stat("--- Selected units ---")
			for(var/obj/RemasterAction/A in RemasterActions()) if(A.needs_units) stat(A.key ? "\[[A.key]]" : "", A)
		stat("--- General ---")
		for(var/obj/RemasterAction/A in RemasterActions()) if(!A.needs_units) stat(A.key ? "\[[A.key]]" : "", A)
	return ..()

// Show the Actions tab once the player has an army (after login or race choice).
Player/proc/RemasterShowActions()
	if(remaster_actions_shown || !client || !length(UnitList)) return
	remaster_actions_shown = 1
	client.statpanel = "Actions"
	src << "Click your people or drag a box to select them; left-click a target to give orders, right-click for more choices. F3 opens the Guide."

// --- Single-click HUD buttons and action rows ----------------------------------

client
	var/tmp/atom/remaster_button_last
	var/tmp/remaster_button_time = -100

client/proc/RemasterButton(atom/A)
	// One run per click burst: a habitual double-click must not run it twice.
	if(A == remaster_button_last && world.time - remaster_button_time <= 5) return 1
	remaster_button_last = A
	remaster_button_time = world.time
	if(istype(A, /obj/HUD) && istype(mob, /Player)) return mob:RemasterPaletteRun(A:remaster_palette_id)
	if(istype(A, /obj/RemasterAction)) A:Run(mob)
	else
		if(istype(A, /obj/Hud) && istype(mob, /Player))
			for(var/list/C in RemasterBorderControls())
				if(A.type == text2path(C["hud_type"]))
					mob:RemasterBorderRun(C["id"])
					return 1
		A.DblClick()
	return 1

client/DblClick(atom/object, location, control, params)
	if((istype(object, /obj/Hud) || istype(object, /obj/HUD) || istype(object, /obj/RemasterAction) || istype(object, /mob/WorkShops)) && object == remaster_button_last && world.time - remaster_button_time <= 5)
		return
	return ..()

// Key bindings for actions without an original key (skin: "," "." F3).
Player/verb/RemasterDo(id as text)
	set hidden = 1
	for(var/obj/RemasterAction/A in RemasterActions()) if(A.action_id == id)
		A.Run(src)
		return

// --- Controls & Actions guide ------------------------------------------------

Player/verb/RemasterHelp()
	set hidden = 1
	remaster_hud_tab = "guide"
	remaster_help_serial++    // the page opens the Guide panel (Onboarding.dm)
	RemasterHUDShow()
	return
