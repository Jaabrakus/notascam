// Dungeon Master Remastered: Warcraft-style quality of life on top of the
// original game. Everything here layers over the original procedures and hands
// anything it does not handle back to them with ..(); the original files are
// unchanged. Controls added:
//   Left-click your unit ........ select only that unit
//   Shift+left-click your unit .. add/remove it from the selection
//   Double-click your unit ...... select all your units of that race in view
//   Drag a box on the map ....... select your units inside (Shift+drag adds)
//   Right-click ................. open the original context/verb dropdown
//   Left-click a work target .... order the selection (move, chop, mine, collect)
//   1-9 / Ctrl+1-9 / Shift+1-9 .. select / set / add control groups (original
//                                 Alt+number keys still work; tap twice to jump)
//   Backspace ................... jump the view to the last unit under attack
// Your units also show health bars, and you are told when one is attacked.

#define REMASTER_ALERT_DELAY 100   // ticks between "under attack" alerts
#define REMASTER_ALERT_SHOWN 300   // the alert button hides 30 seconds after the last hit
#define REMASTER_TRACK_DELAY 5     // ticks between health bar/alert updates

client
	var/tmp/atom/remaster_double_target
	var/tmp/remaster_double_time = -100
	// Right-drag camera pans (2D map): the engine still reports the right button's
	// release as a click or a drop, which a pan must not turn into a menu or a box.
	var/tmp/remaster_pan_time = -100
	var/tmp/remaster_pan_fx = 0
	var/tmp/remaster_pan_fy = 0

Player
	var/tmp/list/remaster_bars
	var/tmp/mob/Monsters/remaster_alert_unit
	var/tmp/remaster_alert_ready = 0
	var/tmp/remaster_alert_at = 0       // last hit; the alert hides after REMASTER_ALERT_SHOWN

mob/Monsters
	var/tmp/remaster_last_hp

// --- Selection ---------------------------------------------------------------

Player/proc/RemasterCancelPlacement()
	Function = null
	if(Up)
		Up = 0
		if(client) for(var/obj/HUD/H in client.screen) del(H)

// Deleted atoms can remain null list slots. Normalize at selection and HUD
// boundaries so badges and commands describe the actual surviving selection.
Player/proc/RemasterNormalizeSelection()
	var/list/current = list()
	// "M in UnitList" for each of a big selection was selection x company list searches every send (200 of 5,000:
	// a million), and "M in current" square in the selection: marks on the units instead (HudView.dm rm_hud_serial;
	// a set would be square too, adding a key scans the list here; hud-craft, 10-24)
	// The company is marked again only every 2 s or when its length changes (30,000 units: 23 ms a send). Every way
	// out of UnitList also changes the owner, kills the unit or deselects it, so a stale mark can't keep a stray; a unit
	// that joined since is looked for in the list.
	var/mk = length(Selected) > 32 ? RmCompanyMark() : 0
	var/dk = ++rm_hud_serial
	for(var/mob/Monsters/M in Selected.Copy())
		// Preserve the original developer DblClick FreeSelect gate. This does
		// not grant it, and modern commands keep their own ownership checks.
		if(((M.Owner == src && ((mk ? (M.rm_hud_umark == mk || (M in UnitList)) : (M in UnitList)) || RemasterIsSiege(M))) || (DE && FreeSelect)) && M.HP > 0 && !M.GoingToDie)
			if(M.rm_hud_dmark != dk)
				M.rm_hud_dmark = dk
				current += M
		else M.Deselect(src)
	if(length(current) != length(Selected)) remaster_queue = 0
	Selected = current

Player/proc/RemasterClearSelection()
	// Selection and input modes belong to the player; work belongs to units.
	// Never call Stop/Pause or change their active, pending or role work here.
	for(var/mob/Monsters/M in Selected.Copy()) M.Deselect(src)
	Selected = list()
	remaster_multi = 0
	remaster_queue = 0
	RemasterCancelPlacement()
	if(islist(remaster_patrol_draft))   // a patrol route being drawn is for the selection: it goes with it (Patrol.dm), or every click after added a point
		remaster_patrol_draft = null
		RemasterNotice("Deselected; the patrol route being drawn is cancelled. Assigned work continues.")
		RemasterHUDTick()
		return
	RemasterNotice("Deselected. Assigned work continues. Click a unit to select it.")
	RemasterHUDTick()

// Space and the HUD button share the original Zip command.
Player/Zip()
	RemasterClearSelection()

Player/proc/RemasterClickSelect(mob/Monsters/M, add)
	if(!M || M.Owner != src || !(M in UnitList))
		RemasterNotice("That unit is no longer available to select. Current selection kept.")
		return 0
	// Removing a selected unit remains possible after it falls asleep or enters
	// a hole/container. Those states reject new selection, not deselection.
	if(add && (M in Selected))
		M.Deselect(src)
		if(M in Selected) return 0
		RemasterNormalizeSelection()
		remaster_queue = 0
		return 1
	// Modern selection normalization already excludes dead/dying members. Do
	// not briefly add one and then let normalization erase the old selection.
	if(M.HP <= 0 || M.GoingToDie)
		RemasterNotice("That unit is no longer alive. Current selection kept.")
		return 0
	// Select owns the original eligibility rules and image handling. Its no-op
	// path must not clear the previous selection or consume Add tasks mode.
	M.Select(src)
	if(!(M in Selected))
		var/reason = M.Sleeping ? "That unit is sleeping" : M.InHole ? "That unit is in a hole" : !isturf(M.loc) ? "That unit is inside something" : "That unit can't be selected"
		RemasterNotice("[reason]. Current selection kept.")
		return 0
	RemasterNormalizeSelection()
	remaster_queue = 0
	if(!add)
		for(var/mob/Monsters/S in Selected.Copy()) if(S != M) S.Deselect(src)
	return 1

Player/proc/RemasterSelectAlike(mob/Monsters/M)
	RemasterNormalizeSelection()
	remaster_queue = 0
	var/list/area = view(src)
	for(var/mob/Monsters/S in Selected) if(S.Race != M.Race) S.Deselect(src)
	for(var/mob/Monsters/U in area) if(U.Owner == src && U.Race == M.Race) U.Select(src)

Player/proc/RemasterBoxSelect(turf/A, turf/B, add)
	RemasterNormalizeSelection()
	remaster_queue = 0
	if(!add) for(var/mob/Monsters/S in Selected) S.Deselect(src)
	var/count = 0
	for(var/turf/T in block(A, B))
		for(var/mob/Monsters/M in T) if(M.Owner == src)
			M.Select(src)
			if(M in Selected) count++
	return count

// Also cover keyboard groups, area selection and Space without changing work.
mob/Select(mob/USER = Owner)
	var/was_selected = USER && (src in USER.Selected)
	// A sleeping unit can be selected (the original refuses): an order wakes it (Orders.dm).
	if(Sleeping && !Egg && !InHole && ismob(USER) && Owner == USER && !ismob(loc) && !isobj(loc))
		if(!was_selected)
			USER.Selected.Add(src)
			if(USER.client) USER.client.images += Star
	else . = ..()
	if(istype(USER, /Player) && !was_selected && (src in USER.Selected)) USER:remaster_queue = 0

mob/Deselect(Player/USER = Owner)
	var/was_selected = USER && (src in USER.Selected)
	. = ..()
	if(istype(USER, /Player) && was_selected) USER.remaster_queue = 0

proc/RemasterTapPaintMode(mode)
	// Only these modes are implemented by turf/MouseDrag. Patrol, arrow slits
	// and tapestries belong to the original client/Click path instead.
	// Furniture and webs (Buildings.dm, "Piece:") are only ever planned, never built at once.
	if(copytext("[mode]", 1, 7) == "Piece:" || RemasterIsHallMode(mode)) return 1   // halls are dragged to size
	return mode in list("Pyrokinesis", "Forcefield", "Telekinesis", "PlaceAutodig", "RemoveAutodig", "PlaceStoneBridge", "PlaceSilkBridge", "PlaceBoneBridge", "PlaceTribalBridge", "PlaceWoodenBridge", "DestroyFloor", "PlaceStoneFloor", "PlaceTribalFloor", "PlaceDevourerFloor", "PlaceBoneFloor", "PlaceWoodenFloor", "PlaceBoneWall", "PlaceSilkWall", "PlaceDevourerWall", "PlaceTribalWall", "PlaceSecretWall", "PlaceStoneWall", "PlaceBoneSpikes", "PlaceStoneFall", "DigChannel", "PlaceRibcage", "PlaceElfWall", "PlaceWoodenWall", "FortressWall", "PlaceStoneRoad", "PlaceDirtRoad", "RemoveRoad", "Beam")

proc/RemasterTurf(atom/A, atom/location)
	if(isturf(location)) return location
	if(isturf(A)) return A
	if(istype(A) && A.z) return locate(A.x, A.y, A.z)

Player/proc/RemasterLegacyHandoff()
	var/paused = 0
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || !(M in UnitList)) continue
		if(M.RemasterHasOrder()) paused++
		M.RemasterManualHandoff(src)
	if(paused) RemasterNotice("Task queue paused for direct interaction; Resume continues it.")

// What a click on the map tells the selected units to do: attack a hostile (or anything
// in Attack mode), or move / chop / mine / pick up. Returns how many units took the
// order, or null when the click is not an order (own units select, workshops open).
Player/proc/RemasterMapOrder(atom/m, shift, right)
	if(Function || !m || !m.z || !length(Selected)) return null
	var/mob/Monsters/first = Selected[1]
	// A knocked-out enemy or animal: the click takes it (Subdue.dm); Attack mode still attacks.
	if(!right && !remaster_attack_mode && istype(m, /mob/Monsters) && istype(first) && m:Owner != src && m:RemasterSubdued() && !RemasterCapturable(first, m))
		return RemasterCaptureOrder(m)
	if(!right && (remaster_attack_mode || (istype(m, /mob/Monsters) && istype(first) && m:Owner != src && RemasterHostile(first, m))))
		return RemasterAttackOrder(m)
	if(!right && istype(m, /mob/Monsters) && m:Owner != src && m:rm_keeper && RmKeeperOk(m)) return RmKeeperClick(m)   // talk to a keeper (QuestKeepers.dm)
	if(istype(m, /mob/Monsters) && m:Owner == src) return null
	if(istype(m, /mob/WorkShops)) return null
	if(RemasterOrderKind(m)) return RemasterOrder(m, shift || remaster_queue, RemasterPointerKind(m))   // the Gather switch (Gather.dm)
	return null

client/Click(atom/m, location, control, params)
	var/list/P = params2list(params)
	if(P["right"] && world.time - remaster_pan_time <= 10) return
	// Aiming a race special (Specials.dm): the click aims it; a right-click cancels.
	if(istype(mob, /Player) && length(mob:remaster_aim) && !istype(m, /obj/Hud) && !istype(m, /obj/HUD) && !istype(m, /obj/RemasterAction))
		if(P["right"]) mob:RemasterSpecialCancel()
		else mob:RemasterSpecialClick(m)
		return
	if(istype(mob, /Player) && !istype(m, /obj/Hud) && !istype(m, /obj/HUD) && mob:RemasterPatrolClick(m)) return
	if(istype(mob, /Player) && !istype(m, /obj/Hud) && !istype(m, /obj/HUD) && mob:RemasterThrowClick(m)) return
	// HUD icons, build-menu buttons and Actions rows run on one click (Actions.dm).
	if(istype(m, /obj/Hud) || istype(m, /obj/HUD) || istype(m, /obj/RemasterAction))
		if(!P["right"]) RemasterButton(m)
		return
	// Siege engines (Siege.dm): a click selects one; with one selected, a click on a wall,
	// door or the ground orders it (Attack mode goes through RemasterAttackOrder).
	if(istype(mob, /Player) && !mob.Function && !P["right"] && RmIsShip(m) && m:Owner == mob && !mob:remaster_attack_mode && mob:RmShipBoardOrder(m)) return   // people selected: aboard (Ships.dm)
	if(istype(mob, /Player) && !mob.Function && !P["right"] && RemasterIsSiege(m) && m:Owner == mob && !mob:remaster_attack_mode)
		mob:RemasterSiegeSelect(m, P["shift"] || mob:remaster_multi)
		return
	if(istype(mob, /Player) && !mob.Function && !P["right"] && m && m.z && !mob:remaster_attack_mode && length(mob:RemasterSelectedSiege()) && !(istype(m, /mob/Monsters) && m:Owner == mob))
		var/sn = mob:RemasterSiegeOrder(m)
		var/others = 0
		for(var/mob/Monsters/O in mob.Selected) if(!RemasterIsSiege(O)) others++
		if(sn && !others) return
	// A fishing spot (Fishing.dm): the selected units fish it with Gather on, else walk to the shore by it (Gather.dm).
	if(istype(mob, /Player) && !mob.Function && !P["right"] && !mob:remaster_attack_mode && length(mob.Selected) && m && m.z)
		var/fishy = istype(m, /obj/RemasterFishSpot)
		if(!fishy && isturf(m)) for(var/obj/RemasterFishSpot/FS in m) fishy = 1
		if(fishy && mob:RemasterGathering() && mob:RemasterFishOrder(m)) return
		if(fishy && !mob:RemasterGathering() && mob:RemasterOrder(isturf(m) ? m : m.loc, P["shift"] || mob:remaster_queue, "Move")) return
	if(istype(mob, /Player) && !isnull(mob:RemasterMapOrder(m, P["shift"], P["right"]))) return
	if(istype(mob, /Player) && RemasterTapPaintMode(mob.Function) && isturf(m))
		// The original placement procedures also work for a single tile tap.
		m.MouseDrag(m)
		return
	if(istype(mob, /Player) && !mob.Function && istype(m, /mob/Monsters) && !istype(m, /mob/Monsters/Chests) && !m:Wagon && m:Owner == mob)
		// The second click of a double-click belongs to DblClick().
		if(m == remaster_double_target && world.time - remaster_double_time <= 1) return
		mob:RemasterClickSelect(m, P["shift"] || mob:remaster_multi)
		return
	if(istype(mob, /Player) && !mob.Function && istype(m, /mob/WorkShops))
		// Migrated workshops hand off only after a recipe/destroy action passes its gates.
		// Other workshop families retain their current handoff until migrated.
		// Never turn a workshop click into movement collision / melee damage.
		var/remaster_cooking_fire = istype(m, /mob/WorkShops/CampFires) && !istype(m, /mob/WorkShops/CampFires/GoodAltar) && !istype(m, /mob/WorkShops/CampFires/EvilAltar)
		if(!istype(m, /mob/WorkShops/Carpentry) && !istype(m, /mob/WorkShops/Masonary) && !istype(m, /mob/WorkShops/Smelters) && !istype(m, /mob/WorkShops/Kitchen) && !remaster_cooking_fire && !istype(m, /mob/WorkShops/CampFires/GoodAltar) && !istype(m, /mob/WorkShops/CampFires/EvilAltar) && !istype(m, /mob/WorkShops/Melter) && !istype(m, /mob/WorkShops/Forge) && !istype(m, /mob/WorkShops/PoisonStation) && !istype(m, /mob/WorkShops/GemCutter) && !istype(m, /mob/WorkShops/PotionStation) && !istype(m, /mob/WorkShops/BoneCraft) && !istype(m, /mob/WorkShops/LeatherWorks)) mob:RemasterLegacyHandoff()
		if(mob:RemasterWalkToStation(m)) return   // nobody beside it: the nearest walks over, the menu opens there (Orders.dm)
		RemasterButton(m)
		return
	if(istype(m, /obj/Items) && ismob(m.loc) && m.loc:Owner == mob)
		if(istype(mob, /Player)) mob:RemasterInventoryUse(m)
		else m.DblClick()
		return
	if(istype(mob, /Player) && !mob.Function && m && m.z && length(mob.Selected))
		mob:RemasterLegacyHandoff()
	return ..()

mob/Monsters/DblClick()
	if(Owner == usr && istype(usr, /Player) && !usr.Function && !Wagon && !istype(src, /mob/Monsters/Chests))
		if(usr.client)
			usr.client.remaster_double_target = src
			usr.client.remaster_double_time = world.time
		usr:RemasterSelectAlike(src)
		return
	return ..()

client/MouseDrop(src_object, over_object, src_location, over_location, src_control, over_control, params)
	if(params2list(params)["right"]) return
	var/turf/A = RemasterTurf(src_object, src_location)
	var/turf/B = RemasterTurf(over_object, over_location)
	if(istype(mob, /Player) && !mob.Function && A && B && A != B && A.z == B.z)
		var/list/P = params2list(params)
		mob:RemasterBoxSelect(A, B, P["shift"])
		return
	return ..()

// --- Health bars and attack alerts -------------------------------------------

// world/New: this file's part is step RmChainWorldNew_QoL in Code/Remastered/Chains/WorldNew.dm

// Each player's track every REMASTER_TRACK_DELAY ticks, spread over ticks so it never holds one up (Spread.dm).
proc/RemasterLoop()
	while(1)
		sleep(1)
		for(var/client/C)
			if(istype(C.mob, /Player)) C.mob:RmTrackDue()

// With spread (the loop's runs), it goes on into the next tick at the safe points once a tick's share is used.
Player/proc/RemasterTrack(spread = 0)
	RemasterAwayTick()               // the village catches up on the time you were away (Away.dm)
	if(remaster_catching_up) return
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && (M.x != M.rm_touched_x || M.y != M.rm_touched_y || M.z != M.rm_touched_z)) RemasterTouchAround(M)   // same tile: nothing to touch (WorldSave.dm)
	RemasterExploreTick(spread)
	if(spread) RmTrackPause()
	RemasterTouchCreatures()
	RemasterBagTick(spread)
	RemasterPatrolTick()
	RemasterDayTick()
	RemasterCareTick(spread)
	RemasterBlueprintTick(spread)
	RemasterSkillTick(spread)
	RemasterBoardTick()
	RmQuestReachTick()               // reach quests (QuestTargets.dm)
	if(spread) RmTrackPause()
	RemasterOrdersTick(spread)
	if(spread) RmTrackPause()
	RemasterCaptiveTick()               // captives led on a rope (Subdue.dm)
	RemasterSettlementTick(spread)
	RemasterPlayModeTick()
	if(spread) RmTrackPause()
	RemasterHUDTick(spread)
	if(spread) RmTrackPause()
	Remaster3DTick(spread)
	if(spread) RmTrackPause()
	// Health bars on the 2D map. In 3D (always, since 2026-10-21) the view hides that map and draws its own bars from each
	// unit's "hp" (View3D.dm, remastered.html v3bars), so they would only be work nobody sees.
	var/list/kept = list()
	for(var/mob/Monsters/M in UnitList)
		if(!remaster_3d)
			var/state = "[M.RemasterHealthState()]"
			var/image/bar = remaster_bars && remaster_bars[M]
			if(!bar)
				bar = image('Icons/Remastered/HPBar.dmi', M, state, FLY_LAYER)
				bar.pixel_y = 6 // Keep the original selection Star visible below the health bar.
			else if(bar.icon_state != state) bar.icon_state = state   // set only when it changes: each set makes a new appearance
			kept[M] = bar
			if(client && !(bar in client.images)) client.images += bar
		M.RemasterCheckAttack(src)
	if(remaster_bars && client)
		for(var/old in remaster_bars) if(old && !kept[old]) client.images -= remaster_bars[old]
	remaster_bars = kept

mob/Monsters/proc/RemasterHealthState()
	if(MAXHP <= 0) return 0
	return round(max(0, min(HP, MAXHP)) * 10 / MAXHP)

mob/Monsters/proc/RemasterCheckAttack(Player/P)
	var/hurt = !isnull(remaster_last_hp) && HP < remaster_last_hp
	remaster_last_hp = HP
	if(!hurt) return
	for(var/mob/Monsters/Enemy in oview(2, src))
		if(Enemy.Owner != Owner)
			if(P.remaster_alert_unit == src || world.time >= P.remaster_alert_ready) P.remaster_alert_at = world.time
			if(world.time < P.remaster_alert_ready) return
			P.remaster_alert_unit = src
			P.remaster_alert_ready = world.time + REMASTER_ALERT_DELAY
			P << "<b><font color=red>[src] is under attack at [x],[y]! Press Backspace to go there.</font></b>"
			return

Player/verb/RemasterJump()
	set hidden = 1
	if(remaster_alert_unit && remaster_alert_unit.z)
		loc = locate(remaster_alert_unit.x, remaster_alert_unit.y, remaster_alert_unit.z)
		RemasterCamTo(remaster_alert_unit)
	RemasterClearAlert()

// Shown while the attacked unit lives and was hit in the last 30 seconds.
Player/proc/RemasterAlertShown()
	var/mob/Monsters/M = remaster_alert_unit
	if(!M || M.HP <= 0 || M.Owner != src || world.time - remaster_alert_at > REMASTER_ALERT_SHOWN)
		remaster_alert_unit = null
		return 0
	return 1

Player/proc/RemasterClearAlert()
	remaster_alert_unit = null
	remaster_alert_at = 0

// The original Logout() works on usr. The engine leaves usr empty when a mob
// logs out without a player action (window closed, test players deleted), so
// give it the mob itself, as BYOND does.
Player/Logout()
	if(!usr) usr = src
	return ..()

// Right-drag on the 2D map moves the camera. The Mac app sends the drag in window
// points ("dx|dy|width|height", y down); the view is client.view tiles across that
// window, so points turn into tiles and the remainder carries to the next step.
Player/proc/RemasterPanPixels(value)
	if(!client) return
	var/list/v = splittext(value, "|")
	if(v.len != 4) return
	var/dx = text2num(v[1])
	var/dy = text2num(v[2])
	var/w = text2num(v[3])
	var/h = text2num(v[4])
	if(isnull(dx) || isnull(dy) || !w || !h) return
	var/list/view = splittext("[client.view]", "x")
	var/cols = view.len == 2 ? text2num(view[1]) : client.view * 2 + 1
	var/rows = view.len == 2 ? text2num(view[2]) : client.view * 2 + 1
	client.remaster_pan_time = world.time
	if(remaster_lock)
		remaster_lock = null
		RemasterNotice("Camera free.")
	client.remaster_pan_fx -= dx * cols / w
	client.remaster_pan_fy += dy * rows / h
	var/tx = round(client.remaster_pan_fx)
	var/ty = round(client.remaster_pan_fy)
	if(client.remaster_pan_fx < 0 && tx != client.remaster_pan_fx) tx++
	if(client.remaster_pan_fy < 0 && ty != client.remaster_pan_fy) ty++
	if(!tx && !ty) return
	client.remaster_pan_fx -= tx
	client.remaster_pan_fy -= ty
	loc = locate(clamp(x + tx, 1, world.maxx), clamp(y + ty, 1, world.maxy), z)
