# Dungeon Master / GOA sprite rig — developer handoff from this chat

Prepared 2026-10-31. This is an implementation history and reproduction guide, not a verbatim transcript. Where earlier code changed during the conversation, the final rules below take precedence. Inspect the saved source for exact formulas and pixel coordinates.

## 1. Goal and final state

The user wanted the approved GOA-style characters to use modular weapons, armor and animation without drawing every equipment combination as a separate full sprite. We developed the Elf male first, tuned its animations interactively, packaged that result, then developed a Human adaptation.

The user approved the final Human preview in this chat. The accepted Human lives here:

```
/Users/kiwimango/Downloads/Dungeon-Master-master/
  Dungeon Master Sample/GOA Retarget Review - Human Male/
```

The approved Elf baseline is separate:

```
Dungeon Master Sample/GOA Reusable Animation Rig v1/
```

Do not overwrite either baseline with a new generic conversion. Duplicate or create a new output for the next character.

This work builds a browser preview and reusable sprite rig. It does not integrate the Human into the live game, implement combat damage/collisions, or produce a newly verified full Human atlas set. The Elf package contains 97 exported animation clips. The Human has the renderer and clip data, with export buttons, but not a newly baked 97-clip Human export set.

## 2. Art and technical conventions

- Use the approved GOA-style sprites intended for the finished game. Do not substitute the older runtime Human that was mapped to Elf.
- Native character cells are **64×64**. Enlarged screenshots are presentation, not coordinate space.
- The base sheet is **256×192**: columns South, North, East, West; rows idle, walk A, walk B.
- The rig uses 15 parts per facing: head, torso, pelvis, and upper/lower/end pieces for both arms and both legs.
- Coordinates and pivots refer to the original full 64×64 canvas. Body-part PNGs retain that canvas.
- Preview exports use **192×192 padded cells**, body origin `[64,64]`, four S/N/E/W columns. Padding is not a change to native sprite resolution.
- Render with smoothing disabled and inspect at native size plus nearest-neighbor enlargement.
- Preserve each body's appearance. Shared timing does not mean identical anatomical dimensions, sockets or pose targets.

## 3. How the Elf animation library was built

Source implementation:

```
standalone/goa-races/elf-game-animations/
  extract.js
  runtime-source.json
  build.py
  engine.js
  app.js
  viewer.html
  check_polish.js
  check_ranged.js
  verify_export.py
  package.py
```

Generated local library:

```
Dungeon Master Sample/GOA Sword and Shield Rig/library/
```

### Runtime provenance

The user specifically requested the animations used by the installed Dungeon Master/Banners of the Deep game. We compared its bundled `gear3d.js` with the working runtime and extracted the included skill, work and death definitions rather than adopting an unrelated sample catalog.

Extraction records source hashes and verifies the runtime relationship. The installed configuration had doll animation enabled, but the separate mining/woodcutting doll moves disabled; those jobs use the active attack-strip fallback in this library. Physics reactions are deterministic visual approximations, not recordings of the live simulation.

### Rendering

`ElfAnimator.sample()` turns source motion channels into waist/torso transforms and hand/foot targets. Two-bone IK solves limbs. `part()` rotates complete cutouts around their source pivots and places them at destination joints. `gear()` attaches equipment at measured image grips. `render()` supplies facing-specific body/limb/equipment ordering.

The game weapon channel `W` is absolute. An early mistake added torso lean a second time; removing it corrected side-view weapon angles. Two-handed weapons constrain their second grip along the weapon axis.

Idle/walk can use drawn source body frames. Other poses use the articulated parts. Missing surfaces are handled with prepared parts and small joint backing; this is **not** an AI-inpainting pipeline.

### Timing retained

- Bow: raise by 0.32s, draw through 0.72s, release at 0.90s, start lowering at 1.15s, rest by 1.75s.
- Throw: windup around 0.26s, release at 0.38s, follow-through around 0.52s, recovery by roughly 0.75–1.00s.
- At release, remove the held projectile and create the detached preview projectile at the release grip. Do not draw both instances.

## 4. Important visual corrections and rejected approaches

### Foreshortening

The original front/back solver preserved full screen-space arm lengths. Arms reaching toward/away from the camera then pushed their elbows sideways, producing a lateral-raise appearance. We introduced shorter projected segments for selected poses and matching raster transforms. Physical calibration and visible projected length are different concepts.

Some later poses use authored elbow/hand targets through `projectArm()`. Do not add a test that blindly demands all projected limbs retain their full side-view lengths.

### Bow

We first tried separate East/West body orientations: East back-facing torso, West front-facing torso, each with a side-facing head. The user subsequently chose **West as the master and East as its exact horizontal reflection**. That supersedes the separate East pose.

The bow uses a separate rendered string. North/South arrows show only a short end/tip, with North body occlusion. The side views show the shaft.

The drawing arm initially folded into an L after release because it returned toward a raised equipment/shield grip. We changed recovery toward relaxed hand positions and straightened both arms as they lower. The later Human engine preserves this correction.

### Spear throw

The user refined this in several stages:

1. Right-shoulder windup/release instead of center-chest launch.
2. East/West spear level on screen.
3. North/South spear vertical on screen; the briefly tested horizontal front/back spear was rejected.
4. South throwing forearm upright.
5. North windup forms a reverse L: elbow out, forearm up, hand above elbow.
6. North hand keeps a stable grip in windup, then turns at release.
7. North spear is narrower/foreshortened, later with a longer rear shaft and thicker forward section around the same grip.
8. North held spear is a layering exception: draw it over the body, then its gripping hand over the shaft.

Do not extrapolate the North spear exception to every weapon.

### Tests were not visual approval

We repeatedly found ugly poses despite passing joint/timing tests. We explicitly corrected the claim that a source-accurate animation or a successful build automatically looks right. Numerical validation and visual approval must be reported separately.

## 5. Why the first Human conversion looked wrong

Initial Human conversion folder:

```
Dungeon Master Sample/GOA Reusable Animation Rig v1 - Human Male/
```

The first review found reused Elf pose coordinates, crude hidden-surface fillers, synthetic far arms, and a South right-arm calibration of about 9px reach versus about 15px on the left. **Those were historical findings. The Human inputs were revised during this conversation and later had balanced arm lengths. Do not assume that old 9px calibration is still present.**

The current candidate was created from the then-current Human profile/assets and the approved Elf package. One real integration bug in our retarget script was ignoring `partSource` metadata. The revised cutter had borrowed some pieces from walking frames, so their source joints differed from the idle destination chain. Treating them as idle cutouts distorted the leg rotations and foot placement.

The fix: use `partSource[0]` and `[1]` as the source endpoints, while preserving the solved destination joints. A third `"fit"` entry requests segment-length fitting.

## 6. Current Human corrections — preserve these

### Side legs and feet

- Some walking-frame thigh/shin cutouts contained a pointed, foot-like fragment. Cropping only the foot did not remove it because it also existed in the thigh/shin artwork.
- Clean idle-side leg artwork replaced those fragments, with correct source endpoints for each reused piece.
- Reusing artwork does not merge the left/right skeletons. Each leg retains its own destination chain.
- East: **right leg leads and draws in front**.
- West: retain the accepted original pose and draw order. A global leg swap was rejected.
- Restoring old West artwork accidentally reintroduced the spike. The accepted resolution keeps the restored West ordering while replacing only the bad cutout artwork.
- Shin pixels stop before the source ankle boundary; foot pixels start at/below it. Remove duplicated toes from shins and calf pixels from feet. Small renderer ankle backing joins the pieces.

### Front/back arms

The cutter's overlapping horizontal bands duplicated wrist pixels between forearm and hand. Narrow shoulder ends and dark cut-edge outlines made visible creases during rotation.

The final repair reconstructs the source arm from the original pieces, then assigns:

- Upper arm through elbow row.
- Forearm from one row above elbow through the row before wrist.
- Hand from wrist row down, without duplicated forearm pixels.
- Small rounded backing at shoulder/elbow using existing limb colors.
- Local removal of dark internal cut-edge pixels inside shoulder/elbow/wrist overlaps. Preserve long external outlines; do not add black seams through joints.

`arm-cut-review.json` records original image references, so reruns do not repeatedly expand repaired parts. Original PNGs are retained.

### Final North layer order

This went through several user corrections. **Use the final order, not an intermediate experiment.**

For sword + shield, back to front:

1. Sword and right arm, with the sword behind the right bicep.
2. Shield.
3. Supporting left arm, visible on the shield's back.
4. Body/head, in front of both arms.

Within each North arm: **forearm → upper arm → hand**. The forearm sits behind the bicep.

The user rejected putting the bicep over the body. The user also rejected hiding the left arm at the very back behind the shield. The final left arm is visible over the shield back while still behind the body.

The separate North spear/hand exception remains as described above. Do not unify these branches into one indiscriminate foreground draw.

## 7. Reproduce the accepted Human exactly

Use the saved package directly. From its folder:

```sh
python3 rebuild.py
python3 -m http.server 8881 --bind 127.0.0.1
```

Open `http://127.0.0.1:8881/preview/`, or open `preview/index.html` locally.

The authoritative inputs for that rebuild are:

| File | Role |
| --- | --- |
| `profiles/character.json` | Joints, grips, `partSource`, image references, lead/near-leg assignment, bow pose targets |
| `source/engine.js` | Accepted Human rendering and pose logic, including local layering fixes |
| `source/app.js`, `source/viewer.html` | Viewer controls/template |
| `source/library-base.json` | Shared source clips and gear definitions |
| `preview/assets/` | Character parts, repair outputs and equipment PNGs |
| `arm-cut-review.json` | Original arm references and cut changes |
| `accepted-state.json` | User approval scope |
| `manifest.json` | File hashes for the saved snapshot |

Do not regenerate this profile from zones merely to rebuild the preview. Do not replace its `source/engine.js` with the original Elf renderer: that would discard local Human corrections.

## 8. Python tooling for another race or hybrid

Tool folder:

```
standalone/goa-races/character-retarget/
```

`retarget.py` creates a **new review candidate**. It accepts either an existing profile/assets or a zoned sprite sheet:

```sh
python3 standalone/goa-races/character-retarget/retarget.py \
  --profile '/path/character.json' --assets '/path/assets' \
  --output '/path/new-review-folder'

python3 standalone/goa-races/character-retarget/retarget.py \
  --inputs '/path/inputs' --race Human --name 'Human male' \
  --output '/path/another-new-review-folder'
```

Zone inputs: `sprites.png`, `fine.png`, `fine.json`, `<Race>.json`. Cutting requires Pillow and numpy; existing-profile builds use Python 3.9+ standard-library facilities. Use `--batch jobs.json` for a list of jobs. Existing output folders are refused rather than overwritten.

The script validates anatomy/image references, flags extreme front/back reach asymmetry, fits guard offsets by reach, and maps bow landmarks relative to neck/shoulder span/torso height. It preserves editable bow targets. It does not fully parameterize every throw/body-motion constant, reconstruct all hidden anatomy, or automatically rig wings/tails. Such anatomy is flagged for further work.

Manual calibrated overrides can be provided with `--overrides`. Set `keepGrips: true` to retain explicit grips. Output `poseTargets.bow` values can be adjusted and rebuilt without repeating the automatic guesses.

### Human-specific refinement scripts

These were written during this conversation. They encode review decisions for this Human and are **not blindly applicable to all races**:

```sh
python3 standalone/goa-races/character-retarget/refine_side_feet.py PACKAGE
python3 standalone/goa-races/character-retarget/refine_side_legs.py PACKAGE
python3 standalone/goa-races/character-retarget/refine_front_back_arms.py PACKAGE
python3 PACKAGE/rebuild.py
```

Run feet before leg-art remapping. The side-leg script fixes East's assignment and replaces West's bad far-leg art without globally swapping West. The arm script modifies North/South pieces only.

The generic converter does not automatically install all Human-specific North layer overrides. Copying those to a new body requires a deliberate review of its equipment and visible limbs.

## 9. Validation actually performed

- Elf final package: 97 clips, 9,140 directional samples, recorded source integrity, event timing, projected-limb/bounds checks, and browser error checks. Portable rebuild data matched the packaged Elf data.
- Retarget tool: tests for identity target mapping, asymmetry reporting, invalid joints, asset-path escape and refusing overwrite.
- Human candidate: 9,140 pose calculations checked for finite arm joints at the initial retarget stage; later source-pivot checks, foot ownership checks, arm cut-boundary checks, syntax/rebuild checks, and browser inspection of representative poses.
- Final Human visual state was approved by the user. It was not subjected to a newly repeated full 97-clip export verification after every local art/layer edit.

Do not reuse an Elf verification report as proof of Human validation. Do not report a successful build as proof that all animations look good.

## 10. How to review future changes

Inspect native size and enlarged nearest-neighbor output, with joints and equipment both on and off. Check idle/walk, sword guard, slash/thrust, bow draw/release/recovery, and throw windup/release across all views.

Useful times: bow `.32, .72, .90, 1.15, 1.40, 1.75`; throw `.26, .38, .52, .75`. Also watch continuous playback for pops. Check complete shoulder/torso coverage, no duplicate wrist pixels, correct source pivots, grounded feet, independent legs, spear grip, and the accepted North depth order.

Keep a baseline screenshot and profile/source snapshot before changing a shared layer. Fix cutout geometry, joint placement, motion targets and render order as separate problems. Several regressions here came from restoring old art when only the draw order needed restoring, or changing both facings when only East was wrong.

## Copyable instruction to another developer/AI

> Use the saved approved Human as the reference. Read this handoff and README-CLAUDE.md. Rebuild from the existing profile/assets/source to reproduce it; do not run the generic cutter over the accepted files. Preserve partSource pivots, East right-leg lead, West's accepted order, clean side-leg art, distinct wrist ownership, and North's final sword/arm/shield/body order. For a new race, create a new review output and calibrate it against its own anatomy. Share timing, not unverified coordinates. Keep technical checks separate from visual approval, and document any remaining approximation.
