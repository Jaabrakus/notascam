# Compact one-handed thrust foundation

One body animation drives the empty-handed, sword and spear previews in four directions. The shield stays on the opposite forearm and can be hidden in the viewer.

The body was drawn once using the built-in image generator. Its prompt is saved in `prompts/body.txt`. Native normalization uses the original Orc palette and nearest-neighbor sampling, with binary transparency. Existing sword, spear and shield artwork is copied into `equipment/`; `equipment/sources.json` records its provenance.

The side-view forearm is shortened by copying the drawn elbow and fist while omitting excess straight forearm columns. The head and legs are locked across the cycle. Recovery is an exact copy of ready. This is a new review animation; it does not replace the approved combat artwork.

## Reuse contract

- Four directions: south, north, east, west. Four phases: ready, pullback, short thrust, recovery.
- Cells are 128×128 to fit the spear without shrinking the body. Body origin is padded by 24 pixels.
- `sheets/body.png` is the only body sheet. Both equipped previews consume those same pixels.
- `sheets/*-rear.png` and `sheets/*-front.png` hold equipment independently of the body. Grip occlusion is baked into the front equipment layer.
- Composition order: rear shield, rear weapon, body, front weapon, front shield.
- `manifest.json` stores per-frame hand and shield attachment points, atlas rectangles and preview timing. Each weapon's directional pixels are reused unchanged across phases; only placement changes.
- Front/back equipment views are fixed foreshortened views; east/west use exact quarter turns. No smoothing or arbitrary-angle resampling.
- `frames/` contains body frames and baked sword/shield and spear/shield comparisons. `layers/` contains the independent equipment frames.

Rebuild from project root:

```sh
python3 standalone/goa-races/character-retarget/build_orc_thrust_foundation.py
```

This is a pose review, not gameplay integration. One-handed thrusts can share this motion; two-handed weapons and bows need their own grips and body poses. The guard drawings originate from the new drawing, not pixel-identical copies of the approved original guard. Existing 224 frames are verified unchanged.
