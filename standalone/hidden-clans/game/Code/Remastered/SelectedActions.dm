// Prompts yield: commit only for the same eligible actors who opened them.
// Lifetime strings survive deleted atoms becoming null list slots.
datum/remaster_action_context
	var/Player/controller
	var/list/tokens = list()
	var/list/units = list()
	var/list/states = list()
	var/count = 0
	var/required_verb
	var/allow_free = 0

Player/proc/RemasterSelectedActor(mob/Monsters/M, allow_free = 0)
	return M && M.HP > 0 && !M.GoingToDie && ((M.Owner == src && RmInCompany(M)) || (allow_free && DE && FreeSelect))   // RmInCompany: HudView.dm

// Pure reasons: exporting availability never allocates actor IDs or prompts.
Player/proc/RemasterSelectedReason(required_verb, allow_free = 0)
	if(!(required_verb in verbs)) return "This command is unavailable."
	if(!length(Selected)) return "Select a unit first."
	if(!allow_free) return RmSelectionCheck() == 1 ? "" : "Select your own living units."   // the same test, once a tick (HudView.dm)
	for(var/entry in Selected)
		if(!istype(entry, /mob/Monsters) || !RemasterSelectedActor(entry,allow_free)) return "Select your own living units."
	return ""

proc/RemasterCuratedVerb(action)
	switch(action)
		if("guard") return /mob/verb/Guard
		if("rename") return /mob/verb/Rename
		if("unitsay") return /mob/verb/UnitSay
		if("emote") return /mob/verb/Emote
		if("leader") return /mob/verb/DeclareLeader
		if("mental") return /mob/verb/MindFlayer
		if("magictarget") return /Targeting/verb/SetTarget
		if("jump") return /Player/verb/RemasterJump
		if("worldchat") return /mob/verb/WorldChat
		if("clanchat") return /mob/verb/ClanChat
		if("allyadd") return /mob/verb/AddAlly
		if("allyremove") return /mob/verb/RemoveAlly
		if("allylist") return /mob/verb/ListAllies
		if("legends") return /mob/verb/Legends
		if("createclan") return /mob/verb/Create_A_Clan
		if("clanmembers") return /mob/verb/Check_Clan_Members
		if("shrines") return /mob/verb/Check_Shrines
		if("tapestry") return /mob/verb/PlaceTapestry
		if("event") return /mob/verb/EVENT
		if("music") return /mob/verb/MusicOff
	return null

Player/proc/RemasterCuratedActionReason(action)
	var/required_verb = RemasterCuratedVerb(action)
	if(required_verb && !(required_verb in verbs)) return "This command is unavailable."
	if(action in list("guard", "rename", "unitsay", "emote", "leader", "mental", "magictarget"))
		var/reason = RemasterSelectedReason(required_verb)
		if(length(reason)) return reason
	if(action == "mental") return RemasterMentalReason()
	if(action == "magictarget") return RemasterMagicTargetReason()
	if(action == "clanchat" && Faction == "Player") return "Join a clan before using clan chat."
	// Deselect and Help are harmless conveniences, not new verb grants.
	return ""

Player/proc/RemasterSelectedActionCapture(required_verb, allow_free = 0)
	if(length(RemasterSelectedReason(required_verb,allow_free))) return null
	var/datum/remaster_action_context/D = new
	D.controller = src
	D.required_verb = required_verb
	D.allow_free = allow_free
	D.count = length(Selected)
	for(var/mob/Monsters/M in Selected)
		if(!RemasterSelectedActor(M,allow_free)) return null
		var/reference = RemasterUIRef(M)
		D.tokens += reference
		D.units[reference] = M
		D.states[reference] = list("owner"=M.Owner, "race"=M.Race, "subrace"=M.SubRace, "mist"=M.IsMist, "royal"=M.IsRoyal, "gender"=M.Gender, "name"=M.name)
	if(length(D.tokens) != D.count) return null
	return D

Player/proc/RemasterSelectedActionCurrent(datum/remaster_action_context/D, require_selection = 1)
	if(!D || D.controller != src || !(D.required_verb in verbs) || length(D.tokens) != D.count) return 0
	if(require_selection && length(Selected) != D.count) return 0
	for(var/reference in D.tokens)
		var/mob/Monsters/M = D.units[reference]
		var/list/state = D.states[reference]
		if(!RemasterSelectedActor(M,D.allow_free) || M.remaster_ui_id != reference) return 0
		if(require_selection && !(M in Selected)) return 0
		if(M.Owner != state["owner"] || M.Race != state["race"] || M.SubRace != state["subrace"] || M.IsMist != state["mist"] || M.IsRoyal != state["royal"] || M.Gender != state["gender"] || M.name != state["name"]) return 0
	return 1

Player/proc/RemasterSelectedText(message, title, default = null)
	return input(src, message, title, default) as text|null

mob/proc/RemasterLeaderChoice(recipient, message, title)
	return alert(recipient, message, title, "Yes", "No")

Player/proc/RemasterRenameSelected(allow_free = 0)
	var/datum/remaster_action_context/D = RemasterSelectedActionCapture(/mob/verb/Rename,allow_free)
	if(!D) return 0
	usr = src
	for(var/reference in D.tokens)
		if(!RemasterSelectedActionCurrent(D)) return 0
		var/mob/Monsters/M = D.units[reference]
		var/TITLE = M.IsRoyal ? M.RmTitle() : null   // the ruler's chosen title (Rulership.dm)
		var/PrefixLength=length("[M.Owner]")+4
		if(TITLE) PrefixLength+=length(TITLE)+1
		var/NAME
		if(copytext(M.name,1,PrefixLength) == "[TITLE] {[M.Owner]} " || copytext(M.name,1,PrefixLength) == "{[M.Owner]} ")
			NAME=RemasterSelectedText("Rename your [M.Gender] [M.Race] to what?","Rename","[copytext(M.name,PrefixLength,0)]")
		else NAME=RemasterSelectedText("Rename your [M.Gender] [M.Race] to what?","Rename","[M.name]")
		if(!RemasterSelectedActionCurrent(D)) return 0
		if(NAME)
			NAME = RmModFilter(NAME)   // the admins' word list (Moderation.dm, A4)
			if(length(NAME)>25)
				usr<<"This name is far too long. Try a shorter one."
				continue
			if(TITLE) M.name="[TITLE] {[M.Owner]} [NAME]"
			else M.name="{[M.Owner]} [NAME]"
			var/list/state = D.states[reference]
			state["name"] = M.name
	return 1

Player/proc/RemasterSpeakSelected(action)
	var/required_verb = action == "unitsay" ? /mob/verb/UnitSay : /mob/verb/Emote
	var/datum/remaster_action_context/D = RemasterSelectedActionCapture(required_verb)
	if(!D) return 0
	var/T = RemasterSelectedText(action == "unitsay" ? "What should your unit say?" : "What should your unit do?", action == "unitsay" ? "Speak through a unit" : "Unit emote")
	if(!T || !RemasterSelectedActionCurrent(D)) return 0
	usr = src
	if(action == "unitsay") UnitSay(T)
	else Emote(T)
	return 1

Player/proc/RemasterDeclareSelected(allow_free = 0)
	var/datum/remaster_action_context/D = RemasterSelectedActionCapture(/mob/verb/DeclareLeader,allow_free)
	if(!D) return 0
	usr = src
	for(var/reference in D.tokens)
		if(!RemasterSelectedActionCurrent(D)) return 0
		var/mob/Monsters/M = D.units[reference]
		if(M.IsRoyal)
			if(M.RemoveLeader(D)) return 1
		else if(M.AddLeader(null,D)) return 1
	return 0

mob/proc/RemasterCrownSnapshot()
	var/list/state = list()
	for(var/obj/Items/Equipment/I in src) if(I.ItemType == "Crown")
		state[RemasterUIRef(I)] = list("item"=I, "suffix"=I.suffix, "name"=I.name)
	return state

mob/proc/RemasterCrownsCurrent(list/state)
	var/count = 0
	for(var/obj/Items/Equipment/I in src) if(I.ItemType == "Crown") count++
	if(count != length(state)) return 0
	for(var/reference in state)
		var/list/old = state[reference]
		var/obj/Items/Equipment/I = old["item"]
		if(!I || I.remaster_ui_id != reference || I.loc != src || I.ItemType != "Crown" || I.suffix != old["suffix"] || I.name != old["name"]) return 0
	return 1
