mob/var
	savedx = 0
	savedy = 0
	savedz = 0
Admin/verb/SaveUnitsInWorld()
	set category="Admin"
	SaveUnits()
	world << "[usr] has saved units."
/proc/CallSave()
	spawn(9500)
		CallSave()
		RmSaveWaitDown()   // Remastered: never while a unit is dying or knocked out, at most ~3 min (Comfort.dm)
		world << "<font size=4>Units Saving"
		sleep(5)
		RmSaveUnitsSpread()   // Remastered: the scan spread over ticks, the writing in one (WorldSave.dm; spike hunt, 10-31)
/proc/SaveUnits(list/turfs)   // Remastered: turfs, the changed tiles' records when the spread save made them
	RemasterSaveWorld(turfs) // Remastered: built and dug world changes, workshops, stockpiles, calendar.
	var/list/saved = list()   // Remastered: the companies saved, for the launcher's world list (WorldSave.dm RmWorldInfo)
	for(var/mob/M in world) if(M.key && (!RmGuestKey(M.key) || M.RmGuestBrowserKept()))   // Remastered: never a guest, but a village its browser keeps (Guests.dm)
		if(!RmGuestKey(M.key)) saved += M   // the world list's facts: accounts only
		var/sav = M.RmUnitsSave()   // Remastered: units/<ckey>_save.sav, or the browser keep's (Guests.dm)
		var/savefile/S
		if(turfs)   // Remastered: the spread save's: a fresh file in its place (the old save never read in), written off
			S = new(sav + ".new")   // the game thread to sav (WorldSave.dm); an engine without that: saved at once, as before
			try
				S.rm_later = sav
			catch
				S = new(sav)
		else S = new(sav)
		M.savedx = M.x
		M.savedy = M.y
		M.savedz = M.z
		for(var/mob/X in M.UnitList)
			X.savedx = X.x
			X.savedy = X.y
			X.savedz = X.z
		M.Write(S)
	RmWorldInfo(saved)

mob/proc/LoadUnits() if(fexists(RmUnitsSave()))   // Remastered: units/<ckey>_save.sav, or a browser-kept guest's (Guests.dm)
	var/sav = RmUnitsSave()
	var/savefile/S = new(sav)
	Read(S)
	if(!isobj(loc))
		x = savedx
		y = savedy
		z = savedz
	Loaded = 1
	density = 0
	Selected = list()
	if(client) client.images = null   // Remastered: no client in a windowless check (tests/guest_keep_check.dm)
	if(IsClanLeader == 1) verbs+=typesof(/Clan/verb)
	var/In = 0
	if(usr in PlayerList) In = 1
	if(In == 0) PlayerList += usr
	for(var/mob/Monsters/K in UnitList)
		for(var/mob/CK in K) CK.Owner = usr
		// Saved contents already restore units held in an object or mob.
		// Applying world coordinates here would pull them out of that container.
		if(!isobj(K.loc) && !ismob(K.loc))
			K.x = K.savedx
			K.y = K.savedy
			K.z = K.savedz
		// Dropped cages are outside the original player save graph.
		// Restore release flags only when no saved container survived.
		if(K.Caged && isturf(K.loc))
			K.Caged = 0
			var/in_live_pit = 0
			for(var/obj/Items/Traps/PitTrap/P in K.loc)
				if(P.HasPersonIn) in_live_pit = 1
			if(!in_live_pit) K.InHole = 0
		K.Owner = usr
		if(K.Meditating)
			K.Meditating = 0
			K.CanWalk = 1
		K.CoolDown = 0
		K.Sleeping = 0
		K.Stunned = 0
		K.Fainted = 0
		K.HomeLoc = null
		K.Target = null
		if(K.HasRightLeg == 1 && K.HasLeftLeg == 1) K.CanWalk = 1
		if(K.Race=="Devourer") K.CanWalk = 1
		K.RebuildOverlays()
		if(K.Race == "Vampire") if(K.y == 1 || K.y == 3) K.y = 2
		var/image/I = new('mob.dmi',K)
		K.Star = I
		K.LimbLoss()
	return(1)