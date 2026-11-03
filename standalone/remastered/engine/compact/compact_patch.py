# Remastered sleeping tiles (map memory, planning/MAP_MEMORY.md; native version 10): exec'd by tools/build_runtime.py's
# COMPACT block (--compact) after the memory patch, with RmTiles.cs in the native procs. A tile whose turf nothing but its cell holds (no things on it, no tag,
# only plain values of its own: numbers, text, types, files) can sleep as a packed record in a 128x128 block of its
# level: its turf object, cell, things list, area-set entry and own-vars table are freed. Any engine read of the tile
# (TryGetCellAt, so locate/block/range/view/get_step/route search, a ref, world's turfs, an area's turfs) wakes it
# first, with the same ref, values, appearance and area, so DM code never sees a difference.
# FILES: path under src -> [(old, new, count)], applied in order; NEW: path under src -> file to copy in.

FILES = {
    'DreamValue.cs': [
        ('    public readonly DreamValueType Type;\n',
         '    public readonly DreamValueType Type;\n'
         '    internal bool RmIsTrueNull => Type == DreamValueType.DreamObject && _refValue == null;   // Remastered sleeping tiles\n'
         '\n'
         '    // Remastered (engine M): exactly the same value, as a read would give it: a number bit for bit (-0 is not 0),\n'
         '    // text by its letters, anything else the same reference (a deleted object is not null here, as a read keeps it)\n'
         '    internal readonly bool RmSame(DreamValue other) {\n'
         '        if (Type != other.Type) return false;\n'
         '        if (Type == DreamValueType.Float) return BitConverter.SingleToInt32Bits(_floatValue) == BitConverter.SingleToInt32Bits(other._floatValue);\n'
         '        if (_refValue is string s) return other._refValue is string o && string.Equals(s, o, StringComparison.Ordinal);\n'
         '        return ReferenceEquals(_refValue, other._refValue);\n'
         '    }\n', 1),
    ],
    'Objects/DreamObject.cs': [
        # engine M (load-asleep-1030): an object's first own-vars table has room for 3 (Dictionary's smallest), not 7: of
        # 62,742 turf tables at 30 players the mean held 2.1 entries in 7 slots; bigger tables grow as before.
        # M2: a write of exactly the type's default to a name the object holds no entry for stores nothing (a read gives
        # that default either way). Without it the trim's dropped entries came back (~107,000 a minute at 100 players),
        # each one moving the change counters (the u5-hud session); RmSkipped tells SetVariable it was no change.
        ('        Variables ??= new(4);\n        value.IncRef();\n        if (Variables.TryGetValue(name, out var oldValue))\n            oldValue.DecRef();\n        Variables[name] = value;\n',
         '        if (Variables != null && Variables.TryGetValue(name, out var oldValue)) {\n'
         '            value.IncRef();\n'
         '            oldValue.DecRef();\n'
         '            Variables[name] = value;\n'
         '            return;\n'
         '        }\n'
         '        if (ObjectDefinition.Variables.TryGetValue(name, out var rmDef) && value.RmSame(rmDef)) {   // Remastered (engine M2): the default, kept by the type\n'
         '            RmSkipped = this;\n'
         '            RmSkippedName = name;\n'
         '            return;\n'
         '        }\n'
         '        Variables ??= new();   // Remastered (engine M): room for 3 to start\n'
         '        value.IncRef();\n'
         '        Variables[name] = value;\n', 1),
        ('    private DreamListVars? _varsList;\n',
         '    private DreamListVars? _varsList;\n'
         '\n'
         '    // --- Remastered sleeping tiles (planning/MAP_MEMORY.md): a turf held only by its cell sleeps as a packed\n'
         '    // record; these read and move its own state. Plain values hold no object, so they need no IncRef/DecRef. ---\n'
         '    internal static bool RmPlain(DreamValue v) => v.Type switch {\n'
         '        DreamValue.DreamValueType.String or DreamValue.DreamValueType.Float or DreamValue.DreamValueType.DreamType\n'
         '            or DreamValue.DreamValueType.DreamResource or DreamValue.DreamValueType.DreamProc => true,\n'
         '        DreamValue.DreamValueType.DreamObject => v.RmIsTrueNull,\n'
         '        _ => false\n'
         '    };\n'
         '\n'
         '    internal static bool RmHeldOnce(DreamObject? o) => o == null || (o.RefCount == 1 && !o.Deleting && !o.Deleted);\n'
         '\n'
         '    // 0: can sleep, else why not: 1 held by something else, 2 a tag, 3 its vars list held, 4 a value that is not plain\n'
         '    internal int RmObjectSleepBlock() {\n'
         '        if (RefCount != 1 || Deleting || Deleted) return 1;\n'
         '        if (Tag != null) return 2;\n'
         '        if (!RmHeldOnce(_varsList)) return 3;\n'
         '        if (Variables != null) foreach (var v in Variables.Values) if (!RmPlain(v)) return 4;\n'
         '        return 0;\n'
         '    }\n'
         '\n'
         '    internal int RmOwnVarCount => Variables?.Count ?? 0;\n'
         '\n'
         '    // Remastered (engine M2): the last write SetVariableValue left unstored (exactly the type\'s default, no entry\n'
         '    // held): which object and name, so SetVariable counts it as the same value (the game thread\'s only)\n'
         '    internal static DreamObject? RmSkipped;\n'
         '    internal static string? RmSkippedName;\n'
         '\n'
         '    // Remastered (engine M, load-asleep-1030): an entry holding exactly its type\'s own default goes (a read falls back\n'
         '    // to that default, and a save skips a default either way), and a table left with far more room than entries is\n'
         '    // trimmed; one left empty goes. The entries let go, and the table slots before and after, are added to counts.\n'
         '    internal void RmTrimVars(List<string> scratch, ref long gone, ref long slotsBefore, ref long slotsAfter) {\n'
         '        if (Variables == null || Deleting || Deleted) return;\n'
         '        var defs = ObjectDefinition.Variables;\n'
         '        var before = Variables.EnsureCapacity(0);\n'
         '        slotsBefore += before;\n'
         '        scratch.Clear();\n'
         '        foreach (var (name, value) in Variables)\n'
         '            if (defs.TryGetValue(name, out var d) && value.RmSame(d)) scratch.Add(name);\n'
         '        foreach (var name in scratch) {\n'
         '            Variables.Remove(name, out var was);\n'
         '            was.DecRef();\n'
         '        }\n'
         '        gone += scratch.Count;\n'
         '        if (Variables.Count == 0) {\n'
         '            Variables = null;\n'
         '            return;\n'
         '        }\n'
         '        var room = Variables.Count + Variables.Count / 4 + 3;   // a quarter more, so a few new names don\'t double it again\n'
         '        if (before > room + room / 4) Variables.TrimExcess(room);\n'
         '        slotsAfter += Variables.EnsureCapacity(0);\n'
         '    }\n'
         '    internal bool RmHasVarsList => _varsList != null;\n'
         '    internal IEnumerable<KeyValuePair<string, DreamValue>> RmOwnVars() => (IEnumerable<KeyValuePair<string, DreamValue>>?)Variables ?? Array.Empty<KeyValuePair<string, DreamValue>>();\n'
         '\n'
         '    internal KeyValuePair<string, DreamValue>[]? RmTakeVars() {\n'
         '        if (_varsList != null) {\n'
         '            var l = _varsList;\n'
         '            _varsList = null;\n'
         '            l.DecRef();\n'
         '            l.Delete();\n'
         '        }\n'
         '        if (Variables == null || Variables.Count == 0) {\n'
         '            Variables = null;\n'
         '            return null;\n'
         '        }\n'
         '        var a = new KeyValuePair<string, DreamValue>[Variables.Count];\n'
         '        var i = 0;\n'
         '        foreach (var kv in Variables) a[i++] = kv;\n'
         '        Variables = null;\n'
         '        return a;\n'
         '    }\n'
         '\n'
         '    internal void RmGiveVars(KeyValuePair<string, DreamValue>[]? vars) {\n'
         '        if (vars == null) return;\n'
         '        Variables = new(vars.Length);   // as many as it holds (engine M; was at least 4: 7 slots for one or two)\n'
         '        foreach (var kv in vars) Variables[kv.Key] = kv.Value;\n'
         '    }\n', 1),
    ],
    'Objects/Types/DreamObjectAtom.cs': [
        ('    private DreamList? _visLocs; // TODO: Implement\n',
         '    private DreamList? _visLocs; // TODO: Implement\n'
         '\n'
         '    // Remastered sleeping tiles: overlays, underlays and filters are views of the appearance; vis_contents and\n'
         '    // vis_locs hold things. Free when nothing else holds them and the last two are empty.\n'
         '    internal bool RmViewsFree() => RmHeldOnce(_overlays) && RmHeldOnce(_underlays) && RmHeldOnce(_filters) &&\n'
         '                                   (_visContents == null || (RmHeldOnce(_visContents) && _visContents.GetLength() == 0)) &&\n'
         '                                   (_visLocs == null || (RmHeldOnce(_visLocs) && _visLocs.GetLength() == 0));\n'
         '\n'
         '    internal int RmViewCount() => (_overlays != null ? 1 : 0) + (_underlays != null ? 1 : 0) + (_visContents != null ? 1 : 0) + (_filters != null ? 1 : 0) + (_visLocs != null ? 1 : 0);\n'
         '\n'
         '    internal void RmDropViews() {\n'
         '        _overlays?.DecRef(); _overlays = null;\n'
         '        _underlays?.DecRef(); _underlays = null;\n'
         '        _visContents?.DecRef(); _visContents = null;\n'
         '        _filters?.DecRef(); _filters = null;\n'
         '        _visLocs?.DecRef(); _visLocs = null;\n'
         '    }\n', 1),
    ],
    'Objects/Types/DreamObjectTurf.cs': [
        ('    public bool IsDense;\n',
         '    public bool IsDense;\n'
         '\n'
         '    // Remastered sleeping tiles: 0 when this turf can sleep as a packed record, else why not\n'
         '    // (1-4 DreamObject.RmObjectSleepBlock, 5 its lists, 6 its contents list held elsewhere)\n'
         '    internal int RmSleepBlock() {\n'
         '        var o = RmObjectSleepBlock();\n'
         '        if (o != 0) return o;\n'
         '        if (!RmViewsFree()) return 5;\n'
         '        if (!RmHeldOnce(_rmContents)) return 6;\n'
         '        return 0;\n'
         '    }\n'
         '\n'
         '    internal int RmExtras() => (_rmContents != null ? 1 : 0) + RmViewCount();\n'
         '\n'
         '    internal KeyValuePair<string, DreamValue>[]? RmSleep() {\n'
         '        if (_rmContents != null) {\n'
         '            var c = _rmContents;\n'
         '            _rmContents = null;\n'
         '            c.DecRef();\n'
         '            c.Delete();\n'
         '        }\n'
         '        RmDropViews();\n'
         '        return RmTakeVars();\n'
         '    }\n', 1),
    ],
    'Objects/Types/DreamObjectArea.cs': [
        ('    public readonly HashSet<DreamObjectTurf> Turfs;\n',
         '    // Remastered sleeping tiles: the awake turfs; reading Turfs wakes the area\'s sleeping tiles first\n'
         '    internal readonly HashSet<DreamObjectTurf> _rmTurfs;\n'
         '    public int RmSleeping;\n'
         '    public HashSet<DreamObjectTurf> Turfs {\n'
         '        get {\n'
         '            if (RmSleeping > 0) DreamMapManager.RmWakeArea(this);\n'
         '            return _rmTurfs;\n'
         '        }\n'
         '    }\n', 1),
        ('        Turfs = new();\n', '        _rmTurfs = new();\n', 1),
        ('        foreach (var turf in Turfs) {\n            if (_cachedX != null) {\n',
         '        foreach (var turf in _rmTurfs) {   // Remastered sleeping tiles: the awake ones; the sleeping ones after\n            if (_cachedX != null) {\n', 1),
        ('        // 0 if there were no turfs\n',
         '        if (RmSleeping > 0) ((OpenDreamRuntime.Map.DreamMapManager)DreamMapManager).RmLowestAsleep(this, ref _cachedX, ref _cachedY, ref _cachedZ);   // Remastered sleeping tiles\n\n'
         '        // 0 if there were no turfs\n', 1),
    ],
    'Objects/DreamRefManager.cs': [
        # turf refs by position (engine GG, load-asleep-1030; DreamMapManager.RmTiles.cs RmRefsByPosition): a map turf's ref
        # is its place in the order the map makes turfs, the ref it always had; the bucket keeps no slot for it
        ('        private readonly List<DreamObject?> _values = new();\n',
         '        private readonly List<DreamObject?> _values = new();\n'
         '        // Remastered: turf refs by position. RmAt finds the turf at a place (a sleeping tile woken); turfs made\n'
         '        // anywhere else (a resized world) get refs from the top down and are kept here.\n'
         '        public Func<int, DreamObject?>? RmAt;\n'
         '        public Func<int>? RmAtCount;\n'
         '        public Dictionary<int, DreamObject>? RmExtra;\n'
         '        public int RmExtraNext = (int)RefIdMask;\n'
         '        public int RmCount => RmAt != null ? RmAtCount!() + (RmExtra?.Count ?? 0) : _values.Count;\n'
         '        public int RmCapacity => _values.Capacity;\n', 1),
        ('        public int FilledCount => _values.Count - _emptySlots.Count;\n',
         '        public int FilledCount => RmAt != null ? RmCount : _values.Count - _emptySlots.Count;\n', 1),
        ('            DreamObject? value = _values[refId];\n            value?.IncRef();\n',
         '            DreamObject? value = RmAt == null ? _values[refId]\n'
         '                : RmExtra != null && RmExtra.TryGetValue(refId, out var rmExtra) ? rmExtra : RmAt(refId);\n'
         '            value?.IncRef();\n', 1),
        ('        public void Remove(int refId) {\n',
         '        public void Remove(int refId) {\n'
         '            if (RmAt != null) {   // Remastered: a turf by position keeps no slot\n'
         '                RmExtra?.Remove(refId);\n'
         '                return;\n'
         '            }\n\n', 1),
        ('            for (var i = 0; i < _values.Count; i++) {\n                var value = _values[i];\n\n                if (value is not null)\n                    yield return value;\n            }\n',
         '            if (RmAt != null) {   // Remastered: turfs by position, in the order they were made, then any others\n'
         '                var rmN = RmAtCount!();\n'
         '                for (var i = 0; i < rmN; i++) {\n'
         '                    var value = RmAt(i);\n'
         '                    if (value is not null)\n'
         '                        yield return value;\n'
         '                }\n'
         '                if (RmExtra != null)\n'
         '                    foreach (var value in new List<DreamObject>(RmExtra.Values))\n'
         '                        yield return value;\n'
         '                yield break;\n'
         '            }\n\n'
         '            for (var i = 0; i < _values.Count; i++) {\n                var value = _values[i];\n\n                if (value is not null)\n                    yield return value;\n            }\n', 1),
        ('    private uint CreateRef(RefType refType, DreamObject value) {\n        var bucket = _buckets[refType];\n',
         '    // Remastered: turf refs by position. The map sets RmNextTurfRef before it makes a turf (a turf\'s ref is made\n'
         '    // before its constructor knows its place).\n'
         '    public uint RmNextTurfRef;\n'
         '    public int RmPosW, RmPosH;   // the map\'s size when refs went by position: their stride\n'
         '    public bool RmTurfRefsOn => _buckets[RefType.DreamObjectTurf].RmAt != null;\n'
         '    public int RmTurfSlots => _buckets[RefType.DreamObjectTurf].RmCount;\n'
         '    public int RmTurfSlotCapacity => _buckets[RefType.DreamObjectTurf].RmCapacity;\n'
         '\n'
         '    public void RmTurfRefsByPosition(Func<int, DreamObject?> at, Func<int> count, int w, int h) {\n'
         '        var bucket = _buckets[RefType.DreamObjectTurf];\n'
         '        if (bucket.FilledCount != 0) return;   // turfs made already: their slots stay\n'
         '        RmPosW = w;\n'
         '        RmPosH = h;\n'
         '        bucket.RmAt = at;\n'
         '        bucket.RmAtCount = count;\n'
         '    }\n'
         '\n'
         '    // the ref of the turf the map makes next at x, y (from 0) of level z, a level of size w x h; 0: from the top down\n'
         '    public uint RmPosRef(int z, int x, int y, int w, int h) {\n'
         '        var bucket = _buckets[RefType.DreamObjectTurf];\n'
         '        if (bucket.RmAt == null || w != RmPosW || h != RmPosH) return 0;\n'
         '        var id = ((long)(z - 1) * RmPosW + x) * RmPosH + y;\n'
         '        return id < bucket.RmExtraNext ? (uint)RefType.DreamObjectTurf | (uint)id : 0;\n'
         '    }\n'
         '\n'
         '    private uint CreateRef(RefType refType, DreamObject value) {\n        var bucket = _buckets[refType];\n'
         '        if (refType == RefType.DreamObjectTurf && bucket.RmAt != null) {\n'
         '            var rmRef = RmNextTurfRef;\n'
         '            RmNextTurfRef = 0;\n'
         '            if (rmRef != 0) return rmRef;\n'
         '            var rmId = bucket.RmExtraNext--;\n'
         '            (bucket.RmExtra ??= new())[rmId] = value;\n'
         '            return (uint)refType | (uint)rmId;\n'
         '        }\n', 1),
    ],
    # the proc-state pool grew to the most procs alive at once (14,897 at the map load, each with its 256 locals) and
    # kept them all game, about 33 MB (load-asleep-1030 census); past 2,048 a finished state is left to the collector
    # DM lists kept for reuse: at most 16, of at most 32,768 values (it kept up to 256 of any size: 154 lists of ~15,000
    # values, 36 MB, in the server's census; engine GG, load-asleep-1030)
    'Objects/Types/DreamList.cs': [
        ('        if (_values.Capacity > DreamManager.ListPoolThreshold && ListPool.Count < DreamManager.ListPoolSize) {\n',
         '        if (_values.Capacity > DreamManager.ListPoolThreshold && _values.Capacity <= 32768 && ListPool.Count < Math.Min(DreamManager.ListPoolSize, 16)) {   // Remastered: a capped pool\n', 1),
    ],
    # Robust's pooled memory streams capped (RmPools.cs; engine GG)
    'DreamManager.cs': [
        ('        ListPoolSize = _config.GetCVar(OpenDreamCVars.ListPoolSize);\n',
         '        ListPoolSize = _config.GetCVar(OpenDreamCVars.ListPoolSize);\n        RmPools.Cap();   // Remastered: memory stream pools capped\n', 1),
        ('            WorldInstance.Cpu = WorldInstance.TickUsage;\n',
         '            RmPools.Tick();   // Remastered: free large stream buffers let go once a minute\n            WorldInstance.Cpu = WorldInstance.TickUsage;\n', 1),
    ],
    # icons' decoded pixels: every icon file the server ever read, and every icon an icon operation made, kept its
    # decoded image for good, 532 of them, 26 MB in the server's census (engine H, load-asleep-1030,
    # planning/REGIONS_ON_DISK_PLAN_2026-10-31.md step A3). Each one remembers its last use; RmPools lets go of those unused
    # for 5 minutes (RM_ICON_IDLE_S), and the next use decodes the resource's own bytes again: the same image.
    'Resources/IconResource.cs': [
        ('    public Image<Rgba32> Texture => _texture ??= Image.Load<Rgba32>(ResourceData);\n',
         '    public Image<Rgba32> Texture { get { RmTextureUsed = System.Environment.TickCount64; return _texture ??= Image.Load<Rgba32>(ResourceData); } }   // Remastered: its last use kept\n'
         '    internal long RmTextureUsed;\n'
         '    internal Image<Rgba32>? RmTextureHeld => _texture;\n'
         '\n'
         '    // Remastered (engine H): the decoded image let go when unused for idleMs, only if the bytes it comes from are there\n'
         '    internal bool RmDropIdleTexture(long now, long idleMs) {\n'
         '        if (_texture == null || now - RmTextureUsed < idleMs || ResourceData == null) return false;\n'
         '        _texture = null;\n'
         '        return true;\n'
         '    }\n', 1),
        ('        _texture = texture;\n',
         '        _texture = texture;\n        RmTextureUsed = System.Environment.TickCount64;   // Remastered\n', 1),
    ],
    'Resources/DreamResourceManager.cs': [
        ('    public IconResource CreateIconResource(byte[] data) {\n',
         '    // Remastered (engine H): icons\' decoded images unused for idleMs let go (IconResource.RmDropIdleTexture): how many, their bytes\n'
         '    internal (int Count, long Bytes) RmDropIdleTextures(long idleMs) {\n'
         '        var now = System.Environment.TickCount64;\n'
         '        int count = 0;\n'
         '        long bytes = 0;\n'
         '        foreach (var resource in _resourceCache) {\n'
         '            if (resource is not IconResource icon || icon.RmTextureHeld is not { } image) continue;\n'
         '            if (!icon.RmDropIdleTexture(now, idleMs)) continue;\n'
         '            count++;\n'
         '            bytes += (long)image.Width * image.Height * 4;\n'
         '        }\n'
         '        return (count, bytes);\n'
         '    }\n'
         '\n'
         '    public IconResource CreateIconResource(byte[] data) {\n', 1),
    ],
    # libbyond (byondapi's trampoline for call_ext) ships for x86-64 only: on Apple silicon's own .NET it can't load and
    # the server stopped at start. The game never uses call_ext, so a missing trampoline only turns call_ext's byondapi
    # off (engine G7, load-asleep-1030); on x86-64 it loads as before.
    'ByondApi/ByondApi.cs': [
        ('        InitTrampoline();\n',
         '        try {\n'
         '            InitTrampoline();\n'
         '        } catch (Exception e) when (e is DllNotFoundException or EntryPointNotFoundException or BadImageFormatException) {   // Remastered\n'
         '            Robust.Shared.Log.Logger.GetSawmill("byondapi").Warning($"libbyond not loaded ({e.GetType().Name}): call_ext with byondapi is off");\n'
         '        }\n', 1),
    ],
    'Procs/DMProc.cs': [
        ('        _catchPosition.Clear();\n        _catchVarIndex.Clear();\n\n        Pool.Push(this);\n',
         '        _catchPosition.Clear();\n        _catchVarIndex.Clear();\n\n        if (Pool.Count < 2048) Pool.Push(this);   // Remastered: a capped pool\n', 1),
    ],
    'Map/DreamMapManager.cs': [
        ('        cell = level.Cells[pos.X - 1, pos.Y - 1];\n        return true;\n',
         '        cell = level.Cells[pos.X - 1, pos.Y - 1] ?? RmWake(level, pos.X - 1, pos.Y - 1);   // Remastered sleeping tiles\n        return true;\n', 1),
        ('        var cell = _levels[z - 1].Cells[pos.X - 1, pos.Y - 1];\n\n        cell.Turf.SetTurfType(type);\n',
         '        var cell = _levels[z - 1].Cells[pos.X - 1, pos.Y - 1] ?? RmWake(_levels[z - 1], pos.X - 1, pos.Y - 1);   // Remastered sleeping tiles\n\n        cell.Turf.SetTurfType(type);\n', 1),
        ('    public void SetWorldSize(Vector2i size) {\n',
         '    public void SetWorldSize(Vector2i size) {\n        RmWakeAll();   // Remastered sleeping tiles: every tile awake before the levels are resized\n', 1),
        ('    public void SetZLevels(int levels) {\n',
         '    public void SetZLevels(int levels) {\n        if (levels < Levels) RmWakeAll();   // Remastered sleeping tiles: before levels go (adding one moves no index)\n', 1),
        # built asleep at load (load-asleep, reports/load-asleep-1030; DreamMapManager.RmTiles.cs RmLoadLevelsAsleep)
        ('        Size = new Vector2i(maxX, maxY);\n        SetZLevels(maxZ);\n',
         '        Size = new Vector2i(maxX, maxY);\n'
         '        RmRefsByPosition();   // Remastered: turf refs by position (engine GG)\n'
         '        RmNearTilesStart();   // Remastered: the 2D map\'s tiles only near players (engine GG)\n'
         '        if (RmLoadAsleep) {   // Remastered: a level at a time, made, loaded and put to sleep\n'
         '            RmLoadLevelsAsleep(maps, maxZ);\n'
         '            return;\n'
         '        }\n'
         '        SetZLevels(maxZ);\n', 1),
        ('                    var area = _levels[z - 1].Cells[x - 1, y - 1].Area;\n',
         '                    var area = RmAreaAt(_levels[z - 1], x - 1, y - 1);   // Remastered: asleep or awake, wakes nothing\n', 1),
        ('                    _levels[z - 1].Cells[x - 1, y - 1].Turf.SpawnProc("New").Dispose();\n                }\n            }\n        }\n',
         '                    (_levels[z - 1].Cells[x - 1, y - 1] ?? RmWake(_levels[z - 1], x - 1, y - 1)).Turf.SpawnProc("New").Dispose();   // Remastered: asleep at load\n'
         '                }\n            }\n\n            RmSleepAfterNew(z);   // Remastered: the level back to sleep\n        }\n', 1),
        # the map's objects: only cells that have some look their turf up (it woke every tile of the map, load-asleep)
        ('                if (TryGetTurfAt((blockX, blockY), block.Z, out var turf)) {\n',
         '                if (cellDefinition.Objects.Count > 0 && TryGetTurfAt((blockX, blockY), block.Z, out var turf)) {   // Remastered\n', 1),
        # an area's appearance change: the sleeping tiles' records changed in place, none woken (load-asleep)
        ('        foreach (var turf in area.Turfs) {\n            if(oldToNewAppearance.TryGetValue(turf.Appearance, out var newAppearance))\n',
         '        foreach (var turf in area._rmTurfs) {   // Remastered sleeping tiles: the awake ones; the sleeping ones after\n            if(oldToNewAppearance.TryGetValue(turf.Appearance, out var newAppearance))\n', 1),
        ('            level.QueuedTileUpdates.Add( (turfPos, new Tile((int)turfId)));\n        }\n    }\n',
         '            level.QueuedTileUpdates.Add( (turfPos, new Tile((int)turfId)));\n        }\n\n'
         '        RmAreaAppearanceAsleep(area, oldAppearance, oldToNewAppearance);   // Remastered sleeping tiles\n    }\n', 1),
        ('        public readonly List<(Vector2i, Tile)> QueuedTileUpdates = new();\n',
         '        public readonly List<(Vector2i, Tile)> QueuedTileUpdates = new();\n'
         '        public DreamMapManager.RmSleepBlock?[]? RmBlocks;   // Remastered sleeping tiles: 128x128 blocks with sleeping tiles\n'
         '        public int RmBlocksW;\n', 1),
        ('                _area.Turfs.Remove(Turf);\n', '                _area._rmTurfs.Remove(Turf);\n', 1),
        ('                _area.Turfs.Add(Turf);\n', '                _area._rmTurfs.Add(Turf);\n', 1),
        ('        public Cell(DreamObjectArea area, DreamObjectTurf turf) {\n',
         '        // Remastered sleeping tiles: a sleeping tile woken, in the area it slept in (no area change)\n'
         '        internal Cell(DreamObjectArea area, DreamObjectTurf turf, bool rmWake) {\n'
         '            Turf = turf;\n'
         '            Turf.IncRef();\n'
         '            _area = area;\n'
         '            area._rmTurfs.Add(turf);\n'
         '        }\n'
         '\n'
         '        public Cell(DreamObjectArea area, DreamObjectTurf turf) {\n', 1),
        # a level's cells in 16x16 blocks that exist only while one of their tiles is awake (engine G5; RmCells)
        ('        public Cell[,] Cells;\n', '        public RmCells Cells;   // Remastered: blocks of awake cells only (DreamMapManager.RmTiles.cs)\n', 1),
        ('            Cells = new Cell[size.X, size.Y];\n', '            Cells = new RmCells(size.X, size.Y);   // Remastered\n', 1),
        ('                existingLevel.Cells = new Cell[Size.X, Size.Y];\n', '                existingLevel.Cells = new RmCells(Size.X, Size.Y);   // Remastered\n', 1),
        ('                existingLevel.Cells = new Cell[size.X, size.Y];\n', '                existingLevel.Cells = new RmCells(size.X, size.Y);   // Remastered\n', 1),
        # turf refs by position (engine GG): the ref a turf the map makes takes, by its place
        ('                    var turf = new DreamObjectTurf(turfType, x + 1, y + 1, z);\n',
         '                    turfType.DreamRefManager.RmNextTurfRef = turfType.DreamRefManager.RmPosRef(z, x, y, size.X, size.Y);   // Remastered\n'
         '                    var turf = new DreamObjectTurf(turfType, x + 1, y + 1, z);\n', 1),
        ('    public void SetZLevels(int levels);\n',
         '    public void SetZLevels(int levels);\n    public void RmWakeArea(DreamObjectArea area);   // Remastered sleeping tiles\n', 1),
        # the 2D map's tiles only near players (engine GG; DreamMapManager.RmTiles.cs RmUpdateNearTiles)
        ('    public void UpdateTiles() {\n',
         '    public void UpdateTiles() {\n'
         '        if (RmNearTiles) {   // Remastered: tiles only near players\n'
         '            RmUpdateNearTiles();\n'
         '            return;\n'
         '        }\n\n', 1),
        # the load's tile queue (2M tiles a level) was cleared but kept at its size all game: 4 x 32 MB (load-asleep-1030 census)
        ('            _mapSystem.SetTiles(level.Grid, tiles);\n            level.QueuedTileUpdates.Clear();\n',
         '            _mapSystem.SetTiles(level.Grid, tiles);\n            level.QueuedTileUpdates.Clear();\n'
         '            if (level.QueuedTileUpdates.Capacity > 4096) level.QueuedTileUpdates.TrimExcess();   // Remastered: the load queue let go\n', 1),
        # one definition per map object, not one per tile it is placed on: 14,300 copies of the types' var tables for
        # 1,326 types (load-asleep-1030 census); a definition is read-only once the maps load, so the tiles share it
        ('    private DreamObjectDefinition CreateMapObjectDefinition(MapObjectJson mapObject) {\n'
         '        DreamObjectDefinition definition = _objectTree.GetObjectDefinition(mapObject.Type);\n'
         '        if (mapObject.VarOverrides?.Count > 0) {\n'
         '            definition = new DreamObjectDefinition(definition);\n',
         '    private readonly Dictionary<MapObjectJson, DreamObjectDefinition> _rmMapDefs = new();   // Remastered\n'
         '\n'
         '    private DreamObjectDefinition CreateMapObjectDefinition(MapObjectJson mapObject) {\n'
         '        DreamObjectDefinition definition = _objectTree.GetObjectDefinition(mapObject.Type);\n'
         '        if (mapObject.VarOverrides?.Count > 0) {\n'
         '            if (_rmMapDefs.TryGetValue(mapObject, out var made)) return made;   // Remastered: made once per map object\n'
         '            definition = new DreamObjectDefinition(definition);\n', 1),
        ('                    definition.Variables[varOverride.Key] = overrideValue;\n'
         '                    overrideValue.IncRef();\n'
         '                }\n'
         '            }\n',
         '                    definition.Variables[varOverride.Key] = overrideValue;\n'
         '                    overrideValue.IncRef();\n'
         '                }\n'
         '            }\n'
         '\n'
         '            _rmMapDefs[mapObject] = definition;   // Remastered\n', 1),
    ],
}

NEW = {'Map/DreamMapManager.RmTiles.cs': 'DreamMapManager.RmTiles.cs', 'RmPools.cs': 'RmPools.cs'}
