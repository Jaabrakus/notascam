# Hybrid walking drafts

70 named appearances across Human, HumanBlack, Dwarves, Elf, Night Elf, Orc,
Goblins, Kobold, FrogMan and LizardMan. Each has Possessed1, Possessed2,
Marked, Ashen, Hellblooded, Werewolf and Zombie walking drafts.

The built-in image generation tool created each sheet separately from the
approved four-view appearance and the race's walk pose guide. Prompts and
generation records live alongside each source in `assets/<race>/<appearance>/`.
Original images are retained. `tail-revision.png`, when present, is the selected
source instead of `generated.png`; its prompt and provenance record the revision.

All ten werewolves have visible hip-attached tails in their north views.
Lizardman base, possessed, marked, ashen and zombie forms have natural tapered
tails; Hellblooded keeps its barbed tail and Werewolf its wolf-hybrid tail.
Dwarf, goblin and kobold Hellblooded tails are shortened to suit their bodies.

`register.py` measures actual sprite bounds and mechanically packs 64x64 cells
without repainting art. PNG columns are South, North, East, West. Three rows
are neutral, step A, step B. Replay is 0,1,0,2 at 200ms. The DMI export stores
that explicit four-phase loop with the base race's movement-state name.

`publish.py` writes distinctly named files under `exports/` and rebuilds
Dungeon Master Sample / GOA Hybrid Walk Animations.zip. Per-race standing
references use row zero from the selected walks. Review sheets carry labels;
game atlases contain no labels. `coverage.json` in exports records names/hashes.

The gallery at `../hybrids/index.html` plays all appearances. Its browser
verification checks actual replay, complete cells, distinct poses and foot
registration. These are generated animation drafts; those checks do not certify
polished gait or exact identity consistency across every pixel. Female bodies,
attacks, sleep and limb-loss states are outside this export. Another chat owns
the limb-loss work; original full-state files are untouched.
