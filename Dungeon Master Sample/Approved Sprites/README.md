# Approved sprites

These are the four male Human sheets approved after the rounded-nose and idle-arm review:

- Male/Human/base
- Male/Human/Possessed1
- Male/HumanBlack/base
- Male/HumanBlack/Possessed1

Each folder contains sprites.png (256x192; 64x64 cells), movement.dmi and atlas.json. Columns are South, North, East, West. Rows are idle, walk A, walk B; replay 0,1,0,2 at 200ms. The DMI contains that four-phase movement loop. These files match the corrected working sheets exactly; manifest.json records the source paths and hashes.

The other current race sheets, equipment and animation work remain in ../Sprites/. That broader collection includes drafts. Earlier rejected Human redraws are not included here. Live game integration is a separate step.
