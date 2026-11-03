using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class DreamProcNativeDatum {
    [DreamProc("Write")]
    [DreamProcParameter("F", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_Write(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (bundle.GetArgument(0, "F").TryGetValueAsDreamObject<DreamObjectSavefile>(out var file))
            file.WriteDatum(src!);
        return DreamValue.Null;
    }

    [DreamProc("Read")]
    [DreamProcParameter("F", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_Read(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (bundle.GetArgument(0, "F").TryGetValueAsDreamObject<DreamObjectSavefile>(out var file))
            file.ReadDatum(src!);
        return DreamValue.Null;
    }
}
