// 3D view (proof of route 2): the game keeps running every rule; the HUD page
// draws the same world in 3D. The server sends the tiles and things around
// the camera, using the game's own tile art as textures and its sprites as
// billboards. Clicks in 3D go back through client/Click, the same path the
// 2D map uses, so selecting, orders and workshops behave identically.

// The area sent to 3D grows with the zoom (see "view3dsize"): 41x31 tiles up close,
// up to 101x81 zoomed all the way out.
#define REMASTER_3D_HALF_W remaster_3d_hw
#define REMASTER_3D_HALF_H remaster_3d_hh
#define REMASTER_3D_TERRAIN_EVERY 6   // RemasterTrack calls between terrain refreshes

// The four game layers line up tile for tile. In 3D they stack:
// Sky (3) above Surface (1) above Caves (2) above Depths (4).
proc/Remaster3DAbove(level)
	switch(level)
		if(1) return world.maxz >= 3 ? 3 : 0
		if(2) return 1
		if(4) return 2
	return 0
proc/Remaster3DBelow(level)
	switch(level)
		if(3) return 1
		if(1) return world.maxz >= 2 ? 2 : 0
		if(2) return world.maxz >= 4 ? 4 : 0
	return 0

Player/var/tmp
	remaster_3d_last
	remaster_3d_stack = 1      // diorama: the layer below drawn as solid ground under you
	remaster_3d_xray = 0
	remaster_3d = 1
	remaster_3d_key
	remaster_3d_clock = 0
	list/remaster_3d_sent
	remaster_3d_moving = 0      // the fast position loop is running
	remaster_3d_moves_last      // each unit's move row as last sent (ref -> "x,y,dir,ms,z,feet", Remaster3DMovesRows); null: send all
	list/remaster_3d_layers     // layer name -> last terrain sent (json)
	list/rm3d_chunks            // "z|cx,cy" -> the 16x16 terrain chunk the page has (its json), for sends of what changed
	list/rm3d_win               // layer name -> "z,x0,y0,w,h" of the window the page puts together from chunks
	rm3d_seen                   // the terrain layer's sight bits last sent ("*": all in sight)
	list/rm3d_cver              // "z|cx,cy" -> the chunk's change numbers when it was last built (the engine's counters)
	rm3d_pg = 0                 // the page the kept things' entries were made for (Remaster3DForget: the next)
	list/rm3d_rel               // this list's relations to each owner met (owner -> "allied at-war", Remaster3DEntryKey)
	list/rm3d_tcache            // a thing's id -> its entry last sent (json)
	list/rm3d_tobj              // a thing's id -> that entry itself (kept entries come back as the same list)
	list/rm3d_tmoved = list()   // ids of kept unit entries given a new place in the last things list (Remaster3DThings)
	list/rm3d_tnp               // a unit's id -> its entry as the page has it, without its place and facing (json)
	rm3d_tord                   // the things' order last sent
	rm3d_tbig = 0               // 1 while the scene has too many things for stage 2 (the whole list sent)
	remaster_3d_hw = 20
	remaster_3d_hh = 15
	remaster_3d_far_key        // camera chunk of the last far view sent
	remaster_3d_far_ver        // explore version it was built from
	list/remaster_3d_far_seen  // what your far-off units can see, refreshed every 2 s
	remaster_3d_far_more       // the last far view was missing chunks not read yet

var/list/remaster_3d_textures = list()   // "icon|state" -> list(file, colour, icon)
var/list/remaster_3d_made_tex = list()   // texture keys of pictures made in play, oldest first
var/list/remaster_3d_made_size = list()  // the same for icon sizes
var/remaster_3d_made_count = 0

// The cache key of an icon. A picture made in play (a body's, turned on its side in MakeBody, Death.dm) has no file
// name: "[icon]" is "" for every one of them, so every body showed the first body's picture (2026-10-23). Those are
// keyed by the icon itself.
proc/Remaster3DIconKey(icon)
	var/s = "[icon]"
	return length(s) ? s : "\ref[icon]"

// Pictures made in play come and go (a body rots away): only the newest 200 stay cached.
proc/Remaster3DKeepMade(list/cache, list/order, key)
	order += key
	if(length(order) > 200)
		cache -= order[1]
		order.Cut(1, 2)

// One PNG per original icon/state, sent to each player once, plus its average colour.
Player/proc/Remaster3DTexture(icon, state)
	if(!icon) return null
	var/made = !length("[icon]")
	var/key = "[Remaster3DIconKey(icon)]|[state]"
	var/list/T = remaster_3d_textures[key]
	if(!T)
		var/icon/I = RemasterPortraitCell(icon, state)
		var/r = 0; var/g = 0; var/b = 0; var/n = 0
		for(var/px = 4, px <= 28, px += 6)
			for(var/py = 4, py <= 28, py += 6)
				var/c = I.GetPixel(px, py)
				if(!c || length(c) < 7) continue
				if(length(c) >= 9 && copytext(c, 8, 10) == "00") continue
				r += text2num(copytext(c, 2, 4), 16); g += text2num(copytext(c, 4, 6), 16); b += text2num(copytext(c, 6, 8), 16); n++
		var/colour = n ? rgb(round(r / n), round(g / n), round(b / n)) : "#556655"
		T = list("file"="r3d-[md5(key)].png", "color"=colour, "icon"=I)
		if(made)
			// its own file name (an icon's ref can come back for a later picture), and the icon held while cached
			T["file"] = "r3d-made-[++remaster_3d_made_count].png"
			T["src"] = icon
			Remaster3DKeepMade(remaster_3d_textures, remaster_3d_made_tex, key)
		remaster_3d_textures[key] = T
		if(!made) rm3d_tex_files[T["file"]] = T   // for a chunk another player built (Remaster3DTexturesFor)
	if(!remaster_3d_sent) remaster_3d_sent = list()
	if(!remaster_3d_sent[T["file"]])
		remaster_3d_sent[T["file"]] = 1
		src << browse_rsc(T["icon"], T["file"])
	return T

// A chunk another player built names its pictures, and this page may not have them (Remaster3DTexture sends each to the
// page it builds for): what's missing is sent here. 0 when one isn't known (a picture made in play is never shared):
// the chunk is then built for this page.
var/list/rm3d_tex_files = list()   // a picture's file name -> its texture entry; not pictures made in play
Player/proc/Remaster3DTexturesFor(list/C)
	if(!remaster_3d_sent) remaster_3d_sent = list()
	for(var/list/K in C["kinds"])
		var/f = K["tex"]
		if(!f || remaster_3d_sent[f]) continue
		var/list/T = rm3d_tex_files[f]
		if(!T) return 0
		remaster_3d_sent[f] = 1
		src << browse_rsc(T["icon"], f)
	return 1

// Stairs lead up when the matching tile on the layer above is stairs too.
// Stairs: map stairs name their icon "Stairs.dmi", but stairs built in play carry its full path
// ("Code/Building/Stairs.dmi"), so match the file name either way.
proc/Remaster3DIsStairs(turf/T)
	return T && findtext("[T.icon]", "Stairs.dmi")

proc/Remaster3DStairs(turf/T)
	var/up = Remaster3DAbove(T.z)
	if(up)
		var/turf/U = locate(T.x, T.y, up)
		if(Remaster3DIsStairs(U)) return "stairsup"
	if(findtext("[T.icon_state]", "AncientUp")) return "stairsup"
	return "stairsdown"

proc/Remaster3DKind(turf/T)
	var/state = "[T.icon_state]"
	if(state == "Sky") return "void"
	if(T.remaster_wallwalk) return "walk"   // the walk on top of a wall (WallWalks.dm): the wall draws it
	if(T.remaster_ramp) return "ramp"       // a ramp tile up to wall stairs (WallWalks.dm)
	if(T.remaster_carve) return "carve"     // steps or a ramp carved up a mountain (Mountains.dm)
	if(findtext(state, "Hole")) return "hole"
	if(Remaster3DIsStairs(T) || findtext(state, "AncientDown") || findtext(state, "AncientUp")) return Remaster3DStairs(T)
	// A felled tree keeps its type and Tree flag but is no longer dense: draw the ground.
	// Tree, isbridge, Content3, IsWall, Detailed and IsWood are atom vars (Vars.dm), so they are read directly: a
	// ("x" in T.vars) lookup per tile made this, called for every tile of the view every tick, much slower.
	if(T.density && (T.Tree || istype(T, /turf/grounds/Trees))) return "tree"
	// A built bridge keeps the water (or lava) under it in Content3; the 3D view draws both.
	if(T.isbridge) return "bridge"
	if(findtext(state, "Lava")) return "lava"
	if(T.Content3 == "Liquid" || findtext(state, "Water") || findtext(state, "Swamp")) return "water"
	// Player-built pieces get the building kit (smart walls, raised floors, roofs).
	if(state == "FarmLand") return "farm"
	if(T.IsWall) return "built"
	if(T.Detailed && !T.density) return "bfloor"
	if(T.density && T.opacity) return "wall"
	if(T.density) return "block"
	return "floor"

// What a bridge spans: water, lava, or a chasm (bridging a chasm clears its Content).
proc/Remaster3DUnderBridge(turf/T)
	var/c3 = T.Content3
	if(c3 == "Lava" || findtext("[T.icon_state]", "Lava")) return "lava"
	if(c3 == "Liquid") return "water"
	return "chasm"

// With a box (list(x0, y0, x1, y1), a 16x16 chunk: Remaster3DPackTerrain), just those tiles and no line of sight, each
// kind with its key (k), so the page can put chunks together into exactly the window this builds. With pz (the camera's
// level, in a spread scene) a safe point every 32 tiles: a chunk's first build (rock heights, veins, new pictures) took
// up to 157 ms in one tick (world-look 2026-10-25); null when the camera went to another level meanwhile.
Player/proc/Remaster3DTerrain(zz = z, list/box, pz = 0)
	var/x0 = box ? box[1] : max(1, x - REMASTER_3D_HALF_W)
	var/x1 = box ? box[3] : min(world.maxx, x + REMASTER_3D_HALF_W)
	var/y0 = box ? box[2] : max(1, y - REMASTER_3D_HALF_H)
	var/y1 = box ? box[4] : min(world.maxy, y + REMASTER_3D_HALF_H)
	var/list/codes = list()       // key -> index
	var/list/kinds = list()       // index list of descriptions
	var/list/tiles = list()
	var/n = 0
	for(var/ty = y0, ty <= y1, ty++)
		for(var/tx = x0, tx <= x1, tx++)
			if(pz && !(++n % 32) && Remaster3DPauseLost(pz, rm3d_slice_build)) return null
			var/turf/T = locate(tx, ty, zz)
			if(!T)
				tiles += 0
				continue
			var/kind = Remaster3DKind(T)
			// the sky layer over a mountain: below the sky height its top is the Surface's, drawn from the ground layer's
			// rock, so it goes as open sky; a sky peak's top stays, at its own height (Peaks.dm, planning/MOUNTAIN_HEIGHTS.md)
			var/peakh = (zz == SKY_LAYER && T.icon_state == "Peak" && RmSkySplit()) ? RmPeakHeight(T) : 0
			if(zz == SKY_LAYER && T.icon_state == "Peak" && RmSkySplit()) kind = peakh < RM_SKY_H ? "void" : "peak"   // "peak": not drawn (the ground layer's rock is), kept for clicks
			if(kind == "void")
				tiles += 0
				continue
			var/biome = RemasterBiomeAt(T)
			var/vein = (kind == "wall" || kind == "block") ? RemasterVeinAt(T) : null    // metal veins (Breaking.dm)
			var/living = vein && RemasterVeinLiving(T) ? 1 : 0                           // a vein that grows back (Yield.dm)
			// stacked blocks (Breaking.dm): a rock column's height, a tunnel's roof
			var/blocks = (kind == "wall" && zz != SKY_LAYER && RemasterIsMountain(T)) ? RemasterBlocksAt(T) : 0
			if(peakh) blocks = peakh      // a sky peak's top: at the column's height
			var/roof = (!T.density && zz != SKY_LAYER) ? T.remaster_roof : 0
			var/under = (kind == "bridge") ? Remaster3DUnderBridge(T) : null
			var/road = (kind == "floor") ? T.remaster_road : null    // Roads.dm
			var/ceil = roof ? (T.remaster_ceil || 2) : 0    // Mountains.dm: a tunnel's ceiling, a carved run
			var/dug = blocks ? (T.remaster_dug ? 1 : T.remaster_dug_top ? 2 : 0) : 0   // 1: the floor block is out (a notch), 2: the one above (an overhang)
			var/gone = (blocks || roof) ? T.remaster_holes : 0   // blocks mined out on their own, bit k block k (Gather.dm)
			var/slope = (blocks || roof) ? RemasterSlopeOn(T) : 0          // a block carved into a ramp, the way it rises
			var/slopeh = slope ? T.remaster_slope_h : 0                    // and its top: the ramp is block slopeh - 1 (Gather.dm)
			var/list/carve = kind == "carve" ? list(T.remaster_carve, T.remaster_carve_n, T.remaster_carve_dir, T.remaster_carve_top, T.remaster_carve_ramp) : null
			var/hoard = T.remaster_hoard    // a dragon's lair floor heaped with coins (Instances.dm)
			var/wood = T.IsWood ? 1 : 0
			var/flow = (kind == "water" && (istype(T, /turf/grounds/waters/river) || istype(T, /turf/grounds/waters/ford))) ? T.dir : 0   // which way a river runs (Water.dm, set by the bake): the 3D view carries its ripples
			var/lift = kind == "water" ? T.remaster_waterlift : 0   // a mountain lake or its river, up in the rock (Water.dm)
			var/deep = (kind == "water" && T.density) ? 1 : 0   // deep water, swum (Swim.dm): the 3D view draws a swimmer down in it
			var/lay = ((blocks || roof) && T.remaster_laid) ? RmLaidMask(T) : 0   // + a room's ceiling laid over open ground (the layered builder, phase 3)   // blocks laid by a plan (Plans.dm), drawn dressed: masonry, logs (building rework L3)
			var/mat = lay ? T.remaster_mat : null                      // their letters (s stone, w wood); never who laid them
			var/key = "[Remaster3DIconKey(T.icon)]|[T.icon_state]|[kind]|[biome]|[vein][living ? "+" : ""]|[blocks]|[roof]|[under]|[road]|[ceil]|[carve ? jointext(carve, ",") : ""]|[dug]|[hoard]|[gone]|[slope]|[slopeh]|[wood]|[flow]|[lift]|[deep]|[lay]|[mat]"
			var/index = codes[key]
			if(!index)
				var/list/X = Remaster3DTexture(T.icon, T.icon_state)
				kinds += list(list("kind"=kind, "tex"=X ? X["file"] : null, "color"=X ? X["color"] : "#556655", "state"=lowertext("[T.icon_state]"), "wood"=wood, "biome"=biome, "vein"=vein, "living"=living, "blocks"=blocks, "roof"=roof, "under"=under, "road"=road, "ceil"=ceil, "carve"=carve, "dug"=dug, "hoard"=hoard, "gone"=gone, "slope"=slope, "slopeh"=slopeh))
				if(flow)
					var/list/KF = kinds[length(kinds)]
					KF["flow"] = flow
				if(lift)
					var/list/KL = kinds[length(kinds)]
					KL["lift"] = lift
				if(deep)
					var/list/KW = kinds[length(kinds)]
					KW["deep"] = 1
				if(lay)
					var/list/KY = kinds[length(kinds)]
					KY["lay"] = lay
					if(mat) KY["mat"] = mat
				index = length(kinds)
				codes[key] = index
				if(box)
					var/list/KD = kinds[index]
					KD["k"] = key
			tiles += index
	var/list/D = list("x0"=x0, "y0"=y0, "w"=x1 - x0 + 1, "h"=y1 - y0 + 1, "z"=zz, "tiles"=tiles, "kinds"=kinds)
	// Wall-walks (WallWalks.dm): each walk tile's outer sides (+16 when worked out) as one base-32 digit.
	if(zz == SKY_LAYER && length(remaster_wallwalks))
		var/list/faces = list()
		var/any = 0
		for(var/ty = y0, ty <= y1, ty++)
			for(var/tx = x0, tx <= x1, tx++)
				var/turf/W = locate(tx, ty, zz)
				var/f = (W && W.remaster_wallwalk) ? W.remaster_walkface : 0
				if(f) any = 1
				faces += copytext("0123456789abcdefghijklmnopqrstuv", f + 1, f + 2)
		if(any) D["face"] = jointext(faces, "")
	// Line of sight. Underground it is as the map shows it: tiles hidden behind rock are blacked out.
	// The surface and the sky layer are seen from above, over the trees, so all of the area is in
	// sight there (the camera's own line of sight made dark patches that moved with it).
	if(zz == z && !box) D["seen"] = Remaster3DSeenBits(zz, x0, y0, x1, y1)
	return D

// The window's line of sight: 1 in sight now, 2 seen before (drawn dim), 0 never seen (dark). On the surface and the
// sky layer all of it is in sight.
Player/proc/Remaster3DSeenBits(zz, x0, y0, x1, y1)
	var/open = (zz == GROUND_LAYER || zz == SKY_LAYER)
	var/list/seen = list()
	if(!open) for(var/turf/V in view(max(REMASTER_3D_HALF_W, REMASTER_3D_HALF_H), src)) seen[V] = 1
	var/list/bits = list()
	for(var/ty = y0, ty <= y1, ty++)
		for(var/tx = x0, tx <= x1, tx++)
			bits += (open || seen[locate(tx, ty, zz)]) ? "1" : (RemasterIsExplored(tx, ty, zz) ? "2" : "0")
	return jointext(bits, "")

// 3D sends only what changed (2026-10-24, the user: "we should do this"). Terrain goes as 16x16 chunks: a layer's
// chunks under the window are looked at when the layer is (as before: the ground every tick up close, the other layers
// every few), and one is sent only when it is new to the page or changed. The page keeps them and puts each layer's
// window together from them (remastered.html v3unpack), the same window Remaster3DTerrain builds. lay: layer name ->
// level, the layers looked at this tick. Returns the chunks to send (D["tc"]); sets rm3d_win, rm3d_seen; 1 in
// D["send"] when the page must put its layers together again. With spread, a safe point between layers (Spread.dm); null
// when the camera went to another level meanwhile.
#define RM3D_CHUNK 16
// A page that (re)loads, or says it is missing something, has none of the chunks or things: all sent again.
Player/proc/Remaster3DForget()
	rm3d_kept = null   // the scene parts it had (Remaster3DSame)
	rm3d_pg++   // the kept things' entries were for the page before: built again (their pictures sent again)
	rm3d_chunks = null
	rm3d_win = null
	rm3d_seen = null
	rm3d_cver = null
	rm3d_tcache = null
	rm3d_tobj = null
	rm3d_tord = null
	rm3d_tnp = null

// Terrain chunks built once for all the players looking at them (u1-sends 10-30). With a box, a chunk's build reads only
// its tiles and world-wide lists (Remaster3DTerrain), and its numbers (ver) are the engine's change counters, so another
// player's build at the same numbers is the same chunk. Only while two or more players look (one alone builds as
// before and nothing is kept); a kept chunk goes RM3D_SHARE_KEEP ticks after its last use.
//   RM3D_SHARE=0 in the server's environment: every player builds its own, as before
#define RM3D_SHARE_KEEP 100
var/rm3d_share = -1             // read from the environment on the first look
var/rm3d_share_on = 0           // two or more players looking now
var/list/rm3d_shared = list()   // "z|cx,cy" -> list(ver, the chunk, its json, the tick it was last used)
var/list/rm3d_lookers = list()  // a player's ref -> the tick of its last terrain look
var/rm3d_share_swept = 0
proc/Rm3DShareLook(Player/P)
	if(rm3d_share < 0) rm3d_share = world.GetConfig("env", "RM3D_SHARE") != "0"
	rm3d_lookers["\ref[P]"] = world.time
	if(world.time - rm3d_share_swept >= 50)
		rm3d_share_swept = world.time
		for(var/k in rm3d_lookers.Copy()) if(world.time - rm3d_lookers[k] > RM3D_SHARE_KEEP) rm3d_lookers -= k
		for(var/k in rm3d_shared.Copy())
			var/list/S = rm3d_shared[k]
			if(world.time - S[4] > RM3D_SHARE_KEEP) rm3d_shared -= k
	rm3d_share_on = rm3d_share && length(rm3d_lookers) > 1
	if(!rm3d_share_on && length(rm3d_shared)) rm3d_shared = list()

Player/proc/Remaster3DPackTerrain(cx, cy, cz, list/lay, moved, spread = 0)
	Rm3DShareLook(src)
	if(!rm3d_chunks) rm3d_chunks = list()
	if(!rm3d_cver) rm3d_cver = list()
	if(moved || !rm3d_win) rm3d_win = list()
	var/x0 = max(1, cx - REMASTER_3D_HALF_W)
	var/x1 = min(world.maxx, cx + REMASTER_3D_HALF_W)
	var/y0 = max(1, cy - REMASTER_3D_HALF_H)
	var/y1 = min(world.maxy, cy + REMASTER_3D_HALF_H)
	var/list/tc = list()
	var/send = 0
	var/first = 1
	for(var/name in lay)
		if(!first && spread && Remaster3DPauseLost(cz)) return null
		first = 0
		var/lz = lay[name]
		var/wk = "[lz],[x0],[y0],[x1 - x0 + 1],[y1 - y0 + 1]"
		if(rm3d_win[name] != wk)
			rm3d_win[name] = wk
			send = 1
		if(rm_native_ver)
			// the engine's change counters (RmVer.cs): whole chunks (the page takes the window's part), each built only when
			// it is new to the page or a turf in it, or on the level over it (stairs read it), changed
			var/up = Remaster3DAbove(lz)
			for(var/ccy = round((y0 - 1) / RM3D_CHUNK), ccy <= round((y1 - 1) / RM3D_CHUNK), ccy++)
				for(var/ccx = round((x0 - 1) / RM3D_CHUNK), ccx <= round((x1 - 1) / RM3D_CHUNK), ccx++)
					var/ck = "[lz]|[ccx],[ccy]"
					var/list/box = list(ccx * RM3D_CHUNK + 1, ccy * RM3D_CHUNK + 1, min(world.maxx, ccx * RM3D_CHUNK + RM3D_CHUNK), min(world.maxy, ccy * RM3D_CHUNK + RM3D_CHUNK))
					// read before it is built: a change while building (a tile working out its blocks) builds it again next time
					var/ver = "[rm_chunk_ver(ccx, ccy, lz)].[up ? rm_chunk_ver(ccx, ccy, up) : 0].[box[3]].[box[4]].[rm_biomes_ready].[length(remaster_wallwalks) ? 1 : 0]"
					var/list/C
					var/code
					if(rm3d_cver[ck] == ver && rm3d_chunks[ck])
						if(!rm_ver_verify) continue
						C = Remaster3DVerifyChunk(lz, box, ck)   // shadow mode: built anyway, and it must be what the page has
						if(!C) continue
					else
						// another player's build of this chunk at the same numbers (Rm3DShareLook): the same chunk
						var/list/S = rm3d_share_on ? rm3d_shared[ck] : null
						if(S && S[1] == ver && Remaster3DTexturesFor(S[2]))
							S[4] = world.time
							C = S[2]
							code = S[3]
						else
							if(spread && Remaster3DPauseLost(cz, rm3d_slice_build)) return null   // its number read before: a change meanwhile builds it again next time
							C = Remaster3DTerrain(lz, box, spread ? cz : 0)
							if(!C) return null   // the camera went to another level while it was built
							if(rm3d_share_on)
								code = json_encode(C)
								rm3d_shared[ck] = list(ver, C, code, world.time)
					rm3d_cver[ck] = ver
					if(!code) code = json_encode(C)
					if(rm3d_chunks[ck] != code)
						rm3d_chunks[ck] = code
						tc += list(C)
						send = 1
			continue
		// without them (an older engine): each chunk's part of the window built (the same pieces as cutting the whole window
		// up: a piece numbers its kinds as they first appear in it), a safe point before each
		for(var/ccy = round((y0 - 1) / RM3D_CHUNK), ccy <= round((y1 - 1) / RM3D_CHUNK), ccy++)
			for(var/ccx = round((x0 - 1) / RM3D_CHUNK), ccx <= round((x1 - 1) / RM3D_CHUNK), ccx++)
				if(spread && Remaster3DPauseLost(cz)) return null
				var/list/C = Remaster3DTerrain(lz, list(max(x0, ccx * RM3D_CHUNK + 1), max(y0, ccy * RM3D_CHUNK + 1), min(x1, ccx * RM3D_CHUNK + RM3D_CHUNK), min(y1, ccy * RM3D_CHUNK + RM3D_CHUNK)), spread ? cz : 0)
				if(!C) return null
				var/ck = "[lz]|[ccx],[ccy]"
				var/code = json_encode(C)
				if(rm3d_chunks[ck] != code)
					rm3d_chunks[ck] = code
					tc += list(C)
					send = 1
	if(lay["terrain"])
		var/s = (cz == GROUND_LAYER || cz == SKY_LAYER) ? "*" : Remaster3DSeenBits(cz, x0, y0, x1, y1)
		if(s != rm3d_seen)
			rm3d_seen = s
			send = 1
	return list("tc" = tc, "send" = send)

// Shadow mode (RM_VER_VERIFY=1): a chunk the counters say is unchanged, built anyway. Null when it is what the page
// has; otherwise the counters missed a change: counted, logged, and the chunk returned to be sent.
var/rm_ver_checked = 0
var/rm_ver_missed = 0
Player/proc/Remaster3DVerifyChunk(lz, list/box, ck)
	rm_ver_checked++
	var/list/C = Remaster3DTerrain(lz, box)
	if(json_encode(C) == rm3d_chunks[ck]) return null
	rm_ver_missed++
	if(rm_ver_missed <= 50) world.log << "RMVER|shadow|missed|[ck]|ver [rm3d_cver[ck]]"
	return C

// Chunks the page keeps that are now far from the window (more than 3 chunks out), or on a level no layer shows: both
// sides forget them (D["tdrop"]).
Player/proc/Remaster3DDropChunks(cx, cy)
	if(!rm3d_chunks || !rm3d_win) return null
	var/list/levels = list()
	for(var/name in rm3d_win)
		var/list/W = splittext(rm3d_win[name], ",")
		levels[W[1]] = 1
	var/list/drop = list()
	var/m = 3 * RM3D_CHUNK
	for(var/ck in rm3d_chunks)
		var/list/P = splittext(ck, "|")
		var/list/Q = splittext(P[2], ",")
		var/ox = text2num(Q[1]) * RM3D_CHUNK + RM3D_CHUNK / 2
		var/oy = text2num(Q[2]) * RM3D_CHUNK + RM3D_CHUNK / 2
		if(!levels[P[1]] || abs(ox - cx) > REMASTER_3D_HALF_W + m || abs(oy - cy) > REMASTER_3D_HALF_H + m) drop += ck
	for(var/ck in drop)
		rm3d_chunks -= ck
		if(rm3d_cver) rm3d_cver -= ck
	return length(drop) ? drop : null

// Things as changes: entries new or changed (c), ids gone (d), and the order (o) when it changed; the whole list on a
// fresh page (rm3d_tcache null) and every 30 s, so nothing can drift. Returns the fields to put in D.
// On for a scene of up to remaster_3d_thing_deltas_max things; above it the whole list goes, as before stage 2 (up to
// 4,000 on engine 8 it costs the server the same or less, things_size_bench.dm; at 5,000 on 6e it cost more).
// Switching sends the whole list (the cache is gone). Back on only under nine tenths of the size, so a scene near it
// doesn't switch every time.
var/remaster_3d_thing_deltas = -1   // stage 2, things as changes: on (user, 2026-10-25); RM_3D_DELTAS=0 off
var/remaster_3d_thing_deltas_max = 4000
Player/proc/Remaster3DPackThings(list/things)
	if(remaster_3d_thing_deltas < 0) remaster_3d_thing_deltas = world.GetConfig("env", "RM_3D_DELTAS") != "0"   // set here: world/New overrides chain before Native.dm's
	rm3d_tbig = length(things) > (rm3d_tbig ? round(remaster_3d_thing_deltas_max * 0.9) : remaster_3d_thing_deltas_max)
	if(!remaster_3d_thing_deltas || rm3d_tbig)
		rm3d_tcache = null
		rm3d_tobj = null
		rm3d_tnp = null
		return list("things" = things)
	var/full = !rm3d_tcache || !(remaster_3d_clock % 60)
	var/list/cache = list()
	var/list/order = list()
	var/list/changed = list()
	var/list/objs = list()
	// A unit the move rows place on the page (Remaster3DMovesRows: on the ground, within their reach, on a tile) whose
	// entry changed only in its place and facing isn't sent again: the rows moved it there already, and the page keeps
	// the entry it has (027 move3D sets t.x, t.y, t.dir). The rows' reach less 3 tiles, for a camera that moved while the
	// list was made; the whole list every 30 s as before (U6 10-31: with 50 of 200 units stepping each second, most of
	// each scene was entries sent again for a step). RM_3D_PLACE_ROWS=0: every changed entry, as before.
	if(rm3d_place_rows < 0) rm3d_place_rows = world.GetConfig("env", "RM_3D_PLACE_ROWS") != "0"
	var/rr = (rm3d_place_rows && z == GROUND_LAYER) ? min(25, max(REMASTER_3D_HALF_W, REMASTER_3D_HALF_H)) - 3 : -1
	// kept from list to list and changed only for the entries encoded below (copying it for every kept entry cost
	// ~0.7 us a thing a list); made anew with the whole list, which also lets go of things gone from view
	var/list/np = (full || !rm3d_tnp) ? list() : rm3d_tnp
	for(var/list/E in things)
		var/id = E["ref"] || E["id"]
		order += id
		objs[id] = E
		if(!full && rm3d_tobj && rm3d_tobj[id] == E && rm3d_tcache[id] && !rm3d_tmoved[id])   // the very entry sent last time (kept): unchanged
			if(rm_ver_verify) RmOnceCheck("3dkept", json_encode(E) != rm3d_tcache[id], id)
			cache[id] = rm3d_tcache[id]
			continue
		var/code = json_encode(E)
		var/nc
		if(rr >= 0 && !E["caged"] && rm3d_unit_kinds[E["kind"]] && abs(E["x"] - x) <= rr && abs(E["y"] - y) <= rr)
			var/list/N = E.Copy()
			N -= "x"
			N -= "y"
			N -= "dir"
			nc = json_encode(N)
		if(!full && rm3d_tcache[id] != code)
			if(nc && rm3d_tcache[id] && np[id] == nc)   // the page has it, and only its place and facing changed: the rows carried them
				cache[id] = code   // what the page has once the rows moved it: this entry (the old text left it one step behind when it came back out of the rows' reach)
				continue
			changed += list(E)
		cache[id] = code
		if(nc) np[id] = nc
		else if(np[id]) np[id] = null   // as the page has it now, with its place: not one to leave to the rows
	var/ord = jointext(order, "|")
	var/list/out = list()
	if(full)
		out["things"] = things
	else
		var/list/gone = list()
		for(var/id in rm3d_tcache) if(!cache[id]) gone += id
		out["td"] = list("c" = changed, "d" = gone)
		if(ord != rm3d_tord) out["to"] = order
	rm3d_tcache = cache
	rm3d_tobj = objs
	rm3d_tord = ord
	rm3d_tnp = np
	return out
var/rm3d_place_rows = -1
var/list/rm3d_unit_kinds = list("mine" = 1, "player" = 1, "npc" = 1, "animal" = 1)

// With spread, a safe point every 64 listed; null when the camera went to another level meanwhile (the scene is given up).
Player/proc/Remaster3DThings(zz = z, units_only = 0, spread = 0)
	if(rm3d_reuse < 0) rm3d_reuse = rm_native_ver && world.GetConfig("env", "RM_3D_REUSE") != "0"   // set here: world/New overrides chain before Native.dm's
	var/list/out = list()
	var/cz = z
	var/n = 0
	var/turf/C = locate(x, y, zz)
	if(!C) return out
	// Units first, so a busy scene never drops them; then buildings and furniture
	// (workshops, banners, siege engines, fishing spots), so ground strewn with
	// loot never hides them; loose items and decals last.
	var/list/later = list()
	var/list/rest = list()
	var/list/gore = list()   // bodies on the ground, then blood (blood): a share of their own (below)
	var/list/blood = list()
	var/fog = RmFogOn(zz)               // fog of war (Fog.dm): others only where you see; buildings as last seen
	var/list/fog_live = fog ? list() : null
	var/list/sel = list()   // the selection as a set: "M in Selected" searched it end to end for each of yours
	for(var/S in Selected) sel[S] = 1
	rm3d_rel = list()   // worked out once a list for each owner, not for each of its units (Remaster3DEntryKey)
	rm3d_tmoved = list()   // the kept entries given their new place in this list (the scene's main list is packed next)
	// range()'s movables in its order without its tiles (native version 28, RmRange.cs; U6 10-31): at r = 25 the list
	// held 2,601 tiles for a few hundred things, walked twice below. RM_RANGE_NATIVE=0: range() itself.
	if(rm_range_native < 0) rm_range_native = (world.GetConfig("env", "RM_RANGE_NATIVE") != "0" && rm_native_version() >= 28) ? 1 : 0
	var/list/seen = rm_range_native ? rm_range_movables(max(REMASTER_3D_HALF_W, REMASTER_3D_HALF_H), C) : null
	if(!seen) seen = range(max(REMASTER_3D_HALF_W, REMASTER_3D_HALF_H), C)
	for(var/obj/Items/Traps/Cages/CG in seen) if(CG.HasPersonIn) for(var/mob/Monsters/CM in CG) if(CM.rm_cap_cage) seen += CM   // shut in a cage: drawn standing in it (Captives.dm)
	var/built = 0
	for(var/atom/movable/A in seen)
		if(spread && (built || !(++n % 64)) && Remaster3DPauseLost(cz, built ? rm3d_slice_build : rm3d_slice)) return null   // and after each entry built: at join every look is new, and 64 looks' pictures took 200-700 ms
		built = 0
		if(Rm3DGone(A) || !A.icon || A.invisibility || A == src) continue   // deleted while it waited (Rm3DGone)
		var/turf/AT = A.loc
		if(!isturf(AT))
			if(!(istype(A, /mob/Monsters) && A:rm_cap_cage && isobj(AT) && isturf(AT.loc))) continue
			AT = AT.loc   // the cage's tile
		var/kind
		if(istype(A, /mob/Monsters))
			var/mob/Monsters/M = A
			if(M.Owner == src) kind = "mine"
			else if(fog && !RmFogSees(AT)) continue   // out of your sight: not sent at all
			else if(ismob(M.Owner)) kind = "player"
			else kind = M.Critter ? "animal" : "npc"
		else if(units_only) continue
		else if(istype(A, /mob/Body)) kind = "body"
		else if(istype(A, /mob/WorkShops)) kind = "station"
		else if(istype(A, /obj/Items)) kind = "item"
		else if(istype(A, /obj/Fire) || istype(A, /obj/Smoke) || istype(A, /obj/RemasterCloud) || istype(A, /obj/RemasterFlame)) kind = "effect"
		else if(isobj(A) && A.density) kind = "object"
		else if(isobj(A)) kind = "decal"   // dig marks, blood, signs on the ground
		else continue
		// the entry: kept from the last scene while nothing it shows can have changed (rm3d_reuse), else built
		var/list/D
		if(rm3d_reuse)
			var/rk = Remaster3DEntryKey(A, kind, sel)
			var/list/E = A.rm3d_ent
			var/list/K = E ? E[src] : null
			if(rk && K && K[1] == rk)
				D = K[2]
				if(istype(A, /mob/Monsters) && (D["x"] != AT.x || D["y"] != AT.y || D["dir"] != A.dir))
					D["x"] = AT.x
					D["y"] = AT.y
					D["dir"] = A.dir
					rm3d_tmoved[D["ref"] || D["id"]] = 1   // the packing encodes it again (Remaster3DPackThings)
				if(rm_ver_verify) Remaster3DEntryVerify(A, AT, kind, sel, D)
			else
				D = Remaster3DEntry(A, AT, kind, sel, spread ? cz : 0)
				built = 1
				if(!D || Rm3DGone(A)) continue   // deleted while its picture was built over ticks
				if(rk && Remaster3DEntryKeeps(D))
					if(!E)
						E = list()
						A.rm3d_ent = E
					E[src] = list(rk, D)
				else if(K) E -= src
		else
			D = Remaster3DEntry(A, AT, kind, sel, spread ? cz : 0)
			built = 1
			if(!D || Rm3DGone(A)) continue
		if(kind in list("mine", "player", "npc", "animal")) out += list(D)
		else if(D["m3"] || D["siege"] || D["banner"] || D["fishspot"] || D["mouth"] || D["hellgate"] || kind == "station")
			if(fog && kind != "decal")   // a building: live where you see it, else as you last saw it (below)
				if(!RmFogSees(AT)) continue
				var/tk = "[AT.x],[AT.y]"
				if(!fog_live[tk]) fog_live[tk] = list()
				fog_live[tk] += list(D)
			later += list(D)
		else if(fog && kind != "decal" && !RmFogSees(AT)) continue   // loose things and effects out of sight
		else if(kind == "body") gore += list(D)
		else if(istype(A, /obj/Bloods) || istype(A, /obj/PermBloods)) blood += list(D)
		else rest += list(D)
	if(fog) later += RmFogRemembered(fog_live, zz, C.x - REMASTER_3D_HALF_W, C.y - REMASTER_3D_HALF_H, C.x + REMASTER_3D_HALF_W, C.y + REMASTER_3D_HALF_H)
	for(var/list/D in later + rest)
		if(length(out) >= 600) break
		out += list(D)
	// Bodies, then blood, have a share of their own, so a big fight's dead and its blood show even when its units fill the
	// 600 above (the owner, 10-28: "dont change the blood just make it show up"), all over the view, not only round the
	// middle ("the bodys and blood tend to focus at the middle"): every one while the scene stays under 3,500 things (the
	// page gets only what changed up to 4,000: remaster_3d_thing_deltas_max), else every n-th, spread evenly out.
	gore += blood
	var/room = max(600, 3500 - length(out))
	var/step = max(1, -round(-length(gore) / room))
	for(var/i = 1, i <= length(gore), i += step) out += list(gore[i])
	return out

// --- Things' entries kept (2026-10-24: unchanged things cost nothing) ----------------------------------------------
// A thing keeps, for each viewer, its entry as last built and the key it was built under (rm3d_ent: viewer -> list(key,
// entry)). The key is the engine's change number for the thing (rm_ver, RmVer.cs: any var written, a move, its look, what
// it carries) and what else the entry reads that can change without it: the viewer's selection, its relations to the
// thing's owner, the unit's action (a swing's time, its target's distance), its timed looks, the page it was built for.
// Entries that change with the clock (a countdown, a climb, an age, flames, food, stalls, sieges, beasts, cave mouths) are
// always built. Only on an engine with the counters (rm_native_ver); RM_3D_REUSE=0 turns it off.
atom/movable/var/tmp/list/rm3d_ent
var/rm3d_reuse = -1
var/rm3d_shown = 0              // units keyed by their shown counter (rm_ver_shown, v35; RM_3D_SHOWN=0 the state counter)
var/rm_range_native = -1        // the scene's things from rm_range_movables (Remaster3DThings)
var/rm3d_reuse_checked = 0      // shadow mode (RM_VER_VERIFY=1): kept entries built again and compared
var/rm3d_reuse_missed = 0       // ...and found different (must stay 0)

Player/proc/Remaster3DEntryKey(atom/movable/A, kind, list/sel)
	// the same key as before, made at once (U6 10-31: ~4,000 keys a second for ten players): a unit is never one of the
	// kinds below, so it skips their seven type checks; its parts are put together in one string
	if(istype(A, /mob/Monsters))
		if(istype(A, /mob/Monsters/RemasterSiege)) return null   // RemasterIsSiege: built every time
		var/mob/Monsters/M = A
		if(M.remaster_ko_until > world.time || M.Fainted) return null   // RemasterKnockedOut (Subdue.dm)
		var/datum/remaster_order/O = M.remaster_active
		var/lay = ""
		if(O)
			if(O.kind == "Scale") return null
			if(O.kind == "Lay block")   // a block rising blow by blow (Sites.dm RmLay3D), all it draws: the shown counter doesn't see the order
				var/list/LY = RmLay3D(M)
				lay = LY ? "|L[LY[1]],[LY[2]],[LY[3]],[LY[4]],[LY[5]],[LY[6]]" : "|L"
		var/rel = ""
		if(kind == "player")
			// another player's: allied or at war, the same for all its units (an oath or a war changes it, between
			// lists); for ten players with 200 units in view these two cost ~9 ms a second, asked for each unit
			rel = rm3d_rel ? rm3d_rel[M.Owner] : null
			if(!rel)
				rel = "[RemasterAllied(src, M.Owner) ? 1 : 0][RemasterAtWar(src, M.Owner) ? 1 : 0]"
				if(rm3d_rel) rm3d_rel[M.Owner] = rel
			rel = "|[rel]"
		// its state counter (rm_ver_state): a walking unit's entry is kept, its place and facing written in where it is used
		// (Remaster3DThings), as the rows place it; the whole counter up on the Sky level (its feet follow the rock) and in a
		// cage (drawn at the cage's tile); its level, and the block it works (next to it or not, which one: RmWorkedBlock3D,
		// the order's own fields no counter sees) in the key (the owner, 10-31, 100 players: "does things multiple itmes")
		// what a view draws of it (rm_ver_shown, v35: its card's order status, current order, order list, combat marks aside;
		// the owner, 10-31: "those rebuilts are high arent they? shouldnt we get like 100?"), so the tool it works with
		// (RmG3Work: the order, its status, the work line) is in the key itself, and its health as the entry draws it (the
		// organs' health is in rm_ver_shown_names: read only for this)
		var/list/WB = kind == "mine" ? RmWorkedBlock3D(M) : null
		var/list/W3 = rm3d_shown ? RmG3Work(M) : null
		return "[(M.z == SKY_LAYER || M.rm_cap_cage) ? "v[rm_ver(A)]" : "s[rm3d_shown ? rm_ver_shown(A) : rm_ver_state(A)]"]|[M.z]|[WB ? "[WB[1]],[WB[2]],[WB[3]]" : ""]|[W3 ? "[W3[1]][W3[2]],[W3[3]]" : ""]|[kind]|[sel[A] ? 1 : 0]|[rm3d_pg][lay]|[Remaster3DAct(M)]|[M.rm_bandaged_until > world.time ? 1 : 0]|[world.time - M.rm_cough_at < 20 ? 1 : 0]|[M.remaster_root_until > world.time ? 1 : 0][rm3d_shown ? "|h[round(100 * RmLifeFrac(M))]" : ""][rel]"
	if(istype(A, /obj/RemasterFlame) || istype(A, /mob/WorkShops/CampFires) || istype(A, /obj/RemasterTrace) || istype(A, /obj/RemasterVomit)) return null
	if(istype(A, /mob/WorkShops/RemasterFood) || istype(A, /mob/WorkShops/RemasterStall) || istype(A, /obj/RemasterCaveMouth) || istype(A, /mob/WorkShops/RemasterNoticeBoard)) return null
	return "[rm_ver(A)]|[kind]|[sel[A] ? 1 : 0]|[rm3d_pg]"

// An entry that is the same whatever the clock says (else it is built every scene).
proc/Remaster3DEntryKeeps(list/D)
	if(!D) return 0
	return !(D["ko"] || D["climb"] || D["cough"] || D["age"] != null || D["vomit"] != null || D["flame"] || D["food"] || D["stall"] || D["siege"] || D["beast"] || D["mouth"] || D["qboard"] || D["qkeeper"])

Player/proc/Remaster3DEntryVerify(atom/movable/A, turf/AT, kind, list/sel, list/D)
	rm3d_reuse_checked++
	var/list/F = Remaster3DEntry(A, AT, kind, sel)
	RmOnceCheck("3dentry", json_encode(F) != json_encode(D), A.type)
	if(json_encode(F) == json_encode(D)) return
	rm3d_reuse_missed++
	if(rm3d_reuse_missed <= 30) world.log << "RMREUSE|missed|[A.type]|[url_encode(json_encode(list("kept" = D, "built" = F)))]"

// One thing's entry for this viewer, as the things round the camera are sent (Remaster3DThings).
Player/proc/Remaster3DEntry(atom/movable/A, turf/AT, kind, list/sel, pz = 0)   // pz: the camera's level in a spread scene (its pictures' safe points)
	var/list/D = list("kind"=kind, "x"=AT.x, "y"=AT.y, "name"=(kind == "station" ? RemasterStationName(A) : "[A.name]"), "dir"=A.dir)
	if(istype(A, /obj/Bloods/RmBloodPool)) return Remaster3DBloodPool(A, D)   // a block's blood pool (BloodPools.dm)
	if(kind == "player" && RemasterAllied(src, A:Owner)) D["ally"] = 1
	else if(kind == "player" && RemasterAtWar(src, A:Owner)) D["war"] = 1
	if(kind == "npc" && A:remaster_caravan) D["peace"] = 1
	if(istype(A, /obj/Items/Plants)) D["crop"] = Remaster3DCrop(A)
	var/list/m3 = Remaster3DObjModel(A)          // furniture, workshops, chests... drawn as 3D models
	if(m3)
		D["m3"] = m3[1]
		if(m3[2]) D["mat"] = m3[2]
		if(m3[3]) D["half"] = m3[3]
		if(isobj(A) && A.density == 0 && m3[1] == "door") D["open"] = 1
	if(istype(A, /obj/RemasterFishSpot)) D["fishspot"] = A:kind
	if(RemasterIsSiege(A))
		D["siege"] = A:remaster_siege_kind
		if(A:remaster_siege_kind == "ballista")   // its reach and what it is shooting at, drawn while it is selected
			D["srange"] = RM_BALLISTA_MAX
			var/turf/ST = A:remaster_siege_target ? RemasterSiegeSpot(A:remaster_siege_target) : null
			if(ST) D["starget"] = list(ST.x, ST.y)
		D["siegeStatus"] = A:remaster_siege_status
		if(RmIsShip(A))   // Ships.dm: those aboard, its sail in its realm's colour
			var/list/crew = list()
			for(var/mob/Monsters/X in A) if(length(crew) < 12) crew += RemasterClaimColour(X.Owner ? X.Owner:key : null)
			D["aboard"] = length(crew)
			if(length(crew)) D["crew"] = crew
			D["sail"] = RemasterClaimColour(A:remaster_owner_key)
		if(A:HP < A:MAXHP) D["siegeHp"] = round(100 * max(0, A:HP) / A:MAXHP)
		if(A:remaster_siege_burning) D["burning"] = 1
	if(istype(A, /obj/RemasterBanner))
		D["banner"] = A:colour
		if(A:siege) D["siege"] = A:siege
	if(istype(A, /obj/RemasterCaveMouth))
		D["mouth"] = A:danger
		var/lk = RemasterLairKind(A)
		if(lk) D["lair"] = lk
		var/list/VS = A:visited
		if(VS && VS[key] && VS[key] >= remaster_days) D["mouthDone"] = 1
	if(istype(A, /obj/RemasterCaveExit)) D["caveexit"] = 1
	if(istype(A, /obj/RemasterEmberVent)) D["vent"] = 1
	// Hellgates (the map's two, and any an admin opens): down to Hell, or back up from it.
	if(istype(A, /obj/Portal) || istype(A, /obj/PermPortal1) || istype(A, /obj/PermPortal2)) D["hellgate"] = A.z == 4 ? "up" : "down"
	if(istype(A, /mob/WorkShops/RemasterNoticeBoard)) D["qboard"] = RmQuestMark(A)   // this viewer's marker: ! to take, ? to hand in (Quests.dm)
	if(istype(A, /mob/WorkShops/RemasterStall)) D["stall"] = ismob(A:Owner) ? RemasterClaimColour(A:Owner:key) : "#e0bb73"
	if(istype(A, /mob/WorkShops/RemasterFood)) D["food"] = Remaster3DFood(A, src)   // food pots and stalls (FoodSupply.dm)
	if(istype(A, /mob/WorkShops/RemasterClinic)) D["clinic"] = Remaster3DClinic(A)   // Doctor.dm
	if(istype(A, /mob/WorkShops/RemasterSurgery)) D["optable"] = Remaster3DTable(A)   // Surgery.dm
	if(istype(A, /mob/WorkShops/RemasterTavern)) D["tavern"] = Remaster3DTavern(A)    // Tavern.dm
	if(istype(A, /mob/WorkShops/RemasterGraveyard)) D["graveyard"] = 1                 // Graves.dm
	if(istype(A, /obj/Items/Graves/Grave)) D["grave"] = 1
	if(istype(A, /obj/Items/Traps/Cages) && A:HasPersonIn && RmCapIsCage(A))   // a captive shut in it (Captives.dm): a cage tall enough for them
		D["cap"] = "Caged"
		D["caged"] = 1
	if(istype(A, /obj/RemasterTrace))                                                   // Forensics.dm
		D["trace"] = A:race || "?"
		D["age"] = round((world.time - A:made) / 600, 0.1)
	if(istype(A, /mob/Monsters))   // drink and sickness show (Ailments.dm)
		var/mob/Monsters/AM = A
		if(AM.rm_drunk >= 15) D["drunk"] = round(AM.rm_drunk)
		if(AM.rm_keeper) D["qkeeper"] = RmKeeperMark(AM)   // a keeper's marker for this viewer (QuestKeepers.dm)
		var/look = AM.RemasterLook()
		if(look) D["look"] = look                         // what anyone sees (Speech.dm)
		// no speech bubbles over units in 3D: the user turned them off (2026-10-23). Units still say their lines
		// (RemasterSay, Speech.dm), the page is just not sent them.
		if(AM.rm_limbs) for(var/slot in AM.rm_limbs) if(findtext(AM.rm_limbs[slot], "gem|") == 1) D["glow"] = 1
		if(AM.rm_brawl_with) D["brawl"] = 1
		var/ill = AM.RemasterIllLevel()
		if(ill) D["ill"] = ill
		if(world.time - AM.rm_cough_at < 20) D["cough"] = 1
		if(AM.remaster_root_until > world.time) D["webbed"] = 1
		var/egg = RmCarriedEgg(AM)   // an egg carried off from a nest (Taming.dm)
		if(egg) D["egg"] = egg
		var/list/glow = RmGlow(AM)   // a Crystal Staff lights the way (MagicGear.dm)
		if(glow) D["glow"] = glow   // held fast in a web (Specials.dm web shot, Buildings.dm sticky web)
	// Where the map really draws it: pixel offsets and pictures bigger than a tile.
	if(A.pixel_x || A.pixel_y)
		D["px"] = A.pixel_x / 32
		D["py"] = A.pixel_y / 32
	var/list/size = Remaster3DIconSize(A.icon)
	if(size[1] != 1 || size[2] != 1)
		D["iw"] = size[1]
		D["ih"] = size[2]
	if(A.mouse_opacity == 0) D["nopick"] = 1
	// Vapours and fire have their own 3D look (puffs, flames) in the page.
	if(istype(A, /obj/RemasterCloud))
		D["tint"] = A.color
		D["vap"] = A.alpha
	if(istype(A, /obj/RemasterFlame))
		D["flame"] = 1
		RmSendFireFx()   // its flames drawn with the fire particles (Beasts.dm)
	if(istype(A, /mob/WorkShops/CampFires)) RmSendFireFx()   // a campfire's flames are the same pixel fire (world-look)
	if(istype(A, /obj/RemasterVomit)) D["vomit"] = round((world.time - A:made) / 10, 0.1)   // FoodSupply.dm
	if(istype(A, /mob/WorkShops/RemasterCauldron)) D["cauldron"] = Remaster3DCauldron(A)
	if(istype(A, /obj/RemasterRune)) D["rune"] = Remaster3DRune(A)
	if(istype(A, /mob/Body)) D["body"] = 1   // a death doll lies over it while it is there (Gear3D.dm)
	if(istype(A, /mob/Body) && A:rm_beast)   // a dead dragon or spider lies as it fell (Beasts.dm)
		var/list/BC = RmBeastCorpse3D(A)
		if(BC) D["beast"] = BC
	// Units with a 3D model: their race (the model) and what they are doing (the animation).
	if(istype(A, /mob/Monsters))
		var/mob/Monsters/MM = A
		var/sc = Remaster3DScale(MM)
		if(sc != 1) D["sc"] = sc
		var/model = Remaster3DModelFor(MM)
		D["act"] = Remaster3DAct(MM)   // sprites animate too (attack swing, work)
		var/list/LY = RmLay3D(MM)   // a block it is laying (Sites.dm)
		if(LY) D["lay"] = LY
		var/list/G3 = RmG3Thing(MM)   // its weapon, shield and helmet in 3D (Gear3D.dm)
		if(G3) D["g3"] = G3
		if(MM.Flying) D["fly"] = RmFlyHeight(MM)   // tiles up in the air (Flying.dm)
		var/list/BE = RmBeast3D(MM)    // dragons and spiders: huge, animated (Beasts.dm)
		if(BE) D["beast"] = BE
		// knocked out (lies down with a "Zzz"; seconds until it wakes, -1 none), and captives on
		// a rope: the word over them, and who leads them (Captives.dm)
		if(MM.RemasterKnockedOut()) D["ko"] = max(1, round((MM.remaster_ko_until - world.time) / 10))
		else if(MM.Fainted) D["ko"] = -1
		if(MM.rm_dying_until)   // bleeding out (BleedOut.dm): the page words it so, with its own seconds left
			D["dying"] = 1
			D["ko"] = max(1, round((MM.rm_dying_until - world.time) / 10))
		if(MM.rm_cap_state == "bound" && !MM.rm_cap_cage)   // (caged: the cage says so)
			D["cap"] = MM.RmCapEscapeOdds() >= 12 ? "Bound, straining" : "Bound"
			if(MM.remaster_captive_lead) D["lead"] = RemasterUIRef(MM.remaster_captive_lead)
			else D["tieTo"] = MM.RmCapTieToSpot()   // the rope to the stake, tree or pillar they are tied to
		// up or down a cliff face (Mountains.dm): progress 0..1, the rock's height, the rock, up 1, the foot
		if(MM.z == SKY_LAYER) D["feet"] = RemasterFeetOf(MM)   // up on a mountain: the height it stands at, top or inside (Gather.dm)
		var/datum/remaster_order/SO = MM.remaster_active
		if(SO && SO.kind == "Scale" && SO.scale_start && SO.target)
			var/turf/SR = SO.target
			var/sl = RemasterBlocksAt(SR) || 3
			D["climb"] = list(round(min(1, (world.time - SO.scale_start) / max(1, RemasterClimbTime(MM, sl))), 0.01), sl + 0.4, SR.x, SR.y, SO.climb_z == SKY_LAYER ? 1 : 0, SO.scale_foot ? SO.scale_foot.x : SR.x, SO.scale_foot ? SO.scale_foot.y : SR.y)
		if(model)
			D["model"] = model
			var/list/G = Remaster3DGear(MM)
			if(length(G)) D["gear"] = G
	if(kind == "mine")
		var/mob/Monsters/M = A
		D["ref"] = RemasterUIRef(M)
		D["tex"] = RemasterPortrait(M)
		D["texd"] = Remaster3DUnitTextures(M, pz)
		if(pz && Rm3DGone(M)) return null   // deleted while its picture was built over ticks
		if(M.remaster_3d_frames > 1) D["wf"] = M.remaster_3d_frames
		if(M.remaster_3d_fx_files) D["fxd"] = M.remaster_3d_fx_files
		D["selected"] = sel[M] ? 1 : 0
		D["hp"] = round(100 * RmLifeFrac(M))   // how near death (Hits.dm)
		var/list/WB = RmWorkedBlock3D(M)   // the block it is mining: the page highlights it (Plans.dm)
		if(WB) D["wk"] = WB
	else
		var/list/X = Remaster3DTexture(A.icon, A.icon_state)
		D["tex"] = X ? X["file"] : null
		D["color"] = X ? X["color"] : null
		D["id"] = "\ref[A]"
		if(istype(A, /mob/Monsters))
			var/mob/Monsters/O = A
			D["hp"] = round(100 * RmLifeFrac(O))
			D["texd"] = Remaster3DUnitTextures(O, pz)
			if(pz && Rm3DGone(O)) return null
			if(O.remaster_3d_frames > 1) D["wf"] = O.remaster_3d_frames
			if(O.remaster_3d_fx_files) D["fxd"] = O.remaster_3d_fx_files
		// Workshops and corpses keep their overlays (signs, wounds), as on the map.
		else if(ismob(A) && length(A.overlays)) D["texd"] = Remaster3DUnitTextures(A, pz)
	return D

// --- Unit models (art/pipeline/export_units.py -> Interface/models/*.json) ---
var/list/remaster_3d_models = list("Orc", "Human", "Dwarf", "Elf", "Goblin", "Kobold", "Lizardman", "Frogman", "Skeleton", "Zombie", "Vampire")
Player/var/tmp/list/remaster_3d_models_sent

Player/proc/Remaster3DModelFor(mob/Monsters/M)
	if(M.Wagon || M.Egg || M.IsMist || !(M.Race in remaster_3d_models)) return null
	// a lost arm or leg: the models are always whole, so such a unit is drawn as its sprite, whose pose shows it (LimbLoss)
	if(!M.HasLeftArm || !M.HasRightArm || !M.HasLeftLeg || !M.HasRightLeg) return null
	var/name = lowertext(M.Race)
	if(!remaster_3d_models_sent) remaster_3d_models_sent = list()
	if(!remaster_3d_models_sent[name])
		remaster_3d_models_sent[name] = 1
		src << browse_rsc(file("Interface/models/[name].json"), "model-[name].json")
	return name

// What a unit wears and holds, for its model: slot -> "kind:tier" (weapon) or tier.
proc/Remaster3DTier(obj/Items/I)
	var/t = lowertext("[I.type] [I.name]")
	if(findtext(t, "hell") || findtext(t, "demonic") || findtext(t, "soul") || findtext(t, "destruction")) return "hell"
	for(var/k in list("adamantium", "diamond", "gold", "silver", "chitin")) if(findtext(t, k)) return k
	if(findtext(t, "bone") || findtext(t, "skull")) return "bone"
	if(findtext(t, "wood") || findtext(t, "elf") || findtext(t, "tribal") || findtext(t, "staff")) return "wood"
	if(findtext(t, "leather")) return "leather"
	return "iron"

proc/Remaster3DGear(mob/Monsters/M)
	var/list/G = list()
	for(var/obj/Items/Equipment/E in M) if(E.suffix == "(Equipped)")
		var/tier = Remaster3DTier(E)
		switch(E.ItemType)
			if("Sword", "Axe", "Mace", "Spear", "Dagger", "Pickaxe", "Bow", "Butcher Knife")
				var/kind = E.ItemType == "Butcher Knife" ? "dagger" : lowertext(E.ItemType)
				if(kind == "bow") G["bow"] = tier
				else G["w"] = "[kind]:[tier]"
			if("Shield") G["s"] = tier
			if("Helmet") G["h"] = tier
			if("Chestplate") G["c"] = tier
			if("Leggings") G["l"] = tier
			if("LeftArm") G["al"] = tier
			if("RightArm") G["ar"] = tier
	return G

proc/Remaster3DAct(mob/Monsters/M)
	if(M.HP <= 0) return "idle"
	// one attack played per swing (Hits.dm swing timer), not the whole time it stands at its foe
	if(world.time - M.rm_swung_at < (M.Race == "Dragon" ? 12 : M.Race == "Spider" ? 9 : 7)) return "attack"   // a beast's strike or breath plays out (BeastData.dm anims)
	if(M.remaster_defense || (ismob(M.Target) && get_dist(M, M.Target) <= 2) || (ismob(M.destination) && get_dist(M, M.destination) <= 1)) return "idle"
	var/datum/remaster_order/O = M.remaster_active
	if(O && (O.kind in list("Chop", "Mine", "Mine roof", "Dig down", "Carve ramp")) && O.target)   // at its block or tree: its attack frames (Gear3D.dm rm_g3_work_mine_chop)
		var/turf/WT = RemasterTurf(O.target)
		if(WT && max(abs(M.x - WT.x), abs(M.y - WT.y)) <= 1) return "work"
	return "idle"

// Icon size in tiles (32 px), cached per icon file.
var/list/remaster_3d_icon_sizes = list()
proc/Remaster3DIconSize(I)
	var/key = Remaster3DIconKey(I)
	var/list/S = remaster_3d_icon_sizes[key]
	if(S) return S
	var/icon/F = icon(I)
	S = list(max(1, round(F.Width() / 32)), max(1, round(F.Height() / 32)))
	if(!length("[I]")) Remaster3DKeepMade(remaster_3d_icon_sizes, remaster_3d_made_size, key)
	remaster_3d_icon_sizes[key] = S
	return S

// Painted ground textures for the 3D view (art/pipeline/make_ground.py), sent once per client.
Player/var/tmp/remaster_3d_textures_sent = 0
Player/proc/Remaster3DSendTextures()
	if(remaster_3d_textures_sent) return
	remaster_3d_textures_sent = 1
	for(var/n in list("ground-grass", "ground-earth", "ground-stone"))
		src << browse_rsc(file("Interface/textures/[n].png"), "r3t-[n].png")

// How far through the day (or the night) it is, 0 to 1, for the sun's path in 3D. Night() in World.dm
// switches every 5500 ticks; until the first switch is seen, it counts from the middle.
var/remaster_sky_night = -1
var/remaster_sky_since = 0
proc/RemasterDayProgress()
	if(night != remaster_sky_night)
		remaster_sky_since = remaster_sky_night == -1 ? world.time - 2750 : world.time
		remaster_sky_night = night
	return round(min(1, max(0, (world.time - remaster_sky_since) / 5500)), 0.001)

// What a scene leaves out because the page has it from the last scene sent (u1-sends 10-30): the fog of war (a scene
// without "fog" keeps the page's), and the blueprints, plan blocks, sites and plan doors, named in "same" for the page
// to put back (027 v3same). Only for a scene at the same place and level as the last one sent; a page that reloads or
// asks for "3dfull" is sent all of it (Remaster3DForget). Returns what the page has once this scene is sent.
Player/var/tmp/list/rm3d_kept
Player/proc/Remaster3DSame(list/D)
	var/list/was = rm3d_kept
	var/list/now = list("@" = "[D["cx"]],[D["cy"]],[D["z"]]")
	var/here = was && was["@"] == now["@"]
	if("fog" in D)
		now["fog"] = json_encode(D["fog"])
		if(here && was["fog"] == now["fog"]) D -= "fog"
	else if(was)
		now["fog"] = was["fog"]
	var/list/same = list()
	for(var/k in list("blueprints", "plan", "sites", "pdoors"))
		if(!(k in D)) continue   // none: the page has none
		now[k] = json_encode(D[k])
		if(here && was[k] == now[k])
			D -= k
			same += k
	if(length(same)) D["same"] = same
	return now

// A browser player whose tabs still have more than RM_WEB_SKIP_KB (default 256) KB queued (native version 29,
// rm_web_behind) gets no 3D scene and no move rows until they catch up: skipped, not queued (OpenRealm's rate; U4's full
// path, 10-31). Each is made against the last one really sent, so the page has it all again with the next one; the
// link's 32 MB close stays the last resort. A player in the app is never behind. RM_WEB_SKIP_KB=0: off.
var/rm_web_skip_at = -1
var/rm_web_skips = 0
Player/proc/RmWebBehind()
	if(rm_web_skip_at < 0)
		var/kb = text2num(world.GetConfig("env", "RM_WEB_SKIP_KB"))
		rm_web_skip_at = rm_native_version() >= 29 ? (isnull(kb) ? 256 : max(0, kb)) * 1024 : 0
	if(!rm_web_skip_at || rm_web_behind(src) <= rm_web_skip_at) return 0
	rm_web_skips++
	return 1

// With spread (the track's runs, Spread.dm) the ground is built in one tick and the units listed in a later one,
// just before the scene is sent, so they are sent as they stand; the scene is for where the camera was at the start.
Player/proc/Remaster3DTick(spread = 0)
	if(!client || !remaster_3d || !remaster_hud_ready) return
	Remaster3DSendTextures()
	if(!remaster_3d_moving) spawn(0) Remaster3DMovesLoop()
	if(RmWebBehind())   // its browser is behind: no scene this time; the next is made against the last one sent
		RmFogTick()     // its sight still kept up to date (what it explores)
		return
	var/pg = rm3d_pg
	var/list/D = Remaster3DScene(spread)
	if(!D || !client) return
	if(spread && (Remaster3DPauseLost(D["z"]) || rm3d_pg != pg)) return Remaster3DAbort()   // a safe point before the encode (a page that reloaded meanwhile: all again)
	var/list/kept = Remaster3DSame(D)
	var/encoded = json_encode(D)
	if(encoded == remaster_3d_last) return
	remaster_3d_last = encoded
	rm3d_kept = kept
	// packed like the HUD's sends (HudPack.dm) when the page unpacks them (1024: RM_HUD_PACK_FROM, defined after this file)
	if(remaster_hud_pack && length(encoded) >= 1024 && RmNativePack())
		var/packed = rm_pack(encoded)
		if(istext(packed))
			src << output("~[packed]", "mapwindow.hud:update3D")
			return
	src << output(url_encode(encoded), "mapwindow.hud:update3D")

// A safe point in the scene (Spread.dm): once the track has done rm3d_slice ms of work in this tick, the scene goes on
// in the next one, so the 3D view never adds more than about that to a tick (the user, 2026-10-24: "the game run good on
// a loaded computer"). True when the camera went to another level, or the page went, meanwhile.
var/rm3d_slice = 10            // ms
var/rm3d_slice_build = 30      // ms, while new ground or new pictures are being built (a join, the camera onto land not yet sent)
var/rm3d_spread_test = 0       // tests: a scene spread over ticks without a client (tests/delta3d_check.dm)
// A thing deleted while a scene waited at a safe point: in OpenDream a deleted object another proc holds is not null and
// reading any of its fields throws (build 24: "Cannot get field loc from <deleted>"), so it is asked inside a try. True
// for null, deleted, or nowhere (no loc).
proc/Rm3DGone(atom/movable/A)
	if(!A) return 1
	try
		return !A.loc
	catch
		return 1
Player/proc/Remaster3DPauseLost(cz, slice = rm3d_slice)
	RmTrackPause(slice)
	return (!client && !rm3d_spread_test) || !remaster_3d || z != cz

// A scene given up halfway: built again for the new level next time, and the ground and far view sent then (the chunks
// and things it counted as sent never went: all again). Returns null, for the scene.
Player/proc/Remaster3DAbort()
	remaster_3d_key = null
	remaster_3d_far_key = null
	Remaster3DForget()
	return null

// The 3D scene round you this tick, as Remaster3DTick sends it (null: nothing this time). Needs no client, so the
// arena can build it (tests/delta3d_check.dm).
Player/proc/Remaster3DScene(spread = 0)
	remaster_3d_clock++
	if(!rm_shed_level || !(remaster_3d_clock % (1 + rm_shed_level))) RmFogTick()   // fog of war: what your units see now (Fog.dm); less often while the server is behind
	if(spread) RmTrackPause()
	if(spread && ((!client && !rm3d_spread_test) || !remaster_3d)) return
	var/pg = rm3d_pg   // the page this scene is for: one that reloads meanwhile (Remaster3DForget) gives it up
	var/cx = x
	var/cy = y
	var/cz = z
	var/jump = remaster_3d_cam_seq   // the page's camera send this scene is begun after ("jump": the page takes its centre only if it is the last; hud-craft)
	var/key = "[cx],[cy],[cz]"
	var/above = Remaster3DAbove(cz)
	var/below = Remaster3DBelow(cz)
	// The ground you stand on is checked every tick, so a felled tree or dug-out
	// rock disappears as soon as it does on the map. It is only sent when it changed.
	var/moved = key != remaster_3d_key
	var/layers_skip = 0
	remaster_3d_key = key
	if(moved || !remaster_3d_layers) remaster_3d_layers = list()
	// Up close the ground is checked every tick; a zoomed-out area (costlier to
	// build) less often: every tick at 41x31, about every 3 seconds at 101x81.
	var/every = max(1, round(remaster_3d_hw * remaster_3d_hh / 330))
	if(!moved && (remaster_3d_clock % every)) layers_skip = 1
	// the layers looked at this tick (as before), sent as the chunks that changed (Remaster3DPackTerrain)
	var/list/lay = layers_skip ? list() : list("terrain" = cz)
	if(moved || !(remaster_3d_clock % (REMASTER_3D_TERRAIN_EVERY * (1 + rm_shed_level))))   // the other layers less often while the server is behind
		if(below && (cz == 3 || remaster_3d_stack)) lay["below"] = below
		// Upper floors: what is built in the Sky layer above the surface.
		if(cz == 1 && above) lay["upper"] = above
		if(remaster_3d_xray && above && cz != 1) lay["above"] = above
	var/list/TP = Remaster3DPackTerrain(cx, cy, cz, lay, moved, spread)
	if(!TP) return Remaster3DAbort()
	var/send_terrain = TP["send"]
	// The far view: explored land beyond the detailed area, 4x4-tile cells.
	// Sent when the camera enters another 16x16 chunk, or every ~10 s while exploring.
	var/list/far
	var/has_far = 0
	var/far_chunk = "[cz]|[round((cx - 1) / 32)],[round((cy - 1) / 32)]"
	if(far_chunk != remaster_3d_far_key || (remaster_3d_far_ver != remaster_explore_version && !(remaster_3d_clock % (40 * (1 + rm_shed_level)))))
		remaster_3d_far_key = far_chunk
		remaster_3d_far_ver = remaster_explore_version
		far = Remaster3DFar()
		has_far = 1
		remaster_3d_far_more = remaster_far_incomplete
	else if(remaster_3d_far_more && !(remaster_3d_clock % (4 * (1 + rm_shed_level))))
		far = Remaster3DFar()
		has_far = 1
		remaster_3d_far_more = remaster_far_incomplete
	if(spread && Remaster3DPauseLost(cz)) return Remaster3DAbort()
	var/list/D = list("cx"=cx, "cy"=cy, "jump"=jump, "z"=cz, "night"=!!night, "dayp"=RemasterDayProgress(), "xray"=remaster_3d_xray, "stack"=remaster_3d_stack, "magic"=(/Targeting/verb/SetTarget in verbs),
		"blueprints"=RemasterBlueprintData(), "skyh"=RM_SKY_H,     // the sky height (Peaks.dm): the page's Sky view reads it
		"build"=(Function ? list("mode"=Function, "label"=RemasterBuildModeLabel(Function), "kind"=RemasterBuildModeKind(Function), "paint"=!!RemasterTapPaintMode(Function)) : null))
	if(cz == GROUND_LAYER && RmPlanAny())
		D["plan"] = RmPlanCells3D(cx, cy, max(REMASTER_3D_HALF_W, REMASTER_3D_HALF_H) + 6)   // queued plan blocks (Plans.dm)
		D["sites"] = RmSites3D(cx, cy, max(REMASTER_3D_HALF_W, REMASTER_3D_HALF_H) + 6)    // their piles and bounds (Sites.dm)
	if(cz == GROUND_LAYER && length(rm_plan_doors)) D["pdoors"] = RmPlanDoors3D(cx, cy, max(REMASTER_3D_HALF_W, REMASTER_3D_HALF_H) + 6)   // doors waiting for their walls (PlanPieces.dm)
	// Flyers in the sky are drawn hovering over the surface; from the sky,
	// units on the ground are drawn below through the haze.
	if(cz == 1 && above)
		D["air"] = Remaster3DThings(above, 1, spread)
		if(!D["air"]) return Remaster3DAbort()
	if(cz == 3 && below)
		D["ground"] = Remaster3DThings(below, 1, spread)
		if(!D["ground"]) return Remaster3DAbort()
	if(spread && (cz == 1 && above || cz == 3 && below) && Remaster3DPauseLost(cz)) return Remaster3DAbort()
	// The things around (as changes), and the ground's chunks: the page puts every layer's window together again
	// whenever any changed, as it rebuilds all layers together.
	var/list/TL = Remaster3DThings(z, 0, spread)
	if(!TL) return Remaster3DAbort()
	var/list/TH = Remaster3DPackThings(TL)
	for(var/k in TH) D[k] = TH[k]
	if(spread && (Remaster3DPauseLost(cz) || rm3d_pg != pg)) return Remaster3DAbort()   // its page reloaded meanwhile: its window and chunks are gone
	if(send_terrain)
		var/list/tw = list()
		for(var/name in rm3d_win) tw[name] = splittext(rm3d_win[name], ",")
		for(var/name in tw)
			var/list/W = tw[name]
			for(var/i = 1, i <= length(W), i++) W[i] = text2num(W[i])
		D["tw"] = tw
		D["tc"] = TP["tc"]
		if(rm3d_win["terrain"]) D["ts"] = rm3d_seen
	if(!(remaster_3d_clock % 20))
		var/list/drop = Remaster3DDropChunks(cx, cy)
		if(drop) D["tdrop"] = drop
	if(has_far) D["far"] = far
	if(cz == 1) D["farunits"] = Remaster3DFarUnits()
	// Fog of war (Fog.dm): each tile's state for the 3D area, drawn soft in the page; 0 where it doesn't apply.
	if(moved || !rm_shed_level || !(remaster_3d_clock % (1 + rm_shed_level))) D["fog"] = RmFogBits(max(1, cx - REMASTER_3D_HALF_W), max(1, cy - REMASTER_3D_HALF_H), min(world.maxx, cx + REMASTER_3D_HALF_W), min(world.maxy, cy + REMASTER_3D_HALF_H), cz)
	// Trees and rock being worked: cracks, chips and falls (Breaking.dm).
	if(!(remaster_3d_clock % 10)) RemasterWorkTidy()
	if(length(rm_worked)) D["work"] = Remaster3DWork(cx - REMASTER_3D_HALF_W, cy - REMASTER_3D_HALF_H, cx + REMASTER_3D_HALF_W, cy + REMASTER_3D_HALF_H)
	if(length(rm_yield_known)) D["yield"] = Remaster3DYield(cx - REMASTER_3D_HALF_W, cy - REMASTER_3D_HALF_H, cx + REMASTER_3D_HALF_W, cy + REMASTER_3D_HALF_H)   // wood and ore left, tending (Yield.dm)
	return D

// The page reports its zoom; the area sent follows what the camera can see.
Player/proc/Remaster3DSize(value)
	var/d = text2num("[value]")
	if(!d) return 0
	var/hw = max(20, min(50, round(d * 1.3) + 4))
	var/hh = max(15, min(40, round(hw * 0.8)))
	if(hw == remaster_3d_hw && hh == remaster_3d_hh) return 0
	remaster_3d_hw = hw
	remaster_3d_hh = hh
	remaster_3d_key = null
	return 1

// Unit positions every tick, so 3D movement glides like the map does (the full scene still comes with
// Remaster3DTick every half second). Every two ticks made a five-tick step look like four, then six: the page's
// glide waited at a tile, then rushed (rts-feel 2026-10-23, tools/rts_feel/move/).
#define REMASTER_3D_MOVES_EVERY 1
Player/proc/Remaster3DMovesLoop()
	remaster_3d_moving = 1
	while(client && remaster_3d && remaster_hud_ready)
		Remaster3DMovesPush()
		sleep(REMASTER_3D_MOVES_EVERY)
	remaster_3d_moving = 0
	remaster_3d_moves_last = null

// One push a tick from now, from its own small proc (a spawn inside the caller would keep the caller's whole frame alive).
Player/proc/Remaster3DMovesPushSoon()
	spawn(1) if(src) Remaster3DMovesPush()

// One push this tick, once the units stepping in it have stepped (Orders.dm: a unit's first step after an order).
Player/var/tmp/remaster_3d_push_tick = -1
Player/proc/Remaster3DMovesPushNow()
	if(remaster_3d_push_tick == world.time) return
	remaster_3d_push_tick = world.time
	spawn(0) if(src) Remaster3DMovesPush()

// The positions of the creatures round the camera, sent when they changed: by the loop above, and once more a tick
// after an order (Orders.dm RemasterOrder), so the first step shows without waiting for the loop (rts-feel). Only the
// rows that changed go (u1-sends 10-30: the whole list went whenever any unit in it moved, 4.9 MB a second of the
// server's allocation for one player); the page moves the units it is told about and leaves the rest where they are.
Player/proc/Remaster3DMovesPush()
	if(!client || !remaster_3d || !remaster_hud_ready) return
	if(RmWebBehind()) return   // its browser is behind: these rows go with the next push, against the last ones sent
	var/list/moves = Remaster3DMovesRows()
	if(!length(moves)) return
	// last in the batch, the server's clock: ["@t", world.time, speed], so the page walks its units at the pace the
	// server keeps (art/hud/src/027 v3rateFrom; the owner, 10-29: "rubberbanding still happens")
	var/encoded = json_encode(moves)
	var/stamp = "\[\"@t\",[num2text(world.time, 12)],[max(1, rm_speed)]\]"
	encoded = copytext(encoded, 1, length(encoded)) + "," + stamp + "\]"
	// packed like the scene's (1024: RM_HUD_PACK_FROM, HudPack.dm) when the page unpacks them (027 v3mvParse)
	if(remaster_hud_pack && length(encoded) >= 1024 && RmNativePack())
		var/packed = rm_pack(encoded)
		if(istext(packed))
			src << output("~[packed]", "mapwindow.hud:move3D")
			return
	src << output(url_encode(encoded), "mapwindow.hud:move3D")

// This tick's move rows that differ from what the page was last sent: [ref, x, y, dir, its last step's length in ms
// (the page's glide), its level, up on a mountain its feet's height]. remaster_3d_moves_last keeps each unit's row as
// sent (ref -> "x,y,dir,ms,z,feet"), only for the units still round the camera, so one that comes back is sent again;
// a page that reloads (HUD.dm "ready") gets every row. Needs no client (reports/u1-sends-1030/tests/u1_sends_check.dm).
Player/proc/Remaster3DMovesRows()
	var/list/was = islist(remaster_3d_moves_last) ? remaster_3d_moves_last : list()
	var/list/now = list()
	var/list/moves = list()
	var/r = min(25, max(REMASTER_3D_HALF_W, REMASTER_3D_HALF_H))
	var/sp = max(1, rm_speed)
	var/turf/C = locate(x, y, z)
	if(rm_rows_native < 0) rm_rows_native = (world.GetConfig("env", "RM_ROWS_NATIVE") != "0" && rm_native_version() >= 27) ? 1 : 0
	if(rm_rows_native && rm_grid && C && C.z != SKY_LAYER)
		var/list/changed = Remaster3DMovesChanged(r, sp, C)
		if(changed) return changed
	rm_rows_key = null   // the rows were made here: the engine's way starts again with every unit
	if(C) for(var/mob/Monsters/M in Rm3DUnitsNear(r, C))
		if(!M.icon || M.invisibility || !isturf(M.loc)) continue
		if(M.Owner != src && !RmFogSees(M.loc)) continue   // fog of war (Fog.dm)
		var/ref = M.Owner == src ? RemasterUIRef(M) : "\ref[M]"
		// a unit on the ground keeps its row while nothing about it changed (its change counter, with the row's own vars
		// quiet: Native.dm rm_ver_quiet): a still army's rows aren't made again every tick (server upgrades U5, 10-30).
		// Up on the Sky level its feet follow the rock under it, so it is always made.
		var/row
		var/v = (rm_ver_quieted && M.z != SKY_LAYER) ? rm_ver(M) : -1
		if(v >= 0 && M.rm_move_row_ver == v && M.rm_move_row_sp == sp) row = M.rm_move_row
		else
			row = "[M.x],[M.y],[M.dir],[round(M.remaster_step_gap * 100 / sp)],[M.z],[M.z == SKY_LAYER ? RemasterFeetOf(M) : 0]"
			if(v >= 0)
				M.rm_move_row = row
				M.rm_move_row_ver = v
				M.rm_move_row_sp = sp
		now[ref] = row
		if(was[ref] != row) moves += list(list(ref, M.x, M.y, M.dir, round(M.remaster_step_gap * 100 / sp), M.z, M.z == SKY_LAYER ? RemasterFeetOf(M) : 0))
	// yours up on a mountain over the ground looked at (Gather.dm): their walks glide as on the ground
	var/turf/CU = z == GROUND_LAYER ? locate(x, y, SKY_LAYER) : null
	if(CU) for(var/mob/Monsters/M in Rm3DUnitsNear(r, CU))
		if(M.Owner != src || !M.icon || M.invisibility || !isturf(M.loc)) continue
		var/ref = RemasterUIRef(M)
		var/gap = round(M.remaster_step_gap * 100 / sp)
		var/feet = RemasterFeetOf(M)
		var/row = "[M.x],[M.y],[M.dir],[gap],[M.z],[feet]"
		now[ref] = row
		if(was[ref] != row) moves += list(list(ref, M.x, M.y, M.dir, gap, M.z, feet))
	remaster_3d_moves_last = now
	return moves

// The same rows on the ground from the engine's unit grid (native version 27, RmGrid.cs rm_grid_changed): only the units
// near the camera that are new to this player's view or whose change counter moved come back, and the kept rows
// (remaster_3d_moves_last) are brought up to date with those; the rest stand (server upgrades U6, 10-30: ten players
// each walked every unit near their camera every tick, ~32 ms a second). When the player's sight changed (Fog.dm
// rm_fog_sight: a source moved) the others' units are all looked at again; every unit is when the pace or the camera's
// level changed, the page reloaded, a unit it had was deleted, and every 5 s. RM_ROWS_NATIVE=0: the old way. Null when
// the engine has no answer (the caller then makes the rows the old way).
var/rm_rows_native = -1
Player/var/tmp
	rm_rows_key              // pace, fog setting, level and the 5 s it was made in: a change asks for every unit
	rm_rows_sight            // the sight (rm_fog_sight) the rows were made with
	list/rm_rows_sky         // yours up on the Sky level as last made (ref -> row): made again every call
Player/proc/Remaster3DMovesChanged(r, sp, turf/C)
	var/key = "[sp]|[remaster_fog]|[C.z]|[round(world.time / 50)]"
	var/mode = (!islist(remaster_3d_moves_last) || key != rm_rows_key) ? 1 : ((remaster_fog && rm_fog_sight != rm_rows_sight) ? 2 : 0)
	var/list/res = rm_grid_changed(src, 1, C.x - r, C.y - r, C.x + r, C.y + r, C.z, mode)
	if(!islist(res) || length(res) < 3) return null
	rm_rows_key = key
	rm_rows_sight = rm_fog_sight
	var/full = res[3]
	var/list/was = islist(remaster_3d_moves_last) ? remaster_3d_moves_last : list()
	var/list/now = full ? list() : was   // the kept rows changed in place: compare before writing
	var/list/sky_was = full ? was : (rm_rows_sky || list())
	if(!full) for(var/k in sky_was) now -= k   // made fresh below
	var/list/moves = list()
	for(var/mob/Monsters/M in res[1])
		var/mine = M.Owner == src
		var/ref = mine ? RemasterUIRef(M) : "\ref[M]"
		if(!full) now -= (mine ? "\ref[M]" : M.remaster_ui_id)   // its name from before its owner changed
		if(!M.icon || M.invisibility || !isturf(M.loc) || (!mine && !RmFogSees(M.loc)))
			now -= ref   // not shown: sent again when it is
			continue
		var/gap = round(M.remaster_step_gap * 100 / sp)
		var/row = "[M.x],[M.y],[M.dir],[gap],[M.z],0"   // not the Sky level: no feet
		if(was[ref] != row) moves += list(list(ref, M.x, M.y, M.dir, gap, M.z, 0))
		now[ref] = row
	for(var/mob/Monsters/M in res[2])
		now -= "\ref[M]"
		if(M.remaster_ui_id) now -= M.remaster_ui_id
	// yours up on a mountain over the ground looked at: as Remaster3DMovesRows (their feet follow the rock)
	var/list/sky = list()
	var/turf/CU = z == GROUND_LAYER ? locate(x, y, SKY_LAYER) : null
	if(CU) for(var/mob/Monsters/M in Rm3DUnitsNear(r, CU))
		if(M.Owner != src || !M.icon || M.invisibility || !isturf(M.loc)) continue
		var/ref = RemasterUIRef(M)
		var/gap = round(M.remaster_step_gap * 100 / sp)
		var/feet = RemasterFeetOf(M)
		var/row = "[M.x],[M.y],[M.dir],[gap],[M.z],[feet]"
		sky[ref] = row
		if(sky_was[ref] != row) moves += list(list(ref, M.x, M.y, M.dir, gap, M.z, feet))
	for(var/k in sky) now[k] = sky[k]
	rm_rows_sky = sky
	remaster_3d_moves_last = now
	return moves

mob/Monsters/var/tmp/rm_move_row        // its move row as last made (Remaster3DMovesRows), the change counter and pace then
mob/Monsters/var/tmp/rm_move_row_ver = -1
mob/Monsters/var/tmp/rm_move_row_sp

// The units within r tiles of the turf C, as `for(var/mob/Monsters/M in range(r, C))` finds them, from the unit grid
// (Native.dm rm_grid_units) instead of a list of every tile in the box (range(25): 2,601 tiles, twice a tick for each
// player). The order differs from range()'s; the units don't. No grid: range() itself.
proc/Rm3DUnitsNear(r, turf/C)
	if(rm_grid)
		var/list/G = rm_grid_units(C.x - r, C.y - r, C.x + r, C.y + r, C.z)
		if(islist(G)) return G
	return range(r, C)

// How far from the camera a 3D click reaches: everything the view shows.
#define REMASTER_3D_REACH max(25, remaster_3d_hw + 6)

// What a 3D click points at: own unit by HUD ref, other things by \ref,
// else the tile. "x|y|ref|..." within the view.
Player/proc/Remaster3DTarget(list/parts)
	if(parts.len < 3 || !client) return null
	var/turf/T = locate(text2num(parts[1]), text2num(parts[2]), z)
	if(!T || get_dist(src, T) > REMASTER_3D_REACH) return null
	// A click on top of a wall means its walk (WallWalks.dm), on the level above.
	var/turf/U = RemasterWalkClickTurf(T, parts.len >= 5 && parts[5] == "1")
	// A mountain top that nobody selected can get up to (no stairs, no climbing) means the rock itself: the click mines
	// it, as the pointer said (playtest r19: a click on a ridge answered "No stairs nearby…"; rts-feel).
	if(U != T && U.icon_state == "Peak" && !RemasterSelectionReaches(U)) U = RemasterRockFaceToward(T)
	T = U
	var/atom/A
	if(length(parts[3]))
		A = RemasterUIUnit(parts[3])
		if(!A)
			var/atom/R = locate(parts[3])
			if(istype(R, /atom/movable) && R:loc == T && !R:invisibility) A = R
	if(istype(A, /mob/Monsters) && !RmFogSeesMob(A)) A = null   // fog of war: what you can't see can't be clicked (Fog.dm)
	return A || T

// Whether one of the selected can get to a tile on another level (by stairs or by climbing); true with nobody selected.
Player/proc/RemasterSelectionReaches(turf/U)
	var/any = 0
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src) continue
		any = 1
		if(M.z == U.z || RemasterStairsTowards(M, U) || RemasterCanClimb(M)) return 1
	return !any

// A ridge top's tile is often a row or two inside the rock, where no miner can stand beside it ("No way through yet",
// playtest r21). From it towards the nearest selected unit, the first rock tile with open ground beside it: the face
// a miner can dig now (the tile itself when it has some).
Player/proc/RemasterRockFaceToward(turf/T)
	var/mob/Monsters/near
	for(var/mob/Monsters/M in Selected) if(M.Owner == src && M.z == T.z && (!near || get_dist(M, T) < get_dist(near, T))) near = M
	if(!near) return T
	var/turf/C = T
	for(var/i = 0, i < 8 && C && C.density, i++)
		for(var/turf/N in orange(1, C)) if(!N.density && RemasterWalkable(N, near, N)) return C
		var/turf/next = get_step_towards(C, near)
		if(!next || next == C) break
		C = next
	return T

// A click in 3D goes through client/Click exactly like a map click.
// Which of a rock column's two outside blocks a 3D click or hover pointed at (6th field: 0 the floor block, 1 the one
// above; the page reads it off the face), as the one still there; null for anything else (Orders.dm takes the floor block).
// Higher up the face (2 and up, to the column's top block) a click mines just that block (Gather.dm).
proc/Remaster3DBlock(list/parts, atom/A)
	if(length(parts) < 6 || !isturf(A) || !A.density || !RemasterIsMountain(A)) return null
	var/b = text2num(parts[6])
	if(!isnum(b) || b < 0 || b != round(b)) return null
	b = min(b, RemasterBlocksAt(A) - 1)
	if(b == 0 && A:remaster_dug) b = 1
	else if(b == 1 && A:remaster_dug_top) b = 0
	return RemasterBlockThere(A, b) ? b : null    // a block already mined out on its own: nothing to take there (Gather.dm)

Player/var/tmp/remaster_click_block   // the block a 3D click pointed at, while the click runs (Orders.dm RemasterOrder)
Player/var/tmp/remaster_click_level   // a 3D click on a dug-out floor up on a mountain: the height it is at (Gather.dm)
Player/proc/Remaster3DClick(value)
	var/list/parts = splittext("[value]", "|")
	var/atom/A = parts.len >= 4 ? Remaster3DTarget(parts) : null
	if(!A) return 0
	usr = src
	remaster_click_block = Remaster3DBlock(parts, A)
	remaster_click_level = (length(parts) >= 6 && parts[5] == "1" && isturf(A) && A.z == SKY_LAYER) ? text2num(parts[6]) : null
	client.Click(A, isturf(A) ? A : A.loc, "mapwindow.map", parts[4] == "1" ? "left=1;shift=1" : "left=1")
	remaster_click_block = null
	remaster_click_level = null
	return 1

// The menu's Pick up on a thing on the ground (the owner, 10-28: "i dropped a sleeping bag and i cant pick it up
// anymore"). A click on furniture walks there (Orders.dm RemasterOrderKind: a bed is somewhere to sleep), so the
// button orders the taking itself for loose furniture and a cage set down, as their own double-click menus did. A
// fixture (part of a building, a cart, a door, anything shut or set down to stay) is walked to, as the click does;
// everything else goes as the click does too, a loose thing being picked up.
Player/proc/Rm3DPickUp(value)
	var/list/parts = splittext("[value]", "|")
	var/obj/Items/I = parts.len >= 4 ? Remaster3DTarget(parts) : null
	if(istype(I) && isturf(I.loc) && isnull(I.suffix) && !I.remaster_placed && !I.density && length(Selected) && \
		((istype(I, /obj/Items/Furniture) && !istype(I, /obj/Items/Furniture/Doors)) || istype(I, /obj/Items/Traps/Cages)))
		usr = src
		return RemasterOrder(I, parts[4] == "1" || remaster_queue, "Pick up")
	return Remaster3DClick(value)

// Double-click in 3D: client/DblClick like the map (workshops, stairs,
// items, corpses, "select all like this").
Player/proc/Remaster3DDblClick(value)
	var/atom/A = Remaster3DTarget(splittext("[value]", "|"))
	if(!A) return 0
	usr = src
	client.DblClick(A, isturf(A) ? A : A.loc, "mapwindow.map", "left=1")
	return 1

// The menu's action on a thing with none of yours by it selected (the owner, 10-28: "clicking a item no interact buttons
// show up" - "nearest unit or highlighted units"): the nearest of the selected, else of all yours on that level that
// can go, is selected and does it as the click would ("click3d~x|y|ref|0": Go to, a portal; "pickup3d~x|y|ref|0": Pick
// up, Rm3DPickUp; "carrybody~body": Drag body).
Player/proc/RmNearAct(value)
	var/list/p = splittext("[value]", "~")
	if(length(p) != 2 || !(p[1] in list("click3d", "pickup3d", "carrybody"))) return 0
	var/atom/A = p[1] != "carrybody" ? Remaster3DTarget(splittext(p[2], "|")) : locate(p[2])
	var/turf/T = A ? (isturf(A) ? A : A.loc) : null
	if(!isturf(T)) return 0
	var/list/pool = length(Selected) ? Selected.Copy() : UnitList
	var/mob/Monsters/best
	var/bd = 1e9
	for(var/mob/Monsters/M in pool)
		if(Rm3DGone(M) || M.Owner != src || M.z != T.z || !isturf(M.loc) || M.HP <= 0 || M.GoingToDie || M.Fainted || M.Sleeping || !M.CanWalk || M.Wagon || M.rm_cap_state) continue
		var/d = get_dist(M, T)
		if(d < bd)
			bd = d
			best = M
	if(!best)
		RemasterNotice("None of yours on this level can go.")
		return 0
	Selected = list(best)
	if(p[1] == "click3d") return Remaster3DClick(p[2])
	if(p[1] == "pickup3d") return Rm3DPickUp(p[2])
	return RemasterCarryBody("[RemasterUIRef(best)]|[p[2]]")

// Drag a box in 3D: the same box selection as dragging on the map.
Player/proc/Remaster3DBox(value)
	var/list/parts = splittext("[value]", "|")
	if(parts.len < 5) return 0
	var/turf/A = locate(text2num(parts[1]), text2num(parts[2]), z)
	var/turf/B = locate(text2num(parts[3]), text2num(parts[4]), z)
	if(!A || !B || get_dist(src, A) > REMASTER_3D_REACH || get_dist(src, B) > REMASTER_3D_REACH) return 0
	usr = src
	RemasterBoxSelect(A, B, parts[5] == "1")
	return 1

// Box select in 3D by what is on screen: "ref,ref,...|shift" (the page tests where each
// of your units is drawn). Without shift the box replaces the selection.
Player/proc/Remaster3DBoxRefs(value)
	var/list/parts = splittext("[value]", "|")
	if(parts.len < 2) return 0
	RemasterNormalizeSelection()
	remaster_queue = 0
	var/add = parts[2] == "1"
	var/list/picked = list()
	for(var/ref in splittext(parts[1], ","))
		var/mob/Monsters/M = RemasterUIUnit(ref)
		if(istype(M) && M.Owner == src && M.HP > 0 && !M.GoingToDie && get_dist(src, M) <= REMASTER_3D_REACH) picked += M
	if(!length(picked)) return 0
	usr = src
	if(!add) for(var/mob/Monsters/S in Selected.Copy()) if(!(S in picked)) S.Deselect(src)
	for(var/mob/Monsters/M in picked) M.Select(src)
	return 1

// Right-click menu in 3D: the map's right-click verb (Set Target) on a unit.
Player/proc/Remaster3DMagicTarget(value)
	var/mob/Monsters/M = Remaster3DTarget(splittext("[value]", "|"))
	if(!istype(M) || !(/Targeting/verb/SetTarget in verbs)) return 0
	usr = src
	RemasterNativeMagicTarget(M, REMASTER_3D_REACH)   // whoever the 3D view lets you right-click, not only within view()'s 9 tiles
	return 1

// Remastered is always 3D. The old F8 toggle (removed from the skin) only turns it back on.
Player/verb/Toggle3DView()
	set name = "Toggle-3D-View"
	set hidden = 1
	if(remaster_3d) return
	remaster_3d = 1
	remaster_3d_far_key = null
	remaster_3d_key = null

// Per-direction unit sprites with gear: base body plus its overlays (equipment,
// hair) for south, north, east and west, so a turning camera shows the side
// the unit really faces. Cached by appearance; sent to each player once.
var/list/remaster_3d_unit_cells = list()

// Dragons and spiders stand taller in 3D than one tile. Spiders grow with their
// stage (Young, Older, Mature sprites); queens are the largest. Every other race
// keeps its one-tile size.
proc/Remaster3DScale(mob/Monsters/M)
	if(M.Race == "Dragon") return 2.4
	var/f = lowertext("[M.icon]")
	if(M.Race == "Spider" || findtext(f, "spider"))
		var/s = findtext(f, "mature") ? 1.6 : findtext(f, "older") ? 1.3 : 1.0
		if(M.SubRace == "Queen") s *= 1.2
		else if(M.SubRace == "Warrior") s *= 1.1
		return round(s, 0.1)
	return 1

// One facing of a picture, in animation frame `frame`; a state with fewer frames gives its first.
proc/Remaster3DCell(source, state, dir, frame = 1)
	if(!source) return null
	if(!(state in icon_states(source))) state = ""
	var/icon/I = icon(source, state, dir, frame, 0)
	if(!length(icon_states(I))) I = icon(source, state, dir, frame, 1)
	if(!length(icon_states(I)) && frame > 1) return Remaster3DCell(source, state, dir)
	if(!length(icon_states(I))) I = icon(source, state, SOUTH, 1, 0)
	return I

// How many animation frames a picture has (up to 5), cached.
var/list/remaster_3d_frame_counts = list()
proc/Remaster3DFrames(source, state)
	var/key = "[source]|[state]"
	. = remaster_3d_frame_counts[key]
	if(.) return
	. = 1
	if(!(state in icon_states(source))) state = ""
	for(var/k = 2, k <= 5, k++)
		var/icon/I = icon(source, state, SOUTH, k, 0)
		if(!length(icon_states(I))) I = icon(source, state, SOUTH, k, 1)
		if(!length(icon_states(I))) break
		. = k
	remaster_3d_frame_counts[key] = .

mob/var/tmp
	remaster_3d_key
	list/remaster_3d_files
	remaster_3d_frames = 1   // frames in each picture strip sent for this unit
	list/remaster_3d_fx_files   // its magic items' effect atlases, one per facing, or null
// The remastered 64 px body for a playable race, or null. Dwarves use Human.dmi
// in the original but have their own remastered sheet.
var/list/remaster_3d_races64 = list("orc.dmi"="Orc", "human.dmi"="Human", "night elf.dmi"="Night Elf", "goblins.dmi"="Goblins",
	"kobold.dmi"="Kobold", "lizardman.dmi"="LizardMan", "frogman.dmi"="FrogMan", "skeleton.dmi"="Skeleton",
	"devourerzombie.dmi"="DevourerZombie", "vampire.dmi"="Vampire", "demon.dmi"="Demon", "humanblack.dmi"="HumanBlack",
	"gargoyle.dmi"="Gargoyle", "fly.dmi"="VampireFly", "fly2.dmi"="DemonFly", "fly3.dmi"="GargoyleFly")   // flying: Fly() puts these on
// On (2026-10-21): the enhanced originals (art/enhance/game_export.py), with every worn
// item drawn fitted to each race's body (Gear.dm, RmGear64).
var/remaster_3d_use64 = 1
proc/Remaster3DBody64(mob/M)
	if(!remaster_3d_use64) return null
	var/were = RmWerewolfSheet(M)   // a werewolf changed at night: its own race's wolf (Undead.dm)
	if(were) return file(RmFemaleBody(M, were))   // a woman's own body (FemaleBodies.dm)
	var/name = RmRaceSheet(M)   // Gear.dm
	if(!name) return null
	return file(RmFemaleBody(M, RmZombieSheet(M, name) || RmHalfDemonSheet(M, name) || RmEyeSheet(M, name) || "Icons/Remastered/Races64/[name].dmi"))   // a zombie's rotted body (Undead.dm), a half-demon kind's own look (HalfDemons.dm)

// The layers a unit's sprite is made of, in the order the original RebuildOverlays()
// stacks them (OverlayBuilds.dm). Built from the unit itself, not read back from
// overlays: in this engine an icon() overlay no longer says which picture it is, so
// gear read from overlays went missing in 3D.
proc/Remaster3DLayers(mob/M, body64)
	var/list/L = list(list(body64 || M.icon, M.icon_state))
	var/list/G = istype(M, /mob/Monsters) ? M:RemasterLimbLayers(body64) : null   // grafted and false limbs (Surgery.dm)
	if(G) L = list(list(body64, G[1])) + G[2]
	if(M.IsMist) return L
	var/list/cut = RmLimbMaskFor(M, body64)   // gear over a lost limb is cut away (LimbGear.dm)
	var/list/eq = list()
	for(var/obj/Items/Equipment/E in M) if(E.suffix == "(Equipped)") eq += E
	// Hair, beards and a woman's top: on a 64 px body, the ones fitted to it (Gear.dm RmLook).
	if(!M.Critter && M.Gender == "Female" && !M.Werepowers && !RmIsFemaleBody(body64))   // a woman's own body has its top drawn in (FemaleBodies.dm)
		if(M.Race in list("Human", "Dwarf", "Elf")) L += RmLimbMaskedAll(RmLook(M, 'Female.dmi', "Unders", body64), cut)
		else if(!(M.Race in list("Dragon", "Spider"))) L += RmLimbMaskedAll(RmLook(M, 'Female.dmi', "Shirt", body64), cut)
	for(var/T in list(/obj/Items/Equipment/Armour/Leggings, /obj/Items/Equipment/Armour/Chestplate))
		for(var/obj/Items/Equipment/E in eq) if(istype(E, T)) L += list(RmLimbMasked(RmGear64(M, E, body64), cut))
	if(M.Beard) L += RmLook(M, 'Beards.dmi', "[M.Beard]", body64)
	if(M.Hair && !RmOwnHeadBody(body64)) L += RmLook(M, 'Hair.dmi', "[M.Hair]", body64)   // and her hair, and the elf man's (FemaleBodies.dm)
	var/list/g3 = body64 ? RmG3Items(M) : null   // what the page draws in 3D in its hand and on its head (Gear3D.dm)
	var/armed = G ? null : RmG3Armed(M, body64)   // holding a 3D weapon: the armed walk, its weapon arm kept at its side (Gear3D.dm)
	if(armed) L[1] = list(body64, armed)
	for(var/T in list(/obj/Items/Equipment/Armour/LeftArm, /obj/Items/Equipment/Armour/RightArm, /obj/Items/Equipment/Armour/Capes, /obj/Items/Equipment/Armour/Helmet,
		/obj/Items/Equipment/Armour/Crown, /obj/Items/Equipment/Armour/Quiver, /obj/Items/Equipment/Armour/Shield, /obj/Items/Equipment/Weapon))
		for(var/obj/Items/Equipment/E in eq) if(istype(E, T) && !RmLimbGearGone(M, E) && !(g3 && (E in g3)))
			var/list/P = RmGear64(M, E, body64)
			if(armed && T == /obj/Items/Equipment/Armour/RightArm) P = RmG3ArmedPiece(P)   // its arm piece kept at its side with the arm
			L += list((T in rm_limb_uncut) ? P : RmLimbMasked(P, cut))
	if(M.HasWings && M.WingsOut)
		var/w = list('Vampire.dmi'="Vampire", 'Demon.dmi'="Demon", 'Gargoyle.dmi'="Gargoyle", 'Angel of Death.dmi'="Death Angel")[M.icon]
		if(w) L += list(list('Wings.dmi', w))
	if(M.icon == 'Lizardman.dmi') L += list(list(body64 || M.icon, "Tail"))
	if(istype(M, /mob/Monsters) && M:rm_cap_state) L += RmRopeLayers(M, body64, L[1][2])   // a captive's rope or a slave's hobble (Captives.dm)
	return L

// Each facing is sent as a strip of frames, left to right: standing, the original's two
// walk frames, and (when what the unit holds has them, Gear64) an attack's wind-up and
// strike. The page picks the frame (walking, fighting). Workshops and the like keep one.
proc/Remaster3DStripFrames(mob/M, list/layers, body64)
	if(!istype(M, /mob/Monsters) || !length(layers)) return 1
	var/list/B = layers[1]
	var/n = min(3, Remaster3DFrames(B[1], B[2]))
	if(n == 3 && body64)
		for(var/list/L in layers) if(Remaster3DFrames(length(L) >= 4 ? L[4] : L[1], L[2]) >= 5) return 5
	return n

// One facing's strip: n frames of the layers stacked, side by side. (This engine's Blend
// ignores x offsets, so each frame is laid at the left and the strip shifted along.)
// fx: effect frame f of an effect sheet, whose frame (k - 1) * 4 + f goes with frame k.
proc/Remaster3DStrip(list/layers, dir, n, body64, fx = 0)
	var/icon/S
	var/w
	for(var/k = n, k >= 1, k--)
		var/icon/F
		for(var/list/L in layers)
			var/icon/C = Remaster3DCell(L[1], L[2], dir, fx ? (k - 1) * 4 + fx : k)
			if(!C) continue
			if(body64 && C.Width() < 64) C.Scale(64, 64)
			if(length(L) >= 5) RmLimbCut(C, L[5], dir, k)   // gear over a lost limb (LimbGear.dm)
			if(!F) F = C
			else F.Blend(C, ICON_OVERLAY)
		if(!F) return null
		if(n == 1) return F
		if(!S)
			w = F.Width()
			S = icon(F)
			S.Scale(w * n, F.Height())
			S.MapColors(0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0)
		else S.Shift(EAST, w)
		S.Blend(F, ICON_OVERLAY)
	return S

// A magic effect's facing for the page: a row per effect frame (4), each a strip of the
// unit picture's n frames. Rows are stacked as the strip's frames are: each laid at the
// top and the atlas shifted down.
var/list/remaster_3d_fx_cells = list()
proc/Remaster3DFxAtlas(list/fx, dir, n)
	var/icon/A
	for(var/f = 4, f >= 1, f--)
		var/icon/R = Remaster3DStrip(fx, dir, n, 0, f)
		if(!R) return null
		if(!A)
			A = icon(R)
			A.Scale(R.Width(), R.Height() * 4)
			A.MapColors(0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0)
		else A.Shift(SOUTH, R.Height())
		A.Blend(R, ICON_OVERLAY)
	return A

// With pz (a spread scene, the camera's level) a look never seen goes on over ticks: a safe point after its layers and
// before each facing's strip. Whatever the safe point says, the picture is finished (the scene stops at its own next
// one): an entry kept without its picture would stay so. Null for a unit gone while it waited.
Player/proc/Remaster3DUnitTextures(mob/M, pz = 0)
	// Playable races: the remastered 64 px body, the gear on it scaled up 2x.
	var/body64 = Remaster3DBody64(M)
	var/list/layers = Remaster3DLayers(M, body64)
	var/n = Remaster3DStripFrames(M, layers, body64)
	var/key = "[n]|"
	for(var/list/L in layers) key += "[length(L) >= 3 ? L[3] : L[1]]:[L[2]][length(L) >= 5 ? ":cut" : ""]|"   // a dragon-coloured picture: its own key (BeastParts.dm)
	// same picture as last time: reuse what this player already has
	if(M.remaster_3d_files && M.remaster_3d_key == key)
		if(!remaster_3d_sent) remaster_3d_sent = list()
		var/all_sent = 1
		for(var/f in M.remaster_3d_files + (M.remaster_3d_fx_files || list())) if(!remaster_3d_sent[f]) all_sent = 0
		if(all_sent) return M.remaster_3d_files
	var/list/files = list()
	if(pz)
		Remaster3DPauseLost(pz, rm3d_slice_build)
		if(Rm3DGone(M)) return null
	for(var/dir in list(SOUTH, NORTH, EAST, WEST))
		var/id = md5("[key][dir]")
		var/file = "r3u-[id].png"
		var/icon/R = remaster_3d_unit_cells[id]
		if(!R)
			if(pz)
				Remaster3DPauseLost(pz, rm3d_slice_build)
				if(Rm3DGone(M)) return null
			R = Remaster3DStrip(layers, dir, n, body64)
			if(!R) return null
			remaster_3d_unit_cells[id] = R
		if(!remaster_3d_sent) remaster_3d_sent = list()
		if(!remaster_3d_sent[file])
			remaster_3d_sent[file] = 1
			src << browse_rsc(R, file)
		files += file
	// Magic items' effects: an atlas per facing, which the page adds as light over the unit.
	var/list/fx = n == 5 ? RmGearFx(M, body64) : null
	var/list/fxfiles
	if(length(fx))
		fxfiles = list()
		for(var/dir in list(SOUTH, NORTH, EAST, WEST))
			var/id = md5("fx|[key][dir]")
			var/file = "r3x-[id].png"
			var/icon/X = remaster_3d_fx_cells[id]
			if(!X)
				X = Remaster3DFxAtlas(fx, dir, n)
				if(!X)
					fxfiles = null
					break
				remaster_3d_fx_cells[id] = X
			if(!remaster_3d_sent[file])
				remaster_3d_sent[file] = 1
				src << browse_rsc(X, file)
			fxfiles += file
	M.remaster_3d_key = key
	M.remaster_3d_files = files
	M.remaster_3d_frames = n
	M.remaster_3d_fx_files = fxfiles
	return files

// The far view: every 16x16 chunk within 10 chunks (160 tiles) of the camera, as
// 4x4 cells of one colour each (rock, trees, water, sand...), the same colours the
// world map uses, plus which cells this player has explored (the page draws the
// rest hazier). The land itself is shared by everyone and cached for 5 minutes.
// Only the surface has a horizon worth drawing.
#define REMASTER_3D_FAR_CHUNKS 10
var/list/remaster_far_cells = list()   // "cx,cy,z" -> list(cells, time)
var/remaster_far_refreshes = 0         // stale chunks re-read in this far view (max 12)
var/remaster_far_reads = 0             // new chunks read in this far view (max 60; the rest next time)
var/remaster_far_incomplete = 0

proc/Remaster3DFarCells(cx, cy, zz)
	var/key = "[cx],[cy],[zz]"
	var/list/E = remaster_far_cells[key]
	if(E && (world.time - E[2] < 3000 || remaster_far_refreshes >= 12)) return E[1]
	if(E) remaster_far_refreshes++
	else if(remaster_far_reads >= 60)
		remaster_far_incomplete = 1
		return list("", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "")
	else remaster_far_reads++
	var/list/cells = list()
	for(var/j = 0, j < 4, j++)
		for(var/i = 0, i < 4, i++)
			var/turf/T = locate(cx * 16 + i * 4 + 2, cy * 16 + j * 4 + 2, zz)
			cells += T ? RemasterTileColor(T) : ""
	remaster_far_cells[key] = list(cells, world.time)
	return cells

Player/proc/Remaster3DFar()
	var/zz = z == SKY_LAYER ? GROUND_LAYER : z   // up on the Sky level the far view is the surface's, drawn under it
	if(zz != 1) return list()
	var/cx = round((x - 1) / 16)
	var/cy = round((y - 1) / 16)
	var/list/L = remaster_explored ? remaster_explored["[zz]"] : null
	remaster_far_refreshes = 0
	remaster_far_reads = 0
	remaster_far_incomplete = 0
	var/maxc = round((world.maxx - 1) / 16)
	var/maxr = round((world.maxy - 1) / 16)
	var/list/out = list()
	for(var/a = max(0, cx - REMASTER_3D_FAR_CHUNKS), a <= min(maxc, cx + REMASTER_3D_FAR_CHUNKS), a++)
		for(var/b = max(0, cy - REMASTER_3D_FAR_CHUNKS), b <= min(maxr, cy + REMASTER_3D_FAR_CHUNKS), b++)
			var/list/rows = L ? L["[a],[b]"] : null
			var/seen = "0000000000000000"
			if(rows) seen = ""
			if(rows) for(var/j = 0, j < 4, j++)
				for(var/i = 0, i < 4, i++)
					var/s = 0
					if(rows) for(var/r = j * 4 + 1, r <= j * 4 + 4, r++) if(rows[r] & (15 << (i * 4))) s = 1
					seen += s ? "1" : "0"
			// with each tile's explored marks too, for the fog beyond the 3D window (the page's v3farFogBuild)
			if(rows) out += list(list(a, b, Remaster3DFarCells(a, b, zz), seen, rows))
			else out += list(list(a, b, Remaster3DFarCells(a, b, zz), seen))
	return out

// Figures in the far view: your own units beyond the detailed area (out to 160
// tiles), and whatever those units can see within 7 tiles (animals, monsters,
// other players), as the map would show around them. Nothing else, so the far view
// never shows what no unit of yours can see. list(x, y, kind): m mine, p player,
// a animal, n monster/npc.
#define REMASTER_3D_FAR_UNIT_SIGHT 7
// Made once (the owner, 10-31: "does things multiple itmes"): the walk over the whole company for its far units' rows
// (twice a second; 2,000 units: ~7 ms of DM a game second with their sights) is made only when the camera, the window or
// night moved, or the company list itself changed; otherwise the engine names the units whose change counter moved
// (rm_list_changed, native version 33, slot 2) and only their rows are made again, put in, or taken out, at their place
// in the company's order, so the list is the walk's own. The units that look round them come from the grid in that order.
Player/var/tmp/list/remaster_3d_far_rows    // your far units' rows (x, y, "m", sight), in UnitList order
Player/var/tmp/list/remaster_3d_far_rat     // each row's place in UnitList (parallel, rising)
Player/var/tmp/list/remaster_3d_far_of      // unit -> its row
Player/var/tmp/list/remaster_3d_far_place   // each unit in UnitList -> its place, as the last walk found it
Player/var/tmp/remaster_3d_far_rkey          // the camera, window and night the rows were made for

Player/proc/Remaster3DFarUnits()
	var/near = max(REMASTER_3D_HALF_W, REMASTER_3D_HALF_H)
	var/key = "[x],[y],[z],[near],[night]"
	var/list/R = rm_list_on && rm_grid ? rm_list_changed(src, 2, UnitList, 0) : null
	var/list/mine
	if(!R || R[3] || key != remaster_3d_far_rkey || !remaster_3d_far_rows) mine = Remaster3DFarWalk(near, key)
	else
		var/list/ch = R[1]
		var/list/pl = R[2]
		for(var/k = 1, k <= length(ch), k++) if(istype(ch[k], /mob/Monsters)) Remaster3DFarRow(ch[k], pl[k], near)
		if(rm_once_verify) Remaster3DFarVerify(near)
	var/list/out = remaster_3d_far_rows.Copy()
	if(!(remaster_3d_clock % 4) || !remaster_3d_far_seen)
		remaster_3d_far_seen = list()
		var/list/done = list()
		// only a unit with someone else near it looks (the owner, 10-31: "does things multiple itmes"): view(7) reaches 7
		// tiles, so a unit with none of the others within 7 tiles finds none of them, and its view() (225 tiles and all on
		// them, for each far unit every 2 s) is not made. Who else is about comes from the engine's unit grid: one look over
		// the far view, then round each of them for your units. With the grid off, every far unit looks, as before.
		var/list/eyes = Remaster3DFarEyes(near)
		if(!mine) mine = Remaster3DFarLookers(eyes)   // no walk: those of your units in reach that have someone near, in order
		for(var/mob/Monsters/M in mine)
			if(max(abs(M.x - x), abs(M.y - y)) <= near - REMASTER_3D_FAR_UNIT_SIGHT) continue
			if(eyes && !eyes[M])
				if(rm_once_verify) RmOnceCheck("far", Remaster3DFarSees(M, near, done), M)
				continue
			for(var/mob/Monsters/O in view(REMASTER_3D_FAR_UNIT_SIGHT, M))
				if(O.Owner == src || done[O] || O.invisibility || !isturf(O.loc)) continue
				done[O] = 1
				if(max(abs(O.x - x), abs(O.y - y)) <= near) continue
				remaster_3d_far_seen += list(list(O.x, O.y, ismob(O.Owner) ? "p" : O.Critter ? "a" : "n"))
				if(length(remaster_3d_far_seen) >= 150) break
	out += remaster_3d_far_seen
	return out

// The walk: your units in reach (on the map, this level, within 160 tiles) in order, and the rows of those beyond the
// window, each with its place in UnitList.
Player/proc/Remaster3DFarWalk(near, key)
	var/list/mine = list()
	var/list/rows = list()
	var/list/at = list()
	var/list/of = list()
	var/list/place = list()
	for(var/i = 1, i <= length(UnitList), i++)
		var/mob/Monsters/M = UnitList[i]
		if(!istype(M)) continue
		place[M] = i
		if(M.Owner != src || !isturf(M.loc) || M.z != z) continue
		var/d = max(abs(M.x - x), abs(M.y - y))
		if(d > 160) continue
		mine += M
		if(d > near)
			var/list/row = list(M.x, M.y, "m", (M.Egg || M.HP <= 0) ? 0 : RmFogRadius(M))   // and its sight, for the fog beyond the window
			rows += list(row)
			at += i
			of[M] = row
	remaster_3d_far_rows = rows
	remaster_3d_far_rat = at
	remaster_3d_far_of = of
	remaster_3d_far_place = place
	remaster_3d_far_rkey = key
	return mine

// One unit whose counter moved, at place p in UnitList: its row as it is now, put in or taken out where it belongs. A row
// still far is written over where it stands (every send's list is encoded the tick it is made, so one sent before is
// text already).
Player/proc/Remaster3DFarRow(mob/Monsters/M, p, near)
	var/far = 0
	if(M.Owner == src && isturf(M.loc) && M.z == z)
		var/d = max(abs(M.x - x), abs(M.y - y))
		far = d <= 160 && d > near
	var/list/old = remaster_3d_far_of[M]
	if(old && far)
		old[1] = M.x
		old[2] = M.y
		old[4] = (M.Egg || M.HP <= 0) ? 0 : RmFogRadius(M)
		return
	if(!old && !far) return
	var/list/row = far ? list(M.x, M.y, "m", (M.Egg || M.HP <= 0) ? 0 : RmFogRadius(M)) : null
	var/list/at = remaster_3d_far_rat
	var/lo = 1   // the first row at or after p (the places rise)
	var/hi = length(at) + 1
	while(lo < hi)
		var/mid = round((lo + hi) / 2)
		if(at[mid] < p) lo = mid + 1
		else hi = mid
	if(old)
		remaster_3d_far_rows.Cut(lo, lo + 1)
		at.Cut(lo, lo + 1)
		remaster_3d_far_of -= M
	else
		remaster_3d_far_rows.Insert(lo, list(row))
		at.Insert(lo, p)
		remaster_3d_far_of[M] = row

// Your units in reach with someone near them (the grid's eyes), in UnitList's order: those of the walk's units the look
// round them would come to.
Player/proc/Remaster3DFarLookers(list/eyes)
	var/list/L = list()
	var/list/K = list()
	for(var/mob/Monsters/M in eyes)
		var/p = remaster_3d_far_place[M]
		if(!p || !isturf(M.loc) || M.z != z || max(abs(M.x - x), abs(M.y - y)) > 160) continue
		L += M
		K += p
	RmSortBy(L, K)
	if(rm_once_verify)
		var/list/W = list()
		for(var/mob/Monsters/M in UnitList) if(M.Owner == src && isturf(M.loc) && M.z == z && max(abs(M.x - x), abs(M.y - y)) <= 160 && eyes[M]) W += M
		var/bad = length(W) != length(L)
		if(!bad) for(var/i = 1, i <= length(W), i++) if(W[i] != L[i]) bad = 1
		RmOnceCheck("farlook", bad, "[length(W)] [length(L)]")
	return L

// RM_ONCE_VERIFY: the rows as the walk would make them
Player/proc/Remaster3DFarVerify(near)
	var/list/F = list()
	for(var/mob/Monsters/M in UnitList)
		if(M.Owner != src || !isturf(M.loc) || M.z != z) continue
		var/d = max(abs(M.x - x), abs(M.y - y))
		if(d <= 160 && d > near) F += list(list(M.x, M.y, "m", (M.Egg || M.HP <= 0) ? 0 : RmFogRadius(M)))
	RmOnceCheck("farrows", json_encode(F) != json_encode(remaster_3d_far_rows), "[length(F)] [length(remaster_3d_far_rows)]")

// Your units with a unit not yours within REMASTER_3D_FAR_UNIT_SIGHT tiles (the only ones whose view() can find one), as
// an associative list; null when the engine's unit grid is off (every far unit looks). The grid holds every unit standing
// on the map (RmGrid.cs), the units view() lists here. Within 7 tiles goes both ways, so it looks round whichever side is
// fewer: the others round a big company, your units when other players' companies fill the far view (100 players: ~3,300
// others for 34 of yours, 2.9 ms a look round the others). Your units within the window less 7 tiles never look, so
// only those beyond it are looked round.
Player/proc/Remaster3DFarEyes(near)
	if(!rm_grid) return null
	var/list/eyes = list()
	var/s = REMASTER_3D_FAR_UNIT_SIGHT
	var/r = 160 + s
	var/list/others = list()
	var/list/mine = list()
	for(var/mob/Monsters/O in rm_grid_units(x - r, y - r, x + r, y + r, z))
		if(O.Owner == src)
			if(max(abs(O.x - x), abs(O.y - y)) > near - s) mine += O
		else if(!O.invisibility) others += O
	if(length(others) <= length(mine))
		for(var/mob/Monsters/O in others)
			for(var/mob/Monsters/M in rm_grid_units(O.x - s, O.y - s, O.x + s, O.y + s, z)) if(M.Owner == src) eyes[M] = 1
	else
		for(var/mob/Monsters/M in mine)
			for(var/mob/Monsters/O in rm_grid_units(M.x - s, M.y - s, M.x + s, M.y + s, z)) if(O.Owner != src && !O.invisibility)
				eyes[M] = 1
				break
	return eyes

// RM_ONCE_VERIFY: whether a far unit that didn't look would have found anyone (what its view() would have added)
Player/proc/Remaster3DFarSees(mob/Monsters/M, near, list/done)
	for(var/mob/Monsters/O in view(REMASTER_3D_FAR_UNIT_SIGHT, M))
		if(O.Owner == src || done[O] || O.invisibility || !isturf(O.loc)) continue
		if(max(abs(O.x - x), abs(O.y - y)) > near) return 1
	return 0

// A planted crop for the 3D view: which plant and how grown (1 sprout .. 5 ripe).
proc/Remaster3DCrop(obj/Items/Plants/P)
	var/st = "[P.icon_state]"
	var/stage = 1
	for(var/i = 5, i >= 1, i--) if(findtext(st, "[i]"))
		stage = i
		break
	var/ripe = P.Content >= 2
	if(istype(P, /obj/Items/Plants/RemasterHerbPlant)) return Remaster3DHerb(P)   // Doctor.dm
	var/kind = istype(P, /obj/Items/Plants/GrapeVine) ? "grape" : (istype(P, /obj/Items/Plants/TomatoPlant) ? "tomato" : "plant")
	return list("type"=kind, "stage"=stage, "ripe"=ripe)

// Which 3D model a thing gets (null: drawn from its own sprite). list(model, material, half)
proc/Remaster3DMaterial(t)
	if(findtext(t, "gold")) return "gold"
	if(findtext(t, "silver")) return "silver"
	if(findtext(t, "adamant")) return "adamantium"
	if(findtext(t, "metal") || findtext(t, "iron")) return "metal"
	if(findtext(t, "bone") || findtext(t, "rib")) return "bone"
	if(findtext(t, "obsidian") || findtext(t, "goblin")) return "obsidian"
	if(findtext(t, "stone") || findtext(t, "dwarf")) return "stone"
	if(findtext(t, "leather") || findtext(t, "silk")) return "leather"
	return "wood"

proc/Remaster3DObjModel(atom/A)
	var/t = lowertext("[A.type]")
	var/n = lowertext("[A.name]")
	var/mat = Remaster3DMaterial(t + " " + n)
	if(istype(A, /mob/WorkShops))
		if(istype(A, /mob/WorkShops/RemasterStall) || istype(A, /mob/WorkShops/RemasterCauldron) || istype(A, /mob/WorkShops/RemasterFood) || istype(A, /mob/WorkShops/RemasterClinic) || istype(A, /mob/WorkShops/RemasterSurgery) || istype(A, /mob/WorkShops/RemasterTavern) || istype(A, /mob/WorkShops/RemasterGraveyard)) return null
		// altars: pale holy stone, darker with each sacrifice on it, then an Evil Altar's black (HalfDemons.dm)
		if(istype(A, /mob/WorkShops/CampFires/EvilAltar)) return list("station:altar", "evil", null)
		if(istype(A, /mob/WorkShops/CampFires/GoodAltar)) return list("station:altar", "holy[A:rm_desecrated || ""]", null)
		if(istype(A, /mob/WorkShops/RemasterNoticeBoard)) return list("sign", "wood", null)   // Quests.dm
		var/half = findtext(t, "/right") ? "R" : (findtext(t, "/left") ? "L" : null)
		for(var/k in list("forge", "carpentry", "smelter", "kitchen", "masonary", "leatherworks", "bonecraft", "gemcutter", "potionstation", "poisonstation", "melter", "campfires", "altar"))
			if(findtext(t, k)) return list("station:[k == "campfires" ? (findtext(t, "altar") ? "altar" : "campfire") : k]", mat, half)
		return list("station:bench", mat, half)
	if(findtext(t, "/wagon")) return list("wagon", "wood", null)
	if(istype(A, /mob/Monsters/Chests)) return list("chest", mat, null)
	if(istype(A, /mob/Monsters/Egg)) return list("egg", lowertext("[A.icon_state]"), null)    // a spider's egg sac, a dragon's egg (Buildings.dm lairs)
	if(!isobj(A)) return null
	if(istype(A, /obj/Items/Traps/RemasterWeb)) return list("web", null, null)               // a sticky web (Buildings.dm)
	if(istype(A, /obj/Items/Furniture/RemasterCobweb)) return list("cobweb", null, null)
	if(istype(A, /obj/Items/Furniture/RemasterHoard)) return list("hoard[min(3, round(A:RemasterTreasure() / 5))]", "gold", null)
	if(istype(A, /obj/Items/Traps/Cages/Cacoon)) return list("cocoon", null, null)          // the spiders' cocoon (a cage)
	if(istype(A, /obj/Items/RemasterStake) && RmStakePlanted(A)) return list("stake", "wood", null)   // driven into the ground (Captives.dm)
	if(istype(A, /obj/Items/Traps/CacoonTrap)) return list("egg", "devourer", null)         // a Devourer's cocoon trap: a fleshy sac
	if(istype(A, /obj/Items/Furniture/Pillars/DwarfPillar)) return list("dwarfpillar", "stone", null)   // a carved dwarven pillar, up to a tunnel's roof
	if(istype(A, /obj/Items/Furniture/RemasterCart)) return list(length(A.contents) ? "minecartfull" : "minecart", "wood", null)   // Carts.dm
	if(istype(A, /obj/Items/Furniture/RemasterCartStop)) return list("cartstop", "wood", null)
	if(istype(A, /obj/Items/Furniture/RemasterPower)) return Remaster3DPowerModel(A)   // Power.dm: wheels, axles, bellows, dynamo
	if(istype(A, /obj/Items/Furniture/RemasterLiftHead)) return Remaster3DLiftModel(A)   // Lifts.dm: the far end of a lift
	if(istype(A, /obj/Items/RmBeastEgg)) return A:kind == "spider" ? list("egg", "spider", null) : list("beastegg", A:variant, null)   // Taming.dm
	if(istype(A, /obj/RmBeastNest)) return list("beastnest", A:kind, null)
	if(findtext(t, "/furniture/doors")) return list("door", mat, null)
	if(findtext(t, "/furniture/beds")) return list(findtext(t, "sleepingbag") ? "bedroll" : "bed", mat, null)
	if(findtext(t, "/furniture/tables")) return list("table", mat, null)
	if(findtext(t, "/furniture/chairs")) return list(findtext(t, "throne") ? "throne" : "chair", mat, null)
	if(findtext(t, "/furniture/pillars/woodenbeam")) return list("beam", "wood", null)    // a tunnel support (Construction.dm)
	if(findtext(t, "/furniture/pillars")) return list(findtext(t, "statue") ? "statue" : "pillar", mat == "wood" ? "stone" : mat, null)
	if(findtext(t, "/furniture/fences")) return list("fence", mat, null)
	if(findtext(t, "/furniture/posts")) return list("post", mat, null)
	if(findtext(t, "/traps/cages")) return list("cage", mat, null)
	if(findtext(t, "/traps/pittrap")) return list("pit", null, null)
	if(findtext(t, "/traps/spikes")) return list("spikes", mat, null)
	if(findtext(t, "/traps/ribtrap")) return list("ribtrap", "bone", null)
	if(findtext(t, "/traps/")) return list("trap", mat, null)
	if(findtext(t, "/shafts/sign")) return list("sign", "wood", null)
	if(findtext(t, "/items/woods/wood/bamboo")) return list("log", "bamboo", null)
	if(findtext(t, "/items/woods")) return list("log", "wood", null)
	if(findtext(t, "/ores/stone")) return list("stone", "stone", null)
	if(findtext(t, "/items/ores")) return list("ore", mat == "wood" ? "iron" : mat, null)
	if(findtext(t, "/items/gems")) return list("gem", null, null)
	if(findtext(t, "/items/ingots")) return list("ingot", mat == "wood" ? "metal" : mat, null)
	if(findtext(t, "/items/bones/bloodylimb")) return null   // a lost limb: never a 3D model; the animation's own limb is its look (gear3d.js), else its picture (the owner, 10-26)
	if(findtext(t, "/items/bones")) return list("bones", "bone", null)
	return null
