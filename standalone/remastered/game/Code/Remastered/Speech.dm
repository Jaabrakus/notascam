// What villagers show and say (Remastered, SS13-style).
//  - Examine: hovering a unit in 3D (and its Health tab) shows what anyone looking at it would
//    notice: pale and sweating, coughing, reeking of wine, green around the gills, bleeding,
//    bandaged, a grafted Orc arm or an iron leg, asleep or knocked out, cheerful or miserable.
//  - Speech bubbles: a short line over a unit's head in 3D for a few seconds when something happens
//    to it ("*cough*", "*hic*", "Ow!", "I don't feel so good..."). At most one every few seconds per
//    unit, so a busy village doesn't drown in them.

#define RM_SAY_TIME 40                // ticks a bubble stays up
#define RM_SAY_GAP 50                 // ticks before the same unit says something else

mob/Monsters/var/tmp
	rm_say = ""
	rm_say_at = -1000
	rm_bandaged_until = 0
	rm_said_hp = 0

// A bubble over the unit's head. force: even if it spoke just now.
mob/Monsters/proc/RemasterSay(text, force = 0)
	if(!text || HP <= 0) return 0
	if(!force && world.time - rm_say_at < RM_SAY_GAP) return 0
	rm_say = "[text]"
	rm_say_at = world.time
	return 1

mob/Monsters/proc/RemasterSaying()
	return world.time - rm_say_at < RM_SAY_TIME ? rm_say : null

// One of a few lines, so the same event doesn't always read the same.
proc/RemasterLine(list/L)
	return length(L) ? pick(L) : ""

// What someone looking at the unit notices (short, comma-separated).
mob/Monsters/proc/RemasterLook()
	var/list/L = list()
	if(HP <= 0 || GoingToDie) return "dead"
	if(rm_dying_until) L += "dying"   // bleeding out, 60 s to save (BleedOut.dm): it reads as knocked out otherwise
	else if(RemasterKnockedOut()) L += "knocked out"
	else if(Fainted) L += "unconscious"
	else if(Sleeping) L += "asleep"
	if(rm_poison > 0 && rm_poison_sick) L += "pale and sweating"
	if(rm_fever >= 3) L += "burning with fever"
	else if(rm_fever == 2) L += "flushed and feverish"
	else if(rm_fever == 1) L += "coughing"
	if(rm_foodsick > 0) L += "green around the gills"
	if(rm_drunk >= 60) L += "staggering drunk"
	else if(rm_drunk >= 35) L += "reeking of wine"
	else if(rm_drunk >= 15) L += "merry"
	if(BleedType in list("Badly", "Very Badly", "Extremly")) L += "bleeding badly"
	else if(BleedType) L += "bleeding"
	else if(rm_bandaged_until > world.time) L += "bandaged"
	if(HP < MAXHP * 0.3 && !Fainted) L += "badly hurt"
	L += RemasterLimbLooks()      // grafted and false limbs (Surgery.dm)
	if(rm_soul) L += "a soul in stone"   // SoulStone.dm
	// limbs only for people: animals keep the arm/leg vars unset, so every deer read "missing an arm, missing a leg" (playtest)
	if(HumanParts)
		if(!HasLeftArm || !HasRightArm) L += "missing an arm"
		if(!HasLeftLeg || !HasRightLeg) L += "missing a leg"
	if(rm_moods_on && !length(L))
		if(remaster_mood >= 75) L += "cheerful"
		else if(remaster_mood < 25) L += "miserable"
	return jointext(L, ", ")

// Hurt: "Ow!" when health drops a lot at once (checked each care step).
mob/Monsters/proc/RemasterSayHurt()
	if(rm_said_hp && HP < rm_said_hp - MAXHP * 0.12 && HP > 0) RemasterSay(RemasterLine(list("Ow!", "Argh!", "Ouch!", "That hurt!")))
	rm_said_hp = HP
