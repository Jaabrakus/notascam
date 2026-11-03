obj/Items/Equipment/Armour/Crown
	// its values: art/items/catalogue.json row equipment.armour.crown (export_items.py writes ItemData.dm)
	Bone
		name="Bone Crown"
		icon = 'RoyalItems.dmi'
		icon_state = "BoneCrown"
		weight=5
		Defence=6
		WeaponDamageMin=6
		WeaponDamageMax=6
	Gold
		name="Gold Crown"
		icon = 'GoldItems.dmi'
		icon_state = "Crown"
		weight=10
		Defence=16
proc/GenderToLeader(GENDER)
	if(GENDER=="Female") return("Queen")
	else return("King")
proc/GenderToTheir(GENDER) switch(GENDER)
	if("Female") return("her")
	if("Male") return("his")
	else return("its")
mob/verb/DeclareLeader()
	if(istype(src, /Player)) return src:RemasterDeclareSelected(1)
	for(var/mob/Monsters/M in Selected)
		if(M.IsRoyal)
			if(M.RemoveLeader()) return
		else if(M.AddLeader()) return
mob/proc
	AddLeader(obj/Items/Equipment/CROWN, datum/remaster_action_context/CONTEXT)
		if(!IsRoyal)
			var/Player/P = istype(usr, /Player) ? usr : null
			var/had_player = !!P
			if(P && !CONTEXT) CONTEXT = P.RemasterSelectedActionCapture(/mob/verb/DeclareLeader,1)
			if(had_player && (!P || !P.RemasterSelectedActionCurrent(CONTEXT) || CONTEXT.units[remaster_ui_id] != src)) return 0
			var/list/crowns = RemasterCrownSnapshot()
			var/crown_ref = CROWN ? RemasterUIRef(CROWN) : null
			var/equipment = UsesEquipment
			var/wearing = WearingCrown
			if(CROWN && (CROWN.loc != src || CROWN.ItemType != "Crown" || CROWN.suffix != "(Carrying)")) return 0
			// Remastered (Rulership.dm): the seat needs the settlement stage's regalia, and a claimed seat waits
			var/REGALIA = RmCrowningRegalia(CROWN)
			if(!REGALIA) return 0
			var/choice = RemasterLeaderChoice(Owner,"Do you wish to make [src] the ruler of your realm?","Set Leader")
			// Validate before even returning an already-royal result to EquipItem.
			// Otherwise a second crown/ownership change can slip through the yield.
			if(had_player && (!P || !P.RemasterSelectedActionCurrent(CONTEXT) || CONTEXT.units[remaster_ui_id] != src)) return 0
			if(!RemasterCrownsCurrent(crowns) || UsesEquipment != equipment || WearingCrown != wearing) return 0
			if(crown_ref && (!CROWN || CROWN.remaster_ui_id != crown_ref || CROWN.loc != src)) return 0
			if(choice=="Yes" && !IsRoyal)
				var/mob/Monsters
					KING
					QUEEN
				for(var/mob/Monsters/M in usr.UnitList) if(M.IsRoyal) switch(GenderToLeader(M.Gender))
					if("King") KING=M
					if("Queen") QUEEN=M
				if(Gender=="Female")
					if("Queen" in usr.CoolDowns)
						usr<<"You cannot crown a new ruler so soon after the loss of your last queen. You must wait one full hour."
						return
					if(QUEEN)
						usr<<"You already have [QUEEN] as your ruler. Your realm may have one ruler of each gender at a time."
						return
				else
					if("King" in usr.CoolDowns)
						usr<<"You cannot crown a new ruler so soon after the loss of your last king. You must wait one full hour."
						return
					if(KING)
						usr<<"You already have [KING] as your ruler. Your realm may have one ruler of each gender at a time."
						return
				// Remastered (Rulership.dm): the law of succession (the realm's first crowning) and the title, from the
				// stage's list; the questions yield, so everything is checked again after them
				var/list/ASK = RmCrowningAsks()
				if(!ASK || IsRoyal || HP <= 0) return 0
				if(had_player && (!P || !P.RemasterSelectedActionCurrent(CONTEXT) || CONTEXT.units[remaster_ui_id] != src)) return 0
				if(!RemasterCrownsCurrent(crowns) || UsesEquipment != equipment || WearingCrown != wearing) return 0
				if(crown_ref && (!CROWN || CROWN.remaster_ui_id != crown_ref || CROWN.loc != src)) return 0
				if(istype(REGALIA, /obj/Items/Equipment/Armour/Crown)) Owner<<"[src] puts on the [RmName(REGALIA)] and becomes [ASK["title"]] of your realm!"
				else Owner<<"[src] has become [ASK["title"]] of your realm!"
				RmWearRegalia(REGALIA)
				ChangeRoyal()
				RmCrowned(REGALIA, ASK)
		if(IsRoyal) return(1)
	RemoveLeader(datum/remaster_action_context/CONTEXT)
		if(!IsRoyal) return 0
		var/Player/P = istype(usr, /Player) ? usr : null
		var/had_player = !!P
		if(P && !CONTEXT) CONTEXT = P.RemasterSelectedActionCapture(/mob/verb/DeclareLeader,1)
		if(had_player && (!P || !P.RemasterSelectedActionCurrent(CONTEXT) || CONTEXT.units[remaster_ui_id] != src)) return 0
		var/list/crowns = RemasterCrownSnapshot()
		var/choice = RemasterLeaderChoice(Owner,"Do you wish [src] to step down as ruler of your realm? You will have to wait a full hour before crowning a new ruler in their place.","Remove Leader")
		if(had_player && (!P || !P.RemasterSelectedActionCurrent(CONTEXT) || CONTEXT.units[remaster_ui_id] != src)) return 0
		if(!RemasterCrownsCurrent(crowns)) return 0
		if(choice=="Yes" && IsRoyal)
			var/TITLE = RmTitleOf()
			for(var/obj/Items/Equipment/Armour/Crown/CROWN in src) UnEquipItem(CROWN,MANUAL=1)
			ChangeRoyal()
			if(TITLE && findtextEx(name, "[TITLE] ") == 1) name=copytext(name,length(TITLE)+2)
			else if(copytext(name,1,6)=="King ") name=copytext(name,6)
			else if(copytext(name,1,7)=="Queen ") name=copytext(name,7)
			Owner<<"[src] has stepped down as [TITLE] of your realm."
			usr.CoolDown("[GenderToLeader(Gender)]",36000)
			RmSteppedDown()   // Remastered: the seat may now be claimed (Rulership.dm)
			return(1)
mob/var/IsRoyal

mob/proc/ChangeRoyal()
	var/INFLUENCE
	if(IsRoyal)
		IsRoyal=null
		INFLUENCE=(-1)
	else
		IsRoyal=1
		INFLUENCE=(1)

	Strength+=10*INFLUENCE
	Agility+=10*INFLUENCE

	SneakingSkill+=40*INFLUENCE
	// Remastered: more health instead of +25 weapon skills, which never go above Attack (CombatSkills.dm)
	if(istype(src, /mob/Monsters))
		src:RemasterCrownHealth(INFLUENCE)
		return(1)
	HP+=100*INFLUENCE
	MAXHP+=100*INFLUENCE
	SpearSkill+=25*INFLUENCE
	SwordSkill+=25*INFLUENCE
	MaceSkill+=25*INFLUENCE
	AxeSkill+=25*INFLUENCE
	DaggerSkill+=25*INFLUENCE
	UnArmedSkill+=25*INFLUENCE
	BowSkill+=25*INFLUENCE
	return(1)
