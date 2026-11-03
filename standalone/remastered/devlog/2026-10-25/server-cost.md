# Smoother ticks and a chat that keeps only what matters (server-cost)

**One tick ledger, in the game since 13:1x.** A click's orders now come first in each tick, and the HUD and 3D wait
their turn instead of piling on top. With 200 units and the army ordered every 10 seconds:
- the worst tick went from 134 to 100;
- ticks over 100 ms went from 4 to 0;
- the worst on-screen move update went from 23 to 8 ms.

The HUD and 3D refresh about 7% less often. Every unit's first step lands on the same tick as before.

The chat route is in too: engine v11, then your keep/drop list (Chat.dm). Both reach the app with the next build.

## Done
- **The tick ledger** (`reports/server-cost/tick-ledger.md`; restore point `restore-points/before-tick-ledger-20261025/`):
  - What shares one count per tick: a big order's hand-out, a click's first steps, the click's formation plan and its
    slot markers, and the player's HUD and 3D work.
  - Order work goes first and is capped at 50 ms a tick (formations' choice). The HUD and 3D give way to it.
  - Agreed with formations and world-look.
  - Off switch: `rm_tick_ledger = 0`.
  - First steps after a click: all 380 in the walking test land on the same tick as before. A 2,000-unit queue starts
    about 0.7 ticks later on average, well inside the run-to-run spread; that's the price of the cap.
  - A spot ready for hud-craft's "build when there's room" portraits and icons: `RmOptionalRoom()`.
- **The chat route, in the game: engine v11 (installed by the coordinator), then Chat.dm, your keep/drop list (13:3x;
  restore point `restore-points/before-chat-dm-20261025/`):**
  - Each chat line goes straight to the HUD's chat, instead of into a hidden 2D box that grew all session.
  - Your keep/drop list then decides what shows: limbs lost and by whom, deaths and the killer, attacks on the village,
    captures and escapes stay; stun and sleep messages, blow-by-blow, the old skill-ups and hungry/tired chatter go.
  - Proven on a real Mac client and in a browser: the same lines in the same order, nothing dropped that should stay,
    and one line per new limb injury.
  - It switches itself on only once the keep/drop list is in the game, so installing it first changes nothing.
- **Systems map entry** (`reports/server-cost/systems-map-entry.md`): what each of server-cost's ten do-less-work
  systems decides, when it runs, what it costs and what it could fold into.
- **Found and handed on:** the 0.7-1 s tick after a 2,000-unit click is the formation planner's "stand on its own
  tile" step. Formations is on hold, so it's parked with its fix on `planning/AFTER_FOCUS_QUEUE.md`.

- **The unit grid, engine v12, on (evening; restore points `before-engine-v12-20261025`, `before-grid-on-20261025`):**
  - The engine keeps every unit's place in 16x16 cells as it moves. Creature and attack looks out in the open read the
    cells instead of every tile (about 2.6x faster), and awake land marks one cell instead of looping over every unit
    (2-3x faster).
  - Proven identical to the old way: every look across a 5,000-unit war; random checks every tick; nothing near a unit
    ever put to sleep in a real game.
  - At 5,000 units a war ticks about 15% lighter. A first try ran slower in packed crowds; fixed by using the old scan
    there.
  - Off switch: `RM_GRID=0`. Details: `reports/server-cost/unit-grid.md`.
- **A group action says it once** (19:58; restore point `before-chat-group-20261025`): 203 units told to fly give one
  chat line, "203 of your units start to fly!", instead of 203. One unit on its own still gets its own line.
- **The hidden chat copier is gone** (the relay removal, after a soak with memory flat and no lost lines).

## Next
- The grid's next readers (B3: the 3D moves push, world-look).
