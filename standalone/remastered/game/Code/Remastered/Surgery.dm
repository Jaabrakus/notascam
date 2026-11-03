// Rescue and surgery (Remastered, SS13's medbay).
//  - The Operating table (Build tab, 1 wood) goes near the Doctor's stall (the Doctor uses the
//    nearest one within 40 tiles).
//  - Rescue: a villager who is down (unconscious, knocked out, can't walk, or near death) is
//    carried by the Doctor to the table, then treated there.
//  - Surgery at the table, by the Doctor: limbs. Any severed limb can be grafted where one is
//    missing (an arm for an arm, a leg for a leg): the villager's own, someone else's, another
//    race's. An Orc's arm on a Human brings some of an Orc's strength, an Elf's some quickness, and
//    so on. Foreign flesh may be rejected (one time in seven: it withers and drops off within a few
//    minutes). A Demon's flesh does to the one it is sewn onto what the hell portal does to those
//    who pass it: some go mad with the horror, some are possessed and turn half-demon. A body brought to the table gives up its arms and legs. Or a false limb, made at the
//    table: an iron arm or leg (2 iron ingots: tough, a bit slow), a wooden peg leg (1 wood: slow),
//    a bone arm or leg (3 bones), a glimmering arm or leg (a cut gem: quick, and some mana), or
//    automail, a jointed steel limb (3 iron ingots and 1 silver ingot for its springs, and a smith's
//    hand to make it: metal crafting 15+): strong, tough and even a little quick.
//  - The chance is 40% + 2% per point of potion skill + half the butchery skill (false limbs 20%
//    more), at most 95%. A failed graft ruins the flesh. A villager awake on the table may go into
//    shock (fainting, health lost, a bad memory): the Doctor first gives a Sleeping Draught it
//    carries, if any.
//  - Each limb's kind is remembered (rm_limbs, saved) and shows when the unit is examined; when the
//    limb is lost again its effect goes with it.

var/list/rm_tables = list()

// Slot -> the vars that hold it.
var/list/rm_limb_slots = list(
	"Left Arm"=list("HasLeftArm", "LeftArmHP", "LeftArm", "CanUseLeftArm"),
	"Right Arm"=list("HasRightArm", "RightArmHP", "RightArm", "CanUseRightArm"),
	"Left Leg"=list("HasLeftLeg", "LeftLegHP", "LeftLeg", null),
	"Right Leg"=list("HasRightLeg", "RightLegHP", "RightLeg", null))

// What another race's flesh brings: strength, agility, defence.
var/list/rm_race_limbs = list(
	"Orc"=list(3, 0, 0), "Human"=list(1, 1, 0), "Dwarf"=list(1, 0, 2), "Elf"=list(0, 3, 0),
	"Goblin"=list(0, 2, 0), "Kobold"=list(-1, 3, 0), "Lizardman"=list(1, 0, 1), "Frogman"=list(0, 2, 0),
	"Ratman"=list(0, 2, 0), "Gargoyle"=list(0, -2, 3), "Vampire"=list(2, 1, 0), "Demon"=list(3, 0, 1),
	"Svartalfar"=list(0, 2, 1), "Zombie"=list(1, -1, 0), "Skeleton"=list(1, 0, 1))

// False limbs: id -> list(name, strength, agility, defence, mana, look)
var/list/rm_prostheses = list(
	"iron"=list("Iron", 0, -2, 3, 0, "a clanking iron"),
	"wood"=list("Wooden peg", 0, -3, 0, 0, "a wooden peg"),
	"bone"=list("Bone", 1, 0, 1, 0, "a bare bone"),
	"gem"=list("Glimmering", 0, 2, 0, 20, "a glimmering"),
	"automail"=list("Automail", 3, 1, 2, 0, "an automail"))

mob/Monsters/var
	list/rm_limbs                  // saved: slot -> "kind|label|str|agi|def|mana|race" (race: whose flesh)
mob/Monsters/var/tmp
	list/rm_reject_at              // slot -> when foreign flesh drops off
	mob/Monsters/rm_carried_by     // the Doctor carrying this one to the table

obj/Items/Bones/BloodyLimb/var/rm_from_race   // whose flesh (set when it comes off, Combats.dm)

obj/Items/RemasterLimb
	// its values: art/items/catalogue.json row remasterlimb (export_items.py writes ItemData.dm)
	var/kind = "iron"
	var/part = "arm"

	New()
		..()
		RemasterLimbLook()

obj/Items/RemasterLimb/proc/RemasterLimbLook()
	var/list/K = rm_prostheses[kind]
	if(K) name = "[K[1]] [part]"
	desc = "A false [part], for the Operating table."
	icon_state = part == "leg" ? "Leg" : "Arm"
	color = list("iron"="#9aa0a8", "wood"="#9a6a3a", "bone"="#e8e0c8", "gem"="#a8e8ff", "automail"="#c8ccd4")[kind]

proc/RemasterLimbPart(obj/Items/I)
	if(istype(I, /obj/Items/RemasterLimb)) return I:part
	if(istype(I, /obj/Items/Bones/BloodyLimb)) return findtext(I.name, "Leg") ? "leg" : "arm"
	return null

mob/WorkShops/RemasterSurgery
	name = "Operating table"
	icon = 'Cave.dmi'
	icon_state = "Table"
	density = 1

	New()
		..()
		rm_tables += src

	Del()
		rm_tables -= src
		return ..()

	DblClick()
		if(istype(usr, /Player)) usr:RemasterNotice("Select a unit beside the Operating table: its box makes false limbs and asks the Doctor to operate.")

proc/RemasterTableBeside(mob/M)
	for(var/mob/WorkShops/RemasterSurgery/S in range(1, M)) return S
	return null

Player/proc/RemasterNearestTable(mob/M)
	var/mob/WorkShops/RemasterSurgery/best
	var/best_d = RM_DOCTOR_REACH + 1
	for(var/mob/WorkShops/RemasterSurgery/S in rm_tables) if(S.Owner == src && S.z == M.z)
		var/d = get_dist(S, M)
		if(d < best_d)
			best = S
			best_d = d
	return best

// --- Limbs ------------------------------------------------------------------------------------
mob/Monsters/proc/RemasterMissingSlots()
	. = list()
	for(var/slot in rm_limb_slots) if(!vars[rm_limb_slots[slot][1]]) . += slot

// The examine lines for grafted and false limbs (Speech.dm).
mob/Monsters/proc/RemasterLimbLooks()
	. = list()
	if(rm_limbs) for(var/slot in rm_limbs)
		var/list/p = splittext(rm_limbs[slot], "|")
		. += "[p[2]] [lowertext(slot)]"

// Put a limb on (no check: the surgery decides). Returns the label.
mob/Monsters/proc/RemasterAttachLimb(slot, obj/Items/I)
	var/list/V = rm_limb_slots[slot]
	if(!V || vars[V[1]]) return null
	var/s = 0
	var/a = 0
	var/d = 0
	var/m = 0
	var/kind
	var/label
	var/race = ""
	if(istype(I, /obj/Items/RemasterLimb))
		var/list/K = rm_prostheses[I:kind]
		kind = I:kind
		s = K[2]; a = K[3]; d = K[4]; m = K[5]
		label = K[6]
	else
		race = I:rm_from_race || "Human"
		var/own = findtext(I.name, RemasterBareName()) && race == Race
		kind = own ? "own" : "flesh"
		if(!own)
			var/list/R = rm_race_limbs[race] || list(1, 0, 0)
			s = R[1]; a = R[2]; d = R[3]
			label = race == Race ? "a grafted" : "a grafted [race]"
			if(prob(15))
				if(!rm_reject_at) rm_reject_at = list()
				rm_reject_at[slot] = world.time + rand(600, 2400)
			if(race == "Demon") spawn(10) RemasterDemonFlesh()
	vars[V[1]] = 1
	vars[V[2]] = OrganMaxHP
	vars[V[3]] = "Good"
	if(V[4]) vars[V[4]] = 1
	if(HasLeftLeg && HasRightLeg) CanWalk = 1
	if(label)
		if(!rm_limbs) rm_limbs = list()
		rm_limbs[slot] = "[kind]|[label]|[s]|[a]|[d]|[m]|[race]"
		Strength += s
		Agility += a
		Defence += d
		if(m && MaxMana) MaxMana += m
	LimbLoss()
	return label || "their own"

// Demon flesh sewn on: what the hell portal does to those who pass it (Vars.dm, Portal), with its
// odds. One in seven goes mad with the horror and tears their eyes out; of the rest, one in four is
// possessed, and turns over a few minutes into a half-demon and then a Demon (RaceChange, Race.dm).
mob/Monsters/proc/RemasterDemonFlesh()
	if(HP <= 0 || SubRace || Wagon || (Race in list("Demon", "Gargoyle", "Dragon"))) return 0
	var/Player/P = Owner
	if(prob(15))
		if(!CanSee || Unholy) return 0
		Owner << "[src] goes insane from the horror and tears their own eyes out!"
		HasLeftEye = 0
		HasRightEye = 0
		CanSee = 0
		RightEyeHP = 0
		LeftEyeHP = 0
		LeftEye = "Destroyed"
		RightEye = "Destroyed"
		RemasterSay("AAAAAH! GET IT OUT!", 1)
		if(istype(P)) P.RemasterFoodAlarm(src, "[RemasterBareName()] went mad from the demon's arm and tore out their own eyes.", "Surgery")
		return "mad"
	if(!prob(25) || !istype(P)) return 0
	Owner << "[src] is possessed by the demonic forces in the grafted flesh!"
	RaceChange(SUBRACE="HalfDemon")
	RemasterSay("I... hear... voices...", 1)
	P.RemasterFoodAlarm(src, "[RemasterBareName()] is possessed by the demon flesh sewn onto them: they are turning half-demon.", "Surgery")
	return "possessed"

// A limb's effect goes with it: lost again in a fight, or rejected.
mob/Monsters/proc/RemasterLimbCheck(Player/P)
	if(rm_reject_at) for(var/slot in rm_reject_at.Copy()) if(world.time >= rm_reject_at[slot])
		rm_reject_at -= slot
		var/list/V = rm_limb_slots[slot]
		if(!vars[V[1]]) continue
		vars[V[1]] = 0
		if(V[4]) vars[V[4]] = 0
		if(slot in list("Left Leg", "Right Leg")) CanWalk = HasLeftLeg && HasRightLeg ? CanWalk : 0
		view(src) << "<font color=#c0a040>[src]'s grafted [lowertext(slot)] withers and drops off!</font>"
		RemasterSay("My [lowertext(slot)]!", 1)
		LimbLoss()
		if(istype(P)) P.RemasterFoodAlarm(src, "[RemasterBareName()]'s body rejected the grafted [lowertext(slot)]: it fell off.", "Surgery")
	if(rm_limbs) for(var/slot in rm_limbs.Copy())
		var/list/V = rm_limb_slots[slot]
		if(vars[V[1]]) continue
		var/list/p = splittext(rm_limbs[slot], "|")
		Strength -= text2num(p[3])
		Agility -= text2num(p[4])
		Defence -= text2num(p[5])
		if(text2num(p[6]) && MaxMana) MaxMana -= text2num(p[6])
		rm_limbs -= slot

// --- How it looks in 3D (View3D.dm, Remaster3DLayers) -------------------------------------------
// The body is drawn without its grafted and false limbs (the original's "No..." pictures) and each
// laid on it from Icons/Remastered/Limbs64 (art/enhance/limbs64.py). The limb keeps the wearer's own
// shape, so it fits from every side; a graft is in the donor race's skin (an Orc's green, a
// skeleton's bones, a lizardman's scales) with stitches where it was sewn on, a false limb in iron,
// wood, bone, gem or automail.

// Missing (or replaced) left arm, right arm, left leg, right leg -> the original's picture, as
// LimbLoss() (Combats.dm) names them.
var/list/rm_limb_states = list("0000"="Normal", "1000"="NoLeftArm", "0100"="NoRightArm", "0010"="NoLeftLeg",
	"0001"="NoRightLeg", "1100"="NoArms", "0011"="NoLegs", "1001"="NoRightLegNoLeftArm", "0110"="NoLeftLegNoRightArm",
	"0101"="NoRightArmNoRightLeg", "1010"="NoLeftArmNoLeftLeg", "0111"="NoLegsNoRightArm", "1011"="NoLegsNoLeftArm",
	"1101"="NoArmsNoRightLeg", "1110"="NoArmsNoLeftLeg", "1111"="None")

// Whose skin a race's flesh is drawn in (beyond Gear.dm's rm_race_sheets).
var/list/rm_limb_sheets = list("Vampire"="Vampire", "Skeleton"="Skeleton", "Zombie"="DevourerZombie", "Devourer"="DevourerZombie")

// list(body state, limb layers) for a unit with grafted or false limbs, or null.
mob/Monsters/proc/RemasterLimbLayers(body64)
	if(!body64 || !length(rm_limbs)) return null
	var/sheet = RmRaceSheet(src)
	if(!sheet || !fexists("Icons/Remastered/Limbs64/[sheet].dmi")) return null
	var/limbs = file("Icons/Remastered/Limbs64/[sheet].dmi")
	var/list/layers = list()
	var/bits = ""
	for(var/slot in rm_limb_slots)
		var/has = vars[rm_limb_slots[slot][1]]
		var/grafted = has && rm_limbs[slot]
		bits += (!has || grafted) ? "1" : "0"
		if(!grafted) continue
		var/key = replacetext(slot, " ", "")
		var/list/p = splittext(rm_limbs[slot], "|")
		if(p[1] in rm_prostheses)
			layers += list(list(limbs, "[key]:[p[1]]"))
			continue
		var/race = length(p) >= 7 && p[7] ? p[7] : Race
		var/donor = rm_race_sheets[race] || rm_limb_sheets[race] || sheet
		if(!("[key]@[donor]" in icon_states(limbs))) donor = sheet
		layers += list(list(limbs, "[key]@[donor]"))
	return list(rm_limb_states[bits] || "Normal", layers)

// --- Rescue -------------------------------------------------------------------------------------
mob/Monsters/proc/RemasterIsDown()
	return HP > 0 && !GoingToDie && (Fainted || RemasterKnockedOut() || !CanWalk || HP < MAXHP * 0.25)

// The Doctor's first duty (Doctor.dm): bring the fallen to the table. 1 while busy with it.
mob/Monsters/proc/RemasterDoctorRescue(Player/P)
	var/mob/WorkShops/RemasterSurgery/S = P.RemasterNearestTable(src)
	if(!S) return 0
	var/mob/Monsters/carried
	for(var/mob/Monsters/M in P.UnitList) if(M.rm_carried_by == src) carried = M
	if(carried)
		if(get_dist(src, S) <= 1)
			carried.rm_carried_by = null
			var/turf/T = RemasterTileNear(S, carried)
			if(T) carried.loc = T
			RemasterSay("On the table with you.")
			remaster_work_status = "Doctor: brought [carried.RemasterBareName()] to the table"
			return 1
		var/turf/behind = get_step(src, turn(dir, 180))
		carried.loc = (behind && !behind.density) ? behind : loc
		RemasterWorkToward(S, "the Operating table")
		remaster_work_status = "Doctor: carrying [carried.RemasterBareName()] to the table"
		return 1
	var/mob/Monsters/down
	var/best = RM_DOCTOR_REACH + 1
	for(var/mob/Monsters/M in P.UnitList)
		if(M == src || M.Owner != P || M.z != z || !isturf(M.loc) || M.Wagon || M.Egg || !M.RemasterIsDown()) continue
		if(get_dist(M, S) <= 2) continue
		var/d = get_dist(M, src)
		if(d < best)
			down = M
			best = d
	if(!down) return 0
	if(!RemasterWorkToward(down, "the fallen"))
		remaster_work_status = "Doctor: going to [down.RemasterBareName()], who is down"
		return 1
	down.rm_carried_by = src
	rm_carry_list |= down
	down.destination = null
	RemasterSay(RemasterLine(list("I've got you.", "Easy now, up you come.", "Stretcher!")), 1)
	return 1

// --- Surgery ----------------------------------------------------------------------------------
// A limb the Doctor can use for part ("arm"/"leg"): carried by the Doctor, or by a villager at the
// table (the patient bringing their own arm, the smith a false leg), or lying near the table or on a
// store.
mob/Monsters/proc/RemasterFindLimb(Player/P, part, mob/WorkShops/RemasterSurgery/S)
	for(var/obj/Items/I in src) if(I.suffix == "(Carrying)" && RemasterLimbPart(I) == part) return I
	for(var/mob/Monsters/H in range(2, S)) if(H != src && H.Owner == P && H.HP > 0)
		for(var/obj/Items/I in H) if(I.suffix == "(Carrying)" && RemasterLimbPart(I) == part) return I
	var/obj/Items/best
	var/best_d = 1#INF
	for(var/obj/Items/I in range(15, S)) if(isturf(I.loc) && RemasterLimbPart(I) == part && P.RemasterMayCollect(I))
		var/d = get_dist(I, src)
		if(d < best_d)
			best = I
			best_d = d
	if(!best) for(var/turf/T in P.RemasterStores()) if(T.z == z) for(var/obj/Items/I in range(1, T)) if(isturf(I.loc) && RemasterLimbPart(I) == part && P.RemasterMayCollect(I))
		return I
	// A body laid beside the table: the Doctor takes the limb from it.
	if(!best) for(var/mob/Body/B in range(1, S)) if(isturf(B.loc) && !B.Critter && B.rm_limbs_taken < 4)
		return RemasterTakeLimb(B, part, B.loc)
	return best

// The Doctor's surgery step (Doctor.dm): a villager missing a limb, a limb for it, the table. 1
// while busy with it.
mob/Monsters/proc/RemasterDoctorSurgery(Player/P)
	var/mob/WorkShops/RemasterSurgery/S = P.RemasterNearestTable(src)
	if(!S) return 0
	var/mob/Monsters/pat
	var/slot
	var/obj/Items/limb
	for(var/mob/Monsters/M in P.UnitList)
		if(M.Owner != P || M.z != z || M.HP <= 0 || M.Wagon || M.Egg || !isturf(M.loc) || get_dist(M, S) > RM_DOCTOR_REACH) continue
		for(var/s in M.RemasterMissingSlots())
			var/obj/Items/L = RemasterFindLimb(P, findtext(s, "Leg") ? "leg" : "arm", S)
			if(!L) continue
			pat = M
			slot = s
			limb = L
			break
		if(pat) break
	if(!pat) return 0
	// The limb in hand: handed over by the villager carrying it, or picked up.
	if(ismob(limb.loc) && limb.loc != src)
		var/mob/Monsters/H = limb.loc
		if(!RemasterWorkToward(H, H.RemasterBareName()))
			remaster_work_status = "Doctor: going to [H.RemasterBareName()] for the [limb.name]"
			return 1
		if(RemasterHandOver(limb, H, src)) return 1
		H.DropItem(limb)
		return 1
	if(limb.loc != src)
		if(!RemasterWorkToward(limb, "the [limb.name]"))
			remaster_work_status = "Doctor: fetching the [limb.name] for [pat.RemasterBareName()]"
			return 1
		if(!PickUpItem(limb)) ForcePickUpItem(limb)
		return 1
	// Patient and Doctor at the table.
	if(get_dist(pat, S) > 2)
		if(!pat.remaster_care && !pat.RemasterHasOrder())
			var/turf/T = RemasterTileNear(S, pat)
			if(T) pat.destination = T
		if(!RemasterWorkToward(S, "the Operating table")) return 1
		remaster_work_status = "Doctor: waiting at the table for [pat.RemasterBareName()]"
		return 1
	if(!RemasterWorkToward(S, "the Operating table")) return 1
	return RemasterOperate(P, pat, slot, limb)

mob/Monsters/proc/RemasterOperate(Player/P, mob/Monsters/pat, slot, obj/Items/limb)
	var/what = limb.name
	// Asleep first, if the Doctor carries a Sleeping Draught.
	if(!pat.Sleeping && !pat.Fainted && !pat.RemasterKnockedOut())
		for(var/obj/Items/Potions/RemasterBrew/B in src) if((B.brew["sleepdraught"] || 0) >= 1)
			if(RemasterHandOver(B, src, pat)) P.RemasterDrinkBrew(pat, B)
			break
	var/awake = !pat.Sleeping && !pat.Fainted && !pat.RemasterKnockedOut()
	var/chance = clamp(40 + PotionSkill * 2 + ButcherySkill / 2 + (istype(limb, /obj/Items/RemasterLimb) ? 20 : 0), 5, 95)
	PotionSkill += 1
	RemasterSay(RemasterLine(list("Hold still...", "This won't hurt a bit.", "Scalpel.", "Easy now...")), 1)
	if(awake && prob(35 - PotionSkill / 2))
		pat.RemasterSay(RemasterLine(list("AAARGH!", "Stop! STOP!", "By the gods!")), 1)
		pat.HP -= 15
		pat.Fainted = 1
		spawn(300) if(pat && pat.Fainted && !pat.RemasterKnockedOut()) pat.Fainted = 0
		pat.RemasterRemember("surgery", "Operated on wide awake", -8, 2)
	if(!prob(chance))
		if(!istype(limb, /obj/Items/RemasterLimb))
			DropItem(limb)
			del limb
		pat.HP -= 20
		pat.BloodContent -= 40
		pat.BloodLoss()
		P.RemasterLog("[RemasterBareName()]'s surgery on [pat.RemasterBareName()] failed: the [what] was ruined", "problem", pat)
		remaster_work_status = "Doctor: the operation failed"
		return 1
	DropItem(limb)
	var/label = pat.RemasterAttachLimb(slot, limb)
	del limb
	pat.rm_bandaged_until = world.time + 3000
	pat.RemasterRemember("surgery", "Got a new [lowertext(slot)]", 4, 2)
	P.RemasterLog("[RemasterBareName()] gave [pat.RemasterBareName()] [label == "their own" ? "back their own [lowertext(slot)]" : "[label] [lowertext(slot)]"]", "good", pat)
	pat.RemasterSay(RemasterLine(list("It moves!", "Feels... strange.", "Thank you, Doctor!")), 1)
	remaster_work_status = "Doctor: attached [label] [lowertext(slot)] to [pat.RemasterBareName()]"
	return 1

// --- The table's box -------------------------------------------------------------------------
// What false limbs cost: id -> list(item type, how many[, a second type, how many])
proc/RemasterProsthesisCost(kind)
	switch(kind)
		if("iron") return list(/obj/Items/Ingots/IronIngot, 2)
		if("wood") return list(/obj/Items/woods/wood, 1)
		if("bone") return list(/obj/Items/Bones/Bones, 3)
		if("gem") return list(/obj/Items/gems, 1)
		if("automail") return list(/obj/Items/Ingots/IronIngot, 3, /obj/Items/Ingots/SilverIngot, 1)
	return null

mob/Monsters/proc/RemasterCountCarried(type)
	. = 0
	for(var/obj/Items/I in src) if(istype(I, type) && I.suffix == "(Carrying)") .++

// Make a false limb at the table from what the unit carries.
mob/Monsters/proc/RemasterMakeProsthesis(kind, part)
	var/list/C = RemasterProsthesisCost(kind)
	if(!C || (kind == "wood" && part != "leg")) return null
	if(kind == "automail" && MetalCraftingSkill < 15) return null
	for(var/i = 1, i < length(C), i += 2) if(RemasterCountCarried(C[i]) < C[i + 1]) return null
	for(var/i = 1, i < length(C), i += 2)
		var/n = C[i + 1]
		for(var/obj/Items/I in src)
			if(n <= 0) break
			if(I.suffix != "(Carrying)" || !istype(I, C[i])) continue
			DropItem(I)
			del I
			n--
	if(kind == "automail") MetalCraftingSkill += 1
	var/obj/Items/RemasterLimb/L = new
	L.kind = kind
	L.part = part
	L.RemasterLimbLook()
	L.loc = loc
	if(!PickUpItem(L)) L.loc = loc
	return L

// A body at the table gives up its arms and legs (up to two of each).
mob/Body/var/rm_limbs_taken = 0
proc/RemasterTakeLimb(mob/Body/B, part, atom/where)
	if(!B || B.rm_limbs_taken >= 4) return null
	B.rm_limbs_taken++
	var/obj/Items/Bones/BloodyLimb/L = new(where)
	L.name = "[RemasterDeadName(B)]'s [part == "leg" ? "Leg" : "Arm"]"
	L.icon_state = part == "leg" ? "Leg" : "Arm"
	L.rm_from_race = B.Race
	return L

Player/proc/RemasterTableBoxData(mob/Monsters/M)
	var/mob/WorkShops/RemasterSurgery/S = RemasterTableBeside(M)
	if(!S) return null
	var/list/kinds = list()
	for(var/k in rm_prostheses)
		var/list/C = RemasterProsthesisCost(k)
		var/ok = 1
		for(var/i = 1, i < length(C), i += 2) if(M.RemasterCountCarried(C[i]) < C[i + 1]) ok = 0
		if(k == "automail" && M.MetalCraftingSkill < 15) ok = 0
		kinds += list(list("id"=k, "name"=rm_prostheses[k][1], "ok"=ok, "what"=list("iron"="2 iron ingots", "wood"="1 wood (legs only)", "bone"="3 bones", "gem"="a cut gem", "automail"="3 iron ingots, 1 silver ingot, metal crafting 15")[k]))
	var/list/limbs = list()
	for(var/obj/Items/I in M) if(I.suffix == "(Carrying)" && RemasterLimbPart(I)) limbs += "[I.name]"
	var/mob/Body/B
	for(var/mob/Body/X in M) if(X.suffix == "(Carrying)") B = X
	if(!B) B = M.RmDraggedBeside()   // dragged beside the table (BodyDrag.dm)
	if(!B) for(var/mob/Body/X in range(1, S)) if(isturf(X.loc)) B = X
	var/doctor = 0
	for(var/mob/Monsters/D in UnitList) if(D.Owner == src && D.remaster_job == "doctor" && D.HP > 0) doctor = 1
	return list("own"=(S.Owner == src), "missing"=M.RemasterMissingSlots(), "grafts"=M.RemasterLimbLooks(), "limbs"=limbs, "kinds"=kinds,
		"body"=(B && B.rm_limbs_taken < 4 ? RemasterDeadName(B) : null), "doctor"=doctor)

// value: "unitref|action|arg"
Player/proc/RemasterTableCommand(value)
	var/list/p = splittext("[value]", "|")
	if(p.len < 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return 0
	var/mob/WorkShops/RemasterSurgery/S = RemasterTableBeside(M)
	if(!S || S.Owner != src)
		RemasterNotice("[M.RemasterBareName()] must stand beside your Operating table.")
		return 0
	var/arg = p.len >= 3 ? p[3] : ""
	switch(p[2])
		if("make")
			var/list/k = splittext(arg, ":")
			if(length(k) != 2) return 0
			var/obj/Items/L = M.RemasterMakeProsthesis(k[1], k[2])
			RemasterNotice(L ? "[M.RemasterBareName()] made a [L.name]." : "Not enough material carried for that.")
			return !!L
		if("harvest")
			var/mob/Body/B
			for(var/mob/Body/X in M) if(X.suffix == "(Carrying)") B = X
			if(!B) B = M.RmDraggedBeside()   // dragged beside the table (BodyDrag.dm)
			if(!B) for(var/mob/Body/X in range(1, S)) if(isturf(X.loc)) B = X
			var/obj/Items/L = RemasterTakeLimb(B, arg == "leg" ? "leg" : "arm", M.loc)
			if(L && !M.PickUpItem(L)) L.loc = M.loc
			RemasterNotice(L ? "[M.RemasterBareName()] took the [L.name] from the body." : "Nothing more to take.")
			return !!L
	return 0

// What the 3D view draws for a table, and for a unit with a glimmering limb.
proc/Remaster3DTable(mob/WorkShops/RemasterSurgery/S)
	var/busy = 0
	for(var/mob/Monsters/M in range(1, S)) if(M.Fainted || M.Sleeping) busy = 1
	return list("busy"=busy)
