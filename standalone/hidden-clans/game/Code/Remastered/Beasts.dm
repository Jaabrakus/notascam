// Huge animated beasts in the 3D view: dragons and spiders drawn from 3D-rendered sprite
// packs (art/enhance/beasts64.py; BeastData.dm says how to cut them), in 8 facings and
// animated by what they are doing. The page picks the facing nearest the camera's view and
// plays the frames. The old small sprite is never drawn for a living beast in 3D: until a
// picture arrives the page keeps the last one it drew (the first time, only the shadow).

proc/RmBeastKind(mob/Monsters/M)
	if(!istype(M) || M.HP <= 0) return null   // dead: the old corpse picture
	if(M.Race == "Dragon") return "dragon"
	if(M.Race == "Spider") return "spider"
	if(M.Race == "Golem") return "golem"   // a stone golem (Golems.dm)

proc/RmBeastVariant(mob/Monsters/M, kind)
	var/list/V = rm_beasts[kind]["variants"]
	if(kind == "dragon")   // its colour, as dragons.dmi names it ("flyingred" while flying)
		var/s = "[M.icon_state]"
		if(copytext(s, 1, 7) == "flying") s = copytext(s, 7)
		return (s in V) ? s : V[1]
	var/c = lowertext("[M.SubRace]")   // a spider's caste
	return (c in V) ? c : V[1]

// Size 1 draws an atlas pixel as 1/RM_BEAST_PPT of a tile. A grown dragon is drawn about
// thirteen tiles from snout to tail, bigger than any spider and dwarfing the people round it;
// a hatchling is the size of a horse and grows every year until it is grown at 50 (when a
// female can lay eggs). Spiders grow with age; queens are the biggest.
proc/RmBeastSize(mob/Monsters/M, kind)
	if(kind == "golem") return 2.5   // Golems.dm RM_GOLEM_SIZE: huge
	if(kind != "spider") return round(0.9 + 1.5 * min(1, max(0, M.Age) / 50), 0.01)
	var/f = lowertext("[M.icon]")
	. = findtext(f, "mature") ? 2.4 : findtext(f, "older") ? 1.7 : 1.2
	if(M.SubRace == "Queen") . *= 1.25
	else if(M.SubRace == "Warrior") . *= 1.1
	return round(., 0.01)

proc/RmBeastAnim(mob/Monsters/M, kind)
	var/list/A = rm_beasts[kind]["anims"]
	var/breath = M.FirePoints || M.IcePoints   // fire and frost dragons breathe on what they fight
	if(M.Flying && ("fly" in A))
		if(Remaster3DAct(M) == "attack" && breath && ("flybreathe" in A)) return "flybreathe"
		return "fly"
	if(Remaster3DAct(M) == "attack")
		if(("breathe" in A) && breath) return "breathe"
		return "attack"
	return "idle"   // the page walks it while it moves

// What the page needs to draw one beast, or null. Sends this player the beast's variant's
// pictures the first time it is seen.
Player/proc/RmBeast3D(mob/Monsters/M)
	var/kind = RmBeastKind(M)
	if(!kind) return null
	var/variant = RmBeastVariant(M, kind)
	var/list/A = rm_beasts[kind]["anims"]
	RmBeastSend(kind, variant)
	var/anim = RmBeastAnim(M, kind)
	var/list/tame = M.rm_bound ? list("bound"=(M.rm_bound == src ? 2 : 1), "trust"=M.rm_trust, "feeds"=rm_tame_feeds, "chains"=M.rm_bound_chains) : null   // Taming.dm
	// take-off and landing are played once by the page as the beast rises or comes down; "air"
	// is its flying, still drawn while it comes down from on high
	var/size = RmBeastSize(M, kind)
	// where its jaws are: how far ahead of where it stands at the strike (measured on the attack's
	// frames in profile, as a part of its half-width) and how high (a part of its height)
	var/list/K = A["attack"]
	var/jaw = round((kind == "dragon" ? 0.48 : 0.55) * K[3] / 2 * size / RM_BEAST_PPT, 0.01)
	var/mouth = round((kind == "dragon" ? 0.3 : 0.15) * K[6] * size / RM_BEAST_PPT, 0.01)
	. = list("kind"=kind, "variant"=variant, "anim"=anim, "meta"=A[anim], "walk"=A["walk"],
		"takeoff"=A["takeoff"], "land"=A["land"], "air"=A["fly"], "size"=size, "ppt"=RM_BEAST_PPT, "fly"=(M.Flying ? 1 : 0),
		"jaw"=jaw, "mouth"=mouth, "mouths"=rm_beast_mouths[kind], "brm"=A["breathe"], "fbrm"=A["flybreathe"])
	for(var/k in tame) .[k] = tame[k]
	if(length(M.rm_feet))   // its parts, for the page's right-click menu ("Attack its left wing")
		var/list/parts = list()
		for(var/obj/RmBeastFoot/F in M.rm_feet) if(isturf(F.loc)) parts += list(list(F.x, F.y, F.part, RmPartHealth(M, F.part)))
		.["parts"] = parts
	if(M.HasWings) .["wings"] = RmPartHealth(M, "wing")   // in the air the menu offers only its wings
	// fighting: where its foe stands, so the page draws it stood back with its jaws on the foe
	// fighting: where its foe stands, so the page turns it to its foe all through the fight (its jaws reach it: RmJawStrike)
	var/mob/T = (ismob(M.Target) && get_dist(M, M.Target) <= 2 && RemasterHostile(M, M.Target)) ? M.Target : ((ismob(M.destination) && get_dist(M, M.destination) <= 1) ? M.destination : null)
	if(T && (!M.Flying || (anim in list("attack", "breathe", "flybreathe"))))
		.["tx"] = T.x
		.["ty"] = T.y
		if(anim in list("breathe", "flybreathe")) .["breath"] = M:RemasterBreathLook()   // what it breathes: the page's particles (Specials.dm)

Player/proc/RmBeastSend(kind, variant)
	if(!remaster_3d_sent) remaster_3d_sent = list()
	if(remaster_3d_sent["rb-[kind]-[variant]"]) return
	remaster_3d_sent["rb-[kind]-[variant]"] = 1
	for(var/anim in rm_beasts[kind]["anims"])
		for(var/f in rm_beast_facings)
			var/name = "rb-[kind]-[variant]-[anim]-[f].png"
			if(remaster_3d_sent[name]) continue
			remaster_3d_sent[name] = 1
			src << browse_rsc(file("Icons/Remastered/Beasts/[kind]/[variant]/[anim]-[f].png"), name)
	var/breath = "rb-breath-[kind].png"   // its breath: the magic weapons' particles (art/enhance/breath64.py)
	if(kind == "dragon" && !remaster_3d_sent[breath])
		remaster_3d_sent[breath] = 1
		src << browse_rsc(file("Icons/Remastered/Fx/breath.png"), breath)

// The fire particles alone, for burning ground (the page draws its flames with them).
Player/proc/RmSendFireFx()
	var/kind = "dragon"
	var/breath = "rb-breath-[kind].png"
	if(remaster_3d_sent[breath]) return
	remaster_3d_sent[breath] = 1
	src << browse_rsc(file("Icons/Remastered/Fx/breath.png"), breath)

// --- A dead beast ----------------------------------------------------------------------
// Its body (Death.dm MakeBody: the old sprite turned on its side) keeps the beast's picture
// in 3D: the pack's death, played once as it falls, then held - lying where it fell.
mob/Body/var/list/rm_beast        // kind, variant, size (saved with the body)
mob/Body/var/tmp/rm_beast_died    // world.time it fell (a body from a save has lain long)

mob/Monsters/CarryPartStats(atom/movable/PART)
	. = ..()
	var/kind = Race == "Dragon" ? "dragon" : Race == "Spider" ? "spider" : null
	if(istype(PART, /mob/Body) && kind && rm_beasts[kind]["anims"]["death"])
		var/mob/Body/B = PART
		B.rm_beast = list(kind, RmBeastVariant(src, kind), RmBeastSize(src, kind))
		B.rm_beast_died = world.time
		B.dir = dir

Player/proc/RmBeastCorpse3D(mob/Body/B)
	var/list/C = B.rm_beast
	if(!C || !rm_beasts[C[1]]) return null
	var/list/A = rm_beasts[C[1]]["anims"]
	if(!A["death"]) return null
	RmBeastSend(C[1], C[2])
	return list("kind"=C[1], "variant"=C[2], "anim"="death", "meta"=A["death"], "size"=C[3], "ppt"=RM_BEAST_PPT, "fly"=0, "dead"=1,
		"since"=isnull(B.rm_beast_died) ? 600 : round((world.time - B.rm_beast_died) / 10, 0.1))

// --- Its jaws' reach -------------------------------------------------------------------
// A great beast on the ground fights from where its head is, not with its foe under its chest: a grown
// dragon (or a great spider queen) bites and breathes, as it fights, at a foe two tiles off, standing still
// and turned to it, so the 3D view draws its jaws on its foe without moving it off its tile. One right
// under it, it steps back from first. RmJawStrike is 0 for anyone else (they fight as they always have).
mob/Monsters/var/tmp/rm_backing = 0

proc/RmJawReach(mob/Monsters/M)
	var/kind = RmBeastKind(M)
	if(!kind || M.Flying) return 1
	return clamp(round(RmBeastSize(M, kind) * (kind == "dragon" ? 0.85 : 0.6)), 1, 2)

mob/Monsters/proc/RmJawStrike(mob/Monsters/E)
	if(!E || E.z != z || RmJawReach(src) < 2) return 0
	var/d = get_dist(src, E)
	if(d > 2 || (d == 2 && !(E in oview(2, src)))) return 0
	destination = null
	Target = E
	if(d <= 1)   // right under it: a step back first, if there is room
		rm_backing = 1
		var/stepped = step(src, get_dir(E, src))
		rm_backing = 0
		if(stepped)
			dir = get_dir(src, E)
			return 1
	dir = get_dir(src, E)
	RemasterStrike(E, "reach")
	return 1

// --- How much room a beast takes -------------------------------------------------------
// Its parts hold the ground under them: invisible blockers, dense to everyone but the beast -
// a dragon's legs, head and wings, a spider's eight legs and head - set out by its size and
// the way it faces, so others walk round it or between its legs, and fight it part by part
// (below). Flying, it holds none. Huge ones (size 2 and up) knock down the trees they walk
// into or put a foot on.

obj/RmBeastFoot
	density = 1
	invisibility = 101
	mouse_opacity = 0
	anchored = 1
	var/mob/Monsters/owner
	var/part   // which part of it stands here (RmBeastParts): what a blow struck here hits

// A foot still under its beast; one left behind goes.
proc/RmBeastFootStands(obj/RmBeastFoot/F)
	var/mob/Monsters/M = F.owner
	if(M && M.HP > 0 && !M.Flying && (F in M.rm_feet)) return 1
	spawn(0) del F
	return 0

obj/RmBeastFoot/Cross(atom/movable/A)
	if(!RmBeastFootStands(src)) return 1
	return A == owner || ..()

mob/Monsters/var/tmp/list/rm_feet

// Which tiles hold a foot (step-cost, 10-27): each tile counts the feet on it (rm_feet_n), kept as they are set down and
// taken up (RmBeastFootPut) and as they go (Del), and a unit's step looks for feet (Chains/Move.dm, step Beasts) only
// where there is one. rm_step_scan_check (Doors.dm) also looks on every tile that counts none (RmStepScanFeet).
turf/var/tmp/rm_feet_n = 0
obj/RmBeastFoot/var/tmp/turf/rm_foot_on   // the tile it is counted on
var/rm_scan_feet_skips = 0
var/rm_scan_feet_bad = 0

proc/RmBeastFootPut(obj/RmBeastFoot/F, turf/T)
	var/turf/O = F.rm_foot_on
	F.loc = T
	if(O == T)
		if(T && T.rm_feet_n < 1) RmBeastFootRecount(T)   // its tile's count lost (a tile made anew under it)
		return
	F.rm_foot_on = T
	if(T) T.rm_feet_n++
	if(O) O.rm_feet_n = max(0, O.rm_feet_n - 1)

proc/RmBeastFootRecount(turf/T)
	var/n = 0
	for(var/obj/RmBeastFoot/F in T) n++
	T.rm_feet_n = n

obj/RmBeastFoot/Del()
	var/turf/O = rm_foot_on
	rm_foot_on = null
	if(O) O.rm_feet_n = max(0, O.rm_feet_n - 1)
	return ..()

// rm_step_scan_check: a step that skipped the look on T (no foot counted there) looks after all.
proc/RmStepScanFeet(turf/T, mob/Monsters/M)
	rm_scan_feet_skips++
	var/n = 0
	var/stops = 0
	for(var/obj/RmBeastFoot/F in T)
		n++
		try
			var/mob/Monsters/B = F.owner
			if(B != M && B && B.HP > 0 && !B.Flying && (F in B.rm_feet)) stops = 1
		catch
			stops = 1
	if(!n) return
	rm_scan_feet_bad++
	world.log << "STEPSCAN|feet|[T.x],[T.y],[T.z]|[n] feet, none counted|the look would stop it: [stops]|[M]"

proc/RmBeastHuge(mob/Monsters/M)
	var/kind = RmBeastKind(M)
	return kind && RmBeastSize(M, kind) >= 2

// The tiles a beast holds, as (forward, side, part): side is to its right. A dragon's four legs
// (its forelegs are its arms, to the body's reckoning), its head in front of them and a wing out
// on either flank; a spider's eight legs, four a side splayed forward and back, and its head.
proc/RmBeastParts(kind, size)
	. = list()
	if(kind == "golem") return RmGolemParts()   // its two feet, 2 x 2 each (Golems.dm)
	if(kind == "dragon")
		var/f = max(1, round(size * 0.9))
		var/s = max(1, round(size * 0.45))
		return list(list(f, -s, "left foreleg"), list(f, s, "right foreleg"), list(-f, -s, "left hind leg"), list(-f, s, "right hind leg"),
			list(f + 1, 0, "head"), list(0, -s - 1, "left wing"), list(0, s + 1, "right wing"))
	var/r = max(1, size * 0.8)
	var/list/names = list("35"="foreleg", "75"="second leg", "105"="third leg", "145"="hind leg")
	for(var/a in list(35, 75, 105, 145))
		. += list(list(round(r * cos(a)), -round(r * sin(a)), "left [names["[a]"]]"), list(round(r * cos(a)), round(r * sin(a)), "right [names["[a]"]]"))
	. += list(list(max(1, round(r)) + 1, 0, "head"))

proc/RmBeastFeetClear(mob/Monsters/M)
	for(var/obj/RmBeastFoot/F in M.rm_feet) del F
	M.rm_feet = null

// Set the beast's parts where it now stands (and knock down the trees under a huge one's).
proc/RmBeastFeetUpdate(mob/Monsters/M)
	var/kind = RmBeastKind(M)
	if(!kind || M.Flying || !isturf(M.loc))
		if(M.rm_feet) RmBeastFeetClear(M)
		return
	var/dx = (M.dir & EAST ? 1 : 0) - (M.dir & WEST ? 1 : 0)
	var/dy = (M.dir & NORTH ? 1 : 0) - (M.dir & SOUTH ? 1 : 0)
	if(!dx && !dy) dy = -1
	var/huge = RmBeastHuge(M)
	if(huge)   // its body flattens the trees round it (a blocked unit steps aside at random, Creatures/Bump.dm, so it may never bump one)
		for(var/turf/T in range(1, M)) if(T.Tree && T.density) RmKnockDownTree(T, M)
	var/list/tiles = list()
	var/list/parts = list()
	for(var/list/o in RmBeastParts(kind, RmBeastSize(M, kind)))
		// forward along its facing, side across it
		var/turf/T = locate(M.x + round(o[1] * dx + o[2] * dy), M.y + round(o[1] * dy - o[2] * dx), M.z)
		if(!T || T == M.loc || (T in tiles)) continue
		if(huge && T.Tree && T.density) RmKnockDownTree(T, M)
		if(T.density) continue                                   // a leg over a wall or water
		var/blocked = 0
		for(var/atom/movable/A in T) if(A.density && !istype(A, /obj/RmBeastFoot)) blocked = 1
		if(blocked) continue
		tiles += T
		parts += o[3]
	var/list/feet = M.rm_feet || list()
	while(length(feet) > length(tiles))
		var/obj/RmBeastFoot/F = feet[length(feet)]
		feet.len--
		del F
	for(var/i = 1, i <= length(tiles), i++)
		var/obj/RmBeastFoot/F = i <= length(feet) ? feet[i] : null
		if(!F)
			F = new
			F.owner = M
			feet += F
		RmBeastFootPut(F, tiles[i])   // (its tile's count kept)
		F.part = parts[i]
	M.rm_feet = feet

// A tree knocked down: it falls away from the beast (Breaking.dm shows it in 3D) and the
// ground under it comes back as when a tree burns down (Verbs.dm), with a log or two.
proc/RmKnockDownTree(turf/T, mob/Monsters/M)
	RemasterWorkBlow(T, M, T.HP)
	T.overlays = null
	T.OnFire = 0
	T.IsWood = 0
	T.opacity = 0
	T.density = 0
	T.CanDigAt = 0
	T.Detailed = 0
	T.icon = 'Cave.dmi'
	T.Tree = 0
	T.icon_state = T.OIcon || "Grass"
	T.GoesTo = null
	new /obj/Items/woods/wood(T)
	if(prob(50)) new /obj/Items/woods/wood(T)
	if(T.z == GROUND_LAYER)   // a floor it held up in the sky above goes with it
		var/turf/TE = locate(T.x, T.y, SKY_LAYER)
		if(TE && TE.Supported == 1)
			TE.Supported = 0
			TE.icon_state = "DFloor"
			TE.name = "Floor"
			TE.density = 0
			TE.Detailed = 0
			if(TE.Content3 == "Peak")
				TE.icon = 'Cave.dmi'
				TE.icon_state = "Peak"
				TE.name = "MountainPeak"
			if(TE.Content == "Sky")
				TE.icon = 'Cave.dmi'
				TE.icon_state = "Sky"
				TE.name = "Sky"
	if(M && istype(M.Owner, /Player) && world.time - M.rm_tree_said > 300)
		M.rm_tree_said = world.time
		M.Owner << "[M] knocks down a tree."

mob/Monsters/var/tmp/rm_tree_said = -1000

// mob/Monsters/Move: this file's part is step RmChainMove_Beasts in Code/Remastered/Chains/Move.dm

mob/Monsters/var/tmp/rm_lame_said = 0
proc/RmBeastLegsMangled(mob/Monsters/M)
	if(M.Race != "Dragon" && M.Race != "Spider" && M.Race != "Golem") return 0
	. = 0
	for(var/v in list(M.LeftArmHP, M.RightArmHP, M.LeftLegHP, M.RightLegHP)) if(isnum(v) && v <= 10) .++

// A dragon breathing on its foe in a fight catches those beside the foe too: a lesser splash of
// its F breath (Specials.dm RemasterBreathBurn), at most every 2 s.
mob/Monsters/var/tmp/rm_splash_at = 0
mob/Monsters/RemasterStrike(mob/M, kind_hint)
	if(rm_bound) return 0   // chained down (Taming.dm)
	. = ..()
	if(!.) return   // no blow this time (Hits.dm swing timer)
	if(istype(M, /mob/Monsters)) RmWingCheck(M)   // its wings broke under the blow: down it comes
	if(Race != "Dragon" || !istype(M, /mob/Monsters) || world.time < rm_splash_at || !RmBeastKind(src)) return
	if(!(RmBeastAnim(src, "dragon") in list("breathe", "flybreathe"))) return
	rm_splash_at = world.time + 20
	var/list/area = list()
	for(var/turf/X in range(1, M)) if(!X.density && X != M.loc) area += X
	RemasterBreathBurn(area, RemasterBreathElement(), rand(4, 9) + RemasterLevelBonus() / 6, "breath", 0)   // the ground isn't set burning every blow

// mob/Monsters/Bump: this file's part is step RmChainBump_Beasts in Code/Remastered/Chains/Bump.dm

// mob/Monsters/Death: this file's part is step RmChainDeath_Beasts in Code/Remastered/Chains/Death.dm

mob/Monsters/Del()
	if(rm_feet) RmBeastFeetClear(src)
	return ..()

// --- Fighting a great beast part by part --------------------------------------------------
// A unit fighting a great beast on the ground strikes from beside one of its part tiles, on its
// own beat: the part it was sent at (right-click the beast in 3D: "Attack its left wing"), else
// the nearest. The blow lands on that part: a dragon's forelegs are its arms to the body's
// reckoning, its hind legs its legs, then its head and its wings. Arrows, thrown weapons and
// ballista bolts go to the part aimed at too, and at a beast in the air mostly find its wings.
// Wings broken ("Broken" and worse, Combats.dm) keep a beast on the ground, and one in the air
// crashes down; they mend slowly.

var/list/rm_beast_part_body = list("foreleg"="Arm", "second leg"="Arm", "third leg"="Leg", "hind leg"="Leg", "head"="Head", "wing"="Wings", "foot"="Leg")   // foot: a golem's (Golems.dm)

mob/Monsters/var/tmp
	mob/Monsters/rm_aim_beast   // the great beast it was sent at
	rm_aim_part                 // and which part of it
	rm_part_at = 0              // its next blow at a part

// A part in the body's reckoning: "LeftArm", "RightLeg", "Head", "Wings" (or null).
proc/RmPartBody(part)
	if(!part) return null
	for(var/k in rm_beast_part_body) if(findtext(part, k))
		var/b = rm_beast_part_body[k]
		if(b == "Arm" || b == "Leg") return "[findtext(part, "left") ? "Left" : "Right"][b]"
		return b

// How whole a part is, 0-100 (the pointer's tag and the right-click menu show it).
proc/RmPartHealth(mob/Monsters/M, part)
	var/b = RmPartBody(part)
	if(!b) return null
	if(b == "Wings") RmWingsReady(M)
	var/v = M.vars["[b]HP"]
	return isnum(v) ? max(0, min(100, round(100 * v / (M.OrganMaxHP || 100)))) : null

// The part tile a unit fights a great beast on the ground at: the one it was sent at, else the nearest.
proc/RmBeastPartFor(mob/Monsters/U, mob/Monsters/B)
	if(!istype(B) || B.Flying || !length(B.rm_feet)) return null
	var/obj/RmBeastFoot/best
	var/bd = 1#INF
	for(var/obj/RmBeastFoot/F in B.rm_feet)
		if(!isturf(F.loc)) continue
		if(U.rm_aim_beast == B && F.part == U.rm_aim_part) return F
		var/d = get_dist(U, F)
		if(d < bd)
			best = F
			bd = d
	return best

// From beside the part's tile (Attack.dm, Defense.dm): a blow at it on the unit's own beat.
mob/Monsters/proc/RmBeastStrikePart(mob/Monsters/B, obj/RmBeastFoot/F)
	destination = null
	dir = get_dir(src, F)
	if(world.time < rm_part_at) return
	rm_part_at = world.time + max(10, Delay * 3)
	rm_aim_beast = B
	rm_aim_part = F.part
	RemasterStrike(B)

// The part a blow, arrow or bolt from src at M is meant for, or null.
mob/proc/RmAimedPart(mob/Monsters/M, wings_chance)
	if(!istype(M) || !RmBeastKind(M)) return null
	if(istype(src, /mob/Monsters) && src:rm_aim_beast == M && src:rm_aim_part) return src:rm_aim_part
	if(M.Flying && M.HasWings && prob(wings_chance)) return "wing"

// Attack (Combats.dm) rolls where a blow lands; at a great beast it lands on the part aimed at
// (in melee at one low in the air, now and then its wings). Only the first blow in a tick: the
// original's wing wound strikes again (Attack's own ".()"), and that one rolls as the original does.
mob/var/tmp/rm_aim_tick = -1
mob/proc/RmAimFlags(mob/Monsters/M, dmg)
	var/b = rm_aim_tick == world.time ? null : RmPartBody(RmAimedPart(M, 40))
	if(b)
		rm_aim_tick = world.time
		HitHead = 0
		HitLeftArm = 0
		HitRightArm = 0
		HitLeftLeg = 0
		HitRightLeg = 0
		HitLowerBody = 0
		HitUpperBody = 0
		HitWings = 0
		switch(b)
			if("Head") HitHead = 1
			if("LeftArm") HitLeftArm = 1
			if("RightArm") HitRightArm = 1
			if("LeftLeg") HitLeftLeg = 1
			if("RightLeg") HitRightLeg = 1
			if("Wings")
				RmWingsReady(M)
				HitWings = 1
	// whatever the blow lands on (aimed or the original's roll), a great beast is crippled by it, never cut apart
	if(dmg && RmBeastKind(M))
		if(HitLeftArm) RmBeastLimbFloor(M, "LeftArmHP", dmg)
		if(HitRightArm) RmBeastLimbFloor(M, "RightArmHP", dmg)
		if(HitLeftLeg) RmBeastLimbFloor(M, "LeftLegHP", dmg)
		if(HitRightLeg) RmBeastLimbFloor(M, "RightLegHP", dmg)
		if(HitWings) RmBeastLimbFloor(M, "WingsHP", dmg, 10)

// A great beast's leg or wing about to take a wound of dmg: it is left at least `least`, so the
// original's "slashed off" (HP 0 or less) never happens to it - mangled, it limps or can't fly.
proc/RmBeastLimbFloor(mob/Monsters/M, hpvar, dmg, least = 1)
	if(!RmBeastKind(M)) return
	if(hpvar == "WingsHP") RmWingsReady(M)
	var/v = M.vars[hpvar]
	if(isnum(v) && v - dmg < least) M.vars[hpvar] = dmg + least

// An arrow (Combat - Bows.dm): its limb roll for the part aimed at; at a beast in the air,
// mostly its wings (struck here: 0, no limb roll used). A great beast's legs are never shot off.
mob/proc/RmArrowLimb(mob/Monsters/M, Limb, dmg)
	switch(RmPartBody(RmAimedPart(M, 60)))
		if("LeftLeg") Limb = 1
		if("RightLeg") Limb = 2
		if("RightArm") Limb = 3
		if("LeftArm") Limb = 4
		if("Head") return pick(5, 6)
		if("Wings")
			RmWingHurt(M, dmg, src)
			return 0
	var/hpvar = list("LeftLegHP", "RightLegHP", "RightArmHP", "LeftArmHP")[clamp(Limb, 1, 4)]
	if(Limb >= 1 && Limb <= 4) RmBeastLimbFloor(M, hpvar, dmg)
	return Limb

// A thrown weapon or bolt (Throwing.dm): the limb for the part aimed at ("Wings" and "Head" are
// struck here), or null for the usual roll.
mob/Monsters/proc/RmThrowPart(mob/Monsters/M, dmg)
	var/b = RmPartBody(RmAimedPart(M, 60))
	if(b == "Wings")
		RmWingHurt(M, dmg, src)
		return "Wings"
	if(b == "Head")
		view(M) << "[M] is hit in the head by [src]!"
		M.HP -= round(dmg * 1.5)
		M.BloodContent -= dmg
		M.BloodLoss()
		if(M && M.HP <= 0 && !M.GoingToDie)
			M.GoingToDie = 1
			M.Killer = "[src]"
			M.DeathType = "a blow to the head"
			M.Death()
		return "Head"
	return b

proc/RmWingsReady(mob/Monsters/M)
	if(isnull(M.WingsHP)) M.WingsHP = M.OrganMaxHP || 100

proc/RmWingsBroken(mob/Monsters/M)
	return istype(M) && M.HasWings && !isnull(M.WingsHP) && M.WingsHP <= 60

// A wound to the wings, by the original's stages (Combats.dm).
proc/RmWingHurt(mob/Monsters/M, dmg, mob/by)
	if(!istype(M) || !M.HasWings) return
	RmWingsReady(M)
	M.WingsHP = max(10, M.WingsHP - dmg)
	if(M.WingsHP <= 100) M.Wings = M.WingsHP <= 10 ? "Mangled" : M.WingsHP <= 40 ? "Crushed" : M.WingsHP <= 60 ? "Broken" : M.WingsHP <= 80 ? "Damaged" : "Bruised"
	view(M) << "[M]'s wings are hit[by ? " by [by]" : ""]! ([lowertext(M.Wings)])"
	RmWingCheck(M)

// Wings broken in the air: down it comes, hard - on the nearest open ground if it is over water
// or a wall.
proc/RmWingCheck(mob/Monsters/M)
	if(istype(M) && M.HasWings && !isnull(M.WingsHP) && M.WingsHP < 10) M.WingsHP = 10   // the original's blows (Combats.dm) don't stop at nothing
	if(!istype(M) || !M.Flying || !RmWingsBroken(M) || M.HP <= 0) return
	if(RmLandingBlocked(M))
		var/turf/best
		var/bd = 99
		for(var/turf/X in range(4, M))
			var/old = M.loc
			M.loc = X
			var/bad = RmLandingBlocked(M)
			M.loc = old
			if(!bad && get_dist(M, X) < bd)
				best = X
				bd = get_dist(M, X)
		if(best) M.loc = best
	M.Fly(0, "Land")
	if(M.Flying) return
	view(M) << "<b><font color=red>[M]'s wings give way: [M] crashes to the ground!</font></b>"
	M.LeftLegHP -= 15
	M.RightLegHP -= 15
	M.HP -= round(M.MAXHP * 0.1)
	if(M.HP <= 0 && !M.GoingToDie)
		M.GoingToDie = 1
		M.Killer = "the fall"
		M.DeathType = "crashing to the ground"
		M.Death()

// Wings mend slowly: a broken pair carries a dragon again after a few minutes.
proc/RmWingsMend()
	while(1)
		sleep(100)
		for(var/mob/Monsters/M in world) if(M.HasWings && !isnull(M.WingsHP) && M.HP > 0)
			var/most = M.OrganMaxHP || 100
			if(M.WingsHP >= most) continue
			if(M.WingsHP < 10) M.WingsHP = 10
			M.WingsHP = min(most, M.WingsHP + 2)
			if(M.WingsHP > 100 || M.WingsHP >= most) M.Wings = "Good"   // mended all the way, whatever its most (a dragon's is 150)

// world/New: this file's part is step RmChainWorldNew_Beasts1 in Code/Remastered/Chains/WorldNew.dm

// A right-click in 3D: the selected units (and ballistas) attack that part of a great beast.
Player/proc/RmAttackPart(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 2) return 0
	var/mob/Monsters/B = locate(p[1])
	if(!istype(B) || !RmBeastKind(B)) return 0
	var/n = 0
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && RemasterHostile(M, B, 1))
		M.rm_aim_beast = B
		M.rm_aim_part = p[2]
		n++
	if(!n) return 0
	RemasterAttackOrder(B)   // then the order as any attack on it (Attack.dm)
	RemasterNotice("[n] going for [B.name]'s [p[2]].")
	return 1

// --- The Health tab (HUD.dm RemasterStatSheet) ---------------------------------------------
// A great beast's legs by their own names, with how hurt each is; anyone with wings, how they
// are and, broken, how long until they carry it again.
proc/RmBodyRows(mob/Monsters/M, list/rows)
	var/most = M.OrganMaxHP || 100
	if(M.Race == "Dragon" || M.Race == "Spider")
		var/list/names = list("Left arm"="Left foreleg", "Right arm"="Right foreleg", "Left leg"="Left hind leg", "Right leg"="Right hind leg")
		var/list/hp = list("Left arm"="LeftArmHP", "Right arm"="RightArmHP", "Left leg"="LeftLegHP", "Right leg"="RightLegHP")
		for(var/list/R in rows) if(names[R[1]])
			var/v = M.vars[hp[R[1]]]
			if(R[2] != "Missing" && isnum(v)) R[2] = "[R[2]] ([max(0, round(v))]/[most])[v <= 10 ? ": crippled" : ""]"
			R[1] = names[R[1]]
	if(M.HasWings)
		RmWingsReady(M)
		var/w = "[M.Wings || "Good"] ([max(0, round(M.WingsHP))]/[most])"
		if(RmWingsBroken(M)) w += ": can't fly; mends in about [max(1, round((61 - M.WingsHP) / 2 * 10 / 60 + 0.5))] min"
		rows += list(list("Wings", w))
	return rows

// --- Wild dragons -----------------------------------------------------------------------
// A dragon nobody owns fights with its new tricks once it is in a fight (hurt, or after one of
// someone's people): its breath at the thickest knot of foes within reach, coming down while
// its wings still carry it when they are hurt, and backing off from its foes when it is badly
// hurt (wings broken on the ground, or under a third of its health).
var/list/rm_dragons = list()
mob/Monsters/Dragon/New()
	. = ..()
	rm_dragons += src
mob/Monsters/Dragon/Del()
	rm_dragons -= src
	return ..()

proc/RmWildDragonsLoop()
	while(1)
		sleep(20)
		for(var/mob/Monsters/M in rm_dragons) if(M && !istype(M.Owner, /Player) && M.HP > 0 && !M.GoingToDie && isturf(M.loc))
			M.RmWildDragonTick()

// world/New: this file's part is step RmChainWorldNew_Beasts2 in Code/Remastered/Chains/WorldNew.dm

mob/Monsters/proc/RmWildDragonTick()
	if(rm_bound) return   // chained down (Taming.dm)
	var/list/foes = list()
	for(var/mob/Monsters/E in oview(7, src)) if(istype(E.Owner, /Player) && RemasterHostile(src, E)) foes += E
	var/fighting = length(foes) && (HP < MAXHP || (HasWings && !isnull(WingsHP) && WingsHP < (OrganMaxHP || 100)) || (Target in foes) || (destination in foes))
	if(rm_nest && !fighting) for(var/mob/Monsters/E in foes) if(get_dist(E, rm_nest) <= 3) fighting = 1   // someone at its nest (Taming.dm)
	if(Flying && HasWings && !isnull(WingsHP) && WingsHP <= 80) Fly(0, "Land")   // down while the wings still carry it
	if(!fighting) return
	if(world.time >= remaster_special_at && RemasterSpecialAble())   // its breath: where most of them stand
		var/turf/best
		var/bn = 0
		for(var/mob/Monsters/E in foes)
			var/n = 0
			for(var/mob/Monsters/O in foes) if(get_dist(O, E) <= 2) n++
			if(n > bn && get_dist(src, E) <= 7)
				bn = n
				best = E.loc
		if(best) RemasterCastSpecial(best)
	if(!Flying && (RmWingsBroken(src) || HP < MAXHP / 3))   // badly hurt: away from the nearest
		var/mob/Monsters/near
		for(var/mob/Monsters/E in foes) if(!near || get_dist(src, E) < get_dist(src, near)) near = E
		if(near && get_dist(src, near) <= 4)
			var/turf/away = locate(clamp(x + 5 * sign(x - near.x), 1, world.maxx), clamp(y + 5 * sign(y - near.y), 1, world.maxy), z)
			if(away) destination = away
