// Building kit, part 2: the Build tab. A catalog of everything the original
// build menus offer (walls, floors, bridges, stairs, workshops, devices, traps,
// dig marks), filtered by the races the player has, with the original menus'
// race rules. Picking an entry sets the original build mode; painting it makes
// a construction task (Blueprints.dm). The tab lists each task with its needs,
// progress and workers. Planned tiles also show as ghosts on the 2D map.
// Other features can add entries with RemasterBuildDef in RemasterBuildCatalog.

var/list/remaster_build_catalog

// id, label, category, build mode, material, pieces used per tile (0: kept in
// the bag, as the original floors do), menu/ghost icon and state, who builds it.
proc/RemasterBuildDef(id, label, cat, mode, mat, per, icon, state, who)
	return list("id"=id, "label"=label, "cat"=cat, "mode"=mode, "mat"=mat, "per"=per, "icon"=icon, "state"=state, "who"=who)

proc/RemasterBuildCatalog()
	if(remaster_build_catalog) return remaster_build_catalog
	var/list/C = list()
	// Fortress (Helm's Deep, WallWalks.dm): every finished wall that is not a house wall gets
	// a walk on the layer above; the 3D view draws walls, towers, gates, stairs and ramps from
	// the tiles. Tower and the single pieces are placed with one click.
	C += list(RemasterBuildDef("fortress_wall", "Fortress wall", "fortress", "FortressWall", "stone", 1, 'Cave.dmi', "DetailedWall", "Stone-wall builders; paint 2-3 rows side by side for one wide wall with a walk"))
	C += list(RemasterBuildDef("tower", "Tower", "fortress", "Tower", "stone", 1, 'Cave.dmi', "StoneWall2", "Stone-wall builders; a 3x3 block of wall around the tile you click"))
	C += list(RemasterBuildDef("gate", "Gate", "fortress", "Gate", "door", 1, 'Cave.dmi', "WoodenDoor", "Anyone with a door (made at a workshop), set in a 1-tile gap between two walls"))
	C += list(RemasterBuildDef("wall_stairs", "Wall stairs", "fortress", "WallStairs", "stone", 1, 'Stairs.dmi', "StoneUp", "Anyone; on open ground beside a wall with a walk"))
	C += list(RemasterBuildDef("wall_ramp", "Ramp up the wall", "fortress", "WallRamp", "stone", 1, 'Cave.dmi', "DetailedFloor", "Anyone; on open ground beside a wall (3 stone), or on the inner row of a wall two thick (cut into it, free)"))
	C += list(RemasterBuildDef("wood_wall", "Wooden wall", "walls", "PlaceWoodenWall", "wood", 1, 'Cave.dmi', "WoodWall", "Dwarves, Humans, Orcs, Goblins, Svartalfar, Vampires, Gargoyles"))
	C += list(RemasterBuildDef("stone_wall", "Stone wall", "walls", "PlaceStoneWall", "stone", 1, 'Cave.dmi', "DetailedWall", "Dwarves, Humans, Goblins (obsidian), Svartalfar, Vampires, Gargoyles, sand workers, Illithids (crystal)"))
	C += list(RemasterBuildDef("bone_wall", "Bone wall", "walls", "PlaceBoneWall", "bones", 1, 'Cave.dmi', "Bone Wall", "Kobolds, Ratmen, Lizardmen, Frogmen, Goblins, Svartalfar, Vampires, Gargoyles, sand workers"))
	C += list(RemasterBuildDef("tribal_wall", "Tribal wall", "walls", "PlaceTribalWall", "wood", 1, 'Cave.dmi', "TribalWall", "Lizardmen, Frogmen"))
	C += list(RemasterBuildDef("elf_wall", "Elf wall", "walls", "PlaceElfWall", "wood", 1, 'Cave.dmi', "Elf Wall", "Elves"))
	C += list(RemasterBuildDef("secret_wall", "Secret wall", "walls", "PlaceSecretWall", "stone", 1, 'Cave.dmi', "CaveWall", "Every race with a wall menu; looks like natural rock"))
	C += list(RemasterBuildDef("silk_wall", "Silk wall", "walls", "PlaceSilkWall", "web", 0, 'Cave.dmi', "SilkWall", "Spiders, 25 web each"))
	C += list(RemasterBuildDef("flesh_wall", "Flesh wall", "walls", "PlaceDevourerWall", "flesh", 0, 'Cave.dmi', "DevourerWall2", "Devourers, from stored flesh"))
	C += list(RemasterBuildDef("wood_floor", "Wooden floor", "floors", "PlaceWoodenFloor", "wood", 0, 'Cave.dmi', "WoodFloor", "Dwarves, Humans, Elves, Orcs, Goblins, Svartalfar, Vampires"))
	C += list(RemasterBuildDef("stone_floor", "Stone floor", "floors", "PlaceStoneFloor", "stone", 0, 'Cave.dmi', "DetailedFloor", "Dwarves, Humans, Goblins, Svartalfar, Vampires, Gargoyles, sand workers, Illithids"))
	C += list(RemasterBuildDef("bone_floor", "Bone floor", "floors", "PlaceBoneFloor", "bones", 0, 'Cave.dmi', "BoneFloor", "Kobolds, Ratmen, Lizardmen, Frogmen, Goblins, Svartalfar, Vampires, sand workers"))
	C += list(RemasterBuildDef("tribal_floor", "Tribal floor", "floors", "PlaceTribalFloor", "wood", 0, 'Cave.dmi', "Tribal", "Lizardmen, Frogmen"))
	C += list(RemasterBuildDef("flesh_floor", "Flesh floor", "floors", "PlaceDevourerFloor", "flesh", 0, 'Cave.dmi', "DevourerFloor", "Devourers with a stored body"))
	C += list(RemasterBuildDef("remove_floor", "Remove floor", "floors", "DestroyFloor", null, 0, 'Cave.dmi', "CaveFloor", "Most races"))
	C += list(RemasterBuildDef("wood_bridge", "Wooden bridge", "bridges", "PlaceWoodenBridge", "wood", 1, 'Cave.dmi', "WoodBridge", "Dwarves, Humans, Elves, Orcs, Goblins, Svartalfar, Vampires, Gargoyles"))
	C += list(RemasterBuildDef("stone_bridge", "Stone bridge", "bridges", "PlaceStoneBridge", "stone", 1, 'Cave.dmi', "Bridge", "Dwarves, Humans, Goblins, Svartalfar, Vampires, Gargoyles; also over lava"))
	C += list(RemasterBuildDef("bone_bridge", "Bone bridge", "bridges", "PlaceBoneBridge", "bones", 1, 'Cave.dmi', "BoneBridge", "Kobolds, Ratmen, Goblins, Svartalfar, Vampires, Gargoyles"))
	C += list(RemasterBuildDef("tribal_bridge", "Tribal bridge", "bridges", "PlaceTribalBridge", "wood", 1, 'Cave.dmi', "TribalBridge", "Lizardmen, Frogmen"))
	C += list(RemasterBuildDef("silk_bridge", "Silk bridge", "bridges", "PlaceSilkBridge", "web", 0, 'Spiders.dmi', "Silk Bride", "Spiders, 25 web each"))
	// Roads (Roads.dm): units walk faster along them.
	C += list(RemasterBuildDef("stone_road", "Cobbled road", "roads", "PlaceStoneRoad", "stone", 1, 'Cave.dmi', "DetailedFloor", "Anyone who can carry stone; units walk about 40% faster on it"))
	C += list(RemasterBuildDef("dirt_road", "Dirt track", "roads", "PlaceDirtRoad", null, 0, 'Cave.dmi', "CaveFloor", "Anyone, no material; units walk about 15% faster on it"))
	C += list(RemasterBuildDef("remove_road", "Remove road", "roads", "RemoveRoad", null, 0, 'Cave.dmi', "Dig", "Anyone"))
	C += list(RemasterBuildDef("stairs_wood", "Wooden stairs", "stairs", "Stairs:Wood", "wood", 1, 'Stairs.dmi', "WoodUp", "Every race but Spiders"))
	C += list(RemasterBuildDef("stairs_stone", "Stone stairs", "stairs", "Stairs:Stone", "stone", 1, 'Stairs.dmi', "StoneUp", "Every race but Spiders"))
	C += list(RemasterBuildDef("stairs_ancient", "Ancient stairs", "stairs", "Stairs:Ancient", "stone", 1, 'Stairs.dmi', "AncientUp", "Every race but Spiders"))
	C += list(RemasterBuildDef("stairs_bamboo", "Bamboo stairs", "stairs", "Stairs:Bamboo", "wood", 1, 'Stairs.dmi', "BambooUp", "Lizardmen, Frogmen"))
	C += list(RemasterBuildDef("stairs_bone", "Bone stairs", "stairs", "Stairs:Bone", "bones", 1, 'Stairs.dmi', "BoneUp", "Poison-using races"))
	C += list(RemasterBuildDef("stairs_silk", "Silk stairs", "stairs", "Stairs:Spider", "web", 0, 'Stairs.dmi', "SpiderUp", "Spiders, 100 web"))
	var/list/W = RemasterWorkshopDefs()
	for(var/id in W)
		var/list/D = W[id]
		var/cat = RemasterIsRune(id) ? "devices" : "workshops"
		var/state = "WorkShopLeft"
		var/icon = 'Cave.dmi'
		switch(id)
			if("campfire") state = "Fire"
			if("cauldron") state = "Oven"
			if("altar") state = "GoodAltar"
			if("banner", "notice") state = "sign"
			if("stall", "foodstall", "clinic", "surgery", "tavern") state = "Table"
			if("graveyard")
				icon = 'StoneItems.dmi'
				state = "TombStone1"
			if("foodpot")
				icon = 'Icons/Remastered/Cauldron.dmi'
				state = "cold"
		if(RemasterIsRune(id))
			icon = 'Icons/Remastered/Runes.dmi'
			var/list/states = list("rune"="line", "crystal"="crystal", "runedoor"="door_shut", "firejet"="jet", "spikes"="spikes_down", "plate"="plate", "lever"="lever_l", "lamp"="lamp_off", "bell"="bell")
			state = states[id]
		var/list/E = RemasterBuildDef(id, D[1], cat, "Workshop:[id]", RemasterMaterialKind(D[3]) == "material" ? null : (RemasterMaterialKind(D[3]) == "gems" ? "gem" : RemasterMaterialKind(D[3])), 1, icon, state, id == "altar" ? "Anyone: stone, with a lump of silver and a golden nugget in the builder's bag. Three sacrifices on it make it an Evil Altar" : "Any race that can carry the material")
		E["shop"] = 1
		if(id == "foodpot") E["who"] = "Anyone with 1 stone. A cauldron for food: villagers eat here, cooks fill it, and with wood under it raw meat stews without burning and hot stew fills more"
		if(id == "surgery") E["who"] = "Anyone with 1 wood. Near the Doctor's stall: the Doctor carries the fallen here, grafts limbs (any race's) and fits false ones: iron, peg legs, bone, glimmering, automail"
		if(id == "graveyard") E["who"] = "Anyone with 1 stone. A villager on the Gravedigger job buries the dead around it (no rot, no fever) and keeps the village clean"
		if(id == "notice") E["who"] = "Anyone with 1 wood. Post quests for other players here (the Quests button): coins and goods you put up are held until the quest is done"
		if(id == "tavern") E["who"] = "Anyone with 1 wood. Keeps wine (poured from bottles or pressed from fruit and fungus); villagers drink here at night, and drunks brawl"
		if(id == "clinic") E["who"] = "Anyone with 1 wood. Keeps herbs and the remedies made from them; give a villager the Doctor job to treat the sick"
		if(id == "foodstall") E["who"] = "Anyone with 1 wood. A food store of 30: farmers and cooks lay food out, villagers eat here and take a piece along"
		C += list(E)
	C += list(RemasterBuildDef("stonefall", "Stonefall trap", "traps", "PlaceStoneFall", "stone", 1, 'Cave.dmi', "FallTrap", "Every race with a trap menu"))
	C += list(RemasterBuildDef("bone_spikes", "Bone spike trap", "traps", "PlaceBoneSpikes", "bones", 1, 'Cave.dmi', "BST", "Kobolds, Goblins, Ratmen"))
	C += list(RemasterBuildDef("ribcage", "Ribcage trap", "traps", "PlaceRibcage", "bones", 1, 'Cave.dmi', "RibTrap", "Kobolds, Goblins, Ratmen"))
	C += list(RemasterBuildDef("beam", "Support beam", "digging", "Beam", "wood", 1, 'Cave.dmi', "Wood Post", "Anyone; drag along a tunnel and a beam goes in every 9 tiles, which keeps it from caving in. Beams made at a carpentry go up by themselves in a tunnel when a unit carries them"))
	C += list(RemasterBuildDef("channel", "Dig a channel", "digging", "DigChannel", null, 0, 'Cave.dmi', "Dig2", "Dwarves, Humans with a spade; next to water or lava"))
	var/list/A = RemasterBuildDef("autodig", "Mark for digging", "digging", "PlaceAutodig", null, 0, 'Cave.dmi', "Dig", "Anyone; the selected units dig the marks")
	A["now"] = 1
	C += list(A)
	A = RemasterBuildDef("autodig_remove", "Remove dig marks", "digging", "RemoveAutodig", null, 0, 'Cave.dmi', "Dig", "Anyone")
	A["now"] = 1
	C += list(A)
	C += RemasterBuildingCatalog() // buildings, lairs, furniture, webs (Buildings.dm)
	remaster_build_catalog = C
	return C

proc/RemasterBuildEntry(id)
	for(var/list/E in RemasterBuildCatalog()) if(E["id"] == id) return E
	return null

proc/RemasterBuildEntryForMode(mode)
	if(!mode) return null
	if(copytext(mode, 1, 8) == "Stairs:")
		var/list/p = splittext(mode, ":")
		if(p.len >= 2) mode = "Stairs:[p[2]]"
	for(var/list/E in RemasterBuildCatalog()) if(E["mode"] == mode) return E
	return null

proc/RemasterBuildCat(mode)
	var/list/E = RemasterBuildEntryForMode(mode)
	return E ? E["cat"] : null

// Does building one tile use the material up (walls, bridges), or does it only
// have to be in the bag (the original floors)?
proc/RemasterBuildUses(mode)
	var/list/E = RemasterBuildEntryForMode(mode)
	return E ? E["per"] : 1

// The original build menus' race rules (Verbs.dm Walls/Floors/Bridge/Trap
// menus, Stairs.dm), per entry.
proc/RemasterBuildRaceOK(id, mob/Monsters/M)
	var/r = M.Race
	var/sand = M.SandWorker
	var/illithid = M.SubRace == "Illithid"
	switch(id)
		if("wood_wall") return r in list("Vampire", "Svartalfar", "Gargoyle", "Goblin", "Orc", "Human", "Dwarf")
		if("stone_wall", "fortress_wall", "tower") return (r in list("Vampire", "Svartalfar", "Gargoyle", "Goblin", "Human", "Dwarf")) || sand || illithid
		if("bone_wall") return (r in list("Vampire", "Svartalfar", "Gargoyle", "Goblin", "Lizardman", "Frogman", "Kobold", "Ratman")) || sand
		if("tribal_wall", "tribal_floor", "tribal_bridge", "stairs_bamboo") return r in list("Lizardman", "Frogman")
		if("elf_wall") return r == "Elf"
		if("secret_wall", "stonefall") return !(r in list("Spider", "Devourer"))
		if("silk_wall", "silk_bridge", "stairs_silk") return r == "Spider"
		if("flesh_wall", "flesh_floor") return r == "Devourer"
		if("wood_floor") return r in list("Elf", "Orc", "Dwarf", "Human", "Goblin", "Svartalfar", "Vampire")
		if("stone_floor") return (r in list("Dwarf", "Human", "Gargoyle", "Goblin", "Svartalfar", "Vampire")) || sand || illithid
		if("bone_floor") return (r in list("Lizardman", "Frogman", "Kobold", "Ratman", "Goblin", "Svartalfar", "Vampire")) || sand
		if("remove_floor") return (r in list("Lizardman", "Frogman", "Elf", "Orc", "Dwarf", "Human", "Gargoyle", "Kobold", "Ratman", "Goblin", "Svartalfar", "Vampire", "Spider")) || sand || illithid
		if("wood_bridge") return r in list("Goblin", "Svartalfar", "Vampire", "Gargoyle", "Dwarf", "Human", "Orc", "Elf")
		if("stone_bridge") return r in list("Goblin", "Svartalfar", "Vampire", "Gargoyle", "Dwarf", "Human")
		if("bone_bridge") return r in list("Goblin", "Svartalfar", "Vampire", "Gargoyle", "Kobold", "Ratman")
		if("stairs_wood", "stairs_stone", "stairs_ancient") return r != "Spider"
		if("stairs_bone") return M.UsesPoison && r != "Spider"
		if("bone_spikes", "ribcage") return r in list("Kobold", "Goblin", "Ratman")
		if("channel") return r in list("Dwarf", "Human")
		if("gem") return !(r in list("Spider", "Kobold"))
		if("autodig", "autodig_remove", "dirt_road", "remove_road") return 1
	var/b = RemasterBuildingRaceOK(id, M) // buildings, lairs, furniture, webs (Buildings.dm)
	if(!isnull(b)) return b
	// Workshops and devices: anyone who can carry the material.
	return r != "Spider"

proc/RemasterBuildEligible(mode, mob/Monsters/M)
	if(!M || M.Wagon) return 0
	var/list/E = RemasterBuildEntryForMode(mode)
	if(!E) return 1 // a mode from elsewhere: the original code decides
	return RemasterBuildRaceOK(E["id"], M)

proc/RemasterRacePlural(race)
	switch(race)
		if("Dwarf") return "Dwarves"
		if("Elf") return "Elves"
		if("Lizardman") return "Lizardmen"
		if("Frogman") return "Frogmen"
		if("Ratman") return "Ratmen"
		if("Svartalfar", "Illithid") return race
	return "[race]s"

// --- Tile rules ------------------------------------------------------------------
// Why a tile can never take this build (null when it can). Painting skips these.
proc/RemasterBuildBlocked(turf/T, mode)
	if(!T) return "off the map"
	var/kind = RemasterBuildShape(mode)
	var/cat = RemasterBuildCat(mode)
	if(kind == "road") return RemasterRoadBlocked(T, mode)
	if(kind == "piece") return RemasterPieceBlocked(T, mode)
	switch(mode)
		if("Beam")
			if(T.density) return "beams stand on open floor"
			if(locate(/obj/Items/Furniture/Pillars) in T) return "there's a pillar there already"
			return null
		if("Gate")
			if(T.density) return "a gate goes in an open gap between walls"
			if(RemasterSiegeDoor(T)) return "there's a door there already"
			return null
		if("WallStairs")
			if(T.z != GROUND_LAYER) return "wall stairs are built on the surface"
			if(T.density || T.Detailed || T.icon == 'Stairs.dmi') return "wall stairs go on open, unfloored ground beside a wall"
			return null
		if("WallRamp")
			if(RemasterWallStands(T)) return null // cut into the wall
			if(T.z != GROUND_LAYER) return "ramps are built on the surface"
			if(T.density || T.icon == 'Stairs.dmi') return "a ramp starts on open ground beside a wall, or on a wall's inner row"
			return null
	if(mode == "DestroyFloor") return (T.density || !T.Detailed) ? "no built floor there" : null
	if(mode == "DigChannel") return T.density ? "the ground must be open" : null
	if(cat == "traps")
		if(T.density) return "traps go on open ground"
		for(var/obj/Items/Traps/X in T) return "there's a trap there already"
		return null
	switch(kind)
		if("wall") return T.density ? "already solid" : null
		if("floor")
			if(T.density) return "solid rock or wall"
			if(T.Detailed || T.isbridge) return "there's a floor there already"
		if("bridge")
			if(T.isbridge) return "there's a bridge there already"
			if(T.Content3 == "Liquid" || T.Content == "Chasm") return null
			if(T.Content3 == "Lava" && mode == "PlaceStoneBridge") return null
			return mode == "PlaceStoneBridge" ? "bridges go over water, chasms or lava" : "bridges go over water or chasms"
		if("stairs") if(T.density || T.opacity || T.icon == 'Stairs.dmi') return "stairs need open ground"
	return null

// Why a tile has to wait for now (null when it can be built).
proc/RemasterBuildWait(turf/T, mode, mob/Monsters/M)
	var/kind = RemasterBuildShape(mode)
	if((mode == "WallStairs" || mode == "WallRamp") && !RemasterWallStands(T) && !RemasterWalkBeside(T))
		return "Waits for the wall beside it to be finished (its walk comes with it)"
	var/trap = RemasterBuildCat(mode) == "traps"
	if(!trap && (kind in list("wall", "floor")) && T.icon_state == "Sky" && !T.Supported && mode != "DestroyFloor")
		return "Needs a wall or floor under it first (sky tiles must be supported)"
	if(kind == "wall" && !trap) for(var/mob/Monsters/X in T) if(X != M) return "[X.name] is standing on the spot"
	if((mode in list("Piece:cartstop", "Piece:minecart")) && T.remaster_road != "rail") return "Waits for the track to be laid there (Carts.dm)"
	var/gate = RemasterGateWait(T, mode)   // a drawbridge built out from the bank (Gates.dm)
	if(gate) return gate
	return null

mob/Monsters/proc/RemasterSiteBodyNeed(mode)
	switch(mode)
		if("PlaceSilkWall", "PlaceSilkBridge")
			if(WebContent < 25) return "Needs 25 web ([name] has [round(WebContent)])"
		if("PlaceDevourerWall")
			if(EggContent < 0.25) return "Needs stored flesh ([name] has none)"
		if("PlaceDevourerFloor")
			if(EggContent < 1) return "Needs a stored body"
		if("DigChannel")
			if(!HasItem(/obj/Items/Shafts/Spade)) return "Needs a spade in the bag"
	if(copytext(mode, 1, 15) == "Stairs:Spider:" && WebContent < 100) return "Needs 100 web ([name] has [round(WebContent)])"
	if(copytext(mode, 1, 7) == "Piece:") return RemasterPieceBodyNeed(mode)
	if(mode == "Workshop:altar") return RmAltarNeed(src)   // silver and gold (HalfDemons.dm)
	return null

Player/proc/RemasterBuildFailReason(mob/Monsters/M, turf/T, mode)
	if(!RemasterMayWork(T, 1)) return "That land belongs to another realm"
	if(!RemasterBuildEligible(mode, M)) return "[RemasterRacePlural(M.Race)] can't build [lowertext(RemasterBuildModeLabel(mode))]"
	var/blocked = RemasterBuildBlocked(T, mode)
	if(blocked) return "Can't build here: [blocked]"
	var/wait = RemasterBuildWait(T, mode, M)
	if(wait) return wait
	var/path = RemasterBuildMaterial(mode)
	if(path && !M.RemasterCarriedCount(path)) return "Needs [RemasterMaterialKind(path)] in the bag"
	var/need = M.RemasterSiteBodyNeed(mode)
	if(need) return need
	switch(mode)
		if("Gate") return "Can't set a door here"
		if("WallStairs") return "Wall stairs need open ground beside a wall with a walk, and open sky above"
		if("WallRamp") return "No room for the ramp: three open tiles along a wall with a walk, or three tiles of a wall's inner row"
	switch(RemasterBuildShape(mode))
		if("road") return "Can't lay the road here: it needs open ground (no built floor, field, water or stairs)"
		if("workshop") return "Can't build the workshop here: it needs open ground, a free tile to its left and no workshop next to it"
		if("stairs") return "Can't build stairs here: both levels must be open there"
	return "[M.name] couldn't build here: check material in their bag and that the tile is clear"

// --- Support beams ---------------------------------------------------------------
// A wooden post with a crossbeam under a tunnel roof. It is a kind of the original pillars,
// so the original cave-in (a pillar within four tiles keeps a floor tile open) counts it,
// as does RemasterCaveIn (Mountains.dm). Not dense: a one-tile tunnel stays passable.
// Built from the Build tab, or made at a carpentry (Settlement.dm) and carried: a unit
// with one in its bag puts it up by itself in an unsupported tunnel (RemasterAutoBeam).
obj/Items/Furniture/Pillars/WoodenBeam
	// its values: art/items/catalogue.json row furniture.pillars.woodenbeam (export_items.py writes ItemData.dm)

// Where the beams of a dragged area go: one every 9 tiles each way (every floor tile then
// has one within 4), the first 4 tiles in, and an extra one at the far end when that is more
// than 4 past the last; on a wall or rock, the nearest open tile of the area within 2 instead.
// Spots that already have a pillar within 2 are left out.
proc/RemasterBeamSpots(list/tiles, x0, y0, x1, y1, level)
	var/list/xs = RemasterBeamLine(min(x0, x1), max(x0, x1))
	var/list/ys = RemasterBeamLine(min(y0, y1), max(y0, y1))
	var/list/out = list()
	for(var/sy in ys)
		for(var/sx in xs)
			var/turf/spot = locate(sx, sy, level)
			var/turf/T = spot
			if(!T || T.density)
				T = null
				if(spot) for(var/turf/N in range(2, spot))
					if(N.density || !(N in tiles)) continue
					if(!T || get_dist(N, spot) < get_dist(T, spot)) T = N
			if(!T || (T in out) || (locate(/obj/Items/Furniture/Pillars) in range(2, T))) continue
			out += T
	return out

proc/RemasterBeamLine(a, b)
	var/list/out = list()
	var/pos = a + min(4, round((b - a) / 2))
	while(pos <= b)
		out += pos
		pos += 9
	if(b - out[length(out)] > 4) out += b
	return out

Player/proc/RemasterBuildBeam(mob/Monsters/M, turf/T)
	if(!T || T.density || get_dist(M, T) > 1 || M.z != T.z) return 0
	if(locate(/obj/Items/Furniture/Pillars) in T) return 0
	var/obj/Items/woods/wood/W = M.HasItem(/obj/Items/woods/wood)
	if(!W) return 0
	if(M.DropItem(W)) del(W)
	var/obj/Items/Furniture/Pillars/WoodenBeam/B = new(T)
	B.Owner = src
	return 1

// A unit carrying a support beam that stands in an open tunnel (cave floor, the tiles a
// cave-in fills) with no pillar within four tiles puts the beam up where it stands. A miner
// with beams in its bag so leaves one about every five tiles of new tunnel, which keeps the
// tiles round it supported while it digs. Set down as the original pillars' Drop does
// (no decay timer), so it stays.
mob/Monsters/proc/RemasterAutoBeam(Player/P)
	if(Flying || !isturf(loc)) return 0
	var/turf/T = loc
	if(T.density || !(istype(T, /turf/grounds/cavefloor) || istype(T, /turf/grounds/cellarfloor))) return 0
	var/obj/Items/Furniture/Pillars/WoodenBeam/B
	for(var/obj/Items/Furniture/Pillars/WoodenBeam/X in src)
		B = X
		break
	if(!B || (locate(/obj/Items/Furniture/Pillars) in range(4, T))) return 0
	B.loc = T
	B.suffix = null
	B.Owner = P
	weight -= B.weight
	P.RemasterLog("[name] put up a support beam", "work", T)
	return 1

// --- Stairs ----------------------------------------------------------------------
proc/RemasterStairsDir(mode)
	var/list/p = splittext("[mode]", ":")
	return p.len >= 3 ? p[3] : null

proc/RemasterStairsLevel(level, dir)
	if(dir == "Up")
		if(level == GROUND_LAYER) return SKY_LAYER
		if(level == UNDERGROUND_LAYER) return GROUND_LAYER
	if(dir == "Down")
		if(level == GROUND_LAYER) return UNDERGROUND_LAYER
		if(level == SKY_LAYER) return GROUND_LAYER
	return 0

// A click with a stairs mode plans one staircase on that tile.
Player/proc/RemasterPlaceStairs(turf/T)
	var/list/E = RemasterBuildEntryForMode(Function)
	var/dir = RemasterStairsDir(Function)
	if(!E || !T || !(dir in list("Up", "Down"))) return 0
	var/level = RemasterStairsLevel(T.z, dir)
	if(!level)
		RemasterNotice("Stairs can't go [lowertext(dir)] from this layer.")
		return 0
	var/turf/U = locate(T.x, T.y, level)
	var/blocked = RemasterBuildBlocked(T, Function)
	if(!blocked && U && (U.density || U.opacity) && U.icon_state != "CaveWall") blocked = "the other end is blocked"
	if(!blocked && U && U.icon == 'Stairs.dmi') blocked = "there are stairs at the other end already"
	if(!blocked && U && U.Detailed && dir == "Up") blocked = "the tile above has a floor"
	if(blocked)
		RemasterNotice("Can't plan stairs there: [blocked].")
		return 0
	if(!RemasterMayWork(T)) return 0
	if(!remaster_blueprints) remaster_blueprints = list()
	if(RemasterBlueprintAt(T))
		RemasterNotice("That tile is already planned.")
		return 0
	var/mode = Function
	var/list/S = RemasterSiteNew(mode, T.z)
	S["x"] = T.x
	S["y"] = T.y
	S["left"] = 1
	S["total"] = 1
	S["workers"] = 1
	remaster_blueprints += list(list("x"=T.x, "y"=T.y, "z"=T.z, "mode"=mode, "note"="Waiting for a builder", "tries"=0, "site"=S["id"]))
	RemasterUndoPush(list("type"="blueprints", "keys"=list("[T.x],[T.y],[T.z]")))
	var/crew = RemasterSiteAssignUnits(S, RemasterBuilderUnits())
	Function = null
	RemasterNotice("Planned [lowertext(S["label"])]. [RemasterSiteNeedText(S)]. [crew ? crew : RmBuildCrewHint()]")
	return 1

// The original stairs (Code/Building/Stairs.dm) without its two choice dialogs:
// the plan already says which material and which way. Same checks and result.
Player/proc/RemasterBuildStairs(mob/Monsters/M, turf/T, mode)
	var/list/p = splittext("[mode]", ":")
	if(p.len != 3 || M.loc != T || M.z == HELL_LAYER) return 0
	var/TYPE = p[2]
	var/DIR = p[3]
	var/LEVEL = RemasterStairsLevel(T.z, DIR)
	if(!LEVEL) return 0
	if((TYPE == "Spider") != (M.Race == "Spider")) return 0
	if(TYPE == "Bamboo" && !(M.Race in list("Lizardman", "Frogman"))) return 0
	if(TYPE == "Bone" && !M.UsesPoison) return 0
	var/turf/LOC1 = T
	var/turf/LOC2 = locate(T.x, T.y, LEVEL)
	if(!LOC2) return 0
	if((LOC2.density || LOC2.opacity) && LOC2.icon_state != "CaveWall") return 0
	if(LOC1.density || LOC1.opacity || LOC1.icon == 'Stairs.dmi' || LOC2.icon == 'Stairs.dmi') return 0
	if(LOC2.Detailed && DIR == "Up") return 0
	if(TYPE == "Spider")
		if(M.WebContent < 100) return 0
		M.WebContent -= 100
	else
		var/obj/Items/MAT
		switch(TYPE)
			if("Wood", "Bamboo") MAT = M.HasItem(/obj/Items/woods/wood/)
			if("Stone", "Ancient") MAT = M.HasItem(/obj/Items/ores/stone/)
			if("Bone") MAT = M.HasItem(/obj/Items/Bones/Bones/)
		if(!MAT) return 0
		if(M.DropItem(MAT)) del(MAT)
	LOC2.ClearTurf()
	rm_ways_ver++   // stairs made: units held for a way to another level look again at once (Attack.dm, B)
	for(var/turf/X in list(LOC1, LOC2))
		X.underlays += icon(X.icon, X.icon_state)
		X.icon = 'Stairs.dmi'
		X.Detailed = 1
	LOC1.icon_state = "[TYPE][DIR]"
	LOC2.icon_state = DIR == "Up" ? "[TYPE]Down" : "[TYPE]Up"
	M.z = LEVEL
	return 1

// Modes placed with one click (stairs, tower, gate, wall stairs, ramp), not painted.
proc/RemasterClickMode(mode)
	if(RemasterIsHallMode(mode)) return 0 // dragged to size
	return copytext("[mode]", 1, 8) == "Stairs:" || copytext("[mode]", 1, 10) == "Building:" || (mode in list("Tower", "Gate", "WallStairs", "WallRamp"))

client/Click(atom/m, location, control, params)
	if(istype(mob, /Player) && RemasterClickMode(mob.Function) && !istype(m, /obj/Hud) && !istype(m, /obj/HUD) && !istype(m, /obj/RemasterAction) && !params2list(params)["right"])
		var/turf/T = RemasterTurf(m, location)
		// A click on a wall top (its walk) means the wall itself: towers, gates, stairs and
		// ramps are built on the ground.
		if(T && T.z == SKY_LAYER && T.remaster_wallwalk) T = locate(T.x, T.y, GROUND_LAYER)
		if(T)
			var/Player/P = mob
			if(copytext(P.Function, 1, 8) == "Stairs:") P.RemasterPlaceStairs(T)
			else if(copytext(P.Function, 1, 10) == "Building:") P.RemasterPlaceBuilding(T)
			else if(P.Function == "Tower") P.RemasterPlaceTower(T)
			else P.RemasterPlaceSingle(T, P.Function)
			return
	return ..()

// What a build mode really makes (RemasterBuildModeKind is only its painting shape).
proc/RemasterBuildShape(mode)
	switch(mode)
		if("Beam") return "beam"
		if("FortressWall") return "wall"
		if("WallStairs", "WallRamp") return "ramp"
		if("Gate") return "gate"
	if(RemasterRoadMode(mode)) return "road"
	if(copytext(mode, 1, 7) == "Piece:") return "piece"
	if(copytext(mode, 1, 10) == "Building:") return "building"
	return RemasterBuildModeKind(mode)

proc/RemasterWalkBeside(turf/T)
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/W = get_step(T, d)
		var/turf/WW = W ? locate(W.x, W.y, SKY_LAYER) : null
		if(WW && WW.remaster_wallwalk) return 1
	return 0

// Pieces of material one tile takes: a ramp beside a wall 3 stone, one cut into a wall none.
proc/RemasterBlueprintNeed(mode, turf/T)
	if(!RemasterBuildMaterial(mode)) return 0
	if(mode == "WallRamp") return RemasterWallStands(T) ? 0 : 3
	if(mode == "Beam") return 1
	if(mode == "Piece:pillar") return 2
	if(mode == "Piece:minecart") return 3
	var/power = RemasterPowerNeed(mode)    // Power.dm
	if(power) return power
	return 1

// Pieces of material (path, or the task's own) a task still uses up. A building's floors
// only need one in the bag (the original floors keep it), so they count as one.
Player/proc/RemasterSiteNeedCount(list/S, path)
	var/n = 0
	var/kept = 0
	var/mixed = RemasterSiteMixed(S)
	if(remaster_blueprints) for(var/list/B in remaster_blueprints) if(B["site"] == S["id"])
		// a building's floor and the piece to go on it once it is laid
		for(var/mode in B["then"] ? list(B["mode"], B["then"]) : list(B["mode"]))
			if(path && RemasterBuildMaterial(mode) != path) continue
			var/k = RemasterBlueprintNeed(mode, locate(B["x"], B["y"], B["z"]))
			if(mixed && !RemasterBuildUses(mode)) kept = max(kept, k)
			else n += k
	return n || kept

// The kinds of piece a task has left (one, unless it is a building's).
Player/proc/RemasterSiteModes(list/S)
	if(!RemasterSiteMixed(S)) return list(S["mode"])
	var/list/out = list()
	if(remaster_blueprints) for(var/list/B in remaster_blueprints) if(B["site"] == S["id"]) out |= B["mode"]
	return out

proc/RemasterSiteMixed(list/S)
	return S && copytext(S["mode"], 1, 10) == "Building:"

// May this unit work on the task: build its kind, or (a building) any piece left in it.
Player/proc/RemasterSiteEligible(list/S, mob/Monsters/M)
	if(!RemasterSiteMixed(S)) return RemasterBuildEligible(S["mode"], M)
	if(!M || M.Wagon) return 0
	for(var/mode in RemasterSiteModes(S)) if(RemasterBuildEligible(mode, M)) return 1
	return !!RemasterBuildingDigWait(S) || (S["ceil"] && length(RemasterBuildingRoofs(S)))   // anyone digs (and mines a high hall's roof), by hand if need be (Buildings.dm)

// One construction task of one tile, planned with a click.
Player/proc/RemasterPlaceSingle(turf/T, mode)
	var/blocked = RemasterBuildBlocked(T, mode)
	if(blocked)
		RemasterNotice("Can't plan [lowertext(RemasterBuildModeLabel(mode))] there: [blocked].")
		return 0
	if(!RemasterMayWork(T)) return 0
	if(!remaster_blueprints) remaster_blueprints = list()
	if(RemasterBlueprintAt(T))
		RemasterNotice("That tile is already planned.")
		return 0
	var/list/S = RemasterSiteNew(mode, T.z)
	S["x"] = T.x
	S["y"] = T.y
	S["left"] = 1
	S["total"] = 1
	S["workers"] = 1
	remaster_blueprints += list(list("x"=T.x, "y"=T.y, "z"=T.z, "mode"=mode, "note"="Waiting for a builder", "tries"=0, "site"=S["id"]))
	RemasterUndoPush(list("type"="blueprints", "keys"=list("[T.x],[T.y],[T.z]")))
	var/crew = RemasterSiteAssignUnits(S, RemasterBuilderUnits())
	Function = null
	RemasterNotice("Planned [lowertext(S["label"])]. [RemasterSiteNeedText(S)]. [crew ? crew : RmBuildCrewHint()]")
	return S

// A tower: a 3x3 block of fortress wall around the clicked tile (the walk covers its top).
Player/proc/RemasterPlaceTower(turf/C)
	if(!C) return 0
	if(!remaster_blueprints) remaster_blueprints = list()
	var/list/S = RemasterSiteNew("FortressWall", C.z)
	S["label"] = "Tower"
	var/list/undo = list()
	for(var/turf/T in block(locate(max(1, C.x - 1), max(1, C.y - 1), C.z), locate(min(world.maxx, C.x + 1), min(world.maxy, C.y + 1), C.z)))
		if(RemasterBlueprintAt(T) || RemasterBuildBlocked(T, "FortressWall") || !RemasterMayWork(T, 1)) continue
		remaster_blueprints += list(list("x"=T.x, "y"=T.y, "z"=T.z, "mode"="FortressWall", "note"="Waiting for a builder", "tries"=0, "site"=S["id"]))
		undo += "[T.x],[T.y],[T.z]"
	if(!length(undo))
		remaster_sites -= list(S)
		RemasterNotice("No room for a tower there.")
		return 0
	S["x"] = C.x
	S["y"] = C.y
	S["left"] = length(undo)
	S["total"] = length(undo)
	RemasterUndoPush(list("type"="blueprints", "keys"=undo))
	var/crew = RemasterSiteAssignUnits(S, RemasterBuilderUnits())
	Function = null
	var/merges = RemasterTowerMerges(C) ? " It touches a wall three rows thick, so it will look like part of that wall, not a tower: leave a gap or use a thinner wall." : ""
	RemasterNotice("Planned a tower ([length(undo)] tiles). [RemasterSiteNeedText(S)]. [crew ? crew : RmBuildCrewHint(1)][merges]")
	if(merges) S["note"] = "Will look like plain wall: it touches a wall three rows thick"
	return S

// The 3D view draws a tower where a 3x3 block of wall is solid and no 3x3 block one
// tile over is solid too. With the tower around C finished, would one be (built or
// planned walls)?
Player/proc/RemasterTowerMerges(turf/C)
	for(var/dx = -1, dx <= 1, dx++)
		for(var/dy = -1, dy <= 1, dy++)
			if(!dx && !dy) continue
			var/solid = 1
			for(var/x2 = C.x + dx - 1, x2 <= C.x + dx + 1 && solid, x2++)
				for(var/y2 = C.y + dy - 1, y2 <= C.y + dy + 1 && solid, y2++)
					var/turf/T = locate(x2, y2, C.z)
					if(!T) solid = 0
					else if(abs(x2 - C.x) <= 1 && abs(y2 - C.y) <= 1) continue // the tower itself
					else if(RemasterWallStands(T)) continue
					else
						var/list/B = RemasterBlueprintAt(T)
						if(!B || RemasterBuildShape(B["mode"]) != "wall") solid = 0
			if(solid) return 1
	return 0

// The original door placement (Click.dm, "Place"), with the unit standing in the gap.
Player/proc/RemasterBuildGate(mob/Monsters/M, turf/T)
	if(M.loc != T || RemasterSiegeDoor(T)) return 0
	var/obj/Items/Furniture/Doors/D = M.HasItem(/obj/Items/Furniture/Doors)
	if(!D || D.Placed) return 0
	D.loc = M.loc
	D.dir = M.dir
	D.density = 1
	M.weight -= D.weight
	D.Placed = 1
	D.opacity = 1
	D.Door = 1
	D.Locked = 0
	D.LockVar = rand(1, 10000)
	D.Owner = M.Owner
	D.Death()
	for(var/d in list(NORTH, SOUTH, EAST, WEST)) if(RemasterWallStands(get_step(T, d))) RemasterWallWalkCheck(get_step(T, d))
	return 1

// Wall stairs and ramps (WallWalks.dm) as if this unit alone were selected beside the tile.
Player/proc/RemasterBuildWallPiece(mob/Monsters/M, turf/T, mode)
	var/list/old = Selected
	var/note = remaster_notice
	Selected = list(M)
	usr = src
	var/ok = 0
	try
		ok = mode == "WallStairs" ? RemasterWallStairs(T) : RemasterWallRamp(T)
	catch(var/exception/E)
		world.log << "Remastered: wall piece failed at [T.x],[T.y]: [E]"
	Selected = old
	if(!ok) remaster_notice = note // the task shows why; keep the player's message
	return ok

// --- What tasks need ------------------------------------------------------------
Player/proc/RemasterStoreCount(path, level)
	var/n = 0
	var/list/counted = list()
	for(var/turf/T in RemasterStores())
		if(T.z != level) continue
		for(var/obj/Items/I in range(1, T)) if(isturf(I.loc) && istype(I, path) && !counted[I] && RemasterMayCollect(I))
			counted[I] = 1
			n++
	return n

Player/proc/RemasterLooseCount(path, turf/C)
	if(!C) return 0
	var/list/stores = list()
	for(var/turf/T in RemasterStores()) if(T.z == C.z) stores += T
	var/n = 0
	for(var/obj/Items/I in range(12, C))
		if(!isturf(I.loc) || !istype(I, path) || !RemasterMayCollect(I)) continue
		var/on_store = 0
		for(var/turf/T in stores) if(get_dist(T, I) <= 1) on_store = 1
		if(!on_store) n++
	return n

// What each open task still needs, sharing the stockpiles out in task order
// (priority, then oldest): site id -> list("mat","need","carried","stock","nearby","missing").
Player/proc/RemasterSiteNeeds()
	var/list/out = list()
	var/list/stock = list()
	for(var/list/S in RemasterOpenSites())
		if(RemasterSiteMixed(S))
			out[S["id"]] = RemasterBuildingNeeds(S, stock)
			continue
		var/path = RemasterBuildMaterial(S["mode"])
		var/list/N = list("mat"=null, "need"=0, "carried"=0, "stock"=0, "nearby"=0, "missing"=0, "uses"=RemasterBuildUses(S["mode"]))
		out[S["id"]] = N
		if(path && !RemasterSiteNeedCount(S))
			N["body"] = "Needs no material (the wall's own stone)"
			continue
		if(!path)
			var/list/E = RemasterBuildEntryForMode(S["mode"])
			if(E && E["mat"] == "web") N["body"] = "Spun from the spider's own web"
			else if(E && E["mat"] == "flesh") N["body"] = "Made from the Devourer's stored flesh"
			else if(S["mode"] == "DigChannel") N["body"] = "Needs a spade, no material"
			else N["body"] = "Needs no material"
			continue
		N["mat"] = RemasterMaterialKind(path)
		var/key = "[path]|[S["z"]]"
		if(isnull(stock[key])) stock[key] = RemasterStoreCount(path, S["z"])
		var/need = N["uses"] ? RemasterSiteNeedCount(S) : (S["left"] ? 1 : 0)
		var/carried = 0
		for(var/mob/Monsters/M in RemasterSiteCrew(S["id"])) carried += M.RemasterCarriedCount(path)
		carried = min(carried, need)
		var/from_stock = min(need - carried, stock[key])
		stock[key] -= from_stock
		var/nearby = 0
		if(need - carried - from_stock > 0) nearby = min(need - carried - from_stock, RemasterLooseCount(path, locate(S["x"], S["y"], S["z"])))
		N["need"] = need
		N["carried"] = carried
		N["stock"] = from_stock
		N["nearby"] = nearby
		N["missing"] = max(0, need - carried - from_stock - nearby)
	return out

Player/proc/RemasterNeedText(list/N)
	if(!N) return ""
	if(N["parts"])
		var/list/lines = list()
		for(var/list/X in N["parts"]) lines += RemasterNeedText(X)
		return length(lines) ? jointext(lines, "; ") : "Needs no material"
	if(!N["mat"]) return N["body"] || "Needs no material"
	var/mat = N["mat"]
	if(!N["uses"]) return "Needs 1 [mat] in the builder's bag (floors don't use it up)"
	if(N["need"] > 1 && (mat in list("door", "bed", "table", "chair"))) mat += "s"
	var/list/parts = list()
	if(N["carried"]) parts += "[N["carried"]] carried"
	if(N["stock"]) parts += "[N["stock"]] in stockpiles"
	if(N["nearby"]) parts += "[N["nearby"]] lying nearby"
	if(N["missing"]) parts += "[N["missing"]] missing"
	if(!length(parts)) return "[N["need"]] [mat]"
	return "[N["need"]] [mat]: [jointext(parts, ", ")]"

Player/proc/RemasterSiteNeedText(list/S)
	return RemasterNeedText(RemasterSiteNeeds()[S["id"]])

// --- The Build tab -----------------------------------------------------------------
Player/var/tmp/list/remaster_build_icons
Player/proc/RemasterBuildIcon(list/E)
	if(!client || !E["icon"]) return ""
	if(!remaster_build_icons) remaster_build_icons = list()
	var/name = "rmb-[E["id"]].png"
	if(!remaster_build_icons[name])
		remaster_build_icons[name] = 1
		src << browse_rsc(icon(E["icon"], E["state"], SOUTH, 1), name)
	return name

Player/proc/RemasterBuildCost(list/E)
	switch(E["id"])
		if("fortress_wall") return "1 stone per tile"
		if("tower") return "9 stone"
		if("gate") return "a door"
		if("wall_stairs") return "1 stone"
		if("wall_ramp") return "3 stone, or free cut into a wall"
		if("beam") return "1 wood each, one every 9 tiles"
	if(E["building"]) return RemasterBuildingCost(E)
	if(E["piececost"]) return E["piececost"]
	switch(E["mat"])
		if("web") return E["mode"] == "Stairs:Spider" ? "100 web" : "25 web per tile"
		if("flesh") return E["mode"] == "PlaceDevourerWall" ? "stored flesh per tile" : "a stored body (kept)"
		if(null) return E["mode"] == "DigChannel" ? "a spade" : "free"
	var/mat = E["mat"] == "gem" ? "gem" : E["mat"]
	if(!E["per"]) return "1 [mat] in the bag (kept)"
	if(E["cat"] in list("walls", "bridges", "traps", "roads")) return "1 [mat] per tile"
	return "1 [mat]"

// Building rework L9 (planning/BUILDING_REWORK_PLAN_2026-10-27.md step 6): the Build tab is Place. A race whose first house
// is a block preset (FirstHouse.dm rm_first_house_def) builds its walls, towers and houses as blocks in Plan mode now,
// so Place no longer offers it the old walls, towers, its own building or the halls; the dig marks go for everyone
// (Plan's Dig marks blocks). The entries stay in the catalog (old saves' blueprints and sites use them); every other race
// keeps its walls and buildings as they were (bone, silk, flesh and secret walls, the den and warren, the lairs).
var/list/rm_place_legacy = list("fortress_wall", "tower", "wood_wall", "stone_wall", "tribal_wall", "elf_wall",
	"human_house", "dwarf_hall", "elf_lodge", "orc_lodge", "goblin_warren", "tribal_hut",
	"hall_dwarf", "hall_human", "hall_elf", "hall_orc", "hall_goblin", "hall_tribal")
var/list/rm_place_gone = list("autodig", "autodig_remove")
proc/RmPlaceLegacy(id, mob/Monsters/M)
	if(id in rm_place_gone) return 1
	if(!(id in rm_place_legacy) || !M || !rm_first_house_def[M.Race]) return 0
	return !(id == "stone_wall" && (M.SandWorker || M.Race == "Illithid"))   // crystal and sand walls stay

Player/proc/RemasterBuildCatalogData()
	var/list/races = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0 && !M.Wagon && !M.Critter)
		var/k = "[M.Race]|[M.SubRace]|[M.SandWorker]|[M.UsesPoison]"
		if(!races[k]) races[k] = M
	var/list/out = list()
	for(var/list/E in RemasterBuildCatalog())
		var/list/can = list()
		for(var/k in races)
			var/mob/Monsters/M = races[k]
			if(RemasterBuildRaceOK(E["id"], M) && !RmPlaceLegacy(E["id"], M)) can |= RemasterRacePlural(M.Race)
		if(!length(can)) continue // only what your races can build
		out += list(list("id"=E["id"], "label"=E["label"], "cat"=E["cat"], "cost"=RemasterBuildCost(E), "icon"=RemasterBuildIcon(E),
			"who"=jointext(can, ", "), "info"=E["who"], "shop"=E["shop"], "stairs"=(E["cat"] == "stairs"), "now"=E["now"],
			"grid"=(E["building"] ? RemasterBuildingGrid(E["building"]) : null), "drag"=RemasterIsHallMode(E["mode"])))
	return out

Player/proc/RemasterConstructionData(full)
	var/list/needs = RemasterSiteNeeds()
	var/list/open = list()
	var/list/done = list()
	var/waiting = 0
	if(remaster_sites) for(var/list/S in remaster_sites)
		var/list/E = RemasterBuildEntryForMode(S["mode"])
		var/list/D = list("id"=S["id"], "label"=S["label"], "cat"=(E ? E["cat"] : null), "icon"=(E && full ? RemasterBuildIcon(E) : ""),
			"total"=S["total"], "built"=S["built"], "left"=S["left"], "failed"=S["failed"], "workers"=S["workers"], "priority"=S["priority"],
			"note"=S["note"], "x"=S["x"], "y"=S["y"], "z"=S["z"], "posted"=S["posted"], "done"=S["done"])
		if(S["done"])
			done += list(D)
			continue
		var/list/crew = list()
		for(var/mob/Monsters/M in RemasterSiteCrew(S["id"]))
			var/path = RemasterBuildMaterial(S["mode"])
			var/carry = RemasterSiteMixed(S) ? length(M.RemasterSiteLeftovers()) : M.RemasterCarriedCount(path)
			crew += list(list("ref"=RemasterUIRef(M), "name"="[M.RemasterBareName()]", "race"="[M.Race]", "status"=M.remaster_work_status, "carry"=carry, "job"=M.remaster_job))
		var/list/N = needs[S["id"]]
		D["crew"] = crew
		D["need"] = RemasterNeedText(N)
		D["missing"] = N ? N["missing"] : 0
		D["mat"] = N ? N["mat"] : null
		var/standby = 0
		for(var/mob/Monsters/M in RemasterSiteCrew(S["id"])) if(M.remaster_site_standby) standby++
		D["state"] = !length(crew) ? "unassigned" : (standby == length(crew) ? "waiting" : "working")
		if(D["state"] == "waiting") waiting++
		open += list(D)
	var/builders = 0
	var/free = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_job == "builder")
		builders++
		if(!M.remaster_site) free++
	var/list/data = list("sites"=open, "done"=done, "builders"=builders, "freeBuilders"=free, "waiting"=waiting,
		"selected"=length(RemasterBuilderUnits()), "stockpile"=!!RemasterStockpile())
	var/list/E = RemasterBuildEntryForMode(Function)
	if(E) data["mode"] = E["id"]
	data["rot"] = remaster_build_rot
	data["facing"] = RemasterBuildingFacing(remaster_build_rot)
	data["ceil"] = remaster_hall_ceil
	if(full) data["catalog"] = RemasterBuildCatalogData()
	var/list/sw = RmStoneWood()   // the Place list's Structure says what the stores hold (PlanPieces.dm)
	data["stone"] = sw[1]
	data["wood"] = sw[2]
	return data

Player/proc/RemasterConstructionCommand(action, value)
	var/list/parts = splittext("[value]", "|")
	if(!length(parts)) return 0
	switch(action)
		if("buildpick")
			var/list/E = RemasterBuildEntry(parts[1])
			if(!E || E["shop"]) return 0 // workshops are placed with the page's ghost (placeworkshop)
			var/ok = 0
			for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0 && RemasterBuildRaceOK(E["id"], M)) ok = 1
			if(!ok)
				RemasterNotice("None of your units can build [lowertext(E["label"])].")
				return 0
			RemasterCancelPlacement()
			if(E["cat"] == "stairs")
				var/dir = parts.len >= 2 ? parts[2] : "Up"
				if(!(dir in list("Up", "Down"))) return 0
				Function = "[E["mode"]]:[dir]"
				RemasterNotice("[E["label"]] going [lowertext(dir)]: click the tile for them. A builder stands there to build them.")
			else if(E["building"] && RemasterIsHallMode(E["mode"]))
				Function = E["mode"]
				RemasterNotice("[E["label"]]: drag its size on the ground or into a mountain ([RemasterBuildCost(E)]). The door goes where it meets open ground or a tunnel. Esc stops.")
			else if(E["building"])
				Function = E["mode"]
				RemasterNotice("[E["label"]]: click where its middle goes ([RemasterBuildCost(E)]). Rotate turns it; Esc stops.")
			else if(RemasterClickMode(E["mode"]))
				Function = E["mode"]
				RemasterNotice("[E["label"]]: click the tile for it. [E["who"]].")
			else
				Function = E["mode"]
				RemasterNotice(E["now"] ? "[E["label"]]: select the units, then click or drag over the tiles." : "[E["label"]]: click or drag on the ground to plan it ([RemasterBuildCost(E)]). Esc stops.")
			return 1
		if("siteassign")
			var/list/S = RemasterSite(parts[1])
			if(!S || S["done"]) return 0
			var/list/units = RemasterBuilderUnits()
			if(!length(units))
				RemasterNotice("Select the units to send first.")
				return 0
			var/text = RemasterSiteAssignUnits(S, units)
			RemasterNotice("[S["label"]]: [text]")
			return 1
		if("siteunassign")
			var/list/S = RemasterSite(parts[1])
			var/mob/Monsters/M = parts.len >= 2 ? RemasterUIUnit(parts[2]) : null
			if(!S || !istype(M) || M.Owner != src || M.remaster_site != S["id"]) return 0
			if(M.remaster_job == "builder") M.remaster_site_skip = S["id"]
			if(M.remaster_builder) M.RemasterSiteEndDuty(src)
			else M.RemasterSiteLeave(src)
			RemasterNotice("[M.name] left [lowertext(S["label"])].")
			return 1
		if("siteworkers")
			var/list/S = RemasterSite(parts[1])
			var/n = parts.len >= 2 ? round(text2num(parts[2])) : 0
			if(!S || S["done"] || n < 1 || n > 10) return 0
			S["workers"] = n
			var/list/crew = RemasterSiteCrew(S["id"])
			while(length(crew) > n)
				var/mob/Monsters/M = crew[length(crew)]
				crew.Cut(length(crew))
				if(M.remaster_job == "builder") M.remaster_site_skip = S["id"]
				if(M.remaster_builder) M.RemasterSiteEndDuty(src)
				else M.RemasterSiteLeave(src)
			return 1
		if("sitepriority")
			var/list/S = RemasterSite(parts[1])
			if(!S || parts.len < 2 || !(parts[2] in list("1", "2", "3"))) return 0
			S["priority"] = text2num(parts[2])
			return 1
		if("sitecancel")
			var/list/S = RemasterSite(parts[1])
			if(!S || S["done"]) return 0
			if(remaster_blueprints) for(var/list/B in remaster_blueprints.Copy()) if(B["site"] == S["id"]) remaster_blueprints -= list(B)
			S["left"] = 0
			RemasterSiteFinish(S, "Cancelled")
			RemasterNotice("Cancelled [lowertext(S["label"])]. Its workers take any leftovers back.")
			return 1
		if("sitegoto")
			var/list/S = RemasterSite(parts[1])
			if(!S) return 0
			var/turf/T = locate(S["x"], S["y"], S["z"])
			if(T) loc = T
			return 1
		if("siteclear")
			if(remaster_sites) for(var/list/S in remaster_sites.Copy()) if(S["done"]) remaster_sites -= list(S)
			return 1
		if("buildceil")
			remaster_hall_ceil = remaster_hall_ceil >= 6 ? 2 : remaster_hall_ceil + 1
			RemasterNotice(remaster_hall_ceil > 2 ? "Halls: a ceiling [remaster_hall_ceil] high. Inside a mountain the builders mine the roof up to it once the hall is built." : "Halls: the ceiling as dug (2 high).")
			return 1
		if("buildrotate")
			remaster_build_rot = (remaster_build_rot + 1) % 4
			var/list/E = RemasterBuildEntryForMode(Function)
			if(E && E["building"]) RemasterNotice("[E["label"]]: the door now faces [RemasterBuildingFacing(remaster_build_rot)].")
			return 1
	return 0

mob/Monsters/var/tmp/remaster_site_skip   // a Builder taken off this task doesn't take it again

// --- Ghosts on the 2D map ------------------------------------------------------------
// Each planned tile shows the piece it will become, faint and blue, to its owner only.
Player/var/tmp/list/remaster_ghosts
Player/var/tmp/remaster_ghost_key
Player/proc/RemasterGhostsTick()
	if(!client) return
	var/list/keys = list()
	if(remaster_blueprints) for(var/list/B in remaster_blueprints) keys += "[B["x"]],[B["y"]],[B["z"]],[B["mode"]]"
	var/key = jointext(keys, ";")
	if(key == remaster_ghost_key) return
	remaster_ghost_key = key
	if(remaster_ghosts) for(var/image/I in remaster_ghosts) client.images -= I
	remaster_ghosts = list()
	if(remaster_blueprints) for(var/list/B in remaster_blueprints)
		var/turf/T = locate(B["x"], B["y"], B["z"])
		if(!T) continue
		var/list/E = RemasterBuildEntryForMode(B["mode"])
		var/image/I = image(E ? E["icon"] : 'Cave.dmi', T, E ? E["state"] : "WorkShopLeft", TURF_LAYER + 0.5)
		I.alpha = 110
		I.color = "#9fc6ff"
		client.images += I
		remaster_ghosts += I
