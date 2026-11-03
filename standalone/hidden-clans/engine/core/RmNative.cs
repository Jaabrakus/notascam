// Remastered native procs (planning/ENGINE_PLAN.md). Each replaces the DM proc of the same name, which the game declares
// in Code/Remastered/Native.dm with a DM fallback body, and only when the game declares that name: new game code on an
// old engine runs the DM bodies, and old game code (no such names) runs on this engine unchanged.
// Patched into the runtime by tools/build_runtime.py (copied into src/Procs/Native, called from SetupNativeProcs).
using OpenDreamRuntime.Objects;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmNative {
    // Bumped whenever a native changes what it takes or returns; the game reads it to know what this engine has.
    // 2: rm_path and rm_walkable take the mover's side (owners whose units it goes through) and the siege type.
    // 3: rm_memory_report (tests: what the memory goes to, RmMemory.cs).
    // 4: rm_slot_reach, rm_slot_tiles, rm_sort_by (a group move's open tiles, its slot tiles and sorts, RmSlots.cs; formations).
    // 5: rm_pack (the HUD's sends deflated for the page, RmPack.cs; server cost).
    // 6: rm_alloc_now, rm_alloc_total (what the game and the process allocate, for the tick profiler, RmAlloc.cs; server
    //    cost); rm_chunk_ver, rm_ver (change counters for the 3D view's sends of what changed, RmVer.cs and the VER patch;
    //    world look). The v6 engine also collects garbage between ticks and indexes big lists (build_runtime.py TICKGC,
    //    ASSOC; formations), which are not procs.
    // 7 (candidate): rm_watch, rm_watch_take (which objects had a watched var written, RmWatch.cs and the WATCH patch);
    //    rm_foe_near (an attack-move's look skipped when no other owner's unit is within sight, RmSight.cs).
    // 8 (candidate): rm_path and rm_walkable take the door types (the own-door rule, Doors.dm RmOwnDoor; RmWalk.cs).
    // 9 (v8 candidate): rm_shape_points, rm_points_ok, rm_box_handout, rm_plan_anchors, rm_uncross_all, rm_plan_group,
    //    rm_points_order (a group move's plan loops, RmPlan.cs; formations).
    // 10 (v10 candidate): rm_tiles_sleep, rm_tiles_sleep_box, rm_tiles_wake, rm_tiles_count, rm_tiles_stats,
    //    rm_area_sets (tiles nobody holds sleep as packed records and wake on any read, RmTiles.cs and the COMPACT patch;
    //    map memory, planning/MAP_MEMORY.md); rm_heap_info, rm_turf_census, rm_tiles_wake_cost, rm_now_ms (tests).
    // 11 (v12 candidate): rm_grid_on, rm_grid_off, rm_grid_cells, rm_grid_held, rm_grid_units, rm_grid_check, rm_grid_stats (the units
    //    on the map in 16x16 cells, kept as they move, RmGrid.cs and the GRID patch; rm_foe_near reads it; server cost,
    //    planning/ONE_SIGHT_GRID.md B2).
    // 12: rm_reach_build, rm_reach, rm_reach_tick, rm_reach_stats, rm_reach_audit, rm_reach_off (the reach map on the flat
    //    levels, RmReach.cs and its hooks in RmVer.cs; navigation plan N1 stage 1, planning/NAVIGATION_PLAN_2026-10-27.md).
    // 13: rm_field_route, rm_field_stats (the battle ways: a shared field of steps to the nearest free tile beside a foe,
    //    RmField.cs; the owner, 10-28: "have the world preplan the best routes so everyone can fight gangup").
    // 14: rm_morale_look (morale's look round from the unit grid, RmMorale.cs; the owner, 10-28: "Yes, morale next").
    // 15: rm_pool_rank (an attack box's foes ranked for a fighter's next pick, RmPool.cs; the owner, 10-28: "Yes, box re-pick").
    // 16: rm_worked_tidy (the worked trees and rocks' list tidied, RmWorked.cs; the owner, 10-28: "Yes, harvest next").
    // 17: rm_store_scan (a delivery's store tile: one zone's cells, the crowd round each and the carriers sent there, RmStore.cs;
    //    the owner, 10-28: "Yes, deliveries next").
    // 18: rm_decay_add, rm_decay_tick, rm_decay_count (one timer for every lying item's 2006 countdown, RmDecay.cs; the owner,
    //    10-28: "Yes, item timers").
    // 19: rm_route_map, rm_route_stats (a map spread out from a goal: the way round anything longer than the route
    //    search's 512 tiles, shared by a group's members, RmRoute.cs; the owner, 10-29: "we want them to go around the mountain").
    // 20: the battle field (RmField.cs) reaches 40 steps round its chunk, not 16 (RM_FIELD_REACH), so a big battle's back
    //    ranks walk it to the front (the owner, 10-29, 1000 v 1000: "lets fix that"); its procs as in 13.
    // 21: rm_step_setup, rm_step (the plain step: the ground's Enter chain and the standard Move's step on a plain tile,
    //    without the standard Move's calls that do nothing; RmStep.cs), rm_walk (RemasterWalkable for the game's own checks,
    //    the types set once; the owner, 10-29: "Native plain step").
    // 22: rm_morale_look keeps what it read of each unit until the unit's change counter moves (RmMorale.cs), and
    //    rm_foe_beside (whether Attack.dm RmFoeBeside can find anyone, RmSight.cs; the owner, 10-29: "Morale + foe look").
    // 23: the walk checks and the plain step read movables' density, Flying, Wagon and Owner through RmKept.cs (kept while
    //    each one's change counter stands; DreamObjectMovable.RmKept, the VER patch), a step that wouldn't turn the unit
    //    leaves its dir, and rm_shares, rm_step_off_tile (the step-off's two looks; RmStep.cs; the owner, 10-29:
    //    "Step-off + step").
    // 24: get_dist by the engine (RmDist.cs, when the game declares rm_get_dist_native; the owner, 10-29: "Field way +
    //    get_dist"), and RmKept.cs's check mode (RM_KEPT_VERIFY=1, rm_kept_stats).
    // 25: swimming (RmSwim.cs; the owner, 10-29: "add swimming to the game some races faster than other"): deep water open
    //     to swimmers in the walk checks, the route search and the route map at RmSwim.Cost steps a tile; the plain step
    //     leaves water to the game; the battle field and a group's places stay on land.
    // 26: the map built asleep at load (engine/compact, load-asleep-1030; the reach map reads sleeping tiles from their
    //     records) and rm_gc_compact (RmTiles.cs: one compaction after the first player's join, Regions.dm).
    // 27: rm_grid_changed (RmGrid.cs; server upgrades U6, 10-30): for each player's view, only the units near it that are new
    //     or changed since its last call, and those that left; the 3D move rows touch only those.
    // 28: rm_range_movables (RmRange.cs; U6, 10-31): range()'s movables in its order, without its tiles (the 3D scene).
    // 29: rm_web_behind (U4's rate skip, 10-31): the bytes still queued for a browser player's tabs, so the game can skip
    //     that player's next scene instead of queueing it (OpenRealm's rate).
    // 30: rm_hud_units (RmHud.cs; U5's rest, 10-31): the HUD units delta's pass over the entries (hot rows, kept entries,
    //     each part encoded by the engine's json_encode), what HUD.dm did in DM to the byte.
    // 31: rm_ver_state, rm_ver_state_quiet (RmVer.cs; the owner, 10-31: "record rebuilt per second thats to much"): a
    //     change counter that stands while a unit walks, for what is worked out from its state (the HUD).
    // 32: rm_fog_mark (RmFog.cs; the owner, 10-31: "does things multiple itmes"): a sight circle marked into a level's
    //     explored map, what Fog.dm RmFogMarkCircle did row by row in DM.
    // 33: rm_list_changed (RmChanged.cs; the owner, 10-31: "does things multiple itmes"): the things in a list whose
    //     change counter moved since a caller's last look, with their places, so the game touches only those.
    // 34: rm_chunk_things_ver (RmVer.cs; load-asleep-1030, the owner, 10-31: "Exact, engine counter"): a chunk's things on
    //     turfs changed (objs lying there changed or arriving; mobs onto or off the map), for scans that keep their answer.
    // 35: rm_ver_shown, rm_ver_shown_quiet (RmVer.cs; the owner, 10-31: "those rebuilts are high arent they? shouldnt we
    //     get like 100?"): the state counter less what no view draws, for the 3D scene's entries.
    public const int Version = 35;

    public static void Register(DreamObjectTree objectTree) {
        if (objectTree.TryGetGlobalProc("rm_native_version", out _)) objectTree.SetGlobalNativeProc(NativeProc_rm_native_version);
        if (objectTree.TryGetGlobalProc("rm_web_behind", out _)) objectTree.SetGlobalNativeProc(NativeProc_rm_web_behind);
        if (objectTree.TryGetGlobalProc("rm_path", out _)) objectTree.SetGlobalNativeProc(RmPath.NativeProc_rm_path);
        if (objectTree.TryGetGlobalProc("rm_walkable", out _)) objectTree.SetGlobalNativeProc(RmPath.NativeProc_rm_walkable);
        if (objectTree.TryGetGlobalProc("rm_memory_report", out _)) objectTree.SetGlobalNativeProc(RmMemory.NativeProc_rm_memory_report);
        if (objectTree.TryGetGlobalProc("rm_slot_reach", out _)) objectTree.SetGlobalNativeProc(RmSlots.NativeProc_rm_slot_reach);
        if (objectTree.TryGetGlobalProc("rm_slot_tiles", out _)) objectTree.SetGlobalNativeProc(RmSlots.NativeProc_rm_slot_tiles);
        if (objectTree.TryGetGlobalProc("rm_sort_by", out _)) objectTree.SetGlobalNativeProc(RmSlots.NativeProc_rm_sort_by);
        if (objectTree.TryGetGlobalProc("rm_shape_points", out _)) objectTree.SetGlobalNativeProc(RmPlan.NativeProc_rm_shape_points);
        if (objectTree.TryGetGlobalProc("rm_points_ok", out _)) objectTree.SetGlobalNativeProc(RmPlan.NativeProc_rm_points_ok);
        if (objectTree.TryGetGlobalProc("rm_box_handout", out _)) objectTree.SetGlobalNativeProc(RmPlan.NativeProc_rm_box_handout);
        if (objectTree.TryGetGlobalProc("rm_plan_anchors", out _)) objectTree.SetGlobalNativeProc(RmPlan.NativeProc_rm_plan_anchors);
        if (objectTree.TryGetGlobalProc("rm_uncross_all", out _)) objectTree.SetGlobalNativeProc(RmPlan.NativeProc_rm_uncross_all);
        if (objectTree.TryGetGlobalProc("rm_plan_group", out _)) objectTree.SetGlobalNativeProc(RmPlan.NativeProc_rm_plan_group);
        if (objectTree.TryGetGlobalProc("rm_points_order", out _)) objectTree.SetGlobalNativeProc(RmPlan.NativeProc_rm_points_order);
        if (objectTree.TryGetGlobalProc("rm_pack", out _)) objectTree.SetGlobalNativeProc(RmPack.NativeProc_rm_pack);
        if (objectTree.TryGetGlobalProc("rm_foe_near", out _)) objectTree.SetGlobalNativeProc(RmSight.NativeProc_rm_foe_near);
        if (objectTree.TryGetGlobalProc("rm_grid_on", out _)) objectTree.SetGlobalNativeProc(RmGrid.NativeProc_rm_grid_on);
        if (objectTree.TryGetGlobalProc("rm_grid_off", out _)) objectTree.SetGlobalNativeProc(RmGrid.NativeProc_rm_grid_off);
        if (objectTree.TryGetGlobalProc("rm_grid_cells", out _)) objectTree.SetGlobalNativeProc(RmGrid.NativeProc_rm_grid_cells);
        if (objectTree.TryGetGlobalProc("rm_grid_held", out _)) objectTree.SetGlobalNativeProc(RmGrid.NativeProc_rm_grid_held);
        if (objectTree.TryGetGlobalProc("rm_grid_units", out _)) objectTree.SetGlobalNativeProc(RmGrid.NativeProc_rm_grid_units);
        if (objectTree.TryGetGlobalProc("rm_grid_changed", out _)) objectTree.SetGlobalNativeProc(RmGrid.NativeProc_rm_grid_changed);
        if (objectTree.TryGetGlobalProc("rm_range_movables", out _)) objectTree.SetGlobalNativeProc(RmRange.NativeProc_rm_range_movables);
        if (objectTree.TryGetGlobalProc("rm_hud_units", out _)) objectTree.SetGlobalNativeProc(RmHud.NativeProc_rm_hud_units);
        if (objectTree.TryGetGlobalProc("rm_grid_check", out _)) objectTree.SetGlobalNativeProc(RmGrid.NativeProc_rm_grid_check);
        if (objectTree.TryGetGlobalProc("rm_grid_stats", out _)) objectTree.SetGlobalNativeProc(RmGrid.NativeProc_rm_grid_stats);
        if (objectTree.TryGetGlobalProc("rm_watch", out _)) objectTree.SetGlobalNativeProc(RmWatch.NativeProc_rm_watch);
        if (objectTree.TryGetGlobalProc("rm_watch_take", out _)) objectTree.SetGlobalNativeProc(RmWatch.NativeProc_rm_watch_take);
        if (objectTree.TryGetGlobalProc("rm_chunk_ver", out _)) objectTree.SetGlobalNativeProc(RmVer.NativeProc_rm_chunk_ver);
        if (objectTree.TryGetGlobalProc("rm_chunk_things_ver", out _)) objectTree.SetGlobalNativeProc(RmVer.NativeProc_rm_chunk_things_ver);
        if (objectTree.TryGetGlobalProc("rm_ver", out _)) objectTree.SetGlobalNativeProc(RmVer.NativeProc_rm_ver);
        if (objectTree.TryGetGlobalProc("rm_ver_quiet", out _)) objectTree.SetGlobalNativeProc(RmVer.NativeProc_rm_ver_quiet);
        if (objectTree.TryGetGlobalProc("rm_ver_state", out _)) objectTree.SetGlobalNativeProc(RmVer.NativeProc_rm_ver_state);
        if (objectTree.TryGetGlobalProc("rm_ver_state_quiet", out _)) objectTree.SetGlobalNativeProc(RmVer.NativeProc_rm_ver_state_quiet);
        if (objectTree.TryGetGlobalProc("rm_ver_shown", out _)) objectTree.SetGlobalNativeProc(RmVer.NativeProc_rm_ver_shown);
        if (objectTree.TryGetGlobalProc("rm_ver_shown_quiet", out _)) objectTree.SetGlobalNativeProc(RmVer.NativeProc_rm_ver_shown_quiet);
        if (objectTree.TryGetGlobalProc("rm_fog_mark", out _)) objectTree.SetGlobalNativeProc(RmFog.NativeProc_rm_fog_mark);
        if (objectTree.TryGetGlobalProc("rm_list_changed", out _)) objectTree.SetGlobalNativeProc(RmChanged.NativeProc_rm_list_changed);
        if (objectTree.TryGetGlobalProc("rm_alloc_now", out _)) objectTree.SetGlobalNativeProc(RmAlloc.NativeProc_rm_alloc_now);
        if (objectTree.TryGetGlobalProc("rm_alloc_total", out _)) objectTree.SetGlobalNativeProc(RmAlloc.NativeProc_rm_alloc_total);
        if (objectTree.TryGetGlobalProc("rm_tiles_sleep", out _)) objectTree.SetGlobalNativeProc(RmTiles.NativeProc_rm_tiles_sleep);
        if (objectTree.TryGetGlobalProc("rm_tiles_sleep_box", out _)) objectTree.SetGlobalNativeProc(RmTiles.NativeProc_rm_tiles_sleep_box);
        if (objectTree.TryGetGlobalProc("rm_tiles_wake", out _)) objectTree.SetGlobalNativeProc(RmTiles.NativeProc_rm_tiles_wake);
        if (objectTree.TryGetGlobalProc("rm_tiles_wake_cost", out _)) objectTree.SetGlobalNativeProc(RmTiles.NativeProc_rm_tiles_wake_cost);
        if (objectTree.TryGetGlobalProc("rm_tiles_count", out _)) objectTree.SetGlobalNativeProc(RmTiles.NativeProc_rm_tiles_count);
        if (objectTree.TryGetGlobalProc("rm_tiles_stats", out _)) objectTree.SetGlobalNativeProc(RmTiles.NativeProc_rm_tiles_stats);
        if (objectTree.TryGetGlobalProc("rm_area_sets", out _)) objectTree.SetGlobalNativeProc(RmTiles.NativeProc_rm_area_sets);
        if (objectTree.TryGetGlobalProc("rm_heap", out _)) objectTree.SetGlobalNativeProc(RmTiles.NativeProc_rm_heap);
        if (objectTree.TryGetGlobalProc("rm_heap_info", out _)) objectTree.SetGlobalNativeProc(RmTiles.NativeProc_rm_heap_info);
        if (objectTree.TryGetGlobalProc("rm_turf_census", out _)) objectTree.SetGlobalNativeProc(RmTiles.NativeProc_rm_turf_census);
        if (objectTree.TryGetGlobalProc("rm_now_ms", out _)) objectTree.SetGlobalNativeProc(RmTiles.NativeProc_rm_now_ms);
        if (objectTree.TryGetGlobalProc("rm_gc_compact", out _)) objectTree.SetGlobalNativeProc(RmTiles.NativeProc_rm_gc_compact);
        if (objectTree.TryGetGlobalProc("rm_reach_build", out _)) objectTree.SetGlobalNativeProc(RmReach.NativeProc_rm_reach_build);
        if (objectTree.TryGetGlobalProc("rm_reach", out _)) objectTree.SetGlobalNativeProc(RmReach.NativeProc_rm_reach);
        if (objectTree.TryGetGlobalProc("rm_reach_tick", out _)) objectTree.SetGlobalNativeProc(RmReach.NativeProc_rm_reach_tick);
        if (objectTree.TryGetGlobalProc("rm_reach_stats", out _)) objectTree.SetGlobalNativeProc(RmReach.NativeProc_rm_reach_stats);
        if (objectTree.TryGetGlobalProc("rm_reach_audit", out _)) objectTree.SetGlobalNativeProc(RmReach.NativeProc_rm_reach_audit);
        if (objectTree.TryGetGlobalProc("rm_reach_off", out _)) objectTree.SetGlobalNativeProc(RmReach.NativeProc_rm_reach_off);
        if (objectTree.TryGetGlobalProc("rm_field_route", out _)) objectTree.SetGlobalNativeProc(RmField.NativeProc_rm_field_route);
        if (objectTree.TryGetGlobalProc("rm_field_stats", out _)) objectTree.SetGlobalNativeProc(RmField.NativeProc_rm_field_stats);
        if (objectTree.TryGetGlobalProc("rm_morale_look", out _)) objectTree.SetGlobalNativeProc(RmMorale.NativeProc_rm_morale_look);
        if (objectTree.TryGetGlobalProc("rm_pool_rank", out _)) objectTree.SetGlobalNativeProc(RmPool.NativeProc_rm_pool_rank);
        if (objectTree.TryGetGlobalProc("rm_worked_tidy", out _)) objectTree.SetGlobalNativeProc(RmWorked.NativeProc_rm_worked_tidy);
        if (objectTree.TryGetGlobalProc("rm_store_scan", out _)) objectTree.SetGlobalNativeProc(RmStore.NativeProc_rm_store_scan);
        if (objectTree.TryGetGlobalProc("rm_decay_add", out _)) objectTree.SetGlobalNativeProc(RmDecay.NativeProc_rm_decay_add);
        if (objectTree.TryGetGlobalProc("rm_decay_tick", out _)) objectTree.SetGlobalNativeProc(RmDecay.NativeProc_rm_decay_tick);
        if (objectTree.TryGetGlobalProc("rm_decay_count", out _)) objectTree.SetGlobalNativeProc(RmDecay.NativeProc_rm_decay_count);
        if (objectTree.TryGetGlobalProc("rm_route_map", out _)) objectTree.SetGlobalNativeProc(RmRoute.NativeProc_rm_route_map);
        if (objectTree.TryGetGlobalProc("rm_route_stats", out _)) objectTree.SetGlobalNativeProc(RmRoute.NativeProc_rm_route_stats);
        if (objectTree.TryGetGlobalProc("rm_step_setup", out _)) objectTree.SetGlobalNativeProc(RmStep.NativeProc_rm_step_setup);
        if (objectTree.TryGetGlobalProc("rm_step", out _)) objectTree.SetGlobalNativeProc(RmStep.NativeProc_rm_step);
        if (objectTree.TryGetGlobalProc("rm_walk", out _)) objectTree.SetGlobalNativeProc(RmStep.NativeProc_rm_walk);
        if (objectTree.TryGetGlobalProc("rm_shares", out _)) objectTree.SetGlobalNativeProc(RmStep.NativeProc_rm_shares);
        if (objectTree.TryGetGlobalProc("rm_step_off_tile", out _)) objectTree.SetGlobalNativeProc(RmStep.NativeProc_rm_step_off_tile);
        if (objectTree.TryGetGlobalProc("rm_kept_stats", out _)) objectTree.SetGlobalNativeProc(RmKept.NativeProc_rm_kept_stats);
        if (objectTree.TryGetGlobalProc("rm_get_dist_native", out _) && !RmDist.Disabled) {   // the standard library's get_dist, by the engine
            objectTree.SetGlobalNativeProc(RmDist.NativeProc_rm_get_dist_native);
            objectTree.SetGlobalNativeProc(RmDist.NativeProc_get_dist);
        }
        if (objectTree.TryGetGlobalProc("rm_foe_beside", out _)) objectTree.SetGlobalNativeProc(RmSight.NativeProc_rm_foe_beside);
        if (objectTree.TryGetGlobalProc("rm_morale_stats", out _)) objectTree.SetGlobalNativeProc(RmMorale.NativeProc_rm_morale_stats);
        if (objectTree.TryGetGlobalProc("rm_swim_setup", out _)) objectTree.SetGlobalNativeProc(RmSwim.NativeProc_rm_swim_setup);
        if (objectTree.TryGetGlobalProc("rm_swim_stats", out _)) objectTree.SetGlobalNativeProc(RmSwim.NativeProc_rm_swim_stats);
    }

    [DreamProc("rm_native_version")]
    public static DreamValue NativeProc_rm_native_version(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        return new DreamValue(Version);
    }

    /// <summary>
    /// Set by the web link when it starts (engine/web RmWebServer.cs): the bytes still queued for that player's browser
    /// tabs. Null without the web link; core knows nothing of it beyond this.
    /// </summary>
    public static System.Func<DreamObject, long>? WebBehind;

    // rm_web_behind(who): bytes still queued for who's browser tabs; 0 for a player in the app, or with no web link.
    [DreamProc("rm_web_behind")]
    [DreamProcParameter("who", Type = DreamValue.DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_web_behind(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (WebBehind == null || !bundle.GetArgument(0, "who").TryGetValueAsDreamObject<DreamObject>(out var who) || who == null)
            return new DreamValue(0);
        return new DreamValue(WebBehind(who));
    }

    // A var read as DM reads it: a missing var is null. Values that hold an object are released after use.
    public static bool Truthy(DreamObject o, string name) {
        if (!o.TryGetVariable(name, out var v)) return false;
        using (v) return v.IsTruthy();
    }

    public static bool VarEquals(DreamObject o, string name, DreamValue other) {
        if (!o.TryGetVariable(name, out var v)) return DMOpcodeHandlers.IsEqual(DreamValue.Null, other);
        using (v) return DMOpcodeHandlers.IsEqual(v, other);
    }

    public static string? VarString(DreamObject o, string name) {
        if (!o.TryGetVariable(name, out var v)) return null;
        using (v) return v.TryGetValueAsString(out var s) ? s : null;
    }

    public static bool VarIsObject(DreamObject o, string name, DreamObject what) {
        if (!o.TryGetVariable(name, out var v)) return false;
        using (v) return v.TryGetValueAsDreamObject<DreamObject>(out var x) && !x.Deleted && x == what;   // DM's == reads a deleted object as null
    }
}
