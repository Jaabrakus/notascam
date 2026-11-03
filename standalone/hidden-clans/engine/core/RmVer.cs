// Change counters for the 3D view's "send only what changed" (world look, 2026-10-24; game/Code/Remastered/View3D.dm):
//   rm_chunk_ver(cx, cy, z)  a number that moves whenever a turf in 16x16 chunk (cx, cy) of level z has a var written
//                            or is replaced (new /turf on the map); cx = round((x - 1) / 16), cy likewise.
//   rm_chunk_things_ver(cx, cy, z)  (native version 34; load-asleep-1030, 10-31, the owner: "Exact, engine counter") a
//                            number that moves whenever a thing on a turf of that chunk changes: an obj (any movable but a
//                            mob) lying there with any counted change (Bump: a write, a move, a look, animate), an obj
//                            arriving there, and a mob coming onto the map there or leaving it (made, deleted, into or out
//                            of something). A mob's step from tile to tile doesn't move it, so walking units don't. Only what
//                            lies on the turf itself: a change inside a cart lying there doesn't. With rm_chunk_ver: an area's
//                            tiles and what lies on them are as they were (the settlement's progress and room scans).
//   rm_ver(A)                for a movable, a number that moves whenever A, or anything inside it (a sword in a pack on
//                            a unit), has a var written, moves, or has its look changed (overlays, underlays, animate),
//                            and whenever something enters or leaves it. For a turf, its chunk's number. For anything
//                            else, a new number every call (always changed).
// The engine calls Written from DreamObject.SetVariable (every DM var write) and animate(), TurfReplaced from the map's
// set-turf, Moved from DreamObjectMovable.SetLoc and Looked from AtomManager.SetAtomAppearance (build_runtime.py, VER).
// Not seen: a list held in a var changed in place (L += x, L[i] = v), apart from contents, overlays and underlays.
//   rm_ver_state(A)          (native version 31; the owner, 10-31: "record rebuilt per second thats to much") for a
//                            movable, a number that moves as rm_ver's does except for its own steps from tile to tile and
//                            writes of the names rm_ver_state_quiet gives: a unit walking keeps it, so what is worked out
//                            from its state (the HUD's entries and records) holds while it walks. Its coming onto the map
//                            or leaving it (into a cart, a pack) still counts, and anything going into or out of it.
//                            A step is counted once, by the move (a loc written is not also a write), and a look a var
//                            write changes is the write's (a facing written is motion; the same value again, nothing).
//   rm_ver_state_quiet(names) names whose writes are motion, not state (a game's step marks and timers; the needs that
//                            fall every few seconds, read only against thresholds the caller keeps itself).
//   rm_ver_shown(A)          (native version 35; the owner, 10-31: "those rebuilts are high arent they? shouldnt we get
//                            like 100?") for a movable, a number that moves as rm_ver_state's does except for writes of
//                            the names rm_ver_shown_quiet gives: state a game's views don't draw (a unit card's lines, its
//                            order list, combat marks), so what a view works out from a thing (the 3D scene's entries)
//                            holds while only those change. Of ~500 3D entries a second made again at 100 players, ~490
//                            came out the same, their state counter moved by the card's order status and current order.
//   rm_ver_shown_quiet(names) names whose writes are state no view draws (a view that reads one keys it itself).
//   rm_ver_quiet(names)      names (a list, or one) whose writes are not a change: a game's own caches and marks kept on
//                            a thing, worked out from the rest of it. A cache keyed on rm_ver that keeps its answer on the
//                            thing would otherwise never hold, and marks written each send would make every thing look
//                            changed. Returns how many names are quiet. RM_VER_TRACE=1: the names written most on
//                            movables are logged every 10 s (what to make quiet).
// Numbers are kept below 2^24, so DM's numbers hold them exactly; they wrap, which only matters if a chunk took exactly
// 16,777,216 writes between two reads. DM bodies (Native.dm) return a new number every call: always changed.
using System.Linq;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmVer {
    private const int Mask = 0xFFFFFF;

    // chunk counters, [z - 1][cy * _w + cx]; grown (values kept) when a turf past the end is written
    private static int[][] _chunks = [];
    private static int[][] _things = [];   // the things-on-turfs counters, the same shape, grown with _chunks
    private static int _w, _h;
    private static int _fresh;

    public static int NextFresh() => ++_fresh & Mask;

    private static readonly HashSet<string> Quiet = new();
    private static readonly HashSet<string> StateQuiet = new();
    private static readonly HashSet<string> ShownQuiet = new();
    private static readonly Dictionary<string, long>? Trace = Environment.GetEnvironmentVariable("RM_VER_TRACE") == "1" ? new() : null;
    private static DateTime _traceAt = DateTime.UtcNow;

    /// <summary>A DM var write (DreamObject.SetVariable, the VER patch): a quiet name is no change.</summary>
    public static void Written(DreamObject o, string name) {
        if (Quiet.Count > 0 && Quiet.Contains(name)) return;
        // a movable's loc, x, y or z went through SetLoc, and Moved counted it (the engine's own Move() steps by writing
        // loc: counted here too, every step was a change of state; v31, the owner, 10-31)
        if (o is DreamObjectMovable && name is "loc" or "x" or "y" or "z") return;
        if (Trace != null && o is DreamObjectMovable) TraceWrite(name);
        if (StateQuiet.Count > 0 && o is DreamObjectMovable sm && StateQuiet.Contains(name)) {
            Bump(sm);   // a change, but motion: its state stands
            return;
        }
        if (ShownQuiet.Count > 0 && o is DreamObjectMovable hm && ShownQuiet.Contains(name)) {
            Bump(hm);
            BumpState(hm, false);   // a change of state, but none a view draws: its shown counter stands
            return;
        }
        Written(o);
    }

    private static void TraceWrite(string name) {
        Trace![name] = Trace.TryGetValue(name, out var n) ? n + 1 : 1;
        var now = DateTime.UtcNow;
        if ((now - _traceAt).TotalSeconds < 10) return;
        var seconds = (now - _traceAt).TotalSeconds;
        _traceAt = now;
        var top = string.Join(", ", Trace.OrderByDescending(p => p.Value).Take(20).Select(p => $"{p.Key} {p.Value / seconds:0}/s"));
        Logger.GetSawmill("opendream.rmver").Info($"rmver: writes on movables, the most: {top}");
        Trace.Clear();
    }

    public static void Written(DreamObject o) {
        if (o is DreamObjectMovable m) {
            Bump(m);
            BumpState(m);
        }
        else if (o is DreamObjectTurf t) {
            BumpChunk(t.X, t.Y, t.Z);
            if (RmReach.On) RmReach.TurfChanged(t);   // the reach map (RmReach.cs): this tile's kind again
        }
    }

    public static void TurfReplaced(DreamObjectTurf t) {
        BumpChunk(t.X, t.Y, t.Z);
        if (RmReach.On) RmReach.TurfChanged(t);
    }

    // it and what holds it, up to the ground (a loc cycle can't happen; the bound is only a guard)
    public static void Bump(DreamObjectMovable? m) {
        if (m is not null and not DreamObjectMob && m.Loc is DreamObjectTurf on) BumpThings(on);   // an obj lying there changed (or is leaving it)
        for (var i = 0; m != null && i < 16; i++) {
            m.RmChanges++;
            m = m.Loc as DreamObjectMovable;
        }
    }

    // its state and its holders': what holds it has something inside it changed; shown, the shown counters too (v35)
    public static void BumpState(DreamObjectMovable? m) => BumpState(m, true);

    private static void BumpState(DreamObjectMovable? m, bool shown) {
        for (var i = 0; m != null && i < 16; i++) {
            m.RmState++;
            if (shown) m.RmShown++;
            m = m.Loc as DreamObjectMovable;
        }
    }

    // called before the move: Loc is still where it was, so its old holder moves with it
    public static void Moved(DreamObjectMovable m, DreamObjectAtom? to) {
        Bump(m);
        if (to is DreamObjectMovable h) Bump(h);
        // state: what it leaves and what it goes into have their contents changed; it itself only coming onto the map or
        // leaving it (a step from tile to tile is not its state)
        if (m.Loc is DreamObjectMovable from) BumpState(from);
        if (to is DreamObjectMovable into) BumpState(into);
        if ((m.Loc is DreamObjectTurf) != (to is DreamObjectTurf)) BumpState(m);
        // the things on turfs (Bump(m) above counted the turf an obj leaves): the turf an obj, or a mob coming onto the map,
        // arrives on, and the turf a mob leaves the map from (a deletion is SetLoc(null), so Moved(m, null))
        if (to is DreamObjectTurf onto && (m is not DreamObjectMob || m.Loc is not DreamObjectTurf)) BumpThings(onto);
        if (m is DreamObjectMob && m.Loc is DreamObjectTurf left && to is not DreamObjectTurf) BumpThings(left);
    }

    // the object a DM var write is being made on (DreamObject.SetVariable, the VER patch): a look it changes is counted by
    // the write itself (Written: its name's rule, so a facing is motion and the same value no change), not here again
    public static DreamObject? Writing;

    public static void Looked(DreamObject atom) {
        if (atom is DreamObjectMovable m) {
            if (ReferenceEquals(m, Writing)) return;   // the write counts it (look vars are never kept as own vars, so never "the same")
            Bump(m);
            BumpState(m);
        }
        else if (RmReach.On && atom is DreamObjectTurf t) RmReach.TurfChanged(t);   // a look set straight: icon, icon_state
    }

    private static void BumpChunk(int x, int y, int z) {
        if (x < 1 || y < 1 || z < 1) return;
        int cx = (x - 1) >> 4, cy = (y - 1) >> 4;
        if (z > _chunks.Length || cx >= _w || cy >= _h) Grow(Math.Max(z, _chunks.Length), Math.Max(cx + 1, _w), Math.Max(cy + 1, _h));
        _chunks[z - 1][cy * _w + cx]++;
    }

    private static void BumpThings(DreamObjectTurf t) {
        int x = t.X, y = t.Y, z = t.Z;
        if (x < 1 || y < 1 || z < 1) return;
        int cx = (x - 1) >> 4, cy = (y - 1) >> 4;
        if (z > _chunks.Length || cx >= _w || cy >= _h) Grow(Math.Max(z, _chunks.Length), Math.Max(cx + 1, _w), Math.Max(cy + 1, _h));
        _things[z - 1][cy * _w + cx]++;
    }

    private static void Grow(int d, int w, int h) {
        w = Math.Max(w, 64); h = Math.Max(h, 64);
        var grown = new int[d][];
        var things = new int[d][];
        for (var z = 0; z < d; z++) {
            grown[z] = new int[w * h];
            things[z] = new int[w * h];
            if (z >= _chunks.Length) continue;
            for (var cy = 0; cy < _h; cy++) {
                Array.Copy(_chunks[z], cy * _w, grown[z], cy * w, _w);
                Array.Copy(_things[z], cy * _w, things[z], cy * w, _w);
            }
        }
        _chunks = grown; _things = things; _w = w; _h = h;
    }

    public static int ChunkVer(int cx, int cy, int z) {
        if (cx < 0 || cy < 0 || z < 1 || z > _chunks.Length || cx >= _w || cy >= _h) return 0;
        return _chunks[z - 1][cy * _w + cx] & Mask;
    }

    public static int ThingsVer(int cx, int cy, int z) {
        if (cx < 0 || cy < 0 || z < 1 || z > _things.Length || cx >= _w || cy >= _h) return 0;
        return _things[z - 1][cy * _w + cx] & Mask;
    }

    [DreamProc("rm_chunk_things_ver")]
    [DreamProcParameter("cx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("cy", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_chunk_things_ver(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "cx").TryGetValueAsInteger(out var cx) || !bundle.GetArgument(1, "cy").TryGetValueAsInteger(out var cy)
            || !bundle.GetArgument(2, "z").TryGetValueAsInteger(out var z)) return DreamValue.Null;
        return new DreamValue(ThingsVer(cx, cy, z));
    }

    [DreamProc("rm_chunk_ver")]
    [DreamProcParameter("cx", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("cy", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_chunk_ver(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "cx").TryGetValueAsInteger(out var cx) || !bundle.GetArgument(1, "cy").TryGetValueAsInteger(out var cy)
            || !bundle.GetArgument(2, "z").TryGetValueAsInteger(out var z)) return DreamValue.Null;
        return new DreamValue(ChunkVer(cx, cy, z));
    }

    [DreamProc("rm_ver_quiet")]
    [DreamProcParameter("names", Type = DreamValueTypeFlag.DreamObject | DreamValueTypeFlag.String)]
    public static DreamValue NativeProc_rm_ver_quiet(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var names = bundle.GetArgument(0, "names");
        if (names.TryGetValueAsString(out var one)) Quiet.Add(one);
        else if (names.TryGetValueAsDreamList(out var list))
            foreach (var value in list.EnumerateValues())
                if (value.TryGetValueAsString(out var name)) Quiet.Add(name);
        return new DreamValue(Quiet.Count);
    }

    [DreamProc("rm_ver")]
    [DreamProcParameter("A", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_ver(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "A").TryGetValueAsDreamObject<DreamObject>(out var o) || o.Deleted) return DreamValue.Null;
        return o switch {
            DreamObjectMovable m => new DreamValue(m.RmChanges & Mask),
            DreamObjectTurf t => new DreamValue(ChunkVer((t.X - 1) >> 4, (t.Y - 1) >> 4, t.Z)),
            _ => new DreamValue(NextFresh())
        };
    }

    [DreamProc("rm_ver_state")]
    [DreamProcParameter("A", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_ver_state(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "A").TryGetValueAsDreamObject<DreamObject>(out var o) || o.Deleted) return DreamValue.Null;
        return o switch {
            DreamObjectMovable m => new DreamValue(m.RmState & Mask),
            DreamObjectTurf t => new DreamValue(ChunkVer((t.X - 1) >> 4, (t.Y - 1) >> 4, t.Z)),
            _ => new DreamValue(NextFresh())
        };
    }

    [DreamProc("rm_ver_state_quiet")]
    [DreamProcParameter("names", Type = DreamValueTypeFlag.DreamObject | DreamValueTypeFlag.String)]
    public static DreamValue NativeProc_rm_ver_state_quiet(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var names = bundle.GetArgument(0, "names");
        if (names.TryGetValueAsString(out var one)) StateQuiet.Add(one);
        else if (names.TryGetValueAsDreamList(out var list))
            foreach (var value in list.EnumerateValues())
                if (value.TryGetValueAsString(out var name)) StateQuiet.Add(name);
        return new DreamValue(StateQuiet.Count);
    }

    [DreamProc("rm_ver_shown")]
    [DreamProcParameter("A", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_ver_shown(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "A").TryGetValueAsDreamObject<DreamObject>(out var o) || o.Deleted) return DreamValue.Null;
        return o switch {
            DreamObjectMovable m => new DreamValue(m.RmShown & Mask),
            DreamObjectTurf t => new DreamValue(ChunkVer((t.X - 1) >> 4, (t.Y - 1) >> 4, t.Z)),
            _ => new DreamValue(NextFresh())
        };
    }

    [DreamProc("rm_ver_shown_quiet")]
    [DreamProcParameter("names", Type = DreamValueTypeFlag.DreamObject | DreamValueTypeFlag.String)]
    public static DreamValue NativeProc_rm_ver_shown_quiet(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var names = bundle.GetArgument(0, "names");
        if (names.TryGetValueAsString(out var one)) ShownQuiet.Add(one);
        else if (names.TryGetValueAsDreamList(out var list))
            foreach (var value in list.EnumerateValues())
                if (value.TryGetValueAsString(out var name)) ShownQuiet.Add(name);
        return new DreamValue(ShownQuiet.Count);
    }
}
