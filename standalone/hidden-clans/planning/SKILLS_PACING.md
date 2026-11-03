# Skill pacing (RuneScape-like)

2026-10-22. How fast skills level, and why.

## How a skill gains

- The game's own numbers stay the source of truth: every swing of an axe adds 0.15 to
  `WoodCuttingSkill` (Bump.dm), a pick 0.1 to `MineingSkill`, a cooked meal 1-2 to
  `CookingSkill`, a craft 1 to the crafting skill, a caught fish its RuneScape XP
  directly (Fishing.dm). A working unit swings about twice a second (its walk delay).
- Once a second `RemasterSkillTick` (Skills.dm) turns that gain into experience:
  `gain × XP per point × rate(level)`, and the level comes back out of RuneScape's XP
  table (level 2 at 83 XP … 99 at 13,034,431).
- `rate(level) = 0.15 + 0.0086 × level`, capped at 1: a sixth of the XP at level 1, all
  of it at 99. In RuneScape the XP an hour grows with the level because you move on to
  better trees, rocks and fish; here the same skill numbers do that job. Before this the
  rate was 1 at every level, so a fresh Dwarf reached Woodcutting 30 in 18 minutes.
- The rate applies only to the per-blow skills, Woodcutting and Mining (`rm_xp_by_blow`).
  A craft, a cooked meal or a built wall is one item and keeps its full RuneScape-sized XP
  (a meal 15, burnt 30; a craft 30; a wall 25), because those skills are limited by
  materials rather than time. Fishing (its own XP per fish) and combat (XP per damage)
  award XP directly and are not scaled.
- Per-item work also takes time now, as in RuneScape (one item every ~3 s): a cook spends
  3 s on each meal (`RM_COOK_EVERY`, FoodRoles.dm) and a station craft from the work board
  takes 3 s (`RM_CRAFT_EVERY`, StationCraft.dm). Before, both happened every half-second tick
  while materials lasted: five meals cooked in under 5 s.

## Expected time, one unit working without a break

| Level | Woodcutting | Mining |
| --- | --- | --- |
| 10 | 8 min | 12 min |
| 20 | 25 min | 37 min |
| 30 | 1 h | 1.5 h |
| 50 | 5 h | 7.5 h |
| 70 | 26 h | 40 h |
| 90 | 150 h | 225 h |
| 99 | 335 h | 500 h |

XP an hour: Woodcutting 6.9k at level 1, 25k at 50, 43k at 99; Mining 4.6k / 17k / 29k.
Real units walk between trees, haul, eat and sleep, so expect 1.5-2× these times.
RuneScape for comparison: 99 Woodcutting is roughly 200-300 hours.

Fishing keeps its fixed XP per catch (RuneScape's table per fish) and a cast every 3 s;
its pace comes from the fish on offer, as in RuneScape. Crafting gives 15-30 XP a
craft and is limited by materials, not time.

## Measured (2026-10-22, private world, three fresh Dwarves)

| Skill | What was measured | Result | Expected |
| --- | --- | --- | --- |
| Woodcutting | chopping with a metal axe | level 2 after ~45 s, 3 after ~50 s more | 43 s, 49 s |
| Mining | miners on a mountain face with hauling in between | level 2 after 51-59 s | 65 s of pure mining |
| Cooking | five raw meats at a campfire, before the per-meal delay | level 2 after the 4th-5th meal, all within 5 s | 15-30 XP a meal |
| Cooking | six raw meats, with the 3 s per-meal delay | level 2 at 9 s (3 meals), 3 at 18 s (6 meals) | one meal every 3 s |

Not measured in game: station crafts (same 3 s guard as cooking, same per-item XP path) and
fishing (unchanged: RuneScape XP per fish, a cast every 3 s). Quirk kept from the original: a
burnt meal trains Cooking by 2, a cooked one by 1, so a level-1 cook levels fastest while failing.

## Work speed

Unchanged: a blow does `max(skill, 12) / 4` damage, so a tree (250 HP) takes about 42 s
at level 1 and 10 s at 99; a rock face (100 HP) 17 s and 4 s. That is the RuneScape
shape too (better level, faster logs).

## Level-up messages

One toast, one line in the Log, one XP drop over the unit per level (Skills.dm
`RemasterSkillDrop`). See NOTES.md for the duplicate that was fixed on 2026-10-22.
