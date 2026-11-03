// Carried items have two original input contracts. Equipment/food use
// DblClick; potions, signs and tombstones have their choices in client/Click.
// Keep that distinction instead of turning every inventory tap into Drop.

// A carried-item dialog can remain open while its carrier changes hands or the
// item is moved/deleted. Keep original menu/effect code, but validate its exact
// participants after the reply. Natural movement/hunger changes are permitted.
datum/remaster_carried_context
	var/mob/controller
	var/mob/carrier
	var/obj/Items/item
	var/controller_token
	var/carrier_token
	var/item_token
	var/require_selected=0
	var/list/profile
	var/list/item_state
	var/list/contents_state

proc/RemasterCarriedCurrent(datum/remaster_carried_context/C)
	if(!C || !C.controller || !C.carrier || !C.item) return 0
	var/mob/P=C.controller
	var/mob/M=C.carrier
	var/obj/Items/I=C.item
	if(P.remaster_ui_id!=C.controller_token || M.remaster_ui_id!=C.carrier_token || I.remaster_ui_id!=C.item_token) return 0
	if(M.Owner!=P || I.loc!=M || M.GoingToDie || (istype(M,/mob/Monsters)&&M.HP<=0)) return 0
	if(C.require_selected)
		if(!istype(P,/Player) || !istype(M,/mob/Monsters)) return 0
		var/Player/PLAYER=P
		if(!PLAYER.RemasterInventoryActor(M,I)) return 0
	for(var/key in C.profile) if(M.vars[key]!=C.profile[key]) return 0
	for(var/key in C.item_state) if(I.vars[key]!=C.item_state[key]) return 0
	if(C.contents_state)
		if(length(I.contents)!=length(C.contents_state)) return 0
		for(var/token in C.contents_state)
			var/atom/movable/A=C.contents_state[token]
			if(!A || A.remaster_ui_id!=token || A.loc!=I) return 0
	return 1

proc/RemasterCarriedCapture(obj/Items/I,mob/M,mob/P,require_selected=0)
	if(!I || !M || !P || M.Owner!=P || I.loc!=M) return null
	var/datum/remaster_carried_context/C=new
	C.controller=P
	C.carrier=M
	C.item=I
	C.controller_token=RemasterUIRef(P)
	C.carrier_token=RemasterUIRef(M)
	C.item_token=RemasterUIRef(I)
	C.require_selected=require_selected
	C.profile=list()
	for(var/key in list("Race","SubRace","IsMist","UsesEquipment","HasRightArm","CanUseRightArm","HasLeftArm","CanUseLeftArm","Carn","IsRoyal","Gender")) C.profile[key]=M.vars[key]
	C.item_state=list()
	for(var/key in list("Owner","Race","name","icon","icon_state","ItemType","suffix","weight","FoodPower","Content","Silver","WeaponDamageMin","WeaponDamageMax","Defence","NoDropOnDeath")) C.item_state[key]=I.vars[key]
	if(I.ItemType=="Quiver")
		C.contents_state=list()
		for(var/atom/movable/A in I) C.contents_state[RemasterUIRef(A)]=A
	return RemasterCarriedCurrent(C) ? C : null

obj/Items/proc/RemasterCarriedChoice(mob/controller,list/menu)
	// in the HUD's question card once it is up, as a potion's, a sign's and a workshop's choices are (AskCard.dm): a
	// weapon's, armour's or food's choices still came up in the native "Choose" window (polish 10-26)
	if(istype(controller,/Player) && controller.client && controller:remaster_hud_ready) return RemasterChoose(controller,"What would you like to do with the [src]?","Choose",menu)
	return input(controller,"What would you like to do with the [src]?","Choose",null) in menu

obj/Items/proc/RemasterUseCarried(mob/carrier,mob/controller,require_selected=0)
	return 0

proc/RemasterSpecialInventoryItem(obj/Items/I)
	return I && (I.IsPotion == 1 || I.icon_state == "sign" || I.TS == 1)

// "Equip all armour" and "Unequip all armour" (the unit controls; the original's HUD buttons) went through every carried
// piece, weapons and tools too: a soldier with an axe and a pickaxe in its bag ended up holding the pickaxe, and
// "Unequip all armour" put its sword away (polish 10-26). Armour only, as they say; the rest is the original's.
obj/Hud/EquipArmor/DblClick() for(var/mob/Monsters/c in usr.Selected) for(var/obj/Items/Equipment/E in c) if(E.EquipmentType() == "Armour") c.EquipItem(E)
obj/Hud/RemoveArmor/DblClick() for(var/mob/Monsters/c in usr.Selected) for(var/obj/Items/Equipment/E in c) if(E.EquipmentType() == "Armour") c.UnEquipItem(E)

Player/proc/RemasterInventoryActor(mob/Monsters/M, obj/Items/I)
	return M && I && M.Owner == src && (M in UnitList) && (M in Selected) && M.HP > 0 && !M.GoingToDie && I.loc == M

Player/proc/RemasterInventoryUse(obj/Items/I)
	if(!I || !istype(I.loc, /mob/Monsters)) return 0
	var/mob/Monsters/M = I.loc
	if(!RemasterInventoryActor(M, I)) return 0
	usr = src
	if(RemasterSpecialInventoryItem(I)) return RemasterInventoryOptions(M, I)
	if(istype(I,/obj/Items/Food) || istype(I,/obj/Items/Equipment)) return I.RemasterUseCarried(M,src,1)
	return RemasterPlainItemMenu(M, I)

// Every other carried thing (a dragon egg, logs, stone, ore, gems, bones, skins, seeds...) had no choices, so it could not
// even be put down (the owner, 10-28: "updated inventory actions for drop drop all or use"): Use on..., its own original
// choices where it has them, Drop, Drop all of its kind, Inspect.
Player/proc/RemasterPlainItemMenu(mob/Monsters/M, obj/Items/I)
	var/datum/remaster_carried_context/C = RemasterCarriedCapture(I, M, src, 1)
	if(!C) return 0
	var/list/menu = list()
	if(istype(I, /obj/Items/Bones) || istype(I, /obj/Items/Traps) || istype(I, /obj/Items/Furniture)) menu += "Its own choices"   // the original's DblClick menu
	menu += "Drop"
	menu += "Inspect"
	I.RmMenuExtras(M, src, menu)
	menu += "Cancel"
	var/result = RemasterInventoryChoice("What would you like to do with the [I.name]?", menu)
	if(!RemasterCarriedCurrent(C) || !(result in menu) || result == "Cancel") return 0
	if(I.RmMenuExtraDo(M, src, result)) return 1
	usr = src
	if(result == "Its own choices") I.DblClick()
	else if(result == "Drop") M.DropItem(I)
	else if(result == "Inspect")
		src << "\icon[I] <b>[I.name]</b>"
		if(I.desc) src << I.desc
		if(I.weight) src << "Weighs [I.weight] units."
	return 1

// The kind an item stacks with (the bag shows one of each with a count, HUD.dm; the owner, 10-28: "each item is a
// catergory ... lets clicks and server ticks"): the same thing in the same state, never something worn.
obj/Items/proc/RmKindKey()
	return suffix == "(Equipped)" ? null : "[type]|[name]|[suffix]"

mob/Monsters/proc/RmSameKind(obj/Items/I)
	var/k = I.RmKindKey()
	if(!k) return list(I)
	. = list()
	for(var/obj/Items/X in src) if(X.RmKindKey() == k) . += X

// Every bag menu's shared choices: Use on... (the item held, what it is for ringed: UseOn.dm), Drop all of its kind.
obj/Items/proc/RmMenuExtras(mob/Monsters/M, Player/P, list/menu)
	if(istype(P) && P.RemasterUseOnTargets(M, src)) menu.Insert(1, "Use on...")
	var/n = length(M.RmSameKind(src))
	if(n < 2) return
	var/i = menu.Find("Drop")
	if(i) menu.Insert(i + 1, "Drop all ([n])")
	else menu += "Drop all ([n])"

obj/Items/proc/RmMenuExtraDo(mob/Monsters/M, Player/P, choice)
	if(choice == "Use on...")
		if(istype(P)) P.RemasterUseOnCommand("useonpick", RemasterUIRef(src))
		return 1
	if(findtext("[choice]", "Drop all (") == 1)
		for(var/obj/Items/X in M.RmSameKind(src)) if(X.loc == M) M.DropItem(X)
		return 1
	return 0

Player/proc/RemasterInventoryChoice(message, list/options)
	return RemasterChoose(src, message, "Choose", options)   // the HUD's question card (AskCard.dm)

Player/proc/RemasterInventoryText(message)
	return input(src, message) as null|text

Player/proc/RemasterInventorySnapshot(mob/Monsters/M, obj/Items/I)
	var/list/state = list("item"=RemasterUIRef(I), "carrier"=RemasterUIRef(M), "race"=M.Race, "subrace"=M.SubRace, "mist"=M.IsMist)
	var/list/fields = list()
	for(var/field in list("name", "icon_state", "IsPotion", "IsEmpty", "TS", "suffix")) fields[field] = I.vars[field]
	state["fields"] = fields
	return state

Player/proc/RemasterInventoryCurrent(mob/Monsters/M, obj/Items/I, list/state)
	if(!RemasterInventoryActor(M, I) || M.Wagon || !M.CanSee) return 0
	if(RemasterUIItem(state["item"]) != I || RemasterUIUnit(state["carrier"]) != M) return 0
	if(M.Race != state["race"] || M.SubRace != state["subrace"] || M.IsMist != state["mist"]) return 0
	var/list/fields = state["fields"]
	for(var/field in fields) if(I.vars[field] != fields[field]) return 0
	return 1

Player/proc/RemasterInventoryOptions(mob/Monsters/M, obj/Items/I)
	if(!RemasterInventoryActor(M, I) || !RemasterSpecialInventoryItem(I) || M.Wagon || !M.CanSee) return 0
	usr = src
	var/list/state = RemasterInventorySnapshot(M, I)
	var/action = I.IsPotion == 1 ? "Drink" : I.icon_state == "sign" ? "Write" : "Inscribe"
	var/list/menu = action == "Drink" ? list("Drop", "Inspect", action, "Cancel") : list("Drop", action, "Inspect", "Cancel")
	I.RmMenuExtras(M, src, menu)
	var/result = RemasterInventoryChoice("What Action Will You Choose?", menu)
	// Prompts yield. The selected carrier and the item must still be exactly
	// those offered, including cargo ownership and the current bottle/sign state.
	if(!RemasterInventoryCurrent(M, I, state)) return 0
	if(I.RmMenuExtraDo(M, src, result)) return 1
	if(!(result in menu) || result == "Cancel") return 1
	if(result == "Inspect")
		src << I.desc
		return 1
	if(result == "Drop")
		if(I.suffix == "(Carrying)" && M.RemasterManualHandoff(src))
			I.loc = M.loc
			I.suffix = null
			M.weight -= I.weight
			if(action == "Write") I.dir = M.dir
		return 1
	if(result == "Write" || result == "Inscribe")
		var/value = RemasterInventoryText(result == "Write" ? "Write On Sign" : "Inscribe Tomb Stone")
		if(!value || !RemasterInventoryCurrent(M, I, state)) return 0
		if(!M.RemasterManualHandoff(src)) return 0
		I.name = value
		if(result == "Inscribe") I.icon_state = "TombStone2"
		return 1
	if(result == "Drink")
		RemasterDrinkPotion(M, I)
		return 1
	return 0

// The original Click potion effects follow unchanged below. Handoff happens
// only when an eligible drink is actually committed, never for Inspect/Cancel.
// Original src was client: keep its display value in the two legacy messages.
// No-argument view() remains centered on usr (the Player) in this runtime.

Player/proc/RemasterDrinkPotion(mob/Monsters/M, obj/Items/m)
	if(m.IsEmpty)
		RemasterNotice("The bottle is empty.")   // it did nothing, silently (polish 10-27)
		return
	if(M.Race == "Spider" || M.HasStomach != 1 || M.Undead != 0 || M.Infects != 0)
		RemasterNotice("[M.RemasterBareName()] can't drink potions.")
		return
	if(m.suffix == "(Carrying)")
		if(M.Race != "Spider")
			if(M.HasStomach == 1 && M.Undead == 0 && M.Infects == 0)
				if(m.name == "Vampirism Cure")
					if(!M.RemasterManualHandoff(src)) return
					usr << "[M] drinks [m]"
					m.icon_state = "Empty"
					m.IsEmpty = 1
					m.name = "Empty Bottle"
					var/Work = prob(60)
					if(Work == 1)
						if(M.InfectedBy)
							view() << "[M] is no longer sick!"
							M.InfectedBy = null
					else
						view() << "The cure didn't work! Try another!"
					return
				if(m.name == "Potion of Vampirism" && M.Race != "Dragon")
					if(!M.RemasterManualHandoff(src)) return
					usr << "[M] drinks [m]"
					m.icon_state = "Empty"
					m.IsEmpty = 1
					m.name = "Empty Bottle"
					var/Work = prob(60)
					if(M.MagicalAptitude == 1) Work = 1
					if(M.SubRace) Work = 0
					if(Work)
						view() << "[M] is struck with extreme chest pain as its heart fails...... after a few moments it rises up and views the world with the new eyes of an undead monster!"
						M.RaceChange("Vampire")
					else
						view() << "[M] is struck with extreme chest pain as its heart fails...!"
						M.DeathType = "Massive Heart Attack"
						M.GoingToDie = 1
						view() << "<b><font color=red>[M] has died!!"
						M.Death()
					return
				if(m.name == "Potion of Poison Immunity")
					if(!M.RemasterManualHandoff(src)) return
					usr << "[M] drinks [m]"
					m.icon_state = "Empty"
					m.IsEmpty = 1
					m.name = "Empty Bottle"
					var/work = prob(70)
					if(M.ImmunePoison == 0)
						if(work == 1)
							usr << "[M] becomes immune to poison!"
							M.ImmunePoison = 1
						else
							usr << "The potion has no effect, try another."
					else
						usr << "The potion has no effect! [M] is already immune to poison!"
					return
				if(m.name == "Potion of LongLife")
					if(!M.RemasterManualHandoff(src)) return
					usr << "[M] drinks [m]"
					m.icon_state = "Empty"
					m.IsEmpty = 1
					m.name = "Empty Bottle"
					var/A
					A = rand(10,15)
					M.Age -= A
					usr << "[M]'s life is extended for another [A] years!"
					switch(M.Pale)
						if(0)
							M.icon += rgb(25,25,25)
							view()  << "[M]'s soul darkens!"
							M.Pale += 1
							return
						if(1)
							M.icon += rgb(50,50,50)
							view()  << "[M]'s soul darkens!"
							M.Pale += 1
							return
						if(2)
							M.icon += rgb(75,75,75)
							view() << "[M]'s soul darkens!"
							M.Pale += 1
							return
				if(m.name == "Potion of Eternal Life")
					if(!M.RemasterManualHandoff(src)) return
					usr << "[M] drinks [m]"
					m.icon_state = "Empty"
					m.IsEmpty = 1
					m.name = "Empty Bottle"
					M.DieAge += 70000
					usr << "[M]'s life is extended forever!"
					M.icon += rgb(95,95,95)
					view() << "[M]'s soul darkens!"
					return
				if(m.name == "Immunity To Devourer Potion")
					if(M.ImmuneToDevourer == 0)
						if(!M.RemasterManualHandoff(src)) return
						usr << "[M] drinks [m]"
						m.icon_state = "Empty"
						m.IsEmpty = 1
						m.name = "Empty Bottle"
						M.ImmuneToDevourer = 1
						usr << "[M] becomes immune to the dread disease of the devourer!"
						M.icon -= rgb(25,25,25)
						view() << "[M]'s skin darkens a bit from the effects of the potion."
						return
				if(m.name == "Potion of Internal Restoration")
					if(!M.RemasterManualHandoff(src)) return
					usr << "[M] drinks [m]"
					M.HasNose = 1
					M.NoseHP = M.OrganMaxHP
					M.Nose = "Good"
					M.HasLeftEar = 1
					M.LeftEarHP = M.OrganMaxHP
					M.LeftEar = "Good"
					M.HasRightEar = 1
					M.RightEarHP = M.OrganMaxHP
					M.RightEar = "Good"
					M.HasTeeth = 1
					M.TeethHP = M.OrganMaxHP
					M.Teeth = "Good"
					M.HasRightEye = 1
					M.RightEyeHP = M.OrganMaxHP
					M.RightEye = "Good"
					M.HasLeftEye = 1
					M.LeftEyeHP = M.OrganMaxHP
					M.LeftEye = "Good"
					M.RightLungHP = M.OrganMaxHP
					M.RightLung = "Good"
					M.LeftLungHP = M.OrganMaxHP
					M.LeftLung = "Good"
					M.SpleenHP = M.OrganMaxHP
					M.Spleen = "Good"
					M.HeadHP = M.OrganMaxHP
					M.Head = "Good"
					M.GutsHP = M.OrganMaxHP
					M.Guts = "Good"
					M.StomachHP = M.OrganMaxHP
					M.Stomach = "Good"
					M.LeftKidneyHP = M.OrganMaxHP
					M.LeftKidney = "Good"
					M.RightKidneyHP = M.OrganMaxHP
					M.RightKidney = "Good"
					M.LiverHP = M.OrganMaxHP
					M.Liver = "Good"
					M.BrainHP = M.OrganMaxHP
					M.Brain = "Good"
					M.HeartHP = M.OrganMaxHP
					M.Heart = "Good"
					M.ThroatHP = M.OrganMaxHP
					M.Throat = "Good"
					M.WingsHP = M.OrganMaxHP
					M.Wings = "Good"
					M.CanSee = 1
					M.LimbLoss()
					m.icon_state = "Empty"
					m.IsEmpty = 1
					m.name = "Empty Bottle"
				if(m.name == "Potion of Restoration")
					if(!M.RemasterManualHandoff(src)) return
					usr << "[M] drinks [m]"
					M.HasLeftLeg = 1
					M.HasRightLeg = 1
					M.HasLeftArm = 1
					M.HasRightArm = 1
					M.HasTeeth = 1
					M.Teeth = "Good"
					M.TeethHP = M.TeethHPMax
					m.icon_state = "Empty"
					m.IsEmpty = 1
					M.LeftArm = "Good"
					M.RightArm = "Good"
					M.LeftLeg = "Good"
					M.RightLeg = "Good"
					M.RightLegHP = M.OrganMaxHP
					M.LeftLegHP = M.OrganMaxHP
					M.LeftArmHP = M.OrganMaxHP
					M.RightArmHP = M.OrganMaxHP
					M.CanUseRightArm = 1
					M.CanUseLeftArm = 1
					M.CanWalk = 1
					m.name = "Empty Bottle"
					M.LimbLoss()
