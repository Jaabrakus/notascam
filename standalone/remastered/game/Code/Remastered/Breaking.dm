// Blocks and trees being mined or chopped, for the 3D view (remastered.html draws the
// cracks, chips, bursting blocks and falling trees). Every blow that lands on a tree or
// rock is recorded here by mob/Monsters/Bump (Orders.dm), so orders, jobs, the original
// dig designations and work by hand all show.

var/list/rm_worked = list()          // turf -> list(hp before the first blow, blows, last blow, dx, dy)
#define RM_WORKED_MAX 400
#define RM_ROOF_LAYER_HP 50          // work in each layer of a tunnel's roof (Mountains.dm)

proc/RemasterWorkBlow(turf/T, mob/M, hp0)
	if(!T || !M) return
	var/list/W = rm_worked[T]
	if(!W)
		if(length(rm_worked) >= RM_WORKED_MAX) RemasterWorkTidy(1)
		W = list(max(1, hp0), 0, 0, 0, 0)
		rm_worked[T] = W
	W[2]++
	W[3] = world.time
	W[4] = T.x - M.x      // the way the blow went: a tree falls away from its feller
	W[5] = T.y - M.y

// Broken tiles are forgotten after a few seconds, damage nobody touched for ten minutes
// too; when the list is full the oldest goes.
proc/RemasterWorkTidy(full = 0)
	if(rm_worked_native)   // the engine's loop, the same tidy (Native.dm)
		var/list/C = rm_worked_verify ? rm_worked.Copy() : null
		if(rm_worked_tidy(rm_worked, world.time, RM_WORKED_MAX, full))
			if(C) RmWorkedVerify(C, full)
			return
	RmWorkTidyDM(rm_worked, full)

proc/RmWorkTidyDM(list/L, full)
	var/turf/oldest
	var/oldest_at = 1#INF
	for(var/turf/T in L.Copy())
		var/list/W = L[T]
		if(world.time - W[3] > (T.density ? 6000 : 50)) L -= T
		else if(W[3] < oldest_at)
			oldest = T
			oldest_at = W[3]
	if(full && oldest && length(L) >= RM_WORKED_MAX) L -= oldest

// For the 3D view: worked tiles on this level inside the area it shows, as
// list(x, y, damage %, blows, dx, dy, broken, roof): roof 1 while a tunnel's roof is mined
// (the damage is then the current layer's).
Player/proc/Remaster3DWork(x0, y0, x1, y1)
	var/list/out = list()
	for(var/turf/T in rm_worked) if(T.z == z && T.x >= x0 && T.x <= x1 && T.y >= y0 && T.y <= y1)
		var/list/W = rm_worked[T]
		var/roofing = !T.density && T.remaster_roof > 0
		var/damage = T.density ? clamp(round(100 * (1 - T.HP / W[1])), 0, 100) : roofing ? (T.remaster_roof_hp > 0 ? clamp(round(100 * (1 - T.remaster_roof_hp / RM_ROOF_LAYER_HP)), 0, 100) : 0) : 100
		if(T.remaster_blk_hp > 0) damage = clamp(round(100 * (1 - T.remaster_blk_hp / RM_ROOF_LAYER_HP)), 0, 100)   // a block on its own (Gather.dm)
		out += list(list(T.x, T.y, damage, W[2], W[4], W[5], (T.density || roofing) ? 0 : 1, roofing ? 1 : 0, T.remaster_dig_lvl))
	return out

// --- Metal veins ---------------------------------------------------------------------
// Natural rock holds iron, silver, gold or adamantium in clusters fixed by place and
// biome, so the 3D view can show them before they are dug (tinted, streaked rock). A vein
// tile always gives its metal, on top of the original random finds when it breaks.
var/list/rm_vein_ores = list("iron"=/obj/Items/ores/Iron, "silver"=/obj/Items/ores/Silver, "gold"=/obj/Items/ores/Gold, "adamantium"=/obj/Items/ores/Adamantium)
turf/var/tmp/remaster_vein          // null: not worked out yet; "": no vein

// 0..1, the same for the same place (a hash of position and seed).
proc/RemasterHash(x, y, s)
	var/v = sin(x * 127.1 + y * 311.7 + s * 74.7) * 43758.5453
	return v - round(v)

// Smooth 0..1 noise, patches a few tiles across: veins come in clusters, not specks.
proc/RemasterNoise(x, y, s)
	var/fx = x / 4.5
	var/fy = y / 4.5
	var/ix = round(fx)
	var/iy = round(fy)
	var/tx = fx - ix
	var/ty = fy - iy
	tx = tx * tx * (3 - 2 * tx)
	ty = ty * ty * (3 - 2 * ty)
	var/a = RemasterHash(ix, iy, s)
	var/b = RemasterHash(ix + 1, iy, s)
	var/c = RemasterHash(ix, iy + 1, s)
	var/d = RemasterHash(ix + 1, iy + 1, s)
	return a + (b - a) * tx + (c - a) * ty + (a - b - c + d) * tx * ty

// The metal in a natural rock tile, or null. Rarest first; underground is richer;
// mesa rock is rich in gold and silver, tundra in iron, adamantium only in the ashlands
// and the depths.
proc/RemasterVeinAt(turf/T)
	if(!T || !T.density || !T.CanDigAt || T.IsWall || T.Tree) return null
	if(T.remaster_ore_max && T.remaster_ore_left <= 0) return null    // worked out (Yield.dm)
	if(T.remaster_built_floor) return null    // stone laid on open ground (Plans.dm)
	if(!isnull(T.remaster_vein)) return T.remaster_vein || null
	var/found = RemasterVeinKind(T)
	T.remaster_vein = found
	return found || null

// Which metal the place holds (or ""), by position and biome only, whatever stands there now.
proc/RemasterVeinKind(turf/T)
	var/biome = RemasterBiomeAt(T)
	// scarce: the surface has only a little iron (more in the tundra, gold and silver only in the mesa);
	// silver and gold are in the caves below, adamantium only in the depths (and the ashlands)
	var/deep = 0
	var/list/need
	if(T.z == 4 || biome == "ashlands") need = list("adamantium"=0.85, "gold"=0.90, "silver"=0.90, "iron"=0.86)
	else if(T.z == UNDERGROUND_LAYER) need = list("adamantium"=2, "gold"=0.93, "silver"=0.91, "iron"=0.84)
	else need = list("adamantium"=2, "gold"=(biome == "mesa" ? 0.90 : 2), "silver"=(biome == "mesa" ? 0.89 : 2), "iron"=(biome == "tundra" ? 0.84 : 0.88))
	var/found = ""
	var/seed = 0
	for(var/ore in need)
		seed += 17
		if(RemasterNoise(T.x, T.y, seed + T.z * 5) > need[ore] - deep)
			found = ore
			break
	return found

proc/RemasterVeinMined(turf/T, mob/M, vein)
	var/type = rm_vein_ores[vein]
	if(!type) return
	var/turf/at = M ? M.loc : T
	new type(at)
	if(prob(50)) new type(at)
	T.remaster_vein = ""

// --- Bamboo wood -----------------------------------------------------------------------
// Felled bamboo gives bamboo canes instead of logs. They are a kind of wood, so every
// recipe and stockpile that takes wood takes them too.
obj/Items/woods/wood/Bamboo
	// its values: art/items/catalogue.json row woods.wood.bamboo (export_items.py writes ItemData.dm)

proc/RemasterBambooWood(turf/at, list/before)
	if(!at) return
	for(var/obj/Items/woods/wood/W in at)
		if(istype(W, /obj/Items/woods/wood/Bamboo) || (before && (W in before))) continue
		new /obj/Items/woods/wood/Bamboo(at)
		del W

// --- Mountains as stacked blocks -------------------------------------------------------
// A natural rock tile is a column of blocks: 3 at a mountain's edge, up to 8 deep inside
// (2 underground: a tunnel's height). Mining is one block an order, and from outside only
// the floor block and the one above can be mined: the first order takes whichever of the two
// the player points at (a notch at the floor, or an overhang over the solid floor block: units,
// two blocks tall, don't fit yet), the second the other, opening a two-high tunnel (the tile's
// HP is the two blocks); the blocks above stay
// as its roof, mined a block an order from inside (Mountains.dm). Heights come from how far the tile is from open ground, counting tunnels
// as mountain, so they don't change as you dig. The roof is saved with the world.
turf/var/tmp/remaster_blocks = 0     // column height in blocks (0: not worked out yet)
turf/var/remaster_roof = 0           // blocks still overhead on a dug-out tile
turf/var/remaster_dug = 0            // 1: the bottom block is out (a notch); units need the one above out too
turf/var/remaster_dug_top = 0        // 1: the block above the floor block is out first (an overhang); the floor block still stands
turf/var/tmp/remaster_dig_lvl = 0    // the block being worked (0 the floor block, 1 the one above), for the 3D cracks

proc/RemasterIsMountain(turf/T)
	if(!T) return 0
	if(T.remaster_roof > 0) return 1
	return T.density && T.opacity && !T.IsWall && !T.Tree

// What the height count sees as mountain: the map's own rock whether dug since or not, so digging a mountain open never
// changes its neighbours' heights after a restart; other rock while it stands; never a block laid on open ground
// (Plans.dm). planning/MOUNTAIN_HEIGHTS.md step 0 (ramps-gather, 2026-10-25).
proc/RemasterRockAtStart(turf/X)
	if(istype(X, /turf/grounds/cavefloor)) return 1
	return RemasterIsMountain(X) && !X.remaster_built_floor

// A column keeps its height (remaster_built, saved with the world) the first time it changes: dug, carved or built on,
// so a later change to how heights are worked out (the sky peaks) never moves what was dug.
proc/RmKeepHeight(turf/T)
	if(!T || T.remaster_built || T.z != GROUND_LAYER || !T.density || !RemasterIsMountain(T)) return
	RemasterBlocksAt(T)
	T.remaster_built = T.remaster_blocks

proc/RemasterBlocksAt(turf/T)
	if(!T) return 0
	if(T.remaster_built && T.remaster_blocks != T.remaster_built) T.remaster_blocks = T.remaster_built   // its height as kept (RmKeepHeight), or built up (Plans.dm)
	if(!T.remaster_blocks && T.remaster_mapblocks) T.remaster_blocks = T.remaster_mapblocks   // set by the map: rock round a raised lake (Water.dm)
	if(T.remaster_blocks) return max(0, T.remaster_blocks - T.remaster_topcut)   // less any dug off its top (Gather.dm)
	var/n = 2
	if(T.z == GROUND_LAYER)
		var/d = 6
		for(var/r = 1, r <= 5 && d == 6, r++)   // the ring at r only: inside it all is mountain, or d would be set (world-look 2026-10-25: 3x faster than range(r) each time)
			for(var/dx = -r, dx <= r && d == 6, dx++)
				var/step = (dx == -r || dx == r) ? 1 : 2 * r   // the ring's side columns whole, between them its top and bottom
				for(var/dy = -r, dy <= r, dy += step)
					var/turf/X = locate(T.x + dx, T.y + dy, T.z)
					if(X && !RemasterRockAtStart(X))
						d = r
						break
		n = list(3, 4, 5, 6, 7, 7)[d]
		if(d >= 2) n += round(RemasterHash(T.x, T.y, 99) * 2.99) - 1     // an uneven skyline
		n = clamp(n, 3, 8)
	T.remaster_blocks = n
	return max(0, n - T.remaster_topcut)
