# Combat (2026-10-26)

- Picked up the combat workstream at build 56 (read the handoff, the distilled chats, the combat plan and the ends of
  the Unit sprites and morale-design chats).
- Planned the approved next step, the surround bonus with veterans resisting swarms plus high ground:
  `reports/combat/PLAN_surround_high_ground_2026-10-26.md` (rule table, code points, checks, battle cases, the
  tables the owner will see).
- Found two things in the code: units up on the rock and units on the ground can't fight each other at all (bows
  included), and melee up on the rock ignores height. Both go to the owner as questions.
- Nothing built or changed in `game/` yet; waiting for the owner's go.

## Afternoon: the owner said go

- Built the surround bonus and high ground on a copy of the game, staged in `reports/combat/staged/surround/` (not in
  `game/`). The rules check passes 16 of 16, and the existing combat checks all pass on the copy.
- A probe corrected my morning finding: up on the rock a sword already reaches only a foe at its own height or one block
  down, because a blow is a step at the foe. So the "sword reach 1 block" change isn't needed in the form planned; it
  goes back to the owner as a question.
- Bow moves (Pinning shot) also reach a tile further from above. Without that, trained archers walked off their hill
  to use them.
- Wall and cliff archers planned: `reports/combat/PLAN_wall_cliff_archers_2026-10-26.md`.
- 31 battle worlds and 6 duel runs going for the before/after tables.

| Foes beside a recruit | Each blow lands today | With the surround bonus |
|---|---|---|
| 1 | 27% | 27% |
| 2 | 27% | 32% |
| 4 | 27% | 42% |
| 6 | 27% | 52% |

## Afternoon: the last combat rules for build 58

- Surround and high ground landed, with flanking off. Ten veterans still lose to a hundred recruits, but in a narrow pass
  the mob gets little from surrounding them.
- Morale became a tug of war: a side riding high lands more criticals (the maims) but softer blows; a shaken side lands a
  little less but its rare criticals hit twice as hard. The side that wavers first still wins about half its fights.
- Any unit can pick up any gear now; below the gear's level it works at partial strength, never below half.
- Next build: every fall can be saved. A killing blow drops the unit dying, with a minute for a friend to bandage it, and
  Lethal fighters finish the fallen once the fight around them is over.
