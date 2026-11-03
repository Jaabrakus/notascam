// Unit movement smoothness, server side (rts-feel 2026-10-23): when each unit really steps, and what the 3D view would
// be told and when (the moves push every 2 ticks, View3D.dm Remaster3DMovesLoop; the whole scene every 5, RemasterTrack),
// for a few walks. Run in check_breaking's arena: python3 tools/rts_feel/move/measure.py
var/rfm_on = 0
var/list/rfm_steps = list()   // unit -> list(list(t, x, y))
var/list/rfm_obs = list()     // unit -> list(list(t, x, y, "p" or "s"))
mob/Monsters/Move(NewLoc, Dir = 0, step_x = 0, step_y = 0)
	. = ..()
	if(. && rfm_on && rfm_steps[src]) rfm_steps[src] += list(list(world.time, x, y))

proc/RfmSampler()
	while(rfm_on)
		for(var/mob/Monsters/M in rfm_obs)
			if(world.time % REMASTER_3D_MOVES_EVERY == 0) rfm_obs[M] += list(list(world.time, M.x, M.y, "p", round(M.remaster_step_gap * 100 / max(1, rm_speed))))   // as the moves push (View3D.dm)
			if(world.time % 5 == 0) rfm_obs[M] += list(list(world.time, M.x, M.y, "s"))
		sleep(1)

proc/RfmDriver(Player/P)
	while(rfm_on)
		P.RemasterOrdersTick()   // the game's order tick (QoL.dm RemasterTrack, every 5 ticks)
		sleep(5)

proc/RfmTrack(list/units)
	for(var/mob/Monsters/M in units)
		rfm_steps[M] = list(list(-1, M.x, M.y))
		rfm_obs[M] = list()

proc/RfmReport(scene, list/units, t0, goal)
	var/i = 0
	for(var/mob/Monsters/M in units)
		i++
		var/list/S = rfm_steps[M]
		S.Cut(1, 2)
		world.log << "BK|move [scene] [i]|1|[json_encode(list("scene"=scene, "unit"=i, "delay"=M.Delay, "t0"=t0, "goal"=goal, "steps"=S, "obs"=rfm_obs[M], "end"=list(M.x, M.y), "status"=M.remaster_order_status))]"
		rfm_steps -= M
		rfm_obs -= M

proc/RfmWalk(Player/P, scene, list/units, turf/T, kind = "Move", limit = 400)
	RfmTrack(units)
	P.Selected = units.Copy()
	usr = P
	sleep(3)
	var/t0 = world.time
	P.RemasterOrder(T, 0, kind)
	for(var/t = 0, t < limit, t++)
		var/busy = 0
		for(var/mob/Monsters/M in units) if(M.RemasterHasOrder()) busy = 1
		if(!busy) break
		sleep(1)
	sleep(5)
	RfmReport(scene, units, t0, list(T.x, T.y))
	P.Selected = list()
	for(var/mob/Monsters/M in units)
		M.RemasterStopOrders()
		M.ChangeOwnership(null)
		del(M)

proc/RfMoveRun()
	sleep(30)
	var/Player/P = new(locate(60, 50, 1))
	P.UnitList = list()
	P.Selected = list()
	P.key = "mover"
	usr = P
	rfm_on = 1
	spawn(0) RfmSampler()
	spawn(0) RfmDriver(P)
	// 1. one unit, 30 tiles over open ground
	RfmWalk(P, "solo-open", list(ObHuman(P, 10, 10)), locate(40, 10, 1))
	// 2. the same through a forest and round a wall
	for(var/X = 14, X <= 36, X++) for(var/Y = 26, Y <= 34, Y++)
		if((X * 7 + Y * 3) % 5 == 0 && !(Y == 30 && X % 2)) new /turf/grounds/Trees/Tree1(locate(X, Y, 1))
	for(var/Y = 27, Y <= 33, Y++)
		var/turf/W = locate(25, Y, 1)
		W.density = 1; W.opacity = 1; W.CanDigAt = 1; W.icon_state = "StoneWall"
	RfmWalk(P, "solo-forest-wall", list(ObHuman(P, 10, 30)), locate(40, 30, 1))
	// 3. a group of 6, then 30, in formation
	var/list/G6 = list()
	for(var/k = 0, k < 6, k++) G6 += ObHuman(P, 8 + k % 3, 48 + round(k / 3))
	RfmWalk(P, "group-6", G6, locate(40, 50, 1))
	var/list/G30 = list()
	for(var/k = 0, k < 30, k++) G30 += ObHuman(P, 6 + k % 6, 64 + round(k / 6))
	RfmWalk(P, "group-30", G30, locate(45, 66, 1), "Move", 600)
	// 4. one unit walking to a dig 25 tiles away (a work order: approached by the order tick, not chained)
	var/turf/R = locate(38, 88, 1)
	R.density = 1; R.opacity = 1; R.CanDigAt = 1; R.icon_state = "StoneWall"; R.HP = 4000
	var/mob/Monsters/D = ObHuman(P, 10, 88)
	RfmTrack(list(D))
	P.Selected = list(D)
	usr = P
	sleep(3)
	var/t0 = world.time
	P.RemasterOrder(R, 0, "Mine")
	for(var/t = 0, t < 300 && get_dist(D, R) > 1, t++) sleep(1)
	sleep(5)
	RfmReport("work-walk", list(D), t0, list(R.x, R.y))
	// 5. one unit walking past six of yours fighting a tough NPC
	var/mob/Monsters/Human/E = new(locate(26, 98, 1), 1)
	E.HP = 100000
	E.MAXHP = 100000
	var/list/F = list()
	for(var/k = 0, k < 6, k++) F += ObHuman(P, 24 + k % 3, 99 - round(k / 3) * 2)
	P.Selected = F.Copy()
	usr = P
	P.RemasterAttackOrder(E)
	sleep(20)
	RfmWalk(P, "walk-by-fight", list(ObHuman(P, 10, 96)), locate(42, 96, 1))
	for(var/mob/Monsters/M in F)
		M.RemasterStopOrders()
		M.ChangeOwnership(null)
		del(M)
	del(E)
	rfm_on = 0
	world.log << "BK|complete"
