# Dungeon Master sample sprites

Current published sprite sheets are organized here for easy use. Working files stay in standalone/goa-races; earlier redraw experiments are kept there as history and are excluded from this folder.

- **Male/** — race / appearance / sprites.png, atlas.json and movement.dmi where available. Human and HumanBlack include the current corrected sheets.
- **Female/** — all 80 female race/appearance walking sheets and metadata.
- **Combat/** — the existing Human attack, weapon, casting, flinch and idle-hold assets. These retain their current artwork.
- **Animations/Universal/** — existing 99 shared clip previews and rig metadata. These are mapping previews; they still require artistic review and retargeting for each body.
- **Equipment/** — existing directional gear textures, armor layers and catalog.
- **Equipped/** — exported previews with the shared equipment loadout.
- **Limbs/** — snapshots of the existing male and female limb/injury sprite work. The separate limb pipeline remains the working source.

PNG body cells are 64x64. Read each atlas.json for its direction order, state availability and timing; flight, injury and combat sheets use their own layouts. A sheet being organized here does not mark draft animation or game integration as complete.

Preview pages, armor galleries and ZIP downloads remain one folder above, in Dungeon Master Sample. Worn Armor and Idle Poses is also already there. manifest.json maps every copied file back to its working source and records a SHA-256 hash. Existing animations were copied without repainting or changing their pixels.

## Complete sample collection

Armor/ now includes the published worn armor and component sets. Matching Gear/ contains the published matching-gear pack with its original folder structure. Equipment/Inventory includes the wearable item sheet and index. Open ../All Sprites.html to search every file, or download ../All Sprites.zip.
