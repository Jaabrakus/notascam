# Orc appearance pipeline

This package applies repeatable appearance changes to the exact attack sheet supplied and approved by the user. It reuses the existing pixel-copy layer engine and calibrated Ashen/Hellblooded mappings. It makes no image-generation or network calls.

## Run

Double-click **Build Variants.command**, or run:

```sh
python3 build_variants.py
```

The script requires Python 3, NumPy and Pillow. If needed, install the dependencies with `python3 -m pip install -r requirements.txt` in your chosen environment.

Open `output-v1/index.html` for the six-variant animation preview. It works offline. Each row shows south, north, east and west. Pause, advance poses or turn overlays off to inspect the palette-only body.

To build selected appearances:

```sh
python3 build_variants.py --only Ashen Hellblooded --output output-test
```

An unchanged batch reuses outputs after verifying input, config, engine, viewer and output hashes. If an existing output differs, the script refuses to overwrite it: use a new `--output` folder. Palette-only intermediates are regenerated deterministically.

## Included appearances

| Variant | Applied appearance |
| --- | --- |
| Ashen | Grey skin, copied red horns and skin markings |
| Hellblooded | Red skin, copied ivory horns and source-visible north/west tail |
| Marked | Green skin, copied small ivory horns and red markings |
| Possessed1 | Darker donor skin palette |
| Possessed2 | Olive donor skin palette |
| Zombie | Donor skin palette, white eye colors and copied wounds |

These are visual-review variants, not six independently redrawn animations. Marked and Zombie mappings extend the existing Orc placement data; their fit still needs artistic review. Skin details are clipped to the skin silhouette. Some placements are completely covered or outside the skin at a particular pose and therefore are not visible; every such case is recorded in each variant's `verification.json`. Hellblooded has no tail in south/east because the donor art has no visible tail there.

Werewolf is listed as uncalibrated in `variants.json`: its changed head, ears and tail need a separate mapping. Other races cannot automatically inherit these coordinates simply because they are humanoid.

## Files and reuse

- `inputs/approved-attack.png`: exact, unmodified approved attachment, locked by SHA-256 in `master-lock.json`.
- `donors/`: copied native source appearances.
- `presets/`: editable JSON definitions for each appearance, including donor extraction, attachment coordinates, layering and skin clipping.
- `variants.json`: variant registry, palette selection and explicitly excluded anatomy.
- `palette-bases/`: same body pixels with deterministic RGB changes. Transparency and protected pixels are preserved.
- `output-v1/Variant/variant/`: composite sheet, palette-only sheet, front/back overlay sheets and individual overlay layers.
- `pipeline/`: the pixel-copy layer engine and offline viewers.

Skin colors are sampled from each donor's torso and mapped using one fixed luminance mapping across the full source animation. Zombie eye changes use a separate declared mask. Overlay pixels are copied from donor sprites, with integer replication and integer placement. No blur, smoothing, newly generated art, arbitrary-angle transforms or body reshaping are used.

The supplied sheet retains its original 1254 × 1254 resolution and existing transparency. It is a drawn review sheet, not a newly registered native game atlas. Exporting native animation cells is a separate calibration step. The packaged 64 punches/kicks are untouched by this batch.

For a new animation or race: supply its master, skin mask/palette rule and per-pose attachment mapping. Reuse this code, not unverified coordinates. The exact geometry of this approved sheet matches the earlier calibrated 16-pose Orc master, which is why those placements can be reused here.
