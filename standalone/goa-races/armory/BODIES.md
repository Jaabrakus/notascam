# Armory body registry

`body_registry.py` writes `bodies.json` and preserves the seven completed updated
walk sheets in `body-sources/`. It does not generate art or change sprite pixels.
The source copies are byte-for-byte identical to the native generated PNGs;
`body-sources/provenance.json` records original locations and SHA-256 hashes.

The registry contains **94 body choices**:

- 15 bases with actual three-frame walking artwork.
- Three bases with two-frame flight artwork.
- 70 standing hybrid designs: seven variants for each of ten races.
- Six standing gargoyle eye-color designs, including their flying forms.

The seven updated walking bases are Human, Dwarf, regular blond Elf, Dark Elf,
Orc, Goblin and Kobold. Their completed outputs had not been saved by the earlier
interrupted generation turn; they are now preserved locally. The remaining
eleven bases use the unchanged full-resolution `result.png` files in their saved
converter jobs. The earlier packed `sprite-engine/converted` exports are not
used: their equal-grid packing can split feet or include the next row's head.

**Standing variant rows are not animation frames.** `standing_only` entries have
one frame per direction and a one-element playback sequence. No walking, flight,
limb-loss, attack, sleep or armed states are synthesized for them by this registry.
The rejected full Human atlas is explicitly excluded.

## Descriptor contract

The root object has `version: 1`, a `bodies` array, and summary counts. Each body
contains:

- `id`: stable selector key; `raceKey` names the race/source family.
- `baseId`: same-race base ID for equipment-fitting inheritance.
- `variant`: `Base` or the specific standing variant name.
- `status`: `walk`, `flight` or `standing_only`.
- `source`: absolute PNG path; `sourceSha256` identifies its exact bytes.
- `sourceRects[frame][view]`: `[x, y, width, height]` in absolute source pixels.
- `frameBounds[frame][view]`: `[left, top, right, bottom]` relative to that cell,
  measured using source alpha >= 128. This threshold measures bounds only; it
  does not alter alpha or pixels in the artwork.
- `unionBounds[view]`: the union of those cell-relative bounds across all frames.
- `targetHeight`: nominal total visible height in the 64-pixel fitting space.
- `layout`: original grid dimensions, selected row, actual frame count and views.
- `animation`: actual art kind, playback sequence and frame durations in ms.
- `normalization.referenceHeight`: maximum visible sprite height across all the
  frames and directions; use it for a single stable body scale.
- `segmentation`: detected row bands. Source cell boundaries come from actual
  transparent separator bands; the generator's equal-grid prompt is not assumed.
- `qualityFlags` / `sourceEdgeContacts`: existing source-art limitations. The
  Human Zombie design reaches its original PNG's bottom edge in all views and
  should be inspected for clipping. No pixels are fabricated to hide this.

Every view uses the BYOND/source order **South, North, East, West**. Walking
sequences are `[0, 1, 0, 2]`, alternating the neutral frame with the two stepping
frames. Flight sequences are `[0, 1]`. Default inspection durations are 200 ms per
sequence entry. These are renderer inspection timings, not a newly integrated
game movement controller.

## Stable placement

Use `normalization.referenceHeight` to derive a **single scale for all animation
frames and directions**. Resizing each frame independently to the same height
would make its body grow and shrink during playback.

Native output is often not an exact equal grid. For example, the Human walking
sheet is 1448 by 1086 pixels, but its real occupied row bands are y100–397,
y431–722 and y756–1040. Cutting it into three 362-pixel rows would remove feet
and include fragments of the next row. The registry infers actual row and column
separators from alpha projections. Source rectangles can therefore have different
widths and heights. They contain complete sprites without neighboring fragments.

For cell-relative frame bounds `b = [left, top, right, bottom]`, a centered fitting
space with feet at y=61 can use:

```js
const scale = body.targetHeight / body.normalization.referenceHeight;
const b = body.frameBounds[frame][view];
const destinationX = 32 - (b[0] + b[2]) * 0.5 * scale;
const destinationY = 61 - b[3] * scale;
const [, , cellWidth, cellHeight] = body.sourceRects[frame][view];
ctx.drawImage(image, ...body.sourceRects[frame][view],
  destinationX, destinationY, cellWidth * scale, cellHeight * scale);
```

Disable image smoothing when rendering pixel art. Per-race fitting anchors and
gear offsets remain separate from these source-image descriptions. `baseId`
allows shared defaults, while horns, hair, tails, wings and altered body shapes
can need variant-specific corrections.

This inventory establishes drawable source cells and real frame availability.
It does not certify gait quality, overlay registration, anatomy consistency, or
finished production animation. Those require visual review in the renderer.

## Rebuild

```sh
python3 standalone/goa-races/armory/body_registry.py
```

Rebuilding verifies the expected number of actual row/column bands, nonempty
selected cells, source bounds, unique IDs and preserved walk-copy hashes. If the
bands cannot be identified unambiguously it fails for manual segmentation rather
than silently assuming equal cells. Existing source art is never replaced.
