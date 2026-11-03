# perf-watch, second pass (10-27)

Same method as 10-26 (devlog/2026-10-26/perf-watch.md). Sources rebuilt and hash-verified: 68 = 6587c5da, 88 = 26b3f4e7 (app compiled 18:22). Pairs run old/new interleaved, speed-4 scenes, the Mac otherwise free
(one background lead job at times). Build 69 was folded into later builds; the lead asked for 88 vs 68 in one go.

## Build 88 vs 68 (today's movement and step work)
- **2,000 workers, worst tick: 2,807 / 1,398 / 1,054 ms -> 1,671 / 468 / 546 ms (-48%, every pair 0.33-0.60): faster.** Same pieces stored (21.4k vs 21.2k).
- 2,000 workers avg and p95: same within noise (pairs 0.84-1.83 and 0.88-1.90): two pairs ~-8%/-16%, one pair 88 high (345 ms avg, 612 ms p95) while 68's was 189/323: unexplained, likely load, not repeated.
- 200 workers, heap (114 MB / 383-400 MB), walk latency scene (4 pairs, 0.36-2.63), HUD script per update (203 units: 2.3-2.7 ms, same), 0 console errors: same within noise.
- **100v100 battle: not settled.** avg ms/tick 72.8/63.2/67.8/68.7 -> 75.7/140.8/93.3/56.9 (pairs 1.04, 2.23, 1.38, 0.83), worst tick 196-251 -> 240-925. 88 was higher in 3 of 4 pairs; swings equal. Needs a quiet-Mac repeat before calling it; the label movers say "other DM" +28 ms/tick, track/orders/attack +4.7.
- **HUD page: 1,655 -> 1,866 KB (+13%, +211 KB)**, no script cost.
| metric (per-run values, A then B pairs) | build 68 | build 88 | change | verdict |
|---|---|---|---|---|
| 100v100 battle (200 units fighting, speed 4): slow ticks | 150 / 38 / 46 / 86 | 118 / 462 / 288 / 62 | +252% | same within noise (pairs 0.72-12.16) |
| 142 units idle + orders (walk latency scene): worst tick ms | 6 / 5 / 15 / 8 | 12 / 15 / 5 / 14 | +88% | same within noise (pairs 0.33-3.00) |
| 100v100 battle (200 units fighting, speed 4): worst tick ms | 223 / 251 / 229 / 196 | 240 / 925 / 345 / 336 | +61% | same within noise (pairs 1.08-3.69) |
| 2,000 workers gathering (speed 4): worst tick ms | 2807 / 1398 / 1054 | 1671 / 468 / 546 | -48% | faster (pairs 0.33-0.60) |
| 142 units idle + orders (walk latency scene): p95 window ms/tick | 1.8 / 0.8 / 2.4 / 2.2 | 2.7 / 2.5 / 0.9 / 2.6 | +34% | same within noise (pairs 0.38-3.12) |
| 100v100 battle (200 units fighting, speed 4): p95 window ms/tick | 123.4 / 104 / 100.4 / 119.4 | 107.6 / 317.4 / 169.4 / 113.8 | +32% | same within noise (pairs 0.87-3.05) |
| 100v100 battle (200 units fighting, speed 4): avg ms/tick | 72.81 / 63.15 / 67.78 / 68.68 | 75.67 / 140.8 / 93.28 / 56.91 | +21% | same within noise (pairs 0.83-2.23) |
| HUD page size (KB) | 1654.9 | 1865.6 | +13% | one pair, no spread yet |
| 2,000 workers gathering (speed 4): p95 window ms/tick | 322.8 / 305.2 / 341.4 | 611.8 / 270.8 / 301.4 | -11% | same within noise (pairs 0.88-1.90) |
| HUD script ms per update, 203 units, quiet (headless Chrome, median of 15 rounds) | 1.1 | 1.1 | -7% | same within noise (under 1 ms) |
| HUD script ms per update, 203 units, none (headless Chrome, median of 15 rounds) | 2.8 | 2.7 | -7% | same within noise (under 1 ms) |
| 2,000 workers gathering (speed 4): avg ms/tick | 189.05 / 185.28 / 215.95 | 345.48 / 172.51 / 182.06 | -7% | same within noise (pairs 0.84-1.83) |
| HUD script ms per update, 203 units, one (headless Chrome, median of 15 rounds) | 2.4 | 2.3 | -5% | same within noise (under 1 ms) |
| 142 units idle + orders (walk latency scene): avg ms/tick | 1.36 / 0.49 / 1.3 / 1.58 | 1.62 / 1.29 / 0.47 / 1.43 | +5% | same within noise (pairs 0.36-2.63) |
| server heap in use after first pass, 2,000 units (MB) | 400.3 | 382.5 | -4% | one pair, no spread yet |
| 200 workers gathering (speed 4): p95 window ms/tick | 29.4 / 28.2 | 26.4 / 28.8 | -4% | same within noise (pairs 0.90-1.02) |
| HUD script ms per update, 203 units, all (headless Chrome, median of 15 rounds) | 2.5 | 2.7 | -3% | same within noise (under 1 ms) |
| 200 workers gathering (speed 4): worst tick ms | 66 / 56 | 66 / 55 | -1% | same within noise (pairs 0.98-1.00) |
| server heap in use after first pass, 200 units (MB) | 114.1 / 114 | 114.3 / 114.4 | +0% | same within noise (pairs 1.00-1.00) |
| 200 workers gathering (speed 4): avg ms/tick | 17.5 / 18.92 | 18.36 / 17.9 | -0% | same within noise (pairs 0.95-1.05) |
| 2,000 workers gathering (speed 4): slow ticks | 1695 / 1691 / 1694 | 1694 / 1694 / 1690 | -0% | same within noise (pairs 1.00-1.00) |
| 100v100 battle (200 units fighting, speed 4): work done (swings) | 4949 / 4827 / 5061 / 5171 | 4908 / 4945 / 4952 / 5027 | | context (same work = fair comparison) |
| 100v100 battle (200 units fighting, speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM +18.91; track/orders +3.47; track/orders/attack +3.04 |
| 2,000 workers gathering (speed 4): work done (pieces stored) | 21414 / 21354 / 21444 | 21207 / 21256 / 21171 | | context (same work = fair comparison) |
| 2,000 workers gathering (speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM +33.34; track/orders +1.06; track/settlement +1.00 |
| 200 workers gathering (speed 4): slow ticks | 0 / 0 | 0 / 0 |  | n/a |
| 200 workers gathering (speed 4): work done (pieces stored) | 1962 / 2006 | 1966 / 1985 | | context (same work = fair comparison) |
| 200 workers gathering (speed 4): biggest per-label movers (ms/tick, B-A) | | | | creature move -0.11; creature walk tick -0.09; track/settlement +0.06 |
| 142 units idle + orders (walk latency scene): slow ticks | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |  | n/a |
| 142 units idle + orders (walk latency scene): work done (group-move first-step ticks) | 0.02 / 0.02 / 0.02 / 0.02 | 0.06 / 0.02 / 0.02 / 0.02 | | context (same work = fair comparison) |
| 142 units idle + orders (walk latency scene): biggest per-label movers (ms/tick, B-A) | | | | track/orders +0.05; ledger in a tick -0.03; track/patrol -0.02 |
| HUD script ms per update, 203 units, another (headless Chrome, median of 15 rounds) | 1.6 | 1.5 | +0% | same within noise (under 1 ms) |
| HUD console errors on load + updates | 0 | 0 | | clean |


## 100v100 battle, narrowed by build (21:00, 5 rotating rounds, avg ms/tick, speed 4; load average 7-17 from other jobs: noisy)
Sources 85/86/87 rebuilt from live game/ minus restore points after each build's "every landing up to" time (not hash-verified: their app copies are gone); 68 and 88 are hash-verified.
| build | round 1 | 2 | 3 | 4 | 5 | best of 5 | median | median ratio to 68 (pairs) |
|---|---|---|---|---|---|---|---|---|
| 68 | 71.8 | 166.8 | 171.3 | 81.8 | 85.2 | 71.8 | 85.2 | 1.00 |
| 85 (before movement) | 65.2 | 226.7 | 72.3 | 112.2 | 82.8 | 65.2 | 82.8 | 0.97 |
| 86 (walking + pace floor) | 162.4 | 234.8 | 101.3 | 170.9 | 77.3 | 77.3 | 162.4 | 1.41 |
| 87 (step fixes) | 140.6 | 159.4 | 75.9 | 141.8 | 77.3 | 75.9 | 140.6 | 0.96 |
| 88 (far steps) | 108.4 | 229.2 | 149.3 | 120.5 | 100.6 | 100.6 | 120.5 | 1.37 |
Reading it: rounds 2-3 are load spikes for every build. Best-of-5 (the least load-hit run) is 65-77 ms for 68, 85, 86, 87 but 101 ms for 88, and 88 is above 68 in 4 of 5 pairs (1.51, 1.37, 0.87, 1.47, 1.18),
so a battle cost of roughly +30-40% first shows in 88 (far steps); 86 and 87 look like 68 on their best runs but have bad medians (load). Not conclusive under this load: repeat on a quiet Mac (best-of-N again).

## Far steps on vs off, same build (21:11, 100v100 battle, 5 alternating rounds, RM_FAR_STEPS unset vs 0, source = live game/ at 21:02)
| | on (default) | off (RM_FAR_STEPS=0) |
|---|---|---|
| avg ms/tick per round | 96.6 / 63.2 / 65.3 / 126.1 / 108.1 | 94.6 / 102.4 / 61.1 / 62.4 / 88.4 |
| best / median | 63.2 / 96.6 | 61.1 / 88.4 |
| p95 window median | 152.6 | 128.0 |
| creature walk tick, ms/tick median | 4.17 | 3.99 |
| creature move | 4.10 | 3.95 |
| swings (same work) | 4.87-5.05k | 4.88-5.04k |
Off/on per round: 0.98, 1.62, 0.94, 0.50, 0.82 (median 0.94). No far-step label ranks in the profile; "other DM" (route searches, ~72-78 ms/tick) dominates both. Verdict: far steps is NOT the cause of the battle slowdown seen in 88 (best 63 vs 61, within noise); the load noise on this Mac (rounds swing 61-126 ms) is larger than any on/off difference.
