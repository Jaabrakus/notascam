// Original numbered control groups, shared by keyboard and touch controls.
// Group membership remains temporary, exactly like the original Quick verb.
datum/remaster_group_selection
	var/list/tokens = list()
	var/list/units = list()   // the same units (checked by mark: a ref lookup each for 30,000 selected was ~150 ms a send)
	var/count = 0

Player
	var/tmp/datum/remaster_group_selection/remaster_group_selection
	var/tmp/list/remaster_group_recalled = list()
	var/tmp/remaster_group_recalled_number = 0
	var/tmp/remaster_group_until = -1
	var/tmp/remaster_group_press = 0

Player/proc/RemasterGroupNumber(number)
	return isnum(number) && number >= 1 && number <= 9 && round(number) == number

// in the company by its mark (HudView.dm RmCompanyMark): "M in UnitList" searched the whole company for each member and
// each selected unit, every send (select all at 30,000: 9.3 s a send; hud-craft, 10-24)
Player/proc/RemasterGroupActor(mob/Monsters/M)
	return M && M.Owner == src && (M.rm_hud_umark == RmCompanyMark() || (M in UnitList)) && M.HP > 0 && !M.GoingToDie

Player/proc/RemasterGroupMembers(number)
	var/list/members = list()
	if(!RemasterGroupNumber(number)) return members
	var/list/old = vars["Group[number]"]
	var/dk = ++rm_hud_serial   // "M in members" made a big group's check square in its size: a mark (HudView.dm; hud-craft, 10-24)
	for(var/mob/Monsters/M in old)
		if(M.rm_hud_dmark != dk && RemasterGroupActor(M))
			M.rm_hud_dmark = dk
			members += M
	// Remove deleted/transferred members before either exporting names or recall.
	vars["Group[number]"] = members
	return members

Player/proc/RemasterGroupSelectionCurrent(datum/remaster_group_selection/D)
	if(!D || length(Selected) != D.count) return 0
	// "M in Selected" for each one was square in the selection: the selection marked once (HudView.dm rm_hud_serial)
	var/sk = ++rm_hud_serial
	for(var/mob/Monsters/S in Selected) S.rm_hud_smark = sk
	// the captured units themselves, all still selected (counted, so a deleted one the loop skips fails the check)
	if(length(D.units) == D.count)
		var/hit = 0
		for(var/mob/Monsters/M in D.units)
			if(!RemasterGroupActor(M) || M.rm_hud_smark != sk) return 0
			hit++
		return hit == D.count
	// Token strings cannot disappear into null slots when an actor is deleted.
	for(var/reference in D.tokens)
		var/mob/Monsters/M = RemasterUIUnit(reference)
		if(!RemasterGroupActor(M) || M.rm_hud_smark != sk) return 0
	return 1

Player/proc/RemasterGroupSelectionCapture()
	var/datum/remaster_group_selection/D = new
	D.count = length(Selected)
	for(var/mob/Monsters/M in Selected)
		if(!RemasterGroupActor(M)) return null
		D.tokens += RemasterUIRef(M)
		D.units += M
	if(length(D.tokens) != D.count) return null
	return D

Player/proc/RemasterControlGroupsData()
	if(!RemasterGroupSelectionCurrent(remaster_group_selection)) remaster_group_selection = RemasterGroupSelectionCapture()
	var/reason = !length(Selected) ? "Select units first." : !remaster_group_selection ? "Selection changed; select your own living units." : ""
	var/list/groups = list()
	for(var/number = 1, number <= 9, number++)
		var/list/members = RemasterGroupMembers(number)
		var/list/names = list()
		for(var/mob/Monsters/M in members)   // the first 12 (the page shows them as a short line; "count" is the size)
			names += "[M.name]"
			if(length(names) >= 12) break
		groups += list(list("number"=number, "count"=length(members), "names"=names, "reason"=(length(members) ? "" : "No units saved in this group.")))
	return list("selection"=(length(reason) ? "" : RemasterUIRef(remaster_group_selection)), "selectedCount"=length(Selected), "setReason"=reason, "addReason"=reason, "groups"=groups)

Player/proc/RemasterGroupRecallCurrent(number, list/members)
	if(remaster_group_recalled_number != number || !length(remaster_group_recalled) || length(Selected) != length(remaster_group_recalled)) return 0
	for(var/reference in remaster_group_recalled)
		var/mob/Monsters/M = RemasterUIUnit(reference)
		if(!RemasterGroupActor(M) || !(M in Selected) || !(M in members)) return 0
	return 1

Player/proc/RemasterQuick(number, action)
	if(!RemasterGroupNumber(number) || !(action in list("Set", "Add", "Select"))) return 0
	// Legacy developer FreeSelect remains usable outside owned-only groups.
	if(action != "Select")
		for(var/mob/Monsters/M in Selected) if(!RemasterGroupActor(M)) return 0
	RemasterNormalizeSelection()
	var/list/members = RemasterGroupMembers(number)
	switch(action)
		if("Set")
			members = Selected.Copy()
			vars["Group[number]"] = members
		if("Add")
			for(var/mob/Monsters/M in Selected) if(!(M in members)) members += M
		if("Select")
			// Retain the original three-tick repeat-to-center behavior, but only
			// for the exact surviving selection made by the preceding recall.
			if(LastQuickButtonPress == "[number]Select" && world.time < remaster_group_until && RemasterGroupRecallCurrent(number, members))
				for(var/mob/Monsters/M in Selected)
					if(isturf(M.loc))
						loc = locate(M.x, M.y, RmViewLayer(M))   // its level's view (Peaks.dm)
						RemasterCamTo(M)
						return 1
			for(var/mob/Monsters/M in Selected.Copy()) M.Deselect(src)
			Selected = list()
			for(var/mob/Monsters/M in members) M.Select(src)
			remaster_queue = 0
			remaster_group_recalled = list()
			remaster_group_recalled_number = number
			for(var/mob/Monsters/M in Selected) remaster_group_recalled += RemasterUIRef(M)
	LastQuickButtonPress = "[number][action]"
	remaster_group_until = world.time + 3
	var/press = ++remaster_group_press
	spawn(3)
		if(remaster_group_press == press) LastQuickButtonPress = null
	if(action == "Select" && !length(members)) RemasterNotice("Group [number] is empty: Ctrl+[number] saves the selected units as group [number].")
	else RemasterNotice(action == "Select" ? "Group [number]: [length(Selected)] selected. Assigned work continues." : "Group [number]: [length(members)] unit\s. Groups last for this session.")
	return 1

Player/proc/RemasterControlGroupRequest(value)
	if(!istext(value)) return 0
	var/list/parts = splittext(value, "|")
	if(parts.len != 3) return 0
	var/number = text2num(parts[1])
	if(!RemasterGroupNumber(number) || "[number]" != parts[1]) return 0
	var/action = parts[2]
	if(!(action in list("Set", "Add", "Select"))) return 0
	if(action != "Select")
		var/datum/remaster_group_selection/D = remaster_group_selection
		if(!D || !length(D.tokens) || parts[3] != D.remaster_ui_id || !RemasterGroupSelectionCurrent(D))
			RemasterNotice("Selection changed; choose the units again before saving a group.")
			return 0
	return RemasterQuick(number, action)

// Z (skin.dmf "Goto"): the camera to the middle of the selection on this layer (the original went to the last
// selected unit's tile), and the 3D view there at once.
Player/Goto()
	var/n = 0
	var/sx = 0
	var/sy = 0
	var/sz = 0
	for(var/mob/Monsters/M in Selected)
		if(!isturf(M.loc) || (sz && M.z != sz)) continue
		sz = M.z
		sx += M.x
		sy += M.y
		n++
	if(!n) return ..()
	var/turf/T = locate(round(sx / n + 0.5), round(sy / n + 0.5), sz)
	if(!T) return ..()
	loc = T
	RemasterCamTo(T)

// F1 (skin.dmf): the next idle unit, selected, with the camera on it (the HUD's Next idle).
Player/verb/RemasterNextIdleVerb()
	set name = "Remaster-Next-Idle"
	set hidden = 1
	set instant = 1
	RemasterNextIdle()
