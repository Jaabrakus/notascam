# Server upgrades borrowed from OpenRealm: plan (2026-10-30)

The owner wants Banners of the Deep hostable on a website server. They asked whether OpenRealm's server ideas could
upgrade our engine, so that more games can be made on it with BOTD as the framework. OpenRealm
(`/Users/kiwimango/Downloads/open-realm-main`) is a C engine in the style of Quake 2 for Warcraft III data. This plan
takes its **ideas, not its code**.

This is a plan only. Nothing in `game/`, `engine/` or `art/` changed, and there were no builds or runs. Everything
below comes from reading the code and existing reports. It waits for the owner's go-ahead.

Numbers say where they come from. **Measured** means a report has the run. **Estimate** means reasoned from those
numbers; treat it as a guess until measured.

## In short

| # | Upgrade | Idea | Saves | Work | Risk to play |
|---|---|---|---|---|---|
| U1 | **Landed and played 10-30.** **Cheaper sends, game side only**: move3D from the unit grid, changed units only, packed; terrain chunks built once for all players; fog, plan and sites only when changed | 1 | one player: -3 to -4.5 MB/s and -15 to -20 ms of DM time a second; each more player in the same area: up to -2.5 MB/s and -29 ms more (estimate) | 3-5 days | low |
| U2 | **Landed 10-30.** **The stall clamp**: at most 2 catch-up ticks after a stall, not 5 | 5 | no memory or CPU; no burst of ticks nobody can answer | half a day, with an engine build | low (the world slips ~0.6 s at a long stall instead of ~0.3 s) |
| U3 | **Landed 10-30.** **Engine/game boundary, step 1**: `engine/native/` split into generic and BOTD folders, plus an audit script | 6 | nothing at run time; lets a second game use the engine safely | 2-3 days | none (same engine bytes) |
| U4 | **Installed 10-30** (engine `5f075ac5`; spike, keys and sign-in; `reports/u4-web-1030/`). **Browsers talk to the server directly**: a WebSocket in the server, no relay client | 2 | per web player on the host: -110 to -300 MB and -45 to -70% of a core (measured relay cost), and no 2D entity sync on the server | spike 3 days; all of it 3-4 weeks | medium (keys, prompts and verbs need an audit; the relay stays as a fallback) |
| U5 | **Started 10-30** (`reports/u5-kept-1030/`: one player with 200 units, 157 → 69 ms of DM a game second). **HUD layers**: a HUD key is built only when its panel is open and its inputs changed | 4 | -40 to -60% of the HUD's ~30-50 ms a second per player (estimate) | 1-2 weeks | low to medium (a missed input leaves a panel stale; shadow checks guard it) |
| U6 | **Native per-player snapshot**: the engine diffs and encodes things and moves for each player and writes them to the socket | 1 | sends from ~100 to ~10-20 ms of DM time per player a second; 10 players fit on one DM thread (estimate) | 2-3 weeks | medium (the same proofs as every native) |
| U7 | **Unit storage**: packed own values, lists made on first use, typed records only where measured | 3 | ~4-5 KB a unit: nothing playing alone, ~0.13 GB at 30,000 units (estimate) | 1-2 weeks, after regions on disk | low |
| later | **U3b** rules out of the natives; the DM framework split; the Mac app as a thin WebKit shell | 6, 2 | the Mac game window: 0.65-0.7 GB → ~0.1-0.15 GB (estimate) | weeks each | medium |

The order is the U number. It is in section 5, with who runs what.

### Three corrections to the starting brief

- **"~50 MB/s for HUD and 3D sends" was never measured** (`reports/memory-1030/README.md:77`).
  - Measured: the whole server allocates **23-26 MB/s** playing alone (`reports/gc-slack-1030/README.md:74`;
    `reports/server-cost/pan6-v6-base.json`).
  - **The sends' share is about half of that: ~11-14 MB/s per player while the camera pans** (section 2). A still
    camera rebuilds no terrain, so it costs less.
  - The one bigger figure is the hidden 2D map's entity sync, while panning with 200 units: 72.8 → 35.6 MB/s when it
    is cut (`reports/server-cost/map2d-layer.md:30-37`).
- **Our sends are already partly deltas.**
  - Terrain chunks go only when their version moves.
  - Things go as `td` changes.
  - HUD units go as `_p`/`_gone`, and HUD keys only when they changed.
  - `3dfull` and `hudfull` already do what OpenRealm's `nodelta` does.
  - What's left to fix: every send is built in full just to compare it, separately for each player.
- **A ring of acknowledged frames isn't needed here.**
  - OpenRealm uses one only on lossy UDP. On a link that never loses or reorders (its loopback and EOS rooms) it
    deltas against the last frame sent (`docs/architecture/network.md:170-175`).
  - Both our links never lose or reorder: Robust's reliable channel and a WebSocket.
  - So we keep "last sent, per player", which we already have, plus a resync and a rate skip.

### How it fits the memory work

The owner picked "server first" (`reports/memory-1030/README.md`).

- **The collector-slack fix has landed** (`reports/gc-slack-1030/`). Since it landed, swept free room no longer adds to
  the footprint. So the send work here saves **CPU and collector time per player**, not much footprint.
- **The memory session's next two steps** (tiles asleep at load, then regions on disk) are the tile half of idea 3.
  This plan adds no second tile store (U7).
- **One big run at a time.** Every proof below is arena-sized or windowless unless it says otherwise.

## 1. What OpenRealm does

- **A fixed 100 ms tick with a clamp** (`server/server.h:128-138`, `docs/architecture/server.md:15-42`).
  - At most one simulation step per loop.
  - More than one tick behind, the deadline resets to now. A stall is never replayed as a burst of ticks.
  - Pause stops the simulation only; messages keep flowing.
- **Per-player snapshots** (`server/sv_ents.c:128`, `docs/architecture/server.md:66-142`).
  - Each tick, for each player, it collects the entities that player may see: not hidden, owner-only ones kept private,
    in view.
  - A game hook may change each copy for that player (`CustomizeEntity`).
  - It keeps 16 snapshots per player (`common/common.h:18`) and writes only the fields that differ from the snapshot
    the player holds.
  - A budget of 1,024 entities, nearest first, with priority entities the game picks (`common/shared.h:279`).
  - A slow link skips snapshots instead of queuing them (`sv_rate`). The next one deltas against what the player holds.
- **Configstrings** (`docs/architecture/network.md:303-351`). Model, sound, image and name strings go into numbered
  tables once. Messages then carry the numbers.
- **Flat entities and typed pools** (`docs/games/warcraft-3/pooled-entity-state.md`).
  - Every entity is a fixed-size `edict_t` in one array.
  - State only some entities have (a construction site, an item, a gold mine, a channelled spell) lives in
    fixed-size pools of typed records.
  - Only the behaviour that owns a record attaches it, and reads never allocate.
  - Hot unit and movement state stays direct "until measurements justify" moving it.
- **Server-authored HUD layers** (`ARCHITECTURE.md:74-105`).
  - The game builds a frame tree per HUD layer and sends it only when it changes.
  - A bitmask says which layers show.
  - Buttons send text commands back.
- **A strict boundary** (`ARCHITECTURE.md:250-289`, `docs/architecture/game-client-boundary.md`).
  - Engine code holds no game names, not even in enum or field names. Games plug in through function tables.
  - The client gets *results* (a position, an index), never *parameters* it must work out.
  - Their own docs call the name-matching audit script "necessary but not sufficient".
  - Their snapshot builder still carries a `#ifdef WOW` and a Warcraft mining debug block (`server/sv_ents.c:136-160`).
    The rule needs review as well as a script.

## 2. How BOTD does each of these today

| Concern | BOTD today | Where |
|---|---|---|
| Tick | 10 Hz (`tick_lag` 1, never set). After a stall, Robust's game loop runs up to **5 owed ticks** back to back and drops the rest (`MaxQueuedTicks = 5`; the server never changes it). Network input is read once, before those ticks. At speeds 1-4 each engine tick runs that many DM steps with no time check | `../opendream/RobustToolbox/Robust.Shared/Timing/GameLoop.cs:91,162-175,195,213-216`; `Robust.Server/BaseServer.cs:541-548`; `engine/clock/RemasterClock.cs:27-44` |
| Per-player work | Each player's track runs every 5 ticks (about twice a second), spread over ticks within a 30 ms budget: the HUD, then the 3D scene. move3D runs every tick | `game/Code/Remastered/QoL.dm:18,271-301`; `Spread.dm:9,90-97`; `View3D.dm:812-813,946-987` |
| What a send is | DM builds lists and `json_encode`s them, then compares the text with the last copy. At 1 KB or more it deflates and base64url-packs it; smaller sends are url-encoded. It goes out with `output()` to `mapwindow.hud:update3D`, `updateHUD` or `move3D` | `View3D.dm:791-807`; `HudPack.dm:28-34`; `engine/native/RmPack.cs` |
| Deltas already in place | Terrain chunks by `rm_chunk_ver` (RmVer, per 16x16 chunk); each chunk's JSON is cached **per player**. Things go as `td` changes, with a full list every 60 scenes. Entries are cached per viewer on `rm_ver`. HUD units go as `_p`/`_gone` plus a `hot` row; HUD keys only when their JSON changed | `View3D.dm:39-42,271-334,375-411,514-536`; `HUD.dm:99-237` |
| Sent in full every scene | Fog bits for the whole window, blueprints, plan, sites, far units, work, yield and build. move3D sends **the whole list** whenever anything in it changed; it is url-encoded and never packed | `View3D.dm:871-929,981-987`; `Fog.dm:356-385` |
| What a player is sent | 3D things from `range()` round the camera (20x15 up to 50x40 tiles), fog-filtered on the surface and in the sky (12-tile sight). move3D runs `range(25)` twice, ground and sky. Caps: 600 entries, and up to 3,500 with bodies and blood. The HUD sends all your units below 1,000, and only those on screen or selected above that | `View3D.dm:432-504,972-978`; `HudView.dm:10-14,316-345` |
| The hidden 2D map | OpenDream still syncs every entity within 25 tiles (`net.pvs_range` default) to the game window, which keeps all it ever saw | `reports/memory-1030/README.md:78`; `reports/server-cost/hidden-2d-audit.md` |
| Browser players | One headless Robust.Client per player (the "relay"), with the full handshake, PVS entities, skin.dmf and icons. It never draws. It turns `output()` into JavaScript and forwards it over a WebSocket; keys go through skin.dmf macros, and prompts are read by reflection | `web-relay/RelayWebViewManager.cs:114-126,186-217,527-608`; `tools/web_host.py:116-148,265` |
| Entities | Every tile is a `DreamObjectTurf` plus a cell: 286 B awake. Sleeping tiles pack into 128x128 blocks of parallel arrays, ~15-20 B a tile and 52 B in all. Every unit is a `DreamObjectMob` with a `Dictionary` of own values (~134 values, ~22 lists, ~100 KB of heap, measured 10-24) and a Robust entity | `engine/compact/DreamMapManager.RmTiles.cs:20-27`; `planning/MAP_MEMORY.md`; `planning/UNIT_MEMORY_PLAN.md` |

### What one player costs the server in sends

**Measured** on 10-24: a pan run, engine v6, one player, 3 units, the camera moving (`reports/server-cost/pan6-v6-base.json`):

| Send | DM time, ms a second | Allocation, MB/s |
|---|---:|---:|
| move3D (10 a second) | 19.6 | 4.9 |
| 3D scene (~2 a second): terrain 14.0 + 15.0 on two layers, things 7.5 + 1.8, fog bits 3.6, unit pictures 3.0, far view 2.2, the rest ~2 | 49 in its parts (12 for the calls the label caught) | 4.4 in its parts (1.9 caught) |
| HUD (~2 a second) | 13.7 caught, 18.7 for its data | 1.9 |
| **One player's sends** | **~90-110** | **~11-14** |
| The whole server | | 23.2 |

- Why a range: a call that sleeps into a later tick is not timed (`TickProfile.dm:13-15`). That is why the
  parent labels read less than their parts.
- **200 units, 10-24**: HUD data 45-50 ms a second and 3D builds 35-40 (`reports/server-cost/map2d-layer.md:20-21`).
- Not measured again since: neither figure is on app 146. U1 starts by measuring again in the arena.
- **Sizes** (measured):
  - 53 units: a 3D send is 25.6-26.2 KB of JSON, a HUD send 41-682 B (`reports/server-cost/hudpack-real.md:73`).
  - 203 units, all selected: HUD 36-514 KB, 3D 91-174 KB (`hud-delta-check.md:71`, `hud-parts-check.md:71`).
- **Bandwidth** (estimate):
  - Today: about 20-150 KB/s per player. Most of it is move3D, url-encoded (+50%) and never packed.
  - After U1 and U4's socket compression: about 5-30 KB/s.
  - 50 web players would then need 0.25-1.5 MB/s of upload, which a small server has. **Bandwidth isn't the limit.
    DM time per player is.**
- **What it means for the MMO** (estimate):
  - At ~100 ms of DM time per player a second, 10 players would take the whole DM thread for sends alone.
  - That is the MMO plan's phase 1 (`planning/MMO_ARCHITECTURE.md:20`). It needs U1, U5 and U6.

## 3. The upgrades

### U1. Cheaper sends, game side only (idea 1, first step)

**Landed 10-30 19:49 (`u1-sends`, restore point `restore-points/before-polish-u1-sends-20261030-194806`).** Arena proof in
`reports/u1-sends-1030/README.md`: 0 differences in rows and page models; a move call allocates 72-76% less and takes
33-43% less time; terrain builds for two players 60 → 42. Played in the real game the same evening (two players in the
browser pane): page and server positions the same for 63 of 63 units, 121 chunks shared, 0 scene pull-backs in 3,224 checks.

OpenRealm takes each player's entities from a spatial index, compares fixed fields and sends what differs. We build
whole DM lists and their JSON every time, only to find out whether anything changed.

Build (all in `game/Code/Remastered/View3D.dm`, no engine change):

1. **move3D from the grid.**
   - Replace the two `range(25)` scans (`View3D.dm:972,978`) with `rm_grid_units`.
   - That native already exists: a box query over the 16x16 unit cells (`engine/native/RmGrid.cs:283`, used by
     `FarSteps.dm:123`).
   - Today's `range()` lists every tile in a 51x51 box, twice, ten times a second.
2. **move3D per unit, not per list.**
   - Keep each unit's last-sent row for each player (x, y, facing, step gap, level, feet). Send only changed rows,
     plus a "gone" list.
   - Keep the `@t` clock stamp on every send; the page paces its walks by it (the rubberbanding fix, app 134).
   - Pack it like the other sends.
3. **Terrain chunks built once for all players.**
   - Each player caches each chunk's JSON in `rm3d_chunks`, so two players looking at one place each build it.
   - Checked: a chunk build reads only the tiles' own vars and the global `remaster_wallwalks`
     (`View3D.dm:152-238`), and its key is made of global counters (`:299`). So one cache keyed by (chunk, key)
     serves everyone. Each player keeps only which key their page has.
   - Underground sight bits (`Remaster3DSeenBits`) stay per player.
4. **Only on change.** Fog bits, plan, sites, far units, work, yield and build go only when their JSON differs, as HUD
   keys already do (`HUD.dm:131-142`).

Saves (estimate, from the table above):

- move3D: 60-80% of its 4.9 MB/s and 19.6 ms a second.
- Fog bits, far view and the rest: ~0.4 MB/s and 3-5 ms a second.
- **One player: about -3 to -4.5 MB/s and -15 to -20 ms a second.**
- **Each more player in the same area: up to -2.5 MB/s and -29 ms a second more**, the terrain they no longer
  build again.
- Bandwidth: move3D shrinks to the units that moved, packed: 3-10x fewer bytes (estimate).
- Footprint: little, since the collector fix.

Work: 3-5 days with proofs.

Risk to play: low. Two things could slip, and both show in the page's model:

- glide pacing, if the stamp or a step gap went missing;
- units that never vanish, if a "gone" were missed.

Proof:

- A shadow mode builds the old and the new send and applies both to a model the way the page does.
- Over an arena battle, a village minute and two players side by side, the models must match after every send (0
  differences).
- Time it from inside with the flat profiler (`step-native`'s engine). The real app is needed only for the landing's
  last check.

Fits with: the construction session sends `sites` in 3D. Land U1 through the lander while that session isn't in
`View3D.dm`.

### U2. The stall clamp (idea 5)

**Landed 10-30 20:41** (engine sha256 c092ac0e after the 20:5x review, `reports/u2u3-engine-1030/README.md`; since 21:15 d48578fc, the memory session's map defs on top, clamp kept): in our game clock rather than
Robust's BaseServer (we don't build Robust.Server). After a stall, 3 game ticks run back to back instead of 5, and 500 ms of
game time is let go instead of 300. `RM_CATCH_UP=5` gives the old behaviour.

- **Today:** after a stall, Robust runs up to 5 owed ticks back to back, within milliseconds of each other. The
  autosave stalls the server ~770 ms (`reports/gc-slack-1030/README.md`), and 5 ticks follow at once.
- **Why that matters on a shared server:**
  - Robust reads the network once before those ticks (`GameLoop.cs:195`), so no order can arrive inside the burst.
  - Fights resolve and units walk for half a second that nobody could answer.
  - The page hides most of it, because it paces walks on the server's clock.
- **OpenRealm and Quake 2** never let a stall be more than one tick late.

Build:

- Set `MaxQueuedTicks = 2` where the server makes its game loop (`Robust.Server/BaseServer.cs:541-548`). One late tick
  is kept and the rest dropped. It goes in as a patch block in `tools/build_runtime.py`.
- An environment switch, as the GC has (`RM_MAX_QUEUED_TICKS`), so it can be compared and undone.
- Pause already freezes the game clock (`RemasterClock.cs:30`). OpenRealm's pause rule already holds here.

Saves: nothing in memory or CPU. It buys fairness: no tick runs that nobody could answer.

Work: half a day, riding on an engine build (renumbered after v25). It shouldn't share a landing with the memory
session's tiles-asleep build: each needs its own proof.

Risk to play: low. A 770 ms stall drops ~0.57 s of world time instead of ~0.27 s. On the page, that looks like a short
still moment instead of a hurry.

Proof:

- An arena run with a forced 800 ms stall (a busy loop in a test proc), timed with gc-slack's stall probe
  (`reports/gc-slack-1030/ZZStall.dm`, which logs every gap between ticks).
- Count the ticks within 50 ms after the stall: 5 today, 2 or fewer after.
- Read the move3D arrival times.

### U3. Engine/game boundary, step 1 (idea 6)

**Landed 10-30 20:41** (`reports/u2u3-engine-1030/README.md`): engine/core (8) and engine/game-botd (18), the same
bytes (the split builds to v26's 88d0dfeb exactly); `tools/engine_boundary_audit.py` with a 47-name baseline, all in
RmNative.Register (U3b's job).

What in our engine is BOTD's today (the natives are registered in `engine/native/RmNative.cs:61-133`, engine v25):

| Kind | Files | BOTD names inside |
|---|---|---|
| **Generic services** | RmVer (chunk and movable change counters), RmWatch (watched var writes), RmPack (deflate + base64url), RmAlloc, RmMemory, RmTiles (sleeping tiles), RmDist (`get_dist`); the build patches MEMORY, VER, WATCH, MAPTRIM, GRID, TICKGC, ASSOC, COMPACT, SAVE | none |
| **Generic mechanism, BOTD names inside** | RmGrid (`"Owner"` foe test), RmKept (`density`, `Flying`, `Wagon`, `Owner`), RmPath (512-tile search; walkability through RmWalk), RmPlan (`Owner`, `Wagon`, `HP`, `GoingToDie`), RmChat (`mapwindow.hud:remasterChatLine`; on only when the game declares `RemasterChatKeep`), RmSight (`Owner`, the `"{NPC Goblins}"` owner text); the CLOCK patch uses `world.game_state` as the speed | var and control names |
| **BOTD rules in the engine** | RmWalk (chasm, sky, holy `GoodGrass` against `Infects`/`Undead`/`Unholy`/Svartalfar/Demon, `remaster_wallwalk`, doors' `Placed`/`Locked`); RmStep (the same, plus `remaster_active`, `rm_door_n`, `IsMist`, `remaster_delivery`, `remaster_site_path`); RmReach; RmRoute (radius 96, 600 steps); RmField (the standing-foe test on `HP`, `remaster_ko_until`, `GoingToDie`, `Fainted`, `rm_dying_until`, `CantKill`, `WS`, `Wagon`; reach 40); RmMorale (`Critter`, `Sleeping`, `IsRoyal`, `remaster_caravan`, the attacked-in-30-s rule); RmPool (the box score); RmSlots; RmStore (`remaster_delivery`); RmDecay (the 2006 item rule on `suffix` and `Content3`, the 180 cutoff); RmWorked (6000/50 cutoffs); RmSwim (`Race`, `remaster_waterlift`) | rules |

A second DM game would already run on this engine, because it would simply never call our natives. Two things leak:

- **The speed.** A game that writes a number into `world.game_state` changes our clock's speed.
- **Engine tuning.** Changing the engine for game two could break BOTD's walking rules, because those rules sit inside
  the engine.

So the boundary protects two things:

- **reuse**: the grid, versions, routes, timers and sends serve the next game;
- **safety**: game two's changes can't touch BOTD's rules.

Build, step 1 (no behaviour change):

- **Two folders.** `engine/core/` holds the generic rows and `engine/game-botd/` the rest. `build_runtime.py` copies
  both into the same place as now.
- **A rule in `planning/ENGINE_PLAN.md`.** No game type paths, var names, races or rule numbers in `engine/core/` or in
  a generic build patch.
- **An audit script** (`tools/engine_boundary_audit.py`). It lists every quoted var or type name in `engine/core/` and
  fails on a new one.
  - It only matches names; OpenRealm's lesson is that this is necessary but not enough.
  - So the native plan's review step also asks "is this a rule?".

Work: 2-3 days. Proof: the engine built from the two folders has the same sha256 as v25. The same check showed a
rebuild was exact on 10-22.

Later, **U3b** (1-2 weeks, a piece at a time with other native work):

- **One walk class.**
  - Walk, step, reach, route, field and slots each carry a copy of "who may stand where": race, holy ground, chasm,
    sky, doors, wall-walks.
  - It becomes one interface in core, which BOTD implements once in `game-botd`.
- **Names from the game.**
  - RmKept's and RmField's var names come from a table the game registers at boot.
  - That is OpenRealm's `game_import` / `game_export` shape: engine services the game calls, and game hooks the engine
    calls.
- **Proofs.** Every move keeps its shadow mode (0 differences), as every native has.

The bigger boundary is in DM. `game/Code/Remastered/` mixes framework files with BOTD's content (races, combat, jobs):

- **Framework DM:** View3D, HUD, HudPack, HudView, Spread, Awake, FarRecords, UnitClock, WildClock, Native,
  TickProfile.
- **Framework page:** `art/hud/src/`.

A second game wants the framework without the dwarves. That split needs two things:

- a list of framework files that may not name BOTD types, checked by the same audit;
- a page that draws *results* only.

It is weeks of work. It is best done after U4 and U6, when the sends are native and the framework is smaller.

### U4. Browsers talk to the server directly (idea 2)

**Spike done 10-30** (`reports/u4-web-1030/README.md`), in a test engine only (`--web`; without it the build is the
installed `d48578fc` byte for byte). In the browser pane, against the arena, with no relay client:

- the game's page, files and calls all came from the server, on one port;
- a player selected a unit and walked it, and had four Humans chop a tree;
- reloading, a second player, leaving after the grace and rejoining all worked;
- a probe checks the same 13 steps without a browser.

What differs from the plan below:

- **Its own HTTP listener** (`RM_WEB_PORT`), not Robust's status host, which the arena and the app run with
  `status.enabled=false`.
- **Calls as `{f, a}`**, not `{js}`: the page calls them by name, with no `eval`.

**Installed 10-30 22:4x** (engine `5f075ac5`, `--web` on by default; nothing listens without `RM_WEB_PORT`).

**Keys and sign-in done 10-30:**

- **Keys.** The skin's macros are run by the server for web players, with the native client's verb lookup and
  argument parsing. +REP keys repeat each tick while held.
- **Sign-in.** A server with `RM_WEB_SECRET_FILE` takes only signed one-use links (HMAC, at most an hour). The Discord
  link service's `/play` hands them out. A server open to other computers needs sign-in or `RM_WEB_OPEN=1`.
- **Proof.** The probe passes 27/27 with sign-in and 10/10 without.

Left for the full path: real Discord (the owner's portal settings and an https host), other windows, deflate, a send
skip, file caching, many players and a real world.

A browser needs little (`web-relay/`, `game/Interface/remastered.html`):

- **From the game:**
  - `{js}` calls: `updateHUD`, `update3D`, `move3D`, chat lines and a few event calls.
  - Files over HTTP: the 2 MB page, PNGs, models, sounds and fonts.
- **From the browser:** `{ready}`, `{nav}` (a Topic `?rm=` action), `{key}`, `{cmd}` and `{prompt}`.

The relay client does all the rest only because OpenDream needs a full client to connect. That rest is:

- the Robust handshake;
- PVS entities and icons it never draws;
- skin.dmf;
- prompt windows read by reflection;
- a port per player.

Build, in the server process (`../opendream/OpenDreamRuntime/DreamConnection.cs`):

- **One HTTP and WebSocket listener, one port for all players.**
  - Robust's status host already takes WebSockets (`Robust.Server/ServerStatus/IStatusHandlerContext.cs:29,61`). Its
    own file transfer uses them (`Network/Transfer/ServerTransferImplWebSocket.cs:107`).
  - It takes extra handlers (`IStatusHost.cs:12-13`). Nothing to download.
- **A web connection.** A `DreamConnection` with no Robust session. `HandleConnection` takes an `ICommonSession` today
  (`:99`). DM still gets a `/client` with a mob, `view`, key and ckey.
  - `OutputControl` (`:312`) becomes `{js}`, with the relay's encoding.
  - `Browse` (`:481`) serves the page.
  - `BrowseResource` (`:455`) becomes a file store per connection, served over HTTP.
  - Prompts and alerts become `{prompt}`.
  - `winset` and `winget` get answers or stubs (`HUD.dm:30-31,62,68,81-84`).
  - Topic goes straight to the topic handler.
- **Keys.**
  - Either skin.dmf's 111 macro commands become a key table the page sends as `rm` actions, or the server runs them by
    name.
  - The digit-group and duplicate-name traps are in the memory note "Skin key bindings".
  - Verbs are then checked by the server's `CanExecute` alone. The relay's "in view" list (`RelayView.cs`) goes.
- **Sign-in.**
  - A short-lived HMAC token in the hello, checked in `RemasterJoinGate` (`planning/MMO_ARCHITECTURE.md:65`), instead
    of a typed name and one shared password.
  - Discord sign-in already works locally.
- **A protocol version in the hello.** OpenRealm turns away a mismatched peer before any state. Our server always
  serves its own page, but a browser can keep an old one in its cache.
- **Rate skip** (OpenRealm's `sv_rate`). If a socket's queue backs up, skip that player's next 3D or move send. The one
  after goes against what was last sent. Sends never queue without bound.
  **Done 10-31** (`reports/u4-rate-1031/README.md`; native version 29 `rm_web_behind`, engine 442d15a0, game
  "web-rate-skip"). A tab that stopped reading for 35 s held 154 KB queued at most instead of 1,434 KB and growing,
  and every unit was in place when it caught up.
- **Socket compression** (per-message deflate) for web players, in place of base64url (+33%) and url-encoding (+50%).
  **Done 10-31** (`reports/u4-deflate-1031/README.md`; engine 4c1396df). One deflate stream kept per tab, binary
  frames, asked for by a page that can inflate. The join went from 28.6 to ~4.6 KB/s, busy steady from 5.6 to ~3.8,
  and quiet from 0.7 to ~0.1.
- **https.** Over the internet the server needs it. A proxy in front (Caddy or nginx) is a download: the owner decides
  when hosting starts.

Saves:

- **Measured: a relay client costs 110-300 MB and 45-70% of one core on the host** (`planning/WEB_CLIENT.md:84-88`;
  10-22, under Rosetta).
  - For 50 web players that is 5.5-15 GB and 22-35 cores.
  - It is the "doubles the bill" line of `planning/MMO_ARCHITECTURE.md:106-114`.
- **The server sends no 2D entity sync to a web player.** While panning with 200 units, that sync was half the server's
  allocation (72.8 → 35.6 MB/s) and 17 points of its CPU (measured 10-24, engine v5). A still camera showed nothing.
- **No port per player** (100 at most today, `web_host.py:265`), and `net.max_connections=16` no longer counts web
  players.

Later, the Mac app (estimate):

- **The window.** The game window is the Robust client, 0.65-0.7 GB (`reports/memory-1030/README.md`). If its WebKit
  page connected the same way, the window would be a thin shell of ~0.1-0.15 GB.
- **Bigger than the 2D lever.** That cut is bigger than the hidden-2D map lever (0.2-0.4 GB).
- **The whole game near 1 GB.** One Mac would sit close to the owner's goal: the server ~0.6-0.9 GB after regions, the
  page ~0.4, the GPU ~0.15, the shell ~0.1.
- **The owner's order.** It keeps that order: the player side after the server, and the 2D map last, after a click
  audit (memory "Remove unneeded 2D").

Work:

- a spike of 3 days: an arena server and one browser in the browser pane, no relay. It sees `update3D`, selects a unit
  and moves it;
- then 3-4 weeks for the whole path: keys, prompts, sign-in, files, many players and the rate skip.

Risk to play: medium.

- Anything that still goes through the 2D map, a macro or a prompt window breaks for web players until it is moved.
- The relay stays as the fallback until the click and key audit passes on both paths.
- The owner tests in the browser pane, so this is also the owner's own test path (memory "Play-test in the browser
  pane").

### U5. HUD layers, built only when open and changed (idea 4)

**Started 10-30** (`reports/u5-kept-1030/README.md`), measured first with the flat profiler. One player with 200 units
went from 157 to 69 ms of DM a game second:

- a unit's health share is kept on its change counter ("life-frac-kept");
- the game's own caches and marks no longer count as a change of a unit (engine `rm_ver_quiet`, "ver-quiet");
- a value written again unchanged no longer counts either (the VER patch; engine a8dd8416);
- the skills pass's skip works again ("skill-pass-skip": it compared text with a number);
- a ground unit keeps its move row ("move-rows-kept").

The 3D view's kept entries now hold for a unit standing still. Next, from the same profile: the HUD entry key and the
units delta. They read lists changed in place, which need their own counters.

OpenRealm's HUD is frame trees the server writes. **That part stays out.** Our HUD is HTML and CSS the owner approved
(the style guide, the lettering), and the page already draws from data. What to borrow is the layer contract:

- **Open panels come from the page.**
  - The page says which panels are open: a mask, like OpenRealm's `uiflags`. The server builds only those keys.
  - Some already work this way: `lineage`, `board` and `ropes` only on their tab (`HUD.dm:673-685`), and the on-screen
    set above 1,000 units.
- **Built when changed, not compared.** Each key gets a change counter from its inputs: RmVer on units, or the game's
  own counters. The key is built only when its counter moves. Today it is built every send just to compare its JSON.
- **A string table per player** (OpenRealm's configstrings). Repeated names (icon keys, item names, picture keys) go
  once, then as small numbers. Sends get smaller, and DM makes fewer strings.
- **Results, not parameters.** The page keeps drawing results. Any rule found in the page moves into DM (OpenRealm's
  camera-shake lesson).

Saves (estimate): -40 to -60% of the HUD's 13.7 + 18.7 ms a second and 1.9 MB/s per player at 3 units. At 200 units
the base is 45-50 ms a second. Sends get smaller too.

Work: 1-2 weeks, a key at a time.

Risk to play: low to medium. An input left out of a counter leaves a panel stale. Guards:

- a full build every few seconds that logs any difference from the kept copy (a shadow check, 0 differences before
  landing);
- `hudfull` stays.

Files: `HUD.dm`, `HudView.dm`, `art/hud/src/`. It can run beside U4 in another session.

**10-31 morning, "Trim HUD updates"** (the owner's pick; `reports/u5-hud-1031/README.md`). One browser player, 200
units with packs, 50 walking:
- **"hud-delta-lean"** (07:48): kept entries are no longer compared part by part, and hot rows are made once. The sends
  are byte for byte as before.
- **"hud-hot-changes"** (07:53, page and server): only the changed units' hot rows go (`hotd`). The HUD sends went from
  4.7-6.4 to 1.4-1.9 KB/s.
- **Native version 30** (engine cee41dca, 08:25; "hud-units-native", 08:25): `rm_hud_units`, the units delta in the
  engine, the same to the byte as the DM pass kept for older engines. The delta and its encoding went from 7.6-8.9 to
  3.6-5.4 ms a game second.
- **"hud-build-once"** (09:06; the owner: "it rebuild entries multiple times"): a kept entry records what it was built
  from (the unit's change counter, what lies outside it, a clock limit). A send that finds none of it moved makes no key
  and no 3 s rebuild. Shadow check: 37,876 kept entries, 0 different from fresh. Keys 400 -> ~110 a second, builds
  82 -> ~50, the HUD 18.7-30.1 -> 14.3-23.5 ms a game second.
- **"hud-view-once"** (09:37; the owner: "multiple players could bring in multiple thousands of unit"): over 1,000
  units the view pass's records stand while nothing they read moved, and the totals move only with a changed record.
  The units on screen come from the unit grid, not a walk over the company. Shadow check 26,727, 0 different.
  2,000 units: the HUD's view work 18-19 -> 13 ms a game second.
- **Native version 31** (engine 2f6b1e9d, 10:52; "hud-state-counter", 10:52; the owner: "record rebuilt per second
  thats to much"): `rm_ver_state`, a counter that stands while a unit walks. An engine trace found every step counted
  twice (the engine's Move() writes loc, and the write was counted on top of the step), facings the same way through the
  look. Shadow check 123,677, 0 different. 200 units, 50 walking: entry keys 104-122 -> 0 and builds 45-52 -> 0 a second,
  the HUD 14.3-23.5 -> 11.4-11.5 ms a game second. 2,000 on orders: view records 110-119 -> 58-76 a second.
- **Native version 32** (engine 2bf3f0a1, 11:12; "once-mana-skills", "far-units-near", "fog-mark-native", 11:12; past
  the HUD, the owner on the rest of the list: "oh shit this is bad"). 2,000 units on orders, ms of DM a game second:
  - skill pass 26-27 -> 2.5 and mana tick 8.4-8.9 -> 2.2-2.6 (skip units whose state counter stands);
  - far figures 24-26 -> 7.2-7.6 and view() 14-16 -> ~0 (only units with someone else near look);
  - fog marks 18-25 -> 0.7-0.9 (`rm_fog_mark` in the engine).
  Shadow check (`RM_ONCE_VERIFY=1`) 429,896, 0 different. `reports/u5-hud-1031/README.md` sections 6-7.
- **Native version 33** (engine cf4491aa, 11:51; "fog-build-moved", "far-units-moved", 11:52): `rm_list_changed`, the
  things in a list whose counter moved since a caller's last look (engine/core/RmChanged.cs). The fog's side build makes
  only moved sources' circles again (~20 -> ~7-8 ms a game second at 2,000), the far figures only changed units' rows
  (~9-10 -> ~2.5-3). Shadow check: whole builds and lists compared, 0 different. README section 8.
- **Native version 35** (engine c81b4d2d, 13:39, on the memory session's K2 b561a233; "3d-shown"; the owner: "those
  rebuilts are high arent they? shouldnt we get like 100?"): `rm_ver_shown`, the state counter less 27 names no 3D entry
  draws (the card's order status, current order, order list, combat marks). Of ~500 unit 3D entries made again a second
  at 100 players, ~490 had come out the same. Now 547 -> 181 built a second, the 3D entry chain 38.8 -> 28.4 ms a game
  second. Shadow check ~112,000 kept entries, 0 different. README sections 11-12.
- **Engine 9ef15f72** (14:57; on the memory session's L2g a4e09664, with the u5 lead session's delayed ref reuse): the HUD
  unit list keeps each part's and each rest field's code while its value stands (engine/game-botd/RmHud.cs; the same
  bytes out). At 100 players 88% of the parts encoded again had come out the same; rm_hud_units 18.7 -> 15.9 ms a game
  second paired (-15%; -21% unpaired on the first version). Verified ~3.97 million times, 0 different. README section 13.
- **Engine 2987f431 + "3d-shown-more"** (18:17; the owner: "Yes, trace them", then "Yes, build them"): a debug engine traced
  what still moved the shown counter (README section 14): the 2006 Births() sweep (an overlay taken off that isn't there
  set the look again: now no change, tools/build_runtime.py), the organs' health (the 3D key now holds the health %), 87
  names no entry reads. RmLifeFrac kept on the state counter (it was worked out again on every step). Identical 3D
  rebuilds at 100 players 126 -> 11 a second; health fraction 12.8 -> 9.0 and the 3D chain 22.0 -> 20.0 ms a game second
  (unpaired). README section 15.
- **Left:**
  - the view pass's walks over the company every 2 s (its list, rows, minimap cells: ~3.5-4 ms a second at 2,000,
    growing with size);
  - the Supplies card;
  - the 3D entry keys made again by each viewer.

### U6. Native per-player snapshot (idea 1, second step)

**Step 1 done 10-31** (`reports/u6-rows-1030/README.md`).

- **The move rows.** They come from the engine's changed units (native version 27, `rm_grid_changed`; engine
  e93509d2), with a fog sight number so that others' units are looked at again only when your sight changed.
- **Measured.** Ten web players with 200 units in view: the server's DM time went from 214 to 161 ms a game second.
  The move rows went from 35.0 to 2.8, and the fog checks from 11.2 to 2.4.
- **Also.** The 3D list asks once per owner whether it is allied or at war ("scene-relations-kept": ~9 ms a second
  for ten players).
- **Step 2 started 10-31** (`reports/u6-scene-1031/README.md`):
  - the scene's things now come from the engine (native version 28, `rm_range_movables`; engine 7e28d0ef). The
    scene gets range()'s things in range()'s order without its 2,601 tiles: range() went from 11.0 to 3.7 ms a
    second for ten players;
  - the 3D entry key is made at once (~18% less);
  - the HUD entry key is made at once (U5's rest, ~20% less).
- **Place by rows (10-31 01:14, its flaw fixed 01:45 as "scene-place-by-rows-2"; `reports/u6-place-1031`).** A unit near the camera whose entry changed only in place
  is left to the move rows. In a busy scene (50 of 200 units walking) the scene fell from 45-51 to 27-34 KB/s, with
  the page model exact every tick.
- **Next:**
  - the scene's order and fog mask, which are now its biggest parts (both need the page owner's eye);
  - the scene's things kept between lists (only the changed built and looked at), as the move rows are now.

After U1 and U5, what's left per player is building, diffing and encoding entries on the DM thread. That moves into
the engine:

- **A send schema, declared by the game at boot.**
  - It says which fields of a thing or a unit go to the 3D page: position, facing, step gap, level, picture key, owner
    relation and flags.
  - The engine keeps one small record per sent entity. Hooks it already has (VER on var writes and moves, GRID on
    `SetLoc`) keep the record current.
- **Per player, at each tick's end:**
  - The engine reads the grid cells in view and filters them by that player's fog. Fog becomes a native grid per realm.
  - It compares each record with that player's last-sent copy as plain data, not JSON, and writes the changes.
  - It copies the records on the DM thread (a few µs a unit). Encoding and socket writes run on a worker thread.
- **A game hook per player** (OpenRealm's `CustomizeEntity`) for what differs by viewer: selection, actions,
  relations.
- **DM-built entries.** Rich entries only DM can build (a unit card's actions) stay DM-built and cached on `rm_ver` as
  now. They ride along as a closed blob.
- **Budget and priority.** Today's caps stay, nearest first, with the game picking priority entities.

Saves (estimate): together with U1 and U5, sends fall from ~100 to ~10-20 ms of DM time per player a second. Ten
players would then spend 100-200 ms of each second on sends instead of all of it. That is what lets the MMO plan's
phase 1 run on one DM thread.

Work: 2-3 weeks, after U4, so it writes straight to the socket instead of through `output()` and Robust.

Risk to play: medium; it is the 3D view's whole input. Proofs, as every native has:

- a shadow mode: the DM send built beside it, and the two page models compared (0 differences);
- arena battles and a village minute;
- the real app only for the landing's last check.

### U7. Unit storage (idea 3)

**Tiles: no new work.**

- The sleeping-tile blocks already are OpenRealm's flat arrays: 128x128 parallel `ushort`/`int` arrays, ~15-20 B a
  tile.
- The memory session owns the next steps: tiles asleep at load, then regions on disk.
- One part of OpenRealm's idea isn't in those steps yet: **peek reads**. The route search, `rm_walkable`, `view` and
  `range` would answer from the packed record without waking the tile.
- Peek reads are already named in `planning/MAP_MEMORY.md` ("What still wakes tiles needlessly") and belong with that
  work.

**Units: not flat arrays.**

- Units as fixed C# structs instead of DreamObjects would put every DM rule that touches a unit (most of ~170 files) in
  two places.
- The native plan's own rule says no: "game rules stay in the game's script"
  (`planning/NATIVE_PLAN_2026-10-28.md:15`).

The forms of the same idea that fit OpenDream are already in `planning/UNIT_MEMORY_PLAN.md`:

- **Packed own values** (its step 2): a slot array instead of the `Dictionary<string, DreamValue>`, with values equal to
  the type's default not stored. About 5 → 2.7 KB a unit (estimate).
- **Lists made on first use** (its step 3). This is OpenRealm's "attach only when the owner needs it; reads never
  allocate".
- **Typed records for sparse state, only where measured.**
  - Candidates: construction sites, blueprints, item timers (RmDecay is already one engine timer for every item) and
    items lying on the ground.
  - Measure first with `rm_memory_report` in the arena, by owner var.
  - OpenRealm measured that a lookup on every unit every frame costs. So hot fields stay direct.
- **The Robust entity per movable** (its step 4) only serves the 2D sync. Once every player connects as in U4, it can
  shrink. That needs the same audit as the 2D map.

Saves (estimate):

- ~4-5 KB a unit.
- Playing alone with 43 units that is ~0.2 MB, nothing for the 1 GB goal.
- At 30,000 units it is ~0.13 GB.
- Where the ~100 KB a unit goes hasn't been measured since 10-24, before `UnitClock.dm` replaced the 8 loops each unit
  ran. Measure before choosing.

Work: 1-2 weeks of engine work for packed values, plus 3-5 days in DM for the lists. It comes after regions on disk.

Risk to play: low; values keep their meaning. Proofs:

- a fuzz test of set, get, the `vars` list and the savefile against the dictionary;
- every arena check.

## 4. What not to take

- **The simulation rewritten as flat C structs.** It is the heart of OpenRealm and the wrong move here: every rule would
  live in two places (U7).
- **UDP with sequence numbers, acks and a 16-frame ring.** Our links never lose or reorder. "Last sent" plus a resync
  is enough.
- **HUD frame trees written by the server.** We send data. The page keeps its approved look (U5).
- **A hard 1,024-entity cut.** Our caps and shed tiers stay, so health, combat, selection and order feedback are never
  held back.

## 5. Order and who runs it

1. **U1** (landed 10-30): game side, days, low risk. It lands while the construction session isn't in `View3D.dm`.
2. **U2 and U3** (landed 10-30) ride on the next engine build after the memory session's tiles-asleep build. Each gets its own proof.
   U3 leaves the engine bytes unchanged.
3. **U4**: the spike first (arena and the browser pane, no full-world run), then all of it. The spike, keys and sign-in
   were done and installed 10-30. Hosting for friends still goes through the relay until "Host on the Web" uses the link. This is the step that makes website hosting real.
4. **U5** in another session beside U4 (different files).
5. **U6** after U4.
6. **U7** after regions on disk, starting with a fresh measure of where a unit's memory goes.
7. **U3b**, the DM framework split and the Mac shell come later, a piece at a time.

Every step keeps the house rules:

- one big run at a time;
- light proofs, land on a pass, build at once;
- shadow modes with 0 differences for anything moved into the engine;
- the saves folder never touched.

## 6. Questions for the owner

1. **U1**: go ahead? It is game side only, 3-5 days.
2. **U4**: should the server go web-first, with browsers (and later the Mac app) connecting with no Robust client? The
   relay would stay until the key and click audit passes. The https proxy for a real host is a download, decided when
   hosting starts.
3. **U2**: is a still moment of ~0.6 s at a long stall better than today's burst of catch-up ticks nobody can answer?
