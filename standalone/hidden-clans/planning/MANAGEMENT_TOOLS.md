# Management tools: running thousands of units by rules (plan, 2026-10-24)

**Goal.** One player runs a village of hundreds, later tens of thousands, of units the way Songs of Syx does: by saying
*what work exists and how many hands it gets*, never by clicking each unit. Direct control stays for heroes, armies and
emergencies. The same rules are what an unwatched or offline village runs on as a record (the 30,000-unit and
1,000,000-unit targets, `MMO_ARCHITECTURE.md` §7), so nothing here may cost per unit per tick more than a few steps.

Four tools, in this order:

1. **Work zones:** paint an area and say what work it holds: wood, stone, a farm, or a stockpile.
2. **The job board:** every kind of work in one list, with how many workers each wants and its priority. Free
   villagers fill the slots by themselves.
3. **Stockpile rules:** what goes where, how much each store keeps, and who carries it.
4. **The population overview:** counts by job, idle, hungry, hurt, tired. Click a count to select those units.

The first slice to build is 1 and 2 together, with units taking work from them (section 7).

---

## 1. What already exists, and what each tool reuses

| Exists | Where | Used by |
|---|---|---|
| Roles with a work area (woodcutter, miner, hauler, farmer, hunter, cook, builder, board worker...): a unit works within 6 tiles of a spot | `Delivery.dm` `RemasterRoleTick`, `FoodRoles.dm`, `Settlement.dm` | Zones hand out these same roles, so the work itself is the game's own (chop, dig, plant, deliver, tend) |
| Bulletin board: work orders with a worker count, priority 1–3, standing "keep at least N" orders, a free pool of board workers | `Board.dm` | The job board is this, grown up: every kind of work becomes a row; the board worker pool becomes "free villagers" |
| Stockpile and filtered stockpile zones | `Zones.dm`, `Settlement.dm` | A stockpile work zone *is* a stockpile zone, painted |
| Single-click work orders and the Gather switch (G) | `Orders.dm`, `QoL.dm` | Unchanged. A direct order takes a unit out of its job until it's done, then it goes back (as board workers already do) |
| Groups (right-click Group / Ctrl+G) and formations | `Formations.dm` | A job's workers can be made a group in one click (Select → Group); armies stay groups, not jobs |
| The Work tab's production queue | `Settlement.dm`, `StationCraft.dm` | Later: a workshop becomes a job with a standing product and "stop at" (section 6) |
| Village › Log | `VillageLog.dm` | Jobs write one line per job and batch, never per unit ("Woodlot: 4 woodcutters brought in 12 wood") |
| Living resources, tending, yields | `Yield.dm` | A wood zone follows the realm's tend setting; the zone's target list leaves tended trees alone |
| Painting by drag in 3D (the build painting: `paint3d`, the page's paint mode) | `Blueprints.dm`, the page | Zones are painted with the same drag; no new picking code |
| The away catch-up | `Away.dm` | Catches up per job (worker-count × time), the start of the records tier |

**From the workplaces prototype** (`prototypes/workplaces/`, run only in test arenas, never shipped), lessons that
carry over:

- Free workers staffing slots by themselves through the board worked cleanly. So did keeping a worker inside its zone
  with one check in `RemasterClaimed`, stopping at a "stop at" mark, and clearing loose goods in the zone before
  standing down.
- A worker's 6-tile role scan is the cost to remove at scale (section 5).
- HUD scripts added to the page must sit *before* the page's last script: its `send('ready')` is a navigation, and
  WebKit stops reading the page there. Chrome hides this; only a real WebKit view shows it.
- The user's direction for later: **a banner declares a place** (woodcutter's lodge, quarry lodge, wood store), a
  building is dragged over it, and benches inside set the worker slots. Zones here are the ground layer that lodges
  will sit on: a lodge is a zone with a banner and furniture-set slots, added after this slice.

## 2. Work zones

**Painting.** Work tab › Zones › **+ Wood / + Stone / + Farm / + Stockpile**, then drag a rectangle on the ground in
3D (the build drag, so it's the same feel as planning walls). The zone is outlined on the ground in 3D in its colour
(wood green, stone grey, farm gold, stockpile the zone's filter colour), with its name on a small plate. A click on
the outline opens its card.

**A zone's card:** name · kind · size · what's in it (trees, rock blocks, farmland tiles) · **workers wanted** (− +) ·
**priority** (High / Normal / Low) · **stop at** (the store total where it pauses, optional) · tend (follows the realm,
or on/off) · Pause · Remove.

**Rules:**

- A zone can be up to 25×25 tiles. Bigger areas are several zones, which is also how the player splits work.
- Wood zones work trees and follow tending. Stone zones work rock blocks the player can reach (the block-by-block
  mining rules, never cubes). Farm zones till grass and plant and pick (the farmer's own steps). Stockpile zones are
  stores with a filter (section 4).
- A zone belongs to its realm. Claims and war rules apply as they do for any work today (`Claims.dm`).

**What it costs.** Each zone keeps a short **target list**: the workable tiles in it (trees standing above their tend
mark, reachable rock faces, farmland states). The list is built once when the zone is painted, and refreshed only when
something in the zone changes: a tree falls or regrows, a block breaks, a field is planted. Those already announce
themselves through `Yield.dm`, `Breaking.dm` and the farming hooks. A slow sweep every 60 s catches anything missed.
Workers take targets from the list. Nobody scans the area.

## 3. The job board

One panel lists every kind of work in the realm as a **job row**:

```
Job              Workers   Priority   Status
East woodlot      4 / 6    ▲ High     Chopping · 38 wood in store (stop at 60)
North quarry      2 / 2    ● Normal   Mining · 12 stone
Wheat field       3 / 4    ● Normal   Planting
Builders          1 / 2    ▲ High     3 plans waiting for wood
Haulers           2 / 3    ▼ Low      Carrying 5 things in
Free villagers   11                    —
```

- **Rows** are every zone, plus the jobs that aren't places: builders, haulers, doctors, cooks, hunters, and later
  workshops and lodges.
- **Workers** is "assigned / wanted", with − + on the row. A slider would be fiddly at 30,000 units, so for big numbers
  a click on the number lets you type it.
- **Priority** decides who is served first when there aren't enough hands: High rows fill first, then Normal, then
  Low. Within a priority, nearest zones go first.
- **Free villagers** are units with the new role **Any work**. The job board takes its workers only from them. A unit
  with a fixed role (a woodcutter you set by hand, a doctor) keeps it. New villagers (births, migrants) join as Any work,
  so a growing village staffs itself.
- **Pausing** a row frees its workers back to the pool. Removing a zone does the same.
- Clicking a job's name selects its workers. From there, Ctrl+G makes them a group and the camera button goes to them.

**The allocator** (changed after the coordinator's review: no loop over every unit every 2 s, since at 30,000 units
that would be a spike of tens of ms per player).

- **Running totals.** Each row keeps its worker count and member list, and the realm keeps the free pool, sorted into
  16-tile cells. They're updated only where something changes:
  - a unit joins or leaves a row;
  - a player changes a unit's role (`RemasterAssignJob`);
  - the records session folds a unit into a record or wakes it (`RmJobUnitGone` / `RmJobUnitBack`).

  Deaths, captures and deletions are found the moment a list is used: invalid entries are dropped and the totals
  corrected.
- **A pass every 2 s** (in the player's settlement tick) walks the rows by priority. It fills shortfalls from the
  nearest free units, searching outward cell by cell from the zone (`rm_near` later), and releases the furthest members
  of rows over their count. That's O(rows + units moved).
- **A worker isn't moved between rows for 60 s** after joining one, so slots don't flap. The exception: a High row that
  can't be filled from the pool may take workers from Low rows.
- **A recount every 60 s**, staggered across players, rebuilds the totals from the realm's units, as a safety net. The
  population overview (section 5) reads the same running totals.

## 4. Stockpile rules (after the slice)

- Each store (the main stockpile, each painted stockpile zone, cart stops, food pots and stalls) gets a **filter**,
  which exists today, plus **keep at most** and **keep at least** numbers per good.
- **Haulers by rule:** a store below its "keep at least" asks for that good, and haulers carry it from the nearest store
  above its own need. That's Songs of Syx's pull orders. It replaces today's "board workers carry from the main
  stockpile to zones".
- **Delivery goes to the nearest store that accepts the good.** Today it's the stockpile or the nearest cart stop.
- **The Village stores bar** (proved in the prototype): totals across all stores, with what people carry shown apart,
  and a click to see where everything is.

## 5. The population overview (after the slice)

The Village tab gets a header band of counts. Each count is a button that selects those units:

`212 people · 41 idle · 18 hungry · 7 hurt · 3 bleeding · 26 tired · 9 carrying · by job: wood 40, stone 22, farm 30,
builders 6, haulers 12, any work 41 …`

It's built server-side in one pass over the realm's units, cached 2 s. It's the same pass as the allocator's count,
so it adds nothing.

## 6. Scale, the engine and the other sessions

- **Who owns what.**
  - The records session (*Far-away units as simple records*) owns sleep and wake for unwatched units. A record's work
    points at a job row: zone, workers × rate × time, limited by what's left and "stop at". This plan owns those rules.
    No `Away.dm` or catch-up code is written here.
  - The performance session owns the unit clock and native code. Each worker's job step is one proc,
    `mob/Monsters/proc/RmJobStep`, with no sleep loop of its own, so it can move onto the clock.
  - `Orders.dm` (the formations session's) needs no change. A direct order already pauses a unit's role
    (`RemasterSettlementTick` skips units with an order), so a job worker given an order does it, then goes back to its
    job.

- **No new forever loops per unit.** The allocator runs in the player's settlement tick, and a worker's own step runs
  where roles run today (`RemasterSettlementTick`'s dispatch).
- **Per worker per step: O(1).** Take the next target from the zone's list (a reservation), walk (native route search),
  work with the existing Chop/Mine/plant code, deliver with the existing delivery.
- **Records tier:** a job row is exactly what an unwatched village simulates (see "Who owns what" above).
- **Native candidates** (performance session's call): zone target list refresh, and the free-worker nearest search
  (`rm_near`). The rules stay in DM, as ENGINE_PLAN says for units' decisions.

## 7. First slice: work zones plus the job board

**In:**

- A new file, `Code/Remastered/Jobs.dm`, and a HUD panel in `Interface/remastered.html`, following STYLE.md: material
  tokens, the type scale, task-card lists, and empty states.
- **Wood, stone and farm zones.** Painted by drag, outlined in 3D, each with a card (workers wanted, priority, stop at,
  pause, remove), and each with a cached target list.
- **Stockpile zones** painted the same way, as today's zones with a filter. No new rules yet.
- **The Any work role and the allocator:** free villagers fill zone rows by priority with no clicks, using the roles'
  own work steps but taking targets from the zone list instead of scanning.
- **The job board panel:** zone rows plus the builders and haulers rows, and the free pool. − + and priority on each
  row, and a click on a name to select its workers.
- **Log lines** per job, batched.

**Not in this slice:** lodges and banners, workshops as jobs, stockpile keep rules, the population overview, records
and catch-up.

**Done looks like:**

1. **The arena proof** (`tests/jobs_test.dm` plus `tools/check_jobs.py`, under `runlock`, light arena): 500 units on
   Any work, three wood zones, two stone zones and one farm zone with set workers and priorities.
   - With no per-unit clicks, the slots fill in priority order within a few allocator passes.
   - Every worker takes its targets inside its own zone.
   - The stores rise.
   - Reducing a row releases workers to the pool, and raising it takes them back.
   - Also measured: the allocator's ms per pass at 500 and at 5,000 units (`world.tick_usage`), and the per-unit cost
     against the old role scan.
2. **A real-WebKit check** (`wkshot` / `capture_hud.py --engine wk`, never Chrome alone): the job board and the zone
   card, with real data, at the four sizes and in two materials. No text under 9 px, no clipping, and no console
   errors.
3. **One short real-client check** at the end, under the lock.
4. **game/ keeps compiling** after every edit. `node --check` runs on every script block, and edits are exact-match
   after a fresh read. No app builds while the build hold is up.

## 8. Questions for the user (with the defaults the slice uses)

- **Do new villagers default to Any work?** Default: yes. Units you've set by hand keep their role.
- **The cap on a zone's workers:** default: up to one per 4 tiles, so a zone can't swallow the village.
- **Do zones need a banner?** Default: not in this slice. The lodge/banner design comes next and builds on zones.

## 9. Built (first slice, 2026-10-24)

**Where it lives.** `game/Code/Remastered/Jobs.dm` (included last in the .dme: OpenDream chains an override placed
before a proc's own definition the wrong way round), small hooks in `Settlement.dm` (the Any work role and its
dispatch, `RmJobRoleChanged`) and `HUD.dm` (Any work in the roster's job list), and the Work tab's job board in
`Interface/remastered.html`. Arena proof: `tests/jobs_test.dm` with `tools/check_jobs.py`.

**What it does.**

- Work tab › Job board: + Wood / + Stone / + Farm / + Store put the build drag into a zone mode; the drag shows the zone
  it will make and its size and worker room, clamped to 25 tiles a side (farms 21). A zone is outlined on the ground in
  its colour with corner posts (drawn on the ghost path, V3.dyn).
- One task card per row (zones, then Builders and Haulers): workers − + (Shift: 10) and Max, priority, Pause, Go to,
  Select workers, Remove, stop at (± 10, Shift 100) against the stores, a bar and the row's status. Free villagers
  are counted above; an empty state shows until a zone is painted.
- The unit card shows the race alone, or the real job: the row's name ("Human · Wood 1") or a set role. The old
  best-skill title is the line's tooltip (the user, 2026-10-24: units are just their race by default).
- Villagers born once a realm has zones join Any work. Each pass logs one Village › Log line per row that changed.

**The allocator.** Running totals (rows' member lists, the free pool in numbered 16-tile cells with per-level counts).
A pass every 2 s moves at most 25 units (`RM_JZ_MOVES`) and checks a rotating slice of 64 workers per row
(`RM_JZ_CHECK`), so no pass reads every unit. A pick reads at most 48 candidates per ring, walking ring edges only. The
recount (the safety net) runs every 60 s, staggered across players. In the player's spread track run (Spread.dm) the
pass and the recount pause at safe points. Tick profile names: `track/jobs`, `track/settlement/any work`.

**Arena numbers** (OpenDream, with other sessions' runs sharing the machine):

| | |
| --- | --- |
| Steady pass, 500 units | 0.7–1.7 ms |
| Steady pass, 5,000 units | 0.25 ms |
| Filling 500 jobs | 21 passes at 25 moves; slowest 19 ms (11 passes at 50: 26–52 ms) |
| 50 moved from crowded cells (5,000 units) | 3 ms; slowest of 20 such passes 8 ms |
| Recount, 5,000 units, in one go | 43 ms (spread over ticks in the track) |

**Real client (2026-10-24, the user's OK, 16:0x): 12/12 in 3D.** A small village with 20 villagers on Any work and a
wood and a stone zone: the rows filled to 8/8 and 4/4 with no clicks, the outlines show on the ground, the Work tab's
board shows every row, Go to centres the 3D camera on the zone, + Wood starts the paint mode. The harness stops at once
unless the page sent ready and the 3D view is on (an earlier run sat in 2D when another change swallowed the ready).
Fixed after the first run: Go to now calls RemasterCamTo (the page's camera follows only a jump).

For far-away units (FarRecords.dm): `RmJobUnitGone` / `RmJobUnitBack` keep the totals, and `RmJobAsleep(M)` tells the
records session what an asleep worker's row has it doing (job, centre, how much is left before the stop at).

The move cap is 25 per pass since the coordinator's 20 ms limit: filling 500 takes 21 passes (slowest 19 ms); at 5,000
units 1,000 fill in 41 passes (slowest 3 ms).

**Found on the way.** With tending on, every tree in a wood gives its log and rests, and the wood's rows stand down
until the trees regrow. That's the living-resources rule working. At the user's ask (2026-10-24) a zone's tag shows
"0 ready · 16 resting" and its status "Resting: every tree has given its log and is growing back" (stone: living ore
at its mark rests the same way, so no miner goes back to it). With no worker yet, tending follows the realm's setting:
with it off, a half-cut tree is work again.

**Polish pass (2026-10-24, the user's ask).** Staffing from the board: Selected → Any work, and Idle → Any work (idle
villagers on Manual; units kept in a control group stay as they are). A row says what its workers are doing ("7
chopping · 4 carrying in · 1 waiting", from 60 of them at most). Work zones can't overlap: the drag turns red and names
the zone in the way, and the server refuses it with the paint mode kept on; a store may sit inside one. The drag is
drawn in the zone's colour and counts the trees or rock under it. Each zone has a name plate in 3D ("Wood 1 · 6/8",
on its far edge); a click opens its row on the Work tab. Remove asks twice. Village Log lines are batched (one per row
at most every 30 s). Removing a zone clears everything kept for it.

Second round: a row's wanted number can be typed (click it; Enter sets it). A zone can be renamed (double-click its
name; plain characters only). Hovering a row on the board makes its zone stand out in 3D and lights its plate. In
colour-blind mode the drag is blue, or vermilion over another zone. Plates hide when the camera is far out. When
villagers are free but no row wants more, the free line says so. Rows aren't redrawn under a field being typed in.

Third round (the user's ask: easier to read and use):
- **One line per job,** a click opens its controls: name, a small workers bar, what's happening (or what needs the
  player, in amber), and what it gathered in the last minute ("+9/min", from Yield.dm's "+1" notes credited to the
  worker's zone). Opened: what's in it, priority, Pause, Select, Go to, Rename, Remove, workers "12 of 12 wanted" with
  − + Fill ("room for 156"), stop at. Which jobs are open is remembered.
- **Stores a minute** at the top of the board: what the stores gained or lost over the last minute (wood, stone, food,
  sampled every 10 s), with how many work and how many are free. Group headers add up their zones' output.
- **Plainer words:** the role is "Job board" (it was "Any work"); "Selected / Idle → job board"; jobs, not rows. A
  first-time guide (paint a zone, give villagers to the board, watch the wood come in) ticks itself off from what the
  realm has done; "Got it" puts it away.

**Not yet.** Zones can't be moved or resized (remove and paint again). Farm rows show no field counts or output. Stockpile rules, the population overview, lodges and
banners are the next slices.

## 10. Toward one player and 30,000 units, then sectors for nobles and lords

The user (2026-10-24): get as close as possible to one human running 30,000 units, Songs of Syx-style. Later, with
multiplayer, those 30,000 are split: nobles and lords run sectors of the kingdom while the King rules it all, with
politics and feuds between them. So every tool works on areas that can be handed over, not on one global list.

**Built so far for scale.** The job board with rows that fill themselves (section 9). Staffing in two clicks
(Selected / Idle → Any work). Board groups by kind that fold, with a summary line each. The population overview at the
top of Village › Roster: people and animals; work (on job rows, free, Manual, idle, each set role); needs (hungry,
need rest, low health, bleeding, cold, limb lost); doing (asleep, eating or resting, carrying in, fighting). A chip
selects those units (up to 500). It's counted 1,000 units a pass, so it costs the same per pass at any size and shows
how old its count is.

**Next, in order:**

1. **Sectors (districts).** A named area of the realm, painted like a zone but large (up to a few hundred tiles a
   side), that owns the work zones, stores and builders inside it, and a share of the free villagers. The board and the
   overview group by sector; a sector has its own priority. Built so that later a sector has a lord: another player who
   sees and runs only its rows, its stores and its people, while the King sees every sector and what each sends up.
2. **Workshops as jobs.** A workshop row with a standing product ("keep 20 tools", "keep 40 bread"), workers wanted and
   priority, like a zone row: the production queue without per-unit clicks.
3. **Stockpile rules.** Per store: what it takes, how much to keep, and haulers that move the rest (Zones.dm filters
   plus amounts).
4. **Alerts that add up.** One line for "23 hungry and the food stores are empty" instead of 23 warnings; each with a
   select and a go-to.
5. **Cost at 30,000.** The board and the overview are sliced. The HUD's unit list (HUD.dm) and the per-unit settlement
   loop are the performance session's; the job step and the free-pool search are theirs to move into engine code when
   the numbers say so.

## 11. The supply chain: Gather, Make, Serve (planned 2026-10-24)

The user (2026-10-24, "we should do this then"): turn the job board into one supply-chain screen with three sections,
built on the systems that exist rather than replacing them.

**The screen.** The top of the Work tab, where the job board is now, becomes **Supply chain** with three tabs (the
choice remembered): **Gather · Make · Serve**. Each tab's label carries its own "needs you" count. Under the tabs, one
line for the whole chain: the stores a minute (wood, stone, food), as the board shows now.

- **Gather** is the job board as it is (zones: wood, stone, farms, stockpiles; Builders and Haulers).
- **Make** is the Bulletin board's orders, as rows like the job board's: the label ("Craft 5 Wooden axe", "Make bread
  ×3 at the Kitchen", "Gather athelas: 3"), workers on it of wanted (− / +), priority, progress (2 / 5), output a minute
  (progress gained over the last minute), status, Cancel. Standing orders ("keep at least 30 wood") are a "Keep in
  stock" group at the top: the amount, now, on/off, priority. "+ Order" opens the post form here (work, amount,
  priority, workers, where). The Village › Bulletin board tab opens this tab: there is one board.
- **Serve** is where goods go out to people: food pots and stalls, Doctor's stalls, taverns, market stalls, grouped
  Food / Health / Drink / Trade. Each row: name and place, how full (12 / 30, a bar), who keeps it filled and how many
  of them there are ("3 cooks, 5 farmers"), how fast it empties (−8/min) and fills (+6/min), and "runs out in about 2
  min" when it empties faster. A row opens to show what's in it (servings by kind, herbs and remedies, cups), the pot's
  fire, Go to. Problems surface the same way as the job board's: "poison suspected", "the pot's fire is out", "nobody
  fills it: give a villager the Cook job", "empty".

**One pool of workers.** Make orders are staffed from the job board's free villagers, like a zone row (a "make" row
per open order: its workers wanted are the order's workers, its priority the order's). A villager on it claims the
order and does the board's own work for it (RemasterBoardWork: the borrowed woodcutter / miner / hauler role, herb
gathering, the production queue, a station). Villagers set to the Board worker job still claim orders as before; a
make row only wants what they leave (the order's workers less the Board workers on it). A villager that can't do an
order (a Spider at carpentry) is passed over for it. Finished or cancelled orders release their villagers to the pool.

**Rates without loops.** Serve: each store keeps a running count of what was put in (the food store's Put, the
Doctor's stall's PutIn, the tavern's PourIn and Press) and a sample every 10 s of how full it is; out = in − change.
Make: each order's progress sampled every 10 s. Who fills: the population overview's role counts (cooks, farmers,
doctors, merchants) and the farm rows' workers. Market stalls are kept in a list as they are built (the market looked
through the whole world for them). All of it per player, O(stores + orders) a call, nothing per unit.

**Tests.** An arena test (tests/chain_test.dm, tools/check_chain.py): a make row fills from the free pool and its
villagers finish a wood order and a craft order; Board workers and job board villagers share an order without
going over its workers; cancel frees them; a stall's fill, in and out a minute match what was put in and eaten; a pot's
thrown-out food isn't counted as eaten; the market stall list. Then the cost at 500 / 5,000 / 30,000, a WebKit
capture of the three tabs (STYLE.md), and the board, settlement, delivery and jobs checks unchanged.

**Built (2026-10-24, evening).** As planned above, with these specifics:
- Work tab: the board is **Supply chain** with Gather · Make · Serve tabs (remembered, arrow keys move between them),
  each tab with a red count of what needs the player; the Work button's badge adds them up. The "Stores a minute" line
  sits under the tabs for all three; the free villagers and the two staffing buttons show on Gather and Make.
- Make: "Keep at least" (wood, stone, food: amount, now, priority, On/Off; typing an amount turns it on), "+ Order"
  (the Bulletin board's form, crafts and station goods included), the order rows (progress bar and done/amount on the
  line, a minute's output, workers −/+ up to 10 or one for a craft or a station, priority, Pause, Select, Go to,
  Cancel with a second click), Finished with Clear. The Village › Bulletin board tab opens Make.
- Serve: Food (pots, stalls), Health (Doctor's stalls), Drink (taverns), Trade (market stalls); a group line with how
  full they are, who fills them and the minute's drain; a row line with fill, what's in it, −N/min; opened: in and out a
  minute, runs out in about N min, what's in it, the pot's fire, Go to (only onto the player's own store).
- Needs you: Make 6 (nobody can work it: no stockpile, or the filter refuses the good) and 5 (High, short, nobody
  free); Serve 1 (empty and nobody fills it), 3 (poison suspected), 4 (raw meat in a pot with no fire), 6 (a market
  stall with no merchant); 2 (empty) and 5 (runs out within 2 min) are shown, not counted.
- Cost (tests/chain_test.dm, arena): with 20 orders and 30 stores, the chain's 2 s pass 0.1 ms and its HUD data
  0.2-0.3 ms at 500, 5,000 and 30,000 units; the allocator pass with 20 make rows 0.4 ms.
