// Realms between players. A new player may join an open realm (Hamlet rank or
// higher, Progress.dm) as migrants instead of founding their own land: their starting
// units arrive at the realm's edge and its ruler accepts or declines them. A whole
// settlement may also swear fealty to another realm. Members and vassals are allies:
// they may work inside each other's land (Claims.dm), attack orders never target
// them (Attack.dm), and their people count toward the realm's rank — migrants and
// vassals grow a Hamlet into a Kingdom.

var/list/rm_lieges = list()           // saved with the world: player key -> liege key

Player/var
	remaster_liege                    // saved: the key of the realm this player belongs to
Player/var/tmp
	list/remaster_requests            // key -> "join" / "fealty" (asked of this ruler)
	remaster_asked                    // key of the realm this player asked

proc/RemasterRootKey(k)
	var/n = 0
	while(k && rm_lieges[k] && n++ < 8) k = rm_lieges[k]
	return k

proc/RemasterAlliedKeys(a, b)
	if(!a || !b) return 0
	return a == b || RemasterRootKey(a) == RemasterRootKey(b)

proc/RemasterAllied(Player/A, Player/B)
	return istype(A) && istype(B) && RemasterAlliedKeys(A.key, B.key)

proc/RemasterPlayerByKey(k)
	for(var/Player/P in world) if(P.key == k) return P
	return null

// The name other players know you by: the login name (without the host part).
Player/proc/RemasterWho()
	var/k = "[key]"
	var/i = findtext(k, "@")
	return i ? copytext(k, i + 1) : (k || "[src]")

// The name a player goes by in the world: the house they named (Realm tab), or their
// login name until they do. Logins (RemasterWho) still decide who is the host.
Player/var/remaster_house          // saved
Player/proc/RemasterHouse()
	return remaster_house || RemasterWho()

// Name (or rename) the house: units' "{name}" prefix, banners and the realm follow.
Player/proc/RemasterNameHouse(v)
	v = trimtext("[v]")
	for(var/bad in list("{", "}", "\[", "]", "<", ">", "|", "\"", "\\")) v = replacetext(v, bad, "")
	v = RmModFilter(trimtext(v))   // the admins' word list (Moderation.dm, A4)
	if(length(v) < 2 || length(v) > 24)
		RemasterNotice("A house name needs 2 to 24 letters.")
		return 0
	for(var/Player/O in world) if(O != src && (lowertext(O.RemasterHouse()) == lowertext(v)))
		RemasterNotice("Another player's house is already called [v].")
		return 0
	var/old = "{[name]} "
	remaster_house = v
	name = v
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && findtextEx(M.name, old))   // a ruler's name has its title first
		M.name = replacetextEx(M.name, old, "{[v]} ")
	for(var/obj/RemasterBanner/B in RemasterBanners()) B.owner_name = v
	RemasterNotice("Your house is now called [v].")
	RemasterLog("The house took the name [v]", "good", null)
	return 1

Player/proc/RemasterRealmName()
	return "[RemasterHouse()]'s [lowertext(rm_ranks[clamp(remaster_rank, 1, length(rm_ranks))]["name"])]"

// Realms a newcomer may join: open (Hamlet+), online, with people of their own.
proc/RemasterOpenRealms(Player/except)
	. = list()
	for(var/Player/P in world) if(P != except && P.client && P.remaster_open && !P.remaster_liege && !RmGuestKey(P.key))
		var/n = 0
		for(var/mob/Monsters/M in P.UnitList) if(M.Owner == P && M.HP > 0) n++
		if(n) . += P

// Called from the race choice (Restart.dm): found new land or migrate to a realm.
// Returns the turf to arrive at, or null for the usual start.
Player/proc/RemasterMigrantChoice()
	var/list/realms = RemasterOpenRealms(src)
	if(!length(realms)) return null
	var/list/menu = list("Found my own land")
	var/list/by = list()
	for(var/Player/P in realms)
		var/label = "Join [P.RemasterRealmName()] ([length(P.UnitList)] people)"
		menu += label
		by[label] = P
	var/c = RemasterChoose(src, "Found your own land, or join a realm as migrants?", "A new arrival", menu)   // a HUD card like the race pick (AskCard.dm); Esc founds your own
	var/Player/R = by[c]
	if(!R) return null
	var/turf/S = R.RemasterStockpile() || R.RemasterProgressCenter()
	if(!S) return null
	RemasterAskRealm(R, "join")
	// arrive at the edge and walk in, like migrants
	for(var/tries = 0, tries < 40, tries++)
		var/a = rand(0, 359)
		var/turf/T = locate(clamp(round(S.x + cos(a) * 18), 2, world.maxx - 1), clamp(round(S.y + sin(a) * 18), 2, world.maxy - 1), S.z)
		if(T && !T.density) return T
	return S

Player/proc/RemasterAskRealm(Player/R, kind)
	if(!istype(R) || R == src) return 0
	if(!R.remaster_requests) R.remaster_requests = list()
	R.remaster_requests[key] = kind
	remaster_asked = R.key
	var/text = kind == "join" ? "[RemasterHouse()] asks to join your realm as migrants." : "[RemasterHouse()] offers to swear fealty to your realm."
	R.RemasterNotice(text + " Answer in the Realm tab.")
	R.RemasterLog(text, "good", null)
	R << "<b><font color=#f2d27a>[text]</font></b>"
	RemasterNotice("You asked [R.RemasterRealmName()]. Waiting for an answer.")
	return 1

Player/proc/RemasterSetLiege(liege_key)
	remaster_liege = liege_key
	if(liege_key) rm_lieges[key] = liege_key
	else rm_lieges -= key
	rm_realm_ver++   // War.dm
	remaster_asked = null

// value: "accept|key", "decline|key", "fealty|key", "leave"
Player/proc/RemasterRealmCommand(value)
	var/list/p = splittext("[value]", "|")
	var/act = p[1]
	var/k = p.len >= 2 ? p[2] : null
	if(act in list("war", "peace", "acceptpeace", "declinepeace")) return RemasterWarCommand(act, k)
	if(act in list("law", "claim", "yield", "refuse")) return RmRuleCommand(act, k)   // rulership (Rulership.dm)
	switch(act)
		if("accept", "decline")
			if(!remaster_requests || !remaster_requests[k]) return 0
			var/kind = remaster_requests[k]
			remaster_requests -= k
			var/Player/O = RemasterPlayerByKey(k)
			if(act == "decline")
				if(O) O.RemasterNotice("[RemasterRealmName()] declined.")
				if(O) O.remaster_asked = null
				return 1
			if(RemasterRootKey(key) == k) return 0   // no loops
			if(O) O.RemasterSetLiege(key)
			else
				rm_lieges[k] = key
				rm_realm_ver++   // War.dm
			var/who = O ? O.RemasterHouse() : k
			var/text = kind == "join" ? "[who]'s people joined your realm." : "[who]'s settlement swore fealty to your realm."
			RemasterLog(text, "good", null)
			RemasterNotice(text)
			if(O)
				O.RemasterNotice("You are now part of [RemasterRealmName()].")
				O.RemasterLog("Joined [RemasterRealmName()]", "good", null)
			return 1
		if("fealty")
			var/Player/R = RemasterPlayerByKey(k)
			if(!R || R == src || remaster_liege || RemasterAlliedKeys(key, k)) return 0
			if(R.remaster_rank < remaster_rank)
				RemasterNotice("Swear fealty only to a realm of your rank or higher.")
				return 0
			return RemasterAskRealm(R, "fealty")
		if("leave")
			if(!remaster_liege) return 0
			var/Player/L = RemasterPlayerByKey(remaster_liege)
			if(L) L.RemasterNotice("[RemasterHouse()] left your realm.")
			RemasterLog("Left the realm", "work", null)
			RemasterSetLiege(null)
			return 1
	return 0

// People of the realm: everyone whose root is this player (members and vassals).
Player/proc/RemasterRealmPlayers()
	. = list()
	for(var/Player/P in world) if(P != src && RemasterRootKey(P.key) == key) . += P

Player/proc/RemasterRealmData()
	var/list/requests = list()
	if(remaster_requests) for(var/k in remaster_requests)
		var/Player/O = RemasterPlayerByKey(k)
		requests += list(list("key"=k, "name"=(O ? O.RemasterHouse() : k), "kind"=remaster_requests[k]))
	var/list/members = list()
	for(var/Player/P in RemasterRealmPlayers())
		var/n = 0
		for(var/mob/Monsters/M in P.UnitList) if(M.Owner == P && M.HP > 0) n++
		members += list(list("name"=P.RemasterHouse(), "people"=n, "vassal"=length(P.RemasterBanners()) > 0))
	var/list/others = list()
	for(var/Player/P in world) if(P != src && P.client && !RemasterAllied(src, P) && length(P.UnitList))
		others += list(list("key"=P.key, "name"=P.RemasterRealmName(), "rank"=P.remaster_rank, "rel"=(RemasterWarState(key, P.key) || "peace"), "ruler"=P.RemasterIsRuler()))
	var/Player/L = remaster_liege ? RemasterPlayerByKey(remaster_liege) : null
	return list("liege"=(remaster_liege ? (L ? L.RemasterRealmName() : remaster_liege) : null), "asked"=remaster_asked,
		"requests"=requests, "members"=members, "others"=others, "war"=RemasterWarData(),
		"house"=RemasterHouse(), "named"=!!remaster_house)
