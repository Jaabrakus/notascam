// Admin controls (planning/ADMIN_PANEL_PLAN_2026-10-31.md, steps A1-A2). The owner, 10-31: "this is a mmo there is only one
// server" and "the admin is not for one player it is for me the overlord who needs to control the game from player doing
// crazy shit". So the staff are only those the game's admins.txt names (shipped with the game): the overlord ("owner"),
// and any Admins or Moderators the overlord adds in game. Hosting a world or playing alone gives nobody anything. A typed
// name can be faked, so a plain name counts only for someone playing on the server's own Mac in the app; anyone else
// only by a Discord key ("discord-<id>", from a signed sign-in link; a typed name can't hold the hyphen). Three
// levels: owner > admin > mod; nobody acts on an equal or a higher; only the owner adds or removes staff. Every command
// is checked here, on the server: the page only hides the Admin button. Every action is one line in admin-log.txt.
// A1: the Admin page (Quests: take down, hide the words, stop posting; Players: message, mute, kick, staff levels; the
// Log). A2: players' reports (a notice from its card, a player from the near card) and the Reports queue. A3: bans
// (1 day, 7 days or for good; by name, Discord key and internet address; the banned player sees the reason and the
// end), and the owner's rule "banned players turn into wanderers on the map": their people stay in the world, nobody's,
// wandering as the wild do (Restart.dm leaves a company behind the same way); after the ban they start over.
// A4: mute covers every way of talking, clan chat too (RmModMayTalk); the word list: words an Admin lists come out as
// stars wherever players write (RmModFilter: chat, unit say, emotes and messages through AntiSpam.dm Safe_Guard,
// notices, house and unit names). A listed word matches a whole word in any case; "x*" matches any word starting with
// x. Names and notices written before a word was listed keep it.

#define RM_MOD_REPORTS_HOUR 5      // reports one player may send an hour
#define RM_MOD_LOG_KEEP 200        // log lines the page can show (the file keeps them all)
#define RM_MOD_REPORTS_KEEP 300    // reports kept (closed ones go first)
#define RM_MOD_WORDS_MAX 300       // words on the list

var/list/rm_mod_staff = list()         // saved: staff id (RmModIdOf) -> list("level"="admin"/"mod", "by", "at")
var/list/rm_mod_mutes = list()         // saved: staff id -> list("until"=list(day, tenths) or null for until lifted, "by", "why")
var/list/rm_mod_postbans = list()      // saved: the same, for posting notices
var/list/rm_mod_reports = list()       // saved: report records, oldest first
var/rm_mod_report_serial = 0           // saved
var/list/rm_mod_bans = list()          // saved: staff id -> list("key", "until" (null: for good), "by", "why", "addr", "at")
var/list/rm_mod_addr = list()          // saved: staff id -> the internet address of their last log-in from elsewhere
var/list/rm_mod_wander_due = list()    // saved: staff id -> 1: banned while their people weren't in the world; done at their next log-in
var/list/rm_mod_words = list()         // saved: the word list (A4), lower case; "x*" for words starting with x
var/list/rm_mod_log                    // the log's last lines (admin-log.txt read once, then kept as written)
var/list/rm_mod_file_staff = list()    // admins.txt: key -> level, read again every minute
var/rm_mod_file_at = -1e9
var/rm_mod_ver = 0                     // moves with every change: the page's kept answer
var/rm_mod_looping = 0
var/list/rm_mod_sent = list()          // reporter key -> world.times of this hour's reports; "key|target" -> day reported
var/list/rm_mod_reasons = list("rude"="Rude words", "scam"="Scam or false notice", "grief"="Griefing", "cheat"="Cheating", "other"="Other")
var/list/rm_mod_rank = list("owner"=3, "admin"=2, "mod"=1)

Player/var/tmp
	rm_mod_view = "quests"
	rm_mod_ban_shown        // turned away at log-in: the text their page shows (RmModBanGate, RmModFullGate)
	rm_mod_full_shown       // ... because the world was full: the page's card says so instead of Banned
	rm_mod_level
	rm_mod_level_key
	rm_mod_page_key
	list/rm_mod_page

// --- who is staff ---------------------------------------------------------------------------------------------------------
// The id staff lists compare: "discord-<id>" as it is (lowercase; ckey would drop the hyphen and let a typed "discord123"
// match), any other key without a host part ("localhost@kiwimango" -> "kiwimango"), as a ckey.
proc/RmModIdOf(k)
	k = lowertext(trimtext("[k]"))
	if(copytext(k, 1, 9) == "discord-") return k
	var/at = findtext(k, "@")
	if(at) k = copytext(k, at + 1)
	return ckey(k)

// May this player be matched by name at all? Yes on the server's own Mac in the app, with a Discord key, or with no
// client (tests, a player away: only ever looked at to protect them).
Player/proc/RmModTrusted()
	if(!client) return 1
	if(copytext(lowertext(key), 1, 9) == "discord-") return 1
	return client.connection != "web" && RemasterLocalAddress(client.address)

// admins.txt (shipped with the game): one name a line, after "owner", "admin" or "mod" (a bare name is an Admin);
// # starts a note. Players who came through a Discord link are "discord-<id>".
proc/RmModFileStaff()
	if(world.time - rm_mod_file_at < 600) return rm_mod_file_staff
	rm_mod_file_at = world.time
	var/list/L = list()
	if(fexists("admins.txt"))
		for(var/line in splittext(file2text("admins.txt"), "\n"))
			line = trimtext(line)
			if(!length(line) || copytext(line, 1, 2) == "#") continue
			var/level = "admin"
			var/sp = findtext(line, " ")
			if(sp && (copytext(line, 1, sp) in list("owner", "admin", "mod")))
				level = copytext(line, 1, sp)
				line = trimtext(copytext(line, sp + 1))
			if(length(line)) L[RmModIdOf(line)] = level
	rm_mod_file_staff = L
	return L

// The level of a key that may not be online: admins.txt and the staff the owner added.
proc/RmModKeyLevel(key)
	if(!key) return ""
	var/list/F = RmModFileStaff()
	var/best = F[RmModIdOf(key)] || ""
	var/list/S = rm_mod_staff[RmModIdOf(key)]
	if(S && rm_mod_rank[S["level"]] > (rm_mod_rank[best] || 0)) best = S["level"]
	return best

// This player's level: "owner", "admin", "mod" or "" (kept a minute, or until the staff changes). A name typed in a
// browser is never matched (RmModTrusted).
Player/proc/RmModLevel()
	var/k = "[rm_mod_ver]|[round(world.time / 600)]|[client ? 1 : 0]"
	if(k == rm_mod_level_key) return rm_mod_level
	rm_mod_level_key = k
	rm_mod_level = RmModTrusted() ? RmModKeyLevel(key) : ""
	return rm_mod_level

// A player by key, compared as staff ids (RmModIdOf; the lists here are keyed by them).
proc/RmModPlayer(key)
	var/ck = RmModIdOf(key)
	for(var/Player/P in world) if(P.key && RmModIdOf(P.key) == ck) return P
	return null

proc/RmModRank(level)
	return rm_mod_rank[level] || 0

// May P do act on the player with this key? Nobody acts on an equal or a higher; only the owner changes the staff.
Player/proc/RmModMay(act, target)
	var/me = RmModRank(RmModLevel())
	if(!me) return 0
	if(target && RmModIdOf(target) != RmModIdOf(key))
		var/Player/T = RmModPlayer(target)
		var/them = RmModRank(T ? T.RmModLevel() : RmModKeyLevel(target))
		if(them >= me)
			RemasterNotice("You can't do that to someone of your own level or higher.")
			return 0
	switch(act)
		if("staff")
			if(me < 3)
				RemasterNotice("Only the owner adds or removes staff.")
				return 0
		if("forever", "words", "restart", "bugs")   // bugs: Confirmed and Fixed (Bugs.dm)
			if(me < 2)
				RemasterNotice("Only an Admin may do that.")
				return 0
	return 1

// --- time ----------------------------------------------------------------------------------------------------------------
proc/RmModLater(hours)
	var/list/N = RemasterNow()
	var/t = N[2] + round(hours * 36000)
	return list(N[1] + round(t / 864000), t % 864000)

proc/RmModActive(list/E)
	if(!E) return 0
	if(!E["until"]) return 1
	return !RmQuestOver(E["until"])

proc/RmModUntilText(list/E)
	if(!E) return ""
	if(!E["until"]) return "until lifted"
	return RmQuestLeftText(E["until"])

proc/RmModNowText()
	var/t = world.timeofday
	var/h = round(t / 36000)
	var/m = round((t % 36000) / 600)
	return "[time2text(0, "YYYY-MM-DD", 0)] [h < 10 ? "0" : ""][h]:[m < 10 ? "0" : ""][m] UTC"

// --- the log -------------------------------------------------------------------------------------------------------------
proc/RmModLogLines()
	if(rm_mod_log) return rm_mod_log
	rm_mod_log = list()
	if(fexists("admin-log.txt"))
		var/list/all = list()
		for(var/line in splittext(file2text("admin-log.txt"), "\n"))   // the engine writes a line as line + CR LF
			line = trimtext(line)
			if(length(line)) all += line
		for(var/i = max(1, length(all) - RM_MOD_LOG_KEEP + 1), i <= length(all), i++) rm_mod_log += all[i]
	return rm_mod_log

Player/proc/RmModLog(act, target, why)
	RmModLogAs("[key] ([RmModLevel()])", act, target, why)

// One line in admin-log.txt for who did it (a player's key and level, or "the server").
proc/RmModLogAs(who, act, target, why)
	var/line = "[RmModNowText()] | [who] | [act] | [target] | [RmQuestText(why, 200)]"
	var/list/L = RmModLogLines()   // read before writing, so the file's first line isn't kept twice
	text2file(line, "admin-log.txt")   // text2file adds to the file, with its own line break
	L += line
	if(length(L) > RM_MOD_LOG_KEEP) L.Cut(1, 2)
	rm_mod_ver++

// --- mutes and posting bans ------------------------------------------------------------------------------------------------
proc/RmModMuted(key)
	var/list/E = rm_mod_mutes[RmModIdOf(key)]
	return RmModActive(E)

proc/RmModPostBanned(key)
	var/list/E = rm_mod_postbans[RmModIdOf(key)]
	return RmModActive(E)

// Whether M may talk now (A4: ClanChat asks it; WorldSay, Emote, UnitSay and SendMSG read the Muted flag it agrees with).
proc/RmModMayTalk(mob/M)
	if(!M || !(M.Muted || (M.key && RmModMuted(M.key)))) return 1
	M << "You are muted."
	return 0

// --- the word list (A4) -------------------------------------------------------------------------------------------------
// t with every listed word as stars. A quick look first: most text has none of them.
proc/RmModFilter(t)
	if(!length(rm_mod_words) || isnull(t)) return t
	t = "[t]"
	var/hit = 0
	for(var/w in rm_mod_words) if(findtext(t, RmModWordStem(w)))
		hit = 1
		break
	if(!hit) return t
	var/out = ""
	var/word = ""
	var/n = length(t)
	for(var/i = 1, i <= n, i++)
		var/c = copytext(t, i, i + 1)
		if(RmModWordChar(c))
			word += c
			continue
		if(length(word))
			out += RmModWordOut(word)
			word = ""
		out += c
	if(length(word)) out += RmModWordOut(word)
	return out

proc/RmModWordStem(w)
	return copytext(w, length(w)) == "*" ? copytext(w, 1, length(w)) : w

// Letters and digits make words (accented letters too); anything else ends one.
proc/RmModWordChar(c)
	var/a = text2ascii(c)
	return (a >= 48 && a <= 57) || (a >= 65 && a <= 90) || (a >= 97 && a <= 122) || a >= 192

proc/RmModWordOut(word)
	var/lw = lowertext(word)
	var/bad = rm_mod_words.Find(lw)
	if(!bad) for(var/w in rm_mod_words) if(copytext(w, length(w)) == "*")
		var/s = copytext(w, 1, length(w))
		if(copytext(lw, 1, length(s) + 1) == s)
			bad = 1
			break
	if(!bad) return word
	var/stars = ""
	for(var/i = 1, i <= length(word), i++) stars += "*"
	return stars

// A word as the list keeps it: lower case, letters and digits, an optional "*" at the end; null if it isn't one.
proc/RmModWordNorm(w)
	w = lowertext(trimtext("[w]"))
	var/star = copytext(w, length(w)) == "*"
	if(star) w = copytext(w, 1, length(w))
	if(length(w) < 2 || length(w) > 30) return null
	for(var/i = 1, i <= length(w), i++) if(!RmModWordChar(copytext(w, i, i + 1))) return null
	return star ? "[w]*" : w

// The old chat verbs (WorldSay, Emote, UnitSay, SendMSG) read the player's Muted flag.
proc/RmModApplyMute(key)
	var/Player/P = RmModPlayer(key)
	if(P) P.Muted = RmModMuted(key) ? 1 : 0

Player/proc/RmModOnLogin()
	if(client && client.address && !RemasterLocalAddress(client.address)) rm_mod_addr[RmModIdOf(key)] = client.address
	if(rm_mod_wander_due[RmModIdOf(key)])   // banned while away: their people go now, and they start over
		rm_mod_wander_due -= RmModIdOf(key)
		RmModWanderers(src)
	Muted = RmModMuted(key) ? 1 : 0
	if(Muted) RemasterNotice("You are muted ([RmModUntilText(rm_mod_mutes[RmModIdOf(key)])]).")
	var/left = RmModRestartLeft()
	if(left > 0) RemasterNotice(RmModRestartText(left))   // a restart notice running
	RmBugOnLogin()   // their reports fixed while they were away (Bugs.dm)

// Every minute: mutes and posting bans whose time is up are lifted.
proc/RmModLoop()
	if(rm_mod_looping) return
	rm_mod_looping = 1
	while(1)
		sleep(600)
		RmModTick()

proc/RmModTick()
	for(var/list/L in list(rm_mod_mutes, rm_mod_postbans, rm_mod_bans))
		var/list/gone = list()
		for(var/k in L) if(!RmModActive(L[k])) gone += k
		for(var/k in gone)
			L -= k
			if(L == rm_mod_mutes) RmModApplyMute(k)
		if(length(gone)) rm_mod_ver++

// --- saving (WorldSave.dm) ----------------------------------------------------------------------------------------------------
proc/RmModSaveData()
	return json_encode(list("version"=1, "staff"=rm_mod_staff, "mutes"=rm_mod_mutes, "postbans"=rm_mod_postbans, "reports"=rm_mod_reports, "serial"=rm_mod_report_serial, "bans"=rm_mod_bans, "addr"=rm_mod_addr, "wanderDue"=rm_mod_wander_due, "words"=rm_mod_words))

proc/RmModLoadData(D)
	if(istext(D))
		try
			D = json_decode(D)
		catch
			D = null
			world.log << "Remastered: the saved admin data could not be read"
	if(islist(D))
		if(islist(D["staff"])) rm_mod_staff = D["staff"]
		if(islist(D["mutes"])) rm_mod_mutes = D["mutes"]
		if(islist(D["postbans"])) rm_mod_postbans = D["postbans"]
		if(islist(D["reports"])) rm_mod_reports = D["reports"]
		if(isnum(D["serial"])) rm_mod_report_serial = D["serial"]
		if(islist(D["bans"])) rm_mod_bans = D["bans"]
		if(islist(D["addr"])) rm_mod_addr = D["addr"]
		if(islist(D["wanderDue"])) rm_mod_wander_due = D["wanderDue"]
		if(islist(D["words"])) rm_mod_words = D["words"]
	rm_mod_ver++
	spawn(0) RmModLoop()
	spawn(0) RmModRestartFileLoop()   // a published update's countdown (tools/public_host.py)

// --- bans (A3) ----------------------------------------------------------------------------------------------------------
// The ban that keeps this player out: by their id, or by the internet address they come from (never a local one: the
// server's own Mac).
proc/RmModBanOf(key, addr)
	var/list/E = rm_mod_bans[RmModIdOf(key)]
	if(RmModActive(E)) return E
	if(addr && !RemasterLocalAddress(addr)) for(var/id in rm_mod_bans)
		var/list/B = rm_mod_bans[id]
		if(B["addr"] == addr && RmModActive(B)) return B
	return null

proc/RmModBanText(list/E)
	return "You are banned from this world [E["until"] ? "([RmModUntilText(E)])" : "for good"][length(E["why"]) ? ": [E["why"]]" : "."]"

// Player/Login's first step (Joining.dm): a banned player is told why and until when, and goes, before anything of
// theirs loads.
Player/proc/RmModBanGate()
	if(!client) return 0
	var/list/E = RmModBanOf(key, client.address)
	if(!E) return 0
	src << "<b>[RmModBanText(E)]</b>"
	world.log << "Join refused (banned) for [key] from [client.address]"
	// they see why on the game's own page: it is sent as for anyone, and once it says it is ready (HUD.dm "ready") it
	// shows a Banned card; then they go. Nothing of theirs has loaded.
	rm_mod_ban_shown = RmModBanText(E)
	src << browse(RmHudPackPage(RemasterHUDPage(src)), "window=mapwindow.hud")
	var/client/C = client
	spawn(150) if(C) del(C)   // whatever the page does, they go
	return 1

// The page of a player turned away is ready: the Banned card, then the door.
Player/proc/RmModBanShow()
	src << output(url_encode(rm_mod_ban_shown), "mapwindow.hud:[rm_mod_full_shown ? "rmFull" : "rmBanned"]")
	var/client/C = client
	spawn(60) if(C) del(C)

// The owner's rule: a banned player's people become wanderers. They stay where they are, nobody's, and wander as the
// wild do (RandomWalk: they roam, fight back, take gear, may be captured); orders, jobs and plans go, and so does the
// house name before theirs. As Restart.dm leaves a company behind (its caged ones dropped, its own work cleared).
proc/RmModWanderers(Player/P)
	if(!P) return 0
	. = 0
	for(var/mob/Monsters/M in P.Selected) M.Deselect(P)
	for(var/mob/Monsters/M in P.UnitList.Copy()) if(M.Owner == P && !M.Wagon)
		for(var/obj/Items/I in M) if(I.Content3 == "Cage") M.ForceDropItem(I)
		M.destination = null
		M.remaster_orders = list()
		M.remaster_active = null
		M.remaster_job = "manual"
		var/b = findtext(M.name, "} ")
		if(copytext(M.name, 1, 2) == "{" && b) M.name = copytext(M.name, b + 2)
		M.CanBeSlaved = 1
		M.ChangeOwnership(null, 1)
		spawn(rand(1, 20)) if(M && M.HP > 0) M.RandomWalk()
		.++
	P.UnitList = list()
	P.Selected = list()
	P.RmStartOverWork()   // their zones, rows, plans and stores go with them (Restart.dm)
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		if(RmModIdOf(Q["maker"]) == RmModIdOf(P.key)) RmQuestEnd(Q, "its maker was banned")

// --- reports from players (A2) ------------------------------------------------------------------------------------------------
// value: "quest|<id>|<reason>|<note>" (a notice, from its card) or "unit|<\ref>|<reason>|<note>" (a player, by one of
// their people in the near card). A copy of what was reported is kept with the report.
Player/proc/RmModReport(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 3) return 0
	var/reason = p[3]
	if(!rm_mod_reasons[reason]) return 0
	var/note = length(p) >= 4 ? RmQuestText(p[4], 200) : ""
	var/target
	var/list/copy
	if(p[1] == "quest")
		var/list/Q = rm_quests[p[2]]
		if(!Q || Q["maker"] == key) return 0
		target = Q["maker"]
		copy = list("quest"=Q["id"], "title"=Q["title"], "text"=Q["text"], "reward"=RmQuestRewardText(Q), "house"=Q["house"], "state"=Q["state"])
	else if(p[1] == "unit")
		var/mob/Monsters/M = locate(p[2])
		if(!istype(M) || !istype(M.Owner, /Player) || M.Owner == src) return 0
		var/Player/O = M.Owner
		target = O.key
		copy = list("unit"=M.RemasterBareName(), "race"="[M.Race]", "house"=O.RemasterHouse(), "x"=M.x, "y"=M.y, "z"=M.z)
		if(M.rm_keeper) copy["keeper"] = list("words"=M.rm_keeper["words"], "topics"=M.rm_keeper["topics"])   // a keeper's words (QuestKeepers.dm)
	else return 0
	// at most RM_MOD_REPORTS_HOUR an hour, and one a day for the same target
	var/list/sent = rm_mod_sent[RmModIdOf(key)]
	if(!sent) sent = rm_mod_sent[RmModIdOf(key)] = list()
	for(var/i = length(sent), i >= 1, i--) if(world.time - sent[i] > 36000) sent.Cut(i, i + 1)
	if(length(sent) >= RM_MOD_REPORTS_HOUR)
		RemasterNotice("You have sent [RM_MOD_REPORTS_HOUR] reports this hour. The admins will look at them.")
		return 0
	var/list/N = RemasterNow()
	var/tk = "[RmModIdOf(key)]|[p[1] == "quest" ? p[2] : RmModIdOf(target)]"
	if(rm_mod_sent[tk] == N[1])
		RemasterNotice("You have reported that today already.")
		return 0
	rm_mod_sent[tk] = N[1]
	sent += world.time
	var/list/R = list("id"="r[++rm_mod_report_serial]", "at"=RmModNowText(), "by"=key, "byHouse"=RemasterHouse(), "kind"=p[1],
		"target"=target, "reason"=reason, "note"=note, "copy"=copy, "state"="open")
	rm_mod_reports += list(R)
	if(length(rm_mod_reports) > RM_MOD_REPORTS_KEEP)
		var/drop = 1
		for(var/i = 1, i <= length(rm_mod_reports), i++) if(rm_mod_reports[i]["state"] != "open")
			drop = i
			break
		rm_mod_reports.Cut(drop, drop + 1)
	rm_mod_ver++
	RemasterNotice("Thank you. Your report went to the admins.")
	return 1

proc/RmModReportCount(target, open = 1)
	. = 0
	var/ck = RmModIdOf(target)
	for(var/list/R in rm_mod_reports) if(RmModIdOf(R["target"]) == ck && (!open || R["state"] == "open")) .++

// --- the Admin page's commands (A1) ---------------------------------------------------------------------------------------------
// value: "view|<tab>", "qdown|<id>|<why>", "qhide|<id>|<why>", "postban|<key>|<days: 0 lifts, -1 until lifted>|<why>",
// "msg|<key>|<text>", "mute|<key>|<hours: 0 lifts, -1 until lifted>|<why>", "kick|<key>|<why>",
// "level|<key>|<mod/admin/none>|<why>", "rclose|<id>|<note>".
Player/proc/RmModCommand(value)
	if(!RmModLevel()) return 0
	var/list/p = splittext("[value]", "|")
	var/act = p[1]
	var/a = length(p) >= 2 ? p[2] : ""
	var/b = length(p) >= 3 ? p[3] : ""
	var/c = length(p) >= 4 ? p[4] : ""
	var/ca = RmModIdOf(a)   // a player key: the lists are keyed by staff ids
	switch(act)
		if("view")
			if(a in list("quests", "players", "reports", "log", "words", "bugs")) rm_mod_view = a
			rm_mod_page_key = null
		if("bugset")    // a bug row's state, the reason box its note (Bugs.dm)
			if(!RmBugSet(a, b, c)) return 0
		if("bugopen")   // a bug row's details shown or hidden
			rm_mod_bug_open = rm_mod_bug_open == a ? null : a
			rm_mod_page_key = null
		if("qdown")
			var/list/Q = rm_quests[a]
			if(!Q || !RmModMay("qdown", Q["maker"])) return 0
			if(RmQuestEnd(Q, "taken down by an admin"))
				RmModLog("took down a notice", "[Q["maker"]]: [Q["title"]]", b)
				RemasterNotice("Taken down: [Q["title"]]. Its reward went back to its maker.")
		if("qhide")
			var/list/Q = rm_quests[a]
			if(!Q || !RmModMay("qhide", Q["maker"])) return 0
			Q["hidden"] = !Q["hidden"]
			RmQuestChanged()
			RmModLog(Q["hidden"] ? "hid a notice's words" : "showed a notice's words", "[Q["maker"]]: [Q["title"]]", b)
		if("postban")
			var/days = text2num(b)
			if(!(days in list(0, 1, 7, -1)) || !RmModMay(days == -1 ? "forever" : "postban", a)) return 0
			if(!days) rm_mod_postbans -= ca
			else rm_mod_postbans[ca] = list("until"=(days > 0 ? RmModLater(days * 24) : null), "by"=key, "why"=RmQuestText(c, 200))
			RmModLog(days ? "stopped posting ([days > 0 ? "[days] day[days > 1 ? "s" : ""]" : "until lifted"])" : "let post again", a, c)
			var/Player/T = RmModPlayer(a)
			if(T) T.RemasterNotice(days ? "An admin stopped you posting notices ([RmModUntilText(rm_mod_postbans[ca])])." : "You may post notices again.")
		if("msg")
			var/text = RmQuestText(b, 300)
			var/Player/T = RmModPlayer(a)
			if(!T || !length(text) || !RmModMay("msg", null)) return 0
			T.RemasterNotice("From an admin: [text]")
			T.RemasterLog("From an admin: [text]", "info", null)
			RmModLog("sent a message", a, text)
		if("mute")
			var/hours = text2num(b)
			if(!(hours in list(0, 1, 24, 168, -1)) || !RmModMay(hours == -1 ? "forever" : "mute", a)) return 0
			if(!hours) rm_mod_mutes -= ca
			else rm_mod_mutes[ca] = list("until"=(hours > 0 ? RmModLater(hours) : null), "by"=key, "why"=RmQuestText(c, 200))
			RmModApplyMute(a)
			RmModLog(hours ? "muted ([hours > 0 ? (hours < 24 ? "[hours] hour" : "[hours / 24] day[hours > 24 ? "s" : ""]") : "until lifted"])" : "unmuted", a, c)
			var/Player/T = RmModPlayer(a)
			if(T) T.RemasterNotice(hours ? "An admin muted you ([RmModUntilText(rm_mod_mutes[ca])])." : "You are no longer muted.")
		if("ban")
			var/days = text2num(b)
			if(!(days in list(1, 7, -1)) || !RmModMay(days == -1 ? "forever" : "ban", a)) return 0
			var/Player/T = RmModPlayer(a)
			var/addr = (T && T.client && !RemasterLocalAddress(T.client.address)) ? T.client.address : rm_mod_addr[ca]
			rm_mod_bans[ca] = list("key"=a, "until"=(days > 0 ? RmModLater(days * 24) : null), "by"=key, "why"=RmQuestText(c, 200), "addr"=addr, "at"=RmModNowText())
			var/n = 0
			if(T) n = RmModWanderers(T)
			else rm_mod_wander_due[ca] = 1
			RmModLog("banned ([days > 0 ? "[days] day[days > 1 ? "s" : ""]" : "for good"]; [T ? "[n] of their people now wander" : "their people wander when they next come"])", a, c)
			if(T && T.client)
				T << "<b>[RmModBanText(rm_mod_bans[ca])]</b>"
				var/client/C = T.client
				spawn(10) if(C) del(C)
			RemasterNotice("[a] is banned[T ? ": [n] of their people now wander the map" : ""].")
		if("unban")
			if(!rm_mod_bans[ca] || !RmModMay("ban", a)) return 0
			rm_mod_bans -= ca
			rm_mod_ver++
			RmModLog("unbanned", a, c)
			RemasterNotice("[a] may come back. Their old people stay wanderers: they start over.")
		if("kick")
			var/Player/T = RmModPlayer(a)
			if(!T || !T.client || !RmModMay("kick", a)) return 0
			RmModLog("kicked", a, b)
			T << "<b>An admin disconnected you[length(b) ? ": [RmQuestText(b, 200)]" : ""].</b>"
			var/client/C = T.client
			spawn(5) if(C) del(C)
		if("level")
			if(!(b in list("mod", "admin", "none")) || !RmModMay("staff", a)) return 0
			if(b == "none") rm_mod_staff -= ca
			else rm_mod_staff[ca] = list("level"=b, "by"=key, "at"=RmModNowText())
			rm_mod_ver++
			RmModLog(b == "none" ? "removed from the staff" : "made [b == "mod" ? "a Moderator" : "an Admin"]", a, c)
			var/Player/T = RmModPlayer(a)
			if(T) T.RemasterNotice(b == "none" ? "You are no longer on the admin staff." : "You are now [b == "mod" ? "a Moderator" : "an Admin"]: the Admin button is on your menu.")
		if("wordadd")   // the word list (A4): Admins only
			var/w = RmModWordNorm(a)
			if(!RmModMay("words", null)) return 0
			if(!w)
				RemasterNotice("A listed word is 2 to 30 letters or digits, with an optional * at the end for every word starting with it.")
				return 0
			if(w in rm_mod_words) return 0
			if(length(rm_mod_words) >= RM_MOD_WORDS_MAX)
				RemasterNotice("The list is full ([RM_MOD_WORDS_MAX] words).")
				return 0
			rm_mod_words += w
			rm_mod_ver++
			RmModLog("listed a word", w, b)
		if("worddel")
			if(!(a in rm_mod_words) || !RmModMay("words", null)) return 0
			rm_mod_words -= a
			rm_mod_ver++
			RmModLog("took a word off the list", a, b)
		if("rclose")
			for(var/list/R in rm_mod_reports) if(R["id"] == a && R["state"] == "open")
				R["state"] = "closed"
				R["closedBy"] = key
				R["closeNote"] = RmQuestText(b, 200)
				rm_mod_ver++
				RmModLog("closed a report", "[R["id"]] on [R["target"]]", b)
		if("restart")   // the restart notice: minutes, or 0 to call it off; Admins only
			var/mins = text2num(a)
			if(!(mins in list(0, 1, 2, 5, 10, 15, 30)) || !RmModMay("restart", null)) return 0
			if(!mins)
				if(!rm_mod_restart) return 0
				rm_mod_restart = null
				rm_mod_ver++
				RmModLog("called off the restart", "the world", b)
				RmModRestartSay("The restart is called off: the world goes on.")
				return 1
			RmModRestartStart(mins, b, key)
			RmModLog("announced a restart in [mins] minute[mins > 1 ? "s" : ""]", "the world", b)
	return 1

// --- the restart notice (the owner, 11-01: "a button for me the admin ... to insert a world restart notification") -------
// An Admin picks how many minutes from now; every player online is told at once, again at 10, 5, 2 and 1 minutes and
// 30 seconds left, and "now" at the end; anyone logging in meanwhile is told what is left. It only warns: the restart
// itself is the server's (Banners Server.app, or a published update). Real time (RemasterNow), not the game's clock.
var/list/rm_mod_restart                 // the notice running: start, mins, why, by, said (marks given), serial
var/rm_mod_restart_serial = 0
var/list/rm_mod_restart_marks = list(600, 300, 120, 60, 30)   // seconds left when it is said again

// Seconds left of the notice running, or null.
proc/RmModRestartLeft()
	if(!rm_mod_restart) return null
	return rm_mod_restart["mins"] * 60 - round((RemasterSince(rm_mod_restart["start"]) || 0) / 10)

proc/RmModRestartText(left)
	var/when = left >= 90 ? "in [round(left / 60 + 0.5)] minutes" : left >= 60 ? "in 1 minute" : left > 0 ? "in [max(1, round(left))] seconds" : "now"
	var/why = rm_mod_restart ? rm_mod_restart["why"] : ""
	if(length(why) && !(copytext(why, -1) in list(".", "!", "?"))) why += "."
	return "The world restarts [when][length(why) ? ": [why]" : "."] Everything is saved; come back a minute after."

proc/RmModRestartStart(mins, why, by)
	rm_mod_restart = list("start"=RemasterNow(), "mins"=mins, "why"=RmQuestText(why, 200), "by"=by, "said"=list(), "serial"=++rm_mod_restart_serial)
	rm_mod_ver++
	RmModRestartSay(RmModRestartText(mins * 60))
	spawn(0) RmModRestartLoop(rm_mod_restart_serial)

// A published update (the owner, 11-01: "publish it in the game and add a countdown to people playing"): the public server
// (tools/public_host.py run) writes restart-notice ("minutes|reason") beside the world; the notice runs as an Admin's
// would, from "the server", and the update goes in when it ends. Looked for every 5 s; the file goes once read.
var/rm_mod_restart_watching = 0
proc/RmModRestartFileLoop()
	if(rm_mod_restart_watching) return
	rm_mod_restart_watching = 1
	while(1)
		sleep(50)
		if(!fexists("restart-notice")) continue
		var/list/p = splittext(trimtext(file2text("restart-notice")), "|")
		fdel("restart-notice")
		var/mins = length(p) ? text2num(p[1]) : 0
		if(!(mins in list(1, 2, 3, 5, 10, 15, 30))) continue
		RmModRestartStart(mins, length(p) > 1 ? p[2] : "An update is going in", "the server")
		RmModLogAs("the server", "announced a restart in [mins] minute[mins > 1 ? "s" : ""] (an update)", "the world", length(p) > 1 ? p[2] : "")

proc/RmModRestartSay(text)
	for(var/Player/P in world) if(P.client)
		P.RemasterNotice(text)
		P.RemasterLog(text, "info", null)
		P << "<b>[text]</b>"

proc/RmModRestartLoop(serial)
	while(rm_mod_restart && rm_mod_restart["serial"] == serial)
		sleep(20)
		if(!rm_mod_restart || rm_mod_restart["serial"] != serial) return
		var/left = RmModRestartLeft()
		if(left <= 0)
			RmModRestartSay(RmModRestartText(0))
			rm_mod_restart = null
			rm_mod_ver++
			return
		var/list/said = rm_mod_restart["said"]
		var/mark = 0
		for(var/m in rm_mod_restart_marks) if(left <= m && m < rm_mod_restart["mins"] * 60 && !("[m]" in said)) mark = m
		if(mark)
			for(var/m in rm_mod_restart_marks) if(m >= mark) said |= "[m]"   // a later mark covers the ones skipped
			RmModRestartSay(RmModRestartText(left))

// --- the player cap (the owner, 11-01: 30 at once on the public server until a test shows the Mac takes more) ------------
// RM_PLAYER_MAX in the server's environment (0: no cap); 30 on a public server without it, none elsewhere. Staff always
// come in; anyone already in stays. The turned-away see a "world is full" card, as the banned see theirs.
var/rm_mod_player_max = -1              // -1: read from the environment once
proc/RmModPlayerMax()
	if(rm_mod_player_max < 0)
		var/n = text2num(world.GetConfig("env", "RM_PLAYER_MAX"))
		rm_mod_player_max = isnum(n) ? max(0, n) : (RmPublicWorld() ? 30 : 0)
	return rm_mod_player_max

// Would one more player with this key be turned away, with this many others online?
proc/RmModFull(key, online)
	var/cap = RmModPlayerMax()
	return cap && online >= cap && !RmModKeyLevel(key)

// Players online, for the top bar (the owner, 11-01: "show a status of how many people are online"): on a public or
// hosted world only, counted at most every 5 s for everyone.
var/rm_online_n = 0                    // players at the last count; 0 when the world is neither public nor hosted
var/rm_online_counted = -1000000       // world.time of the last count
proc/RmOnlineData()
	if(world.time >= rm_online_counted + 50)
		rm_online_counted = world.time
		var/n = 0
		if(RmPublicWorld() || fexists("host-addresses"))
			for(var/Player/P in world) if(P.client) n++
		rm_online_n = n
	return rm_online_n ? list("n"=rm_online_n, "max"=RmModPlayerMax()) : null

// Player/Login's second step (Joining.dm), after the ban gate.
Player/proc/RmModFullGate()
	if(!client) return 0
	var/online = 0
	for(var/Player/P in world) if(P != src && P.client) online++
	if(!RmModFull(key, online)) return 0
	world.log << "Join refused (world full, [online] online) for [key] from [client.address]"
	rm_mod_ban_shown = "The world is full right now ([online] playing). Try again in a little while."
	rm_mod_full_shown = 1
	src << browse(RmHudPackPage(RemasterHUDPage(src)), "window=mapwindow.hud")
	var/client/C = client
	spawn(150) if(C) del(C)
	return 1

// --- what the page is sent ------------------------------------------------------------------------------------------------------
// Staff only: their level and the open reports, and the page while it is open (built again only on a change, or once a
// minute for the times).
Player/proc/RmModHudData()
	var/level = RmModLevel()
	if(!level) return null
	var/open = 0
	for(var/list/R in rm_mod_reports) if(R["state"] == "open") open++
	var/list/D = list("level"=level, "open"=open, "view"=rm_mod_view)
	if(RmBugsOn()) D["bugsNew"] = RmBugNew()   // the Bugs tab's count (Bugs.dm)
	var/left = RmModRestartLeft()
	if(left > 0) D["restart"] = list("left"=left, "why"=rm_mod_restart["why"], "by"=rm_mod_restart["by"])
	if(remaster_hud_tab == "admin")
		var/online = 0
		for(var/client/C) online++
		var/k = "[rm_mod_ver]|[rm_quest_ver]|[rm_mod_view]|[round(world.time / 600)]|[online]|[rm_mod_bug_open]"
		if(k != rm_mod_page_key)
			rm_mod_page_key = k
			rm_mod_page = RmModPageData()
		D["page"] = rm_mod_page
	return D

Player/proc/RmModPageData()
	switch(rm_mod_view)
		if("quests")
			var/list/L = list()
			var/list/ids = list()
			for(var/id in rm_quests) ids.Insert(1, id)   // newest first
			for(var/id in ids)
				if(length(L) >= 300) break
				var/list/Q = rm_quests[id]
				var/list/B = Q["board"]
				L += list(list("id"=id, "title"=Q["title"], "maker"=Q["maker"], "house"=Q["house"], "state"=Q["state"],
					"reward"=RmQuestRewardText(Q), "goal"=(Q["goal"] || "[Q["need"]] [Q["itemName"]]"), "takers"=length(Q["takers"]),
					"hidden"=!!Q["hidden"], "text"=Q["text"], "reports"=RmModReportCount(Q["maker"]), "left"=RmQuestLeftText(Q["ends"]),
					"postban"=RmModUntilText(rm_mod_postbans[RmModIdOf(Q["maker"])]), "x"=B[1], "y"=B[2], "z"=B[3]))
			return list("quests"=L)
		if("players")
			return list("players"=RmModPlayers())
		if("reports")
			var/list/L = list()
			for(var/i = length(rm_mod_reports), i >= 1 && length(L) < 150, i--) L += list(rm_mod_reports[i])
			// open ones first
			var/list/O = list()
			for(var/list/R in L) if(R["state"] == "open") O += list(R)
			for(var/list/R in L) if(R["state"] != "open") O += list(R)
			return list("reports"=O, "reasons"=rm_mod_reasons)
		if("log")
			var/list/L = RmModLogLines()
			var/list/out = list()
			for(var/i = length(L), i >= 1 && length(out) < 150, i--) out += L[i]
			return list("log"=out)
		if("words")
			return list("words"=rm_mod_words.Copy(), "max"=RM_MOD_WORDS_MAX)   // the page sorts them
		if("bugs")
			return list("bugs"=RmBugPageData())   // Bugs.dm
	return null

// Everyone online, then everyone the world knows (world-info.json's companies, the staff, the muted and banned,
// notice makers and those reported).
Player/proc/RmModPlayers()
	var/list/rows = list()
	var/list/seen = list()
	for(var/client/C)
		var/Player/P = C.mob
		if(!istype(P) || !P.key || seen[RmModIdOf(P.key)]) continue
		seen[RmModIdOf(P.key)] = 1
		var/mob/Monsters/U
		var/n = 0
		for(var/mob/Monsters/M in P.UnitList) if(M.Owner == P && M.HP > 0)
			n++
			if(!U && isturf(M.loc)) U = M
		rows += list(RmModPlayerRow(P.key, P.RemasterHouse(), "[P.Race]", n, 1, U, P.RmModLevel()))
	var/list/known = list()
	if(!rm_world_info_players)
		try
			rm_world_info_players = RmWorldInfoPlayers()
		catch
			rm_world_info_players = list()
	for(var/ck in rm_world_info_players)
		var/list/E = rm_world_info_players[ck]
		if(islist(E) && E["key"]) known[E["key"]] = E
	for(var/k in rm_mod_staff) if(!known[k]) known[k] = null
	for(var/k in rm_mod_mutes) if(!known[k]) known[k] = null
	for(var/k in rm_mod_postbans) if(!known[k]) known[k] = null
	for(var/k in rm_mod_bans) if(!known[rm_mod_bans[k]["key"]]) known[rm_mod_bans[k]["key"]] = null
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		if(!known[Q["maker"]]) known[Q["maker"]] = null
	for(var/list/R in rm_mod_reports) if(R["target"] && !known[R["target"]]) known[R["target"]] = null
	for(var/k in known)
		if(seen[RmModIdOf(k)]) continue
		seen[RmModIdOf(k)] = 1
		var/list/E = known[k]
		rows += list(RmModPlayerRow(k, null, E ? E["race"] : null, E ? E["units"] : null, 0, null, RmModKeyLevel(k)))
		if(length(rows) >= 300) break
	return rows

proc/RmModPlayerRow(key, house, race, units, online, mob/Monsters/U, level)
	return list("key"=key, "house"=house, "race"=race, "units"=units, "online"=online, "level"=level,
		"discord"=(copytext(key, 1, 9) == "discord-"), "muted"=(RmModMuted(key) ? RmModUntilText(rm_mod_mutes[RmModIdOf(key)]) : null),
		"postban"=(RmModPostBanned(key) ? RmModUntilText(rm_mod_postbans[RmModIdOf(key)]) : null), "reports"=RmModReportCount(key), "banned"=(RmModBanOf(key) ? RmModUntilText(rm_mod_bans[RmModIdOf(key)]) : null),
		"x"=(U ? U.x : null), "y"=(U ? U.y : null), "z"=(U ? U.z : null))
