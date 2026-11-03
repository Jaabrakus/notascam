// Resources that give as they are worked, and tending (planning/SONGS_OF_SYX_ECONOMY.md).
//  - Trees: 2 logs and a chance of a third. Chopping half-way through drops one at the feller's feet; at
//    zero it falls with one more, the chance of an extra (RemasterTreeFell) and its seeds, and is gone
//    (replant from the seeds). A tree left alone for a couple of minutes grows its wood back, slowly.
//  - Ore veins (Breaking.dm): an ordinary vein block holds 1 or 2 ore. Every RM_ORE_WORK of digging drops
//    one; the rock holds firm until the block is worked out, then mines as plain rock, spent for good.
//  - Living blocks: a vein's richest blocks (RemasterVeinLiving), about one for every 10 blocks of vein and
//    a coin toss for one more (1..7). Each holds RM_LIVING_ORE, every ore deeper in takes RM_ORE_HARDER %
//    more digging than the one before, and one with ore still in it grows one back every RM_ORE_REGROW of
//    rest. Dug to nothing it dies. Workers leave the last ore in one by themselves; the player may tend it
//    higher, or order it dug out (remaster_tend -1). How a realm works its veins is up to it.
//  - Plain rock: every RM_STONE_WORK of digging drops a stone, on top of the original finds.
//  - Tend living resources (a realm setting in Work, which each unit may override in its Orders): when on,
//    workers leave a tree at half (it grows back) and a living block its last ore; when off they fell the
//    tree and dig the block out. A mark set on the tile itself always wins.
//  - Every piece gathered floats up as "+1 Log" over the worker, and the village log notes what each
//    worker brought in (RemasterYieldNote).
//  - Tending: a tree or vein can be marked to keep a share (a half, or three quarters). Orders, jobs and
//    the offline catch-up stop there, so a tended forest is cut again and again as it grows back, and a
//    tended vein keeps its reserve for later. The mark is the land's, saved with the tile.
// The tile's numbers are saved with the world (WorldSave.dm saves the vars of a changed tile).

#define RM_TREE_HP 250            // a grown tree's health (the original Trees type)
#define RM_TREE_LOG_WORK 125      // chopping per log while it stands: one at half, then the fall's
#define RM_TREE_EXTRA 35          // % chance the fall gives an extra log (RM_TREE_EXTRA_GOOD for Humans, Elves, Lizardmen)
#define RM_TREE_EXTRA_GOOD 60
#define RM_TREE_HEAL 4            // health a resting tree grows back each RM_YIELD_EVERY (a log in ~15 min)
#define RM_TREE_REST 1200         // ticks after the last blow before it starts to grow back (2 min)
#define RM_ORE_WORK 20            // digging per piece of ore
#define RM_ORE_REGROW 12000       // rest a living block needs to grow one ore back (20 min)
#define RM_LIVING_ORE 10          // ore a living block holds
#define RM_ORE_HARDER 50          // % more digging for each ore further into a living block
#define RM_LIVING_PER 10          // vein blocks per living block (and a coin toss for one more)
#define RM_LIVING_MAX 7
#define RM_STONE_WORK 25          // digging per stone from plain rock (rock blocks have 50)
#define RM_YIELD_EVERY 300        // the growing loop (30 s)
#define RM_YIELD_HOLD 100000      // added to a vein's health for one blow so it holds while ore is left

Player/var/remaster_tend_living = 1      // saved: the realm's workers tend living resources
mob/Monsters/var/remaster_tend_mode = ""   // saved: "" the realm's setting, "on" or "off" for this unit
mob/Monsters/var/tmp/list/remaster_gathered   // name -> pieces since the last log line
mob/Monsters/var/tmp/remaster_site_digging = 0   // digging out a planned building (Buildings.dm): no holding veins
mob/Monsters/var/tmp/remaster_away_working = 0   // chopping or mining in the offline catch-up (Away.dm)
mob/Monsters/var/tmp/remaster_gathered_at = 0

// Whether M leaves living resources to grow back: never since the owner's Tend redo (10-26): harvesting takes everything,
// and regrowing is the zone's own work (Jobs.dm RmJzRegrowStep). A tree's or vein's own mark still holds.
proc/RemasterTendsLiving(mob/Monsters/M)
	return 0

#define RM_TEND_TREE 50           // a tended tree is left at half
#define RM_TEND_SAPLING -2        // remaster_tend on a sapling a zone planted: never cut, a tree to cut once grown (Jobs.dm)
#define RM_TEND_STUMP -3          // remaster_tend on a felled tree's tile in a zone: its workers plant a sapling there

turf/var
	remaster_tend = 0             // saved: 0, the share (percent) workers leave for it to grow back / keep, or -1: dig it out
	remaster_tree_max             // saved: a worked tree's full health
	remaster_ore_left             // saved: ore left in a vein tile (null until first worked)
	remaster_ore_max              // saved: what it held at first
turf/var/tmp
	remaster_found_said = 0       // its finder was told it's a living block
	remaster_yield_acc = 0        // work done since the last piece dropped
	remaster_yield_n = 0          // pieces dropped (orders watch it for progress while a vein holds)
	remaster_yield_at = 0         // last blow
	remaster_ore_grow = 0         // rest towards the next ore growing back

var/list/rm_yield_known = list()   // turf -> 1: worked or tended tiles, for growing and the 3D card
var/rm_yield_scanned = 0

proc/RemasterYieldIsTree(turf/T)
	return T && T.density && T.Tree

// Natural rock that gives stone (not walls people built, not wooden walls).
proc/RemasterYieldIsRock(turf/T)
	return T && T.density && T.CanDigAt && !T.Tree && !T.IsWall && !T.IsWood

// --- Stone by the block (mountain-stone, 10-27; planning/FIXES_PLAN_2026-10-27.md section 3, step 1) ---
// Every natural block of a mountain gives the same stone however it is dug: from the ground (bottom or top block first),
// from up on the mountain, a tunnel's roof, a Dig down or a plan. Its work (50) earns 2, one half-way through it and one
// as it comes out, and a 70% chance of one more as it comes out: about 2.7. It was 2.7 only for the two outside blocks
// dug the old way (Orders.dm's Bump) and 0.7 for every block above them. A block a build plan laid gives back the 1 stone
// it cost (Plans.dm RmPlanLayTick), so building and digging the same cells never makes stone. Ore and the 2006 finds are
// as before.
turf/var/remaster_laid = 0        // blocks a build plan laid: bit k, block k (saved with the world)
turf/var/tmp/rm_stone_half = 0    // blocks whose half-way stone is paid: bit k
mob/Monsters/var/tmp/rm_dig_own = 0    // set on every blow (Orders.dm's Bump): a worker's mountain block, its stone by the block
mob/Monsters/var/tmp/rm_dig_zone = 0   // ...and a zone's own dig: the 2006 finds bring no cave-in and no critters

proc/RmStoneBit(k)
	return (isnum(k) && k >= 0 && k <= 15) ? 1 << k : 0

// A blow left block k of T with `left` of its `size` work: half-way, its first stone (once).
proc/RmStoneHalf(turf/T, k, mob/Monsters/M, left, size)
	var/bit = RmStoneBit(k)
	if(!T || !M || !bit || left > size / 2 || (T.rm_stone_half & bit) || (T.remaster_laid & bit)) return
	T.rm_stone_half |= bit
	RemasterYieldGive(M, new /obj/Items/ores/stone(isturf(M.loc) ? M.loc : T))

// Block k of T came out under M's blows: the rest of its work's stone, and the piece that may come with it, left at M's
// feet for the caller to take up as before (null when none). A laid block: its 1 stone, or its 1 log (wood), as that piece.
proc/RmStoneOut(turf/T, k, mob/Monsters/M)
	var/bit = RmStoneBit(k)
	var/turf/at = isturf(M.loc) ? M.loc : T
	if((T.remaster_laid | T.rm_laid_gone) & bit)     // laid by a plan (still there, or just gone: Plans.dm RmLaidTidy)
		var/wood = RmLaidMatOf(T, k) == "w"
		RmLaidForget(T, k)
		T.rm_stone_half &= ~bit
		return wood ? new /obj/Items/woods/wood(at) : new /obj/Items/ores/stone(at)
	if(!(T.rm_stone_half & bit)) RemasterYieldGive(M, new /obj/Items/ores/stone(at))
	T.rm_stone_half &= ~bit
	RemasterYieldGive(M, new /obj/Items/ores/stone(at))
	return prob(70) ? new /obj/Items/ores/stone(at) : null

proc/RemasterTreeMax(turf/T)
	if(!T.remaster_tree_max) T.remaster_tree_max = max(T.HP, RM_TREE_HP)
	return T.remaster_tree_max

// A vein block's ore, set the first time it is worked: 1 or 2 (a living block RM_LIVING_ORE), the same
// for the same place.
proc/RemasterOreReserve(turf/T, vein)
	if(isnull(T.remaster_ore_left))
		T.remaster_ore_left = RemasterVeinLiving(T) ? RM_LIVING_ORE : RemasterHash(T.x, T.y, 91 + T.z * 5) < 0.5 ? 1 : 2
		T.remaster_ore_max = T.remaster_ore_left
		remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1
	return T.remaster_ore_left

// A vein's living blocks: where its ore runs richest (the vein noise is highest, Breaking.dm), one for
// every RM_LIVING_PER blocks of vein and a coin toss for one more, 1 to RM_LIVING_MAX. The same for the
// same place: worked out once for a whole vein (its blocks of one metal touching).
var/list/rm_vein_seed = list("adamantium"=17, "gold"=34, "silver"=51, "iron"=68)   // RemasterVeinKind's order
var/list/rm_vein_hearts = list()   // "x,y,z" -> 1
turf/var/tmp/remaster_living
proc/RemasterVeinLiving(turf/T)
	if(!T) return 0
	if(!isnull(T.remaster_living)) return T.remaster_living
	var/metal = RemasterVeinKind(T)
	var/s = rm_vein_seed[metal]
	if(!s)
		T.remaster_living = 0
		return 0
	s += T.z * 5
	// the vein: every place of this metal touching it (a vein is a few dozen blocks at most)
	var/list/vein = list(T)
	var/list/seen = list()
	seen[T] = 1
	var/list/rich = list()
	rich[T] = RemasterNoise(T.x, T.y, s)
	var/turf/heart = T
	for(var/i = 1, i <= length(vein) && i <= 400, i++)
		var/turf/C = vein[i]
		for(var/turf/N in range(1, C))
			if(seen[N]) continue
			seen[N] = 1
			if(RemasterVeinKind(N) != metal) continue
			vein += N
			rich[N] = RemasterNoise(N.x, N.y, s)
			if(RemasterRicher(N, heart, rich)) heart = N
	var/n = clamp(max(1, round(length(vein) / RM_LIVING_PER)) + (RemasterHash(heart.x, heart.y, s + 7) < 0.5 ? 1 : 0), 1, min(RM_LIVING_MAX, length(vein)))
	var/list/hearts = list()
	while(length(hearts) < n)
		var/turf/B
		for(var/turf/V in vein) if(!(V in hearts) && (!B || RemasterRicher(V, B, rich))) B = V
		hearts += B
	for(var/turf/V in vein) V.remaster_living = (V in hearts) ? 1 : 0
	return T.remaster_living

proc/RemasterRicher(turf/A, turf/B, list/rich)
	return rich[A] > rich[B] || (rich[A] == rich[B] && (A.x < B.x || (A.x == B.x && A.y < B.y)))

// Ore a vein block keeps: its tending share; a living block its last one while its worker tends living
// resources, unless the block is ordered dug out (-1).
proc/RemasterTendKeep(turf/T, mob/Monsters/M)
	return 0     // the Tend redo: a vein is dug out whole; marks (old saves' too) are ignored

// The share shown and used: a tree's tending percent, a vein block's ore kept as a percent.
proc/RemasterTendShare(turf/T)
	if(T.Tree) return max(0, T.remaster_tend)
	return T.remaster_ore_max ? round(100 * RemasterTendKeep(T) / T.remaster_ore_max) : max(0, T.remaster_tend)

// The health a tree is left at for M (the worker): its tending mark, or 0 when M fells it.
proc/RemasterTreeMark(turf/T, mob/Monsters/M)
	return 0     // the Tend redo: a tree is felled whole; marks (old saves' too) are ignored

// Worked down to its tending mark: M (the worker) leaves it.
proc/RemasterTendReached(turf/T, mob/Monsters/M)
	if(!isturf(T) || !T.density) return 0
	if(T.Tree)
		var/mark = RemasterTreeMark(T, M)
		return mark && T.HP <= mark
	if(T.remaster_ore_max) return T.remaster_ore_left > 0 && T.remaster_ore_left <= RemasterTendKeep(T, M)
	return 0

// Digging for the next ore: deeper into a living block each one takes RM_ORE_HARDER % more.
proc/RemasterOreWork(turf/T)
	if(!RemasterVeinLiving(T)) return RM_ORE_WORK
	return RM_ORE_WORK * (1 + max(0, T.remaster_ore_max - T.remaster_ore_left) * RM_ORE_HARDER / 100)

// Called by mob/Monsters/Bump (Orders.dm) around the original blow. Before: returns the health a vein, or a
// tree M tends, had (it is raised so the blow can't break it), else null. A tended tree is held on every blow,
// not only at the order tick, so a group's blows between ticks can't take it past its mark and fell it.
proc/RemasterYieldBefore(turf/T, mob/Monsters/M)
	if(!isturf(T) || !T.density) return null
	if(T.Tree)
		if(!RemasterTreeMark(T, M)) return null
		. = T.HP
		T.HP += RM_YIELD_HOLD
		return
	var/vein = RemasterVeinAt(T)
	if(!vein || RemasterOreReserve(T, vein) <= 0) return null
	. = T.HP
	T.HP += RM_YIELD_HOLD

// After: drops what the work earned at M's feet. 1 when a held vein took the blow.
proc/RemasterYieldAfter(turf/T, mob/Monsters/M, hp0, held)
	if(!isturf(T) || !M || isnull(hp0)) return 0
	var/turf/at = isturf(M.loc) ? M.loc : T
	if(!isnull(held) && T.Tree)
		// a held tree takes the blow's work, but never past its mark; its logs follow below as an unheld tree's do
		T.HP = min(held, max(RemasterTreeMark(T, M), T.HP - RM_YIELD_HOLD))
		held = null
	if(!isnull(held))
		var/work = held + RM_YIELD_HOLD - T.HP
		T.HP = held
		if(work <= 0) return 1
		RemasterYieldMark(T)
		T.remaster_yield_acc += work
		var/vein = RemasterVeinAt(T)
		var/type = vein ? rm_vein_ores[vein] : null
		if(RemasterVeinLiving(T) && !T.remaster_found_said && istype(M.Owner, /Player))
			T.remaster_found_said = 1
			M.Owner:RemasterNotice("[M.name] found a living [vein] block: it holds [T.remaster_ore_max] ore and grows one back every [RM_ORE_REGROW / 600] minutes while some is left in it; each ore deeper in is harder to dig. Dug out, it's gone.")
		while(type && T.remaster_yield_acc >= RemasterOreWork(T) && T.remaster_ore_left > 0 && !RemasterTendReached(T, M))
			T.remaster_yield_acc -= RemasterOreWork(T)
			T.remaster_ore_left--
			T.remaster_yield_n++
			RemasterYieldGive(M, new type(at))
			T.remaster_ore_grow = 0
		if(T.remaster_ore_left <= 0)
			T.remaster_vein = ""           // spent: plain rock now (RemasterVeinAt)
			T.remaster_yield_acc = 0
			if(istype(M.Owner, /Player)) M.Owner:RemasterNotice("[M.name]: dug this [vein || "ore"] out to nothing; it won't grow back")
		return 1
	if(!T.density) return 0
	var/work = hp0 - T.HP
	if(work <= 0) return 0
	if(T.Tree)
		RemasterTreeMax(T)
		RemasterYieldMark(T)
		T.remaster_yield_acc += work
		while(T.remaster_yield_acc >= RM_TREE_LOG_WORK)
			T.remaster_yield_acc -= RM_TREE_LOG_WORK
			T.remaster_yield_n++
			var/log = T.Bamboo ? /obj/Items/woods/wood/Bamboo : /obj/Items/woods/wood
			RemasterYieldGive(M, new log(at))
		return 0
	if(RemasterYieldIsRock(T) && !M.rm_dig_own)    // a mountain block's stone comes by the block (RmStoneHalf, RmStoneOut)
		T.remaster_yield_acc += work
		T.remaster_yield_at = world.time
		while(T.remaster_yield_acc >= RM_STONE_WORK)
			T.remaster_yield_acc -= RM_STONE_WORK
			T.remaster_yield_n++
			RemasterYieldGive(M, new /obj/Items/ores/stone(at))
	return 0

// A tree came down (Orders.dm, after the original fall): its logs are one, and the chance of another,
// whatever the original dropped; the seeds stay.
proc/RemasterTreeFell(turf/at, list/before, mob/Monsters/M, bamboo)
	if(!isturf(at)) return
	for(var/obj/Items/woods/wood/W in at) if(!before || !(W in before)) del W
	var/log = bamboo ? /obj/Items/woods/wood/Bamboo : /obj/Items/woods/wood
	RemasterYieldGive(M, new log(at))
	var/good = M && (M.Race in list("Human", "Elf", "Lizardman"))
	if(prob(good ? RM_TREE_EXTRA_GOOD : RM_TREE_EXTRA)) RemasterYieldGive(M, new log(at))
	var/Player/SP = M ? M.Owner : null
	// the stump is the tree's own tile (`at` is where its feller stands): the order's target, else the tile it faces
	var/datum/remaster_order/O = M ? M.remaster_active : null
	var/turf/stump = O ? O.target : null
	if(!isturf(stump) || stump.density || !stump.Tree) stump = M ? get_step(M, M.dir) : null
	if(istype(SP) && isturf(stump) && !stump.density && stump.Tree) SP.RmJzStumpAt(stump)   // in a wood or gather zone: a stump its workers replant (Jobs.dm)

// Into the worker's pack while it has room (as a mined block's stone is, Orders.dm), else at its feet,
// where an order gathers it when the work is done.
proc/RemasterYieldGive(mob/Monsters/M, obj/Items/I)
	if(!M || !I) return
	RemasterYieldNote(M, I)
	if(M.weight + I.weight <= M.weightmax) M.PickUpItem(I)
	else if(isturf(I.loc) && M.rm_jz_id && istype(M.Owner, /Player)) M.Owner:RmJzLying(M.rm_jz_id)   // a full bag: it lies, and a waiting worker of the zone is called (Jobs.dm, J2)

// "+1 Log" floats over the worker (Hits.dm, the 3D view), and the piece counts towards its next log line.
proc/RemasterYieldNote(mob/Monsters/M, obj/Items/I)
	var/what = RemasterYieldName(I)
	if(isturf(M.loc)) RemasterHitAt(M.x, M.y, M.z, 0, "+1 [what]", M, M.Owner)
	if(!M.remaster_gathered) M.remaster_gathered = list()
	if(!length(M.remaster_gathered)) M.remaster_gathered_at = world.time
	var/Player/JP = M.Owner
	if(M.rm_jz_id && istype(JP)) JP.RmJzYield(M)   // the job board's output per zone (Jobs.dm)
	M.remaster_gathered[what] = (M.remaster_gathered[what] || 0) + 1

proc/RemasterYieldName(obj/Items/I)
	if(istype(I, /obj/Items/woods/wood/Bamboo)) return "Bamboo"
	if(istype(I, /obj/Items/woods/wood)) return "Log"
	if(istype(I, /obj/Items/ores/stone)) return "Stone"
	var/n = "[I.name]"
	return n

// A worker's haul goes into the village log a few seconds after it starts, as one line.
proc/RemasterYieldLogFlush(mob/Monsters/M, force)
	if(!M || !length(M.remaster_gathered)) return
	if(!force && world.time - M.remaster_gathered_at < 80) return
	var/Player/P = M.Owner
	var/list/parts = list()
	for(var/k in M.remaster_gathered)
		var/n = M.remaster_gathered[k]
		parts += "[n] [lowertext(k)][n > 1 && (k in list("Log", "Stone")) ? "s" : ""]"
	M.remaster_gathered = null
	if(istype(P)) P.RemasterLog("[M.RemasterBareName()] gathered [jointext(parts, ", ")]", "work", M)

proc/RemasterYieldMark(turf/T)
	T.remaster_yield_at = world.time
	rm_yield_known[T] = 1
	remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1

// Progress an order can see: health, or pieces dropped while a vein holds.
proc/RemasterWorkProgress(atom/A)
	if(!A) return null
	return isturf(A) ? A:HP - A:remaster_yield_n * 1000 : A:HP

// --- Tending ------------------------------------------------------------------------------
// From the 3D card (HUD.dm "tend": "x|y|percent").
Player/proc/RemasterTend(turf/T, pct)
	return 0     // the Tend redo: no marks any more (the owner: "Remove them all"); the page no longer sends it
	if(!isturf(T) || !T.density)
		RemasterNotice("Nothing there to tend.")
		return 0
	var/vein = T.Tree ? null : RemasterVeinAt(T)
	if(!T.Tree && !vein)
		RemasterNotice("Only trees and ore veins can be tended.")
		return 0
	if(!RemasterMayWork(T)) return 0
	pct = clamp(round(pct), -1, 90)
	var/living = vein && RemasterVeinLiving(T)
	if(pct < 0 && !living) pct = 0
	if(vein) RemasterOreReserve(T, vein)
	else RemasterTreeMax(T)
	T.remaster_tend = pct
	RemasterYieldMark(T)
	if(T.Tree)
		if(pct) RemasterNotice("Tended: woodcutters leave this tree at [pct]% and come back when it has grown.")
		else RemasterNotice("No longer tended: this tree can be felled.")
	else if(pct < 0) RemasterNotice("Dig it out: miners will take all its ore, and this living block will die.")
	else if(pct) RemasterNotice("Tended: miners keep [RemasterTendKeep(T)] of this block's [T.remaster_ore_max] ore in the rock[living ? "; it's a living block, so it grows back" : "; it won't grow back, it's kept for later"].")
	else if(living) RemasterNotice("As usual: miners leave this living block's last ore so it lives and grows back.")
	else RemasterNotice("No longer tended: this vein can be worked out.")
	return 1

// --- 3D card ------------------------------------------------------------------------------
// list(x, y, left, kept %, kind, full[, living, tend]) for worked or tended tiles in view: logs before a
// tree falls, or ore left in a vein (living 1: it grows back; tend -1: ordered dug out).
Player/proc/Remaster3DYield(x0, y0, x1, y1)
	var/list/out = list()
	for(var/turf/T in rm_yield_known) if(T.z == z && T.x >= x0 && T.x <= x1 && T.y >= y0 && T.y <= y1 && T.density)
		if(T.Tree) out += list(list(T.x, T.y, -round(-T.HP / RM_TREE_LOG_WORK), T.remaster_tend, "tree", -round(-RemasterTreeMax(T) / RM_TREE_LOG_WORK)))
		else if(T.remaster_ore_max && T.remaster_ore_left > 0) out += list(list(T.x, T.y, T.remaster_ore_left, RemasterTendShare(T), "vein", T.remaster_ore_max, RemasterVeinLiving(T) ? 1 : 0, T.remaster_tend))
	return out

// --- Growing back ---------------------------------------------------------------------------
proc/RemasterYieldLoop()
	while(1)
		sleep(RM_YIELD_EVERY)
		RemasterYieldGrow()

proc/RemasterYieldGrow()
	if(!rm_yield_scanned && remaster_world_ready)
		// tiles restored from the save: worked trees and veins join the list again
		rm_yield_scanned = 1
		for(var/k in remaster_dirty_turfs)
			var/list/c = splittext(k, ",")
			if(length(c) < 3) continue
			var/turf/T = locate(text2num(c[1]), text2num(c[2]), text2num(c[3]))
			if(T && T.density && (T.remaster_tree_max || T.remaster_ore_max || T.remaster_tend)) rm_yield_known[T] = 1
	for(var/turf/T in rm_yield_known)
		if(!T.density || !(T.Tree || T.remaster_ore_max))
			rm_yield_known -= T
			continue
		if(world.time - T.remaster_yield_at < RM_TREE_REST) continue
		if(!T.Tree && !rm_zone_regrow)    // living resources off (Jobs.dm rm_zone_regrow 0): no ore grows back either
			rm_yield_known -= T
			continue
		if(!T.Tree)
			// a living vein tile with ore still in it grows another back; one dug to nothing stays dead
			if(T.remaster_ore_left <= 0 || T.remaster_ore_left >= T.remaster_ore_max || !RemasterVeinLiving(T))
				if(!T.remaster_tend) rm_yield_known -= T
				continue
			T.remaster_ore_grow += RM_YIELD_EVERY
			if(T.remaster_ore_grow >= RM_ORE_REGROW)
				T.remaster_ore_grow = 0
				T.remaster_ore_left++
			continue
		if(T.remaster_tend != RM_TEND_SAPLING)    // only a zone's saplings grow (the Tend redo): no tree heals by itself
			rm_yield_known -= T
			continue
		var/full = RemasterTreeMax(T)
		if(T.HP >= full)
			if(T.remaster_tend == RM_TEND_SAPLING)    // a zone's sapling grown: a tree to cut again (Jobs.dm)
				T.remaster_tend = 0
				T.name = "tree"
				remaster_dirty_turfs["[T.x],[T.y],[T.z]"] = 1
			if(!T.remaster_tend) rm_yield_known -= T      // whole again and nobody's mark on it
			continue
		T.HP = min(full, T.HP + RM_TREE_HEAL)
		T.remaster_yield_acc = 0

// world/New: this file's part is step RmChainWorldNew_Yield in Code/Remastered/Chains/WorldNew.dm
