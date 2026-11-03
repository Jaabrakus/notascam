// Remastered: pause and game speed. DM code sleeps and spawns in ticks; this is the
// tick those delays (and world.time) follow. Paused it stands still while player
// commands still run; at speed 2 or 3 it advances that many ticks per engine tick.
// DM sets it with world.game_state = 0..3 (a hub-only setting this engine never uses;
// see Code/Remastered/Speed.dm). Play is capped at 4 (the checks run at 4).
// A test world's server may set another cap with RM_MAX_SPEED=N (1 to 32; engine v5.1,
// 2026-10-24). Above 4 it takes the extra steps only while the engine tick has time
// left (never falling further behind), and logs the game seconds it ran per real second
// every 10 s. Without the variable play runs exactly as before.
// After a stall the engine runs the ticks it owes back to back (up to 5, Robust's GameLoop): fights and walks resolved
// in a few ms with no player's order able to arrive between them. Since engine v27 (U2, planning/
// SERVER_UPGRADES_PLAN_2026-10-30.md, as Quake II's server never runs more than one tick late) only the first
// RM_CATCH_UP of those (default 2) advance the game; the rest run like a paused tick (commands run, the game's time
// stands), so the world lets the rest of the stall go. A tick is owed when it starts a whole tick or more after its
// time. RM_CATCH_UP=5 (or more) runs every owed tick, as before; test worlds above speed 4 always do.
using System;
using Robust.Shared.IoC;
using Robust.Shared.Log;
using Robust.Shared.Timing;

namespace OpenDreamRuntime;

public static class RemasterClock {
    public static int Speed = 1;
    public static readonly int MaxSpeed = Math.Clamp(int.TryParse(Environment.GetEnvironmentVariable("RM_MAX_SPEED"), out var max) ? max : 4, 1, 32);
    private static uint? _now;
    private static IGameTiming? _timing;
    private static long _steps, _engineTicks;
    private static TimeSpan _lastLog;
    public static readonly int CatchUp = Math.Clamp(int.TryParse(Environment.GetEnvironmentVariable("RM_CATCH_UP"), out var c) ? c : 2, 0, 5);
    private static int _owed, _owedRun, _owedDropped;   // this stall: owed ticks seen, run, let go
    private static double _owedLate;                    // ...and how late the first was, ms
    private static int _logStalls, _logOwed, _logDropped;   // stalls with ticks let go since the last log line
    private static double _logWorst;
    private static TimeSpan _logAt;                     // Zero: no line yet

    public static uint Now => _now ?? IoCManager.Resolve<IGameTiming>().CurTick.Value;

    public static void Run(Action process) {
        _timing ??= IoCManager.Resolve<IGameTiming>();
        _now ??= _timing.CurTick.Value;
        if (Speed <= 0) { process(); return; }       // paused: commands run, sleeps wait
        if (CatchUp < 5 && MaxSpeed <= 4 && Owed()) { process(); return; }   // an owed tick past RM_CATCH_UP: as if paused
        var speed = Math.Min(Speed, MaxSpeed);
        var steps = 0;
        for (; steps < Math.Min(speed, 4); steps++) {   // up to 4: every step, as in play
            _now++;
            process();
        }
        // above 4 (a test world): more steps while this tick leaves 30% of its time for the rest of the engine's work
        while (steps < speed && _timing.RealTime - _timing.LastTick < _timing.TickPeriod * 0.7) {
            _now++;
            process();
            steps++;
        }
        if (MaxSpeed > 4) Report(steps);
    }

    // True when this engine tick is owed after a stall and is past the RM_CATCH_UP that advance the game. GameLoop moves
    // LastTick on by a tick before running one, so RealTime - LastTick is how late this tick starts.
    private static bool Owed() {
        var late = _timing!.RealTime - _timing.LastTick;
        if (late < _timing.TickPeriod) {
            if (_owed > 0) {
                if (_owedDropped > 0) LogStall();
                _owed = _owedRun = _owedDropped = 0;
            }
            return false;
        }
        if (_owed++ == 0) _owedLate = late.TotalMilliseconds;
        if (_owedRun < CatchUp) { _owedRun++; return false; }
        _owedDropped++;
        return true;
    }

    // One line at most every 10 s: a server running behind for a while (a big battle) has a short stall every second.
    private static void LogStall() {
        _logStalls++; _logOwed += _owed; _logDropped += _owedDropped;
        _logWorst = Math.Max(_logWorst, _owedLate);
        var now = _timing!.RealTime;
        if (_logAt != TimeSpan.Zero && now - _logAt < TimeSpan.FromSeconds(10)) return;
        Logger.GetSawmill("clock").Info(_logStalls == 1
            ? $"clock catch-up: {_owed} owed ticks after a stall ({_owedLate:0} ms late), {_owedRun} run, {_owedDropped} let go (RM_CATCH_UP={CatchUp})"
            : $"clock catch-up: {_logStalls} stalls since the last line, {_logOwed} owed ticks, {_logDropped} let go, the worst {_logWorst:0} ms late (RM_CATCH_UP={CatchUp})");
        _logAt = now;
        _logStalls = _logOwed = _logDropped = 0;
        _logWorst = 0;
    }

    private static void Report(int steps) {
        _steps += steps;
        _engineTicks++;
        var now = _timing!.RealTime;
        var s = (now - _lastLog).TotalSeconds;
        if (s < 10) return;
        if (_lastLog != TimeSpan.Zero)
            Logger.GetSawmill("clock").Info($"clock speed={Speed} max={MaxSpeed} game_s_per_real_s={_steps * _timing.TickPeriod.TotalSeconds / s:0.00} steps_per_tick={_steps / (double)Math.Max(1, _engineTicks):0.00} engine_ticks={_engineTicks} s={s:0.0}");
        _lastLog = now;
        _steps = _engineTicks = 0;
    }
}
