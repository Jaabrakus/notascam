// Cave instances. Cave mouths sit at the foot of mountains on the surface and in
// the caves. Units beside a mouth can enter: the party goes into its own private
// cave, made fresh for it in sealed rock in a corner of the Depths (z 4) - a theme
// (goblin warren, kobold den, ratman burrow, undead crypt, orc stronghold), its
// monsters, a boss and treasure at the far end, stairs back up at the start. Units
// leave by the stairs; once nobody of the party is left inside, the cave is wiped
// and its slot is free for the next one. One visit per mouth per day.

#define RM_CAVE_Z 4
#define RM_CAVE_SIZE 40            // slot size, border included
#define RM_CAVE_MOUTHS_SURFACE 28
#define RM_CAVE_MOUTHS_CAVES 10

var/list/rm_cave_slots = list(
	list(6, 6), list(50, 6), list(6, 50), list(50, 50),
	list(906, 6), list(950, 6), list(906, 50), list(950, 50),
	list(6, 906), list(50, 906), list(6, 950), list(50, 950))
var/list/rm_caves = list()          // slot index -> /datum/rm_cave
var/list/rm_cave_mouths = list()

// theme: name, soldier, boss, loot
var/list/rm_cave_themes = list(
	list("Goblin warren", /mob/Monsters/Goblin/NPC/Scout, /mob/Monsters/Goblin/NPC/Commander),
	list("Kobold den", /mob/Monsters/Kobold/NPC/Scout, /mob/Monsters/Kobold/NPC/Chieftain),
	list("Ratman burrow", /mob/Monsters/Ratman/NPC/Scout, /mob/Monsters/Ratman/NPC/King),
	list("Undead crypt", /mob/Monsters/Skeleton/NPC/Warrior, /mob/Monsters/Skeleton/NPC/Lord),
	list("Orc stronghold", /mob/Monsters/Orc/NPCOrc/Warrior, /mob/Monsters/Orc/NPCOrc/Warlord),
	// Lairs (themes 6 and 7): a great beast's home. The grown beast sleeps on its hoard at the far end, with a nest
	// of eggs; a few of its young roam. Killing it clears the lair for good, and what is left of the hoard stays
	// (rm_lair_state, saved with the world). Right-click a mouth in 3D: Enter the cave (RemasterCaveEnterOrder).
	list("Dragon's lair", /mob/Monsters/Dragon/NPCDragon, /mob/Monsters/Dragon/NPCDragon),
	list("Spider's nest", /mob/Monsters/Spider/Warrior, /mob/Monsters/Spider/Queen))
#define RM_CAVE_DRAGON 6
#define RM_CAVE_SPIDER 7
#define RM_LAIR_DRAGONS 2            // surface mouths that are a dragon's lair
#define RM_LAIR_SPIDERS 3            // and a spider's nest
var/list/rm_lair_state = list()      // saved with the world (WorldSave.dm): "x,y,z" -> list("cleared"=0/1, "hoard"=n)
var/list/rm_lair_hoard = list(
	list("/obj/Items/Ingots/GoldIngot", 5), list("/obj/Items/Ingots/SilverIngot", 2), list("/obj/Items/gems/UnCutRuby", 2),
	list("/obj/Items/gems/UnCutEmerald", 1), list("/obj/Items/gems/UnCutDiamond", 1), list("/obj/Items/ores/Gold", 2))

proc/RemasterLairKind(obj/RemasterCaveMouth/O)
	if(!istype(O)) return null
	return O.theme == RM_CAVE_DRAGON ? "dragon" : (O.theme == RM_CAVE_SPIDER ? "spider" : null)

proc/RemasterLairState(obj/RemasterCaveMouth/O)
	var/k = O.owner_key ? "own|[O.owner_key]" : "[O.x],[O.y],[O.z]"
	var/list/LS = rm_lair_state[k]
	if(!islist(LS))
		LS = O.owner_key ? list("cleared"=1, "hoard"=0, "items"=list(), "owned"=O.owner_key) : list("cleared"=0, "hoard"=(O.theme == RM_CAVE_DRAGON ? 14 : 8))
		rm_lair_state[k] = LS
	return LS

// What counts toward a hoard: gold and silver, gems (the coin floor grows with it).
proc/RemasterIsTreasure(obj/Items/X)
	if(!X) return 0
	for(var/list/L in rm_lair_hoard) if("[X.type]" == L[1]) return 1
	return findtext("[X.type]", "/gems/") || findtext("[X.type]", "GoldIngot") || findtext("[X.type]", "SilverIngot")

proc/RemasterCaveMouthName(obj/RemasterCaveMouth/O)
	var/list/TH = rm_cave_themes[O.theme]
	if(O.owner_key)
		var/list/LO = RemasterLairState(O)
		return "[LO["house"] || O.owner_key]'s lair"
	if(RemasterLairKind(O))
		var/list/LS = RemasterLairState(O)
		return "[TH[1]][LS["cleared"] ? " (cleared)" : ""]"
	return "Cave mouth: [TH[1]] ([RemasterCaveDangerName(O.danger)])"

var/list/rm_cave_loot = list(
	list("/obj/Items/ores/Iron", 1), list("/obj/Items/ores/Silver", 2), list("/obj/Items/ores/Gold", 2),
	list("/obj/Items/gems/UnCutEmerald", 2), list("/obj/Items/gems/UnCutRuby", 2), list("/obj/Items/gems/UnCutDiamond", 3),
	list("/obj/Items/Ingots/IronIngot", 1), list("/obj/Items/Ingots/SilverIngot", 2), list("/obj/Items/Ingots/GoldIngot", 3),
	list("/obj/Items/ores/Adamantium", 3))

obj/RemasterCaveMouth
	name = "Cave mouth"
	icon = 'Icons/Remastered/Runes.dmi'
	icon_state = "door_open"
	density = 0
	var/theme = 1
	var/danger = 1
	var/list/visited                // player key -> day of the last visit
	var/tmp/gathering = 0           // until when a right-click party is still walking here (no early entry)
	var/owner_key                   // a player's own lair, planted by their dragon (RemasterPlantLair)
	New()
		..()
		rm_cave_mouths += src

obj/RemasterCaveExit
	name = "Stairs up"
	icon = 'Icons/Remastered/Runes.dmi'
	icon_state = "lever_l"
	density = 0
	var/slot

datum/rm_cave
	var/slot
	var/obj/RemasterCaveMouth/mouth
	var/owner_key
	var/list/party = list()
	var/list/monsters = list()
	var/mob/Monsters/boss           // a lair's beast
	var/had_boss = 0
	var/turf/start
	var/turf/treasure
	var/obj/RemasterCaveExit/exit
	var/opened
	var/empty_since = 0

proc/RemasterCaveDangerName(d)
	return d >= 3 ? "a lair" : (d == 2 ? "deep" : "shallow")

// --- Mouths: at the foot of mountains, the same places every boot ---------------
proc/RemasterPlaceCaveMouths()
	if(length(rm_cave_mouths)) return
	rand_seed(4242)
	for(var/zz in list(1, 2))
		var/want = zz == 1 ? RM_CAVE_MOUTHS_SURFACE : RM_CAVE_MOUTHS_CAVES
		var/made = 0
		for(var/tries = 0, tries < 4000 && made < want, tries++)
			var/turf/T = locate(rand(60, world.maxx - 60), rand(60, world.maxy - 60), zz)
			if(!T || T.density || istype(T, /turf/grounds/waters) || ("Detailed" in T.vars && T.vars["Detailed"])) continue
			// natural rock only: not built or decorated walls (forts, ruins)
			var/rock = 0
			var/built = 0
			for(var/turf/N in orange(1, T))
				if(N.density && N.CanDigAt && !N.IsWall && !("Detailed" in N.vars && N.vars["Detailed"]) && !findtext("[N.type]", "Detailed")) rock++
				if(N.IsWall || findtext("[N.type]", "Detailed") || ("Detailed" in N.vars && N.vars["Detailed"])) built++
			if(rock < 3 || built) continue
			var/crowd = 0
			for(var/mob/Monsters/X in range(8, T)) crowd++
			if(crowd) continue
			var/near = 0
			for(var/obj/RemasterCaveMouth/O in rm_cave_mouths) if(O.z == zz && get_dist(O, T) < 40) near = 1
			if(near) continue
			var/obj/RemasterCaveMouth/M = new(T)
			M.theme = rand(1, length(rm_cave_themes))
			M.danger = zz == 2 ? rand(2, 3) : (prob(60) ? 1 : 2)
			var/list/TH = rm_cave_themes[M.theme]
			M.name = "Cave mouth: [TH[1]] ([RemasterCaveDangerName(M.danger)])"
			made++
	// A few surface mouths are lairs: the same ones every boot.
	var/nd = 0
	var/ns = 0
	var/i = 0
	for(var/obj/RemasterCaveMouth/O in rm_cave_mouths) if(O.z == 1)
		i++
		if(i % 9 == 3 && nd < RM_LAIR_DRAGONS)
			O.theme = RM_CAVE_DRAGON
			nd++
		else if(i % 9 == 7 && ns < RM_LAIR_SPIDERS)
			O.theme = RM_CAVE_SPIDER
			ns++
		else continue
		O.danger = 3
		O.name = RemasterCaveMouthName(O)
	rand_seed(world.timeofday)
	// players' own lairs (saved in rm_lair_state with the world)
	var/no = 0
	for(var/k in rm_lair_state)
		var/list/LO = rm_lair_state[k]
		if(!islist(LO) || !LO["owned"] || !LO["at"]) continue
		var/list/p = splittext("[LO["at"]]", ",")
		var/turf/T = length(p) == 3 ? locate(text2num(p[1]), text2num(p[2]), text2num(p[3])) : null
		if(!T) continue
		var/obj/RemasterCaveMouth/N = new(T)
		N.theme = RM_CAVE_DRAGON
		N.danger = 3
		N.owner_key = LO["owned"]
		N.name = RemasterCaveMouthName(N)
		no++
	world.log << "Cave mouths placed: [length(rm_cave_mouths)] ([nd] dragon lairs, [ns] spider nests, [no] players' lairs)"

// world/New: this file's part is step RmChainWorldNew_Instances in Code/Remastered/Chains/WorldNew.dm

// --- Making a cave in a slot ----------------------------------------------------
proc/RemasterCaveFreeSlot()
	for(var/i = 1, i <= length(rm_cave_slots), i++) if(!rm_caves["[i]"]) return i
	return 0

turf/var/tmp/remaster_hoard = 0     // 1-3: gold coins heaped on this cave floor (a dragon's lair)

proc/RemasterCaveTurf(turf/T, floor)
	T.remaster_hoard = 0
	T.icon = 'Cave.dmi'
	T.icon_state = floor ? "CaveFloor" : "CaveWall"
	T.name = floor ? "cavefloor" : "cave wall"
	T.density = !floor
	T.opacity = !floor
	T.CanDigAt = floor ? 0 : 1
	T.IsWall = 0
	if("Detailed" in T.vars) T.vars["Detailed"] = 0

// Cellular cave in the slot interior; returns the floor tiles of the largest region.
proc/RemasterCaveCarve(x0, y0)
	var/n = RM_CAVE_SIZE - 2
	var/list/G = new /list(n * n)
	for(var/i = 1, i <= n * n, i++) G[i] = prob(46)
	for(var/step = 1, step <= 4, step++)
		var/list/H = new /list(n * n)
		for(var/y = 1, y <= n, y++)
			for(var/x = 1, x <= n, x++)
				var/w = 0
				for(var/dy = -1, dy <= 1, dy++)
					for(var/dx = -1, dx <= 1, dx++)
						var/xx = x + dx
						var/yy = y + dy
						if(xx < 1 || yy < 1 || xx > n || yy > n) w++
						else if(G[(yy - 1) * n + xx]) w++
				H[(y - 1) * n + x] = w >= 5
		G = H
	// keep the largest open region
	var/list/seen = new /list(n * n)
	var/list/best = list()
	for(var/i = 1, i <= n * n, i++)
		if(G[i] || seen[i]) continue
		var/list/region = list()
		var/list/q = list(i)
		seen[i] = 1
		while(length(q))
			var/c = q[length(q)]
			q.len--
			region += c
			var/cx = ((c - 1) % n) + 1
			var/cy = round((c - 1) / n) + 1
			for(var/list/d in list(list(1, 0), list(-1, 0), list(0, 1), list(0, -1)))
				var/xx = cx + d[1]
				var/yy = cy + d[2]
				if(xx < 1 || yy < 1 || xx > n || yy > n) continue
				var/j = (yy - 1) * n + xx
				if(!G[j] && !seen[j])
					seen[j] = 1
					q += j
		if(length(region) > length(best)) best = region
	var/list/floors = list()
	var/list/open = list()
	for(var/c in best) open["[c]"] = 1
	for(var/y = 1, y <= n, y++)
		for(var/x = 1, x <= n, x++)
			var/turf/T = locate(x0 + x, y0 + y, RM_CAVE_Z)
			if(!T) continue
			var/f = open["[(y - 1) * n + x]"] ? 1 : 0
			RemasterCaveTurf(T, f)
			if(f) floors += T
	// a sealed border nobody can dig through
	for(var/x = 0, x < RM_CAVE_SIZE, x++)
		for(var/y = 0, y < RM_CAVE_SIZE, y++)
			if(x && y && x < RM_CAVE_SIZE - 1 && y < RM_CAVE_SIZE - 1) continue
			var/turf/B = locate(x0 + x, y0 + y, RM_CAVE_Z)
			if(B && !istype(B, /turf/grounds/NoDig)) new /turf/grounds/NoDig(B)
	return floors

// A lair remembers: the beast dead means cleared for good; the hoard is what is left at the far end.
proc/RemasterLairRemember(datum/rm_cave/C)
	if(!C || !C.mouth || !RemasterLairKind(C.mouth)) return
	var/list/LS = RemasterLairState(C.mouth)
	if(C.mouth.owner_key)
		// a player's lair keeps everything left lying in it
		var/list/S = rm_cave_slots[C.slot]
		var/list/keep = list()
		var/n = 0
		for(var/turf/T in block(locate(S[1], S[2], RM_CAVE_Z), locate(S[1] + RM_CAVE_SIZE - 1, S[2] + RM_CAVE_SIZE - 1, RM_CAVE_Z)))
			for(var/obj/Items/X in T)
				if(length(keep) >= 300) break
				keep += "[X.type]"
				if(RemasterIsTreasure(X)) n++
		LS["items"] = keep
		LS["hoard"] = n
		C.mouth.name = RemasterCaveMouthName(C.mouth)
		return
	if(C.had_boss && (!C.boss || C.boss.HP <= 0 || C.boss.GoingToDie || !C.boss.loc)) LS["cleared"] = 1
	if(C.treasure)
		var/n = 0
		for(var/obj/Items/X in range(1, C.treasure)) for(var/list/L in rm_lair_hoard) if("[X.type]" == L[1]) n++
		LS["hoard"] = n
	C.mouth.name = RemasterCaveMouthName(C.mouth)

// A lair's beast: the boss is grown and keeps a nest of eggs; the young are hatchlings. Spiders get an owner
// of their own, as the NPC races have, so they count as wild.
proc/RemasterLairBeast(mob/Monsters/E, theme, boss)
	if(theme == RM_CAVE_DRAGON)
		E.Age = boss ? rand(80, 150) : rand(3, 12)
	else
		E.Owner = "{NPC Spiders}"
		E.name = "{NPC Spiders} [boss ? "Spider Queen" : "Spider"]"
		if(boss) E.Age = 60
	if(boss) RmMakeNest(E, theme == RM_CAVE_DRAGON ? 2 : 3)

proc/RemasterCaveWipe(datum/rm_cave/C)
	RemasterLairRemember(C)
	var/list/S = rm_cave_slots[C.slot]
	for(var/turf/T in block(locate(S[1], S[2], RM_CAVE_Z), locate(S[1] + RM_CAVE_SIZE - 1, S[2] + RM_CAVE_SIZE - 1, RM_CAVE_Z)))
		for(var/atom/movable/A in T)
			if(istype(A, /mob/Monsters))
				var/mob/Monsters/M = A
				if(istype(M.Owner, /Player)) continue   // never delete a player's unit
			if(ismob(A) && A:key) continue
			del(A)
	rm_caves -= "[C.slot]"

// --- Entering and leaving --------------------------------------------------------
Player/proc/RemasterCaveEnter(mob/Monsters/M)
	var/obj/RemasterCaveMouth/O
	for(var/obj/RemasterCaveMouth/X in range(1, M)) O = X
	if(!O) return 0
	if(!O.visited) O.visited = list()
	var/own = O.owner_key && RemasterAlliedKeys(O.owner_key, key)
	if(O.owner_key && !own)
		RemasterNotice("This is [O.name]: only its owner and their allies may go in.")
		return 0
	if(!own && O.visited[key] && O.visited[key] >= remaster_days)
		RemasterNotice("Your people already went down this cave today. Try again tomorrow.")
		return 0
	var/slot = RemasterCaveFreeSlot()
	if(!slot)
		RemasterNotice("Every cave is busy right now. Try again in a little while.")
		return 0
	var/list/party = list()
	for(var/mob/Monsters/U in range(2, O)) if(U.Owner == src && U.HP > 0 && !U.GoingToDie && length(party) < 8) party += U
	if(!length(party)) return 0
	var/datum/rm_cave/C = new
	C.slot = slot
	C.mouth = O
	C.owner_key = key
	C.opened = world.time
	rm_caves["[slot]"] = C
	var/list/S = rm_cave_slots[slot]
	var/list/floors = RemasterCaveCarve(S[1], S[2])
	if(length(floors) < 30)
		RemasterCaveWipe(C)
		RemasterNotice("The cave collapsed before you could go in. Try again.")
		return 0
	// start near the slot's lower left, treasure at the far end
	var/turf/start
	var/bd = 1e9
	for(var/turf/T in floors)
		var/d = (T.x - S[1]) + (T.y - S[2])
		if(d < bd)
			bd = d
			start = T
	C.start = start
	var/turf/far
	bd = -1
	for(var/turf/T in floors)
		var/d = get_dist(T, start)
		if(d > bd)
			bd = d
			far = T
	C.treasure = far
	C.exit = new /obj/RemasterCaveExit(start)
	C.exit.slot = slot
	// monsters by theme and danger, away from the start
	var/list/TH = rm_cave_themes[O.theme]
	var/lair = RemasterLairKind(O)
	var/list/LS = lair ? RemasterLairState(O) : null
	var/count = 2 + O.danger * 2 + round(length(party) / 2)
	if(lair) count = O.owner_key ? 0 : (LS["cleared"] ? 1 : (O.theme == RM_CAVE_DRAGON ? rand(0, 2) : 3 + rand(0, 2)))
	var/list/spots = list()
	for(var/turf/T in floors) if(get_dist(T, start) >= 8) spots += T
	for(var/i = 1, i <= count && length(spots), i++)
		var/soldier = TH[2]
		var/mob/Monsters/E = new soldier(pick(spots))
		E.HomeLoc = E.loc
		if(lair) RemasterLairBeast(E, O.theme, 0)
		C.monsters += E
	if(lair ? (!LS["cleared"] && !O.owner_key) : O.danger >= 2)
		var/boss = TH[3]
		var/mob/Monsters/Bs = new boss(far)
		Bs.HomeLoc = far
		if(lair)
			RemasterLairBeast(Bs, O.theme, 1)
			C.boss = Bs
			C.had_boss = 1
		C.monsters += Bs
	if(lair && O.owner_key)
		// a player's lair: everything they left in it, round the far end
		var/list/near = list(far)
		for(var/turf/T in range(3, far)) if(T in floors) near += T
		for(var/t in LS["items"])
			var/path = text2path("[t]")
			if(path) new path(pick(near))
	else if(lair)
		// the hoard: what is left of it lies round the beast
		var/list/near = list(far)
		for(var/turf/T in orange(1, far)) if(T in floors) near += T
		for(var/i = 1, i <= LS["hoard"], i++)
			var/list/L = pick(rm_lair_hoard)
			var/path = text2path(L[1])
			if(path) new path(pick(near))
	// A dragon's lair is floored with its hoard (3D draws it from remaster_hoard, View3D.dm): heaps of coins piled up
	// against the cave walls, and a thin scatter over the open floor between, where the beast and visitors walk and
	// stand out against it; as high as the hoard allows.
	if(lair == "dragon")
		var/hv = LS["hoard"] || 0
		var/cap = hv >= 9 ? 3 : (hv >= 4 ? 2 : (hv >= 1 ? 1 : 0))
		if(cap) for(var/turf/T in floors)
			var/rock = 0
			for(var/turf/N in orange(1, T)) if(N.density) rock++
			T.remaster_hoard = min(cap, rock >= 3 ? 3 : (rock ? 2 : 1))
	else
		// treasure: better with danger
		for(var/i = 1, i <= 2 + O.danger * 2, i++)
			var/list/L = pick(rm_cave_loot)
			if(L[2] > O.danger + 1) continue
			var/path = text2path(L[1])
			if(path) new path(far)
	// in they go
	for(var/mob/Monsters/U in party)
		U.RemasterCancelOrders()
		U.destination = null
		var/turf/T = pick(floors)
		for(var/turf/X in range(2, start)) if(X in floors) T = X
		U.loc = T
		C.party += U
	if(!own) O.visited[key] = remaster_days
	loc = start
	var/text = own ? "[length(party)] went into [O.name]. [LS["hoard"]] treasure[LS["hoard"] == 1 ? "" : "s"] in the hoard; whatever you leave inside stays." : lair ? "[length(party)] went down into the [TH[1]]. [LS["cleared"] ? "The beast is dead; what is left of its hoard lies at the far end." : "The beast sleeps on its hoard at the far end."] The stairs lead back up." : "[length(party)] went down into the [TH[1]] ([RemasterCaveDangerName(O.danger)]). Treasure waits at the far end. The stairs lead back up."
	RemasterNotice(text)
	RemasterLog(text, "fight", start)
	return 1

proc/RemasterCaveAt(turf/T)
	if(!T || T.z != RM_CAVE_Z) return null
	for(var/k in rm_caves)
		var/datum/rm_cave/C = rm_caves[k]
		var/list/S = rm_cave_slots[C.slot]
		if(T.x >= S[1] && T.y >= S[2] && T.x < S[1] + RM_CAVE_SIZE && T.y < S[2] + RM_CAVE_SIZE) return C
	return null

Player/proc/RemasterCaveLeave(mob/Monsters/M)
	var/datum/rm_cave/C = RemasterCaveAt(M.loc)
	if(!C || get_dist(M, C.exit) > 1) return 0
	var/turf/back = C.mouth ? C.mouth.loc : null
	if(!back) return 0
	var/n = 0
	for(var/mob/Monsters/U in range(3, C.exit)) if(U.Owner == src && U.HP > 0)
		var/turf/T = back
		for(var/turf/X in orange(1, back)) if(!X.density) T = X
		U.RemasterCancelOrders()
		U.destination = null
		U.loc = T
		C.party -= U
		n++
	loc = back
	RemasterNotice("[n] climbed back out of the cave.")
	RemasterLog("[n] came back up from the cave", "good", back)
	return n

// Every few seconds: wipe caves nobody of their party is in any more.
proc/RemasterCaveTick()
	// Mouths work like ramps: a unit sent onto one takes its party down.
	for(var/obj/RemasterCaveMouth/O in rm_cave_mouths) if(O.loc && O.gathering < world.time)
		for(var/mob/Monsters/U in O.loc) if(istype(U.Owner, /Player) && U.HP > 0 && !U.GoingToDie)
			var/Player/P = U.Owner
			if(!(O.visited && O.visited[P.key] && O.visited[P.key] >= P.remaster_days)) P.RemasterCaveEnter(U)
			break
	for(var/k in rm_caves.Copy())
		var/datum/rm_cave/C = rm_caves[k]
		// a dragon asleep in its own lair heals faster, more so on a big hoard
		if(C.mouth && C.mouth.owner_key)
			var/list/LH = RemasterLairState(C.mouth)
			for(var/mob/Monsters/U in C.party) if(U && U.Race == "Dragon" && U.HP > 0 && U.HP < U.MAXHP && RemasterCaveAt(U.loc) == C)
				U.HP = min(U.MAXHP, U.HP + max(1, round(U.MAXHP * (0.01 + 0.002 * min(20, LH["hoard"] || 0)))))
		var/inside = 0
		for(var/mob/Monsters/U in C.party) if(U && U.HP > 0 && RemasterCaveAt(U.loc) == C) inside++
		if(inside)
			C.empty_since = 0
			continue
		if(!C.empty_since) C.empty_since = world.time
		else if(world.time - C.empty_since > 300) RemasterCaveWipe(C)

var/rm_cave_loop = 0
proc/RemasterCaveLoop()
	while(1)
		sleep(20)
		RemasterCaveTick()

// For the unit frame: a mouth beside the unit, or the stairs inside.
Player/proc/RemasterCaveData(mob/Monsters/M)
	if(!M) return null
	var/datum/rm_cave/C = RemasterCaveAt(M.loc)
	if(C)
		var/left = 0
		for(var/mob/Monsters/E in C.monsters) if(E && E.HP > 0 && !E.GoingToDie) left++
		var/list/TH = rm_cave_themes[C.mouth ? C.mouth.theme : 1]
		return list("inside"=1, "name"=TH[1], "foes"=left, "exit"=(get_dist(M, C.exit) <= 1),
			"loot"=(C.treasure ? length(C.treasure.contents) : 0), "lootDist"=(C.treasure ? get_dist(M, C.treasure) : null))
	for(var/obj/RemasterCaveMouth/O in range(1, M))
		var/list/TH = rm_cave_themes[O.theme]
		var/mine = O.owner_key && RemasterAlliedKeys(O.owner_key, key)
		var/ready = mine || (!O.owner_key && !(O.visited && O.visited[key] && O.visited[key] >= remaster_days))
		if(O.owner_key)
			var/n0 = 0
			for(var/mob/Monsters/U in range(2, O)) if(U.Owner == src && U.HP > 0) n0++
			return list("inside"=0, "name"=O.name, "danger"=0, "dangerName"=(mine ? "your lair" : "not yours"), "ready"=mine, "party"=min(n0, 8))
		var/n = 0
		for(var/mob/Monsters/U in range(2, O)) if(U.Owner == src && U.HP > 0) n++
		return list("inside"=0, "name"=TH[1], "danger"=O.danger, "dangerName"=RemasterCaveDangerName(O.danger), "ready"=ready, "party"=min(n, 8))
	// no mouth here: a dragon of yours beside rock may make its lair
	if(M.Owner == src && RemasterLairSpot(M)) return list("inside"=0, "plant"=1, "moves"=(rm_lair_state["own|[key]"] ? 1 : 0))
	return null

// A grown dragon of yours, standing beside natural rock with no cave mouth near, can make its lair there: a cave
// mouth of your own (the cave box or the right-click card: "Make our lair here"). One lair per player; making it
// again moves the way in, and the hoard goes with it.
proc/RemasterLairSpot(mob/Monsters/M)
	if(!M || M.Race != "Dragon" || !istype(M.Owner, /Player) || !isturf(M.loc) || M.z > 2 || M.HP <= 0) return null
	if(RmBeastSize(M, "dragon") < 1.5) return null
	var/turf/T = M.loc
	if(T.density || T.z == RM_CAVE_Z) return null
	var/rock = 0
	for(var/turf/N in orange(1, T)) if(RemasterIsMountain(N) && N.CanDigAt && !N.IsWall) rock++
	if(rock < 2) return null
	for(var/obj/RemasterCaveMouth/O in range(6, T)) return null
	return T

Player/proc/RemasterPlantLair(mob/Monsters/M)
	var/turf/T = RemasterLairSpot(M)
	if(!T || M.Owner != src) return 0
	for(var/obj/RemasterCaveMouth/O in rm_cave_mouths.Copy()) if(O.owner_key == key)
		rm_cave_mouths -= O
		del(O)
	var/obj/RemasterCaveMouth/N = new(T)
	N.theme = RM_CAVE_DRAGON
	N.danger = 3
	N.owner_key = key
	var/list/LS = RemasterLairState(N)
	LS["house"] = RemasterHouse() || "[name]"
	LS["at"] = "[T.x],[T.y],[T.z]"
	N.name = RemasterCaveMouthName(N)
	RemasterNotice("[M.RemasterBareName()] made its lair here. Treasure left inside stays; the floor fills with gold as the hoard grows, and the dragon heals faster asleep on it.")
	RemasterLog("[M.RemasterBareName()] made [N.name]", "good", T)
	return 1

// Right-click a cave mouth in 3D (remastered.html, "Enter the cave"): the selected units walk to it and go
// down together once they are all there (or after a minute, with whoever made it). value: "x|y|ref".
Player/proc/RemasterCaveEnterOrder(value)
	var/list/parts = splittext("[value]", "|")
	// from the 3D card with a client; by position alone without one (tests)
	var/atom/A = client ? Remaster3DTarget(parts) : (parts.len >= 2 ? locate(text2num(parts[1]), text2num(parts[2]), z) : null)
	var/obj/RemasterCaveMouth/O = istype(A, /obj/RemasterCaveMouth) ? A : null
	if(!O && A)
		var/turf/T = isturf(A) ? A : A.loc
		if(T) for(var/obj/RemasterCaveMouth/X in T) O = X
	if(!O) return 0
	if(O.visited && O.visited[key] && O.visited[key] >= remaster_days)
		RemasterNotice("Your people already went down this cave today. Try again tomorrow.")
		return 0
	var/list/party = list()
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0 && !M.GoingToDie && !M.Wagon && M.z == O.z && length(party) < 8) party += M
	if(!length(party))
		RemasterNotice("Select units to send into the cave.")
		return 0
	var/list/spots = list()
	for(var/turf/T in orange(1, O)) if(!T.density) spots += T
	if(!length(spots)) spots += O.loc
	O.gathering = world.time + 900
	var/i = 0
	for(var/mob/Monsters/M in party)
		M.RemasterCancelOrders()
		M.destination = spots[(i++ % length(spots)) + 1]
		M.remaster_order_status = "Going to the [O.name]"
	RemasterNotice("[length(party)] head for the [O.name].")
	spawn(0) RemasterCaveGather(O, party)
	return 1

Player/proc/RemasterCaveGather(obj/RemasterCaveMouth/O, list/party)
	var/started = world.time
	while(O && O.loc && world.time - started < 900)
		sleep(5)
		var/near = 0
		var/alive = 0
		for(var/mob/Monsters/M in party) if(M && M.HP > 0 && !M.GoingToDie)
			alive++
			if(M.z == O.z && get_dist(M, O) <= 2) near++
		if(!alive) break
		if(near == alive || (near && world.time - started > 600))
			O.gathering = 0
			var/mob/Monsters/lead
			for(var/mob/Monsters/M in party) if(M && M.HP > 0 && M.z == O.z && get_dist(M, O) <= 2)
				lead = M
				break
			if(lead) RemasterCaveEnter(lead)
			return
	if(O) O.gathering = 0

// value: "unitref|enter" / "unitref|leave"
Player/proc/RemasterCaveCommand(value)
	var/list/p = splittext("[value]", "|")
	if(p.len < 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return 0
	if(!rm_cave_loop)
		rm_cave_loop = 1
		spawn(0) RemasterCaveLoop()
	if(p[2] == "plant") return RemasterPlantLair(M)
	if(p[2] == "enter") return RemasterCaveEnter(M)
	if(p[2] == "leave") return RemasterCaveLeave(M)
	return 0
