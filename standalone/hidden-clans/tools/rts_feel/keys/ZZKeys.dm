// The 2006 letter keys in the real client (rts-feel, 2026-10-25; tools/rts_feel/real_feel.py --only keys). Temporary test
// copy only, after the game's own code. Each old command a letter key ran logs CK|verb|<name> and does nothing else, so a
// key that still runs one shows in the log and no prompt holds the keyboard for the next key.
mob/SendMSG(mob/M, msg)
	world.log << "CK|verb|SendMSG"
mob/WorldSay()
	world.log << "CK|verb|WorldSay"
mob/DeclareLeader()
	world.log << "CK|verb|DeclareLeader"
mob/GMChat()
	world.log << "CK|verb|GMChat"
mob/UnitSay(T)
	world.log << "CK|verb|UnitSay"
mob/WorldChat()
	world.log << "CK|verb|WorldChat"
mob/ClanChat()
	world.log << "CK|verb|ClanChat"
mob/Test()
	world.log << "CK|verb|Test"
mob/Restart()
	world.log << "CK|verb|Restart"
mob/Who()
	world.log << "CK|verb|Who"
mob/Guard()
	world.log << "CK|verb|Guard"
mob/Legends()
	world.log << "CK|verb|Legends"
mob/MusicOff()
	world.log << "CK|verb|MusicOff"
mob/Update()
	world.log << "CK|verb|Update"
mob/PlaceTapestry()
	world.log << "CK|verb|PlaceTapestry"
mob/GetCords()
	world.log << "CK|verb|GetCords"
mob/Emote(T)
	world.log << "CK|verb|Emote"
