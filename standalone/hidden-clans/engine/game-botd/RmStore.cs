// A delivery's store tile (native version 17; the owner, 10-28: "Yes, deliveries next"). Jobs.dm RmJzStoreFor looks
// over every store zone's cells for the one to carry a load to: the nearest, each cell costing RM_STORE_CROWD more for
// every unit standing round it (RmStoreCrowd: a block of 9 tiles, each tile's contents made as a list) and every carrier
// already sent to it (RmJzAimed, which drops those gone elsewhere). 0.69 ms a delivery with 2,000 workers. This is one
// zone's part of that loop, step for step: the cells in order, a cell M is told to avoid or a dense one skipped, one no
// nearer than the best cost so far skipped, then its cost; the first lowest wins. Whether the zone takes the load
// (RmJzZoneTakesLoad, a game rule) is asked of the game at the first cell that could win, as the loop asks it.
//   rm_store_scan(cells, M, not_this, bc, takes, aim, crowd_w, monsters)
//     -1: takes is unknown (-1) and a cell could win: the game asks RmJzZoneTakesLoad and calls again with its answer;
//     else list(best cell or null, best cost): with takes 0 the zone is passed over, as the loop's break does.
//     aim is rm_cell_aim (store tile -> carriers sent there): stale carriers leave each list looked at, as RmJzAimed's do.
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using Robust.Shared.Maths;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmStore {
    [DreamProc("rm_store_scan")]
    [DreamProcParameter("cells", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("not_this", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("bc", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("takes", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("aim", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("crowd_w", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("monsters", Type = DreamValueTypeFlag.DreamType)]
    public static DreamValue NativeProc_rm_store_scan(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "cells").TryGetValueAsDreamList(out var cells)) return DreamValue.Null;
        if (!bundle.GetArgument(1, "M").TryGetValueAsDreamObject<DreamObjectMovable>(out var m) || m.Deleted) return DreamValue.Null;
        bundle.GetArgument(2, "not_this").TryGetValueAsDreamObject<DreamObjectTurf>(out var notThis);
        if (!bundle.GetArgument(3, "bc").TryGetValueAsFloat(out var bc)) return DreamValue.Null;
        if (!bundle.GetArgument(4, "takes").TryGetValueAsFloat(out var takes)) return DreamValue.Null;
        bundle.GetArgument(5, "aim").TryGetValueAsDreamList(out var aim);
        if (!bundle.GetArgument(6, "crowd_w").TryGetValueAsFloat(out var crowdW)) return DreamValue.Null;
        if (!bundle.GetArgument(7, "monsters").TryGetValueAsType(out var monsters)) return DreamValue.Null;
        var map = bundle.MapManager;
        var size = map.Size;
        DreamObjectTurf? best = null;
        foreach (var v in cells.EnumerateValues()) {   // the list's own values: never disposed
            if (!v.TryGetValueAsDreamObject<DreamObjectTurf>(out var t) || t == null) continue;   // the typed loop skips them
            if (t == notThis || t.IsDense) continue;
            var d = Dist(t, m);
            if (d >= bc) continue;
            if (takes < 0) return new DreamValue(-1);   // the game's rule, asked once, here
            if (takes == 0) break;
            var c = d + crowdW * (Crowd(t, m, monsters, map, size) + Aimed(aim, t));
            if (c < bc) {
                bc = c;
                best = t;
            }
        }
        var list = bundle.ObjectTree.CreateList();
        list.AddValue(best != null ? new DreamValue(best) : DreamValue.Null);
        list.AddValue(new DreamValue(bc));
        return new DreamValue(list);
    }

    // get_dist(T, M) as the compiler's _Standard.dm has it, for a turf and a unit: from the unit's own x and y (0 inside
    // something: infinite), the larger gap (0 when it stands on T: -1 is only for the same atom twice).
    private static float Dist(DreamObjectTurf t, DreamObjectMovable m) {
        var mx = RmMorale.Num(m, "x");
        var my = RmMorale.Num(m, "y");
        if (mx == 0 || my == 0) return float.PositiveInfinity;
        return System.Math.Max(System.Math.Abs(mx - t.X), System.Math.Abs(my - t.Y));
    }

    // RmStoreCrowd: dense units but M on the 8 tiles round T (the block clipped to the map).
    private static int Crowd(DreamObjectTurf t, DreamObject m, TreeEntry monsters, OpenDreamRuntime.Map.IDreamMapManager map, Vector2i size) {
        var n = 0;
        for (var y = System.Math.Max(1, t.Y - 1); y <= System.Math.Min(size.Y, t.Y + 1); y++)
            for (var x = System.Math.Max(1, t.X - 1); x <= System.Math.Min(size.X, t.X + 1); x++) {
                if (x == t.X && y == t.Y) continue;
                if (!map.TryGetTurfAt(new Vector2i(x, y), t.Z, out var r)) continue;
                foreach (var u in r.Cell.Movables)
                    if (!u.Deleted && u != m && u.IsSubtypeOf(monsters) && RmNative.Truthy(u, "density")) n++;
            }
        return n;
    }

    // RmJzAimed: the carriers still sent to T (aim[T]), from the end, those gone elsewhere cut from the list.
    private static int Aimed(DreamList? aim, DreamObjectTurf t) {
        if (aim == null) return 0;
        using var lv = aim.GetValue(new DreamValue(t));
        if (!lv.TryGetValueAsDreamList(out var l)) return 0;
        for (var i = l.GetLength(); i >= 1; i--) {
            bool ok;
            using (var mv = l.GetValue(new DreamValue(i))) ok = mv.TryGetValueAsDreamObject<DreamObject>(out var c) && c != null && !c.Deleted && Sent(c, t);
            if (!ok) l.Cut(i, i + 1);
        }
        return l.GetLength();
    }

    // M.rm_store_aim == T && M.remaster_delivery && M.remaster_delivery.target == T
    private static bool Sent(DreamObject c, DreamObjectTurf t) {
        if (!RmNative.VarIsObject(c, "rm_store_aim", t)) return false;
        if (!c.TryGetVariable("remaster_delivery", out var dv)) return false;
        using (dv) return dv.TryGetValueAsDreamObject<DreamObject>(out var d) && d != null && !d.Deleted && RmNative.VarIsObject(d, "target", t);
    }
}
