# Female race and hybrid sprite drafts

80 appearances in the current female roster: Human, HumanBlack, Dwarves, Elf, Night Elf, Orc, Goblins, Kobold, FrogMan and LizardMan; each has base, Possessed1, Possessed2, Marked, Ashen, Hellblooded, Werewolf and Zombie forms.

Current sheets are in `all/<race>/<appearance>/injuries64-v1.png` and `.dmi`. `manifest.json` lists all 80. Frames are 64×64; columns South, North, East, West. Seven rows: Normal, NoLeftArm, NoRightArm, NoArms, NoLeftLeg, NoRightLeg, NoLegs. Red pixel cut caps are retained. No detached limb-piece assets were generated.

Normal walking sheets and playback are in `../../female-animations/`. The sample previews are `Dungeon Master Sample/GOA Female Races and Hybrids.html` and `Dungeon Master Sample/All Female Limb Sheets.html`. Both normal walks and standing injury sheets are bundled in `Dungeon Master Sample/GOA Female Sprite Drafts.zip`.

Standing injury structure, transparency, connected pixels, clipping and PNG/DMI correspondence passed checks for 2,240 frames. All 80 preview selections are checked separately. Normal walk playback was checked for all 80 forms. These remain artwork drafts: injured walking, attacks, sleep, equipment fitting and live game integration are separate work.

Artwork uses direct native AI edits of each approved female identity. Packing only extracts whole poses, orders states, aligns complete poses, samples with nearest neighbours and removes disconnected transparent fragments. Prompts and provenance remain beside source sheets and overrides. The original three-entry first set is historical; use the 80-entry manifest and `pack_all.py`.
