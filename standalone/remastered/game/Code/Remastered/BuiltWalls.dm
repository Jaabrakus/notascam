// Building rework L7 (planning/BUILDING_REWORK_PLAN_2026-10-27.md step 4): built walls only fall to sieges and blows.
// A column with laid blocks (Plans.dm RmBuilt) belongs to the realm of who laid them (remaster_laid_by; for blocks laid
// before L1 with no key, the realm whose claim covers the tile; with neither, nobody's). Nobody outside that realm (the
// ruler, members and vassals: Realms.dm RemasterAlliedKeys) may take any block of it, laid or the natural footing under
// it, by any order, queued or not, a plan's dig or way up, or the old bump-dig: "Built walls fall only to siege
// engines." Natural rock beside it stays as it was. Rams and catapults batter it a block at a time, top first: a stone
// block takes 1300, a wood one 450 (a ram 300 a blow, +100 a crew member up to +200; a boulder 500); each block that
// falls comes off the column (the units on it come down to the new top), and 60% of the time leaves one of what it was
// made of beside it. With no laid block left it is breached: its realm hears of it once; a natural base stays rock.
// The damage to the top block isn't saved (whole again after a reload).
#define RM_BLOCK_HP_STONE 1300
#define RM_BLOCK_HP_WOOD 450
var/const/RM_BUILT_HELD_SAY = "Built walls fall only to siege engines."
var/list/rm_built_dig_kinds = list("Mine", "Mine roof", "Dig down", "Carve ramp")
turf/var/tmp/rm_block_hurt = 0         // damage done to a laid column's top block

// The realm key a column's laid blocks belong to, or null.
proc/RmBuiltOwnerKey(turf/T)
	if(!RmBuilt(T)) return null
	if(T.remaster_laid_by) return T.remaster_laid_by
	var/obj/RemasterBanner/B = RemasterClaimAt(T)
	return B ? B.owner_key : null

// May P not take blocks of T's column? 1: another realm's built wall (every block of it: its laid blocks and the natural
// footing under them; a plan never lays natural rock over a laid block). P null (an NPC, a beast): never of the realm.
proc/RmBuiltHeld(Player/P, turf/T)
	if(!T || !T.remaster_laid) return 0
	var/owner = RmBuiltOwnerKey(T)
	if(!owner) return 0
	return !(istype(P) && RemasterAlliedKeys(owner, P.key))

// An order's target as the column it digs (an order from up on the mountain names the Sky layer's tile).
proc/RmBuiltTurf(turf/A)
	return (isturf(A) && A.z == SKY_LAYER) ? locate(A.x, A.y, GROUND_LAYER) : A

// The column's top block when it is a laid one: its index from the floor, else -1.
proc/RmBuiltTopK(turf/T)
	if(!T || !T.density || !T.remaster_laid) return -1
	var/h = RemasterBlocksAt(T)
	if(h <= 0) return -1
	return (RmLaidMask(T) & (1 << (h - 1))) ? h - 1 : -1

proc/RmBlockHP(turf/T, k)
	return RmLaidMatOf(T, k) == "w" ? RM_BLOCK_HP_WOOD : RM_BLOCK_HP_STONE

// The laid blocks' hit points left (the siege bar): the blocks there, less the top one's damage.
proc/RmBuiltWallHP(turf/T)
	. = -T.rm_block_hurt
	var/m = RmLaidMask(T)
	for(var/k = 0, k <= 15 && (m >> k), k++) if(m & (1 << k)) . += RmBlockHP(T, k)
	. = max(0, .)

// A ram's blow or a boulder on a column of laid blocks (Siege.dm RemasterSiegeBlow).
proc/RmBuiltSiegeBlow(turf/T, dmg, mob/Monsters/RemasterSiege/E, proj, sx, sy)
	var/key = "[T.x],[T.y],[T.z]"
	if(!rm_wall_max[key]) rm_wall_max[key] = max(1, RmBuiltWallHP(T))
	var/owner = RmBuiltOwnerKey(T)
	RemasterSiegeEvent(T, dmg, E, proj, sx, sy, "wall")
	T.rm_block_hurt += dmg
	for(var/k = RmBuiltTopK(T), k >= 0 && T.rm_block_hurt >= RmBlockHP(T, k), k = RmBuiltTopK(T))
		T.rm_block_hurt -= RmBlockHP(T, k)
		RmBuiltBlockFalls(T, k, E)
	if(RmBuiltTopK(T) >= 0) return
	// breached: no laid block left on top (a natural base stays rock)
	T.rm_block_hurt = 0
	rm_wall_max -= key
	view(T) << "<b><font color=red>The wall at [T.x],[T.y] comes crashing down!</font></b>"
	if(owner) RemasterRealmNotice(owner, "Siege: your wall at [T.x],[T.y] was smashed[E && E.Owner ? " by [E.Owner:RemasterHouse()]'s [lowertext(E.name)]" : ""]!")
	if(E && istype(E.Owner, /Player)) E.Owner:RemasterLog("Your [lowertext(E.name)] broke a wall at [T.x],[T.y].", "fight", T)

// Laid block k, the column's top, falls: it comes off, its marks are spent (nobody's pick is paid for it later), the
// units on the column come down, and 60% of the time one of its material lands beside it, on the engine's side.
proc/RmBuiltBlockFalls(turf/T, k, mob/E)
	var/wood = RmLaidMatOf(T, k) == "w"
	RemasterTakeTopBlock(T)
	RmLaidForget(T, k)
	RemasterFeetCheck(T)
	if(!prob(60)) return
	var/turf/D = (E && E.z == T.z) ? get_step(T, get_dir(T, E)) : null
	if(!D || D.density) D = (E && isturf(E.loc)) ? E.loc : T
	if(wood) new /obj/Items/woods/wood(D)
	else new /obj/Items/ores/stone(D)
