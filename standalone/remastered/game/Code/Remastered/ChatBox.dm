// The chat box (the owner, 11-01: "we also need a world chat box where the log is like warcraft people can toggle
// between"; World chat free for now: the crafted item or spell for World, and pigeons for private words, come later).
// The page's chat line (Enter) sends "world|words", "local|words" or "kingdom|words" (HUD.dm "chat"). Each line goes to its listeners
// as a message the page files under its Chat tab (rmChatMsg: channel, who, words), not through the plain-text route,
// so no one can make a line look like World or Kingdom by typing it. World: every player online, but those who turned
// World off (WC) or ignore the speaker. Kingdom: the speaker's realm, the realm it serves and every realm serving that
// one. Muted players can't talk (RmModMayTalk); the words lose markup, go through the word list and the spam guard
// (Safe_Guard), RM_CHAT_MAX characters at most; World waits RM_CHAT_GAP between one player's lines.
// Before Guests.dm, whose WorldSay chains on to this one.
// Local (the owner, 11-01: "we need local chat and world chat"): the players near where the speaker is looking, whose
// own view or people are within RM_CHAT_LOCAL tiles of it on the same layer, as /say is in WoW.
#define RM_CHAT_MAX 300
#define RM_CHAT_GAP 30          // ticks between one player's World lines (3 s)
#define RM_CHAT_LOCAL 40        // tiles a Local line carries

Player/var/tmp/rm_chat_last = -1000

// The name a line goes under: the house, else the leader's name; never a Discord account's number.
Player/proc/RmChatName()
	if(remaster_house) return remaster_house
	if(copytext(lowertext("[key]"), 1, 9) == "discord-")
		for(var/mob/Monsters/M in UnitList) if(M.Owner == src && !M.Critter) return M.RemasterBareName()
		return "Newcomer"
	return RemasterWho()

Player/proc/RmChatSend(value)
	var/v = "[value]"
	var/i = findtext(v, "|")
	if(!i) return 0
	var/ch = copytext(v, 1, i)
	if(!(ch in list("world", "local", "kingdom"))) return 0
	if(!length(RmQuestText(copytext(v, i + 1), RM_CHAT_MAX)) || !RmModMayTalk(src)) return 0
	if(ch == "world")
		if(world.time - rm_chat_last < RM_CHAT_GAP)
			RemasterNotice("Wait a moment before talking to the whole world again.")
			return 0
		rm_chat_last = world.time
	var/words = RmChatWords(copytext(v, i + 1))
	if(!length(words)) return 0
	var/msg = url_encode(json_encode(list("ch"=ch, "who"=RmChatName(), "text"=words)))
	for(var/Player/P in RmChatListeners(ch)) P << output(msg, "mapwindow.hud:rmChatMsg")
	return 1

// Typed words as a line: one line, no markup, RM_CHAT_MAX characters, the word list and the spam guard (which reads the
// speaker from usr, as the old chat verbs left it).
Player/proc/RmChatWords(t)
	usr = src
	return Safe_Guard(RmQuestText(t, RM_CHAT_MAX))

// Who hears a line on ch (online: only those with a client; the arena's test players have none).
Player/proc/RmChatListeners(ch, online = 1)
	. = list()
	if(ch == "world")
		for(var/Player/P in world) if((!online || P.client) && (P == src || (!P.WC && !(src in P.IgnoreList)))) . += P
		return
	if(ch == "local")
		var/turf/here = RemasterGetTurf(src)
		for(var/Player/P in world) if((!online || P.client) && (P == src || !(src in P.IgnoreList)))
			if(P == src || RmChatNear(P, here)) . += P
		return
	var/root = remaster_liege || key
	for(var/Player/P in world) if((!online || P.client) && (P.key == root || P.remaster_liege == root)) . += P

// Is P near enough to hear a Local line said looking at here: their view, or one of their people?
proc/RmChatNear(Player/P, turf/here)
	if(!here) return 0
	var/turf/T = RemasterGetTurf(P)
	if(T && T.z == here.z && get_dist(T, here) <= RM_CHAT_LOCAL) return 1
	for(var/mob/Monsters/M in P.UnitList) if(M.z == here.z && get_dist(M, here) <= RM_CHAT_LOCAL) return 1
	return 0

// The old Shout (the 2006 world chat, from the menu) goes the same way, so it lands under Chat too.
mob/WorldSay()
	if(!istype(src, /Player)) return ..()
	var/T = input("Shout") as null|text
	if(T) src:RmChatSend("world|[T]")
