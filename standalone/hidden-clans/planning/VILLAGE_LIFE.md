# Village life: homes, the bulletin board, groups and kingdoms (plan)

Planned 2026-10-17 from the user's direction. Remastered only. Builds on
`GAME_GAPS.md` (what's missing) and `FAMILY_HOUSES.md` (lineage).

The aim: villagers keep themselves alive, pick up work without being told,
help each other, and over time families grow into houses that can join a
kingdom, eventually with other players.

## 1. Self-care and homes (first)

What the original game already does: units eat carried food (or food within 5
tiles) when hungry, heal over time, and sleep on a bed within 20 tiles or on a
carried sleeping bag. Starting units carry a sleeping bag.

New in Remastered (`Code/Remastered/Care.dm`), run from the per-player tick
(`RemasterTrack`) about every 3 seconds:

| Need | Trigger | What the villager does |
| --- | --- | --- |
| **Home bed** | Tired with no carried bag | Uses their **home bed**. If they have none, they claim the nearest free bed within 30 tiles; it becomes their home (saved as coordinates). |
| **Sleep rough** | Tired, no bag, no bed | Sleeps where they are, and the status says "Sleeping rough: no bed". |
| **Warmth** | Coldness 40 or more | Walks to the nearest campfire within 25 tiles and stays until warm. If there's no fire, a warning shows. |
| **Food** | Hunger 20 or below, carrying none | Walks to the stockpile if it has food; the original eating then takes over. |

- **Interrupting work:** care briefly takes over a villager. Their orders and job are kept and resume afterwards, the same way sleeping already works.
- **Fighting:** units in a fight never break off to look after themselves.
- **Give-up timer:** if a target can't be reached within 2 minutes, the villager gives up and the status says why.
- **Village tab:** shows each villager's home ("Bed at 12, 40", "Sleeping bag", "No bed") and what care they're doing.

## 2. The bulletin board (next)

- **A board in the village:** a placeable Bulletin Board, plus a **Board** view in the HUD Village tab.
- **Work orders** with a target, quantity, priority and an optional place, for example:
  - Chop 20 wood
  - Mine 15 stone
  - Gather or hunt 10 food
  - Cook 8 meals
  - Build a campfire / carpentry here
  - Haul everything to the stockpile
  - Craft N items at a workshop
- **Standing orders** that refill themselves: "Keep 20 food", "Keep 30 wood", "Keep 5 meals". When the stockpile drops below the number, the board posts a work order automatically. This is the "fill it up themselves" part.
- **Who takes the work:** villagers whose job is **Board worker** (a new role next to Woodcutter, Miner and Hauler), or anyone idle, claim orders that match their skills and tools. They show "Working on: Chop 20 wood (12/20)".
- **Card details:** each order card shows who claimed it, progress, and why it's stuck (no axe, no stockpile, can't reach).
- **Engine:** reuses the existing work engine (`Settlement.dm` roles and production queue, `Orders.dm` tasks), so there are no new movement or gathering rules.

## 3. Group awareness and helping each other

- **"Who is doing what":** the Village roster already has this. Add a Board column (claimed order) and a Care column.
- **Help behaviours,** all short and capped:
  - **Feed:** a villager with spare food walks it to a hungry neighbour who has none (within 15 tiles).
  - **Warm:** someone carrying wood near a cold group builds or refuels a campfire. This is later, needing campfire building from the board.
  - **Rescue:** existing Help nearby defence already answers attacks.
  - **Carry:** haulers pick up items dropped by the injured or dead.
- **Group needs line:** a summary of the group's needs on the HUD, for example "3 hungry · 2 cold · 1 no bed · 4 idle". Each item is clickable to filter the roster.

## 4. Houses and kingdoms (later, multiplayer)

- **Kingdom:** a group of houses with a ruling house. The ruling house's head is the King or Queen, using the existing crowning code.
- **Each house:**
  - keeps its own lineage, homes and board;
  - shares a kingdom board for big projects (walls, defence);
  - shares a kingdom treasury or stockpile.
- **Multiplayer:** a player founds or joins a kingdom as a house. The original clan code (`Clan` verbs) is a starting point. Saved data uses house and kingdom ids, never object references (see `FAMILY_HOUSES.md`).
- **Ideas to explore later:** vassal duties (send workers to the kingdom board), marriages between houses, succession inside the ruling house, rival kingdoms, tribute.

## Order of work

1. Self-care and homes (this change).
2. Group needs line and help behaviours (feed a neighbour first).
3. Bulletin board: manual work orders, then standing orders.
4. Heirs and succession (`FAMILY_HOUSES.md` phase 4).
5. Saving the whole world (`GAME_GAPS.md`), needed before kingdoms make sense.
6. Kingdoms.
