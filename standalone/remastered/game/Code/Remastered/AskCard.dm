// Questions with a list of answers are asked in a HUD card (remastered.html, #askcard) instead of the native
// "Choose" window: the original "What Action Will You Choose?" menus (Click.dm, Verbs.dm), the workshops' and the
// Interact menus (RemasterActionChoice, Actions.dm) and a bag item's choices (InventoryActions.dm). As with
// input(), the asking proc waits for the answer. One question at a time; Cancel or Esc answers "Cancel" when
// that is one of the answers, otherwise nothing (as closing the native window does). Without the HUD (no
// client, or before it is ready) the native window is used.

Player/var/tmp
	list/remaster_ask            // the open question: list("id", "message", "title", "options"=labels)
	list/remaster_ask_options    // its answers as given (texts, or objects such as units)
	remaster_ask_answer
	remaster_ask_serial = 0

proc/RemasterChoose(mob/who, message, title, list/options, default = null)
	var/Player/P = istype(who, /Player) ? who : null
	if(!P || !P.client || !P.remaster_hud_ready || !length(options)) return input(who, message, title, default) in options
	return P.RemasterAsk(message, title, options)

Player/proc/RemasterAsk(message, title, list/options, kind, list/extra)    // kind: null, "race", "story" or "company" (Onboarding.dm, Company.dm); extra: the card's own data
	var/started = world.time
	while(remaster_ask && client && world.time - started < 3000) sleep(2)    // one question at a time
	if(!client) return ("Cancel" in options) ? "Cancel" : null
	remaster_ask_serial++
	var/id = remaster_ask_serial
	var/list/labels = list()
	for(var/o in options) labels += RemasterAskLabel(o)
	remaster_ask_options = options.Copy()
	remaster_ask_answer = null
	remaster_ask = list("id"=id, "message"="[message]", "title"="[title || "Choose"]", "options"=labels, "kind"=kind, "extra"=extra)
	RemasterHUDTick()
	while(client && remaster_ask && remaster_ask["id"] == id) sleep(1)
	if(remaster_ask && remaster_ask["id"] == id) remaster_ask = null    // the player left
	var/a = remaster_ask_answer
	remaster_ask_answer = null
	if(!isnull(a) && (a in options)) return a
	return ("Cancel" in options) ? "Cancel" : null

proc/RemasterAskLabel(o)
	if(ismob(o) && istype(o, /mob/Monsters)) return o:RemasterBareName()
	return "[o]"

// "id|index" (1-based) from the card; "id" alone (askcancel) cancels.
Player/proc/RemasterAskAnswer(value)
	var/list/p = splittext("[value]", "|")
	if(!remaster_ask || length(p) < 2 || text2num(p[1]) != remaster_ask["id"]) return 0
	var/i = text2num(p[2])
	if(!isnum(i) || i < 1 || i > length(remaster_ask_options)) return 0
	remaster_ask_answer = remaster_ask_options[i]
	remaster_ask = null
	return 1

Player/proc/RemasterAskCancel(value)
	if(!remaster_ask || text2num("[value]") != remaster_ask["id"]) return 0
	remaster_ask_answer = null
	remaster_ask = null
	return 1
