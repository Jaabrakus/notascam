// HUD unit data at 30,000 units (hud-craft, 2026-10-24; the coordinator's "overdrive" job). The page shows only a few
// units at a time: the open card, the selection, the rows in view in its lists (Company list, Units page, Village
// roster) and the units on screen. Once the page has said what it shows ("hudview", remastered.html hcView), the HUD
// model carries full entries for those only (the view set); the rest of the company goes as counts ("counts",
// "unitCount"), list windows ("lists": each list's total and the refs of the rows asked for, in order), the minimap's
// occupancy ("unitCells") and, for a big selection, its summary ("band"). Until the page asks, everything goes as before
// (tests, an old page). The background pass (counts, cells, the lists' order) runs at most every 2 s, spread like the
// jobs' census; the selection and the units on screen are looked at every send.

#define RM_VIEW_SELCAP 48        // selected units sent whole; a bigger selection also gets the band summary
#define RM_VIEW_SCREENCAP 160    // units on screen sent whole, nearest the camera first
#define RM_VIEW_ROWCAP 120       // rows one list window may ask for
#define RM_VIEW_GROUPCAP 48      // members of an open company group sent whole
#define RM_VIEW_PASS 20          // ticks between background passes (2 s)

// Sets are marks on the units, not lists: in this OpenDream adding a key to an associative list first scans the whole
// list, so a set of the company built each pass would be square in its size (5,000: ~40 ms, 28,000: over a second;
// server-cost, 10-24). A unit is in a set when its mark equals that set's serial (rm_hud_serial).
var/rm_hud_serial = 0
mob/Monsters/var/tmp/rm_hud_mark = 0        // the company (this pass) / the selection's set, by serial
mob/Monsters/var/tmp/rm_hud_gmark = 0       // members of company groups (this pass)
mob/Monsters/var/tmp/rm_hud_smark = 0       // selected (this pass)
mob/Monsters/var/tmp/rm_hud_dmark = 0       // seen once (dedupes)
mob/Monsters/var/tmp/rm_hud_umark = 0       // in its owner's UnitList when last marked (QoL.dm RemasterNormalizeSelection)
Player/var/tmp/remaster_sel_umk = 0         // that mark's serial, when it was made and the list's length then
Player/var/tmp/remaster_sel_umk_at = -1000
Player/var/tmp/remaster_sel_umk_n = -1
Player/var/tmp/remaster_realm_at = -1000    // world.time the realm was last built whole (RmHudRealm)

// "M in UnitList" without searching the list: the company marked (rm_hud_umark) at most every 2 s, and again whenever
// its length changes. Every way out of UnitList also changes the owner, kills the unit or deselects it, so callers that
// check the owner and health as well get the same answer; one that joined since has no mark and is looked for in the list.
Player/proc/RmInCompany(mob/Monsters/M)
	return M.rm_hud_umark == RmCompanyMark() || (M in UnitList)

// The command bar's "Select your own living units." over the whole selection, at most once a tick for one selection
// list: 1 when every entry is a unit of yours, in the company and alive; 2 when the units are but something else is
// selected too; 0 otherwise. RemasterSelectedReason asked it for each of several actions every send, each a search of
// the company per selected unit (select all at 30,000: 8 s a send; hud-craft, 10-24).
Player/var/tmp/list/remaster_sel_check   // list(the Selected list, its length, world.time, the answer)
Player/proc/RmSelectionCheck()
	var/list/K = remaster_sel_check
	if(K && K[1] == Selected && K[2] == length(Selected) && K[3] == world.time) return K[4]
	. = 1
	for(var/entry in Selected)
		if(!istype(entry, /mob/Monsters))
			if(. == 1) . = 2
			continue
		var/mob/Monsters/M = entry
		if(M.HP <= 0 || M.GoingToDie || M.Owner != src || !RmInCompany(M))
			. = 0
			break
	remaster_sel_check = list(Selected, length(Selected), world.time, .)

Player/proc/RmCompanyMark()
	if(!remaster_sel_umk || world.time - remaster_sel_umk_at >= 20 || length(UnitList) != remaster_sel_umk_n)
		remaster_sel_umk = ++rm_hud_serial
		remaster_sel_umk_at = world.time
		remaster_sel_umk_n = length(UnitList)
		for(var/mob/Monsters/U in UnitList) U.rm_hud_umark = remaster_sel_umk
	return remaster_sel_umk
mob/Monsters/var/tmp/list/rm_view_rec       // this unit's record for its owner's view: list(filter bits, 0, status)
Player/var/tmp/list/remaster_view             // the page's last "hudview" (decoded), or null: everything as before
Player/var/tmp/list/remaster_view_ecache      // unit -> its last entry, for list rows off screen and not selected
Player/var/tmp/list/remaster_view_owned       // the company in list order (owned, not wagons), from the pass
Player/var/tmp/list/remaster_view_rows        // the Company list's rows: the company less the members of groups
Player/var/tmp/list/remaster_view_village     // the Village roster: filtered, searched and sorted, from the pass
Player/var/tmp/remaster_view_vkey             // the filter, search and sort remaster_view_village was built for
Player/var/tmp/list/remaster_view_counts      // filter id -> how many
Player/var/tmp/remaster_view_cells            // the minimap's 48x48 cells: 0 none, 1 yours, 2 one selected
Player/var/tmp/remaster_view_pass_at = -1000  // world.time of the last pass
Player/var/tmp/remaster_view_pass_z = 0       // the level the cells were drawn for

// "hudview" from the page: {c: [first, count], u: [first, count] | null, v: {f, q, s, first, count} | null,
// g: [open group numbers]}
Player/proc/RmViewCommand(value)
	var/list/V
	try
		V = json_decode(value)
	catch(var/exception/e)
		V = null
	if(!islist(V)) return
	var/list/old = remaster_view
	remaster_view = V
	var/list/v = V["v"]
	var/key = islist(v) ? "[v["f"]]|[v["q"]]|[v["s"]]" : null
	// a new filter, search or sort (or the companies' cells on another level): the next send redoes the pass
	if(key != remaster_view_vkey || !old) remaster_view_pass_at = -1000

// a window [first, count] as asked, clamped
proc/RmViewWin(list/W, total)
	if(!islist(W) || length(W) < 2) return null
	var/first = max(0, round(text2num("[W[1]]") || 0))
	var/count = max(0, min(RM_VIEW_ROWCAP, round(text2num("[W[2]]") || 0)))
	if(first >= total) first = max(0, total - count)
	return list(first, min(count, total - first))

// The status line the page shows (remastered.html unitStatus), for the Village roster's search, sort and Idle filter
mob/Monsters/proc/RmViewStatus()
	var/order = remaster_order_status || "Idle"
	var/tame = RmTameStatus(src)
	if(tame) order = rm_bound ? tame : "[order] ([tame])"
	if(rm_moods_on)
		var/mn = RemasterMoodName()
		if(mn == "Snapped") return "Snapped - [order]"
		var/c = RemasterCombatStatus()
		if(c) return "[c]"
		if(remaster_mood < 30) return "[mn] - [remaster_care_status || order]"
	else
		var/c = RemasterCombatStatus()
		if(c) return "[c]"
	if(remaster_care_status) return "[remaster_care_status]"
	var/paused = remaster_paused || remaster_wait_for_resume || (!RemasterHasOrder() && remaster_role_paused && (remaster_job != "manual" || length(remaster_production)))
	return (paused && !findtext(order, "paused") ? "Paused - " : "") + order

// the warnings a unit's entry would list (HUD.dm RemasterUnitData), as one yes or no
mob/Monsters/proc/RmViewWarned()
	if(RmLifeFrac(src) < 0.3 || Hunger <= 20 || Tiredness <= 20 || Coldness > 0 || BloodContent < 80) return 1
	if(!HasLeftLeg || !HasRightLeg || !HasLeftArm || !HasRightArm) return 1
	if(length(RemasterAilmentWarnings()) || length(RmTameWarnings(src))) return 1
	return 0

// the Village roster's filters (remastered.html VFILTERS), by id
mob/Monsters/proc/RmViewFilter(id, status)
	switch(id)
		if("idle") return findtext(status, "idle") ? 1 : 0
		if("workers") return remaster_job && remaster_job != "manual"
		if("hurt") return HP < MAXHP * 0.6
		if("hungry") return Hunger <= max(20, MaxHunger * 0.25)
		if("tired") return Tiredness <= 25
		if("warn") return RmViewWarned()
		if("cold") return Coldness >= 40
		if("nobed") return RemasterHomeText() == "No bed"
		if("caring") return remaster_care_status ? 1 : 0
		if("ruler") return IsRoyal ? 1 : 0
	return 1

var/list/rm_view_filter_ids = list("all", "idle", "workers", "hurt", "hungry", "tired", "warn", "cold", "nobed", "caring", "ruler")

// three characters as one number (24 bits: exact in DM's 32-bit numbers), for sorting names and words
proc/RmViewKey3(t, from)
	t = lowertext("[t]")
	var/k = 0
	for(var/i = from, i < from + 3, i++)
		k = k * 256 + (i <= length(t) ? text2ascii(t, i) % 256 : 0)
	return k

// The background pass: the company in order, the Company list's rows, the counts, the minimap's cells and (when the
// roster is open) its filtered, searched and sorted order. A unit's status, filters and cell are kept as a record and
// refreshed 1,000 units a pass (all of them under 1,000 units, so exact there), the totals kept as records change: at
// 30,000 units a record is at most ~1 min old, as the jobs' census. The company's order and the selection are fresh.
Player/var/tmp/list/remaster_view_recmobs    // the units with a record, and their records (parallel: a deleted unit's
Player/var/tmp/list/remaster_view_recs       // record still comes off the totals)
Player/var/tmp/remaster_view_cursor = 0      // where the next slice of records starts in remaster_view_owned
Player/var/tmp/remaster_view_vpass = 0       // passes since the roster's order was last rebuilt

mob/Monsters/proc/RmViewRecord(Player/P)
	var/status = RmViewStatus()
	var/bits = 0
	var/f = 1
	for(var/id in rm_view_filter_ids)
		if(id == "all" || RmViewFilter(id, status)) bits |= f
		f *= 2
	if(findtext("[remaster_care_status]", "bringing food")) bits |= f   // "helping", after the filters
	if(P.RemasterIdleEligible(src, 1)) bits |= f * 2                       // "eligible": the idle badge's test (HUD.dm)
	return list(bits, 0, status)

Player/proc/RmViewRecAdd(list/R, sign)
	var/list/counts = remaster_view_counts
	var/f = 1
	for(var/id in rm_view_filter_ids)
		if(R[1] & f) counts[id] += sign
		f *= 2
	if(R[1] & f) counts["helping"] += sign
	if(R[1] & (f * 2)) counts["eligible"] += sign

Player/var/tmp/remaster_view_passing = -1000   // world.time a pass began, while it is under way

Player/proc/RmViewPass(spread = 0)
	// one at a time: a spread pass pauses between ticks, and a send in between (a command's) must not start another on
	// the same lists; it uses them as they stand. A pass older than 5 s died with an error and no longer holds this.
	if(world.time - remaster_view_passing < 50) return
	remaster_view_passing = world.time
	var/reset = 0
	if(!remaster_view_recmobs || remaster_view_pass_z != z)   // a new level: the records and totals are redone
		for(var/mob/Monsters/M in remaster_view_recmobs) M.rm_view_rec = null
		remaster_view_recmobs = list()
		remaster_view_recs = list()
		remaster_view_counts = list("helping"=0, "eligible"=0)
		for(var/id in rm_view_filter_ids) remaster_view_counts[id] = 0
		remaster_view_cursor = 0
		remaster_view_pass_z = z
		reset = 1
	// the company as the last pass had it (the owner, 10-31: "does things multiple itmes"): the engine names the units whose
	// state counter moved since (rm_list_changed, slot 3), and unless one came or went, changed place in UnitList, or
	// changed owner or wagon, the company's list, its marks and the records' list stand as they are (2,000 units: the walk
	// and the compaction were ~3 ms a pass). The minimap's cells move only for the units that moved (slot 4)
	var/list/C3 = rm_list_on ? rm_list_changed(src, 3, UnitList, 1) : null
	var/list/C4 = rm_list_on ? rm_list_changed(src, 4, UnitList, 0) : null
	var/keep = C3 && !C3[3] && !reset && remaster_view_owned && remaster_view_pk
	if(keep) for(var/mob/Monsters/M in C3[1]) if((M.Owner == src && !M.Wagon) != (M.rm_view_pass == remaster_view_pk))
		keep = 0
		break
	var/list/owned = remaster_view_owned
	var/list/km = remaster_view_recmobs
	var/list/kr = remaster_view_recs
	if(!keep)
		var/mk = ++rm_hud_serial
		owned = list()
		var/oi = 0
		for(var/mob/Monsters/M in UnitList) if(M.Owner == src && !M.Wagon)
			owned += M
			M.rm_hud_mark = mk
			M.rm_view_pass = mk   // this pass's company and each one's place in it, for the units on screen (RmViewSet)
			M.rm_view_i = ++oi
		remaster_view_pk = mk
		if(spread) RmTrackPause()
		// units gone from the company (or deleted): their records come off the totals. The two lists are compacted in place
		// (setting an index is cheap; new lists of 30,000 with a list made for each record were not)
		var/w = 0
		for(var/j = 1, j <= length(km), j++)
			var/mob/Monsters/M = km[j]
			if(M && M.rm_hud_mark == mk && M.rm_view_rec)
				w++
				if(w != j)
					km[w] = M
					kr[w] = kr[j]
			else
				RmViewRecAdd(kr[j], -1)
				if(M) M.rm_view_rec = null
		km.len = w
		kr.len = w
		remaster_view_owned = owned
	// the Company list leaves out the members of company groups (the page shows those as group cards); the groups are
	// the player's own lists, so they are read each pass, and the rows made again when they or the company changed
	var/list/gm = list()
	for(var/n = 1, n <= 9, n++) gm += RemasterGroupMembers(n)
	if(!keep || !remaster_view_rows || !RmViewSameList(gm, remaster_view_gm))
		var/gk = ++rm_hud_serial
		for(var/mob/Monsters/G in gm) G.rm_hud_gmark = gk
		var/list/rows = list()
		for(var/mob/Monsters/M in owned) if(M.rm_hud_gmark != gk) rows += M
		remaster_view_rows = rows
	remaster_view_gm = gm
	if(spread) RmTrackPause()
	// a slice of records: new units first (none is left out of the totals), then 1,000 from the cursor. A company kept as
	// it was has a record for every unit (only this pass makes or drops them)
	var/i = 0
	if(!keep) for(var/mob/Monsters/M in owned) if(!M.rm_view_rec)
		var/list/R = M.RmViewRecord(src)
		M.rm_view_rec = R
		M.rm_view_rec_fp = M.RmViewRecFP()
		km += M
		kr += list(R)
		RmViewRecAdd(R, 1)
		if(spread && !(++i % 250)) RmTrackPause()
	var/n = length(owned)
	var/slice = n < 1000 ? n : 1000
	for(var/k = 1, k <= slice && n, k++)
		remaster_view_cursor = remaster_view_cursor % n + 1
		var/mob/Monsters/M = owned[remaster_view_cursor]
		var/list/R = M.rm_view_rec
		// built once (the owner, 10-31: "it rebuild entries multiple times"): nothing the record reads has moved since it
		// was made (RmViewRecPrint), so it stands; a record made again whose filters are the same leaves the totals be
		if(M.rm_view_rec_fp && M.RmViewRecPrint() == M.rm_view_rec_fp)
			if(rm_hud_verify) RmViewRecVerify(M, R)
			continue
		var/list/N = M.RmViewRecord(src)
		if(N[1] != R[1])
			RmViewRecAdd(R, -1)
			R[1] = N[1]   // in place: the parallel list holds this same record
			RmViewRecAdd(R, 1)
		R[3] = N[3]
		M.rm_view_rec_fp = M.RmViewRecFP()
		if(spread && !(++i % 250)) RmTrackPause()
	if(spread) RmTrackPause()
	// the minimap: 48x48 cells over the map at the camera's level; a cell with any of yours is 1, with one of the selection
	// 2. Each cell counts its units and their selected ones; with the company kept, only the units that moved (slot 4)
	// and those the selection gained or lost are moved between cells, else every unit is counted again
	var/sk = ++rm_hud_serial
	for(var/mob/Monsters/M in Selected) M.rm_hud_smark = sk
	var/cmap = "[world.maxx],[world.maxy],[z]"
	if(!keep || !C4 || C4[3] || cmap != remaster_view_cmap || !remaster_view_ccnt || !world.maxx || !world.maxy)
		RmViewCellsAll(owned, sk, cmap)
	else
		var/list/touch = list()
		for(var/mob/Monsters/M in C4[1]) if(M.rm_view_pass == remaster_view_pk) touch[M] = 1
		if(!RmViewSameList(Selected, remaster_view_selwas))
			for(var/mob/Monsters/M in remaster_view_selwas) if(M.rm_view_pass == remaster_view_pk) touch[M] = 1
			for(var/mob/Monsters/M in Selected) if(M.rm_view_pass == remaster_view_pk) touch[M] = 1
		for(var/mob/Monsters/M in touch) RmViewCellMove(M, sk)
		remaster_view_cells = jointext(remaster_view_ctext, "")
	remaster_view_selwas = Selected ? Selected.Copy() : list()
	if(rm_once_verify) RmViewPassVerify(owned, sk)
	// the Village roster (only while it is open): filtered, searched and sorted, rebuilt when the page asks for another
	// filter, search or sort, and every 5 passes for the units' changes
	var/list/V = remaster_view
	var/list/v = islist(V) ? V["v"] : null
	if(!islist(v))
		remaster_view_village = null
		remaster_view_vkey = null
	else
		var/key = "[v["f"]]|[v["q"]]|[v["s"]]"
		if(key != remaster_view_vkey || !remaster_view_village || ++remaster_view_vpass >= 5 || n < 1000)
			remaster_view_vpass = 0
			remaster_view_vkey = key
			var/fi = rm_view_filter_ids.Find("[v["f"] || "all"]")
			var/fb = fi ? 2 ** (fi - 1) : 1
			var/vq = lowertext("[v["q"] || ""]")
			var/vs = "[v["s"] || "name"]"
			var/list/vl = list()
			var/list/k1 = list()
			var/list/k2 = list()
			for(var/mob/Monsters/M in owned)
				var/list/R = M.rm_view_rec
				if(!R || !(R[1] & fb)) continue
				if(vq && !findtext(lowertext("[M.name] [M.Race] [M.remaster_job] [R[3]] [M.Gender]"), vq)) continue
				vl += M
				switch(vs)
					if("job")
						k1 += RmViewKey3(M.remaster_job, 1)
						k2 += RmViewKey3(M.name, 1)
					if("status")
						k1 += RmViewKey3(R[3], 1)
						k2 += RmViewKey3(R[3], 4)
					if("health")
						k1 += M.MAXHP ? M.HP / M.MAXHP : 1
						k2 += RmViewKey3(M.name, 1)
					if("food")
						k1 += M.MaxHunger ? M.Hunger / M.MaxHunger : 1
						k2 += RmViewKey3(M.name, 1)
					if("rest")
						k1 += M.Tiredness
						k2 += RmViewKey3(M.name, 1)
					if("level")
						k1 += -M.Level
						k2 += RmViewKey3(M.name, 1)
					if("age")
						k1 += -M.Age
						k2 += RmViewKey3(M.name, 1)
					else
						k1 += RmViewKey3(M.name, 1)
						k2 += RmViewKey3(M.name, 4)
				if(spread && !(++i % 500)) RmTrackPause()
			RmSortBy(vl, k1, k2)
			remaster_view_village = vl
	remaster_view_pass_at = world.time
	remaster_view_passing = -1000
	RmShedKeep("pass", 1)

Player/var/tmp/list/remaster_view_gm       // the groups' members as the last pass read them
Player/var/tmp/list/remaster_view_ccnt     // each minimap cell's units (2304)
Player/var/tmp/list/remaster_view_scnt     // and its selected ones
Player/var/tmp/list/remaster_view_ctext    // each cell's character, "0", "1" or "2"
Player/var/tmp/list/remaster_view_selwas   // the selection as the cells last counted it
Player/var/tmp/remaster_view_cmap          // the map's size and the level the cells were counted for
mob/Monsters/var/tmp/rm_view_cell = 0      // the minimap cell it is counted in (0: none; quiet, Native.dm)
mob/Monsters/var/tmp/rm_view_csel = 0      // counted there as selected

proc/RmViewSameList(list/A, list/B)
	if(length(A) != length(B)) return 0
	for(var/i = 1, i <= length(A), i++) if(A[i] != B[i]) return 0
	return 1

proc/RmViewCell(mob/Monsters/M)
	return min(47, max(0, round((world.maxy - M.y) * 48 / world.maxy))) * 48 + min(47, max(0, round((M.x - 1) * 48 / world.maxx))) + 1

// every unit of the company counted into its cell again
Player/proc/RmViewCellsAll(list/owned, sk, cmap)
	var/list/cn = new /list(2304)
	var/list/sn = new /list(2304)
	var/ok = world.maxx && world.maxy
	for(var/mob/Monsters/M in owned)
		var/c = ok && M.z == z ? RmViewCell(M) : 0
		var/s = c && M.rm_hud_smark == sk
		if(c)
			cn[c] = (cn[c] || 0) + 1
			if(s) sn[c] = (sn[c] || 0) + 1
		M.rm_view_cell = c
		M.rm_view_csel = s
	var/list/t = new /list(2304)
	for(var/c = 1, c <= 2304, c++) t[c] = sn[c] ? "2" : (cn[c] ? "1" : "0")
	remaster_view_ccnt = cn
	remaster_view_scnt = sn
	remaster_view_ctext = t
	remaster_view_cmap = cmap
	remaster_view_cells = jointext(t, "")

// one unit moved between cells (or into or out of the selection)
Player/proc/RmViewCellMove(mob/Monsters/M, sk)
	var/c = M.z == z ? RmViewCell(M) : 0
	var/s = c && M.rm_hud_smark == sk
	var/o = M.rm_view_cell
	if(c == o && s == M.rm_view_csel) return
	var/list/cn = remaster_view_ccnt
	var/list/sn = remaster_view_scnt
	if(o)
		cn[o]--
		if(M.rm_view_csel) sn[o]--
		remaster_view_ctext[o] = sn[o] ? "2" : (cn[o] ? "1" : "0")
	if(c)
		cn[c] = (cn[c] || 0) + 1
		if(s) sn[c] = (sn[c] || 0) + 1
		remaster_view_ctext[c] = sn[c] ? "2" : (cn[c] ? "1" : "0")
	M.rm_view_cell = c
	M.rm_view_csel = s

// RM_ONCE_VERIFY: the company, its rows and the minimap as a pass in full makes them
Player/proc/RmViewPassVerify(list/owned, sk)
	var/list/F = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && !M.Wagon) F += M
	RmOnceCheck("viewowned", !RmViewSameList(F, owned), "[length(F)] [length(owned)]")
	var/gk = ++rm_hud_serial
	for(var/n = 1, n <= 9, n++) for(var/mob/Monsters/G in RemasterGroupMembers(n)) G.rm_hud_gmark = gk
	var/list/rows = list()
	for(var/mob/Monsters/M in F) if(M.rm_hud_gmark != gk) rows += M
	RmOnceCheck("viewrows", !RmViewSameList(rows, remaster_view_rows), "[length(rows)] [length(remaster_view_rows)]")
	var/list/cc = new /list(2304)
	if(world.maxx && world.maxy)
		for(var/mob/Monsters/M in F) if(M.z == z)
			var/c = RmViewCell(M)
			if(M.rm_hud_smark == sk) cc[c] = 2
			else if(!cc[c]) cc[c] = 1
	var/list/tt = new /list(2304)
	for(var/c = 1, c <= 2304, c++) tt[c] = cc[c] ? "[cc[c]]" : "0"
	RmOnceCheck("viewcells", jointext(tt, "") != remaster_view_cells, "cells")

// The view set for this send: the selection (up to RM_VIEW_SELCAP), the units on screen (up to RM_VIEW_SCREENCAP,
// nearest first), the members of open company groups and the rows each list window asked for. Also fills D's lists.
// Only for a big company: under ~1,000 units every unit going whole is cheaper than the view's pass, lists, counts and
// cells built each send (200 units all selected: 73 ms a send before the view, 109 ms with it; hud-craft, 10-24). It
// starts above 1,000 and stops under 900, so a company about that size doesn't switch back and forth.
#define RM_VIEW_ON 1000
#define RM_VIEW_OFF 900
Player/var/tmp/remaster_view_on = 0

Player/proc/RmViewSet(list/D, spread = 0)
	var/list/V = remaster_view
	if(!islist(V)) return null
	var/nu = length(UnitList)
	if(remaster_view_on ? nu < RM_VIEW_OFF : nu <= RM_VIEW_ON)
		remaster_view_on = 0
		return null
	remaster_view_on = 1
	var/every = rm_shed_every[min(4, max(0, rm_shed_level) + 1)]   // the tiers: the pass less often when behind
	if(!remaster_view_owned || world.time - remaster_view_pass_at >= RM_VIEW_PASS * every || (length(remaster_view_owned) < 1000 && RmShedDue("pass")) || remaster_view_pass_z != z) RmViewPass(spread)
	var/list/S = list()
	var/n = 0
	for(var/mob/Monsters/M in Selected)
		if(++n > RM_VIEW_SELCAP) break
		if(M.Owner == src) S[M] = 1
	// on screen: the 3D view's area round the camera
	var/hw = remaster_3d_hw || 20
	var/hh = remaster_3d_hh || 15
	var/list/near = RmViewNear(hw, hh)
	var/list/d = list()
	for(var/mob/Monsters/M in near) d += abs(M.x - x) + abs(M.y - y)
	if(rm_hud_verify) RmViewNearVerify(near, hw, hh)
	if(length(near) > RM_VIEW_SCREENCAP)
		RmSortBy(near, d)
		near.Cut(RM_VIEW_SCREENCAP + 1)
	for(var/mob/Monsters/M in near) S[M] = 1
	// the members of the company groups the page has open
	var/list/g = V["g"]
	if(islist(g)) for(var/num in g)
		var/k = 0
		for(var/mob/Monsters/M in RemasterGroupMembers(text2num("[num]")))
			if(++k > RM_VIEW_GROUPCAP) break
			S[M] = 1
	// the list windows
	var/list/lists = list()
	var/list/rows = remaster_view_rows || list()
	var/list/w = RmViewWin(V["c"], length(rows))
	lists["company"] = RmViewListData(rows, w, S)
	if(remaster_units_page) lists["units"] = RmViewListData(remaster_view_owned, RmViewWin(V["u"], length(remaster_view_owned)), S)
	var/list/vv = V["v"]
	if(remaster_view_village && islist(vv)) lists["village"] = RmViewListData(remaster_view_village, RmViewWin(list(vv["first"], vv["count"]), length(remaster_view_village)), S)
	D["lists"] = lists
	D["unitCount"] = length(remaster_view_owned)
	D["counts"] = remaster_view_counts
	D["unitCells"] = remaster_view_cells
	if(length(Selected) > RM_VIEW_SELCAP) D["band"] = RmViewBand()
	return S

// The pass's company on screen (within hw, hh of the camera on its level), in the company's order: from the unit grid's
// tiles round the camera and the company's carried units (RmGrid.cs) when the engine keeps it, so a send looks at the
// units near the camera, not the whole company (2,000 units: ~1 ms a send; 30,000: ~15). The same units in the same
// order as the walk over the company it was (RmViewNearAll, without the grid).
Player/var/tmp/remaster_view_pk = 0   // the pass that made remaster_view_owned (mob rm_view_pass)
mob/Monsters/var/tmp/rm_view_pass = 0
mob/Monsters/var/tmp/rm_view_i = 0
Player/proc/RmViewNear(hw, hh)
	var/list/G = rm_grid ? rm_grid_units(x - hw, y - hh, x + hw, y + hh, z) : null
	if(!islist(G)) return RmViewNearAll(hw, hh)
	var/list/H = rm_grid_held(list(src))
	if(islist(H)) G += H
	var/list/near = list()
	var/list/at = list()
	for(var/mob/Monsters/M in G) if(M.rm_view_pass == remaster_view_pk && M.z == z && abs(M.x - x) <= hw && abs(M.y - y) <= hh)
		near += M
		at += M.rm_view_i
	RmSortBy(near, at)
	return near

Player/proc/RmViewNearAll(hw, hh)
	var/list/near = list()
	for(var/mob/Monsters/M in remaster_view_owned) if(M.z == z && abs(M.x - x) <= hw && abs(M.y - y) <= hh) near += M
	return near

// RM_HUD_VERIFY=1: the grid's units on screen against the walk over the company
Player/proc/RmViewNearVerify(list/near, hw, hh)
	var/list/all = RmViewNearAll(hw, hh)
	rm_hud_verify_n++
	var/same = length(all) == length(near)
	if(same) for(var/i = 1, i <= length(all), i++) if(all[i] != near[i]) same = 0
	if(!same)
		rm_hud_verify_bad++
		if(!rm_hud_verify_keys["#near"])
			rm_hud_verify_keys["#near"] = 1
			world.log << "HUDV|differs|units on screen|[length(near)] from the grid, [length(all)] from the company"

// What a unit's view record (RmViewRecord: its status line, filters, helping, idle) reads: its change counter and what
// lies outside it (crafting and orders, changed in place; its bed). Null while it reads more (a fight, a chained beast,
// an open stump, moods): made again each pass, as before.
mob/Monsters/var/tmp/rm_view_rec_fp
mob/Monsters/proc/RmViewRecPrint()
	if(remaster_defense || remaster_combat_last || rm_bound || rm_moods_on) return null
	if(remaster_attacker && world.time - remaster_attacked_at <= REMASTER_ATTACKED_SHOWN) return null
	if(ismob(Target)) return null
	if(length(rm_stumps) && (RemasterStumpBleeding() || rm_stump_fester > 0)) return null
	// its state counter (walking keeps it), and what the filters and the idle test read of what is motion to the counter
	// (rm_ver_state_names): the hunger and tiredness thresholds, whether it has a next tile or a target
	return "[rm_ver_state(src)]|[Hunger <= max(20, MaxHunger * 0.25)][Hunger <= 20][Tiredness <= 25][Tiredness <= 20][destination ? 1 : 0][Target ? 1 : 0]|\
[length(remaster_production)]|[length(remaster_orders)]|\ref[remaster_active]|\ref[remaster_delivery]|[RemasterHomeText()]"

// made just after the record: an egg carried reads its mother (another unit), so none then
mob/Monsters/proc/RmViewRecFP()
	return (locate(/obj/Items/RmBeastEgg) in src) ? null : RmViewRecPrint()

// RM_HUD_VERIFY=1: a record kept this way against one made fresh
Player/proc/RmViewRecVerify(mob/Monsters/M, list/R)
	var/list/N = M.RmViewRecord(src)
	rm_hud_verify_n++
	if(N[1] != R[1] || N[3] != R[3])
		rm_hud_verify_bad++
		if(!rm_hud_verify_keys["#record"])
			rm_hud_verify_keys["#record"] = 1
			world.log << "HUDV|differs|view record|[M.name]|kept [R[1]] [R[3]]|fresh [N[1]] [N[3]]"

// ----- The HUD's tiers (option 1's load shedding: the coordinator, 10-24) -----
// server-cost's rm_shed_level says how far behind the server is (0 keeping up, 1/2/3 behind). The background keys
// (stores, counts, the board, the realm, the explored map, the idle count, list rows off screen) are then built every
// 2nd, 4th or 8th send and their last value sent in between (unchanged, so the keys delta sends nothing). Never held back
// at any level: the selection's and the on-screen units' entries and fast fields (health, status), hits and damage,
// deaths, captures, alerts, the open card, targets and orders.
// rm_shed_level: server-cost's, declared in Spread.dm (0 until its orders-first code sets it)
var/list/rm_shed_every = list(1, 2, 4, 8)
Player/var/tmp/list/remaster_shed_n     // key -> sends since it was last built
Player/var/tmp/list/remaster_shed_cache // key -> its last value

Player/proc/RmShedDue(k)
	if(rm_shed_level <= 0) return 1
	if(!remaster_shed_n) remaster_shed_n = list()
	if(!remaster_shed_cache || !(k in remaster_shed_cache)) return 1
	var/n = (remaster_shed_n[k] || 0) + 1
	if(n >= rm_shed_every[min(4, rm_shed_level + 1)])
		remaster_shed_n[k] = 0
		return 1
	remaster_shed_n[k] = n
	return 0

Player/proc/RmShedKeep(k, v)
	if(!remaster_shed_cache) remaster_shed_cache = list()
	remaster_shed_cache[k] = v
	return v

// a key that looks at the whole company: every send under 1,000 units, else when "ticks" have passed since it was built
Player/var/tmp/list/remaster_hud_slow_at   // key -> world.time it was last built
Player/proc/RmHudSlow(k, ticks)
	if(!remaster_shed_cache || !(k in remaster_shed_cache)) return 1
	if(length(UnitList) < 1000) return 1
	if(!remaster_hud_slow_at) remaster_hud_slow_at = list()
	if(world.time - (remaster_hud_slow_at[k] || -1000) < ticks) return 0
	remaster_hud_slow_at[k] = world.time
	return 1

// The realm: RemasterRealmData with Rulership.dm's Rule box (RmRuleData walks the whole company for its rulers and
// heir: ~250 ms at 30,000 units). Only the Realm page shows it, but for its war part (the war strip). It is built whole
// while the Realm page is open every 0.5 s (2 s over 1,000 units; and on opening it), else once a minute; the war part
// every send. It walks every player twice: built every send for every company under 1,000 units, 100 players made
// ~100,000 steps a second for pages nobody had open (load-asleep-1030, 10-31, planning/MANY_PLAYERS_PLAN_2026-10-31.md).
Player/proc/RmHudRealm()
	var/list/R = remaster_shed_cache ? remaster_shed_cache["realm"] : null
	var/every = remaster_hud_tab == "realm" ? (length(UnitList) < 1000 ? 5 : 20) : 600
	if(!islist(R) || (RmShedDue("realm") && world.time - remaster_realm_at >= every))
		remaster_realm_at = world.time
		return RmShedKeep("realm", RemasterRealmData())
	R = R.Copy()
	R["war"] = RemasterWarData()
	return R

// one list's window: its total, the first row and the rows' refs, in order (their units go in the view set)
Player/proc/RmViewListData(list/L, list/w, list/S)
	if(!w) return list("total"=length(L), "first"=0, "refs"=list())
	var/list/refs = list()
	for(var/i = w[1] + 1, i <= w[1] + w[2], i++)
		var/mob/Monsters/M = L[i]
		// gone since the pass (deleted, which isn't null here, or given away): not a row now, whatever the tiers hold back
		if(!M || M.Owner != src || !M.loc) continue
		refs += RemasterUIRef(M)
		if(!S[M]) S[M] = 2   // a row only: the tiers may hold it back (the selection, the screen: 1, always fresh)
	return list("total"=length(L), "first"=w[1], "refs"=refs)

// a selection bigger than RM_VIEW_SELCAP: what the band card shows as pressed (when all agree), worked out over all of it
Player/proc/RmViewBand()
	var/style = null
	var/mode = null
	var/nl = null
	var/op = null
	var/first = 1
	for(var/mob/Monsters/M in Selected)   // the vars themselves (RemasterDefenseData made a list per unit: select all is 30,000)
		var/s = M.remaster_combat_style
		var/m = M.remaster_defense_mode
		var/l = M.remaster_nonlethal ? 1 : 0
		var/o = M.remaster_own_pace ? 1 : 0
		if(first)
			style = s
			mode = m
			nl = l
			op = o
			first = 0
			continue
		if(style != s) style = "#mixed"
		if(mode != m) mode = "#mixed"
		if(nl != l) nl = "#mixed"
		if(op != o) op = "#mixed"
		if(style == "#mixed" && mode == "#mixed" && nl == "#mixed" && op == "#mixed") break   // nothing left to agree on
	return list("n"=length(Selected), "style"=style, "mode"=mode, "nonlethal"=nl, "ownPace"=op)

// ----- A unit's HUD entry kept between sends (the coordinator, 10-24: 200 selected, ~80 ms a send) -----
// RemasterUnitData builds ~70 fields from many procs, and the units delta then encodes every part of every entry to see
// what changed, though in most sends nothing in an entry changes but where the unit stands and its health, food and rest
// (the hot fields, sent as one short row each). So an entry is kept on the unit and used again while its key (what its
// order, status and warning lines, its card's shape and its pack are made from) stays the same, for up to
// RM_ENTRY_KEEP ticks (staggered, so the rebuilds spread over the sends): the hot fields are written into it fresh every
// send, and the units delta reuses its parts as encoded last time. A changed order, health warning, bleeding, out cold,
// dying, defence, care or pack changes the key: rebuilt that send. Never kept: the open card's unit (one selected) and
// the selection while the Units page shows its sheets.
#define RM_ENTRY_KEEP 30
Player/var/tmp/remaster_hud_live = 0         // set while RemasterHUDTick builds a send; other callers (tests, checks) get
                                             // every entry built fresh, as before
mob/Monsters/var/tmp/list/rm_hud_entry       // the entry as last built, its key, when, and for which player
mob/Monsters/var/tmp/rm_hud_entry_key
mob/Monsters/var/tmp/rm_hud_entry_at = -1000
mob/Monsters/var/tmp/rm_hud_entry_for
// Built once (the owner, 10-31: "it rebuild entries multiple times or does things multiple itmes"): what the kept entry
// was built from, so a send that finds none of it moved neither makes the key nor rebuilds the entry every RM_ENTRY_KEEP
mob/Monsters/var/tmp/rm_hud_entry_v           // the unit's state counter (rm_ver_state: walking keeps it) just after the build
mob/Monsters/var/tmp/rm_hud_entry_fp          // what lies outside the unit (RmHudEntryOutside), or null: the key path
mob/Monsters/var/tmp/rm_hud_entry_until = 0   // its clock parts (out cold, bandaged) hold until this world.time

mob/Monsters/proc/RmHudEntryKey(Player/P, sel)
	var/datum/remaster_order/A = remaster_active
	var/atom/T = A ? A.target : null
	// combat first, as before: its line is worked out every send, and it may log an event ("Fight over", "Won against")
	// that the events part below reads
	var/status = RemasterCombatStatus()
	var/ev = length(remaster_events)
	// its pack: each thing, worn or not, and a quiver's arrows (the bag, the arrows slot, its formation role, its weapon)
	var/pack = ""
	for(var/obj/O in src) pack += istype(O, /obj/Items/Equipment/Armour/Quiver) ? "[O.type][O.suffix]([O:Content])," : "[O.type][O.suffix],"
	// One string, in the order it was built in thirteen steps before (U5's rest, 10-31: the steps' copies of the growing
	// text were over half of its ~14 us, for each of your units twice a second); the same text.
	// combat, then the orders; health and the warnings (the numbers themselves are the hot fields); the pack; what the
	// card shows
	return "[status]|[remaster_defense ? "[remaster_defense.phase]:[remaster_defense.attacker]" : ""]|[ev]:[ev ? remaster_events[ev][1] : 0]|\
[sel]|[remaster_order_status]|[A ? "[A.kind]@[T ? "[T.x],[T.y],[T.z]" : ""]" : ""]|[remaster_delivery ? 1 : 0]|[length(remaster_orders)]|\
[remaster_job]|[rm_jz_id]|[remaster_paused]|[remaster_wait_for_resume]|[remaster_role_paused]|[remaster_blocked]|[length(remaster_production)]|\
[remaster_patrol ? 1 : 0]|[destination ? 1 : 0]|[Target ? "[Target]" : ""]|[BowOn]|[remaster_tend_mode]|[remaster_auto_unload]|\
[RmLifeFrac(src) < 0.3][Hunger <= 20][Tiredness <= 20][Coldness][BloodContent < 80][HasLeftLeg][HasRightLeg][HasLeftArm][HasRightArm]|\
[jointext(RemasterAilmentWarnings(), ",")]|[jointext(RmTameWarnings(src), ",")]|\
[BleedType]|[Fainted]|[Sleeping]|[GoingToDie]|[Stunned]|[InHole]|[IsMist]|[Meditating]|[rm_cap_state]|[rm_cap_state ? json_encode(RmCaptiveData(P)) : ""]|\
[remaster_defense_mode]|[remaster_combat_style]|[remaster_nonlethal]|[remaster_own_pace]|\
[remaster_care_status]|[remaster_care_note]|[rm_moods_on ? round(remaster_mood) : ""]|\
[weight]|[weightmax]|[pack]|[name]|[Race]|[Level]|[Age]|[MAXHP]|[MaxHunger]|[IsRoyal]|[remaster_priority]|[P.remaster_units_page]|[rm_fav]"

// the hot fields (HUD.dm rm_hud_hot), fresh, into a kept entry
mob/Monsters/proc/RmHudEntryHot(list/E, sel)
	var/turf/at = rm_cap_cage ? RemasterGetTurf(src) : null
	E["x"] = at ? at.x : x
	E["y"] = at ? at.y : y
	E["z"] = at ? at.z : z
	E["hp"] = RmLifeHP(src)
	E["fullness"] = round(Hunger)
	E["energy"] = round(Tiredness)
	E["selected"] = sel

// The unit's entry for P: the kept one while it may be (marked "#r" for the units delta, which takes the mark off), else
// built and kept. Kept with no key made when nothing it was built from has moved (built once); else kept while its key
// holds, up to RM_ENTRY_KEEP, as before.
mob/Monsters/proc/RmHudEntry(Player/P, list/selset)
	var/sel = selset[src] ? 1 : 0
	if(!P.remaster_hud_live || (sel && (length(P.Selected) == 1 || P.remaster_units_page))) return RemasterUnitData(P, selset)
	var/list/E = rm_hud_entry
	if(E && rm_hud_entry_for == P && rm_hud_entry_fp && world.time < rm_hud_entry_until && rm_ver_state(src) == rm_hud_entry_v && RmHudEntryOutside(P, sel) == rm_hud_entry_fp)
		if(rm_hud_verify) RmHudEntryVerify(P, selset, E)
		RmHudEntryHot(E, sel)
		// its events' "ago" (the clock alone) as often as the refresh had it: that part only, not the whole entry
		if(length(remaster_events) && world.time - rm_hud_entry_at >= RM_ENTRY_KEEP)
			E["events"] = RemasterEventData()
			rm_hud_entry_at = world.time
			return E   // not marked kept: the units delta encodes it again and finds only its events changed
		E["#r"] = 1
		return E
	var/key = RmHudEntryKey(P, sel)
	if(E && rm_hud_entry_for == P && rm_hud_entry_key == key && world.time - rm_hud_entry_at < RM_ENTRY_KEEP)
		RmHudEntryHot(E, sel)
		E["#r"] = 1
		return E
	E = RemasterUnitData(P, selset)
	rm_hud_entry = E
	rm_hud_entry_key = key
	rm_hud_entry_for = P
	rm_hud_entry_at = world.time - rand(0, RM_ENTRY_KEEP / 2)
	// what it was built from: the counter after the build (the build's own writes counted) and what lies outside the unit;
	// an egg carried reads its mother (another unit): the key path while it has one
	rm_hud_entry_v = rm_ver_state(src)
	rm_hud_entry_fp = (locate(/obj/Items/RmBeastEgg) in src) ? null : RmHudEntryOutside(P, sel)
	rm_hud_entry_until = RmHudEntryUntil()
	return E

// What a unit's HUD entry reads beyond the unit itself and what it carries (rm_ver sees every write on those, their
// moves and looks, and things going in or out): the player's view of it, lists the game changes in place (events,
// orders, crafting), its orders' targets, the thing it targets, its job row's name, its bed, the game's switches. Null
// while it reads more than this can follow (a fight, a chained beast, a captive, an open stump, moods): the key path then.
mob/Monsters/proc/RmHudEntryOutside(Player/P, sel)
	if(remaster_defense || remaster_combat_last || rm_bound || rm_cap_state || rm_cap_cage || rm_moods_on) return null
	// a stump open or bandaged, or a burn festering, changes in place (Stumps.dm); a healed one shows nothing (every unit
	// has the list, empty at first)
	if(length(rm_stumps) && (RemasterStumpBleeding() || rm_stump_fester > 0)) return null
	if(remaster_attacker && world.time - remaster_attacked_at <= REMASTER_ATTACKED_SHOWN) return null
	if(ismob(Target)) return null
	var/datum/remaster_order/A = remaster_active
	var/datum/remaster_order/B = remaster_delivery
	var/atom/AT = A ? A.target : null
	var/atom/BT = B ? B.target : null
	var/ev = length(remaster_events)
	var/list/Z = rm_jz_id ? P.RmJz(rm_jz_id) : null
	// hunger, tiredness, a walk's next tile and blocked are motion to the counter (rm_ver_state_names): what the entry
	// reads of them counts (the target's change, its name, by its own counter below)
	. = "[sel]|[P.remaster_units_page]|[rm_underdog_on]|[Hunger <= 20][Tiredness <= 20][destination ? 1 : 0]|[remaster_blocked]|[ev]:[ev ? remaster_events[ev][1] : 0]|[length(remaster_orders)]|\
[length(remaster_production)]|\ref[A]:[A ? A.kind : ""]:\ref[AT]:[AT ? rm_ver(AT) : ""]|\ref[B]:[B ? B.kind : ""]:\ref[BT]:[BT ? rm_ver(BT) : ""]|\
\ref[Target]:[Target ? rm_ver(Target) : ""]|[Z ? Z["name"] : ""]|[RemasterHomeText()]"
	// the selection's queued orders show on its card (HUD.dm RemasterUnitData "pending")
	if(sel) for(var/datum/remaster_order/O in remaster_orders)
		var/atom/OT = O.target
		. += "|\ref[O]:[O.kind]:\ref[OT]:[OT ? rm_ver(OT) : ""]"

// The world.time until which the entry's clock parts hold: out cold until, bandaged until
mob/Monsters/proc/RmHudEntryUntil()
	. = 1e9
	if(remaster_ko_until > world.time) . = min(., remaster_ko_until)
	if(rm_bandaged_until > world.time) . = min(., rm_bandaged_until)

// RM_HUD_VERIFY=1 in the server's environment (tests): every entry kept with no key is checked against one built fresh
// (the hot fields aside, written fresh every send; a part null in it the units delta leaves out; its events' texts, their
// "ago" as the refresh keeps it), and the players with no client get their entries made each second too, so the arena
// checks' players (obey, combat) go through it. HUDV lines in the log: how many checked, how many different, which keys.
var/rm_hud_verify = 0
var/rm_hud_verify_n = 0
var/rm_hud_verify_bad = 0
var/list/rm_hud_verify_keys = list()
mob/Monsters/proc/RmHudEntryVerify(Player/P, list/selset, list/E)
	var/list/F = RemasterUnitData(P, selset)
	var/list/K = E.Copy()
	K -= "#r"
	for(var/k in rm_hud_unit_parts)
		if((k in F) && isnull(F[k])) F -= k
		if((k in K) && isnull(K[k])) K -= k
	for(var/k in rm_hud_hot)
		K -= k
		F -= k
	var/list/fe = F["events"]
	var/list/ke = K["events"]
	if(islist(fe) && islist(ke) && length(fe) == length(ke))
		var/same = 1
		for(var/i = 1, i <= length(fe), i++) if(fe[i]["text"] != ke[i]["text"]) same = 0
		if(same) F["events"] = ke
	rm_hud_verify_n++
	if(json_encode(F) != json_encode(K))
		rm_hud_verify_bad++
		for(var/k in F) if(json_encode(F[k]) != json_encode(K[k]) && !rm_hud_verify_keys[k])
			rm_hud_verify_keys[k] = 1
			world.log << "HUDV|differs|[k]|[name]|kept [copytext(json_encode(K[k]), 1, 160)]|fresh [copytext(json_encode(F[k]), 1, 160)]"
		for(var/k in K) if(!(k in F) && !rm_hud_verify_keys[k])
			rm_hud_verify_keys[k] = 1
			world.log << "HUDV|differs|[k]|[name]|kept only"
	if(!(rm_hud_verify_n % 500)) world.log << "HUDV|checked [rm_hud_verify_n]|different [rm_hud_verify_bad]"

proc/RmHudVerifyStart()
	rm_hud_verify = world.GetConfig("env", "RM_HUD_VERIFY") == "1"
	if(!rm_hud_verify) return
	world.log << "HUDV|on"
	spawn(10) while(1)
		for(var/Player/P in world) if(!P.client)
			var/list/sel = list()
			for(var/S in P.Selected) sel[S] = 1
			P.remaster_hud_live = 1
			for(var/mob/Monsters/M in P.UnitList) if(M.Owner == P && !M.Wagon)
				var/list/E = M.RmHudEntry(P, sel)
				E -= "#r"
			P.remaster_hud_live = 0
		world.log << "HUDV|checked [rm_hud_verify_n]|different [rm_hud_verify_bad]"
		sleep(10)
var/rm_hud_verify_started = RmHudVerifyStart()

// Select all (Verbs.dm Every: the HUD's Select all and Ctrl+A). The original looks through the selection for every unit
// (and Select looks again): square in the company's size, seconds at 30,000. Up to 1,000 units it runs as it always has;
// above, the same units in one go: those already selected by a mark, and Select's own tests without its search (Mobs.dm:
// not an egg, in a hole, or inside something; QoL.dm: your sleeping ones too; Captives.dm: a caged one unless asleep;
// Critters.dm: never a critter).
Player/Every()
	if(length(UnitList) <= 1000) return ..()
	var/sk = ++rm_hud_serial
	for(var/mob/Monsters/S in Selected) S.rm_hud_smark = sk
	var/list/add = list()
	var/list/stars = list()
	for(var/mob/Monsters/c in world) if(c.Owner == src && !c.Wagon && c.rm_hud_smark != sk)
		c.rm_hud_smark = sk
		if(istype(c, /mob/Monsters/Critters) || c.Egg || c.InHole) continue
		if((c.rm_cap_cage && isobj(c.loc)) ? c.Sleeping : (ismob(c.loc) || isobj(c.loc))) continue
		add += c
		if(c.Star) stars += c.Star
	if(!length(add)) return
	Selected += add
	if(client && length(stars)) client.images += stars
	remaster_queue = 0
