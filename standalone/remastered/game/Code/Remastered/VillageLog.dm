// One event log for the whole village: births, deaths, fights, finished board
// orders, things units couldn't reach. Each entry remembers where it happened,
// so the Village > Log view can jump there.

#define REMASTER_VILLAGE_LOG_KEPT 150

Player/var/tmp/list/remaster_village_log   // list(list(time, text, kind, x, y, z))
Player/var/tmp/remaster_village_log_serial = 0

Player/proc/RemasterLog(text, kind = "info", atom/where)
	if(!remaster_village_log) remaster_village_log = list()
	var/turf/T = where ? RemasterGetTurf(where) : null
	// The same line again within 20 seconds is not news.
	for(var/i = length(remaster_village_log), i >= 1 && i > length(remaster_village_log) - 6, i--)
		var/list/L = remaster_village_log[i]
		if(L[2] == text && world.time - L[1] < 200) return
	remaster_village_log_serial++
	remaster_village_log += list(list(world.time, text, kind, T ? T.x : 0, T ? T.y : 0, T ? T.z : 0, remaster_village_log_serial))
	while(length(remaster_village_log) > REMASTER_VILLAGE_LOG_KEPT) remaster_village_log.Cut(1, 2)
	RmDayNote(kind, text)   // the day's card (DailySummary.dm)

Player/proc/RemasterVillageLogData()
	var/list/out = list()
	if(remaster_village_log) for(var/i = length(remaster_village_log), i >= 1, i--)
		var/list/L = remaster_village_log[i]
		out += list(list("ago"=round((world.time - L[1]) / 10), "text"=L[2], "kind"=L[3], "x"=L[4], "y"=L[5], "z"=L[6], "id"=L[7]))
	return out

Player/proc/RemasterGotoPlace(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) != 3) return 0
	var/turf/T = locate(text2num(p[1]), text2num(p[2]), text2num(p[3]))
	if(!T) return 0
	loc = T
	return 1

proc/RemasterGetTurf(atom/A)
	while(A && !isturf(A)) A = A.loc
	return A

// Minimap pings: placed log entries from the last minute (fights, deaths,
// births, problems), newest first, at most 12.
Player/proc/RemasterPingData()
	var/list/out = list()
	if(remaster_village_log) for(var/i = length(remaster_village_log), i >= 1 && length(out) < 12, i--)
		var/list/L = remaster_village_log[i]
		if(world.time - L[1] > 600) break
		if(!L[6] || !(L[3] in list("fight", "death", "birth", "problem", "good"))) continue
		out += list(list(L[4], L[5], L[6], L[3], round((world.time - L[1]) / 10)))
	return out
