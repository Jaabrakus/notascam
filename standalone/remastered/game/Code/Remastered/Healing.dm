// Healing (Remastered; the user, 2026-10-23: "no automatic healing. Health comes back only from eating, sleeping or
// resting in a bed, the Doctor's remedies and potions"; part of the slow, brutal game, Pace.dm).
//  - The original healed every unit all the time: two loops (Health.dm Heal(), Mob Procs.dm Hunger()) added 10 health
//    each every 40 s, mended a battered arm or leg back to Good one time in two and inner organs a little, in a fight
//    or out of it. With rm_auto_heal 0 none of that happens awake (tagged hooks in both loops).
//  - A meal heals RM_HEAL_MEAL (the original EatItem(): carried food, a stockpile's, a food pot's or stall's serving).
//  - Sleep heals: RM_HEAL_BED every 10 s asleep in a bed, RM_HEAL_ROUGH sleeping rough or resting (the original
//    Sleep(): the night's sleep, a bed's, a gargoyle's or vampire's Rest). Battered arms and legs and inner organs
//    mend only in sleep (the original's chance, in Heal()).
//  - The Doctor's Athelas poultice heals 80 as before and also sets battered arms and legs (not a gargoyle's stone
//    ones, StoneLimbs.dm). Potions and brews as before. Time away (Away.dm) and asleep as a record (FarRecords.dm) heal by
//    these same rules, through the meals and sleep they get (RmFarLiveThrough).

#define RM_HEAL_MEAL 20
#define RM_HEAL_BED 10
#define RM_HEAL_ROUGH 5

var/rm_auto_heal = 0       // 1 brings the original's healing back

mob/Monsters/EatItem(obj/Items/ITEM)
	. = ..()
	if(. && HP > 0 && !GoingToDie) HP = min(MAXHP, HP + RM_HEAL_MEAL)

mob/Monsters/RemasterAwayMeal(Player/P)
	. = ..()
	if(. && HP > 0 && !GoingToDie) HP = min(MAXHP, HP + RM_HEAL_MEAL)

mob/Monsters/Sleep(TIME = 300)
	var/was = Sleeping
	. = ..()
	if(!was && Sleeping) spawn(100) RemasterSleepHeal()

mob/Monsters/proc/RemasterSleepHeal()
	while(src && Sleeping && HP > 0 && !GoingToDie)
		HP = min(MAXHP, HP + (RemasterInBed() ? RM_HEAL_BED : RM_HEAL_ROUGH))
		sleep(100)

// The original Heal() loop's limb and organ mending: in sleep only, unless the original healing is back.
mob/proc/RemasterMends()
	return rm_auto_heal || Sleeping

mob/Monsters/RemasterApplyRemedy(remedy, mob/Monsters/by)
	. = ..()
	if(!. || remedy != "poultice" || RemasterStoneBody()) return
	for(var/L in rm_stump_limbs) if(vars["Has[L]"] && (vars["[L]HP"] < OrganMaxHP || !(vars[L] in list("Good", "", null))))
		vars["[L]HP"] = max(vars["[L]HP"], OrganMaxHP)
		vars[L] = "Good"
		if(findtext(L, "Arm")) vars["CanUse[L]"] = 1
	if(HasLeftLeg && HasRightLeg) CanWalk = 1
