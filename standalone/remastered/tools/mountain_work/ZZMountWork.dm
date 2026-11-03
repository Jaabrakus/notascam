// Mountain work (temporary game copy only, tools/mountain_work/real_mount.py): a rock massif with peaks over it beside
// the company, a tree, and the steps the runner asks for in mw-scene.txt. "probe N" puts MWPROBE|N|name:x,y,h;... in
// the notice for the page hook (mw_hook.js) to answer with where those world points are on screen (h < 0: -1 the
// ground there, -2 the rock's top). Work on the massif is sped up: each blow nearly breaks its block.
var/mw_scene = ""
var/turf/mw_site
var/list/mw_rock = list()
var/list/mw_pts = list()       // name -> "x,y,h"
var/list/mw_tiles = list()     // name -> turf, for the state lines
var/mw_fast = 1                // work on the massif sped up (the runner's checks); "slow" for a player trying it

world/New()
	..()
	spawn(50) MwLoop()

proc/MwP()
	for(var/Player/P in world) if(P.client) return P

proc/MwLoop()
	while(1)
		sleep(1)
		night = 0
		if(mw_fast) for(var/turf/T in mw_rock)
			if(T.density && T.HP > 1) T.HP = 1
			if(T.remaster_roof_hp > 1) T.remaster_roof_hp = 1
			if(T.remaster_top_hp > 1) T.remaster_top_hp = 1
		if(!fexists("mw-scene.txt")) continue
		var/s = trimtext(file2text("mw-scene.txt"))
		if(!s || s == mw_scene) continue
		mw_scene = s
		var/Player/P = MwP()
		if(P) spawn(0) MwRun(P, s)

proc/MwAt(dx, dy, z = 1)
	return locate(mw_site.x + dx, mw_site.y + dy, z)

proc/MwTileLine(name, turf/T)
	var/turf/U = locate(T.x, T.y, 3)
	return "MW|tile|[name]|[T.x],[T.y]|dense=[T.density]|blocks=[RemasterBlocksAt(T)]|topcut=[T.remaster_topcut]|holes=[T.remaster_holes]|slope=[T.remaster_slope]|dug=[T.remaster_dug][T.remaster_dug_top]|roof=[T.remaster_roof]|ceil=[T.remaster_ceil]|carve=[T.remaster_carve]/[T.remaster_carve_n]|plan=[T.remaster_carve_plan ? 1 : 0]|icon=[T.icon_state]|up=[U ? U.icon_state : "-"]"

proc/MwUnitLine(Player/P, mob/Monsters/M)
	var/datum/remaster_order/O = M.remaster_active
	var/list/q = list()
	for(var/datum/remaster_order/Q in M.remaster_orders) q += Q.kind
	return "MW|unit|[M.name]|ref=[RemasterUIRef(M)]|at=[M.x],[M.y],[M.z]|sel=[(M in P.Selected) ? 1 : 0]|active=[O ? O.kind : "-"]|goal=[O && O.target ? "[O.target:x],[O.target:y],[O.target:z]" : "-"]|feet=[M.z == 3 ? RemasterFeetOf(M) : 0]|block=[O ? O.block : "-"]|queued=[jointext(q, ",")]|status=[M.remaster_order_status]"

proc/MwRun(Player/P, s)
	var/list/a = splittext(s, " ")
	var/list/U = list()
	for(var/mob/Monsters/M in P.UnitList) if(M.HP > 0) U += M
	usr = P
	switch(a[1])
		if("setup")
			var/mob/Monsters/L = U[1]
			mw_site = locate(clamp(L.x, 40, world.maxx - 40), clamp(L.y, 40, world.maxy - 40), 1)
			for(var/turf/T in block(MwAt(-14, -10), MwAt(14, 16)))
				var/turf/G = new /turf/grounds/grass(T)
				for(var/obj/O in G) if(!istype(O, /obj/Hud)) del(O)
				var/turf/S = new /turf/grounds/Sky(locate(T.x, T.y, 3))
				S.density = 0
			for(var/turf/T in block(MwAt(-40, -40), MwAt(40, 40))) P.RemasterMarkExplored(T)
			P.remaster_explore_version++
			for(var/mob/M in range(16, mw_site)) if(!(M in U) && M != P && !istype(M, /mob/WorkShops)) del(M)
			// the massif: x -6..6, y +2..+9, its south face on row +2; peaks over it
			for(var/dx = -6, dx <= 6, dx++) for(var/dy = 2, dy <= 9, dy++)
				var/turf/R = new /turf/grounds/cavefloor(MwAt(dx, dy))
				R.remaster_vein = ""
				mw_rock += R
				var/turf/K = new /turf/grounds/MountainPeak(MwAt(dx, dy, 3))
				K.density = 0
			new /turf/grounds/Trees/Tree1(MwAt(-4, -3))
			var/turf/TALL = MwAt(-4, 2)   // a tall face, six blocks, for a block out of its middle
			TALL.remaster_blocks = 6
			// a one-block rock at the face to carve a ramp into, a one-block top behind it, a two-block one beside that
			MwAt(2, 2):remaster_blocks = 1
			MwAt(2, 3):remaster_blocks = 1
			MwAt(2, 4):remaster_blocks = 2
			mw_tiles = list("tree"=MwAt(-4, -3), "face0"=MwAt(-2, 2), "ramp"=MwAt(2, 2), "top"=MwAt(2, 3), "dig"=MwAt(2, 4), "face1"=MwAt(-4, 2), "face2"=MwAt(-4, 3))
			mw_pts = list("tree"="[mw_site.x - 4],[mw_site.y - 3],1.0", "face0"="[mw_site.x - 2],[mw_site.y + 1.47],0.5", "rampstart"="[mw_site.x + 2],[mw_site.y + 1.47],0.5",
				"top"="[mw_site.x + 2],[mw_site.y + 3],-2", "dig"="[mw_site.x + 2],[mw_site.y + 4],-2",
				"face1b2"="[mw_site.x - 4],[mw_site.y + 1.47],2.5", "face1b3"="[mw_site.x - 4],[mw_site.y + 1.47],3.5", "ground"="[mw_site.x + 3],[mw_site.y],-1", "rampblk"="[mw_site.x + 2],[mw_site.y + 2],-2", "wallb3"="[mw_site.x],[mw_site.y + 6.53],3.5")
			var/i = 0
			for(var/mob/Monsters/M in U)
				M.loc = MwAt(-1 + i * 2, -1)
				M.destination = null
				M.remaster_care_hold = world.time + 100000
				M.Hunger = 100
				M.Tiredness = 100
				M.MineingSkill = 80
				M.WoodCuttingSkill = 80
				if(!M.RemasterHasTool("Pickaxe")) M.ForcePickUpItem(new /obj/Items/Equipment/Weapon/Picks/PickAxe)
				if(!M.RemasterHasTool("Axe")) M.ForcePickUpItem(new /obj/Items/Equipment/Weapon/Axes/MetalAxe)
				i++
			P.remaster_3d = 1
			P.remaster_cine = null
			P.Selected = list()
			P.loc = MwAt(0, 0)
			world.log << "MW|site|[mw_site.x],[mw_site.y]|units=[length(U)]|gather=[P.remaster_gather]"
			for(var/mob/Monsters/M in U) world.log << "MW|ref|[M.name]|[RemasterUIRef(M)]"
		if("probe")
			var/list/parts = list()
			for(var/k in mw_pts) parts += "[k]:[mw_pts[k]]"
			P.RemasterNotice("MWPROBE|[a[2]]|[jointext(parts, ";")]")
		if("state")
			world.log << "MW|state|[a[2]]|sel=[length(P.Selected)]|gather=[P.remaster_gather]|camera=[P.x],[P.y],[P.z]|notice=[P.remaster_notice]"
			for(var/mob/Monsters/M in U) world.log << MwUnitLine(P, M)
			for(var/k in mw_tiles) world.log << MwTileLine(k, mw_tiles[k])
			var/ramps = 0     // ramps carved round the massif (Plan mode's way up)
			for(var/turf/T in block(MwAt(-8, -2), MwAt(8, 11))) if(RemasterSlopeOn(T)) ramps++
			world.log << "MW|tile|ramps|0,0|n=[ramps]"
		if("select")   // fallback when a real click on a unit missed: "select 1"
			var/mob/Monsters/M = U[text2num(a[2])]
			for(var/mob/Monsters/S in P.Selected.Copy()) S.Deselect(P)
			M.Select(P)
		if("stopall")
			for(var/mob/Monsters/M in U) M.RemasterCancelOrders()
		if("hollow")   // the third unit up on the mountain in a hollow two blocks deep, selected (the cut round it)
			var/turf/HT = MwAt(0, 6)
			HT.remaster_topcut = max(0, RemasterBlocksAt(HT) - 2) + HT.remaster_topcut
			mw_tiles["hollow"] = HT
			mw_tiles["wall"] = MwAt(0, 7)
			var/mob/Monsters/M3 = U[3]
			M3.loc = MwAt(0, 6, 3)
			M3.destination = null
			for(var/mob/Monsters/S in P.Selected.Copy()) S.Deselect(P)
			M3.Select(P)
			P.loc = MwAt(0, 4)
			world.log << "MW|hollow|[RemasterBlocksAt(HT)]|wall=[RemasterBlocksAt(MwAt(0, 7))]"
		if("inside")   // a corridor dug through the massif at block 3 (rows +5..+7 six blocks high), the third unit in it, selected
			for(var/dx = -4, dx <= 4, dx++) for(var/dy = 5, dy <= 7, dy++)
				var/turf/C = MwAt(dx, dy)
				C.remaster_blocks = 6
				C.remaster_topcut = 0
				C.remaster_holes = (dy == 6 && dx >= -3 && dx <= 3) ? (1 << 3) : 0
			mw_tiles["corridor"] = MwAt(2, 6)
			mw_tiles["nearwall"] = MwAt(2, 5)
			mw_pts["wall4"] = "[mw_site.x + 2],[mw_site.y + 5],4.5"   // the near wall beside the corridor's end, over the unit's level
			mw_pts["planA"] = "[mw_site.x - 1],[mw_site.y + 5],3.4"   // Plan mode: the corridor's south wall, level 3 (a slab's top)
			mw_pts["planB"] = "[mw_site.x + 1],[mw_site.y + 5],3.4"
			mw_tiles["pw1"] = MwAt(-1, 5)
			mw_tiles["pw2"] = MwAt(0, 5)
			mw_tiles["pw3"] = MwAt(1, 5)
			mw_pts["inside"] = "[mw_site.x + 2],[mw_site.y + 6.3],3.0"   // the floor's far half: the near wall's stub hides the rest from up here
			var/mob/Monsters/M3 = U[3]
			M3.loc = MwAt(-3, 6, 3)
			M3.remaster_feet = 3
			M3.destination = null
			for(var/mob/Monsters/S in P.Selected.Copy()) S.Deselect(P)
			M3.Select(P)
			P.loc = MwAt(0, 4)
			world.log << "MW|inside|[M3.name]|feet=[RemasterFeetOf(M3)]"
		if("buildsetup")   // Plan mode's Build: a stockpile with stone south-east of the massif, the first unit selected on the ground
			P.remaster_stock_x = mw_site.x + 7; P.remaster_stock_y = mw_site.y - 4; P.remaster_stock_z = 1
			P.remaster_stock_filter = "mixed"
			var/turf/ST = P.RemasterStockpile()
			for(var/n = 1, n <= 12, n++) new /obj/Items/ores/stone(ST)
			for(var/n = 0, n <= 2, n++)
				mw_tiles["bw[n + 1]"] = MwAt(3 + n, -3)
				var/turf/UB = MwAt(3 + n, -3, 3)
				UB.icon = 'Cave.dmi'; UB.icon_state = "Sky"; UB.name = "Sky"; UB.density = 0
			mw_pts["buildA"] = "[mw_site.x + 3],[mw_site.y - 3],-1"
			mw_pts["buildB"] = "[mw_site.x + 5],[mw_site.y - 3],-1"
			mw_pts["build2"] = "[mw_site.x + 4],[mw_site.y - 3],1.0"    // level 1 over the middle one (its slab not laid yet: the level's plane)
			mw_pts["tall4"] = "[mw_site.x - 4],[mw_site.y + 2],4.4"     // the six-high face's fifth and sixth blocks (levels 4 and 5)
			mw_pts["tall5"] = "[mw_site.x - 4],[mw_site.y + 2],5.4"
			var/mob/Monsters/M1 = U[1]
			M1.RemasterCancelOrders()
			M1.loc = MwAt(4, -5)
			M1.remaster_feet = null
			M1.destination = null
			for(var/mob/Monsters/S in P.Selected.Copy()) S.Deselect(P)
			M1.Select(P)
			P.loc = MwAt(2, -1)
			world.log << "MW|buildsetup|[M1.name]|stock=[ST.x],[ST.y]"
		if("upsetup")      // the way up: the second unit selected on the ground before the tall face
			var/mob/Monsters/M2 = U[min(2, length(U))]
			M2.RemasterCancelOrders()
			M2.loc = MwAt(-4, 0)
			M2.remaster_feet = null
			M2.destination = null
			for(var/mob/Monsters/S in P.Selected.Copy()) S.Deselect(P)
			M2.Select(P)
			P.loc = MwAt(-4, 1)
			world.log << "MW|upsetup|[M2.name]|tall=[RemasterBlocksAt(MwAt(-4, 2))]"
		if("skysetup")     // mountain heights step 2: the first unit up on an ordinary mountain's top, the second on the ground selected
			var/turf/SC = MwAt(0, 4)
			var/top = RemasterTopHeight(SC)
			var/mob/Monsters/MU = U[1]
			MU.RemasterCancelOrders()
			MU.loc = MwAt(0, 4, 3)
			MU.remaster_feet = null
			MU.destination = null
			var/mob/Monsters/MG = U[min(2, length(U))]
			MG.RemasterCancelOrders()
			MG.loc = MwAt(1, -1)
			MG.remaster_feet = null
			MG.destination = null
			if(length(U) >= 3)     // a flyer up on the Sky level: the player has earned the Sky (rts-feel), its view stays
				var/mob/Monsters/MF = U[3]
				MF.RemasterCancelOrders()
				MF.Flying = 1
				MF.rm_fly_level = 1
				MF.loc = MwAt(4, 0, 3)
				MF.destination = null
			for(var/mob/Monsters/S in P.Selected.Copy()) S.Deselect(P)
			MG.Select(P)
			P.loc = MwAt(0, 1)
			mw_tiles["skycol"] = SC
			mw_pts["skytopS"] = "[mw_site.x],[mw_site.y + 4],[top + 0.05]"                 // its top as the Surface view draws it
			mw_pts["skytop"] = "[mw_site.x],[mw_site.y + 4],[top - RM_SKY_H + 0.05]"        // and as the Sky view does, under the sky plane
			world.log << "MW|skysetup|[MU.name]|top=[top]|feet=[RemasterFeetOf(MU)]|level=[RmLevelOf(MU)]"
		if("slow")     // ordinary work, for a player to try it
			mw_fast = 0
		if("camera")   // "camera dx dy": the camera's centre on the site
			P.loc = MwAt(text2num(a[2]), text2num(a[3]))
		if("clearitems")   // stone and ore the sped-up digging left lying on the massif and in front of it
			for(var/turf/T in block(MwAt(-7, -2), MwAt(7, 10))) for(var/obj/Items/I in T) del(I)
			for(var/turf/T in block(MwAt(-7, -2, 3), MwAt(7, 10, 3))) for(var/obj/Items/I in T) del(I)
	world.log << "MW|done|[s]"
