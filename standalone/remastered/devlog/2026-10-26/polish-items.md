RESUME: finished 10-26 23:55. Everything landed (batch 1 earlier, items-batch2 at 23:54). Nothing left running.

# polish-items (10-26 night): things units carry and wear

Mine carts no longer lose half their load on the way. A unit that loses an arm drops the sword or shield it can no
longer hold. "Take food from the stores" walks the last step instead of saying "Can't carry more" with an empty bag.
The bag's item menus ask on the HUD card, and the Resource Sack no longer offers "Drop Arrows".

## Done

- Landed earlier: cart-keeps-load, limb-gear-off, bag-menu-card.
- Landed 23:54 as items-batch2 (gate compile/jscheck/hudjoin/combat 32/32/obey 32/32): sack-menu, take-reaches, armour-buttons, one-arm-tools, best-armour-scaled, sack-fly-mist, give-says-why. Restore point restore-points/before-polish-items-batch2-20261026-235431.
- Each fix has a folder with README, check and before/after logs in `reports/polish-night-1026/items/`.
- Speed: no measurable change claimed from design, NOT timed in ms/tick: all fixes are event-driven (menu, equip, drop, limb loss, a take order); the only per-tick path touched is RemasterTakeTick (one extra loop pass per order) and one istype in the cart override. The gates' combat and obey runs passed with the same timings.

## Numbers

| Test (arena) | Before | After |
|---|---|---|
| Mine cart: full load of 20, 10 had lain at the stop ~3 min | 10 delivered | 20 delivered |
| Right arm cut off, sword held | sword still held | sword on the ground |
| Left arm cut off, shield worn | shield worn, still counted in Defence | shield on the ground, Defence back |
| Take food: 3 tomatoes a tile past the store tile | 0 taken, "Can't carry more food" | 3 taken |
| Resource Sack's bag menu | has "Drop Arrows" | no "Drop Arrows" |

## In progress

## Needs the owner
