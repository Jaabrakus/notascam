// Quest targets (planning/QUEST_MAKER_PLAN_2026-10-31.md section 17, phase Q3; the owner's "Yes, use it", 10-31).
// Every goal is an action and a target, and a target is one of three kinds:
//  - a thing that exists: a beast, a golem, a cave mouth. The maker clicks it; its marker follows it.
//  - a kind of thing: "5 deer". No marker, though the maker may mark a hint area.
//  - a place: a point or a circle. The only kind that is a waypoint.
// Markers obey the fog of war. A thing out of sight shows where it was last seen and how long ago; the spot is learned
// only when the maker's or a taker's people see it. The maker also picks how exact to be: the spot, a circle about
// it, or only their words. Markers are sent to each viewer for the quests they made, took or read (RmQuestMarksData):
// on the world map, as pins in 3D, and as distance and direction in the tracker.
// Goals are checked against the same target, from events, never by scanning the world:
//  - slay: the thing dies to a blow of a taker's people (RmQuestStruck, from RemasterThreatenedBy; RmQuestDied, from
//    Death). Slain by anyone else, the notice comes down with its reward back to the maker.
//  - hunt: wild creatures of that race killed by a taker's people.
//  - clear: a lair's beast, or every creature of a cave visit, killed while a taker's party is down there.
//  - reach: one of a taker's people inside the place (RmQuestReachTick, from RemasterTrack).
//  - work: blocks a taker's builders lay on the maker's build plan (RmQuestLaid, from Plans.dm RmPlanLayTick). The taker
//    gets a build plan of their own over the maker's blocks, worked by their own builders with their own stone or logs;
//    the blocks are the maker's (remaster_laid_by), and the maker's plan waits meanwhile.
// Wild creatures aren't saved with the world: after a restart a slay quest finds its quarry again near where it was
// last seen (one of the same kind within RM_QUEST_REBIND tiles), or comes down with its reward back to the maker.
// Not here: bounties on another realm's people (that is war's business), chains that reveal targets (Q6).

#define RM_QUEST_HIT_KEEP 600      // a blow by a player's people names the killer this long (1 minute)
#define RM_QUEST_CIRCLE 10         // the radius of "somewhere about here"
#define RM_QUEST_PLACE_MAX 12      // the widest place a maker may mark (radius)
#define RM_QUEST_HUNT_MAX 50       // creatures a hunt may ask for
#define RM_QUEST_WORK_MAX 200      // blocks a work notice may ask for
#define RM_QUEST_MARKS 20          // markers one viewer is sent
#define RM_QUEST_REBIND 12         // after a restart: how far from the last-seen spot a quarry is looked for

var/rm_quest_hunting = 0           // taken quests a death can count for (slay, hunt, clear): 0 = the hooks do nothing
var/rm_quest_working = 0           // taken work quests: 0 = the laying hook does nothing
var/list/rm_quest_by_tag = list()  // a quarry's tag -> its open slay quests
var/list/rm_quest_hunt_by = list() // taker key -> the hunt quests they took
var/list/rm_quest_clear_at = list()   // a cave mouth's "x,y,z" -> its open clear quests
var/list/rm_quest_reach_by = list()   // taker key -> the reach quests they took
var/list/rm_quest_by_maker = list()   // maker key -> their open quests with a target
var/list/rm_quest_things = list()  // tag -> the creature (not saved: RmQuestRebind finds it again)
var/rm_quest_tag_serial = 0
// what a hunt may ask for: wild creatures' races -> one, many
var/list/rm_quest_hunt_kinds = list("Deer"=list("deer", "deer"), "Mole"=list("mole", "moles"), "Spider"=list("spider", "spiders"),
	"CaveSpider"=list("cave spider", "cave spiders"), "Goblin"=list("goblin", "goblins"), "Kobold"=list("kobold", "kobolds"),
	"Ratman"=list("ratman", "ratmen"), "Orc"=list("wild orc", "wild orcs"), "Skeleton"=list("skeleton", "skeletons"),
	"Zombie"=list("zombie", "zombies"), "Lizardman"=list("lizardman", "lizardmen"), "Frogman"=list("frogman", "frogmen"),
	"Gremlin"=list("gremlin", "gremlins"), "Devourer"=list("devourer", "devourers"), "DeathBeatle"=list("death beetle", "death beetles"),
	"FleshCrawler"=list("flesh crawler", "flesh crawlers"), "SandKing"=list("sand king", "sand kings"), "Demon"=list("demon", "demons"),
	"Dragon"=list("dragon", "dragons"), "Golem"=list("stone golem", "stone golems"))

mob/Monsters/var/tmp
	rm_qtag                        // a slay quest's quarry: its tag (rm_quest_things)
	rm_qhit_key                    // the last player whose people struck it, while quests count deaths
	mob/Monsters/rm_qhit_by
	rm_qhit_at = 0
	rm_qdead = 0                   // its death counted once
Player/var/tmp
	list/rm_quest_read             // quest ids whose card this player opened: their markers show
	rm_quest_pick                  // posting: what the next click in the world picks ("thing", "mouth", "place")
	list/rm_quest_picked           // ...and what it picked
	rm_quest_reach_at = 0
	rm_quest_marks_key
	rm_quest_marks_at = 0
	rm_quest_marks_live = 0
	list/rm_quest_marks

// --- the indexes the hooks read, made again after every change (RmQuestChanged) ----------------------------------------
proc/RmQuestKinds()
	rm_quest_hunting = 0
	rm_quest_working = 0
	rm_quest_by_tag = list()
	rm_quest_hunt_by = list()
	rm_quest_clear_at = list()
	rm_quest_reach_by = list()
	rm_quest_by_maker = list()
	rm_quest_next_of = list()
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		if(Q["after"] && RmQuestLive(Q)) for(var/list/L in Q["after"]) RmQuestIndexAdd(rm_quest_next_of, L[1], id)   // chains (QuestChains.dm)
		var/list/G = Q["target"]
		if(!G || (Q["state"] != "open" && Q["state"] != "closing")) continue
		var/k = Q["kind"]
		RmQuestIndexAdd(rm_quest_by_maker, Q["maker"], id)
		if(k == "slay") RmQuestIndexAdd(rm_quest_by_tag, G["tag"], id)
		else if(k == "clear") RmQuestIndexAdd(rm_quest_clear_at, G["mouth"], id)
		var/list/TK = Q["takers"]
		if(!length(TK)) continue
		if(k == "slay" || k == "hunt" || k == "clear") rm_quest_hunting++
		else if(k == "work") rm_quest_working++
		for(var/key in TK)
			if(k == "hunt") RmQuestIndexAdd(rm_quest_hunt_by, key, id)
			else if(k == "reach") RmQuestIndexAdd(rm_quest_reach_by, key, id)

proc/RmQuestIndexAdd(list/L, k, id)
	if(!k) return
	var/list/I = L[k]
	if(!I) I = L[k] = list()
	I += id

proc/RmQuestLive(list/Q)
	return Q && (Q["state"] == "open" || Q["state"] == "closing")

// --- small helpers ----------------------------------------------------------------------------------------------------
proc/RmQuestTag(mob/Monsters/M)
	if(!M.rm_qtag) M.rm_qtag = "t[RemasterIdStamp()]-[++rm_quest_tag_serial]"
	rm_quest_things[M.rm_qtag] = M
	return M.rm_qtag

proc/RmQuestThing(list/G)
	var/mob/Monsters/M = rm_quest_things[G["tag"]]
	if(!M || Rm3DGone(M) || M.rm_qtag != G["tag"]) return null
	return M

// After a restart the quarry is a new creature: one of the same kind near where it was last seen takes the tag.
proc/RmQuestRebind(list/G)
	var/turf/T = locate(G["x"], G["y"], G["z"])
	var/p = text2path("[G["type"]]")
	if(!T || !p) return null
	for(var/mob/Monsters/M in range(RM_QUEST_REBIND, T)) if(M.type == p && !M.rm_qtag && !istype(M.Owner, /Player) && M.HP > 0 && !M.GoingToDie)
		M.rm_qtag = G["tag"]
		rm_quest_things[G["tag"]] = M
		return M
	return null

proc/RmQuestMouth(k)
	var/list/p = splittext("[k]", ",")
	if(length(p) != 3) return null
	var/turf/T = locate(text2num(p[1]), text2num(p[2]), text2num(p[3]))
	return T ? (locate(/obj/RemasterCaveMouth) in T) : null

proc/RmQuestMouthNear(turf/T, r)
	if(!T) return null
	var/obj/RemasterCaveMouth/best
	var/bd = r + 1
	for(var/obj/RemasterCaveMouth/O in rm_cave_mouths) if(O.z == T.z)
		var/d = get_dist(O, T)
		if(d < bd)
			best = O
			bd = d
	return best

// The layers a place covers: the surface and the mountain tops over it are one place.
proc/RmQuestLayers(zz)
	return (zz == GROUND_LAYER || zz == SKY_LAYER) ? list(GROUND_LAYER, SKY_LAYER) : list(zz)

// "about here": a circle round the spot, its centre off it by up to half its radius, so the circle doesn't give the spot
// away. The offset is kept, so the circle moves with a quarry's last-seen spot.
proc/RmQuestCircle(list/G)
	if(G["exact"] != "circle") return
	if(isnull(G["ox"]))
		G["ox"] = rand(-RM_QUEST_CIRCLE / 2, RM_QUEST_CIRCLE / 2)
		G["oy"] = rand(-RM_QUEST_CIRCLE / 2, RM_QUEST_CIRCLE / 2)
	G["cx"] = clamp(G["x"] + G["ox"], 1, world.maxx)
	G["cy"] = clamp(G["y"] + G["oy"], 1, world.maxy)

// The quarry is seen by the maker's or a taker's people: the notice learns where it is.
proc/RmQuestSeen(list/G, mob/Monsters/M)
	var/atom/T = M.loc
	while(T && !isturf(T)) T = T.loc
	if(!T) return
	G["x"] = T.x
	G["y"] = T.y
	G["z"] = T.z
	G["seen"] = RemasterNow()
	RmQuestCircle(G)

proc/RmQuestAgoText(list/when)
	var/s = RemasterSince(when)
	if(isnull(s)) return ""
	s = round(s / 10)
	if(s < 60) return "last seen just now"
	var/n
	if(s < 3600)
		n = round(s / 60)
		return "last seen [n] minute[n == 1 ? "" : "s"] ago"
	if(s < 86400)
		n = round(s / 3600)
		return "last seen [n] hour[n == 1 ? "" : "s"] ago"
	n = round(s / 86400)
	return "last seen [n] day[n == 1 ? "" : "s"] ago"

// Where a quest with a target is about, as a tile (for rewards paid with no board).
proc/RmQuestSpot(list/Q)
	var/list/G = Q["target"]
	if(G && G["x"]) return locate(G["x"], G["y"], G["z"])
	var/list/B = Q["board"]
	return locate(B[1], B[2], B[3])

// The words a taker reads on taking it.
proc/RmQuestHowText(list/Q)
	var/list/G = Q["target"]
	switch(Q["kind"])
		if("slay") return "Its marker shows where it was last seen, and follows it while your people see it."
		if("hunt") return "[Q["goal"]]: wild ones, by your people."
		if("fort") return "Bring a party of up to [RM_FORT_PARTY_MAX] to the way in (the marker) and start a try from this card[Q["fee"] ? ": [Q["fee"]] coins to go in" : ""]."
		if("clear") return "Clear [G["what"]]: go down with your people and kill [G["lair"] ? "its beast" : "everything in it"]."
		if("reach") return "Get one of your people to [G["what"]]."
		if("work") return "Your builders lay its blocks with your own [Q["mat"] == "wood" ? "logs" : "stone"]. It is on your job board."
	return "Bring [Q["need"]] [Q["itemName"]] to [Q["house"]]'s notice board."

// --- picking the target while posting -------------------------------------------------------------------------------
Player/proc/RmQuestPickStart(what)
	rm_quest_pick = (what in list("thing", "mouth", "place", "fortarea", "fortdoor", "fortgoal", "fortchamp")) ? what : null
	if(copytext(rm_quest_pick, 1, 5) == "fort")   // a fort's site (QuestForts.dm)
		rm_fort_corner = null
		RemasterNotice(rm_quest_pick == "fortarea" ? "Click one corner of your fort's area, then the opposite corner." : (rm_quest_pick == "fortdoor" ? "Click the way into your fort." : (rm_quest_pick == "fortgoal" ? "Click where the chest goes." : "Click your champion: one of your people inside the fort.")))
		return
	if(rm_quest_pick == "thing") RemasterNotice("Click the creature in the world. Right-click or Esc stops.")
	else if(rm_quest_pick == "mouth") RemasterNotice("Click the cave mouth or lair, in the world or on the world map. Right-click or Esc stops.")
	else if(rm_quest_pick) RemasterNotice("Click the place, in the world or on the world map. Right-click or Esc stops.")

// A click while picking: in 3D (the page's "pick3d", resolved as a 3D click is: in reach, and in sight) or on the world
// map (explored land only). What it picked goes on the post form.
Player/proc/RmQuestPickClick(atom/A)
	if(!rm_quest_pick) return 0
	var/atom/T = A
	while(T && !isturf(T)) T = T.loc
	if(!T) return 1
	if(copytext(rm_quest_pick, 1, 5) == "fort") return RmFortPickClick(A, T)   // QuestForts.dm
	switch(rm_quest_pick)
		if("thing")
			var/mob/Monsters/M = istype(A, /mob/Monsters) ? A : null
			if(!M) for(var/mob/Monsters/X in T) if(!istype(X.Owner, /Player) && RmFogSeesMob(X))
				M = X
				break
			if(!M)
				RemasterNotice("Click a creature: that was the ground.")
				return 1
			if(istype(M.Owner, /Player))
				RemasterNotice("Only wild creatures and beasts: another realm's people are for war, not notices.")
				return 1
			if(M.z == RM_CAVE_Z)
				RemasterNotice("A cave's creatures are gone when the cave is. Post a Clear notice for the cave instead.")
				return 1
			if(M.Egg)
				RemasterNotice("That is an egg.")
				return 1
			rm_quest_picked = list("kind"="thing", "ref"="\ref[M]", "what"=RemasterCombatName(M), "x"=M.x, "y"=M.y, "z"=M.z)
		if("mouth")
			var/obj/RemasterCaveMouth/O = istype(A, /obj/RemasterCaveMouth) ? A : RmQuestMouthNear(T, 2)
			if(!O)
				RemasterNotice("No cave mouth or lair there.")
				return 1
			rm_quest_picked = list("kind"="mouth", "mouth"="[O.x],[O.y],[O.z]", "what"=RemasterCaveMouthName(O), "x"=O.x, "y"=O.y, "z"=O.z)
		else
			rm_quest_picked = list("kind"="place", "x"=T.x, "y"=T.y, "z"=T.z, "what"="a spot")
	rm_quest_pick = null
	remaster_hud_tab = "quests"
	RemasterNotice("Picked: [rm_quest_picked["what"]].")
	return 1

// The world map's click: explored land only (the map shows nothing else).
Player/proc/RmQuestPickAt(x, y, zz)
	var/turf/T = locate(x, y, zz)
	if(!T || !rm_quest_pick) return 0
	if(rm_quest_pick == "thing" || rm_quest_pick == "fortchamp")
		RemasterNotice("Pick that in the world, where your people can see it, not on the map.")
		return 1
	if(RmFogOn(zz) && !RmQuestMapSeen(x, y, zz))
		RemasterNotice("Your people haven't been there.")
		return 1
	return RmQuestPickClick(T)

// The world map paints a 4x4 cell once any of its tiles was seen (Explore.dm RemasterWorldMapChunks): a click on it counts.
Player/proc/RmQuestMapSeen(x, y, zz)
	var/x0 = x - ((x - 1) % 4)
	var/y0 = y - ((y - 1) % 4)
	for(var/yy = y0, yy < y0 + 4, yy++)
		for(var/xx = x0, xx < x0 + 4, xx++)
			if(RemasterIsExplored(xx, yy, zz)) return 1
	return 0

// --- posting: the target, checked; nothing changes until the notice is up (RmQuestTargetPut) ----------------------------
// A = the post form; returns list(target, need, goal, title, ...) or the reason it can't be posted.
Player/proc/RmQuestPostTarget(list/A, kind)
	var/exact = (A["exact"] in list("exact", "circle", "words")) ? A["exact"] : "exact"
	var/list/K = rm_quest_picked
	var/list/G
	switch(kind)
		if("slay")
			var/mob/Monsters/M = (K && K["kind"] == "thing") ? locate(K["ref"]) : null
			if(!istype(M) || Rm3DGone(M) || M.HP <= 0 || M.GoingToDie || !isturf(M.loc) || istype(M.Owner, /Player) || M.z == RM_CAVE_Z)
				return "Pick the creature it is about: Pick in the world, then click it."
			if(!RmFogSeesMob(M)) return "Your people must see it when you post."
			var/what = RemasterCombatName(M)
			G = list("kind"="thing", "type"="[M.type]", "what"="the [what]", "race"=M.Race, "exact"=exact)
			G["tag"] = RmQuestTag(M)
			RmQuestSeen(G, M)
			return list("target"=G, "need"=1, "goal"="Slay the [what]", "title"="Slay the [what]")
		if("hunt")
			var/race = "[A["race"]]"
			var/list/names = rm_quest_hunt_kinds[race]
			if(!names) return "Pick the kind of creature."
			var/n = clamp(round(text2num("[A["need"]]") || 0), 1, RM_QUEST_HUNT_MAX)
			G = list("kind"="kind", "race"=race, "what"=(n == 1 ? "a [names[1]]" : names[2]), "exact"=exact)
			if(K && K["kind"] == "place") RmQuestPlacePut(G, K, A)   // a hint: where they are
			return list("target"=G, "need"=n, "goal"="Kill [n] [n == 1 ? names[1] : names[2]]", "title"="Hunt [n] [n == 1 ? names[1] : names[2]]")
		if("clear")
			var/obj/RemasterCaveMouth/O = (K && K["kind"] == "mouth") ? RmQuestMouth(K["mouth"]) : null
			if(!O) return "Pick the cave mouth or lair it is about: Pick in the world, then click it."
			if(O.owner_key) return "That is a player's own lair."
			var/lair = RemasterLairKind(O)
			if(lair)
				var/list/LS = RemasterLairState(O)
				if(LS["cleared"]) return "That lair is cleared already."
			var/list/TH = rm_cave_themes[O.theme]
			var/what = "the [TH[1]]"
			G = list("kind"="thing", "mouth"="[O.x],[O.y],[O.z]", "what"=what, "x"=O.x, "y"=O.y, "z"=O.z, "exact"=exact, "lair"=(lair ? 1 : 0))
			RmQuestCircle(G)
			return list("target"=G, "need"=1, "goal"="Clear [what]", "title"="Clear [what]")
		if("reach")
			if(!K || K["kind"] != "place") return "Pick the place: Pick in the world or on the world map, then click it."
			var/what = RmQuestText(A["place"], 30)
			if(!length(what)) what = "the marked place"
			G = list("kind"="place", "what"=what, "exact"=exact)
			RmQuestPlacePut(G, K, A)
			return list("target"=G, "need"=1, "goal"="Reach [what]", "title"="Reach [what]")
		if("fort")
			return RmFortPostTarget(A)   // QuestForts.dm
		if("work")
			var/list/Z = RmJz("[A["row"]]")
			if(!Z || Z["kind"] != "build") return "Pick one of your build plans (marked in Plan mode)."
			if(Z["quest"]) return "That plan is on a notice already."
			var/list/C = list()
			for(var/c in Z["cells"])
				var/list/q = RmPlanCell(c)
				if(q && !RemasterBlockThere(q[1], q[2])) C += c
			if(!length(C)) return "That plan has nothing left to build."
			if(length(C) > RM_QUEST_WORK_MAX) return "That plan has [length(C)] blocks to lay; a work notice takes at most [RM_QUEST_WORK_MAX]. Mark a smaller plan."
			var/x0 = world.maxx
			var/y0 = world.maxy
			var/x1 = 0
			var/y1 = 0
			var/list/cols = list()
			for(var/c in C)
				var/list/p = splittext(c, ",")
				var/x = text2num(p[1])
				var/y = text2num(p[2])
				x0 = min(x0, x); y0 = min(y0, y); x1 = max(x1, x); y1 = max(y1, y)
				cols["[x],[y]"] = 1
			var/mat = RmPlanWood(Z) ? "wood" : "stone"
			G = list("kind"="place", "x"=round((x0 + x1) / 2), "y"=round((y0 + y1) / 2), "z"=GROUND_LAYER, "r"=max(1, -round(-max(x1 - x0, y1 - y0) / 2)),
				"what"="[RemasterHouse()]'s [Z["name"]]", "exact"="exact")
			return list("target"=G, "need"=length(C), "goal"="Lay [length(C)] block[length(C) == 1 ? "" : "s"] of [mat == "wood" ? "logs" : "stone"] on [RemasterHouse()]'s plan",
				"title"="Help build [Z["name"]]", "cells"=C, "cols"=cols, "mat"=mat, "row"=Z["id"])
	return null

proc/RmQuestPlacePut(list/G, list/K, list/A)
	G["x"] = K["x"]
	G["y"] = K["y"]
	G["z"] = K["z"]
	G["r"] = clamp(round(text2num("[A["radius"]]") || 2), 0, RM_QUEST_PLACE_MAX)
	RmQuestCircle(G)

// The notice is up: its target on the record; a work notice's plan waits for its taker.
Player/proc/RmQuestTargetPut(list/Q, list/TG)
	Q["target"] = TG["target"]
	Q["goal"] = TG["goal"]
	if(Q["kind"] == "work")
		Q["cells"] = TG["cells"]
		Q["cols"] = TG["cols"]
		Q["mat"] = TG["mat"]
		Q["row"] = TG["row"]
		var/list/Z = RmJz(TG["row"])
		if(Z)
			Z["quest"] = Q["id"]
			Z["qrole"] = "maker"
			Z["paused"] = 1
	if(Q["kind"] == "fort")
		RmFortPut(Q, TG)   // QuestForts.dm
		rm_fort_picked = null
	rm_quest_picked = null

// --- the hooks ----------------------------------------------------------------------------------------------------------
// Every real attack (Defense.dm RemasterThreatenedBy): who struck it, while quests count deaths.
proc/RmQuestStruck(mob/Monsters/V, mob/Monsters/E)
	if(!istype(V) || !istype(E) || V.Owner == E.Owner || !istype(E.Owner, /Player)) return
	V.rm_qhit_key = E.Owner:key
	V.rm_qhit_by = E
	V.rm_qhit_at = world.time

// A death (Death.dm): a quarry, a hunted kind, the last of a cave.
proc/RmQuestDied(mob/Monsters/M)
	if((!M.rm_qtag && !rm_quest_hunting) || M.rm_qdead) return
	M.rm_qdead = 1
	var/key
	var/mob/Monsters/by
	if(M.rm_qhit_key && world.time - M.rm_qhit_at <= RM_QUEST_HIT_KEEP)
		key = M.rm_qhit_key
		by = M.rm_qhit_by
	else if(ismob(M.Killer))
		var/mob/K = M.Killer
		if(istype(K.Owner, /Player))
			key = K.Owner:key
			by = K
	if(M.rm_qtag)
		var/tag = M.rm_qtag
		M.rm_qtag = null
		rm_quest_things -= tag
		var/list/ids = rm_quest_by_tag[tag]
		if(ids) for(var/id in ids.Copy())
			var/list/Q = rm_quests[id]
			if(!RmQuestLive(Q)) continue
			if(key && Q["takers"][key]) RmQuestDone(Q, key, by)
			else RmQuestEnd(Q, key ? "someone else slew its quarry" : "its quarry died")
	if(key && !istype(M.Owner, /Player))
		var/list/ids = rm_quest_hunt_by[key]
		if(ids) for(var/id in ids.Copy())
			var/list/Q = rm_quests[id]
			if(!RmQuestLive(Q)) continue
			var/list/G = Q["target"]
			var/list/T = Q["takers"][key]
			if(!T || G["race"] != M.Race) continue
			T["got"]++
			rm_quest_ver++   // a count: the HUD's answers move, the indexes don't
			if(T["got"] >= Q["need"]) RmQuestDone(Q, key, by)
	if(M.z == RM_CAVE_Z && length(rm_quest_clear_at)) RmQuestCaveDeath(M, by)

// A cave is cleared: its lair's beast dead, or (a cave) every creature of this visit dead. It counts for the party's
// player, whoever struck the last blow; a lair cleared by anyone else takes its notices down.
proc/RmQuestCaveDeath(mob/Monsters/M, mob/Monsters/by)
	var/datum/rm_cave/C = RemasterCaveAt(M.loc)
	if(!C || !C.mouth) return
	var/list/ids = rm_quest_clear_at["[C.mouth.x],[C.mouth.y],[C.mouth.z]"]
	if(!length(ids)) return
	var/lair = RemasterLairKind(C.mouth)
	if(lair)
		if(M != C.boss) return
	else
		for(var/E in C.monsters)
			if(E == M || Rm3DGone(E)) continue
			var/mob/Monsters/X = E
			if(X.HP > 0 && !X.GoingToDie && RemasterCaveAt(X.loc) == C) return   // not cleared yet
	var/doer = C.owner_key
	if(!istype(by) || Rm3DGone(by) || !istype(by.Owner, /Player) || by.Owner:key != doer)
		by = null
		for(var/U in C.party) if(!Rm3DGone(U) && U:HP > 0)
			by = U
			break
	for(var/id in ids.Copy())
		var/list/Q = rm_quests[id]
		if(!RmQuestLive(Q)) continue
		if(Q["takers"][doer]) RmQuestDone(Q, doer, by)
		else if(lair) RmQuestEnd(Q, "someone else cleared it")

// Reach: one of this player's people inside a place they were sent to (RemasterTrack, once a second).
Player/proc/RmQuestReachTick()
	var/list/ids = rm_quest_reach_by[key]
	if(!ids || world.time < rm_quest_reach_at) return
	rm_quest_reach_at = world.time + 10
	for(var/id in ids.Copy())
		var/list/Q = rm_quests[id]
		if(!RmQuestLive(Q)) continue
		var/list/G = Q["target"]
		var/r = G["r"] || 0
		var/mob/Monsters/hit
		for(var/zz in RmQuestLayers(G["z"]))
			var/turf/C = locate(G["x"], G["y"], zz)
			if(!C) continue
			for(var/mob/Monsters/M in range(r, C)) if(M.Owner == src && M.HP > 0 && !M.GoingToDie)
				var/dx = M.x - C.x
				var/dy = M.y - C.y
				if(dx * dx + dy * dy <= r * r + 1)
					hit = M
					break
			if(hit) break
		if(hit) RmQuestDone(Q, key, hit)

// Work: a block laid (Plans.dm RmPlanLayTick) by a taker's builder on their work plan, on one of the notice's blocks.
proc/RmQuestLaid(mob/Monsters/W, turf/T, k)
	var/Player/P = W.Owner
	if(!istype(P) || !W.rm_jz_id) return
	var/list/Z = P.RmJz(W.rm_jz_id)
	if(!Z || Z["qrole"] != "taker") return
	var/list/Q = rm_quests[Z["quest"]]
	if(!RmQuestLive(Q)) return
	var/list/TK = Q["takers"][P.key]
	var/c = "[T.x],[T.y],[k]"
	if(!TK || !(c in Q["cells"])) return
	T.remaster_laid_by = RemasterRootKey(Q["maker"])   // the maker's wall, as if their own folk had laid it
	Q["cells"] -= c
	TK["got"]++
	rm_quest_ver++   // a count: the HUD's answers move, the indexes don't
	if(!RmQuestWorkPrune(Q)) RmQuestDone(Q, P.key, W)

// A work notice's blocks still to lay (those laid by anyone are dropped).
proc/RmQuestWorkPrune(list/Q)
	var/list/C = Q["cells"]
	if(!islist(C)) return 0
	for(var/i = length(C), i >= 1, i--)
		var/list/q = RmPlanCell(C[i])
		if(!q || RemasterBlockThere(q[1], q[2])) C.Cut(i, i + 1)
	return length(C)

// Whether P's builders may lay on T though its floor is someone else's: T is a block of a work notice P took.
proc/RmQuestWorkLets(Player/P, turf/T)
	if(!rm_quest_working || !istype(P) || !P.rm_quest_log) return 0
	var/c = "[T.x],[T.y]"
	for(var/id in P.rm_quest_log)
		var/list/Q = rm_quests[id]
		if(Q && Q["kind"] == "work" && Q["takers"][P.key] && Q["cols"] && Q["cols"][c]) return 1
	return 0

// Taking a work notice: a build plan of the taker's own over the maker's blocks still to lay, on their job board.
Player/proc/RmQuestWorkStart(list/Q)
	var/list/C = list()
	for(var/c in Q["cells"])
		var/list/q = RmPlanCell(c)
		if(q && !RemasterBlockThere(q[1], q[2])) C += c
	if(!length(C)) return null
	var/list/Z = RmPlanAdd(jointext(C, "/"), 2, "build", Q["mat"] || "stone")
	if(!Z) return null
	Z["quest"] = Q["id"]
	Z["qrole"] = "taker"
	Z["name"] = "Work for [Q["house"]]"
	return Z

// A player's job board rows that belong to work notices, put right: a taker's row goes when they no longer hold the
// notice; a maker's row works again once the notice is closed. At log-in too (the change may have come while away).
Player/proc/RmQuestWorkRows()
	if(!rm_jz) return
	for(var/list/Z in rm_jz.Copy()) if(Z["quest"])
		var/list/Q = rm_quests[Z["quest"]]
		var/live = RmQuestLive(Q)
		if(Z["qrole"] == "taker")
			if(!live || !Q["takers"][key]) RmJzRemove(Z)
		else if(!live)
			Z -= "quest"
			Z -= "qrole"
			Z["paused"] = 0

// Finished by an event: the reward to the taker (into the pack of the one who did it).
proc/RmQuestDone(list/Q, key, mob/Monsters/by)
	if(!RmQuestLive(Q) || !Q["takers"][key]) return 0
	var/Player/P = RemasterPlayerByKey(key)
	if(by && (!P || Rm3DGone(by) || by.Owner != P)) by = null
	if(P && !by) for(var/mob/Monsters/U in P.UnitList) if(U.Owner == P && U.HP > 0 && isturf(U.loc))
		by = U
		break
	RmQuestFinish(Q, P, by, RmQuestBoardAt(Q["board"]), key)
	return 1

// When a notice with a target closes for good.
proc/RmQuestTargetEnd(list/Q)
	if(Q["kind"] == "fort") RmFortClosed(Q)   // its try called off, its chest gone (QuestForts.dm)
	if(Q["kind"] != "work") return
	for(var/k in list(Q["maker"]) + Q["takers"])
		var/Player/P = RemasterPlayerByKey(k)
		if(P) P.RmQuestWorkRows()

// Every 30 s (RmQuestTick): a quarry gone (found again after a restart), a lair cleared by someone else, a work notice's
// blocks all in.
proc/RmQuestTargetsTick()
	for(var/id in rm_quests)
		var/list/Q = rm_quests[id]
		if(!Q["target"] || !RmQuestLive(Q)) continue
		var/list/G = Q["target"]
		switch(Q["kind"])
			if("slay")
				if(!RmQuestThing(G) && !RmQuestRebind(G)) RmQuestEnd(Q, "its quarry is gone")
			if("clear")
				var/obj/RemasterCaveMouth/O = RmQuestMouth(G["mouth"])
				if(!O) RmQuestEnd(Q, "the cave is gone")
				else if(RemasterLairKind(O))
					var/list/LS = RemasterLairState(O)
					if(LS["cleared"]) RmQuestEnd(Q, "someone else cleared it")
			if("fort")
				RmFortPlaceChest(Q)   // after a restart (mobs aren't saved with the world)
			if("work")
				if(!RmQuestWorkPrune(Q))
					var/doer
					for(var/k in Q["takers"]) if(Q["takers"][k]["got"]) doer = k
					if(doer) RmQuestDone(Q, doer)
					else RmQuestEnd(Q, "its blocks are all in")

// --- markers: for each viewer, the quests they made, took or read ----------------------------------------------------
// [id, title, kind, how (own, taken, read), x, y, z, r, now (seen now), ago, ref (the 3D thing it follows), what]
// Built again on a change, and once a second while one follows a quarry.
Player/proc/RmQuestMarksData()
	var/k = "[rm_quest_ver]|[length(rm_quest_read)]|[length(rm_quest_log)]"
	if(k == rm_quest_marks_key && (!rm_quest_marks_live || world.time < rm_quest_marks_at)) return rm_quest_marks
	rm_quest_marks_key = k
	rm_quest_marks_at = world.time + 10
	rm_quest_marks_live = 0
	var/list/how = list()
	for(var/id in rm_quest_by_maker[key]) how[id] = "own"
	for(var/id in rm_quest_log)
		var/list/E = rm_quest_log[id]
		if(E["state"] == "taken") how[id] = "taken"
	for(var/id in rm_quest_read) if(!how[id]) how[id] = "read"
	var/list/L = list()
	for(var/id in how)
		if(length(L) >= RM_QUEST_MARKS) break
		var/list/Q = rm_quests[id]
		if(!Q || !Q["target"] || !RmQuestLive(Q)) continue
		if(Q["kind"] == "slay") rm_quest_marks_live = 1
		var/list/R = RmQuestMarkRow(Q, how[id])
		if(R) L += list(R)
	rm_quest_marks = length(L) ? L : null
	return rm_quest_marks

Player/proc/RmQuestMarkRow(list/Q, how)
	var/list/G = Q["target"]
	if(Q["secret"] && how != "own" && RmQuestAfterWhy(Q, src)) return null   // a chain's secret step (QuestChains.dm)
	var/x = G["x"]
	var/y = G["y"]
	var/zz = G["z"]
	var/r = G["r"] || 0
	var/now = 0
	var/ago = ""
	var/ref
	if(Q["kind"] == "slay")
		var/mob/Monsters/M = RmQuestThing(G)
		var/atom/T = M ? M.loc : null
		while(T && !isturf(T)) T = T.loc
		if(T && RmFogSeesMob(M))
			now = 1
			x = T.x
			y = T.y
			zz = T.z
			r = 0
			ref = "\ref[M]"
			if(how != "read") RmQuestSeen(G, M)
		else ago = RmQuestAgoText(G["seen"])
	if(!now && how != "own")
		if(G["exact"] == "words") return null
		if(G["exact"] == "circle" && !isnull(G["cx"]))
			x = G["cx"]
			y = G["cy"]
			r = max(r, RM_QUEST_CIRCLE)
	if(!x) return null
	return list("id"=Q["id"], "title"=Q["title"], "kind"=Q["kind"], "how"=how, "x"=x, "y"=y, "z"=zz, "r"=r, "now"=now, "ago"=ago, "ref"=ref, "what"=G["what"])

// The card's line about the target, for this viewer.
Player/proc/RmQuestTargetLine(list/Q)
	var/list/G = Q["target"]
	if(!G) return null
	if(!RmQuestLive(Q)) return ""
	if(Q["secret"] && Q["maker"] != key && RmQuestAfterWhy(Q, src)) return "Secret until the step before is done"
	var/list/R = RmQuestMarkRow(Q, Q["maker"] == key ? "own" : "read")
	if(G["kind"] == "kind") return R ? "Anywhere; they are said to be about the marked circle" : "Anywhere"
	if(!R) return "Only their words say where"
	if(R["now"]) return "In sight now"
	if(Q["kind"] == "slay") return "[G["exact"] == "circle" && Q["maker"] != key ? "Somewhere about the marked circle" : "At the marker"], [R["ago"]]"
	if(G["exact"] == "circle" && Q["maker"] != key) return "Somewhere about the marked circle"
	return "At the marker"
