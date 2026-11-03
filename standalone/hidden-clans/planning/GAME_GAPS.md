# What the game does on its own, and what's missing

Checked against the game code on 2026-10-17. ✅ works on its own · ⚠ partly · ❌ missing · ❔ not checked yet.

## Self-care (units look after themselves)

| Need | Status | How it works today | Gap |
| --- | --- | --- | --- |
| Eating | ✅ | Every 40 s hunger drops by 1. At 20 or below a unit eats carried food (cooked meat, grapes and tomatoes first). Otherwise it picks up food lying within 5 tiles, or takes food from a nearby unit. At 10 or below it loses health, and it can starve. (`Creatures/Mob Procs.dm`) | Only works if food exists. Nobody produces food unless ordered (see Work). |
| Sleep | ⚠ | At tiredness 20 a unit walks to a **bed within 20 tiles** and sleeps. Spiders and dragons sleep anywhere. Elves, gargoyles, zombies, Svartalfar and Devourers don't tire. | With no bed nearby they only say "I'm tired!" and later lose health. There's no fallback to sleeping on the ground and no bed assignment. |
| Healing | ✅ | +10 health every 40 s. | |
| Cold | ⚠ | Night and cold ground raise coldness, leading to frostbite damage. A campfire warms everyone within 4 tiles. | Units **don't walk to a fire** on their own, so winter nights can kill an unattended village. |
| Bleeding and injuries | ❔ | Bleeding levels and limb loss exist. | Not checked whether units treat themselves. |
| Self-defence | ✅ | Remastered: Help nearby / Defend self / No response per unit. | |
| Offline | ✅ | Hunger and tiredness only drain while you're connected. | |
| Picking up gear | ⚠ | `FindGear()` exists in the AI code. | Not confirmed for player units. Remastered has an Equip command. |

## Work (what villagers do without orders)

| Area | Status | Notes |
| --- | --- | --- |
| Woodcutter, Miner, Hauler roles | ✅ | Remastered: work within 6 tiles of their area, with priorities, auto-unload and a filtered stockpile. |
| Production queue | ✅ | Remastered: queue crafts on selected units. |
| Farming (plant, harvest) | ❌ | Seeds and planting exist, but only on direct orders. |
| Cooking | ❌ | Kitchens and campfires exist; there's no cook role. |
| Hunting, butchering, fishing | ❌ | Skills and actions exist; there are no roles. |
| Building from plans | ❌ | Building is manual. No "build this blueprint" job. |
| Workshop crafters | ❌ | No role that keeps a workshop busy. |
| Guards and patrols | ⚠ | Guard stances exist and `Patrol()` exists in the AI. There's no patrol-route order for the player. |

The result: a big village will run out of food unless you micromanage. **A food chain (farmer, hunter, cook) is the most important missing piece for "manage a village".**

## Settlement

| Area | Status | Notes |
| --- | --- | --- |
| **Saving the world** | ❌ | Only your units and what they carry are saved. Buildings, dug terrain, stockpiled items and the calendar reset when the game restarts (see `PERSISTENCE_SCOPE.md`). This is the biggest gap for a long-running village or city. |
| Resource overview | ❌ | No count of wood, stone, food or metal in the stockpile. The Crusader Kings-style top bar is planned. |
| Needs alerts | ⚠ | Toasts and attack alerts exist. No row of "3 hungry · 2 cold · 1 idle" icons yet. |
| Housing and bed assignment | ❌ | |
| Population growth | ✅ | Breeding works and is now recorded in houses. |

## Society

| Area | Status | Notes |
| --- | --- | --- |
| Families and houses | ✅ | New: saved parents, partners, houses, and the Village › Lineage view. |
| King and Queen | ✅ | Original crowning, with stat bonuses. |
| Heirs and succession | ❌ | Planned next (`FAMILY_HOUSES.md` phase 4). |
| Mood and happiness | ❌ | Nothing in the game. |
| Friendships and rivalries | ❌ | Only family links. |

## World

| Area | Status | Notes |
| --- | --- | --- |
| Seasons and night | ✅ | A season lasts about 17 minutes. Night affects cold. |
| Raids | ✅ | Each new season sends an NPC army somewhere on the map (`Army()`). |
| Wildlife repopulation | ✅ | `Births()` every minute. |
| Trade and diplomacy | ❔ | Factions and clans exist (clans are multiplayer). NPC trade not checked. |
| Story events and quests | ⚠ | Only the admin "event button" and Remastered's Guide goals. No random story events. |
| Pause and game speed | ❌ | The world always runs in real time. |

## Suggested order

1. **Save the whole world** (buildings, terrain, stockpiles, calendar). Without it, a village can't last.
2. **Survival autonomy:** walk to a fire when cold, sleep on the ground when no bed is near, and bed assignment.
3. **Food chain roles:** Farmer, Hunter/Butcher, Fisher, Cook.
4. **Resource bar and needs alerts** (Crusader Kings-style top bar).
5. **Heirs and succession** (planned).
6. Later: builder/crafter roles, patrol routes, mood, story events, pause.
