// Taming great beasts (Remastered). Dragons and grown spiders are too big to knock out by hand
// (Subdue.dm), so there are two ways to have one of your own:
//  - Steal an egg. Every wild dragon (and wild grown spider) keeps a nest with eggs at its home.
//    An egg is an item: any of your people can pick it up and carry it off, and its mother hunts
//    whoever carries it. Laid down away from a nest it warms, and after a while it hatches into a
//    hatchling of yours (it grows with age: Beasts.dm RmBeastSize).
//  - Chain it down. Iron Chains are made at the Forge (two iron ingots). Right-click a beast,
//    Chain it down: the selected units fight it non-lethal until it is worn down (under a third
//    of its health, or two legs mangled), then one beside it binds it with the chains its party
//    carries (a dragon takes 3, a great spider 2). Bound, it can't walk, fly or fight. Feed it raw
//    meat (right-click, Feed it) three times, a minute or more apart, and it accepts you; left
//    unfed for three minutes it snaps a chain, and with none left it breaks free.
// Pictures: art/enhance/beastparts32.py (eggs, egg sac, nests, chains).

var/rm_egg_hatch = 3600      // ticks an egg must lie warm, away from a nest (the game's own dragon eggs: 3600)
var/rm_tame_feeds = 3        // feedings to win a chained beast over
var/rm_tame_gap = 600        // and at least this long between them
var/rm_tame_hunger = 1800    // unfed this long, it snaps a chain
var/list/rm_eggs = list()
var/list/rm_bound_beasts = list()

mob/Monsters/var/tmp
	obj/RmBeastNest/rm_nest        // a wild beast's nest (it guards it)
	Player/rm_bound                // chained down by this player (from rm_bound_key after a load)
	rm_fed_at = 0                  // last fed (or bound)
	rm_trust_at = 0                // last feeding that counted
// Saved: a chained beast is held by the player who chained it (in their UnitList, as a captive is),
// so it is saved with their army, its chains and how far it has come round with it.
mob/Monsters/var
	rm_bound_key                   // the player holding it in chains
	rm_wild_owner                  // whose it was (an NPC side's name), to go back to if it breaks free
	rm_bound_chains = 0
	rm_trust = 0

obj/RmBeastNest
	name = "Dragon's Nest"
	icon = 'Icons/Remastered/Items/beastparts.dmi'
	icon_state = "nest"
	density = 0
	layer = TURF_LAYER + 0.05
	var/kind = "dragon"
	var/tmp/mob/Monsters/mother

obj/Items/RmBeastEgg
	// its values: art/items/catalogue.json row rmbeastegg (export_items.py writes ItemData.dm)
	var/kind = "dragon"
	var/variant = "red"
	var/claim_key            // the player whose people took it
	var/warm = 0             // ticks lain warm away from a nest
	var/tmp/mob/Monsters/mother
	New()
		..()
		rm_eggs += src
	Del()
		rm_eggs -= src
		return ..()
	DeleteItem()   // laid down, it lies there till it hatches (6 min): the ground's 3-minute clean-up (Item Procs.dm) took it first
		return

obj/Items/RemasterTools/IronChains
	// its values: art/items/catalogue.json row remastertools.ironchains (export_items.py writes ItemData.dm)

proc/RmTameKind(mob/Monsters/M)
	if(!istype(M) || M.HP <= 0) return null
	if(M.Race == "Dragon") return "dragon"
	if(M.Race == "Spider" && RmBeastSize(M, "spider") >= 1.7) return "spider"
	return null

proc/RmChainsNeeded(mob/Monsters/M)
	return M.Race == "Dragon" ? 3 : 2

// How near one of your people must stand to bind or feed it: beside one of its legs.
proc/RmBeastReach(mob/Monsters/M)
	return 1 + round(RmBeastSize(M, M.Race == "Dragon" ? "dragon" : "spider"))

proc/RmWornDown(mob/Monsters/M)
	return M.HP <= M.MAXHP * 0.35 || RmBeastLegsMangled(M) >= 2

// --- Map dragons, nests and eggs -------------------------------------------------------
// The map's dragons are grown (the original leaves their Age at 0, which draws a hatchling).
mob/Monsters/Dragon/NPCDragon/New()
	. = ..()
	if(Age < 30) Age = rand(60, 150)

// world/New: this file's part is step RmChainWorldNew_Taming in Code/Remastered/Chains/WorldNew.dm

proc/RmPlaceNests()
	for(var/mob/Monsters/M in world) if(!istype(M.Owner, /Player) && !M.rm_nest && isturf(M.loc) && RmTameKind(M))
		if(M.Race == "Dragon" && RmBeastSize(M, "dragon") < 1.5) continue
		RmMakeNest(M, M.Race == "Dragon" ? 2 : 3)

proc/RmMakeNest(mob/Monsters/M, eggs = 2)
	var/turf/T = M.loc
	if(!isturf(T)) return null
	if(T.density)
		for(var/turf/X in range(2, M)) if(!X.density)
			T = X
			break
	var/obj/RmBeastNest/N = new(T)
	N.mother = M
	M.rm_nest = N
	M.HomeLoc = T
	if(M.Race == "Spider")
		N.kind = "spider"
		N.name = "Spider's Nest"
		N.icon_state = "webnest"
	var/have = 0
	for(var/obj/Items/RmBeastEgg/E in range(1, T))   // eggs saved from the last game lie here already: its own again
		if(E.claim_key) continue
		E.mother = M
		have++
	for(var/i = have + 1, i <= eggs, i++) RmMakeEgg(M, T)
	return N

proc/RmMakeEgg(mob/Monsters/M, turf/T)
	var/obj/Items/RmBeastEgg/E = new(T)
	E.mother = M
	if(M.Race == "Spider")
		E.kind = "spider"
		E.name = "Spider Egg Sac"
		E.icon_state = "eggsac"
		E.desc = "A great spider's eggs, bound in silk. Carried off and laid down away from a nest, they will hatch into a spider of your own."
	else
		E.variant = RmBeastVariant(M, "dragon") || "red"
		E.icon_state = "egg-[E.variant]"
		E.name = "[rm_dragon_colours[E.variant] || ""] Dragon Egg"
	return E

proc/RmEggPlayer(obj/Items/RmBeastEgg/E)
	for(var/Player/P in Players) if(P.key == E.claim_key) return P
	return null

// Every 2 s: carried eggs are claimed and their mothers hunt the thief; laid-down eggs warm and hatch.
proc/RmTamingLoop()
	while(1)
		sleep(20)
		for(var/obj/Items/RmBeastEgg/E in rm_eggs) if(E) E.RmEggTick()
		RmRelinkBound()
		for(var/mob/Monsters/M in rm_bound_beasts) if(M) M.RmBoundTick()

// After a load: a beast saved in chains is held again by its player once they are in the game.
// Its hunger starts afresh, and it may be fed at once.
proc/RmRelinkBound()
	for(var/Player/P in Players) for(var/mob/Monsters/M in P.UnitList)
		if(M.rm_bound_key == P.key && M.rm_bound != P && M.HP > 0)
			M.rm_bound = P
			M.rm_fed_at = world.time
			M.rm_trust_at = world.time - rm_tame_gap
			rm_bound_beasts |= M

obj/Items/RmBeastEgg/proc/RmEggTick()
	if(ismob(loc))
		var/mob/Monsters/C = loc
		if(!istype(C) || !istype(C.Owner, /Player)) return
		claim_key = C.Owner:key
		var/mob/Monsters/Mo = mother
		if(Mo && Mo.HP > 0 && !Mo.GoingToDie && !istype(Mo.Owner, /Player) && !Mo.rm_bound && Mo.z == C.z && get_dist(Mo, C) <= 15)
			Mo.Target = C     // the mother goes after whoever carries her egg
			Mo.destination = C
		return
	if(!isturf(loc) || !claim_key) return
	if(locate(/obj/RmBeastNest) in loc)
		warm = 0
		return
	warm += 20
	desc = "[initial(desc)] It is [round(100 * min(1, warm / rm_egg_hatch))]% of the way to hatching."
	if(warm >= rm_egg_hatch) RmHatch()

obj/Items/RmBeastEgg/proc/RmHatch()
	var/Player/P = RmEggPlayer(src)
	var/turf/T = loc
	if(!P || !isturf(T)) return
	var/mob/Monsters/H
	if(kind == "spider") H = new /mob/Monsters/Spider/Warrior(T)
	else
		H = new /mob/Monsters/Dragon(T)
		H.icon_state = variant
	H.Age = 0
	H.ChangeOwnership(P)
	H.name = "{[P]} [H.Race]"
	H.Hunger = 100
	H.Tiredness = 100
	P.RemasterNotice("[name] hatched: [H.RemasterBareName()] is yours!")
	P.RemasterLog("[name] hatched", "good", T)
	view(T) << "<b>[name] cracks open: a hatchling!</b>"
	del src

// --- Chain it down ---------------------------------------------------------------------
datum/remaster_attack/var/chain = 0

Player/proc/RmChainOrder(mob/Monsters/E)
	if(!RmTameKind(E))
		RemasterNotice("Only a dragon or a grown great spider can be chained down.")
		return 0
	if(E.rm_bound)
		RemasterNotice("[RemasterCombatName(E)] is already in chains.")
		return 0
	var/n = 0
	var/chains = 0
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || M.HP <= 0 || RemasterIsSiege(M) || M.Wagon || !RemasterHostile(M, E, 1)) continue
		for(var/obj/Items/RemasterTools/IronChains/X in M) chains++
		M.RemasterCancelOrders()
		if(M.remaster_defense) M.RemasterCancelDefense(0)
		M.RemasterCareInterrupt()
		M.RemasterWake()
		M.remaster_patrol = null
		var/datum/remaster_attack/K = new
		K.issuer = src
		K.target = E
		K.chosen = E
		K.capture = 1    // fight it non-lethal (Subdue.dm): never the killing blow
		K.chain = 1
		K.last_position = M.loc
		K.last_progress = world.time
		M.remaster_attack = K
		M.remaster_order_status = "Chaining [RemasterCombatName(E)]"
		n++
	remaster_attack_mode = 0
	var/need = RmChainsNeeded(E)
	if(!n) RemasterNotice("Select units to chain it down with.")
	else RemasterNotice("Chain it down: [n] wear [RemasterCombatName(E)] down (under a third of its health), then bind it with [need] iron chains[chains < need ? " (they carry [chains]: bring more from the Forge)" : ""].")
	return n

// The chain order's part of an attack tick (Subdue.dm): fight it down as any attack, then bind it.
mob/Monsters/RemasterCaptureTick(datum/remaster_attack/K, mob/Monsters/E)
	if(!K || !K.chain) return ..()
	if(!E || E.HP <= 0 || E.GoingToDie || E.rm_bound || E.Owner == Owner)
		RemasterAttackStop()
		return 1
	if(!RmWornDown(E) || get_dist(src, E) > RmBeastReach(E)) return 0
	destination = null
	var/Player/P = K.issuer
	if(istype(P) && P.RmBindBeast(src, E))
		for(var/mob/Monsters/O in P.UnitList) if(O.remaster_attack && O.remaster_attack.target == E && O.remaster_attack.chain) O.RemasterAttackStop()
		remaster_order_status = "Chained [RemasterCombatName(E)]"
	else RemasterAttackStop()
	return 1

Player/proc/RmBindBeast(mob/Monsters/C, mob/Monsters/E)
	var/need = RmChainsNeeded(E)
	var/list/have = list()
	for(var/mob/Monsters/O in range(RmBeastReach(E) + 2, E)) if(O.Owner == src)
		for(var/obj/Items/RemasterTools/IronChains/X in O) if(X.suffix != "(Equipped)") have += X
	if(length(have) < need)
		RemasterNotice("[RemasterCombatName(E)] is worn down, but binding it takes [need] iron chains: your people beside it carry [length(have)].")
		return 0
	for(var/i = 1, i <= need, i++)
		var/obj/Items/X = have[i]
		var/mob/O = X.loc
		O.weight -= X.weight
		del X
	E.rm_bound = src
	E.rm_bound_key = key
	E.rm_wild_owner = istype(E.Owner, /Player) ? null : E.Owner
	E.ChangeOwnership(src)   // held, as a captive is: saved with this player's army; it still can't walk or fight
	E.rm_bound_chains = need
	E.rm_trust = 0
	E.rm_fed_at = world.time
	E.rm_trust_at = 0
	E.Target = null
	E.destination = null
	E.remaster_attack = null
	if(E.Flying) E.Fly(0, "Land")
	rm_bound_beasts |= E
	RemasterNotice("[C.RemasterBareName()] chains [RemasterCombatName(E)] down! Feed it raw meat [rm_tame_feeds] times, a minute or more apart, and it is yours; unfed, it will snap its chains.")
	RemasterLog("Chained [RemasterCombatName(E)]", "good", E)
	view(E) << "<b>[E] is chained down!</b>"
	return 1

// Every 2 s: a chained beast stays put; unfed too long, it snaps a chain, and with none left it is free.
mob/Monsters/proc/RmBoundTick()
	if(!rm_bound || HP <= 0 || GoingToDie)
		rm_bound_beasts -= src
		rm_bound = null
		if(HP <= 0 || GoingToDie) rm_bound_key = null
		return
	Target = null
	destination = null
	if(world.time - rm_fed_at < rm_tame_hunger) return
	rm_fed_at = world.time
	rm_bound_chains--
	var/Player/P = rm_bound
	if(rm_bound_chains > 0)
		P.RemasterNotice("[RemasterCombatName(src)] is hungry and strains at its chains: one snaps! [rm_bound_chains] left. Feed it raw meat.")
		view(src) << "[src] snaps a chain!"
		return
	rm_bound = null
	rm_bound_key = null
	rm_trust = 0
	rm_bound_beasts -= src
	ChangeOwnership(rm_wild_owner)   // wild again: its own wandering takes over (Mob Procs.dm WalkTo / Monster AI.dm RandomWalk)
	CanBeSlaved = 1
	rm_wild_owner = null
	P.RemasterNotice("[RemasterCombatName(src)] breaks its last chain and is free!")
	view(src) << "<b>[src] breaks free!</b>"
	var/mob/Monsters/near
	for(var/mob/Monsters/O in oview(6, src)) if(O.Owner == P && (!near || get_dist(src, O) < get_dist(src, near))) near = O
	if(near)
		Target = near
		destination = near

// Feed it: the nearest selected unit carrying raw meat walks up and feeds it.
Player/proc/RmFeedOrder(mob/Monsters/E)
	if(!istype(E) || E.rm_bound != src)
		RemasterNotice("Only a beast you have chained down can be fed.")
		return 0
	var/mob/Monsters/best
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0 && !M.Wagon && (locate(/obj/Items/Food/Meat) in M))
		if(!best || get_dist(M, E) < get_dist(best, E)) best = M
	if(!best)
		RemasterNotice("Select someone carrying raw meat to feed it.")
		return 0
	best.RemasterCancelOrders()
	best.remaster_order_status = "Feeding [RemasterCombatName(E)]"
	spawn(0) best.RmFeedWalk(E, src)
	return 1

mob/Monsters/proc/RmFeedWalk(mob/Monsters/E, Player/P)
	var/until = world.time + 400
	while(src && E && E.rm_bound == P && world.time < until && HP > 0)
		if(z == E.z && get_dist(src, E) <= RmBeastReach(E))
			destination = null
			P.RmFeedBeast(src, E)
			return
		var/turf/best
		for(var/turf/T in range(RmBeastReach(E), E))
			if(T.density || (locate(/obj/RmBeastFoot) in T)) continue
			if(!best || get_dist(src, T) < get_dist(src, best)) best = T
		destination = best
		sleep(5)
	// Never got to feed it (too far, boxed in, or it was tamed/freed meanwhile): say so and stand down.
	if(src && HP > 0 && E && E.rm_bound == P)
		destination = null
		remaster_order_status = null
		P.RemasterNotice("[RemasterBareName()] couldn't get to [RemasterCombatName(E)] to feed it.")

Player/proc/RmFeedBeast(mob/Monsters/C, mob/Monsters/E)
	var/obj/Items/Food/Meat/F = locate() in C
	if(!F || E.rm_bound != src)
		if(!F) RemasterNotice("[C.RemasterBareName()] has no raw meat left to feed it with.")
		return 0
	if(E.rm_trust > 0 && world.time - E.rm_trust_at < rm_tame_gap)
		RemasterNotice("[RemasterCombatName(E)] isn't hungry yet: feed it again in [round((rm_tame_gap - (world.time - E.rm_trust_at)) / 10) + 1] s.")
		return 0
	C.weight -= F.weight
	del F
	E.rm_trust++
	E.rm_fed_at = world.time
	E.rm_trust_at = world.time
	E.HP = min(E.MAXHP, E.HP + E.MAXHP * 0.1)
	C.remaster_order_status = "Fed [RemasterCombatName(E)]"
	if(E.rm_trust >= rm_tame_feeds)
		RmTameBeast(E)
		return 1
	RemasterNotice("[C.RemasterBareName()] feeds [RemasterCombatName(E)]: it eats from their hand ([E.rm_trust]/[rm_tame_feeds]).")
	return 1

Player/proc/RmTameBeast(mob/Monsters/E)
	for(var/i = 1, i <= E.rm_bound_chains, i++) new /obj/Items/RemasterTools/IronChains(E.loc)   // the chains come off
	rm_bound_beasts -= E
	E.rm_bound = null
	E.rm_bound_key = null
	E.rm_wild_owner = null
	E.rm_bound_chains = 0
	E.CanBeSlaved = 0         // the wild wandering stops (Monster AI.dm RandomWalk)
	E.HomeLoc = null
	if(E.rm_nest) E.rm_nest.mother = null
	E.rm_nest = null
	E.Target = null
	E.destination = null
	E.ChangeOwnership(src)
	E.name = "{[src]} [E.Race]"
	RemasterNotice("[E.RemasterBareName()] accepts you: it is yours now. The chains come off.")
	RemasterLog("Tamed [E.RemasterBareName()]", "good", E)
	view(E) << "<b>[E] has been tamed!</b>"

// --- What the unit card says (HUD.dm RemasterUnitData) -----------------------------------------
// A chained beast: its chains, how far it trusts you, how long until it is hungry. A young dragon: how
// long until it is full grown. Whoever carries an egg: that its mother is after them.
proc/RmTameStatus(mob/Monsters/M)
	if(M.rm_bound)
		return "Chained down: [M.rm_bound_chains] chain[M.rm_bound_chains == 1 ? "" : "s"] left, trust [M.rm_trust]/[rm_tame_feeds], hungry in [RmTimeText((rm_tame_hunger - (world.time - M.rm_fed_at)) / 10)]"
	if(M.Race == "Dragon" && M.Age < 50 && istype(M.Owner, /Player))
		return "full grown in about [RmTimeText(RmGrowPasses(M) * 450)]"
	return null

proc/RmTameWarnings(mob/Monsters/M)
	. = list()
	if(M.rm_bound && rm_tame_hunger - (world.time - M.rm_fed_at) < 300) . += "Hungry: feed it raw meat or a chain snaps"
	for(var/obj/Items/RmBeastEgg/E in M)
		var/mob/Monsters/Mo = E.mother
		if(Mo && Mo.HP > 0 && !Mo.GoingToDie && !istype(Mo.Owner, /Player)) . += "Carrying [E.name]: its mother hunts it"
		break

// The world's ageing passes (World.dm Aging(): every 4500 ticks, a year; two while young) until a
// dragon is 50, full grown (Beasts.dm RmBeastSize).
proc/RmGrowPasses(mob/Monsters/M)
	var/a = max(0, M.Age)
	. = 0
	while(a < 50)
		a++
		if(a <= 5) a++
		.++

// "45 s", "2 min 30 s", "5 h 50 min".
proc/RmTimeText(sec)
	sec = max(0, round(sec))
	if(sec < 60) return "[sec] s"
	if(sec < 3600) return "[round(sec / 60)] min[sec % 60 ? " [sec % 60] s" : ""]"
	var/m = round((sec % 3600) / 60)
	return "[round(sec / 3600)] h[m ? " [m] min" : ""]"

// The 3D view (View3D.dm "egg"): an egg in its carrier's arms, its colour.
proc/RmCarriedEgg(mob/M)
	var/obj/Items/RmBeastEgg/E = locate() in M
	return E ? (E.kind == "spider" ? "spider" : E.variant) : null
