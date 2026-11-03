// Morale (the user, 2026-10-26: "i only want it turned on during combat", "people start at zero moral they gain and if they
// fall negative at certain levels then things happen", "i dont like those effevt that snowballs", "lets polish that thats
// better"; planning/COMBAT_STRATEGY_PLAN_2026-10-26.md system 3). Zero-centred, every state a trade-off:
// - A unit has morale only while in combat: 0 at its first blow struck or taken, gone again rm_morale_calm (10 s) after its
//   last. Once a second on the shared clock (UnitClock.dm "Morale"), for those in combat only.
// - Range -100..+100. A change away from 0 counts (1 - |morale| / 100) of itself, one toward 0 in full; after 3 s with no
//   change it drifts 1 point every 2 s back toward 0.
// - Changes: its blow lands +1, a critical +3, a limb it crushes +3, one it cuts off +5, a kill +5; its own within 4 tiles
//   who see it, a critical or crush +1, a sever or kill +2; the victim's own within 4, a crush -2, a sever -3, one of theirs
//   falling -5 (their ruler or an NPC leader within 6: -20); a blow from its side -2, from behind -4 (Facing.dm);
//   outnumbered 2 to 1 within 4 tiles -1 a second; a banner of its realm or its ruler within 6 tiles +1 a second, to +30.
// - States (enter at the line, leave rm_morale_hyst (5) back inside). Morale only nudges these rolls (the user's table,
//   2026-10-26: "what about this??"):
//   sever chance as attacker (Wounds.dm): Battle fury x1.25, Emboldened x1.1;
//   the armour save, crush instead of sever, as defender (Wounds.dm): Shaken +1, Battle fury -2;
//   the awareness roll (Facing.dm): Shaken 3 easier, Emboldened 3 harder (6 with Committed), Battle fury none (tunnel vision);
//   criticals (CombatSkills.dm): Emboldened on 19-20, Shaken and Broken none;
//   bleeding, adrenaline (fight or flight works both ways): Battle fury 25%, Emboldened 15%, Shaken 15%, Broken 25% (only
//   Steady bleeds in full) of the loss held back in
//   the fight, all lost at once when it ends (one that bleeds out then gets its 60 s rescue window, BleedOut.dm);
//   knock-out or kill stays the striker's choice, its Lethal toggle (Subdue.dm): morale never spares a killing blow;
//   self-care: Battle fury won't stop to bandage itself; Shaken bandages first (WoundCare.dm, Stumps.dm).
//   +60 BATTLE FURY, +30 EMBOLDENED, -30..+30 STEADY, -30 SHAKEN, -60 BROKEN.
// - Shock: losing a limb -15 (half for one that had lost one before); a crushed limb or an untreated stump holds it at
//   Steady at best. Second wind: a critical or a kill while Broken +20. Treated (a bandage, a torch...) +10.
// - Covering (the user: "a unit can gang up to help break the shake... but leaves the helpers exposed"): a blow landed on a
//   foe whose target is a Shaken or Broken one of its own lifts that one +3 (group; "Covered!") and leaves the helper
//   Committed for 3 s: its awareness roll 3 harder.
// - Two parts (the user: "we can do one on one and based on units around using the log to see what is happening";
//   "snowball can be negated if the self unit makes a successful hit"): PERSONAL (its own blows and wounds, limb shock,
//   flank hits it takes, 2+ foes beside it, being treated) and GROUP (onlookers' gains and losses, its own falling,
//   outnumbered 2 to 1 within 4 tiles, a banner or its ruler near). Its state reads from the sum. A blow it lands clears
//   a negative group part (it shakes it off: rm_morale_shakeoff). rm_morale_group 0: personal only.
// - The log (Village > Log, Morale): a player's own units' state changes only, grouped: "Galas, Maan and Gaanley are
//   Shaken: Orin lost an arm beside them".
// - A player's unit never flees by itself. An NPC that is Broken routs home (a raider leaves the raid), striking no blow
//   while it flees (rm_rout_time, 20 s); it can be chased, roped or captured.
// - A word floats over it when its state changes; the card shows a bar from -100 to +100 and the state while in combat
//   (remastered.html, HUD.dm). Animals, great beasts, wagons and siege engines have none. rm_morale_on = 0: none, as before.
var/rm_morale_on = 1
var/rm_morale_calm = 100       // ticks without a blow: out of combat
var/rm_morale_drift_after = 30 // ticks with no change before it drifts
var/rm_morale_hyst = 5
var/rm_morale_vet = 50          // Defence this or more: a veteran, morale never moves it (the user, 2026-10-26 21:3x: "morale shouldnt matter for vets"; 0: off)
var/list/rm_morale_gain = list("hit"=1, "crit"=3, "crush"=3, "sever"=5, "kill"=5)   // the striker
var/list/rm_morale_seen = list("crit"=1, "crush"=1, "sever"=2, "kill"=2)            // its own within 4 who see it
var/list/rm_morale_loss = list("crush"=2, "sever"=3, "death"=5, "leader"=20)        // the victim's own within 4 (a leader: 6)
var/rm_morale_side = 2
var/rm_morale_rear = 4
var/rm_morale_outnumbered = 1
var/rm_morale_rally = 1
var/rm_morale_rally_max = 30
var/rm_rout_time = 200
var/rm_morale_group = 1          // 1: its own see and feel each other's blows and deaths; 0: one-on-one
var/rm_morale_shakeoff = 1       // a blow it lands clears a negative group part
var/list/rm_morale_names = list("2"="Battle fury", "1"="Emboldened", "-1"="Shaken", "-2"="Broken")
var/rm_fury_sever = 1.25         // its cuts' sever chance (Wounds.dm)
var/rm_bold_sever = 1.1
var/rm_fury_save = -2            // armour save faces (Wounds.dm)
var/rm_shaken_save = 1
var/rm_bold_aware = 3            // awareness: a harder roll (Facing.dm)
var/rm_shaken_aware = -3         // an easier one
var/rm_fury_bleed = 0.25         // blood held back while in battle fury, taken when the fight ends
var/rm_bold_bleed = 0.15         // ...while emboldened (the user, 2026-10-26: "Keep 15%")
var/rm_shaken_bleed = 0.15       // ...while shaken
var/rm_broken_bleed = 0.25       // ...while broken
var/rm_shock = 15
var/rm_second_wind = 20
var/rm_treated = 10
var/rm_cover_on = 1
var/rm_cover_gain = 3
var/rm_commit_time = 30
var/rm_commit_aware = 3
mob/Monsters/var/tmp/rm_morale             // null: not in combat
mob/Monsters/var/tmp/rm_morale_p = 0       // its personal part
mob/Monsters/var/tmp/rm_morale_g = 0       // its group part
mob/Monsters/var/tmp/rm_morale_why         // what last moved it, for the log
Player/var/tmp/list/rm_mlog               // state changes waiting to be logged, grouped
mob/Monsters/var/tmp/rm_mstate = 0         // -2 Broken .. 2 Battle fury
mob/Monsters/var/tmp/rm_fight_at = 0
mob/Monsters/var/tmp/rm_morale_at = 0      // its last change (not drift)
mob/Monsters/var/tmp/rm_morale_beat = 0
mob/Monsters/var/tmp/rm_rout_until = 0
mob/Monsters/var/tmp/rm_routs = 0          // times it routed (an NPC; reports)
mob/Monsters/var/tmp/rm_adrenaline = 0     // blood battle fury held back
mob/Monsters/var/tmp/rm_blood_seen          // its blood at the last beat
mob/Monsters/var/tmp/rm_committed_until = 0 // a covering blow: its back to the fight till then
mob/Monsters/var/tmp/rm_covers = 0          // covering blows it struck (reports)

mob/Monsters/proc/RmMoraleOK()
	if(!rm_morale_on || HP <= 0 || GoingToDie || Critter || Wagon || RmBeastKind(src) || RemasterIsSiege(src)) return 0
	return istype(Owner, /Player) || RmNPCRole()

// A blow struck or taken: in combat, from now or still.
mob/Monsters/proc/RmMoraleFight()
	rm_fight_at = world.time
	if(!isnull(rm_morale) || !RmMoraleOK()) return
	rm_morale = 0
	rm_morale_p = 0
	rm_morale_g = 0
	rm_mstate = 0
	rm_morale_at = world.time
	RmClockStart(src, "Morale", 10)

// A veteran: its morale stays at 0, Steady (no state's land, critical, damage or sever change, no blood held back, never
// routs); its own blows still move its friends' and foes' morale (RmMoraleShare).
mob/Monsters/proc/RmMoraleVet()
	return rm_morale_vet && RemasterCombatLevel(src, "Defence") >= rm_morale_vet

mob/Monsters/proc/RmMoraleAdd(n, group = 0, why = null)
	if(isnull(rm_morale) || !n || HP <= 0 || GoingToDie) return
	if(RmMoraleVet())   // a veteran: Steady; one that became one mid-fight (Defence up to 50) lets go of what it had
		if(rm_morale_p || rm_morale_g)
			rm_morale_p = 0
			rm_morale_g = 0
			RmMoraleSum()
			RmMoraleState()
		return
	if(group && !rm_morale_group) return
	if((n > 0 && rm_morale >= 0) || (n < 0 && rm_morale <= 0)) n *= 1 - abs(rm_morale) / 100   // away from 0: less and less
	if(group) rm_morale_g += n
	else rm_morale_p += n
	RmMoraleSum()
	if(rm_morale > 29 && RmMoraleCapped())   // a crushed limb or an untreated stump: Steady at best
		if(group) rm_morale_g -= rm_morale - 29
		else rm_morale_p -= rm_morale - 29
		RmMoraleSum()
	rm_morale_at = world.time
	if(why) rm_morale_why = why
	RmMoraleState()

mob/Monsters/proc/RmMoraleSum()
	rm_morale = clamp(rm_morale_p + rm_morale_g, -100, 100)

mob/Monsters/proc/RmMoraleCapped()
	return LeftArm == "Crushed" || RightArm == "Crushed" || LeftLeg == "Crushed" || RightLeg == "Crushed" || RmStumpBleedingNow()

mob/Monsters/proc/RmMoraleState()
	var/m = rm_morale
	var/h = rm_morale_hyst
	var/n = m >= 60 ? 2 : m >= 30 ? 1 : m > -30 ? 0 : m > -60 ? -1 : -2
	if(rm_mstate == 2 && n == 1 && m >= 60 - h) n = 2   // it leaves a state only h back inside its line
	if(rm_mstate == 1 && n == 0 && m >= 30 - h) n = 1
	if(rm_mstate == -1 && n == 0 && m <= -30 + h) n = -1
	if(rm_mstate == -2 && n == -1 && m <= -60 + h) n = -2
	if(n == rm_mstate) return
	rm_mstate = n
	if(n) RemasterHit(src, 0, "m[n]", src)   // its word over it (remastered.html)
	if(n) RmMoraleLog(n)
	if(n == -2 && !istype(Owner, /Player)) RmRout()

mob/Monsters/proc/RmMoraleSever()    // its cuts' sever chance
	return rm_mstate == 2 ? rm_fury_sever : rm_mstate == 1 ? rm_bold_sever : 1
mob/Monsters/proc/RmMoraleSave()     // its armour saves, in d20 faces
	return rm_mstate == 2 ? rm_fury_save : rm_mstate == -1 ? rm_shaken_save : 0
mob/Monsters/proc/RmMoraleAware()    // its awareness roll, harder (+) or easier (-); a covering blow's helper, harder
	return (rm_mstate == 1 ? rm_bold_aware : rm_mstate == -1 ? rm_shaken_aware : 0) + (rm_committed_until > world.time ? rm_commit_aware : 0)
mob/Monsters/proc/RmMoraleStateText()
	if(isnull(rm_morale)) return null
	switch(rm_mstate)
		if(2) return "Battle fury: severs more, bleeds later; no awareness, won't bandage itself, armour saves worse"
		if(1) return "Emboldened: crits on 19-20, severs more, bleeds later; awareness worse"
		if(-1) return "Shaken: awareness and armour saves better, bandages first, bleeds later; no crits"
		if(-2) return "Broken: bleeds later; no crits"
	return RmMoraleVet() ? "Steady: a veteran (Defence [rm_morale_vet]+), morale doesn't move it" : "Steady"

// Once a second while in combat. Its looks round, here and below, go through RmUnitsNear (Native.dm): the unit grid's
// square, not a walk over the tiles.
mob/Monsters/proc/RmMoraleTick()
	if(isnull(rm_morale) || HP <= 0 || GoingToDie || !isturf(loc)) return RmMoraleEnd()
	if(world.time - rm_fight_at >= rm_morale_calm && !RmMoraleEngaged()) return RmMoraleEnd()
	RmClockBook(src, "Morale", 10)
	rm_morale_beat++
	var/foes = 0
	var/beside = 0
	var/allies = 1
	var/royal   // a royal of its own within 6, looked for by the engine with the rest (null: not looked for)
	var/list/L = rm_morale_native ? RmMoraleLook(src) : null   // the engine's look round, the same counts (Native.dm)
	if(L && !rm_morale_verify)
		foes = L[1]
		beside = L[2]
		allies += L[3]
		royal = L[4]
	else
		var/list/pairs = list()   // each realm's war and alliance once (Attack.dm RemasterHostile)
		for(var/mob/Monsters/O in RmUnitsNear(4, src)) if(O != src && O.HP > 0 && !O.GoingToDie && !O.Critter && !O.Fainted && !O.Sleeping && !O.RemasterKnockedOut())   // one lying down (out cold, bleeding out, asleep) fights no one
			if(O.Owner == Owner) allies++
			else if(RemasterHostile(src, O, 0, pairs))
				foes++
				if(get_dist(src, O) <= 1) beside++
		if(L) RmMoraleVerify(src, L, foes, beside, allies)   // shadow mode (Native.dm)
	if(beside >= 2) RmMoraleAdd(-rm_morale_outnumbered, 0, ": fighting [beside] at once")   // personal
	if(foes >= allies * 2) RmMoraleAdd(-rm_morale_outnumbered, 1, ": outnumbered")       // group
	if(rm_morale < rm_morale_rally_max && (isnull(royal) ? RmMoraleRallied() : (royal || RmMoraleBanner()))) RmMoraleAdd(min(rm_morale_rally, rm_morale_rally_max - rm_morale), 1, ": rallied")
	if(world.time - rm_morale_at >= rm_morale_drift_after && rm_morale && !(rm_morale_beat % 2))   // drifting home, 1 every 2 s
		if(rm_morale_g) rm_morale_g = rm_morale_g > 0 ? max(0, rm_morale_g - 1) : min(0, rm_morale_g + 1)
		else rm_morale_p = rm_morale_p > 0 ? max(0, rm_morale_p - 1) : min(0, rm_morale_p + 1)
		RmMoraleSum()
		RmMoraleState()
	var/hold = rm_mstate == 2 ? rm_fury_bleed : rm_mstate == 1 ? rm_bold_bleed : rm_mstate == -1 ? rm_shaken_bleed : rm_mstate == -2 ? rm_broken_bleed : 0
	if(hold && isnum(rm_blood_seen) && BloodContent < rm_blood_seen)   // adrenaline: a share of the loss held back
		var/back = (rm_blood_seen - BloodContent) * hold
		BloodContent += back
		rm_adrenaline += back
	rm_blood_seen = BloodContent

mob/Monsters/proc/RmMoraleEngaged()
	var/mob/E = remaster_attack ? remaster_attack.target : Target
	return ismob(E) && E.z == z && get_dist(src, E) <= 4

mob/Monsters/proc/RmMoraleRallied()
	return RmMoraleBanner() || RmMoraleRoyalNear()

mob/Monsters/proc/RmMoraleBanner()   // a banner of its realm within 6
	var/Player/P = Owner
	if(!istype(P)) return 0
	for(var/obj/RemasterBanner/B in rm_banners) if(B.owner_key == P.key && B.z == z && get_dist(B, src) <= 6) return 1
	return 0

mob/Monsters/proc/RmMoraleRoyalNear()   // its ruler (a royal of its own) within 6; the engine's look finds it too (Native.dm)
	var/Player/P = Owner
	if(!istype(P)) return 0
	for(var/mob/Monsters/R in RmUnitsNear(6, src)) if(R != src && R.Owner == P && R.IsRoyal && R.HP > 0) return 1
	return 0

mob/Monsters/proc/RmMoraleEnd()
	rm_morale = null
	rm_morale_p = 0
	rm_morale_g = 0
	rm_mstate = 0
	rm_blood_seen = null
	RmClockStop(src, "Morale")
	if(rm_adrenaline && HP > 0 && !GoingToDie)   // the fight over, the held-back blood is lost at once
		BloodContent -= rm_adrenaline
		rm_adrenaline = 0
		BloodLoss()
		if(BloodContent <= 0) RmBleedOut(src)   // bled out: the 60 s rescue window (BleedOut.dm)

// An NPC that breaks flees home.
mob/Monsters/proc/RmRout()
	rm_routs++
	rm_rout_until = world.time + rm_rout_time
	RemasterHit(src, 0, "rout", src)
	Target = null
	var/turf/home = isturf(HomeLoc) && !(remaster_raiders && remaster_raiders[src]) && get_dist(HomeLoc, src) > 6 ? HomeLoc : RmRoutAway()
	if(remaster_raiders && remaster_raiders[src]) remaster_raiders -= src   // it leaves the raid
	HomeLoc = home
	destination = home

mob/Monsters/proc/RmRoutAway()   // 15 tiles away from its foes
	var/sx = 0
	var/sy = 0
	var/n = 0
	for(var/mob/Monsters/O in RmUnitsNear(6, src)) if(O.Owner != Owner && O.HP > 0 && !O.Critter)
		sx += O.x
		sy += O.y
		n++
	var/dx = n ? x - sx / n : 0
	var/dy = n ? y - sy / n : -1
	var/d = max(0.5, sqrt(dx * dx + dy * dy))
	return locate(clamp(round(x + dx / d * 15), 1, world.maxx), clamp(round(y + dy / d * 15), 1, world.maxy), z) || loc

// What one blow did: the striker's morale (personal), its own's who see it and the victim's own's (group); why: words for
// the log.
mob/Monsters/proc/RmMoraleShare(list/to_me, list/to_mine, mob/Monsters/V, list/to_theirs, why_me, why_mine, why_theirs)
	var/g = 0
	for(var/k in to_me) g += rm_morale_gain[k] || 0
	RmMoraleAdd(g, 0, why_me)
	var/s = 0
	for(var/k in to_mine) s += rm_morale_seen[k] || 0
	var/l = 0
	for(var/k in to_theirs) l += rm_morale_loss[k] || 0
	if((!s && !l) || !rm_morale_group) return
	for(var/mob/Monsters/O in RmUnitsNear(4, V || src)) if(O != src && O != V && !isnull(O.rm_morale))
		if(s && O.Owner == Owner) O.RmMoraleAdd(s, 1, why_mine)
		else if(l && V && O.Owner == V.Owner) O.RmMoraleAdd(-l, 1, why_theirs)

proc/RmLimbsOn(mob/Monsters/M)
	return (M.HasLeftArm ? 1 : 0) + (M.HasRightArm ? 1 : 0) + (M.HasLeftLeg ? 1 : 0) + (M.HasRightLeg ? 1 : 0)

var/list/rm_limb_names = list("LeftArm"="an arm", "RightArm"="an arm", "LeftLeg"="a leg", "RightLeg"="a leg")
proc/RmLimbsHad(mob/Monsters/M)   // which limbs it has
	. = list()
	if(ismob(M) && length(rm_limb_names) == 4)   // its own fields, in rm_limb_names' order (combat-speed, 10-26)
		if(M.HasLeftArm) . += "LeftArm"
		if(M.HasRightArm) . += "RightArm"
		if(M.HasLeftLeg) . += "LeftLeg"
		if(M.HasRightLeg) . += "RightLeg"
		return
	for(var/L in rm_limb_names) if(M.vars["Has[L]"]) . += L

// mob/RemasterStrike: this file's part is step RmChainStrike_Morale in Code/Remastered/Chains/Strike.dm

// The log (Village > Log, Morale): a player's own unit's new state, gathered for a second and grouped by state and cause.
mob/Monsters/proc/RmMoraleLog(n)
	var/Player/P = Owner
	if(!istype(P) || !n) return
	if(!P.rm_mlog)
		P.rm_mlog = list()
		spawn(10) if(P) P.RmMoraleLogFlush()
	P.rm_mlog += list(list(src, n, rm_morale_why || ""))

Player/proc/RmMoraleLogFlush()
	var/list/L = rm_mlog
	rm_mlog = null
	if(!L) return
	var/list/groups = list()   // "state|why" -> its units
	for(var/list/E in L)
		var/mob/Monsters/M = E[1]
		if(Rm3DGone(M) || M.HP <= 0) continue
		if(E[2] != "shook" && M.rm_mstate != E[2]) continue   // it changed again since
		var/k = "[E[2]]|[E[3]]"
		if(!groups[k]) groups[k] = list()
		groups[k] |= M
	for(var/k in groups)
		var/list/U = groups[k]
		var/i = findtext(k, "|")
		var/st = copytext(k, 1, i)
		var/why = copytext(k, i + 1)
		var/list/names = list()
		for(var/mob/Monsters/M in U) names += M.RemasterBareName()
		var/who = length(names) == 1 ? names[1] : length(names) == 2 ? "[names[1]] and [names[2]]" : "[jointext(names.Copy(1, length(names)), ", ")] and [names[length(names)]]"
		var/are = length(names) == 1 ? "is" : "are"
		var/line
		switch(st)
			if("shook") line = "[who] shook it off"
			if("2") line = "[who] [are] in a battle fury[why]"
			if("1") line = "[who] [are] Emboldened[why]"
			if("-1") line = "[who] [are] Shaken[why]"
			if("-2")
				line = "[who] [are] Broken[why]"
				for(var/mob/Monsters/M in U) if(RmMoraleHelpComing(M))
					line += "; a friend is coming to help"
					break
		if(line) RemasterLog(line, "morale", U[1])

proc/RmMoraleHelpComing(mob/Monsters/M)
	for(var/mob/Monsters/H in RmUnitsNear(20, M)) if(H.Owner == M.Owner && (H.remaster_care == "stumphelp" || H.remaster_care == "woundhelp") && H.remaster_care_target == M) return 1
	return 0

// mob/Monsters/Death: this file's part is step RmChainDeath_Morale in Code/Remastered/Chains/Death.dm

// Treated in the fight: +10 (a bandage, a torch, a poultice, a potion: Stumps.dm, WoundCare.dm, BleedOut.dm).
mob/Monsters/RemasterStumpDo(list/O, Player/P)
	. = ..()
	if(. && !isnull(rm_morale)) RmMoraleAdd(rm_treated, 0, ": its wounds seen to")
mob/Monsters/RmWoundTreat(list/O, Player/P)
	. = ..()
	if(. && !isnull(rm_morale)) RmMoraleAdd(rm_treated, 0, ": its wounds seen to")

// Battle fury: no bandaging itself; Shaken: its wounds tended as soon as they bleed (WoundCare.dm).
mob/Monsters/RmWoundSelf(Player/P)
	if(rm_mstate == 2) return 0
	return ..()
mob/Monsters/RmWoundBad()
	if(rm_mstate == -1 && BleedType && !rm_dying_until && !RemasterStumpBleeding() && HP > 0 && !GoingToDie) return 1
	return ..()

