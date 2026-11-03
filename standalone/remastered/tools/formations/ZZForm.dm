// Formations real-input run (temporary game copy only; tools/formations/real_formation.py). The runner writes a step
// to click-scene.txt; "probe N" asks the HUD page (the click audit's test hook) where units and tiles are on screen.
// The scene: six of yours (the race pick's people and more of other races) in a 3 x 2 block on open ground, open
// ground to the east, then a forest.
var/fm_scene = ""
var/turf/fm_site
var/list/fm_tiles = list()
var/list/fm_foes = list()

world/New()
	..()
	spawn(50) FmLoop()

proc/FmP()
	for(var/Player/P in world) if(P.client) return P

proc/FmLoop()
	while(1)
		sleep(2)
		night = 0
		if(!fexists("click-scene.txt")) continue
		var/s = trimtext(file2text("click-scene.txt"))
		if(!s || s == fm_scene) continue
		fm_scene = s
		var/Player/P = FmP()
		if(P) spawn(0) FmRun(P, s)

proc/FmOpen(turf/T)
	if(T && T.density)
		var/turf/grounds/grass/G = new(T)
		G.density = 0
	if(T) for(var/obj/O in T) if(!istype(O, /obj/Hud)) del(O)

proc/FmUnitLine(Player/P, mob/Monsters/M)
	var/datum/remaster_order/O = M.remaster_active
	return "[M.name]|ref=[RemasterUIRef(M)]|race=[M.Race]|role=[M.RemasterFormationRole()]|holds=[M.HoldingWeapon]|arrows=[RemasterQuiverCount(M)]|delay=[M.Delay]|at=[M.x],[M.y]|sel=[(M in P.Selected) ? 1 : 0]|active=[O ? O.kind : "-"]|goal=[O && O.target ? "[O.target:x],[O.target:y]" : "-"]|group=[O && O.group ? O.group.id : "-"]|atk=[M.remaster_attack && M.remaster_attack.target ? "\ref[M.remaster_attack.target]" : "-"]|status=[M.remaster_order_status]"

proc/FmRun(Player/P, s)
	var/list/a = splittext(s, " ")
	var/list/U = list()
	for(var/mob/Monsters/M in P.UnitList) if(M.HP > 0) U += M
	switch(a[1])
		if("setup")
			var/mob/Monsters/L = U[1]
			fm_site = locate(clamp(L.x, 30, world.maxx - 30), clamp(L.y, 30, world.maxy - 30), 1)
			var/sx = fm_site.x
			var/sy = fm_site.y
			for(var/turf/T in block(locate(sx - 16, sy - 10, 1), locate(sx + 18, sy + 10, 1))) FmOpen(T)
			for(var/turf/T in block(locate(sx - 45, sy - 45, 1), locate(sx + 45, sy + 45, 1))) P.RemasterMarkExplored(T)
			P.remaster_explore_version++
			for(var/mob/M in range(18, fm_site)) if(!(M in U) && M != P && !istype(M, /mob/WorkShops)) del(M)
			// six: the race pick's people, then others of other races
			var/list/more = list(/mob/Monsters/Dwarf, /mob/Monsters/Goblin, /mob/Monsters/Orc, /mob/Monsters/Kobold, /mob/Monsters/Lizardman, /mob/Monsters/Human)
			var/k = 1
			while(length(U) < 6)
				var/t = more[k++]
				var/mob/Monsters/N = new t(fm_site)
				N.ChangeOwnership(P)
				N.Age = 20
				N.Hunger = 100
				N.Tiredness = 100
				N.remaster_care_hold = world.time + 100000
				if(!(N in P.UnitList)) P.UnitList += N
				U += N
			var/i = 0
			var/list/kit = list("Sword", "Bow", "Sword", "Bow", "Sword", null)   // the sixth casts (MagicalAptitude)
			for(var/mob/Monsters/M in U)
				if(i < 6)
					for(var/obj/Items/I in M) if(I.suffix == "(Equipped)") M.UnEquipItem(I)
					M.HoldingWeapon = kit[i + 1]
					M.MagicalAptitude = i == 5
					if(kit[i + 1] == "Bow")
						// real archers: a bow, a quiver of six arrows (Combat - Bows.dm shoots only with arrows)
						var/obj/Items/Equipment/Weapon/Bows/WoodenBow/B = new(M)
						B.suffix = "(Carrying)"
						M.EquipItem(B)
						var/obj/Items/Equipment/Armour/Quiver/LeatherQuiver/Q = new(M)
						Q.suffix = "(Carrying)"
						M.EquipItem(Q)
						for(var/n = 1, n <= 6, n++)
							var/obj/Items/Arrows/R = new(Q)
							R.Owner = P
						Q.Content = 6
						M.BowSkill = max(M.BowSkill, 40)
				if(i < 6) M.loc = locate(sx - 12 + i % 3, sy - 1 + round(i / 3), 1)
				else M.loc = locate(sx - 15, sy + 8 + i, 1)    // more than six from the race pick: off to one side
				M.destination = null
				M.remaster_care_hold = world.time + 100000
				M.Hunger = 100
				M.Tiredness = 100
				i++
			// a forest east of the open ground: trees on about a third of the tiles round the forest spot
			for(var/X = sx + 5, X <= sx + 17, X++) for(var/Y = sy - 8, Y <= sy + 8, Y++)
				if(abs(X - (sx + 11)) <= 2 && abs(Y - sy) <= 2) continue   // a clearing for the click (a canopy over it took the click: a chop)
				if((X * 7 + Y * 13) % 10 < 3) new /turf/grounds/Trees/Tree1(locate(X, Y, 1))
			fm_tiles["ground"] = locate(sx - 1, sy + 2, 1)       // across open ground, 10 tiles east and a little north
			fm_tiles["forest"] = locate(sx + 11, sy, 1)          // in the forest
			fm_tiles["ground3"] = locate(sx - 3, sy - 2, 1)      // back west out of the forest, in the player's own layout
			fm_tiles["face2"] = locate(sx - 6, sy + 3, 1)        // a drag to face from mid1: two tiles north
			fm_tiles["boxa"] = locate(sx - 13, sy - 2, 1)        // a box round the six
			fm_tiles["boxb"] = locate(sx - 9, sy + 2, 1)
			fm_tiles["mid1"] = locate(sx - 6, sy + 1, 1)         // camera spots: over the first move, over the second
			fm_tiles["mid2"] = locate(sx + 5, sy + 1, 1)
			P.remaster_3d = 1
			P.remaster_cine = null
			P.remaster_formation = "keep"
			P.remaster_formations = list()
			P.Selected = list()
			P.loc = fm_tiles["mid1"]
			world.log << "CK|site|[sx],[sy]"
			for(var/mob/Monsters/M in U) world.log << "CK|unit|[M.name]|[RemasterUIRef(M)]"
		if("foes")
			for(var/mob/Monsters/E in fm_foes) del(E)        // a fresh set each time ("foes 2" for the A-click)
			fm_foes = list()
			world.log << "CK|foeset|[length(a) > 1 ? a[2] : "1"]"
			// four sleeping enemies east of the open ground: two with bows, two with swords
			for(var/i = 0, i < 4, i++)
				var/turf/FT = locate(fm_site.x + 3 + i, fm_site.y + 2 + (i % 2), 1)
				FmOpen(FT)
				var/mob/Monsters/E = new /mob/Monsters/Goblin/NPC/Scout(FT)
				E.Sleeping = 1
				E.CanWalk = 0              // held where they are (the goblins' RandomWalk walks only when CanWalk)
				E.destination = null
				E.HP = 100000
				E.MAXHP = 100000
				// real weapons in hand (a scout's own is put away): two bows, two swords; the A-click's kind follows what they hold
				for(var/obj/Items/Equipment/Weapon/W in E) if(W.suffix == "(Equipped)") E.UnEquipItem(W)
				var/obj/Items/Equipment/Weapon/NW = i < 2 ? new /obj/Items/Equipment/Weapon/Bows/WoodenBow(E) : new /obj/Items/Equipment/Weapon/Swords/Gladius(E)
				NW.suffix = "(Carrying)"
				E.EquipItem(NW)
				fm_foes += E
				fm_tiles["foe[i]"] = FT          // the probe reports where each is on screen
				world.log << "CK|foe|\ref[E]|[E.HoldingWeapon]|[E.x],[E.y]|foe[i]"
		if("look")
			// the player's camera spot (the 3D view follows it): over the first move or the second
			P.loc = fm_tiles[a[2]]
		if("probe")
			var/list/parts = list()
			for(var/k in fm_tiles)
				var/turf/T = fm_tiles[k]
				parts += "[k]:[T.x],[T.y],0"
			P.RemasterNotice("CKPROBE|[a[2]]|[jointext(parts, ";")]")
		if("state")
			world.log << "CK|state|[a[2]]|sel=[length(P.Selected)]|attackmode=[P.remaster_attack_mode]|formation=[P.remaster_formation]"
			for(var/mob/Monsters/M in U) world.log << "CK|u|[a[2]]|[FmUnitLine(P, M)]"
			for(var/mob/Monsters/E in fm_foes) if(E.loc) world.log << "CK|f|[a[2]]|\ref[E]|[E.HoldingWeapon]|[E.RemasterFormationRole()]|sleep=[E.Sleeping]"
			var/list/gs = list()
			for(var/k = 1, k <= 9, k++) if(length(P.RemasterGroupMembers(k))) gs += "[k]:[length(P.RemasterGroupMembers(k))]"
			world.log << "CK|g|[a[2]]|[jointext(gs, ",")]|sel=[length(P.Selected)]|selgroup=[P.RemasterSelectedGroup()]"
	world.log << "CK|done|[s]"
