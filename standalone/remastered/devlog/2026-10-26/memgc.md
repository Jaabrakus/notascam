# Server memory: live data vs footprint (2026-10-26, memgc session)

With a player and 200 units the server holds 2.5 GB, but only **0.78 GB of it is live data**. The rest is room the .NET
collector keeps: garbage and free space, most of it left over from loading the map awake. `DOTNET_GCConserveMemory=5`
takes ~0.5 GB of that back later in a run; building tiles asleep at load is the fix for the rest.

## Done
- Two real-client runs, 200 Dwarves, orders every 60 s, 6.5 min, one after the other on the installed engine (v12e):
  `memgc-base` (today's settings) and `memgc-conserve` (`DOTNET_GCConserveMemory=5`). Reports:
  `reports/server-cost/memgc-*.md`, per-second GC metrics in `memgc-*-metrics.json`.
- Probe `reports/server-cost/memgc/memgc_probe.dm`: 3 min in, `rm_heap_info()` (full blocking compacting collection) gives
  the live heap; vmmap footprint every 120 s.

## Numbers

| | base | ConserveMemory=5 |
|---|---:|---:|
| live data after a full compacting collection | **784 MB** | **788 MB** |
| ...of it big arrays (per-tile tables, sleeping-tile blocks) | 459 MB | 364 MB |
| GC committed at the start of the measure | 2,273 MB | 2,379 MB |
| GC committed just before the forced collection | 2,797 MB | 2,115 MB |
| GC committed just after it | 997 MB | 1,128 MB |
| footprint (vmmap) 2 min in | 2,560 MB | 2,458 MB |
| footprint at the end | 1,946 MB | **1,434 MB** |
| GC committed at the end | 1,647 MB (837 MB of it free space) | **1,101 MB** |
| server allocation | 53 MB/s | 49 MB/s |
| runtime errors / saves changed | 0 / no | 0 / no |

- ConserveMemory compacted on its own twice (2,675 -> 2,116 MB at ~80 s, 2,243 -> 997 MB at ~330 s), with no slow second
  from it. Between those it still floated up to ~2.2 GB.
- The start of the measure already held ~2.3 GB committed with the big-array heap at 860-984 MB (live: 364-459 MB): the
  map is built awake at load, then the sweep puts ~3.9 million tiles to sleep, and their objects die in the oldest
  generation, where the collector keeps the room.

## Caveats
- The probe's object report (`rm_memory_report`) enumerates every turf, which **wakes the whole map**: heap to ~1.76 GB
  and the slowest second of both runs (9.2 s base, 3.8 s conserve) right after it. Samples from 3 min on include that
  wake and the sweep putting it back to sleep; the heap reading and the earlier samples are clean.
- The Mac had other load during the base run (load average 7-11 vs 3-4; the server's pages were compressed), so the
  runs' CPU and stall numbers aren't comparable. Memory numbers are.

## Landed (09:4x): the load pass + ConserveMemory
- `mac-app/launch.zsh`: `export DOTNET_GCConserveMemory=5` (in the app since build 56); `tools/web_host.py`: the same,
  plus `DOTNET_gcServer=0` (it ran the server with Server GC, the setting that once held 6.7 GB).
- `game/Code/Remastered/Regions.dm`: the **load pass**. The moment the world has loaded, every tile that can sleep does,
  the areas' turf sets are trimmed and one full compacting collection runs (`rm_heap_info`, now declared in Native.dm
  with `RM_NATIVE_HEAP`; the map-memory tests' own declarations are guarded by it). `RM_LOAD_SLEEP=0` turns it off.
  Restore point: `restore-points/before-load-sleep-20261026/`.

| full world, no window, both with ConserveMemory=5 | today's game | load pass |
|---|---:|---:|
| footprint (vmmap), each minute for 5 min | 2,355 MB, flat | **1,229-1,331 MB** |
| GC committed | 2,280 MB | 1,194-1,249 MB |
| the load pass itself | - | 3,992,514 tiles asleep in 1.0 s, compaction 0.3 s, live heap 687 MB after |
| runtime errors / saves changed | 0 / no | 0 / no |

- In the app: memload's build at 09:40 (compiled game sha256 e661685c), handed to the user to test.
- Arena checks on the candidate: clip PASS, gather PASS (wood 88, stone 632 stored in 5 min), obey 26/32 with the same 6
  chop cases as the v8 reference (`tests/obey-v8-checks.json`). Those six are the test, not the pass: Tend living is on
  by default (Yield.dm), so a chop order leaves a tree at half by design, and the test still expects it felled.
- Not done: the 200-unit real-client run with the load pass (stopped so the user could test the build), obey on today's
  game for comparison. Watch: with the load pass the heap still climbs ~0.5 MB/s over the 5 min (tiles the world wakes,
  until the sweep re-sleeps them a minute later); a 30-min run would show whether it levels off.
- Reports: `reports/server-cost/memload-world-{cand,base}.md` and `-metrics.json`.

## Obey test brought up to Tend living (10:0x)
- `tests/obey_test.dm`: the six chop cases use `ObChopTree` (HP 150 of a grown 250, so the worker has to walk over and
  chop to the half mark) and pass when the tree reached its tending mark (`RemasterTendReached`), or was felled for a
  worker who doesn't tend. `ObTree` itself is unchanged (ten other tests use it). `tools/check_obey.py` on game/ with the
  load pass: **31/32** (was 26/32).
- The one left is a real game bug the old 20-HP trees hid: **three units chopping one tended tree fell it** (150 -> -6 HP).
  Veins are held per blow (`RemasterYieldBefore`), trees only at the order tick (Orders.dm `RemasterTendReached`), so
  blows between checks run past the mark. Single workers overshoot a little too (stop at 87-100, mark 125).
- **Fixed and landed (09:5x, the user's go):** a tended tree is held on every blow, as a vein is (`Yield.dm`
  `RemasterTreeMark`, `RemasterYieldBefore(T, M)`, the clamp in `RemasterYieldAfter`; `Orders.dm` passes the worker).
  Obey **32/32**: every chop tree, the group's too, stops at exactly 125/250. Gather PASS (wood 88 as before; stone 606
  vs 632, which moves with tick cost). Yield PASS on both (fix: trees left at half stop at hp 125; before: 93).
  Restore point: `restore-points/before-tree-hold-20261026/`. In the app: memload's build at 09:56 (compiled game
  sha256 fcd5331c), with the load pass and ConserveMemory too.

## Points to
1. Not unit memory: live data is 0.78 GB, already under the 1 GB goal at 200 units.
2. **Tiles built asleep at load** (planning/MAP_MEMORY.md): no ~0.85 GB of tile objects dying in the old generation, and
   no 2.5-3.7 GB load spike. The biggest single piece.
3. **`export DOTNET_GCConserveMemory=5`** in mac-app/launch.zsh: one line, -0.5 GB by the end of a run, no stalls seen.
4. Later: the ~50 MB/s the server allocates (HUD and 3D sends) is what refills the slack between collections.
5. Not a heap hard limit yet: the whole-map wake reached 1.76 GB, which a limit would turn into a crash.
