// The sky job, parts 2 and 3 (rts-feel, 2026-10-25; tools/rts_feel/sky/apply_sky2.py). In the obey arena with 3 layers
// (tools/check_arena.py --test sky_check2.dm --entry Sk2Run --maxz 3); the Sky level is open sky. Through the HUD's own
// commands (RemasterTouchCommand: "unitability", "flylevel", "layer", "worldmaplayer") and the , key's ZUp.
//   G. a flyer at its top height: Fly higher takes it to the Sky level, lowest height; Fly lower brings it back at top
//   H. three flyers and two walkers, the group's Fly higher: only the flyers climb
//   I. a flyer flying somewhere climbs on the way: it goes on to the same spot up there
//   J. the Sky earned: shut with no unit up there (the HUD says so; "layer", the world map and the , key refused); open
//      once a flyer is up; the view back on the surface when the last one comes down
//   K. a camera locked on a flyer goes up with it
//   L. the host's override opens it with nobody up there
obj/Hud/ZUp/SkTest/New()   // the , key's button without a client (its own New puts it on a client's screen)
	return

proc/Sk2Sky()
	for(var/turf/T in block(locate(1, 1, 3), locate(world.maxx, world.maxy, 3)))
		T.icon_state = "Sky"
		T.name = "Sky"
		T.Content = "Sky"
		T.density = 0

proc/Sk2Flyer(Player/P, x, y)
	var/mob/Monsters/M = ObHuman(P, x, y, 1, 0)
	M.Flying = 1
	M.rm_fly_level = length(RmFlyHeights(M))   // at its top height
	return M

proc/Sk2Has(Player/P, mob/Monsters/M, name)
	for(var/list/A in P.RemasterAbilities(M)) if(A[1] == "Flying" && A[2] == name) return 1
	return 0

proc/Sk2Ticks(Player/P, n)
	for(var/t = 0, t < n, t += REMASTER_TRACK_DELAY)
		usr = P
		ObTick(P)
		P.RemasterPlayModeTick()
		sleep(REMASTER_TRACK_DELAY)

proc/Sk2Run()
	sleep(30)
	remaster_fog = 0
	var/Player/P = new(locate(60, 50, 1))
	P.UnitList = list()
	P.key = "skycheck2"
	Players += P
	usr = P
	Sk2Sky()
	// J (first part): nobody up there
	var/list/hud = P.RemasterHUDData()
	var/open0 = P.RmSkyOpen()
	P.RemasterTouchCommand("layer", "3")
	var/z_layer = P.z
	P.RemasterTouchCommand("worldmaplayer", "3")
	var/wm = P.remaster_world_map_z
	usr = P
	var/obj/Hud/ZUp/Z = new /obj/Hud/ZUp(new /datum/remaster_screen)   // as the , key's action makes it (Actions.dm)
	Z.DblClick()
	var/z_key = P.z
	world.log << "CK|J1 the Sky shut with no unit up there|[!open0 && !hud["sky"] && z_layer == 1 && wm != 3 && z_key == 1]|open [open0], HUD sky [hud["sky"]], after layer 3: z [z_layer], world map layer [wm], after the , key: z [z_key]; notice '[P.remaster_notice]'"
	// J0: a walker on an ordinary mountain top (layer 3, a few blocks up) doesn't earn the Sky
	var/turf/PK = locate(90, 90, 3)
	PK.icon_state = "Peak"
	PK.name = "MountainPeak"
	PK.Content = null
	PK.Content3 = "Peak"
	ObRock(90, 90, 1)
	var/mob/Monsters/MT = ObHuman(P, 90, 90, 3, 0)
	P.rm_sky_at = -100
	var/open_top = P.RmSkyOpen()
	world.log << "CK|J0 a unit on an ordinary mountain top doesn't earn the Sky|[!open_top]|on [MT.x],[MT.y],[MT.z] feet [RemasterFeetOf(MT)]: open [open_top]"
	del(MT)
	P.rm_sky_at = -100
	// G
	var/mob/Monsters/F = Sk2Flyer(P, 30, 30)
	var/ref = RemasterUIRef(F)
	var/up_shown = Sk2Has(P, F, "Fly higher")
	P.Selected = list(F)
	P.RemasterTouchCommand("unitability", "[ref]|Flying|Fly higher")
	var/at_up = "[F.x],[F.y],[F.z] level [F.rm_fly_level], [RmFlyHeight(F)] over the sky plane"
	var/up_ok = F.z == 3 && F.x == 30 && F.y == 30 && F.rm_fly_level == 1 && RmFlyHeight(F) >= 3   // over a 12-high sky peak's top (2 over the plane)
	var/down_shown = Sk2Has(P, F, "Fly lower")
	P.RemasterTouchCommand("unitability", "[ref]|Flying|Fly lower")
	var/down_ok = F.z == 1 && F.rm_fly_level == length(RmFlyHeights(F))
	world.log << "CK|G Fly higher to the Sky level and Fly lower back|[up_shown && up_ok && down_shown && down_ok]|shown at top height: [up_shown]; up: [at_up]; Fly lower shown up there: [down_shown]; down: [F.x],[F.y],[F.z] level [F.rm_fly_level]"
	// G, the top of the sky: no higher
	P.RemasterTouchCommand("unitability", "[ref]|Flying|Fly higher")
	F.rm_fly_level = length(RmFlyHeights(F))
	var/top_no = !Sk2Has(P, F, "Fly higher")
	F.rm_fly_level = 1
	P.RemasterTouchCommand("unitability", "[ref]|Flying|Fly lower")
	world.log << "CK|G at its top sky height there's no higher|[top_no && F.z == 1]|no Fly higher at the top: [top_no]; back down: z [F.z]"
	// H
	var/list/G = list(Sk2Flyer(P, 40, 30), Sk2Flyer(P, 41, 30), Sk2Flyer(P, 42, 30), ObHuman(P, 43, 30, 1, 0), ObHuman(P, 44, 30, 1, 0))
	P.Selected = G.Copy()
	P.RemasterTouchCommand("flylevel", "up")
	var/list/zs = list()
	var/h_ok = 1
	for(var/mob/Monsters/M in G)
		zs += "[M.Flying ? "flyer" : "walker"] z [M.z]"
		if(M.Flying ? M.z != 3 : M.z != 1) h_ok = 0
	world.log << "CK|H a mixed group's Fly higher: only the flyers climb|[h_ok]|[jointext(zs, ", ")]"
	P.RemasterTouchCommand("flylevel", "down")
	for(var/mob/Monsters/M in G) if(M.z != 1) h_ok = 0
	world.log << "CK|H and the group's Fly lower brings them back|[h_ok]|[jointext(zs, ", ")] -> all z 1: [h_ok]"
	// I
	var/mob/Monsters/W = Sk2Flyer(P, 30, 60)
	ObClick(P, list(W), locate(45, 60, 1))
	Sk2Ticks(P, 15)
	var/mid = "[W.x],[W.y],[W.z]"
	P.Selected = list(W)
	P.RemasterTouchCommand("unitability", "[RemasterUIRef(W)]|Flying|Fly higher")
	Sk2Ticks(P, 120)
	world.log << "CK|I a flyer climbing on its way goes on to the same spot up there|[W.x == 45 && W.y == 60 && W.z == 3]|at [mid] when it climbed; now [W.x],[W.y],[W.z] '[W.remaster_order_status]'"
	// J (second part): open with one up there; shut again, and the view back down, when it comes down
	var/open1 = P.RmSkyOpen()
	var/list/hud1 = P.RemasterHUDData()
	P.RemasterTouchCommand("layer", "3")
	var/z_up = P.z
	P.Selected = list(W)
	P.RemasterTouchCommand("unitability", "[RemasterUIRef(W)]|Flying|Fly lower")
	Sk2Ticks(P, 20)
	world.log << "CK|J2 open once one is up there, the view back on the surface when it comes down|[open1 && hud1["sky"] && z_up == 3 && P.z == 1]|open [open1], HUD sky [hud1["sky"]], after layer 3: z [z_up]; once it came down: z [P.z]; notice '[P.remaster_notice]'"
	// K
	var/mob/Monsters/L = Sk2Flyer(P, 70, 70)
	P.loc = locate(70, 70, 1)
	P.remaster_lock = RemasterUIRef(L)
	P.Selected = list(L)
	P.RemasterTouchCommand("unitability", "[RemasterUIRef(L)]|Flying|Fly higher")
	Sk2Ticks(P, 10)
	var/k_up = P.z
	P.RemasterTouchCommand("unitability", "[RemasterUIRef(L)]|Flying|Fly lower")
	Sk2Ticks(P, 10)
	world.log << "CK|K a locked camera goes up and down with its flyer|[k_up == 3 && P.z == 1]|up: z [k_up]; down: z [P.z]"
	P.remaster_lock = null
	// J3: the camera on the Sky with none of theirs up there (an old save, a login): back on the surface on the next tick;
	// the . key (ZDown) from the Sky still goes down
	P.remaster_lock = null
	P.loc = locate(50, 50, 3)
	Sk2Ticks(P, 5)
	var/z_saved = P.z
	P.loc = locate(50, 50, 3)
	usr = P
	var/obj/Hud/ZDown/D = new /obj/Hud/ZDown(new /datum/remaster_screen)
	D.DblClick()
	world.log << "CK|J3 on the Sky with no unit there (a save, a login): back on the surface; the . key still goes down|[z_saved == 1 && P.z == 1]|after a tick: z [z_saved]; after . from the Sky: z [P.z]"
	// M: a dragon, "Surface low, Sky high": 3, 6, 9 over the surface, then up there 12, 22, 32 from the surface; and back down
	var/mob/Monsters/Dr = new /mob/Monsters/Dragon(locate(80, 20, 1))
	Dr.ChangeOwnership(P)
	Dr.Flying = 1
	Dr.rm_fly_level = 1
	var/dref = RemasterUIRef(Dr)
	P.Selected = list(Dr)
	var/list/seen = list("[Dr.z]:[(Dr.z == 3 ? RM_SKY_H : 0) + RmFlyHeight(Dr)]")
	for(var/i = 1, i <= 5, i++)
		P.RemasterTouchCommand("unitability", "[dref]|Flying|Fly higher")
		seen += "[Dr.z]:[(Dr.z == 3 ? RM_SKY_H : 0) + RmFlyHeight(Dr)]"
	var/top_none = !Sk2Has(P, Dr, "Fly higher")
	for(var/i = 1, i <= 5, i++)
		P.RemasterTouchCommand("unitability", "[dref]|Flying|Fly lower")
		seen += "[Dr.z]:[(Dr.z == 3 ? RM_SKY_H : 0) + RmFlyHeight(Dr)]"
	var/want = "1:3,1:6,1:9,3:12,3:22,3:32,3:22,3:12,1:9,1:6,1:3"
	world.log << "CK|M a dragon climbs 3, 6, 9, then up there 12, 22, 32 (from the surface), and back down|[jointext(seen, ",") == want && top_none]|z:height from the surface: [jointext(seen, ",")]; no Fly higher at the top: [top_none]"
	del(Dr)
	// L
	rm_sky_open_all = 1
	P.rm_sky_at = -100
	P.RemasterTouchCommand("layer", "3")
	var/z_host = P.z
	rm_sky_open_all = 0
	P.RemasterTouchCommand("layer", "1")
	world.log << "CK|L the host's override opens it with nobody up there|[z_host == 3]|after layer 3: z [z_host]"
	world.log << "CK|complete"
