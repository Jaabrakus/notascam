# BOTD sprite enhancement — first visual sample

Built-in image_gen created Human-enhanced-preview.png from the user's Human contact sheet and the earlier enhanced race sheet.

Status: visual art-direction sample only. The full pack has not been enhanced or installed. Generated geometry, row labels and cell spacing require validation before any runtime use.

Source folder: /Users/kiwimango/Downloads/BOTD-sprites
Native assets: /Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Icons/Remastered

## Inventory and compatibility audit

All 669 source PNG sheets correspond to native DMI files; every sheet dimension matches the original exporter's layout formula. The sheets are opaque labeled previews with native artwork displayed at 3x size. Sample comparison of 48 frame crops across eight sheets matched the native source compositing exactly.

| Folder | Sheets | Native directional frame cells |
| --- | ---: | ---: |
| Races64 | 86 | 8,044 |
| Gear64 | 533 | 118,300 |
| Limbs64 | 14 | 8,176 |
| Rope64 | 13 | 10,200 |
| Gear | 19 | 1,500 |
| Items | 4 | 35 |
| Total | 669 | 146,255 |

Native data contains 11,891 state entries. The character and equipment animations primarily use four directions, ordered S/N/E/W, rather than the eight yaw views in the earlier references. Native cells are 64x64 for Races64/Gear64/Limbs64/Rope64 and 32x32 for Gear/Items.

The preview exporter limits each state to eight animation frames. 169 FX states have 20 frames per direction; 8,112 native directional frame cells are absent from the previews. Nine duplicate state-name occurrences (one Races64/Demon, eight Rope64/Demon) are also omitted by the preview loader's first-name-wins behavior.

For game assets, retain the original full DMI metadata/frame stream, transparency, direction order, timing, movement flags and aligned overlay registration. A generated preview is insufficient to reconstruct those reliably.

Relevant code:
- standalone/remastered/art/voxel/export_sprites.py
- standalone/remastered/art/voxel/dmi.py

## Image generation prompt

Use case: identity-preserve.
Asset type: enhanced Human character animation and body-state REFERENCE SHEET for the BOTD fantasy game.
Input 1 (/BOTD-sprites/Races64/Human.png) is the EDIT TARGET and is authoritative for sprite layout, poses, directions, missing-limb states and number of sprites. Input 2 is the enhanced race full-body sheet and is a STYLE REFERENCE ONLY; use its Human row, not other races, as the shading/voxel treatment guide.
Enhance every Human sprite in input 1 with the clean chunky pixel / voxel art, warm sandy-gold skin, clearly defined eyes and brows, tidy silhouettes, dimensional plane shading and warm highlights seen in the Human row of input 2. Preserve original human proportions and neutral base-body design, no new clothes or gear, no hair changes. Keep pure crisp pixel edges, discrete tone ramps and modest clean outlines; no blur, photographic realism or glossy plastic.
The reference sheet shows 17 state rows and 12 maximum frame columns. Preserve EVERY existing row and occupied sprite slot in its original position and framing, keeping blank slots empty. Preserve the four-direction animation ordering within rows. Columns are NOT eight yaw angles: do not convert this sheet into an eight-angle turnaround. Rows with three animation frames each contain four directional views per frame, in south/front, north/back, east/right-profile, west/left-profile order repeated three times with the source's stepping poses.
Keep the Sleep row, its sleeping human and Z icon. Preserve the exact original missing-limb variants: do not regrow arms or legs in rows where they are absent. Preserve the source's small red stump indications at the same stylized intensity and locations. Every sprite must remain inside its cell.
Preserve all original small row labels verbatim, the source label at top left, dark charcoal background and sparse empty areas. Entire sheet visible from top title through last row, same tall aspect ratio, no cropping, no added decorative elements or text. Target a finely resolved output suitable for inspecting the proposed art direction. This is a full enhancement of the original Human sheet, not a new roster.

