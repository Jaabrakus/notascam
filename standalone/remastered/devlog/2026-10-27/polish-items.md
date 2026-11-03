# polish-items, second pass (10-27)

## Done
- drink-says-why (landed 08:07): Drink on an empty bottle, or by a spider / undead / stomachless unit, did nothing and said nothing; now "The bottle is empty." / "<unit> can't drink potions." Arena check `drink_check.dm`: 3 of 4 cases failed before, 4 of 4 pass after. Gate compile/jscheck/hudjoin/combat 32/32. Speed: event-driven (one click), no per-tick code; no measurable change (not timed).

## In progress
- Audit of bag, gear cards, craft/workshop cards, remedies, names on build 68.
