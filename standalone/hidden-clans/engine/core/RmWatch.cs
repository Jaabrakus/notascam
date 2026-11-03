// RmWatch: which objects had a watched variable written (rm_watch, rm_watch_take). A game pass that waits on a var (a
// parked walk loop on destination, the skill pass on skill values, Bed on Tiredness) asks for just those objects instead
// of polling every unit (server cost, 2026-10-24). DreamObject.SetVariable tells it on every DM var write (src.x =, M.x =,
// vars[x] =, x += ...; the WATCH patch in tools/build_runtime.py), beside RmVer: a name's length is checked against the
// watched lengths first (one shift and AND for most writes), then the watched names. Marks are kept in the order of
// their first write since the last take, each object once. Initial values from a type and the engine's own sets of
// built-in vars aren't DM writes and aren't marked. The DM fallbacks (Remastered/Native.dm) watch nothing: the game
// keeps polling, as it does with RM_WATCH=0.
// Not seen (they don't go through SetVariable): a type's initial values and a new object's var overrides set straight
// (SetVariableValue), animate()'s writes (DMOpcodeHandlers' animate), and what the engine changes itself without a DM
// write: a move's loc, x, y, z and dir, appearance vars an engine call sets. A DM write of any of those (src.dir = 2,
// M.loc = T) does go through SetVariable and is seen.
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using OpenDreamShared.Dream;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmWatch {
    public static bool Active;
    private static ulong _lengths;                  // bit n: a watched name n long (names of 64 or more: bit 63)
    private static readonly Dictionary<string, Marks> Watched = new();

    private sealed class Marks {
        public readonly List<DreamObject> Order = new();
        public readonly HashSet<DreamObject> Seen = new();
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static void Written(DreamObject o, string name) {
        if (!Active) return;
        var n = name.Length;
        if (((_lengths >> (n < 63 ? n : 63)) & 1) == 0) return;
        if (Watched.TryGetValue(name, out var m) && m.Seen.Add(o)) m.Order.Add(o);
    }

    // Is o waiting in a mark list (a watched var written since the last take)? The marks hold the object itself, so a turf
    // marked must not sleep before the take (map memory's sleeping tiles, DreamMapManager.RmTiles.cs, ask this).
    public static bool Holds(DreamObject o) {
        if (!Active) return false;
        foreach (var m in Watched.Values) if (m.Seen.Contains(o)) return true;
        return false;
    }

    [DreamProc("rm_watch")]
    [DreamProcParameter("names", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_watch(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (System.Environment.GetEnvironmentVariable("RM_WATCH") == "0") return new DreamValue(0);   // switched off: the game keeps polling
        if (!bundle.GetArgument(0, "names").TryGetValueAsDreamList(out var list)) return new DreamValue(0);
        foreach (var v in list.GetValues()) {
            if (!v.TryGetValueAsString(out var s) || string.IsNullOrEmpty(s) || Watched.ContainsKey(s)) continue;
            Watched[s] = new Marks();
            _lengths |= 1UL << (s.Length < 63 ? s.Length : 63);
        }
        Active = Watched.Count > 0;
        return new DreamValue(1);
    }

    // The objects whose `name` was written since the last take (not deleted ones), in the order first written; cleared.
    [DreamProc("rm_watch_take")]
    [DreamProcParameter("name", Type = DreamValueTypeFlag.String)]
    public static DreamValue NativeProc_rm_watch_take(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var outList = bundle.ObjectTree.CreateList();
        if (bundle.GetArgument(0, "name").TryGetValueAsString(out var name) && Watched.TryGetValue(name, out var m)) {
            foreach (var o in m.Order) if (!o.Deleted) outList.AddValue(new DreamValue(o));
            m.Order.Clear();
            m.Seen.Clear();
        }
        return new DreamValue(outList);
    }
}
