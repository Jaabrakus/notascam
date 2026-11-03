# Scaling toward a Daggerfall-size world with many players (plan)

Written 2026-10-17, after the first stress test. The user's goal: a huge world
(Daggerfall-scale) with thousands of players leading armies, if server cost allows.

## Where we are

| Fact | Value |
| --- | --- |
| Map | 4 layers × 1000×1000 tiles (4 million tiles), loaded from map files |
| Server | One OpenDream process. The game's code (DM) runs on **one thread** |
| Saves | Per-player savefiles plus one world-changes save (WorldSave.dm) |

Stress test (`tools/stress_timing.py`, 200 units, one player, rough 100 ms timer):

| Per-tick system | Cost at 200 units |
| --- | --- |
| Care, board, area tracking | about 5 ms each |
| Skills (after today's fix; was about 130 ms) | about 30 ms per second |
| HUD data for one player | 20–40 ms every 0.5 s |
| 3D feed (when on) | about 20 ms every 0.5 s |
| World save (small test world) | about 33 ms per autosave |

At 200 units one player uses roughly **10–20% of one CPU core** for Remastered's systems, on top of the original game's own AI. So one server today could carry perhaps **5–20 players with mid-size armies**. That's an estimate, to be measured with real clients.

## What "thousands of players" needs

1. **Cheaper per-unit work** (in reach now):
   - Spread unit thinking across ticks instead of every unit every tick.
   - Send only what changed to each player (HUD and 3D).
   - Skip players who aren't looking at a system (no Village data unless the tab is open).
   - Cache everything that doesn't change.
   - **Target: 1000+ units per server.**
2. **A headless dedicated server** that runs without a client, restarts cleanly and keeps the world saved. The world save done today is the first piece.
3. **Sharding, the MMO way:** no single process can run thousands of players. The world is split into **regions or kingdoms**, each its own server process, with:
   - travel between regions (walking off the edge loads you into the next server);
   - a central service for accounts, houses and kingdoms, trade and messages;
   - a database instead of savefiles.
4. **A bigger world:**
   - Daggerfall's size came from procedural generation. Here that means generated regions around hand-made towns and dungeons, created as chunks the first time someone goes there.
   - The world-save design (save only what changed per 16×16 area) already fits this.
5. **Cost:**
   - A region server is a small cloud machine (2–4 cores), roughly **$20–80 a month each**.
   - At about 30 active players per region, 1,000 people online is about 35 regions: **roughly $1–3k a month** plus bandwidth.
   - The 3D feed is the main bandwidth item and needs the "only send changes" work first.

## Order

1. Finish polishing single-player and small-server play (current work).
2. Per-tick optimisation pass, measured with 500–1000 units.
3. Dedicated server build, plus a small multiplayer test (a kingdom of 5–10 players).
4. Region sharding prototype: two regions with travel between them.
5. Procedural regions, a database, a central kingdom service.
