// Far-away units as records (server cost, planning/FAR_UNIT_RECORDS.md, 2026-10-24). The world's goal is 30,000 units,
// a million across the realms, and only watched land holding real units (memory unit-scale-30k). Awake.dm keeps the
// 16-tile chunks round players awake; a player's unit standing in asleep land is a full mob all the same (~55 KB, its
// clock jobs, its walk loop). Now a unit of a player who is not connected, quiet in asleep land for a minute, becomes a
// record: a list of what its saved vars hold that differs from its type (as a save would write it), its things (each a
// type and its vars, inside one another), the owner's lists it was in, where it stood, and when. The mob and its things
// are deleted. A record wakes into a full mob again, the same unit (vars, things, skills, wounds, uid, the owner's lists),
// when its chunk wakes (a player comes near), when anyone's creature or unit on its way somewhere (a raid, a chase)
// comes within a chunk of it, and when its owner connects. A unit standing somewhere it can't be put back (a wall went
// up) wakes on the nearest open tile.
// Its time asleep is not lost. Nothing in asleep land can be seen, so the record's clock only counts (no proc runs for
// it); on waking the unit lives that time through at once (8 hours at most) with the game's own procs, as Away.dm
// catches a village up, but at the live pace:
//  - its work first (woodcutters, miners, board workers on wood or stone, work-zone workers (Jobs.dm), haulers,
//    farmers): Away.dm's work procs on its work area, the goods onto the stores, with a budget of the time less what
//    meals and sleep took, times rm_far_rate (measured against live units in the arena);
//  - then its needs and health, by RmFarLiveThrough, which Away.dm's catch-up uses too: hunger and tiredness as the
//    clock jobs run them, real meals, sleep in a bed or rough, remedies, potions it uses by itself, stone for a
//    gargoyle; health only from those, never topped up for the time (Healing.dm). Nobody starves asleep: with no food
//    they wake hungry (Away.dm's rule, the user's, 2026-10-24).
// Units with anything going on stay full units: bleeding, stumps not yet stopped, ill, drunk, burning, captive, in a
// cage or a hole, on orders, fighting, walking, asleep or out cold, on a construction site or a board order, royal, the
// hero or heir, carrying a unit or regalia, and the races whose needs work differently (spiders, dragons, zombies,
// devourers, vampires). So are units with a link the record can't keep: anything but their own things, the land, their
// owner and the owner's other units (those are kept by uid, and units linked so wake together).
// Saves: the records are the owner's (Player/var/rm_far), written and read with the army by SaveUnits()/LoadUnits().
// Read back in another run, a record's time asleep runs from the real time it fell asleep (RemasterNow()), so the time
// the server was down counts too; Away.dm's catch-up passes over units that were records (rm_far_woke).

#define RM_FAR_EVERY 20          // ticks between the loop's looks (wakes)
#define RM_FAR_SWEEPS 3          // looks between sweeps for units to put to sleep
#define RM_FAR_QUIET 600         // ticks a unit is quiet in asleep land before it becomes a record
#define RM_FAR_MAX 28800         // seconds of time asleep lived through at most on waking (8 hours, as Away.dm)
#define RM_FAR_SETTLE 6000       // ticks a working record sleeps before it lives its time through (loose goods rot in ~30 min)
#define RM_FAR_SETTLE_LOOK 40    // working records woken for that in one look, at most
#define RM_FAR_BATCH 100         // records woken and lived through together (with their link groups)
#define RM_FAR_MEAL_SECS 20      // seconds a meal takes from work (the walk to the food and the eating)
#define RM_FAR_SLEEP_SECS 50     // seconds a night's sleep takes from work (the walk to bed and Sleep(300))
#define RM_FAR_MEAL_FOOD 50      // a meal's food value, for the work time only (the real meal's is used for hunger)
#define RM_FAR_TIRED_SPAN 3200   // seconds from rested (100) to tired (20) at 1 every 40 s

// a record (a list)
#define RMF_X 1
#define RMF_Y 2
#define RMF_Z 3
#define RMF_UID 4
#define RMF_TYPE 5
#define RMF_JOB 6
#define RMF_T0 7                 // world.time it fell asleep
#define RMF_REAL0 8              // RemasterNow() then
#define RMF_RUN 9                // the server run it fell asleep in (rm_far_run)
#define RMF_VARS 10              // list(names, value, value...): values encoded (RmFarEnc), names a shared list
#define RMF_ITEMS 11             // list(type, holder (0 the unit, else an earlier item's place), vars) per thing
#define RMF_LISTS 12             // list(owner's var, assoc value) per owner's list it was in
#define RMF_LINKS 13             // uids of the owner's units it holds
#define RMF_PLANTS 14            // a farmer's plants then: "x,y,z", fruit on it, ... (they go on growing while it sleeps)

var/rm_far_on = 0                        // the switch: 0 wakes every record and keeps every unit a full unit, as before (0 since 2026-10-24 ~23:10 until four arena checks pass with it on)
var/rm_far_auto = 1                      // 0: the loop leaves sleeping and waking to the caller (tests)
var/rm_far_tick_use = 10                 // ms of a tick (on the one tick ledger, Spread.dm) waking and sleeping take before going on next tick
var/rm_far_piece_at = 0                  // world.tick_usage where the work since the last pause began
var/rm_far_piece_tick = -1               // ...and in which tick
var/rm_far_settling = 0                  // a record is living its time through: Away.dm's work loops share the tick out
var/rm_far_quiet = RM_FAR_QUIET          // a var: tests shorten it
var/rm_far_pace = 1                      // 1: the live pace; Away.dm's own catch-up is at 0.5
// Seconds of Away.dm's work budget one second of live work is worth, per job: Away.dm's costs (a 20 s trip a job, the
// blows) against a live unit of a Human's own skills, measured in the arena (tests/far_records_test.dm FrHour, 2.5 and 5
// minutes: woodcutter 3.7 and 2.8+ (the wood ran out), miner 7.9, 7.4 and 6.5, hauler 4.25, 4.19 and 4.26; a farmer is
// held by its plants, not its time: 2 leaves the budget free).
var/list/rm_far_rate = list("woodcutter" = 3.5, "miner" = 7, "hauler" = 4.2, "farmer" = 2)
var/list/rm_far_kept_races = list("Spider", "Dragon", "Zombie", "Devourer", "Vampire")
var/rm_far_run
// Map regions kept on disk (the map-memory work): a datum with Loaded(x, y, z) and Load(x, y, z). In a region not in
// memory a record only counts its time (it never works the map unseen); it wakes once the region is loaded.
var/datum/rm_map_hook
var/list/rm_far_owners = list()          // Player -> how many records
var/list/rm_far_grid                     // chunk (Awake.dm's numbering) -> list(Player -> records there)
var/list/rm_far_cells = list()           // chunks holding records
var/list/rm_far_counts = list()          // what the loop did: "slept", "woke", "kept: <why>"...
var/rm_far_why                           // why the last unit looked at can't be a record
var/mob/rm_far_usr                       // usr while a unit is made (races' New() add to usr's stats)
var/list/rm_far_empty = list("~L")       // every empty list in every record (never changed)
var/list/rm_far_keep = list("~K")        // decoded: leave the var as the type made it
var/list/rm_far_names = list()           // "name,name..." -> that list of var names, shared by every record holding those
// Vars a record never keeps: the engine's own, where it stands (kept apart), and its things (kept apart).
var/list/rm_far_skip = list("vars"=1, "verbs"=1, "contents"=1, "overlays"=1, "underlays"=1, "vis_contents"=1,
	"vis_locs"=1, "loc"=1, "locs"=1, "x"=1, "y"=1, "z"=1, "type"=1, "parent_type"=1, "transform"=1, "filters"=1,
	"appearance"=1, "client"=1, "key"=1, "ckey"=1, "group"=1, "tag"=1, "images"=1, "screen"=1)

Player/var/list/rm_far                   // this player's units asleep as records (saved with the army)
Player/var/tmp
	rm_far_waking = 0
	list/rm_far_tally                    // what records did on waking, for the "While you were away" card
	list/rm_far_goods
	rm_far_settled = 0                   // the longest time asleep lived through since the card was last made (seconds)
	rm_far_left = 0                      // was connected in this run, then left: only such a player's units become records
mob/Monsters/var/tmp
	rm_far_quiet_at = 0                  // world.time it was first seen quiet in asleep land
	rm_far_woke = 0                      // world.time it woke from a record (Away.dm's catch-up passes over it)
	list/rm_far_plants                   // a farmer's plants when it fell asleep (RMF_PLANTS), until it has lived its time

// world/New: this file's part is step RmChainWorldNew_FarRecords in Code/Remastered/Chains/WorldNew.dm

proc/RmFarCount(what, n = 1)
	rm_far_counts[what] = (rm_far_counts[what] || 0) + n

// The one "behind" signal (planning/SYSTEMS_MAP.md Part 6 step 5): the work since the last pause goes on the tick
// ledger (RmTickCharge), and once optional work's room under rm_far_tick_use is used, the rest of the tick goes to
// others: orders and the track first, as for every optional piece (Spread.dm RmTickRoom).
proc/RmFarPause()
	if(rm_far_piece_tick == world.time) RmTickCharge(max(0, (world.tick_usage - rm_far_piece_at) * world.tick_lag))
	if(RmTickRoom(rm_far_tick_use) <= 0) sleep(1)
	rm_far_piece_tick = world.time
	rm_far_piece_at = world.tick_usage

// This server run (a record from another run counts its time asleep on the real clock).
proc/RmFarRun()
	if(!rm_far_run) rm_far_run = "[world.timeofday]-[rand(1000, 9999)]"
	return rm_far_run

var/rm_far_loop_n = 0
proc/RmFarLoop()   // every RM_FAR_EVERY ticks after each run ends (a run may pause, RmFarPause), on the unit clock
	if(rm_far_auto && remaster_world_ready)
		if(!rm_far_on)
			for(var/Player/P in rm_far_owners.Copy()) RmFarWakeOwner(P)
		else
			rm_far_loop_n++
			rm_far_piece_tick = world.time
			rm_far_piece_at = world.tick_usage
			RmFarWakeCheck(rm_far_loop_n % 3 == 0)        // wakes always: they must be done before anyone sees the land
			if(rm_shed_level < 1)                         // behind (Shed.dm): no self-settle and no new sleeping
				RmFarSettleDue()
				if(rm_far_loop_n % RM_FAR_SWEEPS == 0) RmFarSleepSweep()
	RmClockWorldBook("FarRecords", RM_FAR_EVERY)

// --- Asleep land -----------------------------------------------------------------------------------------------

proc/RmFarChunk(x, y, z)
	return ((z - 1) * rm_awake_h + round((y - 1) / RM_AWAKE_CHUNK)) * rm_awake_w + round((x - 1) / RM_AWAKE_CHUNK) + 1

// The grid of chunks holding records, the size of Awake.dm's (made again, with every record, if that changed).
proc/RmFarGridFit()
	if(world.time - rm_awake_at >= 10 || !rm_awake) RmAwakeRefresh()
	var/size = rm_awake_w * rm_awake_h * world.maxz
	if(rm_far_grid && length(rm_far_grid) == size) return
	rm_far_grid = new /list(size)
	rm_far_cells = list()
	for(var/Player/P in rm_far_owners) for(var/list/R in P.rm_far) RmFarIndex(P, R, 0)

proc/RmFarIndex(Player/P, list/R, count = 1)
	var/c = RmFarChunk(R[RMF_X], R[RMF_Y], R[RMF_Z])
	var/list/G = rm_far_grid[c]
	if(!G)
		G = list()
		rm_far_grid[c] = G
		rm_far_cells += c
	G[P] = (G[P] || 0) + 1
	if(count) rm_far_owners[P] = (rm_far_owners[P] || 0) + 1

proc/RmFarUnindex(Player/P, list/R)
	if(!rm_far_owners[P]) return     // read from a save, never indexed
	if(--rm_far_owners[P] <= 0) rm_far_owners -= P
	var/c = RmFarChunk(R[RMF_X], R[RMF_Y], R[RMF_Z])
	var/list/G = rm_far_grid[c]
	if(!G || !G[P]) return
	if(--G[P] <= 0) G -= P
	if(!length(G))
		rm_far_grid[c] = null
		rm_far_cells -= c

// --- Going to sleep --------------------------------------------------------------------------------------------

// Can it be a record now? 0 says why in rm_far_why.
mob/Monsters/proc/RmFarFits(Player/P)
	rm_far_why = null
	if(!isturf(loc) || !z) rm_far_why = "not on the ground"
	else if(HP <= 0 || GoingToDie) rm_far_why = "dying"
	else if(Egg || Wagon) rm_far_why = "an egg or a cart"
	else if(Race in rm_far_kept_races) rm_far_why = "its race"
	else if(IsRoyal || (remaster_uid && (remaster_uid == P.remaster_hero_uid || remaster_uid == P.remaster_heir_uid))) rm_far_why = "royal, the hero or the heir"
	else if(Sleeping || Fainted || Stunned || Meditating || Flying || IsMist) rm_far_why = "asleep, out cold or flying"
	else if(Caged || InHole || rm_cap_state || rm_cap_cage) rm_far_why = "captive"
	else if(destination || Target || remaster_defense || remaster_attack) rm_far_why = "busy"
	else if(length(remaster_orders) || (remaster_active && !remaster_active.automatic) || remaster_delivery) rm_far_why = "on orders"
	else if(remaster_care) rm_far_why = "looking after itself"
	else if(remaster_site || remaster_board_claim) rm_far_why = "on a site or a board order"
	else if(BleedType || RemasterStumpBusy() || OnFire) rm_far_why = "bleeding or burning"
	else if(rm_poison > 0 || rm_fever || rm_fever_incub || rm_foodsick > 0 || rm_drunk >= 15) rm_far_why = "ill or drunk"
	return !rm_far_why

// Every few seconds: units of players who aren't connected, quiet in asleep land for rm_far_quiet, become records.
proc/RmFarSleepSweep()
	if(world.time - rm_awake_at >= 10 || !rm_awake) RmAwakeRefresh()
	for(var/Player/P in world) if(!P.client && P.rm_far_left && length(P.UnitList))   // never a player who wasn't here (tests)
		var/list/batch = list()
		for(var/mob/Monsters/M in P.UnitList)
			if(M.Owner != P || RmAwake(M) || !M.RmFarFits(P))
				M.rm_far_quiet_at = 0
				continue
			if(!M.rm_far_quiet_at) M.rm_far_quiet_at = world.time
			else if(world.time - M.rm_far_quiet_at >= rm_far_quiet) batch += M
		if(length(batch)) RmFarSleep(P, batch)
		RmFarPause()

// Units become records, one at a time with the tick shared out between them; each one's look and record happen
// together (no other proc runs between them).
proc/RmFarSleep(Player/P, list/batch)
	var/list/fits = list()
	for(var/mob/Monsters/M in batch)
		if(M.Owner == P && M.RmFarFits(P)) fits[M] = 1
		else RmFarCount("kept: [rm_far_why || "not theirs"]")
	// a unit an awake unit of the owner holds stays awake
	if(length(fits) < length(P.UnitList)) for(var/mob/Monsters/X in P.UnitList) if(!fits[X])
		for(var/v in X.vars)
			if(rm_far_skip[v]) continue
			var/val = X.vars[v]
			if(ismob(val) && fits[val]) fits -= val
			else if(islist(val) && length(val) < 500) for(var/e in val) if(ismob(e) && fits[e]) fits -= e
	RmFarGridFit()
	if(!P.rm_far) P.rm_far = list()
	. = 0
	for(var/mob/Monsters/M in fits)
		RmFarPause()
		if(M == null || M.Owner != P || !M.RmFarFits(P)) continue     // died or changed while it waited (a deleted unit == null)
		var/list/R = RmFarRecord(M, P)
		if(!R)
			RmFarCount("kept: [rm_far_why]")
			continue
		R[RMF_LISTS] = RmFarUnlist(P, M) || rm_far_empty
		P.rm_far += list(R)
		RmFarIndex(P, R)
		if(hascall(P, "RmJobUnitGone")) call(P, "RmJobUnitGone")(M)   // work zones' running totals (Jobs.dm)
		RmFarDelete(M)
		RmFarCount("slept")
		.++

// The unit and all it carries, as a record; null (rm_far_why) when it holds something a record can't keep.
proc/RmFarRecord(mob/Monsters/M, Player/P)
	rm_far_why = null
	if(!M.remaster_uid) M.remaster_uid = RemasterNewUID()
	var/list/objs = list()
	var/list/holders = list()
	if(!RmFarThings(M, 0, objs, holders)) return null
	var/list/places = list()
	for(var/i = 1, i <= length(objs), i++) places[objs[i]] = i
	var/list/ctx = list("owner" = P, "places" = places, "links" = list())
	var/list/V = RmFarVars(M, ctx)
	if(rm_far_why) return null
	var/list/items = list()
	for(var/i = 1, i <= length(objs), i++)
		var/atom/movable/O = objs[i]
		var/list/IV = RmFarVars(O, ctx)
		if(rm_far_why) return null
		items.len++
		items[items.len] = list(O.type, holders[i], IV)
	var/list/links = ctx["links"]
	var/list/plants = rm_far_empty
	if(M.remaster_job == "farmer")
		plants = list()
		for(var/obj/Items/Plants/G in range(REMASTER_FOOD_AREA, M.RemasterFoodArea())) if(istype(G, /obj/Items/Plants/TomatoPlant) || istype(G, /obj/Items/Plants/GrapeVine))
			plants += "[G.x],[G.y],[G.z]"
			plants += G.Content
	return list(M.x, M.y, M.z, M.remaster_uid, M.type, M.remaster_job, world.time, RemasterNow(), RmFarRun(), V,
		length(items) ? items : rm_far_empty, null, length(links) ? links : rm_far_empty, plants)

// What A holds, depth first, each with the place of what holds it (0 the unit).
proc/RmFarThings(atom/A, holder, list/objs, list/holders)
	for(var/atom/movable/O in A)
		if(!isobj(O))
			rm_far_why = "carrying [O.name]"
			return 0
		if(istype(O, /obj/Items/Equipment/Armour/Crown))
			rm_far_why = "carrying regalia"
			return 0
		objs += O
		holders += holder
		if(length(O.contents) && !RmFarThings(O, length(objs), objs, holders)) return 0
	return 1

// Its saved vars that differ from its type's: list(names, values...). Units of a kind mostly differ in the same vars,
// so the names list is shared (rm_far_names) and a record holds only the values.
proc/RmFarVars(datum/D, list/ctx)
	var/list/names = list()
	var/list/out = list(null)
	for(var/v in D.vars)
		if(rm_far_skip[v] || !issaved(D.vars[v])) continue
		var/val = D.vars[v]
		if(!islist(val) && val == initial(D.vars[v])) continue
		var/e = RmFarEnc(val, ctx)
		if(rm_far_why) return null
		names += v
		out.len++
		out[out.len] = e
	var/key = jointext(names, ",")
	if(!rm_far_names[key]) rm_far_names[key] = names
	out[1] = rm_far_names[key]
	return out

// A value as a record keeps it: plain values as they are; lists, files, tiles and links as tagged lists.
proc/RmFarEnc(val, list/ctx, depth = 0)
	if(isnull(val) || isnum(val) || istext(val) || ispath(val)) return val
	if(depth > 6)
		rm_far_why = "lists too deep"
		return null
	if(islist(val))
		var/list/L = val
		if(!length(L)) return rm_far_empty
		var/list/out = list("~L")
		for(var/k in L)
			var/a = (isnum(k) || isnull(k)) ? null : L[k]
			out.len += 2
			out[out.len - 1] = RmFarEnc(k, ctx, depth + 1)
			out[out.len] = RmFarEnc(a, ctx, depth + 1)
			if(rm_far_why) return null
		return out
	if(isfile(val)) return list("~F", "[val]")
	if(isturf(val)) return list("~T", val:x, val:y, val:z)
	if(val == ctx["owner"]) return list("~O")
	var/list/places = ctx["places"]
	if(isobj(val) && places[val]) return list("~I", places[val])
	if(istype(val, /mob/Monsters) && val:Owner == ctx["owner"])
		if(!val:remaster_uid) val:remaster_uid = RemasterNewUID()
		var/list/links = ctx["links"]
		links |= val:remaster_uid
		return list("~U", val:remaster_uid)
	rm_far_why = "holds [istype(val, /datum) ? "[val:type]" : "[val]"]"
	return null

// Takes the unit out of the owner's lists (UnitList, quick groups...) and says which, with its assoc value there.
proc/RmFarUnlist(Player/P, mob/Monsters/M)
	for(var/v in P.vars)
		if(rm_far_skip[v]) continue
		var/list/L = P.vars[v]
		if(!islist(L) || !(M in L)) continue
		var/a = L[M]
		var/list/out = . || list()
		out.len++
		out[out.len] = list(v, (isnum(a) || istext(a)) ? a : null)
		. = out
		L -= M

// The things first (innermost last), then the unit.
proc/RmFarDelete(mob/Monsters/M)
	var/list/objs = list()
	var/list/holders = list()
	RmFarThings(M, 0, objs, holders)
	for(var/i = length(objs), i >= 1, i--)
		var/atom/movable/O = objs[i]
		O.loc = null
		del O
	del M

// --- Waking ----------------------------------------------------------------------------------------------------

// Every couple of seconds: records whose owner connected, whose chunk woke, or which something on its way came near.
proc/RmFarWakeCheck(walkers)
	if(!length(rm_far_owners)) return
	RmFarGridFit()
	var/list/hot = list()          // "chunk" -> 1
	for(var/c in rm_far_cells) if(rm_awake[c]) hot["[c]"] = 1
	if(walkers) for(var/mob/Monsters/X in world)
		if(!(X.destination || X.Target) || !isturf(X.loc)) continue
		if(istype(X.Owner, /Player) && !X.Owner:client) continue
		var/cx = round((X.x - 1) / RM_AWAKE_CHUNK)
		var/cy = round((X.y - 1) / RM_AWAKE_CHUNK)
		for(var/dy = -1, dy <= 1, dy++)
			if(cy + dy < 0 || cy + dy >= rm_awake_h) continue
			for(var/dx = -1, dx <= 1, dx++)
				if(cx + dx < 0 || cx + dx >= rm_awake_w) continue
				var/c = ((X.z - 1) * rm_awake_h + cy + dy) * rm_awake_w + cx + dx + 1
				if(rm_far_grid[c]) hot["[c]"] = 1
	for(var/Player/P in rm_far_owners.Copy())
		if(P.client)
			RmFarWakeOwner(P)
			continue
		if(!length(hot)) continue
		var/list/W = list()
		for(var/list/R in P.rm_far) if(hot["[RmFarChunk(R[RMF_X], R[RMF_Y], R[RMF_Z])]"]) W += list(R)
		if(length(W)) RmFarWakeOwner(P, W)

// A working record's goods would rot where they lie (Vars.dm ItemDecay: loose wood, ore and food go in about half an
// hour) while a live worker carries them in: so every RM_FAR_SETTLE (10 min) it wakes, lives its time through, and goes back to
// sleep at the next sweep (rm_far_quiet_at set back).
proc/RmFarSettleDue()
	if(!length(rm_far_owners)) return
	var/n = 0
	for(var/Player/P in rm_far_owners.Copy())
		if(P.client || P.rm_far_waking) continue
		var/list/W = list()
		for(var/list/R in P.rm_far)
			if(R[RMF_RUN] != RmFarRun() || world.time - R[RMF_T0] < RM_FAR_SETTLE) continue
			if(!RmFarMapIn(R, 0)) continue
			if(!(R[RMF_JOB] in rm_far_rate) && R[RMF_JOB] != "board" && !RmFarHeld(R, "rm_jz_id")) continue
			W += list(R)
			if(++n >= RM_FAR_SETTLE_LOOK) break
		if(!length(W)) continue
		RmFarWakeOwner(P, W)
		for(var/list/R in W) for(var/mob/Monsters/M in P.UnitList) if(M.remaster_uid == R[RMF_UID] && M.rm_far_woke == world.time)
			M.rm_far_quiet_at = world.time - rm_far_quiet       // asleep again at the next sweep
		if(n >= RM_FAR_SETTLE_LOOK) return

// Is the record's tile in memory (rm_map_hook)? load: have it loaded now if it can be.
proc/RmFarMapIn(list/R, load)
	if(!rm_map_hook || !hascall(rm_map_hook, "Loaded") || call(rm_map_hook, "Loaded")(R[RMF_X], R[RMF_Y], R[RMF_Z])) return 1
	if(load && hascall(rm_map_hook, "Load")) call(rm_map_hook, "Load")(R[RMF_X], R[RMF_Y], R[RMF_Z])
	return load && call(rm_map_hook, "Loaded")(R[RMF_X], R[RMF_Y], R[RMF_Z])

// Does the record hold a value for var v?
proc/RmFarHeld(list/R, v)
	var/list/V = R[RMF_VARS]
	var/list/names = V[1]
	var/i = names.Find(v)
	return i && V[i + 1]

// Their owner's records W (null: all) wake, with any linked to them, and live their time asleep through: nearest a
// connected player first, RM_FAR_BATCH at a time, each with its whole link group (so links find each other), the tick
// shared out (rm_far_tick_use).
proc/RmFarWakeOwner(Player/P, list/W)
	if(P.rm_far_waking || !length(P.rm_far)) return 0
	P.rm_far_waking = 1
	var/list/by_uid = list()
	var/list/nbrs = list()       // uid -> uids it is linked with, both ways
	for(var/list/R in P.rm_far) by_uid[R[RMF_UID]] = R
	for(var/list/R in P.rm_far) for(var/u in R[RMF_LINKS]) if(u != "~L" && by_uid[u])
		RmFarLink(nbrs, R[RMF_UID], u)
		RmFarLink(nbrs, u, R[RMF_UID])
	W = RmFarNearestFirst(W || P.rm_far.Copy())
	var/list/taken = list()
	var/list/batch = list()
	. = 0
	for(var/list/R in W)
		if(taken[R[RMF_UID]]) continue
		var/list/todo = list(R[RMF_UID])
		while(length(todo))
			var/u = todo[length(todo)]
			todo.len--
			if(taken[u] || !by_uid[u]) continue
			taken[u] = 1
			batch += list(by_uid[u])
			for(var/v in nbrs[u]) if(!taken[v]) todo += v
		if(length(batch) >= RM_FAR_BATCH)
			. += RmFarWakeSome(P, batch)
			batch = list()
	if(length(batch)) . += RmFarWakeSome(P, batch)
	P.rm_far_waking = 0

proc/RmFarWakeSome(Player/P, list/batch)
	var/list/woken = RmFarWakeBatch(P, batch)
	if(length(woken)) RmFarSettle(P, woken)
	return length(woken)

proc/RmFarLink(list/nbrs, a, b)
	var/list/L = nbrs[a]
	if(!L)
		L = list()
		nbrs[a] = L
	L |= b

// Records nearest a connected player's camera first (by 16 tiles), the rest after.
proc/RmFarNearestFirst(list/W)
	var/list/eyes = list()
	for(var/client/C) if(istype(C.mob, /Player) && C.mob.z) eyes += C.mob
	if(!length(eyes) || length(W) < 2) return W
	var/list/B = new /list(66)
	for(var/list/R in W)
		var/d = 1#INF
		for(var/mob/E in eyes) if(E.z == R[RMF_Z]) d = min(d, max(abs(E.x - R[RMF_X]), abs(E.y - R[RMF_Y])))
		var/i = min(65, round(d / 16)) + 1
		if(!B[i]) B[i] = list()
		B[i] += list(R)
	. = list()
	for(var/list/L in B) . += L

// Seconds it has been asleep: on the game's clock in this run, else on the real one (the server may have been down).
proc/RmFarAsleep(list/R)
	if(R[RMF_RUN] == RmFarRun()) return max(0, (world.time - R[RMF_T0]) / 10)
	var/t = RemasterSince(R[RMF_REAL0])
	return isnum(t) ? max(0, t / 10) : 0

// Units from records: all made first, with their things, then their vars, so links between them find each other.
// Returns unit -> seconds asleep.
proc/RmFarWakeBatch(Player/P, list/W)
	. = list()
	if(!rm_far_usr) rm_far_usr = new /mob
	var/list/made = list()     // unit -> list(record, things, ctx)
	var/list/uids = list()
	for(var/list/R in W)
		if(!RmFarMapIn(R, 1)) continue            // its region isn't in memory: it waits for it
		var/turf/T = locate(R[RMF_X], R[RMF_Y], R[RMF_Z])
		if(!T) continue
		var/path = R[RMF_TYPE]
		if(!ispath(path)) path = text2path("[path]")
		if(!path) continue
		usr = rm_far_usr
		var/mob/Monsters/M = new path(T)
		for(var/atom/movable/A in M.contents.Copy()) del A       // the gear its kind's New() hands out
		var/list/objs = list()
		for(var/list/I in R[RMF_ITEMS])
			var/ipath = I[1]
			if(!ispath(ipath)) ipath = text2path("[ipath]")
			var/atom/holder = I[2] ? objs[I[2]] : M
			var/obj/O = ipath && holder ? new ipath(holder) : null
			if(O) for(var/atom/movable/A in O.contents.Copy()) del A   // what its New() put in it
			objs.len++
			objs[objs.len] = O
		made[M] = list(R, objs)
		if(length(R) >= RMF_PLANTS && length(R[RMF_PLANTS]) > 1) M.rm_far_plants = R[RMF_PLANTS]
		uids[R[RMF_UID]] = M
		.[M] = RmFarAsleep(R)
		P.rm_far -= list(R)
		RmFarUnindex(P, R)
		RmFarPause()
	for(var/mob/Monsters/M in made)
		RmFarPause()
		var/list/D = made[M]
		var/list/R = D[1]
		var/list/objs = D[2]
		var/list/ctx = list("owner" = P, "objs" = objs, "uids" = uids)
		var/i = 0
		for(var/list/I in R[RMF_ITEMS])
			i++
			if(objs[i]) RmFarApply(objs[i], I[3], ctx)
		RmFarApply(M, R[RMF_VARS], ctx)
		M.Owner = P
		for(var/list/m in R[RMF_LISTS])
			var/list/L = P.vars[m[1]]
			if(!islist(L))
				L = list()
				P.vars[m[1]] = L
			L += M
			if(!isnull(m[2])) L[M] = m[2]
		if(!(M in P.UnitList)) P.UnitList += M
		if(M.loc.density || !RemasterTilePlaces(M.loc, list(M)))
			var/turf/O = RemasterNearestOpen(M.loc, M)
			if(O) M.loc = O
		M.RebuildOverlays()
		M.rm_far_woke = world.time
		if(hascall(P, "RmJobUnitBack")) call(P, "RmJobUnitBack")(M)
		RmFarCount("woke")

// The record's values; a saved var it doesn't hold was the type's own, so one New() changed (a race's random skin,
// stats) goes back to it.
proc/RmFarApply(datum/D, list/V, list/ctx)
	var/list/held = list()
	var/list/names = V[1]
	for(var/i = 2, i <= length(V), i++)
		var/v = names[i - 1]
		held[v] = 1
		if(!(v in D.vars)) continue
		var/val = RmFarDec(V[i], ctx)
		if(val == rm_far_keep) continue
		D.vars[v] = val
	for(var/v in D.vars)
		if(held[v] || rm_far_skip[v] || !issaved(D.vars[v])) continue
		var/val = D.vars[v]
		if(islist(val)) continue        // lists are always held; one it doesn't hold was null, as the type makes it
		var/was = initial(D.vars[v])
		if(val != was) D.vars[v] = was

proc/RmFarDec(e, list/ctx)
	if(!islist(e)) return e
	var/list/L = e
	switch(L[1])
		if("~L")
			var/list/out = list()
			for(var/i = 2, i < length(L), i += 2)
				var/k = RmFarDec(L[i], ctx)
				var/a = RmFarDec(L[i + 1], ctx)
				out.len++
				out[out.len] = k
				if(!isnull(a) && !isnum(k)) out[k] = a
			return out
		if("~F")
			if(fexists(L[2])) return file(L[2])
			if(fexists("Icons/[L[2]]")) return file("Icons/[L[2]]")
			return rm_far_keep
		if("~T") return locate(L[2], L[3], L[4])
		if("~O") return ctx["owner"]
		if("~I")
			var/list/objs = ctx["objs"]
			return L[2] <= length(objs) ? objs[L[2]] : null
		if("~U")
			var/list/uids = ctx["uids"]
			if(uids[L[2]]) return uids[L[2]]
			var/Player/P = ctx["owner"]
			for(var/mob/Monsters/M in P.UnitList) if(M.remaster_uid == L[2]) return M
			return null
	return null

// --- Living the time asleep through --------------------------------------------------------------------------

// units: unit -> seconds asleep. Work first (what it brings in is there for the meals), then needs, meals in turn.
proc/RmFarSettle(Player/P, list/units)
	var/list/tally0 = P.remaster_away_tally
	var/list/goods0 = P.remaster_away_goods
	P.remaster_away_tally = P.rm_far_tally || list()
	P.remaster_away_goods = P.rm_far_goods || list()
	var/list/needs = list()
	for(var/mob/Monsters/M in units)
		var/secs = min(units[M], RM_FAR_MAX)
		if(secs < 1) continue
		needs[M] = secs
		P.rm_far_settled = max(P.rm_far_settled, secs)
		RemasterTouchAround(M)         // its land's tiles as they were, so the save sees what the work changes (WorldSave.dm)
		P.remaster_away_started = world.timeofday
		rm_far_settling++
		M.RmFarWork(P, secs)
		rm_far_settling--
		RmFarPause()
	RmFarLiveThrough(P, needs)
	P.rm_far_tally = P.remaster_away_tally
	P.rm_far_goods = P.remaster_away_goods
	P.remaster_away_tally = tally0
	P.remaster_away_goods = goods0

// Its job over secs, less the time meals and sleep took: Away.dm's work procs with a live-paced budget.
mob/Monsters/proc/RmFarWork(Player/P, secs)
	if(remaster_role_paused || remaster_paused) return
	var/role = remaster_job
	if(role == "board") role = (remaster_board_role in list("woodcutter", "miner")) ? remaster_board_role : null
	var/list/zone   // a work zone's row (Jobs.dm): the job, the zone's centre, what it still wants
	if(("rm_jz_id" in vars) && vars["rm_jz_id"] && hascall(P, "RmJobAsleep"))
		zone = call(P, "RmJobAsleep")(src)
		role = islist(zone) ? zone["job"] : null
		if(islist(zone) && isnum(zone["left"]) && zone["left"] <= 0) role = null
	if(!(role in rm_far_rate)) return
	var/eats = !RmFarEats() ? 0 : secs / 40 * (Race == "Lizardman" ? 0.5 : 1) / RM_FAR_MEAL_FOOD
	var/sleeps = RemasterNeedsSleep() ? secs / RM_FAR_TIRED_SPAN : 0
	var/budget = max(0, secs - eats * RM_FAR_MEAL_SECS - sleeps * RM_FAR_SLEEP_SECS) * rm_far_pace * rm_far_rate[role]
	if(budget <= 0) return
	var/list/area = list(remaster_area_x, remaster_area_y, remaster_area_z)
	if(zone)
		remaster_area_x = zone["x"]
		remaster_area_y = zone["y"]
		remaster_area_z = zone["z"]
	// Away.dm's work procs stop at REMASTER_AWAY_JOBS a call: a live miner can dig more than that in 5 minutes, so a
	// minute at a time.
	var/slices = max(1, -round(-secs / 60))
	switch(role)
		if("woodcutter", "miner") for(var/i = 1, i <= slices, i++)
			P.remaster_away_started = world.timeofday
			RemasterAwayHarvest(P, budget / slices, role)
			RmFarPause()
		if("hauler") for(var/i = 1, i <= slices, i++)
			RemasterAwayHaul(P, budget / slices)
			RmFarPause()
		if("farmer") RmFarFarm(P, secs, budget)
	remaster_area_x = area[1]
	remaster_area_y = area[2]
	remaster_area_z = area[3]

// Its plants went on growing live (a fruit every 2 minutes up to 5, PlantRegen) but stopped full; tended, each would
// have given the fruit it had then and one every 2 minutes since. That is put on them to pick, at most 100 fruit a
// call (Away.dm's farm picks REMASTER_AWAY_PICKS a call and leaves each plant at 2).
mob/Monsters/proc/RmFarFarm(Player/P, secs, budget)
	var/list/G0 = rm_far_plants
	rm_far_plants = null
	if(!G0) return RemasterAwayFarm(P, secs, budget)
	var/list/plants = list()      // plant -> fruit to pick
	var/total = 0
	for(var/i = 1, i < length(G0), i += 2)
		var/list/c = splittext(G0[i], ",")
		var/turf/T = locate(text2num(c[1]), text2num(c[2]), text2num(c[3]))
		if(T) for(var/obj/Items/Plants/G in T) if(istype(G, /obj/Items/Plants/TomatoPlant) || istype(G, /obj/Items/Plants/GrapeVine))
			var/n = max(0, G0[i + 1] - 1) + round(secs / 120)
			plants[G] = n
			total += n
	var/slices = max(1, -round(-total / 100))
	for(var/s = 1, s <= slices, s++)
		for(var/obj/Items/Plants/G in plants) if(G)
			var/n = round(plants[G] / slices) + (s == slices ? plants[G] % slices : 0)
			G.Content = 1 + n
		RemasterAwayFarm(P, 0, budget / slices)
		RmFarPause()

// What this player's records will have brought in so far, roughly, until they wake and the real result replaces it
// (the village overview and the job board): time asleep (8 hours at most) times rm_far_per_hour. Kept 10 s.
var/list/rm_far_per_hour = list("woodcutter" = list("wood", 33), "miner" = list("stone", 210), "hauler" = list("things", 359), "farmer" = list("food", 198))   // what one live worker brought in an hour in the arena (FrHour)
Player/var/tmp/list/rm_far_expected
Player/var/tmp/rm_far_expected_at = -1000
Player/proc/RmFarExpected()
	if(world.time - rm_far_expected_at < 100 && rm_far_expected) return rm_far_expected
	rm_far_expected_at = world.time
	rm_far_expected = list()
	for(var/list/R in rm_far)
		var/job = R[RMF_JOB]
		var/list/E = istext(job) ? rm_far_per_hour[job] : null
		if(!E) continue
		rm_far_expected[E[1]] = (rm_far_expected[E[1]] || 0) + round(min(RmFarAsleep(R), RM_FAR_MAX) / 3600 * E[2])
	return rm_far_expected

// --- Living a span of time through at once (records waking, and Away.dm's catch-up) --------------------------
// Health over the span comes only as it does live (Healing.dm, the user, 2026-10-23 and 2026-10-24): the meals it eats,
// the sleep it gets, a Doctor's or the stall's remedies, what it uses from its bag by itself, a gargoyle's stone.
// Nothing tops it up for the time alone. units: unit -> seconds.
//  1. At the start, as in the first minutes live: a bleeding stump is treated from its own bag or a friend's, by a
//     villager carrying something for it, by the Doctor (its bag, the stall's poultices or one made from Athelas, a
//     torch or bandage from a store), or at a fire close by (Stumps.dm's choices and their effects); then the stump
//     ticks run (bleeding, a bandaged one slowly, until treated or dead; blood coming back; festering).
//  2. The clock jobs' ticks (one every 40 s): hunger to the hungry mark, a meal; tiredness to the tired mark, a sleep:
//     its own bed or a free one within 30 tiles (claimed, as Care.dm does), Sleep(300 - comfort) healing +10 every
//     10 s and resting fully; else rough, Sleep(450) healing +5 every 10 s and resting to 70 only. The Heal tick
//     that falls in a sleep mends limbs and organs. Everyone takes one event in turn, so food runs out evenly.
//  3. After each event, and at the start, what it would do for itself or have done: the bag's use-it-yourself
//     potions, a carried remedy, the Doctor's or the stall's remedy when ill or badly hurt (Doctor.dm
//     RemasterNeeds), stone for a gargoyle's limbs (StoneLimbs.dm).
proc/RmFarLiveThrough(Player/P, list/units)
	var/list/cache = list("beds" = list())   // the stores' food best first and beds by chunk, found once for everyone here
	var/list/claimed = list()      // beds taken, as Care.dm keeps them
	for(var/mob/Monsters/M in P.UnitList) if(M.Owner == P && islist(M.remaster_home) && length(M.remaster_home) == 3)
		claimed["[M.remaster_home[1]],[M.remaster_home[2]],[M.remaster_home[3]]"] = M
	var/list/S = list()            // unit -> list(ticks left, hunger per tick, tiredness per tick, no food left)
	for(var/mob/Monsters/M in units)
		if(M.HP <= 0 || M.GoingToDie) continue
		var/secs = units[M]
		if(M.RemasterStumpBusy()) M.RmFarStumps(P, secs)
		if(!M || M.HP <= 0 || M.GoingToDie) continue      // bled to death (a deleted unit is false)
		var/n = round(secs * 10 / 400)
		M.RmFarTreat(P)
		RmFarPause()
		if(n <= 0) continue
		M.RmFarSlowMends(n)
		var/rh = M.RmFarEats() ? (M.Race == "Lizardman" ? 0.5 : 1) : 0
		var/rt = M.RemasterNeedsSleep() ? 1 : 0
		if(!rt && M.Tiredness < 100) M.Tiredness += 0.5 * min(n, -round(-(100 - M.Tiredness) / 0.5))   // Elves and their kin rest awake
		S[M] = list(n, rh, rt, 0)
	var/meals = 0
	var/sleeps = 0
	var/busy = length(S)
	while(busy)
		busy = 0
		for(var/mob/Monsters/M in S)
			var/list/Q = S[M]
			if(Q[1] <= 0 || !M || M.HP <= 0 || M.GoingToDie) continue
			// ticks to its next meal and its next sleep: each tick drops hunger and tiredness, and the tick that takes
			// one to its mark brings the meal (HungerTick's EatSomething, or Care.dm's walk to food) or the sleep (Care.dm)
			var/kh = (Q[2] && !Q[4]) ? (M.Hunger > REMASTER_CARE_HUNGRY ? -round(-(M.Hunger - REMASTER_CARE_HUNGRY) / Q[2]) : 1) : 1#INF
			var/kt = Q[3] ? (M.Tiredness > REMASTER_CARE_TIRED ? -round(-(M.Tiredness - REMASTER_CARE_TIRED)) : 1) : 1#INF
			var/k = min(kh, kt, Q[1])
			Q[1] -= k
			if(Q[2]) M.Hunger = Q[4] ? max(REMASTER_CARE_HUNGRY, M.Hunger - Q[2] * k) : M.Hunger - Q[2] * k
			if(Q[3]) M.Tiredness -= k
			if(k == kh)
				if(M.RmFarMeal(P, cache)) meals++
				else
					Q[4] = 1                                  // no food: it stays hungry, it doesn't starve
					M.Hunger = max(M.Hunger, REMASTER_CARE_HUNGRY)
					P.RemasterAwayAdd("hungry")
			if(k == kt)
				M.RmFarSleepOnce(P, claimed, cache)
				sleeps++
			M.RmFarTreat(P)
			if(Q[1] > 0) busy = 1
			RmFarPause()
	P.RemasterAwayAdd("meals", meals)
	P.RemasterAwayAdd("slept", sleeps)

mob/Monsters/proc/RmFarEats()
	return !(Race in list("Gargoyle", "Zombie", "Devourer", "Vampire")) && !InHole

// A meal as the unit would have had it: a food pot or stall's serving first (as Away.dm always served them), then
// what it carries or lies by it (HungerTick's EatSomething), else the best food on the stores (Care.dm's walk to food).
mob/Monsters/proc/RmFarMeal(Player/P, list/cache)
	if(RemasterAwayMeal(P)) return 1          // FoodSupply.dm; Healing.dm adds the meal's healing
	if(EatSomething()) return 1
	var/obj/Items/Food/F = cache ? RmFarStoreFood(P, cache) : P.RemasterAwayFood(src)
	if(!F) return 0
	ForcePickUpItem(F)
	if(EatItem(F)) return 1
	return F.loc != src                       // a rotten one thrown away still took the attempt (a deleted F is not null)

// The best food on the stores for src, as Away.dm's RemasterAwayFood picks it (cooked meat, then fruit, then raw meat
// for meat eaters, then anything), from a list made once for everyone living their time through together.
mob/Monsters/proc/RmFarStoreFood(Player/P, list/cache)
	var/list/B = cache["food"]
	if(!B)
		B = list(list(), list(), list(), list())   // cooked meat, fruit, raw meat, the rest
		var/n = 0
		for(var/turf/S in P.RemasterStores()) for(var/obj/Items/Food/F in range(1, S)) if(isturf(F.loc) && P.RemasterMayCollect(F))
			var/i = F.icon_state == "CookedMeat" ? 1 : (F.icon_state in list("Tomato", "Grape")) ? 2 : F.icon_state == "RawMeat" ? 3 : 4
			B[i] += F
			if(++n % 200 == 0) RmFarPause()
		cache["food"] = B
	for(var/i in (Carn ? list(1, 2, 3, 4) : list(1, 2, 4)))
		var/list/L = B[i]
		while(length(L))
			var/obj/Items/Food/F = L[1]
			if(!F || !isturf(F.loc))
				L.Cut(1, 2)                // eaten or gone
				continue
			if(F.z != z) break
			L.Cut(1, 2)
			return F
	return null

// Beds within 30 tiles of src (Care.dm's reach), found a 16-tile chunk at a time and kept for everyone.
mob/Monsters/proc/RmFarBedsNear(list/cache)
	var/list/C = cache["beds"]
	. = list()
	var/cx = round((x - 1) / 16)
	var/cy = round((y - 1) / 16)
	for(var/gy = cy - 2, gy <= cy + 2, gy++) for(var/gx = cx - 2, gx <= cx + 2, gx++)
		if(gx < 0 || gy < 0 || gx * 16 >= world.maxx || gy * 16 >= world.maxy) continue
		var/k = "[gx],[gy],[z]"
		var/list/L = C[k]
		if(!L)
			L = list()
			for(var/turf/T in block(locate(gx * 16 + 1, gy * 16 + 1, z), locate(min(world.maxx, gx * 16 + 16), min(world.maxy, gy * 16 + 16), z)))
				for(var/obj/Items/Furniture/Beds/B in T) L += B
			C[k] = L
			RmFarPause()
		for(var/obj/Items/Furniture/Beds/B in L) if(B && isturf(B.loc) && get_dist(B, src) <= 30) . += B

// One sleep, as Care.dm sends a tired unit to it: its bed, else a free bed within 30 tiles, else rough. Healing.dm
// heals it every 10 s asleep; the Heal tick that falls in the sleep (one every 40 s) mends limbs and organs.
mob/Monsters/proc/RmFarSleepOnce(Player/P, list/claimed, list/cache)
	var/obj/Items/Furniture/Beds/B = RemasterBedAt(remaster_home)
	if(!B && remaster_home) remaster_home = null
	if(!B && isturf(loc))
		var/best_d = 31
		for(var/obj/Items/Furniture/Beds/C in (cache ? RmFarBedsNear(cache) : range(30, src)))
			if(!isturf(C.loc) || (C.Owner && C.Owner != P)) continue
			var/key = "[C.x],[C.y],[C.z]"
			if(claimed[key] && claimed[key] != src) continue
			var/d = get_dist(C, src)
			if(d < best_d)
				B = C
				best_d = d
		if(B)
			remaster_home = list(B.x, B.y, B.z)
			claimed["[B.x],[B.y],[B.z]"] = src
	var/bed = B && B.z == z
	var/ticks = bed ? max(40, 300 - B.CR) : 450
	Tiredness = bed ? 100 : 70              // a rough sleep rests it to 70 (Care.dm)
	if(HP > 0) HP = min(MAXHP, HP + round((ticks - 1) / 100) * (bed ? RM_HEAL_BED : RM_HEAL_ROUGH))
	var/mends = round(ticks / 400) + prob((ticks % 400) / 4)
	for(var/i = 1, i <= mends, i++)
		Sleeping = 1
		HealTick()
		Sleeping = 0

// A bleeding stump, treated as in the first minutes live (Stumps.dm), then its ticks for the span.
mob/Monsters/proc/RmFarStumps(Player/P, secs)
	if(RemasterStumpBleeding())
		// its own bag or a friend's within 3 tiles, by itself (the "stump" rule)
		if(RemasterAutoUseOn("stump"))
			var/list/hands = list()
			var/list/holders = list()
			RemasterStumpNear(hands, holders)
			for(var/list/O in RemasterStumpChoices(hands, holders, 0)) if(O["kind"] != "restore" && RemasterStumpDo(O, P)) break
		// a villager carrying something for it
		if(RemasterStumpBleeding())
			var/mob/Monsters/H = P.RemasterStumpHelper(src)
			if(H) for(var/list/O in RemasterStumpChoices(list(H), list(H), 0)) if(RemasterStumpDo(O, P)) break
		// the Doctor
		if(RemasterStumpBleeding())
			var/mob/Monsters/D = P.RmFarDoctor(src)
			if(D) D.RmFarDoctorStump(P, src)
		// a fire close by, while it can walk
		if(RemasterStumpBleeding() && CanWalk && RemasterStumpCanTreat() && isturf(loc))
			var/atom/F = RemasterFireNear(src, RM_STUMP_FIRE_WALK)
			if(F) RemasterStumpSeal(src, "the [RemasterFireName(F)]", 20, 12)
	// the stump's ticks and, while it bleeds, the original's Bleeding tick (both every 5 s: blood drawn, the rolls to
	// bleed to death)
	for(var/i = 1, i <= round(secs * 10 / rm_stump_every), i++)
		if(BleedType) BleedingTick()
		if(!src || HP <= 0 || GoingToDie || !RemasterStumpTick()) break

// A Doctor of P's who can reach M: one with the job, on its level, within its reach.
Player/proc/RmFarDoctor(mob/Monsters/M)
	for(var/mob/Monsters/D in UnitList)
		if(D.Owner != src || D.remaster_job != "doctor" || D.HP <= 0 || D.GoingToDie || D.Wagon || D.Race == "Spider") continue
		if(!isturf(D.loc) || D.z != M.z || get_dist(D, M) > RM_DOCTOR_REACH || !D.RemasterStumpCanTreat()) continue
		return D
	return null

// The Doctor's stump care (Stumps.dm RemasterDoctorStump), without the walking: what it carries, else a poultice
// from the stall (made from Athelas if none), else a torch or bandage from a store.
mob/Monsters/proc/RmFarDoctorStump(Player/P, mob/Monsters/pat)
	for(var/n = 1, n <= 3 && pat.RemasterStumpBleeding(), n++)
		for(var/list/O in pat.RemasterStumpChoices(list(src), list(src), 0)) if(O["kind"] != "restore" && pat.RemasterStumpDo(O, P)) return 1
		var/mob/WorkShops/RemasterClinic/S = P.RemasterClinicWith("poultice", src)
		if(S)
			S.TakeOut("poultice", src)
			continue
		S = P.RemasterClinicWith("athelas", src)
		if(S)
			if(S.Make("athelas", src) > 0) S.TakeOut("poultice", src)
			continue
		var/obj/Items/I = P.RemasterStumpKitLying(src, pat)
		if(!I) return 0
		ForcePickUpItem(I)
	return 0

// What it does for itself, or has done, now (Bag.dm, Doctor.dm, Care.dm, StoneLimbs.dm).
mob/Monsters/proc/RmFarTreat(Player/P)
	if(HP <= 0 || GoingToDie) return
	// the bag's use-it-yourself potions
	var/need = RemasterNeededPotion()
	if(need)
		var/obj/Items/I = RemasterFindSupply(need)
		if(I && (I.loc == src || RemasterHandOver(I, I.loc, src))) P.RemasterUseFor(src, I)
	// a gargoyle's limbs: stone it or a friend carries, else stone the Doctor brings from a store
	if(RemasterStoneBody() && length(RemasterStoneNeeds()))
		var/list/hands = list()
		var/list/holders = list()
		if(RemasterAutoUseOn("stone"))
			RemasterStumpNear(hands, holders)
			while(RemasterStoneTreatNow(hands, holders)) continue
		var/mob/Monsters/D = length(RemasterStoneNeeds()) ? P.RmFarDoctor(src) : null
		if(D)
			var/turf/ST = P.RemasterStoreWith(/obj/Items/ores/stone, D)
			if(ST && get_dist(ST, D) <= RM_DOCTOR_REACH) for(var/obj/Items/ores/stone/X in range(1, ST))
				if(length(RemasterStonesIn(list(D))) >= RM_STONE_REBUILD * 4) break
				if(P.RemasterMayCollect(X)) D.ForcePickUpItem(X)
			while(RemasterStoneTreatNow(list(D), list(D, src))) continue
	// ill or badly hurt: a carried remedy, else the Doctor's or the stall's
	for(var/n = 1, n <= 3, n++)
		var/list/N = RemasterNeeds()
		if(!N) return
		var/remedy = N[1]
		var/obj/Items/RemasterRemedy/R = RemasterCarriedRemedy(remedy)
		var/mob/Monsters/by = src
		if(!R || !RemasterAutoUseOn("remedy"))
			by = P.RmFarDoctor(src) || src
			var/mob/WorkShops/RemasterClinic/S = P.RemasterClinicWith(remedy, by)
			if(!S && by != src)           // the Doctor makes one from the herb
				var/herb = RemasterHerbOf(remedy)
				S = P.RemasterClinicWith(herb, by)
				if(S && S.Make(herb, by) <= 0) S = null
			R = S ? S.TakeOut(remedy, by) : null
		if(!R) return
		var/mob/H = R.loc
		if(!RemasterApplyRemedy(remedy, by)) return
		if(ismob(H)) H.weight -= R.weight
		del R

// What the clock jobs do for every unit, n 40-second ticks: the Heal tick's brain and lungs, a caster's mana; the
// regrowing races' RegenTick (60 s).
mob/Monsters/proc/RmFarSlowMends(n)
	for(var/part in list("BrainHP", "LeftLungHP", "RightLungHP")) if(vars[part] < 100)
		vars[part] += 0.05 * min(n, -round(-(100 - vars[part]) / 0.05))
	if(MagicalAptitude && Mana < MaxMana)
		var/per = MagicalConcentration / 2
		for(var/obj/Items/Equipment/Armour/Chestplate/ChaosRobe/C in src) if(C.suffix == "(Equipped)") per += 5
		for(var/obj/Items/Equipment/Armour/Helmet/ChaosHood/C in src) if(C.suffix == "(Equipped)") per += 5
		for(var/obj/Items/Equipment/Armour/Capes/ChaosCape/C in src) if(C.suffix == "(Equipped)") per += 5
		Mana = min(MaxMana, Mana + per * n)
	if(Race == "Lizardman" || SubRace == "Werewolf")
		for(var/i = 1, i <= min(round(n * 400 / 600), 30), i++) RegenTick()

// The owner connects: their records wake (RmFarWakeCheck) before the catch-up looks at the army; time records lived
// through goes on the "While you were away" card, with the catch-up's when there is one (Away.dm).
// A catch-up (the first connection of a run, Away.dm) takes the records' tallies onto its own card; otherwise, after a
// relog in the same run (the catch-up runs once a run), the records' card is the only one.
Player/RemasterAwayTick()
	if(client) rm_far_left = 1         // the track runs only for a connected player: from now on, when it leaves
	if(length(rm_far) || rm_far_waking)
		if((client || !rm_far_on) && !rm_far_waking) spawn(0) RmFarWakeOwner(src)   // records read back from a save are in no grid
		return
	. = ..()
	if(rm_far_settled >= REMASTER_AWAY_MIN / 10 && remaster_caught_up && !remaster_catching_up)
		var/list/tally0 = remaster_away_tally
		var/list/goods0 = remaster_away_goods
		remaster_away_tally = rm_far_tally || list()
		remaster_away_goods = rm_far_goods || list()
		var/span = rm_far_settled * 10
		remaster_away_report = RemasterAwayReport(span, span, list(), 0)
		var/lines = jointext(remaster_away_report["lines"], " · ")
		RemasterLog("While you were away ([RemasterAwaySpan(span)]): [lines]", "work", RemasterStockpile())
		remaster_away_tally = tally0
		remaster_away_goods = goods0
		rm_far_settled = 0
		rm_far_tally = null
		rm_far_goods = null
