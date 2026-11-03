// Orders on the Sky level's open sky (rts-feel, 2026-10-25; the user: "so make the sky level clickable tiles"). In the obey
// arena with 3 layers (tools/check_arena.py --test sky_check.dm --entry SkRun --maxz 3): the Sky level (z 3) is open sky,
// with two mountain-top platforms ("Peak", rock under them on the ground). Each case: the hover verdict for the spot, then
// a click there (the order a 3D click gives), the units' order and track ticks for 15 s, then where they are.
//   A. one flyer over open sky, to open sky 15 tiles off: it gets there
//   B. six flyers, to open sky: all over open sky round it
//   C. a walker on a mountain top, to open sky: refused (it stays, the verdict says no one can)
//   D. three flyers and two walkers: the flyers go, the walkers stay
var/sk_n = 0

proc/SkSky(x0, y0, x1, y1)
	for(var/turf/T in block(locate(x0, y0, 3), locate(x1, y1, 3)))
		T.icon_state = "Sky"
		T.name = "Sky"
		T.Content = "Sky"
		T.density = 0

proc/SkPeak(x0, y0, x1, y1)
	for(var/turf/T in block(locate(x0, y0, 3), locate(x1, y1, 3)))
		T.icon_state = "Peak"
		T.name = "MountainPeak"
		T.Content = null
		T.Content3 = "Peak"
		T.density = 0
		ObRock(T.x, T.y, 1)

proc/SkFlyer(Player/P, x, y)
	var/mob/Monsters/M = ObHuman(P, x, y, 3, 0)
	M.Flying = 1
	M.rm_fly_level = 1
	return M

proc/SkVerdict(Player/P, list/U, turf/T)
	P.Selected = U.Copy()
	var/list/V = P.RemasterHoverVerdict(T)
	return V ? "[V["text"]] (ok [V["ok"]], bad [V["bad"]])" : "none"

proc/SkWhere(list/U)
	var/list/out = list()
	for(var/mob/Monsters/M in U)
		var/turf/T = M.loc
		out += "[M.Flying ? "flyer" : "walker"] [T ? "[T.x],[T.y],[T.z] [T.icon_state]" : "nowhere"] '[M.remaster_order_status]'"
	return jointext(out, "; ")

proc/SkRun()
	sleep(30)
	remaster_fog = 0
	var/Player/P = new(locate(100, 90, 1))
	P.UnitList = list()
	P.key = "skycheck"
	Players += P
	usr = P
	SkSky(1, 1, world.maxx, world.maxy)
	SkPeak(16, 16, 22, 24)
	SkPeak(16, 28, 22, 34)
	var/list/cases = list()
	// A
	var/list/A = list(SkFlyer(P, 30, 70))
	cases["A one flyer"] = list(A, locate(45, 70, 3))
	// B
	var/list/B = list()
	for(var/i = 0, i < 6, i++) B += SkFlyer(P, 28 + i % 3, 80 + round(i / 3))
	cases["B six flyers"] = list(B, locate(45, 82, 3))
	// C
	var/list/C = list(ObHuman(P, 20, 20, 3, 0))
	cases["C a walker on a mountain top"] = list(C, locate(32, 20, 3))
	// D
	var/list/D = list(SkFlyer(P, 24, 30), SkFlyer(P, 24, 31), SkFlyer(P, 24, 32), ObHuman(P, 19, 30, 3, 0), ObHuman(P, 19, 32, 3, 0))
	cases["D three flyers, two walkers"] = list(D, locate(36, 31, 3))
	for(var/k in cases)
		var/list/c = cases[k]
		var/list/U = c[1]
		var/turf/T = c[2]
		var/verdict = SkVerdict(P, U, T)
		var/list/before = list()
		for(var/mob/Monsters/M in U) before[M] = M.loc
		usr = P
		var/r = ObClick(P, U, T)
		for(var/t = 0, t < 150, t += REMASTER_TRACK_DELAY)
			usr = P
			ObTick(P)
			sleep(REMASTER_TRACK_DELAY)
		var/fly_ok = 1
		var/walk_still = 1
		var/list/spots = list()
		for(var/mob/Monsters/M in U)
			var/turf/L = M.loc
			if(M.Flying)
				if(!L || L.z != 3 || get_dist(L, T) > 2 || L.icon_state != "Sky" || (L in spots)) fly_ok = 0   // over open sky by it, one to a tile
				spots += L
			else if(L != before[M]) walk_still = 0
		world.log << "CK|[k]|[fly_ok && walk_still]|verdict: [verdict]; order [isnull(r) ? "none" : r]; after 15 s: [SkWhere(U)]"
	// E. a flyer over open sky can't land there (nothing below)
	var/mob/Monsters/F = SkFlyer(P, 60, 60)
	F.Fly(0, "Land")
	world.log << "CK|E a flyer over open sky can't land|[F.Flying]|Flying [F.Flying] at [F.x],[F.y],[F.z]"
	// F. one flyer, two spots queued with shift: it ends at the second
	var/mob/Monsters/Q = SkFlyer(P, 60, 40)
	usr = P
	ObClick(P, list(Q), locate(66, 40, 3))
	ObClick(P, list(Q), locate(66, 46, 3), 1)
	for(var/t = 0, t < 200, t += REMASTER_TRACK_DELAY)
		usr = P
		ObTick(P)
		sleep(REMASTER_TRACK_DELAY)
	world.log << "CK|F a flyer's queued spots over open sky|[Q.x == 66 && Q.y == 46 && Q.z == 3]|at [Q.x],[Q.y],[Q.z] '[Q.remaster_order_status]'"
	world.log << "CK|complete"
