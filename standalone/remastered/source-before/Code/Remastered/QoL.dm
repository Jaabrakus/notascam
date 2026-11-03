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
#define REMASTER_TRACK_DELAY 5     // ticks between health bar/alert updates

client
	var/tmp/atom/remaster_double_target
	var/tmp/remaster_double_time = -100

Player
	var/tmp/list/remaster_bars
	var/tmp/mob/Monsters/remaster_alert_unit
	var/tmp/remaster_alert_ready = 0

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
	for(var/mob/Monsters/M in Selected.Copy())
		// Preserve the original developer DblClick FreeSelect gate. This does
		// not grant it, and modern commands keep their own ownership checks.
		if(((M.Owner == src && (M in UnitList)) || (DE && FreeSelect)) && M.HP > 0 && !M.GoingToDie)
			if(!(M in current)) current += M
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
	RemasterNotice("Deselected. Assigned work continues. Tap a unit to select it.")
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
		var/reason = M.Sleeping ? "That unit is sleeping" : M.InHole ? "That unit is in a hole" : !isturf(M.loc) ? "That unit is inside another object" : "That unit cannot be selected"
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
	. = ..()
	if(istype(USER, /Player) && !was_selected && (src in USER.Selected)) USER:remaster_queue = 0

mob/Deselect(Player/USER = Owner)
	var/was_selected = USER && (src in USER.Selected)
	. = ..()
	if(istype(USER, /Player) && was_selected) USER.remaster_queue = 0

proc/RemasterTapPaintMode(mode)
	// Only these modes are implemented by turf/MouseDrag. Patrol, arrow slits
	// and tapestries belong to the original client/Click path instead.
	return mode in list("Pyrokinesis", "Forcefield", "Telekinesis", "PlaceAutodig", "RemoveAutodig", "PlaceStoneBridge", "PlaceSilkBridge", "PlaceBoneBridge", "PlaceTribalBridge", "PlaceWoodenBridge", "DestroyFloor", "PlaceStoneFloor", "PlaceTribalFloor", "PlaceDevourerFloor", "PlaceBoneFloor", "PlaceWoodenFloor", "PlaceBoneWall", "PlaceSilkWall", "PlaceDevourerWall", "PlaceTribalWall", "PlaceSecretWall", "PlaceStoneWall", "PlaceBoneSpikes", "PlaceStoneFall", "DigChannel", "PlaceRibcage", "PlaceElfWall", "PlaceWoodenWall")

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

client/Click(atom/m, location, control, params)
	var/list/P = params2list(params)
	// HUD icons, build-menu buttons and Actions rows run on one click (Actions.dm).
	if(istype(m, /obj/Hud) || istype(m, /obj/HUD) || istype(m, /obj/RemasterAction))
		if(!P["right"]) RemasterButton(m)
		return
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
		RemasterButton(m)
		return
	if(istype(mob, /Player) && !mob.Function && m && m.z && length(mob.Selected))
		var/kind = RemasterOrderKind(m)
		if(kind in list("Move", "Chop", "Mine", "Pick up"))
			mob:RemasterOrder(m, P["shift"] || mob:remaster_queue)
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
	var/turf/A = RemasterTurf(src_object, src_location)
	var/turf/B = RemasterTurf(over_object, over_location)
	if(istype(mob, /Player) && !mob.Function && A && B && A != B && A.z == B.z)
		var/list/P = params2list(params)
		mob:RemasterBoxSelect(A, B, P["shift"])
		return
	return ..()

// --- Health bars and attack alerts -------------------------------------------

world/New()
	spawn(10) RemasterLoop()
	return ..()

proc/RemasterLoop()
	while(1)
		sleep(REMASTER_TRACK_DELAY)
		for(var/client/C)
			if(istype(C.mob, /Player)) C.mob:RemasterTrack()

Player/proc/RemasterTrack()
	RemasterCareTick()
	RemasterOrdersTick()
	RemasterSettlementTick()
	RemasterHUDTick()
	var/list/kept = list()
	for(var/mob/Monsters/M in UnitList)
		var/state = "[M.RemasterHealthState()]"
		var/image/bar = remaster_bars && remaster_bars[M]
		if(!bar) bar = image('Icons/Remastered/HPBar.dmi', M, state, FLY_LAYER)
		else if(bar.icon_state != state) bar.icon_state = state
		bar.pixel_y = 6 // Keep the original selection Star visible below the health bar.
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
	if(!hurt || world.time < P.remaster_alert_ready) return
	for(var/mob/Monsters/Enemy in oview(2, src))
		if(Enemy.Owner != Owner)
			P.remaster_alert_unit = src
			P.remaster_alert_ready = world.time + REMASTER_ALERT_DELAY
			P << "<b><font color=red>[src] is under attack at [x],[y]! Press Backspace to go there.</font></b>"
			return

Player/verb/RemasterJump()
	set hidden = 1
	if(remaster_alert_unit && remaster_alert_unit.z)
		loc = locate(remaster_alert_unit.x, remaster_alert_unit.y, remaster_alert_unit.z)
