// The planned-building pass with walls waiting for material (world-look 2026-10-25, the user's "yellow things": planned
// walls, amber while waiting): Blueprints.dm RemasterBlueprintTick, each track run (twice a second), with 200 units, of
// them 0, 10 or 30 builders, and 20, 100 or 300 stone walls planned in 10 sites, no stone anywhere (so every builder is
// waiting). Also the 3D view's list of them (RemasterBlueprintData). Obey arena, no client.
//   tools/check_arena.py --test blueprint_tick_check.dm --entry BtRun
proc/BtMs(u0)
	return (world.tick_usage - u0) * world.tick_lag


// each step's time, per builder per run (overrides that time the game's own procs)
var/list/bt_ms = list()
proc/BtAdd(k, u0)
	bt_ms[k] += (world.tick_usage - u0) * world.tick_lag
Player/RemasterSiteFor(mob/Monsters/M, list/claims)
	var/u0 = world.tick_usage
	. = ..()
	BtAdd("choose a site (RemasterSiteFor)", u0)
Player/RemasterSiteNextTile(list/S, mob/Monsters/M)
	var/u0 = world.tick_usage
	. = ..()
	BtAdd("next tile (RemasterSiteNextTile)", u0)
Player/RemasterSiteSource(list/S, path, mob/Monsters/M)
	var/u0 = world.tick_usage
	. = ..()
	BtAdd("look for material (RemasterSiteSource)", u0)
mob/Monsters/RemasterSiteWaitAside(list/S)
	var/u0 = world.tick_usage
	. = ..()
	BtAdd("wait aside (RemasterSiteWaitAside)", u0)
Player/RemasterSiteMissing(list/S, path)
	var/u0 = world.tick_usage
	. = ..()
	BtAdd("note what's missing (RemasterSiteMissing)", u0)
mob/Monsters/RemasterSiteWork(Player/P, list/S)
	var/u0 = world.tick_usage
	. = ..()
	BtAdd("a builder's work, all of it (RemasterSiteWork)", u0)

proc/BtRun()
	sleep(30)
	remaster_fog = 0
	var/Player/P = new(locate(60, 50, 1))
	P.UnitList = list()
	P.key = "bptick"
	Players += P
	usr = P
	var/list/U = list()
	for(var/i = 1, i <= 200, i++) U += ObHuman(P, rand(5, 115), rand(5, 95), 1, 0)
	for(var/list/C in list(list(0, 300), list(10, 300), list(30, 20), list(30, 100), list(30, 300)))
		var/builders = C[1]
		var/N = C[2]
		for(var/mob/Monsters/M in U)
			M.remaster_job = null
			if(M.remaster_site) M.RemasterSiteLeave(P)
		P.remaster_blueprints = list()
		P.remaster_sites = list()
		var/list/sites = list()
		for(var/s = 1, s <= 10, s++) sites += list(P.RemasterSiteNew("PlaceStoneWall", 1))
		for(var/i = 0, i < N, i++)
			var/list/S = sites[(i % 10) + 1]
			P.remaster_blueprints += list(list("x"=30 + i % 60, "y"=30 + round(i / 60) * 3, "z"=1, "mode"="PlaceStoneWall", "note"="Waiting for a builder", "tries"=0, "site"=S["id"]))
		for(var/i = 1, i <= builders, i++)
			var/mob/Monsters/M = U[i]
			M.remaster_job = "builder"
		usr = P
		for(var/k = 1, k <= 3, k++)   // they join their sites and find nothing to build with
			P.RemasterBlueprintTick(0)
			sleep(5)
		var/list/ms = list()
		bt_ms = list()
		for(var/k = 1, k <= 8, k++)
			var/u0 = world.tick_usage
			P.RemasterBlueprintTick(0)
			ms += BtMs(u0)
			sleep(5)
		var/sum = 0
		for(var/v in ms) sum += v
		var/waiting = 0
		for(var/mob/Monsters/M in U) if(M.remaster_site && M.remaster_site_standby) waiting++
		var/u1 = world.tick_usage
		var/list/D = P.RemasterBlueprintData()
		var/d_ms = BtMs(u1)
		world.log << "CK|[builders] builders, [N] walls waiting for stone|1|the pass [round(sum / length(ms), 0.1)] ms a run (worst [round(max(ms), 0.1)]): [round(sum / length(ms) * 2)] ms a second; [waiting] builders waiting; the 3D view's list [round(d_ms, 0.1)] ms, [length(D)] pieces (engine [rm_native_version()])"
		var/list/parts = list()
		for(var/k in bt_ms) parts += "[k] [round(bt_ms[k] / 8, 0.1)]"
		world.log << "CK|  its steps, ms a run|1|[jointext(parts, "; ")]"
	world.log << "CK|complete"
