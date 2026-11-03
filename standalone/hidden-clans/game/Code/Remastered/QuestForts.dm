// Fort challenges (planning/QUEST_MAKER_PLAN_2026-10-31.md sections 4 and 5, phase Q5; the owner's "Yes, all eight",
// 10-31: the real fort and its real garrison, no copies; the maker picks Lethal and captives and the card shows it;
// what dead takers drop stays in the fort; the reward only from the maker).
// A fort notice marks a site: an area, its way in, and its goal (a chest's spot, or a champion of the maker's people).
// The maker garrisons it (Garrison on the notice's card): the selected people take posts inside by themselves, at the
// way in first, then by the goal, then about the rest (Q4's posts, so they guard while the maker is away). A taker who
// took the notice brings a party to the way in and starts a try. For up to RM_FORT_TRY_TIME the party and the garrison
// may fight with no war, but only while both are inside the site (War.dm RemasterWarAllows; the garrison's own look,
// LocateTarget below). Non-lethal: both sides' Lethal switches are held off for the try, so blows knock out. A party
// unit at the goal's chest, or the champion down or dead, wins: the reward goes into the pack of the one who did it.
// The party all down, dead or out of the site, or the time up: the try is lost. Each try's report goes on the notice,
// and the entry fee is the maker's either way. A try isn't saved: a restart ends it, the fee paid.
// The site is marked from the post form (pick the area's corners, the way in, the goal), not a Plan mode tool.

#define RM_FORT_SIDE_MIN 4
#define RM_FORT_SIDE_MAX 48
#define RM_FORT_TRY_TIME 12000      // a try's time: 20 minutes
#define RM_FORT_PARTY_MAX 8
#define RM_FORT_DOOR 3              // tiles from the way in a party gathers to start
#define RM_FORT_GARRISON_MAX 30
#define RM_FORT_TRIES_KEPT 10
#define RM_FORT_LOOK 8              // how far a garrison guard looks for the try's party

var/list/rm_fort_tries = list()     // quest id -> its try (not saved)
var/list/rm_fort_in = list()        // a unit in a try, party or garrison -> the try
var/rm_fort_looping = 0
mob/Monsters/var/tmp
	rm_fort_truce_id                // a try just over: its blows still landing are no grievance for war
	rm_fort_truce_until = 0

Player/var/tmp
	list/rm_fort_picked             // posting a fort: "area", "door", "goal", "champion", "championName"
	list/rm_fort_corner             // the area's first corner while its second is picked

mob/Monsters/Chests/RemasterFortChest
	name = "Fort chest"
	icon_state = "Gold Chest"
	desc = "The goal of a fort challenge: reach it to win the notice's reward."
	var/quest

datum/rm_fort_try
	var/id
	var/taker
	var/house
	var/list/party = list()          // still in the try
	var/list/went = list()           // all who went in
	var/list/entered = list()        // those who have been inside: out again, they have left
	var/list/garrison = list()
	var/list/was = list()            // unit -> its Lethal switch before the try
	var/goal = "chest"               // or "champion"
	var/mob/Monsters/champion
	var/started
	var/ends
	var/lethal = 1
	var/captives = 0
	var/x0
	var/y0
	var/x1
	var/y1
	var/z
	var/gx
	var/gy
	var/dx                           // the way in
	var/dy
	var/left = 0
	var/list/gpost = list()          // each garrison member's post area, in the garrison's order (QuestAdaptive.dm reports)

// Inside the site: its area, on the ground or up on its walls and roofs (the Sky layer over it).
datum/rm_fort_try/proc/Inside(atom/A)
	var/atom/T = A
	while(T && !isturf(T)) T = T.loc
	if(!T || !(T.z in RmQuestLayers(z))) return 0
	return T.x >= x0 && T.x <= x1 && T.y >= y0 && T.y <= y1

// At the way in and not in yet: a party unit going in may already fight (an attack ordered from the doorway).
datum/rm_fort_try/proc/AtDoor(mob/Monsters/M)
	if(M in entered) return 0
	var/turf/D = locate(dx, dy, z)
	return D && (M.z in RmQuestLayers(z)) && get_dist(M, D) <= RM_FORT_DOOR + 2

// The try A and B fight in, when they are on its two sides: the garrison's inside the site, the party's inside or at the
// way in on its way in.
proc/RmTryPair(mob/Monsters/A, mob/Monsters/B)
	if(!length(rm_fort_in) || !A || !B) return null
	var/datum/rm_fort_try/T = rm_fort_in[A]
	if(!T || rm_fort_in[B] != T) return null
	var/a = A in T.party
	if(a == (B in T.party)) return null
	var/mob/Monsters/P = a ? A : B
	var/mob/Monsters/G = a ? B : A
	if(!T.Inside(G) || !(T.Inside(P) || T.AtDoor(P))) return null
	return T

// --- the garrison's look: the try's party inside the site, nearest first ------------------------------------------------
mob/Monsters/LocateTarget(RANGE = 5)
	var/datum/rm_fort_try/T = length(rm_fort_in) ? rm_fort_in[src] : null
	if(T && !(src in T.party) && T.Inside(src))
		var/mob/Monsters/best
		var/bd = max(RANGE, RM_FORT_LOOK) + 1
		for(var/U in T.party)
			if(Rm3DGone(U)) continue
			var/mob/Monsters/M = U
			if(M.HP <= 0 || M.GoingToDie || RmDownOut(M) || !T.Inside(M)) continue
			var/d = get_dist(src, M)
			if(d < bd)
				best = M
				bd = d
		if(best) return best
	return ..(RANGE)

// --- helpers ------------------------------------------------------------------------------------------------------------
proc/RmFortUid(mob/Monsters/M)
	if(!M.remaster_uid) M.remaster_uid = RemasterNewUID()   // as Captives.dm and FarRecords.dm give one
	return M.remaster_uid

proc/RmFortPower(mob/Monsters/M)
	. = M.RmStr() + M.RmAgi() + M.Defence + round(M.MAXHP / 20)
	for(var/obj/Items/I in M) if(I.suffix == "(Equipped)" && I.Defence) . += I.Defence
	. = round(.)

proc/RmFortDanger(g, p)
	if(!p) return null
	var/r = g / p
	return r < 0.6 ? "Easy" : (r < 1.2 ? "Even" : (r < 2 ? "Hard" : "Deadly"))

// The maker's people with these uids, alive (and inside the site when T is given).
proc/RmFortUnits(key, list/uids, datum/rm_fort_try/T)
	. = list()
	var/Player/P = RemasterPlayerByKey(key)
	if(!P || !length(uids)) return
	for(var/mob/Monsters/M in P.UnitList) if(M.Owner == P && M.HP > 0 && !M.GoingToDie && M.remaster_uid && (M.remaster_uid in uids))
		if(!T || T.Inside(M)) . += M

// A fort's site as a try's box (for the card's checks before a try).
proc/RmFortBox(list/Q)
	var/list/S = Q["site"]
	var/datum/rm_fort_try/T = new
	T.x0 = S[1]
	T.y0 = S[2]
	T.x1 = S[3]
	T.y1 = S[4]
	T.z = S[5]
	return T

proc/RmFortChestAt(list/Q)
	var/list/G = Q["goalAt"]
	if(!G) return null
	var/turf/T = locate(G[1], G[2], G[3])
	if(!T) return null
	for(var/mob/Monsters/Chests/RemasterFortChest/C in T) if(C.quest == Q["id"]) return C
	return null

proc/RmFortPlaceChest(list/Q)
	if(Q["goalKind"] != "chest" || RmFortChestAt(Q)) return
	var/list/G = Q["goalAt"]
	var/turf/T = locate(G[1], G[2], G[3])
	if(!T) return
	var/mob/Monsters/Chests/RemasterFortChest/C = new(T)
	C.quest = Q["id"]

// --- picking the site while posting (QuestTargets.dm RmQuestPickClick hands these on) ----------------------------------
Player/proc/RmFortPickClick(atom/A, turf/T)
	if(!rm_fort_picked) rm_fort_picked = list()
	var/turf/G = T.z == SKY_LAYER ? locate(T.x, T.y, GROUND_LAYER) : T
	var/what
	switch(rm_quest_pick)
		if("fortarea")
			rm_fort_corner = list(G.x, G.y, G.z)
			rm_quest_pick = "fortarea2"
			RemasterNotice("One corner of the fort's area. Now click the opposite corner.")
			return 1
		if("fortarea2")
			var/list/c = rm_fort_corner
			if(!c || c[3] != G.z)
				RemasterNotice("Both corners on the same level.")
				return 1
			var/w = abs(G.x - c[1]) + 1
			var/h = abs(G.y - c[2]) + 1
			if(w < RM_FORT_SIDE_MIN || h < RM_FORT_SIDE_MIN || w > RM_FORT_SIDE_MAX || h > RM_FORT_SIDE_MAX)
				RemasterNotice("A fort's area is [RM_FORT_SIDE_MIN] to [RM_FORT_SIDE_MAX] tiles each way; that was [w] by [h]. Click the opposite corner again.")
				return 1
			rm_fort_picked["area"] = list(min(G.x, c[1]), min(G.y, c[2]), max(G.x, c[1]), max(G.y, c[2]), G.z)
			what = "the area, [w] by [h]"
		if("fortdoor")
			rm_fort_picked["door"] = list(G.x, G.y, G.z)
			what = "the way in"
		if("fortgoal")
			rm_fort_picked["goal"] = list(G.x, G.y, G.z)
			what = "the chest's spot"
		if("fortchamp")
			var/mob/Monsters/M = (istype(A, /mob/Monsters) && A:Owner == src) ? A : null
			if(!M) for(var/mob/Monsters/X in T) if(X.Owner == src)
				M = X
				break
			if(!M)
				RemasterNotice("Click one of your own people: the champion.")
				return 1
			rm_fort_picked["champion"] = RmFortUid(M)
			rm_fort_picked["championName"] = M.RemasterBareName()
			what = "[M.RemasterBareName()], your champion"
		else
			return 0
	rm_quest_pick = null
	rm_fort_corner = null
	remaster_hud_tab = "quests"
	RemasterNotice("Picked: [what].")
	return 1

proc/RmFortIn(list/S, list/P)
	return islist(S) && islist(P) && P[3] == S[5] && P[1] >= S[1] && P[1] <= S[3] && P[2] >= S[2] && P[2] <= S[4]

// --- posting: QuestTargets.dm RmQuestPostTarget's "fort" ------------------------------------------------------------------
Player/proc/RmFortPostTarget(list/A)
	var/list/F = rm_fort_picked
	if(!F || !F["area"]) return "Pick the fort's area: its two opposite corners."
	var/list/S = F["area"]
	if(!RmFortIn(S, F["door"])) return "Pick the way in, inside the fort's area."
	var/kind = A["fortGoal"] == "champion" ? "champion" : "chest"
	var/list/D = F["door"]
	var/goal
	var/list/at
	var/datum/rm_fort_try/B = new
	B.x0 = S[1]
	B.y0 = S[2]
	B.x1 = S[3]
	B.y1 = S[4]
	B.z = S[5]
	var/mob/Monsters/champ
	if(kind == "chest")
		if(!RmFortIn(S, F["goal"])) return "Pick the chest's spot, inside the fort's area."
		at = F["goal"]
		var/turf/GT = locate(at[1], at[2], at[3])
		if(!GT || GT.density) return "The chest needs open ground."
		goal = "Take the chest in [RemasterHouse()]'s fort"
		// the chest must be reachable on foot (the reach map's sure "no way"), from one of the maker's people inside
		var/mob/Monsters/near
		var/nd = 1#INF
		for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0 && B.Inside(M) && M.z == GT.z)
			var/d = get_dist(M, locate(D[1], D[2], D[3]))
			if(d < nd)
				near = M
				nd = d
		if(near && RmReachNo(near, GT, 1)) return "Nobody can walk to the chest's spot from inside: a fort's goal must be reachable."
	else
		for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.remaster_uid == F["champion"] && M.HP > 0) champ = M
		if(!champ || !B.Inside(champ)) return "Pick your champion: one of your people inside the fort's area."
		goal = "Defeat [champ.RemasterBareName()], [RemasterHouse()]'s champion"
	var/list/garrison = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0 && M.rm_post && length(garrison) < RM_FORT_GARRISON_MAX)
		var/turf/PT = RmPostTurf(M)
		if(PT && B.Inside(PT)) garrison += RmFortUid(M)
	if(champ && !(champ.remaster_uid in garrison)) garrison += champ.remaster_uid
	var/list/G = list("kind"="place", "x"=D[1], "y"=D[2], "z"=D[3], "r"=1, "what"="the way into [RemasterHouse()]'s fort", "exact"="exact")
	return list("target"=G, "need"=1, "goal"=goal, "title"=(kind == "chest" ? "Storm [RemasterHouse()]'s fort" : "Defeat [RemasterHouse()]'s champion"),
		"site"=S.Copy(), "door"=D.Copy(), "goalKind"=kind, "goalAt"=(at ? at.Copy() : null), "champion"=(champ ? champ.remaster_uid : null),
		"championName"=(champ ? champ.RemasterBareName() : null), "lethal"=(A["lethal"] == "0" ? 0 : 1), "captives"=(A["captives"] == "1" ? 1 : 0),
		"fee"=clamp(round(text2num("[A["fee"]]") || 0), 0, 1000), "garrison"=garrison)

// The notice is up: its site on the record, the chest at its spot.
proc/RmFortPut(list/Q, list/TG)
	for(var/k in list("site", "door", "goalKind", "goalAt", "champion", "championName", "lethal", "captives", "fee", "garrison")) Q[k] = TG[k]
	Q["tries"] = list()
	Q["won"] = 0
	RmFortPlaceChest(Q)

// --- the garrison ------------------------------------------------------------------------------------------------------------
// The selected people take posts inside the site: at the way in first, then by the goal, then about the rest. Aggressive
// guards: they go for whoever a try brings in.
Player/proc/RmFortGarrison(id)
	var/list/Q = rm_quests[id]
	if(!RmQuestLive(Q) || Q["kind"] != "fort" || Q["maker"] != key) return 0
	var/list/units = list()
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0 && !M.Wagon && !M.Critter) units += M
	if(!length(units))
		RemasterNotice("Select the people to garrison the fort with.")
		return 0
	var/datum/rm_fort_try/B = RmFortBox(Q)
	var/list/D = Q["door"]
	var/list/G = Q["goalAt"]
	if(!G && Q["champion"])
		for(var/mob/Monsters/C in RmFortUnits(key, list(Q["champion"]), B)) G = list(C.x, C.y, C.z)
	var/list/spots = list()
	for(var/list/P in list(D, G)) if(P)
		for(var/turf/T in range(2, locate(P[1], P[2], P[3]))) if(!T.density && B.Inside(T) && !(T in spots)) spots += T
	for(var/turf/T in block(locate(B.x0, B.y0, B.z), locate(B.x1, B.y1, B.z))) if(!T.density && !(T in spots) && (T.x + T.y) % 3 == 0) spots += T
	var/list/taken = list()
	for(var/mob/Monsters/O in RmFortUnits(key, Q["garrison"])) if(!(O in units))
		var/turf/OT = RmPostTurf(O)
		if(OT) taken += OT
	var/list/GL = Q["garrison"]
	var/n = 0
	for(var/mob/Monsters/M in units)
		if(!(RmFortUid(M) in GL) && length(GL) >= RM_FORT_GARRISON_MAX)
			RemasterNotice("A fort holds at most [RM_FORT_GARRISON_MAX] in its garrison.")
			break
		var/turf/post
		for(var/turf/T in spots) if(!(T in taken))
			post = T
			break
		if(!post) break
		taken += post
		M.RemasterCancelOrders()
		M.rm_post = "[post.x],[post.y],[post.z]"
		M.rm_post_kind = "aggressive"
		M.HomeLoc = null
		M.RmPostTake()
		if(!(M.remaster_uid in GL)) GL += M.remaster_uid
		n++
	RmQuestChanged()
	RemasterNotice("[n] of yours garrison [Q["title"]]: they take their posts and guard them, while you are away too.")
	return n

// --- tries -----------------------------------------------------------------------------------------------------------------
// Why this player can't start a try now ("" = they can), and the party they would take.
Player/proc/RmFortWhyNotTry(list/Q, list/party)
	if(!RmQuestLive(Q)) return "This notice is closed."
	if(Q["maker"] == key) return "Your own fort."
	if(!Q["takers"][key]) return "Take the notice first, at a notice board."
	if(RemasterAlliedKeys(key, Q["maker"])) return "Your realms are allied: a try needs two realms."
	if(rm_fort_tries[Q["id"]]) return "Another try is on."
	var/list/D = Q["door"]
	var/turf/DT = locate(D[1], D[2], D[3])
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0 && !M.GoingToDie && !RmDownOut(M) && !M.Wagon && !M.Critter && isturf(M.loc) && (M.z in RmQuestLayers(DT.z)) && get_dist(M, DT) <= RM_FORT_DOOR)
		if(party && length(party) < RM_FORT_PARTY_MAX) party += M
	if(party && !length(party)) return "Bring your party to the way in (the marker) first."
	if(remaster_coins < Q["fee"]) return "The entry fee is [Q["fee"]] coins; your treasury has [remaster_coins]."
	return ""

Player/proc/RmFortTryStart(id)
	var/list/Q = rm_quests[id]
	if(!Q || Q["kind"] != "fort") return 0
	var/list/party = list()
	var/why = RmFortWhyNotTry(Q, party)
	if(why)
		RemasterNotice(why)
		return 0
	var/datum/rm_fort_try/T = RmFortBox(Q)
	if(Q["goalKind"] == "champion")
		var/list/C = RmFortUnits(Q["maker"], list(Q["champion"]))
		if(!length(C))
			RmQuestEnd(Q, "its champion is gone")
			RemasterNotice("[Q["title"]]: its champion is gone, so the notice came down.")
			return 0
		T.champion = C[1]
		T.goal = "champion"
	else
		var/list/G = Q["goalAt"]
		T.gx = G[1]
		T.gy = G[2]
		RmFortPlaceChest(Q)
	var/list/DR = Q["door"]
	T.dx = DR[1]
	T.dy = DR[2]
	remaster_coins -= Q["fee"]
	RmQuestPay(Q["maker"], Q["fee"])
	T.id = id
	T.taker = key
	T.house = RemasterHouse()
	T.party = party.Copy()
	T.went = party.Copy()
	T.garrison = RmFortUnits(Q["maker"], Q["garrison"], T)
	for(var/U in T.garrison) T.gpost += RmFortPostArea(T, U)   // where each stands, for the maker's report (QuestAdaptive.dm)
	T.lethal = Q["lethal"]
	T.captives = Q["captives"]
	T.started = world.time
	T.ends = world.time + RM_FORT_TRY_TIME
	rm_fort_tries[id] = T
	for(var/mob/Monsters/M in T.party + T.garrison)
		rm_fort_in[M] = T
		if(!T.lethal)   // non-lethal: blows, arrows and spells knock out (their switches are back after the try)
			T.was[M] = M.remaster_nonlethal
			M.remaster_nonlethal = 1
	RmQuestJournal(Q, "Try by [T.house]: [length(T.party)] went in against [length(T.garrison)]")
	RmQuestChanged()
	RemasterNotice("Your try at [Q["title"]] has begun: [RM_FORT_TRY_TIME / 600] minutes. [Q["goal"]].[T.lethal ? " Lethal." : " Non-lethal: blows knock out."]")
	RemasterLog("[length(T.party)] went into [Q["house"]]'s fort", "fight", locate(T.x0, T.y0, T.z))
	var/Player/K = RemasterPlayerByKey(Q["maker"])
	if(K)
		K.RemasterNotice("[T.house]'s party of [length(T.party)] storms your fort: [Q["title"]].")
		K.RemasterLog("[T.house]'s party of [length(T.party)] storms your fort", "fight", locate(T.x0, T.y0, T.z))
	spawn(0) RmFortLoop()
	return 1

proc/RmFortLoop()
	if(rm_fort_looping) return
	rm_fort_looping = 1
	while(length(rm_fort_tries))
		for(var/id in rm_fort_tries.Copy()) RmFortTick(rm_fort_tries[id])
		sleep(10)
	rm_fort_looping = 0

proc/RmFortTruce(mob/Monsters/A, mob/Monsters/B)
	return istype(A) && istype(B) && A.rm_fort_truce_id && A.rm_fort_truce_id == B.rm_fort_truce_id && A.rm_fort_truce_until > world.time && B.rm_fort_truce_until > world.time

// A unit is out of the try: back to its own Lethal switch, its fights with the other side over (chases, targets,
// defences, attacks: the Q5 play-test saw a guard fight on after a try), with a short truce for blows under way.
proc/RmFortLeave(datum/rm_fort_try/T, mob/Monsters/M)
	rm_fort_in -= M
	T.party -= M
	if(Rm3DGone(M)) return
	if(M in T.was)
		M.remaster_nonlethal = T.was[M]
		T.was -= M
	for(var/U in (M in T.went) ? T.garrison : T.went)
		if(Rm3DGone(U)) continue
		var/mob/Monsters/O = U
		if(O.destination == M) O.destination = null
		if(O.remaster_attacker == M) O.remaster_attacker = null
		if(M.remaster_attacker == O) M.remaster_attacker = null
		if(M.destination == O) M.destination = null
		if(O.Target == M) O.Target = null
		if(M.Target == O) M.Target = null
		var/datum/remaster_defense/OD = O.remaster_defense
		if(OD && OD.attacker == M) O.RemasterCancelDefense(1)
		var/datum/remaster_defense/MD = M.remaster_defense
		if(MD && MD.attacker == O) M.RemasterCancelDefense(1)
		var/datum/remaster_attack/OA = O.remaster_attack
		if(OA && OA.target == M) OA.target = null
		var/datum/remaster_attack/MA = M.remaster_attack
		if(MA && MA.target == O) MA.target = null
		O.rm_fort_truce_id = T.id
		O.rm_fort_truce_until = world.time + 300
	M.rm_fort_truce_id = T.id
	M.rm_fort_truce_until = world.time + 300

// Once a second: the goal, who is still in, the time.
proc/RmFortTick(datum/rm_fort_try/T)
	var/list/Q = rm_quests[T.id]
	if(!RmQuestLive(Q)) return RmFortTryEnd(T, "void", "the notice came down")
	var/list/standing = list()
	var/list/D = Q["door"]
	var/turf/DT = locate(D[1], D[2], D[3])
	for(var/U in T.party.Copy())
		if(Rm3DGone(U)) continue
		var/mob/Monsters/M = U
		if(M.HP <= 0 || M.GoingToDie) continue
		if(T.Inside(M))
			if(!(M in T.entered)) T.entered += M
		else if((M in T.entered) || !DT || get_dist(M, DT) > RM_FORT_DOOR + 2)   // out again, or wandered off from the way in
			T.left++
			RmFortLeave(T, M)
			continue
		if(!RmDownOut(M)) standing += M
	if(T.goal == "champion")   // (a deleted champion reads as null: Rm3DGone first)
		var/C = T.champion
		if(!C || Rm3DGone(C) || C:HP <= 0 || C:GoingToDie || RmDownOut(C))
			return RmFortTryEnd(T, "won", "their champion fell", length(standing) ? standing[1] : null)
	else
		var/turf/G = locate(T.gx, T.gy, T.z)
		for(var/mob/Monsters/M in standing) if(T.Inside(M) && get_dist(M, G) <= 1)
			return RmFortTryEnd(T, "won", "[M.RemasterBareName()] reached the chest", M)
	if(!length(standing)) return RmFortTryEnd(T, "lost", "the party is all down, fallen or out")
	if(world.time >= T.ends) return RmFortTryEnd(T, "lost", "the time ran out")

proc/RmFortTryEnd(datum/rm_fort_try/T, result, why, mob/Monsters/winner)
	rm_fort_tries -= T.id
	var/fell = 0
	var/down = 0
	for(var/U in T.went)
		if(Rm3DGone(U) || U:HP <= 0 || U:GoingToDie) fell++
		else if(RmDownOut(U)) down++
	var/gfell = 0
	var/gdown = 0
	var/list/broke = list()   // the posts that lost someone (QuestAdaptive.dm: the maker's report)
	for(var/i = 1, i <= length(T.garrison), i++)
		var/U = T.garrison[i]
		var/lost = 0
		if(Rm3DGone(U) || U:HP <= 0 || U:GoingToDie)
			gfell++
			lost = 1
		else if(RmDownOut(U))
			gdown++
			lost = 1
		if(lost && i <= length(T.gpost) && !(T.gpost[i] in broke)) broke += T.gpost[i]
	for(var/U in T.went + T.garrison) if(rm_fort_in[U] == T) RmFortLeave(T, U)
	var/list/Q = rm_quests[T.id]
	if(!Q) return
	var/mins = max(1, round((world.time - T.started) / 600))
	var/text = "[T.house]: [length(T.went)] went in, [fell] fell, [down] down, [T.left] left; the garrison lost [gfell] of [length(T.garrison)] ([mins] min). [result == "won" ? "Won" : (result == "lost" ? "Lost" : "Called off")]: [why]."
	var/list/TR = Q["tries"]
	if(!islist(TR)) TR = Q["tries"] = list()
	TR += list(list("text"=text, "result"=result, "at"=RemasterNow(), "party"=length(T.went), "fell"=fell, "down"=down,
		"gsize"=length(T.garrison), "gfell"=gfell, "gdown"=gdown, "broke"=broke))
	if(length(TR) > RM_FORT_TRIES_KEPT) TR.Cut(1, 2)
	if(result == "won") Q["won"] = (Q["won"] || 0) + 1
	else if(result == "lost") RmQuestFailed(Q, T.taker)   // for "after ... failed" (QuestChains.dm)
	RmQuestJournal(Q, text)
	rm_quest_ver++
	var/Player/P = RemasterPlayerByKey(T.taker)
	var/Player/K = RemasterPlayerByKey(Q["maker"])
	if(P) P.RemasterLog("Your try at [Q["title"]]: [text]", result == "won" ? "good" : "fight", locate(T.x0, T.y0, T.z))
	if(K) K.RemasterLog("A try at your fort: [text]", result == "won" ? "fight" : "good", locate(T.x0, T.y0, T.z))
	if(result == "won") RmQuestDone(Q, T.taker, winner)
	else if(P) P.RemasterNotice("Your try at [Q["title"]] is over: [why].")

// The notice closed: its try called off, its chest gone.
proc/RmFortClosed(list/Q)
	var/datum/rm_fort_try/T = rm_fort_tries[Q["id"]]
	if(T) RmFortTryEnd(T, "void", "the notice came down")
	var/mob/Monsters/Chests/RemasterFortChest/C = RmFortChestAt(Q)
	if(C) del C

// --- the card --------------------------------------------------------------------------------------------------------------
Player/proc/RmFortCardData(list/Q)
	var/datum/rm_fort_try/B = RmFortBox(Q)
	var/list/G = RmFortUnits(Q["maker"], Q["garrison"], B)
	var/gp = 0
	for(var/mob/Monsters/M in G) gp += RmFortPower(M)
	var/list/party = list()
	var/why = Q["maker"] == key ? "" : RmFortWhyNotTry(Q, party)
	var/pp = 0
	for(var/mob/Monsters/M in party) pp += RmFortPower(M)
	var/list/D = list("lethal"=Q["lethal"], "captives"=Q["captives"], "fee"=Q["fee"], "garrison"=length(G), "power"=gp,
		"party"=length(party), "partyPower"=pp, "danger"=RmFortDanger(gp, pp), "why"=why, "goalKind"=Q["goalKind"],
		"champion"=Q["championName"], "won"=(Q["won"] || 0), "door"=Q["door"], "site"=Q["site"])
	var/list/tries = list()
	for(var/list/TR in Q["tries"]) tries += TR["text"]
	D["tries"] = tries
	if(Q["maker"] == key) D["report"] = RmFortReport(Q)   // the tries summed for its maker (QuestAdaptive.dm)
	if(Q["maker"] == key)
		var/n = 0
		for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.HP > 0) n++
		D["selected"] = n
	var/datum/rm_fort_try/T = rm_fort_tries[Q["id"]]
	if(T)
		var/inside = 0
		for(var/U in T.party) if(!Rm3DGone(U) && U:HP > 0 && !RmDownOut(U)) inside++
		var/gs = 0
		for(var/U in T.garrison) if(!Rm3DGone(U) && U:HP > 0 && !U:GoingToDie && !RmDownOut(U)) gs++
		D["try"] = list("house"=T.house, "left"=max(0, round((T.ends - world.time) / 600, 0.1)), "in"=inside, "went"=length(T.went), "standing"=gs, "mine"=(T.taker == key))
	return D
