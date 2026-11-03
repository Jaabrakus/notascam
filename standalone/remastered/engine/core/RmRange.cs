// Remastered: range()'s movables without its tiles (native version 28; server upgrades U6, 10-31).
//   rm_range_movables(r, center)   the movables range(r, center) lists for a tile center, in its order (the center's
//                                  contents, then each tile of the view spiral's; DreamProcNativeHelpers.HandleRange),
//                                  leaving out what range leaves out (invisibility 101 and up). No tiles, no areas.
//                                  Null for a center that isn't a tile (the caller then uses range itself).
// A caller that walks range()'s list for its movables only (`for(var/atom/movable/A in range(r, C))`) got every tile
// too: 2,601 of them at r = 25, each with its appearance read, for a few hundred things on them (the 3D scene,
// View3D.dm Remaster3DThings, twice a second for each player).
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmRange {
    [DreamProc("rm_range_movables")]
    [DreamProcParameter("r", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("center", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_range_movables(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "r").TryGetValueAsInteger(out var r) || r < 0 ||
            !bundle.GetArgument(1, "center").TryGetValueAsDreamObject<DreamObjectTurf>(out var center) || center == null)
            return DreamValue.Null;
        var atoms = bundle.AtomManager;
        var list = bundle.ObjectTree.CreateList();

        void Add(DreamObjectTurf t) {
            foreach (DreamValue content in t.EnumerateContents()) {
                if (content.TryGetValueAsDreamObject<DreamObjectAtom>(out var a) && a != null && atoms.MustGetAppearance(a).Invisibility >= 101)
                    continue;   // range leaves it out
                list.AddValue(content);
            }
        }

        Add(center);
        foreach (var t in DreamProcNativeHelpers.MakeViewSpiral(center, new OpenDreamShared.Dream.ViewRange(r)))
            Add(t);
        return new DreamValue(list);
    }
}
