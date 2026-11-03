# Second polish pass: controls (polish-controls, 10-27)

Fresh eyes on build 68: every HUD button's command, the key map, and two "tours" of everyday orders in the arena
reading every answer a player gets. The buttons and keys are right; the rough spots were commands that worked but said
nothing, or said something stale or untrue, and patrol points that could be placed where they'd never be walked.

## Done (each proven before/after in the arena, then landed through the lander and its gate)

- **Stop answers** (landed 08:09). Stop (P, the Stop button, the unit card's Stop) now says "3 units stopped." or
  "Durin stopped."; before, nothing. "Stop patrol" with nobody patrolling says so instead of "Patrol stopped.". Pressing
  the number of an empty group says "Group 5 is empty: Ctrl+5 saves the selected units as group 5." instead of
  "Group 5: 0 selected." (whether that press also clears the selection is still your decision; unchanged).
- **Patrol points on another level** (landed 08:12). A point clicked on a wall top, a mountain top or a tunnel below,
  where none of the selected units are, was taken and then never walked: with all points elsewhere the game said
  "1 unit patrolling 2 points." and the unit stood idle for good. Such a point is now refused with the reason.
- **Put them down, Fly higher/lower** (proven and READY, not landed: its landing timed out waiting for test slots
  while the lead's runs filled them; four of its five gate checks had passed and the lander put the files back; the lead
  lands it when slots free up). After putting a carried friend down the card still said "Carrying
  ..."; it now says Idle. The group card's Fly higher / Fly lower now answer ("1 flyer flies higher.").

## Numbers

| Check (build 68) | Result |
|---|---|
| Every HUD button's command has a server handler (headless, 3 models) | 146 of 146 |
| Key map (no 2006 letters, W/S/D don't pan, R silent, P stops, A attack, C/X from both windows) | all pass, no page errors |

| Tour step (arena) | Build 68 | After |
|---|---|---|
| Stop, 3 units | (nothing) | 3 units stopped. |
| The unit card's Stop | (nothing) | Durin stopped. |
| Stop patrol, nobody patrolling | Patrol stopped. | None of the selected units are patrolling. |
| A digit for an empty group | Group 1: 0 selected. | Group 1 is empty: Ctrl+1 saves the selected units as group 1. |
| Patrol route on the level below | "patrolling", then idle for good | point refused, with the reason |
| Put them down: carrier's card | Carrying Dov | Idle |
| Fly higher / lower (group card) | (nothing) | 1 flyer flies higher. / lower. |

**Speed:** none of these touch tick code; each line runs only when its button or key is pressed.

## Needs the owner

- Unchanged from last night: an empty group's digit clears the selection (keep, or keep the selection?); Tab/F5/F7
  2006 keys; own units stacking in melee; care walks wedging on walls; a job doesn't end a patrol
  (devlog/2026-10-26/polish-controls.md).
