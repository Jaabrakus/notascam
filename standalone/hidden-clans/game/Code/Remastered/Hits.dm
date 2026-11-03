// Damage numbers. Combat hurts body parts, not one HP bar, so each melee strike is
// measured by what it really did: the target's body health (HP plus every part's HP)
// before and after the original Attack(). The 3D view floats the number over the
// target: white for a hit, gold for a big one, grey for a miss or block, red when
// your own unit is hurt, and a skull for a kill. Openings: each strike in a row that
// does nothing adds 3 damage to the next one (armour can't stop a fight forever).

var/list/rm_body_parts = list("HP", "HeadHP", "BrainHP", "ThroatHP", "HeartHP", "GutsHP", "StomachHP", "LiverHP", "SpleenHP",
	"LeftLungHP", "RightLungHP", "LeftKidneyHP", "RightKidneyHP", "LeftArmHP", "RightArmHP", "LeftLegHP", "RightLegHP",
	"LeftEyeHP", "RightEyeHP", "LeftEarHP", "RightEarHP", "NoseHP", "TeethHP", "WingsHP")
mob/var/tmp/remaster_opening = 0     // strikes in a row that did no damage (Combats.dm adds 3 each)
var/list/rm_hits = list()             // list(id, x, y, z, amount, kind, time, owner)
var/rm_hit_id = 0

// The health a card, the roster and the 3D bar show (the owner, 10-28: "health doesnt update when attack lands that is
// something is very important"). A people race's blows land on its parts and draw blood (Combats.dm, CombatSkills.dm
// RmMeleeWhere); only a blunt blow's crush takes HP (Chains/Strike.dm Blunt), so HP alone sat full while it was cut
// down. Its health is the lowest of HP, its blood, the parts it dies without (head, brain, throat, heart) and how
// whole its body is (RmBodyFrac). Beasts and the rest: HP, as before.
//
// It is read about six times a unit a second (the HUD entry and its key, the 3D bar, the warnings) and costs ~20 us, so
// each unit keeps it with its change counter (rm_ver, engine/core/RmVer.cs: any var of the unit written, anything in it
// changed, a move): worked out again only when something about the unit changed (server upgrades, 10-30: 200 units,
// one player, ~27 ms of each second). Writing the two kept values moves the counter by one each, so the second holds
// where the counter stands after it. RM_VER_VERIFY=1: every kept answer is checked against a fresh one; a difference
// is logged (RMVER|life).
mob/var/tmp/rm_life_ver = -1
mob/var/tmp/rm_life_frac = 1
proc/RmLifeFrac(mob/M)
	if(!M) return 1
	if(!rm_native_ver) return RmLifeFracNow(M)
	// kept while its state counter stands (rm_ver_state: its steps aside, none of what it reads is motion; ~800 worked out
	// again a second at 100 players while units walked, ~12 ms of DM a game second; the owner, 10-31: "Yes, build them")
	if(M.rm_life_ver == rm_ver_state(M))
		if(rm_ver_verify)
			var/fresh = RmLifeFracNow(M)
			if(fresh != M.rm_life_frac) world.log << "RMVER|life|[M] [M.type]: kept [M.rm_life_frac], now [fresh]"
		return M.rm_life_frac
	. = RmLifeFracNow(M)
	M.rm_life_frac = .
	M.rm_life_ver = (rm_ver_state(M) + (rm_ver_quieted ? 0 : 1)) % 16777216   // quiet (Native.dm): its own writes move nothing

proc/RmLifeFracNow(mob/M)
	if(!M || !isnum(M.MAXHP) || M.MAXHP <= 0) return 1
	. = clamp(M.HP / M.MAXHP, 0, 1)
	if(!M.HumanParts) return
	if(M.MaxBloodContent > 0 && M.Race != "Gargoyle" && M.Race != "Skeleton") . = min(., clamp(M.BloodContent / M.MaxBloodContent, 0, 1))
	if(M.HasHead) . = min(., RmPartFrac(1, M.HeadHP, initial(M.HeadHP)))
	if(M.HasBrain) . = min(., RmPartFrac(1, M.BrainHP, initial(M.BrainHP)))
	if(M.HasThroat) . = min(., RmPartFrac(1, M.ThroatHP, initial(M.ThroatHP)))
	if(M.HasHeart) . = min(., RmPartFrac(1, M.HeartHP, initial(M.HeartHP)))
	. = min(., RmBodyFrac(M))

// How whole its body is, so a blow anywhere shows (a mace on a leg draws no blood and takes no HP): each zone's parts
// as a share of their full health, the zones weighed as RimWorld weighs its body (head 15%, torso 35%, an arm 10%, a
// leg 15%: 100% whole). A part's full health is what its kind starts with (initial(): the races raise OrganMaxHP, the cap, without
// raising every part, so the cap read a fresh unit as hurt). A part it has lost counts as gone; one its race never has
// ("N/A", Health.dm) as whole.
proc/RmBodyFrac(mob/M)
	var/head = (RmPartFrac(M.HasHead, M.HeadHP, initial(M.HeadHP), M.Head) + RmPartFrac(M.HasBrain, M.BrainHP, initial(M.BrainHP), M.Brain) + RmPartFrac(M.HasThroat, M.ThroatHP, initial(M.ThroatHP), M.Throat) + RmPartFrac(M.HasLeftEye, M.LeftEyeHP, initial(M.LeftEyeHP), M.LeftEye) + RmPartFrac(M.HasRightEye, M.RightEyeHP, initial(M.RightEyeHP), M.RightEye) + RmPartFrac(M.HasLeftEar, M.LeftEarHP, initial(M.LeftEarHP), M.LeftEar) + RmPartFrac(M.HasRightEar, M.RightEarHP, initial(M.RightEarHP), M.RightEar) + RmPartFrac(M.HasNose, M.NoseHP, initial(M.NoseHP), M.Nose)) / 8
	var/torso = (RmPartFrac(M.HasHeart, M.HeartHP, initial(M.HeartHP), M.Heart) + RmPartFrac(M.HasLeftLung, M.LeftLungHP, initial(M.LeftLungHP)) + RmPartFrac(M.HasRightLung, M.RightLungHP, initial(M.RightLungHP)) + RmPartFrac(M.HasStomach, M.StomachHP, initial(M.StomachHP)) + RmPartFrac(M.HasGuts, M.GutsHP, initial(M.GutsHP)) + RmPartFrac(M.HasLiver, M.LiverHP, initial(M.LiverHP)) + RmPartFrac(M.HasSpleen, M.SpleenHP, initial(M.SpleenHP)) + RmPartFrac(M.HasLeftKidney, M.LeftKidneyHP, initial(M.LeftKidneyHP)) + RmPartFrac(M.HasRightKidney, M.RightKidneyHP, initial(M.RightKidneyHP))) / 9
	var/arms = 0.1 * RmPartFrac(M.HasLeftArm, M.LeftArmHP, initial(M.LeftArmHP), M.LeftArm) + 0.1 * RmPartFrac(M.HasRightArm, M.RightArmHP, initial(M.RightArmHP), M.RightArm)
	var/legs = 0.15 * RmPartFrac(M.HasLeftLeg, M.LeftLegHP, initial(M.LeftLegHP), M.LeftLeg) + 0.15 * RmPartFrac(M.HasRightLeg, M.RightLegHP, initial(M.RightLegHP), M.RightLeg)
	return 0.15 * head + 0.35 * torso + arms + legs

proc/RmPartFrac(has, hp, mx, state)
	if(state == "N/A") return 1
	return has && isnum(hp) ? clamp(hp / max(1, mx), 0, 1) : 0

// the health on HP's scale (the card reads hp / maxhp)
proc/RmLifeHP(mob/M)
	return M ? round(RmLifeFrac(M) * max(0, M.MAXHP)) : 0

#define RM_BH_ADD(V) if(isnum(M.V) && M.V > 0) . += M.V
proc/RemasterBodyHealth(mob/M)
	. = 0
	if(!M) return
	if(ismob(M) && length(rm_body_parts) == 24)   // a mob has every one (Vars.dm): its own fields, in rm_body_parts' order (combat-speed, 10-26: by name it cost 13-35 us a call, ~5 calls a blow)
		RM_BH_ADD(HP)
		RM_BH_ADD(HeadHP)
		RM_BH_ADD(BrainHP)
		RM_BH_ADD(ThroatHP)
		RM_BH_ADD(HeartHP)
		RM_BH_ADD(GutsHP)
		RM_BH_ADD(StomachHP)
		RM_BH_ADD(LiverHP)
		RM_BH_ADD(SpleenHP)
		RM_BH_ADD(LeftLungHP)
		RM_BH_ADD(RightLungHP)
		RM_BH_ADD(LeftKidneyHP)
		RM_BH_ADD(RightKidneyHP)
		RM_BH_ADD(LeftArmHP)
		RM_BH_ADD(RightArmHP)
		RM_BH_ADD(LeftLegHP)
		RM_BH_ADD(RightLegHP)
		RM_BH_ADD(LeftEyeHP)
		RM_BH_ADD(RightEyeHP)
		RM_BH_ADD(LeftEarHP)
		RM_BH_ADD(RightEarHP)
		RM_BH_ADD(NoseHP)
		RM_BH_ADD(TeethHP)
		RM_BH_ADD(WingsHP)
		return
	for(var/v in rm_body_parts) if(v in M.vars)
		var/n = M.vars[v]
		if(isnum(n) && n > 0) . += n

// Weapon classes. Every melee strike goes through here (players' and NPCs' alike):
//   Sword  duelist  - parries some blows aimed at its wielder
//   Axe    cleaver  - a hit can cleave into a second enemy beside the target
//   Mace   crusher  - cuts through armour (Combats.dm) and can stagger
//   Spear  reach    - strikes from two tiles away (Attack.dm, Defense.dm)
//   Dagger quick    - often strikes twice; wounds bleed
mob/var/tmp/remaster_striking = 0
mob/var/tmp/remaster_reach_at = 0

proc/RemasterWeaponClass(mob/M)
	var/w = M ? "[M.HoldingWeapon]" : ""
	if(w in list("Sword", "Axe", "Mace", "Spear", "Dagger", "Bow", "Claws")) return lowertext(w)
	if(w == "Butcher Knife") return "dagger"
	return "fist"

proc/RemasterWeaponRole(mob/M)
	return list("sword"="Duelist: parries blows", "axe"="Cleaver: hits a second foe", "mace"="Crusher: breaks armour, staggers",
		"spear"="Reach: strikes from 2 tiles", "dagger"="Quick: double strikes, bleeding", "bow"="Archer", "claws"="Claws", "fist"="Unarmed")[RemasterWeaponClass(M)]

// Swing speed. The original swung with every step a unit took at its foe (every 0.3-0.4 s). Each weapon swings on
// its own timer: the table below (a dagger 1 s; a sword, scimitar, claws or bare fists 1.2 s; a longsword, mace,
// hand axe or spear 1.4 s; a morning star 1.5 s; a warhammer, pickaxe or staff 1.6 s; a battle axe 1.8 s; a halberd
// 2 s; a dragon 1.6 s) times rm_swing_pace. Each blow hits harder by the table's time only (RmSwingDamage, applied
// in Combats.dm Attack, Subdue.dm and WeaponSkills.dm). With rm_swing_pace 2 (the user, 2026-10-23: a slow,
// brutal, grindy game like vanilla WoW or RuneScape) weapons swing at RuneScape's own speeds, a sword every 2.4 s
// and a halberd every 4 s; weapon moves come round as much slower (WeaponSkills.dm). Fights last about twice as long
// (Pace.dm, tools/check_pace.py).
var/rm_swing_pace = 1
// Hidden Clans (the owner, 11-01: "as responsive as possible"): 1, twice Banners' swing rate, nearer GOA's (1 s to 0.2 s between blows); Banners' 2 gave a blow every 2.4-3 s
mob/var/tmp/rm_swing_at = 0        // world.time this unit may swing again
mob/var/tmp/rm_swung_at = -100     // its last swing (the 3D view plays one attack per swing)
var/list/rm_swing_styles = list("dagger"=10, "arming sword"=12, "scimitar"=12, "longsword"=14, "hand axe"=14, "mace"=14,
	"spear"=14, "morning star"=15, "warhammer"=16, "pickaxe"=16, "battle axe"=18, "halberd"=20)
var/list/rm_swing_classes = list("dagger"=10, "sword"=12, "claws"=12, "fist"=12, "axe"=14, "mace"=14, "spear"=14, "bow"=12)

proc/RmSwingTicks(mob/M)
	return RmSwingBase(M) * rm_swing_pace

proc/RmSwingBase(mob/M)
	if(!M) return 12
	if(M.Race == "Dragon") return 16
	var/obj/Items/Equipment/W
	for(var/obj/Items/Equipment/Weapon/X in M) if(X.suffix == "(Equipped)")
		W = X
		break
	if(W)
		if(W.rm_gear)   // the new gear: its style (GearData.dm "weapon.<style>.<tier>", "magic.<staff>")
			var/list/p = splittext(W.rm_gear, ".")
			if(p[1] == "magic") return length(p) >= 2 && findtext(p[2], "staff") ? 16 : 14
			if(length(p) >= 2 && rm_swing_styles[p[2]]) return rm_swing_styles[p[2]]
		var/n = lowertext(W.name)   // the game's own weapons, by name
		if(findtext(n, "halberd")) return 20
		if(findtext(n, "battle") || findtext(n, "great") || findtext(n, "two hand") || findtext(n, "2h")) return 18
		if(findtext(n, "hammer") || findtext(n, "pick") || findtext(n, "staff")) return 16
		if(findtext(n, "morning")) return 15
		if(findtext(n, "long")) return 14
	return rm_swing_classes[RemasterWeaponClass(M)] || 12

// How much harder each blow lands: the table's swing time over the step it used to swing with (not the paced time).
proc/RmSwingDamage(mob/M)
	if(!M) return 1
	return clamp(RmSwingBase(M) / max(2, M.Delay || 4), 1, 5)

// mob/RemasterStrike: this file's part is step RmChainStrike_Hits in Code/Remastered/Chains/Strike.dm

// The swing timer stops this strike before any blow (RmChainStrike_Hits returns 0 at its first check, changing nothing):
// the steps above it then skip measuring the foe for a blow that can't come (combat-speed, 10-26: in a melee 4 of 5
// strikes are such calls, a unit walking at its foe while its weapon comes round).
var/list/rm_swing_free = list("cleave", "double")   // blows that keep no swing timer (RmChainStrike_Hits)
mob/proc/RmSwingWaits(mob/M, kind_hint)
	return M && !(kind_hint in rm_swing_free) && !rm_move_sure && world.time < rm_swing_at

mob/var/tmp/rm_shot_part   // where its last arrow or throw struck, for the 3D view (a part, "block" or "deflect")
proc/RemasterHit(mob/M, amount, kind, mob/by)
	var/turf/T = M.loc
	if(!isturf(T)) return
	RemasterHitAt(T.x, T.y, T.z, amount, kind, by, M.Owner)
	if(kind == "hit" || kind == "crush" || kind == "cleave") RmKnockBack(M, by, amount)

// A heavy blow knocks its target back, alive (the user, 2026-10-25: the arena's "Knocked back, lives" and "Hammer launch,
// lives" in the game): rm_knock_dmg or more, it is moved a tile away from the striker (a warhammer's, two) if there is room,
// and down a moment; the 3D view flies its doll there ("knock|dx|dy|tiles|kind").
var/rm_knock_on = 1
var/rm_knock_dmg = 28
proc/RmKnockBack(mob/Monsters/M, mob/Monsters/by, amount)
	if(!rm_knock_on || amount < rm_knock_dmg || !istype(M) || !istype(by) || M.HP <= 0 || M.GoingToDie || !isturf(M.loc) || M.Flying || M.rm_bound || RmBeastKind(M) || get_dist(by, M) > 1) return 0
	var/obj/Items/Equipment/W = RmHeldWeapon(by)
	var/hammer = W && findtext("[W.rm_gear]", "warhammer")
	var/d = get_dir(by, M)
	var/dx = (d & EAST ? 1 : 0) - (d & WEST ? 1 : 0)
	var/dy = (d & NORTH ? 1 : 0) - (d & SOUTH ? 1 : 0)
	if(!dx && !dy) return 0
	var/turf/T = M.loc
	var/m = 0
	for(var/i = 1, i <= (hammer ? 2 : 1), i++)
		var/turf/N = locate(T.x + dx, T.y + dy, T.z)
		if(!N || N.density) break
		var/taken = 0
		for(var/atom/movable/A in N) if(A.density) taken = 1
		if(taken) break
		T = N
		m++
	if(!m) return 0
	M.loc = T
	M.destination = null
	M.Stunned = 1
	spawn(m >= 2 ? 25 : 15) if(M) M.Stunned = 0
	RemasterHitAt(T.x, T.y, T.z, 0, "stagger", by, M.Owner, "knock|[dx]|[dy]|[m]|[hammer ? "hammer" : "flying"]")
	return m

// proj: "arrow", "javelin", "axe" or "rock" for shots (the 3D view flies it from the attacker).
// Each hit goes in the world's last 160 (rm_hits, which tests and the siege and away code read) and in its 16-tile
// area's own list (rm_hit_cells), which the 3D view reads: so a big fight elsewhere never pushes yours out (server
// cost, 2026-10-24). The 13th field is whose the attacker is.
#define RM_HIT_CELL 16
#define RM_HIT_CELL_KEPT 160    // the newest hits kept in one area (as many as the whole world kept before)
var/list/rm_hit_cells = list()   // "cx,cy,z" -> hit records, oldest first
proc/RemasterHitAt(x, y, z, amount, kind, mob/by, owner, proj)
	var/list/H = list(++rm_hit_id, x, y, z, amount, kind, world.time, owner, by ? by.x : x, by ? by.y : y, RemasterWeaponClass(by), proj, by ? by.Owner : null, istype(by, /mob/Monsters) ? by:rm_move_now : null, by && (proj in list("arrow", "javelin", "axe", "rock")) ? by.rm_shot_part : null)   // 14th: the weapon move it is (WeaponSkills.dm); 15th: where a shot struck (Combat - Bows.dm, Throwing.dm)
	if(by && (proj in list("arrow", "javelin", "axe", "rock"))) by.rm_shot_part = null
	rm_hits += list(H)
	if(length(rm_hits) > 160) rm_hits.Cut(1, length(rm_hits) - 159)
	RmHudHurry(owner)                 // Hidden Clans: both sides' players see the blow this tick, not at the next
	if(by) RmHudHurry(by.Owner)       // half-second update (Drive.dm)
	var/ck = "[round((x - 1) / RM_HIT_CELL)],[round((y - 1) / RM_HIT_CELL)],[z]"
	var/list/C = rm_hit_cells[ck]
	if(!C)
		C = list()
		rm_hit_cells[ck] = C
	C += list(H)
	var/old = 0
	for(var/list/O in C)
		if(world.time - O[7] <= 20) break
		old++
	if(old) C.Cut(1, old + 1)
	if(length(C) > RM_HIT_CELL_KEPT) C.Cut(1, length(C) - RM_HIT_CELL_KEPT + 1)

// For the 3D view: strikes in the last 2 seconds near this player's camera, that they (or an ally, Fog.dm) can see:
// with fog of war on, a blow on a creature they can't see isn't shown (the creature isn't drawn either).
// "mineby": one of their units struck it. In time order, at most the newest 160 (as many as the world kept before).
Player/proc/RemasterHitData()
	var/list/lists = list()   // each area's hits that are shown, in time order
	var/fog = RmFogOn(z)
	for(var/cy = round((y - 25) / RM_HIT_CELL), cy <= round((y + 23) / RM_HIT_CELL), cy++)
		for(var/cx = round((x - 25) / RM_HIT_CELL), cx <= round((x + 23) / RM_HIT_CELL), cx++)
			var/list/C = rm_hit_cells["[cx],[cy],[z]"]
			if(!C) continue
			var/list/got = list()
			for(var/list/H in C)
				if(world.time - H[7] > 20 || abs(H[2] - x) > 24 || abs(H[3] - y) > 24) continue
				if(fog && H[8] != src && H[13] != src && !RmFogSees(locate(H[2], H[3], z))) continue
				got += list(H)
			if(length(got)) lists += list(got)
	// merged from the newest ends (ids grow with time), at most 160, then given oldest first
	var/list/ends = list()
	for(var/list/L in lists) ends += length(L)
	var/list/newest = list()
	while(length(newest) < 160)
		var/best = 0
		for(var/i = 1, i <= length(lists), i++) if(ends[i] && (!best || lists[i][ends[i]][1] > lists[best][ends[best]][1])) best = i
		if(!best) break
		newest += list(lists[best][ends[best]])
		ends[best]--
	. = list()
	for(var/i = length(newest), i >= 1, i--)
		var/list/H = newest[i]
		. += list(list("id"=H[1], "x"=H[2], "y"=H[3], "n"=H[5], "k"=H[6], "mine"=(H[8] == src), "mineby"=(H[13] == src), "ax"=H[9], "ay"=H[10], "w"=H[11], "p"=H[12], "mv"=H[14], "pt"=(length(H) >= 15 ? H[15] : null)))
