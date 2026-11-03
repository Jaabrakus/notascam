// The sky job in the real client (rts-feel, 2026-10-25; tools/rts_feel/real_feel.py --only sky). Temporary test copy only,
// after ZZClick.dm's setup. The runner writes a step to sky-scene.txt:
//   "skysetup"    three flyers (at their top height) and two walkers beside the scenario's site, all selected
//   "skyup"       the selection's Fly higher (HUD "flylevel up"): the flyers climb to the Sky level, the walkers stay
//   "skysel X"    select the flyers (X = flyers) or the walkers (X = walkers)
//   "skyprobe N"  tells the page (sky_hook.js) to report: SKYPROBE|N|<the flyers' middle x,y>
//   "skydown"     the flyers' Fly lower back to the surface
// Each logs CK|sky|<step>|<the player's level>|<sky open>|<each unit: kind x,y,z>.
var/sk_scene = ""
var/list/sk_fly = list()
var/list/sk_walk = list()

world/New()
	..()
	spawn(60) SkLoop()

proc/SkLoop()
	while(1)
		sleep(2)
		if(!fexists("sky-scene.txt")) continue
		var/s = trimtext(file2text("sky-scene.txt"))
		if(!s || s == sk_scene) continue
		sk_scene = s
		var/Player/P = CkP()
		if(P) spawn(0) SkStep(P, s)

proc/SkSay(Player/P, step)
	var/list/u = list()
	for(var/mob/Monsters/M in sk_fly + sk_walk) u += "[M.Flying ? "flyer" : "walker"] [M.x],[M.y],[M.z]"
	P.rm_sky_at = -100
	world.log << "CK|sky|[step]|[P.z]|[P.RmSkyOpen()]|[jointext(u, ";")]"

proc/SkStep(Player/P, s)
	var/list/a = splittext(s, " ")
	usr = P
	switch(a[1])
		if("skysetup")
			var/turf/C = ck_site
			if(!C) return
			sk_fly = list()
			sk_walk = list()
			for(var/i = 1, i <= 5, i++)
				var/turf/T = locate(C.x - 2 + i, C.y + 4, 1)
				CkOpen(T)
				var/mob/Monsters/Human/M = new(T, 1)
				M.ChangeOwnership(P)
				M.Age = 20
				M.Tiredness = 100
				M.Hunger = 100
				M.remaster_care_hold = world.time + 100000
				if(i <= 3)
					M.Flying = 1
					M.rm_fly_level = length(RmFlyHeights(M))
					sk_fly += M
				else sk_walk += M
			P.Selected = sk_fly + sk_walk
			SkSay(P, "setup")
		if("skyup")
			P.Selected = sk_fly + sk_walk
			P.RemasterTouchCommand("flylevel", "up")
			SkSay(P, "up")
		if("skysel")
			P.Selected = a[2] == "walkers" ? sk_walk.Copy() : sk_fly.Copy()
			SkSay(P, "sel [a[2]]")
		if("skyprobe")
			var/sx = 0
			var/sy = 0
			for(var/mob/Monsters/M in sk_fly)
				sx += M.x
				sy += M.y
			sx = round(sx / max(1, length(sk_fly)))
			sy = round(sy / max(1, length(sk_fly)))
			P.RemasterNotice("SKYPROBE|[a[2]]|[sx],[sy]")
			SkSay(P, "probe [a[2]]")
		if("skywhere") SkSay(P, "where [a[2]]")
		if("skydown")
			P.Selected = sk_fly.Copy()
			P.RemasterTouchCommand("flylevel", "down")
			SkSay(P, "down")
