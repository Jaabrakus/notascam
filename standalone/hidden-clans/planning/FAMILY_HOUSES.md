# Families, houses and heirs (plan)

Planned 2026-10-17. Remastered only; Classic stays untouched. Inspired by
Crusader Kings: a player can play one **hero** (their ruler) or run a whole
**village or city**, and over generations both become one **house**.

## What the game already has

| Piece | Where | Notes |
| --- | --- | --- |
| Breeding and births | `Code/Creatures/Breeding.dm` | Pair two units, children are born (eggs for some races). Children get 1/6 of each parent's skills. Kobolds have 2, Ratmen 3. |
| Parent links | same file | `CHILDMALE` / `CHILDFEMALE` are **tmp** on purpose: the author kept them out of saves to avoid duplicate units. After birth, nothing remembers the parents. |
| Ruler | `Code/Items/Crowning.dm` | One King and one Queen (`IsRoyal`) with stat bonuses. If one dies or steps down, there's a one-hour wait before declaring another. |
| History | `Code/Creatures/Death.dm` | `Legends` logs each death: date, age, level, killer and cause. |
| Saves | `Code/Saves.dm` | `M.Write(S)` saves the player with its `UnitList`, so every unit is inside one savefile. |
| Unit ids | `Code/Remastered/UIIdentity.dm` | `remaster_ui_id` is per session only (tmp). It can't be used for lasting links. |

## Rules for the new layer

1. **Store ids and names, never object references.** A saved reference from one unit to another is how duplicate units happen. All family links are text ids plus a copy of the name, race and gender.
2. **Don't change breeding.** Who can breed, timings, skill inheritance and egg behaviour stay as they are. Families only record what already happens.
3. **Old saves must load.** Units without family data become founders of their owner's house (generation 1, parents unknown).
4. **The dead stay in the tree.** A capped family ledger on the player keeps records of dead relatives.

## Phase 1: saved lineage (the foundation)

New saved vars on `mob/Monsters`:

| Var | Meaning |
| --- | --- |
| `remaster_uid` | Lasting id, for example `u-<realtime>-<counter>`. Assigned once at creation or on first load. |
| `remaster_house` | House id. |
| `remaster_father`, `remaster_mother` | Parent uids (text). |
| `remaster_parent_names` | `list(father name, mother name)`, so a link still reads well if a parent's record was trimmed. |
| `remaster_born` | Game date and year at birth (`Date`, `Ages`). |
| `remaster_generation` | Founder = 1, child = max(parents) + 1. |

Saved on `Player`:
- `remaster_houses`: house id → name, banner, founder uid, head uid, founded date.
- `remaster_ledger`: uid → a small record for each dead relative (name, race, gender, house, parents, born, died, cause, killer, level, generation). Capped at about 500, keeping direct ancestors of living members first.
- `remaster_ruler_uid` and `remaster_heir_uid`.

Hooks (each a single call added to the original code):
- `GiveBirth()`: after each `CHILD` is made, call `CHILD.RemasterRecordBirth(FATHER, MOTHER)`. It sets uid, parents, house, generation and birth date, and posts a "born to House X" event.
- **Eggs:** at `Breeding()` time, copy the parent uids onto the egg in saved vars. A save and reload during incubation then keeps the parents, whereas the original falls back to "own parent".
- `Death()`: before `del(src)`, call `RemasterRecordDeath()`. It writes the ledger record and triggers succession if the ruler died.
- `LoadUnits()`: assign uids and founder houses to units that have none (old saves).
- **Ownership change** (capture, gift, werewolf): house membership stays. The tree marks the unit as "serves another lord".

Checks (`tools/check_family.py`, in the style of the existing in-world suites):
- A child born from two parents has their uids, the father's house and the right generation.
- Save and reload keep every link, with **the same number of units** (the duplicate-unit guard).
- An old save gets founder data. A death writes one ledger record. An egg keeps its parents across a save.

## Phase 2: houses

- **Founding:** when a player chooses their race, a house is founded with a name drawn from per-race lists, for example:
  - Orc: Bloodtusk, Ironjaw
  - Human: Ashford, Blackwood
  - Dwarf: Stonebeard
  - Elf: Silverleaf
  - Goblin: Mudfang
  - Lizardman: Scalecrest

  The player can rename it.
- **Banner:** two colours plus an emblem from the game's own icons. It shows on the hero frame, the outliner and the tree.
- **Inheritance:** children take the father's house by default (the mother's for egg-laying races where only the mother is known). Whether this should be a choice per house is an open question below.
- **HUD:** the top-left realm block shows "House Bloodtusk", with the banner and the ruler's portrait. The outliner can group units by house and by job.

## Phase 3: family tree panel

A new **Family** page in the left panel, also opened from the hero frame:

- **Rows:** grandparents, parents, then the focus unit with partners and siblings, then children and grandchildren.
- **Portraits:** living relatives use the existing HUD portraits. Dead relatives show a greyed race silhouette with dates.
- **Click** a portrait to recentre the tree on them. **Hover** shows name, age, house, born and died dates, cause of death, level and top skills.
- **Markers:** a crown for the ruler, a small banner for the heir, and a skull for the dead.
- **House view:** name, banner, founder, current head, living and dead members, generations, and total kills.
- **Data:** the server sends the tree only while the page is open (`remaster_family_focus`), not on every HUD tick.

## Phase 4: heirs and succession

**Built (2026-10-17):** `Code/Remastered/Succession.dm`, check `tools/check_heirs.py`. The head of the family is the hero (chosen in Lineage or the hero frame; else the King or Queen). Crowning stays the original Declare Leader with its one-hour wait (open question 1 left as the original).

- **Heir rule** (default, close to Crusader Kings primogeniture), always among living units the player owns:
  1. Eldest living child of the ruler.
  2. Eldest living sibling.
  3. Eldest living member of the house.
  4. Anyone the player picks, who founds a new house.
- **Choosing an heir:** the player can name a different heir from the tree ("Designate heir").
- **When the ruler dies:** an event window says "The King is dead. Long live ..." with a **Crown heir** button. That uses the existing `AddLeader()`, so crown and stat rules stay the same.
- **Hero mode:** the hero is the ruler. When the hero dies, the hero frame moves to the heir, so the player keeps playing the family.

## Phase 5: polish

- Styled event windows for births, deaths, coming of age (Age 5, when breeding becomes possible) and succession.
- `Legends` entries carry the house name.
- Nested tooltips in the tree.

## Open questions for the user

1. **Succession wait:** should the rightful heir skip the one-hour wait for a new King or Queen? The wait exists in the original game today.
2. **House inheritance:** father's house by default, or a choice per house (matrilineal)?
3. **Partners:** should partners who had a child together be remembered as a couple ("spouse") in the tree? There is no marriage in the game today.
4. **Captured units:** when a unit from another house joins you, does it keep its house or join yours?

## Order of work

Phase 1, then 2, 3, 4 and 5. Each phase ends with its checks, a save/reload test with the unit count unchanged, and a real-window screenshot.
