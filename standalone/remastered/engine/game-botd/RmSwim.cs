// Swimming (native version 25; the owner, 10-29: "add swimming to the game some races faster than other"). Deep water
// (the game's water family, game/Code/Remastered/Water.dm and Building/TurfTypes.dm: dense) stays shut to walking; a unit
// that swims goes into it. The game says once which turfs are water and which races never swim (rm_swim_setup); until
// then nothing here answers and every rule is as before. Mirrored in game/Code/Remastered/Swim.dm (RmSwimWater, RmSwims,
// RmSwimCost): change both together; RM_WALK_VERIFY=1 and RM_PATH_VERIFY=1 log any answer that differs.
//   rm_swim_setup(waters, sky, none, cost, siege)   the water type, the Sky layer's z (no swimming up there), the races
//     that never swim (a list of texts), a water tile's cost to the route search and the route map (steps, at least 1),
//     the siege engines' type (they never swim): 1
//   rm_swim_stats()   "on=..|cost=..|water_reads=.."
// What swims (RmSwims): a dense /mob/Monsters (the caller's type) not flying, not a cart (Wagon), not a siege engine, of
// a race not in the list. What is water (RmSwimWater): a dense turf of the water type, not on the Sky layer, not raised
// (remaster_waterlift: a mountain lake or its river up in the rock).
using System.Collections.Generic;
using OpenDreamRuntime.Map;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmSwim {
    public static bool On { get; private set; }
    public static int Cost { get; private set; } = 1;
    private static TreeEntry? _waters, _siege;
    private static int _sky;
    private static readonly HashSet<string> None = new();
    private static long _reads;

    [DreamProc("rm_swim_setup")]
    [DreamProcParameter("waters", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("sky", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("none", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("cost", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("siege", Type = DreamValueTypeFlag.DreamType)]
    public static DreamValue NativeProc_rm_swim_setup(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "waters").TryGetValueAsType(out var waters)) {
            On = false;
            return new DreamValue(0);
        }
        bundle.GetArgument(1, "sky").TryGetValueAsInteger(out _sky);
        None.Clear();
        if (bundle.GetArgument(2, "none").TryGetValueAsDreamList(out var none))
            foreach (var v in none.EnumerateValues())
                if (v.TryGetValueAsString(out var s)) None.Add(s);
        Cost = bundle.GetArgument(3, "cost").TryGetValueAsInteger(out var c) ? System.Math.Max(1, c) : 1;
        bundle.GetArgument(4, "siege").TryGetValueAsType(out _siege);
        _waters = waters;
        On = true;
        return new DreamValue(1);
    }

    [DreamProc("rm_swim_stats")]
    public static DreamValue NativeProc_rm_swim_stats(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        return new DreamValue($"on={(On ? 1 : 0)}|cost={Cost}|water_reads={_reads}");
    }

    // RmSwimWater(T): deep water a swimmer can go into.
    public static bool Water(DreamObjectTurf t) {
        if (!On || _waters == null || t.Z == _sky || !t.IsSubtypeOf(_waters)) return false;
        _reads++;
        return RmNative.Truthy(t, "density") && !RmNative.Truthy(t, "remaster_waterlift");
    }

    // Water for a sleeping tile (the reach map's build, load-asleep): the same reads, from its record.
    public static bool Water(in DreamMapManager.RmTileView t) {
        if (!On || _waters == null || t.Z == _sky || !t.IsSubtypeOf(_waters)) return false;
        _reads++;
        return RmReach.Truthy(t, "density") && !RmReach.Truthy(t, "remaster_waterlift");
    }

    // RmSwims(M): this unit swims (monsters is the caller's /mob/Monsters).
    public static bool Swims(DreamObject m, TreeEntry? monsters) {
        if (!On || monsters == null || !m.IsSubtypeOf(monsters)) return false;
        if (!RmKept.Dense(m) || RmKept.Flying(m) || RmKept.Wagon(m)) return false;
        if (_siege != null && m.IsSubtypeOf(_siege)) return false;
        if (None.Count == 0) return true;
        var race = RmNative.VarString(m, "Race");
        return race == null || !None.Contains(race);
    }
}
