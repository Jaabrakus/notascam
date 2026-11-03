// Remastered: garbage collection between ticks (engine v6, 2026-10-24; the coordinator's design, planning/ENGINE_PLAN.md;
// reviewed by server-cost). The engine's ticks run inside a no-GC region, so no collection lands inside a tick. At the end
// of a tick (the frame update after it, the game-state send done, just before the loop idles until the next tick):
// - a region under half used stays open (about four ticks of allocation are asked for: the whole process's, the
//   network's and the state sender's too), and so does one under three quarters when there's no time to collect;
// - otherwise it ends, gen0 is collected if the time left before the next tick covers the recent collections, and the
//   next region opens.
// A region the allocations outgrew ("broken": the runtime collected inside the tick), one the runtime wouldn't open
// ("refused") or no time to collect ("short") leaves the normal collector on until a tick's end with time to spare; each
// is counted, and a broken one makes the next ones at least twice as big. No gen0 budget is set. RM_TICK_GC=0 in the
// server's environment turns it all off. Every 10 s a "tickgc" line in the server log gives the counts, the pauses made
// here and the ones outside (inside ticks, or with no region open).
//
// The old generation (gc-slack, 2026-10-30, reports/gc-slack-1030):
// - Left to itself the runtime collects gen2 only once its gen2 budget (hundreds of MB on this heap) is spent, so after
//   the load pass dead objects pile up in gen2 and the large-object heap for many minutes (~50 MB a minute with one
//   player) and the footprint climbs ~0.3-0.4 GB before it levels off. Room a gen2 collection has swept is used again,
//   so collecting sooner keeps the heap near its live size. Once gen2 and the large objects hold GrowMB more than just
//   after the last gen2 collection (RM_GC_GROW_MB, default 64; 0 = never), a tick's end with time to spare starts one in
//   the background (not compacting: the game runs on while it marks), at most one every 20 s.
// - Opening a region while a background collection runs waits for it to finish (the runtime's region start is a
//   blocking gen2 request): that froze the server 0.3-0.95 s at every background gen2 in play. While one may be
//   running, no region opens and the normal collector stays on; gen0 is still collected at tick ends once a region's
//   worth was allocated. RM_GC_BGC_WAIT=1 opens regions anyway (as before).
// - The time a collection is expected to take was the slowest of the last 20, kept until the next one. One slow
//   collection (a gen0 the runtime raised to gen2, 110 ms at load) left no tick's end with time enough, so the GC
//   between ticks stopped for good and left it all to the runtime. A collection that began a gen2 no longer counts,
//   and after 5 s of tick ends with no time the recent ones are forgotten. No early gen2 starts until the ticks have
//   kept to their time for 5 s (none during the load).
using System;
using System.Runtime;
using Robust.Shared.IoC;
using Robust.Shared.Log;
using Robust.Shared.Timing;
using Stopwatch = System.Diagnostics.Stopwatch;

namespace OpenDreamRuntime;

public static class RemasterTickGC {
    private const long MB = 1 << 20;
    private const long MinSize = 16 * MB, Headroom = 4 * MB;
    private const int TicksPerRegion = 4;
    private const double Margin = 2;   // ms to spare after a collection's expected time
    private static readonly bool On = Environment.GetEnvironmentVariable("RM_TICK_GC") != "0";
    private static readonly long GrowMB =
        long.TryParse(Environment.GetEnvironmentVariable("RM_GC_GROW_MB"), out var grow) ? Math.Max(0, grow) : 64;
    private static readonly bool OpenInBgc = Environment.GetEnvironmentVariable("RM_GC_BGC_WAIT") == "1";
    private const double Gen2Timeout = 30;   // s: a gen2 not seen to finish by then is taken as finished
    private const double Gen2Spacing = 20;   // s: at least this long after one ends before another is started here
    private const int ShortForget = 50;      // tick ends in a row with no time to collect: forget the recent collections
    private const int CalmTicks = 50;        // ticks in a row within their time before an early gen2 may start
    // Gen2 left full of holes (engine G6, load-asleep-1030): background gen2s sweep but never compact, so once a join's
    // data has died gen2 kept ~250 MB of free room committed all game (477 MB with 223-278 free, 16 min of play). When it
    // is at least DefragMB free and 35% of gen2, the early gen2 is a compacting one instead, at most every 5 min.
    // RM_GC_DEFRAG_MB, default 128; 0 = never.
    private static readonly long DefragMB =
        long.TryParse(Environment.GetEnvironmentVariable("RM_GC_DEFRAG_MB"), out var defrag) ? Math.Max(0, defrag) : 128;
    private const double DefragSpacing = 300;   // s between compactions here
    // Held while anyone plays (the owner, 10-31, "Yes, hold it"): a compaction froze the server 0.36-0.5 s with 10 players
    // on (the quest maker's Q9 web test), so it waits until no player is connected, native or in a browser, and runs then.
    // Room stays committed meanwhile (~300 MB more with 10 players); background gen2s still sweep it for reuse.
    // RM_GC_DEFRAG_PLAYERS=1: compact while players are on too, as before.
    private static readonly bool DefragWithPlayers = Environment.GetEnvironmentVariable("RM_GC_DEFRAG_PLAYERS") == "1";
    private static DreamManager? _dream;
    private static int _defragHeld;   // tick ends a compaction was due but held for the players (since the last log line)

    private static IGameTiming? _timing;
    private static ISawmill? _log;
    private static uint _lastTick;
    // The most a region asks for (engine GG, load-asleep-1030): a join's sends grew regions to 192 MB, and the runtime
    // kept that room committed all game after (~300 MB above the live heap). RM_GC_MAX_MB (16 and up), default 64.
    private static readonly long MaxSizeFirst = (long.TryParse(Environment.GetEnvironmentVariable("RM_GC_MAX_MB"), out var max) && max >= 16 ? max : 64) * MB;
    private static long _maxSize = MaxSizeFirst;   // lowered if the runtime refuses a size as too big
    private static long _size;
    private static bool _open;
    private static long _openedAt, _lastTotal;   // the process's allocated bytes when the region opened, at the last tick's end
    private static readonly long[] _perTick = new long[20];       // what the process allocated in each recent tick
    private static readonly double[] _collects = new double[20];   // how long each recent collection took (ms)
    private static int _perTickAt, _collectsAt, _gcSeen, _gen2Seen, _shortRun, _calm;
    private static long _collectedAt;          // the process's allocated bytes at the last collection here
    private static bool _gen2;                 // a gen2 collection began that may still be running in the background
    private static long _gen2Since, _gen2EndedAt;   // when it was seen, when the last one was seen to end (Stopwatch timestamps)
    private static long _bgIndex = -1, _fullIndex = -1;   // the last finished background and full blocking collections
    private static long _oldAfter;             // bytes in use in gen2 and the large objects just after the last gen2
    private static TimeSpan _pauseSeen, _lastLog;

    // counts since the last log line
    private static int _ticks, _regions, _kept, _broken, _refused, _overruns, _short, _collected, _startGCs, _outside;
    private static int _gen2Done, _gen2Started, _skipped, _forgot;
    private static double _gen2StartWorst, _gen2SecsWorst;
    private static long _alloc;
    private static double _collectSum, _collectWorst, _startWorst, _ownPause, _outsidePause, _outsideWorst;

    public static void AfterTick() {
        if (!On) return;
        _timing ??= IoCManager.Resolve<IGameTiming>();
        var tick = _timing.CurTick.Value;
        if (tick == _lastTick) return;   // no tick ran in this frame
        var ran = _lastTick == 0 ? 1 : (int)(tick - _lastTick);
        _lastTick = tick;
        _ticks += ran;

        // what the process allocated since the last tick's end, per tick (regions are sized on the recent worst)
        var total = GC.GetTotalAllocatedBytes(false);
        if (_lastTotal != 0) {
            _alloc += total - _lastTotal;
            _perTick[_perTickAt++ % _perTick.Length] = (total - _lastTotal) / Math.Max(1, ran);
        }
        _lastTotal = total;
        if (_bgIndex < 0) {   // the first tick's end: what the load left
            _bgIndex = GC.GetGCMemoryInfo(GCKind.Background).Index;
            _fullIndex = GC.GetGCMemoryInfo(GCKind.FullBlocking).Index;
            _oldAfter = OldInUse();
            _collectedAt = total;
        }

        // a gen2 the runtime began by itself since the last tick's end (a budget ran out inside the tick)
        if (_gen2Seen != 0 && GC.CollectionCount(2) != _gen2Seen) Gen2Began();
        if (_gen2) Gen2Ended();

        // collections the runtime made by itself since the last tick's end: in a broken region, or with none open
        var gcs = GC.CollectionCount(0);
        if (_gcSeen != 0 && gcs != _gcSeen) {
            _outside += gcs - _gcSeen;
            _outsidePause += (GC.GetTotalPauseDuration() - _pauseSeen).TotalMilliseconds;
            var last = GC.GetGCMemoryInfo(GCKind.Any).PauseDurations;
            if (last.Length > 0) _outsideWorst = Math.Max(_outsideWorst, last[0].TotalMilliseconds);
        }

        var left = (_timing.LastTick + _timing.TickPeriod - _timing.RealTime).TotalMilliseconds;
        if (left <= 0) _overruns++;
        _calm = left <= 0 ? 0 : _calm + 1;
        var room = left >= Expected() + Margin;
        _shortRun = room ? 0 : _shortRun + 1;
        if (_shortRun >= ShortForget) {   // a slow collection must not keep every tick's end from collecting
            Array.Clear(_collects);
            _shortRun = 0;
            _forgot++;
        }
        var next = true;   // collect and open the next region (when there's room)
        if (_open) {
            var used = total - _openedAt;
            if (GCSettings.LatencyMode != GCLatencyMode.NoGCRegion) {   // the runtime ended it with a collection
                _open = false;
                Broken(used);
            } else if (used < _size / 2 || (!room && used < _size * 3 / 4)) {
                _kept++;
                next = false;
            } else {
                _open = false;
                try { GC.EndNoGCRegion(); } catch (InvalidOperationException) { Broken(used); }
            }
        }
        if (next) {
            if (!room) {
                _short++;
            } else if (_gen2 && !OpenInBgc) {   // no region while a background gen2 may run; gen0 once a region's worth is in
                _skipped++;
                if (total - _collectedAt >= Math.Max(MinSize, _size) / 2) Collect();
            } else {
                Collect();
                if (!_gen2 && GrowMB > 0) {
                    var used = OldInUse();
                    _oldAfter = Math.Min(_oldAfter, used);   // lower when a gen2 not seen to finish (the load's) took it lower
                    var spaced = Stopwatch.GetElapsedTime(_gen2EndedAt).TotalSeconds >= Gen2Spacing;
                    if (spaced && _calm >= CalmTicks && DefragDue()) Defrag();
                    else if (used - _oldAfter >= GrowMB * MB && spaced && _calm >= CalmTicks) StartGen2();
                }
                if (!_gen2 || OpenInBgc) Open();
            }
        }
        _gcSeen = GC.CollectionCount(0);
        _gen2Seen = GC.CollectionCount(2);   // after Open: a region's start counts as a gen2 without being one
        _pauseSeen = GC.GetTotalPauseDuration();
        Report();
    }

    private static void Broken(long used) {
        _broken++;
        _perTick[_perTickAt++ % _perTick.Length] = Math.Max(used, _size) / 2;   // the next ones at least twice as big
    }

    // The slowest of the recent collections (5 ms until there are some).
    private static double Expected() {
        var worst = 0.0;
        foreach (var ms in _collects) worst = Math.Max(worst, ms);
        return worst > 0 ? worst : 5;
    }

    private static void Collect() {
        var p0 = GC.GetTotalPauseDuration();
        var t0 = Stopwatch.GetTimestamp();
        var g2 = GC.CollectionCount(2);
        GC.Collect(0, GCCollectionMode.Forced, false);   // not blocking: if the runtime raises it to gen2, that runs in the background
        var ms = Stopwatch.GetElapsedTime(t0).TotalMilliseconds;
        _collectedAt = GC.GetTotalAllocatedBytes(false);
        var raised = GC.CollectionCount(2) != g2;
        if (raised) Gen2Began();
        _ownPause += (GC.GetTotalPauseDuration() - p0).TotalMilliseconds;
        if (!raised) _collects[_collectsAt++ % _collects.Length] = ms;   // a gen2's start says nothing of the next gen0
        _collected++;
        _collectSum += ms;
        _collectWorst = Math.Max(_collectWorst, ms);
    }

    // Bytes in use in gen2 and the large objects (their size less the free room in them) after the last collection.
    private static long OldInUse() {
        var gens = GC.GetGCMemoryInfo(GCKind.Any).GenerationInfo;
        var used = 0L;
        for (var g = 2; g <= 3 && g < gens.Length; g++) used += gens[g].SizeAfterBytes - gens[g].FragmentationAfterBytes;
        return used;
    }

    // A gen2 collection began: a blocking one has already finished; a background one runs on until Gen2Ended sees it end.
    private static void Gen2Began() {
        if (_gen2) return;
        _gen2 = true;
        _gen2Since = Stopwatch.GetTimestamp();
        Gen2Ended();
    }

    private static void Gen2Ended() {
        var bg = GC.GetGCMemoryInfo(GCKind.Background).Index;
        var full = GC.GetGCMemoryInfo(GCKind.FullBlocking).Index;
        var secs = Stopwatch.GetElapsedTime(_gen2Since).TotalSeconds;
        if (bg == _bgIndex && full == _fullIndex && secs < Gen2Timeout) return;
        _gen2 = false;
        _bgIndex = bg;
        _fullIndex = full;
        _oldAfter = OldInUse();
        _gen2EndedAt = Stopwatch.GetTimestamp();
        _gen2Done++;
        _gen2SecsWorst = Math.Max(_gen2SecsWorst, secs);
    }

    private static long _defragAt;   // Stopwatch timestamp of the last compaction here (0: none yet)
    private static int _defrags;
    private static double _defragMsWorst;

    private static bool DefragDue() {
        if (DefragMB <= 0 || (_defragAt != 0 && Stopwatch.GetElapsedTime(_defragAt).TotalSeconds < DefragSpacing)) return false;
        var gens = GC.GetGCMemoryInfo(GCKind.Any).GenerationInfo;
        if (gens.Length < 3) return false;
        long size = gens[2].SizeAfterBytes, free = gens[2].FragmentationAfterBytes;
        if (free < DefragMB * MB || free * 100 < size * 35) return false;
        if (!DefragWithPlayers && PlayersOn()) {
            _defragHeld++;
            return false;
        }
        return true;
    }

    // Anyone connected: a connection with a client (a native player's stays listed after they leave, without one).
    private static bool PlayersOn() {
        _dream ??= IoCManager.Resolve<DreamManager>();
        foreach (var connection in _dream.Connections)
            if (connection.Client != null) return true;
        return false;
    }

    // One compacting gen2, blocking, at a tick's end: the holes go and the room is handed back.
    private static void Defrag() {
        var gens = GC.GetGCMemoryInfo(GCKind.Any).GenerationInfo;
        long size = gens[2].SizeAfterBytes, free = gens[2].FragmentationAfterBytes;
        var before = GC.GetGCMemoryInfo(GCKind.Any).TotalCommittedBytes;
        var p0 = GC.GetTotalPauseDuration();
        var t0 = Stopwatch.GetTimestamp();
        var g2 = GC.CollectionCount(2);
        GCSettings.LargeObjectHeapCompactionMode = GCLargeObjectHeapCompactionMode.CompactOnce;
        GC.Collect(2, GCCollectionMode.Forced, true, true);
        var ms = Stopwatch.GetElapsedTime(t0).TotalMilliseconds;
        _ownPause += (GC.GetTotalPauseDuration() - p0).TotalMilliseconds;
        _defragAt = Stopwatch.GetTimestamp();
        _defrags++;
        _defragMsWorst = Math.Max(_defragMsWorst, ms);
        if (GC.CollectionCount(2) != g2) Gen2Began();
        _log ??= Logger.GetSawmill("tickgc");
        _log.Info($"tickgc defrag: gen2 {size / (double)MB:0} MB with {free / (double)MB:0} MB free compacted in {ms:0} ms; " +
                  $"committed {before / (double)MB:0} -> {GC.GetGCMemoryInfo(GCKind.Any).TotalCommittedBytes / (double)MB:0} MB");
    }

    // A gen2 collection in the background (not compacting), started at a tick's end.
    private static void StartGen2() {
        var p0 = GC.GetTotalPauseDuration();
        var t0 = Stopwatch.GetTimestamp();
        var g2 = GC.CollectionCount(2);
        GC.Collect(2, GCCollectionMode.Forced, false, false);
        _gen2StartWorst = Math.Max(_gen2StartWorst, Stopwatch.GetElapsedTime(t0).TotalMilliseconds);
        _ownPause += (GC.GetTotalPauseDuration() - p0).TotalMilliseconds;
        _gen2Started++;
        if (GC.CollectionCount(2) != g2) Gen2Began();
    }

    private static void Open() {
        var perTick = 0L;
        foreach (var a in _perTick) perTick = Math.Max(perTick, a);
        _size = Math.Clamp(perTick * TicksPerRegion + Headroom, MinSize, _maxSize);
        var c0 = GC.CollectionCount(0);
        var p0 = GC.GetTotalPauseDuration();
        var t0 = Stopwatch.GetTimestamp();
        try {
            if (GC.TryStartNoGCRegion(_size, true)) {   // true: never a full blocking collection to make the room
                _open = true;
                _regions++;
                _openedAt = GC.GetTotalAllocatedBytes(false);
            } else {
                _refused++;
            }
        } catch (ArgumentOutOfRangeException) {   // more than the runtime allows: ask for less from now on
            _refused++;
            _maxSize = Math.Max(MinSize, _size * 3 / 4);
        } catch (InvalidOperationException) {     // already in a region (not expected)
            _refused++;
        }
        _startWorst = Math.Max(_startWorst, Stopwatch.GetElapsedTime(t0).TotalMilliseconds);
        _ownPause += (GC.GetTotalPauseDuration() - p0).TotalMilliseconds;
        _startGCs += GC.CollectionCount(0) - c0;
    }

    private static void Report() {
        var now = _timing!.RealTime;
        var s = (now - _lastLog).TotalSeconds;
        if (s < 10) return;
        if (_lastLog != TimeSpan.Zero) {
            _log ??= Logger.GetSawmill("tickgc");
            _log.Info($"tickgc s={s:0.0} ticks={_ticks} alloc_mb_s={_alloc / (double)MB / s:0.0} size_mb={_size / (double)MB:0.0} regions={_regions} kept={_kept} " +
                      $"broken={_broken} refused={_refused} overrun={_overruns} short={_short} collected={_collected} collect_ms_avg={_collectSum / Math.Max(1, _collected):0.00} " +
                      $"collect_ms_worst={_collectWorst:0.00} own_pause_ms={_ownPause:0.0} start_gcs={_startGCs} start_ms_worst={_startWorst:0.00} " +
                      $"outside_gcs={_outside} outside_pause_ms={_outsidePause:0.0} outside_worst_ms={_outsideWorst:0.0} max_mb={_maxSize / MB} " +
                      $"gen2_done={_gen2Done} gen2_started={_gen2Started} gen2_start_ms_worst={_gen2StartWorst:0.00} gen2_s_worst={_gen2SecsWorst:0.0} skipped={_skipped} forgot={_forgot} " +
                      $"old_mb={OldInUse() / (double)MB:0} old_after_mb={_oldAfter / (double)MB:0} committed_mb={GC.GetGCMemoryInfo(GCKind.Any).TotalCommittedBytes / (double)MB:0} " +
                      $"defrags={_defrags} defrag_ms_worst={_defragMsWorst:0} defrag_held={_defragHeld}");
        }
        _lastLog = now;
        _ticks = _regions = _kept = _broken = _refused = _overruns = _short = _collected = _startGCs = _outside = 0;
        _gen2Done = _gen2Started = _skipped = _forgot = _defragHeld = 0;
        _gen2StartWorst = _gen2SecsWorst = 0;
        _alloc = 0;
        _collectSum = _collectWorst = _startWorst = _ownPause = _outsidePause = _outsideWorst = 0;
    }

    public static void Stop() {
        if (!_open) return;
        _open = false;
        if (GCSettings.LatencyMode != GCLatencyMode.NoGCRegion) return;
        try { GC.EndNoGCRegion(); } catch (InvalidOperationException) { }
    }
}
