// Guests (planning/GUEST_MODE_PLAN_2026-10-31.md; the owner 10-31: "allow guest to play but are restricted to some races
// no save let them know after their session the things they build will disappear unless account it made"). A guest
// joins a server from the browser with a typed name instead of signing in; the engine names them "Guest <name>"
// (engine/web, RM_GUEST). A guest plays the core game with one of four races; nothing of theirs is saved; what would
// outlive them or hand things to an account is locked; and when they leave, every unit that came from them dies where
// it stands (burning, or another of the game's deaths: art/gear3d/deaths.js) and what they built goes. Players may do
// to a guest whatever they may do to anyone (war, capture, enslave; the owner: "players can do anything to they can
// regularlly do but when guest leave the units do the burn animation or a random death animation cant be kept"); a
// guest never declares war, so they only ever fight back (realms are at peace unless one declares war, War.dm).
// This file is the last in the .dme: it overrides procs defined earlier (an earlier override chains the wrong way).
//
// Kept by the browser (the owner, 11-01: "we should also allow people to keep there stuff in guest mode save on browser if
// we can, keep it simple for now", picked "Survives restarts"; then "remove the force to sign up as discord and just do
// guest and play and save on browser"). The page makes a secret code once (32 hex), keeps it in its own storage and sends
// it once a load (guestbrowser). A guest with one is kept as an account is: saved with the companies under
// units/guestkeep_<id>_save.sav (id: the first 24 hex of the code's sha1; the code itself is never stored, shown or
// logged), left standing when they go, and handed back when that browser comes again under its new guest key (the engine
// numbers every visit), the world still running or after a restart. While its guest is away a village waits under a
// parked key, "guestkeep<id>", that no browser can join with (the engine may give the guest's name to someone else); a
// guest's live key in a saved world is mapped back to its village by units/guestkeep_<ckey>_live.txt (the id, written
// while they play). No code (storage blocked): a guest as before. Signing up makes it an account's and the keep goes.

#define RM_GUEST_UNITS 30           // a guest company's most people (births, migrants, captures stop there)
#define RM_GUEST_MAX 10             // guests on one server at once (RM_GUEST_MAX overrides)
var/list/rm_guest_races = list("Human", "Dwarf", "Elf", "Orc")
// The owner, 11-01: "unlock all the races and unlock all the guest freezes for now". Off (0), a guest picks any race
// (rare draws too), may come as a migrant, grows past RM_GUEST_UNITS, and may do all that the locks below stop: war,
// claims, trade, stalls, posting quests, world chat, private messages, allies, clans, tapestries, difficulty. Still never
// saved (no company, designs, achievements or settings kept) and still gone when they leave: that is what a guest is.
// rm_guest_locked = 1 puts every lock back.
var/rm_guest_locked = 0
proc/RmGuestLocked(k)
	return rm_guest_locked && RmGuestKey(k)
// how a guest's people die when the guest leaves, besides burning: causes the page acts out (deaths.js RDCAUSE)
var/list/rm_guest_deaths = list("Coldness", "lightning", "Melting Into Goo", "Crumbled into Bonemeal", "Heart Failure", "old age",
	"being slowly melted by holy energy")
var/list/rm_guest_taken = list()     // a guest's id -> their people someone else holds now (enslaved, won over)
var/list/rm_guest_codes = list()     // a keep code (the page's Sign up) -> the guest whose village it keeps
var/rm_guest_grace = 3000            // how long a village waits for its guest's sign-up after they left (5 minutes)

mob/Monsters/var/rm_guest_from       // saved: the id of the guest this unit came from; it goes when they do
mob/Monsters/var/tmp/rm_guest_going = 0
Player/var/tmp
	rm_guest_id                       // "Guest <name>#<stamp>": this guest's session
	list/rm_guest_laid                // turfs where this guest laid blocks (Plans.dm RmLaidMark)
	rm_guest_left = 0
	rm_guest_code                     // the code an account brings back from the sign-up to keep this village
	rm_guest_signup_at = 0            // when this guest opened the sign-up: if they leave, the village waits a while
	rm_guest_kept = 0                 // an account took this village: it is theirs, nothing goes
	rm_guest_keep                     // the id of the browser keep this village is saved under (24 hex), or null: not kept
	rm_guest_browser_seen = 0         // the page has sent its code (or that it has none)
	rm_guest_back = 0                 // a kept village is coming back to this player (its Login leaves the welcome to it)
	rm_guest_back_at = 0              // when it came back: a start the page pressed just then is an old one
	rm_guest_handed = 0               // this fresh player gave its client to the village its browser keeps
	rm_guest_away = 0                 // a kept village's guest left: it waits for its browser (RmGuestPark)
	rm_guest_restoring = 0            // LoadUnits is reading this player's browser-kept company

#define RM_GUEST_BROWSER_WAIT 30      // how long a guest's start waits for the page's code once the page is ready (3 s)
var/list/rm_guest_keeps = list()     // a browser keep's id -> the Player whose village it is (playing or away)

// By the key as the engine keeps it ("Guest Kiwi", "guestkiwi", "localhost@guestkiwi"): it starts with "guest". No
// account may (the sign-in side never issues one), so a typed name can't take an account's saves or a guest's place.
// Only on a server that takes guests (RM_GUEST=1: a public browser server, engine/web gives typed names "Guest <name> <n>").
// Anywhere else (the Mac app's own world, Host for friends, Join a friend) nobody is a guest, whatever their name.
var/rm_guest_on = -1
proc/RmGuestKey(k)
	if(rm_guest_on < 0) rm_guest_on = world.GetConfig("env", "RM_GUEST") == "1"
	if(!rm_guest_on || !istext(k)) return 0
	var/c = ckey(k)
	var/at = findtext(c, "@")
	if(at) c = copytext(c, at + 1)
	return length(c) > 5 && copytext(c, 1, 6) == "guest"

proc/RmIsGuest(mob/M)
	return ismob(M) && RmGuestKey(M.key)

proc/RmGuestOnline(id)
	if(!id) return null
	for(var/Player/P in Players) if(P.rm_guest_id == id && !P.rm_guest_left) return P
	return null

// One line for every lock: why, and what signing in gives.
Player/proc/RmGuestNo(why)
	RemasterNotice("[why] Sign in with Discord to do this, and to keep your village.")
	return 0

// --- joining ------------------------------------------------------------------------------------------------------------
Player/proc/RmGuestStart()
	if(!rm_guest_id) rm_guest_id = "[key]#[RemasterIdStamp()]"
	remaster_open = 0                 // never a realm others may join (Realms.dm RemasterOpenRealms)
	if(!rm_guest_code)
		rm_guest_code = RmGuestNewCode()
		rm_guest_codes[rm_guest_code] = src

proc/RmGuestNewCode()
	do
		. = ""
		for(var/i = 1, i <= 16, i++) . += pick("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f")
	while(rm_guest_codes[.])

// Where the page sends a guest to sign up (the server's RM_WEB_SIGNIN_URL, as the lobby's Sign in), or null: no Sign up.
proc/RmGuestSigninURL()
	var/u = world.GetConfig("env", "RM_WEB_SIGNIN_URL")
	return (istext(u) && length(u)) ? u : null

Player/Login()
	if(!RmGuestKey(key)) return ..()
	var/n = 0
	var/most = text2num(world.GetConfig("env", "RM_GUEST_MAX")) || RM_GUEST_MAX
	for(var/Player/P in Players) if(P != src && P.client && RmGuestKey(P.key)) n++
	if(n >= most)
		src << "Guest places are full. Sign in with Discord to play."
		spawn(5) if(client) del(client)
		return 0
	RmGuestStart()
	name = RemasterWho()   // the name they typed, from the first line others see ("... has logged in")
	. = ..()
	if(!rm_guest_back) spawn(0) RmGuestJoinNotice()   // a kept village coming back says welcome itself (RmGuestUnpark)

// What a guest is told at the start, once their page has said whether this browser keeps their village (RmGuestBrowser).
Player/proc/RmGuestJoinNotice()
	var/until = world.time + RM_HUD_WAIT + RM_GUEST_BROWSER_WAIT
	while(client && !rm_guest_browser_seen && world.time < until) sleep(2)
	if(!client || rm_guest_back || (rm_guest_back_at && world.time - rm_guest_back_at < 50)) return
	if(rm_guest_keep) RemasterNotice("You're playing as a guest: your village is saved in this browser. Come back from this browser to carry on.")
	else RemasterNotice("You're playing as a guest: nothing you build is kept. When you leave, your people die and your village is gone. Sign in with Discord to keep what you build.")

// No load, no save: a guest always starts fresh and leaves nothing on disk, but for a village its browser keeps (below).
// The player's own file (players/) is never a guest's; a player whose client went to another (key gone) writes none.
mob/Load()
	if(RmGuestKey(key)) return
	return ..()
mob/Save()
	if(!ckey || RmGuestKey(key)) return
	return ..()
mob/LoadUnits()
	if(RmGuestKey(key) && !(istype(src, /Player) && src:rm_guest_restoring)) return 0
	. = ..()
	// someone else's guest people saved in this company (a crash before they went): gone now, as they would have; the
	// people of a village a browser keeps stay
	if(.) for(var/mob/Monsters/M in UnitList) if(M.rm_guest_from && !RmGuestAlive(M.rm_guest_from)) RmGuestVanish(M, 0)

// Where a company is saved (Saves.dm SaveUnits, LoadUnits): an account's by its key; a browser-kept guest's by the keep.
mob/proc/RmUnitsSave()
	return "units/[ckey]_save.sav"
Player/RmUnitsSave()
	if(RmGuestBrowserKept()) return RmGuestKeepPath(rm_guest_keep)
	return ..()
// Saved with the companies (Saves.dm SaveUnits): a guest only when their browser keeps the village.
mob/proc/RmGuestBrowserKept()
	return 0
Player/RmGuestBrowserKept()
	return rm_guest_keep && !rm_guest_kept && RmGuestKey(key)

// Locked: four races, never a rare one (Restart.dm asks RmGuestRaceMenu), and never as migrants into a realm.
proc/RmGuestRaceMenu(list/menu)
	if(!rm_guest_locked) return menu
	. = list()
	for(var/r in menu) if((r in rm_guest_races) || r == "Cancel") . += r
Player/RemasterRareDraw()
	if(RmGuestLocked(key)) return list()
	return ..()
Player/RemasterMigrantChoice()
	if(RmGuestLocked(key)) return null
	return ..()

// A guest's company: marked as theirs (so it goes with them, wherever it is); locked, at most RM_GUEST_UNITS people.
mob/ChangeOwnership(WHO, FORCE)
	var/mob/old = ismob(Owner) ? Owner : null
	var/mob/Monsters/U = istype(src, /mob/Monsters) ? src : null
	if(U && istype(WHO, /Player) && WHO != old && RmGuestLocked(WHO:key) && !U.rm_guest_going && length(WHO:UnitList) >= RM_GUEST_UNITS)
		WHO:RemasterNotice("A guest company keeps at most [RM_GUEST_UNITS] people. Sign in with Discord to grow it.")
		return 0
	. = ..()
	if(!. || !U || WHO == old) return
	if(istype(WHO, /Player) && RmGuestKey(WHO:key))
		if(!U.rm_guest_from) U.rm_guest_from = WHO:rm_guest_id
		return
	if(!U.rm_guest_from && istype(old, /Player) && RmGuestKey(old.key)) U.rm_guest_from = old:rm_guest_id
	if(U.rm_guest_from && RmGuestOnline(U.rm_guest_from))   // taken from the guest (enslaved, won over): still goes when they do
		var/list/L = rm_guest_taken[U.rm_guest_from]
		if(!L)
			L = list()
			rm_guest_taken[U.rm_guest_from] = L
		L |= U

// What others see: the name the guest typed. The engine keys a guest "Guest <name> <n>" (engine/web) so the game knows them
// and no one else can take their place; nobody sees that ("Guest Bob 1784" shows as "Bob": the owner, 10-31, "allow them
// to name themselves anything").
proc/RmGuestShownName(k)
	var/t = "[k]"
	var/at = findtext(t, "@")
	if(at) t = copytext(t, at + 1)
	if(lowertext(copytext(t, 1, 7)) == "guest ") t = copytext(t, 7)
	else if(lowertext(copytext(t, 1, 6)) == "guest") t = copytext(t, 6)
	var/n = length(t)
	while(n > 1 && text2ascii(t, n) >= 48 && text2ascii(t, n) <= 57) n--
	if(n < length(t) && copytext(t, n, n + 1) == " ") t = copytext(t, 1, n)
	t = trimtext(t)
	return length(t) ? t : "Traveller"
Player/RemasterWho()
	if(rm_guest_keep && key == RmGuestParkedKey(rm_guest_keep)) return name   // away, under its parked key: as last seen
	if(RmGuestKey(key)) return RmGuestShownName(key)
	return ..()

// --- locks (only while rm_guest_locked) ----------------------------------------------------------------------------------------------------------------
// War, laws, claims on seats, joining or taking in other realms: a guest may only make or take peace.
Player/RemasterRealmCommand(value)
	if(RmGuestLocked(key))
		var/list/p = splittext("[value]", "|")
		if(!length(p) || !(p[1] in list("peace", "acceptpeace", "declinepeace")))
			return RmGuestNo("Guests can't declare war or deal with other realms; they only fight back.")
	return ..()
Player/RemasterBuildBanner(mob/Monsters/M, turf/T)
	if(RmGuestLocked(key)) return RmGuestNo("Guests can't claim land.")
	return ..()
Player/RemasterMarketCommand(value)
	if(RmGuestLocked(key)) return RmGuestNo("Guests can't trade with other players.")
	return ..()
mob/Monsters/RemasterAssignJob(VALUE)
	if(VALUE == "merchant" && istype(Owner, /Player) && RmGuestLocked(Owner:key)) return Owner:RmGuestNo("Guests can't keep a market stall.")
	return ..()
Player/RmQuestCommand(value)
	if(RmGuestLocked(key))
		var/list/p = splittext("[value]", "|")
		if(length(p) && (p[1] in list("post", "postform"))) return RmGuestNo("Guests can't post quests (they can take them).")
	return ..()
Player/RmDesignsLoad()
	if(RmGuestKey(key))
		if(!rm_designs) rm_designs = list()
		return rm_designs
	return ..()
Player/RmDesigns(value)
	if(RmGuestKey(key) && findtext("[value]", "save|") == 1) return RmGuestNo("Guests can't keep designs.")
	return ..()
// The profile is never opened: no achievements kept (no better rare odds), settings only in the page's own storage.
Player/RemasterRecordAchievement(id)
	if(RmGuestKey(key)) return
	return ..()
Player/RemasterAchievementsEver()
	if(RmGuestKey(key)) return remaster_achieved ? remaster_achieved.Copy() : list()
	return ..()
Player/RemasterAudioPrefs()
	if(RmGuestKey(key)) return ""
	return ..()
Player/RemasterAudioSave(value)
	if(RmGuestKey(key)) return
	return ..()
Player/RemasterHUDPrefs()
	if(RmGuestKey(key)) return ""
	return ..()
Player/RemasterHUDPrefsSave(value)
	if(RmGuestKey(key)) return
	return ..()
Player/RemasterSaveNow()
	if(RmGuestKey(key) && !RmGuestBrowserKept()) return RmGuestNo("Guests aren't saved.")
	return ..()
Player/RemasterDifficultyCommand(value)
	if(RmGuestLocked(key)) return RmGuestNo("Guests can't change the world's settings.")
	return ..()
// World chat, private messages, allies, clans, tapestries.
mob/WorldSay()
	if(istype(usr, /Player) && RmGuestLocked(usr.key)) return usr:RmGuestNo("Guests can't talk to the whole world (talk to the people near you).")
	return ..()
mob/ClanChat()
	if(istype(usr, /Player) && RmGuestLocked(usr.key)) return usr:RmGuestNo("Guests can't join clans.")
	return ..()
mob/AddAlly()
	if(istype(usr, /Player) && RmGuestLocked(usr.key)) return usr:RmGuestNo("Guests can't make allies.")
	return ..()
mob/RemoveAlly()
	if(istype(usr, /Player) && RmGuestLocked(usr.key)) return usr:RmGuestNo("Guests can't make allies.")
	return ..()
mob/Create_A_Clan()
	if(istype(usr, /Player) && RmGuestLocked(usr.key)) return usr:RmGuestNo("Guests can't make clans.")
	return ..()
mob/PlaceTapestry()
	if(istype(usr, /Player) && RmGuestLocked(usr.key)) return usr:RmGuestNo("Guests can't hang tapestries.")
	return ..()
Player/RemasterMessage()
	if(RmGuestLocked(key)) return RmGuestNo("Guests can't send private messages.")
	return ..()

// The HUD knows it is a guest's (the banner and Leave, art/hud/src).
Player/RemasterHUDData(spread = 0)
	. = ..()
	if(islist(.) && RmGuestKey(key)) .["guest"] = list("signin" = RmGuestSigninURL(), "code" = rm_guest_code, "kept" = RmGuestBrowserKept() ? 1 : 0)

// --- leaving --------------------------------------------------------------------------------------------------------------
// Each of the guest's people goes where it stands: about half turn to stone (they stiffen and grey in a breath of stone
// dust, and a statue of them is left there), the rest die one of the game's deaths (burning, cold, lightning, goo...),
// acted out by the page; then it and all it carries are gone: no body, nothing dropped, no Legends line, no war score.
proc/RmGuestVanish(mob/Monsters/M, act = 1)
	if(Rm3DGone(M) || M.rm_guest_going) return
	M.rm_guest_going = 1
	if(M.rm_offguard_on)   // the away loop never ticks a unit that is going (OfflineGuards.dm)
		rm_offguard -= M
		M.rm_offguard_on = 0
	if(ismob(M.Owner)) M.Owner:UnitList -= M
	M.destination = null
	M.Stunned = 1
	M.CantKill = 1
	M.remaster_defense = null
	M.remaster_attack = null
	M.remaster_orders = list()
	var/stone = act && prob(50)
	var/cause = stone ? "Turned To Stone" : pick(list("Burned To Death") + rm_guest_deaths)
	M.DeathType = cause
	if(act && isturf(M.loc)) RemasterHitAt(M.x, M.y, M.z, 0, "die", null, M.Owner, cause)
	spawn(stone ? 20 : (act ? 45 : 0))
		if(!Rm3DGone(M))
			var/turf/T = M.loc
			var/who = M.RemasterBareName()
			for(var/atom/movable/A in M) del(A)
			del(M)
			if(stone && isturf(T))   // the game's own stone statue stands where it turned, out of everyone's way
				var/obj/Items/Furniture/Pillars/Statue/S = new(T)
				S.name = "[who], turned to stone"
				S.density = 0

// What a guest leaves: their people (theirs, and those others took from them), their workshops, banners, the blocks they
// laid, the things lying in their stockpiles, their orders and zones, any war on them. The ground they dug or chopped
// stays, as any wild damage does.
Player/proc/RmGuestLeave()
	if(rm_guest_left) return
	rm_guest_left = 1
	var/list/units = list()
	for(var/mob/Monsters/M in UnitList) units |= M
	if(rm_guest_id && rm_guest_taken[rm_guest_id])
		units |= rm_guest_taken[rm_guest_id]
		rm_guest_taken -= rm_guest_id
	for(var/mob/Monsters/M in units) if(!Rm3DGone(M) && (M.Owner == src || (rm_guest_id && M.rm_guest_from == rm_guest_id))) RmGuestVanish(M)
	UnitList = list()
	Selected = list()
	// the things in their stockpiles that nobody else owns
	var/list/piles = list()
	var/turf/S = RemasterStockpile()
	if(S) piles += S
	if(remaster_zones) for(var/list/Z in remaster_zones)
		var/turf/T = locate(Z["x"], Z["y"], Z["z"])
		if(T) piles += T
	var/list/gone = list()
	for(var/turf/T in piles) for(var/obj/Items/I in range(2, T)) if(isturf(I.loc))
		var/k = RemasterWorldOwnerKey(I)
		if(!k || k == key) gone |= I
	for(var/obj/Items/I in world) if(isturf(I.loc) && RemasterWorldOwnerKey(I) == key) gone |= I
	for(var/mob/WorkShops/W in world) if(W.Owner == src || W.remaster_owner_key == key) gone |= W
	for(var/obj/RemasterBanner/B in rm_banners) if(B.owner_key == key) gone |= B
	rm_banners -= gone
	for(var/atom/movable/A in gone) del(A)
	for(var/turf/T in rm_guest_laid) RmGuestUnlay(T, key)
	rm_guest_laid = null
	for(var/w in rm_wars.Copy())
		var/list/two = splittext(w, "|")
		if(key in two) rm_wars -= w
	rm_realm_ver++
	RmStartOverWork()

// The blocks a guest laid at T come down, top first; the natural ground under them stays.
proc/RmGuestUnlay(turf/T, k)
	if(!T || T.remaster_laid_by != k) return
	for(var/n = 0, n < 16, n++)
		var/top = RmBuiltTopK(T)
		if(top < 0) break
		RemasterTakeTopBlock(T)
		RmLaidForget(T, top)
	if(T.remaster_laid_by == k) for(var/b = 0, b < 16, b++) RmLaidForget(T, b)   // marks of blocks no longer there
	RemasterFeetCheck(T)

Player/Logout()
	if(!RmGuestKey(key) || rm_guest_kept || rm_guest_handed) return ..()
	if(rm_guest_keep)   // kept by its browser: the people stay as an account's do (guarding), the village waits for it
		. = ..()
		RmGuestPark()
		return
	if(rm_guest_signup_at && world.time - rm_guest_signup_at < 6000)   // signing up: the village waits for the account
		. = ..()
		spawn(0) RmGuestLeaveLater()
		return
	RmGuestLeave()
	. = ..()
	RmGuestGone()

Player/proc/RmGuestGone()
	Players2 -= src
	if(rm_guest_code) rm_guest_codes -= rm_guest_code
	var/Player/P = src
	spawn(60) if(!Rm3DGone(P) && !P.client) del(P)   // the name is free again

// A guest who left while signing up (the sign-in in this tab, or the tab closed): their village waits rm_guest_grace for
// the account to come for it, or for the guest to come back; then it goes as on any leave.
Player/proc/RmGuestLeaveLater()
	var/until = world.time + rm_guest_grace
	while(world.time < until && !rm_guest_kept && !client) sleep(10)
	if(rm_guest_kept || client) return
	RmGuestLeave()
	RmGuestGone()

// Leave (the guest banner's button, the page): asked first, then the session ends (a browser shows the ended page).
Player/RemasterTouchCommand(action, value)
	if(action == "guestleave")
		if(RmGuestKey(key)) spawn(0) RmGuestLeaveAsk()
		return
	if(action == "guestsignup")   // the page opened the sign-up in a new tab
		if(RmGuestKey(key)) rm_guest_signup_at = world.time
		return
	if(action == "guestkeep")     // an account's page came back from that sign-up with the village's code
		if(!RmGuestKey(key)) spawn(0) RmGuestClaim("[value]")
		return
	if(action == "guestbrowser")  // the page's code from this browser's storage, once a load ("" when it has none); never logged
		if(RmGuestKey(key)) RmGuestBrowser("[value]")
		return
	return ..()
Player/proc/RmGuestLeaveAsk()
	var/c
	if(RmGuestBrowserKept()) c = RemasterChoose(src, "Your village is saved in this browser: come back from this browser to carry on.", "Leave for now?", list("Leave", "Stay"), "Stay")
	else c = RemasterChoose(src, "Your village, its people and everything you built will disappear when you leave. Sign up (the banner) to keep what you build.", "Leave as a guest?", list("Leave anyway", "Stay"), "Stay")
	if(!(c in list("Leave anyway", "Leave")) || !client) return
	src << output("", "mapwindow.hud:rmGuestGone")   // the goodbye card (the page), then the session ends
	var/client/C = client
	spawn(15) if(C) del(C)

// Keep my village: this account came back from the sign-up the guest started, with its code. With no company of its
// own in this world (one company per player per world), it takes the guest's own player (client.mob: the engine gives
// it this account's key and logs it in), so the people, workshops, stockpiles, blocks and orders are all as they were and
// save from now on. The guest's tab ends; this account's fresh player goes.
Player/proc/RmGuestClaim(code)
	var/Player/G = rm_guest_codes[code]
	if(!istype(G) || G == src || Rm3DGone(G) || G.rm_guest_left || G.rm_guest_kept || !RmGuestKey(G.key))
		RemasterNotice("That guest village is gone: a guest's village goes when they leave.")
		return 0
	var/n = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0) n++
	if(n || fexists("units/[ckey]_save.sav"))
		RemasterNotice("Your account already has a company in this world, so the guest village can't join it. It goes when the guest leaves.")
		G.RemasterNotice("That account already has a company in this world: this village can't move to it.")
		return 0
	var/client/C = client
	if(!C) return 0
	G.rm_guest_kept = 1
	rm_guest_codes -= code
	if(G.client) del(G.client)      // the guest's tab ends; its Logout keeps everything (kept)
	var/old = G.key
	C.mob = G
	G.RmGuestBecameAccount(old)
	var/Player/A = src
	spawn(10) if(!Rm3DGone(A) && !A.client) del(A)
	return 1

// The guest's player is an account's now (key changed): nothing of it goes any more, its blocks are the account's, and its
// company is saved at once (the world's own changes with the next save).
Player/proc/RmGuestBecameAccount(old)
	for(var/mob/Monsters/M in UnitList) M.rm_guest_from = null
	if(rm_guest_id && rm_guest_taken[rm_guest_id])
		for(var/mob/Monsters/M in rm_guest_taken[rm_guest_id]) M.rm_guest_from = null
		rm_guest_taken -= rm_guest_id
	RmGuestRekey(old, key)   // its blocks, workshops, things and banners are the account's; wars on the guest end
	rm_guest_laid = null
	if(rm_guest_keep) RmGuestKeepDrop(old)   // the account owns it now: the browser's keep no longer applies
	if(rm_guest_code) rm_guest_codes -= rm_guest_code
	rm_guest_id = null
	rm_guest_code = null
	var/savefile/S = new("units/[ckey]_save.sav")
	savedx = x
	savedy = y
	savedz = z
	for(var/mob/X in UnitList)
		X.savedx = X.x
		X.savedy = X.y
		X.savedz = X.z
	Write(S)
	RemasterNotice("Your village is yours now: it saves with your account.")

// A world loaded after a crash: whatever a guest had in it then goes (WorldSave.dm RemasterLoadWorld calls this), but for
// a village a browser keeps: its things wait under its parked key (those saved while its guest played, by the live file).
proc/RmGuestTidyLoaded()
	var/list/park = list()   // a guest key in the saved world -> the parked key of the browser-kept village it was, or 0
	var/list/gone = list()
	var/p
	for(var/obj/Items/I in world) if(RmGuestKey(I.remaster_owner_key))
		p = RmGuestParkFor(I.remaster_owner_key, park)
		if(p) I.remaster_owner_key = p
		else gone += I
	for(var/mob/WorkShops/W in world) if(RmGuestKey(W.remaster_owner_key))
		p = RmGuestParkFor(W.remaster_owner_key, park)
		if(p) W.remaster_owner_key = p
		else gone += W
	for(var/obj/RemasterBanner/B in rm_banners) if(RmGuestKey(B.owner_key))
		p = RmGuestParkFor(B.owner_key, park)
		if(p) B.owner_key = p
		else gone += B
	rm_banners -= gone
	for(var/atom/movable/A in gone) del(A)
	for(var/c in remaster_dirty_turfs)
		var/list/xyz = splittext(c, ",")
		var/turf/T = length(xyz) == 3 ? locate(text2num(xyz[1]), text2num(xyz[2]), text2num(xyz[3])) : null
		if(T && RmGuestKey(T.remaster_laid_by))
			p = RmGuestParkFor(T.remaster_laid_by, park)
			if(p) T.remaster_laid_by = p
			else RmGuestUnlay(T, T.remaster_laid_by)
	for(var/w in rm_wars.Copy())
		var/list/two = splittext(w, "|")
		if(length(two) == 2 && (RmGuestKey(two[1]) || RmGuestKey(two[2]))) rm_wars -= w
	// nobody plays in a world that has just loaded: every live file is spent (a later guest may get that name)
	for(var/f in flist("units/")) if(findtext(f, "guestkeep_") == 1 && findtext(f, "_live.txt")) fdel("units/[f]")
	return length(gone)

// The parked key a guest key in a loaded world goes under (its village is kept by a browser), or 0: it goes.
proc/RmGuestParkFor(k, list/park)
	if(!isnull(park[k])) return park[k]
	. = RmGuestParkedId(k) ? k : 0
	if(!. && fexists(RmGuestLivePath(k)))
		var/id = trimtext(file2text(RmGuestLivePath(k)))
		if(RmGuestHex(id, 24) && fexists(RmGuestKeepPath(id))) . = RmGuestParkedKey(id)
	park[k] = .

// --- kept by the browser ------------------------------------------------------------------------------------------------
// text of n hex digits (lower case), as the page's code (32) and a keep's id (24) are
proc/RmGuestHex(t, n)
	if(!istext(t) || length(t) != n) return 0
	for(var/i = 1, i <= n, i++)
		var/c = text2ascii(t, i)
		if(!((c >= 48 && c <= 57) || (c >= 97 && c <= 102))) return 0
	return 1

// The keep's id for the page's code: the first 24 hex of its sha1, or null when the code isn't 32 hex (it is ignored).
proc/RmGuestKeepId(code)
	if(!istext(code)) return null
	code = lowertext(code)
	if(!RmGuestHex(code, 32)) return null
	return copytext(sha1(code), 1, 25)

proc/RmGuestKeepPath(id)
	return "units/guestkeep_[id]_save.sav"
proc/RmGuestParkedKey(id)
	return "guestkeep[id]"
proc/RmGuestLivePath(k)
	return "units/guestkeep_[ckey(k)]_live.txt"

// The keep's id when k is a parked key whose village is kept (in this run, or saved), else null.
proc/RmGuestParkedId(k)
	if(!istext(k) || length(k) != 33 || copytext(k, 1, 10) != "guestkeep") return null
	var/id = copytext(k, 10)
	if(!RmGuestHex(id, 24)) return null
	return (rm_guest_keeps[id] || fexists(RmGuestKeepPath(id))) ? id : null

// A guest's people (rm_guest_from) still have their guest: playing now, or a village a browser keeps (its people carry
// the parked key as their guest's id).
proc/RmGuestAlive(id)
	return RmGuestOnline(id) || RmGuestParkedId(id)

Player/proc/RmGuestPeople()
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0) return 1
	return 0

// The page's code (guestbrowser), once a player: this browser's village comes back (away in this world, or saved), or
// this one is kept from now on. A bad code or none: a guest as before. One village a code: a second tab is refused.
Player/proc/RmGuestBrowser(code)
	if(!RmGuestKey(key) || rm_guest_browser_seen || rm_guest_kept) return 0
	rm_guest_browser_seen = 1
	if(rm_guest_keep) return 0
	var/id = RmGuestKeepId(code)
	if(!id) return 0
	var/Player/K = rm_guest_keeps[id]
	if(!istype(K) || Rm3DGone(K) || K.rm_guest_keep != id || K.rm_guest_kept) K = null
	if(K && (K.client || !K.rm_guest_away))   // its guest is playing it now
		RemasterNotice("This browser's village is already open in another tab or window: play it there. What you build here isn't kept.")
		return 0
	if(K || fexists(RmGuestKeepPath(id)))
		if(RmGuestPeople())   // a company started already (the code came late): never two villages for one browser
			RemasterNotice("This browser keeps another village: leave and come back to play it. What you build here isn't kept.")
			return 0
		return K ? RmGuestHandBack(K) : RmGuestKeepLoad(id)
	RmGuestKeepStart(id)
	return 1

// This village is kept by the browser keep id from now on (its first visit, or its save about to be read back).
Player/proc/RmGuestKeepStart(id)
	rm_guest_keep = id
	rm_guest_away = 0
	rm_guest_keeps[id] = src
	var/was = rm_guest_id
	rm_guest_id = RmGuestParkedKey(id)   // what its people carry (rm_guest_from): the same on every visit, after a restart too
	var/list/L = was ? rm_guest_taken[was] : null
	if(L)
		rm_guest_taken -= was
		rm_guest_taken[rm_guest_id] = L
	for(var/mob/Monsters/M in UnitList + (L || list())) if(M.rm_guest_from == was) M.rm_guest_from = rm_guest_id
	RmGuestLiveMark()

// While its guest plays, a kept village's things carry the guest's live key: a world saved now names it, and the next
// start maps it back to the village (RmGuestTidyLoaded) by this small file holding the keep's id (never the code).
Player/proc/RmGuestLiveMark()
	if(!rm_guest_keep || !key) return
	var/f = RmGuestLivePath(key)
	fdel(f)   // text2file adds to a file
	text2file(rm_guest_keep, f)
proc/RmGuestLiveUnmark(k)
	if(k) fdel(RmGuestLivePath(k))

// Everything of this village under the key old goes under fresh (going away, coming back, signing up): the blocks it laid
// (those it laid this run; scan: a loaded world's changed tiles too), its workshops, things, banners and siege engines.
// Wars on old end, as they do when a guest's village goes.
Player/proc/RmGuestRekey(old, fresh, scan = 0)
	if(!old || !fresh || old == fresh) return
	var/was = RemasterRootKey(old)
	var/now = RemasterRootKey(fresh)
	if(!rm_guest_laid) rm_guest_laid = list()
	if(scan) for(var/c in remaster_dirty_turfs)
		var/list/xyz = splittext(c, ",")
		var/turf/T = length(xyz) == 3 ? locate(text2num(xyz[1]), text2num(xyz[2]), text2num(xyz[3])) : null
		if(T && T.remaster_laid_by == was) rm_guest_laid[T] = 1
	for(var/turf/T in rm_guest_laid) if(T.remaster_laid_by == was) T.remaster_laid_by = now
	for(var/obj/Items/I in world) if(I.remaster_owner_key == old)
		I.remaster_owner_key = fresh
		I.Owner = src
	for(var/mob/WorkShops/W in world) if(W.remaster_owner_key == old)
		W.remaster_owner_key = fresh
		W.Owner = src
	for(var/obj/RemasterBanner/B in rm_banners) if(B.owner_key == old) B.owner_key = fresh
	for(var/mob/Monsters/RemasterSiege/E in rm_siege_engines) if(E.remaster_owner_key == old)
		E.remaster_owner_key = fresh
		E.Owner = src
	for(var/w in rm_wars.Copy())
		var/list/two = splittext(w, "|")
		if(old in two) rm_wars -= w
	rm_realm_ver++

// The kept village's guest left: it waits under its parked key (no browser can join with it; the engine may give the
// guest's name and number to someone else), saved at once.
Player/proc/RmGuestPark()
	rm_guest_away = 1
	var/live = key
	var/parked = RmGuestParkedKey(rm_guest_keep)
	RmGuestRekey(live, parked)
	key = parked
	RmGuestLiveUnmark(live)
	RmGuestKeepSave()

// The kept village is this player's again under its new key; told so.
Player/proc/RmGuestUnpark(old, scan = 0)
	rm_guest_away = 0
	RmGuestRekey(old, key, scan)
	RmGuestLiveMark()
	rm_guest_back = 0
	rm_guest_back_at = world.time
	RemasterNotice("Welcome back: your village was kept by this browser.")

// The village this browser keeps, away in this running world, back with this browser's new guest player: as signing up
// does it (RmGuestClaim), the client goes to the village's own Player (the engine gives it this key, logs it in and sends
// the page again), its things are re-keyed, and this fresh player goes.
Player/proc/RmGuestHandBack(Player/K)
	var/old = K.key
	rm_guest_handed = 1
	K.rm_guest_back = 1
	if(client) client.mob = K
	else   // no client (a windowless check): the same hand-over of the key, without the log-in
		var/k = key
		key = null
		K.key = k
	K.RmGuestUnpark(old)
	RmGuestDrop()
	return 1

// The village this browser keeps, from its save (the world restarted since): read into this fresh player as an account's
// company is at log-in (LoadUnits), its things in the loaded world re-keyed to this key, the page sent it all again.
Player/proc/RmGuestKeepLoad(id)
	RmGuestKeepStart(id)
	usr = src   // LoadUnits hands the units to usr
	rm_guest_restoring = 1
	var/ok = LoadUnits()
	rm_guest_restoring = 0
	if(!ok) return 0   // unreadable: this one is kept from now on instead
	RmGuestUnpark(RmGuestParkedKey(id), 1)
	remaster_hud_unit_codes = null   // as the page's "hudfull" and "3dfull" (HUD.dm): its next sends are whole
	Remaster3DForget()
	remaster_3d_last = null
	return 1

// A browser-kept company read back names the guest key it had; this player keeps its own (reading a key into a player
// would hand it whoever has that key now: the engine may have given that guest's name to someone else).
Player/Read(savefile/F)
	if(!rm_guest_restoring || !key) return ..()
	F["key"] << key
	. = ..()
	del(F)   // closed: a later read of this save in this run is what is on disk then (the engine keeps an open save by path)

// This village's company to its browser keep's save, as SaveUnits writes an account's (Saves.dm): through a fresh
// stand-in the engine writes in its place (WorldSave.dm), so a later read in this run never gets an old copy.
Player/proc/RmGuestKeepSave()
	if(!rm_guest_keep) return 0
	var/list/keep = list()
	for(var/X in UnitList) if(X) keep += X
	if(length(keep) != length(UnitList))   // a unit deleted without dying leaves an empty slot (RemasterTidyUnitLists)
		UnitList.Cut()
		UnitList += keep
	savedx = x
	savedy = y
	savedz = z
	for(var/mob/X in UnitList)
		X.savedx = X.x
		X.savedy = X.y
		X.savedz = X.z
	var/sav = RmGuestKeepPath(rm_guest_keep)
	fdel(sav + ".new")
	var/savefile/S = new(sav + ".new")
	try
		S.rm_later = sav
	catch
		del(S)
		S = new(sav)
	Write(S)
	del(S)
	return 1

// Signed up: the account owns the village, so the browser's keep and its save go (else a restart would bring it back to
// the browser as well).
Player/proc/RmGuestKeepDrop(live)
	if(rm_guest_keeps[rm_guest_keep] == src) rm_guest_keeps -= rm_guest_keep
	fdel(RmGuestKeepPath(rm_guest_keep))
	RmGuestLiveUnmark(live)
	rm_guest_keep = null

// The fresh player a browser's village came back in place of: gone (its name free again), nothing of the village with it.
Player/proc/RmGuestDrop()
	Players -= src
	Players2 -= src
	if(rm_guest_code) rm_guest_codes -= rm_guest_code
	var/Player/P = src
	spawn(10) if(!Rm3DGone(P) && !P.client) del(P)

// A guest's start (the race picker, which the page presses for a newcomer, 011-onboarding startCard) waits a moment for
// the page's code, so a browser that keeps a village gets it back instead of a new company; a start pressed as the village
// came back is an old one.
mob/Restart()
	if(istype(src, /Player) && RmGuestKey(key) && !src:RmGuestStartWait()) return
	return ..()
Player/proc/RmGuestStartWait()
	if(rm_guest_back_at && world.time - rm_guest_back_at < 50) return 0
	if(rm_guest_browser_seen || !client) return 1
	RemasterWaitHUD()
	var/until = world.time + RM_GUEST_BROWSER_WAIT
	while(client && !rm_guest_browser_seen && world.time < until) sleep(1)
	if(!client || rm_guest_handed) return 0   // its client went to the village it keeps
	return !(rm_guest_back_at && world.time - rm_guest_back_at < 50)
