// Trade caravans (unlocked at Village rank, Progress.dm). Every couple of days a
// small band of merchants walks to the settlement's stockpile, stays a few minutes
// and leaves. Goods sold from the stockpile pay coins into the realm's treasury
// (Market.dm); coins buy their wares, which are put down on the stockpile. Caravans are never
// attack-move targets (Attack.dm).

#define RM_CARAVAN_EVERY_DAYS 2
#define RM_CARAVAN_STAY 3600      // ticks they stay once arrived (6 minutes)
#define RM_CARAVAN_WALK 3000      // ticks they try to reach the stockpile before setting up where they are (5 minutes)

mob/Monsters/var/tmp/remaster_caravan = 0

// What things are worth, by kind (barter units).
proc/RemasterTradeValue(obj/Items/I)
	if(!istype(I) || I.suffix == "(Equipped)") return 0
	// a great beast's parts (BeastParts.dm) and what taming uses (Taming.dm)
	if(istype(I, /obj/Items/RmBeastEgg)) return I:kind == "spider" ? 40 : 100
	if(istype(I, /obj/Items/Bones/DragonHeart)) return 60
	if(istype(I, /obj/Items/Bones/Bones/DragonBones)) return 15
	if(istype(I, /obj/Items/Bones/DragonScales)) return 12
	if(istype(I, /obj/Items/Bones/BeastFang/SpiderFang)) return 8
	if(istype(I, /obj/Items/Bones/BeastFang)) return 10
	if(istype(I, /obj/Items/Skin/WingHide)) return 15
	if(istype(I, /obj/Items/Glands/PoisonGland/VenomSac)) return 12
	if(istype(I, /obj/Items/RemasterTools/IronChains)) return 20
	if(istype(I, /obj/Items/Ingots/AdamantiumIngot)) return 80
	if(istype(I, /obj/Items/Ingots/GoldIngot)) return 30
	if(istype(I, /obj/Items/Ingots/SilverIngot)) return 20
	if(istype(I, /obj/Items/Ingots)) return 10
	if(istype(I, /obj/Items/gems)) return 25
	if(istype(I, /obj/Items/Potions)) return 15
	if(istype(I, /obj/Items/Equipment)) return 10 * max(1, Remaster3DTier(I))
	if(istype(I, /obj/Items/Skin)) return 5
	if(istype(I, /obj/Items/ores/stone)) return 1
	if(istype(I, /obj/Items/ores)) return 4
	if(istype(I, /obj/Items/woods)) return 2
	if(istype(I, /obj/Items/Food)) return 3
	if(istype(I, /obj/Items/Seeds)) return 3
	if(istype(I, /obj/Items/Bones)) return 1
	return 0

// Caravan wares: type path text, label, price, how many.
var/list/rm_caravan_wares = list(
	list("/obj/Items/Seeds/TomatoSeed", "Tomato seeds", 4, 6),
	list("/obj/Items/Seeds/GrapeSeed", "Grape seeds", 4, 6),
	list("/obj/Items/Shafts/WoodenSpade", "Wooden spade", 8, 2),
	list("/obj/Items/ores/Iron", "Iron ore", 6, 8),
	list("/obj/Items/ores/Silver", "Silver ore", 12, 4),
	list("/obj/Items/ores/Gold", "Gold ore", 18, 3),
	list("/obj/Items/gems/UnCutEmerald", "Uncut emerald", 30, 2),
	list("/obj/Items/gems/UnCutDiamond", "Uncut diamond", 40, 1),
	list("/obj/Items/Potions/EmptyBottle", "Empty bottle", 5, 6),
	list("/obj/Items/Food/Cheese", "Cheese", 4, 6),
	list("/obj/Items/RemasterHerb/Athelas", "Athelas", 5, 4),          // healing herbs (Doctor.dm)
	list("/obj/Items/RemasterHerb/Feverfew", "Feverfew", 5, 4),
	list("/obj/Items/RemasterHerb/MilkThistle", "Milk thistle", 6, 4),
	list("/obj/Items/RemasterSalt", "Rock salt", 3, 6))                 // keeps food (Ailments.dm)

Player/var
	remaster_caravan_day = 0          // saved: day of the last caravan
Player/var/tmp
	list/remaster_caravan             // the merchants here now
	list/remaster_caravan_stock       // id -> list(type, label, price, left)
	remaster_caravan_until = 0
	remaster_caravan_since = 0        // when they set off for the stockpile

Player/proc/RemasterCaravanTick()
	if(remaster_caravan)
		var/alive = 0
		for(var/mob/Monsters/M in remaster_caravan) if(M && M.HP > 0) alive++
		if(!alive || (remaster_caravan_until && world.time > remaster_caravan_until)) RemasterCaravanLeave()
		else if(!remaster_caravan_until)
			var/turf/S = RemasterStockpile() || RemasterProgressCenter()
			for(var/mob/Monsters/M in remaster_caravan) if(M && get_dist(M, S) <= 3)
				remaster_caravan_until = world.time + RM_CARAVAN_STAY
				RemasterNotice("The caravan has set up beside your stockpile. Trade in the Realm tab.")
				RemasterLog("A trade caravan set up at the stockpile", "good", S)
				break
			// Walls, water or shut doors in the way: after RM_CARAVAN_WALK they set up where they stopped. They used to
			// wait outside for good, and no other caravan ever came.
			if(!remaster_caravan_until && remaster_caravan_since && world.time - remaster_caravan_since > RM_CARAVAN_WALK)
				var/mob/Monsters/N
				for(var/mob/Monsters/M in remaster_caravan) if(M && M.HP > 0 && isturf(M.loc) && (!N || get_dist(M, S) < get_dist(N, S))) N = M
				if(N)
					remaster_caravan_until = world.time + RM_CARAVAN_STAY
					for(var/mob/Monsters/M in remaster_caravan) if(M) M.destination = null
					RemasterNotice("The caravan couldn't reach your stockpile and set up at [N.x], [N.y]. Trade in the Realm tab.")
					RemasterLog("A trade caravan set up at [N.x], [N.y]: it couldn't reach the stockpile", "good", N.loc)
		return
	if(!remaster_trade_open || remaster_days < remaster_caravan_day + RM_CARAVAN_EVERY_DAYS) return
	RemasterCaravanArrive()

Player/proc/RemasterCaravanArrive()
	var/turf/S = RemasterStockpile() || RemasterProgressCenter()
	if(!S) return 0
	var/turf/G
	for(var/tries = 0, tries < 30 && !G, tries++)
		var/a = rand(0, 359)
		var/turf/T = locate(clamp(round(S.x + cos(a) * 22), 2, world.maxx - 1), clamp(round(S.y + sin(a) * 22), 2, world.maxy - 1), S.z)
		if(T && !T.density) G = T
	if(!G) return 0
	remaster_caravan = list()
	for(var/i = 1, i <= 3, i++)
		var/mob/Monsters/M = new /mob/Monsters/Goblin(G)
		M.remaster_caravan = 1
		M.name = "{Caravan} [RemasterMakeName("Goblin", "Male")] the merchant"
		M.HomeLoc = S
		M.destination = S
		remaster_caravan += M
	remaster_caravan_stock = list()
	for(var/list/W in rm_caravan_wares)
		var/path = text2path(W[1])
		if(!path) continue
		if(prob(70)) remaster_caravan_stock["[length(remaster_caravan_stock) + 1]"] = list(path, W[2], W[3], rand(max(1, round(W[4] / 2)), W[4]))
	remaster_caravan_day = remaster_days
	remaster_caravan_until = 0
	remaster_caravan_since = world.time
	var/text = "A trade caravan is coming from the [RemasterRaidDirection(G, S)]."
	RemasterNotice(text)
	RemasterLog(text, "good", G)
	src << "<b><font color=#f2d27a>[text]</font></b>"
	spawn(0) RemasterCaravanWalk()
	return 1

// Merchants keep walking to the stockpile until they arrive.
Player/proc/RemasterCaravanWalk()
	while(remaster_caravan && !remaster_caravan_until)
		var/turf/S = RemasterStockpile() || RemasterProgressCenter()
		for(var/mob/Monsters/M in remaster_caravan) if(M && get_dist(M, S) > 2) M.destination = S
		sleep(20)

Player/proc/RemasterCaravanLeave()
	if(remaster_caravan)
		for(var/mob/Monsters/M in remaster_caravan) if(M) del(M)
	if(remaster_caravan_until) RemasterLog("The trade caravan moved on", "work", null)
	remaster_caravan = null
	remaster_caravan_stock = null
	remaster_caravan_until = 0

// What the caravan may buy: goods on any store (the main stockpile and every zone's area), as the stock counts see them
// (RemasterStockCount, Board.dm). It read only the 9 tiles round the stockpile's own tile, so goods on a painted
// stockpile or a yard were never offered. An item round two stores is offered once (the counts' per-call mark).
Player/proc/RemasterStockGoods()
	. = list()
	var/turf/S = RemasterStockpile()
	if(!S) return
	rm_sc_serial++
	var/mark = rm_sc_serial
	for(var/turf/T in RemasterStores())
		for(var/obj/Items/I in range(1, T)) if(isturf(I.loc) && I.rm_sc_mark != mark && RemasterTradeValue(I))
			I.rm_sc_mark = mark
			. += I

// value: "sell|<item name>" (sells all of that kind on the stockpile, one at a time per click: 1) or "buy|<id>"
Player/proc/RemasterTradeCommand(value)
	if(!remaster_caravan || !remaster_caravan_until)
		RemasterNotice("No caravan is set up at the stockpile.")
		return 0
	var/list/p = splittext("[value]", "|")
	if(p.len < 2) return 0
	var/turf/S = RemasterStockpile()
	if(!S) return 0
	if(p[1] == "sell")
		for(var/obj/Items/I in RemasterStockGoods()) if("[I.name]" == p[2])
			var/v = RemasterTradeValue(I)
			remaster_coins += v
			RemasterLog("Sold [I.name] for [v] coins", "work", S)
			del(I)
			return 1
		return 0
	if(p[1] == "buy")
		var/list/W = remaster_caravan_stock && remaster_caravan_stock[p[2]]
		if(!W || W[4] <= 0) return 0
		if(remaster_coins < W[3])
			RemasterNotice("Not enough coins: sell them something first.")
			return 0
		remaster_coins -= W[3]
		W[4]--
		var/type = W[1]
		new type(S)
		RemasterLog("Bought [W[2]] for [W[3]] coins", "good", S)
		return 1
	return 0

Player/proc/RemasterTradeData()
	if(!remaster_caravan) return null
	var/list/wares = list()
	if(remaster_caravan_stock) for(var/id in remaster_caravan_stock)
		var/list/W = remaster_caravan_stock[id]
		wares += list(list("id"=id, "label"=W[2], "price"=W[3], "left"=W[4]))
	var/list/goods = list()
	var/list/seen = list()
	for(var/obj/Items/I in RemasterStockGoods())
		var/n = "[I.name]"
		if(seen[n]) { seen[n]++; continue }
		seen[n] = 1
		goods += list(list("name"=n, "value"=RemasterTradeValue(I)))
	for(var/list/G in goods) G["count"] = seen[G["name"]]
	return list("here"=!!remaster_caravan_until, "credit"=remaster_coins, "wares"=wares, "goods"=goods,
		"stockpile"=!!RemasterStockpile(), "leavesMin"=(remaster_caravan_until ? max(0, round((remaster_caravan_until - world.time) / 600, 0.1)) : null))
