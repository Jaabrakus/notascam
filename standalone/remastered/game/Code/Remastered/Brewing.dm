// Brewing (Remastered alchemy, part 2).
// Reagents work the way tgstation's chemistry does: a brew holds amounts of
// reagents; a recipe fires when every reagent it needs is there in its ratio and
// the brew is hot enough; the number of batches is the smallest amount / ratio,
// that much of each is used and the products are added. Heating moves the brew's
// temperature toward the fire's and re-checks the recipes at each step.
// Ingredients are the game's own items (fruit, glands, roots, bones, blood, meat,
// fungus, gems) plus water drawn from a lake or river. A brew sits in an Empty
// Bottle. Drinking applies the brew; throwing bursts it into a cloud on the target
// tile (Vapours.dm), so a Sleeping Draught becomes sleeping mist and Alchemist's
// Fire becomes burning firedamp.

#define RM_BREW_MAX 30
#define RM_BREW_PER_ITEM 5
#define RM_BREW_FIRE_HEAT 140
#define RM_THROW_RANGE 7

// id -> list(name, colour, gas when burst (or null), gas per unit)
var/list/rm_reagents = list(
	"water"=list("Water", "#4a8ad0", "steam", 0.3),
	"juice"=list("Fruit juice", "#c0405a", null, 0),
	"venom"=list("Venom", "#5aa030", "poison", 0.8),
	"rootsap"=list("Root sap", "#8a6a3a", null, 0),
	"bonedust"=list("Bone dust", "#e0d8c0", "smoke", 0.5),
	"blood"=list("Blood", "#8a1010", null, 0),
	"meat"=list("Meat", "#a05040", null, 0),
	"fungus"=list("Fungus", "#9a8a6a", "smoke", 0.3),
	"rubydust"=list("Ruby dust", "#e03030", null, 0),
	"emeralddust"=list("Emerald dust", "#30c060", null, 0),
	"diamonddust"=list("Diamond dust", "#c8e8ff", "mana", 0.3),
	"healing"=list("Healing Draught", "#ff6070", "heal", 1.2),
	"sleepdraught"=list("Sleeping Draught", "#a080e0", "sleep", 1.2),
	"poison"=list("Venom Draught", "#70d040", "poison", 1.3),
	"firewater"=list("Alchemist's Fire", "#ffa020", "firedamp", 1.2),
	"mana"=list("Mana Elixir", "#40a8ff", "mana", 1.2),
	"smokepowder"=list("Smoke Powder", "#909098", "smoke", 2),
	"tonic"=list("Strength Tonic", "#c03020", "steam", 0.3),
	"elixir"=list("Elixir of Life", "#ffd0e8", "heal", 2.5),
	"dragonfire"=list("Dragonfire", "#ff5010", "firedamp", 3),
	"stoneskin"=list("Stoneskin Draught", "#9a9488", "smoke", 0.5),
	"plague"=list("Plague", "#6a7a30", "miasma", 3),
	"archmana"=list("Archmage's Draught", "#7a60ff", "mana", 2.5),
	"antidote"=list("Antidote", "#3c3a36", null, 0),
	"wine"=list("Wine", "#7a1f3d", null, 0),
	"dragonblood"=list("Dragon's Blood", "#b01010", "firedamp", 0.6),   // a dragon's heart (BeastParts.dm)
	"dragonheart"=list("Dragonheart Draught", "#ff4818", "steam", 0.3))   // Ailments.dm   // bone char against poisoned food (FoodSupply.dm)

// list(needs (id -> parts), makes (id -> parts), minimum temperature, message)
var/list/rm_recipes = list(
	list(list("water"=2, "juice"=1), list("healing"=3), 60, "The brew turns a warm red."),
	list(list("juice"=2, "emeralddust"=1), list("healing"=4), 60, "The emerald dust blooms; the brew glows."),
	list(list("juice"=1, "rootsap"=1), list("sleepdraught"=2), 0, "The brew clouds over, smelling of poppies."),
	list(list("venom"=2, "water"=1), list("poison"=3), 60, "The brew bubbles a sickly green."),
	list(list("rubydust"=1, "bonedust"=1, "water"=1), list("firewater"=3), 90, "The brew catches an inner flame!"),
	list(list("diamonddust"=1, "water"=2), list("mana"=3), 90, "The brew shimmers blue."),
	list(list("bonedust"=2, "fungus"=1), list("smokepowder"=3), 0, "The mix dries to a grey powder."),
	list(list("meat"=2, "blood"=1), list("tonic"=3), 60, "The brew thickens to a red tonic."),
	// Cauldron only: hotter, rarer, stronger.
	list(list("healing"=2, "emeralddust"=1, "diamonddust"=1), list("elixir"=3), 140, "The cauldron glows rose-gold: an Elixir of Life!", 1),
	list(list("firewater"=2, "rubydust"=1), list("dragonfire"=3), 150, "The cauldron roars with Dragonfire!", 1),
	list(list("tonic"=1, "bonedust"=2, "water"=1), list("stoneskin"=3), 120, "The brew sets grey and heavy as stone.", 1),
	list(list("poison"=1, "blood"=1, "fungus"=1), list("plague"=3), 100, "A choking reek rises: Plague.", 1),
	list(list("mana"=2, "diamonddust"=1), list("archmana"=3), 140, "The cauldron hums with an Archmage's Draught.", 1),
	list(list("dragonblood"=1, "tonic"=1, "water"=1), list("dragonheart"=3), 150, "The cauldron beats like a heart: a Dragonheart Draught!", 1),
	// Bone char draws poison out, as tgstation's charcoal does.
	list(list("bonedust"=1, "water"=2), list("antidote"=3), 100, "The bone dust chars black in the boiling water: an Antidote."),
	// Fungus ferments fruit juice into wine (Ailments.dm).
	list(list("juice"=2, "fungus"=1), list("wine"=3), 0, "The juice froths: wine."))

// Which reagent an item gives.
proc/RemasterIngredient(obj/Items/I)
	if(!I) return null
	if(istype(I, /obj/Items/Food/Grape) || istype(I, /obj/Items/Food/Tomato)) return "juice"
	if(istype(I, /obj/Items/Food/Fungus)) return "fungus"
	if(istype(I, /obj/Items/Food/Meat)) return "meat"
	if(istype(I, /obj/Items/Glands/PoisonRoots)) return "rootsap"
	if(istype(I, /obj/Items/Glands)) return "venom"
	if(istype(I, /obj/Items/Bones/BloodyLimb)) return I:rm_from_race == "Gargoyle" ? null : "blood"   // a gargoyle's limb is stone (StoneLimbs.dm)
	if(istype(I, /obj/Items/Bones/DragonHeart)) return "dragonblood"   // BeastParts.dm
	if(istype(I, /obj/Items/Bones/Bones) || istype(I, /obj/Items/Bones/Skull) || istype(I, /obj/Items/Bones/Shell)) return "bonedust"
	if(istype(I, /obj/Items/gems/UnCutRuby) || istype(I, /obj/Items/gems/Ruby)) return "rubydust"
	if(istype(I, /obj/Items/gems/UnCutEmerald) || istype(I, /obj/Items/gems/Emerald)) return "emeralddust"
	if(istype(I, /obj/Items/gems/UnCutDiamond) || istype(I, /obj/Items/gems/Diamond)) return "diamonddust"
	return null

obj/Items/Potions/RemasterBrew
	// its values: art/items/catalogue.json row potions.remasterbrew (export_items.py writes ItemData.dm)
	var/list/brew = list()   // reagent id -> units
	var/brew_temp = 20

proc/RemasterBrewTotal(atom/B)
	. = 0
	var/list/L = B:brew
	for(var/r in L) . += L[r]

proc/RemasterBrewMain(obj/Items/Potions/RemasterBrew/B)
	var/best = 0
	for(var/r in B.brew) if(B.brew[r] > best)
		best = B.brew[r]
		. = r

proc/RemasterBrewLook(obj/Items/Potions/RemasterBrew/B)
	var/main = RemasterBrewMain(B)
	if(!main)
		B.name = "Empty Bottle"
		B.icon_state = "Empty"
		B.desc = "An empty bottle: brew in it again, or fill it at the Cauldron."   // not the brew it held
		return
	var/list/R = rm_reagents[main]
	B.name = "[R[1]] ([round(RemasterBrewTotal(B))])"
	var/list/look = list("elixir"="SparklePotion", "dragonfire"="SparklePotion", "stoneskin"="PurplePotion", "plague"="GreenPotion", "archmana"="BluePotion", "wine"="BloodPotion", "dragonblood"="BloodPotion", "dragonheart"="SparklePotion", "healing"="RedPotion", "tonic"="BloodPotion", "mana"="BluePotion", "poison"="GreenPotion", "sleepdraught"="PurplePotion", "firewater"="SparklePotion", "venom"="GreenPotion", "blood"="BloodPotion", "water"="BluePotion", "juice"="RedPotion")
	B.icon_state = look[main] || "PurplePotion"
	var/list/parts = list()
	for(var/r in B.brew)
		var/list/X = rm_reagents[r]
		parts += "[round(B.brew[r], 0.1)] [X[1]]"
	B.desc = "An alchemist's brew at [round(B.brew_temp)] degrees: [jointext(parts, ", ")]."

// tg-style reaction check: every reagent present in its ratio, hot enough; batches
// = the smallest amount / ratio. Repeats until nothing more reacts.
// B is a bottle (RemasterBrew) or a Cauldron: both hold "brew" and "brew_temp".
// Recipes marked cauldron-only (a fifth entry) need the Cauldron.
proc/RemasterBrewReact(atom/B, mob/witness)
	var/reacted = 0
	var/list/brew = B:brew
	var/in_cauldron = istype(B, /mob/WorkShops/RemasterCauldron)
	for(var/pass = 1, pass <= 5, pass++)
		var/any = 0
		for(var/list/R in rm_recipes)
			var/list/needs = R[1]
			if(B:brew_temp < R[3]) continue
			if(length(R) >= 5 && R[5] && !in_cauldron) continue
			var/batches = 1#INF
			for(var/r in needs) batches = min(batches, (brew[r] || 0) / needs[r])
			batches = round(batches, 0.1)
			if(batches < 0.1) continue
			for(var/r in needs)
				brew[r] -= needs[r] * batches
				if(brew[r] < 0.05) brew -= r
			var/list/makes = R[2]
			for(var/r in makes) brew[r] = (brew[r] || 0) + makes[r] * batches
			if(witness && ismob(witness.Owner)) witness.Owner << "[in_cauldron ? "The cauldron" : witness.name]: [R[4]]"
			any = 1
			reacted = 1
		if(!any) break
	if(istype(B, /obj/Items/Potions/RemasterBrew)) RemasterBrewLook(B)
	return reacted

// The unit's brew, the one its Alchemy box shows and works on: the bottle it last brewed in (or was shown) while
// that is in its bag and holds something, else the first that holds something (a drunk bottle never hides the full
// ones), else an empty one. make: a bottle to add that much to - a full one gives way to an empty one, or an Empty
// Bottle turned into one.
mob/Monsters/var/tmp/obj/Items/Potions/RemasterBrew/rm_brew_now
Player/proc/RemasterBrewOf(mob/Monsters/M, make = 0)
	var/obj/Items/Potions/RemasterBrew/B = M.rm_brew_now
	if(B && (Rm3DGone(B) || B.loc != M || !length(B.brew))) B = null
	if(!B) for(var/obj/Items/Potions/RemasterBrew/X in M) if(length(X.brew))
		B = X
		break
	if(make && B && RemasterBrewTotal(B) + make > RM_BREW_MAX) B = null   // full: brew in another bottle
	if(!B) for(var/obj/Items/Potions/RemasterBrew/X in M) if(!length(X.brew))
		B = X
		break
	if(!B && make) for(var/obj/Items/Potions/EmptyBottle/E in M)
		B = new(M)
		B.suffix = "(Carrying)"
		M.weight += B.weight - E.weight
		del(E)
		RemasterBrewLook(B)
		break
	M.rm_brew_now = B
	return B

// The bottles a unit can fill: Empty Bottles, and brews drunk or poured out.
proc/RmEmptyBottles(mob/M)
	. = list()
	for(var/obj/Items/Potions/P in M) if(istype(P, /obj/Items/Potions/EmptyBottle) || (istype(P, /obj/Items/Potions/RemasterBrew) && !length(P:brew))) . += P

proc/RemasterNearWater(mob/M)
	for(var/turf/T in range(1, M))
		if(findtext(lowertext("[T.icon_state]"), "water") || (("CaveWater" in T.vars) && T.vars["CaveWater"])) return 1
	return 0

proc/RemasterNearFire(mob/M)
	for(var/mob/WorkShops/CampFires/Fire/F in range(2, M)) return RM_BREW_FIRE_HEAT   // a campfire (its altars are CampFires too)
	for(var/turf/T in range(2, M))
		var/datum/rm_air/A = rm_air_of[T]
		if(A && A.burning) return max(RM_BREW_FIRE_HEAT, round(A.temp))
	return 0

mob/Monsters/var/tmp/remaster_heating = 0

// value: "unitref|action|arg"
Player/proc/RemasterBrewCommand(value)
	var/list/p = splittext("[value]", "|")
	if(p.len < 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return 0
	var/act = p[2]
	var/arg = p.len >= 3 ? p[3] : ""
	switch(act)
		if("add")
			var/obj/Items/I
			for(var/obj/Items/X in M) if(X.remaster_ui_id && X.remaster_ui_id == arg) I = X
			var/r = RemasterIngredient(I)
			if(!I || I.loc != M || !r) return 0
			var/obj/Items/Potions/RemasterBrew/B = RemasterBrewOf(M, RM_BREW_PER_ITEM)
			if(!B)
				RemasterNotice("[M.name] needs an Empty Bottle to brew in.")
				return 0
			if(RemasterBrewTotal(B) + RM_BREW_PER_ITEM > RM_BREW_MAX)
				RemasterNotice("The bottle is full.")
				return 0
			B.brew[r] = (B.brew[r] || 0) + RM_BREW_PER_ITEM
			M.weight -= I.weight
			del(I)
			RemasterBrewReact(B, M)
			return 1
		if("water")
			var/obj/Items/Potions/RemasterBrew/B = RemasterBrewOf(M, 1)
			if(!B)
				RemasterNotice("[M.name] needs an Empty Bottle to brew in.")
				return 0
			if(!RemasterNearWater(M))
				RemasterNotice("[M.name] must stand by water to fill the bottle.")
				return 0
			B.brew["water"] = (B.brew["water"] || 0) + min(10, RM_BREW_MAX - RemasterBrewTotal(B))
			RemasterBrewReact(B, M)
			return 1
		if("heat")
			var/obj/Items/Potions/RemasterBrew/B = RemasterBrewOf(M)
			if(!B || !length(B.brew)) return 0
			var/heat = RemasterNearFire(M)
			if(!heat)
				RemasterNotice("[M.name] needs a campfire (or fire) within 2 tiles to heat the brew.")
				return 0
			if(M.remaster_heating) return 1
			M.remaster_heating = 1
			spawn(0)
				// 15 seconds over the fire; it warms toward the fire's heat.
				for(var/i = 1, i <= 15, i++)
					if(!M || !B || B.loc != M) break
					heat = RemasterNearFire(M)
					if(!heat) break
					B.brew_temp = min(heat, B.brew_temp + max(4, (heat - B.brew_temp) * 0.15))
					RemasterBrewReact(B, M)
					sleep(10)
				if(M) M.remaster_heating = 0
			return 1
		if("drink")
			var/obj/Items/Potions/RemasterBrew/B = RemasterBrewOf(M)
			if(!B || !length(B.brew)) return 0
			RemasterDrinkBrew(M, B)
			return 1
		if("throw")
			if(remaster_throw_unit == M)   // pressed again: put it away
				remaster_throw_unit = null
				remaster_throw_brew = null
				RemasterNotice("Throw cancelled.")
				return 1
			var/obj/Items/Potions/RemasterBrew/B = RemasterBrewOf(M)
			if(!B || !length(B.brew)) return 0
			remaster_throw_unit = M
			remaster_throw_brew = B
			RemasterNotice("Click where [M.name] should throw the [B.name] (up to [RM_THROW_RANGE] tiles).")
			return 1
		if("empty")
			var/obj/Items/Potions/RemasterBrew/B = RemasterBrewOf(M)
			if(!B) return 0
			B.brew = list()
			B.brew_temp = 20
			RemasterBrewLook(B)
			return 1
	return 0

// Drinking: each reagent does its thing, scaled by how much there is.
Player/proc/RemasterDrinkBrew(mob/Monsters/M, obj/Items/Potions/RemasterBrew/B)
	var/list/did = list()
	for(var/r in B.brew)
		var/u = B.brew[r]
		switch(r)
			if("healing")
				M.HP = min(M.MAXHP, M.HP + u * 4)
				did += "healed"
			if("sleepdraught")
				if(!M.Sleeping) M.Sleep(100 + round(u * 20))
				did += "fell asleep"
			if("poison", "venom")
				if(!M.Undead) M.HP -= u * (r == "poison" ? 3 : 1.5)
				did += "was poisoned"
			if("firewater")
				M.Fire()
				did += "caught fire"
			if("mana")
				if(M.MaxMana) M.Mana = min(M.MaxMana, M.Mana + u * 3)
				did += "felt mana surge"
			if("tonic")
				var/gain = round(min(10, u / 2))
				M.Strength += gain
				spawn(1800) if(M) M.Strength -= gain
				did += "felt stronger"
			if("smokepowder")
				M.HP -= 1
				did += "coughed"
			if("elixir")
				M.HP = M.MAXHP
				M.BloodContent = M.MaxBloodContent
				M.rm_poison = 0
				did += "was made whole"
			if("antidote")
				did += M.rm_poison > 0 ? (M.rm_poison > u * 3 ? "felt the poison ease" : "was cured of poison") : "tasted bitter char"
				M.rm_poison = max(0, M.rm_poison - u * 3)
				M.BloodContent = min(M.MaxBloodContent, M.BloodContent + u * 3)
			if("dragonfire")
				M.Fire()
				M.HP -= u
				did += "burned from within"
			if("stoneskin")
				var/gain = round(min(30, u))
				var/had = M.ArmourSkill
				M.ArmourSkill += gain
				M.RemasterHoldNow()   // held at Attack at once (CombatSkills.dm)
				// never below where it was: the gain may have been held at Attack
				spawn(1800) if(M) M.ArmourSkill = max(M.ArmourSkill - gain, min(M.ArmourSkill, had))
				did += "turned tough as stone"
			if("plague")
				if(!M.Undead) M.HP -= u * 2
				M.RemasterCatchFever("plague")   // Ailments.dm
				did += "fell sick"
			if("wine")
				if(M.RemasterDrinkWine(u)) did += "drank wine"
			if("archmana")
				if(M.MaxMana) M.Mana = M.MaxMana
				did += "brimmed with mana"
			if("dragonblood")
				M.HP = min(M.MAXHP, M.HP + u * 2)
				did += "drank dragon's blood, hot as embers"
			if("dragonheart")   // BeastParts.dm: fire can't take them, and they are stronger, for 10 minutes
				var/gain = round(min(15, u))
				M.Strength += gain
				spawn(6000) if(M) M.Strength -= gain
				M.rm_fireproof_until = world.time + 6000
				did += "felt a dragon's heart beat in them: fire can't take them for 10 minutes"
	B.brew = list()
	B.brew_temp = 20
	RemasterBrewLook(B)
	var/text = length(did) ? jointext(did, ", ") : "drank it; nothing happened"
	RemasterNotice("[M.name] [text].")
	M.RemasterEvent("Drank a brew: [text]")
	if(M.HP <= 0 && !M.GoingToDie)   // Death() does nothing unless it is going to die (Creatures/Death.dm); last, it may delete M
		M.GoingToDie = 1
		M.Killer = "a bad brew"
		M.DeathType = "a bad brew"
		M.Death()

// Throwing: the next click on a tile in range bursts the brew there.
Player/var/tmp
	mob/Monsters/remaster_throw_unit
	obj/Items/Potions/RemasterBrew/remaster_throw_brew

Player/proc/RemasterThrowClick(atom/A)
	if(!remaster_throw_unit) return 0
	var/mob/Monsters/M = remaster_throw_unit
	var/obj/Items/Potions/RemasterBrew/B = remaster_throw_brew
	remaster_throw_unit = null
	remaster_throw_brew = null
	var/turf/T = RemasterTurf(A, A)
	if(!M || !B || B.loc != M || !T) return 1
	if(T.z != M.z || get_dist(M, T) > RM_THROW_RANGE)
		RemasterNotice("Too far: [M.name] can throw [RM_THROW_RANGE] tiles.")
		return 1
	RemasterBurstBrew(B, T, M)
	return 1

proc/RemasterBurstBrew(obj/Items/Potions/RemasterBrew/B, turf/T, mob/Monsters/thrower)
	var/fire = 0
	for(var/r in B.brew)
		var/list/R = rm_reagents[r]
		if(!R[3]) continue
		RemasterGasAdd(T, R[3], B.brew[r] * R[4] * 3)
		if(r == "firewater" || r == "dragonfire") fire = 1
		if(r == "dragonfire") for(var/turf/N in orange(1, T)) RemasterGasAdd(N, "firedamp", B.brew[r])
	if(fire) RemasterHeat(T, 240)
	if(thrower && ismob(thrower.Owner)) thrower.Owner << "[thrower.name] throws the [B.name]; it bursts!"
	if(thrower) thrower.weight -= B.weight
	// the bottle shatters
	del(B)

// HUD data for one unit: its brew, what it can add, and what's in reach.
Player/proc/RemasterAlchemyData(mob/Monsters/M)
	var/obj/Items/Potions/RemasterBrew/B = RemasterBrewOf(M)
	var/bottles = length(RmEmptyBottles(M)) - (B && !length(B.brew) ? 1 : 0)   // the one shown isn't a spare
	var/list/ingredients = list()
	for(var/obj/Items/I in M)
		var/r = RemasterIngredient(I)
		if(!r || I.suffix == "(Equipped)") continue
		var/list/R = rm_reagents[r]
		ingredients += list(list("ref"=RemasterUIRef(I), "name"="[I.name]", "gives"=R[1]))
		if(length(ingredients) >= 12) break
	if(!B && !bottles && !length(ingredients)) return null
	var/list/contents = list()
	if(B) for(var/r in B.brew)
		var/list/R = rm_reagents[r]
		contents += list(list("name"=R[1], "units"=round(B.brew[r], 0.1), "color"=R[2]))
	return list("brew"=(B ? "[B.name]" : null), "temp"=(B ? round(B.brew_temp) : null), "contents"=contents,
		"bottles"=bottles, "ingredients"=ingredients, "water"=RemasterNearWater(M), "fire"=!!RemasterNearFire(M),
		"heating"=M.remaster_heating, "throwing"=(remaster_throw_unit == M))
