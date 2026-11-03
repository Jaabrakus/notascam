// Tiers to climb: settlement ranks (Camp -> Hamlet -> Village -> Town -> Kingdom),
// metal ages (Stone -> Iron -> Silver -> Gold -> Adamantium) and one-off
// milestones. Everything is measured from the real world (units, workshops, walls,
// farmland, ingots, births, raids, a crowned ruler) every few seconds; a rank once
// reached is kept. Each rank unlocks something (other players may join, traders
// visit, titles, vassals).

#define RM_PROGRESS_EVERY 50      // ticks between measurements
#define RM_PROGRESS_RANGE 40      // tiles around the settlement that count

var/list/rm_ranks = list(
	list("id"="camp", "name"="Camp", "unlock"="Your story begins."),
	list("id"="hamlet", "name"="Hamlet", "unlock"="Other players may ask to join your settlement.",
		"need"=list(list("pop", 5, "people"), list("shops", 2, "workshops"), list("farm", 4, "farmland tiles"))),
	list("id"="village", "name"="Village", "unlock"="Trade caravans start to visit.",
		"need"=list(list("pop", 10, "people"), list("shops", 5, "workshops"), list("walls", 30, "wall tiles"), list("age", 2, "the Iron Age"))),
	list("id"="town", "name"="Town", "unlock"="Your ruler may take a Town's title, wearing a Silver Circlet; bigger caravans.",
		"need"=list(list("pop", 20, "people"), list("births", 3, "children born here"), list("raids", 1, "raids beaten"), list("age", 3, "the Silver Age"), list("hall", 1, "a dining hall"))),
	list("id"="kingdom", "name"="Kingdom", "unlock"="A crowned King or Queen; other settlements may swear fealty.",
		"need"=list(list("pop", 35, "people"), list("walls", 120, "wall tiles"), list("regalia", 5, "a ruler wearing the Gold Crown"), list("age", 4, "the Gold Age"), list("throne", 1, "a throne room"))))

var/list/rm_ages = list(
	list("Stone Age", null),
	list("Iron Age", /obj/Items/Ingots/IronIngot),
	list("Silver Age", /obj/Items/Ingots/SilverIngot),
	list("Gold Age", /obj/Items/Ingots/GoldIngot),
	list("Adamantium Age", /obj/Items/Ingots/AdamantiumIngot))

// id -> list(label, test on stats)
var/list/rm_milestones = list(
	"workshop"=list("First workshop", "shops", 1),
	"farm"=list("First field tilled", "farm", 1),
	"wall"=list("First wall raised", "walls", 1),
	"birth"=list("First child born", "births", 1),
	"iron"=list("Iron smelted", "age", 2),
	"silver"=list("Silver smelted", "age", 3),
	"gold"=list("Gold smelted", "age", 4),
	"adamant"=list("Adamantium!", "age", 5),
	"pop10"=list("Ten people", "pop", 10),
	"pop25"=list("Twenty-five people", "pop", 25),
	"raid"=list("A raid beaten", "raids", 1),
	"crown"=list("A ruler crowned", "ruler", 1),
	"bedroom"=list("A proper bedroom", "bedrooms", 1),
	"hall"=list("A dining hall", "hall", 1),
	"throne"=list("A throne room", "throne", 1))

Player/var
	remaster_rank = 1                 // saved: index in rm_ranks
	remaster_age = 1                  // saved: best metal age reached
	list/remaster_achieved            // saved: milestone id -> day reached
	remaster_raids_won = 0            // saved
	remaster_open = 0                 // saved: others may join (Hamlet+)
	remaster_trade_open = 0           // saved: caravans visit (Village+)
Player/var/tmp
	list/remaster_progress_stats
	remaster_progress_at = 0
	remaster_raid_watch = 0

Player/proc/RemasterProgressCenter()
	var/turf/T = RemasterStockpile()
	if(T) return T
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0 && isturf(M.loc)) return M.loc
	return loc

Player/proc/RemasterAgeOf(obj/Items/I)
	for(var/i = length(rm_ages), i >= 2, i--)
		var/list/A = rm_ages[i]
		var/k = A[2]
		if(istype(I, k)) return i
	return 1

Player/proc/RemasterProgressMeasure()
	var/list/S = list("pop"=0, "shops"=0, "walls"=0, "farm"=0, "births"=0, "ruler"=0, "regalia"=0, "age"=remaster_age, "raids"=remaster_raids_won, "hall"=0, "throne"=0, "bedrooms"=0)
	RemasterRoomsScan()
	S["hall"] = RemasterRoomCount("hall")
	S["throne"] = RemasterRoomCount("throne")
	S["bedrooms"] = RemasterRoomCount("bedroom") + RemasterRoomCount("dorm")
	var/turf/C = RemasterProgressCenter()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0)
		S["pop"]++
		if(M.remaster_generation > 1 || M.remaster_born) S["births"]++
		if(M.IsRoyal)
			S["ruler"] = 1
			S["regalia"] = max(S["regalia"], M.RmRegaliaTier())   // the best regalia a ruler wears (Rulership.dm)
		for(var/obj/Items/Ingots/I in M) S["age"] = max(S["age"], RemasterAgeOf(I))
	// members and vassals count toward the realm they belong to
	if(!remaster_liege) for(var/Player/R in RemasterRealmPlayers())
		for(var/mob/Monsters/M in R.UnitList) if(M.Owner == R && M.HP > 0) S["pop"]++
	for(var/mob/WorkShops/W in world) if(W.Owner == src) S["shops"]++
	if(C)
		var/list/G = RmProgressGround(C)
		S["walls"] += G[1]
		S["farm"] += G[2]
		S["age"] = max(S["age"], G[3])
	// a raid is beaten when the raiders that were here are all gone and we are not: our own raid's (another realm's raid
	// ending gave every player in the world "A raid beaten")
	var/alive = 0
	for(var/mob/Monsters/R in remaster_raiders) if(R && R.HP > 0)
		var/list/D = remaster_raiders[R]
		if(!islist(D) || length(D) < 6 || D[6] == src) alive++
	if(alive) remaster_raid_watch = 1
	else if(remaster_raid_watch)
		remaster_raid_watch = 0
		if(S["pop"] > 0)
			RemasterLog("The raid is over: no raiders are left marching on you.", "good", null)
			remaster_raids_won++
			RemasterCheer("raid", "We beat the raiders", 10, 2)
			S["raids"] = remaster_raids_won
	remaster_age = max(remaster_age, S["age"])
	remaster_progress_stats = S
	return S

// The ground round the settlement: walls and fields built or tilled there, and the best age of the ingots smelted there.
// Each 16x16 chunk's part of the box is kept while its RmChunkKey and the part's bounds hold (load-asleep-1030, 10-31, the
// owner: "Exact, engine counter"; planning/MANY_PLAYERS_PLAN_2026-10-31.md): a scan works out only the chunks that
// changed. It read every tile of the 81x81 box about every 3 s for every player. RM_SCAN_VERIFY=1: the whole box worked
// out too, a different total logged.
Player/var/tmp/list/rm_ground_parts   // "cx,cy,z" -> list(key, walls, farm, age)
Player/proc/RmProgressGround(turf/C)
	var/r = RM_PROGRESS_RANGE
	var/x0 = max(1, C.x - r)
	var/y0 = max(1, C.y - r)
	var/x1 = min(world.maxx, C.x + r)
	var/y1 = min(world.maxy, C.y + r)
	var/walls = 0
	var/farm = 0
	var/age = 0
	var/list/parts = list()
	for(var/cy = round((y0 - 1) / 16), cy <= round((y1 - 1) / 16), cy++)
		for(var/cx = round((x0 - 1) / 16), cx <= round((x1 - 1) / 16), cx++)
			var/ck = "[cx],[cy],[C.z]"
			var/sx0 = max(x0, cx * 16 + 1)
			var/sy0 = max(y0, cy * 16 + 1)
			var/sx1 = min(x1, cx * 16 + 16)
			var/sy1 = min(y1, cy * 16 + 16)
			var/key = "[sx0],[sy0],[sx1],[sy1]|" + RmChunkKey(cx, cy, C.z, ck)
			var/list/P = rm_ground_parts && rm_ground_parts[ck]
			if(!P || P[1] != key) P = list(key) + RmGroundPart(sx0, sy0, sx1, sy1, C.z)
			parts[ck] = P
			walls += P[2]
			farm += P[3]
			age = max(age, P[4])
	rm_ground_parts = parts
	if(RmScanVerify())
		var/list/W = RmGroundPart(x0, y0, x1, y1, C.z)
		if(W[1] != walls || W[2] != farm || W[3] != age)
			rm_scan_differ++
			world.log << "RMSCAN|ground differs|[C.x],[C.y],[C.z]|kept [walls],[farm],[age]|whole [W[1]],[W[2]],[W[3]]"
	return list(walls, farm, age)

// One box of the ground (RmProgressGround): list(walls, farm, age).
Player/proc/RmGroundPart(x0, y0, x1, y1, z)
	var/walls = 0
	var/farm = 0
	var/age = 0
	for(var/turf/T in block(locate(x0, y0, z), locate(x1, y1, z)))
		// only what was built or tilled here, not walls and fields that came with the map
		if(T.IsWall && T.density)
			if(RemasterTileChanged(T)) walls++
		else if(T.remaster_laid && RmLaidCount(T) >= 2) walls++   // a wall-high column of laid blocks (Plans.dm)
		else if(T.icon_state == "FarmLand" && RemasterTileChanged(T)) farm++
		// ingots smelted here, not loot that came with the map or someone else's (playtest: "Gold smelted" on day 1)
		for(var/obj/Items/Ingots/I in T) if((I.remaster_runtime || !remaster_map_items[I]) && (!I.Owner || I.Owner == src))
			age = max(age, RemasterAgeOf(I))
	return list(walls, farm, age)

Player/proc/RemasterRankMet(i, list/S)
	var/list/R = rm_ranks[i]
	for(var/list/N in R["need"]) if((S[N[1]] || 0) < N[2]) return 0
	return 1

Player/proc/RemasterProgressTick()
	if(world.time < remaster_progress_at) return
	remaster_progress_at = world.time + RM_PROGRESS_EVERY
	// no people yet (the race pick) or none left: nothing here is theirs, so nothing to measure
	var/alive = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0)
		alive = 1
		break
	if(!alive) return
	var/list/S = RemasterProgressMeasure()
	if(!remaster_achieved) remaster_achieved = list()
	for(var/id in rm_milestones) if(!remaster_achieved[id])
		var/list/D = rm_milestones[id]
		if((S[D[2]] || 0) >= D[3])
			remaster_achieved[id] = max(1, remaster_days)
			RemasterRecordAchievement(id)     // kept across games: better odds for rare races (Rarity.dm)
			RemasterLog("Milestone: [D[1]]", "good", null)
			RemasterNotice("Milestone: [D[1]]")
	while(remaster_rank < length(rm_ranks) && RemasterRankMet(remaster_rank + 1, S))
		remaster_rank++
		RemasterRankUp()

Player/proc/RemasterRankUp()
	var/list/R = rm_ranks[remaster_rank]
	var/id = R["id"]
	if(id == "hamlet") remaster_open = 1
	if(id == "village") remaster_trade_open = 1
	RemasterCheer("rank", "Our [lowertext(R["name"])] grows", 10, 3)
	var/text = "Your settlement is now a [R["name"]]! [R["unlock"]]"
	RemasterLog(text, "good", null)
	RemasterNotice(text)
	// the ruler's seat rises with the regalia they wear: a new title then, else what to make (Rulership.dm)
	RmSeatRankUp()
	src << "<b><font color=#f2d27a>[text]</font></b>"

Player/proc/RemasterProgressData()
	var/list/S = remaster_progress_stats || RemasterProgressMeasure()
	var/list/R = rm_ranks[remaster_rank]
	var/list/next = remaster_rank < length(rm_ranks) ? rm_ranks[remaster_rank + 1] : null
	var/list/needs = list()
	if(next) for(var/list/N in next["need"])
		var/have = S[N[1]] || 0
		var/label = N[3]
		if(N[1] == "age")
			var/list/AG = rm_ages[N[2]]
			label = "Reach [AG[1]]"
			have = min(have, N[2])
		needs += list(list("label"=label, "have"=have, "need"=N[2], "done"=have >= N[2]))
	var/list/ms = list()
	for(var/id in rm_milestones)
		var/list/D = rm_milestones[id]
		ms += list(list("id"=id, "label"=D[1], "day"=(remaster_achieved && remaster_achieved[id]) || 0))
	var/list/ranks = list()
	for(var/i = 1, i <= length(rm_ranks), i++)
		var/list/X = rm_ranks[i]
		ranks += list(list("name"=X["name"], "unlock"=X["unlock"], "reached"=i <= remaster_rank))
	var/list/A = rm_ages[remaster_age]
	var/list/NA = remaster_age < length(rm_ages) ? rm_ages[remaster_age + 1] : null
	return list("rank"=R["name"], "rankIndex"=remaster_rank, "next"=(next ? next["name"] : null), "nextUnlock"=(next ? next["unlock"] : null),
		"needs"=needs, "age"=A[1], "ageIndex"=remaster_age, "nextAge"=(NA ? NA[1] : null), "milestones"=ms, "ranks"=ranks,
		"stats"=S, "open"=remaster_open, "trade"=remaster_trade_open, "banners"=length(RemasterBanners()), "rooms"=RemasterRoomsData(), "mood"=RemasterMoodAverage(), "coins"=remaster_coins, "radius"=RemasterClaimRadius())
