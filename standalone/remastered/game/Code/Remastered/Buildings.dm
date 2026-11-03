// Building kit, part 4: buildings and lairs (Build tab: Buildings, Lairs, Furniture,
// Webs). A building is a layout of the original pieces in its race's own materials:
// walls, a floor, a door, furniture, a workshop, traps by the door. One click plans
// all of it as one construction task (Blueprints.dm); its workers lay the floor, bring
// the furniture and build the workshop, raise the walls, then hang the door. Rotate
// turns the layout before the click.
//
// The rare races get lairs, each with what they live by:
//   Spiders    - brood lair: silk walls and floor, cocoons for prey, cobwebs, a sticky
//                web across the way in. Spiders in it spin web faster.
//   Dragons    - a cavern with the dragon's hoard. A dragon asleep on or beside its
//                hoard heals faster, more with more treasure lying round the hoard.
//   Devourers  - flesh hive: flesh walls and floor, cocoon traps by the way in.
//                Devourers in it heal.
//   Svartalfar - hidden sanctum: walls that look like natural rock.
// Eggs laid in any lair hatch a third sooner. Rock inside a lair's outline is dug out
// first, by whichever of its workers can dig (claws, or a pickaxe).
//
// Spiders also get their hunting kit as single pieces (Webs): sticky webs that hold
// what walks into them and call the spiders nearby, the original web pit and cocoon,
// cobwebs and silk floor.

#define RM_WEB_HOLD 100        // a sticky web holds what walks into it for 10 seconds
#define RM_WEB_USES 3          // then it is torn after this many catches
#define RM_WEB_CALL 8          // spiders this close come for what it caught

Player/var/tmp/remaster_build_rot = 0   // 0: the door faces south; each Rotate turns it a quarter
Player/var/tmp/remaster_lair_next = 0
obj/Items/var/remaster_placed = 0       // set down as part of a building: not material to fetch
turf/var/remaster_lair                  // "spider", "dragon", "devourer", "sanctum": inside a finished lair
turf/var/remaster_lair_key              // whose lair

// --- Layouts -------------------------------------------------------------------------
// Rows run north to south, the door on the south side. Letters:
//   #  wall          .  floor           ,  open ground (dug out underground, nothing built)
//   D  door          B  bed             T  table          C  chair
//   F  forge  K  kitchen  P  potion station  O  bone crafting  f  campfire
//   ^  trap          ~  secret wall     s  silk floor      *  cobweb
//   c  cocoon        w  sticky web      H  hoard           x  cocoon trap
// A workshop letter is the tile its builder stands on; the workshop also takes the tile
// to its west, as the original does, so that one is floor.
var/list/remaster_building_defs
proc/RemasterBuildingDefs()
	if(remaster_building_defs) return remaster_building_defs
	var/list/D = list()
	D["dwarf_hall"] = list("label"="Dwarven forge-hall", "cat"="buildings", "races"=list("Dwarf"), "icon"='Cave.dmi', "state"="DetailedWall",
		"wall"="PlaceStoneWall", "floor"="PlaceStoneFloor",
		"info"="Dwarves; a stone hall with a forge, a table and two beds",
		"rows"=list(
		"#########",
		"#.F...BB#",
		"#.......#",
		"#..TC...#",
		"#.......#",
		"####D####"))
	D["human_house"] = list("label"="Timber house", "cat"="buildings", "races"=list("Human"), "icon"='Cave.dmi', "state"="WoodWall",
		"wall"="PlaceWoodenWall", "floor"="PlaceWoodenFloor",
		"info"="Humans; a wooden house with a kitchen, two beds, a table and a chair",
		"rows"=list(
		"#######",
		"#.K..B#",
		"#....B#",
		"#.TC..#",
		"###D###"))
	D["elf_lodge"] = list("label"="Elven lodge", "cat"="buildings", "races"=list("Elf"), "icon"='Cave.dmi', "state"="Elf Wall",
		"wall"="PlaceElfWall", "floor"="PlaceWoodenFloor",
		"info"="Elves; a round lodge of elf walls with two beds and a table",
		"rows"=list(
		"  #####  ",
		" ##...## ",
		"##.B.B.##",
		"#.......#",
		"#...T...#",
		"##.....##",
		" ##...## ",
		"  ##D##  "))
	// No wooden floor: the campfire in the middle would set it alight (the original fire).
	D["orc_lodge"] = list("label"="Orc war lodge", "cat"="buildings", "races"=list("Orc"), "icon"='Cave.dmi', "state"="WoodWall",
		"wall"="PlaceWoodenWall",
		"info"="Orcs; a long wooden lodge round a campfire, with eight beds or bedrolls",
		"rows"=list(
		"###########",
		"#B,B,,,B,B#",
		"#,,,,,,,,,#",
		"#,,,,f,,,,#",
		"#,,,,,,,,,#",
		"#B,B,,,B,B#",
		"#####D#####"))
	D["goblin_warren"] = list("label"="Goblin warren", "cat"="buildings", "races"=list("Goblin"), "icon"='Cave.dmi', "state"="DetailedWall",
		"wall"="PlaceStoneWall", "floor"="PlaceBoneFloor", "trap"="PlaceBoneSpikes",
		"info"="Goblins; obsidian walls round a bone floor, bone crafting, two beds and spike traps by the door",
		"rows"=list(
		" ####### ",
		"##.B.B.# ",
		"#......# ",
		"#.O....##",
		"##......#",
		" ####D###",
		"    ^,^  "))
	D["kobold_den"] = list("label"="Kobold den", "cat"="buildings", "races"=list("Kobold"), "icon"='Cave.dmi', "state"="Bone Wall",
		"wall"="PlaceBoneWall", "floor"="PlaceBoneFloor", "trap"="PlaceRibcage",
		"info"="Kobolds; a little bone den with two beds and ribcage traps outside",
		"rows"=list(
		" ##### ",
		"##B.B##",
		"#.....#",
		"##...##",
		" ##D## ",
		" ^,,,^ "))
	D["rat_warren"] = list("label"="Rat warren", "cat"="buildings", "races"=list("Ratman"), "icon"='Cave.dmi', "state"="Bone Wall",
		"wall"="PlaceBoneWall", "floor"="PlaceBoneFloor",
		"info"="Ratmen; two bone burrows of two beds each off one passage",
		"rows"=list(
		"#########",
		"#BB.#.BB#",
		"#.......#",
		"##.###.##",
		" #.....# ",
		" ###D### "))
	D["tribal_hut"] = list("label"="Tribal hut", "cat"="buildings", "races"=list("Lizardman", "Frogman"), "icon"='Cave.dmi', "state"="TribalWall",
		"wall"="PlaceTribalWall", "floor"="PlaceTribalFloor",
		"info"="Lizardmen, Frogmen; a round hut of tribal walls round a campfire, two beds",
		"rows"=list(
		" ##### ",
		"##...##",
		"#B.f.B#",
		"#.....#",
		"##...##",
		" ##D## "))
	D["spider_lair"] = list("label"="Brood lair", "cat"="lairs", "races"=list("Spider"), "icon"='Cave.dmi', "state"="SilkWall", "lair"="spider",
		"wall"="PlaceSilkWall", "floor"="Piece:silk",
		"info"="Spiders; silk walls and floor, two cocoons, cobwebs and a sticky web across the way in. Underground the rock is the wall. Spiders in it spin web faster; eggs hatch sooner",
		"rows"=list(
		" ####### ",
		"##c*s*c##",
		"#sssssss#",
		"#sssssss#",
		"##sssss##",
		" ###w### "))
	D["dragon_lair"] = list("label"="Dragon's lair", "cat"="lairs", "races"=list("Dragon"), "icon"='GoldItems.dmi', "state"="Coin", "lair"="dragon",
		"info"="Dragons; a cavern dug out round the dragon's hoard. Asleep by its hoard a dragon heals faster, more with treasure (gold, gems) lying round it; eggs hatch sooner",
		"rows"=list(
		"  ,,,,,  ",
		" ,,,,,,, ",
		",,,,H,,,,",
		" ,,,,,,, ",
		"  ,,,,,  "))
	D["devourer_hive"] = list("label"="Flesh hive", "cat"="lairs", "races"=list("Devourer"), "icon"='Cave.dmi', "state"="DevourerWall2", "lair"="devourer",
		"wall"="PlaceDevourerWall", "floor"="PlaceDevourerFloor",
		"info"="Devourers; flesh walls and floor, cocoon traps by the way in. Devourers in it heal; eggs hatch sooner",
		"rows"=list(
		" ##### ",
		"##...##",
		"#.....#",
		"##...##",
		" ##,## ",
		" x,,,x "))
	D["svart_sanctum"] = list("label"="Hidden sanctum", "cat"="lairs", "races"=list("Svartalfar"), "icon"='Cave.dmi', "state"="CaveWall", "lair"="sanctum",
		"wall"="PlaceSecretWall", "floor"="PlaceStoneFloor",
		"info"="Svartalfar; a stone room behind walls that look like natural rock, with a potion station, a bed and a table",
		"rows"=list(
		"~~~~~~~",
		"~.P..B~",
		"~.....~",
		"~.T...~",
		"~~~D~~~"))
	// Halls (drag to size, RemasterPlanHall): a race's materials and what goes in. "support" holds
	// the roof every few tiles (stone pillars, or support beams for wood and bone); "shop" the
	// workshop near the door; "fire" a campfire in the middle instead of a table.
	D["hall_dwarf"] = list("label"="Dwarven hall", "cat"="halls", "races"=list("Dwarf"), "icon"='StoneItems.dmi', "state"="Pillar", "hall"=1,
		"wall"="PlaceStoneWall", "floor"="PlaceStoneFloor", "support"="Piece:pillar", "shop"="forge",
		"info"="Dwarves; drag its size, on open ground or into a mountain: stone walls (or the rock itself), rows of stone pillars, beds along the back, a table, a forge")
	D["hall_human"] = list("label"="Timber hall", "cat"="halls", "races"=list("Human"), "icon"='Cave.dmi', "state"="WoodWall", "hall"=1,
		"wall"="PlaceWoodenWall", "floor"="PlaceWoodenFloor", "support"="Beam", "shop"="kitchen",
		"info"="Humans; drag its size: wooden walls and floor, support beams, beds, a table, a kitchen")
	D["hall_elf"] = list("label"="Elven hall", "cat"="halls", "races"=list("Elf"), "icon"='Cave.dmi', "state"="Elf Wall", "hall"=1,
		"wall"="PlaceElfWall", "floor"="PlaceWoodenFloor", "support"="Beam", "shop"="potion",
		"info"="Elves; drag its size: elf walls, a wooden floor, support beams, beds, a table, a potion station")
	D["hall_orc"] = list("label"="Orc longhouse", "cat"="halls", "races"=list("Orc"), "icon"='Cave.dmi', "state"="WoodWall", "hall"=1,
		"wall"="PlaceWoodenWall", "support"="Beam", "fire"=1,
		"info"="Orcs; drag its size: a wooden palisade, support beams, beds round a campfire")
	D["hall_goblin"] = list("label"="Goblin hall", "cat"="halls", "races"=list("Goblin"), "icon"='Cave.dmi', "state"="DetailedWall", "hall"=1,
		"wall"="PlaceStoneWall", "floor"="PlaceBoneFloor", "support"="Piece:pillar", "shop"="bone", "trap"="PlaceBoneSpikes",
		"info"="Goblins; drag its size: obsidian walls, a bone floor, stone pillars, beds, bone crafting, spike traps by the door")
	D["hall_bone"] = list("label"="Bone hall", "cat"="halls", "races"=list("Kobold", "Ratman"), "icon"='Cave.dmi', "state"="Bone Wall", "hall"=1,
		"wall"="PlaceBoneWall", "floor"="PlaceBoneFloor", "support"="Beam", "shop"="bone", "trap"="PlaceRibcage",
		"info"="Kobolds, Ratmen; drag its size: bone walls and floor, support beams, beds, bone crafting, ribcage traps by the door")
	D["hall_tribal"] = list("label"="Tribal longhouse", "cat"="halls", "races"=list("Lizardman", "Frogman"), "icon"='Cave.dmi', "state"="TribalWall", "hall"=1,
		"wall"="PlaceTribalWall", "floor"="PlaceTribalFloor", "support"="Beam", "fire"=1,
		"info"="Lizardmen, Frogmen; drag its size: tribal walls and floor, support beams, beds round a campfire")
	D["hall_svart"] = list("label"="Hidden hall", "cat"="halls", "races"=list("Svartalfar"), "icon"='Cave.dmi', "state"="CaveWall", "hall"=1,
		"wall"="PlaceSecretWall", "floor"="PlaceStoneFloor", "support"="Piece:pillar", "shop"="potion",
		"info"="Svartalfar; drag its size: walls that look like rock, a stone floor, stone pillars, beds, a potion station")
	for(var/id in D) D[id]["id"] = id
	remaster_building_defs = D
	return D

proc/RemasterBuildingDef(id)
	return RemasterBuildingDefs()[id]

// What a layout letter becomes in this building ("open": nothing, but dug out).
proc/RemasterBuildingMode(list/D, c)
	switch(c)
		if("#") return D["wall"]
		if("~") return "PlaceSecretWall"
		if(".") return D["floor"] || "open"
		if(",") return "open"
		if("D") return "Gate"
		if("B") return "Piece:bed"
		if("T") return "Piece:table"
		if("C") return "Piece:chair"
		if("F") return "Workshop:forge"
		if("K") return "Workshop:kitchen"
		if("P") return "Workshop:potion"
		if("O") return "Workshop:bone"
		if("f") return "Workshop:campfire"
		if("^") return D["trap"]
		if("s") return "Piece:silk"
		if("*") return "Piece:cobweb"
		if("c") return "Piece:cocoon"
		if("w") return "Piece:web"
		if("H") return "Piece:hoard"
		if("x") return "Piece:fleshtrap"
		if("|") return D["support"]                       // a hall's pillar or support beam
		if("W") return D["shop"] ? "Workshop:[D["shop"]]" : null
	return null

proc/RemasterBuildingFacing(rot)
	return list("south", "west", "north", "east")[(rot % 4) + 1]

// The layout's cells on the map round C, turned rot quarters clockwise:
// list of list(turf, letter); null if part of it is off the map.
proc/RemasterBuildingCells(list/D, rot, turf/C)
	var/list/rows = D["rows"]
	var/h = length(rows)
	var/w = 0
	for(var/r in rows) w = max(w, length(r))
	var/cx = round((w - 1) / 2)   // the middle (round() with one argument rounds down)
	var/cy = round((h - 1) / 2)
	var/list/grid = list()   // "x,y" -> letter
	var/list/out = list()
	for(var/row = 1, row <= h, row++)
		var/line = rows[row]
		for(var/col = 1, col <= length(line), col++)
			var/c = copytext(line, col, col + 1)
			if(c == " ") continue
			var/dx = col - 1 - cx
			var/dy = cy - (row - 1)       // north is up
			for(var/i = 1, i <= rot % 4, i++)
				var/t = dx
				dx = dy
				dy = -t
			var/turf/T = locate(C.x + dx, C.y + dy, C.z)
			if(!T) return null
			grid["[T.x],[T.y]"] = c
			out += list(list(T, c))
	// A workshop takes the tile to its west: after a turn that may be a wall, so the
	// workshop moves a tile east onto the floor (its west tile is then where it was).
	for(var/list/X in out)
		var/turf/T = X[1]
		if(!(X[2] in list("F", "K", "P", "O"))) continue
		var/west = grid["[T.x - 1],[T.y]"]
		if(west == "." || west == ",") continue
		var/east = grid["[T.x + 1],[T.y]"]
		if(east != "." && east != ",") continue
		var/shop = X[2]
		for(var/list/Y in out) if(Y[1] == locate(T.x + 1, T.y, T.z))
			Y[2] = shop
			break
		X[2] = east
		grid["[T.x],[T.y]"] = east
		grid["[T.x + 1],[T.y]"] = shop
	return out

// The menu's little plan of it (unturned).
proc/RemasterBuildingGrid(id)
	var/list/D = RemasterBuildingDef(id)
	if(D && D["hall"]) return RemasterHallRows(D, 9, 7)
	return D ? D["rows"] : null

// What the whole of it takes, for the menu.
Player/proc/RemasterBuildingCost(list/E)
	var/list/D = RemasterBuildingDef(E["building"])
	if(!D) return ""
	var/list/rows = D["hall"] ? RemasterHallRows(D, 9, 7) : D["rows"]
	var/list/count = list()
	var/web = 0
	var/flesh = 0
	var/list/kept = list()
	for(var/r in rows)
		for(var/i = 1, i <= length(r), i++)
			var/c = copytext(r, i, i + 1)
			var/mode = RemasterBuildingMode(D, c)
			if(!mode || mode == "open") continue
			if(D["floor"] && (c in list("B", "T", "C", "D", "F", "K", "P", "O", "W", "|", "c", "*", "w"))) web += RemasterPieceWeb(D["floor"]) // its floor under it
			web += RemasterPieceWeb(mode)
			if(mode in list("PlaceDevourerWall", "Piece:fleshtrap")) flesh++
			var/path = RemasterBuildMaterial(mode)
			if(!path) continue
			var/kind = RemasterMaterialKind(path)
			if(!RemasterBuildUses(mode)) kept |= kind
			else count[kind] = (count[kind] || 0) + RemasterBlueprintNeed(mode, null)
	var/list/parts = list()
	for(var/kind in count) parts += "[count[kind]] [kind][count[kind] > 1 && (kind in list("door", "bed", "table", "chair")) ? "s" : ""]"
	for(var/kind in kept) if(!count[kind]) parts += "1 [kind] (kept)"
	if(web) parts += "[web] web"
	if(flesh) parts += "stored flesh"
	if(D["floor"] == "PlaceDevourerFloor") parts += "a stored body (kept)"
	if(!length(parts)) parts += "free"
	if(D["hall"]) return "9x7: [jointext(parts, ", ")]; any size, less where rock is its wall"
	return "[jointext(parts, ", ")][D["lair"] ? "; less where rock is its wall" : ""]"

// --- Placing a building ----------------------------------------------------------------
proc/RemasterDiggable(turf/T)
	if(("IsWall" in T.vars) && T.vars["IsWall"]) return 0   // a built wall is in the way, not rock
	return T.density && (T.CanDigAt || T.icon_state == "CaveWall")

proc/RemasterCanDigRock(mob/Monsters/M)
	return M && (M.UsesPicks == 0 || M.HoldingWeapon == "Pickaxe" || M.VampPick || M.Werepowers)

Player/proc/RemasterPlaceBuilding(turf/C)
	var/list/E = RemasterBuildEntryForMode(Function)
	var/list/D = E ? RemasterBuildingDef(E["building"]) : null
	if(!D || !C) return 0
	if(C.z == SKY_LAYER)
		RemasterNotice("[D["label"]]: buildings go on the ground or underground.")
		return 0
	var/list/cells = RemasterBuildingCells(D, remaster_build_rot, C)
	if(!cells)
		RemasterNotice("[D["label"]]: too close to the edge of the map.")
		return 0
	var/way = ""
	for(var/r in D["rows"]) if(findtext(r, "D")) way = ", door to the [RemasterBuildingFacing(remaster_build_rot)]"
	if(!way) for(var/r in D["rows"]) if(findtext(r, "w") || findtext(r, ",")) way = ", way in to the [RemasterBuildingFacing(remaster_build_rot)]"
	if(D["id"] == "dragon_lair") way = ""
	return RemasterPlanCells(E, D, cells, C, way, "Try another spot, or Rotate it.")

// Plans a building's cells (list of list(turf, layout letter)) as one construction task: rock
// in the way of anything but a wall is dug out first, rock where a wall goes is the wall.
Player/proc/RemasterPlanCells(list/E, list/D, list/cells, turf/C, way, hint)
	var/list/plan = list()
	var/list/dig = list()
	var/problems = 0
	var/why
	for(var/list/X in cells)
		var/turf/T = X[1]
		var/mode = RemasterBuildingMode(D, X[2])
		if(!mode) continue
		var/fail
		if(!RemasterMayWork(T, 1)) fail = "someone else's land"
		else if(RemasterBlueprintAt(T)) fail = "planned already"
		else if(RemasterBuildShape(mode) == "wall")
			if(T.density) continue // rock or a wall already: that is the wall
		else if(T.density)
			if(!RemasterDiggable(T)) fail = (("Tree" in T.vars) && T.vars["Tree"]) ? "a tree is in the way (fell it first)" : "a wall or building is in the way"
			else dig += "[T.x],[T.y]"
		else if(mode != "open" && (T.Content3 == "Liquid" || T.Content3 == "Lava" || findtext("[T.icon_state]", "Lava")))
			fail = "water or lava in the way"
		else if(mode != "open")
			var/blocked = RemasterBuildBlocked(T, mode)
			if(blocked)
				if(RemasterBuildShape(mode) == "floor" && (T.Detailed || T.isbridge)) continue // floored already
				fail = blocked
		if(fail)
			problems++
			why = fail
			continue
		// Furniture, a workshop or the door stands on the building's floor: that is laid
		// first on its tile, then the piece goes on it (the same plan; see RemasterSiteBuild).
		var/under = D["floor"]
		if(under && (X[2] in list("B", "T", "C", "D", "F", "K", "P", "O", "W", "|", "c", "*", "w")) && !T.Detailed && !T.isbridge && !RemasterBuildBlocked(T, under))
			plan += list(list(T, under, mode))
			continue
		if(mode != "open") plan += list(list(T, mode))
	if(problems)
		RemasterNotice("Can't put the [lowertext(D["label"])] there: [problems] tile[problems == 1 ? "" : "s"] in the way ([why]). [hint]")
		return 0
	if(!length(plan))
		RemasterNotice("[D["label"]]: everything it needs is there already.")
		return 0
	if(!remaster_blueprints) remaster_blueprints = list()
	var/list/S = RemasterSiteNew(E["mode"], C.z)
	S["x"] = C.x
	S["y"] = C.y
	S["building"] = D["id"]
	S["rot"] = remaster_build_rot
	if(length(dig)) S["dig"] = dig
	var/list/undo = list()
	var/pieces = 0
	for(var/list/X in plan)
		var/turf/T = X[1]
		var/list/B = list("x"=T.x, "y"=T.y, "z"=T.z, "mode"=X[2], "note"="Waiting for a builder", "tries"=0, "site"=S["id"])
		if(length(X) >= 3) B["then"] = X[3]
		remaster_blueprints += list(B)
		undo += "[T.x],[T.y],[T.z]"
		pieces += length(X) >= 3 ? 2 : 1
	S["left"] = pieces
	S["total"] = pieces
	RemasterUndoPush(list("type"="blueprints", "keys"=undo))
	var/crew = RemasterSiteAssignUnits(S, RemasterBuilderUnits())
	Function = null
	var/text = "Planned the [lowertext(D["label"])][way]: [pieces] piece[pieces == 1 ? "" : "s"]"
	if(length(dig)) text += " once [length(dig)] tile[length(dig) == 1 ? "" : "s"] of rock [length(dig) == 1 ? "is" : "are"] dug out"
	text += ". [RemasterSiteNeedText(S)]."
	text += crew ? " [crew]" : " [RmBuildCrewHint(1)]"
	RemasterNotice(text)
	return S

// While rock in the outline is left, every piece waits (the diggers come first). A cave-in
// (Bump.dm, Mountains.dm) can fill dug tiles or a planned tile again: they are dug out again.
Player/proc/RemasterBuildingRock(list/S)
	var/list/out = list()
	if(S["dig"]) for(var/k in S["dig"])
		var/list/p = splittext(k, ",")
		var/turf/T = locate(text2num(p[1]), text2num(p[2]), S["z"])
		if(T && RemasterDiggable(T)) out += T
	if(S["building"] && remaster_blueprints) for(var/list/B in remaster_blueprints) if(B["site"] == S["id"])
		var/turf/T = locate(B["x"], B["y"], B["z"])
		if(T && T.density && RemasterDiggable(T) && !(T in out)) out += T
	return out

Player/proc/RemasterBuildingDigWait(list/S)
	if(!S["building"]) return null
	var/list/rock = RemasterBuildingRock(S)
	if(!length(rock))
		if(S["digging"])
			S["digging"] = null
			RemasterBuildingDigDone(S)
		return null
	S["digging"] = 1
	return "Waits for the rock to be dug out ([length(rock)] tile[length(rock) == 1 ? "" : "s"] left)"

// A worker with nothing to build yet digs the rock left in the outline, as a Mine order does
// (Orders.dm): it walks beside the nearest piece and works it, with its pickaxe or claws at
// the race's own speed, by hand a blow every two seconds (RemasterHandWork). Mountain rock
// comes out block by block the same way.
Player/proc/RemasterBuildingDigTick(list/S, mob/Monsters/M)
	var/list/rock = RemasterBuildingRock(S)
	if(!length(rock))
		var/list/roofs = RemasterBuildingRoofs(S)       // a high hall, built: its ceiling next
		if(length(roofs)) RemasterBuildingRoofTick(S, M, roofs)
		return
	var/turf/target
	var/turf/W
	for(var/turf/T in rock)
		var/turf/spot = get_dist(M, T) <= 1 ? M.loc : RemasterBuildSpot(T, M)  // rock with open ground beside it
		if(spot && (!W || get_dist(M, spot) < get_dist(M, W)))
			W = spot
			target = T
	if(!target)
		S["note"] = "No way to the rock: dig a tunnel to it"
		return
	M.remaster_site_standby = 0
	if(get_dist(M, target) > 1)
		M.RemasterSiteWalk(W)
	else
		if(M.remaster_site_dest && M.destination == M.remaster_site_dest) M.destination = null
		M.dir = get_dir(M, target)
		M.remaster_site_digging = 1      // a building's rock comes out whole, veins and all (Yield.dm)
		if(RemasterCanDigRock(M))
			M.destination = target
			M.Bump(target)
		else M.RemasterHandWork(target, "Mine")
		if(M) M.remaster_site_digging = 0
	S["note"] = "[M.name] is digging out the rock ([length(rock)] tile[length(rock) == 1 ? "" : "s"] left)"
	M.RemasterSiteStatus("Digging out the [lowertext(S["label"])] ([length(rock)] left)")

Player/proc/RemasterBuildingDigDone(list/S)
	for(var/mob/Monsters/M in UnitList) if(M.remaster_site == S["id"] && M.destination && isturf(M.destination) && M.destination:density)
		M.destination = null   // the rock it was digging is out

// A finished lair: its tiles remember whose lair they are (kept in world saves).
Player/proc/RemasterBuildingFinished(list/S, note)
	RemasterBuildingDigDone(S)
	var/list/D = RemasterBuildingDef(S["building"])
	if(!D || !D["lair"] || S["left"] || !S["built"] || note == "Cancelled") return
	var/list/cells = RemasterBuildingCells(D, S["rot"] || 0, locate(S["x"], S["y"], S["z"]))
	if(!cells) return
	for(var/list/X in cells)
		var/turf/T = X[1]
		if(T.density && X[2] != "w") continue
		T.remaster_lair = D["lair"]
		T.remaster_lair_key = key
		remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1
	RemasterNotice("The [lowertext(D["label"])] is finished. [RemasterLairEffect(D["lair"])]")

proc/RemasterLairEffect(kind)
	switch(kind)
		if("spider") return "Spiders in it spin web faster, and eggs laid in it hatch sooner."
		if("dragon") return "Asleep by its hoard a dragon heals faster (more with gold and gems round the hoard), and eggs laid in it hatch sooner."
		if("devourer") return "Devourers in it heal, and eggs laid in it hatch sooner."
		if("sanctum") return "Its walls look like natural rock to everyone else."
	return ""

// What a building's task still needs, material by material.
Player/proc/RemasterBuildingNeeds(list/S, list/stock)
	var/list/paths = list()
	var/body
	if(remaster_blueprints) for(var/list/B in remaster_blueprints) if(B["site"] == S["id"])
		for(var/mode in B["then"] ? list(B["mode"], B["then"]) : list(B["mode"]))
			var/path = RemasterBuildMaterial(mode)
			if(path) paths |= path
			else if(!body) body = RemasterPieceBodyText(mode)
	var/list/parts = list()
	var/missing = 0
	var/list/rock = RemasterBuildingRock(S)
	if(length(rock)) parts += list(list("mat"=null, "body"="First dig out [length(rock)] tile[length(rock) == 1 ? "" : "s"] of rock"))
	for(var/path in paths)
		var/need = RemasterSiteNeedCount(S, path)
		if(!need) continue
		var/key = "[path]|[S["z"]]"
		if(isnull(stock[key])) stock[key] = RemasterStoreCount(path, S["z"])
		var/carried = 0
		for(var/mob/Monsters/M in RemasterSiteCrew(S["id"])) carried += M.RemasterCarriedCount(path)
		carried = min(carried, need)
		var/from_stock = min(need - carried, stock[key])
		stock[key] -= from_stock
		var/nearby = 0
		if(need - carried - from_stock > 0 && !RemasterFurniturePath(path)) nearby = min(need - carried - from_stock, RemasterLooseCount(path, locate(S["x"], S["y"], S["z"])))
		var/miss = max(0, need - carried - from_stock - nearby)
		missing += miss
		parts += list(list("mat"=RemasterMaterialKind(path), "need"=need, "carried"=carried, "stock"=from_stock, "nearby"=nearby, "missing"=miss, "uses"=1))
	if(body) parts += list(list("mat"=null, "body"=body))
	var/list/first = length(parts) ? parts[1] : null
	return list("parts"=parts, "missing"=missing, "mat"=first ? first["mat"] : null)

// --- Catalog --------------------------------------------------------------------------
proc/RemasterBuildingCatalog()
	var/list/C = list()
	var/list/D = RemasterBuildingDefs()
	for(var/id in D)
		var/list/B = D[id]
		var/list/E = RemasterBuildDef(id, B["label"], B["cat"], "Building:[id]", null, 0, B["icon"], B["state"], B["info"])
		E["building"] = id
		C += list(E)
	// Furniture, carried from a stockpile and set down where planned.
	var/list/F = RemasterBuildDef("furn_bed", "Bed", "furniture", "Piece:bed", "bed", 1, 'Cave.dmi', "Bed", "Any race with hands; a bed or bedroll from a stockpile (made at a carpentry)")
	F["piececost"] = "a bed or bedroll"
	C += list(F)
	F = RemasterBuildDef("furn_table", "Table", "furniture", "Piece:table", "table", 1, 'Cave.dmi', "Table", "Any race with hands; a table from a stockpile")
	F["piececost"] = "a table"
	C += list(F)
	F = RemasterBuildDef("furn_chair", "Chair", "furniture", "Piece:chair", "chair", 1, 'Cave.dmi', "Chair", "Any race with hands; a chair from a stockpile")
	F["piececost"] = "a chair"
	C += list(F)
	// The spiders' hunting kit.
	F = RemasterBuildDef("web_sticky", "Sticky web", "webs", "Piece:web", "web", 0, 'Decoration1.dmi', "", "Spiders; holds anyone else who walks into it for 10 seconds and calls the spiders nearby. Torn after 3 catches")
	F["piececost"] = "25 web"
	C += list(F)
	F = RemasterBuildDef("web_pit", "Web pit", "webs", "Piece:pit", "web", 0, 'Cave.dmi', "Hole", "Spiders; a pit covered with web: prey falls in and is held for a cocoon")
	F["piececost"] = "50 web"
	C += list(F)
	F = RemasterBuildDef("web_cocoon", "Cocoon", "webs", "Piece:cocoon", "web", 0, 'Spiders.dmi', "Cage", "Spiders; a cocoon to wrap caught prey in alive")
	F["piececost"] = "50 web"
	C += list(F)
	F = RemasterBuildDef("web_cobweb", "Cobweb", "webs", "Piece:cobweb", "web", 0, 'Decoration2.dmi', "", "Spiders; webs strung about a lair")
	F["piececost"] = "25 web"
	C += list(F)
	F = RemasterBuildDef("silk_floor", "Silk floor", "webs", "Piece:silk", "web", 0, 'Cave.dmi', "SilkWall", "Spiders; silk spun over the ground, as in a spider queen's lair")
	F["piececost"] = "8 web per tile"
	C += list(F)
	// Mine carts (Carts.dm): track, stops, carts.
	F = RemasterBuildDef("rail", "Rail track", "rails", "Piece:rail", "wood", 1, 'Cave.dmi', "WoodBridge", "Anyone; drag the line: 1 wood a tile. Carts run on it")
	F["piececost"] = "1 wood per tile"
	C += list(F)
	F = RemasterBuildDef("cartstop", "Cart stop", "rails", "Piece:cartstop", "wood", 1, 'Cave.dmi', "sign", "Anyone; on the track. Beside a stockpile carts unload there; anywhere else miners drop what they dig and a cart takes it to the stockpile")
	F["piececost"] = "1 wood"
	C += list(F)
	F = RemasterBuildDef("minecart", "Mine cart", "rails", "Piece:minecart", "wood", 1, 'Cave.dmi', "Wagon", "Anyone; on the track. Runs between the stops by itself, 20 loads at a time")
	F["piececost"] = "3 wood"
	C += list(F)
	F = RemasterBuildDef("stone_pillar", "Stone pillar", "digging", "Piece:pillar", "stone", 1, 'StoneItems.dmi', "Pillar", "Stone-wall builders; holds the roof up within 4 tiles, like a support beam (halls put rows of them in)")
	F["piececost"] = "2 stone"
	C += list(F)
	F = RemasterBuildDef("hoard", "Hoard", "lairs", "Piece:hoard", null, 0, 'GoldItems.dmi', "Coin", "Dragons; where the dragon keeps its treasure and sleeps. Drop gold and gems round it")
	F["piececost"] = "free"
	C += list(F)
	F = RemasterBuildDef("flesh_trap", "Cocoon trap", "traps", "Piece:fleshtrap", "flesh", 0, 'Devourer.dmi', "TinyCacoon", "Devourers; a cocoon trap: monsters burst out at anyone who comes near")
	F["piececost"] = "a stored body's flesh"
	C += list(F)
	C += RemasterPowerCatalog()   // water wheels, axles, bellows (Power.dm)
	C += RemasterLiftCatalog()    // lifts (Lifts.dm)
	C += RemasterGateCatalog()    // portcullis, drawbridge (Gates.dm)
	return C

// Race rules for buildings and pieces (null: not one of these).
proc/RemasterBuildingRaceOK(id, mob/Monsters/M)
	var/r = M.Race
	var/list/D = RemasterBuildingDef(id)
	if(D) return r in D["races"]
	switch(id)
		if("furn_bed", "furn_table", "furn_chair") return !(r in list("Spider", "Dragon", "Devourer"))
		if("web_sticky", "web_pit", "web_cocoon", "web_cobweb", "silk_floor") return r == "Spider"
		if("hoard") return r == "Dragon"
		if("stone_pillar") return RemasterBuildRaceOK("stone_wall", M)
		if("rail", "cartstop", "minecart") return !(r in list("Spider", "Dragon", "Devourer"))
		if("waterwheel", "windmill", "axle", "bellows", "dynamo", "lift_up", "lift_down", "portcullis", "drawbridge") return !(r in list("Spider", "Dragon", "Devourer"))
		if("flesh_trap") return r == "Devourer"
	return null

// --- Pieces ---------------------------------------------------------------------------
proc/RemasterFurniturePath(path)
	return path && (ispath(path, /obj/Items/Furniture/Beds) || ispath(path, /obj/Items/Furniture/Tables) || ispath(path, /obj/Items/Furniture/Chairs))

proc/RemasterPieceRank(mode)
	if(mode == "Piece:silk" || mode == "Piece:rail") return 1     // a floor, a track: first
	return 2                              // furniture, webs, a hoard: before the walls

proc/RemasterPieceWeb(mode)
	switch(mode)
		if("Piece:web", "Piece:cobweb") return 25
		if("Piece:pit", "Piece:cocoon") return 50
		if("Piece:silk") return 8
		if("PlaceSilkWall", "PlaceSilkBridge") return 25
	return 0

proc/RemasterPieceBodyText(mode)
	if(RemasterPieceWeb(mode)) return "Spun from the spiders' own web"
	if(mode in list("PlaceDevourerWall", "PlaceDevourerFloor", "Piece:fleshtrap")) return "Made from the Devourer's stored flesh"
	if(mode == "Piece:hoard") return "The dragon scrapes its hoard together"
	return null

mob/Monsters/proc/RemasterPieceBodyNeed(mode)
	var/web = RemasterPieceWeb(mode)
	if(web && WebContent < web) return "Needs [web] web ([name] has [round(WebContent)])"
	if(mode == "Piece:fleshtrap" && EggContent < 1) return "Needs stored flesh ([name] has none)"
	return null

proc/RemasterPieceBlocked(turf/T, mode)
	if(RemasterGateMode(mode)) return RemasterGateBlocked(T, mode)   // a drawbridge goes on water (Gates.dm)
	if(T.density) return "it goes on open ground"
	if(RemasterPowerMode(mode)) return RemasterPowerBlocked(T, mode)
	if(RemasterLiftMode(mode)) return RemasterLiftBlocked(T, mode)
	switch(mode)
		if("Piece:rail")
			if(T.remaster_road == "rail") return "there's track there already"
			if(T.remaster_road == "stone") return "a cobbled road is there (track can't cross it)"
			if(T.icon == 'Stairs.dmi') return "there are stairs there"
			if(T.icon_state == "Sky" || T.Content3 == "Liquid" || T.Content3 == "Lava" || T.Content == "Chasm") return "track goes on the ground"
			return null
		if("Piece:cartstop")
			for(var/obj/Items/Furniture/RemasterCartStop/X in T) return "there's a stop there already"
			return null
		if("Piece:minecart")
			for(var/obj/Items/Furniture/RemasterCart/X in T) return "there's a cart there already"
			return null
	switch(mode)
		if("Piece:silk")
			if(T.Detailed || T.isbridge) return "there's a floor there already"
			return null
		if("Piece:web", "Piece:pit", "Piece:fleshtrap")
			for(var/obj/Items/Traps/X in T) return "there's a trap there already"
			return null
		if("Piece:pillar")
			if(locate(/obj/Items/Furniture/Pillars) in T) return "there's a pillar there already"
	for(var/obj/Items/Furniture/X in T) if(X.density || X.remaster_placed) return "something stands there already"
	for(var/obj/Items/Traps/X in T) return "there's a trap there already"
	for(var/mob/WorkShops/W in T) return "a workshop stands there"
	return null

// Builds one piece from the tile beside it (as the original furniture Drop and the
// spider menu's Create do, with the costs they take).
Player/proc/RemasterBuildPiece(mob/Monsters/M, turf/T, mode)
	if(!T || get_dist(M, T) > 1 || M.z != T.z || RemasterPieceBlocked(T, mode)) return 0
	if(M.RemasterPieceBodyNeed(mode)) return 0
	var/web = RemasterPieceWeb(mode)
	switch(mode)
		if("Piece:bed", "Piece:table", "Piece:chair")
			var/path = RemasterBuildMaterial(mode)
			var/obj/Items/I
			for(var/obj/Items/X in M) if(istype(X, path) && (X in M.remaster_site_load))
				I = X
				break
			if(!I) return 0
			I.loc = T
			I.suffix = null
			I.dir = SOUTH
			I.Owner = src
			I.remaster_placed = 1
			M.weight -= I.weight
			M.remaster_site_load -= I
		// Made first, then owned, then set down, as the original Create does: traps
		// look round as soon as they are on the ground and go off for anyone not their owner's.
		if("Piece:rail", "Piece:cartstop", "Piece:minecart")
			// wood from the bag: a tile of track, a stop, a cart (three)
			var/need = mode == "Piece:minecart" ? 3 : 1
			var/list/woods = list()
			for(var/obj/Items/woods/wood/X in M) if(X.suffix != "(Equipped)") woods += X
			if(length(woods) < need) return 0
			for(var/k = 1, k <= need, k++)
				var/obj/Items/X = woods[k]
				if(M.DropItem(X)) del(X)
			if(mode == "Piece:rail")
				T.remaster_road = "rail"
				remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1   // a var only (Roads.dm)
			else
				var/obj/Items/P = mode == "Piece:minecart" ? new /obj/Items/Furniture/RemasterCart : new /obj/Items/Furniture/RemasterCartStop
				P.Owner = src
				P.remaster_owner_key = key
				P.loc = T
		if("Piece:waterwheel", "Piece:windmill", "Piece:axle", "Piece:bellows", "Piece:dynamo")
			if(!RemasterBuildPower(M, T, mode)) return 0     // Power.dm
		if("Piece:liftup", "Piece:liftdown")
			if(!RemasterBuildLift(M, T, mode)) return 0      // Lifts.dm
		if("Piece:portcullis", "Piece:drawbridge")
			if(!RemasterBuildGatePiece(M, T, mode)) return 0 // Gates.dm
		if("Piece:pillar")
			// cut from two stone where it stands (a hall's pillars; as a support beam is put up)
			var/list/stones = list()
			for(var/obj/Items/ores/stone/X in M) if(X.suffix != "(Equipped)") stones += X
			if(length(stones) < 2) return 0
			for(var/k = 1, k <= 2, k++)
				var/obj/Items/X = stones[k]
				if(M.DropItem(X)) del(X)
			var/obj/Items/Furniture/Pillars/P = M.Race == "Goblin" ? new /obj/Items/Furniture/Pillars/GoblinPillar : new /obj/Items/Furniture/Pillars/DwarfPillar
			P.loc = T
			P.suffix = null
			P.Owner = src
			P.remaster_placed = 1
			M.StoneCraftingSkill += 1
		if("Piece:web")
			var/obj/Items/Traps/RemasterWeb/W = new
			W.Owner = src
			W.loc = T
		if("Piece:pit")
			var/obj/Items/Traps/PitTrap/L = new
			L.Owner = src
			L.loc = T
			L.name = "Pit"
			L.icon = null   // covered with web, as the original CoverPit
			L.Hole = 1
			M.StoneCraftingSkill += 1
		if("Piece:cocoon")
			var/obj/Items/Traps/Cages/Cacoon/K = new
			K.desc = "This is a cocoon, it is used by spiders to entrap victims."
			K.Owner = src
			K.loc = T
		if("Piece:cobweb")
			var/obj/Items/Furniture/RemasterCobweb/W = new(T)
			if(prob(50)) W.icon = 'Decoration2.dmi'
			W.Owner = src
		if("Piece:silk")
			T.icon = 'Cave.dmi'
			T.icon_state = "SilkWall"  // the original lair's silk
			T.Detailed = 1
		if("Piece:hoard")
			var/obj/Items/Furniture/RemasterHoard/H = new(T)
			H.Owner = src
			H.remaster_owner_key = key
		if("Piece:fleshtrap")
			var/obj/Items/Traps/CacoonTrap/L = new
			L.Owner = src
			L.loc = T
			L.Hole = 1
			L.name = "Cocoon Trap"
			M.EggContent -= 1
			M.BoneCraftingSkill += 1
		else return 0
	if(web) M.WebContent -= web
	return 1

// --- The pieces themselves ----------------------------------------------------------------
obj/Items/Furniture/RemasterCobweb
	// its values: art/items/catalogue.json row furniture.remastercobweb (export_items.py writes ItemData.dm)

obj/Items/Furniture/RemasterHoard
	// its values: art/items/catalogue.json row furniture.remasterhoard (export_items.py writes ItemData.dm)

// Treasure lying on or right beside the hoard.
obj/Items/Furniture/RemasterHoard/proc/RemasterTreasure()
	var/n = 0
	for(var/obj/Items/I in range(1, src))
		if(I == src || !isturf(I.loc)) continue
		if(istype(I, /obj/Items/gems) || findtext(lowertext("[I.type]"), "gold") || findtext(lowertext("[I.type]"), "silver")) n++
	return n

// A sticky web: whoever else walks into it is held fast (as a spider's web shot does,
// longer), and the owner's spiders nearby come for it.
obj/Items/Traps/RemasterWeb
	// its values: art/items/catalogue.json row traps.remasterweb (export_items.py writes ItemData.dm)
	var/remaster_holds = RM_WEB_USES
	New()
		..()
		spawn(5) RemasterWebWatch()

obj/Items/Traps/RemasterWeb/proc/RemasterWebWatch()
	while(src && loc)
		if(isturf(loc)) for(var/mob/Monsters/M in loc) RemasterWebCatch(M)
		sleep(3)

obj/Items/Traps/RemasterWeb/proc/RemasterWebCatch(mob/Monsters/M)
	if(M.HP <= 0 || M.GoingToDie || M.Flying || M.Race == "Spider" || M.Wagon || M.WS) return
	if(M.remaster_root_until > world.time) return
	var/Player/P = Owner
	if(M.Owner && M.Owner == Owner) return
	if(istype(P) && istype(M.Owner, /Player) && RemasterAllied(P, M.Owner)) return
	M.remaster_root_until = world.time + RM_WEB_HOLD
	M.remaster_slow_until = world.time + RM_WEB_HOLD + 50
	remaster_holds--
	view(M) << "<b>[M.RemasterBareName()] is caught in a sticky web!</b>"
	if(istype(P))
		P.RemasterNotice("[M.RemasterBareName()] is caught in a sticky web: it's held for 10 seconds.")
		P.RemasterLog("[M.RemasterBareName()] caught in a web", "fight", loc)
		for(var/mob/Monsters/S in P.UnitList)
			if(S.Owner != P || S.Race != "Spider" || S.z != M.z || get_dist(S, M) > RM_WEB_CALL) continue
			if(S.HP <= 0 || S.Sleeping || S.remaster_attack || length(S.remaster_orders) || S.remaster_site || !RemasterHostile(S, M, 1)) continue
			var/datum/remaster_attack/K = new
			K.issuer = P
			K.target = M
			K.chosen = M
			K.last_position = S.loc
			K.last_progress = world.time
			S.remaster_attack = K
			S.remaster_order_status = "Going for [RemasterCombatName(M)] in the web"
	if(remaster_holds <= 0)
		view(M) << "The web tears."
		spawn(RM_WEB_HOLD) if(src) del(src)

// --- What lairs do ------------------------------------------------------------------------
Player/proc/RemasterLairTick()
	RemasterWallHoldTick()   // walls that hold the roof (below)
	if(world.time < remaster_lair_next) return
	remaster_lair_next = world.time + 50
	for(var/mob/Monsters/M in UnitList)
		if(M.Owner != src || M.HP <= 0 || !isturf(M.loc)) continue
		var/turf/T = M.loc
		if(!T.remaster_lair || T.remaster_lair_key != key) continue
		switch(T.remaster_lair)
			if("spider")
				if(M.Race == "Spider" && M.MaxWebContent && M.WebContent < M.MaxWebContent) M.WebContent = min(M.MaxWebContent, M.WebContent + 2)
			if("dragon")
				if(M.Race != "Dragon" || !M.Sleeping || M.HP >= M.MAXHP) continue
				var/obj/Items/Furniture/RemasterHoard/H = locate() in range(1, M)
				if(H) M.HP = min(M.MAXHP, M.HP + 3 + min(5, round(H.RemasterTreasure() / 5)))
			if("devourer")
				if(M.Race == "Devourer" && M.HP < M.MAXHP) M.HP = min(M.MAXHP, M.HP + 2)

// Eggs laid in a lair hatch a third sooner.
mob/Monsters/Egg/Breeding(mob/breederMale, mob/breederFemale, TIME = 3000)
	var/turf/T = loc
	if(isturf(T) && T.remaster_lair && T.remaster_lair != "sanctum") TIME = round(TIME * 2 / 3)
	return ..(breederMale, breederFemale, TIME)

// --- Halls: drag to size --------------------------------------------------------------------
// A hall is laid out to fit the rectangle dragged (RemasterPaint): walls round it (rock where
// it is cut into a mountain is its wall), the race's floor, a door in the wall spot with the
// shortest way out (a tunnel is dug through up to ten tiles of rock to open ground), lines of
// pillars or support beams down the hall so no tile is more than four from one (the cave-in
// rule), beds along the back wall, a table and chairs or a campfire in the middle, and the
// race's workshop near the door.
proc/RemasterIsHallMode(mode)
	if(copytext("[mode]", 1, 10) != "Building:") return 0
	var/list/D = RemasterBuildingDef(copytext("[mode]", 10))
	return D && D["hall"]

// The layout of a w by h hall with its door in the side wall ("south" is the bottom row,
// j = 0) at place "at" along it: list of list(i, j, letter), i east and j north from the
// corner; outside it the tile in front of the door (",") and the traps beside that ("^").
proc/RemasterHallLayout(list/D, w, h, side, at)
	var/list/G = list()
	for(var/j = 0, j < h, j++)
		for(var/i = 0, i < w, i++)
			G["[i],[j]"] = (!i || !j || i == w - 1 || j == h - 1) ? "#" : "."
	// "in" (ix, iy) runs from the door into the hall
	var/ix = 0
	var/iy = 0
	var/di = at
	var/dj = at
	switch(side)
		if("south")
			iy = 1
			dj = 0
		if("north")
			iy = -1
			dj = h - 1
		if("west")
			ix = 1
			di = 0
		else
			ix = -1
			di = w - 1
	G["[di],[dj]"] = "D"
	var/deep = (ix ? w : h) - 2      // inside, from the door's wall to the back wall
	var/wide = (ix ? h : w) - 2      // inside, along the door's wall
	var/lane = (ix ? dj : di) - 1    // the door's place along it
	var/list/pos = list()            // "a,d" (a along, d in from the door) -> "i,j"
	var/list/back = list()           // "i,j" -> "a,d"
	for(var/d = 0, d < deep, d++)
		for(var/a = 0, a < wide, a++)
			var/i = ix ? (ix > 0 ? 1 + d : w - 2 - d) : 1 + a
			var/j = ix ? 1 + a : (iy > 0 ? 1 + d : h - 2 - d)
			pos["[a],[d]"] = "[i],[j]"
			back["[i],[j]"] = "[a],[d]"
	var/list/clear = list()          // the way in: two tiles straight in from the door
	for(var/d = 0, d < min(2, deep), d++) clear["[lane],[d]"] = 1
	// pillars (or beams): lines down the hall one in from the sides, and down the middle of
	// a wide one, every third tile from the back; then one wherever a tile is still more than
	// four from any
	var/list/cols = list()
	if(wide >= 5) cols += list(1, wide - 2)
	if(wide >= 9 || (wide < 5 && deep >= 6)) cols += round((wide - 1) / 2)
	var/list/pil = list()
	for(var/a in cols)
		for(var/d = deep - 2, d >= 2, d -= 3)
			if(!clear["[a],[d]"] && G[pos["[a],[d]"]] == ".")
				G[pos["[a],[d]"]] = "|"
				pil += list(list(a, d))
	var/ca = round((wide - 1) / 2)
	var/cd = round((deep - 1) / 2)
	for(var/d = deep - 1, d >= 0, d--)
		for(var/a = 0, a < wide, a++)
			var/held = 0
			for(var/list/q in pil) if(abs(q[1] - a) <= 4 && abs(q[2] - d) <= 4)
				held = 1
				break
			if(held) continue
			var/list/at2 = list(ca, max(min(deep - 1, 2), cd))
			if(clear["[at2[1]],[at2[2]]"] || G[pos["[at2[1]],[at2[2]]"]] != ".") at2 = list(a, d)
			if(clear["[at2[1]],[at2[2]]"] || G[pos["[at2[1]],[at2[2]]"]] != ".") continue
			G[pos["[at2[1]],[at2[2]]"]] = "|"
			pil += list(at2)
	// beds along the back wall, every other tile
	var/beds = 0
	if(deep >= 3) for(var/a = 0, a < wide && beds < 8, a += 2)
		var/k = "[a],[deep - 1]"
		if(!clear[k] && G[pos[k]] == ".")
			G[pos[k]] = "B"
			beds++
	// in the middle: a campfire well away from the walls, or a table with a chair each side
	if(D["fire"])
		if(wide >= 5 && deep >= 5 && !clear["[ca],[cd]"] && G[pos["[ca],[cd]"]] == ".") G[pos["[ca],[cd]"]] = "f"
	else if(wide >= 3 && deep >= 4)
		for(var/off in list(0, 1, -1, 2))
			var/td = cd + off
			if(td < 2 || td > deep - 2 || clear["[ca],[td]"] || G[pos["[ca],[td]"]] != ".") continue
			G[pos["[ca],[td]"]] = "T"
			for(var/s in list(-1, 1))
				var/k = "[ca + s],[td]"
				if(pos[k] && !clear[k] && G[pos[k]] == ".") G[pos[k]] = "C"
			break
	// the workshop near the door, with the tile to its west clear (it takes that one too)
	if(D["shop"])
		var/done = 0
		for(var/d = 1, d < deep - 1 && !done, d++)
			for(var/a = wide - 1, a >= 0, a--)
				var/k = "[a],[d]"
				if(clear[k] || G[pos[k]] != ".") continue
				var/list/ij = splittext(pos[k], ",")
				var/wk = "[text2num(ij[1]) - 1],[text2num(ij[2])]"
				if(!back[wk] || clear[back[wk]] || G[wk] != ".") continue
				G[pos[k]] = "W"
				done = 1
				break
	var/list/out = list()
	for(var/k in G)
		var/list/ij = splittext(k, ",")
		out += list(list(text2num(ij[1]), text2num(ij[2]), G[k]))
	out += list(list(di - ix, dj - iy, ","))
	if(D["trap"])
		var/ax = ix ? 0 : 1
		var/ay = ix ? 1 : 0
		out += list(list(di - ix + ax, dj - iy + ay, "^"), list(di - ix - ax, dj - iy - ay, "^"))
	return out

// The menu's plan of a hall: w by h, its door to the south (rows north first).
proc/RemasterHallRows(list/D, w, h)
	var/list/G = list()
	var/lo = 0
	for(var/list/X in RemasterHallLayout(D, w, h, "south", round((w - 1) / 2)))
		G["[X[1]],[X[2]]"] = X[3]
		lo = min(lo, X[2])
	var/list/rows = list()
	for(var/j = h - 1, j >= lo, j--)
		var/r = ""
		for(var/i = 0, i < w, i++) r += G["[i],[j]"] || " "
		rows += r
	return rows

// A hall dragged from x0,y0 to x1,y1 on this layer.
Player/proc/RemasterPlanHall(x0, y0, x1, y1)
	var/list/E = RemasterBuildEntryForMode(Function)
	var/list/D = E ? RemasterBuildingDef(E["building"]) : null
	if(!D) return 0
	var/ax = min(x0, x1)
	var/bx = max(x0, x1)
	var/ay = min(y0, y1)
	var/by = max(y0, y1)
	var/w = bx - ax + 1
	var/h = by - ay + 1
	if(z == SKY_LAYER)
		RemasterNotice("[D["label"]]: halls go on the ground, underground or into a mountain.")
		return 0
	if(w < 4 || h < 4)
		RemasterNotice("[D["label"]]: drag at least 4 by 4 tiles (walls round a room).")
		return 0
	if(w > 25 || h > 25)
		RemasterNotice("[D["label"]]: at most 25 by 25 tiles.")
		return 0
	// The door: the wall spot with the shortest way out to open ground, nearest the stockpile
	// (or the builders), towards the middle of its wall.
	var/atom/from = RemasterStockpile()
	if(!from || from:z != z)
		from = null
		for(var/mob/Monsters/M in RemasterBuilderUnits()) if(M.z == z)
			from = M
			break
	var/best_side
	var/best_at
	var/best_rock = 0
	var/best_cost = 1#INF
	for(var/side in list("south", "north", "west", "east"))
		var/len = (side in list("south", "north")) ? w : h
		var/sx = side == "west" ? -1 : (side == "east" ? 1 : 0)
		var/sy = side == "south" ? -1 : (side == "north" ? 1 : 0)
		for(var/at = 1, at <= len - 2, at++)
			var/wx = side == "west" ? ax : (side == "east" ? bx : ax + at)
			var/wy = side == "south" ? ay : (side == "north" ? by : ay + at)
			var/rock = 0
			var/turf/O
			var/ok = 0
			for(var/n = 1, n <= 11, n++)
				O = locate(wx + sx * n, wy + sy * n, z)
				if(!O) break
				if(!O.density)
					ok = 1
					break
				if(n == 11 || !RemasterDiggable(O)) break
				rock++
			if(!ok) continue
			var/cost = rock * 100 + (from ? get_dist(O, from) : 0) + abs(at - (len - 1) / 2) * 0.1
			if(cost < best_cost)
				best_cost = cost
				best_side = side
				best_at = at
				best_rock = rock
	if(!best_side)
		RemasterNotice("[D["label"]]: no way out within ten tiles of rock. Dig a tunnel towards it first, or drag it nearer one.")
		return 0
	var/list/cells = list()
	for(var/list/X in RemasterHallLayout(D, w, h, best_side, best_at))
		var/turf/T = locate(ax + X[1], ay + X[2], z)
		if(T) cells += list(list(T, X[3]))
		else if(X[3] != "^")
			RemasterNotice("[D["label"]]: too close to the edge of the map.")
			return 0
	// the tunnel out through the rock, beyond the tile in front of the door
	var/ox = best_side == "west" ? -1 : (best_side == "east" ? 1 : 0)
	var/oy = best_side == "south" ? -1 : (best_side == "north" ? 1 : 0)
	var/dx = best_side == "west" ? ax : (best_side == "east" ? bx : ax + best_at)
	var/dy = best_side == "south" ? ay : (best_side == "north" ? by : ay + best_at)
	for(var/n = 2, n <= best_rock, n++) cells += list(list(locate(dx + ox * n, dy + oy * n, z), ","))
	var/turf/C = locate(round((ax + bx) / 2), round((ay + by) / 2), z)
	var/list/S = RemasterPlanCells(E, D, cells, C, ", [w] by [h], door to the [best_side]", "Drag it somewhere else.")
	if(S && remaster_hall_ceil > 2)
		S["ceil"] = remaster_hall_ceil         // a high hall: its roof is mined out once it is built
		S["rect"] = "[ax],[ay],[bx],[by]"
	return S

// --- High halls --------------------------------------------------------------------------------
// A hall planned with a ceiling higher than the two blocks a dug tunnel has (the Build tab's
// Ceiling line) is built as usual, then its builders mine the rock over its inner tiles a block
// at a time (Mountains.dm's RemasterRoofBlow, the Mine roof work) until the ceiling is that high.
// At least one block is left overhead, so a hall never opens to the sky; its pillars, built
// first, hold the roof while they work. Only a hall dug into a mountain has rock overhead.
Player/var/tmp/remaster_hall_ceil = 2

// The inner tiles of a high hall whose roof is still to come down (none while pieces are left).
Player/proc/RemasterBuildingRoofs(list/S)
	. = list()
	var/want = S["ceil"]
	if(!want || want <= 2 || !S["rect"]) return
	if(remaster_blueprints) for(var/list/B in remaster_blueprints) if(B["site"] == S["id"]) return
	var/list/r = splittext(S["rect"], ",")
	for(var/turf/T in block(locate(text2num(r[1]) + 1, text2num(r[2]) + 1, S["z"]), locate(text2num(r[3]) - 1, text2num(r[4]) - 1, S["z"])))
		if(!T.density && T.remaster_roof > 1 && (T.remaster_ceil || 2) < want) . += T

// A worker on a high hall with its pieces done: to the nearest such tile, then a blow at a time.
Player/proc/RemasterBuildingRoofTick(list/S, mob/Monsters/M, list/roofs)
	var/turf/target
	for(var/turf/T in roofs) if(!target || get_dist(M, T) < get_dist(M, target)) target = T
	if(!target) return
	M.remaster_site_standby = 0
	if(get_dist(M, target) > 1)
		M.RemasterSiteWalk(target)
	else if(world.time >= M.remaster_hand_at)
		if(M.remaster_site_dest && M.destination == M.remaster_site_dest) M.destination = null
		M.remaster_hand_at = world.time + max(8, M.Delay * 2)
		M.dir = get_dir(M, target) || M.dir
		var/before = target.remaster_roof
		M.RemasterRoofBlow(target, !RemasterCanDigRock(M))
		if(target.remaster_roof != before) remaster_dirty_turfs["[target.x],[target.y],[target.z]"] = 1   // a var only: the tile's signature can't see it
	S["note"] = "[M.name] is raising the ceiling ([length(roofs)] tile[length(roofs) == 1 ? "" : "s"] to go, up to [S["ceil"]] high)"
	M.RemasterSiteStatus("Raising the ceiling of the [lowertext(S["label"])] ([length(roofs)] left)")

// --- Walls hold the roof ---------------------------------------------------------------------
// A built wall underground or in a mountain holds the roof up like a support beam. The
// original cave-in (digging, Bump.dm) and roof mining's (Mountains.dm) spare cave floor with
// a pillar within four tiles, so each such wall carries an unseen pillar, kept by this sweep
// round the player's units: put in by new walls, taken out with walls that are gone.
obj/Items/Furniture/Pillars/RemasterWallHold
	// its values: art/items/catalogue.json row furniture.pillars.remasterwallhold (export_items.py writes ItemData.dm)

Player/var/tmp/remaster_hold_next = 0
Player/proc/RemasterWallHoldTick()
	if(world.time < remaster_hold_next) return
	remaster_hold_next = world.time + 100
	var/list/seen = list()
	for(var/mob/Monsters/M in UnitList)
		if(M.Owner != src || !isturf(M.loc)) continue
		var/turf/U = M.loc
		if(U.z != UNDERGROUND_LAYER && !U.remaster_roof) continue
		for(var/turf/T in range(5, U))
			if(seen[T]) continue
			seen[T] = 1
			var/wall = (T.density && ("IsWall" in T.vars) && T.vars["IsWall"]) || RmBuilt(T)   // a laid column too (Plans.dm)
			var/obj/Items/Furniture/Pillars/RemasterWallHold/H = locate() in T
			if(wall && !H)
				H = new
				H.loc = T
			else if(!wall && H) del(H)
