var/list/BodyParts=list("LeftArm","RightArm","LeftLeg","RightLeg","LeftEye","RightEye","LeftLung","RightLung","Spleen","Teeth","Head","LeftEar","RightEar","Guts","Stomach","LeftKidney","RightKidney","Liver","Brain","Heart","Throat","Nose","Wings")
mob/proc/FullHeal(GROW)
	if(GROW)
		if(Race!="Devourer")
			HasLeftLeg = 1
			HasRightLeg = 1
		HasLeftArm = 1
		HasRightArm = 1
	CanUseRightArm = 1
	CanUseLeftArm = 1
	CanWalk = 1
	Stunned = 0
	Fainted = 0
	CanSee = 1
	BleedType = null
	for(var/Part in BodyParts)
		if(vars["Has[Part]"])
			vars["[Part]HP"] = OrganMaxHP
			vars["[Part]"] = "Good"
			vars["Has[Part]"] = 1
		else
			vars["[Part]HP"] = 0
			vars["[Part]"] = ""
			vars["Has[Part]"] = 0

	HP=MAXHP
	BloodContent=MaxBloodContent
	LimbLoss()
mob/proc/Bleeding() if(StopDouble("Bleeding")) RmClockStart(src, "Bleeding", 50)   // the shared clock runs its tick (Remastered/UnitClock.dm)
mob/proc/BleedingTick()
	RmClockBook(src, "Bleeding", 50)   // its next run, as the loop's sleep(50)
	if(src.InHole == 0)
		if(src.HasLeftLung == 0)
			if(src.HasRightLung == 0)
				src.GoingToDie = 1
				src.DeathType = "Lung Failure"
				src.Owner << "<b><font color=red>[src]'s lungs have failed!!"
				src.Death()
		if(src.BleedType)
			var/bleed
			bleed = rand(1,4)
			switch(bleed)
				if(1)
					var/obj/Bloods/Blood1/B1 = new
					B1.loc = src.loc
					B1.BloodAcidity = src.BloodAcidity
				if(2)
					var/obj/Bloods/Blood2/B2 = new
					B2.loc = src.loc
					B2.BloodAcidity = src.BloodAcidity
					if(src.WebContent>0)
						src.WebContent-=1
						var/obj/Items/Silks/SpiderSilk/S = new
						S.loc = src.loc
				if(3)
					var/obj/Bloods/Blood3/B3 = new
					B3.loc = src.loc
					B3.BloodAcidity = src.BloodAcidity
				if(4)
					var/obj/Bloods/Blood4/B4 = new
					B4.loc = src.loc
					B4.BloodAcidity = src.BloodAcidity
					if(src.WebContent>0)
						src.WebContent-=1
						var/obj/Items/Silks/SpiderSilk/S = new
						S.loc = src.loc
			if(prob(20) && RemasterBleedStops()) // Remastered: a stump bleeds until treated; its blood comes back slowly (Stumps.dm)
				src.BleedType = null
				src.BloodContent = src.MaxBloodContent
				src.Owner << "<b><font color=red>[src] has stopped bleeding!!"
		switch(BleedType)
			if("Badly")
				var/DieChance
				DieChance = prob(8)
				if(DieChance)
					if(RmBleedOut(src)) return // Remastered: down and dying, a minute to be saved (BleedOut.dm)
					src.DeathType = "Bleeding To Death"
					src.GoingToDie = 1
					view() << "<b><font color=red>[src] has bled to death!!"
					src.Death()
					RmClockStop(src, "Bleeding")   // bled to death: the bleeding stops, as its loop did
					return
			if("Very Badly")
				var/DieChance
				DieChance = prob(20)
				if(DieChance)
					if(RmBleedOut(src)) return // Remastered: down and dying, a minute to be saved (BleedOut.dm)
					src.DeathType = "Bleeding To Death"
					src.GoingToDie = 1
					view() << "<b><font color=red>[src] has bled to death!!"
					src.Death()
					RmClockStop(src, "Bleeding")   // bled to death: the bleeding stops, as its loop did
					return
			if("Extremly")
				var/DieChance
				DieChance = prob(40)
				if(DieChance)
					if(RmBleedOut(src)) return // Remastered: down and dying, a minute to be saved (BleedOut.dm)
					src.DeathType = "Bleeding To Death"
					src.GoingToDie = 1
					view() << "<b><font color=red>[src] has bled to death!!"
					src.Death()
					RmClockStop(src, "Bleeding")   // bled to death: the bleeding stops, as its loop did
					return
		src.SaidBleed = 0
mob/proc/Heal() if(StopDouble("Heal")) RmClockStart(src, "Heal", 400)   // the shared clock runs its tick (Remastered/UnitClock.dm)
mob/proc/HealTick()
	RmClockBook(src, "Heal", 400)   // its next run, as the loop's sleep(400)
	if(src.HP < src.MAXHP && rm_auto_heal) // Remastered: no automatic healing (Healing.dm)
		src.HP += 10
		if(src.HP >= src.MAXHP) src.HP = src.MAXHP
	if(src.BrainHP < 100) src.BrainHP += 0.05
	if(src.LeftLungHP < 100) src.LeftLungHP += 0.05
	if(src.RightLungHP < 100) src.RightLungHP += 0.05
	if(prob(50))
		if(src.Stunned == 1)
			if(suffix == null)
				Stunned = 0
				view() << "[src] is no longer stunned!"
		if(Fainted == 1)
			Fainted = 0
			view() << "[src] wakes up!"
	if(prob(50) && RemasterMends()) // Remastered: battered limbs mend in sleep (Healing.dm)
		if(LeftArmHP <= OrganMaxHP) if(HasLeftArm)
			LeftArmHP = OrganMaxHP
			LeftArm = "Good"
			CanUseLeftArm = 1
		if(RightArmHP <= OrganMaxHP) if(HasRightArm)
			RightArmHP = OrganMaxHP
			RightArm = "Good"
			CanUseRightArm = 1
	if(prob(50) && RemasterMends()) // Remastered: battered limbs mend in sleep (Healing.dm)
		if(LeftLegHP <= OrganMaxHP) if(HasLeftLeg)
			LeftLegHP = OrganMaxHP
			LeftLeg = "Good"
			CanWalk = 1
		if(RightLegHP <= OrganMaxHP) if(HasRightLeg)
			RightLegHP = OrganMaxHP
			RightLeg = "Good"
			CanWalk = 1
	if(RemasterMends()) for(var/Part in BodyParts) // Remastered: organs mend in sleep (Healing.dm)
		var/HEAL=1.8
		if(vars["Has[Part]"]) if(vars["[Part]HP"]<OrganMaxHP)
			switch(Part)
				if("Brain","Heart","Throat") HEAL=1
				if("LeftArm","RightArm","LeftLeg","RightLeg") continue
			vars["[Part]HP"] += HEAL
			if(vars["[Part]HP"]>=OrganMaxHP)
				vars["[Part]"]="Good"
				vars["[Part]HP"]=OrganMaxHP
mob/proc/Regen() if(StopDouble("Regen")) RmClockStart(src, "Regen", 600)   // the shared clock runs its tick (Remastered/UnitClock.dm)
mob/proc/RegenTick()
	RmClockBook(src, "Regen", 600)   // its next run, as the loop's sleep(600)
	if(!HasLeftEye) if(prob(20))
		src.Owner << "[src] grows their left eye back!"
		src.HasLeftEye = 1
		src.LeftEyeHP = 10
		src.CanSee = 1
		src.LeftEye = "Mangled"
		src.LimbLoss()
	if(!HasRightEye) if(prob(20))
		src.Owner << "[src] grows their right eye back!"
		src.HasRightEye = 1
		src.RightEyeHP = 10
		src.CanSee = 1
		src.RightEye = "Mangled"
		src.LimbLoss()
	if(!HasLeftArm) if(prob(20))
		src.CanUseLeftArm = 1
		src.Owner << "[src] grows their left arm back!"
		src.HasLeftArm = 1
		src.LeftArmHP = 10
		src.LeftArm = "Mangled"
		src.LimbLoss()
	if(!HasRightArm) if(prob(20))
		src.CanUseRightArm = 1
		src.Owner << "[src] grows their right arm back!"
		src.HasRightArm = 1
		src.RightArmHP = 10
		src.RightArm = "Mangled"
		src.LimbLoss()
	if(!HasLeftLeg) if(prob(20))
		src.Owner << "[src] grows their left leg back!"
		src.HasLeftLeg = 1
		src.LeftLegHP = 10
		src.LeftLeg = "Mangled"
		src.LimbLoss()
	if(!HasRightLeg) if(prob(20))
		src.Owner << "[src] grows their right leg back!"
		src.HasRightLeg = 1
		src.RightLegHP = 10
		src.RightLeg = "Mangled"
		src.LimbLoss()