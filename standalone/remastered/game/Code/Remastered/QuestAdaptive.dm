// Quests that come and go with the stores and the world (planning/QUEST_MAKER_PLAN_2026-10-31.md section 8, phase Q8;
// the owner's "Yes, all eight", 10-31, with question 6 "world notices in Q8"):
//  - standing notices: the maker sets "keep at least 50 iron bars, pay 3 coins each" on a Bring notice, and it goes up by
//    itself for what the stores lack (counted in the maker's stores on the board's level) and comes down while nobody has
//    taken it once they are full again. The coins are taken from the treasury as each notice goes up. Players set the
//    price; the game never does;
//  - the going rate: the post form's hint of what a good sold for lately at market stalls (Market.dm), a hint only;
//  - what this party can manage: a board's notices rated for the viewer's people there (their real Attack, Strength,
//    Defence, health and armour, as a fort's danger is: QuestForts.dm RmFortPower) against a fort's garrison, a creature
//    to slay, a cave's danger; sorted that way on ask;
//  - fort reports: each try keeps its numbers (party, who fell, the posts that lost someone), and the maker's card sums
//    them ("the way in fell in 3 of 4 tries");
//  - world notices: the world posts notices with no giver, for a stone golem walking (Golems.dm) and a great beast's lair
//    with its hoard (Instances.dm). The prize is the place itself, never coins from nothing. The map's ruins aren't known
//    to the game as places yet, so "a ruin was found" waits for them.

#define RM_QUEST_STANDING_MAX 3       // standing notices a realm may keep
#define RM_QUEST_STANDING_WAIT 3000   // after one is done: the goods lie by the board a while before the stores count them
#define RM_QUEST_SALES_KEPT 10        // sales kept for each good, for the going rate
#define RM_WORLD_DAYS 7               // a world notice stays up this long, then goes up again while its thing is there

var/rm_world_key = "*world*"          // the world's notices' maker: no player's key looks like it
var/list/rm_quest_sales = list()      // saved with the quests: "type path" -> list(list(price, day))
var/rm_adapt_ticks = 0
Player/var/list/rm_quest_standing     // saved: list(list("id", "item", "itemName", "keep", "each", "quality", "board", "who", "rank", "days", "title", "text", "quest", "have", "note"))
Player/var/rm_quest_standing_serial = 0
Player/var/tmp/rm_quest_sort          // the board card's order: "manage" (what this party can manage) or newest

world/New()
	spawn(1200) RmQuestLoop()   // the world's notices go up with no player's notice to start the loop
	. = ..()

// Every 30 s (Quests.dm RmQuestTick): standing notices each minute, world notices every two.
proc/RmAdaptTick()
	rm_adapt_ticks++
	if(rm_adapt_ticks % 2 == 0) for(var/client/C) if(istype(C.mob, /Player) && length(C.mob:rm_quest_standing)) C.mob:RmStandingTick()
	if(rm_adapt_ticks % 4 == 1) RmWorldNoticePass()

// --- standing notices ---------------------------------------------------------------------------------------------------
proc/RmStandingWanted(list/A)
	return islist(A) && (!A["kind"] || A["kind"] == "bring") && !A["token"] && (text2num("[A["keep"]]") || 0) > 0

Player/proc/RmStandingMake(list/A)
	var/mob/Monsters/M = RemasterUIUnit(A["unit"])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return null
	var/mob/WorkShops/RemasterNoticeBoard/B = RmQuestBoardBeside(M, 1)
	if(!B)
		RemasterNotice("[M.RemasterBareName()] must stand by your notice board to post.")
		return null
	if(RmModMuted(key) || RmModPostBanned(key))
		RemasterNotice("An admin has stopped you posting notices for now.")
		return null
	if(length(rm_quest_standing) >= RM_QUEST_STANDING_MAX)
		RemasterNotice("A realm keeps at most [RM_QUEST_STANDING_MAX] standing notices. Stop one first (Quests, Ours).")
		return null
	var/path = text2path("[A["item"]]")
	if(!path || !RmQuestGoods()["[path]"])
		RemasterNotice("Pick what the notice asks for.")
		return null
	var/keep = clamp(round(text2num("[A["keep"]]") || 0), 1, 200)
	var/each = clamp(round(text2num("[A["each"]]") || 0), 0, 1000)
	if(!each)
		RemasterNotice("Set what you pay for each one.")
		return null
	var/days = text2num("[A["days"]]")
	if(!(days in rm_quest_days)) days = 3
	var/list/S = list("id"="s[++rm_quest_standing_serial]", "item"="[path]", "itemName"=RmQuestGoodName(path), "keep"=keep, "each"=each,
		"quality"=((A["quality"] in rm_quest_qualities) ? A["quality"] : null), "board"=list(B.x, B.y, B.z),
		"who"=((A["who"] in list("anyone", "others", "realm")) ? A["who"] : "anyone"), "rank"=clamp(round(text2num("[A["rank"]]") || 1), 1, length(rm_ranks)),
		"days"=days, "title"=RmModFilter(RmQuestText(A["title"], 40)), "text"=RmModFilter(RmQuestText(A["text"], 300)), "quest"=null, "have"=0, "note"="")
	if(!rm_quest_standing) rm_quest_standing = list()
	rm_quest_standing += list(S)
	rm_quest_post_open = 0
	RmStandingCheck(S)
	if(S["quest"]) rm_quest_card = S["quest"]
	RemasterNotice("Standing notice set: keep [keep] [S["itemName"]] in your stores, [each] coins each. [S["note"]].")
	RemasterLog("Standing notice: keep [keep] [S["itemName"]], [each] coins each", "good", B)
	return null

Player/proc/RmStandingTick()
	for(var/list/S in rm_quest_standing) RmStandingCheck(S)

// The stores against what it keeps: a notice up for what they lack, down (while nobody took it) once they are full.
Player/proc/RmStandingCheck(list/S)
	var/list/BP = S["board"]
	var/path = text2path("[S["item"]]")
	if(!path) return
	var/have = RemasterStoreCount(path, BP[3])
	S["have"] = have
	var/list/Q = S["quest"] ? rm_quests[S["quest"]] : null
	if(Q && Q["state"] != "open" && Q["state"] != "closing")
		if(Q["state"] == "done") S["wait"] = world.time + RM_QUEST_STANDING_WAIT   // its goods lie by the board a while
		Q = null
		S["quest"] = null
	if(have >= S["keep"])
		if(Q && Q["state"] == "open" && !length(Q["takers"]))
			RmQuestEnd(Q, "the stores are full again")
			S["quest"] = null
		S["note"] = "The stores are full"
		return
	if(Q)
		S["note"] = "A notice is up"
		return
	if(world.time < (S["wait"] || 0))
		S["note"] = "Done lately: the goods are by your notice board"
		return
	RmStandingPost(S, min(200, S["keep"] - have), have)

Player/proc/RmStandingPost(list/S, need, have)
	var/mob/WorkShops/RemasterNoticeBoard/B = RmQuestBoardAt(S["board"])
	if(!B || RmQuestBoardKey(B) != key)
		S["note"] = "Its notice board is gone"
		return null
	if(RmModMuted(key) || RmModPostBanned(key))
		S["note"] = "An admin has stopped your notices"
		return null
	var/cap = rm_quest_open_cap[clamp(remaster_rank, 1, length(rm_quest_open_cap))]
	if(RmQuestRealmOpen() >= cap)
		S["note"] = "Waiting: your realm has all the notices it may"
		return null
	var/coins = need * S["each"]
	if(remaster_coins < coins + RM_QUEST_POST_COST)
		S["note"] = "Waiting: [coins + RM_QUEST_POST_COST] coins needed, the treasury has [remaster_coins]"
		return null
	remaster_coins -= coins + RM_QUEST_POST_COST
	var/id = "q[++rm_quest_serial]"
	var/title = length(S["title"]) ? S["title"] : "Bring [need] [S["itemName"]]"
	var/list/Q = list("id"=id, "kind"="bring", "maker"=key, "house"=RemasterHouse(), "title"=title, "text"=S["text"],
		"board"=list(B.x, B.y, B.z), "item"=S["item"], "itemName"=S["itemName"], "need"=need, "quality"=S["quality"],
		"coins"=coins, "goods"=list(), "goodsNames"=list(), "worth"=coins, "who"=S["who"], "rank"=S["rank"],
		"state"="open", "posted"=RemasterNow(), "ends"=RmQuestLater(S["days"]), "days"=S["days"],
		"takers"=list(), "realms_done"=list(), "stats"=list("taken"=0, "done"=0, "gaveup"=0), "standing"=S["id"])
	Q["region"] = RmQuestRegion(B.x, B.y, B.z)   // its region (QuestScale.dm)
	RmQuestJournal(Q, "Posted by itself: the stores had [have] of [S["keep"]]")
	rm_quests[id] = Q
	RmQuestChanged()
	spawn(0) RmQuestLoop()
	S["quest"] = id
	S["note"] = "A notice is up"
	RemasterLog("Standing notice: [title] ([coins] coins)", "good", B)
	return id

// The Quests page's Ours: each standing notice and how it stands.
Player/proc/RmStandingRows()
	. = list()
	for(var/list/S in rm_quest_standing)
		. += list(list("id"=S["id"], "itemName"=S["itemName"], "keep"=S["keep"], "each"=S["each"], "have"=S["have"], "note"=S["note"], "quest"=S["quest"]))

// --- the going rate --------------------------------------------------------------------------------------------------
// A sale at a market stall (Market.dm): kept for the post form's hint.
proc/RmQuestSold(path, price)
	var/k = "[path]"
	var/list/L = rm_quest_sales[k]
	if(!L) L = rm_quest_sales[k] = list()
	var/list/N = RemasterNow()
	L += list(list(price, N[1]))
	if(length(L) > RM_QUEST_SALES_KEPT) L.Cut(1, 2)

// "type path" -> list(average price, sales) for the goods sold lately.
proc/RmQuestRates()
	var/list/R = list()
	for(var/k in rm_quest_sales)
		var/list/L = rm_quest_sales[k]
		if(!length(L)) continue
		var/t = 0
		for(var/list/X in L) t += X[1]
		R[k] = list(round(t / length(L), 0.1), length(L))
	return R

// --- what this party can manage --------------------------------------------------------------------------------------
// This player's people who can act at the board (beside it or its quest givers), else those selected.
Player/proc/RmQuestPartyPower(mob/WorkShops/RemasterNoticeBoard/B)
	. = 0
	for(var/mob/Monsters/M in RmQuestNearUnits(B)) if(M.Owner == src && M.HP > 0) . += RmFortPower(M)
	if(!.) for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0) . += RmFortPower(M)

// What a quest puts against a party (as RmFortPower counts it), or null: nothing to fight (bring, reach, work, a hunt).
proc/RmQuestFoePower(list/Q)
	switch(Q["kind"])
		if("fort")
			. = 0
			for(var/mob/Monsters/M in RmFortUnits(Q["maker"], Q["garrison"], RmFortBox(Q))) . += RmFortPower(M)
			return . || null
		if("slay")
			var/mob/Monsters/M = RmQuestThing(Q["target"])
			return M ? RmFortPower(M) : null
		if("clear")
			var/list/G = Q["target"]
			var/obj/RemasterCaveMouth/O = G ? RmQuestMouth(G["mouth"]) : null
			if(!O) return null
			if(RemasterLairKind(O)) return 600   // a great beast's lair, whatever its mouth's number
			var/list/P = list(150, 300, 600)   // a cave's danger: scouts, a war band, a great beast
			return P[clamp(O.danger, 1, 3)]
	return null

var/list/rm_quest_danger_order = list("Easy"=1, "Even"=3, "Hard"=4, "Deadly"=5)   // unrated: 2, with the easy ones

// The board card's rows rated for this party (row "danger"), sorted by what it can manage when asked. The party's power.
Player/proc/RmQuestRateRows(list/rows, mob/WorkShops/RemasterNoticeBoard/B)
	var/pp = RmQuestPartyPower(B)
	if(pp) for(var/list/R in rows)
		var/list/Q = rm_quests[R["id"]]
		var/fp = Q ? RmQuestFoePower(Q) : null
		if(fp) R["danger"] = RmFortDanger(fp, pp)
	if(rm_quest_sort == "manage")
		for(var/i = 2, i <= length(rows), i++)   // a stable insertion sort: the board's own order within a rating
			var/j = i
			while(j > 1 && RmQuestDangerRank(rows[j - 1]) > RmQuestDangerRank(rows[j]))
				var/list/X = rows[j - 1]
				rows[j - 1] = rows[j]
				rows[j] = X
				j--
	return pp

proc/RmQuestDangerRank(list/R)
	return R["danger"] ? rm_quest_danger_order[R["danger"]] : 2

// --- fort reports ------------------------------------------------------------------------------------------------------
// Where a garrison member stands for a try (its post, else where it is): the way in, the goal, or inside.
proc/RmFortPostArea(datum/rm_fort_try/T, mob/Monsters/U)
	var/list/c = U.rm_post ? splittext(U.rm_post, ",") : null
	var/px = c ? text2num(c[1]) : U.x
	var/py = c ? text2num(c[2]) : U.y
	if(!isnull(T.dx) && max(abs(px - T.dx), abs(py - T.dy)) <= 2) return "the way in"
	if(!isnull(T.gx) && max(abs(px - T.gx), abs(py - T.gy)) <= 2) return "the goal"
	return "inside"

// The maker's report: the tries' numbers summed (tries kept since Q8 carry them).
proc/RmFortReport(list/Q)
	var/n = 0
	var/won = 0
	var/party = 0
	var/fell = 0
	var/gfell = 0
	var/list/areas = list()
	for(var/list/R in Q["tries"]) if(!isnull(R["party"]))
		n++
		if(R["result"] == "won") won++
		party += R["party"]
		fell += R["fell"] + R["down"]
		gfell += R["gfell"] + R["gdown"]
		for(var/a in R["broke"]) areas[a] = (areas[a] || 0) + 1
	if(!n) return null
	var/tries = n == 1 ? "try" : "tries"
	. = list("[n] [tries]: [won] won, [n - won] not. Parties of about [round(party / n, 0.1)].", "Takers fallen or knocked out: [fell]. Your garrison lost [gfell].")
	for(var/a in areas) . += "[uppertext(copytext(a, 1, 2))][copytext(a, 2)] lost someone in [areas[a]] of [n] [tries]."

// --- world notices -----------------------------------------------------------------------------------------------------
proc/RmWorldNoticePass()
	var/list/have = list()   // what the world's open notices are about
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		if(Q["maker"] != rm_world_key || (Q["state"] != "open" && Q["state"] != "closing")) continue
		var/list/G = Q["target"]
		if(G) have[G["tag"] || G["mouth"]] = id
	for(var/mob/Monsters/StoneGolem/S in rm_golems)
		if(Rm3DGone(S) || S.HP <= 0 || S.GoingToDie || !isturf(S.loc)) continue
		if(S.rm_qtag && have[S.rm_qtag]) continue
		have[RmQuestTag(S)] = RmWorldPostGolem(S)   // listed once even if the list has it twice
	for(var/obj/RemasterCaveMouth/O in rm_cave_mouths)
		if(O.z != GROUND_LAYER || O.owner_key || !RemasterLairKind(O)) continue
		var/k = "[O.x],[O.y],[O.z]"
		if(have[k]) continue
		var/list/LS = RemasterLairState(O)
		if(!LS["cleared"]) have[k] = RmWorldPostLair(O)

proc/RmWorldPostGolem(mob/Monsters/StoneGolem/S)
	var/list/G = list("kind"="thing", "type"="[S.type]", "what"="the stone golem", "race"=S.Race, "exact"="circle")
	G["tag"] = RmQuestTag(S)
	RmQuestSeen(G, S)
	RmQuestCircle(G)
	return RmWorldPost("slay", G, "Fell the stone golem", "A stone golem walks near the mountains here. Felled, it falls and a mountain of rock rises where it lay.",
		"The mountain it leaves when it falls", S)

proc/RmWorldPostLair(obj/RemasterCaveMouth/O)
	var/list/TH = rm_cave_themes[O.theme]
	var/what = "the [TH[1]]"
	var/list/G = list("kind"="thing", "mouth"="[O.x],[O.y],[O.z]", "what"=what, "x"=O.x, "y"=O.y, "z"=O.z, "exact"="exact", "lair"=1)
	var/list/LS = RemasterLairState(O)
	var/beast = RemasterLairKind(O) == "dragon" ? "A dragon sleeps on its hoard in this lair" : "A great spider keeps its nest and its hoard here"
	return RmWorldPost("clear", G, "Clear [what]", "[beast]. Its young roam near.", "The lair's hoard ([LS["hoard"]] pieces of gold, silver and gems)", O)

// A notice of the world's: no giver, nothing held, the prize the place itself. Boards near the place list it.
proc/RmWorldPost(kind, list/G, goal, text, prize, atom/A)
	var/atom/T = A
	while(T && !isturf(T)) T = T.loc
	if(!T) return null
	var/id = "q[++rm_quest_serial]"
	var/list/Q = list("id"=id, "kind"=kind, "maker"=rm_world_key, "house"="The world", "title"=goal, "text"=text,
		"board"=list(T.x, T.y, T.z), "item"=null, "itemName"=null, "need"=1, "quality"=null, "coins"=0, "goods"=list(),
		"goodsNames"=list(), "worth"=0, "who"="anyone", "rank"=1, "prize"=prize, "target"=G, "goal"=goal,
		"state"="open", "posted"=RemasterNow(), "ends"=RmQuestLater(RM_WORLD_DAYS), "days"=RM_WORLD_DAYS,
		"takers"=list(), "realms_done"=list(), "stats"=list("taken"=0, "done"=0, "gaveup"=0))
	Q["region"] = RmQuestRegion(T.x, T.y, T.z)   // its region (QuestScale.dm)
	RmQuestJournal(Q, "Posted by the world")
	rm_quests[id] = Q
	RmQuestChanged()
	return id

// --- commands (Quests.dm RmQuestCommand) --------------------------------------------------------------------------------
Player/proc/RmAdaptCommand(act, rest)
	switch(act)
		if("sort")           // sort|manage or sort|new: the board card's order
			rm_quest_sort = rest == "manage" ? "manage" : null
			return 1
		if("standingstop")   // standingstop|<id>: no more notices from it; one up now stays until it ends or comes down
			for(var/list/S in rm_quest_standing) if(S["id"] == rest)
				rm_quest_standing -= list(S)
				RemasterNotice("Standing notice stopped: [S["itemName"]].[S["quest"] ? " The notice up now stays until it ends or you take it down." : ""]")
				return 1
	return 0
