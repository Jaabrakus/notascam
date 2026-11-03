// Regions on disk, step R3 (planning/REGIONS_ON_DISK_PLAN_2026-10-31.md; the owner, 10-31: "Yes, start R3"): the world
// save written as a file a region and a small world file, so a save writes only the regions that changed and a start
// can read only the regions near players (R2, when far regions unload). On today's map a region is a 256x256 block of
// one layer (rm_region_size); the generated world's hexes take its place (R4).
// - A region's file, units/regions/r<z>_<rx>_<ry>.<save>.sav: its changed tiles, the things on them (items, workshops,
//   siege engines, banners, runes, as WorldSave.dm records them), the quests posted on its boards (by Q["region"]), when
//   it was saved ("asleep since", for R2's catch-up) and a fingerprint of what it holds. A region that holds nothing
//   has no file.
// - The world file, units/regions/world.<save>.sav: the save's number and stamp, each region's file, the calendar,
//   realms, wars, quests' own numbers and order and the rest of WorldSave.dm's world-wide values (RemasterWorldGlobals).
// - A save writes a region's file only when its fingerprint moved; the others keep theirs. Every file has a name of its
//   own, written once: the engine keeps a file's contents by its path, so a name used again in a run came back as its
//   first contents (the single world save lost every save after a run's first that way, 10-31). Each is written as the
//   unit saves are (rm_later: by the engine, off the game thread, temp file + replace). A start reads the newest world
//   file; one that names a region file not there isn't used. Files neither it nor the save before name are let go.
// - For now the single file (units/remaster_world.sav) is still written beside them, with the same stamp: a start reads
//   the region files only when their world file is complete and carries the stamp of the last single file
//   (RM_WORLD_STAMP, WorldSave.dm), else the single file as before. An old save loads as before and is written as region
//   files by the next save. RM_REGION_FILES=0 in the server's environment: no region files, written or read.
#define RM_REGIONS_DIR "units/regions/"

var/rm_region_size = 256           // tiles a side of a region on today's map (tests set it smaller)
var/rm_region_files_on = -1        // -1: not looked at yet (RmRegionFilesOn)
var/rm_region_save_no = 0          // the last region save's number (from the world file at load)
var/list/rm_region_sig = list()    // region id -> the fingerprint of what its file holds
var/list/rm_region_file = list()   // region id -> its file
var/list/rm_region_prev = list()   // the save before's table (its files are kept: that set stays whole)
var/rm_region_prev_world           // the save before's world file
var/list/rm_region_stats = list()  // the last save: "written", "kept", "regions", "save", "ms" (tests, the devlog)

proc/RmRegionFilesOn()
	if(rm_region_files_on < 0) rm_region_files_on = world.GetConfig("env", "RM_REGION_FILES") != "0"
	return rm_region_files_on

proc/RmRegionId(x, y, z)
	return "[z]_[round((x - 1) / rm_region_size)]_[round((y - 1) / rm_region_size)]"

// A record into its region's lists (made on first use); a quest goes in as list(id, quest).
proc/RmRegionPut(list/R, x, y, z, kind, rec)
	var/id = RmRegionId(x, y, z)
	var/list/G = R[id]
	if(!G)
		G = list("turfs"=list(), "shops"=list(), "siege"=list(), "banners"=list(), "runes"=list(), "items"=list(), "quests"=list())
		R[id] = G
	var/list/L = G[kind]
	if(kind == "quests") L[rec[1]] = rec[2]
	else L += list(rec)

// The save's records (WorldSave.dm RemasterSaveWorld) as region files and a world file. Siege engines, banners and
// runes keep their place in the world's order (list(n, record)), as the quests do (the world file's "order"). Never
// stops a save: anything wrong leaves the last whole set, which a start then doesn't use (its stamp is old).
proc/RmRegionsSave(list/turfs, list/shops, list/siege, list/banners, list/runes, list/items, list/G, stamp)
	if(!RmRegionFilesOn()) return
	var/t0 = world.timeofday
	try
		var/list/R = list()
		for(var/list/T in turfs) RmRegionPut(R, T[1], T[2], T[3], "turfs", T)
		for(var/list/W in shops) RmRegionPut(R, W[2], W[3], W[4], "shops", W)
		for(var/i = 1, i <= length(siege), i++)
			var/list/E = siege[i]
			RmRegionPut(R, E[2], E[3], E[4], "siege", list(i, E))
		for(var/i = 1, i <= length(banners), i++)
			var/list/B = banners[i]
			RmRegionPut(R, B[1], B[2], B[3], "banners", list(i, B))
		for(var/i = 1, i <= length(runes), i++)
			var/list/U = runes[i]
			RmRegionPut(R, U[2], U[3], U[4], "runes", list(i, U))
		for(var/list/I in items) RmRegionPut(R, I[1], I[2], I[3], "items", I)
		// the quests by their boards' regions; the world file keeps their own numbers and their order
		var/list/WG = G.Copy()
		var/list/QD = istext(G["Quests"]) ? json_decode(G["Quests"]) : null
		if(islist(QD) && islist(QD["quests"]))
			var/list/QS = QD["quests"]
			var/list/order = list()
			for(var/id in QS)
				var/list/Q = QS[id]
				order += id
				var/list/BP = Q["board"]
				var/rid = Q["region"]
				if(!rid && islist(BP) && length(BP) >= 3) rid = RmRegionId(BP[1], BP[2], BP[3])
				if(!rid) rid = "0_0_0"
				var/list/RG = R[rid]
				if(!RG)
					RG = list("turfs"=list(), "shops"=list(), "siege"=list(), "banners"=list(), "runes"=list(), "items"=list(), "quests"=list())
					R[rid] = RG
				var/list/QL = RG["quests"]
				QL[id] = Q
			QD["quests"] = null
			QD["order"] = order
			WG["Quests"] = json_encode(QD)
		var/n = ++rm_region_save_no
		var/list/table = list()
		var/written = 0
		for(var/id in R)
			var/list/RG = R[id]
			// by place, row by row (each tile's own records in the order they came): the same region gives the same file
			// whatever order the save's scan found them in, which differs after a restart
			RG["turfs"] = RmRegionsByPlace(RG["turfs"], 1)
			RG["items"] = RmRegionsByPlace(RG["items"], 1)
			RG["shops"] = RmRegionsByPlace(RG["shops"], 2)
			RG["quests"] = length(RG["quests"]) ? json_encode(RG["quests"]) : null   // as the single file keeps them: JSON text
			var/sig = md5(json_encode(RG))
			if(sig == rm_region_sig[id] && rm_region_file[id] && fexists(rm_region_file[id]))
				table[id] = rm_region_file[id]
				continue
			var/f = "[RM_REGIONS_DIR]r[id].[n].sav"
			fdel(f)
			var/savefile/F = new(f)
			F.rm_later = 1   // written by the engine when closed (below), off the game thread
			F["version"] << 1
			F["region"] << id
			F["size"] << rm_region_size
			F["save"] << n
			F["savedAt"] << RemasterNow()   // asleep since: for the catch-up when far regions sleep (R2)
			F["sig"] << sig
			for(var/k in RG) F[k] << RG[k]
			F["complete"] << 1
			del(F)   // closed: written out, and the engine lets its contents go
			table[id] = f
			rm_region_sig[id] = sig
			rm_region_file[id] = f
			written++
		for(var/id in rm_region_file.Copy()) if(!table[id])   // a region that holds nothing now
			rm_region_file -= id
			rm_region_sig -= id
		var/wf = "[RM_REGIONS_DIR]world.[n].sav"
		fdel(wf)
		var/savefile/S = new(wf)
		S.rm_later = 1
		S["version"] << 1
		S["save"] << n
		S["stamp"] << stamp
		S["size"] << rm_region_size
		S["regions"] << table
		S["previous"] << rm_region_prev
		S["globals"] << WG
		S["complete"] << 1
		del(S)
		// files neither this set nor the one before names are let go (the one before stays whole, as a backup)
		var/list/keep = list()
		keep[wf] = 1
		if(rm_region_prev_world) keep[rm_region_prev_world] = 1
		for(var/id in table) keep[table[id]] = 1
		for(var/id in rm_region_prev) keep[rm_region_prev[id]] = 1
		for(var/f in flist(RM_REGIONS_DIR)) if((copytext(f, 1, 2) == "r" || copytext(f, 1, 7) == "world.") && !keep[RM_REGIONS_DIR + f]) fdel(RM_REGIONS_DIR + f)
		rm_region_prev = table
		rm_region_prev_world = wf
		var/ms = world.timeofday - t0
		if(ms < 0) ms += 864000
		rm_region_stats = list("written"=written, "kept"=length(table) - written, "regions"=length(table), "save"=n, "ms"=ms * 100)
	catch(var/exception/e)
		world.log << "Remastered: the region files were not written ([e]); the single world save stands"

// The last save's region files, restored as the single file would be (WorldSave.dm RemasterRestoreWorldThings and
// RemasterRestoreWorldGlobals); null when there's no whole set to read, or it isn't the last save's (the single file
// then). Every file is read before anything is restored, so a missing one leaves the single file to load.
proc/RmRegionsLoad()
	if(!RmRegionFilesOn()) return null
	var/path = RmRegionsWorldFile()
	if(!path) return null
	var/savefile/S = new(path)
	var/complete
	S["complete"] >> complete
	if(!complete) return null
	var/stamp
	S["stamp"] >> stamp
	if(fexists(REMASTER_WORLD_SAVE) || fexists(REMASTER_WORLD_SAVE + ".bak"))
		var/last = fexists(RM_WORLD_STAMP) ? replacetext(replacetext(file2text(RM_WORLD_STAMP), ascii2text(13), ""), "\n", "") : null
		if(!stamp || last != stamp) return null   // the single file was saved after this set (or by a game without them)
	var/list/table
	S["regions"] >> table
	var/list/G
	S["globals"] >> G
	var/size
	S["size"] >> size
	var/n
	S["save"] >> n
	if(!islist(table) || !islist(G)) return null
	var/list/got = list()   // region id -> its lists
	for(var/id in table)
		var/f = table[id]
		if(!fexists(f)) return null
		var/savefile/F = new(f)
		var/c
		F["complete"] >> c
		if(!c) return null
		var/list/RG = list()
		for(var/k in list("turfs", "shops", "siege", "banners", "runes", "items", "quests", "sig"))
			var/v
			F[k] >> v
			RG[k] = v
		got[id] = RG
	var/list/turfs = list()
	var/list/shops = list()
	var/list/items = list()
	var/list/SE = list()
	var/list/BN = list()
	var/list/RN = list()
	var/list/QS = list()
	for(var/id in got)
		var/list/RG = got[id]
		if(islist(RG["turfs"])) turfs += RG["turfs"]
		if(islist(RG["shops"])) shops += RG["shops"]
		if(islist(RG["items"])) items += RG["items"]
		RmRegionsPlace(SE, RG["siege"])
		RmRegionsPlace(BN, RG["banners"])
		RmRegionsPlace(RN, RG["runes"])
		if(istext(RG["quests"]))
			var/list/Q = json_decode(RG["quests"])
			if(islist(Q)) for(var/qid in Q) QS[qid] = Q[qid]
	var/list/QD = istext(G["Quests"]) ? json_decode(G["Quests"]) : null
	if(islist(QD))
		var/list/inorder = list()
		if(islist(QD["order"])) for(var/qid in QD["order"]) if(QS[qid]) inorder[qid] = QS[qid]
		for(var/qid in QS) if(!inorder[qid]) inorder[qid] = QS[qid]
		QD["quests"] = inorder
		QD -= "order"
		G["Quests"] = QD
	// kept for the next save: a region whose fingerprint stands keeps its file
	if(isnum(size) && size > 0) rm_region_size = size
	if(isnum(n)) rm_region_save_no = max(rm_region_save_no, n)
	rm_region_prev_world = path
	for(var/id in got)
		rm_region_file[id] = table[id]
		rm_region_sig[id] = got[id]["sig"]
	rm_region_prev = table
	var/list/R = RemasterRestoreWorldThings(turfs, shops, RmRegionsCompact(SE), RmRegionsCompact(BN), RmRegionsCompact(RN), items)
	world.log << "Remastered: the world save read from [length(got)] region files"
	return RemasterRestoreWorldGlobals(G, R[1], R[2])

// list(n, record) entries into their places in L (the world's order when saved).
proc/RmRegionsPlace(list/L, list/E)
	if(!islist(E)) return
	for(var/list/P in E)
		if(length(P) < 2 || !isnum(P[1]) || P[1] < 1) continue
		if(length(L) < P[1]) L.len = P[1]
		L[P[1]] = P[2]

proc/RmRegionsCompact(list/L)
	. = list()
	for(var/X in L) if(islist(X)) . += list(X)

// Records by their place, row by row and along each row (xi: where x is in a record, y after it), keeping the order of
// records on one tile. Rows are found by their y; a row's few records are put in order by x.
proc/RmRegionsByPlace(list/L, xi)
	if(length(L) < 2) return L
	var/list/rows = list()
	var/y0
	var/y1
	for(var/list/E in L)
		var/y = E[xi + 1]
		var/list/row = rows["[y]"]
		if(!row)
			row = list()
			rows["[y]"] = row
			if(isnull(y0) || y < y0) y0 = y
			if(isnull(y1) || y > y1) y1 = y
		row += list(E)
	. = list()
	for(var/y = y0, y <= y1, y++)
		var/list/row = rows["[y]"]
		if(!row) continue
		for(var/i = 2, i <= length(row), i++)   // in order by x, the equal ones as they came
			var/list/E = row[i]
			var/j = i - 1
			while(j >= 1 && row[j][xi] > E[xi])
				row[j + 1] = row[j]
				j--
			row[j + 1] = E
		. += row

// The newest world file (the highest save number), or null.
proc/RmRegionsWorldFile()
	var/best = 0
	for(var/f in flist(RM_REGIONS_DIR)) if(copytext(f, 1, 7) == "world.")
		var/list/P = splittext(f, ".")
		var/k = length(P) == 3 ? text2num(P[2]) : null
		if(isnum(k) && k > best) best = k
	return best ? "[RM_REGIONS_DIR]world.[best].sav" : null

