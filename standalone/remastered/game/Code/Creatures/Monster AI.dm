#ifndef RM_WILD_TRACE
#define RM_WILD_TRACE(T)
#endif
#define RM_WILD_AWAKE (world.time - rm_wild_seen < 10 ? rm_wild_was : RmWildLook())   // its land awake, asked at most every 10 ticks (Remastered/WildClock.dm)
#define RM_WANDER_RESTING (key == "Wander" ? rm_wander_rest : RmWildPhase(src, key) == "rest")   // this wander loop is resting on the clock
mob/var/tmp/list/Hostilities   // made on first use (load-asleep-1030: most creatures never use one)
mob/proc/MakeHostile(NAME="Basic",TIME=6000)
	if("[NAME]" in Hostilities) return
	if(!Hostilities) Hostilities = list()
	Hostilities+="[NAME]"
	if(TIME>0) spawn(TIME) if(Hostilities) Hostilities-="[NAME]"
	return(1)
mob/Monsters/var/tmp
	ReturnDelay=400
	PatrolPoint1
	PatrolPoint2
	HomeLoc = null
	list/GuardRules   // made on first use, as Friendlies (load-asleep-1030: most creatures never use one)
mob/Monsters/var
	list/Friendlies
mob/Monsters/proc/StayLocal()
	HomeLoc = loc
	spawn() if(CanBeSlaved) StayLocalRun(RmWildKey(src, "StayLocal"), 1)   // asleep in its proc or on the clock (Remastered/WildClock.dm)
mob/Monsters/proc/StayLocalRun(key, wait)   // the loop: every ReturnDelay while it is wild (wait 0: the clock's run, its sleep over)
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(ReturnDelay)
			else return RmWildBook(src, key, ReturnDelay)
		wait = 1
		RM_WILD_TRACE("s")
		ReturningHome=2
		if(!CanBeSlaved) break
	RmWildEnd(src, key)
mob/verb/Guard()
	var/Player/P = istype(usr, /Player) ? usr : null
	var/had_player = !!P
	var/datum/remaster_action_context/context
	if(P)
		context = P.RemasterSelectedActionCapture(/mob/verb/Guard,1)
		if(!context) return
	var/list/actors = usr.Selected.Copy()
	var/list/menu = new()
	menu += "Guard On"
	menu += "Guard Off"
	menu += "Check Rules"
	menu += "Add Agressive Rule"
	menu += "Add Patrol Rule"
	menu += "Clear Rules"
	menu += "Set Friendly to..."
	menu += "Clear Friendlies"
	menu += "Cancel"
	var/choice = usr.RemasterActionChoice("What Action Will You Choose?", "Choose", menu)
	// Guard keeps the original captured actors when selection changes. Their
	// lifetimes, authority, profiles and the initiating controller must survive.
	if(had_player && (!P || !P.RemasterSelectedActionCurrent(context,0))) return
	if(istype(usr, /Player))
		for(var/mob/Monsters/M in actors.Copy())
			if(!usr:RemasterInteractActor(M)) actors -= M
	switch(choice)
		if("Guard On")
			for(var/mob/Monsters/M in actors) if(!M.Wagon)
				if(istype(usr, /Player) && !M.RemasterManualHandoff(usr)) continue
				M.Guarding()
			usr << "<b>Selected units will now use guarding AI."
		if("Guard Off")
			for(var/mob/Monsters/M in actors) if(!M.Wagon) M.HomeLoc = null
			usr << "<b>Selected units will no longer use guarding AI."
		if("Check Rules")
			for(var/mob/Monsters/M in actors)
				var/RULES="[M]'s Rules:"
				for(var/R in M.GuardRules) RULES+=" '[R]'"
				if(M.PatrolPoint1&&M.PatrolPoint2) RULES+=" 'Patrol'"
				var/FRIENDLIES="[M]'s Friendlies:"
				for(var/F in M.Friendlies) FRIENDLIES+=" '[F]'"
				usr<<"[RULES]<br>[FRIENDLIES]<br>"
		if("Add Patrol Rule")
			usr << "<b>Click tile to create a patrol route between that location and your unit's current location."
			usr.Function = "Patrol"
		if("Add Agressive Rule")
			for(var/mob/Monsters/M in actors) if(!M.Wagon && !("Agressive" in M.GuardRules))
				if(!M.GuardRules) M.GuardRules = list()
				M.GuardRules += "Agressive"
			usr << "<b>Agressive Rule added to selected units. They will now automatically attack any units they see while on guard."
		if("Set Friendly to...")
			var/FRIEND
			if(P) FRIEND = P.RemasterSelectedText("Set a Owner to friendly for selected units, input including parentheses if adding a NPC Owner.","Add Friendly","{NPC Alliance}")
			else FRIEND = input("Set a Owner to friendly for selected units, input including parentheses if adding a NPC Owner.","Add Friendly","{NPC Alliance}") as text|null
			if(had_player && (!P || !P.RemasterSelectedActionCurrent(context,0))) return
			if(FRIEND)
				for(var/mob/Monsters/M in actors) if(!M.Wagon)
					if(istype(usr, /Player) && !usr:RemasterInteractActor(M)) continue
					if(!M.Friendlies) M.Friendlies = list()
					M.Friendlies+=FRIEND
				usr<<"<b>Selected units will no longer be agressive to units owned by ''[FRIEND]''."
		if("Clear Friendlies")
			for(var/mob/Monsters/M in actors) M.Friendlies=list()
			usr << "<b>Selected units have been cleared of all friendlies."
		if("Clear Rules")
			usr << "<b>Selected units have been cleared of all guard rules."
			for(var/mob/Monsters/M in actors)
				var/old_first = M.PatrolPoint1
				var/old_second = M.PatrolPoint2
				M.PatrolPoint1 = null
				M.PatrolPoint2 = null
				M.GuardRules = list()
				// Old patrol coordinates may now belong to another movement controller.
				// A paused FIFO does not own movement while Guard is running.
				var/other_controller = M.remaster_defense || (!M.remaster_paused && !M.remaster_wait_for_resume && M.RemasterHasOrder())
				if(!M.remaster_paused && !M.remaster_role_paused && M.remaster_work_destination && M.destination==M.remaster_work_destination) other_controller=1
				if(!other_controller && ((old_first && M.destination==old_first) || (old_second && M.destination==old_second))) M.destination=null
				if((old_first && M.HomeLoc==old_first) || (old_second && M.HomeLoc==old_second)) M.HomeLoc=null
mob/Monsters/proc/Patrol(LOC1,LOC2)
	PatrolPoint1=LOC1
	PatrolPoint2=LOC2
	HomeLoc=PatrolPoint1
mob/Monsters/proc/Guarding(RANGE=5,RATE=10,AUTO=0)
	if(Critter) return
	// Reuse a sleeping guard loop when a direct action immediately restarts it.
	if(!HomeLoc || !("Guard" in RunningProcs)) HomeLoc=loc
	if(!StopDouble("Guard")) return
	spawn()   // both loops asleep in their procs or on the clock (Remastered/WildClock.dm)
		spawn() if(HomeLoc) GuardHomeRun(RmWildKey(src, "GuardHome"), 1)
		rm_guard_range = RANGE
		rm_guard_rate = RATE
		rm_guard_auto = AUTO
		GuardRun(RmWildKey(src, "Guard"), 0)   // the loop's first body comes before its first sleep
mob/Monsters/proc/GuardHomeRun(key, wait)   // the side loop: every 250 while it guards (HomeLoc); one after a creature heads home for 50
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(250)
			else return RmWildBook(src, key, 250)
		wait = 1
		RM_WILD_TRACE(RmWildPhase(src, key) == "home" ? "H" : "h")
		if(RmWildPhase(src, key) == "home")   // the clock's run: its 50 over
			RmWildSetPhase(src, key, null)
			ReturningHome=0
		else if(!remaster_defense && !RmWildInFight(src))   // in a fight beside it, it stays in it (Remastered/WildClock.dm)
			if(ismob(destination))
				ReturningHome=1
				if(RM_WILD_AWAKE) sleep(50)
				else
					RmWildSetPhase(src, key, "home")
					return RmWildBook(src, key, 50)
				RM_WILD_TRACE("H")
				ReturningHome=0
		if(!HomeLoc) break
	RmWildEnd(src, key)
mob/Monsters/proc/GuardRun(key, wait)   // the main loop: every RATE while it guards (HomeLoc)
	var/RANGE = rm_guard_range
	var/RATE = rm_guard_rate
	var/AUTO = rm_guard_auto
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(RATE)
			else return RmWildBook(src, key, RmWildIdle() ? max(RATE, rm_wild_far_think) : RATE)   // far and idle: a look every few seconds
		wait = 1
		if(!HomeLoc) break
		RM_WILD_TRACE("m")
		if(remaster_defense) continue
		if(AUTO) if(ismob(Owner)) if(!Owner:client) break
		if(ReturningHome)
			if(loc!=HomeLoc) destination = HomeLoc
			else ReturningHome=0
		else
			var/mob/Monsters/F = RmWildFoeBeside(src)   // struck at by a foe beside it: it turns on that one (Remastered/WildClock.dm)
			if(F) destination = F
			else if(!destination || (prob(10) && !RmWildInFight(src)))
				destination=RmPostMayLook(src) ? LocateTarget(RANGE) : null   // an away owner's guard in asleep land starts no fight (Remastered/OfflineGuards.dm)
				if(!destination)
					destination=HomeLoc
					if(loc==PatrolPoint1) HomeLoc=PatrolPoint2
					if(loc==PatrolPoint2) HomeLoc=PatrolPoint1
	RmWildEnd(src, key)
	RunningProcs-="Guard"
mob/Monsters/proc/RandomWalk(LINKED=0) if(StopDouble("WalkTo") || LINKED)
	if("Guard" in RunningProcs)
		GuardWalk(1)
		return
	spawn() if(CanBeSlaved) WanderClearRun(RmWildKey(src, "WanderClear"), 1)   // both loops asleep in their procs or on the clock (Remastered/WildClock.dm)
	if(CanBeSlaved) WanderRun(RmWildKey(src, "Wander"), 1)
	else WalkTo(1)
mob/Monsters/proc/WanderClearRun(key, wait)   // the side loop: every 300 while it is wild
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(300)
			else return RmWildBook(src, key, 300)
		wait = 1
		RM_WILD_TRACE("c")
		if(!RmWildInFight(src)) src.destination = null   // never out of a fight beside it (Remastered/WildClock.dm)
		src.BowOn = 0
		if(!CanBeSlaved) break
	RmWildEnd(src, key)
mob/Monsters/proc/WanderRun(key, wait)   // the main loop: Delay+1 after the last while it is wild
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(Delay+1)
			else return RmWildBook(src, key, Delay+1)
		wait = 1
		RM_WILD_TRACE(RM_WANDER_RESTING ? "r" : "w")
		if(RM_WANDER_RESTING)   // the clock's run: its rest over, the loop goes round again
			RmWanderRest(key, 0)
		else if(!destination && !RmAwake(src))   // nowhere to go and no player near: rest (Remastered Awake.dm)
			RmWanderRest(key, 1)
			return RmWildBook(src, key, rm_asleep_nap)   // its land is asleep: the rest on the clock
		else
			var/mob/Monsters/F = RmWildFoeBeside(src)   // struck at by a foe beside it: it stands and fights back (Remastered/WildClock.dm)
			if(F) destination = F
			FindGear()
			if(!InHole && CanWalk)
				if(destination)
					if(ismob(destination) || destination == HomeLoc)
						if(destination in range(6,src)) step_towards(src,destination)
						else
							if(destination==HomeLoc) step_towards(src,destination)
							else destination = null
					if(destination == loc) destination=null
				if(!destination)
					if(HomeLoc&&ReturningHome==2)
						step_towards(src,HomeLoc)
						ReturningHome=0
					else
						step_rand(src)
						destination = LocateTarget()
		if(!CanBeSlaved) break
	RmWildEnd(src, key)
	WalkTo(1)
mob/Monsters/proc/GuardWalk(LINKED=0) if(StopDouble("WalkTo") || LINKED) spawn()   // both loops asleep in their procs or on the clock (Remastered/WildClock.dm)
	spawn() GuardGearRun(RmWildKey(src, "GuardGear"), 0)   // the gear loop's first body comes before its first sleep
	if(CanBeSlaved) GuardWalkRun(RmWildKey(src, "GuardWalk"), 1)
	else WalkTo(1)
mob/Monsters/proc/GuardGearRun(key, wait)   // the gear loop: every 200 while it is wild
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(200)
			else return RmWildBook(src, key, 200)
		wait = 1
		if(!CanBeSlaved) break
		RM_WILD_TRACE("f")
		FindGear()
	RmWildEnd(src, key)
mob/Monsters/proc/GuardWalkRun(key, wait)   // the main loop: Delay+1 after the last while it is wild
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(Delay+1)
			else return RmWildBook(src, key, !destination && RmWildIdle() ? max(Delay+1, rm_wild_far_think) : Delay+1)   // far and idle: a look every few seconds
		wait = 1
		RM_WILD_TRACE("g")
		if(!InHole && CanWalk)
			if(destination==HomeLoc) if(loc==HomeLoc) destination=null
			if(destination) step_towards(src,destination)
		if(!CanBeSlaved) break
	RmWildEnd(src, key)
	WalkTo(1)
mob/Monsters/proc/LocateTarget(RANGE=5)
	if(!rm_foe_near(src, RANGE, /mob/Monsters)) return   // nobody of another owner within RANGE: the scan would find no one (engine RmSight.cs; Native.dm's fallback: always scan)
	var/standing = -1   // Remastered: a foe of its standing near (looked up once, at the first fallen one)
	for(var/mob/Monsters/M in oview(RANGE,src))
		var/Gunna=CanBeSlaved
		if("Agressive" in GuardRules) Gunna=1
		if(ismob(M.Owner)) switch(Owner)
			if("{NPC Alliance}") if(!M.Undead&&!M.Morphed&&M.SubRace!="HalfDemon"&&M.SubRace!="Hellblooded"&&!M.Werepowers) Gunna=0   // Remastered: Hellblooded (HalfDemons.dm)
			if("{NPC Undead}")
				if(M.Undead || M.Race==Race) Gunna=0
			else if(M.Race == Race) Gunna=0
		if("[M.Owner]" in Friendlies) Gunna=0
		if("[Owner]" in M.Hostilities) Gunna=1
		if(ismob(Owner)&&ismob(M.Owner))
			var/mob/OWNERA = Owner
			var/mob/OWNERB = M.Owner
			if(OWNERB.name in OWNERA.AllyList) Gunna=0
			if(OWNERB.Faction == OWNERA.Faction) Gunna=0
		if(ismob(M.destination))
			var/mob/Monsters/D = M.destination
			if(D.Owner == Owner) Gunna=1
		if(M.Owner == Owner || M.CantKill) continue
		if(RmDownOut(M))   // Remastered: one down is out of the fight while a foe stands near (Falls.dm); that foe looked up once
			if(standing < 0) standing = RmStandingFoeNear(src)
			if(standing) continue
		switch(M.Race)
			if("Plant") if(prob(99)) continue
			if("Egg") continue
		if(Gunna) return(M)
mob/proc/FindGear()
	var/OOO
	for(var/obj/Items/I in view(1,src))
		OOO = 1
		break
	if(OOO == 1) for(var/obj/Items/Equipment/E in view(1,src))
		var/OLDLOCATION=E.loc
		var/TryIt
		switch(E.ItemType)
			if("Helmet") if(!WearingHelmet) TryIt=1
			if("Cape") if(!WearingCape) TryIt=1
			if("Neckguard") if(!WearingFullPlateHelm) TryIt=1
			if("Quiver") if(!WearingBack) TryIt=1
			if("Chestplate") if(!WearingChest) TryIt=1
			if("LeftArm") if(!WearingLeftArm) TryIt=1
			if("RightArm") if(!WearingRightArm) TryIt=1
			if("Leggings") if(!WearingLegs) TryIt=1
			if("Shield")
				if(!WearingShield) TryIt=1
			else if(E.EquipmentType()=="Weapon") if(!HoldingWeapon) TryIt=1
		if(TryIt) if(PickUpItem(E))
			if(EquipItem(E)) continue
			else if(DropItem(E)) E.loc=OLDLOCATION
