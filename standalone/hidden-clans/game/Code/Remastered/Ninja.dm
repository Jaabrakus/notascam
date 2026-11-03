// Hidden Clans: chakra and the first ninja techniques (planning/GOA_MECHANICS_PLAN.md, first slice, 2026-11-01).
//  * Every ninja (a unit with a people's body: HumanParts, not a beast, a wagon or the undead) has chakra: 80, and 4 for
//    each point of Intelligence (its Magic folded in, StatFold.dm RmInt). It comes back by itself, 1.5% of it a second,
//    as GOA's did. What was spent and when is kept, and the chakra is worked out when read, so no unit is ticked for it.
//  * Techniques are weapon moves (WeaponSkills.dm rm_moves) that every ninja has whatever it holds ("ninja"), paid from
//    its chakra ("chakra") or the kunai it carries ("supply") instead of a weapon's mana. A seal ("seal", ticks) holds
//    the ninja where it stands forming the hand seals before the technique goes off. "min": not at a foe closer than this.
//  * In a fight a ninja uses them by itself when they are ready (the card's Auto / Manual): Substitution when it trades
//    blows (WeaponSkills.dm RmAutoMove), the ranged ones while it closes in (Attack.dm, Defense.dm: RmNinjaRanged). The
//    card's button uses one at once on the nearest foe in reach.

#define RM_CHAKRA_BASE 80
#define RM_CHAKRA_PER_INT 4
#define RM_CHAKRA_BACK 0.015     // share of its chakra back a second
#define RM_KUNAI_MAX 10          // kunai a ninja carries
#define RM_KUNAI_BACK 200        // ticks for one to be made good (GOA's were bought at the shop)

// Cooldowns are ticks before the swing pace (WeaponSkills.dm: x rm_swing_pace, 1 in Hidden Clans): 30 s, 5 s, 60 s and 3 s, GOA's.
var/list/rm_ninja_moves = list(
	"substitution"=list("name"="Substitution", "ninja"=1, "kind"="self", "chakra"=10, "cool"=300,
		"fx"=list("sub"=50), "desc"="For 5 seconds the next blow at it hits a log instead: it is gone in a puff and stands a few tiles off."),
	"flashstep"=list("name"="Flash step", "ninja"=1, "ranged"=1, "kind"="cast", "range"=6, "min"=3, "chakra"=12, "cool"=50,
		"fx"=list("flash"=1), "desc"="Crosses up to 6 tiles in a blink to stand beside a foe. Its next blow lands hard, but it is dazed for a moment."),
	"fireball"=list("name"="Fireball", "ninja"=1, "ranged"=1, "kind"="cast", "range"=5, "min"=3, "chakra"=25, "seal"=5, "cool"=600,
		"fx"=list("fireball"=1), "desc"="Hand seals, then a ball of fire at a foe up to 5 tiles off: everyone within a tile of it burns, and the ground catches."),
	"kunai"=list("name"="Kunai", "ninja"=1, "ranged"=1, "kind"="cast", "range"=6, "min"=2, "supply"=1, "cool"=30,
		"fx"=list("kunai"=1), "desc"="Throws a kunai at a foe up to 6 tiles off; it wounds where it lands. Carries 10, and one is made good every 20 seconds."))
// The order a ninja closing in tries the ranged ones (RmNinjaRanged).
var/list/rm_ninja_ranged = list("fireball", "kunai", "flashstep")
var/rm_ninja_merged = 0

mob/Monsters/var/tmp
	rm_chakra_spent = 0     // chakra spent and not back yet, as it was at rm_chakra_at
	rm_chakra_at = 0
	rm_kunai_spent = 0
	rm_kunai_at = 0
	rm_sub_until = 0        // Substitution is ready for a blow until then

obj/Items/woods/wood/var/tmp/rm_sub_log = 0

// The techniques join the weapon moves the first time any are looked at; the kunai joins the throws.
proc/RmNinjaMerge()
	if(rm_ninja_merged) return
	rm_ninja_merged = 1
	for(var/id in rm_ninja_moves) rm_moves[id] = rm_ninja_moves[id]
	rm_throw_kinds["kunai"] = list(6, 4, 9, null, 2, "kunai")

proc/RmIsNinja(mob/M)
	if(!istype(M, /mob/Monsters)) return 0
	var/mob/Monsters/N = M
	return N.HumanParts && !N.Critter && !N.Wagon && !N.Undead

proc/RmNinjaMoveIds()
	RmNinjaMerge()
	. = list()
	for(var/id in rm_ninja_moves) . += id

// --- Chakra and kunai -----------------------------------------------------------------------
mob/Monsters/proc/RmChakraMax()
	return round(RM_CHAKRA_BASE + RmInt() * RM_CHAKRA_PER_INT)

// Read without writing anything, so a ninja looked at is not marked changed.
mob/Monsters/proc/RmChakraSpentNow()
	if(rm_chakra_spent <= 0) return 0
	return max(0, rm_chakra_spent - RmChakraMax() * RM_CHAKRA_BACK * (world.time - rm_chakra_at) / 10)

mob/Monsters/proc/RmChakra()
	return max(0, RmChakraMax() - RmChakraSpentNow())

mob/Monsters/proc/RmKunaiSpentNow()
	if(rm_kunai_spent <= 0) return 0
	return max(0, rm_kunai_spent - (world.time - rm_kunai_at) / RM_KUNAI_BACK)

mob/Monsters/proc/RmKunai()
	return max(0, round(RM_KUNAI_MAX - RmKunaiSpentNow()))

// Before a technique goes: its chakra, its kunai, and not too close. manual: the player asked (it says why not).
mob/Monsters/proc/RmNinjaReady(id, mob/Monsters/T, manual = 0)
	var/list/D = rm_moves[id]
	var/Player/P = manual && istype(Owner, /Player) ? Owner : null
	if(D["chakra"] && RmChakra() < D["chakra"])
		if(P) P.RemasterNotice("[RemasterBareName()] needs [D["chakra"]] chakra for [D["name"]]; it has [round(RmChakra())].")
		return 0
	if(D["supply"] && RmKunai() < D["supply"])
		if(P) P.RemasterNotice("[RemasterBareName()] has no kunai left; one is made good every [RM_KUNAI_BACK / 10] seconds.")
		return 0
	if(T && D["min"] && get_dist(src, T) < D["min"])
		if(P) P.RemasterNotice("Too close for [D["name"]]: the foe must be [D["min"]] or more tiles off.")
		return 0
	return 1

mob/Monsters/proc/RmNinjaPay(id)
	var/list/D = rm_moves[id]
	if(D["chakra"])
		rm_chakra_spent = RmChakraSpentNow() + D["chakra"]
		rm_chakra_at = world.time
	if(D["supply"])
		rm_kunai_spent = RmKunaiSpentNow() + D["supply"]
		rm_kunai_at = world.time

// The open card (HUD.dm "chakra").
mob/Monsters/proc/RmChakraData()
	return list("chakra"=round(RmChakra()), "max"=RmChakraMax(), "kunai"=RmKunai(), "kunaiMax"=RM_KUNAI_MAX)

// --- Using them ---------------------------------------------------------------------------------
// What a technique does (WeaponSkills.dm RmMoveApply). 1 when it went.
mob/Monsters/proc/RmNinjaApply(id, mob/Monsters/T)
	var/list/D = rm_moves[id]
	var/list/F = D["fx"]
	var/seal = D["seal"] || 0
	if(seal)
		remaster_root_until = max(remaster_root_until, world.time + seal)
		destination = null
		RemasterHit(src, 0, "seal", src)
	if(F["sub"])
		rm_sub_until = world.time + F["sub"]
		RemasterHit(src, 0, "subready", src)
		return 1
	if(!T || !T.loc) return 0
	if(F["flash"]) return RmFlashStep(T)
	if(F["kunai"])
		RmNinjaKunai(T)
		return 1
	if(F["fireball"])
		var/turf/at = T.loc
		spawn(seal) RmFireball(at)
		return 1
	return 0

mob/Monsters/proc/RmFlashStep(mob/Monsters/T)
	var/turf/best
	for(var/turf/X in orange(1, T)) if(RemasterSpecialOpen(X, src) && (!best || get_dist(src, X) < get_dist(src, best))) best = X
	if(!best) return 0
	var/sx = x
	var/sy = y
	loc = best
	destination = null
	dir = get_dir(src, T)
	RemasterSpecialFx("shadowstep", src, sx, sy, x, y, null)
	remaster_opening = max(remaster_opening, 4)    // +12 on the next blow (Combats.dm), as a shadow step's
	RemasterHit(src, 0, "flash", src)
	RemasterStun(src, 10)                          // dazed a moment (GOA's flicker stunned for 2.7 s)
	return 1

mob/Monsters/proc/RmFireball(turf/at)
	if(!at || HP <= 0 || GoingToDie || at.z != z) return
	RemasterSpecialFx("breath", src, x, y, at.x, at.y, "fire")
	var/turf/c = at
	spawn(3)
		if(!src || !c) return
		var/list/area = list()
		for(var/turf/X in range(1, c)) if(!X.density) area += X
		RemasterBreathBurn(area, "fire", rand(10, 18), "fireball")   // burns, may set alight, and heats the ground (Specials.dm, Vapours.dm)

// A kunai as a thrown blade (Throwing.dm RemasterThrowAt): Ranged against Defence to land, a shield may block it, then a
// wound where it lands, through half the armour there.
mob/Monsters/proc/RmNinjaKunai(mob/Monsters/M)
	var/tx = M.x
	var/ty = M.y
	var/tz = M.z
	var/skill = ("DaggerSkill" in vars) && isnum(vars["DaggerSkill"]) ? vars["DaggerSkill"] : 0
	var/before = RemasterBodyHealth(M)
	var/alive = M.HP > 0 && !M.GoingToDie
	if(alive) M.RemasterThreatenedBy(src)
	var/kind = "miss"
	if(prob(RemasterThrowHitChance(src, M, skill)))
		if(M.WearingShield && prob(M.ShieldSkill / 2)) kind = "block"
		else kind = RemasterThrownWound(M, max(2, round(rand(4, 9) + skill / 8 + RmStr() / 12 + RemasterRangedBonus(src, M))), "kunai", 1 / 2)
	if(M && M.loc)
		var/d = round(before - RemasterBodyHealth(M))
		if(alive && (M.HP <= 0 || M.GoingToDie)) kind = "kill"
		RemasterCombatXP("throw", d)
		RemasterHitAt(tx, ty, tz, max(0, d), kind == "hit" && d <= 0 ? "miss" : kind, src, M.Owner, "kunai")
	else RemasterHitAt(tx, ty, tz, before, "kill", src, null, "kunai")

// A blow at a ninja with Substitution ready (Chains/Strike.dm): it hits a log. 1 when it did.
mob/Monsters/proc/RmSubstitute(mob/attacker)
	if(rm_sub_until <= world.time || HP <= 0 || GoingToDie || Stunned || Fainted || Sleeping || !isturf(loc)) return 0
	rm_sub_until = 0
	var/turf/from = loc
	var/turf/best
	var/far = -1
	for(var/turf/X in range(3, src))
		if(get_dist(X, from) < 2 || !RemasterSpecialOpen(X, src)) continue
		var/f = attacker ? get_dist(X, attacker) : get_dist(X, from)
		if(f > far)
			far = f
			best = X
	if(!best) return 0
	loc = best
	destination = null
	RemasterSpecialFx("shadowstep", src, from.x, from.y, x, y, null)
	RemasterHit(src, 0, "sub", attacker)
	var/obj/Items/woods/wood/L = new(from)
	L.rm_sub_log = 1
	spawn(100) if(L && isturf(L.loc)) del L   // the log is only for show: gone again before anyone hauls it off
	return 1

// Closing in on E (Attack.dm, Defense.dm): a ranged technique that is ready. 1 when one was used.
mob/Monsters/proc/RmNinjaRanged(mob/Monsters/E)
	if(!E || remaster_nonlethal || E.z != z || HP <= 0 || Stunned || Fainted || Sleeping || !RmIsNinja(src)) return 0
	RmNinjaMerge()
	var/d = get_dist(src, E)
	if(d < 2) return 0
	for(var/id in rm_ninja_ranged)
		var/list/D = rm_moves[id]
		if(d < (D["min"] || 2) || d > D["range"] || (rm_moves_off && (id in rm_moves_off))) continue
		if(RmMoveWait(src, id) || !RmNinjaReady(id, E)) continue
		if(!(E in oview(D["range"], src))) continue
		if(RmUseMove(id, E)) return 1
	return 0
