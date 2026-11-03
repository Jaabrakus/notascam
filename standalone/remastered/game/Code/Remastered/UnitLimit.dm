// A world-wide soft limit on units (the owner approved, 11-01): on the public server, once the world holds the limit's
// number of living units (every unit, wild creatures and every player's people together), new births, migrants and wild
// or monster spawns wait until the count drops below it again. Nobody loses a unit; growth just waits. The limit is 5,000
// on a server run with RM_PUBLIC=1; RM_UNIT_MAX=<n> sets it on any server (0 = off). A Mac app world (no RM_PUBLIC) has
// none unless RM_UNIT_MAX is set. A brand-new player's starting company always comes (Restart.dm's MakeMany is never
// held): only births, migrants and wild spawns wait.
//
// Held, here: a birth (GiveBirth: the baby stays in its mother, the hatchling in its egg, tried again every
// rm_unit_retry), a stolen beast egg's hatching (Taming.dm RmHatch: it lies warm till there is room), migrants (a newcomer
// is not offered a realm to join, so their company founds its own land; they may swear fealty later, which brings nobody
// new) and the season's raid on a settlement (Raids.dm RemasterRaid). Held in their own files: the original random army
// (Raids.dm RemasterSeasonChanged), the biomes' morning creatures (Biomes.dm), critters dug out of the rock
// (Chains/Bump.dm), golems rising (Golems.dm) and a great kobold's two avengers (Creatures/Death.dm).
// Not held: units coming back (a log-in, a world load), a cave's monsters (Instances.dm: at most 12 caves, wiped when the
// party leaves; held, a cave would be empty treasure), a caravan's three merchants (they leave), a company's re-rolls,
// and what players make (raised skeletons, gargoyles, siege engines, ships). world.Repop() does nothing on this engine.
//
// The count: never a walk over every unit at each check. RmUnitCount walks the world's mobs at most once every
// rm_unit_recount ticks, and only when something asks while the limit is on (off, nothing is counted); what the game lets
// in between counts is added to the number at once (RmUnitAdd), so a burst of births or a raid can't run far past the
// limit, and deaths show at the next count. Counted: every mob/Monsters but chests and carts (Wagon), unhatched eggs,
// siege engines and ships, and the dying.

#define RM_UNIT_MAX_PUBLIC 5000

var/rm_unit_max = -1                 // the limit: -1 until read (RmUnitMax), 0 off
var/rm_unit_recount = 50             // ticks a count is kept for (5 s)
var/rm_unit_retry = 100              // a held birth is tried again after this many ticks (10 s)
var/rm_unit_say_every = 6000         // a realm is told at most once in this many ticks (10 minutes)
var/rm_unit_n = 0                    // living units at the last count, and those let in since
var/rm_unit_counted = -1000000       // world.time of the last count
var/rm_unit_logged = -1000000        // world.time of the last "crowded" line in world.log
Player/var/tmp/rm_unit_said = -1000000   // when this realm was last told the world is crowded

proc/RmUnitMax()
	if(rm_unit_max < 0)
		var/v = world.GetConfig("env", "RM_UNIT_MAX")
		var/n = (istext(v) && length(v)) ? text2num(v) : null
		rm_unit_max = isnum(n) ? max(0, round(n)) : (RmPublicWorld() ? RM_UNIT_MAX_PUBLIC : 0)
	return rm_unit_max

// The living units: counted again once the last count is rm_unit_recount old.
proc/RmUnitCount()
	if(world.time >= rm_unit_counted + rm_unit_recount)
		rm_unit_counted = world.time
		var/n = 0
		for(var/mob/Monsters/M in world) if(!M.Wagon && !M.Egg && !M.GoingToDie && !istype(M, /mob/Monsters/RemasterSiege)) n++
		rm_unit_n = n
		if(rm_unit_max > 0 && n >= rm_unit_max && world.time >= rm_unit_logged + rm_unit_say_every)
			rm_unit_logged = world.time
			world.log << "RMUNITS|crowded|t=[world.time]|units=[n]|max=[rm_unit_max]"
	return rm_unit_n

// Room for one more: below the limit (always, with it off).
proc/RmUnitRoom()
	var/most = rm_unit_max < 0 ? RmUnitMax() : rm_unit_max
	return !most || RmUnitCount() < most

// n let in since the last count.
proc/RmUnitAdd(n = 1)
	if(rm_unit_max && n > 0) rm_unit_n += n

// Count again at the next look (a whole army came).
proc/RmUnitSoon()
	rm_unit_counted = -1000000

// One quiet line in a realm's log while its growth waits, at most once every rm_unit_say_every.
proc/RmUnitHeld(Player/P)
	if(!istype(P) || world.time < P.rm_unit_said + rm_unit_say_every) return
	P.rm_unit_said = world.time
	P.RemasterLog("The world is crowded: births and newcomers wait for room.", "info", null)

// --- births ---------------------------------------------------------------------------------------------------------
// The baby (or an egg's hatchling) waits where it is and is tried again every rm_unit_retry, so it comes once there is
// room; the mother stays expecting meanwhile (no second child begins), and one who dies first takes it with her, as before.
mob/Monsters/GiveBirth()
	if(CHILDTYPE && CHILDCOUNT > 0 && !RmUnitRoom())
		RmUnitHeld(Owner)
		spawn(rm_unit_retry) if(!Rm3DGone(src)) GiveBirth()
		return
	if(CHILDTYPE) RmUnitAdd(max(1, CHILDCOUNT))
	return ..()

// A stolen beast egg laid down warm: it hatches once there is room (the taming loop asks again every 2 s).
obj/Items/RmBeastEgg/RmHatch()
	if(!RmUnitRoom())
		RmUnitHeld(RmEggPlayer(src))
		return
	RmUnitAdd(1)
	return ..()

// --- migrants -------------------------------------------------------------------------------------------------------
// While the world is full a newcomer isn't offered a realm to join: their starting company comes all the same and founds
// its own land. Told so only when there was a realm to join.
Player/proc/RmUnitMigrantsWait()
	if(RmUnitRoom()) return 0
	if(length(RemasterOpenRealms(src))) RemasterNotice("The world is crowded: realms take no migrants until there is room. Your people found their own land.")
	return 1

Player/RemasterMigrantChoice()
	if(RmUnitMigrantsWait()) return null
	return ..()

// --- raids ----------------------------------------------------------------------------------------------------------
// No band this season while the world is full; the raiders who come are added to the count.
Player/RemasterRaid()
	if(!RmUnitRoom()) return 0
	var/had = length(remaster_raiders)
	. = ..()
	RmUnitAdd(length(remaster_raiders) - had)
