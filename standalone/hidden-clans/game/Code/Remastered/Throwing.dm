// Throwing weapons and visible shots. Units carrying javelins, throwing axes or
// stone throw them at an enemy a few tiles off before closing in (attack orders and
// defenders do this on their own):
//   Javelin       range 6  - heavy, pierces armour, uses spear skill
//   Throwing axe  range 4  - spins, can cut a limb off, uses axe skill
//   Rock (stone)  range 5  - any carried stone; light damage but can stagger
// Thrown things land where they hit and can be picked up again. Every bow shot and
// throw is sent to the 3D view as a projectile that arcs from the thrower to the
// target, and its damage number pops up when it lands.

obj/Items/Thrown
	var/remaster_throw = "javelin"
	Javelin
		// its values: art/items/catalogue.json row thrown.javelin (export_items.py writes ItemData.dm)
	ThrowingAxe
		// its values: art/items/catalogue.json row thrown.throwingaxe (export_items.py writes ItemData.dm)

mob/Monsters/var/tmp/remaster_throw_at = 0

// kind -> list(range, min dmg, max dmg, skill var, armour divisor, name)
var/list/rm_throw_kinds = list(
	"javelin"=list(6, 12, 22, "SpearSkill", 3, "javelin"),
	"axe"=list(4, 10, 18, "AxeSkill", 2, "throwing axe"),
	"rock"=list(5, 3, 8, null, 1, "rock"),
	"boulder"=list(10, 10, 22, null, 1, "boulder"),     // catapult splash (Siege.dm)
	"bolt"=list(12, 40, 70, null, 1, "ballista bolt"))   // ballista (Siege.dm)

proc/RemasterThrownKind(obj/Items/I)
	if(istype(I, /obj/Items/Thrown))
		var/obj/Items/Thrown/T = I
		return T.remaster_throw
	if(istype(I, /obj/Items/ores/stone)) return "rock"
	return null

// The best thing this unit can throw at a foe d tiles away (javelin, then axe, then rock).
mob/Monsters/proc/RemasterThrowable(d)
	var/list/best
	for(var/obj/Items/I in src)
		if(I.suffix == "(Equipped)") continue
		var/k = RemasterThrownKind(I)
		if(!k || d > rm_throw_kinds[k][1]) continue
		var/rank = list("javelin"=3, "axe"=2, "rock"=1)[k]
		if(!best || rank > best[2]) best = list(I, rank)
	return best ? best[1] : null

mob/Monsters/proc/RemasterThrowSummary()
	var/list/n = list()
	for(var/obj/Items/I in src) if(I.suffix != "(Equipped)")
		var/k = RemasterThrownKind(I)
		if(k) n[k] = (n[k] || 0) + 1
	if(!length(n)) return ""
	var/list/out = list()
	for(var/k in list("javelin", "axe", "rock")) if(n[k])
		out += "[n[k]] [list("javelin"="javelin", "axe"="throwing axe", "rock"="rock")[k]][n[k] > 1 ? "s" : ""]"
	return " · throws [jointext(out, ", ")]"

// Throw at E if something fits the range and the arm is free. Returns 1 when thrown.
mob/Monsters/proc/RemasterTryThrow(mob/Monsters/E)
	if(!E || world.time < remaster_throw_at || !HasRightArm || Sleeping || Stunned || Fainted) return 0
	if(HoldingWeapon == "Bow") return 0
	var/d = get_dist(src, E)
	if(d < 2 || E.z != z) return 0
	var/obj/Items/I = RemasterThrowable(d)   // first: it only reads its pack, and most carry nothing to throw (combat-speed, 10-26)
	if(!I || !(E in oview(6, src))) return 0
	remaster_throw_at = world.time + 25
	destination = null
	RemasterThrowAt(E, I)
	return 1

mob/Monsters/proc/RemasterThrowAt(mob/Monsters/M, obj/Items/I)
	var/k = RemasterThrownKind(I)
	var/list/K = rm_throw_kinds[k]
	var/skill = K[4] && (K[4] in vars) ? vars[K[4]] : 0
	var/str = ("Strength" in vars) ? vars["Strength"] : 0
	var/tx = M.x
	var/ty = M.y
	var/tz = M.z
	var/before = RemasterBodyHealth(M)
	var/alive = M.HP > 0 && !M.GoingToDie
	weight -= I.weight
	I.loc = M.loc
	I.suffix = null
	if(alive) M.RemasterThreatenedBy(src)
	if(K[4] && (K[4] in vars)) vars[K[4]] = min(200, skill + 0.2)
	GainEXP(3)
	var/kind = "miss"
	if(prob(RemasterThrowHitChance(src, M, skill)))   // Ranged against Defence (CombatSkills.dm)
		if(M.WearingShield && prob(M.ShieldSkill / 2))
			kind = "block"
			view(M) << "[M] blocks [src]'s [K[6]] with their shield!"
		else
			var/dmg = rand(K[2], K[3]) + skill / 6 + str / 10 + RemasterRangedBonus(src, M)   // armour comes off where it lands (RemasterThrownWound)
			dmg = max(2, round(dmg))
			kind = RemasterThrownWound(M, dmg, k, 1 / K[5])
	else view(src) << "[src] throws a [K[6]] at [M] but misses!"
	if(M && M.loc)
		var/d = round(before - RemasterBodyHealth(M))
		if(alive && (M.HP <= 0 || M.GoingToDie)) kind = "kill"
		RemasterCombatXP("throw", d)
		RemasterHitAt(tx, ty, tz, max(0, d), kind == "hit" && d <= 0 ? "miss" : kind, src, M.Owner, k)
	else RemasterHitAt(tx, ty, tz, before, "kill", src, null, k)

// Where a thrown weapon lands and what it does. Returns the hit kind.
// armour: the share of the armour that counts against this throw (a javelin a third, an axe half, a rock all);
// 0 for siege shots, which ignore armour (Siege.dm).
mob/Monsters/proc/RemasterThrownWound(mob/Monsters/M, dmg, k, armour = 0)
	if(!M.HumanParts)
		if(armour) dmg = max(2, round(dmg * RemasterArmourShare(M, armour)))
		M.HP -= dmg
		view(M) << "[M] is hit by [src]'s [rm_throw_kinds[k][6]]!"
		if(M.HP <= 0 && !M.GoingToDie)
			M.GoingToDie = 1
			M.Killer = "[src]"
			M.DeathType = "a thrown [rm_throw_kinds[k][6]]"
			M.Death()
		return "hit"
	var/part = pick("LeftLeg", "RightLeg", "LeftArm", "RightArm", "Chest", "Chest")
	var/aim = RmThrowPart(M, dmg)   // a great beast's part (Beasts.dm): its wings and head are struck there
	if(aim == "Wings" || aim == "Head") return M ? "hit" : "kill"
	if(aim) part = aim
	rm_shot_part = part   // the 3D view lands it there (Hits.dm)
	if(armour) dmg = max(2, round(dmg * RemasterPartShare(M, part == "Chest" ? "UpperBody" : part, armour)))   // the armour covering where it lands (CombatSkills.dm)
	var/where = list("LeftLeg"="left leg", "RightLeg"="right leg", "LeftArm"="left arm", "RightArm"="right arm", "Chest"="chest")[part]
	view(M) << "[M] is hit in the [where] by [src]'s [rm_throw_kinds[k][6]]!"
	M.BloodContent -= k == "rock" ? round(dmg / 3) : dmg
	if(k != "rock") M.BloodLoss()
	if(part != "Chest")
		var/hpv = "[part]HP"
		RmBeastLimbFloor(M, hpv, dmg)   // a great beast is crippled, never torn apart (Beasts.dm)
		M.vars[hpv] = M.vars[hpv] - dmg
		if(M.vars[hpv] <= 0 && M.vars["Has[part]"])
			M.vars["Has[part]"] = 0
			M.vars[part] = "Destroyed"
			M.BloodContent -= 90
			M.BloodLoss()
			M.LimbLoss()
			if(!M) return "kill"
			var/nice = list("LeftLeg"="Left Leg", "RightLeg"="Right Leg", "LeftArm"="Left Arm", "RightArm"="Right Arm")[part]
			view(M) << "<b><font color=red>[M]'s [lowertext(nice)] is torn off by the [rm_throw_kinds[k][6]]!</font></b>"
			M.LimbFling(nice)
			if(part == "LeftLeg" || part == "RightLeg") M.CanWalk = 0
			if(part == "RightArm") for(var/obj/Items/Equipment/Weapon/S in M) if(M.UnEquipItem(S)) M.DropItem(S)
	else M.HP -= round(dmg / 2)
	if(M && k == "rock" && prob(18) && !M.Stunned)
		M.Stunned = 1
		spawn(15) if(M) M.Stunned = 0
		return "stagger"
	if(M && M.HP <= 0 && !M.GoingToDie)
		M.GoingToDie = 1
		M.Killer = "[src]"
		M.RmFallBy(src)   // it falls dying, as from a blow (Falls.dm)
		M.DeathType = "a thrown [rm_throw_kinds[k][6]]"
		M.Death()
	return "hit"

// Bow shots: measure what each arrow really did and send it to the 3D view.
proc/RemasterQuiverCount(mob/M)
	. = 0
	for(var/obj/Items/Equipment/Armour/Quiver/LeatherQuiver/L in M) if(L.suffix == "(Equipped)") . += L.Content

mob/BowTarget(remaster_defensive_shot = 0, datum/remaster_bow_controller/controller = null)
	var/mob/T = Target
	var/list/was
	if(istype(T) && HoldingWeapon == "Bow") was = list(RemasterBodyHealth(T), T.x, T.y, T.z, T.HP > 0 && !T.GoingToDie, RemasterQuiverCount(src), T.Owner)
	..()
	if(!was || !src || RemasterQuiverCount(src) >= was[6]) return
	if(T && T.loc)
		var/d = round(was[1] - RemasterBodyHealth(T))
		var/kind = d > 0 ? "hit" : "miss"
		if(was[5] && (T.HP <= 0 || T.GoingToDie)) kind = "kill"
		RemasterHitAt(T.x, T.y, T.z, max(0, d), kind, src, T.Owner, "arrow")
	else RemasterHitAt(was[2], was[3], was[4], was[1], "kill", src, was[7], "arrow")

// Crafting (Carpentry: Javelins, Forge: Throwing Axes), called from the station menus.
mob/Monsters/proc/RemasterCraftThrown(mob/WorkShops/W, Player/P, k)
	if(!(src in range(1, W)) || !RemasterManualHandoff(P)) return
	var/obj/Items/S
	if(k == "javelin") for(var/obj/Items/woods/wood/X in src) S = X
	else for(var/obj/Items/Ingots/IronIngot/X in src) S = X
	if(!S)
		P << "[src] needs [k == "javelin" ? "wood" : "an iron ingot"] to make [k == "javelin" ? "javelins" : "throwing axes"]."
		return
	weight -= S.weight
	del(S)
	var/skill = k == "javelin" ? WoodCraftingSkill : MetalCraftingSkill
	if(!prob(RemasterCraftOdds(skill)))
		P << "Failed!"
		if(k == "javelin") WoodCraftingSkill += 1
		else MetalCraftingSkill += 1
		return
	var/path = k == "javelin" ? /obj/Items/Thrown/Javelin : /obj/Items/Thrown/ThrowingAxe
	for(var/i = 1, i <= 3, i++) new path(loc)
	if(k == "javelin") WoodCraftingSkill += 1
	else MetalCraftingSkill += 1
	P << "[src] makes 3 [k == "javelin" ? "javelins" : "throwing axes"]."
