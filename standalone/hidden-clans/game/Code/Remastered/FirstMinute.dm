// The first minutes, step by step (the owner, 11-01: three guests left within 25-90 s; "Yes, look into it", then "all
// three"): on a public server every player's way in goes to the server log as one line a step, so tools/first_minute.py
// can show where newcomers stop. A step is logged once a session, with the real seconds since they joined:
//   RMFIRST|<key>|<step>|<detail>|<seconds>
// joined (guest or account), race-card, race (the people picked), company-card, company (Begin or Back), story-card,
// begin (the story's Begin), goal (a guide milestone: select, order, gather, craft, defend), left. Keys only: nothing
// typed and no addresses (the engine's own "joined from" line has those). Before Guests.dm, whose overrides chain on.
var/rm_fm_on = -1                       // -1: on for a public server (RmPublicWorld)
Player/var/tmp/list/rm_fm_start         // RemasterNow() at log-in
Player/var/tmp/list/rm_fm_said          // the steps logged this session

proc/RmFmOn()
	if(rm_fm_on < 0) rm_fm_on = RmPublicWorld() ? 1 : 0
	return rm_fm_on

Player/proc/RmFirst(step, detail)
	if(!RmFmOn() || !rm_fm_start) return
	var/id = detail && step == "goal" ? "goal:[detail]" : step
	if(!rm_fm_said) rm_fm_said = list()
	if(id in rm_fm_said) return
	rm_fm_said += id
	world.log << "RMFIRST|[replacetext("[key]", "|", "/")]|[step]|[replacetext("[detail]", "|", "/")]|[round((RemasterSince(rm_fm_start) || 0) / 10)]"

Player/Login()
	rm_fm_start = RemasterNow()
	rm_fm_said = null
	. = ..()
	if(client && !rm_mod_ban_shown) RmFirst("joined", RmGuestKey(key) ? "guest" : "account")

Player/Logout()
	RmFirst("left")
	rm_fm_start = null
	return ..()

Player/RemasterAsk(message, title, list/options, kind, list/extra)
	var/card = kind in list("race", "company", "story")
	if(card) RmFirst("[kind]-card")
	. = ..()
	if(kind == "race") RmFirst("race", "[.]")
	else if(kind == "company") RmFirst("company", "[.]")
	else if(kind == "story") RmFirst("begin")

Player/RemasterMilestone(id)
	if(!remaster_milestones || !remaster_milestones[id]) RmFirst("goal", "[id]")
	return ..()
