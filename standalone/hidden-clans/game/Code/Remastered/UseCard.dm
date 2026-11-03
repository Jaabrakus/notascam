// "Use / open" on a workshop (the 3D right-click card) opens the Interact card (remastered.html): everything
// its original menus offer, instead of the native question. The menus are read with the station stand-in
// (StationCraft.dm: a unit of the same race far from the station, carrying nothing), so reading never makes
// anything. A choice is made by the selected unit, which walks over first when it isn't beside the station;
// any later question (a material, an amount) is asked as usual. Anything that isn't a workshop keeps the
// original double-click.

Player/var/tmp/list/remaster_use_card    // list("id", "title", "x", "y", "unit", "options"=list(list("label","group","path")))

// A workshop's name as players know it: the original names the parts of a two-tile workshop "Left" and
// "Right"; those say what the workshop is instead (the 3D cards and statuses use this).
proc/RemasterStationName(mob/WorkShops/W)
	var/n = "[W.name]"
	// the original names some parts "CarpentryCraftingStation", "LeatherCraftingStation": use the station's own name (playtest)
	if(!(n in list("Left", "Right", "Middle", "Centre", "Center", "Top", "Bottom", "Front", "Back")) && !findtext(n, "CraftingStation")) return n
	var/list/defs = RemasterStationDefs()
	for(var/id in defs)
		var/list/D = defs[id]
		if(istype(W, D[2])) return D[1]
	var/list/parts = splittext("[W.type]", "/")
	return length(parts) >= 2 ? RemasterSpaced(parts[length(parts) - 1]) : n

// "BoneCraft" -> "Bone Craft"
proc/RemasterSpaced(t)
	. = ""
	for(var/i = 1, i <= length(t), i++)
		var/c = copytext(t, i, i + 1)
		if(i > 1 && c != lowertext(c) && copytext(t, i - 1, i) == lowertext(copytext(t, i - 1, i))) . += " "
		. += c

Player/proc/RemasterUseCardUnit()
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0 && !M.GoingToDie && !M.Wagon && !RemasterIsSiege(M)) return M
	return null

Player/proc/RemasterUseCardOpen(value)
	var/atom/A = Remaster3DTarget(splittext("[value]", "|"))
	if(!istype(A, /mob/WorkShops) || !RemasterUseCardFor(A)) return Remaster3DDblClick(value)
	return 1

// Opens the card for a workshop: 0 when its menus offer nothing to choose (then it is used directly).
Player/proc/RemasterUseCardFor(mob/WorkShops/W)
	var/mob/Monsters/M = RemasterUseCardUnit()
	var/list/recipes = RemasterStationRecipes(W, M ? M.Race : "Human")
	if(!length(recipes)) return 0
	var/list/opts = list()
	for(var/list/R in recipes)
		var/list/path = R["path"]
		opts += list(list("label"="[R["label"]]", "group"=(length(path) > 1 ? "[path[1]]" : ""), "path"=path.Copy()))
	remaster_use_card = list("id"="\ref[W]", "title"=RemasterStationName(W), "x"=W.x, "y"=W.y, "unit"=(M ? M.RemasterBareName() : null), "options"=opts)
	return 1

// What the HUD shows of the open card (the answer paths stay here).
Player/proc/RemasterUseCardData()
	var/list/C = remaster_use_card
	if(!C) return null
	var/mob/WorkShops/W = locate(C["id"])
	if(!istype(W) || W.z != z)
		remaster_use_card = null
		return null
	var/list/opts = list()
	for(var/list/O in C["options"]) opts += list(list("label"=O["label"], "group"=O["group"]))
	var/mob/Monsters/M = RemasterUseCardUnit()
	return list("id"=C["id"], "title"=C["title"], "unit"=(M ? M.RemasterBareName() : null), "near"=(M && get_dist(M, W) <= 1), "options"=opts)

// "index": make that option, by the selected unit.
Player/proc/RemasterUseCardRun(value)
	var/list/C = remaster_use_card
	if(!C) return 0
	var/list/opts = C["options"]
	var/i = text2num("[value]")
	if(!isnum(i) || i < 1 || i > length(opts)) return 0
	var/mob/WorkShops/W = locate(C["id"])
	var/mob/Monsters/M = RemasterUseCardUnit()
	var/list/O = opts[i]
	remaster_use_card = null
	if(!istype(W))
		return 0
	if(!M)
		RemasterNotice("Select a unit to use the [RemasterStationName(W)].")
		return 0
	if(get_dist(M, W) > 1 || M.z != W.z)
		M.RemasterCancelOrders()
		M.remaster_patrol = null   // a direct order ends a patrol (Patrol.dm)
		M.destination = W
		M.remaster_order_status = "Going to the [RemasterStationName(W)]"
		RemasterNotice("[M.RemasterBareName()] goes to the [RemasterStationName(W)] for [O["label"]].")
		spawn(0) RemasterUseCardWhenThere(M, W, O["path"])
		return 1
	spawn(0) RemasterUseCardDo(M, W, O["path"])
	return 1

Player/proc/RemasterUseCardWhenThere(mob/Monsters/M, mob/WorkShops/W, list/path)
	for(var/t = 0, t < 120, t++)
		sleep(5)
		if(!M || !W || M.HP <= 0 || M.z != W.z) return
		if(get_dist(M, W) <= 1) return RemasterUseCardDo(M, W, path)
		if(M.destination != W) return      // given another order on the way
	if(M && W) RemasterNotice("[M.RemasterBareName()] couldn't reach the [RemasterStationName(W)].")

// The original menu with those answers; questions after them are asked as usual.
Player/proc/RemasterUseCardDo(mob/Monsters/M, mob/WorkShops/W, list/path)
	if(!M || !W) return 0
	M.destination = null
	M.remaster_order_status = "At the [RemasterStationName(W)]"
	remaster_preset_then_ask = 1
	RemasterRunStation(W, M, path)
	remaster_preset_then_ask = 0
	return 1
