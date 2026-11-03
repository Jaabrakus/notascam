// Keepers (planning/QUEST_MAKER_PLAN_2026-10-31.md sections 4 and 15, phase Q7; the owner's "Yes, all eight", 10-31:
// "keepers yes, a few per realm, never a whole town of them"). A keeper is one of the maker's own units with a standing job:
//  - a quest giver stands by one of the maker's notice boards. Other realms' people talk to it (a click on it, or Talk
//    on the Interact (I) card), and beside it they take and hand in its quests as if at the board (RmQuestNear);
//  - a stall keeper is the maker's Merchant (Market.dm) with words of its own: talking to it shows what it sells.
// It stays the maker's unit: it eats and sleeps (the job waits, as any job does), can be killed or captured, and a capture
// ends its job. A gate warden waits for tolls (the economy plan), which the game doesn't have yet.
// Its words are the maker's: four lines (greeting, while you work, thanks, turn away) and up to 3 "Ask about" topics,
// filtered like chat (Moderation.dm) and reportable with the unit. An empty line is said in its race's own default words.
// The game fills in {taker}, {left}, {reward} and {house}. What a quest asks and pays is always the game's own card.

#define RM_KEEPER_MAX 3        // keepers a realm may have at once
#define RM_KEEPER_LINE 120     // a line of its words
#define RM_KEEPER_TOPICS 3     // "Ask about" topics
#define RM_KEEPER_ASK 40       // a topic's question
#define RM_KEEPER_ANSWER 200   // a topic's answer
#define RM_KEEPER_OFFERS 12    // quests it may be given to offer
#define RM_KEEPER_SIGHT 60     // tiles from one's own people to a keeper to talk (its board's reach for listing, RM_QUEST_SEE)
#define RM_KEEPER_THANKS 6000  // a quest of it done this lately (tenths of a second): it says thanks

// Saved with the unit: list("job"="quest"|"stall", "at"=list(x, y, z) of its board or stall, "key" and "house" of its
// maker, "offers"=its quest ids (null: all its board's), "words"=list(greet, work, thanks, away), "topics"=list(list(q, a)))
mob/Monsters/var/list/rm_keeper
var/list/rm_keepers = list()           // quest givers seen working (RmKeeperTick, RmKeeperMake): a board's reach
Player/var/tmp/rm_quest_keeper         // the keeper this player talks to ("\ref"); rm_quest_card "keeper" shows it
Player/var/tmp/rm_quest_keeper_q       // the quest opened from it: its card shows the keeper and Back

var/list/rm_keeper_line_names = list("Greeting", "While you work", "Thanks", "Turn away")
// Each race's own words, said when a line is left empty (no names: the world's places and people are the players').
var/list/rm_keeper_words = list(
	"Human"=list("Good day, {taker}. {house} has work, and pays for it.", "{left} still to go. We're counting on you.", "Well done. {house} keeps its word.", "Sorry, friend. This work isn't for your realm."),
	"Dwarf"=list("Well met, {taker}. You've the look of someone after work.", "Still {left} to go. The forge won't wait.", "Good work. It's yours, as promised.", "Not for the likes of your realm."),
	"Elf"=list("Be welcome, {taker}. {house} asks a service of you.", "{left} remain. The trees are patient; we are less so.", "Gracefully done. Take what was promised.", "This task is not for your people."),
	"Orc"=list("You. {taker}. Want work? {house} has work.", "{left} left. Move faster.", "Good. Take your pay.", "Not you. Go."),
	"Goblin"=list("Psst, {taker}! Shiny pay for quick hands.", "Still {left}! Hurry, hurry.", "Hehe, done! Pay's yours, fair and square.", "Nope. Not for your lot."),
	"Lizardman"=list("The sun is warm, {taker}. {house} has a task for you.", "{left} yet. Be patient as the swamp.", "It is done. Take your reward.", "Your realm may not take this."),
	"Frogman"=list("Hrrk. Welcome, {taker}. Work from {house}, if you want it.", "{left} more. The reeds are waiting.", "Good, good. The reward is yours.", "Not for your kind, sorry."),
	"Kobold"=list("Hello, {taker}! Many small jobs, many small coins!", "{left} still! Quick, quick!", "Done! Done! Take, take!", "No, no. Not for your realm."),
	"Ratman"=list("Sss, {taker}. Coin for work. Interested?", "Still {left}. We are watching.", "Done. Take the coin. Go.", "Not for your nest."))

proc/RmKeeperDefaults(race)
	return rm_keeper_words["[race]"] || rm_keeper_words["Human"]

// --- the keeper ---------------------------------------------------------------------------------------------------------
// Its job, still good: alive, still its maker's (a capture ends it), on the job it was given (other work ends it).
proc/RmKeeperOk(mob/Monsters/K)
	var/list/R = K ? K.rm_keeper : null
	if(!R || Rm3DGone(K) || K.HP <= 0) return 0
	if(istype(K.Owner, /Player) && K.Owner:key != R["key"])
		RmKeeperEnd(K, 0)
		return 0
	if(K.remaster_job != (R["job"] == "stall" ? "merchant" : "keeper"))
		RmKeeperEnd(K, 0)
		return 0
	return 1

// Not a keeper any more. back: a quest giver goes back to Manual (a stall keeper stays its realm's Merchant).
proc/RmKeeperEnd(mob/Monsters/K, back = 1)
	if(back && K.rm_keeper && K.rm_keeper["job"] == "quest" && K.remaster_job == "keeper") K.RemasterAssignJob("manual")
	K.rm_keeper = null
	rm_keepers -= K

// Its board or stall.
proc/RmKeeperPlace(mob/Monsters/K)
	var/list/A = K.rm_keeper ? K.rm_keeper["at"] : null
	if(!islist(A) || length(A) < 3) return null
	var/turf/T = locate(A[1], A[2], A[3])
	if(!T) return null
	if(K.rm_keeper["job"] == "stall") return locate(/mob/WorkShops/RemasterStall) in T
	return locate(/mob/WorkShops/RemasterNoticeBoard) in T

// The quest giver's job (Settlement.dm runs it as the Merchant's): walk to its board and stand by it.
mob/Monsters/proc/RmKeeperTick(Player/P)
	if(!RmKeeperOk(src))
		if(remaster_job == "keeper") RemasterAssignJob("manual")
		return
	if(!(src in rm_keepers)) rm_keepers += src
	var/mob/WorkShops/RemasterNoticeBoard/B = RmKeeperPlace(src)
	if(!B)
		remaster_work_status = "Quest giver: its notice board is gone"
		return
	if(z == B.z && get_dist(src, B) <= 1)
		destination = null
		remaster_work_destination = null
		remaster_work_status = "Quest giver: by the notice board"
		return
	destination = B
	remaster_work_destination = B
	remaster_work_status = "Quest giver: walking to the notice board"

// The quest givers working by this board.
proc/RmKeepersAt(mob/WorkShops/RemasterNoticeBoard/B)
	. = list()
	for(var/mob/Monsters/K in rm_keepers.Copy())
		if(!RmKeeperOk(K))
			rm_keepers -= K
			continue
		if(K.rm_keeper["job"] == "quest" && K.z == B.z && get_dist(K, B) <= RM_QUEST_REACH && RmKeeperPlace(K) == B) . += K

// --- a board's reach (Quests.dm): beside it, or beside a quest giver standing by it ------------------------------------
proc/RmQuestNear(mob/Monsters/M, mob/WorkShops/RemasterNoticeBoard/B)
	if(!M || !B || !isturf(M.loc) || M.z != B.z) return 0
	if(get_dist(M, B) <= RM_QUEST_REACH) return 1
	for(var/mob/Monsters/K in RmKeepersAt(B)) if(get_dist(M, K) <= RM_QUEST_REACH) return 1
	return 0

proc/RmQuestNearUnits(mob/WorkShops/RemasterNoticeBoard/B)
	. = list()
	for(var/mob/Monsters/M in range(RM_QUEST_REACH, B)) . += M
	for(var/mob/Monsters/K in RmKeepersAt(B))
		for(var/mob/Monsters/M in range(RM_QUEST_REACH, K)) if(!(M in .)) . += M

// No board beside M: the board of a quest giver M stands beside.
proc/RmKeeperBoardBeside(mob/Monsters/M)
	if(!M || !isturf(M.loc)) return null
	for(var/mob/Monsters/K in rm_keepers.Copy()) if(K.z == M.z && get_dist(K, M) <= RM_QUEST_REACH && RmKeeperOk(K) && K.rm_keeper["job"] == "quest")
		var/mob/WorkShops/RemasterNoticeBoard/B = RmKeeperPlace(K)
		if(B && B.z == K.z && get_dist(K, B) <= RM_QUEST_REACH) return B
	return null

// --- what it offers and says, for a viewer --------------------------------------------------------------------------------
// Its quests: those it was given (all its board's when none were picked), open, that this viewer may see.
Player/proc/RmKeeperQuests(mob/Monsters/K, shown = 1)
	. = list()
	var/mob/WorkShops/RemasterNoticeBoard/B = RmKeeperPlace(K)
	if(!B || K.rm_keeper["job"] != "quest") return
	var/list/I = RmQuestIndex()
	var/list/offers = K.rm_keeper["offers"]
	for(var/id in I["[B.x],[B.y],[B.z]"])
		if(islist(offers) && !(id in offers)) continue
		var/list/Q = rm_quests[id]
		if(Q && (!shown || RmQuestShown(Q, src))) . += list(Q)

// Its marker for this viewer: "?" one to hand in, "!" one to take, "..." one taken; with its name and job.
Player/proc/RmKeeperMark(mob/Monsters/K)
	if(!RmKeeperOk(K)) return null
	var/list/R = K.rm_keeper
	var/m = ""
	if(R["job"] == "quest" && R["key"] != key)
		for(var/list/Q in RmKeeperQuests(K))
			if(Q["takers"][key])
				if(!Q["kind"] || Q["kind"] == "bring") m = "?"
				else if(m == "") m = "..."
			else if(m != "?" && !RmQuestWhyNot(Q, src)) m = "!"
	return list("m"=m, "n"=K.RemasterBareName(), "j"=(R["job"] == "stall" ? "stall keeper" : "quest giver"))

// The line it says to this viewer, and which: work (a quest of it taken), thanks (one done lately), away (none of its
// quests is for them), else its greeting; filled in.
Player/proc/RmKeeperLine(mob/Monsters/K)
	var/list/R = K.rm_keeper
	var/which = 1
	var/list/about
	if(R["key"] != key && R["job"] == "quest")
		var/list/taken
		var/list/first
		var/barred = 0
		var/hidden = 0
		for(var/list/Q in RmKeeperQuests(K, 0))
			if(!RmQuestShown(Q, src))
				hidden++
				continue
			if(Q["takers"][key])
				if(!taken) taken = Q
				continue
			var/why = RmQuestWhyNot(Q, src)
			if(!why)
				if(!first) first = Q
			else if(findtext(why, "Only for") == 1 || findtext(why, "Your realm has done it") == 1) barred++
		var/list/won
		var/mob/WorkShops/RemasterNoticeBoard/B = RmKeeperPlace(K)
		if(B && !taken) for(var/id in rm_quests)
			var/list/D = rm_quests[id]
			var/list/DB = D["board"]
			if(D["state"] == "done" && D["winner"] == key && DB[1] == B.x && DB[2] == B.y && DB[3] == B.z && RemasterSince(D["closed"]) < RM_KEEPER_THANKS) won = D
		if(taken)
			which = 2
			about = taken
		else if(won)
			which = 3
			about = won
		else if(!first && (barred || hidden))
			which = 4
		else about = first
	else if(R["job"] == "quest")   // its maker's Preview: about its first quest, so {reward} reads as others will see it
		var/list/QS = RmKeeperQuests(K)
		if(length(QS)) about = QS[1]
	var/list/W = R["words"]
	var/list/DW = RmKeeperDefaults(K.Race)
	var/t = (islist(W) && length(W) >= which && length(W[which])) ? W[which] : DW[which]
	return list(rm_keeper_line_names[which], RmKeeperFill(t, src, K, about))

proc/RmKeeperFill(t, Player/P, mob/Monsters/K, list/Q)
	t = replacetext("[t]", "{taker}", P.RemasterHouse())
	t = replacetext(t, "{house}", "[K.rm_keeper["house"]]")
	t = replacetext(t, "{reward}", Q ? RmQuestRewardText(Q) : "a fair reward")
	var/left = "a little"
	if(Q)
		var/list/T = Q["takers"][P.key]
		if(!Q["kind"] || Q["kind"] == "bring") left = "[max(0, Q["need"] - (T ? T["got"] : 0))] [Q["itemName"]]"
		else left = Q["goal"] || Q["title"]
	return replacetext(t, "{left}", left)

// This player's unit beside it (a selected one first).
Player/proc/RmKeeperTalker(mob/Monsters/K)
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0 && isturf(M.loc) && M.z == K.z && get_dist(M, K) <= RM_QUEST_REACH) return M
	for(var/mob/Monsters/M in range(RM_QUEST_REACH, K)) if(M.Owner == src && M.HP > 0) return M
	return null

// The talk card (Quests.dm RmQuestCardData, kind "keeper").
Player/proc/RmKeeperCardData()
	var/mob/Monsters/K = locate(rm_quest_keeper)
	if(!istype(K) || !RmKeeperOk(K))
		rm_quest_card = null
		rm_quest_keeper = null
		return null
	var/list/R = K.rm_keeper
	var/stall = R["job"] == "stall"
	var/list/rows = list()
	if(!stall) for(var/list/Q in RmKeeperQuests(K))
		var/list/W = RmQuestRow(Q)
		W["tag"] = W["mine"] == "taken" ? (W["mark"] == "?" ? "hand it in here" : "you took this") : (Q["kind"] == "fort" ? "fort challenge" : W["goal"])
		rows += list(W)
	var/list/L = RmKeeperLine(K)
	var/list/topics = list()
	for(var/list/T in R["topics"]) topics += list(list(T[1], RmKeeperFill(T[2], src, K, null)))
	var/mob/Monsters/U = RmKeeperTalker(K)
	var/list/D = list("kind"="keeper", "ref"="\ref[K]", "name"=K.RemasterBareName(), "house"=R["house"], "job"=R["job"],
		"race"="[K.Race]", "attack"=RemasterCombatLevel(K, "Attack"), "portrait"=RemasterPortrait(K),
		"line"=L[2], "lineKind"=L[1], "rows"=rows, "topics"=topics, "own"=(R["key"] == key),
		"unit"=(U ? U.RemasterBareName() : null))
	if(stall && U)
		D["uref"] = RemasterUIRef(U)
		D["market"] = RemasterMarketData(U)
	return D

// The quest card opened from it: its name and what it says (Quests.dm).
Player/proc/RmKeeperStrip(list/Q)
	if(!rm_quest_keeper || rm_quest_keeper_q != Q["id"]) return null
	var/mob/Monsters/K = locate(rm_quest_keeper)
	if(!istype(K) || !RmKeeperOk(K)) return null
	var/list/L = RmKeeperLine(K)
	return list("name"=K.RemasterBareName(), "line"=L[2])

// Close enough to talk: one of this player's people within sight of it, or its maker.
Player/proc/RmKeeperInSight(mob/Monsters/K)
	if(K.rm_keeper["key"] == key) return 1
	for(var/mob/Monsters/M in UnitList) if(M.HP > 0 && M.z == K.z && get_dist(M, K) <= RM_KEEPER_SIGHT) return 1
	return 0

// A click on another realm's keeper (QoL.dm RemasterMapOrder): talk; nobody beside it, the selected walk over.
Player/proc/RmKeeperClick(mob/Monsters/K)
	var/mob/Monsters/first = Selected[1]
	if(!RmKeeperTalker(K) && istype(first) && first.Owner == src)
		var/turf/T = get_step(K, get_dir(K, first))
		RemasterOrder(T || K.loc, 0, "Move")
	RmKeeperCommand("keeper", "\ref[K]")
	return 1

// --- the maker's side: the Keeper tab and the boxes that make one -----------------------------------------------------
Player/proc/RmKeeperCount()
	. = 0
	for(var/mob/Monsters/M in UnitList) if(M.rm_keeper && RmKeeperOk(M)) .++

// The board or market box's "make a keeper" (a single own unit by its own board or stall, not a keeper yet).
Player/proc/RmKeeperMakeData(mob/Monsters/M)
	if(M.Owner != src || M.HP <= 0 || RmGuestKey(key) || (M.rm_keeper && RmKeeperOk(M))) return null
	var/q = RmQuestBoardBeside(M, 1) ? 1 : 0
	var/s = 0
	for(var/mob/WorkShops/RemasterStall/S in range(2, M)) if(S.Owner == src) s = 1
	if(!q && !s) return null
	return list("quest"=q, "stall"=s, "left"=RM_KEEPER_MAX - RmKeeperCount(), "max"=RM_KEEPER_MAX)

// The Keeper tab (one of this player's keepers).
Player/proc/RmKeeperTabData(mob/Monsters/M)
	if(M.Owner != src || !M.rm_keeper || !RmKeeperOk(M)) return null
	var/list/R = M.rm_keeper
	var/list/A = R["at"]
	var/list/boards = list()   // where it may stand, for each job (no distances: the tab would be drawn again at each step)
	for(var/mob/WorkShops/RemasterNoticeBoard/B in RmQuestBoardsOf(key)) if(length(boards) < 12) boards += list(list("[B.x],[B.y],[B.z]", "Notice board at [B.x], [B.y]"))
	var/list/stalls = list()
	for(var/mob/WorkShops/RemasterStall/S in rm_chain_stalls) if(S.Owner == src && length(stalls) < 12) stalls += list(list("[S.x],[S.y],[S.z]", "Market stall at [S.x], [S.y]"))
	var/list/offers = list()
	var/mob/WorkShops/RemasterNoticeBoard/B = R["job"] == "quest" ? RmKeeperPlace(M) : null
	var/list/I = RmQuestIndex()
	if(B) for(var/id in I["[B.x],[B.y],[B.z]"]) if(length(offers) < RM_KEEPER_OFFERS)
		var/list/Q = rm_quests[id]
		offers += list(list(id, Q["title"], !islist(R["offers"]) || (id in R["offers"])))
	return list("job"=R["job"], "at"="[A[1]],[A[2]],[A[3]]", "boards"=boards, "stalls"=stalls, "offers"=offers, "words"=R["words"],
		"defaults"=RmKeeperDefaults(M.Race), "topics"=R["topics"], "race"="[M.Race]", "count"=RmKeeperCount(), "max"=RM_KEEPER_MAX,
		"lines"=RM_KEEPER_LINE, "ask"=RM_KEEPER_ASK, "answer"=RM_KEEPER_ANSWER, "topicMax"=RM_KEEPER_TOPICS)

Player/proc/RmKeeperMake(mob/Monsters/M, job)
	if(!istype(M) || M.Owner != src || M.HP <= 0 || (M.rm_keeper && RmKeeperOk(M))) return 0
	if(RmGuestKey(key))
		RemasterNotice("Guests can't have keepers: nothing of a guest's is kept.")
		return 0
	if(RmKeeperCount() >= RM_KEEPER_MAX)
		RemasterNotice("A realm has at most [RM_KEEPER_MAX] keepers. Free one first: its Keeper tab, Job: None.")
		return 0
	var/atom/A
	if(job == "stall")
		for(var/mob/WorkShops/RemasterStall/S in range(2, M)) if(S.Owner == src) A = S
	else A = RmQuestBoardBeside(M, 1)
	if(!A)
		RemasterNotice("[M.RemasterBareName()] must stand by your own [job == "stall" ? "market stall" : "notice board"].")
		return 0
	M.RemasterAssignJob(job == "stall" ? "merchant" : "keeper")
	M.rm_keeper = list("job"=(job == "stall" ? "stall" : "quest"), "at"=list(A.x, A.y, A.z), "key"=key, "house"=RemasterHouse(),
		"offers"=null, "words"=list("", "", "", ""), "topics"=list())
	if(job != "stall") rm_keepers += M
	M.remaster_work_status = job == "stall" ? "Merchant: at the stall" : "Quest giver: by the notice board"
	RemasterNotice("[M.RemasterBareName()] is your [job == "stall" ? "stall keeper" : "quest giver"] now. Give them their words on their Keeper tab.")
	RemasterLog("[M.RemasterBareName()] became a keeper: [job == "stall" ? "stall keeper" : "quest giver"]", "good", M)
	return 1

// The Keeper tab's Save: {"job":"quest"|"stall"|"none", "at":"x,y,z", "all":1 or "offers":[ids], "words":[4], "topics":[[q, a]]}
Player/proc/RmKeeperSave(mob/Monsters/M, json)
	if(!istype(M) || M.Owner != src || !RmKeeperOk(M)) return 0
	var/list/A = json_decode("[json]")
	if(!islist(A)) return 0
	var/list/R = M.rm_keeper
	if(A["job"] == "none")
		var/nm = M.RemasterBareName()
		RmKeeperEnd(M)
		RemasterNotice("[nm] is no keeper any more.")
		return 1
	var/job = A["job"] == "stall" ? "stall" : "quest"
	var/list/c = splittext("[A["at"]]", ",")
	var/atom/P
	if(length(c) == 3)
		var/turf/T = locate(text2num(c[1]), text2num(c[2]), text2num(c[3]))
		if(T) P = job == "stall" ? locate(/mob/WorkShops/RemasterStall) in T : locate(/mob/WorkShops/RemasterNoticeBoard) in T
	if(!P || (job == "stall" ? P:Owner != src : RmQuestBoardKey(P) != key))
		RemasterNotice("Pick one of your own [job == "stall" ? "market stalls" : "notice boards"] for them to stand at.")
		return 0
	if(job != R["job"])
		M.RemasterAssignJob(job == "stall" ? "merchant" : "keeper")
		R["job"] = job
	R["at"] = list(P.x, P.y, P.z)
	if(job == "quest" && !(M in rm_keepers)) rm_keepers += M
	if(job == "stall") rm_keepers -= M
	if(A["all"] || !islist(A["offers"])) R["offers"] = null
	else
		var/list/I = RmQuestIndex()
		var/list/own = I["[P.x],[P.y],[P.z]"] || list()
		var/list/O = list()
		for(var/id in A["offers"]) if(("[id]" in own) && length(O) < RM_KEEPER_OFFERS) O += "[id]"
		R["offers"] = O
	var/list/W = list()
	var/list/WA = islist(A["words"]) ? A["words"] : list()
	for(var/i = 1, i <= 4, i++) W += RmModFilter(RmQuestText(i <= length(WA) ? WA[i] : "", RM_KEEPER_LINE))   // the admins' word list
	R["words"] = W
	var/list/T = list()
	if(islist(A["topics"])) for(var/list/X in A["topics"]) if(length(X) >= 2 && length(T) < RM_KEEPER_TOPICS)
		var/q = RmModFilter(RmQuestText(X[1], RM_KEEPER_ASK))
		var/a = RmModFilter(RmQuestText(X[2], RM_KEEPER_ANSWER))
		if(length(q) && length(a)) T += list(list(q, a))
	R["topics"] = T
	R["house"] = RemasterHouse()
	RemasterNotice("Saved: [M.RemasterBareName()]'s words.")
	return 1

// --- commands (Quests.dm RmQuestCommand: "keeper..." actions) --------------------------------------------------------
Player/proc/RmKeeperCommand(act, rest)
	var/i = findtext(rest, "|")
	var/a1 = i ? copytext(rest, 1, i) : rest
	var/more = i ? copytext(rest, i + 1) : ""
	switch(act)
		if("keeper")      // talk: keeper|<its \ref>
			var/mob/Monsters/K = locate(a1)
			if(!istype(K) || !RmKeeperOk(K)) return 0
			if(!RmKeeperInSight(K))
				RemasterNotice("Too far away to talk to [K.RemasterBareName()].")
				return 0
			rm_quest_keeper = "\ref[K]"
			rm_quest_keeper_q = null
			var/mob/WorkShops/RemasterNoticeBoard/B = K.rm_keeper["job"] == "quest" ? RmKeeperPlace(K) : null
			if(B) rm_quest_board = list(B.x, B.y, B.z)
			rm_quest_card = "keeper"
			return 1
		if("keeperq")     // one of its quests: keeperq|<id>
			if(!rm_quest_keeper || !rm_quests[a1]) return 0
			RmQuestCommand("open|[a1]")
			rm_quest_keeper_q = a1
			return 1
		if("keeperback")  // from its quest's card, back to it
			if(!rm_quest_keeper) return 0
			rm_quest_card = "keeper"
			return 1
		if("keepermake")  // keepermake|<unit ref>|quest or stall
			return RmKeeperMake(RemasterUIUnit(a1), more == "stall" ? "stall" : "quest")
		if("keepersave")  // keepersave|<unit ref>|<json>
			return RmKeeperSave(RemasterUIUnit(a1), more)
		if("keeperpreview")  // its maker sees it as others do: keeperpreview|<unit ref>
			var/mob/Monsters/M = RemasterUIUnit(a1)
			if(!istype(M) || M.Owner != src || !RmKeeperOk(M)) return 0
			return RmKeeperCommand("keeper", "\ref[M]")
	return 0
