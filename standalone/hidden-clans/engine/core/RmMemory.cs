// What the server's memory goes to (planning/ENGINE_PLAN.md, memory), for tests: rm_memory_report() returns one text
// line of "name=value" pairs: objects of each kind (the engine's ref buckets), how many of them hold their own variables
// and how many those are, list elements, the map's levels and cells, the managed heap and the process, and the bytes one
// of each small per-tile structure takes (measured by allocating a thousand). Bound only where a test declares it.
using System.Diagnostics;
using System.Reflection;
using Robust.Shared.GameObjects;
using Robust.Shared.IoC;
using OpenDreamRuntime.Map;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmMemory {
    private static readonly FieldInfo? VariablesField = typeof(DreamObject).GetField("Variables", BindingFlags.Instance | BindingFlags.NonPublic);

    private static long Measure(Func<object> make) {
        var keep = new object[1000];
        var before = GC.GetAllocatedBytesForCurrentThread();
        for (var i = 0; i < keep.Length; i++) keep[i] = make();
        var after = GC.GetAllocatedBytesForCurrentThread();
        GC.KeepAlive(keep);
        return (after - before) / keep.Length;
    }

    [DreamProc("rm_memory_report")]
    public static DreamValue NativeProc_rm_memory_report(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var refs = bundle.RefManager;
        var parts = new List<string>();
        foreach (var type in new[] { RefType.DreamObjectTurf, RefType.DreamObjectMob, RefType.DreamObjectMovable, RefType.DreamObjectArea,
                     RefType.DreamObjectDatum, RefType.DreamObjectList, RefType.DreamObjectAssocList, RefType.DreamObjectImage, RefType.DreamObjectSavefile }) {
            long objects = 0, withVars = 0, vars = 0, elements = 0;
            foreach (var o in refs.EnumerateType(type)) {
                objects++;
                if (VariablesField?.GetValue(o) is Dictionary<string, DreamValue> v) {
                    withVars++;
                    vars += v.Count;
                }
                if (o is DreamList l && o is not TurfContentsList) elements += l.GetLength();
            }
            var name = type.ToString().Replace("DreamObject", "").ToLowerInvariant();
            parts.Add($"{name}={objects}");
            parts.Add($"{name} with own vars={withVars}");
            parts.Add($"{name} own vars={vars}");
            if (elements > 0) parts.Add($"{name} elements={elements}");
        }
        var mapManager = bundle.MapManager;
        long cells = 0, cellsWithMovables = 0;
        for (var z = 1; z <= mapManager.Levels; z++) {
            for (var x = 1; x <= mapManager.Size.X; x++) {
                for (var y = 1; y <= mapManager.Size.Y; y++) {
                    if (mapManager is DreamMapManager rmMap && rmMap.RmAsleep(x, y, z)) {   // a sleeping tile: no things, and reading it would wake it
                        cells++;
                        continue;
                    }
                    if (!mapManager.TryGetCellAt(new Robust.Shared.Maths.Vector2i(x, y), z, out var cell)) continue;
                    cells++;
                    if (cell.Movables.Count > 0) cellsWithMovables++;
                }
            }
        }
        parts.Add($"cells={cells}");
        parts.Add($"cells with movables={cellsWithMovables}");
        parts.Add($"bytes a movables list={Measure(() => new List<DreamObjectMovable>())}");
        parts.Add($"bytes a vars table of 4={Measure(() => new Dictionary<string, DreamValue>(4) { ["a"] = DreamValue.Null, ["b"] = DreamValue.Null, ["c"] = DreamValue.Null, ["d"] = DreamValue.Null })}");
        // sleeping procs (each sleep() or spawn() waiting, with its whole proc state) and the engine's entities (one a movable)
        var scheduler = IoCManager.Resolve<ProcScheduler>();
        var tickers = typeof(ProcScheduler).GetField("_tickers", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(scheduler);
        var waiting = tickers?.GetType().GetProperty("Count")?.GetValue(tickers);
        parts.Add($"procs waiting={waiting ?? "?"}");
        parts.Add($"entities={IoCManager.Resolve<IEntityManager>().EntityCount}");
        GC.Collect();
        var info = GC.GetGCMemoryInfo();
        parts.Add($"heap MB={info.HeapSizeBytes / 1048576}");
        parts.Add($"committed MB={info.TotalCommittedBytes / 1048576}");
        using var process = Process.GetCurrentProcess();
        parts.Add($"working set MB={process.WorkingSet64 / 1048576}");
        parts.Add($"private MB={process.PrivateMemorySize64 / 1048576}");
        return new DreamValue(string.Join("|", parts));
    }
}
