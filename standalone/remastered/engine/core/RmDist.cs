// get_dist by the engine (native version 24; the owner, 10-29: "Field way + get_dist"): the game's compiler's own
// DMStandard proc (replica/runtime/macos-x64/compiler/DMStandard/_Standard.dm), line for line, in place of its DM body
// (~1 us a call, ~19,000 a second in a 1000 v 1000):
//     if (Loc1 == Loc2) return -1
//     if (!istype(Loc1) || !istype(Loc2) || isarea(Loc1) || isarea(Loc2)) return 1.#INF
//     if (!Loc1.x || !Loc1.y || !Loc2.x || !Loc2.y) return 1.#INF
//     return max(abs(Loc2.x - Loc1.x), abs(Loc2.y - Loc1.y))
// == is the == opcode's own (DMOpcodeHandlers.IsEqual: a deleted object reads as null); istype(Loc1) is istype against
// the argument's declared /atom (a deleted object is no atom); x and y as their var reads give them. Bound only when the
// game declares rm_get_dist_native (Native.dm; it answers 1 here, 0 from the DM body), and never with RM_GET_DIST=0 in
// the server's environment. reports/polish-night-1026/field-way/tests/get_dist_check.dm compares it with the DM body.
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmDist {
    public static readonly bool Disabled = System.Environment.GetEnvironmentVariable("RM_GET_DIST") == "0";
    private static readonly DreamValue Same = new(-1), Far = new(float.PositiveInfinity);

    [DreamProc("get_dist")]
    [DreamProcParameter("Loc1", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("Loc2", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_get_dist(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var a = bundle.GetArgument(0, "Loc1");
        var b = bundle.GetArgument(1, "Loc2");
        if (DMOpcodeHandlers.IsEqual(a, b)) return Same;
        var atom = bundle.ObjectTree.Atom;
        if (!AtomXY(a, atom, out var x1, out var y1) || !AtomXY(b, atom, out var x2, out var y2)) return Far;
        if (x1 == 0 || y1 == 0 || x2 == 0 || y2 == 0) return Far;
        return new DreamValue(System.Math.Max(System.Math.Abs(x2 - x1), System.Math.Abs(y2 - y1)));
    }

    [DreamProc("rm_get_dist_native")]
    public static DreamValue NativeProc_rm_get_dist_native(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        return new DreamValue(1);
    }

    // istype(v) against /atom and not isarea(v): its x and y as DM reads them.
    private static bool AtomXY(DreamValue v, TreeEntry atom, out float x, out float y) {
        x = y = 0;
        if (!v.TryGetValueAsDreamObject<DreamObject>(out var o) || o == null || o.Deleted || !o.IsSubtypeOf(atom) || o is DreamObjectArea) return false;
        switch (o) {
            case DreamObjectMovable m:
                x = m.X;
                y = m.Y;
                return true;
            case DreamObjectTurf t:
                x = t.X;
                y = t.Y;
                return true;
        }
        x = Read(o, "x");
        y = Read(o, "y");
        return true;
    }

    private static float Read(DreamObject o, string name) {
        if (!o.TryGetVariable(name, out var v)) return 0;
        using (v) return v.TryGetValueAsFloat(out var n) ? n : 0;
    }
}
