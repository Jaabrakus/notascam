// Building rework L8 (planning/BUILDING_REWORK_PLAN_2026-10-27.md step 5; the owner, 10-29: "make building buildings be
// block based or construction like"): a new village's first house or lodge is placed by the game, as blocks. Right after
// the story card's Begin, the race's old layout (Buildings.dm) is found a spot near the first founder (rings 2-12 tiles
// out, then 24, all four turns; every wall tile able to take blocks or rock already, every tile inside open ground, the
// tile outside the door open; the door facing the founders first, then the nearest) and made into:
// - one Plan build row named after it, every wall tile 2 blocks high, in the race's material (wood: Humans, Elves, Orcs,
//   Lizardmen, Frogmen; stone: Dwarves, Goblins), the door's tile left open; the founders go on the job board (Any) and
//   start on it, and the Builders row wants 1;
// - one furnish site (Buildings.dm RemasterPlanCells, without the walls and the door): the floor, beds, table, chair,
//   workshops and traps, built while the walls rise;
// - the door: planned once the walls are up, ordered from the carpentry as doors are.
// While the walls are short of their material it posts the same "Chop wood / Mine stone for building" order a site
// does. With trees in the way (a forest start) and no clear spot, it takes the spot within 12 with the fewest trees (6
// at most), puts a wood zone over them and plans the house once they are felled. With no ground at all (water, swamp),
// one notice, and it tries again where the first founder stops (10+ tiles on, 30 s still) for 20 minutes.
// Skipped for migrants (they join a realm with buildings), rare and lair races, Kobolds and Ratmen (bone walls: no
// blocks for them yet), and test runs (unless rm_first_house_test). The Orc war lodge is one row shorter than its Build
// tab layout (36 tiles inside, not 45; still 8 beds and the fire).
// Off since 11-01 (the owner, after its builder stayed on the house: "No first house"): new villages start with nothing
// planned and lay out their own buildings in Plan mode. A first house planned before stays the realm's own plan.
// RM_FIRST_HOUSE=1 in the server's environment (or rm_first_house_on = 1) turns it back on; RM_FIRST_HOUSE=0 keeps it off.
var/rm_first_house_on = 0
var/rm_first_house_test = 0
var/list/rm_first_house_def = list("Human"="human_house", "Dwarf"="dwarf_hall", "Elf"="elf_lodge", "Orc"="orc_lodge",
	"Goblin"="goblin_warren", "Lizardman"="tribal_hut", "Frogman"="tribal_hut")
var/list/rm_first_house_wood = list("Human", "Elf", "Orc", "Lizardman", "Frogman")
var/list/rm_first_house_rows = list("orc_lodge" = list("###########", "#B,B,,,B,B#", "#,,,,f,,,,#", "#,,,,,,,,,#", "#B,B,,,B,B#", "#####D#####"))
#define RM_FH_H 2               // wall blocks high
#define RM_FH_EVERY 300         // ticks between its looks (30 s)
#define RM_FH_GIVE_UP 12000     // 20 minutes

Player/var/list/rm_fh                 // the first house (saved with the player): list("def", "state", ...)
Player/var/tmp/rm_fh_next = 0
Player/var/tmp/rm_fh_skip = 0         // a migrant company

// The layout (a copy, with its own rows where the preset differs) and its id.
proc/RmFhDef(id)
	var/list/D = RemasterBuildingDef(id)
	if(!D) return null
	D = D.Copy()
	D["id"] = id
	if(rm_first_house_rows[id]) D["rows"] = rm_first_house_rows[id]
	return D

Player/proc/RmFhFounder()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && isturf(M.loc) && M.z == GROUND_LAYER && M.HP > 0) return M

proc/RmFhWet(turf/T)
	return T.Content3 == "Liquid" || T.Content3 == "Lava" || findtext("[T.icon_state]", "Lava") || istype(T, /turf/grounds/waters)

// The spot's cells and what they cost: list(cells, trees, door turf, the tile outside the door) or null when it can't go
// there (trees counted, not refused: trees_ok says how many may be in the way).
Player/proc/RmFhFit(list/D, turf/C, rot, trees_ok)
	var/list/cells = RemasterBuildingCells(D, rot, C)
	if(!cells) return null
	var/trees = 0
	var/turf/door
	var/list/foot = list()
	for(var/list/X in cells)
		var/turf/T = X[1]
		foot[T] = 1
		if(T.z != GROUND_LAYER || !RemasterMayWork(T, 1) || RemasterBlueprintAt(T) || RmFhWet(T)) return null
		if(T.Tree)
			if(++trees > trees_ok) return null
			continue
		if(X[2] == "#")
			if(!T.density && !RmPlanGroundOK(T, src)) return null    // rock where a wall goes is the wall
			continue
		if(T.density) return null
		for(var/atom/movable/A in T) if(A.density && !istype(A, /mob/Monsters)) return null
		if(X[2] == "D") door = T
	if(!door) return null
	var/turf/out
	for(var/d in list(SOUTH, WEST, NORTH, EAST))
		var/turf/N = get_step(door, d)
		if(N && !foot[N]) out = N
	if(!out || out.density || out.Tree || RmFhWet(out)) return null
	return list(cells, trees, door, out)

// The best spot within R of F: the nearest ring with one, the door facing F first.
Player/proc/RmFhSpot(list/D, mob/Monsters/F, R, trees_ok)
	var/list/best
	var/bs = 1#INF
	for(var/r = 2, r <= R, r++)
		for(var/dx = -r, dx <= r, dx++)
			for(var/dy = -r, dy <= r, dy++)
				if(max(abs(dx), abs(dy)) != r) continue
				var/turf/C = locate(F.x + dx, F.y + dy, F.z)
				if(!C) continue
				for(var/rot = 0, rot <= 3, rot++)
					var/list/fit = RmFhFit(D, C, rot, trees_ok)
					if(!fit) continue
					var/turf/door = fit[3]
					var/turf/out = fit[4]
					var/s = fit[2] * 100 + (get_dist(out, F) < get_dist(door, F) ? 0 : 3)
					if(s < bs)
						bs = s
						best = list(C, rot) + fit
		if(best) return best
		if(!(r % 4)) sleep(0)
	return null

// Begin pressed (Restart.dm): the first house planned, or looked for.
Player/proc/RmFirstHousePlan()
	var/env = world.GetConfig("env", "RM_FIRST_HOUSE")
	if(!(rm_first_house_on || env == "1") || env == "0" || rm_fh_skip || remaster_liege || rm_fh) return
	if(RemasterTestRun() && !rm_first_house_test) return
	var/mob/Monsters/F = RmFhFounder()
	if(!F) return
	var/id = rm_first_house_def[F.Race]
	if(!id || !RmFhDef(id)) return
	rm_fh = list("def"=id, "race"=F.Race, "state"="looking", "since"=world.time, "fx"=F.x, "fy"=F.y, "still"=world.time)
	RmFhTry(1)

// Look for its spot: planned at once, or after felling, or waiting for open ground.
Player/proc/RmFhTry(first)
	var/list/D = RmFhDef(rm_fh["def"])
	var/mob/Monsters/F = RmFhFounder()
	if(!D || !F) return
	var/list/S = RmFhSpot(D, F, 12, 0) || RmFhSpot(D, F, 24, 0)
	if(S)
		RmFhMake(D, S)
		return
	S = RmFhSpot(D, F, 12, 6)
	if(S)
		var/turf/C = S[1]
		rm_fh["state"] = "felling"
		rm_fh["x"] = C.x
		rm_fh["y"] = C.y
		rm_fh["rot"] = S[2]
		var/x0 = 1#INF
		var/y0 = 1#INF
		var/x1 = -1#INF
		var/y1 = -1#INF
		for(var/list/X in S[3])
			var/turf/T = X[1]
			if(!T.Tree) continue
			x0 = min(x0, T.x); y0 = min(y0, T.y); x1 = max(x1, T.x); y1 = max(y1, T.y)
		var/list/Z = RmJzAdd("wood", x0, y0, x1, y1, GROUND_LAYER)
		if(Z)
			Z["prio"] = 1
			Z["want"] = max(1, Z["want"])
			Z["name"] = "Clear for the [lowertext(D["label"])]"
			rm_fh["fell"] = Z["id"]
		RemasterNotice("Your [lowertext(D["label"])] goes where [S[4]] tree[S[4] == 1 ? " stands" : "s stand"]: they are being felled first.")
		RemasterLog("The [lowertext(D["label"])] waits for [S[4]] tree[S[4] == 1 ? "" : "s"] to be felled where it goes.", "work", C)
		return
	rm_fh["state"] = "waiting"
	rm_fh["fx"] = F.x
	rm_fh["fy"] = F.y
	rm_fh["still"] = world.time
	if(first || !rm_fh["said"])
		rm_fh["said"] = 1
		RemasterNotice("No open ground near for the [lowertext(D["label"])]: move your people to open ground and it will be planned where they stop.")

// The plan row, the furnish site and the founders on it.
Player/proc/RmFhMake(list/D, list/S)
	var/turf/C = S[1]
	var/rot = S[2]
	var/list/cells = S[3]
	var/turf/door = S[5]
	var/wood = rm_fh["race"] in rm_first_house_wood
	var/list/blocks = list()
	var/list/furnish = list()
	for(var/list/X in cells)
		var/turf/T = X[1]
		if(X[2] == "#")
			if(!T.density) for(var/k = 0, k < RM_FH_H, k++) blocks += "[T.x],[T.y],[k]"
		else if(X[2] != "D") furnish += list(X)
	var/list/founders = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && !M.Wagon && !M.Critter && !M.Egg && M.HP > 0) founders += M
	var/list/keep = Selected
	Selected = founders
	var/list/Z = length(blocks) ? RmPlanAdd(jointext(blocks, "/"), 2, "build", wood ? "wood" : "stone") : null
	Selected = keep
	if(Z)
		Z["name"] = D["label"]
		Z["preset"] = 1
	RmJzFixedRows()
	var/list/BR = RmJz("builders")
	if(BR) BR["want"] = max(1, BR["want"])
	var/list/site
	var/list/E = RemasterBuildEntry(D["id"])
	if(E && length(furnish))
		var/r0 = remaster_build_rot
		remaster_build_rot = rot
		site = RemasterPlanCells(E, D, furnish, C, "", "")
		remaster_build_rot = r0
	rm_fh["state"] = "planned"
	rm_fh["x"] = C.x
	rm_fh["y"] = C.y
	rm_fh["rot"] = rot
	rm_fh["plan"] = Z ? Z["id"] : null
	rm_fh["site"] = islist(site) ? site["id"] : null
	rm_fh["dx"] = door.x
	rm_fh["dy"] = door.y
	rm_fh["mat"] = wood ? "wood" : "stone"
	var/text = "Your [lowertext(D["label"])] is planned, door to the [RemasterBuildingFacing(rot)]: [length(blocks)] blocks of [wood ? "wood" : "stone"] for its walls, on the job board"
	if(islist(site)) text += ", its floor and furniture as they go up"
	RemasterNotice("[text].")
	RemasterLog("[D["label"]] planned at [C.x],[C.y]: [length(blocks)] blocks of [wood ? "wood" : "stone"].", "work", C)
	var/mob/WorkShops/Carpentry/W = locate() in range(20, C)
	if(!RemasterStockpile() || !W)
		RemasterLog("Your [lowertext(D["label"])] is planned. Set a stockpile and place a carpentry so its beds and door can be made.", "info", C)

// Every 30 s from the settlement's tick: the felling done, open ground where the founder stopped, the walls' material
// ordered, the door once the walls are up.
Player/proc/RmFirstHouseTick()
	if(!rm_fh || rm_fh["state"] == "done" || world.time < rm_fh_next) return
	rm_fh_next = world.time + RM_FH_EVERY
	var/list/D = RmFhDef(rm_fh["def"])
	if(!D) return
	switch(rm_fh["state"])
		if("felling")
			var/turf/C = locate(rm_fh["x"], rm_fh["y"], GROUND_LAYER)
			var/list/fit = C ? RmFhFit(D, C, rm_fh["rot"], 0) : null
			if(fit)
				var/list/Z = rm_fh["fell"] ? RmJz(rm_fh["fell"]) : null
				if(Z) RmJzRemove(Z)
				RmFhMake(D, list(C, rm_fh["rot"]) + fit)
			else if(!RmFhFit(D, C, rm_fh["rot"], 6))   // built over meanwhile: look again
				rm_fh["state"] = "looking"
				RmFhTry(0)
		if("waiting")
			var/mob/Monsters/F = RmFhFounder()
			if(world.time - rm_fh["since"] > RM_FH_GIVE_UP)
				rm_fh["state"] = "done"
				RemasterLog("No open ground was found for the [lowertext(D["label"])]; set its walls as blocks in Plan mode.", "info")
				return
			if(!F) return
			if(F.x != rm_fh["mx"] || F.y != rm_fh["my"])
				rm_fh["mx"] = F.x
				rm_fh["my"] = F.y
				rm_fh["still"] = world.time
				return
			if(max(abs(F.x - rm_fh["fx"]), abs(F.y - rm_fh["fy"])) >= 10 && world.time - rm_fh["still"] >= 300) RmFhTry(0)
		if("planned")
			var/list/Z = rm_fh["plan"] ? RmJz(rm_fh["plan"]) : null
			var/left = Z ? RmPlanLeft(Z) : 0
			if(left > 0)
				var/kind = rm_fh["mat"]
				var/need = left - RemasterStockCount(kind)
				if(need <= 0) return
				if(remaster_board_orders) for(var/list/O in remaster_board_orders) if(!O["done"] && O["standing"] == "build-[kind]") return
				var/list/O = RemasterBoardPost(kind, min(20, need), 1, 2, null, null, "build-[kind]")
				if(O) O["label"] = "[kind == "wood" ? "Chop wood" : "Mine stone"] for building: [O["amount"]]"
				return
			// the walls are up: the door, from the carpentry as doors are
			rm_fh["state"] = "done"
			var/turf/T = locate(rm_fh["dx"], rm_fh["dy"], GROUND_LAYER)
			var/turf/C = locate(rm_fh["x"], rm_fh["y"], GROUND_LAYER)
			var/list/E = RemasterBuildEntry(D["id"])
			if(T && C && E && !T.density)
				var/r0 = remaster_build_rot
				remaster_build_rot = rm_fh["rot"]
				RemasterPlanCells(E, D, list(list(T, "D")), C, "", "")
				remaster_build_rot = r0
			RemasterLog("The walls of your [lowertext(D["label"])] are up: its door is ordered from the carpentry.", "work", C)
