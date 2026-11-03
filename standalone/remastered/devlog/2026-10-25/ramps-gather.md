# ramps-gather, 2026-10-25

- Plan mode test arena (`tools/plan_mode/arena.html`, served by the `planarena` launch entry on port 8811): a standalone
  3D page, not the game. One level at a time (the level's blocks drawn as low slabs so floors show, its floors lit), a
  block cursor moved by the mouse on that level only or by WASD turned to the camera, R/F level, Space to mark, drag for
  Single/Line/Box/Outline, Dig/Build/Ramp/Erase, a plan card (blocks, stone out/needed, free miners and builders,
  priority, Queue it) and a task list (progress, pause, priority, remove). Miners dig, the builder builds and carves
  ramps, a selected unit does any; one block at a time, walking by the game's rules (up only by a ramp, down one).
- The map never follows the mouse cursor (the user asked); keyboard moves pan only near the screen's edge.
- Arena polish (the user: "polish it"): faceted rock blocks (four shapes, rounded corners, chipped edges) with sun
  shadows; the cursor glides, turns red where the tool can't act, and shows a ramp's rise as an arrow; a drag reads out
  its size and count ("Box 4 × 2 · 8 to dig"); Cmd/Ctrl+Z undoes marking; a ring over the block being worked fills as
  the work goes, chips fly when it comes out or goes in, and each unit has a name tag with what it's doing; a level
  ruler (dots where marks are, click to go there); hovering a task lights its blocks, clicking it flies the camera there;
  gilded-edge panels, drawn icons for the tools and shapes, a gold Queue it.
- Arena feel pass (the user picked "in the arena now"): the level slice animates (blocks rise and settle, entering and
  leaving Plan mode too); marks pop in, queued ones shimmer in a slow wave, finished blocks flash and a finished task
  lights up in a gold wave and turns its row green; the cursor springs to its block, glows, and shakes red when refused;
  jointed workers walk and swing a pick or hammer, cracks spread over the block as the ring fills, it breaks into
  tumbling chunks, built blocks rise into place, "+1 stone" / "-1 stone" float up and the counter bumps; the camera
  turn carries on, the wheel zooms toward the pointer, fly-to eases; drag across levels (R/F mid-drag), a Room shape
  (two high: walls with a door gap on your side, or a dug room), copy and paste of a plan (Cmd/Ctrl+C, V, T turns).
- Planning many levels (the user: "highlight blocks on each level or do a drag clear? will units figure it out?"):
  a Clear tool (5) marks everything from the level looked at up inside the shape (a hillside in one drag, leaving a floor
  at that level); the wheel or R/F mid-drag takes more levels and the ruler lights the range. Workers now dig top-down
  within reach, never dig a block someone stands on, never dig out under their own feet, and when nobody can reach a
  task they plan a way there themselves (cheapest route: walk, tunnel at their height, or cut a step: dig the room over
  the block ahead, carve it into a ramp, step up) and add those blocks to the task. Arena runs: a 3x3 clear from level 4
  up, out of reach: Edven tunnelled and cut steps, 20/20 done; with only the miners and builder on the ground, a clear
  from level 5 up: a staircase cut from the ground, 25/25 done in about 40 s of game time.
- Plan mode in the game, stage 1 (dig and clear): `game/Code/Remastered/Plans.dm` (new) makes a queued plan a job board
  row of kind "dig" (Jobs.dm hooks: the kind, its targets left, its step, Plans in the HUD model, a dig plan can be
  removed, the allocator passes over villagers with nothing of a plan in reach for a minute). A worker's step takes a
  block in its reach (the ground: the lowest three of a face; up on the mountain: Gather.dm's work spots), the higher
  first, never one someone stands on, and makes the Mine (or Mine roof) order a click makes. Selected units on Manual
  join a plan queued with them. View3D sends the queued blocks round the camera (D["plan"]); HUD command `planadd`.
- Page: `tools/plan_mode/pm_module.js`, patched in by `tools/plan_mode/patch_page.py` (before the last script): a Plan
  button in the quick dock, the bar (Dig, Clear, Erase; shapes; level), the plan card with the plans and their
  pause/priority/go to/remove, the key strip, the level cut (the cutaway disc at the level's slab height), the cursor on
  the level's plane, marks and queued blocks drawn. Game keys: arrows move the cursor, PageUp/PageDown the level, Esc.
- Checks: tests/plan_test.dm 5/5 (arena: a face dug by the board's villagers, out of reach waits and says so, from up
  on the mountain the top blocks but never the one stood on, a finished plan leaves the board, Manual selected join);
  tools/plan_mode/headless_plan.py 12/12 (the real page in headless Chrome). formations' headless_slots.py has two
  fails that are the same on the page from before Plan mode (a Company menu label, a Ctrl-click group select).
- 13:23 Real-window Plan run (real_mount.py --only plan, tag plan1): 12 pass, 1 fail. The dock button, Plan mode on
  the unit's level, a real drag marking three blocks and Queue it all worked, but the game's plan held 1 block, not 3:
  the cells went as "x,y,k;x,y,k" and a ";" splits the page's byond:// link into fields, so only the first arrived.
  Fixed: cells go as "x,y,k/x,y,k" (as formations do), the server takes "/" or ";". Arena 5/5, headless 12/12 again.
  The real-window recheck is not run yet.
- 13:37 Real-window recheck (tag plan2): 13/13. The plan held all 3 blocks ("Dig 1", 3 blocks, Done) and the selected villager dug all three by itself, block by block. Report: reports/mountain-work/real-mount-plan2.json.
- 13:55 PLAN MODE STAGE 3, BUILDING BLOCK BY BLOCK (arena first). Plan mode's new Build tool (key 2) marks blocks to lay
  where there are none: on open ground, or on a block or a mark under it, so a drag over several levels stacks a
  wall. They show as blue ghost blocks. Queue it sends a build plan (and a dig plan for any dig marks) to the job
  board, and the board's villagers do the rest: fetch stone from the stores, lay the lowest course first, one stone
  a block, never on anyone standing there. A block can go on open ground (the tile becomes rock and its top a place
  to stand), on a column's top (up to 8 high), into a hole in a face, or under a tunnel's ceiling. Dug out again,
  the ground under it comes back, and built rock holds no ore.
  Server: Plans.dm (build kind, RmPlanCanLay / RmPlanPutBlock, the Lay block order), hooks in Jobs.dm, Orders.dm,
  HUD.dm, Breaking.dm (heights of built columns, no veins) and Gather.dm (the ground back). Checks:
  tests/plan_build_test.dm 7/7, headless_plan.py 17/17 (screens reports/plan-mode/headless/4-, 5-).
  Not done yet: a real-window check; workers cutting ramps or steps to reach blocks higher than 3 (they say "nothing
  in reach" for now); naming the rooms built ("designate").
- 14:07 WORKED BLOCKS IN YELLOW (the user: "we should see a yellow highlight of what blocks are being worked on"). Every
  block one of your villagers is mining right now has a yellow outline on its rock faces, whoever gave the work: a
  click, a dig plan or the job board. It shows while the villager is at the block, and goes when the block comes out
  or they leave it. Where a selected unit's order already outlines that rock in the orders' gold, there's no yellow
  too. Server: each own unit's 3D record carries its block (Plans.dm RmWorkedBlock3D, View3D.dm "wk"). Page:
  pm_module.js pmWorked reuses the dig mark, built only when the things, the orders, the ground or the camera's turn
  change. world-look dropped their own version, so there's one system.
  Checks: arena plan_test 6/6 (the record names the mined block, only while at it); tools/plan_mode/worked_probe.py:
  still reports/plan-mode/worked/worked-60.png, shadow 0 differences in 5 phases, frame time with 200 workers on vs
  off unchanged within noise (WKWebView median 0-1 vs 0 ms, p95 1 vs 1; Chrome 0.5 vs 0.3-0.4 ms); world-look's
  dig_cache_check PASS, 0 differences. Restore point: restore-points/before-worked-blocks-20261025/.
- 14:53 WORKERS CUT THEIR OWN WAY UP (arena first; the user: "make workers carve their own ramps or steps to reach blocks
  higher than 3"). When none of a plan's blocks are in reach (more than three up from the ground, nobody up there),
  a worker finds the cheapest way from where it stands, by tile and height (the arena's planAccess, ported):
  - walk along, hop down a block, go up a ramp already there;
  - tunnel (dig the block ahead at its height);
  - cut a step (dig the space above the block ahead, carve that block into a ramp);
  - on a build plan, build a step (lay stone up to its height beside the work, carve the top into a ramp).
  That work goes on the plan as its own jobs, in order; one worker cuts the way while the others wait for it, then
  everyone works from up there. It never cuts another plan's blocks or a ramp.
  Fixes found on the way: a plan's order now gives up after 15 s with no way through (the game's walk to a work spot
  never gave up), and a worker sent up a way goes to the spot the way leads to (the mining spot pick could choose
  the unreachable top of its own column).
  Arena: tests/plan_access_test.dm 2/2 (a six-high face: 3 steps carved, its top three blocks dug; a five-high
  column on open ground: two built steps, all five laid).
  Not done: the ramp carve can take a few tries before the carver is on the right side; built steps stay as stairs.
- 15:11 Way up, regressions: the dig and build arenas caught three bugs, now fixed. (1) The route counted ground tiles
  as goals and sent workers "up" to blocks they could work from the ground. (2) A plan order hung on "No stairs
  nearby"; it now gives up and the plan finds another way. (3) A worker could be routed to the block under its own
  feet, which mining takes from on top. The route now skips blocks anyone stands on, and the dig test checks that no
  block ever comes out from under a standing unit. Arena: plan_test 6/6, plan_build_test 7/7, plan_access_test 2/2.
- 15:38 Real-window run plan3: 17/17 up to the way up, all of building included (Build tool, a drag of three on grass,
  ▲, a fourth stacked, Queue it; the villager fetched stone and laid all four). The way up got stuck. The user saw it:
  "wasnt able to build where it wanted to go". The worker carved a ramp into the tall column, then tried its next job
  (a block of the column behind, block 2) from the ground, where nothing touches that column, again and again.
  Fixed: each job on the way up carries the place on the way it is done from (on the ramp, at its height).
  The arena now has the real massif's case (six high in a three-high face, five behind): way-up test 3/3, dig 6/6,
  build 7/7. Real-window rerun (plan4) queued.
- 15:53 Real-window rerun plan4: 19/19 with real input. Dig plan in a corridor; Build (a drag of three on grass, ▲, a fourth stacked, all four laid with stone from the stockpile); the way up (the six-high face's top two marked on levels 4 and 5 from the ground: the worker carved its own ramps, climbed and dug both; the face now 4 high). No runtime errors. No stills: the window-recording helpers were missing from the scratchpad.
- 17:59 MOUNTAIN HEIGHTS step 0 (planning/MOUNTAIN_HEIGHTS.md, the user: "implement what is best"). Two parts:
  - Heights count the map's own rock (Breaking.dm RemasterRockAtStart). Digging a mountain open no longer changes
    its neighbours' heights after a restart, a bug until now.
  - A column keeps its height the first time it changes (RmKeepHeight -> remaster_built, saved). Later rule
    changes such as the sky peaks never move what was dug.
  Arena tests/mountain_heights_test.dm 5/5: neighbours steady through digging and a restart (the old count gave 3,
  now 4, as the map made it); a dug column keeps its height; a new save round-trips through a real savefile; an old
  save loads with every value the same; an unknown value is skipped.
  Gather 25/25 after pinning one check's layout (it leaned on the old shrinking). Dig, build and way up pass.
  breaking_test fails the same 8 checks before and after (they predate this). Restore point:
  restore-points/before-mountain-heights-step0-20261025/.
- 18:08 MOUNTAIN HEIGHTS step 1, STAGED: reports/ramps-gather/staged/heights_step1.py (not in game/).
  - var/const/RM_SKY_H = 10, the one source.
  - RmLevelOf(atom): an ordinary mountain top (below 10) is the Surface; a summit at 10 or more, a flyer up there
    and open sky are the Sky.
  - RmViewLayer(atom), and the camera follows it: the lock, a group recall, Next idle, Go to and the glide. A camera
    on a walker up an ordinary mountain stays on the Surface view (where Plan mode works too).
  - Arena on a patched copy: tests/mountain_levels_test.dm 4/4; heirs passes (it runs the camera tick). No page
    change, so no headless gate.
  - Not in step 1: Sky-view walker clicks. They go with step 2, which takes ordinary peaks out of the Sky view;
    before that, a refusal would hit peaks the player still sees there.
  - Fog stays as it is: layer 3 still means up high.
- 18:58 MOUNTAIN HEIGHTS step 2 LANDED (18:57:53): the peaks over ordinary mountains leave the 3D's sky layer (the Sky
  view's flat slab is gone), "skyh" goes in every scene for world-look's page, and RmSkyOpenFor lets rts-feel's
  open-sky rule treat an ordinary top as open sky from the Sky view. The user: "0% for now", so no mountain reaches
  the Sky; it is all open sky, plus building floors and wall walks. Off switch RM_SKY_SPLIT=0.
- 18:59 Real window sky1 for step 2 (with world-look's and rts-feel's parts): 12/12.
