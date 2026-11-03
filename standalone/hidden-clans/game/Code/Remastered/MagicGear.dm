// What the magic gear does (Remastered). The staffs and enchanted weapons hold their own mana; what they
// do is their moves (WeaponSkills.dm: their defaults, and branch moves and spells unlocked by the wielder's
// skills), paid from that mana. Here: the defaults that are not a blow -
//   Crystal Staff  - its own mana refills fast and tops up the other magic weapons carried; it lights the way
//   Orb Staff      - its bearer's race special now and then strikes twice (10 mana)
//   Flame Staff    - its bearer's fire always catches (3 mana a foe)
//   Nature Staff   - its bearer's people close by heal faster, crops near it ripen faster (1 mana a time)
//   Skull Staff    - Raise Skeleton (the move "raiseskeleton", 15 mana)
// and how the mana comes back (RmManaTick): slowly by itself, from a rune stone carried in the bag, and on a
// rune circuit (standing beside one of its pieces, from its crystals). A unit's own mana is its race's only.

var/rm_orb_echo = 30     // chance in 100 that the Orb Staff's special strikes again

// Mana a second: an item by itself; the Crystal Staff's own, and what it gives each other magic item
// carried; a rune stone to what it charges; a circuit to each item and stone beside it; a stone by itself.
var/rm_mana_self = 0.05
var/rm_mana_crystal = 1
var/rm_mana_crystal_share = 0.5
var/rm_mana_stone = 1
var/rm_mana_circuit = 3
var/rm_stone_self = 0.15
#define RM_STONE_MAX 100

mob/Monsters/var/tmp/rm_echoing = 0

proc/RmHolding(mob/M, id)
	var/obj/Items/Equipment/W = RmHeldWeapon(M)
	return W && W.rm_gear == id

// The Orb Staff: the special strikes again at once, now and then.
mob/Monsters/RemasterCastSpecial(turf/T)
	. = ..()
	if(. && !rm_echoing && RmHolding(src, "magic.orb staff") && prob(rm_orb_echo) && RmManaSpend(RmHeldWeapon(src), 10))
		rm_echoing = 1
		spawn(4)
			if(src && T && HP > 0)
				remaster_special_at = 0
				RemasterCastSpecial(T)
				RemasterHit(src, 0, "echo", src)
			if(src) rm_echoing = 0

// The Flame Staff: its bearer's fire never fails to catch, while it has the mana.
mob/Monsters/RemasterBreathBurn(list/area, el, dmg, id, heat = 1)
	. = ..()
	if(el == "fire" && RmHolding(src, "magic.flame staff"))
		var/obj/Items/Equipment/W = RmHeldWeapon(src)
		for(var/mob/Monsters/M in RemasterSpecialFoes(area)) if(M.HP > 0 && !M.OnFire && !RmFireproof(M) && RmManaSpend(W, 3)) M.Fire()

// A skull in sight rises as a skeleton of yours (the Skull Staff's move; its mana is paid by the move).
proc/RmRaiseSkeleton(mob/Monsters/M, mob/owner)
	for(var/obj/Items/Bones/Skull/B in oview(M))
		var/mob/Monsters/Skeleton/Z = new(B.loc)
		view(M) << "[M] fires a bolt of death energy into [B], raising an evil creature from the bones!"
		Z.ChangeOwnership(owner)
		Z.name = "[M.name]'s Skeleton"
		M.NecromancySkill += 0.25
		M.MagicSkill += 0.25
		Z.PillarPowerup()
		Z.GainEXP(M.NecromancySkill * 4)
		del(B)
		return Z
	if(ismob(owner)) owner << "[M] sees no skull to raise."
	return 0

// --- Rune stones ------------------------------------------------------------------------------
// Cut from a gem at the Gem cutter. Carried, it tops up the magic weapons in the bag until it runs dry; it
// fills again slowly by itself, fast beside a rune circuit.
obj/Items/RmRuneStone
	// its values: art/items/catalogue.json row rmrunestone (export_items.py writes ItemData.dm)
	var/charge = RM_STONE_MAX

// --- Mana coming back, every half second; the Nature Staff every 2 s -----------------------------
proc/RmMagicGearLoop()
	var/n = 0
	while(1)
		sleep(5)
		n++
		for(var/Player/P in Players) for(var/mob/Monsters/M in P.UnitList) if(M.HP > 0 && isturf(M.loc))
			RmManaTick(M, 0.5)
			if(n % 4 == 0 && RmHolding(M, "magic.nature staff")) RmNatureTick(M)

// A unit whose pack held no magic gear and no rune stone isn't looked through again until its state counter moves
// (rm_ver_state: anything going into or out of it, or written on what it carries); 4,000 looks a second with 2,000 units
// were nearly all for nothing (the owner, 10-31: "does things multiple itmes"). Its mana items' kinds are fixed
// (rm_item_mana, by rm_gear).
mob/Monsters/var/tmp/rm_mana_none = -1   // that counter when it was last found carrying none (a quiet name, Native.dm)

proc/RmManaTick(mob/Monsters/M, secs)
	var/v = rm_ver_state(M)
	if(M.rm_mana_none == v)
		if(rm_once_verify) RmOnceCheck("mana", RmManaCarries(M), M)
		return
	var/list/items = list()
	var/list/stones = list()
	for(var/obj/Items/I in M)
		if(istype(I, /obj/Items/RmRuneStone)) stones += I
		else if(RmManaMax(I)) items += I
	if(!length(items) && !length(stones))
		M.rm_mana_none = v
		return
	var/datum/rm_runenet/N
	for(var/obj/RemasterRune/R in range(1, M)) if(R.net && RemasterRuneNetMana(R.net) > 0)
		N = R.net
		break
	for(var/obj/Items/I in items)
		RmManaAdd(I, rm_mana_self * secs)
		if(N)
			var/want = min(rm_mana_circuit * secs, RmManaMax(I) - RmManaOf(I), RemasterRuneNetMana(N))
			if(want > 0 && RemasterRuneSpend(N, want)) RmManaAdd(I, want)
	var/obj/Items/Equipment/W = RmHeldWeapon(M)
	if(W && W.rm_gear == "magic.crystal staff")
		RmManaAdd(W, rm_mana_crystal * secs)
		for(var/obj/Items/I in items) if(I != W && RmManaOf(W) > 0)
			var/give = min(rm_mana_crystal_share * secs, RmManaOf(W), RmManaMax(I) - RmManaOf(I))
			if(give > 0)
				W.rm_mana -= give
				RmManaAdd(I, give)
	for(var/obj/Items/RmRuneStone/S in stones)
		S.charge = min(RM_STONE_MAX, S.charge + rm_stone_self * secs)
		if(N)
			var/want = min(rm_mana_circuit * secs, RM_STONE_MAX - S.charge, RemasterRuneNetMana(N))
			if(want > 0 && RemasterRuneSpend(N, want)) S.charge += want
		var/obj/Items/low
		for(var/obj/Items/I in items) if(RmManaOf(I) < RmManaMax(I) && (!low || RmManaOf(I) / RmManaMax(I) < RmManaOf(low) / RmManaMax(low))) low = I
		if(low && S.charge > 0)
			var/give = min(rm_mana_stone * secs, S.charge, RmManaMax(low) - RmManaOf(low))
			S.charge -= give
			RmManaAdd(low, give)

// RM_ONCE_VERIFY: a pack the mana tick skipped, looked through anyway
proc/RmManaCarries(mob/Monsters/M)
	for(var/obj/Items/I in M) if(istype(I, /obj/Items/RmRuneStone) || RmManaMax(I)) return 1
	return 0

proc/RmNatureTick(mob/Monsters/M)
	var/obj/Items/Equipment/W = RmHeldWeapon(M)
	if(RmManaOf(W) < 1) return
	var/healed = 0
	for(var/mob/Monsters/O in range(3, M)) if(O.Owner == M.Owner && O.HP > 0 && !O.GoingToDie)
		if(O.HP < O.MAXHP)
			O.HP = min(O.MAXHP, O.HP + 2)
			healed = 1
		if(O.BloodContent < O.MaxBloodContent)
			O.BloodContent = min(O.MaxBloodContent, O.BloodContent + 2)
			healed = 1
	for(var/obj/Items/Plants/C in range(3, M)) if(prob(25))
		C.PlantRegen(1)   // one step: a plain PlantRegen() starts one more endless regrow loop on the plant each time
		healed = 1
	if(healed) RmManaSpend(W, 1)

// world/New: this file's part is step RmChainWorldNew_MagicGear in Code/Remastered/Chains/WorldNew.dm

// The Crystal Staff lights the way in 3D (View3D.dm "glow": radius, colour).
proc/RmGlow(mob/Monsters/M)
	if(RmHolding(M, "magic.crystal staff")) return list(5, 0.55, 0.85, 1.0)
	return null
