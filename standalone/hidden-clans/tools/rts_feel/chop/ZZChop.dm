// The chop hitch (rts-feel, 2026-10-25; the user: "i notice a hitch in actions when i click on a units to chop wood when they
// are moving there i think it hitched maybe 2-3 times"). Temporary test copy only (tools/rts_feel/real_feel.py --only chop,
// after ZZClick.dm's setup). The runner writes a step to chop-scene.txt:
//   "chopsetup"  30 more Humans with axes beside the scenario's units, three groves 13-17 tiles out, Gather on
//   "chopgo N"   tells the page (tools/rts_feel/chop/chop_hook.js) to start: CHOPGO|N|<grove tiles> as a notice
var/zc_scene = ""
var/list/zc_groves = list()

world/New()
	..()
	spawn(60) ZcLoop()

proc/ZcLoop()
	while(1)
		sleep(2)
		if(!fexists("chop-scene.txt")) continue
		var/s = trimtext(file2text("chop-scene.txt"))
		if(!s || s == zc_scene) continue
		zc_scene = s
		var/Player/P = CkP()
		if(P) spawn(0) ZcRun(P, s)

proc/ZcRun(Player/P, s)
	var/list/a = splittext(s, " ")
	switch(a[1])
		if("chopsetup")
			var/turf/C = ck_site
			if(!C) return
			usr = P
			for(var/i = 1, i <= 30, i++)
				var/turf/T = locate(C.x - 6 + (i % 10), C.y - 3 + round(i / 10), 1)
				CkOpen(T)
				var/mob/Monsters/Human/M = new(T, 1)
				M.ChangeOwnership(P)
				M.Age = 20
				M.WoodCuttingSkill = 100
				M.Tiredness = 100
				M.Hunger = 100
				M.remaster_care_hold = world.time + 100000   // no trips to the fire or bed mid-test
				M.ForcePickUpItem(new /obj/Items/Equipment/Weapon/Axes/MetalAxe)
			for(var/mob/Monsters/M in P.UnitList)
				M.WoodCuttingSkill = max(M.WoodCuttingSkill, 100)
				if(!(locate(/obj/Items/Equipment/Weapon/Axes) in M)) M.ForcePickUpItem(new /obj/Items/Equipment/Weapon/Axes/MetalAxe)
			// three groves of six trees: east, north-east, west
			zc_groves = list()
			for(var/list/g in list(list(15, 0), list(12, 9), list(-15, 2)))
				var/list/trees = list()
				for(var/k = 0, k < 6, k++)
					var/turf/T = locate(C.x + g[1] + (k % 3) * 2, C.y + g[2] + round(k / 3) * 2, 1)
					if(!T) continue
					for(var/obj/O in T) if(!istype(O, /obj/Hud)) del(O)
					new /turf/grounds/Trees/Tree1(T)
					trees += T
				zc_groves += list(trees)
			P.remaster_gather = 1
			if(P.client) P << output("1", "mapwindow.hud:gather3d")
			P.Selected = list()
			world.log << "CK|chop|setup|units=[length(P.UnitList)]|groves=[length(zc_groves)]"
		if("chopgo")
			var/list/parts = list()
			for(var/list/trees in zc_groves)
				var/turf/T = trees[1]
				parts += "[T.x],[T.y]"
			P.RemasterNotice("CHOPGO|[a[2]]|[jointext(parts, ";")]")
			world.log << "CK|chop|go|[a[2]]"
