// Tick profiler (server cost, 2026-10-23; tools/tick_profile.py). Off in play: it only runs when the server is
// started with RM_TICK_PROFILE=1 in its environment, and then changes nothing the game does.
// Each per-tick system below is wrapped (an override that calls ..()) and timed with world.tick_usage, the engine's
// 1 ms clock inside a tick. Once a game second (10 ticks) one line is appended to tick-profile.log in the world folder:
//   RMPROF|t=<world.time>|rt=<world.timeofday>|ticks=<ticks>|real=<real deciseconds those ticks took>|cpu=<avg>/<max>/<ticks over 100%>|
//     stalls=<gaps of 0.3 s or more between ticks>/<longest, deciseconds>/<world.cpu after it>|players=..|mobs=..|
//     alloc=<MB the game thread allocated that second>/<MB the whole process did>|kb=<system>~<KB>,...|
//     <system>=<ms in that second>/<calls>/<slowest call ms>;...
//   SLOWTICK|t=<world.time>|cpu=<world.cpu>|<system>=<ms in that tick>;... for each tick over 100 ms, costliest first.
// alloc and kb need an engine with rm_alloc_now (engine/native/RmAlloc.cs, v6); without it they read 0. The process
// minus the game thread is the engine's own allocation (the network: what each client is sent).
// cpu is the engine's own world.cpu: the DM part of each tick (procs, map update) as a share of the 100 ms tick.
// real above ticks means the server fell behind. A call that slept into another tick is not timed (counted in "slept").
// Systems nest by name ("track/..." inside "track", "hud/data" inside "hud"), and the HUD and 3D parts are also built
// inside the track. "other DM" is world.cpu minus the timed calls that were not inside another timed call: units'
// own loops, NPCs, world loops, the map update.

var/rm_prof = 0
var/list/rm_prof_ms = list()
var/list/rm_prof_n = list()
var/list/rm_prof_max = list()
var/rm_prof_slept = 0
var/rm_prof_depth = 0     // how many timed calls are open: a call that opens at 0 is top-level
var/rm_prof_top = 0       // ms in top-level timed calls this second
var/list/rm_prof_kb = list()       // KB the game thread allocated in each system this second
var/list/rm_prof_tick = list()     // ms each system took since the profiler last looked: about one tick (SLOWTICK lines)
var/list/rm_prof_astack = list()   // the game thread's allocation count at each open timed call

// The engine's where it has them (RmAlloc.cs): KB allocated so far, wrapping every 1 GB; 0 without them.
proc/rm_alloc_now()
	return 0
proc/rm_alloc_total()
	return 0

proc/RmAllocKB(a0, a1)   // KB between two readings, across the wrap
	var/d = a1 - a0
	return d < 0 ? d + 1048576 : d

// world/New: this file's part is step RmChainWorldNew_TickProfile in Code/Remastered/Chains/WorldNew.dm

proc/RmProfIn()
	rm_prof_depth++
	rm_prof_astack += rm_alloc_now()
	return world.tick_usage

proc/RmProf(name, t0, w0)
	rm_prof_depth = max(0, rm_prof_depth - 1)
	var/a0 = 0
	var/n_open = length(rm_prof_astack)
	if(n_open)
		a0 = rm_prof_astack[n_open]
		rm_prof_astack.len--
	if(world.time != w0)
		rm_prof_slept++
		return
	var/ms = (world.tick_usage - t0) * world.tick_lag   // tick_usage is a share of the tick, tick_lag 1 = 100 ms
	if(!rm_prof_depth) rm_prof_top += ms
	rm_prof_ms[name] += ms
	rm_prof_tick[name] += ms
	rm_prof_n[name] += 1
	if(ms > rm_prof_max[name]) rm_prof_max[name] = ms
	if(n_open) rm_prof_kb[name] += RmAllocKB(a0, rm_alloc_now())

proc/RmProfLoop()
	var/ticks = 0
	var/cpu = 0
	var/cpu_max = 0
	var/over = 0
	var/mobs = 0
	var/w0 = world.time
	var/r0 = world.timeofday
	var/count_at = 0
	var/last = world.timeofday
	var/stalls = 0       // gaps of 300 ms or more between two ticks (timeofday counts tenths of a second)
	var/stall_max = 0
	var/stall_cpu = 0    // world.cpu just after the longest gap: low means the time went outside DM code
	var/g0 = rm_alloc_now()
	var/p0 = rm_alloc_total()
	while(rm_prof)
		sleep(1)
		var/gap = world.timeofday - last
		if(gap < 0) gap += 864000
		last = world.timeofday
		if(gap >= 4)
			stalls++
			if(gap > stall_max)
				stall_max = gap
				stall_cpu = world.cpu
		// a tick over its 100 ms: which systems ran in it, the costliest first (options 1 and 2: what to spread or shed)
		if(world.cpu > 100 && length(rm_prof_tick))
			var/list/top = list()
			for(var/k in rm_prof_tick) top += list(list(k, rm_prof_tick[k]))
			for(var/a = 1, a <= length(top), a++) for(var/b = a + 1, b <= length(top), b++) if(top[b][2] > top[a][2]) top.Swap(a, b)
			var/list/out = list()
			for(var/i = 1, i <= min(8, length(top)), i++) out += "[top[i][1]]=[round(top[i][2], 0.1)]"
			text2file("SLOWTICK|t=[world.time]|cpu=[round(world.cpu)]|[jointext(out, ";")]", "tick-profile.log")
		rm_prof_tick = list()
		ticks++
		cpu += world.cpu
		cpu_max = max(cpu_max, world.cpu)
		if(world.cpu > 100) over++
		if(world.time - w0 < 10) continue
		if(world.time >= count_at)   // counting every creature costs a little: every 30 s
			count_at = world.time + 300
			mobs = 0
			for(var/mob/Monsters/M in world) mobs++
		var/real = world.timeofday - r0
		if(real < 0) real += 864000   // midnight
		var/players = 0
		for(var/client/C) players++
		var/cpu_ms = cpu * world.tick_lag
		var/list/parts = list()
		for(var/name in rm_prof_ms) parts += "[name]=[round(rm_prof_ms[name], 0.1)]/[rm_prof_n[name]]/[round(rm_prof_max[name], 0.1)]"
		parts += "other DM=[round(cpu_ms - rm_prof_top, 0.1)]/[ticks]/0"
		var/g1 = rm_alloc_now()
		var/p1 = rm_alloc_total()
		var/list/kb = list()
		for(var/name in rm_prof_kb) kb += "[name]~[round(rm_prof_kb[name], 1)]"
		var/alloc = "alloc=[round(RmAllocKB(g0, g1) / 1024, 0.01)]/[round(RmAllocKB(p0, p1) / 1024, 0.01)]|kb=[jointext(kb, ",")]"
		g0 = g1
		p0 = p1
		text2file("RMPROF|t=[world.time]|rt=[world.timeofday]|ticks=[world.time - w0]|real=[real]|cpu=[round(cpu / max(1, ticks), 0.1)]/[round(cpu_max, 0.1)]/[over]|stalls=[stalls]/[stall_max]/[round(stall_cpu)]|players=[players]|mobs=[mobs]|slept=[rm_prof_slept]|[alloc]|[jointext(parts, ";")]", "tick-profile.log")
		rm_prof_ms = list()
		rm_prof_n = list()
		rm_prof_max = list()
		rm_prof_kb = list()
		if(length(rm_prof_astack) > 64) rm_prof_astack = list()   // a timed call that threw never closed: start clean
		rm_prof_slept = 0
		rm_prof_top = 0
		stalls = 0
		stall_max = 0
		stall_cpu = 0
		ticks = 0
		cpu = 0
		cpu_max = 0
		over = 0
		w0 = world.time
		r0 = world.timeofday

// --- The per-player track (QoL.dm RemasterTrack, every REMASTER_TRACK_DELAY ticks) ---------------------------------
Player/RemasterTrack()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track", t0, w0)
Player/RemasterAwayTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/away", t0, w0)
Player/RemasterExploreTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/explore", t0, w0)
Player/RemasterBagTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/bag", t0, w0)
Player/RemasterPatrolTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/patrol", t0, w0)
Player/RemasterDayTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/day", t0, w0)
Player/RemasterCareTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/care", t0, w0)
Player/RemasterBlueprintTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/blueprints", t0, w0)
Player/RemasterSkillTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/skills", t0, w0)
Player/RemasterBoardTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/board", t0, w0)
Player/RemasterOrdersTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/orders", t0, w0)
Player/RemasterProgressTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/orders/progress", t0, w0)
Player/RemasterCaravanTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/orders/caravans", t0, w0)
Player/RemasterClaimTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/orders/claims", t0, w0)
Player/RemasterMoodsTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/orders/moods", t0, w0)
mob/Monsters/RemasterDefenseTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/orders/defense", t0, w0)
mob/Monsters/RemasterAttackTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/orders/attack", t0, w0)
mob/Monsters/RemasterOrderTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("unit order", t0, w0)   // also called outside the track (orders given, steps)
Player/RemasterCaptiveTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/captives", t0, w0)
Player/RemasterSettlementTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/settlement", t0, w0)
Player/RemasterPlayModeTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("track/playmode", t0, w0)

// --- The HUD model (HUD.dm), built for each player on the track and after commands ---------------------------------
Player/RemasterHUDTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("hud", t0, w0)
Player/RemasterHUDData()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("hud/data", t0, w0)
mob/Monsters/RemasterUnitData(Player/P)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("hud/data/units", t0, w0)
Player/RemasterSettlementData()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("hud/data/settlement", t0, w0)
Player/RemasterCommandData()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("hud/data/commands", t0, w0)
Player/RemasterIdleUnits()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("hud/data/idle", t0, w0)
Player/RemasterProgressData()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("hud/data/progress", t0, w0)
Player/RemasterExploredMaskCached()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("hud/data/explored", t0, w0)
Player/RemasterBorderData()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("hud/data/border", t0, w0)
Player/RmCaptivesData()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("hud/data/captives", t0, w0)

// --- The 3D scene (View3D.dm), every track; positions every tick ---------------------------------------------------
Player/Remaster3DTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("3d", t0, w0)
Player/RmFogTick()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("3d/fog tick", t0, w0)
Player/Remaster3DThings(zz = z, units_only = 0)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf(units_only ? "3d/things (other layer)" : "3d/things", t0, w0)
Player/Remaster3DTerrain(zz = z)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf(zz == z ? "3d/terrain" : "3d/terrain (other layer)", t0, w0)
Player/RemasterBlueprintData()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("3d/blueprints", t0, w0)
Player/Remaster3DFar()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("3d/far", t0, w0)
Player/Remaster3DFarUnits()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("3d/far units", t0, w0)
Player/RmFogBits(x0, y0, x1, y1, zz)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("3d/fog bits", t0, w0)
Player/Remaster3DWork(x0, y0, x1, y1)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("3d/work", t0, w0)
Player/Remaster3DYield(x0, y0, x1, y1)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("3d/yield", t0, w0)
Player/Remaster3DTexture(icon, state)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("3d/textures", t0, w0)   // a tile or thing's picture, made and sent the first time it is seen
Player/Remaster3DUnitTextures(mob/M)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("3d/unit pictures", t0, w0)   // a creature's sprite strips, built the first time its look is seen
	var/ms = (world.tick_usage - t0) * world.tick_lag
	if(world.time == w0 && ms >= 100) text2file("SLOW|3d/unit pictures|[round(ms)] ms|[M.type]|[M.name]|frames=[M.remaster_3d_frames]|t=[world.time]", "tick-profile.log")
Player/RemasterPortrait(mob/Monsters/M)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("portraits", t0, w0)
mob/Monsters/RemasterApproach(datum/remaster_order/O, atom/A, reach)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("unit order/approach", t0, w0)
mob/Monsters/RemasterGroupApproach(datum/remaster_order/O, turf/goal)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("unit order/approach/with its group", t0, w0)
mob/Monsters/RemasterSlotNear(turf/S, datum/remaster_group/G)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("unit order/approach/free tile near its slot", t0, w0)
datum/remaster_group/Pass(mob/Monsters/me)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("group: mates walking", t0, w0)
datum/remaster_group/Pace()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("group: pace", t0, w0)
mob/Monsters/RemasterChainStep()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("creature move/next step of its route", t0, w0)
Player/RemasterOrder(atom/A, queued = 0, kind = null)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("order given", t0, w0)
Player/Remaster3DMovesPush()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("3d moves", t0, w0)

// mob/Monsters/Move: this file's part is step RmChainMove_TickProfile in Code/Remastered/Chains/Move.dm
// mob/Monsters/RemasterStepDelay: this file's part is step RmChainStepDelay_TickProfile in Code/Remastered/Chains/StepDelay.dm
mob/FindGear()
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("npc find gear", t0, w0)
mob/Monsters/LocateTarget(RANGE = 5)
	if(!rm_prof) return ..()
	var/t0 = RmProfIn()
	var/w0 = world.time
	. = ..()
	RmProf("npc look for a target", t0, w0)
