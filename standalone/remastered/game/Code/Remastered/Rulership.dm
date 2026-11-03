// Rulership (planning/RULERSHIP.md; the user's decisions, 2026-10-23). Every settlement stage has its seat of rule,
// with its regalia and its health; a ruler's title comes from a list for their race and stage, chosen when crowned;
// a realm keeps one of five laws of succession; and the heir carries an heir's item, which can be stolen.
// Succession honours who holds the items: whoever of the realm holds its heir's item is its heir, and when a realm's
// seat falls empty while another realm holds that item, the other realm has a claim on the seat (the claimed realm
// yields and becomes its vassal, or refuses and it's war).
// Hooks elsewhere: AddLeader and RemoveLeader (Items/Crowning.dm), the crown's place (EquipItem, Items/Item
// Procs.dm), RemasterCrownHealth (CombatSkills.dm), RemasterHeirOf and RemasterSuccession (Succession.dm), the rank-up
// and the Kingdom's need (Progress.dm), the names (Names.dm, SelectedActions.dm), the Realm page's commands
// (Realms.dm), peace and a fallen realm (War.dm). Checked by tools/check_rulership.py (tests/rulership_test.dm).

#define RM_CLAIM_WINDOW 6000   // ticks a claimant has to press a claim (10 minutes)
#define RM_LAW_MOOD -10        // changing the law of succession: mood -10 for a week
#define RM_LAW_DAYS 7
#define RM_GROWN 5             // grown from this age (RemasterOfAge, Capture.dm)

// --- the seats --------------------------------------------------------------------------------------------------
// By stage (rm_ranks, Progress.dm): the seat's health, its regalia and where that is made. A ruler has the health of
// the settlement's stage as far as the regalia they wear reaches; the Kingdom's is RM_CROWN_HEALTH (CombatSkills.dm).
var/list/rm_seat_health = list(50, 75, 100, 125, RM_CROWN_HEALTH)
var/list/rm_seat_items = list("Chief's Totem", "Elder's Staff", "Chain of Office", "Silver Circlet", "Gold Crown")
var/list/rm_seat_made = list("at a carpentry from 2 wood and 1 bone, or a Bone Crown", "at a leatherworks from 2 wood and 1 skin",
	"at a forge from 3 iron ingots", "at a forge from 2 silver ingots and a cut emerald", "at a forge from 3 gold ingots and a cut ruby")

// Titles by race, then stage (Camp .. Kingdom); "Male/Female" for a pair. Other races use the Human list.
var/list/rm_titles = list(
	"Human"=list(list("Chief", "Elder"), list("Headman/Headwoman", "Elder"), list("Reeve", "Elder"), list("Lord/Lady", "Duke/Duchess"), list("King/Queen", "High King/High Queen", "Emperor/Empress")),
	"Dwarf"=list(list("Elder"), list("Stonewarden", "Elder"), list("Stonewarden"), list("Thane"), list("High Thane", "Under-King/Under-Queen")),
	"Orc"=list(list("Chief"), list("Big Boss", "Chief"), list("Big Boss"), list("Warlord"), list("Overlord", "Warchief")),
	"Goblin"=list(list("Chief"), list("Head Goblin", "Chief"), list("Head Goblin"), list("Boss"), list("Goblin King/Goblin Queen")),
	"Elf"=list(list("Elder"), list("Warden", "Elder"), list("Warden"), list("Lord of the Wood/Lady of the Wood"), list("High Lord/High Lady")),
	"Lizardman"=list(list("Elder"), list("Shaman", "Elder"), list("Shaman"), list("Sire/Matriarch"), list("Great Sire/Great Matriarch")),
	"Kobold"=list(list("Den-elder"), list("Den-elder"), list("Den-elder"), list("Den-lord/Den-lady"), list("Great Father/Great Mother")))
// The heir's word on the card; Heir for the races without one.
var/list/rm_heir_words = list("Human"="Prince/Princess", "Elf"="Prince/Princess", "Dwarf"="Prince/Princess", "Svartalfar"="Prince/Princess", "Vampire"="Prince/Princess")

// The laws of succession: id -> name, what it does. The heir's item comes first under every law.
var/list/rm_laws = list(
	"bloodline"=list("Bloodline", "The named heir, else the eldest child, then the eldest sibling, then the eldest of the house."),
	"chosen"=list("Chosen heir", "Whoever the ruler names; if no one, the eldest of the house."),
	"might"=list("Might", "The strongest grown member of the house (Attack, Strength and Defence)."),
	"council"=list("Council", "The people choose: the grown unit they like best (mood, family, level)."),
	"regalia"=list("Regalia", "Whoever holds the realm's regalia, the item its last ruler was crowned with: even an enemy."))
var/list/rm_law_by_race = list("Human"="bloodline", "Dwarf"="bloodline", "Elf"="chosen", "Orc"="might", "Goblin"="might", "Lizardman"="council", "Kobold"="council")

mob/Monsters/var
	rm_title                 // saved: the ruler's title ("King"), chosen when crowned
	rm_title_stage = 0       // saved: the stage that title was chosen at
	rm_seat_v = 0            // saved: 1 when crowned under these rules (a ruler crowned before keeps what they were given)
mob/Monsters/var/tmp/rm_title_asking = 0

Player/var
	rm_law                   // saved: the law of succession; null until the first crowning (the race's law)
	list/rm_house_titles     // saved: house id -> the title entry ("Lord/Lady") last chosen in it
	rm_seat_vacant = 0       // saved: the last ruler died or stepped down, and no one has been crowned since
	list/rm_claim            // saved: another realm's claim on this realm's empty seat (RmClaimScan)
Player/var/tmp/rm_claim_until = 0

// --- the items --------------------------------------------------------------------------------------------------
// Regalia and heir's items are worn in the crown's place. They never fade where they're dropped. The pictures are
// placeholders: the two crown sprites, tinted (art/regalia/make_regalia_icons.py).
obj/Items/Equipment/Armour/Crown
	var
		rm_tier = 0          // the stage this regalia lets its wearer rule, 1 (Camp) to 5 (Kingdom); 0 when it isn't regalia
		rm_heir_item = 0     // an heir's circlet or band
		rm_realm             // saved: the key of the realm it belongs to (an heir's item: when first put on; regalia: at a crowning)
		rm_realm_house       // saved: that realm's house then, for messages
		rm_item_uid          // saved: names it in a claim
	Bone
		rm_tier = 1
	Gold
		rm_tier = 5
	RmTotem
		// its values: art/items/catalogue.json row equipment.armour.crown.rmtotem (export_items.py writes ItemData.dm)
	RmStaff
		// its values: art/items/catalogue.json row equipment.armour.crown.rmstaff (export_items.py writes ItemData.dm)
	RmChain
		// its values: art/items/catalogue.json row equipment.armour.crown.rmchain (export_items.py writes ItemData.dm)
	RmSilverCirclet
		// its values: art/items/catalogue.json row equipment.armour.crown.rmsilvercirclet (export_items.py writes ItemData.dm)
	RmHeirCirclet
		// its values: art/items/catalogue.json row equipment.armour.crown.rmheircirclet (export_items.py writes ItemData.dm)
	RmHeirBand
		// its values: art/items/catalogue.json row equipment.armour.crown.rmheirband (export_items.py writes ItemData.dm)

var/list/rm_regalia = list()   // every regalia and heir's item in the world
obj/Items/Equipment/Armour/Crown/New()
	. = ..()
	rm_regalia |= src
obj/Items/Equipment/Armour/Crown/Del()
	rm_regalia -= src
	return ..()
obj/Items/Equipment/Armour/Crown/DeleteItem()
	return

// Craft new gear › Regalia (Gear.dm). They are kept out of rm_gear_defs, the generated catalogue that every new item
// with its 64 px pictures is checked against (tests/gear_test.dm), and go into the workshops' lists directly.
var/list/rm_regalia_defs = list(
	list("id"="regalia.totem", "name"="Chief's Totem", "slot"="regalia", "group"="wood", "tier"="wood", "station"="carpentry", "craft"="WoodCraftingSkill", "craft_level"=3, "types"=list(/obj/Items/Equipment/Armour/Crown/RmTotem), "recipe"=list("wood"=2, "bones"=1)),
	list("id"="regalia.staff", "name"="Elder's Staff", "slot"="regalia", "group"="leather", "tier"="leather", "station"="leather", "craft"="LeatherCraftingSkill", "craft_level"=5, "types"=list(/obj/Items/Equipment/Armour/Crown/RmStaff), "recipe"=list("wood"=2, "skin"=1)),
	list("id"="regalia.chain", "name"="Chain of Office", "slot"="regalia", "group"="iron", "tier"="iron", "station"="forge", "craft"="MetalCraftingSkill", "craft_level"=10, "types"=list(/obj/Items/Equipment/Armour/Crown/RmChain), "recipe"=list("iron ingot"=3)),
	list("id"="regalia.silver circlet", "name"="Silver Circlet", "slot"="regalia", "group"="silver", "tier"="silver", "station"="forge", "craft"="MetalCraftingSkill", "craft_level"=25, "types"=list(/obj/Items/Equipment/Armour/Crown/RmSilverCirclet), "recipe"=list("silver ingot"=2, "cut emerald"=1)),
	list("id"="regalia.gold crown", "name"="Gold Crown", "slot"="regalia", "group"="gold", "tier"="gold", "station"="forge", "craft"="MetalCraftingSkill", "craft_level"=35, "types"=list(/obj/Items/Equipment/Armour/Crown/Gold), "recipe"=list("gold ingot"=3, "cut ruby"=1)),
	list("id"="regalia.heir circlet", "name"="Heir's Circlet", "slot"="regalia", "group"="silver", "tier"="silver", "station"="forge", "craft"="MetalCraftingSkill", "craft_level"=20, "types"=list(/obj/Items/Equipment/Armour/Crown/RmHeirCirclet), "recipe"=list("silver ingot"=1)),
	list("id"="regalia.heir band", "name"="Heir's Band", "slot"="regalia", "group"="bone", "tier"="bone", "station"="bone", "craft"="BoneCraftingSkill", "craft_level"=3, "types"=list(/obj/Items/Equipment/Armour/Crown/RmHeirBand), "recipe"=list("bones"=1, "skin"=1)))

var/rm_regalia_gear = 0
proc/RmRegaliaGear()
	if(rm_regalia_gear || !length(rm_gear_defs)) return
	rm_regalia_gear = 1
	rm_gear_slots["regalia"] = "Regalia"
	for(var/list/G in rm_regalia_defs)
		var/list/L = RmGearDefsAt(G["station"])
		L += list(G)

// world/New: this file's part is step RmChainWorldNew_Rulership in Code/Remastered/Chains/WorldNew.dm

// --- small helpers ----------------------------------------------------------------------------------------------
proc/RmName(obj/I)   // an item's name without its quality ("Heir's Circlet - Quality")
	var/n = "[I ? I.name : ""]"
	var/i = findtext(n, " - ")
	return i ? copytext(n, 1, i) : n

proc/RmAn(t)   // "an Elder's Staff", "a Chief's Totem"
	t = "[t]"
	return "[findtext("AEIOU", copytext(t, 1, 2)) ? "an" : "a"] [t]"

proc/RmHolder(obj/I)
	return (I && istype(I.loc, /mob/Monsters)) ? I.loc : null

proc/RmItemUid(obj/Items/Equipment/Armour/Crown/C)
	if(!C.rm_item_uid) C.rm_item_uid = RemasterNewUID()
	return C.rm_item_uid

proc/RmItemByUid(uid)
	if(uid) for(var/obj/Items/Equipment/Armour/Crown/C in rm_regalia) if(C.rm_item_uid == uid && C.loc) return C
	return null

// Where an item is, as the realm P sees it.
proc/RmWhere(obj/I, Player/P)
	var/mob/Monsters/H = RmHolder(I)
	if(H)
		var/how = I.suffix == "(Equipped)" ? "worn" : "carried"
		if(H.Owner == P) return "[how] by [H.RemasterBareName()]"
		var/Player/O = H.Owner
		return "[how] by [istype(O) ? "House [O.RemasterHouse()]'s " : ""][H.RemasterBareName()]"
	var/turf/T = RemasterGetTurf(I)
	return T ? "lies at [T.x], [T.y]" : "lost"

proc/RmTitleForm(t, gender)
	var/i = findtext("[t]", "/")
	if(!i) return "[t]"
	return gender == "Female" ? copytext(t, i + 1) : copytext(t, 1, i)

proc/RmTitleList(race, stage)
	var/list/R = rm_titles[race] || rm_titles["Human"]
	return R[clamp(stage, 1, length(R))]

// "Lord or Lady" for the stage's first title.
proc/RmStageTitleText(race, stage)
	var/list/L = RmTitleList(race, stage)
	return replacetext("[L[1]]", "/", " or ")

proc/RmStageName(stage)
	return rm_ranks[clamp(stage, 1, length(rm_ranks))]["name"]

proc/RmTell(Player/P, text, kind = "info")
	if(!istype(P)) return
	P.RemasterNotice(text)
	P.RemasterLog(text, kind, null)
	P << "<b><font color=#f2d27a>[text]</font></b>"

// A question with a list of answers (the HUD's ask card). With no one there to answer (away, or a test), the first
// answer: the default.
Player/proc/RmAsk(message, title, list/options)
	if(!client || !remaster_hud_ready) return options[1]
	return RemasterChoose(src, message, title, options)

// --- a unit and its seat ----------------------------------------------------------------------------------------
// The best regalia this unit wears (or holds at all).
mob/Monsters/proc/RmRegalia(worn_only = 1)
	var/obj/Items/Equipment/Armour/Crown/best
	for(var/obj/Items/Equipment/Armour/Crown/C in src) if(C.rm_tier && (!worn_only || C.suffix == "(Equipped)") && (!best || C.rm_tier > best.rm_tier)) best = C
	return best

mob/Monsters/proc/RmRegaliaTier()
	var/obj/Items/Equipment/Armour/Crown/C = RmRegalia()
	return C ? C.rm_tier : 0

// The stage this ruler's seat reaches: the settlement's, as far as the regalia they wear goes (0 without any).
mob/Monsters/proc/RmSeatTier()
	var/Player/P = Owner
	var/t = RmRegaliaTier()
	if(!t || !istype(P)) return 0
	return clamp(min(t, P.remaster_rank), 1, length(rm_seat_health))

mob/Monsters/proc/RmGrown()
	return !Critter && !Egg && Age >= RM_GROWN && !rm_cap_state

// The seat's health: kept in line with the regalia worn and the stage, for a ruler crowned under these rules. One
// crowned before keeps what they were given (old saves); stepping down takes it off (RemasterCrownHealth).
mob/Monsters/proc/RmSeatHealthSync()
	if(!rm_seat_v) return
	var/s = IsRoyal ? RmSeatTier() : 0
	var/want = s ? rm_seat_health[s] : 0
	var/d = want - rm_crown_health
	if(!d) return
	rm_crown_health = want
	MAXHP += d
	if(d > 0) HP += d
	else if(HP > 0) HP = max(1, HP + d)
	HP = min(HP, MAXHP)

// Putting regalia on or taking it off moves the health at once.
mob/Monsters/ForceEquipItem(obj/Items/ITEM)
	. = ..()
	if(IsRoyal && istype(ITEM, /obj/Items/Equipment/Armour/Crown)) RmSeatHealthSync()
mob/Monsters/ForceUnEquipItem(obj/Items/ITEM)
	. = ..()
	if(IsRoyal && istype(ITEM, /obj/Items/Equipment/Armour/Crown)) RmSeatHealthSync()

// The title on a ruler's name ("[Title] {House} Name").
mob/Monsters/proc/RmTitle()
	if(rm_title) return rm_title
	if(!IsRoyal) return null
	var/n = "[name]"
	var/i = findtext(n, " {")
	if(i > 1) return copytext(n, 1, i)
	return GenderToLeader(Gender)

mob/proc/RmTitleOf()
	return GenderToLeader(Gender)
mob/Monsters/RmTitleOf()
	return RmTitle() || GenderToLeader(Gender)

// A ruler crowned before these rules: their title as their name has it. The old Town rank-up wrote "{House} Lord
// Grak", which put the title in the bare name; it goes back in front.
mob/Monsters/proc/RmLegacyTitle()
	var/n = "[name]"
	var/i = findtext(n, " {")
	if(i > 1)
		rm_title = copytext(n, 1, i)
		return
	var/j = findtext(n, "} ")
	if(copytext(n, 1, 2) == "{" && j)
		var/rest = copytext(n, j + 2)
		for(var/t in list("King", "Queen", "Lord", "Lady")) if(findtextEx(rest, "[t] ") == 1)
			rm_title = t
			name = "[t] [copytext(n, 1, j + 2)][copytext(rest, length(t) + 2)]"
			return
	rm_title = GenderToLeader(Gender)

mob/Monsters/proc/RmHeirWord()
	return RmTitleForm(rm_heir_words[Race] || "Heir", Gender)

mob/Monsters/proc/RmTitleRace()
	return rm_titles[Race] ? Race : "Human"

// label -> title entry for a stage, the house's last title first.
mob/Monsters/proc/RmTitleChoices(Player/P, stage)
	var/list/E = RmTitleList(RmTitleRace(), stage).Copy()
	var/kept = (P && remaster_house && P.rm_house_titles) ? P.rm_house_titles[remaster_house] : null
	if(kept && (kept in E))
		E -= kept
		E.Insert(1, kept)
	. = list()
	for(var/e in E) .[RmTitleForm(e, Gender)] = e

// The title the succession banner offers an heir: the house's last one, if the stage has it, else the stage's first.
mob/Monsters/proc/RmOfferTitle(Player/P)
	var/list/C = RmTitleChoices(P, clamp(P.remaster_rank, 1, length(rm_seat_items)))
	return length(C) ? C[1] : GenderToLeader(Gender)

mob/Monsters/proc/RmSetTitle(Player/P, title, entry)
	var/bare = RemasterBareName()
	rm_title = title
	RemasterSetName(bare)
	if(P && remaster_house && entry)
		if(!P.rm_house_titles) P.rm_house_titles = list()
		P.rm_house_titles[remaster_house] = entry

// The settlement rose a stage and the ruler's regalia reaches it: keep the title, or take one of the new stage's.
mob/Monsters/proc/RmRetitle(Player/P, stage)
	rm_title_asking = 1
	var/list/C = RmTitleChoices(P, stage)
	var/now = RmTitle()
	var/keep = "Keep [now]"
	var/list/labels = list(keep)
	for(var/l in C) if(l != now) labels += l
	var/a = P.RmAsk("Your settlement is now a [RmStageName(stage)]. What will [RemasterBareName()] be called?", "Title", labels)
	rm_title_asking = 0
	if(!IsRoyal || HP <= 0 || Owner != P) return
	rm_title_stage = max(rm_title_stage, stage)
	if(!a || a == keep || !C[a]) return
	RmSetTitle(P, a, C[a])
	P.RemasterLog("[RemasterBareName()] now rules as [a]", "good", src)

// --- crowning (AddLeader, Crowning.dm) ----------------------------------------------------------------------------
// What crowns this unit: the regalia being put on, else the best one it holds. Null (and the player told why) when
// it holds none good enough for the settlement's stage, or another realm's claim holds the seat.
mob/proc/RmCrowningRegalia(obj/Items/Equipment/CROWN)
	return CROWN || 1
mob/Monsters/RmCrowningRegalia(obj/Items/Equipment/CROWN)
	var/Player/P = istype(Owner, /Player) ? Owner : null
	if(!P) return ..()
	var/why = P.RmClaimBlocks()
	if(why)
		RmTell(P, why, "fight")
		return null
	var/stage = clamp(P.remaster_rank, 1, length(rm_seat_items))
	var/obj/Items/Equipment/Armour/Crown/C = (istype(CROWN, /obj/Items/Equipment/Armour/Crown) && CROWN:rm_tier) ? CROWN : RmRegalia(0)
	if(!C || C.rm_tier < stage)
		var/had = C ? " The [RmName(C)] is for [RmAn(lowertext(RmStageName(C.rm_tier)))]." : ""
		var/text = "To rule your [lowertext(RmStageName(stage))], [RemasterBareName()] must hold [RmAn(rm_seat_items[stage])][stage < length(rm_seat_items) ? " or better" : ""] (made [rm_seat_made[stage]]).[had]"
		P.RemasterNotice(text)
		P << text
		return null
	return C

// The law of succession (the realm's first crowning) and the title. list("title", "entry", "law"), or null when the
// player cancelled.
mob/proc/RmCrowningAsks()
	return list("title"=GenderToLeader(Gender))
mob/Monsters/RmCrowningAsks()
	var/Player/P = istype(Owner, /Player) ? Owner : null
	if(!P) return ..()
	var/law
	if(!P.rm_law)
		var/def = P.RmLawDefault()
		var/list/labels = list("[rm_laws[def][1]] (your people's way)"=def)
		for(var/id in rm_laws) if(id != def) labels["[rm_laws[id][1]]"] = id
		var/list/lines = list()
		for(var/id in rm_laws) lines += "[rm_laws[id][1]]: [rm_laws[id][2]]"
		var/a = P.RmAsk("Your realm's first ruler: which law of succession will it keep? Whoever of the realm holds the heir's circlet inherits first under every law. [jointext(lines, " ")] (It can be changed later in the Realm tab[rm_moods_on ? ", which unsettles the people" : ""].)", "Law of succession", labels + "Cancel")
		if(!a || !labels[a]) return null
		law = labels[a]
	var/stage = clamp(P.remaster_rank, 1, length(rm_seat_items))
	var/list/C = RmTitleChoices(P, stage)
	var/list/labels = list()
	for(var/l in C) labels += l
	var/t = P.RmAsk("What will [RemasterBareName()] be called as ruler of your [lowertext(RmStageName(stage))]?", "Title", labels + "Cancel")
	if(!t || !C[t]) return null
	return list("title"=t, "entry"=C[t], "law"=law)

// The regalia goes on (in the crown's place) before the seat's health is worked out.
mob/proc/RmWearRegalia(obj/Items/Equipment/CROWN)
	return
mob/Monsters/RmWearRegalia(obj/Items/Equipment/Armour/Crown/C)
	if(!istype(C) || C.loc != src || C.suffix == "(Equipped)") return
	for(var/obj/Items/Equipment/Armour/Crown/W in src) if(W.suffix == "(Equipped)") ForceUnEquipItem(W)
	ForceEquipItem(C)

mob/proc/RmCrowned(obj/Items/Equipment/CROWN, list/ASK)
	name = "[ASK["title"]] [name]"
mob/Monsters/RmCrowned(obj/Items/Equipment/Armour/Crown/C, list/ASK)
	var/Player/P = istype(Owner, /Player) ? Owner : null
	rm_title = ASK["title"]
	rm_title_stage = RmSeatTier()
	name = "[rm_title] [name]"
	if(!P) return
	if(ASK["law"] && !P.rm_law) P.rm_law = ASK["law"]
	if(ASK["entry"] && remaster_house)
		if(!P.rm_house_titles) P.rm_house_titles = list()
		P.rm_house_titles[remaster_house] = ASK["entry"]
	if(istype(C) && !C.rm_realm)
		C.rm_realm = P.key
		C.rm_realm_house = P.RemasterHouse()
		RmItemUid(C)
	P.rm_seat_vacant = 0
	P.rm_claim = null
	P.RemasterLog("[RemasterBareName()] was crowned [rm_title][istype(C) ? " with the [RmName(C)]" : ""]", "good", src)

mob/proc/RmSteppedDown()
	return
mob/Monsters/RmSteppedDown()
	rm_title = null
	rm_title_stage = 0
	if(istype(Owner, /Player)) Owner:RmSeatCheck(src)

// The crown's place (EquipItem, Item Procs.dm). Any other mob as before. On a unit: an heir's item goes on like a hat
// (and becomes the realm's); regalia on a ruler swaps for what they wear; on anyone else it's a crowning, and
// AddLeader puts it on.
mob/proc/RmEquipCrownSlot(obj/Items/ITEM)
	if(!WearingCrown && AddLeader(ITEM)) return ForceEquipItem(ITEM)
mob/Monsters/RmEquipCrownSlot(obj/Items/Equipment/Armour/Crown/C)
	if(!istype(C) || (!C.rm_heir_item && !C.rm_tier)) return ..()
	var/Player/P = istype(Owner, /Player) ? Owner : null
	if(C.rm_heir_item)
		if(P && !P.RmBindHeirItem(C, src)) return null
		RmSwapCrownPlace(C)
		return C
	if(IsRoyal)
		RmSwapCrownPlace(C)
		if(P && !C.rm_realm)
			C.rm_realm = P.key
			C.rm_realm_house = P.RemasterHouse()
			RmItemUid(C)
		return C
	if(!AddLeader(C)) return null
	if(C.loc == src && C.suffix != "(Equipped)") RmSwapCrownPlace(C)
	return C

mob/Monsters/proc/RmSwapCrownPlace(obj/Items/Equipment/Armour/Crown/C)
	for(var/obj/Items/Equipment/Armour/Crown/W in src) if(W != C && W.suffix == "(Equipped)") ForceUnEquipItem(W)
	if(C.suffix != "(Equipped)") ForceEquipItem(C)

// --- the heir's item ----------------------------------------------------------------------------------------------
// This realm's heir's item, wherever it is.
Player/proc/RmHeirItem()
	for(var/obj/Items/Equipment/Armour/Crown/C in rm_regalia) if(C.rm_heir_item && C.rm_realm == key && C.loc) return C
	return null

// An heir's item becomes the realm's when one of its people first puts it on. A realm has one: while its own is
// still in the world (even held by an enemy), another can't take its place.
Player/proc/RmBindHeirItem(obj/Items/Equipment/Armour/Crown/C, mob/Monsters/M)
	if(C.rm_realm) return 1
	var/obj/Items/Equipment/Armour/Crown/O = RmHeirItem()
	if(O && O != C)
		var/t = "House [RemasterHouse()]'s [RmName(O)] is still out there ([RmWhere(O, src)]): a realm has one heir's item at a time."
		RemasterNotice(t)
		src << t
		return 0
	C.rm_realm = key
	C.rm_realm_house = RemasterHouse()
	RmItemUid(C)
	RemasterNotice("[M.RemasterBareName()] puts on the [RmName(C)]: whoever of House [RemasterHouse()] holds it is the heir.")
	RemasterLog("[M.RemasterBareName()] put on the [RmName(C)]", "good", M)
	return 1

// What the succession follows, first first: under the Regalia law the realm's regalia (the best first, not counting
// what a living ruler of it wears), then its heir's item.
Player/proc/RmClaimItems()
	. = list()
	if(RmLaw() == "regalia")
		var/list/R = list()
		for(var/obj/Items/Equipment/Armour/Crown/C in rm_regalia) if(C.rm_tier && C.rm_realm == key && C.loc)
			var/mob/Monsters/H = RmHolder(C)
			if(H && H.IsRoyal && H.Owner == src && H.HP > 0) continue
			var/at = 1
			for(var/obj/Items/Equipment/Armour/Crown/B in R)
				if(B.rm_tier < C.rm_tier) break
				at++
			R.Insert(at, C)
		. += R
	var/obj/I = RmHeirItem()
	if(I) . += I

// The heir by the items: one of the realm's own, grown and free, holding what the succession follows. list(unit, why).
Player/proc/RmItemHeir(list/living)
	for(var/obj/Items/Equipment/Armour/Crown/C in RmClaimItems())
		var/mob/Monsters/H = RmHolder(C)
		if(H && (H in living) && H.RmGrown()) return list(H, "holds the [RmName(C)]")
	return null

// --- the laws -----------------------------------------------------------------------------------------------------
Player/proc/RmLaw()
	return rm_law || RmLawDefault()

Player/proc/RmLawDefault()
	var/mob/Monsters/H = RemasterHero()
	return (H && rm_law_by_race[H.Race]) || "bloodline"

proc/RmMight(mob/Monsters/M)
	return RemasterCombatLevel(M, "Attack") + RemasterCombatLevel(M, "Strength") + RemasterCombatLevel(M, "Defence")

// How well the people like M: their mood, their family among the living, their level.
proc/RmLiking(mob/Monsters/M, list/living)
	var/kin = 0
	for(var/mob/Monsters/O in living) if(O != M && O.remaster_uid && M.remaster_uid)
		if(O.remaster_father == M.remaster_uid || O.remaster_mother == M.remaster_uid || M.remaster_father == O.remaster_uid || M.remaster_mother == O.remaster_uid) kin++
		else if((M.remaster_father && O.remaster_father == M.remaster_father) || (M.remaster_mother && O.remaster_mother == M.remaster_mother)) kin++
		else if(islist(M.remaster_partners) && (O.remaster_uid in M.remaster_partners)) kin++
	return M.remaster_mood + 6 * kin + M.Level

// The heir by the realm's law, when no one of the realm holds its items. list(unit, why).
Player/proc/RmLawHeir(mob/Monsters/R, list/living)
	var/law = RmLaw()
	var/list/house = list()
	if(R && R.remaster_house) for(var/mob/Monsters/M in living) if(M.remaster_house == R.remaster_house) house += M
	switch(law)
		if("might", "council")
			var/list/pool = list()
			for(var/mob/Monsters/M in house) if(M.RmGrown()) pool += M
			if(!length(pool)) for(var/mob/Monsters/M in living) if(M.RmGrown()) pool += M
			var/mob/Monsters/best
			var/bv = 0
			for(var/mob/Monsters/M in pool)
				var/v = law == "might" ? RmMight(M) : RmLiking(M, living)
				if(!best || v > bv || (v == bv && M.Age > best.Age))
					best = M
					bv = v
			if(best) return list(best, law == "might" ? "by Might: the strongest" : "by Council: the people's choice")
		if("chosen", "regalia")
			if(remaster_heir_uid) for(var/mob/Monsters/M in living) if(M.remaster_uid == remaster_heir_uid) return list(M, "named heir")
			if(length(house)) return list(RemasterEldest(house), "eldest of the house")
			return list(RemasterEldest(living), "chosen by the village")
	return RmBloodlineHeir(R, living)

// --- the seat falls empty, and claims ------------------------------------------------------------------------------
// When its last ruler dies or steps down (RemasterSuccession, RmSteppedDown).
Player/proc/RmSeatCheck(mob/Monsters/gone)
	for(var/mob/Monsters/M in UnitList) if(M != gone && M.Owner == src && M.HP > 0 && !M.GoingToDie && M.IsRoyal) return
	rm_seat_vacant = 1
	RmClaimScan(gone)

// While the seat is empty: if what the succession follows first is held by another realm's unit (grown, free, not
// of this realm's own members or vassals), that unit's player has a claim on the seat.
Player/proc/RmClaimScan(mob/Monsters/gone)
	if(rm_claim || !rm_seat_vacant) return
	for(var/obj/Items/Equipment/Armour/Crown/C in RmClaimItems())
		var/mob/Monsters/H = RmHolder(C)
		if(!H || H == gone || H.HP <= 0) continue
		if(H.Owner == src) return
		var/Player/E = H.Owner
		if(!istype(E) || RemasterAllied(E, src) || !H.RmGrown()) continue
		if(!H.remaster_uid) H.RemasterLineageEnsure(E)
		rm_claim = list("by"=E.key, "house"=E.RemasterHouse(), "holder"=H.remaster_uid, "holderName"=H.RemasterBareName(), "item"=RmName(C), "uid"=RmItemUid(C), "state"="open")
		rm_claim_until = world.time + RM_CLAIM_WINDOW
		RmTell(src, "[H.RemasterBareName()] of House [E.RemasterHouse()] holds your [RmName(C)] and claims your seat. No one can be crowned until it's settled: take it back, or answer in the Realm tab.", "fight")
		RmTell(E, "[RemasterRealmName()] has lost its ruler, and [H.RemasterBareName()] holds its [RmName(C)]: you have a claim on its seat. Press it in the Realm tab within [round(RM_CLAIM_WINDOW / 600)] minutes.", "good")
		return

// The claim on this realm, if it still stands. It is void when the realm has its item back, and lapses when the
// claimant's realm no longer holds it, or the claim wasn't pressed in time (the item is then spent).
Player/proc/RmClaimTick()
	if(!rm_claim)
		if(rm_seat_vacant) RmClaimScan()
		return
	var/obj/Items/Equipment/Armour/Crown/C = RmItemByUid(rm_claim["uid"])
	var/mob/Monsters/H = RmHolder(C)
	var/what = lowertext(rm_claim["item"])
	if(!C) return RmClaimEnd("Your [what] is gone: House [rm_claim["house"]]'s claim on your seat has lapsed.", "The [what] is gone: your claim on [RemasterRealmName()]'s seat has lapsed.", 0)
	if(H && H.Owner == src) return RmClaimEnd("[H.RemasterBareName()] has your [what] back: House [rm_claim["house"]]'s claim is void. You may crown a ruler.", "[RemasterRealmName()] took back its [what]: your claim is void.", 0)
	var/Player/E = RemasterPlayerByKey(rm_claim["by"])
	if(!E || !H || H.HP <= 0 || !istype(H.Owner, /Player) || !RemasterAllied(H.Owner, E))
		return RmClaimEnd("House [rm_claim["house"]] no longer holds your [what]: its claim on your seat has lapsed[C && !H ? " (the [what] [RmWhere(C, src)])" : ""].", "Your people no longer hold [RemasterRealmName()]'s [what]: the claim has lapsed.", 0)
	if(rm_claim["state"] == "open")
		if(!rm_claim_until) rm_claim_until = world.time + RM_CLAIM_WINDOW   // read back from a save
		if(world.time > rm_claim_until) return RmClaimEnd("House [rm_claim["house"]] never pressed its claim on your seat: it has lapsed, and your [what] is only a trophy now.", "You didn't press your claim on [RemasterRealmName()]'s seat in time: it has lapsed.", 1)

Player/proc/RmClaimEnd(mine, theirs, spend)
	if(!rm_claim) return
	var/Player/E = RemasterPlayerByKey(rm_claim["by"])
	if(spend)
		var/obj/Items/Equipment/Armour/Crown/C = RmItemByUid(rm_claim["uid"])
		if(C) C.rm_realm = null
	rm_claim = null
	if(mine) RmTell(src, mine, "good")
	if(theirs && E) RmTell(E, theirs, "work")

// Why no one can be crowned now (null when someone may).
Player/proc/RmClaimBlocks()
	RmClaimTick()
	if(!rm_claim) return null
	return "[rm_claim["holderName"]] of House [rm_claim["house"]] holds your [rm_claim["item"]] and claims your seat. No one can be crowned until it's settled: take the [lowertext(rm_claim["item"])] back, or answer the claim in the Realm tab."

Player/proc/RmClaimText()
	if(!rm_claim) return null
	return "[rm_claim["holderName"]] of House [rm_claim["house"]] holds your [rm_claim["item"]] and claims your seat."

// A refused claim, and the claimant takes the realm's last banner (RemasterSiegeTake, War.dm): the fallen realm swears
// fealty to the claimant's. 1 when it did.
proc/RmClaimFall(Player/W, loser_key, wk)
	for(var/Player/V in world) if(V.rm_claim && V.rm_claim["state"] == "refused" && RemasterAlliedKeys(V.key, loser_key) && RemasterAlliedKeys(V.rm_claim["by"], W.key))
		var/item = lowertext(V.rm_claim["item"])
		var/liege = RemasterRootKey(W.key)
		if(liege == V.key) return 0
		RemasterRealmNotice(W.key, "[V.RemasterRealmName()] has fallen and swears fealty to your realm: your claim on its seat is won.", "good")
		RemasterRealmNotice(V.key, "Your realm has fallen: by House [V.rm_claim["house"]]'s claim, with your [item], you swear fealty to [RemasterRulerName(W.key)].")
		var/obj/Items/Equipment/Armour/Crown/C = RmItemByUid(V.rm_claim["uid"])
		if(C) C.rm_realm = null
		V.rm_claim = null
		RmEndWar(wk)
		V.RemasterSetLiege(liege)
		return 1
	return 0

// Peace sworn between two realms (RemasterMakePeace, War.dm): a claim either holds on the other is dropped, and its
// item is spent.
proc/RmClaimPeace(wk)
	for(var/Player/V in world) if(V.rm_claim && RemasterWarKey(V.key, V.rm_claim["by"]) == wk)
		V.RmClaimEnd("Peace is sworn: House [V.rm_claim["house"]]'s claim on your seat is dropped. You may crown a ruler.", "Peace is sworn: your claim on [V.RemasterRealmName()]'s seat is dropped.", 1)

// A war ended by a claim (yielded, or won): a truce, as RemasterMakePeace makes, without its notices.
proc/RmEndWar(wk)
	var/list/W = wk ? rm_wars[wk] : null
	if(!W || W[1] == "truce") return
	rm_wars[wk] = list("truce", rm_war_now + RM_WAR_TRUCE, null, W[4], W[5], null)
	rm_realm_ver++
	for(var/obj/RemasterBanner/B in rm_banners) if(B.owner_key && RemasterWarKey(B.owner_key, B.siege_by) == wk)
		B.siege = 0
		B.siege_by = null

// The Realm page: "law|id", "claim|key" (press our claim on that realm), "yield|key" and "refuse|key" (our answer to
// the claim by that player).
Player/proc/RmRuleCommand(act, k)
	switch(act)
		if("law")
			if(!rm_laws[k] || RmLaw() == k && rm_law) return 0
			var/first = !rm_law
			rm_law = k
			if(first)
				RemasterNotice("Your realm keeps the law of [rm_laws[k][1]].")
				return 1
			RemasterCheer("law", "The law of succession was changed", RM_LAW_MOOD, RM_LAW_DAYS)
			RmTell(src, "Your realm now keeps the law of [rm_laws[k][1]].[rm_moods_on ? " The change unsettles your people: mood [RM_LAW_MOOD] for a week." : ""]", "work")   // no mood while moods are off
			return 1
		if("claim")
			var/Player/V = RemasterPlayerByKey(k)
			if(!V || !V.rm_claim || V.rm_claim["by"] != key) return 0
			V.RmClaimTick()
			if(!V.rm_claim || V.rm_claim["state"] != "open") return 0
			V.rm_claim["state"] = "pressed"
			RmTell(V, "House [RemasterHouse()] presses its claim on your seat ([V.rm_claim["holderName"]] holds your [V.rm_claim["item"]]). Yield and swear fealty to [RemasterRealmName()], or refuse, and it's war: answer in the Realm tab.", "fight")
			RmTell(src, "You pressed your claim on [V.RemasterRealmName()]'s seat. Waiting for their answer.", "good")
			return 1
		if("yield", "refuse")
			if(!rm_claim || rm_claim["by"] != k) return 0
			RmClaimTick()
			if(!rm_claim || rm_claim["state"] == "open") return 0
			var/Player/E = RemasterPlayerByKey(k)
			var/wk = RemasterWarKey(key, k)
			var/item = lowertext(rm_claim["item"])
			if(act == "refuse")
				if(rm_claim["state"] != "pressed" || !wk) return 0
				rm_claim["state"] = "refused"
				var/list/W = rm_wars[wk]
				if(!W || W[1] != "war")
					rm_wars[wk] = list("war", rm_war_now, key, (W ? W[4] : 0), (W ? W[5] : 0), null)
					rm_realm_ver++
				RemasterRealmNotice(key, "You refused House [rm_claim["house"]]'s claim: it's war, now. Take your [item] back, or hold out until peace.")
				RemasterRealmNotice(k, "[RemasterRealmName()] refused your claim: it's war, now. Take its last banner and its realm falls to you.")
				RemasterRealmCheer(key, "war", "Our realm is at war", -5, 1)
				return 1
			var/liege = RemasterRootKey(k)
			if(!liege || RemasterRootKey(liege) == key) return 0
			RemasterRealmNotice(key, "You yielded to House [rm_claim["house"]]'s claim: your realm swears fealty to [RemasterRulerName(k)].", "work")
			RemasterRealmNotice(k, "[RemasterRealmName()] yielded to your claim and swears fealty to your realm.", "good")
			RemasterCheer("yield", "Our realm bent the knee", -8, 2)
			if(E) E.RemasterCheer("claimwon", "We won a realm by right of claim", 6, 2)
			var/obj/Items/Equipment/Armour/Crown/C = RmItemByUid(rm_claim["uid"])
			if(C) C.rm_realm = null
			rm_claim = null
			RmEndWar(wk)
			RemasterSetLiege(liege)
			return 1
	return 0

// Captured: the captor takes an heir's item and any regalia along with the weapons (RmCapDisarm, Captives.dm).
mob/Monsters/RmCapDisarm(mob/Monsters/C)
	var/said = ..()
	var/list/took = list()
	for(var/obj/Items/Equipment/Armour/Crown/R in src) if(R.rm_heir_item || R.rm_tier)
		if(R.suffix == "(Equipped)") ForceUnEquipItem(R)
		weight -= R.weight
		R.suffix = null
		R.loc = loc
		if(C && C.PickUpItem(R, 0, 2)) took += RmName(R)
	if(length(took)) said = length(said) ? "[said], and their [jointext(took, ", ")]" : " and takes their [jointext(took, ", ")]"
	return said

// --- the stage rises (RemasterRankUp, Progress.dm), and the rulership tick ----------------------------------------
Player/proc/RmSeatRankUp()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0 && M.IsRoyal)
		M.RmSeatHealthSync()   // the regalia worn may reach further now
		var/t = RmSeatNeed(M)
		if(t) RmTell(src, t, "work")

// What a ruler needs for the settlement's stage ("" when they have it).
Player/proc/RmSeatNeed(mob/Monsters/M)
	if(!M || !M.IsRoyal) return ""
	var/stage = clamp(remaster_rank, 1, length(rm_seat_items))
	if(!M.rm_seat_v) return M.RmRegaliaTier() >= stage ? "" : "Crowned before regalia: [M.RemasterBareName()] keeps the seat and what the crowning gave. Rulers crowned from now on need the [rm_seat_items[stage]]."
	var/obj/Items/Equipment/Armour/Crown/C = M.RmRegalia()
	if(C && C.rm_tier >= stage) return ""
	var/s = M.RmSeatTier()
	return "Your [lowertext(RmStageName(stage))] needs [RmAn(RmStageTitleText(M.RmTitleRace(), stage))]: make [RmAn(rm_seat_items[stage])] ([rm_seat_made[stage]]) for [M.RemasterBareName()] to wear.[s ? " Until then the seat stays a [lowertext(RmStageName(s))]'s, at +[rm_seat_health[s]] health." : " Without regalia worn, the seat gives no health."]"

proc/RmRulershipLoop()
	RmRegaliaGear()
	while(1)
		sleep(20)
		for(var/Player/P in world) P.RmRulershipTick()

Player/proc/RmRulershipTick()
	RmClaimTick()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.IsRoyal && M.HP > 0)
		if(!M.rm_title) M.RmLegacyTitle()
		M.RmSeatHealthSync()
		if(M.rm_seat_v && !M.rm_title_asking && client && remaster_hud_ready && M.RmSeatTier() > M.rm_title_stage)
			M.rm_title_asking = 1
			spawn(0) M.RmRetitle(src, M.RmSeatTier())

// --- HUD data -----------------------------------------------------------------------------------------------------
// The unit card's Family tab: the seat, the heir, what crowning would need, another realm's items held.
mob/Monsters/RemasterFamilyData(Player/P)
	var/list/D = ..()
	if(Critter || !istype(P) || !islist(D)) return D
	var/list/K = D["kin"]
	if(islist(K) && (P.RmLaw() in list("might", "council"))) K["canHeir"] = 0   // the law, not the ruler, picks
	var/list/R = list()
	if(IsRoyal)
		var/obj/Items/Equipment/Armour/Crown/C = RmRegalia()
		R["seat"] = list("title"=RmTitle(), "regalia"=(C ? RmName(C) : null), "health"=rm_crown_health, "legacy"=!rm_seat_v, "need"=P.RmSeatNeed(src))
	else if(Owner == P)
		var/mob/Monsters/head = P.RemasterHero()
		var/list/H = head ? P.RemasterHeirOf(head) : null
		if(H && H[1] == src) R["heir"] = list("word"=RmHeirWord(), "why"=H[2])
		var/stage = clamp(P.remaster_rank, 1, length(rm_seat_items))
		var/obj/Items/Equipment/Armour/Crown/G = RmRegalia(0)
		if(!rm_cap_state) R["canRule"] = (G && G.rm_tier >= stage) ? "Can be crowned: holds the [RmName(G)] (Declare Leader)." : "To be crowned, needs [RmAn(rm_seat_items[stage])][stage < length(rm_seat_items) ? " or better" : ""] (made [rm_seat_made[stage]])."
	var/list/held = list()
	for(var/obj/Items/Equipment/Armour/Crown/C in src) if(C.rm_realm && (C.rm_heir_item || C.rm_tier))
		if(C.rm_realm == P.key)
			if(C.rm_heir_item && IsRoyal) held += list(list("text"="Holds your [RmName(C)]: give it to your heir (drag it onto them)."))
			continue
		var/Player/O = RemasterPlayerByKey(C.rm_realm)
		var/claim = (O && O.rm_claim && O.rm_claim["uid"] == C.rm_item_uid) ? "a claim on its seat: press it in the Realm tab" : "a claim on its seat if it falls empty"
		held += list(list("text"="Holds House [C.rm_realm_house]'s [RmName(C)]: [claim]."))
	R["held"] = held
	D["rule"] = R
	return D

// The Realm page's Rule box.
Player/RemasterRealmData()
	var/list/D = ..()
	if(islist(D)) D["rule"] = RmRuleData()
	return D

Player/proc/RmRuleData()
	var/stage = clamp(remaster_rank, 1, length(rm_seat_items))
	var/list/rulers = list()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0 && M.IsRoyal)
		var/obj/Items/Equipment/Armour/Crown/C = M.RmRegalia()
		rulers += list(list("name"=M.RemasterBareName(), "title"=M.RmTitle(), "ref"=RemasterUIRef(M), "regalia"=(C ? RmName(C) : null), "health"=M.rm_crown_health, "legacy"=!M.rm_seat_v, "need"=RmSeatNeed(M)))
	var/mob/Monsters/head = RemasterHero()
	var/list/H = head ? RemasterHeirOf(head) : null
	var/mob/Monsters/heir = H ? H[1] : null
	var/obj/Items/Equipment/Armour/Crown/I = RmHeirItem()
	var/mob/Monsters/IH = RmHolder(I)
	var/list/laws = list()
	for(var/id in rm_laws) laws += list(list("id"=id, "name"=rm_laws[id][1], "tip"=rm_laws[id][2]))
	var/list/on
	if(rm_claim)
		on = rm_claim.Copy()
		on["mins"] = rm_claim["state"] == "open" ? max(1, round((rm_claim_until - world.time) / 600) + 1) : null
	var/list/mine = list()
	for(var/Player/V in world) if(V != src && V.rm_claim && V.rm_claim["by"] == key)
		mine += list(list("key"=V.key, "realm"=V.RemasterRealmName(), "holder"=V.rm_claim["holderName"], "item"=V.rm_claim["item"], "state"=V.rm_claim["state"],
			"mins"=(V.rm_claim["state"] == "open" ? max(1, round((V.rm_claim_until - world.time) / 600) + 1) : null)))
	return list("stage"=RmStageName(stage), "item"=rm_seat_items[stage], "made"=rm_seat_made[stage], "health"=rm_seat_health[stage],
		"rulers"=rulers, "vacant"=rm_seat_vacant, "law"=RmLaw(), "lawSet"=!!rm_law, "laws"=laws, "lawMood"=(rm_moods_on ? RM_LAW_MOOD : null),
		"heir"=(heir ? heir.RemasterBareName() : null), "heirWord"=(heir ? heir.RmHeirWord() : null), "heirWhy"=(H ? H[2] : null),
		"heirItem"=(I ? list("name"=RmName(I), "where"=RmWhere(I, src), "ours"=(IH && IH.Owner == src)) : null),
		"claimOn"=on, "claims"=mine)
