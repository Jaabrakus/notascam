# Original-height enhanced artwork

Exports match each corresponding original native sprite’s visible height. Width follows the enhanced design proportions. The original frame height and bottom baseline are retained; canvas width can expand.

Current checked artwork:

- `Races64/Goblins/standing-front.png`: 44-pixel visible height, 42-pixel visible width, 72×64 canvas. One of 98 native Goblin cells.
- `Items/stonelimb/Arm.png`: 4-pixel visible height, 32×32 canvas. The source has one state and one cell, so artwork coverage is complete.
- `Items/stonelimb.dmi`: single-cell package with the original native DMI Description unchanged and decoded pixels identical to `Arm.png`.

Three explicitly selected Sol agents handled local export, packaging and independent QA. This batch made zero image-generation calls; source artwork came from earlier calls. Fresh redraws remain pending under the user’s credit constraint.

See `../_meta/sol-local-batch.json` and `../_meta/sol-original-height-review.json`. Original source files remain unchanged. Runtime installation and gameplay checks have not been performed.
