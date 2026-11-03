// Herbs and the Doctor (Remastered). Three healing herbs grow wild around each village (and come
// with caravans). A Doctor's stall stores them and the remedies made from them; a villager given the
// Doctor job keeps it stocked and treats the sick. When something is wrong and there is no remedy,
// the Doctor makes one from herbs, and with no herbs posts a Board order to gather them, which Board
// workers take up (Board.dm): the work goes down the line by itself.
//  - Athelas (kingsfoil) -> Athelas poultice: closes wounds (+80 health) and stops bleeding.
//  - Feverfew -> Feverfew tonic: breaks the fever (Ailments.dm) and leaves the patient immune.
//  - Milk thistle -> Thistle purge: draws out 30 poison (FoodSupply.dm), settles food poisoning and
//    sobers. Poured into a poisoned pot or stall, it neutralises 30 of its poison.
//  - Remedies are made at the stall from one herb each: 50% + 3% per point of potion skill (the
//    original Potion skill); a failure wastes the herb.
//  - Herbs grow as perennial plants: picked down, they grow back a leaf every two minutes, up to
//    three. Nine are placed once around each village (three of each).
//  - Without a Doctor, sick villagers walk to a stall that has their remedy and take it themselves
//    (Care.dm); remedies in the bag are used from the bag like potions (Bag.dm).

#define RM_CLINIC_MAX 30
#define RM_DOCTOR_REACH 40

var/list/rm_clinics = list()

// --- Herbs and remedies ------------------------------------------------------------------------
// id -> list(name, herb item, remedy item, remedy name, what it treats)
var/list/rm_herbs = list(
	"athelas"=list("Athelas", /obj/Items/RemasterHerb/Athelas, "poultice", "Athelas poultice", "wounds and bleeding"),
	"feverfew"=list("Feverfew", /obj/Items/RemasterHerb/Feverfew, "tonic", "Feverfew tonic", "fever"),
	"thistle"=list("Milk thistle", /obj/Items/RemasterHerb/MilkThistle, "purge", "Thistle purge", "poison, food poisoning and drink"))

proc/RemasterHerbOf(remedy)
	for(var/h in rm_herbs) if(rm_herbs[h][3] == remedy) return h
	return null

proc/RemasterRemedyName(remedy)
	var/h = RemasterHerbOf(remedy)
	return h ? rm_herbs[h][4] : "remedy"

obj/Items/RemasterHerb
	// its values: art/items/catalogue.json row remasterherb (export_items.py writes ItemData.dm)
	var/herb = "athelas"

	New()
		..()
		ItemDecay()

	Athelas
		// its values: art/items/catalogue.json row remasterherb.athelas (export_items.py writes ItemData.dm)
	Feverfew
		// its values: art/items/catalogue.json row remasterherb.feverfew (export_items.py writes ItemData.dm)
	MilkThistle
		// its values: art/items/catalogue.json row remasterherb.milkthistle (export_items.py writes ItemData.dm)

obj/Items/RemasterRemedy
	// its values: art/items/catalogue.json row remasterremedy (export_items.py writes ItemData.dm)
	var/remedy = "poultice"

	Poultice
		// its values: art/items/catalogue.json row remasterremedy.poultice (export_items.py writes ItemData.dm)
	Tonic
		// its values: art/items/catalogue.json row remasterremedy.tonic (export_items.py writes ItemData.dm)
	Purge
		// its values: art/items/catalogue.json row remasterremedy.purge (export_items.py writes ItemData.dm)

proc/RemasterRemedyPath(remedy)
	switch(remedy)
		if("poultice") return /obj/Items/RemasterRemedy/Poultice
		if("tonic") return /obj/Items/RemasterRemedy/Tonic
		if("purge") return /obj/Items/RemasterRemedy/Purge
	return null

// What a patient most needs: list(remedy, urgency, why), or null.
mob/Monsters/proc/RemasterNeeds()
	if(HP <= 0 || GoingToDie || !RemasterPoisonable()) return null
	var/list/best
	var/list/cases = list()
	if(BleedType in list("Badly", "Very Badly", "Extremly")) cases += list(list("poultice", 6, "bleeding [BleedType == "Extremly" ? "extremely" : lowertext(BleedType)]"))
	if(rm_poison > 0 && rm_poison_sick) cases += list(list("purge", 5, "poisoned"))
	if(rm_fever) cases += list(list("tonic", 3 + rm_fever, "fever"))
	if(rm_foodsick > 0) cases += list(list("purge", 3, "food poisoning"))
	if(HP < MAXHP * 0.4) cases += list(list("poultice", 3, "badly hurt"))
	if(rm_drunk >= 60) cases += list(list("purge", 1, "very drunk"))
	for(var/list/C in cases) if(!best || C[2] > best[2]) best = C
	return best

// The remedy's effect on src.
mob/Monsters/proc/RemasterApplyRemedy(remedy, mob/Monsters/by)
	var/did
	switch(remedy)
		if("poultice")
			HP = min(MAXHP, HP + 80)
			if(BleedType)
				BleedType = null
				BloodContent = MaxBloodContent
			did = "wounds dressed"
		if("tonic")
			if(rm_fever || rm_fever_incub)
				RemasterFeverCured("Cured of the fever with a Feverfew tonic")
				did = "fever broken"
			else
				rm_immune = max(rm_immune, 600)
				did = "kept safe from the fever"
		if("purge")
			rm_poison = max(0, rm_poison - 30)
			if(rm_poison <= 0) rm_poison_sick = 0
			rm_foodsick = 0
			rm_drunk = max(0, rm_drunk - 50)
			did = "purged"
	if(!did) return 0
	view(src) << "[by && by != src ? "[by] treats [src]" : "[src] takes a remedy"]: [did]."
	RemasterEvent("[RemasterRemedyName(remedy)][by && by != src ? " from [by:RemasterBareName()]" : ""]: [did]")
	var/Player/P = Owner
	if(istype(P)) P.RemasterLog("[by && by != src ? "[by:RemasterBareName()] treated [RemasterBareName()] with" : "[RemasterBareName()] took"] the [RemasterRemedyName(remedy)] ([did])", "good", src)
	return 1

mob/Monsters/proc/RemasterCarriedRemedy(remedy)
	for(var/obj/Items/RemasterRemedy/R in src) if(R.remedy == remedy && R.suffix == "(Carrying)") return R
	return null

mob/Monsters/proc/RemasterCarriedHerb(herb)
	for(var/obj/Items/RemasterHerb/H in src) if(H.herb == herb && H.suffix == "(Carrying)") return H
	return null

// --- Herb plants -------------------------------------------------------------------------------
obj/Items/Plants/RemasterHerbPlant
	// its values: art/items/catalogue.json row plants.remasterherbplant (export_items.py writes ItemData.dm)
	var/herb = "athelas"

	New()
		..()
		spawn(20) RemasterHerbRegrow()

	DblClick()
		if(istype(usr, /Player)) usr:RemasterNotice("[name]: select a unit and click it to pick it ([Content] ready). Doctors and Board workers pick herbs by themselves.")

	Athelas
		// its values: art/items/catalogue.json row plants.remasterherbplant.athelas (export_items.py writes ItemData.dm)
	Feverfew
		// its values: art/items/catalogue.json row plants.remasterherbplant.feverfew (export_items.py writes ItemData.dm)
	MilkThistle
		// its values: art/items/catalogue.json row plants.remasterherbplant.milkthistle (export_items.py writes ItemData.dm)

obj/Items/Plants/RemasterHerbPlant/proc/RemasterHerbRegrow()
	while(src && loc)
		sleep(1200)
		if(Content < 3 && Season != "Winter") Content++

// Pick one: the herb goes into M's bag.
obj/Items/Plants/RemasterHerbPlant/proc/Pick(mob/Monsters/M)
	if(Content < 1 || get_dist(M, src) > 1) return null
	var/path = rm_herbs[herb][2]
	var/obj/Items/RemasterHerb/H = new path(M.loc)
	if(!M.PickUpItem(H))
		del H
		return null
	Content--
	return H

proc/RemasterHerbPlantPath(herb)
	switch(herb)
		if("athelas") return /obj/Items/Plants/RemasterHerbPlant/Athelas
		if("feverfew") return /obj/Items/Plants/RemasterHerbPlant/Feverfew
		if("thistle") return /obj/Items/Plants/RemasterHerbPlant/MilkThistle
	return null

Player/var/rm_herbs_placed = 0      // saved: the wild herbs around this village were placed

// Once per village: three of each herb on open grass 6-25 tiles from the stockpile (or the first unit).
Player/proc/RemasterPlaceWildHerbs()
	if(rm_herbs_placed) return
	var/atom/C = RemasterStockpile()
	if(!C) for(var/mob/Monsters/M in UnitList) if(M.Owner == src && isturf(M.loc))
		C = M
		break
	if(!C || C.z != 1) return
	rm_herbs_placed = 1
	var/list/kinds = list("athelas", "athelas", "athelas", "feverfew", "feverfew", "feverfew", "thistle", "thistle", "thistle")
	for(var/i = 1, i <= 200 && length(kinds), i++)
		var/turf/T = locate(C.x + rand(-25, 25), C.y + rand(-25, 25), C.z)
		if(!T || T.density || get_dist(T, C) < 6 || !istype(T, /turf/grounds) || T.icon_state == "FarmLand") continue
		if(locate(/obj/Items/Plants) in T) continue
		var/path = RemasterHerbPlantPath(kinds[1])
		new path(T)
		kinds.Cut(1, 2)

// The nearest herb plant of that kind with a leaf ready, within reach of A.
proc/RemasterHerbPlantNear(atom/A, herb, reach = 30)
	var/obj/Items/Plants/RemasterHerbPlant/best
	var/best_d = reach + 1
	for(var/obj/Items/Plants/RemasterHerbPlant/H in range(reach, A))
		if((herb && H.herb != herb) || H.Content < 1) continue
		var/d = get_dist(H, A)
		if(d < best_d)
			best = H
			best_d = d
	return best

// --- The Doctor's stall ------------------------------------------------------------------------
mob/WorkShops/RemasterClinic
	name = "Doctor's stall"
	icon = 'Cave.dmi'
	icon_state = "Table"
	density = 1
	var/athelas = 0
	var/feverfew = 0
	var/thistle = 0
	var/poultice = 0
	var/tonic = 0
	var/purge = 0

	New()
		..()
		rm_clinics += src

	Del()
		rm_clinics -= src
		return ..()

	DblClick()
		if(istype(usr, /Player)) usr:RemasterNotice("Select a unit beside the Doctor's stall: its box shows the herbs and remedies.")

mob/WorkShops/RemasterClinic/proc/Total()
	return athelas + feverfew + thistle + poultice + tonic + purge

mob/WorkShops/RemasterClinic/proc/Remedies()
	return poultice + tonic + purge

// An herb or a remedy (herb and remedy ids are the var names) put in from a unit's bag.
mob/WorkShops/RemasterClinic/proc/PutIn(obj/Items/I)
	var/id = istype(I, /obj/Items/RemasterHerb) ? I:herb : istype(I, /obj/Items/RemasterRemedy) ? I:remedy : null
	if(!id || Total() >= RM_CLINIC_MAX) return 0
	vars[id] = vars[id] + 1
	if(ismob(I.loc))
		var/mob/H = I.loc
		H.DropItem(I)
	del I
	return 1

// One remedy into M's bag.
mob/WorkShops/RemasterClinic/proc/TakeOut(remedy, mob/Monsters/M)
	if(!(remedy in list("poultice", "tonic", "purge")) || vars[remedy] < 1) return null
	var/path = RemasterRemedyPath(remedy)
	var/obj/Items/RemasterRemedy/R = new path(M.loc)
	if(!M.PickUpItem(R))
		del R
		return null
	vars[remedy] = vars[remedy] - 1
	return R

// M makes a remedy from one of the stall's herbs (or one M carries).
mob/WorkShops/RemasterClinic/proc/Make(herb, mob/Monsters/M)
	var/list/H = rm_herbs[herb]
	if(!H) return 0
	var/obj/Items/RemasterHerb/carried = M.RemasterCarriedHerb(herb)
	if(carried) PutIn(carried)
	if(vars[herb] < 1) return 0
	vars[herb] = vars[herb] - 1
	M.PotionSkill += 1
	if(!prob(50 + (M.PotionSkill - 1) * 3))
		view(M) << "[M] spoils the [lowertext(H[1])]."
		return -1
	vars[H[3]] = vars[H[3]] + 1
	return 1

proc/RemasterClinicBeside(mob/M)
	for(var/mob/WorkShops/RemasterClinic/S in range(1, M)) return S
	return null

// The nearest own stall on M's level (with the remedy or herb id in stock when one is given).
Player/proc/RemasterClinicWith(id, mob/M, reach = RM_DOCTOR_REACH)
	var/mob/WorkShops/RemasterClinic/best
	var/best_d = reach + 1
	for(var/mob/WorkShops/RemasterClinic/S in rm_clinics)
		if(S.Owner != src || S.z != M.z || (id && S.vars[id] < 1)) continue
		var/d = get_dist(S, M)
		if(d < best_d)
			best = S
			best_d = d
	return best

Player/proc/RemasterHasDoctor()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0 && M.remaster_job == "doctor") return 1
	return 0

// --- The Board: gathering herbs (Board.dm) ------------------------------------------------------
proc/RemasterHerbKinds()
	. = list()
	for(var/h in rm_herbs) .["herb_[h]"] = list("label"="Gather [lowertext(rm_herbs[h][1])]", "noun"=lowertext(rm_herbs[h][1]), "role"="herbs", "type"=rm_herbs[h][2])

// Herbs in the stalls count as gathered (RemasterStockCount).
Player/proc/RemasterClinicHerbs(path)
	. = 0
	for(var/h in rm_herbs) if(rm_herbs[h][2] == path) for(var/mob/WorkShops/RemasterClinic/S in rm_clinics) if(S.Owner == src) . += S.vars[h]

// A Doctor short of an herb asks for it, unless it's already on the Board.
Player/proc/RemasterAskForHerb(herb, amount, priority, why)
	for(var/list/O in remaster_board_orders) if(!O["done"] && O["kind"] == "herb_[herb]") return O
	var/list/O = RemasterBoardPost("herb_[herb]", amount, priority, 1, null, null, null)
	if(O)
		O["note"] = why
		RemasterLog("The Doctor posted on the Board: [O["label"]] ([why])", "work", RemasterStockpile())
	return O

// A Board worker on an herb order (and a Doctor gathering): pick the herb nearby, take it to the
// Doctor's stall (or the stockpile).
mob/Monsters/proc/RemasterHerbGatherTick(Player/P, herb)
	var/obj/Items/RemasterHerb/carried = herb ? RemasterCarriedHerb(herb) : (locate(/obj/Items/RemasterHerb) in src)
	var/n = 0
	for(var/obj/Items/RemasterHerb/H in src) if(H.suffix == "(Carrying)") n++
	var/turf/S = P.RemasterStockpile()
	var/atom/C = (S && S.z == z) ? S : src
	var/obj/Items/Plants/RemasterHerbPlant/plant = n < 3 ? RemasterHerbPlantNear(C, herb, 30) : null
	if(plant)
		if(!RemasterWorkToward(plant, lowertext(plant.name))) return 1
		var/obj/Items/RemasterHerb/got = plant.Pick(src)
		remaster_work_status = got ? "Picked [lowertext(got.name)]" : "Can't carry more"
		return 1
	if(carried)
		var/mob/WorkShops/RemasterClinic/K = P.RemasterClinicWith(null, src)
		if(K)
			if(!RemasterWorkToward(K, "Doctor's stall")) return 1
			var/put = 0
			for(var/obj/Items/RemasterHerb/H in src) if(H.suffix == "(Carrying)" && K.PutIn(H)) put++
			remaster_work_status = "Put [put] herb\s in the Doctor's stall"
			return 1
		var/list/L = list()
		for(var/obj/Items/RemasterHerb/H in src) if(H.suffix == "(Carrying)") L += H
		return RemasterStoreFood(P, L, "herbs")
	remaster_work_status = "No [herb ? lowertext(rm_herbs[herb][1]) : "herbs"] ready within 30 tiles (they grow back; caravans sell them)"
	return 0

// --- The Doctor -----------------------------------------------------------------------------------
// A patient: the own villager in most need of a remedy within reach of the Doctor.
Player/proc/RemasterNextPatient(mob/Monsters/D)
	var/list/best
	for(var/mob/Monsters/M in UnitList)
		if(M.Owner != src || M.z != D.z || get_dist(M, D) > RM_DOCTOR_REACH || M.Wagon || M.Egg) continue
		var/list/N = M.RemasterNeeds()
		if(!N) continue
		if(!best || N[2] > best[3] || (N[2] == best[3] && get_dist(M, D) < get_dist(best[1], D))) best = list(M, N[1], N[2], N[3])
	return best

// The Doctor's job (Settlement.dm): treat the sick, then poisoned food, then keep the stall stocked.
mob/Monsters/proc/RemasterDoctorTick(Player/P)
	if(Race == "Spider" || Wagon)
		remaster_work_status = "This unit can't work as a Doctor"
		return
	P.RemasterPlaceWildHerbs()
	if(RemasterDoctorRescue(P)) return       // the fallen to the Operating table first (Surgery.dm)
	// While a remedy waits on the Board, the Doctor gets on with the rest (waiting: what it waits for).
	var/waiting
	var/list/C = P.RemasterNextPatient(src)
	if(C)
		var/mob/Monsters/pat = C[1]
		var/got = RemasterDoctorGet(P, C[2], "[pat.RemasterBareName()] ([C[4]])")
		if(got == 1)
			if(pat == src || RemasterWorkToward(pat, "patient"))
				var/obj/Items/RemasterRemedy/R = RemasterCarriedRemedy(C[2])
				if(pat.RemasterApplyRemedy(C[2], src))
					weight -= R.weight
					del R
					remaster_work_status = "Doctor: treated [pat.RemasterBareName()] ([C[4]])"
			else remaster_work_status = "Doctor: going to [pat.RemasterBareName()] ([C[4]])"
			return
		if(got == 0) return
		waiting = remaster_work_status
	if(RemasterDoctorSurgery(P)) return      // a missing limb and a limb for it (Surgery.dm)
	// Poisoned food: check what's under suspicion, neutralise what's poisoned.
	var/mob/WorkShops/RemasterFood/F
	var/fd = RM_DOCTOR_REACH + 1
	for(var/mob/WorkShops/RemasterFood/X in rm_food_places) if(X.Owner == P && X.z == z && X.rm_suspect)
		var/d = get_dist(X, src)
		if(d < fd)
			F = X
			fd = d
	if(F && F.rm_suspect != 1)
		var/got = RemasterDoctorGet(P, "purge", "the poisoned [lowertext(F.name)]")
		if(got == 0) return
		if(got == -1)
			waiting = waiting || remaster_work_status
			F = null
	if(F)
		var/what = lowertext(F.name)
		if(F.rm_suspect == 1)
			if(!RemasterWorkToward(F, what)) return
			var/r = RemasterInspectFood(F)
			remaster_work_status = r == "poisoned" ? "Doctor: found the [what] poisoned" : r == "clean" ? "Doctor: the [what] is clean" : "Doctor: checking the [what]"
			if(r == "poisoned") P.RemasterFoodAlarm(F, "The Doctor found the [what] at [F.x], [F.y] poisoned. A Thistle purge will neutralise it.")
			return
		if(!RemasterWorkToward(F, what))
			remaster_work_status = "Doctor: taking a Thistle purge to the poisoned [what]"
			return
		var/obj/Items/RemasterRemedy/R = RemasterCarriedRemedy("purge")
		weight -= R.weight
		del R
		F.RemasterCleanse(30)
		if(!F.Poisoned())
			F.rm_suspect = 0
			F.rm_suspect_why = ""
			P.RemasterLog("[RemasterBareName()] neutralised the poison in the [what] at [F.x], [F.y]", "good", F)
			remaster_work_status = "Doctor: the [what] is safe again"
		else remaster_work_status = "Doctor: poured a purge into the [what]; more is needed"
		return
	// Keep two of each remedy in the stall: make them from herbs, bring herbs in, or ask for them.
	var/mob/WorkShops/RemasterClinic/S = P.RemasterClinicWith(null, src)
	if(!S)
		remaster_work_status = "Doctor: build a Doctor's stall (Place tab) to keep herbs and make remedies"
		return
	for(var/h in rm_herbs)
		var/rid = rm_herbs[h][3]
		if(S.vars[rid] >= 2) continue
		if(S.vars[h] > 0 || RemasterCarriedHerb(h))
			if(!RemasterWorkToward(S, "Doctor's stall")) return
			var/r = S.Make(h, src)
			remaster_work_status = r > 0 ? "Doctor: made a [rm_herbs[h][4]]" : "Doctor: spoiled the [lowertext(rm_herbs[h][1])]"
			return
		if(RemasterHerbPlantNear(S, h, 25) && RemasterHerbGatherTick(P, h)) return
		P.RemasterAskForHerb(h, 3, 3, "to keep [rm_herbs[h][4]]s in stock")
	// Herbs carried back go in the stall.
	for(var/obj/Items/RemasterHerb/H in src) if(H.suffix == "(Carrying)")
		if(!RemasterWorkToward(S, "Doctor's stall")) return
		S.PutIn(H)
		return
	if(get_dist(src, S) > 2)
		RemasterWorkToward(S, "Doctor's stall")
		remaster_work_status = waiting || "Doctor: going back to the stall"
		return
	remaster_work_status = waiting || "Doctor: all well (poultices [S.poultice], tonics [S.tonic], purges [S.purge])"

// Get the remedy in hand: from the bag, the stall, made from an herb at the stall, or asked for on
// the Board. 1 when carried now, 0 while busy getting it, -1 when it waits on the Board.
mob/Monsters/proc/RemasterDoctorGet(Player/P, remedy, why)
	if(RemasterCarriedRemedy(remedy)) return 1
	var/herb = RemasterHerbOf(remedy)
	var/mob/WorkShops/RemasterClinic/S = P.RemasterClinicWith(remedy, src)
	if(S)
		if(!RemasterWorkToward(S, "Doctor's stall"))
			remaster_work_status = "Doctor: fetching a [RemasterRemedyName(remedy)] for [why]"
			return 0
		S.TakeOut(remedy, src)
		return !!RemasterCarriedRemedy(remedy)
	S = P.RemasterClinicWith(herb, src)
	if(!S && RemasterCarriedHerb(herb)) S = P.RemasterClinicWith(null, src)
	if(S)
		if(!RemasterWorkToward(S, "Doctor's stall"))
			remaster_work_status = "Doctor: going to make a [RemasterRemedyName(remedy)] for [why]"
			return 0
		var/r = S.Make(herb, src)
		remaster_work_status = r > 0 ? "Doctor: made a [RemasterRemedyName(remedy)] for [why]" : "Doctor: spoiled the [lowertext(rm_herbs[herb][1])]; trying again"
		if(r > 0) S.TakeOut(remedy, src)
		return 0
	// No herb: pick it if any grows near, and ask the Board for it.
	P.RemasterAskForHerb(herb, 2, 1, "for [why]")
	if(RemasterHerbPlantNear(src, herb, 25) && RemasterHerbGatherTick(P, herb)) return 0
	remaster_work_status = "Doctor: needs [lowertext(rm_herbs[herb][1])] for [why]: posted on the Board"
	return -1

// A purge poured into poisoned food: the pot's stew, or the poisoned pieces on a stall.
mob/WorkShops/RemasterFood/proc/RemasterCleanse(amount)
	rm_poison = max(0, rm_poison - amount)
	for(var/list/E in Items())
		if(amount <= 0) break
		var/t = min(E[6], amount)
		E[6] -= t
		amount -= t
	Store()

// Care without a Doctor (Care.dm): go to a stall with the remedy, take it there.
mob/Monsters/proc/RemasterCareRemedy(Player/P)
	var/mob/WorkShops/RemasterClinic/S = remaster_care_target
	var/list/N = RemasterNeeds()
	if(!N) return RemasterCareDone("Feeling better")
	if(!istype(S) || S.z != z || S.vars[N[1]] < 1) return RemasterCareDone("The Doctor's stall has no [RemasterRemedyName(N[1])]")
	if(get_dist(src, S) <= 2)
		if(destination == remaster_care_dest) destination = null
		var/obj/Items/RemasterRemedy/R = S.TakeOut(N[1], src)
		if(R && RemasterApplyRemedy(N[1], src))
			weight -= R.weight
			del R
		return RemasterCareDone("Took the [RemasterRemedyName(N[1])] at the Doctor's stall")
	var/turf/T = RemasterTileNear(S, src)
	if(T && destination != T)
		destination = T
		remaster_care_dest = T

// --- HUD --------------------------------------------------------------------------------------
Player/proc/RemasterClinicBoxData(mob/Monsters/M)
	var/mob/WorkShops/RemasterClinic/S = RemasterClinicBeside(M)
	if(!S) return null
	var/own = S.Owner == src
	var/list/herbs = list()
	for(var/h in rm_herbs) herbs += list(list("id"=h, "name"=rm_herbs[h][1], "n"=S.vars[h], "remedy"=rm_herbs[h][4], "rid"=rm_herbs[h][3], "rn"=S.vars[rm_herbs[h][3]], "treats"=rm_herbs[h][5]))
	var/carried = 0
	for(var/obj/Items/I in M) if(I.suffix == "(Carrying)" && (istype(I, /obj/Items/RemasterHerb) || istype(I, /obj/Items/RemasterRemedy))) carried++
	var/list/N = M.RemasterNeeds()
	var/doctor = 0
	for(var/mob/Monsters/D in UnitList) if(D.Owner == src && D.remaster_job == "doctor" && D.HP > 0) doctor = 1
	return list("own"=own, "owner"=(S.Owner ? "[S.Owner]" : null), "n"=S.Total(), "max"=RM_CLINIC_MAX, "herbs"=herbs, "carried"=carried,
		"need"=(N ? N[1] : null), "needWhy"=(N ? N[3] : null), "skill"=round(M.PotionSkill), "doctor"=doctor)

// value: "unitref|action|arg"; the stall is the one beside the unit.
Player/proc/RemasterClinicCommand(value)
	var/list/p = splittext("[value]", "|")
	if(p.len < 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return 0
	var/mob/WorkShops/RemasterClinic/S = RemasterClinicBeside(M)
	if(!S || S.Owner != src)
		RemasterNotice("[M.RemasterBareName()] must stand beside your Doctor's stall.")
		return 0
	var/arg = p.len >= 3 ? p[3] : ""
	switch(p[2])
		if("put")
			var/n = 0
			for(var/obj/Items/I in M) if(I.suffix == "(Carrying)" && (istype(I, /obj/Items/RemasterHerb) || istype(I, /obj/Items/RemasterRemedy)) && S.PutIn(I)) n++
			RemasterNotice(n ? "[M.RemasterBareName()] put [n] thing\s in the Doctor's stall." : "Nothing to put in (or the stall is full).")
			return n > 0
		if("make")
			if(!rm_herbs[arg]) return 0
			switch(S.Make(arg, M))
				if(1) RemasterNotice("[M.RemasterBareName()] made a [rm_herbs[arg][4]].")
				if(-1) RemasterNotice("[M.RemasterBareName()] spoiled the [lowertext(rm_herbs[arg][1])]. Potion skill helps.")
				else RemasterNotice("No [lowertext(rm_herbs[arg][1])] in the stall.")
			return 1
		if("take")
			var/obj/Items/R = S.TakeOut(arg, M)
			RemasterNotice(R ? "[M.RemasterBareName()] took a [R.name]." : "None to take, or too heavy.")
			return !!R
		if("use")
			if(S.vars[arg] < 1) return 0
			var/obj/Items/R = S.TakeOut(arg, M)
			if(R && M.RemasterApplyRemedy(arg, M))
				M.weight -= R.weight
				del R
			return 1
	return 0

// What the 3D view draws: how stocked, and the jars and bundles on it.
proc/Remaster3DClinic(mob/WorkShops/RemasterClinic/S)
	return list("n"=S.Total(), "max"=RM_CLINIC_MAX, "herbs"=S.athelas + S.feverfew + S.thistle, "poultice"=S.poultice, "tonic"=S.tonic, "purge"=S.purge,
		"col"=(ismob(S.Owner) ? RemasterClaimColour(S.Owner:key) : "#c8a060"))

proc/Remaster3DHerb(obj/Items/Plants/RemasterHerbPlant/H)
	return list("type"=H.herb, "stage"=5, "ripe"=H.Content >= 1, "n"=H.Content)
