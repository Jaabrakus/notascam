// Hero or Village play (planning/VILLAGE_LIFE.md). Same game either way; the
// mode only changes what the HUD puts first.
// Hero: one character is "you". The hero frame shows them when nothing else is
// selected, the Units tab opens first and the camera can follow them.
// Village: the Village tab opens first and the frame shows the settlement.

Player/var
	remaster_play_mode = "village"
	remaster_hero_uid               // lineage id of the chosen hero
Player/var/tmp/remaster_follow = 0
// Camera lock: follow any one of your units (its UI ref, not the mob, so the
// unit can still be recycled). Works in 2D and 3D, in either play mode.
Player/var/tmp/remaster_lock
Player/var/tmp/turf/remaster_lock_at   // where the locked unit was: the view moves as far as it moves

// The chosen hero, or the ruler, or the first living unit.
Player/proc/RemasterHero()
	var/mob/Monsters/best
	for(var/mob/Monsters/M in UnitList)
		if(M.Owner != src || M.HP <= 0) continue
		if(remaster_hero_uid && M.remaster_uid == remaster_hero_uid) return M
		if(!best || (M.IsRoyal && !best.IsRoyal)) best = M
	return best

Player/proc/RemasterPlayModeTick()
	if(remaster_lock)
		var/mob/Monsters/L = RemasterUIUnit(remaster_lock)
		if(!istype(L) || L.Owner != src || L.HP <= 0 || !(L in UnitList))
			remaster_lock = null
			RemasterNotice("Camera lock released: that unit is gone.")
		else
			// The view follows the unit and stays free: it moves as far as the unit moves, so a pan
			// (the page's camera command) keeps its offset; onto the unit when it changes level.
			if(isturf(L.loc) && L.loc != remaster_lock_at)
				var/turf/W = remaster_lock_at
				var/lz = RmViewLayer(L)      // up on an ordinary mountain the view stays on the Surface (Peaks.dm)
				if(!W || W.z != L.z || z != lz) loc = locate(L.x, L.y, lz)
				else loc = locate(clamp(x + L.x - W.x, 1, world.maxx), clamp(y + L.y - W.y, 1, world.maxy), z)
				remaster_lock_at = L.loc
			return
	if(remaster_play_mode != "hero" || !remaster_follow) return
	var/mob/Monsters/H = RemasterHero()
	var/turf/T = (H && isturf(H.loc)) ? H.loc : null
	if(T && loc != T) loc = T

Player/proc/RemasterPlayModeCommand(action, value)
	switch(action)
		if("playmode")
			// Remastered is always played as the village (Hero mode was removed).
			if(value != "village") return 0
			remaster_play_mode = value
			remaster_hud_tab = value == "hero" ? "units" : "village"
			if(value != "hero") remaster_follow = 0
			var/mob/Monsters/H = RemasterHero()
			if(H && value == "hero")
				if(!H.remaster_uid) H.RemasterLineageEnsure(src)
				remaster_hero_uid = H.remaster_uid
			RemasterNotice(value == "hero" ? "Hero mode: you are [H ? H.name : "your first unit"]. The village keeps working on its own." : "Village mode: manage everyone from the Village tab.")
			return 1
		if("makehero")   // Hidden Clans: the ninja you play (Drive.dm); Banners had it off since Hero mode went
			var/mob/Monsters/M = RemasterUIUnit(value)
			if(!istype(M) || M.Owner != src) return 0
			if(!M.remaster_uid) M.RemasterLineageEnsure(src)
			if(M.remaster_uid == remaster_heir_uid) remaster_heir_uid = null
			remaster_hero_uid = M.remaster_uid
			RemasterNotice("[M.name] is now your hero.")
			return 1
		// Chase button: free the camera if it follows someone, else lock on the one
		// selected unit, else on the hero (or leader).
		if("chasecam")
			if(remaster_lock || remaster_follow)
				remaster_lock = null
				remaster_follow = 0
				RemasterNotice("Camera free.")
				return 1
			var/mob/Monsters/pick
			var/n = 0
			for(var/mob/Monsters/M in Selected) if(M.Owner == src)
				pick = M
				n++
			if(n != 1) pick = RemasterHero()
			if(!pick) return 0
			return RemasterPlayModeCommand("lockcam", RemasterUIRef(pick))
		if("lockcam")
			if(!value || value == remaster_lock)
				if(remaster_lock) RemasterNotice("Camera free.")
				remaster_lock = null
				return 1
			var/mob/Monsters/U = RemasterUIUnit(value)
			if(!istype(U) || U.Owner != src) return 0
			remaster_lock = value
			remaster_lock_at = null   // the first tick brings the view onto it
			remaster_follow = 0
			RemasterNotice("The camera follows [U.name]: pan, turn and zoom as you like. F9 or Unlock frees it.")
			return 1
		if("follow")
			remaster_follow = remaster_play_mode == "hero" && !remaster_follow
			if(remaster_follow) remaster_lock = null
			RemasterNotice(remaster_follow ? "The camera follows your hero." : "Camera free.")
			return 1
	return 0

Player/proc/RemasterPlayModeData()
	if(remaster_play_mode != "village")      // saves from when Hero mode existed
		remaster_play_mode = "village"
		remaster_follow = 0
	var/mob/Monsters/H = remaster_play_mode == "hero" ? RemasterHero() : null
	var/mob/Monsters/L = remaster_lock ? RemasterUIUnit(remaster_lock) : null
	return list("mode"=remaster_play_mode, "hero"=(H ? RemasterUIRef(H) : null), "follow"=remaster_follow, "succession"=remaster_succession,
		"lock"=(istype(L) ? remaster_lock : null), "lockName"=(istype(L) ? "[L.name]" : null))

// F9: lock the camera on the one selected unit, or free it.
Player/verb/RemasterLockCameraVerb()
	set name = "Remaster-Lock-Camera"
	set hidden = 1
	RemasterPlayModeCommand("chasecam", "")
