// The undead's and the cursed's 64 px looks (Remastered).
//  - A plague zombie (a Devourer's bite, Vars.dm Infection) keeps the picture of the body it was:
//    in 3D it is that race's body rotted (Races64/<sheet>-Zombie.dmi, art/enhance/zombie64.py):
//    grey-green flesh, patches of decay and bare bone, torn clothes, dead eyes, blood at the mouth.
//    The original marks it only with a bloody overlay, which the 3D view does not draw.

var/list/rm_zombie_sheets = list()   // path -> whether it exists (zombie and werewolf sheets)

proc/RmZombieSheet(mob/Monsters/M, name)
	if(!istype(M) || M.Race != "Zombie") return null
	var/path = "Icons/Remastered/Races64/[name]-Zombie.dmi"
	if(isnull(rm_zombie_sheets[path])) rm_zombie_sheets[path] = fexists(path)
	return rm_zombie_sheets[path] ? path : null

//  - A werewolf changed at night (Werewolves.dm: the original puts its one 32 px Werewolf.dmi on
//    every race) is drawn as its own race's wolf (Races64/<sheet>-Werewolf.dmi,
//    art/enhance/werewolf64.py): its shape, furred in a wolf's coat tinted by the race, wolf ears,
//    red eyes, fangs and claws. The race is the picture it had before the change (SavedIcon).
proc/RmWerewolfSheet(mob/Monsters/M)
	if(!istype(M) || !M.Werepowers || !M.SavedIcon) return null
	var/name = remaster_3d_races64[RmIconName(M.SavedIcon)]
	if(name && M.Race == "Dwarf") name = "Dwarves"
	if(!name) return null
	var/path = "Icons/Remastered/Races64/[name]-Werewolf.dmi"
	if(isnull(rm_zombie_sheets[path])) rm_zombie_sheets[path] = fexists(path)
	return rm_zombie_sheets[path] ? path : null
