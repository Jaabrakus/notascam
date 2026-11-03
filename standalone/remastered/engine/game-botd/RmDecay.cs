// The lying items' timer (native version 18; the owner, 10-28: "Yes, item timers"). Every item put down on the ground ran
// its own 2006 loop (Items/Item Procs.dm atom/DeleteItem): awake once every 10 ticks while it lies (no suffix), Content3
// one more each time; past 180 the game's rule (kept on a stockpile, Content3 back to 1; else deleted). On a stockpile it
// never ended: about 1.8 ms of every tick per 10,000 items lying (reports/polish-night-1026/native-plan/item_timers.dm),
// growing as stores fill. Here one timer holds them all, on the same ticks: the game does the first look itself, as the
// loop's first pass did, and hands the item over (rm_decay_add); each later look is this one's, 10 ticks after the last:
// lifted (a suffix) -> Content3 null and it leaves; still lying -> Content3 + 1, and past 180 it is handed back to the game
// for the rule (rm_decay_tick's answer). A deleted item leaves. Content3 that isn't a number (set by something else
// meanwhile) ends its timer, as the loop's "+= 1" would have stopped it with an error. The timer holds a reference to each
// item while it runs, as the loop's src did.
//   rm_decay_add(I, now)  its next look 10 ticks on
//   rm_decay_tick(now)    every look due up to now; a list of the items past 180 (the game's rule), or null
//   rm_decay_count()      items held
using System.Collections.Generic;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmDecay {
    private sealed class Entry(DreamObject item, long due) {
        public readonly DreamObject Item = item;
        public long Due = due;
    }

    private static readonly List<Entry>?[] Buckets = new List<Entry>?[10];   // by due % 10: each look 10 ticks after the last
    private static long _done = -1;   // the last tick looked at
    private static int _held;

    [DreamProc("rm_decay_add")]
    [DreamProcParameter("I", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("now", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_decay_add(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "I").TryGetValueAsDreamObject<DreamObject>(out var item) || item == null || item.Deleted) return new DreamValue(0);
        if (!bundle.GetArgument(1, "now").TryGetValueAsFloat(out var now)) return new DreamValue(0);
        var due = (long)now + 10;
        item.IncRef();
        (Buckets[due % 10] ??= new List<Entry>()).Add(new Entry(item, due));
        _held++;
        return new DreamValue(1);
    }

    [DreamProc("rm_decay_tick")]
    [DreamProcParameter("now", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_decay_tick(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "now").TryGetValueAsFloat(out var nowF)) return DreamValue.Null;
        var now = (long)nowF;
        if (_done < 0 || now - _done > 10) _done = now - 1;   // a first call, or a long gap: each bucket once
        DreamList? over = null;
        for (var t = _done + 1; t <= now; t++) {
            var b = Buckets[t % 10];
            if (b == null || b.Count == 0) continue;
            var keep = 0;
            for (var i = 0; i < b.Count; i++) {
                var e = b[i];
                if (e.Due > t) {   // added for a later round of this bucket
                    b[keep++] = e;
                    continue;
                }
                if (Look(e.Item, bundle, ref over)) {
                    e.Due += 10;
                    b[keep++] = e;
                } else {
                    _held--;
                    e.Item.DecRef();   // the loop's src let go
                }
            }
            b.RemoveRange(keep, b.Count - keep);
        }
        _done = now;
        return over != null ? new DreamValue(over) : DreamValue.Null;
    }

    // One pass of the loop: true while it goes on.
    private static bool Look(DreamObject item, NativeProc.Bundle bundle, ref DreamList? over) {
        if (item.Deleted || item.Deleting) return false;
        if (RmNative.Truthy(item, "suffix")) {   // lifted: the loop ends, Content3 = null
            item.SetVariable("Content3", DreamValue.Null);
            return false;
        }
        float c = 0;
        if (item.TryGetVariable("Content3", out var cv)) {
            using (cv) {
                if (!cv.IsNull && !cv.TryGetValueAsFloat(out c)) return false;   // not a number: "+= 1" would have stopped it
            }
        }
        c += 1;
        item.SetVariable("Content3", new DreamValue(c));
        if (c > 180) (over ??= bundle.ObjectTree.CreateList()).AddValue(new DreamValue(item));
        return true;
    }

    [DreamProc("rm_decay_count")]
    public static DreamValue NativeProc_rm_decay_count(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        return new DreamValue(_held);
    }
}
