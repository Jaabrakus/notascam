# Items, the bag and today's bug list

The health bar now moves with every blow, and deaths play once. Wild units fight where they stand. Every item's menu
offers Pick up, Drag body and Drop all. The bag holds one slot per kind and can combine items by category. Every item
can be one catalogue row, and 386 of the game's own items now are, with nothing lost.

## Needs the user

- Combine ideas still waiting for your pick (sharpen, set a gem, mix a remedy...): `planning/COMBINE_PLAN_2026-10-28.md`.

## Done

- **Your units can use things on themselves (build 113).** You said units should be able to act on themselves, not
  just other things. A held bandage, potion, food or piece of gear now rings the unit holding it too: click it and it
  treats itself, eats, drinks or puts it on. Select one unit and right-click it for its own card: Open its bag, Eat,
  Drink, Treat itself, Put on, and Sleep (in its sleeping bag, to its bed, or rough). Checked windowless: 10 of 10.
- **Dropped beds can be picked up again (build 112).** You dropped a sleeping bag and couldn't pick it up. A click on
  furniture walks your unit there (a bed is somewhere to sleep), and the menu's Pick up sent that same click. Now
  Pick up really picks it up, by the selected unit or the nearest one: beds, sleeping bags, chairs, tables and cages.
  Doors and pieces set into a building are still only walked to. Checked windowless: 8 of 8, including the nearest
  unit picking it up with nothing selected.
- **Adopted all the rest that can move (build 111).** You said "Yes, move all 353": the 2006 weapons and armour,
  furniture, traps, bones, potions, plants and shafts, and the Remastered items, all moved the same way. Their
  values left 24 files. The compiled game was compared kind by kind again: the same, apart from each row's id. 31
  kinds stay where they are: 24 have no values to move, 5 have values mixed with code, and 2 crowns have values in
  two files.
- **Adopted the simple items (build 110).** The 6 ores, 4 ingots, 10 gems, 7 seeds and 6 foods are now rows in the item
  catalogue, under their own names in the code. Only their values moved: name, picture, weight, description and
  their own numbers. Their code (menus, gargoyles eating ore, food going off) stays where it was, and saves still find
  them. Before landing, the game was compiled with and without the change and compared kind by kind: the same,
  apart from each row's id.
- **The full item list:** `art/items/ITEM_LIST.md`. It has every kind of item in the game (792), grouped. For each
  kind it shows its picture, weight, categories, where its values are written, its own code, what makes it in the
  game, and whether it can be adopted (or why not).
- **One row each (build 109):** a new item is one catalogue row plus its picture. A recipe row puts it in the five
  workshops' Craft menu.
- **Combine by category (builds 107-108):** a held poison outlines every weapon and quiver it can coat or tip.
  Proven: a coated longsword went from 23-28 to 27-30 damage, and 10 of 15 arrows were tipped.
- **Bag clicks (build 107):** a left click holds the item or opens its menu; a right click always opens the menu. No
  double-click.
- **Bug list (builds 104-106):** health bar, death once, battle drums, item menus via the nearest or selected unit,
  the War Leap aim arc, and wild units holding their ground.

## Numbers

| Item kinds | Count |
|---|---|
| Weapons and armour from the gear catalogue | 375 |
| Item catalogue rows (adopted today) | 386 |
| Still written in the old files (24 with no values to move, 7 that can't move as they are) | 31 |
