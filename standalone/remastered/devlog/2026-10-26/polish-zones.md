# Polish night: gather zones (polish-zones)

> **State (10-27 02:0x): done.** Landed zones-batch (01:12, in build 66) and regrow-living-off (01:57, alone, for
> build 67). Nothing of mine queued or running.

The owner, 19:58: "in the polish we need make the gather zones work better idk how but you will be able to make it
happen", and later "build it in a way we can easily make systems where we dont have to micro manage each unit to gather
we can do zones tell them where to place it and etc like a rts right?". I dragged zones in the test arena the way a
player does (trees, a rock outcrop, a mountain face, a mixed Gather zone, two zones side by side, one far from the
stockpile, one half walled in, a fishing zone) with 1, 5 and 20 workers each, timed what the workers did for 8 minutes
of game time at speed 4, and compared what each zone's job-board row said with what was true. Then I fixed what made
zones need a player's help.

## What made zones feel bad (ranked, today's game)

1. **Wood zones stop after one log a tree.** With Tend on (today's default) every tree is cut to half, then rests ~15
   minutes. A 64-tree wood with 5 workers: 64 logs in 2.5 minutes, then "Resting" and the workers leave (66% of their
   time off the zone). Fixed by your Tend redo, landed tonight as regrow-living-off (below).
2. **Two zones side by side jam each other.** The stone zone's yard was painted inside the wood zone; wood workers lifted
   the stored stone as "pieces lying in the zone" and put it back a tile away, for good: 1,230 trips of under a tile in
   8 minutes, the wood row stuck on "Collected Stone" with 11 trees ready.
3. **Trees with no way to them hold the whole zone.** Half-walled wood: the workers walked at the walled-in trees and
   stood "No way through yet; trying again" forever while the row said "5 chopping". With 20 workers the zone made
   nothing at all in 8 minutes.
4. **Stone piles up round rock zones.** Miners lift every find; ore, gems and bones the drop-off won't take fill their
   bags, and then every stone is left on the ground: 180 lying round a 15 x 8 outcrop at 5 minutes, 30% of worker time
   spent lifting them again. The loops chat already had the fix (miners leave what no store takes); I measured it on
   my scenes: 93 left lying -> 0. Landed in their loops-batch (01:04).
5. **A stone zone over a mountain digs a crawlspace and stops**: only each column's floor block, then "Nothing left to
   work" at 4 minutes with 556 of the zone's 676 blocks standing. (Needs the owner: how much it should take.)
6. **Rows that didn't say what was happening**: a Gather zone's row had no "to work" count and called its miners
   "chopping"; a fishing zone's row read +0/min while it fed the village.

Not a problem (measured): workers crowding one tile (0 samples of two resting on one tile in every scene), nearest-first
order, the 3D zone outline after mining (it is redrawn whenever the ground changes), time to first harvest (13-35 s).

## Done

Landed: **zones-batch** 01:12 (the six fixes below; in build 66; restore point
`restore-points/before-polish-zones-batch-20261027-003437`) and **regrow-living-off** 01:57 (your Tend redo; alone, for
build 67; restore point `restore-points/before-polish-regrow-living-off-20261027-015107`). Both gates passed: compile,
jscheck, hudjoin, combat 32/32, obey 32/32, buildings 26/26, food 7/7.


- **Goods on a store are never "lying in the zone."** Two zones side by side, 5 workers a zone: 1,230 junk trips -> 209
  real ones; workers stuck 12 -> 0; time on nothing 36% -> 3%.
- **A zone's yard never lands inside a neighbouring zone**: the free edge nearest the stockpile instead (about 1.5 tiles
  more a carry for that zone; keeps stone off the neighbour's trees and, with the regrow redo, off its stumps).
- **Trees and rock with no way to them are left out and counted.** A worker that finds no way gives up in 15 s (as Plan
  mode's do); the zone then works out which targets have no way in, leaves them out, and its row says "Nothing in reach:
  32 trees with no way to them from outside the zone" with a "32 out of reach" tag. Half-walled wood, 20 workers: 0 ->
  32 logs, worker-seconds stuck 8,539 -> 0. Zones with nothing walled in pay nothing for this.
- **The Gather zone's row**: "12 trees and rock faces to work", "+N/min", "3 gathering".
- **A fishing zone's row counts its catch**: +0/min -> about +22/min, matching the food coming in.
- **A mountain zone that has worked all it reaches says so**: "Nothing left in reach: 316 blocks overhead (Plan mode
  digs a mountain from the top)" instead of "Nothing left to work".

## Numbers

Test: `reports/polish-night-1026/zones/zones_scenes.dm` (one arena, seven realms), 8 minutes at speed 4, Humans at
skill 25. "Worked" = at the tree or rock; "walking" = to it; "lifting" = pieces from the ground.

| Scene, 5 workers | stored, before -> after | walking | lifting | stuck (worker-seconds) |
|---|---|---|---|---|
| Two zones side by side | 360 -> 376 | 4% -> 6% | 10% -> 10% | 1,941 -> 0 |
| Half-walled wood | 24 -> 32 (all it can reach) | 91% -> 2% | 0 | 1,974 -> 0 |
| Rock outcrop, with loops' miners fix | 353 -> 440 | 5% -> 22% | 30% -> 8% | 1 -> 0 (lying 93 -> 0) |

| Half-walled wood, 20 workers | before | after |
|---|---|---|
| logs in 8 min | 0 | 32 |
| first log | never | 34.5 s |
| workers stuck 30 s or more | 20 | 0 |

**The Tend redo (regrow-living-off)**, 30 minutes at speed 4, 5 workers a zone; today's live game against live + the
redo (`tests/zones-live5L.json`, `tests/zones-lo5L.json`; README in `reports/polish-night-1026/zones/regrow-living-off/`):

| Scene | stored | wood per worker-hour | time off the zone | saplings planted / grown |
|---|---|---|---|---|
| Wood, 64 trees | 128 -> 325 | 51 -> 130 | 83% -> 2% | 64 / 64 |
| Wood 45 tiles from the stockpile | 128 -> 335 | 51 -> 134 | 70% -> 0% | 64 / 64 |
| Half-walled wood | 64 -> 168 | 26 -> 67 | 91% -> 12% | 32 / 32 |
| Gather zone, trees + rock | 307 -> 402 | 123 -> 161 | 67% -> 5% | 32 / 31 |
| Wood + stone side by side | 427 -> 579 | 85 -> 116 | 76% -> 31% | 45 / 45 |
| Rock outcrop, mountain face | 441 -> 456, 322 -> 308 | - | unchanged | - |

Pieces left lying: 0 everywhere. Toasts: 0 a minute (loops-batch quietened automatic work; before it, my scenes showed
2-12 toasts a minute a zone, most of them "click the rock again to dig the next one").

**Speed** (the settlement call timed 10 times at the end of `tests/gather_score.dm`, ms for the 10; each figure one run,
other sessions' runs going): 2,000 workers, live 63.6 and 73.9 -> with the redo 33.1, 34.6, 52.1, 33.8 (wood 2,465 ->
10,300 in 5 minutes, stone the same); 20 workers 0.3, 0.5 -> 1.3, 0.6. The 190 ms I read before the stop was haulers
with bags of ore no store takes reading all 15,700 pieces in 41 yards on every step; loops-batch stopped miners lifting
such ore, and the cost went with it (I had a throttle for the haulers' look ready; with loops-batch in it measured no
gain, so it was withdrawn).

Its own checks on a fresh copy of live + the redo: regrow_test, living_test, jobs and yield (redo versions),
gather_zone_test (its tree check updated from Tend's "worked to half" to "felled whole, a stump each"), j2_wood, lodge Elf
(built from gathered wood, banner up), the 30-minute scenes: all pass.

## Needs the owner

- **Landed the parked regrow + no-Tend redo on your "make zones work better"; undo = restore point
  `restore-points/before-polish-regrow-living-off-20261027-015107`, or switch `rm_zone_regrow = 0` (Jobs.dm; nothing
  regrows then).** A 64-tree wood with 5 workers: 128 -> 325 logs in 30 minutes, workers off the zone 83% -> 2%, all 64
  stumps replanted and grown back; the far wood 128 -> 335; wood + stone side by side 427 -> 579. Server cost at 2,000
  workers is no higher than today (settlement 63-74 -> 34-52 ms for 10 calls). Build 67 has it alone, to compare with 66.
- **A worker waiting on saplings keeps its place on the wood row.** When rows ask for more than the village has (a test
  with 20 villagers, wood wanting 40 and stone wanting 40), today a "Resting" wood let its workers fall through to stone
  (wood 105, stone 618 in 5 min); now the wood row keeps them planting and tending (wood ~436, stone ~24). With numbers the
  village can fill, both rows work. In a wood whose trees are all saplings, about half its workers' time is waiting for
  the next visit. Should a waiting tender go and help a short row, and come back when its saplings are due? (A change of
  the board's rules, so not done.)

- **"Tell them where to place it" (your message tonight).** Today a zone's loads go to the nearest store that takes them:
  its own yard (made by itself on the village side) or any store you paint ("Stockpile here", + Store). What doesn't
  exist is pointing one zone at one store ("this quarry's stone goes to the stockpile by the forge"). It would be a
  "Deliver to" pick on the zone's row (and a drag from the zone to a store in 3D): its carriers use only that store, no
  yard is made, haulers leave it alone. Gains: workshops fed from their own quarry, no wood crossing the village. A new
  control, so after the freeze; say if you want it.
- **Mountain zones: how much of a mountain a stone zone should take.** Today: each column's floor block (a one-block
  crawl under the rock), then it stops. I tried the three blocks a miner reaches, top down, like a click: 5 miners 316 ->
  625 stone in 8 min and still working at the end. But 1 miner: 240 -> 99, because a block above the bottom two gives 0.7
  stone under the block-by-block rule against ~4.7 for the bottom two (2.4x less stone a minute of digging). A yield
  question, so not landed. Choices: (a) as now (the row says what's left overhead and points at Plan mode); (b) the
  bottom two blocks (2-high halls, the same stone a minute, twice the stone from a zone); (c) three blocks top-down, with
  upper blocks giving stone like the lower ones.
- **Fishers released from a fishing zone** (a spot drifting out of it) were seen once standing "Paused for manual
  orders" for 2+ minutes; not seen again in a traced re-run, so not changed. Noted for the loops chat.
