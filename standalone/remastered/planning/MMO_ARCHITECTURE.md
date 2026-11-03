# Kin & Stone as an RTS MMO: architecture plan

Written 2026-10-22 from the code and notes as they are today. Goal set by the user the same day: "I want this game to be the first RTS MMO" and "I want the world as Daggerfall": one persistent land that never stops, vast and generated, many players on it at once, with accounts.

Every number says where it comes from: **measured** (a test run), **notes** (`../NOTES.md`, `planning/WEB_CLIENT.md`), or **estimate** (reasoned from those; treat as a guess until measured).

## 1. What "MMO" means here, and the target

Today the game is one world per host: the Mac app runs a server and a client on the player's Mac (`mac-app/launch.zsh`), friends join it over the internet with one shared password (`game/Code/Remastered/Joining.dm`), the server allows 16 connections (`net.max_connections=16`, `launch.zsh`), and the world only runs while the host's app is open. A village only works while its player is connected (`RemasterLoop` in `Code/Remastered/QoL.dm` ticks only `client` mobs), and catches up when they return (`Away.dm`, up to 8 hours at half pace).

MMO means:
- **One persistent world** on a server that is always up; players come and go; the land, the realms and the war carry on.
- **Many players at once**: tens on one world to begin with, hundreds later.
- **Accounts**: a player is an account, not a Mac login name or a lobby nickname.
- **A Daggerfall-scale land**: not one 1000x1000 map but a generated world of many regions, with countless places, persisted as players touch it (section 11).

Targets, in order:
| Stage | Players on one world at once | Realms | Land |
|---|---|---|---|
| Phase 1 | 10 | 10 | the current map (4 layers of 1000x1000) |
| Phase 2 | 50 | 50 | several generated regions on one server |
| Phase 3 | 200+ | hundreds | thousands of regions over many servers |

Uptime target from phase 1: the world is up 24/7 with a nightly maintenance window; a crash loses at most 5 minutes (section 3).

## 2. Server topology

**Today** (`mac-app/launch.zsh`, `mac-app/Launcher.m`): `Robust.Server.dll` runs the compiled game (`Cave Crawlers.json`) with `auth.mode=0` (no accounts), `net.bindto`, port 12151, `hub.advertise=false`; the local `Robust.Client` connects to it. "Host for friends" writes `join-password`, `host-addresses` and `host-name` into the world folder; `Joining.dm`'s `RemasterJoinGate()` asks every non-host client for the password. The browser path (`planning/WEB_CLIENT.md`) runs one headless `Robust.Client --headless` per web player on the hosting Mac, with the relay module `engine/webview-relay/` serving the HUD page over HTTP and WebSocket, started by `tools/web_host.py`.

**Then:**
```
                 +-----------------------------+
 Mac app  --udp--|  Game server (Linux, .NET)  |--+
 (native client) |  Robust.Server + OpenDream  |  |  per region shard (phase 3)
                 +-----------------------------+  |
 browser --ws--> relay client (headless) --udp-----+
                 (one per web player, on relay hosts)
 launcher/lobby --https--> account service (login, tokens, which shard)
```
- **Dedicated server on Linux.** `Robust.Server.dll` and `OpenDreamRuntime.dll` are .NET assemblies and run on Linux with the linux-x64 .NET 10 runtime; the server folder already carries 4 `.so` next to its 4 `.dylib` natives (`../replica/runtime/macos-x64/server/`, counted), so the native deps have Linux builds. To do: a `tools/build_server_linux.py` that packages the server folder with a linux-x64 dotnet, and a `systemd` unit. Not yet tried; the first run will tell.
- **The Mac app becomes a client only.** `Launcher.m`'s Play / Host / Join gains "Play online": it fetches a token from the account service and starts only the client with `--connect-address` and the token. Local solo play and LAN hosting stay as they are.
- **The web client** stays "one relay client per browser player", but on relay hosts next to the server, not on a player's Mac. Its cost is the expensive part (section 8), so native clients first.
- **Joins:** today one password for the whole world; then a per-player token checked at login (section 4).

## 3. Persistence

**Today:**
- The world is 4 layers of 1000x1000 tiles loaded from `game/Maps/*.dmm` (2 MB ground map; 1 MB each for underground, sky, hell). `Code/Remastered/WorldSave.dm` saves only what changed: tiles that differ from the map in 16-tile chunks players have visited, items and workshops made during play, calendar and land history, to `units/remaster_world.sav`.
- Each player's army is a separate save (`units/localhost@<name>_save.sav`, keyed by connection address and name) written by `SaveUnits()` (`Code/Saves.dm`), every 950 s (`CallSave()`, `spawn(9500)` at 10 ticks/s) and on quit.
- A save freezes the game for 1.6–2.4 s (notes, soak test). Open bugs from the soak test (notes): after a long war run 27 of 46 units reloaded with no location; one workshop kind and about 40% of ground items don't survive a reload; ground items grow during fights.

**Then:**
- **Fix the reload bugs first.** They are blockers: an MMO reloads the world every restart, and a lost village is a lost player. Tests: extend `tools/check_siege_save.py` with a long-war-then-reload case; add a ground-item count-and-reload check.
- **Save without freezing.** Save by chunk, a few chunks per tick, write-behind, so no tick stalls: `RemasterSaveWorld()` becomes a scheduler over `remaster_chunks`, dirty chunks first. Player armies save on logout and every few minutes, one player per tick.
- **A database instead of .sav files.** `Microsoft.Data.Sqlite.dll` is already in the server folder; the DM side keeps writing JSON blobs (one per chunk, one per player) through a small server verb or file, and a sidecar process (`tools/world_db.py`) moves them into SQLite/Postgres with versions, so a crash restores the last consistent set and a bad save can be rolled back. Target: lose at most 5 minutes.
- **Keys.** Everything owned (units, items, workshops, claims, `rm_lieges`) is already stored by player key, never by object link (`WorldSave.dm` header). The key changes from `localhost@kiwimango` to an account id (section 4); a one-off migration renames keys in the saves.
- **Regions** (section 11): the world save becomes one file set per region, diffed against what the generator produces for that region's seed, so an untouched region costs nothing.

## 4. Accounts and identity

**Today:** `auth.mode=0`; the client's `--username` is the Mac login name (`launch.zsh`); the player's key and save name come from it; the browser lobby takes any name typed (`WEB_CLIENT.md`, "Not done yet"). Anyone who knows the host's address and the one password can log in as any name.

**Then:**
- **An account service** (small, outside the game: `tools/account_service.py` to start, a real service later): sign-up with e-mail or a third-party login, password hashing, a session token per login, and which world/shard the player's realm lives on.
- **Tokens at the gate.** Keep `auth.mode=0` at first (Robust's own auth mode expects Space Station 14's auth server) and check a per-player token in `RemasterJoinGate()` instead of the shared password: the client passes it the way `DM_JOIN_PASSWORD` travels today (`MacWebViewManager.AnswerJoinPassword`, the relay's `DM_JOIN_PASSWORD`), the server asks the account service once per login (an HTTP call from DM goes through a server-side helper, since DM itself has no HTTP; a small `tools/token_check` sidecar answering over the topic port, or the server reads a signed token with a shared secret so no call is needed). Signed tokens (HMAC, short-lived) are the simpler first step.
- **The key is the account id.** `RemasterWho()` / the save name come from the token, not the client's `--username` (`Joining.dm`, `Saves.dm`); `RemasterTakeName()` keeps the house name as the display name.
- **Later:** move to Robust's `auth.mode` with our own auth server implementing its two endpoints, which also gives encrypted sessions.

## 5. The engine's limits, and how many players one world carries

DM runs on one thread, one world tick at a time; OpenDream interprets it. Numbers from the 2026-10-20 soak (notes): about 60 units, every workshop, a rival realm at war, sieges and raids, with one player's 3D view on: the server holds 10 ticks/s at normal speed, but at speed 2 and 3 reaches only about 14 ticks/s. So one tick of that world takes about 70 ms (**estimate** from 14/s), against a 100 ms budget at normal speed. The per-player 3D builder (`Remaster3DTick`: terrain about 40 ms, things about 11 ms per call, notes) and the HUD are 15–20% of it and run per game tick for each connected player.

From that: about 1 ms of tick per unit (**estimate**: (70 − 12) ms / 60 units), and about 12 ms per connected player for the scene and HUD. A world at normal speed can carry roughly:
- 80 units and 2 players today (**estimate**), which is 10 players only if each has 8 units;
- a Kingdom is 35+ people (`Code/Remastered/Progress.dm`), so 10 realms is 350+ units, four times the budget.

What has to change, in order of payoff (all **estimate** until profiled):
1. **Take the 3D scene and HUD off the tick.** Build the scene only when something in view changed, cache terrain per 16-tile chunk (the same chunks as `WorldSave.dm`), send things as deltas. Saves about 12 ms per player per tick: with 50 players that is the whole budget on its own.
2. **Run villages at the pace they need.** Units far from any player, and whole realms whose player is offline, tick at 1/5 or 1/10 of the rate (the original's per-unit `spawn` loops become one scheduler with per-unit intervals), and sleeping or idle units skip most of their step. The abstract catch-up in `Away.dm` is the low-fidelity simulation for offline realms (section 7).
3. **Profile the original AI.** The per-unit cost is in the original's loops (`Code/Creatures/*.dm`: wandering, hunger, combat scans with `range()` and `view()`), not in the Remastered code; `tools/check_world_soak.py` plus OpenDream's profiler will show the top ten procs. Expect 2–3x from fixing the worst scans.
4. **Shard by region** when one process is full (section 11): each region is a world on its own server process; a gateway tells the client which to connect to; moving between regions transfers the player's army as its save blob.

Targets after 1–3: about 300 units and 50 players per process at 10 ticks/s (**estimate**). Beyond that, shards. The honest risk: if OpenDream's interpreter cannot be made 3x faster per unit, phase 2 needs sharding already, and the 50-player world is 2–3 processes.

## 6. Server authority and cheating

- **HUD commands** arrive as `byond://?rm=...` and go through `client/Topic` in `Code/Remastered/HUD.dm` → `RemasterHUDSelectionAuthorized` → `RemasterTouchCommand`. Unit references resolve through `RemasterUIUnit()` (`Code/Remastered/UIIdentity.dm`), which only returns units with `M.Owner == src` in the player's own `UnitList`, so the HUD path is already owner-checked.
- **Original verbs and clicks** are not: everything in `Code/Verbs.dm`, `Code/Click.dm` and the creatures' verbs trusts `usr`. Audit every `verb/` and `DblClick`/`Click` handler for "does `usr` own this?" and "is it in range?"; the `Admin` type's verbs (`Code/Saves.dm` `Admin/verb/SaveUnitsInWorld` and friends) must be granted by account role, never by name.
- **Speed and pause** (`Pause and game speed`, notes) are per world today; in an MMO they are the server's alone: remove the client's power to change them.
- **Rate limits** on `Topic`: a client sending thousands of commands a second must be throttled (count per tick, drop past a limit) so one player cannot stall the tick.
- **Trust nothing from the page**: the HUD page is served by the server but runs on the client; its JS can be changed. All rules stay in DM (they are), and the server should ignore any `rm` command for units not selected by the same player (it does, via `RemasterHUDSelectionAuthorized`).
- Tests: `tools/check_multiplayer.py` gains an "Eve sends commands for Alice's units" case (expect refusal, no effect), and a flood case.

## 7. Offline realms when the world never stops

Today `RemasterTrack()` runs only for connected players (`QoL.dm` `RemasterLoop`), and `Away.dm` replays up to 8 hours at half pace in at most 12 s of real time on login. In a world that never stops, an offline realm must still exist for others: its walls stand, its guards fight, its food runs down.

Rule: **sleeping realms, woken on contact.**
- A realm with no player online is "sleeping": its units do not run their full AI. Every N minutes the server runs `Away.dm`'s catch-up for it in place (eat, sleep, work, stock), so when the player returns there is nothing left to replay; `REMASTER_AWAY_MAX` (8 h) becomes "sleep forever, at the away pace".
- When an enemy unit enters a sleeping realm's claim (`Claims.dm`), the realm wakes: its units run the full AI, guards and defense (`Defense.dm`) work, siege rules apply. It sleeps again a few minutes after the last enemy leaves.
- Protection: a realm is immune to raids by other players for its first 3 days of play, and for the first 12 hours after its player logs off, and a player can be raided at most once per 24 hours while offline (numbers to tune). Wars still need a declaration (`War.dm`), and the war strip tells the player on return what happened (the "While you were away" card already lists events).
- The "away" card becomes a log of the time asleep, built from the same events.

## 8. Hosting: machines and cost

From `planning/WEB_CLIENT.md` (**measured** 2026-10-22 on this Mac, x64 under Rosetta, no ReadyToRun): the server uses 1.5–2.7 GB; a relay client for one web player uses about 300 MB and 45% of one core. Native app players cost the server only. Linux native x64 with ReadyToRun should cut the relay client to roughly half (**estimate**).

| Players at once | Servers | Relay hosts (if all on web) | Monthly (**estimate**, cloud list prices) |
|---|---|---|---|
| 10 | 1 × 4 vCPU / 8 GB | 1 × 8 vCPU / 16 GB | $50 server; +$80 relay |
| 50 | 2–3 shards × 4 vCPU / 8 GB | 3 × 8 vCPU / 16 GB | $150; +$250 relay |
| 200 | 8–12 shards | 12 × 8 vCPU / 16 GB | $600; +$1,000 relay |

Plus the account service and database (small, $20–40) and bandwidth (the client receives the scene as JSON; a few KB/s per player at rest, more in sieges; measure in phase 1). The web client doubles the bill; keep it optional and native-first.

## 9. Roadmap

**Phase 0, prerequisites (1–2 weeks):**
- Fix the three reload bugs (section 3). Files: `WorldSave.dm`, `Saves.dm`; tests in `tools/check_siege_save.py` and a new `tools/check_reload_long.py`.
- Linux server package (`tools/build_server_linux.py`) and a 24-hour unattended run with bots (`tools/check_world_soak.py` extended with `--hours`).
- Risks: an engine native dep without a Linux build; the reload bug's cause being in OpenDream's serializer rather than in game code.

**Phase 1, a persistent server for 10 players over the internet (3–4 weeks):**
- Tokens at the gate instead of the shared password (`Joining.dm`, `Launcher.m`, `launch.zsh`, `MacWebViewManager.cs`), the account id as the player key (`Saves.dm`, `RemasterWho`), the account service with sign-up and login.
- Save without freezing, write-behind to SQLite (`WorldSave.dm`, `tools/world_db.py`).
- Sleeping realms (`Away.dm`, `QoL.dm`, `Claims.dm`, `Defense.dm`), raid protection rules.
- Verb and click audit for ownership (`Verbs.dm`, `Click.dm`, the creatures' verbs), admin by role, `Topic` rate limit (`HUD.dm`).
- Server-only speed and pause.
- Tests: `check_multiplayer.py` with 10 bots for 2 hours, Eve-commands-Alice, the flood case, save-and-restart with 10 realms. Risks: the tick budget with 10 real realms (expect to need item 1 of section 5 already).

**Phase 2, 50 players, a generated world (6–8 weeks):**
- Scene and HUD off the tick, per-chunk terrain cache, deltas (`View3D.dm`, `HUD.dm`, the page's `update3D`).
- Unit scheduling by distance and realm state; profiling the original AI loops.
- The region generator and region travel (section 11), the region map in the HUD's world map.
- The web client on relay hosts, with the lobby as part of the account service.
- Tests: a 50-bot soak; a 10-region world reload. Risks: interpreter speed (the honest one; if 300 units per process is not reached, shard in this phase).

**Phase 3, 200+ players, thousands of regions (open-ended):**
- One server process per group of regions, a gateway that maps regions to processes, cross-process transfer of a player's army (its save blob), chat and markets across shards.
- Operations: deploys without downtime (drain a shard, move its regions), backups, monitoring.

## 10. Positioning

"The first RTS MMO" is not a claim that holds: Shattered Galaxy (2001) is usually credited as the first MMORTS, and others followed. What is true and rarer: a colony-building RTS, block-by-block mining and building in 3D, in one persistent world with everyone else, free, from a game that died on BYOND years ago. Say: "a persistent-world colony RTS you play with everyone", "an RTS MMO", "a dead BYOND game rebuilt as an RTS MMO". The video and the store text should use those.

## 11. The world as Daggerfall: regions, generation, travel

Daggerfall's land is about 160,000 km² with thousands of generated towns and dungeons. Our map is 1000x1000 tiles per layer (`WorldSave.dm` header), hand-placed in `game/Maps/`, with the biomes (`Biomes.dm`: mesa, ashlands, tundra, mushroom and so on, placed at boot with a fixed seed) and 38 cave mouths leading to instanced caves (`Instances.dm`: themed, generated fresh in sealed rock on the Depths layer, wiped when empty). So the pieces of a generator exist: biome placement, instanced dungeon generation, cave themes with bosses and treasure, and a diff-based world save.

Design:
- **A region is the current map's size**: 1000x1000 tiles, four layers (ground, underground, sky, hell as today). The current hand-made map becomes region (0,0), the capital region.
- **Regions come from a seed.** A generator (`Code/Remastered/WorldGen.dm`, new) makes a region's terrain, mountains, rivers, lakes, biomes, forests, ore, cave mouths, dragon lairs with hoards (the dwarf-fortress-and-dragon-lair story of the video is exactly this), ruins and monster camps, from `hash(world_seed, rx, ry)`, so the same region is always the same. The generator runs on an empty z-level set, not from a `.dmm`: the engine adds z-levels at runtime. **Verified 2026-10-22** (`tests/maxz_test.dm`, run with `tools/check_breaking.py --entry MzRun --extra tests/maxz_test.dm`): in the 120x100 arena, `world.maxz = maxz + 1` took 5 ms and the new level took a grass turf, an item and a unit that moved on it; four more levels took 56 ms; widening the world by 50 columns (`world.maxx += 50`) took 109 ms; the old tiles were untouched. Scaled to a 1000x1000 region that is roughly 0.4 s per layer and under 2 s for a four-layer region (**estimate**, linear from the arena), which fits in a background generation step before a party arrives.
- **Loaded on demand.** A region is in memory only while a player or a woken realm is in it; `WorldSave.dm`'s chunks diff against the generated region, not the map file, so untouched regions cost nothing on disk. Memory: 4M tiles take about 1.5–2.7 GB today (notes), so one process can hold perhaps 4–8 regions in 8–16 GB (**estimate**); more than that is a shard.
- **Travel.** The world map (`#worldmap` in `remastered.html`) becomes a region grid like Daggerfall's travel map: pick a region, your army travels by road or caravan, time passes (the `Away.dm` pace), and the army arrives at the region's edge. Walking off a region's edge enters the neighbour. If the neighbour lives in another process, the army goes as its save blob and the client reconnects (phase 3).
- **Places.** Every region gets named places from the generator: towns of other races (the original's monster races as NPC settlements, trading through `Market.dm`), lairs, crypts, hellgates. Thousands of regions is thousands of places; the generator's quality is the content budget, so it gets its own test (`tools/check_worldgen.py`: a region generates in under N seconds, is reachable, has the counts it promises).
- **Claims and realms** are per region (`Claims.dm` keys gain the region), and a realm's rank can span regions later (vassal towns in the next valley).
- **Building upward.** Today a surface building can rise one storey: the Sky layer (z 3) above the ground takes floors on supported tiles and the wall-walks (`WallWalks.dm`; the 3D view draws it as "upper floors", `View3D.dm`), and inside rock a hall's ceiling can be raised to 6 blocks. The user wants to build "as high as you want" on the surface. That needs more layers above the ground, which is the same engine step as regions: z-levels added at runtime, each a storey, with stairs between them and the 3D view stacking them (it already stacks ground, sky and below). Put it in phase 2 with the generator, since both stand on growing `world.maxz`.

Order: the generator and one extra region on the same server in phase 2; many regions and travel across processes in phase 3.

### What to take from Daggerfall Unity

The user asked (2026-10-22) about "a Daggerfall online we can copy". The open-source base is **Daggerfall Unity** (dfworkshop.net, GitHub `Interkarma/daggerfall-unity`, MIT-licensed C#, 1.0 released 31 December 2023), a single-player re-implementation that reads the original game's data files. Two multiplayer builds of it exist (found by search, repositories still to confirm with the user):
- **Daggerfall Enhanced** (news from late September 2026): an open-source port of Daggerfall Unity with a persistent online server: one world clock for everyone, shops open around the clock, the original's 250+ quests playable together, reportedly a browser build, and the player must supply the original game data. This is the closest thing to "Daggerfall online" and the one to study for the server side: how it keeps one world time and one world state for everyone, how it decides who has authority over an enemy or a shop, and how it handles a player's data.
- **Daggerfall Unity Co-op** (GitHub `Visty93/Daggerfall-Unity-Co-op`, built on DFU-Tanguy-Multiplayer, on DFU 1.1.1): co-op with shared quests, enemies spawned by the host and a "dynamic authority" system (whoever is nearest owns the simulation of a thing). The authority idea maps onto this plan's sleeping realms and region shards: the server process that holds a region owns everything in it.

What can be copied is the **design and code** (MIT), not Bethesda's data, names or art (the original game is free to download but its content is still Bethesda's, and the user's own game already had to drop a borrowed name once).

Its world system, and what each piece becomes here:
- **A world grid of "map pixels"** (1000 x 500 for Daggerfall, each about 800 m): a climate, a terrain height and, for some pixels, a location. Here: the region grid of section 11, each region a 1000x1000 map, with climate and height from a world-scale noise function so coasts, mountain ranges and deserts span many regions.
- **Terrain streamed around the player** from the heightmap plus per-pixel noise, only the tiles in view loaded. Here: regions loaded on demand (already in the design) and, inside a region, `WorldSave.dm`'s 16-tile chunks generated lazily so a region costs little until walked.
- **Locations as block layouts**: towns and dungeons are assembled from a library of prebuilt blocks (RMB town blocks, RDB dungeon blocks) chosen and rotated by the generator. Here: a block library in DM for NPC towns (an orc stronghold's blocks, a human market town's, a dwarf hold's), lairs and crypts; `Instances.dm` already generates themed caves and is the seed of this.
- **A travel map with time**: pick a place, choose speed and whether to camp, and days pass. Here: the region map in `#worldmap`, travel by road or caravan at the `Away.dm` pace, arriving at the region edge.
- **Deterministic from a seed**: everything regenerates the same, so only changes are saved. Here: already the plan; their code shows the practical seams (location placement vs. terrain, how blocks are positioned at pixel borders).
- Read first in their repository: the terrain sampler and streaming (`Terrain`/`StreamingWorld`), the location layout (`RMBLayout`, `RDBLayout`), the travel map, and the climate/season handling. Multiplayer is not there; that part is this plan's own.

## 12. Towns and heroes: how a Daggerfall-size world fits this game

The user's framing (2026-10-22): "players are the towns themselves, while also carrying around their own heroes." So every player is two things at once, and the huge world is where the second one goes.

- **The town** is the player's realm in its home region: today's game. It runs in full while they are online and is a sleeping realm woken on contact while they are away (section 7), and while their heroes are away in another region.
- **The heroes** are a party of a few named units from that town (the ruler, champions, a doctor, a hauler for loot) the player takes out into the world. They are the same units as in the village, with the same skills, gear, spells and the tabbed unit card as their hero sheet, so there is no separate hero mode (the old Hero mode was removed on 2026-10-21 in favour of always-Village; this brings heroes back as a party inside the village game, not as a mode). A party is 3–8 units, so a region full of visiting parties stays inside the tick budget of section 5.
- **The world beyond** is the generated land of section 11: a town is anchored in one region, everything else is generated from its seed and loaded only when a party goes there, so a Daggerfall-size map costs nothing until it is visited. The travel map shows regions, the places the player has found and their active quests; travel takes time at the away pace, and the party arrives at the region's edge, or at its destination by road or caravan.
- **Procedural quests**, the way Daggerfall does them: templates with slots (a place, a person, an item, a monster, a reward) filled from the generated world. Quest givers are the NPC towns the generator places (the original's other races as settlements, trading through `Market.dm`) and the player's own Bulletin board (`Board.dm`). Six templates to start: clear a lair or crypt; hunt a named beast; escort a caravan to another region; recover an item from a dungeon; rescue a captive (ties into `Capture.dm`); deliver N goods (ties into the market's needs). Rewards go back to the town: coins into the realm treasury, rare gear, a dragon egg or a soul stone, migrants who join the town, and reputation with that NPC town that opens trade and alliance. Quest state is saved per player; quests expire; a region's quests regenerate from its seed and the date so two players can get different ones.
- **Between players**: parties meet in regions, to clear a lair together or to fight; NPC towns are shared; and other players' towns are destinations on the map, to trade with, visit or raid (under the protection rules of section 7). This is where "RTS" and "MMO" meet: the town is the base, the party is the character.
- **In the engine**: a party moving between regions is the per-player army save blob of section 3 moved to the region's process (section 11); the town stays where it is. The hero sheet, skills and combat already exist; what is new is the travel map, the party as a saved unit of its own, the quest templates and the NPC towns.
- **When**: phase 2 with the generator (one extra region, the travel map, the six quest templates, one NPC town kind); phase 3 for travel across shards and the full spread of towns and dungeons.
