// The reach map (navigation plan N1 stage 1, planning/NAVIGATION_PLAN_2026-10-27.md; native version 12): which tiles of a
// flat level (every level but the Sky layer's: ground, underground, hell) a walking unit could get to through the ground
// at all, so a route search that can't find a way is answered without one. The owner's rule (10-27): the map may only
// ever be too hopeful. A tile counts as blocked here only where the route search (RmPath.cs, RmWalk.cs) would call it
// blocked for every unit it answers for, from the tile alone: the unit-free half of RmWalkRules.Walkable, in its order
// (density; the stairs icon, unless it is the goal; a wall walk is open; Chasm or Sky stops a dense walker; GoodGrass stops
// the unholy). Everything on a tile (units, doors, furniture, beasts' feet) is left out: open. So "no" from the map is
// always the search's "no"; "maybe" costs the search, as before. Version 25: deep water a swimmer may cross (RmSwim.cs)
// is a kind of its own, open here for every class; the route map and the battle field read it themselves.
// Areas: 8-connected open tiles (the search steps diagonally past corners on these levels), per level and per class
// (0 walkers, 1 the unholy, made from the kinds when first asked), kept as a label per tile and a union-find over labels.
// Kept current by RmVer's hooks (every DM write to a turf, a turf replaced, a turf's look set: RmVer.cs): a tile that
// opens joins its open neighbours' areas at once (never late, or a "no" would be wrong); a tile that shuts only leaves
// the labels over-joined (still hopeful) and marks them for a fresh labelling (rm_reach_tick, at most every
// RM_REACH_RELABEL_S seconds, 300 by default).
// Built once the world has loaded and before its tiles sleep (Regions.dm): a level with a sleeping tile is not read (that
// would wake it) and stays unknown. A map grown since (world.maxx, maxy) answers unknown.
//   rm_reach_build(stairs, monsters, sky)  levels built (a number); the stairs icon, /mob/Monsters and the Sky layer's z
//   rm_reach(M, goal, reach)               1 maybe, 0 no way through the ground at all, null not known
//   rm_reach_tick()                        a fresh labelling of one level and class when due: its ms, or 0
//   rm_reach_stats()                       "on=..|levels=..|..." for logs
//   rm_reach_audit(z)                      tests: the kept map against one read fresh from the tiles (wakes them):
//                                          "tiles=..|kind_diff=..|split=..|..."; kind_diff and split must be 0
//   rm_reach_off()                         tests: off (every answer null) until built again
// RM_REACH=0 in the server's environment: never built (rm_reach_build answers 0).
using System.Diagnostics;
using OpenDreamRuntime.Map;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using Robust.Shared.Maths;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmReach {
    private static readonly bool Disabled = System.Environment.GetEnvironmentVariable("RM_REACH") == "0";
    private static readonly long RelabelGapMs = (long.TryParse(System.Environment.GetEnvironmentVariable("RM_REACH_RELABEL_S"), out var s) ? s : 300) * 1000;
    public static bool On { get; private set; }

    private const byte Open = 0, Dense = 1, Stairs = 2, Drop = 3, Holy = 4;
    internal const byte WaterKind = 5;   // version 25: deep water (RmSwim.Water), open here (a swimmer may cross it: hopeful)
    private const int MaxReach = 64;   // a bigger reach is answered "not known" (the box would be large)
    private static readonly DreamValue ChasmS = new("Chasm"), SkyS = new("Sky"), GoodGrassS = new("GoodGrass"), Svartalfar = new("Svartalfar"), Demon = new("Demon");

    private sealed class Areas {
        public int[] Label = System.Array.Empty<int>();    // per tile: its area, or -1 blocked for this class
        public int[] Parent = System.Array.Empty<int>();   // union-find over areas
        public int Count;
        public bool Dirty;                                 // a tile shut since the labelling: some areas may be over-joined
        public long LabelledAt;
    }

    private sealed class Level {
        public byte[] Kind = System.Array.Empty<byte>();
        public ulong[] Marked = System.Array.Empty<ulong>();   // a bit a tile: changed since the last Flush, to be read again (64 to a word, 10-31)
        public readonly Areas?[] Cls = new Areas?[2];
    }

    private static readonly System.Collections.Generic.List<int> Pending = new();   // marked tiles: ((z - 1) * h + y) * w + x

    private static IDreamMapManager? _map;
    private static Level?[] _levels = System.Array.Empty<Level?>();
    private static int _w, _h;
    private static DreamValue _stairs;
    private static TreeEntry? _monsters;
    private static readonly Stopwatch Clock = Stopwatch.StartNew();
    private static long _buildMs, _relabels, _relabelMs, _opened, _shut, _queries, _no, _yes, _unknown;

    private static bool Blocked(byte kind, int cls) => kind == Dense || kind == Stairs || kind == Drop || (cls == 1 && kind == Holy);

    // The unit-free half of RmWalkRules.Walkable for tile t, in its order.
    // A tile's kind, asleep (read from its record, waking nothing: load-asleep) or awake. x, y, z from 1.
    private static byte KindAt(int x, int y, int z) {
        if (_map is DreamMapManager dm && dm.RmPeek(x, y, z, out var view)) return KindOf(view);
        return _map!.TryGetTurfAt(new Vector2i(x, y), z, out var t) ? KindOf(t) : Dense;
    }

    // KindOf for a sleeping tile: the same reads, from its record.
    private static byte KindOf(in DreamMapManager.RmTileView t) {
        if (t.IsDense) return RmSwim.Water(t) ? WaterKind : Dense;
        if (VarEquals(t, "icon", _stairs)) return Stairs;
        if (Truthy(t, "remaster_wallwalk")) return Open;
        if (VarEquals(t, "icon_state", ChasmS) || VarEquals(t, "icon_state", SkyS)) return Drop;
        if (VarEquals(t, "icon_state", GoodGrassS)) return Holy;
        return Open;
    }

    internal static bool Truthy(in DreamMapManager.RmTileView t, string name) => t.TryGetVar(name, out var v) && v.IsTruthy();

    internal static bool VarEquals(in DreamMapManager.RmTileView t, string name, DreamValue other) =>
        DMOpcodeHandlers.IsEqual(t.TryGetVar(name, out var v) ? v : DreamValue.Null, other);

    private static byte KindOf(DreamObjectTurf t) {
        if (t.IsDense) return RmSwim.Water(t) ? WaterKind : Dense;
        if (RmNative.VarEquals(t, "icon", _stairs)) return Stairs;
        if (RmNative.Truthy(t, "remaster_wallwalk")) return Open;   // room for two units (WalkRoom): it depends on what stands there
        if (RmNative.VarEquals(t, "icon_state", ChasmS) || RmNative.VarEquals(t, "icon_state", SkyS)) return Drop;
        if (RmNative.VarEquals(t, "icon_state", GoodGrassS)) return Holy;
        return Open;
    }

    private static int Find(int[] parent, int a) {
        while (parent[a] != a) {
            parent[a] = parent[parent[a]];
            a = parent[a];
        }
        return a;
    }

    // The areas of class cls on level l, labelled from its kinds (no tile is read).
    private static Areas Label(Level l, int cls) {
        var n = _w * _h;
        var a = l.Cls[cls] ?? new Areas();
        if (a.Label.Length != n) a.Label = new int[n];
        var queue = new int[n];   // made for this labelling only: it was kept between them, 4 MB a level (load-asleep-1030, 10-31)
        var label = a.Label;
        var kind = l.Kind;
        for (var i = 0; i < n; i++) label[i] = Blocked(kind[i], cls) ? -1 : -2;   // -2: open, not labelled yet
        var count = 0;
        for (var i = 0; i < n; i++) {
            if (label[i] != -2) continue;
            var id = count++;
            label[i] = id;
            int head = 0, tail = 0;
            queue[tail++] = i;
            while (head < tail) {
                var c = queue[head++];
                int cx = c % _w, cy = c / _w;
                for (var dy = -1; dy <= 1; dy++) {
                    var ny = cy + dy;
                    if (ny < 0 || ny >= _h) continue;
                    for (var dx = -1; dx <= 1; dx++) {
                        var nx = cx + dx;
                        if (nx < 0 || nx >= _w || (dx == 0 && dy == 0)) continue;
                        var j = ny * _w + nx;
                        if (label[j] != -2) continue;
                        label[j] = id;
                        queue[tail++] = j;
                    }
                }
            }
        }
        a.Parent = new int[System.Math.Max(16, count + count / 4)];
        for (var i = 0; i < a.Parent.Length; i++) a.Parent[i] = i;
        a.Count = count;
        a.Dirty = false;
        a.LabelledAt = Clock.ElapsedMilliseconds;
        l.Cls[cls] = a;
        return a;
    }

    private static Areas AreasOf(Level l, int cls) => l.Cls[cls] ?? Label(l, cls);

    // Tile i opened for class a: it joins every open neighbour's area (a new one if none).
    private static void Opened(Areas a, int i) {
        int cx = i % _w, cy = i / _w;
        var root = -1;
        for (var dy = -1; dy <= 1; dy++) {
            var ny = cy + dy;
            if (ny < 0 || ny >= _h) continue;
            for (var dx = -1; dx <= 1; dx++) {
                var nx = cx + dx;
                if (nx < 0 || nx >= _w || (dx == 0 && dy == 0)) continue;
                var lab = a.Label[ny * _w + nx];
                if (lab < 0) continue;
                var r = Find(a.Parent, lab);
                if (root < 0) root = r;
                else if (r != root) a.Parent[r] = root;
            }
        }
        if (root < 0) {
            if (a.Count >= a.Parent.Length) {
                var grown = new int[a.Parent.Length * 2];
                System.Array.Copy(a.Parent, grown, a.Parent.Length);
                for (var k = a.Parent.Length; k < grown.Length; k++) grown[k] = k;
                a.Parent = grown;
            }
            root = a.Count++;
        }
        a.Label[i] = root;
    }

    // Called by RmVer for every DM write to a turf, a turf replaced and a turf's look set. The tile is only marked here and
    // read again before the map's next answer (Flush): some hooks come before the change is whole (a turf replaced gets its
    // new look after the hook, DreamMapManager.SetTurf; a look set is told before it is set, AtomManager.SetAtomAppearance),
    // and a kind read then would be the old one: a tile that opened could stay shut, and a "no" go wrong.
    public static void TurfChanged(DreamObjectTurf t) {
        var z = t.Z;
        if (z < 1 || z > _levels.Length) return;
        var l = _levels[z - 1];
        if (l == null) return;
        int x = t.X - 1, y = t.Y - 1;
        if (x < 0 || y < 0 || x >= _w || y >= _h) return;
        var i = y * _w + x;
        var bit = 1UL << (i & 63);
        if ((l.Marked[i >> 6] & bit) != 0) return;
        l.Marked[i >> 6] |= bit;   // the main thread only, as Pending
        Pending.Add(((z - 1) * _h + y) * _w + x);
    }

    // Every marked tile read again, now that the changes are whole. Before every answer, tick and audit.
    private static void Flush() {
        if (Pending.Count == 0) return;
        var plane = _w * _h;
        foreach (var p in Pending) {
            var z = p / plane + 1;
            var i = p % plane;
            var l = _levels[z - 1]!;
            l.Marked[i >> 6] &= ~(1UL << (i & 63));
            Apply(l, i, KindAt(i % _w + 1, i / _w + 1, z));   // asleep since it changed: read from its record
        }
        Pending.Clear();
    }

    private static void Apply(Level l, int i, byte now) {
        var was = l.Kind[i];
        if (was == now) return;
        l.Kind[i] = now;
        for (var cls = 0; cls < 2; cls++) {
            var a = l.Cls[cls];
            if (a == null) continue;
            bool before = Blocked(was, cls), after = Blocked(now, cls);
            if (before && !after) {
                Opened(a, i);
                _opened++;
            } else if (!before && after) {
                a.Label[i] = -1;
                a.Dirty = true;
                _shut++;
            }
        }
    }

    // The battle ways (RmField.cs): level z's tile kinds as kept here (marked tiles read again first), or null (off, the
    // level not known, the map grown since); w the map's width.
    internal static byte[]? KindsFor(int z, out int w) {
        w = _w;
        if (!On || _map == null) return null;
        var size = _map.Size;
        if (size.X != _w || size.Y != _h || z < 1 || z > _levels.Length || _levels[z - 1] is not { } l) return null;
        Flush();
        return l.Kind;
    }

    internal static bool BlockedFor(byte kind, int cls) => Blocked(kind, cls);

    private static int Dist(DreamObjectTurf a, DreamObjectTurf b) => a == b ? -1 : System.Math.Max(System.Math.Abs(b.X - a.X), System.Math.Abs(b.Y - a.Y));

    [DreamProc("rm_reach_build")]
    [DreamProcParameter("stairs")]
    [DreamProcParameter("monsters", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("sky", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_reach_build(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (Disabled || !bundle.GetArgument(1, "monsters").TryGetValueAsType(out var monsters)) return new DreamValue(0);
        bundle.GetArgument(2, "sky").TryGetValueAsInteger(out var sky);
        On = false;
        _stairs = bundle.GetArgument(0, "stairs");
        _monsters = monsters;
        _map = bundle.MapManager;
        var t0 = Clock.ElapsedMilliseconds;
        var size = _map.Size;
        _w = size.X;
        _h = size.Y;
        _levels = new Level?[_map.Levels];
        Pending.Clear();
        var built = 0;
        for (var z = 1; z <= _levels.Length; z++) {
            if (z == sky) continue;
            var l = new Level { Kind = new byte[_w * _h], Marked = new ulong[(_w * _h + 63) / 64] };
            for (var y = 0; y < _h; y++)
                for (var x = 0; x < _w; x++)
                    l.Kind[y * _w + x] = KindAt(x + 1, y + 1, z);
            _levels[z - 1] = l;
            Label(l, 0);
            built++;
        }
        _buildMs = Clock.ElapsedMilliseconds - t0;
        On = built > 0;
        return new DreamValue(built);
    }

    [DreamProc("rm_reach")]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("goal", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("reach", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_reach(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!On) return DreamValue.Null;
        Flush();
        _queries++;
        var r = Reach(bundle);
        if (r == null) _unknown++;
        else if (r == 0) _no++;
        else _yes++;
        return r == null ? DreamValue.Null : new DreamValue(r.Value);
    }

    private static int? Reach(NativeProc.Bundle bundle) {
        if (!bundle.GetArgument(0, "M").TryGetValueAsDreamObject<DreamObjectMovable>(out var m) || m.Deleted) return null;
        if (m.Loc is not DreamObjectTurf start) return null;
        if (!bundle.GetArgument(1, "goal").TryGetValueAsDreamObject<DreamObjectTurf>(out var goal)) return null;
        if (!bundle.GetArgument(2, "reach").TryGetValueAsInteger(out var reach) || reach < 0 || reach > MaxReach) return null;
        if (_monsters == null || !m.IsSubtypeOf(_monsters)) return null;
        if (!RmNative.Truthy(m, "density") || RmNative.Truthy(m, "Flying")) return null;   // flyers and the non-dense: the search
        var size = _map!.Size;
        if (size.X != _w || size.Y != _h) return null;   // the map grew since the build
        var z = start.Z;
        if (z < 1 || z > _levels.Length || _levels[z - 1] is not { } l) return null;
        if (Dist(start, goal) <= reach) return 1;          // where it stands is in reach: an empty route
        var cls = RmNative.Truthy(m, "Infects") || RmNative.Truthy(m, "Undead") || RmNative.Truthy(m, "Unholy") ||
                  RmNative.VarEquals(m, "Race", Svartalfar) || RmNative.VarEquals(m, "Race", Demon) ? 1 : 0;
        var a = AreasOf(l, cls);
        // the areas it can step into: its own tile's, else those of the open tiles round it
        int sx = start.X - 1, sy = start.Y - 1;
        if (sx < 0 || sy < 0 || sx >= _w || sy >= _h) return null;
        System.Span<int> roots = stackalloc int[9];
        var nr = 0;
        var si = sy * _w + sx;
        if (a.Label[si] >= 0) roots[nr++] = Find(a.Parent, a.Label[si]);
        else {
            for (var dy = -1; dy <= 1; dy++)
                for (var dx = -1; dx <= 1; dx++) {
                    int nx = sx + dx, ny = sy + dy;
                    if ((dx == 0 && dy == 0) || nx < 0 || ny < 0 || nx >= _w || ny >= _h) continue;
                    var lab = a.Label[ny * _w + nx];
                    if (lab >= 0) roots[nr++] = Find(a.Parent, lab);
                }
        }
        if (nr == 0) return 0;   // shut in where it stands
        // every tile within reach of the goal's x, y on its own level (the search's Dist ignores the level)
        int x0 = System.Math.Max(0, goal.X - 1 - reach), x1 = System.Math.Min(_w - 1, goal.X - 1 + reach);
        int y0 = System.Math.Max(0, goal.Y - 1 - reach), y1 = System.Math.Min(_h - 1, goal.Y - 1 + reach);
        for (var y = y0; y <= y1; y++)
            for (var x = x0; x <= x1; x++) {
                var lab = a.Label[y * _w + x];
                if (lab >= 0 && In(roots, nr, Find(a.Parent, lab))) return 1;
            }
        // the goal itself, stairs: walkable as the goal (RmWalk: "stairs && t != goal"), from a tile beside it
        if (goal.Z == z && goal.X >= 1 && goal.Y >= 1 && goal.X <= _w && goal.Y <= _h && l.Kind[(goal.Y - 1) * _w + goal.X - 1] == Stairs) {
            if (System.Math.Max(System.Math.Abs(goal.X - start.X), System.Math.Abs(goal.Y - start.Y)) <= 1) return 1;
            for (var dy = -1; dy <= 1; dy++)
                for (var dx = -1; dx <= 1; dx++) {
                    int nx = goal.X - 1 + dx, ny = goal.Y - 1 + dy;
                    if ((dx == 0 && dy == 0) || nx < 0 || ny < 0 || nx >= _w || ny >= _h) continue;
                    var lab = a.Label[ny * _w + nx];
                    if (lab >= 0 && In(roots, nr, Find(a.Parent, lab))) return 1;
                }
        }
        return 0;
    }

    private static bool In(System.Span<int> roots, int n, int r) {
        for (var i = 0; i < n; i++) if (roots[i] == r) return true;
        return false;
    }

    [DreamProc("rm_reach_tick")]
    public static DreamValue NativeProc_rm_reach_tick(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!On) return new DreamValue(0);
        Flush();
        var now = Clock.ElapsedMilliseconds;
        foreach (var l in _levels) {
            if (l == null) continue;
            for (var cls = 0; cls < 2; cls++) {
                var a = l.Cls[cls];
                if (a == null || !a.Dirty || now - a.LabelledAt < RelabelGapMs) continue;
                Label(l, cls);
                var ms = Clock.ElapsedMilliseconds - now;
                _relabels++;
                _relabelMs += ms;
                return new DreamValue(System.Math.Max(1, ms));
            }
        }
        return new DreamValue(0);
    }

    [DreamProc("rm_reach_stats")]
    public static DreamValue NativeProc_rm_reach_stats(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var levels = new System.Collections.Generic.List<string>();
        long bytes = 0;
        for (var z = 1; z <= _levels.Length; z++) {
            if (_levels[z - 1] is not { } l) continue;
            levels.Add(z.ToString());
            bytes += l.Kind.Length;
            foreach (var a in l.Cls) if (a != null) bytes += 4L * (a.Label.Length + a.Parent.Length);
        }
        var areas = string.Join(",", System.Linq.Enumerable.Select(System.Linq.Enumerable.Where(_levels, l => l != null), l => l!.Cls[0]?.Count ?? 0));
        return new DreamValue($"on={(On ? 1 : 0)}|levels={(levels.Count > 0 ? string.Join(",", levels) : "none")}|size={_w}x{_h}|areas={areas}|bytes={bytes}|build_ms={_buildMs}|" +
                              $"queries={_queries}|no={_no}|maybe={_yes}|unknown={_unknown}|opened={_opened}|shut={_shut}|relabels={_relabels}|relabel_ms={_relabelMs}");
    }

    [DreamProc("rm_reach_audit")]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_reach_audit(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!On || !bundle.GetArgument(0, "z").TryGetValueAsInteger(out var z) || z < 1 || z > _levels.Length || _levels[z - 1] is not { } kept) return DreamValue.Null;
        Flush();
        var n = _w * _h;
        var fresh = new Level { Kind = new byte[n] };
        long kindDiff = 0;
        var first = "";
        for (var y = 0; y < _h; y++)
            for (var x = 0; x < _w; x++) {
                var i = y * _w + x;
                fresh.Kind[i] = KindAt(x + 1, y + 1, z);
                if (fresh.Kind[i] == kept.Kind[i]) continue;
                if (kindDiff++ == 0) first = $"|first={x + 1},{y + 1},{z} kept {kept.Kind[i]} fresh {fresh.Kind[i]}";
            }
        // hopeful: tiles one fresh area joins must share one kept area (the kept map may join more, never fewer)
        long split = 0;
        var keptAreas = 0;
        var freshAreas = 0;
        for (var cls = 0; cls < 2; cls++) {
            var ka = kept.Cls[cls];
            if (ka == null) continue;
            var fa = Label(fresh, cls);
            var seen = new int[fa.Count];
            System.Array.Fill(seen, -1);
            for (var i = 0; i < n; i++) {
                var f = fa.Label[i];
                if (f < 0) continue;
                var k = ka.Label[i] < 0 ? -1 : Find(ka.Parent, ka.Label[i]);
                if (k < 0) { split++; continue; }
                if (seen[f] < 0) seen[f] = k;
                else if (seen[f] != k) split++;
            }
            if (cls == 0) {
                freshAreas = fa.Count;
                var roots = new System.Collections.Generic.HashSet<int>();
                for (var i = 0; i < ka.Count; i++) roots.Add(Find(ka.Parent, i));
                keptAreas = roots.Count;
            }
        }
        return new DreamValue($"tiles={n}|kind_diff={kindDiff}|split={split}|kept_areas={keptAreas}|fresh_areas={freshAreas}{first}");
    }

    [DreamProc("rm_reach_off")]
    public static DreamValue NativeProc_rm_reach_off(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        On = false;
        return DreamValue.Null;
    }
}
