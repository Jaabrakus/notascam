// The fog's explored marks (native version 32; the owner, 10-31: "does things multiple itmes"). Each unit that moved
// marked its whole sight circle into its side's explored map row by row in DM (Fog.dm RmFogMarkCircle: ~25 rows, ~50 us a
// circle, ~360 circles a second with 2,000 units on orders), almost all of it already marked. The same marks here, the
// same map: Explore.dm's memory, "chx,chy" (16x16 chunks) -> 16 numbers, one a row, bit i for the tile i + 1 across. A
// chunk the circle reaches that has no rows yet gets them (16 zeros), as the DM did, even where nothing new is marked.
//   rm_fog_mark(L, cx, cy, r, maxx, maxy)  L: one level's chunks; 1 when any tile was new, else 0. Null (the DM marks)
//                                          for anything it doesn't expect: a number that isn't whole, a chunk that isn't a
//                                          list of 16, a row that isn't a number.
using System.Collections.Generic;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmFog {
    private static bool Whole(DreamValue v, out int n) {
        n = 0;
        if (!v.TryGetValueAsFloat(out var f) || f != System.MathF.Floor(f) || System.MathF.Abs(f) > 16777216) return false;
        n = (int)f;
        return true;
    }

    [DreamProc("rm_fog_mark")]
    [DreamProcParameter("L", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("cx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("cy", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("r", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("maxx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("maxy", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_fog_mark(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "L").TryGetValueAsDreamList(out var L) || L.GetType() != typeof(DreamList)) return DreamValue.Null;
        if (!Whole(bundle.GetArgument(1, "cx"), out var cx) || !Whole(bundle.GetArgument(2, "cy"), out var cy) ||
            !Whole(bundle.GetArgument(3, "r"), out var r) || !Whole(bundle.GetArgument(4, "maxx"), out var maxx) ||
            !Whole(bundle.GetArgument(5, "maxy"), out var maxy)) return DreamValue.Null;
        var tree = bundle.ObjectTree;
        var added = false;
        var gy = -1;
        var gx = new List<DreamList?>();   // this chunk row's chunks, by chx (Fog.dm's gx)
        for (var y = System.Math.Max(1, cy - r); y <= System.Math.Min(maxy, cy + r); y++) {
            // round(sqrt(max(0, r * r - (y - cy) * (y - cy)))): DM's numbers are 32-bit floats, its one-argument round floors
            var half = (int)System.Math.Floor(System.MathF.Sqrt(System.Math.Max(0, r * r - (y - cy) * (y - cy))));
            var x0 = System.Math.Max(1, cx - half);
            var x1 = System.Math.Min(maxx, cx + half);
            var row = (y - 1) % 16 + 1;
            var chy = (y - 1) / 16;
            if (chy != gy) {
                gy = chy;
                gx.Clear();
            }
            for (var x = x0; x <= x1;) {
                var chx = (x - 1) / 16;
                var end = System.Math.Min(x1, chx * 16 + 16);
                while (gx.Count <= chx) gx.Add(null);
                var rows = gx[chx];
                if (rows == null) {
                    var key = new DreamValue($"{chx},{chy}");
                    using (var rv = L.GetValue(key)) {
                        if (rv.TryGetValueAsDreamList(out var had) && had.GetType() == typeof(DreamList)) rows = had;
                        else if (rv.IsTruthy()) return DreamValue.Null;   // something there that isn't a chunk's rows
                    }
                    if (rows == null) {
                        rows = tree.CreateList();
                        for (var i = 0; i < 16; i++) rows.AddValue(new DreamValue(0));
                        using (var nv = new DreamValue(rows)) L.SetValue(key, nv);   // the map holds it; this proc lets go
                    }
                    if (rows.GetLength() < 16) return DreamValue.Null;
                    gx[chx] = rows;
                }
                var lo = (x - 1) % 16;
                var hi = (end - 1) % 16;
                var bits = ((1 << (hi + 1)) - 1) & ~((1 << lo) - 1);
                var at = new DreamValue(row);
                int was;
                using (var wv = rows.GetValue(at)) {
                    if (wv.IsNull) was = 0;   // as DM's & and | take a null
                    else if (!wv.TryGetValueAsInteger(out was)) return DreamValue.Null;
                }
                if ((was & bits) != bits) {
                    rows.SetValue(at, new DreamValue(was | bits));
                    added = true;
                }
                x = end + 1;
            }
        }
        return new DreamValue(added ? 1 : 0);
    }
}
