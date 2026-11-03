# Art direction: Dungeon Master Remastered

Status: proposal and working prototype for the lead designer to review. Nothing is wired into the game. The prototype pipeline, sprites and comparison sheet are in [art/](../art/README.md); see [art/out/comparison.png](../art/out/comparison.png).

## The look in one paragraph

Pre-rendered 3D, drawn as crisp pixel sprites. **Bodies** follow the chunky, hand-painted high-fantasy tradition: oversized hands, shoulders and heads, bold local colour, and painted light rather than realistic shading. **Items** follow a material-tier language: one silhouette per item type, recoloured per material, so a bronze, iron or steel axe is recognisable at a glance and its tier from its colour. Everything is judged at game size (32 px on a grass tile), not in the Blender viewport.

These are inspirations for style only. Do not copy, trace, sample or extract assets, names, logos or palettes from World of Warcraft, RuneScape or any other game. Models are built here, procedurally or by hand. Item names are generic (Bronze Axe, Iron War Helm).

## 1. Camera and projection

| Rule | Value | Why |
| --- | --- | --- |
| Projection | Orthographic | Tile-true sizes; no perspective drift across the 32 px cell. |
| Elevation | 30° above the horizon, no yaw | Matches the existing near-front "top-down map, upright sprite" look. Faces stay readable and the top of the head and shoulders shows, which reads as 3/4. Steeper angles (45°+) lose faces at 32 px. |
| Scale | 1 Blender unit = 1 tile = 32 px | Height budget is set in world units (below). |
| Ground anchor | World origin at x 16, y 29.5 of the 32 px cell | Feet sit where the original sprites' feet sit (rows 29 to 30), with room for the outline. |
| Directions | Rotate the *model* by 0°, 180°, +90°, −90° for S, N, E, W | Camera and light never move, so lighting is identical in every direction. DMI order is S, N, E, W. |
| Motion | Every translation snapped to whole output pixels (1/32 unit) | Sub-pixel motion makes eyes and tusks flicker between frames after downscaling. |

Render each cell at 256 × 256 (8 × of 32). The master render stays the source of truth, so 32 px and 64 px builds come from the same pixels.

## 2. Light and palette

**One key light for every render:** a sun from the screen's top-left and slightly in front (direction `(-1, -0.9, 1.35)` towards the light, strength 2.2), with no cast-shadow softness, plus a cool, dim world ambient (linear RGB 0.13, 0.14, 0.19). No fill or rim lights per asset. Consistency matters more than per-asset beauty.

**Shading is a painted ramp, not physical:** lit diffuse goes through a constant colour ramp.

| Band | Threshold on lit intensity | Colour rule |
| --- | --- | --- |
| Shadow | < 0.30 | Darker, shifted cool (towards blue or purple), never black. |
| Base | 0.30 to 0.62 | The local colour. |
| Light | 0.62 to 0.80 | Lighter, shifted warm (towards yellow). |
| Glint (metal only) | > 0.80 | Near-white, tinted with the metal. |

Warm lights and cool shadows give the hand-painted feel without textures, which would turn to noise at 32 px anyway. Organic materials get three bands; metals get four, so metal reads as shiny next to skin and wood.

Local colours should be saturated but not neon. Keep sprite values in the middle range so the outline separates them from both dark caves and bright snow.

## 3. Outline and readability

- 1 px exterior outline on every layer, 4-neighbour (no diagonal corners, which keeps it thin and clean).
- Outline colour: the touching colour × 0.3, desaturated 40 %, never lighter than `#2e2228`. A selective near-black outline reads on grass, sand and snow, and is softer than the originals' pure black.
- No inner outlines; the toon bands separate forms. Overlays get their own outline, which also separates gear from the body under it.
- Binary alpha only. No soft edges or drop shadows inside the sprite (the map has no shadow layer to match).
- **Readability checklist at 32 px, judged on the game's grass tile:** the race can be named from the silhouette alone; eyes are visible (2 px) facing south; the weapon's head shape is visible; the item tier can be named from colour alone; the walk cycle does not flicker.
- Feature minimums at 32 px: eyes 1 to 2 px, hands at least 3 px, weapon heads at least 4 × 4 px, hafts at least 1 px wide over their full length.

## 4. Race silhouettes and proportions

Heights are in tiles at 1x (1 tile = 32 px). Projected height is about 0.87 × model height at 30°. Every race has the same rig joints (root, hips, chest, head, shoulders, hands, forearms, hips), so equipment builders work for all of them. Every race exaggerates its *one* defining feature beyond realism, because at 32 px only one idea survives.

| Race | Model height | Width at shoulders | Head size | Defining shape | Notes |
| --- | --- | --- | --- | --- | --- |
| **Orc** (prototype) | 0.92 | 0.60 (widest) | Small, low, forward, scaled 1.28 for the face | Inverted triangle: huge shoulders and forearms, hunched neck, short thick legs, big fists | Green-olive skin, red eyes, ivory tusks, topknot. Head sits below the shoulder line. |
| **Human** | 0.85 | 0.42 | Medium | Upright, balanced, readable "default". Slightly large hands and feet | Varied skin tones from a fixed set. The neutral reference other races are compared against. |
| **Dwarf** | 0.62 | 0.48 (wider than tall-looking) | Large, with a big beard mass | A box: barrel chest, beard reaching the belt, stubby legs, heavy boots | The beard is the silhouette. Beard colour must contrast with armour. |
| **Elf** | 0.95 | 0.34 (narrowest) | Small, with long swept ears | Tall vertical: long legs, narrow waist, ears extending past the head outline | Ears must break the outline by at least 2 px in every direction except north. |
| **Goblin** | 0.55 | 0.36 | Very large (about 35 % of height) | Big head and ears, hunched, thin limbs, big feet | Large ears and a big nose. Reads as "small and mischievous" next to the orc. |

Rules shared by all races:

- Hands are 1.3 to 1.5 × realistic size. Forearms are thicker than upper arms.
- Feet are boxy and slightly too large; they anchor the sprite on the tile.
- Keep the arms visibly apart from the torso in the south view (at least 1 px gap or a shading break), so held items read.
- Legs keep about 2 px between them facing south, so the walk cycle reads.
- Base bodies wear only a neutral loincloth or underclothes (as the originals do); all gear is overlays.
- Missing-limb states (NoLeftArm and so on) hide that limb and show a blood stump. The body does not shift; this matches the originals.

## 5. Material tier language (items)

One shape per item type; the material sets the colour. Higher tiers may add, at most, a trim or glint, never a new silhouette (that is reserved for named or unique items).

| Tier | Shadow | Base | Light | Glint | Character |
| --- | --- | --- | --- | --- | --- |
| Wood | `#43281e` | `#86562e` | `#bd8a4e` | none | Warm brown, matte. Hafts, bucklers, bows. |
| Bone | `#7d6e5c` | `#d6c9a0` | `#f6eed2` | none | Pale ivory, matte. Horns, tusks, bone gear. |
| Bronze | `#5a3022` | `#a8692e` | `#dda04c` | `#fbe3a0` | Orange-brown, warm; the first metal. |
| Iron | `#2c2a2e` | `#58534f` | `#837b72` | `#a89e92` | Dark warm grey, low contrast, a dull glint. |
| Steel | `#3b4560` | `#8794a8` | `#c6d2e2` | `#ffffff` | Light cool blue-grey, high contrast, white glint. |
| Mithril | `#25296e` | `#5266c4` | `#94b0ff` | `#eaf2ff` | Saturated blue-violet, the "magic metal" read. |
| Gold | `#6e3e14` | `#c8952a` | `#f5d55c` | `#fffbe0` | Yellow, warm, bright. |

The progression is a value and temperature ladder: warm/mid (bronze) → dark/neutral (iron) → light/cool (steel) → saturated cool (mithril) → bright warm (gold). Neighbouring tiers always differ in *value* as well as hue, so they stay distinct for colour-blind players and in dark caves. Existing materials (Adamantium, Silver, Chitin, Demonic, gem-set) get rows here before they are rendered.

## 6. Sprite size: 32 × 32 versus 64 × 64 drawn at 2x

The comparison sheet shows both: the "New 32 px" columns are what the game would show today, and the "64 px at 2x" column is the same render at double density, shown at the same on-screen size.

**What 64 would need from OpenDream.** OpenDream draws the map into a render target of view tiles × `world.icon_size` pixels, then stretches it to the window (`OpenDreamClient/Interface/Controls/ControlMap.cs`, `UpdateViewRange`, nearest-neighbour for the default zoom mode). A 64 px sprite drawn into a 32 px tile, for example with `transform = matrix() * 0.5`, is resampled into that 32 px-per-tile target first, so the extra detail is thrown away before it reaches the screen. There are two ways to get real 64 px detail:

1. **`world.icon_size = 64` for the whole game.** Works on the existing engine, but every original 32 px DMI would have to be upscaled 2× (lossless, nearest) and every pixel-based number in the game code doubled: `pixel_x`/`pixel_y`, step and glide sizes, `screen_loc` pixel offsets, maptext offsets and the HUD. OpenDream also has open `icon_size other than 32` TODOs in `MouseInputSystem.cs` (screen-location clicks). That means high risk and a wide code change.
2. **An engine change: supersample the map.** Render the main map target at 2× (`ViewportSize * 2`) and draw 32 px icons at 2× with nearest filtering. 64 px icons marked as high-density (a new DMI header key, or a naming convention) would draw at 1×. Game logic stays at 32 px per tile. This is a contained change in `ControlMap`/`DreamViewOverlay`, but it is an engine fork that must keep replica parity untouched.

**Recommendation: ship 32 × 32 now, and keep 64 open.**

- 32 px is a drop-in: same tile grid, same state names, frames, delays and movement flags, same overlay model, no engine or game-code change. The prototype shows that 3D-rendered 32 px sprites read clearly on the map, with recognisable races, faces and tiers.
- Keep the 256 px master renders. The pipeline already emits 64 px sheets from the same renders, so moving to 64 later is a rebuild, not a redraw.
- If the team wants the extra detail (the 64 column shows clearer faces, plank seams and blade shapes), choose option 2 as a separate, Remastered-only engine task, and measure it on the target Macs and mobile first. Do not change `world.icon_size`.

## 7. Layers and overlays

- Layers and draw order: base body → chest → helmet → shield → weapon. Each is its own DMI state, rendered with the body as a holdout, so it is already cut where the body is in front of it (for example, the far-hand weapon behind the torso in the west view).
- All layers share the rig and the exact camera, so they line up pixel for pixel in every direction and walk frame.
- State format matches the originals: 4 directions × 3 frames (stand, left step, right step), `delay = 2,2,2`, `movement = 1`. Body states without legs are 1 frame, `movement = 0`.

## 8. Wiring notes (a later, separate step)

Not done; listed so the review can price it:

1. **Overlays are body-specific.** The original game uses one item overlay for every race, because all original bodies share roughly one shape. With distinct WoW-style proportions, gear must be rendered per body (`OrcGear.dmi`, `HumanGear.dmi`, …) and the game must pick the sheet by race when it builds overlays. That is a game-code change in the equip/overlay path (`Code/Items/Equipment Lists.dm` sets `icon`/`icon_state` per item type today).
2. **Ground and inventory icons.** Original items use the same state for the worn overlay and the ground/inventory icon. A worn overlay cut by the body holdout looks broken on the ground (only the visible parts of the axe remain). Add a separate full-item `icon` state per item (one direction, rendered without the body), and make the item's own icon use it.
3. **Swapping a body** is a file swap: `art/out/dmi32/Orc.dmi` has the same 16 states and frame layout as `game/Icons/Orc.dmi`. It still needs a visual pass against existing overlays (hair, clothes, armour) that were drawn for the old body shape. Those would look misaligned on the chunkier orc until they are re-rendered too.
4. Run `tools/export_sprite_assets.py` and its full check after any swap, and keep the Classic replica untouched.
5. **Licensing:** add the new art's licence/provenance next to the existing notices before packaging.

## 9. Production rules

- One master `.blend`/script per model. Generated sprites are never hand-edited. If a pixel needs fixing, fix the model, the palette or the pipeline and rebuild.
- Review at 1x on the grass, sand, cave and snow tiles before approving anything.
- Keep every new palette in `art/pipeline/blender_models.py` `PALETTE`, and add it to the tier table above.
