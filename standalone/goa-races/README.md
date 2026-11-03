# GOA-style race adaptations

First visual draft adapting Dungeon Master's existing enhanced race identities to the GOA character style. Generated using the built-in imagegen tool on October 29, 2026.

The [sprite converter](sprite-engine/index.html) imports existing art and prepares redraw jobs against this approved reference for Codex's built-in image generation. It also reviews and packs finished redraws into PNG/JSON atlases. Start it using `Dungeon Master Sample/Launch GOA Sprite Converter.command`, or use the portable HTML. [Workflow and engine documentation](sprite-engine/README.md).

The subsequent interactive equipment fitting tool is in [gear-preview/index.html](gear-preview/index.html). It uses the current game's original 16-angle, 3D-derived weapon/shield/helmet strips and source armor layers, rather than generating another equipment illustration. See [its notes](gear-preview/README.md) for controls and limitations.

- Image: `goa-races-lotr-v1.png` (1024 × 1536, RGBA).
- Rows: Human, Dwarf, Night Elf, Orc, Goblin, Kobold.
- Columns: south/front, north/back, east/right-facing, west/left-facing.
- Reference sheets are in `references/`; the generation prompt is in `PROMPT.md`.

This is an enlarged visual draft, not a production-ready 32 × 32 sprite atlas. The generated pixels, positioning, and silhouettes need cleanup and consistency checks against the GOA base before integration. Walking, running, attacks, casting, injury, death, and equipment overlays have not been adapted. No DMI animation metadata has been created and no existing game artwork has been replaced.

The source images retain the generated alpha channel. No background removal or manual pixel edits were applied after generation.

References were extracted from `standalone/remastered/game/Icons/Remastered/Races64/` and `/Users/kiwimango/Downloads/GOA Source/icons/`. The earlier 32-pixel source discussion concerned the original Dungeon Master sprites; the enhanced race set used here has 64-pixel frames.
