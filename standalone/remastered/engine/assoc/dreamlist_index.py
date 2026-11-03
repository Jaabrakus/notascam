# Remastered engine v6: a membership index for /list (tools/build_runtime.py --assoc-index; RM_ASSOC_INDEX=0 turns it
# off at run time). Exact-match edits to OpenDreamRuntime/Objects/Types/DreamList.cs (upstream 2e58532), the base class
# only: (old text, new text, how many times old text is there).
#
# What it changes: OpenDream's ContainsValue scanned every element, and `L[x] = v` (a keyed write) calls it every time,
# so building a set with `L[x] = 1` was O(n^2); `x in L`, `L |= x` and L.Find of a missing element scanned too.
# Removing (`L -= x`, L.Remove) keeps its scan: List.LastIndexOf calls DreamValue.Equals on each element in place, and
# Equals turns a deleted object's reference into null where it's stored, which later keyed lookups by that element see
# (found by tests/list_index_check.dm: skipping the scan changed what `L + M` gave for a list holding deleted keys).
# The index keeps each element with how many copies the list holds (duplicates are allowed in DM lists). It's made for a
# list of 32+ elements once it has been looked up 16 times by scanning with no change from outside (v6e: a list made,
# looked up once and dropped never pays for an index; at 30,000 units v6d's build on every first lookup made large-object
# garbage and multi-second collections while units were made), kept up by DreamList's own changes, and dropped when the
# elements changed any other way: List<T>'s private change count must have moved by exactly this class's own steps (so
# a deletion run from inside a DecRef, or anything holding GetValues(), can't leave it stale).
# Exactness: DreamValue.Equals makes a null or deleted object equal to every null and deleted object, but a deleted
# object hashes as itself, so lookups of a null or deleted value still scan. Every other value (a live object, a string,
# a number, a type, a resource) is equal exactly when its hash and Equals match, so the index answers as the scan did.
# Order, duplicates, associations, which copy `-=` removes (the last) and every result are unchanged.

PAIRS = [
    ("""    private readonly List<DreamValue> _values;
    private Dictionary<DreamValue, DreamValue>? _associativeValues;
""", """    private readonly List<DreamValue> _values;
    private Dictionary<DreamValue, DreamValue>? _associativeValues;

    // Remastered (engine v6; RM_ASSOC_INDEX=0 turns it off): a membership index, each element and how many copies the
    // list holds, so `x in L`, `L[x] = v` and Find stop scanning (removing keeps its scan: see RemoveValue). Made for a list of
    // RmIndexMin+ elements once it has been looked up RmIndexScans times by scanning with no change from outside this class
    // (a list made, looked up once or twice and dropped never pays for one: a big index is a large-object allocation),
    // kept by this class's own changes, dropped on any other (List<T>'s change count). A null or deleted object equals
    // every null and deleted object but hashes as itself, so those are still looked up by the scan
    // (engine/assoc/dreamlist_index.py). RM_ASSOC_REPORT=1 logs the builds every 10 s or more.
    private static readonly bool RmIndexOn = Environment.GetEnvironmentVariable("RM_ASSOC_INDEX") != "0";
    private static readonly bool RmIndexReport = Environment.GetEnvironmentVariable("RM_ASSOC_REPORT") == "1";
    private const int RmIndexMin = 32;
    private const int RmIndexScans = 16;
    private Dictionary<DreamValue, int>? _rmIndex;
    private int _rmSeenVer;   // the elements' change count as this class last left it; the index (if any) is for it
    private int _rmScans;     // lookups by scanning since the last change from outside
    private static long _rmBuilds, _rmBuiltElements, _rmBuildTicks, _rmDrops, _rmReportAt;

    private static class RmListVersion<T> {
        [UnsafeAccessor(UnsafeAccessorKind.Field, Name = "_version")]
        public static extern ref int Of(List<T> list);
    }

    // Catches up with a change from outside this class: the index is stale, and scans count again from none.
    private void RmIndexSync() {
        var ver = RmListVersion<DreamValue>.Of(_values);
        if (ver == _rmSeenVer) return;
        if (_rmIndex != null) _rmDrops++;
        _rmIndex = null;
        _rmScans = 0;
        _rmSeenVer = ver;
    }

    // The index, if it's there and nothing has changed the elements since it was last kept up.
    private bool RmIndexLive => _rmIndex != null && RmListVersion<DreamValue>.Of(_values) == _rmSeenVer;

    // The index for a lookup: kept, made now (a list big enough and looked up often enough), or none (scan).
    private bool RmIndexReady() {
        RmIndexSync();
        if (_rmIndex != null) return true;
        if (!RmIndexOn || _values.Count < RmIndexMin || ++_rmScans <= RmIndexScans) return false;
        var t0 = System.Diagnostics.Stopwatch.GetTimestamp();
        _rmIndex = new Dictionary<DreamValue, int>(_values.Count);
        foreach (var v in _values) RmIndexAdd(v);
        _rmBuilds++;
        _rmBuiltElements += _values.Count;
        _rmBuildTicks += System.Diagnostics.Stopwatch.GetTimestamp() - t0;
        if (RmIndexReport) RmIndexLog();
        return true;
    }

    private static void RmIndexLog() {
        var now = System.Diagnostics.Stopwatch.GetTimestamp();
        if (now - _rmReportAt < 10 * System.Diagnostics.Stopwatch.Frequency) return;
        _rmReportAt = now;
        Logger.GetSawmill("assoc").Info($"assoc builds={_rmBuilds} elements={_rmBuiltElements} build_ms={_rmBuildTicks * 1000.0 / System.Diagnostics.Stopwatch.Frequency:0.0} drops={_rmDrops}");
    }

    private void RmIndexAdd(DreamValue v) {
        if (_rmIndex == null) return;
        ref var n = ref CollectionsMarshal.GetValueRefOrAddDefault(_rmIndex, v, out _);
        n++;
    }

    private void RmIndexDrop(DreamValue v) {
        if (_rmIndex == null) return;
        ref var n = ref CollectionsMarshal.GetValueRefOrNullRef(_rmIndex, v);
        if (Unsafe.IsNullRef(ref n)) {   // not in it (a deleted element nulled where it's stored): made again after more scans
            _rmIndex = null;
            _rmScans = 0;
            _rmDrops++;
        } else if (--n == 0) _rmIndex.Remove(v);
    }

    // Before this class changes the elements: caught up with any change from outside; their change count now.
    private int RmIndexBefore() {
        RmIndexSync();
        return _rmSeenVer;
    }

    // After: the index and the scan count stay only if the elements changed by exactly this class's own `steps` changes
    // (nothing else changed them meanwhile, as a deletion run from a DecRef could).
    private void RmIndexAfter(int before, int steps) {
        if (RmListVersion<DreamValue>.Of(_values) == before + steps) _rmSeenVer = before + steps;
        else RmIndexSync();
    }
""", 1),

    ("""    protected override void HandleDeletion() {
        foreach (var value in _values)
""", """    protected override void HandleDeletion() {
        _rmIndex = null;
        foreach (var value in _values)
""", 1),

    ("""    public virtual void SetValue(DreamValue key, DreamValue value, bool allowGrowth = false) {
        if (key.TryGetValueAsInteger(out int keyInteger)) {
            if (allowGrowth && keyInteger == _values.Count + 1) {
                value.IncRef();
                _values.Add(value);
            } else {
                var oldValue = _values[keyInteger - 1];

                value.IncRef();
                oldValue.DecRef();
                _values[keyInteger - 1] = value;
            }
        } else {
            if (!ContainsValue(key)) {
                _values.Add(key);
                key.IncRef();
            }
""", """    public virtual void SetValue(DreamValue key, DreamValue value, bool allowGrowth = false) {
        if (key.TryGetValueAsInteger(out int keyInteger)) {
            if (allowGrowth && keyInteger == _values.Count + 1) {
                var rmBefore = RmIndexBefore();
                value.IncRef();
                _values.Add(value);
                RmIndexAdd(value);
                RmIndexAfter(rmBefore, 1);
            } else {
                var oldValue = _values[keyInteger - 1];
                var rmBefore = RmIndexBefore();

                value.IncRef();
                oldValue.DecRef();
                _values[keyInteger - 1] = value;
                RmIndexDrop(oldValue);
                RmIndexAdd(value);
                RmIndexAfter(rmBefore, 1);
            }
        } else {
            if (!ContainsValue(key)) {
                var rmBefore = RmIndexBefore();
                _values.Add(key);
                key.IncRef();
                RmIndexAdd(key);
                RmIndexAfter(rmBefore, 1);
            }
""", 1),

    ("""    public virtual void RemoveValue(DreamValue value) {
        int valueIndex = _values.LastIndexOf(value);

        if (valueIndex != -1) {
            if (_associativeValues?.TryGetValue(value, out var associatedValue) is true)  {
                associatedValue.DecRef();
                _associativeValues.Remove(value);
            }

            _values.RemoveAt(valueIndex);
            value.DecRef();
        }
""", """    public virtual void RemoveValue(DreamValue value) {
        // Remastered: no index shortcut here. LastIndexOf runs DreamValue.Equals on the stored elements, which nulls the
        // deleted objects it passes where they're stored; later lookups by those elements depend on it.
        int valueIndex = _values.LastIndexOf(value);

        if (valueIndex != -1) {
            var rmRemoved = _values[valueIndex];
            if (_associativeValues?.TryGetValue(value, out var associatedValue) is true)  {
                associatedValue.DecRef();
                _associativeValues.Remove(value);
            }

            var rmBefore = RmIndexBefore();
            _values.RemoveAt(valueIndex);
            RmIndexDrop(rmRemoved);
            RmIndexAfter(rmBefore, 1);
            value.DecRef();
        }
""", 1),

    ("""    public virtual void AddValue(DreamValue value) {
        _values.Add(value);
        value.IncRef();
        UpdateTracyContentsMemory();
    }
""", """    public virtual void AddValue(DreamValue value) {
        var rmBefore = RmIndexBefore();
        _values.Add(value);
        value.IncRef();
        RmIndexAdd(value);
        RmIndexAfter(rmBefore, 1);
        UpdateTracyContentsMemory();
    }
""", 1),

    ("""    public virtual bool ContainsValue(DreamValue value) {
        var count = _values.Count;
""", """    public virtual bool ContainsValue(DreamValue value) {
        if (!value.IsNull && RmIndexReady()) return _rmIndex!.ContainsKey(value);   // Remastered: the index

        var count = _values.Count;
""", 1),

    ("""    public virtual int FindValue(DreamValue value, int start = 1, int end = 0) {
        if (end == 0 || end > _values.Count) end = _values.Count + 1;
""", """    public virtual int FindValue(DreamValue value, int start = 1, int end = 0) {
        if (!value.IsNull && RmIndexReady() && !_rmIndex!.ContainsKey(value)) return 0;   // Remastered: not in the list
        if (end == 0 || end > _values.Count) end = _values.Count + 1;
""", 1),

    ("""        if (end > start) {
            for (int i = start; i < end; i++) {
                _values[i - 1].DecRef();
            }

            _values.RemoveRange(start - 1, end - start);
        }
""", """        if (end > start) {
            var rmBefore = RmIndexBefore();
            for (int i = start; i < end; i++) {
                RmIndexDrop(_values[i - 1]);
                _values[i - 1].DecRef();
            }

            _values.RemoveRange(start - 1, end - start);
            RmIndexAfter(rmBefore, 1);
        }
""", 1),

    ("""    public void Insert(int index, DreamValue value) {
        _values.Insert(index - 1, value);
        value.IncRef();
        UpdateTracyContentsMemory();
    }
""", """    public void Insert(int index, DreamValue value) {
        var rmBefore = RmIndexBefore();
        _values.Insert(index - 1, value);
        value.IncRef();
        RmIndexAdd(value);
        RmIndexAfter(rmBefore, 1);
        UpdateTracyContentsMemory();
    }
""", 1),
]
