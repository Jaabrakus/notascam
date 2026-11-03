// The battle ways (native version 13; the owner, 10-28: "have the world preplan the best routes so everyone can fight
// gangup", then "native C# could do it in ~1m then we should do it in native"): for one side fighting one foe owner on
// a flat level, a field over a box round a 32x32 chunk (40 tiles each way since v20) giving every tile its steps to the nearest free tile beside
// a standing foe of that owner. A fighter walks the field down to the nearest place it can fight from, with no route
// search (game/Code/Remastered/Attack.dm RmGangUp). Built from the tiles at most once every RefreshTicks of game time
// (world.time, given by the game) and shared by every unit of that side in the chunk.
// Tiles as the route search sees them (RmWalkRules.Walkable with the asking unit and no goal): 0 shut, 1 open, 2 units of
// its side only (gone through, never ended on). A tile holding a standing foe (a unit of the foe owner with HP left, not
// dying, fainted, knocked out, CantKill, WS or a cart) is shut, and its open neighbours are where fights are (steps 0).
// With the reach map on (RmReach.cs), a tile it calls blocked (density, stairs, a drop, holy ground for the unholy) is
// shut and an empty open one open without reading the tile; the rest go through Walkable.
// The game's own chase (Attack.dm) stays the fallback and runs for whatever this answers null.
//   rm_field_route(M, foe, key, now, stairs, foot, monsters, ground, sky, side, siege, door, trapdoor)
//     a route (tiles from beside M to a free tile beside a foe of foe; its end free now, never a tile of M's side), an
//     empty list (M is a step from such tiles and every one is taken now: it waits its turn), 0 (no free tile beside a
//     foe of that owner it can get to within MaxSteps steps), or null (not known: a flyer, not dense, the Sky layer, not on a tile).
//   rm_field_stats()  "builds=..|build_ms=..|routes=..|waits=..|none=..|unknown=..|fields=.."
// RM_FIELD=0 in the server's environment: always null. RM_FIELD_TICKS: game ticks a field is kept (5). RM_FIELD_REACH: its reach (40).
using System.Collections.Generic;
using System.Diagnostics;
using OpenDreamRuntime.Map;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using Robust.Shared.Maths;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmField {
    private static readonly bool Disabled = System.Environment.GetEnvironmentVariable("RM_FIELD") == "0";
    private static readonly float RefreshTicks = float.TryParse(System.Environment.GetEnvironmentVariable("RM_FIELD_TICKS"), out var t) && t > 0 ? t : 5;
    // How far round its chunk a field reaches, and how many steps it leads (native version 20; the owner, 10-29, 1000 v 1000:
    // "lets fix that"). A big battle's back ranks are further than 16 steps from any free place, so each searched a route
    // that the foes' ranks shut (~0.5 ms a time, the biggest cost of the battle); 40 leads them on to the front. RM_FIELD_REACH
    // in the server's environment: 16 (as v19) to 64.
    private static readonly int Reach = System.Math.Clamp(int.TryParse(System.Environment.GetEnvironmentVariable("RM_FIELD_REACH"), out var r) ? r : 40, 16, 64);
    private const int Chunk = 32;
    private static readonly int Margin = Reach, Box = Chunk + 2 * Reach;
    private static readonly int MaxSteps = Reach;   // a place to fight from further than this: 0 (the game's chase), so none is led off across the field
    private const byte Shut = 0, Open = 1, SideOnly = 2, Foe = 3;

    // NORTH, SOUTH, EAST, WEST, NORTHEAST, NORTHWEST, SOUTHEAST, SOUTHWEST, as the route search takes them (RmPath.cs)
    private static readonly (int dx, int dy)[] Steps = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)];
    private static readonly DreamValue Svartalfar = new("Svartalfar"), Demon = new("Demon");

    private sealed class Field {
        public int X0, Y0, W, H, Z;          // the box: tiles X0..X0+W-1, Y0..Y0+H-1 (from 1)
        public float Built = float.MinValue; // world.time when built
        public readonly short[] Dist = new short[Box * Box];   // steps to the nearest free tile beside a foe; -1 none
        public readonly byte[] Walk = new byte[Box * Box];
    }

    private static readonly Dictionary<(string key, int z, int cx, int cy, int cls), Field> Fields = new();
    private static readonly int[] Queue = new int[Box * Box];
    private static readonly Stopwatch Clock = Stopwatch.StartNew();
    private static long _builds, _buildTicks, _routes, _waits, _none, _unknown;

    [DreamProc("rm_field_route")]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("foe", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("key", Type = DreamValueTypeFlag.String)]
    [DreamProcParameter("now", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("stairs")]
    [DreamProcParameter("foot", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("monsters", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("ground", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("sky", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("side", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("siege", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("door", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("trapdoor", Type = DreamValueTypeFlag.DreamType)]
    public static DreamValue NativeProc_rm_field_route(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var r = Route(bundle);
        if (r.IsNull) _unknown++;
        return r;
    }

    private static DreamValue Route(NativeProc.Bundle bundle) {
        if (Disabled) return DreamValue.Null;
        if (!bundle.GetArgument(0, "M").TryGetValueAsDreamObject<DreamObjectMovable>(out var m) || m.Deleted) return DreamValue.Null;
        if (m.Loc is not DreamObjectTurf start) return DreamValue.Null;
        if (!bundle.GetArgument(1, "foe").TryGetValueAsDreamObject(out var foe) || foe == null || foe.Deleted) return DreamValue.Null;
        if (!bundle.GetArgument(2, "key").TryGetValueAsString(out var key)) return DreamValue.Null;
        if (!bundle.GetArgument(3, "now").TryGetValueAsFloat(out var now)) return DreamValue.Null;
        bundle.GetArgument(5, "foot").TryGetValueAsType(out var foot);
        bundle.GetArgument(6, "monsters").TryGetValueAsType(out var monsters);
        bundle.GetArgument(7, "ground").TryGetValueAsInteger(out var ground);
        bundle.GetArgument(8, "sky").TryGetValueAsInteger(out var sky);
        bundle.GetArgument(9, "side").TryGetValueAsDreamList(out var side);
        bundle.GetArgument(10, "siege").TryGetValueAsType(out var siege);
        bundle.GetArgument(11, "door").TryGetValueAsType(out var door);
        bundle.GetArgument(12, "trapdoor").TryGetValueAsType(out var trapdoor);
        if (monsters == null || !m.IsSubtypeOf(monsters)) return DreamValue.Null;
        if (start.Z == sky || !RmNative.Truthy(m, "density") || RmNative.Truthy(m, "Flying")) return DreamValue.Null;   // the Sky layer's heights, flyers: the chase
        var rules = new RmWalkRules { StairsIcon = bundle.GetArgument(4, "stairs"), FootType = foot, MonsterType = monsters, GroundZ = ground, SkyZ = sky, Side = side, SiegeType = siege, DoorType = door, TrapDoorType = trapdoor, Swim = false };
        var map = bundle.MapManager;
        var size = map.Size;
        var cls = RmNative.Truthy(m, "Infects") || RmNative.Truthy(m, "Undead") || RmNative.Truthy(m, "Unholy") ||
                  RmNative.VarEquals(m, "Race", Svartalfar) || RmNative.VarEquals(m, "Race", Demon) ? 1 : 0;   // holy ground (RmReach.cs)
        int cx = (start.X - 1) / Chunk, cy = (start.Y - 1) / Chunk;
        var k = (key, start.Z, cx, cy, cls);
        if (!Fields.TryGetValue(k, out var f)) {
            if ((Fields.Count & 63) == 63) Forget(now);
            f = new Field();
            Fields[k] = f;
        }
        if (now - f.Built >= RefreshTicks || now < f.Built) {
            f.X0 = System.Math.Max(1, cx * Chunk + 1 - Margin);
            f.Y0 = System.Math.Max(1, cy * Chunk + 1 - Margin);
            f.W = System.Math.Min(size.X, cx * Chunk + Chunk + Margin) - f.X0 + 1;
            f.H = System.Math.Min(size.Y, cy * Chunk + Chunk + Margin) - f.Y0 + 1;
            f.Z = start.Z;
            f.Built = now;
            Build(f, m, foe, now, cls, rules, map);
        }
        return Walk(bundle, f, m, start);
    }

    // Fields not asked for in 10 s go.
    private static void Forget(float now) {
        var old = new List<(string, int, int, int, int)>();
        foreach (var (k, f) in Fields) if (now - f.Built > 100 || now < f.Built) old.Add(k);
        foreach (var k in old) Fields.Remove(k);
    }

    private static void Build(Field f, DreamObject m, DreamObject foe, float now, int cls, RmWalkRules rules, IDreamMapManager map) {
        var t0 = Clock.ElapsedTicks;
        _builds++;
        var kinds = RmReach.KindsFor(f.Z, out var mapW);
        var dm = map as DreamMapManager;
        int w = f.W, h = f.H;
        var walk = f.Walk;
        var dist = f.Dist;
        for (var y = 0; y < h; y++) {
            for (var x = 0; x < w; x++) {
                var i = y * w + x;
                dist[i] = -1;
                int gx = f.X0 + x, gy = f.Y0 + y;
                if (kinds != null) {
                    var kind = kinds[(gy - 1) * mapW + gx - 1];
                    if (RmReach.BlockedFor(kind, cls) || kind == RmReach.WaterKind) {   // no fighting in deep water (version 25)
                        walk[i] = Shut;
                        continue;
                    }
                    if (dm != null && dm.RmCountSleeping(f.Z, gx, gy, gx, gy) > 0) {   // asleep: nothing on it (read without waking it)
                        walk[i] = Open;
                        continue;
                    }
                }
                if (!map.TryGetTurfAt(new Vector2i(gx, gy), f.Z, out var turf)) {
                    walk[i] = Shut;
                    continue;
                }
                if (kinds != null && turf.Cell.Movables.Count == 0) {
                    walk[i] = Open;
                    continue;
                }
                var ok = rules.Walkable(turf, m, null);
                walk[i] = ok == 0 ? (HoldsFoe(turf, foe, now, rules) ? Foe : Shut) : (byte)ok;
            }
        }
        // where fights are: the open tiles beside a standing foe
        int head = 0, tail = 0;
        for (var i = 0; i < w * h; i++) {
            if (walk[i] != Foe) continue;
            int x = i % w, y = i / w;
            foreach (var (dx, dy) in Steps) {
                int nx = x + dx, ny = y + dy;
                if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
                var j = ny * w + nx;
                if (walk[j] != Open || dist[j] == 0) continue;
                dist[j] = 0;
                Queue[tail++] = j;
            }
        }
        // steps out from them, through open tiles and its side's
        while (head < tail) {
            var c = Queue[head++];
            int x = c % w, y = c / w;
            var d = (short)(dist[c] + 1);
            foreach (var (dx, dy) in Steps) {
                int nx = x + dx, ny = y + dy;
                if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
                var j = ny * w + nx;
                if (dist[j] >= 0 || (walk[j] != Open && walk[j] != SideOnly)) continue;
                dist[j] = d;
                Queue[tail++] = j;
            }
        }
        _buildTicks += Clock.ElapsedTicks - t0;
    }

    // A standing foe of that owner on the tile.
    private static bool HoldsFoe(DreamObjectTurf turf, DreamObject foe, float now, RmWalkRules rules) {
        foreach (var a in turf.Cell.Movables) {
            if (a.Deleted || rules.MonsterType == null || !a.IsSubtypeOf(rules.MonsterType)) continue;
            if (!RmNative.VarIsObject(a, "Owner", foe)) continue;
            if (Standing(a, now)) return true;
        }
        return false;
    }

    private static bool Standing(DreamObject a, float now) {
        if (Num(a, "HP") <= 0 || Num(a, "remaster_ko_until") > now) return false;
        return !RmNative.Truthy(a, "GoingToDie") && !RmNative.Truthy(a, "Fainted") && !RmNative.Truthy(a, "rm_dying_until") &&
               !RmNative.Truthy(a, "CantKill") && !RmNative.Truthy(a, "WS") && !RmNative.Truthy(a, "Wagon");
    }

    private static float Num(DreamObject o, string name) {
        if (!o.TryGetVariable(name, out var v)) return 0;
        using (v) return v.TryGetValueAsFloat(out var n) ? n : 0;
    }

    // No unit on the tile now but m.
    private static bool Free(DreamObjectTurf turf, DreamObject m, TreeEntry monsters) {
        foreach (var a in turf.Cell.Movables)
            if (!a.Deleted && a != m && a.IsSubtypeOf(monsters)) return false;
        return true;
    }

    // Down the field from where m stands.
    private static DreamValue Walk(NativeProc.Bundle bundle, Field f, DreamObject m, DreamObjectTurf start) {
        var map = bundle.MapManager;
        var monsters = bundle.GetArgument(6, "monsters").TryGetValueAsType(out var mt) ? mt : null;
        int w = f.W, h = f.H;
        int sx = start.X - f.X0, sy = start.Y - f.Y0;
        if (sx < 0 || sy < 0 || sx >= w || sy >= h) return DreamValue.Null;
        var cur = sy * w + sx;
        int d = f.Dist[cur];
        if (d < 0) {   // its own tile not reached (the builder's walk rules shut it): from its best neighbour
            var best = -1;
            foreach (var (dx, dy) in Steps) {
                int nx = sx + dx, ny = sy + dy;
                if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
                var j = ny * w + nx;
                if (f.Dist[j] >= 0 && (best < 0 || f.Dist[j] < best)) best = f.Dist[j];
            }
            if (best < 0) {
                _none++;
                return new DreamValue(0);
            }
            d = best + 1;
        }
        if (d > MaxSteps) {
            _none++;
            return new DreamValue(0);
        }
        var route = new List<(int i, DreamObjectTurf t)>();
        var cx = sx;
        var cy = sy;
        while (d > 0) {
            var next = -1;
            DreamObjectTurf? nt = null;
            foreach (var (dx, dy) in Steps) {
                int nx = cx + dx, ny = cy + dy;
                if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
                var j = ny * w + nx;
                if (f.Dist[j] != d - 1) continue;
                if (!map.TryGetTurfAt(new Vector2i(f.X0 + nx, f.Y0 + ny), f.Z, out var turf)) continue;
                if (d - 1 == 0 && monsters != null && !Free(turf, m, monsters)) continue;   // a place to fight from, taken since
                next = j;
                nt = turf;
                break;
            }
            if (next < 0) break;
            route.Add((next, nt!));
            cx = next % w;
            cy = next / w;
            d--;
        }
        // never ending on a tile of its side's units (Clip.dm): its last open tile, or nothing
        while (route.Count > 0 && (f.Walk[route[^1].i] != Open || (monsters != null && !Free(route[^1].t, m, monsters)))) route.RemoveAt(route.Count - 1);
        var list = bundle.ObjectTree.CreateList();
        foreach (var (_, turf) in route) list.AddValue(new DreamValue(turf));
        if (route.Count == 0) _waits++;
        else _routes++;
        return new DreamValue(list);
    }

    [DreamProc("rm_field_stats")]
    public static DreamValue NativeProc_rm_field_stats(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        var ms = _buildTicks * 1000.0 / Stopwatch.Frequency;
        return new DreamValue($"builds={_builds}|build_ms={ms:F1}|routes={_routes}|waits={_waits}|none={_none}|unknown={_unknown}|fields={Fields.Count}");
    }
}
