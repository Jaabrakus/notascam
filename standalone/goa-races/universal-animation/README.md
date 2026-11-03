# Universal humanoid animation library

Open `Dungeon Master Sample/GOA Universal Animation Library.html`. Shared clips animate anatomical bones; a race/sex supplies its own pixel parts, joints and equipment sockets. Four body directions are sufficient. Movement vectors can be continuous; four sprite views do not require four-direction-only navigation.

The library imports all57 keyed definitions from the current `standalone/remastered/art/gear3d/skills.js`, `work.js` and `deaths.js`, preserving key times, channels and combat event markers. It also provides17 deterministic preview adaptations for physics reactions,14 source-defined cause-of-death sequences, the legacy death presentation, and ten locomotion/new clips: idle, walk, armed idle, armed walk, run, sleep, bow shot, low one-handed spear jab, anticipation hop and universal flinch. Total99 clips. The83 humanoid arena controls resolve to these clips; staff materials, carried objects and projectile choices reuse body clips rather than duplicating them.

Physics-driven falls in the live game are simulations, not stored sheets. Their baked previews here are deterministic adaptations, not captures or replacements for that simulation. Particle effects, spell projectiles, load meshes, loose equipment and blood remain external. Bosses require separate skeletons; this is the humanoid library. Limb-removal previews respect hidden bone slots and reuse the existing pixel layers; the other limb-loss pipeline is not modified.

The Human mapping is a calibration draft made from existing approved GOA pixel-cut layers in `limbs/pixel-assets/human/`, copied read-only and split at elbow/knee boundaries. No new race art is generated here. The optional armed calibration skin reuses translated near-arm pixels for hidden arms, matching the existing game fallback; it remains a rough rig proof. Mapping geometry and shoulder coverage need visual review. The generic animation renderer and exact source keys are the reusable deliverable; baked Human sprites are mapping previews.

## Mapping a body

The canonical bones are head, torso, armRu/Rl, armLu/Ll, legRu/Rl and legLu/Ll. R and L are anatomical. Ten64px part columns and four S/N/E/W rows make a640×256 skin atlas. `human-rig.json` records each part's source root and tip, plus its parent. Forearm tips are weapon/shield sockets. The core torso/head and disjoint limb pixels reconstruct the static source; bends can expose hidden areas that require authored skin art.

Use the joint overlay and rest-pose map to drag shoulders, elbows, wrists, hips, knees and feet. Save the limb map JSON; load another640×256 part atlas and its mapping through the JSON editor. These change the body, not the clips. A later race mapping can use the same99 clips. Preview proportions normalize lunge/step/hop by leg length; pixel hand targets use the mapping's handTargetScale or a leg-length-derived default.

## Data and exports

`clips.json` contains portable clips and arena aliases. `source-clips.json` is the serialized original keyed definitions, weapon-class lists and death sequences; `extract.js` rebuilds it read-only. `engine.js` samples and retargets tracks, places limbs and attaches equipment. `app.js` handles playback, mapping and PNG export. `exports/` contains four-direction Human atlases sampled at approximately12fps in192px padded cells (64px body space, origin[64,64]) and companion metadata for every clip, not hand-drawn replacement anatomy for every action.

`coverage.json` and `verification.json` record actual export/playback checks. Tests verify coverage, finite bone transforms, nonempty direction frames, UI mapping edits, event preservation and source identities. They cannot certify artistic quality or full game integration.

Run `node standalone/goa-races/universal-animation/extract.js`, then `python3 standalone/goa-races/universal-animation/build.py` and `verify.py`. Live game files and the other limb chat's assets remain unchanged.
