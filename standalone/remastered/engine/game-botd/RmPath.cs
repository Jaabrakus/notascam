// The route search, step for step as game/Code/Remastered/Orders.dm RemasterOrderPath (the DM version stays as the
// fallback and the reference): up to 512 tiles taken, the next tile always the lowest score (steps so far + distance
// left, get_dist as the game's: -1 on the same tile, else the larger of the x and y gaps), ties going to the tile added first, the same eight directions
// in the same order, the same bounds, and the same "closest point" for partial routes. Tiles holding only units of the
// mover's side are gone through but never ended on (Clip.dm). Returns list(route or null, rm_path_partial). Returns
// null, so the DM search runs instead, for anything it doesn't expect. Version 25: a deep water tile a swimmer goes into
// costs RmSwim.Cost steps (Swim.dm RmSwimCost), so routes keep to land and fords where the way round is short.
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using OpenDreamShared.Dream;
using Robust.Shared.Maths;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmPath {
    private sealed class Node(DreamObjectTurf turf, int seq) {
        public readonly DreamObjectTurf Turf = turf;
        public readonly int Seq = seq;
        public int Cost;
        public int Score;
        public Node? Parent;
        public bool Closed;
        public bool Side;   // units of the mover's side on it: gone through, never ended on
    }

    // NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST, as the DM loop takes them
    private static readonly (int dx, int dy)[] Steps = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)];

    // The game's get_dist (the compiler's DMStandard/_Standard.dm): -1 for the same tile, else the larger of the x and y
    // gaps. The -1 matters: the goal scores one below a neighbour with the same steps, so it is taken first (with 0,
    // a search reaching the goal near its 512 limit could run out a step short: 3 routes in 10,272 differed).
    private static int Dist(DreamObjectTurf a, DreamObjectTurf b) => a == b ? -1 : Math.Max(Math.Abs(b.X - a.X), Math.Abs(b.Y - a.Y));

    [DreamProc("rm_path")]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("goal", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("reach", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("bounds", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("radius", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("partial", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("pass", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("stairs")]
    [DreamProcParameter("foot", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("monsters", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("ground", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("sky", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("side", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("siege", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("trace", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("door", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("trapdoor", Type = DreamValueTypeFlag.DreamType)]
    public static DreamValue NativeProc_rm_path(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "M").TryGetValueAsDreamObject<DreamObjectMovable>(out var m)) return DreamValue.Null;
        if (m.Loc is not DreamObjectTurf start) return DreamValue.Null;
        if (!bundle.GetArgument(1, "goal").TryGetValueAsDreamObject<DreamObjectTurf>(out var goal)) return DreamValue.Null;
        if (!bundle.GetArgument(2, "reach").TryGetValueAsInteger(out var reach)) reach = 0;
        bundle.GetArgument(3, "bounds").TryGetValueAsDreamObject<DreamObjectTurf>(out var bounds);
        if (!bundle.GetArgument(4, "radius").TryGetValueAsInteger(out var radius)) radius = 0;
        var partial = bundle.GetArgument(5, "partial").IsTruthy();
        bundle.GetArgument(6, "pass").TryGetValueAsDreamList(out var pass);
        bundle.GetArgument(8, "foot").TryGetValueAsType(out var foot);
        bundle.GetArgument(9, "monsters").TryGetValueAsType(out var monsters);
        bundle.GetArgument(10, "ground").TryGetValueAsInteger(out var ground);
        bundle.GetArgument(11, "sky").TryGetValueAsInteger(out var sky);
        bundle.GetArgument(12, "side").TryGetValueAsDreamList(out var side);
        bundle.GetArgument(13, "siege").TryGetValueAsType(out var siege);
        bundle.GetArgument(15, "door").TryGetValueAsType(out var door);           // version 8: the own-door rule (null: off)
        bundle.GetArgument(16, "trapdoor").TryGetValueAsType(out var trapdoor);
        var rules = new RmWalkRules { StairsIcon = bundle.GetArgument(7, "stairs"), FootType = foot, MonsterType = monsters, GroundZ = ground, SkyZ = sky, Pass = pass, Side = side, SiegeType = siege, DoorType = door, TrapDoorType = trapdoor };
        var trace = bundle.GetArgument(14, "trace").IsTruthy() ? new List<DreamObjectTurf>() : null;   // tests: the tiles taken, in order

        var map = bundle.MapManager;
        var nodes = new Dictionary<DreamObjectTurf, Node>();
        var walk = new Dictionary<DreamObjectTurf, int>();   // asked once a search: nothing changes during one
        var open = new PriorityQueue<Node, (int score, int seq)>();
        var seq = 1;
        var first = new Node(start, seq) { Cost = 0, Score = Dist(start, goal) };
        nodes[start] = first;
        open.Enqueue(first, (first.Score, first.Seq));
        var openCount = 1;
        var closest = first;
        var closestD = first.Score;
        for (var tries = 0; tries < 512 && openCount > 0; tries++) {
            Node? current = null;
            while (open.TryDequeue(out var n, out var key)) {
                if (n.Closed || key.score != n.Score) continue;   // an older entry for a tile whose score dropped since
                current = n;
                break;
            }
            if (current == null) return DreamValue.Null;   // can't happen: every open tile has its current entry
            openCount--;
            trace?.Add(current.Turf);
            var d = Dist(current.Turf, goal);
            if (d <= reach && !current.Side) return Result(bundle, current, first, 0, trace);
            if (!current.Side && (d < closestD || (d == closestD && current.Cost < closest.Cost))) {
                closest = current;
                closestD = d;
            }
            current.Closed = true;
            foreach (var (dx, dy) in Steps) {
                if (!map.TryGetTurfAt(new Vector2i(current.Turf.X + dx, current.Turf.Y + dy), current.Turf.Z, out var next)) continue;
                if (bounds != null && (next.Z != bounds.Z || Dist(next, bounds) > radius)) continue;
                nodes.TryGetValue(next, out var node);
                if (node is { Closed: true }) continue;
                if (!walk.TryGetValue(next, out var ok)) {
                    ok = rules.Walkable(next, m, goal);
                    if (ok != 0 && RmSwim.On && RmSwim.Water(next) && !rules.FliesOver(m, next)) ok |= 4;   // deep water swum: RmSwim.Cost steps; flown over: one (version 25)
                    walk[next] = ok;
                }
                if (ok == 0) continue;
                var step = (ok & 4) != 0 ? RmSwim.Cost : 1;
                ok &= 3;
                var fresh = node == null;
                if (fresh || node!.Cost > current.Cost + step) {
                    if (fresh) {
                        seq++;
                        node = new Node(next, seq) { Side = ok == 2 };
                        nodes[next] = node;
                        openCount++;
                    }
                    node!.Cost = current.Cost + step;
                    node.Score = node.Cost + Dist(next, goal);
                    node.Parent = current;
                    open.Enqueue(node, (node.Score, node.Seq));
                }
            }
        }
        // Nothing nearer than where it stands: as close as it gets.
        var why = (openCount > 0 && closest != first) ? 1 : 2;
        if (!partial || closest == first) return Pair(bundle, null, why, trace);
        return Result(bundle, closest, first, why, trace);
    }

    private static DreamValue Result(NativeProc.Bundle bundle, Node end, Node start, int why, List<DreamObjectTurf>? trace) {
        var tiles = new List<DreamObjectTurf>();
        for (var n = end; n != start && n != null; n = n.Parent) tiles.Add(n.Turf);
        tiles.Reverse();
        var route = bundle.ObjectTree.CreateList();
        foreach (var t in tiles) route.AddValue(new DreamValue(t));
        return Pair(bundle, route, why, trace);
    }

    private static DreamValue Pair(NativeProc.Bundle bundle, DreamList? route, int why, List<DreamObjectTurf>? trace) {
        var pair = bundle.ObjectTree.CreateList();
        using (var rv = route != null ? new DreamValue(route) : DreamValue.Null) pair.AddValue(rv);   // the pair holds it; this proc lets go
        pair.AddValue(new DreamValue(why));
        if (trace != null) {
            var taken = bundle.ObjectTree.CreateList();
            foreach (var t in trace) taken.AddValue(new DreamValue(t));
            using (var tv = new DreamValue(taken)) pair.AddValue(tv);
        }
        return new DreamValue(pair);
    }

    // Tests: RmWalkRules.Walkable for one tile, as RemasterWalkable(T, M, goal, side) with rm_path_pass.
    [DreamProc("rm_walkable")]
    [DreamProcParameter("T", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("goal", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("pass", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("stairs")]
    [DreamProcParameter("foot", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("monsters", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("ground", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("sky", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("side", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("siege", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("door", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("trapdoor", Type = DreamValueTypeFlag.DreamType)]
    public static DreamValue NativeProc_rm_walkable(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "T").TryGetValueAsDreamObject<DreamObjectTurf>(out var t)) return DreamValue.Null;
        if (!bundle.GetArgument(1, "M").TryGetValueAsDreamObject<DreamObject>(out var m)) return DreamValue.Null;
        bundle.GetArgument(2, "goal").TryGetValueAsDreamObject<DreamObjectTurf>(out var goal);
        bundle.GetArgument(3, "pass").TryGetValueAsDreamList(out var pass);
        bundle.GetArgument(5, "foot").TryGetValueAsType(out var foot);
        bundle.GetArgument(6, "monsters").TryGetValueAsType(out var monsters);
        bundle.GetArgument(7, "ground").TryGetValueAsInteger(out var ground);
        bundle.GetArgument(8, "sky").TryGetValueAsInteger(out var sky);
        bundle.GetArgument(9, "side").TryGetValueAsDreamList(out var side);
        bundle.GetArgument(10, "siege").TryGetValueAsType(out var siege);
        bundle.GetArgument(11, "door").TryGetValueAsType(out var door);
        bundle.GetArgument(12, "trapdoor").TryGetValueAsType(out var trapdoor);
        var rules = new RmWalkRules { StairsIcon = bundle.GetArgument(4, "stairs"), FootType = foot, MonsterType = monsters, GroundZ = ground, SkyZ = sky, Pass = pass, Side = side, SiegeType = siege, DoorType = door, TrapDoorType = trapdoor };
        return new DreamValue(rules.Walkable(t, m, goal));
    }
}
