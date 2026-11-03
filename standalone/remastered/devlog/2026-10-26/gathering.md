# Gathering, economy and Plan mode (gathering session, 2026-10-26)

Picked up the jobs (chat 30) and ramps-gather (chats 32-33) workstreams. Read-only so far: nothing changed in game/.

## What's in the game (build 56 + the 09:56 rebuild)
- The gathering batch is in game/ byte for byte as gated (Jobs.dm 0defdac4, Zones.dm 2a42b63c, Carts.dm 4c31e849,
  Fishing.dm c800daba): whole-area stockpiles, a yard by each wood and stone zone, haulers to the main stockpile,
  + Fish zones, farmers waiting at their farm. Landed 10-25 20:3x, in the app since build 39.
- J2 parts 1 + 2 (zones wake their workers): 2,000 workers 285 -> 48-80 ms a tick (build 27).
- Tended trees held on every blow (memload, 10-26 09:5x): obey 32/32, the old "known 6" are gone.
- Plan mode: dig, build block by block, workers cut their own way up; yellow worked-block highlight. Real window plan4
  19/19 (10-25 15:53). Make and Serve tabs off (`rm_chain_tabs = 0`).

## Parked / not started
- Store clipping v4, workshops taking from any store (reports/jobs/parked/).
- J2 part 3: spread the rest of the settlement pass (163 ms/s, worst call 403 ms at 2,000 workers). The owner, 10-25
  15:41: "we need to cut this even more".
- Farmers standing 3 tiles short of a busy stockpile tile (reports/jobs/stockpile-design.md).
- Plan mode: naming rooms; owned plans and charges for rulers (designed only).

## J2 part 3 (the owner: "Yes: re-measure the settlement pass at 2,000 workers on today's game, then build J2 part 3")
- Harness: reports/gathering/tools/make_set_test.py (gather_score + aw_prof + settlement timers inside a stand-in track run).
- Today's game, 2,000 workers, 5 min, two runs: 165 ms/s, 92 ms a pass, worst tick 912 / 298 ms, 95% of ticks under
  123-127 ms; wood 2,454-2,472, stone 11,014-11,089. The 912 ms tick was one villager's route search (unit order/approach
  796 ms), which no spreading between units can split.
- Candidate 1 (safe points between units, 5 ms share a tick): worst tick 54 ms, 95% under 14 ms, BUT wood 873 and stone
  3,453: a pass now spans ~17 ticks, so each villager steps 4x less often. Fails the gather gate. Next: the ledger's 30 ms
  line only, and 15 ms; then cut the free villagers' step-off check (aw/clear store 51 ms/s).

## Proposals waiting for the owner
- Tending follows Lethal / Non-lethal: reports/gathering/staged/tend-by-lethal/PROPOSAL.md.
- Plan mode takes over building (blocks, then designate): reports/gathering/staged/plan-build-takeover/DESIGN.md.

## J2 part 3: share sizes (2,000 workers, 5 min, interleaved with today's game)
| | Today (3 runs) | 5 ms share | 15 ms | ledger's 30 ms line |
|---|---|---|---|---|
| Worst tick | 298-912 ms | 54-63 | 484 | 589 |
| 95% of ticks under | 115-127 ms | 14-15 | 25 | 35 |
| Wood / stone | 2,460 / 11,026 | 832 / 3,239 | 2,152 / 8,451 | 2,401 / 9,884 |
- Spreading alone trades gathering for smoothness; the worst ticks are single route searches. Next: cut the work
  (idle villagers' step-off check 51 ms/s; slow searches to unreachable spots), then spread what's left.

## Build by shape (the owner: "Option B: blocks, and the game recognises walls, towers and gateways by their shape, no designating. Make a test arena first.")
- reports/gathering/staged/build-by-shape/: make_arena.py (from tools/plan_mode/arena.html) -> arena.html; check_arena.py
  (headless Chrome) 7/7: walled yard (5 wall sections with battlements, 4 hollow round towers, 3-wide gateway, carved
  stairs, guard on the walk) and a timber house (no battlements, a doorway). Stills in shots/.
- Found on the way: a solid 3x3 tower's middle column can't be reached once its sides are up, so towers are 3x3 rings
  (a solid one still counts); a gap between two buildings isn't a gateway (the wall must go on in line on both sides).

## Routed for the owner
- Unit and its frame drawn apart (screenshot) -> world-look-sky; fight hitches (live server.log: 3x "Cannot keep up!",
  worst 10 s window 85 of 100 ticks, alloc 47 MB/s) -> server-engine for a profiled big-fight click.

## J2 part 3 staged (2,000 workers, 5 min, interleaved with today's game)
| | Today | Marks | Marks + spread 30 ms (staged) | Marks + spread 15 ms |
|---|---|---|---|---|
| Settlement pass | 145 ms/s | 127 | 104 | 83 |
| Ticks: 95% / 99% under | 108 / 119 ms | 96 / 138 | 31 / 47 | 20 / 34 |
| Wood / stone | 2,467 / 10,981 | 2,471 / 10,979 | 2,459 / 11,066 | 2,420 / 10,401 |
- Staged: reports/gathering/staged/store-area-marks/ and settle-spread/ (land scripts, READMEs). Tests: store_area 7/7,
  settle_spread_test 8/8.

## The Gather bar, server side (the owner's picks via the coordinator; names agreed with hud-controls)
- tend-bar/: `seltend on|off`, model `selTend`. tend_bar_test 9/9 (Tend off fells a grown tree while the realm tends).
- gather-zone/: a "gather" row (trees + rock + pieces, a yard for anything), `gatherzone x0|y0|x1|y1|z|what|queued|tend`,
  the zone keeps the bar's Tend (the owner: "Yes: a Gather zone takes the bar's Tend when I drag it ..."), `jobrow id|tend`.
  gather_zone_test 17/17.
- Set blocks: plan only (plan-build-takeover/SET_BLOCKS_PLAN.md): the per-block material is a save addition, owner's OK.
- tend-by-lethal parked (superseded by the Tend button).

## The bars batch landed (14:56, build 58)
- The Gather bar's Auto unload, the Gather zone and Stockpile here, with hud-controls' bars and B key. The joint gates
  on one copy passed: obey 32/32 (x3, and x2 on game/), jobs 40/40, gather 24/24, lodges 4.0-4.5 min, the bar's own
  Gather zone builds a lodge in 4.1 min. Table: reports/gathering/staged/GATES.md.

## The Tend redo: zones regrow their trees (the owner: "no we can still keep the zone regrowing plans")
- First try planted nothing in 25 minutes: the stump was marked on the feller's own tile, not the tree's. Fixed.
- Now 12 felled trees become 12 saplings within the first minute, and the workers tend them faster than they grow
  alone.
- A regrowing wood keeps one worker a stump and one for every 10 saplings; the rest go back to the board. Keeping one a
  sapling soaked up the stone row's freed workers in jobs_test.
- yield_test and jobs_test checked the old Tend rules; staged redo versions (patch_regrow_tests.py) check the new ones.

## J2 part 3 landed (15:54, build 59)
- Store-area marks and the settlement spread. At 2,000 workers the settlement pass goes from 106 to 79 ms/s, and the
  slowest 1 in 100 ticks from 95 to 40 ms; gathering is unchanged.

## Living resources (the owner: "regrowing is the same thing is living resources its just living requires nuturing")
- Three regrow bugs found and fixed:
  - the stump was marked on the feller's own tile, not the tree's;
  - a unit walking into a sapling knocked it down, and that tile was lost;
  - tree seeds on a stump kept anyone from planting there.
- Regrowing at first doubled the server cost at 2,000 workers (80 -> 159 ms/s). Felling whole alone is 94, so the cost
  was the replanting. Now a worker keeps the stump it picked, and a zone wants one worker per 3 stumps.
- Next, from the owner (not built):
  - tile fertility, with aqueducts to raise it;
  - runic power to regrow ore veins.
