// Coins and merchants. Each realm keeps a treasury of coins (saved). Caravans pay
// coins for stockpile goods and take coins for their wares (Trade.dm). A unit given
// the Merchant job walks to its realm's Market stall and stands there; whatever it
// carries is for sale at its value (Trade.dm) times the realm's markup. Another
// player's unit standing beside the stall can buy: the coins go from the buyer's
// treasury to the seller's, the item into the buyer's unit.

Player/var
	remaster_coins = 0                // saved: the realm's treasury
	remaster_markup = 100             // saved: stall prices, percent of value

mob/WorkShops/RemasterStall
	name = "Market stall"
	icon = 'Icons/Remastered/Runes.dmi'
	icon_state = "plate"
	density = 1

proc/RemasterStallPrice(obj/Items/I, Player/seller)
	return max(1, round(RemasterTradeValue(I) * (seller ? seller.remaster_markup : 100) / 100))

// The merchant tending a stall right now (its owner's unit on the job, next to it).
proc/RemasterStallMerchant(mob/WorkShops/RemasterStall/S)
	for(var/mob/Monsters/M in range(1, S)) if(M.Owner == S.Owner && M.remaster_job == "merchant" && M.HP > 0) return M
	return null

// Merchant job: walk to the nearest own stall and stay beside it.
mob/Monsters/proc/RemasterMerchantTick(Player/P)
	var/mob/WorkShops/RemasterStall/best
	var/bd = 1e9
	for(var/mob/WorkShops/RemasterStall/S in world) if(S.Owner == P && S.z == z)
		var/d = get_dist(src, S)
		if(d < bd)
			bd = d
			best = S
	if(!best)
		remaster_work_status = "Merchant: build a Market stall first (Work › Place a workshop)"
		return
	if(bd <= 1)
		destination = null
		var/n = 0
		for(var/obj/Items/I in src) if(I.suffix != "(Equipped)" && RemasterTradeValue(I)) n++
		remaster_work_status = n ? "Merchant: selling [n] item[n > 1 ? "s" : ""] at the stall" : "Merchant: at the stall, nothing to sell (give it goods)"
		return
	destination = best
	remaster_work_status = "Merchant: walking to the stall"

// The stall beside one of this player's selected units, and what it sells.
Player/proc/RemasterMarketData(mob/Monsters/M)
	if(!M) return null
	var/mob/WorkShops/RemasterStall/S
	for(var/mob/WorkShops/RemasterStall/X in range(2, M)) S = X
	if(!S) return null
	var/Player/seller = S.Owner
	var/mob/Monsters/merchant = RemasterStallMerchant(S)
	var/list/wares = list()
	if(merchant) for(var/obj/Items/I in merchant) if(I.suffix != "(Equipped)" && RemasterTradeValue(I))
		wares += list(list("ref"=RemasterUIRef(I), "name"="[I.name]", "price"=RemasterStallPrice(I, seller)))
	return list("own"=(seller == src), "seller"="[seller]", "merchant"=(merchant ? "[merchant.name]" : null), "wares"=wares,
		"coins"=remaster_coins, "markup"=(seller == src ? remaster_markup : null))

// value: "unitref|buy|itemref" or "unitref|markup|+10/-10"
Player/proc/RemasterMarketCommand(value)
	var/list/p = splittext("[value]", "|")
	if(p.len < 3) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return 0
	var/mob/WorkShops/RemasterStall/S
	for(var/mob/WorkShops/RemasterStall/X in range(2, M)) S = X
	if(!S) return 0
	var/Player/seller = S.Owner
	if(p[2] == "markup")
		if(seller != src) return 0
		remaster_markup = clamp(remaster_markup + text2num(p[3]), 50, 300)
		return 1
	if(p[2] != "buy" || seller == src) return 0
	var/mob/Monsters/merchant = RemasterStallMerchant(S)
	if(!merchant)
		RemasterNotice("No merchant is tending that stall: nothing to buy right now.")
		return 0
	for(var/obj/Items/I in merchant) if(I.remaster_ui_id && I.remaster_ui_id == p[3] && I.suffix != "(Equipped)")
		var/price = RemasterStallPrice(I, seller)
		if(remaster_coins < price)
			RemasterNotice("Not enough coins: [price] needed, the treasury has [remaster_coins].")
			return 0
		remaster_coins -= price
		if(istype(seller)) seller.remaster_coins += price
		RmQuestSold(I.type, price)   // the going rate on the quest post form (QuestAdaptive.dm)
		merchant.weight -= I.weight
		I.loc = M
		I.suffix = "(Carrying)"
		M.weight += I.weight
		RemasterLog("Bought [I.name] for [price] coins from [seller]'s market", "good", S)
		if(istype(seller)) seller.RemasterLog("[merchant.name] sold [I.name] for [price] coins", "good", S)
		return 1
	return 0
