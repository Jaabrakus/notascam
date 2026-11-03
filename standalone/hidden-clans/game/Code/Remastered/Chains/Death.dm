// mob/Monsters/Death: one chain, in the order DM ran it when it was spread over 5 files (cleanup, from
// chains.py). The call runs Falls > Morale > HalfDemons > WeaponSkills > Beasts: each step below calls the next one down where it used to call ..().
// Add a feature's part as a new step at its place in this order, never as another override elsewhere.
var/rm_chain_base_Death   // set by the bottom step for one call: the next Death() on that object goes on with ..()
mob/Monsters/Death()
	if(rm_chain_base_Death == src)   // the bottom step's ..(): the parent type's Death, as the first override's ..() reached
		rm_chain_base_Death = null
		return ..()
	return RmChainDeath_Falls(arglist(args))

// step 1 of 5: Falls (was Code/Remastered/Falls.dm:25)
mob/Monsters/proc/RmChainDeath_Falls()
	if(RmFallSpares(src))
		var/why = DeathType
		GoingToDie = 0
		DeathType = null
		HP = max(HP, 1)
		rm_downed_by = ismob(Killer) && Killer != src ? Killer : rm_fall_at == world.time ? rm_fall_by : null   // named in its fall's lines (BleedOut.dm)
		var/spared = RmBleedOut(src)
		rm_downed_by = null
		if(spared)
			rm_fall_spared++
			RmFallMorale(src)
			return
		GoingToDie = 1
		DeathType = why
	return RmChainDeath_Morale(arglist(args))

// step 2 of 5: Morale (was Code/Remastered/Morale.dm:372)
// One of its own falling near it. (A killing blow is never spared by morale: knock-out or kill is the striker's Lethal
// toggle, Subdue.dm.)
mob/Monsters/proc/RmChainDeath_Morale()
	if(rm_morale_on && rm_morale_group && GoingToDie && isturf(loc) && !rm_fall_spared)   // spared a fall, its own felt it then (Falls.dm)
		var/leader = IsRoyal || (RmNPCRole() in list("commander", "boss"))
		var/n = leader ? rm_morale_loss["leader"] : rm_morale_loss["death"]
		var/nm = RemasterBareName()
		for(var/mob/Monsters/O in RmUnitsNear(leader ? 6 : 4, src)) if(O != src && O.Owner == Owner && !isnull(O.rm_morale))
			O.RmMoraleAdd(-n, 1, ": [nm] fell[leader ? "" : " beside them"]")
	return RmChainDeath_HalfDemons(arglist(args))

// step 3 of 5: HalfDemons (was Code/Remastered/HalfDemons.dm:210)
// --- Gifts and prices ------------------------------------------------------------------
// The Marked feed on what they kill.
mob/Monsters/proc/RmChainDeath_HalfDemons()
	if(GoingToDie && !key && !CantKill && !Wagon && istype(Killer, /mob/Monsters))
		var/mob/Monsters/K = Killer
		if(K.SubRace == "Marked" && K.HP > 0) K.HP = min(K.MAXHP, K.HP + 15)
	return RmChainDeath_WeaponSkills(arglist(args))

// step 4 of 5: WeaponSkills (was Code/Remastered/WeaponSkills.dm:405)
// A move's killing blow keeps the move's name, whatever part it took.
mob/Monsters/proc/RmChainDeath_WeaponSkills()
	if(rm_move_killing) DeathType = rm_move_killing
	return RmChainDeath_Beasts(arglist(args))

// step 5 of 5: Beasts (was Code/Remastered/Beasts.dm:340)
mob/Monsters/proc/RmChainDeath_Beasts()
	if(rm_feet) RmBeastFeetClear(src)
	return RmChainDeath_Base(arglist(args))

// the bottom's ..(): marks src and calls Death() again, so the override above does the parent type's Death
mob/Monsters/proc/RmChainDeath_Base()
	rm_chain_base_Death = src
	return Death(arglist(args))
