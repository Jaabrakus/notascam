# Reusable appearance layers

`appearance_layers.py` adds donor-art details to an existing pose sheet. The first
configured example is the Orc's Ashen and Hellblooded appearances, across sixteen
body-only poses. Horns, tail, shoulder/forearm markings and chest markings are
separate PNG layers. Equipment remains separate.

## Run the saved batch

From the Dungeon-Master-master repository root:

```sh
python3 standalone/goa-races/character-retarget/appearance_layers.py \
  --batch 'Dungeon Master Sample/GOA Drawn Animation Library/pipelines/review-batch.json'
```

The current output is `Dungeon Master Sample/GOA Drawn Animation Library/Male/Orc/appearance-layer-test-v3`.
Open its `index.html` to change appearance, pose, and layer visibility.

Individual jobs use `--config preset.json --output new-folder`. A batch is a list
of objects with `config` and `output` paths relative to the project root. `--root`
allows a different project root. A failed job does not prevent later independent
jobs from running. An unchanged job reuses verified outputs without rendering.
Changed or unverified existing output is refused; select a new versioned folder.

## Add another race or appearance

1. Supply that race's pose sheet and palette-swapped body sheets. This stage does
   not draw missing poses or automatically decide which bodies share anatomy.
2. Copy the Orc JSON preset and replace its geometry reference, grid, and variants.
   `xEdges`/`yEdges` explicitly register cells; normal uniform sheets can omit them.
   Use an alpha mask PNG in `bodyMask` to identify skin on other palettes. The
   optional green-channel selection rule belongs to this Orc test, not every race.
3. Define each layer's donor `source`, native `cell`, extraction `region`, and
   optional polygon/color selection. `outlineRadius` copies existing dark donor
   pixels around a selected feature; it never invents outline colors.
4. Set its `sourceAnchor` and target attachment point in each pose/direction.
   Target coordinates are local to their animation cell. A placement's `cell` is
   `[poseRow, directionColumn]`; an extraction's `cell` is `[column, row]` in the
   donor sprite sheet. Calibrate these against the actual artwork. Do not carry
   the Orc's coordinates onto a different body without checking them.
5. Choose front/behind depth and, for markings, `clipToSkin`. Foreground limb
   occluders can be explicit `occludePolygons` in pose-local coordinates. A fully
   covered mark must be explicitly allowed with `allowOccluded`.
6. Add the new config/output pair to a batch, inspect its preview, then retain the
   reviewed configuration as the reusable appearance mapping.

Compatible bodies can share placement records. Different proportions require
calibration. The same feature can be attached to any number of existing poses.
Wings, tails and unusual anatomy require their own source art and placements.

## Pixel preservation

- Existing base PNGs and donor PNGs are read-only.
- Layers use exact RGBA samples from donor sprites. There is no image generation,
  blending, smoothing, automatic seam filling, or arbitrary-angle transformation.
- Placement uses integer coordinates, optional quarter turns, and integer pixel
  replication. Use scale 1 for native-sized art. This enlarged Orc draft uses
  scale 3–5 to match its display scale; that does not make it a native game atlas.
- Overlay composition copies covered pixels directly. Pixels outside visible
  overlays are byte-identical to the palette-only body. No body geometry is moved.
- Behind-body occlusion uses a configurable alpha threshold; faint pre-existing
  fringes must not cut holes in a copied tail. Source transparency is otherwise
  preserved.

## Outputs and verification

Each appearance gets `layers/*.png`, `front-layers.png`, `back-layers.png`,
`palette-only.png` and `composite.png`. The review folder includes its exact config,
input hashes, file hashes, technical verification, comparison PNG and local HTML
viewer. Rendering is staged in a temporary folder and published only after checks.

The checks enforce nonempty configured attachments, no crossing cell boundaries,
exact donor colors/alpha, unchanged base pixels outside overlays and unchanged
source files. Cache reuse additionally checks source, engine, viewer, config and
saved output hashes. These checks do not certify artistic fit or game integration.

## Current scope

Only this Orc preset is calibrated. It contains 30 source feature layers and 120
pose placements across two appearances. Ashen uses horn and skin-marking parts;
Hellblooded uses horns and the source-visible North/West tail. The source has no
visible tail in South/East, so those directions deliberately add none. Eye and
tusk pixels stay those of the supplied body sheet.

The base pose sheet is an earlier generated draft. The pipeline preserves it but
does not turn it into a registered native atlas, fix its anatomy, or complete the
97-action library. Native game art and calibrated masks can replace that input
without rewriting the layer engine.
