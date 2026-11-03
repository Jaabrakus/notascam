// Skill bar (Remastered): a unit's special abilities as buttons on the hero frame.
// The abilities are whatever the original Interact menu offers that unit right
// now (This Creature: Fly, Dragon Breath, Turn Into Mist, Lay Egg, Berserk, the
// gargoyle gem spells...; Magical Skills: Meditate, Nether Travel...), found by
// opening the menu with answers ready and recording the choices (StationCraft.dm's
// preset answers), so the bar follows the game's own rules for level, wings, gems
// and age. A button runs the original Interact with those answers; any question
// after them (a target, a direction) is asked as usual.

#define REMASTER_ABILITY_REFRESH 100   // ticks a unit's ability list is reused

// Everyday options that are not race skills (they have their own buttons or menus).
var/list/remaster_ability_skip = list("Run", "Dig On/Off", "Give Creature To", "Suicide", "Cancel", "Pull Out Arrow", "Closest Creature")

mob/Monsters/var/tmp
	list/remaster_abilities
	remaster_abilities_at = -1000

Player/var/tmp/remaster_preset_then_ask = 0   // once the preset answers run out, ask normally
Player/var/tmp/remaster_preset_sticky = 0     // Closest Creature: wait for the creature the answer names

Player/proc/RemasterInteractOptions(mob/Monsters/M, top)
	var/list/old = Selected
	var/oldusr = usr
	Selected = list(M)
	remaster_preset_choices = list(top)
	remaster_preset_record = 1
	remaster_preset_seen = null
	remaster_preset_asked = 0
	usr = src
	try
		Interact()
	catch(var/exception/E)
		world.log << "Remastered: ability scan failed: [E]"
	var/list/seen = remaster_preset_seen
	remaster_preset_choices = null
	remaster_preset_record = 0
	Selected = old
	usr = oldusr
	return seen

// The I key (skin.dmf): with one of your units selected, the page's card for the creatures beside it
// (remastered.html nearCardToggle: the original menu's Closest Creature, capture, child...); its own
// abilities are on its card's Interact tab. Otherwise the original Interact menu, as before.
Player/verb/RemasterInteractKey()
	set name = "Remaster-Interact-Key"
	set hidden = 1
	if(client && length(Selected) == 1)
		var/mob/Monsters/M = Selected[1]
		if(istype(M) && M.Owner == src && remaster_hud_ready)
			src << output("1", "mapwindow.hud:nearKey")
			return
	Interact()

// list(list(menu, ability)...) for one of the player's units.
Player/proc/RemasterAbilities(mob/Monsters/M)
	if(!istype(M) || M.Owner != src || M.HP <= 0 || M.rm_bound) return list()   // chained down, not yet tamed (Taming.dm): nothing to use
	if(world.time - M.remaster_abilities_at < REMASTER_ABILITY_REFRESH && M.remaster_abilities) return M.remaster_abilities
	var/list/out = list()
	var/list/tops = list("This Creature")
	if(M.MagicalAptitude) tops += "Magical Skills"
	for(var/top in tops)
		var/list/seen = RemasterInteractOptions(M, top)
		var/list/had = list()   // the menu can offer one twice (a vampire's Rest)
		if(seen) for(var/o in seen) if(!(o in remaster_ability_skip) && !(o in had))
			had += o
			out += list(list(top, o))
	// Closest Creature: the original asks once per creature beside the unit, so its
	// options are listed here the way Interact.dm builds them, one set per creature.
	// Rescue only does anything for one caught in a pit trap, so it's left out otherwise.
	var/list/partners = M.RemasterPartners(src)
	for(var/mob/Monsters/C in oview(1, M))
		if(C.Wagon || RemasterIsSiege(C)) continue
		if(M.Race == "Vampire" && M.density) out += list(list("Closest Creature", "Feed From [C]"))
		if(C.InHole) out += list(list("Closest Creature", "Rescue [C]"))
		// only a mate of its own kind (the opposite sex, both people or both animals) that isn't
		// already a partner with a "Child" chip in the unit panel: never a deer for a person
		if(M.Race != "Vampire" && !(C in partners) && C.Race == M.Race && C.Gender && M.Gender && C.Gender != M.Gender && !C.Critter == !M.Critter) out += list(list("Closest Creature", "Breed With [C]"))
		if(M.Werepowers == 1) out += list(list("Closest Creature", "Bite [C]"))
	M.remaster_abilities = out
	M.remaster_abilities_at = world.time
	return out

// "unitref|menu|ability": run it as the original Interact would.
Player/proc/RemasterUseAbility(value)
	var/list/p = splittext("[value]", "|")
	if(p.len != 3) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src || M.HP <= 0) return 0
	var/ok = 0
	for(var/list/A in RemasterAbilities(M)) if(A[1] == p[2] && A[2] == p[3]) ok = 1
	if(!ok)
		RemasterNotice("[M.name] can't do that right now.")
		return 0
	var/list/old = Selected
	var/oldusr = usr
	Selected = list(M)
	remaster_preset_choices = list(p[2], p[3])
	remaster_preset_then_ask = 1
	remaster_preset_sticky = p[2] == "Closest Creature"
	remaster_preset_asked = 0
	remaster_preset_record = 0
	usr = src
	try
		Interact()
	catch(var/exception/E)
		world.log << "Remastered: ability failed: [E]"
	remaster_preset_choices = null
	remaster_preset_then_ask = 0
	remaster_preset_sticky = 0
	Selected = old
	usr = oldusr
	M.remaster_abilities_at = -1000   // the list may change (Fly -> Land, mist...)
	return 1
