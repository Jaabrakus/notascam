// Bags that work together.
//  - Give: drag an item onto another unit; the carrier walks over and hands it
//    across. Potions and food given this way are used on arrival.
//  - Use: double-click an item to eat, drink or equip it straight away.
//  - Shared bag: friends within 3 tiles lend what's needed.
//  - Use it yourself: units drink Restoration when a limb is lost, Internal
//    Restoration when organs are badly hurt, a Vampirism Cure after a bite,
//    an Antidote when poisoned (FoodSupply.dm) (per-unit tick boxes).
// The potion effects are the original ones (RemasterDrinkPotion).

#define REMASTER_SHARE_RANGE 3

mob/Monsters/var
	list/remaster_autouse                    // rule -> 1/0; null means the defaults
mob/Monsters/var/tmp
	obj/Items/remaster_give_item
	list/remaster_give_extra                 // the rest of a stack given together
	mob/Monsters/remaster_give_to
	remaster_give_use = 0
	remaster_give_since = 0
	remaster_autouse_at = 0
Player/var/tmp/remaster_auto_use = 0         // drinking for a rule, not a manual action

proc/RemasterAutoUseRules()
	return list("restore"="Drink Restoration when a limb is lost", "stump"="Treat a bleeding stump (fire, a torch, a bandage or a poultice)", "stone"="Mend stone limbs with carried stone (gargoyles)", "organs"="Drink Internal Restoration when badly hurt inside", "cure"="Drink a Vampirism Cure after a bite", "antidote"="Drink an Antidote when poisoned", "remedy"="Use a carried Doctor's remedy when ill or hurt", "wine"="Have a drink of carried wine when unhappy")   // FoodSupply.dm, Doctor.dm, Ailments.dm

mob/Monsters/proc/RemasterAutoUseOn(rule)
	if(!remaster_autouse) return 1
	return isnull(remaster_autouse[rule]) ? 1 : remaster_autouse[rule]

// --- What a unit needs ---------------------------------------------------------
mob/Monsters/proc/RemasterLostLimb()
	if(initial(HasLeftArm) && !HasLeftArm) return 1
	if(initial(HasRightArm) && !HasRightArm) return 1
	if(initial(HasLeftLeg) && !HasLeftLeg) return 1
	if(initial(HasRightLeg) && !HasRightLeg) return 1
	return 0

mob/Monsters/proc/RemasterHurtInside()
	var/max = OrganMaxHP || 100
	for(var/v in list("HeartHP", "LiverHP", "StomachHP", "BrainHP", "GutsHP", "ThroatHP", "LeftLungHP", "RightLungHP"))
		if((v in vars) && vars[v] < max * 0.4) return 1
	return 0

// The potion this unit needs now (by name), or null.
mob/Monsters/proc/RemasterNeededPotion()
	if(HP <= 0 || GoingToDie || Race == "Spider" || HasStomach != 1 || Undead || Infects) return null
	if(InfectedBy && RemasterAutoUseOn("cure")) return "Vampirism Cure"
	if(RemasterLostLimb() && RemasterAutoUseOn("restore")) return "Potion of Restoration"
	if(RemasterHurtInside() && RemasterAutoUseOn("organs")) return "Potion of Internal Restoration"
	return null

// A carried item by name: own bag first, then friends within reach.
mob/Monsters/proc/RemasterFindSupply(name, range = REMASTER_SHARE_RANGE)
	for(var/obj/Items/I in src) if(I.name == name && I.suffix == "(Carrying)") return I
	var/Player/P = Owner
	if(!istype(P) || !isturf(loc)) return null
	for(var/mob/Monsters/F in range(range, src))
		if(F == src || F.Owner != P || F.HP <= 0) continue
		for(var/obj/Items/I in F) if(I.name == name && I.suffix == "(Carrying)") return I
	return null

// Move a carried item from one unit's bag to another's.
proc/RemasterHandOver(obj/Items/I, mob/Monsters/giver, mob/Monsters/taker)
	if(!I || !giver || !taker || I.loc != giver || I.suffix == "(Equipped)") return 0
	if(taker.weight + I.weight > taker.weightmax) return 0
	giver.weight -= I.weight
	I.loc = taker
	I.suffix = "(Carrying)"
	taker.weight += I.weight
	return 1

// Use an item the unit carries, with the original effects.
Player/proc/RemasterUseFor(mob/Monsters/M, obj/Items/I)
	if(!I || I.loc != M || M.Owner != src) return 0
	usr = src
	remaster_auto_use = 1
	var/ok = 0
	var/label = "[I.name]"
	if(istype(I, /obj/Items/Potions/RemasterBrew))
		ok = length(I:brew) > 0
		if(ok) RemasterDrinkBrew(M, I)
	else if(I.IsPotion == 1 && !I.IsEmpty)
		var/before = I.name
		RemasterDrinkPotion(M, I)
		ok = (I.name != before || I.loc != M)
	else if(istype(I, /obj/Items/RemasterSalt))     // salt the food this unit carries (Ailments.dm)
		ok = M.RemasterSaltFood(I) > 0
	else if(istype(I, /obj/Items/RemasterSoulStone))   // take a soul, or give it to a gargoyle (SoulStone.dm)
		ok = M.RemasterUseSoulStone(I)
	else if(istype(I, /obj/Items/RemasterRemedy))   // a Doctor's remedy (Doctor.dm)
		ok = M.RemasterApplyRemedy(I:remedy, M)
		if(ok)
			M.weight -= I.weight
			del I
	else if(istype(I, /obj/Items/Food))
		M.EatItem(I)
		ok = !I || I.loc != M
	else if(istype(I, /obj/Items/Equipment) && I:EquipmentType())
		// Equip or unequip right away (the original toggle, no menu).
		var/before = I.suffix
		M.ToggleEquipItem(ITEM=I, MANUAL=1)
		ok = I && I.suffix != before
	remaster_auto_use = 0
	if(ok) M.RemasterEvent("Used [label]")
	return ok

// --- Give -----------------------------------------------------------------------
Player/proc/RemasterGive(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 2) return 0
	// "ref" or a whole stack "ref,ref,ref"
	var/list/refs = splittext(p[1], ",")
	var/obj/Items/I = RemasterUIItem(refs[1])
	var/mob/Monsters/taker = RemasterUIUnit(p[2])
	if(!I || !istype(taker) || taker.Owner != src || !istype(I.loc, /mob/Monsters)) return 0
	var/mob/Monsters/giver = I.loc
	if(giver.Owner != src || I.suffix != "(Carrying)")
		RemasterNotice("Only carried items can be handed over (unequip it first).")
		return 0
	var/use = length(p) >= 3 ? p[3] == "1" : ((I.IsPotion == 1 && !I.IsEmpty) || istype(I, /obj/Items/Food))
	if(giver == taker)
		if(use) return RemasterUseFor(giver, I)
		return 0
	giver.remaster_give_item = I
	giver.remaster_give_extra = list()
	for(var/i = 2, i <= length(refs) && i <= 50, i++)
		var/obj/Items/X = RemasterUIItem(refs[i])
		if(X && X.loc == giver && X.suffix == "(Carrying)") giver.remaster_give_extra += X
	giver.remaster_give_to = taker
	giver.remaster_give_use = use
	giver.remaster_give_since = world.time
	giver.RemasterGiveTick()
	return 1

mob/Monsters/proc/RemasterGiveTick()
	var/obj/Items/I = remaster_give_item
	var/mob/Monsters/T = remaster_give_to
	var/Player/P = Owner
	if(!I || !T || I.loc != src || T.HP <= 0 || T.z != z || !istype(P) || world.time - remaster_give_since > 1200)
		remaster_give_item = null
		remaster_give_to = null
		return
	if(get_dist(src, T) > 1)
		if(destination != T.loc) destination = T.loc
		remaster_order_status = "Bringing [I.name] to [T.RemasterBareName()]"
		return
	if(destination == T.loc) destination = null
	var/use = remaster_give_use
	remaster_give_item = null
	remaster_give_to = null
	var/list/extra = remaster_give_extra
	remaster_give_extra = null
	if(!RemasterHandOver(I, src, T))
		remaster_order_status = "[T.RemasterBareName()] can't carry the [I.name]"
		P.RemasterNotice("[T.RemasterBareName()] can't carry the [I.name].")   // it was only on the unit's status line (polish 10-26)
		return
	var/n = 1
	if(extra) for(var/obj/Items/X in extra) if(X.loc == src && RemasterHandOver(X, src, T)) n++
	var/what = n > 1 ? "[n] × [I.name]" : "[I.name]"
	remaster_order_status = "Gave [what] to [T.RemasterBareName()]"
	RemasterEvent("Gave [what] to [T.RemasterBareName()]")
	if(use && !P.RemasterUseFor(T, I)) P.RemasterNotice("[T.RemasterBareName()] can't use the [I.name] now.")   // given, but not eaten, drunk or worn: say so

// --- Every 2 seconds: give-walks and use-it-yourself ----------------------------
Player/proc/RemasterBagTick(spread = 0)
	var/rm_n = 0   // units since the last safe point (Spread.dm)
	for(var/mob/Monsters/M in UnitList)
		RmBagUnit(M)
		if(spread && ++rm_n >= 16)   // a safe point every 16 units (Spread.dm compiles after this file)
			rm_n = 0
			RmTrackPause()

Player/proc/RemasterBagCommand(action, value)
	switch(action)
		if("giveitem") return RemasterGive(value)
		if("useitem")
			var/obj/Items/I = RemasterUIItem(value)
			if(!I || !istype(I.loc, /mob/Monsters)) return 0
			var/mob/Monsters/M = I.loc
			if(M.Owner != src) return 0
			if(!RemasterUseFor(M, I)) RemasterNotice("[M.name] can't use the [I.name] now.")
			return 1
		if("autouse")
			// unitref|rule|1/0
			var/list/p = splittext("[value]", "|")
			if(length(p) != 3 || !(p[2] in RemasterAutoUseRules())) return 0
			var/mob/Monsters/M = RemasterUIUnit(p[1])
			if(!istype(M) || M.Owner != src) return 0
			if(!M.remaster_autouse) M.remaster_autouse = list()
			M.remaster_autouse[p[2]] = p[3] == "1"
			return 1
	return 0

mob/Monsters/proc/RemasterAutoUseData()
	var/list/out = list()
	var/list/R = RemasterAutoUseRules()
	for(var/k in R) out += list(list("id"=k, "label"=R[k], "on"=RemasterAutoUseOn(k)))
	return out

// --- Take from the stores ------------------------------------------------------
// Selected units walk to the nearest store holding that kind and fill up.
mob/Monsters/var/tmp/remaster_take
mob/Monsters/var/tmp/remaster_take_since = 0

proc/RemasterTakeKinds()
	return list("food"=/obj/Items/Food, "wood"=/obj/Items/woods/wood, "stone"=/obj/Items/ores/stone, "potions"=/obj/Items/Potions)

Player/proc/RemasterTakeCommand(kind)
	if(!(kind in RemasterTakeKinds())) return 0
	var/n = 0
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && (M in UnitList) && !M.Wagon && M.HP > 0)
		M.remaster_take = kind
		M.remaster_take_since = world.time
		n++
	RemasterNotice(n ? "Fetching [kind] from the stores." : "Select units first.")
	return n

mob/Monsters/proc/RemasterTakeTick(Player/P)
	var/type = RemasterTakeKinds()[remaster_take]
	if(!type || world.time - remaster_take_since > 1200)
		remaster_take = null
		return
	var/turf/S = P.RemasterStoreWith(type, src)
	if(!S)
		remaster_order_status = "No [remaster_take] in any store on this level"
		remaster_take = null
		return
	if(get_dist(src, S) > 1)
		if(destination != S) destination = S
		remaster_order_status = "Fetching [remaster_take] from the stores"
		return
	if(destination == S) destination = null
	var/n = 0
	var/full = 0
	var/obj/Items/far   // a store's goods lie up to a tile around it: one out of reach from where the unit stopped
	for(var/obj/Items/I in range(1, S))
		if(n >= 10) break
		if(!isturf(I.loc) || !istype(I, type) || !P.RemasterMayCollect(I)) continue
		if(type == /obj/Items/Potions && I.IsEmpty) continue
		if(weight + I.weight > weightmax)
			full = 1
			break
		if(get_dist(src, I) > 1)
			if(!far) far = I
			continue
		if(PickUpItem(I)) n++
	if(!n && !full && far)
		// nothing within reach (it said "Can't carry more" with an empty bag, polish 10-26): over to it, taken next time
		destination = far.loc
		remaster_order_status = "Fetching [remaster_take] from the stores"
		return
	remaster_order_status = n ? "Took [n] [remaster_take] from the stores" : "Can't carry more [remaster_take]"
	remaster_take = null

// One line for an item's tooltip: what it does, from its own numbers.
proc/RemasterItemInfo(obj/Items/I, mob/Monsters/M)
	var/list/out = list()
	if(I.WeaponDamageMax) out += "Damage [I.WeaponDamageMin]-[I.WeaponDamageMax]"
	if(I.Defence) out += "Armour [I.Defence]"   // owner 10-27: armour, not the Defence skill
	if(I.ItemType in list("Axe", "Pickaxe"))
		var/list/T = RemasterToolTier(I)
		if(T)
			var/skill = I.ItemType == "Axe" ? M.WoodCuttingSkill : M.MineingSkill
			out += "[T[2]] tool: ×[T[4]] speed from [I.ItemType == "Axe" ? "Woodcutting" : "Mining"] [T[3]][round(skill) >= T[3] ? "" : " (you have [round(skill)])"]"
	if(istype(I, /obj/Items/Food) && I.FoodPower) out += "Food +[I.FoodPower]"
	if(I.IsPotion == 1) out += I.IsEmpty ? "Empty bottle" : "[I.desc]"
	if(I.weight) out += "Weight [I.weight]"
	if(I.CraftRank) out += "[I.CraftRank]"
	return jointext(out, " · ")

// --- Equip best armour -----------------------------------------------------------
// For each armour slot, wear the carried piece with the most defence: as it protects this unit, below the piece's level
// scaled (GearAny.dm; by its raw Defence a level-1 unit put on iron plate worth 6 to it over leather worth 7, polish 10-26).
proc/RmArmourWorth(obj/Items/I, mob/M)
	return I.Defence * RmGearEff(I, M)

Player/proc/RemasterEquipBest(mob/Monsters/M)
	var/changed = 0
	usr = src
	remaster_auto_use = 1
	for(var/slot in list("Helmet", "Chestplate", "LeftArm", "RightArm", "Leggings", "Shield", "Neckguard", "Cape"))
		var/obj/Items/best
		var/obj/Items/worn
		for(var/obj/Items/I in M)
			if(I.ItemType != slot || I.icon == 'DemonicItems.dmi') continue
			if(I.suffix == "(Equipped)") worn = I
			if(!best || RmArmourWorth(I, M) > RmArmourWorth(best, M)) best = I
		if(!best || best == worn || (worn && RmArmourWorth(worn, M) >= RmArmourWorth(best, M))) continue
		if(worn) M.ToggleEquipItem(ITEM=worn, MANUAL=1)
		M.ToggleEquipItem(ITEM=best, MANUAL=1)
		if(best.suffix == "(Equipped)") changed++
	remaster_auto_use = 0
	return changed

Player/proc/RemasterEquipBestCommand()
	var/total = 0
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && (M in UnitList) && M.HP > 0) total += RemasterEquipBest(M)
	RemasterNotice(total ? "Put on [total] better piece[total == 1 ? "" : "s"] of armour." : "Already wearing the best armour they carry.")
	return total

// One unit of the bag pass (RemasterBagTick), as the pass did it in one go (server cost, 2026-10-24).
Player/proc/RmBagUnit(mob/Monsters/M)
	if(M.Owner != src || M.HP <= 0) return
	M.RemasterAutoName()
	if(!isturf(M.loc)) return
	if(M.remaster_give_item)
		M.RemasterGiveTick()
		return
	if(M.remaster_take)
		M.RemasterTakeTick(src)
		return
	if(world.time < M.remaster_autouse_at) return
	M.remaster_autouse_at = world.time + 20
	var/need = M.RemasterNeededPotion()
	if(need)
		var/obj/Items/S = M.RemasterFindSupply(need)
		if(S)
			var/mob/Monsters/holder = S.loc
			if(holder != M && !RemasterHandOver(S, holder, M)) return
			if(RemasterUseFor(M, S)) RemasterLog("[M.name] drank [need][holder != M ? " from [holder.name]'s bag" : ""]", "good", M)
			return
