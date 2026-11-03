// The Cauldron (Remastered alchemy, part 3): a workshop built like the others
// (1 stone, one tile, from the Build menu or the 3D ghost). It holds 150 units -
// five bottles' worth - has its own fire (wood as fuel, a minute per piece, up to
// 160 degrees, cooling when it goes out), and is the only place the advanced
// recipes work (Brewing.dm). Units next to it add ingredients from their bags,
// pour water, feed and light the fire, and fill their Empty Bottles from it.

#define RM_CAULDRON_MAX 150
#define RM_CAULDRON_HEAT 160
#define RM_CAULDRON_FUEL_TIME 600   // ticks one piece of wood burns

mob/WorkShops/RemasterCauldron
	name = "Cauldron"
	icon = 'Icons/Remastered/Cauldron.dmi'
	icon_state = "cold"
	density = 1
	var/list/brew = list()
	var/brew_temp = 20
	var/fuel = 0          // ticks of burning left
	var/lit = 0

	New()
		..()
		spawn(10) RemasterCauldronLoop()

	DblClick()
		// The HUD's Alchemy box is the cauldron's menu; the original menus never open for it.
		if(istype(usr, /Player)) usr:RemasterNotice("Select a unit beside the Cauldron: its Alchemy box shows the Cauldron.")

mob/WorkShops/RemasterCauldron/proc/RemasterCauldronLoop()
	while(src && loc)
		sleep(10)
		if(lit && fuel > 0)
			fuel -= 10
			brew_temp = min(RM_CAULDRON_HEAT, brew_temp + max(3, (RM_CAULDRON_HEAT - brew_temp) * 0.08))
			if(fuel <= 0)
				lit = 0
				fuel = 0
		else
			lit = 0
			brew_temp = max(20, brew_temp - max(1, (brew_temp - 20) * 0.03))
		if(length(brew)) RemasterBrewReact(src, null)
		var/want = lit ? "lit" : "cold"
		if(icon_state != want) icon_state = want

proc/RemasterCauldronNear(mob/M)
	for(var/mob/WorkShops/RemasterCauldron/C in range(1, M)) return C
	return null

// value: "unitref|action|arg"; the cauldron is the one beside the unit.
Player/proc/RemasterCauldronCommand(value)
	var/list/p = splittext("[value]", "|")
	if(p.len < 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return 0
	var/mob/WorkShops/RemasterCauldron/C = RemasterCauldronNear(M)
	if(!C)
		RemasterNotice("[M.name] must stand beside the Cauldron.")
		return 0
	var/act = p[2]
	var/arg = p.len >= 3 ? p[3] : ""
	switch(act)
		if("add", "addall")
			var/obj/Items/first
			for(var/obj/Items/X in M) if(X.remaster_ui_id && X.remaster_ui_id == arg) first = X
			var/r = RemasterIngredient(first)
			if(!r) return 0
			var/list/items = act == "add" ? list(first) : list()
			if(act == "addall") for(var/obj/Items/X in M) if(RemasterIngredient(X) == r && X.suffix != "(Equipped)") items += X
			var/n = 0
			for(var/obj/Items/X in items)
				if(RemasterBrewTotal(C) + RM_BREW_PER_ITEM > RM_CAULDRON_MAX) break
				C.brew[r] = (C.brew[r] || 0) + RM_BREW_PER_ITEM
				M.weight -= X.weight
				del(X)
				n++
			if(!n) RemasterNotice("The Cauldron is full.")
			RemasterBrewReact(C, M)
			return n > 0
		if("water")
			// water from within 6 tiles of the cauldron (the unit carries it over)
			var/near = 0
			for(var/turf/T in range(6, C)) if(findtext(lowertext("[T.icon_state]"), "water") || (("CaveWater" in T.vars) && T.vars["CaveWater"]))
				near = 1
				break
			if(!near)
				RemasterNotice("There is no water within 6 tiles of the Cauldron.")
				return 0
			C.brew["water"] = (C.brew["water"] || 0) + min(30, RM_CAULDRON_MAX - RemasterBrewTotal(C))
			RemasterBrewReact(C, M)
			return 1
		if("fuel")
			for(var/obj/Items/woods/wood/W in M) if(W.suffix != "(Equipped)")
				C.fuel += RM_CAULDRON_FUEL_TIME
				M.weight -= W.weight
				del(W)
				C.lit = 1
				return 1
			RemasterNotice("[M.name] has no wood to feed the fire.")
			return 0
		if("light")
			if(C.fuel <= 0)
				RemasterNotice("Put wood under the Cauldron first.")
				return 0
			C.lit = !C.lit
			return 1
		if("bottle")
			// Each Empty Bottle the unit carries (or brew it drank or poured out) takes up to 30 units of the mix.
			var/n = 0
			for(var/obj/Items/Potions/E in RmEmptyBottles(M))
				var/total = RemasterBrewTotal(C)
				if(total < 1) break
				var/take = min(RM_BREW_MAX, total)
				var/obj/Items/Potions/RemasterBrew/B = istype(E, /obj/Items/Potions/RemasterBrew) ? E : new /obj/Items/Potions/RemasterBrew(M)
				B.suffix = "(Carrying)"
				B.brew_temp = C.brew_temp
				for(var/r in C.brew.Copy())
					var/u = C.brew[r] * take / total
					B.brew[r] = u
					C.brew[r] -= u
					if(C.brew[r] < 0.05) C.brew -= r
				if(B != E)
					M.weight += B.weight - E.weight
					del(E)
				RemasterBrewLook(B)
				n++
			if(!n) RemasterNotice(length(C.brew) ? "[M.name] has no Empty Bottles." : "The Cauldron is empty.")
			else RemasterNotice("[M.name] filled [n] bottle[n > 1 ? "s" : ""].")
			return n > 0
		if("empty")
			C.brew = list()
			return 1
	return 0

// HUD data for the cauldron beside a unit.
Player/proc/RemasterCauldronData(mob/Monsters/M)
	var/mob/WorkShops/RemasterCauldron/C = RemasterCauldronNear(M)
	if(!C) return null
	var/list/contents = list()
	var/main
	var/best = 0
	for(var/r in C.brew)
		var/list/R = rm_reagents[r]
		contents += list(list("name"=R[1], "units"=round(C.brew[r], 0.1), "color"=R[2]))
		if(C.brew[r] > best)
			best = C.brew[r]
			main = r
	var/list/ingredients = list()
	var/list/seen = list()
	for(var/obj/Items/I in M)
		var/r = RemasterIngredient(I)
		if(!r || I.suffix == "(Equipped)") continue
		var/list/R = rm_reagents[r]
		if(seen[r])
			seen[r]++
			continue
		seen[r] = 1
		ingredients += list(list("ref"=RemasterUIRef(I), "name"="[I.name]", "gives"=R[1], "id"=r))
	for(var/list/G in ingredients) G["count"] = seen[G["id"]]
	var/wood = 0
	for(var/obj/Items/woods/wood/W in M) wood++
	var/bottles = length(RmEmptyBottles(M))
	return list("temp"=round(C.brew_temp), "lit"=C.lit, "fuel"=round(C.fuel / 600, 0.1), "total"=round(RemasterBrewTotal(C)), "max"=RM_CAULDRON_MAX,
		"contents"=contents, "main"=(main ? RemasterReagentName(main) : null), "ingredients"=ingredients, "wood"=wood, "bottles"=bottles)

// What the 3D view needs: the brew's colour, how full, how hot, lit or not.
proc/Remaster3DCauldron(mob/WorkShops/RemasterCauldron/C)
	var/main
	var/best = 0
	for(var/r in C.brew) if(C.brew[r] > best)
		best = C.brew[r]
		main = r
	var/list/R = main ? rm_reagents[main] : null
	var/colour = R ? R[2] : null
	return list("color"=colour, "fill"=round(RemasterBrewTotal(C) / RM_CAULDRON_MAX, 0.05), "temp"=round(C.brew_temp), "lit"=C.lit)

proc/RemasterReagentName(id)
	var/list/R = rm_reagents[id]
	return R ? R[1] : "[id]"
