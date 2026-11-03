// Comfort: undo, Save now with a "saved ... ago" indicator.

// --- Undo (Ctrl+Z or the top bar): the last plan or order -----------------------
Player/var/tmp/list/remaster_undo            // newest last, at most 10

Player/proc/RemasterUndoPush(list/E)
	if(!remaster_undo) remaster_undo = list()
	remaster_undo += list(E)
	while(length(remaster_undo) > 10) remaster_undo.Cut(1, 2)

Player/proc/RemasterUndo()
	if(!length(remaster_undo))
		RemasterNotice("Nothing to undo.")
		return 0
	var/list/E = remaster_undo[length(remaster_undo)]
	remaster_undo.Cut(length(remaster_undo))
	switch(E["type"])
		if("blueprints")
			var/n = 0
			var/list/keys = E["keys"]
			if(remaster_blueprints) for(var/list/B in remaster_blueprints.Copy())
				if(("[B["x"]],[B["y"]],[B["z"]]" in keys))
					remaster_blueprints -= list(B)
					n++
			RemasterNotice(n ? "Undone: [n] planned tile[n == 1 ? "" : "s"] removed." : "Those plans were already built.")
			return n
		if("order")
			var/n = 0
			var/list/pairs = E["pairs"]
			// Orders are remembered by reference text (holding them would keep
			// finished orders alive); kind and target must match too.
			for(var/list/PR in pairs)
				var/mob/Monsters/M = PR[1]
				if(!M || M.Owner != src) continue
				var/datum/remaster_order/O
				for(var/datum/remaster_order/X in M.remaster_orders) if("\ref[X]" == PR[2] && X.kind == PR[3] && "\ref[X.target]" == PR[4]) O = X
				if(O)
					M.remaster_orders -= O
					n++
				else if(M.remaster_active && "\ref[M.remaster_active]" == PR[2] && M.remaster_active.kind == PR[3] && "\ref[M.remaster_active.target]" == PR[4])
					M.RemasterCancelOrders()
					n++
			RemasterNotice(n ? "Undone: the last order for [n] unit[n == 1 ? "" : "s"]." : "That order already finished.")
			return n
	return 0

Player/verb/RemasterUndoVerb()
	set name = "Remaster-Undo"
	set hidden = 1
	RemasterUndo()

// --- Saving -------------------------------------------------------------------------
var/list/remaster_last_save                  // RemasterNow() at the last complete save (Away.dm)
var/remaster_save_ready_at = 0

// No save while a unit is down (fixes plan 10-27, 6): the dying and knock-out clocks aren't saved and LoadUnits()
// stands every unit up, so a unit caught dying or out cold would come back standing. Save Now refuses; the
// autosave (Saves.dm CallSave) looks again every 10 s and saves anyway after about 3 minutes, so a long battle
// can't stop saving for good. The save itself is unchanged.
#define RM_SAVE_WAIT_STEP 100
#define RM_SAVE_WAIT_MAX 1800

// The first of this player's units that is dying or knocked out, else null.
Player/proc/RmSaveDownUnit()
	for(var/mob/Monsters/M in UnitList) if(M.rm_dying_until || M.RemasterKnockedOut()) return M
	return null

// Waits while any player SaveUnits() writes has a unit down; returns the ticks waited.
proc/RmSaveWaitDown()
	var/waited = 0
	while(waited < RM_SAVE_WAIT_MAX)
		var/down = 0
		for(var/Player/P in world) if(P.key && P.RmSaveDownUnit())
			down = 1
			break
		if(!down) break
		sleep(RM_SAVE_WAIT_STEP)
		waited += RM_SAVE_WAIT_STEP
	return waited

Player/proc/RemasterSaveNow()
	if(RmPublicWorld() && !RmModLevel())   // a public server saves itself (its autosave); staff may still save
		RemasterNotice("This world saves itself.")
		return 0
	if(world.time < remaster_save_ready_at)
		RemasterNotice("Saved a moment ago.")
		return 0
	var/mob/Monsters/D = RmSaveDownUnit()
	if(D)
		RemasterNotice("Can't save while [D.RemasterBareName()] is down.")
		return 0
	remaster_save_ready_at = world.time + 300
	RemasterNotice("Saving...")
	spawn() RmSaveNowSpread(src)   // the scan over a few ticks, then "Game saved." (WorldSave.dm; spike hunt, 10-31)
	return 1

proc/RemasterSaveAgo()
	var/t = RemasterSince(remaster_last_save)
	return isnull(t) ? -1 : max(0, round(t / 10))
