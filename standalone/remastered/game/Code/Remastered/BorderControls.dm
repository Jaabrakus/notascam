// Labeled access to the original permanent map controls. This trusted local
// catalog is the only source of runnable HUD types; requests supply an ID only.
var/list/remaster_border_controls

proc/RemasterBorderControls()
	if(!remaster_border_controls)
		remaster_border_controls = json_decode(file2text('Interface/border-controls.json'))
	return remaster_border_controls

proc/RemasterBorderControl(id)
	for(var/list/C in RemasterBorderControls()) if(C["id"] == id) return C

proc/RemasterBorderGroups()
	return list(list("id"="units", "label"="Units"), list("id"="gather", "label"="Gather & inventory"), list("id"="build", "label"="Build & terrain"), list("id"="camera", "label"="Camera & world"), list("id"="people", "label"="People & settings"))

Player
	var/remaster_border_visible = 0
	var/remaster_border_layout_version = 0
	var/tmp/list/remaster_border_resources

Player/proc/RemasterInitBorderLayout()
	// Upgrade older profiles once. Subsequent Show/Hide choices survive loading.
	if(remaster_border_layout_version < 1)
		remaster_border_visible = 0
		remaster_border_layout_version = 1

obj/Hud
	var/tmp/remaster_border_hidden = 0
	var/tmp/remaster_border_alpha
	var/tmp/remaster_border_mouse

obj/Hud/proc/RemasterBorderHide(hidden)
	if(hidden && !remaster_border_hidden)
		remaster_border_alpha = alpha
		remaster_border_mouse = mouse_opacity
		alpha = 0
		mouse_opacity = 0
		remaster_border_hidden = 1
	else if(!hidden && remaster_border_hidden)
		alpha = remaster_border_alpha
		mouse_opacity = remaster_border_mouse
		remaster_border_hidden = 0

Player/proc/RemasterApplyBorder()
	RemasterInitBorderLayout()
	if(!client) return
	// Keep these objects in client.screen: original autodig and day/night code
	// updates them there. Uppercase /obj/HUD build/magic menus stay usable.
	// Keep the working border available until the replacement browser is ready.
	// In 3D the map is covered, so the HUD's own controls always stand in for these.
	for(var/obj/Hud/H in client.screen) H.RemasterBorderHide(remaster_hud_ready && (!remaster_border_visible || remaster_3d))

Player/proc/RemasterBorderIcon(id)
	var/name = "remaster-border-[id].png"
	if(client)
		if(!remaster_border_resources) remaster_border_resources = list()
		if(!(id in remaster_border_resources))
			src << browse_rsc(file("Interface/border-icons/[id].png"), name)
			remaster_border_resources += id
	return name

Player/proc/RemasterBorderData()
	RemasterInitBorderLayout()
	var/list/controls = list()
	for(var/list/C in RemasterBorderControls())
		var/id = C["id"]
		var/active = 0
		if(id == "digpaint") active = (Function in list("PlaceAutodig", "RemoveAutodig"))
		if(id == "digadd") active = Function == "PlaceAutodig"
		if(id == "digremove") active = Function == "RemoveAutodig"
		var/icon_id = id == "daynight" ? "daynight-[night ? "moon" : "sun"]" : id
		var/reason = C["needs_units"] && !length(Selected) ? "Select a unit first" : ""
		if(id in list("digadd", "digremove"))
			if(!(Function in list("PlaceAutodig", "RemoveAutodig"))) reason = "Enable autodig marking first"
		controls += list(list("id"=id, "label"=C["label"], "description"=C["description"],
			"key"=C["key"], "edge"=C["edge"], "position"=C["position"], "group"=C["group"],
			"icon"=RemasterBorderIcon(icon_id), "indicator"=C["indicator"], "reason"=reason, "active"=active, "selectionBound"=(C["needs_units"] || id == "build")))
	return list("visible"=remaster_border_visible, "controls"=controls, "groups"=RemasterBorderGroups(), "period"=(night ? "Night" : "Day"))

// The border as the HUD sends it, kept while what it reads stands: Show/Hide, the mode (autodig marking), day or night,
// whether anything is selected, and the client (its icons go to that client). It was built and encoded every send for
// every player, ~2.9 ms and ~230 KB a send, for a list that hardly changes (the Q9 web test's slow ticks, 10-31). The
// same list goes while it is kept, so the send reuses its encoded text (HUD.dm RemasterHUDKeysDelta).
Player/var/tmp/rm_border_key
Player/var/tmp/list/rm_border_kept
Player/proc/RemasterBorderDataKept()
	RemasterInitBorderLayout()
	var/k = "[remaster_border_visible]|[Function]|[night]|[length(Selected) ? 1 : 0]|\ref[client]"
	if(k == rm_border_key && rm_border_kept) return rm_border_kept
	rm_border_key = k
	rm_border_kept = RemasterBorderData()
	return rm_border_kept

Player/proc/RemasterBorderRun(id)
	var/list/C = RemasterBorderControl(id)
	if(!C || C["indicator"]) return 0
	if(C["needs_units"] && !length(Selected))
		RemasterNotice("Select a unit first.")
		return 0
	if(id in list("digadd", "digremove"))
		if(!(Function in list("PlaceAutodig", "RemoveAutodig")))
			RemasterNotice("Enable autodig marking first, then choose Add or Remove marks.")
			return 0
	var/T = text2path(C["hud_type"])
	if(!ispath(T, /obj/Hud)) return 0
	usr = src
	// These two old shortcuts omitted required prompt arguments. Use the same
	// existing safe wrappers as the Actions panel, without changing their intent.
	if(id == "msg")
		RemasterMessage()
		return 1
	if(id == "warp")
		RemasterCoordinates()
		return 1
	var/obj/Hud/H
	if(client) for(var/obj/Hud/candidate in client.screen)
		if(candidate.type == T)
			H = candidate
			break
	var/temporary = !H
	if(!H) H = new T(new /datum/remaster_screen)
	// Preserve the original pickup/harvesting/equipment rules. Some border
	// actions intentionally differ from the simplified nearby-resource buttons.
	RemasterNotice(C["label"])
	H.DblClick()
	if(temporary && H) del(H)
	return 1
