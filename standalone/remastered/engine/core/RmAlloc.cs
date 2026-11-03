// What the game allocates, for the tick profiler (server cost, 2026-10-24; game/Code/Remastered/TickProfile.dm):
// rm_alloc_now() is the managed memory the game thread (the one DM runs on) has allocated so far, and rm_alloc_total()
// the whole process's, in kilobytes, wrapping every 1 GB (2^20 KB) so DM's 32-bit numbers keep 64-byte steps; a
// difference across the wrap adds 2^20. Read round each profiled call they give each system's KB a second; the process
// minus the game thread is the engine's own (the network, what each client is sent). Bound only where a test or the
// profiler declares them; their DM bodies return 0.
using OpenDreamRuntime.Objects;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmAlloc {
    private const double Wrap = 1 << 20;   // KB

    [DreamProc("rm_alloc_now")]
    public static DreamValue NativeProc_rm_alloc_now(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        return new DreamValue((float)(GC.GetAllocatedBytesForCurrentThread() / 1024.0 % Wrap));
    }

    [DreamProc("rm_alloc_total")]
    public static DreamValue NativeProc_rm_alloc_total(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        return new DreamValue((float)(GC.GetTotalAllocatedBytes(false) / 1024.0 % Wrap));
    }
}
