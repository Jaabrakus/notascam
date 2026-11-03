// Capture check in the real client (temporary game copy only, tools/capture_real/capture_real.py). Beside the click
// audit's ZZClick.dm (its "setup" and "probe" steps), this reads its own steps from cap-scene.txt:
//   capsetup: the first unit carries a leather rope; a goblin scout lies knocked out three tiles north of it
//   capstate TAG: the goblin's state, for the runner
//   capaside: the captive's leader steps two tiles to the side (for the pictures)
//   capwake: the knocked-out captive comes to
//   capfind: after a restart, the captive found again among the player's units
//   capwood: the first unit carries a log of wood; captree: a tree four tiles from the captive
//   capshop: a Leatherworks beside the first unit, which carries a skin (Leather crafting 60)
//   capitems TAG: ropes lying near the first unit and carried by it
//   capweak: a second goblin tied with plant rope well away from your people, the camera there, its tries at the rope
//            every 0.2 s until it breaks free (the real roll and break-free code; only the 30 s wait is skipped)
//   caprevolt: five of your slaves together with no guards near, the revolt roll every 0.1 s until they rise; their spears
//              on the ground, one of yours 5 tiles off; a watcher logs CAP|rising (who struck, then who ran) within 30 s
var/cp_scene = ""
var/mob/Monsters/cp_goblin

world/New()
	..()
	spawn(55) CpLoop()

proc/CpLoop()
	while(1)
		sleep(2)
		if(!fexists("cap-scene.txt")) continue
		var/s = trimtext(file2text("cap-scene.txt"))
		if(!s || s == cp_scene) continue
		cp_scene = s
		var/Player/P = CkP()   // ZZClick.dm
		if(P) spawn(0) CpStep(P, s)

proc/CpStep(Player/P, s)
	var/list/a = splittext(s, " ")
	var/list/U = list()
	for(var/mob/Monsters/M in P.UnitList) if(M.HP > 0 && !M.rm_cap_state) U += M
	var/mob/Monsters/F = U[1]
	switch(a[1])
		if("capsetup")
			var/obj/Items/RemasterRope/LeatherRope/R = new(F.loc)
			F.ForcePickUpItem(R)
			var/turf/T = locate(F.x, F.y + 3, F.z)   // open ground beyond the line of units (in view, above the HUD)
			CkOpen(T)
			var/mob/Monsters/G = new /mob/Monsters/Goblin/NPC/Scout(T)
			G.destination = null
			G.RemasterKnockOut(F)
			G.remaster_ko_until = world.time + 6000   // stays down for the check
			cp_goblin = G
			world.log << "CAP|goblin|\ref[G]|[G.x],[G.y]|unit=[RemasterUIRef(F)]"
		if("capstate")
			var/mob/Monsters/G = cp_goblin
			var/mob/Monsters/L = G ? G.remaster_captive_lead : null
			var/mob/Monsters/K = G ? G.rm_cap_talker : null
			var/rl = ""
			if(G) for(var/list/X in Remaster3DLayers(G, Remaster3DBody64(G))) if(findtext("[X[1]]", "Rope64")) rl = replacetext("[X[1]]:[X[2]]", "|", "/")
			world.log << "CAP|state|[a[2]]|ko=[G && G.RemasterKnockedOut() ? 1 : 0]|layers=[rl]|state=[G ? G.rm_cap_state : "gone"]|mine=[G && G.Owner == P ? 1 : 0]|ref=[G ? RemasterUIRef(G) : "-"]|rope=[G ? G.rm_cap_rope_name : "-"]|lead=[L ? L.name : "-"]|talker=[K ? K.name : "-"]|loyalty=[G ? round(G.rm_cap_loyalty) : -1]|odds=[G ? G.RmCapEscapeOdds() : -1]|name=[G ? G.name : "-"]|armed=[G && (locate(/obj/Items/Equipment/Weapon) in G) ? 1 : 0]|tied=[G && G.rm_cap_tied ? 1 : 0]|post=[G ? G.rm_cap_post : 0]|kind=[G ? G.RmCapPostKind() : "-"]|at=[G && isturf(G.loc) ? "[G.x],[G.y]" : "-"]|status=[F.remaster_order_status]|notice=[P.remaster_notice]"
		if("capaside")   // the leader steps two tiles to the side, so the captive isn't hidden behind it (still on the leash)
			var/mob/Monsters/G = cp_goblin
			var/mob/Monsters/L = G ? G.remaster_captive_lead : null
			if(L)
				var/turf/T = locate(G.x + 2, G.y, G.z)
				CkOpen(T)
				L.loc = T
				L.destination = null
				L.dir = WEST
		if("capwake")
			var/mob/Monsters/G = cp_goblin
			if(G)
				G.remaster_ko_until = world.time - 1
				G.RemasterWakeUp()
		if("capapart")   // the second captive steps two tiles off the first line's tile so a click finds it alone
			for(var/mob/Monsters/M in rm_captives) if(M.Owner == P && M.name == "Goblin Two")
				var/turf/T = locate(M.x, M.y - 2, M.z)
				CkOpen(T)
				M.loc = T
		if("capline")   // two more goblins knocked out and tied on the leader's rope (a second line, then behind the shorter)
			var/mob/Monsters/G = cp_goblin
			var/mob/Monsters/L = G ? G.remaster_captive_lead : null
			if(!L) L = F
			for(var/i = 1, i <= 2, i++)
				var/turf/T = locate(L.x - 1 - i, L.y, L.z)
				CkOpen(T)
				var/mob/Monsters/X = new /mob/Monsters/Goblin/NPC/Scout(T)
				X.destination = null
				var/obj/Items/RemasterRope/LeatherRope/R = new(T)
				X.RmCapBind(P, L, R)
				X.name = "Goblin [i == 1 ? "Two" : "Three"]"
				X.rm_cap_roll_at = world.time + 100000
				var/mob/Monsters/XL = X.remaster_captive_lead
				world.log << "CAP|line|[RemasterUIRef(X)]|lead=[XL ? XL.name : "-"]"
			if(G) G.rm_cap_roll_at = world.time + 100000
		if("capcage")   // an empty wooden cage on the ground two tiles from the first captive
			var/mob/Monsters/G = cp_goblin
			var/turf/T = locate(G.x + 3, G.y + 2, G.z)   // a few tiles off: the leader takes them there
			CkOpen(T)
			var/obj/Items/Traps/Cages/WoodenCage/C = new(T)
			world.log << "CAP|cage|\ref[C]|[T.x],[T.y]"
		if("caplines")
			for(var/mob/Monsters/M in rm_captives) if(M.Owner == P)
				var/mob/Monsters/L = M.remaster_captive_lead
				world.log << "CAP|link|[M.name]|lead=[L ? L.name : "-"]|caged=[M.rm_cap_cage]|dist=[L ? get_dist(M, L) : -1]"
		if("capfind")
			for(var/mob/Monsters/M in P.UnitList) if(M.rm_cap_state) cp_goblin = M
			var/mob/Monsters/G = cp_goblin
			world.log << "CAP|found|[G ? RemasterUIRef(G) : "-"]|state=[G ? G.rm_cap_state : "-"]|rope=[G ? G.rm_cap_rope_name : "-"]|loyalty=[G ? round(G.rm_cap_loyalty) : -1]|tied=[G && G.rm_cap_tied ? 1 : 0]|name=[G ? G.name : "-"]|listed=[G && (G in rm_captives) ? 1 : 0]"
		if("capwood")   // the first unit carries a log of wood (a stake is cut from it)
			var/obj/Items/woods/wood/W = new(F.loc)
			F.ForcePickUpItem(W)
			world.log << "CAP|wood|[RemasterUIRef(F)]"
		if("captree")   // a tree a few tiles from the captive, in open ground
			var/mob/Monsters/G = cp_goblin
			var/turf/T = locate(G.x - 4, G.y + 1, G.z)
			for(var/atom/movable/O in T) if(!ismob(O)) del O
			new /turf/grounds/Trees/Tree1(T)
			ck_tiles["captree"] = T   // the click audit's probe reports where it is on screen (ZZClick.dm)
			world.log << "CAP|tree|[T.x],[T.y]"
		if("capshop")
			var/turf/T = locate(P.x + 1, P.y + 1, P.z)   // by the camera's middle, clear of the side panels whichever way it faces
			CkOpen(T)
			CkOpen(locate(T.x + 1, T.y, T.z))
			new /mob/WorkShops/LeatherWorks/Left(T)
			new /mob/WorkShops/LeatherWorks/Right(locate(T.x + 1, T.y, T.z))
			ck_tiles["forge"] = T   // the click audit's probe reports where it is on screen (ZZClick.dm)
			var/obj/Items/Skin/K = new(F.loc)
			F.ForcePickUpItem(K)
			F.LeatherCraftingSkill = 60
			world.log << "CAP|shop|[T.x],[T.y]|unit=[RemasterUIRef(F)]"
		if("capitems")
			var/lying = 0
			var/carried = 0
			for(var/obj/Items/RemasterRope/R in range(8, F)) if(isturf(R.loc)) lying++
			for(var/obj/Items/RemasterRope/R in F) carried++
			var/skins = 0
			for(var/obj/Items/Skin/K in F) skins++
			world.log << "CAP|items|[a[2]]|lying=[lying]|carried=[carried]|skins=[skins]|status=[F.remaster_order_status]|notice=[P.remaster_notice]"
		if("capweak")
			var/turf/T = locate(F.x - 10, F.y + 2, F.z)
			CkOpen(T)
			var/mob/Monsters/G2 = new /mob/Monsters/Goblin/NPC/Scout(T)
			G2.destination = null
			var/obj/Items/RemasterRope/PlantRope/R = new(T)
			G2.RmCapBind(P, F, R)
			G2.RmCapTieHere(P)
			P.loc = locate(T.x + 3, T.y, T.z)   // the camera goes there
			world.log << "CAP|weak|start|[RemasterUIRef(G2)]|odds=[G2.RmCapEscapeOdds()]"
			var/n = 0
			while(G2.rm_cap_state && n < 300)
				n++
				G2.rm_cap_roll_at = world.time
				sleep(2)
			var/turf/at = G2.loc
			sleep(30)
			var/logged = 0
			for(var/list/E in P.remaster_village_log) if(findtext("[E[2]]", "broke free")) logged = 1
			world.log << "CAP|weak|free=[G2.rm_cap_state ? 0 : 1]|tries=[n]|owner=[G2.Owner]|mine=[(G2 in P.UnitList) ? 1 : 0]|moved=[G2.loc != at ? 1 : 0]|logged=[logged]|id=\ref[G2]"
		if("caprevolt")
			var/turf/C0 = locate(F.x - 10, F.y + 5, F.z)
			var/list/S = list()
			for(var/i = 0, i < 5, i++)
				var/turf/T = locate(C0.x + i, C0.y, C0.z)
				CkOpen(T)
				var/mob/Monsters/V = new /mob/Monsters/Goblin/NPC/Scout(T)
				V.destination = null
				V.rm_cap_from = "{NPC Goblins}"
				V.rm_cap_rope = "plant"
				V.rm_cap_rope_name = "Plant Rope"
				V.rm_cap_rope_power = 20
				V.ChangeOwnership(P)
				V.RmCapDisarm(null)   // their spears on the ground beside them, as left when they were tied
				V.rm_cap_state = "slave"
				V.rm_cap_slave_at = world.time + 100000
				V.name = "{[P]} Slave [V.RmCapBareName()]"
				rm_captives |= V
				S += V
			P.loc = locate(C0.x + 2, C0.y - 1, C0.z)
			if(length(U) >= 2)   // one of yours 5 tiles off: someone for the armed ones to fall on
				var/mob/Monsters/Gd = U[2]
				var/turf/GT = locate(C0.x + 2, C0.y - 5, C0.z)
				CkOpen(GT)
				Gd.loc = GT
				Gd.destination = null
				Gd.remaster_defense_mode = "off"
			sleep(20)
			var/rounds = 0
			var/free = 0
			while(!free && rounds < 400)
				rounds++
				P.RmCapRevoltTick()
				for(var/mob/Monsters/V in S) if(!V.rm_cap_state) free++
				sleep(1)
			var/logged = 0
			for(var/list/E in P.remaster_village_log) if(findtext("[E[2]]", "revolt")) logged = 1
			spawn(0) CpWatchRising(P, S)
			world.log << "CAP|revolt|rose=[free]|rounds=[rounds]|logged=[logged]|notice=[P.remaster_notice]"
	world.log << "CAP|done|[s]"

// The rising after caprevolt: who took up a weapon, who went for one of yours, and who then ran.
proc/CpWatchRising(Player/P, list/S)
	var/list/hit = list()
	var/list/ran = list()
	for(var/t = 0, t < 150, t++)
		sleep(2)
		for(var/mob/Monsters/V in S)
			if(!V.loc) continue
			if(V.Target && ismob(V.Target) && V.Target:Owner == P) hit[V] = 1
			else if(hit[V] && !V.Target && V.HomeLoc) ran[V] = 1
		if(length(hit) && length(ran) >= length(hit)) break
	var/armed = 0
	for(var/mob/Monsters/V in S) if(V.loc) for(var/obj/Items/Equipment/Weapon/W in V) if(W.suffix == "(Equipped)")
		armed++
		break
	world.log << "CAP|rising|struck=[length(hit)]|ran=[length(ran)]|armed=[armed]|notice=[P.remaster_notice]"
