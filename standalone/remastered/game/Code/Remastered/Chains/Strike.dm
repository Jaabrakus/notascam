// mob/RemasterStrike: one chain, in the order DM ran it when it was spread over 8 files (cleanup, from
// chains.py). The call runs Morale > Facing > NPCLevels > Chat > Wounds > Blunt > HalfDemons > Hits: each step below calls the next one down where it used to call ..().
// Add a feature's part as a new step at its place in this order, never as another override elsewhere.
mob/proc/RemasterStrike(mob/M, kind_hint)
	return RmChainStrike_Morale(arglist(args))

// step 1 of 8: Morale (was Code/Remastered/Morale.dm:256)
// Blows: struck or taken puts both in combat; what the blow did moves morale; a routing NPC strikes none.
mob/proc/RmChainStrike_Morale(mob/M, kind_hint)
	if(!rm_morale_on || !istype(src, /mob/Monsters) || !istype(M, /mob/Monsters)) return RmChainStrike_Facing(arglist(args))
	var/mob/Monsters/A = src
	var/mob/Monsters/V = M
	if(A.rm_rout_until > world.time) return 0
	A.RmMoraleFight()
	V.RmMoraleFight()
	// no blow can come of this call (the swing timer, Hits.dm RmSwingWaits; nothing seeded on the way, no facing turn): V can't
	// change, so there is nothing to measure (combat-speed, 10-26)
	var/waits = !rm_facing_on && A.RmSeedDone() && V.RmSeedDone() && A.RmSwingWaits(V, kind_hint)
	var/h0 = waits ? 0 : RemasterBodyHealth(V)
	var/c0 = A.rm_crits
	var/k0 = V.rm_crushes
	var/list/had = waits ? null : RmLimbsHad(V)
	var/vn = V.RemasterBareName()
	. = RmChainStrike_Facing(arglist(args))
	if(isnull(A.rm_morale)) return
	var/an = A.RemasterBareName()
	if(Rm3DGone(V) || V.HP <= 0 || V.GoingToDie)
		if(A.rm_mstate == -2) A.RmMoraleAdd(rm_second_wind, 0, ": a second wind")
		A.RmMoraleShare(list("kill"), list("kill"), null, list(), " after killing [vn]", ": [an] killed [vn]")   // the victim's own lose theirs as it falls (Death below)
		return
	if(waits) return   // nothing struck: no hit, critical, crush or limb to count
	var/list/me = list()
	var/list/mine = list()
	var/list/theirs = list()
	var/why_me
	var/why_mine
	var/why_theirs
	if(RemasterBodyHealth(V) < h0)
		me += "hit"
		if(rm_morale_group && rm_cover_on)   // a covering blow: the foe it struck was set on a Shaken or Broken one of its own
			var/mob/Monsters/X = V.remaster_attack ? V.remaster_attack.target : V.Target
			if(istype(X) && X != A && X.Owner == A.Owner && !isnull(X.rm_morale) && X.rm_mstate < 0)
				X.RmMoraleAdd(rm_cover_gain, 1, ": covered by [an]")
				RemasterHit(X, 0, "cover", A)
				A.rm_covers++
				A.rm_committed_until = world.time + rm_commit_time
		if(rm_morale_shakeoff && A.rm_morale_g < 0)   // it shakes off the group's fear with a blow of its own
			var/s0 = A.rm_mstate
			A.rm_morale_g = 0
			A.RmMoraleSum()
			A.rm_morale_why = ""
			A.RmMoraleState()
			if(s0 && !A.rm_mstate) A.RmMoraleLog("shook")
	if(A.rm_crits > c0)
		me += "crit"
		mine += "crit"
		why_me = " after a critical on [vn]"
		why_mine = ": [an] struck [vn] hard"
		if(A.rm_mstate == -2) A.RmMoraleAdd(rm_second_wind, 0, ": a second wind")
	if(V.rm_crushes > k0)
		me += "crush"
		mine += "crush"
		theirs += "crush"
		why_me = " after crushing [vn]'s limb"
		why_mine = ": [an] crushed [vn]'s limb"
		why_theirs = ": [vn]'s limb was crushed beside them"
	var/list/lost = had - RmLimbsHad(V)
	if(length(lost))
		var/what = rm_limb_names[lost[1]]
		var/limb = copytext(what, findtext(what, " ") + 1)
		me += "sever"
		mine += "sever"
		theirs += "sever"
		why_me = " after taking [vn]'s [limb]"
		why_mine = ": [an] took [vn]'s [limb]"
		why_theirs = ": [vn] lost [what] beside them"
		V.RmMoraleAdd(-(length(had) < 4 ? rm_shock / 2 : rm_shock), 0, ": lost [what]")   // shock (half for one that had lost a limb before)
	if(length(me)) A.RmMoraleShare(me, mine, V, theirs, why_me, why_mine, why_theirs)

// step 2 of 8: Facing (was Code/Remastered/Facing.dm:111)
mob/proc/RmChainStrike_Facing(mob/M, kind_hint)
	if(!rm_facing_on || !istype(M, /mob/Monsters)) return RmChainStrike_NPCLevels(arglist(args))
	var/was = rm_arc
	var/was_left = rm_arc_left
	if(istype(src, /mob/Monsters)) src:RmTurnToward(get_dir(src, M))
	M:rm_hit_at = world.time
	var/charge = 0
	if(rm_charge_on && istype(src, /mob/Monsters) && src:rm_run_steps >= rm_charge_steps && world.time - src:rm_step_at <= rm_charge_window && world.time - max(rm_swung_at, src:rm_hit_at) > rm_charge_fresh && get_dist(locate(src:rm_run_x, src:rm_run_y, z), M) - get_dist(src, M) >= rm_charge_steps)
		charge = 1   // a charge: its first blow, and its sides covered a moment
		src:rm_run_steps = 0
		src:rm_charge_until = world.time + rm_charge_cover
		rm_charges++
		RemasterHit(src, 0, "charge", M)
	var/was_charge = rm_charge_blow
	rm_charge_blow = charge
	rm_arc_left = 0
	rm_arc = RmArc(src, M)
	if(rm_arc && M:RmAware(src, rm_arc))   // it turns to meet it in time: as from the front
		rm_arc = 0
		M:rm_turns++
		RemasterHit(M, 0, "turned", src)
	var/h0 = rm_arc ? RemasterBodyHealth(M) : 0
	. = RmChainStrike_NPCLevels(arglist(args))
	if(rm_arc && !Rm3DGone(M) && RemasterBodyHealth(M) < h0)
		rm_flanks++
		M:RmMoraleAdd(rm_arc == 2 ? -rm_morale_rear : -rm_morale_side, 0, rm_arc == 2 ? ": struck from behind" : ": struck from the side")   // its morale (Morale.dm)
		RemasterHit(M, 0, rm_arc == 2 ? "rear" : "flank", src)
	rm_arc = was
	rm_arc_left = was_left
	rm_charge_blow = was_charge

// step 3 of 8: NPCLevels (was Code/Remastered/NPCLevels.dm:49)
mob/proc/RmChainStrike_NPCLevels(mob/M, kind_hint)
	if(istype(src, /mob/Monsters) && !src:remaster_combat_seeded) src:RmSeedNPC()
	if(istype(M, /mob/Monsters) && !M:remaster_combat_seeded) M:RmSeedNPC()
	return RmChainStrike_Chat(arglist(args))

// step 4 of 8: Chat (was Code/Remastered/Chat.dm:78)
mob/proc/RmChainStrike_Chat(mob/M, kind_hint)
	if(!istype(M, /mob/Monsters) || RmSwingWaits(M, kind_hint)) return RmChainStrike_Wounds(arglist(args))   // no blow (Hits.dm): no limb can change
	var/list/before = list()
	for(var/part in rm_limb_parts) before[part] = RmLimbRank(M, part)
	. = RmChainStrike_Wounds(arglist(args))
	if(!M) return
	for(var/part in rm_limb_parts)
		var/r = RmLimbRank(M, part)
		if(r <= before[part]) continue
		var/line = r == 4 ? "[RmChatName(src)] cuts off [RmChatName(M)]'s [rm_limb_parts[part]]!" : "[RmChatName(src)] [rm_limb_verbs[r]] [RmChatName(M)]'s [rm_limb_parts[part]]!"
		M.RmLimbSay(src, line)

// step 5 of 8: Wounds (was Code/Remastered/Wounds.dm:54)
mob/proc/RmChainStrike_Wounds(mob/M, kind_hint)
	var/mob/Monsters/T = rm_wound_formula && istype(M, /mob/Monsters) ? M : null
	if(!T || T.rm_wound_in || !T.HumanParts || T.HP <= 0 || T.GoingToDie || RmSwingWaits(M, kind_hint)) return RmChainStrike_Blunt(arglist(args))   // no blow (Hits.dm): no blood to reckon
	var/blood = T.BloodContent
	var/list/before = list()
	for(var/v in rm_wound_parts) before += T.vars[v]
	T.rm_wound_in = 1
	. = RmChainStrike_Blunt(arglist(args))
	if(Rm3DGone(T)) return   // deleted in the blow (a deleted ref isn't null)
	T.rm_wound_in = 0
	if(T.HP <= 0 || T.GoingToDie || DamageType == "Blunt") return
	if(blood - T.BloodContent <= 0) return   // nothing bled (no blood to lose, or the blow missed)
	T.BloodContent = blood - RmWoundBlood(T, before)
	T.RemasterStumpBleedLevel()
	if(rm_sever_on && DamageType == "Slashing") RmSeverRoll(T, before, src)

// step 6 of 8: Blunt (was Code/Remastered/Blunt.dm:35)
mob/proc/RmChainStrike_Blunt(mob/M, kind_hint)
	rm_blunt_parts = null
	var/mob/Monsters/T = istype(M, /mob/Monsters) ? M : null
	var/before = T && !RmSwingWaits(M, kind_hint) ? RemasterBodyHealth(T) : 0   // no blow (Hits.dm): no blunt parts come back, so before is never read
	. = RmChainStrike_HalfDemons(arglist(args))
	var/list/parts = rm_blunt_parts
	rm_blunt_parts = null
	if(!rm_blunt_mode || !parts || !T || !T.loc || !T.HumanParts || T.HP <= 0 || T.GoingToDie) return
	var/want = 0
	for(var/part in parts) want += max(min(rm_blunt_dmg, 5), rm_blunt_dmg * RemasterArmourFactor(src, T, part))
	var/rest = round(want - (before - RemasterBodyHealth(T)))
	if(rest < 1) return
	var/fists = RemasterWeaponClass(src) == "fist"
	if(rm_blunt_mode == 2 && fists && !T.RemasterKnockedOut() && !RemasterTooBigToKO(T) && T.HP - rest <= T.MAXHP * RM_KO_MARK)
		T.HP = max(1, T.HP - rest)
		T.RemasterKnockOut(src)
		return
	T.HP -= rest
	RemasterHit(T, rest, "crush", src)
	if(T.HP > 0) return
	T.GoingToDie = 1
	T.DeathType = fists ? "Beaten to death" : "Crushed by blows"
	T.Killer = src
	T.Death()

// step 7 of 8: HalfDemons (was Code/Remastered/HalfDemons.dm:211)
// An Ashen's blows may set its foe alight.
mob/proc/RmChainStrike_HalfDemons(mob/M, kind_hint)
	. = RmChainStrike_Hits(arglist(args))
	if(!.) return   // no blow this time (Hits.dm swing timer)
	if(SubRace == "Ashen" && istype(M, /mob/Monsters) && M.HP > 0 && prob(15)) spawn(0) RmBurn(M, 2, 0.04)

// step 8 of 8: Hits (was Code/Remastered/Hits.dm:86)
// The original melee strike (Combats.dm calls this instead of Attack directly). Returns 1 when a blow was made,
// 0 while its weapon is still coming round (a dagger's second stab and an axe's cleave are the same swing).
mob/proc/RmChainStrike_Hits(mob/M, kind_hint)
	if(!M) return 0
	if(!(kind_hint in rm_swing_free) && !rm_move_sure)   // a weapon move's blow keeps no swing timer (WeaponSkills.dm); RmSwingWaits above reads the same
		if(world.time < rm_swing_at) return 0
		rm_swing_at = world.time + RmSwingTicks(src)
		rm_swung_at = world.time
		// a weapon move that is ready goes instead of the plain blow (WeaponSkills.dm)
		if(!kind_hint && istype(src, /mob/Monsters) && istype(M, /mob/Monsters) && src:RmAutoMove(M)) return 1
	. = 1
	var/w = RemasterWeaponClass(src)
	// Riposte (WeaponSkills.dm): every blow at it is parried and struck back while it lasts
	if(!remaster_striking && istype(M, /mob/Monsters) && M:rm_riposte_until > world.time && !(istype(src, /mob/Monsters) && src:rm_riposting) && RemasterCanParry(M) && M.HP > 0)
		RemasterHit(M, 0, "parry", src)
		var/mob/Monsters/R = M
		R.rm_riposting = 1
		if(istype(src, /mob/Monsters)) R.RmMoveBlow(src, 1)   // struck back: a move's blow, sure to land (WeaponSkills.dm)
		R.rm_riposting = 0
		return
	// a sword parries: no blow lands. Like the dodge, half from its side and none from behind (RmArcDodge, the arc of this
	// blow: Facing.dm; the user, 2026-10-26: "Like dodge")
	if(!remaster_striking && RemasterWeaponClass(M) == "sword" && RemasterCanParry(M) && !M.Stunned && !M.Fainted && M.HP > 0 && prob(min(30, 6 + M.SwordSkill / 8) * RmArcDodge()))
		RemasterHit(M, 0, "parry", src)
		return
	// non-lethal (the toggle, or a Capture order): a subdue blow instead (Subdue.dm)
	if(istype(src, /mob/Monsters) && istype(M, /mob/Monsters) && src:RemasterFightsNonLethal(M)) return src:RemasterSubdueBlow(M)
	var/before = RemasterBodyHealth(M)
	var/alive = M.HP > 0 && !M.GoingToDie
	Attack(M)
	if(!M || !M.loc) return
	var/d = round(before - RemasterBodyHealth(M))
	var/kind = d > 0 ? (kind_hint || (w == "mace" ? "crush" : "hit")) : "miss"
	if(alive && (M.HP <= 0 || M.GoingToDie)) kind = "kill"
	remaster_opening = d > 0 ? 0 : min(remaster_opening + 1, 12)
	if(d > 0 && istype(src, /mob/Monsters)) src:RemasterCombatXP("melee", d)
	RemasterHit(M, max(0, d), kind, src)
	if(remaster_striking || d <= 0 || !alive) return
	remaster_striking = 1
	switch(w)
		if("mace")
			if(prob(12) && !M.Stunned && M.HP > 0)
				M.Stunned = 1
				spawn(15) if(M) M.Stunned = 0
				RemasterHit(M, 0, "stagger", src)
		if("axe")
			// the swing carries on into a foe beside the wielder or the target
			if(prob(60)) for(var/mob/Monsters/O in (orange(1, src) | orange(1, M))) if(O != M && O != src && istype(src, /mob/Monsters) && !RemasterIsSiege(O) && RemasterHostile(src, O))
				RemasterStrike(O, "cleave")
				break
		if("dagger")
			if(M.HP > 0 && ("BloodContent" in M.vars))
				M.BloodContent -= 4
				M.BloodLoss()
				RemasterHit(M, 0, "bleed", src)
			if(prob(35) && M && M.HP > 0) RemasterStrike(M, "double")
	if(M && M.HP > 0) RmWeaponEffect(M, d)   // a beast's weapon, a staff, an enchanted blade: their effects (BeastParts.dm, MagicGear.dm)
	remaster_striking = 0
