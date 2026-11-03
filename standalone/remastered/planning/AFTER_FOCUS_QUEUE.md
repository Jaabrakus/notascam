# Tests dropped for the focus list (2026-10-24, ~22:45)

The user: "Let make a list and run less tests so we can focus and get more done". Then: "What was drop so if we
finish early we can run those test after the 16".

**Rule:** when a session's focus item is done (landed or reported) and 3 or fewer runs are going, it queues the next
item from its own list below, one at a time, in this order. Mark each `[x]` here when it has run and post the result
on the board.

## server-cost
- [x] Game checks after the slices + shedding landing (skills ×3, savers, explore, shed, hud-craft's tier check).
  Folded into walk v2e's landing run if they can share it; otherwise they go first.
  Done 22:53 on v2e's copy: all pass (skills: the 3 known stale failures, same as game/); tiers at level 3 give health and blows 8/8; 0 exceptions.
- [x] Track passes suite + 30k track cadence (care/bag/blueprints safe points, carry list).
  Done 01:16 on game/ as of 00:5x: care, doctor, food, stumps, bag, combat, blueprints, construction, savers pass; subdue
  15/16 = plain (case 8 is Fog.dm's stale-cells first-tick drop, world-look's). 30k standing: the track's worst tick
  1,175 -> 197 ms, its share 43.4 -> 33.9 ms a tick, DM 156.7 -> 149.4. Ready; landing asked.
- [x] rm_foe_near's strengthened exactness test, with "yes" cases (foes within 6, at exactly 6, walls, allies, wild,
  invisible/flying), then its war-phase run.
  Exactness: formations ran sight_check2 on v7f (01:1x, pass). War run 02:1x on v7f: attack-move first steps mean
  0.12 -> 0, 5k war 123.5 -> 106.3 ms a tick; standing and moving equal. Attack.dm line ready; landing asked.
- [x] Measured-step budget comparison (the first-step budget charging the real step instead of ×2).
  Done 02:4x: dropped. Measured charges ~0.33 ms a unit vs ×2's ~0.28, so a group of 30 starts 21/9/0/0 vs 29/1/0/0.
  ×2 stays. The click's own cost is mostly formations' slots (18-86 ms); details on the board.
- [x] RmWatch completeness fuzz and per-write cost gates. These may fold into formations' combined v7 gate run.
  Ticked 02:2x (coordinator): fuzz 8/8, cost gated by formations. The fallback checks wait until the game calls
  rm_watch, which waits on the leaner Written below (a later engine build, not on tonight's list).
  Fuzz passed on v7c at 22:37 (8/8, 4,000 random writes, 0 differ). The 5k cost runs are dropped: formations runs v7's cost
  gate once (5k stress + per-write microbenchmark, v6e vs v7e). Left here: the RM_WATCH=0 / no-engine fallback checks.
  formations' v7e gate (00:2x): nothing watched, no measurable cost; with 3 names watched, +15–19 ns on every DM var write,
  misses included. The game doesn't call rm_watch until that's near 0. Fix staged for v7f: one `_lengths` load (no
  `Active`), statics in a nested holder (no class-init check), then a C# microbench of Written plus
  tests/write_cost_watch_check.dm.
- [x] 30k bare-world / no-Bed experiments (where the 335 ms of "other DM" goes).
  Done 02:5x on game/ with v2e: other DM now 58 ms a tick; Bed costs ~43 ms a tick in all (169.5 vs 126.4); bare objects
  ~0 (0.6% cpu). Follow-up being checked: the clock books a non-tired unit's Bed run itself (exact, no call).

## formations
- [x] Candidate 4 checks and sweeps: the group's pass list shared per tick (633 µs → ~0 a call, half of a first
  order tick).
  Done 01:2x on game/ as of 00:2x: pass list 282 -> 4 us a call, order tick 77 -> 36 us; 200-block sweep 0/1/2/3+ 48/286/238/428 -> 220/261/187/332; walk latency equal or better (2 samples); clip, formation pass; obey = game/ (one asleep-attack flake in 1 of 2 runs). Landing asked.
- [~] 30k move work: one shared order per group, then spreading the hand-out over ticks.
  02:5x: the giving spread over ticks LANDED (candidate 5: 5k click 208 -> 122-164 ms, 30k 788 -> 350-439 ms, <= 200 identical). A shared order per group isn't needed for it (the order objects are 0.5 us of ~14). Left: the planning loops (~330 ms at 30k) into the engine (v8).

## world-look
- [x] Entry reuse by rm_ver: shadow compare, delta check, bench (unchanged things cost nothing in a scene build). Done 23:3x, results on the board.
- [x] The last 200-unit real-window profile: the 3D budget on v6e. Done 23:5x, results on the board.

## jobs
- [x] Lodge reruns: lodge5c-Orc, lodge-doors Elf/Orc (doors with no workaround, after doors (a) is in).
  Done 02:0x on the doors landing's exact files: no workaround (own doors open) Elf 2.7 min, Orc 3.2 min, banner 15 s
  after; Orc live on v6e (door opened by hand after) 3.2 min + banner 15 s.
- [x] Old-code 200-worker profile. (jobs 00:0x: settlement "any work" 8.7 ms/s at 66 µs a call, vs 98 ms/s at 408 µs with the gather fixes; posted on the board.)
- [x] Live check_stumps / check_doctor comparison; two lodge-v5 check_doctor reruns; the lodge-v5 check chain (check_jobs
  onward).
  Covered: the Jobs.dm landing suite (00:2x, game/ + the lodge code) ran doctor, stumps, jobs, buildings, blueprints,
  build_handoff, settlement, station, ... all PASS; server-cost's track suite (01:16, game/ with Jobs.dm in) ran doctor,
  stumps, food, care again: PASS. No separate runs needed.
- [x] Scoreboards: a7 20S and 2000S, b2 2000S, a4 20.
  Done 02:2x on the live game/ (gather + lodge + doors in; a7/b2/a4 were candidates of what landed). Stored per
  worker-hour, 5 min, arena speed 4: 20 one stockpile wood 214 (91 wood / 232 stone stored, as at landing); 20 with a
  store by each zone wood 234 stone 537 (107 / 608 stored); 2,000 with stores wood 58.8 stone 367 (2,446 / 10,466
  stored; 6,207 trips of 7.1 s; one stockpile was 1.7 / 3.5). Left at 2,000: 635 pieces lying at the end (628 over
  2 min, mostly in stone zones) and 23 of 170 carriers "No way through yet": the next gather item.

## Held by design (not just dropped)
- map-memory: the full-world run. It waits for 6 GB of free memory, which this Mac won't have while tests run.
- rts-feel: wild-AI fixes after its one profile run and report.
- 3D stage 2: stays off until its v6e bench (world-look, after the FORM|zoom fix).

## capture-rope (found by jobs 2026-10-25 02:0x, not started)
- [ ] Captives.dm RmCapPostWalk: a deadlock that a change in same-tick wake order trips (capture_test tie-to-tree). Make it
  independent of wake order. Details on the board, "jobs 02:0x".

## web relay (found by server-cost 2026-10-25 ~10:00, not urgent, for the web-relay owner)
- [ ] In the chat shadow run's browser client (tools/web_host.py, web-relay/), the page's own test reports never
  reached DM: a send('chatshadow', ~3-6 KB JSON) every 300 ms. On the Mac client the same reports arrived. The
  relay passes on every `nav` (RelayWebViewManager.cs ~160), and DM's client/Topic gate (HUD.dm ~1089) didn't refuse
  them: 0 CHATSHADOW lines, 0 "Selection changed" notices. So the cause is still open, perhaps the long byond:// URL in
  Page.Navigate. Ordinary clicks work in browser play. Repro: reports/server-cost/staged/chat/web_shadow.py with
  tests/chat_shadow_log.dm. Details in reports/server-cost/hidden-2d-audit.md, "(a2) SHADOW PROOF".

## Hitch 1: the tick after a 2,000-unit click (server-cost found it 10-25, formations diagnosed it; parked, formations on hold)
- [ ] 0.7-1 s of DM in the tick after a 2,000-unit "keep" move whose target lies inside the block's own footprint. Seen in
  tests/tick_ledger_check.dm's eastward rounds; the ledger v2/v3 charges the plan and shows it there.
  - Formations' lead: the planner's stand step (Formations.dm "Each unit must be able to stand on its own tile") runs
    with rm_path_pass null, so the group's own standing units count as blocking. Every slot over one of them is picked
    again: `taken` is rebuilt and all of `reach` scanned, up to 841 x ~1,700.
  - Fix idea: rm_path_pass = pass for the stand step, as for the flood before it, then reset. That changes small groups'
    slots (today a slot on a group-mate's tile is moved), so it needs the formation and obey gates and the coordinator's OK.
  - To confirm first: check_arena.py --test tests/plan_profile_check.dm --entry PpRun --size 400x400 with PP_MODE=ledger
    PP_REPS=3; "8 stand" should be most of the eastward plan.
