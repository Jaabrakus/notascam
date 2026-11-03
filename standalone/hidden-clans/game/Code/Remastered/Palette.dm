// Larger controls for the *current* original build/ability menu. Requests name
// an existing screen object, never an arbitrary type or proc. Original handlers
// retain their menus, costs, racial restrictions and placement behavior.
Player
	var/tmp/list/remaster_palette_resources
	var/tmp/obj/HUD/remaster_palette_last
	var/tmp/remaster_palette_time = -100

obj/HUD
	var/tmp/remaster_palette_id
	var/tmp/list/remaster_palette_actors
	var/tmp/remaster_palette_hidden = 0
	var/tmp/remaster_palette_alpha
	var/tmp/remaster_palette_mouse
	New(client/C)
		. = ..()
		if(istype(C) && istype(C.mob, /Player))
			remaster_palette_id = RemasterUIRef(src)
			remaster_palette_actors = list()
			for(var/mob/Monsters/M in C.mob.Selected)
				if(M.Owner == C.mob && (M in C.mob.UnitList)) remaster_palette_actors[RemasterUIRef(M)] = "[M.Race]|[M.SubRace]|[M.IsMist]"

obj/HUD/proc/RemasterPaletteHide(hidden)
	if(hidden && !remaster_palette_hidden)
		remaster_palette_alpha = alpha
		remaster_palette_mouse = mouse_opacity
		alpha = 0
		mouse_opacity = 0
		remaster_palette_hidden = 1
	else if(!hidden && remaster_palette_hidden)
		alpha = remaster_palette_alpha
		mouse_opacity = remaster_palette_mouse
		remaster_palette_hidden = 0

Player/proc/RemasterRestorePalette()
	// HUDTick calls this before its browser-readiness early return. A browser
	// reload must restore the native buttons even when no HUD data is sent.
	if(client) for(var/obj/HUD/H in client.screen) H.RemasterPaletteHide(0)

Player/proc/RemasterPaletteReason(obj/HUD/H)
	if(!H || !client || !(H in client.screen) || !H.screen_loc || !length(H.name) || istype(H, /obj/HUD/Text)) return "Menu is no longer open."
	if(!length(Selected)) return "Select a unit, then reopen the build or ability menu."
	if(length(H.remaster_palette_actors) != length(Selected)) return "Selection changed; reopen the menu for these units."
	// Deletion leaves null slots in DM lists; typed mob iteration skips them.
	// Resolve every captured token so a vanished actor cannot leave a menu valid.
	for(var/reference in H.remaster_palette_actors)
		var/mob/Monsters/M = RemasterUIUnit(reference)
		if(!M || !(M in Selected) || M.HP <= 0 || M.GoingToDie || H.remaster_palette_actors[reference] != "[M.Race]|[M.SubRace]|[M.IsMist]") return "Selection changed; reopen the menu for these units."
	return ""

Player/proc/RemasterPaletteIcon(obj/HUD/H)
	if(!client || !H.icon) return ""
	if(!remaster_palette_resources) remaster_palette_resources = list()
	var/id = "[H.icon]|[H.icon_state]|[H.dir]"
	var/resource = remaster_palette_resources[id]
	if(!resource)
		resource = "remaster-palette-[remaster_palette_resources.len + 1].png"
		remaster_palette_resources[id] = resource
		src << browse_rsc(icon(H.icon, H.icon_state, H.dir, 1), resource)
	return resource

Player/proc/RemasterPaletteData()
	var/list/entries = list()
	var/list/seen = list()
	if(client)
		for(var/obj/HUD/H in client.screen)
			// Some racial menus construct unavailable buttons without positioning
			// them. Letter sprites have letter names, but are never commands.
			if(!H.screen_loc || !length(H.name) || istype(H, /obj/HUD/Text)) continue
			var/id = "[H.type]|[H.icon]|[H.icon_state]"
			if(id in seen) continue
			seen += id
			entries += list(list("ref"=H.remaster_palette_id, "label"="[H.name]", "icon"=RemasterPaletteIcon(H), "reason"=RemasterPaletteReason(H)))
		// Hide the original menu only while its larger replacement is ready.
		// Keep screen membership so the original submenu/Close code still works.
		for(var/obj/HUD/H in client.screen) H.RemasterPaletteHide(length(entries) && remaster_hud_ready && (!remaster_border_visible || remaster_3d))
	return list("open"=!!length(entries), "entries"=entries, "title"="Build & abilities")

Player/proc/RemasterPaletteRun(reference)
	if(!client || !reference) return 0
	// OpenDream may recycle deleted atom refs within a menu transition. Tokens
	// never repeat during this server session, so a stale tap cannot hit a
	// different new button which happened to receive the old atom reference.
	var/obj/HUD/H
	for(var/obj/HUD/candidate in client.screen)
		if(candidate.remaster_palette_id == reference)
			H = candidate
			break
	if(!H) return 0
	var/reason = RemasterPaletteReason(H)
	if(length(reason))
		RemasterNotice(reason)
		return 0
	// A second tap in the same burst must not duplicate an immediate craft.
	if(H == remaster_palette_last && world.time - remaster_palette_time <= 5) return 0
	remaster_palette_last = H
	remaster_palette_time = world.time
	usr = src
	RemasterNotice("[H.name]")
	H.DblClick()
	return 1

Player/proc/RemasterPaletteClose()
	Function = null
	Up = 0
	if(client) for(var/obj/HUD/H in client.screen) del(H)
	RemasterNotice("Menu closed. Assigned work continues.")
