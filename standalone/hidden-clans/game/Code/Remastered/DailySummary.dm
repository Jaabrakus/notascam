// Daily summary. The game has no day counter (Date is a random year picked at
// world start), so a day here is one night-to-morning change. Each morning the
// player gets a card for the day before: resources gained, births, deaths,
// fights, and what is stuck. It also goes into the village log.

Player/var/remaster_days = 0                 // mornings seen
Player/var/tmp
	remaster_was_night = -1
	list/remaster_day_start                  // kind -> stock count at the last morning
	remaster_day_log_from = 0                // village log serial at the last morning
	list/remaster_day_summary                // shown on the card until closed
	remaster_day_had_people = 0               // people at the last morning: no report for the day you arrived (playtest)
	// The day's births, deaths, attacks and problems, counted as they are logged (RmDayNote). The card used to read
	// them back from the village log, which keeps 150 lines: a busy day's skill, morale and fight lines pushed its
	// births and deaths off it before the morning.
	list/rm_day_counts
	rm_day_fought_at = -1000000

Player/proc/RemasterDayTick()
	if(remaster_was_night == -1)
		remaster_was_night = night
		RemasterDayStart()
		return
	if(remaster_was_night && !night) RemasterDayEnd()
	remaster_was_night = night

Player/proc/RemasterDayStart()
	remaster_day_start = list()
	for(var/k in list("wood", "stone", "food")) remaster_day_start[k] = RemasterStockCount(k)
	remaster_day_log_from = remaster_village_log_serial
	remaster_day_had_people = length(UnitList) > 0
	rm_day_counts = list("births"=0, "deaths"=0, "fights"=0, "problems"=0)

// One village log line, counted for the day's card (RemasterLog, VillageLog.dm). An attack on the village is every
// "Attacked by" line until a minute without one: each villager hit logs its own (again after 10 s quiet), so one raid
// read as dozens of attacks.
Player/proc/RmDayNote(kind, text)
	if(!rm_day_counts) return
	switch(kind)
		if("birth") if(findtext(text, "was born")) rm_day_counts["births"]++
		if("death") rm_day_counts["deaths"]++
		if("fight")
			if(findtext(text, "Attacked by"))
				if(world.time - rm_day_fought_at > 600) rm_day_counts["fights"]++
				rm_day_fought_at = world.time
		if("problem") rm_day_counts["problems"]++

Player/proc/RemasterDayEnd()
	if(!length(UnitList) || !remaster_day_had_people)    // no people, or they only arrived today: no all-zero report (playtest)
		RemasterDayStart()
		return
	remaster_days++
	var/list/gained = list()
	for(var/k in list("wood", "stone", "food"))
		var/d = RemasterStockCount(k) - (remaster_day_start ? remaster_day_start[k] : 0)
		if(d) gained[k] = d
	var/list/C = rm_day_counts || list()
	var/births = C["births"] || 0
	var/deaths = C["deaths"] || 0
	var/fights = C["fights"] || 0
	var/problems = C["problems"] || 0
	var/stuck = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && (M.remaster_blocked || M.remaster_wait_for_resume)) stuck++
	var/list/parts = list()
	for(var/k in gained) parts += "[gained[k] > 0 ? "+" : ""][gained[k]] [k]"
	if(births) parts += "[births] born"
	if(deaths) parts += "[deaths] died"
	if(fights) parts += "[fights] attack[fights == 1 ? "" : "s"]"
	if(stuck) parts += "[stuck] stuck"
	var/text = length(parts) ? jointext(parts, " · ") : "A quiet day"
	remaster_day_summary = list("day"=remaster_days, "text"=text, "gained"=gained, "births"=births, "deaths"=deaths, "fights"=fights, "problems"=problems, "stuck"=stuck)
	RemasterLog("Day [remaster_days]: [text]", stuck || deaths ? "problem" : "work", null)
	RemasterDayStart()
