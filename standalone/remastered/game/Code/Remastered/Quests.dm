// Player-made quests (planning/QUEST_MAKER_PLAN_2026-10-31.md, phases Q1-Q2; the owner's "Yes, all eight", 10-31).
// A quest is a record, never an object: text, numbers, player keys and x,y,z, as OpenRealm keeps its 2,737 WoW quests as
// rows read by a little code. rm_quests holds every one (saved with the world: WorldSave.dm "Quests"); a player's quest
// log (rm_quest_log, saved with their units) holds only what that player is doing with them.
// Q2 has one kind, Bring: the maker posts it on their notice board with coins and goods held aside (taken off them at
// once, kept as item records on the quest); a taker's units hand the goods in at that board, counted per taker and kept
// as theirs until the whole amount is in; then the goods go to the maker and the reward to the taker. A notice that
// ends unfinished gives everything back: the reward to its maker, the handed-in goods to whoever brought them, on the
// board's tile. Nothing is ever made from nothing: a quest for your own second company only moves what you had.

#define RM_QUEST_LOG_MAX 10        // quests a player may hold open at once
#define RM_QUEST_BOARD_MAX 20      // notices a board shows
#define RM_QUEST_POST_COST 2       // coins a notice costs (not given back)
#define RM_QUEST_REACH 2           // tiles from a board to read, post, take or hand in
#define RM_QUEST_SEE 60            // a board also lists the public notices of boards this near
#define RM_QUEST_GOODS_MAX 10      // reward goods on one notice
#define RM_QUEST_RENOWN_FLOOR 10   // a reward worth less than this (coins and trade value) earns no renown
#define RM_QUEST_RENOWN_DAY 3      // renown a maker earns from one taker realm a day, at most
#define RM_QUEST_JOURNAL 20        // lines kept on a quest
#define RM_QUEST_KEEP_DAYS 3       // a finished or ended notice is kept this many days for the logs, then dropped

var/list/rm_quests = list()        // saved: quest id -> record (RmQuestPost)
var/rm_quest_serial = 0            // saved
var/list/rm_quest_owed = list()    // saved: player key -> coins owed to a player not in the world (paid at login)
var/list/rm_quest_renown = list()  // saved: maker key -> renown
var/list/rm_quest_renown_day = list()   // saved: "day|maker|taker realm" -> renown given that day (today's only)
var/rm_quest_ver = 0               // moves with every change: the HUD's kept answers and the boards' index
var/rm_quest_index_ver = -1
var/list/rm_quest_by_board = list()     // "x,y,z" -> open quest ids posted on that board (RmQuestIndex)
var/list/rm_quest_open_cap = list(1, 3, 5, 10, 20)   // open notices a realm may have up, by settlement rank (Camp to Kingdom)
var/list/rm_quest_days = list(1, 3, 7)               // how long a notice stays up: real days
var/list/rm_quest_goods            // what a Bring quest may ask for: "path" -> name (RmQuestGoods)
var/list/rm_quest_qualities = list("Poor Quality", "Average Quality", "Quality", "Impressive Quality", "Grand Quality", "Masterful Quality", "Epic Quality", "Legendary Quality")   // Gear.dm RmGearRank, worst first
var/list/rm_notice_boards = list()
var/rm_quest_looping = 0

Player/var
	list/rm_quest_log              // saved: quest id -> list("state", "title", "house", "at"); the quest itself is in rm_quests
Player/var/tmp
	rm_quest_card                  // the card open: a quest id, "board" (rm_quest_board's notices) or null
	list/rm_quest_board            // the board whose notices the card shows: x, y, z
	rm_quest_post_open = 0         // the post form is open (its lists are sent only then)
	rm_quest_track_key
	list/rm_quest_track

// --- the notice board -------------------------------------------------------------------------------------------------
// A workshop (Build > Workshops, 1 wood), so the world save keeps it with its owner like any other (WorldSave.dm "shops").
mob/WorkShops/RemasterNoticeBoard
	name = "Notice board"
	icon = 'Cave.dmi'
	icon_state = "sign"
	density = 1
	var/house                      // its maker's house name, kept for when they are away
	New()
		..()
		rm_notice_boards += src
	Del()
		rm_notice_boards -= src
		if(remaster_world_ready && isturf(loc)) RmQuestBoardGone(x, y, z)
		..()

proc/RmQuestBoardKey(mob/WorkShops/W)
	return ismob(W.Owner) ? W.Owner:key : W.remaster_owner_key

proc/RmQuestBoardAt(list/B)
	if(!islist(B) || length(B) < 3) return null
	var/turf/T = locate(B[1], B[2], B[3])
	return T ? (locate(/mob/WorkShops/RemasterNoticeBoard) in T) : null

// A board within reach of the unit (its owner's own when own is set).
proc/RmQuestBoardBeside(mob/Monsters/M, own = 0)
	if(!M || !isturf(M.loc)) return null
	for(var/mob/WorkShops/RemasterNoticeBoard/B in rm_notice_boards) if(B.z == M.z && get_dist(B, M) <= RM_QUEST_REACH)
		if(!own || RmQuestBoardKey(B) == M.Owner:key) return B
	if(!own) return RmKeeperBoardBeside(M)   // beside a quest giver standing by its board (QuestKeepers.dm)
	return null

// --- small helpers ----------------------------------------------------------------------------------------------------
proc/RmQuestLater(days)
	var/list/N = RemasterNow()
	return list(N[1] + days, N[2])

proc/RmQuestOver(list/ends)
	var/s = RemasterSince(ends)
	return !isnull(s) && s >= 0

// "2 days", "5 hours", "20 minutes" left (RemasterSince is in tenths of a second)
proc/RmQuestLeftText(list/ends)
	var/s = RemasterSince(ends)
	if(isnull(s)) return ""
	var/t = -s / 10
	if(t <= 0) return "ending"
	// rounded up: a notice put up for 3 days says "3 days left", not 2
	var/n
	if(t > 86400)
		n = -round(-t / 86400)
		return "[n] day[n == 1 ? "" : "s"] left"
	if(t > 3600)
		n = -round(-t / 3600)
		return "[n] hour[n == 1 ? "" : "s"] left"
	n = max(1, -round(-t / 60))
	return "[n] minute[n == 1 ? "" : "s"] left"

// Typed text on a notice: one line, no markup, at most n characters.
proc/RmQuestText(t, n)
	t = "[t]"
	for(var/c in list("<", ">", "\n", "\t"))
		t = replacetext(t, c, " ")
	t = trimtext(t)
	if(length(t) > n) t = copytext(t, 1, n + 1)
	return t

proc/RmQuestJournal(list/Q, text)
	var/list/J = Q["journal"]
	if(!islist(J)) J = Q["journal"] = list()
	J += list(list(text, RemasterNow()))
	if(length(J) > RM_QUEST_JOURNAL) J.Cut(1, 2)

proc/RmQuestChanged()
	rm_quest_ver++
	RmQuestKinds()   // the indexes the targets' hooks read (QuestTargets.dm)

// The kinds a Bring quest may ask for: every catalogued item (art/items/catalogue.json, art/enhance/catalogue.json:
// rm_item or rm_gear on the type) but graves and severed limbs, by the type's own name. Built once, from the types.
proc/RmQuestGoods()
	if(rm_quest_goods) return rm_quest_goods
	var/list/G = list()
	for(var/p in typesof(/obj/Items))
		var/obj/Items/X = p
		var/id = initial(X.rm_item)
		if(!id && !initial(X.rm_gear)) continue
		if(ispath(p, RM_QUEST_TOKEN_TYPE)) continue   // a chain's token is asked for by its own id (QuestChains.dm)
		if(id && (copytext(id, 1, 7) == "graves" || copytext(id, 1, 13) == "remasterlimb")) continue
		G["[p]"] = "[initial(X.name)]"
	rm_quest_goods = G
	return G

proc/RmQuestGoodName(path)
	var/list/G = RmQuestGoods()
	return G["[path]"] || "[path]"

proc/RmQuestQualityRank(rank)
	return rank ? (rm_quest_qualities.Find(rank) || 0) : 0

// The goods a Bring quest counts: the very kind (not its kin), and at least the quality asked for.
proc/RmQuestGoodEnough(obj/Items/I, path, quality, token)
	if(I.type != path || I.suffix == "(Equipped)") return 0
	if(token && I:rm_token != token) return 0   // a chain's token: that very one (QuestChains.dm)
	if(quality && RmQuestQualityRank(I.CraftRank) < RmQuestQualityRank(quality)) return 0
	return 1

proc/RmQuestRankName(rank)
	var/list/R = rm_ranks[clamp(rank, 1, length(rm_ranks))]
	return R["name"]

// Coins to a player: into their treasury, or owed until they log in.
proc/RmQuestPay(key, coins)
	if(!key || coins <= 0) return
	var/Player/P = RemasterPlayerByKey(key)
	if(P) P.remaster_coins += coins
	else rm_quest_owed[key] = (rm_quest_owed[key] || 0) + coins

// Item records kept on a quest are JSON-safe (the world save writes the quests as one JSON text, ~4x quicker than a
// savefile tree for quest_check's 1,000 quests): a type path in an item's settings is kept as "path:<path>".
proc/RmQuestItemRecord(obj/Items/I)
	return RmQuestPathsOut(RemasterItemRecord(I))

proc/RmQuestPathsOut(list/R)
	var/list/V = R[2]
	for(var/k in V) if(ispath(V[k])) V[k] = "path:[V[k]]"
	for(var/list/C in R[4]) RmQuestPathsOut(C)
	return R

proc/RmQuestPathsIn(list/R)
	var/list/V = R[2]
	for(var/k in V) if(istext(V[k]) && copytext(V[k], 1, 6) == "path:") V[k] = text2path(copytext(V[k], 6))
	for(var/list/C in R[4]) RmQuestPathsIn(C)
	return R

// Item records put back into the world on T, owned by key.
proc/RmQuestDrop(list/records, turf/T, key)
	var/Player/P = RemasterPlayerByKey(key)
	for(var/list/R in records)
		var/obj/Items/I = RemasterItemRestore(RmQuestPathsIn(R), T)
		if(!I) continue
		I.remaster_owner_key = key
		I.Owner = P
		I.suffix = null

// The open quests on each board (rebuilt only after a change).
proc/RmQuestIndex()
	if(rm_quest_index_ver == rm_quest_ver) return rm_quest_by_board
	rm_quest_index_ver = rm_quest_ver
	rm_quest_by_board = list()
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		if(Q["state"] != "open" && Q["state"] != "closing") continue
		var/list/B = Q["board"]
		var/k = "[B[1]],[B[2]],[B[3]]"
		var/list/L = rm_quest_by_board[k]
		if(!L) L = rm_quest_by_board[k] = list()
		L += id
	return rm_quest_by_board

// Why this player may not take it ("" = they may).
proc/RmQuestWhyNot(list/Q, Player/P)
	if(Q["state"] != "open") return Q["state"] == "closing" ? "Its maker is taking it down." : "This notice is closed."
	if(P.key == Q["maker"]) return "Your own notice."
	var/list/L = P.rm_quest_log
	if(L && L[Q["id"]]) return L[Q["id"]]["state"] == "taken" ? "You have taken it." : "You have done it."
	var/allied = RemasterAlliedKeys(P.key, Q["maker"])
	if(Q["who"] == "others" && allied) return "Only for folk from outside [Q["house"]]'s realm."
	if(Q["who"] == "realm" && !allied) return "Only for [Q["house"]]'s realm."
	if(Q["rank"] > 1 && P.remaster_rank < Q["rank"]) return "Only for a [RmQuestRankName(Q["rank"])] or bigger."
	if(RemasterRootKey(P.key) in Q["realms_done"]) return "Your realm has done it."
	if(Q["kind"] == "work" && length(Q["takers"])) return "Someone is working on it already."
	var/aw = RmQuestAfterWhy(Q, P)   // a chain's step before (QuestChains.dm)
	if(aw) return aw
	if(P.RmQuestOpenCount() >= RM_QUEST_LOG_MAX) return "Your quest log is full ([RM_QUEST_LOG_MAX])."
	return ""

// May this player see it on a board? Its maker always; others when it is open to them.
proc/RmQuestShown(list/Q, Player/P)
	if(P.key == Q["maker"]) return 1
	var/allied = RemasterAlliedKeys(P.key, Q["maker"])
	if(Q["who"] == "others" && allied) return 0
	if(Q["who"] == "realm" && !allied) return 0
	return 1

Player/proc/RmQuestOpenCount()
	. = 0
	for(var/id in rm_quest_log)
		var/list/E = rm_quest_log[id]
		var/list/Q = rm_quests[id]
		if(E["state"] == "taken" && Q && (Q["state"] == "open" || Q["state"] == "closing")) .++

// Open notices up by this player's realm (the cap is the realm's, by rank).
Player/proc/RmQuestRealmOpen()
	. = 0
	var/root = RemasterRootKey(key)
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		if((Q["state"] == "open" || Q["state"] == "closing") && RemasterRootKey(Q["maker"]) == root) .++

// --- posting ----------------------------------------------------------------------------------------------------------
// A = the post form (decoded JSON): unit, item (a type path), need, quality, coins, goods (the unit's carried items'
// refs), who ("anyone", "others", "realm"), rank (1-5), days (1, 3 or 7), title, text. Returns the quest id, or null.
Player/proc/RmQuestPost(list/A)
	if(!islist(A)) return null
	var/mob/Monsters/M = RemasterUIUnit(A["unit"])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return null
	var/mob/WorkShops/RemasterNoticeBoard/B = RmQuestBoardBeside(M, 1)
	if(!B)
		RemasterNotice("[M.RemasterBareName()] must stand by your notice board to post.")
		return null
	if(RmModMuted(key) || RmModPostBanned(key))   // Moderation.dm
		RemasterNotice("An admin has stopped you posting notices for now.")
		return null
	var/kind = (A["kind"] in list("slay", "hunt", "clear", "reach", "work", "fort")) ? A["kind"] : "bring"
	var/path
	var/need
	var/list/TG
	var/tok   // a chain's token asked for (QuestChains.dm)
	if(kind == "bring")
		tok = A["token"] ? RmQuestTokenFor(A["token"]) : null
		path = tok ? RM_QUEST_TOKEN_TYPE : text2path("[A["item"]]")
		if(!path || (!tok && !RmQuestGoods()["[path]"]))
			RemasterNotice("Pick what the notice asks for.")
			return null
		need = clamp(round(text2num("[A["need"]]") || 0), 1, 200)
	else
		TG = RmQuestPostTarget(A, kind)   // what or where it is about (QuestTargets.dm)
		if(!islist(TG))
			RemasterNotice(TG || "Pick what the notice is about.")
			return null
		need = TG["need"]
	var/list/CH = RmQuestChainPost(A)   // what it comes after, the token it gives (QuestChains.dm)
	if(!islist(CH))
		RemasterNotice(CH)
		return null
	var/coins = max(0, round(text2num("[A["coins"]]") || 0))
	var/quality = (A["quality"] in rm_quest_qualities) ? A["quality"] : null
	var/days = text2num("[A["days"]]")
	if(!(days in rm_quest_days)) days = 3
	var/who = (A["who"] in list("anyone", "others", "realm")) ? A["who"] : "anyone"
	var/rank = clamp(round(text2num("[A["rank"]]") || 1), 1, length(rm_ranks))
	var/cap = rm_quest_open_cap[clamp(remaster_rank, 1, length(rm_quest_open_cap))]
	if(RmQuestRealmOpen() >= cap)
		RemasterNotice("Your realm has [cap] notice[cap == 1 ? "" : "s"] up, all a [RmQuestRankName(remaster_rank)] may have. Grow your settlement for more.")
		return null
	var/list/goods = list()
	var/list/ids = islist(A["goods"]) ? A["goods"] : list()
	for(var/obj/Items/I in M) if(I.remaster_ui_id && (I.remaster_ui_id in ids) && I.suffix != "(Equipped)" && length(goods) < RM_QUEST_GOODS_MAX)
		goods += I
	if(!coins && !length(goods))
		RemasterNotice("Put up a reward: coins, or goods [M.RemasterBareName()] carries.")
		return null
	if(remaster_coins < coins + RM_QUEST_POST_COST)
		RemasterNotice("Not enough coins: [coins + RM_QUEST_POST_COST] needed ([RM_QUEST_POST_COST] for the notice), the treasury has [remaster_coins].")
		return null
	var/name = tok ? tok : (path ? RmQuestGoodName(path) : null)
	var/title = RmQuestText(A["title"], 40)
	if(!length(title)) title = TG ? TG["title"] : "Bring [need] [name]"
	title = RmModFilter(title)   // the admins' word list (Moderation.dm, A4)
	var/text = RmModFilter(RmQuestText(A["text"], 300))
	remaster_coins -= coins + RM_QUEST_POST_COST
	var/worth = coins
	var/list/held = list()
	var/list/names = list()
	for(var/obj/Items/I in goods)
		worth += RemasterTradeValue(I)
		names += "[I.name]"
		held += list(RmQuestItemRecord(I))
		M.weight -= I.weight
		del I
	var/id = "q[++rm_quest_serial]"
	if(!B.house) B.house = RemasterHouse()
	var/list/Q = list("id"=id, "kind"=kind, "maker"=key, "house"=RemasterHouse(), "title"=title, "text"=text,
		"board"=list(B.x, B.y, B.z), "item"=(path ? "[path]" : null), "itemName"=name, "need"=need, "quality"=quality,
		"coins"=coins, "goods"=held, "goodsNames"=names, "worth"=worth, "who"=who, "rank"=rank,
		"state"="open", "posted"=RemasterNow(), "ends"=RmQuestLater(days), "days"=days,
		"takers"=list(), "realms_done"=list(), "stats"=list("taken"=0, "done"=0, "gaveup"=0))
	Q["region"] = RmQuestRegion(B.x, B.y, B.z)   // its region (QuestScale.dm)
	RmQuestJournal(Q, "Posted by [RemasterHouse()]")
	if(TG) RmQuestTargetPut(Q, TG)   // its target; a work notice's plan waits (QuestTargets.dm)
	RmQuestChainPut(Q, CH)
	if(tok) Q["tokenWant"] = A["token"]
	rm_quests[id] = Q
	RmQuestChanged()
	spawn(0) RmQuestLoop()
	RemasterNotice("Notice posted: [title].")
	RemasterLog("Posted a notice: [title]", "good", B)
	return id

// --- taking, handing in, giving up ------------------------------------------------------------------------------------
// A board that lists Q and is within reach of one of this player's units: the quest's own board, or one near it.
Player/proc/RmQuestBoardFor(list/Q, mob/Monsters/M)
	var/mob/WorkShops/RemasterNoticeBoard/B = RmQuestBoardBeside(M)
	if(!B) return null
	var/list/QB = Q["board"]
	if(B.z == QB[3] && max(abs(B.x - QB[1]), abs(B.y - QB[2])) <= RM_QUEST_SEE) return B
	return null

Player/proc/RmQuestTake(id, mob/Monsters/M)
	var/list/Q = rm_quests[id]
	if(!Q || !istype(M) || M.Owner != src || M.HP <= 0) return 0
	if(!RmQuestBoardFor(Q, M))
		RemasterNotice("[M.RemasterBareName()] must stand by a notice board that shows it.")
		return 0
	var/why = RmQuestWhyNot(Q, src)
	if(why)
		RemasterNotice(why)
		return 0
	if(!rm_quest_log) rm_quest_log = list()
	rm_quest_log[id] = list("state"="taken", "title"=Q["title"], "house"=Q["house"], "at"=RemasterNow())
	var/list/T = Q["takers"]
	T[key] = list("got"=0, "goods"=list(), "house"=RemasterHouse(), "root"=RemasterRootKey(key))
	var/list/S = Q["stats"]
	S["taken"]++
	RmQuestJournal(Q, "Taken by [RemasterHouse()]")
	RmQuestChanged()
	if(Q["kind"] == "work" && !RmQuestWorkStart(Q)) RemasterNotice("Nothing of it can be built just now.")   // QuestTargets.dm
	RemasterNotice("Quest taken: [Q["title"]]. [RmQuestHowText(Q)]")
	return 1

// Every unit of this player at the quest's own board hands in what it carries of the kind asked for, up to what is
// still needed. The goods are kept on the quest as this player's until the whole amount is in.
Player/proc/RmQuestHandIn(id, mob/Monsters/M)
	var/list/Q = rm_quests[id]
	if(!Q || !istype(M) || M.Owner != src || (Q["kind"] && Q["kind"] != "bring")) return 0   // only Bring is handed in
	var/list/T = Q["takers"][key]
	if(!T || (Q["state"] != "open" && Q["state"] != "closing")) return 0
	var/mob/WorkShops/RemasterNoticeBoard/B = RmQuestBoardAt(Q["board"])
	if(!B || !RmQuestNear(M, B))   // by it, or by a quest giver standing by it (QuestKeepers.dm)
		RemasterNotice("Hand it in at [Q["house"]]'s own notice board.")
		return 0
	var/path = text2path(Q["item"])
	var/left = Q["need"] - T["got"]
	var/list/give = list()
	for(var/mob/Monsters/U in RmQuestNearUnits(B)) if(U.Owner == src && U.HP > 0)
		for(var/obj/Items/I in U) if(length(give) < left && RmQuestGoodEnough(I, path, Q["quality"], Q["tokenWant"])) give += I
	if(!length(give))
		RemasterNotice("Nobody of yours by the board carries [Q["itemName"]][Q["quality"] ? " ([Q["quality"]] or better)" : ""].")
		return 0
	for(var/obj/Items/I in give)
		var/mob/Monsters/U = I.loc
		T["goods"] += list(RmQuestItemRecord(I))
		if(istype(U)) U.weight -= I.weight
		del I
	T["got"] += length(give)
	RmQuestJournal(Q, "[RemasterHouse()] handed in [length(give)] ([T["got"]]/[Q["need"]])")
	RmQuestChanged()
	if(T["got"] >= Q["need"]) RmQuestFinish(Q, src, M, B)
	else RemasterNotice("Handed in [length(give)] [Q["itemName"]]: [T["got"]] of [Q["need"]].")
	return 1

Player/proc/RmQuestGiveUp(id)
	var/list/Q = rm_quests[id]
	if(rm_quest_log) rm_quest_log -= id
	if(!Q) return 0
	var/list/T = Q["takers"][key]
	if(T)
		var/list/BT = Q["board"]
		RmQuestDrop(T["goods"], locate(BT[1], BT[2], BT[3]), key)
		Q["takers"] -= key
		RmQuestFailed(Q, key)   // for "after ... failed" (QuestChains.dm)
		var/list/S = Q["stats"]
		S["gaveup"]++
		RmQuestJournal(Q, "[RemasterHouse()] gave up[length(T["goods"]) ? ": [length(T["goods"])] handed back at the board" : ""]")
	RmQuestChanged()
	RmQuestWorkRows()   // a work notice's plan off the job board (QuestTargets.dm)
	RemasterNotice("You gave up [Q["title"]].")
	return 1

// The quest is done: a Bring quest's goods to the maker (on the board's tile, theirs); the reward to the taker (coins into
// the treasury, goods into the pack of the one who did it, or at its feet if it can't carry more); everyone else's goods
// back to them. P may be null: a taker not in the world (key), whose coins are owed and goods left where it was done.
proc/RmQuestFinish(list/Q, Player/P, mob/Monsters/M, mob/WorkShops/RemasterNoticeBoard/B, key)
	if(P) key = P.key
	var/list/T = Q["takers"][key]
	var/turf/BT = B ? B.loc : RmQuestSpot(Q)
	var/turf/MT = (M && isturf(M.loc)) ? M.loc : BT
	if(BT) RmQuestDrop(T["goods"], BT, Q["maker"])
	if(P) P.remaster_coins += Q["coins"]
	else RmQuestPay(key, Q["coins"])
	for(var/list/R in Q["goods"])
		var/obj/Items/I = RemasterItemRestore(RmQuestPathsIn(R), M || MT)
		if(!I) continue
		I.remaster_owner_key = key
		I.Owner = P
		if(!M || M.weight + I.weight > M.weightmax)
			I.loc = MT
			I.suffix = null
		else
			I.suffix = "(Carrying)"
			M.weight += I.weight
	RmQuestGiveToken(Q, P, M, MT, key)   // a chain's token (QuestChains.dm)
	for(var/k in Q["takers"]) if(k != key) RmQuestFailed(Q, k)   // the others holding it didn't do it
	var/house = P ? P.RemasterHouse() : T["house"]
	T["goods"] = list()
	Q["goods"] = list()
	Q["state"] = "done"
	Q["closed"] = RemasterNow()
	Q["winner"] = key
	Q["winnerHouse"] = house
	Q["realms_done"] += RemasterRootKey(key)
	var/list/S = Q["stats"]
	S["done"]++
	var/list/E = (P && P.rm_quest_log) ? P.rm_quest_log[Q["id"]] : null
	if(E) E["state"] = "done"
	if(BT) RmQuestReturnOthers(Q, BT)
	RmQuestRenown(Q, key)
	RmQuestJournal(Q, "Done by [house]")
	RmQuestChanged()
	RmQuestTargetEnd(Q)   // a work notice's plans put right (QuestTargets.dm)
	var/reward = RmQuestRewardText(Q)
	if(P)
		P.RemasterNotice("Quest done: [Q["title"]]. Reward: [reward].")
		P.RemasterLog("Quest done for [Q["house"]]: [Q["title"]] ([reward])", "good", M || B)
	var/Player/K = RemasterPlayerByKey(Q["maker"])
	if(K)
		K.RemasterNotice("[house] did your notice: [Q["title"]].[Q["kind"] == "bring" || !Q["kind"] ? " The goods are by your notice board." : ""]")
		K.RemasterLog("[house] did your notice: [Q["title"]]", "good", B || BT)

// Takers still holding it when it closes get what they handed in back, on the board's tile.
proc/RmQuestReturnOthers(list/Q, turf/BT)
	var/list/TK = Q["takers"]
	for(var/k in TK)
		var/list/T = TK[k]
		if(length(T["goods"])) RmQuestDrop(T["goods"], BT, k)
		T["goods"] = list()

proc/RmQuestRewardText(list/Q)
	var/list/L = list()
	if(Q["coins"]) L += "[Q["coins"]] coins"
	for(var/n in Q["goodsNames"]) L += n
	if(Q["prize"]) L += Q["prize"]   // a world notice's: the place itself (QuestAdaptive.dm)
	return jointext(L, ", ")

// Renown for the maker: a taker from another realm, a reward worth the floor, at most RM_QUEST_RENOWN_DAY a day from
// that realm (plan section 10). Counted per maker key, shown on every board.
proc/RmQuestRenown(list/Q, key)
	if(istype(key, /Player)) key = key:key
	if(RemasterAlliedKeys(Q["maker"], key) || Q["worth"] < RM_QUEST_RENOWN_FLOOR) return 0
	var/list/N = RemasterNow()
	var/k = "[N[1]]|[Q["maker"]]|[RemasterRootKey(key)]"
	if((rm_quest_renown_day[k] || 0) >= RM_QUEST_RENOWN_DAY) return 0
	rm_quest_renown_day[k] = (rm_quest_renown_day[k] || 0) + 1
	rm_quest_renown[Q["maker"]] = (rm_quest_renown[Q["maker"]] || 0) + 1
	return 1

// --- ending: time ran out, the maker took it down, or the board is gone --------------------------------------------------
proc/RmQuestEnd(list/Q, why)
	if(Q["state"] != "open" && Q["state"] != "closing") return 0
	var/list/BP = Q["board"]
	var/turf/BT = locate(BP[1], BP[2], BP[3])
	RmQuestPay(Q["maker"], Q["coins"])
	RmQuestDrop(Q["goods"], BT, Q["maker"])
	RmQuestReturnOthers(Q, BT)
	Q["goods"] = list()
	Q["state"] = "ended"
	Q["closed"] = RemasterNow()
	Q["why"] = why
	RmQuestJournal(Q, "Ended: [why]")
	RmQuestChanged()
	var/Player/K = RemasterPlayerByKey(Q["maker"])
	if(K) K.RemasterLog("Your notice came down ([why]): [Q["title"]]. Its reward is back with you.", "info", BT)
	for(var/k in Q["takers"])
		RmQuestFailed(Q, k)   // it came down while they held it (QuestChains.dm)
		var/Player/T = RemasterPlayerByKey(k)
		if(T) T.RemasterLog("A quest you took came down ([why]): [Q["title"]]", "info", BT)
	RmQuestTargetEnd(Q)   // a work notice's plans put right (QuestTargets.dm)
	return 1

Player/proc/RmQuestCancel(id)
	var/list/Q = rm_quests[id]
	if(!Q || Q["maker"] != key || Q["state"] != "open") return 0
	if(length(Q["takers"]))
		Q["state"] = "closing"
		RmQuestJournal(Q, "Taken down by its maker: those who took it have until it ends")
		RmQuestChanged()
		RemasterNotice("[Q["title"]] takes no new takers. Those who took it have until it ends ([RmQuestLeftText(Q["ends"])]).")
		return 1
	RmQuestEnd(Q, "taken down")
	RemasterNotice("[Q["title"]] is down. Its reward is back with you.")
	return 1

proc/RmQuestBoardGone(x, y, z)
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		var/list/B = Q["board"]
		if(B[1] == x && B[2] == y && B[3] == z) RmQuestEnd(Q, "its notice board is gone")

// Every 30 s: notices whose time is up come down; finished ones are dropped after a few days; old renown days go.
proc/RmQuestLoop()
	if(rm_quest_looping) return
	rm_quest_looping = 1
	while(1)
		sleep(300)
		RmQuestTick()

proc/RmQuestTick()
	RmAdaptTick()   // standing notices, the world's notices (QuestAdaptive.dm)
	RmQuestTargetsTick()   // quarries gone, lairs cleared by others, work all laid (QuestTargets.dm)
	var/list/drop = list()
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		if(Q["state"] == "open" || Q["state"] == "closing")
			if(RmQuestOver(Q["ends"])) RmQuestEnd(Q, "it ran out of time")
		else if(Q["closed"] && !rm_quest_next_of[id])   // kept while an open notice comes after it (QuestChains.dm)
			var/s = RemasterSince(Q["closed"])
			if(!isnull(s) && s > RM_QUEST_KEEP_DAYS * 864000) drop += id
	for(var/id in drop) rm_quests -= id
	if(length(drop)) RmQuestChanged()
	if(length(rm_quest_renown_day))
		var/list/N = RemasterNow()
		var/today = "[N[1]]|"
		var/list/keep = list()
		for(var/k in rm_quest_renown_day) if(copytext(k, 1, length(today) + 1) == today) keep[k] = rm_quest_renown_day[k]
		rm_quest_renown_day = keep

Player/proc/RmQuestOnLogin()
	for(var/id in rm_quest_log)   // done while away (their people did it: QuestTargets.dm)
		var/list/LE = rm_quest_log[id]
		var/list/LQ = rm_quests[id]
		if(LQ && LE["state"] == "taken" && LQ["state"] == "done" && LQ["winner"] == key) LE["state"] = "done"
	RmQuestWorkRows()
	if(rm_quest_owed[key])
		var/n = rm_quest_owed[key]
		remaster_coins += n
		rm_quest_owed -= key
		RemasterNotice("While you were away your notices paid back [n] coins.")

// --- saving (WorldSave.dm) ----------------------------------------------------------------------------------------------
// One JSON text: quick to write and read back (quest_check: 1,000 quests in well under 0.1 s each way).
proc/RmQuestSaveData()
	return json_encode(list("version"=1, "serial"=rm_quest_serial, "quests"=rm_quests, "owed"=rm_quest_owed, "renown"=rm_quest_renown, "renownDay"=rm_quest_renown_day, "sales"=rm_quest_sales))

proc/RmQuestLoadData(D)
	if(istext(D))
		try
			D = json_decode(D)
		catch
			D = null
			world.log << "Remastered: the saved quests could not be read"
	if(islist(D))
		if(isnum(D["serial"])) rm_quest_serial = D["serial"]
		if(islist(D["quests"])) rm_quests = D["quests"]
		RmQuestRegionsFill()   // saves from before Q9 (QuestScale.dm)
		if(islist(D["owed"])) rm_quest_owed = D["owed"]
		if(islist(D["renown"])) rm_quest_renown = D["renown"]
		if(islist(D["renownDay"])) rm_quest_renown_day = D["renownDay"]
		if(islist(D["sales"])) rm_quest_sales = D["sales"]   // the going rate (QuestAdaptive.dm)
	RmQuestChanged()
	spawn(0) RmQuestLoop()

// --- the HUD: commands ---------------------------------------------------------------------------------------------------
// "quest" value: "board|unitref" (the notices of the board beside it), "open|id", "close", "take|id|unitref",
// "handin|id|unitref", "giveup|id", "cancel|id", "postform|1/0", "post|<json>".
Player/proc/RmQuestCommand(value)
	var/v = "[value]"
	var/i = findtext(v, "|")
	var/act = i ? copytext(v, 1, i) : v
	var/rest = i ? copytext(v, i + 1) : ""
	var/list/p = splittext(rest, "|")
	if(copytext(act, 1, 7) == "keeper") return RmKeeperCommand(act, rest)   // keepers (QuestKeepers.dm)
	if(act == "sort" || act == "standingstop") return RmAdaptCommand(act, rest)   // QuestAdaptive.dm
	switch(act)
		if("board")
			var/mob/Monsters/M = RemasterUIUnit(rest)
			var/mob/WorkShops/RemasterNoticeBoard/B = istype(M) ? RmQuestBoardBeside(M) : null
			if(!B) return 0
			rm_quest_board = list(B.x, B.y, B.z)
			rm_quest_card = "board"
		if("open")
			if(rm_quests[rest])
				rm_quest_card = rest
				if(!rm_quest_read) rm_quest_read = list()
				rm_quest_read -= rest
				rm_quest_read += rest   // read: its marker shows (QuestTargets.dm)
				if(length(rm_quest_read) > 30) rm_quest_read.Cut(1, 2)
		if("close")
			rm_quest_card = null
		if("take")
			if(length(p) >= 2 && RmQuestTake(p[1], RemasterUIUnit(p[2]))) rm_quest_card = p[1]
		if("handin")
			if(length(p) >= 2) RmQuestHandIn(p[1], RemasterUIUnit(p[2]))
		if("giveup")
			RmQuestGiveUp(rest)
		if("cancel")
			RmQuestCancel(rest)
		if("postform")
			rm_quest_post_open = rest == "1"
			if(!rm_quest_post_open)
				rm_quest_pick = null
				rm_quest_picked = null
				rm_fort_picked = null
		if("garrison")   // fort challenges (QuestForts.dm)
			RmFortGarrison(rest)
		if("try")
			RmFortTryStart(rest)
		if("pick")   // the next click in the world picks the target (QuestTargets.dm)
			RmQuestPickStart(rest)
		if("pick3d")
			var/atom/PA = Remaster3DTarget(p)
			if(PA) RmQuestPickClick(PA)
		if("pickat")
			if(length(p) >= 3) RmQuestPickAt(text2num(p[1]), text2num(p[2]), text2num(p[3]))
		if("post")
			var/list/A
			try
				A = json_decode(rest)
			catch
				A = null
			var/id = RmStandingWanted(A) ? RmStandingMake(A) : RmQuestPost(A)   // a standing notice (QuestAdaptive.dm)
			if(id)
				rm_quest_post_open = 0
				rm_quest_card = id
	return 1

// --- the HUD: what the page is sent -----------------------------------------------------------------------------------
// One quest as a notice row (the board card, the Quests page lists).
Player/proc/RmQuestRow(list/Q)
	var/list/E = rm_quest_log ? rm_quest_log[Q["id"]] : null
	var/list/T = Q["takers"][key]
	var/mark = ""
	if(Q["state"] == "open" || Q["state"] == "closing")
		if(T) mark = (Q["kind"] && Q["kind"] != "bring") ? "" : "?"   // a goal on a target has nothing to hand in (QuestTargets.dm)
		else if(!RmQuestWhyNot(Q, src)) mark = "!"
	var/list/B = Q["board"]
	var/goal = Q["goal"] || "[Q["need"]] [Q["itemName"]][Q["quality"] ? " ([Q["quality"]] or better)" : ""]"
	return list("id"=Q["id"], "title"=(Q["hidden"] ? (Q["goal"] || "Bring [Q["need"]] [Q["itemName"]]") : Q["title"]), "house"=Q["house"], "mark"=mark, "state"=Q["state"],
		"goal"=goal, "goalKind"=(Q["kind"] || "bring"),
		"reward"=RmQuestRewardText(Q), "got"=(T ? T["got"] : null), "need"=Q["need"], "own"=(Q["maker"] == key),
		"mine"=(E ? E["state"] : null), "left"=RmQuestLeftText(Q["ends"]), "takers"=length(Q["takers"]),
		"x"=B[1], "y"=B[2], "z"=B[3])

// The card: a board's notices, or one quest with the "checked by the game" box.
Player/proc/RmQuestCardData()
	if(!rm_quest_card) return null
	if(rm_quest_card == "keeper") return RmKeeperCardData()   // a keeper's talk (QuestKeepers.dm)
	if(rm_quest_card == "board")
		var/mob/WorkShops/RemasterNoticeBoard/B = RmQuestBoardAt(rm_quest_board)
		if(!B)
			rm_quest_card = null
			return null
		var/list/rows = list()
		var/list/I = RmQuestIndex()
		var/list/own = I["[B.x],[B.y],[B.z]"]
		for(var/id in own) if(length(rows) < RM_QUEST_BOARD_MAX && RmQuestShown(rm_quests[id], src)) rows += list(RmQuestRow(rm_quests[id]))
		for(var/k in I)
			if(k == "[B.x],[B.y],[B.z]") continue
			for(var/id in I[k])
				var/list/Q = rm_quests[id]
				var/list/QB = Q["board"]
				if(length(rows) >= RM_QUEST_BOARD_MAX || QB[3] != B.z || max(abs(QB[1] - B.x), abs(QB[2] - B.y)) > RM_QUEST_SEE || !RmQuestShown(Q, src)) continue
				rows += list(RmQuestRow(Q))
		var/pp = RmQuestRateRows(rows, B)   // rated for this party, sorted so on ask (QuestAdaptive.dm)
		var/bk = RmQuestBoardKey(B)
		return list("kind"="board", "house"=B.house || "[B.Owner]", "own"=(bk == key), "renown"=(rm_quest_renown[bk] || 0),
			"rows"=rows, "unit"=RmQuestCardUnit(B), "sort"=(rm_quest_sort || "new"), "party"=pp)
	var/list/Q = rm_quests[rm_quest_card]
	if(!Q)
		rm_quest_card = null
		return null
	var/list/R = RmQuestRow(Q)
	R["kind"] = "quest"
	R["text"] = Q["hidden"] ? "" : Q["text"]   // an admin hid its words (Moderation.dm)
	R["report"] = Q["maker"] != key && Q["maker"] != rm_world_key   // the world's notices: nobody to report (QuestAdaptive.dm)
	R["world"] = Q["maker"] == rm_world_key
	R["renown"] = rm_quest_renown[Q["maker"]] || 0
	R["who"] = Q["who"] == "others" ? "Only folk from outside [Q["house"]]'s realm" : Q["who"] == "realm" ? "Only [Q["house"]]'s realm" : "Anyone"
	if(Q["rank"] > 1) R["who"] += ", a [RmQuestRankName(Q["rank"])] or bigger"
	R["why"] = RmQuestWhyNot(Q, src)
	R["stats"] = Q["stats"]
	R["target"] = RmQuestTargetLine(Q)   // where it is about, as this viewer knows it (QuestTargets.dm)
	R["chain"] = RmQuestChainCard(Q)   // what it comes after, gives, leads to (QuestChains.dm)
	if(Q["kind"] == "work") R["mat"] = Q["mat"]
	if(Q["kind"] == "fort") R["fort"] = RmFortCardData(Q)   // garrison, danger, tries (QuestForts.dm)
	R["winner"] = Q["winnerHouse"]
	R["ended"] = Q["why"]
	var/mob/WorkShops/RemasterNoticeBoard/B = RmQuestBoardAt(Q["board"])
	if(!B) R["where"] = "its notice board is gone"
	// the unit acts at the board the card was opened from, when that board lists it; else at its own board
	var/mob/WorkShops/RemasterNoticeBoard/V = RmQuestBoardAt(rm_quest_board)
	var/list/QB = Q["board"]
	if(!V || V.z != QB[3] || max(abs(V.x - QB[1]), abs(V.y - QB[2])) > RM_QUEST_SEE) V = B
	R["unit"] = V ? RmQuestCardUnit(V, Q) : null
	if(Q["maker"] == key) R["journal"] = Q["journal"]
	R["keeper"] = RmKeeperStrip(Q)   // opened from a keeper: its name and words, and Back (QuestKeepers.dm)
	return R

// The unit of this player at a board that can act there (take at any board listing it, hand in at its own), and what
// its units there carry of the kind asked for.
Player/proc/RmQuestCardUnit(mob/WorkShops/RemasterNoticeBoard/B, list/Q)
	var/mob/Monsters/best
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0 && RmQuestNear(M, B))
		best = M
		break
	if(!best) for(var/mob/Monsters/M in RmQuestNearUnits(B)) if(M.Owner == src && M.HP > 0)
		best = M
		break
	if(!best) return null
	var/list/U = list("ref"=RemasterUIRef(best), "name"=best.RemasterBareName())
	if(Q)
		var/list/QB = Q["board"]
		U["here"] = (B.x == QB[1] && B.y == QB[2] && B.z == QB[3])
		var/path = text2path(Q["item"])
		var/n = 0
		for(var/mob/Monsters/M in RmQuestNearUnits(B)) if(M.Owner == src && M.HP > 0)
			for(var/obj/Items/I in M) if(RmQuestGoodEnough(I, path, Q["quality"], Q["tokenWant"])) n++
		U["carry"] = n
	return U

// The Quests page: Taken (this player's log) and Ours (their notices); the post form's lists only while it is open.
Player/proc/RmQuestPageData()
	var/list/taken = list()
	for(var/id in rm_quest_log)
		var/list/E = rm_quest_log[id]
		var/list/Q = rm_quests[id]
		if(Q) taken += list(RmQuestRow(Q))
		else taken += list(list("id"=id, "title"=E["title"], "house"=E["house"], "state"="gone", "mine"=E["state"]))
	var/list/ours = list()
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		if(Q["maker"] == key) ours += list(RmQuestRow(Q))
	var/list/D = list("taken"=taken, "ours"=ours, "renown"=(rm_quest_renown[key] || 0), "coins"=remaster_coins,
		"open"=RmQuestRealmOpen(), "cap"=rm_quest_open_cap[clamp(remaster_rank, 1, length(rm_quest_open_cap))],
		"rank"=RmQuestRankName(remaster_rank), "cost"=RM_QUEST_POST_COST, "logMax"=RM_QUEST_LOG_MAX)
	D["standing"] = RmStandingRows()   // standing notices (QuestAdaptive.dm)
	if(rm_quest_post_open) D["post"] = RmQuestPostData()
	return D

// The post form: the unit by its own board (who posts and carries the reward goods), the kinds that may be asked for,
// the qualities, ranks and lengths.
Player/proc/RmQuestPostData()
	var/mob/Monsters/poster
	var/mob/WorkShops/RemasterNoticeBoard/B
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0)
		B = RmQuestBoardBeside(M, 1)
		if(B)
			poster = M
			break
	var/list/carry = list()
	if(poster) for(var/obj/Items/I in poster) if(I.suffix != "(Equipped)" && length(carry) < 60)
		carry += list(list("ref"=RemasterUIRef(I), "name"="[I.name]"))
	var/list/kinds = list()
	var/list/G = RmQuestGoods()
	for(var/p in G) kinds += list(list(p, G[p]))
	var/list/ranks = list()
	for(var/list/R in rm_ranks) ranks += R["name"]
	var/list/hunt = list()   // the goals on targets (QuestTargets.dm): kinds to hunt, build plans, what was picked
	for(var/r in rm_quest_hunt_kinds)
		var/list/HN = rm_quest_hunt_kinds[r]
		hunt += list(list(r, HN[2]))
	var/list/plans = list()
	if(rm_jz) for(var/list/Z in rm_jz) if(Z["kind"] == "build" && !Z["quest"] && length(Z["cells"]))
		plans += list(list(Z["id"], Z["name"], length(Z["cells"])))
	return list("unit"=(poster ? RemasterUIRef(poster) : null), "unitName"=(poster ? poster.RemasterBareName() : null),
		"board"=(B ? list(B.x, B.y, B.z) : null), "carry"=carry, "kinds"=kinds, "qualities"=rm_quest_qualities,
		"ranks"=ranks, "days"=rm_quest_days, "boards"=length(RmQuestBoardsOf(key)),
		"hunt"=hunt, "plans"=plans, "pick"=rm_quest_pick, "picked"=rm_quest_picked, "circle"=RM_QUEST_CIRCLE, "placeMax"=RM_QUEST_PLACE_MAX,
		"huntMax"=RM_QUEST_HUNT_MAX, "workMax"=RM_QUEST_WORK_MAX, "fortPicked"=rm_fort_picked, "fortMax"=RM_FORT_SIDE_MAX, "chain"=RmQuestChainChoices(), "rates"=RmQuestRates())

proc/RmQuestBoardsOf(key)
	. = list()
	for(var/mob/WorkShops/RemasterNoticeBoard/B in rm_notice_boards) if(RmQuestBoardKey(B) == key) . += B

// The tracker on the left: this player's open quests, rebuilt only when a quest changed (or once a minute, for the time
// left).
Player/proc/RmQuestTrackData()
	if(!length(rm_quest_log)) return null
	var/k = "[rm_quest_ver]|[round(world.time / 600)]"
	if(k == rm_quest_track_key) return rm_quest_track
	rm_quest_track_key = k
	var/list/L = list()
	for(var/id in rm_quest_log)
		var/list/E = rm_quest_log[id]
		var/list/Q = rm_quests[id]
		if(!Q || E["state"] != "taken" || (Q["state"] != "open" && Q["state"] != "closing")) continue
		var/list/T = Q["takers"][key]
		var/list/TR = list("id"=id, "title"=Q["title"], "goal"=(Q["goal"] || Q["itemName"]), "kind"=(Q["kind"] || "bring"), "got"=(T ? T["got"] : 0), "need"=Q["need"], "left"=RmQuestLeftText(Q["ends"]))
		var/list/MR = Q["target"] ? RmQuestMarkRow(Q, "taken") : null   // where to go: its marker, or the board to hand in at
		if(MR)
			for(var/f in list("x", "y", "z", "r", "ago")) TR[f] = MR[f]
		else if(!Q["target"])
			var/list/QB = Q["board"]
			TR["x"] = QB[1]
			TR["y"] = QB[2]
			TR["z"] = QB[3]
		L += list(TR)
	rm_quest_track = length(L) ? L : null
	return rm_quest_track

// The unit card's box: a single selected unit by a board (any board).
Player/proc/RmQuestBoxData(mob/Monsters/M)
	var/mob/WorkShops/RemasterNoticeBoard/B = RmQuestBoardBeside(M)
	if(!B) return null
	var/list/m = RmQuestMark(B)
	return list("house"=B.house || "[B.Owner]", "own"=(RmQuestBoardKey(B) == key), "n"=m["n"], "mark"=m["m"])

// The board's marker for this viewer: "?" when they have taken a quest posted there (hand in there), "!" when one there
// may be taken; n = the notices posted on it.
Player/proc/RmQuestMark(mob/WorkShops/RemasterNoticeBoard/B)
	var/list/C = RmQuestMarkCached(B)   // the same answer until a quest, this player's rank or the realms change (QuestScale.dm)
	if(C) return C
	var/list/I = RmQuestIndex()
	var/list/ids = I["[B.x],[B.y],[B.z]"]
	var/m = ""
	var/n = 0
	for(var/id in ids)
		var/list/Q = rm_quests[id]
		if(!RmQuestShown(Q, src)) continue
		n++
		if(Q["takers"][key])
			if(!Q["kind"] || Q["kind"] == "bring") m = "?"   // a goal on a target has nothing to hand in (QuestTargets.dm)
		else if(m == "" && !RmQuestWhyNot(Q, src)) m = "!"
	return RmQuestMarkKeep(B, list("n"=n, "m"=m))
