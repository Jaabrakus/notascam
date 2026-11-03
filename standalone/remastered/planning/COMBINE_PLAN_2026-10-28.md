# Combining items by category (2026-10-28)

The owner asked for the bag to "combine anything via catergories" and for "the one click highlight to combine with or use item and right click for the menu". This is built and landed (`combine`, `bag-menu`). It is in build 107.

## How it plays

- **Left-click a bag item:**
  - If the item can be used on something or combined with something, the unit holds it. What it works on is ringed in the world, and the bag items it combines with get a gold outline.
  - Otherwise its menu opens.
- **Right-click a bag item:** the menu always opens. It offers Use on…, the item's own uses (Equip, Eat, Drink…), Drop, Drop all (n) of that kind, and Inspect.
- **There is no double-click.**
- **While an item is held,** click an outlined bag item to combine the two. Right-click or Esc lets the held item go.
- **The bag shows one slot per kind of item,** with a count. The server sends one row per kind, not one per item.

## Categories

Every kind of carried item says what it is **in its own definition**, as a line of category words: `rm_cats = "poison"`, or `rm_cats = "weapon blade"` for more than one. The engine reads it once per kind and caches it (`UseOn.dm RmItemCats`).

A new item joins every rule its categories are in with no engine code. Tested: a test-only kind, "Test Venom", with nothing but `rm_cats = "poison"`, coated a sword.

The original game's kinds have their categories in one labelled block in UseOn.dm, because their definitions live in the 2006 files.

| Category | Original kinds |
|---|---|
| poison | Toxic, Poison, Strong Poison |
| quiver | Leather quiver (a resource sack is left out) |
| weapon | Every weapon. The original counts the pickaxe and the woodcutting axe as weapons too. |
| arrows | Arrows |
| wood | Logs |
| stone | Stone |
| ore | Ores (not stone) |
| ingot | Ingots |
| gem | Gems |
| bone | Bones, skulls |
| skin | Skins and hides |
| seed | Seeds |
| food | Food |
| herb | Herbs |
| egg | Dragon egg, spider egg sac |

## Rules

A rule joins two categories and works in either order: you can hold either item. It works on **any** item of those categories, using what the category gives, such as a poison's dose (`RemasterPoisonDose`) or a weapon's damage. Each rule is one row in `rm_combine_rules` plus its case in `RmCombineDo`. It may also have a check in `RmCombineCan` for whether it can apply right now.

**Built.** Both rules are the original game's own, from the toxic vial's "Arrows" and "Weapon" choices in Click.dm. They now take every poison, each at its own dose. All three poisons' descriptions say they "can be used to add poison to weapons".

| Rule | Joins | What it does |
|---|---|---|
| Tip the arrows | poison + quiver | Tips the quiver's untipped arrows with the poison at its own dose, ten arrows per vial. The vial is used up at ten. |
| Coat the weapon | poison + weapon | The weapon gets 2 to 4 more damage and becomes "… - [poison] Tipped". The vial is used up. |

Proven in the real app:
- A held vial outlined the pickaxe, the axe, the quiver and the sword.
- Coating the iron longsword raised its damage from 23–28 to 27–30.
- Holding the quiver offered the other vial, and 10 of the 15 arrows were tipped.

**Candidates.** None of these is built; they wait for the owner. Each one is a single row and a case.

| Idea | Joins | Would do |
|---|---|---|
| Fill the quiver | arrows + quiver | Loose arrows go into the quiver. |
| Sharpen | stone + weapon | A whetted edge: more damage for a while. |
| Set a gem | gem + weapon (or armour) | A lasting bonus by gem kind. |
| Mix a remedy | herb + herb | A remedy, as the Doctor's are. |
| Season or preserve | food + herb | Food that rots more slowly, or fills more. |
| Field tool | wood + stone | A crude stone axe or pick without a station. |
| Bone tool | bone + wood | A bone knife or spear point. |
| Poultice | herb + skin | A bandage-like dressing for a stump. |

## Making a new item: one row each

Built 10-28: the owner said "Yes, one row each". Every item is now one catalogue row plus its picture.

**Weapons and armour:** `art/enhance/catalogue.json`.
- Each row also takes an optional `cats` list. The exporter always writes `weapon` or `armour` (by slot), then the row's own words.
- `python3 art/enhance/game_export.py --data-only` rewrites `GearData.dm` alone, when only a row's numbers, recipe or categories changed.
- A new piece of gear still needs the full export to render its pictures.

**Everything else** (potions, food, poisons, herbs, materials, tools, special items): `art/items/catalogue.json`.
- `python3 art/items/export_items.py` checks every row and writes `game/Code/Remastered/ItemData.dm`. A bad row (an unknown station, skill, material or picture) stops the export with a message, instead of breaking the build.
- **id, name, kind** (food | potion | poison | herb | material | tool | misc). The kind decides where the item sits in the game's tree, so everything the game already does with that kind comes with it.
- **picture:** `pictures/<file>.png` (32 × 32, beside the catalogue), packed into `Icons/Remastered/Items/catalogue.dmi`, or `{"dmi", "state"}` for a picture the game already has.
- **weight, desc, cats, vars:** its own numbers, using the game's variable names, such as `{"FoodPower": 30, "PoisonContent": 25}`.
- **recipe** (optional): the station, the skill and its level, the materials, `makes` (how many per craft) and who can make it.
  - It uses the same stations, skills and materials as the gear rows.
  - The five workshops' "Craft new gear" lists it under **Supplies → Other items**, with the same skill, race and material checks.
  - There is no quality grade.

Proven in the real app with a two-row test catalogue (`reports/reddit-shots/itemtest/`):
- "Test Tonic" was made at a Carpentry from 2 logs, two at a time.
- "Test Venom", with its own new picture, was made at Bone crafting from bones. Held, it was offered "Coat the weapon" for the bag's weapons, with no code written for it.

## Adopting the game's own items

Built 10-28: the owner said "List, then adopt".

**The list:** `python3 art/items/list_items.py` writes `art/items/ITEM_LIST.md` (and `item_list.json`). It covers every kind of item in the game.
- It reads the compiled game for each kind's name, picture, weight and categories.
- It reads the source (`art/items/dmsource.py`) for where the values are written, the kind's own code, and which code makes it.
- Its **Adopt** column says whether a kind can move into the catalogue as it is, or why not. Reasons include "values mixed with code" and "New() changes its values when made".
- Run it again after a build.

**Adopting a kind** moves only its values. Its type name stays, so saves and every line of code that names it still find it. All its code stays where it is: its menu, what it does, a gargoyle eating iron.
- Run `python3 art/items/export_items.py --adopt /obj/Items/ores/Iron ...`.
- It takes the kind's own values (name, picture, weight, description, own numbers) out of the old file. It leaves a one-line note there saying which row holds them now.
- It writes them as a row with `"adopt": "<type>"` and the values the compiled game has. Then it exports. ItemData.dm writes them back on the same type.
- A row and an old file may never both set the same value. The export stops with a message if they do.

**Adopted on 10-28: 386 kinds, in two steps.**
- Build 110: 33 kinds. The 6 ores, 4 ingots, 10 gems (rings included), 7 seeds and 6 foods.
- Build 111: the other 353 the list marked as adoptable. The owner said "Yes, move all 353". They include the 2006 weapons and armour, furniture, traps, bones, potions, plants and shafts, and the hand-written Remastered items. Their values left 24 files.
- Both times, the compiled game was compared type by type, before and after. It was the same apart from each row's id.
- A row holds only what was written as a plain value. A sword's damage, for example, is worked out by the crafting code when it is made, and that code stays where it is.
- Categories stay in UseOn.dm's block of the original's kinds.

**What stays (31 kinds):**
- 24 have no values of their own (mostly groups), so there is nothing to move.
- 5 have values mixed with code, such as the Food group.
- 2 crowns have values split between Crowning.dm and Rulership.dm.

Those stay as their files define them until we change them. The list's Adopt column gives the reason for each.
