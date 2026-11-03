// Fishing, RuneScape style. Fishing spots bubble on the shore: shallow (small ponds),
// river, deep (big lakes), swamp and cave water. Each kind takes certain tools and
// holds certain fish, each with a Fishing level to catch it:
//   shallow   net: Shrimp 1, Anchovy 15         rod: Sardine 5, Herring 10
//   river     rod: Trout 20, Pike 25, Salmon 30
//   deep      cage: Lobster 40                  harpoon: Tuna 35, Swordfish 50, Shark 76
//   swamp     net: Tropical fish 12, Blowfish 22
//   cave      rod: Cave fish 18, Cave eel 38
// A unit fishes a spot from the shore beside it (click the spot, or the right-click
// list; Fisher workers find spots themselves). Every 3 seconds it tries for the best
// fish its level allows first: 30% plus 2% per level above that fish's requirement
// (15% to 85%). Bigger fish give more Fishing experience and more meat. Without a tool
// only shallow water can be fished, by hand, for shrimp. Spots drift along the shore
// every few minutes. Tools: Fishing Rod, Fishing Net and Lobster Cage at the
// Carpentry, Harpoon at the Forge.

#define RM_FISH_EVERY 30
#define RM_FISH_SPOTS 160
#define RM_FISH_MOVE 3000

// method -> fish: list(name, level, weight, icon_state)
var/list/rm_fish = list(
	"shallow"=list("net"=list(list("Shrimp", 1, 2, "Fish"), list("Anchovy", 15, 2, "Fish")), "rod"=list(list("Sardine", 5, 3, "Fish"), list("Herring", 10, 3, "Fish")), "hand"=list(list("Shrimp", 1, 2, "Fish"))),
	"river"=list("rod"=list(list("Trout", 20, 4, "Fish"), list("Pike", 25, 5, "Fish"), list("Salmon", 30, 6, "Fish"))),
	"deep"=list("cage"=list(list("Lobster", 40, 6, "Fish")), "harpoon"=list(list("Tuna", 35, 10, "Fish"), list("Swordfish", 50, 14, "Fish"), list("Shark", 76, 30, "Fish"))),
	"swamp"=list("net"=list(list("Tropical fish", 12, 3, "TFish"), list("Blowfish", 22, 4, "BlowFish")), "hand"=list(list("Tropical fish", 12, 3, "TFish"))),
	"cave"=list("rod"=list(list("Cave fish", 18, 4, "CaveFish"), list("Cave eel", 38, 6, "CaveFish"))))
// RuneScape XP per catch
var/list/rm_fish_xp = list("Shrimp"=10, "Sardine"=20, "Herring"=30, "Tropical fish"=35, "Anchovy"=40, "Cave fish"=45, "Trout"=50,
	"Blowfish"=55, "Pike"=60, "Salmon"=70, "Tuna"=80, "Lobster"=90, "Cave eel"=95, "Swordfish"=100, "Shark"=110)
// best first
var/list/rm_fish_methods = list("harpoon", "cage", "rod", "net", "hand")
var/list/rm_fish_spots = list()

obj/Items/RemasterTools
	// its values: art/items/catalogue.json row remastertools (export_items.py writes ItemData.dm)
	var/remaster_method
	FishingRod
		// its values: art/items/catalogue.json row remastertools.fishingrod (export_items.py writes ItemData.dm)
	FishingNet
		// its values: art/items/catalogue.json row remastertools.fishingnet (export_items.py writes ItemData.dm)
	LobsterCage
		// its values: art/items/catalogue.json row remastertools.lobstercage (export_items.py writes ItemData.dm)
	Harpoon
		// its values: art/items/catalogue.json row remastertools.harpoon (export_items.py writes ItemData.dm)

obj/RemasterFishSpot
	name = "Fishing spot"
	icon = 'Icons/Remastered/Runes.dmi'
	icon_state = "plate"
	density = 0
	layer = 2.1
	var/kind = "shallow"
	var/tmp/move_at = 0
	New()
		..()
		rm_fish_spots += src
		move_at = world.time + rand(RM_FISH_MOVE, RM_FISH_MOVE * 2)
	Del()
		rm_fish_spots -= src
		..()

proc/RemasterFishName(kind)
	return list("shallow"="Shallow water", "river"="River", "deep"="Deep water", "swamp"="Swamp", "cave"="Cave pool")[kind]

proc/RemasterIsFishWater(turf/T)
	return T && ("CanFish" in T.vars) && T.vars["CanFish"]

// A shore tile: fishing water with walkable land beside it.
proc/RemasterShoreLand(turf/T)
	for(var/d in list(NORTH, SOUTH, EAST, WEST))
		var/turf/N = get_step(T, d)
		if(N && !N.density && !RemasterIsFishWater(N)) return N
	return null

proc/RemasterFishKindAt(turf/T)
	if(("CaveWater" in T.vars) && T.vars["CaveWater"]) return "cave"
	if("[T.icon]" == "Icons/Swamp.dmi" || findtext("[T.icon]", "Swamp") || findtext(lowertext("[T.name]"), "swamp")) return "swamp"
	// how much water around (a shore tile sees about half of its lake)
	var/n = 0
	for(var/turf/X in range(6, T)) if(RemasterIsFishWater(X)) n++
	if(n < 25) return "shallow"
	if(n < 70) return "river"
	return "deep"

proc/RemasterPlaceSpot(turf/T)
	if(!T || !RemasterIsFishWater(T) || !RemasterShoreLand(T)) return null
	for(var/obj/RemasterFishSpot/O in range(3, T)) return null
	var/obj/RemasterFishSpot/S = new(T)
	S.kind = RemasterFishKindAt(T)
	S.name = "Fishing spot ([lowertext(RemasterFishName(S.kind))])"
	RmJzFishSpotMoved(S)     // a fishing zone's waiting fishers (Jobs.dm)
	return S

// At boot: spots scattered over the world's waters.
proc/RemasterPlaceFishSpots()
	rand_seed(5151)
	for(var/tries = 0, tries < 40000 && length(rm_fish_spots) < RM_FISH_SPOTS, tries++)
		var/turf/T = locate(rand(2, world.maxx - 1), rand(2, world.maxy - 1), pick(1, 1, 1, 2))
		if(RemasterIsFishWater(T)) RemasterPlaceSpot(T)
	rand_seed(world.timeofday)
	world.log << "Fishing spots placed: [length(rm_fish_spots)]"

// Every settlement gets spots on the shores near it.
Player/proc/RemasterFishSpotsNear()
	var/turf/C = RemasterProgressCenter()
	if(!C) return
	var/n = 0
	for(var/obj/RemasterFishSpot/S in rm_fish_spots) if(S.z == C.z && get_dist(S, C) <= 30) n++
	if(n >= 3) return
	for(var/turf/T in range(30, C)) if(RemasterIsFishWater(T) && RemasterShoreLand(T) && prob(8))
		if(RemasterPlaceSpot(T) && ++n >= 3) return

// --- Fishing ---------------------------------------------------------------------------
mob/Monsters/var/tmp
	obj/RemasterFishSpot/remaster_fish_spot
	remaster_fish_at = 0

// The best way this unit can fish the spot: a tool it carries (or bare hands) with at
// least one fish its level allows. levels_only: ignore the level (what tools fit).
mob/Monsters/proc/RemasterFishMethod(obj/RemasterFishSpot/S, levels_only = 0)
	var/list/M = rm_fish[S.kind]
	var/list/have = list("hand"=1)
	for(var/obj/Items/RemasterTools/T in src) if(T.remaster_method) have[T.remaster_method] = 1
	var/lvl = RemasterSkillLevel(FishingSkill)
	for(var/m in rm_fish_methods) if(M[m] && have[m])
		if(levels_only) return m
		for(var/list/F in M[m]) if(lvl >= F[2]) return m
	return null

// The lowest level that catches anything at this spot with the tools carried.
mob/Monsters/proc/RemasterFishNeed(obj/RemasterFishSpot/S)
	var/list/M = rm_fish[S.kind]
	var/best
	for(var/obj/Items/RemasterTools/T in src) if(M[T.remaster_method])
		var/list/F = M[T.remaster_method][1]
		if(!best || F[2] < best[2]) best = F
	return best

proc/RemasterFishTools(kind)
	. = list()
	for(var/m in rm_fish[kind]) if(m != "hand") . += list("rod"="a fishing rod", "net"="a fishing net", "cage"="a lobster cage", "harpoon"="a harpoon")[m]

// One try for a fish. Returns the catch's name, or null.
mob/Monsters/proc/RemasterFishTry(obj/RemasterFishSpot/S)
	var/method = RemasterFishMethod(S)
	if(!method) return null
	var/list/F = rm_fish[S.kind][method]
	var/lvl = RemasterSkillLevel(FishingSkill)
	for(var/i = length(F), i >= 1, i--)
		var/list/fish = F[i]
		if(lvl < fish[2]) continue
		var/odds = clamp(30 + 2 * (lvl - fish[2]), 15, 85)
		if(method == "hand") odds = round(odds / 2)
		if(prob(odds)) return fish
	return null

mob/Monsters/proc/RemasterFishCatch(list/fish, obj/RemasterFishSpot/S)
	var/mob/Body/B = new(loc)
	B.icon = 'cave.dmi'
	B.icon_state = fish[4]
	B.name = fish[1]
	B.Race = "Fish"
	B.weight = fish[3]
	spawn(3000) if(B && isnull(B.suffix) && isturf(B.loc)) del(B)     // fish keep five minutes
	RemasterAddXP("Fishing", rm_fish_xp[fish[1]] || 10)     // RuneScape XP per fish
	GainEXP(2 + round(fish[2] / 10))
	RemasterHitAt(x, y, z, 0, "+[fish[1]]", src, Owner)
	RemasterSpecialFx("catch", src, S.x, S.y, x, y, null)

// Called every order tick for a unit with a spot (Orders.dm chain).
mob/Monsters/proc/RemasterFishTick()
	var/obj/RemasterFishSpot/S = remaster_fish_spot
	if(!S) return 0
	if(!S.loc || S.z != z)
		remaster_fish_spot = null
		remaster_work_status = "The fish moved on"
		return 0
	if(get_dist(src, S) > 1)
		var/turf/L = RemasterShoreLand(S.loc)
		if(L) destination = L
		remaster_work_status = "Walking to the [lowertext(S.name)]"
		return 1
	destination = null
	dir = get_dir(src, S)
	var/method = RemasterFishMethod(S)
	if(!method)
		var/list/need = RemasterFishNeed(S)
		if(need) remaster_work_status = "Fishing level [need[2]] needed here ([need[1]])"
		else remaster_work_status = "Needs [jointext(RemasterFishTools(S.kind), " or ")] for [lowertext(RemasterFishName(S.kind))]"
		return 1
	remaster_work_status = "Fishing ([method]) · level [RemasterSkillLevel(FishingSkill)]"
	if(world.time < remaster_fish_at) return 1
	remaster_fish_at = world.time + RM_FISH_EVERY
	RemasterSpecialFx("fish", src, x, y, S.x, S.y, method)
	var/list/fish = RemasterFishTry(S)
	if(fish) RemasterFishCatch(fish, S)
	return 1

// An order on a spot: the selected units fish it.
Player/proc/RemasterFishOrder(atom/A)
	var/turf/T = RemasterTurf(A)
	var/obj/RemasterFishSpot/S = istype(A, /obj/RemasterFishSpot) ? A : null
	if(!S && T) for(var/obj/RemasterFishSpot/X in T) S = X
	if(!S) return 0
	var/n = 0
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && (M in UnitList) && M.HP > 0 && !M.Wagon && !RemasterIsSiege(M))
		M.RemasterCancelOrders()
		M.remaster_fish_spot = S
		M.remaster_fish_at = world.time + 10
		n++
	if(n)
		var/mob/Monsters/F = Selected[1]
		var/method = istype(F) ? F.RemasterFishMethod(S) : null
		RemasterNotice("[n] fishing the [lowertext(S.name)][method ? "" : ": they need [jointext(RemasterFishTools(S.kind), " or ")]"].")
	return n

// Spots drift along the shore now and then; settlements are kept supplied.
proc/RemasterFishLoop()
	while(1)
		sleep(100)
		for(var/obj/RemasterFishSpot/S in rm_fish_spots.Copy()) if(world.time >= S.move_at)
			S.move_at = world.time + rand(RM_FISH_MOVE, RM_FISH_MOVE * 2)
			for(var/tries = 1, tries <= 12, tries++)
				var/turf/T = locate(clamp(S.x + rand(-8, 8), 2, world.maxx - 1), clamp(S.y + rand(-8, 8), 2, world.maxy - 1), S.z)
				if(T == S.loc || !RemasterIsFishWater(T) || !RemasterShoreLand(T)) continue
				var/clear = 1
				for(var/obj/RemasterFishSpot/O in range(3, T)) if(O != S) clear = 0
				if(!clear) continue
				S.loc = T
				S.kind = RemasterFishKindAt(T)
				S.name = "Fishing spot ([lowertext(RemasterFishName(S.kind))])"
				RmJzFishSpotMoved(S)     // a fishing zone's waiting fishers (Jobs.dm)
				break
		for(var/Player/P in world) if(P.client) P.RemasterFishSpotsNear()

// world/New: this file's part is step RmChainWorldNew_Fishing in Code/Remastered/Chains/WorldNew.dm

// --- Tools at the stations ----------------------------------------------------------------
mob/Monsters/proc/RemasterCraftFishTool(mob/WorkShops/W, Player/P, id)
	if(!(src in range(1, W)) || !RemasterManualHandoff(P)) return
	var/list/D = list("rod"=list(/obj/Items/RemasterTools/FishingRod, /obj/Items/woods/wood, 1, "WoodCraftingSkill"),
		"net"=list(/obj/Items/RemasterTools/FishingNet, /obj/Items/woods/wood, 1, "WoodCraftingSkill"),
		"cage"=list(/obj/Items/RemasterTools/LobsterCage, /obj/Items/woods/wood, 2, "WoodCraftingSkill"),
		"harpoon"=list(/obj/Items/RemasterTools/Harpoon, /obj/Items/Ingots/IronIngot, 1, "MetalCraftingSkill"),
		"climbing"=list(/obj/Items/RemasterTools/ClimbingGear, /obj/Items/Ingots/IronIngot, 1, "MetalCraftingSkill"),    // Mountains.dm
		"chains"=list(/obj/Items/RemasterTools/IronChains, /obj/Items/Ingots/IronIngot, 2, "MetalCraftingSkill"),    // Taming.dm
		"runestone"=list(/obj/Items/RmRuneStone, /obj/Items/gems, 1, "JewlCraftingSkill"))[id]    // MagicGear.dm
	if(!D) return
	var/list/mats = list()
	for(var/obj/Items/X in src) if(istype(X, D[2]) && X.suffix != "(Equipped)") mats += X
	if(length(mats) < D[3])
		P << "[src] needs [D[3]] [D[2] == /obj/Items/woods/wood ? "wood" : D[2] == /obj/Items/gems ? "gem" : "iron ingot"] for that."
		return
	for(var/i = 1, i <= D[3], i++)
		var/obj/Items/X = mats[i]
		weight -= X.weight
		del(X)
	if(!prob(RemasterCraftOdds(vars[D[4]])))
		P << "Failed!"
		vars[D[4]] += 1
		return
	var/path = D[1]
	var/obj/Items/T = new path(loc)
	vars[D[4]] += 1
	P << "[src] makes a [lowertext(T.name)]."
