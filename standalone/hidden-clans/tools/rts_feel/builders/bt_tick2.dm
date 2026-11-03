// The builders' pass in the cases world-look's fixture (reports/world-look/yellow/blueprint_tick_check.dm) doesn't reach
// (rts-feel, 2026-10-25): there no builder ever joins a task (no stone anywhere from the start). Here, 200 units:
//   "joined, then out of stone": 30 builders, 300 stone walls in 10 tasks; each builder starts with one stone, builds a
//     piece, and then waits at its task (the amber walls in play: on the task, waiting);
//   "full stockpile, no stone": the same, plus 400 logs on the stockpile (its store look walks them all).
// Each the pass's ms a run over 8 runs, and its steps.
//   tools/check_arena.py --test bt_tick2.dm --entry Bt2Run
var/list/bt2_ms = list()
proc/Bt2Add(k, u0)
	bt2_ms[k] += (world.tick_usage - u0) * world.tick_lag
Player/RemasterSiteFor(mob/Monsters/M, list/claims)
	var/u0 = world.tick_usage
	. = ..()
	Bt2Add("choose a site", u0)
Player/RemasterSiteSource(list/S, path, mob/Monsters/M)
	var/u0 = world.tick_usage
	. = ..()
	Bt2Add("look for material", u0)
Player/RemasterSiteNextTile(list/S, mob/Monsters/M)
	var/u0 = world.tick_usage
	. = ..()
	Bt2Add("next tile", u0)
mob/Monsters/RemasterSiteWork(Player/P, list/S)
	var/u0 = world.tick_usage
	. = ..()
	Bt2Add("a builder's work", u0)

proc/Bt2Run()
	sleep(30)
	remaster_fog = 0
	var/Player/P = new(locate(60, 50, 1))
	P.UnitList = list()
	P.key = "bptick2"
	Players += P
	usr = P
	P.remaster_stock_x = 60
	P.remaster_stock_y = 50
	P.remaster_stock_z = 1
	var/list/U = list()
	for(var/i = 1, i <= 200, i++) U += ObHuman(P, rand(5, 115), rand(5, 95), 1, 0)
	for(var/full in list(0, 1))
		for(var/mob/Monsters/M in U)
			M.remaster_job = null
			if(M.remaster_site) M.RemasterSiteLeave(P)
		var/list/gone = list()
		for(var/obj/Items/ores/stone/I in world) gone += I
		for(var/obj/Items/woods/wood/I in world) gone += I
		for(var/obj/Items/I in gone) del(I)
		if(full)
			var/turf/ST = P.RemasterStockpile()
			for(var/n = 1, n <= 400, n++) new /obj/Items/woods/wood(locate(ST.x + (n % 3) - 1, ST.y + round(n / 3) % 3 - 1, 1))
		P.remaster_blueprints = list()
		P.remaster_sites = list()
		var/list/sites = list()
		for(var/s = 1, s <= 10, s++) sites += list(P.RemasterSiteNew("PlaceStoneWall", 1))
		for(var/i = 0, i < 300, i++)
			var/list/S = sites[(i % 10) + 1]
			P.remaster_blueprints += list(list("x"=30 + i % 60, "y"=30 + round(i / 60) * 3, "z"=1, "mode"="PlaceStoneWall", "note"="Waiting for a builder", "tries"=0, "site"=S["id"]))
		for(var/i = 1, i <= 30, i++)
			var/mob/Monsters/M = U[i]
			M.remaster_job = "builder"
			M.ForcePickUpItem(new /obj/Items/ores/stone)
		var/waiting = 0
		for(var/k = 1, k <= 400, k++)   // they join, walk over, build their piece, then wait
			usr = P
			P.RemasterBlueprintTick(0)
			sleep(5)
			waiting = 0
			for(var/mob/Monsters/M in U) if(M.remaster_site && M.remaster_site_standby) waiting++
			if(waiting >= 30) break
		var/built = 0
		for(var/list/S in P.remaster_sites) built += S["built"]
		var/list/ms = list()
		bt2_ms = list()
		for(var/k = 1, k <= 8, k++)
			var/u0 = world.tick_usage
			usr = P
			P.RemasterBlueprintTick(0)
			ms += (world.tick_usage - u0) * world.tick_lag
			sleep(5)
		var/sum = 0
		for(var/v in ms) sum += v
		var/label = full ? "full stockpile (400 logs), no stone" : "joined, then out of stone"
		world.log << "CK|30 builders, 300 walls: [label]|1|the pass [round(sum / length(ms), 0.1)] ms a run (worst [round(max(ms), 0.1)]); [waiting] builders waiting at their tasks, [built] pieces built (engine [rm_native_version()])"
		var/list/parts = list()
		for(var/k in bt2_ms) parts += "[k] [round(bt2_ms[k] / 8, 0.1)]"
		world.log << "CK|  its steps, ms a run|1|[jointext(parts, "; ")]"
	world.log << "CK|complete"
