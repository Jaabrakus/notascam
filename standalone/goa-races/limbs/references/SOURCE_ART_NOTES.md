# Limb and injury source art inventory

These files extract existing game frames without repainting, resizing or changing their alpha. Labeled contact sheets add labels only outside the source cells. The separate AI redraw work must use the approved updated body references for visual identity; these old sprites are pose and wound-language guides only.

## Ready-to-use references

- `{race}-arms-source.png`: 3 rows × 4 columns, 64-pixel cells. Rows `NoLeftArm`, `NoRightArm`, `NoArms`.
- `{race}-legs-source.png`: 4 rows × 4 columns. Rows `NoLeftLeg`, `NoRightLeg`, `NoLegs`, `None`.
- `{race}-mixedA-source.png`: 4 rows × 4 columns. Rows `NoRightLegNoLeftArm`, `NoLeftLegNoRightArm`, `NoRightArmNoRightLeg`, `NoLeftArmNoLeftLeg`.
- `{race}-mixedB-source.png`: 4 rows × 4 columns. Rows `NoLegsNoRightArm`, `NoLegsNoLeftArm`, `NoArmsNoRightLeg`, `NoArmsNoLeftLeg`.
- `{race}-injury-source.png`: `Normal` plus the 7 simple injury rows, all four directions.
- `{race}-self-graft-source.png`: race's own graft-overlay pixels, rows `LeftArm`, `RightArm`, `LeftLeg`, `RightLeg`. These are positioned in whole body cells; they are not loose ground items.
- `blood-and-stone-source.png` and `blood-and-stone-labeled.png`: original 32-pixel detached item, small blood decals, several burst phases, and bloodless stone item.
- `source-inventory.json`: complete 14-sheet limb overlay inventory and measured wound palette.
- `canonical-source-coverage.json`: 15 base identities plus 70 hybrid variants, source-state aliases and missing states.

Direction columns always follow BYOND's four-direction DMI order: **South/front, North/back, East/right-facing, West/left-facing**. No cells have been mirrored.

All 14 existing ground body races have references: Human, HumanBlack, Dwarves, Night Elf, Orc, Goblins, Kobold, FrogMan, LizardMan, Demon, DevourerZombie, Skeleton, Gargoyle, Vampire. The new regular `Elf` references alias Human poses only; its identity must come from the approved fair-skinned, golden-haired Elf artwork. The existing `Night Elf` is the updated blue-skinned, silver-haired dark elf.

## Left and right are anatomical

- South/front: actor's left arm/leg is on the viewer's **right**.
- North/back: actor's left arm/leg is on the viewer's **left**.
- East: the actor's **right** limb is near the camera; the left limb is usually hidden behind the body.
- West: the actor's **left** limb is near the camera; the right limb is usually hidden behind the body.

The old source side views often hide the far limb completely. Do not remove the visible near limb just to make a far-limb injury more obvious. The existing graft generator uses a small rearward peek for a replaced far limb, up to 5 source pixels for arms and 3 for legs, with its colors multiplied by 0.9.

## Blood and wound pixels

The original `Icons/Blood.dmi`, state `Arm`, contains only **33 visible pixels** in a 32 × 32 cell, occupying bounding box `(11,13)-(20,17)`, a 9 × 4 pixel mark. Its exact opaque palette is:

| Color | RGB | Pixel count |
|---|---|---:|
| Dark brown rim | 50, 4, 2 (`#320402`) | 12 |
| Bright blood | 255, 0, 0 (`#ff0000`) | 11 |
| Red shade | 189, 0, 0 (`#bd0000`) | 3 |
| Deep red | 167, 0, 0 (`#a70000`) | 3 |
| Bright red shade | 233, 0, 0 (`#e90000`) | 2 |
| Red midtone | 211, 0, 0 (`#d30000`) | 2 |

Original 32-pixel Human `NoLeftArm` wound red pixels are `#a70000` (4 pixels) and `#d30000` (1 pixel). The enhanced 64-pixel Human source uses softened darker shades: `#9d3d33` RGB157,61,51 (8 pixels), `#832b37` RGB131,43,55 (4), `#b53b3d` (1), `#64212a` (1) in its first South-facing `NoLeftArm` cell.

For updated sprites, this suggests small crisp red/maroon clusters, a dark rim, a readable cut surface and sparing highlights, rather than a large soft or photorealistic wound. The source blood item itself is a simple red fragment, not an anatomically detailed detachable arm. New race-specific detached assets may need a more readable limb silhouette while retaining this pixel-scale blood treatment.

## Race-specific rules

- **Gargoyle:** stone, not flesh. Broken-off limbs have grey fractured ends and no red blood or trail. `StoneLimbs.dm` explicitly uses `Remastered/Items/stonelimb.dmi`. Preserve this for gargoyle eye variants too.
- **Skeleton:** bone, no blood loss. Keep exposed broken bone and bone fragments. All four limbs lost causes it to crumble in the current game.
- **Vampire:** retains the original blood pictures on wounds and lost limbs, despite never starting ongoing bleeding or blood drips. This is explicit in `Stumps.dm:124-128`; do not interpret no bleeding as a requirement to erase wound-red pixels.
- Full limb loss for Gargoyle similarly causes the current game to smash it into stone powder.
- The original body-loss proc returns immediately for Devourer, Dragon and Spider. The `DevourerZombie` art sheet still has limb-loss states; artwork coverage and gameplay eligibility are separate.

## Existing overlay system

`Icons/Remastered/Limbs64` has **14 wearer sheets**, each with **74 states / 584 cells**, total **1,036 states / 8,176 cells**. Wearer races are the same 14 ground bodies listed above.

Every body slot supports these names:

- `<slot>@<donor>` for grafts: four slots × 14 donors. The recipient's own limb geometry is recolored to the donor's skin palette with donor material detail (bone, scales, frog spots, stone) and a stitch row.
- `<slot>:iron`, `:bone`, `:gem`, `:automail` for all four slots.
- `<slot>:wood` for legs only. No wooden-arm states exist.

Arms use three animation frames × four directions with source delay `2,2,2` (BYOND deciseconds). Legs use one frame × four directions, because the original leg-loss body states are static. Grafts and prostheses are overlays that fill holes in an injury-state body, not loose item pictures.

The current loose item art does not include a `Leg` state in `Blood.dmi`, although `Surgery.dm` assigns `Leg` to legs and `ItemData.dm` keeps both bloody limbs and prostheses on this icon. Adding proper arm/leg item states is a real missing-art requirement. `LimbFling()` currently starts its generic item in `Arm` regardless of the lost limb name. Do not assume these old generic item pictures already distinguish every slot.

## Canonical coverage and source defect

`Surgery.dm` maps 16 limb-availability combinations, with bit order **LeftArm, RightArm, LeftLeg, RightLeg**. The coverage registry records 15 base identities and 10 eligible race families × 7 hybrid appearances = 70 variants (85 entries total). Hybrid kinds are `Possessed1`, `Possessed2`, `Marked`, `Ashen`, `Hellblooded`, `Werewolf`, `Zombie`. Regular Elf currently uses Human pose aliases for its source coverage.

One source defect exists: **Demon lacks `NoRightArmNoRightLeg`**. It contains duplicated `NoLeftArmNoLeftLeg` names instead. Thus `Demon-mixedA-source.png` row index 2 is transparent, and its sidecar JSON flags this as missing. That empty row is a missing reference, not a request for an invisible character. All other canonical states map exactly or by equivalent order of limb names.

Scripts: `extract_source_references.py` inventories and extracts simple guides; `mixed_source_guides.py` extracts mixed guides, emits their row metadata, and audits canonical coverage.
