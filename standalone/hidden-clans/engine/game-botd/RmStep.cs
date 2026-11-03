// The plain step (native version 21; the owner, 10-29: "Native plain step"). A unit's step ran the game compiler's
// standard Move (DMStandard Types/Atoms/Movable.dm) and the ground's Enter chain (Code/Remastered/Chains/Enter.dm): in a
// 1000 v 1000 about 25 of a ~55 µs step (reports/polish-night-1026/step-native). Most of it was calls that do nothing: the
// old tile's Exit and Uncross on everything lying on it (~13 a step on a battle's tiles of bodies, blood and gear), Exited
// and Uncrossed, Crossed on everything on the new tile; no type of the game has its own (looked at once, below).
// On a plain tile this answers the ground's Enter chain rule for rule (Doors, Clip, Flying, WallWalks, TurfTypes) and
// moves the unit; the game then calls the ground's own Entered (Turfs.dm), or bumps what the standard Move bumps (Native.dm
// RmStepPlain). Not plain, and the game's script runs the standard Move as before: a tile with a placed door (rm_door_n), a
// wall-walk tile, cursed grass under a unit that minds it, another area, a turf whose Enter isn't the ground's own, a route
// of its side read through anything but tiles, and a game with its own Uncross, Uncrossed, Crossed, Exit or Exited.
// Change Chains/Enter.dm and this file together: the shadow mode (RM_STEP_VERIFY=1) logs any step that differs.
//   rm_step_setup(stairs, foot, monsters, siege, door, trapdoor, ground, sky, grounds)   the types, once (world start)
//   rm_step(M, T, Dir, side, pass, doors, decide)   1 moved, 0 blocked (the caller bumps), null not plain. decide: only
//     the answer, nothing done. side: RmSide(M); pass: rm_path_pass; doors: rm_own_doors.
//   rm_walk(T, M, goal, side, pass, doors)   RemasterWalkable(T, M, goal, side) (Orders.dm), as rm_walkable with the types
//     set once: 0, 1, 2, or null (T or M not one it reads: the game's own).
// Version 23 (the owner, 10-29: "Step-off + step"): the movables' density and Flying through RmKept.cs (kept while each
// one's change counter stands); a step that wouldn't turn the unit doesn't write its dir again (the write rebuilt its whole
// look, ~1 us, for 81% of a battle's steps); and the step-off's two looks (Clip.dm RmStepOffShared):
//   rm_shares(M, side)   1 when another dense unit of M's side, not flying, shares M's tile (the loop's test: O.density,
//     not Flying, RmSideUnit), else 0; null: M not on a tile, or not set up.
//   rm_step_off_tile(M, aim, pass, doors)   the tile beside M it steps off to, as its orange(1, M) loop finds it (its own
//     tile first, then the spiral; an invisible tile left out as orange leaves it): RemasterWalkable(T, M, T) == 1 and
//     RemasterTilePlaces(T, list(M)) > 0, the nearest aim (get_dist, the first of equals); 0 none; null not one it reads.
using System.Collections.Generic;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using Robust.Shared.Maths;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmStep {
    private static bool _set;
    private static DreamValue _stairs;
    private static TreeEntry? _foot, _monsters, _siege, _door, _trapdoor, _grounds;
    private static int _ground, _sky;
    private static int _quiet = -1;   // 1: the standard Move's other calls are all the standard library's own, doing nothing
    private static readonly Dictionary<DreamObjectDefinition, bool> GroundEnter = new();
    private static readonly List<DreamObject> Clip = new();
    private static readonly DreamValue GoodGrass = new("GoodGrass"), Svartalfar = new("Svartalfar"), Demon = new("Demon");
    private static readonly string[] Ways = { "remaster_active", "remaster_attack", "remaster_defense" };

    [DreamProc("rm_step_setup")]
    [DreamProcParameter("stairs")]
    [DreamProcParameter("foot", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("monsters", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("siege", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("door", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("trapdoor", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("ground", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("sky", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("grounds", Type = DreamValueTypeFlag.DreamType)]
    public static DreamValue NativeProc_rm_step_setup(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        _stairs = bundle.GetArgument(0, "stairs");
        bundle.GetArgument(1, "foot").TryGetValueAsType(out _foot);
        bundle.GetArgument(2, "monsters").TryGetValueAsType(out _monsters);
        bundle.GetArgument(3, "siege").TryGetValueAsType(out _siege);
        bundle.GetArgument(4, "door").TryGetValueAsType(out _door);
        bundle.GetArgument(5, "trapdoor").TryGetValueAsType(out _trapdoor);
        bundle.GetArgument(6, "ground").TryGetValueAsInteger(out _ground);
        bundle.GetArgument(7, "sky").TryGetValueAsInteger(out _sky);
        bundle.GetArgument(8, "grounds").TryGetValueAsType(out _grounds);
        _set = _monsters != null && _grounds != null;
        return new DreamValue(_set ? 1 : 0);
    }

    private static RmWalkRules Rules(DreamList? side, DreamList? pass, bool doors) => new() {
        StairsIcon = _stairs, FootType = _foot, MonsterType = _monsters, GroundZ = _ground, SkyZ = _sky, Pass = pass, Side = side,
        SiegeType = _siege, DoorType = doors ? _door : null, TrapDoorType = doors ? _trapdoor : null
    };

    [DreamProc("rm_walk")]
    [DreamProcParameter("T", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("goal", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("side", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("pass", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("doors", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_walk(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!_set) return DreamValue.Null;
        if (!bundle.GetArgument(0, "T").TryGetValueAsDreamObject<DreamObjectTurf>(out var t)) return DreamValue.Null;
        if (!bundle.GetArgument(1, "M").TryGetValueAsDreamObject<DreamObject>(out var m) || m == null) return DreamValue.Null;
        bundle.GetArgument(2, "goal").TryGetValueAsDreamObject<DreamObjectTurf>(out var goal);
        bundle.GetArgument(3, "side").TryGetValueAsDreamList(out var side);
        bundle.GetArgument(4, "pass").TryGetValueAsDreamList(out var pass);
        var doors = bundle.GetArgument(5, "doors").IsTruthy();
        return new DreamValue(Rules(side, pass, doors).Walkable(t, m, goal));
    }

    // The standard Move's other calls (Exit and Uncross on the old tile and what lies on it, Exited, Uncrossed, Crossed)
    // are all the standard library's own: /atom's and /turf's, no override anywhere.
    private static bool Quiet(DreamObjectTree tree) {
        if (_quiet >= 0) return _quiet == 1;
        _quiet = 0;
        var atom = tree.Atom.ObjectDefinition;
        var turf = tree.Turf.ObjectDefinition;
        if (!atom.TryGetProc("Uncross", out var uncross) || !atom.TryGetProc("Uncrossed", out var uncrossed) || !atom.TryGetProc("Crossed", out var crossed) ||
            !atom.TryGetProc("Exit", out var atomExit) || !atom.TryGetProc("Exited", out var atomExited)) return false;
        if (uncross.SuperProc != null || uncrossed.SuperProc != null || crossed.SuperProc != null || atomExit.SuperProc != null || atomExited.SuperProc != null) return false;
        if (!turf.TryGetProc("Exit", out var turfExit) || !turf.TryGetProc("Exited", out var turfExited)) return false;
        if (turfExit.SuperProc != atomExit || turfExited.SuperProc != atomExited) return false;
        foreach (var type in tree.GetAllDescendants(tree.Atom)) {
            var d = type.ObjectDefinition;
            if (d == null) continue;
            if (!d.TryGetProc("Uncross", out var p) || p != uncross || !d.TryGetProc("Uncrossed", out p) || p != uncrossed ||
                !d.TryGetProc("Crossed", out p) || p != crossed) return false;
        }
        foreach (var type in tree.GetAllDescendants(tree.Turf)) {
            var d = type.ObjectDefinition;
            if (d == null) continue;
            if (!d.TryGetProc("Exit", out var p) || p != turfExit || !d.TryGetProc("Exited", out p) || p != turfExited) return false;
        }
        _quiet = 1;
        return true;
    }

    // A ground tile whose Enter is the ground's own chain (Chains/Enter.dm), not a type of its own.
    private static bool IsGround(DreamObjectTurf t) {
        var d = t.ObjectDefinition;
        if (GroundEnter.TryGetValue(d, out var ok)) return ok;
        ok = t.IsSubtypeOf(_grounds!) && _grounds!.ObjectDefinition.TryGetProc("Enter", out var ge) && d.TryGetProc("Enter", out var e) && e == ge;
        GroundEnter[d] = ok;
        return ok;
    }

    [DreamProc("rm_step")]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("T", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("Dir", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("side", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("pass", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("doors", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("decide", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_step(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!_set) return DreamValue.Null;
        if (!bundle.GetArgument(0, "M").TryGetValueAsDreamObject<DreamObjectMovable>(out var m) || m == null || m.Deleted) return DreamValue.Null;
        if (!bundle.GetArgument(1, "T").TryGetValueAsDreamObject<DreamObjectTurf>(out var t)) return DreamValue.Null;
        if (m.Loc is not DreamObjectTurf old || old == t) return DreamValue.Null;
        if (!Quiet(bundle.ObjectTree) || !IsGround(t) || old.Cell.Area != t.Cell.Area) return DreamValue.Null;
        bundle.GetArgument(2, "Dir").TryGetValueAsInteger(out var dir);
        bundle.GetArgument(3, "side").TryGetValueAsDreamList(out var side);
        bundle.GetArgument(4, "pass").TryGetValueAsDreamList(out var pass);
        var doors = bundle.GetArgument(5, "doors").IsTruthy();
        var decide = bundle.GetArgument(6, "decide").IsTruthy();
        var rules = Rules(side, pass, doors);

        // step 1 of 5, Doors: a tile that counts a placed door is the game's
        if (RmNative.Truthy(t, "rm_door_n")) return DreamValue.Null;

        // step 2 of 5, Clip: a step under its own usr onto a tile holding only units of its side, its way going on from it to
        // a tile it can stop on: those units don't count for the steps below
        var mMonster = m.IsSubtypeOf(_monsters!);
        var mDense = RmKept.Dense(m);
        var tDense = RmNative.Truthy(t, "density");
        if (tDense && RmSwim.Water(t)) return DreamValue.Null;   // deep water: the game's (Swim.dm, version 25)
        Clip.Clear();
        if (usr == m && !tDense && mMonster && mDense && !RmKept.Flying(m) && side != null) {
            var clipping = true;
            foreach (var a in t.Cell.Movables) {
                if (a.Deleted || a == m || !RmKept.Dense(a)) continue;
                if (!rules.SideUnit(a)) {
                    clipping = false;
                    break;
                }
                Clip.Add(a);
            }
            if (!clipping) Clip.Clear();
            if (Clip.Count > 0) {
                var lands = ClipLands(m, t, old, rules);
                if (lands < 0) {
                    Clip.Clear();
                    return DreamValue.Null;
                }
                if (lands == 0) Clip.Clear();
            }
        }

        bool enter;
        if (rules.FliesOver(m, t)) enter = true;   // step 3 of 5, Flying
        else if (RmNative.Truthy(t, "remaster_wallwalk") && mMonster) {   // step 4 of 5, WallWalks: the game's
            Clip.Clear();
            return DreamValue.Null;
        } else if (usr == null || RmNative.Truthy(usr, "key")) enter = true;   // step 5 of 5, TurfTypes: the original's rule
        else if (RmNative.VarEquals(t, "icon_state", GoodGrass) && (RmNative.Truthy(usr, "Infects") || RmNative.Truthy(usr, "Undead") ||
                     RmNative.Truthy(usr, "Unholy") || RmNative.VarEquals(usr, "Race", Svartalfar) || RmNative.VarEquals(usr, "Race", Demon))) {
            Clip.Clear();
            return DreamValue.Null;   // it shuts the tile a moment (a spawn): the game's
        } else if (RmNative.Truthy(m, "IsMist")) enter = true;
        else if (!tDense) {
            enter = true;
            if (mDense)
                foreach (var a in t.Cell.Movables) {
                    if (a.Deleted || Clip.Contains(a) || !RmKept.Dense(a)) continue;
                    enter = false;
                    break;
                }
        } else enter = false;
        Clip.Clear();

        if (decide) return new DreamValue(enter ? 1 : 0);
        if (dir != 0 && !FacesAlready(m, dir)) m.SetVariable("dir", new DreamValue(dir));   // the standard Move turns it first, moved or not
        if (!enter) return new DreamValue(0);
        m.SetVariable("loc", new DreamValue(t));
        return new DreamValue(1);
    }

    // Already facing dir: the standard Move's write would set the same look again.
    private static bool FacesAlready(DreamObjectMovable m, int dir) {
        if (!m.TryGetVariable("dir", out var d)) return false;
        using (d) return d.TryGetValueAsInteger(out var now) && now == dir;
    }

    [DreamProc("rm_shares")]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("side", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_shares(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!_set) return DreamValue.Null;
        if (!bundle.GetArgument(0, "M").TryGetValueAsDreamObject<DreamObjectMovable>(out var m) || m == null || m.Deleted) return DreamValue.Null;
        if (m.Loc is not DreamObjectTurf here) return DreamValue.Null;
        bundle.GetArgument(1, "side").TryGetValueAsDreamList(out var side);
        if (side == null) return new DreamValue(0);   // RmSideUnit: no side, nobody of it
        var rules = Rules(side, null, false);
        foreach (var a in here.Cell.Movables) {
            if (a.Deleted || a == m || !a.IsSubtypeOf(_monsters!)) continue;
            if (RmKept.Dense(a) && !RmKept.Flying(a) && rules.SideUnit(a)) return new DreamValue(1);
        }
        return new DreamValue(0);
    }

    [DreamProc("rm_step_off_tile")]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("aim", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("pass", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("doors", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_step_off_tile(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!_set) return DreamValue.Null;
        if (!bundle.GetArgument(0, "M").TryGetValueAsDreamObject<DreamObjectMovable>(out var m) || m == null || m.Deleted) return DreamValue.Null;
        if (m.Loc is not DreamObjectTurf here) return DreamValue.Null;
        if (!bundle.GetArgument(1, "aim").TryGetValueAsDreamObject<DreamObjectTurf>(out var aim) || aim == null) return DreamValue.Null;
        bundle.GetArgument(2, "pass").TryGetValueAsDreamList(out var pass);
        if (RmKept.Flying(m)) return DreamValue.Null;   // RmAllFly(list(M)) would matter on open sky: the game's (it never asks for one flying)
        var rules = Rules(null, pass, bundle.GetArgument(3, "doors").IsTruthy());   // RemasterWalkable(T, M, T): no side
        DreamObjectTurf? best = null;
        var bestD = 0;
        var map = bundle.MapManager;
        var atoms = bundle.AtomManager;
        // orange(1, M) for M on a tile (DreamProcNativeHelpers.HandleRange): M's own tile, then the spiral round it: the
        // left column bottom to top, the tile below, the tile above, the right column bottom to top
        for (var i = 0; i < 9; i++) {
            DreamObjectTurf? t;
            if (i == 0) t = here;
            else {
                var (dx, dy) = Spiral[i - 1];
                if (!map.TryGetTurfAt(new Vector2i(here.X + dx, here.Y + dy), here.Z, out t)) continue;
            }
            if (atoms.MustGetAppearance(t).Invisibility >= 101) continue;   // orange leaves it out
            if (t.Z != here.Z || rules.Walkable(t, m, t) != 1 || !HasPlace(t, m)) continue;
            var d = t == aim ? -1 : Dist(t, aim);   // get_dist as the game's compiler has it: -1 for the same tile
            if (best == null || d < bestD) {
                best = t;
                bestD = d;
            }
        }
        if (best == null) return new DreamValue(0);
        best.IncRef();   // the caller's reference (a value handed back holds one, as the engine's own procs do it)
        return new DreamValue(best);
    }

    private static readonly (int, int)[] Spiral = { (-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1) };

    // Orders.dm RemasterTilePlaces(T, list(M)) > 0 for M not flying: not dense, not open sky or a chasm, not stairs, and no
    // dense thing on it but M (on a wall-walk tile, at most one unit).
    private static bool HasPlace(DreamObjectTurf t, DreamObjectMovable m) {
        if (RmNative.Truthy(t, "density")) return false;
        var iconState = RmNative.VarString(t, "icon_state");
        if (iconState == "Sky" || iconState == "Chasm") return false;   // RmOpenSky(T) && RmAllFly(list(M)): M isn't flying
        if (RmNative.VarEquals(t, "icon", _stairs)) return false;
        var wallwalk = RmNative.Truthy(t, "remaster_wallwalk");
        var taken = 0;
        foreach (var a in t.Cell.Movables) {
            if (a.Deleted || a == m || !RmKept.Dense(a)) continue;
            if (!wallwalk || !a.IsSubtypeOf(_monsters!)) return false;
            taken++;
        }
        return (wallwalk ? 2 : 1) - taken > 0;
    }

    // Clip.dm: L = M.RmRouteInto(T); length(L) > 1 && RmClipLands(L, M, L[length(L)], side). 1 lands, 0 not, -1 not one
    // it reads (the game's).
    private static int ClipLands(DreamObject m, DreamObjectTurf t, DreamObjectTurf old, RmWalkRules rules) {
        var r = RouteInto(m, t, old, out var route, out var straight);
        if (r < 0) return -1;
        if (straight != null)   // list(T, destination): its destination open
            return rules.Walkable(straight, m, straight) == 1 ? 1 : 0;
        if (route == null) return 0;
        var len = route.GetLength();
        if (len <= 1) return 0;
        DreamObjectTurf? goal;
        using (var last = route.GetValue(new DreamValue(len))) {
            if (!last.TryGetValueAsDreamObject<DreamObjectTurf>(out goal)) return -1;
        }
        var i = 0;
        foreach (var v in route.EnumerateValues()) {   // the list's own values: never disposed
            i++;
            if (!v.TryGetValueAsDreamObject<DreamObjectTurf>(out var step)) return -1;
            if (i == 1) {
                if (step == goal) return 0;
                continue;
            }
            var w = rules.Walkable(step, m, goal);
            if (w == 1) return 1;
            if (w == 0 || step == goal) return 0;
            if (i >= 13) break;   // RM_CLIP_AHEAD 12
        }
        return 0;
    }

    // Clip.dm RmRouteInto(T): a delivery's route, an order's, an attack's, guard duty's or a building site's whose next tile
    // is T; or a walk straight at a destination it nears through T. 0 read (route or straight, or neither), -1 not readable.
    private static int RouteInto(DreamObject m, DreamObjectTurf t, DreamObjectTurf old, out DreamList? route, out DreamObjectTurf? straight) {
        route = null;
        straight = null;
        var k = WayOf(m, "remaster_delivery", t, out route);
        if (k != 0) return k < 0 ? -1 : 0;
        foreach (var name in Ways) {
            k = WayOf(m, name, t, out route);
            if (k != 0) return k < 0 ? -1 : 0;
        }
        if (m.TryGetVariable("remaster_site_path", out var sp))
            using (sp) {
                if (sp.TryGetValueAsDreamList(out var sl) && FirstIs(sl, t)) {
                    route = sl;
                    return 0;
                }
            }
        route = null;
        if (m.TryGetVariable("destination", out var dv))
            using (dv) {
                if (dv.TryGetValueAsDreamObject<DreamObjectTurf>(out var d) && d != t && d.Z == t.Z && Dist(t, d) < Dist(old, d)) straight = d;
            }
        return 0;
    }

    // name's datum's path, when its first tile is T: 1 (route set), 0 not, -1 a deleted datum (the game's).
    private static int WayOf(DreamObject m, string name, DreamObjectTurf t, out DreamList? route) {
        route = null;
        if (!m.TryGetVariable(name, out var v)) return 0;
        using (v) {
            if (!v.TryGetValueAsDreamObject<DreamObject>(out var o) || o == null) return 0;
            if (o.Deleted) return -1;
            if (!o.TryGetVariable("path", out var p)) return 0;
            using (p) {
                if (p.TryGetValueAsDreamList(out var l) && FirstIs(l, t)) {
                    route = l;
                    return 1;
                }
            }
        }
        return 0;
    }

    private static bool FirstIs(DreamList l, DreamObjectTurf t) {
        foreach (var v in l.EnumerateValues()) return v.TryGetValueAsDreamObject<DreamObjectTurf>(out var f) && f == t;
        return false;
    }

    // get_dist as the game's compiler has it, for two tiles: the larger gap (a unit on a tile reads that tile's x and y)
    private static int Dist(DreamObjectTurf a, DreamObjectTurf b) => System.Math.Max(System.Math.Abs(b.X - a.X), System.Math.Abs(b.Y - a.Y));
}
