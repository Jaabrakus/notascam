// Captives (Remastered). The user's rule (2026-10-23): a captive never joins by itself. It has to be tied
// down with a rope, then won over or enslaved, and while it is roped it keeps trying to break free.
//  - Rope. Plant rope (1 wood: log fibre, Carpentry), leather rope (1 skin) and silk rope (1 spider silk,
//    Leatherworks); Iron Chains (two iron ingots, Forge) bind a person too. Each has a strength from its
//    material, then the maker's skill sets its quality (Poor .. Legendary), as gear quality is set.
//  - Taking a captive (Capture.dm RemasterCapture) ties them with a rope the captor carries, one carried by
//    your people beside them, or one fetched from a stockpile or the ground nearby while the others hold them
//    down. Bound, they can't walk on their own or fight: they are led behind their captor (dragged, lying, while they
//    are out cold), or tied to the spot (beside a post or a wall they hold better). Out cold, nobody can win them over. Selected, a click on the ground has one of yours take them there.
//  - Win them over: one of yours sits with them, talks and shares food (the talker's Intelligence and level, the
//    same race, food when they are hungry). Loyalty rises; at full loyalty they join your house.
//  - Enslave: the rope is cut down to a hobble. A slave works (jobs and work orders, a bit slower) but never fights
//    or defends, isn't of your house and can't be heir. Armed by you, a loyal slave (60+) fights for you; a
//    resentful one (under 40) may turn on you. Winning a slave over frees them into your house.
//  - Breaking free: about every 30 s a bound captive tries its bonds: its strength and wits against the rope,
//    your people near it (left alone it tries harder), its wounds and hunger, and how far it has been won over.
//    Loose, it runs home or fights. Slaves don't, but many slaves together with few guards may rise up (rare):
//    a rising unties the bound captives near it (they join), takes up the weapons in its bags, falls on your
//    people within 6 tiles for a while (the better fighters longer, 8-30 s), then runs home together (user, 2026-10-23).
//  - Lines (user, 2026-10-23): a bound captive can be roped behind another, one after the other; a leader holds two
//    lines side by side at most (a third captive goes behind the shorter line). One that leaves a line (breaks
//    free, joins, is released, enslaved or caged) is closed up behind: the next follows the one in front.
//  - Tie to a tree or a post: one of yours leads them there and ties them to it (they hold better).
//  - Cages (the game's own: wooden, bone, metal, gold): a bound captive is put into an empty cage on the ground (one
//    carried by your people is set down first) and taken out again. Caged, they can't break free; a cage with someone
//    in it can't be picked up.
//  - Saved with the army (every var here that isn't tmp): bound or slave, the rope, loyalty, the spot they're
//    tied to, in a cage, and whose they were. After a load, a captive that was being led is tied where it stands, and
//    one that was caged is put back into the cage on its spot.

#define RM_CAP_ROLL 300          // a bound captive tries its bonds about every 30 s
#define RM_CAP_TALK 30           // winning over: loyalty every 3 s of talk
#define RM_CAP_FEED_GAP 600      // the talker shares food at most once a minute
#define RM_CAP_SLAVE_EVERY 600   // a slave's loyalty drifts, and an armed one may turn: every minute
#define RM_CAP_REVOLT 2400       // slaves together may rise: looked at every 4 min
#define RM_CAP_LEASH 10          // a leader further off than this leaves them tied
#define RM_CAP_STRIKE 80         // a rising's strike: 8 s, and 0.25 s more per level of Attack and Strength (30 s at most)

var/list/rm_captives = list()
var/rm_cap_relink_at = 0
var/rm_cap_revolt_at = 0
// kind -> label, strength (before quality)
var/list/rm_rope_kinds = list("plant"=list("Plant rope", 20), "leather"=list("Leather rope", 40), "silk"=list("Silk rope", 60), "chains"=list("Iron chains", 95))
var/list/rm_rope_quality = list("Poor Quality"=0.8, "Average Quality"=0.9, "Quality"=1, "Impressive Quality"=1.1,
	"Grand Quality"=1.2, "Masterful Quality"=1.3, "Epic Quality"=1.4, "Legendary Quality"=1.5)

mob/Monsters/var
	rm_cap_state                // "bound" or "slave"
	rm_cap_rope                 // what holds them: "plant", "leather", "silk" or "chains"
	rm_cap_rope_power = 0       // its strength, 0-100
	rm_cap_rope_name            // the item's name ("Silk Rope - Grand Quality")
	rm_cap_rope_rank            // its quality, given back with it
	rm_cap_loyalty = 0          // 0-100: won over at 100
	list/rm_cap_tied            // list(x, y, z): tied to this spot (null: led)
	rm_cap_post = 0             // tied beside a post or a wall
	rm_cap_from                 // whose they were: an NPC side ("{NPC Goblin}") or a player's key
	rm_cap_from_player = 0
	rm_cap_name                 // their name before
	list/rm_cap_home            // list(x, y, z): where they came from, when that is known
	rm_cap_cage = 0             // held in a cage (the mob is inside the cage object)
mob/Monsters/var/tmp
	rm_cap_roll_at = 0
	rm_cap_said_at = -1000
	rm_cap_step_at = 0
	rm_cap_leading = 0          // a step on the rope (Move lets it through)
	rm_cap_talking = 0          // this unit is winning someone over (its job waits)
	rm_cap_fed_at = -1000
	rm_cap_slave_at = 0
	rm_cap_strike_until = 0     // a rising: fights until then, then runs
	list/rm_cap_flee_home       // where a rising one runs to (its home, when known)
	mob/Monsters/rm_cap_talker  // who is winning this captive over
	mob/Monsters/rm_cap_fetcher // who is fetching a rope for them

// --- Rope ------------------------------------------------------------------------------------------
obj/Items/RemasterRope
	// its values: art/items/catalogue.json row remasterrope (export_items.py writes ItemData.dm)
	var/rm_rope = "leather"
	var/rm_power = 40
	PlantRope
		// its values: art/items/catalogue.json row remasterrope.plantrope (export_items.py writes ItemData.dm)
	LeatherRope
		// its values: art/items/catalogue.json row remasterrope.leatherrope (export_items.py writes ItemData.dm)
	SilkRope
		// its values: art/items/catalogue.json row remasterrope.silkrope (export_items.py writes ItemData.dm)

obj/Items/RemasterRope/proc/RmSetQuality(rank)
	CraftRank = rank
	rm_power = min(100, round(initial(rm_power) * (rm_rope_quality[rank] || 1)))
	name = "[initial(name)] - [rank]"
	desc = "[initial(desc)] Strength [rm_power]."

// The rope on a captive's 64 px body in the 3D view (View3D.dm Remaster3DLayers): Rope64/<sheet>.dmi, from
// art/enhance/rope64.py, fitted to each pose ("<kind>|<pose>"; a slave's hobble "hobble-<kind>|<pose>"). It is part of
// the unit's picture, so it stays on whatever the body does, lying knocked out included.
proc/RmRopeLayers(mob/Monsters/M, body64, pose)
	if(!body64 || !M.rm_cap_state) return list()
	if(M.rm_cap_state == "bound" && !M.rm_cap_rope) return list()   // caged: the rope is off them
	var/sheet = RmGearSheet(M)   // Gear.dm
	if(sheet in rm_gear_sheet_alias) sheet = rm_gear_sheet_alias[sheet]
	if(!sheet) return list()
	var/path = "Icons/Remastered/Rope64/[sheet].dmi"
	var/list/S = RmGear64States(path)
	if(!length(S)) return list()
	var/kind = M.rm_cap_rope || "leather"
	var/pre = M.rm_cap_state == "slave" ? "hobble-" : ""
	var/st = "[pre][kind]|[(pose in list("", "Normal")) ? "" : pose]"
	if(!(st in S)) st = "[pre][kind]|"
	return (st in S) ? list(list(file(path), st)) : list()

// How hard this item is to break out of (0: it isn't a rope).
proc/RmRopePower(obj/Items/I)
	if(istype(I, /obj/Items/RemasterTools/IronChains)) return rm_rope_kinds["chains"][2]
	if(istype(I, /obj/Items/RemasterRope)) return I:rm_power
	return 0

proc/RmRopeWord(power)
	if(power >= 85) return "iron-hard"
	if(power >= 60) return "very strong"
	if(power >= 40) return "strong"
	if(power >= 25) return "fair"
	return "flimsy"

proc/RmCapNoRopeText(mob/Monsters/T)
	return "[T ? "[T.RemasterBareName()] is down, but you" : "You"] need a rope to tie them: plant rope at a Carpentry (1 wood), leather or silk rope at a Leatherworks (1 skin or 1 spider silk), or Iron Chains from a Forge."

// Made at the Carpentry (plant) and the Leatherworks (leather, silk): their menus (CraftingStations.dm).
mob/Monsters/proc/RemasterCraftRope(mob/WorkShops/W, Player/P, kind)
	if(!(src in range(1, W)) || !RemasterManualHandoff(P)) return
	var/list/D = list("plant"=list(/obj/Items/RemasterRope/PlantRope, /obj/Items/woods/wood, "wood", "WoodCraftingSkill", "Wood crafting"),
		"leather"=list(/obj/Items/RemasterRope/LeatherRope, /obj/Items/Skin, "skin", "LeatherCraftingSkill", "Leather crafting"),
		"silk"=list(/obj/Items/RemasterRope/SilkRope, /obj/Items/Silks/SpiderSilk, "spider silk", "LeatherCraftingSkill", "Leather crafting"))[kind]
	if(!D) return
	var/obj/Items/X
	for(var/obj/Items/Y in src) if(istype(Y, D[2]) && Y.suffix != "(Equipped)")
		X = Y
		break
	if(!X)
		P << "[src] needs [D[3] == "wood" ? "a log of wood (its fibre is twisted into rope)" : "a piece of [D[3]]"] to make [lowertext(rm_rope_kinds[kind][1])]."
		return
	weight -= X.weight
	del X
	var/skill = vars[D[4]]
	if(!prob(RemasterCraftOdds(skill)))
		P << "The attempt failed and the [D[3]] is used up. [D[5]] rises with every try."
		vars[D[4]] += 1
		return
	var/path = D[1]
	var/obj/Items/RemasterRope/R = new path(loc)
	R.RmSetQuality(RmGearRank(skill, list()))   // Gear.dm: the skill sets the quality
	vars[D[4]] += 1
	P << "[src] makes [R.name] (strength [R.rm_power])."

// --- Binding ---------------------------------------------------------------------------------------
// The strongest rope (or chains) the captor carries, or one of yours beside the captive, or null.
proc/RmCapRopeAtHand(Player/P, mob/Monsters/C, mob/Monsters/T)
	var/obj/Items/best
	for(var/obj/Items/I in C) if(I.suffix != "(Equipped)" && RmRopePower(I) && (!best || RmRopePower(I) > RmRopePower(best))) best = I
	if(best || !T) return best
	for(var/mob/Monsters/O in range(2, T)) if(O != C && O.Owner == P && !O.rm_cap_state)
		for(var/obj/Items/I in O) if(I.suffix != "(Equipped)" && RmRopePower(I) && (!best || RmRopePower(I) > RmRopePower(best))) best = I
	return best

// A rope lying in a stockpile or a zone, or loose on the ground near C: the nearest, or null.
Player/proc/RmCapRopeLying(mob/Monsters/C)
	var/obj/Items/best
	for(var/turf/S in RemasterStores()) if(S.z == C.z && get_dist(S, C) <= 40)
		for(var/obj/Items/I in range(1, S)) if(RmRopePower(I) && RemasterMayCollect(I) && (!best || get_dist(C, I) < get_dist(C, best))) best = I
	for(var/obj/Items/I in range(20, C)) if(RmRopePower(I) && RemasterMayCollect(I) && (!best || get_dist(C, I) < get_dist(C, best))) best = I
	return best

// "carried", "stockpile" (or lying near) or null: what the Capture button tells the player.
Player/proc/RmCapRopeSource(mob/Monsters/C, mob/Monsters/T)
	if(RmCapRopeAtHand(src, C, T)) return "carried"
	if(RmCapRopeLying(C)) return "stockpile"
	return null

// C (one of P's) ties T, who is down, with rope R. 1 when done.
mob/Monsters/proc/RmCapBind(Player/P, mob/Monsters/C, obj/Items/R)
	var/Player/was = istype(Owner, /Player) ? Owner : null
	rm_cap_from = was ? was.key : (istext(Owner) ? Owner : null)
	rm_cap_from_player = was ? 1 : 0
	rm_cap_name = name
	var/turf/H = isturf(HomeLoc) ? HomeLoc : null
	rm_cap_home = H ? list(H.x, H.y, H.z) : null
	RmCapRopeOn(R)
	// tied hand to body and disarmed: the captor takes their weapons, or they are left on the ground (never in their bag)
	var/took = RmCapDisarm(C)
	for(var/obj/Items/Equipment/Armour/Shield/E in src) if(E.suffix == "(Equipped)") UnEquipItem(E)
	rm_cap_state = "bound"
	rm_cap_loyalty = 0
	rm_cap_tied = null
	rm_cap_post = 0
	rm_cap_fetcher = null
	remaster_captive_lead = RmCapLeadSpot(C)   // the captor's hand, or the end of the shorter of its two lines
	remaster_root_until = 0
	remaster_slow_until = 0
	Target = null
	destination = null
	HomeLoc = null
	PatrolPoint1 = null
	PatrolPoint2 = null
	remaster_attack = null
	ChangeOwnership(P)
	name = RemasterBareName()             // no owner tag while held (the roster); rm_cap_name has it back if they get away
	remaster_order_status = "Bound captive"
	if(!remaster_uid) remaster_uid = RemasterNewUID()
	rm_cap_roll_at = world.time + RM_CAP_ROLL + rand(-50, 50)
	rm_captives |= src
	if(was)
		was.RemasterNotice("[RemasterBareName()] was captured by [P.RemasterHouse()]'s people!")
		RemasterWarScore(P.key, was.key, 1)
	P.RemasterNotice("[C.RemasterBareName()] ties [RemasterBareName()] with the [lowertext(rm_cap_rope_name)][took]. They won't join on their own: win them over or enslave them (their card, Interact tab). Bound captives try to break free; keep someone near.")
	P.RemasterLog("Captured [RemasterBareName()] ([lowertext(rm_cap_rope_name)])", "fight", src)
	view(src) << "<b>[RemasterBareName()] is tied up by [C.RemasterBareName()]!</b>"
	return 1

// Their weapons out of their bag: carried off by C (the one who tied them) when C can carry them, else on the ground
// beside them (laid down, not dropped: a dropped item fades after a while). Returns words for the notice.
mob/Monsters/proc/RmCapDisarm(mob/Monsters/C)
	var/list/took = list()
	var/left = 0
	for(var/obj/Items/Equipment/Weapon/W in src)
		if(W.suffix == "(Equipped)") UnEquipItem(W)
		weight -= W.weight
		W.suffix = null
		W.loc = loc
		if(C && C.PickUpItem(W, 0, 2)) took += lowertext("[W.name]")
		else left++
	var/obj/Items/K = rm_ko_weapon   // let go of when knocked out (Gear3D.dm RmKoDrop): taken up the same, if it lies where it fell beside them
	if(K && !Rm3DGone(K) && isturf(K.loc) && "[K.x],[K.y],[K.z]" == rm_ko_weapon_at && get_dist(src, K) <= 1)
		rm_ko_weapon = null
		rm_ko_weapon_at = ""
		if(C && C.PickUpItem(K, 0, 2)) took += lowertext("[K.name]")
		else left++
	if(!length(took) && !left) return ""
	if(!length(took)) return " (their weapon[left == 1 ? " lies" : "s lie"] on the ground beside them)"
	return " and takes their [jointext(took, ", ")][left ? " (more lies on the ground)" : ""]"

// No rope at hand: C fetches the nearest one lying in a stockpile or near, while the others hold T down.
mob/Monsters/proc/RmCapFetchRope(Player/P, mob/Monsters/T, obj/Items/R)
	T.rm_cap_fetcher = src
	RemasterCancelOrders()
	remaster_order_status = "Fetching a rope for [T.RemasterBareName()]"
	var/until = world.time + 900
	while(src && T && R && HP > 0 && !GoingToDie && T.HP > 0 && !T.rm_cap_state && T.rm_cap_fetcher == src && world.time < until)
		if(remaster_active || remaster_attack || length(remaster_orders)) break   // sent off to do something else
		if(R.loc != src)
			if(!isturf(R.loc) || !P.RemasterMayCollect(R)) break
			if(z == R.z && get_dist(src, R) <= 1)
				destination = null
				if(!PickUpItem(R)) break
				R.Owner = P
				remaster_order_status = "Bringing a rope to [T.RemasterBareName()]"
			else destination = R.loc
		else
			// the others beside them hold them down until the rope comes (at most 90 s from the fetch)
			if(T.RemasterKnockedOut() && T.remaster_ko_until - world.time < 20 && world.time + 50 <= until)
				for(var/mob/Monsters/O in range(1, T)) if(O != src && O.Owner == P && !O.rm_cap_state && O.HP > 0)
					T.remaster_ko_until = world.time + 50
					spawn(51) if(T) T.RemasterWakeUp()   // Subdue.dm: wakes only once the time is up
					break
			if(z == T.z && get_dist(src, T) <= 1)
				destination = null
				if(T.rm_cap_fetcher == src) T.rm_cap_fetcher = null
				if(!P.RemasterCapture("[RemasterUIRef(src)]|\ref[T]")) remaster_order_status = "Idle"
				return
			destination = RmCapBeside(T, src)
		sleep(5)
	if(T && T.rm_cap_fetcher == src)
		T.rm_cap_fetcher = null
		if(src && R && R.loc == src && !T.rm_cap_state) P.RemasterNotice("[RemasterBareName()] came back with the rope too late: [T.RemasterBareName()] is no longer down. Knock them out again (Capture).")
	if(src && findtext("[remaster_order_status]", "rope")) remaster_order_status = "Idle"

// The rope R goes on them (taken from whoever carried it).
mob/Monsters/proc/RmCapRopeOn(obj/Items/R)
	rm_cap_rope = istype(R, /obj/Items/RemasterTools/IronChains) ? "chains" : R:rm_rope
	rm_cap_rope_power = RmRopePower(R)
	rm_cap_rope_name = "[R.name]"
	rm_cap_rope_rank = R.CraftRank
	var/mob/holder = R.loc
	if(ismob(holder)) holder.weight -= R.weight
	del R

// The rope comes off (won over, released): it lies at their feet for the taking, as good as it was.
mob/Monsters/proc/RmCapRopeOff()
	if(isturf(loc)) RmCapRopeItem(loc)

// Their rope as an item again, at `where` (null when they wear none); the rope is off them after.
mob/Monsters/proc/RmCapRopeItem(atom/where)
	var/obj/Items/R
	if(rm_cap_rope == "chains") R = new /obj/Items/RemasterTools/IronChains(where)
	else
		var/path = list("plant"=/obj/Items/RemasterRope/PlantRope, "leather"=/obj/Items/RemasterRope/LeatherRope, "silk"=/obj/Items/RemasterRope/SilkRope)[rm_cap_rope]
		if(path)
			var/obj/Items/RemasterRope/RR = new path(where)
			if(rm_cap_rope_rank) RR.RmSetQuality(rm_cap_rope_rank)
			else RR.rm_power = rm_cap_rope_power
			R = RR
	rm_cap_rope = null
	rm_cap_rope_power = 0
	rm_cap_rope_name = null
	rm_cap_rope_rank = null
	return R

mob/Monsters/proc/RmCapClear()
	if(rm_cap_cage) RmCapUncage()
	RmCapLeaveLine()
	rm_cap_state = null
	rm_cap_rope = null
	rm_cap_rope_power = 0
	rm_cap_rope_name = null
	rm_cap_rope_rank = null
	rm_cap_loyalty = 0
	rm_cap_tied = null
	rm_cap_post = 0
	rm_cap_talker = null
	rm_cap_fetcher = null
	remaster_captive_lead = null
	rm_captives -= src

// Their name without the owner tag, and without "Slave".
mob/Monsters/proc/RmCapBareName()
	var/n = RemasterBareName()
	if(findtext(n, "Slave ") == 1) n = copytext(n, 7)
	return n

// A unit of an NPC kind (a captive, a slave, one won over) is handed its kind's gear by New() (Mobs.dm), and New()
// runs again when the army is read back from a save, before the saved bag is restored: every reload added another
// spear (tests/save_roundtrip_test.dm with captives, 2026-10-23). The saved bag is the real one.
mob/Monsters/Read(savefile/F)
	var/list/had = list()
	if(findtext("[initial(Owner)]", "{NPC") == 1) for(var/obj/Items/I in src) had += I
	. = ..()
	for(var/obj/Items/I in had) del I

// mob/Monsters/Move: this file's part is step RmChainMove_Captives in Code/Remastered/Chains/Move.dm

// A bound captive never strikes; a slave only when armed and loyal (RmCapMayFight).
mob/Monsters/RemasterStrike(mob/M, kind_hint)
	if(rm_cap_state && !RmCapMayFight()) return
	return ..()

mob/Monsters/Attack(mob/Monsters/M)
	if(rm_cap_state && !RmCapMayFight()) return
	return ..()

// Bound, caged or enslaved, they never take up gear lying by them on their own: an NPC's wander loop takes one last
// look round for gear (Monster AI.dm FindGear) after it is tied, and re-armed it with the spear just taken off it
// (user, 2026-10-23: "cage unit has spear"). A rising frees them first (RmCapFree), so risers do fetch weapons.
mob/Monsters/FindGear()
	if(rm_cap_state) return
	return ..()

// Shut in a cage they can still be selected with a click (their card: Take out, Win over...); the original Select
// (Mobs.dm) refuses any unit inside an object.
mob/Monsters/Select(mob/USER = Owner)
	if(rm_cap_cage && isobj(loc) && ismob(USER) && !Egg && !InHole && !Sleeping)
		if(!USER.Selected.Find(src))
			USER.Selected.Add(src)
			if(USER.client) USER.client.images += Star
		return
	return ..()

mob/Monsters/proc/RmCapArmed()
	for(var/obj/Items/Equipment/Weapon/W in src) if(W.suffix == "(Equipped)")
		return (RemasterWeaponClass(src) in list("sword", "mace", "spear", "dagger", "bow"))   // axes and picks are work tools
	return 0

mob/Monsters/proc/RmCapMayFight()
	return rm_cap_state == "slave" && rm_cap_loyalty >= 60 && RmCapArmed()

// A post or a wall beside them: they're tied to it.
mob/Monsters/proc/RmCapPostNear()
	return RmCapPostAt() ? 1 : 0

// What they are tied to: a stake driven in beside them (or under them), a tree, a pillar, furniture or any solid
// thing, a workshop, a wall or rock; null when none.
mob/Monsters/proc/RmCapPostAt()
	for(var/obj/Items/RemasterStake/K in range(1, src)) if(RmStakePlanted(K)) return K
	for(var/turf/T in orange(1, src)) if(T.vars["Tree"]) return T
	for(var/obj/O in orange(1, src)) if(isturf(O.loc) && RmCapTieable(O)) return O
	for(var/mob/WorkShops/W in orange(1, src)) return W
	for(var/turf/T in orange(1, src)) if(T.density && RmCapTieable(T)) return T
	return null

// Anything a captive can be tied to (user, 2026-10-23: "we can tie it to anything really"): a tree, a wall or rock,
// a pillar, furniture, a workshop, a stake in the ground, any solid object.
proc/RmCapTieable(atom/A)
	if(isturf(A)) return A.vars["Tree"] || (A.density && (A:IsWall || RemasterIsMountain(A)))   // (not water)
	if(istype(A, /mob/WorkShops)) return 1
	if(istype(A, /obj/Items/RemasterStake)) return RmStakePlanted(A)
	if(istype(A, /obj/Items/Traps/Cages)) return 0
	if(isobj(A)) return A.density || istype(A, /obj/Items/Furniture)
	return 0

// The tied-to thing's name for the card and notices: "stake", "tree", "wall", a workshop's or an object's name.
proc/RmCapTieName(atom/A)
	if(!A) return null
	if(istype(A, /obj/Items/RemasterStake)) return "stake"
	if(isturf(A)) return A.vars["Tree"] ? "tree" : (RemasterIsMountain(A) ? "rock" : "wall")
	if(istype(A, /mob/WorkShops)) return lowertext(RemasterStationName(A))
	var/n = "[A.name]"
	if(findtext(n, "}")) n = trimtext(copytext(n, findtext(n, "}") + 1))
	return lowertext(n)

// For the card: what they are tied to ("stake", "tree", "wall", "leatherworks"...), null when not tied to anything.
mob/Monsters/proc/RmCapPostKind()
	if(!rm_cap_tied || !rm_cap_post) return null
	return RmCapTieName(RmCapPostAt()) || "post"

// Tied to a stake, a tree or a pillar: where the rope runs to in the 3D view (x, y), else null.
mob/Monsters/proc/RmCapTieToSpot()
	if(rm_cap_state != "bound" || rm_cap_cage || !rm_cap_tied || !rm_cap_post || remaster_captive_lead) return null
	var/atom/A = RmCapPostAt()
	if(!A || (isturf(A) && !A.vars["Tree"])) return null   // (a wall: no rope drawn into it)
	return list(A.x, A.y)

mob/Monsters/proc/RmCapTieHere(Player/P, why)
	if(rm_cap_state != "bound") return
	remaster_captive_lead = null
	rm_cap_tied = list(x, y, z)
	rm_cap_post = RmCapPostNear()
	destination = null
	if(P && why) P.RemasterNotice("[RmCapBareName()] is tied up [rm_cap_post ? "to a post" : "where they stand"]: [why].")

// Every other tick: a bound captive follows its leader at its own pace; one left behind is tied there.
mob/Monsters/proc/RmCapLeadTick(Player/P)
	Target = null
	if(destination) destination = null
	var/mob/Monsters/L = remaster_captive_lead
	if(!L || !isturf(loc)) return
	if(L.HP <= 0 || L.GoingToDie || L.Owner != P || L.z != z || L.rm_cap_state == "slave" || !isturf(L.loc) || get_dist(src, L) > RM_CAP_LEASH)
		RmCapTieHere(P, L && L.HP > 0 && !L.GoingToDie && L.Owner == P ? "[L.RemasterBareName()] went too far off" : "nobody leads them")
		return
	if(get_dist(src, L) > 1 && world.time >= rm_cap_step_at)
		// out cold, they are dragged along on the rope, lying, at about half a walking pace (user, 2026-10-23)
		var/out = RmCapOutCold()
		RmCapStepToward(L)
		rm_cap_step_at = world.time + (out ? max(6, RemasterStepDelay() * 2) : max(2, RemasterStepDelay()))

// One step on the rope towards A: onto a free tile nearer A (straight, or a diagonal either side), never onto another
// unit or A's own tile, so captives in a line never stand on top of each other (user, 2026-10-23); none free: wait.
mob/Monsters/proc/RmCapStepToward(atom/A)
	var/turf/goal = RemasterGetTurf(A)
	if(!goal || goal.z != z) return 0
	var/d0 = get_dist(src, goal)
	var/dir0 = get_dir(src, goal)
	for(var/dd in list(dir0, turn(dir0, 45), turn(dir0, -45)))
		var/turf/T = get_step(src, dd)
		if(!T || T == goal || T.density || get_dist(T, goal) >= d0) continue
		var/taken = 0
		for(var/mob/Monsters/M in T) if(M != src && M.HP > 0)
			taken = 1
			break
		if(taken) continue
		rm_cap_leading = 1
		var/ok = Move(T, dd)
		rm_cap_leading = 0
		if(ok) return 1
	return 0

// A free tile beside T, the nearest to M (or T's own tile).
proc/RmCapBeside(atom/T, mob/M)
	var/turf/best
	for(var/turf/X in orange(1, T))
		if(X.density) continue
		var/blocked = 0
		for(var/atom/movable/O in X) if(O.density && O != M)
			blocked = 1
			break
		if(!blocked && (!best || get_dist(X, M) < get_dist(best, M))) best = X
	return best || RemasterGetTurf(T)

// Open ground beside A with nobody and no cage or stake on it, never A's own tile; 2 tiles off when every tile
// beside is taken; A's own tile last of all.
proc/RmCapFreeBeside(atom/A)
	var/turf/a = RemasterGetTurf(A)
	if(!a) return null
	for(var/r = 1, r <= 2, r++)
		for(var/turf/X in orange(r, a))
			if(get_dist(X, a) != r || X.density || X.vars["Tree"] || (locate(/mob) in X) || (locate(/obj/Items/Traps/Cages) in X) || (locate(/obj/Items/RemasterStake) in X)) continue
			var/blocked = 0
			for(var/atom/movable/O in X) if(O.density)
				blocked = 1
				break
			if(!blocked) return X
	return a

// The nearest of P's free people (not a captive, a slave or an animal) within `range` of T, or null.
proc/RmCapNearestFree(Player/P, mob/Monsters/T, range = 15)
	var/mob/Monsters/best
	for(var/mob/Monsters/O in P.UnitList) if(O != T && O.Owner == P && !O.rm_cap_state && !O.Critter && !O.Wagon && O.HP > 0 && !O.GoingToDie && !O.Fainted && O.z == T.z && get_dist(O, T) <= range && isturf(O.loc))
		if(!best || get_dist(O, T) < get_dist(best, T)) best = O
	return best

// "Move them": L (their leader, or the nearest of yours) takes the rope and leads them to `goal`, and ties them there.
mob/Monsters/proc/RmCapEscort(mob/Monsters/T, turf/goal, Player/P)
	if(T.remaster_captive_lead && T.remaster_captive_lead != src)
		var/mob/Monsters/old = T.remaster_captive_lead
		if(old.remaster_order_status == "Leading [T.RmCapBareName()]") old.remaster_order_status = "Idle"
	RemasterCancelOrders()
	remaster_patrol = null
	remaster_order_status = "Leading [T.RmCapBareName()]"
	var/until = world.time + 1800
	while(src && T && T.rm_cap_state == "bound" && T.Owner == P && HP > 0 && !GoingToDie && world.time < until)
		if(remaster_active || remaster_attack || length(remaster_orders)) return   // given something else to do
		if(T.remaster_captive_lead != src)
			if(z == T.z && get_dist(src, T) <= 1)
				T.remaster_captive_lead = src
				T.rm_cap_tied = null
				T.rm_cap_post = 0
			else
				destination = RmCapBeside(T, src)
				sleep(5)
				continue
		if(get_dist(T, goal) <= 1 && T.z == goal.z)
			destination = null
			T.RmCapTieHere(P)
			P.RemasterNotice("[RemasterBareName()] ties [T.RmCapBareName()] [T.rm_cap_post ? "to a post" : "up"] there.")
			remaster_order_status = "Idle"
			return
		destination = goal
		sleep(5)
	if(src && remaster_order_status == "Leading [T ? T.RmCapBareName() : ""]") remaster_order_status = "Idle"

// A bound captive in the selection can't take an order. A click on the ground has one of yours lead them there.
Player/RemasterOrder(atom/A, queued = 0, kind = null)
	var/list/held = list()
	for(var/mob/Monsters/M in Selected) if(M.rm_cap_state == "bound" && M.Owner == src) held += M
	if(!length(held)) return ..()
	var/k = kind || RemasterClickKind(A)
	Selected -= held
	. = length(Selected) ? ..() : 0
	Selected += held
	. = . || 0
	if(k == "Move" && A && A.z)
		var/turf/goal = isturf(A) ? A : A.loc
		for(var/mob/Monsters/T in held)
			if(T.rm_cap_cage)
				RemasterNotice("[T.RmCapBareName()] is in a cage: take them out first (their card, Interact tab).")
				continue
			var/mob/Monsters/L = T.remaster_captive_lead
			if(!L || L.HP <= 0 || L.Owner != src) L = RmCapNearestFree(src, T)
			if(!L)
				RemasterNotice("[T.RmCapBareName()] is bound: none of your people are near enough to lead them.")
				continue
			spawn(0) L.RmCapEscort(T, goal, src)
			RemasterNotice("[L.RemasterBareName()] leads [T.RmCapBareName()] there on the rope.")
			.++
	else if(!.) RemasterNotice("[length(held) == 1 ? "[held[1]:RmCapBareName()] is" : "They are"] bound: they can't do that. Click the ground to have them led there.")

// Bound captives and unarmed (or untrusted) slaves don't attack.
Player/RemasterAttackOrder(atom/A)
	var/list/held = list()
	for(var/mob/Monsters/M in Selected) if(M.rm_cap_state && M.Owner == src && !M.RmCapMayFight()) held += M
	if(!length(held)) return ..()
	Selected -= held
	. = length(Selected) ? ..() : 0
	Selected += held
	if(!.) RemasterNotice(held[1]:rm_cap_state == "slave" ? "Slaves don't fight. Armed, a loyal one (loyalty 60) would." : "Bound captives can't fight.")

Player/RemasterCaptureOrder(mob/Monsters/E)
	var/list/held = list()
	for(var/mob/Monsters/M in Selected) if(M.rm_cap_state && M.Owner == src) held += M
	if(!length(held)) return ..()
	Selected -= held
	. = length(Selected) ? ..() : 0
	Selected += held
	if(!.) RemasterNotice("Captives and slaves can't take anyone captive.")

// A bound captive or a slave isn't of your house, and can't be heir.
mob/Monsters/RemasterLineageEnsure(Player/P)
	if(!rm_cap_state) return ..()
	if(!remaster_uid) remaster_uid = RemasterNewUID()
	if(!remaster_generation) remaster_generation = 1

mob/Monsters/RemasterCanInherit(Player/P)
	if(rm_cap_state) return 0
	return ..()

// Slaves work a bit slower (a fifth of their work ticks skipped); a unit winning someone over leaves its job; a bound
// captive does no work at all.
mob/Monsters/RemasterMoodSkipsWork()
	if(rm_cap_talking || rm_cap_state == "bound") return 1
	if(rm_cap_state == "slave" && prob(20)) return 1
	return ..()

// A bound captive takes no job (enslave them first), and doesn't go off to eat or sleep: it is fed by whoever wins it over.
mob/Monsters/RemasterAssignJob(VALUE)
	if(rm_cap_state == "bound" && VALUE != "manual")
		if(istype(Owner, /Player)) Owner:RemasterNotice("[RmCapBareName()] is bound: enslave them to put them to work, or win them over.")
		return
	return ..()

mob/Monsters/RemasterCareStep(Player/P, list/claimed)
	if(rm_cap_state == "bound") return
	return ..()

// A bound captive isn't an idle worker (the Village page's idle count, the next-idle key).
Player/RemasterIdleEligible(mob/Monsters/M, listed)
	if(M && M.rm_cap_state == "bound") return 0
	return ..()

// mob/Monsters/RemasterStepDelay: this file's part is step RmChainStepDelay_Captives in Code/Remastered/Chains/StepDelay.dm

// (its pace in a group, RemasterOwnStep, is hobbled in CaptivesPace.dm: an override must come after Formations.dm)

// --- Winning them over ----------------------------------------------------------------------------
// The best talker of P's people within 15 tiles (Intelligence and level, the same race), or null.
proc/RmCapBestTalker(Player/P, mob/Monsters/T)
	var/mob/Monsters/best
	var/best_s = -1#INF
	for(var/mob/Monsters/O in P.UnitList) if(O != T && O.Owner == P && !O.rm_cap_state && !O.Critter && !O.Wagon && O.HP > O.MAXHP * 0.3 && !O.GoingToDie && !O.Fainted && O.z == T.z && get_dist(O, T) <= 15 && isturf(O.loc))
		var/s = max(0, O.RmIntC()) * 3 + max(0, O.Level) + (O.Race == T.Race ? 10 : 0) - get_dist(O, T) * 0.5
		if(s > best_s)
			best_s = s
			best = O
	return best

// Loyalty from one 3 s talk with C.
mob/Monsters/proc/RmCapTalkGain(mob/Monsters/C)
	var/g = 0.8 + max(0, C.RmIntC()) * 0.12 + max(0, C.Level) * 0.04
	if(C.Race == Race) g *= 1.5
	if(MaxHunger && Hunger < MaxHunger * 0.3) g *= 0.5     // too hungry to listen
	if(HP < MAXHP * 0.5) g *= 0.75
	if(rm_cap_from_player) g *= 0.7                          // another realm's people hold to their own
	if(rm_cap_state == "slave") g *= 0.8                     // a slave has less reason to trust you
	return g / (1 + max(0, Level) * 0.02)

proc/RmCapFoodOf(mob/Monsters/C)
	for(var/obj/Items/Food/F in C) if(F.suffix != "(Equipped)" && F.FoodPower > 0) return F
	return null

// Out cold (knocked out, fainted, asleep): nobody can be talked round.
mob/Monsters/proc/RmCapOutCold()
	return RemasterKnockedOut() || Fainted || Sleeping

Player/proc/RmCapWinOver(mob/Monsters/T, mob/Monsters/C)
	if(!istype(T) || !T.rm_cap_state || T.Owner != src) return 0
	if(T.RmCapOutCold())
		RemasterNotice("[T.RmCapBareName()] is out cold: win them over once they come to.")
		return 0
	if(!C || C.Owner != src || C.rm_cap_state || C.Critter || C.HP <= 0 || C.z != T.z || get_dist(C, T) > 30) C = RmCapBestTalker(src, T)
	if(!C)
		RemasterNotice("None of your people are near enough to talk with [T.RmCapBareName()].")
		return 0
	var/mob/Monsters/old = T.rm_cap_talker
	if(old && old != C) old.rm_cap_talking = 0
	C.RemasterCancelOrders()
	if(C.remaster_defense) C.RemasterCancelDefense(0)
	C.RemasterCareInterrupt()
	C.remaster_patrol = null
	T.rm_cap_talker = C
	C.rm_cap_talking = 1
	C.remaster_order_status = "Winning over [T.RmCapBareName()]"
	RemasterNotice("[C.RemasterBareName()] goes to sit with [T.RmCapBareName()]: talk, and food when they're hungry (carry some). Loyalty [round(T.rm_cap_loyalty)]%; at 100 they join your house.")
	spawn(0) C.RmCapTalkWalk(T, src)
	return 1

mob/Monsters/proc/RmCapTalkWalk(mob/Monsters/T, Player/P)
	var/next = world.time + RM_CAP_TALK
	while(src && T && T.rm_cap_state && T.Owner == P && T.rm_cap_talker == src && HP > 0 && !GoingToDie && Owner == P)
		if(remaster_active || remaster_attack || length(remaster_orders) || remaster_defense) break   // given something else to do
		var/turf/at = RemasterGetTurf(T)   // a caged captive is talked to through the bars
		if(!at || z != at.z || get_dist(src, at) > 1)
			destination = RmCapBeside(at || T, src)
			next = max(next, world.time + 10)
			sleep(5)
			continue
		destination = null
		if(world.time >= next)
			next = world.time + RM_CAP_TALK
			T.RmCapTalk(src, P)
		sleep(5)
	rm_cap_talking = 0
	if(T && T.rm_cap_talker == src) T.rm_cap_talker = null
	if(src && findtext("[remaster_order_status]", "Winning over") == 1) remaster_order_status = "Idle"

var/list/rm_cap_talk_lines = list("We have food, and a place by the fire.", "No one here wants you hurt.", "Where are your own people now?",
	"You'd be one of us. A name, a bed, a share.", "Rest. Eat. Think on it.", "Your old masters left you behind.")
var/list/rm_cap_reply_lines = list("...", "Why should I trust you?", "Hm.", "Maybe.", "Leave me be.", "Is there more food?")

mob/Monsters/proc/RmCapTalk(mob/Monsters/C, Player/P)
	if(RmCapOutCold())   // knocked out again, fainted or asleep: the talker waits beside them
		C.remaster_order_status = "Waiting for [RmCapBareName()] to come to"
		return
	rm_cap_loyalty = min(100, rm_cap_loyalty + RmCapTalkGain(C))
	if(world.time - rm_cap_fed_at >= RM_CAP_FEED_GAP && MaxHunger && Hunger < MaxHunger * 0.7)
		var/obj/Items/Food/F = RmCapFoodOf(C)
		if(F)
			Hunger = min(MaxHunger, Hunger + max(10, F.FoodPower))
			C.weight -= F.weight
			del F
			rm_cap_fed_at = world.time
			rm_cap_loyalty = min(100, rm_cap_loyalty + 6)
			C.RemasterSay("Here. Eat.")
			P.RemasterNotice("[C.RemasterBareName()] shares food with [RmCapBareName()] (loyalty [round(rm_cap_loyalty)]%).")
	if(prob(20))
		if(prob(60)) C.RemasterSay(pick(rm_cap_talk_lines))
		else RemasterSay(rm_cap_loyalty > 60 ? pick("Maybe you're right.", "I could stay.", "Thank you.") : pick(rm_cap_reply_lines))
	C.remaster_order_status = "Winning over [RmCapBareName()] ([round(rm_cap_loyalty)]%)"
	if(rm_cap_loyalty >= 100) RemasterJoinHouse(P)   // Capture.dm

// --- Enslaving, releasing -----------------------------------------------------------------------------
Player/proc/RmCapEnslave(mob/Monsters/T)
	if(!istype(T) || T.Owner != src || T.rm_cap_state != "bound")
		RemasterNotice("Only a bound captive can be enslaved.")
		return 0
	var/bare = T.RmCapBareName()
	if(T.rm_cap_cage) T.RmCapUncage()
	T.RmCapLeaveLine()
	T.rm_cap_state = "slave"
	T.remaster_captive_lead = null
	T.rm_cap_tied = null
	T.rm_cap_post = 0
	T.rm_cap_slave_at = world.time + RM_CAP_SLAVE_EVERY
	T.name = "{[src]} Slave [bare]"
	T.remaster_order_status = "Slave: give them a job or an order"
	T.remaster_defense_mode = "off"          // never fights on its own (Defense.dm)
	T.remaster_nonlethal = 0
	T.remaster_job = "manual"
	T.RmCapDisarm(RmCapNearestFree(src, T, 2))   // anything they were handed: to the one beside them, or the ground
	RemasterNotice("[bare] is your slave now: give them a job (Village tab) or a work order. They work a bit slower in a hobble, never fight or defend, and aren't of your house. Armed, a resentful slave may turn on you; win them over to free them into your house.")
	RemasterLog("Enslaved [bare]", "problem", T)
	view(T) << "[bare] has been enslaved."
	return 1

Player/proc/RmCapRelease(mob/Monsters/T)
	if(!istype(T) || T.Owner != src || !T.rm_cap_state) return 0
	var/bare = T.RmCapBareName()
	T.RmCapRopeOff()
	T.RmCapFree(src, "release")
	RemasterNotice("You let [bare] go. The rope lies where they stood; they head home.")
	RemasterLog("Released [bare]", "info", T)
	return 1

// Loose: back to their own side (a player's, an NPC side's, or nobody's), then home, or a fight.
mob/Monsters/proc/RmCapFree(Player/P, how)
	var/bare = RmCapBareName()
	var/from = rm_cap_from
	var/from_player = rm_cap_from_player
	var/old_name = rm_cap_name
	var/list/home = rm_cap_home
	RmCapClear()
	rm_cap_from = null
	rm_cap_from_player = 0
	rm_cap_name = null
	rm_cap_home = null
	RemasterCancelOrders()
	remaster_job = "manual"
	var/Player/H
	if(from_player) for(var/Player/X in Players) if(X.key == from) H = X
	if(H)
		ChangeOwnership(H)
		name = "{[H]} [bare]"
	else
		ChangeOwnership(from_player ? null : from)
		CanBeSlaved = 1                       // their own wandering again (Monster AI.dm RandomWalk), as a beast freed from chains
		name = (old_name && !from_player) ? old_name : bare
	remaster_defense_mode = "assist"
	Target = null
	destination = null
	if(how == "release") return RmCapGoHome(P, home)
	if(how == "rising")
		rm_cap_flee_home = home
		return "rises"
	var/mob/Monsters/foe
	for(var/mob/Monsters/O in orange(how == "escape" ? 1 : 6, src)) if(O.Owner == P && O.HP > 0 && !O.rm_cap_state && (!foe || get_dist(O, src) < get_dist(foe, src))) foe = O
	if(foe && (how == "turn" || (HP > MAXHP * 0.5 && prob(50))))
		Target = foe
		destination = foe
		return "fights"
	RmCapGoHome(P, home)
	return "flees"

// Off towards home, or away from P's people.
mob/Monsters/proc/RmCapGoHome(Player/P, list/home)
	var/turf/T = (islist(home) && length(home) == 3) ? locate(home[1], home[2], home[3]) : null
	if(T && T.z == z && get_dist(T, src) > 10 && !T.density)
		destination = T
		HomeLoc = T   // an NPC's wander walks only to a mob or its HomeLoc (Monster AI.dm RandomWalk)
		return "flees"
	var/mob/Monsters/near
	if(P) for(var/mob/Monsters/O in P.UnitList) if(O.z == z && O.HP > 0 && (!near || get_dist(O, src) < get_dist(near, src))) near = O
	var/dx = near ? x - near.x : rand(-1, 1)
	var/dy = near ? y - near.y : rand(-1, 1)
	var/d = max(1, sqrt(dx * dx + dy * dy))
	for(var/r = 20, r >= 6, r -= 4)
		var/turf/G = locate(clamp(round(x + dx / d * r), 2, world.maxx - 1), clamp(round(y + dy / d * r), 2, world.maxy - 1), z)
		if(G && !G.density)
			destination = G
			HomeLoc = G   // see above: without it a freed NPC stood where it broke loose
			break
	return "flees"

// --- Breaking free ------------------------------------------------------------------------------------
// The odds (percent) that a bound captive breaks free on its next try; `why` gets the reasons, for the card.
mob/Monsters/proc/RmCapEscapeOdds(list/why)
	if(rm_cap_state != "bound" || HP <= 0) return 0
	if(rm_cap_cage)
		if(why) why += "in a cage: it holds them"
		return 0
	if(Fainted || Sleeping || Stunned || RemasterKnockedOut())
		if(why) why += "out cold: can't struggle"
		return 0
	var/s = 18 + max(0, RmStr()) * 0.3 + max(0, RmAgi()) * 0.15 + max(0, RmIntC()) * 0.8 + max(0, Level) * 0.3
	s -= rm_cap_rope_power * 0.4
	if(why) why += "[rm_cap_rope_name ? lowertext(rm_cap_rope_name) : "the rope"]: [RmRopeWord(rm_cap_rope_power)]"
	var/close = 0
	var/near = 0
	var/far = 0
	for(var/mob/Monsters/O in range(8, src)) if(O != src && O.Owner == Owner && !O.rm_cap_state && !O.Critter && O.HP > 0 && !O.Fainted && !O.Sleeping)
		var/d = get_dist(src, O)
		if(d <= 2) close++
		else if(d <= 5) near++
		else far++
	s -= min(3, close) * 7 + min(3, near) * 3
	if(why && (close || near)) why += "[close + near] of yours watching"
	if(!close && !near && !far)
		s += 10
		if(why) why += "left alone"
	if(MAXHP && HP < MAXHP * 0.25)
		s -= 12
		if(why) why += "badly hurt"
	else if(MAXHP && HP < MAXHP * 0.5)
		s -= 6
		if(why) why += "hurt"
	if(MaxHunger && Hunger < MaxHunger * 0.2)
		s -= 5
		if(why) why += "weak with hunger"
	if(rm_cap_loyalty >= 5)
		s -= rm_cap_loyalty * 0.25
		if(why) why += "half won over ([round(rm_cap_loyalty)]%)"
	if(rm_cap_tied && rm_cap_post)
		s -= 6
		if(why) why += "tied to a post"
	return clamp(round(s), 0, 75)

proc/RmCapRiskWord(odds)
	if(odds <= 0) return "none"
	if(odds < 5) return "low"
	if(odds < 12) return "some"
	if(odds < 25) return "high"
	return "very high"

// The roll: about every 30 s.
mob/Monsters/proc/RmCapTryBonds(Player/P)
	rm_cap_roll_at = world.time + RM_CAP_ROLL + rand(-50, 50)
	var/odds = RmCapEscapeOdds()
	if(odds <= 0) return 0
	if(!prob(odds))
		if(odds >= 12 && world.time - rm_cap_said_at > 1200)
			rm_cap_said_at = world.time
			P.RemasterNotice("[RmCapBareName()] strains at the [lowertext(rm_cap_rope_name || "rope")]; it holds (may break free: [RmCapRiskWord(odds)]).")
		return 0
	RmCapBreakFree(P)
	return 1

mob/Monsters/proc/RmCapBreakFree(Player/P)
	var/bare = RmCapBareName()
	var/rope = rm_cap_rope
	var/rope_name = lowertext(rm_cap_rope_name || "rope")
	if(rope == "chains" && isturf(loc)) new /obj/Items/RemasterTools/IronChains(loc)   // slipped out of: the chains are still whole
	var/what = RmCapFree(P, "escape")
	var/how = rope == "chains" ? "slips out of the [rope_name]" : "breaks the [rope_name]"
	P.RemasterNotice("[bare] [how] and [what == "fights" ? "turns on your people!" : "runs for it!"]")
	P.RemasterLog("[bare] broke free ([what == "fights" ? "fighting" : "fled"])", "fight", src)
	view(src) << "<b>[bare] breaks free!</b>"

// --- Slaves -------------------------------------------------------------------------------------------------
// Every minute: loyalty drifts (fed and whole: up; starving or badly hurt: down). Armed and resentful, they may turn.
mob/Monsters/proc/RmCapSlaveTick(Player/P)
	rm_cap_slave_at = world.time + RM_CAP_SLAVE_EVERY
	if((MaxHunger && Hunger < MaxHunger * 0.15) || (MAXHP && HP < MAXHP * 0.3)) rm_cap_loyalty = max(0, rm_cap_loyalty - 1)
	else if(!MaxHunger || Hunger >= MaxHunger * 0.3) rm_cap_loyalty = min(99, rm_cap_loyalty + 0.5)
	if(!RmCapArmed() || rm_cap_loyalty >= 40) return
	if(!prob(min(20, (40 - rm_cap_loyalty) * 0.5))) return
	var/bare = RmCapBareName()
	RmCapFree(P, "turn")
	P.RemasterNotice("[bare] turns on you with the weapon you gave them!")
	P.RemasterLog("[bare], a slave, turned on you", "fight", src)
	view(src) << "<b>[bare] turns on their masters!</b>"

// Every 4 minutes: four or more slaves together with too few of your people near them may rise (rare).
Player/proc/RmCapRevoltTick()
	var/list/seen = list()
	for(var/mob/Monsters/S in UnitList)
		if(S.rm_cap_state != "slave" || seen[S] || S.HP <= 0 || !isturf(S.loc)) continue
		var/list/group = list()
		var/loyal = 0
		for(var/mob/Monsters/O in range(7, S)) if(O.Owner == src && O.rm_cap_state == "slave" && O.HP > 0)
			group += O
			seen[O] = 1
			loyal += O.rm_cap_loyalty
		if(length(group) < 4) continue
		var/guards = 0
		for(var/mob/Monsters/G in range(7, S)) if(G.Owner == src && !G.rm_cap_state && !G.Critter && G.HP > 0 && !G.Fainted && !G.Sleeping) guards++
		if(length(group) <= guards * 2) continue
		var/chance = clamp(1 + (length(group) - guards * 2) * 1.5 - (loyal / length(group)) * 0.06, 0, 8)
		if(!prob(chance)) continue
		var/list/rising = list()
		for(var/mob/Monsters/O in group) if(O.rm_cap_loyalty < 70) rising += O
		if(!length(rising)) continue
		// they untie the bound captives near them (and open the cages), who join them
		var/untied = 0
		for(var/mob/Monsters/B in rm_captives.Copy()) if(B.Owner == src && B.rm_cap_state == "bound" && B.HP > 0)
			var/turf/bt = RemasterGetTurf(B)
			if(!bt || bt.z != S.z || get_dist(bt, S) > 7) continue
			if(B.rm_cap_rope == "chains" && bt) new /obj/Items/RemasterTools/IronChains(bt)
			rising += B
			untied++
		for(var/mob/Monsters/O in rising) O.RmCapFree(src, "rising")
		RemasterNotice("The slaves rise up! [length(rising) - untied] throw off their hobbles[untied ? ", untie [untied] captive[untied == 1 ? "" : "s"]" : ""] and fall on your people.")
		RemasterLog("Slave revolt: [length(rising) - untied] rose up[untied ? ", [untied] captives untied" : ""]", "fight", S)
		view(S) << "<b>The slaves rise up!</b>"
		spawn(0) RmCapRising(src, rising)

// How long one of a rising fights before it runs: the better fighter, the longer (8-30 s).
proc/RmCapStrikeTime(mob/Monsters/M)
	return min(300, RM_CAP_STRIKE + (RemasterCombatLevel(M, "Attack") + RemasterCombatLevel(M, "Strength")) * 2.5)

mob/Monsters/proc/RmCapArmed1()
	for(var/obj/Items/Equipment/Weapon/W in src) if(W.suffix == "(Equipped)") return W
	for(var/obj/Items/Equipment/Weapon/W in src) if(W.suffix == "(Carrying)")
		EquipItem(W)   // its answer isn't always the item: look at what it holds
		if(W.suffix == "(Equipped)") return W
	return null

// The nearest weapon lying on the ground within 6 tiles that nobody else of the rising is going for, or null.
proc/RmCapLooseWeapon(mob/Monsters/M, list/claimed)
	var/obj/Items/best
	for(var/obj/Items/Equipment/Weapon/W in range(6, M)) if(isturf(W.loc) && !W.suffix && !(W in claimed) && (!best || get_dist(W, M) < get_dist(best, M))) best = W
	return best

// A rising (user, 2026-10-23): each goes for a weapon lying within 6 tiles, if there is one, and takes it up; armed, it
// falls on your people within 6 tiles (as far as an NPC chases, Monster AI.dm RandomWalk) for its strike time (the better
// fighter, the longer) or until badly hurt, then runs home. Unarmed, it runs at once, fighting back for a moment only
// when one of yours is right beside it. The rising breaks off when the last one runs.
proc/RmCapRising(Player/P, list/group)
	var/list/phase = list()     // M -> "arm", "strike", "cornered" or "run"
	var/list/goal = list()      // M -> the weapon it goes for
	var/list/claimed = list()
	var/list/fought = list()    // who has had its moment of fighting back while cornered
	for(var/mob/Monsters/M in group)
		if(M.RmCapArmed1())
			phase[M] = "strike"
			M.rm_cap_strike_until = world.time + RmCapStrikeTime(M)
			continue
		var/obj/W = RmCapLooseWeapon(M, claimed)
		if(W)
			phase[M] = "arm"
			goal[M] = W
			claimed += W
			M.rm_cap_strike_until = world.time + 200   // at most 20 s to reach it
		else phase[M] = "run"
	var/struck = 0
	var/until = world.time + 900
	while(length(phase) && world.time < until)
		for(var/mob/Monsters/M in phase.Copy())
			if(!M || M.HP <= 0 || M.GoingToDie)
				phase -= M
				continue
			var/mob/Monsters/foe   // the nearest of P's free people in sight
			if(P) for(var/mob/Monsters/O in range(10, M)) if(O.Owner == P && !O.rm_cap_state && !O.Critter && O.HP > 0 && !O.GoingToDie && (!foe || get_dist(O, M) < get_dist(foe, M))) foe = O
			switch(phase[M])
				if("arm")
					var/obj/Items/W = goal[M]
					if(M.RmCapArmed1())   // its own look round for gear (Monster AI.dm FindGear) got there first
						phase[M] = "strike"
						M.rm_cap_strike_until = world.time + RmCapStrikeTime(M)
					else if(!W || !isturf(W.loc) || world.time >= M.rm_cap_strike_until)
						phase[M] = "run"
					else if(get_dist(M, W) <= 1)
						M.destination = null
						if(M.PickUpItem(W, 0, 1) && M.RmCapArmed1())
							phase[M] = "strike"
							M.rm_cap_strike_until = world.time + RmCapStrikeTime(M)
						else phase[M] = "run"
					else
						M.HomeLoc = W.loc   // an NPC walks only to a mob or its HomeLoc (Monster AI.dm RandomWalk)
						M.destination = W.loc
						continue
				if("cornered")
					if(world.time >= M.rm_cap_strike_until || !foe || get_dist(foe, M) > 1) phase[M] = "run"
					else
						struck = 1
						M.Target = foe
						M.destination = foe
						continue
				if("strike")
					if(!foe || world.time >= M.rm_cap_strike_until || M.HP < M.MAXHP * 0.4) phase[M] = "run"
					else
						struck = 1
						M.Target = foe
						M.destination = foe
						if(get_dist(M, foe) > 6)   // an NPC chases a mob only within 6 tiles: further off, to where it stands (RandomWalk)
							M.HomeLoc = foe.loc
							M.destination = foe.loc
						continue
			// running: unarmed with one of yours right beside it, it fights back for a moment first
			if(phase[M] == "run")
				if(foe && get_dist(foe, M) <= 1 && !fought[M])
					fought[M] = 1
					phase[M] = "cornered"
					M.rm_cap_strike_until = world.time + 50
					M.Target = foe
					M.destination = foe
					struck = 1
					continue
				phase -= M
				M.Target = null
				M.RmCapGoHome(P, M.rm_cap_flee_home)
		sleep(10)
	if(P) P.RemasterNotice(struck ? "The rising breaks off: the slaves run for it." : "The slaves run for it.")
	if(P) P.RemasterLog(struck ? "The slave rising broke off; they ran" : "The risen slaves ran off", "fight")

// --- Lines ------------------------------------------------------------------------------------------------
// Who follows X directly on the rope (a captive has one follower at most; a leader two lines).
proc/RmCapFollowers(mob/Monsters/X)
	. = list()
	for(var/mob/Monsters/M in rm_captives) if(M.remaster_captive_lead == X && M.rm_cap_state == "bound") . += M

// The last captive of the line behind X (X itself when nobody follows it).
proc/RmCapLineEnd(mob/Monsters/X)
	var/mob/Monsters/E = X
	for(var/n = 0, n < 60, n++)
		var/list/F = RmCapFollowers(E)
		if(!length(F)) break
		E = F[1]
	return E

proc/RmCapLineLength(mob/Monsters/H)
	. = 0
	var/mob/Monsters/E = H
	while(E && . < 60)
		.++
		var/list/F = RmCapFollowers(E)
		E = length(F) ? F[1] : null

// For the card and the Captives list, looked up at most every 2 s: a tree or post near (1/0), another captive's line
// near (1/0), an empty cage near (1/0).
mob/Monsters/var/tmp/list/rm_cap_near
mob/Monsters/var/tmp/rm_cap_near_at = 0
mob/Monsters/proc/RmCapNear(Player/P)
	if(rm_cap_near && world.time < rm_cap_near_at) return rm_cap_near
	rm_cap_near_at = world.time + 20
	var/free = rm_cap_state == "bound" && !rm_cap_cage
	rm_cap_near = list(free && RmCapPostSpot(src) ? 1 : 0, free && RmCapNearestLine(P, src) ? 1 : 0, free && RmCapCageNear(P, src) ? 1 : 0, free && RmCapStaker(P, src) ? 1 : 0)
	return rm_cap_near

// Where a captive goes on L's rope: L's hand while it holds fewer than two lines, else behind the shorter line.
proc/RmCapLeadSpot(mob/Monsters/L)
	if(L.rm_cap_state == "bound") return RmCapLineEnd(L)
	var/list/heads = RmCapFollowers(L)
	if(length(heads) < 2) return L
	var/mob/Monsters/A = heads[1]
	var/mob/Monsters/B = heads[2]
	return RmCapLineEnd(RmCapLineLength(A) <= RmCapLineLength(B) ? A : B)

// Is X somewhere behind T in T's line (so tying T behind X would make a ring)?
proc/RmCapBehind(mob/Monsters/T, mob/Monsters/X)
	var/mob/Monsters/E = X
	for(var/n = 0, E && n < 60, n++)
		if(E == T) return 1
		E = E.remaster_captive_lead
	return 0

// Leaving a line: whoever followed this one follows the one in front of it (or is tied where it stands).
mob/Monsters/proc/RmCapLeaveLine()
	var/mob/Monsters/front = remaster_captive_lead
	var/Player/P = istype(Owner, /Player) ? Owner : null
	for(var/mob/Monsters/F in RmCapFollowers(src))
		if(front && front != F && isturf(front.loc)) F.remaster_captive_lead = front
		else F.RmCapTieHere(P)

// "attach": T goes on X's rope: behind X's line when X is a captive, on X's own rope when X is one of your people.
Player/proc/RmCapAttach(mob/Monsters/T, mob/Monsters/X)
	if(!istype(T) || T.rm_cap_state != "bound" || T.Owner != src) return 0
	if(!istype(X) || X == T || X.Owner != src || X.HP <= 0 || (X.rm_cap_state && X.rm_cap_state != "bound") || X.Critter)
		RemasterNotice("[T.RmCapBareName()] can be roped behind another bound captive, or handed to one of your people.")
		return 0
	if(T.rm_cap_cage)
		RemasterNotice("[T.RmCapBareName()] is in a cage: take them out first.")
		return 0
	var/turf/a = RemasterGetTurf(T)
	var/turf/b = RemasterGetTurf(X)
	if(!a || !b || a.z != b.z || get_dist(a, b) > 8)
		RemasterNotice("[X.rm_cap_state ? X.RmCapBareName() : X.RemasterBareName()] is too far off: bring them closer first (Move them).")
		return 0
	var/mob/Monsters/E = RmCapLeadSpot(X)
	if(E == T || RmCapBehind(T, E))
		RemasterNotice("[T.RmCapBareName()] can't be roped behind their own line.")
		return 0
	var/mob/Monsters/old = T.remaster_captive_lead
	if(old != E)
		T.RmCapLeaveLine()   // the ones behind them close up on the old line
		T.remaster_captive_lead = E
		T.rm_cap_tied = null
		T.rm_cap_post = 0
	RemasterNotice(X.rm_cap_state ? "[T.RmCapBareName()] is roped behind [E.RmCapBareName()], in [X.RmCapBareName()]'s line." : "[X.RemasterBareName()] takes [T.RmCapBareName()]'s rope[E != X ? " (behind [E.RmCapBareName()])" : ""].")
	return 1

// The nearest bound captive of P's within 8 tiles that T could go behind (not in T's own line), or null.
proc/RmCapNearestLine(Player/P, mob/Monsters/T)
	var/mob/Monsters/best
	var/turf/a = RemasterGetTurf(T)
	for(var/mob/Monsters/M in rm_captives)
		if(M == T || M.Owner != P || M.rm_cap_state != "bound" || M.rm_cap_cage || !isturf(M.loc) || M.z != a.z || get_dist(M, a) > 8) continue
		if(RmCapBehind(T, RmCapLeadSpot(M))) continue
		if(!best || get_dist(M, a) < get_dist(best, a)) best = M
	return best

// --- A tree or a post --------------------------------------------------------------------------------------
// The thing nearest T within `range` to tie them to: anything RmCapTieable, other than what they are tied to now
// (then "Tie to something" moves them on to the next thing); null when none.
proc/RmCapNearestTieable(mob/Monsters/T, range = 10)
	var/turf/a = RemasterGetTurf(T)
	if(!a) return null
	var/atom/now = T.rm_cap_tied && T.rm_cap_post ? T.RmCapPostAt() : null
	var/atom/best
	for(var/atom/X in range(range, a))
		if(X == now || ismob(X) && !istype(X, /mob/WorkShops)) continue
		if(!isturf(X) && !isturf(X.loc)) continue
		if((!best || get_dist(X, a) < get_dist(best, a)) && RmCapTieable(X)) best = X
	return best

// The open tile beside the nearest thing to tie T to (or beside `best` when given), nearest T, or null.
proc/RmCapPostSpot(mob/Monsters/T, range = 10, atom/best)
	var/turf/a = RemasterGetTurf(T)
	if(!best) best = RmCapNearestTieable(T, range)
	if(!best) return null
	var/turf/spot
	for(var/turf/S in orange(1, best))
		if(S.density || S.vars["Tree"]) continue
		var/blocked = 0
		for(var/atom/movable/O in S) if(O.density && O != T)
			blocked = 1
			break
		if(!blocked && (!spot || get_dist(S, a) < get_dist(spot, a))) spot = S
	return spot

Player/proc/RmCapTieToPost(mob/Monsters/T, atom/A)
	if(!istype(T) || T.rm_cap_state != "bound" || T.Owner != src || T.rm_cap_cage) return 0
	if(A)
		var/turf/at = RemasterGetTurf(A)
		if(!at || at.z != T.z || get_dist(at, T) > 15 || !RmCapTieable(A))
			RemasterNotice("[T.RmCapBareName()] can't be tied to that.")
			return 0
	else A = RmCapNearestTieable(T)
	if(!A)
		RemasterNotice("Nothing to tie [T.RmCapBareName()] to within 10 tiles: a tree, a wall, a post, furniture... or Stake here.")
		return 0
	var/what = RmCapTieName(A)
	if(T.z == A.z && get_dist(T, A) <= 1 && T.loc != RemasterGetTurf(A))   // beside it already: tied there and then
		T.RmCapTieHere(src)
		RemasterNotice("[T.RmCapBareName()] is tied to the [what].")
		return 1
	var/turf/S = RmCapPostSpot(T, 10, A)
	if(!S)
		RemasterNotice("No open ground beside the [what] to tie [T.RmCapBareName()] at.")
		return 0
	var/mob/Monsters/L = T.remaster_captive_lead
	if(!L || L.rm_cap_state || L.HP <= 0 || L.Owner != src) L = RmCapNearestFree(src, T)
	if(!L)
		RemasterNotice("None of your people are near enough to lead [T.RmCapBareName()] there.")
		return 0
	spawn(0) L.RmCapPostWalk(T, S, src)
	RemasterNotice("[L.RemasterBareName()] takes [T.RmCapBareName()] to the [what] to tie them to it.")
	return 1

// --- A stake in open ground ----------------------------------------------------------------------------------
// A pointed wooden stake (art/enhance/rope32.py "stake"): carried like a tool, or cut from a log of wood on the spot.
// Driven into the ground beside a bound captive and the rope tied to it, it is a post: they hold as well as at a
// tree (user, 2026-10-23: "stake rope in ground"). It stays in the ground for the next one; picked up, it can be carried.
obj/Items/RemasterStake
	// its values: art/items/catalogue.json row remasterstake (export_items.py writes ItemData.dm)
	var/list/rm_planted   // x, y, z where it was driven in

proc/RmStakePlanted(obj/Items/RemasterStake/S)
	return S && isturf(S.loc) && S.suffix == "(In the ground)" && islist(S.rm_planted) && S.rm_planted[1] == S.x && S.rm_planted[2] == S.y && S.rm_planted[3] == S.z

// What O can stake someone with: a stake they carry, else a log of wood (cut into one); null when neither.
proc/RmStakeStuff(mob/Monsters/O)
	for(var/obj/Items/RemasterStake/S in O) if(S.suffix != "(Equipped)") return S
	for(var/obj/Items/woods/wood/W in O) if(W.suffix != "(Equipped)") return W
	return null

// Who stakes T: their leader if they have the stuff, else the nearest of yours within 10 tiles who does.
proc/RmCapStaker(Player/P, mob/Monsters/T)
	var/turf/a = RemasterGetTurf(T)
	if(!a) return null
	var/mob/Monsters/L = T.remaster_captive_lead
	if(L && !L.rm_cap_state && L.HP > 0 && L.Owner == P && RmStakeStuff(L)) return L
	var/mob/Monsters/best
	for(var/mob/Monsters/O in range(10, a)) if(O.Owner == P && !O.rm_cap_state && O.HP > 0 && !O.GoingToDie && !O.RemasterKnockedOut() && RmStakeStuff(O))
		if(!best || get_dist(O, a) < get_dist(best, a)) best = O
	return best

Player/proc/RmCapStakeHere(mob/Monsters/T)
	if(!istype(T) || T.rm_cap_state != "bound" || T.Owner != src || T.rm_cap_cage) return 0
	var/mob/Monsters/U = RmCapStaker(src, T)
	if(!U)
		RemasterNotice("To stake [T.RmCapBareName()] where they are, one of yours near them needs a stake, or a log of wood to cut one from.")
		return 0
	if(U.z == T.z && get_dist(U, T) <= 1) return U.RmCapStakeNow(T, src)
	spawn(0) U.RmCapStakeWalk(T, src)
	RemasterNotice("[U.RemasterBareName()] goes to stake [T.RmCapBareName()] where they are.")
	return 1

mob/Monsters/proc/RmCapStakeWalk(mob/Monsters/T, Player/P)
	RemasterCancelOrders()
	remaster_order_status = "Staking [T.RmCapBareName()]"
	var/until = world.time + 900
	while(src && T && T.rm_cap_state == "bound" && !T.rm_cap_cage && T.Owner == P && HP > 0 && world.time < until)
		if(remaster_active || remaster_attack || length(remaster_orders)) return
		if(z == T.z && get_dist(src, T) <= 1)
			destination = null
			RmCapStakeNow(T, P)
			break
		destination = RmCapBeside(T, src)
		sleep(3)
	if(src && findtext("[remaster_order_status]", "Staking")) remaster_order_status = "Idle"

// The stake goes into open ground beside T (a straight side first; their own tile when none is free), they are tied to it.
mob/Monsters/proc/RmCapStakeNow(mob/Monsters/T, Player/P)
	var/obj/Items/X = RmStakeStuff(src)
	if(!X || !T || T.rm_cap_state != "bound" || T.rm_cap_cage || !isturf(T.loc)) return 0
	var/turf/spot
	for(var/d in list(NORTH, EAST, SOUTH, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST))
		var/turf/S = get_step(T, d)
		if(!S || S.density || S.vars["Tree"] || (locate(/mob) in S) || (locate(/obj/Items/RemasterStake) in S) || (locate(/obj/Items/Traps/Cages) in S)) continue
		var/blocked = 0
		for(var/atom/movable/O in S) if(O.density)
			blocked = 1
			break
		if(!blocked)
			spot = S
			break
	if(!spot) spot = T.loc
	var/obj/Items/RemasterStake/K
	var/cut = 0
	if(istype(X, /obj/Items/RemasterStake))
		K = X
		if(K.suffix == "(Equipped)") UnEquipItem(K)
		weight -= K.weight
	else
		weight -= X.weight
		del X
		K = new
		cut = 1
	K.loc = spot
	K.suffix = "(In the ground)"   // not taken off to a stockpile (Settlement.dm RemasterMayCollect)
	K.Owner = P
	K.rm_planted = list(spot.x, spot.y, spot.z)
	T.RmCapTieHere(P)
	if(P) P.RemasterNotice("[RemasterBareName()] [cut ? "cuts a stake from a log of wood, drives it" : "drives a stake"] into the ground beside [T.RmCapBareName()] and ties them to it: they hold as well as at a tree.")
	return 1

// L leads T next to the spot S beside a tree or post, the captive is stepped onto S and tied to it.
mob/Monsters/proc/RmCapPostWalk(mob/Monsters/T, turf/S, Player/P)
	RemasterCancelOrders()
	remaster_order_status = "Taking [T.RmCapBareName()] to tie them up"
	var/until = world.time + 1200
	var/blocked = 0      // pulls that brought them no nearer
	var/aside_until = 0  // stepping round to the far side of the spot
	while(src && T && T.rm_cap_state == "bound" && !T.rm_cap_cage && T.Owner == P && HP > 0 && world.time < until)
		if(remaster_active || remaster_attack || length(remaster_orders)) return
		if(S != T.loc && (locate(/mob/Monsters) in S))   // someone (a captive roped behind) took the spot: another one beside it
			S = RmCapPostSpot(T) || S
		if(T.loc == S || (get_dist(T, S) <= 1 && T.RmCapPostNear()))
			destination = null
			T.RmCapTieHere(P)
			P.RemasterNotice("[RemasterBareName()] ties [T.RmCapBareName()] to the [T.RmCapPostKind() || "spot"].")
			remaster_order_status = "Idle"
			return
		if(T.remaster_captive_lead != src)
			if(z == T.z && get_dist(src, T) <= 1)
				T.RmCapLeaveLine()
				T.remaster_captive_lead = src
				T.rm_cap_tied = null
			else
				destination = RmCapBeside(T, src)
				sleep(5)
				continue
		if(world.time >= aside_until)   // (not while the leader steps round to the far side of the spot, below)
			if(T.z == S.z && get_dist(T, S) <= 2 && get_dist(src, S) <= 1 && world.time >= T.rm_cap_step_at)
				destination = null
				var/d_was = get_dist(T, S)
				if(get_dist(T, S) == 1 && !(locate(/mob/Monsters) in S))   // the last step onto the spot, pulled by the rope
					T.rm_cap_leading = 1
					T.Move(S, get_dir(T, S))
					T.rm_cap_leading = 0
				else T.RmCapStepToward(S)
				T.rm_cap_step_at = world.time + max(2, T.RemasterStepDelay())
				// every step nearer taken (its leader stands in the way, another captive...): the leader steps round to the far
				// side of the spot, so the two never wait on each other for good (polish 10-26; AFTER_FOCUS_QUEUE "tie-to-tree")
				if(get_dist(T, S) < d_was) blocked = 0
				else if(++blocked >= 3)
					blocked = 0
					var/turf/W = RmCapFarBeside(S, T, src)
					if(W)
						destination = W
						aside_until = world.time + 20
			else if(get_dist(src, S) > 1) destination = RmCapBesideNot(S, src, S)
		sleep(3)
	if(src && findtext("[remaster_order_status]", "to tie them up")) remaster_order_status = "Idle"

// A free tile beside A for M to stand on, never `not` (where the captive is to go).
// A free tile beside A as far from T as can be, for T's leader to stand on out of its way; null when none is farther off
// than where the leader stands.
proc/RmCapFarBeside(atom/A, mob/T, mob/L)
	var/turf/best
	for(var/turf/X in orange(1, A))
		if(X.density || X.vars["Tree"] || X == L.loc) continue
		var/blocked = 0
		for(var/atom/movable/O in X) if(O != L && (O.density || ismob(O)))
			blocked = 1
			break
		if(blocked) continue
		if(!best || get_dist(X, T) > get_dist(best, T) || (get_dist(X, T) == get_dist(best, T) && get_dist(X, L) < get_dist(best, L))) best = X
	if(best && get_dist(best, T) <= get_dist(L, T)) return null
	return best

proc/RmCapBesideNot(atom/A, mob/M, turf/not)
	var/turf/best
	for(var/turf/X in orange(1, A))
		if(X == not || X.density) continue
		var/blocked = 0
		for(var/atom/movable/O in X) if(O.density && O != M)
			blocked = 1
			break
		if(!blocked && (!best || get_dist(X, M) < get_dist(best, M))) best = X
	return best || RemasterGetTurf(A)

// --- Cages -------------------------------------------------------------------------------------------------
// "wooden cage" (the original names are "WoodenCage", "MetalCage"...).
proc/RmCapCageName(obj/O)
	var/n = "[O.name]"
	var/out = ""
	for(var/i = 1, i <= length(n), i++)
		var/c = copytext(n, i, i + 1)
		if(i > 1 && c != lowertext(c) && copytext(n, i - 1, i) != " ") out += " "
		out += c
	return lowertext(out)

proc/RmCapIsCage(obj/O)
	return istype(O, /obj/Items/Traps/Cages) && !istype(O, /obj/Items/Traps/Cages/Cacoon)

// The nearest empty cage within `range` of T: on the ground, or carried by one of P's people; or null.
proc/RmCapCageNear(Player/P, mob/Monsters/T, range = 8)
	var/turf/a = RemasterGetTurf(T)
	var/obj/best
	for(var/obj/Items/Traps/Cages/C in range(range, a)) if(RmCapIsCage(C) && !C.HasPersonIn && !(locate(/mob) in C) && (!best || get_dist(C, a) < get_dist(best, a))) best = C
	if(best) return best
	for(var/mob/Monsters/M in range(range, a)) if(M.Owner == P && !M.rm_cap_state)
		for(var/obj/Items/Traps/Cages/C in M) if(RmCapIsCage(C) && !C.HasPersonIn && C.suffix == "(Carrying)") return C
	return null

Player/proc/RmCapIntoCage(mob/Monsters/T, obj/Items/Traps/Cages/C)
	if(!istype(T) || T.rm_cap_state != "bound" || T.Owner != src) return 0
	if(T.rm_cap_cage)
		RemasterNotice("[T.RmCapBareName()] is already in a cage.")
		return 0
	if(!C) C = RmCapCageNear(src, T)
	if(!C || !RmCapIsCage(C) || C.HasPersonIn)
		RemasterNotice("No empty cage near [T.RmCapBareName()]: cages are made at a Carpentry (wooden), Bone crafting (bone) or a Forge (metal, gold).")
		return 0
	if(ismob(C.loc))   // a carried cage is set down first: a cage with someone in it can't be carried
		var/mob/Monsters/U = C.loc
		U.DropItem(C)
	var/mob/Monsters/L = T.remaster_captive_lead
	if(!L || L.rm_cap_state || L.HP <= 0 || L.Owner != src) L = RmCapNearestFree(src, T)
	if(get_dist(RemasterGetTurf(T), C) <= 1)
		T.RmCapCageIn(C, src, 0, L)
		return 1
	if(!L)
		RemasterNotice("None of your people are near enough to take [T.RmCapBareName()] to the cage.")
		return 0
	spawn(0) L.RmCapCageWalk(T, C, src)
	RemasterNotice("[L.RemasterBareName()] takes [T.RmCapBareName()] to the [RmCapCageName(C)].")
	return 1

// L leads T to the cage C and puts them in.
mob/Monsters/proc/RmCapCageWalk(mob/Monsters/T, obj/Items/Traps/Cages/C, Player/P)
	RemasterCancelOrders()
	remaster_order_status = "Taking [T.RmCapBareName()] to the cage"
	var/until = world.time + 1200
	var/stuck_at = world.time   // when the captive last got nearer the cage
	var/last_d = 1#INF
	while(src && T && C && T.rm_cap_state == "bound" && !T.rm_cap_cage && T.Owner == P && HP > 0 && world.time < until && isturf(C.loc) && !C.HasPersonIn)
		if(remaster_active || remaster_attack || length(remaster_orders)) return
		if(T.remaster_captive_lead != src)
			if(z == T.z && get_dist(src, T) <= 1)
				T.RmCapLeaveLine()
				T.remaster_captive_lead = src
				T.rm_cap_tied = null
			else
				destination = RmCapBeside(T, src)
				sleep(5)
				continue
		var/dc = T.z == C.z ? get_dist(T, C) : 1#INF
		if(dc < last_d)
			last_d = dc
			stuck_at = world.time
		if(T.z == C.z && (dc <= 1 || (dc <= 2 && get_dist(src, C) <= 1 && world.time >= stuck_at + 15)))
			destination = null   // beside it, or a step off with the leader at the door (bundled in)
			T.RmCapCageIn(C, P, 0, src)
			remaster_order_status = "Idle"
			return
		if(T.z == C.z && get_dist(T, C) <= 3 && get_dist(src, C) <= 1)
			destination = null
			if(world.time >= T.rm_cap_step_at)   // the last steps to the cage, pulled by the rope
				T.RmCapStepToward(C)
				T.rm_cap_step_at = world.time + max(2, T.RemasterStepDelay())
		else destination = RmCapBeside(C, src)
		sleep(3)
	if(src && findtext("[remaster_order_status]", "to the cage")) remaster_order_status = "Idle"

// In the cage the rope comes off them (user, 2026-10-23): back to `by`, the one who put them in, else beside the cage.
mob/Monsters/proc/RmCapCageIn(obj/Items/Traps/Cages/C, Player/P, quiet = 0, mob/Monsters/by)
	RmCapLeaveLine()
	remaster_captive_lead = null
	rm_cap_tied = null
	rm_cap_post = 0
	destination = null
	if(P) P.Selected -= src
	loc = C
	Caged = 1
	C.HasPersonIn = 1
	C.underlays += src     // the original cage shows who is in it
	rm_cap_cage = 1
	var/rope = rm_cap_rope_name ? lowertext(rm_cap_rope_name) : null
	var/obj/Items/R = RmCapRopeItem(RemasterGetTurf(C))
	var/back = ""
	if(R) back = (by && by.HP > 0 && by.PickUpItem(R, 0, 2)) ? ", and [by.RemasterBareName()] takes the [rope] back" : ", the [rope] off them (it lies beside the cage)"
	if(P && !quiet)
		P.RemasterNotice("[RmCapBareName()] is shut in the [RmCapCageName(C)][back]. They can't get out on their own, and a cage with someone in it can't be carried.")
		P.RemasterLog("[RmCapBareName()] caged", "info", C)

// Out of the cage, onto its tile, tied there.
mob/Monsters/proc/RmCapUncage(Player/P)
	var/obj/C = loc
	var/turf/T = RemasterGetTurf(C)
	if(istype(C, /obj))
		C.HasPersonIn = 0
		C.underlays = null
		C.overlays = null
	rm_cap_cage = 0
	Caged = 0
	if(T)
		loc = RmCapFreeBeside(C)   // beside it, never on the cage's own tile (they looked still shut in)
		rm_cap_tied = list(x, y, z)
		rm_cap_post = RmCapPostNear()
	if(P) P.RemasterNotice("[RmCapBareName()] is taken out of the cage and tied up beside it.")

// Caged, they wear no rope: to take them out, one of yours with a rope (the nearest within 10 tiles of the cage) goes
// to the cage and ties them up beside it as they come out.
proc/RmCapCageRoper(Player/P, mob/Monsters/T)
	var/turf/a = RemasterGetTurf(T)
	if(!a) return null
	var/mob/Monsters/best
	for(var/mob/Monsters/O in range(10, a)) if(O.Owner == P && !O.rm_cap_state && O.HP > 0 && !O.GoingToDie && !O.RemasterKnockedOut() && RmCapRopeAtHand(P, O, null))
		if(!best || get_dist(O, a) < get_dist(best, a)) best = O
	return best

Player/proc/RmCapTakeOut(mob/Monsters/T)
	if(!istype(T) || !T.rm_cap_cage || T.Owner != src) return 0
	var/mob/Monsters/U = RmCapCageRoper(src, T)
	if(!U)
		RemasterNotice("To take [T.RmCapBareName()] out of the cage, one of yours near it needs a rope to tie them as they come out. [RmCapNoRopeText(null)]")
		return 0
	if(get_dist(U, RemasterGetTurf(T)) <= 1) return U.RmCapTakeOutNow(T, src)
	spawn(0) U.RmCapTakeOutWalk(T, src)
	RemasterNotice("[U.RemasterBareName()] goes to let [T.RmCapBareName()] out of the [RmCapCageName(T.loc)].")
	return 1

mob/Monsters/proc/RmCapTakeOutWalk(mob/Monsters/T, Player/P)
	RemasterCancelOrders()
	remaster_order_status = "Letting [T.RmCapBareName()] out of the cage"
	var/until = world.time + 900
	while(src && T && T.rm_cap_cage && T.Owner == P && HP > 0 && world.time < until)
		if(remaster_active || remaster_attack || length(remaster_orders)) return
		var/obj/C = T.loc
		if(!isobj(C) || !isturf(C.loc)) break
		if(z == C.z && get_dist(src, C) <= 1)
			destination = null
			RmCapTakeOutNow(T, P)
			break
		destination = RmCapBeside(C, src)
		sleep(3)
	if(src && findtext("[remaster_order_status]", "out of the cage")) remaster_order_status = "Idle"

mob/Monsters/proc/RmCapTakeOutNow(mob/Monsters/T, Player/P)
	var/obj/Items/R = RmCapRopeAtHand(P, src, null)
	if(!R || !T.rm_cap_cage) return 0
	var/cage = RmCapCageName(T.loc)
	T.RmCapUncage()
	T.RmCapRopeOn(R)
	T.rm_cap_roll_at = world.time + RM_CAP_ROLL + rand(-50, 50)
	if(P) P.RemasterNotice("[RemasterBareName()] lets [T.RmCapBareName()] out of the [cage] and ties them up beside it with the [lowertext(T.rm_cap_rope_name)].")
	return 1

// A cage with someone in it is too heavy to carry (user, 2026-10-23).
mob/PickUpItem(atom/movable/ITEM, Telling = 0, Range = 1)
	if(istype(ITEM, /obj/Items/Traps/Cages) && ITEM:HasPersonIn && isturf(ITEM.loc))
		if(Telling || istype(usr, /Player)) usr << "A cage with someone in it is too heavy to carry: take them out first."
		return 0
	if(istype(ITEM, /obj/Items/RemasterStake) && RmStakePlanted(ITEM))
		for(var/mob/Monsters/M in range(1, ITEM)) if(M.rm_cap_state == "bound" && M.rm_cap_tied && M.rm_cap_post && M.RmCapPostAt() == ITEM)
			if(Telling || istype(usr, /Player)) usr << "[M.RmCapBareName()] is tied to this stake: lead them away or take the rope off first."
			return 0
	return ..()

obj/Items/Traps/Cages/DblClick()
	if(HasPersonIn && isturf(loc))
		usr << "A cage with someone in it is too heavy to carry. Select the one inside (their card's Interact tab) to take them out."
		return
	return ..()

// Saved with the army inside a cage: their place is the cage's tile (a unit inside an object is at 0, 0, 0).
mob/Monsters/Write(savefile/F)
	if(rm_cap_cage && istype(loc, /obj))
		var/turf/T = RemasterGetTurf(loc)
		if(T)
			savedx = T.x
			savedy = T.y
			savedz = T.z
	else if(RmIsShip(loc))   // aboard a ship: ashore beside it (Ships.dm)
		var/turf/S = RmShipSaveTurf(loc)
		if(S)
			savedx = S.x
			savedy = S.y
			savedz = S.z
	return ..()

// world/New: this file's part is step RmChainWorldNew_Captives in Code/Remastered/Chains/WorldNew.dm

proc/RmCaptiveLoop()
	while(1)
		sleep(2)
		if(world.time >= rm_cap_relink_at) RmCapRelink()
		for(var/mob/Monsters/M in rm_captives.Copy())
			var/Player/P = M ? M.Owner : null
			if(!M || !M.rm_cap_state || M.HP <= 0 || M.GoingToDie || !istype(P))
				rm_captives -= M
				continue
			if(M.rm_cap_state == "bound")
				M.RmCapLeadTick(P)
				if(world.time >= M.rm_cap_roll_at) M.RmCapTryBonds(P)
			else if(world.time >= M.rm_cap_slave_at) M.RmCapSlaveTick(P)
		if(world.time >= rm_cap_revolt_at)
			rm_cap_revolt_at = world.time + RM_CAP_REVOLT
			for(var/Player/P in Players) P.RmCapRevoltTick()

// Captives saved with an army are picked up again once their player is in the game: one that was led is tied where it
// stands, and its next try at its bonds comes a full half-minute later.
proc/RmCapRelink()
	rm_cap_relink_at = world.time + 50
	for(var/Player/P in Players) for(var/mob/Monsters/M in P.UnitList)
		if(!M.rm_cap_state || (M in rm_captives) || M.Owner != P || M.HP <= 0) continue
		rm_captives += M
		M.rm_cap_roll_at = world.time + RM_CAP_ROLL
		M.rm_cap_slave_at = world.time + RM_CAP_SLAVE_EVERY
		if(M.rm_cap_state == "bound" && M.rm_cap_cage && isturf(M.loc))   // saved in a cage: back into the empty cage on its spot
			var/obj/Items/Traps/Cages/C
			for(var/obj/Items/Traps/Cages/X in range(1, M)) if(RmCapIsCage(X) && !(locate(/mob) in X))
				C = X
				break
			if(C) M.RmCapCageIn(C, null, 1)
			else M.rm_cap_cage = 0
		if(M.rm_cap_state == "bound" && !M.rm_cap_cage && !M.remaster_captive_lead && !M.rm_cap_tied) M.rm_cap_tied = list(M.x, M.y, M.z)

// --- The card (HUD.dm RemasterUnitData "captive") and its buttons ------------------------------------------
mob/Monsters/proc/RmCaptiveData(Player/P)
	if(!rm_cap_state) return null
	var/list/why = list()
	var/odds = RmCapEscapeOdds(why)
	var/mob/Monsters/L = remaster_captive_lead
	var/mob/Monsters/K = rm_cap_talker
	var/list/N = RmCapNear(P)
	var/from = rm_cap_from_player ? "another realm" : rm_cap_from ? "the [replacetext(replacetext(replacetext("[rm_cap_from]", "{", ""), "}", ""), "NPC ", "")]" : null
	return list("state"=rm_cap_state, "rope"=rm_cap_rope_name, "ropeWord"=RmRopeWord(rm_cap_rope_power), "ropePower"=rm_cap_rope_power,
		"loyalty"=round(rm_cap_loyalty), "odds"=(rm_cap_state == "bound" ? odds : null), "risk"=(rm_cap_state == "bound" ? RmCapRiskWord(odds) : null), "why"=why,
		"led"=(L ? (L.rm_cap_state ? L.RmCapBareName() : L.RemasterBareName()) : null), "tied"=(rm_cap_tied ? 1 : 0), "post"=rm_cap_post, "postKind"=RmCapPostKind(), "talker"=(K ? K.RemasterBareName() : null),
		"armed"=RmCapArmed(), "fights"=RmCapMayFight(), "from"=from, "out"=RmCapOutCold(),
		"cage"=(rm_cap_cage && isobj(loc) ? RmCapCageName(loc) : null), "inLine"=(L && L.rm_cap_state == "bound" ? L.RmCapBareName() : null), "behind"=length(RmCapFollowers(src)),
		"canPost"=N[1], "canLine"=N[2], "canCage"=N[3], "canStake"=N[4], "canOut"=(rm_cap_cage && RmCapCageRoper(P, src) ? 1 : 0))

// Army > Captives (hud-craft's page): every captive this player holds, with its actions and why one can't be done now.
// state: "bound", "winning" (bound, someone talking with them) or "slave"; risk: the chance (%) at the next try at the
// rope, next: seconds to it; by: who is winning them over. Buttons send "captive" "ref|cmd"; a row goes to x, y, z.
Player/proc/RmCaptivesData()
	. = list()
	for(var/mob/Monsters/M in UnitList)
		if(!M.rm_cap_state || M.Owner != src || M.HP <= 0) continue
		var/bound = M.rm_cap_state == "bound"
		var/turf/MT = RemasterGetTurf(M)
		var/list/N = M.RmCapNear(src)
		var/mob/Monsters/K = M.rm_cap_talker
		var/talker = (K && K.HP > 0) ? K : RmCapBestTalker(src, M)
		var/list/acts = list(list("win", "Win over", M.RmCapOutCold() ? "Out cold: wait until they come to" : talker ? "" : "None of your people are near enough to talk with them"),
			list("enslave", "Enslave", bound ? "" : "Already a slave"),
			list("release", "Release", ""),
			list("move", "Move them", M.rm_cap_cage ? "In a cage: take them out first" : bound && !RmCapNearestFree(src, M) && !M.remaster_captive_lead ? "None of your people are near enough to lead them" : ""))
		if(bound && !M.rm_cap_cage) acts += list(M.remaster_captive_lead ? list("tie", "Tie here", "") : list("lead", "Lead", RmCapNearestFree(src, M) ? "" : "None of your people are near enough to lead them"))
		if(bound && !M.rm_cap_cage)
			acts += list(list("post", "Tie to something", N[1] ? "" : "Nothing to tie them to within 10 tiles"))
			acts += list(list("stake", "Stake here", N[4] ? "" : "None of yours near them has a stake or a log of wood"))
			acts += list(list("line", "Add to a line", N[2] ? "" : "No other bound captive within 8 tiles"))
		if(bound) acts += list(M.rm_cap_cage ? list("uncage", "Take out of the cage", RmCapCageRoper(src, M) ? "" : "None of yours near the cage has a rope to tie them as they come out") : list("cage", "Put in a cage", N[3] ? "" : "No empty cage within 8 tiles"))
		. += list(list("ref"=RemasterUIRef(M), "name"=M.RmCapBareName(), "race"="[M.Race]", "state"=(bound ? (K ? "winning" : "bound") : "slave"),
			"rope"=(M.rm_cap_rope_name || ""), "ropeq"=RmRopeWord(M.rm_cap_rope_power), "loyalty"=round(M.rm_cap_loyalty),
			"risk"=(bound ? M.RmCapEscapeOdds() : 0), "next"=(bound ? max(0, round((M.rm_cap_roll_at - world.time) / 10)) : null),
			"by"=(K ? K.RemasterBareName() : ""), "x"=(MT ? MT.x : 0), "y"=(MT ? MT.y : 0), "z"=(MT ? MT.z : 0),
			"cage"=(M.rm_cap_cage ? 1 : 0), "acts"=acts))

// Ropes (and chains) for tying captives: lying in your stockpiles and zones, and carried by your people.
Player/proc/RmRopesData()
	var/stock = 0
	var/carried = 0
	var/list/seen = list()
	for(var/turf/S in RemasterStores()) for(var/obj/Items/I in range(1, S)) if(isturf(I.loc) && !seen[I] && RmRopePower(I) && RemasterMayCollect(I))
		seen[I] = 1
		stock++
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && !M.rm_cap_state)
		for(var/obj/Items/I in M) if(I.suffix != "(Equipped)" && RmRopePower(I)) carried++
	return list("stock"=stock, "carried"=carried)

// "captive" value "ref|verb[|talker ref]": win, enslave, release, tie, lead, move.
Player/proc/RmCaptiveCommand(value)
	var/list/p = splittext("[value]", "|")
	var/mob/Monsters/T = length(p) >= 1 ? RemasterUIUnit(p[1]) : null
	var/verb = length(p) >= 2 ? p[2] : null
	if(!istype(T) || T.Owner != src || !T.rm_cap_state)
		RemasterNotice("That isn't one of your captives.")
		return 0
	switch(verb)
		if("win") return RmCapWinOver(T, length(p) >= 3 ? RemasterUIUnit(p[3]) : null)
		if("enslave") return RmCapEnslave(T)
		if("release") return RmCapRelease(T)
		if("tie")
			if(T.rm_cap_state != "bound" || T.rm_cap_tied) return 0
			var/mob/Monsters/L = T.remaster_captive_lead
			T.RmCapTieHere(src)
			RemasterNotice("[L ? L.RemasterBareName() : "Your people"] tie[L ? "s" : ""] [T.RmCapBareName()] [T.rm_cap_post ? "to a post" : "up"] where they are.")
			return 1
		if("lead")
			if(T.rm_cap_state != "bound") return 0
			var/mob/Monsters/L = RmCapNearestFree(src, T)
			if(!L)
				RemasterNotice("None of your people are near enough to lead [T.RmCapBareName()].")
				return 0
			spawn(0) L.RmCapTakeRope(T, src)
			return 1
		if("attach")   // value "ref|attach|target ref" (the right-click card: another captive's line, or one of your people)
			return RmCapAttach(T, length(p) >= 3 ? RemasterUIUnit(p[3]) : null)
		if("line")
			var/mob/Monsters/X = RmCapNearestLine(src, T)
			if(!X)
				RemasterNotice("No other bound captive within 8 tiles of [T.RmCapBareName()].")
				return 0
			return RmCapAttach(T, X)
		if("post") return RmCapTieToPost(T)
		if("tieto")   // value "ref|tieto|[0x...]" (a thing) or "ref|tieto|x,y" (a tree or wall): the right-click card's Tie ... to this
			if(length(p) < 3) return 0
			var/atom/A
			if(findtext(p[3], ","))
				var/list/xy = splittext(p[3], ",")
				A = locate(text2num(xy[1]), text2num(xy[2]), T.z)
			else A = locate(p[3])
			return RmCapTieToPost(T, A)
		if("stake") return RmCapStakeHere(T)
		if("cage") return RmCapIntoCage(T, length(p) >= 3 ? locate(p[3]) : null)
		if("uncage") return RmCapTakeOut(T)
		if("move")
			RemasterNotice(T.rm_cap_state == "bound" ? "With [T.RmCapBareName()] selected, click the ground where they should go: one of yours leads them there and ties them up." : "Click where [T.RmCapBareName()] should go, or give them a job.")
			return 1
	return 0

// "Lead": the nearest of yours walks over and takes the rope; the captive follows them from then on.
mob/Monsters/proc/RmCapTakeRope(mob/Monsters/T, Player/P)
	RemasterCancelOrders()
	remaster_order_status = "Taking [T.RmCapBareName()]'s rope"
	var/until = world.time + 600
	while(src && T && T.rm_cap_state == "bound" && T.Owner == P && HP > 0 && world.time < until)
		if(remaster_active || remaster_attack || length(remaster_orders)) return
		if(z == T.z && get_dist(src, T) <= 1)
			destination = null
			T.remaster_captive_lead = src
			T.rm_cap_tied = null
			T.rm_cap_post = 0
			remaster_order_status = "Idle"
			P.RemasterNotice("[RemasterBareName()] leads [T.RmCapBareName()] on the rope: they follow wherever [RemasterBareName()] goes.")
			return
		destination = RmCapBeside(T, src)
		sleep(5)
