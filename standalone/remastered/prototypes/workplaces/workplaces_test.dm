// Prototype scene, headless (Workplaces.dm, VillageStores.dm): lodges. A stockpile with some wood, a
// wood, three free board workers, a builder, and logs left lying about. A woodcutter's lodge is dragged
// the way the HUD does it; builders put up its banner, benches and upgrades through the normal
// construction tasks; a zone is dragged from its card; nobody is given a job by hand. Every WP| line
// must report 1.

proc/WpIndustry(Player/P, label)
	for(var/list/D in P.RmWorkplaceData())
		world.log << "WP|industry [label]: [D["name"]]|1|workers [D["workers"]] [jointext(D["who"], ", ")] · stores [D["stock"]]/[D["stop"]] [D["good"]] · brought in [D["total"]] · loose [D["loose"]] · [D["status"]]"

proc/WpTicks(Player/P, n)
	for(var/t = 1, t <= n, t++)
		ObTick(P)
		P.RemasterBoardTick()
		P.RemasterBlueprintTick()     // the builders (QoL.dm runs it for a connected player)
		sleep(5)

proc/WpLooseAt(x0, y0, x1, y1)
	. = 0
	for(var/turf/T in block(locate(x0, y0, 1), locate(x1, y1, 1))) for(var/obj/Items/woods/wood/X in T) if(!X.suffix) .++

proc/WpRun()
	sleep(30)
	var/Player/P = new(locate(60, 50, 1))
	P.UnitList = list()
	P.Selected = list()
	P.key = "workplaces"
	usr = P
	for(var/X = 30, X <= 70, X++) for(var/Y = 30, Y <= 70, Y++)
		var/turf/T = locate(X, Y, 1)
		T.density = 0; T.opacity = 0; T.CanDigAt = 0; T.Tree = 0
	P.remaster_stock_x = 40; P.remaster_stock_y = 40; P.remaster_stock_z = 1
	for(var/i = 1, i <= 8, i++) new /obj/Items/woods/wood(locate(40, 40, 1))
	for(var/i = 0, i < 10, i++)
		var/turf/T = ObTree(52 + (i % 5) * 2, 38 + round(i / 5) * 3)
		T.HP = RM_TREE_HP
	var/list/crew = list()
	for(var/i = 1, i <= 3, i++)
		var/mob/Monsters/M = ObHuman(P, 40 + i, 42)
		M.remaster_job = "board"
		crew += M
	var/mob/Monsters/B = ObHuman(P, 44, 42)
	B.remaster_job = "builder"
	B.name = "Dara"
	// 1. the lodge's yard is dragged; builders put up its banner and a bench
	P.RemasterTouchCommand("wppaint", "woodlot")
	world.log << "WP|+ Woodcutter's lodge puts the game's painting into lodge mode|[P.Function == "Piece:wp_woodlot" && RemasterTapPaintMode(P.Function) ? 1 : 0]|Function=[P.Function]"
	P.RemasterPaint("45|37|48|40")
	var/list/L = P.RmWorkplace("w1")
	world.log << "WP|dragging the yard plans the lodge, its banner and a bench|[L && P.RmLodgePlanned(L, "Piece:rmbanner") == 1 && P.RmLodgePlanned(L, "Piece:rmbench") == 1 && findtext(P.rm_wp_open, "w1") ? 1 : 0]|yard [L ? "[L["x0"]],[L["y0"]]-[L["x1"]],[L["y1"]]" : "-"] banner planned=[L ? P.RmLodgePlanned(L, "Piece:rmbanner") : 0] bench planned=[L ? P.RmLodgePlanned(L, "Piece:rmbench") : 0]"
	for(var/t = 0, t < 120 && (!length(P.RmLodgeBuilt(L, /obj/Items/Shafts/Sign/RmLodgeBanner)) || !P.RmLodgeSlots(L)), t++) WpTicks(P, 2)
	var/list/BN = P.RmLodgeBuilt(L, /obj/Items/Shafts/Sign/RmLodgeBanner)
	world.log << "WP|the builder puts up the banner and the bench|[length(BN) && P.RmLodgeSlots(L) == 1 ? 1 : 0]|banner=[length(BN)] benches=[P.RmLodgeSlots(L)] builder: [B.remaster_work_status]"
	// using the banner opens the card
	P.rm_wp_open = null
	if(length(BN))
		usr = P
		BN[1]:DblClick()
	world.log << "WP|using the banner opens the lodge's card|[findtext(P.rm_wp_open, "w1") ? 1 : 0]|[P.rm_wp_open]"
	// 2. a zone dragged from the card, and upgrades: a second bench, a store shed, a tool rack
	P.RemasterTouchCommand("wp", "w1|zone")
	P.RemasterPaint("51|36|61|44")
	world.log << "WP|a zone to tend is dragged from the card|[length(L["zones"]) == 1 ? 1 : 0]|zones=[length(L["zones"])]"
	P.RemasterTouchCommand("wp", "w1|upgrade|bench")
	P.RemasterTouchCommand("wp", "w1|upgrade|shed")
	P.RemasterTouchCommand("wp", "w1|upgrade|rack")
	P.RemasterTouchCommand("wp", "w1|upgrade|shed")     // a second shed is refused
	world.log << "WP|upgrades are planned for the builders|[P.RmLodgePlanned(L, "Piece:rmbench") == 1 && P.RmLodgePlanned(L, "Piece:rmshed") == 1 && P.RmLodgePlanned(L, "Piece:rmrack") == 1 ? 1 : 0]|bench=[P.RmLodgePlanned(L, "Piece:rmbench")] shed=[P.RmLodgePlanned(L, "Piece:rmshed")] rack=[P.RmLodgePlanned(L, "Piece:rmrack")]"
	// work at the mark: the stores' wood now and four more
	L["stop"] = P.RemasterStockCount("wood") + 4
	// logs left lying: three inside the zone, one just outside it
	for(var/i = 1, i <= 3, i++) new /obj/Items/woods/wood(locate(52 + i, 43, 1))
	new /obj/Items/woods/wood(locate(64, 40, 1))
	for(var/t = 0, t < 160 && (P.RmLodgeSlots(L) < 2 || !P.RmLodgeShed(L) || !length(P.RmLodgeBuilt(L, /obj/Items/Furniture/Pillars/WoodenBeam/RmToolRack))), t++) WpTicks(P, 2)
	world.log << "WP|benches set the worker slots|[P.RmLodgeSlots(L) == 2 ? 1 : 0]|benches=[P.RmLodgeSlots(L)]"
	world.log << "WP|the store shed and tool rack go up|[P.RmLodgeShed(L) && length(P.RmLodgeBuilt(L, /obj/Items/Furniture/Pillars/WoodenBeam/RmToolRack)) ? 1 : 0]|shed=[P.RmLodgeShed(L) ? 1 : 0] rack=[length(P.RmLodgeBuilt(L, /obj/Items/Furniture/Pillars/WoodenBeam/RmToolRack))]"
	L["stop"] = P.RemasterStockCount("wood") + 4
	// 3. free workers staff its benches by themselves and keep to its zone; the tool rack speeds them
	WpTicks(P, 24)
	var/staff = 0
	var/outside = 0
	var/boosted = 0
	for(var/mob/Monsters/M in crew)
		if(M.rm_wp_lodge == "w1") staff++
		if(M.rm_wp_boost) boosted++
		if(M.rm_wp_rect && M.remaster_active && (M.remaster_active.kind in list("Chop", "Mine")) && !RmInRect(M.remaster_active.target, M.rm_wp_rect)) outside++
	world.log << "WP|free workers fill its benches by themselves|[staff == 2 ? 1 : 0]|on the lodge=[staff]/2"
	world.log << "WP|they work inside its zone only|[!outside ? 1 : 0]|working outside=[outside]"
	world.log << "WP|the tool rack makes them faster|[boosted == staff && staff ? 1 : 0]|boosted=[boosted]"
	WpIndustry(P, "at work")
	// 4. they unload at the store shed
	var/turf/SH = P.RmLodgeShed(L)
	var/at_shed = 0
	for(var/t = 0, t < 120 && !at_shed, t++)
		WpTicks(P, 2)
		at_shed = 0
		for(var/obj/Items/woods/wood/X in range(1, SH)) if(isturf(X.loc) && !X.remaster_placed) at_shed++
	world.log << "WP|they unload at the lodge's store shed|[at_shed ? 1 : 0]|wood at the shed=[at_shed]"
	// 5. the stores reach the mark; they clear up what's left lying in the zone, then stand down
	for(var/t = 0, t < 160 && L["phase"] != "idle", t++) WpTicks(P, 4)
	var/inside_left = WpLooseAt(51, 36, 61, 44)
	var/outside_left = WpLooseAt(64, 40, 64, 40)
	world.log << "WP|before standing down they clear the zone|[L["phase"] == "idle" && !inside_left ? 1 : 0]|phase=[L["phase"]] logs left in the zone=[inside_left]"
	world.log << "WP|what lies outside its zone is not theirs|[outside_left == 1 ? 1 : 0]|logs outside=[outside_left]"
	var/busy = 0
	for(var/mob/Monsters/M in crew) if(M.remaster_board_claim || M.rm_wp_cleaning) busy++
	world.log << "WP|with the stores full and the zone clear they stand down|[!busy ? 1 : 0]|on a job=[busy]"
	WpIndustry(P, "stood down")
	// 6. the Village stores bar knows the shed
	P.rm_stores_at = -1000
	var/list/VS = P.RmVillageStores()
	var/named = 0
	for(var/list/w in VS["kinds"]["wood"]["where"]) if(findtext(w[1], "store shed")) named = 1
	world.log << "WP|the stores bar lists the lodge's store shed|[named ? 1 : 0]|"
	var/list/HD = P.RemasterHUDData()
	world.log << "WP|the HUD model has the stores and the lodge|[islist(HD["stores"]) && length(HD["workplaces"]) == 1 ? 1 : 0]|"
	P.RemasterTouchCommand("wp", "w1|remove")
	world.log << "WP|Remove takes the lodge away|[!P.RmWorkplace("w1") ? 1 : 0]|"
	world.log << "WP|complete|1|"
