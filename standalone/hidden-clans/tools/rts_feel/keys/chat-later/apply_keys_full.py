#!/usr/bin/env python3
"""One key map (rts-feel, 2026-10-25; the playtest audit's launch blocker 3). The user's decisions:
  "no wsd to pan camera A = Attack-move what it is now"   W, S and D don't pan; their old commands (SendMSG, WorldSay,
                                                          DeclareLeader) and Y's GMChat come off the game window's keys
  "enter opens chat box"                                  Enter: a one-line chat box; plain text shouts, /c clan,
                                                          /w name whisper
  R "Menu only"                                           Restart comes off R (Settings and the menu keep it)
  U, L, X, - and B's old build menu come off the keys and stay in the menus; C = cutaway and X = x-ray, as the page.
Server and skin half (the page's half: apply_keys_page.py; the web view's: apply_keys_native.py).
  skin.dmf            the W S D Y U L - B R macros go; C and X go to the page (Remaster-3D-Key); RETURN opens the chat line
  Attack.dm           Remaster-3D-Key passes c, x and enter on; an attack or attack-move order can be undone (Ctrl+Z)
  Formations.dm       the same for an attack on a pool of foes (A, then a foe: all of its kind near it; a box)
  Comfort.dm          the undo of an attack order
  HUD.dm              the HUD command "chatline" and RmChatLine (the old verbs' rules: muted, ignore lists, world chat
                      off, the shout cooldown)
  Actions.dm          the action list's keys (the Controls list and the tooltips' keycaps)
  border-controls.json  the same for the border controls
Exact-match edits, idempotent, Latin-1 safe.
    python3 tools/rts_feel/keys/apply_keys.py <game folder>"""
import os, sys, tempfile
from pathlib import Path


def elem(name, command):
    return f'\telem \n\t\tname = "{name}"\n\t\tcommand = "{command}"\n\t\tis-disabled = false\n'


# the macros that come off the keys (their commands stay in the menus): key, command
GONE = [('W', 'SendMSG'), ('S', 'WorldSay'), ('D', 'DeclareLeader'), ('Y', 'GMChat'), ('U', 'UnitSay'),
        ('L', 'WorldChat'), ('-', 'ClanChat'), ('B', 'Test'), ('R', 'Restart')]

EDITS = {
'skin.dmf': [
    (elem('C', 'GetCords'), elem('C', 'Remaster-3D-Key \\"c\\"')),
    (elem('X', 'Emote'), elem('X', 'Remaster-3D-Key \\"x\\"')),
    (elem('ESCAPE', 'Remaster-3D-Key \\"escape\\"'),
     elem('ESCAPE', 'Remaster-3D-Key \\"escape\\"') + elem('RETURN', 'Remaster-3D-Key \\"enter\\"')),
],
'Code/Remastered/Attack.dm': [
("""	if(client && (k in list("q", "e", "n", "north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest", "escape"))) src << output(k, "mapwindow.hud:key3d")""",
"""	// c (cutaway), x (x-ray) and enter (the chat line) are the page's keys too (rts-feel 2026-10-25: one key map)
	if(client && (k in list("q", "e", "n", "north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest", "escape", "c", "x", "enter"))) src << output(k, "mapwindow.hud:key3d")"""),
("""		RM = RmReachFor(U, list(T))
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || M.HP <= 0 || RemasterIsSiege(M)) continue""",
"""		RM = RmReachFor(U, list(T))
	var/list/undo = list()   // Ctrl+Z takes the order back (Comfort.dm)
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || M.HP <= 0 || RemasterIsSiege(M)) continue"""),
("""		M.remaster_attack = K
		M.remaster_push_step = 1""",
"""		M.remaster_attack = K
		undo += list(list(M, "\\ref[K]"))
		M.remaster_push_step = 1"""),
("""	if(n)
		if(remaster_3d) Remaster3DMovesPushSoon()   // the first step on screen a tick after the order (View3D.dm)
		RemasterNotice(E ? "Attack! [n] going for""",
"""	if(n)
		if(remaster_3d) Remaster3DMovesPushSoon()   // the first step on screen a tick after the order (View3D.dm)
		if(length(undo)) RemasterUndoPush(list("type"="attack", "pairs"=undo))
		RemasterNotice(E ? "Attack! [n] going for"""),
],
'Code/Remastered/Formations.dm': [   # the attack on a pool of foes (A, then a foe: all of its kind near it; or a box)
("""	var/datum/rm_reach/RM = RmReachFor(U, pool)
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || !(M in UnitList) || M.HP <= 0 || M.GoingToDie || RemasterIsSiege(M)) continue""",
"""	var/datum/rm_reach/RM = RmReachFor(U, pool)
	var/list/undo = list()   // Ctrl+Z takes the order back (Comfort.dm)
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || !(M in UnitList) || M.HP <= 0 || M.GoingToDie || RemasterIsSiege(M)) continue"""),
("""		RmFirstTick(M, K, n + 1)   // its first step this tick, as a move's (the first RM_FIRST_NOW of them; Formations.dm)
		n++""",
"""		RmFirstTick(M, K, n + 1)   // its first step this tick, as a move's (the first RM_FIRST_NOW of them; Formations.dm)
		undo += list(list(M, "\\ref[K]"))
		n++"""),
("""	if(n)
		if(remaster_3d) Remaster3DMovesPushSoon()
		RemasterNotice("Attack! [n] going for [length(pool) - out] foe\\s""",
"""	if(n)
		if(remaster_3d) Remaster3DMovesPushSoon()
		RemasterUndoPush(list("type"="attack", "pairs"=undo))
		RemasterNotice("Attack! [n] going for [length(pool) - out] foe\\s"""),
],
'Code/Remastered/Comfort.dm': [
("""			RemasterNotice(n ? "Undone: the last order for [n] unit[n == 1 ? "" : "s"]." : "That order already finished.")
			return n
	return 0
""",
"""			RemasterNotice(n ? "Undone: the last order for [n] unit[n == 1 ? "" : "s"]." : "That order already finished.")
			return n
		if("attack")   // an attack or attack-move (Attack.dm), stopped where it's still the same one
			var/n = 0
			for(var/list/PR in E["pairs"])
				var/mob/Monsters/M = PR[1]
				if(!M || M.Owner != src || !M.remaster_attack || "\\ref[M.remaster_attack]" != PR[2]) continue
				M.RemasterAttackStop()
				n++
			RemasterNotice(n ? "Undone: the attack for [n] unit[n == 1 ? "" : "s"]." : "That attack already finished.")
			return n
	return 0
"""),
],
'Code/Remastered/HUD.dm': [
("""		if("flylevel") RmFlySelection(value == "up")   // the selection's flyers up or down a step, the Sky level too (Flying.dm)
""",
"""		if("flylevel") RmFlySelection(value == "up")   // the selection's flyers up or down a step, the Sky level too (Flying.dm)
		if("chatline") RmChatLine(value)   // the chat line (Enter): shout, /c clan, /w whisper
"""),
("""	SendMSG(recipient, message)

Player/proc/RemasterCoordinates()""",
"""	SendMSG(recipient, message)

// The chat line (Enter; rts-feel 2026-10-25, the user: "enter opens chat box"). Plain text shouts to everyone, as S did
// (Verbs.dm WorldSay); "/c text" goes to the clan (ClanChat); "/w name text" whispers to one player (SendMSG). The
// rules are those verbs': muted, ignore lists, world chat off, the shout cooldown.
Player/proc/RmChatLine(t)
	usr = src
	t = trimtext("[t]")
	if(!t) return 0
	if(Muted)
		src << "You are muted."
		return 0
	var/head = lowertext(copytext(t, 1, 4))
	if(head == "/w ")
		var/list/W = RmChatWhom(trimtext(copytext(t, 4)))
		if(!W)
			RemasterNotice("No one by that name is online. Whisper: /w name message")
			return 0
		if(!W[2])
			RemasterNotice("Write the message after the name: /w [W[1]] hello")
			return 0
		SendMSG(W[1], W[2])
		return 1
	if(head == "/c ")
		t = trimtext(copytext(t, 4))
		if(!t) return 0
		if(Faction == "Player")
			src << "You're not in a clan."
			return 0
		var/s = Safe_Guard(t)
		for(var/mob/M in Players2)
			if(M.Faction == Faction) M << "<b><font color=red>[src] Clanchats:</b><font color=red> [s]"
			else if(M.key == world.host) M << "<b><font color=silver>[Faction] - [src] Clanchats:</b><font color=silver> [s]"
		return 1
	if(WC)
		RemasterNotice("Your world chat is off: World chat on/off in the menu turns it back on.")
		return 0
	if(!CoolDown("OOC", 5))
		src << "Must Wait before speaking again!"
		return 0
	var/s = Safe_Guard(t)
	if(!s) return 0
	for(var/Player/M in Players) if(!M.WC && !(src in M.IgnoreList) && !(ckey in M.IgnoreList))
		M << "<font color=green><strong>OOC: [src]</strong>: [s]</html> <br>"
	return 1

// A whisper's "name message": the other player online whose name (or key) the line starts with, the longest that fits
// (names have spaces), and the rest. list(player, message), or null.
Player/proc/RmChatWhom(rest)
	var/low = lowertext(rest)
	var/mob/whom
	var/best = ""
	for(var/mob/M in Players) if(M != src && (M.client || rm_chat_any))
		for(var/nm in list("[M.name]", "[M.key]"))
			var/l = lowertext(nm)
			if(!length(l) || copytext(low, 1, length(l) + 1) != l) continue
			if(length(low) > length(l) && copytext(low, length(l) + 1, length(l) + 2) != " ") continue
			if(!whom || length(l) > length(best))
				whom = M
				best = l
	return whom ? list(whom, trimtext(copytext(rest, length(best) + 1))) : null

var/rm_chat_any = 0   // tests: players without a client count as online (tools/rts_feel/keys/keys_check.dm)

Player/proc/RemasterCoordinates()"""),
],
'Code/Remastered/Actions.dm': [
("""		// keys as the skin binds them today (rts-feel 2026-10-23): N faces the 3D camera north, A is Attack, Q/E turn the
		// camera and Ctrl+A selects all, so Rename, Select nearby and Waypoint have no key of their own""",
"""		// keys as the skin binds them today (rts-feel 2026-10-23): N faces the 3D camera north, A is Attack, Q/E turn the
		// camera and Ctrl+A selects all, so Rename, Select nearby and Waypoint have no key of their own. One key map
		// (rts-feel 2026-10-25): U, X, D, B, C, G, R, S, W, L and - aren't these commands' keys any more (Enter's chat
		// line shouts, whispers and clan-chats); the menus keep them"""),
('list("unitsay", "Speak through a unit", "U", 1, null)', 'list("unitsay", "Speak through a unit", null, 1, null)'),
('list("emote", "Unit emote", "X", 1, null)', 'list("emote", "Unit emote", null, 1, null)'),
('list("leader", "Declare a king/queen", "D", 1, null)', 'list("leader", "Declare a king/queen", null, 1, null)'),
('list("build", "Build menu (needs stone or wood)", "B", 0, /obj/Hud/Build)', 'list("build", "Build menu (needs stone or wood)", null, 0, /obj/Hud/Build)'),
('list("coords", "Show my coordinates", "C", 0, /obj/Hud/Cords)', 'list("coords", "Show my coordinates", null, 0, /obj/Hud/Cords)'),
('list("warp", "Go to coordinates", "G", 0, /obj/Hud/Warp)', 'list("warp", "Go to coordinates", null, 0, /obj/Hud/Warp)'),
('list("race", "Choose your people / start over", "R", 0, /obj/Hud/Restart)', 'list("race", "Choose your people / start over", null, 0, /obj/Hud/Restart)'),
('list("say", "Say to the world", "S", 0, /obj/Hud/Say)', 'list("say", "Say to the world", "Enter", 0, /obj/Hud/Say)'),
('list("msg", "Message a player", "W", 0, /obj/Hud/MSG)', 'list("msg", "Message a player", null, 0, /obj/Hud/MSG)'),
('list("worldchat", "World chat on/off", "L", 0, null)', 'list("worldchat", "World chat on/off", null, 0, null)'),
('list("clanchat", "Clan chat", "-", 0, null)', 'list("clanchat", "Clan chat", null, 0, null)'),
],
}

# border-controls.json: the key of each control (by its id), and say's description
CONTROLS = {'race': ('"R"', 'null'), 'msg': ('"W"', 'null'), 'say': ('"S"', '"Enter"'), 'build': ('"B"', 'null'),
            'coords': ('"C"', 'null'), 'warp': ('"G"', 'null')}
SAY_OLD = '"description": "Send a message to world chat, subject to the game’s chat rules and cooldown.",'
SAY_NEW = ('"description": "Send a message to world chat, subject to the game’s chat rules and cooldown. Enter opens the '
           'chat line: plain text to everyone, /c to your clan, /w name to whisper.",')


def write(p, t):
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.keys-'); os.write(fd, t.encode('latin-1' if p.suffix != '.json' else 'utf-8')); os.close(fd)
    os.chmod(tmp, p.stat().st_mode); os.replace(tmp, p)


def skin_drops(t):
    done = 0
    for key, cmd in GONE:
        b = elem(key, cmd)
        n = t.count(b)
        if n == 0: continue
        if n != 1: sys.exit(f'skin.dmf: {n} copies of the {key} macro')
        i = t.index(b); j = i + len(b)
        if t[j:j + 1] == '\n': j += 1    # and the blank line after it
        t = t[:i] + t[j:]; done += 1
    return t, done


def main(game):
    game = Path(game)
    for rel, edits in EDITS.items():
        p = game/rel
        t = p.read_bytes().decode('latin-1')
        done = 0
        if rel == 'skin.dmf': t, done = skin_drops(t)
        for old, new in edits:
            if new in t: continue
            if t.count(old) != 1: sys.exit(f'{p}: no unique match for:\n{old[:160]}')
            t = t.replace(old, new); done += 1
        if done: write(p, t)
        print(f'{rel}: {done} edit(s)' if done else f'{rel}: already applied')
    p = game/'Interface/border-controls.json'
    t = p.read_text(encoding='utf-8'); done = 0
    for cid, (old, new) in CONTROLS.items():
        a = t.index(f'"id": "{cid}",'); e = t.index('\n  }', a)
        blk = t[a:e]
        if f'"key": {new},' in blk: continue
        if blk.count(f'"key": {old},') != 1: sys.exit(f'border-controls.json: {cid} has no "key": {old}')
        t = t[:a] + blk.replace(f'"key": {old},', f'"key": {new},') + t[e:]; done += 1
    if SAY_NEW not in t:
        if t.count(SAY_OLD) != 1: sys.exit("border-controls.json: say's description not found")
        t = t.replace(SAY_OLD, SAY_NEW); done += 1
    if done: write(p, t)
    print(f'Interface/border-controls.json: {done} edit(s)' if done else 'Interface/border-controls.json: already applied')


if __name__ == '__main__':
    main(sys.argv[1])
