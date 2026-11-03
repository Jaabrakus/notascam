// Touch-first HUD. Browser links are requests; all ownership, costs and game
// effects are checked here on the server. No client-supplied proc/type calls.
Player
	var/tmp/remaster_hud_started = 0
	var/tmp/remaster_hud_ready = 0
	var/tmp/remaster_hud_tab = "units"
	var/tmp/remaster_log_open = 0
	var/tmp/remaster_map_sent = 0
	var/tmp/list/remaster_portraits
	var/tmp/remaster_hud_last
	var/tmp/list/remaster_hud_unit_codes   // unit ref -> its entry's parts as last sent (null: the next send is a full model)
	var/tmp/remaster_hud_sends = 0
	var/tmp/remaster_hud_sent_z = 0
	var/tmp/list/remaster_hud_key_codes     // top-level key -> its JSON as last sent
	var/tmp/list/rm_hud_key_objs            // a kept key (rm_hud_kept_keys) -> the list its JSON as last sent was made from
	var/tmp/list/rm_hud_key_objs_next       // the same for the model being made, until it goes
	var/tmp/remaster_hud_order_last          // the unit refs, in order, as last sent
	var/tmp/remaster_units_page = 0          // the page's Units page is open (it says so: "unitspage")
	var/remaster_tutorial_hidden = 0
	var/tmp/remaster_idle_last

var/list/remaster_maps = list()

Player
	var/tmp/remaster_classic_info = 0

Player/proc/RemasterHUDShow()
	if(!client) return
	// The map fills the window and the HUD (mapwindow.hud) is a transparent
	// layer over it. The game log and Classic info tabs share an optional strip
	// under the map, hidden until the player opens one of them.
	winset(src, "mainwindow.mainvsplit", "is-vert=false;left=mapwindow;right=rpane")
	winset(src, "rpanewindow", "is-vert=true;left=outputwindow;right=infowindow")
	remaster_log_open = 0
	remaster_classic_info = 0
	RemasterLayoutPanes()
	if(!remaster_hud_started)
		remaster_hud_started = 1
		RemasterClaimWorld()
		client.view = "33x19"
		// Remastered is always played in 3D.
		remaster_3d = 1
		spawn(5) RemasterFitView()
		remaster_hud_unit_codes = null   // a new page: its first model is a full one
		// Permanent border commands live in the labeled command dock. Original
		// contextual build/magic palettes remain separate and available.
		src << browse(RmHudPackPage(RemasterHUDPage(src)), "window=mapwindow.hud")   // the page with its sound engine and recordings (Audio.dm) and its unpacker (HudPack.dm)
	else RemasterHUDTick()

// The old 2D map under the 3D view goes once the page's 3D view runs (its first "view3dsize") (fps60 10-27; the owner:
// "i think we need to remove the 2d tiles in the back ground right? when i try to reseize the screen i can see the 2d
// tiles"). Hidden, the client stops drawing it: unseen under the 3D view, it took about a quarter of the game's GPU time
// every frame, and a resize showed its tiles at the edge before the page caught up. In 3D the page claims every click
// (click3d, View3D.dm) and the skin's keys run through the client's own key system, so neither goes through this
// control. Its on-hide would take the map window (and the HUD in it) out of the split, so that is cleared first.
// RM_KEEP_2D=1 in the server's environment keeps it: the real-client checks that click through the 2D map itself
// (the native UI probe's map clicks).
var/remaster_keep_2d = -1
Player/var/tmp/client/remaster_2d_hidden
Player/proc/RemasterHide2DMap()
	if(remaster_keep_2d < 0) remaster_keep_2d = world.GetConfig("env", "RM_KEEP_2D") == "1"
	if(remaster_keep_2d || !client || remaster_2d_hidden == client) return
	remaster_2d_hidden = client
	winset(src, "mapwindow.map", "on-hide=;is-visible=false")

// With the HUD layered over a full-window map, widen the view to the window's
// shape (19 tiles tall, as before) so the map fills the screen edge to edge.
Player/proc/RemasterFitView()
	if(!client) return
	var/list/parts = splittext("[winget(src, "mapwindow.map", "size")]", "x")
	if(!client || length(parts) < 2) return
	var/w = text2num(parts[1])
	var/h = text2num(parts[2])
	if(!w || !h) return
	var/cols = max(25, min(45, round(19 * w / h)))
	if(!(cols % 2)) cols++
	if(client.view != "[cols]x19") client.view = "[cols]x19"

Player/proc/RemasterLayoutPanes()
	if(!client) return
	remaster_log_open = 0    // the HUD's Log (remastered.html) replaces the native output pane
	if(!remaster_log_open && !remaster_classic_info)
		winset(src, "mainwindow.mainvsplit", "splitter=100")
		return
	winset(src, "mainwindow.mainvsplit", "splitter=74")
	winset(src, "rpanewindow", "splitter=[remaster_classic_info ? (remaster_log_open ? 40 : 0) : 100]")

// With spread (the track's runs, Spread.dm), the units are built over ticks and the model is sent from a fresh one.
// A unit's fields that change most (a step, a blow, a meal, a click on it): every unit's go as one small array, "hot", in
// the units' order, so a step doesn't send the rest of its entry again. Kept in this order on the page (remastered.html).
var/list/rm_hud_hot = list("x", "y", "z", "hp", "fullness", "energy", "selected")

// The parts of a unit's HUD entry that go on their own when they change (big ones, slow to change, or only filled for
// one unit); everything else in the entry goes as one part (RemasterHUDTick).
var/list/rm_hud_unit_parts = list("skills"=1, "stats"=1, "items"=1, "autouse"=1, "special"=1, "defense"=1, "pending"=1,
	"active"=1, "resume"=1, "events"=1, "toolTiers"=1, "look"=1, "captive"=1, "warnings"=1, "thoughts"=1, "family"=1,
	"captures"=1, "health"=1, "nearby"=1, "selfuses"=1, "abilities"=1, "moves"=1, "wmana"=1, "alchemy"=1, "cauldron"=1, "market"=1,
	"food"=1, "clinic"=1, "table"=1, "tavern"=1, "cave"=1, "runes"=1, "keeper"=1, "chakra"=1)

Player/var/tmp/remaster_3d_cam_seq = 0   // the page's last camera send applied (its count; HUD.dm "camera", View3D.dm "jump")
Player/proc/RemasterHUDTick(spread = 0)
	if(!client) return
	RemasterApplyBorder()
	if(!remaster_hud_ready) RemasterRestorePalette()
	if(!remaster_hud_started)
		RemasterHUDShow()
		return
	if(!remaster_hud_ready) return
	remaster_hud_live = 1   // the sends' own build: units' entries may be kept between sends (HudView.dm RmHudEntry)
	var/list/D = RemasterHUDData(spread)
	remaster_hud_live = 0
	if(spread) RmTrackPause()
	// a full model after the page (re)loads and when it says it missed one ("hudfull"); changes otherwise, on another
	// level too (the units are all of them on any level, and the minimap goes as "terrain" when the level changes). No
	// timed one: the user, 10-24, the full model is the big send
	var/full = !remaster_hud_unit_codes
	var/list/codes = RemasterHUDUnitsDelta(D, spread, full)
	var/list/keys = RemasterHUDKeysDelta(D, full)
	var/encoded = json_encode(D)
	if(encoded == remaster_hud_last) return   // nothing changed since the last send (an idle army sends nothing)
	remaster_hud_last = encoded
	remaster_hud_unit_codes = codes
	remaster_hud_key_codes = keys
	rm_hud_key_objs = rm_hud_key_objs_next
	remaster_hud_order_last = codes["#order"]
	remaster_hud_sent_z = z
	remaster_hud_sends++
	RemasterHUDSend(encoded)   // packed for a page that unpacks (HudPack.dm)

// The model's other keys as changes (the page carries the rest over from the last model, remastered.html updateHUD): only
// those whose value changed go, and "_goneKeys" lists keys it had and hasn't now. With 200 units standing still a model
// was ~66 KB of the same settlement, border, commands and so on, twice a second. "terrain" (the minimap, sent when it
// changes) is never carried over. Returns each key's JSON as sent.
// Keys whose lists are kept between sends while what they show stands, and never changed in place (a new list when it
// changes): while the model carries the very list the last send's JSON was made from, that JSON is the key's, unencoded.
// Text is the same: an equal text's JSON is the one made last time (the explored map's ~2 KB, every send). Encoding
// every key to compare it was most of a send's cost: the border's ~15 KB alone ~2.4 ms (the Q9 web test, 10-31).
var/list/rm_hud_kept_keys = list("border"=1, "commands"=1, "icons"=1, "questCard"=1, "quests"=1)

Player/proc/RemasterHUDKeysDelta(list/D, full)
	var/list/codes = list()
	var/list/objs = list()
	for(var/k in D.Copy())
		if(k in list("units", "unitOrder", "unitsDelta", "hot", "hotd", "terrain")) continue
		var/V = D[k]
		if((rm_hud_kept_keys[k] && islist(V)) || (istext(V) && length(V) > 64))
			objs[k] = V
			if(rm_hud_key_objs && rm_hud_key_objs[k] == V && remaster_hud_key_codes && !isnull(remaster_hud_key_codes[k]))
				codes[k] = remaster_hud_key_codes[k]
				if(!full) D -= k
				continue
		codes[k] = json_encode(V)
		if(!full && remaster_hud_key_codes && codes[k] == remaster_hud_key_codes[k]) D -= k
	if(!full && remaster_hud_key_codes)
		var/list/gone = list()
		for(var/k in remaster_hud_key_codes) if(isnull(codes[k])) gone += k
		if(length(gone)) D["_goneKeys"] = gone
		D["keysDelta"] = 1
	rm_hud_key_objs_next = objs
	return codes

// The units as changes (the page merges them before anything reads the model, remastered.html updateHUD): a unit
// whose entry changed since the last send goes with only the parts that changed ("_p"; the rest of it stays as the page
// has it, and "_gone" lists keys it no longer has), and every unit's ref goes in order. With 200 units selected a full
// model was 1.4 MB twice a second, and a unit taking a step resent its whole entry. A full model still goes after the
// page (re)loads, when the page asks, and when the changes would be more than half of it. An empty
// part (null) isn't sent at all: the page reads a missing key as it read null, and "_gone" drops one that empties. The
// units' fast fields (rm_hud_hot) go as rows ("hotd") only for the units whose row changed. Changes D's units in place;
// returns each unit's parts as sent, which RemasterHUDTick keeps once the model really goes.
Player/proc/RemasterHUDUnitsDelta(list/D, spread = 0, full = 0)
	var/list/units = D["units"]
	// the entries' codes and, unless full, the changed entries against the last send: in the engine (RmHud.cs, native
	// version 30: the same to the byte, without the DM's ~7 us a kept entry and ~50-100 us an entry encoded again; U5's
	// rest, 10-31) or, on an older engine or with RM_HUD_NATIVE=0, in DM (RmHudUnitsPass)
	// The engine keeps each unit's codes while their values stand (RmHud.cs, the owner, 10-31: "Yes, do it"): 88% of the
	// parts encoded again at 100 players came out as before; RM_HUD_KEEP=0 encodes every one, RM_HUD_KEEP_VERIFY=1 checks
	var/list/N = RmHudNative() ? rm_hud_units(units, remaster_hud_unit_codes, rm_hud_unit_parts, rm_hud_hot, full) : null
	if(!N) N = RmHudUnitsPass(units, spread, full)
	var/list/codes = N[1]          // ref -> list(part -> JSON); "" is the part with everything not in rm_hud_unit_parts
	var/list/order = N[2]          // every unit's ref, in order
	var/list/moved = N[3]          // the units whose hot row isn't as last sent (by place in the order), for "hotd"
	var/full_bytes = N[4]
	if(!full)
		var/list/changed = N[5]
		var/bytes = N[6]
		if(bytes * 2 <= full_bytes)
			D["units"] = changed
			if(codes["#order"] != remaster_hud_order_last) D["unitOrder"] = order   // the page keeps the last order otherwise
			D["unitsDelta"] = 1
			// only the hot rows not as last sent, each with its place in the order (from 0): the page keeps every other
			// unit's (remastered.html updateHUD). Every unit's went whenever one had changed: with 50 of 200 walking,
			// ~95% of what a HUD send carried (U5's rest, 10-31)
			if(length(moved))
				var/list/hd = list()
				for(var/n in moved)
					var/list/U = units[n]
					hd += list(list(n - 1, U["x"], U["y"], U["z"], U["hp"], U["fullness"], U["energy"], U["selected"]))
				D["hotd"] = hd
	return codes

// The units delta's pass in DM (RemasterHUDUnitsDelta, when the engine has no rm_hud_units): each entry's hot row as
// text, a kept entry's codes reused, any other encoded part by part; then, unless full, each against the last send.
// list(codes, order, moved, full bytes, changed entries or null, their size), as the engine's.
Player/proc/RmHudUnitsPass(list/units, spread = 0, full = 0)
	var/list/codes = list()        // ref -> list(part -> JSON); "" is the part with everything not in rm_hud_unit_parts
	var/list/order = list()        // every unit's ref, in order
	var/list/moved = list()        // the units whose hot row isn't as last sent (by place in the order), for "hotd"
	var/full_bytes = 0
	var/i = 0
	for(var/list/U in units)
		i++
		var/r = U["ref"]
		order += r
		// its hot row as text, rm_hud_hot's fields in order (as jointext made it of them)
		var/hot = "[U["x"]],[U["y"]],[U["z"]],[U["hp"]],[U["fullness"]],[U["energy"]],[U["selected"]]"
		// a kept entry (HudView.dm RmHudEntry): its parts as encoded last time; only its hot row is new
		var/reused = U["#r"]
		if(reused) U -= "#r"
		var/list/was = remaster_hud_unit_codes ? remaster_hud_unit_codes[r] : null
		if(was && hot != was["hot"]) moved += i
		if(reused && was && was["#n"])
			// the last send's codes list itself, its hot row rewritten (no copy of each, 200 a send): the comparison below
			// then has nothing to compare
			if(hot != was["hot"]) was["hot"] = hot
			codes[r] = was
			full_bytes += was["#n"]
			if(spread) RmTrackPause()
			continue
		var/list/C = list()
		var/list/rest = U.Copy()
		for(var/k in rm_hud_unit_parts) if(k in U)
			rest -= k
			if(isnull(U[k]))
				U -= k
				continue
			C[k] = json_encode(U[k])
			full_bytes += length(C[k])
		for(var/k in rm_hud_hot) rest -= k
		C["hot"] = hot
		C[""] = json_encode(rest)
		C["#"] = jointext(U, "|")      // its keys: some are only there sometimes (Formations.dm's ownPace)
		full_bytes += length(C[""])
		var/nb = 0
		for(var/k in C) if(k != "#" && k != "hot") nb += length(C[k])
		C["#n"] = max(1, nb)           // its parts' size, for a kept entry's share of full_bytes
		codes[r] = C
		if(spread) RmTrackPause()
	codes["#order"] = jointext(order, "|")
	var/list/changed
	var/bytes = 0
	if(!full)
		changed = list()
		var/list/olds = remaster_hud_unit_codes
		for(var/list/U in units)
			var/r = U["ref"]
			var/list/C = codes[r]
			var/list/old = olds[r]
			// a kept entry's codes are the last send's own list: every part as it was (its hot row is noted above). Most
			// of the company most sends (200 units: each part of each compared again, ~2.7 ms a send; U5's rest, 10-31)
			if(C == old) continue
			if(!old)
				changed += list(U)
				for(var/k in C) if(k != "#n") bytes += length(C[k])
				continue
			var/list/P
			for(var/k in C) if(k != "#" && k != "hot" && k != "#n" && C[k] != old[k])
				if(!P) P = list("ref"=r, "_p"=1)
				bytes += length(C[k])
				if(k == "")
					for(var/f in U) if(!rm_hud_unit_parts[f] && !(f in rm_hud_hot)) P[f] = U[f]
				else P[k] = U[k]
			if(C["#"] != old["#"])
				// keys it had and hasn't now: the page drops them ("_gone")
				var/list/gone = splittext(old["#"], "|") - splittext(C["#"], "|")
				if(length(gone))
					if(!P) P = list("ref"=r, "_p"=1)
					P["_gone"] = gone
			if(P) changed += list(P)
	return list(codes, order, moved, full_bytes, changed, bytes)

// Portraits use the unit's real appearance; they never rebuild equipment or
// alter a unit's dir, location, icon or overlay list. Cache values retain actual
// appearances/resources, not recyclable string refs.
var/list/remaster_portrait_images = list()
// a layer's cell and whether it is opaque, kept per sheet and state ("md5:state" -> list(cell, 1 opaque or 0)): they
// depend on nothing else, and each new portrait cut every layer again and read its 1,024 pixels (hud-craft, 10-25)
var/list/remaster_portrait_cells = list()
var/remaster_portrait_serial = 0
mob/Monsters
	var/tmp/remaster_portrait_appearance
	var/tmp/remaster_portrait_south   // that look facing south, as the portrait shows it whatever way the unit faces (hud-craft)
	var/tmp/list/remaster_portrait_record
	var/tmp/remaster_portrait_serial = 0

proc/RemasterPortraitCell(source, state)
	if(!(state in icon_states(source))) state = ""
	var/icon/I = icon(source, state, SOUTH, 1, 0)
	if(!length(icon_states(I))) I = icon(source, state, SOUTH, 1, 1)
	return I

// This first composition path supports the original flat, native-size sprite
// layers. Unsupported effects retain the previous base-only portrait instead
// of producing an incomplete or incorrectly tinted composition.
proc/RemasterPortraitLayer(image/A, is_base, base_layer, base_plane)
	if(!A.icon) return null
	if(A.color || A.alpha != 255 || A.blend_mode || A.appearance_flags) return null
	if(A.pixel_x || A.pixel_y || A.pixel_w || A.pixel_z || A.invisibility) return null
	if(A.render_source || A.render_target || A.maptext || length(A.filters) || length(A.vis_contents)) return null
	if(length(A.underlays) || (!is_base && length(A.overlays))) return null
	var/matrix/T = A.transform
	if(T && (T.a != 1 || T.b || T.c || T.d || T.e != 1 || T.f)) return null
	var/effective_layer = A.layer
	if(!is_base)
		if(A.dir != SOUTH || (A.plane != -32767 && A.plane != base_plane)) return null
		if(A.layer < -1) return null
		if(A.layer == -1) effective_layer = base_layer
	if(effective_layer < 0 || effective_layer >= 20000) return null
	var/state = A.icon_state
	var/list/states = icon_states(A.icon)
	if(!(state in states)) state = ""
	if(!(state in states)) return null
	return list("source"=A.icon, "state"=state, "layer"=effective_layer, "key"=list(md5(A.icon), state, effective_layer))

proc/RemasterPortraitOpaqueCell(icon/I)
	// Reject partial-alpha artwork until its composition is independently
	// supported; original Human/Orc/hair/equipment cells have binary alpha.
	if(I.Width() != 32 || I.Height() != 32 || length(icon_states(I)) != 1) return 0
	for(var/x = 1, x <= 32, x++)
		for(var/y = 1, y <= 32, y++)
			var/pixel = I.GetPixel(x,y)
			if(pixel && length(pixel) == 9 && copytext(pixel,8) != "ff" && copytext(pixel,8) != "00") return 0
	return 1

proc/RemasterPortraitRecord(mob/Monsters/M)
	var/current = M.appearance
	if(M.remaster_portrait_record && M.remaster_portrait_appearance == current) return M.remaster_portrait_record
	var/image/A = image(current)
	// a turn (walking off, a new heading) changes only the facing, and the portrait is drawn facing south whatever way
	// the unit faces: the record made for the same look facing another way still holds (a whole-army order re-read every
	// layer of every unit; hud-craft, 10-25)
	A.dir = SOUTH
	var/south = A.appearance
	if(M.remaster_portrait_record && M.remaster_portrait_south == south)
		del(A)
		M.remaster_portrait_appearance = current
		return M.remaster_portrait_record
	// A playable race's portrait is the 64 px body the 3D view and the company card draw (Races64, the LOTR look) with
	// its gear, facing south, one frame: from the old 32 px sprite every race looked alike in the Company list and the
	// cards (the owner, 10-30: "the dwarf icons on company and etc do not [look] like the race selected"). Creatures
	// with no 64 px body keep the sprite's portrait below.
	var/list/record64 = RemasterPortrait64(M)
	if(record64)
		del(A)
		M.remaster_portrait_appearance = current
		M.remaster_portrait_south = south
		M.remaster_portrait_record = record64
		return record64
	var/list/base = RemasterPortraitLayer(A, 1, A.layer, A.plane)
	var/list/layers = list()
	var/list/keys = list()
	var/supported = !!base
	if(base) layers += list(base)
	if(supported)
		for(var/i = 1, i <= length(A.overlays), i++)
			var/image/O = image(A.overlays[i])
			var/list/L = RemasterPortraitLayer(O, 0, A.layer, A.plane)
			del(O)
			if(!L)
				supported = 0
				break
			// Stable effective-layer order: floating layers inherit the parent;
			// equal-layer overlays follow the base and original overlay order.
			var/at = length(layers) + 1
			for(var/j = 1, j <= length(layers), j++)
				var/list/other = layers[j]
				if(L["layer"] < other["layer"])
					at = j
					break
			layers.Insert(at, list(L))
	del(A)
	if(supported)
		for(var/list/L in layers) keys += list(L["key"])
	else keys = list("base-only", md5(M.icon), M.icon_state)
	var/id = md5(json_encode(keys))
	var/list/record = remaster_portrait_images[id]
	if(!record)
		var/icon/result = RemasterPortraitCell(M.icon, M.icon_state)
		if(supported)
			var/list/cells = list()
			for(var/list/L in layers)
				var/list/K = L["key"]
				var/ck = "[K[1]]:[L["state"]]"
				var/list/CC = remaster_portrait_cells[ck]
				if(!CC)
					var/icon/made = RemasterPortraitCell(L["source"], L["state"])
					CC = list(made, RemasterPortraitOpaqueCell(made) ? 1 : 0)
					remaster_portrait_cells[ck] = CC
				var/icon/cell = CC[1]
				if(!CC[2])
					supported = 0
					break
				cells += cell
			if(supported)
				result.Blend(rgb(255,255,255,0), ICON_MULTIPLY)
				for(var/icon/cell in cells) result.Blend(cell, ICON_OVERLAY)
		record = list("id"=id, "image"=result, "composed"=supported)
		if(length(remaster_portrait_images) >= 256) remaster_portrait_images.Cut(1,2)
		remaster_portrait_images[id] = record
	M.remaster_portrait_appearance = current
	M.remaster_portrait_south = south
	M.remaster_portrait_record = record
	return record

// The portrait record of a unit with a 64 px race body (Remaster3DBody64), keyed by its layers as the 3D view keys its
// pictures; null for one without.
proc/RemasterPortrait64(mob/Monsters/M)
	var/body64 = Remaster3DBody64(M)
	if(!body64) return null
	var/list/layers = Remaster3DLayers(M, body64)
	var/key = "portrait64|"
	for(var/list/L in layers) key += "[length(L) >= 3 ? L[3] : L[1]]:[L[2]][length(L) >= 5 ? ":cut" : ""]|"
	var/id = md5(key)
	var/list/record = remaster_portrait_images[id]
	if(record) return record
	var/icon/I = Remaster3DStrip(layers, SOUTH, 1, body64)
	if(!I) return null
	I = RemasterPortraitFit(I)
	record = list("id"=id, "image"=I, "composed"=1)
	if(length(remaster_portrait_images) >= 256) remaster_portrait_images.Cut(1,2)
	remaster_portrait_images[id] = record
	return record

// The figure in a 64 px portrait cut to a square round it, so a short race fills its frame in the Company list as the
// old sprites did (icon.Crop, engine/icon). On an engine without Crop the whole 64 px frame stays.
proc/RemasterPortraitFit(icon/I)
	var/w = I.Width()
	var/h = I.Height()
	var/x1 = w + 1
	var/y1 = h + 1
	var/x2 = 0
	var/y2 = 0
	for(var/y = 1, y <= h, y++)
		for(var/x = 1, x <= w, x++)
			if(I.GetPixel(x, y))
				if(x < x1) x1 = x
				if(x > x2) x2 = x
				if(y < y1) y1 = y
				if(y > y2) y2 = y
	if(!x2) return I
	var/side = min(max(x2 - x1, y2 - y1) + 3, w, h)
	var/ax = min(max(round((x1 + x2 - side) / 2) + 1, 1), w - side + 1)
	var/ay = min(max(round((y1 + y2 - side) / 2) + 1, 1), h - side + 1)
	I.Crop(ax, ay, ax + side - 1, ay + side - 1)
	return I

proc/RemasterPortraitImage(mob/Monsters/M)
	var/list/R = RemasterPortraitRecord(M)
	return R["image"]

// Keep one descriptor per current owned unit. A fixed-size FIFO here would
// resend every image on every HUD tick once the roster exceeded the cap.
Player/proc/RemasterPrunePortraits()
	if(!remaster_portraits) return
	// over 1,000 units every 2 s, not every send (a gone unit's entry here is only a file name until then; HudView.dm)
	if(!RmHudSlow("portraits", 20)) return
	RmShedKeep("portraits", 1)
	// the company marked, not collected in a set: adding a key scans the list here, so a set of 30,000 units each send
	// was square in its size (HudView.dm rm_hud_serial; hud-craft, 10-24)
	var/mk = ++rm_hud_serial
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && !M.Wagon) M.rm_hud_mark = mk
	for(var/file in remaster_portraits.Copy())
		var/list/D = remaster_portraits[file]
		var/mob/Monsters/M = D["unit"]
		if(!M || M.rm_hud_mark != mk) remaster_portraits -= file

Player/proc/RemasterPortrait(mob/Monsters/M)
	if(!client) return ""
	if(!remaster_portraits) remaster_portraits = list()
	var/list/R = RemasterPortraitRecord(M)
	if(!M.remaster_portrait_serial)
		global.remaster_portrait_serial++
		M.remaster_portrait_serial = global.remaster_portrait_serial
	var/file = "remaster-unit-[M.remaster_portrait_serial].png"
	var/list/previous = remaster_portraits[file]
	if(!previous || previous["id"] != R["id"])
		remaster_portraits[file] = list("unit"=M, "id"=R["id"])
		src << browse_rsc(R["image"], file)
	// A unit reuses its resource filename; the content query refreshes the
	// browser image without accumulating per-unit server resource filenames.
	return "[file]?v=[R["id"]]"

// Item sprites for the HUD bag grid: one PNG per original icon/state,
// sent to each player once. The game's own sprite files are not changed.
var/list/remaster_item_icons = list()
// an icon file's HUD name per state (icon -> list(state -> id)), worked out once: md5() of the file ran for every item
// of every selected unit each time its entry was built (hud-craft, 10-25)
var/list/remaster_item_icon_ids = list()
proc/RemasterItemIconId(obj/I)
	var/list/S = remaster_item_icon_ids[I.icon]
	if(!S)
		S = list()
		remaster_item_icon_ids[I.icon] = S
	var/k = "[I.icon_state]"
	. = S[k]
	if(!.)
		. = md5("[md5(I.icon)]:[I.icon_state]")
		S[k] = .
Player
	var/tmp/list/remaster_item_icons_sent

Player/proc/RemasterItemIcon(obj/I)
	if(!client || !I.icon) return ""
	var/id = RemasterItemIconId(I)
	var/file = "remaster-item-[id].png"
	if(!remaster_item_icons_sent) remaster_item_icons_sent = list()
	if(!remaster_item_icons_sent[file])
		var/icon/image = remaster_item_icons[id]
		if(!image)
			image = RemasterPortraitCell(I.icon, I.icon_state)
			remaster_item_icons[id] = image
		src << browse_rsc(image, file)
		remaster_item_icons_sent[file] = 1
	return file

// selset: the selection as a set (RemasterHUDData makes it once), so 200 selected units aren't each searched for in it.
mob/Monsters/proc/RemasterUnitData(Player/P, list/selset = null)
	RemasterLineageEnsure(P)
	var/sel = (selset ? selset[src] : (src in P.Selected)) ? 1 : 0
	var/single = sel && length(P.Selected) == 1
	var/list/warnings = list()
	if(RmLifeFrac(src) < 0.3) warnings += "Low health"
	if(Hunger <= 20) warnings += "Hungry"
	if(Tiredness <= 20) warnings += "Needs rest"
	if(Coldness > 0) warnings += "Cold"
	if(BloodContent < 80) warnings += "Blood loss"
	if(!HasLeftLeg || !HasRightLeg) warnings += "Leg injury"
	if(!HasLeftArm || !HasRightArm) warnings += "Arm injury"
	warnings += RemasterAilmentWarnings()   // poison, fever, food poisoning, drink (Ailments.dm)
	warnings += RmTameWarnings(src)   // a chained beast hungry, an egg carried off (Taming.dm)
	var/role = "Settler"
	var/best = 0
	var/list/skills = list("Miner"=MineingSkill, "Woodworker"=WoodCraftingSkill, "Builder"=BuildingSkill, "Woodcutter"=WoodCuttingSkill, "Smith"=MetalCraftingSkill, "Cook"=CookingSkill)
	for(var/S in skills) if(skills[S] > best)
		best = skills[S]
		role = S
	var/list/items = list()
	if(sel)
		var/list/kinds = list()   // one row a kind with its count (InventoryActions.dm RmKindKey; the owner, 10-28: "each item is a catergory")
		for(var/obj/Items/I in src)
			var/k = I.RmKindKey()
			var/list/row = k ? kinds[k] : null
			if(row)
				row["n"]++
				row["refs"] += RemasterUIRef(I)
				continue
			var/useon = RemasterUseOnAble(I)   // a click holds it, to click onto what it is for (UseOn.dm)
			row = list("ref"=RemasterUIRef(I), "name"="[I.name]", "state"="[I.suffix]", "icon"=P.RemasterItemIcon(I), "info"=RemasterItemInfo(I, src), "use"=RemasterItemUseKind(I), "useon"=useon, "n"=1, "refs"=list(RemasterUIRef(I)))
			items += list(row)
			if(k) kinds[k] = row
	var/list/pending = list()
	var/list/active
	var/list/resume
	if(remaster_active) active = RemasterOrderData(remaster_active, 0)
	if(remaster_delivery)
		resume = active
		active = RemasterOrderData(remaster_delivery, 0)
	if(sel)
		for(var/i = 1, i <= length(remaster_orders), i++)
			var/datum/remaster_order/O = remaster_orders[i]
			pending += list(RemasterOrderData(O, i))
	var/status = rm_dying_until ? "Bleeding out" : RemasterKnockedOut() ? "Knocked out" : remaster_order_status   // down: says so, not its last order (BleedOut.dm, Subdue.dm)
	var/tame = RmTameStatus(src)   // chained down, a young dragon growing (Taming.dm)
	if(tame) status = rm_bound ? tame : "[status || "Idle"] ([tame])"
	var/turf/at = rm_cap_cage ? RemasterGetTurf(src) : null   // shut in a cage (Captives.dm): at the cage's tile, not 0, 0, 0
	return list("ref"=RemasterUIRef(src), "name"="[name]", "race"="[Race]", "kind"=RmKindLabel(src), "level"=Level, "role"=role, "skill"=round(best),
		"selected"=sel, "fav"=rm_fav, "portrait"=P.RemasterPortrait(src),
		"hp"=RmLifeHP(src), "maxhp"=MAXHP, "fullness"=round(Hunger), "maxfullness"=MaxHunger,
		"energy"=round(Tiredness), "cold"=Coldness, "weight"=weight, "capacity"=weightmax,
		"morale"=(isnull(rm_morale) ? null : round(rm_morale)), "mstate"=RmMoraleStateText(),   // in combat only (Morale.dm)
		"warnings"=warnings, "order"=status, "queued"=length(remaster_orders), "job"=remaster_job, "patrolling"=!!remaster_patrol,
		"active"=active, "resume"=resume, "pending"=pending, "craftQueued"=length(remaster_production), "paused"=(remaster_paused || remaster_wait_for_resume || (!RemasterHasOrder() && remaster_role_paused && (remaster_job != "manual" || length(remaster_production)))), "blocked"=remaster_blocked, "autoUnload"=remaster_auto_unload, "tend"=remaster_tend_mode,
		"defense"=RemasterDefenseData(), "combat"=RemasterCombatStatus(), "nonlethal"=remaster_nonlethal, "aptitude"=!!MagicalAptitude, "events"=RemasterEventData(), "autouse"=(single || (sel && P.remaster_units_page) ? RemasterAutoUseData() : null),   // shown only on the Units page's selected rows
		"x"=(at ? at.x : x), "y"=(at ? at.y : y), "z"=(at ? at.z : z), "items"=items,
		// the sheets for the open card (one selected) or every selected unit while the Units page shows them; the band card
		// (two or more) needs only each one's combat style (the user, 10-24: 200 selected made a full send 1.46 MB)
		"stats"=(single || (sel && P.remaster_units_page) ? RemasterStatSheet() : null),
		"skills"=(single || (sel && P.remaster_units_page) ? RemasterSkillPanel() : (sel ? list("style"=remaster_combat_style) : null)),
		"special"=(single ? RemasterSpecialData() : null),   // the open card's special (remastered.html heroPanes)
		"family"=(single ? RemasterFamilyData(P) : null),
		"captive"=RmCaptiveData(P),   // bound or a slave: rope, loyalty, escape odds (Captives.dm)
		"captures"=(single ? RemasterCaptureData(P) : null),
		"health"=(single ? RemasterHealthData() : null),
		"nearby"=(single ? RemasterNearbyData(P) : null),
		"selfuses"=(single ? P.RemasterSelfUses(src) : null),   // its own right-click card (TargetActions.dm)
		"abilities"=(single ? P.RemasterAbilities(src) : null),
		"moves"=(single ? RmMovesData(src) : null),   // its weapon's moves and spells (WeaponSkills.dm)
		"wmana"=(single ? RmWeaponManaData(src) : null),
		"chakra"=(single && RmIsNinja(src) ? RmChakraData() : null),   // a ninja's chakra and kunai (Ninja.dm)
		"alchemy"=(single ? P.RemasterAlchemyData(src) : null),
		"cauldron"=(single ? P.RemasterCauldronData(src) : null),
		"market"=(single ? P.RemasterMarketData(src) : null),
		"food"=(single ? P.RemasterFoodBoxData(src) : null),
		"clinic"=(single ? P.RemasterClinicBoxData(src) : null),
		"table"=(single ? P.RemasterTableBoxData(src) : null),
		"tavern"=(single ? P.RemasterTavernBoxData(src) : null),
		"qboard"=(single ? P.RmQuestBoxData(src) : null),   // a notice board beside it (Quests.dm)
		"keeper"=(single ? P.RmKeeperTabData(src) : null),   // its Keeper tab (QuestKeepers.dm)
		"keeperMake"=(single ? P.RmKeeperMakeData(src) : null),   // by its own board or stall: make it a keeper
		"look"=RemasterLook(),
		"cave"=(single ? P.RemasterCaveData(src) : null),
		"weapon"="[RemasterWeaponRole(src)][RemasterThrowSummary()]", "mood"=(rm_moods_on ? round(remaster_mood) : null), "moodName"=(rm_moods_on ? RemasterMoodName() : null), "thoughts"=(rm_moods_on ? remaster_thoughts : null),
		"runes"=(single ? P.RemasterRuneData(src) : null),
		"toolTiers"=(single || (sel && P.remaster_units_page) ? RemasterToolData() : null),
		"gender"="[Gender]", "age"=Age, "priority"=remaster_priority, "royal"=!!IsRoyal, "uid"=remaster_uid,
		"home"=RemasterHomeText(), "care"=remaster_care_status, "careNote"=remaster_care_note,
		"tools"=(UsesPicks ? "Uses an axe to chop and a pickaxe to mine; carried tools equip automatically." : "Can gather without a pickaxe."),
		"equipment"=(UsesEquipment ? "Can use equipment." : "Natural abilities; equipment is restricted."))

proc/RemasterOrderData(datum/remaster_order/O, index)
	if(!O) return null
	var/atom/A = O.target
	return list("ref"=RemasterUIRef(O), "index"=index, "kind"=O.kind, "name"=(A ? "[A.name]" : "Unavailable target"), "x"=(A ? A.x : 0), "y"=(A ? A.y : 0), "z"=(A ? A.z : 0))

// Idle means ready for reassignment, not merely lacking a destination. This
// predicate is read-only and shared by the displayed count and next-unit picker.
// listed: the caller is walking UnitList, so the "in UnitList" scan (30,000 long at scale, and once per unit) is skipped
Player/proc/RemasterIdleEligible(mob/Monsters/M, listed)
	if(!M || M.Owner != src || (!listed && !(M in UnitList)) || M.Wagon || M.Critter) return 0
	if(!isturf(M.loc) || M.HP <= 0 || M.GoingToDie || M.Egg || M.InHole || M.Sleeping) return 0
	if(!M.CanWalk || M.Fainted || M.Stunned || M.Meditating) return 0
	if(M.RemasterHasOrder() || M.remaster_job != "manual" || length(M.remaster_production)) return 0
	if(M.remaster_defense || M.destination || M.Target || M.BowOn) return 0
	if(M.HomeLoc || M.Dig || M.DigTarget || M.remaster_work_destination) return 0
	if(M.remaster_builder || M.remaster_site || M.remaster_site_return) return 0
	if(M.remaster_order_status in list("Holding", "Holding position")) return 0
	return 1

Player/proc/RemasterIdleUnits()
	var/list/available = list()
	// "M in available" made it square in the company's size (5,000 units: ~96 ms); a set would be too (adding a key
	// scans the list here), so a mark on each unit (HudView.dm rm_hud_serial; hud-craft, 10-24)
	var/dk = ++rm_hud_serial
	for(var/mob/Monsters/M in UnitList)
		if(M.rm_hud_dmark != dk && RemasterIdleEligible(M, 1))
			M.rm_hud_dmark = dk
			available += M
	return available

Player/proc/RemasterNextIdle()
	var/list/available = RemasterIdleUnits()
	if(!length(available))
		RemasterNotice("No idle units are ready for new orders.")
		return 0
	// Prefer the current single selection; otherwise continue from the last
	// successful lifetime token. Deleted/transferred cursors cannot select a
	// replacement atom that happens to reuse an engine reference.
	var/mob/Monsters/previous = RemasterUIUnit(remaster_idle_last)
	if(length(Selected) == 1 && (Selected[1] in available)) previous = Selected[1]
	var/start = available.Find(previous)
	for(var/offset = 1, offset <= length(available), offset++)
		var/index = ((start + offset - 1) % length(available)) + 1
		var/mob/Monsters/M = available[index]
		if(!RemasterIdleEligible(M)) continue
		// Original Select can reject a unit. Try it before removing the old
		// selection, and commit camera/cursor only once membership is proven.
		M.Select(src)
		if(!(M in Selected)) continue
		RemasterClickSelect(M, 0)
		remaster_idle_last = RemasterUIRef(M)
		loc = locate(M.x, M.y, RmViewLayer(M))   // its level's view (Peaks.dm)
		RemasterCamTo(M)
		RemasterNotice("Selected [M.name]. F1 (Next idle) finds the next one.")
		return 1
	RemasterNotice("No idle units could be selected. Their availability may have changed.")
	return 0

// The same numbers the original Unit Stats / Inventory / Unit Information tabs
// show (Code/1 - Stat Proc.dm), as grouped rows for the styled HUD.
mob/Monsters/proc/RemasterStatSheet()
	// The 2006 Strength, Agility and Intelligence stats are not shown: the Skills tab's Strength, Attack and Magic are the
	// ones (owner 10-27: "do we have two different stats happening with the same name?", "Fold old stats into skills")
	var/list/attributes = list(list("EXP", "[EXP] / [EXPNeeded]"), list("Armour", "[Defence]"), list("Cold", "[Coldness]"))   // the Defence stat is armour (roll + worn); Defence is the skill
	if(MaxWebContent) attributes += list(list("Web", "[WebContent] / [MaxWebContent]"))
	if(HasGland) attributes += list(list("Poison damage", "[PoisonDMG]"))
	if(MagicalAptitude)
		attributes += list(list("Mana", "[Mana] / [MaxMana]"), list("Magical anger", "[MagicalAnger]"), list("Magical mind", "[MagicalMind]"),
			list("Magical will", "[MagicalWill]"), list("Concentration", "[MagicalConcentration]"))
	var/list/combat = list()
	if(HoldingWeapon == "Claws" || SubRace == "Werewolf") combat += list(list("Claws", "[ClawSkill]"))
	else
		if(HoldingWeapon == "Butcher Knife") combat += list(list("Butchery", "[ButcherySkill]"))
		combat += list(list("Spear", "[SpearSkill]"), list("Sword", "[SwordSkill]"), list("Bow", "[BowSkill]"), list("Axe", "[AxeSkill]"),
			list("Dagger", "[DaggerSkill]"), list("Mace", "[MaceSkill]"), list("Unarmed", "[UnArmedSkill]"), list("Shield", "[ShieldSkill]"), list("Armour", "[ArmourSkill]"))
	var/list/craft = list()
	switch(Race)
		if("Spider", "Dragon", "Zombie", "Devourer")
			if(Race == "Spider") craft += list(list("Crafting", "[WoodCraftingSkill]"))
			if(Race == "Dragon")
				craft += list(list("Eggs", "[EggContent]"))
				if(!SubRace) craft += list(list("Fire", "[FirePoints/10]%"), list("Ice", "[IcePoints/10]%"), list("Desert", "[SandPoints/10]%"),
					list("Poison", "[PoisonPoints/10]%"), list("Magma", "[MagmaPoints/10]%"), list("Water", "[WaterPoints/10]%"), list("Zombie", "[ZombiePoints/10]%"))
			if(Race == "Devourer") craft += list(list("Stored bodies", "[EggContent]"), list("Bone crafting", "[BoneCraftingSkill]"))
			craft += list(list("Woodcutting", "[WoodCuttingSkill]"), list("Mining", "[MineingSkill]"), list("Building", "[BuildingSkill]"),
				list("Fishing", "[FishingSkill]"), list("Sneaking", "[SneakingSkill]"))
		else
			craft += list(list("Woodcutting", "[WoodCuttingSkill]"), list("Mining", "[MineingSkill]"), list("Wood crafting", "[WoodCraftingSkill]"),
				list("Metal crafting", "[MetalCraftingSkill]"), list("Jewel crafting", "[JewlCraftingSkill]"), list("Leather crafting", "[LeatherCraftingSkill]"),
				list("Poison", "[PoisonSkill]"), list("Bone crafting", "[BoneCraftingSkill]"), list("Stone crafting", "[StoneCraftingSkill]"),
				list("Sneaking", "[SneakingSkill]"), list("Lock picking", "[LockPickingSkill]"), list("Cooking", "[CookingSkill]"),
				list("Potions", "[PotionSkill]"), list("Fishing", "[FishingSkill]"), list("Building", "[BuildingSkill]"))
	var/list/body = list(list("Gender", "[Gender]"), list("Age", "[Age]"), list("Bleeding", BleedType ? (BleedType == "Extremly" ? "Extremely" : "[BleedType]") : "No"), list("Blood", "[BloodContent]"),
		list("Head", "[Head]"), list("Brain", "[Brain]"), list("Throat", "[Throat]"), list("Nose", "[Nose]"), list("Teeth", "[Teeth]"),
		list("Left eye", "[LeftEye]"), list("Right eye", "[RightEye]"), list("Left ear", "[LeftEar]"), list("Right ear", "[RightEar]"),
		list("Left arm", HasLeftArm ? "[LeftArm]" : "Missing"), list("Right arm", HasRightArm ? "[RightArm]" : "Missing"),
		list("Left leg", HasLeftLeg ? "[LeftLeg]" : "Missing"), list("Right leg", HasRightLeg ? "[RightLeg]" : "Missing"), list("Heart", "[Heart]"))
	body = RmBodyRows(src, body)   // a great beast's parts and anyone's wings (Beasts.dm)
	if(rm_dying_until) body.Insert(1, list(list("Bleeding out", "[max(0, round((rm_dying_until - world.time) / 10))] s left: a bandage, torch, poultice or healing potion from someone, or a Doctor")))   // BleedOut.dm
	else if(RemasterKnockedOut()) body.Insert(1, list(list("Knocked out", "wakes in [max(1, round((remaster_ko_until - world.time) / 10))] s")))   // Subdue.dm
	return list("attributes"=attributes, "combat"=combat, "craft"=craft, "body"=body)

Player/proc/RemasterWorldInfo()
	return list(list("Land", "[WorldName]"), list("Date", "[Date] - [Ages]"), list("Season", "[Season]"), list("Time", night ? "Night" : "Day"),
		list("Your kills", "[Kills]"), list("History", "[History]"))

Player/proc/RemasterHUDData(spread = 0)
	RemasterPrunePortraits()
	RemasterNormalizeSelection()
	var/list/units = list()
	var/list/targets = list()
	// the idle count: over 1,000 units, the jobs' census's (Jobs.dm RmIdleCount: the same test, at most ~1 min old at 30k)
	// rather than every unit looked at each send; under that, or before its first sweep, counted here as before
	var/idle = (!RmShedDue("idle") && remaster_shed_cache) ? remaster_shed_cache["idle"] : null   // the tiers (HudView.dm)
	if(isnull(idle)) idle = length(UnitList) > 1000 ? RmIdleCount() : null
	if(isnull(idle) && length(UnitList) > 1000 && remaster_view_counts) idle = remaster_view_counts["eligible"]   // the view's pass (HudView.dm) until the census has swept
	if(isnull(idle)) idle = length(RemasterIdleUnits())
	RmShedKeep("idle", idle)
	// once the page has said what it shows ("hudview"), whole entries go only for that (HudView.dm); else every unit
	var/list/vdata = list()
	var/list/vset = RmViewSet(vdata, spread)
	var/list/sel = list()   // the selection as a set: "M in Selected" searched it end to end for every unit
	if(vset)   // only the view set's selected units: a set of a big selection is square in its size to build here
		var/sk = ++rm_hud_serial
		for(var/mob/Monsters/M in Selected) M.rm_hud_smark = sk
		for(var/mob/Monsters/M in vset) if(M.rm_hud_smark == sk) sel[M] = 1
	else
		for(var/S in Selected) sel[S] = 1
	var/rows_due = !vset || RmShedDue("rows")
	if(rows_due) RmShedKeep("rows", 1)
	var/list/ecache = list()
	for(var/mob/Monsters/M in (vset || UnitList)) if(M.Owner == src && !M.Wagon)
		// a list row off screen and not selected (vset 2) keeps its last entry while the tiers hold rows back; the
		// selection, the screen and open groups (vset 1) are always built fresh
		var/list/E = (!rows_due && vset[M] == 2 && remaster_view_ecache) ? remaster_view_ecache[M] : null
		if(!E) E = M.RmHudEntry(src, sel)   // kept between sends while it may be (HudView.dm)
		if(vset && vset[M] == 2) ecache[M] = E
		units += list(E)
		if(sel[M] && M.remaster_active && M.remaster_active.target)
			var/atom/A = M.remaster_active.target
			targets += list(list("x"=A.x, "y"=A.y, "z"=A.z, "kind"=M.remaster_active.kind, "unit"=RemasterUIRef(M), "index"=0, "blk"=M.remaster_active.block))
		if(sel[M])
			for(var/i = 1, i <= length(M.remaster_orders), i++)
				var/datum/remaster_order/O = M.remaster_orders[i]
				var/atom/A = O.target
				if(A && A.z) targets += list(list("x"=A.x, "y"=A.y, "z"=A.z, "kind"=O.kind, "index"=i, "unit"=RemasterUIRef(M), "blk"=O.block))
		if(spread) RmTrackPause()   // between units, after this one is done (Spread.dm)
	var/list/D = list("tab"=remaster_hud_tab, "notice"=remaster_notice, "units"=units,
		"selection"=length(Selected), "multi"=remaster_multi, "queue"=remaster_queue, "gather"=remaster_gather, "selAutoUnload"=RemasterSelAutoUnloadState(),
		"season"=Season, "day"=(night ? "Night" : "Day"), "date"=Date,
		"x"=x, "y"=y, "z"=z, "maxx"=world.maxx, "maxy"=world.maxy, "maxz"=world.maxz, "sky"=RmSkyOpen(),
		"idle"=idle, "alert"=RemasterAlertShown(), "targets"=targets, "mode"=Function,
		"world"=RemasterWorldInfo(), "view3d"=remaster_3d, "villageView"=remaster_village_view, "xpDrops"=RemasterXPDropData(),
		"lineage"=((remaster_hud_tab == "village" && remaster_village_view == "lineage") ? (RmShedDue("lineage") ? RmShedKeep("lineage", RemasterLineageDataCached()) : remaster_shed_cache["lineage"]) : null),
		"board"=((remaster_hud_tab == "village" && remaster_village_view == "board") ? (RmShedDue("board") ? RmShedKeep("board", RemasterBoardData()) : remaster_shed_cache["board"]) : null), "villageLog"=((remaster_hud_tab == "village" && remaster_village_view == "log") ? (RmShedDue("villageLog") ? RmShedKeep("villageLog", RemasterVillageLogData()) : remaster_shed_cache["villageLog"]) : null), "logCount"=remaster_village_log_serial, "classicInfo"=remaster_classic_info, "logOpen"=remaster_log_open, "play"=RemasterPlayModeData(), "raids"=RemasterRaidData(), "icons"=RemasterHudIcons(), "cine"=remaster_cine, "attackMode"=remaster_attack_mode, "useCard"=RemasterUseCardData(), "ask"=remaster_ask, "progress"=(RmShedDue("progress") ? RmShedKeep("progress", RemasterProgressData()) : remaster_shed_cache["progress"]), "trade"=(RmShedDue("trade") ? RmShedKeep("trade", RemasterTradeData()) : remaster_shed_cache["trade"]), "claims"=(RmShedDue("claims") ? RmShedKeep("claims", RemasterClaimData()) : remaster_shed_cache["claims"]), "realm"=RmHudRealm(), "hosting"=(RemasterIsHost() ? RemasterHostingData() : null), "hits"=RemasterHitData(), "siegeWalls"=RemasterSiegeData(), "aim"=RemasterAimData(), "specialFx"=RemasterSpecialFxData(), "speed"=rm_speed, "fog"=remaster_fog, "fogHost"=(RemasterIsHost() || !fexists("host-name")), "explored"=(RmShedDue("explored") ? RmShedKeep("explored", RemasterExploredMaskCached()) : remaster_shed_cache["explored"]), "pings"=RemasterPingData(), "formation"=remaster_formation, "savedAgo"=RemasterSaveAgo(), "canUndo"=length(remaster_undo), "daySummary"=remaster_day_summary, "awayReport"=remaster_away_report, "patrol"=RemasterPatrolData(), "zones"=(remaster_hud_tab == "work" ? (RmShedDue("zones") ? RmShedKeep("zones", RemasterZoneData()) : remaster_shed_cache["zones"]) : null), "hover"=(length(Selected) ? remaster_hover : null), "worldMap"=(remaster_world_map_open ? RemasterWorldMapData() : null),
		"tutorialHidden"=remaster_tutorial_hidden, "milestones"=remaster_milestones,
		"settlement"=(RmShedDue("settlement") ? RmShedKeep("settlement", RemasterSettlementData()) : remaster_shed_cache["settlement"]), "commands"=(RmShedDue("commands") ? RmShedKeep("commands", RemasterCommandDataKept()) : remaster_shed_cache["commands"]), "border"=(RmShedDue("border") ? RmShedKeep("border", RemasterBorderDataKept()) : remaster_shed_cache["border"]), "palette"=RemasterPaletteData(), "magicTarget"=RemasterMagicTargetData(), "controlGroups"=RemasterControlGroupsData())
	for(var/k in vdata) D[k] = vdata[k]   // lists, counts, unitCells, band (HudView.dm)
	if(vset) remaster_view_ecache = ecache
	// Army > Captives (Captives.dm) and the ropes: both look at every unit (and ropes every unit's bag), so over 1,000
	// units they are rebuilt every 1 s and 2 s rather than every send (30,000: ~200 and ~140 ms a send; hud-craft)
	D["captives"] = RmHudSlow("captives", 10) ? RmShedKeep("captives", RmCaptivesData()) : remaster_shed_cache["captives"]
	// only Army > Captives shows the ropes, and counting them looks in every unit's pack (62 ms at 30,000): only while
	// Army is open; the tiers (HudView.dm) build it less often when the server is behind
	D["ropes"] = remaster_hud_tab != "army" ? null : ((RmShedDue("ropes") && RmHudSlow("ropes", 20)) ? RmShedKeep("ropes", RmRopesData()) : remaster_shed_cache["ropes"])
	D["quests"] = remaster_hud_tab == "quests" ? RmQuestPageDataCached() : null   // the Quests page, its card and tracker (Quests.dm)
	D["questCard"] = RmQuestCardDataCached()   // kept while nothing on it changed (QuestScale.dm)
	D["questTrack"] = RmQuestTrackData()
	D["questMarks"] = RmQuestMarksData()   // quest markers for this viewer, and the target being picked (QuestTargets.dm)
	D["questPick"] = rm_quest_pick
	D["admin"] = RmModHudData()   // the Admin button and page: staff only (Moderation.dm)
	if(RmBugsOn()) D["bugs"] = 1  // Settings > Report a bug, and the page's own errors sent (Bugs.dm)
	if(RmPublicWorld()) D["speedLocked"] = 1   // one speed for everyone: the page hides pause and fast (the owner, 11-01: "Yes, hide them")
	D["online"] = RmOnlineData()   // players online, in the top bar: public and hosted worlds (Moderation.dm)
	if(remaster_hud_tab == "build") D["construction"] = RemasterConstructionData(1)
	D["foodAlert"] = RemasterFoodAlertData()   // poisoned food (FoodSupply.dm)
	D["useon"] = RemasterUseOnData()           // an item held, to click onto what it is for (UseOn.dm)
	D["audio"] = RemasterAudioPrefs()          // the player's sound settings (Audio.dm)
	D["hudPrefs"] = RemasterHUDPrefs()         // the player's other HUD settings, kept across restarts (Audio.dm)
	D["help"] = remaster_help_serial            // F3 / Help opens the Guide panel (Onboarding.dm)
	// the band card's Fly row ("flylevel"): looked at every send up to 1,000 selected, else once a second (hud-craft)
	D["selFly"] = (length(Selected) <= 1000 || RmHudSlow("selfly", 10)) ? RmShedKeep("selfly", RmHudSelFly()) : remaster_shed_cache["selfly"]
	RemasterOnboardTick()    // the Guide goals that have no event of their own (Onboarding.dm)
	if(remaster_map_sent != z)
		D["terrain"] = RemasterMap(z)
		remaster_map_sent = z
	return D

proc/RemasterMap(level)
	var/id = "[level]"
	if(remaster_maps[id]) return remaster_maps[id]
	var/list/grid = list()
	for(var/gy = 1, gy <= 48, gy++)
		for(var/gx = 1, gx <= 48, gx++)
			var/turf/T = locate(clamp(round((gx - 0.5) * world.maxx / 48), 1, world.maxx), clamp(world.maxy - round((gy - 0.5) * world.maxy / 48), 1, world.maxy), level)
			var/color = "#314c35"
			if(T)
				var/s = lowertext("[T.icon_state]")
				if(T.density) color = "#655e4a"
				if(T.Tree && T.density) color = "#25442c"
				if(findtext(s, "water") || T.CaveWater) color = "#31586a"
				if(findtext(s, "desert") || findtext(s, "sand")) color = "#9c8757"
				if(findtext(s, "snow")) color = "#a2b8bb"
				if(findtext(s, "cave")) color = T.density ? "#3c3c44" : "#64616b"
				if(findtext(s, "lava")) color = "#a35032"
				if(s == "sky") color = "#6f93a0"
			grid += color
	remaster_maps[id] = grid
	return grid

Player/proc/RemasterCommandData()
	var/list/commands = list()
	for(var/obj/RemasterAction/A in RemasterActions())
		var/reason = A.needs_units && !length(Selected) ? "Select a unit first" : ""
		if(A.action_id == "build" && !length(Selected)) reason = "Select a builder first"
		if(A.action_id == "mental") reason = RemasterMentalReason()
		if(A.action_id == "magictarget") reason = RemasterMagicTargetReason()
		var/curated_reason = RemasterCuratedActionReason(A.action_id)
		if(length(curated_reason)) reason = curated_reason
		commands += list(list("id"=A.action_id, "label"=A.name, "key"=A.key, "reason"=reason, "selectionBound"=(A.needs_units || A.action_id == "build")))
	return commands

// The command bar as the HUD sends it: its reasons read the selection, so it is built each send, but while every
// command's reason is as before the kept list goes again and the send reuses its encoded text (RemasterHUDKeysDelta).
// The commands themselves are one table for everyone (Actions.dm RemasterActions).
Player/var/tmp/rm_commands_sig
Player/var/tmp/list/rm_commands_kept
Player/proc/RemasterCommandDataKept()
	var/list/C = RemasterCommandData()
	var/list/sig = list(length(C))
	for(var/list/E in C) sig += "[E["id"]]=[E["reason"]]"
	var/s = jointext(sig, "|")
	if(s == rm_commands_sig && rm_commands_kept) return rm_commands_kept
	rm_commands_sig = s
	rm_commands_kept = C
	return C

Player/proc/RemasterPickupNearby(obj/RemasterAction/A)
	var/type = A.RemasterItemType()
	if(!type) return
	var/count = 0
	var/reason = "No matching items within one tile."
	for(var/mob/Monsters/M in Selected) if(M.Owner == src)
		for(var/obj/Items/I in range(1, M)) if(istype(I, type) && isturf(I.loc) && !I.suffix)
			if(A.action_id == "pickores" && istype(I, /obj/Items/ores/stone)) continue
			if(M.PickUpItem(I))
				count++
			else reason = M.RemasterPickupReason(I)
	RemasterNotice(count ? "Picked up [count] item[count == 1 ? "" : "s"]." : reason)
	if(count) RemasterMilestone("gather")

Player/proc/RemasterMessage()
	var/list/recipients = list()
	for(var/mob/P in Players) if(P != src && P.client) recipients += P
	if(!recipients.len)
		RemasterNotice("No other players are online.")
		return
	var/mob/recipient = input(src, "Choose a player", "Message") as null|anything in recipients
	if(!recipient || !recipient.client) return
	var/message = input(src, "Your message", "Message") as text|null
	if(isnull(message) || !recipient || !recipient.client) return
	SendMSG(recipient, message)

Player/proc/RemasterCoordinates()
	var/X = input(src, "X coordinate", "Move view", x) as num|null
	if(isnull(X)) return
	var/Y = input(src, "Y coordinate", "Move view", y) as num|null
	if(isnull(Y)) return
	var/Z = input(src, "Level", "Move view", z) as num|null
	if(isnull(Z)) return
	Coords(X, Y, Z)

Player/proc/RemasterBuildBasic(kind)
	if(!(kind in list("campfire", "carpentry"))) return 0
	for(var/mob/Monsters/M in Selected.Copy()) if(M.Owner == src && (M in UnitList) && M.HP > 0 && !M.GoingToDie && !M.Wagon && M.Race != "Spider")
		if(M.IsMist || M.Flying || M.Sleeping || M.Fainted)
			RemasterNotice("Builder must be awake and on the ground.")
			continue
		var/blocked = 0
		for(var/mob/WorkShops/W in range(1, M)) blocked = 1
		var/turf/left = locate(M.x - 1, M.y, M.z)
		if(blocked || !isturf(M.loc) || M.loc:density || (kind == "carpentry" && (!left || left.density)))
			RemasterNotice("Needs open space, at least two tiles from another workshop.")
			continue
		for(var/obj/Items/woods/wood/W in M)
			// Keep interrupted tasks/roles, while a production-only worker can
			// immediately use the newly built workshop without another command.
			var/continue_production = M.remaster_job == "manual" && length(M.remaster_production) && !M.RemasterHasOrder() && !M.remaster_paused && !M.remaster_wait_for_resume && !M.remaster_role_paused
			if(!M.RemasterManualHandoff(src)) continue
			if(kind == "carpentry") M.CreateCarpentry()
			else new /mob/WorkShops/CampFires/Fire(M.loc)
			M.weight -= W.weight
			del(W)
			if(continue_production) M.remaster_role_paused = 0
			RemasterMilestone(kind == "campfire" ? "camp" : "workshop")
			remaster_built_at = world.time    // Onboarding.dm: its crafting XP is not the crafting goal
			RemasterNotice("Built [kind] with 1 wood.")
			return 1
		RemasterNotice("Builder needs 1 wood in their bag.")
	if(!length(Selected)) RemasterNotice("Select a builder first.")
	return 0

// Touch commands that act on a selection bind to its advertised lifetime token.
// Original keyboard/map callbacks remain independent of this browser boundary.
Player/proc/RemasterHUDSelectionBound(route, id)
	// Direct Work/Orders buttons use the same advertised actor-set boundary.
	// Setting a stockpile at the camera (or clearing it) remains player-wide.
	if(route in list("build", "stance", "dropoff", "unloadresume", "job", "craft", "cancel", "workarea", "priority")) return 1
	if(route == "stockpile") return id == "unit"
	if(route == "action")
		for(var/obj/RemasterAction/A in RemasterActions()) if(A.action_id == id) return A.needs_units || id == "build"
	if(route == "borderaction")
		var/list/C = RemasterBorderControl(id)
		return C && (C["needs_units"] || id == "build")
	return 0

Player/proc/RemasterHUDSelectionAuthorized(route, id, token)
	if(!RemasterHUDSelectionBound(route,id)) return 1
	var/datum/remaster_group_selection/D = remaster_group_selection
	return istext(token) && length(token) && D && D.count > 0 && token == D.remaster_ui_id && RemasterGroupSelectionCurrent(D)

Player/proc/RemasterDeferHUDCommand(route, id)
	var/bound = RemasterHUDSelectionBound(route,id)
	var/datum/remaster_group_selection/D = bound ? RemasterGroupSelectionCapture() : null
	var/Player/P = src
	spawn(0)
		if(!P) return
		if(bound && (!D || !P.RemasterGroupSelectionCurrent(D)))
			P.RemasterNotice("Selection changed; choose the command again. Assigned work continues.")
			P.RemasterHUDTick()
			return
		if(route == "action")
			for(var/obj/RemasterAction/A in RemasterActions()) if(A.action_id == id)
				A.Run(P)
				break
		else if(route == "borderaction") P.RemasterBorderRun(id)

Player/proc/RemasterTouchCommand(action, value)
	usr = src
	switch(action)
		if("ready")
			if(rm_mod_ban_shown) return RmModBanShow()   // turned away: their page shows why (Moderation.dm)
			remaster_hud_ready = 1
			remaster_map_sent = 0
			remaster_hud_last = null
			remaster_hud_unit_codes = null   // a page that (re)loads has no units yet: the next send is a full model
			remaster_hud_pack = 0            // until it says it unpacks (HudPack.dm)
			// A page that (re)loads starts empty: send the whole 3D scene again too.
			remaster_3d_key = null
			remaster_3d_far_key = null
			remaster_3d_last = null
			remaster_3d_layers = null
			remaster_3d_moves_last = null
			Remaster3DForget()   // its chunks and things: all sent again (View3D.dm)
		if("hudfull") remaster_hud_unit_codes = null   // the page missed a send: the next one is a full model
		if("3dfull")   // the 3D page is missing a chunk or a thing: send it all again (View3D.dm)
			Remaster3DForget()
			remaster_3d_last = null
		if("unitspage") remaster_units_page = value == "1"   // the Units page shows every selected unit's sheets while open
		if("hudview") RmViewCommand(value)   // what the page shows: its list windows (HudView.dm)
		if("hudpack") remaster_hud_pack = value == "1"      // the page unpacks packed sends (HudPack.dm), or one failed
		if("playmode", "makehero", "follow", "lockcam", "chasecam") RemasterPlayModeCommand(action, value)
		if("difficulty") RemasterDifficultyCommand(value)
		if("audioprefs") RemasterAudioSave(value)    // Sound settings (Audio.dm)
		if("hudprefs") RemasterHUDPrefsSave(value)  // other HUD settings (Audio.dm)
		if("worldmap", "worldmaplayer") RemasterWorldMapCommand(action, value)
		if("zoneadd", "zoneremove", "zonefilter") RemasterZoneCommand(action, value)
		if("giveitem", "useitem", "autouse") RemasterBagCommand(action, value)
		if("unitability") RemasterUseAbility(value)
		if("flylevel") RmFlySelection(value == "up")   // the selection's flyers up or down a step, the Sky level too (Flying.dm)
		if("specialaim") RemasterSpecialVerb()
		if("drive") RmDriveCommand(value)   // WASD: your ninja (Drive.dm)
		if("ninjacast") RmNinjaCastCommand(value)   // 1-4: a technique at the mouse (Drive.dm)
		if("housename")   // Realm > Name the house sends "<name>"; Village > Lineage > Rename sends "<house id>|<name>" (polish-hud 10-26)
			if(findtext("[value]", "|")) RemasterRenameHouse(value)
			else RemasterNameHouse(value)
		if("breed") RemasterBreedOrder(value)
		if("capture") RemasterCapture(value)
		if("captureorder") RemasterCaptureOrder(locate(value))     // Subdue.dm
		if("captive") RmCaptiveCommand(value)                      // a captive's card: win over, enslave, release, tie, lead (Captives.dm)
		if("attackorder")                                          // the card's Interact tab
			var/mob/Monsters/E = locate(value)
			if(istype(E)) RemasterAttackOrder(E)
		if("attackpart") RmAttackPart(value)                        // a great beast's part (Beasts.dm)
		if("chainorder") RmChainOrder(locate(value))                // Taming.dm
		if("feedbeast") RmFeedOrder(RemasterUIUnit(value) || locate(value))   // Taming.dm: a chained beast is held (one of yours)
		if("weaponmove") RmMoveCommand(value)            // a weapon move or spell, now (WeaponSkills.dm)
		if("weaponmoveauto") RmMoveCommand(value, 1)     // on or off by itself in fights
		if("lethal") RemasterLethalToggle()
		if("specialcancel") RemasterSpecialCancel()
		if("brew") RemasterBrewCommand(value)
		if("cauldron") RemasterCauldronCommand(value)
		if("foodsupply") RemasterFoodCommand(value)
		if("clinic") RemasterClinicCommand(value)
		if("stump") RemasterStumpCommand(value)          // the Health tab's stump buttons (Stumps.dm)
		if("surgery") RemasterTableCommand(value)
		if("tavern") RemasterTavernCommand(value)
		if("quest") RmQuestCommand(value)   // notices and the Quests page (Quests.dm)
		if("admin") RmModCommand(value)     // the Admin page: checked against the staff list (Moderation.dm)
		if("report") RmModReport(value)     // a player reports a notice or a player (Moderation.dm)
		if("bugreport") RmBugReport(value)  // Settings > Report a bug (Bugs.dm)
		if("bugauto") RmBugPageError(value) // the page's own script errors (Bugs.dm)
		if("chat") RmChatSend(value)        // the chat box's line: World or Kingdom (ChatBox.dm)
		if("foodalert") RemasterFoodAlertCommand(value)
		if("useonpick", "useonat", "useoncancel") RemasterUseOnCommand(action, value)   // UseOn.dm
		if("rune") RemasterRuneCommand(value)
		if("renameunit") RemasterRenameCommand(value)
		if("takestock") RemasterTakeCommand(value)
		if("equipbest") RemasterEquipBestCommand()
		if("dayclose") remaster_day_summary = null
		if("awayclose") remaster_away_report = null
		if("undo") RemasterUndo()
		if("savenow") RemasterSaveNow()
		if("patrolstart", "patrolfinish", "patrolcancel", "patrolclear") RemasterPatrolCommand(action)
		if("unitpace") RemasterPaceCommand(value)   // "Own pace" or the group's, for group moves (Formations.dm)
		if("attackbox") RemasterAttackBox(value)   // Attack (A), then a box dragged over foes (Formations.dm)
		if("formationsave", "formationuse", "formationdel") RemasterFormationCommand(action, value)   // your own formations, Army: Formations (Formations.dm)
		if("formation") RemasterFormationPick(value)   // the selection's control group's, or the player's own (Formations.dm)
		if("formmove") RemasterFormMove(value)          // a drag to face (Formations.dm)
		if("fmgroup") RemasterGroupCommand(value)       // groups from the Company list, Ctrl+G, Ctrl-click (Formations.dm)
		if("designateheir", "crownheir", "succession_ok") RemasterSuccessionCommand(action, value)
		if("tab")
			if(value in list("units", "village", "orders", "work", "build", "guide", "realm", "army", "quests", "admin")) remaster_hud_tab = value   // army: Formations and Captives (hud-craft)
		if("select")
			var/mob/Monsters/M = RemasterUIUnit(value)
			if(istype(M) && M.Owner == src && (M in UnitList))
				RemasterClickSelect(M, remaster_multi)
				RemasterMilestone("select")
		if("multi") remaster_multi = !remaster_multi
		if("queue")
			if(!length(Selected))
				remaster_queue = 0
				RemasterNotice("Select a unit before adding tasks.")
			else remaster_queue = value == "add" ? 1 : value == "now" ? 0 : !remaster_queue
		if("view3d")
			// Always 3D: the page may still ask, but the view stays on.
			if(!remaster_3d)
				remaster_3d = 1
				remaster_3d_far_key = null
				remaster_3d_key = null
		if("click3d") Remaster3DClick(value)
		if("pickup3d") Rm3DPickUp(value)                        // the menu's Pick up (View3D.dm)
		if("gather") RemasterGatherToggle("[value]")          // the Gather switch: the button and the page's G (Gather.dm)
		if("selautounload") RemasterSelAutoUnload("[value]") // the Gather bar's Auto unload, the selected units (Gather.dm)
		if("carveramp")       // "x|y|shift|block": the menu's Carve into a ramp (Gather.dm)
			var/list/cr = splittext("[value]", "|")
			if(length(cr) >= 2) RemasterCarveRamp(locate(text2num(cr[1]), text2num(cr[2]), GROUND_LAYER), length(cr) >= 3 && cr[3] == "1", length(cr) >= 4 ? text2num(cr[4]) : null)
		if("work3d", "walk3d") RemasterMenuClick(action, value)   // the menu's Mine here / Chop it / Dig down here, or Walk here
		if("mapmove") RemasterMapMove(value)                       // a right-click on the minimap (Orders.dm)
		if("wallramp")
			var/list/wr = splittext("[value]", "|")
			if(length(wr) >= 2) RemasterWallRamp(locate(text2num(wr[1]), text2num(wr[2]), z))
		if("wallstairs")
			var/list/ws = splittext("[value]", "|")
			if(length(ws) >= 2) RemasterWallStairs(locate(text2num(ws[1]), text2num(ws[2]), z))
		if("carve")       // steps (0) or a ramp (1) up a mountain: "x|y|ramp|shift" (Mountains.dm)
			var/list/cv = splittext("[value]", "|")
			if(length(cv) >= 3) RemasterCarve(locate(text2num(cv[1]), text2num(cv[2]), z), cv[3] == "1", length(cv) >= 4 && cv[4] == "1")
		if("planadd")     // "priority|x,y,k/x,y,k/...|dig or build|stone or wood": Plan mode's marks queued as a plan (Plans.dm)
			var/list/pa = splittext("[value]", "|")
			if(length(pa) >= 2) RmPlanAdd(pa[2], pa[1], length(pa) >= 3 && pa[3] == "build" ? "build" : "dig", length(pa) >= 4 && pa[4] == "wood" ? "wood" : "stone")
		if("plandoor")    // "x,y/x,y/...": Plan mode's door marks (PlanPieces.dm)
			RmPlanDoors(value)
		if("planfloor")   // "stone or wood|x,y/x,y/...": Plan mode's floor marks (PlanPieces.dm)
			RmPlanFloors(value)
		if("planstep")    // "x,y,k,d/...": the steps of a building's stairs (PlanPieces.dm, the layered builder phase 3)
			RmPlanSteps(value)
		if("pmdesign")    // "save|name|text", "del|name", "list": Plan mode's saved designs (PlanPieces.dm)
			RmDesigns(value)
		if("mineroof")    // "x|y|shift|block": the block pointed at, mined up to (Gather.dm)
			var/list/mr = splittext("[value]", "|")
			remaster_click_block = length(mr) >= 4 ? text2num(mr[4]) : null
			if(length(mr) >= 2) RemasterMineRoof(locate(text2num(mr[1]), text2num(mr[2]), z), length(mr) >= 3 && mr[3] == "1")
			remaster_click_block = null
		if("tend")        // "x|y|percent": leave a tree or vein at that share (Yield.dm)
			var/list/td = splittext("[value]", "|")
			if(length(td) >= 3) RemasterTend(locate(text2num(td[1]), text2num(td[2]), z), text2num(td[3]))
		if("dblclick3d") Remaster3DDblClick(value)
		if("carryunit") RemasterCarryUnit(value)                    // TargetActions.dm
		if("carrybody") RemasterCarryBody(value)
		if("nearact") RmNearAct(value)
		if("selfsleep") RmSelfSleep(value)                      // a unit's own card (TargetActions.dm)
		if("favunit") RmFavToggle(value)                        // a favourite (TargetActions.dm)
		if("askanswer") RemasterAskAnswer(value)                    // AskCard.dm
		if("askcancel") RemasterAskCancel(value)
		if("companyroll") RemasterCompanyCommand(value)
		if("usecard") RemasterUseCardOpen(value)                   // UseCard.dm
		if("usecardrun") RemasterUseCardRun(value)
		if("usecardclose") remaster_use_card = null
		if("view3dsize")
			Remaster3DSize(value)
			RemasterHide2DMap()   // the page's 3D view runs: the 2D map under it goes
		if("hover3d")
			var/list/hp = splittext("[value]", "|")
			var/atom/HA = length(hp) >= 3 ? Remaster3DTarget(hp) : null
			RemasterHoverAt(HA)
			// the verdict is for the hovered tile (x, y); a click there works HA's tile (tx, ty: a ridge top becomes the
			// face block below it, View3D.dm), where the page outlines the block that will break (rts-feel)
			if(remaster_hover && isturf(HA))
				remaster_hover["x"] = text2num(hp[1])
				remaster_hover["y"] = text2num(hp[2])
				remaster_hover["tx"] = HA.x
				remaster_hover["ty"] = HA.y
				remaster_hover["blk"] = Remaster3DBlock(hp, HA)   // which of its two outside blocks a click would take
				if(remaster_hover["kind"] == "Mine" && isnum(remaster_hover["blk"]) && !RemasterReaches(0, remaster_hover["blk"]) && !RemasterSelectionOn(SKY_LAYER))   // Gather.dm
					remaster_hover["text"] = "Out of reach" + " · " + "a unit works three blocks up from where it stands"
					remaster_hover["bad"] = 1
					remaster_hover["ok"] = 0
		if("box3d") Remaster3DBox(value)
		if("combatstyle") RemasterCombatStyleCommand(value)
		if("boxrefs") Remaster3DBoxRefs(value)
		if("target3d") Remaster3DMagicTarget(value)
		if("paint3d") RemasterPaint(value)
		if("placeworkshop") RemasterPlaceWorkshop(value)
		if("blueprintcancel") RemasterBlueprintCancel(value)
		if("buildpick", "buildrotate", "buildceil", "siteassign", "siteunassign", "siteworkers", "sitepriority", "sitecancel", "sitegoto", "siteclear") RemasterConstructionCommand(action, value)
		if("stack3d")
			remaster_3d_stack = value == "1"
			remaster_3d_key = null
		if("xray3d")
			remaster_3d_xray = value == "1"
			remaster_3d_key = null
		if("villageview")
			if(value in list("roster", "lineage", "board", "log"))
				remaster_village_view = value
				remaster_hud_tab = "village"
		if("gotoplace") RemasterGotoPlace(value)
		if("boardpost", "boardcancel", "boardpriority", "boardclear", "standing") RemasterBoardCommand(action, value)
		if("lineagefocus")
			if(istext(value) && length(value) < 80) remaster_lineage_focus = value
		if("selectmany")
			// Village roster: replace the selection with the checked units.
			var/list/picked = list()
			for(var/ref in splittext("[value]", "|"))
				var/mob/Monsters/M = RemasterUIUnit(ref)
				if(istype(M) && M.Owner == src && (M in UnitList) && !M.Wagon && !(M in picked)) picked += M
			if(length(picked))
				RemasterClearSelection()
				var/added = 0
				for(var/mob/Monsters/M in picked) if(RemasterClickSelect(M, added)) added = 1
				RemasterNotice("Selected [length(Selected)] of [length(picked)] checked unit[length(picked) == 1 ? "" : "s"].")
		if("villagebulk")
			// Village roster and group card bulk change: "job|miner|ref,ref", "priority|1|...", "defense|self|...",
			// "lethal|nonlethal|..." or "style|aggressive|...".
			var/list/parts = splittext("[value]", "|")
			if(parts.len == 3 && (parts[1] in list("job", "priority", "defense", "lethal", "style")))
				var/list/commands = list("job"="unitjob", "priority"="unitpriority", "defense"="defensemode", "lethal"="unitlethal", "style"="unitstyle")
				var/command = commands[parts[1]]
				var/done = 0
				for(var/ref in splittext(parts[3], ","))
					if(RemasterUnitCommand(command, "[ref]|[parts[2]]")) done++
				var/units = "[done] unit[done == 1 ? "" : "s"]"
				if(parts[1] == "lethal") RemasterNotice(parts[2] == "nonlethal" ? "[units] now fight non-lethal: they knock enemies out instead of killing them." : "[units] now fight to kill.")
				else if(parts[1] == "style") RemasterNotice("[units] now fight [lowertext(rm_combat_styles[parts[2]] || parts[2])].")
				else RemasterNotice("Updated [units]: [parts[1]] set to [parts[2]].")
		if("unitpause", "unitresume", "unitstop", "autounload", "removeorder", "defensemode", "unitjob", "unitpriority", "unitgoto", "unitlethal", "unittend")
			RemasterUnitCommand(action, value)
		if("dropoff") RemasterDropOff(remaster_queue, 0)
		if("unloadresume") RemasterDropOff(0, 1)
		if("action", "borderaction") RemasterDeferHUDCommand(action,value)
		if("palette")
			spawn(0) RemasterPaletteRun(value)
		if("paletteclose") RemasterPaletteClose()
		if("controlgroup") RemasterControlGroupRequest(value)
		if("magictarget") RemasterMagicTargetChoose(value)
		if("magictargetclose") RemasterMagicTargetClose(value)
		if("border")
			if(value in list("show", "hide"))
				remaster_border_layout_version = 1
				remaster_border_visible = value == "show"
				RemasterApplyBorder()
				RemasterNotice(remaster_border_visible ? "Classic border shown. Labeled controls remain available." : "Classic border hidden. Use the command dock or open Controls.")
		if("build") RemasterBuildBasic(value)
		if("job", "workarea", "stockpile", "stockfilter", "priority", "craft", "cancel", "tendliving")
			RemasterSettlementCommand(action, value)
		if("idle") RemasterNextIdle()
		if("attack") RemasterJump()
		if("attackdismiss") RemasterClearAlert()
		if("layer")
			var/level = text2num(value)
			if(level == SKY_LAYER && !RmSkyOpen()) RmSkyShutNote()   // earned with a unit up there (Flying.dm)
			else if(level >= 1 && level <= world.maxz) loc = locate(x, y, level)
		if("pan")
			if(value in list("n", "s", "e", "w"))
				var/dx = value == "e" ? 6 : value == "w" ? -6 : 0
				var/dy = value == "n" ? 6 : value == "s" ? -6 : 0
				loc = locate(clamp(x + dx, 1, world.maxx), clamp(y + dy, 1, world.maxy), z)
		if("panpx") RemasterPanPixels(value)
		if("camunit")   // the camera onto one of your units wherever it is, its level too (a double-click on it; hud-craft, 10-25)
			var/mob/Monsters/CU = RemasterUIUnit(value)
			if(istype(CU) && CU.Owner == src)
				var/turf/CT = RemasterGetTurf(CU)
				if(CT)
					loc = CT
					RemasterCamTo(CT)
		if("camera")
			var/list/coords = splittext(value, ",")
			if(coords.len >= 3) remaster_3d_cam_seq = text2num(coords[3]) || 0   // the page's count of its camera sends: each scene says the one it was begun at (View3D.dm "jump")
			if(coords.len >= 2)
				var/X = text2num(coords[1])
				var/Y = text2num(coords[2])
				if(!isnull(X) && !isnull(Y)) loc = locate(clamp(round(X), 1, world.maxx), clamp(round(Y), 1, world.maxy), z)
		if("stance")
			if(value in list("hold", "guard", "aggressive"))
				for(var/mob/Monsters/M in Selected) if(M.Owner == src)
					M.RemasterCancelOrders()
					M.remaster_production = list()
					M.RemasterStopWork()
					M.remaster_job = "manual"
					M.HomeLoc = null
					if(M.GuardRules) M.GuardRules -= "Agressive"   // made on first use (Monster AI.dm)
					if(value != "hold")
						if(value == "aggressive")
							if(!M.GuardRules) M.GuardRules = list()
							M.GuardRules += "Agressive"
						M.Guarding()
					M.remaster_order_status = value == "hold" ? "Holding position" : value == "guard" ? "Guarding" : "Aggressive guard"
				RemasterMilestone("defend")
		if("inventory")
			var/obj/Items/I = RemasterUIItem(value)
			if(I)
				spawn(0)
					// Selection, cargo and ownership may change before this callback.
					if(I && RemasterUIItem(value) == I) RemasterInventoryUse(I)
		if("details")
			// Classic mode is retired: everything its tabs showed is in the HUD
			// (Character, the bag, the Company list, Controls).
			remaster_classic_info = 0
			RemasterLayoutPanes()
		if("log")
			remaster_log_open = !remaster_log_open
			RemasterLayoutPanes()
		if("trade") RemasterTradeCommand(value)
		if("market") RemasterMarketCommand(value)
		if("realm") RemasterRealmCommand(value)
		if("cave") RemasterCaveCommand(value)
		if("caveenter") RemasterCaveEnterOrder(value)
		if("speed") RemasterSetSpeed(value)
		if("pause") RemasterSetSpeed(rm_speed ? 0 : max(1, rm_speed_before_pause))
		if("attackmode")
			RemasterAttackModeToggle()
		if("cancelmode")
			RemasterSpecialCancel()
			remaster_attack_mode = 0
			RemasterCancelPlacement()
			RemasterNotice("Placement cancelled. Assigned work continues.")
		if("tutorial")
			remaster_tutorial_hidden = !remaster_tutorial_hidden
			if(remaster_tutorial_hidden) RmFirst("guide-skip")   // the first-steps guide hidden (FirstMinute.dm; the page's Skip guide)
	RemasterHUDTick()

// Each card request captures a specific owned unit. Removal also supplies the
// order ref: if the queue advanced after rendering, never remove another task.
Player/proc/RemasterUnitCommand(action, value)
	var/list/parts = splittext("[value]", "|")
	if(!parts.len) return 0
	var/mob/Monsters/M = RemasterUIUnit(parts[1])
	if(!istype(M) || M.Owner != src || !(M in UnitList) || M.Wagon) return 0
	switch(action)
		if("defensemode")
			if(parts.len != 2 || !(parts[2] in list("assist", "self", "off"))) return 0
			return RemasterDefenseMode(M, parts[2])
		if("unitlethal")
			if(parts.len != 2 || !(parts[2] in list("lethal", "nonlethal"))) return 0
			return RemasterUnitLethal(M, parts[2] == "nonlethal")
		if("unitstyle")
			if(parts.len != 2 || !(parts[2] in rm_combat_styles)) return 0
			M.remaster_combat_style = parts[2]
			return 1
		if("unitjob")
			if(parts.len != 2 || !(parts[2] in list("manual", "woodcutter", "miner", "hauler", "board", "builder", "farmer", "hunter", "cook", "merchant", "any"))) return 0
			M.RemasterAssignJob(parts[2])
			RemasterNotice("[M.name]: [parts[2] == "manual" ? "manual control" : parts[2] == "board" ? "now a board worker" : parts[2] == "builder" ? "now a builder: works on the Build tab's construction" : "now a [parts[2]]"].")
		if("unitpriority")
			if(parts.len != 2 || !(parts[2] in list("1", "2", "3"))) return 0
			M.remaster_priority = text2num(parts[2])
		if("unitgoto")
			if(isturf(M.loc)) loc = locate(M.x, M.y, RmViewLayer(M))   // its level's view (Peaks.dm)
		if("unitpause") M.RemasterPauseOrders(1)
		if("unitresume") M.RemasterPauseOrders(0)
		if("unitstop")   // the unit card's Stop: a patrol ends too, as with the Stop command (Orders.dm StopAll)
			M.RemasterStopOrders()
			M.remaster_patrol = null
			RemasterNotice("[M.RemasterBareName()] stopped.")
		if("unittend")    // tend living resources: the realm's setting, on, off, round again (Yield.dm)
			M.remaster_tend_mode = M.remaster_tend_mode == "" ? "on" : M.remaster_tend_mode == "on" ? "off" : ""
			var/realm = remaster_tend_living ? "on" : "off"
			if(M.remaster_tend_mode == "on") RemasterNotice("[M.name]: tends living resources: leaves trees at half and living ore blocks their last ore, so they grow back.")
			else if(M.remaster_tend_mode == "off") RemasterNotice("[M.name]: takes everything: fells whole trees and digs living ore blocks out (they die).")
			else RemasterNotice("[M.name]: follows the realm's setting (tend living resources: [realm]).")
		if("autounload")
			M.remaster_auto_unload = !M.remaster_auto_unload
			RemasterNotice("[M.name]: Auto unload [M.remaster_auto_unload ? "on" : "off"]. Only the stockpile's accepted resources are delivered. Tools, food and seeds stay carried.")
		if("removeorder")
			if(parts.len != 3) return 0
			var/index = text2num(parts[2])
			if(isnull(index) || index != round(index) || index < 1 || index > length(M.remaster_orders)) return 0
			var/datum/remaster_order/O = M.remaster_orders[index]
			if(!O || !O.remaster_ui_id || O.remaster_ui_id != parts[3])
				RemasterNotice("That task has already advanced. The list has been refreshed.")
				return 0
			M.RemasterRemoveOrder(index)
	return 1

client/Topic(href, list/h, hsrc)
	if(h["rm"])
		if(istype(mob, /Player))
			var/Player/P = mob
			if(!P.RemasterHUDSelectionAuthorized(h["rm"],h["value"],h["selection"]))
				P.RemasterNotice("Selection changed; choose the command again. Assigned work continues.")
				P.RemasterHUDTick()
				return
			P.RemasterTouchCommand(h["rm"], h["value"])
		return
	return ..()

// Login should show the same inline guidance as F3, never an obsolete popup.
Player/Intro()
	RemasterHUDShow()

obj/Hud/MSG/DblClick()
	if(istype(usr, /Player)) usr:RemasterMessage()

obj/Hud/Warp/DblClick()
	if(istype(usr, /Player)) usr:RemasterCoordinates()

// The original HUD.dmi icons the overlay HUD draws on its action bar and top bar.
Player/proc/RemasterHudIcons()
	if(rm_hud_icons && rm_hud_icons_client == client) return rm_hud_icons   // one table a client: kept, and its JSON reused (RemasterHUDKeysDelta)
	var/list/I = list()
	for(var/id in list("stop", "interact", "goto", "pointer", "area", "who", "all", "waypoint", "build", "daynight-sun", "daynight-moon", "msg", "equip", "autodig", "updates", "race"))
		I[id] = RemasterBorderIcon(id)
	rm_hud_icons = I
	rm_hud_icons_client = client
	return I
Player/var/tmp/list/rm_hud_icons
Player/var/tmp/client/rm_hud_icons_client

// Cinematic camera for recorded shots: list(dist, pitch, spin, hud) or null (normal play).
Player/var/tmp/list/remaster_cine

// The band card's Fly row (hud-craft, 10-25): of the selected flyers in the air, how many can go up a height (or up to
// the Sky level) and how many down one (or down to the surface), as RmFlySelection would move them; null when none is
// flying, so the row shows only then.
Player/proc/RmHudSelFly()
	var/up = 0
	var/down = 0
	for(var/mob/Monsters/M in Selected) if(M.Flying && M.Owner == src && M.HP > 0)
		if(M.rm_fly_level < length(RmFlyList(M)) || RmCanFlyUp(M)) up++
		if(M.rm_fly_level > 1 || M.z == SKY_LAYER) down++
	return (up || down) ? list(up, down) : null
