# Building rework: plan (2026-10-27, revision 2). Plan only, nothing built yet.

The owner approved this on 10-27, word for word:

> "Go: shapes recognised (B), stone+wood first, save each block's material, built walls only broken by sieges/blows,
> first house/lodge as auto-placed block presets, old Build tab becomes Place, old saves untouched, arena first."

Background: `reports/gathering/staged/plan-build-takeover/DESIGN.md` (option B) and `SET_BLOCKS_PLAN.md`. The arena
proof is `reports/gathering/staged/build-by-shape/` (`make_arena.py` recognise(), `check_arena.py` 7/7, stills in
`shots/`). Line numbers below are from the files as read on 10-27, before the staged fixes land. They are there to
help find things. Write every edit against the live text.

## In one paragraph

There is one way to build a wall: Plan mode lays blocks, in stone or wood, and each block's material is saved on its
tile, with the player who laid it. The 3D page draws laid blocks as masonry or timber. It finds walls, round towers and
gateways from the blocks by itself, as the arena does. The server only needs to know which blocks were laid, what they
are made of and by whom. Nobody but the builder's own realm can dig, pick or carve a built block, at war or not, on
claimed land or not. Only siege engines and golem blows take it down, one block at a time from the top. A new village
gets its first house or lodge planned by the game as blocks plus furniture. The old Build tab becomes **Place** and
keeps only placed things. Walls and buildings in old saves keep working exactly as they do now.

## What changed in revision 2 (answers to the review)

| # | Review point | Answer in this plan |
|---|---|---|
| 1 | The first-house fix (a)+(b) alone does not finish the 3-villager rounds (`reports/polish-night-1026/first-house/fix/README.md`: "The 3-villager rounds are not fixed by (a)+(b) alone"; 3 Dwarves never started x3, 3 Humans stuck 36/41 x3) | Agreed. L8 now depends on the separate, unapproved `first-house/fix-order-area` (Board.dm, 2 edits: the area move fires on the new idle wording and goes to the village's own zone first). New question 1. Without it, L8 says plainly that 3-founder Dwarf and Human villages are expected to stall, and L8 does not land (step 5, "Depends on") |
| 2 | Built blocks on unclaimed land could be picked by anyone, and nothing gives a new village a claim | Agreed. Protection is now the default everywhere: L1 also saves who laid the blocks (`remaster_laid_by`, one text var a tile, the builder's key). L7 protects by that key, not by the claim. The claim is used only for blocks laid before L1 landed. Question 6 now asks to confirm this extra saved var |
| 3 | Carving a ramp was missing from the guarded takers, and carving gives 50% stone even from a wood block (Gather.dm:777) | Agreed. RmBuiltHeld is also checked in RemasterCarveRamp (Gather.dm:709), RemasterRampTick (:729, before the first blow) and in the plan way-up search RmPlanAccess (Plans.dm:624), which never picks a held block to dig or carve. Carving a laid block drops nothing (it keeps its 1 for when it is dug). Lay + carve + dig = 1, never more. This follows the approved mountain rule "built blocks give back at most 1" |
| 4 | Undermining was made a feature without asking; opening the floor block (RemasterTakeBlock k=0 -> RemasterOpenColumn) makes a tunnel under the wall; a cave-in can refill it and the staged edit wipes the laid bits | Agreed. Default now: the footing is held too. Under another realm's laid block, the natural blocks of that column are held (RmBuiltHeld says yes for any k below the column's top laid block). Neighbouring natural rock stays diggable, so going round a wall is still possible. Cave-ins skip any tile with a laid bit, in both loops (Mountains.dm:169 RemasterCaveIn, Chains/Bump.dm ~297, the 2006 loop) instead of the staged `remaster_laid = 0` line. New question 7 asks if undermining should be allowed later |
| 5 | The no-click house is not provable: no carpentry means no beds, table or door (Jobs.dm RmJzFurnitureRecipe returns null); the spot search fails in forests with only a click as fallback; "50 starts" had no threshold | Agreed, and one more gap: no stockpile means material orders can't count (Board.dm:37-39 RemasterStockCount returns 0 with no stockpile). L8 now has two tiers: what it always does, and what it adds only if question 4 says yes. The main proof is like for like: the 10-26 round script (`reports/polish-night-1026/loops/play_round.dm`) with its step 7 (placing the house by hand) removed, so the preset makes the house. Spot search: a felling fallback for trees, a retry for the rest, and a pass threshold of 48 of 50 per terrain kind |
| 6 | Allies may pick another realm's built walls | In the code "allied" means the same realm: RemasterAlliedKeys (Realms.dm:22-24) is true only when both keys have the same root (ruler, members, vassals). There are no treaty allies. The rule now says "the builder's own realm" outright. Question 6 asks if members and vassals count (recommended yes) |
| 7 | RemasterMayWork in RmPlanGroundOK changes saved plan rows | Agreed: RmPlanLeft (Plans.dm:83) drops every cell that fails RmPlanGroundOK, so saved rows would lose cells. It is taken out of L7. Question 8: if the owner wants plans kept out of a neighbour's land at peace, the check goes in RmPlanAdd only (new rows), never in RmPlanGroundOK |
| 8 | L9 hides the 8 buildings and the wall stairs although questions 2 and 9 recommend keeping some | Agreed. L9 hides only what has a replacement, and only for the races that have a preset: Fortress wall, Tower, Wooden, Stone, Tribal and Elf wall, and the six buildings that became presets. Kept until questions 2 and 9 are answered (and kept if nobody answers): Kobold den, Rat warren, bone/silk/flesh/secret walls, Wall stairs, Ramp up the wall, halls and lairs. L9 waits for those answers |
| 9 | Laid bits are cleared only in RmStoneOut and the cave-in, so golems and other takers leave stale bits | Agreed, and revision 1 had a worse bug: it cleared the letters inside RemasterTakeBlock / RemasterTakeTopBlock, but the staged code calls those BEFORE RmStoneOut (staged Gather.dm edits: `RemasterTakeBlock(T, k)` then `RmStoneOut(T, k, src)`; the same in RemasterTopBlow, RemasterRoofBlow and Bump). A laid block would then have paid ~2.7. Now there is one tidy, RmLaidTidy, called at the end of RemasterColumnSettle (Gather.dm:116), which every taker goes through. It moves the bits and letters of vanished blocks into tmp "just gone" marks, which RmStoneOut and the siege break read once. Every server reader also masks by the blocks present (RmLaidMask) |

## What is NOT in this plan (not approved)

- No designating, no Room shape, and no supported blocks over open air: no roofs or upper floors of blocks, and nothing
  to walk on over a gateway.
- No bone, silk, flesh, brick or secret-wall blocks. Stone and wood only.
- No wall-walk code for block walls and no two ranks to a tile. Units stand on block tops, as they do on rock today.
- No fighting between layers. Wall and cliff archers are a separate plan, parked
  (`reports/combat/PLAN_wall_cliff_archers_2026-10-26.md`).
- Old walls are not converted. Enemies at war can pick old walls today (Orders.dm:139-148, Chains/Bump.dm:255), and
  they still can after this work. The approval's "as old walls are" was never quite true; old saves stay untouched.
- Only the first house/lodge is a preset. Other one-click presets (wall line, tower, room box) were not approved; see
  question 10.
- No land claim check on plans (question 8), no undermining (question 7), no store/carpentry/banner from the preset
  (question 4), and not the fix-order-area patch (question 1) until the owner says yes.

## Landing order (each is its own landing, proven in an arena first, through the land lock)

| # | Landing | Step | Needs first |
|---|---|---|---|
| 0 | mountain-stone fix (staged; `remaster_laid`, a built block gives back 1) | in flight | - |
| 0 | first-house fix (a)+(b) (staged, Jobs.dm allocator, after the regrow spike fix) | in flight | regrow spike fix |
| 0' | first-house fix-order-area (staged, Board.dm, 2 edits) | **not approved: question 1** | first-house fix |
| L1 | Material and builder on the plan, saved per block; one central tidy | 1a | mountain-stone |
| L2 | Built blocks aren't a quarry: zones and miners leave them alone; they count as walls | 1b | mountain-stone, and L1's RmLaidMask (or a copy of it) |
| L3 | The built look: masonry and timber, mountains stay rock | 2 | L1 |
| L4 | Shapes, part 1: walls and battlements; house roofs follow the walls | 3a | L3 |
| L5 | Shapes, part 2: round towers | 3b | L4 |
| L6 | Shapes, part 3: gateways | 3c | L4 |
| L7 | Built walls only fall to sieges and blows | 4 | L1, L2 |
| L8 | First house/lodge presets placed by the game (and plans shown outside Plan mode) | 5 | L1, L2, L7, first-house fix, fix-order-area (question 1) |
| L9 | Build tab becomes Place; old pieces no longer offered | 6 | L8 proven per race, questions 2 and 9 answered |

L4-L6 are page-only and can go in parallel with L7. L8 now waits for L7 so the first house is never a pickable quarry
for a neighbour. L9 goes last: hiding the old buildings before the presets work would leave a new player with no house.

---------------------------------------------------------------------------------------------------------------------

## Step 1a (L1). Material and builder on the plan, saved per block

### What the player gets
In Plan mode the Build tool has **Stone | Wood**, a two-button switch on the Plan card (key M toggles it in the page).
The card shows "Stone needed N" and "Wood needed N" (and "have N" once RmPlansData sends the store counts). Queued
blocks are drawn blue-grey for stone and amber for wood. Villagers lay wood blocks with logs, fetched the same way they
fetch stone now. Dig a laid block out and it gives back exactly one of what it was made of.

### Numbers
| | Value | Where |
|---|---|---|
| Cost | 1 stone or 1 log a block (unchanged for stone) | Plans.dm RmPlanLayTick 569-577 |
| Fetch | up to RM_BUILD_LOAD 4 a trip, fewer if the bag is full | Plans.dm:238 |
| Work | RM_BUILD_WORK 3 blows a block, both materials | Plans.dm:239 |
| Highest | RM_BUILD_TOP 8 | Plans.dm:237 |
| One plan | RM_PLAN_MAX 600 blocks; the page splits a bigger queue into several plans, never cut silently | Plans.dm:19 |
| Give-back, laid block, any way it is dug (click, Dig down, from the top, a roof, a plan) | exactly 1 of its material | staged Yield.dm RmStoneOut |
| Give-back, natural block | ~2.7 stone (unchanged from the staged fix) | staged Yield.dm |
| Carving a ramp into a laid block | **nothing** (today 50% a stone, Gather.dm:777); the block keeps its material and gives 1 when dug | Gather.dm:729 RemasterRampTick |
| Carving a natural block | unchanged (50% a stone) | Gather.dm:777 |
| Wood counts as | /obj/Items/woods/wood, bamboo included | Breaking.dm:118 |

A laid block never gives more than it cost, however it is carved or dug, so laying and digging the same cells can't make
stone or logs.

### Saved format (the approved save addition, plus one var for question 6)
- **`remaster_mat`, turf text var**, declared next to the plan vars (Plans.dm:241-243). One letter for each block index,
  counted from the floor: `s` = stone, `w` = wood, `.` = not laid. Example: `..ss` = two laid stone blocks on two
  natural ones.
- **`remaster_laid_by`, turf text var**: the key of the player who laid the tile's laid blocks. Written when a block is
  laid on a tile with no laid blocks left; kept while any are left; cleared by the tidy when the last one goes. Read only
  in L7. This is one more saved var than the approval named; question 6 asks to confirm it. Without it, built blocks on
  unclaimed land have no owner and anyone could dig them (review point 2).
- The staged `remaster_laid` bitmask stays the mark of "laid by a plan". `remaster_mat` is read only where that bit is
  set. A laid bit with no letter is stone (blocks laid between the mountain-stone landing and this one).
- **No WorldSave.dm change and no version bump.** The world save writes every turf var that is a number or text and
  differs from its start value (WorldSave.dm:119-133 RemasterTurfRecord). The load writes only vars that exist
  (156-164). So an old save has neither var and loads exactly as before; an older build reading a new save skips them.
- Every change to the letters or the key dirty-marks the tile (`remaster_dirty_turfs`), because neither is part of the
  tile signature (WorldSave.dm:73-74). RmPlanPutBlock (Plans.dm:306), RemasterTakeBlock (Gather.dm:209) and
  RemasterTakeTopBlock (:395) already dirty-mark.
- Plan rows get a field `mat` ("stone" or "wood"). The rows are saved with the player (rm_jz, Jobs.dm:51). An old row
  with no `mat` lays stone.
- Plan-built blocks in old saves, laid before the mountain-stone fix, have no laid bit. They stay natural-looking rock
  that gives ~2.7 stone. That is the "old saves untouched" reading.

### One central tidy (review point 9)
The staged code takes the block first and pays after (Gather.dm RemasterBlockTick: `RemasterTakeBlock(T, k)` then
`RmStoneOut(T, k, src)`; RemasterTopBlow, Mountains.dm RemasterRoofBlow and Chains/Bump.dm do the same). So the bits and
letters can't simply be cleared in the takers. Instead:
- New tmp vars `rm_laid_gone` (bitmask) and `rm_mat_gone` (letters): the laid blocks that just vanished.
- New `RmLaidTidy(T)`, called at the end of RemasterColumnSettle (Gather.dm:116). Every taker goes through it:
  RemasterTakeBlock 208, RemasterOpenColumn 223 (ends in ColumnSettle, :243), RemasterTakeTopBlock 394, RemasterRoofBlow
  (staged: ColumnSettle then RmStoneOut), so golem slams (Golems.dm:305, RmGolemRise :448) and the new siege break are
  covered with no edit of their own. It moves each laid bit whose block is no longer there (RemasterBlockThere) into
  `rm_laid_gone`, with its letter, clears it from `remaster_laid` and `remaster_mat`, clears `remaster_laid_by` when no
  laid bit is left, and dirty-marks the tile if anything changed. Cost: at most 16 RemasterBlockThere calls, only on a
  tile that has a laid bit (one `if(!T.remaster_laid && !T.rm_laid_gone) return` first).
- RmStoneOut (staged Yield.dm) pays a laid block when `(remaster_laid | rm_laid_gone) & bit`, by its letter (1 stone or 1
  log), and clears that bit from both. The siege break reads the same marks for its 60% drop.
- RmPlanPutBlock clears bit k from `rm_laid_gone` too (a fresh block), as it already clears the staged bit.
- `RmLaidMask(T)` = `remaster_laid` ANDed with the blocks present. Every server reader (L2 counts and exclusions, L7
  targets and guards) uses it, never the raw bits.

### Files
- `HUD.dm:916-918`: `planadd` reads a 4th field, `stone` or `wood` (missing = stone).
- `Plans.dm`:
  - RmPlanAdd (32-72) gets a `mat` argument and stores `Z["mat"]`; one row per material.
  - RmPlanBuildStep's stone fetch (457-482), RmPlanLayTick (518-579) and the access step's lay (802-810) use the row's
    material path instead of the hard-coded stone.
  - RmPlanLayTick, after RmPlanPutBlock and the staged `remaster_laid |=`: writes letter k and `remaster_laid_by`.
  - RmPlanPutBlock (305-325) clears a stale letter and `rm_laid_gone` bit k.
  - RmPlansData (185-206) sends `mat` (and the stock counts if cheap); RmPlanCells3D (213-226) a 6th field, material.
- `Gather.dm`: RmLaidTidy at the end of RemasterColumnSettle (116); RemasterRampTick (729): no stone at :777 when block
  h-1 is laid.
- `Yield.dm` (staged RmStoneOut): reads `rm_laid_gone` as above; the laid branch switches on the letter.
- `Mountains.dm` RemasterCaveIn (169) and `Chains/Bump.dm` the 2006 cave-in loop (~297): skip any tile with a laid bit
  (replaces the staged `CF.remaster_laid = 0` line; review point 4).
- Page `art/hud/src/045-script.js`:
  - PM gets `mat`, and marks become {born,b,m};
  - apply() :52, and undo() :56 must copy `m`;
  - queue() :58-60 sends one planadd for each material, splits at 600 and keeps the colour in PM.sent;
  - card() :98-104 shows the two "needed" rows;
  - pmDraw :168-170 picks the colour.
  - Build with `python3 art/hud/hud.py build`, never by hand-editing remastered.html.

### Proof (arena first)
- Server: extend `tests/plan_build_test.dm` (PbRun, through `tools/check_arena.py` under runlock, speed 4):
  - **PbWood**: a wood plan of 12 blocks. Logs are fetched from a store and laid, the letters read `ww`, the key is the
    planner's, and stone stays untouched.
  - **PbDigBack**: dig out 6 laid stone and 6 laid wood blocks, two each by click, by Dig down and by a plan dig. That
    gives exactly 6 stone and 6 logs. 40 natural blocks give 2.7 +-0.3 each.
  - **PbCarve**: carve a laid wood block into a ramp, then dig it: 0 from the carving, 1 log from the dig.
  - **PbTidy**: a golem break (RmGolemBreakRock) on a 3-high laid column: bits, letters and the key are clear after, and
    the column is gone from RmLaidMask.
  - **PbCaveIn**: a forced RemasterCaveIn next to an opened laid column: the laid tile is not refilled.
  - **PbSaveMat**: save the world, reload it: letters, laid bits and key are the same. A record without the new vars
    loads as before.
  - **PbOldRow**: a plan row with no `mat` lays stone.
- Page: copy `tools/plan_mode/headless_plan.py` (the real page in headless Chrome). Queue stone and wood marks; the
  sends are `prio|cells|build|stone` and `prio|cells|build|wood`, and the card rows are right. A 700-block queue goes
  as two plans.
- Re-run: plan, planbuild, planaccess, buildings, lodge Elf/Orc, breaking, gather_zone, golem_check, the gate
  (compile+jscheck+hudjoin+combat), and `hud.py status`.

**Size:** M. Server ~220 lines, page ~60.

---------------------------------------------------------------------------------------------------------------------

## Step 1b (L2). Built blocks are walls, not a quarry

Today a laid column is a "Mountain" tile with IsWall 0 and CanDigAt 1. So the owner's own villagers dig their own
block walls:
- a stone zone (with the staged change it digs three blocks a tile, top block first);
- the miner job, Board and Delivery orders;
- away workers.

This is the first player-visible bug the rework would show. It can land right after the mountain-stone fix, carrying
its own copy of RmLaidMask if L1 is not in yet.

| Reads "built wall" today | Change |
|---|---|
| Jobs.dm:166,174 (RmJzRests/RmJzWorkable), Board.dm:207, Delivery.dm:169, Away.dm:331 skip only `IsWall` | Also skip any column with RmLaidMask != 0, the natural base under it included. Automatic digging never takes a built block. Only a Plan dig or a direct order by the builder's realm does (step 4) |
| Progress.dm:94-95 counts "wall tiles" for Village (30) and Kingdom (120) and the "wall" milestone | Also count a tile with **2 or more blocks in RmLaidMask** (a wall-high column; a one-block kerb doesn't count) |
| Buildings.dm:1124-1140 RemasterWallHoldTick (an underground wall holds the roof like a pillar) | Also accept a laid column |
| Explore.dm:160 minimap colour | A laid column shows like a built wall |

**Save impact:** none. **Proof:** `tests/gather_zone_test.dm`, a new entry: a stone zone drawn over a 2-high laid
wall and a natural outcrop. The outcrop is dug and the wall is left whole. Similar entries for a miner job,
`tests/away_test.dm` and `tests/board_test.dm`. `tests/progress_test.dm`: 30 laid wall tiles meet the Village wall
need. Re-run: buildings, food, obey, gather_zone. **Size:** S, ~40 lines.

---------------------------------------------------------------------------------------------------------------------

## Step 2 (L3). The built look: masonry and timber, mountains stay rock

### Server (small)
`View3D.dm:186-197` (Remaster3DTerrain): a tile with any laid block also sends `lay` (RmLaidMask) and `mat` (the
letters). Both go into the kind AND into its dedupe key at :193. If they were left out of the key, two columns of the
same height but different materials would share one kind and draw wrong. Natural columns send neither, so mountains
keep their few kinds. The engine's chunk counters move on any turf var write (Native.dm:25-29), so a changed letter
resends its chunk by itself. `remaster_laid_by` is never sent.

### Page
Inside the rock-stack branch (020:419 -> 021:25-48), a block that is laid is dressed:
- **Stone `s`:** exact seams, with no wander and no rounded corners (v3stackPt 021:22-24); flat faces with no bulge
  (021:36-37); a flat top whose middle point is kept, because unit feet read it (022:136). Masonry courses come from
  the cut-stone texture the old walls use (r3t-ground-stone.png, alpha 0.99, 018:64). Palette ~(0.70,0.66,0.57), the
  arena's. Course lines run on across tiles, so a wall reads as one wall, not a row of cubes (owner: no cubes).
- **Wood `w`:** horizontal log rods (MD.rod, like the old timber rampart 020:314-325), palette ~(0.50,0.34,0.20).
- **Natural `.`:** unchanged faceted rock. A wall built on a mountain keeps its natural base and gets a dressed top.
- **Own units stay in sight behind built walls** (owner: own units never hidden). The rock fade (v3rockTag, alpha 0.94,
  023:274) and the masonry tag (0.99) fight over one alpha value. Plan: a new "masonry + fade" alpha band, with a
  shader edit at 018:57 and :64. Check every alpha band in use before taking one (0.976-0.984 looks free). The
  view3d-batch1 silhouettes must still show.
- Effects (020:617-630): a block laid over open ground plays a dust ring, not the cave-in rockfall it plays today
  (020:623). Digging out a wood block bursts wood chips.
- Minimap colours (031:398): stone like a built wall (#9a8f7a), wood brown.

**Save impact:** none (sent data only). **Proof:** a new `tools/check_shapes_page.py`, a copy of
`tools/plan_mode/headless_plan.py`. It feeds the real page a made-up terrain: stone, wood, natural and mixed columns
side by side. It checks:
- the kinds keep `lay`/`mat`;
- adding one block rebuilds only its chunk; an unchanged terrain rebuilds nothing;
- an own unit behind a 3-high stone wall still fades or shows its silhouette;
- no script errors;
- stills: masonry, timber, natural, mixed.

Also measure the kinds and chunk JSON size on a 300-block build. Re-run delta3d, delta3d_page,
`tools/check_rock_fade.py`, `tools/check_wallwalks.py` (old walls drawn as before) and `hud.py status`. No WebKit
stills; one real-window look at the end. **Size:** M. Page ~250 lines, server ~20.

---------------------------------------------------------------------------------------------------------------------

## Step 3 (L4-L6). Shapes recognised from the blocks

### The rules (the arena's, ported as they are)
| Shape | Found when | Drawn |
|---|---|---|
| Barrier | a column with **2 or more laid blocks** in a run (mined holes break the run); natural rock is never a barrier | - |
| Wall | barriers joined side by side (4-way), 3+ tiles, or any length that meets a tower or gateway | stone: merlons on the top's outer edges, 2 per edge, 0.2 x 0.34 x 0.3, set 0.39 in from the tile middle; wood: palisade stakes, 3 per edge |
| Outer edge | faces open ground that reaches outside (a flood over the page's window, gateways counted shut). A wall that encloses nothing faces away from the nearest claim banner (V3.claims) | - |
| House | wall touching an enclosure of 4 to 40 tiles (the server's hut rule, WallWalks.dm:28-29 REMASTER_HUT_MAX/MIN) | no battlements; the gap is a doorway |
| Platform | more than 25% of its tiles are interior | flat, nothing added |
| Round tower | a 3x3 ring of barriers, middle hollow or filled, with no full row of barriers beside it | a drum of radius ~1.5 up to the top block, 14 merlons or stakes on the crown (v3tower 027:338 given a height and a wood look). Its 9 tiles keep their stacks for picking and standing but draw nothing; in Plan mode the real blocks come back |
| Gateway | 1-3 open tiles in a line between barriers, with the wall going on past both ends and open ground on both sides; side-by-side runs (a thick wall) are one gateway | a lintel 0.42 thick at the wall top, posts, and open gate leaves (0.08 thick). No leaves when a door, portcullis or drawbridge stands in the gap |

All of it is worked out once each time the terrain changes, behind the existing terrain key (027:507). It is skipped
completely when no kind has `mat`. It is never worked out per frame. A tile's shape tag goes into the chunk signature
(020:36-44), so closing the last gap of a yard rebuilds every wall chunk whose battlements change, even 30 tiles away.
Block houses: v3roofs (020:546-612) already roofs small rooms. It must put the roof at the wall top (today a fixed
2.36), use thatch when the walls are wood, and use the same 4-40 rule as the recognition. The arena's live-only parts
(the Recognised card, floating tags, gold flashes) are not ported. A new shape gets at most one toast.

### What is page-only and what the server must know
| | Page | Server |
|---|---|---|
| Wall, tower, gateway, house, battlements, drum, lintel, leaves | all of it, drawn from `lay`/`mat` | nothing. No shape is saved; the shape is the blocks |
| Standing on a wall top | the flat top (step 2) | already works: units stand on block tops on the Sky layer; same height is a free walk along the wall; down 1 is a hop |
| Getting up a wall | - | already works: up 1 needs a carved ramp (a laid block carved with the existing Carve; it keeps its material, the carving drops nothing), or climbing gear; plan workers cut their own steps (Plans.dm:706-711) |
| Room on a wall top | - | one unit to a tile (friends pass through but never rest on one tile); no second rank |
| High ground | - | already works (Surround.dm): a unit a block or more above its foe gets +5 to land in melee and +1 tile of bow reach, built or natural rock alike |
| Wall top vs ground below | - | different layers never fight (Attack.dm RemasterHostile), the same as old wall walks. Wall and cliff archers are the parked plan |
| Gate shut | leaves are decoration | the gap is open ground. A Place door, portcullis (Gates.dm:128-142, plain density jambs) or drawbridge closes it. Rooms.dm counts a room only once a door stands in the gap |
| Crossing over a gateway | lintel only | not possible: nothing over air (not approved) |
| Rank and siege rules | - | use RmLaidMask, never shapes (steps 1b, 4) |

### Proof
`tools/check_shapes_page.py`, fed the arena's own scene as terrain. It must give the arena's numbers:
- 5 wall sections of 25 tiles round the yard, all with battlements on the outside;
- 4 round towers;
- one gateway 3 wide;
- one timber house with a 1-tile doorway and no battlements;
- after one gap is closed, the right chunks rebuilt; nothing rebuilt on an unchanged terrain;
- recognition time on a terrain change, and 0 ms with no laid blocks;
- stills to match `shots/yard.png`, `house.png`, `gateway.png`.

Server: a new entry in `plan_build_test.dm`, **PbWallTop**. A guard walks up a carved laid block onto a 2-high laid
wall and along its top, with the real height rules. Re-run check_wallwalks (old walls), check_rock_fade,
headless_plan, delta3d_page.

**Size:** L in all, page only. 3a walls + roofs ~250 lines, 3b towers ~120, 3c gateways ~100.

---------------------------------------------------------------------------------------------------------------------

## Step 4 (L7). Built walls only fall to sieges and blows

### Who may take a built block
The **owner** of a column is the realm of `remaster_laid_by` (L1). For blocks laid before L1 landed (laid bit, no key)
it is the realm whose claim covers the tile (RemasterClaimAt, Claims.dm:32). With neither, nobody owns it and it is not
held (only blocks laid in the short time between the mountain-stone landing and L1, on unclaimed land).

"The owner's realm" is RemasterAlliedKeys(owner, digger) (Realms.dm:22-24): the same root key, so the ruler, members and
vassals. The game has no treaty allies, so nobody outside the realm counts (review point 6; question 6).

| Who | Pick, Mine order, Dig down, roof blow, Carve ramp, Plan dig or way-up | Zone, miner, Board, Delivery, away workers |
|---|---|---|
| The owner's realm | yes; gives back 1 of its material (carving: nothing) | never (step 1b) |
| Anyone else, at war or not, claimed land or not | **no**: "Built walls fall only to siege engines." | never |

**What is held** (`RmBuiltHeld(Player/P, turf/T, k)`, true = refuse): the column has a laid block in RmLaidMask, it has
an owner, P is not of the owner's realm (a null P, an NPC, is never of it), and block k is laid **or lies below the
column's top laid block** (the footing; review point 4). Natural rock with no laid block above it is unchanged: at war an
enemy may still dig your ground and the mountains beside a wall, so going round a wall stays a real choice, but nobody
digs out from under it (question 7).

The rule is checked where the block is actually taken, not only at the click, because plans, zones and queued orders
never pass through the click check (RemasterMayWork, Claims.dm:52-57, is called only on click and blueprint paths).
RmBuiltHeld is called in:
- the click: Orders.dm:247 (the message), and RemasterCarveRamp Gather.dm:709;
- the ticks, before the first blow: `Gather.dm` RemasterBlockTick 247, RemasterDigDownTick 326, RemasterTopBlow 370
  (k = the top block), RemasterRampTick 729 (k = h-1); a held block finishes the order with the message;
- `Mountains.dm` RemasterRoofBlow 139;
- `Chains/Bump.dm` old two-outside path ~255 (k = 0 or 1);
- `Plans.dm` RmPlanStep dig (a held cell is dropped from the plan with a line on the row) and RmPlanAccess 624 (a held
  block is never chosen as a dig or ramp step on the way up, so plan workers never queue a refused order).

### How breaking a block works, exactly
1. **Targets.** Rams and catapults may now target a column whose top block is laid (Siege.dm:80-81 RemasterSiegeWall,
   RemasterSiegeSpot, RemasterSiegeFind), as well as old walls and doors. Who may siege is unchanged
   (RemasterSiegeMay 95-103):
   - own or allied land: refused;
   - at war: allowed;
   - at peace: "declare war first";
   - unclaimed land: allowed.
   For a block column the "own" test also refuses the owner's realm by `remaster_laid_by` (no one sieges their own wall).
2. **Hit points per block:** stone 1300, wood 450. A column's bar (rm_wall_max) is the sum of its laid blocks.
3. **Damage, as today:**
   - a ram does 300 a blow every 2.5 s, +100 for each extra crew member up to +200 (Siege.dm:208);
   - a catapult boulder does 500 (:263);
   - ballistas only hit units.
4. **A block falls** each time a block's worth of damage is done:
   - its top laid block comes off (RemasterTakeTopBlock); the tidy (L1) clears its bit and letter;
   - units standing on it come down to the new top (RemasterFeetCheck, Gather.dm:542);
   - the tile is dirty-marked for the save (TakeTopBlock does it);
   - 60% of the time 1 of its material drops (read from `rm_laid_gone`/`rm_mat_gone`; an old wall's breach drops stone
     60% of the time); never more than 1;
   - the 3D page shows a burst in the block's colour.
5. **A breach** is a column with no laid blocks left. A natural base stays as rock. The realm gets the old breach
   notice once per column (copied from Siege.dm:348-350). Do NOT call RemasterSiegeBreak (327): it resets the whole
   tile and would wipe a natural base.
6. **Golem slams** already break mountain columns, 16 top blocks at once (Golems.dm:301-306). Laid blocks go the same
   way, and the tidy clears them.
7. **Nothing else breaks a built block.** Units' melee blows never did, and still don't. Fire doesn't burn wood blocks
   in this step (question 8b).
8. **Damage below one block is not saved** (a tmp var). After a reload the top block is whole again. Old walls keep
   their saved HP as now.

Times with one ram crew member (to check in the arena):

| Column | Old wall today | Block wall |
|---|---|---|
| stone, 2 high | 3000+skill: 10-11 blows, ~26 s | 2600: 9 blows, ~22 s |
| stone, 3 high | same old wall | 3900: 13 blows, ~32 s |
| wood, 2 high | 1000: 4 blows, ~10 s | 900: 3 blows, ~7.5 s |
| wood, 3 high | same | 1350: 5 blows, ~12.5 s |
| stone block vs boulders | - | 3 boulders a block |

Page: the siege bar sits on the column's top, not at one storey (023:604). The breach burst for a laid block is new
(020:628 has only the old-wall burst).

Taken out of L7 (review point 7): the RemasterMayWork check on plans. RmPlanLeft (Plans.dm:83) drops every cell that
fails RmPlanGroundOK, so putting a claim check there would cut saved rows short. If question 8 says yes, it goes in
RmPlanAdd only, for new rows.

**Save impact:** none beyond step 1. **Proof:** a new `tests/siege_blocks_test.dm`, two realms in the obey arena:
- at war: an enemy's Mine order and Carve on a laid column are refused with the message;
- an enemy's queued pick, Dig down, Carve ramp, roof blow and Plan dig all leave it, and the plan's way-up never routes
  through it; the enemy digs the natural rock beside it; the natural block under it (the footing) is refused;
- at peace and on unclaimed land (no banner anywhere): the same refusals, by `remaster_laid_by`;
- a ram on a 3-high stone column: 13 blows, blocks off top first, a defender standing on top comes down, and the
  drops counted (60% of 3 over 20 runs);
- a 3-high wood column takes 5 blows; a catapult takes 3 boulders a stone block;
- a golem break clears the bits, letters and key;
- the owner's own Plan dig takes its own wall and gets back 1 a block; a vassal of the owner's realm may dig it; a
  player of another realm may not;
- a block laid before L1 (bit, no key) inside a claim is held by the claim; on unclaimed land it is not.

Re-run siege_test, siege_save_test, war_test, claims_test, golem_check, gates_test, breaking. **Size:** M. Server ~220
lines, page ~20.

---------------------------------------------------------------------------------------------------------------------

## Step 5 (L8). The first house or lodge, placed by the game

### Today
Nothing places a house, a lodge, a stockpile or a banner for a new village. The player opens the Build tab, picks a
building and clicks. Founders start on "manual" (Settlement.dm:10). The Builders row wants 0 (Jobs.dm:86-89). There is
no stockpile and no carpentry until the player makes them. A plan row short of stone only says "waiting for stone"
(Plans.dm:459-466); it posts nothing. Three facts set what a preset can do on its own:
- with no stockpile, a "for building" order can't count what is gathered (Board.dm:37-39 RemasterStockCount returns 0),
  and a plan fetches only what lies within 12 tiles;
- with no carpentry near the stockpile, no bed, table, chair or door order is posted (Jobs.dm RmJzFurnitureRecipe
  returns null; the site just says to build one);
- with (a)+(b) only, 3-villager rounds stall on "Mine stone for building" when the rock is far from the stockpile
  (`first-house/fix/README.md`); with fix-order-area every round finished (3 Dwarves 10.0 / 9.6 / 13.1 min, 3 Humans
  14.2 / 15.2 / 14.0).

### Depends on
L1, L2, L7 (so the house is never a neighbour's quarry), the first-house fix (a)+(b), and **fix-order-area**
(question 1). If the owner says no to fix-order-area, L8 does not land as written: 3-founder Dwarf and Human villages
are expected to stall exactly as the 10-26 rounds did. The fallback then is for the spot search to require the race's
material (rock for stone races, trees for wood races) within 6 tiles of the door, and the 3-founder rounds decide.

### When
In `game/Code/Restart.dm`, after the story card's Begin and before `Restart = 0` (line 185). By then the safe-start move
has happened and the founders are spread out. Skipped for:
- migrants (Restart.dm:107-109): they join a realm that already has buildings;
- rare races with lairs: Spider, Dragon, Devourer, Svartalfar, Sand King, Illithid;
- races whose question 2 answer is "no preset yet" (Kobold, Ratman by default);
- test runs, unless a test asks for it.

### Where
- Anchor: the first founder's tile.
- Search rings 2 to 12 tiles out, all four turns (remaster_build_rot), for a footprint plus a 1-tile margin:
  - every wall cell must pass RmPlanGroundOK; rock counts as wall already standing, as in RemasterPlanCells;
  - every inside cell must be open ground: no tree, water, lava or solid thing;
  - prefer the door facing the founders, then the nearest spot.
- None within 12: try 24.
- **Trees in the way (forest starts; SafeStart picks spots with trees within 15, SafeStart.dm:89-120):** still none,
  take the spot within 12 with the fewest trees in footprint and margin, at most 6. The preset makes a wood zone row
  over just those trees (the job board's own zone row, want 1, High), and the plan row and site wait as a pending
  preset. Every 30 s it looks again; when the footprint is clear it makes them. The logs lie or go to the store, and a
  wood house's plan fetches them (within 12).
- Still nothing (water, swamp, chasm all round): one notice, "No open ground near for the timber house: move your
  people to open ground and it will be planned where they stop." The pending preset retries when the first founder has
  moved 10+ tiles and stood 30 s, for 20 minutes, then gives up with a line in the Village Log. This is the only case
  that needs a player's move.
- Founders standing on a wall cell are sent inside first.

### What it makes: always (under the approval)
Exactly the race's old layout from Buildings.dm:43-128, redone as blocks.
1. **One Plan build row**, named after the building. Every `#` tile gets blocks k = 0..H-1 (H = 2, question 3). The
   material comes from the race. The door tile is left open. Normal priority. The row is marked `preset`.
2. **One furnish site** made with RemasterPlanCells' piece part: the floor, beds, table, chair, workshops (forge,
   kitchen, campfire, bone crafting) and traps. No walls and no door. It is NOT made to wait for the ring: the staged
   fix (b) counts a waiting site as workable, so it would hold its builders. The furniture goes in while the walls rise;
   a room counts only with walls and a door.
3. **The door**: when the plan row finishes, the game adds the Gate blueprint to the site. It then orders itself from
   the carpentry, as doors do today.
4. **Staffing:** the founders go on the Any role, as RmPlanAdd does for a selected unit (Plans.dm:65-69); the Builders
   row wants 1.
5. **Supply:** a plan row short of its material posts the same "Chop wood for building" / "Mine stone for building"
   board order a site posts (Blueprints.dm:569-582: High, min(20, need), one open order a kind). Fix (a) lets that High
   order borrow a Normal worker after 60 s; fix-order-area sends its worker to the rock or trees.
6. **A guide line** on the Village Log and the first goals: "Your timber house is planned. Set a stockpile and place a
   carpentry so its beds and door can be made." (only while either is missing).

### What it adds only if the owner says yes (question 4)
- the stockpile spot (remaster_stock_x/y, Settlement.dm:32) on open ground outside the door, as the Gather bar's
  "Stockpile here" does;
- a carpentry site by the door (RemasterPlaceWorkshop, as play_round.dm:278);
- the Claim banner on the floor, last, as `tests/lodge_test.dm` plans it.
With all three, the house needs no click at all. Without them, the player does what the first goals already ask (camp,
stockpile, carpentry: 011-onboarding-playtest.js:41), and the preset does the house.

### Per race (walls 2 high; 3 high in brackets)
| Race | Layout | Blocks | Walls | Material | Inside | Furniture and pieces |
|---|---|---|---|---|---|---|
| Human | Timber house 7x5 | 38 (57) | 19 tiles | wood | 15 tiles | 2 beds, table, chair, kitchen, wooden floor, door |
| Dwarf | Forge-hall 9x6 | 50 (75) | 25 | stone | 28 | 2 beds, table, chair, forge, stone floor, door |
| Elf | Elven lodge 9x8 (round) | 58 (87) | 29 | wood | 30 | 2 beds, table, wooden floor, door |
| Orc | War lodge 11x7 | 62 (93) | 31 | wood | **45** (question 5) | 8 beds, campfire, no floor, door |
| Goblin | Warren 9x7 | 50 (75) | 25 | stone | 23 | 2 beds, bone crafting, bone floor, 2 spike traps, door |
| Lizardman, Frogman | Tribal hut 7x6 (round) | 42 (63) | 21 | wood | 16 | 2 beds, campfire, tribal floor, door |
| Kobold | Den 7x6 | 38 (57) | 19 | bone today (question 2) | 11 | 2 beds, bone floor, 2 ribcage traps, door |
| Ratman | Warren 9x6 | 58 (87) | 29 | bone today (question 2) | 20 | 4 beds, bone floor, door |

The cost doubles: the old house cost 1 piece a wall tile, and now each tile is 2 blocks. Natural mining gives ~2.7 stone
a block, so stone supply is fine. The risk is hands: 3 founders (5 for Kobolds and Ratmen) and two systems to staff,
the plan row and the site. The fresh-village rounds of 10-26 (devlog/2026-10-26/polish-loops.md:99-125) stalled on
exactly that, which is why fix-order-area is a dependency.

### The page (in this landing)
- Queued blocks are drawn outside Plan mode too. pmDraw (045:151-178) returns early at :155 today, so a preset would be
  invisible. They are cached by the signature it already computes (:154).
- The Construction view (016) gets a **Block plans** section that lists model.plans, reusing the Plan card's row
  markup (045:102-103). A preset's progress then shows without opening Plan mode.

### How it meets the first-house fixes
- Fix (a): High rows may take from Normal after 60 s. This moves a founder from the wall row onto "Chop wood for
  building", "Mine stone for building" or the carpentry's bed order. It never takes a builder at work, and never a
  woodcutter for a wood order.
- Fix (b): the Builders row lets villagers go while no site can be worked. For (b) to work the furnish site must not use
  a RemasterBuildWait reason; hence "no wait on the ring" above.
- fix-order-area: the "for building" order's worker goes to the village's own zone or the nearest rock/trees instead of
  standing at the stockpile.
- All three act only on rows that exist; the preset makes its rows itself (the plan row, Builders at 1, the material
  orders). None of the three is changed by L8.

**Save impact:** none in the turf format. The plan row (with its `preset` mark), the pending preset and the site are
player data, already saved. **Proof:**
- **Like for like (the main pass):** the 10-26 round script `reports/polish-night-1026/loops/play_round.dm` with its
  step 7 (the house placed from the Build tab, :280-283) taken out, so the preset makes the house; steps 1-6 (stockpile,
  everyone on the job board, wood/stone/fish zones, the carpentry) stay as the player's own actions. Rounds LpHuman3,
  LpDwarf, LpHuman, LpDwarf8, LpOrc, LpElf, 3 runs each, speed 4. Pass: every run has the ring laid, the furniture in,
  the door hung and the room recognised by Rooms.dm within 30 minutes, with what waited on what logged. Compare each
  round's finish minute with the README's "fix + order-area" column.
- **Through the real start path** (a new `tests/first_house_preset_test.dm`, driven like `tests/safe_start_test.dm`),
  one entry per preset race: within 5 s of Begin the plan row, the furnish site, founders on Any and Builders at 1
  exist, the door tile is open, and every wall cell is buildable.
- **Spot search:** 50 safe starts per terrain kind (open grass, forest, mountain foot, desert) on the test map. Pass: a
  spot found directly or by the felling fallback in at least 48 of 50 for each kind; every miss listed with its
  coordinates; the felling fallback finishes its footprint within 5 minutes in the forest starts.
- **Only if question 4 is yes:** the same rounds with steps 1 and 6 also taken out (the preset sets the stockpile and the
  carpentry). Same 30-minute pass.
- Re-run lodge Elf/Orc, buildings, rooms_test, progress_test, safe_start_test, plan_build.

**Size:** L. Server ~350 lines, page ~60.

---------------------------------------------------------------------------------------------------------------------

## Step 6 (L9). The Build tab becomes Place

Lands only after L8 is proven for a race and questions 2 and 9 are answered. If nobody answers, the "kept" defaults
below stand.

### Still offered in Place
- furniture (bed, table, chair and the rest);
- doors: Gate (a door in a gap), portcullis, drawbridge;
- workshops (banner, stall, food pot and stall, clinic, surgery, tavern, altar, graveyard, carpentry...);
- rune devices;
- traps;
- rails, cart stop, mine cart;
- lifts;
- bridges (blocks can't go on water, Plans.dm:259);
- until questions 2 and 9 say otherwise: floors, roads, stairs between levels, beam/pillar/channel, webs, hoard, power,
  Wall stairs and Ramp up the wall (old walls need them), the 8 halls, the 4 lairs, the Kobold den and Rat warren, and
  the bone, silk, flesh and secret walls.

### No longer offered (a `legacy` flag, never deleted), and only for the races that have a preset
For Human, Dwarf, Elf, Orc, Goblin, Lizardman and Frogman (the races whose presets passed L8):
- Fortress wall, Tower, Wooden wall, Stone wall (with its obsidian variant), Tribal wall, Elf wall;
- their own building: Timber house, Forge-hall, Elven lodge, War lodge, Warren, Tribal hut.
Every other race keeps its walls and buildings exactly as now (Stone wall stays for Illithid crystal and sand workers,
Construction.dm:28). The filter is per race, in RemasterBuildCatalogData (Construction.dm:733-748, beside
RemasterBuildRaceOK 149-199), and the page's BUILD_CATS (016:2). Entries stay in RemasterBuildCatalog because old saves
hold blueprints and sites in those modes (Blueprints.dm:18-19, RemasterSitesSync 232). Lookups such as
RemasterBuildEntryForMode, RemasterBuildEligible and RemasterBuildMaterial would go wrong if the entries were deleted.
Tests use the catalog ids too.

### Old saves keep working
Nothing in these files changes for old pieces:
- walls with their walks and stairs (WallWalks.dm);
- towers and gates;
- buildings, halls and lairs;
- rooms;
- siege breaches of old walls (RemasterSiegeBreak);
- the 'built' 3D drawing (020:252-394);
- sites half-built when the save was made (RemasterSiteBuild and RemasterBuildNow keep building them).

### Names
- The tab is titled **Place** (012:210 PANEL_HEAD, 009-page.html:138). The tab id stays `build` (HUD.dm:881).
- On the Build bar (043:14-19), "Build list" becomes "Place list" and "Set blocks" moves first.
- Every player-visible "Build tab" changes in the same landing, so text and tab agree:
  - server: Blueprints.dm:98 and 158, HUD.dm:1113, Doctor.dm:433;
  - page: 009:173, 273, 302, 310; 011:41 ("Place > Workshops"); 037:74.

**Save impact:** none. **Proof:** a page check per race: a Human sees no Fortress wall, Stone wall or Timber house; a
Kobold still sees its bone wall and den; nothing says "Build tab". Re-run buildings_test, halls_test, lair_test,
blueprints_test, construction_test, wallwalk_test, siege_save_test, save_roundtrip_test and real_save_test. Then load a
save from before the change, with old walls and a half-built house: the walls keep their walks and stairs and the house
finishes (check_app "saves unchanged"). **Size:** S-M. Server ~70 lines, page ~80, mostly words.

---------------------------------------------------------------------------------------------------------------------

## The arena scene (what is built first, before any game window)
The arena's two demos, rebuilt in the real game's obey arena (check_arena.py) and fed to the real page headless:
- **Walled yard**, 13x13, stone, 2 high:
  - 3-high hollow round towers on the four corners (3x3 rings);
  - a 3-wide gateway in the south wall;
  - one laid block inside the north wall, carved into a ramp, as the way up.
- **Timber house**, 5x5, wood, 2 high, with a 1-tile doorway: 30 blocks.

Villagers on the Any role, with a store holding stone and logs, lay both from plans with no clicks. A guard walks up
the ramp onto the wall top. Then one block of each material is dug back (1 stone, 1 log; the carving gave nothing), and
the world is saved and reloaded with the letters and the builder's key. The page must recognise:
- 5 wall sections of 25 tiles round the yard, with battlements on the outside only;
- 4 round towers;
- one 3-wide gateway;
- one timber house with a doorway and no battlements.

Those are the arena's numbers (`shots/results.json`). The same scene then carries the step 4 entries: a second realm,
at war and at peace, with picks, carving and plan digs refused on the walls and their footing, the natural rock beside
them dug, a ram, a catapult and a golem on the wall, and the owner dismantling its own.

## Conflicts with work in flight
- **mountain-stone fix** (staged, lands first). It edits the same procs: Plans.dm RmPlanLayTick/RmPlanPutBlock,
  Gather.dm RemasterBlockTick/RemasterTopBlow, Mountains.dm RemasterRoofBlow/RemasterCaveIn, Chains/Bump.dm, Yield.dm
  RmStoneOut, and Jobs.dm's zone face order. This work builds on its `remaster_laid`. Write against its patch.json
  text and rebase after it lands. Two of its lines change in L1: RmStoneOut also reads `rm_laid_gone`, and the cave-in's
  `CF.remaster_laid = 0` becomes "skip a tile with a laid bit". Its "zones dig three blocks top-first" makes step 1b
  urgent.
- **first-house fix (a)+(b)** (staged, Jobs.dm allocator only, after the regrow spike fix). The presets lean on both
  fixes and change neither. (b) counts RemasterBuildWait reasons as workable, so the furnish site must not wait on the
  ring (step 5).
- **first-house fix-order-area** (staged, Board.dm, not approved). L8 depends on it (question 1).
- **regrow spike fix** (WalkLoop.dm): no overlap.
- **Navigation plan** (planning/NAVIGATION_PLAN_2026-10-27.md, plan only). If its area map is built, laying or removing
  a block is "a turf var write that walking reads". A wall closing a valley is its costly split case. No code to clash
  with yet; tell that session that block walls change heights block by block.
- **Combat**: high ground (Surround.dm) is landed and reads heights, so block walls get it for free. Wall and cliff
  archers is parked. The combat-rules session is landing now; Siege.dm was last touched by village-polish (landed).
  Write L7 against the live Siege.dm.
- **HUD page**: edit art/hud/src only, then build with hud.py. Builds refuse drift.
  - 043, 045, 016, 009 and 012 are shared with the bars and HUD work.
  - The hud-rework CSS block sits at the end of 041: add nothing inside it.
  - view3d-batch1 (rock fade, silhouettes and picking for own units on rock) lives in 023/027/031. The dressed-stone
    look must keep it.
- **Landing rules**: .dm edits stay ASCII and are Latin-1 safe (encode, temp file, replace). Land through the land lock
  (land_polish.py, .land.lock). Use one batched build. Behaviour checks run at speed 4, time checks at speed 1. One big
  run at a time. Dropped work goes to the Trash.

## Questions the approval did not settle
1. **fix-order-area** (`reports/polish-night-1026/first-house/fix-order-area/`, Board.dm, 2 edits): may it land? With
   only (a)+(b), the 3-villager rounds stalled (3 Dwarves never started, 3 Humans stuck at 36/41); with it they built in
   10-15 minutes. The first-house presets depend on it. Recommended: yes.
2. **Races with no stone or wood wall today**:
   - Kobold and Ratman build only bone walls; Spiders silk; Devourers flesh.
   - What is the Kobold den's and Rat warren's first house? Stone blocks, the old bone layout placed by the game as
     Place pieces, or no preset until bone blocks exist (the default)?
   - Do the bone, silk, flesh and secret walls stay offered in Place until their block materials exist? Recommended and
     default: yes.
3. **House and lodge wall height for the presets**: 2 blocks (recommended: 38-62 blocks a house) or 3 (57-93)?
4. **What the preset may add so it really needs no clicks.** It always sets the founders to Any and Builders to 1 and
   posts its own material orders. May it also set the stockpile outside the door, place a carpentry there (without them
   no material order can count and no bed, table or door can be made), and the Claim banner on the floor (it claims
   land; one banner a rank)? Without them, the player sets the stockpile and carpentry as the first goals already ask.
5. **The Orc war lodge has 45 tiles inside**, more than the 40-tile house rule. As blocks it would read as a walled yard
   (battlements, no roof). Raise the block-house limit to 48, or make the lodge one row shorter (9x4 inside, still
   8 beds and the fire)?
6. **Who owns a built block.** Planned: the realm of the player who laid it, saved on the tile (`remaster_laid_by`, one
   more saved text var beside the approved material), so a wall is protected on unclaimed land too; "the realm" = the
   same root key (ruler, members, vassals), as the rest of the game counts allies. OK? Or protect only inside a claim
   (no extra var, but a new village's first house would be pickable by anyone until it has a banner)?
7. **Undermining**: planned, nobody but the owner's realm digs the natural blocks under a built wall (its footing),
   and cave-ins never refill a laid tile. Should enemies at war be allowed to dig under walls later?
8. a. **Plans in another realm's land at peace**: today a plan can lay or dig blocks inside a neighbour's claim
   (Plans.dm:251 tests only T.Owner). Close it for new plans (a check in RmPlanAdd only; saved rows untouched)?
   b. **Wood blocks and fire**: they don't burn in this step (recommended). Or burn like old wooden walls (a separate
   task for mixed columns)?
9. **Old Build tab items the approval didn't name**: floors, roads, stairs between levels, beam / pillar / channel,
   the "Mark for digging" marks (Plan Dig does that now), webs and hoard, power, the 8 halls, the 4 lairs, and Wall
   stairs / Ramp up the wall. Default until answered: all kept. Recommended: keep floors, roads, stairs,
   beam/pillar/channel, webs, power and lairs; drop the dig marks and the halls; keep Wall stairs listed only while the
   realm has old walls. Also: does the bar stay "Build" (it holds Set blocks) with the tab called Place?
10. **More presets**: wall line with a height, tower, room box with a door gap, later houses, and a Plan-mode ramp mark
    (the arena had one) were not approved. Plan mode's Line and Outline shapes with the level arrows already make walls,
    towers and boxes, and right-click Carve makes a ramp. Add one-click versions?
11. **Numbers to confirm**:
    - siege: stone 1300 and wood 450 HP a block; 60% chance of the block's material back; a breach = no laid blocks
      left; "blows" = rams, boulders and golem slams only, never units' melee;
    - a tile counts as a "wall tile" for Village and Kingdom at 2 or more laid blocks;
    - the spot search goes 12 tiles out, then 24; the felling fallback takes at most 6 trees.
