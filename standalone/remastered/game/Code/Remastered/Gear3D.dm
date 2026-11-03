// 3D gear and unit animations (art/gear3d, planning/ANIMATIONS_INTO_GAME.md). A unit on a 64 px body holding a weapon,
// shield or helmet that has a 3D look (Gear3DData.dm rm_g3_pieces) is sent with it (D["g3"]: its race sheet, and each
// piece as "style:tier"), and its picture leaves those layers out (View3D.dm Remaster3DLayers): the page draws them as
// palette pixel-art pieces in its hand and on its head (Interface/gear3d.js, put in the page at its rm-gear3d marker).
// The page's files (Interface/gear3d/: the pieces' pictures and meshes, the magic effects) go to each player once.
var/rm_g3_on = 1   // 0: every unit as before, its pieces drawn on its picture, and the page draws none
var/rm_g3_dolls = 1         // 1: units' moves, deaths, work and climbs drawn as dolls (gear3d.js); 0: as before stage 2
var/rm_g3_doll_deaths = 1   // with dolls on, 0: deaths drawn as before (the fading picture, then the body)
var/rm_g3_work_mine_chop = 0   // 1: mining and chopping drawn as dolls' work moves too; 0: with the unit's own attack frames, as before
                               // builds 27-28 (the user, 2026-10-26: "i think we should keep mining and chopping with their attack frames then")

Player/var/tmp/client/rm_g3_sent   // the connection that has the files

// The page with the gear and animation scripts in.
proc/RmG3Page(page)
	if(!rm_g3_on || !findtext(page, "<!--rm-gear3d-->")) return page
	var/js = file2text('Interface/gear3d.js')
	if(!js) return page
	return replacetext(page, "<!--rm-gear3d-->", "<script>window.G3GAME=1;window.G3NODOLLS=[rm_g3_dolls ? 0 : 1];window.G3NODEATHS=[rm_g3_doll_deaths ? 0 : 1];[js]</script>")

// The files the page fetches, once a connection, ahead of the page.
Player/proc/RmG3Send()
	if(!rm_g3_on || !client || rm_g3_sent == client) return
	rm_g3_sent = client
	for(var/f in rm_g3_files) src << browse_rsc(file("Interface/gear3d/[f]"), f)
	if(!remaster_3d_sent) remaster_3d_sent = list()
	RmSendFireFx()   // the burning deaths' flames are the dragons' pixel fire (deaths.js, Beasts.dm)

// An equipped piece's look in the catalogue's terms ("weapon.longsword.iron", "magic.flame staff"), or null: new gear by
// its id, the game's own by its new look (GearOldLooks.dm).
proc/RmG3Look(obj/Items/Equipment/E)
	if(E.rm_gear) return E.rm_gear
	var/list/N = rm_old_gear_looks["[RmOldGroup(E.icon)]|[E.icon_state]"]
	return N ? N[2] : null

// The race sheet a unit's pieces are placed on (anchors.json), or null: a playable race on its 64 px body, not a mist or
// a changed werewolf. Flying bodies and the dark-skinned humans wear theirs as on the walking body (Gear.dm).
proc/RmG3Sheet(mob/Monsters/M)
	if(!rm_g3_on || !remaster_3d_use64 || !istype(M) || M.IsMist || RmWerewolfSheet(M)) return null
	var/sheet = RmGearSheet(M)
	if(sheet in rm_gear_sheet_alias) sheet = rm_gear_sheet_alias[sheet]
	return rm_g3_sheets[sheet] ? sheet : null

// What it holds and wears in 3D: slot ("w", "s", "h") -> list(the item, "style:tier"); a magic piece is its style alone
// (its tier is its own, meshes.MAGIC_TIER). Null when nothing. Gear over a lost limb is gone (LimbGear.dm).
proc/RmG3Pieces(mob/Monsters/M)
	if(!RmG3Sheet(M)) return null
	var/list/slots = list("weapon"="w", "magic"="w", "shield"="s", "helmet"="h")
	for(var/obj/Items/Equipment/E in M) if(E.suffix == "(Equipped)")
		var/look = RmG3Look(E)
		if(!look) continue
		var/list/p = splittext(look, ".")
		if(length(p) < 2) continue
		var/slot = slots[p[1]]
		if(!slot || (. && .[slot])) continue
		if(!rm_g3_pieces["[p[1] == "magic" ? "weapon" : p[1]].[p[2]]"] || RmLimbGearGone(M, E)) continue
		if(!.) . = list()
		.[slot] = list(E, length(p) >= 3 ? "[p[2]]:[p[3]]" : p[2])

// The armed walk (hud-rework 10-27, the owner: "we need a new animation for when they have weapons held"): a unit on a
// 64 px body holding a weapon drawn in 3D walks with that arm at its side, gripping, while its legs and other arm walk:
// its sheet's "Armed" state (its standing frame's right arm on its walk frames, made from its own pictures by
// reports/polish-night-1026/hud-rework/sprites/armed/armed_walk.py) and its right-arm armour's "<state> armed"
// (Remaster3DLayers). The page holds the weapon at that kept hand (gear3d.js, D["g3"]["armed"]). Null without it.
proc/RmG3Armed(mob/M, body64)
	if(!body64 || !istype(M, /mob/Monsters)) return null
	var/mob/Monsters/U = M
	if(!U.HasRightArm || length(U.rm_limbs)) return null
	var/list/P = RmG3Pieces(U)
	if(!P || !P["w"]) return null
	// its pose's own armed frames; a pose its sheet has no state for draws the sheet's first one, so its armed frames are
	// the sheet's plain "Armed" (Human, Dwarf, Elf, Goblin, Lizardman, Frogman, Gargoyle and Vampire are "Normal" on a
	// sheet whose first state is unnamed: they never got the armed walk; the owner, 10-27: "all the playable races")
	var/list/S = RmGear64States("[body64]")
	var/st = U.icon_state ? "[U.icon_state] Armed" : "Armed"
	if(!(st in S) && U.icon_state && !(U.icon_state in S)) st = "Armed"
	return (st in S) ? st : null

proc/RmG3ArmedPiece(list/P)
	if(length(P) < 2) return P
	var/st = "[P[2]] armed"
	return (st in RmGear64States("[P[1]]")) ? list(P[1], st) : P

// What a hauler carries, as the page draws a load (work.js wkLoad): a log, a stone, ore, else a sack.
proc/RmG3CarryKind(mob/Monsters/M)
	for(var/obj/Items/I in M) if(I.suffix != "(Equipped)")
		if(istype(I, /obj/Items/woods)) return "log"
		if(istype(I, /obj/Items/ores/stone)) return "stone"
		if(istype(I, /obj/Items/ores)) return "ore"
	return "sack"

// A limb flung off (Combats.dm LimbFling): where it will come down (up to dist tiles its way, short of a wall), sent
// to the 3D view, which flies the doll's limb there.
proc/RmG3Limb(mob/M, part, d, dist, obj/I)   // I: the limb's item, so the page draws the animation's limb as its look
	if(!rm_g3_on || !isturf(M.loc)) return
	var/turf/T = M.loc
	for(var/i = 1, i <= dist, i++)
		var/turf/N = get_step(T, d)
		if(!N || N.density) break
		var/taken = 0
		for(var/atom/movable/A in N) if(A.density) taken = 1
		if(taken) break
		T = N
	var/key = I ? "|\ref[I]" : ""
	RemasterHitAt(M.x, M.y, M.z, 0, "limb", null, M.Owner, "limb|[part]|[T.x]|[T.y][key]")

// A dying unit's pieces, dropped (Death.dm): each on a tile of its own - a tile away from its killer (or a way of its
// own), its weapon most often, a helmet least - and the 3D view told where, so the doll's pieces land there.
proc/RmG3Drops(mob/Monsters/M, list/P)
	if(!rm_g3_on || !isturf(M.loc)) return
	var/away = ismob(M.Killer) && M.Killer != M ? get_dir(M.Killer, M) : 0
	for(var/slot in P)
		var/obj/Items/I = P[slot][1]
		if(!I || I.loc != M.loc) continue
		var/turf/T = M.loc
		if(prob(slot == "w" ? 75 : slot == "s" ? 55 : 35))
			var/d = away && prob(70) ? away : pick(NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST)
			var/turf/N = get_step(T, d)
			var/open = N && !N.density
			if(open) for(var/atom/movable/A in N) if(A.density) open = 0
			if(open)
				T = N
				I.loc = T
		RemasterHitAt(M.x, M.y, M.z, 0, "drop", null, M.Owner, "drop|[slot]|[T.x]|[T.y]|\ref[I]")

// A dying unit drops everything at once (Death.dm): its look is rebuilt once after the drops, not once for each piece
// taken off (stump-ticks, 10-29: each rebuild makes a new icon for every piece worn, ~0.6 ms, about 3 a death, and the
// unit is deleted a moment later). It ends with the same look: one rebuild from what it still wears.
mob/var/tmp/rm_look_hold = 0   // 1 while it drops all at once, 2 once a rebuild was asked for meanwhile
mob/RebuildOverlays()
	if(rm_look_hold)
		rm_look_hold = 2
		return
	return ..()

mob/proc/RmLookRelease()
	var/asked = rm_look_hold == 2
	rm_look_hold = 0
	if(asked) RebuildOverlays()

// Knocked out, a unit lets go of its weapon (the owner, 2026-10-26: "real item, on the ground others can take, if it has
// been unchanged when they get back up then they pick it up like normal"): it falls as a real item on its tile or the next
// (RmG3Drops: the 3D view's piece comes down there and is its look), and anyone may take it up. Coming to, a unit takes it
// back and holds it again if it still lies where it fell and is within reach; taken or moved, it is gone. A captive
// takes up no weapon. rm_ko_drops 0: the weapon stays in the hand, as before.
var/rm_ko_drops = 1
mob/Monsters/var/tmp/obj/Items/rm_ko_weapon   // what it let go of
mob/Monsters/var/tmp/rm_ko_weapon_at = ""      // "x,y,z" where it came down

proc/RmKoDrop(mob/Monsters/M)
	if(!rm_ko_drops || !istype(M) || !isturf(M.loc) || M.rm_ko_weapon) return
	var/obj/Items/W
	for(var/obj/Items/Equipment/E in M) if(E.suffix == "(Equipped)" && E.EquipmentType() == "Weapon")
		W = E
		break
	if(!W) return
	var/list/P = RmG3Pieces(M)   // its 3D piece, before it drops
	P = (P && P["w"] && P["w"][1] == W) ? list("w" = P["w"]) : null
	M.DropItem(W)
	if(!W || Rm3DGone(W) || !isturf(W.loc)) return   // an item that never drops (NoDropOnDeath) is gone
	if(P) RmG3Drops(M, P)   // a tile of its own, and the 3D view told where
	M.rm_ko_weapon = W
	M.rm_ko_weapon_at = "[W.x],[W.y],[W.z]"

proc/RmKoRetake(mob/Monsters/M)
	var/obj/Items/W = M.rm_ko_weapon
	var/at = M.rm_ko_weapon_at
	M.rm_ko_weapon = null
	M.rm_ko_weapon_at = ""
	if(!W || Rm3DGone(W) || !isturf(W.loc) || "[W.x],[W.y],[W.z]" != at) return   // taken up, or moved
	if(M.HP <= 0 || M.GoingToDie || M.rm_cap_state || !isturf(M.loc) || get_dist(M, W) > 1) return
	if(!M.ForcePickUpItem(W)) return
	if(M.HasRightArm && M.CanUseRightArm && !M.HoldingWeapon) M.ForceEquipItem(W)   // held again as it was (its own: no new skill check, Gear.dm)

// The items drawn in 3D, which its picture leaves out (Remaster3DLayers).
proc/RmG3Items(mob/M)
	if(!istype(M, /mob/Monsters)) return null
	var/list/P = RmG3Pieces(M)
	if(!P) return null
	. = list()
	for(var/slot in P) . += P[slot][1]

// For the page: list("sheet"=..., "w"="longsword:iron", "s"=..., "h"=..., "lost"=..., "arms"=1), or null. Every unit on an anchored
// sheet has one, holding something or not: its race's part map cuts its doll (game.js). "lost": the limbs it has lost,
// bits (1 right arm, 2 left arm, 4 right leg, 8 left leg), so its dolls are made without them.
Player/proc/RmG3Thing(mob/Monsters/M)
	var/sheet = RmG3Sheet(M)
	if(!sheet) return null
	RmG3Send()
	. = list("sheet" = sheet)
	var/list/P = RmG3Pieces(M)
	if(P) for(var/slot in P) .[slot] = P[slot][2]
	var/lost = (M.HasRightArm ? 0 : 1) | (M.HasLeftArm ? 0 : 2) | (M.HasRightLeg ? 0 : 4) | (M.HasLeftLeg ? 0 : 8)
	if(lost) .["lost"] = lost
	if(RmG3Armed(M, Remaster3DBody64(M))) .["armed"] = 1   // its picture walks with the weapon arm kept at its side
	for(var/obj/Items/Equipment/Armour/E in M) if(E.suffix == "(Equipped)" && (istype(E, /obj/Items/Equipment/Armour/LeftArm) || istype(E, /obj/Items/Equipment/Armour/RightArm)))
		.["arms"] = 1   // in arm armour: its sleeves are wider than the bare arm (parts.py's sleeved map)
		break
	var/list/W = RmG3Work(M)
	if(W) .["work"] = W
	var/datum/remaster_order/SO = M.remaster_active
	if(SO && SO.kind == "Scale" && !M.CliffClimber && !M.Flying && (locate(/obj/Items/RemasterTools/ClimbingGear) in M)) .["cg"] = 1   // climbs on a rope
	if(M.remaster_delivery) .["carry"] = RmG3CarryKind(M)   // hauling a load in (Jobs.dm): held before it as it walks (work.js)
	if(M.rm_bandaged_until > world.time) .["band"] = 1      // its stump bandaged (Stumps.dm): it stops bleeding

// What it is working at, for the page to play with the tool in hand (game.js g3jobs): list(job, x, y), or null. Only
// while it is at it, as each job's own state says: an order at its target (mining, chopping), a fishing spot beside it
// (by the way it fishes), a workshop it is making things at, a piece it has just built beside it.
mob/Monsters/var/tmp/turf/rm_g3_built   // the last piece it built (Blueprints.dm)
var/list/rm_g3_fish_jobs = list("rod"="fish", "harpoon"="spearfish", "net"="netfish", "cage"="netfish", "hand"="pick")
proc/RmG3Work(mob/Monsters/M)
	var/datum/remaster_order/O = M.remaster_active
	if(O && O.target)
		var/turf/T = RemasterTurf(O.target)
		if(T && max(abs(M.x - T.x), abs(M.y - T.y)) <= 1)
			if(O.kind in list("Mine", "Mine roof", "Dig down", "Carve ramp")) return rm_g3_work_mine_chop ? list("mine", T.x, T.y) : null   // else its attack frames (View3D.dm Remaster3DAct)
			if(O.kind == "Chop") return rm_g3_work_mine_chop ? list("chop", T.x, T.y) : null
			if(O.kind == "Lay block" && M.remaster_order_status == "Laying a block") return list("build", T.x, T.y)   // the hammer at the block (Sites.dm)
	var/obj/RemasterFishSpot/S = M.remaster_fish_spot
	if(S && S.loc && S.z == M.z && get_dist(M, S) <= 1)
		var/method = M.RemasterFishMethod(S)
		if(method && rm_g3_fish_jobs[method]) return list(rm_g3_fish_jobs[method], S.x, S.y)
	if(findtext("[M.remaster_work_status]", "Making ") == 1)
		for(var/mob/WorkShops/K in range(1, M)) if(K != M)
			return list(RmGearStationKey(K) == "forge" ? "smith" : "build", K.x, K.y)
	if(M.rm_g3_built && findtext("[M.remaster_work_status]", "Building ") == 1 && get_dist(M, M.rm_g3_built) <= 1)
		return list("build", M.rm_g3_built.x, M.rm_g3_built.y)
	return null

// A unit's death, for the 3D view to act out (game.js g3hit): a hit record of kind "die" whose projectile field is the
// cause (DeathType), struck from its killer's tile. A blow's own "kill" comes first and plays instead.
proc/RmG3Died(mob/Monsters/M)
	if(!rm_g3_on || !istype(M) || !isturf(M.loc)) return
	RemasterHitAt(M.x, M.y, M.z, 0, "die", ismob(M.Killer) ? M.Killer : null, M.Owner, "[M.DeathType]")
