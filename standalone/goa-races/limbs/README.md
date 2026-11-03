# GOA limbs and injuries

Open `index.html`, or **Dungeon Master Sample / GOA Limbs and Injuries.html**,
for isolated review of detached limb cutouts and missing-limb poses made from the actual approved sprite pixels. The gallery
is self-contained and works without a server, API key or network connection.

Choose a race, asset sheet, and row. Four direction views are shown together at
true **1×** and **4×** scale. Click a preview to inspect a pixel's RGBA value.
The original source sheet is available under its disclosure. This tool does not
paint, recolor, or alter the embedded source image.

**Download 64px PNG atlas** packs every source row into 64 × 64 cells using
nearest-neighbor sampling with one common source-pixel scale across the asset. Unequal source rectangles are centered inside their cells; frames are never independently stretched. Its companion JSON lists row names, direction order,
frame rectangles, source provenance, and the current draft status. Fractional
source cell boundaries are supported when an image's dimensions are
not evenly divisible by its declared grid. Review actual sprite registration;
packing and alpha checks cannot establish anatomical accuracy.

These rows are **static design / pose drafts**. They are not looped or presented
as completed animations. Missing-limb movement, timing, graft/prosthetic fitting,
equipment registration and game integration require separate checks.

## Manifest

`manifest.json` is maintained by the artwork pipeline. It contains a list:

```json
[
  {
    "id": "human-detached",
    "race": "Human",
    "category": "detached",
    "label": "Detached limbs",
    "path": "generated/Human-detached.png",
    "columns": 4,
    "rows": 4,
    "rowLabels": ["LeftArm", "RightArm", "LeftLeg", "RightLeg"],
    "directionOrder": ["South", "North", "East", "West"],
    "status": "draft"
  }
]
```

Categories are `detached` and `injury`. Paths can be absolute, relative to the
manifest, or repository-relative. Columns must be four; every row must have a
label. Optional `sourceGridRows` describes the original sheet's total rows; `selectedRows` selects one original row for every exported row. For example, `rows: 3`, `sourceGridRows: 4`, `selectedRows: [0, 1, 2]` excludes an incorrect fourth source row.

Optional `sourceRects[row][view]` supplies absolute `[x, y, width, height]` source rectangles. It can describe all original rows or just the selected output rows. Explicit rectangles are required for sheets with intentionally empty far-side limb cells. Without explicit rectangles, alpha projection finds separated row and direction bands and places cuts in the intervening whitespace. The inferred row count must match `sourceGridRows`; ambiguous layouts fail for manual segmentation instead of silently clipping sprites. Original PNG bytes remain unchanged.

Duplicate IDs, malformed grids and non-PNG sources are rejected. A missing
manifest produces an empty gallery explaining that artwork remains pending.

## Batch the limb sprites

From the project root, build the15 reviewed ground-body families and their missing-limb blood states:

```sh
python3 standalone/goa-races/limbs/build_limb_sprites.py --gallery
```

This produces the PNG/DMI asset folders, metadata, proofs, existing-game slot binding and `Dungeon Master Sample/Sprite Limb Assets.zip`. Use `--only human,orc` for a subset. `--all` also exports94 appearance records, whose hybrid/flight geometry still needs calibration. It adds no new fly-off simulation; existing `LimbFling` / `RmG3Limb` handle that in the game.

For a data/gallery verification after rebuilding:

```sh
python3 standalone/goa-races/limbs/verify.py --real-only
```

The build uses Pillow to measure or validate source rectangles. Verification also uses the already
installed Playwright and Google Chrome. It checks a transparent fixture
with odd dimensions, direction/state indexing, preserved source bytes, true
preview scales, PNG and JSON exports, pixel inspection, race selection, missing
manifest handling, and every real asset available at the time of the check.
Fixtures are temporary; verification makes no AI calls.

Editable sources are `gallery.template.html`, `gallery.js` and `build.py`.
Rebuild after adding sprite cutouts to the manifest. Original game sprites
remain unchanged.

## Literal source-pixel limb exporter

`build_pixel_assets.py` consumes the approved body registry and `pixel_cutter.py`.
It packages literal body-pixel partitions; it does not redraw anatomy, darken hidden limbs, or mirror an invented far-side limb. When `wound_pixels.py` is available, tiny wound overlays are exported separately and applied only to additional blood-state sheets.

```sh
python3 standalone/goa-races/limbs/build_pixel_assets.py --only human
python3 standalone/goa-races/limbs/build.py
python3 standalone/goa-races/limbs/verify.py --real-only
```

The default is the Human preview. Do not publish all registered bodies until the
cut geometry has been reviewed. `--all` explicitly selects the entire registry;
`--only` accepts comma-separated registry body IDs.

Each body folder in `pixel-assets/` contains aligned 64px normal/core images,
four original-pixel limb layers, all 16 canonical `Surgery.dm` limb-availability
combinations, DMI files, masks, metadata, and a proof report. Every actual source
pose is retained. The walk sequence `[0, 1, 0, 2]` is encoded as four DMI frames
with the source timing; flight and standing sequences retain their own timing.
The intact canonical state is named `Normal`, matching `rm_limb_states`; callers
using another intact-state name must bind it through the exported metadata.

Proof checks require exact full-RGBA reconstruction of every rendered body cell,
disjoint core/limb assignments, no changes outside removed masks, unchanged
source files, and intact DMI state/timing serialization. Empty hidden limbs are
valid. A proof pass establishes pixel preservation, not correct anatomical mask
placement. Geometry quality flags remain in each body's metadata and proof.

Blood caps use at most4 pixels in the exact source red palette per visible cut. `wound-caps.png/.dmi` keep those overlays separate; `injuries-with-blood.png/.dmi` contain the16 composed body states. Pure source parts and injury files stay unchanged. Gargoyles and Skeleton receive no red caps. Use `--no-wounds` to export only the pure versions. Proofs additionally require zero changes outside the cap and removed-limb supports. Already-packed64px atlas downloads pass through
their original PNG bytes unchanged, avoiding browser alpha-rounding alterations.

`verify_pixel_export.py` checks all16 combinations against asymmetric synthetic
parts, including partial alpha, an empty hidden arm, overlap rejection and the
realized DMI walk loop. It does not create project artwork or call image AI.

The fly-off page created earlier is an archived prototype and is not part of the requested batch workflow. The game already supplies limb-fling physics.
