// A group action's own replies, one line each (server cost, 2026-10-25; the user's chat rule: replies to the player's
// own actions are short toasts, and 150 of the same is spam). While one unit of a group Interact (GroupInteract.dm
// RmGiRun) runs its action, a kept chat line that starts with that unit's name is counted instead of sent (Chat.dm
// RemasterChatKeep asks RmChatGroupTake). When the group is done, each kind of line goes once: as it was, for one
// unit; "150 of your units start to fly!" for many. A unit is counted once per kind, so a line two players got isn't
// counted twice. Only lines sent in the tick the unit's action started are counted: an action that waits (the first
// unit's follow-up question card, a spawned step) sends what comes after the wait as it is, so nothing else about that
// unit (a hit, a death) is ever held for the group's end (hud-craft, 10-25).
var/mob/Monsters/rm_chat_group_unit      // the unit whose group action is running now
var/Player/rm_chat_group_player          // ...and whose group it is
var/rm_chat_group_at = -1                // ...and the tick its action started
Player/var/tmp/list/rm_chat_group        // the line after the name -> list(the first whole line, the units it came from)
Player/var/tmp/list/rm_chat_group_order  // ...in the order they first came

// Chat.dm RemasterChatKeep, for a line it keeps while a group action runs: 0, counted (sent at the end), or 1, sent now.
proc/RmChatGroupTake(text)
	var/mob/Monsters/M = rm_chat_group_unit
	var/Player/P = rm_chat_group_player
	if(!M || !P || world.time != rm_chat_group_at) return 1
	var/name = "[M]"
	if(!length(name) || findtextEx(text, name) != 1) return 1
	var/rest = copytext(text, length(name) + 1)
	if(!P.rm_chat_group)
		P.rm_chat_group = list()
		P.rm_chat_group_order = list()
	var/list/G = P.rm_chat_group[rest]
	if(!G)
		G = list(text, list())
		P.rm_chat_group[rest] = G
		P.rm_chat_group_order += rest
	var/list/U = G[2]
	if(!(M in U)) U += M
	return 0

Player/RmGiRun(mob/Monsters/M, menu, entry, first)
	var/was_unit = rm_chat_group_unit
	var/was_player = rm_chat_group_player
	var/was_at = rm_chat_group_at
	rm_chat_group_unit = M
	rm_chat_group_player = src
	rm_chat_group_at = world.time
	. = ..()
	rm_chat_group_unit = was_unit
	rm_chat_group_player = was_player
	rm_chat_group_at = was_at

Player/RmGroupInteract()
	RmChatGroupFlush()   // any left by a group cut short
	. = ..()
	RmChatGroupFlush()

// Each kind of line once: the line itself for one unit, how many of them for more.
Player/proc/RmChatGroupFlush()
	if(!rm_chat_group) return
	var/list/G = rm_chat_group
	var/list/order = rm_chat_group_order
	rm_chat_group = null
	rm_chat_group_order = null
	for(var/rest in order)
		var/list/E = G[rest]
		var/n = length(E[2])
		RmChatGroupSay(n <= 1 ? E[1] : RmChatGroupMany(n, rest, E[1]))

Player/proc/RmChatGroupSay(text)
	src << text

// "150 of your units start to fly!" from " starts to fly!"; where the line doesn't go on with a verb (a name's "'s"),
// the first one's line and how many more.
var/list/rm_chat_group_irregular = list("is" = "are", "was" = "were", "has" = "have", "does" = "do", "goes" = "go")
proc/RmChatGroupEnds(word, suffix)
	return length(word) > length(suffix) && copytext(word, length(word) - length(suffix) + 1) == suffix

proc/RmChatGroupMany(n, rest, first)
	if(copytext(rest, 1, 2) == " ")
		var/sp = findtext(rest, " ", 2)
		var/word = sp ? copytext(rest, 2, sp) : copytext(rest, 2)
		var/tail = sp ? copytext(rest, sp) : ""
		var/plural
		if(rm_chat_group_irregular[word]) plural = rm_chat_group_irregular[word]
		else if(RmChatGroupEnds(word, "ies")) plural = copytext(word, 1, length(word) - 2) + "y"
		else if(RmChatGroupEnds(word, "ches") || RmChatGroupEnds(word, "shes") || RmChatGroupEnds(word, "sses") || RmChatGroupEnds(word, "xes")) plural = copytext(word, 1, length(word) - 1)
		else if(RmChatGroupEnds(word, "s") && !RmChatGroupEnds(word, "ss")) plural = copytext(word, 1, length(word))
		if(plural) return "[n] of your units [plural][tail]"
	return "[first] (and [n - 1] more)"
