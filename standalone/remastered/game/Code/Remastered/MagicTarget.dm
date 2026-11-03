// Magic targeting is separate from destination, bow Target and casting.
// The chooser captures actors and a view; choosing only assigns MagicTarget.
datum/remaster_magic_target
	var/list/actors = list()
	var/actor_count = 0
	var/list/actor_tokens = list()
	var/list/actor_states = list()
	var/list/targets = list()
	var/list/target_states = list()
	var/turf/camera
	var/view_size
	var/reach = 0   // the 3D right-click's: anyone within this many tiles (View3D.dm REMASTER_3D_REACH), not only view()'s 9

Player/var/tmp/datum/remaster_magic_target/remaster_magic_target

Player/proc/RemasterMagicTargetReason()
	if(!(/Targeting/verb/SetTarget in verbs)) return "Magic targeting is unavailable."
	if(!length(Selected)) return "Select a unit first."
	// the selection's units all yours, in the company and alive (HudView.dm, once a tick: 30,000 selected)
	return RmSelectionCheck() ? "" : "Select your own living units."

Player/proc/RemasterMagicViewSize()
	return client ? client.view : world.view

// OpenDream view() includes hidden movables. Match the observer mob's
// visibility threshold explicitly and exclude carried/contained creatures.
Player/proc/RemasterMagicVisible(mob/Monsters/T)
	return T && isturf(T.loc) && T.HP > 0 && !T.GoingToDie && T.invisibility <= see_invisible

Player/proc/RemasterMagicTargetCapture(reach = 0)
	if(length(RemasterMagicTargetReason())) return null
	var/datum/remaster_magic_target/D = new
	D.camera = loc
	D.view_size = RemasterMagicViewSize()
	D.reach = reach
	for(var/mob/Monsters/M in Selected)
		D.actors += M
		D.actor_count++
		D.actor_tokens += RemasterUIRef(M)
		D.actor_states[M] = list("ref"=RemasterUIRef(M), "race"=M.Race, "subrace"=M.SubRace, "mist"=M.IsMist)
	// Preserve original SetTarget's view-based scope and friendly/self targets.
	// Death/deletion cannot leave a selectable replacement object behind.
	for(var/mob/Monsters/T in (reach ? range(reach, src) : view(src)))
		if(!RemasterMagicVisible(T)) continue
		var/reference = RemasterUIRef(T)
		D.targets[reference] = T
		D.target_states[reference] = list("owner"=T.Owner, "race"=T.Race, "subrace"=T.SubRace)
	return D

Player/proc/RemasterMagicSessionReason(datum/remaster_magic_target/D)
	if(!D) return "Magic target chooser is closed."
	var/reason = RemasterMagicTargetReason()
	if(length(reason)) return reason
	if(loc != D.camera || RemasterMagicViewSize() != D.view_size) return "View changed; reopen the magic target chooser."
	if(length(Selected) != D.actor_count || length(D.actors) != D.actor_count) return "Selection changed; reopen the magic target chooser."
	// Deleted mob entries can remain null slots in DM lists. Iterate the
	// original token strings so a missing actor cannot silently be skipped.
	for(var/reference in D.actor_tokens)
		var/mob/Monsters/M = RemasterUIUnit(reference)
		if(!M || !(M in Selected)) return "Selection changed; reopen the magic target chooser."
		var/list/state = D.actor_states[M]
		if(!state || M.Race != state["race"] || M.SubRace != state["subrace"] || M.IsMist != state["mist"]) return "Selection changed; reopen the magic target chooser."
	return ""

Player/proc/RemasterMagicCandidateReason(datum/remaster_magic_target/D, mob/Monsters/T)
	if(!D || !RemasterMagicVisible(T) || !(D.reach ? get_dist(src, T) <= D.reach : (T in view(src)))) return "Target is no longer visible."
	var/reference = T.remaster_ui_id
	if(!reference || D.targets[reference] != T) return "Target is no longer available."
	var/list/state = D.target_states[reference]
	if(!state || T.Owner != state["owner"] || T.Race != state["race"] || T.SubRace != state["subrace"]) return "Target changed; reopen the magic target chooser."
	return ""

Player/proc/RemasterApplyMagicTarget(datum/remaster_magic_target/D, mob/Monsters/T)
	var/reason = RemasterMagicSessionReason(D)
	if(!length(reason)) reason = RemasterMagicCandidateReason(D, T)
	if(length(reason))
		RemasterNotice(reason)
		return 0
	// Original SetTarget's effect only. No handoff, movement, attack or casting.
	for(var/mob/Monsters/M in D.actors)
		M.MagicTarget = T
		src << "[M] is now targeting [T]"
	return 1

Player/proc/RemasterNativeMagicTarget(mob/Monsters/T, reach = 0)
	usr = src
	var/datum/remaster_magic_target/D = RemasterMagicTargetCapture(reach)
	if(!D)   // nothing (of yours) selected: say so, not "chooser is closed"
		RemasterNotice(RemasterMagicTargetReason())
		return 0
	var/assigned = RemasterApplyMagicTarget(D, T)
	if(assigned) remaster_magic_target = null
	return assigned

Player/proc/RemasterMagicTargetOpen()
	var/reason = RemasterMagicTargetReason()
	if(length(reason))
		RemasterNotice(reason)
		return 0
	// Placement and a target chooser cannot own the next interaction together.
	// Cancelling placement affects no unit work or assigned magic targets.
	RemasterCancelPlacement()
	remaster_magic_target = RemasterMagicTargetCapture()
	RemasterUIRef(remaster_magic_target)
	RemasterNotice("Choose a magic target. This does not cast or interrupt work.")
	return 1

Player/proc/RemasterMagicTargetData()
	if(remaster_magic_target && (Up || Function)) remaster_magic_target = null
	var/datum/remaster_magic_target/D = remaster_magic_target
	if(!D) return list("open"=0, "session"="", "reason"="", "actors"=list(), "entries"=list())
	var/list/entries = list()
	var/list/actors = list()
	var/reason = RemasterMagicSessionReason(D)
	for(var/mob/Monsters/M in D.actors) actors += "[M.name]"
	var/list/visible = view(src)
	for(var/reference in D.targets)
		var/mob/Monsters/T = D.targets[reference]
		if(!RemasterMagicVisible(T) || !(T in visible)) continue
		entries += list(list("ref"=reference, "label"="[T.name]", "race"=T.Race, "x"=T.x, "y"=T.y, "z"=T.z, "reason"=(length(reason) ? reason : RemasterMagicCandidateReason(D, T))))
	if(!length(entries) && !length(reason)) reason = "No creatures from this chooser are visible. Close and reopen to refresh."
	return list("open"=1, "session"=RemasterUIRef(D), "reason"=reason, "actors"=actors, "entries"=entries)

Player/proc/RemasterMagicTargetChoose(value)
	if(!istext(value)) return 0
	var/list/parts = splittext(value, "|")
	var/datum/remaster_magic_target/D = remaster_magic_target
	if(!D || parts.len != 2 || parts[1] != D.remaster_ui_id) return 0
	if(Up || Function)
		remaster_magic_target = null
		return 0
	var/mob/Monsters/T = D.targets[parts[2]]
	if(!RemasterApplyMagicTarget(D, T)) return 0
	remaster_magic_target = null
	RemasterNotice("Magic target: [T.name]. Now cast the ability as usual; its range and costs still apply.")
	return 1

Player/proc/RemasterMagicTargetClose(session)
	if(!remaster_magic_target || session != remaster_magic_target.remaster_ui_id) return 0
	remaster_magic_target = null
	RemasterNotice("Magic target chooser closed. Assigned work continues.")
	return 1
