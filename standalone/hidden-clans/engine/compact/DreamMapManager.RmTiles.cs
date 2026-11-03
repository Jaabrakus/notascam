// Remastered sleeping tiles (map memory, planning/MAP_MEMORY.md; the COMPACT patch, engine/compact/compact_patch.py).
// A tile whose turf nothing but its cell holds, with no things on it, no tag and only plain values of its own, can sleep:
// its turf object, cell, things list, area-set entry and own-vars table are freed, and what they held is kept in a
// 128x128 block of its level. Any read of the tile wakes it first, with the same ref, type, appearance, density,
// area and own values, so DM code cannot tell. Blocks are made when their first tile sleeps and freed with their last.
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DMCompiler.Json;
using OpenDreamShared.Dream;
using Robust.Shared.Map;
using Robust.Shared.Maths;
using Robust.Shared.GameObjects;
using Robust.Shared.IoC;
using Level = OpenDreamRuntime.Map.IDreamMapManager.Level;
using Cell = OpenDreamRuntime.Map.IDreamMapManager.Cell;

namespace OpenDreamRuntime.Map;

public sealed partial class DreamMapManager {
    public const int RmBlock = 128;

    // What the turfs of one block's sleeping tiles held, by tile (row-major in the block): a kind, an index into the
    // block's own table of (type, appearance, area, density); 0 for an awake tile. Types and areas index the world's
    // tables, appearances the block's own (which holds them strongly: appearances are weakly registered). Own values are
    // kept only for the tiles that have some. The ref is the tile's place (turf refs by position). 2 bytes a tile; 15
    // before engine GG (load-asleep-1030), which kept the ref and the four indexes per tile.
    public readonly record struct RmKind(ushort Def, ushort App, ushort Area, bool Dense);

    public sealed class RmSleepBlock {
        public readonly ushort[] Kind = new ushort[RmBlock * RmBlock];
        public readonly List<RmKind> Kinds = new() { default };
        public readonly Dictionary<RmKind, ushort> KindIndex = new();
        public readonly List<ImmutableAppearance> Apps = new();
        public readonly Dictionary<ImmutableAppearance, ushort> AppIndex = new();
        public Dictionary<int, KeyValuePair<string, DreamValue>[]>? Vars;   // by tile, only the tiles that have some
        public int Sleeping;

        private ushort AppOf(ImmutableAppearance a) {
            if (AppIndex.TryGetValue(a, out var i)) return i;
            i = (ushort)Apps.Count;
            Apps.Add(a);
            AppIndex[a] = i;
            return i;
        }

        public ushort KindOf(ushort def, ImmutableAppearance app, ushort area, bool dense) {
            if (Kinds.Count >= ushort.MaxValue || Apps.Count >= ushort.MaxValue) Compact();
            var k = new RmKind(def, AppOf(app), area, dense);
            if (KindIndex.TryGetValue(k, out var i)) return i;
            i = (ushort)Kinds.Count;
            Kinds.Add(k);
            KindIndex[k] = i;
            return i;
        }

        // The tables rebuilt from the tiles asleep now: kinds and appearances that woken tiles or an area's look changes
        // left behind go (at most 16,384 tiles a block, so the rebuilt tables always fit).
        private void Compact() {
            var oldKinds = Kinds.ToArray();
            var oldApps = Apps.ToArray();
            Kinds.Clear();
            Kinds.Add(default);
            KindIndex.Clear();
            Apps.Clear();
            AppIndex.Clear();
            var map = new Dictionary<ushort, ushort>();
            for (var t = 0; t < Kind.Length; t++) {
                var o = Kind[t];
                if (o == 0) continue;
                if (!map.TryGetValue(o, out var n)) {
                    var k = oldKinds[o] with { App = AppOf(oldApps[oldKinds[o].App]) };
                    if (!KindIndex.TryGetValue(k, out n)) {
                        n = (ushort)Kinds.Count;
                        Kinds.Add(k);
                        KindIndex[k] = n;
                    }
                    map[o] = n;
                }
                Kind[t] = n;
            }
        }

        public KeyValuePair<string, DreamValue>[]? VarsAt(int i) => Vars != null && Vars.TryGetValue(i, out var v) ? v : null;

        // the kind array (16 bytes of header and length), the tables (a kind or an appearance: a list slot and a
        // dictionary entry), the own-value entries
        public long Bytes => RmBlock * RmBlock * 2 + 16 + 96 + Kinds.Count * (8 + 24) + Apps.Count * (8 + 24) + (Vars?.Count ?? 0) * 24;
    }

    // the world's definitions and areas, by index (definitions include the map's per-tile ones for var-edited tiles)
    private readonly List<DreamObjectDefinition> _rmDefs = new() { null! };
    private readonly Dictionary<DreamObjectDefinition, ushort> _rmDefIndex = new();
    private readonly List<DreamObjectArea> _rmAreas = new();
    private readonly Dictionary<DreamObjectArea, ushort> _rmAreaIndex = new();

    private bool RmIndexes(DreamObjectDefinition def, DreamObjectArea area, out ushort d, out ushort a) {
        a = 0;
        if (!_rmDefIndex.TryGetValue(def, out d)) {
            if (_rmDefs.Count >= ushort.MaxValue) return false;
            d = (ushort)_rmDefs.Count;
            _rmDefs.Add(def);
            _rmDefIndex[def] = d;
        }
        if (!_rmAreaIndex.TryGetValue(area, out a)) {
            if (_rmAreas.Count >= ushort.MaxValue) return false;
            a = (ushort)_rmAreas.Count;
            _rmAreas.Add(area);
            _rmAreaIndex[area] = a;
        }
        return true;
    }

    [Dependency] private DreamRefManager _rmRefs = default!;
    public long RmSleepingTiles, RmWokenTotal, RmSleptTotal, RmVarArrays, RmVarEntries, RmBlockBytesHeld;
    public int RmBlocksHeld;

    // --- Turf refs by position (engine GG, load-asleep-1030). The map makes its turfs a level at a time, x then y, and a
    // turf's ref was the count of turfs made before it, so every map turf's ref is already ((z-1)*W + x)*H + y (x, y from
    // 0; W, H the map's size when its first level was made). The ref manager now works it out instead of keeping a slot
    // per tile (32 MB), the map no longer keeps a slot -> tile index (17 MB) or a ref per sleeping tile (16 MB), and no
    // ref changes. A tile only sleeps if its turf's ref is the one its place gives (a resized world's turfs never do).
    // RM_POS_REFS=0 in the server's environment keeps the slots, and then nothing sleeps. ---
    internal bool RmSleepOn => Environment.GetEnvironmentVariable("RM_COMPACT_TILES") != "0" &&
                               Environment.GetEnvironmentVariable("RM_POS_REFS") != "0" &&
                               _objectTree.TryGetGlobalProc("rm_tiles_sleep_box", out _);

    // LoadMaps, before any level is made
    private void RmRefsByPosition() {
        if (_rmRefs.RmTurfRefsOn || Levels > 0 || !RmSleepOn) return;
        _rmRefs.RmTurfRefsByPosition(RmTurfAt, () => Levels * _rmRefs.RmPosW * _rmRefs.RmPosH, Size.X, Size.Y);
    }

    private uint RmTurfRef(int z, int x, int y) =>
        (uint)RefType.DreamObjectTurf | (uint)(((z - 1) * _rmRefs.RmPosW + x) * _rmRefs.RmPosH + y);

    // a turf ref's tile (asleep: woken), for the ref manager's lookups
    private DreamObject? RmTurfAt(int id) {
        int w = _rmRefs.RmPosW, h = _rmRefs.RmPosH;
        if (id < 0 || w <= 0 || h <= 0) return null;
        var z = id / (w * h) + 1;
        var rest = id % (w * h);
        int x = rest / h, y = rest % h;
        if (z > Levels || x >= Size.X || y >= Size.Y) return null;
        var level = _levels[z - 1];
        return (level.Cells[x, y] ?? RmWake(level, x, y)).Turf;
    }

    // The tile at x, y (from 0) of a level, asleep: made awake again.
    internal Cell RmWake(Level level, int x, int y) {
        var bi = y / RmBlock * level.RmBlocksW + x / RmBlock;
        var b = level.RmBlocks?[bi] ?? throw new InvalidOperationException($"no tile at {x + 1},{y + 1},{level.Z}");
        var i = y % RmBlock * RmBlock + x % RmBlock;
        if (b.Kind[i] == 0) throw new InvalidOperationException($"no sleeping tile at {x + 1},{y + 1},{level.Z}");
        var kind = b.Kinds[b.Kind[i]];
        var def = _rmDefs[kind.Def];
        _rmRefs.RmNextTurfRef = RmTurfRef(level.Z, x, y);
        var turf = new DreamObjectTurf(def, x + 1, y + 1, level.Z);
        _rmRefs.RmNextTurfRef = 0;
        turf.Appearance = b.Apps[kind.App];
        turf.IsDense = kind.Dense;
        KeyValuePair<string, DreamValue>[]? vars = null;
        if (b.Vars != null && b.Vars.Remove(i, out vars)) {
            RmVarArrays--;
            RmVarEntries -= vars.Length;
        }
        turf.RmGiveVars(vars);
        var area = _rmAreas[kind.Area];
        var cell = new Cell(area, turf, true);
        turf.Cell = cell;
        level.Cells[x, y] = cell;
        turf.DecRef();   // the cell holds it now
        area.RmSleeping--;
        RmBlockBytesHeld -= b.Bytes;
        b.Kind[i] = 0;
        RmBlockBytesHeld += b.Bytes;
        if (--b.Sleeping == 0) {
            level.RmBlocks![bi] = null;
            RmBlocksHeld--;
            RmBlockBytesHeld -= b.Bytes;
        }
        RmSleepingTiles--;
        RmWokenTotal++;
        if (_rmLoadDone && ++_rmWokenSinceSleep == 200_000) RmLogMassWake("200,000 tiles one at a time since the last sleep");
        return cell;
    }

    private void RmPrepare(Level level) {
        if (level.RmBlocks == null) {
            level.RmBlocksW = (Size.X + RmBlock - 1) / RmBlock;
            level.RmBlocks = new RmSleepBlock?[level.RmBlocksW * ((Size.Y + RmBlock - 1) / RmBlock)];
        }
    }

    // Puts the tiles of a box (from 1, inclusive) to sleep; with dry, only counts. reasons[k]: tiles that stay awake for
    // reason k (1-6 DreamObjectTurf.RmSleepBlock, 7 things on it, 8 the index tables full or the turf's ref not its
    // place's, 9 a watched var written since the game last took the marks: RmWatch keeps the object); reasons[0]: tiles
    // already asleep. Without turf refs by position nothing sleeps.
    public int RmSleep(int z, int x0, int y0, int x1, int y1, bool dry, long[] reasons) {
        if (z < 1 || z > Levels) return 0;
        if (!dry && !_rmRefs.RmTurfRefsOn) return 0;
        x0 = Math.Max(1, x0);
        y0 = Math.Max(1, y0);
        x1 = Math.Min(Size.X, x1);
        y1 = Math.Min(Size.Y, y1);
        var level = _levels[z - 1];
        if (!dry) RmPrepare(level);
        var n = 0;
        for (var y = y0 - 1; y < y1; y++) {
            for (var x = x0 - 1; x < x1; x++) {
                var cell = level.Cells[x, y];
                if (cell == null) {
                    reasons[0]++;
                    continue;
                }
                if (cell.Movables.Count > 0) {
                    reasons[7]++;
                    continue;
                }
                var turf = cell.Turf;
                var why = turf.RmSleepBlock();
                if (why == 0 && global::OpenDreamRuntime.Procs.Native.RmWatch.Holds(turf)) why = 9;
                if (why != 0) {
                    reasons[why]++;
                    continue;
                }
                if (dry) {
                    n++;
                    continue;
                }
                if (turf.RefId != RmTurfRef(z, x, y) || !RmIndexes(turf.ObjectDefinition, cell.Area, out var di, out var ai)) {
                    reasons[8]++;
                    continue;
                }
                n++;
                var bi = y / RmBlock * level.RmBlocksW + x / RmBlock;
                var b = level.RmBlocks![bi];
                if (b == null) {
                    b = level.RmBlocks[bi] = new RmSleepBlock();
                    RmBlocksHeld++;
                    RmBlockBytesHeld += b.Bytes;
                }
                var i = y % RmBlock * RmBlock + x % RmBlock;
                RmBlockBytesHeld -= b.Bytes;
                b.Kind[i] = b.KindOf(di, turf.Appearance, ai, turf.IsDense);
                var vars = turf.RmSleep();
                if (vars != null) {
                    RmVarArrays++;
                    RmVarEntries += vars.Length;
                    (b.Vars ??= new())[i] = vars;
                }
                b.Sleeping++;
                RmBlockBytesHeld += b.Bytes;
                cell.Area._rmTurfs.Remove(turf);
                cell.Area.RmSleeping++;
                level.Cells[x, y] = null;
            }
        }
        if (!dry) {
            RmSleepingTiles += n;
            RmSleptTotal += n;
            if (n > 0) _rmWokenSinceSleep = 0;
        }
        return n;
    }

    // Wakes the sleeping tiles of a box (from 1, inclusive); returns how many.
    public int RmWakeBox(int z, int x0, int y0, int x1, int y1) {
        if (z < 1 || z > Levels) return 0;
        var level = _levels[z - 1];
        if (level.RmBlocks == null) return 0;
        var n = 0;
        for (var y = Math.Max(1, y0) - 1; y < Math.Min(Size.Y, y1); y++) {
            for (var x = Math.Max(1, x0) - 1; x < Math.Min(Size.X, x1); x++) {
                if (level.Cells[x, y] != null) continue;
                RmWake(level, x, y);
                n++;
            }
        }
        return n;
    }

    // Is the tile at x, y, z (from 1) asleep? Wakes nothing (rm_memory_report and the census count with it).
    public bool RmAsleep(int x, int y, int z) =>
        z >= 1 && z <= Levels && x >= 1 && x <= Size.X && y >= 1 && y <= Size.Y && _levels[z - 1].Cells[x - 1, y - 1] == null;

    public int RmCountSleeping(int z, int x0, int y0, int x1, int y1) {
        if (z < 1 || z > Levels) return 0;
        var level = _levels[z - 1];
        var n = 0;
        for (var y = Math.Max(1, y0) - 1; y < Math.Min(Size.Y, y1); y++)
            for (var x = Math.Max(1, x0) - 1; x < Math.Min(Size.X, x1); x++)
                if (level.Cells[x, y] == null) n++;
        return n;
    }

    public void RmWakeArea(DreamObjectArea area) {
        if (area.RmSleeping <= 0) return;
        RmLogMassWake($"area {area.ObjectDefinition.Type}'s {area.RmSleeping} sleeping tiles");
        foreach (var level in _levels) {
            if (level.RmBlocks == null) continue;
            for (var bi = 0; bi < level.RmBlocks.Length && area.RmSleeping > 0; bi++) {
                var b = level.RmBlocks[bi];
                if (b == null) continue;
                var bx = bi % level.RmBlocksW * RmBlock;
                var by = bi / level.RmBlocksW * RmBlock;
                if (!_rmAreaIndex.TryGetValue(area, out var ai)) return;
                for (var i = 0; i < RmBlock * RmBlock; i++) {
                    if (b.Kind[i] == 0 || b.Kinds[b.Kind[i]].Area != ai) continue;
                    RmWake(level, bx + i % RmBlock, by + i / RmBlock);
                    if (level.RmBlocks[bi] == null) break;
                }
            }
        }
    }

    public void RmWakeAll() {
        if (RmSleepingTiles <= 0) return;
        RmLogMassWake("every sleeping tile");
        foreach (var level in _levels) {
            if (level.RmBlocks == null) continue;
            for (var bi = 0; bi < level.RmBlocks.Length; bi++) {
                var b = level.RmBlocks[bi];
                if (b == null) continue;
                var bx = bi % level.RmBlocksW * RmBlock;
                var by = bi / level.RmBlocksW * RmBlock;
                for (var i = 0; i < RmBlock * RmBlock; i++) {
                    if (b.Kind[i] == 0) continue;
                    RmWake(level, bx + i % RmBlock, by + i / RmBlock);
                    if (level.RmBlocks[bi] == null) break;
                }
            }
            level.RmBlocks = null;
        }
    }

    // SetAreaAppearance for an area's sleeping tiles: each record's appearance changed as an awake turf's would be (the
    // area's old appearance out of its overlays, the new one in; one new appearance for each old one) and its client tile
    // queued, waking none (an area that set its look in New() woke every tile of it: the whole map at load).
    internal void RmAreaAppearanceAsleep(DreamObjectArea area, ImmutableAppearance oldAreaAppearance, Dictionary<ImmutableAppearance, ImmutableAppearance> oldToNew) {
        if (area.RmSleeping <= 0 || !_rmAreaIndex.TryGetValue(area, out var ai)) return;
        foreach (var level in _levels) {
            if (level.RmBlocks == null) continue;
            for (var bi = 0; bi < level.RmBlocks.Length; bi++) {
                var b = level.RmBlocks[bi];
                if (b == null) continue;
                var bx = bi % level.RmBlocksW * RmBlock;
                var by = bi / level.RmBlocksW * RmBlock;
                for (var i = 0; i < RmBlock * RmBlock; i++) {
                    if (b.Kind[i] == 0) continue;
                    var kind = b.Kinds[b.Kind[i]];
                    if (kind.Area != ai) continue;
                    var old = b.Apps[kind.App];
                    if (!oldToNew.TryGetValue(old, out var now)) {
                        var mutable = old.ToMutable();
                        mutable.Overlays.Remove(oldAreaAppearance);
                        mutable.Overlays.Add(area.Appearance);
                        now = _appearanceSystem.AddAppearance(mutable);
                        oldToNew.Add(old, now);
                    }
                    RmBlockBytesHeld -= b.Bytes;
                    b.Kind[i] = b.KindOf(kind.Def, now, kind.Area, kind.Dense);
                    RmBlockBytesHeld += b.Bytes;
                    level.QueuedTileUpdates.Add((new Vector2i(bx + i % RmBlock + 1, by + i / RmBlock + 1), new Tile((int)now.MustGetId())));
                }
            }
        }
    }

    // DreamObjectArea's coordinate cache: its lowest sleeping tile (z, then y, then x) where lower than the awake ones'.
    internal void RmLowestAsleep(DreamObjectArea area, ref int? cx, ref int? cy, ref int? cz) {
        if (!_rmAreaIndex.TryGetValue(area, out var ai)) return;
        foreach (var level in _levels) {
            if (level.RmBlocks == null || (cz != null && level.Z > cz)) continue;
            for (var bi = 0; bi < level.RmBlocks.Length; bi++) {
                var b = level.RmBlocks[bi];
                if (b == null) continue;
                var bx = bi % level.RmBlocksW * RmBlock;
                var by = bi / level.RmBlocksW * RmBlock;
                for (var i = 0; i < RmBlock * RmBlock; i++) {
                    if (b.Kind[i] == 0 || b.Kinds[b.Kind[i]].Area != ai) continue;
                    int x = bx + i % RmBlock + 1, y = by + i / RmBlock + 1;
                    if (cx != null && (level.Z > cz || (level.Z == cz && y * Size.X + x >= cy * Size.X + cx))) continue;
                    cx = x;
                    cy = y;
                    cz = level.Z;
                }
            }
        }
    }

    // How many times a whole area or every tile was woken (logged, the first few: a wake like that during the load brings
    // the load peak back).
    private int _rmMassWakes, _rmWokenSinceSleep;
    private bool _rmLoadDone;

    private void RmLogMassWake(string what) {
        if (_rmMassWakes++ >= 3) return;
        Robust.Shared.Log.Logger.GetSawmill("rmtiles").Info($"{what} woken ({RmSleepingTiles} tiles asleep): {Environment.StackTrace}");
    }

    // --- Built asleep at load (load-asleep, 2026-10-30, reports/load-asleep-1030). LoadMaps made every level's tiles awake
    // (about 4 million turfs on the user's world: the server's 2.5-2.7 GB load peak) and the game's load pass put them to
    // sleep only once the world had started. Now each level is made, given its map cells and put to sleep before the next
    // is made, and InitializeAtoms wakes one level at a time for its turfs' New() (in the same order) and puts it back. Each
    // turf keeps the ref it was made with, so the game sees the same turfs, refs, types, values and order of New() calls;
    // only the order of an area's turf set changes, as with any sleeping. On when the game uses the sleeping tiles (it
    // declares rm_tiles_sleep_box); RM_LOAD_ASLEEP=0, RM_LOAD_SLEEP=0 (no load pass) or RM_COMPACT_TILES=0 in the server's
    // environment loads them awake, as before. ---
    private bool? _rmLoadAsleep;
    public long RmLoadSlept, RmLoadNewSlept;   // tiles put to sleep after the map was loaded, after New()

    internal bool RmLoadAsleep => _rmLoadAsleep ??= Environment.GetEnvironmentVariable("RM_LOAD_ASLEEP") != "0" &&
                                                     Environment.GetEnvironmentVariable("RM_LOAD_SLEEP") != "0" &&
                                                     Environment.GetEnvironmentVariable("RM_COMPACT_TILES") != "0" &&
                                                     _objectTree.TryGetGlobalProc("rm_tiles_sleep_box", out _);

    // LoadMaps, a level at a time: made (awake, the default turf set as SetZLevels does), its map blocks loaded, asleep.
    private void RmLoadLevelsAsleep(List<DreamMapJson>? maps, int maxZ) {
        if (maps != null) _jsonMaps = maps;
        var reasons = new long[10];
        for (var z = Levels + 1; z <= maxZ; z++) {
            SetZLevels(z);
            if (maps != null) {
                foreach (var map in maps) {
                    foreach (MapBlockJson block in map.Blocks) {
                        if (block.Z == z) LoadMapAreasAndTurfs(block, map.CellDefinitions);
                    }
                }
            }
            RmLoadSlept += RmSleep(z, 1, 1, Size.X, Size.Y, false, reasons);
            RmLoadCollect(z == maxZ);
        }
        if (maps != null) {   // blocks above the last level would have been loaded too (none: maxZ covers every block)
            foreach (var map in maps) {
                foreach (MapBlockJson block in map.Blocks) {
                    if (block.Z > maxZ) LoadMapAreasAndTurfs(block, map.CellDefinitions);
                }
            }
        }
    }

    // Between levels: the turfs a level made (awake for its map, or for its New()) and put to sleep are dead in the old
    // generation; a full collection lets the next level use their room (swept), and after the last one hands it back
    // (compacted). No player is in yet, so the load stalls, not the game. Without it the load still peaked at ~2 GB.
    private double _rmLoadGcMs;

    private void RmLoadCollect(bool compact) {
        var t0 = System.Diagnostics.Stopwatch.GetTimestamp();
        if (compact) System.Runtime.GCSettings.LargeObjectHeapCompactionMode = System.Runtime.GCLargeObjectHeapCompactionMode.CompactOnce;
        GC.Collect(2, GCCollectionMode.Forced, true, compact);
        _rmLoadGcMs += System.Diagnostics.Stopwatch.GetElapsedTime(t0).TotalMilliseconds;
    }

    // The area of the tile at x, y (from 0) of a level, awake or asleep (InitializeAtoms' areas' New()); wakes nothing.
    private DreamObjectArea RmAreaAt(Level level, int x, int y) {
        var cell = level.Cells[x, y];
        if (cell != null) return cell.Area;
        var b = level.RmBlocks![y / RmBlock * level.RmBlocksW + x / RmBlock]!;
        return _rmAreas[b.Kinds[b.Kind[y % RmBlock * RmBlock + x % RmBlock]].Area];
    }

    // InitializeAtoms: a level's turfs have had New(); back to sleep, those that can.
    private void RmSleepAfterNew(int z) {
        if (!RmLoadAsleep) return;
        RmLoadNewSlept += RmSleep(z, 1, 1, Size.X, Size.Y, false, new long[10]);
        RmLoadCollect(z == Levels);
        if (z != Levels) return;
        _rmLoadDone = true;
        Robust.Shared.Log.Logger.GetSawmill("rmtiles").Info($"built asleep at load: {RmLoadSlept} tiles asleep after the map, " +
            $"{RmLoadNewSlept} after New(), {RmSleepingTiles} asleep now; {_rmLoadGcMs:0} ms collecting between levels");
    }

    // A sleeping tile read without waking it: what its turf would answer for a var, its type, its density (the reach
    // map's build reads every tile of every level; waking them all would bring the load peak back).
    public readonly struct RmTileView {
        private readonly DreamMapManager _map;
        private readonly DreamObjectDefinition _def;
        private readonly ImmutableAppearance _app;
        private readonly KeyValuePair<string, DreamValue>[]? _vars;
        public readonly bool IsDense;
        public readonly int Z;

        internal RmTileView(DreamMapManager map, DreamObjectDefinition def, ImmutableAppearance app, KeyValuePair<string, DreamValue>[]? vars, bool dense, int z) {
            _map = map;
            _def = def;
            _app = app;
            _vars = vars;
            IsDense = dense;
            Z = z;
        }

        public bool IsSubtypeOf(TreeEntry type) => _def.IsSubtypeOf(type);

        // as DreamObjectTurf.TryGetVar for the vars a sleeping turf can hold: density, then the appearance's vars, then its
        // own values, then its type's. Plain values only (a sleeping tile holds no objects), so nothing to dispose.
        public bool TryGetVar(string name, out DreamValue value) {
            if (name == "density") {
                value = IsDense ? DreamValue.True : DreamValue.False;
                return true;
            }
            if (_map._atomManager.IsValidAppearanceVar(name)) {
                value = _map._atomManager.GetAppearanceVar(_app, name);
                return true;
            }
            if (_vars != null) {
                foreach (var kv in _vars) {
                    if (kv.Key != name) continue;
                    value = kv.Value;
                    return true;
                }
            }
            return _def.Variables.TryGetValue(name, out value);
        }
    }

    // The sleeping tile at x, y, z (from 1) as a view; false when it is awake (or off the map). Wakes nothing.
    public bool RmPeek(int x, int y, int z, out RmTileView view) {
        view = default;
        if (z < 1 || z > Levels || x < 1 || x > Size.X || y < 1 || y > Size.Y) return false;
        var level = _levels[z - 1];
        if (level.Cells[x - 1, y - 1] != null || level.RmBlocks == null) return false;
        var b = level.RmBlocks[(y - 1) / RmBlock * level.RmBlocksW + (x - 1) / RmBlock];
        if (b == null) return false;
        var i = (y - 1) % RmBlock * RmBlock + (x - 1) % RmBlock;
        if (b.Kind[i] == 0) return false;
        var kind = b.Kinds[b.Kind[i]];
        view = new RmTileView(this, _rmDefs[kind.Def], b.Apps[kind.App], b.VarsAt(i), kind.Dense, z);
        return true;
    }

    // what the sleeping state takes: the blocks and their tables, the own-value arrays (24 bytes of header, 24 an entry)
    public long RmBytes => RmBlockBytesHeld + RmVarArrays * 24 + RmVarEntries * 24;

    // --- The 2D map's tiles only near players (engine GG, load-asleep-1030). OpenDream gives every turf a Robust tile so
    // the hidden 2D map can draw it: all 15,876 chunks of the four levels, ~72 MB in the server and ~130 MB in the game
    // window, which keeps a copy. The 3D view never reads them. But the stock window finds the player's mob through the
    // tile under it (DreamViewOverlay): with no tile there its mob verbs, so the skin's macros and buttons, do nothing.
    // So tiles are kept only in the 3x3 chunks (16x16 tiles each) around each connected player's mob: filled from the
    // turfs (asleep or awake, waking none) when it comes near, emptied when it leaves, and the mob put on its level's grid
    // again when its chunk fills. Robust deletes a grid whose last chunk goes, so that is turned off. RM_NEAR_TILES=0 in
    // the server's environment keeps every tile, as before. ---
    private const int RmChunk = 16;
    private bool? _rmNearTiles;
    private HashSet<(int Z, int X, int Y)> _rmLive = new(), _rmWant = new();
    private DreamManager? _rmDream;
    private SharedTransformSystem? _rmTransform;

    internal bool RmNearTiles => _rmNearTiles ??= Environment.GetEnvironmentVariable("RM_NEAR_TILES") != "0" && RmSleepOn;

    // LoadMaps, before any level is made
    private void RmNearTilesStart() {
        if (RmNearTiles)
            IoCManager.Resolve<Robust.Shared.Configuration.IConfigurationManager>().SetCVar(Robust.Shared.CVars.GameDeleteEmptyGrids, false);
    }

    private static DreamObjectTurf? RmTurfUnder(DreamObjectMob? mob) {
        if (mob == null || mob.Deleted) return null;
        var loc = mob.Loc;
        for (var i = 0; i < 16 && loc is DreamObjectMovable m; i++) loc = m.Loc;
        return loc as DreamObjectTurf;
    }

    // UpdateTiles, every tick
    private void RmUpdateNearTiles() {
        _rmDream ??= IoCManager.Resolve<DreamManager>();
        _rmWant.Clear();
        foreach (var connection in _rmDream.Connections) {
            if (connection.Session == null) continue;   // a browser player (the web link): no Robust tiles, no window
            if (RmTurfUnder(connection.Mob) is not { } t) continue;
            for (var dx = -1; dx <= 1; dx++)
                for (var dy = -1; dy <= 1; dy++)
                    _rmWant.Add((t.Z, (t.X >> 4) + dx, (t.Y >> 4) + dy));
        }
        var filled = false;
        foreach (var level in _levels) {
            var z = level.Z;
            List<(Vector2i, Tile)>? tiles = null;
            foreach (var c in _rmLive)
                if (c.Z == z && !_rmWant.Contains(c)) RmChunkTiles(level, c, false, tiles ??= new());
            foreach (var c in _rmWant) {
                if (c.Z != z || _rmLive.Contains(c)) continue;
                RmChunkTiles(level, c, true, tiles ??= new());
                filled = true;
            }
            foreach (var u in level.QueuedTileUpdates) {   // changes inside the chunks that stay (a filled one read them already)
                var c = (z, u.Item1.X >> 4, u.Item1.Y >> 4);
                if (_rmLive.Contains(c) && _rmWant.Contains(c)) (tiles ??= new()).Add(u);
            }
            level.QueuedTileUpdates.Clear();
            if (level.QueuedTileUpdates.Capacity > 4096) level.QueuedTileUpdates.TrimExcess();
            if (tiles != null) _mapSystem.SetTiles(level.Grid, tiles);
        }
        (_rmLive, _rmWant) = (_rmWant, _rmLive);
        if (filled) RmReseatMobs();
    }

    private void RmChunkTiles(Level level, (int Z, int X, int Y) c, bool fill, List<(Vector2i, Tile)> tiles) {
        for (var x = Math.Max(1, c.X * RmChunk); x < c.X * RmChunk + RmChunk && x <= Size.X; x++) {
            for (var y = Math.Max(1, c.Y * RmChunk); y < c.Y * RmChunk + RmChunk && y <= Size.Y; y++) {
                var tile = Tile.Empty;
                if (fill) {
                    var app = level.Cells[x - 1, y - 1]?.Turf.Appearance ?? RmAppAsleep(level, x - 1, y - 1);
                    if (app != null) tile = new Tile((int)app.MustGetId());
                }
                tiles.Add((new Vector2i(x, y), tile));
            }
        }
    }

    // a sleeping tile's appearance (x, y from 0), or null
    private ImmutableAppearance? RmAppAsleep(Level level, int x, int y) {
        var b = level.RmBlocks?[y / RmBlock * level.RmBlocksW + x / RmBlock];
        if (b == null) return null;
        var k = b.Kind[y % RmBlock * RmBlock + x % RmBlock];
        return k == 0 ? null : b.Apps[b.Kinds[k].App];
    }

    // A mob that moved where no tile was is parented to the map, not its level's grid (Robust: no grid there); once
    // its chunk has tiles, put it on the grid again, as a move would.
    private void RmReseatMobs() {
        _rmTransform ??= _entitySystemManager.GetEntitySystem<SharedTransformSystem>();
        foreach (var connection in _rmDream!.Connections) {
            if (connection.Session == null) continue;
            var mob = connection.Mob;
            if (mob == null || mob.Deleted || mob.Loc is not DreamObjectTurf t) continue;
            _rmTransform.SetParent(mob.Entity, GetZLevelEntity(t.Z));
            _rmTransform.SetWorldPosition(mob.Entity, new System.Numerics.Vector2(t.X, t.Y));
        }
    }
}

// A level's cells (engine G5, load-asleep-1030): Cell[,] was 8 bytes for every tile of every level (30.5 MB for four
// 1000x1000 levels), almost all of them null once the map sleeps. Same indexer, but the cells are kept in 16x16-tile
// blocks that exist only while one of their tiles is awake. Reads off the level's edge give null (Cell[,] threw; every
// caller checks the bounds first).
public sealed class RmCells {
    private const int Shift = 4, Mask = 15;
    private readonly IDreamMapManager.Cell?[]?[] _blocks;
    private readonly short[] _counts;
    private readonly int _bw;
    public readonly int Width, Height;

    public RmCells(int width, int height) {
        Width = width;
        Height = height;
        _bw = (width + Mask) >> Shift;
        var n = _bw * ((height + Mask) >> Shift);
        _blocks = new IDreamMapManager.Cell?[]?[n];
        _counts = new short[n];
    }

    public IDreamMapManager.Cell? this[int x, int y] {
        get {
            if ((uint)x >= (uint)Width || (uint)y >= (uint)Height) return null;
            var b = _blocks[(y >> Shift) * _bw + (x >> Shift)];
            return b?[((y & Mask) << Shift) | (x & Mask)];
        }
        set {
            if ((uint)x >= (uint)Width || (uint)y >= (uint)Height) throw new IndexOutOfRangeException($"cell {x},{y} off a {Width}x{Height} level");
            var bi = (y >> Shift) * _bw + (x >> Shift);
            var i = ((y & Mask) << Shift) | (x & Mask);
            var b = _blocks[bi];
            if (b == null) {
                if (value == null) return;
                b = _blocks[bi] = new IDreamMapManager.Cell?[1 << (2 * Shift)];
            }
            var was = b[i];
            b[i] = value;
            if (was == null && value != null) _counts[bi]++;
            else if (was != null && value == null && --_counts[bi] == 0) _blocks[bi] = null;
        }
    }

    // blocks held now (memory reports)
    public int BlocksHeld {
        get {
            var n = 0;
            foreach (var b in _blocks) if (b != null) n++;
            return n;
        }
    }
}
