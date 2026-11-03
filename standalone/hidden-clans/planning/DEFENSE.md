# Automatic defense

Target: the active **Remastered** game. Classic game rules remain unchanged.

Actual melee attacks and fired arrows trigger the help call, including misses
and blocks. This feature does not infer an attacker from hunger, bleeding, or
other damage-only effects. Other spell-specific triggers have not been added.

Automatic defense is a temporary interruption of a unit's work. The unit card
shows **Responding** or **Returning** while keeping its previous task and pending
queue visible. Deselecting the unit leaves its work and response running.

## Unit setting

The **Automatic defense** selector is on selected unit cards in both **Units**
and **Orders**. It changes that unit only; the existing Hold, Guard and Aggressive
commands remain separate.

| Choice | Behavior |
| --- | --- |
| **Help nearby** — default | Defend itself, call nearby helpers, and answer calls from units with the same owner. |
| **Defend self** | Respond when attacked and call nearby helpers, but do not leave work to answer their calls. |
| **No response** | Disable automatic responses and calls for help. Direct combat orders remain available. |

Helpers hear attacks within **8 tiles**, in every direction, on the **same map
level**. Walls do not block hearing; the unit still needs a route to reach the
threat. Hearing a call does not permit walking through a wall.

Pursuit stays within 8 tiles of the original **alarm site**, and lasts at most
20 seconds before returning. The return to the unit's previous position has a
10-second limit; a blocked return also ends the response. Previous work then
resumes from the unit's current position. The UI keeps that task under
**Work to resume** during the interruption; queued tasks retain their order.

Paused, stopped and held units do not answer calls. Direct Stop, Pause or a new
**Do now** command cancels a response and gives that command 10 seconds of priority before
automatic defense can interrupt again. A paused autonomous role is unavailable
as a helper; an idle Manual unit can still help. **Add tasks** appends work without
interrupting the response.

## Data and requests

`mob/Monsters.RemasterDefenseData()` supplies each unit's `defense` object:

```text
mode: assist | self | off
state: Responding | Returning | Help nearby | Defend self | No response
responding: boolean
target: display name or empty string
radius: 8
```

The saved mode is `remaster_defense_mode`, defaulting to `assist`. An active
temporary response is held in `remaster_defense`.

The browser sends `defensemode` with `unit-ref|mode`. The server verifies the
unit's type, ownership, membership in the player's unit list, and allowed mode
before calling `Player.RemasterDefenseMode`. A selection change cannot redirect
an already-issued card request to another unit.

## Verification

- [x] HUD modes and exact unit/mode request contract.
- [x] Responding and Returning display with previous task and pending queue.
- [x] Live updates retain selector identity and keyboard focus.
- [x] Escape in the selector does not deselect the unit.
- [x] Touch target and layout at 320, 390 and 768 pixels.
- [x] Existing HUD controls and original border catalog remain covered.
- [x] Core response, range, pursuit and return tests.
- [x] Server mode validation and task-identity preservation tests.
- [x] Packaged-game source/runtime checks and normal-save native startup.

`tools/check_easy_orders_hud.py`: **56 checks passed**, zero browser errors.
These are browser rendering/request tests; they do not simulate combat or claim
native gameplay coverage. The preview is `tests/defense-hud.png`.

Final integration verification: **103 defense checks passed** using real Human
and Orc game constructors, actual melee and arrows, and real movement/inventory.
This includes bow cadence and lethal target cleanup, all hearing boundaries,
wall routes, interrupted deliveries, returns, mode serialization, and server
request validation. The existing **72 order**, **33 settlement**, and **32 combat**
checks also passed with no runtime errors.

The canonical app was rebuilt, checked against current source, and reopened
with the normal Kiwi save. Its client reached InGame and loaded the HUD and 45
active border images without missing resources or client/server errors. This
startup check is passive; the combat scenarios were exercised in isolated real
game worlds. Shared engine binaries are unchanged by this feature.

The prebuild save already had an empty UnitList. It is preserved under
`restore-points/before-nearby-defense-20261016/player-units/`. The earlier
`before-border-menu-animation-20261016/player-units/` backup contains three Orcs;
it was not restored over the user's current save.

Evidence: `tests/defense-checks.json`, `tests/combat-defense-checks.json`,
`tests/easy-orders-defense-checks.json`, `tests/settlement-checks.json`,
`tests/easy-orders-hud-checks.json`, `tests/defense-package.json`, and
`tests/defense-normal-launch.json`.
