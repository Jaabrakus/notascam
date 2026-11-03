// The resource sack (Leatherworks, 2 skins). Worn on the back where a quiver goes (it is one to the
// equip code, ItemType "Quiver", so a unit wears a sack or a quiver), it holds RM_SACK_PIECES of a
// worker's resources (wood, stone, ore, gems, food... RemasterResourceKind) at half their weight.
// The resources stay in the unit's pack as before, so every job, order and delivery works unchanged:
// wearing it lifts the unit's carry limit by RM_SACK_BONUS, and things that aren't resources may only
// use the room the sack frees, not the sack itself. A worker empties it where it unloads anyway: the
// stockpile, or a cart loading stop when that is nearer (Delivery.dm, Carts.dm).
// Picture: art/sack/make_sack_icon.py (drawn over the leather quiver's frames).

#define RM_SACK_PIECES 10
#define RM_SACK_BONUS 100          // 10 resources of 20 at half weight

obj/Items/Equipment/Armour/Quiver/RemasterSack
	// its values: art/items/catalogue.json row equipment.armour.quiver.remastersack (export_items.py writes ItemData.dm)

mob/var/remaster_sack_bonus = 0     // saved: carry limit the worn sack adds

proc/RemasterIsSack(obj/Items/I)
	return istype(I, /obj/Items/Equipment/Armour/Quiver/RemasterSack)

mob/proc/RemasterWornSack()
	for(var/obj/Items/Equipment/Armour/Quiver/RemasterSack/S in src) if(S.suffix == "(Equipped)") return S
	return null

// The weight the sack takes off: half of up to RM_SACK_PIECES carried resources, at most its bonus.
mob/proc/RemasterSackRelief(obj/Items/extra)
	if(!remaster_sack_bonus) return 0
	var/list/w = list()
	for(var/obj/Items/I in src) if(I.suffix == "(Carrying)" && RemasterResourceKind(I)) w += I.weight
	if(extra && RemasterResourceKind(extra)) w += extra.weight
	. = 0
	var/n = 0
	for(var/x in w)
		if(++n > RM_SACK_PIECES) break
		. += x / 2
	. = min(., remaster_sack_bonus)

mob/proc/RemasterSackPieces()
	. = 0
	for(var/obj/Items/I in src) if(I.suffix == "(Carrying)" && RemasterResourceKind(I)) .++
	. = min(., RM_SACK_PIECES)

// What Inspect says of a sack. The bag menu treats it as a quiver, which offered "Drop Arrows" and said "Has 0 arrows."
proc/RemasterSackInspect(obj/Items/S, mob/M)
	if(S.suffix == "(Equipped)" && M) return "Holds [M.RemasterSackPieces()] of [RM_SACK_PIECES] pieces of wood, stone, ore or food at half their weight."
	return "Worn, it holds [RM_SACK_PIECES] pieces of wood, stone, ore or food at half their weight."

mob/ForceEquipItem(obj/Items/ITEM)
	. = ..()
	if(. && RemasterIsSack(ITEM) && !remaster_sack_bonus)
		remaster_sack_bonus = RM_SACK_BONUS
		RemasterSackRoom(RM_SACK_BONUS)
		RemasterSackName(ITEM)

mob/ForceUnEquipItem(obj/Items/ITEM)
	. = ..()
	if(RemasterIsSack(ITEM) && remaster_sack_bonus)
		RemasterSackRoom(-remaster_sack_bonus)
		remaster_sack_bonus = 0
		ITEM.name = initial(ITEM.name)
		// what the sack held and the pack can't: put down here
		if(weight > weightmax && !Flying && istype(src, /mob/Monsters)) src:RemasterMakeRoom(0)

// Flying and mist hold the carry limit aside in Old (Race.dm Fly, Vampires.dm VampireMistForm) and put it back after,
// so the sack's room goes into the limit held aside too: else each mist (which takes the sack off and on) added 100 to a
// vampire's limit for good, and a sack taken off in flight left its 100 behind (polish 10-26). In flight the limit
// itself is the "can't carry" mark and stays.
mob/proc/RemasterSackRoom(n)
	if(isnum(Old)) Old += n
	if(!Flying) weightmax += n

// Things that aren't resources may use only the room the sack frees, not the sack itself.
mob/PickUpItem(atom/movable/ITEM, Telling = 0, Range = 1)
	if(remaster_sack_bonus && istype(ITEM, /obj/Items) && !RemasterResourceKind(ITEM))
		if(ITEM.weight + weight - RemasterSackRelief() > weightmax - remaster_sack_bonus)
			if(Telling) usr << "[src]: I Can't Carry Too Much! (The sack only takes wood, stone, ore and food.)"
			return 0
	return ..()

// Its name says how full it is.
mob/proc/RemasterSackName(obj/Items/S)
	if(!S) S = RemasterWornSack()
	if(S) S.name = "Resource Sack ([RemasterSackPieces()]/[RM_SACK_PIECES])"

Player/RemasterBagTick()
	..()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src)
		if(M.remaster_sack_bonus) M.RemasterSackName()
		if(M.remaster_gathered) RemasterYieldLogFlush(M)     // what it gathered, into the village log (Yield.dm)

// The Leatherworks recipe (its menu in Items/CraftingStations.dm).
mob/Monsters/proc/RemasterCraftSack(mob/WorkShops/W, Player/P)
	if(!(src in range(1, W)) || !RemasterManualHandoff(P)) return
	var/list/skins = list()
	for(var/obj/Items/Skin/S in src) if(S.suffix != "(Equipped)" && length(skins) < 2) skins += S
	if(length(skins) < 2)
		P << "[src] needs 2 pieces of skin to make a resource sack."
		return
	for(var/obj/Items/Skin/S in skins)
		weight -= S.weight
		del S
	if(!prob(RemasterCraftOdds(LeatherCraftingSkill, 4)))
		P << "The attempt failed and the skins are used up. Leather crafting rises with every try."
		LeatherCraftingSkill += 1
		return
	var/obj/Items/Equipment/Armour/Quiver/RemasterSack/B = new(loc)
	B.dir = NORTH
	LeatherCraftingSkill += 0.5
	P << "[src] makes a resource sack: worn on the back, it carries 10 resources at half weight."
