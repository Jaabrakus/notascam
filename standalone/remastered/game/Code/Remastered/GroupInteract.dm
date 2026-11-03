// The Interact menu for a group (hud-craft, 10-25; the user: "a painpoint when we have 203 units selected and hit
// interact we are doomed"). The original Interact (Creatures/Interact.dm) asks "Have [M] interact how?" once for every
// selected unit, so 203 question cards came one after another. With two or more selected it now asks once: what they can
// do, read the way each one's skill bar reads it (Abilities.dm RemasterAbilities: This Creature and Magical Skills, and
// Closest Creature by kind, each with the creature beside it), every choice with how many of them can. The one answer then
// runs for every unit it fits, through the original menu with the answers ready (as a skill bar button runs it), a few
// units a tick within the tick ledger (Spread.dm), so 203 or 2,000 never stall a tick; one line says how it went. A
// question after the answer (a kind of land, a direction) is asked once, for the first unit, and its answer used for the
// rest (where it is one of their answers). One unit selected: as before (the I key's near card, or the original menu).

#define RM_GI_LINE 30   // ms: the tick ledger's line for this work (the track's, RM_TRACK_SLICE); at least one unit a tick

var/rm_gi_test = 0              // tests: the group path without a client, answered by rm_gi_test_answer (the label's start)
var/rm_gi_test_answer
var/rm_gi_asked = 0             // tests: group questions asked
var/list/rm_gi_test_opts        // tests: the last group question's answers
var/rm_gi_tick_max = 0          // tests: the most ms of this work in one tick
var/list/rm_gi_pieces = list()  // tests: each piece's ms (scan, then run)

Player/var/tmp
	rm_gi_busy = 0              // a group Interact under way (looking, asking or running): another waits for it
	list/rm_gi_follow           // the first unit's answers after the ready ones, used for the rest

Player/Interact()
	if(length(Selected) < 2 || remaster_preset_choices || remaster_preset_record || !(client || rm_gi_test)) return ..()
	if(rm_gi_busy)
		RemasterNotice("Still working through the last Interact.")
		return
	rm_gi_busy = 1
	spawn(0) RmGroupInteract()

// The kind a menu entry is grouped by: This Creature and Magical Skills by name; Closest Creature by what it does
// ("Breed With Ann" and "Breed With Bo" are one choice: each with its own mate beside it).
proc/RmGiKind(menu, ability)
	if(menu != "Closest Creature") return "[menu]|[ability]"
	for(var/p in list("Feed From ", "Rescue ", "Breed With ", "Bite ")) if(findtext("[ability]", p) == 1) return "Closest Creature|[p]"
	return null

proc/RmGiWhat(key)
	var/list/p = splittext(key, "|")
	if(p[1] != "Closest Creature") return p[2]
	switch(p[2])
		if("Feed From ") return "Drink blood"   // a vampire, from the creature beside it
		if("Rescue ") return "Rescue from a pit"
		if("Breed With ") return "Breed with a mate"
		if("Bite ") return "Bite a neighbour"
	return p[2]

// One piece of the work at a time: on while this tick's ledger has room under RM_GI_LINE, else the next tick (one piece
// a tick always goes, so a busy server still gets through). Returns the tick the next piece is in.
Player/proc/RmGiWait(list/state)
	if(state[1] != world.time)
		rm_gi_tick_max = max(rm_gi_tick_max, state[3])
		state[1] = world.time
		state[2] = 0
		state[3] = 0
	if(state[2] && RmTickRoom(RM_GI_LINE) <= 0)
		sleep(world.tick_lag)
		rm_gi_tick_max = max(rm_gi_tick_max, state[3])
		state[1] = world.time
		state[2] = 0
		state[3] = 0
	state[2]++

// What a piece took (ms; none if it slept), on the ledger and on this run's own count for the tick.
Player/proc/RmGiCharge(list/state, t0, w0)
	if(world.time != w0) return
	var/ms = max(0, (world.tick_usage - t0) * world.tick_lag)
	RmTickCharge(ms)
	state[3] += ms
	if(rm_gi_test) rm_gi_pieces += ms

Player/proc/RmGroupInteract()
	usr = src
	var/list/units = list()
	for(var/mob/Monsters/M in Selected) if(RemasterInteractActor(M) && M.HP > 0) units += M
	var/n = length(units)
	if(n < 2)   // only one of them can act: its own menu, as before
		rm_gi_busy = 0
		if(n == 1)
			var/list/old = Selected
			Selected = list(units[1])
			Interact()
			Selected = old
		return
	// what each can do, a few a tick
	var/list/count = list()
	var/list/order = list()
	var/list/state = list(world.time, 0, 0)
	for(var/mob/Monsters/M in units)
		RmGiWait(state)
		if(!M) continue
		var/t0 = world.tick_usage
		var/w0 = world.time
		var/list/had = list()
		for(var/list/A in RemasterAbilities(M))
			var/k = RmGiKind(A[1], A[2])
			if(!k || had[k]) continue
			had[k] = 1
			if(!count[k])
				count[k] = 0
				order += k
			count[k] = count[k] + 1
		RmGiCharge(state, t0, w0)
		usr = src
	var/list/opts = list()
	var/list/map = list()
	for(var/k in order)
		var/l = "[RmGiWhat(k)] ([count[k] == n ? "all" : "[count[k]]"])"   // how many of them can (the card says so)
		var/list/kp = splittext(k, "|")
		if(map[l]) l = "[l] - [kp[1]]"
		opts += l
		map[l] = k
	if(!length(opts))
		RemasterNotice("Your [n] selected have nothing to do from Interact here.")
		rm_gi_busy = 0
		return
	opts += "Cancel"
	rm_gi_asked++
	var/ans
	if(rm_gi_test)
		rm_gi_test_opts = opts.Copy()
		for(var/o in opts) if(rm_gi_test_answer && findtext(o, "[rm_gi_test_answer]") == 1) ans = o
	else if(client && remaster_hud_ready) ans = RemasterAsk("Have your [n] units interact how?", "Interact - the number is how many of them can", opts, "group")   // AskCard.dm; "group": long choices wrap
	else ans = RemasterChoose(src, "Have your [n] units interact how?", "Interact", opts)
	usr = src
	if(!ans || ans == "Cancel" || !map[ans])
		rm_gi_busy = 0
		return
	var/list/K = splittext(map[ans], "|")
	var/menu = K[1]
	var/what = K[2]
	var/done = 0
	var/skipped = 0
	var/first = 1
	rm_gi_follow = null
	state = list(world.time, 0, 0)
	for(var/mob/Monsters/M in units)
		RmGiWait(state)
		usr = src
		if(!M || !RemasterInteractActor(M) || M.HP <= 0)
			skipped++
			continue
		var/t0 = world.tick_usage
		var/w0 = world.time
		var/entry
		for(var/list/A in RemasterAbilities(M)) if(A[1] == menu && (menu == "Closest Creature" ? findtext("[A[2]]", what) == 1 : A[2] == what))
			entry = A[2]
			break
		if(!entry) skipped++
		else
			RmGiRun(M, menu, entry, first)
			done++
			if(first)
				first = 0
				if(rm_gi_follow && (("Cancel" in rm_gi_follow) || (null in rm_gi_follow)))   // the first one's follow-up was cancelled: the rest too
					skipped += n - done - skipped
					break
		RmGiCharge(state, t0, w0)
	rm_gi_tick_max = max(rm_gi_tick_max, state[3])
	rm_gi_follow = null
	RemasterNotice("[RmGiWhat(map[ans])]: done for [done][skipped ? "; [skipped] couldn't" : ""].")
	rm_gi_busy = 0

// One unit through the original menu with the answers ready (as Abilities.dm RemasterUseAbility). The first unit asks
// any question after them as usual, and its answers are kept (RemasterActionChoice below) for the others.
Player/proc/RmGiRun(mob/Monsters/M, menu, entry, first)
	var/list/old = Selected
	var/oldusr = usr
	Selected = list(M)
	remaster_preset_choices = list(menu, entry)
	if(!first && rm_gi_follow) remaster_preset_choices += rm_gi_follow
	remaster_preset_then_ask = first
	remaster_preset_sticky = menu == "Closest Creature"
	remaster_preset_asked = 0
	remaster_preset_record = 0
	if(first) rm_gi_follow = list()
	usr = src
	try
		Interact()
	catch(var/exception/E)
		world.log << "Remastered: group interact failed: [E]"
	remaster_preset_choices = null
	remaster_preset_then_ask = 0
	remaster_preset_sticky = 0
	if(first && !length(rm_gi_follow)) rm_gi_follow = null
	Selected = old
	usr = oldusr
	M.remaster_abilities_at = -1000   // its list may change (Fly -> Land, mist...)

// The first unit's questions after the ready answers, kept for the rest of the group (asked for real: no answers left).
Player/RemasterActionChoice(message, title, list/options, default = null)
	. = ..()
	if(rm_gi_busy && islist(rm_gi_follow) && isnull(remaster_preset_choices)) rm_gi_follow += list(.)
