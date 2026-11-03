// Half-demon kinds (Remastered). The original half-demon - possessed at the hell portal, its
// eyes reddening, then its body, until it is a Demon (Race.dm RaceChange) - stays as it was.
// Three more are made in play, each with its own story, gift and price, and its own look on
// the race's 64 px body (art/enhance/halfdemon64.py: Races64/<sheet>-<kind>.dmi):
//  Marked       drank Unholy Blood (a Flask of Blood blessed at an Evil Altar). The dark gods'
//               mark: +3 weapon damage, a little health back from every kill. One drinker in four
//               is taken by the blood instead: the heart stops and it rises a Vampire (the
//               original RaceChange; the Alchemy station's Potion of Vampirism is gone).
//  Ashen        drank Hellfire (a flask of embers from an Ashlands ember vent, blessed at an
//               Evil Altar) and lived through the burning. Can't burn, shrugs off heat, its
//               blows may set foes alight; cold bites it twice as hard.
//  Hellblooded  born, not made: the child of a Demon and a half-demon of any kind, or of a
//               Hellblooded parent. The original half-demon's strength, growing with each
//               level, and no fear of heat or cold; the NPC Alliance attacks it on sight.
// Holy Water (a Flask of Water blessed at a Good Altar) washes out Marked and Ashen; hell's
// blood runs too deep to wash out. Every half-demon kind takes the original's extra harm from
// silver and blessed weapons (Combats.dm).
// Evil Altars are not built but made: a Good Altar (Build menu: stone, with a lump of silver
// and a golden nugget in the builder's bag) is desecrated by three sacrifices on it.

var/list/rm_half_demons = list("HalfDemon", "Marked", "Ashen", "Hellblooded")
var/rm_unholy_vampire = 25   // percent of Unholy Blood drinkers who rise as Vampires instead of Marked

mob/Monsters/var
	rm_was_subrace          // what it was before Marked or Ashen, given back when washed out
	tmp/rm_burning = 0      // in hellfire (RmBurn)
	tmp/rm_hellblood_child  // carrying a child of hell's blood (Breeding)

// Who can take a kind: the living races that drink and bleed, not already something else.
proc/RmHalfDemonCan(mob/Monsters/M)
	if(!istype(M) || M.Critter || M.Undead || M.SubRace) return 0
	return !(M.Race in list("Demon", "Dragon", "Spider", "Gargoyle", "Vampire", "Zombie", "Skeleton", "Devourer", "Angel of Death"))

proc/RmBecomeHalfDemon(mob/Monsters/M, kind)
	if(!RmHalfDemonCan(M)) return 0
	M.rm_was_subrace = M.SubRace
	M.SubRace = kind
	switch(kind)
		if("Marked")
			M.WeaponDamageMin += 3
			M.WeaponDamageMax += 3
		if("Hellblooded")   // as the original half-demon (Race.dm), grown further each level (Leveling.dm)
			M.ImmuneToTemperature = 1
			M.Defence += M.Level / 5
			M.Strength += M.Level / 2
			M.Agility += M.Level / 2
			M.weightmax += M.Level * 5
			M.Intelligence += M.Level * 0.01
	M.RebuildOverlays()
	return 1

// The kind shown before a unit's race (HUD.dm): "Marked Human", "Half-demon Orc".
proc/RmKindLabel(mob/Monsters/M)
	if(!istype(M)) return null
	if(M.SubRace == "HalfDemon") return "Half-demon"
	if(M.SubRace in list("Marked", "Ashen", "Hellblooded")) return M.SubRace

// Holy Water: Marked and Ashen are washed out; the others can't be.
proc/RmWashOut(mob/Monsters/M)
	if(M.SubRace == "Marked")
		M.WeaponDamageMin -= 3
		M.WeaponDamageMax -= 3
	else if(M.SubRace != "Ashen") return 0
	M.SubRace = M.rm_was_subrace
	M.rm_was_subrace = null
	M.RebuildOverlays()
	return 1

// The 3D body of a half-demon (View3D.dm Remaster3DBody64): its kind's sheet of the race's; the
// possessed, the stage it has reached (red eyes, then red all over; at the last it is a Demon).
mob/var/rm_possessed   // 1-3: how far the hell portal's possession has gone (Race.dm RaceChange)
var/list/rm_half_demon_sheets = list()
proc/RmHalfDemonSheet(mob/Monsters/M, name)
	if(!istype(M)) return null
	var/suffix = (M.SubRace in list("Marked", "Ashen", "Hellblooded")) ? M.SubRace : null
	if(M.SubRace == "HalfDemon" && (M.rm_possessed in list(1, 2))) suffix = "Possessed[M.rm_possessed]"
	if(!suffix) return null
	var/path = "Icons/Remastered/Races64/[name]-[suffix].dmi"
	if(isnull(rm_half_demon_sheets[path])) rm_half_demon_sheets[path] = fexists(path)
	return rm_half_demon_sheets[path] ? path : null

// --- Burning --------------------------------------------------------------------------
// Hellfire (and an Ashen's blows): the unit burns for `pulses` pulses of 5 s, losing `part`
// of its health each; then, if it lives and `then_kind` is set, it rises as that kind.
proc/RmBurn(mob/Monsters/M, pulses, part, then_kind)
	if(!istype(M) || M.SubRace == "Ashen" || M.rm_burning || M.HP <= 0) return
	M.rm_burning = 1
	var/obj/RemasterFlame/F = new(M.loc)
	for(var/i = 1, i <= pulses && M && M.HP > 0, i++)
		M.HP -= max(1, round(M.MAXHP * part))
		if(M.HP <= 0)
			M.GoingToDie = 1
			M.Killer = "Hellfire"
			M.DeathType = "Burned To Death"
			M.Death()
			break
		for(var/k = 1, k <= 10 && M, k++)   // the flame keeps with it
			if(F && isturf(M.loc)) F.loc = M.loc
			sleep(5)
	if(F) del F
	if(!M) return
	M.rm_burning = 0
	if(M.HP > 0 && then_kind && RmBecomeHalfDemon(M, then_kind))
		view(M) << "<b><font color=#e0602a>[M] rises from the flames grey as cinders, the fire still crawling under their skin. [M] is Ashen!</font></b>"

// --- Flasks (Turfs.dm MetalFlask/LeatherFlask call these from their menus) ---------------
proc/RmFlaskOptions(obj/Items/F, mob/Monsters/M)
	. = list()
	if(!istype(M) || M.Wagon) return
	if(!F:HasWater && (locate(/obj/RemasterEmberVent) in view(1, M))) . += "Fill [F] with embers"
	if(F:HasWater == "Unholy" || F:HasWater == "Holy") . += "Drink"

proc/RmFlaskChoice(obj/Items/F, mob/Monsters/M, choice)
	if(!istype(M)) return 0
	if(choice == "Fill [F] with embers")
		F:HasWater = "Embers"
		M.Owner << "[M] scoops glowing embers from the vent into [F]."
		return 1
	if(choice != "Drink" || !(F:HasWater in list("Unholy", "Holy", "Hellfire", "Embers"))) return 0
	var/what = F:HasWater
	F:HasWater = null
	switch(what)
		if("Unholy")
			if(RmHalfDemonCan(M) && prob(rm_unholy_vampire))
				view(M) << "<b><font color=#8e1b2a>[M] drinks the unholy blood and is struck with extreme chest pain as its heart fails...... after a few moments it rises up and views the world with the new eyes of an undead monster. [M] is a Vampire!</font></b>"
				M.RaceChange("Vampire")
			else if(RmBecomeHalfDemon(M, "Marked"))
				view(M) << "<b><font color=#c0392b>[M] drinks the unholy blood. The dark gods' mark burns into them: their eyes smoulder and small horns push through. [M] is Marked!</font></b>"
			else
				M.Owner << "[M] retches up the unholy blood: it won't take in them."
		if("Holy")
			if(RmWashOut(M))
				view(M) << "<b><font color=#f1e3a0>[M] drinks the holy water. The hellish taint burns away: [M] is themselves again.</font></b>"
			else if(M.SubRace in rm_half_demons)
				M.Owner << "The holy water burns in [M]'s throat, but hell's blood runs too deep to wash out."
			else
				M.Coldness = 0
				M.Owner << "[M] drinks the holy water and feels at peace."
		if("Hellfire")
			view(M) << "<b><font color=#e0602a>[M] drinks the hellfire and bursts into flame!</font></b>"
			spawn(0) RmBurn(M, 6, 0.09, RmHalfDemonCan(M) ? "Ashen" : null)
		if("Embers")
			view(M) << "[M] tries to swallow burning embers!"
			spawn(0) RmBurn(M, 2, 0.06)
	return 1

// --- Altars (CraftingStations.dm GoodAltar/EvilAltar call these from their menus) --------
mob/WorkShops/CampFires/GoodAltar/var
	rm_desecrated = 0   // sacrifices made on it
	rm_offered = 0      // their worth: the Evil Altar's first worship points

proc/RmGoodAltarOptions(mob/WorkShops/CampFires/GoodAltar/A, mob/Monsters/M)
	return list("Sacrifice")

proc/RmGoodAltarChoice(mob/WorkShops/CampFires/GoodAltar/A, mob/Monsters/M, Player/P, choice)
	if(choice != "Sacrifice") return 0
	if(!(M in view(2, A)) || !M.RemasterManualHandoff(P)) return 1
	view(A) << "<b><font color=#8e2b2b>[M] lies down upon [A] and gives up their life to it. The holy light gutters.</font></b>"
	A.rm_offered += M.Level * 2 + M.RmStr() + M.RmAgi() / 2   // what the Evil Altar would take (CraftingStations.dm)
	A.rm_desecrated++
	M.DeathType = "Sacrificed To Death"
	M.GoingToDie = 1
	M.Death()
	if(A.rm_desecrated >= 3) RmAltarTurnsEvil(A)
	else A.color = A.rm_desecrated == 1 ? "#c4aaaa" : "#8a6464"   // darker with each (3D: View3D.dm tint)
	return 1

proc/RmAltarTurnsEvil(mob/WorkShops/CampFires/GoodAltar/A)
	var/mob/WorkShops/CampFires/EvilAltar/E = new(A.loc)
	E.Content2 = A.rm_offered
	E.Owner = A.Owner
	view(E) << "<b><font color=#8e2b2b>[A] cracks and blackens. It is an Evil Altar now.</font></b>"
	del A

proc/RmEvilAltarOptions(mob/WorkShops/CampFires/EvilAltar/A, mob/Monsters/M)
	. = list()
	if(RmEmberFlask(M)) . += "Bless Flask of Embers"

proc/RmEmberFlask(mob/Monsters/M)
	for(var/obj/Items/Shafts/F in M)
		if((istype(F, /obj/Items/Shafts/MetalFlask) || istype(F, /obj/Items/Shafts/LeatherFlask)) && F:HasWater == "Embers") return F

proc/RmEvilAltarChoice(mob/WorkShops/CampFires/EvilAltar/A, mob/Monsters/M, Player/P, choice)
	if(choice != "Bless Flask of Embers") return 0
	var/obj/Items/F = RmEmberFlask(M)
	if(!F || !M.RemasterManualHandoff(P)) return 1
	F:HasWater = "Hellfire"
	view(M) << "[M] holds the embers over [A]. They flare black and red: Hellfire."
	return 1

// --- Building a Good Altar (Blueprints.dm "Workshop:altar") -----------------------------
// Stone (the site's material), with a lump of silver and a golden nugget in the builder's bag.
proc/RmAltarNeed(mob/Monsters/M)
	var/list/missing = list()
	if(!(locate(/obj/Items/ores/Silver) in M)) missing += "a lump of silver"
	if(!(locate(/obj/Items/ores/Gold) in M)) missing += "a golden nugget"
	if(length(missing)) return "A good altar also needs [jointext(missing, " and ")] in [M.name]'s bag"

proc/RmAltarBuild(mob/Monsters/M, turf/T)
	if(RmAltarNeed(M)) return 0
	for(var/path in list(/obj/Items/ores/Silver, /obj/Items/ores/Gold))
		var/obj/Items/I = locate(path) in M
		M.weight -= I.weight
		del I
	new /mob/WorkShops/CampFires/GoodAltar(T)
	return 1

// mob/Monsters/Death: this file's part is step RmChainDeath_HalfDemons in Code/Remastered/Chains/Death.dm

// mob/RemasterStrike: this file's part is step RmChainStrike_HalfDemons in Code/Remastered/Chains/Strike.dm

// The Ashen shrug off heat and feel cold twice over (this proc works on usr, as the original).
turf/ApplyTemperature(Temperature, steps = 1)   // steps: Turfs.dm, the ground's run for several steps
	if(ismob(usr) && usr:SubRace == "Ashen")
		if(Temperature > 0) return
		Temperature *= 2
	return ..(Temperature, steps)

// --- Hellblooded births ---------------------------------------------------------------
// The parent whose race a child of hell's blood takes, or null: a Demon's child by a
// half-demon is of the half-demon's race; a Hellblooded parent's of its mother's (unless she
// is the Demon).
proc/RmHellbloodParent(mob/Monsters/father, mob/Monsters/mother)
	if(!istype(father) || !istype(mother)) return null
	if(father.Race == "Demon" && (mother.SubRace in rm_half_demons)) return mother
	if(mother.Race == "Demon" && (father.SubRace in rm_half_demons)) return father
	if(father.SubRace == "Hellblooded" || mother.SubRace == "Hellblooded") return mother.Race == "Demon" ? father : mother

mob/Monsters/Breeding(mob/breederMale, mob/breederFemale, TIME = 3000)
	var/was = CHILDMALE || CHILDFEMALE
	. = ..()
	if(was || !CHILDMALE) return   // already carrying: nothing new began
	var/mob/Monsters/H = RmHellbloodParent(breederMale, breederFemale)
	if(!H) return
	rm_hellblood_child = 1
	if(!Egg) CHILDTYPE = text2path("/mob/Monsters/[H.Race]")

mob/Monsters/RemasterRecordBirth(mob/Monsters/F, mob/Monsters/M, mob/Monsters/carrier)
	. = ..()
	if(istype(carrier) && carrier.rm_hellblood_child && RmBecomeHalfDemon(src, "Hellblooded"))
		view(src) << "<b><font color=#c0392b>[src] is born red-skinned, horned and tailed: Hellblooded.</font></b>"

mob/Monsters/GiveBirth()
	. = ..()
	if(src) rm_hellblood_child = 0
