// A slave's hobble in a group's pace (Captives.dm): Formations.dm declares RemasterOwnStep, and an override compiled
// before the declaration is not used, so this file is included after it.
mob/Monsters/RemasterOwnStep()
	. = ..()
	if(rm_cap_state == "slave") . = max(. + 1, round(. * 1.25))
