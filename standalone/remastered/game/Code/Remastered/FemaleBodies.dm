// Hidden Clans: women on their own GOA bodies (the owner, 2026-11-01: "add in the females and the hybrids").
// Banners drew a woman on her race's male sheet with Female.dmi's underclothes and Hair.dmi laid over it. The GOA pack's
// female sheets (reports/goa-sprite-test/staged FEMALES.md: "<male sheet> Female.dmi", 80 of them, every race and every
// hybrid look: Ashen, Hellblooded, Marked, Possessed1/2, Werewolf, Zombie) are bodies of their own with their top and
// hair drawn in, so their underclothes and hair are not laid over again (View3D.dm Remaster3DLayers). An elf woman gets
// the Elf sheets (Banners draws elves on the Human sheet). Everything else keyed by the race's sheet name stays the
// race's (Gear.dm RmRaceSheet/RmGearSheet: armour fitted to the male shape, limb grafts, ropes, 3D grips and the doll's
// part map), so it all keeps working on the slimmer body.
// Only Human Female has been tuned limb by limb; the other 79 are the pipeline's first pass.

var/list/rm_female_sheets = list()   // path -> whether it exists

// The female sheet for a woman's 64 px body at path, else path.
proc/RmFemaleBody(mob/M, path)
	if(!path || !istype(M, /mob/Monsters)) return path
	var/mob/Monsters/W = M
	if(W.Gender != "Female" || W.Critter) return RmElfMaleBody(W, path)
	var/p = "[path]"
	var/base = copytext(p, 1, length(p) - 3)   // without ".dmi"
	if(W.Race == "Elf" && findtext(base, "Races64/Human") && !findtext(base, "Races64/HumanBlack"))
		base = replacetext(base, "Races64/Human", "Races64/Elf")
	var/f = "[base] Female.dmi"
	if(isnull(rm_female_sheets[f])) rm_female_sheets[f] = fexists(f)
	return rm_female_sheets[f] ? f : path

// An elf man gets his own GOA body (the owner, 11-02: "elfs males have their own sprites"): Races64/Elf.dmi, the pack's
// Male/Elf/base (staged scratch-elf-male), his blonde hair and pointed ears drawn in, instead of the Human sheet with
// the old Elf head (Hair.dmi "ElfMale") laid over it. Everything keyed by the race's sheet stays Human's, as for the women.
var/rm_elf_male_sheet = "Icons/Remastered/Races64/Elf.dmi"
var/rm_elf_male_ok = null
proc/RmElfMaleBody(mob/Monsters/M, path)
	if(M.Race != "Elf" || M.Critter || "[path]" != "Icons/Remastered/Races64/Human.dmi") return path
	if(isnull(rm_elf_male_ok)) rm_elf_male_ok = fexists(rm_elf_male_sheet)
	return rm_elf_male_ok ? rm_elf_male_sheet : path

// A body with its head's hair drawn in: a woman's own sheet or the elf man's, so Hair.dmi is not laid over it (View3D.dm).
proc/RmOwnHeadBody(body64)
	return RmIsFemaleBody(body64) || (body64 && "[body64]" == rm_elf_male_sheet)

proc/RmIsFemaleBody(body64)
	return body64 && findtext("[body64]", " Female")   // the sheets are "<sheet> Female": only theirs hold the word
