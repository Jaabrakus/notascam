// Remastered (engine GG, load-asleep-1030): Robust's pooled memory streams. Its manager (RobustMemoryManager, made with
// the library's defaults) keeps every free block and large buffer it ever had: 43 MB in the server after a game's
// start, one 22 MB buffer among them (the server's heap census). Here its free small blocks are capped at the start, and
// once a minute the free large buffers are let go (the next large stream gets a new one); so are the icons' decoded
// images unused for 5 minutes (engine H). Reflection, because the
// manager is private to Robust: if its fields are not found nothing changes, and it says so once. RM_POOL_CAPS=0 in the
// server's environment turns it off.
using System.Collections.Concurrent;
using System.Reflection;
using System.Threading;

namespace OpenDreamRuntime;

internal static class RmPools {
    private const long SmallFreeCap = 8L << 20;
    private static object? _manager;
    private static ConcurrentStack<byte[]>[]? _largePools;
    private static long[]? _largeFree;
    private static int _ticks;
    private static bool _off;

    // DreamManager.PreInitialize, before the map loads
    public static void Cap() {
        _off = Environment.GetEnvironmentVariable("RM_POOL_CAPS") == "0";
        if (_off) return;
        try {
            var t = Type.GetType("Robust.Shared.GameObjects.RobustMemoryManager, Robust.Shared");
            _manager = t?.GetField("MemStreamManager", BindingFlags.NonPublic | BindingFlags.Static)?.GetValue(null);
            var settings = _manager?.GetType().GetProperty("Settings")?.GetValue(_manager);
            var small = settings?.GetType().GetProperty("MaximumSmallPoolFreeBytes");
            if (small == null) {
                Say("the memory stream manager's settings were not found; its pools are left as they are");
                _off = true;
                return;
            }
            small.SetValue(settings, SmallFreeCap);
            var mt = _manager!.GetType();
            _largePools = mt.GetField("largePools", BindingFlags.NonPublic | BindingFlags.Instance)?.GetValue(_manager) as ConcurrentStack<byte[]>[];
            _largeFree = mt.GetField("largeBufferFreeSize", BindingFlags.NonPublic | BindingFlags.Instance)?.GetValue(_manager) as long[];
            if (_largePools == null || _largeFree == null || _largeFree.Length != _largePools.Length) {
                Say("the memory stream manager's large pools were not found; only its small blocks are capped");
                _largePools = null;
            }
        } catch (Exception e) {
            Say($"capping the memory stream pools failed ({e.GetType().Name}: {e.Message}); left as they are");
            _off = true;
        }
    }

    // DreamManager.Update, every tick: once a minute (600 ticks at 10 a second) the free large buffers let go, and the icons'
    // decoded images unused for 5 minutes (engine H; RM_ICON_IDLE_S, 0 = never)
    public static void Tick() {
        if (++_ticks < 600) return;
        _ticks = 0;
        if (!_off && _largePools != null) {
            for (var i = 0; i < _largePools.Length; i++) {
                while (_largePools[i].TryPop(out var buffer))
                    Interlocked.Add(ref _largeFree![i], -buffer.Length);
            }
        }
        Icons();
        VarTrim();
    }

    private static long _iconIdleMs = -1;

    private static void Icons() {
        if (_iconIdleMs < 0)
            _iconIdleMs = long.TryParse(Environment.GetEnvironmentVariable("RM_ICON_IDLE_S"), out var s) ? s * 1000 : 300_000;
        if (_iconIdleMs <= 0) return;
        try {
            var (count, bytes) = Robust.Shared.IoC.IoCManager.Resolve<Resources.DreamResourceManager>().RmDropIdleTextures(_iconIdleMs);
            if (count > 0)
                Robust.Shared.Log.Logger.GetSawmill("rmpools").Info($"icons: let go of {count} decoded images unused for {_iconIdleMs / 1000} s, ~{bytes >> 20} MB");
        } catch (Exception e) {
            Say($"letting go of idle icon images failed ({e.GetType().Name}: {e.Message}); they are kept from now on");
            _iconIdleMs = 0;
        }
    }

    // Engine M (load-asleep-1030): once a minute, every unit's, thing's and datum's own variables written back at exactly
    // their type's default let go, and tables left far bigger than their entries trimmed (DreamObject.RmTrimVars). At 30
    // players a third of the units' entries were defaults (HasHead = 1, Fainted = 0 ...), ~146 a unit in ~198 slots.
    // Turfs are not walked (that would wake every sleeping tile): theirs start small instead. RM_VAR_TRIM=0: never.
    private static int _varTrim = -1;
    private static readonly List<string> TrimScratch = new();
    private static int _trimRuns;

    internal static (long Gone, long Before, long After, long Ms) VarTrim(bool force = false) {
        if (_varTrim < 0) _varTrim = Environment.GetEnvironmentVariable("RM_VAR_TRIM") == "0" ? 0 : 1;
        if (_varTrim == 0 && !force) return (0, 0, 0, 0);
        var watch = System.Diagnostics.Stopwatch.StartNew();
        long gone = 0, before = 0, after = 0;
        try {
            var refs = Robust.Shared.IoC.IoCManager.Resolve<Objects.DreamRefManager>();
            foreach (var type in new[] { Objects.RefType.DreamObjectMob, Objects.RefType.DreamObjectMovable, Objects.RefType.DreamObjectDatum })
                foreach (var o in refs.EnumerateType(type))
                    o.RmTrimVars(TrimScratch, ref gone, ref before, ref after);
        } catch (Exception e) {
            Say($"trimming the own-vars tables failed ({e.GetType().Name}: {e.Message}); they are left as they are from now on");
            _varTrim = 0;
        }
        TrimScratch.Clear();
        var ms = watch.ElapsedMilliseconds;
        if (++_trimRuns <= 3 || _trimRuns % 30 == 0)
            Robust.Shared.Log.Logger.GetSawmill("rmpools").Info($"vars: {gone} entries at their default let go, table slots {before} -> {after} ({ms} ms)");
        return (gone, before, after, ms);
    }

    private static void Say(string what) => Robust.Shared.Log.Logger.GetSawmill("rmpools").Warning(what);
}
