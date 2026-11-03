// Real names. Units used to be called "{Owner} Orc". Each now gets a first
// name built from its race's sounds, keeping the original "{Owner} " prefix
// and the King/Queen title (see the original Rename verb). Players can rename
// from the unit panel with the same rules (25 characters).

var/list/remaster_name_parts = list(
	"Orc"=list(list("Gr","Ur","Kr","Th","Mog","Gor","Az","Dr","Sh","Zug"), list("ak","ash","uk","og","um","ag","ok","uz","ar","ush"), list("","nak","gul","thar","rok")),
	"Goblin"=list(list("Sn","Gr","Sk","Nix","Iz","Fiz","Kr","Gob","Zik","Rat"), list("ik","ag","eek","ix","ob","it","ag","uz"), list("","le","ik","nob","zit")),
	"Human"=list(list("Al","Ber","Cor","Ed","Hal","Ma","Ro","Ste","Wil","Ga","Tho","Eli"), list("an","ric","wyn","bert","mund","ard","las","ven","ra","na"), list("","son","ley","ton")),
	"Dwarf"=list(list("Thor","Dur","Bal","Gim","Bor","Kaz","Dwa","Brom","Har","Gun"), list("in","ar","li","im","ur","rik","dok","grim"), list("","bek","drin","mund")),
	"Elf"=list(list("Ael","Ela","Fae","Ith","Lae","Syl","Tha","Cae","Ner","Ilia"), list("ran","wen","dor","las","riel","thir","nor","lin"), list("","iel","eth","ae")),
	"Kobold"=list(list("Kik","Snip","Yip","Tik","Rek","Zap","Nib","Skri"), list("ik","ap","eek","it","ak","op"), list("","ki","zz","yip")),
	"Lizardman"=list(list("Ssa","Ka","Thes","Ix","Zsa","Rhy","Sil","Vex"), list("ss","tal","ith","rax","zor","shk"), list("","ss","ka","zith")),
	"Ratman"=list(list("Skrit","Gnaw","Sni","Vrik","Tchk","Quee","Rask"), list("ch","ik","itt","eek","ak"), list("","ch","ik","sk")),
	"Frogman"=list(list("Gru","Blo","Rib","Kro","Plo","Mur"), list("ak","op","bit","ug","bbo"), list("","p","k","gg")),
	"Spider"=list(list("Ssi","Ara","Ven","Ith","Kre","Shel"), list("ssa","neth","rix","ka","zith"), list("","ss","a")),
	"Gargoyle"=list(list("Grav","Stone","Kor","Ash","Bas","Ob"), list("el","ul","rak","im","ox"), list("","ith","ar")),
	"Devourer"=list(list("Vor","Gul","Maw","Xa","Thul","Nak"), list("ax","gor","uth","ra","ok"), list("","oth","ash")),
	"Dragon"=list(list("Vael","Drak","Ignis","Syr","Kal","Thra"), list("ox","rath","ion","oros","ith"), list("","ax","or")))

proc/RemasterMakeName(race, gender)
	var/list/P = remaster_name_parts[race]
	if(!P) P = remaster_name_parts["Human"]
	var/name = "[pick(P[1])][pick(P[2])][pick(P[3])]"
	// A softer ending for most female names (not for every race).
	if(gender == "Female" && !(race in list("Spider", "Gargoyle", "Devourer")) && prob(70))
		name = "[copytext(name, 1, max(3, length(name)))][pick("a", "e", "ia", "wyn", "ra")]"
	return uppertext(copytext(name, 1, 2)) + lowertext(copytext(name, 2))

// The part of the name after "{Owner} " (and after a King/Queen title).
mob/Monsters/proc/RemasterBareName()
	var/n = "[name]"
	var/i = findtext(n, "} ")
	return i ? copytext(n, i + 2) : n

mob/Monsters/proc/RemasterSetName(bare)
	if(IsRoyal) name = "[RmTitle()] {[Owner]} [bare]"   // the ruler's chosen title (Rulership.dm)
	else name = "{[Owner]} [bare]"

// A unit whose name is still just its race (or a copy of its owner prefix) gets one.
mob/Monsters/proc/RemasterAutoName()
	if(Wagon || Egg || Critter || !Race || !ismob(Owner)) return 0
	var/bare = RemasterBareName()
	if(bare != "[Race]" && bare != "[initial(name)]") return 0
	var/n = RemasterMakeName(Race, Gender)
	// One the realm hasn't got yet (a few tries): a race has a few hundred names, so most villages of 20 had two units
	// of one name, which read as one in the log and the family tree. Not looked for in a very big realm (a look reads
	// every unit).
	var/Player/P = Owner
	if(istype(P) && length(P.UnitList) <= 400)
		for(var/tries = 1, tries <= 6 && RmNameTaken(P, n), tries++) n = RemasterMakeName(Race, Gender)
	RemasterSetName(n)
	return 1

proc/RmNameTaken(Player/P, n)
	for(var/mob/Monsters/M in P.UnitList) if(M.Owner == P && M.RemasterBareName() == n) return 1
	return 0

Player/proc/RemasterRenameCommand(value)
	var/list/p = splittext("[value]", "|")
	if(length(p) < 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	if(!istype(M) || M.Owner != src) return 0
	var/bare = RemasterTrim(replacetext(replacetext(replacetext(replacetext(jointext(p.Copy(2), "|"), "<", ""), ">", ""), "{", ""), "}", ""))
	if(!length(bare))
		RemasterNotice("Type a name first.")
		return 0
	if(length(bare) > 25)
		RemasterNotice("This name is far too long. Try a shorter one.")
		return 0
	var/old = M.RemasterBareName()
	M.RemasterSetName(bare)
	RemasterLog("[old] is now called [bare]", "birth", M)
	return 1

proc/RemasterTrim(t)
	t = "[t]"
	while(length(t) && copytext(t, 1, 2) == " ") t = copytext(t, 2)
	while(length(t) && copytext(t, length(t)) == " ") t = copytext(t, 1, length(t))
	return t
