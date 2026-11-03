// ===== The Realm overview (hud-rework 10-27, owner: "build them"): the goods in store and how they move =====
// The Realm page's Overview tab answers "is my economy keeping up?" for a realm of thousands. Its people and workplaces
// come from what the page already has (Jobs.dm: the population counts and the job board's rows); this adds the goods:
// every kind on the stores (the main stockpile and every zone, as the stock counts see them, Board.dm
// RemasterStockCount, an item round two stores counted once), counted at most every 10 s and only while the Realm page
// is open, and each kind's change per hour from counts a minute apart over the last 10 minutes.
#define RM_OV_EVERY 100        // a recount at most this often (10 s)
#define RM_OV_SAMPLE 600       // a count kept for the change per hour this often (1 min)
#define RM_OV_SPAN 6000        // the change per hour is measured over this long at most (10 min)
#define RM_OV_ROWS 40          // the most kinds sent (the biggest stocks first), and how many more

Player/var/tmp/list/rm_ov_rows     // the last answer: list("goods"=rows, "more"=n, "span"=seconds measured, "at"=world.time)
Player/var/tmp/list/rm_ov_hist     // list(list(world.time, list(name = count)), ...), oldest first

// Every item kind on the stores, by name: list(name = count).
Player/proc/RmOvCount()
	var/list/G = list()
	if(!RemasterStockpile()) return G
	rm_sc_serial++
	var/mark = rm_sc_serial
	for(var/turf/T in RemasterStores())
		for(var/obj/Items/I in range(1, T)) if(isturf(I.loc) && I.rm_sc_mark != mark)
			I.rm_sc_mark = mark
			var/k = "[I.name]"
			G[k] = (G[k] || 0) + 1
	return G

Player/proc/RmOvData()
	if(rm_ov_rows && world.time - rm_ov_rows["at"] < RM_OV_EVERY) return rm_ov_rows
	var/list/G = RmOvCount()
	if(!rm_ov_hist) rm_ov_hist = list()
	// counts older than the span go (a page closed for an hour starts measuring again), then one a minute is kept
	while(length(rm_ov_hist) && world.time - rm_ov_hist[1][1] > RM_OV_SPAN + RM_OV_SAMPLE) rm_ov_hist.Cut(1, 2)
	if(!length(rm_ov_hist) || world.time - rm_ov_hist[length(rm_ov_hist)][1] >= RM_OV_SAMPLE) rm_ov_hist += list(list(world.time, G.Copy()))
	var/list/old = rm_ov_hist[1]
	var/span = world.time - old[1]
	var/list/prev = old[2]
	var/list/rows = list()
	for(var/k in G) rows += list(list(k, G[k], span >= RM_OV_SAMPLE ? round((G[k] - (prev[k] || 0)) * 36000 / span) : null))
	if(span >= RM_OV_SAMPLE) for(var/k in prev) if(isnull(G[k])) rows += list(list(k, 0, round(-prev[k] * 36000 / span)))   // all used up
	// the biggest stocks first (an insertion sort: a few dozen kinds)
	for(var/i = 2, i <= length(rows), i++)
		var/list/r = rows[i]
		var/j = i - 1
		while(j >= 1 && rows[j][2] < r[2])
			rows[j + 1] = rows[j]
			j--
		rows[j + 1] = r
	var/more = max(0, length(rows) - RM_OV_ROWS)
	if(more) rows.Cut(RM_OV_ROWS + 1)
	rm_ov_rows = list("goods"=rows, "more"=more, "span"=round(span / 10), "at"=world.time)
	return rm_ov_rows

Player/RemasterHUDData()
	. = ..()
	if(islist(.) && remaster_hud_tab == "realm")
		var/list/O = RmOvData()
		.["overview"] = list("goods"=O["goods"], "more"=O["more"], "span"=O["span"])
