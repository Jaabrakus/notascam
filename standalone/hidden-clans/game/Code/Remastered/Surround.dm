// Surround bonus and high ground (the user, 2026-10-26: "start with the surround bonus (with veterans resisting swarms)
// plus high ground"; planning/COMBAT_STRATEGY_PLAN_2026-10-26.md section 2c). Surround: every foe beside a unit (its 8
// tiles) beyond the first gives each melee blow on it +rm_surround_land (5) to land (CombatSkills.dm RmMeleeWhere), weapon
// moves too (the user, 2026-10-26: "moves get it too"). Only foes actually beside it count: not its own or an ally's,
// standing and able to fight (not knocked out, fainted, stunned, asleep, rooted or a tied captive), and up on the rock
// only those that can strike it, as a blow is a step at it (Orders.dm Move): at its height, a block above it, or below
// it on a ramp. So rock, trees, water and doors limit them, and a held pass cancels it. Veterans resist
// swarms: Defence rm_surround_vet1 (50) shrugs off one extra foe, rm_surround_vet2 (80) two. Great beasts and golems
// have none, as they have no flanks (Facing.dm). High ground: a unit standing a block or more above its foe gets
// +rm_high_land (5) to land in melee, and its arrows reach rm_high_reach (1) tile further at that foe (BeastParts.dm
// RmBowRange: Combat - Bows.dm, Attack.dm, Defense.dm), its bow's moves as well (WeaponSkills.dm, Formations.dm
// RemasterCastFirst). Only up on the rock do heights meet: a unit up there and one on
// the ground below never fight (Attack.dm RemasterHostile: one layer). Flyers stand on no block: no high ground either
// way. rm_surround_on 0 / rm_high_ground_on 0: the rolls of build 56.
var/rm_surround_on = 1
var/rm_surround_land = 5
var/rm_surround_vet1 = 50
var/rm_surround_vet2 = 80
var/rm_high_ground_on = 1
var/rm_high_land = 5
var/rm_high_reach = 1
mob/var/tmp/rm_surround_blows = 0   // blows it struck with a surround bonus (reports)
mob/var/tmp/rm_high_blows = 0       // ...from higher ground (reports)

// The foes beside D that could strike it.
proc/RmFoesBeside(mob/Monsters/D)
	. = 0
	if(!istype(D) || !isturf(D.loc)) return
	var/list/pairs = list()   // each realm's war and alliance once in this look (Attack.dm RemasterHostile; combat-speed, 10-26)
	for(var/mob/Monsters/O in orange(1, D))
		if(O.Owner == D.Owner || O.HP <= 0 || O.GoingToDie || O.Sleeping || O.RemasterSubdued() || RemasterIsSiege(O)) continue
		if(O.rm_cap_state && O.rm_cap_strike_until <= world.time) continue   // a captive, not rising (Captives.dm)
		if(O.Critter && O.Target != D) continue                              // a wild critter only while it goes for it
		if(!RemasterHostile(D, O, 1, pairs)) continue
		if(D.z == SKY_LAYER && !O.RemasterStepSpot(D.loc)) continue           // up on the rock: no step at it, no blow (Gather.dm)
		.++

// A melee blow's land bonus on D for the foes round it.
proc/RmSurroundLand(mob/A, mob/Monsters/D)
	if(!rm_surround_on || !istype(D) || RmBeastKind(D)) return 0
	var/extra = RmFoesBeside(D) - 1
	var/def = RemasterCombatLevel(D, "Defence")
	if(def >= rm_surround_vet2) extra -= 2
	else if(def >= rm_surround_vet1) extra -= 1
	if(extra <= 0) return 0
	A.rm_surround_blows++
	return extra * rm_surround_land

// A stands a block or more above D, both on their feet up on the rock.
proc/RmHigher(mob/A, mob/D)
	if(!rm_high_ground_on || !istype(A, /mob/Monsters) || !istype(D, /mob/Monsters) || A.z != SKY_LAYER || D.z != SKY_LAYER) return 0
	if(A:Flying || D:Flying) return 0
	return RemasterFeetOf(A) - RemasterFeetOf(D) >= 1

// A melee blow's land bonus from the higher ground.
proc/RmHighLand(mob/A, mob/D)
	if(!RmHigher(A, D)) return 0
	A.rm_high_blows++
	return rm_high_land

// How far M's bow reaches at T: one tile more shooting down at it.
proc/RmBowRangeTo(mob/M, mob/T)
	return RmBowRange(M) + (T && RmHigher(M, T) ? rm_high_reach : 0)

// A move's reach at T (WeaponSkills.dm): a bow's moves are arrows too, a tile further shooting down at it, so an archer
// up on the higher ground stays there to use them.
proc/RmMoveRange(mob/M, list/D, mob/T)
	return (D["range"] || 1) + (D["class"] == "bow" && T && RmHigher(M, T) ? rm_high_reach : 0)
