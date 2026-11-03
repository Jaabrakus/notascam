# Dungeon Master Remastered: every action

Everything you can do in the game, how to do it, and where it lives. In the game,
press **F3** for this guide, or open **Info › Actions**: it lists every command
with its key, and **one click on a row runs it**. HUD icons around the map also
run with **one click** (the original needed a double-click).

The HUD's **Controls** button opens every border icon with its name, description
and shortcut. **Hide/Show map border** is saved; those labeled commands remain
available while hidden. The [complete border reference](planning/BORDER_CONTROLS.md)
explains all 44 buttons. Top +/− adds/removes autodig marks. Border drop buttons
drop cargo here; the Easy Orders **Drop off** command travels to the stockpile.

## Mouse

| Action | How |
| --- | --- |
| Select one of your units | Click it |
| Add / remove a unit | Shift+click it |
| Select all your units of that race on screen | Double-click one |
| Box-select | Drag on the map (a green box shows the area); Shift+drag adds |
| Move / attack / interact | Left-click/tap the ground, an enemy or an object |
| Contextual dropdown | Right-click an object or unit, then choose its available command |
| Pick up an item | Double-click it with a selected unit next to it |
| Equip, inspect or drop an item | Info › Inventory, double-click the item |
| Craft | Click/tap a workshop with a selected unit next to it |
| Select a unit from the list | Info › Units, click it |

## Keyboard

| Key | Action | Key | Action |
| --- | --- | --- | --- |
| Arrows / numpad | Move the view | Z | Centre on selected unit |
| , / . | Camera up / down a level | Backspace | Go to last unit under attack |
| A / E | Select units nearby / all units | Space | Clear selection |
| 1-9 | Select control group (tap twice: jump) | Ctrl+1-9 | Set control group |
| Shift+1-9 | Add to control group | Alt+1-9 | Original group keys (still work) |
| P | Stop: cancel orders and targets | J | Guard / guard rules |
| I | Interact with something nearby | B | Build menu (needs stone or wood) |
| Q | Create / go to waypoint | G / C | Go to coordinates / show coordinates |
| N | Rename selected units | U / X | Speak through a unit / unit emote |
| D | Declare a king or queen (crown) | R | Choose race / restart |
| S / W | Say to the world / message a player | L / - | World chat on/off / clan chat |
| H / K / T | Who / legends / updates | O | Music off |
| Tab / F5 | Autodig add-subtract / use autodig | F3 | Controls & Actions guide |

## Actions tab only (one click, no key)

- Equip all armour / unequip all armour
- Autodig on/off for the selected units
- Pick up nearby: wood, stone, ores, gems, ingots, food, bones, skin, seeds, armour, arrows (with a quiver)
- Drop all: wood, stone, ores, gems, ingots, food, bones, armour
- Tear meat / tear skin from carried corpses
- Add an ally, remove an ally, list allies

After a pick-up or drop the game now says what happened ("Picked up 2 wood",
"Nothing to pick up next to your selected units", "Your units can't carry any
more", "Your selected units carry no stone"); the original buttons failed silently.

## Info tabs

| Tab | Shows |
| --- | --- |
| Actions | Every command above for your selection, with keys |
| Units | Your army; click a unit to select it |
| Unit Stats | Selected unit: level, hunger, cold, tiredness, stats, carry weight, skills |
| Inventory | Selected unit: carry weight and every item, "(Equipped)" / "(Carrying)" |
| Unit Information | Selected unit: bleeding, gender, age, every body part's condition |
| Your Information | Land, date, history, kills, season, time of day |

## Health and alerts

- Your units show a health bar (only you see it).
- When an enemy next to one of your units hurts it: a red message with where,
  at most every 10 seconds; Backspace takes you there.

## Checked

These are the intended controls. See [REVIEW.md](REVIEW.md) for the verification
limits and open defects.

- `tests/actions-checks.json` records invocations and some effects, without
  assertions for every action. The associated world log contains a `SendMSG`
  exception that its old error filter missed.
- `tests/mouse-checks.json` records click and drag selection in a real window.
  The right-click step has no recorded destination changes, so movement orders
  still need verification.
- `tests/qol-checks.json`: 19 selection, health-bar and alert behavior checks
  pass in a bounded arena, followed by the completion marker.
- `tests/border-controls-checks.json`: 24 focused behavior assertions pass.
- `tests/easy-orders-hud-checks.json`: 43 responsive input/asset checks pass,
  including all 44 border commands and the day/night indicator.
