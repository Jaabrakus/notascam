# Human weapon action drafts

Open `index.html` or `Dungeon Master Sample/GOA Human Combat Sample.html`. The earlier sword/shield sample link opens the same updated viewer.

The default melee animation is a one-handed sweep across the body: guard, windup, sweep and recovery. Spear, sword, longsword, scimitar, hand axe, battle axe, mace, morning star, warhammer and dagger all use these four body poses in four directions. Only the anatomical RIGHT fist grips the weapon; the LEFT arm stays in guard and can carry an optional shield. Every weapon retains its own existing equipment art, measured grip and fitting scale. The shared animation is a prototype for these weapon families, not a claim of distinct finished combat mechanics for each item.

Bow draw/release and staff charge/cast retain separate three-pose body sets. These sources and the directional arrows remain unchanged. The earlier two-handed spear thrust and sweep experiments are excluded from the active selector and export archive.

Body cells are 64×64. Composed exports use 128×128 cells with a [32,32] body origin, four direction columns and four rows for melee, or three for bow/staff. The browser can pause or step through the loop and export the selected PNG and JSON. The sample ZIP contains the current exported sheets, body layers and metadata. Foot positions are registered and equipment has padding; every item still needs artistic review before game integration.

New one-handed body art uses the built-in image_gen tool. Its exact prompt, original image, generation provenance and registration are in `combat/spear-one-hand-sweep/`. `rig.json` records the right-hand socket, independent left guard socket, and projected weapon vectors. The generated atlas contains four complete pose rows; the importer exports those actual rows and does not invent extra drawings. Packing only crops, scales and registers the source alpha with nearest-neighbor sampling. Original art remains intact.

Bow, staff, arrow and prior sword prompts remain alongside their sources. `actions.js` contains the shared layer renderer; `demo.js` contains controls, timing and metadata export. Run `pack_one_hand_sweep.py` after source edits, then `build.py` and `verify.py`. Verification checks actual playback, all selected weapon variants, grip coordinates, optional shield, frame uniqueness and equipment clipping. It does not certify visual quality or combat balance.

Other races/sexes, shield-block poses, hit reactions and game integration are separate work.

The low spear jab uses three body keys with a return to ready, seven pixels maximum socket travel, independent front/back length foreshortening and shaft width fitting. The anticipation hop applies one root transform to body and gear; root timing is exported in JSON. A shared three-key damage flinch keeps all equipment attached. Use Take hit for a one-shot interruption or select Universal damage flinch to inspect/export it. See EQUIPMENT_RULES.md for the fitting contract and combat/current-game-reference/NOTES.md for the inspected game sources.

Idle holds: `Dungeon Master Sample/GOA Idle Weapon Holds.html` compares13 weapon choices and three shield combinations in all four directions. The interactive viewer opens on Idle/holding; idle PNG/JSON exports contain one row. The spear jab cycle with anticipation lasts1460ms, with240ms at extension; its universal clip lasts1.2s. Side spear angles retain the approved east/west upward tilt.
