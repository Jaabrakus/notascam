// What the walk checks and the plain step read of a movable, kept while its change counter stands (native version 23;
// the owner, 10-29: "Step-off + step"). A walk check (RmWalk.cs) read each thing on a tile by name, its density first: a
// battle tile holds ~13 (bodies, blood, gear), ~1.3 us a check, ~4 checks a step through friends. Kept on the movable
// itself (DreamObjectMovable.RmKept, the VER patch in tools/build_runtime.py) with its change counter RmChanges (RmVer.cs),
// which moves on every DM var write to it or anything in it, every move and every look change: a value is read again
// the first time it is asked for after the counter moved. The vars kept are only ever written by DM (SetVariable) or
// animate, both counted, so the answers are the reads' own. Owner is kept as read and only compared or looked up.
// v24: RM_KEPT_VERIFY=1 in the server's environment: every answer is also read fresh and compared (rm_kept_stats(), for tests:
// "kept N read N checked N differ N").
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;

namespace OpenDreamRuntime.Procs.Native;

internal sealed class RmKept {
    private static readonly bool Verify = System.Environment.GetEnvironmentVariable("RM_KEPT_VERIFY") == "1";
    private static long _kept, _read, _checked, _differ;

    [DreamProc("rm_kept_stats")]
    public static DreamValue NativeProc_rm_kept_stats(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        return new DreamValue($"kept {_kept} read {_read} checked {_checked} differ {_differ}");
    }

    private static void Check(bool same) {
        _checked++;
        if (!same) _differ++;
    }
    private const int DenseBit = 1, FlyingBit = 2, WagonBit = 4, OwnerBit = 8;
    private int _changes, _known;
    private bool _dense, _flying, _wagon;
    private DreamValue _owner;   // not counted: the movable's var holds the reference

    private static RmKept Of(DreamObjectMovable a) {
        if (a.RmKept is RmKept k) {
            if (k._changes != a.RmChanges) {
                k._changes = a.RmChanges;
                k._known = 0;
            }
            return k;
        }
        k = new RmKept { _changes = a.RmChanges };
        a.RmKept = k;
        return k;
    }

    public static bool Dense(DreamObject o) {
        if (o is not DreamObjectMovable a) return RmNative.Truthy(o, "density");
        var k = Of(a);
        if ((k._known & DenseBit) == 0) {
            k._dense = RmNative.Truthy(a, "density");
            k._known |= DenseBit;
            _read++;
        } else {
            _kept++;
            if (Verify) Check(k._dense == RmNative.Truthy(a, "density"));
        }
        return k._dense;
    }

    public static bool Flying(DreamObject o) {
        if (o is not DreamObjectMovable a) return RmNative.Truthy(o, "Flying");
        var k = Of(a);
        if ((k._known & FlyingBit) == 0) {
            k._flying = RmNative.Truthy(a, "Flying");
            k._known |= FlyingBit;
        } else if (Verify) Check(k._flying == RmNative.Truthy(a, "Flying"));
        return k._flying;
    }

    public static bool Wagon(DreamObject o) {
        if (o is not DreamObjectMovable a) return RmNative.Truthy(o, "Wagon");
        var k = Of(a);
        if ((k._known & WagonBit) == 0) {
            k._wagon = RmNative.Truthy(a, "Wagon");
            k._known |= WagonBit;
        } else if (Verify) Check(k._wagon == RmNative.Truthy(a, "Wagon"));
        return k._wagon;
    }

    // Owner as read (null when it has none): compare or look it up, never keep or dispose it.
    public static DreamValue Owner(DreamObjectMovable a) {
        var k = Of(a);
        if ((k._known & OwnerBit) == 0) {
            if (!a.TryGetVariable("Owner", out var v)) v = DreamValue.Null;
            k._owner = v;
            v.Dispose();
            k._known |= OwnerBit;
        } else if (Verify) {
            if (!a.TryGetVariable("Owner", out var now)) now = DreamValue.Null;
            using (now) Check(DMOpcodeHandlers.IsEqual(now, k._owner) && now.Type == k._owner.Type);
        }
        return k._owner;
    }
}
