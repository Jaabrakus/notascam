// Weapon moves and spells (Remastered): a web of skills.
//  * Every weapon class (sword, axe, mace, spear, dagger, bow, staff, fist) has moves, and enchanted or rare
//    items carry their own: their defaults (anyone who can wield the item has them) and branch moves and
//    spells. Which a unit has depends on how its skills are built: each move needs some skills at a level -
//    the weapon's own (Sword, Axe...) and the character's (Attack, Strength, Defence, Ranged, Magic...).
//  * Items' moves are paid from the item's own mana (rm_mana), not the unit's: it refills slowly by itself,
//    faster from a rune stone carried in the bag, fastest on a rune circuit (MagicGear.dm RmManaTick). A
//    character's own mana is only its race's (a Svartalfar's Magical Skills).
//  * A unit fighting uses its moves by itself when they are ready (the player can turn any off on the unit
//    card's Combat tab, or use one at once); NPCs use theirs too.
// The moves are data (rm_moves); what they do is made of a few effects (RmMoveApply). The seed set here
// proves the system; the full web is mapped from it.

#define RM_MOVE_SKILL_NAMES list("Sword"="Sword", "Axe"="Axe", "Mace"="Mace", "Spear"="Spear", "Dagger"="Dagger", "Bow"="Bow", "UnArmed"="Unarmed", "Attack"="Attack", "Strength"="Strength", "Defence"="Defence", "Ranged"="Ranged", "Magic"="Magic")

// id -> move:
//   "name", "desc"
//   "class": a weapon class's move (RmMoveClass), or "item": an item's (its rm_gear)
//   "default": an item's own move - open to anyone holding it
//   "needs": skill id -> level (RemasterCombatLevel: "Sword", "Attack", "Magic"...)
//   "kind": "strike" (its foe, within "range"), "cast" (a foe within "range", from afar), "self" (no foe),
//           "passive" (on each of its blows that lands, "chance" in 100)
//   "mana": what each use takes from the item; "cool": ticks before it is ready again
//   "fx": what it does (RmMoveApply)
var/list/rm_moves = list(
	// --- weapon classes (seed) ---
	"lunge"=list("name"="Lunge", "class"="sword", "needs"=list("Sword"=10, "Attack"=10), "kind"="strike", "range"=2, "cool"=80,
		"fx"=list("step"=1, "dmg"=1.5), "desc"="Steps in and strikes a foe up to 2 tiles off, half again as hard."),
	"heavyblow"=list("name"="Heavy blow", "class"="sword", "needs"=list("Sword"=10, "Strength"=10), "kind"="strike", "range"=1, "cool"=100,
		"fx"=list("dmg"=1.8), "desc"="A slow, full-weight blow: nearly twice as hard."),
	"riposte"=list("name"="Riposte", "class"="sword", "needs"=list("Sword"=10, "Defence"=10), "kind"="self", "cool"=200,
		"fx"=list("riposte"=40), "desc"="For 4 seconds every blow at it is parried and struck back."),
	"cleave"=list("name"="Cleave", "class"="axe", "needs"=list("Axe"=10, "Strength"=10), "kind"="strike", "range"=1, "cool"=100,
		"fx"=list("dmg"=1, "around"=1), "desc"="One sweep through its foe and everyone beside it."),
	"skullcracker"=list("name"="Skullcracker", "class"="mace", "needs"=list("Mace"=10, "Strength"=10), "kind"="strike", "range"=1, "cool"=120,
		"fx"=list("dmg"=1.2, "stun"=20), "desc"="A blow to the head that stuns for 2 seconds."),
	"skewer"=list("name"="Skewer", "class"="spear", "needs"=list("Spear"=10, "Attack"=10), "kind"="strike", "range"=2, "cool"=100,
		"fx"=list("dmg"=1.3, "behind"=1), "desc"="Drives through its foe into the one behind it."),
	"flurry"=list("name"="Flurry", "class"="dagger", "needs"=list("Dagger"=10, "Attack"=10), "kind"="strike", "range"=1, "cool"=80,
		"fx"=list("hits"=3, "dmg"=0.6), "desc"="Three quick stabs."),
	"pinshot"=list("name"="Pinning shot", "class"="bow", "needs"=list("Bow"=10, "Ranged"=10), "kind"="cast", "range"=6, "cool"=120,
		"fx"=list("look"="pierce", "dmg"=1, "root"=30), "desc"="An arrow through the foot: held where it stands for 3 seconds."),

	// --- enchanted and rare items: their defaults, then branch moves and spells ---
	"astraledge"=list("name"="Astral edge", "item"="magic.rune sword", "default"=1, "kind"="passive", "mana"=1,
		"fx"=list("astral"=1), "desc"="Each hit adds astral damage."),
	"runebolt"=list("name"="Rune bolt", "item"="magic.rune sword", "needs"=list("Sword"=20, "Magic"=15), "kind"="cast", "range"=6, "mana"=12, "cool"=120,
		"fx"=list("look"="pierce", "bolt"=12), "desc"="A bolt of runic force at a foe up to 6 tiles off."),
	"burningedge"=list("name"="Burning edge", "item"="magic.flame sword", "default"=1, "kind"="passive", "chance"=30, "mana"=3,
		"fx"=list("burn"=1), "desc"="Its hits can set the foe alight."),
	"firewave"=list("name"="Fire wave", "item"="magic.flame sword", "needs"=list("Sword"=20, "Strength"=20), "kind"="strike", "range"=1, "mana"=15, "cool"=150,
		"fx"=list("dmg"=1, "around"=1, "burn"=1), "desc"="A sweep of fire through its foe and everyone beside it, setting them alight."),
	"frostbite"=list("name"="Frostbite", "item"="magic.frost axe", "default"=1, "kind"="passive", "mana"=1,
		"fx"=list("chill"=1), "desc"="Its hits slow and chill the foe."),
	"frozenhamstring"=list("name"="Frozen hamstring", "item"="magic.frost axe", "needs"=list("Axe"=20, "Attack"=20), "kind"="strike", "range"=1, "mana"=8, "cool"=150,
		"fx"=list("dmg"=1, "root"=30, "chill"=1), "desc"="Freezes the foe's legs: held where it stands for 3 seconds."),
	"chainspark"=list("name"="Chain spark", "item"="magic.storm spear", "default"=1, "kind"="passive", "mana"=4,
		"fx"=list("chain"=1), "desc"="Lightning jumps from the foe to another close by."),
	"calllightning"=list("name"="Call lightning", "item"="magic.storm spear", "needs"=list("Spear"=20, "Magic"=20), "kind"="cast", "range"=6, "mana"=15, "cool"=200,
		"fx"=list("look"="pierce", "bolt"=14, "stun"=15), "desc"="Lightning from the sky on a foe up to 6 tiles off; it is stunned."),
	"voiddrain"=list("name"="Drain", "item"="magic.void blade", "default"=1, "kind"="passive", "mana"=2,
		"fx"=list("drain"=33), "desc"="A third of each hit's damage heals its wielder."),
	"smite"=list("name"="Smite", "item"="magic.holy mace", "default"=1, "kind"="passive", "mana"=2,
		"fx"=list("smite"=1), "desc"="Double damage to the undead, demons and half-demons."),
	"manawell"=list("name"="Mana well", "item"="magic.crystal staff", "default"=1, "kind"="passive", "chance"=0,
		"fx"=list(), "desc"="Its own mana refills fast and tops up the other magic weapons you carry; it lights the way."),
	"echo"=list("name"="Echo", "item"="magic.orb staff", "default"=1, "kind"="passive", "chance"=0, "mana"=10,
		"fx"=list(), "desc"="Its bearer's race special now and then strikes twice."),
	"raiseskeleton"=list("name"="Raise Skeleton", "item"="magic.skull staff", "default"=1, "kind"="self", "mana"=15, "cool"=50,
		"fx"=list("raise"=1), "desc"="A skull in sight rises as a skeleton of yours."),
	"bonespear"=list("name"="Bone spear", "item"="magic.skull staff", "needs"=list("Magic"=20), "kind"="cast", "range"=6, "mana"=10, "cool"=100,
		"fx"=list("look"="pierce", "bolt"=12, "bleed"=1), "desc"="A shard of bone at a foe up to 6 tiles off; it bleeds."),
	"ignite"=list("name"="Ignite", "item"="magic.flame staff", "default"=1, "kind"="passive", "chance"=20, "mana"=3,
		"fx"=list("burn"=1), "desc"="Its bearer's fire always catches; its blows can set foes alight."),
	"regrowth"=list("name"="Regrowth", "item"="magic.nature staff", "default"=1, "kind"="passive", "chance"=0,
		"fx"=list(), "desc"="Your people near it heal faster, and crops near it ripen faster."),
	"dragonward"=list("name"="Dragon's ward", "item"="magic.dragon staff", "default"=1, "kind"="passive", "chance"=15, "mana"=3,
		"fx"=list("burn"=1), "desc"="Fire can't touch its bearer; its blows can set foes alight."),
	"silkstrike"=list("name"="Silk strike", "item"="magic.spider staff", "default"=1, "kind"="passive", "chance"=20, "mana"=3,
		"fx"=list("web"=1), "desc"="Its blows can hold a foe fast in silk."))

// How much mana an item holds (its rm_gear); none, no mana.
var/list/rm_item_mana = list("magic.rune sword"=40, "magic.flame sword"=40, "magic.frost axe"=50, "magic.storm spear"=50,
	"magic.void blade"=60, "magic.holy mace"=60, "magic.crystal staff"=100, "magic.orb staff"=100, "magic.skull staff"=100,
	"magic.flame staff"=100, "magic.nature staff"=100, "magic.dragon staff"=100, "magic.spider staff"=100)

obj/Items/var/rm_mana   // an enchanted item's mana (saved); null until first looked at: full

mob/Monsters/var/list/rm_moves_off   // saved: move ids this unit doesn't use by itself
mob/Monsters/var/tmp
	rm_moves_last                    // the move it used last (a death's cause)
	list/rm_move_at                  // move id -> when it is ready again
	rm_riposte_until = 0
	rm_riposting = 0

proc/RmManaMax(obj/Items/I)
	return I && I.rm_gear ? (rm_item_mana[I.rm_gear] || 0) : 0

proc/RmManaOf(obj/Items/I)
	var/m = RmManaMax(I)
	if(!m) return 0
	if(!isnum(I.rm_mana)) I.rm_mana = m
	return I.rm_mana

proc/RmManaSpend(obj/Items/I, n)
	if(!n) return 1
	if(RmManaOf(I) < n) return 0
	I.rm_mana -= n
	return 1

proc/RmManaAdd(obj/Items/I, n)
	var/m = RmManaMax(I)
	if(!m || n <= 0) return 0
	var/had = RmManaOf(I)
	I.rm_mana = min(m, had + n)
	return I.rm_mana - had

// The class of what it holds: a staff, else the game's weapon classes (Hits.dm).
proc/RmMoveClass(mob/M)
	var/obj/Items/Equipment/W = RmHeldWeapon(M)
	if(W && W.rm_gear && findtext(W.rm_gear, "staff")) return "staff"
	return RemasterWeaponClass(M)

// The moves its weapon gives it, open or not: its class's and its item's.
proc/RmMovesFor(mob/M)
	. = list()
	var/obj/Items/Equipment/W = RmHeldWeapon(M)
	var/cls = RmMoveClass(M)
	for(var/id in rm_moves)
		var/list/D = rm_moves[id]
		if(D["class"] ? D["class"] == cls : (W && D["item"] == W.rm_gear)) . += id

// What it lacks for a move, "" when it has it.
proc/RmMoveLacks(mob/M, id)
	var/list/D = rm_moves[id]
	var/list/need = D["needs"]
	var/list/lack = list()
	var/list/names = RM_MOVE_SKILL_NAMES
	for(var/s in need) if(RemasterCombatLevel(M, s) < need[s]) lack += "[names[s] || s] [need[s]]"
	return jointext(lack, " · ")

proc/RmMoveOpen(mob/M, id)
	return (id in RmMovesFor(M)) && RmMoveNeedsMet(M, id)

// RmMoveLacks(M, id) is "": every skill it needs is at its level (combat-speed, 10-26: without the words and lists).
proc/RmMoveNeedsMet(mob/M, id)
	var/list/D = rm_moves[id]
	var/list/need = D["needs"]
	for(var/s in need) if(RemasterCombatLevel(M, s) < need[s]) return 0
	return 1

proc/RmMoveWait(mob/Monsters/M, id)
	var/t = M.rm_move_at ? M.rm_move_at[id] : 0
	return max(0, (t || 0) - world.time)

// A foe for a move: the one it fights, else the nearest within reach.
proc/RmMoveTarget(mob/Monsters/M, list/D)
	var/r = D["range"] || 1
	var/list/cands = list(M.Target)
	if(M.remaster_attack) cands += M.remaster_attack.target
	if(ismob(M.destination)) cands += M.destination
	for(var/mob/Monsters/E in cands) if(E && E != M && E.HP > 0 && !E.GoingToDie && E.z == M.z && get_dist(M, E) <= r && RemasterHostile(M, E, 1) && (E in view(r, M)))
		return E
	var/mob/Monsters/best
	for(var/mob/Monsters/E in oview(r, M)) if(E.HP > 0 && !E.GoingToDie && RemasterHostile(M, E))
		if(!best || get_dist(M, E) < get_dist(M, best)) best = E
	return best

// Use a move now. 1 when it was used. manual: the player asked (it says why not).
mob/Monsters/var/tmp/rm_move_now   // the move it is making, while its blows land
mob/Monsters/proc/RmUseMove(id, mob/Monsters/T, manual = 0)
	var/list/D = rm_moves[id]
	var/Player/P = istype(Owner, /Player) ? Owner : null
	if(!D || HP <= 0 || GoingToDie || Stunned || Fainted || Sleeping) return 0
	if(D["kind"] == "passive") return 0
	if(!RmMoveOpen(src, id))
		if(manual && P) P.RemasterNotice("[RemasterBareName()] can't use [D["name"]] yet: needs [RmMoveLacks(src, id) || "the right weapon"].")
		return 0
	if(RmMoveWait(src, id))
		if(manual && P) P.RemasterNotice("[D["name"]] is ready in [round(RmMoveWait(src, id) / 10) + 1] s.")
		return 0
	var/obj/Items/Equipment/W = RmHeldWeapon(src)
	if(D["mana"] && RmManaOf(W) < D["mana"])
		if(manual && P) P.RemasterNotice("[W] needs [D["mana"]] mana for [D["name"]]; it has [round(RmManaOf(W))].")
		return 0
	if(D["kind"] in list("strike", "cast"))
		if(!T) T = RmMoveTarget(src, D)
		if(!T || get_dist(src, T) > RmMoveRange(src, D, T))   // a bow's, a tile further from higher ground (Surround.dm)
			if(manual && P) P.RemasterNotice("No foe within [D["range"] || 1] tile[(D["range"] || 1) == 1 ? "" : "s"] of [RemasterBareName()] for [D["name"]].")
			return 0
	rm_moves_last = lowertext(D["name"])
	rm_move_now = id   // its blows carry the move to the 3D view (Hits.dm)
	var/done = RmMoveApply(id, T)
	rm_move_now = null
	if(!done) return 0
	if(D["mana"]) RmManaSpend(W, D["mana"])
	if(!rm_move_at) rm_move_at = list()
	rm_move_at[id] = world.time + (D["cool"] || 50) * rm_swing_pace   // the slow pace, as the swings' (Hits.dm)
	rm_swung_at = world.time   // drawn as a blow (View3D.dm Remaster3DAct)
	if(T) RmTurnToward(get_dir(src, T))   // at a turn's pace (Facing.dm)
	return 1

// What a move does. 1 when it did something.
mob/Monsters/proc/RmMoveApply(id, mob/Monsters/T)
	var/list/D = rm_moves[id]
	var/list/F = D["fx"] || list()
	if(F["riposte"])
		rm_riposte_until = world.time + F["riposte"]
		RemasterHit(src, 0, "guard", src)
		return 1
	if(F["raise"]) return !!RmRaiseSkeleton(src, Owner)
	if(!T) return 0
	if(F["look"]) RemasterSpecialFx(F["look"], src, x, y, T.x, T.y, "spark")
	if(F["step"] && get_dist(src, T) > 1) step_towards(src, T)
	var/list/foes = list(T)
	if(F["around"]) for(var/mob/Monsters/O in orange(1, T)) if(O != src && O.HP > 0 && !O.GoingToDie && RemasterHostile(src, O)) foes += O
	if(F["behind"])
		var/turf/B = get_step(T, get_dir(src, T))
		for(var/mob/Monsters/O in B) if(O != src && O.HP > 0 && !O.GoingToDie && RemasterHostile(src, O)) foes += O
	for(var/mob/Monsters/E in foes)
		if(!E || E.HP <= 0 || E.GoingToDie) continue
		var/before = RemasterBodyHealth(E)
		if(F["dmg"])
			for(var/n = 1, n <= (F["hits"] || 1), n++) if(E && E.HP > 0 && !E.GoingToDie) RmMoveBlow(E, F["dmg"])
		if(F["bolt"] && E && E.HP > 0)
			var/x = rand(round(F["bolt"] * 0.7), round(F["bolt"] * 1.3))
			E.HP -= x
			E.RemasterThreatenedBy(src)
			RemasterHit(E, x, "shock", src)
		var/d = E ? max(0, before - RemasterBodyHealth(E)) : 0
		if(E && (!F["dmg"] || d > 0)) RmMoveEffects(F, E, d)   // a blow's effects only when it lands
	return 1

// A move's blow: it lands. As the game's blow is reckoned (Combats.dm Attack: the weapon's damage, Strength, the
// melee skills, the foe's armour; the swing's weight, Hits.dm RmSwingDamage), times the move's factor, taken from
// its health; its weapon's own effects follow (RmWeaponEffect). Fighting to knock out, a subdue blow. The game's
// own blows land only where a roll of body parts picks, so most do nothing; a move doesn't. Returns the damage.
mob/Monsters/proc/RmMoveBlow(mob/Monsters/E, mult = 1)
	if(!E || E.HP <= 0 || E.GoingToDie) return 0
	if(RemasterFightsNonLethal(E))
		RemasterSubdueBlow(E)
		return 0
	if(rm_moves_parts) return RmMovePartBlow(E, mult)   // a blow, on a part (below)
	var/dmg = (rand(min(WeaponDamageMin, WeaponDamageMax), max(WeaponDamageMin, WeaponDamageMax)) + RmStr() / 2 + RemasterMeleeBonus(src, E)) * RemasterArmourFactor(src, E, "UpperBody")   // a move strikes the body: the chestplate's armour (CombatSkills.dm)
	dmg = round(max(5, dmg) * DamageMultiplier * RmSwingDamage(src) * mult)
	var/alive = E.HP > 0 && !E.GoingToDie
	E.HP -= dmg
	E.RemasterThreatenedBy(src)
	RemasterCombatXP("melee", dmg)
	RemasterHit(E, dmg, "hit", src)
	if(alive && E.HP <= 0 && !E.GoingToDie)
		E.GoingToDie = 1
		E.Killer = "[src]"
		E.RmFallBy(src)   // it falls dying, as from a blow (Falls.dm)
		E.DeathType = "a [rm_moves_last || "blow"]"
		E.Death()
		return dmg
	RmWeaponEffect(E, dmg)
	return dmg

// The lasting effects, on a foe a move or a passive has hit for d.
mob/Monsters/proc/RmMoveEffects(list/F, mob/Monsters/E, d)
	if(!E || E.HP <= 0 || E.GoingToDie)
		return
	if(F["stun"] && !E.Stunned)
		E.Stunned = 1
		spawn(F["stun"]) if(E) E.Stunned = 0
		RemasterHit(E, 0, "stagger", src)
	if(F["root"] && !E.Flying)
		E.remaster_root_until = max(E.remaster_root_until, world.time + F["root"])
		E.remaster_slow_until = max(E.remaster_slow_until, world.time + F["root"] * 2)
		E.destination = null
		RemasterHit(E, 0, "webbed", src)
	if(F["web"] && E.remaster_root_until <= world.time && !E.Flying)
		E.remaster_root_until = world.time + 30
		E.remaster_slow_until = world.time + 60
		E.destination = null
		RemasterHit(E, 0, "webbed", src)
	if(F["burn"] && !RmFireproof(E) && !E.OnFire)
		E.Fire()
		RemasterHit(E, 0, "burn", src)
	if(F["chill"])
		E.remaster_slow_until = max(E.remaster_slow_until, world.time + 40)
		E.Coldness = min(100, E.Coldness + 10)
		RemasterHit(E, 0, "chill", src)
	if(F["bleed"] && ("BloodContent" in E.vars))
		E.BloodContent -= 10
		E.BloodLoss()
		RemasterHit(E, 0, "bleed", src)
	if(F["astral"])
		var/x = rand(5, 9)
		E.HP -= x
		RemasterHit(E, x, "astral", src)
	if(F["smite"] && (E.Undead || E.Race == "Demon" || (E.SubRace in rm_half_demons)))
		var/x = max(1, d)
		E.HP -= x
		RemasterHit(E, x, "smite", src)
	if(F["drain"])
		var/back = round(max(0, d) * F["drain"] / 100)
		if(back > 0)
			HP = min(MAXHP, HP + back)
			RemasterHit(src, back, "drain", src)
	if(F["chain"])
		for(var/mob/Monsters/O in orange(3, E)) if(O != src && O.HP > 0 && !O.GoingToDie && RemasterHostile(src, O))
			var/x = rand(8, 14)
			O.HP -= x
			O.RemasterThreatenedBy(src)
			RemasterSpecialFx("pierce", E, E.x, E.y, O.x, O.y, "shock")
			RemasterHit(O, x, "shock", src)
			if(O.HP <= 0 && !O.GoingToDie)
				O.GoingToDie = 1
				O.Killer = "[src]"
				O.RmFallBy(src)   // it falls dying, as from a blow (Falls.dm)
				O.DeathType = "lightning"
				O.Death()
			break
	if(E && E.HP <= 0 && !E.GoingToDie)
		E.GoingToDie = 1
		E.Killer = "[src]"
		E.RmFallBy(src)   // it falls dying, as from a blow (Falls.dm)
		E.Death()

// Each blow that lands: the passives of what it holds (chance, then its mana).
mob/Monsters/proc/RmPassiveMoves(mob/Monsters/E, d)
	var/obj/Items/Equipment/W = RmHeldWeapon(src)
	if(!W || !W.rm_gear) return
	for(var/id in RmMovesFor(src))
		var/list/D = rm_moves[id]
		if(D["kind"] != "passive" || !length(D["fx"]) || !RmMoveOpen(src, id)) continue
		if(!prob(isnull(D["chance"]) ? 100 : D["chance"])) continue
		if(D["mana"] && !RmManaSpend(W, D["mana"])) continue
		RmMoveEffects(D["fx"], E, d)
		if(!E || E.HP <= 0) return

// In a fight (Hits.dm RemasterStrike, each plain blow): a move that is ready, open and allowed to go by
// itself is used instead of the plain blow. 1 when one was.
mob/Monsters/proc/RmAutoMove(mob/Monsters/E)
	if(!istype(E) || rm_riposting) return 0
	for(var/id in RmMovesFor(src))   // its moves now: a move tried and not used changes nothing it holds, so each id stays one of them (RmMoveOpen's first half)
		var/list/D = rm_moves[id]
		if(D["kind"] == "passive" || (rm_moves_off && (id in rm_moves_off))) continue
		var/list/F = D["fx"]
		if(D["kind"] == "self" && !F["riposte"]) continue   // Raise Skeleton and the like only when asked
		if(!RmMoveNeedsMet(src, id) || RmMoveWait(src, id)) continue
		if((D["kind"] in list("strike", "cast")) && get_dist(src, E) > RmMoveRange(src, D, E)) continue
		if(RmUseMove(id, D["kind"] == "self" ? null : E)) return 1
	return 0

// --- For the unit card (HUD.dm "moves", "wmana") --------------------------------------------
proc/RmMovesData(mob/Monsters/M)
	. = list()
	for(var/id in RmMovesFor(M))
		var/list/D = rm_moves[id]
		. += list(list("id"=id, "name"=D["name"], "desc"=D["desc"], "kind"=D["kind"], "item"=!!D["item"], "lack"=RmMoveLacks(M, id),
			"wait"=round(RmMoveWait(M, id) / 10, 0.1), "auto"=!(M.rm_moves_off && (id in M.rm_moves_off)), "mana"=D["mana"] || 0,
			"range"=D["range"] || 0, "cool"=round((D["cool"] || 0) * rm_swing_pace / 10, 0.1)))

proc/RmWeaponManaData(mob/M)
	var/obj/Items/Equipment/W = RmHeldWeapon(M)
	if(!RmManaMax(W)) return null
	return list("name"="[W.name]", "mana"=round(RmManaOf(W)), "max"=RmManaMax(W))

Player/proc/RmMoveCommand(value, auto = 0)
	var/list/p = splittext("[value]", "|")
	if(length(p) != 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || !rm_moves[p[2]]) return 0
	if(auto)
		if(!M.rm_moves_off) M.rm_moves_off = list()
		if(p[2] in M.rm_moves_off) M.rm_moves_off -= p[2]
		else M.rm_moves_off += p[2]
		return 1
	if(M.RmUseMove(p[2], null, 1) && M.Owner == src) RemasterNotice("[M.RemasterBareName()]: [rm_moves[p[2]]["name"]]!")
	return 1

// Weapon moves hit like blows (the user, 2026-10-26: "Yes, build it"; "Skills chance of landing is based on attack and
// weapon level"): the move's blow is the game's own, no swing timer, parry, riposte or the weapon's own extras, its factor
// on the blow; the shield and the dodge as for any blow, then its own land roll (CombatSkills.dm RmMoveLandChance), one
// part by the d20, through its armour, the wound formula and severing (Wounds.dm). Returns the damage it did.
var/rm_moves_parts = 1   // 0: a move's blow lands every time and takes health directly, as before
mob/var/tmp/rm_move_sure = 0               // the move's factor while its blow is struck (Combats.dm Attack, Hits.dm, CombatSkills.dm)
mob/var/tmp/rm_move_skill = "Attack"       // the weapon skill its land roll counts (CombatSkills.dm RmMoveLandChance)
mob/Monsters/var/tmp/rm_move_killing       // the move's name while its blow is struck at this one ("a lunge")
mob/Monsters/proc/RmMovePartBlow(mob/Monsters/E, mult)
	var/before = RemasterBodyHealth(E)
	var/was = remaster_striking
	remaster_striking = 1
	rm_move_sure = mult || 1
	rm_move_skill = RmMoveSkillOf()
	E.rm_move_killing = "a [rm_moves_last || "blow"]"
	RemasterStrike(E)
	rm_move_sure = 0
	remaster_striking = was
	if(Rm3DGone(E)) return max(1, round(before))
	E.rm_move_killing = null
	var/d = max(0, round(before - RemasterBodyHealth(E)))
	if(d > 0 && E.HP > 0 && !E.GoingToDie) RmWeaponEffect(E, d)
	return d

// The weapon skill of the move being made (its "needs"), else of the weapon in hand (a riposte).
mob/Monsters/proc/RmMoveSkillOf()
	var/list/D = rm_move_now ? rm_moves[rm_move_now] : null
	if(D && D["needs"]) for(var/k in D["needs"]) if(!(k in list("Attack", "Strength", "Defence", "Ranged", "Magic"))) return k
	var/list/by_class = list("sword"="Sword", "axe"="Axe", "mace"="Mace", "spear"="Spear", "dagger"="Dagger", "bow"="Bow", "claws"="Claw", "fist"="UnArmed")
	return by_class[RemasterWeaponClass(src)] || "Attack"

// The original's head and body hits do something only where one of its organ rolls lands (4 in 100 each, Combats.dm): a
// move's blow that lands there strikes one of them at least.
var/rm_move_organ = 0   // 1: a move's head or body blow strikes an organ at least (off: it rolls them as a plain blow; the duel table)
mob/proc/RmMoveOrgan(list/flags)
	for(var/f in flags) if(vars[f]) return
	vars[pick(flags)] = 1

// mob/Monsters/Death: this file's part is step RmChainDeath_WeaponSkills in Code/Remastered/Chains/Death.dm
