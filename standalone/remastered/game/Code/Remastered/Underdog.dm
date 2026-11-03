// Morale as a tug of war (the user, 2026-10-26: high morale "more critical hits but less damage? but more critical to do
// potential maiming", low morale "lower chances but chance for a high critical hit"; then "i want a good underdawg strory the
// first one shaken shouldnt lose all the time it should be a tug of war right"; "Into build 58"). Each state's blows:
//   state          land    plain blow   critical on   critical         a critical's sever chance
//   Battle fury     +0       x0.75        18-20         x1.5             x1.5
//   Emboldened      +0       x0.9         19-20         x1.5             x1.25
//   Steady          +0       x1           20            x1.5             x1
//   Shaken          -3       x1           20            x2               x1.5
//   Broken          -5       x1           20            x2.5             x2
// So a side ahead maims more but hits softer, and one behind lands less but its rare critical hits hard: a blow's worth
// stays within about 15% of Steady's either way, so no side snowballs. Morale no longer moves armour saves or awareness.
// The rest of morale stays (Morale.dm): what moves it, the blood held back, bandaging, limb shock, routing NPCs.
var/rm_underdog_on = 1      // 0: morale's ties as before (Morale.dm's table)
var/list/rm_md_land = list("2"=0, "1"=0, "0"=0, "-1"=-3, "-2"=-5)
var/list/rm_md_hit = list("2"=0.75, "1"=0.9, "0"=1, "-1"=1, "-2"=1)
var/list/rm_md_crit_low = list("2"=18, "1"=19, "0"=20, "-1"=20, "-2"=20)
var/list/rm_md_crit = list("2"=1.5, "1"=1.5, "0"=1.5, "-1"=2, "-2"=2.5)     // a critical's damage in all (rm_crit_mult 1.5 of it)
var/list/rm_md_sever = list("2"=1.5, "1"=1.25, "0"=1, "-1"=1.5, "-2"=2)

proc/RmMdState(mob/M)
	return istype(M, /mob/Monsters) && !isnull(M:rm_morale) ? "[M:rm_mstate]" : "0"

// A land roll's change (CombatSkills.dm RmMeleeWhere).
proc/RmMoraleLand(mob/M)
	return rm_underdog_on ? rm_md_land[RmMdState(M)] : 0

// The lowest d20 face that is a critical (CombatSkills.dm RmMeleeWhere): before, emboldened 19, shaken and broken none.
proc/RmMoraleCritLow(mob/M)
	if(!rm_underdog_on)
		if(istype(M, /mob/Monsters) && M:rm_mstate < 0) return 21
		return istype(M, /mob/Monsters) && M:rm_mstate == 1 ? 19 : 20
	return rm_md_crit_low[RmMdState(M)]

// A landed melee blow's damage (Combats.dm, before rm_crit_mult): a plain blow's factor, or a critical's beyond x1.5.
proc/RmMoraleBlow(mob/M)
	if(!rm_underdog_on) return 1
	var/s = RmMdState(M)
	return M.rm_crit ? rm_md_crit[s] / rm_crit_mult : rm_md_hit[s]

mob/Monsters/RmMoraleSever()
	if(!rm_underdog_on) return ..()
	return rm_crit ? rm_md_sever[RmMdState(src)] : 1
mob/Monsters/RmMoraleSave()
	return rm_underdog_on ? 0 : ..()
mob/Monsters/RmMoraleAware()
	if(!rm_underdog_on) return ..()
	return rm_committed_until > world.time ? rm_commit_aware : 0
mob/Monsters/RmMoraleStateText()
	if(!rm_underdog_on || isnull(rm_morale)) return ..()
	switch(rm_mstate)
		if(2) return "Battle fury: crits on 18-20 that maim more, plain blows softer; bleeds later, won't bandage itself"
		if(1) return "Emboldened: crits on 19-20 that maim more, plain blows a little softer; bleeds later"
		if(-1) return "Shaken: lands a little less, but its crits hit twice as hard and maim more; bandages first, bleeds later"
		if(-2) return "Broken: lands less, but its crits hit two and a half times as hard and maim twice as often; bleeds later"
	return ..()
