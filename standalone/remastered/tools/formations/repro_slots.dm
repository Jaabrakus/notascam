// Native against DM (python3 tools/formations/repro_select.py tools/formations/repro_slots.dm --engine main [--dll D]):
// a group move's open tiles, rm_slot_reach (engine/native/RmSlots.cs) and RemasterSlotReachDM (Formations.dm), on
// scenes with walls, trees, units of the group's own side (gone through), enemies (in the way) and wall-walk tiles (two
// to a tile), for many targets and reaches: the tiles in the same order and the same free places, or it says where not.
world
	maxx = 90
	maxy = 90
	maxz = 3
	turf = /turf/grounds/grass
	fps = 10

proc/ReproSame(list/A, list/B)       // the same keys in the same order, the same values
	if(length(A) != length(B)) return 0
	for(var/i = 1, i <= length(A), i++)
		var/a = A[i]
		var/b = B[i]
		if(a != b || A[a] != B[b]) return 0
	return 1

proc/ReproRun()
	sleep(10)
	remaster_fog = 0
	world.log << "REPRO|native|version=[rm_native_version()]|slots=[rm_native_slots]"
	var/Player/P = new(locate(2, 2, 1))
	var/Player/Q = new(locate(3, 2, 1))
	usr = P
	// the scene: walls and trees here and there, a wall-walk strip, a few of the other player's units, a few of ours
	for(var/x = 5, x <= 85, x++) for(var/y = 5, y <= 85, y++)
		var/turf/T = locate(x, y, 1)
		var/h = (x * 73 + y * 151 + x * y * 7) % 100
		if(h < 9)
			T.density = 1
			T.name = "wall"
		else if(h < 12)
			T.density = 1
			T.Tree = 1
			T.name = "tree"
		else if(x >= 40 && x <= 44 && y == 50) T.remaster_wallwalk = 1
	var/list/G = list()
	for(var/i = 0, i < 30, i++)
		var/turf/S = locate(30 + i % 6, 30 + round(i / 6), 1)
		if(S.density) continue
		var/mob/Monsters/M = new /mob/Monsters/Human(S)
		M.ChangeOwnership(P)
		if(!(M in P.UnitList)) P.UnitList += M
		G += M
	for(var/i = 0, i < 12, i++)
		var/turf/S = locate(45 + i * 2, 47 + (i % 3), 1)
		if(S.density) continue
		var/mob/Monsters/E = new /mob/Monsters/Goblin(S)
		E.ChangeOwnership(Q)
	for(var/i = 0, i < 8, i++)
		var/turf/S = locate(50 + i, 40, 1)
		if(S.density) continue
		var/mob/Monsters/F = new /mob/Monsters/Dwarf(S)
		F.ChangeOwnership(P)      // ours, not in the group: gone through, but not a free place
		if(!(F in P.UnitList)) P.UnitList += F
	var/mob/Monsters/lead = G[1]
	var/list/pass = list()
	for(var/mob/Monsters/M in G) pass[M] = 1
	var/cases = 0
	var/differ = 0
	var/tiles = 0
	for(var/tx = 20, tx <= 70, tx += 5) for(var/ty = 20, ty <= 70, ty += 5)
		var/turf/T = locate(tx, ty, 1)
		var/turf/seed = T
		if(T.density) for(var/turf/C in range(2, T)) if(!C.density)
			seed = C
			break
		if(seed.density) continue
		for(var/R in list(4, 9, 14))
			rm_path_pass = pass
			var/list/N = rm_slot_reach(T, R, seed, lead, G, pass, 'Stairs.dmi', /obj/RmBeastFoot, /mob/Monsters, GROUND_LAYER, SKY_LAYER, RmSide(lead), /mob/Monsters/RemasterSiege)
			var/list/D = RemasterSlotReachDM(T, R, seed, lead, G, 0)
			rm_path_pass = null
			cases++
			if(!islist(N))
				differ++
				if(differ <= 5) world.log << "REPRO|differ|[tx],[ty] R=[R]|native gave nothing"
				continue
			tiles += length(D[1])
			if(!ReproSame(N[1], D[1]) || !ReproSame(N[2], D[2]))
				differ++
				if(differ <= 5) world.log << "REPRO|differ|[tx],[ty] R=[R]|reach [length(N[1])] vs [length(D[1])]|places [length(N[2])] vs [length(D[2])]"
	world.log << "REPRO|equiv|cases=[cases]|tiles=[tiles]|differ=[differ]"
	// the slot tiles: points round each target in a block, a line and a long column, with some walls, the free places
	// taken as they go (each side on its own copy)
	var/tcases = 0
	var/tdiff = 0
	for(var/tx = 25, tx <= 65, tx += 10) for(var/ty = 25, ty <= 65, ty += 10)
		var/turf/T = locate(tx, ty, 1)
		var/turf/seed = T
		if(T.density) for(var/turf/C in range(2, T)) if(!C.density)
			seed = C
			break
		if(seed.density) continue
		rm_path_pass = pass
		var/list/D0 = RemasterSlotReachDM(T, 14, seed, lead, G, 0)
		rm_path_pass = null
		for(var/sh in list("box", "line", "column"))
			for(var/n in list(12, 40, 120))
				var/list/pts = list()
				for(var/list/q in RemasterShapePoints(sh, n, tx, ty, 0.6, 0.8)) pts += list(list(q[1], q[2], null))
				var/list/ok = list()
				for(var/list/q in pts) ok += max(abs(q[1] - tx), abs(q[2] - ty))
				RmSortByDM(pts, ok)
				var/list/P0 = D0[2]
				var/list/PN = P0.Copy()
				var/list/PD = P0.Copy()
				var/list/A = rm_slot_tiles(pts, 0, 1, tx, ty, 1, PN)
				var/list/B = RemasterSlotTilesDM(pts, 0, 1, tx, ty, 1, PD)
				tcases++
				var/same = islist(A) && length(A[1]) == length(B[1]) && ReproSame(PN, PD)
				if(same)
					var/list/AT = A[1]
					var/list/BT = B[1]
					for(var/i = 1, i <= length(BT), i++) if(AT[i] != BT[i]) same = 0
				if(!same)
					tdiff++
					if(tdiff <= 5) world.log << "REPRO|tdiffer|[tx],[ty] [sh] [n]|tiles [islist(A) ? length(A[1]) : "none"] vs [length(B[1])]"
	world.log << "REPRO|tiles_equiv|cases=[tcases]|differ=[tdiff]"
	// the sort: keys with many ties, two keys, against the DM merge sort
	var/scases = 0
	var/sdiff = 0
	for(var/k = 1, k <= 60, k++)
		var/list/L = list()
		var/list/K1 = list()
		var/list/K2 = list()
		for(var/i = 1, i <= 5 + k * 3, i++)
			L += "item[i]"
			K1 += ((i * 37 + k * 11) % 7) - 3
			K2 += (((i * 53 + k) % 5) - 2) * 0.5
		var/list/LN = L.Copy()
		var/list/LD = L.Copy()
		rm_sort_by(LN, K1.Copy(), k % 2 ? K2.Copy() : null)
		RmSortByDM(LD, K1.Copy(), k % 2 ? K2.Copy() : null)
		scases++
		for(var/i = 1, i <= length(LD), i++) if(LN[i] != LD[i])
			sdiff++
			break
	world.log << "REPRO|sort_equiv|cases=[scases]|differ=[sdiff]"
	// how long each takes, the same 200 times over
	var/t0 = world.tick_usage
	for(var/k = 1, k <= 100, k++)
		rm_path_pass = pass
		rm_slot_reach(locate(40, 40, 1), 14, locate(40, 40, 1), lead, G, pass, 'Stairs.dmi', /obj/RmBeastFoot, /mob/Monsters, GROUND_LAYER, SKY_LAYER, RmSide(lead), /mob/Monsters/RemasterSiege)
	var/t1 = world.tick_usage
	for(var/k = 1, k <= 100, k++)
		RemasterSlotReachDM(locate(40, 40, 1), 14, locate(40, 40, 1), lead, G, 0)
	var/t2 = world.tick_usage
	rm_path_pass = null
	world.log << "REPRO|speed|native_ms=[round((t1 - t0) * world.tick_lag / 100, 0.01)]|dm_ms=[round((t2 - t1) * world.tick_lag / 100, 0.01)]"
	world.log << "REPRO|done"
