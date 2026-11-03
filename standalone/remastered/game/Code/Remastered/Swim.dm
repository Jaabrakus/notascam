// Swimming (swim, 10-29; the owner: "add swimming to the game some races faster than other"). Deep water (the sea, a
// river, a lake, a swamp, cave water: Water.dm and Building/TurfTypes.dm, all dense) stays shut to walking; a unit that
// swims goes into it as onto open ground (Chains/Enter.dm, the ground's rule), at its race's pace (rm_swim_pace, a share
// of its walking pace: Chains/StepDelay.dm, Formations.dm RemasterOwnStep). The route search counts a water tile as
// rm_swim_cost steps (Orders.dm RemasterOrderPathDM), so routes keep to land and fords where the way round is short. The
// battle field and a group's places stay on land (no fighting in deep water). Stone gargoyles and golems sink, plants
// can't swim, and carts and siege engines don't float; flyers fly over as before; a mountain lake up in the rock
// (remaster_waterlift) and the Sky layer have none. The 3D view draws a swimmer down in the water to the chest.
// Mirrored in the engine (engine/native/RmSwim.cs, native version 25; the walk checks, the route search and the route
// map read it): change both together. RM_SWIM=0 in the server's environment, or an older engine: no swimming.
var/rm_swim_on = 0
var/rm_swim_cost = 3        // a water tile's steps to the route search
var/list/rm_swim_none = list("Gargoyle", "Golem", "Plant")
// A swimmer's pace, a share (%) of its walking pace, by race; any other race rm_swim_pace_else.
var/list/rm_swim_pace = list("Frogman" = 100, "Lizardman" = 90, "Illithid" = 70, "Ratman" = 60, "Dragon" = 60,
	"Elf" = 55, "Human" = 50, "Werewolf" = 50, "Orc" = 45, "Goblin" = 45, "Svartalfar" = 45, "Kobold" = 40,
	"Vampire" = 40, "Devourer" = 40, "HalfDemon" = 40, "Demon" = 35, "Spider" = 30, "Dwarf" = 30)
var/rm_swim_pace_else = 40

// Deep water a swimmer can go into (RmSwim.Water).
proc/RmSwimWater(turf/T)
	return rm_swim_on && T && T.density && T.z != SKY_LAYER && istype(T, /turf/grounds/waters) && !T.remaster_waterlift

// This unit swims (RmSwim.Swims).
proc/RmSwims(mob/M)
	if(!rm_swim_on || !istype(M, /mob/Monsters) || !M.density || M:Flying || M:Wagon || istype(M, /mob/Monsters/RemasterSiege)) return 0
	return !(M:Race in rm_swim_none)

// A step onto T for the route search: deep water swum costs rm_swim_cost steps, flown over or any other tile one.
proc/RmSwimCost(turf/T, mob/Monsters/M)
	return (RmSwimWater(T) && !RmFliesOver(M, T)) ? rm_swim_cost : 1

// A step's time from deep water: at the race's pace, at least a tick slower than walking but for a race as quick in water.
mob/Monsters/proc/RmSwimDelay(d)
	var/p = Race ? rm_swim_pace[Race] : null
	if(isnull(p)) p = rm_swim_pace_else
	if(p >= 100) return d
	return max(d + 1, round(d * 100 / max(10, p)))

// The races and their pace, for the help and tests: "Frogman 100%, ..., others 40%; never: Gargoyle, Golem, Plant".
proc/RmSwimTable()
	var/list/L = list()
	for(var/r in rm_swim_pace) L += "[r] [rm_swim_pace[r]]%"
	return "[jointext(L, ", ")], others [rm_swim_pace_else]%; never: [jointext(rm_swim_none, ", ")]"
