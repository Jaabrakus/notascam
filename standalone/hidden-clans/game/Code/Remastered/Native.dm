// Native procs in the Remastered engine (planning/ENGINE_PLAN.md, engine/native/). Each is declared here with a DM
// body that says "not here": the Remastered runtime replaces the proc of the same name with its own (RmNative.cs),
// so on an engine without it the game runs the DM versions as before.
//   RM_NATIVE_PATH=0   don't use the engine's route search (it is used whenever the engine has it: proven identical to
//                      the DM search on 25,271 searches on the user's map, 22x faster; planning/ENGINE_PLAN.md)
//   RM_PATH_VERIFY=1   shadow mode: both searches run, the DM one is used, and any difference is logged
// Version 2 (2026-10-24): the search goes through units of the mover's side and never ends on one (Clip.dm); an engine
// without it (version 1) runs the DM search.
// Version 8: the engine's search has the own-door rule (Doors.dm RmOwnDoor, RmWalk.cs); it is given the door types. On
// an older engine with its search on, Doors.dm keeps the rule off (rm_own_doors), so the two searches still agree.

var/rm_native_path = 0
var/rm_path_verify = 0
var/rm_path_verified = 0      // searches compared in shadow mode
var/rm_path_differ = 0        // ...and how many differed
var/rm_native_doors = 0       // the engine's search knows the own-door rule (version 8)

// world/New: this file's part is step RmChainWorldNew_Native in Code/Remastered/Chains/WorldNew.dm

// The engine's version of these natives, or 0 on an engine without them.
proc/rm_native_version()
	return 0

// Change counters (version 6, 2026-10-24; the 3D view sends only the terrain chunks that changed, View3D.dm). In the
// engine (RmVer.cs): rm_chunk_ver(cx, cy, z) moves whenever a turf in 16x16 chunk cx = round((x - 1) / 16), cy likewise,
// of level z has a var written or is replaced; rm_ver(A) moves whenever movable A or anything in it has a var
// written, moves or changes its look (a turf: its chunk's number). Neither sees a list changed in place. These DM
// bodies give a new number every call: always changed.
//   RM_NATIVE_VER=0   don't use them (the 3D view builds the whole window every time, as before)
//   RM_VER_VERIFY=1   shadow mode: chunks the counters call unchanged are built anyway; a difference is logged
var/rm_native_ver = 0
var/rm_ver_verify = 0
var/rm_ver_fresh = 0
proc/rm_chunk_ver(cx, cy, z)
	return ++rm_ver_fresh
proc/rm_ver(A)
	return ++rm_ver_fresh
// Version 34 (RmVer.cs): a number that moves whenever a thing on a turf of 16x16 chunk (cx, cy) of level z changes (an obj
// lying there changed or arriving; a mob made there, deleted, or taken off or onto the map). A unit's step doesn't.
proc/rm_chunk_things_ver(cx, cy, z)
	return ++rm_ver_fresh

// The names of the caches and marks the game keeps on a thing, worked out from the rest of it (the HUD's marks and
// kept entries, portraits, 3D pictures and entries, a unit's kept health): writing them is not a change of the thing,
// so the 3D view's kept entries and the kept health hold while a unit stands still (the sends wrote the marks on every
// unit each send; server upgrades, 10-30). Given to the engine at start (RmVer.cs rm_ver_quiet); the DM body here does
// nothing (an engine without it: every write counts, as before). RM_VER_QUIET=0 keeps every write counted.
var/rm_ver_quieted = 0
var/list/rm_ver_quiet_names = list("rm_hud_mark", "rm_hud_smark", "rm_hud_dmark", "rm_hud_umark", "rm_view_rec",
	"rm_hud_entry", "rm_hud_entry_key", "rm_hud_entry_at", "rm_hud_entry_for", "rm_hud_entry_v", "rm_hud_entry_fp", "rm_hud_entry_until",
	"rm_hud_gmark", "rm_view_pass", "rm_view_i", "rm_view_rec_fp",
	"remaster_portrait_appearance", "remaster_portrait_south", "remaster_portrait_record", "remaster_portrait_serial",
	"remaster_3d_key", "remaster_3d_files", "remaster_3d_fx_files", "remaster_3d_frames", "rm3d_ent",
	"rm_life_ver", "rm_life_frac",
	// a unit's own timers and marks, written each pass (the engine's write trace, RM_VER_TRACE=1)
	"rm_walk_swept", "remaster_last_hp", "rm_held_at", "remaster_skill_seen", "rm_skill_seeded", "remaster_autouse_at",
	"rm_said_hp", "rm_help_called", "rm_wound_called", "SaidBleed", "rm_jz_free_in",
	"rm_move_row", "rm_move_row_ver", "rm_move_row_sp",   // View3D.dm Remaster3DMovesRows
	"rm_mana_none", "rm_skill_v",   // MagicGear.dm RmManaTick, Skills.dm RmSkillUnit
	"rm_view_cell", "rm_view_csel")   // HudView.dm RmViewPass's minimap cells
proc/rm_ver_quiet(names)
	return 0

// A sight circle marked into one level's explored chunks (native version 32, RmFog.cs; Fog.dm RmFogMarkCircle): 1 when a
// tile was new, else 0. The DM body: no answer (Fog.dm marks it itself).
proc/rm_fog_mark(list/L, cx, cy, r, maxx, maxy)
	return null

// The things in a list whose change counter moved since a caller's last look (native version 33, RmChanged.cs):
// list(changed, their places, 1 when everything is to be taken as changed). who, a player; slot, one of its uses:
// 1 the fog's side build (Fog.dm), 2 the 3D view's far figures (View3D.dm), 3 and 4 the HUD view pass's company (on the
// state counter) and its minimap (HudView.dm). The DM body: no answer (the callers walk).
proc/rm_list_changed(who, slot, list/L, state)
	return null
var/rm_list_on = rm_native_version() >= 33 && world.GetConfig("env", "RM_LIST_CHANGED") != "0"

// RM_ONCE_VERIFY=1 in the server's environment (tests): work a tick skips because nothing it reads has moved (the mana
// tick, the skill pass, the distant units' sight checks, the fog's marks; the owner, 10-31: "it rebuild entries multiple
// times or does things multiple itmes") is done anyway and compared. ONCEV lines in the log every 10 s: for each kind,
// how many were checked and how many came out different; the first difference of each kind, with what it was.
var/rm_once_verify = 0
var/list/rm_once_n = list()
var/list/rm_once_bad = list()
var/rm_once_at = 0
proc/RmOnceCheck(kind, bad, what)
	rm_once_n[kind] = (rm_once_n[kind] || 0) + 1
	if(bad)
		if(!rm_once_bad[kind]) world.log << "ONCEV|differs|[kind]|[what]"
		rm_once_bad[kind] = (rm_once_bad[kind] || 0) + 1
	if(world.time - rm_once_at >= 100)
		rm_once_at = world.time
		var/list/t = list()
		for(var/k in rm_once_n) t += "[k] [rm_once_n[k]] checked [rm_once_bad[k] || 0] different"
		world.log << "ONCEV|checked|[jointext(t, ", ")]"
proc/RmOnceVerifyStart()
	rm_once_verify = world.GetConfig("env", "RM_ONCE_VERIFY") == "1"
	if(rm_once_verify) world.log << "ONCEV|on"
	return rm_once_verify
var/rm_once_verify_started = RmOnceVerifyStart()

// A change counter that stands while a unit walks (native version 31, RmVer.cs; the owner, 10-31: "record rebuilt per
// second thats to much"): as rm_ver, less its own steps from tile to tile and writes of rm_ver_state_names, so what is
// worked out from a unit's state (the HUD's entries and view records, HudView.dm) holds while it walks. The DM body:
// rm_ver itself (every step counts, as before).
proc/rm_ver_state(A)
	return rm_ver(A)
proc/rm_ver_state_quiet(names)
	return 0
// motion, not state: a unit's step marks and walk timers (written each step), its facing, the needs that fall every few
// seconds, and what a walk sets and clears as it goes (its next tile, blocked, a target): the HUD reads those only as the
// thresholds and values it keeps in its prints itself (HudView.dm RmHudEntryOutside, RmViewRecPrint)
var/list/rm_ver_state_names = list("dir", "rm_came_from", "remaster_stepped_at", "rm_ground_steps", "rm_touched_x",
	"rm_touched_y", "rm_touched_span", "remaster_step_gap", "rm_walk_running", "rm_walk_due", "rm_walk_parked", "rm_walk_booked",
	"remaster_mate_wait", "Hunger", "Tiredness", "destination", "remaster_blocked", "Target",
	// the walk loop's own bookkeeping (WalkLoop.dm) and the 3D view's first-step mark (the engine's state trace, 2,000 walking)
	"rm_walk_idle", "rm_walk_listed", "rm_walk_gen", "rm_walk_step", "rm_walk_usr", "remaster_push_step",
	// timers and marks of the wild's look, morale, orders and strikes (the engine's state trace, 100 swarm players: each of
	// these moved companies' counters tens to hundreds of times a second; nothing worked out from state reads them)
	"rm_wild_seen", "rm_wander_rest", "rm_fight_at", "rm_morale_beat", "rm_morale_at", "rm_morale_p", "rm_morale_g",
	"rm_morale_why", "rm_given_serial", "rm_wound_in", "remaster_care_hold", "__od_collision_target")

// What a view draws (native version 35, RmVer.cs; the owner, 10-31: "those rebuilts are high arent they? shouldnt we get
// like 100?"): as rm_ver_state, less writes of rm_ver_shown_names, so the 3D scene's entries (View3D.dm
// Remaster3DEntryKey) hold while only a unit's card changes. Of ~500 entries a second made again at 100 players, ~490
// came out the same. The DM body: rm_ver_state itself.
proc/rm_ver_shown(A)
	return rm_ver_state(A)
proc/rm_ver_shown_quiet(names)
	return 0
// state no 3D entry reads (each name checked against every proc Remaster3DEntry calls, 10-31): the card's order status,
// current order and work line (the key holds what the entry draws of those itself: the tool at work, RmG3Work, and the
// block being laid, RmLay3D), the order list, coldness, morale, the digging zones, experience and skills, combat's marks
// and timers (the action and its swing are in the key: Remaster3DAct). The busiest first (the engine's state trace, 100
// swarm players)
var/list/rm_ver_shown_names = list("remaster_order_status", "remaster_active", "remaster_work_status", "remaster_orders",
	"Coldness", "rm_morale", "rm_dig_own", "rm_dig_zone", "EXP", "remaster_combat_last", "remaster_combat_foe",
	"remaster_defense", "rm_blunt_dmg", "SkillDMG", "rm_swing_at", "rm_swung_at", "UnArmedSkill", "remaster_defense_snooze",
	"remaster_opening", "rm_surround_blows", "rm_blunt_parts", "Killer", "remaster_work_since", "remaster_events",
	"rm_plan_wait", "rm_blood_seen", "remaster_striking",
	// the shown counter's own trace (reports/u5-hud-1031 section 14, 100 swarm players: the names behind the 3D entries made
	// again for nothing, each checked against every proc Remaster3DEntry calls): hit counters, weapon skills, crits, XP,
	// aim and move marks, speech, food aging in a pack; the organs' health, read only for the health the key holds itself
	"rm_age", "SpearSkill", "weight", "HitLowerBody", "HitUpperBody", "remaster_crawl_at", "HitRightLeg", "rm_crit",
	"HitLeftArm", "HitHead", "HitRightArm", "rm_clock_usr", "rm_mstate", "HitLeftLeg", "ReturningHome", "remaster_ui_id",
	"rm_fs_next", "HitNose", "HitLeftKidney", "HitRightLung", "HitGuts", "HitLiver", "HitLeftEar", "HitRightEar",
	"HitStomach", "remaster_reach_at", "HitLeftEye", "HitRightEye", "HitBrain", "HitSkull", "HitThroat", "HitSpleen",
	"HitHeart", "HitRightKidney", "HitWings", "HitTeeth", "HitLeftLung", "DamageType", "rm_crits", "rm_move_killing",
	"remaster_care_note", "rm_part_at", "SwordSkill", "rm_move_now", "rm_move_sure", "AxeSkill", "rm_aim_tick",
	"remaster_help_ready", "EXPNeeded", "weightmax", "rm_plan_last", "PoisonDMG", "WebContent", "MaxWebContent",
	"rm_aim_part", "Hostilities", "RangedSkill", "WeaponDamageMin", "WeaponDamageMax", "DodgeDelay", "rm_adrenaline",
	"remaster_throw_at", "rm_shot_part", "ArmourSkill", "rm_aim_beast", "ThrowingSkill", "rm_moves_last",
	"rm_npc_checked", "remaster_combat_seeded", "remaster_xp", "DefenceSkill", "rm_say", "rm_say_at", "BowSkill",
	"rm_spore_told", "remaster_hand_at", "remaster_auto_unload", "OnFire", "CanUseRightArm", "CanWalk", "ShieldSkill",
	"rm_move_skill", "rm_move_at", "Defence", "Fuel", "Liver", "CanUseLeftArm",
	"BrainHP", "GutsHP", "HeadHP", "HeartHP", "LeftArmHP", "LeftEarHP", "LeftEyeHP", "LeftKidneyHP", "LeftLegHP",
	"LeftLungHP", "LiverHP", "NoseHP", "RightArmHP", "RightEarHP", "RightEyeHP", "RightKidneyHP", "RightLegHP",
	"RightLungHP", "SpleenHP", "StomachHP", "ThroatHP")

// The units near a player's view that are new to it or changed since its last call (native version 27, RmGrid.cs; the
// 3D move rows, View3D.dm Remaster3DMovesChanged): list(changed, left, 1 when it is every unit). The DM body: no answer.
proc/rm_grid_changed(who, slot, x0, y0, x1, y1, z, mode)
	return null

// range(r, center)'s movables in its order, without its tiles (native version 28, RmRange.cs; the 3D scene, View3D.dm
// Remaster3DThings). The DM body: no answer (the caller uses range itself).
proc/rm_range_movables(r, center)
	return null

// The bytes still queued for who's browser tabs (native version 29, the web link; View3D.dm RmWebBehind). The DM body:
// never behind.
proc/rm_web_behind(who)
	return 0

// The HUD units delta's pass over the entries in the engine (native version 30, RmHud.cs; HUD.dm RemasterHUDUnitsDelta):
// list(codes, order, moved, full bytes, changed entries or null, their size). The DM body: no answer (the delta does it
// in DM, RmHudUnitsPass).
proc/rm_hud_units(list/units, list/old, list/parts, list/hot, full)
	return null

// 1: the delta uses rm_hud_units; RM_HUD_NATIVE=0 in the server's environment: the DM pass (tests, a way out)
var/rm_hud_native = -1
proc/RmHudNative()
	if(rm_hud_native < 0) rm_hud_native = world.GetConfig("env", "RM_HUD_NATIVE") == "0" ? 0 : 1
	return rm_hud_native

// RemasterOrderPathDM in the engine (RmPath.cs, RmWalk.cs): list(route or null, rm_path_partial), or null. With trace
// (tests only) a third item lists the tiles it took, in order.
proc/rm_path(mob/Monsters/M, turf/goal, reach, turf/bounds, radius, partial, list/pass, stairs, foot, monsters, ground, sky, list/side, siege, trace, door, trapdoor)
	return null

// Whether the DM search would take M's route on the Sky layer flat, as the engine's does (navigation plan E3,
// planning/NAVIGATION_PLAN_2026-10-27.md section 12). It keeps the block heights (Gather.dm RemasterLevelPathDM) only for
// a unit that can't climb standing over rock: Orders.dm RemasterOrderPathDM's first line sends climbers and flyers flat,
// and RemasterLevelPathDM's first lines send a unit with no places over its tile (a wall walk, an upper floor) flat. The
// same tests in the same order as the DM's, so the same procs run either way (RemasterSpotsOrNull may store a column's
// height or clear a dead ramp the first time it is read; the DM search reads the same tile first).
proc/RmSkyFlat(mob/Monsters/M)
	return RemasterCanClimb(M) || !RemasterSpotsOrNull(M.loc)

// The route search every order uses (Orders.dm, Formations.dm, Attack.dm and the rest).
proc/RemasterOrderPath(mob/Monsters/M, turf/goal, reach, turf/bounds = null, radius = 0, partial = 0)
	if(rm_nav_count && !rm_nav_in) return RmNavCountedPath(M, goal, reach, bounds, radius, partial)   // counted (navigation plan N0, below)
	if(rm_reach_built && !rm_reach_in) return RmReachPath(M, goal, reach, bounds, radius, partial)   // the reach map first (navigation plan N1, below)
	var/list/side = RmSide(M)   // through units of its side (Clip.dm)
	if(rm_native_path && (M.z != SKY_LAYER || RmSkyFlat(M)))   // up on a mountain the DM search keeps the block heights (Gather.dm), where it uses them (RmSkyFlat)
		var/list/R = rm_native_doors ? rm_path(M, goal, reach, bounds, radius, partial, rm_path_pass, 'Stairs.dmi', /obj/RmBeastFoot, /mob/Monsters, GROUND_LAYER, SKY_LAYER, side, /mob/Monsters/RemasterSiege, null, /obj/Items/Furniture/Doors, /obj/Items/Furniture/Doors/TrapDoor) : rm_path(M, goal, reach, bounds, radius, partial, rm_path_pass, 'Stairs.dmi', /obj/RmBeastFoot, /mob/Monsters, GROUND_LAYER, SKY_LAYER, side, /mob/Monsters/RemasterSiege)
		if(islist(R) && length(R) == 2)
			if(!rm_path_verify)
				rm_path_partial = R[2]
				return R[1]
			// shadow mode: the DM search decides; a difference is logged with what was asked
			var/list/D = RemasterOrderPathDM(M, goal, reach, bounds, radius, partial, side)
			rm_path_verified++
			if(!RmPathSameRoute(D, R[1]) || rm_path_partial != R[2])
				rm_path_differ++
				if(rm_path_differ <= 50) world.log << "RMPATH|shadow|differs|[M.type] at [M.x],[M.y],[M.z] to [goal ? "[goal.x],[goal.y],[goal.z]" : "null"]|reach=[reach] bounds=[bounds ? radius : 0] partial=[partial] pass=[length(rm_path_pass)]|DM [length(D)] tiles, partial [rm_path_partial]|engine [length(R[1])] tiles, partial [R[2]]"
			return D
	return RemasterOrderPathDM(M, goal, reach, bounds, radius, partial, side)

proc/RmPathSameRoute(list/A, list/B)
	if(isnull(A) || isnull(B)) return isnull(A) && isnull(B)
	if(length(A) != length(B)) return 0
	for(var/i = 1, i <= length(A), i++) if(A[i] != B[i]) return 0
	return 1

// Route search counts (navigation plan N0, planning/NAVIGATION_PLAN_2026-10-27.md): with RM_NAV_COUNT=1 in the server's
// environment every route search is counted by who asked (rm_path_who, set just before the call by the callers that
// name themselves; "other" for the rest), by where the unit stood and by how it ended, and so are the walk checks
// (Orders.dm RemasterWalkable) and the hover checks (HoverCheck.dm). Once a game minute, and on RmNavCountFlush(), one
// line goes to world.log: RMNAV|counts|t=<world.time>|<name>=<n>;... With the tick profiler on (RM_TICK_PROFILE=1) each
// search is also timed as "route search/<who>". Off (the default) nothing is counted. On, the game does the same: the
// only extra calls are reads the search makes first anyway (RemasterCanClimb, RemasterSpotsOrNull on the Sky layer) and,
// for an attack on one foe, a look at the 8 tiles round it (RmNavFoeFull: RemasterWalkable, which changes nothing; those
// looks add to the walk check count). No loop of its own: the call that finds the minute up writes the line.
var/rm_nav_count = 0
var/rm_nav_in = 0              // a counted search is running: its own call of RemasterOrderPath isn't counted again
var/rm_path_who                // who asks for the next search: set just before it, cleared by it
var/list/rm_nav_counts = list()
var/rm_nav_count_at = 0        // world.time of the next RMNAV line

proc/RmNavCount(name, n = 1)
	rm_nav_counts[name] = (rm_nav_counts[name] || 0) + n
	if(world.time >= rm_nav_count_at) RmNavCountFlush()
	return 1

proc/RmNavCountFlush()
	rm_nav_count_at = world.time + 600
	if(!length(rm_nav_counts)) return
	var/list/out = list()
	for(var/k in rm_nav_counts) out += "[k]=[rm_nav_counts[k]]"
	world.log << "RMNAV|counts|t=[world.time]|[jointext(out, ";")]"
	rm_nav_counts = list()

// RemasterOrderPath, counted: who asked, where the unit stood, how it ended, the route's length, and its time.
proc/RmNavCountedPath(mob/Monsters/M, turf/goal, reach, turf/bounds, radius, partial)
	var/who = rm_path_who || "other"
	rm_path_who = null
	var/where = "ground"
	if(M && M.z == SKY_LAYER) where = RemasterCanClimb(M) ? "sky, flyer or climber" : RemasterSpotsOrNull(M.loc) ? "sky, over rock" : "sky, off rock"
	else if(M && M.z == UNDERGROUND_LAYER) where = "underground"
	else if(M && M.z != GROUND_LAYER) where = "layer [M.z]"
	var/t0 = rm_prof ? RmProfIn() : 0
	var/w0 = world.time
	rm_nav_in = 1
	. = RemasterOrderPath(M, goal, reach, bounds, radius, partial)
	rm_nav_in = 0
	if(rm_prof) RmProf("route search/" + (findtext(who, ",") ? copytext(who, 1, findtext(who, ",")) : who), t0, w0)   // by caller only
	var/how = length(.) ? (rm_path_partial == 0 ? "found" : rm_path_partial == 1 ? "part of a long way" : "as close as it gets") : (rm_path_partial == 2 ? "no way" : "ran out")
	RmNavCount("search [who]: [how]")
	RmNavCount("search on [where]")
	if(length(.)) RmNavCount("route tiles [who]", length(.))

// Why a chase searches again (Attack.dm, Defense.dm): its first, its foe on another tile, its next step shut, or no route.
proc/RmNavChaseWhy(turf/was, turf/goal, list/path)
	return !was ? "first" : was != goal ? "foe moved" : length(path) ? "step blocked" : "no route"

// The attack search's name: a march to an attack-move's spot, or a foe, and whether every tile beside the foe is shut
// or held (a route can't end beside it).
proc/RmNavAttackWho(mob/Monsters/M, datum/remaster_attack/K, turf/goal, reach)
	var/why = RmNavChaseWhy(K.path_goal, goal, K.path)
	if(K.goal && goal == K.goal) return "attack-move march, [why]"
	if(reach > 1) return "attack from range, [why]"
	if(RmNavFoeFull(M, goal)) return "attack, foe has no free side, [why]"
	return "attack, [why]"

// No tile beside goal is one M's route could end on (open, no unit on it: RemasterWalkable 1).
proc/RmNavFoeFull(mob/Monsters/M, turf/goal)
	var/list/side = RmSide(M)
	for(var/turf/C in orange(1, goal)) if(C.z == goal.z && RemasterWalkable(C, M, goal, side) == 1) return 0
	return 1

// An order's search's name: the zone job's, a plan's, an automatic one's or a player's, its kind, and why it searches.
proc/RmNavOrderWho(datum/remaster_order/O, why)
	var/k = O.rm_jz ? "zone " : O.rm_plan ? "plan " : O.automatic ? "auto " : ""
	return k + lowertext("[O.kind]") + ", " + why

proc/RmNavWalkCount(turf/T)
	RmNavCount("walk checks")
	RmNavCount("walk check things on the tile", length(T.contents))

// The reach map (version 12; navigation plan N1 stage 1, planning/NAVIGATION_PLAN_2026-10-27.md; engine RmReach.cs): on
// the flat levels (ground, underground, hell; never the Sky layer), the areas a walking unit could get to through the
// ground at all, kept by the engine as tiles change. The owner's rule (10-27): the map may only ever be too hopeful. It
// calls a tile blocked only where the route search would for every unit it answers for, and leaves out everything that
// stands on tiles, so its "no" (rm_reach 0) is always the search's "no"; anything unsure is "maybe" (1) or "not known" (null).
// Its one use, exact (the same answers as before): a search whose caller reads only whether a route came back (the hover
// check, a group's free-tile check, defence; none of them reads rm_path_partial after) is answered null at once when the
// map says no way (rm_path_partial 2), where the search would have failed after up to 512 tiles.
// The safety net: one in RM_REACH_SAMPLE of those "no"s still runs the search (every one with RM_REACH_VERIFY=1), and
// every partial search that found the whole way asks the map too. A way found where the map said none is logged
// (RMREACH|wrong-no), counted, and the map goes off for good (today's searches, as before).
//   RM_REACH=0          never built (the engine's own switch too)
//   RM_REACH_VERIFY=1   every "no" is searched as well, and the search's answer is used
// Built once the world has loaded, before its tiles sleep (Regions.dm RmRegionsLoop; RMREACH|build logs it). The regions
// loop also gives the engine its turn to label a level afresh after tiles shut (RMREACH|relabel).
var/rm_reach = 0             // the engine has it (version 12) and RM_REACH isn't 0
var/rm_reach_verify = 0
var/rm_reach_built = 0       // built and trusted (a wrong "no" turns it off)
var/rm_reach_in = 0          // RmReachPath's own search is running
var/rm_reach_noes = 0        // searches the map answered "no way"
var/rm_reach_sample = 0
var/rm_reach_checked = 0     // "no"s searched anyway
var/rm_reach_wrong = 0       // a way found where the map said none
#define RM_REACH_SAMPLE 32
proc/rm_reach_build(stairs, monsters, sky)
	return 0
proc/rm_reach(mob/Monsters/M, turf/goal, reach)
	return null
proc/rm_reach_tick()
	return 0
proc/rm_reach_stats()
	return null
proc/rm_reach_audit(z)
	return null
proc/rm_reach_off()
	return null

proc/RmReachBuild()
	var/n = rm_reach_build('Stairs.dmi', /mob/Monsters, SKY_LAYER)
	rm_reach_built = n > 0
	world.log << "RMREACH|build|levels=[n]|[rm_reach_stats()]"

proc/RmReachTick()
	var/ms = rm_reach_tick()
	if(ms) world.log << "RMREACH|relabel|[ms] ms|[rm_reach_stats()]"

// The map's answer is "no way through the ground at all".
proc/RmReachNo(mob/Monsters/M, turf/goal, reach)
	var/r = rm_reach(M, goal, reach)
	return isnum(r) && r == 0

// RemasterOrderPath with the reach map in front (see above).
proc/RmReachPath(mob/Monsters/M, turf/goal, reach, turf/bounds, radius, partial)
	if(!partial && RmReachNo(M, goal, reach))
		rm_reach_noes++
		if(!rm_reach_verify && ++rm_reach_sample < RM_REACH_SAMPLE)
			rm_path_partial = 2
			return null
		rm_reach_sample = 0
		rm_reach_checked++
		rm_reach_in = 1
		. = RemasterOrderPath(M, goal, reach, bounds, radius, partial)
		rm_reach_in = 0
		if(.) RmReachWrong(M, goal, reach, "a search found the way")
		return .
	rm_reach_in = 1
	. = RemasterOrderPath(M, goal, reach, bounds, radius, partial)
	rm_reach_in = 0
	if(partial && . && rm_path_partial == 0 && RmReachNo(M, goal, reach)) RmReachWrong(M, goal, reach, "a partial search found the whole way")

proc/RmReachWrong(mob/Monsters/M, turf/goal, reach, why)
	rm_reach_wrong++
	rm_reach_built = 0
	world.log << "RMREACH|wrong-no|[why]|[M.type] at [M.x],[M.y],[M.z] to [goal ? "[goal.x],[goal.y],[goal.z]" : "null"]|reach=[reach]|[rm_reach_stats()]"
	rm_reach_off()

// The battle ways (version 13, RmField.cs; the owner, 10-28: "have the world preplan the best routes so everyone can fight
// gangup", then "native C# could do it in ~1m then we should do it in native"): a field kept by the engine for one side's
// units in a 32x32 chunk against one foe realm, every tile's steps to the nearest free tile beside a standing foe of it,
// made again at most every half second of game time and shared by all of them. A fighter takes its route down the field
// (Attack.dm RmGangUp) instead of a route search. The DM body says "not here": the game's own chase runs.
//   RM_FIELD=0   don't use it (the engine's own switch too)
var/rm_field = 0
proc/rm_field_route(mob/Monsters/M, foe, key, now, stairs, foot, monsters, ground, sky, list/side, siege, door, trapdoor)
	return null
proc/rm_field_stats()
	return null

// M's route down its side's field against the units of foe (an owner): a list of tiles (empty: every place to fight from
// near is taken, it waits its turn), 0 (no free tile beside one it can get to near), or null (not known).
proc/RmFieldRoute(mob/Monsters/M, foe)
	if(!rm_field || !foe || !M.Owner) return null
	return rm_field_route(M, foe, "\ref[M.Owner]>\ref[foe]", world.time, 'Stairs.dmi', /obj/RmBeastFoot, /mob/Monsters, GROUND_LAYER, SKY_LAYER, RmSide(M), /mob/Monsters/RemasterSiege, rm_own_doors ? /obj/Items/Furniture/Doors : null, rm_own_doors ? /obj/Items/Furniture/Doors/TrapDoor : null)

// Morale's look round (version 14, RmMorale.cs; the owner, 10-28: "Yes, morale next"): Morale.dm RmMoraleTick's count of
// the units within 4 tiles (its friends, its foes and those beside it), read by the engine from the unit grid, rule for rule
// as its DM loop and RemasterHostile, which stay as the fallback and the reference. A player's war and alliance with each
// other player met is worked out once a tick here (RmVerdict) and given to the engine. The engine also looks for a royal of
// its own within 6 (RmMoraleRallied's second half) when the rally could apply. The DM body says "not here".
//   RM_MORALE_NATIVE=0   don't use it
//   RM_MORALE_VERIFY=1   shadow mode: both run, the DM loop's counts are used, and any difference is logged (RMMORALE|differs)
var/rm_morale_native = 0
var/rm_morale_verify = 0
var/rm_morale_checked = 0     // looks compared in shadow mode
var/rm_morale_differ = 0      // ...and how many differed
proc/rm_morale_look(mob/Monsters/M, r, royal_r, now, chests, siege, player, list/verdicts)
	return null

Player/var/tmp/list/rm_verdicts     // this tick's war and alliance with each other player met in morale's looks
Player/var/tmp/rm_verdicts_at = -1
Player/proc/RmVerdicts()
	if(rm_verdicts_at != world.time || !rm_verdicts)
		rm_verdicts_at = world.time
		rm_verdicts = list()
	return rm_verdicts

// As RemasterHostile's pairs: 1 allied (never a foe), 2 at war, 3 at peace (a foe only when one attacked the other lately).
proc/RmVerdict(Player/P, Player/O)
	if(RemasterAllied(O, P)) return 1
	return RemasterAtWar(P, O) ? 2 : 3

// The engine's look round M: list(foes, beside, allies but M, royal near or null), or null (the DM loop).
proc/RmMoraleLook(mob/Monsters/M)
	var/Player/P = M.Owner
	var/list/V = istype(P) ? P.RmVerdicts() : null
	var/rr = istype(P) && M.rm_morale < rm_morale_rally_max ? 6 : 0
	var/list/L = rm_morale_look(M, 4, rr, world.time, /mob/Monsters/Chests, /mob/Monsters/RemasterSiege, /Player, V)
	if(!islist(L)) return null
	if(L[5])   // players not judged yet this tick: judged, and looked again
		for(var/Player/O in L[5]) V[O] = RmVerdict(P, O)
		L = rm_morale_look(M, 4, rr, world.time, /mob/Monsters/Chests, /mob/Monsters/RemasterSiege, /Player, V)
		if(!islist(L) || L[5]) return null
	for(var/mob/Monsters/S in L[6]) if(RemasterHostile(M, S, 0))   // a siege engine: its own rule (Attack.dm)
		L[1]++
		if(get_dist(M, S) <= 1) L[2]++
	return L

// The foes beside a fighter (version 22, RmSight.cs; the owner, 10-29: "Morale + foe look"): Attack.dm RmFoeBeside looked
// over the units round a fighter on every gang-up pass, ~2,900 a second in a 1000 v 1000 and nearly all finding nobody of
// that realm (~12 us each). The engine reads the same tiles from the unit grid and says whether any unit of that realm
// stands on them (its owner not the fighter's, and the foe); nobody, and RmFoeBeside answers null at once. Someone, and
// its DM look picks one by every rule as before. (Version 22 also made morale's look faster, with no game change.)
//   RM_FOE_BESIDE=0          don't use it
//   RM_FOE_BESIDE_VERIFY=1   shadow mode: the DM look runs every time, and one that finds a foe where the engine said
//                            nobody is logged (RMFOEBESIDE|differs)
var/rm_foe_beside_native = 0
var/rm_foe_beside_verify = 0
var/rm_foe_beside_checked = 0
var/rm_foe_beside_differ = 0
proc/rm_foe_beside(mob/Monsters/M, foe, monsters)
	return null

proc/RmFoeBesideVerify(mob/Monsters/M, mob/Monsters/best)
	if(!(++rm_foe_beside_checked % 20000)) world.log << "RMFOEBESIDE|checked|[rm_foe_beside_checked]|differ|[rm_foe_beside_differ]"
	if(!best) return
	rm_foe_beside_differ++
	if(rm_foe_beside_differ <= 20) world.log << "RMFOEBESIDE|differs|[M.type] at [M.x],[M.y],[M.z]|the DM look found [best.type] at [best.x],[best.y]"

proc/RmMoraleVerify(mob/Monsters/M, list/L, foes, beside, allies)
	if(!(++rm_morale_checked % 5000)) world.log << "RMMORALE|checked|[rm_morale_checked]|differ|[rm_morale_differ]"
	var/royal = isnull(L[4]) ? null : M.RmMoraleRoyalNear()
	if(L[1] == foes && L[2] == beside && L[3] + 1 == allies && (isnull(royal) || royal == L[4])) return
	rm_morale_differ++
	if(rm_morale_differ <= 30) world.log << "RMMORALE|differs|[M.type] at [M.x],[M.y],[M.z]|DM foes [foes] beside [beside] allies [allies] royal [royal]|engine foes [L[1]] beside [L[2]] allies [L[3] + 1] royal [L[4]]"

// An attack box's next foe, ranked by the engine (version 15, RmPool.cs; the owner, 10-28: "Yes, box re-pick"):
// Formations.dm RemasterPoolNext looked at every foe of the box for every pick (about 6 ms a pick in a 500 v 500). The
// engine drops those the look drops (gone, or no longer one it may fight: RemasterHostile with explicit 1, by the realms'
// verdicts) and ranks the rest by the lowest score each could have; the game looks at them in that order with its own
// down, fog, room and score rules and stops when no later one can score lower (RmPoolWalk): the same foe as the whole look.
// One difference: the look kept each foe's room for up to 5 s once it had looked (RmReachFor's cache), and this looks at
// fewer, so a foe's room is worked out when it is first needed: never older than the look's, sometimes newer.
//   RM_POOL_NATIVE=0   don't use it (the whole look, as before)
//   RM_POOL_VERIFY=1   shadow mode: both, the whole look's foe used, any difference logged (RMPOOL|differs)
var/rm_pool_native = 0
var/rm_pool_verify = 0
var/rm_pool_checked = 0
var/rm_pool_differ = 0
proc/rm_pool_rank(mob/Monsters/M, list/pool, list/load, list/far_on, far, now, list/verdicts, monsters, player, chests, siege)
	return null

// The engine's ranking of K's box for M (list(foes, lowest scores, down, dropped, unknown, places)); the dropped leave the
// box here, as the whole look drops them. null: the whole look.
proc/RmPoolRank(mob/Monsters/M, datum/remaster_attack/K, far)
	if(length(rm_fort_in) && rm_fort_in[M]) return null   // in a fort try: the DM look, which knows tries (QuestForts.dm)
	var/Player/P = M.Owner
	var/list/V = istype(P) ? P.RmVerdicts() : null
	var/list/R = rm_pool_rank(M, K.pool, K.pool_load, K.pool_far, far, world.time, V, /mob/Monsters, /Player, /mob/Monsters/Chests, /mob/Monsters/RemasterSiege)
	if(!islist(R)) return null
	if(R[5])   // players not judged yet this tick: judged, and ranked again
		for(var/Player/O in R[5]) V[O] = RmVerdict(P, O)
		R = rm_pool_rank(M, K.pool, K.pool_load, K.pool_far, far, world.time, V, /mob/Monsters, /Player, /mob/Monsters/Chests, /mob/Monsters/RemasterSiege)
		if(!islist(R) || R[5]) return null
	for(var/mob/Monsters/E in R[4])
		K.pool -= E
		K.pool_load -= E
		K.pool_far -= E
	return R

proc/RmPoolVerify(mob/Monsters/A, mob/Monsters/B)
	if(!(++rm_pool_checked % 500)) world.log << "RMPOOL|checked|[rm_pool_checked]|differ|[rm_pool_differ]"
	if(A == B) return
	rm_pool_differ++
	if(rm_pool_differ <= 30) world.log << "RMPOOL|differs|engine [A ? "[A.x],[A.y]" : "none"]|look [B ? "[B.x],[B.y]" : "none"]"

// The worked trees and rocks' tidy (version 16, RmWorked.cs; the owner, 10-28: "Yes, harvest next"): Breaking.dm
// RemasterWorkTidy's loop over rm_worked, step for step in the engine. With 400 entries (RM_WORKED_MAX) every first blow on a
// new tile ran it; a 2,000-worker village works more tiles than that at once, so it ran dozens of times a game second. The
// DM body says "not here".
//   RM_WORKED_NATIVE=0   don't use it
//   RM_WORKED_VERIFY=1   shadow mode: the DM loop also runs on a copy, and any difference is logged (RMWORKED|differs)
var/rm_worked_native = 0
var/rm_worked_verify = 0
var/rm_worked_checked = 0
var/rm_worked_differ = 0
proc/rm_worked_tidy(list/L, now, max, full)
	return null

proc/RmWorkedVerify(list/C, full)   // C: rm_worked as it was; the DM loop on it against the engine's result
	RmWorkTidyDM(C, full)
	if(!(++rm_worked_checked % 200)) world.log << "RMWORKED|checked|[rm_worked_checked]|differ|[rm_worked_differ]"
	var/same = length(C) == length(rm_worked)
	if(same) for(var/i = 1, i <= length(C), i++) if(C[i] != rm_worked[i])
		same = 0
		break
	if(same) return
	rm_worked_differ++
	if(rm_worked_differ <= 30) world.log << "RMWORKED|differs|DM [length(C)] entries, engine [length(rm_worked)]|full [full]"

// A delivery's store tile (version 17, RmStore.cs; the owner, 10-28: "Yes, deliveries next"): Jobs.dm RmJzStoreFor's loop
// over each store zone's cells, with the crowd round each cell and the carriers sent to it, in the engine (0.69 ms a
// delivery in the game's script with 2,000 workers). Whether a zone takes the load stays the game's (RmJzZoneTakesLoad),
// asked at the same point. The DM body says "not here".
//   RM_STORE_NATIVE=0   don't use it
//   RM_STORE_VERIFY=1   shadow mode: the DM loop too, its tile used, any difference logged (RMSTORE|differs)
var/rm_store_native = 0
var/rm_store_verify = 0
var/rm_store_checked = 0
var/rm_store_differ = 0
proc/rm_store_scan(list/cells, mob/Monsters/M, turf/not_this, bc, takes, list/aim, crowd_w, monsters)
	return null

// The lying items' timer (version 18, RmDecay.cs; the owner, 10-28: "Yes, item timers"): every item put down ran its own
// 2006 countdown loop (Items/Item Procs.dm atom/DeleteItem), awake every second while it lay, for ever on a stockpile
// (about 1.8 ms of every tick per 10,000 items lying, growing as stores fill). With the engine's timer, DeleteItem
// (FoodRoles.dm) makes the loop's first pass and hands the item over; the timer makes the later passes on the same ticks,
// and an item past 180 comes back here for the 2006 rule (RmDecayOver). The DM bodies say "not here".
//   RM_DECAY_NATIVE=0   don't use it: each item's own loop, as before
var/rm_decay_native = 0
proc/rm_decay_add(atom/I, now)
	return 0
proc/rm_decay_tick(now)
	return null
proc/rm_decay_count()
	return 0

// Past 180 counts: the loop's rule (Item Procs.dm), kept on a stockpile, else gone.
proc/RmDecayOver(atom/I)
	if(I.RemasterOnStockpile()) I.Content3 = 1 // Remastered: stockpiled items are kept
	else del(I)

proc/RmDecayLoop()
	while(rm_decay_native)
		var/list/L = rm_decay_tick(world.time)
		for(var/atom/I in L) RmDecayOver(I)
		sleep(1)

// The route map (version 19, RmRoute.cs; the owner, 10-29: "we want them to go around the mountain we dont want them to
// stop", and "Yes, group routes"): the route search looks at 512 tiles at most, and a way round a long ridge is longer, so a
// unit went to the rock face nearest its goal and stood there. The engine spreads a map out from the goal over the ground
// (units passed over: they move), up to 96 tiles round it, and reads a unit's whole way down it; every unit of a player
// going to the same goal in the next 5 s reads the same map (a group's members, Formations.dm). Used where the search
// gave no step at all (the nearest point it found is where the unit stands: the rock face) while the reach map doesn't say
// there is no way through (Orders.dm, Attack.dm; a long trip whose part of the way goes on is walked in legs as before),
// and by a group's members still far from their slots. The DM
// body says "not here": the search's part of the way, as before.
//   RM_ROUTE=0   don't use it (the engine's own switch too)
var/rm_route = 0
proc/rm_route_map(mob/Monsters/M, turf/goal, reach, key, now, turf/stop_at, stop_d, stairs, foot, monsters, ground, sky, door, trapdoor, list/known)
	return null
proc/rm_route_stats()
	return null

// M's whole way to within reach of goal down the route map, ending where it first comes within stop_d of stop_at when
// given: a list of tiles; 0 no way there within the map; null not known.
// With fog of war, the map is made from what M's player knows (the owner, 10-29: "if they hit a dead end thats correct if
// they never been that way before we have to use fog of war and what they know"): a tile its player never explored
// (Explore.dm) counts as open, so a unit sent past rock nobody has seen walks up to it, sees it, and its next plan goes round.
proc/RmRouteMap(mob/Monsters/M, turf/goal, reach, turf/stop_at = null, stop_d = 0)
	if(!rm_route || !M || !goal) return null
	var/Player/P = M.Owner
	var/list/known = istype(P) && RmFogOn(goal.z) ? ((P.remaster_explored && P.remaster_explored["[goal.z]"]) || list()) : null
	return rm_route_map(M, goal, reach, "\ref[M.Owner][known ? "|fog" : ""]", world.time, stop_at, stop_d, 'Stairs.dmi', /obj/RmBeastFoot, /mob/Monsters, GROUND_LAYER, SKY_LAYER, rm_own_doors ? /obj/Items/Furniture/Doors : null, rm_own_doors ? /obj/Items/Furniture/Doors/TrapDoor : null, known)

// Its goal further than it sees now, with fog of war, and ground its player never explored on the way: the way from what
// its player knows, the route map's (Orders.dm). Where all of it is explored, the search (which sees the ground itself)
// finds the same way, more cheaply (a village's work trips: a map each made the work orders' closing in twice as dear).
mob/Monsters/proc/RmRouteByKnowing(turf/goal)
	return rm_route && istype(Owner, /Player) && RmFogOn(goal.z) && get_dist(src, goal) > RmFogRadius(src) && !RmKnowsWay(goal)

// Every 16x16 chunk of the box round it and goal (4 tiles more each way) wholly explored by its player (Explore.dm).
mob/Monsters/proc/RmKnowsWay(turf/goal)
	var/Player/P = Owner
	var/list/L = P.remaster_explored ? P.remaster_explored["[goal.z]"] : null
	if(!L) return 0
	var/x0 = max(1, min(x, goal.x) - 4)
	var/x1 = min(world.maxx, max(x, goal.x) + 4)
	var/y0 = max(1, min(y, goal.y) - 4)
	var/y1 = min(world.maxy, max(y, goal.y) + 4)
	for(var/cy = round((y0 - 1) / 16), cy <= round((y1 - 1) / 16), cy++)
		for(var/cx = round((x0 - 1) / 16), cx <= round((x1 - 1) / 16), cx++)
			var/list/rows = L["[cx],[cy]"]
			if(!rows) return 0
			for(var/r in rows) if(r != 65535) return 0
	return 1

// An order's search gave no step nearer (rm_path_partial set, no route) and the reach map knows of no wall all round: the
// route map's whole way instead, when it
// has one. 1 when taken.
mob/Monsters/proc/RmRouteInstead(datum/remaster_order/O, turf/goal, reach, turf/stop_at = null, stop_d = 0, map_goal = null)
	var/list/R = RmRouteMap(src, map_goal || goal, map_goal ? 1 : reach, stop_at, stop_d)
	if(!islist(R) || !length(R)) return 0
	O.path = R
	O.partial = stop_at && R[length(R)] != goal ? 1 : 0   // to the group's slot's neighbourhood: part of the way, searched on from there
	return 1

// The plain step (version 21, RmStep.cs; the owner, 10-29: "Native plain step"). In a 1000 v 1000 a unit's step was
// ~55 us, and the walkable checks round it (44,000 a second) cost more than the steps (reports/polish-night-1026/step-native).
// - The game's walkable checks (Orders.dm RemasterWalkable) are the engine's copy, rule for rule as RemasterWalkableDM (the
//   route search's own, RmWalk.cs), with the types set once.
// - A step onto a plain tile (Chains/Move.dm, the bottom) is the engine's: the ground's Enter chain answered rule for rule
//   and the unit moved, without the standard Move's calls that do nothing (Exit and Uncross on the old tile and everything
//   lying on it, Exited, Uncrossed, Crossed: no type of the game has its own); then the ground's own Entered here, or the
//   bump the standard Move makes. Doors, wall-walks, cursed grass, another area, another turf's Enter: the standard Move.
//   RM_WALK_NATIVE=0 / RM_STEP_NATIVE=0   don't use them
//   RM_WALK_VERIFY=1 / RM_STEP_VERIFY=1   shadow modes: the game's own answer is used, any difference logged (RMWALK|differs,
//   RMSTEP|differs)
var/rm_walk_native = 0
var/rm_walk_verify = 0
var/rm_walk_checked = 0
var/rm_walk_differ = 0
var/rm_step_native = 0
var/rm_step_verify = 0
var/rm_step_checked = 0
var/rm_step_differ = 0
var/rm_step_plainc = 0     // shadow mode: steps the engine answered...
var/rm_step_odd = 0        // ...and ones it left to the standard Move
proc/rm_step_setup(stairs, foot, monsters, siege, door, trapdoor, ground, sky, grounds)
	return 0
proc/rm_step(mob/Monsters/M, turf/T, Dir, list/side, list/pass, doors, decide)
	return null
proc/rm_walk(turf/T, mob/Monsters/M, turf/goal, list/side, list/pass, doors)
	return null

proc/RmStepSetup()
	return rm_step_setup('Stairs.dmi', /obj/RmBeastFoot, /mob/Monsters, /mob/Monsters/RemasterSiege, /obj/Items/Furniture/Doors, /obj/Items/Furniture/Doors/TrapDoor, GROUND_LAYER, SKY_LAYER, /turf/grounds) == 1

proc/RmWalkVerify(turf/T, mob/Monsters/M, turf/goal, list/side, w)
	var/d = RemasterWalkableDM(T, M, goal, side)
	if(!(++rm_walk_checked % 50000)) world.log << "RMWALK|checked|[rm_walk_checked]|differ|[rm_walk_differ]"
	if(d == w) return
	rm_walk_differ++
	if(rm_walk_differ <= 30) world.log << "RMWALK|differs|[T.x],[T.y],[T.z]|[M ? M.type : "-"]|DM [d] engine [w]"

// The step onto T by the engine (1 moved, 0 blocked), or null: the standard Move's (Chains/Move.dm).
mob/Monsters/proc/RmStepPlain(turf/T, Dir)
	if(rm_step_scan_check || rm_nav_count || !isturf(T)) return null
	if(remaster_active && remaster_active.kind == "Hop" && remaster_active.target == T) return null   // onto the top it hops down from: the standard Move (Chains/Enter.dm lets it onto its own people there)
	var/atom/was = loc
	var/r = rm_step(src, T, Dir, usr == src ? RmSide(src) : null, rm_path_pass, rm_own_doors, 0)
	if(isnull(r)) return null
	if(r)
		T.Entered(src, was)   // the ground's own (Turfs.dm), as the standard Move calls it
		return 1
	var/atom/B = T   // blocked: what the game compiler's standard Move bumps, the first dense thing there, else the tile
	if(!T.density) for(var/atom/movable/C in T) if(C.density)
		B = C
		break
	Bump(B)
	return 0

// The shadow mode: the engine's answer before the standard Move runs (null: not a plain step), then both compared.
mob/Monsters/proc/RmStepDecide(turf/T, Dir)
	if(rm_step_scan_check || rm_nav_count || !isturf(T)) return null
	. = rm_step(src, T, Dir, usr == src ? RmSide(src) : null, rm_path_pass, rm_own_doors, 1)
	if(isnull(.)) rm_step_odd++
	else rm_step_plainc++

mob/Monsters/proc/RmStepVerify(want, got, turf/T)
	if(!(++rm_step_checked % 20000)) world.log << "RMSTEP|checked|[rm_step_checked]|differ|[rm_step_differ]|plain [rm_step_plainc]|standard [rm_step_odd]"
	if(want ? (got && loc == T) : !got) return
	rm_step_differ++
	if(rm_step_differ <= 30) world.log << "RMSTEP|differs|[type] at [x],[y],[z] to [T.x],[T.y],[T.z]|engine [want]|DM [got]"

// The step-off's two looks (version 23, RmStep.cs; the owner, 10-29: "Step-off + step"): Clip.dm RmStepOffShared, on
// every pass of the orders tick for every unit, looked at its tile for one of its side (~4 us in DM), and one sharing a
// tile looked at the tiles round it (orange(1), which copies the look of every tile and thing in range, then a walkable
// and room check each: ~25 us, ~1,400 a second in a 1000 v 1000, nearly all finding no room). The engine answers both,
// rule for rule: rm_shares (another dense unit of its side, not flying, on its tile) and rm_step_off_tile (the first
// nearest tile beside it, in orange's order, it can step to and stop on). Version 23 also reads movables' density,
// Flying, Wagon and Owner for the walk checks and the plain step through kept reads, and a step that wouldn't turn the
// unit leaves its dir (no game change; RM_WALK_VERIFY=1 and RM_STEP_VERIFY=1 check those).
//   RM_STEP_OFF=0          don't use them
//   RM_STEP_OFF_VERIFY=1   shadow mode: the DM looks run too and are used; any difference is logged (RMSTEPOFF|differs)
var/rm_step_off_native = 0
var/rm_step_off_verify = 0
var/rm_step_off_checked = 0
var/rm_step_off_differ = 0
proc/rm_shares(mob/Monsters/M, list/side)
	return null
proc/rm_step_off_tile(mob/Monsters/M, turf/aim, list/pass, doors)
	return null

proc/RmStepOffVerify(mob/Monsters/M, what, engine, game)
	if(!rm_step_off_verify) return
	if(!(++rm_step_off_checked % 20000)) world.log << "RMSTEPOFF|checked|[rm_step_off_checked]|differ|[rm_step_off_differ]"
	if(engine == game) return
	rm_step_off_differ++
	if(rm_step_off_differ <= 30) world.log << "RMSTEPOFF|differs|[what]|[M.type] at [M.x],[M.y],[M.z]|engine [isturf(engine) ? "[engine:x],[engine:y]" : "[engine]"]|game [isturf(game) ? "[game:x],[game:y]" : "[game]"]"

// get_dist by the engine (version 24, RmDist.cs; the owner, 10-29: "Field way + get_dist"): the standard library's
// get_dist (the compiler's DMStandard _Standard.dm) was DM, ~1 us a call and ~19,000 a second in a 1000 v 1000. With this
// declared, an engine of version 24 or later binds its own get_dist in its place, line for line the same, and answers 1
// here; an older one leaves both as they are. RM_GET_DIST=0 in the server's environment: the DM body as before.
// reports/polish-night-1026/field-way/tests/get_dist_check.dm compares the two over every kind of argument.
proc/rm_get_dist_native()
	return 0

// Swimming (version 25, RmSwim.cs; Swim.dm): the engine's walk checks, route search and route map let swimmers into deep
// water once told which turfs are water, the races that never swim, a water tile's steps and the siege engines' type.
// Without the engine's: 0, and rm_swim_on stays 0 (no swimming: the engine and the game must agree).
proc/rm_swim_setup(waters, sky, list/none, cost, siege)
	return 0
proc/rm_swim_stats()
	return null

// Whether a unit an attack-move's look could pick stands within dist of M: any /mob/Monsters but M within the square
// oview(dist, M) looks over that isn't of M's own owner (engine RmSight.cs). Without the engine's: always yes, so
// the look runs as before.
proc/rm_foe_near(mob/Monsters/M, dist, monsters)
	return 1

// The unit grid (version 11, engine v12; RmGrid.cs; server cost, planning/ONE_SIGHT_GRID.md B2): the units on the map
// in 16x16 cells (awake land's chunks), kept by the engine as they move. The engine's rm_foe_near reads it; Awake.dm
// asks rm_grid_cells for the cells holding the connected players' units instead of looping over every unit. These DM
// bodies say "not here", and the callers keep their own loops.
//   RM_GRID=0          don't use it
//   RM_GRID_VERIFY=1   shadow mode: the engine's rm_foe_near works out both answers (the tile scan's is used), and
//                      Awake.dm finds the unit chunks both ways and compares them (RMGRID| lines, rm_grid_stats())
var/rm_grid = 0
var/rm_grid_verify = 0
proc/rm_grid_on(type)
	return 0
proc/rm_grid_off()
	return null
proc/rm_grid_cells(list/owners)
	return null
proc/rm_grid_held(list/owners)
	return null
proc/rm_grid_units(x0, y0, x1, y1, z)
	return null
proc/rm_grid_check()
	return -1
proc/rm_grid_stats()
	return null

// The units standing within r tiles of A, as `for(var/mob/Monsters/O in range(r, A))` finds them (the same square on
// A's layer), from the unit grid instead of a walk over the tiles (server-engine, 2026-10-26: Morale.dm's looks round a
// fight cost 76 ms a second in a 100 v 100 melee). The order differs from range()'s; the units don't. A not standing
// on a tile, or no grid: range() itself.
//   RM_NEAR_VERIFY=1   shadow mode: range()'s units are used, and any difference from the grid's is counted and logged
#define RM_NATIVE_NEAR      // RmUnitsNear is here (tests read its counts)
var/rm_near_verify = 0
var/rm_near_checked = 0      // looks compared in shadow mode
var/rm_near_differ = 0       // ...and how many differed
proc/RmUnitsNear(r, atom/A)
	if(!rm_grid || !A || !isturf(A.loc)) return range(r, A)
	var/list/G = rm_grid_units(A.x - r, A.y - r, A.x + r, A.y + r, A.z)
	if(!islist(G)) return range(r, A)
	if(!rm_near_verify) return G
	var/list/R = list()
	for(var/mob/Monsters/M in range(r, A)) R += M
	rm_near_checked++
	if(length(R) != length(G) || length(R - G) || length(G - R))
		rm_near_differ++
		if(rm_near_differ <= 20) world.log << "RMNEAR|differs|[A.type] at [A.x],[A.y],[A.z] r=[r]|range [length(R)] grid [length(G)]"
	return R

// A group move's plan loops in the engine (version 9, engine v8 candidate; RmPlan.cs), step for step as RemasterGroupForm's
// DM loops (Formations.dm), which stay as the fallback and the reference.
//   RM_NATIVE_PLAN=0   don't use them
//   RM_PLAN_VERIFY=1   shadow mode: both run, DM's answers are used, and any difference is logged (RMPLAN|differs)
var/rm_native_plan = 0
var/rm_plan_verify = 0
var/rm_plan_checked = 0       // plan steps compared in shadow mode
var/rm_plan_differ = 0        // ...and how many differed
proc/rm_shape_points(n, tx, ty, sx, sy, per, box)
	return null
proc/rm_points_ok(list/points, sx, sy, mx, my)
	return null
proc/rm_box_handout(list/units, list/anchors, cx, cy, ffx, ffy, list/ok, list/tiles, mx, my, per)
	return null
proc/rm_plan_anchors(list/group, from, z, list/anchors, list/start)
	return null
proc/rm_uncross_all(list/assign, list/anchors, list/key_of, ties_on)
	return null
proc/rm_plan_group(list/selected, owner, list/units, monsters, siege)
	return null
proc/rm_points_order(list/points, sx, sy, mx, my)
	return null

// Shadow mode: the engine's answer A against DM's B, element for element (nested lists too, and a unit key's value).
proc/RmPlanSame(list/A, list/B)
	if(length(A) != length(B)) return 0
	for(var/i = 1, i <= length(A), i++)
		var/a = A[i]
		var/b = B[i]
		if(islist(a) && islist(b))
			if(!RmPlanSame(a, b)) return 0
		else if(a != b) return 0
		if(ismob(a))
			var/va = A[a]
			var/vb = B[b]
			if(islist(va) && islist(vb))
				if(!RmPlanSame(va, vb)) return 0
			else if(va != vb) return 0
	return 1

proc/RmPlanCheck(what, list/A, list/B)
	rm_plan_checked++
	if(RmPlanSame(A, B)) return
	rm_plan_differ++
	if(rm_plan_differ <= 20) world.log << "RMPLAN|differs|[what]|engine [length(A)] DM [length(B)]"

// Sleeping tiles (version 10, map memory, planning/MAP_MEMORY.md; RmTiles.cs and the engine's COMPACT patch): a tile that
// only its cell holds is kept as a small packed record and woken on any read with the same ref, values, look and area, so
// the game can't tell. Regions.dm's sweep puts to sleep the tiles of land nobody has been near for a minute. These DM
// bodies sleep nothing: on an older engine every tile stays awake, as before. RM_COMPACT_TILES=0: the engine sleeps nothing.
#define RM_NATIVE_TILES
// x0..x1, y0..y1 on level z: "slept=N|already=..|held=..|..." (why tiles stay awake); dry: only counts
proc/rm_tiles_sleep(x0, y0, x1, y1, z, dry)
	return null
// the same, returning only how many were put to sleep
proc/rm_tiles_sleep_box(x0, y0, x1, y1, z)
	return 0
// wakes a box's sleeping tiles (reading them does it too); returns how many
proc/rm_tiles_wake(x0, y0, x1, y1, z)
	return 0
// how many of a box's tiles are asleep (wakes nothing)
proc/rm_tiles_count(x0, y0, x1, y1, z)
	return 0
// "sleeping=..|blocks=..|bytes=..|woken=..|slept=..|vararrays=..|varentries=..|on=.."
proc/rm_tiles_stats()
	return null
// the areas' turf sets (trim: give their spare room back) and the turf ref table: "areas=..|turfs=..|room=..|..."
proc/rm_area_sets(trim)
	return null
// a full blocking, compacting collection, big objects too, then the heap: "total=..|heap=..|fragmented=..|committed=..|gen0=.."
// in bytes (Regions.dm's load pass); this DM body collects nothing. Tests that declared it themselves check RM_NATIVE_HEAP.
#define RM_NATIVE_HEAP
proc/rm_heap_info()
	return null
