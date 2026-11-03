// No-input timing (python3 tools/formations/repro_select.py tools/formations/repro_order.dm): 200 of yours on open
// ground, one order 30 tiles off: the slot planning alone (RemasterGroupForm) against the whole order (RemasterOrder),
// each repeated for a second or more (world.timeofday counts tenths of a second).
world
	maxx = 140
	maxy = 140
	maxz = 3
	turf = /turf/grounds/grass
	fps = 10

proc/ReproTime(Player/P, what, turf/T, n)
	var/t0 = world.timeofday
	var/i = 0
	while(i < 3 || (world.timeofday - t0 < 15 && i < 60))
		if(what == "form")
			P.RemasterGroupForm(T)
			P.remaster_forming = null
		else P.RemasterOrder(T)
		i++
	world.log << "REPRO|time|[what]|n=[n]|ms=[round((world.timeofday - t0) * 100 / i, 0.1)]|runs=[i]|uncross=[jointext(rm_uncross_last, ",")]"

proc/ReproCross(list/assign)   // how many pairs of routes (where each stands to its slot) cross
	var/list/W = list()
	for(var/mob/Monsters/M in assign) W += M
	. = 0
	for(var/a = 1, a <= length(W), a++)
		var/mob/Monsters/A = W[a]
		var/turf/TA = assign[A]
		for(var/b = a + 1, b <= length(W), b++)
			var/mob/Monsters/B = W[b]
			var/turf/TB = assign[B]
			if(RmSegCross(A.x, A.y, TA.x, TA.y, B.x, B.y, TB.x, TB.y)) .++

proc/ReproRun()
	sleep(10)
	remaster_fog = 0
	var/Player/P = new(locate(5, 5, 1))
	usr = P
	for(var/n in list(50, 200))
		var/list/U = list()
		for(var/i = 0, i < n, i++)
			var/mob/Monsters/M = new /mob/Monsters/Human(locate(20 + i % 10, 20 + round(i / 10), 1))
			M.ChangeOwnership(P)
			M.Hunger = 100
			M.Tiredness = 100
			M.remaster_care_hold = world.time + 100000
			if(!(M in P.UnitList)) P.UnitList += M
			U += M
		P.Selected = U.Copy()
		var/turf/T = locate(60, 60, 1)
		ReproTime(P, "form", T, n)
		for(var/cap in list(2))
			rm_uncross_big = cap
			for(var/sh in list("box", "line", "column"))
				P.remaster_formation = sh
				ReproTime(P, "form", T, "[n] [sh] cap=[cap]")
				var/list/AS = P.RemasterGroupForm(T)
				P.remaster_forming = null
				world.log << "REPRO|cross|[n] [sh] cap=[cap]|crossing_pairs=[ReproCross(AS)]|uncross=[jointext(rm_uncross_last, ",")]"
		rm_uncross_big = 0
		P.remaster_formation = "keep"
		ReproTime(P, "order", T, n)
		if(n == 200)                          // where it goes: each stage's ms a run (Formations.dm FmProf)
			for(var/sh in list("keep", "box"))
				P.remaster_formation = sh
				fm_prof = 1
				fm_prof_ms = list()
				for(var/k = 1, k <= 20, k++)
					P.RemasterOrder(T)
					sleep(1)                    // each in a tick of its own
				fm_prof = 0
				var/list/parts = list()
				var/total = 0
				for(var/l in fm_prof_ms)
					parts += "[l]=[round(fm_prof_ms[l] / 20, 0.1)]"
					total += fm_prof_ms[l] / 20
				world.log << "REPRO|stages|[sh]|total=[round(total, 0.1)]|[jointext(parts, "|")]"
				// the whole order without the marks, in a tick of its own each time (the delayed first steps run in the ticks after)
				var/whole = 0
				var/worst = 0
				var/list/each = list()
				var/list/after = list()
				for(var/k = 1, k <= 20, k++)
					sleep(3)
					var/t0 = world.tick_usage
					P.RemasterOrder(T)
					var/ms = (world.tick_usage - t0) * world.tick_lag
					whole += ms
					worst = max(worst, ms)
					each += round(ms, 1)
					// the next tick: the first batch of delayed first steps (RmFirstLater), timed from the tick's start
					sleep(1)
					after += round(world.tick_usage * world.tick_lag, 1)
				world.log << "REPRO|whole|[sh]|ms=[round(whole / 20, 0.1)]|worst=[round(worst, 0.1)]|each=[jointext(each, ",")]|next_tick_so_far=[jointext(after, ",")]"
			P.remaster_formation = "keep"
		for(var/mob/Monsters/M in U) del(M)
		P.Selected = list()
	world.log << "REPRO|done"
