# Polish, second pass: gather zones (polish-zones, 10-27)

Last night's work (zones-batch, the Tend redo) is in `devlog/2026-10-26/polish-zones.md`. Today the lead's fixes hold most
of the zone code (the regrow tick-spike fix, first house, ore storage, mountain digging), so anything of mine in Jobs.dm,
Yield.dm, Zones.dm or Delivery.dm is staged for the lead to land after those, not landed by me.

Focus: fishing and farm zones, and what the zone rows say on the HUD. I made them the way a player does in the test arena
(`reports/polish-night-1026/zones/zones_fish.dm`: a shore with 3 fishing spots and 5 villagers; `zones_farm.dm`: a farm
painted on plain grass, 12 seeds on the stockpile, 3 villagers, two with a spade) and read each minute what the row says
against what the people do.

## What I saw (today's game, build 68)

- **Fishing works**: first fish in 20 s, about 21 food a minute, the row's +N/min matches. But the row holds 3 of the 5
  asked for, two villagers stand "free, waiting for a job" for the whole run, and nothing says why (one fisher a spot).
  Its "Fill" button offered "room for 56" (one worker a 4 tiles of a 9 x 25 shore).
- **Farming works**: 15 farmland tilled and all 12 seeds in by minute 1, first food at 2 min, 120 food in 15 min. But the
  farm's row read **+0/min the whole time**, and a farmer on its way to wait at the farm read "Farm 1: Farm 1: going to
  the farm to wait for the crops" on its card and on the row.
- **A leftover from Tend**: a miner's first find in a living ore block still said "miners leave the last one so it
  lives (right-click it to tend it or dig it out)". There's no tend click any more and miners dig a block out whole.

## Fixes

| Fix | What changes | State |
|---|---|---|
| `zones/p2-fish-farm-rows` | Fishing row: a "3 fishing spots · one fisher each" tag; Fill and "room for" = the spots (3, was 56). Farm row: each harvest counts in its +N/min (+0 -> ~8/min, 120 food in 15 min both runs) | LANDED 08:46 (restore point `restore-points/before-polish-fish-farm-rows-20261027-081955`) |
| `zones/p2-farm-name-once` | The farm's name once in a farmer's line (3 doubled lines -> 0 in the farm scene) | STAGED (Jobs.dm), for the lead |
| `zones/p2-start-over-clears-work` | Owner's bug (via hud-rework): starting over kept the old company's work zones. Restart now empties the old rows, zones, plans, sites, board orders and the stockpile's place (8 rows -> 0; the new company chops 0 -> 57 wood in 2 min) | In the lead's batch after build 83 |
| `zones/p2-living-ore-words` | "...grows one back every 20 minutes while some is left in it; each ore deeper in is harder to dig. Dug out, it's gone." | STAGED (Yield.dm) |

Speed: none of them adds work to a tick (a count on a harvest, a string, a page tag).

Each fix's README (in `reports/polish-night-1026/zones/<fix>/`) has its proof. The staged two wait for the lead's
Jobs.dm and Yield.dm landings; their anchors were checked on today's live game.

## Needs the owner

Nothing new. Last night's questions stand (devlog/2026-10-26/polish-zones.md): waiting tenders helping a short row,
mountain zones, "Deliver to".
