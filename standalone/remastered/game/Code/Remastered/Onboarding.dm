// Remastered onboarding (playtest pass, 2026-10-22): the race pick and the arrival story are HUD cards
// (AskCard.dm, remastered.html renderAskCard) instead of the stock native "Choose" list and alert windows,
// and F3 / Help opens the Guide panel. Without the HUD (no client yet, or before it is ready) the native
// windows are used, as before.

Player/var/tmp/remaster_help_serial = 0   // the page opens the Guide panel each time this changes

// Automated runs (check_app, click_audit, *_native) answer the native race prompt and alerts from the client
// (DM_TEST_RACE, MacWebViewManager.RunRaceSmokeTest), so they keep the native windows: the server sees
// DM_TEST_RACE when the app launched it; harnesses that start their own server can write test-race.txt.
proc/RemasterTestRun()
	return world.GetConfig("env", "DM_TEST_RACE") || fexists("test-race.txt")

// A start (R) pressed while the HUD page is still loading waits for it, so players always get the HUD card and never
// the stock list (the user, 2026-10-24: "we want the new one"). Only a client with no HUD at all, which never says
// ready, gets the native window, after RM_HUD_WAIT.
#define RM_HUD_WAIT 300    // world.time units, tenths of a second: 30 s
Player/proc/RemasterWaitHUD()
	var/until = world.time + RM_HUD_WAIT
	while(client && !remaster_hud_ready && world.time < until) sleep(2)

proc/RemasterChooseRace(mob/who, list/menu)
	var/Player/P = istype(who, /Player) ? who : null
	if(P) P.remaster_succession = null    // a new start: the old "has died" card goes (playtest)
	if(P && !RemasterTestRun()) P.RemasterWaitHUD()
	if(!P || !P.client || !P.remaster_hud_ready || RemasterTestRun()) return input(who, "Which people will you lead?", "Choose your people", null) in menu
	return P.RemasterAsk("Which people will you lead?", "Choose your people", menu, "race")

// Guide goals with no single event to hook: any selection (map click, box, roster) meets "Meet your company";
// crafting XP in an artisan skill (a workshop's Craft menu or the Work tab's production queue) meets "Try your hand at crafting".
Player/var/tmp/remaster_built_at = -1000    // the last workshop built: building one gives crafting XP too (CreateCarpentry)
var/list/rm_onboard_craft_labels = list("Wood crafting", "Metal crafting", "Stone crafting", "Bone crafting", "Leather crafting", "Jewel crafting")
Player/proc/RemasterOnboardTick()
	if(!remaster_milestones) remaster_milestones = list()
	if(length(Selected) && !remaster_milestones["select"]) RemasterMilestone("select")
	if(!remaster_milestones["craft"] && remaster_xp_drops)
		for(var/list/D in remaster_xp_drops) if(D["xp"] && (D["skill"] in rm_onboard_craft_labels) && D["at"] > remaster_built_at + 80)
			RemasterMilestone("craft")
			break

// A start with no trees in reach (SafeStart found no better spot, e.g. open desert): each starter brings one log, so the
// first goals (campfire, carpentry, a first craft) can still be done (playtest round 13: a new player stuck at goal 4).
Player/proc/RemasterStartLogs()
	var/mob/Monsters/F
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && !M.Critter)
		F = M
		break
	if(!F || !isturf(F.loc) || (F.Race in rm_rare_races) || RemasterStartLand(F.loc)) return
	var/n = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && !M.Critter && M.HP > 0)
		M.ForcePickUpItem(new /obj/Items/woods/wood(M.loc))
		n++
	if(n) RemasterNotice("No trees nearby: your people brought [n] log\s to start a camp.")

// The arrival story: the people's tale, as a note at the side with "Got it" (the owner, 11-01: four start screens cut to
// two; newcomers left within a minute). The game goes on underneath at once: nothing waits for the answer.
proc/RemasterStory(mob/who, message, title)
	var/Player/P = istype(who, /Player) ? who : null
	if(P && !RemasterTestRun())
		P.RemasterStartLogs()
		P.RemasterWaitHUD()
	if(!P || !P.client || !P.remaster_hud_ready || RemasterTestRun())
		alert(who, message, title)
		return
	spawn(0) P.RemasterAsk(message, title, list("Got it"), "story")
