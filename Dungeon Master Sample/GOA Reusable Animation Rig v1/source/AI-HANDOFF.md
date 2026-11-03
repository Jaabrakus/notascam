> Latest: bow-mirror-9 uses West as the master side bow pose and renders East as its exact horizontal reflection, per user request. West drawing-hand follow-through is reduced to 2px back / 1px down before lowering. This supersedes the separate East back-body stance below. Spear-level-8 keeps the thrown spear horizontal in all views.

> Update: archer-6 changes side-view bow stances per user confirmation: East uses North body + East head; West uses South body + West head. Both side views use the right bow arm, with the left drawing arm. Earlier ranged-4 descriptions below are historical. Front/back arm projection was added in projection-5.

# Elf animation rig: reproduction and visual correction brief

Status: 2026-10-30, revision `ranged-4`. This is a working animation prototype, not an approved visual match or a live-game replacement.

## What the user wants

Use the approved GOA-style Elf male as the first calibrated character. Preserve its head, proportions, palette and native pixel scale. Make the same action readable from South, North, East and West. Start with a convincing bow shot and right-shoulder throw; extend the method after those are visually accepted.

West holds the bow in the character's right hand and draws with the left. East uses the opposite hands. This is an intentional view-dependent convention requested by the user, not proof of consistent anatomical handedness during a turn. Keep it explicit rather than accidentally swapping labels. North/South arrows should be mostly hidden or show only a small end/tip. North/South throws originate beside the character's anatomical right shoulder, never from the center of the chest.

Keep the previously accepted shield rules: North's shield is physically ahead of the character, so the body can occlude it; South's attacking weapon/hand can render above the shield. Do not flatten every object into one universal draw order.

## What the screenshots actually show

The supplied screenshots show different clips and times: spear throw at 0.50s (after its 0.38s release), and bow shot at 0.72s (full draw, before its 0.90s release). They should not have identical poses. Within each screenshot, however, all four views must communicate the same action phase.

They do not yet do that convincingly. Front/back arms read as sideways gestures; the side bow silhouette is cramped; the front/back projectile treatment does not establish depth as clearly as the side views. These are visual shortcomings, even though numerical tests pass.

The current library transfers source timing and motion channels to a different sprite body. It is not a frame-for-frame reproduction of the game's rendered animation. Do not claim a visual match based on source provenance or passing tests.

## Files to read first

All paths below are relative to `/Users/kiwimango/Downloads/Dungeon-Master-master`.

| File | Role |
| --- | --- |
| `standalone/goa-races/shared-body-rigs-v1/references/Elf_male_User_Approved.png` | Approved Elf reference, 4× presentation of native sprite cells |
| `Dungeon Master Sample/Unique Body Equipment Rig/rig.json` | Existing directional body-part rig and calibration |
| `standalone/goa-races/elf-game-animations/extract.js` | Extracts definitions and checks runtime provenance |
| `standalone/goa-races/elf-game-animations/runtime-source.json` | Extracted game motion definitions |
| `standalone/goa-races/elf-game-animations/build.py` | Packs approved body parts, gear, clips, metadata and viewer |
| `standalone/goa-races/elf-game-animations/engine.js` | IK, body transforms, per-view posing, gear and projectile compositing |
| `standalone/goa-races/elf-game-animations/app.js` | Playback, scrubbing and export UI |
| `standalone/goa-races/elf-game-animations/viewer.html` | Viewer template |
| `standalone/goa-races/elf-game-animations/check_polish.js` | Grip/recovery/counterbalance checks |
| `standalone/goa-races/elf-game-animations/check_ranged.js` | Bow timing, hand selection, throw shoulder and weapon-angle checks |
| `standalone/goa-races/elf-game-animations/verify_export.py` | Browser checks and baked PNG/JSON exports |
| `Dungeon Master Sample/GOA Sword and Shield Rig/library/` | Generated preview, assets, exports and verification reports |

Edit source files, then rebuild. Editing generated `library/engine.js` alone will be overwritten. Preserve unrelated concurrent changes in the project.

## How the current version was built

1. Read the installed game's bundled `gear3d.js`, compare it with the working runtime, and extract the included skill/work/death definitions. Preserve actual event times. Mining/woodcutting use the currently enabled fallback, not the disabled doll move.
2. Load the approved Elf's four directional views and existing 15-part rig: head, torso, pelvis, and upper/lower/end segments for each of four limbs.
3. Use waist/neck transforms for torso motion. Derive hand/foot targets from source motion channels, then solve two-bone IK using calibrated segment lengths.
4. Rotate complete sprite parts around joints, add small source-palette joint caps, and composite them. Idle/walking also use existing drawn source frames. This is not AI inpainting; the renderer uses existing parts and simple backing pixels.
5. Attach equipment at measured grips. Game `W` is an absolute weapon angle; do not add torso lean a second time. Two-handed poses constrain both grips to the weapon axis.
6. Add explicit per-facing bow targets in `bowPose()`, a separate drawn string in `bowArt()`, and short front/back arrow tips in `arrowTip()`.
7. Override front/back throwing-hand targets near the right shoulder. On release remove held gear and spawn a detached preview projectile from the release grip.
8. Render through the browser at native coordinates with smoothing disabled. Export four directional columns in padded 192px cells; the body is still native 64px, located at origin `[64,64]` within each export cell.
9. Verify source integrity, timing, limb constraints, image bounds and browser errors. These checks establish mechanical correctness only.

Current test snapshot: 97 clips, 9,140 directional samples, 184 recorded source files unchanged, 246 ranged checks passed. This count is not a count of visually approved animations.

## Why simply tweaking offsets is insufficient

`sample()` projects motion into screen space and solves IK with fixed **screen-space** limb lengths. A forearm aimed toward or away from the camera should look shorter. Keeping its full side-view length in the front/back projection forces the elbow outward, which can produce the lateral-raise silhouette the user dislikes.

`bowArt()` currently reuses the East bow image and narrows it for front/back views. Narrowing alone does not specify the correct pose, depth or overlap. North currently draws both complete arms before the body, which can hide useful elbow/hand detail. A whole-arm layer rule is too coarse for some poses.

Rotating flat limb cutouts can also expose incomplete shoulders, jagged contours or holes. A 3×3 joint cap cannot reconstruct missing anatomy or create a foreshortened hand. Preserved palette and disabled smoothing do not guarantee clean pixel art.

## Next pass: pose mock-up specification

First build a four-column contact sheet at the exact shared event times below. Display native 1× and nearest-neighbor 4×. Establish silhouettes with equipment hidden, then show the same frames with equipment. Do not start by retargeting all races or baking all 97 clips again.

### Bow shot

| Time | Action | Side-view reading | Front/back reading |
| --- | --- | --- | --- |
| 0.00 | Rest | Relaxed grip, bow lowered | Relaxed shoulders |
| 0.32 | Raised/nocked | Bow hand ahead, drawing hand at string | Bow arm reaches into depth; avoid spreading both arms sideways |
| 0.72 | Full draw | Bow grip forward; drawing hand at cheek; elbow behind | Drawing hand near cheek, appropriate elbow visible; bow arm visually foreshortened |
| 0.90 | Release | String returns, arrow separates, drawing hand follows through | Tiny arrow end or occluded arrow, same release instant |
| 1.15 | Follow-through | Aim briefly retained, then lower | Same body intent and recovery phase |
| 1.75 | Rest | Return to start without popping | Return to start without popping |

North: torso/head can hide the bow hand, string and arrow, but preserve enough elbow/shoulder silhouette to read the draw. South: hand and bow may overlap torso; the arrow points toward the viewer, so do not draw a full horizontal shaft across the chest. Its exact visible tip depends on the chosen camera projection.

### Right-handed throw

| Time | Action | Side-view reading | Front/back reading |
| --- | --- | --- | --- |
| 0.00 | Guard | Weapon held, balanced stance | Same guard intent |
| 0.26 | Windup | Hand/weapon behind or above right shoulder; torso coils | Hand outside anatomical right shoulder, elbow visibly bent |
| 0.38 | Release | Hand drives forward; projectile separates from grip | Release beside right shoulder, reaching into depth; avoid center-chest launch |
| 0.52 | Follow-through | Throwing arm follows through, weight shifts forward | Foreshortened reach and readable shoulder follow-through |
| 0.75–1.00 | Recover | Empty throwing hand returns to guard | Same recovery, no weapon reappearing mid-clip |

Anatomical right shoulder is screen-left in South and screen-right in North. Maintain that identity for all throw variants. Keep spear aligned with its trajectory; axe/dagger flight can use their own rotation without changing the body's action timing.

## Implementation plan for the next AI

1. Freeze existing output as a comparison reference; make new review output rather than overwriting source art.
2. Author explicit four-view key poses for only `bow_shot` and `throw`, using the tables above. Review hand, elbow, shoulder, hips and planted feet together. Do not independently tune hands until they merely satisfy a coordinate test.
3. Separate body-space limb length from projected visible length. Either use a small 2.5D skeleton with depth followed by projection, or authored per-view foreshortened part variants. For this small sprite, authored key-pose variants are a reasonable first implementation. Keep the existing side-view rig where it reads well.
4. If adding depth, declare camera basis and projection once; derive all four views from the same timed body-space action. Then apply explicit view-specific art/hand conventions. Do not interpret a projected short limb as a physically shortened bone.
5. Give each segment a depth/layer assignment by facing and phase. Split near/far forearms and hands when needed. Keep hair/head overlap intentional. Avoid putting an entire North arm behind the torso when the elbow should remain visible.
6. Complete hidden torso/shoulder pixels and add clean foreshortened elbow/hand variants where existing cutouts cannot cover the pose. Match the approved palette/outline; inspect at native scale. Do not claim automated transforms remove the need for this cleanup.
7. Drive held weapon and projectile from the same release socket. Preserve release times. Remove the held instance at release; spawn one projectile, then recover with an empty hand.
8. Interpolate between accepted key poses. Snap raster placement at render time, retain floating-point pose calculations, and inspect every in-between frame for seams and popping.
9. Update tests to reflect the new representation. If introducing projection, assert fixed body-space bone lengths, not fixed projected 2D lengths. Retain grip continuity, event timing, no clipping and no double projectile checks.
10. Present synchronized four-view contact sheets and looping playback for visual review. Only after that apply the recipe to other clips, then calibrate additional race/female/hybrid rigs. Share animation semantics; do not assume identical anatomy or sockets.

## Reproduction commands

Run from the repository root. Extraction re-reads live sources; use it only when intentionally refreshing the source audit.

```sh
node standalone/goa-races/elf-game-animations/extract.js
python3 standalone/goa-races/elf-game-animations/build.py
node standalone/goa-races/elf-game-animations/check_polish.js
node standalone/goa-races/elf-game-animations/check_ranged.js
python3 standalone/goa-races/elf-game-animations/verify_export.py --review
```

The verifier uses the local preview server on port 8878 and installed Chrome. If the server is absent, start it separately:

```sh
python3 -m http.server 8878 --bind 127.0.0.1 --directory 'Dungeon Master Sample/GOA Sword and Shield Rig'
```

After the limited review passes, run `verify_export.py` without `--review` to bake/check the full library. The current verifier has a revision string and specific assertions; update those deliberately when changing the representation. Passing those assertions is not visual approval.

Current previews:

- Bow: http://127.0.0.1:8878/library/?v=ranged-4&clip=bow_shot
- Throw: http://127.0.0.1:8878/library/?v=ranged-4&clip=throw

## Copyable task prompt

> Read `standalone/goa-races/elf-game-animations/AI-HANDOFF.md` in the Dungeon-Master-master repository. Continue the existing approved GOA Elf rig; do not replace its art or live game runtime. The current ranged-4 implementation passes technical tests but is not visually approved. Make bow_shot and throw show the same action phase convincingly across S/N/E/W. Build synchronized key-pose contact sheets first. Correct front/back foreshortening and segment overlap, preserve West's right-hand bow convention, obscure front/back arrows appropriately, and keep throws beside the anatomical right shoulder. Preserve source release times. Inspect native pixels and seams before expanding to more clips. Explain what remains approximate. Do not claim visual equivalence from numerical tests alone.
