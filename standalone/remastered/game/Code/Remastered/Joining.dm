// Joining a hosted world from another Mac. The launcher's "Host for friends" writes
// the password to join-password and this Mac's network addresses to host-addresses
// in the world folder (mac-app/launch.zsh); solo play removes both. Players
// connecting from another computer are asked for the password (the joining Mac's
// launcher answers it for them) and turned away after two wrong tries. The host
// (host-name) is never asked.

proc/RemasterJoinPassword()
	if(!fexists("join-password")) return null
	var/p = trimtext(file2text("join-password"))
	return length(p) ? p : null

proc/RemasterHostAddresses()
	if(!fexists("host-addresses")) return null
	. = list()
	for(var/line in splittext(file2text("host-addresses"), "\n"))
		line = trimtext(line)
		if(length(line)) . += line

proc/RemasterLocalAddress(a)
	return !a || a == "127.0.0.1" || a == "::1" || a == "localhost"

Player/proc/RemasterJoinGate()
	var/want = RemasterJoinPassword()
	if(!want || !client) return 1
	// Only the host (named in host-name by the launcher) skips the password; without
	// that file, a client on this Mac does.
	var/host = fexists("host-name") ? trimtext(file2text("host-name")) : null
	// A player in a web browser (the engine's web link, client.connection "web") is never the host: anyone can type the
	// host's name in the lobby (U4, reports/u4-web-1030).
	if(client.connection != "web" && (host ? RemasterWho() == host : RemasterLocalAddress(client.address))) return 1
	for(var/tries = 1, tries <= 2, tries++)
		var/got = input(src, tries == 1 ? "This world asks for a password." : "Wrong password. Try once more.", "Join password") as text|null
		if(!client) return 0
		if(got && trimtext(got) == want) return 1
	src << "<b>Wrong password. Ask the host for it and join again.</b>"
	world.log << "Join refused (wrong password) from [client.address]"
	spawn(5) if(client) del(client)
	return 0

Player/Login()
	if(RmModBanGate()) return   // banned: told why and until when, and gone before anything loads (Moderation.dm)
	if(RmModFullGate()) return  // the player cap: a full world turns newcomers away the same way (Moderation.dm)
	if(!RemasterJoinGate()) return
	// A player coming back to their mob brings a fresh client: the HUD page must be sent again.
	remaster_hud_started = 0
	remaster_hud_ready = 0
	// ... and every file the old one was sent (11-01: a guest village handed back to its browser drew no people: their
	// pictures, the item icons, the ground and the models counted as sent to the browser before). Sounds, fonts and the
	// 3D gear go by client already (Audio.dm, Gear3D.dm).
	remaster_portraits = null
	remaster_item_icons_sent = null
	remaster_3d_sent = null
	remaster_3d_models_sent = null
	remaster_3d_textures_sent = 0
	remaster_map_sent = 0
	remaster_border_resources = null
	..()
	RemasterTakeName()

// Each player is known by their login name, and so are their units ("{Alice} Grak"):
// the player object used to stay "Player", so in a shared world every unit looked alike.
Player/proc/RemasterTakeName()
	var/who = RemasterHouse()        // the house name, once the player has chosen one (Realms.dm)
	if(!who || name == who) return
	var/old = "{[name]} "
	name = who
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && findtext(M.name, old) == 1)
		M.name = "{[who]} " + copytext(M.name, length(old) + 1)

// The player hosting this world (named in host-name by the launcher); without that
// file every player counts (solo play, tests).
Player/proc/RemasterIsHost()
	if(RmPublicWorld()) return 0   // a public server has no host: the owner and helpers act as Admins (Moderation.dm)
	if(!fexists("host-name")) return 1
	// a player in a web browser is never the host where one is named: anyone can type the host's name in the lobby
	if(client && client.connection == "web") return 0
	return RemasterWho() == trimtext(file2text("host-name"))

// A public server (tools/public_host.py sets RM_PUBLIC=1): nobody is the host, nobody pauses the world or changes
// (the engine's web link reads the visitor's address behind the proxy and limits floods there: engine-web-harden, 10-31)
// (and answers the proxy for any Host, refusing other computers, with https sign-in links: engine-web-public-host)
// its speed or fog for everyone.
var/rm_public_world = -1
proc/RmPublicWorld()
	if(rm_public_world < 0) rm_public_world = world.GetConfig("env", "RM_PUBLIC") == "1"
	return rm_public_world

// For the HUD: the address friends use to join this world, when hosting.
proc/RemasterHostingData()
	var/list/A = RemasterHostAddresses()
	if(!A) return null
	var/n = 0
	for(var/Player/P in world) if(P.client) n++
	return list("addresses"=A, "players"=n)
