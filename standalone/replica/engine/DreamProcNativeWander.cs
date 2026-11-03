using System.Linq;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using OpenDreamShared.Dream;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

// Independently randomized wandering must never advance rand()/prob()/pick().
// The unobstructed forward bias is measured against BYOND 516.1655. Its 5x5
// edge-following rule is still an explicitly open compatibility difference.
internal static class DreamProcNativeWander {
    private static readonly Random Random = new();
    private static readonly int[] Directions = [1, 5, 4, 6, 2, 10, 8, 9];

    [DreamProc("get_step_rand")]
    [DreamProcParameter("Ref", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_get_step_rand(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "Ref").TryGetValueAsDreamObject<DreamObjectAtom>(out var atom))
            return new(0);
        atom.GetVariable("dir").TryGetValueAsInteger(out var facing);
        var start = Array.IndexOf(Directions, facing);
        if (start < 0) start = 0;
        var side = Random.Next(2) == 0 ? 1 : -1;
        Span<int> offsets = stackalloc int[] { 0, side, -side, 2*side, -2*side, 3*side, -3*side, 4 };
        var dense = atom.GetVariable("density").IsTruthy();
        foreach (var offset in offsets) {
            var direction = (AtomDirection)Directions[(start + offset + 8) % 8];
            var target = DreamProcNativeHelpers.GetStep(bundle.AtomManager, bundle.MapManager, atom, direction);
            if (target == null) continue;
            if (dense && (target.IsDense || target.Contents.GetValues().Any(value =>
                    value.TryGetValueAsDreamObject<DreamObjectAtom>(out var other) && other != atom &&
                    other.GetVariable("density").IsTruthy()))) continue;
            if (Random.Next(8) == 0) continue;
            if (offset == 4 && Random.Next(4) != 0) continue;
            target.IncRef();
            return new(target);
        }
        return new(0);
    }
}
