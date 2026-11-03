#!/usr/bin/env python3
"""The 2006 letter keys off the keyboard (rts-feel, 2026-10-25; the playtest audit's launch blocker 3). The user: "take
the 2006 letter keys off the keyboard (R, W, S, D, Y, U, L, -, B and the rest), C and X do cutaway and x-ray, W/S/D
don't pan, A stays as it is. Leave the chat box for later." Every command stays in the menus (Controls, All commands).
Server and skin half (the page's half: apply_keys_page.py; the chat box, for later: chat-later/).
  skin.dmf              the W S D Y U L - B R H J K M O T V = / macros go; C and X go to the page (Remaster-3D-Key)
  Attack.dm             Remaster-3D-Key passes c and x on to the page
  Actions.dm            those commands' keys come off the action list (the Controls list and the tooltips' keycaps)
  border-controls.json  the same for the border controls
Exact-match edits, idempotent, Latin-1 safe.
    python3 tools/rts_feel/keys/apply_keys.py <game folder>"""
import os, sys, tempfile
from pathlib import Path


def elem(name, command):
    return f'\telem \n\t\tname = "{name}"\n\t\tcommand = "{command}"\n\t\tis-disabled = false\n'


# the macros that come off the keys (their commands stay in the menus): key, command
GONE = [('W', 'SendMSG'), ('S', 'WorldSay'), ('D', 'DeclareLeader'), ('Y', 'GMChat'), ('U', 'UnitSay'),
        ('L', 'WorldChat'), ('-', 'ClanChat'), ('B', 'Test'), ('R', 'Restart'), ('H', 'Who'), ('J', 'Guard'),
        ('K', 'Legends'), ('M', 'ViewBug'), ('O', 'MusicOff'), ('T', 'Update'), ('V', 'Reportabug'),
        ('=', 'PlaceTapestry'), ('/', 'Developer-Logs')]

EDITS = {
'skin.dmf': [
    (elem('C', 'GetCords'), elem('C', 'Remaster-3D-Key \\"c\\"')),
    (elem('X', 'Emote'), elem('X', 'Remaster-3D-Key \\"x\\"')),
],
'Code/Remastered/Attack.dm': [
("""	if(client && (k in list("q", "e", "n", "north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest", "escape"))) src << output(k, "mapwindow.hud:key3d")""",
"""	// c (cutaway) and x (x-ray) are the page's keys too (rts-feel 2026-10-25: the 2006 letter keys off the keyboard)
	if(client && (k in list("q", "e", "n", "north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest", "escape", "c", "x"))) src << output(k, "mapwindow.hud:key3d")"""),
],
'Code/Remastered/Actions.dm': [
("""		// keys as the skin binds them today (rts-feel 2026-10-23): N faces the 3D camera north, A is Attack, Q/E turn the
		// camera and Ctrl+A selects all, so Rename, Select nearby and Waypoint have no key of their own""",
"""		// keys as the skin binds them today (rts-feel 2026-10-23): N faces the 3D camera north, A is Attack, Q/E turn the
		// camera and Ctrl+A selects all, so Rename, Select nearby and Waypoint have no key of their own. The 2006 letter
		// keys are off the keyboard (rts-feel 2026-10-25, the user's call): these commands are in the menus only"""),
('list("guard", "Guard / guard rules", "J", 1, null)', 'list("guard", "Guard / guard rules", null, 1, null)'),
('list("unitsay", "Speak through a unit", "U", 1, null)', 'list("unitsay", "Speak through a unit", null, 1, null)'),
('list("emote", "Unit emote", "X", 1, null)', 'list("emote", "Unit emote", null, 1, null)'),
('list("leader", "Declare a king/queen", "D", 1, null)', 'list("leader", "Declare a king/queen", null, 1, null)'),
('list("build", "Build menu (needs stone or wood)", "B", 0, /obj/Hud/Build)', 'list("build", "Build menu (needs stone or wood)", null, 0, /obj/Hud/Build)'),
('list("coords", "Show my coordinates", "C", 0, /obj/Hud/Cords)', 'list("coords", "Show my coordinates", null, 0, /obj/Hud/Cords)'),
('list("warp", "Go to coordinates", "G", 0, /obj/Hud/Warp)', 'list("warp", "Go to coordinates", null, 0, /obj/Hud/Warp)'),
('list("race", "Choose your people / start over", "R", 0, /obj/Hud/Restart)', 'list("race", "Choose your people / start over", null, 0, /obj/Hud/Restart)'),
('list("say", "Say to the world", "S", 0, /obj/Hud/Say)', 'list("say", "Say to the world", null, 0, /obj/Hud/Say)'),
('list("msg", "Message a player", "W", 0, /obj/Hud/MSG)', 'list("msg", "Message a player", null, 0, /obj/Hud/MSG)'),
('list("worldchat", "World chat on/off", "L", 0, null)', 'list("worldchat", "World chat on/off", null, 0, null)'),
('list("clanchat", "Clan chat", "-", 0, null)', 'list("clanchat", "Clan chat", null, 0, null)'),
('list("who", "Who is online", "H", 0, /obj/Hud/Who)', 'list("who", "Who is online", null, 0, /obj/Hud/Who)'),
('list("legends", "Legends of the world", "K", 0, null)', 'list("legends", "Legends of the world", null, 0, null)'),
('list("updates", "Game updates", "T", 0, /obj/Hud/Updates)', 'list("updates", "Game updates", null, 0, /obj/Hud/Updates)'),
('list("music", "Music off", "O", 0, null)', 'list("music", "Music off", null, 0, null)'),
],
}

# border-controls.json: the key each control (by its id) loses
CONTROLS = {'race': '"R"', 'msg': '"W"', 'say': '"S"', 'build': '"B"', 'who': '"H"', 'coords': '"C"', 'warp': '"G"',
            'updates': '"T"'}


def write(p, t, enc):
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.keys-'); os.write(fd, t.encode(enc)); os.close(fd)
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
        if done: write(p, t, 'latin-1')
        print(f'{rel}: {done} edit(s)' if done else f'{rel}: already applied')
    p = game/'Interface/border-controls.json'
    t = p.read_text(encoding='utf-8'); done = 0
    for cid, old in CONTROLS.items():
        a = t.index(f'"id": "{cid}",'); e = t.index('\n  }', a)
        blk = t[a:e]
        if '"key": null,' in blk: continue
        if blk.count(f'"key": {old},') != 1: sys.exit(f'border-controls.json: {cid} has no "key": {old}')
        t = t[:a] + blk.replace(f'"key": {old},', '"key": null,') + t[e:]; done += 1
    if done: write(p, t, 'utf-8')
    print(f'Interface/border-controls.json: {done} edit(s)' if done else 'Interface/border-controls.json: already applied')


if __name__ == '__main__':
    main(sys.argv[1])
