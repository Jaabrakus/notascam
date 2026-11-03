// Quests that connect (planning/QUEST_MAKER_PLAN_2026-10-31.md section 7, phase Q6; the owner's "Yes, all eight", 10-31).
// A notice can say what has to come first: other notices done, or failed, all of them or any one ("after"). It can give a
// token when done: a real item ("the hold's seal") that can be traded, stolen or lost, and that another notice's Bring
// goal can ask for, by anyone's notice, so chains cross between players with no other link. A step's target can be kept
// secret until the step before it is done (section 17: "the seal tells you where the hold is"). A fort's tiers are two
// fort notices, the inner one after the outer.
//  - Done: the taker's realm did it (its record), or their quest log says so. Failed: they gave it up, it came down while
//    they held it, someone else did it first, or (a fort) they lost a try.
//  - Limits at posting: links only to notices the maker can see (their own, or on their boards), at most
//    RM_QUEST_LINKS of them, at most RM_QUEST_CHAIN_DEPTH steps deep. A new notice can't be linked to before it exists,
//    so a chain has no loops.
//  - A record linked to by an open notice is kept past its usual few days (RmQuestTick), so "after" can still be read.

#define RM_QUEST_LINKS 3
#define RM_QUEST_CHAIN_DEPTH 10
#define RM_QUEST_TOKEN_TYPE /obj/Items/Shafts/MagicScroll/RemasterToken

var/list/rm_quest_next_of = list()   // a notice's id -> the open notices that come after it (RmQuestKinds)

obj/Items/Shafts/MagicScroll/RemasterToken
	desc = "A token from a quest: another quest may ask for it."
	weight = 0
	var/rm_token                      // the id of the notice that gave it ("tok-q12")
	var/rm_token_from                 // the house that gave it

// --- links ------------------------------------------------------------------------------------------------------------
proc/RmQuestLinkMet(list/L, Player/P)
	var/list/A = rm_quests[L[1]]
	var/list/E = P.rm_quest_log ? P.rm_quest_log[L[1]] : null
	if(L[2] == "failed") return (A && islist(A["failed"]) && (P.key in A["failed"])) || (E && E["state"] == "failed")
	return (A && (RemasterRootKey(P.key) in A["realms_done"])) || (E && E["state"] == "done")

// Why P can't take Q yet for its links ("" = they can).
proc/RmQuestAfterWhy(list/Q, Player/P)
	var/list/links = Q["after"]
	if(!length(links)) return ""
	var/any = Q["afterMode"] == "any"
	var/list/miss = list()
	for(var/list/L in links)
		if(RmQuestLinkMet(L, P))
			if(any) return ""
		else miss += "[L[2] == "failed" ? "failing" : "doing"] \"[L[3]]\" ([L[4]])"
	if(!length(miss)) return ""
	return any ? "Only after one of: [jointext(miss, "; ")]." : "Only after [jointext(miss, " and ")]."

proc/RmQuestChainDepth(id, n = 0)
	if(n > RM_QUEST_CHAIN_DEPTH) return n
	var/list/Q = rm_quests[id]
	. = n
	if(Q) for(var/list/L in Q["after"]) . = max(., RmQuestChainDepth(L[1], n + 1))

// May this player link a new notice to that one? Their own, or one their boards would show them.
Player/proc/RmQuestMayLink(list/Q)
	return Q && (Q["maker"] == key || RmQuestShown(Q, src))

// The post form's chain fields, checked: list("after"=..., "afterMode"=..., "token"=..., "secret"=...) or a reason.
Player/proc/RmQuestChainPost(list/A)
	var/list/C = list()
	var/list/links = list()
	var/list/ids = islist(A["after"]) ? A["after"] : list()
	for(var/list/L in ids)
		if(length(L) < 2) continue
		var/list/Q = rm_quests["[L[1]]"]
		if(!RmQuestMayLink(Q)) return "A notice it comes after is gone, or not one you can see."
		if(RmQuestChainDepth(Q["id"]) >= RM_QUEST_CHAIN_DEPTH) return "A chain is at most [RM_QUEST_CHAIN_DEPTH] steps."
		links += list(list(Q["id"], L[2] == "failed" ? "failed" : "done", Q["title"], Q["house"]))
		if(length(links) > RM_QUEST_LINKS) return "A notice comes after at most [RM_QUEST_LINKS] others."
	if(length(links))
		C["after"] = links
		C["afterMode"] = A["afterMode"] == "any" ? "any" : "all"
	var/tok = RmModFilter(RmQuestText(A["gives"], 30))   // the admins' word list (Moderation.dm)
	if(length(tok)) C["token"] = tok
	if(A["secret"] == "1" && length(links)) C["secret"] = 1
	return C

proc/RmQuestChainPut(list/Q, list/C)
	for(var/k in C) Q[k] = C[k]
	if(Q["token"]) Q["tokenId"] = "tok-[Q["id"]]"

// A notice's taker who didn't do it: for "after ... failed".
proc/RmQuestFailed(list/Q, key)
	if(!islist(Q["failed"])) Q["failed"] = list()
	if(!(key in Q["failed"])) Q["failed"] += key

// --- tokens ---------------------------------------------------------------------------------------------------------------
// The token a done notice gives: into the pack of the one who did it (or at its feet), the taker's.
proc/RmQuestGiveToken(list/Q, Player/P, mob/Monsters/M, turf/MT, key)
	if(!Q["token"]) return null
	var/obj/Items/Shafts/MagicScroll/RemasterToken/T = new(M || MT)
	T.name = Q["token"]
	T.rm_token = Q["tokenId"]
	T.rm_token_from = Q["house"]
	T.desc = "A token from [Q["house"]]'s \"[Q["title"]]\": another quest may ask for it."
	T.remaster_owner_key = key
	T.Owner = P
	T.suffix = M ? "(Carrying)" : null
	return T

// The name of the token with this id, when this player may ask for it (it comes from a notice they can see).
Player/proc/RmQuestTokenFor(tid)
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		if(Q["tokenId"] == "[tid]" && RmQuestMayLink(Q)) return Q["token"]
	return null

// For the post form: notices to come after, tokens to ask for.
Player/proc/RmQuestChainChoices()
	var/list/links = list()
	var/list/tokens = list()
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		if(!RmQuestMayLink(Q) || Q["maker"] == rm_world_key) continue   // the world's notices aren't steps (QuestAdaptive.dm)
		if(length(links) < 60) links += list(list(id, Q["title"], Q["house"], Q["state"]))
		if(Q["tokenId"] && length(tokens) < 40) tokens += list(list(Q["tokenId"], Q["token"], Q["house"]))
	return list("links"=links, "tokens"=tokens)

// --- the card --------------------------------------------------------------------------------------------------------------
Player/proc/RmQuestChainCard(list/Q)
	var/list/after = list()
	for(var/list/L in Q["after"]) after += list(list(L[3], L[4], L[2], RmQuestLinkMet(L, src)))
	var/list/next = list()
	for(var/id in rm_quest_next_of[Q["id"]])
		var/list/N = rm_quests[id]
		if(N && RmQuestShown(N, src)) next += N["title"]
	if(!length(after) && !length(next) && !Q["token"] && !Q["tokenWant"]) return null
	return list("after"=after, "mode"=(Q["afterMode"] || "all"), "next"=next, "token"=Q["token"], "wants"=(Q["tokenWant"] ? Q["itemName"] : null), "secret"=Q["secret"])
