// Browser requests outlive individual render updates. Engine \ref slots can
// be reused after deletion, so they are not lifetime identities for controls.
// These temporary tokens are assigned only on export and never saved to units.
var/tmp/remaster_ui_session
var/tmp/remaster_ui_sequence = 0
var/tmp/remaster_ui_generation = 0

datum/var/tmp/remaster_ui_id
// Units by their ref's sequence number (this generation's): RemasterUIUnit looks one up in one step instead of searching
// the whole company for every command and check (30,000 units: ~18 ms each; hud-craft, 10-24). A plain list indexed
// by number (setting an index is cheap; an associative key would scan the list here). Units only, so no item is kept.
var/tmp/list/rm_ui_units = list()

proc/RemasterUIRef(datum/D)
	if(!D) return ""
	if(!D.remaster_ui_id)
		if(!remaster_ui_session) remaster_ui_session = "[world.realtime]-[world.timeofday]"
		// Keep counters below single-precision integer limits in long sessions.
		if(remaster_ui_sequence >= 1000000)
			remaster_ui_generation++
			remaster_ui_sequence = 0
			rm_ui_units = list()
		remaster_ui_sequence++
		D.remaster_ui_id = "ui-[remaster_ui_session]-[remaster_ui_generation]-[remaster_ui_sequence]"
		if(istype(D, /mob/Monsters))
			if(length(rm_ui_units) < remaster_ui_sequence) rm_ui_units.len = remaster_ui_sequence
			rm_ui_units[remaster_ui_sequence] = D
	return D.remaster_ui_id

Player/proc/RemasterUIUnit(reference)
	if(!istext(reference) || !length(reference)) return null
	var/p = findlasttext(reference, "-")
	var/seq = p ? text2num(copytext(reference, p + 1)) : 0
	if(seq >= 1 && seq <= length(rm_ui_units))
		var/mob/Monsters/U = rm_ui_units[seq]
		if(U && U.remaster_ui_id == reference) return U.Owner == src ? U : null   // the same unit (its whole ref matches)
	for(var/mob/Monsters/M in UnitList)   // an older generation's ref: the search, as before
		if(M.Owner == src && M.remaster_ui_id && M.remaster_ui_id == reference) return M
	return null

Player/proc/RemasterUIItem(reference)
	if(!istext(reference) || !length(reference)) return null
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || !(M in UnitList)) continue
		for(var/obj/Items/I in M)
			if(I.loc == M && I.remaster_ui_id && I.remaster_ui_id == reference) return I
	return null
