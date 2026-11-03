// Quests with many players (planning/QUEST_MAKER_PLAN_2026-10-31.md sections 9 and 11, phase Q9; the owner, 10-31: do the
// part that is ready now, region saves and far-record garrisons waiting for REGIONS_ON_DISK R3 and far records).
//  - Every quest carries its region key: one value until hex regions are in the game, so R3 can split the quests' save by
//    region (each region's file holding its sites and quests) without touching the records again.

// The region a place belongs to. One region until hex regions are in the game (WORLDGEN; then the hex id).
proc/RmQuestRegion(x, y, z)
	return RmRegionId(x, y, z)   // the region file it is saved in (WorldRegions.dm)

// Saves from before Q9: each quest gets its region from its board's place.
proc/RmQuestRegionsFill()
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		var/list/B = Q["board"]
		if(islist(B) && length(B) >= 3) Q["region"] = RmQuestRegion(B[1], B[2], B[3])   // also saves from before R3 ("heartland")

// - Built again only when what it shows can change (the scale test, tests/quest_scale_check.dm: 10 realms, 500 quests,
//   50 forts: the Quests page took 1.7 ms a HUD send, a board's 3D marker 0.6 ms a board a scene, a board's card 1 ms a
//   send). A quest's change anywhere (RmQuestChanged: rm_quest_ver), this player's rank or coins, the realms and their
//   alliances (rm_realm_ver), the minute (the days left) and, for a board's card, the people at it and the order asked.
Player/var/tmp/rm_quest_mark_key
Player/var/tmp/list/rm_quest_mark_cache
Player/var/tmp/rm_quest_card_key
Player/var/tmp/list/rm_quest_card_cache
Player/var/tmp/rm_quest_page_key
Player/var/tmp/list/rm_quest_page_cache

// A board's marker for this player (Quests.dm RmQuestMark: the 3D view asks for every board in view, every scene).
Player/proc/RmQuestMarkCached(mob/WorkShops/RemasterNoticeBoard/B)
	var/ck = "[rm_quest_ver]|[remaster_rank]|[rm_realm_ver]"
	if(rm_quest_mark_key != ck)
		rm_quest_mark_key = ck
		rm_quest_mark_cache = list()
		return null
	return rm_quest_mark_cache["[B.x],[B.y],[B.z]"]

Player/proc/RmQuestMarkKeep(mob/WorkShops/RemasterNoticeBoard/B, list/M)
	if(rm_quest_mark_cache) rm_quest_mark_cache["[B.x],[B.y],[B.z]"] = M
	return M

// The card the HUD sends (HUD.dm): a board's notices kept while nothing they show changed; a quest's card as before.
Player/proc/RmQuestCardDataCached()
	if(rm_quest_card != "board") return RmQuestCardData()
	var/mob/WorkShops/RemasterNoticeBoard/B = RmQuestBoardAt(rm_quest_board)
	if(!B) return RmQuestCardData()
	var/list/U = RmQuestCardUnit(B)
	var/k = "[rm_quest_ver]|[B.x],[B.y],[B.z]|[remaster_rank]|[rm_realm_ver]|[round(world.time / 600)]|[RmQuestPartyPower(B)]|[U ? U["ref"] : ""]|[rm_quest_sort]|[rm_quest_renown[RmQuestBoardKey(B)]]"
	if(k == rm_quest_card_key && rm_quest_card_cache) return rm_quest_card_cache
	rm_quest_card_key = k
	rm_quest_card_cache = RmQuestCardData()
	return rm_quest_card_cache

// The Quests page the HUD sends: its lists kept while nothing they show changed; the post form is built each time (it
// reads the poster's pack and what is being picked).
Player/proc/RmQuestPageDataCached()
	if(rm_quest_post_open) return RmQuestPageData()
	var/k = "[rm_quest_ver]|[remaster_coins]|[remaster_rank]|[rm_realm_ver]|[round(world.time / 600)]|[rm_quest_renown[key]]|[json_encode(RmStandingRows())]"
	if(k == rm_quest_page_key && rm_quest_page_cache) return rm_quest_page_cache
	rm_quest_page_key = k
	rm_quest_page_cache = RmQuestPageData()
	return rm_quest_page_cache
