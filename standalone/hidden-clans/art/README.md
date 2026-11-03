# Remastered art: 3D-rendered sprite prototype

Prototype for the look in [planning/ART_DIRECTION.md](../planning/ART_DIRECTION.md). Nothing here is wired into the game yet: the game still loads its original `Icons/*.dmi`. The prototype models are original procedural Blender models; no downloaded or extracted assets are used.

## Rerun everything

From the repository root (`Dungeon-Master-master/`):

```bash
sh standalone/remastered/art/run_pipeline.sh
```

That runs the three steps below; about 10 seconds on this Mac. Run them one at a time like this:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python standalone/remastered/art/pipeline/render_sprites.py
```

```bash
python3 standalone/remastered/art/pipeline/build_dmi.py --sizes 32 64
```

```bash
python3 standalone/remastered/art/pipeline/make_comparison.py
```

Options:

- `render_sprites.py -- --only Orc` or `-- --only Items` renders one sheet and merges it into the existing `index.json`.
- `render_sprites.py -- --preview` renders only `Normal` and two axes, for quick look checks.
- `build_dmi.py --sizes 32` builds only the 32 px sheets.
- Set `BLENDER=/path/to/Blender` to use a different Blender with `run_pipeline.sh`.

Requirements: Blender 5.x (tested with 5.2.1 LTS, EEVEE), Python 3.9+ with Pillow and numpy. These are already installed here (Pillow 11.3.0). Nothing else is installed or downloaded.

## What is where

| Path | What |
| --- | --- |
| `pipeline/blender_models.py` | Palette, toon materials, construction kit, Orc rig and body, axe, buckler and helmet builders. |
| `pipeline/render_sprites.py` | Stage 1 (inside Blender): camera, key light, walk poses, missing-limb states and overlay layers. Writes `build/renders/`. |
| `pipeline/build_dmi.py` | Stage 2 (plain Python): nearest-neighbour downscale, outline, DMI v4.0 packing. Writes `out/dmi32/` and `out/dmi64/`. |
| `pipeline/make_comparison.py` | Original vs new sheet, on the game's own grass tile. Writes `out/comparison.png`. |
| `build/renders/` | Generated 256 px intermediate cells plus `index.json`. Safe to delete. |
| `out/dmi32/Orc.dmi` | New Orc base body. Same 16 states, frames, delays and movement flags as `game/Icons/Orc.dmi`. |
| `out/dmi32/OrcGear.dmi` | Overlay states `Bronze Axe`, `Iron Axe`, `Steel Axe`, `Wooden Buckler`, `Iron War Helm`: 4 directions × 3 walk frames, delay 2,2,2, movement 1, like the original item states. |
| `out/dmi64/…` | The same sheets at 64 × 64, for the size decision only. |
| `out/comparison.png` | Original 1x / 4x next to new 32 px 1x / 4x and 64 px at 2x. |

## How it works

1. **Render.** `render_sprites.py` builds the Orc rig (empties as joints, low-poly parts parented to them) and each item, parented to the hand, forearm or head pivot. Every cell is rendered at 256 × 256 with an orthographic camera at 30° and one fixed sun from the screen's top-left. Materials are flat toon ramps (shader → RGB → constant colour ramp → emission). For each direction the model turns; the camera and light never move. Equipment layers are rendered with the body collection set to *holdout*. The overlay is cut wherever the body is in front of it, so an axe in the far hand disappears behind the torso.
2. **Downscale.** `build_dmi.py` takes the centre sample of each 8 × 8 block (32 px) or 4 × 4 block (64 px): nearest-neighbour, never averaged, so every pixel stays on a palette colour. A pixel is opaque when at least 34 % of its block is covered, which keeps thin hafts. Alpha is binary, as in the originals.
3. **Outline.** A 1 px exterior outline goes around every layer. It uses the touching colour, darkened and desaturated, and is never lighter than `#2e2228`.
4. **Pack.** Cells are packed frame-major in S, N, E, W order, in `ceil(sqrt(n))` columns, as a PNG with chunk order IHDR, zTXt `Description`, IDAT, IEND. That is the layout of the game's own files. The project's decoder (`tools/export_sprite_assets.py`, `decode_asset`) parses all four sheets with no issues.

## Adding things

- **New item tier:** add a palette entry in `PALETTE` (shadow, base, light, glint) and one line in `ITEMS`, e.g. `("Mithril Axe", "weapon", lambda rig, col: bm.build_axe(rig, col, "mithril"))`.
- **New item shape:** write a `build_<thing>(rig, col, ...)` that parents to `rig["hand"]["R"]`, `rig["forearm"]["L"]`, `rig["head"]` or `rig["chest"]`.
- **New race:** write `build_<race>(rig_col, body_col)` that returns the same rig dictionary keys as `build_orc`. Equipment then re-fits to that body automatically, but needs its own overlay sheet per body (see the art bible's wiring notes).
