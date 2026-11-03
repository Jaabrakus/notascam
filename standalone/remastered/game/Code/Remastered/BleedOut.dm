// Bleeding out (the user, 2026-10-25, via the coordinator: "someone that trained up a unit and dies quickly would
// devastate them"): a unit that would bleed to death (Health.dm's bleeding rolls, Stumps.dm's last blood) falls instead,
// out cold and dying, for RM_BLEED_OUT (60 s). Someone else can save it with what stops bleeding - a bandage, a torch or
// a fire, an Athelas poultice, a healing draught or the Elixir of Life, a Doctor: those within 3 tiles who carry one do
// it, else one who carries one comes over, and the Doctor puts it before all other work (Stumps.dm's care: the dying count
// as a bleeding stump). Saved, it comes to with little blood, which comes back slowly; unsaved, it dies. It can't treat
// itself, its bleeding doesn't stop by itself, and foes can still finish it or take it captive as one knocked out
// (Subdue.dm). Its card's Health tab and the 3D view show the seconds left.
#define RM_BLEED_OUT 600
var/rm_bleed_out_on = 0          // 0: bleeding to death is at once, as the original's (the owner, 10-27: "the 60 second
                                 // bleeding" goes; Falls.dm). 1 = the 60 s dying, kept for tests
mob/var/tmp/rm_dying_until = 0   // world.time it bleeds to death unless saved
mob/Monsters/var/tmp/rm_help_called = 0   // it called for help for this wound (Stumps.dm RemasterStumpCare: once)
mob/Monsters/var/tmp/mob/rm_downed_by     // the foe whose blow, shot or throw brings it down this moment (Falls.dm): named in its fall's lines

// Would bleed to death now: dying instead (1), or already dying (1); 0 when it isn't spared.
proc/RmBleedOut(mob/M)
	if(!rm_bleed_out_on || !istype(M, /mob/Monsters)) return 0
	var/mob/Monsters/U = M
	if(U.rm_dying_until) return 1
	if(U.HP <= 0 || U.GoingToDie || !isturf(U.loc)) return 0
	U.rm_dying_until = world.time + RM_BLEED_OUT
	U.rm_help_called = 0   // going down, it calls for help once (Stumps.dm); down, it never treats itself (the user, 2026-10-26:
	                       // "a dying cannot save themselves or a knocked out one"): only friends or the Doctor
	U.remaster_ko_until = U.rm_dying_until + 20   // down and out cold past its end: it can't act; foes may finish it or rope it (Subdue.dm)
	U.Fainted = 1
	U.destination = null
	U.Target = null
	U.remaster_attack = null
	RemasterHit(U, 0, "ko", null)
	RmKoDrop(U)   // it lets go of its weapon (Gear3D.dm)
	RmDownLeft(U)   // those fighting it turn to a foe still standing (Falls.dm)
	var/mob/K = Rm3DGone(U.rm_downed_by) ? null : U.rm_downed_by   // brought down by a foe: who did it, as a death names its killer
	view(U) << "<b><font color=red>[K ? "[U] is struck down by [K], bleeding out!" : "[U] collapses, bleeding out!"]</font></b>"
	if(istype(U.Owner, /Player)) U.Owner:RemasterLog("[U.RemasterBareName()] [K ? "was struck down by [RmKillerName(K, U.Owner)] and " : ""]is bleeding out: [RM_BLEED_OUT / 10] s to save them (a bandage, torch, poultice or healing potion from someone near, or a Doctor)", "problem", U)
	spawn(10) RmBleedOutLoop(U)
	return 1

proc/RmBleedOutLoop(mob/Monsters/U)
	while(U && U.rm_dying_until)
		if(U.HP <= 0 || U.GoingToDie)
			U.rm_dying_until = 0
			return
		if(U.remaster_ko_until < U.rm_dying_until + 20) U.remaster_ko_until = U.rm_dying_until + 20   // knocked out again meanwhile: still down
		U.Fainted = 1
		if(world.time >= U.rm_dying_until)
			U.rm_dying_until = 0
			U.DeathType = "Bleeding To Death"
			U.GoingToDie = 1
			view(U) << "<b><font color=red>[U] has bled to death!!"
			U.Death()
			return
		if(RmFinishOff(U)) return   // a Lethal foe beside it, none standing near it (Falls.dm)
		sleep(10)

// Dying, nothing else wakes it (a knock-out's own 30 s timer, Subdue.dm): only being saved, or death.
mob/Monsters/RemasterWakeUp()
	if(rm_dying_until) return
	return ..()

// Saved: it comes to with little blood, which comes back slowly (Stumps.dm's loop); its bleeding is over.
mob/Monsters/proc/RmBleedSaved(mob/Monsters/by, what)
	if(!rm_dying_until) return
	rm_dying_until = 0
	remaster_ko_until = world.time
	BleedType = null
	SaidBleed = 0
	BloodContent = max(BloodContent, round(MaxBloodContent * 0.15))
	if(BloodContent < MaxBloodContent) rm_blood_back = 1
	RemasterWakeUp()
	if(!rm_stumps) rm_stumps = list()
	RemasterStumpLoop()
	rm_help_called = 0
	var/how = what ? " ([lowertext(what)])" : ""
	var/who = by ? by.RemasterBareName() : "someone"
	view(src) << "<font color=#e0802a>[who] saves [RemasterBareName()] from bleeding out.</font>"
	if(istype(Owner, /Player)) Owner:RemasterLog("[who] saved [RemasterBareName()] from bleeding out[how]", "good", src)

// Stumps.dm's care treats the dying as a bleeding stump: the unit's own care step (those within 3 tiles, one who
// carries something comes over) and the Doctor's.
mob/Monsters/RemasterStumpBleeding()
	return ..() || (rm_dying_until ? 1 : 0)

// Dying of wounds, not a stump, a bandage is put on the wounds (Stumps.dm offers one only for an open stump).
mob/Monsters/RemasterStumpBandageSpot(hold)
	. = ..()
	if(!. && rm_dying_until && !RmStumpBleedingNow()) return "wounds"

mob/Monsters/proc/RmStumpBleedingNow()
	if(rm_stumps) for(var/L in rm_stumps) if(rm_stumps[L] == "open" || rm_stumps[L] == "bandaged") return 1
	return 0

mob/Monsters/RemasterBleedStops()
	if(rm_dying_until) return 0   // dying, its bleeding doesn't stop by itself
	return ..()

// A treatment on the dying saves it: a stump's own treatment as ever, and bleeding out of wounds (no stump) whatever
// would stop a stump's (the torch, bandage or poultice used up as it would be).
mob/Monsters/RemasterStumpDo(list/O, Player/P)
	if(!rm_dying_until) return ..()
	if(RmStumpBleedingNow())
		. = ..()
		if(.) RmBleedSaved(O["by"], O["label"])
		return
	var/obj/Items/I = O["item"]
	switch(O["kind"])
		if("torch")
			I:rm_burns--
			if(I:rm_burns <= 0) RmStumpUseUp(I)
		if("bandage") RmStumpUseUp(I)
		if("poultice")
			if(!RemasterApplyRemedy("poultice", O["by"])) return 0
			if(I) RmStumpUseUp(I)
		if("elixir", "healing", "restore")
			if(!..()) return 0
		if("spell") return 0
	RmBleedSaved(O["by"], O["label"])
	return 1
