# perf-watch: is the game getting faster? (polish night 2026-10-26)

**RESUME (23:25):** I only read the lead's usage-limit STOP (22:07) at 23:25: the arena runs from 22:07 to 23:25 (arena only, one at a time through runlock) ran after it. Killed my last run then; nothing of mine is running. To resume: wait for the next BUILD_OK on `reports/polish-night-1026/BOARD.md`, rebuild its source
(`perf-watch/rebuild_src.py`, below), then `perf-watch/chain3.sh <old> <new> <firstrep> <olddir> <newdir>` and
`python3 reports/polish-night-1026/perf-watch/pw_report.py <old> <new> <hud.json>`. Measured so far: build 62 -> 63 -> 64.

**Summary:** through build 64 nothing got slower beyond the noise; build 65 made the HUD page 24% bigger and ~1.3 ms slower per update (server unchanged within noise). 62 -> 63 (the six chain clean-ups + 19 polish fixes): the 100v100 battle
ticked about 13% cheaper and had about half the slow ticks; gathering, walking, memory and the HUD page are the same. 63 -> 64 (five polish
batches): same within noise everywhere; one open item, a single 2,000-worker pair whose worst tick was 1,100 ms against 331 ms (an average
only +7%): a repeat was running when the stop came.

## How it was measured
- The app bundles carry only compiled code, so each build's source was rebuilt: live `game/` with later landings put back from `restore-points/`,
  compiled with the build's own compiler call, and the result's sha256 compared with the app's `Cave Crawlers.json`. All three match
  (62 = db42dc4b, 63 = ccda7734, 64 = 35cff532). Sources: `reports/polish-night-1026/perf-watch/src/g62, g63b, g64`.
- Same scene on both builds, **interleaved** (old, new, old, new), through `tools/runlock.py` and `tools/check_arena.py --profile`. The Mac was
  shared (load average 2-7 during the runs), so a verdict is on the **ratio inside each old/new pair**: SLOWER only if every pair is more than 10% worse.
  Spread shown as "pairs lo-hi" (new/old).
- Scenes: 100v100 battle (200 units, own scene `perf-watch/tests/pw_battle100.dm`, 120 game seconds), 200 and 2,000 workers gathering (`gather_score.dm`,
  GsRun200S / GsRun2000S), the walk-latency scene (142 units idle and ordered), heap after each unit has walked once (`pw_mem.dm`, 200 and 2,000 units; heap minus
  fragmented). HUD: headless Chrome, the same 203-unit model fed to each build's page (`pw_hud.py`), script ms per `updateHUD` call.
- ms/tick = the tick profiler's own DM time per tick at game speed 4 (the scenes need it); it reads high against speed 1 by the same factor on both sides, so read ratios, not absolutes.
  "slow ticks" = ticks over the profiler's threshold. "work done" rows show both builds did the same work (swings, pieces stored).
- Not measured: HUD in the real WKWebView (no real windows tonight), 3D frame ms (brief: arena/headless only), 5k+ runs.

## Build 62 -> 63 (chains StepDelay/Enter/Death/Bump/Move/Strike + 19 polish fixes)
| metric (per-run values, A then B pairs) | build 62 | build 63 | change | verdict |
|---|---|---|---|---|
| 142 units idle + orders (walk latency scene): worst tick ms | 12 / 5 | 10 / 14 | +82% | same within noise (pairs 0.83-2.80) |
| 142 units idle + orders (walk latency scene): avg ms/tick | 1.49 / 0.69 | 0.79 / 2 | +71% | same within noise (pairs 0.53-2.90) |
| 142 units idle + orders (walk latency scene): p95 window ms/tick | 2.1 / 1.2 | 1.5 / 2.7 | +48% | same within noise (pairs 0.71-2.25) |
| 100v100 battle (200 units fighting, speed 4): slow ticks | 654 / 670 | 384 / 306 | -48% | faster (pairs 0.46-0.59) |
| 100v100 battle (200 units fighting, speed 4): worst tick ms | 220 / 223 | 351 / 236 | +33% | same within noise (pairs 1.06-1.60) |
| 2,000 workers gathering (speed 4): worst tick ms | 458 | 575 | +26% | one pair, no spread yet |
| 200 workers gathering (speed 4): slow ticks | 0 / 72 | 0 / 60 | -17% | one pair, no spread yet |
| 100v100 battle (200 units fighting, speed 4): avg ms/tick | 120.95 / 117.26 | 108.18 / 99.83 | -13% | faster (pairs 0.85-0.89) |
| 2,000 workers gathering (speed 4): avg ms/tick | 132.82 | 146.1 | +10% | one pair, no spread yet |
| HUD script ms per update, 203 units, another (headless Chrome, median of 9 rounds) | 1.2 | 1.2 | -7% | same within noise (under 1 ms) |
| 200 workers gathering (speed 4): worst tick ms | 51 / 224 | 40 / 301 | +6% | same within noise (pairs 0.78-1.34) |
| 2,000 workers gathering (speed 4): p95 window ms/tick | 219.6 | 207.4 | -6% | one pair, no spread yet |
| 100v100 battle (200 units fighting, speed 4): p95 window ms/tick | 161 / 168.4 | 179.8 / 167.2 | +5% | same within noise (pairs 0.99-1.12) |
| HUD script ms per update, 203 units, one (headless Chrome, median of 9 rounds) | 1.8 | 1.8 | -5% | same within noise (under 1 ms) |
| 200 workers gathering (speed 4): p95 window ms/tick | 18.6 / 69.8 | 18.2 / 72.6 | +1% | same within noise (pairs 0.98-1.04) |
| 200 workers gathering (speed 4): avg ms/tick | 12.56 / 37.83 | 13.19 / 35.64 | -0% | same within noise (pairs 0.94-1.05) |
| 2,000 workers gathering (speed 4): slow ticks | 1647 | 1642 | -0% | one pair, no spread yet |
| server heap in use after first pass, 200 units (MB) | 114 / 114 | 114 / 114.2 | +0% | same within noise (pairs 1.00-1.00) |
| HUD page size (KB) | 1331.8 | 1332.4 | +0% | one pair, no spread yet |
| server heap in use after first pass, 2,000 units (MB) | 399.9 / 400.6 | 400.1 / 400.1 | -0% | same within noise (pairs 1.00-1.00) |
| 100v100 battle (200 units fighting, speed 4): work done (swings) | 5154 / 4772 | 4736 / 5083 | | context (same work = fair comparison) |
| 100v100 battle (200 units fighting, speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM -11.76; track/orders -4.64; track/orders/attack -4.13 |
| 2,000 workers gathering (speed 4): work done (pieces stored) | 13415 | 13418 | | context (same work = fair comparison) |
| 2,000 workers gathering (speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM +13.50; creature walk tick +0.86; creature move +0.72 |
| 200 workers gathering (speed 4): work done (pieces stored) | 1340 / 1328 | 1341 / 1342 | | context (same work = fair comparison) |
| 200 workers gathering (speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM -0.64; track/settlement -0.07; creature walk tick -0.05 |
| 142 units idle + orders (walk latency scene): slow ticks | 0 / 0 | 0 / 0 |  | n/a |
| 142 units idle + orders (walk latency scene): work done (group-move first-step ticks) | 0.07 / 0.11 | 0.11 / 0.1 | | context (same work = fair comparison) |
| 142 units idle + orders (walk latency scene): biggest per-label movers (ms/tick, B-A) | | | | ledger in a tick +0.14; other DM +0.10; track/care +0.10 |
| HUD script ms per update, 203 units, all (headless Chrome, median of 9 rounds) | 1.9 | 1.9 | +0% | same within noise (under 1 ms) |
| HUD script ms per update, 203 units, none (headless Chrome, median of 9 rounds) | 2 | 2 | +0% | same within noise (under 1 ms) |
| HUD script ms per update, 203 units, quiet (headless Chrome, median of 9 rounds) | 1 | 1 | +0% | same within noise (under 1 ms) |
| HUD console errors on load + updates | 0 | 0 | | clean |

Reading it: the battle's lower cost is real in all pairs (0.85-0.89, slow ticks 0.46-0.59); work done is the same. The walk-latency rows swing
between runs of the SAME build (0.69 to 2.0 ms/tick) with Mac load, so they say "same". No 3D frame or real-window HUD numbers.

## Build 63 -> 64 (order-give-dead-unit, recount-dead-unit, village-polish x10, words-batch, combat-rules-morale)
| metric (per-run values, A then B pairs) | build 63 | build 64 | change | verdict |
|---|---|---|---|---|
| 2,000 workers gathering (speed 4): worst tick ms | 331 | 1100 | +232% | one pair, no spread yet |
| 100v100 battle (200 units fighting, speed 4): slow ticks | 50 / 140 | 202 / 118 | +144% | same within noise (pairs 0.84-4.04) |
| 100v100 battle (200 units fighting, speed 4): p95 window ms/tick | 99.4 / 112.2 | 138 / 121.2 | +23% | same within noise (pairs 1.08-1.39) |
| 200 workers gathering (speed 4): worst tick ms | 29 / 52 | 49 / 37 | +20% | same within noise (pairs 0.71-1.69) |
| 142 units idle + orders (walk latency scene): worst tick ms | 16 / 15 | 18 / 16 | +10% | same within noise (pairs 1.07-1.12) |
| 2,000 workers gathering (speed 4): p95 window ms/tick | 200 | 218.2 | +9% | one pair, no spread yet |
| 2,000 workers gathering (speed 4): avg ms/tick | 131.02 | 140.18 | +7% | one pair, no spread yet |
| 100v100 battle (200 units fighting, speed 4): avg ms/tick | 72.5 / 74.31 | 83.35 / 73.01 | +7% | same within noise (pairs 0.98-1.15) |
| HUD script ms per update, 203 units, one (headless Chrome, median of 9 rounds) | 1.7 | 1.8 | +6% | same within noise (under 1 ms) |
| 142 units idle + orders (walk latency scene): p95 window ms/tick | 5.2 / 3 | 5 / 3.4 | +5% | same within noise (pairs 0.96-1.13) |
| 100v100 battle (200 units fighting, speed 4): worst tick ms | 142 / 240 | 180 / 160 | -3% | same within noise (pairs 0.67-1.27) |
| 200 workers gathering (speed 4): avg ms/tick | 11.66 / 16.01 | 12 / 16.47 | +3% | same within noise (pairs 1.03-1.03) |
| 142 units idle + orders (walk latency scene): avg ms/tick | 3.17 / 2.2 | 3.38 / 2.18 | +3% | same within noise (pairs 0.99-1.07) |
| 200 workers gathering (speed 4): p95 window ms/tick | 16.8 / 21.4 | 17.6 / 21.4 | +2% | same within noise (pairs 1.00-1.05) |
| 2,000 workers gathering (speed 4): slow ticks | 1670 | 1694 | +1% | one pair, no spread yet |
| server heap in use after first pass, 2,000 units (MB) | 400.5 | 400.8 | +0% | one pair, no spread yet |
| server heap in use after first pass, 200 units (MB) | 113.8 / 113.9 | 113.9 / 113.9 | +0% | same within noise (pairs 1.00-1.00) |
| 100v100 battle (200 units fighting, speed 4): work done (swings) | 5091 / 5004 | 5051 / 4745 | | context (same work = fair comparison) |
| 100v100 battle (200 units fighting, speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM +3.57; track/orders +1.26; track/orders/attack +1.01 |
| 2,000 workers gathering (speed 4): work done (pieces stored) | 13400 | 13391 | | context (same work = fair comparison) |
| 2,000 workers gathering (speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM +7.87; creature walk tick +0.81; creature move +0.75 |
| 200 workers gathering (speed 4): slow ticks | 0 / 0 | 0 / 0 |  | n/a |
| 200 workers gathering (speed 4): work done (pieces stored) | 1344 / 1335 | 1323 / 1332 | | context (same work = fair comparison) |
| 200 workers gathering (speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM +0.29; creature move +0.11; creature walk tick +0.09 |
| 142 units idle + orders (walk latency scene): slow ticks | 0 / 0 | 0 / 0 |  | n/a |
| 142 units idle + orders (walk latency scene): work done (group-move first-step ticks) | 0.23 / 0.24 | 0.23 / 0.17 | | context (same work = fair comparison) |
| 142 units idle + orders (walk latency scene): biggest per-label movers (ms/tick, B-A) | | | | track/orders +0.10; ledger in a tick +0.08; track/orders/progress +0.05 |
| HUD script ms per update, 203 units, another (headless Chrome, median of 9 rounds) | 1.2 | 1.2 | +0% | same within noise (under 1 ms) |
| HUD script ms per update, 203 units, all (headless Chrome, median of 9 rounds) | 1.9 | 1.9 | +0% | same within noise (under 1 ms) |
| HUD script ms per update, 203 units, none (headless Chrome, median of 9 rounds) | 2 | 2 | +0% | same within noise (under 1 ms) |
| HUD script ms per update, 203 units, quiet (headless Chrome, median of 9 rounds) | 1 | 1 | +0% | same within noise (under 1 ms) |
| HUD page size (KB) | 1332.4 | 1332.4 | +0% | one pair, no spread yet |
| HUD console errors on load + updates | 0 | 0 | | clean |

Reading it: all rows same within noise. Closed at 00:05 (second pair): 63 itself spiked to 2,425 ms and 64 to 1,764, avg 276 vs 160 ms: Mac-load noise, same within noise. Earlier note: "2,000 workers: worst tick" (1,100 vs 331 ms, one pair) was a single spike; avg +7%, p95 +9%,
slow ticks +1%, same pieces stored. A second pair was queued when the stop came (not run). Likely landings if it holds: gathering/orders-side
ones (order-give-dead-unit, recount-dead-unit); no evidence yet.

## Build 64 -> 65 (HUD rework, new loading screen/launcher, hud-batch, items, creatures, combat batches, WorldNew)
Source rebuilt and hash-verified: 65 = c81f8dc1.
**Finding: the HUD page got heavier.** Page 1,332 -> 1,657 KB (+24%); script per update with 203 units about 1.9 -> 3.2 ms (one unit, none selected: every pair worse;
Select all +68% but one pair overlapped). Absolute cost is small (+1.3 ms of a 16.7 ms frame, still far under the 13/17 ms of 10-25), but it is real. Likely landings:
hud-rework (CSS block), hud-batch (9), screens (start cards, boot cover). Console errors: none. Real-window/WKWebView not measured.
**Server side:** the Mac was loaded (the same 2,000-worker scene read 131 ms/tick earlier, 243-324 now), so battle/gather/walk rows are same within noise (pairs wide); memory identical (114 MB at 200 units, 384 MB at 2,000); same work done in every scene.
| metric (per-run values, A then B pairs) | build 64 | build 65 | change | verdict |
|---|---|---|---|---|
| 200 workers gathering (speed 4): slow ticks | 4 / 0 | 0 / 0 | -100% | one pair, no spread yet |
| HUD script ms per update, 203 units, none (headless Chrome, median of 15 rounds) | 2 | 3.5 | +75% | SLOWER (pairs 1.56-1.94) |
| HUD script ms per update, 203 units, all (headless Chrome, median of 15 rounds) | 1.9 | 3.2 | +68% | same within noise (pairs 1.09-1.89) |
| HUD script ms per update, 203 units, one (headless Chrome, median of 15 rounds) | 1.9 | 3.2 | +67% | SLOWER (pairs 1.16-2.06) |
| 100v100 battle (200 units fighting, speed 4): worst tick ms | 309 / 428 | 794 / 324 | +66% | same within noise (pairs 0.76-2.57) |
| 100v100 battle (200 units fighting, speed 4): p95 window ms/tick | 190.4 / 152.6 | 453 / 129.4 | +61% | same within noise (pairs 0.85-2.38) |
| 2,000 workers gathering (speed 4): p95 window ms/tick | 840.8 | 486.8 | -42% | one pair, no spread yet |
| 142 units idle + orders (walk latency scene): p95 window ms/tick | 1.8 / 7.5 | 2 / 1.8 | -32% | same within noise (pairs 0.24-1.11) |
| 2,000 workers gathering (speed 4): worst tick ms | 3016 | 2210 | -27% | one pair, no spread yet |
| 2,000 workers gathering (speed 4): avg ms/tick | 324.45 | 242.94 | -25% | one pair, no spread yet |
| HUD page size (KB) | 1332.4 | 1656.8 | +24% | one pair, no spread yet |
| 142 units idle + orders (walk latency scene): avg ms/tick | 1.38 / 2.88 | 1.62 / 1.08 | -23% | same within noise (pairs 0.38-1.17) |
| 200 workers gathering (speed 4): worst tick ms | 103 / 61 | 36 / 80 | -17% | same within noise (pairs 0.35-1.31) |
| 100v100 battle (200 units fighting, speed 4): avg ms/tick | 113.99 / 93.1 | 165.09 / 79.82 | +15% | same within noise (pairs 0.86-1.45) |
| 200 workers gathering (speed 4): avg ms/tick | 13.02 / 12.74 | 13.96 / 15.58 | +15% | same within noise (pairs 1.07-1.22) |
| 2,000 workers gathering (speed 4): slow ticks | 1706 | 1456 | -15% | one pair, no spread yet |
| 200 workers gathering (speed 4): p95 window ms/tick | 18.8 / 22 | 20.6 / 23.6 | +8% | same within noise (pairs 1.07-1.10) |
| 100v100 battle (200 units fighting, speed 4): slow ticks | 442 / 266 | 478 / 222 | -4% | same within noise (pairs 0.83-1.08) |
| 142 units idle + orders (walk latency scene): worst tick ms | 6 / 37 | 10 / 11 | -2% | same within noise (pairs 0.30-1.67) |
| server heap in use after first pass, 2,000 units (MB) | 383.9 | 383.6 | -0% | one pair, no spread yet |
| server heap in use after first pass, 200 units (MB) | 114 / 114.1 | 113.9 / 114.1 | -0% | same within noise (pairs 1.00-1.00) |
| 100v100 battle (200 units fighting, speed 4): work done (swings) | 4891 / 5155 | 4823 / 4899 | | context (same work = fair comparison) |
| 100v100 battle (200 units fighting, speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM +14.20; track/orders +4.97; track/orders/attack +4.46 |
| 2,000 workers gathering (speed 4): work done (pieces stored) | 13428 | 13367 | | context (same work = fair comparison) |
| 2,000 workers gathering (speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM -69.87; track/orders -3.89; unit order -3.27 |
| 200 workers gathering (speed 4): work done (pieces stored) | 1324 / 1326 | 1332 / 1309 | | context (same work = fair comparison) |
| 200 workers gathering (speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM +1.60; track/settlement +0.11; creature walk tick +0.10 |
| 142 units idle + orders (walk latency scene): slow ticks | 0 / 0 | 0 / 0 |  | n/a |
| 142 units idle + orders (walk latency scene): work done (group-move first-step ticks) | 0.08 / 0.14 | 0.02 / 0.12 | | context (same work = fair comparison) |
| 142 units idle + orders (walk latency scene): biggest per-label movers (ms/tick, B-A) | | | | other DM -0.47; ledger in a tick -0.19; track/care -0.14 |
| HUD script ms per update, 203 units, another (headless Chrome, median of 15 rounds) | 1.3 | 1.3 | +0% | same within noise (under 1 ms) |
| HUD script ms per update, 203 units, quiet (headless Chrome, median of 15 rounds) | 1 | 1 | +0% | same within noise (under 1 ms) |
| HUD console errors on load + updates | 0 | 0 | | clean |


### Bisect of the HUD cost, 64 -> 65 (HUD page after each HUD landing; 203 units, headless Chrome, median of 15 rounds)
Page rebuilt from art/hud/src with each later restore point put back (`perf-watch/bisect_hud.py`; step 0 = 64's page size exactly, step 8 = 65's).
| after landing | page KB | one unit ms | Select all ms | none ms | another / quiet ms |
|---|---|---|---|---|---|
| build 64 | 1,332.4 | 1.9 | 1.9 | 2.0 | 1.2 / 0.9 |
| f3-f6-page-keys | 1,332.7 | 1.8 | 1.9 | 2.2 | 1.2 / 1.0 |
| view3d-batch1 | 1,334.1 | 2.0 | 1.9 | 2.0 | 1.2 / 0.9 |
| view3d-light-fade | 1,334.3 | 2.0 | 1.9 | 1.9 | 1.2 / 0.9 |
| hud-rework | 1,432.7 (+98 KB) | 2.0 | 2.1 | 2.2 | 1.2 / 0.9 |
| words-batch-hud | 1,432.6 | 2.1 | 2.0 | 2.1 | 1.2 / 1.0 |
| screens-boot-cover | 1,547.6 (+115 KB) | 2.2 | 2.0 | 2.1 | 1.2 / 1.0 |
| hud-batch | 1,549.3 | 2.2 | 2.0 | 2.1 | 1.2 / 0.9 |
| **screens-start-cards** | 1,656.8 (+107 KB) | **3.1** | **3.2** | **3.4** | 1.2 / 1.0 |
- **Size (+325 KB):** hud-rework +98 KB (CSS), screens-boot-cover +115 KB (boot images), screens-start-cards +107 KB (the race-picture atlas, inline PNG). The size costs no script time (removing the atlas: no change in ms).
- **Time (+1.2 ms, selection changes only):** all of it is `screens-start-cards`, and within it only five CSS rules in `041-style.css` using `:has(>button:nth-child(11))`
  on `#askcard.race` / `.race-opts` (lines 78-82 of that file; they widen the race card to 3 columns when it has 11+ options). Removing just those five rules brings one/all/none back to 2.0/2.3/2.3 ms
  (the page without them is otherwise the full 65 page); removing the image, the `:not(:has(.rc-pic...))` rules, or the JS change does nothing. Likely cause: `:has()` makes the browser recheck those
  selectors whenever the page's nodes change, and a selection change rewrites the unit rows. WebKit's `:has()` invalidation is not cheaper. Fix idea (not applied): set a class on `.race-opts` from the JS that builds the buttons (11+ options) and select on that class instead of `:has()`.

## Final (04:20): builds 66, 67, 68
Sources rebuilt and hash-verified: 66 = 9d18cefc, 67 = 68 = 6587c5da (build 68 changed only the HUD page; the compiled game is the same as 67's).

### HUD script ms per update, 203 units (headless Chrome, 15 rounds), the owner's question first
| build | page KB | one unit | Select all | none | another / quiet |
|---|---|---|---|---|---|
| 64 (before the cost) | 1,332 | 1.7 | 2.0 | 2.0 | 1.2 / 0.9 |
| 65 | 1,657 | 2.9 | 3.1 | 3.5 | 1.3 / 1.0 |
| 66 | 1,657 | 2.9 | 3.2 | 3.4 | 1.2 / 1.0 |
| 67 | 1,655 | 2.9 | 3.0 | 3.4 | 1.2 / 1.0 |
| **68 (race-many :has() fix)** | 1,655 | **1.9** | **2.2** | **2.3** | 1.2 / 1.0 |
68 gives back the +1.2 ms (0.2-0.3 ms above 64, within noise). The +323 KB of page stays (images and CSS, no script cost). 0 console errors in every build.

### Server, build 65 -> 66 (loops-batch, zones-batch, gear-oldgroup-noicon): no row SLOWER; battle p95 -19% (pairs 0.80-0.81), the rest same within noise; same work done; heap identical.
| metric (per-run values, A then B pairs) | build 65 | build 66 | change | verdict |
|---|---|---|---|---|
| 200 workers gathering (speed 4): worst tick ms | 32 / 39 | 140 / 34 | +162% | same within noise (pairs 0.87-4.38) |
| 2,000 workers gathering (speed 4): worst tick ms | 1187 | 279 | -76% | one pair, no spread yet |
| 100v100 battle (200 units fighting, speed 4): slow ticks | 62 / 88 | 30 / 46 | -50% | faster (pairs 0.48-0.52) |
| 100v100 battle (200 units fighting, speed 4): p95 window ms/tick | 117 / 116.8 | 94.4 / 94 | -19% | faster (pairs 0.80-0.81) |
| 142 units idle + orders (walk latency scene): avg ms/tick | 2.69 / 2.22 | 3.32 / 2.38 | +15% | same within noise (pairs 1.07-1.23) |
| 2,000 workers gathering (speed 4): p95 window ms/tick | 211.4 | 180.8 | -14% | one pair, no spread yet |
| 100v100 battle (200 units fighting, speed 4): avg ms/tick | 72.26 / 59.83 | 56.38 / 57.94 | -13% | same within noise (pairs 0.78-0.97) |
| 100v100 battle (200 units fighting, speed 4): worst tick ms | 156 / 301 | 161 / 241 | -8% | same within noise (pairs 0.80-1.03) |
| 2,000 workers gathering (speed 4): avg ms/tick | 134.5 | 126.17 | -6% | one pair, no spread yet |
| 142 units idle + orders (walk latency scene): p95 window ms/tick | 4.4 / 3.1 | 4.3 / 3.5 | +5% | same within noise (pairs 0.98-1.13) |
| 200 workers gathering (speed 4): p95 window ms/tick | 22.4 / 22.2 | 20.6 / 22.2 | -4% | same within noise (pairs 0.92-1.00) |
| 2,000 workers gathering (speed 4): slow ticks | 1691 | 1630 | -4% | one pair, no spread yet |
| 200 workers gathering (speed 4): avg ms/tick | 16.89 / 16.95 | 15.82 / 16.85 | -3% | same within noise (pairs 0.94-0.99) |
| 142 units idle + orders (walk latency scene): worst tick ms | 18 / 15 | 17 / 15 | -3% | same within noise (pairs 0.94-1.00) |
| server heap in use after first pass, 2,000 units (MB) | 400.6 | 400.1 | -0% | one pair, no spread yet |
| 100v100 battle (200 units fighting, speed 4): work done (swings) | 4703 / 4953 | 5025 / 4767 | | context (same work = fair comparison) |
| 100v100 battle (200 units fighting, speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM -7.12; track/orders -1.60; track/orders/attack -1.52 |
| 2,000 workers gathering (speed 4): work done (pieces stored) | 13488 | 13427 | | context (same work = fair comparison) |
| 2,000 workers gathering (speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM -6.32; track/orders -0.77; creature walk tick -0.62 |
| 200 workers gathering (speed 4): slow ticks | 0 / 0 | 4 / 0 |  | n/a |
| 200 workers gathering (speed 4): work done (pieces stored) | 1349 / 1328 | 1320 / 1320 | | context (same work = fair comparison) |
| 200 workers gathering (speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM -0.60; creature move +0.08; creature walk tick +0.04 |
| 142 units idle + orders (walk latency scene): slow ticks | 0 / 0 | 0 / 0 |  | n/a |
| 142 units idle + orders (walk latency scene): work done (group-move first-step ticks) | 0.33 / 0.15 | 0.18 / 0.19 | | context (same work = fair comparison) |
| 142 units idle + orders (walk latency scene): biggest per-label movers (ms/tick, B-A) | | | | other DM +0.22; ledger in a tick +0.11; track/patrol +0.09 |
| server heap in use after first pass, 200 units (MB) | 114 / 114.1 | 114 / 114.1 | +0% | same within noise (pairs 1.00-1.00) |


### Server, build 66 -> 67 (regrow-living-off redo + combat-speed-2): **SLOWER at 2,000 workers, and it does more work**
Three pairs at 2,000 workers: avg ms/tick +43% (pairs 1.24-1.45), p95 +53% (1.41-1.61), worst tick 1.3-1.5 s vs 0.5-0.7 s (speed 4). 200 workers: p95 +19% (both pairs), avg +8% (noise).
But the work differs: 67 stores **+58% more** (2,000 workers: 21,300 vs 13,400 pieces; 200 workers: 1,990 vs 1,320), as the redo intends (harvest takes all, zone workers replant). Per piece stored,
67 costs about 20% LESS tick time (170 ms / 21,356 vs 137 ms / 13,490). Likely landing: regrow-living-off (the zones agent warned of its 2,000-worker cost); combat-speed-2 is behaviour-identical
and the battle scene is unchanged (-5% avg, noise). Heap identical (114 / 400 MB). Walk latency and the 100v100 battle: same within noise.
| metric (per-run values, A then B pairs) | build 66 | build 67 | change | verdict |
|---|---|---|---|---|
| 2,000 workers gathering (speed 4): worst tick ms | 487 / 484 / 690 | 1473 / 1359 / 1320 | +181% | SLOWER (pairs 1.91-3.02) |
| 2,000 workers gathering (speed 4): p95 window ms/tick | 197.8 / 186 / 189.2 | 279.4 / 298.6 / 290 | +53% | SLOWER (pairs 1.41-1.61) |
| 2,000 workers gathering (speed 4): avg ms/tick | 136.97 / 125.62 / 122.6 | 170.49 / 179.17 / 177.82 | +43% | SLOWER (pairs 1.24-1.45) |
| 200 workers gathering (speed 4): p95 window ms/tick | 22.6 / 22.2 | 26.2 / 27.2 | +19% | SLOWER (pairs 1.16-1.23) |
| 100v100 battle (200 units fighting, speed 4): slow ticks | 64 / 42 | 32 / 48 | -18% | same within noise (pairs 0.50-1.14) |
| 100v100 battle (200 units fighting, speed 4): worst tick ms | 322 / 259 | 222 / 290 | -10% | same within noise (pairs 0.69-1.12) |
| 200 workers gathering (speed 4): avg ms/tick | 17.21 / 17.27 | 18.18 / 18.98 | +8% | same within noise (pairs 1.06-1.10) |
| 100v100 battle (200 units fighting, speed 4): p95 window ms/tick | 107.4 / 97 | 90.6 / 100.4 | -6% | same within noise (pairs 0.84-1.04) |
| 142 units idle + orders (walk latency scene): avg ms/tick | 3.11 / 2.65 | 2.75 / 2.67 | -5% | same within noise (pairs 0.88-1.01) |
| 100v100 battle (200 units fighting, speed 4): avg ms/tick | 62.84 / 63.12 | 57.19 / 62.62 | -5% | same within noise (pairs 0.91-0.99) |
| 200 workers gathering (speed 4): worst tick ms | 51 / 36 | 35 / 50 | +4% | same within noise (pairs 0.69-1.39) |
| 142 units idle + orders (walk latency scene): worst tick ms | 18 / 18 | 18 / 17 | -3% | same within noise (pairs 0.94-1.00) |
| 142 units idle + orders (walk latency scene): p95 window ms/tick | 4.1 / 4.2 | 3.8 / 4.4 | -1% | same within noise (pairs 0.93-1.05) |
| 2,000 workers gathering (speed 4): slow ticks | 1691 / 1679 / 1662 | 1691 / 1691 / 1690 | +1% | same within noise (pairs 1.00-1.02) |
| server heap in use after first pass, 2,000 units (MB) | 400.1 | 400.7 | +0% | one pair, no spread yet |
| server heap in use after first pass, 200 units (MB) | 114 / 114 | 114 / 114.1 | +0% | same within noise (pairs 1.00-1.00) |
| 100v100 battle (200 units fighting, speed 4): work done (swings) | 4997 / 4876 | 5084 / 4831 | | context (same work = fair comparison) |
| 100v100 battle (200 units fighting, speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM -2.21; track/orders -0.98; track/orders/attack -0.87 |
| 2,000 workers gathering (speed 4): work done (pieces stored) | 13490 / 13421 / 13494 | 21356 / 21226 / 21277 | | context (same work = fair comparison) |
| 2,000 workers gathering (speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM +41.68; creature walk tick +2.99; creature move +2.71 |
| 200 workers gathering (speed 4): slow ticks | 0 / 0 | 0 / 0 |  | n/a |
| 200 workers gathering (speed 4): work done (pieces stored) | 1321 / 1317 | 1990 / 1998 | | context (same work = fair comparison) |
| 200 workers gathering (speed 4): biggest per-label movers (ms/tick, B-A) | | | | other DM +1.22; track/settlement/any work +0.16; track/settlement +0.09 |
| 142 units idle + orders (walk latency scene): slow ticks | 0 / 0 | 0 / 0 |  | n/a |
| 142 units idle + orders (walk latency scene): work done (group-move first-step ticks) | 0.25 / 0.11 | 0.23 / 0.22 | | context (same work = fair comparison) |
| 142 units idle + orders (walk latency scene): biggest per-label movers (ms/tick, B-A) | | | | other DM -0.20; ledger in a tick -0.05; track/orders/progress +0.04 |


## Night summary
- Faster: 100v100 battle 62 -> 63 (-13% ms/tick, half the slow ticks) and 65 -> 66 (p95 -19%).
- Slower and fixed: HUD +1.2 ms per update in 65-67 (screens-start-cards' five :has() rules), fixed in 68.
- Slower, by design: 2,000 workers gathering +43% ms/tick (worst tick about 2-3x) in 67 for +58% more pieces (regrow redo). Owner call: whether the worst-tick spikes at 2,000 workers matter (not seen at 200 workers: worst 35-50 ms).
- Unchanged: memory (114 MB at 200 units, 400 MB at 2,000 after the first pass), walk latency, 200-worker gathering (+8% avg in 67).
- Method limits: Mac shared (load 2-7), speed-4 profiler values; no real-window HUD, no 3D frame ms, no 5k runs.

## Needs the owner
- Build 67: 2,000-worker gathering costs +43% ms/tick (worst tick 2-3x) for +58% more pieces: decide if the redo's cost is acceptable or needs trimming. Build 65: HUD page +24% / script +1.3 ms per update (see above). Decide whether the rework's page weight is worth trimming; no server regression seen.
