// PROTOTYPE scene to watch in a real game window (watch_prototype.py): a small mapless field with a
// stockpile with some wood, a wood, a rock face, three free workers, a builder and a few logs and stones
// left lying about. No lodge yet: the player drags one (+ Woodcutter's lodge / + Quarry lodge). Every 20
// seconds the Industry list is posted as a notice; every 90 seconds the village burns 3 wood.
world
	maxx = 60
	maxy = 44
	maxz = 2   // no sky level (the 3D view would draw it as a floor over everyone)
	turf = /turf/grounds/grass
	fps = 50

Player/Login()
	name = "Workplaces"
	winset(src, "mainwindow", "title=Land of Lords - Workplaces prototype (test arena)")
	loc = locate(31, 24, 1)
	Selected = list()
	UnitList = list()
	Players += src
	night = 0
	remaster_stock_x = 26; remaster_stock_y = 24; remaster_stock_z = 1
	// the wood, east
	for(var/i = 0, i < 12, i++)
		var/turf/T = locate(38 + (i % 4) * 2, 20 + round(i / 4) * 3, 1)
		T.Tree = 1; T.IsWood = 1; T.density = 1; T.opacity = 0; T.HP = RM_TREE_HP; T.name = "tree"
	// the rock face, north
	for(var/X = 23, X <= 29, X++) for(var/Y = 31, Y <= 33, Y++)
		var/turf/R = locate(X, Y, 1)
		R.CanDigAt = 1; R.IsWall = 0; R.density = 1; R.opacity = 0; R.icon_state = "StoneWall"; R.OIcon = "Grass"
		R.HP = 100; R.name = "rock"; R.remaster_vein = ""
	// some wood on the stockpile for the lodge's pieces
	for(var/i = 1, i <= 8, i++) new /obj/Items/woods/wood(locate(26, 24, 1))
	// three free workers and a builder in front of the stockpile
	for(var/n in list("Ada", "Bram", "Cole", "Dara"))
		var/mob/Monsters/Human/M = new(locate(27 + length(UnitList), 23, 1), 1)
		M.ChangeOwnership(src)
		M.name = n
		M.Age = 20
		M.WoodCuttingSkill = 40
		M.MineingSkill = 40
		M.Tiredness = 100
		M.Hunger = 100
		M.remaster_care_hold = world.time + 1000000
		M.ForcePickUpItem(new /obj/Items/Equipment/Weapon/Axes/MetalAxe)
		M.ForcePickUpItem(new /obj/Items/Equipment/Weapon/Picks/PickAxe)
		M.remaster_job = n == "Dara" ? "builder" : "board"
	// a few things left lying about, for the clean-up to find
	for(var/i = 1, i <= 3, i++) new /obj/Items/woods/wood(locate(38 + i * 2, 27, 1))
	for(var/i = 1, i <= 2, i++) new /obj/Items/ores/stone(locate(24 + i * 2, 29, 1))
	RemasterNotice("Prototype: Ada, Bram and Cole are free workers and Dara is a builder; nobody else has a job. In the Village stores bar, choose + Woodcutter's lodge (or + Quarry lodge) and drag a small yard on open ground. Dara puts up its banner and a bench. Use the banner to open the lodge's card: add a zone to tend (drag over the trees), and more upgrades. The free workers take up its benches by themselves.")
	spawn(100) WpWatchLoop(src)

proc/WpWatchLoop(Player/P)
	var/tick = 0
	while(P)
		sleep(200)
		tick++
		var/list/lines = list()
		for(var/list/D in P.RmWorkplaceData())
			lines += "[D["name"]]: workers [D["workers"]][length(D["who"]) ? " ([jointext(D["who"], ", ")])" : ""], store [D["stock"]]/[D["stop"]] [D["good"]]. [D["status"]]"
		P.RemasterNotice("Industry · [jointext(lines, " · ")]")
		if(!(tick % 5))
			// the village burns 3 wood
			var/used = 0
			for(var/turf/S in P.RemasterStores()) for(var/obj/Items/woods/wood/X in range(1, S)) if(isturf(X.loc) && used < 3)
				del X
				used++
			if(used) P.RemasterNotice("The village burned [used] wood. The woodlot will open again if the store drops below 6.")
