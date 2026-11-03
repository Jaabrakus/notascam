// Biomes. Regions laid over the original map at boot, the same every boot:
//  jungle   - grassland near water: dense trees, wild grapes and tomatoes
//  mesa     - desert at the foot of mountains: red rock rich in gold and silver
//  tundra   - snowfields: bitter cold, sparse pines, wolves to hunt for furs
//  ashlands - the Depths: ash fields, ember vents that burn, adamantium
//  mushroom - the Caves: giant mushrooms (chop for wood), fungus to eat, mana in the air
// A biome is a deterministic region, not a tile change, so saves are unaffected:
// RemasterBiomeAt(T) answers for any tile. The 3D view colours biome ground and rock
// and draws biome trees in their own style; resources are put down at boot and grow
// back a little every morning; mining biome rock can turn up extra ore.

var/list/rm_biomes = list()           // list(id, z, cx, cy, r)
var/list/rm_biome_chunks = list()     // "cx,cy,z" -> list of region indexes overlapping that 16x16 chunk
var/rm_biomes_ready = 0
var/rm_biome_day = -1

proc/RemasterBiomeAt(turf/T)
	if(!T || !rm_biomes_ready) return null
	var/list/near = rm_biome_chunks["[round((T.x - 1) / 16)],[round((T.y - 1) / 16)],[T.z]"]
	if(!near) return null
	for(var/i in near)
		var/list/B = rm_biomes[i]
		var/dx = T.x - B[3]
		var/dy = T.y - B[4]
		// a wobbly edge so regions are not circles
		var/wob = (sin(T.x * 23 + T.y * 7) + cos(T.y * 19 - T.x * 11)) * B[5] * 0.12
		if(dx * dx + dy * dy <= (B[5] + wob) * (B[5] + wob)) return B[1]
	return null

proc/RemasterBiomeName(id)
	return list("jungle"="Jungle", "mesa"="Mesa", "tundra"="Tundra", "ashlands"="Ashlands", "mushroom"="Mushroom caves")[id]

proc/RemasterBiomeAdd(id, turf/C, r)
	rm_biomes += list(list(id, C.z, C.x, C.y, r))
	var/i = length(rm_biomes)
	for(var/cy = round((C.y - r - 4) / 16), cy <= round((C.y + r + 4) / 16), cy++)
		for(var/cx = round((C.x - r - 4) / 16), cx <= round((C.x + r + 4) / 16), cx++)
			var/k = "[cx],[cy],[C.z]"
			if(!rm_biome_chunks[k]) rm_biome_chunks[k] = list()
			rm_biome_chunks[k] += i

// How many tiles of a kind around T (sampled).
proc/RemasterBiomeCount(turf/T, r, type)
	. = 0
	for(var/dx = -r, dx <= r, dx += 3)
		for(var/dy = -r, dy <= r, dy += 3)
			var/turf/X = locate(T.x + dx, T.y + dy, T.z)
			if(X && istype(X, type)) .++

proc/RemasterBiomeFar(turf/T)
	for(var/list/B in rm_biomes) if(B[2] == T.z && abs(B[3] - T.x) + abs(B[4] - T.y) < 70) return 0
	return 1

proc/RemasterPlaceBiomes()
	if(rm_biomes_ready) return
	rand_seed(9191)
	var/list/plan = list(
		list("jungle", 1, 6, 16, 24, /turf/grounds/grass, /turf/grounds/marsh),
		list("mesa", 1, 5, 14, 20, /turf/grounds/desert, /turf/grounds/cavefloor),
		list("tundra", 1, 5, 16, 24, /turf/grounds/snow, null),
		list("ashlands", 4, 5, 14, 22, /turf/grounds/hellfloor, null),
		list("mushroom", 2, 6, 12, 18, /turf/grounds/cellarfloor, null))
	for(var/list/P in plan)
		var/made = 0
		for(var/tries = 0, tries < 3000 && made < P[3], tries++)
			var/turf/T = locate(rand(80, world.maxx - 80), rand(80, world.maxy - 80), P[2])
			if(!T || !istype(T, P[6])) continue
			if(RemasterBiomeCount(T, 9, P[6]) < 20) continue
			if(P[7] && !RemasterBiomeCount(T, 15, P[7])) continue
			if(!RemasterBiomeFar(T)) continue
			RemasterBiomeAdd(P[1], T, rand(P[4], P[5]))
			made++
	rm_biomes_ready = 1
	RemasterBiomeGrow()
	RemasterBiomeStock(1)
	rand_seed(world.timeofday)
	world.log << "Biomes placed: [length(rm_biomes)]"

// Dense growth at boot: jungles fill with trees, mushroom caves with giant mushrooms,
// tundra gets its scattered pines.
proc/RemasterBiomeGrow()
	// mushroom caves are caverns opened in the solid rock of the Caves level
	for(var/list/B in rm_biomes) if(B[1] == "mushroom")
		for(var/turf/T in block(locate(max(2, B[3] - B[5]), max(2, B[4] - B[5]), B[2]), locate(min(world.maxx - 1, B[3] + B[5]), min(world.maxy - 1, B[4] + B[5]), B[2])))
			if(!istype(T, /turf/grounds/cellarfloor) || RemasterBiomeAt(T) != "mushroom") continue
			var/n = sin(T.x * 21 + T.y * 13) + cos(T.y * 25 - T.x * 9) + sin((T.x + T.y) * 7) * 0.6
			var/d = sqrt((T.x - B[3]) ** 2 + (T.y - B[4]) ** 2) / B[5]
			if(n > -0.6 + d * 1.4) RemasterCaveTurf(T, 1)
	for(var/list/B in rm_biomes)
		var/share = list("jungle"=24, "mushroom"=12, "tundra"=5)[B[1]]
		if(!share) continue
		var/ground = list("jungle"=/turf/grounds/grass, "mushroom"=/turf/grounds/cellarfloor, "tundra"=/turf/grounds/snow)[B[1]]
		var/tree = B[1] == "tundra" ? /turf/grounds/Trees/TundraTree : /turf/grounds/Trees/Tree1
		for(var/turf/T in block(locate(max(2, B[3] - B[5]), max(2, B[4] - B[5]), B[2]), locate(min(world.maxx - 1, B[3] + B[5]), min(world.maxy - 1, B[4] + B[5]), B[2])))
			if(!istype(T, ground) || T.density || !prob(share) || RemasterBiomeAt(T) != B[1]) continue
			var/busy = 0
			for(var/atom/movable/X in T) busy = 1
			if(!busy) new tree(T)

// Put resources down (at boot: full; each morning: a little regrowth).
proc/RemasterBiomeStock(full)
	for(var/list/B in rm_biomes)
		var/n = full ? round(B[5] * 0.9) : 2 + round(B[5] / 10)
		for(var/i = 1, i <= n, i++)
			var/a = rand(0, 359)
			var/d = rand(0, B[5] - 2)
			var/turf/T = locate(clamp(round(B[3] + cos(a) * d), 2, world.maxx - 1), clamp(round(B[4] + sin(a) * d), 2, world.maxy - 1), B[2])
			if(!T || T.density || RemasterBiomeAt(T) != B[1]) continue
			var/busy = 0
			for(var/atom/movable/X in T) busy = 1
			if(busy) continue
			RemasterBiomeResource(B[1], T, full)

proc/RemasterBiomeResource(id, turf/T, full)
	switch(id)
		if("jungle")
			if(full && prob(55)) new /turf/grounds/Trees/Tree1(T)        // dense jungle
			else if(prob(50)) RemasterWildPlant(/obj/Items/Plants/GrapeVine, T)
			else RemasterWildPlant(/obj/Items/Plants/TomatoPlant, T)
		if("mesa")
			var/ore = prob(60) ? /obj/Items/ores/Gold : /obj/Items/ores/Silver
			new ore(T)
		if("tundra")
			if(full && prob(30)) new /turf/grounds/Trees/TundraTree(T)
			else if(prob(25) && text2path("/mob/Monsters/Wolf"))
				if(RmUnitRoom())   // no wolf while the world is crowded (UnitLimit.dm)
					RmUnitAdd(1)
					var/wolf = text2path("/mob/Monsters/Wolf")
					var/mob/Monsters/W = new wolf(T)
					W.HomeLoc = T
			else new /obj/Items/ores/Iron(T)
		if("ashlands")
			if(prob(35)) new /obj/Items/ores/Adamantium(T)
			else new /obj/RemasterEmberVent(T)
		if("mushroom")
			if(full && prob(45)) new /turf/grounds/Trees/Tree1(T)        // giant mushrooms (3D draws them)
			else if(prob(70)) new /obj/Items/Food/Fungus(T)
			else
				var/kind = prob(50) ? /mob/Monsters/Critters/TowerCap : /mob/Monsters/Critters/CaveSpider
				if(RmUnitRoom())   // no creature while the world is crowded (UnitLimit.dm)
					RmUnitAdd(1)
					new kind(T)

proc/RemasterWildPlant(type, turf/T)
	var/obj/Items/Plants/P = new type(T)
	P.icon_state = "PPlant5"
	P.Content = 3       // ripe: ready to pick

// Ember vents in the ashlands: a puff of fire now and then.
obj/RemasterEmberVent
	name = "Ember vent"
	icon = 'Icons/Remastered/Runes.dmi'
	icon_state = "jet"
	density = 0

proc/RemasterBiomeLoop()
	while(1)
		sleep(100)
		for(var/obj/RemasterEmberVent/V in world) if(prob(12))
			RemasterHeat(V.loc, 260)
		// the tundra bites: units out there get colder unless by a fire
		for(var/Player/P in world) for(var/mob/Monsters/M in P.UnitList) if(M.Owner == P && M.z == 1 && M.RemasterFeelsCold())
			if(RemasterBiomeAt(M.loc) == "tundra" && !M.RemasterNearestFire()) M.Coldness = min(100, M.Coldness + 6)
		// mushroom caves breathe a little mana
		for(var/list/B in rm_biomes) if(B[1] == "mushroom" && prob(30))
			var/turf/T = locate(B[3] + rand(-B[5], B[5]), B[4] + rand(-B[5], B[5]), B[2])
			if(T && !T.density && RemasterBiomeAt(T) == "mushroom") RemasterGasAdd(T, "mana", 30)
		// a little regrowth every morning
		for(var/Player/P in world) if(P.remaster_days != rm_biome_day)
			rm_biome_day = P.remaster_days
			RemasterBiomeStock(0)
			break

// world/New: this file's part is step RmChainWorldNew_Biomes in Code/Remastered/Chains/WorldNew.dm

// Mining biome rock can turn up extra ore (called when a mined rock tile opens).
proc/RemasterBiomeMined(turf/T, mob/Monsters/M)
	var/id = RemasterBiomeAt(T)
	var/turf/at = M ? M.loc : T
	if(id == "mesa" && prob(35))
		var/ore = prob(55) ? /obj/Items/ores/Gold : /obj/Items/ores/Silver
		new ore(at)
	else if(id == "ashlands" && prob(18)) new /obj/Items/ores/Adamantium(at)
	else if(id == "tundra" && prob(20)) new /obj/Items/ores/Iron(at)
	if(prob(id == "mesa" ? 20 : 6)) new /obj/Items/RemasterSalt(at)   // rock salt, to keep food (Ailments.dm)
	if(T.z == 1 && prob(0.7)) new /obj/Items/RemasterSoulStone(at)    // a soul stone, rare, in the mountains (SoulStone.dm)
