// What changed in a list since a caller last looked (native version 33; the owner, 10-31: "it rebuild entries multiple
// times or does things multiple itmes"). A game that works something out from every thing in a big list (a player's
// units: the fog's sight circles, the 3D view's far figures) walked the whole list in DM to find the few that changed.
// Here the walk is the engine's: each caller (who, a player; slot, one of its uses) keeps what it saw, and the answer
// names only the things whose change counter (RmVer.cs) moved, with their places, so the game touches only those.
//   rm_list_changed(who, slot, L, state)  list(changed, places, all): the things in L whose counter moved since this
//                                         caller's last call, and each one's place in L (1-based). all is 1 when the
//                                         caller must take everything as changed (and the two lists are then empty):
//                                         its first call, a thing come into L or gone from it, a thing at another place
//                                         in L, or a thing at some place not what it was (a deleted one, a null). state
//                                         1: rm_ver_state's counter (its own steps aside), else rm_ver's.
using System.Collections.Generic;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmChanged {
    private const int Mask = 0xFFFFFF;

    // what one caller saw: each live movable's counter and place, and what stood at the other places
    private sealed class Seen {
        public Dictionary<DreamObjectMovable, (int Ver, int At)> Had = new();
        public Dictionary<DreamObjectMovable, (int Ver, int At)> Next = new();
        public Dictionary<int, object?> Odd = new();
        public Dictionary<int, object?> OddNext = new();
        public bool Fresh = true;
    }
    private static readonly System.Runtime.CompilerServices.ConditionalWeakTable<DreamObject, Seen[]> _seen = new();

    [DreamProc("rm_list_changed")]
    [DreamProcParameter("who", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("slot", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("L", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("state", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_list_changed(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "who").TryGetValueAsDreamObject<DreamObject>(out var who) || who == null ||
            !bundle.GetArgument(1, "slot").TryGetValueAsInteger(out var slot) || slot < 0 || slot > 7 ||
            !bundle.GetArgument(2, "L").TryGetValueAsDreamList(out var L)) return DreamValue.Null;
        bundle.GetArgument(3, "state").TryGetValueAsInteger(out var state);
        var seen = (_seen.GetValue(who, _ => new Seen[8])[slot] ??= new Seen());
        var all = seen.Fresh;
        var tree = bundle.ObjectTree;
        var changed = tree.CreateList();
        var places = tree.CreateList();
        var next = seen.Next;
        var oddNext = seen.OddNext;
        next.Clear();
        oddNext.Clear();
        var at = 0;
        foreach (var v in L.EnumerateValues()) {
            at++;
            if (v.TryGetValueAsDreamObject<DreamObjectMovable>(out var m) && m != null && !m.Deleted) {
                var ver = (state == 1 ? m.RmState : m.RmChanges) & Mask;
                if (!next.TryAdd(m, (ver, at))) { all = true; continue; }   // in the list twice
                if (all) continue;
                if (!seen.Had.TryGetValue(m, out var h) || h.At != at) all = true;   // come, or at another place
                else if (h.Ver != ver) {
                    changed.AddValue(new DreamValue(m));
                    places.AddValue(new DreamValue(at));
                }
            } else {
                // a null, a deleted thing, anything not a movable: what stands there (the same deleted thing again is no change)
                v.TryGetValueAsDreamObject<DreamObject>(out var o);
                oddNext[at] = o;
            }
        }
        if (!all && next.Count != seen.Had.Count) all = true;   // one went (or was deleted)
        if (!all) {
            if (oddNext.Count != seen.Odd.Count) all = true;
            else foreach (var (k, o) in oddNext)
                if (!seen.Odd.TryGetValue(k, out var was) || !ReferenceEquals(was, o)) { all = true; break; }
        }
        seen.Next = seen.Had;
        seen.Had = next;
        seen.OddNext = seen.Odd;
        seen.Odd = oddNext;
        seen.Fresh = false;
        if (all) {
            changed.Cut();
            places.Cut();
        }
        var result = tree.CreateList();
        using (var cv = new DreamValue(changed)) result.AddValue(cv);
        using (var pv = new DreamValue(places)) result.AddValue(pv);
        result.AddValue(new DreamValue(all ? 1 : 0));
        return new DreamValue(result);
    }
}
