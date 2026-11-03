// Sleeping tiles (map memory, planning/MAP_MEMORY.md; native version 10, with the COMPACT patch in tools/build_runtime.py,
// engine/compact/): DM's handle on the engine's sleeping tiles (Map/DreamMapManager.RmTiles.cs). The game declares the
// first six in Code/Remastered/Native.dm (Regions.dm's sweep uses them); the rest are bound only where a test declares them.
//   rm_tiles_sleep(x0, y0, x1, y1, z, dry) -> "slept=N|already=..|held=..|tag=..|varslist=..|values=..|lists=..|contents=..|things=..|full=..|watched=.."
//   rm_tiles_sleep_box(x0, y0, x1, y1, z)  -> tiles put to sleep (a number: the game's sweep)
//   rm_tiles_wake(x0, y0, x1, y1, z)       -> tiles woken
//   rm_tiles_count(x0, y0, x1, y1, z)      -> tiles asleep in the box (wakes nothing)
//   rm_tiles_wake_cost(x0, y0, x1, y1, z)  -> "woken=N|allocated=B": the bytes waking them allocated
//   rm_tiles_stats()                       -> "sleeping=..|blocks=..|bytes=..|woken=..|slept=..|vararrays=..|varentries=.."
//   rm_heap()                              -> the managed heap in bytes after a full blocking collection (text: DM numbers are floats)
//   rm_turf_census(z)                      -> awake turfs of a level: own values, vars lists, var names, value kinds
//   rm_now_ms()                            -> milliseconds since the server started (fine-grained, for timings)
//   rm_heap_info()                         -> the heap after a full collection: total, heap size, fragmentation, generations
//   rm_area_sets(trim)                     -> the areas' turf sets and the turf ref table (and trims the sets)
//   rm_gc_compact()                        -> one full compacting collection now (Regions.dm, after the first join): its ms
// The others are for tests and measurements: rm_tiles_wake_cost, rm_heap, rm_heap_info, rm_turf_census, rm_now_ms.
// RM_COMPACT_TILES=0 in the server's environment turns sleeping off (rm_tiles_sleep only counts).
using System.Linq;
using System.Runtime;
using OpenDreamRuntime.Map;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmTiles {
    private static readonly bool On = Environment.GetEnvironmentVariable("RM_COMPACT_TILES") != "0";
    private static readonly string[] Reasons = ["already", "held", "tag", "varslist", "values", "lists", "contents", "things", "full", "watched"];
    private static readonly long[] BoxReasons = new long[10];   // rm_tiles_sleep_box's, never read

    private static bool Box(NativeProc.Bundle bundle, out int x0, out int y0, out int x1, out int y1, out int z) {
        x0 = y0 = x1 = y1 = z = 0;
        return bundle.GetArgument(0, "x0").TryGetValueAsInteger(out x0) && bundle.GetArgument(1, "y0").TryGetValueAsInteger(out y0) &&
               bundle.GetArgument(2, "x1").TryGetValueAsInteger(out x1) && bundle.GetArgument(3, "y1").TryGetValueAsInteger(out y1) &&
               bundle.GetArgument(4, "z").TryGetValueAsInteger(out z);
    }

    [DreamProc("rm_tiles_sleep")]
    [DreamProcParameter("x0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("x1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("dry", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_tiles_sleep(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!Box(bundle, out var x0, out var y0, out var x1, out var y1, out var z)) return DreamValue.Null;
        var dry = !On || bundle.GetArgument(5, "dry").IsTruthy();
        var reasons = new long[10];
        var n = ((DreamMapManager)bundle.MapManager).RmSleep(z, x0, y0, x1, y1, dry, reasons);
        return new DreamValue($"slept={n}|" + string.Join("|", Reasons.Select((r, i) => $"{r}={reasons[i]}")));
    }

    [DreamProc("rm_tiles_sleep_box")]
    [DreamProcParameter("x0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("x1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_tiles_sleep_box(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!On || !Box(bundle, out var x0, out var y0, out var x1, out var y1, out var z)) return new DreamValue(0);
        return new DreamValue(((DreamMapManager)bundle.MapManager).RmSleep(z, x0, y0, x1, y1, false, BoxReasons));
    }

    [DreamProc("rm_tiles_wake")]
    [DreamProcParameter("x0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("x1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_tiles_wake(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!Box(bundle, out var x0, out var y0, out var x1, out var y1, out var z)) return DreamValue.Null;
        return new DreamValue(((DreamMapManager)bundle.MapManager).RmWakeBox(z, x0, y0, x1, y1));
    }

    // rm_tiles_wake, measured: "woken=N|allocated=B" (bytes allocated on this thread while waking: what the awake tiles take)
    [DreamProc("rm_tiles_wake_cost")]
    [DreamProcParameter("x0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("x1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_tiles_wake_cost(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!Box(bundle, out var x0, out var y0, out var x1, out var y1, out var z)) return DreamValue.Null;
        var before = GC.GetAllocatedBytesForCurrentThread();
        var n = ((DreamMapManager)bundle.MapManager).RmWakeBox(z, x0, y0, x1, y1);
        var after = GC.GetAllocatedBytesForCurrentThread();
        return new DreamValue($"woken={n}|allocated={after - before}");
    }

    [DreamProc("rm_tiles_count")]
    [DreamProcParameter("x0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("x1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_tiles_count(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!Box(bundle, out var x0, out var y0, out var x1, out var y1, out var z)) return DreamValue.Null;
        return new DreamValue(((DreamMapManager)bundle.MapManager).RmCountSleeping(z, x0, y0, x1, y1));
    }

    [DreamProc("rm_tiles_stats")]
    public static DreamValue NativeProc_rm_tiles_stats(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var m = (DreamMapManager)bundle.MapManager;
        return new DreamValue($"sleeping={m.RmSleepingTiles}|blocks={m.RmBlocksHeld}|bytes={m.RmBytes}|woken={m.RmWokenTotal}|slept={m.RmSleptTotal}" +
                              $"|vararrays={m.RmVarArrays}|varentries={m.RmVarEntries}|on={(On ? 1 : 0)}");
    }

    [DreamProc("rm_heap")]
    public static DreamValue NativeProc_rm_heap(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        GCSettings.LargeObjectHeapCompactionMode = GCLargeObjectHeapCompactionMode.CompactOnce;
        GC.Collect(2, GCCollectionMode.Forced, true, true);
        GC.WaitForPendingFinalizers();
        GC.Collect(2, GCCollectionMode.Forced, true, true);
        return new DreamValue(GC.GetTotalMemory(false).ToString());
    }

    // milliseconds since the server started, to a microsecond or so (world.time and RemasterNow are too coarse for this)
    private static readonly System.Diagnostics.Stopwatch Clock = System.Diagnostics.Stopwatch.StartNew();

    [DreamProc("rm_now_ms")]
    public static DreamValue NativeProc_rm_now_ms(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        return new DreamValue((float)Clock.Elapsed.TotalMilliseconds);
    }

    // One full blocking, compacting collection, big objects too: the room a player's join left with the collector handed
    // back (Regions.dm RmJoinCompact, once, as the first player's game appears; load-asleep-1030). Returns its milliseconds.
    [DreamProc("rm_gc_compact")]
    public static DreamValue NativeProc_rm_gc_compact(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var t0 = Clock.Elapsed;
        GCSettings.LargeObjectHeapCompactionMode = GCLargeObjectHeapCompactionMode.CompactOnce;
        GC.Collect(2, GCCollectionMode.Forced, true, true);
        return new DreamValue((float)(Clock.Elapsed - t0).TotalMilliseconds);
    }

    // The managed heap after a full blocking, compacting collection: "total=|heap=|fragmented=|committed=|gen0=..gen4=" in
    // bytes (text): total is GC.GetTotalMemory, heap the GC's heap size, fragmented the free space inside it; the gens
    // are what each generation holds after the collection (gen3 the large objects, gen4 the pinned ones).
    [DreamProc("rm_heap_info")]
    public static DreamValue NativeProc_rm_heap_info(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        GCSettings.LargeObjectHeapCompactionMode = GCLargeObjectHeapCompactionMode.CompactOnce;
        GC.Collect(2, GCCollectionMode.Forced, true, true);
        GC.WaitForPendingFinalizers();
        GC.Collect(2, GCCollectionMode.Forced, true, true);
        var info = GC.GetGCMemoryInfo(GCKind.FullBlocking);
        var gens = string.Join("|", info.GenerationInfo.ToArray().Select((g, i) => $"gen{i}={g.SizeAfterBytes}"));
        return new DreamValue($"total={GC.GetTotalMemory(false)}|heap={info.HeapSizeBytes}|fragmented={info.FragmentedBytes}|committed={info.TotalCommittedBytes}|{gens}");
    }

    // The engine's per-tile tables that never shrink: every area's turf set (its turfs and its room: a HashSet keeps its
    // size when turfs leave it, and the world's default area held all 4 million turfs while the levels were made) and
    // the turf ref table. With trim, each set is trimmed to its turfs (HashSet.TrimExcess). Returns
    // "areas=|turfs=|room=|set bytes=|ref slots=|ref room=" (set bytes: 20 B a place, a bucket and an entry).
    [DreamProc("rm_area_sets")]
    [DreamProcParameter("trim", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_area_sets(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var trim = bundle.GetArgument(0, "trim").IsTruthy();
        long areas = 0, turfs = 0, room = 0;
        foreach (var o in bundle.RefManager.EnumerateType(RefType.DreamObjectArea)) {
            if (o is not DreamObjectArea a) continue;
            areas++;
            if (trim) a._rmTurfs.TrimExcess();
            turfs += a._rmTurfs.Count;
            room += a._rmTurfs.Capacity;
        }
        var refs = bundle.RefManager;
        return new DreamValue($"areas={areas}|turfs={turfs}|room={room}|set bytes={room * 20}|ref slots={refs.RmTurfSlots}|ref room={refs.RmTurfSlotCapacity}");
    }

    [DreamProc("rm_turf_census")]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_turf_census(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "z").TryGetValueAsInteger(out var z)) return DreamValue.Null;
        var map = bundle.MapManager;
        long turfs = 0, asleep = 0, withVars = 0, vars = 0, varsLists = 0, things = 0, extras = 0;
        var names = new Dictionary<string, long>();
        var kinds = new Dictionary<string, long>();
        var reasons = new long[10];
        for (var y = 1; y <= map.Size.Y; y++) {
            for (var x = 1; x <= map.Size.X; x++) {
                turfs++;
                if (map is DreamMapManager dm && dm.RmCountSleeping(z, x, y, x, y) > 0) {
                    asleep++;
                    continue;
                }
                if (!map.TryGetCellAt((x, y), z, out var cell)) continue;
                var t = cell.Turf;
                if (cell.Movables.Count > 0) things++;
                if (t.RmHasVarsList) varsLists++;
                extras += t.RmExtras();
                var n = t.RmOwnVarCount;
                if (n > 0) {
                    withVars++;
                    vars += n;
                    foreach (var kv in t.RmOwnVars()) {
                        names[kv.Key] = names.GetValueOrDefault(kv.Key) + 1;
                        var k = kv.Value.Type.ToString();
                        kinds[k] = kinds.GetValueOrDefault(k) + 1;
                    }
                }
                var why = cell.Movables.Count > 0 ? 7 : t.RmSleepBlock();
                reasons[why]++;
            }
        }
        var top = string.Join(",", names.OrderByDescending(p => p.Value).Take(40).Select(p => $"{p.Key}:{p.Value}"));
        var kindText = string.Join(",", kinds.Select(p => $"{p.Key}:{p.Value}"));
        return new DreamValue($"z={z}|turfs={turfs}|asleep={asleep}|with own vars={withVars}|own vars={vars}|vars lists={varsLists}|with things={things}" +
                              $"|lazy lists={extras}|could sleep={reasons[0]}|held={reasons[1]}|tag={reasons[2]}|varslist={reasons[3]}|values={reasons[4]}|lists={reasons[5]}|contents={reasons[6]}" +
                              $"|kinds={kindText}|names={top}");
    }
}
