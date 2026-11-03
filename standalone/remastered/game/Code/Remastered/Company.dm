// Remastered (screens, staged 10-27, past the freeze): the first-company card. After the race pick, a start of 3 to 5
// people shows them before the story: each one's own sprite, name (type over it), age, sex and the four stats its race
// rolls. A die re-rolls one person; "Re-roll all" the whole company; the sex switch rolls that person again as the
// other sex. Begin goes on to the story, as before. The owner (10-27): "after we pick our race we should be shown the
// 3-5 char models With the states Name and random and maybe some customization options?"
// A re-roll makes a new unit of the same type where the old one stands, so the race's own New() rolls stay the only
// rules, every cache (portrait, look, GPU record) starts clean, and the old unit's start kit moves over unchanged.

#define RM_COMPANY_WAIT 6000    // the card gives up after 10 minutes (world.time tenths); the company is kept

Player/var/tmp/list/remaster_company    // the units on the card, while it is open
var/list/rm_company_stats = list("Strength", "Attack", "Magic", "Defence")   // the combat skills the roll sets (RmStartRolls), shown as:
var/list/rm_company_labels = list("Strength", "Agility", "Intelligence", "Defence")   // the owner's names for them (10-27: "keep the four names"); no Armour ("do not show the armor stat in the roll")

Player/proc/RemasterCompanyCard()
	if(RemasterTestRun()) return
	RemasterWaitHUD()
	if(!client || !remaster_hud_ready) return
	remaster_company = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && !M.Critter && M.HP > 0) remaster_company += M
	if(length(remaster_company) < 2)
		remaster_company = null
		return
	var/list/extra = list("units"=list())
	RmCompanyData(extra)
	. = RemasterAsk("Your first company. Name them, or roll again until you like who came.", "Your company", list("Begin", "Back"), "company", extra)
	remaster_company = null

// A new company's stats. Owner 10-27: "the intelligence and the new defense stats need to be apart of that roll of 20
// skills randomly allocated" (race-leaning): 20 points, each landing on Strength, Agility, Intelligence or the Defence
// skill with the race's weight (the means of its original rolls, Mobs.dm New()); the Defence skill is at least 1. The
// Defence stat (armour: the body's own toughness under every piece, plus what is worn) keeps the race's roll at two
// thirds, a frogman's thick hide (15-25) at 0.55 ("Lower the starting stat rolls"). Only starters: births and NPCs of
// the race keep the original rolls.
#define RM_START_POINTS 20
#define RM_START_MIN 3   // each of the four first (owner 10-27: "at least 3 minimun each and what is leftover from that spread it")
var/list/rm_start_lean = list("Human"=list(8, 10, 2, 7), "Dwarf"=list(11, 6, 1, 11), "Elf"=list(4, 12, 3, 9),
	"Orc"=list(12, 7, 1, 10), "Goblin"=list(7, 11, 1, 7), "Lizardman"=list(9, 11, 1, 12), "Frogman"=list(7, 9, 1, 21),
	"Kobold"=list(7, 12, 1, 5), "Ratman"=list(2, 13, 1, 2))   // Strength, Agility, Intelligence, Defence skill
#define RM_START_ROLL (2 / 3)
#define RM_START_ROLL_HIDE 0.55
mob/Monsters/proc/RmStartRolls()
	var/list/w = rm_start_lean[Race] || list(1, 1, 1, 1)
	var/total = 0
	for(var/k in w) total += k
	var/list/pts = list(RM_START_MIN, RM_START_MIN, RM_START_MIN, RM_START_MIN)
	for(var/n = 1, n <= RM_START_POINTS - 4 * RM_START_MIN, n++)
		var/r = rand(1, total)
		for(var/i = 1, i <= 4, i++)
			r -= w[i]
			if(r <= 0)
				pts[i]++
				break
	Strength = initial(Strength) + pts[1]
	Agility = initial(Agility) + pts[2]
	Intelligence = initial(Intelligence) + pts[3]
	// the real combat skills, so the roll counts in fights and shows on the Skills tab (owner 10-27: "the rolled skills
	// doesnt translate into the game"): Strength the Strength skill, Agility the Attack skill, Intelligence Magic
	if(!remaster_xp) remaster_xp = list()
	var/list/skill = list("Strength"=pts[1], "Attack"=pts[2], "Magic"=pts[3], "Defence"=pts[4])
	for(var/id in skill)
		vars["[id]Skill"] = max(1, skill[id])
		remaster_xp[id] = RemasterRSXP(vars["[id]Skill"])
	remaster_combat_seeded = 1   // a new unit: nothing to seed from (CombatSkills.dm)
	Defence = RmStartRoll(Defence, initial(Defence), Race == "Frogman" ? RM_START_ROLL_HIDE : RM_START_ROLL)

proc/RmStartRoll(v, base, k)
	var/rolled = v - base
	if(rolled <= 0) return v
	return base + max(1, round(rolled * k, 1))

// Back on the card: the company just made goes (its kit with it) and the race pick opens again (Restart.dm); a rare
// people drawn for this start is offered again.
Player/var/tmp/list/remaster_rare_back
Player/proc/RmCompanyBack()
	for(var/mob/Monsters/M in UnitList.Copy()) if(M.Owner == src)
		if(M in Selected) M.Deselect(src)
		del M
	UnitList = list()
	remaster_company = null
	if(remaster_rare_back) remaster_rare_drawn = remaster_rare_back
	remaster_rare_back = null

// The person's own Defence: worn armour adds its Defence to the unit's (Item Procs.dm), and the card shows the roll.
mob/Monsters/proc/RmOwnDefence()
	. = Defence
	for(var/obj/Items/Equipment/E in src) if(E.suffix == "(Equipped)" && isnum(E.Defence)) . -= E.Defence

// The card's numbers, rebuilt in place (the open ask holds this list, so the next HUD update carries the change). Names, ages and
// sex come from the HUD unit list by ref; the picture is RmCompanyPic's (below).
Player/proc/RmCompanyData(list/extra)
	var/list/rows = list()
	for(var/mob/Monsters/M in remaster_company)
		var/list/s = list()
		for(var/id in rm_company_stats) s += RemasterCombatLevel(M, id)
		rows += list(list("ref"=RemasterUIRef(M), "stats"=s, "pic"=RmCompanyPic(M)))
	extra["units"] = rows
	extra["names"] = rm_company_labels

// "askid|ref" re-rolls one, "askid|all" all of them, "askid|ref|sex" one as the other sex.
Player/proc/RemasterCompanyCommand(value)
	var/list/p = splittext("[value]", "|")
	if(!remaster_ask || remaster_ask["kind"] != "company" || length(p) < 2 || text2num(p[1]) != remaster_ask["id"]) return 0
	if(p[2] == "all")
		for(var/mob/Monsters/M in remaster_company.Copy()) RmCompanyReroll(M, prob(50) ? "Male" : "Female")
	else
		var/mob/Monsters/M = RemasterUIUnit(p[2])
		if(!istype(M) || !(M in remaster_company)) return 0
		var/sex = M.Gender
		if(length(p) >= 3 && p[3] == "sex") sex = (M.Gender == "Male") ? "Female" : "Male"
		RmCompanyReroll(M, sex)
	RmCompanyData(remaster_ask["extra"])
	RemasterHUDTick()
	return 1

// The same type rolled again where M stands, with M's kit and place in the company: a new person, so a new name. Rolled by the race's New(LOC, GENDER): GENDER 1 is male there.
Player/proc/RmCompanyReroll(mob/Monsters/M, sex)
	var/turf/T = M.loc
	if(!isturf(T)) return
	var/mob/Monsters/N = new M.type(T, sex == "Male")
	if(!(N.Race in rm_rare_races))
		N.RemasterStartSkills()
		N.RmStartRolls()
	for(var/obj/Items/I in M)
		if(I.suffix == "(Equipped)") M.ForceUnEquipItem(I)
		I.loc = T
		N.ForcePickUpItem(I)
	for(var/obj/Items/Equipment/E in N) N.EquipItem(E)
	if(N.weight > N.weightmax) N.weightmax = N.weight + 30
	N.ChangeOwnership(src)
	N.name = "{[name]} [N.name]"
	N.RemasterAutoName()
	N.CantBeGiven = 1
	N.PillarPowerup()
	remaster_company[remaster_company.Find(M)] = N
	if(M in Selected) M.Deselect(src)
	UnitList -= M
	del M

// The card's picture of M: bare, facing south, on the 64 px body the 3D view uses (Races64, the LOTR look), with what
// is the person's own (women's underclothes, beard, hair, a lizardman's tail) and none of the kit (owner 10-27: "use
// the new Lotr sprite we have and have them bare"). Made once a look and sent once a player, as the 3D view's are.
var/list/rm_company_pics = list()
Player/proc/RmCompanyPic(mob/Monsters/M)
	var/body64 = Remaster3DBody64(M)
	if(!body64) return null
	var/list/L = list(list(body64, M.icon_state))
	if(M.Gender == "Female")
		if(M.Race in list("Human", "Dwarf", "Elf")) L += RmLook(M, 'Female.dmi', "Unders", body64)
		else L += RmLook(M, 'Female.dmi', "Shirt", body64)
	if(M.Beard) L += RmLook(M, 'Beards.dmi', "[M.Beard]", body64)
	if(M.Hair) L += RmLook(M, 'Hair.dmi', "[M.Hair]", body64)
	if(M.icon == 'Lizardman.dmi') L += list(list(body64, "Tail"))
	var/key = ""
	for(var/list/X in L) key += "[length(X) >= 3 ? X[3] : X[1]]:[X[2]]|"
	var/id = md5("bare|[key]")
	var/file = "r3u-[id].png"
	var/icon/I = rm_company_pics[id]
	if(!I)
		I = Remaster3DStrip(L, SOUTH, 1, body64)
		if(!I) return null
		rm_company_pics[id] = I
	if(!remaster_3d_sent) remaster_3d_sent = list()
	if(!remaster_3d_sent[file])
		remaster_3d_sent[file] = 1
		src << browse_rsc(I, file)
	return file
