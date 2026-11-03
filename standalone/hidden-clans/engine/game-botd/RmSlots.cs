// A group move's open tiles (formations, 2026-10-24), step for step as game/Code/Remastered/Formations.dm
// RemasterSlotReachDM (the DM version stays as the fallback and the reference): from the seed, a depth-first flood
// (the last tile found is the next one looked from), the same eight directions in the same order, out to R of the
// target, each tile tested once (Walkable with goal = that tile, rm_path_pass and the mover's side, as RmWalkRules),
// then each tile reached, in the order it was reached, counted for free places as Orders.dm RemasterTilePlaces.
// Returns list(reach: tile -> 1, places: tile -> free places, only those with some). A 200-unit order spent 5-7 ms of
// its tick on this in DM (the user: "single digits"). Not used up on a mountain top: the block heights (Gather.dm) are
// DM's.
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using Robust.Shared.Maths;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmSlots {
    // NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST, as the DM loop takes them
    private static readonly (int dx, int dy)[] Steps = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)];

    private static readonly DreamValue Chasm = new("Chasm"), Sky = new("Sky");

    [DreamProc("rm_slot_reach")]
    [DreamProcParameter("T", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("R", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("seed", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("group", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("pass", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("stairs")]
    [DreamProcParameter("foot", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("monsters", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("ground", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("sky", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("side", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("siege", Type = DreamValueTypeFlag.DreamType)]
    public static DreamValue NativeProc_rm_slot_reach(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "T").TryGetValueAsDreamObject<DreamObjectTurf>(out var target)) return DreamValue.Null;
        if (!bundle.GetArgument(1, "R").TryGetValueAsInteger(out var r)) return DreamValue.Null;
        if (!bundle.GetArgument(2, "seed").TryGetValueAsDreamObject<DreamObjectTurf>(out var seed)) return DreamValue.Null;
        if (!bundle.GetArgument(3, "M").TryGetValueAsDreamObject<DreamObject>(out var m)) return DreamValue.Null;
        if (!bundle.GetArgument(4, "group").TryGetValueAsDreamList(out var group)) return DreamValue.Null;
        bundle.GetArgument(5, "pass").TryGetValueAsDreamList(out var pass);
        bundle.GetArgument(7, "foot").TryGetValueAsType(out var foot);
        bundle.GetArgument(8, "monsters").TryGetValueAsType(out var monsters);
        bundle.GetArgument(9, "ground").TryGetValueAsInteger(out var ground);
        bundle.GetArgument(10, "sky").TryGetValueAsInteger(out var sky);
        bundle.GetArgument(11, "side").TryGetValueAsDreamList(out var side);
        bundle.GetArgument(12, "siege").TryGetValueAsType(out var siege);
        var stairs = bundle.GetArgument(6, "stairs");
        var rules = new RmWalkRules { StairsIcon = stairs, FootType = foot, MonsterType = monsters, GroundZ = ground, SkyZ = sky, Pass = pass, Side = side, SiegeType = siege, Swim = false };   // a group's places are on land (version 25)

        var map = bundle.MapManager;
        var order = new List<DreamObjectTurf> { seed };     // reach, in the order the DM list gets them
        var reach = new HashSet<DreamObjectTurf> { seed };
        var shut = new HashSet<DreamObjectTurf>();
        var front = new List<DreamObjectTurf> { seed };
        while (front.Count > 0) {
            var c = front[^1];
            front.RemoveAt(front.Count - 1);
            foreach (var (dx, dy) in Steps) {
                if (!map.TryGetTurfAt(new Vector2i(c.X + dx, c.Y + dy), c.Z, out var n)) continue;
                if (reach.Contains(n) || shut.Contains(n)) continue;
                if (Math.Max(Math.Abs(n.X - target.X), Math.Abs(n.Y - target.Y)) > r) continue;
                if (rules.Walkable(n, m, n) == 0) {
                    shut.Add(n);
                    continue;
                }
                reach.Add(n);
                order.Add(n);
                front.Add(n);
            }
        }

        var reachList = bundle.ObjectTree.CreateList();
        var places = bundle.ObjectTree.CreateList();
        foreach (var t in order) {
            reachList.SetValue(new DreamValue(t), new DreamValue(1));
            var k = Places(t, group, stairs, monsters);
            if (k > 0) places.SetValue(new DreamValue(t), new DreamValue(k));
        }
        var pair = bundle.ObjectTree.CreateList();
        using (var v = new DreamValue(reachList)) pair.AddValue(v);   // the pair holds them; this proc lets go
        using (var v = new DreamValue(places)) pair.AddValue(v);
        return new DreamValue(pair);
    }

    // Formations.dm RemasterSlotTilesDM: each slot point (in the order given, middle first) takes the free tile nearest
    // it, its own tile when that is free (it always wins), else the best of range(2) round it (the engine's own order:
    // the middle, then its view spiral; the first of equals), else the best of all those still free (places' order).
    // The sums as DM does them, in single precision. places (tile -> free places) is used up as tiles are taken.
    // Returns list(tiles, owners), owners each point's third item.
    [DreamProc("rm_slot_tiles")]
    [DreamProcParameter("ordered", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("sx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("sy", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("mx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("my", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("places", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_slot_tiles(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "ordered").TryGetValueAsDreamList(out var ordered)) return DreamValue.Null;
        bundle.GetArgument(1, "sx").TryGetValueAsFloat(out var sx);
        bundle.GetArgument(2, "sy").TryGetValueAsFloat(out var sy);
        bundle.GetArgument(3, "mx").TryGetValueAsFloat(out var mx);
        bundle.GetArgument(4, "my").TryGetValueAsFloat(out var my);
        if (!bundle.GetArgument(5, "z").TryGetValueAsInteger(out var z)) return DreamValue.Null;
        if (!bundle.GetArgument(6, "places").TryGetValueAsDreamList(out var places)) return DreamValue.Null;
        var map = bundle.MapManager;
        var maxx = map.Size.X;
        var maxy = map.Size.Y;
        var tiles = bundle.ObjectTree.CreateList();
        var owners = bundle.ObjectTree.CreateList();
        float Score(DreamObjectTurf c, float px, float py) {
            var t = MathF.Pow(c.X - px, 2) + MathF.Pow(c.Y - py, 2);
            return t + 0.1f * MathF.Max(MathF.Abs(c.X - mx), MathF.Abs(c.Y - my));
        }
        int Free(DreamObjectTurf c) {
            using var v = places.GetValue(new DreamValue(c));
            return v.TryGetValueAsInteger(out var k) ? k : (v.IsTruthy() ? 1 : 0);
        }
        foreach (var pv in ordered.EnumerateValues()) {
            if (!pv.TryGetValueAsDreamList(out var p)) return Drop(tiles, owners);
            using var p1 = p.GetValue(new DreamValue(1));
            using var p2 = p.GetValue(new DreamValue(2));
            if (!p1.TryGetValueAsFloat(out var x) || !p2.TryGetValueAsFloat(out var y)) return Drop(tiles, owners);
            var px = x + sx;
            var py = y + sy;
            DreamObjectTurf? best = null;
            var bestD = float.PositiveInfinity;
            var x0 = (int)Math.Clamp(MathF.Floor(px + 0.5f), 1, maxx);
            var y0 = (int)Math.Clamp(MathF.Floor(py + 0.5f), 1, maxy);
            map.TryGetTurfAt(new Vector2i(x0, y0), z, out var p0);
            if (p0 != null && Free(p0) > 0 && p0.X == px && p0.Y == py) best = p0;
            else if (p0 != null) {
                foreach (var c in Range2(p0)) {
                    if (Free(c) <= 0) continue;
                    var d = Score(c, px, py);
                    if (d < bestD) { best = c; bestD = d; }
                }
            }
            if (best == null) {
                foreach (var cv in places.EnumerateValues()) {
                    if (!cv.TryGetValueAsDreamObject<DreamObjectTurf>(out var c)) continue;
                    var d = Score(c, px, py);
                    if (d < bestD) { best = c; bestD = d; }
                }
            }
            if (best == null) break;
            var left = Free(best) - 1;
            if (left <= 0) places.RemoveValue(new DreamValue(best));
            else places.SetValue(new DreamValue(best), new DreamValue(left));
            tiles.AddValue(new DreamValue(best));
            using var p3 = p.GetLength() >= 3 ? p.GetValue(new DreamValue(3)) : DreamValue.Null;
            owners.AddValue(p3);
        }
        var pair = bundle.ObjectTree.CreateList();
        using (var v = new DreamValue(tiles)) pair.AddValue(v);   // the pair holds them; this proc lets go
        using (var v = new DreamValue(owners)) pair.AddValue(v);
        return new DreamValue(pair);
    }

    // an early "no answer": the lists made for it are held by nothing, so they are let go
    private static DreamValue Drop(DreamList a, DreamList b) {
        a.DecRef();
        b.DecRef();
        return DreamValue.Null;
    }

    // range(2, t)'s tiles in its own order: t, then the view spiral round it (DreamProcNativeHelpers.HandleRange), the
    // tiles it would leave out (invisibility 101 and up) left out here too.
    private static IEnumerable<DreamObjectTurf> Range2(DreamObjectTurf t) {
        if (Seen(t)) yield return t;
        foreach (var c in DreamProcNativeHelpers.MakeViewSpiral(t, new OpenDreamShared.Dream.ViewRange(2)))
            if (Seen(c)) yield return c;
    }

    private static bool Seen(DreamObjectTurf t) {
        using var appearanceValue = t.GetVariable("appearance");
        using var appearance = appearanceValue.MustGetValueAsAppearance();
        return appearance.Invisibility < 101;
    }

    // Formations.dm RmSortBy: L in order of K1, then K2, smallest first, equal keys in the order they came; in place.
    // Returns 1 (null for keys it can't read).
    [DreamProc("rm_sort_by")]
    [DreamProcParameter("L", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("K1", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("K2", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_sort_by(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "L").TryGetValueAsDreamList(out var l)) return DreamValue.Null;
        if (!bundle.GetArgument(1, "K1").TryGetValueAsDreamList(out var k1)) return DreamValue.Null;
        bundle.GetArgument(2, "K2").TryGetValueAsDreamList(out var k2);
        var n = l.GetLength();
        if (k1.GetLength() != n || (k2 != null && k2.GetLength() != n)) return DreamValue.Null;
        var items = new DreamValue[n];
        var a = new float[n];
        var b = new float[n];
        for (var i = 0; i < n; i++) {
            items[i] = l.GetValue(new DreamValue(i + 1));
            using var va = k1.GetValue(new DreamValue(i + 1));
            if (!va.TryGetValueAsFloat(out a[i])) return DreamValue.Null;
            if (k2 != null) {
                using var vb = k2.GetValue(new DreamValue(i + 1));
                if (!vb.TryGetValueAsFloat(out b[i])) return DreamValue.Null;
            }
        }
        var idx = new int[n];
        for (var i = 0; i < n; i++) idx[i] = i;
        Array.Sort(idx, (p, q) => a[p] != a[q] ? a[p].CompareTo(a[q]) : (b[p] != b[q] ? b[p].CompareTo(b[q]) : p.CompareTo(q)));
        for (var i = 0; i < n; i++) l.SetValue(new DreamValue(i + 1), items[idx[i]]);
        foreach (var v in items) v.Dispose();
        return new DreamValue(1);   // not L itself: a new DreamValue of it holds no reference, and DM letting it go would free L
    }

    // Orders.dm RemasterTilePlaces(T, group): free places on a tile for a group (two on a wall-walk), 0 for none.
    private static int Places(DreamObjectTurf t, DreamList group, DreamValue stairs, TreeEntry? monsters) {
        if (RmNative.Truthy(t, "density") || RmNative.VarEquals(t, "icon_state", Sky) || RmNative.VarEquals(t, "icon_state", Chasm)) return 0;
        if (RmNative.VarEquals(t, "icon", stairs)) return 0;
        var wallwalk = RmNative.Truthy(t, "remaster_wallwalk");
        var taken = 0;
        foreach (var x in t.Cell.Movables) {   // the tile's things (a deleted one passed over, as DM's for-in does)
            if (x.Deleted || !RmNative.Truthy(x, "density") || group.ContainsValue(new DreamValue(x))) continue;
            if (!wallwalk || monsters == null || !x.IsSubtypeOf(monsters)) return 0;
            taken++;
        }
        return Math.Max(0, (wallwalk ? 2 : 1) - taken);
    }
}
