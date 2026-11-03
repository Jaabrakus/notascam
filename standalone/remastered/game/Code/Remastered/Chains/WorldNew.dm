// world/New: one chain, in the order DM ran it when it was spread over 28 files (cleanup, from
// chains.py). The call runs Shed > TickProfile > Doors > Regions > FarRecords > Native > Rulership > Formations > Flying > MagicGear > Captives > Taming > Golems > Beasts2 > Beasts1 > WallWalks > Gates > Yield > Ailments > Vapours > Biomes > Instances > Fishing > Specials > Siege > War > QoL > World (kept in Code/World.dm): each step below calls the next one down where it used to call ..().
// Add a feature's part as a new step at its place in this order, never as another override elsewhere.
var/rm_chain_base_WorldNew   // set by the bottom step for one call: the next New() on that object goes on with ..()
world/New()
	if(rm_chain_base_WorldNew == src)   // the bottom step's ..(): the first definition, kept in Code/World.dm
		rm_chain_base_WorldNew = null
		return ..()
	return RmChainWorldNew_Shed(arglist(args))

// step 1 of 27: Shed (was Code/Remastered/Shed.dm:23)
world/proc/RmChainWorldNew_Shed()
	. = RmChainWorldNew_TickProfile(arglist(args))
	spawn(0) RmShedLoop()

// step 2 of 27: TickProfile (was Code/Remastered/TickProfile.dm:39)
world/proc/RmChainWorldNew_TickProfile()
	. = RmChainWorldNew_Doors(arglist(args))
	if(world.GetConfig("env", "RM_TICK_PROFILE") == "1")
		rm_prof = 1
		spawn(0) RmProfLoop()

// step 3 of 27: Doors (was Code/Remastered/Doors.dm:74)
world/proc/RmChainWorldNew_Doors()
	RmChainWorldNew_Regions(arglist(args))
	var/native = ("rm_native_doors" in global.vars) ? global.vars["rm_native_doors"] : 0
	rm_own_doors = !rm_native_path || rm_path_verify || native

// step 4 of 27: Regions (was Code/Remastered/Regions.dm:47)
world/proc/RmChainWorldNew_Regions()
	. = RmChainWorldNew_FarRecords(arglist(args))
	rm_regions = new
	rm_map_hook = rm_regions
	if(world.GetConfig("env", "RM_REGIONS") == "0" || rm_native_version() < 10) rm_regions_on = 0
	if(world.GetConfig("env", "RM_LOAD_SLEEP") == "0") rm_regions_load_sleep = 0
	if(world.GetConfig("env", "RM_REGIONS_TEST") == "1")
		rm_regions_test = 1
		rm_regions_quiet = 0
		rm_regions_start = 20
	spawn(0) RmRegionsLoop()

// step 5 of 27: FarRecords (was Code/Remastered/FarRecords.dm:102)
world/proc/RmChainWorldNew_FarRecords()
	spawn(150) RmClockWorldBook("FarRecords", RM_FAR_EVERY)   // RmFarLoop, a job on the unit clock (UnitClock.dm)
	return RmChainWorldNew_Native(arglist(args))

// step 6 of 27: Native (was Code/Remastered/Native.dm:18)
world/proc/RmChainWorldNew_Native()
	. = RmChainWorldNew_Rulership(arglist(args))
	rm_native_path = world.GetConfig("env", "RM_NATIVE_PATH") != "0" && rm_native_version() >= 2
	rm_path_verify = world.GetConfig("env", "RM_PATH_VERIFY") == "1" && rm_native_version() >= 2
	rm_native_ver = world.GetConfig("env", "RM_NATIVE_VER") != "0" && rm_native_version() >= 6
	rm_ver_verify = world.GetConfig("env", "RM_VER_VERIFY") == "1" && rm_native_ver
	if(rm_native_ver && world.GetConfig("env", "RM_VER_QUIET") != "0") rm_ver_quieted = rm_ver_quiet(rm_ver_quiet_names) > 0   // Native.dm
	if(rm_native_version() >= 31) rm_ver_state_quiet(rm_ver_state_names)   // Native.dm: the HUD's prints stand while units walk
	rm3d_shown = rm_native_version() >= 35 && world.GetConfig("env", "RM_3D_SHOWN") != "0"
	if(rm3d_shown) rm_ver_shown_quiet(rm_ver_shown_names)   // Native.dm: the 3D entries stand while only a card changes
	if(rm_path_verify) rm_native_path = 1
	rm_native_plan = world.GetConfig("env", "RM_NATIVE_PLAN") != "0" && rm_native_version() >= 9
	rm_plan_verify = world.GetConfig("env", "RM_PLAN_VERIFY") == "1" && rm_native_plan
	rm_native_doors = rm_native_version() >= 8
	rm_grid = world.GetConfig("env", "RM_GRID") != "0" && rm_native_version() >= 11 && rm_grid_on(/mob/Monsters)
	rm_grid_verify = world.GetConfig("env", "RM_GRID_VERIFY") == "1" && rm_grid
	rm_near_verify = world.GetConfig("env", "RM_NEAR_VERIFY") == "1" && rm_grid
	rm_nav_count = world.GetConfig("env", "RM_NAV_COUNT") == "1"   // route search counts (Native.dm, navigation plan N0)
	if(rm_nav_count) rm_nav_count_at = world.time + 600
	rm_reach = world.GetConfig("env", "RM_REACH") != "0" && rm_native_version() >= 12   // the reach map (Native.dm, navigation plan N1)
	rm_reach_verify = world.GetConfig("env", "RM_REACH_VERIFY") == "1" && rm_reach
	rm_field = world.GetConfig("env", "RM_FIELD") != "0" && rm_native_version() >= 13   // the battle ways (Native.dm, Attack.dm RmGangUp)
	rm_morale_native = world.GetConfig("env", "RM_MORALE_NATIVE") != "0" && rm_native_version() >= 14 && rm_grid   // morale's look round (Native.dm)
	rm_morale_verify = world.GetConfig("env", "RM_MORALE_VERIFY") == "1" && rm_morale_native
	rm_pool_native = world.GetConfig("env", "RM_POOL_NATIVE") != "0" && rm_native_version() >= 15   // the box's next foe ranked (Native.dm)
	rm_pool_verify = world.GetConfig("env", "RM_POOL_VERIFY") == "1" && rm_pool_native
	rm_worked_native = world.GetConfig("env", "RM_WORKED_NATIVE") != "0" && rm_native_version() >= 16   // the worked tiles' tidy (Native.dm)
	rm_worked_verify = world.GetConfig("env", "RM_WORKED_VERIFY") == "1" && rm_worked_native
	rm_store_native = world.GetConfig("env", "RM_STORE_NATIVE") != "0" && rm_native_version() >= 17   // a delivery's store tile (Native.dm)
	rm_store_verify = world.GetConfig("env", "RM_STORE_VERIFY") == "1" && rm_store_native
	rm_decay_native = world.GetConfig("env", "RM_DECAY_NATIVE") != "0" && rm_native_version() >= 18   // the lying items' timer (Native.dm)
	if(rm_decay_native) spawn() RmDecayLoop()
	rm_route = world.GetConfig("env", "RM_ROUTE") != "0" && rm_native_version() >= 19   // the route map (Native.dm)
	rm_zoc_on = world.GetConfig("env", "RM_ZOC") != "0"   // a store tile's zone kept (Zones.dm)
	rm_zoc_verify = world.GetConfig("env", "RM_ZOC_VERIFY") == "1" && rm_zoc_on
	rm_walk_native = world.GetConfig("env", "RM_WALK_NATIVE") != "0" && rm_native_version() >= 21 && RmStepSetup()   // the game's walkable checks by the engine (Native.dm)
	rm_walk_verify = world.GetConfig("env", "RM_WALK_VERIFY") == "1" && rm_walk_native
	rm_step_native = world.GetConfig("env", "RM_STEP_NATIVE") != "0" && rm_native_version() >= 21 && RmStepSetup()   // the plain step (Native.dm)
	rm_step_verify = world.GetConfig("env", "RM_STEP_VERIFY") == "1" && rm_step_native
	rm_foe_beside_native = world.GetConfig("env", "RM_FOE_BESIDE") != "0" && rm_native_version() >= 22   // the foes beside a fighter (Native.dm)
	rm_foe_beside_verify = world.GetConfig("env", "RM_FOE_BESIDE_VERIFY") == "1" && rm_foe_beside_native
	rm_step_off_native = world.GetConfig("env", "RM_STEP_OFF") != "0" && rm_native_version() >= 23 && RmStepSetup()   // the step-off's looks (Native.dm)
	rm_step_off_verify = world.GetConfig("env", "RM_STEP_OFF_VERIFY") == "1" && rm_step_off_native
	rm_swim_on = world.GetConfig("env", "RM_SWIM") != "0" && rm_native_version() >= 25 && rm_swim_setup(/turf/grounds/waters, SKY_LAYER, rm_swim_none, rm_swim_cost, /mob/Monsters/RemasterSiege)   // swimming (Swim.dm)

// step 7 of 27: Rulership (was Code/Remastered/Rulership.dm:152)
world/proc/RmChainWorldNew_Rulership()
	. = RmChainWorldNew_Formations(arglist(args))
	RmRegaliaGear()
	spawn(50) RmRulershipLoop()

// step 8 of 27: Formations (was Code/Remastered/Formations.dm:979)
world/proc/RmChainWorldNew_Formations()
	. = RmChainWorldNew_Flying(arglist(args))
	rm_native_slots = rm_native_version() >= 4 && world.GetConfig("env", "RM_NATIVE_SLOTS") != "0"

// step 9 of 27: Flying (was Code/Remastered/Flying.dm:123)
world/proc/RmChainWorldNew_Flying()
	. = RmChainWorldNew_MagicGear(arglist(args))
	if(text2num(world.GetConfig("env", "RM_SKY_OPEN"))) rm_sky_open_all = 1

// step 10 of 27: MagicGear (was Code/Remastered/MagicGear.dm:138)
world/proc/RmChainWorldNew_MagicGear()
	spawn(140) RmMagicGearLoop()
	return RmChainWorldNew_Captives(arglist(args))

// step 11 of 27: Captives (was Code/Remastered/Captives.dm:1522)
// --- The loop ---------------------------------------------------------------------------------------------
world/proc/RmChainWorldNew_Captives()
	spawn(140) RmCaptiveLoop()
	return RmChainWorldNew_Taming(arglist(args))

// step 12 of 27: Taming (was Code/Remastered/Taming.dm:91)
world/proc/RmChainWorldNew_Taming()
	spawn(120) RmPlaceNests()
	spawn(130) RmTamingLoop()
	return RmChainWorldNew_Golems(arglist(args))

// step 13 of 27: Golems (was Code/Remastered/Golems.dm:443)
world/proc/RmChainWorldNew_Golems()
	spawn(600)
		while(1)
			RmGolemRisePass()
			sleep(rm_golem_rise_every)
	return RmChainWorldNew_Beasts2(arglist(args))

// step 14 of 27: Beasts2 (was Code/Remastered/Beasts.dm:572)
world/proc/RmChainWorldNew_Beasts2()
	spawn(60) RmWildDragonsLoop()
	return RmChainWorldNew_Beasts1(arglist(args))

// step 15 of 27: Beasts1 (was Code/Remastered/Beasts.dm:514)
world/proc/RmChainWorldNew_Beasts1()
	spawn(100) RmWingsMend()
	return RmChainWorldNew_WallWalks(arglist(args))

// step 16 of 27: WallWalks (was Code/Remastered/WallWalks.dm:22)
world/proc/RmChainWorldNew_WallWalks()
	spawn(60) RemasterWallWalkLoop()
	return RmChainWorldNew_Gates(arglist(args))

// step 17 of 27: Gates (was Code/Remastered/Gates.dm:18)
world/proc/RmChainWorldNew_Gates()
	rm_rune_defs["portcullis"] = list("Portcullis", /obj/RemasterRune/Door/Portcullis, 0)   // pays for itself (RemasterGateEnergy)
	rm_rune_defs["drawbridge"] = list("Drawbridge", /obj/RemasterRune/Door/Drawbridge, 0)
	return RmChainWorldNew_Yield(arglist(args))

// step 18 of 27: Yield (was Code/Remastered/Yield.dm:364)
world/proc/RmChainWorldNew_Yield()
	RmChainWorldNew_Ailments(arglist(args))
	spawn(260) RemasterYieldLoop()

// step 19 of 27: Ailments (was Code/Remastered/Ailments.dm:140)
world/proc/RmChainWorldNew_Ailments()
	. = RmChainWorldNew_Vapours(arglist(args))
	spawn(300) RemasterFoodRotLoop()

// step 20 of 27: Vapours (was Code/Remastered/Vapours.dm:292)
world/proc/RmChainWorldNew_Vapours()
	. = RmChainWorldNew_Biomes(arglist(args))
	spawn(200) RemasterRotLoop()

// step 21 of 27: Biomes (was Code/Remastered/Biomes.dm:169)
world/proc/RmChainWorldNew_Biomes()
	RmChainWorldNew_Instances(arglist(args))
	spawn(220) RemasterBiomeLoop()

// step 22 of 27: Instances (was Code/Remastered/Instances.dm:175)
world/proc/RmChainWorldNew_Instances()
	RmChainWorldNew_Fishing(arglist(args))
	spawn(200) RemasterPlaceCaveMouths()
	spawn(250)
		if(!rm_cave_loop)
			rm_cave_loop = 1
			RemasterCaveLoop()

// step 23 of 27: Fishing (was Code/Remastered/Fishing.dm:255)
world/proc/RmChainWorldNew_Fishing()
	RmChainWorldNew_Specials(arglist(args))
	spawn(60)
		RemasterPlaceFishSpots()
		RemasterFishLoop()

// step 24 of 27: Specials (was Code/Remastered/Specials.dm:30)
// Names for the wound messages (Throwing.dm's table).
world/proc/RmChainWorldNew_Specials()
	RmChainWorldNew_Siege(arglist(args))
	for(var/race in rm_specials)
		var/list/S = rm_specials[race]
		if(!rm_throw_kinds[S[1]]) rm_throw_kinds[S[1]] = list(S[4], 8, 16, null, 1, lowertext(S[2]))

// step 25 of 27: Siege (was Code/Remastered/Siege.dm:358)
world/proc/RmChainWorldNew_Siege()
	RmChainWorldNew_War(arglist(args))
	if(!rm_siege_loop)
		rm_siege_loop = 1
		spawn(30) RemasterSiegeLoop()

// step 26 of 27: War (was Code/Remastered/War.dm:243)
world/proc/RmChainWorldNew_War()
	RmChainWorldNew_QoL(arglist(args))
	if(!rm_war_loop)
		rm_war_loop = 1
		spawn(30) RemasterWarLoop()

// step 27 of 27: QoL (was Code/Remastered/QoL.dm:267)
world/proc/RmChainWorldNew_QoL()
	spawn(1) RemasterLoadWorld()
	spawn(10) RemasterLoop()
	return RmChainWorldNew_Base(arglist(args))

// the bottom's ..(): marks src and calls New() again, so the override above does the kept World definition
world/proc/RmChainWorldNew_Base()
	rm_chain_base_WorldNew = src
	return New(arglist(args))
