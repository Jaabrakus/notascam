// RmGrid (engine v12 candidate, native version 11; server cost, 2026-10-25; planning/ONE_SIGHT_GRID.md step B2): the
// units standing on the map, in 16x16 cells layer by layer (the same cells as awake land's chunks, Awake.dm: cell x is
// (x - 1) / 16), kept by the engine as they move. The GRID patch (build_v12.py) tells it at the places a tile's list of
// things changes, all in DreamObjectMovable.SetLoc (onto a turf, into another movable, off the map; a deletion, a cut
// turf.contents and a smaller map go through SetLoc(null) too), so it holds exactly the units in those lists: what
// rm_foe_near's tile scan reads. A map that changes size is built again (every cell's number moves) by the next query;
// until then a step onto a tile past the old edge just leaves the grid.
// Off until the game calls rm_grid_on(type) (Native.dm, at world start), which builds it from the atoms (no tile read);
// from then on every move keeps it. RM_GRID=0: never on (rm_grid_on answers 0 and the game keeps its own loops).
// RM_GRID_VERIFY=1: shadow mode, rm_foe_near works out both answers, uses the tile scan's and counts any difference.
//   rm_grid_on(type)                 1: on, built from every unit of type now
//   rm_grid_off()                    off again (tests, a way out); rm_grid_on builds it again
//   rm_grid_cells(owners)            the cells holding a unit whose Owner is one of owners: a flat list cx, cy, z, ...
//   rm_grid_held(owners)             those owners' units inside another movable (carried, in a cart): no tile of their own
//   rm_grid_units(x0, y0, x1, y1, z) the units on the tiles of that box
//   rm_grid_changed(who, slot, x0, y0, x1, y1, z, mode)  (native version 27; server upgrades U6, 10-30) for one caller
//                                    (who, a player; slot, one of its views): list(the units in the box that are new to it or
//                                    whose change counter moved since its last call, the units it had that left the box, 1
//                                    when the first list is every unit in the box). mode 1: every unit (the caller's pace or
//                                    page changed); mode 2: the changed and every unit not who's (its fog changed: the others
//                                    are looked at again); a unit it had that was deleted makes it every unit too (the caller
//                                    drops what it kept for it). The 3D move rows (View3D.dm) then touch only what changed.
//   rm_grid_check()                  tests: every unit of the type checked against the grid; how many are wrong
//   rm_grid_stats()                  "units N cells N held N foe_checked N foe_differed N"
using System.Collections.Generic;
using OpenDreamRuntime.Map;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using Robust.Shared.Maths;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmGrid {
    public const int CellSize = 16;
    private static readonly bool Disabled = System.Environment.GetEnvironmentVariable("RM_GRID") == "0";
    public static readonly bool Verify = System.Environment.GetEnvironmentVariable("RM_GRID_VERIFY") == "1";
    public static bool On { get; private set; }
    private static TreeEntry? _type;
    private static IDreamMapManager? _map;
    private static AtomManager? _atoms;
    private static int _w, _h, _levels, _sx, _sy;
    private static List<DreamObjectMovable>?[] _cells = System.Array.Empty<List<DreamObjectMovable>?>();
    // A unit's own cell is kept on it (DreamObjectMovable.RmGridCell, the GRID patch): a step reads one field of the object
    // it is moving, not a dictionary (v12d: the dictionary cost ~0.5 us a step on a loaded Mac, tests/grid_bench_ab.dm).
    public const int NoCell = -1, HeldCell = -2;
    private static readonly HashSet<DreamObjectMovable> _held = new();          // a unit inside another movable
    private static int _occupied, _units;
    private static long _foeChecked, _foeDiffered;

    // --- kept by SetLoc (the GRID patch) ---
    public static void OnTurf(DreamObjectMovable m, DreamObjectTurf t) {
        if (!On || !m.IsSubtypeOf(_type!)) return;
        var i = Index(t.X, t.Y, t.Z);   // with the map grown, -1 until a query builds it again (Resized)
        var old = m.RmGridCell;
        if (old == i) return;
        Leave(m);
        if (i < 0) return;
        Put(i, m);
        m.RmGridCell = i;
    }

    public static void Held(DreamObjectMovable m) {
        if (!On || !m.IsSubtypeOf(_type!)) return;
        if (m.RmGridCell == HeldCell) return;
        Leave(m);
        _held.Add(m);
        m.RmGridCell = HeldCell;
    }

    public static void Off(DreamObjectMovable m) {
        if (!On || !m.IsSubtypeOf(_type!)) return;
        Leave(m);
    }

    // Out of its cell, or out of the held set; no cell after.
    private static void Leave(DreamObjectMovable m) {
        var old = m.RmGridCell;
        if (old >= 0) Take(old, m);
        else if (old == HeldCell) _held.Remove(m);
        m.RmGridCell = NoCell;
    }

    private static void Put(int i, DreamObjectMovable m) {
        var l = _cells[i] ??= new List<DreamObjectMovable>(4);
        if (l.Count == 0) _occupied++;
        l.Add(m);
        _units++;
    }

    private static void Take(int i, DreamObjectMovable m) {
        var l = _cells[i];
        if (l == null) return;
        var k = l.IndexOf(m);
        if (k < 0) return;
        var last = l.Count - 1;
        l[k] = l[last];
        l.RemoveAt(last);
        _units--;
        if (l.Count == 0) _occupied--;
    }

    private static int Index(int x, int y, int z) {
        if (x < 1 || y < 1 || z < 1 || z > _levels) return -1;
        int cx = (x - 1) / CellSize, cy = (y - 1) / CellSize;
        if (cx >= _w || cy >= _h) return -1;
        return ((z - 1) * _h + cy) * _w + cx;
    }

    // The map's size or levels changed (world.maxx and the like): every cell's number moves, so it's built again.
    private static bool Resized() {
        var size = _map!.Size;
        if (size.X == _sx && size.Y == _sy && _map.Levels == _levels) return false;
        Build();
        return true;
    }

    private static void Build() {
        var size = _map!.Size;
        _sx = size.X;
        _sy = size.Y;
        _levels = _map.Levels;
        _w = (size.X + CellSize - 1) / CellSize;
        _h = (size.Y + CellSize - 1) / CellSize;
        _cells = new List<DreamObjectMovable>?[_w * _h * _levels];
        _held.Clear();
        _occupied = 0;
        _units = 0;
        foreach (var a in _atoms!.EnumerateAtoms(_type)) {
            if (a is not DreamObjectMovable m || m.Deleted) continue;
            m.RmGridCell = NoCell;
            if (m.Loc is DreamObjectTurf t) {
                var i = Index(t.X, t.Y, t.Z);
                if (i >= 0 && t.Cell.Movables.Contains(m)) {
                    Put(i, m);
                    m.RmGridCell = i;
                }
            } else if (m.Loc is DreamObjectMovable) {
                _held.Add(m);
                m.RmGridCell = HeldCell;
            }
        }
    }

    // --- rm_foe_near from the grid (RmSight.cs): null when the grid can't answer, and the tile scan does ---
    // The same units as the scan's: those of the cells over the square, on its tiles. Where the cells over the square
    // hold more units than it has tiles (a crowd), null: the plain tile scan reads less there (tests/grid_bench.dm). A
    // cell holding more units than it has tiles under the square has those tiles read instead.
    public static bool? FoeNear(DreamObjectMovable m, DreamObjectTurf here, int dist, TreeEntry monsters, DreamObject? own, string? ownName) {
        if (!On || !monsters.IsSubtypeOf(_type!)) return null;
        Resized();
        var size = _map!.Size;
        int x0 = System.Math.Max(1, here.X - dist), x1 = System.Math.Min(size.X, here.X + dist);
        int y0 = System.Math.Max(1, here.Y - dist), y1 = System.Math.Min(size.Y, here.Y + dist);
        int z = here.Z;
        if (z < 1 || z > _levels || x0 > x1 || y0 > y1) return null;
        int cx0 = (x0 - 1) / CellSize, cx1 = (x1 - 1) / CellSize, cy0 = (y0 - 1) / CellSize, cy1 = (y1 - 1) / CellSize;
        if (cx1 >= _w || cy1 >= _h) return null;
        // A crowd: the cells hold more units than the square has tiles, so the plain tile scan reads less (tests/grid_bench.dm)
        var held = 0;
        for (var cy = cy0; cy <= cy1; cy++)
            for (var cx = cx0; cx <= cx1; cx++)
                held += _cells[((z - 1) * _h + cy) * _w + cx]?.Count ?? 0;
        if (held > (x1 - x0 + 1) * (y1 - y0 + 1)) return null;
        for (var cy = cy0; cy <= cy1; cy++) {
            for (var cx = cx0; cx <= cx1; cx++) {
                var l = _cells[((z - 1) * _h + cy) * _w + cx];
                if (l == null || l.Count == 0) continue;
                int rx0 = System.Math.Max(x0, cx * CellSize + 1), rx1 = System.Math.Min(x1, cx * CellSize + CellSize);
                int ry0 = System.Math.Max(y0, cy * CellSize + 1), ry1 = System.Math.Min(y1, cy * CellSize + CellSize);
                if (l.Count <= (rx1 - rx0 + 1) * (ry1 - ry0 + 1)) {
                    foreach (var a in l) {
                        if (a == m || a.Deleted || !a.IsSubtypeOf(monsters)) continue;
                        if (a.Loc is not DreamObjectTurf at) return null;   // on a tile by way of an area: the scan knows where
                        if (at.X < rx0 || at.X > rx1 || at.Y < ry0 || at.Y > ry1) continue;
                        if (Foe(a, own, ownName)) return true;
                    }
                } else {
                    for (var y = ry0; y <= ry1; y++) {
                        for (var x = rx0; x <= rx1; x++) {
                            if (!_map.TryGetTurfAt(new Vector2i(x, y), z, out var t)) continue;
                            foreach (var a in t.Cell.Movables) {
                                if (a == m || a.Deleted || !a.IsSubtypeOf(monsters)) continue;
                                if (Foe(a, own, ownName)) return true;
                            }
                        }
                    }
                }
            }
        }
        return false;
    }

    // One the look could pick (RmSight.cs's rule, the same lines).
    public static bool Foe(DreamObjectMovable a, DreamObject? own, string? ownName) {
        if (own == null && ownName == null) return true;   // M has no owner: any unit may be one it fights
        if (!a.TryGetVariable("Owner", out var ao)) return true;
        using (ao) {
            if (own != null) {
                if (!ao.TryGetValueAsDreamObject<DreamObject>(out var o) || o.Deleted || o != own) return true;
            } else if (!ao.TryGetValueAsString(out var an) || !string.Equals(an, ownName, System.StringComparison.Ordinal)) {
                return true;
            }
        }
        return false;
    }

    public static void Compared(bool same, DreamObjectTurf here, int dist, bool grid, bool scan) {
        _foeChecked++;
        if (same) return;
        if (++_foeDiffered <= 20) System.Console.WriteLine($"RMGRID|foe differs|{here.X},{here.Y},{here.Z}|dist {dist}|grid {grid} scan {scan}");
    }

    private static HashSet<DreamObject> OwnerSet(DreamList owners) {
        var set = new HashSet<DreamObject>();
        foreach (var v in owners.EnumerateValues())
            if (v.TryGetValueAsDreamObject<DreamObject>(out var o) && o != null && !o.Deleted) set.Add(o);
        return set;
    }

    private static bool OwnedBy(DreamObjectMovable a, HashSet<DreamObject> set) {
        if (!a.TryGetVariable("Owner", out var ao)) return false;
        using (ao) return ao.TryGetValueAsDreamObject<DreamObject>(out var o) && o != null && set.Contains(o);
    }

    [DreamProc("rm_grid_on")]
    [DreamProcParameter("type", Type = DreamValueTypeFlag.DreamType)]
    public static DreamValue NativeProc_rm_grid_on(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (Disabled || !bundle.GetArgument(0, "type").TryGetValueAsType(out var type)) return new DreamValue(0);
        _type = type;
        _map = bundle.MapManager;
        _atoms = bundle.AtomManager;
        On = false;
        Build();
        On = true;
        return new DreamValue(1);
    }

    // Off again (tests, and a way out at run time): the hooks do nothing and rm_foe_near scans; rm_grid_on builds it again.
    [DreamProc("rm_grid_off")]
    public static DreamValue NativeProc_rm_grid_off(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        On = false;
        _cells = System.Array.Empty<List<DreamObjectMovable>?>();
        _held.Clear();
        _occupied = 0;
        _units = 0;
        _sx = _sy = _levels = 0;
        return DreamValue.Null;
    }

    [DreamProc("rm_grid_cells")]
    [DreamProcParameter("owners", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_grid_cells(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!On || !bundle.GetArgument(0, "owners").TryGetValueAsDreamList(out var owners)) return DreamValue.Null;
        var set = OwnerSet(owners);
        var list = bundle.ObjectTree.CreateList();
        if (set.Count == 0) return new DreamValue(list);
        Resized();
        for (var i = 0; i < _cells.Length; i++) {
            var l = _cells[i];
            if (l == null || l.Count == 0) continue;
            foreach (var a in l) {
                if (!OwnedBy(a, set)) continue;
                list.AddValue(new DreamValue(i % _w));
                list.AddValue(new DreamValue(i / _w % _h));
                list.AddValue(new DreamValue(i / (_w * _h) + 1));
                break;
            }
        }
        return new DreamValue(list);
    }

    [DreamProc("rm_grid_held")]
    [DreamProcParameter("owners", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_grid_held(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!On || !bundle.GetArgument(0, "owners").TryGetValueAsDreamList(out var owners)) return DreamValue.Null;
        var set = OwnerSet(owners);
        var list = bundle.ObjectTree.CreateList();
        Resized();
        foreach (var a in _held) if (!a.Deleted && OwnedBy(a, set)) list.AddValue(new DreamValue(a));
        return new DreamValue(list);
    }

    [DreamProc("rm_grid_units")]
    [DreamProcParameter("x0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("x1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_grid_units(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!On) return DreamValue.Null;
        if (!bundle.GetArgument(0, "x0").TryGetValueAsInteger(out var x0) || !bundle.GetArgument(1, "y0").TryGetValueAsInteger(out var y0) ||
            !bundle.GetArgument(2, "x1").TryGetValueAsInteger(out var x1) || !bundle.GetArgument(3, "y1").TryGetValueAsInteger(out var y1) ||
            !bundle.GetArgument(4, "z").TryGetValueAsInteger(out var z)) return DreamValue.Null;
        var list = bundle.ObjectTree.CreateList();
        Resized();
        x0 = System.Math.Max(1, x0); y0 = System.Math.Max(1, y0);
        if (z < 1 || z > _levels || x1 < x0 || y1 < y0) return new DreamValue(list);
        int cx1 = System.Math.Min(_w - 1, (x1 - 1) / CellSize), cy1 = System.Math.Min(_h - 1, (y1 - 1) / CellSize);
        for (var cy = (y0 - 1) / CellSize; cy <= cy1; cy++) {
            for (var cx = (x0 - 1) / CellSize; cx <= cx1; cx++) {
                var l = _cells[((z - 1) * _h + cy) * _w + cx];
                if (l == null) continue;
                foreach (var a in l)
                    if (a.Loc is DreamObjectTurf t && t.X >= x0 && t.X <= x1 && t.Y >= y0 && t.Y <= y1) list.AddValue(new DreamValue(a));
            }
        }
        return new DreamValue(list);
    }

    // The units on the tiles of a box into `into` (cleared first), as rm_grid_units lists them, with no DM list made (morale's
    // look round, RmMorale.cs); false when the grid is off.
    internal static bool UnitsIn(int x0, int y0, int x1, int y1, int z, List<DreamObjectMovable> into) {
        into.Clear();
        if (!On) return false;
        Resized();
        x0 = System.Math.Max(1, x0); y0 = System.Math.Max(1, y0);
        if (z < 1 || z > _levels || x1 < x0 || y1 < y0) return true;
        int cx1 = System.Math.Min(_w - 1, (x1 - 1) / CellSize), cy1 = System.Math.Min(_h - 1, (y1 - 1) / CellSize);
        for (var cy = (y0 - 1) / CellSize; cy <= cy1; cy++) {
            for (var cx = (x0 - 1) / CellSize; cx <= cx1; cx++) {
                var l = _cells[((z - 1) * _h + cy) * _w + cx];
                if (l == null) continue;
                foreach (var a in l)
                    if (a.Loc is DreamObjectTurf t && t.X >= x0 && t.X <= x1 && t.Y >= y0 && t.Y <= y1) into.Add(a);
            }
        }
        return true;
    }

    // what each caller (a player, one of its views) had in its box, with each unit's change counter then
    private sealed class Seen {
        public Dictionary<DreamObjectMovable, int> Units = new();
        public Dictionary<DreamObjectMovable, int> Next = new();
    }
    private static readonly System.Runtime.CompilerServices.ConditionalWeakTable<DreamObject, Seen[]> _seen = new();
    private static readonly List<DreamObjectMovable> _box = new();

    [DreamProc("rm_grid_changed")]
    [DreamProcParameter("who", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("slot", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("x0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y0", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("x1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("y1", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("z", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("mode", Type = DreamValueTypeFlag.Float)]
    public static DreamValue NativeProc_rm_grid_changed(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!On || !bundle.GetArgument(0, "who").TryGetValueAsDreamObject<DreamObject>(out var who) || who == null ||
            !bundle.GetArgument(1, "slot").TryGetValueAsInteger(out var slot) || slot < 0 || slot > 7 ||
            !bundle.GetArgument(2, "x0").TryGetValueAsInteger(out var x0) || !bundle.GetArgument(3, "y0").TryGetValueAsInteger(out var y0) ||
            !bundle.GetArgument(4, "x1").TryGetValueAsInteger(out var x1) || !bundle.GetArgument(5, "y1").TryGetValueAsInteger(out var y1) ||
            !bundle.GetArgument(6, "z").TryGetValueAsInteger(out var z)) return DreamValue.Null;
        if (!bundle.GetArgument(7, "mode").TryGetValueAsInteger(out var mode)) mode = 0;
        var seen = (_seen.GetValue(who, _ => new Seen[8])[slot] ??= new Seen());
        if (mode != 1)
            foreach (var a in seen.Units.Keys)
                if (a.Deleted) { mode = 1; break; }
        UnitsIn(x0, y0, x1, y1, z, _box);
        var tree = bundle.ObjectTree;
        var changed = tree.CreateList();
        var gone = tree.CreateList();
        var next = seen.Next;
        next.Clear();
        foreach (var a in _box) {
            if (a.Deleted) continue;
            var ver = a.RmChanges & 0xFFFFFF;   // rm_ver's number (RmVer.cs)
            next[a] = ver;
            if (mode == 1 || !seen.Units.TryGetValue(a, out var was) || was != ver || (mode == 2 && !Owns(who, a)))
                changed.AddValue(new DreamValue(a));
        }
        foreach (var a in seen.Units.Keys)
            if (!next.ContainsKey(a) && !a.Deleted) gone.AddValue(new DreamValue(a));
        seen.Next = seen.Units;
        seen.Units = next;
        var result = tree.CreateList();
        using (var cv = new DreamValue(changed)) result.AddValue(cv);   // the result holds them; this proc lets go
        using (var gv = new DreamValue(gone)) result.AddValue(gv);
        result.AddValue(new DreamValue(mode == 1 ? 1 : 0));
        return new DreamValue(result);
    }

    private static bool Owns(DreamObject who, DreamObjectMovable a) {
        if (!a.TryGetVariable("Owner", out var ao)) return false;
        using (ao) return ao.TryGetValueAsDreamObject<DreamObject>(out var o) && o == who;
    }

    [DreamProc("rm_grid_check")]
    public static DreamValue NativeProc_rm_grid_check(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!On) return new DreamValue(-1);
        Resized();
        var bad = 0;
        var seen = 0;
        foreach (var a in _atoms!.EnumerateAtoms(_type)) {
            if (a is not DreamObjectMovable m || m.Deleted) continue;
            if (m.Loc is DreamObjectTurf t && t.Cell.Movables.Contains(m)) {
                seen++;
                var i = Index(t.X, t.Y, t.Z);
                if (m.RmGridCell != i || i < 0 || _cells[i] == null || !_cells[i]!.Contains(m) || _held.Contains(m)) bad++;
            } else if (m.Loc is DreamObjectMovable) {
                if (!_held.Contains(m) || m.RmGridCell != HeldCell) bad++;
            } else if (m.RmGridCell != NoCell || _held.Contains(m)) {
                bad++;
            }
        }
        var listed = 0;
        foreach (var l in _cells) if (l != null) listed += l.Count;
        if (listed != seen) bad += System.Math.Abs(listed - seen);   // entries for units no longer on a tile
        if (listed != _units) bad += System.Math.Abs(listed - _units);
        return new DreamValue(bad);
    }

    [DreamProc("rm_grid_stats")]
    public static DreamValue NativeProc_rm_grid_stats(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        return new DreamValue($"units {_units} cells {_occupied} held {_held.Count} foe_checked {_foeChecked} foe_differed {_foeDiffered}");
    }
}
