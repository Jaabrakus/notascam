// A group move's plan, step for step as game/Code/Remastered/Formations.dm RemasterGroupForm (engine v8 candidate,
// formations, 2026-10-25; native version 9). The DM loops stay as the fallback and the reference (RM_NATIVE_PLAN=0 uses
// them; RM_PLAN_VERIFY=1 runs both and logs any difference). DM's numbers are 32-bit floats: every sum and product here
// is a float, in DM's order, and round() is floor (OpenDream's one-argument round), so the answers are the same bits.
// A 30,000-unit move spent ~270 ms planning, most of it in these loops (tests/plan_profile_check.dm).
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmPlan {
    // RemasterShapePoints' loop, with its facing (sx, sy: RemasterSnapDir) and row width (per: RemasterShapePer) from DM:
    // n points, front row first, each row right to left, each list(x, y, null) as RemasterGroupForm keeps them.
    [DreamProc("rm_shape_points")]
    [DreamProcParameter("n", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("tx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("ty", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("sx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("sy", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("per", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("box", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_shape_points(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "n").TryGetValueAsFloat(out var n)) return DreamValue.Null;
        if (!bundle.GetArgument(1, "tx").TryGetValueAsFloat(out var tx)) return DreamValue.Null;
        if (!bundle.GetArgument(2, "ty").TryGetValueAsFloat(out var ty)) return DreamValue.Null;
        if (!bundle.GetArgument(3, "sx").TryGetValueAsFloat(out var sx)) return DreamValue.Null;
        if (!bundle.GetArgument(4, "sy").TryGetValueAsFloat(out var sy)) return DreamValue.Null;
        if (!bundle.GetArgument(5, "per").TryGetValueAsFloat(out var per) || per <= 0) return DreamValue.Null;
        var box = bundle.GetArgument(6, "box").IsTruthy();
        var ax = -sy;
        var ay = sx;
        var rowsAll = Floor((n + per - 1) / per);
        var points = bundle.ObjectTree.CreateList();
        for (float i = 0; i < n; i++) {
            var r = Floor(i / per);
            var c = i % per;
            var count = r == rowsAll - 1 ? n - r * per : per;
            var off = c - Floor((count - 1) / 2);
            var back = box ? r - Floor((rowsAll - 1) / 2) : r;
            var p = bundle.ObjectTree.CreateList();
            p.AddValue(new DreamValue(tx + ax * off - sx * back));
            p.AddValue(new DreamValue(ty + ay * off - sy * back));
            p.AddValue(DreamValue.Null);
            using (var pv = new DreamValue(p)) points.AddValue(pv);   // the points hold it; this proc lets go
        }
        return new DreamValue(points);
    }

    // The middle-first key of each point (RemasterGroupForm: max(abs(p[1] + sx - mx), abs(p[2] + sy - my))), parallel to
    // points.
    [DreamProc("rm_points_ok")]
    [DreamProcParameter("points", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("sx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("sy", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("mx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("my", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_points_ok(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "points").TryGetValueAsDreamList(out var points)) return DreamValue.Null;
        bundle.GetArgument(1, "sx").TryGetValueAsFloat(out var sx);
        bundle.GetArgument(2, "sy").TryGetValueAsFloat(out var sy);
        bundle.GetArgument(3, "mx").TryGetValueAsFloat(out var mx);
        bundle.GetArgument(4, "my").TryGetValueAsFloat(out var my);
        var ok = bundle.ObjectTree.CreateList();
        foreach (var pv in points.EnumerateValues()) {
            if (!pv.TryGetValueAsDreamList(out var p) || !Xy(p, out var x, out var y)) {   // DM's typed loop would skip it: leave it to DM
                ok.DecRef();   // made here and held by nothing: let go
                return DreamValue.Null;
            }
            ok.AddValue(new DreamValue(MathF.Max(MathF.Abs(x + sx - mx), MathF.Abs(y + sy - my))));
        }
        return new DreamValue(ok);
    }

    // The hand-out for a line, column or box (RemasterGroupForm's last branch): units sorted front first then right to
    // left (k1, k2; units sorted in place, as DM does), the tiles put back in shape order (each point's place in the
    // middle-first order, from ok), then row by row each row's units to its slots across from them. Returns assign
    // (unit -> tile), its keys in DM's order.
    [DreamProc("rm_box_handout")]
    [DreamProcParameter("units", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("anchors", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("cx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("cy", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("ffx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("ffy", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("ok", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("tiles", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("mx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("my", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("per", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_box_handout(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "units").TryGetValueAsDreamList(out var unitList)) return DreamValue.Null;
        if (!bundle.GetArgument(1, "anchors").TryGetValueAsDreamList(out var anchors)) return DreamValue.Null;
        bundle.GetArgument(2, "cx").TryGetValueAsFloat(out var cx);
        bundle.GetArgument(3, "cy").TryGetValueAsFloat(out var cy);
        bundle.GetArgument(4, "ffx").TryGetValueAsFloat(out var ffx);
        bundle.GetArgument(5, "ffy").TryGetValueAsFloat(out var ffy);
        if (!bundle.GetArgument(6, "ok").TryGetValueAsDreamList(out var okList)) return DreamValue.Null;
        if (!bundle.GetArgument(7, "tiles").TryGetValueAsDreamList(out var tileList)) return DreamValue.Null;
        bundle.GetArgument(8, "mx").TryGetValueAsFloat(out var mx);
        bundle.GetArgument(9, "my").TryGetValueAsFloat(out var my);
        if (!bundle.GetArgument(10, "per").TryGetValueAsFloat(out var perF) || perF < 1) return DreamValue.Null;
        var per = (int)perF;
        var ax = -ffy;
        var ay = ffx;

        // the units and their anchors (list(x, y)); anything DM's typed loop would treat differently: leave it to DM
        var n = unitList.GetLength();
        var units = new DreamValue[n];
        var ux = new float[n];
        var uy = new float[n];
        for (var i = 0; i < n; i++) {
            units[i] = unitList.GetValue(new DreamValue(i + 1));
            if (!units[i].TryGetValueAsDreamObject<DreamObjectMob>(out _)) return Fail(units);
            using var av = anchors.GetValue(units[i]);
            if (!av.TryGetValueAsDreamList(out var a) || !Xy(a, out ux[i], out uy[i])) return Fail(units);
        }
        // front first, then right to left; equal keys kept in the order they came (RmSortBy)
        var k1 = new float[n];
        var k2 = new float[n];
        for (var i = 0; i < n; i++) {
            k1[i] = -((ux[i] - cx) * ffx + (uy[i] - cy) * ffy);
            k2[i] = (ux[i] - cx) * ax + (uy[i] - cy) * ay;
        }
        var uidx = Order(n, k1, k2);
        for (var i = 0; i < n; i++) unitList.SetValue(new DreamValue(i + 1), units[uidx[i]]);   // DM sorts units in place

        // the tiles back in shape order: point j's place in the middle-first order is at[j] (stable sort of 1..m by ok)
        var m = okList.GetLength();
        var ok = new float[m];
        for (var j = 0; j < m; j++) {
            using var v = okList.GetValue(new DreamValue(j + 1));
            if (!v.TryGetValueAsFloat(out ok[j])) return Fail(units);
        }
        var perm = Order(m, ok, null);
        var at = new int[m];
        for (var i = 0; i < m; i++) at[perm[i]] = i + 1;
        var nt = tileList.GetLength();
        var shapeTiles = new List<DreamObjectTurf>();
        for (var j = 0; j < m; j++) {
            var i = at[j];
            if (i == 0 || i > nt) continue;
            using var tv = tileList.GetValue(new DreamValue(i));
            if (!tv.TryGetValueAsDreamObject<DreamObjectTurf>(out var tt)) return Fail(units);
            shapeTiles.Add(tt);
        }

        // row by row
        var assign = bundle.ObjectTree.CreateList();
        var count = Math.Min(n, shapeTiles.Count);
        for (var i0 = 0; i0 < count; i0 += per) {
            var i1 = Math.Min(i0 + per, count);
            var len = i1 - i0;
            var ku = new float[len];
            var kt = new float[len];
            for (var q = 0; q < len; q++) {
                var u = uidx[i0 + q];
                ku[q] = (ux[u] - cx) * ax + (uy[u] - cy) * ay;
                var t = shapeTiles[i0 + q];
                kt[q] = (t.X - mx) * ax + (t.Y - my) * ay;
            }
            var ru = Order(len, ku, null);
            var rt = Order(len, kt, null);
            for (var q = 0; q < len; q++) assign.SetValue(units[uidx[i0 + ru[q]]], new DreamValue(shapeTiles[i0 + rt[q]]));
        }
        foreach (var v in units) v.Dispose();
        return new DreamValue(assign);
    }

    // RemasterGroupForm's anchors loop for an order that isn't queued, from group[from] on: each unit standing on a tile of
    // T's level gets anchors[M] = list(x, y) and start[M] = its tile; one on another level (stairs, a climb: DM's) stops it,
    // and its index comes back for DM to do and call again after it. Returns length(group) + 1 when all are done.
    [DreamProc("rm_plan_anchors")]
    [DreamProcParameter("group", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("from", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("anchors", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("start", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_plan_anchors(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "group").TryGetValueAsDreamList(out var group)) return DreamValue.Null;
        if (!bundle.GetArgument(1, "from").TryGetValueAsInteger(out var from) || from < 1) return DreamValue.Null;
        if (!bundle.GetArgument(2, "z").TryGetValueAsInteger(out var z)) return DreamValue.Null;
        if (!bundle.GetArgument(3, "anchors").TryGetValueAsDreamList(out var anchors)) return DreamValue.Null;
        if (!bundle.GetArgument(4, "start").TryGetValueAsDreamList(out var start)) return DreamValue.Null;
        var n = group.GetLength();
        for (var k = from; k <= n; k++) {
            using var mv = group.GetValue(new DreamValue(k));
            if (!mv.TryGetValueAsDreamObject<DreamObjectMob>(out var m) || m.Deleted) continue;   // DM's typed loop skips it
            if (m.Loc is not DreamObjectTurf s) continue;                                         // not on a tile: DM goes on
            if (s.Z != z) return new DreamValue(k);                                               // another level: DM's
            var a = bundle.ObjectTree.CreateList();
            a.AddValue(new DreamValue(s.X));
            a.AddValue(new DreamValue(s.Y));
            using (var av = new DreamValue(a)) anchors.SetValue(mv, av);   // the anchors hold it; this proc lets go
            start.SetValue(mv, new DreamValue(s));
        }
        return new DreamValue(n + 1);
    }

    // RemasterUncross for RM_SWAP_ALL or fewer (every pair; the cells are DM's): passes that shorten the routes in all until
    // none does (six at most), then one that also swaps crossing routes of the same length (ties, when on). assign updated
    // in place, as DM does; returns list(passes, checks, swaps) for rm_uncross_last.
    [DreamProc("rm_uncross_all")]
    [DreamProcParameter("assign", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("anchors", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("key_of", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("ties_on", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_uncross_all(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "assign").TryGetValueAsDreamList(out var assign)) return DreamValue.Null;
        if (!bundle.GetArgument(1, "anchors").TryGetValueAsDreamList(out var anchors)) return DreamValue.Null;
        if (!bundle.GetArgument(2, "key_of").TryGetValueAsDreamList(out var keyOf)) return DreamValue.Null;
        var tiesOn = bundle.GetArgument(3, "ties_on").IsTruthy();
        var who = new List<DreamValue>();
        foreach (var v in assign.EnumerateValues())
            if (v.TryGetValueAsDreamObject<DreamObjectMob>(out var mm) && !mm.Deleted) who.Add(v);
        var n = who.Count;
        var result = bundle.ObjectTree.CreateList();
        if (n < 2) {
            result.AddValue(new DreamValue(0)); result.AddValue(new DreamValue(0)); result.AddValue(new DreamValue(0));
            return new DreamValue(result);   // DM returns before setting rm_uncross_last: the caller keeps it then
        }
        var ax = new float[n];
        var ay = new float[n];
        var sl = new DreamObjectTurf[n];
        var key = new DreamValue[n];
        for (var i = 0; i < n; i++) {
            using var av = anchors.GetValue(who[i]);
            if (!av.TryGetValueAsDreamList(out var a) || !Xy(a, out ax[i], out ay[i])) {
                result.DecRef();   // made here and held by nothing: let go
                return DreamValue.Null;
            }
            using var sv = assign.GetValue(who[i]);
            if (!sv.TryGetValueAsDreamObject<DreamObjectTurf>(out var t)) {
                result.DecRef();   // made here and held by nothing: let go
                return DreamValue.Null;
            }
            sl[i] = t;
            key[i] = keyOf.GetValue(who[i]);
        }
        const int cap = 6;
        var ties = false;
        int passes = 0, checks = 0, swaps = 0;
        for (var pass = 1; pass <= cap + 1; pass++) {
            var swapped = false;
            passes++;
            for (var a = 0; a < n; a++) {
                for (var b = a + 1; b < n; b++) {
                    if (!key[a].Equals(key[b])) continue;   // an archer never swaps onto a front square
                    checks++;
                    var ta = sl[a];
                    var tb = sl[b];
                    var now = MathF.Sqrt(MathF.Pow(ta.X - ax[a], 2) + MathF.Pow(ta.Y - ay[a], 2)) + MathF.Sqrt(MathF.Pow(tb.X - ax[b], 2) + MathF.Pow(tb.Y - ay[b], 2));
                    var then = MathF.Sqrt(MathF.Pow(tb.X - ax[a], 2) + MathF.Pow(tb.Y - ay[a], 2)) + MathF.Sqrt(MathF.Pow(ta.X - ax[b], 2) + MathF.Pow(ta.Y - ay[b], 2));
                    if (then < now - 0.01f || (ties && tiesOn && then < now + 0.01f && SegCross(ax[a], ay[a], ta.X, ta.Y, ax[b], ay[b], tb.X, tb.Y))) {
                        sl[a] = tb;
                        sl[b] = ta;
                        swapped = true;
                        swaps++;
                    }
                }
            }
            if (ties) break;
            if (!swapped || pass >= cap) ties = true;
        }
        for (var i = 0; i < n; i++) assign.SetValue(who[i], new DreamValue(sl[i]));
        foreach (var k in key) k.Dispose();
        result.AddValue(new DreamValue(passes));
        result.AddValue(new DreamValue(checks));
        result.AddValue(new DreamValue(swaps));
        return new DreamValue(result);
    }

    // RmSegCross: do A-B and C-D cross (not just touch)? DM's products, in DM's order
    private static bool SegCross(float ax, float ay, float bx, float by, float cx, float cy, float dx, float dy) {
        var d1 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx);
        var d2 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx);
        var d3 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
        var d4 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax);
        return ((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0));
    }

    // The units of an order (RemasterGroupForm's, and RemasterOrder's without the siege test): of the selection, in its
    // order, each /mob/Monsters (not deleted) whose Owner is the player, that is in its UnitList, not a cart (Wagon), alive
    // (HP > 0), not GoingToDie, and (siege given) not a siege engine. A new list.
    [DreamProc("rm_plan_group")]
    [DreamProcParameter("selected", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("owner", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("units", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("monsters", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("siege", Type = DreamValueTypeFlag.DreamType)]
    public static DreamValue NativeProc_rm_plan_group(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "selected").TryGetValueAsDreamList(out var selected)) return DreamValue.Null;
        var owner = bundle.GetArgument(1, "owner");
        if (!bundle.GetArgument(2, "units").TryGetValueAsDreamList(out var units)) return DreamValue.Null;
        if (!bundle.GetArgument(3, "monsters").TryGetValueAsType(out var monsters)) return DreamValue.Null;
        bundle.GetArgument(4, "siege").TryGetValueAsType(out var siege);
        var group = bundle.ObjectTree.CreateList();
        foreach (var v in selected.EnumerateValues()) {
            if (!v.TryGetValueAsDreamObject<DreamObject>(out var m) || m == null || m.Deleted || !m.IsSubtypeOf(monsters)) continue;
            if (!m.TryGetVariable("Owner", out var o)) continue;
            using (o) if (!o.Equals(owner)) continue;
            if (!units.ContainsValue(v)) continue;
            if (RmNative.Truthy(m, "Wagon")) continue;
            if (!m.TryGetVariable("HP", out var hp)) continue;
            using (hp) if (!hp.TryGetValueAsFloat(out var h) || !(h > 0)) continue;
            if (RmNative.Truthy(m, "GoingToDie")) continue;
            if (siege != null && m.IsSubtypeOf(siege)) continue;
            group.AddValue(v);
        }
        return new DreamValue(group);
    }

    // The points in middle-first order (RemasterGroupForm: ordered = points.Copy(), ok = each one's key, RmSortBy(ordered,
    // ok)): list(ordered, ok), ok parallel to points (not sorted), as the hand-out needs it.
    [DreamProc("rm_points_order")]
    [DreamProcParameter("points", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("sx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("sy", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("mx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("my", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_points_order(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "points").TryGetValueAsDreamList(out var points)) return DreamValue.Null;
        bundle.GetArgument(1, "sx").TryGetValueAsFloat(out var sx);
        bundle.GetArgument(2, "sy").TryGetValueAsFloat(out var sy);
        bundle.GetArgument(3, "mx").TryGetValueAsFloat(out var mx);
        bundle.GetArgument(4, "my").TryGetValueAsFloat(out var my);
        var vals = new List<DreamValue>();
        var keys = new List<float>();
        foreach (var pv in points.EnumerateValues()) {
            // DM's typed loop would treat it otherwise: leave it to DM (the values are the list's own: EnumerateValues adds no
            // reference, so there is nothing to give back)
            if (!pv.TryGetValueAsDreamList(out var p) || !Xy(p, out var x, out var y)) return DreamValue.Null;
            vals.Add(pv);
            keys.Add(MathF.Max(MathF.Abs(x + sx - mx), MathF.Abs(y + sy - my)));
        }
        var k = keys.ToArray();
        var idx = Order(k.Length, k, null);
        var ordered = bundle.ObjectTree.CreateList();
        var ok = bundle.ObjectTree.CreateList();
        for (var i = 0; i < idx.Length; i++) ordered.AddValue(vals[idx[i]]);
        foreach (var f in k) ok.AddValue(new DreamValue(f));
        var pair = bundle.ObjectTree.CreateList();
        using (var v = new DreamValue(ordered)) pair.AddValue(v);   // the pair holds them; this proc lets go
        using (var v = new DreamValue(ok)) pair.AddValue(v);
        return new DreamValue(pair);
    }

    private static DreamValue Fail(DreamValue[] held) {
        foreach (var v in held) v.Dispose();
        return DreamValue.Null;
    }

    // OpenDream's one-argument round(): floor, through a double, back to a float
    private static float Floor(float a) => (float)Math.Floor(a);

    private static bool Xy(DreamList p, out float x, out float y) {
        x = y = 0;
        if (p.GetLength() < 2) return false;
        using var p1 = p.GetValue(new DreamValue(1));
        using var p2 = p.GetValue(new DreamValue(2));
        return p1.TryGetValueAsFloat(out x) && p2.TryGetValueAsFloat(out y);
    }

    // indices 0..n-1 in order of a (then b), equal keys in the order they came: RmSortBy's order
    private static int[] Order(int n, float[] a, float[]? b) {
        var idx = new int[n];
        for (var i = 0; i < n; i++) idx[i] = i;
        Array.Sort(idx, (p, q) => a[p] != a[q] ? a[p].CompareTo(a[q]) : (b != null && b[p] != b[q] ? b[p].CompareTo(b[q]) : p.CompareTo(q)));
        return idx;
    }
}
