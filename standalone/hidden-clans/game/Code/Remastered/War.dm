// War between realms. Realms (a ruler with their members and vassals, Realms.dm) are
// at peace by default: attack orders and attack-move leave another realm's people
// alone, though anyone attacked may still fight back. A realm's ruler may:
//   Declare war   - the war horns sound; fighting starts after 60 seconds (at once
//                   when the other realm attacked your people while at peace)
//   Offer peace   - the other ruler accepts or declines; peace brings a 10 minute
//                   truce in which neither may declare war again
// At war the realms' people fight on sight, may dig and tear down walls and doors in
// each other's land, and can besiege banners: units standing by an enemy banner with
// no defender near it raise the siege; at 100% the banner and its land change hands,
// with a quarter of the loser's coins as plunder. Kills count 1, banners taken 5. A
// realm that loses its last banner sues for peace. Wars are saved with the world.

#define RM_WAR_WARNING 60           // seconds before fighting starts
#define RM_WAR_TRUCE 600
#define RM_SIEGE_REACH 2
#define RM_SIEGE_GUARD 5

var/list/rm_wars = list()           // saved: "rootA|rootB" -> list(state, until, by, scoreA, scoreB, peace_by)
var/rm_realm_ver = 0                // moves whenever a war's state or a liege changes (Attack.dm RmAtkPairs keeps answers while it stands)
var/rm_war_loop = 0
var/rm_war_now = 0                  // saved: seconds of war time (the war loop counts it)
obj/RemasterBanner/var/tmp
	siege = 0
	siege_by                        // key of the besieging player
Player/var/tmp/list/remaster_grievances   // root key -> world.time they attacked us at peace

proc/RemasterWarKey(a, b)
	a = RemasterRootKey(a)
	b = RemasterRootKey(b)
	if(!a || !b || a == b) return null
	return sorttext(a, b) > 0 ? "[a]|[b]" : "[b]|[a]"

proc/RemasterWar(a, b)
	var/k = RemasterWarKey(a, b)
	return k ? rm_wars[k] : null

// "war", "warning", "truce" or null (peace).
proc/RemasterWarState(a, b)
	var/list/W = RemasterWar(a, b)
	return W ? W[1] : null

proc/RemasterAtWarKeys(a, b)
	return RemasterWarState(a, b) == "war"

proc/RemasterAtWar(Player/A, Player/B)
	return istype(A) && istype(B) && RemasterAtWarKeys(A.key, B.key)

// Another realm's unit may be fought: at war, or it attacked this unit lately.
proc/RemasterWarAllows(mob/Monsters/me, mob/Monsters/E)
	if(!istype(me.Owner, /Player) || !istype(E.Owner, /Player)) return 1
	if(length(rm_fort_in) && RmTryPair(me, E)) return 1   // a fort challenge's try, inside its site (QuestForts.dm)
	if(RemasterAtWar(me.Owner, E.Owner)) return 1
	if(me.remaster_attacker == E && world.time - me.remaster_attacked_at < 300) return 1
	if(E.remaster_attacker && E.remaster_attacker:Owner == me.Owner && world.time - E.remaster_attacked_at < 300) return 1
	return 0

// Score: index of the side in the war key (1 = first key, 2 = second).
proc/RemasterWarSide(k, key)
	var/list/p = splittext(k, "|")
	return RemasterRootKey(key) == p[1] ? 1 : 2

proc/RemasterWarScore(a, b, points)
	var/k = RemasterWarKey(a, b)
	var/list/W = k && rm_wars[k]
	if(!W || W[1] != "war") return
	if(RemasterWarSide(k, a) == 1) W[4] = W[4] + points
	else W[5] = W[5] + points

// Everyone of a realm (the ruler, members and vassals) online.
proc/RemasterRealmOf(key)
	. = list()
	var/r = RemasterRootKey(key)
	for(var/Player/P in world) if(RemasterRootKey(P.key) == r) . += P

proc/RemasterRealmNotice(key, text, kind = "fight")
	for(var/Player/P in RemasterRealmOf(key))
		P.RemasterNotice(text)
		P.RemasterLog(text, kind, null)
		P << "<b><font color=#e0675a>[text]</font></b>"

proc/RemasterRealmCheer(key, id, text, value, days = 1)
	for(var/Player/P in RemasterRealmOf(key)) P.RemasterCheer(id, text, value, days)

proc/RemasterRulerName(key)
	var/Player/P = RemasterPlayerByKey(RemasterRootKey(key))
	return P ? P.RemasterRealmName() : RemasterRootKey(key)

Player/proc/RemasterIsRuler()
	return !remaster_liege

// value: "war|key", "peace|key", "acceptpeace|key", "declinepeace|key"
Player/proc/RemasterWarCommand(act, k)
	var/Player/O = RemasterPlayerByKey(k)
	if(!O || O == src) return 0
	if(!RemasterIsRuler())
		RemasterNotice("Only your realm's ruler decides on war and peace.")
		return 0
	if(RemasterAllied(src, O))
		RemasterNotice("[O.RemasterHouse()] is part of your realm.")
		return 0
	var/wk = RemasterWarKey(key, O.key)
	var/list/W = rm_wars[wk]
	var/them = RemasterRulerName(O.key)
	switch(act)
		if("war")
			if(W && W[1] == "truce" && rm_war_now < W[2])
				RemasterNotice("You swore a truce with [them]: [round((W[2] - rm_war_now) / 60) + 1] more minute\s.")
				return 0
			if(W && W[1] != "truce") return 0
			var/cause = remaster_grievances && remaster_grievances[RemasterRootKey(O.key)]
			var/start = cause ? rm_war_now : rm_war_now + RM_WAR_WARNING
			rm_wars[wk] = list(cause ? "war" : "warning", start, key, 0, 0, null)
			rm_realm_ver++
			if(remaster_grievances) remaster_grievances -= RemasterRootKey(O.key)
			RemasterRealmNotice(key, cause ? "War! You answer [them]'s attack: fighting starts now." : "You declared war on [them]. Fighting starts in [RM_WAR_WARNING] seconds.")
			RemasterRealmNotice(O.key, cause ? "[RemasterRealmName()] declared war on you over your attack. Fighting starts now!" : "[RemasterRealmName()] declared war on you! Fighting starts in [RM_WAR_WARNING] seconds: gather your people.")
			RemasterRealmCheer(key, "war", "Our realm went to war", -3, 1)
			RemasterRealmCheer(O.key, "war", "Our realm is at war", -5, 1)
			return 1
		if("peace")
			if(!W || W[1] == "truce") return 0
			W[6] = RemasterRootKey(key)
			RemasterNotice("You offered peace to [them].")
			O = RemasterPlayerByKey(RemasterRootKey(O.key)) || O
			O.RemasterNotice("[RemasterRealmName()] offers peace. Answer in the Realm tab.")
			O.RemasterLog("[RemasterRealmName()] offers peace.", "good", null)
			O << "<b><font color=#f2d27a>[RemasterRealmName()] offers peace. Answer in the Realm tab.</font></b>"
			return 1
		if("acceptpeace", "declinepeace")
			if(!W || !W[6] || W[6] == RemasterRootKey(key)) return 0
			if(act == "declinepeace")
				W[6] = null
				RemasterRealmNotice(O.key, "[RemasterRealmName()] refused your peace. The war goes on.")
				RemasterNotice("You refused peace.")
				return 1
			RemasterMakePeace(wk, "Peace with [them] is sworn.", "Peace with [RemasterRealmName()] is sworn.", O.key)
			return 1
	return 0

proc/RemasterMakePeace(wk, text_mine, text_theirs, their_key)
	var/list/W = rm_wars[wk]
	if(!W) return
	var/list/p = splittext(wk, "|")
	var/score = "[RemasterRulerName(p[1])] [W[4]] : [W[5]] [RemasterRulerName(p[2])]"
	rm_wars[wk] = list("truce", rm_war_now + RM_WAR_TRUCE, null, W[4], W[5], null)
	rm_realm_ver++
	var/mine = p[1] == RemasterRootKey(their_key) ? p[2] : p[1]
	RemasterRealmNotice(mine, "[text_mine] Final score: [score].", "good")
	RemasterRealmNotice(their_key, "[text_theirs] Final score: [score].", "good")
	for(var/k in p) RemasterRealmCheer(k, "war", "The war is over", 6, 1)
	for(var/obj/RemasterBanner/B in rm_banners) if(B.owner_key && RemasterWarKey(B.owner_key, B.siege_by) == wk)
		B.siege = 0
		B.siege_by = null
	RmClaimPeace(wk)   // a claim between the two is dropped (Rulership.dm)

// Attacked by another realm's unit while at peace: a reason for war (no warning).
proc/RemasterWarGrievance(mob/Monsters/victim, mob/Monsters/enemy)
	var/Player/P = victim.Owner
	var/Player/E = enemy.Owner
	if(!istype(P) || !istype(E) || RemasterAllied(P, E) || RemasterWarState(P.key, E.key)) return
	var/Player/R = RemasterPlayerByKey(RemasterRootKey(P.key)) || P
	if(!R.remaster_grievances) R.remaster_grievances = list()
	var/ek = RemasterRootKey(E.key)
	if(R.remaster_grievances[ek] && world.time - R.remaster_grievances[ek] < 1200) return
	R.remaster_grievances[ek] = world.time
	R.RemasterNotice("[E.RemasterHouse()]'s people attacked yours while at peace. You may declare war at once (Realm tab).")

// A unit of a player died: the realm at war with its owner scores.
proc/RemasterWarDeath(mob/Monsters/D)
	var/mob/Monsters/K = D.remaster_attacker
	if(!istype(D.Owner, /Player) || !istype(K) || !istype(K.Owner, /Player)) return
	if(world.time - D.remaster_attacked_at > 300 || !RemasterAtWar(D.Owner, K.Owner)) return
	RemasterWarScore(K.Owner:key, D.Owner:key, 1)

// Enemies at war may work (dig, tear down) inside each other's land.
proc/RemasterWarMayWork(Player/P, obj/RemasterBanner/B)
	return B && istype(P) && RemasterAtWarKeys(P.key, B.owner_key)

proc/RemasterWarLoop()
	while(1)
		sleep(10)
		rm_war_now++
		for(var/k in rm_wars.Copy())
			var/list/W = rm_wars[k]
			if(W[1] == "warning" && rm_war_now >= W[2])
				W[1] = "war"
				rm_realm_ver++
				var/list/p = splittext(k, "|")
				for(var/s in p) RemasterRealmNotice(s, "The war with [RemasterRulerName(s == p[1] ? p[2] : p[1])] has begun!")
			else if(W[1] == "truce" && rm_war_now >= W[2])
				rm_wars -= k
				rm_realm_ver++
		RemasterSiegeTick()

// Sieges: once a second for every banner of a realm at war.
proc/RemasterSiegeTick()
	for(var/obj/RemasterBanner/B in rm_banners)
		if(!B.loc || !B.owner_key) continue
		var/war = 0
		for(var/k in rm_wars) if(rm_wars[k][1] == "war" && findtext("|[k]|", "|[RemasterRootKey(B.owner_key)]|")) war = 1
		if(!war)
			B.siege = 0
			continue
		var/list/foes = list()
		var/guards = 0
		var/was = B.siege
		var/owner = B.owner_key
		for(var/mob/Monsters/M in range(RM_SIEGE_GUARD, B))
			if(M.HP <= 0 || M.GoingToDie || M.Sleeping || M.Fainted || !istype(M.Owner, /Player)) continue
			if(RemasterAlliedKeys(M.Owner:key, B.owner_key)) guards++
			else if(get_dist(M, B) <= RM_SIEGE_REACH && RemasterAtWarKeys(M.Owner:key, B.owner_key)) foes += M
		if(length(foes) && !guards)
			var/mob/Monsters/F = foes[1]
			if(B.siege_by != F.Owner:key && !RemasterAlliedKeys(B.siege_by, F.Owner:key)) B.siege = 0
			if(!B.siege) RemasterRealmNotice(B.owner_key, "Your banner at [B.x],[B.y] is under siege by [F.Owner:RemasterHouse()]'s people!")
			B.siege_by = F.Owner:key
			B.siege = min(100, B.siege + 2 * min(5, length(foes)))
			if(B.siege >= 100) RemasterSiegeTake(B, F.Owner)
		else if(guards && B.siege) B.siege = max(0, B.siege - 3 * min(5, guards))
		else if(B.siege) B.siege = max(0, B.siege - 1)
		if(!B.siege)
			// it faded (defenders came, or the besiegers left): the owner is told, as it was told when it began
			if(was && B.owner_key == owner) RemasterRealmNotice(owner, "The siege of your banner at [B.x],[B.y] is lifted.", "good")
			B.siege_by = null

proc/RemasterSiegeTake(obj/RemasterBanner/B, Player/W)
	var/loser = B.owner_key
	var/Player/L = RemasterPlayerByKey(loser)
	var/name = L ? L.RemasterHouse() : B.owner_name
	B.owner_key = W.key
	B.owner_name = W.RemasterHouse()
	B.colour = RemasterClaimColour(W.key)
	B.radius = W.RemasterClaimRadius()
	B.siege = 0
	B.siege_by = null
	var/plunder = 0
	if(L)
		plunder = round(L.remaster_coins / 4)
		L.remaster_coins -= plunder
		W.remaster_coins += plunder
	RemasterWarScore(W.key, loser, 5)
	RemasterRealmNotice(W.key, "Your people took [name]'s banner at [B.x],[B.y]: the land is yours[plunder ? ", with [plunder] coins of plunder" : ""].", "good")
	RemasterRealmNotice(loser, "[W.RemasterHouse()]'s people took your banner at [B.x],[B.y][plunder ? " and [plunder] coins" : ""]!")
	RemasterRealmCheer(W.key, "siege", "We took enemy land", 5, 1)
	RemasterRealmCheer(loser, "siege", "We lost land to the enemy", -6, 1)
	// a realm with no banner left sues for peace
	var/left = 0
	for(var/obj/RemasterBanner/X in rm_banners) if(X.loc && RemasterAlliedKeys(X.owner_key, loser)) left++
	if(!left)
		var/wk = RemasterWarKey(W.key, loser)
		// a realm that refused W's claim on its seat swears fealty to W's instead (Rulership.dm)
		if(!RmClaimFall(W, loser, wk)) RemasterMakePeace(wk, "[name]'s realm has fallen and sues for peace.", "Your realm has fallen: you sue for peace.", loser)

// world/New: this file's part is step RmChainWorldNew_War in Code/Remastered/Chains/WorldNew.dm

// For the Realm tab: relations with every other realm, and the sieges that concern us.
Player/proc/RemasterWarData()
	var/list/wars = list()
	var/me = RemasterRootKey(key)
	for(var/k in rm_wars)
		var/list/p = splittext(k, "|")
		if(!(me in p)) continue
		var/list/W = rm_wars[k]
		var/side = p[1] == me ? 1 : 2
		var/other = p[3 - side]
		var/Player/O = RemasterPlayerByKey(other)
		wars += list(list("key"=other, "name"=(O ? O.RemasterRealmName() : other), "state"=W[1],
			"secs"=max(0, W[2] - rm_war_now), "mine"=W[3 + side], "theirs"=W[6 - side],
			"peaceBy"=(W[6] ? (W[6] == me ? "me" : "them") : null)))
	var/list/sieges = list()
	for(var/obj/RemasterBanner/B in rm_banners) if(B.siege && B.loc)
		var/ours = RemasterAlliedKeys(B.owner_key, key)
		if(ours || RemasterAlliedKeys(B.siege_by, key)) sieges += list(list("x"=B.x, "y"=B.y, "p"=B.siege, "ours"=ours, "name"=B.owner_name))
	return list("wars"=wars, "sieges"=sieges, "ruler"=RemasterIsRuler(), "grievances"=(remaster_grievances ? remaster_grievances.Copy() : list()))
