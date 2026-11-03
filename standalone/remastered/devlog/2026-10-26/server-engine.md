# Server, engine and memory (2026-10-26, server-engine session)

Picked up the server performance, engine and memory workstream. Nothing changed in `game/`, the engine or the app today.

## The user's game, watched passively (12:51-13:20, the 09:56 app with the load pass)
Read from the kernel's counters (proc_pid_rusage: Activity Monitor's "Memory"; no vmmap, no stalls) every 15 s,
`reports/server-cost/memcheck/watch_live.py`, data `reports/server-cost/live-play-20261026*.jsonl`. The user's own
village (unit save 3.26 MB, so a few units, not 200).

| | Memory (footprint) | Note |
|---|---:|---|
| Server, while loading | 2,402 MB peak | the map is built awake, then the load pass sleeps it |
| Server, load pass | 3,991,437 tiles asleep in 952 ms, compaction 285 ms, 688 MB live | from the world's ErrorLog.txt |
| Server, playing | 1,300 -> 1,620 MB (median 1,480) | climbed ~13 MB a minute once play got busy; not level after 30 min |
| Client | 658-692 MB | flat |
| 3D page (WebKit) | 408-747 MB (median 518) | |
| WebKit GPU process | 101-323 MB | |
| ps RSS of the server | median 304 MB | misses compressed memory: don't use RSS on macOS |

- The Mac's load average was a median of 14 and peaked at 32 (other sessions' test runs). The worst stall of the session
  (12:59-13:01: 1.5 s of ticks lost, Shed level 3 for 15 s) fell inside that peak.

## Fight hitch (the user: "i click during a high stacks fight and the game hitches")
Headless arena, speed 1, `reports/server-cost/fightclick/fight_click_check.dm`: 100 armoured humans against 100 Orc Scout
raiders, the whole group clicked every 6 s (attack a foe, attack-move past, move into the melee). Report:
`fight_report.py`. On a loaded Mac, nice 10.

| 144 s of fight | morale on (today) | morale off |
|---|---:|---:|
| ticks over 100 ms | 123 | 59 |
| average DM per tick | 25% | 17% |
| worst tick | 393 ms | 280 ms |
| memory allocated | 63 MB/s | 35 MB/s |
| morale's cost | 76.5 ms/s, costliest in 134 slow ticks | - |

- Cause: every fighting unit's morale tick (Morale.dm RmMoraleTick) scans all tiles within 4 (and 6 for a rally) once a
  second, and the clocks start in step at first contact, so they all land in one tick.
- The click itself: an attack on a foe 0-2 ms; an attack-move up to 123-138 ms and a move into the melee up to 66-82 ms
  at 70-96 units selected (the formation plan in the click's tick).
- Next (the user's direction): morale computed on events and per zone, not scanned per unit per second. Morale.dm is
  combat's; staged with its OK, landed through the coordinator.

## Morale by zone, step 1: built, checked, READY (14:0x)
The user: "Yes: build step 1 ... show me the fight numbers before it lands", then "Land morale step 1". Staged in
`reports/server-cost/staged/morale-zones/`: Morale.dm's six looks round a unit use the unit grid (RmUnitsNear,
Native.dm). Shadow mode: 34,500 looks, 0 differences. 100 v 100 fight: ticks over 100 ms 52 -> 12, worst tick
352 -> 170 ms, morale 55.5 -> 20.8 ms/s. morale 25/25, facing 15/15, parry 2/2, combat 32/32; battles within noise;
combat's rules check passed. Sent to the coordinator for build 58 (it lands it; restore point in the land script).

## 200 units, real window, the load pass on (13:54-14:02; build 57's game, v12e, ConserveMemory)
`reports/server-cost/memcheck-200-load.md`; footprint from proc_pid_rusage (no vmmap), GC from the engine's metrics.
The Mac was loaded by other sessions' tests (load average 7-24), so tick counts aren't comparable with earlier runs.

| | 10-26 morning, no load pass (memgc-conserve) | load pass |
|---|---:|---:|
| server footprint while measured | 2,458 -> 1,434 MB (vmmap, 3 samples) | 1,536 -> 1,799 MB (median 1,793) |
| server peak while loading | - | 2,408 MB |
| GC committed, median | 2,218 MB | 1,549 MB |
| GC heap minus gaps, median | 992 MB | 962 MB |
| GC pauses over 100 ms | 7 (the probe forced some) | 1 |
| client footprint | - | 702-719 MB |

- Still climbing ~18 MB a minute at the end (as in the user's own session): the 30-minute run after build 58 says
  whether it levels off.
- Click to move, 203 units, 10 orders: the first unit steps 2-3 ticks after the click (0.2-0.3 s), half in 3-6 ticks,
  90 % in 6-29 (median 1.0 s), all in 26-64 (median 4.3 s: the back of the formation waits its turn). The order call
  itself 10-40 ms.
- Not done (the freeze; after build 58): the same run with the load pass off, back to back, and the 30-minute run.
