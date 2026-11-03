// No-input repro (tools/formations/repro_select.py): the real run's scene (six, two archers with real bows and
// quivers), a box select of the six, the HUD data, then 5 s of the world running. Each step logs; a hang shows as the
// last line before it.
world
	maxx = 60
	maxy = 60
	maxz = 3
	turf = /turf/grounds/grass
	fps = 10

proc/ReproRun()
	sleep(10)
	var/Player/P = new(locate(30, 30, 1))
	usr = P
	var/list/U = list()
	var/list/types = list(/mob/Monsters/Human, /mob/Monsters/Human, /mob/Monsters/Human, /mob/Monsters/Dwarf, /mob/Monsters/Goblin, /mob/Monsters/Orc)
	var/list/kit = list("Sword", "Bow", "Sword", "Bow", "Sword", null)
	for(var/i = 1, i <= 6, i++)
		var/t = types[i]
		var/mob/Monsters/M = new t(locate(26 + i % 3, 28 + round(i / 3), 1))
		M.ChangeOwnership(P)
		M.Age = 20
		M.Hunger = 100
		M.Tiredness = 100
		M.remaster_care_hold = world.time + 100000
		if(!(M in P.UnitList)) P.UnitList += M
		for(var/obj/Items/I in M) if(I.suffix == "(Equipped)") M.UnEquipItem(I)
		M.HoldingWeapon = kit[i]
		M.MagicalAptitude = i == 6
		if(kit[i] == "Bow")
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
		U += M
		world.log << "REPRO|unit|[i]|holds=[M.HoldingWeapon]|arrows=[RemasterQuiverCount(M)]|role=[M.RemasterFormationRole()]"
	var/list/refs = list()
	for(var/mob/Monsters/M in U) refs += RemasterUIRef(M)
	world.log << "REPRO|boxrefs|start"
	P.Remaster3DBoxRefs("[jointext(refs, ",")]|0")
	world.log << "REPRO|boxrefs|sel=[length(P.Selected)]"
	for(var/mob/Monsters/M in U)
		M.RemasterUnitData(P)
		world.log << "REPRO|unitdata|[M.name]"
	P.RemasterHUDData()
	world.log << "REPRO|hud"
	// one archer alone (its bag and quiver in the data), then the six as a group (the groups' supplies)
	P.Selected = list(U[2])
	var/list/D1 = U[2].RemasterUnitData(P)
	var/list/q
	for(var/list/e in D1["items"]) if(!isnull(e["arrows"])) q = e
	world.log << "REPRO|quiver|[q ? "[q["arrows"]]|[length(q["arrowKinds"])]|[q["info"]]" : "none"]"
	P.Selected = U.Copy()
	P.RemasterGroupMake()
	var/list/CD = P.RemasterControlGroupsData()
	var/list/G1 = CD["groups"][1]
	var/list/S1 = G1["supply"]
	world.log << "REPRO|supply|arrows=[S1 ? S1["arrows"] : "-"]|archers=[S1 ? S1["archers"] : "-"]|medical=[S1 ? S1["medical"] : "-"]|throws=[S1 ? S1["throws"] : "-"]|food=[S1 ? S1["food"] : "-"]|kinds=[length(G1["bag"])]"
	var/list/HD = P.RemasterHUDData()
	world.log << "REPRO|hud2"
	var/mob/Monsters/W = U[1]
	W.HP = W.MAXHP * 0.3                       // one wounded
	P.rm_supply_cache = null
	P.Selected = U.Copy() - U[6]               // five: not a group
	HD = P.RemasterHUDData()
	var/list/SEL = HD["selSupply"]
	var/list/SU = SEL ? SEL["supply"] : null
	world.log << "REPRO|selsupply|n=[SU ? SU["n"] : "-"]|hp=[SU ? SU["hp"] : "-"]|maxhp=[SU ? SU["maxhp"] : "-"]|hurt=[SU ? SU["hurt"] : "-"]|arrows=[SU ? SU["arrows"] : "-"]|group=[SEL ? SEL["group"] : "-"]|kinds=[SEL ? length(SEL["bag"]) : "-"]"
	P.Selected = list(U[1])
	HD = P.RemasterHUDData()
	world.log << "REPRO|selsupply_one|[HD["selSupply"] ? "sent" : "none"]"
	for(var/k = 1, k <= 5, k++)
		sleep(10)
		P.RemasterOrdersTick()
		world.log << "REPRO|tick|[k]"
	world.log << "REPRO|done"
