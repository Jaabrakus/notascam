# Universal armory

One drawable gear catalog shared by the updated GOA-style races and hybrid designs.
This is a local fitting and export tool, separate from the live game. It uses actual
game assets and does not invent item statistics.

Open **Dungeon Master Sample/GOA Universal Armory.html**, or double-click
**Launch GOA Universal Armory.command** to run it locally. The default local address
is `http://127.0.0.1:8877/`. Python 3 is sufficient for the launcher; the standalone
HTML needs only a modern browser.

## Shared gear

63 designs, 454 actual supported design/material combinations:

- 33 weapons, including swords, axes, polearms, bows, tools, staves, special weapons,
  and the original GOA held sword.
- 5 shields and 6 helmets.
- 10 chest designs, including armor, robes and the GOA chest/shoulders.
- 3 arm-armor designs, 5 leg-armor designs and 1 boots design.

Dedicated glove and cloak artwork is missing. Empty hands/back slots in the catalog
are not represented as finished assets. The [catalog](CATALOG.md) lists supported
materials for each design. `Universal Gear and Weapons.csv` lists each supported
shape/material combination as a row; `catalog.json` contains the source recipes.

The existing 3D-derived weapons, shields and helmets retain their sixteen angle
frames and available weapon poses. Body facings remain four directions. Armored
bodies and held-weapon sprites are composed at render/export time, instead of
storing a new copy of every item for every race.

## Fitting and motion

Choose a race or variant, then fill any combination of seven equipment slots. Each
slot offers only its actual supported materials. Sword/shield, scout and mage
loadouts are provided. Choose standing/holding, walking/flight, or weapon pose
inspection. Weapon pose inspection keeps the body standing and is not a body
attack animation.

The registry has 94 choices: 15 walking bases, 3 flying bases and 76 standing-only
variants. All seven previously unfinished updated base walk sheets are preserved
under `body-sources/`. Raw generated rows were unevenly spaced; the registry uses
actual alpha separators to avoid importing neighboring heads or cutting off feet.
Images remain unchanged. Source hashes and the exact frame rectangles are recorded
in `bodies.json` and described in [BODIES.md](BODIES.md).

Gear shares a common 64px fitting space with body feet near y=61. The renderer fits
armor to torso/arm/hip/boot regions and attaches weapons/shields/helmets to sockets.
You can move an attachment in the large preview, change size, width, rotation and
front/back depth, and adjust one body frame separately. Base-race fitting overrides
are inherited by its hybrid designs; a variant's own overrides take precedence.
Fitting changes save locally in the browser when storage is available.

**Save loadout & all race fits** exports a portable JSON preset. Loading the preset
restores the selected body, all equipment/material choices and every fitting
override. It validates IDs and numeric bounds before applying them.

## Sprite export

The exported ZIP contains:

- `sprites.png`: composed equipped sprites with four cardinal columns. Long gear
  receives transparent padding so a spear or staff can extend beyond the body cell.
- `body64.png`: the corresponding unequipped 64px body frames.
- `atlas.json`: direction/frame rectangles, body origins, feet, animation sequence,
  selected weapon pose, exact loadout and fitting settings, and padding metadata.
- `loadout.json`: reusable equipment and fit preset.

`Dungeon Master Sample/GOA Universal Equipped Sprites.zip` contains a shared soldier
loadout example for all 94 registered choices, with every available base walk/flight
frame. `GOA Equipped Races Preview.png` compares twelve of those fits. Regenerate
these examples using `python3 standalone/goa-races/armory/export_samples.py`.

Equipped frames normally start at 128px, with the body still in a 64px coordinate
space. Frames expand when measured gear bounds require more room; use the manifest
origin when integrating into a renderer. The app does not silently crop a long
weapon to a 64px body cell.

## Current limits

These are generated body-animation and equipment-fitting drafts. The tool allows
all listed gear to be previewed on each registered body; that is not a claim that
every material, pose, horn, tail, hair or wing combination has production-quality
masking. Inspect grip coverage, near/far hands, shoulders, head/hair occlusion, and
the complete animation loop. The armor recipes use canonical Human source layers
with fitting transforms, not newly authored armor for every race.

Standing-only hybrids remain standing when equipped. Their walk, injury,
missing-limb, sleep and armed-motion states are not fabricated. The full-state
inventory in `../full-states/coverage.json` remains a work list, not finished art.
The rejected dense Human atlas is not in this armory. Human Zombie source artwork
touches its original image's bottom edge; that source limitation is recorded.

## Development

```sh
python3 standalone/goa-races/armory/build.py
python3 standalone/goa-races/armory/verify_armory.py
```

`equipment.js` is the reusable body/equipment renderer. `armory.js` is the fitting,
catalog, preset and export UI. `catalog.py` and `body_registry.py` build source-backed
descriptors without changing the original artwork. The builder embeds images and
scripts into self-contained HTML, so no game process or external service is needed.

No new AI gear image was generated for this tool. Gear is fitted through rendering
transforms and existing source recipes. Earlier AI-generated body designs and
walking drafts keep their existing provenance; the exact copied walk filenames
and hashes are included with the body registry.

The fit pass applies a neutral side-view cant to long held weapons to keep their
blades and heads clear of the face. Helmet fitting measures the lower head rather
than ear/horn tips; body ear and horn pixels render over the helmet where needed.
Boot coverage and ankle position are fitted independently from leg armor.

The original GOA sword has complete South/East held overlays but incomplete
North/West ones. The armory uses the measured grip at [21,43] in 64px coordinates,
reconstructs North/West by reflection, and follows the new body's hand motion
using the neutral blade image. Those reflected views are adaptations, not newly
discovered native GOA frames. `goa.sword.fitAdaptation` records this in the catalog.
