# Current Dungeon Master animation reference

Read-only inspection; live game sources were not edited.

- `standalone/remastered/art/gear3d/skills.js`: thrust keys at 0.18 / 0.30 / 0.46 / 0.74 seconds coordinate upper arm, forearm, wrist, lean, step and lunge. The stock thrust has lunge 0.5 leg lengths and step 0.85; the new sample uses no such large lunge. `skStep` attaches the weapon to the actual forearm tip, adds target-facing depth, and hides front-reaching arms behind the north-facing torso. Stock SKTWO contains spear, but a shield makes that game path one-handed; this sample follows the user's explicit one-handed design regardless of shield.
- `standalone/remastered/art/gear3d/gear3d.js`: weapon and shield depth follow the actual fist and forearm, with the west weapon on the far side. G3GRIP raises the longsword hilt three source pixels.
- `standalone/remastered/game/Interface/gear3d.js` is the installed combination of those sources, not a separate animation design.
- Human.dmi has the Armed body state and old-Spear.dmi has five overlay frames. `original-held-spear.png/.gif` mechanically combines the standing Armed body with those legacy overlay frames for reference. It is NOT a capture of the procedural live skill animation.

The small-jab body import excludes the generated fully extended source row and uses the low ready, tiny retraction and bent-elbow intermediate instead. The old full extension remains preserved in generated.png. Pole width is fitted independently of length so the shaft fits inside a closed fist. Near fist pixels render over it; north and west retain far-side occlusion.
