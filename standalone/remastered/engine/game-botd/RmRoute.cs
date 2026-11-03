// The route map (native version 19; the owner, 10-29: "we want them to go around the mountain we dont want them to stop",
// and a group's shared route, "Yes, group routes"). The route search (RmPath.cs) looks at 512 tiles at most; a way round a
// long ridge is longer than that, so it went to the point nearest the goal (the rock face) and stood there
// (reports/polish-night-1026/group-routes/ridge_check.dm: a minute at the face, never round). This is a map spread out
// from the goal, step by step over the ground (8 ways, as the search steps), as far as a unit asking for it, up to Radius
// tiles round the goal: each tile's steps to the goal. A unit reads its way down the map. One map serves every unit going to
// the same goal (a group's target) for RefreshTicks; it grows only as far as the units asking need.
// The ground as the search sees it (RmWalkRules.Walkable with the goal), but units passed over: they move, and each step's
// own checks meet them (Clip.dm, Orders.dm). Not on the Sky layer (block heights) nor for flyers: null, the search's as before.
// Version 25 (swimming): a deep water tile a swimmer goes into counts RmSwim.Cost steps, as in the search, so the map
// spreads by the least steps first (a queue by steps, not one step at a time); swimmers and those who don't swim have
// maps of their own.
// What the player knows (the owner, 10-29: "if they hit a dead end thats correct if they never been that way before we have
// to use fog of war and what they know"): with known (the level's explored memory, Explore.dm: "cx,cy" -> 16 row bitmasks)
// a tile never explored counts as open; a unit finds out on the way, and its next plan knows. Without it: the ground itself.
// A way ends on a goal tile no other unit stands on (a unit never stops on another's tile, Clip.dm): all of them held, 0, as
// the search said (a village's work trips ask this ~30 times a game second, each a held tree side or store tile).
//   rm_route_map(M, goal, reach, key, now, stop_at, stop_d, stairs, foot, monsters, ground, sky, door, trapdoor, known)
//     M's way to within reach of goal: a list of tiles (ending where it first comes within stop_d of stop_at, when given);
//     0: no way there within the map (M's tile isn't on it once it is spread as far as it goes); null: not known.
//   rm_route_stats()  "maps=..|built_tiles=..|routes=..|none=..|ms=.."
// RM_ROUTE=0: always null.
using System.Collections.Generic;
using System.Diagnostics;
using OpenDreamRuntime.Map;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using Robust.Shared.Maths;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmRoute {
    private static readonly bool Disabled = System.Environment.GetEnvironmentVariable("RM_ROUTE") == "0";
    private const int Radius = 96, Side = 2 * Radius + 1;
    private const float RefreshTicks = 50;
    private const int MaxRoute = 600;
    // NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST, as the route search takes them (RmPath.cs)
    private static readonly (int dx, int dy)[] Steps = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)];
    private static readonly DreamValue Svartalfar = new("Svartalfar"), Demon = new("Demon");

    private sealed class Map {
        public int X0, Y0, W, H, Z, Cls;
        public DreamList? Known;                                // the explored memory, or null: everything known
        public readonly Dictionary<int, int[]?> Rows = new();   // its chunks' rows, read once a map
        public float Built;
        public readonly int[] Dist = new int[Side * Side];     // steps to the goal (so far, until Done); -1 not reached yet
        public readonly bool[] Done = new bool[Side * Side];   // its steps to the goal are final
        public readonly byte[] Walk = new byte[Side * Side];   // 0 not read, 1 open, 2 shut, 3 passed through but not ended on, 4 deep water swum
        public readonly PriorityQueue<int, int> Open = new();  // tiles reached, by steps to the goal
        public bool Swims;
    }

    private static readonly Dictionary<string, Map> Maps = new();
    private static readonly Stopwatch Clock = Stopwatch.StartNew();
    private static long _built, _routes, _none, _ticks;

    [DreamProc("rm_route_map")]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("goal", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("reach", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("key", Type = DreamValueTypeFlag.String)]
    [DreamProcParameter("now", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("stop_at", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("stop_d", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("stairs")]
    [DreamProcParameter("foot", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("monsters", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("ground", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("sky", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("door", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("trapdoor", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("known", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_route_map(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var t0 = Clock.ElapsedTicks;
        try {
            return Route(bundle);
        } finally {
            _ticks += Clock.ElapsedTicks - t0;
        }
    }

    private static DreamValue Route(NativeProc.Bundle bundle) {
        if (Disabled) return DreamValue.Null;
        if (!bundle.GetArgument(0, "M").TryGetValueAsDreamObject<DreamObjectMovable>(out var m) || m.Deleted) return DreamValue.Null;
        if (m.Loc is not DreamObjectTurf start) return DreamValue.Null;
        if (!bundle.GetArgument(1, "goal").TryGetValueAsDreamObject<DreamObjectTurf>(out var goal)) return DreamValue.Null;
        if (!bundle.GetArgument(2, "reach").TryGetValueAsInteger(out var reach)) reach = 0;
        if (!bundle.GetArgument(3, "key").TryGetValueAsString(out var key)) return DreamValue.Null;
        if (!bundle.GetArgument(4, "now").TryGetValueAsFloat(out var now)) return DreamValue.Null;
        bundle.GetArgument(5, "stop_at").TryGetValueAsDreamObject<DreamObjectTurf>(out var stopAt);
        bundle.GetArgument(6, "stop_d").TryGetValueAsInteger(out var stopD);
        bundle.GetArgument(8, "foot").TryGetValueAsType(out var foot);
        bundle.GetArgument(9, "monsters").TryGetValueAsType(out var monsters);
        bundle.GetArgument(10, "ground").TryGetValueAsInteger(out var ground);
        bundle.GetArgument(11, "sky").TryGetValueAsInteger(out var sky);
        bundle.GetArgument(12, "door").TryGetValueAsType(out var door);
        bundle.GetArgument(13, "trapdoor").TryGetValueAsType(out var trapdoor);
        bundle.GetArgument(14, "known").TryGetValueAsDreamList(out var known);
        if (monsters == null || !m.IsSubtypeOf(monsters)) return DreamValue.Null;
        if (start.Z != goal.Z || start.Z == sky || !RmNative.Truthy(m, "density") || RmNative.Truthy(m, "Flying")) return DreamValue.Null;
        if (System.Math.Max(System.Math.Abs(start.X - goal.X), System.Math.Abs(start.Y - goal.Y)) > Radius) return DreamValue.Null;   // past the map
        var cls = RmNative.Truthy(m, "Infects") || RmNative.Truthy(m, "Undead") || RmNative.Truthy(m, "Unholy") ||
                  RmNative.VarEquals(m, "Race", Svartalfar) || RmNative.VarEquals(m, "Race", Demon) ? 1 : 0;   // holy ground
        var swims = RmSwim.Swims(m, monsters);
        var mapKey = $"{key}|{goal.X},{goal.Y},{goal.Z}|{reach}|{cls}|{(swims ? 1 : 0)}";
        var rules = new RmWalkRules { StairsIcon = bundle.GetArgument(7, "stairs"), FootType = foot, MonsterType = monsters, GroundZ = ground, SkyZ = sky, DoorType = door, TrapDoorType = trapdoor, IgnoreUnits = true };
        var map = bundle.MapManager;
        var size = map.Size;
        if (!Maps.TryGetValue(mapKey, out var r) || now - r.Built >= RefreshTicks || now < r.Built) {
            if ((Maps.Count & 31) == 31) Forget(now);
            r = new Map { Z = goal.Z, Built = now, Cls = cls, Known = known, Swims = swims };
            r.X0 = System.Math.Max(1, goal.X - Radius);
            r.Y0 = System.Math.Max(1, goal.Y - Radius);
            r.W = System.Math.Min(size.X, goal.X + Radius) - r.X0 + 1;
            r.H = System.Math.Min(size.Y, goal.Y + Radius) - r.Y0 + 1;
            System.Array.Fill(r.Dist, -1, 0, r.W * r.H);
            // the goal's tiles: within reach of it, open (stairs only as the goal itself)
            for (var y = System.Math.Max(r.Y0, goal.Y - reach); y <= System.Math.Min(r.Y0 + r.H - 1, goal.Y + reach); y++)
                for (var x = System.Math.Max(r.X0, goal.X - reach); x <= System.Math.Min(r.X0 + r.W - 1, goal.X + reach); x++) {
                    var i = (y - r.Y0) * r.W + (x - r.X0);
                    var gw = WalkAt(r, i, m, goal, rules, map);
                    if (gw != 1 && gw != 4) continue;
                    r.Dist[i] = 0;
                    r.Open.Enqueue(i, 0);
                }
            Maps[mapKey] = r;
        }
        int sx = start.X - r.X0, sy = start.Y - r.Y0;
        if (sx < 0 || sy < 0 || sx >= r.W || sy >= r.H) return DreamValue.Null;
        var si = sy * r.W + sx;
        // spread on until M's tile is reached (its own tile shut to the map's rules: a tile beside it)
        var ownShut = WalkAt(r, si, m, goal, rules, map) == 2;
        while ((ownShut ? !NeighbourReached(r, sx, sy) : !r.Done[si]) && r.Open.Count > 0) Spread(r, m, goal, rules, map);
        var d = r.Done[si] ? r.Dist[si] : -1;
        if (d < 0) {
            var best = -1;
            foreach (var (dx, dy) in Steps) {
                int nx = sx + dx, ny = sy + dy;
                if (nx < 0 || ny < 0 || nx >= r.W || ny >= r.H) continue;
                var j = ny * r.W + nx;
                if (!r.Done[j]) continue;
                var e = r.Dist[j] + Enter(r, j);
                if (best < 0 || e < best) best = e;
            }
            if (best < 0) {
                _none++;
                return new DreamValue(0);
            }
            d = best;
        }
        var list = bundle.ObjectTree.CreateList();
        int cx = sx, cy = sy, n = 0;
        while (d > 0 && n < MaxRoute) {
            var next = -1;
            var held = false;
            foreach (var (dx, dy) in Steps) {
                int nx = cx + dx, ny = cy + dy;
                if (nx < 0 || ny < 0 || nx >= r.W || ny >= r.H) continue;
                var j = ny * r.W + nx;
                if (!r.Done[j] || r.Dist[j] + Enter(r, j) != d) continue;
                // the goal's own tile must be free now (no unit on it but M): a unit never stops on another's tile (Clip.dm),
                // and a goal held is what the search's "no way" was about; none free: no way, as the search said
                if (r.Dist[j] == 0 && !FreeNow(r, nx, ny, m, monsters, map)) {
                    held = true;
                    continue;
                }
                next = j;
                break;
            }
            if (next < 0) {
                if (held) {   // a step from the goal, every goal tile held: the search's answer stands
                    _none++;
                    list.DecRef();   // made here and held by nothing: let go
                    return new DreamValue(0);
                }
                break;
            }
            cx = next % r.W;
            cy = next / r.W;
            d = r.Dist[next];
            if (!map.TryGetTurfAt(new Vector2i(r.X0 + cx, r.Y0 + cy), r.Z, out var turf)) break;
            list.AddValue(new DreamValue(turf));
            n++;
            if (stopAt != null && System.Math.Max(System.Math.Abs(turf.X - stopAt.X), System.Math.Abs(turf.Y - stopAt.Y)) <= stopD) break;
        }
        _routes++;
        return new DreamValue(list);
    }

    private static bool FreeNow(Map r, int x, int y, DreamObject m, TreeEntry monsters, IDreamMapManager map) {
        if (!map.TryGetTurfAt(new Vector2i(r.X0 + x, r.Y0 + y), r.Z, out var t)) return false;
        foreach (var a in t.Cell.Movables)
            if (!a.Deleted && a != m && a.IsSubtypeOf(monsters) && RmNative.Truthy(a, "density")) return false;
        return true;
    }

    private static bool NeighbourReached(Map r, int sx, int sy) {
        foreach (var (dx, dy) in Steps) {
            int nx = sx + dx, ny = sy + dy;
            if (nx < 0 || ny < 0 || nx >= r.W || ny >= r.H) continue;
            if (r.Done[ny * r.W + nx]) return true;
        }
        return false;
    }

    // A step onto tile i (read already): deep water swum costs RmSwim.Cost steps, any other tile one.
    private static int Enter(Map r, int i) => r.Walk[i] == 4 ? RmSwim.Cost : 1;

    // One tile of the map's spread, the nearest to the goal not done yet: its steps are final, and its open neighbours get
    // its steps and the step onto it (when that is fewer than they had).
    private static void Spread(Map r, DreamObject m, DreamObjectTurf goal, RmWalkRules rules, IDreamMapManager map) {
        if (!r.Open.TryDequeue(out var c, out var dc)) return;
        if (r.Done[c] || dc != r.Dist[c]) return;   // an older entry for a tile whose steps dropped since
        r.Done[c] = true;
        int cx = c % r.W, cy = c / r.W;
        var d = r.Dist[c] + Enter(r, c);
        foreach (var (dx, dy) in Steps) {
            int nx = cx + dx, ny = cy + dy;
            if (nx < 0 || ny < 0 || nx >= r.W || ny >= r.H) continue;
            var j = ny * r.W + nx;
            if (r.Done[j] || (r.Dist[j] >= 0 && r.Dist[j] <= d)) continue;
            var w = WalkAt(r, j, m, goal, rules, map);
            if (w == 2) continue;
            if (r.Dist[j] < 0) _built++;
            r.Dist[j] = d;
            r.Open.Enqueue(j, d);
        }
    }

    // The tile's walk, read once a map: 1 open, 2 shut, 3 gone through (an own door) as the search's 2. With the reach map on
    // (RmReach.cs), a tile it calls blocked (but the goal itself, stairs being open as a goal) is shut, and an open one that
    // is asleep or holds nothing is open, without reading it (a sleeping tile isn't woken).
    private static byte WalkAt(Map r, int i, DreamObject m, DreamObjectTurf goal, RmWalkRules rules, IDreamMapManager map) {
        if (r.Walk[i] != 0) return r.Walk[i];
        int gx = r.X0 + i % r.W, gy = r.Y0 + i / r.W;
        var kinds = RmReach.KindsFor(r.Z, out var mapW);
        byte w = 0;
        var isGoal = gx == goal.X && gy == goal.Y && r.Z == goal.Z;
        if (r.Known != null && !isGoal && !Explored(r, gx, gy)) w = 1;   // never seen: as open as far as the player knows
        var kind = kinds != null ? kinds[(gy - 1) * mapW + gx - 1] : (byte)0;
        // with nothing on it, a tile's kind says it: deep water is swum (4) or shut (2), as the walk check says (RmSwim)
        var bare = kind == RmReach.WaterKind ? (r.Swims ? (byte)4 : (byte)2) : (byte)1;
        if (kinds != null && !isGoal) {
            if (RmReach.BlockedFor(kind, r.Cls)) w = 2;
            else if (map is DreamMapManager dm && dm.RmCountSleeping(r.Z, gx, gy, gx, gy) > 0) w = bare;
        }
        if (w == 1 && kind == RmReach.WaterKind) w = bare;   // never seen, but water all the same
        if (w == 0) {
            w = 2;
            if (map.TryGetTurfAt(new Vector2i(gx, gy), r.Z, out var t)) {
                if (kinds != null && !isGoal && t.Cell.Movables.Count == 0) w = bare;
                else {
                    var ok = rules.Walkable(t, m, goal);
                    w = ok == 0 ? (byte)2 : ok == 2 ? (byte)3 : RmSwim.On && RmSwim.Water(t) ? (byte)4 : (byte)1;
                }
            }
        }
        r.Walk[i] = w;
        return w;
    }

    // RemasterIsExplored(x, y, z): its chunk's row bitmask has the tile's bit.
    private static bool Explored(Map r, int x, int y) {
        int cx = (x - 1) / 16, cy = (y - 1) / 16, k = cx * 65536 + cy;
        if (!r.Rows.TryGetValue(k, out var rows)) {
            rows = null;
            using var v = r.Known!.GetValue(new DreamValue($"{cx},{cy}"));
            if (v.TryGetValueAsDreamList(out var L) && L.GetLength() >= 16) {
                rows = new int[16];
                for (var i = 0; i < 16; i++) {
                    using var e = L.GetValue(new DreamValue(i + 1));
                    rows[i] = e.TryGetValueAsFloat(out var f) ? (int)f : 0;
                }
            }
            r.Rows[k] = rows;
        }
        return rows != null && (rows[(y - 1) % 16] & (1 << ((x - 1) % 16))) != 0;
    }

    private static void Forget(float now) {
        var old = new List<string>();
        foreach (var (k, r) in Maps) if (now - r.Built >= RefreshTicks || now < r.Built) old.Add(k);
        foreach (var k in old) Maps.Remove(k);
    }

    [DreamProc("rm_route_stats")]
    public static DreamValue NativeProc_rm_route_stats(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        return new DreamValue($"maps={Maps.Count}|built_tiles={_built}|routes={_routes}|none={_none}|ms={_ticks * 1000.0 / Stopwatch.Frequency:F1}");
    }
}
