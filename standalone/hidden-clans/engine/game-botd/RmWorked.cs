// The worked tiles' tidy (native version 16; the owner, 10-28: "Yes, harvest next"). Breaking.dm keeps rm_worked: each tree
// or rock being worked (its first hp, blows, last blow, the blow's way) for the 3D view's cracks and a rock column's halves.
// At RM_WORKED_MAX (400) entries, every first blow on a new tile ran RemasterWorkTidy(1) over all of them: in a village of
// 2,000 workers more than 400 tiles are worked at once, so it ran dozens of times a game second (25 ms of 47 in the
// harvest blow, reports/polish-night-1026/harvest-native). This is that loop, step for step: over the entries in order,
// those whose last blow is older than 6,000 ticks (a standing tree or rock) or 50 (one broken) leave; of the others, the
// first with the oldest last blow; with full set and the list still at max, that one leaves too.
//   rm_worked_tidy(L, now, max, full)  1 when done; null (the game's own loop runs) when an entry isn't as the game makes them
using System.Collections.Generic;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmWorked {
    private static readonly List<(DreamValue key, DreamObjectTurf turf, float at)> Entries = new();
    private static readonly DreamValue Three = new(3);

    [DreamProc("rm_worked_tidy")]
    [DreamProcParameter("L", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("now", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("max", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("full", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_worked_tidy(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "L").TryGetValueAsDreamList(out var list)) return DreamValue.Null;
        if (!bundle.GetArgument(1, "now").TryGetValueAsFloat(out var now)) return DreamValue.Null;
        if (!bundle.GetArgument(2, "max").TryGetValueAsFloat(out var max)) return DreamValue.Null;
        var full = bundle.GetArgument(3, "full").IsTruthy();
        // every entry read first, the list unchanged: one the game didn't make (its loop would stop on it) gets the game's loop
        Entries.Clear();
        foreach (var key in list.EnumerateValues()) {   // the list's own values: never disposed
            if (!key.TryGetValueAsDreamObject<DreamObjectTurf>(out var t) || t == null || t.Deleted) continue;   // the typed loop skips them
            using var w = list.GetValue(key);
            if (!w.TryGetValueAsDreamList(out var W) || W.GetLength() < 3) {
                Entries.Clear();
                return DreamValue.Null;
            }
            using var last = W.GetValue(Three);
            if (!last.TryGetValueAsFloat(out var at)) {
                Entries.Clear();
                return DreamValue.Null;
            }
            Entries.Add((key, t, at));
        }
        DreamObjectTurf? oldest = null;
        var oldestAt = float.PositiveInfinity;
        foreach (var (key, t, at) in Entries) {
            if (now - at > (t.IsDense ? 6000 : 50)) list.RemoveValue(new DreamValue(t));
            else if (at < oldestAt) {
                oldest = t;
                oldestAt = at;
            }
        }
        Entries.Clear();
        if (full && oldest != null && list.GetLength() >= max) list.RemoveValue(new DreamValue(oldest));
        return new DreamValue(1);
    }
}
