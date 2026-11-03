# Original-height exports from detailed artwork

`export_family(family, output_root=None, overrides=None)` reads the completed
`detailed-artwork/manifest.json` plates and their ordered state-index mappings.
It creates one first-occupied-facing design per inventory state, a high-resolution
transparent source cutout, and inventory/player original-height PNGs.

```sh
python3 output/imagegen/BOTD-sprites-enhanced/_tools/export_detailed_items.py \
  --family wood
```

`--overrides` accepts a JSON object mapping native inventory state indices to
explicit `[left, top, right, bottom]` rectangles, with exclusive right/bottom.
For Python calls, pass that same dictionary as `overrides`. When an outer
dictionary groups multiple families, pass only the selected family's dictionary.

Automatic proposals isolate the first-view column, use area-weighted component
positions to cluster rows, and retain the largest object plus nearby detached
parts. These are proposals: inspect each family montage and source cutouts for
column headings, clipped or adjacent objects, text fragments and separated parts.
Supply explicit crop overrides when needed. The helper never declares its own
visual review passed. Its family report remains pending until the responsible
worker reviews and updates it. Four transparent pixels are added around each
cutout for the existing exporter's clear-perimeter checks.

All cutouts use the frozen alpha-only `extract_existing_sprite.py`. Retained
source RGB is verified exactly before resizing. Source plates remain unchanged.
The native inventory state is matched by ordered index; player equipment is
matched by exact state name and occurrence because its state order and frame
count differ. The first occupied native cell supplies height and baseline.
All 375 inventory states were checked to have an occupied first S cell.

`export_sprite_height.py` retains aspect ratio and original bottom baseline,
with native 32px inventory or 64px player frame height. Width may vary. Nearest
resampling is tried first; Lanczos is used only when sparse extreme pixels make
nearest lose the required visible height. Every output's alpha bounds are checked
against the native reference. These sized designs are **not drop-in overlays**.

The default output root is `detailed-artwork/exports`, containing:

- `source-cutouts/<family>`: high-resolution alpha-only PNGs and crop audits.
- `game-height/inventory/<family>` and `game-height/player/<family>`: PNGs and
  proportional-export reports.
- `reports/<family>.json`: per-state source hashes, crop rules, extraction audits,
  native references, dimensions, alpha bounds and review results.
- `review/<family>-native3x.png`: paired inventory/player review montage.

Existing outputs are reused only when their explicit crop agrees. To correct a
crop, preserve the affected cutout/audit and both sized PNG/export-report pairs
under a candidate directory, then rerun with the corrected override. The full
family report and montage will be rebuilt. Never replace the large artwork
plates with these size exports.
